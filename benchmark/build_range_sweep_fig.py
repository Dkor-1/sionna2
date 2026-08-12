# -*- coding: utf-8 -*-
"""
build_range_sweep_fig.py — ⭐**거리와 광선 예산** — 무엇이 진짜 한계인가.

이 그림을 다시 짠 이유 (2026-08-10, 사용자: *"대체 뭘 의미하는지 아예 모르겠어"*)
---------------------------------------------------------------------------
옛 판은 여섯 패널이었고 **읽을 수 없었다.** 무엇이 문제였는지 정직하게 적는다.
  ⓵ 윗줄 맵 넷을 **각자 최대로 정규화**해 놓아서, 40 m 판이 빨갛게 타올라 «신호가 세다» 로
     읽혔다. 실제로는 그 판의 78 %가 경로 0 이고 빨간 것은 **바닥 잡음을 늘린 것**이었다.
     그림이 사실의 반대를 말하고 있었다.
  ⓶ 아랫줄 왼쪽의 계단선 네 겹은 500 자세를 한 축에 눌러 담아 무늬가 안 보였다.
  ⓷ 아랫줄 오른쪽의 −505 dB 점은 log(0) 산술이지 물리량이 아니다.
  ⓸ ⭐그리고 결정적으로 — 그 판 전체가 **광선을 규칙값의 0.18 배만 쏜 것**이었다.
     별도 결판 시험이 그것을 밝혔다(아래).

그래서 이 그림은 **질문을 바꾼다.** «거리가 멀면 못 보나» 가 아니라
**«거리가 멀 때 광선을 얼마나 부어야 하나, 그 비용이 감당되나»** 를 묻는다.

무엇을 그리나 — 세 패널, 각각 한 문장
  (a) 40 m 에서 **광선만** 늘린 사다리 → 빈 자세가 77.3 % 에서 **0 %** 로 사라진다.
      ⇒ 40 m 붕괴는 «PathSolver 의 구조» 가 아니라 **예산 부족**이었다.
  (b) 거리별로 규칙값 (R/3)²·1M 이 얼마인가 vs 우리가 실제로 쓴 값.
      ⇒ 부족분이 거리와 함께 벌어진다. 이것이 옛 판이 무너져 보인 이유다.
  (c) ⭐그럼에도 남는 것 — **비용**. ⭐이 판은 **측정만** 싣는다. 두 팔이 같은 자세 4096 개·
      같은 기하·같은 슬로타임 격자로 돈 자세당 벽시계 초다. PathSolver 는 (b) 의 (R/3)² 규칙
      예산(1M / 25M / 178M 발)을, 우리 SBR+PO 는 거리마다 다시 돌린 얼린 격자를 쓴다.
      정본 서술(RETRACTION_LOG R26) — 가까운 거리에서 최소 예산이면 PathSolver 가 싸고,
      멀어지거나 예산을 올리면 우리 커널이 싸다.

읽는 것: outputs/report07_ray_budget_test.json      (결판 시험 — 40 m 광선 사다리)
         outputs/report07_sionna_ranges.json        (거리 스윕 — 예산 부족 판이라고 표시)
         outputs/report07_three_engine_ranges.json  (PathSolver 실측 자세당 초 · 3 / 15 m)
         outputs/report07_range40_raybudget.json    (PathSolver 실측 자세당 초 · 40 m 두 예산)
         outputs/deck_ours_by_range.json            (우리 SBR+PO 실측 자세당 초 · 3 / 15 / 40 m)
쓰는 것: outputs/figures/report07_f9.{png,pdf}
"""
from __future__ import annotations

import json
import os
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIGDIR = f"{ROOT}/outputs/figures"

RB = json.load(open(f"{ROOT}/outputs/report07_ray_budget_test.json"))
RBM, LAD = RB["_meta"], RB["ladder"]
SW = json.load(open(f"{ROOT}/outputs/report07_sionna_ranges.json"))
SWM, SWR = SW["_meta"], SW["ranges"]

