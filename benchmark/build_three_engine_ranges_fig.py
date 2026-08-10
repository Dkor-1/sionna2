# -*- coding: utf-8 -*-
"""
build_three_engine_ranges_fig.py — ⭐그림 3 을 거리 3/8/15 m 세 줄로 (사용자 요청 2026-08-10).

한 줄 = 한 거리. 왼쪽 열만 거리마다 다시 푼 Sionna PathSolver(진짜 모노스태틱)이고,
가운데·오른쪽 열(우리 SBR+PO · 가림 끈 대조군)은 **표적 앵커 평면파라 거리 무관** —
세 줄에서 같은 맵이 반복된다. 그 반복 자체가 이 그림의 절반이다.

읽는 것: outputs/report07_three_engine_ranges.{npz,json} (Sionna, 거리별)
         outputs/report07_three_engines.{npz,json}       (sbr·po 열 — 그림 3 원장)
쓰는 것: outputs/figures/report07_f12.{png,pdf}
"""
from __future__ import annotations

import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
from md_mapstyle import flash_spec, auto_periods, draw, caption              # noqa: E402

TR = json.load(open(f"{ROOT}/outputs/report07_three_engine_ranges.json"))
ZR = np.load(f"{ROOT}/outputs/report07_three_engine_ranges.npz")
TJ = json.load(open(f"{ROOT}/outputs/report07_three_engines.json"))["_meta"]
ZO = np.load(f"{ROOT}/outputs/report07_three_engines.npz")
M, RGS = TR["_meta"], TR["ranges"]
PRF, FFL, FTIP = M["prf_hz"], M["f_flash_hz"], M["f_tip_hz"]

FS = 9.5
plt.rcParams.update({
    "font.size": FS, "axes.labelsize": FS, "axes.titlesize": FS,
    "xtick.labelsize": FS - 1, "ytick.labelsize": FS - 1,
    "axes.linewidth": 0.9, "figure.dpi": 200, "savefig.dpi": 200,
    "font.family": "DejaVu Sans",
})

def _depth_db(E):
    """변조 깊이 두 가지 — (p5~p95 강건, p-p 전폭).

    ⚠ 2026-08-10 실측: 고해상도(4096 자세)로 가니 Sionna 팔의 p-p 가 32.6 / 2.5 / 50.1 dB 로
      거리마다 요동쳤다. 원인은 물리가 아니라 **광선 표본화** — 경로를 거의 못 찾은 자세 하나가
      −186 dB 까지 떨어져 전폭을 혼자 정한다. 그래서 제목에는 **p5~p95 를 앞에** 적고
      p-p 는 괄호로 남긴다(우리 팔은 둘의 차이가 작아 안정성 자체가 비교 항목이 된다)."""
    d = 20 * np.log10(np.abs(np.asarray(E, complex)) + 1e-30)
    p5, p95 = np.percentile(d, [5, 95])
    return float(p95 - p5), float(d.max() - d.min())


ROWS = ["R3", "R8", "R15"]
fig = plt.figure(figsize=(11.6, 9.6))
gs = fig.add_gridspec(3, 4, width_ratios=[1, 1, 1, 0.045], wspace=0.16, hspace=0.30,
                      left=0.062, right=0.925, top=0.905, bottom=0.075)

CAP = ""
for r, key in enumerate(ROWS):
    rng_m = RGS[key]["range_m"]
    Es, Eb, Ep = (np.asarray(ZR[f"{key}/E"], complex),
                  np.asarray(ZO["sbr"], complex), np.asarray(ZO["po"], complex))
    ds, db_, dp = _depth_db(Es), _depth_db(Eb), _depth_db(Ep)
    cols = [
        (Es, f"Sionna PathSolver — R = {rng_m:.0f} m\n"
             f"{ds[0]:.1f} dB p5-p95 ({ds[1]:.0f} p-p) · "
             f"median {RGS[key]['paths_median']:.0f} paths/pose · "
             f"level {RGS[key]['level_db']:.0f} dB"),
        (Eb, f"Ours (SBR+PO, default) — {db_[0]:.1f} dB p5-p95 ({db_[1]:.1f} p-p)\n"
             + ("range-invariant (plane wave)" if r == 0 else "same map, by construction")),
        (Ep, f"Ours, nothing blocked (control) — {dp[0]:.1f} dB p5-p95 ({dp[1]:.1f} p-p)\n"
             + ("range-invariant (plane wave)" if r == 0 else "same map, by construction")),
    ]
    for c, (E, title) in enumerate(cols):
        ax = fig.add_subplot(gs[r, c])
        f, t, S, nper = flash_spec(E, PRF, FFL, auto_periods(PRF, FFL))
        m = draw(ax, t, f, S, FTIP)
        if r == 0 and c == 0:
            CAP = caption(PRF, FFL, nper, len(t))
        ax.set_title(title, fontsize=FS - 0.5)
        if c == 0:
            ax.set_ylabel(f"R = {rng_m:.0f} m\nDoppler [Hz]")
        else:
            plt.setp(ax.get_yticklabels(), visible=False)
        if r == 2:
            ax.set_xlabel("Time [ms]")
        else:
            plt.setp(ax.get_xticklabels(), visible=False)

cax = fig.add_subplot(gs[:, 3])
fig.colorbar(m, cax=cax).set_label("Magnitude, each map to its own peak [dB]",
                                   fontsize=FS - 0.5)

fig.suptitle(f"{M['name']} hovering, belly view (az {M['az_deg']:.0f}, "
             f"el {M['el_deg']:.0f}), {M['fc_hz']/1e9:.1f} GHz — one row per range. "
             "Only the Sionna column is re-solved per range (true monostatic, "
             "rays scaled (R/3)²).", fontsize=FS + 0.5, y=0.965)

import textwrap                                                        # noqa: E402
cap = (CAP + "\n"
       "Middle and right columns are computed once on a target-anchored plane-wave "
       "grid, so they do not depend on range by construction — the repetition down "
       "each column is the point. Far-field boundary 2D²/λ ≈ 8.0 m: "
       "the 3 m row is near-field for the Sionna column, 8 and 15 m are far-field. "
       "Sionna maps use ray budgets 1M / 7.1M / 25M (per-range level in each title; "
       "maps normalized to their own peak). Depth is quoted as the 5-95 percentile spread because a single ray-starved pose can set the full peak-to-peak on its own — the gap between the two numbers is itself a stability measure. Individual blade flashes are resolved here but crowd together over 200 ms, so figure 6 zooms one 60 ms window.")
# ⚠ 캡션 한 줄이 길면 bbox_inches="tight" 가 **그림 폭을 캡션에 맞춰 늘린다**(2026-08-10 실측:
#   f12 가 4652 px 로 벌어지고 오른쪽이 하얗게 남았다). 패널 폭에 맞춰 접는다.
cap = "\n".join(textwrap.fill(p, 150) for p in cap.split("\n"))
fig.text(0.062, 0.012, cap, fontsize=FS - 1.5, color="0.3", va="top")

for ext in ("png", "pdf"):
    fig.savefig(f"{ROOT}/outputs/figures/report07_f12.{ext}",
                bbox_inches="tight", facecolor="white")
plt.close(fig)
print("  ✅ outputs/figures/report07_f12.png")
for key in ROWS:
    v = RGS[key]
    print(f"     R={v['range_m']:4.0f} m  경로중앙 {v['paths_median']:.0f} · "
          f"빈자세 {v['paths_zero_frac']:.1%} · 레벨 {v['level_db']:.1f} dB")
