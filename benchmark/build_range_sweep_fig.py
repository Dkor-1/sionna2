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
  (c) ⭐그럼에도 남는 것 — **비용**. 같은 경로 수를 유지하려면 광선이 R² 로 늘고,
      자세 수천 개를 쌓는 마이크로도플러에서는 그 곱이 감당 밖으로 간다.
      반면 우리 SBR+PO 는 표적 앵커 평면파라 **거리에 불변**이다(수평선).

읽는 것: outputs/report07_ray_budget_test.json (결판 시험)
         outputs/report07_sionna_ranges.json   (거리 스윕 — 예산 부족 판이라고 표시)
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
ax.set_title(f"(a) At {RBM['range_m']:.0f} m, rays alone fix it\n"
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
ax.set_title("(b) The old sweep under-launched, and the\ngap widens with range", fontsize=FS)

# ── (c) 비용 — 무엇이 진짜 남는 한계인가 ────────────────────────────────────
ax = axes[2]
rr = np.linspace(3, 120, 300)
ax.plot(rr, (rr / 3.0) ** 2, "-", color=C_BAD, lw=2.2,
        label="PathSolver, rays $\\propto R^2$")
ax.axhline(1.0, color=C_OURS, lw=2.2, ls="-",
           label="Ours (SBR+PO), range invariant")
ax.set_yscale("log")
ax.set_xlabel("Range [m]")
ax.set_ylabel("Relative cost per pose (3 m = 1)")
ax.grid(alpha=0.25, lw=0.5)
ax.legend(loc="upper left", framealpha=0.92)
for r in (40.0, 100.0):
    ax.plot([r], [(r / 3.0) ** 2], "o", color=C_BAD, ms=6)
    ax.annotate(f"{(r/3.0)**2:.0f}x", (r, (r / 3.0) ** 2),
                textcoords="offset points", xytext=(6, -12), fontsize=FS - 2, color=C_BAD)
ax.set_title("(c) What actually remains is cost, and it\ngrows while ours does not", fontsize=FS)

fig.suptitle(f"{SWM['name']} hovering, belly view, {SWM['fc_hz']/1e9:.1f} GHz. "
             "Is range a wall for the path solver, or a budget?",
             fontsize=FS + 1.5, y=0.955)

cap = ("(a) Range, geometry, poses and rotor speeds are all held fixed at "
       f"{RBM['range_m']:.0f} m. Only the ray count changes, and the empty poses vanish, so the "
       "earlier collapse was a budget shortfall on our side rather than a property of the solver. "
       "(b) The dashed rule is rays scaled as (R/3) squared from the 3 m case. "
       "(c) Cost is the honest limit. Holding the path count needs rays growing as R squared, and "
       "a micro-Doppler run stacks thousands of poses on top of that, while our target-anchored "
       "plane-wave grid is computed once and does not depend on range.")
fig.text(0.055, 0.045, "\n".join(textwrap.fill(p, 170) for p in cap.split("\n")),
         fontsize=FS - 2.2, color="0.3", va="top")

for ext in ("png", "pdf"):
    fig.savefig(f"{FIGDIR}/report07_f9.{ext}", bbox_inches="tight", facecolor="white")
plt.close(fig)
print("  ✅ outputs/figures/report07_f9.png — 광선 예산 판으로 재작성")
for k in LAD:
    v = LAD[k]
    print(f"     {k:>6s}  경로중앙 {v['paths_median']:.0f} · 빈자세 {v['zero_frac']:.1%}")
