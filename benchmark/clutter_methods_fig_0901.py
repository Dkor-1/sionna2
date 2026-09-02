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
#: ⭐**다섯 팔 축으로 옮겼다**(사용자 지시 2026-09-02 — 「저거 팔 별로 다 보여주는 방향」).
#  ⛔옛 판은 `sionna_p4000000000_r15_n8192_d1` — 옛 「엔진 셋」 틀의 팔이라 **다섯 팔 중
#    어느 것도 아니었고 깊이도 1** 이었다. 덱 2 부(다섯 팔)는 깊이 2 인데 3 부만 깊이 1 이라
#    같은 것을 두 이름으로 부르게 됐다.
#  ⭐프롭 단독 대조는 다섯 팔에 없다(`partsprop` 은 옛 틀에만 있다) — 그래서 목표 열은
#    **자유공간 팔**(드론 몸통 없이 프로펠러만 도는 판)이 아니라, 같은 팔의 **el −30 판**을
#    쓰지 않는다. 대신 «필터 전» 을 목표로 놓고 필터가 무엇을 지우는지 본다.
MESH = "mfixbatteryi5_blperairframe"
FIVE = [("ours",        f"ours_r15_n8192_{MESH}"),
        ("all off",     f"sionna_p4000000000_swR0D0E0F1_r15_n8192_{MESH}_d2"),
        ("refraction",  f"sionna_p4000000000_swR1D0E0F1_r15_n8192_{MESH}_d2"),
        ("diffraction", f"sionna_p4000000000_swR0D1E1F1_r15_n8192_{MESH}_d2"),
        ("both",        f"sionna_p4000000000_swR1D1E1F1_r15_n8192_{MESH}_d2")]
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
           ("notch\n100 Hz", eca),
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
    # ⭐열 셋 — 프로펠러 단독(목표) · 전체 드론 · 에너지(사용자 지시 2026-09-02:
    #   「저 상태를 프로펠러만 돌린거랑 비교해야하지않을까」). 같은 필터를 양쪽에 건다.
    fig, ax = plt.subplots(len(METHODS), 3, figsize=(19.6, 2.25 * len(METHODS)),
                           gridspec_kw=dict(width_ratios=[1.0, 1.0, 1.15], wspace=0.13))
    for r, (nm, fn) in enumerate(METHODS):
        y = fn(W)
        yp = fn(P)                                   # 목표에도 같은 필터
        for ci, (dat, ttl) in enumerate(((yp, "propellers only"), (y, "whole drone"))):
            a = ax[r, ci]
            f_, t_, S_, _ = flash_spec(np.asarray(dat)[:NZ], PRF, FFL, PERIODS)
            draw(a, t_, f_, S_, f_tip(el))
            a.set_ylim(-2000, 2000)
            a.tick_params(labelsize=14, labelbottom=(r == len(METHODS) - 1))
            if ci == 0:
                a.set_ylabel(nm, fontsize=16, weight="bold", color=INK, linespacing=1.4)
            else:
                a.set_yticklabels([])
            if r == len(METHODS) - 1:
                a.set_xlabel("time [ms]", fontsize=16)
            if r == 0:
                a.set_title(ttl, fontsize=19, color=INK, weight="bold", pad=9)
        b = ax[r, 2]
        fr, Yp = psd(P)
        _, Yw = psd(y)
        b.plot(fr, Yw, color=NAVY, lw=1.0, alpha=0.9,
               label="whole drone" if r == 0 else None)
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
    # ⛔하단 문구를 뺐다(사용자 2026-09-02 — 「그림이 너무 작다」). 범례는 제목 줄에 붙인다.
    fig.subplots_adjust(top=0.862, bottom=0.082, left=0.092, right=0.990, hspace=0.16)
    h, l = ax[0, 2].get_legend_handles_labels()
    # ⛔범례가 «energy» 열 제목을 덮었다 — 머리글 줄 오른쪽 빈 자리로 올린다
    fig.legend(h, l, loc="upper right", bbox_to_anchor=(0.995, 0.995),
               fontsize=15, frameon=False, ncol=2)
    fig.text(0.34, 0.962, f"four ways to remove the steady echo   {chr(183)}   "
             f"el {el:+.0f}{DEG}", ha="center", fontsize=24, color=INK, weight="bold")
    fig.text(0.34, 0.912, sub, ha="center", fontsize=16, color=ACC, weight="bold")
    p = f"{ROOT}/outputs/figures/{fname}"
    fig.savefig(p, dpi=132, bbox_inches="tight"); plt.close(fig)
    print(f"  ✅ {p}")


