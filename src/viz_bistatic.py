# -*- coding: utf-8 -*-
"""
viz_bistatic.py — (report4) **무반사 챔버 내부** 바이스태틱 패시브 레이더 시각화
==================================================================================
report1~3 과 동일한 30×20×11 m 무반사 차폐시설(anechoic chamber) **안에서** 바이스태틱
패시브 레이더 실험을 구성한다(실외 기지국 시나리오가 아니라 실내 제어 측정):
  · 신호원(illuminator) 안테나 TX 와 패시브 수신 안테나 RX 를 챔버 양쪽 벽에 벌려 놓고,
  · 표적 드론이 quiet zone(중앙~안쪽)을 저속 비행한다.
  · **무반사**: 벽·천장 피라미드 흡수체가 다중경로를 억제 → 클러터는 약하고, 주된 방해는
    직접파(DPI, TX→RX 가시선). 그래서 ECA 는 주로 **직접파 제거** + 약한 잔향(흡수체 불완전·
    바닥/장비 반사, ~−25~−30 dB) 제거가 핵심이다. (실외판의 강한 지형 클러터와 대비)

생성물 (outputs/figures/, report4_ 접두어)
  report4_geometry.png   : 챔버 내부 3D 배치(TX·RX·드론·경로 R1/R2·직접파 L·등Rb 타원·속도벡터)
  report4_rangedoppler.png : 거리-도플러 맵 ECA 전/후 (직접파·잔향 제거 → 표적 검출 + CFAR)
  report4_detection.png  : 검출 성능 — 파형별/점유별 Pd vs SNR (왜 SSB만으론 못 잡나)
  report4_tracking.gif   : 드론이 챔버 안을 날며 거리-도플러 검출이 표적을 따라감

주의(챔버 스케일): 챔버는 작아서 **거리분해능(ΔRb=c/B)이 상대적으로 크다** — 5G(100MHz)≈3.1 m,
  WiFi(≈76MHz)≈4.0 m 는 챔버 안 Rb(수~수십 m)를 가르지만, LTE(18MHz)≈16.7 m 는 너무 거칠어
  표적을 직접파와 거의 구분 못 한다(아래 Pd·거리맵에서 드러남).
"""
from __future__ import annotations
import os
import numpy as np

import vizstyle
vizstyle.use_korean()
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from mpl_toolkits.mplot3d.art3d import Poly3DCollection, Line3DCollection

from drones import DRONES, build_drone, drone_colors
from waveforms import all_waveforms, lte_downlink, nr_downlink, wifi_80211ac
from bistatic_scene import bistatic_params, C0
from passive_process import make_cpi, eca, range_doppler, ca_cfar_2d, peak_detection

FIG = os.path.join(os.path.dirname(__file__), "..", "outputs", "figures")
_NAME = {k: DRONES[k].name.replace("DJI ", "") for k in DRONES}

# --- 무반사 챔버(30×20×11 m) 내부 바이스태틱 배치 ---------------------------- #
CHAMBER = (30.0, 20.0, 11.0)      # 내부 치수 W(x)·D(y)·H(z)  (report1 과 동일)
TX = (4.0, 2.5, 8.0)              # 신호원(illuminator) 안테나 — 한쪽 측벽 상단
RX = (4.0, 17.5, 6.5)            # 패시브 수신 안테나 — 반대 측벽
TGT = (21.0, 10.0, 5.5)           # 표적 드론(quiet zone)
VEL = (-3.0, 2.0, 0.5)            # 표적 속도[m/s] — 실내 저속

# 무반사 잔향 클러터(약함): (지연[s], 진폭). DPI 대비 ~−25~−30 dB 수준(dpi_amp≈55~60 기준).
#   바닥/장비 반사·흡수체 불완전에서 오는 약한 0-도플러 잔향. ECA 가 DPI 와 함께 제거한다.
CH_CLUTTER = ((8e-9, 3.0), (22e-9, 2.0), (45e-9, 1.4))


def _scaled_mesh(mesh, target_extent, center):
    V = np.array(mesh.v); b0, b1 = V.min(0), V.max(0); c = (b0 + b1) / 2
    s = target_extent / max((b1 - b0).max(), 1e-9)
    return (V - c) * s + np.asarray(center)


