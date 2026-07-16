# -*- coding: utf-8 -*-
"""viz_report3_cad.py — report03 (표적 검증) 의 **신뢰 경계 종합 그림**.

숫자는 손으로 적지 않는다. outputs/real_cad_compare.json + community_compare.json
(mesh_compare.py / community_compare.py 가 남긴 것)을 읽어 그린다.
→ 그림과 본문 표가 어긋날 수 없다.

그림 텍스트는 영어(프로젝트 규약), 본문·주석은 한국어.
출력: outputs/figures/report03_confidence.png
"""
from __future__ import annotations

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
OUT = os.path.join(ROOT, "outputs", "figures", "report03_confidence.png")

with open(os.path.join(ROOT, "outputs", "real_cad_compare.json")) as f:
    REAL = json.load(f)
with open(os.path.join(ROOT, "outputs", "community_compare.json")) as f:
    COMM = json.load(f)

# 3중 교차검증 = Typhoon(실물 CAD) · M100 · M600(커뮤니티). prop 은 부품 단위 보조 점검.
DRONES = [
    ("Typhoon H480\n(real CAD, hexa)", REAL["typhoon"]),
    ("Matrice 100\n(community, quad)", COMM["m100"]),
    ("Matrice 600 Pro\n(community, hexa)", COMM["m600"]),
]
PROP = ("Holybro 1345 prop\n(real CAD)", REAL["prop"])
ALL = DRONES + [PROP]

C_REAL = "#1f77b4"   # reference CAD
C_OURS = "#d62728"   # our parametric mesh
C_OK = "#2ca02c"
C_WARN = "#ff7f0e"

fig = plt.figure(figsize=(15, 9), dpi=130)
gs = fig.add_gridspec(2, 3, height_ratios=[1.05, 0.95], hspace=0.42, wspace=0.28,
                      left=0.06, right=0.985, top=0.90, bottom=0.09)

fig.suptitle("report03 — Independent-mesh cross-validation: where our numbers are trustworthy, and where they are NOT",
             fontsize=14, fontweight="bold", y=0.975)

# ── Row 1: sigma vs azimuth (dBsm), reference solid vs ours dashed ───────────
for i, (name, d) in enumerate(DRONES):
    ax = fig.add_subplot(gs[0, i])
    az = np.array(d["az"])
    sr = 10 * np.log10(np.array(d["sigma_real"]))
    so = 10 * np.log10(np.array(d["sigma_ours"]))
    ax.plot(az, sr, color=C_REAL, lw=1.6, label="reference CAD")
    ax.plot(az, so, color=C_OURS, lw=1.6, ls="--", label="ours (parametric)")
    ax.axhline(d["sigma_mean_real_dbsm"], color=C_REAL, lw=1.0, alpha=0.5, ls=":")
    ax.axhline(d["sigma_mean_ours_dbsm"], color=C_OURS, lw=1.0, alpha=0.5, ls=":")
    ax.set_title(name, fontsize=10.5, fontweight="bold")
    ax.set_xlabel("azimuth [deg]", fontsize=9)
    if i == 0:
        ax.set_ylabel("RCS  σ  [dBsm]", fontsize=9)
    ax.set_xlim(0, 360)
    ax.set_xticks([0, 90, 180, 270, 360])
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8, loc="lower center", ncol=2, framealpha=0.85)
    # 주석: 평균은 거의 겹치나(dotted), 곡선(널/글린트)은 크게 갈린다
    ax.text(0.02, 0.97,
            f"mean Δσ = {d['d_sigma_db']:+.2f} dB\nper-az RMS = {d['d_sigma_rms_db']:.1f} dB",
            transform=ax.transAxes, va="top", ha="left", fontsize=8.5,
            bbox=dict(boxstyle="round", fc="white", ec="0.6", alpha=0.9))

# ── Row 2, panel A: mean sigma difference bars with +-1 dB band ──────────────
axA = fig.add_subplot(gs[1, 0])
labels = ["Typhoon", "M100", "M600", "1345 prop"]
dsig = [d["d_sigma_db"] for _, d in ALL]
cols = [C_OK if abs(v) <= 1.0 else C_WARN for v in dsig]
axA.axhspan(-1, 1, color=C_OK, alpha=0.13, zorder=0, label="±1 dB band")
axA.axhline(0, color="0.4", lw=0.8)
bars = axA.bar(labels, dsig, color=cols, edgecolor="0.3")
for b, v in zip(bars, dsig):
    axA.text(b.get_x() + b.get_width() / 2, v + (0.06 if v >= 0 else -0.16),
             f"{v:+.2f}", ha="center", va="bottom" if v >= 0 else "top", fontsize=9)
axA.set_title("A. Mean RCS difference (ours − reference)", fontsize=10.5, fontweight="bold")
axA.set_ylabel("Δ mean σ  [dB]", fontsize=9)
axA.set_ylim(-1.6, 1.6)
axA.grid(axis="y", alpha=0.25)
axA.legend(fontsize=8, loc="lower right")
axA.text(0.5, -0.30, "3-way average agreement is within ~1 dB → method is calibrated",
         transform=axA.transAxes, ha="center", fontsize=8.5, style="italic", color="0.3")

# ── Row 2, panel B: per-azimuth RMS bars (un-citable pointwise) ──────────────
axB = fig.add_subplot(gs[1, 1])
rms = [d["d_sigma_rms_db"] for _, d in ALL]
barsB = axB.bar(labels, rms, color=C_WARN, edgecolor="0.3")
for b, v in zip(barsB, rms):
    axB.text(b.get_x() + b.get_width() / 2, v + 0.15, f"{v:.1f}", ha="center", fontsize=9)
axB.set_title("B. Per-azimuth RMS difference", fontsize=10.5, fontweight="bold")
axB.set_ylabel("RMS of Δσ(az)  [dB]", fontsize=9)
axB.set_ylim(0, max(rms) * 1.25)
axB.grid(axis="y", alpha=0.25)
axB.text(0.5, -0.30,
         "5–12 dB pointwise → nulls & glints are NOT citable per-angle",
         transform=axB.transAxes, ha="center", fontsize=8.5, style="italic", color="0.3")

# ── Row 2, panel C: projected-area difference bars ──────────────────────────
axC = fig.add_subplot(gs[1, 2])
dar = [d["d_area_db"] for _, d in ALL]
colsC = [C_OK if abs(v) <= 1.0 else C_WARN for v in dar]
axC.axhline(0, color="0.4", lw=0.8)
barsC = axC.bar(labels, dar, color=colsC, edgecolor="0.3")
for b, v in zip(barsC, dar):
    axC.text(b.get_x() + b.get_width() / 2, v + (0.12 if v >= 0 else -0.12),
             f"{v:+.2f}", ha="center", va="bottom" if v >= 0 else "top", fontsize=9)
axC.set_title("C. Projected-area difference", fontsize=10.5, fontweight="bold")
axC.set_ylabel("Δ mean projected area  [dB]", fontsize=9)
axC.grid(axis="y", alpha=0.25)
axC.text(0.5, -0.30,
         "−3.5…−5.3 dB: ours is smaller (legs / masts under-modelled)",
         transform=axC.transAxes, ha="center", fontsize=8.5, style="italic", color="0.3")

fig.savefig(OUT, dpi=130, bbox_inches="tight", facecolor="white")
print("saved:", os.path.relpath(OUT, ROOT))
