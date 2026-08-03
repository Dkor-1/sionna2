# -*- coding: utf-8 -*-
"""멀티스태틱 Δσ(β) 재생성 워커 — 생산자 `multistatic_check` 를 (드론×밴드) 한 칸씩 부른다."""
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drone", required=True)
    ap.add_argument("--band", required=True, choices=["lte", "nr", "wifi"])
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    import experiment_freespace_sigma as X
    band = X._BAND_BY_STD[a.band]
    t0 = time.time()
    r = X.multistatic_check([a.drone], [band], beta_grid=(0, 15, 30, 45, 60, 75, 90),
                            n_az=24, el_deg=-2.0, div=X.DIV, backend="direct", verbose=True)
    tmp = a.out + ".tmp"
    json.dump(dict(drone=a.drone, band=band[0], rows=r[a.drone][band[0]],
                   runtime_s=round(time.time() - t0, 1)), open(tmp, "w"))
    os.replace(tmp, a.out)
    print(f"[{a.drone}/{a.band}] DONE {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
