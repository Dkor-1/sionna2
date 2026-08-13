# -*- coding: utf-8 -*-
"""
build_el15_stft_check.py — 15 m 재설계판의 **STFT 맵을 눈으로 검사**한다.

왜
--
사용자: *"현재까지의 STFT 결과물은 어떠하니?"* — 스칼라 지표(박자·h1/h2)만으로는
오판한다. 실제로 −30°·−45° 에서 박자 추정기가 **2·f_flash 에 물렸고**(오차가 정확히
+126.67 = f_flash), 그 자리에서 h1/h2 가 **음수**다. 즉 «틀린 값» 이 아니라
«2 차 고조파가 기본파보다 크다» 는 물리를 추정기가 따라간 것일 수 있다.
그 판정은 맵을 봐야 선다 — 빗살이 보이는지, 몇 줄로 보이는지.

무엇을 그리나
    행 = max_depth 1 · 2      열 = 완결된 앙각
    각 패널에 f_flash 와 2·f_flash 를 가로선으로 얹어, 어느 쪽에 에너지가 있는지 본다.

⭐그림 글자는 전부 영어(집 규약).

    PYTHONPATH=src:benchmark python benchmark/build_el15_stft_check.py
"""
from __future__ import annotations

import glob
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                        # noqa: E402
import numpy as np                                                     # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from md_mapstyle import auto_periods, flash_spec, draw                 # noqa: E402

FIGDIR = os.path.join(ROOT, "outputs", "figures")
SHD = os.path.join(ROOT, "outputs", "elev_sweep_shards")
TJ = json.load(open(os.path.join(ROOT, "outputs",
                                 "report07_three_engines.json")))["_meta"]
PRF, FFL = float(TJ["prf_hz"]), float(TJ["f_flash_hz"])
FTIP0 = float(TJ["f_tip_hz"]) / np.cos(np.radians(-15.0))
ELS = (0.0, -15.0, -30.0, -45.0, -60.0, -75.0, -90.0)


def load(el, d):
    fs = sorted(glob.glob(f"{SHD}/sionna_p4000000000_phys_r15_n8192_d{d}"
                          f"_el{el:+.0f}_*.npz"))
    if len(fs) < 16:
        return None
    E = np.zeros(8192, complex)
    for f in fs:
        z = np.load(f)
        E[z["idx"].astype(int)] = z["E"]
    return E


def main():
    have = [el for el in ELS if load(el, 1) is not None and load(el, 2) is not None]
    if not have:
        print("  완결된 앙각이 없다"); return
    nc = len(have)
    fig, axes = plt.subplots(2, nc, figsize=(3.05 * nc, 6.6), dpi=165,
                             squeeze=False)
    per = auto_periods(PRF, FFL)
    for r, d in enumerate((1, 2)):
        for c, el in enumerate(have):
            ax = axes[r][c]
            E = load(el, d)
            f, t, S, nper = flash_spec(E, PRF, FFL, per)
            ftip = FTIP0 * np.cos(np.radians(el))
            draw(ax, t, f, S, ftip, mode="peak")
            for y, col, ls in ((FFL, "#00d0ff", "-"), (2 * FFL, "#ff5ac8", "--")):
                ax.axhline(y, color=col, lw=0.9, ls=ls, alpha=0.85)
                ax.axhline(-y, color=col, lw=0.9, ls=ls, alpha=0.85)
            if r == 0:
                ax.set_title(f"el {'0°' if el == 0 else f'−{abs(el):.0f}°'}"
                             f"\n$f_{{tip}}$ = {ftip:.0f} Hz", fontsize=10)
            if c == 0:
                ax.set_ylabel(f"max_depth {d}\nDoppler [Hz]", fontsize=9.6)
            else:
                ax.set_ylabel("")
            if r == 1:
                ax.set_xlabel("slow time [ms]", fontsize=9)
            ax.tick_params(labelsize=7.6)

    fig.suptitle("15 m elevation sweep — flash spectrograms  "
                 "(cyan = $f_{flash}$ 126.67 Hz,  magenta = 2$f_{flash}$ 253.34 Hz)",
                 fontsize=12.4, y=0.985)
    fig.text(0.995, 0.985,
             f"Sionna PathSolver · 4,000M rays · all physics on · "
             f"8,192 poses · STFT {per:.2f} flash-periods ({nper} samples)",
             fontsize=7.8, color="#5a6570", ha="right", va="top")
    fig.tight_layout(rect=(0, 0, 1, 0.955))
    out = os.path.join(FIGDIR, "el15_stft_check.png")
    fig.savefig(out, facecolor="white")
    print(f"  ✅ {os.path.relpath(out, ROOT)}   앙각 {len(have)} 점 × depth 2")


if __name__ == "__main__":
    main()
