# -*- coding: utf-8 -*-
"""
anim_plots.py — **matplotlib 애니메이션(GIF)** 로 실험 결과를 '움직이는 그림'으로 (report04~12)
==================================================================================================
Sionna RT 렌더(render_anim.py)가 '장면'을 움직인다면, 여기선 **신호·검출 결과**를 움직인다:
  · report12 : Rx 1→4 증설로 표적이 잡음에서 떠오르는 RD 맵, Pd 곡선이 그려지는 애니,
               몬테카를로 시행수↑ 로 Pd 가 수렴, 배열 빔패턴이 N 으로 날카로워짐
  · report08 : RCS 방위각 회전(폴라), 마이크로도플러 스펙트로그램
  · report11 : 모호함수(ambiguity), 도플러 분해능
  · report10 : CFAR 문턱이 RD 위를 훑는다
  · report04/05 : WiFi/LTE/5G 스펙트럼

전부 영어 텍스트(그림 규약). 데이터는 outputs/detection_*.{json,npz} + 즉석 계산.
실행:  python src/anim_plots.py --which all   (또는 특정 이름)
출력:  outputs/renders/anim/<name>.gif
"""
from __future__ import annotations

import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_BENCH = os.path.abspath(os.path.join(_HERE, "..", "benchmark"))
for _p in (_HERE, _BENCH):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np                                    # noqa: E402
import matplotlib                                     # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                       # noqa: E402
from matplotlib import animation                      # noqa: E402

ROOT = os.path.abspath(os.path.join(_HERE, ".."))
OUT = os.path.join(ROOT, "outputs")
ANIM = os.path.join(OUT, "renders", "anim")
C0 = 299792458.0
FC = 3.5e9
NAME = {"nr": "5G NR 100 MHz", "wifi": "WiFi 80 MHz", "lte": "LTE 20 MHz"}
COL = {1: "#c0392b", 2: "#e67e22", 3: "#2980b9", 4: "#27ae60"}
# 9모드 JSON: 검출 GIF 는 각 표준의 **풀(제어) 모드**를 대표로 쓴다(파일명은 std 유지).
STD2FULL = {"nr": "G3", "wifi": "W3", "lte": "L3"}


def _mode(j, std):
    """9모드('modes') 또는 구 3모드('waveforms') 구조 모두에서 대표 모드 dict + 배열키(std or code)."""
    if "modes" in j:
        code = STD2FULL[std]
        return j["modes"][code], code
    return j["waveforms"][std], std


def _save(anim_obj, name, fps=6):
    os.makedirs(ANIM, exist_ok=True)
    p = os.path.join(ANIM, f"{name}.gif")
    anim_obj.save(p, writer=animation.PillowWriter(fps=fps))
    plt.close("all")
    print(f"  ✅ {name}.gif")
    return p


def _load():
    j = json.load(open(os.path.join(OUT, "detection_rx_sweep.json")))
    arr = dict(np.load(os.path.join(OUT, "detection_arrays.npz")))
    return j, arr


# --------------------------------------------------------------------------- #
#  report12 ① Rx 증설 → RD 맵에서 표적이 떠오른다
# --------------------------------------------------------------------------- #
def rx_buildup(std="nr"):
    j, arr = _load()
    w, code = _mode(j, std); di, ri = w["di_true"], w["ri_true"]
    Rb = arr[f"{code}_Rb"]; fd = arr[f"{code}_fd"]
    rds = [arr[f"{code}_rdN{N}"] for N in (1, 2, 3, 4)]
    vmax = max(20 * np.log10(r.max() + 1e-9) for r in rds)
    fig, ax = plt.subplots(figsize=(6.6, 4.8))
    ext = [Rb[0], Rb[-1], fd[0], fd[-1]]

    def frame(k):
        ax.clear()
        rd_db = 20 * np.log10(rds[k] + 1e-9)
        im = ax.imshow(rd_db, aspect="auto", origin="lower", extent=ext,
                       vmin=vmax - 45, vmax=vmax, cmap="turbo")
        ax.plot(Rb[ri], fd[di], "s", mfc="none", mec="w", ms=16, mew=2)
        ax.set_title(f"{NAME[std]} — surveillance array N = {k+1} Rx  "
                     f"(coherent gain +{10*np.log10(k+1):.1f} dB)")
        ax.set_xlabel("bistatic range $R_b$ [m]"); ax.set_ylabel("Doppler [Hz]")
        ax.text(0.02, 0.95, "target", color="w", transform=ax.transAxes, fontsize=9)
        return [im]

    frame(0)
    a = animation.FuncAnimation(fig, frame, frames=4, blit=False)
    return _save(a, f"rd_rxbuildup_{std}", fps=1.3)


