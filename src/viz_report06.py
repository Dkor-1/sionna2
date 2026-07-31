# -*- coding: utf-8 -*-
"""viz_report06.py — 리포트 06(실측 계약) 그림 4장

하우스 규약: **그림 안의 글자는 전부 영어**(제목·축·범례·주석). 본문·주석·print 는 한국어.
모든 수치는 `outputs/*.json` 에서 읽는다 — 이 파일에 손으로 친 측정값은 없다.

    PYTHONPATH=src:benchmark python src/viz_report06.py
    → outputs/figures/report06_*.png
"""
from __future__ import annotations

import json
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                          # noqa: E402
import numpy as np                                       # noqa: E402
from matplotlib.patches import FancyArrowPatch, Rectangle  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
FIGDIR = os.path.join(ROOT, "outputs", "figures")

C0 = 299792458.0
CK = dict(tx="#1565c0", ref="#2e7d32", surv="#c62828", tgt="#6a1b9a",
          grid="#b0bec5", ink="#263238", warn="#ef6c00")
BANDC = {"LTE 1.843 GHz": "#1565c0", "5G 3.5 GHz": "#2e7d32",
         "WiFi 5.21 GHz": "#c62828"}


def _load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return json.load(f)


def _style():
    plt.rcParams.update({
        "figure.facecolor": "white", "savefig.facecolor": "white",
        "axes.grid": True, "grid.alpha": 0.30, "grid.linewidth": 0.6,
        "axes.spines.top": False, "axes.spines.right": False,
        "font.size": 10, "axes.titlesize": 11.5, "axes.labelsize": 10,
        "legend.frameon": False, "axes.unicode_minus": False,
    })


def _save(fig, name):
    os.makedirs(FIGDIR, exist_ok=True)
    p = os.path.join(FIGDIR, name)
    fig.savefig(p, dpi=170, bbox_inches="tight")
    plt.close(fig)
    print(f"  [fig] {os.path.relpath(p, ROOT)}")
    return p


# --------------------------------------------------------------------------- #
#  그림 1 — X410 채널 배분과 바이스태틱 기하
# --------------------------------------------------------------------------- #
def fig_testbed(P):
    _style()
    hw = P["hw"]
    fig, ax = plt.subplots(figsize=(9.2, 5.0))
    ax.set_axis_off()
    ax.set_xlim(0, 10); ax.set_ylim(0, 6.3)

    tx, ref, surv, tgt = (0.9, 1.2), (2.1, 1.2), (8.4, 1.2), (5.0, 4.0)

    def node(xy, c, label, sub):
        ax.plot(*xy, marker="^", ms=15, color=c, zorder=5, clip_on=False)
        ax.text(xy[0], xy[1] - 0.42, label, ha="center", va="top",
                fontsize=10, fontweight="bold", color=c)
        ax.text(xy[0], xy[1] - 0.78, sub, ha="center", va="top",
                fontsize=8.6, color=CK["ink"])

    node(tx, CK["tx"], "TX", f"illuminator\n{hw['n_tx']} TX ch")
    node(ref, CK["ref"], "RX0  reference", "direct path\n(known signal)")
    node(surv, CK["surv"], f"RX1-{hw['n_surveillance_ch']}  surveillance",
         f"{hw['n_surveillance_ch']}-elem ULA\n"
         f"AoA BW {hw['aoa_beamwidth_deg']:.0f} deg")
    ax.plot(*tgt, marker="X", ms=17, color=CK["tgt"], zorder=5)
    ax.text(tgt[0], tgt[1] + 0.32, "TARGET   Matrice 4E  /  Mini 5 Pro",
            ha="center", fontsize=10, fontweight="bold", color=CK["tgt"])

    def arrow(a, b, c, ls="-", lw=1.8):
        ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=13,
                                     color=c, lw=lw, linestyle=ls,
                                     shrinkA=13, shrinkB=13))

    arrow(tx, ref, CK["ref"], lw=2.6)
    arrow(tx, surv, CK["warn"], ls=(0, (5, 3)))
    arrow(tx, tgt, CK["tx"])
    arrow(tgt, surv, CK["surv"])
    ax.text(4.9, 0.95, "direct-path interference  (DPI)  -  must be cancelled",
            ha="center", fontsize=8.8, color=CK["warn"])
    ax.text(1.45, 1.55, "reference\ncapture", ha="center", fontsize=8.4,
            color=CK["ref"])
    ax.text(2.7, 2.75, "$R_1$", fontsize=11, color=CK["tx"])
    ax.text(7.0, 2.75, "$R_2$", fontsize=11, color=CK["surv"])
    ax.text(5.2, 1.42, "$L$  baseline", fontsize=9.5, color=CK["ink"])

    box = ("USRP X410  +  2x ZBX\n"
           f"{hw['n_tx']} TX / {hw['n_rx']} RX   "
           f"{hw['max_bw_mhz']:.0f} MHz per ch\n"
           f"{hw['f_lo_hz']/1e6:.0f} MHz - {hw['f_hi_hz']/1e9:.1f} GHz\n"
           f"ADC {hw['adc_bits']} bit  ->  {hw['dynamic_range_db']:.0f} dB "
           f"dynamic range")
    ax.text(0.25, 6.2, box, ha="left", va="top", fontsize=9, color=CK["ink"],
            bbox=dict(boxstyle="round,pad=0.45", fc="#eceff1", ec="#90a4ae"))
    ax.set_title("Bistatic testbed: which X410 channel plays which role",
                 loc="left", fontweight="bold")
    return _save(fig, "report06_testbed.png")


