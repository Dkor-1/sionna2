# -*- coding: utf-8 -*-
"""ledger_outofband_power.py — ⭐**날개끝 밖 전력의 정본 원장** (계산 0, 디스크에서 읽는다)

무엇을 바로잡나
================
리포트 7b·8 권이 헤드라인으로 쓰던 잣대 `frac_power_beyond_ftip` 은 **분모가 틀렸다**.
이름은 «블레이드 대역 전력 중 날개끝 밖 비율» 인데, 실제로 잰 것은 «**동체 DC 봉우리 대비**»
였다. 이 파일이 그 지표를 폐기하고 **절대 대역밖 전력**으로 갈아탄다.

옛 잣대의 정의 (`report07b_bistatic_md.py` · `sbr_grid_convergence_md.py`)
--------------------------------------------------------------------------
    f, S  = 전 구간 주기도 (Hann · 4배 제로패딩)
    P     = 이동평균(|S|², 폭 4·f_flash)          ← ⚠**이 평활이 사고의 원인**
    blade = |f| > 0.15·f_tip                       ← «동체선 밖» 이라고 부른 대역
    out   = |f| > f_tip
    frac_power_beyond_ftip = ΣP[out] / ΣP[blade]

왜 틀렸나 — 커널이 대역 시작보다 넓다 (실측)
---------------------------------------------
    평활 커널 폭      4 × f_flash = 4 × 126.67 Hz = **506.7 Hz**  (반폭 **252.5 Hz**, 421 빈)
    블레이드 대역 시작 0.15 × f_tip = 0.15 × 1228.72 Hz = **184.3 Hz**
    → 커널 **반폭(252.5) > 대역 시작(184.3)**. 이동평균이 f=0 의 동체 봉우리를 대역 안으로
      **끌어다 놓는다**. 분모 ΣP[blade] 가 «블레이드가 만든 전력» 이 아니라 대부분 동체다.

분모 중 동체 DC 번짐이 차지하는 몫 (2026-08-10 실측, 이 파일이 다시 잰다)
    report07_three_engines.npz   SBR **63.5 %** · Sionna **91.7 %** · 순수 PO **98.9 %**
    sbr_grid_convergence.npz     생산 15~64 % · 위상고정 27~98 % · **얼림 96.8~98.4 %**

즉 얼린 팔에서는 분모의 **98 %** 가 동체다. 이 지표는 사실상 `대역밖 전력 / 동체 전력` 이고,
동체 전력은 격자를 얼리든 말든 거의 안 변하므로(±1.3 dB) 지표가 «우연히» 굴러갔을 뿐이다.

무엇이 뒤집히나
    · 엔진 순위 — 평활을 빼고 같은 비율을 다시 재면 **SBR 16.66 % ↔ Sionna 29.81 %** 로
      **순위가 뒤집힌다**(옛 값은 SBR 6.05 % > Sionna 2.12 %).
    · 얼리기 이득 — 비율로는 λ/12 에서 **−1.5 dB**(부호가 뒤집혀 «얼리면 나빠진다» 가 된다),
      절대 전력으로는 **+13.1 dB**. 분모가 같이 15 dB 내려가서 이득을 먹은 것이다.

⚠ 평활은 왜 있었나 — 그리고 왜 여기서 빼는가
==============================================
평활은 **대역 전력을 재려고 넣은 것이 아니다**. 원 코드의 주석이 그렇게 적어 두었다
(`report07b_bistatic_md.envelope`):

    "빗살을 지우고 포락만 남긴다 … 스펙트럼의 **선 위치**(f_flash 배수)는 β 에 안 변하고
     **포락의 폭**만 변한다. 선 구조를 그대로 두고 축척을 재려 하면 추정기가 «안 변한다»
     쪽으로 끌려간다(초판 모양정합이 전부 s≈1 로 붙었다)."

즉 평활의 목적은 **모양·가장자리·축척 추정기**(`edge_of` · `scale_fit`)가 움직이지 않는
빗살선에 붙잡히지 않게 하는 것이었다. 그 목적은 **여기서 필요 없다**:

  1. 대역 전력은 이미 적분이다. 빗살이든 아니든 대역 안 전력의 합은 같다 — 빗살은
     «잡음» 이 아니라 **블레이드 신호 그 자체**이고, 합산이 이미 평균을 낸다.
  2. 이동평균은 선형이라 대역 합에 아무것도 더하지 않는다. Σ_band (K∗P) = Σ_f P(f)·(커널
     질량 중 대역에 떨어지는 몫). 즉 평활이 하는 일은 **대역 경계에서 전력을 주고받는 것뿐**
     이고, 그 주고받음이 바로 위의 DC 번짐이다. 이득은 0, 손해만 있다.
  3. 그러므로 원래 목적(빗살 제거)은 **그것이 필요한 추정기에만 남긴다** — `edge_of`,
     `scale_fit`, 포락 그림은 계속 평활을 쓰면 된다. 대역 전력만 평활에서 뗀다.

⭐ 새 잣대 — 절대 대역밖 전력 (비율이 아니다)
==============================================
    X(f) = FFT(E·w, 4N) ,  w = Hann(N)              ← 창·제로패딩은 옛 잣대와 **같다**
    P(f) = |X(f)|² / (4N · Σ w[n]²)                 ← Parseval 정규화 → 단위가 **평균전력**
                                                       (합이 mean|E|² 와 같다. 검산에 쓴다)

    **P_out  = Σ P(f) over |f| > f_tip**            ← ⭐헤드라인. 절대량이다.
      P_in   = Σ P(f) over 0.15·f_tip < |f| ≤ f_tip   참고 (블레이드 대역, 옛 «분모» 자리)
      P_body = Σ P(f) over |f| ≤ 0.15·f_tip           참고 (동체선)
      P_tot  = Σ P(f) over 전 대역

    정규화가 필요한 곳(단위가 다른 엔진끼리)에서는 **전체 전력**으로만 나눈다:
      **frac_of_total = P_out / P_tot** — 이름에 분모를 박아 둔다. 대역 경계 선택이
      분모에 들어가지 않으므로 DC 번짐 같은 사고가 **구조적으로 불가능**하다.

    ⚠ `out_over_in_ratio_SECONDARY` 도 같이 내지만 **헤드라인이 아니다**. 분모 P_in 자체가
      생산 팔에서는 순수 PO 대비 +19.1 dB 나 부풀어 있다(=그 자리도 격자 잡음이다). 잡음을
      잡음으로 나누는 비율이라 순위가 쉽게 뒤집힌다. 대역 폭도 다르다(밖 8621 Hz ↔ 안 1044 Hz,
      8.26 배) — 비율 하나로 읽으면 폭 차이가 숨는다. 그래서 대역별 평균 PSD 도 같이 낸다.

무엇을 재나 (전부 이미 디스크에 있다 — GPU·재계산 0)
=====================================================
  outputs/report07_three_engines.npz    sbr(생산) · po(순수 PO) · sionna
  outputs/sbr_grid_convergence.npz      E_{prod,phase,froz}_div{8,12,16,24,32} · po_div{8,11,16,24,32}

⚠ 엔진 간 **절대** 비교의 유효범위: `sbr`·`po` 는 같은 단위(산란장 E [m²])이고 전체 레벨도
  1.9 dB 안이라 P_out 을 그대로 비교해도 된다. `sionna` 는 채널계수(경로손실 포함, 레벨
  −110 dB)라 **절대 비교 대상이 아니다** — 그 칸은 `frac_of_total` 로만 읽는다.

원장
    outputs/outofband_power.json    (이 파일이 쓰는 유일한 산출물)
⛔ outputs/report07_three_engines.{json,npz} 와 outputs/sbr_grid_convergence.* 는 **안 건드린다**.

    cd sionna2
    PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/ledger_outofband_power.py
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import socket
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))

SRC_ENG_J = os.path.join(_ROOT, "outputs", "report07_three_engines.json")
SRC_ENG_Z = os.path.join(_ROOT, "outputs", "report07_three_engines.npz")
SRC_GRID_J = os.path.join(_ROOT, "outputs", "sbr_grid_convergence.json")
SRC_GRID_Z = os.path.join(_ROOT, "outputs", "sbr_grid_convergence.npz")
OUTJ = os.path.join(_ROOT, "outputs", "outofband_power.json")

M = json.load(open(SRC_ENG_J))["_meta"]
PRF = float(M["prf_hz"])
FTIP = float(M["f_tip_hz"])
FFL = float(M["f_flash_hz"])
NT = int(M["n"])
FBODY = 0.15 * FTIP
PAD = 4
SMOOTH_HZ = 4.0 * FFL            # 옛 잣대의 평활 폭 (재현용으로만 쓴다)


def _db(x):
    return float(10.0 * np.log10(max(float(x), 1e-300)))


# ═══════════════════════════════════════════════════════════════════════════ #
#  ① 새 잣대 — 평활 없는 주기도의 절대 대역 전력
# ═══════════════════════════════════════════════════════════════════════════ #
def periodogram(E, pad=PAD, window="hann"):
    """Parseval 정규화 주기도. Σ P(f) = mean|E|² (창·패딩 무관).

    창·제로패딩은 옛 잣대와 **같은 값**을 쓴다 — 바뀐 것은 평활 제거와 정규화뿐이다."""
    E = np.asarray(E, complex)
    n = len(E)
    w = np.hanning(n) if window == "hann" else np.blackman(n)
    nf = int(pad * n)
    X = np.fft.fftshift(np.fft.fft(E * w, nf))
    f = np.fft.fftshift(np.fft.fftfreq(nf, 1.0 / PRF))
    P = np.abs(X) ** 2 / (nf * float(np.sum(w ** 2)))
    return f, P


def band_powers(E, f_tip=FTIP, f_body=FBODY, pad=PAD, window="hann"):
    """⭐**정본 정의**. 절대 전력 [|E|² 단위], 비율 아님."""
    Ea = np.asarray(E, complex)
    w = np.hanning(len(Ea)) if window == "hann" else np.blackman(len(Ea))
    win_mean = float(np.sum(np.abs(Ea) ** 2 * w ** 2) / np.sum(w ** 2))   # Parseval 의 참값
    f, P = periodogram(E, pad=pad, window=window)
    m_body = np.abs(f) <= f_body
    m_in = (np.abs(f) > f_body) & (np.abs(f) <= f_tip)
    m_out = np.abs(f) > f_tip
    P_out = float(P[m_out].sum())
    P_in = float(P[m_in].sum())
    P_body = float(P[m_body].sum())
    P_tot = float(P.sum())
    # 대역 폭 [Hz] — 비율을 읽을 때 폭 차이가 숨지 않게 평균 PSD 도 낸다
    w_out = 2.0 * (PRF / 2.0 - f_tip)
    w_in = 2.0 * (f_tip - f_body)
    return dict(
        P_out=P_out, P_in=P_in, P_body=P_body, P_tot=P_tot,
        P_out_db=_db(P_out), P_in_db=_db(P_in), P_tot_db=_db(P_tot),
        frac_of_total=P_out / P_tot,
        frac_of_total_db=_db(P_out / P_tot),
        psd_out_mean=P_out / w_out, psd_in_mean=P_in / w_in,
        psd_out_over_in_db=_db((P_out / w_out) / (P_in / w_in)),
        out_over_in_ratio_SECONDARY=P_out / P_in,
        mean_abs2=float(np.mean(np.abs(Ea) ** 2)),
        # ⭐Parseval 검산 — 참값은 **창가중** 평균전력이다(창을 씌운 신호의 전력)
        parseval_rel_err=abs(P_tot / win_mean - 1.0),
        # 창가중 평균 ↔ 맨 평균 차이. 결함이 아니라 신호가 정상성이 아니라는 뜻(플래시)이다.
        window_vs_plain_mean_db=_db(win_mean / float(np.mean(np.abs(Ea) ** 2))),
    )


# ═══════════════════════════════════════════════════════════════════════════ #
#  ② 옛 잣대 — 폐기 대상. 나란히 보이려고 **그대로** 재현한다
# ═══════════════════════════════════════════════════════════════════════════ #
def old_metric(E):
    """`report07b_bistatic_md` / `sbr_grid_convergence_md` 의 `frac_power_beyond_ftip`
    한 글자도 안 바꾼 재현 + 그 분모가 동체 DC 번짐을 얼마나 먹었는지."""
    E = np.asarray(E, complex)
    w = np.hanning(len(E))
    nf = PAD * len(E)
    S = np.fft.fftshift(np.abs(np.fft.fft(E * w, nf)))
    f = np.fft.fftshift(np.fft.fftfreq(nf, 1.0 / PRF))
    P = S ** 2
    df = float(f[1] - f[0])
    kn = max(3, int(round(SMOOTH_HZ / df)) | 1)
    ker = np.ones(kn) / kn
    Pe = np.convolve(P, ker, mode="same")
    Pdc = np.convolve(np.where(np.abs(f) <= FBODY, P, 0.0), ker, mode="same")
    Pbl = np.convolve(np.where(np.abs(f) > FBODY, P, 0.0), ker, mode="same")
    blade = np.abs(f) > FBODY
    out = blade & (np.abs(f) > FTIP)
    den = float(Pe[blade].sum())
    # 부수 지표 — 리포트 표의 «바닥» 칸도 평활에 걸려 있다
    hi = np.abs(f) > 1.5 * FTIP
    return dict(
        frac_power_beyond_ftip=float(Pe[out].sum() / den),
        denominator_dc_leak_frac=float(Pdc[blade].sum() / den),
        # 평활은 두고 DC 번짐만 뺀 판 (적대적 감사 2 의 `frac_clean`) — 이것도 비율이라 뒤집힌다
        dc_cleaned_ratio_smoothed=float(Pe[out].sum() / float(Pbl[blade].sum())),
        floor_rel_db_smoothed=float(10 * np.log10(np.median(Pe[hi]) / Pe.max())),
        floor_rel_db_raw_median=float(10 * np.log10(np.median(P[hi]) / P.max())),
        floor_rel_db_raw_mean=float(10 * np.log10(np.mean(P[hi]) / P.max())),
        kernel_bins=int(kn), df_hz=df,
    )


def row(label, E, extra=None):
    r = dict(label=label)
    r.update(band_powers(E))
    o = old_metric(E)
    r["old_frac_power_beyond_ftip"] = o["frac_power_beyond_ftip"]
    r["old_denominator_dc_leak_frac"] = o["denominator_dc_leak_frac"]
    r["old_dc_cleaned_ratio_smoothed"] = o["dc_cleaned_ratio_smoothed"]
    r["old_floor_rel_db_smoothed"] = o["floor_rel_db_smoothed"]
    r["new_floor_rel_db_raw_mean"] = o["floor_rel_db_raw_mean"]
    r["new_floor_rel_db_raw_median"] = o["floor_rel_db_raw_median"]
    if extra:
        r.update(extra)
    return r


def band_profile(E):
    """대역밖이 어디에 몰려 있나 — f_tip 배수 구간별 **절대** 전력(평활 없이)."""
    f, P = periodogram(E)
    prof = {}
    for lo, hi in [(1.0, 1.5), (1.5, 2.0), (2.0, 3.0), (3.0, 8.0)]:
        m = (np.abs(f) >= lo * FTIP) & (np.abs(f) < hi * FTIP)
        prof[f"{lo}-{hi}"] = float(P[m].sum())
    return prof


def loglog_slope(divs, vals):
    d = np.log(np.asarray(divs, float))
    v = np.log(np.asarray(vals, float))
    A = np.stack([d, np.ones_like(d)], 1)
    c, *_ = np.linalg.lstsq(A, v, rcond=None)
    res = v - A @ c
    tot = float(np.sum((v - v.mean()) ** 2))
    return float(c[0]), float(1 - np.sum(res ** 2) / tot) if tot > 0 else float("nan")


# ═══════════════════════════════════════════════════════════════════════════ #
def main():
    ZE = np.load(SRC_ENG_Z)
    ZG = np.load(SRC_GRID_Z)
    GM = json.load(open(SRC_GRID_J))["_meta"]
    DIVS = [int(d) for d in GM["divs"]]
    PO_DIVS = [int(d) for d in GM["po_divs"]]

    # ── ① 세 엔진 (모노 원장) ───────────────────────────────────────────────
    ENG_NOTE = {
        "sbr": "우리 SBR (가림 + 각도의존 Γ) · 단위 = 산란장 E [m²]",
        "po": "우리 순수 PO (가림 없음) · 단위 = 산란장 E [m²]",
        "sionna": "Sionna PathSolver 채널계수 h (경로손실 포함) · **절대 비교 대상 아님**",
    }
    eng_rows = []
    for k in ("sbr", "po", "sionna"):
        r = row(k, np.asarray(ZE[k])[:NT],
                extra=dict(engine=ENG_NOTE[k],
                           units_comparable_to_po=(k != "sionna"),
                           band_profile_abs=band_profile(np.asarray(ZE[k])[:NT])))
        eng_rows.append(r)
    E = {r["label"]: r for r in eng_rows}

    def rank(key, rev=True):
        return [r["label"] for r in sorted(eng_rows, key=lambda x: x[key], reverse=rev)]

    ranking = dict(
        note=("«나쁜 순서» = 대역밖이 큰 순서. 옛 잣대와 새 잣대가 어디서 갈리는지 본다. "
              "sionna 는 단위가 달라 절대 순위에서 뺀다."),
        old_frac_power_beyond_ftip=dict(
            order=rank("old_frac_power_beyond_ftip"),
            values_pct={r["label"]: 100 * r["old_frac_power_beyond_ftip"] for r in eng_rows}),
        new_frac_of_total=dict(
            order=rank("frac_of_total"),
            values_pct={r["label"]: 100 * r["frac_of_total"] for r in eng_rows}),
        new_P_out_absolute=dict(
            order=[l for l in rank("P_out") if E[l]["units_comparable_to_po"]],
            values={l: E[l]["P_out"] for l in ("sbr", "po")},
            sbr_over_po_db=_db(E["sbr"]["P_out"] / E["po"]["P_out"]),
            excluded=["sionna (채널계수라 단위가 다르다)"]),
        secondary_out_over_in=dict(
            order=rank("out_over_in_ratio_SECONDARY"),
            values_pct={r["label"]: 100 * r["out_over_in_ratio_SECONDARY"] for r in eng_rows},
            warning=(
                ("⚠ 이것이 **순위를 뒤집는 칸**이다 — "
                 if rank("out_over_in_ratio_SECONDARY") != rank("frac_of_total") else
                 "⚠ 이 칸은 헤드라인과 **같은 순서**다(격자를 얼리기 전에는 뒤집혔다) — ")
                + f"SBR {100*E['sbr']['out_over_in_ratio_SECONDARY']:.1f} % ↔ Sionna "
                  f"{100*E['sionna']['out_over_in_ratio_SECONDARY']:.1f} %. "
                  "분모 P_in 이 광선 팔에서는 격자 잡음으로 부풀 수 있다. "
                  "헤드라인으로 쓰지 마라.")),
        verdict=(
            f"옛 잣대(SBR {100*E['sbr']['old_frac_power_beyond_ftip']:.2f} % · "
            f"Sionna {100*E['sionna']['old_frac_power_beyond_ftip']:.2f} % · "
            f"PO {100*E['po']['old_frac_power_beyond_ftip']:.2f} %)는 «동체 DC 대비» 였다. "
            f"새 헤드라인 `frac_of_total` 로는 SBR {100*E['sbr']['frac_of_total']:.2f} % · "
            f"Sionna {100*E['sionna']['frac_of_total']:.2f} % · "
            f"PO {100*E['po']['frac_of_total']:.5f} % 다. SBR↔Sionna 간격은 "
            f"{_db(E['sbr']['old_frac_power_beyond_ftip'] / E['sionna']['old_frac_power_beyond_ftip']):.1f} dB "
            f"에서 {_db(E['sbr']['frac_of_total'] / E['sionna']['frac_of_total']):.1f} dB 로 옮겨간다"
            f"(순서는 {'그대로' if rank('frac_of_total') == rank('old_frac_power_beyond_ftip') else '바뀐다'}). "
            + ("대역비(P_out/P_in)로 읽으면 순위가 **뒤집힌다** — 그래서 비율을 안 쓴다."
               if rank("out_over_in_ratio_SECONDARY") != rank("frac_of_total") else
               "대역비(P_out/P_in)로 읽어도 지금은 같은 순서다 — 그래도 분모가 격자 잡음에 "
               "걸리므로 헤드라인은 분모를 이름에 박은 `frac_of_total` 로만 쓴다.")),
        sbr_over_sionna_db=dict(
            old_frac=_db(E["sbr"]["old_frac_power_beyond_ftip"]
                         / E["sionna"]["old_frac_power_beyond_ftip"]),
            new_frac_of_total=_db(E["sbr"]["frac_of_total"] / E["sionna"]["frac_of_total"]),
            secondary_out_over_in=_db(E["sbr"]["out_over_in_ratio_SECONDARY"]
                                      / E["sionna"]["out_over_in_ratio_SECONDARY"]),
        ),
    )

    # ── ② 격자 사다리 ───────────────────────────────────────────────────────
    po_ref = band_powers(ZG[f"po_div{11}"]) if "po_div11" in ZG else band_powers(ZE["po"][:NT])
    grid_rows = []
    for dv in DIVS:
        for arm in ("prod", "phase", "froz"):
            e = np.asarray(ZG[f"E_{arm}_div{dv}"])
            r = row(f"{arm}_div{dv}", e,
                    extra=dict(arm=arm, div=dv,
                               P_out_db_over_pure_po=_db(band_powers(e)["P_out"] / po_ref["P_out"]),
                               P_in_db_over_pure_po=_db(band_powers(e)["P_in"] / po_ref["P_in"]),
                               n_grid_median=float(np.median(ZG[f"n_grid_div{dv}"])),
                               n_lit_median=float(np.median(ZG[f"n_lit_div{dv}"]))))
            grid_rows.append(r)
    po_rows = [row(f"po_div{dv}", np.asarray(ZG[f"po_div{dv}"]), extra=dict(arm="pure_po", div=dv))
               for dv in PO_DIVS]
    G = {(r["arm"], r["div"]): r for r in grid_rows}

    # ── ③ ⭐얼리기 이득 — 새 잣대로 확정 ────────────────────────────────────
    freeze = []
    for dv in DIVS:
        p, ph, fz = G[("prod", dv)], G[("phase", dv)], G[("froz", dv)]
        freeze.append(dict(
            div=dv,
            # ⭐헤드라인 — 절대 대역밖 전력의 감소
            freeze_gain_P_out_db=_db(p["P_out"] / fz["P_out"]),
            # 갈라 보기: 위상원점 고정의 몫 ↔ 격자 자체를 얼린 몫
            split_prod_to_phase_db=_db(p["P_out"] / ph["P_out"]),
            split_phase_to_froz_db=_db(ph["P_out"] / fz["P_out"]),
            # 참고 정규화
            freeze_gain_frac_of_total_db=_db(p["frac_of_total"] / fz["frac_of_total"]),
            # 폐기된 옛 잣대와 그 «DC 뺀 비율» 판 — 둘 다 얼마나 다른지
            old_ratio_gain_db=_db(p["old_frac_power_beyond_ftip"]
                                  / fz["old_frac_power_beyond_ftip"]),
            band_ratio_gain_db_SECONDARY=_db(p["out_over_in_ratio_SECONDARY"]
                                             / fz["out_over_in_ratio_SECONDARY"]),
            dc_cleaned_smoothed_ratio_gain_db=_db(p["old_dc_cleaned_ratio_smoothed"]
                                                  / fz["old_dc_cleaned_ratio_smoothed"]),
            # 이득이 «전체 레벨이 내려간 것» 이 아님을 보이는 칸들
            d_P_body_db=_db(p["P_body"] / fz["P_body"]),
            d_P_tot_db=_db(p["P_tot"] / fz["P_tot"]),
            d_P_in_db=_db(p["P_in"] / fz["P_in"]),
            # 깎인 P_in 이 «신호» 였나 «격자 잡음» 이었나 — 심판은 순수 PO
            prod_P_in_db_over_pure_po=p["P_in_db_over_pure_po"],
            froz_P_in_db_over_pure_po=fz["P_in_db_over_pure_po"],
        ))
    fz12 = next(r for r in freeze if r["div"] == 12)
    freeze_verdict = dict(
        headline=(
            f"⭐**격자를 얼리면 대역밖 절대 전력이 λ/12 에서 "
            f"{fz12['freeze_gain_P_out_db']:.1f} dB, λ/32 에서 "
            f"{freeze[-1]['freeze_gain_P_out_db']:.1f} dB 내려간다.** 사다리 전체에서 "
            f"+{min(r['freeze_gain_P_out_db'] for r in freeze):.1f} ~ "
            f"+{max(r['freeze_gain_P_out_db'] for r in freeze):.1f} dB, "
            "부호가 한 번도 안 뒤집힌다."),
        gains_db={r["div"]: r["freeze_gain_P_out_db"] for r in freeze},
        old_ratio_gains_db={r["div"]: r["old_ratio_gain_db"] for r in freeze},
        band_ratio_gains_db_SECONDARY={r["div"]: r["band_ratio_gain_db_SECONDARY"]
                                       for r in freeze},
        dc_cleaned_smoothed_ratio_gains_db={r["div"]: r["dc_cleaned_smoothed_ratio_gain_db"]
                                            for r in freeze},
        why_the_ratio_flipped_sign=(
            f"λ/12 에서 대역비는 {fz12['band_ratio_gain_db_SECONDARY']:+.2f} dB, 평활을 두고 "
            f"DC 번짐만 뺀 판은 {fz12['dc_cleaned_smoothed_ratio_gain_db']:+.2f} dB — 둘 다 "
            "«얼리면 나빠진다» 로 읽힌다. 이유는 분모다: 얼리면 P_in 도 "
            f"{fz12['d_P_in_db']:.1f} dB 같이 내려간다. 비율은 그 둘을 상쇄시켜 이득을 통째로 "
            "먹는다. ⚠ 분모를 어떻게 고쳐도 비율인 한 이 함정이 남는다 — 그래서 절대량으로 "
            "간다."),
        is_the_P_in_drop_signal_loss=dict(
            question="얼리기가 진짜 블레이드 신호를 깎았나?",
            answer="아니다 — 격자 잡음을 깎았다.",
            evidence=("심판은 독립 엔진인 순수 PO 다. 생산 팔의 P_in 은 순수 PO 보다 "
                      f"{fz12['prod_P_in_db_over_pure_po']:+.1f} dB 높고(= 그 대역도 대부분 "
                      f"격자 잡음이다), 얼린 팔은 {fz12['froz_P_in_db_over_pure_po']:+.1f} dB 다. "
                      "얼리기는 P_in 을 **물리 기준 쪽으로** 끌어내린다."),
            per_div={r["div"]: dict(prod=r["prod_P_in_db_over_pure_po"],
                                    froz=r["froz_P_in_db_over_pure_po"]) for r in freeze},
        ),
        not_a_global_level_shift=dict(
            note=("이득이 «전부 다 내려간 것» 이 아님 — 동체(DC)는 거의 안 변하고 전체 전력도 "
                  "1.3 dB 안이다. 내려간 것은 블레이드 대역과 그 밖이다."),
            d_P_body_db={r["div"]: r["d_P_body_db"] for r in freeze},
            d_P_tot_db={r["div"]: r["d_P_tot_db"] for r in freeze},
        ),
    )

    # ── ④ 수렴 — 새 잣대로 다시 (결론이 바뀌나) ─────────────────────────────
    conv = {}
    ge12 = [d for d in DIVS if d >= 12]
    for arm in ("prod", "phase", "froz"):
        v12 = [G[(arm, d)]["P_out"] for d in ge12]
        s12, r2 = loglog_slope(ge12, v12)
        sf, r2f = loglog_slope(DIVS, [G[(arm, d)]["P_out"] for d in DIVS])
        conv[arm] = dict(slope_ge12=s12, r2_ge12=r2, slope_full=sf, r2_full=r2f,
                         drop_db_div12_to_div32=_db(v12[0] / v12[-1]),
                         P_out_per_div={d: G[(arm, d)]["P_out"] for d in DIVS})
    po_slope, po_r2 = loglog_slope(PO_DIVS, [r["P_out"] for r in po_rows])
    conv["pure_po"] = dict(slope_full=po_slope, r2_full=po_r2,
                           P_out_per_div={r["div"]: r["P_out"] for r in po_rows},
                           spread_db=_db(max(r["P_out"] for r in po_rows)
                                         / min(r["P_out"] for r in po_rows)))
    conv["verdict"] = (
        "⭐**결론은 안 바뀐다.** 새 절대 잣대로도 생산 팔의 기울기는 "
        f"{conv['prod']['slope_ge12']:+.2f}(d² 이산화 잡음이면 −2 여야 한다)이고 λ/12→λ/32 "
        f"에서 {conv['prod']['drop_db_div12_to_div32']:.1f} dB 만 내려간다. 얼린 팔은 "
        f"{conv['froz']['slope_ge12']:+.2f} (R² {conv['froz']['r2_ge12']:.3f}) 로 예측된 −2 에 "
        "붙는다. 순수 PO 는 점 간격에 무관하다"
        f"(사다리 전체 산포 {conv['pure_po']['spread_db']:.2f} dB). "
        "바뀐 것은 **숫자와 엔진 순위**이지 격자 얼리기 판정이 아니다.")

    # ── ⑤ 적대적 점검 — 새 잣대 자체가 인공물이 아닌가 ──────────────────────
    robust = dict(
        note=("새 잣대가 창 누설·제로패딩·대역 경계의 산물이 아님을 보인다. "
              "P_out 은 f_body 를 **아예 안 쓴다** — 옛 사고(DC 번짐)가 구조적으로 불가능하다."),
        window_hann_vs_blackman_db={
            k: _db(band_powers(np.asarray(ZE[k])[:NT])["P_out"]
                   / band_powers(np.asarray(ZE[k])[:NT], window="blackman")["P_out"])
            for k in ("sbr", "po", "sionna")},
        zero_pad_4_vs_1_db={
            k: _db(band_powers(np.asarray(ZE[k])[:NT])["P_out"]
                   / band_powers(np.asarray(ZE[k])[:NT], pad=1)["P_out"])
            for k in ("sbr", "po", "sionna")},
        parseval_max_rel_err=float(max(r["parseval_rel_err"]
                                       for r in eng_rows + grid_rows + po_rows)),
        parseval_note=("참값은 **창가중** 평균전력이다. 맨 평균과의 차이"
                       "(`window_vs_plain_mean_db`, 최대 "
                       f"{max(abs(r['window_vs_plain_mean_db']) for r in eng_rows + grid_rows + po_rows):.2f} dB)"
                       "는 결함이 아니라 신호가 정상성이 아니라는 뜻이다 — 플래시가 있다."),
        band_edge_sensitivity_db={
            k: {f"f_tip x{s}": _db(band_powers(np.asarray(ZE[k])[:NT], f_tip=s * FTIP)["P_out"]
                                   / band_powers(np.asarray(ZE[k])[:NT])["P_out"])
                for s in (0.95, 1.05)} for k in ("sbr", "po", "sionna")},
        f_body_independence="P_out 의 정의에 f_body 가 들어가지 않는다 (P_in 에만 들어간다)",
        band_edge_reading=(
            "⭐경계 민감도가 엔진을 가른다. f_tip 을 5 % 올려 자르면 광선 두 팔은 "
            "0.7~0.9 dB 만 움직이고(=넓은 바닥) 순수 PO 는 5.1 dB 움직인다(=절벽). "
            "즉 PO 의 P_out 절대값은 «절벽을 어디서 잘랐나» 에 가깝고 바닥 높이가 아니다 — "
            "PO 를 «0 에 가깝다» 의 기준선으로만 쓰고 그 절대값을 인용하지 마라."),
        dc_window_leak_argument=(
            "Hann 창의 누설이 f_tip 밖까지 갈 수 있나 — f_tip 은 DC 에서 "
            f"{FTIP / (PRF / NT):.0f} 빈 떨어져 있고 Hann 은 그 거리에서 −100 dB 아래다. "
            "Blackman 으로 바꿔도 P_out 이 0.2 dB 안에서 같다는 위 칸이 그 실증이다."),
    )

    # ── ⑥ 리포트가 무엇을 고쳐 써야 하나 ────────────────────────────────────
    must_change = [
        ("reports/06_5_bistatic.ipynb 절 2 표 — «블레이드 전력 중 f_tip 밖 비율» 칸의 "
         "0.02 / 2.12 / 6.05 % 를 전부 버린다. 새 표는 `frac_of_total` 로 "
         f"PO {100*E['po']['frac_of_total']:.5f} % · Sionna {100*E['sionna']['frac_of_total']:.2f} % · "
         f"SBR {100*E['sbr']['frac_of_total']:.2f} % 이고, 열 제목을 «전체 전력 중 f_tip 밖 "
         "몫» 으로 바꿔야 한다(분모를 이름에 박는다)."),
        ("reports/06_5_bistatic.ipynb 같은 표의 «날개끝 밖 바닥(봉우리 대비)» 칸 "
         "−118.8 / −41.4 / −33.5 dB 도 평활에 걸려 있다. 평활을 빼면 "
         f"{E['po']['new_floor_rel_db_raw_mean']:.1f} / {E['sionna']['new_floor_rel_db_raw_mean']:.1f} / "
         f"{E['sbr']['new_floor_rel_db_raw_mean']:.1f} dB 다(평균 기준). 순서는 안 바뀌지만 "
         "값이 20~30 dB 옮겨간다 — 평활이 분모의 봉우리를 421 빈에 퍼뜨려 깎았기 때문이다."),
        ("reports/06_5_bistatic.ipynb 절 2 본문 «광선을 쓰는 두 팔은 둘 다 새어 나간다» 는 "
         "**유지된다**(그리고 이것이 이 절의 논지다). 하지만 SBR↔Sionna 의 대소는 "
         "**분모를 밝히지 않고 쓰면 안 된다** — 전체전력 대비로는 SBR 이 "
         f"{ranking['sbr_over_sionna_db']['new_frac_of_total']:.1f} dB 위지만, 대역비로 재면 "
         f"순위가 뒤집힌다(SBR {100*E['sbr']['out_over_in_ratio_SECONDARY']:.1f} % ↔ Sionna "
         f"{100*E['sionna']['out_over_in_ratio_SECONDARY']:.1f} %). 표에 «전체 전력 중» 을 "
         "명기하고, 순위가 정규화에 달렸다는 각주를 단다."),
        ("reports/06_5_bistatic.ipynb 부록 «추정기» 표에 대역밖 전력 행을 새로 넣는다 — "
         "«평활 없는 주기도의 절대 대역 전력, 정규화는 전체 전력» 이라고 정의를 박는다."),
        ("benchmark/report07b_bistatic_md.py 의 `frac_power_beyond_ftip` (578행) 은 "
         "폐기 표시하고 이 원장을 참조하게 한다. `envelope` 평활은 `edge_of`·`scale_fit` "
         "에서는 **그대로 둔다** — 거기서는 목적이 맞다."),
        ("benchmark/sbr_grid_convergence_md.py 의 `measure()` (229행) 도 같다. json 의 "
         "`convergence.freeze_gain_db_at_div12 = 9.34 dB` 는 옛 잣대 값이다 — 새 값은 "
         f"**{fz12['freeze_gain_P_out_db']:.2f} dB**(절대 대역밖 전력)."),
        ("docs/PLAN_0818.md 26행의 «대역 밖 전력 6.05 %» 를 «전체 전력 중 f_tip 밖 "
         f"{100*E['sbr']['frac_of_total']:.2f} %» 로 고친다."),
        ("docs/RETRACTION_LOG.md 에 새 항목을 넣는다 — «지표의 분모가 이름과 달랐다» 는 "
         "선행연구 오독이 아니라 **우리 추정기의 결함**이고, 이 프로젝트가 스스로 반증해 "
         "거둬들인 것이므로 정본에 남아야 한다."),
        ("얼리기를 다룰 8 권/리포트 문장은 이득을 **절대 전력**으로 적어야 한다 — "
         f"λ/12 {fz12['freeze_gain_P_out_db']:+.1f} dB. 어떤 비율로 적어도 λ/12 에서 부호가 "
         f"뒤집힌다(대역비 {fz12['band_ratio_gain_db_SECONDARY']:+.2f} dB · DC 뺀 평활판 "
         f"{fz12['dc_cleaned_smoothed_ratio_gain_db']:+.2f} dB) — «얼리면 나빠진다» 는 거짓 "
         f"결론이 된다. 비율을 쓸 거면 분모(P_in)가 같이 {fz12['d_P_in_db']:.1f} dB "
         "내려갔다는 사실을 같은 줄에 적는다."),
        ("반대로 **안 고쳐도 되는 것** — 격자 수렴 판정(생산 기울기 −0.55, 얼린 팔 −2.1, "
         "순수 PO 무관)은 새 잣대로도 같다. 얼리기 문단의 논리는 그대로 두고 숫자만 바꾼다."),
    ]

    # ── 원장 쓰기 ───────────────────────────────────────────────────────────
    out = dict(
        _meta=dict(
            generated=_dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            host=socket.gethostname(), python=sys.version.split()[0],
            purpose=("`frac_power_beyond_ftip` 폐기 · 절대 대역밖 전력으로 교체. "
                     "계산 0 — 이미 있는 npz 만 읽는다."),
            sources=[os.path.relpath(p, _ROOT) for p in (SRC_ENG_Z, SRC_GRID_Z)],
            drone=M["drone"], fc_hz=M["fc_hz"], az_deg=M["az_deg"], el_deg=M["el_deg"],
            n=NT, prf_hz=PRF, nyquist_hz=PRF / 2.0,
            f_tip_hz=FTIP, f_flash_hz=FFL, f_body_hz=FBODY,
            df_hz=PRF / NT, window="hann", zero_pad=PAD,
            band_widths_hz=dict(out=2.0 * (PRF / 2.0 - FTIP), inband=2.0 * (FTIP - FBODY),
                                out_over_in=(PRF / 2.0 - FTIP) / (FTIP - FBODY)),
            writes_only=os.path.relpath(OUTJ, _ROOT),
            does_not_touch=["outputs/report07_three_engines.json",
                            "outputs/report07_three_engines.npz",
                            "outputs/sbr_grid_convergence.json",
                            "outputs/sbr_grid_convergence.npz"],
        ),
        why_old_metric_is_wrong=dict(
            old_definition="frac_power_beyond_ftip = Σ(K∗P)[|f|>f_tip] / Σ(K∗P)[|f|>0.15 f_tip]",
            fault=("이름은 «블레이드 대역 전력 중» 인데 실제 분모는 대부분 동체 DC 다. "
                   "평활 커널이 대역 시작보다 넓어서 f=0 의 봉우리를 대역 안으로 끌어온다."),
            smoothing_kernel_hz=SMOOTH_HZ,
            smoothing_kernel_half_hz=float((old_metric(ZE["sbr"][:NT])["kernel_bins"] - 1) / 2
                                           * old_metric(ZE["sbr"][:NT])["df_hz"]),
            band_start_hz=FBODY,
            kernel_half_wider_than_band_start=bool(
                (old_metric(ZE["sbr"][:NT])["kernel_bins"] - 1) / 2
                * old_metric(ZE["sbr"][:NT])["df_hz"] > FBODY),
            measured_dc_leak_frac_of_denominator=dict(
                three_engines={r["label"]: r["old_denominator_dc_leak_frac"] for r in eng_rows},
                grid_ladder={r["label"]: r["old_denominator_dc_leak_frac"] for r in grid_rows},
            ),
            why_smoothing_was_there=(
                "원 목적은 대역 전력이 아니라 **모양·가장자리·축척 추정기**를 위한 빗살 제거였다 "
                "(`envelope` 주석: 빗살 선 위치는 β 에 안 변하고 포락 폭만 변한다). "
                "대역 전력은 이미 적분이라 빗살을 지울 이유가 없고, 이동평균은 선형이라 "
                "대역 경계에서 전력을 주고받는 일밖에 안 한다 — 이득 0, 손해(DC 번짐)만 있다."),
            is_the_purpose_lost=(
                "아니다. 빗살 제거가 필요한 곳(`edge_of` · `scale_fit` · 포락 그림)에는 평활을 "
                "그대로 둔다. 대역 전력에서만 뗀다. 두 잣대는 목적이 다르므로 같은 전처리를 "
                "공유할 이유가 없었다."),
        ),
        new_definition=dict(
            headline="P_out = Σ |X(f)|² over |f| > f_tip   (평활 없음, 원 주기도)",
            reference="P_in  = Σ |X(f)|² over 0.15 f_tip < |f| ≤ f_tip",
            also="P_body (|f| ≤ 0.15 f_tip) · P_tot (전 대역)",
            normalization=("필요할 때만, **전체 전력**으로: frac_of_total = P_out / P_tot. "
                           "분모를 이름에 박았다. 대역 경계가 분모에 안 들어간다."),
            units=("Parseval 정규화라 Σ P(f) = mean|E|². 절대값은 그 팔의 |E|² 단위이고 "
                   "같은 단위끼리(sbr↔po, prod↔phase↔froz)만 직접 비교한다."),
            ratio_policy=("out_over_in_ratio 는 `_SECONDARY` 로만 낸다 — 분모 자체가 격자 "
                          "잡음이고 대역 폭이 8.26 배 다르다."),
        ),
        three_engines=eng_rows,
        three_engines_ranking=ranking,
        grid_ladder=grid_rows,
        pure_po_ladder=po_rows,
        freeze_gain=freeze,
        freeze_verdict=freeze_verdict,
        convergence=conv,
        robustness=robust,
        what_reports_must_change=must_change,
    )
    json.dump(out, open(OUTJ, "w"), ensure_ascii=False, indent=1)
    print("→", OUTJ)

    # ── 사람이 읽는 표 ──────────────────────────────────────────────────────
    print(f"\n■ 세팅 — f_tip {FTIP:.1f} Hz · f_body {FBODY:.1f} Hz · PRF {PRF:.0f} Hz · N {NT}")
    print(f"  옛 평활 커널 {SMOOTH_HZ:.1f} Hz (반폭 252.5 Hz) > 대역 시작 {FBODY:.1f} Hz  ⇒ DC 번짐")
    print(f"  대역 폭 — 밖 {2*(PRF/2-FTIP):.0f} Hz · 안 {2*(FTIP-FBODY):.0f} Hz "
          f"(밖이 {(PRF/2-FTIP)/(FTIP-FBODY):.2f} 배 넓다)")

    print("\n■ 세 엔진 (outputs/report07_three_engines.npz)")
    print(f"{'arm':>7} | {'옛 frac%':>9} {'분모중DC%':>9} | {'P_out':>11} {'P_in':>11} "
          f"{'frac_tot%':>10} | {'out/in%':>8}")
    for r in eng_rows:
        print(f"{r['label']:>7} | {100*r['old_frac_power_beyond_ftip']:9.4f} "
              f"{100*r['old_denominator_dc_leak_frac']:9.2f} | {r['P_out']:11.4e} "
              f"{r['P_in']:11.4e} {100*r['frac_of_total']:10.5f} | "
              f"{100*r['out_over_in_ratio_SECONDARY']:8.3f}")
    print(f"  순위  옛(frac_power_beyond_ftip): {' > '.join(ranking['old_frac_power_beyond_ftip']['order'])}")
    print(f"  순위  새(frac_of_total)         : {' > '.join(ranking['new_frac_of_total']['order'])}")
    print(f"  순위  대역비(참고·헤드라인 아님) : {' > '.join(ranking['secondary_out_over_in']['order'])}  ⚠뒤집힘")
    print(f"  절대  SBR P_out 은 순수 PO 보다 {ranking['new_P_out_absolute']['sbr_over_po_db']:+.1f} dB")

    print("\n■ 바닥(봉우리 대비) — 이 칸도 평활에 걸려 있었다")
    print(f"{'arm':>7} {'옛(평활)':>10} {'새(원·평균)':>12} {'새(원·중앙)':>12}")
    for r in eng_rows:
        print(f"{r['label']:>7} {r['old_floor_rel_db_smoothed']:10.2f} "
              f"{r['new_floor_rel_db_raw_mean']:12.2f} {r['new_floor_rel_db_raw_median']:12.2f}")

    print("\n■ 격자 사다리 (outputs/sbr_grid_convergence.npz)")
    print(f"{'div':>4} {'arm':>6} | {'옛 frac%':>9} {'분모중DC%':>9} | {'P_out':>11} "
          f"{'P_in':>11} {'frac_tot%':>9} | {'P_out−PO dB':>11} {'P_in−PO dB':>10}")
    for r in grid_rows:
        print(f"{r['div']:>4} {r['arm']:>6} | {100*r['old_frac_power_beyond_ftip']:9.3f} "
              f"{100*r['old_denominator_dc_leak_frac']:9.2f} | {r['P_out']:11.4e} "
              f"{r['P_in']:11.4e} {100*r['frac_of_total']:9.4f} | "
              f"{r['P_out_db_over_pure_po']:11.2f} {r['P_in_db_over_pure_po']:10.2f}")
    print(f"  순수 PO 사다리: P_out {po_rows[0]['P_out']:.4e} … 산포 "
          f"{conv['pure_po']['spread_db']:.2f} dB (점 간격에 무관)")

    print("\n■ ⭐얼리기 이득 — 새 잣대로 확정")
    print(f"{'div':>4} {'새 절대 P_out':>13} {'옛 비율':>9} {'대역비(참고)':>13} | "
          f"{'ΔP_in':>8} {'ΔP_body':>9} {'ΔP_tot':>8}")
    for r in freeze:
        print(f"{r['div']:>4} {r['freeze_gain_P_out_db']:+13.2f} {r['old_ratio_gain_db']:+9.2f} "
              f"{r['band_ratio_gain_db_SECONDARY']:+13.2f} | {r['d_P_in_db']:+8.2f} "
              f"{r['d_P_body_db']:+9.2f} {r['d_P_tot_db']:+8.2f}")
    print("  갈라 보기 (P_out): " + "  ".join(
        f"div{r['div']} 위상 {r['split_prod_to_phase_db']:+.1f} / 격자 {r['split_phase_to_froz_db']:+.1f}"
        for r in freeze))
    print("  P_in 이 순수 PO 보다 몇 dB 위인가: " + "  ".join(
        f"div{r['div']} 생산 {r['prod_P_in_db_over_pure_po']:+.1f} → 얼림 "
        f"{r['froz_P_in_db_over_pure_po']:+.1f}" for r in freeze))

    print("\n■ 수렴 (새 절대 잣대)")
    for arm in ("prod", "phase", "froz"):
        c = conv[arm]
        print(f"  {arm:>6}: 기울기(div≥12) {c['slope_ge12']:+.2f} (R² {c['r2_ge12']:.3f})  "
              f"λ/12→λ/32 {c['drop_db_div12_to_div32']:+.2f} dB")
    print(f"  {'pure_po':>6}: 기울기 {conv['pure_po']['slope_full']:+.2f}  "
          f"산포 {conv['pure_po']['spread_db']:.2f} dB")

    print("\n■ 적대적 점검")
    print(f"  Parseval 최대 상대오차 {robust['parseval_max_rel_err']:.2e}")
    print("  창 hann↔blackman [dB]: " + "  ".join(
        f"{k} {v:+.2f}" for k, v in robust["window_hann_vs_blackman_db"].items()))
    print("  제로패딩 4↔1 [dB]: " + "  ".join(
        f"{k} {v:+.2f}" for k, v in robust["zero_pad_4_vs_1_db"].items()))

    print("\n■ 리포트가 고쳐 써야 할 것")
    for i, s in enumerate(must_change, 1):
        print(f"  {i:>2}. {s}")


if __name__ == "__main__":
    main()