# ── (c) 판이 읽는 원장 셋 — 전부 자세 4096 개의 **실측** 벽시계 초다 ─────────
#  ⭐두 팔을 같은 자세 수로 나눈다. 정규화를 안 하고 절대 초를 그대로 그린다.
DK = json.load(open(f"{ROOT}/outputs/deck_ours_by_range.json"))
DKM, DKR = DK["_meta"], DK["ranges"]
TER = json.load(open(f"{ROOT}/outputs/report07_three_engine_ranges.json"))
R40 = json.load(open(f"{ROOT}/outputs/report07_range40_raybudget.json"))

#: 우리 SBR+PO — 거리마다 다시 돌린 얼린 격자(위상만 구면파)
OUR_R = [DKR[k]["range_m"] for k in ("3", "15", "40")]
OUR_S = [DKR[k]["cpu_seconds"] / DKM["n"] for k in ("3", "15", "40")]
#: PathSolver — 규칙 예산 판. 3 / 15 m 는 세 엔진 거리 원장, 40 m 는 예산 원장의 178 M 판
_R40_RULE = [r for r in R40["rows"] if r["spp"] < 1e9]
_R40_BIG = [r for r in R40["rows"] if r["spp"] >= 1e9]
PS_R = [TER["ranges"]["R3"]["range_m"], TER["ranges"]["R15"]["range_m"],
        R40["_meta"]["range_m"]]
PS_S = [TER["ranges"]["R3"]["seconds"] / TER["_meta"]["n"],
        TER["ranges"]["R15"]["seconds"] / TER["_meta"]["n"],
        _R40_RULE[0]["seconds"] / _R40_RULE[0]["n_poses"]]
PS_RAYS = [TER["ranges"]["R3"]["spp"], TER["ranges"]["R15"]["spp"],
           _R40_RULE[0]["spp"]]
#: 같은 40 m 에서 예산만 22.5 배 올린 판 — 시드 두 개의 평균
BIG_S = sum(r["seconds"] / r["n_poses"] for r in _R40_BIG) / len(_R40_BIG)
BIG_RAYS = _R40_BIG[0]["spp"]
#: (b) 스윕의 PathSolver 실측 초 — 캡션이 «평평하다» 고 적는 근거
SW_S = [SWR[k]["seconds"] / SWM["n"] for k in SWR]

FS = 10.0
plt.rcParams.update({
    "font.size": FS, "axes.labelsize": FS, "axes.titlesize": FS,
    "xtick.labelsize": FS - 1, "ytick.labelsize": FS - 1, "legend.fontsize": FS - 1.5,
    "axes.linewidth": 0.9, "figure.dpi": 200, "savefig.dpi": 200,
    "font.family": "DejaVu Sans",
})

C_OK, C_BAD, C_OURS = "#1b6ca8", "#c62828", "#2e7d32"

fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.0))
fig.subplots_adjust(left=0.055, right=0.985, top=0.80, bottom=0.165, wspace=0.30)

# ── (a) 40 m 에서 광선만 늘린 사다리 ────────────────────────────────────────
ax = axes[0]
spp = np.array([LAD[k]["spp"] for k in LAD], float) / 1e6
zero = np.array([LAD[k]["zero_frac"] for k in LAD]) * 100.0
med = np.array([LAD[k]["paths_median"] for k in LAD])
ax.plot(spp, zero, "-o", color=C_BAD, lw=2.0, ms=7, label="Poses with no path")
ax.set_xscale("log")
ax.set_xlabel("Rays launched per pose [millions]")
ax.set_ylabel("Poses with no path [%]", color=C_BAD)
ax.tick_params(axis="y", labelcolor=C_BAD)
ax.set_ylim(-4, 88)
ax.grid(alpha=0.25, lw=0.5)
from matplotlib.ticker import NullFormatter, NullLocator
ax.set_xticks(spp)
ax.set_xticklabels([f"{v:.0f}M" for v in spp])
ax.xaxis.set_minor_locator(NullLocator())        # ⚠로그축 부눈금 라벨이 겹쳐 읽히지 않았다
ax.xaxis.set_minor_formatter(NullFormatter())
axr = ax.twinx()
axr.plot(spp, med, "-s", color=C_OK, lw=1.8, ms=6, label="Median paths per pose")
axr.set_ylabel("Median paths per pose", color=C_OK)
axr.tick_params(axis="y", labelcolor=C_OK)
axr.set_ylim(-0.3, max(med) * 1.35)
rule = RBM["rule_value_spp"] / 1e6
ax.axvline(rule, color="0.45", ls=":", lw=1.2)
ax.set_title(f"(a) PathSolver at {RBM['range_m']:.0f} m, rays alone fix it\n"
             f"{zero[0]:.0f}% empty at {spp[0]:.0f}M, {zero[1]:.0f}% at {spp[1]:.0f}M",
             fontsize=FS)
