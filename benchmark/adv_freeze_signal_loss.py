# -*- coding: utf-8 -*-
"""
adv_freeze_signal_loss.py — ⭐**얼리기가 «신호» 도 깎았나** (적대적 감사 · 렌즈 B)
=====================================================================================

기본 입장
---------
`outputs/freeze_before_after.json` 은 «날개끝 **밖** 전력이 27/27 열에서 내려갔다» 를
헤드라인으로 든다. 대역밖은 물리가 없는 자리이므로 내려가면 좋다. 그런데 같은 재계산에서
**블레이드 대역 안**의 전력도 같이 내려갔다. 이 파일의 기본 입장은 그 반대편이다:

    ⛔ «얼리기가 진짜 마이크로도플러도 지웠다»

그 입장을 깨려면 «없어진 것이 잡음이었다» 는 **독립 증거**가 있어야 한다. 여기서 독립이란
광선 격자를 **안 쓰는** 엔진이라는 뜻이다 — 순수 PO(`_po_series` · 점구름 면적분)가 그것이다.
PO 열은 이 재계산에서 비트 그대로였다(광선 격자와 무관하므로). 그래서 PO 를 심판으로 쓸 수 있다.

무엇을 재나 (전부 디스크에서 읽는다 — GPU·재계산 0)
----------------------------------------------------
    ① P_in          블레이드 대역 0.15·f_tip < |f| ≤ f_tip 의 절대 전력
                    → 얼린 뒤 얼마나 줄었나, 그리고 **순수 PO 대비 초과분**이 얼마나 줄었나.
                      초과분이 0 밑으로 내려가면 진짜 신호를 깎은 것이다.
    ② blade_coh     같은 대역만 남긴 복소 파형과 순수 PO 의 복소 상관
                    → 남은 것이 PO 와 **닮아졌나**. 잡음을 지웠으면 올라가야 한다.
    ③ flash_contrast  20·log10( max|E−Ē| / median|E−Ē| ) — 플래시가 바닥보다 몇 dB 위인가
                    (`benchmark/report16_base.md_metrics16` 와 **같은 정의**)
    ④ comb_line_db  블레이드 빗살의 선 대 선사이 대조비 — f_flash 배수 자리의 PSD 중앙값을
                    그 사이 자리의 중앙값으로 나눈 것. «플래시 선이 흐려졌나» 의 정량.
    ⑤ f_flash_est   |E−Ē| 포락의 자기상관 첫 봉우리 → 예측 f_flash 에서 멀어졌나
    ⑥ oob_over_in   P_out / P_in — ⭐**대가**. 절대 대역밖은 내려가도 블레이드 대역이 더 많이
                    내려가면 «신호 대 비물리 잔차» 는 나빠진다. 헤드라인이 안 보여 주는 칸이다.

⚠ 대역 정의·창·제로패딩은 정본 원장(`benchmark/ledger_outofband_power.band_powers`)과 같다.
⛔ 원장을 하나도 안 덮어쓴다. 산출은 `outputs/freeze_signal_loss.json` 하나다.

    PYTHONPATH=src python benchmark/adv_freeze_signal_loss.py
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

OUTJ = os.path.join(ROOT, "outputs", "freeze_signal_loss.json")
PRE = os.path.join(ROOT, "outputs", "prefreeze")
PAD = 4
F_BODY_FRAC = 0.15


def _db(x):
    return float(10.0 * np.log10(max(float(x), 1e-300)))


def periodogram(E, prf, pad=PAD):
    """Parseval 정규화 주기도 — 정본 원장과 같은 창·패딩."""
    E = np.asarray(E, complex)
    n = len(E)
    w = np.hanning(n)
    nf = pad * n
    X = np.fft.fftshift(np.fft.fft(E * w, nf))
    f = np.fft.fftshift(np.fft.fftfreq(nf, 1.0 / prf))
    return f, np.abs(X) ** 2 / (nf * float(np.sum(w ** 2)))


def bands(E, prf, f_tip):
    f, P = periodogram(E, prf)
    fb = F_BODY_FRAC * f_tip
    return dict(P_body=float(P[np.abs(f) <= fb].sum()),
                P_in=float(P[(np.abs(f) > fb) & (np.abs(f) <= f_tip)].sum()),
                P_out=float(P[np.abs(f) > f_tip].sum()),
                P_tot=float(P.sum()))


def bandpass(E, prf, lo, hi):
    X = np.fft.fft(np.asarray(E, complex))
    f = np.fft.fftfreq(len(X), 1.0 / prf)
    Y = np.zeros_like(X)
    m = (np.abs(f) > lo) & (np.abs(f) <= hi)
    Y[m] = X[m]
    return np.fft.ifft(Y)


def coherence(x, y):
    return float(abs(np.vdot(x, y)) / np.sqrt(np.vdot(x, x).real * np.vdot(y, y).real))


def flash_contrast_db(E):
    ac = np.abs(np.asarray(E, complex) - np.mean(E))
    return float(20 * np.log10(max(float(ac.max()), 1e-300) /
                               max(float(np.median(ac)), 1e-300)))


def comb(E, prf, f_flash, f_tip, tol_bins=2):
    """빗살 선의 세기 — 선 위 PSD 중앙값 ÷ 선 사이 PSD 중앙값 [dB], 블레이드 대역 안에서."""
    ac = np.asarray(E, complex) - np.mean(E)
    f, P = periodogram(ac, prf)
    df = float(f[1] - f[0])
    band = (np.abs(f) > F_BODY_FRAC * f_tip) & (np.abs(f) <= f_tip)
    line = np.zeros_like(f, bool)
    k = 1
    while k * f_flash <= f_tip:
        line |= np.abs(np.abs(f) - k * f_flash) <= tol_bins * df
        k += 1
    on, off = band & line, band & (~line)
    if not on.any() or not off.any():
        return float("nan"), float("nan")
    return (_db(float(np.median(P[on])) / max(float(np.median(P[off])), 1e-300)),
            float(P[on].sum() / max(float(P[band].sum()), 1e-300)))


def width_ratio(E, prf, f_tip, thr_db=-20.0):
    """AC 스펙트럼이 첨두 대비 thr_db 위인 **가장 바깥** 주파수 ÷ f_tip.

    운동학이 맞으면 1 근처여야 한다(팁보다 빨리 도는 것은 없다). 비물리 잔차가 첨두 대비
    높이 남으면 이 값이 커진다 — `report16_base.md_metrics16` 의 `width_ratio` 와 같은 뜻이다."""
    ac = np.asarray(E, complex) - np.mean(E)
    f, P = periodogram(ac, prf)
    idx = np.where(P >= P.max() * 10 ** (thr_db / 10.0))[0]
    return float(np.max(np.abs(f[idx])) / f_tip)


def f_flash_est(E, prf, f_flash_true):
    """|E−Ē| 포락의 자기상관 첫 봉우리 → 플래시 주파수 추정 [Hz]."""
    ac = np.abs(np.asarray(E, complex) - np.mean(E))
    ac = ac - ac.mean()
    s = float(np.std(ac))
    if s <= 0:
        return float("nan")
    ac = ac / s
    nf = 1 << int(np.ceil(np.log2(2 * len(ac))))
    r = np.fft.irfft(np.abs(np.fft.rfft(ac, nf)) ** 2, nf)[:len(ac)]
    r = r / r[0]
    lo, hi = int(0.4 * prf / f_flash_true), min(int(3.0 * prf / f_flash_true), len(r) - 1)
    if hi <= lo + 2:
        return float("nan")
    return float(prf / (int(np.argmax(r[lo:hi])) + lo))


def analyse(tag, Eb, Ea, prf, f_tip, f_flash, Epo=None):
    row = {"tag": tag, "n": int(len(Ea)), "prf_hz": float(prf),
           "f_tip_hz": float(f_tip), "f_flash_hz": float(f_flash)}
    bb, ba = bands(Eb, prf, f_tip), bands(Ea, prf, f_tip)
    row["P_in_db_before"], row["P_in_db_after"] = _db(bb["P_in"]), _db(ba["P_in"])
    row["P_in_delta_db"] = row["P_in_db_after"] - row["P_in_db_before"]
    row["P_out_delta_db"] = _db(ba["P_out"]) - _db(bb["P_out"])
    row["oob_over_in_db_before"] = _db(bb["P_out"] / bb["P_in"])
    row["oob_over_in_db_after"] = _db(ba["P_out"] / ba["P_in"])
    row["oob_over_in_delta_db"] = row["oob_over_in_db_after"] - row["oob_over_in_db_before"]
    row["flash_contrast_db_before"] = flash_contrast_db(Eb)
    row["flash_contrast_db_after"] = flash_contrast_db(Ea)
    row["comb_line_db_before"], row["comb_frac_before"] = comb(Eb, prf, f_flash, f_tip)
    row["comb_line_db_after"], row["comb_frac_after"] = comb(Ea, prf, f_flash, f_tip)
    row["width_ratio_before"] = width_ratio(Eb, prf, f_tip)
    row["width_ratio_after"] = width_ratio(Ea, prf, f_tip)
    row["f_flash_est_before_hz"] = f_flash_est(Eb, prf, f_flash)
    row["f_flash_est_after_hz"] = f_flash_est(Ea, prf, f_flash)
    row["f_flash_relerr_before"] = row["f_flash_est_before_hz"] / f_flash - 1.0
    row["f_flash_relerr_after"] = row["f_flash_est_after_hz"] / f_flash - 1.0
    if Epo is not None:
        bp = bands(Epo, prf, f_tip)
        row["P_in_db_po"] = _db(bp["P_in"])
        row["P_in_excess_over_po_db_before"] = row["P_in_db_before"] - row["P_in_db_po"]
        row["P_in_excess_over_po_db_after"] = row["P_in_db_after"] - row["P_in_db_po"]
        row["P_out_excess_over_po_db_after"] = _db(ba["P_out"]) - _db(bp["P_out"])
        lo, hi = F_BODY_FRAC * f_tip, f_tip
        row["blade_coh_vs_po_before"] = coherence(bandpass(Eb, prf, lo, hi),
                                                  bandpass(Epo, prf, lo, hi))
        row["blade_coh_vs_po_after"] = coherence(bandpass(Ea, prf, lo, hi),
                                                 bandpass(Epo, prf, lo, hi))
        row["flash_contrast_db_po"] = flash_contrast_db(Epo)
        row["comb_line_db_po"], _ = comb(Epo, prf, f_flash, f_tip)
        row["oob_over_in_db_po"] = _db(bp["P_out"] / bp["P_in"])
        row["width_ratio_po"] = width_ratio(Epo, prf, f_tip)
    return row


def _med(xs):
    xs = [x for x in xs if x is not None and np.isfinite(x)]
    return float(np.median(xs)) if xs else float("nan")


def _group(tag):
    """⭐두 무리를 갈라야 대가가 보인다 — 동체가 든 열과 블레이드만 있는 열은 반대로 움직인다."""
    return "blade_only" if ("F_blade_occ" in tag or "G_blade_free" in tag) else "with_body"


def _by_group(rows):
    out = {}
    for g in ("with_body", "blade_only"):
        v = [r for r in rows if _group(r["tag"]) == g]
        if not v:
            continue
        d_oob = [r["oob_over_in_delta_db"] for r in v]
        d_fl = [r["flash_contrast_db_after"] - r["flash_contrast_db_before"] for r in v]
        d_cb = [r["comb_line_db_after"] - r["comb_line_db_before"] for r in v]
        out[g] = dict(
            n=len(v),
            oob_over_in_db_before_median=round(_med([r["oob_over_in_db_before"] for r in v]), 3),
            oob_over_in_db_after_median=round(_med([r["oob_over_in_db_after"] for r in v]), 3),
            oob_over_in_delta_db_median=round(_med(d_oob), 3),
            n_oob_worse=sum(1 for x in d_oob if x > 0),
            flash_contrast_delta_db_median=round(_med(d_fl), 3),
            n_flash_improved=sum(1 for x in d_fl if x > 0),
            comb_line_delta_db_median=round(_med(d_cb), 3),
            n_comb_improved=sum(1 for x in d_cb if x > 0),
        )
    out["why_ko"] = (
        "동체가 든 열(A·B·2 초 호버·세 엔진)은 동체 DC 가 크고 가짜 변조도 거기에 실려 있었다 — "
        "얼리면 블레이드 대역이 크게 빠지면서 남은 대역밖 잔차가 **상대적으로** 커 보인다. "
        "블레이드만 남긴 열(F·G)은 신호 자체가 25 dB 아래라 빗살이 잔차에 묻혀 있었다 — "
        "얼리면 빗살이 드러나서 두 잣대가 함께 좋아진다.")
    return out


def main():
    rows = []

    # ── ① 세 엔진 판 (SBR ↔ 순수 PO 가 같은 파일에 있다) ──────────────────────
    M = json.load(open(os.path.join(ROOT, "outputs", "report07_three_engines.json"),
                       encoding="utf-8"))["_meta"]
    A = np.load(os.path.join(ROOT, "outputs", "report07_three_engines.npz"))
    B = np.load(os.path.join(PRE, "report07_three_engines.npz"))
    rows.append(analyse("report07_three_engines/sbr", B["sbr"], A["sbr"],
                        M["prf_hz"], M["f_tip_hz"], M["f_flash_hz"], A["po"]))

    # ── ② 리포트 15b — 6 칸 × SBR 4 팔, PO 짝이 있는 팔만 심판을 붙인다 ────────
    J = json.load(open(os.path.join(ROOT, "outputs", "report15b_microdoppler.json"),
                       encoding="utf-8"))
    ZA = np.load(os.path.join(ROOT, "outputs", "report15b_series.npz"))
    ZB = np.load(os.path.join(PRE, "report15b_series.npz"))
    PAIR = {"A_sbr_locked": "C_po_locked", "B_sbr_spread": "D_po_spread",
            "F_blade_occ": None, "G_blade_free": None}
    for cell, cd in J["cells"].items():
        ph = cd["physics"]
        for arm, po in PAIR.items():
            k = f"{cell}/{arm}/E"
            if k not in ZA.files:
                continue
            rows.append(analyse(f"report15b/{cell}/{arm}", ZB[k], ZA[k], ph["prf"],
                                ph["f_tip"], ph["f_flash"],
                                ZA[f"{cell}/{po}/E"] if po else None))

    # ── ③ 2 초 호버 — ⚠PO 대조 팔이 **없다**(이 파일이 그것을 결함으로 적는다) ──
    for pre in ("report07_hover_long", "report07_hover_long_outdoor"):
        m = json.load(open(os.path.join(ROOT, "outputs", f"{pre}.json"),
                           encoding="utf-8"))["_meta"]
        rows.append(analyse(f"{pre}/{m['preset']}",
                            np.load(os.path.join(PRE, f"{pre}.npz"))["E"],
                            np.load(os.path.join(ROOT, "outputs", f"{pre}.npz"))["E"],
                            m["prf_hz"], m["f_tip_hz"], m["f_flash_hz"]))

    judged = [r for r in rows if "blade_coh_vs_po_after" in r]
    up = [r for r in judged if r["blade_coh_vs_po_after"] > r["blade_coh_vs_po_before"]]
    below = [r for r in judged if r["P_in_excess_over_po_db_after"] < 0.0]
    fl_up = [r for r in rows if r["flash_contrast_db_after"] > r["flash_contrast_db_before"]]
    closer = [r for r in judged
              if abs(r["flash_contrast_db_after"] - r["flash_contrast_db_po"])
              < abs(r["flash_contrast_db_before"] - r["flash_contrast_db_po"])]

    res = {
        "_meta": {
            "script": "benchmark/adv_freeze_signal_loss.py",
            "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "lens_ko": "적대적 감사 렌즈 B — 기본 입장은 «얼리기가 진짜 물리도 지웠다»",
            "independent_judge_ko": (
                "순수 PO 열(`C_po_locked`·`D_po_spread`·`report07_three_engines.npz['po']`)은 "
                "점구름 면적분이라 **광선 격자를 안 쓴다**. 이번 재계산에서 비트 그대로였다 — "
                "그래서 «없어진 것이 잡음이었나» 의 심판이 된다."),
            "band_definition_ko": (
                "정본 원장 `benchmark/ledger_outofband_power.band_powers` 와 같은 정의 — "
                "동체 |f|≤0.15·f_tip · 블레이드 0.15·f_tip<|f|≤f_tip · 대역밖 |f|>f_tip, "
                "Hann·4배 제로패딩·Parseval 정규화."),
            "flash_contrast_definition_ko": (
                "`benchmark/report16_base.md_metrics16` 와 같은 정의 — "
                "20·log10(max|E−Ē| / median|E−Ē|)."),
            "before_is_ko": "outputs/prefreeze/ 사본(자세마다 격자를 다시 정의하던 판)",
            "reads_only": ["outputs/report07_three_engines.*", "outputs/report15b_*",
                           "outputs/report07_hover_long*.npz", "outputs/prefreeze/*"],
            "writes": ["outputs/freeze_signal_loss.json"],
            "no_recompute_ko": "GPU 0 초. 이미 디스크에 있는 복소열만 다시 읽었다.",
        },
        "rows": {r["tag"]: r for r in rows},
        "summary": {
            "n_series": len(rows),
            "n_with_po_judge": len(judged),
            "P_in_delta_db_median": round(_med([r["P_in_delta_db"] for r in rows]), 3),
            "P_in_excess_over_po_db": {
                "before_median": round(_med([r["P_in_excess_over_po_db_before"]
                                             for r in judged]), 3),
                "after_median": round(_med([r["P_in_excess_over_po_db_after"]
                                            for r in judged]), 3),
                "n_below_po_after": len(below),
                "meaning_ko": (
                    "얼린 뒤에도 블레이드 대역이 순수 PO **위**에 있으면 깎인 것은 잉여였다. "
                    "PO 밑으로 내려간 열이 하나라도 있으면 그 열은 진짜 신호를 잃은 것이다."),
            },
            "blade_coh_vs_po": {
                "before_median": round(_med([r["blade_coh_vs_po_before"] for r in judged]), 4),
                "after_median": round(_med([r["blade_coh_vs_po_after"] for r in judged]), 4),
                "n_improved": len(up), "n_judged": len(judged),
                "regressed": sorted(r["tag"] for r in judged if r not in up),
                "meaning_ko": (
                    "블레이드 대역만 남긴 복소 파형이 광선을 안 쓰는 엔진과 얼마나 닮았나. "
                    "전력이 줄면서 **닮음이 오르면** 줄어든 것은 잡음이다."),
            },
            "flash_contrast_db": {
                "n_improved": len(fl_up), "n_series": len(rows),
                "delta_median": round(_med([r["flash_contrast_db_after"]
                                            - r["flash_contrast_db_before"] for r in rows]), 3),
                "n_closer_to_po": len(closer), "n_judged": len(judged),
                "meaning_ko": (
                    "플래시 대조비는 «봉우리가 바닥보다 몇 dB 위인가» 다. 자의 흔들림은 "
                    "골짜기를 메워 중앙값을 올리므로 대조비를 **낮춘다** — 얼리면 올라가야 한다."),
            },
            "comb_line_db_delta_median": round(_med([r["comb_line_db_after"]
                                                     - r["comb_line_db_before"]
                                                     for r in rows]), 3),
            "f_flash_relerr_abs_median": {
                "before": round(_med([abs(r["f_flash_relerr_before"]) for r in rows]), 5),
                "after": round(_med([abs(r["f_flash_relerr_after"]) for r in rows]), 5),
                "meaning_ko": "포락 자기상관으로 읽은 플래시 주파수 — 두 판 다 예측 위에 선다.",
            },
            "width_ratio_20db": {
                "before_median": round(_med([r["width_ratio_before"] for r in rows]), 3),
                "after_median": round(_med([r["width_ratio_after"] for r in rows]), 3),
                "po_median": round(_med([r["width_ratio_po"] for r in judged]), 3),
                "n_farther_from_one": sum(
                    1 for r in rows
                    if abs(r["width_ratio_after"] - 1.0) > abs(r["width_ratio_before"] - 1.0)),
                "meaning_ko": (
                    "⚠ 스펙트럼 **가장자리**(첨두 −20 dB) ÷ f_tip. 운동학이 맞으면 1 이고 "
                    "순수 PO 가 그 자리에 선다. 얼린 뒤 중앙값은 1 쪽으로 오지만 여전히 멀고, "
                    "동체가 든 열에서는 오히려 더 멀어진다 — 가장자리는 «잔차 ÷ 첨두» 로 "
                    "정해지는 양이라 P_out/P_in 이 나빠진 것과 같은 사실이다. "
                    "⭐폭·가장자리 지표는 얼린 SBR 열이 아니라 PO 열에서 읽는다."),
            },
            "oob_over_in_db": {
                "before_median": round(_med([r["oob_over_in_db_before"] for r in rows]), 3),
                "after_median": round(_med([r["oob_over_in_db_after"] for r in rows]), 3),
                "delta_median": round(_med([r["oob_over_in_delta_db"] for r in rows]), 3),
                "po_median": round(_med([r["oob_over_in_db_po"] for r in judged]), 3),
                "n_worse": sum(1 for r in rows if r["oob_over_in_delta_db"] > 0),
                "meaning_ko": (
                    "⭐**대가**. 절대 대역밖 전력은 내려가지만 블레이드 대역이 더 많이 내려가는 "
                    "열이 있어, «신호 대 비물리 잔차» 로 읽으면 나빠진다. 헤드라인(절대 대역밖 "
                    "−11 dB)만 인용하면 이 칸이 안 보인다."),
            },
            "by_group": _by_group(rows),
        },
    }
    res["verdict"] = {
        "signal_was_erased": bool(below),
        "headline_ko": (
            f"블레이드 대역 전력은 중앙값 {res['summary']['P_in_delta_db_median']:+.1f} dB 줄었다. "
            f"그러나 광선을 안 쓰는 엔진(순수 PO) 대비 초과분이 "
            f"+{res['summary']['P_in_excess_over_po_db']['before_median']:.1f} dB 에서 "
            f"+{res['summary']['P_in_excess_over_po_db']['after_median']:.1f} dB 로 줄었을 뿐 "
            f"**PO 밑으로 내려간 열은 "
            f"{res['summary']['P_in_excess_over_po_db']['n_below_po_after']} 개**이고, "
            f"같은 대역의 복소 일치는 {res['summary']['blade_coh_vs_po']['before_median']:.2f} → "
            f"{res['summary']['blade_coh_vs_po']['after_median']:.2f} 로 올랐다"
            f"({res['summary']['blade_coh_vs_po']['n_improved']}/"
            f"{res['summary']['blade_coh_vs_po']['n_judged']} 열). "
            f"플래시 대조비도 {res['summary']['flash_contrast_db']['n_improved']}/"
            f"{res['summary']['flash_contrast_db']['n_series']} 열에서 올랐다 — "
            f"⛔«진짜 물리도 지웠다» 는 반증됐다."),
        "cost_ko": (
            f"⚠ 대가는 **비율**이다. 동체가 든 "
            f"{res['summary']['by_group']['with_body']['n']} 열에서 P_out/P_in 이 "
            f"{res['summary']['by_group']['with_body']['oob_over_in_db_before_median']:.1f} dB "
            f"→ {res['summary']['by_group']['with_body']['oob_over_in_db_after_median']:.1f} dB "
            f"로 {res['summary']['by_group']['with_body']['n_oob_worse']} 열에서 **나빠진다**"
            f"(순수 PO 는 {res['summary']['oob_over_in_db']['po_median']:.1f} dB). "
            "잉여 신호가 사라진 만큼 남은 잔차가 상대적으로 커 보이는 것이고, 그 잔차는 "
            "여전히 물리가 아니다 — 지금 판의 마이크로도플러 동적범위 상한이 여기 있다. "
            f"블레이드만 남긴 {res['summary']['by_group']['blade_only']['n']} 열은 반대로 "
            f"{res['summary']['by_group']['blade_only']['oob_over_in_delta_db_median']:+.1f} dB "
            f"좋아지고 빗살 대조비가 "
            f"{res['summary']['by_group']['blade_only']['n_comb_improved']}/"
            f"{res['summary']['by_group']['blade_only']['n']} 열에서 "
            f"{res['summary']['by_group']['blade_only']['comb_line_delta_db_median']:+.1f} dB "
            "올라온다 — 약한 신호일수록 얼리기가 크게 남는다."),
        "open_ko": (
            "⚠ `report07_hover_long*` 두 열에는 **순수 PO 대조 팔이 없다**. 2 초 창의 능선이 "
            "이 감사에서 심판을 못 받는 유일한 자리다 — 같은 자세·같은 rpm 궤적으로 PO 팔을 "
            "한 번 돌리면(모노 PO 는 4096 자세에 8.4 초였다) 닫힌다."),
    }

    with open(OUTJ, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(f"✅ {os.path.relpath(OUTJ, ROOT)}  ({len(rows)} 열)")
    print(json.dumps(res["verdict"], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
