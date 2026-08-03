# -*- coding: utf-8 -*-
"""기하 대리표적(큐브·박스·구) 대조군 — Phantom 3 앵커와 같은 자로 잰다.

목적: '드론 메쉬 대신 금속 정육면체/직육면체를 놓는' 선행 관행(evasion_catalogue E10)이
      같은 실측 앵커(Yuan θ90) 대비 얼마나 틀리는지를 우리 메쉬와 나란히 잰다.
규약: μ(f) = 10log10( mean_az σ_lin ), el=0, 방위 360점, 1.8–18.2 GHz 21점 균등.
커널: src/rcs_po.rcs_from_points (PEC, |Γ|=1). 볼록체이므로 자기차폐가 없어
      SBR 1-bounce PO 와 물리적으로 동일하다(가림 오차 0).
"""
import json, sys, time
import numpy as np

sys.path.insert(0, "/home/yunjung/workspace/sionna2")
sys.path.insert(0, "/home/yunjung/workspace/sionna2/src")

from src import geom
from src.rcs_po import mesh_to_points, C0
from src.drones import DRONES, build_drone

OUT = "/home/yunjung/workspace/sionna2/outputs/p3_control.json"

FREQS = np.linspace(1.8, 18.2, 21)          # GHz, p3_ours 와 동일 격자
AZ = np.linspace(0, 360, 360, endpoint=False)


def sigma_az(mesh, fc_hz, spacing, az=AZ, el=0.0, chunk=24):
    P, N, dA = mesh_to_points(mesh, spacing)
    lam = C0 / fc_hz
    k = 2 * np.pi / lam
    azr = np.radians(az); elr = np.radians(el)
    U = np.stack([np.cos(elr) * np.cos(azr), np.cos(elr) * np.sin(azr),
                  np.full_like(azr, np.sin(elr))], axis=-1)
    P = P.astype(np.float64); N = N.astype(np.float64); dA = dA.astype(np.float64)
    out = np.empty(len(az))
    for s in range(0, len(az), chunk):
        Uc = U[s:s + chunk]
        NU = N @ Uc.T
        PU = P @ Uc.T
        integ = np.where(NU > 0, NU, 0.0) * dA[:, None] * np.exp(1j * 2 * k * PU)
        E = integ.sum(axis=0)
        out[s:s + chunk] = (4 * np.pi / lam ** 2) * np.abs(E) ** 2
    return out, len(P)


def mu_curve(mesh, div=16, name=""):
    mus, eps, npts = [], [], []
    for f in FREQS:
        fc = f * 1e9
        sp = (C0 / fc) / div
        t0 = time.time()
        sig, n = sigma_az(mesh, fc, sp)
        mus.append(10 * np.log10(sig.mean()))
        eps.append(float(np.std(10 * np.log10(np.maximum(sig, 1e-30)))))
        npts.append(n)
        print(f"  {name} {f:5.2f} GHz  mu={mus[-1]:8.3f} dBsm  np={n:8d}  {time.time()-t0:5.1f}s",
              flush=True)
    return np.array(mus), np.array(eps), npts


def fit(f, mu):
    a, b = np.polyfit(f, mu, 1)
    pred = a * f + b
    ss = 1 - np.sum((mu - pred) ** 2) / np.sum((mu - mu.mean()) ** 2)
    return float(a), float(b), float(ss)


# ---------------------------------------------------------------- 실제 P3 메쉬 치수
spec = DRONES["phantom3"]
m3 = build_drone(spec)
V = np.array(m3.v)
bb_lo, bb_hi = V.min(axis=0), V.max(axis=0)
ext = bb_hi - bb_lo
# 폐곡면 부피(발산정리) — 프롭 포함 전체 메쉬라 근사치
F = np.array(m3.f)
v0, v1, v2 = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
vol_signed = float(np.abs(np.einsum('ij,ij->i', v0, np.cross(v1, v2)).sum()) / 6.0)

