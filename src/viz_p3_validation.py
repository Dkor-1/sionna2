# -*- coding: utf-8 -*-
"""viz_p3_validation.py — 봉인 해제 대조 그림 (우리 blind σ(f) vs Das / Yuan 실측)

하우스 규약: **그림 안의 글자는 전부 영어**. 수치는 outputs/p3_validation.json 에서만 읽는다.

색: Okabe-Ito 범주 3색(파랑/청록/주황) — 검증기 통과
    (node validate_palette.js "#0072B2,#009E73,#D55E00" --mode light → ALL CHECKS PASS).
    우리 곡선은 범주색이 아니라 **두꺼운 잉크선**으로 세운다(정체성이 색 하나에 안 걸리도록
    선굵기·마커를 2차 부호화로 함께 쓴다).

    PYTHONPATH=src python src/viz_p3_validation.py
    → outputs/figs/p3_validation.png
"""
from __future__ import annotations

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                   # noqa: E402
import numpy as np                                                # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SRC = os.path.join(ROOT, "outputs", "p3_validation.json")
FIGDIR = os.path.join(ROOT, "outputs", "figs")

C_OURS = "#263238"     # ours (SBR+PO, blind) — ink, thick, markers
C_MEAS = "#0072B2"     # Yuan measured curve, azimuth plane
C_YUAN = "#009E73"     # Yuan published linear fit
C_DAS = "#D55E00"      # Das published linear fit (converted to linear-mean)
MUTED = "#90a4ae"
BANDC = "#eceff1"


def _style():
    plt.rcParams.update({
        "figure.facecolor": "white", "savefig.facecolor": "white",
        "axes.grid": True, "grid.alpha": 0.25, "grid.linewidth": 0.6,
        "axes.spines.top": False, "axes.spines.right": False,
        "font.size": 9.5, "axes.titlesize": 10.5, "axes.labelsize": 9.5,
        "legend.frameon": False, "axes.unicode_minus": False,
    })


