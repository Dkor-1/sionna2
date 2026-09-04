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
#: ⚠일곱 열 격자에서는 행 이름이 길면 **위아래 행 이름끼리 겹친다**. 짧은 이름을 따로 둔다.
SHORT = {"Our kernel": "Ours", "Sionna, physics off": "Physics off",
         "Sionna, physics on": "Physics on"}

#: ⭐**물리 켬 곡선은 연하게 그린다** (사용자 지시 2026-08-17: «너무 난잡해서 보기 힘들어»).
#  이 팔은 선이 서지 않고 바닥이 출렁이는 것이 판정 내용이라, 곡선 하나가 화면의 절반을
#  덮으면서 **정작 봐야 할 빨강·회색 빗살을 가린다**. 그래서 굵기를 줄이고 투명하게,
#  그리고 뒤로 보낸다 — 지우는 것이 아니라 뒤로 물리는 것이라 판정은 그대로 선다.
#  ⚠범례 표본만은 불투명하게 되돌린다(연한 선은 범례에서 안 보인다).
LINE_STYLE = {
    "Our kernel":          dict(lw=2.0, alpha=1.00, zorder=4),
    "Sionna, physics off": dict(lw=2.0, alpha=1.00, zorder=3),
    "Sionna, physics on":  dict(lw=1.1, alpha=0.38, zorder=2),
}


def opaque_legend(a, **kw):
    """범례를 그리되 표본선은 불투명·굵게 — 연한 곡선도 범례에서는 보이게."""
    leg = a.legend(**kw)
    for h in leg.legend_handles:
        h.set_alpha(1.0)
        h.set_linewidth(2.6)
    return leg

#: 잘라 볼 구간 — 앞쪽 20 ms 를 건너뛰고 60 ms. 플래시가 여러 번 지나가는 길이다.
T0, TSPAN = 0.020, 0.060

#: ⭐발표장에서 읽히는 크기. 슬라이드가 그림에 주는 폭이 약 25 in 이고 그림을 그 폭에
#  맞춰 축소하므로, 그림 안 글자는 «슬라이드에서 몇 pt 로 보이나» 로 정해야 한다.
plt.rcParams.update({
    "font.size": 19, "axes.titlesize": 22, "axes.labelsize": 19,
    "xtick.labelsize": 17, "ytick.labelsize": 17,
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
                transform=ax.transAxes, color="w", fontsize=15.5, va="top",
                bbox=dict(fc="k", alpha=0.5, ec="none", pad=2.2))
    return m


def full_grid():
    """팔 3 × 앙각 7 — 덱의 본판."""
    #: ⚠슬라이드의 그림 상자는 가로세로비 약 3.4 다. 그림이 그보다 «세로로 길면»
#  높이에 맞춰 축소돼 폭을 절반만 쓴다 — 발표장에서 안 읽힌다.
    fig, ax = plt.subplots(3, 7, figsize=(26.0, 9.0), sharex=True, sharey=True)
    for i, (arm, nm) in enumerate(ARMS):
        for j, el in enumerate(ELS):
            a = ax[i, j]
            m = panel(a, arm, el)
            if i == 0:
                a.set_title(f"{el:+.0f}" + chr(176), pad=8)
            if j == 0:
                a.set_ylabel(f"{SHORT.get(nm, nm)}\nDoppler [Hz]")
            if i == 2:
                a.set_xlabel("time [ms]")
    # ⚠제목·부제·컬러바의 자리를 **직접** 잡는다. 기본 배치에 맡기면 그림을 눕힐 때마다
    #   제목이 열 제목 위로 내려앉는다(2026-08-14 에 두 번 겪었다).
    fig.subplots_adjust(top=0.905, bottom=0.098, left=0.078, right=0.952,
                        hspace=0.20, wspace=0.10)
    fig.text(0.5, 0.962, "each panel scaled to its own peak",
             ha="center", fontsize=19, color="0.35")
    cax = fig.add_axes([0.960, 0.088, 0.008, 0.817])
    cb = fig.colorbar(ax[0, 0].collections[0], cax=cax)
    cb.set_label("dB below the brightest point in that panel", fontsize=17)
    out = f"{FIG}/deck_maps_full.png"
    fig.savefig(out, dpi=150)          # ⚠tight 로 자르면 계산해 둔 가로세로비가 틀어진다
    plt.close(fig)
    print(f"  ✅ {out}")


def pair(els=(0.0, -60.0), stem="deck_maps_pair", title=None):
    """앙각 한두 점만 크게 — 한 슬라이드에서 «무엇이 다른가» 를 묻는 판."""
    nr = len(els)
    fig, ax = plt.subplots(nr, 3, figsize=(27.5, 4.1 * nr + 0.6),
                           sharex=True, sharey=True)
    ax = np.atleast_2d(ax)
    for r, el in enumerate(els):
        for c, (arm, nm) in enumerate(ARMS):
            a = ax[r, c]
            panel(a, arm, el)
            if r == 0:
                a.set_title(nm, pad=8)
            if c == 0:
                a.set_ylabel(f"{el:+.0f}" + chr(176) + "\nDoppler [Hz]")
            if r == len(els) - 1:
                a.set_xlabel("time [ms]")
    #: ⚠한 줄짜리 판에서 y 를 0.985 로 두면 제목이 **열 제목과 겹친다**. 줄 수로 띄운다.
    if title:
        fig.suptitle(title, y=1.0 - 0.012 / nr, fontsize=25)
        fig.subplots_adjust(top=0.86 if nr == 1 else 0.92)
    cb = fig.colorbar(ax[0, 0].collections[0], ax=ax, fraction=0.016, pad=0.010)
    cb.set_label("dB below the brightest point in that panel")
    out = f"{FIG}/{stem}.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✅ {out}")