# --------------------------------------------------------------------------- #
#  report12 ② Pd 곡선이 N=1..4 순서로 그려진다
# --------------------------------------------------------------------------- #
def pd_curves_build(std="nr"):
    j, _ = _load()
    w, code = _mode(j, std); g = np.array(w["snr_grid"])
    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    seq = []
    for N in (1, 2, 3, 4):
        for step in range(1, len(g) + 1):
            seq.append((N, step))
        seq += [(N, len(g))] * 3

    def frame(i):
        ax.clear()
        Nc, step = seq[i]
        for N in (1, 2, 3, 4):
            c = w["curves"][str(N)]["Pd"]
            if N < Nc:
                ax.plot(g, c, "-o", ms=3, color=COL[N], label=f"N={N}")
            elif N == Nc:
                ax.plot(g[:step], c[:step], "-o", ms=3, color=COL[N], label=f"N={N}")
        ax.set_xlim(g[0], g[-1]); ax.set_ylim(-0.03, 1.03)
        ax.axhline(0.5, ls=":", c="gray"); ax.grid(alpha=0.3)
        ax.set_xlabel("single-Rx output SNR [dB]"); ax.set_ylabel("$P_d$")
        ax.set_title(f"{NAME[std]} — detection probability vs SNR, adding receivers")
        ax.legend(loc="lower right", fontsize=9)

    a = animation.FuncAnimation(fig, frame, frames=len(seq), blit=False)
    return _save(a, f"pd_build_{std}", fps=12)


# --------------------------------------------------------------------------- #
#  report12 ③ 배열 빔패턴이 N 으로 날카로워진다 (표적 az 로 조향)
# --------------------------------------------------------------------------- #
def beampattern():
    az0 = -23.8                                        # 표적 방위
    th = np.linspace(-90, 90, 721)
    lam = C0 / FC; d = lam / 2
    fig = plt.figure(figsize=(6.2, 5.2)); ax = plt.subplot(111, projection="polar")
    frames = []
    for N in (1, 2, 3, 4):
        frames += [N] * 8

    def frame(i):
        ax.clear()
        N = frames[i]
        k = np.arange(N) - (N - 1) / 2
        # 표적 방위로 조향한 배열인자
        phase = 2 * np.pi / lam * d * np.outer(k, np.sin(np.radians(th)) - np.sin(np.radians(az0)))
        AF = np.abs(np.exp(1j * phase).sum(0)) / N
        AFdb = 20 * np.log10(AF + 1e-3)
        ax.plot(np.radians(th), np.clip(AFdb, -30, 0) + 30, color=COL[N], lw=2)
        ax.fill(np.radians(th), np.clip(AFdb, -30, 0) + 30, color=COL[N], alpha=0.15)
        ax.set_theta_zero_location("N"); ax.set_theta_direction(-1)
        ax.set_thetamin(-90); ax.set_thetamax(90); ax.set_rticks([])
        ax.axvline(np.radians(az0), ls="--", c="k", lw=1)
        ax.set_title(f"Surveillance ULA beam pattern, N = {N} Rx\n"
                     f"steered to target az = {az0:.0f}° (dashed)", fontsize=11)

    a = animation.FuncAnimation(fig, frame, frames=len(frames), blit=False)
    return _save(a, "beampattern", fps=4)