def main():
    _style()
    D = json.load(open(SRC))
    f = np.array(D["ours_curve"]["f_ghz"])
    mu = np.array(D["ours_curve"]["mu_dbsm"])
    fy = np.array(D["yuan_curve_theta90"]["f_ghz"])
    my = np.array(D["yuan_curve_theta90"]["mu_dbsm"])
    S, L = D["slope"], D["level"]
    a_o, b_o = S["ours_el0_full_band"]["a"], S["ours_el0_full_band"]["b"]
    se_o = S["ours_el0_full_band"]["se_a"]
    a_y, b_y = S["yuan_theta90_published"]["a"], S["yuan_theta90_published"]["b"]
    a_d, b_d = S["das_published"]["a"], S["das_published"]["b"]
    off_e = L["convention_branches"]["exponential_db"]
    c_e, d_e = 0.03, 5.16                                     # Das eps(f) = 0.03f + 5.16
    grid = np.linspace(1.8, 18.2, 400)
    das_e = a_d * grid + b_d + off_e
    das_l = a_d * grid + b_d + np.log(10.0) / 20.0 * (c_e * grid + d_e) ** 2

    R = D["residual"]["vs_yuan_theta90_measured_curve"]
    rc = np.array(R["resid_db"])
    rm = np.array(D["residual"]["vs_yuan_theta90_model"]["resid_db"])
    rd = np.array(D["residual"]["vs_das_exponential"]["resid_db"])
    OB = D["our_operating_band"]

    fig, (ax, bx) = plt.subplots(2, 1, figsize=(11.4, 8.2), sharex=True,
                                 gridspec_kw=dict(height_ratios=[1.55, 1.0], hspace=0.10))

    # ── (a) mu(f) ────────────────────────────────────────────────────────
    for a_ in (ax, bx):
        a_.axvspan(1.8, 6.0, color=BANDC, zorder=0)
    ax.text(1.95, -8.6, "our operating band\n(LTE / 5G / Wi-Fi)", fontsize=8.2,
            color="#546e7a", va="top")

    ax.plot(fy, my, lw=1.0, color=C_MEAS, alpha=0.55, zorder=2,
            label="Measured, DJI Phantom 3, azimuth plane  (Yuan Fig.5, digitised)")
    ax.plot(grid, a_y * grid + b_y, lw=2.0, color=C_YUAN, zorder=4,
            label=f"Yuan published fit, $\\theta$=90$\\degree$   $a$={a_y:.3f} dB/GHz")
    ax.fill_between(grid, das_e, das_l, color=C_DAS, alpha=0.16, lw=0, zorder=3)
    ax.plot(grid, das_e, lw=2.0, color=C_DAS, zorder=4,
            label=f"Das published fit, $\\theta_b$=0$\\degree$, elevation-pooled   $a$={a_d:.3f} dB/GHz")
    ax.plot(grid, das_l, lw=1.0, ls=(0, (4, 2)), color=C_DAS, zorder=4,
            label="   └ statistic-convention branch: exponential $\\rightarrow$ log-normal")
    ax.plot(grid, a_o * grid + b_o, lw=2.6, color=C_OURS, zorder=6,
            label=f"OURS — SBR+PO, blind, el=0   $a$={a_o:.3f} $\\pm$ {se_o:.3f} dB/GHz")
    ax.plot(f, mu, "o", ms=5.2, mfc="white", mec=C_OURS, mew=1.6, zorder=7,
            label="OURS, 21 frequency samples")

    ax.annotate("", xy=(3.5, np.interp(3.5, grid, a_o * grid + b_o)),
                xytext=(3.5, np.interp(3.5, grid, a_y * grid + b_y)),
                arrowprops=dict(arrowstyle="<->", color=C_OURS, lw=1.2, shrinkA=0, shrinkB=0),
                zorder=8)
    ax.text(3.75, -18.6, "level deficit", fontsize=8.6, color=C_OURS)

    ax.set_ylabel("$\\mu(f)$  = 10 log$_{10}\\,\\langle\\sigma\\rangle_\\phi$   [dBsm]")
    ax.set_title("DJI Phantom 3 monostatic RCS vs frequency — our blind SBR+PO kernel "
                 "against the only two measured datasets  (both are the same campaign)",
                 loc="left", pad=9)
    ax.set_ylim(-29, -7)
    ax.legend(loc="lower right", fontsize=8.3, ncol=1, handlelength=2.4, labelspacing=0.32)

    # ── (b) residual ─────────────────────────────────────────────────────
    bx.axhline(0.0, color=MUTED, lw=1.0)
    bx.axhline(rc.mean(), color=C_OURS, lw=1.0, ls=(0, (5, 3)))
    bx.text(1.62, rc.mean() + 0.30, f"mean {rc.mean():+.2f} dB", ha="left",
            fontsize=8.4, color=C_OURS)
    bx.plot(f, rd, "-", lw=1.3, color=C_DAS, marker="^", ms=4.2, alpha=0.85,
            label=f"ours − Das (exponential branch)   mean {rd.mean():+.2f} dB")
    bx.plot(f, rm, ls=(0, (4, 2)), lw=1.3, color=C_YUAN, marker="s", ms=4.2, alpha=0.85,
            label=f"ours − Yuan $\\theta$=90$\\degree$ fitted line   mean {rm.mean():+.2f} dB")
    bx.plot(f, rc, "-", lw=2.4, color=C_OURS, marker="o", ms=5.2, mfc="white", mew=1.5,
            label=f"ours − Yuan $\\theta$=90$\\degree$ measured curve   mean {rc.mean():+.2f} dB "
                  "(elevation-, convention- and estimator-matched)")

    iw = int(np.argmax(np.abs(rc)))
    bx.annotate(f"worst {rc[iw]:+.2f} dB\n@ {f[iw]:.2f} GHz", xy=(f[iw], rc[iw]),
                xytext=(f[iw] + 1.5, rc[iw] - 1.9), fontsize=8.4, color=C_OURS,
                arrowprops=dict(arrowstyle="->", color=C_OURS, lw=1.0))
    bx.text(6.4, -0.9,
            f"low band ($\\leq$6 GHz) {R['low_band_mean_db']:+.2f} dB     "
            f"high band ($\\geq$12 GHz) {R['high_band_mean_db']:+.2f} dB     "
            f"residual trend {R['trend_db_per_ghz']:+.3f} dB/GHz "
            f"({R['trend_sigma']:.1f}$\\sigma$)",
            fontsize=8.4, color="#37474f")
    bx.set_xlabel("Frequency  [GHz]")
    bx.set_ylabel("Residual  ours − measured   [dB]")
    bx.set_xlim(1.4, 18.6)
    bx.set_ylim(-10.4, 1.4)
    bx.legend(loc="lower right", fontsize=8.3, handlelength=2.4, labelspacing=0.32)

    foot = ("VERDICT   level error dominates: "
            f"{OB['level_error_db']['mean']:+.1f} dB in 1.8–6 GHz, "
            f"{rc.mean():+.1f} dB band-averaged   |   "
            f"slope excess +{a_o - a_y:.3f} dB/GHz vs the elevation-matched comparand "
            f"= {(a_o - a_y) / se_o:.1f}$\\sigma$, NOT significant at 95%   |   "
            f"in 1.8–6 GHz alone ours rises {OB['ours']['a']:.2f} vs measured "
            f"{OB['measured_theta90_curve_dense']['a']:.2f} dB/GHz "
            f"({OB['slope_ratio']:.1f}×)   |   "
            "blind result, not retro-fitted")
    fig.text(0.012, 0.012, foot, fontsize=8.3, color="#37474f")

    os.makedirs(FIGDIR, exist_ok=True)
    out = os.path.join(FIGDIR, "p3_validation.png")
    fig.savefig(out, dpi=190, bbox_inches="tight", pad_inches=0.22)
    print("wrote", out)


if __name__ == "__main__":
    main()
