# -*- coding: utf-8 -*-
"""
das_fleet_box_control.py — ⭐ **큐브(상자) 대조군을 네 기체 전부에 대해** 돌린다
================================================================================
묻는 것
  "드론 메쉬 대신 금속 상자를 놓는" 선행 관행(evasion_catalogue E10)이 같은 실측 앵커
  (Das Table III) 앞에서 얼마나 틀리는가. **우리 메쉬가 상자를 이기는가.**

무엇을 계산하나
  네 기체 각각에 대해 상자/구 대조표적을 두고, Das 가 그 기체를 잰 **바로 그 격자**
  (주파수 창·방위 격자·θb 7 각도)에서 σ 를 내고, 같은 규약으로 μ(f)=a·f+b 를 적합한다.
  → DL_box = μ_box(f_c) − [a_das·f_c + b_das + 2.5068]   (우리 메쉬의 DL 과 같은 정의)

왜 닫힌형 PO 인가 (그리고 그것이 우리 커널과 같은 물리인 이유)
  우리 SBR 커널은 û_i 개구에 격자광선을 쏘고 히트마다 |Γ|·e^{jk(û_i+û_s)·p}·d² 를 더한다.
  d² = (n̂·û_i)dS 이므로 연속극한이 정확히
        E(i,s) = ∫_lit |Γ| e^{jk(û_i+û_s)·p} (n̂·û_i) dS ,  σ = 4π/λ² |E|²
  이고, 게이트는 (n̂·û_i>0) ∧ (n̂·û_s>0) 다. 상자는 **볼록**이라 자기가림이 없고
  exit_vis 그림자광선도 no-op 다 → 위 적분이 면마다 닫힌형(사각형 → sinc×sinc)으로 풀린다.
  즉 닫힌형은 우리 커널의 **이산화 오차만 뺀** 같은 물리다. 그 차이는 verify 절이 직접 잰다
  (같은 상자를 rcs_sbr_multistatic 으로도 돌려 비교).
  ⚠ 닫힌형이 이산화 잡음이 없다는 점은 **상자 쪽에 유리**하다 — 대조군을 유리하게 두는 것은
    "우리가 상자를 이긴다" 는 주장을 약화시키는 방향이므로 보수적이다.

대조표적 네 종
  box_table1   Das Table I 치수 그대로의 PEC 직육면체
  box_bbox     우리 메쉬의 bounding box PEC 직육면체
  cube_eqvol   우리 메쉬와 **부피가 같은** PEC 정육면체
  sphere_eqvol 우리 메쉬와 부피가 같은 PEC 구 (σ=πa², 주파수 무관 — 광학영역)

산출: outputs/das_fleet_box_control.json  (⛔ 다른 워크플로 파일은 쓰지 않는다)
"""
from __future__ import annotations

