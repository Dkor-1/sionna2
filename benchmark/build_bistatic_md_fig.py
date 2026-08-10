# -*- coding: utf-8 -*-
"""
build_bistatic_md_fig.py — 그림 g2: **β 스윕의 결과판**

무엇을 보이나 (윗줄부터)
  1행 방위면(우리 기하) β별 마이크로도플러 맵 — 흰 파선이 **예측 B**(이등분선 수평투영),
       검은 점선이 **예측 A**(교과서 cos(β/2)). 능선이 어느 선에 앉는가가 판정이다.
  2행 앙각면(대조군) — 같은 β 인데 이등분선이 로터면 밖으로 더 기운다. 두 예측이 크게 갈린다.
  3행 (k) 도플러 축척 예측 대 실측 · (l) 레벨 감쇠와 게이트 센서스 · (m) 플래시 포락 ·
       (n) 플래시율과 밀림.

⭐맵의 표시 규약은 `src/md_mapstyle.py` 가 강제한다 — flash_spec(auto_periods) + draw + caption.
  주파수축은 보이는 범위(±2.1·f_tip)로 **자르고** 넘긴다(표시 범위 조정이지 규약 변경이 아니다).

읽는 것: outputs/report07b_bistatic_md.{json,npz}
쓰는 것: outputs/figures/report07b_g2.{png,pdf}

    cd sionna2 && PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/build_bistatic_md_fig.py
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
from matplotlib.lines import Line2D

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from md_mapstyle import auto_periods, caption, draw, flash_spec        # noqa: E402

J = json.load(open(f"{ROOT}/outputs/report07b_bistatic_md.json"))
Z = np.load(f"{ROOT}/outputs/report07b_bistatic_md.npz")
M = J["_meta"]
FIGDIR = f"{ROOT}/outputs/figures"
PRF, FFL, FTIP0, EL = M["prf_hz"], M["f_flash_hz"], M["f_tip_mono_hz"], M["el_deg"]
E = Z["E"]
LAB = list(Z["labels"])
ROWS = {r["label"]: r for r in J["rows"]}

FS = 9.5
plt.rcParams.update({
    "font.size": FS, "axes.labelsize": FS, "axes.titlesize": FS,
    "xtick.labelsize": FS - 1.5, "ytick.labelsize": FS - 1.5, "legend.fontsize": FS - 2,
    "axes.linewidth": 0.9, "figure.dpi": 200, "savefig.dpi": 200,
    "font.family": "DejaVu Sans", "mathtext.fontset": "dejavusans",
})
C_A, C_B, C_EL, C_CEN = "#111111", "#1565c0", "#e65100", "#2e7d32"
YLIM = 2.1 * FTIP0

BET = [b for b in M["betas_deg"]]
AZK = [f"az{b:.0f}" for b in BET]
ELK = ["az0"] + [f"el{b:.0f}" for b in BET[1:]]

fig = plt.figure(figsize=(16.6, 11.4))
gs = fig.add_gridspec(3, 1, height_ratios=[1.0, 1.0, 0.92], hspace=0.34)
g0 = gs[0].subgridspec(1, len(AZK), wspace=0.07)
g1 = gs[1].subgridspec(1, len(ELK), wspace=0.07)
g2 = gs[2].subgridspec(1, 5, wspace=0.42)

nper_seen, slots_seen = None, None


def map_row(sub, keys, tag):
    global nper_seen, slots_seen
    axs, mesh = [], None
    for c, k in enumerate(keys):
        ax = fig.add_subplot(sub[0, c], sharey=axs[0] if axs else None)
        j = LAB.index(k)
        r = ROWS[k]
        f, t, S, nper = flash_spec(E[:, j], PRF, FFL, auto_periods(PRF, FFL))
        m = np.abs(f) <= YLIM * 1.02                    # 표시 범위로 자른다(규약은 그대로)
        mesh = draw(ax, t, f[m], S[m], r["f_tip_pred_B_hz"])
        ax.axhline(+r["f_tip_pred_A_hz"], color="k", ls=":", lw=1.0, alpha=0.85)
        ax.axhline(-r["f_tip_pred_A_hz"], color="k", ls=":", lw=1.0, alpha=0.85)
        ax.set_ylim(-YLIM, YLIM)
        ax.set_xlabel("Time [ms]")
        ttl = (r"$\beta$ = 0 (monostatic)" if r["beta_deg"] == 0 else
               rf"$\beta$ = {r['beta_deg']:.0f}$^\circ$  ({tag})")
        ax.set_title(f"{ttl}\n{r['level_db_rel_mono']:+.1f} dB vs monostatic", fontsize=FS - 0.5)
        if c:
            ax.tick_params(labelleft=False)
        axs.append(ax)
        nper_seen, slots_seen = nper, S.shape[1]
    axs[0].set_ylabel("Doppler [Hz]")
    axs[0].legend(handles=[
        Line2D([], [], color="w", ls="--", lw=1.4),
        Line2D([], [], color="k", ls=":", lw=1.2)],
        labels=["prediction B (bisector, horizontal part)", r"prediction A ($\cos\beta/2$)"],
        loc="lower left", framealpha=0.45, facecolor="black", edgecolor="none",
        labelcolor="white", fontsize=FS - 3.2, handlelength=2.4)
    return axs, mesh


ax_az, mesh = map_row(g0, AZK, "azimuth plane")
ax_el, _ = map_row(g1, ELK, "elevation plane")
cb = fig.colorbar(mesh, ax=[*ax_az, *ax_el], pad=0.008, fraction=0.016)
cb.set_label("Magnitude, each panel to its own peak [dB]", fontsize=FS - 1)

# ─────────────────────────────────────────────────────────────────────────── #
#  (k) 도플러 축척 — 예측 둘 대 순수-PO 대조팔의 실측
# ─────────────────────────────────────────────────────────────────────────── #
bb = np.linspace(0, 155, 621)
ce, se = np.cos(np.radians(EL)), np.sin(np.radians(EL))
cph = (np.cos(np.radians(bb)) - se * se) / (ce * ce)
ok = np.abs(cph) <= 1
CURVE_A = np.cos(np.radians(bb) / 2)
CURVE_AZ = np.cos(np.arccos(np.clip(cph, -1, 1)) / 2)
CURVE_EL = (ce + np.cos(np.radians(EL + bb))) / (2 * ce)

ax = fig.add_subplot(g2[0, 0])
ax.plot(bb, CURVE_A, color=C_A, lw=2.0, label=r"A: $\cos(\beta/2)$")
ax.plot(bb[ok], CURVE_AZ[ok], color=C_B, lw=2.0, label="B: azimuth plane")
ax.plot(bb, CURVE_EL, color=C_EL, lw=2.0, label="B: elevation plane")
for keys, col, mk, lab in ((AZK, C_B, "o", "measured, azimuth"),
                           (ELK[1:], C_EL, "s", "measured, elevation")):
    x = [ROWS[k]["beta_deg"] for k in keys]
    y = np.array([ROWS[k]["po_ratio"] for k in keys])
    lo = np.array([min(ROWS[k]["po_ratio_lo"], ROWS[k]["po_ratio_hi"]) for k in keys])
    hi = np.array([max(ROWS[k]["po_ratio_lo"], ROWS[k]["po_ratio_hi"]) for k in keys])
    ax.errorbar(x, y, yerr=[np.maximum(y - lo, 0), np.maximum(hi - y, 0)], fmt=mk, color=col,
                ms=7, mec="white", mew=0.9, capsize=3, lw=1.2, zorder=5, label=lab)
ax.set_xlim(0, 155); ax.set_ylim(0, 1.15); ax.set_xticks([0, 30, 60, 90, 120, 150])
ax.set_xlabel(r"Bistatic angle $\beta$  [deg]")
ax.set_ylabel(r"$f_{tip}(\beta)\,/\,f_{tip}(0)$")
ax.set_title("(k) Doppler scale, PO control arm")
ax.legend(loc="lower left", frameon=False, fontsize=FS - 2.8)
ax.grid(alpha=0.25, lw=0.6)

# ─────────────────────────────────────────────────────────────────────────── #
#  (l) 같은 잣대를 SBR 팔에 대면 — 광대역 바닥이 축척을 덮는다
# ─────────────────────────────────────────────────────────────────────────── #
ax = fig.add_subplot(g2[0, 1])
ax.plot(bb[ok], CURVE_AZ[ok], color="#999999", lw=1.6, ls="--",
        label="prediction (azimuth)")
ax.plot(bb, CURVE_EL, color="#999999", lw=1.6, ls=":", label="prediction (elevation)")
for keys, col, mk, lab in ((AZK, C_B, "o", "SBR arm, azimuth"),
                           (ELK[1:], C_EL, "s", "SBR arm, elevation")):
    x = [ROWS[k]["beta_deg"] for k in keys]
    ax.plot(x, [ROWS[k]["sbr_ratio"] for k in keys], mk + "-", color=col, ms=7,
            mec="white", mew=0.9, lw=1.6, label=lab)
for keys, col, mk in ((AZK, C_B, "o"), (ELK[1:], C_EL, "s")):
    ax.plot([ROWS[k]["beta_deg"] for k in keys], [ROWS[k]["po_ratio"] for k in keys],
            mk, color=col, ms=5, mfc="none", alpha=0.45)
ax.axhline(1.0, color="#cccccc", lw=0.8)
ax.set_xlim(0, 130); ax.set_ylim(0, 3.1); ax.set_xticks([0, 30, 60, 90, 120])
ax.set_xlabel(r"Bistatic angle $\beta$  [deg]")
ax.set_ylabel("same estimator, SBR arm")
ax.set_title("(l) The kernel arm cannot see the scale")
ax.legend(loc="upper left", frameon=False, fontsize=FS - 2.8)
ax.grid(alpha=0.25, lw=0.6)

# ─────────────────────────────────────────────────────────────────────────── #
#  (m) 레벨 감쇠 + 게이트 센서스
# ─────────────────────────────────────────────────────────────────────────── #
ax = fig.add_subplot(g2[0, 2])
cen = J["census"]
for pl, col in (("azimuth", C_B), ("elevation", C_EL)):
    c = [x for x in cen if x["plane"] == pl]
    b = np.array([x["beta_deg"] for x in c])
    a = np.array([x["A_eff_rel_mono"] for x in c])
    inc, coh = 10 * np.log10(np.maximum(a, 1e-4)), 20 * np.log10(np.maximum(a, 1e-4))
    ax.fill_between(b, inc, coh, color=col, alpha=0.13, lw=0)
    ax.plot(b, inc, color=col, lw=0.9, ls=":")
    ax.plot(b, coh, color=col, lw=0.9, ls=":")
for keys, col, mk, lab in ((AZK, C_B, "o", "azimuth"), (ELK, C_EL, "s", "elevation")):
    ax.plot([ROWS[k]["beta_deg"] for k in keys],
            [ROWS[k]["level_db_rel_mono"] for k in keys], mk + "-", color=col, ms=7,
            mec="white", mew=0.9, lw=1.6, label=lab)
ax.set_xlim(0, 182); ax.set_xticks([0, 30, 60, 90, 120, 150, 180]); ax.set_ylim(-85, 12)
ax.set_xlabel(r"Bistatic angle $\beta$  [deg]")
ax.set_ylabel("Echo power vs monostatic [dB]")
ax.set_title("(m) Level, and the gate census behind it")
h, l_ = ax.get_legend_handles_labels()
h.append(Line2D([], [], color="#777777", lw=6, alpha=0.25)); l_.append(r"$A_{eff}$ band")
ax.legend(h, l_, loc="lower left", frameon=False, fontsize=FS - 2.8)
ax.grid(alpha=0.25, lw=0.6)

# ─────────────────────────────────────────────────────────────────────────── #
#  (n) 플래시 열차 — 주기는 그대로, 시각만 밀린다
# ─────────────────────────────────────────────────────────────────────────── #
ax = fig.add_subplot(g2[0, 3])
show = [("az0", "#555555"), (f"az{BET[2]:.0f}", C_B), (f"az{BET[-1]:.0f}", "#8e24aa"),
        (f"el{BET[-1]:.0f}", C_EL)]
for k, col in show:
    j = LAB.index(k); r = ROWS[k]
    f, t, S, _ = flash_spec(E[:, j], PRF, FFL, auto_periods(PRF, FFL))
    lo, hi = 0.35 * FTIP0 * r["pred_bisector_horiz"], 1.05 * FTIP0 * r["pred_bisector_horiz"]
    b = (S[(np.abs(f) > lo) & (np.abs(f) < hi)] ** 2).sum(axis=0)
    b = (b - b.min()) / (b.max() - b.min() + 1e-30)
    w = (t * 1e3 >= 20) & (t * 1e3 <= 20 + 3.0 / FFL * 1e3)
    lab = (r"$\beta$ = 0" if r["beta_deg"] == 0 else
           rf"$\beta$={r['beta_deg']:.0f}$^\circ$ {'az' if r['plane']=='azimuth' else 'el'}")
    ax.plot(t[w] * 1e3, b[w], color=col, lw=1.5, label=lab)
for n in range(4):
    ax.axvline(20 + n / FFL * 1e3, color="#bbbbbb", lw=0.8, ls="--", zorder=0)
ax.set_xlabel("Time [ms]"); ax.set_ylabel("Blade-band energy, normalized")
ax.set_title("(n) Flash train: same rate, shifted timing")
ax.legend(loc="upper right", frameon=False, fontsize=FS - 2.8, ncol=2)
ax.grid(alpha=0.2, lw=0.6)

# ─────────────────────────────────────────────────────────────────────────── #
#  (o) 플래시율은 시선이 아니라 로터가 정한다
# ─────────────────────────────────────────────────────────────────────────── #
ax = fig.add_subplot(g2[0, 4])
ax.axhline(1.0, color="#999999", lw=1.2, ls="--")
ax.axhline(2.0, color="#cccccc", lw=1.0, ls=":")
for keys, col, mk, lab in ((AZK, C_B, "o", "azimuth"), (ELK, C_EL, "s", "elevation")):
    x = [ROWS[k]["beta_deg"] for k in keys]
    ax.plot(x, [ROWS[k]["f_flash_meas_hz"] / FFL for k in keys], mk + "-", color=col,
            ms=7, mec="white", mew=0.9, lw=1.6, label=lab)
ax.set_ylim(0.55, 2.45); ax.set_xlim(-5, 130); ax.set_xticks([0, 30, 60, 90, 120])
ax.set_yticks([1.0, 1.5, 2.0])
ax.set_xlabel(r"Bistatic angle $\beta$  [deg]")
ax.set_ylabel(r"measured $f_{flash}$ / nominal")
ax.set_title("(o) Flash rate is set by the rotor")
ax.legend(loc="center left", frameon=False, fontsize=FS - 2.8)
ax.grid(alpha=0.25, lw=0.6)
axr = ax.twinx()                                   # 밀림은 흐리게 겹쳐 둔다(부차 축)
for keys, col, mk in ((AZK, C_B, "o"), (ELK, C_EL, "s")):
    x = np.array([ROWS[k]["beta_deg"] for k in keys])
    axr.plot(x, [ROWS[k]["flash_lag_frac_period"] for k in keys], mk, color=col, ms=6,
             alpha=0.5, mfc="none", ls="none")
    o = np.argsort(x)
    for sgn, key in ((+1, "flash_lag_pred_frac"), (-1, "flash_lag_pred_cw_frac")):
        y = np.array([ROWS[k][key] for k in keys], float)
        y = np.where(y > 0.5, y - 1.0, y)
        axr.plot(x[o], y[o], color=col, lw=0.9, alpha=0.28)
axr.set_ylim(-0.62, 0.62)
axr.set_ylabel("flash lag [periods]  (faded)", fontsize=FS - 2, color="#888888")
axr.tick_params(labelsize=FS - 2.5, colors="#888888")

V = J["verdict"]["doppler_scaling"]
SB = J["verdict"]["sbr_edge_unusable"]
cap = textwrap.fill(
    "Bistatic sweep of the report-7 micro-Doppler scene: the target, attitude, carrier, rotor "
    "speeds and slow-time grid are inherited unchanged from the monostatic ledger and only the "
    "receive direction is opened. Top row keeps both ground stations at the same depression "
    "angle and separates them in azimuth, which is the geometry a passive bistatic link "
    "actually has. Middle row lifts the receiver inside the vertical plane instead, which tilts "
    "the bisector out of the rotor plane much faster and is included as a control. Panels are "
    "each normalized to their own peak so the pattern stays readable; the level drop is the "
    "number in every title and the curve in (m). In (m) the shaded band is the projected area "
    "that survives both the illumination and the reception gate, drawn between its incoherent "
    "and fully coherent power laws. In (n) the vertical guides are spaced by one nominal flash "
    "period, and the faded right-hand axis of (o) carries the flash timing shift against its two "
    "predictions, one per rotor handedness. "
    "Panels (k) and (l) apply the same yardstick, the time-resolved maximum Doppler, to two "
    "arms: the pure physical-optics control, which has a clean blade cut-off, and the ray-traced "
    "kernel that produced the maps. "
    + f"Against the control the relative scatter is {V['po_rms_rel_err_vs_pred_B']:.3f} for "
    + f"prediction B and {V['po_rms_rel_err_vs_pred_A']:.3f} for prediction A. On the kernel arm "
    + "the same estimator runs away from both predictions, because that arm carries a broadband "
    + f"slow-time floor about {abs(SB['mono_ledger_engine_floors_db']['sbr']['floor_rel_db']):.0f} dB "
    + "below its peak that reaches past the blade tip.", 210)
# ⚠ 캡션은 **한 덩어리**로 붙인다 — 두 개를 따로 놓으면 bbox tight 가 겹쳐 찍는다.
cap = cap + "\n" + textwrap.fill(caption(PRF, FFL, nper_seen, slots_seen), 210)
fig.text(0.5, 0.052, cap, ha="center", va="top", fontsize=FS - 1.5, color="#333333")

os.makedirs(FIGDIR, exist_ok=True)
for ext in ("png", "pdf"):
    fig.savefig(f"{FIGDIR}/report07b_g2.{ext}", bbox_inches="tight", facecolor="white")
plt.close(fig)
print(f"  ✅ outputs/figures/report07b_g2.png "
      f"({os.path.getsize(f'{FIGDIR}/report07b_g2.png')/1e6:.2f} MB) · pdf "
      f"{os.path.getsize(f'{FIGDIR}/report07b_g2.pdf')/1e6:.2f} MB")
