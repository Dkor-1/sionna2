# -*- coding: utf-8 -*-
"""
build_flash_zoom.py — ⭐**블레이드 플래시가 보이는** 마이크로도플러 맵 · 세 엔진 비교.

사용자가 보여준 문헌 그림 (b) 의 **아치 무늬**가 블레이드 플래시다. 그것을 보려면 둘이 필요하다.

  ① **조각을 한 블레이드 주기보다 짧게** — 플래시는 한 주기 안의 사건이라, 조각이 길면
     그 안에서 시간평균되어 가로 능선만 남는다.
  ② **시간축을 확대** — 2 초를 다 그리면 플래시가 한 화면에 눌려 붙는다.

⭐ 2026-08-10 사용자 지시 둘로 이 그림을 다시 짰다.
   ① *"주파수 해상도가 높은 경우(시간해상도가 너무 낮은 경우)는 애초에 필요가 없어"*
      → 옛 오른쪽 «능선판»(6.5 주기 조각) 패널을 **뺐다**. 이제 전부 플래시 해상도다.
   ② *"저 그림도 SBR+PO 랑 path solver 를 비교해줘"*
      → 같은 짧은 창을 **세 엔진**(Sionna PathSolver · 우리 SBR+PO · 가림 끈 대조군)으로 나란히.
      데이터는 그림 3 과 같은 원장(report07_three_engines)이라 슬로타임 격자·회전수가 동일하다.

읽는 것: outputs/report07_three_engines.{npz,json}
쓰는 것: outputs/figures/report07_f8.{png,pdf}
"""
import json
import os
import sys
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from md_mapstyle import flash_spec, draw, caption                      # noqa: E402

J = json.load(open(f"{ROOT}/outputs/report07_three_engines.json"))["_meta"]
Z = np.load(f"{ROOT}/outputs/report07_three_engines.npz")
PRF, FFL, FTIP = J["prf_hz"], J["f_flash_hz"], J["f_tip_hz"]
PER = PRF / FFL                                   # 블레이드 한 주기 = 표본 수

FS = 9.5
plt.rcParams.update({"font.size": FS, "axes.labelsize": FS, "axes.titlesize": FS,
                     "xtick.labelsize": FS - 1, "ytick.labelsize": FS - 1,
                     "figure.dpi": 200, "savefig.dpi": 200, "font.family": "DejaVu Sans"})

ZOOM_MS = 60.0
N0 = int(round(0.02 * PRF))                       # 시작 과도를 조금 피한다(창이 205 ms 뿐)
NZ = int(round(ZOOM_MS / 1000 * PRF))

ARMS = [("sionna", "Sionna PathSolver"),
        ("sbr", "Ours (SBR+PO, default)"),
        ("po", "Ours w/o occlusion (control)")]

fig = plt.figure(figsize=(11.4, 3.9))
gs = fig.add_gridspec(1, 4, width_ratios=[1, 1, 1, 0.05], wspace=0.14,
                      left=0.062, right=0.93, top=0.80, bottom=0.155)

CAP, m = "", None
for i, (key, title) in enumerate(ARMS):
    seg = np.asarray(Z[key], complex)[N0:N0 + NZ]
    ax = fig.add_subplot(gs[0, i])
    f, t, S, nper = flash_spec(seg, PRF, FFL)
    m = draw(ax, t + N0 / PRF, f, S, FTIP)
    if i == 0:
        CAP = caption(PRF, FFL, nper, len(t))
    ax.set_title(title)
    ax.set_xlabel("Time [ms]")
    if i == 0:
        ax.set_ylabel("Doppler [Hz]")
    else:
        plt.setp(ax.get_yticklabels(), visible=False)

cax = fig.add_subplot(gs[0, 3])
fig.colorbar(m, cax=cax).set_label("Magnitude, each map to its own peak [dB]",
                                   fontsize=FS - 0.5)
fig.suptitle(f"{J['name']} hovering, {J['fc_hz']/1e9:.1f} GHz, belly view — the same "
             f"{ZOOM_MS:.0f} ms window through three engines. "
             f"Blade flashes repeat every {1000/FFL:.1f} ms.",
             fontsize=FS + 0.5, y=0.965)

cap = (CAP + "\n"
       "All three panels share the slow-time grid, the rotor speeds and the display "
       "convention, so only the scattering engine differs. Time resolution is "
       "deliberately favoured over frequency resolution: segments shorter than one "
       "blade period are what make the flash arches visible at all. "
       "Maps are normalized to their own peak, so this figure compares structure, "
       "not level.")
cap = "\n".join(textwrap.fill(p, 145) for p in cap.split("\n"))
fig.text(0.062, -0.02, cap, fontsize=FS - 1.5, color="0.3", va="top")

for e in ("png", "pdf"):
    fig.savefig(f"{ROOT}/outputs/figures/report07_f8.{e}",
                bbox_inches="tight", facecolor="white")
print(f"  ✅ report07_f8.png · 블레이드 주기 {PER:.1f} 표본 = {1000/FFL:.1f} ms · "
      f"창 {ZOOM_MS:.0f} ms · 세 엔진")
