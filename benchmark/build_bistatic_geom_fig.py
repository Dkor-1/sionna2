# -*- coding: utf-8 -*-
"""
build_bistatic_geom_fig.py — 그림 g1: **바이스태틱 기하 설명도** (matplotlib 만, GPU 불필요)

이 그림이 답하는 것 — «바이스태틱이 되면 무엇이 달라지는가» 를 계산 전에 눈으로 못박는다.
  (a) 등거리합 타원 — 모노의 **원**이 바이스태틱에서 **타원**이 된다(초점이 둘). β·이등분선.
  (b) 속도가 왜 이등분선으로 투영되는가 — û_i + û_s = 2cos(β/2)·û_b 라는 벡터 항등식.
      ⭐그런데 우리 표적의 속도(로터 날개끝)는 **수평**이라, 실제로 재는 것은
      |horiz(û_i+û_s)| 이고 이등분선이 기울면 cos(β/2) 만으로는 안 맞는다.
  (c) 그래서 예측이 **둘**이다 — 교과서 축약 cos(β/2) 와 우리 기하의 정확한 값.

읽는 것: outputs/report07b_bistatic_md.json  (β·φ·이등분선은 원장에서 읽는다 — 하드코딩 금지)
쓰는 것: outputs/figures/report07b_g1.{png,pdf}

    cd sionna2 && PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/build_bistatic_geom_fig.py
"""
from __future__ import annotations

import json
import os
import sys
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Arc, Ellipse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

J = json.load(open(f"{ROOT}/outputs/report07b_bistatic_md.json"))
M = J["_meta"]
FIGDIR = f"{ROOT}/outputs/figures"
EL = float(M["el_deg"])

FS = 9.5
plt.rcParams.update({
    "font.size": FS, "axes.labelsize": FS, "axes.titlesize": FS,
    "xtick.labelsize": FS - 1, "ytick.labelsize": FS - 1, "legend.fontsize": FS - 1.5,
    "axes.linewidth": 0.9, "figure.dpi": 200, "savefig.dpi": 200,
    "font.family": "DejaVu Sans", "mathtext.fontset": "dejavusans",
})

C_TX, C_RX, C_TGT = "#1565c0", "#c62828", "#2e7d32"
C_BIS, C_A, C_B = "#6a1b9a", "#444444", "#1565c0"


# ── 예측 곡선 (닫힌 식) — 원장의 β별 값과 대조해 어긋나면 멈춘다 ──────────────
def phi_of_beta(beta, el):
    """등부각 원뿔에서 β 를 내는 **방위차** φ.  cos β = cos²el·cos φ + sin²el."""
    ce, se = np.cos(np.radians(el)), np.sin(np.radians(el))
    c = (np.cos(np.radians(beta)) - se * se) / (ce * ce)
    return np.where(np.abs(c) <= 1.0, np.degrees(np.arccos(np.clip(c, -1, 1))), np.nan)


def ratio_azimuth(beta, el):
    """방위면(등부각 원뿔): |horiz(û_i+û_s)| / (2cos el) = cos(φ/2)."""
    return np.cos(np.radians(phi_of_beta(beta, el)) / 2.0)


def ratio_elevation(beta, el):
    """앙각면: (cos el + cos(el+β)) / (2 cos el)."""
    return (np.cos(np.radians(el)) + np.cos(np.radians(el + beta))) / (2 * np.cos(np.radians(el)))


for r in J["rows"]:
    f = ratio_azimuth if r["plane"] == "azimuth" else ratio_elevation
    assert abs(float(f(r["beta_deg"], EL)) - r["pred_bisector_horiz"]) < 1e-9, \
        f"그림의 닫힌 식이 원장과 다르다: {r['label']}"

fig = plt.figure(figsize=(13.6, 4.55))
gs = fig.add_gridspec(1, 3, width_ratios=[1.02, 0.92, 1.10], wspace=0.26)
gsb = gs[0, 1].subgridspec(2, 1, height_ratios=[1.0, 1.22], hspace=0.30)

