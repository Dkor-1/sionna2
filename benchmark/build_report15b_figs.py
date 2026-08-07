# -*- coding: utf-8 -*-
"""
build_report15b_figs.py — 재계산한 마이크로도플러 **패턴을 눈으로 확인**한다.

읽는 것: outputs/report15b_microdoppler.json · outputs/report15b_series.npz
쓰는 것: outputs/figures/report15b_f{1,2,3}.{png,pdf}

그림 1  스펙트로그램 — 로터 rpm 이 잠겼을 때 ↔ 흩어졌을 때
        ⭐ 잠기면 시간에 안 변한다(완전 주기). 그게 옛 코드의 성질이었다.
그림 2  가림 단일축 — 동체가 막을 때 ↔ 안 막을 때 (조화 스펙트럼 + 파형)
그림 3  요약 — 자세·기체별 가림량과 시간변동성

⚠ 그림 글자는 전부 영어(하우스 규약). 본문·주석은 한국어.
"""
from __future__ import annotations

import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import spectrogram as _spec

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

J = os.path.join(ROOT, "outputs", "report15b_microdoppler.json")
NPZ = os.path.join(ROOT, "outputs", "report15b_series.npz")
FIGDIR = os.path.join(ROOT, "outputs", "figures")
os.makedirs(FIGDIR, exist_ok=True)

FS = 9.5
plt.rcParams.update({
    "font.size": FS, "axes.labelsize": FS, "axes.titlesize": FS,
    "xtick.labelsize": FS - 1, "ytick.labelsize": FS - 1, "legend.fontsize": FS - 1.5,
    "axes.linewidth": 0.9, "figure.dpi": 200, "savefig.dpi": 200,
    "font.family": "DejaVu Sans",
})
C_OCC, C_FREE = "#c62828", "#1565c0"


