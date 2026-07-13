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
from rcs_po import drone_rcs_pattern, dbsm
from waveforms import all_waveforms
from radar_process import range_profile, mainlobe_width_m, sphere_calib, estimate_rcs_dbsm
from radar_scene import ANT_POS, TGT_POS, farfield_distance, target_extent  # sionna 지연 import 라 가벼움

FIG = os.path.join(os.path.dirname(__file__), "..", "outputs", "figures")
_COL = {"mini5pro": "#1565c0", "mavic4pro": "#2e7d32", "matrice4e": "#ef6c00",
        "s1000plus": "#000000", "phantom4": "#c62828"}
_NAME = {k: DRONES[k].name.split("  ")[0].replace("DJI ", "") for k in DRONES}


def fig_setup(outdir=FIG):
    R = abs(TGT_POS[0] - ANT_POS[0])
    fig, ax = plt.subplots(figsize=(12, 4.6), constrained_layout=True)
    ax.add_patch(plt.Rectangle((0, 0), 30, 11, fill=False, ec="0.5", lw=1.5))
    ax.text(15, 11.4, "Anechoic chamber cross-section (30 m × 11 m)  ·  walls = RF absorber", ha="center", fontsize=10, color="0.4")
    # 안테나
    ax.plot(ANT_POS[0], ANT_POS[2], "^", ms=16, color="#c62828")
    ax.text(ANT_POS[0], ANT_POS[2] - 1.1, "Monostatic\nantenna (TX≈RX)", ha="center", fontsize=9, color="#c62828")
    # 표적
    ax.plot(TGT_POS[0], TGT_POS[2], "o", ms=12, color="k")
    ax.text(TGT_POS[0], TGT_POS[2] + 0.8, "Target drone\n(quiet zone)", ha="center", fontsize=9)
    # 빔/왕복
    ax.annotate("", xy=TGT_POS[::2], xytext=ANT_POS[::2],
                arrowprops=dict(arrowstyle="->", color="#1565c0", lw=2))
    ax.annotate("", xy=ANT_POS[::2], xytext=TGT_POS[::2],
                arrowprops=dict(arrowstyle="->", color="#1565c0", lw=2, ls=":"))
    ax.text((ANT_POS[0]+TGT_POS[0])/2, ANT_POS[2]+0.5, f"R = {R:.0f} m  (round trip 2R/c)",
            ha="center", fontsize=10, color="#1565c0")
    # 원거리장 표
    txt = "Far-field 2D²/λ check @3.5GHz:  "
    for k in DRONES:
        D = target_extent(k); rff = farfield_distance(D, 3.5e9)
        ok = "○" if rff <= R else "×"        # (✓/✗ 는 NanumGothic 에 글리프가 없어 □ 로 깨짐)
        txt += f"{_NAME[k]} {rff:.0f}m{ok}  "
    ax.text(15, -1.6, txt, ha="center", fontsize=8.5, color="#444")
    ax.set_xlim(-2, 32); ax.set_ylim(-2.5, 13); ax.axis("off")
    ax.set_title("Monostatic radar setup — antenna (one end) ↔ target (quiet zone)", fontsize=13, fontweight="bold")
    fn = os.path.join(outdir, "report2_setup.png"); fig.savefig(fn, dpi=130); plt.close(fig)
    print("[radar]", os.path.relpath(fn)); return fn