# --------------------------------------------------------------------------- #
#  그림 2 — 원거리장 거리
# --------------------------------------------------------------------------- #
def fig_farfield(P):
    _style()
    ff, bands = P["farfield"], P["bands"]
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    f = np.linspace(1.6, 6.2, 300)                     # GHz
    order = [k for k in ff if ff[k]["kind"] == "airframe"] + \
            [k for k in ff if ff[k]["kind"] == "calibration"]
    sty = {"airframe": "-", "calibration": "--"}
    cols = ["#1565c0", "#c62828", "#546e7a", "#8d6e63"]
    for c, k in zip(cols, order):
        D = ff[k]["D_m"]
        ax.plot(f, 2 * D ** 2 * f * 1e9 / C0, sty[ff[k]["kind"]], color=c, lw=2.1,
                label=f"{ff[k]['name']}   D = {D:.2f} m")
    y0, y1 = ax.get_ylim()
    for b, v in bands.items():
        ax.axvline(v["fc_hz"] / 1e9, color=BANDC[b], lw=1.0, alpha=0.55)
        ax.text(v["fc_hz"] / 1e9, y0 + 0.02 * (y1 - y0), " " + b.split()[0],
                rotation=90, va="bottom", ha="left", fontsize=8, color=BANDC[b])
    worst = max(ff, key=lambda k: ff[k]["bands"]["WiFi 5.21 GHz"]["R_ff_m"])
    Rw = ff[worst]["bands"]["WiFi 5.21 GHz"]["R_ff_m"]
    ax.annotate(f"worst case\n{Rw:.1f} m", xy=(5.21, Rw), xytext=(5.45, Rw * 0.58),
                fontsize=9.5, color=CK["ink"], fontweight="bold", ha="left",
                arrowprops=dict(arrowstyle="->", color=CK["ink"], lw=1.1))
    ax.set_ylim(y0, y1)
    ax.set_xlabel("Frequency [GHz]")
    ax.set_ylabel(r"Far-field range  $R_{ff}=2D^2/\lambda$  [m]")
    ax.set_title("How far away must the receiver be for far-field RCS to be defined",
                 loc="left", fontweight="bold")
    ax.legend(loc="upper left", fontsize=8.6)
    ax.set_xlim(1.6, 6.2)
    return _save(fig, "report06_farfield.png")


