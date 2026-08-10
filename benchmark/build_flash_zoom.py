# -*- coding: utf-8 -*-
"""
build_flash_zoom.py — ⭐**블레이드 플래시가 보이는** 마이크로도플러 맵.

사용자가 보여준 문헌 그림 (b) 의 **아치 무늬**가 블레이드 플래시다. 그것을 보려면 둘이 필요하다.

  ① **조각을 한 블레이드 주기보다 짧게** — 플래시는 한 주기 안의 사건이라, 조각이 길면
     그 안에서 시간평균되어 가로 능선만 남는다. 그동안 우리가 그렇게 그리고 있었다.
  ② **시간축을 확대** — 2 초를 다 그리면 플래시 253 개가 한 화면에 눌려 붙는다.
     문헌 그림도 0.02 s 만 그린다.

⚠ 대가가 있다. 조각이 짧으면 주파수 분해능이 나빠진다(능선이 굵어진다).
  **둘을 한 그림에 담을 수 없다** — 그래서 왼쪽(플래시)·오른쪽(능선) 두 장으로 낸다.
  이것은 시간·주파수 분해능의 맞바꿈이지 우리 계산의 결함이 아니다.

읽는 것: outputs/report07_hover_long.{npz,json}
쓰는 것: outputs/figures/report07_f8.{png,pdf}
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import spectrogram as _spec

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
J = json.load(open(f"{ROOT}/outputs/report07_hover_long.json"))["_meta"]
E = np.asarray(np.load(f"{ROOT}/outputs/report07_hover_long.npz")["E"], complex)
PRF, FFL, FTIP = J["prf_hz"], J["f_flash_hz"], J["f_tip_hz"]
PER = PRF / FFL                                   # 블레이드 한 주기 = 표본 수

FS = 9.5
plt.rcParams.update({"font.size": FS, "axes.labelsize": FS, "axes.titlesize": FS,
                     "xtick.labelsize": FS - 1, "ytick.labelsize": FS - 1,
                     "figure.dpi": 200, "savefig.dpi": 200, "font.family": "DejaVu Sans"})

ZOOM_MS = 60.0
n0 = int(0.3 * PRF)                                # 시작 과도를 피해 0.3 s 부터
seg = E[n0:n0 + int(ZOOM_MS / 1000 * PRF)]


def sg(x, nper, hop, pad):
    f, t, S = _spec(x, fs=PRF, nperseg=nper, noverlap=nper - hop, nfft=pad * nper,
                    detrend=False, window="hann", return_onesided=False,
                    scaling="spectrum", mode="magnitude")
    return np.fft.fftshift(f), t, np.fft.fftshift(S, axes=0)


fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.0), sharey=True)
for ax, (nper, hop, pad, tag) in zip(
        axes, [(int(round(0.6 * PER)), 2, 8, "flash-resolved"),
               (int(round(6.5 * PER)), 4, 2, "ridge-resolved")]):
    f, t, S = sg(seg, nper, hop, pad)
    m = ax.pcolormesh((t + n0 / PRF) * 1e3, f, 20 * np.log10(S / S.max() + 1e-12),
                      cmap="jet", vmin=-40, vmax=0, shading="gouraud")
    for s in (+1, -1):
        ax.axhline(s * FTIP, color="w", ls="--", lw=1.0, alpha=0.8)
    ax.set_xlabel("Time [ms]")
    ax.set_ylim(-1.9 * FTIP, 1.9 * FTIP)
    ax.set_title(f"{tag} — {nper}-sample segments = {nper/PER:.2f} blade periods\n"
                 f"resolution {PRF/nper:.0f} Hz, hop {hop} ({hop/PRF*1e3:.2f} ms)",
                 fontsize=FS)
axes[0].set_ylabel("Doppler [Hz]")
fig.colorbar(m, ax=axes, pad=0.012).set_label("Magnitude [dB]", fontsize=FS)
fig.suptitle(f"{J['name']} hovering, {J['fc_hz']/1e9:.1f} GHz — the same {ZOOM_MS:.0f} ms, "
             f"two segment lengths.   Blade flashes repeat every {1000/FFL:.1f} ms.",
             fontsize=FS + 0.5, y=1.045)
for e in ("png", "pdf"):
    fig.savefig(f"{ROOT}/outputs/figures/report07_f8.{e}",
                bbox_inches="tight", facecolor="white")
print(f"  ✅ report07_f8.png · 블레이드 주기 {PER:.1f} 표본 = {1000/FFL:.1f} ms")