import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (os.path.join(ROOT, "src"), os.path.join(ROOT, "benchmark")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np                                                    # noqa: E402
from gpu import pick                                                  # noqa: E402

pick()

from rcs_sbr import rcs_sbr_multistatic, _look                        # noqa: E402
from drones import DRONES, build_drone                                # noqa: E402
from geom import box as geom_box                                      # noqa: E402

C0 = 299792458.0
THETA_B = [0, 15, 30, 45, 60, 75, 90]
GAMMA_PEC = 1.0

#  기체별 격자 — das_fleet_spec.json / das_fleet_sigma.GRIDS 와 **같은 창·같은 방위격자**.
GRIDS = {
    "phantom3": dict(f_ghz=np.linspace(1.8, 18.2, 21), az_n=360, fc=10.0,
                     mesh_key="phantom3", table1_m=(0.35 / np.sqrt(2), 0.35 / np.sqrt(2), 0.20),
                     table1_note="Table I 35 cm = 수평대각 → 대각이 0.35 m 인 정사각 바닥(0.2475 m), 높이 0.20 m"),
    "phantom2": dict(f_ghz=11.0 + 0.1 * np.arange(0, 150, 5), az_n=360, fc=18.5,
                     mesh_key="phantom3", table1_m=(0.35 / np.sqrt(2), 0.35 / np.sqrt(2), 0.20),
                     table1_note="Table I 35 cm = 수평대각(P3 와 같은 수) → 0.2475 m 정사각 바닥, 높이 0.20 m"),
    "mini2": dict(f_ghz=np.linspace(21.0, 27.0, 41), az_n=720, fc=24.0,
                  mesh_key="mini2", table1_m=(0.159, 0.203, 0.056),
                  table1_note="Table I 15.9x20.3 cm = DJI 공표 unfolded 바닥면적, 높이 56 mm"),
    "m350rtk": dict(f_ghz=np.linspace(21.0, 27.0, 41), az_n=720, fc=24.0,
                    mesh_key="m350rtk", table1_m=(0.81, 0.67, 0.43),
                    table1_note="Table I 81x67 cm = DJI 공표 unfolded 바닥면적, 높이 430 mm"),
}

#  Das Table III (a, b) — outputs/das_fleet_spec.json :: table3 와 같은 수(검증필).
DAS_T3 = {
    "phantom2": {0: (0.21, -12.10), 15: (0.50, -19.31), 30: (0.22, -13.30), 45: (0.21, -14.76),
                 60: (0.12, -14.18), 75: (-0.13, -7.85), 90: (0.08, -10.40)},
    "phantom3": {0: (0.21, -19.19), 15: (0.21, -19.23), 30: (0.21, -19.33), 45: (0.21, -19.48),
                 60: (0.21, -19.64), 75: (0.21, -19.77), 90: (0.21, -19.82)},
    "mini2": {0: (0.07, -25.85), 15: (0.07, -25.89), 30: (0.07, -25.99), 45: (0.07, -26.14),
              60: (0.07, -26.30), 75: (0.07, -26.43), 90: (0.07, -26.47)},
    "m350rtk": {0: (0.17, -18.85), 15: (0.17, -18.89), 30: (0.17, -18.99), 45: (0.17, -19.15),
                60: (0.17, -19.31), 75: (0.17, -19.43), 90: (0.17, -19.48)},
}
DAS_OFFSET_DB = 2.5068          # das_fleet_ours.json :: convention.das_offset_db


# --------------------------------------------------------------------------- #
#  닫힌형 PO — 직육면체
# --------------------------------------------------------------------------- #
def _sinc(x):
    """sin(x)/x, x=0 에서 1."""
    return np.where(np.abs(x) < 1e-12, 1.0, np.sin(x) / np.where(np.abs(x) < 1e-12, 1.0, x))


def box_faces(lx, ly, lz):
    """6 면 → (중심, 법선, 면내축1, 길이1, 면내축2, 길이2)."""
    hx, hy, hz = lx / 2, ly / 2, lz / 2
    ex, ey, ez = np.eye(3)
    return [
        (np.array([+hx, 0, 0]), +ex, ey, ly, ez, lz),
        (np.array([-hx, 0, 0]), -ex, ey, ly, ez, lz),
        (np.array([0, +hy, 0]), +ey, ex, lx, ez, lz),
        (np.array([0, -hy, 0]), -ey, ex, lx, ez, lz),
        (np.array([0, 0, +hz]), +ez, ex, lx, ey, ly),
        (np.array([0, 0, -hz]), -ez, ex, lx, ey, ly),
    ]


def box_sigma(dims, fc_hz, u_i, U_s, gamma=GAMMA_PEC):
    """상자의 바이스태틱 σ [m²] (닫힌형 PO). U_s = (M,3) → 길이 M 배열."""
    lam = C0 / fc_hz
    k = 2 * np.pi / lam
    u_i = np.asarray(u_i, float)
    U_s = np.atleast_2d(np.asarray(U_s, float))
    out = np.zeros(len(U_s), complex)
    for c, n, a1, L1, a2, L2 in box_faces(*dims):
        ci = float(n @ u_i)
        if ci <= 1e-9:                                   # 조명 게이트
            continue
        w = u_i[None, :] + U_s                           # (M,3)
        gate = (U_s @ n) > 1e-9                          # 수신 게이트
        ph = np.exp(1j * k * (w @ c))
        s1 = _sinc(k * (w @ a1) * L1 / 2)
        s2 = _sinc(k * (w @ a2) * L2 / 2)
        out += np.where(gate, gamma * ci * (L1 * L2) * ph * s1 * s2, 0.0)
    return (4 * np.pi / lam ** 2) * np.abs(out) ** 2


def sphere_sigma(radius):
    """PEC 구, 광학영역 σ = π a² (주파수 무관, 방위 무관, 바이스태틱도 같은 값 — PO 근사)."""
    return np.pi * radius ** 2


# --------------------------------------------------------------------------- #
#  방위 스윕 + 통계 (das_fleet_ours 규약과 동일)
# --------------------------------------------------------------------------- #
def mu_eps(dims, f_ghz, az_n, kind="box", radius=None):
    """(mu_lin[nf,7], mu_db[nf,7], eps[nf,7]) — μ_lin=10log10(mean_φ σ), μ_db=mean_φ(10log10 σ)."""
    AZ = np.linspace(0.0, 360.0, az_n, endpoint=False)
    nf = len(f_ghz)
    mu_lin = np.empty((nf, len(THETA_B)))
    mu_db = np.empty((nf, len(THETA_B)))
    eps = np.empty((nf, len(THETA_B)))
    for i, fg in enumerate(f_ghz):
        if kind == "sphere":
            sig = np.full((az_n, len(THETA_B)), sphere_sigma(radius))
        else:
            sig = np.empty((az_n, len(THETA_B)))
            for j, phi in enumerate(AZ):
                u_i = _look(phi, 0.0)
                U_s = np.array([_look(phi + tb, 0.0) for tb in THETA_B])
                sig[j] = box_sigma(dims, fg * 1e9, u_i, U_s)
        sdb = 10 * np.log10(np.maximum(sig, 1e-30))
        mu_lin[i] = 10 * np.log10(np.maximum(sig.mean(axis=0), 1e-30))
        mu_db[i] = sdb.mean(axis=0)
        eps[i] = sdb.std(axis=0)
    return mu_lin, mu_db, eps


def linfit(f, y):
    a, b = np.polyfit(f, y, 1)
    pred = a * f + b
    rmse = float(np.sqrt(np.mean((y - pred) ** 2)))
    return float(a), float(b), rmse


# --------------------------------------------------------------------------- #
#  ⭐ 검산 — 닫힌형이 우리 SBR 커널과 같은 물리인가
# --------------------------------------------------------------------------- #
def verify_vs_sbr(dims, f_ghz, n_az=12, div=16):
    """같은 상자를 rcs_sbr_multistatic(금속 그룹)으로도 돌려 dB 차를 잰다."""
    mesh = geom_box(*dims, group="metal")
    gm = {"metal": "metal"}
    AZ = np.linspace(0.0, 360.0, n_az, endpoint=False)
    rows = []
    for fg in f_ghz:
        fc = fg * 1e9
        lam = C0 / fc
        for phi in AZ:
            u_i = _look(phi, 0.0)
            U_s = [_look(phi + tb, 0.0) for tb in THETA_B]
            s_sbr = np.atleast_1d(np.asarray(rcs_sbr_multistatic(
                mesh, gm, fc, u_i, U_s, spacing=lam / div, cache_key=("boxctl", dims, round(fc / 1e6)),
                penetrate=False, jitter=2, exit_vis=True, symmetrize=False), float))
            s_cf = box_sigma(dims, fc, u_i, np.array(U_s), gamma=0.99986)
            for t, tb in enumerate(THETA_B):
                rows.append(dict(f_ghz=float(fg), az_deg=float(phi), theta_b=tb,
                                 sbr_dbsm=float(10 * np.log10(max(s_sbr[t], 1e-30))),
                                 closed_dbsm=float(10 * np.log10(max(s_cf[t], 1e-30)))))
    d = np.array([r["sbr_dbsm"] - r["closed_dbsm"] for r in rows])
    fin = np.isfinite(d) & (d > -60) & (d < 60)
    mono = np.array([r["theta_b"] == 0 for r in rows])
    return dict(n=int(fin.sum()), mean_db=float(d[fin].mean()), rms_db=float(np.sqrt((d[fin] ** 2).mean())),
                p90_abs_db=float(np.percentile(np.abs(d[fin]), 90)),
                mono_rms_db=float(np.sqrt((d[fin & mono] ** 2).mean())),
                bist_rms_db=float(np.sqrt((d[fin & ~mono] ** 2).mean())),
                what=("SBR(격자 λ/16, jitter=2) − 닫힌형(연속극한). 0 에 가까울수록 닫힌형이 "
                      "우리 커널의 연속극한이라는 뜻이고, 남는 것은 이산화 오차다."))


def main():
    t_all = time.time()
    out = {"_meta": dict(
        generated=time.strftime("%Y-%m-%d %H:%M:%S"),
        generator="benchmark/das_fleet_box_control.py",
        what="⭐ 큐브(상자)·구 대조군 — 네 기체 전부, Das 격자·Das 규약",
        wrote_only="outputs/das_fleet_box_control.json",
        convention="μ_lin(f)=10log10(mean_φ σ) · DL_box = μ_lin(f_c) − [a_das·f_c + b_das + 2.5068]",
        kernel="닫힌형 PO(사각면 sinc×sinc) — 우리 SBR+PO 커널의 연속극한. verify 절이 그 등가성을 잰다.",
    ), "airframes": {}}

    for af, G in GRIDS.items():
        mesh = build_drone(DRONES[G["mesh_key"]])
        V = np.asarray(mesh.v, float)
        ext = V.max(0) - V.min(0)
        F = np.asarray(mesh.f, int)
        v0, v1, v2 = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
        vol = float(abs(np.einsum("ij,ij->i", v0, np.cross(v1, v2)).sum()) / 6.0)
        side = vol ** (1 / 3)
        r_eq = (3 * vol / (4 * np.pi)) ** (1 / 3)

        controls = {
            "box_table1": (tuple(G["table1_m"]), "box", G["table1_note"]),
            "box_bbox": (tuple(float(x) for x in ext), "box",
                         f"우리 메쉬 bbox {ext[0]*1e3:.0f}x{ext[1]*1e3:.0f}x{ext[2]*1e3:.0f} mm 의 PEC 상자"),
            "cube_eqvol": ((side, side, side), "box",
                           f"메쉬와 부피가 같은 PEC 정육면체(한 변 {side*1e3:.1f} mm, V={vol*1e3:.2f} L)"),
            "sphere_eqvol": ((2 * r_eq,) * 3, "sphere",
                             f"메쉬와 부피가 같은 PEC 구(반경 {r_eq*1e3:.1f} mm), σ=πa² 광학영역"),
        }

        f_ghz = np.asarray(G["f_ghz"], float)
        fc = G["fc"]
        rec = dict(mesh_key=G["mesh_key"], band_ghz=[float(f_ghz[0]), float(f_ghz[-1])],
                   band_centre_ghz=fc, n_freq=len(f_ghz), az_n=G["az_n"],
                   mesh_bbox_m=[float(x) for x in ext], mesh_volume_m3=vol, controls={})
        for name, (dims, kind, desc) in controls.items():
            t0 = time.time()
            mu_lin, mu_db, eps = mu_eps(dims, f_ghz, G["az_n"], kind=kind, radius=r_eq)
            per = {}
            for t, tb in enumerate(THETA_B):
                a, b, rmse = linfit(f_ghz, mu_lin[:, t])
                a_d, b_d, _ = linfit(f_ghz, mu_db[:, t])
                das_a, das_b = DAS_T3[af][tb]
                das_mu = das_a * fc + das_b
                mu_fc = a * fc + b
                per[str(tb)] = dict(
                    a=a, b=b, rmse_db=rmse, mu_lin_at_fc_dbsm=mu_fc,
                    mu_db_at_fc_dbsm=a_d * fc + b_d,
                    eps_at_fc_db=float(np.interp(fc, f_ghz, eps[:, t])),
                    das_a=das_a, das_mu_at_fc_dbsm=das_mu,
                    DL_prereg_db=mu_fc - (das_mu + DAS_OFFSET_DB),
                    DL_dbdomain_db=(a_d * fc + b_d) - das_mu,
                    Da_db_per_ghz=a - das_a)
            rec["controls"][name] = dict(dims_m=[float(x) for x in dims], kind=kind, desc=desc,
                                         by_theta_b=per, runtime_s=round(time.time() - t0, 1))
            print(f"[{af}] {name:13s} DL(0)={per['0']['DL_prereg_db']:+7.2f} dB "
                  f"({time.time()-t0:.1f}s)", flush=True)
        out["airframes"][af] = rec

    #  검산 — 가장 작은 상자 하나로 닫힌형 ↔ SBR 등가성
    print("[verify] closed-form vs SBR ...", flush=True)
    out["verify_closed_form_vs_sbr"] = {
        "mini2_box_table1": verify_vs_sbr((0.159, 0.203, 0.056), [21.0, 24.0, 27.0], n_az=12),
        "phantom3_box_table1": verify_vs_sbr((0.2475, 0.2475, 0.20), [1.8, 10.0, 18.2], n_az=12),
    }
    out["_meta"]["runtime_s"] = round(time.time() - t_all, 1)
    p = os.path.join(ROOT, "outputs", "das_fleet_box_control.json")
    with open(p, "w") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("wrote", p, f"({time.time()-t_all:.0f}s)")


if __name__ == "__main__":
    main()
