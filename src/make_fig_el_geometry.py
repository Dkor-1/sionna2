# -*- coding: utf-8 -*-
"""
make_fig_el_geometry.py — 권 16 절 1 의 **기하 한 장** → outputs/figures/ch1_f0_geometry.png
==========================================================================================
이 그림이 답하는 질문 하나 —
    «이 판은 표적을 어느 자리에서 보고, 그 자리에서 무엇이 한 축에 묶이나?»

(a) 잰 자리 — 반경 10 m 구면 위의 앙각 7 점. 송신과 수신은 같은 자리(baseline 0)다.
    원거리장 경계 2D²/λ 를 함께 그려 **10 m 가 그 안쪽**임을 눈으로 보인다.
(b) 그 축이 묶고 있는 것 둘 — 날개끝 속도의 시선 방향 성분(cos(el))과 동체 가림.
    메쉬를 통째로 넣었으므로 이 둘은 한 축 위에서 함께 움직인다.

원장에서 읽는 값 (손으로 치지 않는다)
    outputs/elevation_sweep_md.json : _meta.range_m · _meta.elevations_deg · _meta.range_why_ko
    (경계 14.08 m 는 range_why_ko 문자열에서 뽑는다 — 그 원장이 유일한 출처다)

⚠ 그림 안 글자는 **전부 영어**(하우스 규약, `assert_fig_text` 가 검사한다).
⚠ 그림 안에 하이퍼파라미터(광선 수·격자·PRF·STFT 설정)를 쓰지 않는다 — 기하만 그린다.
⛔ GPU 를 쓰지 않는다. 원장 JSON 하나를 읽고 CPU 로 그린다.

실행
    cd /workspace/sionna
    PYTHONPATH=src ~/.venvs/py312/bin/python src/make_fig_el_geometry.py
"""
from __future__ import annotations

import os
import re
import sys

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt                                          # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from report_style import assert_fig_text, fetch, load_json                # noqa: E402

J = "outputs/elevation_sweep_md.json"
FIG = os.path.join(_ROOT, "outputs", "figures")
OUT = os.path.join(FIG, "ch1_f0_geometry.png")

R = float(fetch((J, "_meta.range_m")))
ELS = [float(x) for x in load_json(os.path.join(_ROOT, J))["_meta"]["elevations_deg"]]
_WHY = str(fetch((J, "_meta.range_why_ko")))
_M = re.search(r"≈\s*([0-9.]+)\s*m", _WHY)
if not _M:
    raise SystemExit("⛔ 원거리장 경계를 _meta.range_why_ko 에서 못 읽었다")
RFF = float(_M.group(1))

INK, SEA, RUST, SAND = "#22313f", "#1f6f8b", "#b03a2e", "#c9a227"

plt.rcParams.update({
    "font.size": 11, "axes.titlesize": 12.5, "axes.labelsize": 11,
    "legend.fontsize": 10, "figure.facecolor": "white",
    "savefig.facecolor": "white", "axes.axisbelow": True,
})

TXT: list[str] = []


def T(s: str) -> str:
    """그림에 들어가는 글자를 전부 모아 둔다 — 마지막에 영어인지 검사한다."""
    TXT.append(s)
    return s


def drone_side(ax, x, y, s=1.0, color=INK):
    """옆에서 본 기체 — 동체 + 로터 두 개(면으로 보이는 원반은 선으로)."""
    ax.add_patch(plt.Rectangle((x - 0.9 * s, y - 0.16 * s), 1.8 * s, 0.32 * s,
                               fc=color, ec="none", zorder=5))
    for sx in (-1, 1):
        ax.plot([x + sx * 1.45 * s, x + sx * 0.55 * s], [y + 0.30 * s] * 2,
                color=color, lw=2.4 * s, solid_capstyle="round", zorder=5)
        ax.plot([x + sx * 0.95 * s] * 2, [y + 0.16 * s, y + 0.30 * s],
                color=color, lw=1.6 * s, zorder=5)


