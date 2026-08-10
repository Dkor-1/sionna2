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
g2 = gs[2].subgridspec(1, 4, wspace=0.30)

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
#  (k) 도플러 축척 — 예측 둘 대 실측 셋
# ─────────────────────────────────────────────────────────────────────────── #
ax = fig.add_subplot(g2[0, 0])
bb = np.linspace(0, 155, 621)
ce, se = np.cos(np.radians(EL)), np.sin(np.radians(EL))
cphi = np.clip((np.cos(np.radians(bb)) - se * se) / (ce * ce), -1, 1)
ok = np.abs((np.cos(np.radians(bb)) - se * se) / (ce * ce)) <= 1
ax.plot(bb, np.cos(np.radians(bb) / 2), color=C_A, lw=2.0, label=r"A: $\cos(\beta/2)$")
ax.plot(bb[ok], np.cos(np.arccos(cphi[ok]) / 2), color=C_B, lw=2.0, label="B: azimuth plane")
ax.plot(bb, (ce + np.cos(np.radians(EL + bb))) / (2 * ce), color=C_EL, lw=2.0,
        label="B: elevation plane")
for keys, col, mk, lab in ((AZK[1:], C_B, "o", "measured, azimuth"),
                           (ELK[1:], C_EL, "s", "measured, elevation")):
    x = [ROWS[k]["beta_deg"] for k in keys]
    est = np.array([[ROWS[k]["meas_ratio_shape"], ROWS[k]["meas_ratio_quantile"],
                     ROWS[k]["meas_ratio_knee"]] for k in keys])
    y, lo, hi = est.mean(1), est.min(1), est.max(1)
    ax.errorbar(x, y, yerr=[y - lo, hi - y], fmt=mk, color=col, ms=7, mec="white",
                mew=0.9, capsize=3, lw=1.2, zorder=5, label=lab)
ax.plot(0, 1.0, "o", color="#555555", ms=7, mec="white", mew=0.9, zorder=5)
ax.set_xlim(0, 155); ax.set_ylim(0, 1.12)
ax.set_xticks([0, 30, 60, 90, 120, 150])
ax.set_xlabel(r"Bistatic angle $\beta$  [deg]")
ax.set_ylabel(r"$f_{tip}(\beta)\,/\,f_{tip}(0)$")
ax.set_title("(k) Doppler scale: prediction vs measurement")
ax.legend(loc="lower left", frameon=False, fontsize=FS - 2.6)
ax.grid(alpha=0.25, lw=0.6)

# ─────────────────────────────────────────────────────────────────────────── #
#  (l) 레벨 감쇠 + 게이트 센서스
# ─────────────────────────────────────────────────────────────────────────── #
ax = fig.add_subplot(g2[0, 1])
cen = J["census"]
for pl, col, ls in (("azimuth", C_B, "-"), ("elevation", C_EL, "-")):
    c = [x for x in cen if x["plane"] == pl]
    b = np.array([x["beta_deg"] for x in c])
    a = np.array([x["A_eff_rel_mono"] for x in c])
    inc, coh = 10 * np.log10(np.maximum(a, 1e-6)), 20 * np.log10(np.maximum(a, 1e-6))
    ax.fill_between(b, inc, coh, color=col, alpha=0.13, lw=0)
    ax.plot(b, inc, color=col, lw=1.0, ls=":")
    ax.plot(b, coh, color=col, lw=1.0, ls=":")
for keys, col, mk, lab in ((AZK, C_B, "o", "azimuth"), (ELK, C_EL, "s", "elevation")):
    x = [ROWS[k]["beta_deg"] for k in keys]
    y = [ROWS[k]["level_db_rel_mono"] for k in keys]
    ax.plot(x, y, mk + "-", color=col, ms=7, mec="white", mew=0.9, lw=1.6, label=lab)
ax.set_xlim(0, 182); ax.set_xticks([0, 30, 60, 90, 120, 150, 180])
ax.set_xlabel(r"Bistatic angle $\beta$  [deg]")
ax.set_ylabel("Echo power vs monostatic [dB]")
ax.set_title("(l) Level: measured echo and the gate census")
h, l_ = ax.get_legend_handles_labels()
h.append(Line2D([], [], color="#777777", lw=6, alpha=0.25))
l_.append(r"gate census $A_{eff}$ band")
ax.legend(h, l_, loc="lower left", frameon=False, fontsize=FS - 2.6)
ax.grid(alpha=0.25, lw=0.6)

# ─────────────────────────────────────────────────────────────────────────── #
#  (m) 플래시 포락 — 주기는 그대로, 시각만 밀린다
# ─────────────────────────────────────────────────────────────────────────── #
ax = fig.add_subplot(g2[0, 2])
show = [("az0", "#555555"), (f"az{BET[2]:.0f}", C_B), (f"az{BET[-1]:.0f}", "#8e24aa"),
        (f"el{BET[-1]:.0f}", C_EL)]
