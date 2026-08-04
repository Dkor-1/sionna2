# -*- coding: utf-8 -*-
"""p3_control_v2.py — ⭐ 기하 대리표적(큐브·박스·구) 대조군, **v2 메쉬 기준으로 재실행**.

물음: 사진 실측으로 다시 만든 우리 메쉬가 **여전히 상자를 이기는가?**
구판(outputs/p3_attack.json Q5): 우리 |−4.85| dB vs 부피등가 큐브 |+6.94| dB.

규약: μ(f)=10log10(mean_az σ_lin) · el=0 · 방위 360점 · 격자 λ/16 · PEC(|Γ|=1)
      — outputs/p3_ours_v2.json 과 같은 자. 주파수 격자도 같은 61점.
커널: src/rcs_po.rcs_from_points 계열 면적분. 대조군은 전부 **볼록체**라 자기차폐가 없어
      SBR 1-bounce PO 와 물리적으로 동일하다(가림 오차 0) → GPU 를 드론 스윕에 양보하고
      CPU 로 돌린다. ⭐ 커널 등가성은 `cube_vol_v1`(구판과 같은 한 변 132.7 mm) 를 함께
      계산해 p3_attack 의 +6.94 dB 를 재현하는지로 **직접 검증**한다.

실행:  PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/p3_control_v2.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "benchmark"))
os.environ.setdefault("SIONNA2_CPU", "1")

OUT = os.path.join(ROOT, "outputs", "p3_control_v2.json")
FREQS = np.linspace(1.8, 18.2, 61)                  # p3_ours_v2 와 동일 격자
AZ = np.linspace(0, 360, 360, endpoint=False)
DIV = 16
C0 = 299792458.0


def _sigma_az(mesh, fc_hz, spacing, chunk=16):
    """볼록 PEC 표적의 원시 σ(az) [m²] — 1-bounce PO 면적분(가림 없음)."""
    from rcs_po import mesh_to_points
    P, N, dA = mesh_to_points(mesh, spacing)
    lam = C0 / fc_hz
    k = 2 * np.pi / lam
    azr = np.radians(AZ)
    U = np.stack([np.cos(azr), np.sin(azr), np.zeros_like(azr)], axis=-1)
    P = P.astype(np.float64); N = N.astype(np.float64); dA = dA.astype(np.float64)
    out = np.empty(len(AZ))
    for s in range(0, len(AZ), chunk):
        Uc = U[s:s + chunk]
        NU = N @ Uc.T
        PU = P @ Uc.T
        integ = np.where(NU > 0, NU, 0.0) * dA[:, None] * np.exp(1j * 2 * k * PU)
        out[s:s + chunk] = (4 * np.pi / lam ** 2) * np.abs(integ.sum(axis=0)) ** 2
    return out, len(P)


def _stats(sig):
    lin = np.maximum(np.asarray(sig, float), 1e-30)
    sdb = 10 * np.log10(lin)
    amp = np.sqrt(lin)
    return dict(mu_dbsm=float(10 * np.log10(lin.mean())), eps_db=float(np.std(sdb)),
                cv_amp=float(np.std(amp) / np.mean(amp)))


def _job(arg):
    key, dims, f = arg
    from geom import box
    fc = f * 1e9
    m = box(*dims, group="box")
    t0 = time.time()
    sig, npts = _sigma_az(m, fc, (C0 / fc) / DIV)
    st = _stats(sig)
    st.update(f_ghz=float(f), n_points=int(npts), runtime_s=round(time.time() - t0, 2))
    return key, st


def main():
    from drones import DRONES, build_drone
    m3 = build_drone(DRONES["phantom3"])
    V = np.array(m3.v); F = np.array(m3.f)
    ext = (V.max(0) - V.min(0))
    v0, v1_, v2_ = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    vol = float(abs(np.einsum('ij,ij->i', v0, np.cross(v1_, v2_)).sum()) / 6.0)
    side_v2 = vol ** (1 / 3)
    print(f"[v2 mesh] bbox={ext}  volume={vol*1e3:.3f} L  cube side={side_v2*1e3:.1f} mm", flush=True)

    boxes = {
        "cube_vol_v2": ((side_v2, side_v2, side_v2),
                        f"PEC 정육면체, 부피 = v2 메쉬 고체부피 {vol*1e3:.3f} L (한 변 {side_v2*1e3:.1f} mm)"),
        "cube_vol_v1": ((0.1327, 0.1327, 0.1327),
                        "PEC 정육면체 한 변 132.7 mm — **구판과 같은 상자**(커널 등가성 교차검증용)"),
        "box_bbox_v2": (tuple(float(x) for x in ext),
                        f"PEC 박스 = v2 메쉬 bbox {ext[0]*1e3:.0f}×{ext[1]*1e3:.0f}×{ext[2]*1e3:.0f} mm"),
        "box_paper": ((0.35, 0.35, 0.20), "PEC 박스 350×350×200 mm — 논문 표기 치수를 그대로 상자로"),
        "box_bbox_lit": ((0.35, 0.20, 0.185), "PEC 박스 350×200×185 mm — Das Table I + DJI 높이"),
        "cube_side_max": ((0.35, 0.35, 0.35), "PEC 정육면체 한 변 350 mm — 최대치수를 그대로"),
    }

    jobs = [(k, dims, f) for k, (dims, _) in boxes.items() for f in FREQS]
    jobs.sort(key=lambda j: -j[2])                       # 비싼 것 먼저
    res: dict = {k: {} for k in boxes}
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=10) as ex:
        for i, (key, st) in enumerate(ex.map(_job, jobs)):
            res[key][f"{st['f_ghz']:.3f}"] = st
            if i % 40 == 0:
                print(f"  {i}/{len(jobs)}  {time.time()-t0:.0f}s", flush=True)

    from mie_pec_sphere import mie_pec_sigma_m2
    out = dict(
        _meta=dict(
            what="기하 대리표적 대조군 — v2(사진 실측) 메쉬 기준 재실행",
            generator="benchmark/p3_control_v2.py",
            generated=time.strftime("%Y-%m-%d %H:%M:%S"),
            p3_mesh_bbox_m=[float(x) for x in ext], p3_mesh_volume_m3=vol,
            n_tri=int(len(F)),
            freqs_ghz=[float(x) for x in FREQS], n_az=len(AZ), el_deg=0.0, div=DIV,
            kernel=("src/rcs_po 면적분(PEC |Γ|=1). 볼록체 → 자기차폐 없음 = SBR 1-bounce PO 와 "
                    "동일 물리. cube_vol_v1 이 구판 rcs_sbr 결과를 재현하는지로 검증한다."),
            convention="mu(f)=10log10(mean_az sigma_lin), p3_ours_v2.json 과 동일",
            wall_clock_s=round(time.time() - t0, 1)),
        controls={},
    )
    for k, (dims, desc) in boxes.items():
        fs = np.array(sorted(float(x) for x in res[k]))
        kk = {float(x): x for x in res[k]}
        mu = np.array([res[k][kk[x]]["mu_dbsm"] for x in fs])
        a, b = np.polyfit(fs, mu, 1)
        out["controls"][k] = dict(
            desc=desc, dims_m=list(dims),
            f_ghz=[float(x) for x in fs], mu_dbsm=[float(x) for x in mu],
            eps_db=[float(res[k][kk[x]]["eps_db"]) for x in fs],
            cv_amp=[float(res[k][kk[x]]["cv_amp"]) for x in fs],
            a=float(a), b=float(b))

    # 부피등가 구 — **정확 Mie** (메쉬 이산화 인공물이 없다)
    for name, vv in [("sphere_vol_v2", vol), ("sphere_eqvol_paperbox", 0.35 * 0.20 * 0.185)]:
        r = (3 * vv / (4 * np.pi)) ** (1 / 3)
        mu = np.array([10 * np.log10(float(mie_pec_sigma_m2(r, f * 1e9))) for f in FREQS])
        a, b = np.polyfit(FREQS, mu, 1)
        out["controls"][name] = dict(
            desc=f"PEC 구 r={r*1e3:.1f} mm (부피 {vv*1e3:.2f} L 등가), **정확 Mie** — 방위의존 없음",
            dims_m=[r], f_ghz=[float(x) for x in FREQS], mu_dbsm=[float(x) for x in mu],
            eps_db=[0.0] * len(FREQS), cv_amp=[0.0] * len(FREQS), a=float(a), b=float(b))

    json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1)
    print("wrote", OUT, f"({time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