h1, l1 = ax.get_legend_handles_labels()
h2, l2 = axr.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, loc="center right", framealpha=0.92)

# ── (b) 규칙값 대 실제로 쓴 값 ──────────────────────────────────────────────
ax = axes[1]
rng = np.array([SWR[k]["range_m"] for k in SWR], float)
used = np.array([SWR[k]["spp"] for k in SWR], float) / 1e6
need = 1.0 * (rng / 3.0) ** 2
x = np.arange(len(rng))
ax.bar(x - 0.2, need, width=0.38, color="0.72", label="Rays needed, (R/3)$^2$ rule")
ax.bar(x + 0.2, used, width=0.38, color=C_BAD, label="Rays actually launched")
for i, (n, u) in enumerate(zip(need, used)):
    ax.text(i + 0.2, u * 1.25, f"{u/n:.2f}x", ha="center", fontsize=FS - 2, color=C_BAD)
ax.set_yscale("log")
ax.set_xticks(x)
ax.set_xticklabels([f"{r:.0f} m" for r in rng])
ax.set_ylabel("Rays per pose [millions]")
ax.set_xlabel("Range")
ax.grid(axis="y", alpha=0.25, lw=0.5)
ax.legend(loc="upper left", framealpha=0.92)
ax.set_title("(b) PathSolver budget: this sweep under-launched,\nand the gap widens with range",
             fontsize=FS)

# ── (c) 비용 — 실측만 싣는다(규칙 곡선은 (b) 에 있다) ───────────────────────
ax = axes[2]
ax.plot(PS_R, PS_S, "-s", color=C_BAD, lw=2.0, ms=6.5,
        label="PathSolver, rule-sized budget, measured")
ax.plot([R40["_meta"]["range_m"]], [BIG_S], "^", color=C_BAD, ms=10,
        mfc="none", mew=1.9,
        label=f"PathSolver at {R40['_meta']['range_m']:.0f} m, "
              f"{BIG_RAYS/1e6:,.0f} M rays")
ax.plot(OUR_R, OUR_S, "-o", color=C_OURS, lw=2.2, ms=7,
        label="Ours (SBR+PO), measured")
for r, s, ray in zip(PS_R, PS_S, PS_RAYS):
    ax.annotate(f"{ray/1e6:,.0f} M", (r, s), textcoords="offset points",
                xytext=(0, -15), ha="center", fontsize=FS - 2.5, color=C_BAD)
ax.annotate(f"{BIG_RAYS/1e6:,.0f} M", (R40["_meta"]["range_m"], BIG_S),
            textcoords="offset points", xytext=(0, 10), ha="center",
            fontsize=FS - 2.5, color=C_BAD)
