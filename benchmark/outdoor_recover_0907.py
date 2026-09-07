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

⛔⛔**2026-09-07 감사 — 이 원장의 첫 판에는 셋이 빠져 있었다.** 고쳤고, 한계를 여기 적는다.
    ① **자유공간 기준값이 「같은 경로가 여러 줄로 적힌」 판 위에 있었다.** `load()` 는
       `z["E"]` 를 쓰는데, el 0° 자유공간 샤드는 8,192 자세 중 8,191 개가 `E_dedup` 와
       다르다 — 그 판의 **레벨 변동이 거의 다 겹친 줄 수의 변동**이다(폭: E 9.5402 dB
       ↔ E_dedup 0.0063 dB). 겹침을 걷으면 el 0° 자유공간이 3.42 → **51.69 dB** 로 뛰고
       R0D0E0F1·R1D0E0F1 두 칸의 「무너짐」이 False → **True** 로 뒤집힌다(n_broken 16 → 18).
       ⇒ `has_dedup_*` · `comb_free_dedup_db` · `is_broken_if_dedup` 을 칸마다 적는다.
       ⚠**실외 짝에는 `E_dedup` 가 없다**(옛 세대 샤드). 그래서 한쪽만 걷은 수이고,
         el 0° 열은 **두 판의 세대가 다르다** — 그 열의 drop_db 를 인용하지 않는다.
    ② **「돌아온다」가 원장에 없던 자유 파라미터 하나에 매달려 있었다.** 밝은 자세 문턱
       1.05 는 `_meta` 에 없었다. 흔들어 보면 R1D0E0F1/el−60 은 1.05 에서 67 자세를 메워
       36.03 dB(차 −0.98, 돌아옴)인데 **1.06 에서 66 자세 · 19.70 dB(차 −17.31, 탈락)** —
       자세 **하나**가 16.33 dB 를 가른다. R0D0E0F1/el−60 도 1.10↔1.15 에서 갈린다.
       ⇒ 문턱을 `_meta` 에 적고 `bright_ladder` 로 사다리를 남긴다.
       ⛔이 저장소 규약: 자유 파라미터를 흔들어 결론이 바뀌면 그 결론은 머리기사로 안 쓴다.
    ③ **«보임» 문턱(치환 널)을 안 걸었다.** `comb_snr.py:204` 에 `comb_visible` 이 이미
       있는데 맨 `comb_snr` 만 불렀다. 널을 걸면 **실외 24 칸 중 22 칸이 널 아래**다 —
       그 칸의 실외값은 값이 아니라 **바닥**이고, 따라서 `drop_db` 는 값이 아니라 **하한**이다.
       ⇒ `null_max_*` · `visible_*` · `drop_is_lower_bound_only` 를 적는다.
       ⚠양 끝(자유공간이 크다 · 메우면 돌아온다)은 널의 여러 배 위라 그대로 선다.
         무너지는 것은 **drop_db 의 크기**와 **「몇 칸」이라는 셈**이다.

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
#: ⭐«밝은 자세» 문턱 — 첫 판은 1.05 하나였고 그것이 `_meta` 에도 없었다.
#  이제 사다리를 통째로 잰다. BRIGHT0 은 옛 판과 견주기 위한 자리다.
BRIGHT0 = 1.05
BRIGHTS = (1.02, 1.03, 1.04, 1.05, 1.06, 1.08, 1.10, 1.15)
MESH = "mfixbatteryi5_blperairframe"


def load(arm: str, el: float, env: bool):
    tag = "envoutdoor01_" if env else ""
    import glob                                                        # noqa: PLC0415
    fs = sorted(glob.glob(
        f"{SHD}/sionna_p4000000000_sw{arm}_r15_n8192_{tag}{MESH}_d2_el{el:+g}_*.npz"))
    if not fs:
        return None, None
    E, I, D = [], [], []
    for f in fs:
        z = np.load(f)
        E.append(z["E"])
        I.append(z["idx"])
        #: ⭐겹침을 걷은 판 — **옛 세대 샤드에는 없다.** 하나라도 없으면 통째로 없는 걸로 본다
        #  (반만 걷은 배열을 만들면 그게 제일 나쁘다).
        D.append(z["E_dedup"] if "E_dedup" in z.files else None)
    o = np.argsort(np.concatenate(I))
    Dc = None if any(d is None for d in D) else np.concatenate(D)[o]
    return np.concatenate(E)[o], Dc


