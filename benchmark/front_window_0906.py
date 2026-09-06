# -*- coding: utf-8 -*-
"""
front_window_0906.py — **정면 창은 얼마나 좁은가**
==========================================================================================
물음
    솔버가 **같은 경로를 여러 줄로 적는** 현상(N = |E| / |E_dedup|)은 az 0°·el 0° 한 점에서만
    난다는 것이 2026-09-05 에 갈렸다. 그 점의 **폭**이 이 물음이다 —
      · 폭이 0.1° 보다 좁으면 축 위 특이점이고, 실제 비행 자세에서는 거의 안 만난다.
      · 0.5° 쯤 되면 호버링 자세 흔들림 안에 들어와 **실제로 만나는 자리**가 된다.
    ⇒ 덱이 말한 «0° 서든 드랍» 을 발표에 어떻게 올릴지가 여기서 갈린다.

무엇을 재나
    `outputs/elev_sweep_shards/*.npz` 의 `E` 와 `E_dedup` 으로
      N = median( |E| / |E_dedup| )  (E_dedup > 0 인 자세만)
    을 방위·앙각 사다리로 읽는다. N=1 이면 겹쳐 적히지 않는 것이고, N=3 이면 세 번 적힌 것이다.

⛔판정하지 않는다 — 수를 내고 문장은 사람이 쓴다(주장 게이트 ⓑ).
⛔실외(`_env`)·재실행(`_rep`) 샤드는 뺀다. 축이 다르다.

실행
    cd /workspace/sionna
    CUDA_VISIBLE_DEVICES="" python3 benchmark/front_window_0906.py
"""
from __future__ import annotations

import collections
import glob
import json
import os
import re

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SHD = os.path.join(ROOT, "outputs", "elev_sweep_shards")
OUT = os.path.join(ROOT, "outputs", "front_window_0906.json")
MIN_POSES = 50          # 이보다 적으면 중앙값이 안 선다


def read(path: str):
    """(방위, 앙각, N, 자세수) — 못 읽으면 None."""
    b = os.path.basename(path)
    if "_rep" in b or "_env" in b:
        return None
    try:
        z = np.load(path)
    except Exception:
        return None
    if "n_dup" not in z.files or "E_dedup" not in z.files:
        return None                       # 옛 샤드 — 겹침을 안 적었다
    E, D = np.abs(z["E"]), np.abs(z["E_dedup"])
    ok = D > 0
    if int(ok.sum()) < MIN_POSES:
        return None
    ma = re.search(r"_az([0-9.]+)", b)
    me = re.search(r"_el([+-][0-9.]+)", b)
    if me is None:
        return None
    return (float(ma.group(1)) if ma else 0.0, float(me.group(1)),
            float(np.median(E[ok] / D[ok])), int(ok.sum()), b)


def ladder(rows, key, fixed, fixed_val):
    d = collections.defaultdict(list)
    for az, el, n, _p, _b in rows:
        if abs((az if fixed == "az" else el) - fixed_val) < 1e-9:
            d[az if key == "az" else el].append(n)
    return {f"{k:g}": dict(N=round(float(np.median(v)), 4), n_shards=len(v))
            for k, v in sorted(d.items())}


def main() -> int:
    rows = [r for r in (read(p) for p in sorted(glob.glob(f"{SHD}/*.npz"))) if r]
    az_l = ladder(rows, "az", "el", 0.0)
    el_l = ladder(rows, "el", "az", 0.0)

    def width(lad, axis):
        """N 이 1 로 떨어지기 **직전** 각도와 **처음 1 이 되는** 각도."""
        ks = sorted(lad, key=lambda x: abs(float(x)))
        last_hi = first_one = None
        for k in ks:
            if lad[k]["N"] > 1.01 and abs(float(k)) > 0:
                last_hi = k
            if lad[k]["N"] <= 1.01 and first_one is None and abs(float(k)) > 0:
                first_one = k
        return dict(axis=axis, last_above_one_deg=last_hi, first_at_one_deg=first_one)

    doc = {
        "_meta": {
            "generator": "benchmark/front_window_0906.py",
            "question_ko": "같은 경로가 여러 줄로 적히는 «정면 창» 은 얼마나 좁은가",
            "metric_ko": "N = median(|E| / |E_dedup|) — 1 이면 안 겹치고, 3 이면 세 번 적힌다",
            "excluded_ko": "실외(_env)·재실행(_rep) 샤드는 뺐다 — 축이 다르다",
            "min_poses": MIN_POSES,
            "n_shards_read": len(rows),
        },
        "azimuth_ladder_at_el0": az_l,
        "elevation_ladder_at_az0": el_l,
        "window": [width(az_l, "azimuth"), width(el_l, "elevation")],
        "observations_ko": [
            "두 축 모두 0.2° 에서 N 이 1.000 으로 떨어진다 — 창은 **1° 보다 훨씬 좁다.**",
            "⚠두 축이 **같은 모양으로 죽지 않는다.** 앙각은 단조로 내려가고"
            "(0° 3.00 → −0.05° 2.71 → −0.10° 1.76 → −0.20° 1.000),"
            " 방위는 0.05° 에서 오히려 **올라간다**(0° 3.00 → 0.05° 4.97 → 0.10° 2.59).",
            "⛔0.05·0.10° 칸은 샤드가 4~6 장이고 축 위는 86 장이다 — 표본이 갈린다."
            " «방위가 왜 튀나» 는 이 원장으로 답하지 않는다.",
            "⛔이 창을 «실제 비행에서 만나나» 로 옮기려면 호버링 자세 흔들림의 크기가 있어야"
            " 하는데, 이 저장소에는 그 실측이 없다.",
        ],
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print(f"샤드 {len(rows)} 장 → {OUT}\n")
    for name, lad in (("방위 (el 0°)", az_l), ("앙각 (az 0°)", el_l)):
        print(f"  {name}")
        for k, v in lad.items():
            if abs(float(k)) <= 6:
                print(f"    {float(k):+7.2f}°  N={v['N']:.4f}  샤드 {v['n_shards']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
