# -*- coding: utf-8 -*-
"""
das_fleet_compare_fig.py — outputs/figs/das_fleet_compare.png (그림 텍스트는 전부 영어)
=======================================================================================
패널 넷
  (a) 28 셀 레벨오차 DL(θb) — 4 기체 × 7 각도. 사전등록 문턱 ±4 / ±6 dB 를 띠로.
  (b) θb=0 레벨오차: 우리 메쉬 vs 기하 대조군(상자 3 종 + 부피등가 구).
  (c) 바이스태틱 표류 DL(θb)−DL(0) 와 사전등록 상한 포락선.
  (d) |DL(0)| vs 그 기체 자체의 형상 증거 — 2:2 분할.

색은 dataviz 기준 팔레트의 categorical slot 1~4 를 **고정 순서**로 쓴다
(blue/orange/aqua/yellow). 네 계열 전부 직접 라벨을 단다(노란색 대비 완화 규칙).
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import matplotlib                                                     # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                       # noqa: E402
import numpy as np                                                    # noqa: E402

OUT = os.path.join(ROOT, "outputs")
THETA_B = [0, 15, 30, 45, 60, 75, 90]
AF = ["phantom3", "phantom2", "mini2", "m350rtk"]
LBL = {"phantom3": "Phantom 3", "phantom2": "Phantom 2",
       "mini2": "Mini 2", "m350rtk": "M350 RTK"}
COL = {"phantom3": "#2a78d6", "phantom2": "#eb6834",
       "mini2": "#1baf7a", "m350rtk": "#eda100"}
MRK = {"phantom3": "o", "phantom2": "s", "mini2": "^", "m350rtk": "D"}
INK, INK2, GRID = "#0b0b0b", "#52514e", "#d8d7d2"


def style(ax):
    ax.set_facecolor("white")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=8.5, length=3)
    ax.grid(True, color=GRID, lw=0.6, alpha=0.7)
    ax.set_axisbelow(True)


def main():
    v = json.load(open(os.path.join(OUT, "das_fleet_validation.json")))
    rows = v["table_28"]
    DL0 = {a: v["prereg_judgement"]["DL0_db"][a] for a in AF}

    fig, axes = plt.subplots(2, 2, figsize=(12.6, 9.0), dpi=170)
    fig.patch.set_facecolor("white")
    ax = axes[0, 0]

    # ---------------- (a) DL vs theta_b ------------------------------------- #
    style(ax)
    ax.axhspan(-6, 6, color="#1baf7a", alpha=0.07, lw=0)
    ax.axhspan(-4, 4, color="#1baf7a", alpha=0.09, lw=0)
    ax.axhline(0, color=INK2, lw=1.0)
    for a in AF:
        y = [r["DL_db"] for r in rows if r["airframe"] == a]
        ax.plot(THETA_B, y, color=COL[a], lw=2.0, marker=MRK[a], ms=6,
                mec="white", mew=0.9, label=LBL[a], zorder=3)
        ax.annotate(LBL[a], (THETA_B[-1], y[-1]), xytext=(6, 0), textcoords="offset points",
                    color=COL[a], fontsize=9, fontweight="bold", va="center")
    ax.text(3, 5.0, "prereg  |ΔL| ≤ 6 dB", color="#0f7a55", fontsize=8)
    ax.text(3, 3.0, "prereg  |ΔL| ≤ 4 dB", color="#0f7a55", fontsize=8)
    ax.set_xlim(-4, 112)
    ax.set_xticks(THETA_B)
    ax.set_xlabel("bistatic angle  θ_b  [deg]", color=INK, fontsize=9.5)
    ax.set_ylabel("level error  ΔL = μ_ours − μ_Das  [dB]", color=INK, fontsize=9.5)
    ax.set_title("(a)  28 cells: our σ vs Das Table III, all four airframes",
                 color=INK, fontsize=11, fontweight="bold", loc="left")

    # ---------------- (b) ours vs geometric controls ------------------------ #
    ax = axes[0, 1]
    style(ax)
    bc = v["box_control"]
    names = ["ours (mesh)", "box (Table I)", "box (bbox)", "cube (eq. vol.)", "sphere (eq. vol.)"]
    keys = [None, "box_table1", "box_bbox", "cube_eqvol", "sphere_eqvol"]
    w = 0.16
    x = np.arange(len(AF))
    for i, (nm, k) in enumerate(zip(names, keys)):
        vals = [abs(DL0[a]) if k is None else bc[a]["controls"][k]["abs_DL_db"] for a in AF]
        col = "#2a78d6" if k is None else ["#c9c8c2", "#a8a7a1", "#7d7c76", "#eb6834"][i - 1]
        b = ax.bar(x + (i - 2) * w, vals, w * 0.88, color=col, label=nm,
                   edgecolor="white", linewidth=0.8, zorder=3)
        if k is None:
            ax.bar_label(b, fmt="%.1f", fontsize=8, color=INK, padding=2)
    ax.set_xticks(x)
    ax.set_xticklabels([LBL[a] for a in AF], fontsize=9, color=INK)
    ax.set_ylabel("|ΔL| at θ_b = 0  [dB]   (lower is better)", color=INK, fontsize=9.5)
    ax.set_title("(b)  does the drone mesh beat a box?", color=INK, fontsize=11,
                 fontweight="bold", loc="left")
    ax.legend(fontsize=8, frameon=False, labelcolor=INK2, ncol=2, loc="upper left")
    ax.set_ylim(0, 38)

    # ---------------- (c) bistatic drift ------------------------------------ #
    ax = axes[1, 0]
    style(ax)
    PRE = [0.0, 0.5, 1.0, 2.5, 5.0, 10.0, 16.0]
    ax.fill_between(THETA_B, [-p for p in PRE], PRE, color="#7d7c76", alpha=0.10, lw=0,
                    label="pre-registered bound")
    ax.plot(THETA_B, [-p for p in PRE], color="#7d7c76", lw=1.0, ls="--")
    ax.plot(THETA_B, PRE, color="#7d7c76", lw=1.0, ls="--")
    ax.axhline(0, color=INK2, lw=1.0)
    DY = {"phantom3": -13, "phantom2": 13, "mini2": 0, "m350rtk": 0}   # 라벨 충돌 회피
    for a in AF:
        t = v["bistatic_trend"][a]["drift_vs_mono_db"]
        y = [t[str(x)] for x in THETA_B]
        ax.plot(THETA_B, y, color=COL[a], lw=2.0, marker=MRK[a], ms=6, mec="white", mew=0.9)
        ax.annotate(LBL[a], (THETA_B[-1], y[-1]), xytext=(6, DY[a]), textcoords="offset points",
                    color=COL[a], fontsize=9, fontweight="bold", va="center")
    #  Das 자신의 taper(합성) — 비교용 회색 점선
    das = [v["bistatic_trend"]["mini2"]["dmu_das_bandcentre_db"][str(x)] for x in THETA_B]
    ax.plot(THETA_B, das, color="#52514e", lw=1.4, ls=":", marker=".", ms=5,
            label="Das synthetic taper (Mini 2 row)")
    ax.set_ylim(-5.2, 4.6)                       # ⭐ 데이터에 맞춰 확대 — 포락선은 밖으로 나간다
    ax.text(46, 3.9, "pre-registered bound runs to ±5 / ±10 / ±16 dB at 60 / 75 / 90°"
                     "  (off-scale)", color="#52514e", fontsize=7.8, ha="center")
    ax.set_xlim(-4, 112)
    ax.set_xticks(THETA_B)
    ax.set_xlabel("bistatic angle  θ_b  [deg]", color=INK, fontsize=9.5)
    ax.set_ylabel("drift  ΔL(θ_b) − ΔL(0)  [dB]", color=INK, fontsize=9.5)
    ax.set_title("(c)  bistatic trend: our error drifts down, monotonically",
                 color=INK, fontsize=11, fontweight="bold", loc="left")
    ax.legend(fontsize=8, frameon=False, labelcolor=INK2, loc="lower left")

    # ---------------- (d) evidence axis ------------------------------------- #
    ax = axes[1, 1]
    style(ax)
    EVID = {"phantom3": 86.9, "mini2": 77.3, "m350rtk": 56.0, "phantom2": 30.0}
    for a in AF:
        ax.scatter(EVID[a], abs(DL0[a]), s=150, color=COL[a], marker=MRK[a],
                   edgecolor="white", linewidth=1.4, zorder=4)
        ax.annotate(LBL[a], (EVID[a], abs(DL0[a])), xytext=(0, 12),
                    textcoords="offset points", ha="center", color=COL[a],
                    fontsize=9.5, fontweight="bold")
    ax.axhspan(v["degrees_of_freedom"]["evidence_split"]["well_constrained"]["max_db"],
               v["degrees_of_freedom"]["evidence_split"]["weakly_constrained"]["min_db"],
               color="#e34948", alpha=0.08, lw=0)
    ax.text(64, 4.3, f"{v['degrees_of_freedom']['evidence_split']['gap_db']:.1f} dB empty band",
            color="#b33837", fontsize=8.5, ha="center")
    ax.axvline(66, color=GRID, lw=1.2, ls="--")
    ax.text(33, 11.9, "no own-airframe\nshape evidence", color=INK2, fontsize=8.5, ha="center")
    ax.text(85, 11.9, "shape measured\nfrom this airframe", color=INK2, fontsize=8.5, ha="center")
    ax.set_xlim(22, 96)
    ax.set_ylim(-0.6, 13.4)
    ax.set_xlabel("silhouette IoU as % of achievable cap   (Phantom 2 = proxy mesh, nominal)",
                  color=INK, fontsize=9.5)
    ax.set_ylabel("|ΔL| at θ_b = 0  [dB]", color=INK, fontsize=9.5)
    ax.set_title("(d)  what splits the fleet is evidence, not band or size",
                 color=INK, fontsize=11, fontweight="bold", loc="left")

    fig.suptitle("Four-airframe validation of the SBR+PO mesh pipeline against Das (IEEE WCL 2026) "
                 "Table III — 28 comparison cells",
                 fontsize=12.5, fontweight="bold", color=INK, y=0.985)
    fig.text(0.006, 0.020,
             "ΔL = μ_ours(f_c) − [a_Das·f_c + b_Das + 2.5068 dB].   θ_b = TX–target–RX included angle, "
             "el = 0.   Kernel: SBR (Mitsuba/OptiX) + PO, λ/16, jitter 2, exit-visibility on.",
             fontsize=7.6, color=INK2)
    fig.text(0.006, 0.005,
             "Das bistatic rows for Phantom 3 / Mini 2 / M350 RTK are a synthetic taper (−0.6153·sin²θ_b), "
             "not measurements — only the Phantom 2 row is measured bistatic, and it is near-field (2.6 m).",
             fontsize=7.6, color=INK2)
    fig.tight_layout(rect=[0, 0.035, 1, 0.965])
    p = os.path.join(OUT, "figs", "das_fleet_compare.png")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    fig.savefig(p, facecolor="white")
    print("wrote", p)


if __name__ == "__main__":
    main()