def _draw_chamber(ax, W, D, H):
    """3D 축에 무반사 챔버(상자)를 그린다 — 바닥 격자 + 12모서리 + 반투명 벽 + 흡수체 힌트."""
    # 바닥(옅은 면) + 격자
    ax.plot_surface(np.array([[0, W], [0, W]]), np.array([[0, 0], [D, D]]),
                    np.zeros((2, 2)), color="0.93", alpha=0.5, zorder=0, shade=False)
    for gx in range(0, int(W) + 1, 5):
        ax.plot([gx, gx], [0, D], [0, 0], color="0.8", lw=0.4)
    for gy in range(0, int(D) + 1, 5):
        ax.plot([0, W], [gy, gy], [0, 0], color="0.8", lw=0.4)
    # 8모서리 → 12에지(옅은 회색)
    c = np.array([[x, y, z] for x in (0, W) for y in (0, D) for z in (0, H)])
    E = [(0,1),(2,3),(4,5),(6,7),(0,2),(1,3),(4,6),(5,7),(0,4),(1,5),(2,6),(3,7)]
    ax.add_collection3d(Line3DCollection([[c[a], c[b]] for a, b in E],
                                         colors="0.6", linewidths=0.8))
    # 뒷벽/측벽 반투명(흡수체 라이닝 힌트)
    walls = [  # 뒷벽 x=W, 측벽 y=0, y=D
        [[W,0,0],[W,D,0],[W,D,H],[W,0,H]],
        [[0,0,0],[W,0,0],[W,0,H],[0,0,H]],
        [[0,D,0],[W,D,0],[W,D,H],[0,D,H]],
    ]
    ax.add_collection3d(Poly3DCollection(walls, facecolors="#e8eef5", edgecolors="none", alpha=0.10))
    # 뒷벽 흡수체 피라미드 힌트(몇 개만)
    for yy in np.linspace(2, D - 2, 6):
        for zz in np.linspace(1.5, H - 1.5, 4):
            ax.plot([W, W - 0.7], [yy, yy], [zz, zz], color="#b7c4d6", lw=0.6)
    ax.text(W * 0.5, D * 0.5, H + 0.6, "무반사 챔버 30×20×11 m", color="0.4",
            fontsize=8, ha="center")


def _draw_chamber_plan(ax, W, D):
    """평면도에 챔버 바닥 사각형 + 흡수체 라이닝 힌트."""
    ax.add_patch(plt.Rectangle((0, 0), W, D, fill=False, edgecolor="0.5", lw=1.4))
    ax.add_patch(plt.Rectangle((0, 0), W, D, facecolor="#eef2f7", edgecolor="none", zorder=0))
    # 4면 흡수체 해치(짧은 빗금)
    for yy in np.linspace(1, D - 1, 12):
        ax.plot([0, 0.5], [yy, yy], color="#c2ccdb", lw=0.6)
        ax.plot([W, W - 0.5], [yy, yy], color="#c2ccdb", lw=0.6)
    for xx in np.linspace(1, W - 1, 16):
        ax.plot([xx, xx], [0, 0.5], color="#c2ccdb", lw=0.6)
        ax.plot([xx, xx], [D, D - 0.5], color="#c2ccdb", lw=0.6)


