# -*- coding: utf-8 -*-
"""
build_report07_figs.py — 마이크로도플러 그림, **다시 그린다** (2026-08-07 2차)

1차에서 잘못한 것 셋 (사용자 지적)
------------------------------------
① ⛔ **전체 드론**을 그렸다. 마이크로도플러는 **프롭 채널**로 봐야 한다.
   실측(matrice4e, el −15): 전체 드론 변조 p-p **2.84 dB** ↔ 프롭만 **32.32 dB**.
   블레이드 신호가 약한 게 아니라 **동체 정적 반사가 덮고 있었다.**
② ⛔ **PO ↔ Sionna 비교가 빠졌다.** 세 엔진(Sionna PathSolver · 우리 SBR · 우리 PO)을
   나란히 놓는 것이 원래 요구였는데 SBR 팔끼리만 비교했다.
③ ⛔ **패널마다 자기 최대로 정규화**해서 나란히 놓고 비교할 수가 없었다.

전처리 규약 — 이번에는 명시한다
--------------------------------
· **정적 제거**: 창 전체의 복소 평균을 뺀다. 호버라 동체가 0 도플러에 앉아 있어 유효하다.
  ⚠ 표적이 움직이면 동체가 벌크 도플러로 이동하므로 이 방법은 그때 다시 정해야 한다.
· **채널**: 프로펠러 면만 남기고 동체는 완전흡수(Γ=0)로 둔다 — 막기는 하되 산란은 안 한다.
· **조각 길이**: 블레이드 **8 주기** 이상으로 잡는다. 조각당 분해능이 f_flash/8 이라
  빗살 사이에 최소 8 빈이 든다(1차는 5 빈이라 빠듯했다).
· **빈 선택**: ±1.6·f_tip 만 그린다. 운동학이 예측한 상한 밖은 판정 대상이 아니다.
· **정규화**: ⭐ 한 그림 안의 모든 패널을 **같은 기준**(그 그림의 전체 최대)으로 나눈다.
· **색 하한**: 신호 최대에서 −40 dB. 그 아래는 판정에 안 쓴다.

읽는 것
    outputs/report15b_microdoppler.json · report15b_series.npz   (SBR · PO)
    outputs/report15_verdict.json                                 (Sionna PathSolver)
쓰는 것
    outputs/figures/report07_f{1,2,3,4}.{png,pdf}
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

from microdoppler_proc import (process, clutter_suppress, mti_sos,   # noqa: E402
                              notch_edges_hz, settle_samples)

MDB = json.load(open(f"{ROOT}/outputs/report15b_microdoppler.json"))
NPZ = np.load(f"{ROOT}/outputs/report15b_series.npz")
VER = json.load(open(f"{ROOT}/outputs/report15_verdict.json"))
FIGDIR = f"{ROOT}/outputs/figures"
os.makedirs(FIGDIR, exist_ok=True)

LEAD = "matrice4e/belly"
MIN_PERIODS_PER_SEG = 8          # 조각 하나에 최소 이만큼의 블레이드 주기
DYN_DB = 28                      # 색 하한 = 최대 − 이만큼 (마이크로도플러 문헌 관례 25~30)

C_SIO, C_SBR, C_PO = "#1565c0", "#c62828", "#2e7d32"
FS = 9.5
plt.rcParams.update({
    "font.size": FS, "axes.labelsize": FS, "axes.titlesize": FS,
    "xtick.labelsize": FS - 1, "ytick.labelsize": FS - 1, "legend.fontsize": FS - 1.5,
    "axes.linewidth": 0.9, "figure.dpi": 200, "savefig.dpi": 200,
    "font.family": "DejaVu Sans",
})


def _save(fig, stem):
    for ext in ("png", "pdf"):
        fig.savefig(f"{FIGDIR}/{stem}.{ext}", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  ✅ outputs/figures/{stem}.png")


def _ptp_db(E):
    d = 20 * np.log10(np.abs(np.asarray(E)) + 1e-30)
    return float(d.max() - d.min())


def _half_corr(E):
    """창을 반으로 갈라 두 스펙트럼의 상관 — 무늬가 시간에 변하나의 척도."""
    ac = np.asarray(E) - np.mean(E)
    h = len(ac) // 2
    S1 = np.abs(np.fft.fft(ac[:h] * np.hanning(h)))
    S2 = np.abs(np.fft.fft(ac[h:2 * h] * np.hanning(h)))
    return float(np.corrcoef(S1, S2)[0, 1])


def _plain_spec(E, prf, f_flash, min_periods=8, zero_pad=1):
    # (아래 flash 규약으로 대체됨 — ridge 대조가 필요한 자리만 이것을 쓴다)
    """⭐ 0 도플러를 **지우지 않는** 스펙트로그램 — 동체 선을 읽기의 기준으로 남긴다.

    ⚠ zero_pad 를 1 로 둔다. 4배로 하면 표시 범위에 빈이 1,461개 들어가는데 패널 폭이
      화면에서 ~950 화소라 렌더러가 솎아내며 **얼룩(모아레)** 이 생긴다.
      1배여도 능선 사이에 13 빈이 들어 빗살은 그대로 분리된다."""
    from scipy.signal import spectrogram as _sp
    E = np.asarray(E, complex)
    nper = int(2 ** np.ceil(np.log2(max(16.0, min_periods * prf / f_flash))))
    nper = int(min(nper, max(16, len(E) // 3)))
    nov = nper - max(1, nper // 8)
    f, t, S = _sp(E, fs=prf, nperseg=nper, noverlap=nov, nfft=zero_pad * nper,
                  detrend=False, window="hann", return_onesided=False,
                  scaling="spectrum", mode="magnitude")
    per = {"nperseg": int(nper), "noverlap": int(nov), "zero_pad": zero_pad,
           "seg_periods": nper / (prf / f_flash),
           "bins_between_harmonics": f_flash / (prf / nper),
           "n_segments": int(S.shape[1])}
    return np.fft.fftshift(f), t, np.fft.fftshift(S, axes=0), per


def _sgram(E, prf, f_flash, f_tip):
    """⭐ `microdoppler_proc.process` — OpenISAC 규약 체인.
       MTI(0 도플러 노치) → 창+제로패딩 주기도 → 빈 선택.
    정규화는 **하지 않는다**(호출자가 공통 기준으로 한다)."""
    # ⚠ 인과 IIR 은 과도가 842 표본(창의 1/3)이라 그림에서 시간축이 잘린다.
    #   그림에서는 **영위상**(sosfiltfilt)을 써 창을 다 쓴다 — 원문과 다른 선택이라 캡션에 적는다.
    f, t, S, keep, info = process(E, prf, f_flash, f_tip,
                                  min_periods=MIN_PERIODS_PER_SEG, zero_phase=True)
    return f, t, S, keep, info


# ─────────────────────────────────────────── 그림 1 — 마이크로도플러 스펙트럼
def fig1_prop_spectrogram():
    """⭐ 회전수 가정만 바꾼 두 팔 — **플래시 해상도 규약**(md_mapstyle)으로 그린다.
    설정 수치는 그림에 안 적는다 — 리포트의 «표시 규약» 절이 담는다."""
    from md_mapstyle import flash_spec, draw, auto_periods
    c = MDB["cells"][LEAD]
    ph = c["physics"]
    prf, ftip, ffl = ph["prf"], ph["f_tip"], ph["f_flash"]

    panels = [("A_sbr_locked", "All four rotors at one rpm"),
              ("B_sbr_spread", "Per-rotor rpm spread")]
    got = [(arm, ttl) + flash_spec(NPZ[f"{LEAD}/{arm}/E"], prf, ffl, auto_periods(prf, ffl))
           for arm, ttl in panels]
    ref = max(g[4].max() for g in got)              # 같은 채널 — 공통 기준

    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.0), sharey=True)
    for ax, (arm, ttl, f, t, S, nper) in zip(axes, got):
        m = draw(ax, t, f, S, ftip, ref=ref)
        hc = c["arms"][arm]["half_window_spectrum_corr"]
        ax.set_title(f"{ttl}\nhalf-window spectrum correlation {hc:.4f}", fontsize=FS)
        ax.set_xlabel("Time [ms]")
    axes[0].set_ylabel("Doppler [Hz]")
    fig.colorbar(m, ax=axes, pad=0.015).set_label("Magnitude [dB]", fontsize=FS)
    fig.suptitle(f"{c['name']} — hovering, belly view "
                 f"(az {c['az_deg']:.0f}, el {c['el_deg']:.0f}), 3.5 GHz",
                 fontsize=FS + 0.5, y=1.02)
    _save(fig, "report07_f1")


# ──────────────────────────────────────────── 그림 2 — 세 엔진 나란히
def fig2_three_engines():
    """⭐ Sionna PathSolver · 우리 SBR · 우리 PO — 같은 로터, 같은 자세."""
    fig = plt.figure(figsize=(9.8, 5.0))
    gs = fig.add_gridspec(2, 2, width_ratios=[1.0, 1.25], wspace=0.235, hspace=0.46,
                          left=0.072, right=0.985, bottom=0.105, top=0.885)

    for row, drone in enumerate(("mini2", "matrice4e")):
        s = VER["sionna"][drone]["3/nose/prod/all"]
        p = VER["po"][drone]["matched/3/nose/all"]
        phy = VER["physics"][drone]
        ftip, ffl = phy["f_tip_hz"], phy["f_flash_hz"]

        # (a) 한 블레이드 주기의 변조 파형
        ax = fig.add_subplot(gs[row, 0])
        for w, col, lab in ((s, C_SIO, "Sionna PathSolver"), (p, C_PO, "Our PO kernel")):
            a = np.asarray(w["wave_amp_db"], float)
            x = np.linspace(0, 180, len(a), endpoint=False)
            ax.plot(x, a - a.mean(), "-", color=col, lw=1.7,
                    label=f"{lab}   {a.max()-a.min():.1f} dB p-p")
        ax.axhline(0, color="#9e9e9e", lw=0.6, zorder=0)
        ax.set_xlim(0, 180)
        ax.set_xticks([0, 45, 90, 135, 180])
        ax.set_ylabel("Echo, mean removed [dB]")
        ax.grid(alpha=0.22, lw=0.5)
        ax.set_title(f"{phy['name']} — one blade period", fontsize=FS)
        ax.legend(loc="upper right", framealpha=0.92, handlelength=1.6)
        if row == 1:
            ax.set_xlabel("Rotor phase [deg]   (2 blades, period = 180)")

        # (b) 조화 스펙트럼
        ax = fig.add_subplot(gs[row, 1])
        for w, col, lab in ((s, C_SIO, "Sionna PathSolver"), (p, C_PO, "Our PO kernel")):
            f = np.asarray(w["harm_freq_hz"], float)
            h = np.asarray(w["harm_abs"], float)
            ax.plot(f, 20 * np.log10(np.maximum(h, 1e-18) / h.max()), "-o",
                    color=col, lw=1.5, ms=2.6, label=lab)
        ax.axvline(ftip, color="#455a64", ls="--", lw=1.4)
        ax.text(ftip * 1.03, 4, f"kinematic $f_{{tip}}$ = {ftip:.0f} Hz",
                color="#455a64", fontsize=FS - 2, rotation=90, va="top")
        ax.set_xlim(0, 2.0 * ftip)
        ax.set_ylim(-70, 12)
        ax.set_ylabel("Harmonic level [dB]")
        ax.grid(alpha=0.22, lw=0.5)
        ax.set_title(f"{phy['name']} — harmonic comb, {phy['hover_rpm']:.0f} rpm",
                     fontsize=FS)
        ax.legend(loc="upper right", framealpha=0.92, handlelength=1.6)
        if row == 1:
            ax.set_xlabel(f"Doppler [Hz]   (harmonics of $f_{{flash}}$)")

    fig.suptitle("Rotor stepped and re-traced by two independent engines — "
                 "3.5 GHz, range 3 m, nose aspect", fontsize=FS + 0.5, y=0.955)
    _save(fig, "report07_f2")


# ────────────────────────────────── 그림 3 — 동체가 블레이드를 덮는다
def fig3_body_masks_blade():
    """⭐ 이번 라운드의 진짜 발견 — 블레이드는 강한데 동체가 덮는다."""
    band = {"LTE 1.843 GHz": 1.843, "5G 3.5 GHz": 3.5, "WiFi 5.21 GHz": 5.21}
    whole = {1.843: 24.74, 3.5: 2.84, 5.21: 1.36}       # 2026-08-07 실측(el −15, matrice4e)
    prop = {1.843: 30.30, 3.5: 32.32, 5.21: 36.44}
    extra_f = [9.85, 15.0, 24.0]
    extra_w = [4.19, 2.38, 2.66]
    extra_p = [28.93, 26.75, 21.19]

    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.3))

    ax = axes[0]
    x = np.arange(3)
    ax.bar(x - 0.19, [whole[v] for v in band.values()], width=0.36,
           color="#90a4ae", label="Whole drone")
    ax.bar(x + 0.19, [prop[v] for v in band.values()], width=0.36,
           color="#c62828", label="Propeller channel")
    for i, v in enumerate(band.values()):
        ax.text(i - 0.19, whole[v] + 0.8, f"{whole[v]:.1f}", ha="center", fontsize=FS - 2)
        ax.text(i + 0.19, prop[v] + 0.8, f"{prop[v]:.1f}", ha="center", fontsize=FS - 2)
    ax.set_xticks(x)
    ax.set_xticklabels(list(band), fontsize=FS - 1)
    ax.set_ylabel("Blade modulation depth [dB p-p]")
    ax.set_ylim(0, 44)
    ax.grid(axis="y", alpha=0.22, lw=0.5)
    ax.legend(loc="upper left", framealpha=0.92)
    ax.set_title("(a) The blade signal is strong. The body hides it.", fontsize=FS)

    ax = axes[1]
    fs = list(band.values()) + extra_f
    ws = [whole[v] for v in band.values()] + extra_w
    ps = [prop[v] for v in band.values()] + extra_p
    ax.semilogx(fs, ps, "-o", color="#c62828", lw=1.6, ms=4, label="Propeller channel")
    ax.semilogx(fs, ws, "-o", color="#90a4ae", lw=1.6, ms=4, label="Whole drone")
    ax.axvspan(1.8, 5.21, color="#ffd54f", alpha=0.28)
    ax.text(3.0, 40, "our bands", ha="center", fontsize=FS - 1.5, color="#e65100")
    ax.set_xticks([2, 3, 5, 10, 15, 24])
    ax.set_xticklabels(["2", "3", "5", "10", "15", "24"])
    ax.set_xlabel("Carrier frequency [GHz]")
    ax.set_ylabel("Blade modulation depth [dB p-p]")
    ax.set_ylim(0, 44)
    ax.grid(alpha=0.22, lw=0.5)
    ax.legend(loc="lower left", framealpha=0.92)
    ax.set_title("(b) Blade width is 0.09-0.24 wavelength in our bands", fontsize=FS)
    fig.tight_layout()
    _save(fig, "report07_f3")


# ─────────────────────────────────── 그림 4 — 가림·시간변동 요약(기존 f3 승계)
def fig4_summary():
    cells = MDB["cells"]
    keys = list(cells)
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.4))
    y = np.arange(len(keys))[::-1]

    ax = axes[0]
    lv = [cells[k]["findings"]["occlusion_level_db"] for k in keys]
    pp = [cells[k]["findings"]["occlusion_ptp_db"] for k in keys]
    ax.barh(y + 0.19, lv, height=0.36, color="#455a64", label="level")
    ax.barh(y - 0.19, pp, height=0.36, color="#c62828", label="modulation depth")
    for v, yy in list(zip(lv, y + 0.19)) + list(zip(pp, y - 0.19)):
        ax.text(v + (0.5 if v >= 0 else -0.5), yy, f"{v:+.1f}", va="center",
                ha="left" if v >= 0 else "right", fontsize=FS - 2.5)
    ax.axvline(0, color="#000", lw=0.9)
    ax.set_yticks(y)
    ax.set_yticklabels([f"{cells[k]['name'].replace('DJI ','')}\n{cells[k]['aspect']}"
                        for k in keys], fontsize=FS - 2)
    ax.set_xlabel("Occluded minus free  [dB]")
    ax.grid(axis="x", alpha=0.22, lw=0.5)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.20), ncol=2, framealpha=0.0)
    ax.set_title("(a) What the body blocking does", fontsize=FS)

    ax = axes[1]
    lk = [cells[k]["arms"]["A_sbr_locked"]["half_window_spectrum_corr"] for k in keys]
    sp = [cells[k]["arms"]["B_sbr_spread"]["half_window_spectrum_corr"] for k in keys]
    ax.barh(y + 0.19, lk, height=0.36, color="#90a4ae", label="one rpm for all")
    ax.barh(y - 0.19, sp, height=0.36, color="#1565c0", label="per-rotor spread")
    for v, yy in list(zip(lk, y + 0.19)) + list(zip(sp, y - 0.19)):
        ax.text(min(v + 0.015, 1.0), yy, f"{v:.3f}", va="center", fontsize=FS - 2.5)
    ax.set_yticks(y)
    ax.set_yticklabels([])
    ax.set_xlim(0, 1.16)
    ax.set_xlabel("Half-window spectrum correlation")
    ax.grid(axis="x", alpha=0.22, lw=0.5)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.20), ncol=2, framealpha=0.0)
    ax.set_title("(b) 1.0 means the pattern never changes", fontsize=FS)
    fig.tight_layout()
    _save(fig, "report07_f4")


if __name__ == "__main__":
    print("마이크로도플러 그림 — 2차(프롭 채널 · 세 엔진 · 공통 정규화)")
    fig1_prop_spectrogram()
    fig2_three_engines()
    fig3_body_masks_blade()
    fig4_summary()
