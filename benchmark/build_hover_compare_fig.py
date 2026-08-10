# -*- coding: utf-8 -*-
"""
build_hover_compare_fig.py — ⭐산포 **프리셋 비교** 2패널: 실내-이상(sitl) vs 야외(웹앵커).

왜 이 그림인가 (2026-08-10)
---------------------------
로터 산포 ±0.22 % 는 선배 PX4 SITL 실측이지만, SITL 은 **대칭-이상 조건의 하한**이다.
웹 실측 앵커(outputs/rotor_rpm_web_anchor.json)의 야외 실기체는 산포 ~2 %·흔들림 2.5 % 다.
실증이 야외이므로([[실측=외부]]) 두 프리셋을 나란히 보여 정직하게 답한다:
  «야외 산포에서는 능선 빗살이 어긋나 뭉개진다 — 그래서 **플래시(시간축 사건)** 로 읽어야 한다.»
이것이 시간분해능-우선 표시 규약(md_mapstyle)의 물리적 근거이기도 하다.

읽는 것: outputs/report07_hover_long.{npz,json} (sitl) · outputs/report07_hover_long_outdoor.{npz,json}
쓰는 것: outputs/figures/report07_f11.{png,pdf}
"""
from __future__ import annotations

import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from md_mapstyle import flash_spec, auto_periods, VMIN, VMAX, CMAP, SHADING   # noqa: E402

ARMS = [
    ("", "Indoor-ideal preset (PX4 SITL, measured)"),
    ("_outdoor", "Outdoor preset (web-anchored hover logs)"),
]

FS = 9.5
plt.rcParams.update({
    "font.size": FS, "axes.labelsize": FS, "axes.titlesize": FS,
    "xtick.labelsize": FS - 1, "ytick.labelsize": FS - 1, "legend.fontsize": FS - 1.5,
    "axes.linewidth": 0.9, "figure.dpi": 200, "savefig.dpi": 200,
    "font.family": "DejaVu Sans",
})

fig = plt.figure(figsize=(9.6, 5.2))
gs = fig.add_gridspec(2, 2, height_ratios=[3.0, 1.0], hspace=0.34, wspace=0.14,
                      left=0.075, right=0.90, bottom=0.11, top=0.90)
cax = fig.add_axes([0.915, 0.42, 0.016, 0.48])

meta = {}
for col, (tag, title) in enumerate(ARMS):
    J = json.load(open(f"{ROOT}/outputs/report07_hover_long{tag}.json"))["_meta"]
    Z = np.load(f"{ROOT}/outputs/report07_hover_long{tag}.npz")
    E, RPM = np.asarray(Z["E"], complex), np.asarray(Z["rpm_t"], float)
    PRF, FFL, FTIP = J["prf_hz"], J["f_flash_hz"], J["f_tip_hz"]
    meta[tag] = J

    f, t, S, NPER = flash_spec(E, PRF, FFL, auto_periods(PRF, FFL))
    D = 20 * np.log10(S / S.max() + 1e-12)

    ax = fig.add_subplot(gs[0, col])
    m = ax.pcolormesh(t, f, D, cmap=CMAP, vmin=VMIN, vmax=VMAX, shading=SHADING)
    for s in (+1, -1):
        ax.axhline(s * FTIP, color="w", ls="--", lw=1.0, alpha=0.85)
    ax.set_ylim(-2000, 2000)
    ax.set_title(title, fontsize=FS)
    if col == 0:
        ax.set_ylabel("Doppler [Hz]")
    else:
        ax.set_yticklabels([])

    ax2 = fig.add_subplot(gs[1, col])
    tt = np.arange(len(RPM)) / PRF
    for k in range(RPM.shape[1]):
        ax2.plot(tt, RPM[:, k], lw=0.9, label=f"rotor {k+1}")
    ax2.set_xlim(t[0], t[-1])
    ax2.set_xlabel("Time [s]")
    ax2.grid(alpha=0.25, lw=0.5)
    if col == 0:
        ax2.set_ylabel("Rotor speed [rpm]")
        ax2.legend(ncol=4, loc="upper center", bbox_to_anchor=(1.05, -0.46),
                   framealpha=0.0, columnspacing=1.6)

cb = fig.colorbar(m, cax=cax)
cb.set_label("Magnitude [dB]", fontsize=FS)
J0 = meta[""]
fig.suptitle(f"{J0['name']} hovering — {J0['seconds']:.0f} s, {J0['fc_hz']/1e9:.1f} GHz, "
             f"belly view (az {J0['az_deg']:.0f}, el {J0['el_deg']:.0f}) — "
             "same target, two rotor-spread presets", fontsize=FS + 0.5, y=0.975)

for ext in ("png", "pdf"):
    fig.savefig(f"{ROOT}/outputs/figures/report07_f11.{ext}",
                bbox_inches="tight", facecolor="white")
plt.close(fig)
print("  ✅ outputs/figures/report07_f11.png")
for tag, ttl in ARMS:
    J = meta[tag]
    print(f"     {ttl}: spread ±{J['static_spread']*100:.2f}% · "
          f"wobble ±{J['wobble_amp']*100:.2f}% @ {J['wobble_hz']:.1f} Hz")