for k, col in show:
    j = LAB.index(k)
    r = ROWS[k]
    f, t, S, _ = flash_spec(E[:, j], PRF, FFL, auto_periods(PRF, FFL))
    lo, hi = 0.35 * FTIP0 * r["pred_bisector_horiz"], 1.05 * FTIP0 * r["pred_bisector_horiz"]
    b = (S[(np.abs(f) > lo) & (np.abs(f) < hi)] ** 2).sum(axis=0)
    b = (b - b.min()) / (b.max() - b.min() + 1e-30)
    w = (t * 1e3 >= 20) & (t * 1e3 <= 20 + 3.0 / FFL * 1e3)
    lab = (r"$\beta$ = 0" if r["beta_deg"] == 0 else
           rf"$\beta$ = {r['beta_deg']:.0f}$^\circ$ {'az' if r['plane']=='azimuth' else 'el'}")
    ax.plot(t[w] * 1e3, b[w], color=col, lw=1.5, label=lab)
for n in range(4):
    ax.axvline(20 + n / FFL * 1e3, color="#bbbbbb", lw=0.8, ls="--", zorder=0)
ax.set_xlabel("Time [ms]")
ax.set_ylabel("Blade-band energy, normalized")
ax.set_title("(m) Flash train: same rate, shifted timing")
ax.legend(loc="upper right", frameon=False, fontsize=FS - 2.6, ncol=2)
ax.grid(alpha=0.2, lw=0.6)

# ─────────────────────────────────────────────────────────────────────────── #
#  (n) 플래시율은 β 에 안 변한다 + 밀림
# ─────────────────────────────────────────────────────────────────────────── #
ax = fig.add_subplot(g2[0, 3])
ax.axhline(1.0, color="#999999", lw=1.2, ls="--")
for keys, col, mk, lab in ((AZK, C_B, "o", "azimuth"), (ELK, C_EL, "s", "elevation")):
    x = [ROWS[k]["beta_deg"] for k in keys]
    y = [ROWS[k]["f_flash_meas_hz"] / FFL for k in keys]
    ax.plot(x, y, mk + "-", color=col, ms=7, mec="white", mew=0.9, lw=1.6, label=lab)
ax.set_ylim(0.80, 1.20)
ax.set_xlim(-5, 130); ax.set_xticks([0, 30, 60, 90, 120])
ax.set_xlabel(r"Bistatic angle $\beta$  [deg]")
ax.set_ylabel(r"measured $f_{flash}$ / nominal")
ax.set_title("(n) Flash rate is a rotor property, not a look property")
ax.legend(loc="lower left", frameon=False, fontsize=FS - 2.6)
ax.grid(alpha=0.25, lw=0.6)
axr = ax.twinx()
for keys, col, mk in ((AZK, C_B, "o"), (ELK, C_EL, "s")):
    x = [ROWS[k]["beta_deg"] for k in keys]
    axr.plot(x, [ROWS[k]["flash_lag_frac_period"] for k in keys], mk, color=col, ms=5,
             alpha=0.45, mfc="none")
    axr.plot(x, [ROWS[k]["flash_lag_pred_frac"] for k in keys], "-", color=col, lw=1.0,
             alpha=0.35)
    axr.plot(x, [ROWS[k]["flash_lag_pred_cw_frac"] - 1.0 for k in keys], "-", color=col,
             lw=1.0, alpha=0.35)
axr.set_ylim(-0.62, 0.62)
axr.set_ylabel("flash lag [flash periods]  (faded)", fontsize=FS - 1.5, color="#777777")
axr.tick_params(labelsize=FS - 2.5, colors="#777777")

V = J["verdict"]["doppler_scaling"]
cap = textwrap.fill(
    "Bistatic sweep of the report-7 micro-Doppler scene: the target, attitude, carrier, rotor "
    "speeds and slow-time grid are inherited unchanged from the monostatic ledger and only the "
    "receive direction is opened. Top row keeps both ground stations at the same depression "
    "angle and separates them in azimuth, which is the geometry a passive bistatic link "
    "actually has. Middle row lifts the receiver inside the vertical plane instead, which tilts "
    "the bisector out of the rotor plane much faster and is included as a control. Panels are "
    "each normalized to their own peak so the pattern stays readable; the level drop is the "
    "number in every title and the curve in (l). In (l) the shaded band is the projected area "
    "that survives both the illumination and the reception gate, drawn between its incoherent "
    "and fully coherent power laws. In (m) the vertical guides are spaced by one nominal flash "
    "period. "
    + f"Measured Doppler scale departs from prediction A by up to {V['max_err_vs_pred_A']:.3f} "
    + f"and from prediction B by up to {V['max_err_vs_pred_B']:.3f}.", 210)
fig.text(0.5, 0.055, cap, ha="center", va="top", fontsize=FS - 1.5, color="#333333")
fig.text(0.5, 0.008, textwrap.fill(caption(PRF, FFL, nper_seen, slots_seen), 210),
         ha="center", va="top", fontsize=FS - 1.5, color="#333333")

os.makedirs(FIGDIR, exist_ok=True)
for ext in ("png", "pdf"):
    fig.savefig(f"{FIGDIR}/report07b_g2.{ext}", bbox_inches="tight", facecolor="white")
plt.close(fig)
print(f"  ✅ outputs/figures/report07b_g2.png "
      f"({os.path.getsize(f'{FIGDIR}/report07b_g2.png')/1e6:.2f} MB) · pdf "
      f"{os.path.getsize(f'{FIGDIR}/report07b_g2.pdf')/1e6:.2f} MB")