def leakage_bars():
    """상한 위 누설 막대 — 덱 전용 **가로 판**.

    리포트 그림(`ch1_f6_above_tip_r15.png`)은 위아래 두 칸이라 슬라이드에서 폭 30 % 밖에
    못 쓴다. 발표장에서 읽히려면 폭을 채워야 하므로 막대만 넓게 다시 그린다.
    """
    WB = json.load(open(f"{ROOT}/outputs/wideband_energy_r15.json"))["cells"]
    els = [0, -15, -30, -45, -60, -75]
    bars = [(nm, [100.0 * WB[f"{arm}/el{e:+.0f}"]["above_f_tip_frac"] for e in els], c)
            for (arm, nm), c in zip(ARMS, ("#c62828", "#8e9aab", "#1565c0"))]
    fig, ax = plt.subplots(figsize=(24.0, 7.0))
    x = np.arange(len(els))
    w = 0.26
    for i, (nm, v, c) in enumerate(bars):
        b = ax.bar(x + (i - 1) * w, v, w, color=c, label=nm)
        ax.bar_label(b, fmt="%.1f", fontsize=17, padding=2)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{e:+.0f}" + chr(176) for e in els], fontsize=19)
    ax.set_xlabel("angle the radar looks down from level", fontsize=19, labelpad=10)
    ax.set_ylabel("share of the motion that lands\nabove the blade ceiling  [%]",
                  fontsize=19)
    ax.set_ylim(0, 108)
    ax.tick_params(axis="y", labelsize=17)
    ax.grid(alpha=0.25, axis="y")
    ax.set_axisbelow(True)
    # ⚠범례를 축 **안**에 두면 +0 도 막대와 −75 도 막대 둘 다에 걸린다(양 끝이 다 높다).
    #   축 밖 위쪽에 가로로 눕혀 데이터와 겹칠 여지를 없앤다.
    ax.legend(fontsize=18, ncol=3, loc="lower center", bbox_to_anchor=(0.5, 1.005),
              frameon=False, handlelength=1.6, columnspacing=2.4)
    out = f"{FIG}/deck_leakage.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✅ {out}")