# ─────────────────────────────────────────────────────────────────────────── #
#  (a) 등거리합 타원 — 모노의 원이 바이스태틱에서 타원이 된다
# ─────────────────────────────────────────────────────────────────────────── #
ax = fig.add_subplot(gs[0, 0])
L = 2.9                                     # 기선(TX–RX) — 타원의 이심률이 보이게
tx, rx = np.array([-L / 2, 0.0]), np.array([+L / 2, 0.0])
tgt = np.array([0.45, 1.35])
Rt, Rr = np.linalg.norm(tgt - tx), np.linalg.norm(tgt - rx)
Ssum = Rt + Rr                              # 등거리합
a_e, c_e = Ssum / 2.0, L / 2.0
b_e = np.sqrt(a_e ** 2 - c_e ** 2)
ax.add_patch(Ellipse((0, 0), 2 * a_e, 2 * b_e, fill=False, ec=C_TGT, lw=1.6,
                     label="Bistatic iso-range-sum (ellipse)"))
ax.add_patch(plt.Circle((0, 0), Ssum / 2.0, fill=False, ec="#999999", lw=1.3, ls="--",
                        label="Monostatic iso-range (circle)"))

ui = (tx - tgt) / Rt                         # 표적 → TX
us = (rx - tgt) / Rr                         # 표적 → RX
beta = np.degrees(np.arccos(np.clip(ui @ us, -1, 1)))
bis = (ui + us) / np.linalg.norm(ui + us)
for p, u, c, lab in ((tgt, ui, C_TX, None), (tgt, us, C_RX, None)):
    ax.annotate("", xy=p + u * 0.62, xytext=p,
                arrowprops=dict(arrowstyle="-|>", lw=1.8, color=c))
ax.plot([tx[0], tgt[0]], [tx[1], tgt[1]], color=C_TX, lw=1.0, alpha=0.55)
ax.plot([rx[0], tgt[0]], [rx[1], tgt[1]], color=C_RX, lw=1.0, alpha=0.55)
ax.plot([tx[0], rx[0]], [tx[1], rx[1]], color="#555555", lw=1.0, ls=":")
ax.annotate("", xy=tgt + bis * 0.95, xytext=tgt,
            arrowprops=dict(arrowstyle="-|>", lw=2.0, color=C_BIS, ls="-"))
a0 = np.degrees(np.arctan2(ui[1], ui[0]))
a1 = np.degrees(np.arctan2(us[1], us[0]))
ax.add_patch(Arc(tgt, 0.80, 0.80, theta1=min(a0, a1), theta2=max(a0, a1),
                 color="k", lw=1.1))
ax.text(*(tgt + bis * 0.30 + np.array([0.14, -0.16])), r"$\beta$", fontsize=FS + 2.5)
ax.text(*(tgt + bis * 1.02), "bisector", color=C_BIS, fontsize=FS - 0.5,
        ha="center", va="bottom")
ax.text(*(tgt + ui * 0.68 + np.array([-0.05, 0.06])), r"$\hat u_i$", color=C_TX,
        fontsize=FS + 1.5, ha="right")
ax.text(*(tgt + us * 0.68 + np.array([0.05, 0.06])), r"$\hat u_s$", color=C_RX,
        fontsize=FS + 1.5, ha="left")
ax.plot(*tx, "s", ms=8, color=C_TX); ax.text(tx[0], tx[1] - 0.22, "TX", color=C_TX,
                                             ha="center", va="top", fontsize=FS)
ax.plot(*rx, "^", ms=9, color=C_RX); ax.text(rx[0], rx[1] - 0.22, "RX", color=C_RX,
                                             ha="center", va="top", fontsize=FS)
ax.plot(*tgt, "o", ms=8, color=C_TGT); ax.text(tgt[0] + 0.14, tgt[1] + 0.02, "target",
                                               color=C_TGT, fontsize=FS, va="bottom")
ax.text(0.0, -0.30, "baseline", color="#555555", ha="center", va="top", fontsize=FS - 1)
ax.set_title("(a) Two foci, not one: range becomes an ellipse")
ax.set_aspect("equal"); ax.axis("off")
ax.set_xlim(-a_e * 1.12, a_e * 1.12); ax.set_ylim(-b_e * 1.20, b_e * 1.25)
ax.legend(loc="lower center", frameon=False, ncol=1, fontsize=FS - 1.5,
          bbox_to_anchor=(0.5, -0.09))

# ─────────────────────────────────────────────────────────────────────────── #
#  (b) 벡터 항등식 û_i + û_s = 2cos(β/2)·û_b, 그리고 **수평 성분**만이 도플러를 만든다
# ─────────────────────────────────────────────────────────────────────────── #
BETA_DEMO = 90.0
phi_d = float(phi_of_beta(BETA_DEMO, EL))


