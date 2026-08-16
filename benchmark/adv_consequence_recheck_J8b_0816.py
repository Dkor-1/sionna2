# -*- coding: utf-8 -*-
"""
adv_consequence_recheck_J8b_0816.py — 앞 라운드의 «코사인 0.839» 가 자[尺] 탓인가 각도 탓인가
==============================================================================================

앞 라운드는 mini5pro·el −30·**전력** 코사인으로 0.839 를 얻고 그것을 발표 일치도
(크기 코사인 0.955/0.760, el −15)와 나란히 놨다. 자도 다르고 앙각도 다르다.
여기서는 **같은 신호쌍**에 두 자를 다 대고, 두 앙각에서 각각 재서 원인을 가른다.

규약: CPU 전용 · 소스 무변경 · 순수 PO. 조각 산출 → `outputs/_J8b_ruler_split_0816.json`.
"""
from __future__ import annotations

import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import adv_consequence_recheck_0816 as R                                   # noqa: E402
from adv_consequence_recheck_J8_0816 import shape_mag, shape_pow           # noqa: E402
from drones import DRONES                                                   # noqa: E402


def main():
    t0 = time.time()
    out = {}
    for key in ("mini5pro", "matrice4e"):
        spec = DRONES[key]
        v_tip = math.pi * (spec.prop_dia_mm / 1000.0) * spec.hover_rpm / 60.0
        per_el = {}
        for el, n in ((-15.0, 8192), (-30.0, 8192)):
            f_tip = 2.0 * v_tip / R.LAM * math.cos(math.radians(el))
            ser = {}
            for law in R.LAWS:
                res, _ = R.slowtime(spec, law, [el], n_poses=n)
                ser[law] = res[el]["E"]
            per_el[f"{el:+.0f}"] = {
                law: dict(
                    cosine_in_ftip_magnitude=round(float(
                        shape_mag(ser["legacy"], f_tip) @ shape_mag(ser[law], f_tip)), 4),
                    cosine_fullband_power=round(float(
                        shape_pow(ser["legacy"]) @ shape_pow(ser[law])), 4))
                for law in R.LAWS[1:]}
            print(f"  J8b {key} el{el:+.0f} {time.time()-t0:.1f}s", flush=True)
        out[key] = dict(n=8192, per_el=per_el)
    res = dict(rows=out,
               published_ruler="크기 코사인, |f|≤f_tip (report07 verdict.cosine_in_ftip)",
               reading_ko="같은 신호쌍에 두 자를 대면 전력 코사인이 늘 더 낮게 나온다. "
                          "앞 라운드의 0.839 는 자와 앙각이 함께 만든 값이다.",
               elapsed_s=round(time.time() - t0, 1))
    json.dump(res, open(os.path.join(ROOT, "outputs", "_J8b_ruler_split_0816.json"),
                        "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