def structure_bars():
    """⭐**구조 검사** — 상한 위 에너지 중 «날개 박자의 정수배» 에 붙은 몫 [%].

    왜 이 잣대인가 (2026-08-14 적대검증 2 차의 결론)
    ----------------------------------------------
    「상한 위 누설 %」는 분모가 **정지 성분을 뺀 AC 전력**이라, 평평한 표본화 잡음만 남은
    팔이 자동으로 높은 점수를 받는다 — AC/DC 가 무너진 것과 같은 병이다. 실제로 물리를 켠
    팔의 96 % 는 그 팔의 AC 전력이 총 수신전력의 0.1 % 뿐이라는 사실을 감춘다.

    이 잣대는 **세기가 아니라 구조**를 잰다. 상한 위 에너지가 f_flash 의 정수배에 몰려 있나,
    아니면 고르게 퍼져 있나. 눈금·정규화에 무관하다.

    ⛔**2026-09-04 정정 — 전 판의 «백색잡음이 13 %, 이상적인 로터가 100 % 다» 는 틀렸다.**
    CLAUDE.md 가 이 함수를 «리듬 몫 정의의 정본» 으로 지목해 두었는데, 정작 이 정본을
    인용하는 `build_md_atlas.py` 가 정반대를 적어 두고 있었다 —
      · **널은 칸마다 다르다.** 빗살폭÷빗살간격(2·hw/f_flash)이라는 **기하 바닥**이고
        기체·자세 수를 탄다: matrice4e ≈ 12.6 · s1000plus ≈ 10.8 · mini5pro ≈ 8.7 %.
        ⛔«13» 하나를 모든 팔에 대면 안 된다.
      · **천장 100 은 도달 불가다.** 실제 로터는 rpm 이 흩어져 선이 번지고 창 반폭이 8 Hz
        로 고정이라 높은 배음일수록 창 밖으로 샌다. 100 을 «완벽한 로터» 로 적지 않는다.
    ⛔**리듬 몫의 크기는 인용하지 않는다**(RETRACTION_LOG R29) — 창 반폭 hw 를 2/8/32 Hz 로만 옮겨도 같은 데이터가 9.9/63.4/90.0 % 로 움직이고, `f_above` 를 함수 기본값(1.5·f_flash)으로 두면 63.4 % 가 98.9 % 가 된다. **순서만** 읽는다.
    """
    ELS6 = [0, -15, -30, -45, -60, -75]
    FT0 = float(ROW[(ARMS[0][0], 0.0)]["f_tip_hz"])

    def share(E, el, hw=8.0):
        n = E.size
        P = np.abs(np.fft.fft((E - E.mean()) * np.hanning(n))) ** 2
        fr = np.fft.fftfreq(n, 1.0 / PRF)
        above = np.abs(fr) >= FT0 * np.cos(np.radians(el))
        k = np.round(np.abs(fr) / FFL)
        return 100.0 * P[above & (np.abs(np.abs(fr) - k * FFL) <= hw)].sum() / P[above].sum()

    rng = np.random.default_rng(0)
    white = rng.normal(size=8192) + 1j * rng.normal(size=8192)
    t = np.arange(8192) / PRF
    ideal = np.sum([np.exp(1j * 2 * np.pi * k * FFL * t) for k in range(1, 40)], axis=0)

    fig, ax = plt.subplots(figsize=(24.0, 7.0))
    x = np.arange(len(ELS6))
    w = 0.26
    for i, ((arm, nm), c) in enumerate(zip(ARMS, ("#c62828", "#8e9aab", "#1565c0"))):
        v = [share(np.asarray(Z[f"{arm}/el{e:+.0f}"], complex), e) for e in ELS6]
        b = ax.bar(x + (i - 1) * w, v, w, color=c, label=nm)
        ax.bar_label(b, fmt="%.0f", fontsize=18, padding=2)
    # ⚠두 기준선의 이름을 그림 안에 직접 쓰면 −75° 막대 라벨과 겹친다 — 범례로 뺀다.
    wn = float(np.mean([share(white, e) for e in ELS6]))
    ax.axhline(100.0, color="#2e7d32", lw=2.0, ls="-", label="a perfect rotor")
    ax.axhline(wn, color="0.35", lw=1.8, ls="--", label="pure noise")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{e:+.0f}" + chr(176) for e in ELS6], fontsize=19)
    ax.set_xlabel("angle the radar looks down from level", fontsize=19, labelpad=10)
    ax.set_ylabel("share of the leftover energy that\nlands on the blade rhythm  [%]",
                  fontsize=19)
    ax.set_ylim(0, 118)
    ax.tick_params(axis="y", labelsize=17)
    ax.grid(alpha=0.25, axis="y")
    ax.set_axisbelow(True)
    ax.legend(fontsize=17, ncol=5, loc="lower center", bbox_to_anchor=(0.5, 1.005),
              frameon=False, handlelength=1.8, columnspacing=2.0)
    out = f"{FIG}/deck_structure.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✅ {out}")


