# -*- coding: utf-8 -*-
"""run_bridge_window.py — 기동 브리지 **생산 러너** (px4_bridge API 의 CLI 껍데기).

    PYTHONPATH=src:benchmark python benchmark/run_bridge_window.py \
        --engine ours --mesh phantom4 --grade 2 --pulses 5000 [--ptd]
출력: outputs/px4_bridge/<engine>_<mesh>_g<grade>_w0.npz (s, idx, R, meta)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, HERE)
import px4_bridge as PB                                                # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--engine", choices=("ours", "sionna"), required=True)
ap.add_argument("--mesh", choices=("phantom4", "matrice4e"), required=True)
ap.add_argument("--grade", type=int, default=2)
ap.add_argument("--pulses", type=int, default=5000)
ap.add_argument("--ptd", action="store_true")
ap.add_argument("--spp", type=int, default=0, help="sionna 전용. 0=규칙값")
a = ap.parse_args()

win = PB.load_window(a.grade, n_pulses=a.pulses)
poser = PB.SeniorMeshPoser() if a.mesh == "phantom4" else PB.OursPoser()
t0 = time.time()
if a.engine == "ours":
    out = PB.run_ours(poser, win, ptd=a.ptd)
else:
    kw = dict(max_pulses=a.pulses)
    if a.spp:
        kw["spp"] = a.spp
    out = PB.run_sionna_window(poser, win, **kw)
sec = time.time() - t0

d = os.path.join(ROOT, "outputs", "px4_bridge")
os.makedirs(d, exist_ok=True)
tag = f"{a.engine}{'_ptd' if a.ptd else ''}_{a.mesh}_g{a.grade}_w0"
np.savez_compressed(os.path.join(d, tag + ".npz"),
                    s=out["s"], idx=out.get("idx", np.arange(len(out["s"]))),
                    R=out.get("R", np.zeros(0)),
                    meta=json.dumps({**{k: v for k, v in out.get("meta", {}).items()
                                        if isinstance(v, (int, float, str, bool))},
                                     "seconds": round(sec, 1), "pulses": a.pulses}))
print(f"✅ {tag}  {len(out['s'])} 펄스 · {sec/60:.1f} 분")