def fig_rcs_polar(outdir=FIG, fc=3.5e9):
    az = np.arange(0, 360, 1.0)
    fig = plt.figure(figsize=(13, 5.8), constrained_layout=True)
    fig.suptitle("Drone RCS characteristics — physical optics (PO)  ·  validated vs plate & sphere theory",
                 fontsize=14, fontweight="bold")
    axp = fig.add_subplot(1, 2, 1, projection="polar")
    for k in DRONES:
        sig, _ = drone_rcs_pattern(k, fc, az)
        axp.plot(np.radians(az), dbsm(sig), color=_COL[k], lw=1.3, label=_NAME[k])
    axp.set_title(f"(a) RCS (azimuth) @ {fc/1e9:.1f} GHz [dBsm]", fontsize=11)
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
    axf.set_xlabel("Frequency [GHz]"); axf.set_ylabel("Azimuth-avg RCS [dBsm]")
    axf.set_title("(b) RCS (frequency) — per-standard carriers marked", fontsize=11); axf.grid(alpha=0.3); axf.legend(fontsize=8)
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
    ax.set_ylabel("Azimuth-avg RCS [dBsm]")
    ax.set_title("Drone RCS per standard carrier — RCS of the same target varies with frequency",
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
    fig.suptitle("Real commercial OFDM waveforms — spectra (occupied band) and time waveforms", fontsize=14, fontweight="bold")
    for j, (key, wf) in enumerate(wfs.items()):
        f = np.fft.fftshift(np.fft.fftfreq(len(wf.tx), 1/wf.fs_hz))/1e6
        P = np.fft.fftshift(np.abs(np.fft.fft(wf.tx))**2); P = 10*np.log10(P/P.max()+1e-12)
        axes[0, j].plot(f, P, lw=0.5, color="#1565c0")
        axes[0, j].set_title(f"{wf.name}\n{wf.bw_hz/1e6:.0f}MHz · {wf.carrier_hz/1e9:.2f}GHz · resolution {wf.range_resolution_m:.2f}m",
                             fontsize=10)
        axes[0, j].set_xlabel("Baseband frequency [MHz]"); axes[0, j].set_ylabel("PSD [dB]")
        axes[0, j].set_ylim(-60, 3); axes[0, j].grid(alpha=0.3)
        t = np.arange(min(800, len(wf.tx)))/wf.fs_hz*1e6
        axes[1, j].plot(t, np.real(wf.tx[:len(t)]), lw=0.6, color="#2e7d32")
        axes[1, j].set_xlabel("Time [µs]"); axes[1, j].set_ylabel("Re{s(t)}")
        axes[1, j].set_title(f"Reference signal={wf.ref_name} · FFT{wf.fft}", fontsize=9); axes[1, j].grid(alpha=0.3)
    fn = os.path.join(outdir, "report2_wave_spectra.png"); fig.savefig(fn, dpi=130); plt.close(fig)
    print("[radar]", os.path.relpath(fn)); return fn


def fig_range_profiles(outdir=FIG, target="mavic4pro", R=10.0, snr_db=20.0):
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
                label=f"{wf.name}  (B={wf.bw_hz/1e6:.0f}MHz, resolution≈{res:.1f}m)")
    ax.axvline(R, color="k", ls="--", lw=1, label=f"True range {R:.0f} m")
    ax.set_xlim(0, 2*R+5); ax.set_ylim(-40, 2)
    ax.set_xlabel("Range [m]"); ax.set_ylabel("Matched-filter output [dB]")
    ax.set_title(f"Same target ({_NAME[target]}) measured with three waveforms — range resolution comparison\n"
                 f"(wider bandwidth → sharper peak: 5G > WiFi > LTE)", fontsize=13, fontweight="bold")
    ax.legend(fontsize=9.5); ax.grid(alpha=0.3)
    fn = os.path.join(outdir, "report2_range_profiles.png"); fig.savefig(fn, dpi=130); plt.close(fig)
    print("[radar]", os.path.relpath(fn)); return fn


def fig_summary(outdir=FIG, target="mavic4pro", R=10.0):
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
    cols = ["Standard", "Carrier", "Channel BW", "Reference\nsignal", "Theoretical res.\nc/2·ref BW", "Measured res.\n(-3dB)",
            "True RCS\n[dBsm]", "Estimated RCS\n[dBsm]"]
    t = ax.table(cellText=rows, colLabels=cols, loc="center", cellLoc="center")
    t.auto_set_font_size(False); t.set_fontsize(10.5); t.scale(1, 2.0)
    for c in range(len(cols)):
        t[0, c].set_facecolor("#1565c0"); t[0, c].set_text_props(color="white", fontweight="bold")
    ax.set_title(f"WiFi vs LTE vs 5G — target {_NAME[target]} @ R={R:.0f}m summary\n"
                 f"(Estimated RCS matches true value → sphere-calibrated matched filter OK; 5G best resolution)",
                 fontsize=13, fontweight="bold", pad=14)
    fn = os.path.join(outdir, "report2_summary.png"); fig.savefig(fn, dpi=130); plt.close(fig)
    print("[radar]", os.path.relpath(fn)); return fn


