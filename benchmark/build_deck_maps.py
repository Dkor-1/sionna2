# -*- coding: utf-8 -*-
"""
build_deck_maps.py — 0818 팀미팅 덱이 쓸 **마이크로도플러 맵**을 굽는다.

리포트 그림(`ch1_f1_maps_r15.png`)은 앙각 7 점 중 넷만 싣는다. 덱은 토론용이라
**일곱 점을 전부** 보여야 하고, 글자가 발표장에서 읽혀야 한다.

굽는 것
    outputs/figures/deck_maps_full.png   팔 3 × 앙각 7 — 전수 격자(덱의 본판)
    outputs/figures/deck_maps_pair.png   앙각 두 점(0° · −60°)만 크게 — «무엇이 다른가»
    outputs/figures/deck_maps_nadir.png  직하방 한 점 — 세 팔이 나란히

규약
  · 그림 안 글자는 **영어**, 본문·노트는 한국어([[sionna2-viz-english]]).
  · STFT 는 `md_mapstyle.flash_spec` 기본값(0.6 주기 · hop 2)을 쓴다 — 플래시가 보이는 설정.
    설정값은 그림에 적지 않고 **리포트·노트**에 적는다([[md-time-resolution-first]]).
  · 패널마다 자기 최댓값으로 정규화한다. 그래서 **판 사이 레벨 비교는 이 그림 밖**이다.
  · 겹침 금지 — 제목·라벨·주석이 서로 물리지 않는지 눈으로 본다([[figure-and-plain-language]]).

    PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/build_deck_maps.py
"""
from __future__ import annotations

import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                       # noqa: E402
import numpy as np                                                    # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
from md_mapstyle import auto_periods, flash_spec, draw                 # noqa: E402

FIG = os.path.join(ROOT, "outputs", "figures")
os.makedirs(FIG, exist_ok=True)

J = json.load(open(f"{ROOT}/outputs/elevation_sweep_md.json"))
Z = np.load(f"{ROOT}/outputs/elevation_sweep_md.npz", allow_pickle=True)
M = J["_meta"]
assert int(np.asarray(Z["phase_sign_v2"]).ravel()[0]) == 1, "⛔ 부호 정정본이 아니다"

PRF = float(M["prf_hz"])
FFL = float(M["f_flash_hz"])
PERIODS = auto_periods(PRF, FFL)
ELS = [0.0, -15.0, -30.0, -45.0, -60.0, -75.0, -90.0]
ROW = {(r["engine"], r["el_deg"]): r for r in J["rows"]}

#: 덱이 쓰는 세 팔 — 광선 예산이 40 억 발로 같고, 갈리는 축은 엔진과 물리 스위치뿐이다.
ARMS = [
    ("ours_r15_n8192", "Our kernel"),
    ("sionna_p4000000000_r15_n8192_d1", "Sionna, physics off"),
    ("sionna_p4000000000_phys_r15_n8192_d1", "Sionna, physics on"),
]

#: 잘라 볼 구간 — 앞쪽 20 ms 를 건너뛰고 60 ms. 플래시가 여러 번 지나가는 길이다.
T0, TSPAN = 0.020, 0.060

plt.rcParams.update({
    "font.size": 15, "axes.titlesize": 17, "axes.labelsize": 15,
    "figure.facecolor": "white", "savefig.facecolor": "white",
})


def panel(ax, arm, el, *, show_ftip=True):
    n0, nz = int(round(T0 * PRF)), int(round(TSPAN * PRF))
    E = np.asarray(Z[f"{arm}/el{el:+.0f}"], complex)[n0:n0 + nz]
    f, t, S, _ = flash_spec(E, PRF, FFL, PERIODS)
    ft = float(ROW[(arm, el)]["f_tip_hz"])
    m = draw(ax, t, f, S, ft)                     # 패널마다 자기 최댓값 기준
    ax.set_ylim(-2000, 2000)
    if show_ftip:
        ax.text(0.035, 0.945, r"$f_{\rm tip}$ = " + f"{ft:.0f} Hz",
                transform=ax.transAxes, color="w", fontsize=12.5, va="top",
                bbox=dict(fc="k", alpha=0.5, ec="none", pad=2.2))
    return m


def full_grid():
    """팔 3 × 앙각 7 — 덱의 본판."""
    fig, ax = plt.subplots(3, 7, figsize=(25.0, 10.4), sharex=True, sharey=True)
    for i, (arm, nm) in enumerate(ARMS):
        for j, el in enumerate(ELS):
            a = ax[i, j]
            m = panel(a, arm, el)
            if i == 0:
                a.set_title(f"{el:+.0f}°" + ("\n(straight below)" if el == -90 else ""),
                            pad=8)
            if j == 0:
                a.set_ylabel(f"{nm}\nDoppler [Hz]")
            if i == 2:
                a.set_xlabel("time [ms]")
    fig.suptitle("What the radar sees as it moves under the drone", y=0.985, fontsize=22)
    fig.text(0.5, 0.945, "each panel is scaled to its own brightest point, "
                         "so compare shapes and not brightness",
             ha="center", fontsize=14, color="0.35")
    cb = fig.colorbar(ax[0, 0].collections[0], ax=ax, fraction=0.013, pad=0.008)
    cb.set_label("dB below the brightest point in that panel")
    out = f"{FIG}/deck_maps_full.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✅ {out}")


def pair(els=(0.0, -60.0), stem="deck_maps_pair"):
    """앙각 두 점만 크게 — 한 슬라이드에서 «무엇이 다른가» 를 묻는 판."""
    fig, ax = plt.subplots(len(els), 3, figsize=(17.0, 4.7 * len(els)),
                           sharex=True, sharey=True)
    ax = np.atleast_2d(ax)
    for r, el in enumerate(els):
        for c, (arm, nm) in enumerate(ARMS):
            a = ax[r, c]
            panel(a, arm, el)
            if r == 0:
                a.set_title(nm, pad=8)
            if c == 0:
                a.set_ylabel(f"looking {abs(el):.0f}° below level\nDoppler [Hz]"
                             if el else "looking level\nDoppler [Hz]")
            if r == len(els) - 1:
                a.set_xlabel("time [ms]")
    fig.suptitle("Same target, same rays, same place, and only the engine differs",
                 y=0.985, fontsize=20)
    cb = fig.colorbar(ax[0, 0].collections[0], ax=ax, fraction=0.016, pad=0.010)
    cb.set_label("dB below the brightest point in that panel")
    out = f"{FIG}/{stem}.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✅ {out}")


if __name__ == "__main__":
    print("═══ 덱 맵 ═══")
    full_grid()
    pair((0.0, -60.0), "deck_maps_pair")
    pair((-90.0,), "deck_maps_nadir")