def _save(fig, stem):
    for ext in ("png", "pdf"):
        fig.savefig(f"{FIGDIR}/{stem}.{ext}", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  ✅ outputs/figures/{stem}.png")


def _sgram(E, prf, nper=None):
    """복소 슬로타임 → (도플러 f, 시간 t, dB). 정적 0-도플러는 뺀다."""
    E = np.asarray(E) - np.mean(E)
    nper = nper or max(64, len(E) // 12)
    nov = nper - max(1, nper // 8)
    f, t, S = _spec(E, fs=prf, nperseg=nper, noverlap=nov, nfft=4 * nper,
                    detrend=False, window="hann", return_onesided=False,
                    scaling="spectrum", mode="magnitude")
    f = np.fft.fftshift(f)
    S = np.fft.fftshift(S, axes=0)
    return f, t, 20 * np.log10(S / (S.max() + 1e-30) + 1e-12)


def fig1_spectrogram(res, npz, cell_key):
    """⭐ rpm 이 잠기면 시간에 안 변한다 — 그 사실을 눈으로 보인다."""
    c = res["cells"][cell_key]
    ph = c["physics"]
    prf, ftip = ph["prf"], ph["f_tip"]
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.5), sharey=True)
    for ax, arm, ttl in ((axes[0], "A_sbr_locked", "All four rotors at one rpm"),
                         (axes[1], "B_sbr_spread", "Per-rotor rpm spread")):
        E = npz[f"{cell_key}/{arm}/E"]
        f, t, S = _sgram(E, prf)
        m = ax.pcolormesh(t * 1e3, f, S, cmap="turbo", vmin=-45, vmax=0, shading="auto")
        for s in (+1, -1):
            ax.axhline(s * ftip, color="w", ls="--", lw=1.0, alpha=0.85)
        hc = c["arms"][arm]["half_window_spectrum_corr"]
        ax.set_title(f"{ttl}\nhalf-window spectrum correlation = {hc:.4f}", fontsize=FS)
        ax.set_xlabel("Time [ms]")
        ax.set_ylim(-1.6 * ftip, 1.6 * ftip)
    axes[0].set_ylabel("Doppler [Hz]")
    axes[0].text(0.02, 0.96, f"white dashed = kinematic $f_{{tip}}$ = {ftip:.0f} Hz",
                 transform=axes[0].transAxes, fontsize=FS - 2, color="w", va="top")
    fig.colorbar(m, ax=axes, pad=0.015).set_label("Normalised magnitude [dB]", fontsize=FS)
    fig.suptitle(f"{c['name']} — {c['aspect']} (az {c['az_deg']:.0f}, el {c['el_deg']:.0f}), "
                 f"{ph['n_t']} slow-time samples over "
                 f"{res['_meta']['n_flash_periods']} blade periods",
                 fontsize=FS + 0.5, y=1.04)
    _save(fig, "report15b_f1")


def fig2_occlusion(res, npz, cell_key):
    """⭐ 단일축 — 동체가 막느냐만 다르다."""
    c = res["cells"][cell_key]
    ph = c["physics"]
    prf, ftip = ph["prf"], ph["f_tip"]
    fig = plt.figure(figsize=(9.6, 3.6))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.0, 1.25], wspace=0.24,
                          left=0.07, right=0.985, bottom=0.155, top=0.845)

    # (a) 한 블레이드 주기의 파형
    ax = fig.add_subplot(gs[0])
    n_show = int(prf / ph["f_flash"] * 2)                 # 2 주기만
    for arm, col, lab in (("F_blade_occ", C_OCC, "Body blocks (occluded)"),
                          ("G_blade_free", C_FREE, "Body removed (free)")):
        E = npz[f"{cell_key}/{arm}/E"][:n_show]
        db = 20 * np.log10(np.abs(E) + 1e-30)
        x = np.arange(len(db)) / prf * 1e3
        ptp = c["arms"][arm]["modulation_ptp_db"]     # 전체 창 기준(창 일부만 그린다)
        ax.plot(x, db - db.mean(), "-", color=col, lw=1.5,
                label=f"{lab}   {ptp:.1f} dB p-p over the full window")
    ax.set_xlabel("Time [ms]   (two blade periods of the full window)")
    ax.set_ylabel("Blade echo, mean removed [dB]")
    ax.grid(alpha=0.22, lw=0.5)
    ax.legend(loc="lower right", framealpha=0.92, handlelength=1.6)
    ax.set_title("(a) Same rays, same mesh, same motion", fontsize=FS)

    # (b) 조화 스펙트럼
    ax = fig.add_subplot(gs[1])
    # ⚠ 창 하나짜리 FFT 는 빈이 촘촘해 빗살이 잡음 바닥에 묻힌다.
    #   ⭐ 스펙트로그램을 시간으로 평균한다(Welch) — 자리가 고정된 빗살은 그대로 더해지고
    #     무작위 바닥은 √(조각 수)만큼 내려간다. 분해능은 조각 길이가 정한다.
    n_seg = 6
    for arm, col, lab in (("F_blade_occ", C_OCC, "Body blocks"),
                          ("G_blade_free", C_FREE, "Body removed")):
        E = np.asarray(npz[f"{cell_key}/{arm}/E"])
        E = E - E.mean()
        L = len(E) // n_seg
        segs = np.stack([E[i * L:(i + 1) * L] * np.hanning(L) for i in range(n_seg)])
        P = (np.abs(np.fft.fftshift(np.fft.fft(segs, n=8 * L, axis=1), axes=1)) ** 2).mean(0)
        fw = np.fft.fftshift(np.fft.fftfreq(8 * L, 1.0 / prf))
        dbw = 10 * np.log10(P / P.max() + 1e-12)
        ax.plot(fw, dbw, "-", color=col, lw=1.2, label=lab)
    res_hz = prf / L
    ax.text(0.02, 0.04, f"time-averaged over {n_seg} segments\n"
                        f"resolution {res_hz:.0f} Hz  ({ftip/res_hz:.0f} bins to $f_{{tip}}$)",
            transform=ax.transAxes, fontsize=FS - 2.5, color="#455a64", va="bottom")
    for s_ in (+1, -1):
        ax.axvline(s_ * ftip, color="#2e7d32", ls="--", lw=1.3)
    ax.text(ftip * 1.03, 2, f"$f_{{tip}}$ = {ftip:.0f} Hz", color="#2e7d32",
            fontsize=FS - 2, rotation=90, va="top")
    ax.set_xlim(-1.7 * ftip, 1.7 * ftip)
    ax.set_ylim(-42, 4)
    ax.set_xlabel("Doppler [Hz]")
    ax.set_ylabel("Level [dB]")
    ax.grid(alpha=0.22, lw=0.5)
    ax.legend(loc="upper right", framealpha=0.92, handlelength=1.6)
    fnd = c["findings"]
    ax.set_title(f"(b) Occlusion changes level by {fnd['occlusion_level_db']:+.2f} dB "
                 f"and depth by {fnd['occlusion_ptp_db']:+.2f} dB", fontsize=FS)
    fig.suptitle(f"{c['name']} — {c['aspect']} (az {c['az_deg']:.0f}, "
                 f"el {c['el_deg']:.0f}), propeller channel only",
                 fontsize=FS + 0.5, y=1.02)
    _save(fig, "report15b_f2")


