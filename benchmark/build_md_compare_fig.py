# -*- coding: utf-8 -*-
"""
build_md_compare_fig.py — ⭐**두 팔(또는 여러 팔)의 마이크로도플러 맵을 나란히** 굽는다.

왜
--
사용자 지시(2026-08-13): *"모든 경우를 다 비교하기보다 비교 포인트 두기 좋은 부분을
2~5 개 셀렉해서 비교하자"* · *"맵 결과물을 띄워놓고 교수님·박사님들과 의논하는 방향"*.

그래서 이 스크립트는 **비교 한 건 = 그림 한 장**을 낸다. 팔을 인자로 받으므로
어떤 조합이든 같은 도구로 뽑는다(덱 규약: 그림이 주인공, 텍스트는 라벨만).

    행 = 팔          열 = 앙각
    각 패널에 f_flash(126.67 Hz)·2f_flash 를 가로선으로 얹어 어디에 에너지가 있는지 본다.

⭐집 규약 — 그림 안 글자는 전부 영어. 맵마다 자기 최대값으로 정규화하므로
  **패널 사이 절대 레벨 비교는 이 그림 밖이다**(캡션에 명시된다).

사용법
    PYTHONPATH=src:benchmark python benchmark/build_md_compare_fig.py \\
        --out el15_physics_onoff \\
        --arms "sionna_p4000000000_r15_n8192_d1=Physics off" \\
               "sionna_p4000000000_phys_r15_n8192_d1=Physics on" \\
        --els 0,-30,-60,-90 \\
        --title "PathSolver at 15 m, 4,000M rays, max_depth 1"
"""
from __future__ import annotations

import argparse
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


def load(arm: str, el: float):
    """팔 하나 · 앙각 하나의 복소 시계열. 샤드가 모자라면 None."""
    fs = sorted(glob.glob(f"{SHD}/{arm}_el{el:+.0f}_*.npz"))
    if not fs:
        return None, 0
    n = int(np.asarray(np.load(fs[0])["meta"], float)[3])
    E = np.zeros(n, complex)
    for f in fs:
        z = np.load(f)
        E[z["idx"].astype(int)] = z["E"]
    miss = int((E == 0).sum())
    return (None, miss) if miss > n * 0.05 else (E, miss)


def acdc(E, ftip, per):
    f, t, S, _ = flash_spec(np.asarray(E, complex), PRF, FFL, per)
    b = (np.abs(f) >= 0.35 * ftip) & (np.abs(f) <= max(ftip, 1e-6))
    if b.sum() < 2:
        return None
    g = (S[b, :] ** 2).sum(axis=0)
    return 10 * np.log10(g.std() ** 2 / g.mean() ** 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="출력 파일 이름(확장자 없이)")
    ap.add_argument("--arms", nargs="+", required=True,
                    help="'샤드접두사=표시이름' 형식. 행 순서대로.")
    ap.add_argument("--els", default="0,-30,-60,-90", help="쉼표 구분 앙각")
    ap.add_argument("--title", default="", help="그림 제목(영어)")
    ap.add_argument("--note", default="", help="캡션 한 줄(영어)")
    a = ap.parse_args()

    arms = []
    for s in a.arms:
        k, _, lab = s.partition("=")
        arms.append((k, lab or k))
    els = [float(x) for x in a.els.split(",") if x.strip()]
    per = auto_periods(PRF, FFL)

    # ⭐덱 규약 5번 — 그림이 주인공. 패널을 크게 잡는다.
    fig, axes = plt.subplots(len(arms), len(els),
                             figsize=(3.5 * len(els), 3.15 * len(arms)),
                             dpi=170, squeeze=False)
    stat = {}
    for r, (arm, lab) in enumerate(arms):
        for c, el in enumerate(els):
            ax = axes[r][c]
            E, miss = load(arm, el)
            ftip = FTIP0 * np.cos(np.radians(el))
            if E is None:
                ax.text(0.5, 0.5, "not run" if miss == 0 else f"incomplete\n({miss} missing)",
                        ha="center", va="center", transform=ax.transAxes,
                        fontsize=11, color="#888")
                ax.set_xticks([]); ax.set_yticks([])
            else:
                f, t, S, _ = flash_spec(E, PRF, FFL, per)
                draw(ax, t, f, S, ftip, mode="peak")
                for y, col, ls in ((FFL, "#00d0ff", "-"), (2 * FFL, "#ff5ac8", "--")):
                    ax.axhline(y, color=col, lw=0.9, ls=ls, alpha=0.8)
                    ax.axhline(-y, color=col, lw=0.9, ls=ls, alpha=0.8)
                v = acdc(E, ftip, per)
                stat[(r, c)] = v
                if v is not None:
                    ax.text(0.97, 0.965, f"AC/DC {v:.1f} dB", transform=ax.transAxes,
                            ha="right", va="top", fontsize=10.5, color="white",
                            bbox=dict(fc="#0008", ec="none", pad=2.2))
            if r == 0:
                lab_el = "0" if el == 0 else f"−{abs(el):.0f}"
                ax.set_title(f"el {lab_el}°   $f_{{tip}}$ {ftip:.0f} Hz", fontsize=12.5)
            if c == 0:
                ax.set_ylabel(f"{lab}\nDoppler [Hz]", fontsize=12)
            else:
                ax.set_ylabel("")
            if r == len(arms) - 1:
                ax.set_xlabel("slow time [ms]", fontsize=10.5)
            ax.tick_params(labelsize=8.6)

    if a.title:
        fig.suptitle(a.title, fontsize=15, y=0.995)
    cap = a.note or ("each panel normalised to its own maximum, so levels are not "
                     "comparable across panels")
    fig.text(0.5, 0.004,
             f"cyan $f_{{flash}}$ 126.67 Hz · magenta 2$f_{{flash}}$ · {cap}",
             fontsize=9.4, color="#5a6570", ha="center", va="bottom")
    fig.tight_layout(rect=(0, 0.022, 1, 0.975 if a.title else 1.0))
    out = os.path.join(FIGDIR, f"{a.out}.png")
    fig.savefig(out, facecolor="white")
    print(f"  ✅ {os.path.relpath(out, ROOT)}   {len(arms)} 팔 × {len(els)} 앙각")
    for r, (arm, lab) in enumerate(arms):
        vs = [f"{stat.get((r,c)):.1f}" if stat.get((r, c)) is not None else "—"
              for c in range(len(els))]
        print(f"     {lab:26s} AC/DC  {' '.join(f'{v:>7s}' for v in vs)}")


if __name__ == "__main__":
    main()
