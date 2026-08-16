# -*- coding: utf-8 -*-
"""
capdiag_groups_0816.py — ③ 이 «끝단만» 손댔는지 **그룹별 지문**으로 확인
=========================================================================
smooth_iters 4 → 0 을 걸었을 때 프레임의 어느 그룹이 움직이는지 본다.
셸(body) 말고 다른 그룹이 움직이면 그건 `frame_fit_scale` 이 따라 움직였다는 뜻이다
(셸 bbox 가 바뀌면 높이 강제 배율이 미세하게 재계산된다) — 그 경우 숫자로 남긴다.

산출: outputs/_capdiag_groups_0816.json
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import warnings

import numpy as np

warnings.filterwarnings("ignore")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import drone_cad as dc                                     # noqa: E402
import drones as dr                                        # noqa: E402

SHELL_KEYS = ["matrice4e", "mavic4pro", "mini5pro", "phantom4", "phantom3", "mini2"]


def group_fp(m):
    V, G = np.asarray(m.v, np.float32), np.asarray(m.g, object)
    F = np.asarray(m.f, np.int32)
    out = {}
    for g in sorted(set(G.tolist())):
        sel = G == g
        idx = np.unique(F[sel])
        out[g] = hashlib.sha256(V[idx].tobytes()).hexdigest()[:12]
    return out


def main():
    res = {}
    for k in SHELL_KEYS:
        dc._SHELL_SHAPE[k]["smooth_iters"] = 4
    dr._FIT_CACHE.clear()
    before = {k: group_fp(dr.build_frame(dr.DRONES[k])) for k in SHELL_KEYS}
    fit_b = {k: dr.frame_fit_scale(dr.DRONES[k]) for k in SHELL_KEYS}
    for k in SHELL_KEYS:
        dc._SHELL_SHAPE[k]["smooth_iters"] = 0
    dr._FIT_CACHE.clear()
    after = {k: group_fp(dr.build_frame(dr.DRONES[k])) for k in SHELL_KEYS}
    fit_a = {k: dr.frame_fit_scale(dr.DRONES[k]) for k in SHELL_KEYS}
    for k in SHELL_KEYS:
        moved = sorted(g for g in before[k] if before[k][g] != after[k].get(g))
        same = sorted(g for g in before[k] if before[k][g] == after[k].get(g))
        res[k] = dict(moved_groups=moved, unchanged_groups=same,
                      fit_scale=[[round(x, 8) for x in fit_b[k]], [round(x, 8) for x in fit_a[k]]],
                      fit_scale_changed=bool(fit_b[k] != fit_a[k]))
    out = os.path.join(ROOT, "outputs", "_capdiag_groups_0816.json")
    json.dump(res, open(out, "w"), ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
