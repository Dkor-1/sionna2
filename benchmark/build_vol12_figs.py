# -*- coding: utf-8 -*-
"""build_vol12_figs.py — 리포트 12 «실외 장면» 그림.

⛔판형 함정(2026-09-01 사용자 지적 「글자가 겹침이 매우 심한데」):
  · 줄 이름을 세로로 왼쪽 여백에 두면 y 축 라벨과 겹친다 ⇒ **첫 판 안에 배지**로 넣는다
  · 출처 줄이 x 축 라벨과 겹친다 ⇒ 아래 여백을 넉넉히
  · 부제가 길면 좌우로 잘린다 ⇒ 짧게

⛔잣대 이름을 그림에 «rho» 로 쓰지 않는다 — 전문용어다. 재는 것은 「포락이 되풀이되는가」이므로
   **repeats / no repeat** 로 적고 수는 곁들인다.

    PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/build_vol12_figs.py
"""
import importlib
import os
import sys

import numpy as np

ROOT = "/workspace/sionna"
sys.path.insert(0, f"{ROOT}/benchmark")
sys.path.insert(0, f"{ROOT}/src")
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

import matplotlib.pyplot as plt                                        # noqa: E402
from clutter_parts_ladder_0824 import cs_eca                           # noqa: E402

FIG = f"{ROOT}/outputs/figures"
MESH = "mfixbatteryi5_blperairframe"
ELS = [0.0, -30.0, -60.0]
DEG, MINUS = chr(176), chr(8722)
GREEN, RED, INK, GRAY = "#1C7A40", "#C81E3C", "#141926", "#5E5E5E"
Z = np.load(f"{ROOT}/outputs/elevation_sweep_md.npz")


def arm(el, env=False):
    tag = "_envoutdoor01" if env else ""
    return f"sionna_p4000000000_swR0D0E0F1_r15_n8192{tag}_{MESH}_d2/el{el:+.0f}"


def rho(E):
    a = np.abs(np.asarray(E))
    ac = a - a.mean()
    d = float(np.dot(ac, ac))
    return float(np.dot(ac[:-1], ac[1:]) / d) if d > 0 else float("nan")


def grid_mod(el):
    """⚠FT30 이 임포트 시점에 SWGRID_EL 로 굳는다 — 앙각마다 다시 부른다."""
    os.environ["SWGRID_EL"] = f"{el:g}"
    import build_switch_grid_figs as M
    importlib.reload(M)
    return M


ROWS = [("free space", "지금까지 봐 온 판", False, False),
        ("outdoor scene", "지면·건물을 넣었다", True, False),
        ("static part removed", "걷어내 봤다", True, True)]


def main():
    fig, ax = plt.subplots(3, len(ELS), figsize=(17.4, 15.0), squeeze=False)
    for r, (lab, _ko, use_env, remove) in enumerate(ROWS):
        for c, el in enumerate(ELS):
            M = grid_mod(el)
            E = np.asarray(Z[arm(el, use_env)])
            if remove:
                E = cs_eca(E)
            n0 = int(round(M.T0 * M.PRF))
            nz = int(round(M.TSPAN * M.PRF))
            f_, t_, S_, _ = M.flash_spec(E[n0:n0 + nz], M.PRF, M.FFL, M.PERIODS)
            a = ax[r, c]
            M.draw(a, t_, f_, S_, M.FT30)
            a.set_ylim(-2200, 2200)
            if r == 0:
                a.set_title(f"el {el:+.0f}{DEG}".replace("-", MINUS),
                            fontsize=22, pad=11)
            a.set_xlabel("time [ms]" if r == 2 else "")
            if c == 0:
                a.set_ylabel("Doppler [Hz]", fontsize=17)
            else:
                a.set_yticklabels([])
            if r != 2:
                a.set_xticklabels([])

            # ⭐줄 이름 — 왼쪽 여백이 아니라 **첫 판 안**에 (여백 겹침을 원천 차단)
            if c == 0:
                a.text(0.028, 0.945, lab, transform=a.transAxes, ha="left", va="top",
                       fontsize=19, weight="bold", color="white",
                       bbox=dict(boxstyle="round,pad=0.38", fc=(0, 0, 0, 0.62),
                                 ec="white", lw=1.5))
            # ⭐판정 — «rho» 대신 쉬운 말
            rr = rho(E)
            ok = abs(rr) > 0.10
            a.text(0.972, 0.945, ("beat repeats" if ok else "no repeat") + f"\n{rr:+.3f}",
                   transform=a.transAxes, ha="right", va="top", fontsize=17,
                   weight="bold", color="white", linespacing=1.3,
                   bbox=dict(boxstyle="round,pad=0.36", ec="white", lw=1.6,
                             fc=(0.09, 0.42, 0.14, 0.88) if ok
                             else (0.58, 0.06, 0.16, 0.88)))

    fig.subplots_adjust(top=0.858, bottom=0.062, left=0.062, right=0.988,
                        hspace=0.075, wspace=0.045)
    fig.text(0.5, 0.962, "what the outdoor scene does to the blade beat",
             ha="center", fontsize=27, color=INK, weight="bold")
    fig.text(0.5, 0.930, "the stripes go, and removing the static part does not "
             "bring them back", ha="center", fontsize=20, color=RED, weight="bold")
    fig.text(0.5, 0.903, "the number is how strongly the envelope repeats - "
             "near zero means no beat, whatever the level says",
             ha="center", fontsize=15, color=GRAY)
    fig.text(0.008, 0.012, "stock engine, extra physics off  ·  matrice4e at 15 m  ·  "
             "8,192 poses  ·  our own kernel cannot run this scene yet - see section 3",
             ha="left", fontsize=13, color=GRAY)
    out = f"{FIG}/vol12_outdoor_stft.png"
    fig.savefig(out, dpi=140)
    plt.close(fig)
    print(f"  ✅ {out}")


if __name__ == "__main__":
    print("═══ 리포트 12 그림 ═══")
    main()
