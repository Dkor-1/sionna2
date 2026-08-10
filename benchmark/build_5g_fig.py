# -*- coding: utf-8 -*-
"""
build_5g_fig.py — 같은 채널에 5G 파형을 태운 네 팔을 나란히.

⭐ 이 그림이 답하는 것: **차이는 파형이 아니라 반복률이다.**
   왼쪽 두 맵(CW 5 kHz ↔ 5G 풀캡처 28 kHz)이 같아 보이는 것이 핵심이다 —
   잡음 0·단일 거리빈에서 둘의 최대 상대오차는 2.4e-14 다.
   오른쪽 두 팔은 채널을 읽는 속도만 낮췄다: CRS 급 1 kHz 는 날개끝(±1229 Hz)이
   접히고, SSB 급 50 Hz 는 플래시선(127 Hz)마저 접힌다 — «5G 이중고».

정직 표시
  · CRS 팔은 flash_spec 의 조각이 최소 8표본으로 클램프되어 거칠다 — 그대로 둔다.
  · SSB 팔은 표본 100개라 스펙트로그램이 무의미하다(조각 8표본 = 160 ms = 블레이드
    20주기 — 플래시가 원리적으로 안 보인다) → 주기도(PSD)로 대체하고 캡션에 밝힌다.
  · 시간축 솎음은 **표시용**뿐이다(조각 길이가 시간 분해능을 정하고, 인접 열은
    hop 2 로 거의 같은 정보다) — 분석 규약(flash_spec)은 그대로다.

읽는 것: outputs/report07_5g_waveform.{npz,json}, outputs/report07_hover_long.json(_meta)
쓰는 것: outputs/figures/report07_f10.{png,pdf}
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

from md_mapstyle import flash_spec, draw, caption                      # noqa: E402

J = json.load(open(f"{ROOT}/outputs/report07_5g_waveform.json"))
Z = np.load(f"{ROOT}/outputs/report07_5g_waveform.npz")
HOV = json.load(open(f"{ROOT}/outputs/report07_hover_long.json"))["_meta"]
FIGDIR = f"{ROOT}/outputs/figures"
M, A = J["_meta"], J["arms"]
FFL, FTIP = M["f_flash_hz"], M["f_tip_hz"]

FS = 9.5
plt.rcParams.update({
    "font.size": FS, "axes.labelsize": FS, "axes.titlesize": FS,
    "xtick.labelsize": FS - 1, "ytick.labelsize": FS - 1, "legend.fontsize": FS - 1.5,
    "axes.linewidth": 0.9, "figure.dpi": 200, "savefig.dpi": 200,
    "font.family": "DejaVu Sans",
})


def alias(f0: float, fs: float) -> float:
    """f0 가 표본율 fs 에서 접혀 떨어지는 자리 |f| (나이퀴스트 구간으로 접기)."""
    return abs(((f0 + fs / 2) % fs) - fs / 2)


def prep(E, fs):
    """⭐분석은 md_mapstyle 규약 그대로 — 표시용으로만 행(도플러 창)·열(시간)을 줄인다."""
    f, t, S, nper = flash_spec(np.asarray(E, complex), fs, FFL)
    n_slots = len(t)
    keep = np.abs(f) <= min(fs / 2, 2600.0) * 1.0001    # 그리는 창 밖 행은 모아레만 낳는다
    f, S = f[keep], S[keep]
    stride = max(1, int(np.ceil(len(t) / 640.0)))        # 열이 화소보다 많으면 솎는다(표시용)
    return f, t[::stride], S[:, ::stride], nper, n_slots


fig = plt.figure(figsize=(13.4, 3.9))
# 4번째 열 = 컬러바, 5번째 열 = 빈 간격(컬러바 라벨이 주기도 패널을 침범하지 않게)
gs = fig.add_gridspec(1, 6, width_ratios=[1, 1, 1, 0.05, 0.16, 1], wspace=0.30,
                      left=0.048, right=0.985, top=0.80, bottom=0.155)

# ── 맵 세 장 — CW 5 kHz · 풀캡처 28 kHz · CRS 급 1 kHz ────────────────────────
titles = {
    "cw_5k": f"CW channel series (reference)\nfs = {A['cw_5k']['fs_hz']/1e3:.0f} kHz",
    "nr_full_28k": (f"5G OFDM, full capture (every symbol)\n"
                    f"fs = {A['nr_full_28k']['fs_hz']/1e3:.0f} kHz — "
                    f"max rel. err vs CW {M['full_capture_max_rel_err']:.1e}"),
    "nr_crs_1k": (f"1 kHz pilots (LTE-CRS-like)\n"
                  f"fs = {A['nr_crs_1k']['fs_hz']/1e3:.0f} kHz — blade tips fold"),
}
axes, m, CAP_CW = [], None, ""
for i, k in enumerate(["cw_5k", "nr_full_28k", "nr_crs_1k"]):
    ax = fig.add_subplot(gs[0, i], sharey=axes[0] if k == "nr_full_28k" else None)
    f, t, S, nper, n_slots = prep(Z[k], A[k]["fs_hz"])
    m = draw(ax, t, f, S, FTIP, t_scale=1.0)             # 초 단위 — 네 팔 모두 2 s
    if k == "cw_5k":
        CAP_CW = caption(A[k]["fs_hz"], FFL, nper, n_slots)
    if k == "nr_crs_1k":                                 # 나이퀴스트 500 Hz — 접힌 창만 그린다
        ax.set_ylim(-A[k]["nyquist_hz"], A[k]["nyquist_hz"])
        for s in (+1, -1):                               # 날개끝이 접혀 떨어지는 자리(점선)
            ax.axhline(s * alias(FTIP, A[k]["fs_hz"]), color="w", ls=":", lw=1.1)
    ax.set_title(titles[k])
    ax.set_xlim(0, HOV["seconds"])
    ax.set_xlabel("Time [s]")
    if i == 0:
        ax.set_ylabel("Doppler [Hz]")
    elif k == "nr_full_28k":
        plt.setp(ax.get_yticklabels(), visible=False)
    axes.append(ax)
cax = fig.add_subplot(gs[0, 3])
fig.colorbar(m, cax=cax).set_label("Magnitude, each map to its own peak [dB]",
                                   fontsize=FS - 0.5)

# ── SSB 급 50 Hz — 표본 100개: 스펙트로그램 대신 주기도(정직한 쪽) ─────────────
axp = fig.add_subplot(gs[0, 5])
E = np.asarray(Z["nr_ssb_50"], complex)
fs = A["nr_ssb_50"]["fs_hz"]
nfft = 8 * len(E)
P = np.abs(np.fft.fftshift(np.fft.fft(E * np.hanning(len(E)), nfft)))
fax = np.fft.fftshift(np.fft.fftfreq(nfft, 1.0 / fs))
axp.plot(20 * np.log10(P / P.max() + 1e-12), fax, lw=1.0, color="#1f77b4")
for s in (+1, -1):                                       # 플래시선이 접혀 떨어지는 자리
    axp.axhline(s * alias(FFL, fs), color="0.25", ls=":", lw=1.1)
axp.set_xlim(-40, 1.5)
axp.set_ylim(-fs / 2, fs / 2)
axp.grid(alpha=0.25, lw=0.5)
axp.set_xlabel("Power [dB rel. max]")
axp.set_title("50 Hz bursts (5G SSB rate)\nfs = 50 Hz — even the flash folds "
              "(periodogram)")

fig.suptitle(f"Same 2 s hover channel — {HOV['name']}, {M['fc_hz']/1e9:.1f} GHz, "
             f"belly view (az {HOV['az_deg']:.0f}, el {HOV['el_deg']:.0f}). "
             f"Only the waveform / repetition rate changes.",
             fontsize=FS + 0.5, y=0.975)

# ── 캡션 — 그림 밖 하단 (설정 수치는 리포트 부록이 담는다) ─────────────────────
cap = ("CW arm: " + CAP_CW + "\n"
       "OFDM arms use the same display convention at each arm's own rate "
       "(the 1 kHz arm clamps to the 8-sample segment minimum — hence coarse). "
       "Maps normalized to their own peak; time axis thinned for display only.\n"
       "Dashed white: blade-tip Doppler. Dotted: where the blade-tip (1 kHz arm) / "
       "blade-flash (50 Hz arm) lines land after aliasing. The 50 Hz arm has 100 "
       "samples — a periodogram replaces the (meaningless) spectrogram.")
fig.text(0.048, -0.02, cap, fontsize=FS - 1.5, color="0.3", va="top")

for ext in ("png", "pdf"):
    fig.savefig(f"{FIGDIR}/report07_f10.{ext}", bbox_inches="tight", facecolor="white")
plt.close(fig)
print("  ✅ outputs/figures/report07_f10.png")
for k in ("cw_5k", "nr_full_28k", "nr_crs_1k", "nr_ssb_50"):
    v = A[k]
    print(f"     {k:12s} fs {v['fs_hz']:7.0f} Hz · f_tip 접힘 "
          f"{'예' if v['ftip_folds'] else '아니오'} · f_flash 접힘 "
          f"{'예' if v['fflash_folds'] else '아니오'}")
