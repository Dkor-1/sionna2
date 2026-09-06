# -*- coding: utf-8 -*-
"""
outdoor_recover_0907.py — **실외에서 날개 박자가 돌아오나** — 팔 넷 × 앙각 여섯 전수
==========================================================================================
왜 있나 — 앞 원장(outputs/outdoor_order_0907.json)이 팔 하나·앙각 셋만 봤고,
그 위에 세운 설명 셋이 **전수로 보니 틀렸다**(2026-09-07).

    ⛔① 「정지 성분 노치가 박자를 되찾는 데 한몫한다」 — **아니다.**
       노치는 |f| ≤ 100 Hz 를 지우는데, 빗살 잣대의 대역은 0.35·f_tip 에서 **시작**한다.
       그 값이 앙각마다 115~445 Hz 라 **겹치는 칸이 하나도 없다.**
       ⇒ 「메우고 → 뺀다」 와 「빼고 → 메운다」 가 갈린 것은 노치의 효과가 아니라,
         노치가 깊은 골을 얕게 만들어 «|E| < 중앙값×0.1» 규칙이 그 자세를 **못 찾게** 된 것이다.
    ⛔② 「꺼진 자세를 메우면 돌아온다」 — 팔 넷·앙각 여섯에서 **안 선다.**
    ⛔③ 「el −60° 는 절반만 돌아온다」 — **아니다.** 봉우리는 다 돌아오고 바닥만 남는다.
       그 잔차는 «꺼진» 자세가 아니라 **밝은** 자세 몇 개에 몰려 있다.

무엇을 재나 — 잣대는 빗살 하모닉 SNR (⛔ρ 로 재지 않는다)
    칸마다: 자유공간 · 실외 · 노치 · 메움 · 메움→노치 · 노치→메움
    그리고 노치가 잣대의 대역과 겹치는지(band_lo_hz 대 노치 문턱)
    그리고 el −60 류의 «안 돌아오는» 칸에서 잔차가 어디에 몰리는지

⛔판정하지 않는다 — 수를 내고 문장은 사람이 쓴다(주장 게이트 ⓑ).

실행
    cd /workspace/sionna
    CUDA_VISIBLE_DEVICES="" PYTHONPATH=src:benchmark /workspace/.venvs/py312/bin/python benchmark/outdoor_recover_0907.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "benchmark"))
OUT = os.path.join(ROOT, "outputs", "outdoor_recover_0907.json")
SHD = os.path.join(ROOT, "outputs", "elev_sweep_shards")

from clutter_parts_ladder_0824 import FCUT, cs_eca                     # noqa: E402
import comb_snr as CS                                                  # noqa: E402

ARMS = ["R0D0E0F1", "R1D0E0F1", "R0D1E1F1", "R1D1E1F1"]
ELS = [0.0, -15.0, -30.0, -45.0, -60.0, -75.0]
PRF, DIP = 19700.0, 0.1
MESH = "mfixbatteryi5_blperairframe"


def load(arm: str, el: float, env: bool):
    tag = "envoutdoor01_" if env else ""
    import glob                                                        # noqa: PLC0415
    fs = sorted(glob.glob(
        f"{SHD}/sionna_p4000000000_sw{arm}_r15_n8192_{tag}{MESH}_d2_el{el:+g}_*.npz"))
    if not fs:
        return None
    E, I = [], []
    for f in fs:
        z = np.load(f)
        E.append(z["E"])
        I.append(z["idx"])
    o = np.argsort(np.concatenate(I))
    return np.concatenate(E)[o]


def fill(E, thr=DIP, bright=None):
    """꺼진 자세(+선택적으로 **밝은** 자세)를 이웃값으로 메운다."""
    a = np.abs(E)
    med = float(np.median(a))
    bad = set(np.where(a / med < thr)[0].tolist())
    if bright is not None:
        bad |= set(np.where(a / med > bright)[0].tolist())
    bad = np.array(sorted(bad), int)
    if not bad.size:
        return E, 0
    good = np.setdiff1d(np.arange(E.size), bad)
    R = E.copy()
    R[bad] = (np.interp(bad, good, E[good].real)
              + 1j * np.interp(bad, good, E[good].imag))
    return R, int(bad.size)


def snr(E, el, nm):
    v = CS.comb_snr(np.asarray(E), PRF, el, arm=nm)
    return None if v is None else round(float(v), 2)


def band_lo(el, nm):
    """빗살 잣대의 대역이 어디서 시작하나 [Hz] — 노치와 겹치는지 보려고."""
    try:
        import elevation_sweep_md as S                                 # noqa: PLC0415
        return round(0.35 * float(S.f_tip_at(el, nm)), 1)
    except Exception:                                                  # noqa: BLE001
        return None


def main() -> int:
    cells, notch_same, recovered, broken = {}, 0, 0, 0
    for arm in ARMS:
        for el in ELS:
            F, O = load(arm, el, False), load(arm, el, True)
            if F is None or O is None or F.size != O.size:
                continue
            nm = f"sionna_p4000000000_sw{arm}_r15_n8192_envoutdoor01_{MESH}_d2"
            o_fill, n_fill = fill(O)
            o_notch = cs_eca(O)
            _, n_after = fill(o_notch)
            c = {
                "arm": arm, "el_deg": el, "n_poses": int(O.size),
                "band_lo_hz": band_lo(el, nm), "notch_cut_hz": float(FCUT),
                "n_dips": n_fill, "n_dips_after_notch": n_after,
                "comb_free_db": snr(F, el, nm), "comb_raw_db": snr(O, el, nm),
                "comb_notch_db": snr(o_notch, el, nm),
                "comb_fill_db": snr(o_fill, el, nm),
                "comb_fill_then_notch_db": snr(cs_eca(o_fill), el, nm),
                "comb_notch_then_fill_db": snr(fill(o_notch)[0], el, nm),
            }
            #: ① 노치가 값을 바꾸나
            if c["comb_raw_db"] is not None and c["comb_notch_db"] is not None:
                c["notch_delta_db"] = round(c["comb_notch_db"] - c["comb_raw_db"], 3)
                if abs(c["notch_delta_db"]) < 0.05:
                    notch_same += 1
            #: ② 무너졌나 · 돌아왔나 (자유공간 대비)
            if c["comb_free_db"] is not None and c["comb_raw_db"] is not None:
                c["drop_db"] = round(c["comb_raw_db"] - c["comb_free_db"], 2)
                c["is_broken"] = bool(c["drop_db"] <= -10.0)
                if c["is_broken"]:
                    broken += 1
                    c["recover_gap_db"] = round(c["comb_fill_db"] - c["comb_free_db"], 2)
                    c["is_recovered"] = bool(abs(c["recover_gap_db"]) <= 3.0)
                    recovered += int(c["is_recovered"])
                    #: ③ 안 돌아오면 — 잔차가 어디 몰리나, 밝은 자세를 함께 메우면?
                    if not c["is_recovered"]:
                        #: ⚠**평균을 먼저 뺀다.** 실외 기록은 지면이 만든 정지 성분이
                        #  압도해서(자세 평균이 변동분의 수백 배), 그대로 빼면 잔차가
                        #  그 상수 하나로 채워져 «어느 자세에 몰렸나» 가 안 보인다.
                        d = np.abs((o_fill - o_fill.mean()) - (F - F.mean()))
                        k = np.argsort(d)[::-1][:10]
                        c["residual_top10_share_pct"] = round(
                            100 * float(np.sum(d[k] ** 2) / max(np.sum(d ** 2), 1e-300)), 1)
                        c["residual_note_ko"] = "자세 평균을 뺀 뒤의 잔차다 — 안 빼면 지면의 상수가 다 먹는다"
                        a = np.abs(O) / float(np.median(np.abs(O)))
                        c["top10_pose_idx"] = [int(x) for x in sorted(k)]
                        c["top10_abs_over_median"] = [round(float(a[x]), 3) for x in sorted(k)]
                        o2, n2 = fill(O, bright=1.05)
                        c["comb_fill_with_bright_db"] = snr(o2, el, nm)
                        c["n_filled_with_bright"] = n2
            cells[f"{arm}/el{el:+.0f}"] = c

    doc = {"_meta": {
        "generator": "benchmark/outdoor_recover_0907.py",
        "question_ko": "실외에서 날개 박자가 돌아오나 — 팔 넷 × 앙각 여섯 전수",
        "metric_ko": "빗살 하모닉 SNR [dB]. ⛔ρ 로 재지 않는다(docs/RHO_IS_SMOOTHNESS_0902.md)",
        "broken_rule_ko": "실외가 자유공간보다 10 dB 넘게 낮으면 «무너졌다»",
        "recover_rule_ko": "메운 뒤 자유공간과 3 dB 안이면 «돌아왔다»",
        "dip_rule_ko": f"꺼진 자세 = |E| < 중앙값 × {DIP}",
        "notch_ko": f"정지 성분 노치는 |f| ≤ {FCUT:g} Hz 를 지운다. band_lo_hz 와 견주면"
                    " 겹치는지 알 수 있다",
        "caution_ko": "⛔이 원장은 «지면이 박자를 부순다» 를 말하지 않는다. 그리고 이 값은 σ 가 아니다",
    }, "summary": {
        "n_cells": len(cells), "n_broken": broken, "n_recovered": recovered,
        "n_notch_changed_nothing": notch_same,
    }, "cells": cells}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)

    print(f"칸 {len(cells)} → {OUT}\n")
    print(f"  ① 노치가 값을 0.05 dB 도 안 바꾼 칸: {notch_same} / "
          f"{sum(1 for c in cells.values() if 'notch_delta_db' in c)}")
    print(f"  ② 무너진 칸 {broken} · 그중 메워서 돌아온 칸 {recovered}\n")
    print("  팔          앙각   자유공간   실외   메움   차     돌아옴")
    for k, c in cells.items():
        if not c.get("is_broken"):
            continue
        print(f"  {c['arm']} {c['el_deg']:+6.0f}° {c['comb_free_db']:8.1f}"
              f" {c['comb_raw_db']:6.1f} {c['comb_fill_db']:6.1f}"
              f" {c['recover_gap_db']:+7.1f}   {'✅' if c['is_recovered'] else '⛔'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
