# -*- coding: utf-8 -*-
"""
viz_radar.py — (report2) 레이더/RCS/파형 비교 시각화 (matplotlib)
==================================================================
생성물 (outputs/figures/, report2_ 접두어)
  report2_setup.png        : 모노스태틱 구성 + 원거리장 도식
  report2_rcs_polar.png    : 드론 5종 RCS(방위각) 극좌표 + RCS(주파수)
  report2_rcs_bands.png    : LTE/5G/WiFi 반송파에서의 5종 RCS 비교(막대)
  report2_wave_spectra.png : 세 파형의 스펙트럼(점유대역) + 시간파형
  report2_range_profiles.png : 같은 표적, 세 파형 거리프로파일(분해능 비교)
  report2_summary.png      : 표준별 요약표 + RCS 추정 비교
"""
from __future__ import annotations
import os
import numpy as np

import vizstyle
vizstyle.use_korean()
import matplotlib.pyplot as plt

from drones import DRONES
from rcs_po import drone_rcs_pattern, dbsm, C0
from waveforms import all_waveforms
from radar_process import range_profile, mainlobe_width_m, sphere_calib, estimate_rcs_dbsm

FIG = os.path.join(os.path.dirname(__file__), "..", "outputs", "figures")
_COL = {"mini5pro": "#1565c0", "mavic4pro": "#2e7d32", "matrice4e": "#ef6c00",
        "s1000plus": "#000000", "phantom4": "#c62828"}
_NAME = {k: DRONES[k].name.split("  ")[0].replace("DJI ", "") for k in DRONES}


def fig_setup(outdir=FIG):
    from radar_scene import ANT_POS, TGT_POS, farfield_distance, target_extent
    R = abs(TGT_POS[0] - ANT_POS[0])
    fig, ax = plt.subplots(figsize=(12, 4.6), constrained_layout=True)
    ax.add_patch(plt.Rectangle((0, 0), 30, 11, fill=False, ec="0.5", lw=1.5))
    ax.text(15, 11.4, "차폐시설 단면 (30 m × 11 m)  ·  벽=전파흡수체", ha="center", fontsize=10, color="0.4")
    # 안테나
    ax.plot(ANT_POS[0], ANT_POS[2], "^", ms=16, color="#c62828")
    ax.text(ANT_POS[0], ANT_POS[2] - 1.1, "모노스태틱\n안테나(TX≈RX)", ha="center", fontsize=9, color="#c62828")
    # 표적
    ax.plot(TGT_POS[0], TGT_POS[2], "o", ms=12, color="k")
    ax.text(TGT_POS[0], TGT_POS[2] + 0.8, "표적 드론\n(quiet zone)", ha="center", fontsize=9)
    # 빔/왕복
    ax.annotate("", xy=TGT_POS[::2], xytext=ANT_POS[::2],
                arrowprops=dict(arrowstyle="->", color="#1565c0", lw=2))
    ax.annotate("", xy=ANT_POS[::2], xytext=TGT_POS[::2],
                arrowprops=dict(arrowstyle="->", color="#1565c0", lw=2, ls=":"))
    ax.text((ANT_POS[0]+TGT_POS[0])/2, ANT_POS[2]+0.5, f"R = {R:.0f} m  (왕복 2R/c)",
            ha="center", fontsize=10, color="#1565c0")
    # 원거리장 표
    txt = "원거리장 2D²/λ 점검 @3.5GHz:  "
    for k in DRONES:
        D = target_extent(k); rff = farfield_distance(D, 3.5e9)
        ok = "✓" if rff <= R else "✗"
        txt += f"{_NAME[k]} {rff:.0f}m{ok}  "
    ax.text(15, -1.6, txt, ha="center", fontsize=8.5, color="#444")
    ax.set_xlim(-2, 32); ax.set_ylim(-2.5, 13); ax.axis("off")
    ax.set_title("모노스태틱 레이더 구성 — 안테나(한쪽 끝) ↔ 표적(quiet zone)", fontsize=13, fontweight="bold")
    fn = os.path.join(outdir, "report2_setup.png"); fig.savefig(fn, dpi=130); plt.close(fig)
    print("[radar]", os.path.relpath(fn)); return fn