# --------------------------------------------------------------------------- #
#  report12 ④ 몬테카를로 수렴 — 시행수↑ 로 Pd 추정이 안정된다
# --------------------------------------------------------------------------- #
def montecarlo_converge(std="nr", p_true=0.7, Kmax=2000, seed=0):
    rng = np.random.default_rng(seed)
    hits = np.cumsum(rng.random(Kmax) < p_true)
    ks = np.arange(1, Kmax + 1)
    pd = hits / ks
    ci = 1.96 * np.sqrt(pd * (1 - pd) / ks)
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    steps = np.unique(np.round(np.geomspace(5, Kmax, 60)).astype(int))

    def frame(i):
        ax.clear()
        kk = steps[i]
        ax.plot(ks[:kk], pd[:kk], color="#2980b9", lw=1.5)
        ax.fill_between(ks[:kk], (pd - ci)[:kk], (pd + ci)[:kk], color="#2980b9", alpha=0.2)
        ax.axhline(p_true, ls="--", c="k", label=f"true $P_d$={p_true}")
        ax.set_xscale("log"); ax.set_xlim(5, Kmax); ax.set_ylim(0, 1)
        ax.set_xlabel("number of Monte-Carlo trials"); ax.set_ylabel("estimated $P_d$")
        ax.set_title(f"{NAME[std]} — Pd estimate converges with more trials "
                     f"(K={kk})")
        ax.legend(loc="lower right"); ax.grid(alpha=0.3, which="both")

    a = animation.FuncAnimation(fig, frame, frames=len(steps), blit=False)
    return _save(a, f"mc_converge_{std}", fps=10)


# --------------------------------------------------------------------------- #
#  report08 ⑤ RCS 방위각 폴라 (표적을 돌리며 밝기 변화)
# --------------------------------------------------------------------------- #
def rcs_azimuth(drone="mavic4pro"):
    from rcs_po import drone_rcs_pattern
    az = np.arange(0, 360, 3.0)
    sig, _ = drone_rcs_pattern(drone, FC, az, el_deg=10.0)
    dbsm = 10 * np.log10(sig + 1e-12)
    fig = plt.figure(figsize=(5.8, 5.8)); ax = plt.subplot(111, projection="polar")
    lo = np.floor(dbsm.min() / 5) * 5

    def frame(i):
        ax.clear()
        n = i + 2
        ax.plot(np.radians(az[:n]), dbsm[:n] - lo, color="#8e44ad", lw=1.8)
        ax.plot([np.radians(az[n - 1])], [dbsm[n - 1] - lo], "o", color="#c0392b")
        ax.set_theta_zero_location("N"); ax.set_theta_direction(-1)
        ax.set_rlabel_position(90)
        ax.set_title(f"{drone} monostatic RCS vs azimuth (SBR·Mitsuba)\n"
                     f"az={az[n-1]:.0f}°, σ={dbsm[n-1]:.1f} dBsm", fontsize=11)

    a = animation.FuncAnimation(fig, frame, frames=len(az) - 1, blit=False)
    return _save(a, f"rcs_azimuth_{drone}", fps=15)


# --------------------------------------------------------------------------- #
#  report11 ⑥ 모호함수 — 신호가 표적을 얼마나 또렷이 가르나 (지연 vs 도플러)
# --------------------------------------------------------------------------- #
def ambiguity(std="nr"):
    from waveforms import nr_downlink, lte_downlink, wifi_80211ac
    wf = {"nr": nr_downlink, "lte": lte_downlink, "wifi": wifi_80211ac}[std](occupancy="G3")
    x = wf.tx[:4096].astype(np.complex64); fs = wf.fs_hz
    ndop = 41; fdop = np.linspace(-2000, 2000, ndop)
    n = np.arange(len(x))
    lags = np.arange(-30, 31)
    A = np.zeros((ndop, len(lags)))
    for i, fdv in enumerate(fdop):
        xs = x * np.exp(1j * 2 * np.pi * fdv * n / fs)
        for jl, L in enumerate(lags):
            if L >= 0:
                A[i, jl] = abs(np.vdot(x[L:], xs[:len(x) - L]))
            else:
                A[i, jl] = abs(np.vdot(x[:L], xs[-L:]))
    A /= A.max()
    Adb = 20 * np.log10(A + 1e-3)
    rng_m = lags * C0 / fs
    fig, ax = plt.subplots(figsize=(6.4, 4.8))

    def frame(i):
        ax.clear()
        sh = Adb.copy()
        cut = ndop // 2 + int((i - ndop // 2))
        im = ax.imshow(sh, aspect="auto", origin="lower",
                       extent=[rng_m[0], rng_m[-1], fdop[0], fdop[-1]],
                       vmin=-30, vmax=0, cmap="turbo")
        ax.axhline(fdop[min(i, ndop - 1)], color="w", ls=":", lw=1)
        ax.set_xlabel("bistatic range lag [m]"); ax.set_ylabel("Doppler [Hz]")
        ax.set_title(f"{NAME[std]} ambiguity function — sharpness sets resolution")
        return [im]

    a = animation.FuncAnimation(fig, frame, frames=ndop, blit=False)
    return _save(a, f"ambiguity_{std}", fps=8)