# --------------------------------------------------------------------------- #
#  (1) 챔버 내부 바이스태틱 3D 기하
# --------------------------------------------------------------------------- #
def fig_geometry(outdir=FIG, target="mavic4pro", fc=3.5e9):
    p = bistatic_params(TX, RX, TGT, VEL, fc)
    fig = plt.figure(figsize=(13, 6.4), constrained_layout=True)
    fig.suptitle("무반사 챔버 내부 바이스태틱 패시브 레이더 — 신호원(TX) ↔ 표적 드론 ↔ 패시브 수신기(RX)",
                 fontsize=14, fontweight="bold")
    ax = fig.add_subplot(1, 2, 1, projection="3d")
    tx, rx, tg = np.array(TX), np.array(RX), np.array(TGT)
    W, D, H = CHAMBER
    _draw_chamber(ax, W, D, H)
    # TX 마스트, RX
    ax.plot([tx[0], tx[0]], [tx[1], tx[1]], [0, tx[2]], color="0.4", lw=2)
    ax.scatter(*tx, s=150, marker="^", color="#ef6c00", depthshade=False)
    ax.text(tx[0], tx[1] - 1.5, tx[2] + 1.0, "신호원 TX\n(WiFi/5G)", color="#ef6c00", fontsize=9, ha="center")
    ax.plot([rx[0], rx[0]], [rx[1], rx[1]], [0, rx[2]], color="0.4", lw=2)
    ax.scatter(*rx, s=140, marker="v", color="#1565c0", depthshade=False)
    ax.text(rx[0], rx[1] + 1.5, rx[2] + 1.0, "패시브 수신기 RX", color="#1565c0", fontsize=9, ha="center")
    # 경로 R1(TX→표적), R2(표적→RX), 직접파 L
    ax.add_collection3d(Line3DCollection([[tx, tg]], colors="#ef6c00", linewidths=1.8, linestyles="--"))
    ax.add_collection3d(Line3DCollection([[tg, rx]], colors="#2e7d32", linewidths=2.0))
    ax.add_collection3d(Line3DCollection([[tx, rx]], colors="#c62828", linewidths=1.2, linestyles=":"))
    ax.text(*(0.5 * (tx + tg) + [0, 0, 0.8]), "R1", color="#ef6c00", fontsize=9)
    ax.text(*(0.5 * (tg + rx) + [0, 0, 0.8]), "R2", color="#2e7d32", fontsize=9)
    ax.text(*(0.5 * (tx + rx) + [0.5, 0, 0.6]), "직접파 L(DPI)", color="#c62828", fontsize=8)
    # 드론 메쉬(확대) + 속도벡터
    spec = DRONES[target]; mesh = build_drone(spec)
    Vs = _scaled_mesh(mesh, 2.6, tg)
    tris = [[Vs[a], Vs[b], Vs[c]] for (a, b, c) in mesh.f]
    dc = drone_colors(spec)
    ax.add_collection3d(Poly3DCollection(tris, facecolors=[dc.get(g, (.6, .6, .6)) for g in mesh.g],
                                         edgecolors=(0, 0, 0, 0.2), linewidths=0.1))
    ax.quiver(*tg, *np.array(VEL) * 1.4, color="#c62828", lw=2.5, arrow_length_ratio=0.3)
    ax.text(tg[0] + 2.5, tg[1], tg[2] + 2.0, f"표적 {_NAME[target]}\nv={np.linalg.norm(VEL):.1f} m/s",
            color="k", fontsize=9)
    ax.set_xlim(0, W); ax.set_ylim(0, D); ax.set_zlim(0, H)
    try: ax.set_box_aspect((W, D, H))
    except Exception: pass
    ax.set_xlabel("x [m]"); ax.set_ylabel("y [m]"); ax.set_zlabel("z [m]")
    ax.view_init(elev=22, azim=-70); ax.tick_params(labelsize=7)

    # (우) 평면 등Rb 타원 + 측정량
    axp = fig.add_subplot(1, 2, 2); axp.set_aspect("equal")
    _draw_chamber_plan(axp, W, D)
    axp.plot(tx[0], tx[1], "^", ms=12, color="#ef6c00"); axp.text(tx[0]+0.6, tx[1], "TX", color="#ef6c00")
    axp.plot(rx[0], rx[1], "v", ms=12, color="#1565c0"); axp.text(rx[0]+0.6, rx[1], "RX", color="#1565c0")
    axp.plot(tg[0], tg[1], "o", ms=9, color="k"); axp.text(tg[0]+0.6, tg[1], "표적", color="k")
    # 등Rb 타원(TX,RX 초점, 합=R1+R2)
    fa, fb = tx[:2], rx[:2]; c2 = np.linalg.norm(fa - fb) / 2; a_e = (p["R1"] + p["R2"]) / 2
    b_e = np.sqrt(max(a_e**2 - c2**2, 0)); mid = (fa + fb) / 2
    ang = np.arctan2((fb - fa)[1], (fb - fa)[0]); th = np.linspace(0, 2*np.pi, 240)
    ER = np.array([[np.cos(ang), -np.sin(ang)], [np.sin(ang), np.cos(ang)]])
    ell = (ER @ np.vstack([a_e*np.cos(th), b_e*np.sin(th)])).T + mid
    axp.plot(ell[:, 0], ell[:, 1], color="#7b1fa2", lw=1.3, label="등Rb 타원(한 수신기 위치모호)")
    axp.plot([fa[0], tg[0]], [fa[1], tg[1]], "--", color="#ef6c00", lw=1)
    axp.plot([tg[0], fb[0]], [tg[1], fb[1]], "-", color="#2e7d32", lw=1.5)
    axp.plot([fa[0], fb[0]], [fa[1], fb[1]], ":", color="#c62828", lw=1)
    axp.set_title(f"평면도 · L={p['L']:.1f}m  Rb={p['Rb']:.1f}m  지연={p['tau']*1e9:.0f}ns  "
                  f"f_d={p['fd']:+.0f}Hz  바이각={p['beta']:.0f}°", fontsize=10)
    axp.set_xlabel("x [m]"); axp.set_ylabel("y [m]"); axp.legend(fontsize=8, loc="upper right")
    axp.set_xlim(-2, W + 2); axp.set_ylim(-2, D + 2); axp.grid(alpha=0.25)
    fn = os.path.join(outdir, "report4_geometry.png"); fig.savefig(fn, dpi=130); plt.close(fig)
    print("[bist]", os.path.relpath(fn)); return fn