def drone_bottom(ax, x, y, s=1.0, color=INK):
    """아래에서 본 기체 — 동체 원반이 로터 원반 앞에 온다."""
    for dx, dy in ((-1, 1), (1, 1), (-1, -1), (1, -1)):
        ax.add_patch(plt.Circle((x + dx * 0.95 * s, y + dy * 0.95 * s), 0.62 * s,
                                fc="none", ec=color, lw=1.6, zorder=4))
        ax.plot([x + dx * 0.30 * s, x + dx * 0.95 * s],
                [y + dy * 0.30 * s, y + dy * 0.95 * s], color=color, lw=1.8, zorder=4)
    ax.add_patch(plt.Circle((x, y), 0.72 * s, fc="#d7dde3", ec=color, lw=1.8, zorder=6))


fig, axs = plt.subplots(1, 2, figsize=(15.2, 6.6),
                        gridspec_kw=dict(width_ratios=[1.05, 1.0]))

# ══ (a) 잰 자리 ═════════════════════════════════════════════════════════════
ax = axs[0]
ax.set_aspect("equal")
th = np.radians(np.linspace(-96.0, 8.0, 400))

ax.fill(np.concatenate([R * np.cos(th), RFF * np.cos(th[::-1])]),
        np.concatenate([R * np.sin(th), RFF * np.sin(th[::-1])]),
        color=RUST, alpha=0.10, zorder=0, lw=0)
ax.plot(RFF * np.cos(th), RFF * np.sin(th), ls=(0, (6, 4)), color=RUST, lw=1.8, zorder=2)
ax.plot(R * np.cos(th), R * np.sin(th), color=SEA, lw=1.2, alpha=0.55, zorder=2)

for el in ELS:
    a = np.radians(el)
    px, py = R * np.cos(a), R * np.sin(a)
    ax.annotate("", xy=(0.9 * np.cos(a), 0.9 * np.sin(a)), xytext=(px, py),
                arrowprops=dict(arrowstyle="-|>", color=SEA, lw=1.5,
                                shrinkA=6, shrinkB=0, alpha=0.85), zorder=3)
    ax.plot([px], [py], "o", ms=8.5, mfc="white", mec=SEA, mew=2.0, zorder=6)
    lx, ly = (R - 1.75) * np.cos(a), (R - 1.75) * np.sin(a)
    ax.text(lx, ly, T(f"{el:+.0f}°"), color=SEA, fontsize=11.5, fontweight="bold",
            ha="center", va="center", zorder=7,
            bbox=dict(fc="white", ec="none", alpha=0.88, pad=1.6))

drone_side(ax, 0.0, 0.0, s=0.85)
ax.text(0.0, 1.5, T("target"), ha="center", va="bottom", fontsize=11.5,
        fontweight="bold", color=INK)
ax.text(5.0, 0.55, T(f"R = {R:.0f} m"), ha="center", va="bottom",
        fontsize=12, color=SEA, fontweight="bold")
ax.text(19.0, 2.5, T(f"far-field boundary  2D²/λ = {RFF:.2f} m"),
        color=RUST, fontsize=11.5, ha="right", va="bottom", fontweight="bold")
ax.text(12.1 * np.cos(np.radians(-52)), 12.1 * np.sin(np.radians(-52)),
        T("near-field side"), color=RUST, fontsize=11,
        ha="center", va="center", rotation=38, alpha=0.95)
ax.text(-2.2, -16.2, T("open marker = sensor position, transmit and receive\n"
                       "at the same point   |   azimuth 0°: all seven look\n"
                       "directions lie in this plane"),
        fontsize=10.5, color=INK, ha="left", va="bottom",
        bbox=dict(fc="white", ec="#d0d7de", lw=0.8, pad=6))

ax.set_xlim(-3.0, 19.2)
ax.set_ylim(-16.6, 4.4)
ax.set_xlabel(T("horizontal distance from target [m]"))
ax.set_ylabel(T("height relative to target [m]"))
ax.set_title(T("(a) One range, seven look directions"), loc="left", pad=10)
ax.grid(alpha=0.22)