# --------------------------------------------------------------------------- #
#  report04/05 ⑦ 파형 스펙트럼 — 조명원이 차지하는 대역 (대역↑ = 거리분해능↑)
# --------------------------------------------------------------------------- #
def waveform_spectrum(std="nr"):
    from waveforms import nr_downlink, lte_downlink, wifi_80211ac
    wf = {"nr": nr_downlink, "lte": lte_downlink, "wifi": wifi_80211ac}[std](occupancy="G3")
    x = wf.tx[:8192].astype(np.complex64); fs = wf.fs_hz
    X = np.fft.fftshift(np.fft.fft(x * np.hanning(len(x))))
    f = np.fft.fftshift(np.fft.fftfreq(len(x), 1 / fs)) / 1e6
    psd = 20 * np.log10(np.abs(X) + 1e-6); psd -= psd.max()
    fig, ax = plt.subplots(figsize=(6.6, 4.2))
    nfr = 48
    idx = np.linspace(0, len(f), nfr).astype(int)

    def frame(i):
        ax.clear()
        k = idx[min(i, nfr - 1)]
        ax.fill_between(f[:k], -80, psd[:k], color="#2980b9", alpha=0.5)
        ax.plot(f[:k], psd[:k], color="#1f4e79", lw=0.8)
        if 0 < k < len(f):
            ax.axvline(f[k - 1], color="#c0392b", lw=1.2)
        ax.set_xlim(f[0], f[-1]); ax.set_ylim(-80, 3)
        ax.set_xlabel("frequency [MHz]"); ax.set_ylabel("PSD [dB]")
        ax.set_title(f"{NAME[std]} spectrum — occupied band {wf.ref_bw_hz/1e6:.0f} MHz → "
                     f"range resolution {wf.range_resolution_m:.1f} m")
        ax.grid(alpha=0.3)

    a = animation.FuncAnimation(fig, frame, frames=nfr, blit=False)
    return _save(a, f"spectrum_{std}", fps=12)


# --------------------------------------------------------------------------- #
#  report10 ⑧ CFAR 슬라이딩 — 잡음 따라 문턱이 자동으로 움직인다
# --------------------------------------------------------------------------- #
def cfar_sweep(std="nr"):
    j, arr = _load()
    w, code = _mode(j, std); di, ri = w["di_true"], w["ri_true"]
    rd = arr[f"{code}_rdN4"]                                       # N=4 노이지 RD
    fd = arr[f"{code}_fd"]
    cut = rd[:, ri]                                               # 표적 거리빈에서 도플러 컷
    P = cut ** 2
    G, T = 2, 8                                                   # 가드·훈련(한쪽)
    nd = len(P)
    fig, ax = plt.subplots(figsize=(6.8, 4.3))
    cells = list(range(T + G, nd - T - G))

    def frame(i):
        ax.clear()
        c = cells[min(i, len(cells) - 1)]
        tr = np.r_[P[c - G - T:c - G], P[c + G + 1:c + G + T + 1]]
        noise = tr.mean(); alpha = len(tr) * (1e-4 ** (-1 / len(tr)) - 1)
        thr = alpha * noise
        ax.plot(fd, 20 * np.log10(cut + 1e-9), color="#333", lw=1.2, label="signal (Doppler cut)")
        ax.axvspan(fd[max(0, c - G - T)], fd[max(0, c - G)], color="#3498db", alpha=0.15)
        ax.axvspan(fd[min(nd - 1, c + G)], fd[min(nd - 1, c + G + T)], color="#3498db", alpha=0.15,
                   label="CFAR training")
        ax.plot(fd[c], 10 * np.log10(thr + 1e-9), "rv", ms=9,
                label="adaptive threshold")
        ax.axvline(fd[di], ls=":", color="#27ae60", label="target Doppler")
        det = P[c] > thr
        ax.set_title(f"{NAME[std]} CFAR — threshold follows local noise "
                     f"{'· DETECT at target!' if (det and abs(c-di)<=2) else ''}")
        ax.set_xlabel("Doppler [Hz]"); ax.set_ylabel("[dB]"); ax.set_ylim(bottom=None)
        ax.legend(fontsize=8, loc="upper right"); ax.grid(alpha=0.3)

    a = animation.FuncAnimation(fig, frame, frames=len(cells), blit=False)
    return _save(a, f"cfar_sweep_{std}", fps=10)