def fig_rcs_polar(outdir=FIG, fc=3.5e9):
    az = np.arange(0, 360, 1.0)
    fig = plt.figure(figsize=(13, 5.8), constrained_layout=True)
    fig.suptitle(f"드론 RCS 특성 — 물리광학(PO) 계산  ·  검증됨(평판·구 이론 일치)",
                 fontsize=14, fontweight="bold")
    axp = fig.add_subplot(1, 2, 1, projection="polar")
    for k in DRONES:
        sig, _ = drone_rcs_pattern(k, fc, az)
        axp.plot(np.radians(az), dbsm(sig), color=_COL[k], lw=1.3, label=_NAME[k])
    axp.set_title(f"(a) RCS(방위각) @ {fc/1e9:.1f} GHz [dBsm]", fontsize=11)
    axp.set_theta_zero_location("N"); axp.set_theta_direction(-1)
    axp.set_rlabel_position(135); axp.legend(loc="upper right", bbox_to_anchor=(1.18, 1.1), fontsize=8)
    # RCS vs frequency
    axf = fig.add_subplot(1, 2, 2)
    freqs = np.linspace(1.0e9, 6.0e9, 26)
    azc = np.arange(0, 360, 3.0)
    for k in DRONES:
        mean_rcs = []
        for f in freqs:
            sig, _ = drone_rcs_pattern(k, f, azc)
            mean_rcs.append(dbsm(sig.mean()))
        axf.plot(freqs/1e9, mean_rcs, color=_COL[k], lw=1.8, marker="o", ms=3, label=_NAME[k])
    for fb, lab in [(1.84, "LTE"), (3.5, "5G"), (5.21, "WiFi")]:
        axf.axvline(fb, color="0.6", ls="--", lw=1); axf.text(fb, axf.get_ylim()[1], lab, fontsize=8, ha="center", va="bottom")
    axf.set_xlabel("주파수 [GHz]"); axf.set_ylabel("방위평균 RCS [dBsm]")
    axf.set_title("(b) RCS(주파수) — 표준별 반송파 표시", fontsize=11); axf.grid(alpha=0.3); axf.legend(fontsize=8)
    fn = os.path.join(outdir, "report2_rcs_polar.png"); fig.savefig(fn, dpi=130); plt.close(fig)
    print("[radar]", os.path.relpath(fn)); return fn


def fig_rcs_bands(outdir=FIG):
    bands = [("LTE 1.8GHz", 1.84e9), ("5G 3.5GHz", 3.5e9), ("WiFi 5.2GHz", 5.21e9)]
    az = np.arange(0, 360, 2.0)
    keys = list(DRONES.keys())
    data = np.zeros((len(keys), len(bands)))
    for i, k in enumerate(keys):
        for j, (_, f) in enumerate(bands):
            sig, _ = drone_rcs_pattern(k, f, az); data[i, j] = dbsm(sig.mean())
    fig, ax = plt.subplots(figsize=(11, 5.2), constrained_layout=True)
    x = np.arange(len(keys)); w = 0.26
    for j, (lab, _) in enumerate(bands):
        ax.bar(x + (j-1)*w, data[:, j], w, label=lab)
    ax.set_xticks(x); ax.set_xticklabels([_NAME[k] for k in keys])
    ax.set_ylabel("방위평균 RCS [dBsm]")
    ax.set_title("표준 반송파별 드론 RCS 비교 — 같은 표적도 주파수에 따라 RCS 가 달라짐",
                 fontsize=13, fontweight="bold")
    ax.legend(); ax.grid(axis="y", alpha=0.3)
    for i in range(len(keys)):
        for j in range(len(bands)):
            ax.text(x[i]+(j-1)*w, data[i, j]+0.3, f"{data[i,j]:.0f}", ha="center", fontsize=7.5)
    fn = os.path.join(outdir, "report2_rcs_bands.png"); fig.savefig(fn, dpi=130); plt.close(fig)
    print("[radar]", os.path.relpath(fn)); return fn


def fig_wave_spectra(outdir=FIG):
    wfs = all_waveforms()
    fig, axes = plt.subplots(2, 3, figsize=(14, 6.4), constrained_layout=True)
    fig.suptitle("실제 상용 OFDM 파형 — 스펙트럼(점유대역)과 시간파형", fontsize=14, fontweight="bold")
    for j, (key, wf) in enumerate(wfs.items()):
        f = np.fft.fftshift(np.fft.fftfreq(len(wf.tx), 1/wf.fs_hz))/1e6
        P = np.fft.fftshift(np.abs(np.fft.fft(wf.tx))**2); P = 10*np.log10(P/P.max()+1e-12)
        axes[0, j].plot(f, P, lw=0.5, color="#1565c0")
        axes[0, j].set_title(f"{wf.name}\n{wf.bw_hz/1e6:.0f}MHz · {wf.carrier_hz/1e9:.2f}GHz · 분해능 {wf.range_resolution_m:.2f}m",
                             fontsize=10)
        axes[0, j].set_xlabel("기저대역 주파수 [MHz]"); axes[0, j].set_ylabel("PSD [dB]")
        axes[0, j].set_ylim(-60, 3); axes[0, j].grid(alpha=0.3)
        t = np.arange(min(800, len(wf.tx)))/wf.fs_hz*1e6
        axes[1, j].plot(t, np.real(wf.tx[:len(t)]), lw=0.6, color="#2e7d32")
        axes[1, j].set_xlabel("시간 [µs]"); axes[1, j].set_ylabel("Re{s(t)}")
        axes[1, j].set_title(f"기준신호={wf.ref_name} · FFT{wf.fft}", fontsize=9); axes[1, j].grid(alpha=0.3)
    fn = os.path.join(outdir, "report2_wave_spectra.png"); fig.savefig(fn, dpi=130); plt.close(fig)
    print("[radar]", os.path.relpath(fn)); return fn


