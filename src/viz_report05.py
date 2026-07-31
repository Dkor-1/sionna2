# -*- coding: utf-8 -*-
"""
viz_report05.py — 리포트 05(검출 결과)의 그림 8장을 만든다
==========================================================================
입력은 전부 `outputs/*.json` 이고, 이 스크립트는 **읽기만** 한다(실험을 다시 돌리지 않는다).

    PYTHONPATH=src ~/.venvs/py312/bin/python src/viz_report05.py

출력: `outputs/figures/report05_f{1..8}_*.png`

하우스 규약 — **그림 안의 글자는 전부 영어**(제목·축·범례·주석). 산문·주석·print 는 한국어.
저장 직전에 `report_style.assert_fig_text()` 로 그 규약을 강제한다(한글이 섞이면 예외).

그림 1장 = 질문 1개. 각 함수의 docstring 첫 줄이 그 질문이다.
"""
from __future__ import annotations

import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from report_style import assert_fig_text                              # noqa: E402

ROOT = os.path.abspath(os.path.join(_HERE, ".."))
OUT = os.path.join(ROOT, "outputs")
FIG = os.path.join(OUT, "figures")

# 파형 3종 = 상시 기준신호 모드(각 표준의 G1). 색은 전 그림에서 고정한다.
MODES = ("W1", "L1", "G1")
MODE_LABEL = {"W1": "WiFi 5.2 GHz (VHT-LTF)",
              "L1": "LTE 1.8 GHz (CRS)",
              "G1": "5G NR 3.5 GHz (SSB)"}
MODE_SHORT = {"W1": "WiFi", "L1": "LTE", "G1": "5G"}
MODE_C = {"W1": "#1565c0", "L1": "#2e7d32", "G1": "#c62828"}
DRONE_LABEL = {"mini5pro": "Mini 5 Pro", "mavic4pro": "Mavic 4 Pro",
               "matrice4e": "Matrice 4E", "phantom4": "Phantom 4",
               "s1000plus": "S1000+"}
DRONE_ORDER = ("mini5pro", "mavic4pro", "matrice4e", "phantom4", "s1000plus")

plt.rcParams.update({"figure.facecolor": "white", "savefig.facecolor": "white",
                     "axes.grid": True, "grid.alpha": 0.3, "font.size": 10,
                     "axes.titlesize": 11, "figure.dpi": 130})


def _load(name):
    with open(os.path.join(OUT, name), encoding="utf-8") as f:
        return json.load(f)


def _texts(fig):
    """그림 안의 모든 문자열을 긁어모은다(제목·축·눈금·범례·주석) — 영어 검사용."""
    out = []
    for ax in fig.get_axes():
        out += [ax.get_title(), ax.get_xlabel(), ax.get_ylabel()]
        out += [t.get_text() for t in ax.texts]
        out += [t.get_text() for t in ax.get_xticklabels()]
        out += [t.get_text() for t in ax.get_yticklabels()]
        lg = ax.get_legend()
        if lg:
            out += [t.get_text() for t in lg.get_texts()]
    out += [t.get_text() for t in fig.texts]
    return [s for s in out if s]


def _save(fig, name):
    assert_fig_text(*_texts(fig))          # 하우스 규약: 그림 글자는 영어만
    os.makedirs(FIG, exist_ok=True)
    p = os.path.join(FIG, name)
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    print(f"  저장: outputs/figures/{name}")
    return p