# --------------------------------------------------------------------------- #
#  (2) 거리-도플러 맵 ECA 전/후 (챔버 스케일)
# --------------------------------------------------------------------------- #
def fig_rangedoppler(outdir=FIG, fc=3.5e9, M=48):
    wf = nr_downlink(occupancy="G3")               # 5G n78 100MHz (광대역·고분해능)
    fs = wf.fs_hz; ref_frame = wf.tx
    p = bistatic_params(TX, RX, TGT, VEL, fc)
    tau, fd = p["tau"], p["fd"]
    Rb_max = 45.0                                  # 챔버 스케일: Rb 수~수십 m
    n_range = int(min(len(ref_frame), Rb_max / (C0 / fs)))
    surv, ref = make_cpi(ref_frame, M, fs, tau, fd, a_tgt=1.0, dpi_amp=55.0,
                         clutter=CH_CLUTTER, snr_db=14.0, rng=np.random.default_rng(3))
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.6), constrained_layout=True)
    prf = fs / (len(ref) // M)
    fig.suptitle(f"거리-도플러 맵 (5G NR 100MHz, 무반사 챔버) — ECA 직접파/잔향제거 전/후  ·  "
                 f"PRF={prf:.0f}Hz (±{prf/2:.0f}Hz), 거리분해능 {C0/wf.bw_hz:.1f}m, 도플러분해능 {prf/M:.1f}Hz",
                 fontsize=13, fontweight="bold")
    for ax, (tag, sig) in zip(axes, [("ECA 전 — 직접파(DPI)가 지배", surv),
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
def _pd_curve(wf, fc, snr_list, T_cpi=0.03, K=6, pfa=1e-3, seed0=0):
    """파형 1개의 Pd vs (표적 per-sample 에코 SNR[dB]).
    **고정 CPI 시간 T_cpi → 도플러분해능(1/T_cpi)을 파형 무관하게 균일화**한다. 이게 중요한 이유:
    WiFi 는 프레임(패킷)이 짧아 PRF 가 매우 커서, M 을 작게 고정하면 Δf_d 가 거칠어져 표적 도플러가
    0-도플러(DPI) 빈에 묻혀 ECA 에 함께 지워진다(검출 실패). T_cpi 고정이면 WiFi 도 충분한 M(≈수백)을
    얻어 표적을 DPI 와 분리한다. 절대 잡음(σ²=1), 표적은 에코 SNR 로 진폭 결정.
    무반사 챔버는 DPI 지배(잔향 약함)라 Pd 계산은 **DPI만**(clutter 생략)으로 두어도 결과 동일하고 빠르다."""
    fs = wf.fs_hz; ref_frame = wf.tx; Lf = len(ref_frame)
    prf = fs / Lf
    # M(슬로타임 프레임수)을 2의 거듭제곱으로 → slow-time FFT 가 빠르다(소수 M 회피). Δf_d≈1/T_cpi 유지.
    M = int(2 ** round(np.log2(max(16, T_cpi * prf))))
    p = bistatic_params(TX, RX, TGT, VEL, fc); tau, fd = p["tau"], p["fd"]
    n_range = int(min(Lf, 45.0 / (C0 / fs)))
    pds = []
    for si, sdb in enumerate(snr_list):
        a = 10.0 ** (sdb / 20.0)                             # 에코 진폭(절대, 잡음σ²=1) — 모드 무관 동일
        hit = 0
        for k in range(K):
            surv, ref = make_cpi(ref_frame, M, fs, tau, fd, a_tgt=a, dpi_amp=40.0,
                                 clutter=(),                 # 무반사: DPI만(잔향 생략 → 빠름, Pd 동일)
                                 abs_noise=True, noise_var=1.0,
                                 rng=np.random.default_rng(seed0 + si * 100 + k))
            Rb, f_d, rd = range_doppler(eca(surv, ref, 16), ref, fs, M, n_range=n_range)
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


def fig_detection(outdir=FIG, fc=3.5e9, T_cpi=0.03, K=4):
    snr_list = list(range(-70, -24, 8))            # 표적 에코 진폭[dB] (동일 물리 에코, 잡음 고정)
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.2), constrained_layout=True)
    fig.suptitle("무반사 챔버 검출 성능 Pd vs 에코 진폭 — 파형/점유가 탐지를 좌우 (왜 한가한 5G(SSB)로는 못 잡나)\n"
                 f"같은 물리 에코·고정 잡음 / CPI {T_cpi*1e3:.0f}ms(도플러분해능 {1/T_cpi:.0f}Hz 균일) / CFAR Pfa=1e-3",
                 fontsize=12.5, fontweight="bold")
    col = {"wifi": "#1565c0", "lte": "#ef6c00", "nr": "#2e7d32"}
    for key, wf in all_waveforms("G3").items():
        pd, M = _pd_curve(wf, wf.carrier_hz, snr_list, T_cpi, K)
        axes[0].plot(snr_list, pd, "o-", color=col[key], lw=1.8,
                     label=f"{wf.name} (B={wf.bw_hz/1e6:.0f}MHz, 분해능={C0/wf.bw_hz:.0f}m, M={M})")
    axes[0].set_title("(a) 파형별 (G3 풀로드) — 대역폭↑ → 처리이득·거리분해능↑ → 같은 SNR서 Pd↑\n"
                      "  ※ 챔버 스케일: LTE 거리분해능≈17 m 는 챔버 Rb 를 못 가름", fontsize=10)
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


# --------------------------------------------------------------------------- #
#  (4) 추적 애니메이션 — 드론이 챔버 안을 날며 거리-도플러 검출이 표적을 따라감
# --------------------------------------------------------------------------- #
def _trajectory(n_frames, speed=4.0):
    """챔버 quiet zone 을 가로지르는 곡선 비행경로. 반환 (positions[n,3], velocities[n,3])."""
    P0 = np.array([16.0, 5.0, 6.0]); C = np.array([25.0, 10.0, 5.0]); P1 = np.array([18.0, 15.0, 6.5])
    t = np.linspace(0, 1, n_frames)[:, None]
    pos = (1 - t)**2 * P0 + 2 * (1 - t) * t * C + t**2 * P1        # 2차 베지어(챔버 내부)
    dpos = 2 * (1 - t) * (C - P0) + 2 * t * (P1 - C)               # 접선(속도방향)
    vel = dpos / (np.linalg.norm(dpos, axis=1, keepdims=True) + 1e-9) * speed
    return pos, vel


def gif_bistatic_tracking(outdir=FIG, target="mavic4pro", occupancy="G3",
                          n_frames=30, M=24, fps=7):
    """드론 비행 → 프레임마다 ECA+CAF+CFAR 로 거리-도플러 맵 갱신, 검출이 표적 궤적을 따라감."""
    wf = nr_downlink(occupancy=occupancy); fc = wf.carrier_hz; fs = wf.fs_hz
    ref_frame = wf.tx; Lf = len(ref_frame); prf = fs / Lf
    n_range = int(min(Lf, 45.0 / (C0 / fs)))
    W, D, H = CHAMBER
    pos, vel = _trajectory(n_frames)
    print(f"[bist-gif] {n_frames}프레임 사전계산 (무반사 챔버, 5G {occupancy}, PRF={prf:.0f}Hz, ±{prf/2:.0f}Hz)…")

    frames = []                                                    # 프레임별 (rd_db, Rb, f_d, true, det)
    rng = np.random.default_rng(11)
    for kf in range(n_frames):
        p = bistatic_params(TX, RX, pos[kf], vel[kf], fc)
        surv, ref = make_cpi(ref_frame, M, fs, p["tau"], p["fd"], a_tgt=1.0, dpi_amp=50.0,
                             clutter=CH_CLUTTER, snr_db=16.0, rng=rng)
        Rb, f_d, rd = range_doppler(eca(surv, ref, 36), ref, fs, M, n_range=n_range)
        rdb = 20 * np.log10(rd / rd.max() + 1e-9)
        zd = int(np.argmin(np.abs(f_d))); rd2 = rd.copy(); rd2[max(0, zd-1):zd+2, :] = 0
        di, ri = np.unravel_index(np.argmax(rd2), rd2.shape)
        thr = 6.0 * np.median(rd2[rd2 > 0])
        det = (Rb[ri], f_d[di]) if rd2[di, ri] > thr else None
        frames.append((rdb, Rb, f_d, (p["Rb"], p["fd"]), det, p))

    fig = plt.figure(figsize=(13, 5.6))
    axg = fig.add_subplot(1, 2, 1); axr = fig.add_subplot(1, 2, 2)
    det_hist = []

    def update(kf):
        rdb, Rb, f_d, (tRb, tfd), det, p = frames[kf]
        # (좌) 챔버 평면 기하
        axg.clear()
        _draw_chamber_plan(axg, W, D)
        axg.plot(TX[0], TX[1], "^", ms=13, color="#ef6c00"); axg.text(TX[0]+0.6, TX[1], "TX")
        axg.plot(RX[0], RX[1], "v", ms=13, color="#1565c0"); axg.text(RX[0]+0.6, RX[1], "RX")
        axg.plot(pos[:, 0], pos[:, 1], ":", color="0.7", lw=1)           # 전체 경로
        axg.plot(pos[:kf+1, 0], pos[:kf+1, 1], "-", color="#c62828", lw=1.5)  # 지나온 궤적
        axg.plot(pos[kf, 0], pos[kf, 1], "o", ms=9, color="k")
        axg.plot([TX[0], pos[kf, 0]], [TX[1], pos[kf, 1]], "--", color="#ef6c00", lw=0.9)
        axg.plot([pos[kf, 0], RX[0]], [pos[kf, 1], RX[1]], "-", color="#2e7d32", lw=1.3)
        # 등Rb 타원
        fa, fb = np.array(TX[:2]), np.array(RX[:2]); c2 = np.linalg.norm(fa-fb)/2
        a_e = (p["R1"]+p["R2"])/2; b_e = np.sqrt(max(a_e**2-c2**2, 0)); mid = (fa+fb)/2
        ang = np.arctan2((fb-fa)[1], (fb-fa)[0]); th = np.linspace(0, 2*np.pi, 200)
        ER = np.array([[np.cos(ang), -np.sin(ang)], [np.sin(ang), np.cos(ang)]])
        ell = (ER @ np.vstack([a_e*np.cos(th), b_e*np.sin(th)])).T + mid
        axg.plot(ell[:, 0], ell[:, 1], color="#7b1fa2", lw=1.0, alpha=0.8)
        axg.set_xlim(-2, W+2); axg.set_ylim(-2, D+2); axg.set_aspect("equal")
        axg.set_title(f"챔버 비행 {kf+1}/{n_frames} · Rb={p['Rb']:.0f}m f_d={p['fd']:+.0f}Hz", fontsize=10)
        axg.set_xlabel("x [m]"); axg.set_ylabel("y [m]"); axg.grid(alpha=0.25)
        # (우) 거리-도플러 맵
        axr.clear()
        axr.pcolormesh(Rb, f_d, rdb, cmap="turbo", vmin=-45, vmax=0, shading="auto")
        axr.plot(tRb, tfd, "o", mfc="none", mec="w", ms=13, mew=1.4)     # 참 표적
        if det:
            det_hist.append(det)
            axr.plot(det[0], det[1], "x", color="r", ms=11, mew=2.5)
        if det_hist:
            dh = np.array(det_hist); axr.plot(dh[:, 0], dh[:, 1], ".", color="#ffd600", ms=4)  # 검출 트랙
        axr.set_xlim(Rb[0], Rb[-1]); axr.set_ylim(f_d[0], f_d[-1])
        axr.set_xlabel("바이스태틱 거리 Rb [m]"); axr.set_ylabel("도플러 f_d [Hz]")
        axr.set_title("거리-도플러 맵 (ECA+CAF+CFAR) — ○참표적 ×검출 ·트랙", fontsize=10)
        fig.suptitle("무반사 챔버 바이스태틱 패시브 레이더 — 드론 비행 추적 (5G NR, 프레임마다 검출)",
                     fontsize=13, fontweight="bold")
        return ()

    anim = FuncAnimation(fig, update, frames=n_frames, blit=False)
    os.makedirs(outdir, exist_ok=True)
    fn = os.path.join(outdir, "report4_tracking.gif")
    anim.save(fn, writer=PillowWriter(fps=fps), dpi=90)
    plt.close(fig); print("[bist-gif]", os.path.relpath(fn)); return fn


def build_all(outdir=FIG):
    fig_geometry(outdir)
    fig_rangedoppler(outdir)
    fig_detection(outdir)
    print("바이스태틱(무반사 챔버) 시각화 완료 →", os.path.relpath(outdir))


if __name__ == "__main__":
    build_all()
