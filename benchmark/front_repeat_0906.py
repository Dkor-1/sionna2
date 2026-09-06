# -*- coding: utf-8 -*-
"""
front_repeat_0906.py — **정면에서 기록된 흔들림이 무엇에서 오나**
==========================================================================================
물음
    방위 0°·고도 0° 에서 경로 목록에 **값이 완전히 같은 줄**이 여러 개 들어 있다.
    그 줄들을 한 번씩만 세면(`E_dedup`) 남는 신호는 어떻게 되나.

무엇을 재나 — 자세 8,192 개를 이어 붙여
    · `|E|` 와 `|E_dedup|` 각각의 **자세 간 폭**[dB] — 얼마나 흔들리나
    · `n_dup` 분포 — 자세마다 몇 줄이 지워지나
    · `|E|` 와 배수 `|E|/|E_dedup|` 의 상관 — 흔들림이 **줄 수**로 설명되나
    · 0.2° 벗어난 자리에서 같은 것들

⛔판정하지 않는다 — 수를 내고 문장은 사람이 쓴다(주장 게이트 ⓑ).
⛔「솔버가 틀렸다」로 적지 않는다. 관측은 **「같은 값의 줄이 여러 번 적혀 있다」** 까지다.

실행
    cd /workspace/sionna
    CUDA_VISIBLE_DEVICES="" /workspace/.venvs/py312/bin/python benchmark/front_repeat_0906.py
"""
from __future__ import annotations

import collections
import glob
import json
import os

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SHD = os.path.join(ROOT, "outputs", "elev_sweep_shards")
OUT = os.path.join(ROOT, "outputs", "front_repeat_0906.json")
MESH = "mfixbatteryi5_blperairframe"
ARMS = [("R0D0E0F1", "확산만 켠 팔"), ("R0D1E1F1", "회절·모서리회절도 켠 팔")]
CELLS = [("az0", "방위 0°"), ("az0.2", "방위 0.2° 벗어남")]


def series(arm: str, tag: str):
    """샤드를 `idx` 로 이어 붙여 자세 순서의 시간열을 만든다.

    ⚠샤드는 한 칸씩 엇갈려 채운다(간격 2). 파일 순서로 이으면 자세가 뒤섞인다.
    """
    i, e, d, n = [], [], [], []
    for f in sorted(glob.glob(
            f"{SHD}/sionna_p4000000000_sw{arm}_r15_n8192_{tag}_{MESH}_d2_el+0_*.npz")):
        try:
            z = np.load(f)
        except Exception:                                          # noqa: BLE001
            continue
        if "E_dedup" not in z.files:
            continue
        i.append(z["idx"])
        e.append(z["E"])
        d.append(z["E_dedup"])
        n.append(z["n_dup"])
    if not i:
        return None
    o = np.argsort(np.concatenate(i))
    return (np.concatenate(e)[o], np.concatenate(d)[o], np.concatenate(n)[o])


def span_db(x: np.ndarray) -> float:
    """자세 간 폭 — 최대와 최소의 dB 차. 0 에 가까우면 «평평하다»."""
    a = np.abs(x)
    a = a[a > 0]
    return float(20.0 * np.log10(a.max() / a.min())) if a.size else float("nan")


def measure(arm: str, tag: str):
    s = series(arm, tag)
    if s is None:
        return None
    E, D, nd = s
    a, b = np.abs(E), np.abs(D)
    ok = b > 0
    r = a[ok] / b[ok]
    same = bool(np.array_equal(E, D))
    return {
        "n_poses": int(E.size),
        "recorded_span_db": round(span_db(E), 4),
        "deduped_span_db": round(span_db(D), 4),
        "identical_arrays": same,
        "n_dup_hist": {str(k): int(v) for k, v in sorted(collections.Counter(nd.tolist()).items())},
        "ratio_median": round(float(np.median(r)), 4),
        "ratio_max": round(float(r.max()), 4),
        "share_pct": round(100.0 * float((r > 1.5).mean()), 2),
        #: ⭐흔들림이 «줄 수» 로 설명되나 — 1 에 가까우면 그렇다.
        #  ⚠배수가 상수인 칸(창 밖)에서는 상관이 **정의되지 않는다** — 0 이 아니라 null 이다.
        "corr_absE_vs_ratio": (None if float(r.std()) == 0.0
                               else round(float(np.corrcoef(a[ok], r)[0, 1]), 6)),
        "std_ratio_recorded_over_deduped": round(float(E.std() / D.std()), 3),
    }


def main() -> int:
    doc = {
        "_meta": {
            "generator": "benchmark/front_repeat_0906.py",
            "question_ko": "정면에서 기록된 자세 간 흔들림이 «같은 줄이 여러 번 적힌 것» 으로 설명되나",
            "recorded_span_db_ko": "|E| 의 자세 간 폭 [dB] — 기록 그대로",
            "deduped_span_db_ko": "|E_dedup| 의 자세 간 폭 [dB] — 같은 값의 줄을 한 번씩만 셌을 때",
            "corr_ko": "|E| 와 배수의 상관 — 1 에 가까우면 흔들림이 줄 수로 설명된다",
            "scope_ko": "15 m · 깊이 2 · mfixbatteryi5_blperairframe · 광선 4e9 · 자세 8,192",
            "caution_ko": "⛔«정확히 3 배» 로 적지 마라 — 배수의 최댓값이 3 에 못 닿는다",
        },
        "cells": {},
    }
    for arm, arm_ko in ARMS:
        for tag, tag_ko in CELLS:
            m = measure(arm, tag)
            if m is None:
                continue
            m["arm_ko"] = arm_ko
            m["where_ko"] = tag_ko
            doc["cells"][f"{arm}/{tag}"] = m
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)

    print(f"칸 {len(doc['cells'])} → {OUT}\n")
    for k, v in doc["cells"].items():
        print(f"  {k:22s} 자세 {v['n_poses']}")
        print(f"      기록 그대로 폭 {v['recorded_span_db']:8.4f} dB"
              f" · 되풀이 지운 폭 {v['deduped_span_db']:8.4f} dB"
              f" · 두 배열이 같나 {v['identical_arrays']}")
        _c = v["corr_absE_vs_ratio"]
        print(f"      배수 중앙 {v['ratio_median']:.4f} · 최대 {v['ratio_max']:.4f}"
              f" · 겹친 자세 {v['share_pct']:.2f}%"
              f" · |E|-배수 상관 " + ("정의 안 됨(배수가 상수)" if _c is None else f"{_c:.6f}"))
        print(f"      지워진 줄 수 분포 {v['n_dup_hist']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