def null_max(E, el, nm, n_null=CS.N_NULL, seed=0):
    """치환 널의 **최댓값** — 시간축을 뒤섞어 주기성을 없앤 판의 잣대값.

    ⭐`comb_snr.py:190-204` 가 `comb_visible` 로 쓰는 바로 그 문턱이다. 그 아래의 값은
    「보인다」고 말할 수 없고, 두 값의 차도 값이 아니라 **하한**이 된다.
    """
    rng = np.random.default_rng(seed)
    E = np.asarray(E)
    vs = [CS.comb_snr(E[rng.permutation(E.size)], PRF, el, arm=nm) for _ in range(n_null)]
    vs = [float(v) for v in vs if v is not None]
    return round(max(vs), 2) if vs else None


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
            F, Fd = load(arm, el, False)
            O, Od = load(arm, el, True)
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
            #: ⓪ ⭐«보임» 문턱 — 치환 널. 이것 없이는 값이 바닥인지 신호인지 모른다.
            c["null_max_free_db"] = null_max(F, el, nm, seed=1)
            c["null_max_out_db"] = null_max(O, el, nm, seed=2)
            for side, val, nul in (("free", c["comb_free_db"], c["null_max_free_db"]),
                                   ("out", c["comb_raw_db"], c["null_max_out_db"])):
                c[f"visible_{side}"] = (None if (val is None or nul is None)
                                        else bool(val > nul))
            #: ⭐한쪽이라도 널 아래면 두 값의 차는 **값이 아니라 하한**이다.
            c["drop_is_lower_bound_only"] = bool(c.get("visible_out") is False
                                                 or c.get("visible_free") is False)

            #: ⓪′ ⭐겹침을 걷은 판이 있나 — 없으면 그 칸의 기준값은 「같은 경로가 여러 줄로
            #  적힌」 판 위의 값일 수 있고, 그것을 모른 채로 쓰면 안 된다.
            c["has_dedup_free"] = Fd is not None
            c["has_dedup_out"] = Od is not None
            if Fd is not None:
                c["comb_free_dedup_db"] = snr(Fd, el, nm)
                c["n_pose_E_ne_Ededup"] = int(np.count_nonzero(np.abs(F) != np.abs(Fd)))
                c["level_span_free_E_db"] = round(float(
                    20 * np.log10(np.abs(F).max() / max(np.abs(F).min(), 1e-300))), 4)
                c["level_span_free_Ededup_db"] = round(float(
                    20 * np.log10(np.abs(Fd).max() / max(np.abs(Fd).min(), 1e-300))), 4)

            #: ① 노치가 값을 바꾸나
            if c["comb_raw_db"] is not None and c["comb_notch_db"] is not None:
                c["notch_delta_db"] = round(c["comb_notch_db"] - c["comb_raw_db"], 3)
                if abs(c["notch_delta_db"]) < 0.05:
                    notch_same += 1
            #: ② 무너졌나 · 돌아왔나 (자유공간 대비)
            if c["comb_free_db"] is not None and c["comb_raw_db"] is not None:
                c["drop_db"] = round(c["comb_raw_db"] - c["comb_free_db"], 2)
                c["is_broken"] = bool(c["drop_db"] <= -10.0)
                #: ⭐겹침을 걷은 기준값으로 다시 재면 판정이 뒤집히나
                #  ⚠실외 짝에는 E_dedup 가 없으므로 이것은 **한쪽만 걷은** 수다.
                if c.get("comb_free_dedup_db") is not None:
                    c["drop_db_if_dedup"] = round(
                        c["comb_raw_db"] - c["comb_free_dedup_db"], 2)
                    c["is_broken_if_dedup"] = bool(c["drop_db_if_dedup"] <= -10.0)
                    c["broken_flips_on_dedup"] = bool(
                        c["is_broken"] != c["is_broken_if_dedup"])
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
                        #: ⭐**문턱 하나에 매달리지 않는다.** 1.05 는 원래 `_meta` 에도
                        #  없던 자유 파라미터였다. 사다리를 통째로 남기고, 판정이
                        #  문턱에 따라 갈리는 칸을 `bright_verdict_flips` 로 표시한다.
                        lad = {}
                        for b in BRIGHTS:
                            o2, n2 = fill(O, bright=b)
                            v2 = snr(o2, el, nm)
                            lad[f"{b:g}"] = {
                                "n_filled": n2, "comb_db": v2,
                                "gap_db": (None if v2 is None else
                                           round(v2 - c["comb_free_db"], 2)),
                            }
                        c["bright_ladder"] = lad
                        c["bright_recovered_at"] = [
                            k for k, x in lad.items()
                            if x["gap_db"] is not None and abs(x["gap_db"]) <= 3.0]
                        c["bright_verdict_flips"] = bool(
                            0 < len(c["bright_recovered_at"]) < len(lad))
                        #: 옛 판이 쓰던 값 — 견줄 수 있게 남긴다
                        c["comb_fill_with_bright_db"] = lad[f"{BRIGHT0:g}"]["comb_db"]
                        c["n_filled_with_bright"] = lad[f"{BRIGHT0:g}"]["n_filled"]
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
        #: ⭐2026-09-07 감사로 더한 것들 — 첫 판에는 이 셋이 없었다
        "null_ko": f"«보임» 문턱은 치환 널({CS.N_NULL} 회)의 최댓값이다"
                   " (comb_snr.py:204 comb_visible 과 같은 뜻)."
                   " ⛔널 아래의 값은 값이 아니라 바닥이고, 그 칸의 drop_db 는 하한이다",
        "bright_threshold_used": BRIGHT0,
        "bright_ladder_ko": f"«밝은 자세» 문턱 {BRIGHT0} 은 자유 파라미터다."
                            f" 흔든 자리: {list(BRIGHTS)}."
                            " ⛔사다리에서 판정이 갈리는 칸(bright_verdict_flips)의"
                            " 결론은 머리기사로 쓰지 않는다",
        "dedup_ko": "comb_free_dedup_db 는 «같은 경로가 여러 줄로 적힌» 것을 걷은 판의 값이다."
                    " ⚠실외 짝에는 E_dedup 가 없다(옛 세대) — 한쪽만 걷은 수이므로"
                    " drop_db_if_dedup 은 두 판의 세대가 다르다. el 0° 열은 인용하지 않는다",
        "limits_ko": [
            "⛔이 저장소에 실기 계측 대조는 0 건이다 — 「검증됐다」로 읽지 않는다.",
            "⛔두 엔진의 절대 레벨을 견주지 않는다. 이 값은 σ(dBsm) 가 아니다.",
        ],
    }, "summary": {
        "n_cells": len(cells), "n_broken": broken, "n_recovered": recovered,
        "n_notch_changed_nothing": notch_same,
        #: ⭐이 셋이 첫 판의 「16 / 8」 을 어디까지 믿을 수 있는지 정한다
        "n_free_below_null": sum(1 for c in cells.values()
                                 if c.get("visible_free") is False),
        "n_out_below_null": sum(1 for c in cells.values()
                                if c.get("visible_out") is False),
        "n_drop_lower_bound_only": sum(1 for c in cells.values()
                                       if c.get("drop_is_lower_bound_only")),
        "n_cells_with_dedup_free": sum(1 for c in cells.values()
                                       if c.get("has_dedup_free")),
        "n_broken_flips_on_dedup": sum(1 for c in cells.values()
                                       if c.get("broken_flips_on_dedup")),
        "n_broken_if_dedup": broken + sum(1 for c in cells.values()
                                          if c.get("broken_flips_on_dedup")),
        "n_bright_verdict_flips": sum(1 for c in cells.values()
                                      if c.get("bright_verdict_flips")),
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
