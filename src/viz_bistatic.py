# -*- coding: utf-8 -*-
"""
viz_bistatic.py — (report4) 바이스태틱 패시브 레이더 시각화
============================================================
생성물 (outputs/figures/, report4_ 접두어)
  report4_geometry.png   : 바이스태틱 3D 장면 (TX·RX·베이스라인·드론메쉬·등Rb 타원·속도벡터)
  report4_rangedoppler.png : 거리-도플러 맵 ECA 전/후 (직접파·클러터 제거 → 표적 검출 + CFAR)
  report4_detection.png  : 검출 성능 — 파형별/점유별 Pd vs SNR (왜 SSB만으론 못 잡나)
"""
from __future__ import annotations
import os
import numpy as np

import vizstyle
vizstyle.use_korean()
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection, Line3DCollection

from drones import DRONES, build_drone, drone_colors
from waveforms import all_waveforms, lte_downlink, nr_downlink, wifi_80211ac
from bistatic_scene import bistatic_params, C0
from passive_process import make_cpi, eca, range_doppler, ca_cfar_2d, peak_detection

FIG = os.path.join(os.path.dirname(__file__), "..", "outputs", "figures")
_NAME = {k: DRONES[k].name.replace("DJI ", "") for k in DRONES}

# 대표 시나리오: 기지국(TX) 옥상, 지상 수신기(RX), 드론이 감시영역 비행
TX = (0.0, 250.0, 35.0)       # 기지국(illuminator)
RX = (0.0, 0.0, 6.0)          # 패시브 수신기
TGT = (90.0, 110.0, 55.0)     # 표적 드론
VEL = (14.0, -6.0, 0.0)       # 표적 속도


def _scaled_mesh(mesh, target_extent, center):
    V = np.array(mesh.v); b0, b1 = V.min(0), V.max(0); c = (b0 + b1) / 2
    s = target_extent / max((b1 - b0).max(), 1e-9)
    return (V - c) * s + np.asarray(center)


