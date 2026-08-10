# -*- coding: utf-8 -*-
"""
build_hover_fig.py — 호버링 마이크로도플러 맵을 **문헌 규약**으로 그린다.

사용자가 보여준 문헌 그림의 규약을 그대로 따른다:
  · 도플러축 **±2000 Hz** · 시간축 **초**
  · 색역 **0 ~ −40 dB** · 색 **jet**
  · 0 도플러 동체 선을 살린다(지우지 않는다)
  · 능선(HERM lines)이 가늘고 선명하게 — 조각을 길게 잡아 주파수 분해능을 산다

⭐ 우리 것이 문헌과 달랐던 진짜 이유는 색이 아니라 **rpm 을 고정값으로 둔 것**이었다.
   문헌 그림의 능선이 물결치는 것은 호버링 드론의 비행제어기가 rpm 을 계속 흔들기 때문이다.
   `report07_hover_long.py` 가 그 흔들림을 넣어 다시 계산한다.

읽는 것: outputs/report07_hover_long.{npz,json}
쓰는 것: outputs/figures/report07_f7.{png,pdf}
"""
from __future__ import annotations

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import spectrogram as _spec

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
J = json.load(open(f"{ROOT}/outputs/report07_hover_long.json"))["_meta"]
Z = np.load(f"{ROOT}/outputs/report07_hover_long.npz")
E, RPM = np.asarray(Z["E"], complex), np.asarray(Z["rpm_t"], float)
PRF, FFL, FTIP = J["prf_hz"], J["f_flash_hz"], J["f_tip_hz"]

FS = 9.5
plt.rcParams.update({
    "font.size": FS, "axes.labelsize": FS, "axes.titlesize": FS,
    "xtick.labelsize": FS - 1, "ytick.labelsize": FS - 1, "legend.fontsize": FS - 1.5,
    "axes.linewidth": 0.9, "figure.dpi": 200, "savefig.dpi": 200,
    "font.family": "DejaVu Sans",
})

# ⭐ 두 가지를 문헌에 맞춘다.
#   ① 조각 길이 — 능선이 가늘고 선명하려면 길어야 한다. 블레이드 12 주기.
#   ② ⭐⭐**겹침** — 이것이 «빈이 너무 크다» 의 원인이었다.
#      hop 을 조각의 1/8(64 표본)로 두면 시간 슬롯이 149 개뿐이라 계단처럼 보인다.
#      hop 을 8 표본(1.6 ms)으로 줄이면 슬롯이 1,187 개가 되어 문헌처럼 매끈해진다.
#      ⚠ 겹침은 정보를 늘리지 않는다 — 같은 정보를 **촘촘히 다시 읽을** 뿐이다.
#        시간 분해능은 여전히 조각 길이가 정한다. 보기 좋아지는 것이지 좋아지는 것이 아니다.
import sys as _sys
_sys.path.insert(0, os.path.join(ROOT, "src"))
from md_mapstyle import flash_spec, auto_periods, VMIN, VMAX, CMAP, SHADING   # noqa: E402
f, t, S, NPER = flash_spec(E, PRF, FFL, auto_periods(PRF, FFL))
D = 20 * np.log10(S / S.max() + 1e-12)

fig = plt.figure(figsize=(9.2, 4.6))
gs = fig.add_gridspec(2, 1, height_ratios=[3.1, 1.0], hspace=0.30,
                      left=0.088, right=0.985, bottom=0.115, top=0.865)

ax = fig.add_subplot(gs[0])
m = ax.pcolormesh(t, f, D, cmap=CMAP, vmin=VMIN, vmax=VMAX, shading=SHADING,
                  rasterized=True)       # ⚠PDF 폭증 방지
for s in (+1, -1):
    ax.axhline(s * FTIP, color="w", ls="--", lw=1.0, alpha=0.85)
ax.set_ylim(-2000, 2000)
ax.set_ylabel("Doppler [Hz]")
ax.set_title(f"{J['name']} hovering — {J['seconds']:.0f} s, {J['fc_hz']/1e9:.1f} GHz, "
             f"belly view (az {J['az_deg']:.0f}, el {J['el_deg']:.0f})", fontsize=FS)
cb = fig.colorbar(m, ax=ax, pad=0.012)
cb.set_label("Magnitude [dB]", fontsize=FS)

ax2 = fig.add_subplot(gs[1])
tt = np.arange(len(RPM)) / PRF
for k in range(RPM.shape[1]):
    ax2.plot(tt, RPM[:, k], lw=1.0, label=f"rotor {k+1}")
ax2.set_xlim(t[0], t[-1])
ax2.set_ylabel("Rotor speed [rpm]")
ax2.grid(alpha=0.25, lw=0.5)
ax2.legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.42),
           framealpha=0.0, columnspacing=1.6)
ax2.set_xlabel("Time [s]")
ax2.set_title("Rotor speeds — spread taken from measured PX4 telemetry (0.07-0.29 %)",
              fontsize=FS - 0.5)

# 설정 수치는 그림에 안 적는다 — 리포트의 «표시 규약» 절이 담는다.

for ext in ("png", "pdf"):
    fig.savefig(f"{ROOT}/outputs/figures/report07_f7.{ext}",
                bbox_inches="tight", facecolor="white")
plt.close(fig)
print(f"  ✅ outputs/figures/report07_f7.png")
print(f"     조각 {NPER} 표본 = {NPER/(PRF/FFL):.1f} 블레이드 주기 · "
      f"분해능 {PRF/NPER:.1f} Hz · 시간 슬롯 {len(t)}개")
