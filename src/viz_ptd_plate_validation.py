# -*- coding: utf-8 -*-
"""viz_ptd_plate_validation.py — 검증 1 그림 (평판 PO vs PO+PTD vs MoM 참조해)

하우스 규약: **그림 안의 글자는 전부 영어**. 수치는 outputs/ptd_plate_validation.json 에서만 읽는다.

    PYTHONPATH=src python src/viz_ptd_plate_validation.py
    → outputs/figs/ptd_plate_validation.png
"""
from __future__ import annotations

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                   # noqa: E402
import numpy as np                                                # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
FIGDIR = os.path.join(ROOT, "outputs", "figs")
SRC = os.path.join(ROOT, "outputs", "ptd_plate_validation.json")

#  범주형 4색 — Okabe-Ito (src/viz_ptd_drone_effect.py 와 같은 배정).
#  참조해는 색이 아니라 **두꺼운 잉크색 실선**으로 따로 세운다(정체성=색 하나에 의존하지 않도록
#  선굵기·선종류를 2 차 부호화로 함께 쓴다).
C_REF = "#263238"     # MoM reference (2-D EFIE)
C_PO = "#0072B2"      # PO only
C_PTD = "#D55E00"     # PO + PTD, as implemented
C_FIX = "#009E73"     # PO + PTD, sign corrected
MUTED = "#78909c"

POLS = [("H", "E $\\parallel$ long edges  (2-D TM / soft, $f^{(1)}$)"),
        ("V", "E $\\perp$ long edges  (2-D TE / hard, $g^{(1)}$)")]


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
    th = np.array(D["theta_deg"])
    n1 = D["first_null_deg"]
    head = D["headline_rms_db_pooled_over_pol"]

    fig, axes = plt.subplots(2, 2, figsize=(12.4, 7.6), sharex=True,
                             gridspec_kw=dict(height_ratios=[1.35, 1.0], hspace=0.16,
                                              wspace=0.16))

    for col, (pol, label) in enumerate(POLS):
        c = D["curves"][pol]
        e = D["errors"][pol]
        ref = np.array(c["sigma_ref_dbsm"])
        po = np.array(c["sigma_po_dbsm"])
        ptd = np.array(c["sigma_po_ptd_dbsm"])
        flip = np.array(c["sigma_po_ptd_signflip_control_dbsm"])

        ax = axes[0, col]
        ax.axvspan(0, n1, color=MUTED, alpha=0.10, lw=0)
        ax.plot(th, ref, "-", color=C_REF, lw=2.6, alpha=0.9,
                label="reference: 2-D EFIE MoM (exact)", zorder=2)
        ax.plot(th, po, "--", color=C_PO, lw=1.5, label="PO only", zorder=3)
        ax.plot(th, flip, "-", color=C_PTD, lw=1.6, alpha=0.75,
                label="PO + PTD, sign flipped (negative control)", zorder=4)
        ax.plot(th, ptd, "-", color=C_FIX, lw=1.6, label="PO + PTD (kernel)", zorder=5)
        ax.set_title(label)
        ax.set_ylabel(r"monostatic $\sigma$ [dBsm]")
        ax.set_ylim(-45, 46)
        ax.set_xlim(0, th.max())
        if col == 0:
            ax.legend(loc="lower left", fontsize=8.6, ncol=1)
            ax.annotate("specular lobe\n(|$\\theta$| < first null %.2f$^\\circ$)" % n1,
                        xy=(n1, 33), xytext=(13, 39), fontsize=8.2, color=MUTED,
                        va="center", arrowprops=dict(arrowstyle="->", color=MUTED, lw=0.9))
        else:
            tw = D["traveling_wave_check"]
            ax.annotate("travelling-wave lobe %.0f$^\\circ$\n(classic %.1f$^\\circ$) — 2nd order,\n"
                        "absent from PO and 1st-order PTD"
                        % (tw["mom_V_peak_theta_deg"], tw["classic_estimate_theta_deg"]),
                        xy=(tw["mom_V_peak_theta_deg"], tw["mom_V_peak_dbsm"] + 1.0),
                        xytext=(41, 34), fontsize=8.2, color=C_REF, va="center",
                        arrowprops=dict(arrowstyle="->", color=C_REF, lw=0.9))

        ax = axes[1, col]
        ax.axvspan(0, n1, color=MUTED, alpha=0.10, lw=0)
        ax.axhline(0, color=C_REF, lw=1.2, alpha=0.55)
        ax.plot(th, po - ref, "--", color=C_PO, lw=1.5)
        ax.plot(th, flip - ref, "-", color=C_PTD, lw=1.6, alpha=0.75)
        ax.plot(th, ptd - ref, "-", color=C_FIX, lw=1.6)
        ax.set_ylim(-30, 30)
        ax.set_xlabel(r"incidence angle $\theta$ from plate normal [deg]")
        ax.set_ylabel("error vs reference [dB]")
        rows = [("PO only", e["po_only"], C_PO),
                ("PO+PTD flipped", e["po_ptd_sign_flipped_control"], C_PTD),
                ("PO+PTD kernel", e["po_ptd"], C_FIX)]
        txt = "oblique band ($\\theta$ > %.1f$^\\circ$)  RMS / median / worst\n" % n1
        for nm, blk, _ in rows:
            txt += "  %-16s %5.2f / %4.2f / %5.1f dB\n" % (
                nm, blk["oblique"]["rms_db"], blk["oblique"]["median_abs_db"],
                blk["oblique"]["max_abs_db"])
        ax.text(0.985, 0.035, txt.rstrip(), transform=ax.transAxes, ha="right", va="bottom",
                fontsize=8.3, family="monospace", color=C_REF,
                bbox=dict(boxstyle="round,pad=0.35", fc="white", ec=MUTED, lw=0.7, alpha=0.9))

    a_l, b_l = D["a_lambda"], D["b_lambda"]
    fig.suptitle("PTD validation 1 — PEC rectangular plate, monostatic, principal-plane cut\n"
                 "%.0f$\\lambda \\times$ %.0f$\\lambda$ plate at %.1f GHz  ·  reference = 2-D EFIE "
                 "MoM (self-tested to %.3f dB against the exact circular-cylinder series)"
                 % (a_l, b_l, D["fc_hz"] / 1e9,
                    D["reference_solver_selftest"]["worst_abs_db_at_240seg"]),
                 fontsize=11.2, y=0.985)
    fig.text(0.5, 0.012,
             "phase gate arg(A$_{code}$/A$_{analytic}$) = 0 (max %.1e deg); pooled oblique RMS  "
             "PO %.2f dB  ·  PO+PTD %.2f dB  ·  sign-flipped control %.2f dB — the control also "
             "improves, so RMS alone cannot validate the kernel"
             % (D["sign_probe"]["max_abs_phase_deg"], head["oblique"]["po_only"],
                head["oblique"]["po_ptd"], head["oblique"]["po_ptd_sign_flipped_control"]),
             ha="center", fontsize=8.8, color=C_REF)

    os.makedirs(FIGDIR, exist_ok=True)
    dst = os.path.join(FIGDIR, "ptd_plate_validation.png")
    fig.savefig(dst, dpi=170, bbox_inches="tight")
    print("저장:", dst)


if __name__ == "__main__":
    main()
