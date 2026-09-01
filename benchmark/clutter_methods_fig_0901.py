# -*- coding: utf-8 -*-
"""clutter_methods_fig_0901.py — 정지 클러터 제거 방식을 STFT + 에너지로 견준다.

사용자 요청(2026-09-01): 「평균빼기, ECA, MTI 전부 다 STFT 해둔거 비교해서 보여줄 수
있나? 에너지 쪽 그래프도 그렇고」

⭐숫자 비교는 `clutter_methods_0901.py` 가 낸다. 여기는 **눈으로 보는 판**이다.
⛔MTI 는 0 Hz 를 지우는 대신 날개 박자(126.7 Hz = PRF 의 0.64 %)를 27.9~83.6 dB
   깎는다 — MTI 저지대역 한복판이다. 그림에서 그게 보여야 한다.
"""
import math
import os
import sys

import numpy as np

ROOT = "/workspace/sionna"
sys.path.insert(0, f"{ROOT}/benchmark")
sys.path.insert(0, f"{ROOT}/src")
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
os.environ.setdefault("SWGRID_EL", "-30")

import matplotlib.pyplot as plt                                        # noqa: E402
from clutter_parts_ladder_0824 import load, f_tip, PRF, FFL            # noqa: E402
from md_mapstyle import auto_periods, flash_spec, draw                 # noqa: E402

INK, GRAY, ACC, NAVY = "#141926", "#5E5E5E", "#C81E3C", "#1F3864"
ORANGE = "#E07B39"
DEG, MINUS = chr(176), chr(8722)
ARM_W = "sionna_p4000000000_r15_n8192_d1"
ARM_P = "sionna_p4000000000_partsprop_r15_n8192_d1"
PERIODS = auto_periods(PRF, FFL)
NZ = int(round(0.058 * PRF))


def eca(x, fcut=100.0):
    X = np.fft.fft(x)
    fr = np.fft.fftfreq(x.size, 1.0 / PRF)
    X[np.abs(fr) <= fcut] = 0.0
    return np.fft.ifft(X)


def mti(x, k=3):
    c = [(-1) ** i * math.comb(k - 1, i) for i in range(k)]
    y = np.zeros_like(x)
    y[k - 1:] = sum(c[i] * x[k - 1 - i: x.size - i] for i in range(k))
    return y


#: ⛔행 이름은 짧아야 한다 — 길면 위아래 이름끼리 겹친다(2026-09-01)
METHODS = [("no filter", lambda x: x),
           ("mean\nsubtracted", lambda x: x - x.mean()),
           ("ECA notch\n100 Hz", eca),
           ("MTI\n3-pulse", lambda x: mti(x, 3))]
ELS = (0.0, -30.0)


def psd(x):
    w = np.hanning(x.size)
    Y = np.abs(np.fft.fftshift(np.fft.fft(x * w))) ** 2 / (w.sum()) ** 2
    fr = np.fft.fftshift(np.fft.fftfreq(x.size, 1.0 / PRF))
    return fr, 10 * np.log10(Y + 1e-300)


def build(el, fname, sub):
    """⭐각도 하나 = 그림 하나. 16 판을 한 장에 넣으면 슬라이드에서 눈금이 안 읽힌다
       (사용자 지적 2026-09-01). 4 방식 x [STFT · 에너지] = 8 판이면 두 배로 커진다."""
    W, P = load(ARM_W, el)[0], load(ARM_P, el)[0]
    fig, ax = plt.subplots(len(METHODS), 2, figsize=(13.6, 2.75 * len(METHODS)),
                           gridspec_kw=dict(width_ratios=[1.0, 1.0], wspace=0.17))
    for r, (nm, fn) in enumerate(METHODS):
        y = fn(W)
        a = ax[r, 0]
        f_, t_, S_, _ = flash_spec(np.asarray(y)[:NZ], PRF, FFL, PERIODS)
        draw(a, t_, f_, S_, f_tip(el))
        a.set_ylim(-2000, 2000)
        a.tick_params(labelsize=14, labelbottom=(r == len(METHODS) - 1))
        a.set_ylabel(nm, fontsize=16, weight="bold", color=INK, linespacing=1.4)
        if r == len(METHODS) - 1:
            a.set_xlabel("time [ms]", fontsize=16)
        if r == 0:
            a.set_title("time-frequency", fontsize=19, color=INK, weight="bold", pad=9)
        b = ax[r, 1]
        fr, Yp = psd(P)
        _, Yw = psd(y)
        b.plot(fr, Yw, color=NAVY, lw=1.0, alpha=0.9,
               label="whole drone, filtered" if r == 0 else None)
        b.plot(fr, Yp, color=ORANGE, lw=1.1,
               label="propellers only" if r == 0 else None)
        for sgn in (-1, 1):
            b.axvline(sgn * f_tip(el), color="0.6", lw=1.1, ls=(0, (4, 4)), zorder=1)
        b.set_xlim(-2000, 2000); b.set_xticks([-1500, 0, 1500])
        top = max(float(Yw.max()), float(Yp.max()))
        b.set_ylim(top - 120, top + 6)
        b.tick_params(labelsize=14, labelbottom=(r == len(METHODS) - 1))
        if r == len(METHODS) - 1:
            b.set_xlabel("Doppler [Hz]", fontsize=16)
        if r == 0:
            b.set_title("energy", fontsize=19, color=INK, weight="bold", pad=9)
        b.grid(True, color="#E8E8E8", lw=0.6); b.set_axisbelow(True)
        for sp in ("top", "right"):
            b.spines[sp].set_visible(False)
    fig.subplots_adjust(top=0.870, bottom=0.115, left=0.108, right=0.988, hspace=0.20)
    h, l = ax[0, 1].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", bbox_to_anchor=(0.5, 0.005),
               fontsize=16, frameon=False, ncol=2)
    fig.text(0.5, 0.962, f"four ways to remove the steady echo   {chr(183)}   "
             f"el {el:+.0f}{DEG}", ha="center", fontsize=25, color=INK, weight="bold")
    fig.text(0.5, 0.918, sub, ha="center", fontsize=17, color=ACC, weight="bold")
    p = f"{ROOT}/outputs/figures/{fname}"
    fig.savefig(p, dpi=132, bbox_inches="tight"); plt.close(fig)
    print(f"  ✅ {p}")