# --------------------------------------------------------------------------- #
#  report02 ⑨ 드론 전 기종 가로 정렬 회전 갤러리 (명칭 라벨) — 재질색
# --------------------------------------------------------------------------- #
def drone_row_gif(name="drone_gallery_row", frames=48):
    """**레지스트리 전 기종**이 가로로 나란히, **몸체가 돌면서 프로펠러도 스핀**(분절 메쉬 시연), 위에 명칭.
    재질색(plastic=회색(프롭 포함)·carbon=검정·metal=파랑·camera=주황·pcb=초록). pose_articulated 로
    프레임마다 몸체 yaw + 로터 위상을 바꿔 그린다(부위별 회전이 분리 가능함을 한눈에)."""
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    from drones import DRONES, pose_articulated, drone_colors, drone_order, drone_label
    #  ⭐ 2026-07-30: 예전엔 5종 하드코딩 목록을 `if d in DRONES` 로 걸러 썼다 — 목록에 없는
    #     신규 기종이 **에러 없이 갤러리에서 빠졌다**. 이제 앞머리 순서만 고정하고 나머지는 자동.
    drones = drone_order(("mavic4pro", "matrice4e", "mini5pro", "phantom4", "s1000plus"))
    disp = {d: drone_label(d) for d in drones}          # 이름은 DroneSpec 에서 유도(사전 하드코딩 금지)
    cmaps = {d: drone_colors(DRONES[d]) for d in drones}

    def _polys(mesh, cmap):
        V = np.array(mesh.v)
        tris = [[V[a], V[b], V[c]] for (a, b, c) in mesh.f]
        cols = [cmap.get(g, (0.6, 0.6, 0.6)) for g in mesh.g]
        return Poly3DCollection(tris, facecolors=cols, edgecolors=(0, 0, 0, 0.25), linewidths=0.15)

    # ⚠ 축 범위는 드론마다 **한 번만** 정해 고정(프레임마다 bounds() 를 다시 잡으면 회전 중
    #   바운딩박스가 변해 줌이 출렁이며 깜빡인다). 중심 기준 최대반경은 z회전에 불변.
    LIM = {}
    for d in drones:
        s = DRONES[d]
        m0 = pose_articulated(s, body_rpy=(0, 0, 0), rotor_phase_deg=[0] * s.num_rotors)
        V0 = np.array(m0.v); c = (V0.min(0) + V0.max(0)) / 2
        rxy = float(np.hypot(V0[:, 0] - c[0], V0[:, 1] - c[1]).max()) * 1.05
        rz = max(float(np.abs(V0[:, 2] - c[2]).max()) * 1.15, rxy * 0.18)
        LIM[d] = (c, rxy, rz)

    def _fix(ax, d):
        c, rxy, rz = LIM[d]
        ax.set_xlim(c[0]-rxy, c[0]+rxy); ax.set_ylim(c[1]-rxy, c[1]+rxy)
        ax.set_zlim(c[2]-rz, c[2]+rz)
        try:
            ax.set_box_aspect((1, 1, float(rz / rxy)))
        except Exception:
            pass
        ax.set_axis_off()

    fig = plt.figure(figsize=(3.7 * len(drones), 4.7), dpi=135)
    fig.patch.set_facecolor("black")   # Sionna spin_<drone>.gif(검은 배경)과 배경 일치
    axes = [fig.add_subplot(1, len(drones), i + 1, projection="3d") for i in range(len(drones))]

    def update(i):
        yaw = 360.0 * i / frames                          # 몸체 회전
        spin = (i * 48) % 360                             # 프로펠러 빠른 스핀
        for ax, d in zip(axes, drones):
            ax.clear()
            spec = DRONES[d]
            dirs = [(-1) ** k for k in range(spec.num_rotors)]   # 교대 회전방향(CW/CCW)
            phases = [dd * spin for dd in dirs]
            m = pose_articulated(spec, body_rpy=(0, 0, yaw), rotor_phase_deg=phases)
            ax.add_collection3d(_polys(m, cmaps[d])); _fix(ax, d)
            ax.view_init(elev=24, azim=-60)
            ax.set_title(disp[d], fontsize=15, fontweight="bold", pad=2, color="white")
        fig.suptitle(f"{len(drones)} drones - body rotating + propellers spinning (articulated mesh)   "
                     "material colors: metal=steel-blue - plastic/prop=gray - carbon=black - "
                     "camera=orange - pcb=green", fontsize=10.5, y=0.99, color="white")
        fig.subplots_adjust(left=0.003, right=0.997, top=0.88, bottom=0.01, wspace=0.02)

    a = animation.FuncAnimation(fig, update, frames=frames, blit=False)
    return _save(a, name, fps=15)


