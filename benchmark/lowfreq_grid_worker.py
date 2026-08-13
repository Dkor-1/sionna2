# -*- coding: utf-8 -*-
"""
lowfreq_grid_worker.py — 저주파 격차 판정용 **격자 사다리** 워커 (1 프로세스 = 1 GPU 슬롯)
==========================================================================================
쓰임새: benchmark/lowfreq_grid.py 가 만든 태스크 조각을 받아 μ(f, d) 를 계산해 부분 JSON 으로 뱉는다.

호출:  SIONNA2_GPU=3 python benchmark/lowfreq_grid_worker.py <tasks.json> <out.json>

⚠ 규약은 생산 경로(benchmark/rcs_anchor.raw_sigma_az)와 **spacing 만** 다르다:
  el=0 · az=linspace(0,360,n_az,endpoint=False) · penetrate=True · ptd=False · max_bounce=1 ·
  jitter=2 · 재질 DRONE_GROUP_MAT · μ=10log10(mean_φ σ_lin) [dBsm] · ε=std(10log10 σ_lin) [dB].
  spacing 은 λ 상대가 아니라 **절대값[m]** 으로 주입한다 — 그게 이 실험의 전부다.
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

sys.path[:0] = ["/workspace/sionna/src",
                "/workspace/sionna/benchmark"]

# rcs_sbr 는 import 시점에 gpu.pick() 을 부른다 → SIONNA2_GPU 는 부모가 이미 넣어 두었다.
from rcs_sbr import rcs_sbr_batch                       # noqa: E402
from drones import DRONES, build_drone, DRONE_GROUP_MAT  # noqa: E402

C0 = 299792458.0


def main():
    tasks = json.load(open(sys.argv[1]))
    out_path = sys.argv[2]

    mesh = build_drone(DRONES["phantom3"])
    gm = {g: mat for g, (mat, _) in DRONE_GROUP_MAT.items()}

    res = []
    for i, t in enumerate(tasks):
        f = float(t["f_ghz"]) * 1e9
        d = float(t["d_mm"]) * 1e-3
        n_az = int(t["n_az"])
        az = np.linspace(0.0, 360.0, n_az, endpoint=False)
        t0 = time.time()
        sig = rcs_sbr_batch(mesh, gm, f, az_deg=az, el_deg=0.0, spacing=d,
                            cache_key=("phantom3", round(f / 1e6), 0.0, "lfg"))
        dt = time.time() - t0
        sig = np.maximum(np.atleast_1d(np.asarray(sig, float)), 1e-30)
        rec = dict(t)
        rec.update(mu_dbsm=float(10.0 * np.log10(np.mean(sig))),
                   eps_db=float(np.std(10.0 * np.log10(sig))),
                   median_dbsm=float(np.median(10.0 * np.log10(sig))),
                   sigma_dbsm_az=[round(float(x), 4) for x in 10.0 * np.log10(sig)],
                   t_s=round(dt, 2))
        res.append(rec)
        # 진행상황을 매번 덮어써 둔다 — 중간에 죽어도 앞부분을 건진다.
        json.dump(res, open(out_path, "w"))
        print(f"[{os.environ.get('SIONNA2_GPU')}] {i+1}/{len(tasks)} "
              f"f={t['f_ghz']:.3f}GHz d={t['d_mm']:.4f}mm  mu={rec['mu_dbsm']:.3f} dBsm  {dt:.1f}s",
              flush=True)

    json.dump(res, open(out_path, "w"))


if __name__ == "__main__":
    main()
