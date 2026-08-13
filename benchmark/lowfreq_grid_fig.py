# -*- coding: utf-8 -*-
"""
lowfreq_grid_fig.py — outputs/lowfreq_grid.json → outputs/figs/lowfreq_grid_convergence.png
============================================================================================
그림 글자는 **영어**(하우스 규약). 색은 dataviz 레퍼런스 팔레트의 검증된 값만 쓴다:
  · 주파수(순서형) = blue 순차램프 250/350/450/550/700 (밝은 표면 하한 step 250 준수)
  · 격자 두 계열   = categorical slot1 blue #2a78d6 · slot2 orange #eb6834 (all-pairs 통과 구간)
  · 문헌 기준선    = 중립 회색 파선 (계열색이 아니다 — 기준선은 계열이 아니므로)
"""
from __future__ import annotations

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = "/workspace/sionna"
JSON_PATH = os.path.join(ROOT, "outputs", "lowfreq_grid.json")
FIG_PATH = os.path.join(ROOT, "outputs", "figs", "lowfreq_grid_convergence.png")

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
GRID = "#e4e3df"
RAMP = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#0d366b"]   # 1.8 → 18.2 GHz
C_BASE = "#eb6834"      # lambda/16 (production baseline)
C_CONV = "#2a78d6"      # converged absolute grid
C_ALT = "#1baf7a"       # lambda/12 (the spacing the hypothesis named)
C_REF = "#6f6e6a"       # literature reference (neutral)


def style():
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "axes.edgecolor": "#c9c8c3", "axes.labelcolor": INK, "text.color": INK,
        "xtick.color": INK2, "ytick.color": INK2, "grid.color": GRID, "grid.linewidth": 0.8,
        "axes.grid": True, "axes.axisbelow": True, "axes.spines.top": False,
        "axes.spines.right": False, "font.size": 10.5, "axes.titlesize": 11.5,
        "legend.frameon": False, "lines.linewidth": 2.0, "lines.markersize": 6.5,
    })