def look(az, el):
    a, e = np.radians(az), np.radians(el)
    return np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])


UI, US = look(0.0, EL), look(phi_d, EL)
Q = UI + US
Qh = np.array([Q[0], Q[1], 0.0])

# (b1) 바이스태틱 평면 안의 벡터 합 — 길이가 2cos(β/2) 라는 항등식
ax = fig.add_subplot(gsb[0, 0])
h = np.radians(BETA_DEMO) / 2.0
vi, vs = np.array([np.cos(h), np.sin(h)]), np.array([np.cos(h), -np.sin(h)])
vq = vi + vs
for v, c, lab, dy in ((vi, C_TX, r"$\hat u_i$", 0.10), (vs, C_RX, r"$\hat u_s$", -0.10)):
    ax.annotate("", xy=v, xytext=(0, 0), arrowprops=dict(arrowstyle="-|>", lw=2.0, color=c))
    ax.text(v[0] * 1.06, v[1] + dy, lab, color=c, fontsize=FS + 1.5, ha="left", va="center")
ax.plot([vi[0], vq[0]], [vi[1], vq[1]], color="#aaaaaa", lw=0.9, ls=":")
ax.plot([vs[0], vq[0]], [vs[1], vq[1]], color="#aaaaaa", lw=0.9, ls=":")
ax.annotate("", xy=vq, xytext=(0, 0), arrowprops=dict(arrowstyle="-|>", lw=2.6, color=C_BIS))
ax.add_patch(Arc((0, 0), 0.46, 0.46, theta1=-np.degrees(h), theta2=np.degrees(h),
                 color="k", lw=1.1))
ax.text(0.31, 0.0, r"$\beta$", fontsize=FS + 2.5, ha="center", va="center")
ax.text(vq[0] * 0.62, 0.22, r"$2\cos(\beta/2)$", color=C_BIS, fontsize=FS, ha="center")
ax.text(vq[0] * 1.02, -0.16, "bisector", color=C_BIS, fontsize=FS - 0.5, ha="center",
        va="top")
ax.set_title(r"(b) The sum $\hat u_i+\hat u_s$ shrinks as $2\cos(\beta/2)$…", pad=4)
ax.set_aspect("equal"); ax.axis("off")
ax.set_xlim(-0.18, 1.72); ax.set_ylim(-1.02, 1.02)

# (b2) 위에서 본 판 — 도플러를 만드는 것은 그 합의 **수평 성분**뿐이다
ax = fig.add_subplot(gsb[1, 0])
Rd = 0.52
th = np.linspace(0, 2 * np.pi, 240)
ax.plot(Rd * np.cos(th), Rd * np.sin(th), color=C_TGT, lw=1.4)
ax.plot([0], [0], "o", ms=5, color=C_TGT)
for v, c, lab, ha in ((UI[:2], C_TX, r"$\hat u_i$ (horiz.)", "left"),
                      (US[:2], C_RX, r"$\hat u_s$ (horiz.)", "left")):
    ax.annotate("", xy=v, xytext=(0, 0), arrowprops=dict(arrowstyle="-|>", lw=1.8, color=c))
    ax.text(v[0] * 1.10, v[1] * 1.10, lab, color=c, fontsize=FS - 0.5, ha=ha, va="center")
ax.annotate("", xy=Qh[:2], xytext=(0, 0),
            arrowprops=dict(arrowstyle="-|>", lw=2.6, color=C_B))
ax.text(Qh[0] * 0.52 - 0.16, Qh[1] * 0.52 + 0.10, r"$\mathrm{horiz}(\hat u_i+\hat u_s)$",
        color=C_B, fontsize=FS - 0.5, ha="right")
vaz = np.arctan2(Qh[1], Qh[0])
for k in range(6):                                   # 한 회전에 모든 방위를 훑는다
    aa = vaz + np.pi / 3 * k
    ax.annotate("", xy=(Rd * np.cos(aa), Rd * np.sin(aa)), xytext=(0, 0),
                arrowprops=dict(arrowstyle="-|>", lw=1.1, color="#e65100", alpha=0.35))
ax.annotate("", xy=(Rd * np.cos(vaz), Rd * np.sin(vaz)), xytext=(0, 0),
            arrowprops=dict(arrowstyle="-|>", lw=2.4, color="#e65100"))