# --------------------------------------------------------------------------- #
#  (1) 바이스태틱 3D 기하
# --------------------------------------------------------------------------- #
def fig_geometry(outdir=FIG, target="mavic4pro", fc=3.5e9):
    p = bistatic_params(TX, RX, TGT, VEL, fc)
    fig = plt.figure(figsize=(13, 6.4), constrained_layout=True)
    fig.suptitle("바이스태틱 패시브 레이더 기하 — 기지국(TX, illuminator) ↔ 표적 ↔ 수신기(RX)",
                 fontsize=14, fontweight="bold")
    ax = fig.add_subplot(1, 2, 1, projection="3d")
    tx, rx, tg = np.array(TX), np.array(RX), np.array(TGT)
    # 지면 격자
    for gx in range(0, 161, 40):
        ax.plot([gx, gx], [0, 260], [0, 0], color="0.9", lw=0.5)
    for gy in range(0, 261, 40):
        ax.plot([0, 160], [gy, gy], [0, 0], color="0.9", lw=0.5)
    # TX 마스트, RX
    ax.plot([tx[0], tx[0]], [tx[1], tx[1]], [0, tx[2]], color="0.4", lw=3)
    ax.scatter(*tx, s=160, marker="^", color="#ef6c00", depthshade=False)
    ax.text(tx[0], tx[1], tx[2] + 12, "기지국 TX\n(5G/LTE)", color="#ef6c00", fontsize=9, ha="center")
    ax.scatter(*rx, s=140, marker="v", color="#1565c0", depthshade=False)
    ax.text(rx[0], rx[1], rx[2] + 12, "패시브 수신기 RX", color="#1565c0", fontsize=9, ha="center")
    # 경로 R1(TX→표적), R2(표적→RX), 베이스라인 L(직접파)
    ax.add_collection3d(Line3DCollection([[tx, tg]], colors="#ef6c00", linewidths=1.8, linestyles="--"))
    ax.add_collection3d(Line3DCollection([[tg, rx]], colors="#2e7d32", linewidths=2.0))
    ax.add_collection3d(Line3DCollection([[tx, rx]], colors="0.5", linewidths=1.2, linestyles=":"))
    ax.text(*(0.5 * (tx + tg) + [0, 0, 8]), "R1", color="#ef6c00", fontsize=9)
    ax.text(*(0.5 * (tg + rx) + [0, 0, 8]), "R2", color="#2e7d32", fontsize=9)
    ax.text(*(0.5 * (tx + rx) + [6, 0, 6]), "베이스라인 L (직접파)", color="0.45", fontsize=8)
    # 드론 메쉬(확대) + 속도벡터
    spec = DRONES[target]; mesh = build_drone(spec)
    Vs = _scaled_mesh(mesh, 26.0, tg)
    tris = [[Vs[a], Vs[b], Vs[c]] for (a, b, c) in mesh.f]
    dc = drone_colors(spec)
    ax.add_collection3d(Poly3DCollection(tris, facecolors=[dc.get(g, (.6, .6, .6)) for g in mesh.g],
                                         edgecolors=(0, 0, 0, 0.2), linewidths=0.1))
    ax.quiver(*tg, *np.array(VEL) * 2.2, color="#c62828", lw=2.5, arrow_length_ratio=0.3)
    ax.text(tg[0] + 22, tg[1], tg[2] + 18, f"표적 {_NAME[target]}\nv={np.linalg.norm(VEL):.0f} m/s",
            color="k", fontsize=9)
    ax.set_xlim(0, 160); ax.set_ylim(0, 260); ax.set_zlim(0, 90)
    try: ax.set_box_aspect((160, 260, 90))
    except Exception: pass
    ax.set_xlabel("x [m]"); ax.set_ylabel("y [m]"); ax.set_zlabel("z [m]")
    ax.view_init(elev=24, azim=-72); ax.tick_params(labelsize=7)

    # (우) 평면 등Rb 타원 + 측정량
    axp = fig.add_subplot(1, 2, 2); axp.set_aspect("equal")
    axp.plot(tx[0], tx[1], "^", ms=12, color="#ef6c00"); axp.text(tx[0]+4, tx[1], "TX", color="#ef6c00")
    axp.plot(rx[0], rx[1], "v", ms=12, color="#1565c0"); axp.text(rx[0]+4, rx[1], "RX", color="#1565c0")
    axp.plot(tg[0], tg[1], "o", ms=9, color="k"); axp.text(tg[0]+4, tg[1], "표적", color="k")
    # 등Rb 타원(TX,RX 초점, 합=R1+R2): 점들
    fa, fb = tx[:2], rx[:2]; c2 = np.linalg.norm(fa - fb) / 2; a_e = (p["R1"] + p["R2"]) / 2
    b_e = np.sqrt(max(a_e**2 - c2**2, 0)); mid = (fa + fb) / 2
    ang = np.arctan2((fb - fa)[1], (fb - fa)[0]); th = np.linspace(0, 2*np.pi, 200)
    ex = a_e*np.cos(th); ey = b_e*np.sin(th)
    ER = np.array([[np.cos(ang), -np.sin(ang)], [np.sin(ang), np.cos(ang)]])
    ell = (ER @ np.vstack([ex, ey])).T + mid
    axp.plot(ell[:, 0], ell[:, 1], color="#7b1fa2", lw=1.3, label="등Rb 타원(한 수신기로 얻는 위치 모호)")
    axp.plot([fa[0], tg[0]], [fa[1], tg[1]], "--", color="#ef6c00", lw=1)
    axp.plot([tg[0], fb[0]], [tg[1], fb[1]], "-", color="#2e7d32", lw=1.5)
    axp.plot([fa[0], fb[0]], [fa[1], fb[1]], ":", color="0.5", lw=1)
    axp.set_title(f"평면도 · L={p['L']:.0f}m  Rb={p['Rb']:.0f}m  지연={p['tau']*1e9:.0f}ns  "
                  f"f_d={p['fd']:+.0f}Hz  바이각={p['beta']:.0f}°", fontsize=10)
    axp.set_xlabel("x [m]"); axp.set_ylabel("y [m]"); axp.legend(fontsize=8, loc="upper right")
    axp.grid(alpha=0.3)
    fn = os.path.join(outdir, "report4_geometry.png"); fig.savefig(fn, dpi=130); plt.close(fig)
    print("[bist]", os.path.relpath(fn)); return fn