def band_energy_spectrum(pairs=(((0.0, -30.0), "a"), ((-60.0, -90.0), "b"))):
    """⭐**블레이드 대역 전력의 변조 스펙트럼** — 두 각도씩, 넓은/확대 × 3팔/2팔 = 8 장.

    v10(사용자 지시 2026-08-15): 짝을 «잘 맞는 판(−30°·−60°)» 과 «의아한 판(0°·−90°)» 으로
    재편 — pairs 인자로 굽는다(태그 3060 · 0090). v9 짝(a·b)도 재현 가능하게 남긴다.

    사용자 지시(2026-08-15): −90° 를 추가하되 잘 보이게 «0°·−30° 한 장, −60°·−90° 한 장».
    ⚠−90° 는 날개 천장이 0 Hz 라 **블레이드 대역이 정의되지 않는다** — 0° 의 대역
    (0.35~1.0 × 1272.9 Hz)을 빌려 쓰고 패널에 명시한다. 참값이 «선 없음» 인 자리라,
    여기서 빗살이 서면 그것이 곧 인공물이다.
    """
    FT0 = float(ROW[(ARMS[0][0], 0.0)]["f_tip_hz"])

    def modspec(arm, el):
        """대역 전력 g(t) 의 변조 스펙트럼 — el=−90 만 0° 대역을 빌린다."""
        E = np.asarray(Z[f"{arm}/el{el:+.0f}"], complex)
        ft = FT0 * np.cos(np.radians(el))
        borrowed = ft <= 1e-6
        if borrowed:
            ft = FT0
        nper = max(8, int(round(0.45 * PRF / FFL)))
        nfft = 8 * nper
        w = np.hanning(nper + 1)[:-1]
        from numpy.lib.stride_tricks import sliding_window_view
        frm = sliding_window_view(E, nper)[::2]
        S = np.abs(np.fft.fft(frm * w, n=nfft, axis=1)).T / w.sum()
        f = np.fft.fftshift(np.fft.fftfreq(nfft, 1.0 / PRF))
        S = np.fft.fftshift(S, axes=0)
        m = (np.abs(f) >= 0.35 * ft) & (np.abs(f) <= ft)
        g = (S ** 2)[m, :].sum(axis=0)
        fs = PRF / 2.0
        n = g.size
        Y = np.abs(np.fft.rfft((g - g.mean()) * np.hanning(n))) ** 2
        fr = np.fft.rfftfreq(n, 1.0 / fs)
        return fr, Y, borrowed

    cols = ("#c62828", "#8e9aab", "#1565c0")
    for narm, atag in ((3, ""), (2, "2")):
        for lo, hi, vtag in ((100.0, 1000.0, "wide"), (0.0, 420.0, "zoom")):
            for pair, ptag in pairs:
                fig, ax = plt.subplots(1, 2, figsize=(26.0, 9.4), sharey=True)
                for j, el in enumerate(pair):
                    a = ax[j]
                    borrowed = False
                    for arm, nm in ARMS[:narm]:
                        fr, Y, borrowed = modspec(arm, el)
                        m = (fr >= lo) & (fr <= hi)
                        a.plot(fr[m], 10 * np.log10(Y[m] / Y[m].max()),
                               color=cols[[x[0] for x in ARMS].index(arm)],
                               label=SHORT[nm], **LINE_STYLE[nm])
                    for k in range(max(1, int(np.ceil(lo / FFL))), int(hi / FFL) + 1):
                        a.axvline(k * FFL, color="0.35", ls="--", lw=1.2, zorder=1)
                    a.set_xlim(lo, hi)
                    if hi > 500:
                        a.set_xticks(np.arange(200, hi + 1, 200))
                    a.set_ylim(-52, 4)
                    a.set_title(f"{el:+.0f}" + chr(176)
                                + ("   (band borrowed from 0" + chr(176) + ")"
                                   if borrowed else ""), pad=8)
                    a.set_xlabel("modulation rate [Hz]")
                    a.grid(alpha=0.25)
                    a.set_axisbelow(True)
                    if j == 0:
                        a.set_ylabel("line level [dB]")
                        opaque_legend(a, fontsize=17, loc="lower right", framealpha=0.95)
                fig.subplots_adjust(top=0.845, bottom=0.115, left=0.055, right=0.985,
                                    wspace=0.05)
                fig.text(0.5, 0.935, f"dashed lines mark {FFL:.1f} Hz and its "
                                     f"multiples, the rate the blades should make",
                         ha="center", fontsize=19, color="0.35")
                out = f"{FIG}/deck_be{atag}_{vtag}_{ptag}.png"
                fig.savefig(out, dpi=150)
                plt.close(fig)
                print(f"  ✅ {out}")


def maps_dc_removed(els=(0.0, -30.0, -60.0), stem="deck_maps_dc"):
    """⭐**정지 성분을 뺀** 맵 — 가만히 있는 동체가 맵 에너지의 32~66 % 를 먹는다.

    빼기 전에는 세 판 모두 가운데 가로띠가 화면을 지배해 색눈금을 가져간다. 자세 시계열의
    평균(= 정지 성분)을 빼면 **움직이는 것만** 남아 판 사이 차이가 드러난다.
    """
    fig, ax = plt.subplots(len(els), 3, figsize=(27.5, 3.1 * len(els) + 0.5),
                           sharex=True, sharey=True)
    ax = np.atleast_2d(ax)
    n0, nz = int(round(T0 * PRF)), int(round(TSPAN * PRF))
    for r, el in enumerate(els):
        for c, (arm, nm) in enumerate(ARMS):
            a = ax[r, c]
            E = np.asarray(Z[f"{arm}/el{el:+.0f}"], complex)[n0:n0 + nz]
            E = E - E.mean()                      # ⭐정지 성분 제거
            f, t, S, _ = flash_spec(E, PRF, FFL, PERIODS)
            draw(a, t, f, S, float(ROW[(arm, el)]["f_tip_hz"]))
            a.set_ylim(-2000, 2000)
            if r == 0:
                a.set_title(nm, pad=8)
            if c == 0:
                a.set_ylabel(f"{el:+.0f}" + chr(176) + "\nDoppler [Hz]")
            if r == len(els) - 1:
                a.set_xlabel("time [ms]")
    cb = fig.colorbar(ax[0, 0].collections[0], ax=ax, fraction=0.014, pad=0.008)
    cb.set_label("dB below the brightest point in that panel", fontsize=17)
    out = f"{FIG}/{stem}.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✅ {out}")