# --------------------------------------------------------------------------- #
#  F1 — 기하: 헤드라인 거리에서 바이스태틱 각이 유효창(β≤45°) 안에 있나?
# --------------------------------------------------------------------------- #
def f1_geometry():
    FS = _load("report13_freespace.json")
    S = FS["solve"]["W1"]
    d = np.array(S["d_grid_m"]); beta = np.array(S["beta_deg"])
    el = np.array(S["el_look_deg"]); snr = np.array(S["snr_d_db"])
    R90 = float(S["R_m"])
    d45 = float(np.interp(45.0, beta[::-1], d[::-1]))       # β=45° 를 넘는 지점
    snr45 = float(np.interp(d45, d, snr))

    fig, (a, b) = plt.subplots(1, 2, figsize=(12.4, 4.6))

    # (a) 평면 배치 — 좌표는 `src/freespace_scene.py:72` 의 선언 상수에서 읽는다
    from freespace_scene import FS_RX_H, FS_TX
    L = float(S["L_m"])
    a.plot([0], [0], "^", ms=12, color="#c62828",
           label=f"TX illuminator ({FS_TX[0]:.0f}, {FS_TX[1]:.0f}, {FS_TX[2]:.0f} m)")
    a.plot([L], [0], "v", ms=12, color="#1565c0",
           label=f"RX passive ({L:.0f}, 0, {FS_RX_H:.0f} m)")
    a.plot([L / 2], [0], "o", ms=5, color="0.35", label="midpoint O")
    for dd, ls in ((1000.0, "-"), (2000.0, "--")):
        tx, ty = L / 2, dd
        a.plot([0, tx], [0, ty], ls, lw=1.2, color="0.5")
        a.plot([L, tx], [0, ty], ls, lw=1.2, color="0.5")
        a.plot([tx], [ty], "*", ms=13, color="#ef6c00")
        bb = float(np.interp(dd, d, beta))
        a.annotate(f"target at d = {dd:.0f} m\n" + r"$\beta$ = " + f"{bb:.1f}" + r"$^\circ$",
                   (tx, ty), textcoords="offset points", xytext=(12, -4), fontsize=9)
    a.annotate("R1", (10, 780), fontsize=9, color="0.3")
    a.annotate("R2", (520, 780), fontsize=9, color="0.3")
    a.set_xlim(-700, 1700); a.set_ylim(-350, 2950)
    a.set_aspect("equal")
    a.set_xlabel("x [m]"); a.set_ylabel("y [m]  (target offset d from midpoint)")
    a.set_title(f"(a) Layout: baseline L = {L:.0f} m, scene azimuth "
                + r"$\varphi$ = " + f"{float(S['phi_deg']):.0f}" + r"$^\circ$"
                + f", altitude {float(S['alt_m']):.0f} m")
    a.legend(loc="upper left", fontsize=8.5)

    # (b) β(d) · |el|(d) — β>45° 인 근거리 구간을 해칭
    b.semilogx(d, beta, color="#6a1b9a", lw=2, label=r"bistatic angle $\beta$")
    b.semilogx(d, np.abs(el), color="#00838f", lw=2, ls="--",
               label=r"|bisector elevation| (looking up at the belly)")
    b.axhline(45, color="k", lw=1, ls=":")
    b.axvspan(d[0], d45, color="#c62828", alpha=0.12)
    b.annotate(r"$\beta$ > 45$^\circ$: outside the validated window" + "\n"
               + f"(d < {d45:.0f} m, where SNR is already {snr45:.0f} dB)",
               (700, 58), fontsize=9, color="#8e1a1a")
    b.axvline(R90, color="#ef6c00", lw=1.6)
    b.annotate(f"headline R90 = {R90 / 1000:.1f} km\n"
               + r"$\beta$ = " + f"{float(np.interp(R90, d, beta)):.1f}" + r"$^\circ$",
               (R90 * 0.36, 20), fontsize=9, color="#a35200")
    b.set_xlabel("horizontal range d from midpoint [m]")
    b.set_ylabel("angle [deg]")
    b.set_ylim(0, 125)
    b.set_title(r"(b) $\beta$ and elevation versus range")
    b.legend(loc="upper right", fontsize=9)

    fig.suptitle("Free-space passive bistatic geometry — the headline range sits at "
                 r"$\beta \approx 3^\circ$", y=1.01)
    return _save(fig, "report05_f1_geometry.png")