# --------------------------------------------------------------------------- #
#  (2) 거리-도플러 맵 ECA 전/후
# --------------------------------------------------------------------------- #
def fig_rangedoppler(outdir=FIG, fc=3.5e9, M=48):
    wf = nr_downlink(occupancy="G3")               # 5G n78 100MHz (광대역·고분해능)
    fs = wf.fs_hz; ref_frame = wf.tx
    p = bistatic_params(TX, RX, TGT, VEL, fc)
    tau, fd = p["tau"], p["fd"]
    n_range = int(min(len(ref_frame), 900 / (C0 / fs)))
    surv, ref = make_cpi(ref_frame, M, fs, tau, fd, a_tgt=1.0, dpi_amp=60.0,
                         clutter=((0.0, 10.0), (30e-9, 6.0), (90e-9, 4.0)),
                         snr_db=14.0, rng=np.random.default_rng(3))
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.6), constrained_layout=True)
    prf = fs / (len(ref) // M)
    fig.suptitle(f"거리-도플러 맵 (5G NR 100MHz) — ECA 클러터제거 전/후  ·  PRF={prf:.0f}Hz "
                 f"(±{prf/2:.0f}Hz), 거리분해능 {C0/wf.bw_hz:.1f}m, 도플러분해능 {prf/M:.1f}Hz",
                 fontsize=13, fontweight="bold")
    for ax, (tag, sig) in zip(axes, [("ECA 전 — 직접파/클러터가 지배", surv),
                                     ("ECA 후 — 표적 드러남 + CFAR 검출", eca(surv, ref, 40))]):
        Rb, f_d, rd = range_doppler(sig, ref, fs, M, n_range=n_range)
        rdb = 20 * np.log10(rd / rd.max() + 1e-9)
        im = ax.pcolormesh(Rb, f_d, rdb, cmap="turbo", vmin=-50, vmax=0, shading="auto")
        ax.axhline(fd, color="w", ls=":", lw=0.8, alpha=0.6)
        ax.plot(p["Rb"], fd, "o", mfc="none", mec="w", ms=14, mew=1.5)  # 참 표적
        if "후" in tag:
            det, _, _ = ca_cfar_2d(rd, pfa=1e-4)
            pk = peak_detection(Rb, f_d, rd, det)
            if pk:
                ax.plot(pk["Rb"], pk["fd"], "x", color="r", ms=12, mew=2.5,
                        label=f"검출 ({pk['Rb']:.0f}m, {pk['fd']:+.0f}Hz)")
                ax.legend(fontsize=9, loc="upper right")
        ax.set_xlabel("바이스태틱 거리 Rb [m]"); ax.set_ylabel("도플러 f_d [Hz]")
        ax.set_title(tag, fontsize=10.5)
        fig.colorbar(im, ax=ax, fraction=0.046, label="정규화 [dB]")
    axes[0].text(0.02, 0.96, f"참 표적 ○ (Rb={p['Rb']:.0f}m, f_d={fd:+.0f}Hz)", transform=axes[0].transAxes,
                 fontsize=8.5, color="w", va="top")
    fn = os.path.join(outdir, "report4_rangedoppler.png"); fig.savefig(fn, dpi=130); plt.close(fig)
    print("[bist]", os.path.relpath(fn)); return fn


# --------------------------------------------------------------------------- #
#  (3) 검출 성능 — 파형별·점유별 Pd vs SNR
# --------------------------------------------------------------------------- #
def _pd_curve(wf, fc, snr_list, T_cpi=0.035, K=8, pfa=1e-3, seed0=0):
    """파형 1개의 Pd vs (표적 per-sample 에코 SNR[dB]).
    고정 CPI 시간 T_cpi → 도플러분해능(1/T_cpi)을 파형 무관하게 균일화(WiFi 거친 Δf_d 혼선 제거).
    절대 잡음(σ²=1), 표적은 에코 SNR 로 진폭 결정 → 파형/점유의 '처리이득' 차이가 Pd 로 드러남.
    검출 = 표적셀(±1) 전력 > CFAR 임계(타겟-free 영역 잡음 기반, 주어진 Pfa)."""
    fs = wf.fs_hz; ref_frame = wf.tx; Lf = len(ref_frame)
    prf = fs / Lf; M = max(10, int(round(T_cpi * prf)))
    p = bistatic_params(TX, RX, TGT, VEL, fc); tau, fd = p["tau"], p["fd"]
    n_range = int(min(Lf, 900 / (C0 / fs)))
    pds = []
    for si, sdb in enumerate(snr_list):
        a = 10.0 ** (sdb / 20.0)                             # 에코 진폭(절대, 잡음σ²=1) — 모드 무관 동일
        #   → 점유가 낮으면(희소·협대역) 처리이득↓ 로 같은 진폭에서도 Pd↓ (SSB 에너지 부족이 드러남)
        hit = 0
        for k in range(K):
            surv, ref = make_cpi(ref_frame, M, fs, tau, fd, a_tgt=a, dpi_amp=40.0,
                                 clutter=((0.0, 8.0), (40e-9, 4.0)),
                                 abs_noise=True, noise_var=1.0,
                                 rng=np.random.default_rng(seed0 + si * 100 + k))
            Rb, f_d, rd = range_doppler(eca(surv, ref, 36), ref, fs, M, n_range=n_range)
            ri = int(np.argmin(np.abs(Rb - p["Rb"]))); di = int(np.argmin(np.abs(f_d - fd)))
            cell = rd[max(0, di-1):di+2, max(0, ri-1):ri+2].max() ** 2     # 표적셀 전력
            mask = np.ones_like(rd, bool); zd = int(np.argmin(np.abs(f_d)))
            mask[max(0, zd-1):zd+2, :] = False                            # 0-도플러 제외
            mask[max(0, di-3):di+4, max(0, ri-3):ri+4] = False            # 표적 근방 제외
            noise_pow = float(np.mean(rd[mask] ** 2)) + 1e-30
            thr = -noise_pow * np.log(pfa)                                # 지수꼬리 CFAR 임계
            hit += int(cell > thr)
        pds.append(hit / K)
    return pds, M


def fig_detection(outdir=FIG, fc=3.5e9, T_cpi=0.035, K=8):
    snr_list = list(range(-72, -27, 4))            # 표적 에코 진폭[dB] (동일 물리 에코, 잡음 고정)
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.2), constrained_layout=True)
    fig.suptitle("검출 성능 Pd vs 에코 진폭 — 파형/점유가 탐지를 좌우 (왜 한가한 5G(SSB)로는 못 잡나)\n"
                 f"같은 물리 에코·고정 잡음 / CPI {T_cpi*1e3:.0f}ms(도플러분해능 {1/T_cpi:.0f}Hz 균일) / CFAR Pfa=1e-3",
                 fontsize=12.5, fontweight="bold")
    col = {"wifi": "#1565c0", "lte": "#ef6c00", "nr": "#2e7d32"}
    for key, wf in all_waveforms("G3").items():
        pd, M = _pd_curve(wf, wf.carrier_hz, snr_list, T_cpi, K)
        axes[0].plot(snr_list, pd, "o-", color=col[key], lw=1.8,
                     label=f"{wf.name} (B={wf.bw_hz/1e6:.0f}MHz, M={M})")
    axes[0].set_title("(a) 파형별 (G3 풀로드) — 대역폭↑ → 처리이득↑ → 같은 SNR서 Pd↑", fontsize=10.5)
    for mode, c in [("G1", "#c62828"), ("G2", "#ef6c00"), ("G3", "#2e7d32")]:
        wf = nr_downlink(occupancy=mode)
        pd, M = _pd_curve(wf, wf.carrier_hz, snr_list, T_cpi, K)
        axes[1].plot(snr_list, pd, "o-", color=c, lw=1.8,
                     label=f"5G {mode} (기준 {wf.ref_name}, 점유 {wf.occupancy_frac*100:.0f}%)")
    axes[1].set_title("(b) 5G 점유모드별 — G1(SSB·희소·협대역)은 처리이득↓로 탐지 불리", fontsize=10.5)
    for ax in axes:
        ax.axhline(0.9, color="0.6", ls="--", lw=0.8); ax.set_ylim(-0.03, 1.03)
        ax.set_xlabel("표적 에코 진폭 [dB] (절대·잡음 고정)"); ax.set_ylabel("검출확률 Pd")
        ax.grid(alpha=0.3); ax.legend(fontsize=8.5, loc="best")
    fn = os.path.join(outdir, "report4_detection.png"); fig.savefig(fn, dpi=130); plt.close(fig)
    print("[bist]", os.path.relpath(fn)); return fn


def build_all(outdir=FIG):
    fig_geometry(outdir)
    fig_rangedoppler(outdir)
    fig_detection(outdir)
    print("바이스태틱 시각화 완료 →", os.path.relpath(outdir))


if __name__ == "__main__":
    build_all()