def spin_articulated(drone="mavic4pro", frames=40, name=None):
    """단일 드론 — 몸체 회전 + **프로펠러 스핀**(분절 메쉬), 재질색. spin_<drone>.gif 덮어씀."""
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    from drones import DRONES, pose_articulated, drone_colors, drone_label
    disp = drone_label(drone) if drone in DRONES else drone
    name = name or f"spin_{drone}"
    spec = DRONES[drone]; cmap = drone_colors(spec)
    fig = plt.figure(figsize=(5.4, 5.4), dpi=140)
    ax = fig.add_subplot(111, projection="3d")
    # ⚠ 축 범위는 **한 번만** 정하고 고정한다. 프레임마다 bounds() 로 다시 잡으면 몸체가 돌 때
    #   바운딩박스가 커졌다 작아졌다 해서 드론이 **줌인/줌아웃 하듯 깜빡인다**(이전 버그).
    #   중심에서의 **최대 반경**은 z축 회전에 불변이므로 이것으로 고정한다.
    _m0 = pose_articulated(spec, body_rpy=(0, 0, 0), rotor_phase_deg=[0] * spec.num_rotors)
    _V0 = np.array(_m0.v); _c = (_V0.min(0) + _V0.max(0)) / 2
    _rxy = float(np.hypot(_V0[:, 0] - _c[0], _V0[:, 1] - _c[1]).max()) * 1.05   # z회전 불변
    _rz = max(float(np.abs(_V0[:, 2] - _c[2]).max()) * 1.15, _rxy * 0.18)
    _asp = (1.0, 1.0, float(_rz / _rxy))                 # 납작한 드론에 맞춘 박스 → 여백 최소

    def update(i):
        yaw = 360.0 * i / frames
        spin = (i * 50) % 360
        dirs = [(-1) ** k for k in range(spec.num_rotors)]
        m = pose_articulated(spec, body_rpy=(0, 0, yaw), rotor_phase_deg=[d * spin for d in dirs])
        V = np.array(m.v)
        tris = [[V[a], V[b], V[c]] for (a, b, c) in m.f]
        cols = [cmap.get(g, (0.6, 0.6, 0.6)) for g in m.g]
        ax.clear()
        ax.add_collection3d(Poly3DCollection(tris, facecolors=cols, edgecolors=(0, 0, 0, 0.22),
                                             linewidths=0.15))
        ax.set_xlim(_c[0]-_rxy, _c[0]+_rxy); ax.set_ylim(_c[1]-_rxy, _c[1]+_rxy)
        ax.set_zlim(_c[2]-_rz, _c[2]+_rz)                   # 고정 → 깜빡임 없음
        try:
            ax.set_box_aspect(_asp)                         # 실제 비율 → 드론이 프레임을 채움
        except Exception:
            pass
        ax.set_axis_off(); ax.view_init(elev=22, azim=-60)
        ax.set_title(f"{disp} — body + propeller rotation (material-colored)", fontsize=12,
                     fontweight="bold")

    a = animation.FuncAnimation(fig, update, frames=frames, blit=False)
    return _save(a, name, fps=14)