# --------------------------------------------------------------------------- #
#  F2 — 감도사슬: 1 km 에서의 출력 SNR 은 어떤 항들의 합인가?
# --------------------------------------------------------------------------- #
def f2_budget():
    FS = _load("report13_freespace.json")
    drone = "mavic4pro"
    keys = ["eirp", "grx", "lambda2", "sigma", "spread", "n0", "t_cpi",
            "eta_ref", "duty", "losses", "k_mode"]
    nice = {"eirp": "EIRP", "grx": "RX gain", "lambda2": r"$\lambda^2$",
            "sigma": r"$\sigma$", "spread": "spread $1/(4\\pi)^3R_1^2R_2^2$",
            "n0": r"$1/N_0$", "t_cpi": "CPI gain", "eta_ref": "ref. efficiency",
            "duty": "duty", "losses": "losses", "k_mode": "mode calib."}
    fig, axes = plt.subplots(1, 3, figsize=(13.6, 4.4), sharey=True)
    for ax, m in zip(axes, MODES):
        t = FS["ranges"][drone][m]["equal_psd"]["full_waveform_capture"]["by_N"]["1"]
        B = t["budget_terms_db"]
        vals = [float(B[k]) for k in keys]
        cum = np.cumsum(vals)
        x = np.arange(len(keys))
        for i, (v, c) in enumerate(zip(vals, cum)):
            base = c - v
            ax.bar(i, v, bottom=base, color=("#2e7d32" if v >= 0 else "#c62828"),
                   alpha=0.85, width=0.68)
        ax.plot(x, cum, "o-", color="0.25", ms=3, lw=1)
        ax.axhline(0, color="k", lw=0.8)
        ax.bar(len(keys), float(B["total"]), color="#ef6c00", width=0.68)
        ax.set_xticks(list(x) + [len(keys)])
        ax.set_xticklabels([nice[k] for k in keys] + ["output SNR"],
                           rotation=60, ha="right", fontsize=8)
        ax.set_title(f"{MODE_LABEL[m]}\noutput SNR = {float(B['total']):.1f} dB "
                     f"at d = {float(B['d_ref_m']):.0f} m")
    axes[0].set_ylabel("dB (bars = term, line = running total)")
    lb = FS["meta"]["link_budget"]                    # 선언값은 JSON 에서 읽는다
    fig.suptitle(f"Sensitivity chain for {DRONE_LABEL[drone]} — declared budget: "
                 f"EIRP {lb['eirp_dbm']:.0f} dBm, RX {lb['rx_gain_dbi']:.0f} dBi, "
                 f"NF {lb['noise_figure_db']:.0f} dB, "
                 f"CPI {FS['solve']['W1']['T_cpi_s'] * 1e3:.0f} ms, 1 receiver", y=1.03)
    return _save(fig, "report05_f2_budget.png")


# --------------------------------------------------------------------------- #
#  F3 — 검출기 전달함수: 각 파형이 Pd=0.9 에 필요한 출력 SNR 은 몇 dB 인가?
# --------------------------------------------------------------------------- #
def f3_detector():
    FS = _load("report13_freespace.json")
    fig, ax = plt.subplots(figsize=(7.6, 5.0))
    txt = []
    for i_m, m in enumerate(MODES):
        cell = FS["detector_transfer"]["S_G"][m]["N"]["1"]["dopoff"]["3"]
        if cell.get("skipped"):
            txt.append(f"{MODE_SHORT[m]}: NOT MEASURABLE — {cell['reason']}")
            continue
        g = np.array(cell["snr_grid_db"]); p = np.array(cell["Pd"])
        lo = np.array(cell["wilson_lo"]); hi = np.array(cell["wilson_hi"])
        ax.plot(g, p, "o-", ms=4, color=MODE_C[m], label=MODE_LABEL[m])
        ax.fill_between(g, lo, hi, color=MODE_C[m], alpha=0.18)
        s90 = float(np.interp(0.9, p, g))
        ax.plot([s90], [0.9], "k|", ms=14)
        ax.annotate(f"{MODE_SHORT[m]} needs {s90:.2f} dB", (s90, 0.9),
                    textcoords="offset points", xytext=(8, -16 - 16 * i_m),
                    fontsize=9, color=MODE_C[m])
    pf = FS["threshold"]["pfa"]
    ax.axhline(0.9, color="k", lw=0.9, ls=":")
    ax.set_xlabel("range-Doppler output SNR [dB]   (peak$^2$ / mean noise-cell power)")
    ax.set_ylabel(r"$P_d$")
    ax.set_ylim(-0.02, 1.03)
    ax.legend(loc="upper left", fontsize=9)
    note = (f"empirical $P_{{fa}}$ at the operating threshold: "
            f"WiFi {pf['W1']['empirical']:.2e} | LTE {pf['L1']['empirical']:.2e} | "
            f"5G {pf['G1']['empirical']:.2e}   (target 1e-4)")
    ax.annotate(note + ("\n" + "\n".join(txt) if txt else ""),
                (0.02, 0.02), xycoords="axes fraction", fontsize=8.5,
                va="bottom", color="0.2")
    ax.set_title("Detector transfer measured in free space, "
                 "Monte-Carlo with calibrated false-alarm rate")
    return _save(fig, "report05_f3_detector.png")


