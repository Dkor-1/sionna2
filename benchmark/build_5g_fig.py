# -*- coding: utf-8 -*-
"""
build_5g_fig.py — 같은 채널에 5G 파형을 태운 네 팔을 나란히.

⭐ 이 그림이 답하는 것: **차이는 파형이 아니라 반복률이다.**
   왼쪽 두 맵(CW 5 kHz ↔ 5G 풀캡처 28 kHz)이 같아 보이는 것이 핵심이다 —
   잡음 0·단일 거리빈에서 둘의 최대 상대오차는 2.4e-14 다.
   오른쪽 두 팔은 채널을 읽는 속도만 낮췄다: CRS 급 1 kHz 는 날개끝(±1229 Hz)이
   접히고, SSB 급 50 Hz 는 플래시선(127 Hz)마저 접힌다 — «5G 이중고».

⭐ 2026-08-10 사용자 지적 반영 — **네 패널 축 동일** + **관측창 단축**.
   · 이전 판은 CRS 패널이 자기 나이퀴스트(±500 Hz)로 좁혀져 있고 SSB 는 주기도라
     축이 제각각이었다 → 네 팔 전부 같은 스펙트로그램 축(시간 0~0.3 s ·
     도플러 ±1.9·f_tip)으로 통일한다.
   · 그러면 낮은 반복률의 결과가 **빈 띠**로 정직하게 보인다: CRS 는 ±500 Hz 밖이
     비고(그 안에 접힌 날개끝), SSB 는 ±25 Hz 의 가는 띠뿐이다 — 그 공백이 결론이다.
   · SSB 0.3 s = 표본 15개 → 조각 8·hop 2 = 시간 슬롯 4개. 스펙트로그램이 극도로
     거친 것 자체가 «50 Hz 로는 이만큼도 못 본다» 의 정직한 표시다.

정직 표시
  · CRS 팔은 flash_spec 의 조각이 최소 8표본으로 클램프되어 거칠다 — 그대로 둔다.
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

from md_mapstyle import (YLIM_FTIP, auto_periods, caption, draw,       # noqa: E402
                         flash_spec)

J = json.load(open(f"{ROOT}/outputs/report07_5g_waveform.json"))
Z = np.load(f"{ROOT}/outputs/report07_5g_waveform.npz")
HOV = json.load(open(f"{ROOT}/outputs/report07_hover_long.json"))["_meta"]
FIGDIR = f"{ROOT}/outputs/figures"
M, A = J["_meta"], J["arms"]
FFL, FTIP = M["f_flash_hz"], M["f_tip_hz"]

T_SHOW = 0.3          # ⭐관측창 [s] — 2 s 전체 대신 앞 0.3 s 만 (사용자: 훨씬 짧게)
# ⭐도플러축 상한 [Hz] — 사용자 지시 «±1200 Hz 정도에서 잘라서». 날개끝이 1229 Hz 라
#   정확히 1200 으로 자르면 팁 선이 화면 밖으로 나가므로 그 위 1300 에서 자른다.
YMAX_HZ = 1300.0

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
    """⭐분석은 md_mapstyle 규약 그대로 — 앞 T_SHOW 초만 잘라 그린다.
    표시용으로만 행(그리는 도플러 창 밖)·열(화소 초과분)을 줄인다."""
    E = np.asarray(E, complex)[: max(8, int(round(T_SHOW * fs)))]
    #  ⭐ 2026-08-10 정정 — 조각 길이를 규약 기본값(0.6 주기)에 두고 있었다. auto_periods 가
    #     표본이 충분한 팔에서는 0.45 주기를 골라 준다(전량 포착 팔: Δt 4.75 → 3.54 ms).
    #     표본이 모자란 팔(1 kHz 파일럿·50 Hz SSB)에서는 auto_periods 가 스스로 0.6 으로
    #     물러서므로, 팔마다 «가장 뚜렷한» 조각이 자동으로 잡힌다.
    f, t, S, nper = flash_spec(E, fs, FFL, auto_periods(fs, FFL))
    n_slots = len(t)
    keep = np.abs(f) <= YMAX_HZ * 1.05                   # 그리는 창 밖 행은 모아레만 낳는다
    f, S = f[keep], S[keep]
    stride = max(1, int(np.ceil(len(t) / 640.0)))        # 열이 화소보다 많으면 솎는다(표시용)
    return f, t[::stride], S[:, ::stride], nper, n_slots


titles = {
    "cw_5k": f"CW channel series (reference)\nfs = {A['cw_5k']['fs_hz']/1e3:.0f} kHz",
    "nr_full_28k": (f"5G OFDM, full capture (every symbol)\n"
                    f"fs = {A['nr_full_28k']['fs_hz']/1e3:.0f} kHz — "
                    f"max rel. err vs CW {M['full_capture_max_rel_err']:.1e}"),
    "nr_crs_1k": (f"1 kHz pilots (LTE-CRS-like)\n"
                  f"fs = {A['nr_crs_1k']['fs_hz']/1e3:.0f} kHz — blade tips fold"),
    "nr_ssb_50": (f"50 Hz bursts (5G SSB rate)\n"
                  f"fs = {A['nr_ssb_50']['fs_hz']:.0f} Hz — even the flash folds"),
}

fig = plt.figure(figsize=(13.6, 3.9))
gs = fig.add_gridspec(1, 5, width_ratios=[1, 1, 1, 1, 0.05], wspace=0.24,
                      left=0.048, right=0.94, top=0.80, bottom=0.155)

axes, m, CAP_CW = [], None, ""
for i, k in enumerate(["cw_5k", "nr_full_28k", "nr_crs_1k", "nr_ssb_50"]):
    ax = fig.add_subplot(gs[0, i], sharey=axes[0] if i else None)
    fs_k = A[k]["fs_hz"]
    f, t, S, nper, n_slots = prep(Z[k], fs_k)
    m = draw(ax, t, f, S, FTIP, t_scale=1.0)
    ax.set_ylim(-YMAX_HZ, YMAX_HZ)                       # ⭐네 패널 도플러축 통일 (±1.3 kHz)
    if k == "cw_5k":
        CAP_CW = caption(fs_k, FFL, nper, n_slots)
    if fs_k / 2 < YMAX_HZ:
        # ⭐2026-08-10 사용자 문답: «범위 밖까지 그릴 수 없나» → 그 자리엔 **정보가 없다**.
        #   표본화 스펙트럼은 주기 fs 로 반복하므로 복사본을 그릴 수는 있지만, 그러면
        #   «저것도 측정한 것» 으로 읽혀 혼동만 커진다. 그려 넣지 않는다.
        #   ⚠ 대신 **비워 두지도 않는다** — 하양은 «조용하다» 로 읽힌다. 회색으로 덮어
        #   «이 표본율로는 닿지 못하는 영역» 임을 그림 자체가 말하게 한다.
        ax.axhspan(fs_k / 2, YMAX_HZ, color="0.86", zorder=3)
        ax.axhspan(-YMAX_HZ, -fs_k / 2, color="0.86", zorder=3)
        for s in (+1, -1):
            ax.axhline(s * fs_k / 2, color="0.35", ls="-", lw=0.9, zorder=4)
    if A[k]["ftip_folds"]:                               # 날개끝이 접혀 떨어지는 자리(점선)
        for s in (+1, -1):
            ax.axhline(s * alias(FTIP, fs_k), color="w", ls=":", lw=1.1)
    if A[k]["fflash_folds"]:                             # 플래시선이 접히는 자리(점선)
        for s in (+1, -1):
            ax.axhline(s * alias(FFL, fs_k), color="w", ls=":", lw=1.1)
    ax.set_title(titles[k])
    ax.set_xlim(0, T_SHOW)
    ax.set_xlabel("Time [s]")
    if i == 0:
        ax.set_ylabel("Doppler [Hz]")
    else:
        plt.setp(ax.get_yticklabels(), visible=False)
    axes.append(ax)

cax = fig.add_subplot(gs[0, 4])
fig.colorbar(m, cax=cax).set_label("Magnitude, each map to its own peak [dB]",
                                   fontsize=FS - 0.5)

fig.suptitle(f"Same hover channel, first {T_SHOW:.1f} s shown — {HOV['name']}, "
             f"{M['fc_hz']/1e9:.1f} GHz, belly view (az {HOV['az_deg']:.0f}, "
             f"el {HOV['el_deg']:.0f}). Only the waveform / repetition rate changes. "
             "All four panels share the same axes.",
             fontsize=FS + 0.5, y=0.975)

cap = ("CW arm: " + CAP_CW + "\n"
       "All four panels: same time window and same Doppler axis. OFDM arms use the "
       "same display convention at each arm's own rate (the 1 kHz arm clamps to the "
       "8-sample segment minimum; the 50 Hz arm has 15 samples in this window = 4 "
       "time slots — that coarseness is the honest result). Maps normalized to their "
       "own peak; time axis thinned for display only.\n"
       "Dashed white: true blade-tip Doppler. Solid grey: the arm's Nyquist edge — "
       "the white area beyond it is not \"quiet\", it is unmeasurable at that rate. "
       "Dotted white: where the blade-tip (1 kHz arm) / blade-flash (50 Hz arm) lines "
       "land after aliasing.")
# ⚠ 긴 한 줄 캡션은 bbox_inches="tight" 에서 **그림 폭을 늘린다** — 패널 폭에 맞춰 접는다.
import textwrap                                                        # noqa: E402
cap = "\n".join(textwrap.fill(p, 170) for p in cap.split("\n"))
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