def fig_rcs_materials(outdir=FIG, fc=3.5e9):
    """재질 가중의 효과 — 구모델(전부 PEC·내부 산란체 없음) vs 신모델(재질 |Γ| + 내부 금속).
    좌: mavic4pro 방위 패턴 비교 / 우: 5종 방위평균 막대 비교(감소량 표기)."""
    from drones import build_drone, drone_gamma_map
    from rcs_po import mesh_to_points, rcs_from_points
    az = np.arange(0, 360, 2.0)
    fig, axes = plt.subplots(1, 2, figsize=(13.6, 5.4), constrained_layout=True,
                             gridspec_kw=dict(width_ratios=[1.15, 1.0]))
    # (a) mavic4pro 패턴: 구모델 = 내부(battery/pcb) 기여 0 + 전 부위 |Γ|=1
    spec = DRONES["mavic4pro"]; mesh = build_drone(spec)
    spacing = (299792458.0 / fc) / 7.0
    g_old = {"battery": 0.0, "pcb": 0.0}                 # 나머지 그룹은 기본 1.0(PEC)
    P, N, dA, w_old = mesh_to_points(mesh, spacing, gamma=g_old)
    _, _, _, w_new = mesh_to_points(mesh, spacing, gamma=drone_gamma_map(spec))
    s_old = rcs_from_points(P, N, dA, fc, az, w=w_old)
    s_new = rcs_from_points(P, N, dA, fc, az, w=w_new)
    axes[0].plot(az, dbsm(s_old), color="0.55", lw=1.4, label="old: all-PEC, no internals")
    axes[0].plot(az, dbsm(s_new), color="#2e7d32", lw=1.8,
                 label="new: material-weighted + internal metal (battery/PCB)")
    axes[0].set_xlabel("Azimuth [deg]"); axes[0].set_ylabel("RCS [dBsm]")
    axes[0].set_title(f"(a) Mavic 4 Pro azimuth pattern @ {fc/1e9:.1f} GHz", fontsize=11)
    axes[0].grid(alpha=0.3); axes[0].legend(fontsize=9)
    # (b) 5종 방위평균 비교
    keys = list(DRONES.keys()); olds, news = [], []
    for k in keys:
        sp2 = DRONES[k]; m2 = build_drone(sp2)
        P2, N2, dA2, wo = mesh_to_points(m2, spacing, gamma=g_old)
        _, _, _, wn = mesh_to_points(m2, spacing, gamma=drone_gamma_map(sp2))
        olds.append(dbsm(rcs_from_points(P2, N2, dA2, fc, az, w=wo).mean()))
        news.append(dbsm(rcs_from_points(P2, N2, dA2, fc, az, w=wn).mean()))
    x = np.arange(len(keys)); wbar = 0.38
    axes[1].bar(x - wbar/2, olds, wbar, color="0.6", label="old (all-PEC)")
    axes[1].bar(x + wbar/2, news, wbar, color="#2e7d32", label="new (material-weighted)")
    for xi, (o, n) in enumerate(zip(olds, news)):
        axes[1].text(xi + wbar/2, n + 0.4, f"{n-o:+.1f} dB", ha="center", fontsize=8.5)
    axes[1].set_xticks(x, [_NAME[k] for k in keys], fontsize=8.5)
    axes[1].set_ylabel("Azimuth-avg RCS [dBsm]")
    axes[1].set_title("(b) Azimuth-mean per drone — plastic shell is semi-transparent to RF",
                      fontsize=10.5)
    axes[1].grid(axis="y", alpha=0.3); axes[1].legend(fontsize=9)
    fig.suptitle("Material-weighted PO — the shell reflects ~" r"$|\Gamma|\!\approx\!0.3$"
                 "; battery/motors/PCB dominate the echo",
                 fontsize=13, fontweight="bold")
    fn = os.path.join(outdir, "report2_rcs_materials.png"); fig.savefig(fn, dpi=130); plt.close(fig)
    print("[radar]", os.path.relpath(fn)); return fn