# --------------------------------------------------------------------------- #
#  F4 — R90 행렬: 공칭 자세에서 기종별로 몇 m 까지 보이나?
# --------------------------------------------------------------------------- #
def f4_range_bars():
    FS = _load("report13_freespace.json")
    fig, ax = plt.subplots(figsize=(9.6, 4.8))
    w = 0.26
    xs = np.arange(len(DRONE_ORDER))
    for j, m in enumerate(MODES):
        r = [FS["ranges"][dr][m]["equal_psd"]["full_waveform_capture"]
             ["by_N"]["1"]["R90_C50_m"] / 1000.0 for dr in DRONE_ORDER]
        blind = [FS["ranges"][dr][m]["equal_psd"]["full_waveform_capture"]
                 ["by_N"]["1"]["blind_heading_frac"] for dr in DRONE_ORDER]
        hatch = "///" if min(blind) >= 1.0 else None
        ax.bar(xs + (j - 1) * w, r, w, color=MODE_C[m], alpha=0.88,
               hatch=hatch, edgecolor="white",
               label=MODE_LABEL[m] + (" — blind at every heading" if hatch else ""))
        for x, v in zip(xs + (j - 1) * w, r):
            ax.annotate(f"{v:.1f}", (x, v), ha="center", va="bottom", fontsize=8)
    ax.set_xticks(xs); ax.set_xticklabels([DRONE_LABEL[d] for d in DRONE_ORDER])
    ax.set_ylabel("R90 at nominal aspect [km]")
    ax.set_ylim(0, 11.8)
    ax.legend(loc="upper left", fontsize=8.5)
    ax.set_title("Range at which $P_d$ = 0.9, one receiver, declared budget")
    ax.annotate("Bars use our own $\\sigma$ level. Read the band-to-band comparison "
                "on anchored $\\sigma$ only (Fig. 8), never off this panel.",
                (0.5, -0.19), xycoords="axes fraction", ha="center",
                fontsize=9, color="#8e1a1a")
    return _save(fig, "report05_f4_range_bars.png")