def main():
    D = json.load(open(JSON_PATH))
    lad = D["ladder"]
    ref = D["refit"]
    hl = D["headline"]
    das = hl["das_a"]
    fs = [1.8, 3.5, 6.0, 12.0, 18.2]

    style()
    fig, axes = plt.subplots(2, 2, figsize=(13.2, 9.4))
    (axA, axB), (axC, axD) = axes

    # ---------------------------------------------------------------- A. 사다리 (수렴값 기준 상대)
    axA.axhspan(-0.1, 0.1, color="#eceae4", zorder=1)
    for i, f in enumerate(fs):
        k = f"{f:g}GHz"
        ref_mu = lad[k]["mu_finest"]
        rows = sorted(lad[k]["rows"], key=lambda r: -r["d_mm"])
        abs_d = [r["d_mm"] for r in rows if r["d_mm"] in (6.0, 3.0, 1.5, 0.75, 0.5, 0.375)]
        abs_m = [r["mu_dbsm"] - ref_mu for r in rows if r["d_mm"] in (6.0, 3.0, 1.5, 0.75, 0.5, 0.375)]
        axA.plot(abs_d, abs_m, "-o", color=RAMP[i], label=f"{f:g} GHz", zorder=3,
                 markeredgecolor=SURFACE, markeredgewidth=1.2)
        lam = lad[k]["lam_mm"]
        axA.plot([lam / 12.0], [lad[k]["mu_lam12"] - ref_mu], marker="s", ms=10, mfc="none",
                 mec=RAMP[i], mew=2.2, ls="none", zorder=4)
        axA.plot([lam / 16.0], [lad[k]["mu_lam16"] - ref_mu], marker="D", ms=9, mfc="none",
                 mec=RAMP[i], mew=2.2, ls="none", zorder=4)
    axA.axhline(0, color="#a9a8a3", lw=1.2, zorder=2)
    axA.set_xscale("log")
    axA.invert_xaxis()
    axA.set_xlabel("Ray-grid spacing  d  [mm]   (coarse → fine)")
    axA.set_ylabel(r"$\mu(d)-\mu(d_{\mathrm{finest}})$   [dB]")
    axA.set_title("A · Absolute grid ladder — does $\\mu$ converge?", loc="left", color=INK)
    axA.set_xticks([6, 3, 1.5, 0.75, 0.375])
    axA.get_xaxis().set_major_formatter(matplotlib.ticker.FixedFormatter(
        ["6", "3", "1.5", "0.75", "0.375"]))
    axA.get_xaxis().set_minor_formatter(matplotlib.ticker.NullFormatter())
    sec = axA.secondary_xaxis("top", functions=(lambda d: 13.78 / np.maximum(d, 1e-9),
                                                lambda r: 13.78 / np.maximum(r, 1e-9)))
    sec.set_xlabel("Rays across the 13.8 mm prop-blade thickness", color=INK2, fontsize=9.5)
    sec.set_xticks([2, 5, 10, 20, 35])
    sec.xaxis.set_major_formatter(matplotlib.ticker.ScalarFormatter())
    sec.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    axA.set_ylim(top=max(2.2, axA.get_ylim()[1]), bottom=min(-1.1, axA.get_ylim()[0]))
    axA.set_xlim(left=axA.get_xlim()[0] * 1.25)
    leg1 = axA.legend(ncols=2, loc="lower right", fontsize=9.5, frameon=True,
                      facecolor=SURFACE, edgecolor="none", framealpha=1.0)
    axA.add_artist(leg1)
    h2 = [matplotlib.lines.Line2D([], [], marker=m, ms=8, mfc="none", mec=INK2, mew=2.0, ls="none")
          for m in ("s", "D")]
    axA.legend(h2, [r"$\lambda/12$", r"$\lambda/16$"], loc="upper left", fontsize=9.5,
               frameon=True, facecolor=SURFACE, edgecolor="none", framealpha=1.0)
    k18 = f"{18.2:g}GHz"
    r6 = [r for r in lad[k18]["rows"] if r["d_mm"] == 6.0][0]
    axA.annotate("18.2 GHz", xy=(6.0, r6["mu_dbsm"] - lad[k18]["mu_finest"]),
                 xytext=(10, 2), textcoords="offset points", color=RAMP[4], fontsize=10)
    k1 = f"{1.8:g}GHz"
    axA.annotate("1.8 GHz  $\\lambda/12$", xy=(lad[k1]["lam_mm"] / 12.0,
                                               lad[k1]["mu_lam12"] - lad[k1]["mu_finest"]),
                 xytext=(4, -14), textcoords="offset points", ha="left", color=RAMP[0], fontsize=10)
    axA.annotate("converged  ±0.1 dB", xy=(0.4, 0.1), xytext=(0, 6),
                 textcoords="offset points", ha="right", color=INK2, fontsize=9)

    # ---------------------------------------------------------------- B. 이동량
    s16 = [lad[f"{f:g}GHz"]["shift_conv_minus_lam16_db"] for f in fs]
    s12 = [lad[f"{f:g}GHz"]["shift_conv_minus_lam12_db"] for f in fs]
    xs = np.arange(len(fs)); w = 0.36
    axB.bar(xs - w / 2, s12, w, color=C_ALT, edgecolor=SURFACE, linewidth=2, zorder=3,
            label=r"vs $\lambda/12$")
    axB.bar(xs + w / 2, s16, w, color=C_BASE, edgecolor=SURFACE, linewidth=2, zorder=3,
            label=r"vs $\lambda/16$  (production)")
    for x, v in zip(xs - w / 2, s12):          # λ/12 계열은 항상 위에
        axB.annotate(f"{v:+.2f}", (x, max(v, 0.0)), xytext=(0, 5), textcoords="offset points",
                     ha="center", color=INK2, fontsize=9)
    for x, v in zip(xs + w / 2, s16):          # λ/16 계열은 항상 아래에
        axB.annotate(f"{v:+.2f}", (x, min(v, 0.0)), xytext=(0, -14), textcoords="offset points",
                     ha="center", color=INK2, fontsize=9)
    axB.axhline(0, color="#a9a8a3", lw=1.2, zorder=2)
    axB.set_xticks(xs, [f"{f:g}" for f in fs])
    axB.set_xlabel("Frequency [GHz]")
    axB.set_ylabel(r"$\mu(0.75\,\mathrm{mm}) - \mu(\mathrm{baseline})$   [dB]")
    axB.set_title("B · How much does the converged grid move $\\mu$?", loc="left", color=INK)
    axB.legend(loc="lower right", fontsize=9.5)
    axB.margins(y=0.30)

    # ---------------------------------------------------------------- C. 대역 재적합
    fg = np.asarray(ref["freqs_ghz"], float)
    mb = np.asarray(ref["mu_lam16_dbsm"], float)
    mc = np.asarray(ref["mu_conv_dbsm"], float)
    axC.plot(fg, mb, "-o", color=C_BASE, label=r"$\lambda/16$  (production)", ms=8, lw=4.0,
             alpha=0.9, markeredgecolor=SURFACE, markeredgewidth=1.0, zorder=3)
    axC.plot(fg, mc, "-o", color=C_CONV, label=r"$d=0.75$ mm  (converged)", ms=4.5, lw=1.8,
             markeredgecolor=SURFACE, markeredgewidth=0.8, zorder=4)
    for fits, col in ((ref["fits_lam16"], C_BASE), (ref["fits_converged"], C_CONV)):
        for band, (lo, hi) in (("1.8-6.0", (1.8, 6.0)), ("6.0-18.2", (6.0, 18.2))):
            ft = fits[band]
            xx = np.array([lo, hi])
            axC.plot(xx, ft["a"] * xx + ft["b"], "--", color=col, lw=1.6, alpha=0.85, zorder=2)
    y0 = float(np.mean(mc)) - das * float(np.mean(fg))
    axC.plot([1.8, 18.2], [das * 1.8 + y0, das * 18.2 + y0], ":", color=C_REF, lw=2.2,
             label=f"Das slope {das} dB/GHz (offset arbitrary)", zorder=2)
    axC.set_xlabel("Frequency [GHz]")
    axC.set_ylabel(r"$\mu(f)$   [dBsm]")
    axC.set_title("C · Band re-fit on the converged grid", loc="left", color=INK)
    axC.legend(loc="lower right", fontsize=9.5)

    # ---------------------------------------------------------------- D. 기울기
    bands = ["1.8-6.0", "6.0-18.2", "1.8-18.2"]
    ab = [ref["fits_lam16"][b]["a"] for b in bands]
    ac = [ref["fits_converged"][b]["a"] for b in bands]
    eb = [ref["bootstrap_az_slope"]["lam16"][b]["se"] for b in bands]
    ec = [ref["bootstrap_az_slope"]["conv"][b]["se"] for b in bands]
    x = np.arange(3); w = 0.36
    axD.bar(x - w / 2, ab, w, yerr=eb, capsize=3, color=C_BASE, edgecolor=SURFACE,
            linewidth=2, label=r"$\lambda/16$  (production)", zorder=3,
            error_kw=dict(ecolor=INK2, lw=1.2))
    axD.bar(x + w / 2, ac, w, yerr=ec, capsize=3, color=C_CONV, edgecolor=SURFACE,
            linewidth=2, label=r"$d=0.75$ mm  (converged)", zorder=3,
            error_kw=dict(ecolor=INK2, lw=1.2))
    for xi, v, s in list(zip(x - w / 2, ab, eb)) + list(zip(x + w / 2, ac, ec)):
        axD.annotate(f"{v:+.2f}", (xi, v + s), xytext=(0, 6), textcoords="offset points",
                     ha="center", color=INK2, fontsize=9.5)
    axD.axhline(das, color=C_REF, ls="--", lw=1.8, zorder=2,
                label=f"Das measured  {das} dB/GHz")
    axD.axhline(0, color="#c9c8c3", lw=1.2, zorder=2)
    axD.set_xticks(x, ["1.8–6.0 GHz", "6.0–18.2 GHz", "1.8–18.2 GHz"])
    axD.set_ylabel(r"Slope  $a$  of  $\mu = a\,f + b$   [dB/GHz]")
    axD.set_title("D · Band slopes vs the measured anchor", loc="left", color=INK)
    axD.legend(loc="upper right", fontsize=9.5, frameon=True, facecolor=SURFACE,
               edgecolor="none", framealpha=1.0)
    axD.margins(y=0.22)

    fig.suptitle(f"Phantom 3 · monostatic el=0° · 360 azimuths · SBR+PO — grid-density decision test"
                 f"    (verdict: {D['verdict']})", x=0.012, ha="left", fontsize=13, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.965))
    os.makedirs(os.path.dirname(FIG_PATH), exist_ok=True)
    fig.savefig(FIG_PATH, dpi=200, bbox_inches="tight", facecolor=SURFACE)
    print("wrote", FIG_PATH)


if __name__ == "__main__":
    main()
