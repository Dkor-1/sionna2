# -*- coding: utf-8 -*-
"""
build_range_sweep_fig.py — Sionna PathSolver 거리 스윕(3/10/20/40 m)을 한 그림에.

⭐ 이 그림이 답하는 것: **거리가 멀어지면 Sionna 경로해가 어떻게 무너지나.**
   PathSolver 는 TX 에서 광선을 쏘고 그 광선이 표적을 맞혀야 경로가 생긴다.
   표적 입체각이 (D/R)² 로 줄므로, 광선을 (R/3)² 로 늘려 보상해도(1M→32M)
   40 m 에선 자세의 78% 가 경로 0 이다 — 그 붕괴를 가리지 않고 그대로 보인다.

윗줄  거리별 마이크로도플러 맵 4장(자기 최대 정규화 — 레벨 차는 아랫줄이 담당)
아랫줄 (a) 자세 인덱스별 발견 경로 수  (b) 평균 레벨 vs 거리(경로 중앙값은 범례로)

읽는 것: outputs/report07_sionna_ranges.{npz,json}
쓰는 것: outputs/figures/report07_f9.{png,pdf}
"""
from __future__ import annotations

import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import ScalarFormatter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from md_mapstyle import flash_spec, draw, caption                      # noqa: E402

J = json.load(open(f"{ROOT}/outputs/report07_sionna_ranges.json"))
Z = np.load(f"{ROOT}/outputs/report07_sionna_ranges.npz")
FIGDIR = f"{ROOT}/outputs/figures"
M = J["_meta"]
PRF, FFL, FTIP = M["prf_hz"], M["f_flash_hz"], M["f_tip_hz"]
RANGES = [3.0, 10.0, 20.0, 40.0]
KEYS = [f"R{r:.0f}" for r in RANGES]
COLS = ["#1f77b4", "#2ca02c", "#ff7f0e", "#d62728"]        # 3/10/20/40 m — 두 아랫패널 공통

FS = 9.5
plt.rcParams.update({
    "font.size": FS, "axes.labelsize": FS, "axes.titlesize": FS,
    "xtick.labelsize": FS - 1, "ytick.labelsize": FS - 1, "legend.fontsize": FS - 1.5,
    "axes.linewidth": 0.9, "figure.dpi": 200, "savefig.dpi": 200,
    "font.family": "DejaVu Sans",
})

fig = plt.figure(figsize=(13.0, 6.6))
gs = fig.add_gridspec(2, 5, width_ratios=[1, 1, 1, 1, 0.045],
                      height_ratios=[1.35, 1.0], hspace=0.52, wspace=0.34,
                      left=0.052, right=0.972, top=0.865, bottom=0.10)

# ── 윗줄 — 거리별 마이크로도플러 맵 (⭐md_mapstyle 규약, 자기 최대 정규화) ──────
axes_top, m, NPER, NSLOT = [], None, 0, 0
for i, (k, rng) in enumerate(zip(KEYS, RANGES)):
    ax = fig.add_subplot(gs[0, i], sharey=axes_top[0] if axes_top else None)
    f, t, S, NPER = flash_spec(np.asarray(Z[f"{k}/E"], complex), PRF, FFL)
    NSLOT = len(t)
    m = draw(ax, t, f, S, FTIP)
    ax.set_title(f"R = {rng:.0f} m")
    ax.set_xlabel("Time [ms]")
    if i == 0:
        ax.set_ylabel("Doppler [Hz]")
    else:
        plt.setp(ax.get_yticklabels(), visible=False)
    axes_top.append(ax)
cax = fig.add_subplot(gs[0, 4])
fig.colorbar(m, cax=cax).set_label("Magnitude, each panel to its own peak [dB]",
                                   fontsize=FS - 0.5)

# ── 아랫줄 (a) — 자세 인덱스별 발견 경로 수 ─────────────────────────────────
axa = fig.add_subplot(gs[1, 0:2])
for k, rng, c in zip(KEYS, RANGES, COLS):
    axa.plot(np.arange(M["n"]), Z[f"{k}/npaths"], drawstyle="steps-mid",
             lw=0.9, color=c, alpha=0.9, label=f"R = {rng:.0f} m")
axa.set_xlim(0, M["n"] - 1)
axa.set_ylim(-0.3, 11.8)                     # 위 여백 — 범례가 계단선을 안 덮게
axa.set_xlabel("Pose index")
axa.set_ylabel("Target paths found")
axa.grid(alpha=0.25, lw=0.5)
axa.legend(ncol=4, loc="upper right", framealpha=0.9, columnspacing=1.2,
           handlelength=1.4)

# ── 아랫줄 (b) — 평균 레벨 vs 거리 (경로 중앙값은 ⭐범례 라벨로) ─────────────
axb = fig.add_subplot(gs[1, 2:4])
lev = [J["ranges"][k]["level_db"] for k in KEYS]
axb.plot(RANGES, lev, color="0.45", lw=1.0, zorder=1)
for k, rng, c, l in zip(KEYS, RANGES, COLS, lev):
    r = J["ranges"][k]
    med = f"median {r['paths_median']:.0f} paths"
    if r["paths_zero_frac"] > 0:
        med += f" ({r['paths_zero_frac']:.0%} of poses: none)"
    axb.scatter([rng], [l], s=34, color=c, zorder=3, label=med)
rr = np.geomspace(3.0, 40.0, 64)
axb.plot(rr, lev[0] - 40.0 * np.log10(rr / 3.0), color="0.55", ls="--", lw=1.0,
         zorder=2, label="two-way 1/R² amplitude (from 3 m)")
axb.axvline(M["farfield_boundary_m"], color="0.3", ls=":", lw=1.0,
            label="far-field boundary 2D²/λ")
axb.set_xscale("log")
axb.set_xticks(RANGES)
axb.xaxis.set_major_formatter(ScalarFormatter())
axb.minorticks_off()
axb.set_xlabel("Range [m]")
axb.set_ylabel("Mean level [dB]")
axb.grid(alpha=0.25, lw=0.5)
axb.legend(loc="lower left", framealpha=0.9, handlelength=1.5)

fig.suptitle(f"{M['name']} hovering — Sionna PathSolver range sweep, "
             f"true monostatic (TX = RX, baseline 0), "
             f"belly view (az {M['az_deg']:.0f}, el {M['el_deg']:.0f}), "
             f"{M['fc_hz']/1e9:.1f} GHz", fontsize=FS + 0.5, y=0.965)

# ── 캡션 — 그림 밖 하단 (설정 수치는 리포트 부록이 담고, 여기는 표시 규약 한 줄) ──
cap = (caption(PRF, FFL, NPER, NSLOT) + "\n"
       "Top row: each map normalized to its own peak — level differences are in "
       "panel (b). Dashed white: blade-tip Doppler.")
fig.text(0.052, -0.03, cap, fontsize=FS - 1.5, color="0.3", va="top")

for ext in ("png", "pdf"):
    fig.savefig(f"{FIGDIR}/report07_f9.{ext}", bbox_inches="tight", facecolor="white")
plt.close(fig)
print("  ✅ outputs/figures/report07_f9.png")
for k, rng in zip(KEYS, RANGES):
    r = J["ranges"][k]
    print(f"     R={rng:4.0f} m  경로중앙 {r['paths_median']:.0f} · "
          f"빈자세 {r['paths_zero_frac']:.1%} · 레벨 {r['level_db']:.1f} dB")
