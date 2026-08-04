# -*- coding: utf-8 -*-
"""
das_fleet_box_verify_mu.py — 상자 대조군의 **닫힌형 ↔ SBR 등가성을 μ 수준에서** 잰다
=====================================================================================
왜 다시 재나
  das_fleet_box_control.py 의 1 차 검산은 자세별(σ(φ)) dB 차의 rms 였다. 그 지표는 상자의
  **sinc 널(deep null)** 에 지배된다 — 널 안쪽은 σ 가 −60 dBsm 급이라 이산화 잡음 1 개가
  수십 dB 로 보인다. 그러나 대조에 실제로 쓰는 양은 **방위평균 μ_lin(f)** 다. 그래서 같은
  방위격자 전체에서 μ 를 두 방법으로 내어 비교한다. 이게 옳은 자다.

산출: outputs/das_fleet_box_control.json 의 `verify_mu_closed_vs_sbr` 절을 갱신한다
     (같은 파일의 다른 절은 건드리지 않는다).
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
from geom import box as geom_box                                      # noqa: E402
from das_fleet_box_control import box_sigma, THETA_B, C0              # noqa: E402

CASES = {
    #  이름: (치수, 주파수[GHz], 방위점수)
    "mini2_box_table1": ((0.159, 0.203, 0.056), [21.0, 24.0, 27.0], 720),
    "phantom3_box_table1": ((0.2475, 0.2475, 0.20), [1.8, 10.0, 18.2], 360),
}


def run(dims, f_list, az_n, div=16):
    mesh = geom_box(*dims, group="metal")
    gm = {"metal": "metal"}
    AZ = np.linspace(0.0, 360.0, az_n, endpoint=False)
    rows = []
    for fg in f_list:
        fc = fg * 1e9
        lam = C0 / fc
        s_sbr = np.empty((az_n, len(THETA_B)))
        s_cf = np.empty((az_n, len(THETA_B)))
        t0 = time.time()
        for j, phi in enumerate(AZ):
            u_i = _look(phi, 0.0)
            U_s = [_look(phi + tb, 0.0) for tb in THETA_B]
            s_sbr[j] = np.atleast_1d(np.asarray(rcs_sbr_multistatic(
                mesh, gm, fc, u_i, U_s, spacing=lam / div,
                cache_key=("boxmu", dims, round(fc / 1e6)),
                penetrate=False, jitter=2, exit_vis=True, symmetrize=False), float))
            s_cf[j] = box_sigma(dims, fc, u_i, np.array(U_s), gamma=0.99986)
        mu_sbr = 10 * np.log10(np.maximum(s_sbr.mean(axis=0), 1e-30))
        mu_cf = 10 * np.log10(np.maximum(s_cf.mean(axis=0), 1e-30))
        rows.append(dict(f_ghz=float(fg), theta_b=THETA_B,
                         mu_lin_sbr_dbsm=[float(x) for x in mu_sbr],
                         mu_lin_closed_dbsm=[float(x) for x in mu_cf],
                         d_db=[float(a - b) for a, b in zip(mu_sbr, mu_cf)],
                         runtime_s=round(time.time() - t0, 1)))
        print(f"  f={fg:5.2f} GHz  Δμ(θb=0)={mu_sbr[0]-mu_cf[0]:+.3f} dB  "
              f"Δμ(all)={np.abs(mu_sbr-mu_cf).max():.3f} dB max  ({time.time()-t0:.0f}s)", flush=True)
    d0 = np.array([r["d_db"][0] for r in rows])
    dall = np.array([r["d_db"] for r in rows]).ravel()
    return dict(rows=rows, az_n=az_n, div=div,
                mono_mean_db=float(d0.mean()), mono_rms_db=float(np.sqrt((d0 ** 2).mean())),
                all_mean_db=float(dall.mean()), all_rms_db=float(np.sqrt((dall ** 2).mean())),
                all_max_abs_db=float(np.abs(dall).max()),
                what="Δ = μ_lin(SBR 격자 λ/16, jitter=2) − μ_lin(닫힌형 연속극한), 같은 방위격자 전체 평균")


def main():
    p = os.path.join(ROOT, "outputs", "das_fleet_box_control.json")
    with open(p) as fh:
        out = json.load(fh)
    res = {}
    for name, (dims, fl, az_n) in CASES.items():
        print(f"[{name}] dims={dims}", flush=True)
        res[name] = run(dims, fl, az_n)
    res["_reading"] = ("μ 수준에서 두 방법이 얼마나 같은가. |Δμ| 가 작을수록 닫힌형 대조군이 "
                       "우리 커널과 **같은 자**로 잰 것이다. 자세별 dB rms(1 차 검산)가 큰 것은 "
                       "sinc 널 안쪽 때문이고, 대조에 쓰는 양은 이 μ 다.")
    out["verify_mu_closed_vs_sbr"] = res
    with open(p, "w") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("updated", p)


if __name__ == "__main__":
    main()
