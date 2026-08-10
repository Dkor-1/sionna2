# -*- coding: utf-8 -*-
"""
build_deck0811_range_figs.py — 덱 개편용 그림 셋 (거리별 STFT · 밴드 에너지 · 시드 두 판).

사용자 지시(2026-08-10)
> 7페이지: 거리별로 STFT 실제로 뽑아낸 결과(**직접 거리별로 뽑아내도록**).
>          우리 커널·path solver 비교, 3 m · 15 m · 40 m. 우측 그림은 삭제.
> 8페이지: 그 결과를 토대로 **밴드 에너지** 그리기.
> 9페이지: 40 m 에서 path solver 를 **시드 두 개**로, 밴드 에너지도.

⭐«직접 거리별로» 를 지키려고 우리 커널도 거리마다 다시 계산했다 —
  `benchmark/deck_ours_by_range.py` 가 구면파 조명(`sbr_field(..., range_m=R)`)으로 낸다.
  그전에는 평면파(원거리장)라 거리 입력이 아예 없어 한 배열을 재사용했다.

읽는 것
  outputs/deck_ours_by_range.npz           우리 커널, 거리별(구면파)
  outputs/report07_three_engine_ranges.npz Sionna 3 m · 15 m
  outputs/report07_range40.npz             Sionna 40 m 시드 2개
쓰는 것
  outputs/figures/deck0811_maps_ranges.{png,pdf}
  outputs/figures/deck0811_band_ranges.{png,pdf}
  outputs/figures/deck0811_seed40.{png,pdf}
  outputs/deck0811_range_figs.json
"""
from __future__ import annotations

import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from md_mapstyle import auto_periods, draw, flash_spec                # noqa: E402

FIG = f"{ROOT}/outputs/figures"
TJ = json.load(open(f"{ROOT}/outputs/report07_three_engines.json"))["_meta"]
PRF, FFL, FTIP = TJ["prf_hz"], TJ["f_flash_hz"], TJ["f_tip_hz"]
NAME = TJ["name"]
PERIODS = auto_periods(PRF, FFL)

BAND_LO, BAND_HI = 0.35, 1.00                     # 날개끝 대역 (f_tip 배수)
LO_HZ, HI_HZ = BAND_LO * FTIP, BAND_HI * FTIP
ZOOM_MS, N0 = 60.0, 500
NZ = int(round(ZOOM_MS * 1e-3 * PRF))

C_S, C_O = "#c2570a", "#1f5fa8"
FS = 13
plt.rcParams.update({"font.size": FS, "axes.labelsize": FS, "axes.titlesize": FS,
                     "xtick.labelsize": FS - 2, "ytick.labelsize": FS - 2,
                     "legend.fontsize": FS - 2.5, "figure.dpi": 200,
                     "savefig.dpi": 200, "font.family": "DejaVu Sans"})

OZ = np.load(f"{ROOT}/outputs/deck_ours_by_range.npz")
RZ = np.load(f"{ROOT}/outputs/report07_three_engine_ranges.npz")
SZ = np.load(f"{ROOT}/outputs/report07_range40.npz")

SERIES = {
    3.0:  ("Sionna PathSolver", RZ["R3/E"],  "Ours (SBR + PO)", OZ["R3/E"]),
    15.0: ("Sionna PathSolver", RZ["R15/E"], "Ours (SBR + PO)", OZ["R15/E"]),
    40.0: ("Sionna PathSolver", SZ["S1/E"],  "Ours (SBR + PO)", OZ["R40/E"]),
}