def build_five(el, fname, sub):
    """⭐다섯 팔 x [필터 없음 · ECA · MTI] — 3 부를 2 부와 같은 축에 올린다.

    ⛔방식을 넷에서 셋으로 줄였다(사용자 승인 ⓐ). 「평균빼기」는 ECA 와 사실상 같고
       (0 Hz 한 칸 vs ±100 Hz), 「필터 없음」은 목표 열 노릇을 겸한다.
       5 팔 x 4 방식 x 3 열 = 60 판은 한 쪽에 못 넣는다.
    """
    import numpy as np
    Z = np.load(f"{ROOT}/outputs/elevation_sweep_md.npz")
    METH = [("no filter", lambda x: x),
            ("notch\n100 Hz", eca),
            ("MTI\n3-pulse", lambda x: mti(x, 3))]
    fig, ax = plt.subplots(len(METH), len(FIVE),
                           figsize=(3.75 * len(FIVE), 3.05 * len(METH)))
    for c, (nm, key) in enumerate(FIVE):
        k = f"{key}/el{el:+.0f}"
        if k not in Z.files:
            print(f"  ⚠ 없음 {k}"); continue
        E = np.asarray(Z[k])
        for r, (mn, fn) in enumerate(METH):
            a = ax[r, c]
            y = fn(E)
            f_, t_, S_, _ = flash_spec(np.asarray(y)[:NZ], PRF, FFL, PERIODS)
            draw(a, t_, f_, S_, f_tip(el))
            a.set_ylim(-2000, 2000)
            a.tick_params(labelsize=12, labelbottom=(r == len(METH) - 1))
            if r == 0:
                a.set_title(nm, fontsize=18, color=INK, weight="bold", pad=9)
            if r == len(METH) - 1:
                a.set_xlabel("time [ms]", fontsize=14)
            if c == 0:
                a.set_ylabel("Doppler [Hz]", fontsize=13)
            else:
                a.set_yticklabels([])
    # ⭐행 이름은 왼쪽 여백에 한 번(덱 배치 규약 2026-09-02)
    # ⛔행 이름이 y 축 이름과 겹쳤다 — 여백을 넓히고 더 왼쪽으로
    fig.subplots_adjust(top=0.842, bottom=0.085, left=0.135, right=0.990,
                        hspace=0.17, wspace=0.06)
    for r, (mn, _f) in enumerate(METH):
        bx = ax[r, 0].get_position()
        fig.text(0.072, bx.y0 + bx.height / 2, mn, ha="right", va="center",
                 fontsize=17, weight="bold", color=INK, linespacing=1.3)
    # ⛔그림 제목·부제 삭제(라벨 검증 2026-09-02) — 슬라이드 제목·결론바가 이미 말한다.
    p = f"{ROOT}/outputs/figures/{fname}"
    fig.savefig(p, dpi=126, bbox_inches="tight"); plt.close(fig)
    print(f"  ✅ {p}")


def main():
    build(0.0, "clutter_methods_el0.png",
          "the notch reveals the streaks - it does not remove them")
    build(-30.0, "clutter_methods_el30.png",
          "MTI drops the whole-drone curve 30-50 dB below the target")
    build_five(0.0, "clutter_five_el0.png",
               "the notch reveals the streaks; MTI takes the blade rate with them")
    build_five(-30.0, "clutter_five_el30.png",
               "MTI flattens every arm; the notch leaves all five as they were")


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
    fig.text(0.34, 0.962, "four ways to remove the steady echo",
             ha="center", fontsize=24, color=INK, weight="bold")
    fig.text(0.5, 0.912, f"matrice4e {chr(183)} 15 m {chr(183)} PathSolver, extra physics "
             f"off {chr(183)} dashed = blade-tip frequency",
             ha="center", fontsize=16, color=GRAY)
    # ⛔각주를 지웠다(사용자 지시 2026-09-02) — 결론바가 같은 말을 하고 있고,
    #   0.64 % · 55.7 dB 는 발표자 노트에 있다. 그림에 변명을 적지 않는다.
    p = f"{ROOT}/outputs/figures/clutter_methods_0901.png"
    fig.savefig(p, dpi=132, bbox_inches="tight"); plt.close(fig)
    print(f"  ✅ {p}")


if __name__ == "__main__":
    print("═══ 클러터 제거 방식 · 그림 ═══")
    main()