def mechanism_row():
    """⭐0° 붕괴 기전 해부(덱 v11) — PS 다끔(확산 켬) 한 엔진, 장면을 반으로 갈라 본다.

    전체 장면 / 로터만 / 동체만. **관측**(2026-08-15): 로터만 판은 박자 구조가 뚜렷하고
    동체 에코보다 훨씬 약하며, 전체 장면의 요동은 두 판의 합과 **상관이 0.005** 다 —
    합으로 설명되지 않는다.

    ⛔**2026-09-04 — 여기 있던 판정 문장을 내린다.** ⓐ «리듬 ~90 %» 는 ⛔**리듬 몫의 크기는 인용하지 않는다**(RETRACTION_LOG R29) — 창 반폭 hw 를 2/8/32 Hz 로만 옮겨도 같은 데이터가 9.9/63.4/90.0 % 로 움직이고, `f_above` 를 함수 기본값(1.5·f_flash)으로 두면 63.4 % 가 98.9 % 가 된다. **순서만** 읽는다.
    ⓑ «회전 프롭이 동체 가림을 흔드는 **표본화 깜빡임**이다» 는 이 저장소가 이미 반박해
    뒀다 — `benchmark/az_falsify_judge.py` 가 「박자 몫이 13.1 %(백색 12.5 %)이고 이웃 표본
    상관이 0.010 이라 «프롭이 동체 가림을 흔든다» 는 물리 모습과 맞지 않는다」고 적는다.
    상관 0.005 가 보이는 것은 «합이 아니다» 뿐이고 «무엇인가» 는 아니다.
    ⇒ 남는 요동의 정체는 이 그림이 아니라 따로 판정한다.
    """
    A_FULL = "sionna_p4000000000_r15_n8192_d1"
    A_ROT = "sionna_p4000000000_partsprop_r15_n8192_d1"
    A_BODY = "sionna_p4000000000_partsnoprop_r15_n8192_d1"
    FT0 = float(ROW[(A_FULL, 0.0)]["f_tip_hz"])

    def rhy(E, hw=8.0):
        n = E.size
        P = np.abs(np.fft.fft((E - E.mean()) * np.hanning(n))) ** 2
        fr = np.fft.fftfreq(n, 1.0 / PRF)
        above = np.abs(fr) >= FT0
        k = np.round(np.abs(fr) / FFL)
        return 100.0 * P[above & (np.abs(np.abs(fr) - k * FFL) <= hw)].sum() / P[above].sum()

    Es = {a: np.asarray(Z[f"{a}/el+0"], complex) for a in (A_FULL, A_ROT, A_BODY)}
    acp = {a: float(np.mean(np.abs(E - E.mean()) ** 2)) for a, E in Es.items()}
    lab = {
        A_FULL: f"motion rhythm {rhy(Es[A_FULL]):.0f} %",
        A_ROT: f"motion {10*np.log10(acp[A_ROT]/acp[A_FULL]):.0f} dB weaker, "
               f"rhythm {rhy(Es[A_ROT]):.0f} %",
        A_BODY: "no motion at all",
    }
    n0, nz = int(round(T0 * PRF)), int(round(TSPAN * PRF))
    fig, ax = plt.subplots(1, 3, figsize=(27.5, 4.7), sharex=True, sharey=True)
    #: ⭐패널 제목에 «spinning» 을 명시한다(사용자 지적 2026-08-15) — 세 판 모두 같은
    #  회전 시계열을 돌렸고, 로터만 판의 박자는 그 회전이 만든 것임이 그림에서 읽혀야 한다.
    for c, (arm, nm) in enumerate(((A_FULL, "Full scene"),
                                   (A_ROT, "Propellers only, still spinning"),
                                   (A_BODY, "Body only"))):
        a = ax[c]
        E = Es[arm][n0:n0 + nz]
        f, t, S, _ = flash_spec(E, PRF, FFL, PERIODS)
        draw(a, t, f, S, FT0)
        a.set_ylim(-2000, 2000)
        a.set_title(nm, pad=8)
        a.set_xlabel("time [ms]")
        if c == 0:
            a.set_ylabel("0" + chr(176) + "\nDoppler [Hz]")
        a.text(0.035, 0.945, lab[arm], transform=a.transAxes, color="w",
               fontsize=15.5, va="top",
               bbox=dict(fc="k", alpha=0.55, ec="none", pad=2.2))
    cb = fig.colorbar(ax[0].collections[0], ax=ax, fraction=0.016, pad=0.010)
    cb.set_label("dB below the brightest point in that panel")
    out = f"{FIG}/deck_maps_mech0.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✅ {out}")