# --------------------------------------------------------------------------- #
#  F5 — 헤딩 의존성: R90 한 숫자가 표적 헤딩 평균에서도 살아남나?
# --------------------------------------------------------------------------- #
def f5_heading():
    FS = _load("report13_freespace.json")
    drone = FS["solve"]["W1"]["drone"]
    fig = plt.figure(figsize=(11.8, 4.8))
    ax1 = fig.add_subplot(1, 2, 1, projection="polar")
    for m in MODES:
        hp = FS["solve"][m]["heading_polar"]
        psi = np.radians(np.array(hp["psi_deg"], dtype=float))
        r = np.array(hp["R90_m"], dtype=float) / 1000.0
        blind = np.array(hp["blind"], dtype=bool)
        r = np.where(blind, np.nan, r)
        psi = np.append(psi, psi[0]); r = np.append(r, r[0])
        ax1.plot(psi, r, lw=1.8, color=MODE_C[m], label=MODE_SHORT[m])
    ax1.set_title(f"(a) R90 [km] versus target heading $\\psi$\n"
                  f"({DRONE_LABEL[drone]}; gaps = Doppler-blind headings)", pad=26)
    ax1.legend(loc="lower left", bbox_to_anchor=(-0.16, -0.10), fontsize=9)
    fig.text(0.5, -0.04, "5G NR SSB is absent from both panels: it is Doppler-blind at "
                         "EVERY heading (PRF 50 Hz gives M = 5, and the zero-Doppler "
                         "guard covers the whole folded axis).",
             ha="center", fontsize=9, color="#8e1a1a")

    ax2 = fig.add_subplot(1, 2, 2)
    xs = np.arange(len(DRONE_ORDER)); w = 0.26
    for j, m in enumerate(MODES):
        e = [FS["ranges"][dr][m]["equal_psd"]["full_waveform_capture"]
             ["by_N"]["1"]["E_psi_Pd_at_R90"] for dr in DRONE_ORDER]
        ax2.bar(xs + (j - 1) * w, e, w, color=MODE_C[m], alpha=0.88,
                label=MODE_SHORT[m])
    ax2.axhline(0.9, color="k", ls=":", lw=1)
    ax2.annotate("$P_d$ = 0.9 claimed at the nominal aspect", (0.02, 0.90),
                 xycoords="axes fraction", fontsize=9)
    ax2.set_xticks(xs)
    ax2.set_xticklabels([DRONE_LABEL[d] for d in DRONE_ORDER], rotation=18,
                        ha="right", fontsize=9)
    ax2.set_ylabel(r"heading-averaged $P_d$ at that same R90")
    ax2.set_ylim(0, 1.0)
    ax2.legend(fontsize=9)
    ax2.set_title("(b) The same range, averaged uniformly over heading")
    fig.suptitle("R90 is a single-aspect number; averaged over heading it collapses",
                 y=1.08)
    return _save(fig, "report05_f5_heading.png")


# --------------------------------------------------------------------------- #
#  F6 — 다중 수신기: 수신기를 더 붙이면 감도가 얼마나 오르나?
# --------------------------------------------------------------------------- #
def f6_multirx():
    D = _load("detection_rx_sweep.json")
    modes = D["meta"]["modes"]
    ns = [int(n) for n in D["meta"]["n_list"]]
    fig, (a, b) = plt.subplots(1, 2, figsize=(12.2, 4.6))

    for m in modes:
        c = D["modes"][m]["curves"]
        s = [float(c[str(n)]["snr50"]) for n in ns]
        gain = [s[0] - v for v in s]
        col = MODE_C.get(m, None) or MODE_C[{"W": "W1", "L": "L1", "G": "G1"}[m[0]]]
        a.plot(ns, gain, "o-", ms=4, lw=1.2, color=col, alpha=0.75)
    a.plot(ns, 10 * np.log10(np.array(ns, float)), "k--", lw=2,
           label=r"coherent array gain against thermal noise  $10\log_{10}N$")
    for lab, m in (("WiFi", "W1"), ("LTE", "L1"), ("5G", "G1")):
        a.plot([], [], color=MODE_C[m], lw=2, label=f"{lab} (3 occupancy modes)")
    a.set_xticks(ns)
    a.set_xlabel(r"surveillance ULA elements N (one site, $\lambda$/2 spacing)")
    a.set_ylabel(r"sensitivity gain: SNR50(1) $-$ SNR50(N)  [dB]")
    a.legend(fontsize=9, loc="upper left")
    a.set_title("(a) Measured gain versus the thermal-noise reference line")

    ex = []
    for m in modes:
        c = D["modes"][m]["curves"]
        s = [float(c[str(n)]["snr50"]) for n in ns]
        ex.append([(s[0] - v) - 10 * np.log10(n) for v, n in zip(s, ns)])
    ex = np.array(ex)
    b.boxplot([ex[:, i] for i in range(len(ns))], tick_labels=[str(n) for n in ns],
              widths=0.5)
    b.axhline(0, color="k", lw=1)
    b.set_xlabel(r"surveillance ULA elements N (one site, $\lambda$/2 spacing)")
    b.set_ylabel("measured gain $-$ $10\\log_{10}N$  [dB]")
    b.set_title(f"(b) Excess over the reference line, all {len(modes)} modes\n"
                "(the ECA residual is N-independent, so the target also gains on it)")
    fig.suptitle("Element gain is exact phase alignment on the true target direction; "
                 r"$10\log_{10}N$ bounds the thermal-noise part only", y=1.03)
    fig.text(0.5, -0.06, "Relative gain only. The absolute SNR50 comes from a "
                         "short-baseline bench geometry, not from the free-space layout "
                         "of Fig. 1.", ha="center", fontsize=9, color="0.25")
    return _save(fig, "report05_f6_multirx.png")


