# -*- coding: utf-8 -*-
"""
viz_report05_paper.py — 리포트 05(결과편)의 **게재 규격** 그림
==========================================================================================
    PYTHONPATH=src ~/.venvs/py312/bin/python src/viz_report05_paper.py

출력: `outputs/figures/report05_pf{1..7}_*.pdf` + 같은 이름의 400 dpi PNG.

규격은 `docs/PAPER_SPEC.md` §4.3 이고 그 실행 구현이 `src/paper_kit.py` 다 —
벡터 PDF + 300 dpi 이상 PNG 동시 저장 · 2단 축소 후에도 8 pt 이상 · **색 + 마커/해치
이중부호화**(흑백 인쇄에서 계열이 살아남는다) · 그림 글자는 전부 영어.
`save_figure()` 가 저장 직전에 그 셋을 검사하고 결과를 PDF 메타데이터에 심는다.

이 파일은 `outputs/*.json` 을 **읽기만** 한다(실험을 다시 돌리지 않는다).

그림 1장 = 질문 1개. 각 함수 docstring 의 첫 줄이 그 질문이다.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from paper_kit import HATCHES, paper_style, save_figure            # noqa: E402

ROOT = os.path.abspath(os.path.join(_HERE, ".."))
OUT = os.path.join(ROOT, "outputs")
FIG = "outputs/figures"

MODES = ("W1", "L1", "G1")
LABEL = {"W1": "WiFi 5.21 GHz (VHT-LTF)",
         "L1": "LTE 1.84 GHz (CRS)",
         "G1": "5G NR 3.5 GHz (SSB)"}
SHORT = {"W1": "WiFi", "L1": "LTE", "G1": "5G NR"}
DRONES = ("mini5pro", "mavic4pro", "matrice4e", "phantom4", "s1000plus")
DLAB = {"mini5pro": "Mini 5 Pro", "mavic4pro": "Mavic 4 Pro",
        "matrice4e": "Matrice 4E", "phantom4": "Phantom 4",
        "s1000plus": "S1000+"}
ANCHOR_BAND = {"W1": "WiFi 5.21 GHz", "L1": "LTE 1.843 GHz", "G1": "5G 3.5 GHz"}
CELL = ("ranges.{d}.{m}.equal_psd.full_waveform_capture.by_N.1")


def _load(name):
    with open(os.path.join(OUT, name), encoding="utf-8") as f:
        return json.load(f)


def _cell(FS, drone, mode):
    return FS["ranges"][drone][mode]["equal_psd"]["full_waveform_capture"]["by_N"]["1"]


def _plain_log(ax, which: str, ticks):
    """로그축 눈금을 **평문**으로 적는다.

    matplotlib 기본 로그 눈금은 `10^{-1}` 꼴 mathtext 라 지수가 본문의 0.7 배로 작아진다
    — 8 pt 하한(PAPER_SPEC §4.3)을 그 지수 하나가 깬다. 그래서 평문으로 다시 쓴다.
    """
    from matplotlib.ticker import FixedFormatter, FixedLocator, NullFormatter
    axis = ax.xaxis if which == "x" else ax.yaxis
    lab = [("%g" % t) for t in ticks]
    axis.set_major_locator(FixedLocator(list(ticks)))
    axis.set_major_formatter(FixedFormatter(lab))
    axis.set_minor_formatter(NullFormatter())


def _band_style(i: int) -> dict:
    """밴드 계열의 막대 스타일 — 색 + **해치** 이중부호화."""
    from paper_kit import PALETTE
    return dict(color=PALETTE[i], hatch=HATCHES[i], edgecolor="black", linewidth=0.6)


# --------------------------------------------------------------------------- #
#  PF1 — 밴드 간 격차를 만드는 항은 무엇인가?
# --------------------------------------------------------------------------- #
def pf1_gap():
    """밴드 간 출력 SNR 격차를 만드는 항은 λ² 와 σ 중 무엇인가?"""
    FS, AN, SS = (_load("report13_freespace.json"), _load("sigma_anchor.json"),
                  _load("sigma_sensitivity.json"))
    B = {}
    for m in MODES:
        t = dict(_cell(FS, "mavic4pro", m)["budget_terms_db"])
        t["dsig"] = float(AN["drones"]["mavic4pro"]["modes"]["slope_only"]
                          ["delta_db"][ANCHOR_BAND[m]])
        t["sigma_anch"] = t["sigma"] + t["dsig"]
        t["common"] = sum(float(t[k]) for k in
                          ("eirp", "grx", "spread", "n0", "t_cpi", "eta_ref",
                           "duty", "losses", "k_mode"))
        t["total_anch"] = t["total"] + t["dsig"]
        B[m] = t
    keys = [("common", "common terms"), ("lambda2", "λ²"),
            ("sigma_anch", "σ (anchored)"), ("total_anch", "output SNR")]

    gd = SS["gap_decomposition"]["by_drone"]
    pair_names = ("W1-L1", "W1-G1", "L1-G1")

    with paper_style(width="double", base_pt=10.0, aspect=0.42) as st:
        fig, (a, b) = st.figure(1, 2)

        x = np.arange(len(keys), dtype=float)
        w = 0.26
        for j, m in enumerate(MODES):
            a.bar(x + (j - 1) * w, [float(B[m][k]) for k, _ in keys], w,
                  label=SHORT[m], **_band_style(j))
        a.axhline(0.0, color="black", linewidth=0.8)
        a.set_xticks(x)
        a.set_xticklabels([lab for _, lab in keys], rotation=18, ha="right")
        a.set_ylabel("dB")
        a.set_title("(a) Link terms at d = 1 km, one receiver")
        a.legend(loc="lower right", ncol=1)

        for i, p in enumerate(pair_names):
            xs = [abs(gd[d]["pairs"][p]["d_sigma_db"]) for d in DRONES]
            ys = [abs(gd[d]["pairs"][p]["d_axes_db"]) for d in DRONES]
            b.plot(xs, ys, linestyle="none", label=p.replace("W1", "WiFi")
                   .replace("L1", "LTE").replace("G1", "5G"),
                   **{k: v for k, v in st.series(i).items() if k != "linestyle"})
        lim = 20.0
        b.plot([0, lim], [0, lim], color="black", linewidth=0.9, linestyle="--",
               marker="none", label="equal contribution")
        b.set_xlim(0, lim)
        b.set_ylim(0, lim)
        b.set_xlabel("|Δσ| between the two bands [dB]")
        b.set_ylabel("|Δ(σ-free axes)| [dB]")
        b.set_title("(b) Which term makes the pair gap\n"
                    f"({SS['gap_decomposition']['n_pairs_sigma_dominates']} of "
                    f"{SS['gap_decomposition']['n_pairs_total']} pairs below the line)")
        b.legend(loc="upper left")

    return save_figure(
        fig, f"{FIG}/report05_pf1_gap", dpi=400, placed_width_in=7.16,
        title="Per-band cost decomposition",
        caption="Per-band cost decomposition. (a) Only two link terms differ between "
                "the three illuminators at a fixed geometry: the wavelength term "
                "lambda-squared and the target cross section sigma. (b) For each "
                "airframe and band pair, the cross-section difference exceeds the "
                "sigma-free difference in 9 of 15 pairs, so the ranking is a target "
                "property as much as a waveform property.")


# --------------------------------------------------------------------------- #
#  PF2 — 세 파형의 순위는 기체마다 같은가?
# --------------------------------------------------------------------------- #
def pf2_ranking():
    """세 파형의 순위는 자세 인용 방식에 따라 어떻게 달라지는가?"""
    SS = _load("sigma_sensitivity.json")
    cfg = SS["configurations"]["by_config"]
    panels = [("as_published", "(a) Single aspect (ψ = 0)"),
              ("aspect_avg_anchored",
               "(b) Aspect-averaged σ, measured slope")]

    with paper_style(width="double", base_pt=10.0, aspect=0.42) as st:
        fig, axes = st.figure(1, 2, sharey=True)
        for ax, (name, title) in zip(axes, panels):
            by = cfg[name]["by_drone"]
            x = np.arange(len(DRONES), dtype=float)
            w = 0.26
            for j, m in enumerate(MODES):
                rel = []
                for d in DRONES:
                    R = by[d]["R90_m"]
                    ref = float(np.exp(np.mean(np.log([R[k] for k in MODES]))))
                    rel.append(R[m] / ref)
                ax.bar(x + (j - 1) * w, rel, w, label=SHORT[m], **_band_style(j))
            ax.axhline(1.0, color="black", linewidth=0.8)
            ax.set_xticks(x)
            ax.set_xticklabels([DLAB[d] for d in DRONES], rotation=22, ha="right")
            n_ord = cfg[name]["n_distinct_orders"]
            ax.set_title(f"{title}\n{n_ord} distinct order(s) across 5 airframes")
        axes[0].set_ylabel("range relative to the\nthree-band geometric mean")
        axes[0].set_ylim(0.5, 1.6)
        axes[0].legend(loc="upper left", ncol=3)

    return save_figure(
        fig, f"{FIG}/report05_pf2_ranking", dpi=400, placed_width_in=7.16,
        title="Three-waveform comparison, normalised",
        caption="Three-waveform comparison, normalised per airframe to remove the "
                "absolute-level dependence. Quoted at a single aspect the five "
                "airframes produce three different waveform orders (a); quoted on "
                "aspect-averaged cross sections with the measured frequency slope "
                "applied, all five agree on LTE > 5G NR > WiFi (b). The ordering is "
                "therefore a statement about the aspect statistic, not about a single "
                "look direction.")


# --------------------------------------------------------------------------- #
#  PF3 — 그 순위는 σ 오차 아래에서 얼마나 버티나?
# --------------------------------------------------------------------------- #
def pf3_robust():
    """σ 오차가 공통모드일 때와 밴드별일 때 순위는 각각 어디까지 버티는가?"""
    SS = _load("sigma_sensitivity.json")
    cm = SS["common_mode"]
    df = SS["differential"]
    aa = SS["aspect_averaged"]
    mc = SS["monte_carlo_per_band_error"]
    span = float(SS["_meta"]["realistic_differential_span_db"])

    with paper_style(width="double", base_pt=10.0, aspect=0.36) as st:
        fig, (a, b, c) = st.figure(1, 3)

        off = np.array(cm["by_drone"]["mavic4pro"]["offset_db"], float)
        for j, m in enumerate(MODES):
            R = np.array(cm["by_drone"]["mavic4pro"]["R90_m"][m], float)
            a.plot(off, R / R[len(R) // 2], label=SHORT[m], markevery=8,
                   **st.series(j))
        a.set_xlabel("common-mode σ error [dB]")
        a.set_ylabel("range relative to baseline")
        a.set_title("(a) Common mode:\norder invariant in 15 of 15 cells")
        a.legend(loc="upper left")

        y = np.arange(len(DRONES), dtype=float)
        h = 0.36
        b.barh(y + h / 2, [df["by_drone"][d]["analytic_smallest_flip_span_db"]
                           for d in DRONES], h, label="single aspect",
               **_band_style(0))
        b.barh(y - h / 2, [aa["by_drone"][d]["smallest_flip_span_db"]
                           for d in DRONES], h, label="aspect-averaged",
               **_band_style(1))
        b.axvline(span, color="black", linewidth=1.0, linestyle="--")
        b.annotate("realistic\nenvelope", (span, -0.45),
                   textcoords="offset points", xytext=(3, 0), ha="left",
                   va="center")
        b.set_yticks(y)
        b.set_yticklabels([DLAB[d] for d in DRONES])
        b.invert_yaxis()
        b.set_xlabel("per-band differential error\nthat flips the order [dB]")
        b.set_title("(b) Differential mode:\nflip threshold per airframe")
        b.legend(loc="lower right", frameon=True, framealpha=0.92,
                 edgecolor="none")
        b.set_xlim(0, 8.6)

        ks = sorted(mc["by_drone"][DRONES[0]]["by_sigma_e_db"], key=float)
        lv = [float(k) for k in ks]
        for j, d in enumerate(DRONES):
            p = [mc["by_drone"][d]["by_sigma_e_db"][k]["p_order_preserved"]
                 for k in ks]
            c.plot(lv, p, label=DLAB[d], **st.series(j))
        c.set_xscale("log")
        _plain_log(c, "x", [0.5, 1, 2, 3, 5, 10])
        c.set_xlabel("per-band σ error, 1 s.d. [dB]")
        c.set_ylabel("P(order preserved)")
        c.set_ylim(0.0, 1.02)
        c.set_title(f"(c) Monte Carlo, K = {mc['K'] // 1000}k\nper-band independent error")
        c.legend(loc="upper right", frameon=True, framealpha=0.92,
                 edgecolor="none")

    return save_figure(
        fig, f"{FIG}/report05_pf3_robust", dpi=400, placed_width_in=7.16,
        title="Ranking robustness against cross-section error",
        caption="Ranking robustness against cross-section error. A common-mode error "
                "moves all three bands together: the order is preserved at every "
                r"offset in $\pm$10 dB and only the absolute range moves, by about a "
                "quarter of the error in dB (a). A per-band differential error is what "
                "reorders the waveforms, and the threshold at which it does is an "
                "airframe property: 0.61 to 7.42 dB at a single aspect and 0.09 to "
                "2.95 dB after aspect averaging (b), consistent with the Monte-Carlo "
                "order-preservation probability (c).")


# --------------------------------------------------------------------------- #
#  PF4 — 5G 의 도플러 가드는 CPI 를 늘리면 어떻게 되나?
# --------------------------------------------------------------------------- #
def pf4_cpi():
    """5G 의 눈먼 헤딩 비율은 CPI 와 표적 속도에 따라 어떻게 움직이는가?"""
    CG = _load("cpi_guard_sweep.json")
    sw = CG["cpi_sweep"]["at_R90"]
    cost = CG["cost_of_long_cpi"]
    ref_T = float(CG["meta"]["geometry"]["T_cpi_ref_s"])

    with paper_style(width="double", base_pt=10.0, aspect=0.42) as st:
        fig, (a, b) = st.figure(1, 2)

        for j, m in enumerate(MODES):
            T = np.array([r["T_cpi_s"] for r in sw[m]], float)
            y = np.array([r["blind_hard"] for r in sw[m]], float)
            a.plot(T, y, label=f"{SHORT[m]} (1.5-bin guard)", markevery=24,
                   **st.series(j))
        Tg = np.array([r["T_cpi_s"] for r in sw["G1"]], float)
        yg = np.array([r["blind_declared"] for r in sw["G1"]], float)
        a.plot(Tg, yg, label="5G NR (2.5-bin guard)", markevery=24, **st.series(3))
        a.axvline(ref_T, color="black", linewidth=0.9, linestyle=":")
        a.annotate("CPI of the headline\nresult, 0.1 s", (ref_T, 0.80),
                   textcoords="offset points", xytext=(5, 0), ha="left")
        a.set_xscale("log")
        _plain_log(a, "x", [0.01, 0.1, 1, 10])
        a.set_xlabel("coherent processing interval [s]")
        a.set_ylabel("blind heading fraction")
        a.set_ylim(-0.03, 1.05)
        a.set_title("(a) The 5G penalty is a CPI-dependent trade")
        a.legend(loc="center right", frameon=True, framealpha=0.92,
                 edgecolor="none")

        v = np.array([r["speed_ms"] for r in cost["by_speed"]], float)
        tc = np.array([r["T_coh_s"] for r in cost["by_speed"]], float)
        b.plot(v, tc, label="coherence limit (one range and\none Doppler bin)",
               **st.series(0))
        for k, (name, lab) in enumerate((("to_LTE_parity", "CPI for LTE parity"),
                                         ("to_WiFi_parity", "CPI for WiFi parity"))):
            b.axhline(float(cost["required_cpi_s"][name]), color="black",
                      linewidth=0.9, linestyle=("--", "-.")[k])
            b.annotate(lab, (v[0], float(cost["required_cpi_s"][name])),
                       textcoords="offset points", xytext=(2, 3), ha="left")
        b.set_yscale("log")
        _plain_log(b, "y", [0.1, 0.3, 1, 3, 10, 30])
        b.set_xlabel("target speed [m/s]")
        b.set_ylabel("time [s]")
        b.set_title("(b) What buying that CPI costs")
        b.legend(loc="upper right", frameon=True, framealpha=0.92,
                 edgecolor="none")

    return save_figure(
        fig, f"{FIG}/report05_pf4_cpi", dpi=400, placed_width_in=7.16,
        title="5G always-on reference penalty as a CPI sweep",
        caption="The 5G always-on-reference penalty presented as a CPI sweep rather "
                "than a single point. The SSB repetition rate of 50 Hz folds the "
                "Doppler axis, so at the 0.1 s CPI used for the headline the blind "
                "heading fraction is 0.64 under the 1.5-bin guard the detector "
                "actually applies and 1.00 under the 2.5-bin declared guard (a). "
                "Lengthening the CPI recovers coverage, and the CPI needed to reach "
                "LTE parity stays below the coherence limit for target speeds up to "
                "30 m/s while costing 3.75 times the revisit interval (b).")


# --------------------------------------------------------------------------- #
#  PF5 — 수신소자를 늘리면 이득이 어디까지 오르나?
# --------------------------------------------------------------------------- #
def pf5_multirx():
    """수신소자 N 의 측정 이득은 열잡음 코히어런트 상한 10log₁₀N 과 얼마나 다른가?"""
    D = _load("detection_rx_sweep.json")
    modes = list(D["meta"]["modes"])
    ns = [int(n) for n in D["meta"]["n_list"]]

    with paper_style(width="double", base_pt=10.0, aspect=0.42) as st:
        fig, (a, b) = st.figure(1, 2)

        for j, m in enumerate(MODES):
            s = [float(D["modes"][m]["curves"][str(n)]["snr50"]) for n in ns]
            a.plot(ns, [s[0] - v for v in s], label=SHORT[m], **st.series(j))
        a.plot(ns, 10 * np.log10(np.array(ns, float)), color="black",
               linewidth=1.2, linestyle="--", label="10 log10 N upper bound")
        a.set_xticks(ns)
        a.set_xlabel("receive elements N (λ/2 ULA, one site)")
        a.set_ylabel("sensitivity gain [dB]")
        a.set_title("(a) Measured gain against the\nidealised coherent bound")
        a.legend(loc="upper left")

        ex = []
        for m in modes:
            s = [float(D["modes"][m]["curves"][str(n)]["snr50"]) for n in ns]
            ex.append([(s[0] - v) - 10 * np.log10(n) for v, n in zip(s, ns)])
        ex = np.array(ex)
        b.boxplot([ex[:, i] for i in range(len(ns))],
                  tick_labels=[str(n) for n in ns], widths=0.5)
        b.axhline(0.0, color="black", linewidth=1.0)
        b.set_xlabel("receive elements N")
        b.set_ylabel("measured gain − 10 log10 N [dB]")
        b.set_title(f"(b) Excess over the bound,\nall {len(modes)} waveform modes")

    return save_figure(
        fig, f"{FIG}/report05_pf5_multirx", dpi=400, placed_width_in=7.16,
        title="Multi-receiver gain against the idealised coherent bound",
        caption="Multi-receiver gain measured against the idealised coherent bound. "
                "The bound 10 log10 N is the array gain available against thermal "
                "noise alone, with perfect steering onto the true target direction and "
                "no coupling or calibration error (a). The measured gain exceeds that "
                "bound because the clutter-cancellation residual is independent of N, "
                "so coherent combining raises the target against the residual as well; "
                "the excess spans -0.11 to +0.47 dB over all nine waveform modes and "
                "the largest value is 11 times the Monte-Carlo standard deviation of "
                "the 50 percent detection point (b).")


# --------------------------------------------------------------------------- #
#  PF6 — 교정된 오경보율 위에서 각 파형이 요구하는 SNR 은?
# --------------------------------------------------------------------------- #
def pf6_detector():
    """교정된 오경보율 위에서 세 파형이 Pd=0.5 에 요구하는 SNR 은 몇 dB 인가?"""
    D = _load("detection_rx_sweep.json")
    order = ("W1", "W2", "W3", "L1", "L2", "L3", "G1", "G2", "G3")

    with paper_style(width="double", base_pt=10.0, aspect=0.42) as st:
        fig, (a, b) = st.figure(1, 2)

        for j, m in enumerate(MODES):
            g = np.array(D["modes"][m]["snr_grid"], float)
            p = np.array(D["modes"][m]["curves"]["1"]["Pd"], float)
            a.plot(g, p, label=SHORT[m], markevery=3, **st.series(j))
        a.axhline(0.5, color="black", linewidth=0.9, linestyle=":")
        a.set_xlabel("range-Doppler output SNR [dB]")
        a.set_ylabel("Pd")
        a.set_ylim(-0.02, 1.04)
        a.set_title("(a) Detection curves at an empirically\ncalibrated false-alarm rate")
        a.legend(loc="upper left")

        x = np.arange(3, dtype=float)
        w = 0.26
        for j, std in enumerate(("W", "L", "G")):
            vals = [float(D["modes"][f"{std}{k}"]["curves"]["1"]["snr50"])
                    for k in (1, 2, 3)]
            b.bar(x + (j - 1) * w, vals, w, label=SHORT[MODES[j]], **_band_style(j))
        b.set_xticks(x)
        b.set_xticklabels(["always-on\n(grade 1)", "grade 2", "session\n(grade 3)"])
        b.set_ylabel("SNR at Pd = 0.5 [dB]")
        b.set_ylim(0, 18)
        b.set_title("(b) Cost of restricting the receiver\nto always-on reference signals")
        b.legend(loc="upper right", ncol=3)

    return save_figure(
        fig, f"{FIG}/report05_pf6_detector", dpi=400, placed_width_in=7.16,
        title="Detection curves and the always-on reference cost",
        caption="Detection performance on one target, one geometry and one detector, "
                "with the threshold set from an empirically calibrated false-alarm "
                "rate (a). Restricting a 5G receiver to the always-on SSB instead of "
                "the session-scheduled positioning reference costs 3.82 dB of "
                "sensitivity and coarsens bistatic range resolution from 3.05 m to "
                "41.64 m, while the same restriction costs WiFi 0.21 dB and LTE "
                "0.08 dB (b).")


# --------------------------------------------------------------------------- #
#  PF7 — 앵커 뒤의 밴드 격차는 앵커 자신의 미통제 항보다 큰가?
# --------------------------------------------------------------------------- #
def pf7_anchor():
    """기울기 앵커가 옮긴 밴드 격차는 앵커 자신의 미통제 항보다 큰가?"""
    FS, AN = _load("report13_freespace.json"), _load("sigma_anchor.json")
    with paper_style(width="double", base_pt=10.0, aspect=0.42) as st:
        fig, (a, b) = st.figure(1, 2)

        x = np.arange(len(DRONES), dtype=float)
        w = 0.26
        for j, m in enumerate(MODES):
            d = [float(AN["drones"][dr]["modes"]["slope_only"]["delta_db"]
                       [ANCHOR_BAND[m]]) for dr in DRONES]
            a.bar(x + (j - 1) * w, d, w, label=SHORT[m], **_band_style(j))
        a.axhline(0.0, color="black", linewidth=0.8)
        a.set_xticks(x)
        a.set_xticklabels([DLAB[d] for d in DRONES], rotation=22, ha="right")
        a.set_ylabel("Δσ applied by the slope anchor [dB]")
        a.set_title("(a) The anchor moves each band by a scalar")
        a.legend(loc="upper left", ncol=1, frameon=True, framealpha=0.92,
                 edgecolor="none")

        spread, unc = [], []
        for dr in DRONES:
            R, n = [], []
            for m in MODES:
                c = _cell(FS, dr, m)
                dd = float(AN["drones"][dr]["modes"]["slope_only"]["delta_db"]
                           [ANCHOR_BAND[m]])
                nl = float(c["n_local_at_R90"])
                R.append(float(c["R90_C50_m"]) * 10 ** (dd / (10 * nl)))
                n.append(nl)
            spread.append(10 * float(np.mean(n)) * np.log10(max(R) / min(R)))
            unc.append(float(AN["drones"][dr]["comparability"]["size_law_spread_db"]))
        y = np.arange(len(DRONES), dtype=float)
        h = 0.36
        b.barh(y + h / 2, spread, h, label="band spread after anchoring",
               **_band_style(0))
        b.barh(y - h / 2, unc, h, label="anchor size-transfer term",
               **_band_style(1))
        b.set_yticks(y)
        b.set_yticklabels([DLAB[d] for d in DRONES])
        b.invert_yaxis()
        b.set_xlabel("σ-equivalent [dB]")
        b.set_title("(b) Band gap against the anchor's\nown uncontrolled term")
        b.legend(loc="center right", frameon=True, framealpha=0.92,
                 edgecolor="none")

    return save_figure(
        fig, f"{FIG}/report05_pf7_anchor", dpi=400, placed_width_in=7.16,
        title="Slope anchoring and the anchor's own uncontrolled term",
        caption="Slope anchoring applies one scalar per band per airframe, preserving "
                "the computed aspect pattern and the three-band mean level (a). The "
                "resulting band-to-band spread is compared with the size-transfer term "
                "the anchor itself leaves open, which is the quantity that decides "
                "whether an airframe is comparable to the measured reference "
                "platform (b).")


ALL = (pf1_gap, pf2_ranking, pf3_robust, pf4_cpi, pf5_multirx, pf6_detector,
       pf7_anchor)


def main():
    print("리포트 05 게재규격 그림 (입력은 outputs/*.json, 실험 재실행 없음)")
    for fn in ALL:
        r = fn()
        chk = r.get("check", {})
        print(f"  저장: {r['pdf']}  (글자 최소 {chk.get('min_font_pt')} pt · "
              f"PNG {chk.get('png_dpi')} dpi · 판정 {'OK' if chk.get('ok') else 'NG'})")
    print(f"완료 — {len(ALL)}장")


if __name__ == "__main__":
    main()
