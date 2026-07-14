# -*- coding: utf-8 -*-
"""
viz_report3.py — report3 의 **SBR(가림 포함) 마이크로도플러** + **Sionna 렌더 분절 애니메이션**
=================================================================================================
왜 새로 만들었나 (헤드라인)
  기존 report3 의 마이크로도플러는 순수 PO(microdoppler_series)였다 — **가림이 없다.**
  블레이드가 동체·모터 뒤로 돌아가도, 동체 내부의 배터리·PCB 도, 언제나 산란체로 계상된다.
  그 결과 **정적 성분(DC)이 부풀고**, 블레이드 변조(AC)는 가짜 뒷면 기여로 상쇄돼 얕아진다.
  SBR(rcs_sbr.sbr_field, Mitsuba 광선 + PO 적분)은 **광선이 실제로 맞은 첫 지점만** 적분한다.

    mavic4pro, az=0°, el=15°, 3.5 GHz, hover 5500 rpm(가정값)
      |DC|          PO 1.089e-2  →  SBR 5.43e-3     (가려진 산란체가 빠지며 -6.0 dB)
      std(AC)       PO 7.04e-5   →  SBR 2.62e-4     (블레이드가 동체를 가렸다 열며 변조가 깊어짐 +11.4 dB)
      |DC|/std(AC)  PO 154.8 (+43.8 dB) → SBR 20.7 (+26.3 dB)   ⇒ **17.5 dB**

  ⇒ 정적 받침대(pedestal) 대비 블레이드 선(line)이 **17.5 dB 위로 올라온다**
     = 마이크로도플러 검출이 기존 PO 추정보다 **17.5 dB 쉽다**.

⚠ 수치 정정(측정 근거): 이 17.5 dB 는 **광선 격자 λ/32** 에서 잰 값이다.
  microdoppler_sbr 의 기본 격자(λ/12)로 재면 SBR DC/AC = 12.3(+21.8 dB) 이 나와 차이가 22 dB 로 보이는데,
  그 초과분은 **물리가 아니라 광선격자 이산화 잡음**이다(자세가 돌 때 hit 집합이 툭툭 바뀌며 생기는 광대역 잡음).
  격자를 조이면 std(AC) 가 4.68e-4(λ/12) → 2.62e-4(λ/32) 로 내려가 수렴한다(λ/20~λ/48 에서 ±1 dB).
  그래서 이 모듈은 **SBR_DIV=32** 를 쓴다.

생성물 (outputs/figures/)
  report3_microdoppler.png     PO vs SBR 스펙트로그램 나란히 + DC/AC 막대 (헤드라인)
  report3_md_drones.png        5종 드론 SBR 스펙트로그램
  report3_md_spectrum.png      정확한 선 스펙트럼(창 없음) + 창 길이 스터디 (누설 vs AM 측대역)
  report3_rt_articulation.png  **Sionna 렌더**로 본 분절(몸체 자세 ⟂ 프로펠러 스핀)
  report3_rt_spin.gif          **Sionna 렌더** 프로펠러 스핀 애니메이션
  report3_anim_microdoppler.gif  Sionna 렌더 프레임 + SBR 스펙트로그램 시간커서
  outputs/report3_microdoppler.json  본문이 인용하는 수치

실행:  python src/viz_report3.py            (전체, ~10분)
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# ⚠ mitsuba 를 import 하는 모듈(rcs_sbr / scene_build)이 내부에서 gpu.pick() 을 먼저 부른다.
import numpy as np                                             # noqa: E402
from rcs_sbr import sbr_field                                  # noqa: E402  (Mitsuba 광선 + PO 적분)
from scene_build import build_scene, Part                      # noqa: E402  (Sionna 씬)
import sionna.rt as rt                                         # noqa: E402
import mitsuba as mi                                           # noqa: E402

import vizstyle                                                # noqa: E402
vizstyle.use_korean()
import matplotlib.pyplot as plt                                # noqa: E402
import matplotlib.image as mpimg                              # noqa: E402
import matplotlib.patheffects as pe                           # noqa: E402
from matplotlib.animation import FuncAnimation, PillowWriter   # noqa: E402

from drones import (DRONES, DRONE_GROUP_MAT, drone_colors, pose_articulated,   # noqa: E402
                    rotor_layout, build_propeller)
from microdoppler import microdoppler_series, spectrogram, _look, C0           # noqa: E402

ROOT = os.path.abspath(os.path.join(_HERE, ".."))
FIG = os.path.join(ROOT, "outputs", "figures")
OUT = os.path.join(ROOT, "outputs")
RTDIR = os.path.join(OUT, "renders", "report3")

FC = 3.5e9
AZ, EL = 0.0, 15.0            # 시선(표적 → 레이더)
PRF = 20_000.0                # 슬로타임 샘플률 [Hz] — f_tip 을 모호 없이 보려면 ≳2·f_tip
N_T = 2400                    # 120 ms (플래시 약 22회)
SBR_DIV = 32                  # 광선 격자 λ/32 (수렴 — 위 주석 참조)
N_PHASE = 720                 # φ ∈ [0,180°) 를 0.25° 로 (GPU 를 아끼지 않는다)

_NAME = {k: DRONES[k].name.replace("DJI ", "").split("  ")[0] for k in DRONES}
GMAT = {g: mat for g, (mat, _) in DRONE_GROUP_MAT.items()}


# --------------------------------------------------------------------------- #
#  SBR 위상 테이블 — 드론 자세는 단일 각도 φ 의 함수다
# --------------------------------------------------------------------------- #
#  로터 k 의 스핀 = dir_k·φ (장착 오프셋 base_ang 은 rotor_layout 이 갖고 있다).
#  n-블레이드 프로펠러는 360/n 회전에 불변 → φ 의 주기 = 360/n.  2엽이면 **180°**.
#  ⇒ 한 주기를 n_phase 로 잘라 SBR 을 미리 계산해 두면, 시간축은 조회로 끝난다.
#  ⇒ 그리고 이 테이블의 FFT 는 **창 없는 정확한 선 스펙트럼**이다(주기신호를 한 주기 균일샘플).
def sbr_phase_table(spec, fc=FC, az=AZ, el=EL, n_phase=N_PHASE, div=SBR_DIV, verbose=True):
    """φ 별 복소 산란장 테이블 tab[n_phase] (가림 포함). 반환 (tab, info)."""
    lam = C0 / fc
    u = _look(az, el)
    dirs = [r["dir"] for r in rotor_layout(spec)]
    period = 360.0 / max(1, spec.prop_blades)
    phis = np.linspace(0.0, period, n_phase, endpoint=False)
    t0 = time.time()
    tab = np.empty(n_phase, complex)
    for i, ph in enumerate(phis):
        mesh = pose_articulated(spec, rotor_phase_deg=[d * ph for d in dirs])
        tab[i] = sbr_field(mesh, GMAT, fc, u, spacing=lam / div)   # 자세마다 씬이 바뀐다(캐시 불가)
    rpm = spec.hover_rpm
    omega = 2 * np.pi * rpm / 60.0
    prop_R = spec.prop_dia_mm / 2000.0
    Vp = np.asarray(build_propeller(spec, n=10).v, float)
    R_mesh = float(np.hypot(Vp[:, 0], Vp[:, 1]).max())            # 메쉬 실제 최대반경(운동학적 상한용)
    info = dict(key=spec.key, rpm=rpm, fc=fc, lam=lam, az=az, el=el, n_phase=n_phase,
                div=div, period_deg=period, n_rotors=len(dirs), blades=spec.prop_blades,
                v_tip=omega * prop_R, prop_R=prop_R, R_mesh=R_mesh,
                f_tip=2 * omega * prop_R / lam * np.cos(np.radians(el)),
                f_kin=2 * omega * R_mesh / lam * np.cos(np.radians(el)),
                flash_hz=spec.prop_blades * rpm / 60.0,
                secs=time.time() - t0)
    if verbose:
        print(f"  [sbr-table] {spec.key:10s} n_phase={n_phase} λ/{div}  "
              f"f_tip=±{info['f_tip']:.0f}Hz flash={info['flash_hz']:.0f}Hz  ({info['secs']:.0f}s)")
    return tab, info


def series_from_table(tab, info, prf=PRF, n_t=N_T):
    """테이블 → 슬로타임 E(t). (microdoppler.microdoppler_sbr 과 동일한 조회+선형보간)"""
    n_phase = len(tab); period = info["period_deg"]
    t = np.arange(n_t) / prf
    idx = np.mod((360.0 * info["rpm"] / 60.0) * t / period * n_phase, n_phase)
    i0 = np.floor(idx).astype(int) % n_phase
    i1 = (i0 + 1) % n_phase
    fr = idx - np.floor(idx)
    return t, tab[i0] * (1 - fr) + tab[i1] * fr


def dc_ac(E):
    """정적 받침대 |DC| 와 변조 std(AC), 그 비."""
    dc = float(abs(np.mean(E))); ac = float(np.std(E))
    return dc, ac, dc / ac


def line_spectrum(tab, info):
    """창 없는 **정확한 선 스펙트럼**: tab 은 주기 1/flash 를 균일샘플한 한 주기다.
    반환 (f[Hz], H[복소], 하모닉 간격 f0)."""
    n = len(tab); f0 = info["flash_hz"]
    H = np.fft.fft(tab) / n
    f = np.fft.fftfreq(n, d=1.0 / (n * f0))
    o = np.argsort(f)
    return f[o], H[o], f0


# --------------------------------------------------------------------------- #
#  (1) 헤드라인 — PO vs SBR 스펙트로그램
# --------------------------------------------------------------------------- #
def fig_po_vs_sbr(outdir=FIG, target="mavic4pro", tab=None, info=None):
    spec = DRONES[target]
    if tab is None:
        tab, info = sbr_phase_table(spec)
    t, E_sbr = series_from_table(tab, info)
    _, E_po, ipo = microdoppler_series(spec, fc=FC, az=AZ, el=EL, prf=PRF, n_t=N_T)

    d_po, a_po, r_po = dc_ac(E_po)
    d_sb, a_sb, r_sb = dc_ac(E_sbr)
    gain = 20 * np.log10(r_po / r_sb)

    fig = plt.figure(figsize=(16.2, 5.6), constrained_layout=True)
    gs = fig.add_gridspec(1, 3, width_ratios=[1, 1, 0.52])
    fig.suptitle(f"Occlusion makes micro-Doppler {gain:.1f} dB easier to see", fontsize=17, fontweight="bold")

    for j, (E, nm, sub) in enumerate(
            ((E_po, "PO (no occlusion)", f"|DC|/std(AC) = {r_po:.0f}  (+{20*np.log10(r_po):.1f} dB)"),
             (E_sbr, "SBR (occlusion included)", f"|DC|/std(AC) = {r_sb:.1f}  (+{20*np.log10(r_sb):.1f} dB)"))):
        ax = fig.add_subplot(gs[0, j])
        f, tt, S = spectrogram(E, PRF, nperseg=64, noverlap=58, nfft=1024)
        im = ax.pcolormesh(tt * 1e3, f, S, cmap="turbo", vmin=-45, vmax=0, shading="gouraud")
        for sgn in (+1, -1):
            ax.axhline(sgn * info["f_tip"], color="k", ls="--", lw=1.6, zorder=5)
        ax.text(tt[-1] * 1e3 * 0.99, info["f_tip"], f" tip Doppler +{info['f_tip']:.0f} Hz ",
                color="k", fontsize=8, ha="right", va="bottom", zorder=6)
        ax.set_ylim(-2.2 * info["f_tip"], 2.2 * info["f_tip"])
        ax.set_xlabel("Time [ms]"); ax.set_ylabel("Doppler frequency [Hz]")
        ax.set_title(f"{nm}\n{sub}", fontsize=12,
                     color=("#b3261e" if j == 0 else "#1b5e20"), fontweight="bold")
        fig.colorbar(im, ax=ax, fraction=0.046, label="Normalized power [dB]")

    # 막대: 정적 받침대 대비 블레이드 변조
    ax = fig.add_subplot(gs[0, 2])
    vals = [20 * np.log10(r_po), 20 * np.log10(r_sb)]
    bars = ax.bar(["PO", "SBR"], vals, color=["#e57373", "#66bb6a"], width=0.55, edgecolor="k")
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.8, f"+{v:.1f} dB", ha="center", fontsize=11,
                fontweight="bold")
    ax.annotate("", xy=(1.36, vals[1]), xytext=(1.36, vals[0]),
                arrowprops=dict(arrowstyle="<->", color="#1a237e", lw=2.2))
    ax.text(1.44, (vals[0] + vals[1]) / 2, f"{gain:.1f} dB\neasier", color="#1a237e",
            fontsize=12, fontweight="bold", va="center")
    ax.set_xlim(-0.6, 2.1)
    ax.set_ylim(0, vals[0] * 1.28); ax.set_ylabel("Static pedestal above blade AC  [dB]")
    ax.set_title("Body pedestal |DC| / blade std(AC)", fontsize=11)
    ax.grid(axis="y", alpha=0.3)

    fig.supxlabel(
        f"{_NAME[target]} hovering, az {AZ:.0f}° / el {EL:.0f}°, {FC/1e9:.1f} GHz, "
        f"{info['rpm']:.0f} rpm (assumed - DJI does not publish it). Static 0-Doppler removed before the STFT.\n"
        "PO counts scatterers the rays never reach (battery/PCB inside the shell, blade backsides), inflating |DC| and "
        "cancelling part of the blade modulation.\n"
        f"SBR integrates only the first ray hit: the pedestal drops {20*np.log10(d_sb/d_po):.1f} dB and the blade "
        f"modulation deepens {20*np.log10(a_sb/a_po):+.1f} dB - the same blade lines now sit far above the body. "
        "The speckle in the SBR panel is ray-grid discretisation noise ($\\lambda$/32 grid, 44 dB below the strongest blade line).",
        fontsize=8.5, color="0.45")
    fn = os.path.join(outdir, "report3_microdoppler.png")
    fig.savefig(fn, dpi=130); plt.close(fig)
    print("[fig] ", os.path.relpath(fn, ROOT))
    return fn, dict(po=dict(dc=d_po, ac=a_po, ratio=r_po, ratio_db=20 * np.log10(r_po)),
                    sbr=dict(dc=d_sb, ac=a_sb, ratio=r_sb, ratio_db=20 * np.log10(r_sb)),
                    gain_db=gain, f_tip=info["f_tip"], flash_hz=info["flash_hz"],
                    v_tip=info["v_tip"], rpm=info["rpm"], f_tip_po=ipo["f_tip"])


# --------------------------------------------------------------------------- #
#  (2) 5종 드론 — SBR 스펙트로그램
# --------------------------------------------------------------------------- #
def fig_drones(outdir=FIG, tables=None):
    keys = list(DRONES.keys())
    fig, axes = plt.subplots(1, len(keys), figsize=(21, 4.9), constrained_layout=True)
    fig.suptitle("Blade micro-Doppler of five drones - SBR (occlusion included)",
                 fontsize=17, fontweight="bold")
    rows = {}
    for ax, k in zip(axes, keys):
        tab, info = (tables[k] if tables and k in tables else sbr_phase_table(DRONES[k]))
        t, E = series_from_table(tab, info, n_t=1200)     # 60 ms — 플래시 줄무늬가 넓게 보이도록
        dc, ac, r = dc_ac(E)
        rows[k] = dict(rpm=info["rpm"], f_tip=info["f_tip"], flash=info["flash_hz"],
                       v_tip=info["v_tip"], n_rotors=info["n_rotors"], ratio=r,
                       ratio_db=20 * np.log10(r))
        f, tt, S = spectrogram(E, PRF, nperseg=64, noverlap=58, nfft=1024)
        im = ax.pcolormesh(tt * 1e3, f, S, cmap="turbo", vmin=-45, vmax=0, shading="gouraud")
        for sgn in (+1, -1):
            ax.axhline(sgn * info["f_tip"], color="k", ls="--", lw=1.4, zorder=5)
        ax.set_ylim(-2200, 2200)
        ax.set_xlabel("Time [ms]")
        ax.set_title(f"{_NAME[k]}\n{info['n_rotors']} rotors, {info['rpm']:.0f} rpm (assumed)\n"
                     f"tip {info['v_tip']:.0f} m/s $\\rightarrow$ $\\pm${info['f_tip']:.0f} Hz, "
                     f"flash {info['flash_hz']:.0f} Hz", fontsize=10)
        ax.text(0.03, 0.03, f"|DC|/AC {r:.1f}", transform=ax.transAxes, fontsize=9,
                color="w", fontweight="bold",
                bbox=dict(fc="k", alpha=0.45, ec="none", pad=2))
    axes[0].set_ylabel("Doppler frequency [Hz]")
    fig.colorbar(im, ax=axes[-1], fraction=0.046, label="Normalized power [dB]")
    fig.supxlabel(
        "Same look (az 0° / el 15°), 3.5 GHz, hover rpm assumed per propeller size. Dashed = $\\pm$tip Doppler. "
        "Static 0-Doppler removed.\n"
        "Big propellers turn slower: S1000+ (15 in, 3500 rpm) flashes at 117 Hz, Mini5Pro (6 in, 7500 rpm) at 250 Hz - "
        "the flash rate alone separates the airframes.",
        fontsize=8.5, color="0.45")
    fn = os.path.join(outdir, "report3_md_drones.png")
    fig.savefig(fn, dpi=125); plt.close(fig)
    print("[fig] ", os.path.relpath(fn, ROOT))
    return fn, rows


# --------------------------------------------------------------------------- #
#  (3) 선 스펙트럼 + 창 길이 — "점선 너머 에너지"의 정체
# --------------------------------------------------------------------------- #
def fig_spectrum(outdir=FIG, target="mavic4pro", tab=None, info=None):
    from scipy.signal import welch
    spec = DRONES[target]
    if tab is None:
        tab, info = sbr_phase_table(spec)
    f, H, f0 = line_spectrum(tab, info)
    ac = H.copy(); ac[np.argmin(abs(f))] = 0.0            # 0-도플러(몸체) 제거
    pk = float(abs(ac).max())
    L = 20 * np.log10(abs(ac) / pk + 1e-30)
    floor_db = 20 * np.log10(float(np.median(abs(ac[abs(f) > 10_000]))) / pk)   # 광선격자 잡음 바닥
    P = abs(ac) ** 2
    inside = 100 * P[abs(f) <= info["f_tip"]].sum() / P.sum()

    t, E = series_from_table(tab, info, n_t=16384)
    E = E - E.mean()

    fig, axes = plt.subplots(1, 2, figsize=(15.2, 5.4), constrained_layout=True)
    fig.suptitle("What lies beyond the tip-Doppler line: window leakage vs real AM sidebands",
                 fontsize=16, fontweight="bold")

    ax = axes[0]
    m = abs(f) <= 4000
    ax.vlines(f[m], -60, L[m], color="#1565c0", lw=1.4)
    ax.plot(f[m], L[m], "o", ms=2.6, color="#0d47a1")
    for sgn in (+1, -1):
        ax.axvline(sgn * info["f_tip"], color="k", ls="--", lw=1.6)
        ax.axvline(sgn * info["f_kin"], color="#b71c1c", ls=":", lw=1.6)
    ax.axhline(floor_db, color="0.5", ls="-.", lw=1.2)
    ax.text(-3900, floor_db + 1.2, f"SBR ray-grid noise floor {floor_db:.1f} dB", fontsize=8, color="0.35")
    ax.text(info["f_tip"] + 60, -3, f"$f_{{tip}}$ {info['f_tip']:.0f} Hz", fontsize=9, rotation=90, va="top")
    ax.text(info["f_kin"] + 60, -30, f"kinematic bound {info['f_kin']:.0f} Hz", fontsize=8, rotation=90,
            va="top", color="#b71c1c")
    ax.set_xlim(-4000, 4000); ax.set_ylim(-60, 5)
    ax.set_xlabel("Doppler frequency [Hz]"); ax.set_ylabel("Line level re strongest line [dB]")
    ax.set_title(f"Exact line spectrum - no window\nharmonics of the {f0:.1f} Hz blade flash, "
                 f"{inside:.1f}% of AC power inside $\\pm f_{{tip}}$", fontsize=11)
    ax.grid(alpha=0.25)

    ax = axes[1]
    for nps, col in ((64, "#e53935"), (256, "#fb8c00"), (1024, "#1e88e5"), (4096, "#2e7d32")):
        fw, Pw = welch(E, fs=PRF, nperseg=nps, noverlap=nps // 2, return_onesided=False,
                       scaling="spectrum", detrend=False)
        o = np.argsort(fw); fw, Pw = fw[o], Pw[o]
        Pdb = 10 * np.log10(Pw / Pw.max())
        ax.plot(fw, Pdb, color=col, lw=1.4,
                label=f"window {nps/PRF*1e3:.1f} ms ({nps} pts)" + (" - used in the STFT" if nps == 64 else ""))
    for sgn in (+1, -1):
        ax.axvline(sgn * info["f_tip"], color="k", ls="--", lw=1.6)
    ax.set_xlim(-4000, 4000); ax.set_ylim(-70, 3)
    ax.set_xlabel("Doppler frequency [Hz]"); ax.set_ylabel("Power re peak [dB]")
    ax.set_title("Same signal through windows of increasing length", fontsize=11)
    ax.legend(fontsize=8, loc="lower right"); ax.grid(alpha=0.25)

    fig.supxlabel(
        "Left: the rotating drone is periodic in $\\varphi$, so its spectrum is a line spectrum - "
        "sampling one period exactly gives it with zero leakage.\n"
        f"{inside:.1f}% of the AC power sits inside $\\pm f_{{tip}}$; the lines past the kinematic bound "
        f"({info['f_kin']:.0f} Hz = 2$\\omega R_{{mesh}}$/$\\lambda$ cos el) are 20-40 dB down and are AM sidebands of the blade "
        "flash, not kinematic Doppler - no scatterer in the model moves faster.\n"
        "Right: the same signal through longer windows. The smooth skirt of the 3.2 ms window (red - the one used in the "
        "STFT) is window leakage: lengthen the window 64x and it collapses ~16 dB, resolving into the discrete lines. "
        "So not all of the energy past the dashed line is leakage - the AM-sideband lines (25-40 dB down) survive any window.",
        fontsize=8.5, color="0.45")
    fn = os.path.join(outdir, "report3_md_spectrum.png")
    fig.savefig(fn, dpi=130); plt.close(fig)
    print("[fig] ", os.path.relpath(fn, ROOT))
    return fn, dict(floor_db=floor_db, inside_pct=inside, f_kin=info["f_kin"], R_mesh=info["R_mesh"])


# --------------------------------------------------------------------------- #
#  (4) Sionna 렌더 — 분절 드론을 시뮬레이터가 직접 그린다
# --------------------------------------------------------------------------- #
def _render_pose(spec, tmpdir, tag, body_rpy=(0, 0, 0), phases=None, cam_key="iso",
                 spp=384, res=(760, 570), fov=35.0):
    """pose_articulated 메쉬 → 부위별 OBJ → Sionna 씬 → PNG. (drone_parts 는 정적 메쉬만 쓰므로 직접 조립)"""
    m = pose_articulated(spec, body_rpy=body_rpy, rotor_phase_deg=phases)
    d = os.path.join(tmpdir, tag)
    paths = m.write_obj_per_group(d, "pose")
    cols = drone_colors(spec)
    parts = [Part(name=f"{spec.key}_{g}", obj=p, mat_key=DRONE_GROUP_MAT[g][0], color=cols[g])
             for g, p in paths.items()]
    scene = build_scene(parts, fc=FC)
    V = np.asarray(m.v, float)
    c = 0.5 * (V.max(0) + V.min(0))
    r = float(np.linalg.norm(V.max(0) - V.min(0))) * 1.35        # fov 35° 에 꽉 차게
    pos = {"iso": (c[0] + r * 0.72, c[1] - r * 0.60, c[2] + r * 0.42),
           "top": (c[0] + 0.01 * r, c[1], c[2] + r)}[cam_key]
    camera = rt.Camera(position=mi.Point3f(*[float(v) for v in pos]),
                       look_at=mi.Point3f(*[float(v) for v in c]))
    fn = os.path.join(RTDIR, f"{tag}.png")
    os.makedirs(RTDIR, exist_ok=True)
    scene.render_to_file(camera=camera, filename=fn, num_samples=spp, resolution=res, fov=fov)
    return fn


def fig_rt_articulation(outdir=FIG, target="mavic4pro", spp=512):
    """Sionna 렌더판 분절 검증 — mpl 도해(report3_articulation.png)와 같은 실험, 렌더러만 Sionna."""
    spec = DRONES[target]; n = spec.num_rotors
    dirs = [(1 if k % 2 == 0 else -1) for k in range(n)]
    tmp = tempfile.mkdtemp(prefix="rt3_artic_")
    print("④ Sionna 렌더 — 분절 검증")
    row1 = [("level", (0, 0, 0)), ("roll 30°", (30, 0, 0)), ("pitch 30°", (0, 30, 0)), ("yaw 45°", (0, 0, 45))]
    imgs1 = [_render_pose(spec, tmp, f"rt3_body_{lab.split()[0]}", body_rpy=rpy, spp=spp) for lab, rpy in row1]
    imgs2 = [_render_pose(spec, tmp, f"rt3_spin_{ph:03d}", phases=[d * ph for d in dirs],
                          cam_key="top", spp=spp) for ph in (0, 45, 90, 135)]

    fig, axes = plt.subplots(2, 4, figsize=(15, 8.0), constrained_layout=True)
    fig.suptitle(f"Articulation, rendered by Sionna RT - {_NAME[target]}", fontsize=16, fontweight="bold")
    for ax, (lab, _), p in zip(axes[0], row1, imgs1):
        ax.imshow(mpimg.imread(p)); ax.set_axis_off(); ax.set_title(f"Body {lab}", fontsize=11)
    for ax, ph, p in zip(axes[1], (0, 45, 90, 135), imgs2):
        ax.imshow(mpimg.imread(p)); ax.set_axis_off()
        ax.set_title(f"Propeller spin {ph}° (top view)", fontsize=11)
    fig.supxlabel(
        "Every frame is a Sionna RT render of the mesh that the SBR micro-Doppler actually integrates "
        "(pose_articulated -> per-group OBJ -> Sionna scene).\n"
        "Top: body tilt only, propellers frozen. Bottom: body level, propellers only - and neighbouring rotors "
        "counter-rotate, so the diagonal pair stays in phase.",
        fontsize=8.5, color="0.45")
    fn = os.path.join(outdir, "report3_rt_articulation.png")
    fig.savefig(fn, dpi=125); plt.close(fig)
    print("[fig] ", os.path.relpath(fn, ROOT))
    return fn


def rt_spin_frames(target="mavic4pro", frames=36, spp=256, res=(640, 480)):
    """프로펠러 위상 φ 를 한 플래시 주기(=180°)에 걸쳐 도는 Sionna 렌더 프레임."""
    spec = DRONES[target]
    dirs = [r["dir"] for r in rotor_layout(spec)]
    tmp = tempfile.mkdtemp(prefix="rt3_spin_")
    out = []
    period = 360.0 / spec.prop_blades
    for i in range(frames):
        ph = period * i / frames
        out.append(_render_pose(spec, tmp, f"rt3_frame_{i:03d}", phases=[d * ph for d in dirs],
                                cam_key="iso", spp=spp, res=res))
        if i % 12 == 0:
            print(f"  frame {i:2d}/{frames}")
    return out


def gif_rt_spin(outdir=FIG, frames=None, fps=14):
    """Sionna 렌더 프로펠러 스핀 GIF."""
    from PIL import Image
    frames = frames or rt_spin_frames()
    imgs = [Image.open(p).convert("P", palette=Image.ADAPTIVE) for p in frames]
    fn = os.path.join(outdir, "report3_rt_spin.gif")
    imgs[0].save(fn, save_all=True, append_images=imgs[1:], duration=int(1000 / fps), loop=0, optimize=True)
    print("[gif] ", os.path.relpath(fn, ROOT))
    return fn


# --------------------------------------------------------------------------- #
#  (5) 애니메이션 — Sionna 렌더(왼쪽) + SBR 스펙트로그램 시간커서(오른쪽)
# --------------------------------------------------------------------------- #
def gif_anim_microdoppler(outdir=FIG, target="mavic4pro", tab=None, info=None,
                          frames=None, n_flash=3, fps=12):
    """왼쪽 = Sionna 가 렌더한 그 자세, 오른쪽 = 그 자세가 만든 SBR 스펙트로그램 위의 시간커서.
    시간창 = 플래시 3주기. 프레임의 φ 와 스펙트로그램의 시간축은 **같은 φ(t)=360·rpm/60·t** 에서 온다."""
    spec = DRONES[target]
    if tab is None:
        tab, info = sbr_phase_table(spec)
    frames = frames or rt_spin_frames(target, frames=36)
    n_fr = len(frames)
    T = n_flash / info["flash_hz"]                       # 표시 구간 [s]
    n_t = int(round(T * PRF))
    t, E = series_from_table(tab, info, n_t=n_t)
    f, tt, S = spectrogram(E, PRF, nperseg=64, noverlap=60, nfft=1024)

    # 프레임 i 의 시각: φ 는 프레임당 (period/n_fr) 씩 증가 → 한 프레임 = period/(n_fr·360·rpm/60) 초
    dt_frame = (info["period_deg"] / n_fr) / (360.0 * info["rpm"] / 60.0)
    n_show = int(np.ceil(T / dt_frame))                  # 3플래시 = 프레임 3바퀴

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(12.4, 4.9), constrained_layout=True,
                                   gridspec_kw=dict(width_ratios=[0.85, 1.15]))
    fig.suptitle(f"{_NAME[target]} - Sionna render (left) and the SBR micro-Doppler it produces (right)",
                 fontsize=13, fontweight="bold")
    im0 = axL.imshow(mpimg.imread(frames[0])); axL.set_axis_off()
    im = axR.pcolormesh(tt * 1e3, f, S, cmap="turbo", vmin=-45, vmax=0, shading="gouraud")
    for sgn in (+1, -1):
        axR.axhline(sgn * info["f_tip"], color="k", ls="--", lw=1.4)
    axR.set_ylim(-2.2 * info["f_tip"], 2.2 * info["f_tip"])
    axR.set_xlim(tt[0] * 1e3, tt[-1] * 1e3)          # 커서(axvline)가 축을 넓히지 않도록 고정
    axR.set_xlabel("Time [ms]"); axR.set_ylabel("Doppler frequency [Hz]")
    fig.colorbar(im, ax=axR, fraction=0.046, label="Normalized power [dB]")
    cur = axR.axvline(tt[0] * 1e3, color="w", lw=2.2)
    cur.set_path_effects([pe.Stroke(linewidth=4.0, foreground="k"), pe.Normal()])
    txt = axL.set_title("", fontsize=10)

    def update(i):
        im0.set_data(mpimg.imread(frames[i % n_fr]))
        tc = float(np.clip((i * dt_frame) * 1e3, tt[0] * 1e3, tt[-1] * 1e3))   # STFT 축 안으로
        cur.set_xdata([tc, tc])
        phi = (360.0 * info["rpm"] / 60.0) * (i * dt_frame)
        txt.set_text(f"rotor phase $\\varphi$ = {phi % 360:5.0f}°   t = {tc:5.2f} ms")
        return ()

    anim = FuncAnimation(fig, update, frames=n_show, blit=False)
    os.makedirs(outdir, exist_ok=True)
    fn = os.path.join(outdir, "report3_anim_microdoppler.gif")
    anim.save(fn, writer=PillowWriter(fps=fps), dpi=92)
    plt.close(fig)
    print("[gif] ", os.path.relpath(fn, ROOT))
    return fn


# --------------------------------------------------------------------------- #
def build_all(outdir=FIG):
    os.makedirs(outdir, exist_ok=True)
    t0 = time.time()
    print("① SBR 위상 테이블 (5종 × n_phase=%d, λ/%d)" % (N_PHASE, SBR_DIV))
    tables = {k: sbr_phase_table(DRONES[k]) for k in DRONES}

    print("\n② 헤드라인 — PO vs SBR")
    tab, info = tables["mavic4pro"]
    _, head = fig_po_vs_sbr(outdir, tab=tab, info=info)
    print(f"   PO  |DC|/std(AC) = {head['po']['ratio']:.1f} (+{head['po']['ratio_db']:.1f} dB)")
    print(f"   SBR |DC|/std(AC) = {head['sbr']['ratio']:.1f} (+{head['sbr']['ratio_db']:.1f} dB)")
    print(f"   ⇒ 가림이 주는 이득 {head['gain_db']:.1f} dB")

    print("\n③ 5종 SBR 스펙트로그램 / 선 스펙트럼")
    _, rows = fig_drones(outdir, tables={k: v for k, v in tables.items()})
    _, spec_info = fig_spectrum(outdir, tab=tab, info=info)

    fig_rt_articulation(outdir)
    print("\n⑤ Sionna 렌더 프레임 → GIF 2종")
    frames = rt_spin_frames()
    gif_rt_spin(outdir, frames=frames)
    gif_anim_microdoppler(outdir, tab=tab, info=info, frames=frames)

    js = dict(headline=head, drones=rows, spectrum=spec_info,
              cfg=dict(fc=FC, az=AZ, el=EL, prf=PRF, n_t=N_T, n_phase=N_PHASE, sbr_div=SBR_DIV))
    p = os.path.join(OUT, "report3_microdoppler.json")
    with open(p, "w") as fh:
        json.dump(js, fh, indent=1, ensure_ascii=False)
    print(f"\n[json] {os.path.relpath(p, ROOT)}")
    print(f"✅ report3 SBR/Sionna 그림 완료 ({time.time()-t0:.0f}s)")
    return js


if __name__ == "__main__":
    build_all()