def main():
    build(0.0, "clutter_methods_el0.png",
          "the notch reveals the streaks - it does not remove them")
    build(-30.0, "clutter_methods_el30.png",
          "MTI drops the whole-drone curve 30-50 dB below the target")


def _old_main():

    D = {el: (load(ARM_W, el)[0], load(ARM_P, el)[0]) for el in ELS}
    fig, ax = plt.subplots(len(METHODS), 4, figsize=(16.4, 3.35 * len(METHODS)))
    for r, (nm, fn) in enumerate(METHODS):
        for ci, el in enumerate(ELS):
            W, P = D[el]
            y = fn(W)
            # ── STFT
            a = ax[r, 2 * ci]
            f_, t_, S_, _ = flash_spec(np.asarray(y)[:NZ], PRF, FFL, PERIODS)
            draw(a, t_, f_, S_, f_tip(el))
            a.set_ylim(-2000, 2000)
            a.tick_params(labelsize=13, labelbottom=(r == len(METHODS) - 1))
            if r == len(METHODS) - 1:
                a.set_xlabel("time [ms]", fontsize=14)
            if ci == 0:
                a.set_ylabel(nm, fontsize=15, weight="bold", color=INK)
            if r == 0:
                a.set_title(f"STFT  {chr(183)}  el {el:+.0f}{DEG}", fontsize=17,
                            color=INK, weight="bold", pad=8)
            # ── 에너지 분포
            b = ax[r, 2 * ci + 1]
            fr, Yp = psd(P)
            _, Yw = psd(y)
            b.plot(fr, Yw, color=NAVY, lw=0.8, alpha=0.9,
                   label="whole drone, filtered" if (r == 0 and ci == 0) else None)
            b.plot(fr, Yp, color=ORANGE, lw=0.9,
                   label="propellers only" if (r == 0 and ci == 0) else None)
            ft = f_tip(el)
            for sgn in (-1, 1):
                b.axvline(sgn * ft, color="0.6", lw=1.0, ls=(0, (4, 4)), zorder=1)
            b.set_xlim(-2000, 2000); b.set_xticks([-1500, 0, 1500])
            top = max(float(Yw.max()), float(Yp.max()))
            b.set_ylim(top - 120, top + 6)
            b.tick_params(labelsize=13, labelbottom=(r == len(METHODS) - 1))
            if r == len(METHODS) - 1:
                b.set_xlabel("Doppler [Hz]", fontsize=14)
            if r == 0:
                b.set_title(f"energy  {chr(183)}  el {el:+.0f}{DEG}", fontsize=17,
                            color=INK, weight="bold", pad=8)
            b.grid(True, color="#E8E8E8", lw=0.6); b.set_axisbelow(True)
            for sp in ("top", "right"):
                b.spines[sp].set_visible(False)
        print(f"  {nm}")
    fig.subplots_adjust(top=0.855, bottom=0.075, left=0.088, right=0.988,
                        hspace=0.20, wspace=0.16)
    # ⭐범례는 그림 **밖**에 둔다(사용자 지시 2026-09-01 — 안에 두면 곡선을 덮는다)
    h, l = ax[0, 1].get_legend_handles_labels()
    fig.legend(h, l, loc="upper right", bbox_to_anchor=(0.988, 0.912),
               fontsize=15, frameon=False, ncol=2)
    fig.text(0.5, 0.962, "four ways to remove the steady echo",
             ha="center", fontsize=24, color=INK, weight="bold")
    fig.text(0.5, 0.912, f"matrice4e {chr(183)} 15 m {chr(183)} PathSolver, extra physics "
             f"off {chr(183)} dashed = blade-tip frequency",
             ha="center", fontsize=16, color=GRAY)
    fig.text(0.008, 0.012, f"MTI removes the steady echo, and the blade rate with it - "
             f"126.7 Hz is 0.64 % of the 19.7 kHz PRF, so a 3-pulse canceller sits "
             f"55.7 dB down there", ha="left", fontsize=14, color=ACC, weight="bold")
    p = f"{ROOT}/outputs/figures/clutter_methods_0901.png"
    fig.savefig(p, dpi=132, bbox_inches="tight"); plt.close(fig)
    print(f"  ✅ {p}")


if __name__ == "__main__":
    print("═══ 클러터 제거 방식 · 그림 ═══")
    main()