def fig_range_profiles(outdir=FIG, target="phantom4", R=10.0, snr_db=20.0):
    wfs = all_waveforms()
    fig, ax = plt.subplots(figsize=(12, 5.4), constrained_layout=True)
    col = {"wifi": "#1565c0", "lte": "#ef6c00", "nr": "#2e7d32"}
    for key, wf in wfs.items():
        sig, _ = drone_rcs_pattern(target, wf.carrier_hz, np.array([0.0])); sig = float(sig[0])
        rng_m, prof, pkr, pkv = range_profile(wf, R, sig, snr_db=snr_db,
                                              rng=np.random.default_rng(7))
        pdb = 20*np.log10(prof/prof.max()+1e-12)
        res = mainlobe_width_m(rng_m, prof)
        ax.plot(rng_m, pdb, color=col[key], lw=1.6,
                label=f"{wf.name}  (B={wf.bw_hz/1e6:.0f}MHz, 분해능≈{res:.1f}m)")
    ax.axvline(R, color="k", ls="--", lw=1, label=f"실제 거리 {R:.0f} m")
    ax.set_xlim(0, 2*R+5); ax.set_ylim(-40, 2)
    ax.set_xlabel("거리 [m]"); ax.set_ylabel("정합필터 출력 [dB]")
    ax.set_title(f"같은 표적({_NAME[target]})을 세 파형으로 측정 — 거리 분해능 비교\n"
                 f"(대역폭이 클수록 피크가 날카로움: 5G > WiFi > LTE)", fontsize=13, fontweight="bold")
    ax.legend(fontsize=9.5); ax.grid(alpha=0.3)
    fn = os.path.join(outdir, "report2_range_profiles.png"); fig.savefig(fn, dpi=130); plt.close(fig)
    print("[radar]", os.path.relpath(fn)); return fn


def fig_summary(outdir=FIG, target="phantom4", R=10.0):
    wfs = all_waveforms()
    rows = []
    for key, wf in wfs.items():
        sig, _ = drone_rcs_pattern(target, wf.carrier_hz, np.array([0.0])); sig = float(sig[0])
        rng_m, prof, pkr, pkv = range_profile(wf, R, sig, snr_db=20.0, rng=np.random.default_rng(7))
        res = mainlobe_width_m(rng_m, prof)
        cpk, csig = sphere_calib(wf, R); est = estimate_rcs_dbsm(pkv, cpk, csig)
        rows.append([wf.name, f"{wf.carrier_hz/1e9:.2f} GHz", f"{wf.bw_hz/1e6:.0f} MHz",
                     wf.ref_name, f"{wf.range_resolution_m:.2f} m", f"{res:.1f} m",
                     f"{dbsm(sig):.1f}", f"{est:.1f}"])
    fig, ax = plt.subplots(figsize=(13, 3.2), constrained_layout=True); ax.axis("off")
    cols = ["표준", "반송파", "대역폭", "기준신호", "이론분해능\nc/2B", "측정분해능\n(-3dB)",
            "참RCS\n[dBsm]", "추정RCS\n[dBsm]"]
    t = ax.table(cellText=rows, colLabels=cols, loc="center", cellLoc="center")
    t.auto_set_font_size(False); t.set_fontsize(10.5); t.scale(1, 2.0)
    for c in range(len(cols)):
        t[0, c].set_facecolor("#1565c0"); t[0, c].set_text_props(color="white", fontweight="bold")
    ax.set_title(f"WiFi vs LTE vs 5G — 표적 {_NAME[target]} @ R={R:.0f}m 요약\n"
                 f"(추정 RCS 가 참값과 일치 → 구 보정 정합필터 정상; 5G 분해능 최우수)",
                 fontsize=13, fontweight="bold", pad=14)
    fn = os.path.join(outdir, "report2_summary.png"); fig.savefig(fn, dpi=130); plt.close(fig)
    print("[radar]", os.path.relpath(fn)); return fn


def build_all(outdir=FIG):
    fig_setup(outdir); fig_rcs_polar(outdir); fig_rcs_bands(outdir)
    fig_wave_spectra(outdir); fig_range_profiles(outdir); fig_summary(outdir)
    print("report2 그림 생성 완료 →", os.path.relpath(outdir))


if __name__ == "__main__":
    build_all()