def band_energy(E):
    """날개끝 대역 에너지의 **변조율 스펙트럼** — 대역 전력을 시간축으로 보고 다시 FFT."""
    f, t, S, _ = flash_spec(np.asarray(E, complex), PRF, FFL, PERIODS)
    b = (np.abs(f) >= LO_HZ) & (np.abs(f) <= HI_HZ)
    g = (S[b, :] ** 2).sum(axis=0)
    g = g - g.mean()
    dt = float(t[1] - t[0]); m = len(g)
    A = np.abs(np.fft.rfft(g * np.hanning(m), n=64 * m))
    fr = np.fft.rfftfreq(64 * m, dt)
    A = A / A.max()
    s = fr <= 420
    sel = (fr >= 40) & (fr <= 400)
    i0 = int(np.where(sel)[0][0]); i = int(np.argmax(A[sel])) + i0
    y0, y1, y2 = A[i - 1], A[i], A[i + 1]
    den = y0 - 2 * y1 + y2
    pk = fr[i] + (0.5 * (y0 - y2) / den if den else 0.0) * (fr[1] - fr[0])
    return fr[s], A[s], float(pk)


def _map(ax, E):
    seg = np.asarray(E, complex)[N0:N0 + NZ]
    f, t, S, _ = flash_spec(seg, PRF, FFL, PERIODS)
    return draw(ax, t + N0 / PRF, f, S, FTIP)


