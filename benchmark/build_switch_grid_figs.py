# -*- coding: utf-8 -*-
"""
build_switch_grid_figs.py — **물리 스위치 7 조합**의 STFT 맵·대역 에너지 그림과 원장.

사용자 지시(2026-08-15): 「물리 스위치 7 조합 결과 STFT 마이크로도플러 맵을 토대로 다음
작업을 정한다 — 맵 결과물들과 blade band energy 를 다 실어서 읽기 편하게, 팀미팅 때
보이는 분석 방식으로」.

판: matrice4e · 3.5 GHz · 15 m · 앙각 −30° · 자세 8,192 · 광선 40 억 발 · 깊이 1 ·
확산반사 켬 — 전부 같고, 갈리는 축은 굴절 R · 회절 D · 모서리회절 E 세 비트뿐이다.
(⚠101(굴절+모서리)은 소스 구조상 100 과 동일해 계산하지 않았다 — 모서리회절 후보 생성이
`if diffraction_enabled:` 안에 있다. sb_candidate_generator:338)

굽는 것
    outputs/switch_grid.json                   조합별 수치(보고서가 인용)
    outputs/figures/swgrid_maps.png            STFT 맵 — 우리 커널 + 7 조합 (2×4)
    outputs/figures/swgrid_maps_dc.png         같은 판, 정지 성분 제거
    outputs/figures/swgrid_be_wide.png         대역 에너지 100~1,000 Hz (조합당 패널)
    outputs/figures/swgrid_be_zoom.png         대역 에너지 0~420 Hz

    PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/build_switch_grid_figs.py
"""
from __future__ import annotations

import glob
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
SHD = os.path.join(ROOT, "outputs", "elev_sweep_shards")
#: ⭐앙각은 환경변수로 연다(2026-08-27) — 다섯 팔 매트릭스가 el 0·−30·−60·−90 넷을 쓴다.
#  기본 −30 은 정본 산출 이름을 그대로 쓰고, 다른 앙각은 접미사를 붙여 덮어쓰지 않는다.
EL = float(os.environ.get("SWGRID_EL", "-30.0"))
SUF = "" if abs(EL + 30.0) < 1e-9 else f"_el{EL:+.0f}"

TJ = json.load(open(f"{ROOT}/outputs/report07_three_engines.json"))["_meta"]
PRF = float(TJ["prf_hz"])
FFL = float(TJ["f_flash_hz"])
FT30 = float(TJ["f_tip_hz"]) / np.cos(np.radians(-15.0)) * np.cos(np.radians(EL))
PERIODS = auto_periods(PRF, FFL)

#: 표시 순서 — 왼쪽 위가 기준(우리 커널), 그 다음 «끈 것부터 켠 것 순».
#  이름은 청중용(스위치 이니셜이 아니라 말로).
ARMS = [
    ("ours_r15_n8192_mfixbatteryi5_blperairframe",                              "Our kernel"),
    ("sionna_p4000000000_swR0D0E0F1_r15_n8192_mfixbatteryi5_blperairframe_d2",  "all off (diffuse only)"),
    ("sionna_p4000000000_swR1D0E0F1_r15_n8192_mfixbatteryi5_blperairframe_d2",  "refraction"),
    ("sionna_p4000000000_swR0D1E1F1_r15_n8192_mfixbatteryi5_blperairframe_d2",  "diffraction"),
    ("sionna_p4000000000_swR1D1E1F1_r15_n8192_mfixbatteryi5_blperairframe_d2",  "refraction + diffraction"),
]
T0, TSPAN = 0.020, 0.060

plt.rcParams.update({
    "font.size": 19, "axes.titlesize": 21, "axes.labelsize": 19,
    "xtick.labelsize": 16, "ytick.labelsize": 16,
    "figure.facecolor": "white", "savefig.facecolor": "white",
})