print("P3 mesh bbox extents [m]:", ext, " signed volume [m^3]:", vol_signed, flush=True)

# 문헌(Das Table I)이 적는 표적 치수: 35 cm x 20 cm
LIT_L, LIT_W, LIT_H = 0.35, 0.20, 0.185     # 높이는 DJI 공표 185 mm

controls = {}
controls["box_bbox_lit"] = dict(
    mesh=geom.box(LIT_L, LIT_W, LIT_H, group="box"),
    desc="PEC 직육면체 0.350 x 0.200 x 0.185 m — 문헌 표기 치수(Das Table I 35x20 cm + DJI 높이)")
side_max = LIT_L
controls["cube_side_max"] = dict(
    mesh=geom.box(side_max, side_max, side_max, group="box"),
    desc=f"PEC 정육면체 한 변 {side_max:.3f} m — 최대치수를 그대로 쓴 '금속 큐브'")
side_eq = (LIT_L * LIT_W * LIT_H) ** (1 / 3)
controls["cube_eqvol_bbox"] = dict(
    mesh=geom.box(side_eq, side_eq, side_eq, group="box"),
    desc=f"PEC 정육면체 한 변 {side_eq:.4f} m — 위 직육면체와 같은 부피")

res = {}
for key, c in controls.items():
    print("==", key, flush=True)
    mu, ep, npts = mu_curve(c["mesh"], name=key)
    a, b, r2 = fit(FREQS, mu)
    res[key] = dict(desc=c["desc"], mu_dbsm=mu.tolist(), eps_db=ep.tolist(),
                    a=a, b=b, R2=r2, n_points=npts)

# 등가부피 PEC 구 — 정확 Mie
sys.path.insert(0, "/home/yunjung/workspace/sionna2/benchmark")
from mie_pec_sphere import mie_pec_sigma_m2
r_eq = (3 * LIT_L * LIT_W * LIT_H / (4 * np.pi)) ** (1 / 3)
mu_sph = np.array([10 * np.log10(float(mie_pec_sigma_m2(r_eq, f * 1e9))) for f in FREQS])
a, b, r2 = fit(FREQS, mu_sph)
res["sphere_eqvol_mie"] = dict(
    desc=f"PEC 구 반지름 {r_eq:.4f} m (직육면체와 등가부피), **정확 Mie** — 방위의존 없음",
    mu_dbsm=mu_sph.tolist(), a=a, b=b, R2=r2)

# 수렴 대조 (div=24, 3주파수)
conv = {}
for f in [1.8, 10.0, 18.2]:
    fc = f * 1e9
    s16, _ = sigma_az(controls["box_bbox_lit"]["mesh"], fc, (C0 / fc) / 16)
    s24, _ = sigma_az(controls["box_bbox_lit"]["mesh"], fc, (C0 / fc) / 24)
    conv[f"{f:.2f}"] = dict(div16=float(10 * np.log10(s16.mean())),
                            div24=float(10 * np.log10(s24.mean())),
                            delta_db=float(10 * np.log10(s24.mean() / s16.mean())))
    print("conv", f, conv[f"{f:.2f}"], flush=True)

meta = dict(
    p3_mesh_bbox_m=ext.tolist(), p3_mesh_volume_m3=vol_signed,
    lit_dims_m=[LIT_L, LIT_W, LIT_H],
    freqs_ghz=FREQS.tolist(), n_az=len(AZ), el_deg=0.0, div=16,
    kernel="src/rcs_po.rcs_from_points (PEC |Γ|=1). 볼록체 → 자기차폐 없음 = SBR 1-bounce PO 와 동일 물리",
    convention="mu(f)=10log10(mean_az sigma_lin), p3_ours.json 과 동일")

json.dump(dict(_meta=meta, controls=res, convergence=conv), open(OUT, "w"),
          ensure_ascii=False, indent=1)
print("wrote", OUT)