def drone_size_compare(name="drone_size_compare"):
    """드론 **전 기종**을 같은 축척으로 위에서 본 실루엣 — 실제 크기 비교(재질색·명칭·대각 mm·스케일바)."""
    from matplotlib.collections import PolyCollection
    from drones import DRONES, build_drone, drone_colors, drone_order, drone_label
    order = drone_order(("mini5pro", "mavic4pro", "phantom4", "matrice4e", "s1000plus"))
    disp = {d: drone_label(d) for d in order}
    meshes = {d: build_drone(DRONES[d]) for d in order}

    def hspan(m):
        b0, b1 = m.bounds(); return max(b1[0] - b0[0], b1[1] - b0[1])
    R = max(hspan(meshes[d]) for d in order) * 0.56
    fig, axes = plt.subplots(1, len(order), figsize=(3.6 * len(order), 4.3), dpi=140)
    fig.patch.set_facecolor("black")   # 드론 렌더는 전부 검은 배경으로 통일(spin_*·r1_30·gallery 와 일치)
    for ax, d in zip(axes, order):
        m = meshes[d]; cmap = drone_colors(DRONES[d]); V = np.array(m.v)
        zmean = np.array([V[list(t)][:, 2].mean() for t in m.f])
        ordk = np.argsort(zmean)                                   # painter: 낮은 z 먼저
        polys = [V[list(m.f[k])][:, :2] for k in ordk]
        cols = [cmap.get(m.g[k], (0.6, 0.6, 0.6)) for k in ordk]
        ax.add_collection(PolyCollection(polys, facecolors=cols, edgecolors=(0, 0, 0, 0.12),
                                         linewidths=0.1))
        ax.set_facecolor("black")
        c = (m.bounds()[0] + m.bounds()[1]) / 2
        ax.set_xlim(c[0] - R, c[0] + R); ax.set_ylim(c[1] - R, c[1] + R)
        ax.set_aspect("equal"); ax.axis("off")
        ax.set_title(f"{disp[d]}\n{DRONES[d].diagonal_mm:.0f} mm diagonal", fontsize=12,
                     fontweight="bold", color="white")
    # 스케일바 0.5 m (첫 패널 좌하단)
    ax0 = axes[0]; c0 = (meshes[order[0]].bounds()[0] + meshes[order[0]].bounds()[1]) / 2
    x0, y0 = c0[0] - R * 0.85, c0[1] - R * 0.85
    ax0.plot([x0, x0 + 0.5], [y0, y0], "w-", lw=3)
    ax0.text(x0 + 0.25, y0 + R * 0.06, "0.5 m", ha="center", fontsize=10, color="white")
    fig.suptitle("Actual size comparison — same scale, top view (material-colored)", fontsize=13,
                 y=0.99, color="white")
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    os.makedirs(ANIM.replace("renders/anim", "figures"), exist_ok=True)
    p = os.path.join(ANIM.replace("renders/anim", "figures"), f"{name}.png")
    fig.savefig(p, dpi=140, facecolor="black"); plt.close(fig)
    print(f"  ✅ {name}.png (figures)")
    return p


REG = {
    "rx_buildup": lambda: [rx_buildup(s) for s in ("nr", "wifi", "lte")],
    "spectrum": lambda: [waveform_spectrum(s) for s in ("nr", "wifi", "lte")],
    "cfar_sweep": lambda: [cfar_sweep(s) for s in ("nr", "wifi", "lte")],
    "drone_row": drone_row_gif,
    "drone_size": drone_size_compare,
    "pd_build": lambda: [pd_curves_build(s) for s in ("nr", "wifi", "lte")],
    "beampattern": beampattern,
    "mc_converge": lambda: [montecarlo_converge(s) for s in ("nr", "wifi", "lte")],
    "rcs_azimuth": lambda: [rcs_azimuth(d) for d in ("mavic4pro", "matrice4e")],
    "ambiguity": lambda: [ambiguity(s) for s in ("nr", "wifi", "lte")],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--which", default="all")
    a = ap.parse_args()
    os.makedirs(ANIM, exist_ok=True)
    todo = list(REG) if a.which == "all" else a.which.split(",")
    for k in todo:
        try:
            REG[k]()
        except Exception as e:
            print(f"  ⚠ {k} 실패: {e}")


if __name__ == "__main__":
    main()