def props_band(el=-90.0, stem=None):
    """⭐프로펠러만 · **한 앙각**의 블레이드 대역 전력 변조 스펙트럼 (사용자 지시 2026-08-17).

    덱 v23 이 «0° 말고 −90° 도 보고 싶다» 고 해서 `props_compare` 의 선그림 절만 떼어
    앙각을 인자로 받게 한 것이다. 굽는 것: `deck_be_props3_el<앙각>.png`.

    ⚠**−90° 는 날개 천장이 0 Hz 라 블레이드 대역이 정의되지 않는다.** 다른 −90° 판과
    같은 규약으로 **0° 의 대역을 빌려** 재고, 그 사실을 패널 제목에 적는다. 곡선마다
    자기 최대값 기준이라 **절대량은 이 그림 밖**이다.
    """
    P_ARMS = [
        ("ours_free_r15_n8192", "Our kernel", "#c62828"),
        ("sionna_p4000000000_partsprop_r15_n8192_d1", "Sionna, physics off", "#8e9aab"),
        ("sionna_p4000000000_phys_partsprop_r15_n8192_d1", "Sionna, physics on", "#1565c0"),
    ]
    FT0 = float(ROW[(ARMS[0][0], 0.0)]["f_tip_hz"])          # 0° 천장(빌려 쓰는 대역)
    borrowed = abs(float(ROW[(ARMS[0][0], el)]["f_tip_hz"])) < 1.0
    Es = {a: np.asarray(Z[f"{a}/el{el:+.0f}"], complex) for a, _n, _c in P_ARMS}

    def modspec(E):
        nper = max(8, int(round(0.45 * PRF / FFL)))
        nfft = 8 * nper
        w = np.hanning(nper + 1)[:-1]
        from numpy.lib.stride_tricks import sliding_window_view
        frm = sliding_window_view(E, nper)[::2]
        S = np.abs(np.fft.fft(frm * w, n=nfft, axis=1)).T / w.sum()
        f = np.fft.fftshift(np.fft.fftfreq(nfft, 1.0 / PRF))
        S = np.fft.fftshift(S, axes=0)
        m = (np.abs(f) >= 0.35 * FT0) & (np.abs(f) <= FT0)
        g = (S ** 2)[m, :].sum(axis=0)
        n = g.size
        Y = np.abs(np.fft.rfft((g - g.mean()) * np.hanning(n))) ** 2
        return np.fft.rfftfreq(n, 2.0 / PRF), Y

    fig, ax = plt.subplots(1, 2, figsize=(26.0, 9.0), sharey=True)
    for j, (lo, hi) in enumerate(((100.0, 1000.0), (0.0, 420.0))):
        a = ax[j]
        for arm, nm, col in P_ARMS:
            fr, Y = modspec(Es[arm])
            m = (fr >= lo) & (fr <= hi)
            a.plot(fr[m], 10 * np.log10(Y[m] / Y[m].max()), color=col,
                   label=SHORT.get(nm, nm), **LINE_STYLE[nm])
        for k in range(max(1, int(np.ceil(lo / FFL))), int(hi / FFL) + 1):
            a.axvline(k * FFL, color="0.35", ls="--", lw=1.2, zorder=1)
        a.set_xlim(lo, hi)
        if hi > 500:
            a.set_xticks(np.arange(200, hi + 1, 200))
        a.set_ylim(-52, 4)
        a.set_title("wide, 100 to 1,000 Hz" if j == 0 else "zoom, first three lines",
                    pad=8)
        a.set_xlabel("modulation rate [Hz]")
        a.grid(alpha=0.25)
        a.set_axisbelow(True)
        if j == 0:
            a.set_ylabel("line level [dB]")
            opaque_legend(a, fontsize=17, loc="lower right", framealpha=0.95)
    fig.subplots_adjust(top=0.845, bottom=0.115, left=0.055, right=0.985, wspace=0.05)
    fig.text(0.5, 0.935,
             f"propellers only at {el:+.0f}{chr(176)}, dashed lines mark {FFL:.1f} Hz "
             f"and its multiples, the rate the blades should make"
             + (f"   (band borrowed from 0{chr(176)})" if borrowed else ""),
             ha="center", fontsize=19, color="0.35")
    out = f"{FIG}/{stem or f'deck_be_props3_el{el:+.0f}'}.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  ✅ {out}")