def fig3_summary(res):
    """자세·기체별로 가림량과 시간변동성을 한 장에."""
    cells = res["cells"]
    keys = list(cells)
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.2))

    # (a) 가림 — 레벨과 변조 깊이
    ax = axes[0]
    y = np.arange(len(keys))[::-1]
    lv = [cells[k]["findings"]["occlusion_level_db"] for k in keys]
    pp = [cells[k]["findings"]["occlusion_ptp_db"] for k in keys]
    ax.barh(y + 0.19, lv, height=0.36, color="#455a64", label="level")
    ax.barh(y - 0.19, pp, height=0.36, color=C_OCC, label="modulation depth")
    for v, yy in list(zip(lv, y + 0.19)) + list(zip(pp, y - 0.19)):
        ax.text(v + (0.6 if v >= 0 else -0.6), yy, f"{v:+.1f}", va="center",
                ha="left" if v >= 0 else "right", fontsize=FS - 2.5)
    ax.axvline(0, color="#000", lw=0.9)
    ax.set_yticks(y)
    ax.set_yticklabels([f"{cells[k]['name'].replace('DJI ','')}\n{cells[k]['aspect']}"
                        for k in keys], fontsize=FS - 2)
    ax.set_xlabel("Occluded minus free  [dB]")
    ax.grid(axis="x", alpha=0.22, lw=0.5)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.20), ncol=2,
              framealpha=0.0, borderpad=0.1)
    ax.set_title("(a) What the body blocking does", fontsize=FS)

    # (b) 시간 변동성
    ax = axes[1]
    lk = [cells[k]["arms"]["A_sbr_locked"]["half_window_spectrum_corr"] for k in keys]
    sp = [cells[k]["arms"]["B_sbr_spread"]["half_window_spectrum_corr"] for k in keys]
    ax.barh(y + 0.19, lk, height=0.36, color="#90a4ae", label="one rpm for all rotors")
    ax.barh(y - 0.19, sp, height=0.36, color=C_FREE, label="per-rotor rpm spread")
    for v, yy in list(zip(lk, y + 0.19)) + list(zip(sp, y - 0.19)):
        ax.text(min(v + 0.015, 1.0), yy, f"{v:.3f}", va="center", fontsize=FS - 2.5)
    ax.set_yticks(y)
    ax.set_yticklabels([])
    ax.set_xlim(0, 1.16)
    ax.set_xlabel("Half-window spectrum correlation")
    ax.grid(axis="x", alpha=0.22, lw=0.5)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.20), ncol=2,
              framealpha=0.0, borderpad=0.1)
    ax.set_title("(b) 1.0 means the pattern never changes in time", fontsize=FS)
    fig.tight_layout()
    _save(fig, "report15b_f3")


def main():
    res = json.load(open(J))
    npz = np.load(NPZ)
    cells = list(res["cells"])

    # ⭐ 대표 칸은 «가림이 큰 칸» 이 아니라 **메쉬가 깨끗한 기체** 로 고른다.
    #   2026-08-07 메쉬 확정검사: matrice4e 프롭-벨 겹침 0.01 % (깨끗) ·
    #   mini5pro 9.12 % (R3 이연). 헤드라인 그림을 결함이 남은 기체로 그리면
    #   «그 9 % 때문 아니냐» 는 반론에 답할 수 없다.
    #   matrice4e 는 1차 실측 표적이기도 하다.
    def _pick(drone):
        c = [k for k in cells if res["cells"][k]["drone"] == drone]
        return max(c, key=lambda k: abs(res["cells"][k]["findings"]["occlusion_ptp_db"]))

    lead = _pick("matrice4e")          # 깨끗한 메쉬 · 1차 실측 표적
    second = _pick("mini5pro")         # ⚠ 겹침 9.12 % 남아 있음
    print(f"  대표 칸(헤드라인) {lead}   ·   두 번째 {second}")
    fig1_spectrogram(res, npz, lead)
    fig2_occlusion(res, npz, lead)
    fig3_summary(res)
    # 두 번째 기체도 같은 그림으로 남긴다(파일명 b)
    import builtins
    _orig = globals()["_save"]
    def _save_b(fig, stem):
        _orig(fig, stem + "b")
    globals()["_save"] = _save_b
    fig1_spectrogram(res, npz, second)
    fig2_occlusion(res, npz, second)
    globals()["_save"] = _orig

    print("\n═══ 판정 요약 ═══")
    for k in cells:
        c = res["cells"][k]
        f = c["findings"]
        print(f"  {c['name']:16s} {c['aspect']:11s}  "
              f"가림 레벨 {f['occlusion_level_db']:+7.2f} dB · 깊이 {f['occlusion_ptp_db']:+7.2f} dB  |  "
              f"반창상관 잠김 {f['rpm_spread_makes_it_time_varying']['locked_half_corr']:.4f} "
              f"→ 흩어짐 {f['rpm_spread_makes_it_time_varying']['spread_half_corr']:.4f}")


if __name__ == "__main__":
    main()