# --------------------------------------------------------------------------- #
#  F7 — 어느 벽이 거리를 정하나: 열잡음 · ADC · 직접파 잔차 · 거리워크?
# --------------------------------------------------------------------------- #
def f7_walls():
    FS = _load("report13_freespace.json")
    base = FS["sensitivity"]["baseline"]
    ref = FS["sensitivity"]["baseline_meta"]["ref_drone"]
    order = [("wifi", "W1"), ("lte", "L1"), ("nr", "G1")]
    fig, axes = plt.subplots(1, 3, figsize=(13.4, 4.3), sharey=True)
    for ax, (std, m) in zip(axes, order):
        e = base[std]
        L = np.array(e["L_m"], float)
        for key, lab, c, ls in (("R_thermal_m", "thermal noise", "#1565c0", "-"),
                                ("R_adc_m", "ADC dynamic range", "#2e7d32", "--"),
                                ("R_dpi60_m", "direct-path residual (60 dB ECA)",
                                 "#c62828", "-."),
                                ("R_walk_m", "range walk", "#ef6c00", ":")):
            ax.loglog(L, np.array(e[key], float) / 1000.0, ls, lw=1.9, color=c,
                      label=lab)
        binding = np.min(np.vstack([np.array(e[k], float) for k in
                                    ("R_thermal_m", "R_adc_m", "R_dpi60_m",
                                     "R_walk_m")]), axis=0) / 1000.0
        ax.loglog(L, binding, color="k", lw=3, alpha=0.30, label="binding wall")
        ax.set_xlabel("baseline L [m]")
        ax.set_title(f"{e['band']}")
    axes[0].set_ylabel("detection range [km]")
    axes[0].legend(fontsize=8.5, loc="lower right")
    fig.suptitle(f"Which limit binds, and where — reference airframe "
                 f"{DRONE_LABEL.get(ref, ref)}, "
                 "direct-path residual dominates at short baselines", y=1.04)
    return _save(fig, "report05_f7_walls.png")


# --------------------------------------------------------------------------- #
#  F8 — 밴드 비교: 앵커 σ 위에서 밴드 격차가 파형의 우열로 남나?
# --------------------------------------------------------------------------- #
#: 앵커 JSON 의 밴드 키 ↔ 검출 모드 코드
ANCHOR_BAND = {"W1": "WiFi 5.21 GHz", "L1": "LTE 1.843 GHz", "G1": "5G 3.5 GHz"}


def anchored_ranges():
    """R90(원 σ) → R90(앵커 σ). 국소 지수 n_local 로 1차 전이한다.

    d 축에서 R ∝ σ^(1/4) 는 전역적으로 성립하지 않는다(`src/freespace_scene.py:76`).
    그래서 전역 4 승이 아니라 **JSON 이 들고 있는 R90 근방의 국소 지수**를 쓴다.
    """
    FS = _load("report13_freespace.json")
    AN = _load("sigma_anchor.json")
    out = {}
    for dr in DRONE_ORDER:
        row = {}
        for m in MODES:
            c = FS["ranges"][dr][m]["equal_psd"]["full_waveform_capture"]["by_N"]["1"]
            R, n = float(c["R90_C50_m"]), float(c["n_local_at_R90"])
            dd = float(AN["drones"][dr]["modes"]["slope_only"]["delta_db"][ANCHOR_BAND[m]])
            row[m] = dict(raw_km=R / 1e3, anch_km=R / 1e3 * 10 ** (dd / (10 * n)),
                          delta_db=dd, n_local=n)
        out[dr] = row
    return out, AN