def load(arm):
    """샤드 16 장 → 자세 8,192 시계열. 빠진 자세가 있으면 그 수를 함께 돌려준다."""
    fs = sorted(glob.glob(f"{SHD}/{arm}_el{EL:+.0f}_*.npz"))
    E = seen = None
    for f in fs:
        d = np.load(f)
        n = int(np.asarray(d["meta"], float)[3])
        if E is None:
            E = np.zeros(n, complex)
            seen = np.zeros(n, bool)
        ii = d["idx"].astype(int)
        E[ii] = d["E"]
        seen[ii] = True
    if E is None:
        raise SystemExit(f"⛔ 샤드가 없다: {arm}")
    return E, int((~seen).sum())


def modspec(E):
    """블레이드 대역(0.35~1.0 × f_tip(−30°)) 전력의 변조 스펙트럼 — 덱과 같은 규약."""
    nper = max(8, int(round(0.45 * PRF / FFL)))
    nfft = 8 * nper
    w = np.hanning(nper + 1)[:-1]
    from numpy.lib.stride_tricks import sliding_window_view
    frm = sliding_window_view(E, nper)[::2]
    S = np.abs(np.fft.fft(frm * w, n=nfft, axis=1)).T / w.sum()
    f = np.fft.fftshift(np.fft.fftfreq(nfft, 1.0 / PRF))
    S = np.fft.fftshift(S, axes=0)
    m = (np.abs(f) >= 0.35 * FT30) & (np.abs(f) <= FT30)
    g = (S ** 2)[m, :].sum(axis=0)
    n = g.size
    Y = np.abs(np.fft.rfft((g - g.mean()) * np.hanning(n))) ** 2
    fr = np.fft.rfftfreq(n, 1.0 / (PRF / 2.0))
    return fr, Y


def rhythm_share(E, hw=8.0):
    """상한 위 에너지 중 날개 박자 정수배에 붙은 몫 [%] — 살아남은 구조 잣대."""
    n = E.size
    P = np.abs(np.fft.fft((E - E.mean()) * np.hanning(n))) ** 2
    fr = np.fft.fftfreq(n, 1.0 / PRF)
    above = np.abs(fr) >= FT30
    k = np.round(np.abs(fr) / FFL)
    on = np.abs(np.abs(fr) - k * FFL) <= hw
    return float(100.0 * P[above & on].sum() / P[above].sum())


