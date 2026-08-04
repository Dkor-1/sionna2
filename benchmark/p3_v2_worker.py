# -*- coding: utf-8 -*-
"""p3_v2_worker.py — Phantom 3 **el=0 전용** 원시 σ(az) 워커 (v2 메쉬).

주파수 몇 개를 인자로 받아 그 주파수의 σ(az) 와 통계를 계산해 부분 JSON 으로 떨군다.
⚠ 규약은 구판(outputs/p3_ours.json meta)과 **완전히 동일**해야 한다:
    div=16 · n_az=360 · jitter=2(커널 기본) · penetrate=True(커널 기본) · max_bounce=1(배치 커널)
    · ptd=False · μ(f)=10log10(mean_az σ_lin)  [선형평균]
바뀐 것은 오직 **메쉬**(사진 실측 재구축)와 **주파수 격자 밀도**뿐이다.

사용:  SIONNA2_GPU=2 python p3_v2_worker.py <out.json> <f1,f2,...>   (GHz)
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "benchmark"))

import rcs_anchor as RA                                   # noqa: E402  (import 시 GPU 고정)

C0 = 299792458.0
DRONE = "phantom3"
N_AZ = 360
DIV = 16
EL = 0.0


def one_freq(f_ghz: float) -> dict:
    """단일 주파수의 원시 σ(az) 와 구판과 같은 통계 묶음."""
    t0 = time.time()
    fc = float(f_ghz) * 1e9
    sig = RA.raw_sigma_az(DRONE, fc, EL, n_az=N_AZ, div=DIV, ptd=False)
    lin = np.maximum(np.asarray(sig, float), 1e-30)
    sdb = 10.0 * np.log10(lin)
    mu = float(10.0 * np.log10(lin.mean()))
    mean_db = float(sdb.mean())

    summary, frozen = RA.fit_distributions(lin)
    lam_mm = C0 / fc * 1e3
    return dict(
        f_ghz=float(f_ghz),
        lambda_mm=lam_mm,
        ray_spacing_mm=lam_mm / DIV,
        mu_dbsm=mu,
        mean_db_domain_dbsm=mean_db,
        lin_minus_db_mean_db=mu - mean_db,
        eps_db=float(np.std(sdb)),
        median_dbsm=float(np.median(sdb)),
        peak_dbsm=float(sdb.max()),
        min_dbsm=float(sdb.min()),
        p90_dbsm=float(np.percentile(sdb, 90)),
        percentiles_norm=RA.percentiles_norm(lin),
        distributions=summary,
        fit_rmse_db=RA.fit_rmse_db(lin, frozen),
        runtime_s=round(time.time() - t0, 2),
        sigma_dbsm_az=[round(float(x), 4) for x in sdb],
    )


def main():
    out_path = sys.argv[1]
    freqs = [float(x) for x in sys.argv[2].split(",")]
    res = {}
    for f in freqs:
        e = one_freq(f)
        res[f"{f:.3f}"] = e
        print(f"[{os.environ.get('SIONNA2_GPU','?')}] {f:6.3f} GHz  mu={e['mu_dbsm']:8.3f} dBsm  "
              f"eps={e['eps_db']:5.2f} dB  {e['runtime_s']:7.1f}s", flush=True)
        json.dump(res, open(out_path, "w"), ensure_ascii=False)     # 중간 저장(죽어도 회수)
    json.dump(res, open(out_path, "w"), ensure_ascii=False)
    print("done", out_path, flush=True)


if __name__ == "__main__":
    main()