def fig_rcs_shape_ab(outdir=FIG):
    """형상 민감도 A/B — 파라메트릭 메쉬 vs **실기체 3D 스캔**(Phantom 4, CC-BY).
    두 모델 모두 PEC + 동일 부위구성(스캔엔 프로펠러·카메라가 없어 파라메트릭도 제외)으로
    맞춰 **순수 형상 차이만** 측정한다. λ=6~16cm 에선 λ/8 이하 디테일이 안 보인다는
    주장을 데이터로 검증하는 그림."""
    from drones import build_drone
    from rcs_po import mesh_to_points, rcs_from_points
    npz = os.path.join(os.path.dirname(__file__), "..", "assets", "meshes", "cad",
                       "phantom4_scan_points.npz")
    d = np.load(npz)
    Ps, Ns, dAs = d["P"].astype(float), d["N"].astype(float), d["dA"].astype(float)
    spec = DRONES["phantom4"]; mesh = build_drone(spec)
    az = np.arange(0, 360, 1.0)
    bands = [("LTE 1.84", 1.84e9), ("5G 3.5", 3.5e9), ("WiFi 5.21", 5.21e9)]
    # 비교 가능 부위만: 스캔에 없는 프로펠러/카메라(+내부 산란체)는 파라메트릭에서 제외
    g_cmp = {"prop": 0.0, "camera": 0.0, "battery": 0.0, "pcb": 0.0}

    fig, axes = plt.subplots(1, 2, figsize=(13.6, 5.4), constrained_layout=True,
                             gridspec_kw=dict(width_ratios=[1.25, 1.0]))
    fc0 = 3.5e9
    Pp, Np_, dAp, wp = mesh_to_points(mesh, (299792458.0 / fc0) / 7.0, gamma=g_cmp)
    s_par = rcs_from_points(Pp, Np_, dAp, fc0, az, w=wp)
    s_scan = rcs_from_points(Ps, Ns, dAs, fc0, az)
    # 방위 오프셋 정렬(스캔의 기수 방향은 미지 — dB 패턴 순환상관 최대점으로 정렬, 쿼드 90° 모호)
    a_p, a_s = dbsm(s_par), dbsm(s_scan)
    xc = [np.corrcoef(a_p, np.roll(a_s, k))[0, 1] for k in range(360)]
    k0 = int(np.argmax(xc))
    axes[0].plot(az, a_p, color="0.55", lw=1.5, label="parametric mesh (spec-sheet)")
    axes[0].plot(az, np.roll(a_s, k0), color="#1565c0", lw=1.6,
                 label=f"real-body 3D scan (az-aligned {k0}°)")
    axes[0].axhline(dbsm(s_par.mean()), color="0.55", ls="--", lw=1)
    axes[0].axhline(dbsm(s_scan.mean()), color="#1565c0", ls="--", lw=1)
    axes[0].set_xlabel("Azimuth [deg]"); axes[0].set_ylabel("RCS [dBsm]")
    axes[0].set_title(f"(a) Phantom 4 azimuth pattern @ {fc0/1e9:.1f} GHz — both PEC, "
                      "matched parts (no props/camera)", fontsize=10.5)
    axes[0].grid(alpha=0.3); axes[0].legend(fontsize=9, loc="lower left")
    # (b) 대역별 방위평균
    means_p, means_s = [], []
    for _, f in bands:
        Pp2, Np2, dAp2, wp2 = mesh_to_points(mesh, (299792458.0 / f) / 7.0, gamma=g_cmp)
        means_p.append(dbsm(rcs_from_points(Pp2, Np2, dAp2, f, az, w=wp2).mean()))
        means_s.append(dbsm(rcs_from_points(Ps, Ns, dAs, f, az).mean()))
    x = np.arange(len(bands)); wb = 0.38
    axes[1].bar(x - wb/2, means_p, wb, color="0.6", label="parametric")
    axes[1].bar(x + wb/2, means_s, wb, color="#1565c0", label="3D scan")
    for xi, (mp, ms) in enumerate(zip(means_p, means_s)):
        axes[1].text(xi, max(mp, ms) + 0.4, f"{ms-mp:+.1f} dB", ha="center",
                     fontsize=9.5, fontweight="bold")
    axes[1].set_xticks(x, [b[0] + " GHz" for b in bands], fontsize=9)
    axes[1].set_ylabel("Azimuth-avg RCS [dBsm]")
    axes[1].set_title("(b) Azimuth-mean per band — shape realism costs only a few dB",
                      fontsize=10.5)
    axes[1].grid(axis="y", alpha=0.3); axes[1].legend(fontsize=9)
    fig.suptitle("Shape sensitivity A/B — spec-sheet parametric mesh vs real-body 3D scan (Phantom 4)",
                 fontsize=13, fontweight="bold")
    fig.text(0.01, 0.005, "Scan: 'DJI PHANTOM 4 HI RES SCAN' by NeverDun, Thingiverse 1456295 (CC-BY)",
             fontsize=7.5, color="0.45")
    fn = os.path.join(outdir, "report2_rcs_shape_ab.png"); fig.savefig(fn, dpi=130); plt.close(fig)
    print("[radar]", os.path.relpath(fn)); return fn


def build_all(outdir=FIG):
    fig_setup(outdir); fig_rcs_polar(outdir); fig_rcs_bands(outdir)
    fig_rcs_materials(outdir); fig_rcs_shape_ab(outdir)
    fig_wave_spectra(outdir); fig_range_profiles(outdir); fig_summary(outdir)
    print("report2 그림 생성 완료 →", os.path.relpath(outdir))


if __name__ == "__main__":
    build_all()