def props_compare():
    """⭐프로펠러만 3엔진 비교(덱 v13, 사용자 지시 2026-08-15) — 0°, 로터는 계속 회전.

    우리 커널(ours_free) / Sionna 물리 끔 / Sionna 물리 켬 — 셋 다 장면에 **프로펠러만**
    남기고 같은 회전 시계열(8,192 자세)을 돌린 판. 굽는 것:
      deck_maps_props3.png   맵 1×3
      deck_be_props3.png     블레이드 대역 전력의 변조 스펙트럼 — 넓은/확대 두 패널 × 3곡선
    """
    P_ARMS = [
        ("ours_free_r15_n8192", "Our kernel", "#c62828"),
        ("sionna_p4000000000_partsprop_r15_n8192_d1", "Sionna, physics off", "#8e9aab"),
        ("sionna_p4000000000_phys_partsprop_r15_n8192_d1", "Sionna, physics on", "#1565c0"),
    ]
    FT0 = float(ROW[(ARMS[0][0], 0.0)]["f_tip_hz"])

    def rhy(E, hw=8.0):
        n = E.size
        P = np.abs(np.fft.fft((E - E.mean()) * np.hanning(n))) ** 2
        fr = np.fft.fftfreq(n, 1.0 / PRF)
        above = np.abs(fr) >= FT0
        k = np.round(np.abs(fr) / FFL)
        return 100.0 * P[above & (np.abs(np.abs(fr) - k * FFL) <= hw)].sum() / P[above].sum()

    Es = {a: np.asarray(Z[f"{a}/el+0"], complex) for a, _n, _c in P_ARMS}
    # ── 맵 1×3 ──
    n0, nz = int(round(T0 * PRF)), int(round(TSPAN * PRF))
    fig, ax = plt.subplots(1, 3, figsize=(27.5, 4.7), sharex=True, sharey=True)
    for c, (arm, nm, _col) in enumerate(P_ARMS):
        a = ax[c]
        E = Es[arm][n0:n0 + nz]
        f, t, S, _ = flash_spec(E, PRF, FFL, PERIODS)
        draw(a, t, f, S, FT0)
        a.set_ylim(-2000, 2000)
        a.set_title(nm, pad=8)
        a.set_xlabel("time [ms]")
        if c == 0:
            a.set_ylabel("0" + chr(176) + "\nDoppler [Hz]")
        a.text(0.035, 0.945, f"rhythm {rhy(Es[arm]):.0f} %", transform=a.transAxes,
               color="w", fontsize=15.5, va="top",
               bbox=dict(fc="k", alpha=0.55, ec="none", pad=2.2))
    fig.subplots_adjust(top=0.82, bottom=0.16, left=0.055, right=0.94, wspace=0.08)
    fig.text(0.5, 0.93, "propellers only and still spinning, every engine at 0"
             + chr(176) + ", each panel scaled to its own peak",
             ha="center", fontsize=19, color="0.35")
    cax = fig.add_axes([0.948, 0.16, 0.008, 0.66])
    cb = fig.colorbar(ax[0].collections[0], cax=cax)
    cb.set_label("dB below the brightest point in that panel", fontsize=16)
    out = f"{FIG}/deck_maps_props3.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  ✅ {out}")

    # ── 대역 전력의 변조 스펙트럼 — 넓은/확대 ──
    def modspec(E):
        nper = max(8, int(round(0.45 * PRF / FFL)))
        nfft = 8 * nper
        w = np.hanning(nper + 1)[:-1]
        from numpy.lib.stride_tricks import sliding_window_view
        frm = sliding_window_view(E, nper)[::2]
        S = np.abs(np.fft.fft(frm * w, n=nfft, axis=1)).T / w.sum()
        f = np.fft.fftshift(np.fft.fftfreq(nfft, 1.0 / PRF))
        S = np.fft.fftshift(S, axes=0)
        m = (np.abs(f) >= 0.35 * FT0) & (np.abs(f) <= FT0)
        g = (S ** 2)[m, :].sum(axis=0)
        n = g.size
        Y = np.abs(np.fft.rfft((g - g.mean()) * np.hanning(n))) ** 2
        fr = np.fft.rfftfreq(n, 2.0 / PRF)
        return fr, Y

    fig, ax = plt.subplots(1, 2, figsize=(26.0, 9.0), sharey=True)
    for j, (lo, hi) in enumerate(((100.0, 1000.0), (0.0, 420.0))):
        a = ax[j]
        for arm, nm, col in P_ARMS:
            fr, Y = modspec(Es[arm])
            m = (fr >= lo) & (fr <= hi)
            a.plot(fr[m], 10 * np.log10(Y[m] / Y[m].max()), color=col,
                   label=SHORT.get(nm, nm), **LINE_STYLE[nm])
        for k in range(max(1, int(np.ceil(lo / FFL))), int(hi / FFL) + 1):
            a.axvline(k * FFL, color="0.35", ls="--", lw=1.2, zorder=1)
        a.set_xlim(lo, hi)
        if hi > 500:
            a.set_xticks(np.arange(200, hi + 1, 200))
        a.set_ylim(-52, 4)
        a.set_title("wide, 100 to 1,000 Hz" if j == 0 else "zoom, first three lines",
                    pad=8)
        a.set_xlabel("modulation rate [Hz]")
        a.grid(alpha=0.25)
        a.set_axisbelow(True)
        if j == 0:
            a.set_ylabel("line level [dB]")
            opaque_legend(a, fontsize=17, loc="lower right", framealpha=0.95)
    fig.subplots_adjust(top=0.845, bottom=0.115, left=0.055, right=0.985, wspace=0.05)
    fig.text(0.5, 0.935, f"propellers only at 0{chr(176)}, dashed lines mark "
                         f"{FFL:.1f} Hz and its multiples, the rate the blades "
                         f"should make", ha="center", fontsize=19, color="0.35")
    out = f"{FIG}/deck_be_props3.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  ✅ {out}")


