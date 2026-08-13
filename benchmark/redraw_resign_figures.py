# -*- coding: utf-8 -*-
"""정정된 npz 로 그림만 다시 그린다. **원장(json/npz)은 한 개도 안 쓴다.**

· 덱 거리 그림 3 종  — build_deck0811_range_figs 의 그리기 함수만 호출(모듈의 __main__ 은 안 탄다)
· 40 m 나란히판     — build_raybudget_40m_fig 의 merge/_map 만 빌려 옆판만 다시 그린다
GPU 안 씀 (npz 만 읽는다).
"""
from __future__ import annotations
import os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = "/workspace/sionna"
sys.path.insert(0, f"{ROOT}/src")
sys.path.insert(0, f"{ROOT}/benchmark")

# ── ① 덱 거리 그림 ──────────────────────────────────────────────────────────
import build_deck0811_range_figs as D                                   # noqa: E402
D.build_maps()
band = D.build_band()
seed = D.build_seed40()
print("  band peaks:", band)
print("  seed40 peaks:", seed)

# ── ② 40 m 나란히판 (세 번째 칸만 우리 커널) ────────────────────────────────
import build_raybudget_40m_fig as R                                     # noqa: E402
SH, S178 = f"{ROOT}/outputs/range40_shards", f"{ROOT}/outputs/range40_178M"
d1 = R.merge([SH], 1, 4.0e9)
d2 = R.merge([SH], 2, 4.0e9)
OZ = np.load(f"{ROOT}/outputs/deck_ours_by_range.npz")
E_ours = OZ["R40/E"]
C_OURS, C_HI, FS = "#1f5fa8", R.C_HI, R.FS
figs = plt.figure(figsize=(22.0, 8.2))
gss = figs.add_gridspec(1, 4, width_ratios=[1, 1, 1, 0.028],
                        wspace=0.09, left=0.055, right=0.965, top=0.865, bottom=0.115)
ms = None
panels = [(d1["E"], "Sionna Path Solver\n4,000 M rays  ·  seed 1", C_HI),
          (d2["E"], "Sionna Path Solver\n4,000 M rays  ·  seed 2", C_HI),
          (E_ours,  "Ours (SBR + PO)\nno randomness",              C_OURS)]
for c, (E, ttl, col) in enumerate(panels):
    ax = figs.add_subplot(gss[0, c])
    ms = R._map(ax, E)
    ax.set_title(ttl, color=col, fontweight="bold", fontsize=FS + 4, pad=10)
    ax.set_xlabel("Time [ms]", fontsize=FS + 2)
    if c == 0:
        ax.set_ylabel("Doppler [Hz]", fontsize=FS + 2)
    else:
        plt.setp(ax.get_yticklabels(), visible=False)
    for sp in ax.spines.values():
        sp.set_color(col); sp.set_linewidth(2.4)
caxs = figs.add_subplot(gss[0, 3])
cbs = figs.colorbar(ms, cax=caxs); cbs.set_label("Normalised power [dB]", fontsize=FS + 1)
OUT_SIDE = f"{ROOT}/outputs/figures/raybudget_40m_vs_ours.png"
figs.savefig(OUT_SIDE, bbox_inches="tight")
plt.close(figs)
print(f"✅ {OUT_SIDE}")
