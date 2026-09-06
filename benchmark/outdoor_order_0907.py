# -*- coding: utf-8 -*-
"""
outdoor_order_0907.py — **실외에서 날개 박자를 되찾을 수 있나, 그리고 순서가 결과를 바꾸나**
==========================================================================================
물음
    리포트 12 절 2 가 ⚠⑥ 으로 열어 둔 것: 「실외에서 정지 클러터 제거가 박자를 되찾는지는
    아직 모른다 — 낙차 자세를 어떻게 처리하느냐로 값이 흔들린다.」
    그 «어떻게 처리하느냐» 를 **다섯 갈래로 못 박고** 정본 잣대로 잰다.

무엇을 재나 — 잣대는 **빗살 하모닉 SNR** 이다
    ⛔ρ(포락 자기상관)로 재지 않는다 — ρ 는 «리듬» 이 아니라 «매끄러움» 을 잰다
      (docs/RHO_IS_SMOOTHNESS_0902.md). 직선·계단·붉은잡음이 전부 «박자» 칸에 든다.

    갈래 다섯 (같은 실외 기록에 처리만 다르게)
      raw              그대로
      notch            정지 성분만 뺀다 (0 Hz 부근 직각 노치, clutter_parts_ladder_0824.cs_eca)
      fill             꺼지는 자세만 이웃값으로 메운다 (|E| < 중앙값 × 0.1)
      fill_then_notch  메우고 → 뺀다
      notch_then_fill  빼고 → 메운다      ⭐이 둘이 갈리는 것이 이 원장의 알맹이다

⛔판정하지 않는다 — 수를 내고 문장은 사람이 쓴다(주장 게이트 ⓑ).
⛔이 원장은 «지면이 박자를 부순다» 를 말하지 않는다. 부순 것이 무엇인지는 자세를 세어
  따로 물어야 한다.

실행
    cd /workspace/sionna
    CUDA_VISIBLE_DEVICES="" PYTHONPATH=src:benchmark /workspace/.venvs/py312/bin/python benchmark/outdoor_order_0907.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "benchmark"))
OUT = os.path.join(ROOT, "outputs", "outdoor_order_0907.json")

from clutter_parts_ladder_0824 import cs_eca                          # noqa: E402
import comb_snr as CS                                                 # noqa: E402

ELS = [0.0, -30.0, -60.0]
PRF = 19700.0
DIP_RULE = 0.1            # |E| < 중앙값 × 이 값 이면 «꺼진 자세» (outdoor_scene_0901 과 같은 규약)


def arm(el: float, env: bool) -> str:
    """리포트 12 와 **같은 팔 이름**을 만든다 — 갈리면 두 원장이 다른 것을 말하게 된다."""
    import build_vol12_figs as B                                      # noqa: PLC0415
    return B.arm(el, env)


def fill_dips(E: np.ndarray):
    """꺼진 자세를 이웃값으로 메운다. 반환 (메운 배열, 메운 자세 수).

    ⚠물리를 고치는 것이 아니라 «그 자세들이 없었다면 무엇이 보이나» 를 묻는 조작이다.
    """
    a = np.abs(E)
    med = float(np.median(a))
    bad = np.where(a / med < DIP_RULE)[0] if med > 0 else np.zeros(0, int)
    if not bad.size:
        return E, 0
    good = np.setdiff1d(np.arange(E.size), bad)
    R = E.copy()
    R[bad] = (np.interp(bad, good, E[good].real)
              + 1j * np.interp(bad, good, E[good].imag))
    return R, int(bad.size)


def snr(E: np.ndarray, el: float, nm: str):
    v = CS.comb_snr(np.asarray(E), PRF, el, arm=nm)
    return None if v is None else round(float(v), 2)


def main() -> int:
    Z = np.load(os.path.join(ROOT, "outputs", "elevation_sweep_md.npz"))
    cells = {}
    for el in ELS:
        nf, no = arm(el, False), arm(el, True)
        if nf not in Z or no not in Z:
            continue
        F = np.asarray(Z[nf])
        O = np.asarray(Z[no])
        o_fill, n_fill = fill_dips(O)
        o_notch = cs_eca(O)
        o_nf, n_nf = fill_dips(o_notch)          # 빼고 → 메우기
        cells[f"el{el:+.0f}"] = {
            "el_deg": el,
            "n_poses": int(O.size),
            "n_dips_raw": n_fill,                # 실외 기록에서 꺼진 자세 수
            "n_dips_after_notch": n_nf,          # ⭐정지 성분을 먼저 빼면 몇 개가 걸리나
            "comb_free_db": snr(F, el, nf),
            "comb_raw_db": snr(O, el, no),
            "comb_notch_db": snr(o_notch, el, no),
            "comb_fill_db": snr(o_fill, el, no),
            "comb_fill_then_notch_db": snr(cs_eca(o_fill), el, no),
            "comb_notch_then_fill_db": snr(o_nf, el, no),
        }
    doc = {
        "_meta": {
            "generator": "benchmark/outdoor_order_0907.py",
            "question_ko": "실외에서 날개 박자를 되찾을 수 있나, 그리고 두 조작의 순서가 결과를 바꾸나",
            "metric_ko": "빗살 하모닉 SNR [dB] — 날개 박자의 조화선이 주변 바닥보다 몇 dB 위에 서는가."
                         " ⛔ρ(포락 자기상관)로 재지 않는다(docs/RHO_IS_SMOOTHNESS_0902.md)",
            "dip_rule_ko": f"꺼진 자세 = |E| < 중앙값 × {DIP_RULE}"
                           " (benchmark/outdoor_scene_0901.py 와 같은 규약)",
            "arm_ko": "스톡 엔진 ①다끔(R0D0E0F1) · matrice4e · 15 m · 자세 8,192 · 광선 4e9 · 깊이 2."
                      " 실외 팔은 지면 120×120 m 콘크리트 + 건물 넷 + 금속 기둥 둘 · 드론 고도 20 m",
            "answers_ko": "리포트 12 절 2 의 ⚠⑥ 「실외에서 정지 클러터 제거가 박자를 되찾는지는"
                          " 아직 모른다」 에 답한다",
            "caution_ko": "⛔이 원장은 «지면이 박자를 부순다» 를 말하지 않는다 — 무엇이 부쉈는지는"
                          " 자세를 세어 따로 물어야 한다. 그리고 이 값은 σ 가 아니다",
        },
        "cells": cells,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)

    print(f"칸 {len(cells)} → {OUT}\n")
    hdr = (f"{'앙각':>6}{'자유공간':>10}{'실외':>8}{'노치':>8}{'메움':>8}"
           f"{'메움→노치':>12}{'노치→메움':>12}{'꺼진 자세':>11}")
    print(hdr); print("-" * len(hdr))
    for k, c in cells.items():
        g = lambda x: "  —  " if c[x] is None else f"{c[x]:6.1f}"          # noqa: E731
        print(f"{k:>6}{g('comb_free_db'):>10}{g('comb_raw_db'):>8}{g('comb_notch_db'):>8}"
              f"{g('comb_fill_db'):>8}{g('comb_fill_then_notch_db'):>12}"
              f"{g('comb_notch_then_fill_db'):>12}"
              f"{c['n_dips_raw']:>7}→{c['n_dips_after_notch']:<4}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