# ══ (b) 한 축이 묶고 있는 것 둘 ═════════════════════════════════════════════
ax = axs[1]
ax.set_aspect("equal")
ax.set_xlim(0, 10)
ax.set_ylim(0, 7.4)
ax.axis("off")
ax.set_title(T("(b) What one mesh bundles onto that same axis"), loc="left", pad=10)

for x0, x1 in ((0.20, 4.85), (5.15, 9.80)):
    ax.add_patch(plt.Rectangle((x0, 0.30), x1 - x0, 6.85, fc="#f6f8fa",
                               ec="#d0d7de", lw=1.0, zorder=0))

# ── 왼쪽: el = 0° (옆에서 본다) ────────────────────────────────────────────
ax.text(2.52, 6.85, T("blade tip velocity"), color=SAND, fontsize=11,
        ha="center", va="top", fontweight="bold")
drone_side(ax, 2.60, 5.20, s=0.95, color=INK)
for sx, y1 in ((-1, 6.25), (1, 4.60)):
    bx = 2.60 + sx * 1.30
    ax.annotate("", xy=(bx, y1), xytext=(bx, 5.42),
                arrowprops=dict(arrowstyle="-|>", color=SAND, lw=2.4))
ax.annotate("", xy=(1.55, 5.20), xytext=(0.60, 5.20),
            arrowprops=dict(arrowstyle="-|>", color=SEA, lw=2.4))
ax.text(0.55, 4.78, T("line of sight"), color=SEA, fontsize=10.5, ha="left")
ax.annotate("", xy=(3.55, 4.20), xytext=(1.60, 4.20),
            arrowprops=dict(arrowstyle="-|>,head_width=0.26", color=RUST, lw=2.4))
ax.text(2.52, 3.85, T("full component\nalong the line of sight"),
        color=RUST, fontsize=10.5, ha="center", va="top")
ax.text(2.52, 2.05, T("el = 0°\nrotor plane edge-on,\nbody beside the rotors"),
        fontsize=11.5, ha="center", va="top", color=INK, fontweight="bold")

# ── 오른쪽: el = −90° (아래에서 본다) ──────────────────────────────────────
ax.text(7.47, 6.85, T("tip velocity turns perpendicular"), color=SAND,
        fontsize=11, ha="center", va="top", fontweight="bold")
drone_bottom(ax, 7.47, 5.05, s=0.86, color=INK)
for dx, dy in ((-1, 1), (1, 1), (-1, -1), (1, -1)):
    cx, cy = 7.47 + dx * 0.82, 5.05 + dy * 0.82
    ax.annotate("", xy=(cx + dy * 0.62, cy - dx * 0.62),
                xytext=(cx + dy * 0.08, cy - dx * 0.74),
                arrowprops=dict(arrowstyle="-|>", color=SAND, lw=2.1,
                                connectionstyle="arc3,rad=0.35"))
ax.plot([7.47], [5.05], "x", ms=12, mew=2.8, color=RUST, zorder=8)
ax.text(7.47, 3.85, T("x = line of sight, into the page"),
        color=RUST, fontsize=10.5, ha="center", va="top")
ax.text(7.47, 3.30, T("body disc covers part of the rotors"),
        color=INK, fontsize=10.5, ha="center", va="top")
ax.text(7.47, 2.05, T("el = −90°\nrotor plane face-on,\nbody between rotors\n"
                      "and sensor"),
        fontsize=11.5, ha="center", va="top", color=INK, fontweight="bold")

fig.suptitle(T("CH1-F0   Where the elevation sweep looks from, and what moves with "
               "that one axis"), fontsize=14, y=0.985)

assert_fig_text(*TXT)
os.makedirs(FIG, exist_ok=True)
fig.savefig(OUT, dpi=170, bbox_inches="tight")
plt.close(fig)
print(f"  ✅ {OUT}")
