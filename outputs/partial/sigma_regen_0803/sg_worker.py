# -*- coding: utf-8 -*-
"""σ 격자 재생성 워커 — (드론 × 밴드) 한 칸을 계산해 shard JSON 으로 쓴다.

정확한 재현이 목적이므로 **생산자 함수를 그대로 부른다**(`experiment_freespace_sigma`).
el 을 한 줄씩 잘라 `_sigma_grid_one` 을 부르는데, 3° 각도평활이 az 행 단위로 독립이라
9줄을 한 번에 부른 것과 **비트 단위로 같다** — 대신 el 한 줄마다 중간저장이 남는다.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

ROOT = "/home/yunjung/workspace/sionna2"
for p in (os.path.join(ROOT, "src"), os.path.join(ROOT, "benchmark")):
    if p not in sys.path:
        sys.path.insert(0, p)

import numpy as np  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drone", required=True)
    ap.add_argument("--band", required=True, choices=["lte", "nr", "wifi"])
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    import experiment_freespace_sigma as X          # gpu.pick 은 rcs_sbr import 시 걸린다
    from channel import _mesh_fp

    bname, fc, bw = X._BAND_BY_STD[a.band]
    az, el = X.AZ_GRID, X.EL_GRID
    t0 = time.time()
    raw, sm = [], []
    for i, e in enumerate(el):
        g = X._sigma_grid_one(a.drone, fc, bw, az, np.array([float(e)]),
                              n_f=X.N_F, div=X.DIV, smooth_deg=X.SMOOTH_DEG,
                              backend="direct", verbose=False)
        raw.append(np.asarray(g["sigma_m2"], float)[0])
        sm.append(np.asarray(g["sigma_smooth_m2"], float)[0])
        print(f"[{a.drone}/{a.band}] el={e:+6.1f}  "
              f"mean={10*np.log10(np.mean(sm[-1])):+7.2f} dBsm  "
              f"({time.time()-t0:.0f}s, {i+1}/{len(el)})", flush=True)
        # 중간저장 — 죽어도 여기까지는 남는다
        _dump(a.out + ".partial", a, bname, fc, bw, az, el[:i + 1], raw, sm, _mesh_fp(a.drone),
              time.time() - t0, done=False)
    _dump(a.out, a, bname, fc, bw, az, el, raw, sm, _mesh_fp(a.drone),
          time.time() - t0, done=True)
    try:
        os.remove(a.out + ".partial")
    except OSError:
        pass
    print(f"[{a.drone}/{a.band}] DONE {time.time()-t0:.0f}s → {a.out}", flush=True)


def _dump(path, a, bname, fc, bw, az, el, raw, sm, fp, sec, done):
    import experiment_freespace_sigma as X
    sm_a = np.asarray(sm, float)
    node = dict(
        el_deg=np.asarray(el, float).tolist(), az_deg=np.asarray(az, float).tolist(),
        fc_hz=float(fc), bw_hz=float(bw),
        sigma_dbsm=[[X._dbsm(v) for v in row] for row in raw],
        sigma_smooth_dbsm=[[X._dbsm(v) for v in row] for row in sm],
        stats=X._stats(sm_a),
        by_el={f"{e:+.1f}": X._stats(sm_a[i]) for i, e in enumerate(np.asarray(el, float))})
    obj = dict(drone=a.drone, band=bname, mesh_fp=fp, runtime_s=round(sec, 1),
               done=bool(done), node=node)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f)
    os.replace(tmp, path)


if __name__ == "__main__":
    main()