ax.set_yscale("log")
ax.set_xlim(0, 47)
ax.set_xticks(OUR_R)
ax.set_xticklabels([f"{r:.0f} m" for r in OUR_R])
ax.set_ylim(0.13, 45.0)                          # 범례가 앉을 자리를 위에 비운다
ax.set_xlabel("Range")
ax.set_ylabel(f"Measured wall time per pose [s], {DKM['n']:,} poses")
ax.grid(alpha=0.25, lw=0.5)
ax.legend(loc="upper left", framealpha=0.92)
ax.set_title(f"(c) Measured cost, {DKM['n']:,} poses on both arms.\n"
             f"Budget moves it {BIG_S/PS_S[2]:.1f}x, range {PS_S[2]/PS_S[0]:.1f}x",
             fontsize=FS)

fig.suptitle(f"{SWM['name']} hovering, belly view, {SWM['fc_hz']/1e9:.1f} GHz. "
             "Is range a wall for the path solver, or a budget?",
             fontsize=FS + 1.5, y=0.955)

cap = ("Panels (a) and (b) carry the path-solver arm alone: the two ledgers behind them hold only "
       "path-solver keys, so the SBR+PO arm has no range point there. Its cost comes from its own "
       "ledger and appears in panel (c). "
       "(a) Range, geometry, poses and rotor speeds are all held fixed at "
       f"{RBM['range_m']:.0f} m. Only the ray count changes, and the empty poses vanish, so the "
       "collapse at that range is a budget shortfall rather than a property of the solver. "
       "(b) The grey bars are the rule, rays scaled as (R/3) squared from the 3 m case; the red "
       "bars are what this sweep launched. Its wall time is flat across range "
       f"({SW_S[0]:.3f} s per pose at {SWR['R3']['range_m']:.0f} m down to {SW_S[-1]:.3f} s at "
       f"{SWR['R40']['range_m']:.0f} m, {SWM['n']} poses) because the budget stayed near the 3 m "
       "value. "
       "(c) Measurement only, at rule-sized budgets; the rule itself is panel (b). Both arms run "
       f"the same {DKM['n']:,} poses, same airframe, azimuth 0 and elevation "
       f"{DKM['el_deg']:.0f} deg, {DKM['fc_hz']/1e9:.1f} GHz, {DKM['prf_hz']/1e3:.1f} kHz "
       "slow time. PathSolver budgets follow the panel (b) rule ("
       + ", ".join(f"{r/1e6:,.0f} M at {x:.0f} m" for r, x in zip(PS_RAYS, PS_R))
       + "), while ours is one frozen ray grid re-solved per range with spherical-wave phase. "
       "At short range on the minimum budget PathSolver costs less per pose, and cost crosses "
       "over as range or budget grows. Ledgers: report07_ray_budget_test.json, "
       "report07_sionna_ranges.json, report07_three_engine_ranges.json, "
       "report07_range40_raybudget.json, deck_ours_by_range.json.")
fig.text(0.055, 0.045, "\n".join(textwrap.fill(p, 170) for p in cap.split("\n")),
         fontsize=FS - 2.2, color="0.3", va="top")

for ext in ("png", "pdf"):
    fig.savefig(f"{FIGDIR}/report07_f9.{ext}", bbox_inches="tight", facecolor="white")
plt.close(fig)
print("  ✅ outputs/figures/report07_f9.png — 광선 예산 판")
for k in LAD:
    v = LAD[k]
    print(f"     {k:>6s}  경로중앙 {v['paths_median']:.0f} · 빈자세 {v['zero_frac']:.1%}")
print(f"  (c) 실측 자세당 초 · 자세 {DKM['n']:,} 개")
for r, s, ray in zip(PS_R, PS_S, PS_RAYS):
    print(f"     PathSolver {r:5.0f} m  {ray/1e6:7,.0f} M 발  {s:.3f} s")
print(f"     PathSolver {R40['_meta']['range_m']:5.0f} m  {BIG_RAYS/1e6:7,.0f} M 발  "
      f"{BIG_S:.3f} s (시드 {len(_R40_BIG)} 판 평균)")
for r, s in zip(OUR_R, OUR_S):
    print(f"     Ours       {r:5.0f} m  {'얼린 격자':>12s}  {s:.3f} s")