def f8_anchored_bands():
    R, AN = anchored_ranges()
    fig, (a, b) = plt.subplots(1, 2, figsize=(12.8, 4.7),
                               gridspec_kw={"width_ratios": [1.55, 1.0]})

    FS = _load("report13_freespace.json")
    xs = np.arange(len(DRONE_ORDER)); w = 0.26
    for j, m in enumerate(MODES):
        pos = xs + (j - 1) * w
        blind = min(FS["ranges"][d][m]["equal_psd"]["full_waveform_capture"]
                    ["by_N"]["1"]["blind_heading_frac"] for d in DRONE_ORDER)
        hatch = "///" if blind >= 1.0 else None
        a.bar(pos, [R[d][m]["anch_km"] for d in DRONE_ORDER], w, color=MODE_C[m],
              alpha=0.9, hatch=hatch, edgecolor="white",
              label=MODE_LABEL[m] + (" — blind at every heading" if hatch
                                     else " (anchored)"))
        a.plot(pos, [R[d][m]["raw_km"] for d in DRONE_ORDER], "_", ms=13, mew=2.2,
               color="0.15")
    a.plot([], [], "_", ms=13, mew=2.2, color="0.15", label="same cell before anchoring")
    a.set_xticks(xs); a.set_xticklabels([DRONE_LABEL[d] for d in DRONE_ORDER],
                                        rotation=15, ha="right", fontsize=9)
    a.set_ylabel("R90 [km], one receiver")
    a.legend(fontsize=8.2, loc="upper left", ncol=2)
    a.set_ylim(0, 14.5)
    a.set_title("(a) Anchoring moves each band by a scalar; the ordering does not settle")

    # (b) 밴드 격차 vs 앵커 자신의 미통제 항 — 어느 쪽이 큰가
    lab, spread, unc, verdict = [], [], [], []
    for d in DRONE_ORDER:
        r = [R[d][m]["anch_km"] for m in MODES]
        n = np.mean([R[d][m]["n_local"] for m in MODES])
        spread.append(10 * n * np.log10(max(r) / min(r)))          # σ 등가 dB
        unc.append(float(AN["drones"][d]["comparability"]["size_law_spread_db"]))
        verdict.append(AN["drones"][d]["comparability"]["verdict"])
        lab.append(DRONE_LABEL[d])
    y = np.arange(len(lab))
    b.barh(y + 0.19, spread, 0.36, color="#455a64", label="band spread after anchoring")
    b.barh(y - 0.19, unc, 0.36, color="#c62828", alpha=0.85,
           label="anchor size-transfer term (unresolved)")
    for i, v in enumerate(verdict):
        inside = unc[i] > 3.0
        b.annotate(v, (unc[i] + (-0.3 if inside else 0.3), y[i] - 0.19),
                   va="center", ha="right" if inside else "left", fontsize=8,
                   color="white" if inside else "#8e1a1a")
    b.set_yticks(y); b.set_yticklabels(lab, fontsize=9)
    b.invert_yaxis()
    b.set_xlim(0, max(max(spread), max(unc)) * 1.35)
    b.set_xlabel(r"$\sigma$-equivalent [dB]")
    b.legend(fontsize=8.2, loc="center right", framealpha=0.95)
    b.set_title("(b) Is the band gap bigger than the anchor's own\nuncontrolled term?")
    sl = float(AN["drones"]["phantom4"]["modes"]["slope_only"]["slope_anchor_db_per_ghz"])
    fig.suptitle("Band-to-band comparison on anchored "
                 r"$\sigma$ — every airframe is put on the measured slope "
                 f"{sl:.3f} dB/GHz", y=1.03)
    return _save(fig, "report05_f8_anchored_bands.png")


ALL = (f1_geometry, f2_budget, f3_detector, f4_range_bars,
       f5_heading, f6_multirx, f7_walls, f8_anchored_bands)


def main():
    print("리포트 05 그림 생성 (입력은 outputs/*.json, 실험 재실행 없음)")
    for fn in ALL:
        fn()
    print(f"완료 — {len(ALL)}장")


if __name__ == "__main__":
    main()
