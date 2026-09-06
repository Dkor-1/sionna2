# -*- coding: utf-8 -*-
"""build_vol12_figs.py — 리포트 12 «실외 장면» 그림.

⛔판형 함정(2026-09-01 사용자 지적 「글자가 겹침이 매우 심한데」):
  · 줄 이름을 세로로 왼쪽 여백에 두면 y 축 라벨과 겹친다 ⇒ **첫 판 안에 배지**로 넣는다
  · 출처 줄이 x 축 라벨과 겹친다 ⇒ 아래 여백을 넉넉히
  · 부제가 길면 좌우로 잘린다 ⇒ 짧게

⛔잣대 이름을 그림에 «rho» 로 쓰지 않는다 — 전문용어다. 재는 것은 「포락이 되풀이되는가」이므로
   **envelope repeat** 로 적고 수를 곁들인다.
⛔ 2026-09-06 그 수로 «있다/없다» 를 찍지 않는다 — 종전 규약 「**repeats / no repeat** 로 적고」
   는 자유 문턱 |rho| > 0.10 하나에 판정을 걸어 두었으므로 내렸다. 배지는 수만 싣는다.

    PYTHONPATH=src:benchmark /workspace/.venvs/py312/bin/python benchmark/build_vol12_figs.py
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


#: (얼굴 이름, 한국어 메모, 환경 켜나, 정지 성분 걷어내나, 꺼지는 자세를 메우나)
#: ⭐네 번째 줄이 이 그림의 알맹이다 — 실외에서 박자를 가린 것은 장면 전체가 아니라
#  «|E| 가 중앙값의 10 % 아래로 꺼지는» 소수의 자세다(el −30 에서 8,192 중 74 개).
ROWS = [("free space", "지금까지 봐 온 판", False, False, False),
        ("outdoor scene", "지면·건물을 넣었다", True, False, False),
        ("static part removed", "걷어내 봤다", True, True, False),
        ("dips filled in", "꺼지는 자세만 이웃값으로", True, False, True),
        #: ⭐다섯째 줄 — 넷째 줄은 빗살 수가 돌아오는데 **그림은 평평하다.** 지면의 정지
        #  성분이 색눈금을 다 먹어서 작은 주기 성분이 안 보이기 때문이다. 둘을 같이 해야
        #  «수» 와 «그림» 이 같은 것을 말하는지 볼 수 있다.
        ("dips filled, then static removed", "둘 다 — 순서가 중요하다", True, True, True)]


def fill_dips(E):
    """|E| 가 중앙값의 10 % 아래로 꺼지는 자세를 이웃값으로 메운다.

    ⚠**메운다** 는 것은 그 자세의 값을 버리고 앞뒤에서 이어 붙인다는 뜻이다. 물리를
      고치는 것이 아니라 «그 자세들이 없었다면 무엇이 보이나» 를 묻는 조작이다.
      규약은 `benchmark/outdoor_scene_0901.py` 와 같다(|E| < 중앙값 × 0.1).
    """
    a = np.abs(E); med = float(np.median(a))
    bad = np.where(a / med < 0.1)[0] if med > 0 else np.zeros(0, int)
    if not len(bad):
        return E, 0
    good = np.setdiff1d(np.arange(E.size), bad)
    R = E.copy()
    R[bad] = (np.interp(bad, good, E[good].real)
              + 1j * np.interp(bad, good, E[good].imag))
    return R, len(bad)


def main():
    fig, ax = plt.subplots(len(ROWS), len(ELS), figsize=(17.4, 24.0), squeeze=False)
    for r, (lab, _ko, use_env, remove, fill) in enumerate(ROWS):
        for c, el in enumerate(ELS):
            M = grid_mod(el)
            E = np.asarray(Z[arm(el, use_env)])
            #: ⭐⭐**순서가 결과를 바꾼다.** 반드시 «메우고 → 뺀다» 다.
            #  꺼지는 자세는 «|E| 가 중앙값의 10 % 아래» 로 찾는데, 정지 성분을 먼저 빼면
            #  중앙값이 확 작아져서 엉뚱한 자세가 걸린다(el −30 에서 74 개 → 290 개).
            #  실측: 메움→제거 59.7 dB · 제거→메움 4.3 dB (2026-09-07).
            n_dip = 0
            if fill:
                E, n_dip = fill_dips(E)
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
            a.set_xlabel("time [ms]" if r == len(ROWS) - 1 else "")
            if c == 0:
                a.set_ylabel("Doppler [Hz]", fontsize=17)
            else:
                a.set_yticklabels([])
            if r != len(ROWS) - 1:
                a.set_xticklabels([])

            # ⭐줄 이름 — 왼쪽 여백이 아니라 **첫 판 안**에 (여백 겹침을 원천 차단)
            if c == 0:
                a.text(0.028, 0.945, lab, transform=a.transAxes, ha="left", va="top",
                       fontsize=(15 if len(lab) > 24 else 19), weight="bold", color="white",
                       bbox=dict(boxstyle="round,pad=0.38", fc=(0, 0, 0, 0.62),
                                 ec="white", lw=1.5))
            # ⛔ 2026-09-06 판정 배지를 내린다 — 자유 문턱 |rho| > 0.10 하나로 판마다
            #    «beat repeats / no repeat» 를 찍고 초록·빨강으로 칠하던 자리다. 레포가
            #    문서로 무효화한 판정 규칙이 그림 얼굴에서만 살아 있었고, 문턱 하나가
            #    빗나가면 실외 장면 서사 전체가 거짓음성 위에 선다. 수만 남기고, 박자가
            #    있느냐는 빗살 선(f_flash 하모닉)으로 따로 읽는다.
            #: ⭐잣대를 정본으로 바꿨다(2026-09-07). ρ(포락 자기상관)는 «리듬» 이 아니라
            #  «매끄러움» 을 잰다 — 직선·계단·붉은잡음이 전부 «박자» 칸에 든다
            #  (docs/RHO_IS_SMOOTHNESS_0902.md). 박자는 **빗살 하모닉 SNR** 로 읽는다.
            #  ⛔판정 문구·색칠을 붙이지 않는다. 수만 적고 읽기는 사람이 한다.
            import comb_snr as _CS                                     # noqa: PLC0415
            v = _CS.comb_snr(E, M.PRF, el, arm=arm(el, use_env))
            txt = "comb SNR\n—" if v is None else f"comb SNR\n{float(v):.1f} dB"
            if fill and n_dip:
                txt += f"\n({n_dip} dips filled)"
            a.text(0.972, 0.945, txt,
                   transform=a.transAxes, ha="right", va="top", fontsize=16,
                   weight="bold", color="white", linespacing=1.3,
                   bbox=dict(boxstyle="round,pad=0.36", ec="white", lw=1.6,
                             fc=(0.16, 0.16, 0.18, 0.88)))

    fig.subplots_adjust(top=0.925, bottom=0.062, left=0.062, right=0.988,
                        hspace=0.075, wspace=0.045)
    #: ⛔제목에 판정을 넣지 않는다 — 무엇을 보는 중인지만 적는다(집 규약).
    fig.text(0.5, 0.978, "Free space, outdoor scene, and two ways of undoing it",
             ha="center", fontsize=27, color=INK, weight="bold")
    fig.text(0.5, 0.956, "comb SNR is the harmonic line of the blade beat above the "
             "surrounding floor, in dB", ha="center", fontsize=16, color=GRAY)
    fig.text(0.008, 0.012, "stock engine, extra physics off  ·  matrice4e at 15 m  ·  "
             "8,192 poses  ·  ground 120x120 m concrete + 4 buildings + 2 poles, drone 20 m up",
             ha="left", fontsize=13, color=GRAY)
    out = f"{FIG}/vol12_outdoor_stft.png"
    fig.savefig(out, dpi=140)
    plt.close(fig)
    print(f"  ✅ {out}")


if __name__ == "__main__":
    print("═══ 리포트 12 그림 ═══")
    main()