def props_grid():
    """⭐프로펠러만 × 네 앙각 전수(덱 v14, 사용자 지시 2026-08-15) — 3엔진 × 4앙각 격자.

    ours_free 는 원장에 7앙각 완비, Sionna 두 팔은 0°(v13)에 −30/−60/−90 를 큐로 추가한 판.
    패널 구석에 리듬 몫[%] — 상한은 각 앙각의 f_tip(−90° 는 0 이라 전체 AC 몫으로 퇴화, 각주).
    """
    P_ARMS = [
        ("ours_free_r15_n8192", "Our kernel"),
        ("sionna_p4000000000_partsprop_r15_n8192_d1", "Physics off"),
        ("sionna_p4000000000_phys_partsprop_r15_n8192_d1", "Physics on"),
    ]
    ELS4 = [0.0, -30.0, -60.0, -90.0]
    FT0 = float(ROW[(ARMS[0][0], 0.0)]["f_tip_hz"])

    def rhy(E, el, hw=8.0):
        n = E.size
        P = np.abs(np.fft.fft((E - E.mean()) * np.hanning(n))) ** 2
        fr = np.fft.fftfreq(n, 1.0 / PRF)
        above = np.abs(fr) >= FT0 * np.cos(np.radians(el))
        k = np.round(np.abs(fr) / FFL)
        return 100.0 * P[above & (np.abs(np.abs(fr) - k * FFL) <= hw)].sum() / P[above].sum()

    n0, nz = int(round(T0 * PRF)), int(round(TSPAN * PRF))
    fig, ax = plt.subplots(3, 4, figsize=(26.0, 10.8), sharex=True, sharey=True)
    for r, (arm, nm) in enumerate(P_ARMS):
        for c, el in enumerate(ELS4):
            a = ax[r, c]
            E = np.asarray(Z[f"{arm}/el{el:+.0f}"], complex)
            f, t, S, _ = flash_spec(E[n0:n0 + nz], PRF, FFL, PERIODS)
            draw(a, t, f, S, FT0 * np.cos(np.radians(el)))
            a.set_ylim(-2000, 2000)
            if r == 0:
                a.set_title(f"{el:+.0f}" + chr(176), pad=8)
            if c == 0:
                a.set_ylabel(f"{nm}\nDoppler [Hz]")
            if r == 2:
                a.set_xlabel("time [ms]")
            a.text(0.035, 0.94, f"{rhy(E, el):.0f} %", transform=a.transAxes,
                   color="w", fontsize=15, va="top",
                   bbox=dict(fc="k", alpha=0.55, ec="none", pad=2.0))
    fig.subplots_adjust(top=0.885, bottom=0.085, left=0.075, right=0.950,
                        hspace=0.20, wspace=0.10)
    fig.text(0.5, 0.955, "propellers only and still spinning, corner number is the "
                         "rhythm share, each panel scaled to its own peak",
             ha="center", fontsize=19, color="0.35")
    cax = fig.add_axes([0.958, 0.085, 0.008, 0.80])
    cb = fig.colorbar(ax[0, 0].collections[0], cax=cax)
    cb.set_label("dB below the brightest point in that panel", fontsize=16)
    out = f"{FIG}/deck_maps_props_grid.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  ✅ {out}")


if __name__ == "__main__":
    print("═══ 덱 맵 ═══")
    band_energy_spectrum()
    maps_dc_removed()
    structure_bars()
    leakage_bars()
    full_grid()
    pair((0.0, -60.0), "deck_maps_pair")
    pair((-90.0,), "deck_maps_nadir")
    # ── v10 짝(사용자 지시 2026-08-15): 잘 맞는 판 −30°·−60° / 의아한 판 0°·−90° ──
    band_energy_spectrum(pairs=(((-30.0, -60.0), "3060"), ((0.0, -90.0), "0090")))
    maps_dc_removed((-30.0, -60.0), stem="deck_maps_dc3060")
    maps_dc_removed((0.0, -90.0), stem="deck_maps_dc0090")
    pair((-30.0, -60.0), "deck_maps_pair3060")
    pair((0.0, -90.0), "deck_maps_pair0090")
    mechanism_row()
    props_compare()
    props_grid()