# --------------------------------------------------------------------------- #
#  그림 3 — DPI 제거 깊이 → 검출거리 (ADC 천장)
# --------------------------------------------------------------------------- #
def fig_dpi_ladder(P, FS):
    _style()
    fig, ax = plt.subplots(figsize=(7.8, 4.6))
    depths, x_inf = [40.0, 60.0, 90.0], 105.0
    modes = {"W1": ("WiFi 80 MHz", "#1565c0"), "L1": ("LTE 20 MHz", "#2e7d32"),
             "G1": ("5G NR 100 MHz", "#c62828")}
    mk = {"matrice4e": ("o", "-"), "mini5pro": ("s", "--")}
    for dr, (m, ls) in mk.items():
        for mo, (lab, c) in modes.items():
            n = FS["ranges"][dr][mo]["equal_psd"]["full_waveform_capture"]["by_N"]["1"]
            xs = depths + [x_inf]
            ys = [n["R_dpi_resid_m"][k] / 1000.0 for k in ("40", "60", "90", "inf")]
            ax.plot(xs, ys, marker=m, color=c, lw=1.9, ms=6, ls=ls,
                    label=f"{lab}  -  {dr}")
    adc = P["adc"]["dynamic_range_db"]
    ax.set_xlim(34, 112)
    y0, y1 = ax.get_ylim()
    ax.axvspan(adc, 112, color=CK["warn"], alpha=0.12, lw=0)
    ax.axvline(adc, color=CK["warn"], lw=1.7)
    ax.text(adc + 1.5, y0 + 0.10 * (y1 - y0),
            f"beyond a {P['adc']['bits']}-bit ADC\n({adc:.0f} dB dynamic range)",
            va="bottom", fontsize=9, color=CK["warn"], fontweight="bold")
    ax.set_xticks(depths + [x_inf])
    ax.set_xticklabels(["40", "60", "90", r"$\infty$"])
    ax.set_ylim(y0, y1)
    ax.set_xlabel("Achieved direct-path cancellation depth [dB]")
    ax.set_ylabel(r"Detection range  $R_{90}$  [km]")
    ax.set_title("How much simulated range survives finite DPI cancellation",
                 loc="left", fontweight="bold")
    ax.legend(fontsize=8.0, ncol=2, loc="upper left")
    return _save(fig, "report06_dpi_ladder.png")


# --------------------------------------------------------------------------- #
#  그림 4 — 기울기 판별 (절대교정 없이 결판나는 축)
# --------------------------------------------------------------------------- #
def fig_slope(P):
    _style()
    S, bands = P["slope_discrimination"], P["bands"]
    f = np.linspace(S["f_lo_ghz"], S["f_hi_ghz"], 200)
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    for k, c in zip(P["meta"]["airframes_purchased"], ["#1565c0", "#c62828"]):
        a = S["per_airframe"][k]["slope_db_per_ghz"]
        ax.plot(f, a * (f - S["f_lo_ghz"]), color=c, lw=2.2,
                label=f"simulated {k}   {a:.2f} dB/GHz")
    a_l = S["lit_slope_db_per_ghz"]
    ax.plot(f, a_l * (f - S["f_lo_ghz"]), color=CK["ink"], lw=2.4, ls="--",
            label=f"measured literature   {a_l:.2f} dB/GHz")
    for b, v in bands.items():
        fx = v["fc_hz"] / 1e9
        ax.axvline(fx, color=BANDC[b], lw=1.0, alpha=0.5)
        ax.text(fx + 0.03, 0.02, b.split()[0], rotation=90, va="bottom",
                ha="left", fontsize=8, color=BANDC[b])
    gaps = S["gap_db_measured_pair"]
    lo, hi = min(gaps.values()), max(gaps.values())
    ax.annotate("", xy=(S["f_hi_ghz"], a_l * S["band_span_ghz"]),
                xytext=(S["f_hi_ghz"], hi),
                arrowprops=dict(arrowstyle="<->", color=CK["warn"], lw=1.8))
    ax.text(S["f_hi_ghz"] - 0.10, hi * 0.55,
            f"discriminating gap\n{lo:.1f} - {hi:.1f} dB", ha="right",
            fontsize=9.2, color=CK["warn"], fontweight="bold")
    ax.set_xlabel("Frequency [GHz]")
    ax.set_ylabel(r"$\Delta\sigma$ relative to the lowest band  [dB]")
    ax.set_title("Which frequency slope a three-band session discriminates",
                 loc="left", fontweight="bold")
    ax.legend(loc="upper left", fontsize=8.6)
    ax.set_xlim(S["f_lo_ghz"], S["f_hi_ghz"] + 0.05)
    return _save(fig, "report06_slope.png")


# --------------------------------------------------------------------------- #
def build_all():
    P = _load("outputs/report06_measurement.json")
    FS = _load("outputs/report13_freespace.json")
    print("[viz_report06] 그림 생성")
    return dict(testbed=fig_testbed(P), farfield=fig_farfield(P),
                dpi_ladder=fig_dpi_ladder(P, FS), slope=fig_slope(P))


if __name__ == "__main__":
    build_all()