# ═══ 그림 B — 거리별 맵 3×2 ══════════════════════════════════════════════════
def build_maps():
    fig = plt.figure(figsize=(12.4, 8.6))
    gs = fig.add_gridspec(3, 3, width_ratios=[1, 1, 0.038], wspace=0.10,
                          hspace=0.30, left=0.085, right=0.945, top=0.905, bottom=0.075)
    m = None
    for r, R in enumerate((3.0, 15.0, 40.0)):
        ns, Es, no, Eo = SERIES[R]
        for c, (E, nm, col) in enumerate(((Es, ns, C_S), (Eo, no, C_O))):
            ax = fig.add_subplot(gs[r, c])
            m = _map(ax, E)
            if c == 1:
                for sp in ax.spines.values():
                    sp.set_color(C_O); sp.set_linewidth(2.0)
            if r == 0:
                ax.set_title(nm, color=col, fontweight="bold", pad=7)
            if c == 0:
                ax.set_ylabel(f"R = {R:.0f} m\nDoppler [Hz]")
            else:
                plt.setp(ax.get_yticklabels(), visible=False)
            if r == 2:
                ax.set_xlabel("Time [ms]")
            else:
                plt.setp(ax.get_xticklabels(), visible=False)
    cb = fig.colorbar(m, cax=fig.add_subplot(gs[:, 2]))
    cb.set_label("Each map to its own peak [dB]", fontsize=FS - 1)
    fig.suptitle(f"{NAME}, hovering, {TJ['fc_hz']/1e9:.1f} GHz. "
                 f"Each range solved separately, same {ZOOM_MS:.0f} ms window.",
                 fontsize=FS + 1, y=0.965)
    for e in ("png", "pdf"):
        fig.savefig(f"{FIG}/deck0811_maps_ranges.{e}", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  ✅ deck0811_maps_ranges")


# ═══ 그림 C — 거리별 밴드 에너지 ═════════════════════════════════════════════
def build_band():
    out = {}
    fig, axes = plt.subplots(1, 3, figsize=(14.6, 4.5), sharey=True)
    for ax, R in zip(axes, (3.0, 15.0, 40.0)):
        ns, Es, no, Eo = SERIES[R]
        for E, nm, col in ((Es, ns, C_S), (Eo, no, C_O)):
            fr, A, pk = band_energy(E)
            ax.plot(fr, 20 * np.log10(A + 1e-6), color=col, lw=2.0,
                    label=f"{nm}   {pk:.1f} Hz")
            out[f"{R:.0f}/{nm}"] = pk
        for h in (1, 2, 3):
            ax.axvline(h * FFL, color="0.25", ls="--",
                       lw=1.4 if h == 1 else 0.9, zorder=0)
        ax.set_title(f"R = {R:.0f} m")
        ax.set_xlabel("Modulation rate [Hz]")
        ax.set_xlim(0, 420); ax.set_ylim(-46, 8)
        ax.grid(alpha=0.22)
        ax.legend(loc="upper right", fontsize=FS - 3.5, framealpha=0.92)
    axes[0].set_ylabel("Line level [dB]")
    fig.suptitle(f"Energy in the blade tip band ({LO_HZ:.0f} to {HI_HZ:.0f} Hz), "
                 f"how fast it rises and falls.   Dashed lines, kinematic prediction "
                 f"{FFL:.1f} Hz and its harmonics.", fontsize=FS + 0.5, y=1.02)
    fig.tight_layout()
    for e in ("png", "pdf"):
        fig.savefig(f"{FIG}/deck0811_band_ranges.{e}", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  ✅ deck0811_band_ranges")
    return out


# ═══ 그림 D — 40 m, 시드 두 판 ═══════════════════════════════════════════════
def build_seed40():
    runs = [("run 1", SZ["S1/E"]), ("run 2", SZ["S2/E"])]
    fig = plt.figure(figsize=(13.6, 5.2))
    gs = fig.add_gridspec(1, 4, width_ratios=[1, 1, 0.038, 1.25],
                          wspace=0.16, left=0.055, right=0.975, top=0.845, bottom=0.155)
    m = None
    for c, (nm, E) in enumerate(runs):
        ax = fig.add_subplot(gs[0, c])
        m = _map(ax, E)
        ax.set_title(f"Sionna PathSolver, {nm}", color=C_S, fontweight="bold", pad=7)
        ax.set_xlabel("Time [ms]")
        if c == 0:
            ax.set_ylabel("Doppler [Hz]")
        else:
            plt.setp(ax.get_yticklabels(), visible=False)
    cb = fig.colorbar(m, cax=fig.add_subplot(gs[0, 2]))
    cb.set_label("Each map to its own peak [dB]", fontsize=FS - 1)

    ax = fig.add_subplot(gs[0, 3])
    peaks = {}
    for (nm, E), ls in zip(runs, ("-", "--")):
        fr, A, pk = band_energy(E)
        ax.plot(fr, 20 * np.log10(A + 1e-6), color=C_S, lw=2.0, ls=ls,
                label=f"{nm}   {pk:.1f} Hz")
        peaks[nm] = pk
    for h in (1, 2, 3):
        ax.axvline(h * FFL, color="0.25", ls="--", lw=1.4 if h == 1 else 0.9, zorder=0)
    ax.set_xlim(0, 420); ax.set_ylim(-46, 8); ax.grid(alpha=0.22)
    ax.set_xlabel("Modulation rate [Hz]"); ax.set_ylabel("Line level [dB]")
    ax.set_title(f"Blade tip band energy ({LO_HZ:.0f} to {HI_HZ:.0f} Hz)", pad=7)
    ax.legend(loc="upper right", fontsize=FS - 3, framealpha=0.92)
    fig.suptitle(f"{NAME} at 40 m. The same computation run twice, "
                 f"only the random start differs.   Prediction {FFL:.1f} Hz.",
                 fontsize=FS + 1, y=0.955)
    for e in ("png", "pdf"):
        fig.savefig(f"{FIG}/deck0811_seed40.{e}", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  ✅ deck0811_seed40")
    return peaks


if __name__ == "__main__":
    build_maps()
    band = build_band()
    seed = build_seed40()
    json.dump({"_meta": {
        "generator": "benchmark/build_deck0811_range_figs.py",
        "band_hz": [LO_HZ, HI_HZ], "band_ftip_frac": [BAND_LO, BAND_HI],
        "prediction_hz": FFL, "zoom_ms": ZOOM_MS,
        "ours_illumination": "spherical wave, computed per range",
        "sionna_40m_seeds": ["run 1", "run 2"]},
        "band_peaks": band, "seed40_peaks": seed},
        open(f"{ROOT}/outputs/deck0811_range_figs.json", "w"),
        ensure_ascii=False, indent=1)
    print(f"\n✅ outputs/deck0811_range_figs.json")
    print(f"   밴드 {LO_HZ:.0f}~{HI_HZ:.0f} Hz · 예측 {FFL:.1f} Hz")
    for k, v in band.items():
        print(f"   {k:<38} {v:7.2f} Hz")
    for k, v in seed.items():
        print(f"   40 m {k:<33} {v:7.2f} Hz")