ax.text(Rd * np.cos(vaz) * 0.62 + 0.10, Rd * np.sin(vaz) * 0.62 - 0.02, r"$v_{tip}$",
        color="#e65100", fontsize=FS, ha="left", va="top")
ax.set_title(r"…but only its horizontal part meets $v_{tip}$", pad=4)
ax.set_aspect("equal"); ax.axis("off")
ax.set_xlim(-0.80, 1.60); ax.set_ylim(-0.70, 1.60)

# ─────────────────────────────────────────────────────────────────────────── #
#  (c) 그래서 예측이 둘이다
# ─────────────────────────────────────────────────────────────────────────── #
ax = fig.add_subplot(gs[0, 2])
bb = np.linspace(0, 180, 721)
ax.plot(bb, np.cos(np.radians(bb) / 2), color=C_A, lw=2.2,
        label=r"A: textbook $\cos(\beta/2)$")
ax.plot(bb, ratio_azimuth(bb, EL), color=C_B, lw=2.2,
        label="B: azimuth plane (ours)")
ax.plot(bb, ratio_elevation(bb, EL), color="#e65100", lw=2.2, ls="-",
        label="B: elevation plane (control)")
for r in J["rows"]:
    c = C_B if r["plane"] == "azimuth" else "#e65100"
    mk = "o" if r["plane"] == "azimuth" else "s"
    ax.plot(r["beta_deg"], r["pred_bisector_horiz"], mk, color=c, ms=6,
            mec="white", mew=0.8, zorder=5)
ax.axhline(0, color="#bbbbbb", lw=0.8)
ax.set_xlim(0, 180); ax.set_ylim(-0.05, 1.08)
ax.set_xticks(np.arange(0, 181, 30))
ax.set_xlabel(r"Bistatic angle $\beta$  [deg]")
ax.set_ylabel(r"Blade-tip Doppler scale  $f_{tip}(\beta)/f_{tip}(0)$")
ax.set_title("(c) Two competing predictions the sweep must decide")
ax.legend(loc="lower left", frameon=False)
ax.grid(alpha=0.25, lw=0.6)

cap = textwrap.fill(
    "Passive bistatic geometry for the report-7 target and look direction. (a) The transmitter "
    "and the receiver are the two foci of the iso-range-sum ellipse, so a monostatic range "
    "circle becomes an ellipse and the target sees a bistatic angle beta with a bisector "
    "halfway between the two legs. (b) Doppler is set by the vector sum of the two unit "
    "directions, which has length 2cos(beta/2) along the bisector. The blade-tip velocity of a "
    "hovering rotorcraft lies in the horizontal rotor plane and sweeps every azimuth once per "
    "revolution, so the tip Doppler is fixed by the HORIZONTAL part of that sum, not by its "
    "length. (c) The two predictions therefore differ whenever the bisector tilts out of the "
    "rotor plane: A is the textbook shorthand, B is the exact projection for the geometry "
    "actually swept here. Panel (b) is drawn at beta = 90 deg in the azimuth plane; the marker "
    "positions in (c) are read from the sweep ledger, and the curves are the closed forms "
    "checked against it.", 168)
fig.text(0.5, -0.075, cap, ha="center", va="top", fontsize=FS - 1.5, color="#333333")

os.makedirs(FIGDIR, exist_ok=True)
for ext in ("png", "pdf"):
    fig.savefig(f"{FIGDIR}/report07b_g1.{ext}", bbox_inches="tight", facecolor="white")
plt.close(fig)
sz = os.path.getsize(f"{FIGDIR}/report07b_g1.png") / 1e6
print(f"  ✅ outputs/figures/report07b_g1.png ({sz:.2f} MB) · pdf "
      f"{os.path.getsize(f'{FIGDIR}/report07b_g1.pdf')/1e6:.2f} MB")
print(f"  기하 검산: β_demo {BETA_DEMO:.0f}° → φ {phi_d:.3f}° · "
      f"|û_i+û_s| {np.linalg.norm(Q):.4f} (=2cos(β/2) {2*np.cos(np.radians(BETA_DEMO)/2):.4f}) · "
      f"|horiz| {np.linalg.norm(Qh):.4f} · 축척 {np.linalg.norm(Qh)/(2*np.cos(np.radians(EL))):.4f}")