def maps(data, drop_dc, stem, shared=False):
    """스펙트로그램 격자.

    shared=False (기본) — 패널마다 **자기 최대값**으로 0 dB. 무늬 비교용이지만
                          ⚠팔 사이 **레벨 차이가 그림에서 사라진다**.
    shared=True  — ⭐**전 패널 공통 기준**(모든 팔의 최대값). 찍힌 그대로의 세기가
                   보인다. 색역은 가장 약한 팔까지 담기게 자동으로 넓힌다.
    """
    n0, nz = int(round(T0 * PRF)), int(round(TSPAN * PRF))
    # ⭐한 번에 다 계산해 두고(공통 기준을 알아야 그릴 수 있다) 그린다.
    specs = []
    for arm, nm in ARMS:
        E = data[arm][n0:n0 + nz]
        if drop_dc:
            E = E - E.mean()
        f, t, S, _ = flash_spec(E, PRF, FFL, PERIODS)
        specs.append((nm, f, t, S))
    ref = vmin = None
    if shared:
        ref = max(float(S.max()) for _, _, _, S in specs)
        peaks = [20 * np.log10(float(S.max()) / (ref + 1e-30) + 1e-30)
                 for _, _, _, S in specs]
        vmin = float(np.floor((min(peaks) - 12.0) / 10.0) * 10.0)
    nc = len(ARMS) if len(ARMS) <= 5 else 4
    nr = int(np.ceil(len(ARMS) / nc))
    fig, ax = plt.subplots(nr, nc, figsize=(5.4 * nc, 4.8 * nr + 0.9),
                           sharex=True, sharey=True, squeeze=False)
    for i, (nm, f, t, S) in enumerate(specs):
        a = ax[i // nc, i % nc]
        draw(a, t, f, S, FT30, ref=ref, vmin=vmin)
        a.set_ylim(-2000, 2000)
        a.set_title(nm, pad=7)
        if i % nc == 0:
            a.set_ylabel("Doppler [Hz]")
        if i // nc == nr - 1:
            a.set_xlabel("time [ms]")
    for j in range(len(specs), nr * nc):        # 남는 칸은 지운다
        ax[j // nc, j % nc].axis("off")
    fig.subplots_adjust(top=0.865, bottom=0.10, left=0.055, right=0.945,
                        hspace=0.22, wspace=0.08)
    fig.text(0.5, 0.945, ("body echo removed, " if drop_dc else "")
             + "every run looking up from 30" + chr(176) + " below the drone, "
             + ("one shared scale " + chr(8212) + " panel brightness is the real level"
                if shared else "each panel scaled to its own peak"),
             ha="center", fontsize=19, color="0.35")
    cax = fig.add_axes([0.953, 0.10, 0.008, 0.765])
    cb = fig.colorbar(ax[0, 0].collections[0], cax=cax)
    cb.set_label("dB below the brightest point across all panels" if shared
                 else "dB below the brightest point in that panel", fontsize=16)
    out = f"{FIG}/{stem}{SUF}.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  ✅ {out}")


def band(data, lo, hi, stem):
    """조합당 패널 — 7 곡선을 한 축에 겹치면 안 읽힌다(덱에서 실측). 우리 커널을 옅게 깔아
    기준으로 삼고, 각 패널에 그 조합 하나만 진하게 얹는다."""
    fr0, Y0 = modspec(data[ARMS[0][0]])
    m0 = (fr0 >= lo) & (fr0 <= hi)
    ref_db = 10 * np.log10(Y0[m0] / Y0[m0].max())
    fig, ax = plt.subplots(2, 4, figsize=(27.0, 9.6), sharex=True, sharey=True)
    for i, (arm, nm) in enumerate(ARMS):
        a = ax[i // 4, i % 4]
        if i:
            a.plot(fr0[m0], ref_db, color="#c62828", lw=1.2, alpha=0.35,
                   label="Our kernel")
        fr, Y = modspec(data[arm])
        m = (fr >= lo) & (fr <= hi)
        a.plot(fr[m], 10 * np.log10(Y[m] / Y[m].max()),
               color="#c62828" if not i else "#1565c0", lw=1.8, label=nm)
        for k in range(max(1, int(np.ceil(lo / FFL))), int(hi / FFL) + 1):
            a.axvline(k * FFL, color="0.35", ls="--", lw=1.0, zorder=1)
        a.set_xlim(lo, hi)
        if hi > 500:
            a.set_xticks(np.arange(200, hi + 1, 200))
        a.set_ylim(-52, 4)
        a.set_title(nm, pad=7)
        a.grid(alpha=0.25)
        a.set_axisbelow(True)
        if i % 4 == 0:
            a.set_ylabel("line level [dB]")
        if i // 4 == 1:
            a.set_xlabel("modulation rate [Hz]")
        if i == 1:
            a.legend(fontsize=13, loc="lower right", framealpha=0.95)
    fig.subplots_adjust(top=0.865, bottom=0.10, left=0.055, right=0.985,
                        hspace=0.22, wspace=0.06)
    fig.text(0.5, 0.945, "blade band power over time turned into a spectrum, "
                         f"dashed lines mark {FFL:.1f} Hz and its multiples, "
                         "the faint red curve repeats our kernel for reference",
             ha="center", fontsize=18, color="0.35")
    out = f"{FIG}/{stem}{SUF}.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  ✅ {out}")


if __name__ == "__main__":
    print("═══ 스위치 격자 그림 ═══")
    data, doc = {}, {}
    for arm, nm in ARMS:
        E, miss = load(arm)
        data[arm] = E
        fr, Y = modspec(E)
        df = fr[1] - fr[0]
        floor = float(np.median(Y[(fr > 20) & (fr < 500)]))
        b = int(round(FFL / df))
        seg = Y[max(0, b - 3):b + 4]
        pk = max(0, b - 6) + int(np.argmax(Y[max(0, b - 6):b + 7]))
        doc[nm] = dict(
            arm=arm, n_missing=miss,
            rhythm_share_pct=round(rhythm_share(E), 1),
            h1_over_floor_db=round(float(10 * np.log10(seg.max() / floor)), 2),
            h1_peak_hz=round(float(fr[pk]), 2))
        print(f"  {nm:26s} 결측 {miss:4d} · 리듬 {doc[nm]['rhythm_share_pct']:5.1f} % · "
              f"1차선 {doc[nm]['h1_over_floor_db']:6.1f} dB @ {doc[nm]['h1_peak_hz']:.1f} Hz")

    # ⭐⭐2026-08-18: 결측 자세를 **말없이 0 으로 두고 그리지 않는다.**
    #   load() 는 빠진 자세를 0 으로 남긴다. 샤드는 성큼성큼(stride) 나뉘므로 한 장이 없으면
    #   0 이 **규칙적인 간격**으로 박히고, 그것은 시계열에 주기 창을 곱한 것과 같아
    #   스펙트럼에 없는 구조를 만든다. 실제로 그런 그림이 나갔다 — «굴절+회절» 팔이
    #   512 자세(샤드 1 장, 간격 16) 결측인 채 그려져 리듬 몫이 12.33 → 13.2 % 로 부풀고
    #   1 차 선이 9.7 dB 로 눌렸다(docs/SWITCH_GRID_HOLE_0818.md).
    holed = {nm: d["n_missing"] for nm, d in doc.items() if d["n_missing"]}
    if holed and os.environ.get("ALLOW_MISSING_POSES") != "1":
        print("\n⛔ 결측 자세가 있는 팔이 있다 — 그림을 만들지 않는다:")
        for nm, k in holed.items():
            print(f"     {nm}: {k} 자세 (0 으로 남아 주기 무늬를 만든다)")
        print("   샤드를 마저 돌리고 다시 실행한다. "
              "그래도 강행하려면 ALLOW_MISSING_POSES=1 을 준다(그림에 꼬리표가 필요하다).")
        raise SystemExit(1)

    maps(data, False, "swgrid_maps")
    maps(data, True, "swgrid_maps_dc")
    # ⭐찍힌 그대로의 세기가 보이는 판 (2026-08-27 추가) — 팔 사이 레벨 차이가 살아 있다.
    maps(data, False, "swgrid_maps_shared", shared=True)
    maps(data, True, "swgrid_maps_dc_shared", shared=True)
    band(data, 100.0, 1000.0, "swgrid_be_wide")
    band(data, 0.0, 420.0, "swgrid_be_zoom")

    out = {"_meta": {
        "generator": "benchmark/build_switch_grid_figs.py",
        "purpose_ko": "물리 스위치 7 조합 + 우리 커널, 앙각 −30° 한 자리 비교",
        "setup_ko": "matrice4e · 3.5 GHz · 15 m · 자세 8192 · 광선 4e9 · 깊이 1 · 확산 켬",
        "excluded_ko": "101(굴절+모서리)은 소스 구조상 100 과 동일해 계산하지 않았다 — "
                       "모서리회절 후보 생성이 회절 스위치 안에 있다"
                       "(sb_candidate_generator.py:338)",
        "rhythm_ko": "상한 위 에너지 중 f_flash 정수배 ±8 Hz 에 붙은 몫[%] — "
                     "백색잡음 13, 이상 로터 100",
        "h1_ko": "블레이드 대역 전력 변조 스펙트럼의 1 차 선 — 국소 바닥 위 dB 와 봉우리 위치",
        "el_deg": EL, "f_tip_hz": round(FT30, 1), "f_flash_hz": FFL,
    }, "cells": doc}
    p = f"{ROOT}/outputs/switch_grid{SUF}.json"
    json.dump(out, open(p, "w"), ensure_ascii=False, indent=1)
    print(f"  ✅ {p}")
