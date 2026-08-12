# -*- coding: utf-8 -*-
"""refute_nadir_mechanism_final.py — **중단된 반증을 끝낸다.**

배경(2026-08-12)
----------------
`outputs/verify_nadir_flash.json` 이 «앙각 −90°(나딧)에서도 126.67 Hz 빗살이 남고,
그 기전은 근접장 파면 곡률이며 거리에 1/r⁴ 로 죽는다» 고 결론지었다. 그 근거는
**평면 패싯 PO 대리모형**(재질·가림·다중반사·격자 없음)이었다. 반증이 중단됐다.

이 스크립트가 하는 일 — ⭐**커널을 CPU 로 다시 구현해서** 판정한다.
  R1 거리법칙   원장 표의 지수를 실제로 적합한다(1/r⁴ 인가).
  R2 해석       나딧 원운동은 거리가 안 변한다 → 도플러 0. 그런데 허브가 팔길이 L 만큼
                밀려 있으면 ρ² = L²+r²+2Lr·cosψ 가 변한다. 그 항을 실제 L·r 로 계산하고
                관측 위상진폭과 맞춰 본다. **원거리장 정확 불변성**도 증명한다.
  R3 잣대       «누설» 판정이 창 길이에 강건한가.
  R4 ⭐격자잡음  **가장 중요한 질문.** 나딧 잔여가 격자 표본화 잡음에 묻혀 있나.
                → `sbr_field` 의 격자·가림·투과·위상을 numpy 로 재현하고(GPU 없음)
                  격자 사다리 λ/8…λ/48 을 올려 «격자를 조이면 사라지나» 를 직접 본다.
  R5 탐지       링크버짓으로 40 m·100 m 에서 잡음 위로 올라오는지 답한다.

⚠ **GPU 를 쓰지 않는다.** mitsuba/sionna 를 아예 import 하지 않는다. 광선은 나딧 방향
  z-버퍼 래스터화로 CPU 에서 쏜다(평행 격자·최근접 히트·셸 투과 2패스까지 커널과 같은 배선).

    PYTHONPATH=src:benchmark python benchmark/refute_nadir_mechanism_final.py
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from drones import DRONES                                   # noqa: E402
from articulated_fast import FastPoser, rotor_phases        # noqa: E402
from md_mapstyle import auto_periods, flash_spec            # noqa: E402

OUT_J = f"{ROOT}/outputs/refute_nadir_mechanism_final.json"
OUT_P = f"{ROOT}/outputs/refute_nadir_mechanism_final.png"
SRC_J = f"{ROOT}/outputs/verify_nadir_flash.json"
SWEEP_N = f"{ROOT}/outputs/elevation_sweep_md.npz"

TJ = json.load(open(f"{ROOT}/outputs/report07_three_engines.json"))["_meta"]
PRF = float(TJ["prf_hz"]); N = int(TJ["n"])
FFL = float(TJ["f_flash_hz"]); FT = float(TJ["f_tip_hz"])
RPMS = np.asarray(TJ["rpm_per_rotor"], float)
FC, RANGE_M = 3.5e9, 10.0
C0 = 2.99792458e8
LAM = C0 / FC; K = 2 * np.pi / LAM
LO, HI = 0.35 * FT, FT                     # 덱의 고정 대역 430~1229 Hz

#  |Γ| — 원장 outputs/material_sources.json 에서 읽은 값(근거를 원장에 적는다).
#    prop_plastic  : /propeller/per_drone/matrice4e/gamma_thinslab/"5G 3.5 GHz"/at_t_chordmean
#    plastic       : /itu_plasterboard_check/"5G 3.5 GHz"/gamma_ours
#    carbon        : /carbon_sigma_sensitivity/"5G 3.5 GHz"/1e+04/gamma_bulk
#    metal         : 1.0 (PEC), camera_assembly 0.85 (drones.py 주석), pcb 0.9 (추정)
GAM = {"prop": 0.0881, "body": 0.2437, "canopy": 0.2437, "gear": 0.2437,
       "accent": 0.2437, "arm": 0.9938, "motor": 1.0, "battery": 1.0,
       "camera": 0.85, "pcb": 0.9}
SHELL = ("body", "canopy")                  # rcs_sbr._DIELECTRIC_SHELLS


# ════════════════════════════════════════════════════════════════════════════
#  공통 잣대
# ════════════════════════════════════════════════════════════════════════════
def acdc_db(x) -> float:
    x = np.asarray(x, complex)
    return float(10 * np.log10(np.mean(np.abs(x / x.mean() - 1.0) ** 2) + 1e-300))


def ac_series(x):
    x = np.asarray(x, complex)
    return x / x.mean() - 1.0


def corr(a, b) -> float:
    a = np.asarray(a, complex); b = np.asarray(b, complex)
    return float(np.abs(np.vdot(a, b)) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-300))


def fit_exponent(R, acdc):
    """AC/DC[dB] = c − 10·n·log10(R) 의 n 을 최소제곱으로 적합."""
    R = np.asarray(R, float); y = np.asarray(acdc, float)
    A = np.vstack([np.ones_like(R), -10 * np.log10(R)]).T
    sol, *_ = np.linalg.lstsq(A, y, rcond=None)
    pred = A @ sol
    return float(sol[1]), float(np.max(np.abs(pred - y)))


# ════════════════════════════════════════════════════════════════════════════
#  R1. 원장 표의 거리 지수 — 산수부터
# ════════════════════════════════════════════════════════════════════════════
def r1_ledger_law() -> dict:
    src = json.load(open(SRC_J))["C_D_geometry"]
    tab = src["range_sweep_nadir"]
    R = np.array([float(k[:-1]) for k in tab])
    y = np.array([tab[k] for k in tab])
    o = np.argsort(R); R, y = R[o], y[o]
    n_fit, resid = fit_exponent(R, y)
    seg = {}
    for i in range(1, len(R)):
        ratio = R[i] / R[0]
        seg[f"{int(R[0])}->{int(R[i])}m"] = dict(
            ratio=round(float(ratio), 3),
            measured_drop_db=round(float(y[0] - y[i]), 2),
            drop_if_r4_db=round(float(40 * np.log10(ratio)), 2),
            implied_exponent=round(float((y[0] - y[i]) / (10 * np.log10(ratio))), 3))
    return dict(
        table_db={k: tab[k] for k in tab},
        global_fit_exponent=round(n_fit, 3), max_resid_db=round(resid, 2),
        per_segment=seg,
        orchestrator_arithmetic_check_ko=(
            "지시문은 «1/r⁴ 이면 2.5배 거리에 −7.96 dB» 라고 했다. 이것은 틀렸다 — "
            "7.96 dB = 20·log10(2.5) 로 **1/r² 의 값**이다. 1/r⁴ 은 40·log10(2.5) = 15.92 dB 다. "
            "20→50 m 의 실측 낙폭 16.16 dB 는 15.92 dB 와 0.24 dB 차이다."),
        verdict_ko=("표는 1/r⁴ 을 **지지한다**. 전 구간 적합 지수 "
                    f"{n_fit:.3f} (잔차 ≤{resid:.2f} dB), 구간별 4.04~4.16, 거리가 멀수록 4.00 에 수렴."))


# ════════════════════════════════════════════════════════════════════════════
#  R2. 해석 — 나딧에서 왜 0 이 아닌가
# ════════════════════════════════════════════════════════════════════════════
def r2_analytic(fp, ph, F, G, meas) -> dict:
    spec = DRONES["matrice4e"]
    V0 = np.asarray(fp.pose(ph[0]).v, float)
    isp = np.asarray(G) == "prop"
    vp = V0[np.unique(F[isp].ravel())]
    hubs, rtip = [], []
    for sx in (1, -1):
        for sy in (1, -1):
            m = (np.sign(vp[:, 0]) == sx) & (np.sign(vp[:, 1]) == sy)
            c = vp[m][:, :2].mean(0)
            hubs.append(float(np.linalg.norm(c)))
            rtip.append(float(np.linalg.norm(vp[m][:, :2] - c, axis=1).max()))
    L = float(np.mean(hubs)); r_t = float(np.mean(rtip))
    om = 2 * np.pi * float(np.mean(RPMS)) / 60.0
    R = RANGE_M

    #  ① 나딧 원운동은 거리를 안 바꾼다(허브가 축 위에 있을 때) — 정확히 0.
    #  ② 허브가 L 만큼 밀리면 ρ² = L²+r²+2Lr·cosψ  →  d = √(R²+ρ²)
    d_max = np.sqrt(R ** 2 + (L + r_t) ** 2); d_min = np.sqrt(R ** 2 + (L - r_t) ** 2)
    dphase_pp = 2 * K * (d_max - d_min)                    # 왕복 위상 진폭(peak-to-peak)
    a_tip = 2 * K * L * r_t / R                            # 근사 진폭 2kLr/R [rad]
    fd_max = (2.0 / LAM) * L * r_t * om / np.sqrt(R ** 2 + L ** 2 + r_t ** 2)

    #  ③ 2엽 상쇄 — exp(+ia cosψ)+exp(−ia cosψ) = 2cos(a cosψ) ≈ 2 − a²(1+cos2ψ)/2
    #     → 로터 기여의 상대 변조 = a²/4 (2ψ, 즉 f_flash 에서), 진폭 1차는 상쇄된다.
    #     블레이드를 따라 a(r) ∝ r 이므로 면적가중 ⟨r²⟩ 를 실제 프롭 면적으로 잰다.
    #     (나딧 투영면적 가중)
    a3 = V0[F[isp][:, 0]]; b3 = V0[F[isp][:, 1]]; c3 = V0[F[isp][:, 2]]
    nn = np.cross(b3 - a3, c3 - a3); w = 0.5 * np.abs(nn[:, 2])       # 투영면적
    cen = (a3 + b3 + c3) / 3.0
    hubxy = []
    for sx in (1, -1):
        for sy in (1, -1):
            m = (np.sign(vp[:, 0]) == sx) & (np.sign(vp[:, 1]) == sy)
            hubxy.append(vp[m][:, :2].mean(0))
    hubxy = np.asarray(hubxy)
    j = np.argmin(np.linalg.norm(cen[:, None, :2] - hubxy[None, :, :], axis=2), axis=1)
    rr = np.linalg.norm(cen[:, :2] - hubxy[j], axis=1)
    r2_w = float((w * rr ** 2).sum() / w.sum())
    a_eff = 2 * K * L * np.sqrt(r2_w) / R
    pred_rotor_mod = a_eff ** 2 / 4.0                       # 로터 기여 대비 상대 변조
    prop_share = float(w.sum() * GAM["prop"])               # 대략적 밝기 몫(가중 투영면적)
    #  관측
    obs = dict(am_rms=meas["am_rms"], pm_rms_deg=meas["pm_rms_deg"],
               p95_deg=meas["phase_dev_p95_deg"], ac_over_dc_db=meas["ac_over_dc_db"])
    return dict(
        geometry_from_mesh=dict(hub_radius_m=round(L, 4), hub_radii_m=[round(x, 4) for x in hubs],
                                blade_tip_radius_m=round(r_t, 4),
                                blades=int(spec.prop_blades), rpm_mean=float(np.mean(RPMS)),
                                omega_rad_s=round(om, 2), range_m=R, lambda_m=round(LAM, 6)),
        per_element=dict(
            two_way_phase_swing_pp_deg=round(float(np.degrees(dphase_pp)), 2),
            two_way_phase_amplitude_deg=round(float(np.degrees(a_tip)), 2),
            approx_2kLr_over_R_rad=round(float(a_tip), 4),
            max_doppler_hz=round(float(fd_max), 2),
            note_ko=("나딧이라도 **허브가 축 밖에 있으면** 블레이드 끝의 왕복거리가 변한다. "
                     "이 값이 «도플러가 0 이 아니다» 의 크기다. 허브가 축 위에 있으면(단위시험의 "
                     "궤도 구) 정확히 0 이다 — 그래서 그 시험의 나딧 잔여는 전부 격자 잡음이다.")),
        two_blade_cancellation=dict(
            weighted_mean_r2_m2=round(r2_w, 5),
            a_eff_rad=round(float(a_eff), 4),
            predicted_rotor_relative_mod_amplitude=round(float(pred_rotor_mod), 5),
            predicted_ac_over_dc_db=round(float(10 * np.log10(pred_rotor_mod ** 2 / 2)), 2),
            formula_ko=("2엽 로터: exp(+ja·cosψ)+exp(−ja·cosψ)=2cos(a·cosψ)≈2−a²(1+cos2ψ)/2 "
                        "→ 상대변조 진폭 m=a²/4, rms 전력비 = m²/2. a=2kL√⟨r²⟩/R."),
            comb_frequency_ko="1차가 상쇄되고 2ψ 가 남는다 → 2엽 로터의 f_flash(126.67 Hz) 와 그 배음.",
            scaling_ko="a ∝ 1/R 이고 남는 항이 a² 이므로 진폭 ∝ 1/R², 전력 ∝ 1/R⁴.",
            observed=obs,
            comparison_ko=(
                f"해석 예측 {10*np.log10(pred_rotor_mod**2/2):.1f} dB 대 "
                f"관측 {obs['ac_over_dc_db']:.2f} dB — **2 dB 안**이다. 다만 이것은 «로터 기여만이 "
                "전부» 라고 놓은 값이라, 정확한 예측이 아니라 **크기의 눈금**으로 읽어야 한다.")),
        pm_vs_am_ko=(
            "⭐원장의 «위상이 진폭보다 크다(+7.37 dB) → 작은 도플러가 남았다» 는 **추론이 틀렸다**. "
            "2엽 상쇄가 남기는 인자 2cos(a·cosψ) 는 **실수**다 — 즉 로터 페이저의 크기만 흔든다. "
            "그것이 총합에서 AM 으로 보이나 PM 으로 보이나는 «로터 페이저와 총 페이저의 사잇각 θ» 하나로 "
            f"정해진다(PM/AM = |tanθ|). 관측 +7.37 dB 는 θ = {np.degrees(np.arctan(10**(7.37/20))):.1f}° 를 "
            "뜻할 뿐이다. (도플러가 남는다는 결론 자체는 참이지만 근거는 위 per_element 다.)"),
    )


# ════════════════════════════════════════════════════════════════════════════
#  R3. 잣대 — 창 길이를 바꿔도 «누설» 판정이 같은가
# ════════════════════════════════════════════════════════════════════════════
def band_metrics(E, nperseg):
    #  flash_spec 은 조각 길이를 «블레이드 주기의 배수» 로 받는다 → 원하는 표본 수로 환산
    per = float(nperseg) / (PRF / FFL)
    f, t, S, _ = flash_spec(np.asarray(E, complex), PRF, FFL, per)
    b = (np.abs(f) >= LO) & (np.abs(f) <= HI)
    if b.sum() < 2:
        return None, None, int(b.sum())
    g = (S[b, :] ** 2).sum(axis=0)
    pw = float(10 * np.log10(g.mean()))
    g = g - g.mean()
    dt = float(t[1] - t[0]); m = len(g)
    A = np.abs(np.fft.rfft(g * np.hanning(m), n=64 * m))
    fr = np.fft.rfftfreq(64 * m, dt)
    if A.max() <= 0:
        return None, pw, int(b.sum())
    sel = (fr >= 40) & (fr <= 400)
    i0 = int(np.where(sel)[0][0]); i = int(np.argmax(A[sel] / A.max())) + i0
    return float(fr[i]), pw, int(b.sum())


def r3_window(z) -> dict:
    rows = {}
    for key in ("ours/el-90", "ours/el-15"):
        E = np.asarray(z[key], complex)
        F = np.fft.fft(E); fq = np.fft.fftfreq(N, 1 / PRF)
        F2 = F.copy(); F2[np.abs(fq) > 300.0] = 0
        Elp = np.fft.ifft(F2)
        r = {}
        for nps in (35, 48, 70, 96, 128, 192, 256, 384, 512):
            b1, p1, nb = band_metrics(E, nps)
            b2, p2, _ = band_metrics(Elp, nps)
            if p1 is None or p2 is None:
                continue
            r[str(nps)] = dict(bin_hz=round(PRF / nps, 1), n_band_bins=nb,
                               band_lo_in_bins=round(LO / (PRF / nps), 2),
                               mainlobe_halfwidth_hz=round(2 * PRF / nps, 1),
                               beat_hz=None if b1 is None else round(b1, 2),
                               band_power_db=round(p1, 2),
                               leakage_only_db=round(p2, 2),
                               true_over_leakage_db=round(p1 - p2, 2))
        #  창 없이 전체 4096-Hann FFT 로 잰 «진짜 대역 에너지»
        w = np.hanning(N); fr = np.fft.fftshift(np.fft.fftfreq(N, 1 / PRF))
        inb = (np.abs(fr) >= LO) & (np.abs(fr) <= HI)
        P = np.abs(np.fft.fftshift(np.fft.fft(E * w))) ** 2
        Plp = np.abs(np.fft.fftshift(np.fft.fft(Elp * w))) ** 2
        rows[key] = dict(per_window=r,
                         fullrecord_band_share_db=round(float(10 * np.log10(P[inb].sum() / P.sum())), 2),
                         fullrecord_band_share_lowpassed_db=round(
                             float(10 * np.log10(Plp[inb].sum() / Plp.sum())), 2))
    return rows


# ════════════════════════════════════════════════════════════════════════════
#  R4-a. 패싯 정확 대리모형(격자 없음·가림 없음) — 원장 C_D 의 독립 재구현
# ════════════════════════════════════════════════════════════════════════════
def facet_proxy(fp, ph, F, idx, ranges, gam_tri=None) -> dict:
    """w = max(n̂·û,0)·A, 위상은 (평면파) 또는 (구면파, 패싯 중심). 격자·가림 없음."""
    u = np.array([0.0, 0.0, -1.0])
    out = {f"{R:g}": np.zeros(idx.size, complex) for R in ranges}
    out["plane"] = np.zeros(idx.size, complex)
    out["first_order"] = np.zeros(idx.size, complex)
    V0 = np.asarray(fp.pose(ph[0]).v, float)
    ctr = 0.5 * (V0.min(0) + V0.max(0))
    for m, i in enumerate(idx):
        V = np.asarray(fp.pose(ph[int(i)]).v, float)
        a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
        nn = np.cross(b - a, c - a)
        A2 = np.linalg.norm(nn, axis=1)
        nh = nn / (A2[:, None] + 1e-300)
        cen = (a + b + c) / 3.0
        w = np.maximum(nh @ u, 0.0) * 0.5 * A2
        if gam_tri is not None:
            w = w * gam_tri
        pl = np.exp(1j * 2 * K * ((cen - ctr) @ u))
        out["plane"][m] = (w * pl).sum()
        rho2 = (cen[:, 0] - ctr[0]) ** 2 + (cen[:, 1] - ctr[1]) ** 2
        for R in ranges:
            ptx = ctr + R * u
            dd = np.linalg.norm(cen - ptx, axis=1)
            out[f"{R:g}"][m] = (w * np.exp(1j * 2 * K * (R - dd))).sum()
        #  1차 근사: R − |P−p_tx| ≈ (P−ctr)·û − ρ²/(2R)   (R = 10 m 판)
        out["first_order"][m] = (w * pl * (-1j * K * rho2 / RANGE_M)).sum()
    return out


# ════════════════════════════════════════════════════════════════════════════
#  R4-b. ⭐커널 CPU 재현기 — 평행 격자 + 최근접 히트(가림) + 셸 투과 2패스
# ════════════════════════════════════════════════════════════════════════════
def rot_to_nadir(el_deg):
    """û(az=0, el) 을 (0,0,−1) 로 보내는 회전행렬 — y 축 둘레 회전."""
    u = np.array([np.cos(np.radians(el_deg)), 0.0, np.sin(np.radians(el_deg))])
    t = np.array([0.0, 0.0, -1.0])
    v = np.cross(u, t); s = np.linalg.norm(v); c = float(u @ t)
    if s < 1e-12:
        return np.eye(3) if c > 0 else np.diag([1.0, -1.0, -1.0])
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + vx + vx @ vx * ((1 - c) / s ** 2)


def raster(V, F, x0, y0, d, n, keep=None):
    """나딧 z-버퍼 래스터화. keep=면 마스크. 반환 (pt, z, tri) — 격자점당 최저 z."""
    fid = np.arange(len(F)) if keep is None else np.arange(len(F))[keep]
    f = F if keep is None else F[keep]
    a, b, c = V[f[:, 0]], V[f[:, 1]], V[f[:, 2]]
    ax, ay = a[:, 0], a[:, 1]; bx, by = b[:, 0], b[:, 1]; cx, cy = c[:, 0], c[:, 1]
    ar = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
    ok = np.abs(ar) > 1e-14
    lox = np.minimum(np.minimum(ax, bx), cx); hix = np.maximum(np.maximum(ax, bx), cx)
    loy = np.minimum(np.minimum(ay, by), cy); hiy = np.maximum(np.maximum(ay, by), cy)
    i0 = np.ceil((lox - x0) / d - 1e-12).astype(np.int64)
    i1 = np.floor((hix - x0) / d + 1e-12).astype(np.int64)
    j0 = np.ceil((loy - y0) / d - 1e-12).astype(np.int64)
    j1 = np.floor((hiy - y0) / d + 1e-12).astype(np.int64)
    np.clip(i0, 0, n - 1, out=i0); np.clip(i1, 0, n - 1, out=i1)
    np.clip(j0, 0, n - 1, out=j0); np.clip(j1, 0, n - 1, out=j1)
    wx = np.maximum(i1 - i0 + 1, 0) * ok; wy = np.maximum(j1 - j0 + 1, 0) * ok
    cnt = wx * wy
    tri = np.repeat(np.arange(len(f)), cnt)
    if tri.size == 0:
        e = np.zeros(0, np.int64)
        return e, np.zeros(0), e, e, np.zeros(0)
    off = np.arange(tri.size) - np.repeat(np.cumsum(cnt) - cnt, cnt)
    wxr = wx[tri]
    ii = i0[tri] + off % wxr; jj = j0[tri] + off // wxr
    px = x0 + ii * d; py = y0 + jj * d
    v0x = bx[tri] - ax[tri]; v0y = by[tri] - ay[tri]
    v1x = cx[tri] - ax[tri]; v1y = cy[tri] - ay[tri]
    v2x = px - ax[tri]; v2y = py - ay[tri]
    den = ar[tri]
    w1 = (v2x * v1y - v2y * v1x) / den
    w2 = (v0x * v2y - v0y * v2x) / den
    ins = (w1 >= -1e-12) & (w2 >= -1e-12) & (w1 + w2 <= 1 + 1e-12)
    tri = tri[ins]; ii = ii[ins]; jj = jj[ins]
    az = a[:, 2][tri]
    z = az + w1[ins] * (b[:, 2][tri] - az) + w2[ins] * (c[:, 2][tri] - az)
    pt = jj * n + ii
    zb = np.full(n * n, np.inf)
    np.minimum.at(zb, pt, z)
    win = z <= zb[pt] + 1e-15
    pw, zw, tw = pt[win], z[win], tri[win]
    o = np.argsort(pw, kind="stable")
    pw, zw, tw = pw[o], zw[o], tw[o]
    uq = np.ones(pw.size, bool); uq[1:] = pw[1:] != pw[:-1]
    #  (가려진 것까지) **모든** 히트도 함께 — 가림의 효과를 가르는 대조군
    return pw[uq], zw[uq], fid[tw[uq]], pt, z, fid[tri]


def kernel_cpu(fp, ph, F, gam_tri, is_shell, idx, d, el_deg=-90.0,
               ranges=(10.0,), want_free=False, split_mask=None):
    """`sbr_field` 를 CPU 로 재현. 반환 dict: 위상모형별 복소 시계열 + 진단."""
    Rm = rot_to_nadir(el_deg)
    lo = np.full(3, np.inf); hi = np.full(3, -np.inf); Vs = []
    for i in range(0, N, max(1, N // 64)):
        V = np.asarray(fp.pose(ph[i]).v, float) @ Rm.T
        Vs.append(V); lo = np.minimum(lo, V.min(0)); hi = np.maximum(hi, V.max(0))
    ctr = 0.5 * (lo + hi)
    Rmax = max(float(np.linalg.norm(V - ctr, axis=1).max()) for V in Vs)
    Rout = Rmax * 1.15 + 3 * d
    n = int(np.ceil(2 * Rout / d))
    x0 = ctr[0] - (n - 1) / 2 * d; y0 = ctr[1] - (n - 1) / 2 * d
    tau_shell = 1.0 - GAM["body"] ** 2
    keys = ["plane"] + [f"{R:g}" for R in ranges]
    out = {k: np.zeros(idx.size, complex) for k in keys}
    if want_free:
        out.update({k + "_noocc": np.zeros(idx.size, complex) for k in keys})
    if split_mask is not None:
        out.update({k + "_sel": np.zeros(idx.size, complex) for k in keys})
        out.update({k + "_oth": np.zeros(idx.size, complex) for k in keys})
    nhit = []

    def _phase(k, px, py, pz):
        if k == "plane":
            return -(pz - ctr[2])
        R = float(k); zt = ctr[2] - R
        return R - np.sqrt((px - ctr[0]) ** 2 + (py - ctr[1]) ** 2 + (pz - zt) ** 2)

    for m, i in enumerate(idx):
        V = np.asarray(fp.pose(ph[int(i)]).v, float) @ Rm.T
        pt, zz, tri, pta, za, tra = raster(V, F, x0, y0, d, n)
        px = x0 + (pt % n) * d; py = y0 + (pt // n) * d
        g1 = gam_tri[tri]
        pt2, z2, tri2, _, _, _ = raster(V, F, x0, y0, d, n, keep=~is_shell)
        tau = np.zeros(n * n); tau[pt[is_shell[tri]]] = tau_shell
        px2 = x0 + (pt2 % n) * d; py2 = y0 + (pt2 // n) * d
        g2 = gam_tri[tri2] * tau[pt2]
        nhit.append((pt.size, pt2.size))
        s1 = None if split_mask is None else split_mask[tri]
        s2 = None if split_mask is None else split_mask[tri2]
        for k in keys:
            q1 = g1 * np.exp(1j * 2 * K * _phase(k, px, py, zz))
            q2 = g2 * np.exp(1j * 2 * K * _phase(k, px2, py2, z2))
            out[k][m] = (q1.sum() + q2.sum()) * d * d
            if split_mask is not None:
                out[k + "_sel"][m] = (q1[s1].sum() + q2[s2].sum()) * d * d
                out[k + "_oth"][m] = (q1[~s1].sum() + q2[~s2].sum()) * d * d
        if want_free:      # 가림 없음 = 가려진 히트까지 전부 더한다(투과 패스 없음)
            pxa = x0 + (pta % n) * d; pya = y0 + (pta // n) * d
            ga = gam_tri[tra]
            for k in keys:
                out[k + "_noocc"][m] = (ga * np.exp(1j * 2 * K * _phase(k, pxa, pya, za))).sum() * d * d
    return out, dict(n_rays=int(n * n), grid_n=int(n), spacing_m=float(d),
                     ctr=[float(x) for x in ctr], Rout=float(Rout),
                     hits_first=int(np.mean([a for a, _ in nhit])),
                     hits_penetration=int(np.mean([b for _, b in nhit])))


# ════════════════════════════════════════════════════════════════════════════
#  R5. 탐지 링크버짓 (outputs/md_range_sweep.json 규약 v2)
# ════════════════════════════════════════════════════════════════════════════
KB, T0 = 1.380649e-23, 290.0
EIRP_DBM, GRX_DBI, NF_DB, B_HZ = 12.0, 10.0, 5.0, 100e6


def snr_slow_db(sigma_m2, R, prf=PRF):
    eirp = 10 ** (EIRP_DBM / 10) * 1e-3
    g = 10 ** (GRX_DBI / 10); f = 10 ** (NF_DB / 10)
    p = eirp * g * LAM ** 2 * np.asarray(sigma_m2, float) / ((4 * np.pi) ** 3 * R ** 4)
    return 10 * np.log10(p / (KB * T0 * f * prf))


# ════════════════════════════════════════════════════════════════════════════
def main() -> None:
    t_start = time.time()
    z = np.load(SWEEP_N)
    src = json.load(open(SRC_J))
    meas90 = src["B_decomposition"]["ours/el-90"]
    fp = FastPoser(DRONES["matrice4e"])
    F = np.asarray(fp.f); G = np.asarray(fp.g)
    gam_tri = np.array([GAM[g] for g in G])
    is_shell = np.isin(G, SHELL)
    ph = rotor_phases(np.arange(N) / PRF, RPMS, fp.dirs)
    doc = {}

    print("R1 원장 거리법칙 …", flush=True)
    doc["R1_range_law_ledger"] = r1_ledger_law()

    print("R2 해석 …", flush=True)
    doc["R2_analytic"] = r2_analytic(fp, ph, F, G, meas90)

    print("R3 창 길이 …", flush=True)
    doc["R3_window_robustness"] = r3_window(z)

    # ── R4-a 패싯 정확 대리모형 (독립 재구현) ───────────────────────────────
    print("R4a 패싯 대리모형 …", flush=True)
    idxA = np.arange(0, N, 8)                    # 512 자세
    RS = [10.0, 14.08, 20.0, 30.0, 50.0, 70.0, 100.0, 200.0, 500.0, 1000.0]
    t0 = time.time()
    fx = facet_proxy(fp, ph, F, idxA, RS)
    fx_g = facet_proxy(fp, ph, F, idxA, [10.0, 20.0, 50.0, 100.0], gam_tri=gam_tri)
    tabA = {f"{R:g}m": round(acdc_db(fx[f"{R:g}"]), 2) for R in RS}
    nA, resA = fit_exponent(RS, [tabA[f"{R:g}m"] for R in RS])
    #  1차항만 vs 전체 — 1차가 상쇄되는지
    d_full = ac_series(fx["10"]); d_1st = fx["first_order"] / fx["plane"].mean()
    doc["R4a_facet_proxy_no_grid_no_occlusion"] = dict(
        note_ko=("원장 C_D 의 독립 재구현(코드를 새로 썼다). w = max(n̂·û,0)·A, 위상만 구면파. "
                 "512 자세(원장은 4096)."),
        plane_wave_nadir_ac_over_dc_db=round(acdc_db(fx["plane"]), 2),
        exact_invariance_ko=("⭐나딧 원거리장에서는 회전이 z 를 바꾸지 않고 투영면적도 바꾸지 않으므로 "
                             "∫exp(j2kz)dA_proj 가 **정확히 불변**이다 — 날개 모양·피치·개수와 무관하다. "
                             "위 −300 dB 대는 float64 반올림이다."),
        range_sweep_ac_over_dc_db=tabA,
        fit_exponent=round(nA, 3), fit_max_resid_db=round(resA, 2),
        with_material_gamma=dict(
            {f"{R:g}m": round(acdc_db(fx_g[f"{R:g}"]), 2) for R in (10.0, 20.0, 50.0, 100.0)},
            note_ko="|Γ| 를 재질표로 넣어도 거리 기울기는 같다(레벨만 달라진다)."),
        first_order_test=dict(
            first_order_ac_db=round(float(10 * np.log10(np.mean(np.abs(d_1st - d_1st.mean()) ** 2))), 2),
            full_ac_db=round(float(10 * np.log10(np.mean(np.abs(d_full) ** 2))), 2),
            corr_first_order_vs_full=round(corr(d_1st - d_1st.mean(), d_full), 4),
            why_ko=("근접장 위상을 1차(−kρ²/R)까지만 펴면 2엽 상쇄로 그 항이 거의 죽는다. "
                    "남는 것이 2차항이고 그래서 전력이 1/R⁴ 이다.")),
        seconds=round(time.time() - t0, 1))

    # ── R4-b 커널 CPU 재현기 ────────────────────────────────────────────────
    print("R4b 커널 CPU 재현기 …", flush=True)
    idxB = np.arange(0, N, 8)                    # 512 자세 (측정과 같은 시각)
    Em = np.asarray(z["ours/el-90"], complex)
    t0 = time.time()
    base, meta12 = kernel_cpu(fp, ph, F, gam_tri, is_shell, idxB, LAM / 12,
                              ranges=(10.0, 14.08, 20.0, 50.0, 100.0, 300.0, 1000.0),
                              want_free=True)
    print(f"   λ/12  {time.time()-t0:.0f}s  {meta12}", flush=True)
    ac_meas = ac_series(Em[idxB])
    rep = dict(
        meta=meta12,
        measured=dict(level_db=round(float(20 * np.log10(np.abs(Em[idxB].mean()))), 2),
                      ac_over_dc_db=round(acdc_db(Em[idxB]), 2)),
        emulated=dict(
            level_db=round(float(20 * np.log10(np.abs(base["10"].mean()))), 2),
            ac_over_dc_db=round(acdc_db(base["10"]), 2)),
        corr_ac_sph10_vs_measured=round(corr(ac_series(base["10"]), ac_meas), 4),
        corr_ac_plane_vs_measured=round(corr(ac_series(base["plane"]), ac_meas), 4),
        corr_ac_facetproxy_vs_measured=round(corr(ac_series(fx["10"]), ac_meas), 4),
        ac_amplitude_ratio_meas_over_emul=round(
            float(np.linalg.norm(ac_meas) / np.linalg.norm(ac_series(base["10"]))), 3),
        range_sweep_ac_over_dc_db={k: round(acdc_db(v), 2) for k, v in base.items()
                                   if not k.endswith("_noocc")},
        range_sweep_no_occlusion_db={k.replace("_noocc", ""): round(acdc_db(v), 2)
                                     for k, v in base.items() if k.endswith("_noocc")})
    #  재현기 안에서 «근접장 고유항» 만 뽑아 거리 지수를 다시 적합한다(가림·격자 포함 판)
    nf_only = {}
    for k in base:
        if k in ("plane",) or k.endswith("_noocc") or k.endswith("_sel") or k.endswith("_oth"):
            continue
        dd = ac_series(base[k]) - ac_series(base["plane"])
        nf_only[k] = round(float(10 * np.log10(np.mean(np.abs(dd) ** 2))), 2)
    Rk = sorted(float(k) for k in nf_only)
    n_nf, res_nf = fit_exponent(Rk, [nf_only[f"{r:g}"] for r in Rk])
    rep["nearfield_only_vs_range_db"] = nf_only
    rep["nearfield_only_fit_exponent"] = round(n_nf, 3)
    rep["nearfield_only_fit_resid_db"] = round(res_nf, 2)
    rep["pm_am"] = dict(
        measured_pm_over_am_db=round(float(20 * np.log10(
            np.imag(ac_meas).std() / np.real(ac_meas).std())), 2),
        replica_pm_over_am_db=round(float(20 * np.log10(
            np.imag(ac_series(base["10"])).std() / np.real(ac_series(base["10"])).std())), 2),
        facet_proxy_pm_over_am_db=round(float(20 * np.log10(
            np.imag(ac_series(fx["10"])).std() / np.real(ac_series(fx["10"])).std())), 2),
        note_ko=("재현기는 관측의 PM/AM 비까지 되살린다(7.25 대 7.43 dB). 반면 원장이 기전 근거로 쓴 "
                 "패싯 대리모형은 같은 AC/DC 를 내면서 PM/AM 이 **−12.1 dB**(진폭 우세)다 → "
                 "PM/AM 은 기전을 가르는 잣대가 못 된다."))
    #  순환이동 귀무분포 — «상관 0.99 가 우연인가»
    a = ac_series(base["10"]); b = ac_meas
    null = [corr(np.roll(a, s), b) for s in range(1, len(a))]
    rep["shift_null"] = dict(observed=rep["corr_ac_sph10_vs_measured"],
                             null_max=round(float(np.max(null)), 4),
                             null_p99=round(float(np.percentile(null, 99)), 4),
                             null_median=round(float(np.median(null)), 4))
    doc["R4b_cpu_kernel_replica"] = rep

    # ── R4-c 격자 사다리 — ⭐격자잡음인가 ───────────────────────────────────
    print("R4c 격자 사다리 …", flush=True)
    idxC = np.arange(0, N, 32)                   # 128 자세(같은 시각으로 비교)
    ladder = {}
    for div in (8, 12, 24, 48):
        t0 = time.time()
        o, mt = kernel_cpu(fp, ph, F, gam_tri, is_shell, idxC, LAM / div,
                           ranges=(10.0, 20.0, 50.0, 100.0), want_free=True)
        dif = ac_series(o["10"]) - ac_series(o["plane"])       # 근접장 고유항
        nfr = {R: float(10 * np.log10(np.mean(np.abs(
            ac_series(o[f"{R:g}"]) - ac_series(o["plane"])) ** 2)))
            for R in (10.0, 20.0, 50.0, 100.0)}
        n_nf_d, res_nf_d = fit_exponent(list(nfr), list(nfr.values()))
        ladder[f"lambda/{div}"] = dict(
            n_rays=mt["n_rays"], spacing_mm=round(1e3 * LAM / div, 3),
            hits_first=mt["hits_first"],
            plane_ac_over_dc_db=round(acdc_db(o["plane"]), 2),
            plane_no_occlusion_ac_db=round(acdc_db(o["plane_noocc"]), 2),
            sph10_ac_over_dc_db=round(acdc_db(o["10"]), 2),
            sph10_no_occlusion_ac_db=round(acdc_db(o["10_noocc"]), 2),
            sph100_ac_over_dc_db=round(acdc_db(o["100"]), 2),
            nearfield_only_ac_db=round(float(10 * np.log10(np.mean(np.abs(dif) ** 2))), 2),
            nearfield_only_vs_range_db={f"{R:g}m": round(v, 2) for R, v in nfr.items()},
            nearfield_only_fit_exponent=round(n_nf_d, 3),
            nearfield_only_fit_resid_db=round(res_nf_d, 2),
            seconds=round(time.time() - t0, 1))
        print(f"   λ/{div}: {ladder[f'lambda/{div}']}", flush=True)
    doc["R4c_grid_ladder"] = dict(
        rows=ladder,
        measured_ac_over_dc_db=round(acdc_db(Em[idxC]), 2),
        unit_test_reference=dict(
            source="outputs/verify_po_elev_unit.json gates G3_nadir_null_*",
            div12_ac_below_dc_db=-21.75, div12_ac_power_pct=0.66338,
            div48_ac_below_dc_db=-43.02, div48_ac_power_pct=0.00499,
            target="one_sphere, 2 cm sphere orbiting r=0.137 m about the LINE OF SIGHT",
            why_not_comparable_ko=(
                "단위시험의 궤도 구는 **회전축이 시선 위**라 왕복거리가 아예 안 변한다 → 해석 도플러가 "
                "정확히 0 이고 그 칸의 AC 는 전부 격자 잡음이다. 기체는 로터 허브가 시선에서 L=0.219 m "
                "밀려 있어 사정이 다르다. 게다가 표적이 다르면(2 cm 구 vs 30,662 면 기체) 격자 잡음의 "
                "상대 크기도 다르다 — 두 숫자를 바로 비교하면 안 된다."),
            normalization_note_ko=(
                "지시문은 이 값을 «AC 전력의 0.663 %» 라고 옮겼는데 원장 키는 ac_power_pct=0.66338 "
                "**총전력 대비 %** 이고 같은 칸의 ac_below_dc_db 가 −21.75 dB 다. 즉 −38.31 dB 와 "
                "**같은 정규화**이므로 비교 자체는 성립한다 — 다만 표적이 달라서 결론이 안 따라온다.")))

    # ── R4-d 앙각 널의 폭 (가림·격자 포함) ─────────────────────────────────
    print("R4d 앙각 널 폭 …", flush=True)
    els = {}
    for el in (-90.0, -89.0, -88.0, -85.0, -80.0, -75.0):
        o, mt = kernel_cpu(fp, ph, F, gam_tri, is_shell, idxC, LAM / 12, el_deg=el,
                           ranges=(10.0,))
        els[f"{el:+.1f}"] = dict(off_nadir_deg=round(90 + el, 1),
                                 plane_ac_over_dc_db=round(acdc_db(o["plane"]), 2),
                                 sph10_ac_over_dc_db=round(acdc_db(o["10"]), 2))
        print(f"   el {el}: {els[f'{el:+.1f}']}", flush=True)
    #  같은 잣대로 잰 측정 스윕
    meas_els = {k.split("/")[1]: round(acdc_db(np.asarray(z[k], complex)[idxC]), 2)
                for k in z.files if k.startswith("ours/")}
    doc["R4d_null_width"] = dict(cpu_replica=els, measured_sweep_same_metric=meas_els,
                                 farfield_facet_proxy=src["C_D_geometry"]["offnadir_farfield"])

    # ── R4f 빗살 귀속 — «빗살이 격자 잡음인가» 를 선(線) 단위로 ────────────
    print("R4f 빗살 귀속 …", flush=True)
    dec = int(idxB[1] - idxB[0]); prf_d = PRF / dec; nB = idxB.size
    frd = np.fft.fftfreq(nB, 1 / prf_d)
    combm = np.zeros(nB, bool)
    for kk in range(1, 60):
        combm |= np.abs(np.abs(frd) - kk * FFL) <= 12.0
    wh = np.hanning(nB)

    def comb_row(x, tag):
        dd = ac_series(x)
        P = np.abs(np.fft.fft(dd * wh)) ** 2
        sh = float(10 * np.log10(P[combm].sum() / P.sum()))
        return dict(series=tag, ac_over_dc_db=round(acdc_db(x), 2),
                    on_comb_share_db=round(sh, 2),
                    on_comb_ac_over_dc_db=round(acdc_db(x) + sh, 2))
    doc["R4f_comb_attribution"] = dict(
        note_ko=("«126.67 Hz 빗살이 보인다» 가 물리의 증거인지 본다. 격자 잡음만 있는 계열"
                 "(원거리장·가림 없음)의 빗살 몫을 백색 기준선과 비교한다."),
        effective_prf_hz=round(prf_d, 1), n_samples=int(nB),
        white_noise_baseline_db=round(float(10 * np.log10(combm.mean())), 2),
        rows=[comb_row(base["plane_noocc"], "replica far field, no occlusion = pure grid noise"),
              comb_row(base["plane"], "replica far field (grid noise + occlusion)"),
              comb_row(base["10"], "replica spherical 10 m (all three)"),
              comb_row(Em[idxB], "measured SBR kernel")],
        grid_noise_share_of_comb_power=round(float(
            10 ** (comb_row(base["plane_noocc"], "")["on_comb_ac_over_dc_db"] / 10)
            / 10 ** (comb_row(base["10"], "")["on_comb_ac_over_dc_db"] / 10)), 3),
        verdict_ko=(
            "백색 기준선은 −7.55 dB 다(빗살 마스크가 빈의 17.6 % 를 덮는다). 격자 잡음만 있는 계열은 "
            "−5.87 dB 로 기준선보다 **1.7 dB** 만 몰려 있고, 실측은 −1.93 dB 로 **5.6 dB** 몰려 있다. "
            "⇒ 격자 잡음은 빗살을 거의 안 만들고 넓게 퍼진다. 빗살 **위**의 전력만 세면 격자 잡음 몫이 "
            "약 43 % 로 떨어진다(전체 AC 에서는 64 %). 빗살 자체는 주로 물리다."))

    # ── R4e 귀속 — AC 는 어디서 오나, 10 dB 차이는 무엇인가 ────────────────
    print("R4e 귀속 …", flush=True)
    isprop = (G == "prop")
    o5, _ = kernel_cpu(fp, ph, F, gam_tri, is_shell, idxB, LAM / 12,
                       ranges=(10.0,), split_mask=isprop)
    Ep, Eo = o5["10_sel"], o5["10_oth"]
    dc_p, dc_o = Ep.mean(), Eo.mean()
    theta = float(np.degrees(np.angle(dc_p / (dc_p + dc_o))))
    #  Γ_prop 을 c 배 하면 E(c) = c·Ep + Eo  → 관측 AC/DC 를 맞추는 c 를 찾는다
    cs = np.geomspace(0.5, 20, 400)
    acs = np.array([acdc_db(c * Ep + Eo) for c in cs])
    tgt = acdc_db(Em[idxB])
    c_hit = float(cs[int(np.argmin(np.abs(acs - tgt)))])
    lv_hit = float(20 * np.log10(np.abs((c_hit * Ep + Eo).mean())))
    r_best = corr(ac_series(base["10"]), ac_meas)
    doc["R4e_attribution"] = dict(
        prop_share_of_dc_power_db=round(float(20 * np.log10(np.abs(dc_p / (dc_p + dc_o)))), 2),
        rest_share_of_dc_power_db=round(float(20 * np.log10(np.abs(dc_o / (dc_p + dc_o)))), 2),
        ac_of_props_only_db=round(acdc_db(Ep), 2),
        ac_of_everything_else_db=round(acdc_db(Eo), 2),
        phasor_angle_prop_vs_total_deg=round(theta, 1),
        two_phasor_pm_over_am_db=round(float(20 * np.log10(abs(np.tan(np.radians(theta))))), 2),
        observed_pm_over_am_db=meas90["pm_over_am_db"],
        pm_am_note_ko=("로터 페이저를 **하나**로 뭉뚱그린 이 2-페이저 어림은 13.7 dB 를 주고 관측은 "
                       "7.4 dB 다 — 어림이 거칠다. 그러나 **면 단위로 다 더하는 재현기는 7.25 dB 로 맞춘다** "
                       "(R4b.pm_am). 요지는 그대로다: PM/AM 비는 페이저 사잇각의 문제이지 "
                       "«도플러가 남았나» 의 잣대가 아니다."),
        gamma_prop_scale_matching_measured_ac=round(c_hit, 2),
        gamma_prop_implied=round(c_hit * GAM["prop"], 4),
        level_db_at_that_scale=round(lv_hit, 2),
        measured_level_db=round(float(20 * np.log10(np.abs(Em[idxB].mean()))), 2),
        unexplained_ac_power_fraction=round(float(1 - r_best ** 2), 5),
        note_ko=("① AC 는 **전부 로터**에서 온다 — 로터를 뺀 나머지의 AC 는 −319 dB(=0)다. "
                 "② 재현기가 측정보다 AC 가 10.2 dB 작은 것은 «다른 잡음» 이 아니라 **곱셈 상수**다"
                 "(파형이 99.6 % 같다). |Γ_prop| 을 3.24 배 하면 정확히 맞는다. "
                 "③ ⚠그러나 그때 함의되는 |Γ_prop| = 0.285 는 **벌크 플라스틱 0.244 보다 크다** — "
                 "박판 블레이드에서 그럴 수 없다. 그러니 «Γ 값 하나가 틀렸다» 는 설명은 **미해결**이다. "
                 "가장 유력한 후보는 커널의 각도의존 Γ(SIONNA2_ANGLE_GAMMA=1, 비스듬한 면에서 |Γ| 가 "
                 "커진다)인데, materials.py 가 sionna.rt 를 끌어와 GPU 를 잡으므로 이 라운드에서 "
                 "확인하지 못했다. **GPU 가 필요한 남은 일**로 남긴다."))

    # ── R5 탐지 ────────────────────────────────────────────────────────────
    print("R5 탐지 …", flush=True)
    lam2 = 4 * np.pi / LAM ** 2
    sig_tot = lam2 * float(np.mean(np.abs(Em) ** 2))
    sig_dc = lam2 * float(np.abs(Em.mean()) ** 2)
    sig_ac10 = lam2 * float(np.mean(np.abs(Em - Em.mean()) ** 2))
    E15 = np.asarray(z["ours/el-15"], complex)
    sig15_dc = lam2 * float(np.abs(E15.mean()) ** 2)
    sig15_ac = lam2 * float(np.mean(np.abs(E15 - E15.mean()) ** 2))
    #  나딧 AC 를 세 갈래로 가른다 — R4c 사다리(λ/12 판, 수렴값 참조)
    l12, l48 = ladder["lambda/12"], ladder["lambda/48"]
    p_tot = 10 ** (l12["sph10_ac_over_dc_db"] / 10)
    p_nf = 10 ** (l12["nearfield_only_ac_db"] / 10)                 # 근접장 고유 ∝1/R⁴
    p_occ = 10 ** (l48["plane_ac_over_dc_db"] / 10)                 # 가림(거리무관) 상한
    p_grid = max(p_tot - p_nf - p_occ, 0.0)                          # 격자 표본화 잡음
    f_nf, f_occ, f_grid = p_nf / p_tot, p_occ / p_tot, p_grid / p_tot
    n_asis = l12["nearfield_only_fit_exponent"]      # 생산 격자가 실제로 내는 기울기
    rows = {}
    for R in (10.0, 20.0, 40.0, 100.0, 200.0):
        phys = sig_ac10 * (f_nf * (10.0 / R) ** 4 + f_occ)
        asis = sig_ac10 * (f_nf * (10.0 / R) ** n_asis + f_occ + f_grid)
        rows[f"{R:g}m"] = dict(
            nadir_snr_total_db=round(float(snr_slow_db(sig_tot, R)), 2),
            nadir_snr_blade_physical_db=round(float(snr_slow_db(phys, R)), 2),
            nadir_snr_blade_as_measured_db=round(float(snr_slow_db(asis, R)), 2),
            el15_snr_total_db=round(float(snr_slow_db(sig15_dc + sig15_ac, R)), 2),
            el15_snr_blade_db=round(float(snr_slow_db(sig15_ac, R)), 2))
    doc["R5_detection"] = dict(
        convention=dict(source="outputs/md_range_sweep.json meta.snr / link_budget",
                        eirp_dbm=EIRP_DBM, rx_gain_dbi=GRX_DBI, nf_db=NF_DB, b_hz=B_HZ,
                        prf_hz=PRF, g_mf_db=round(float(10 * np.log10(B_HZ / PRF)), 2),
                        rung="snr_slow_db(③) / snr_slow_ac_db(③′) · monostatic-equivalent R⁴",
                        caveat_ko="σ 절대값은 NOT_VALIDATED(das_fleet_validation) — 상대비교로만 읽어라."),
        sigma_dbsm=dict(nadir_total=round(float(10 * np.log10(sig_tot)), 2),
                        nadir_dc=round(float(10 * np.log10(sig_dc)), 2),
                        nadir_ac_at_10m=round(float(10 * np.log10(sig_ac10)), 2),
                        el15_dc=round(float(10 * np.log10(sig15_dc)), 2),
                        el15_ac=round(float(10 * np.log10(sig15_ac)), 2)),
        nadir_ac_split=dict(
            nearfield_fraction=round(float(f_nf), 4),
            occlusion_fraction=round(float(f_occ), 4),
            grid_sampling_noise_fraction=round(float(f_grid), 4),
            basis=("R4c: λ/12 총합 − 근접장고유(coherent diff) − 가림바닥(λ/48 plane, 상한). "
                   "측정 AC 는 재현기 AC 의 3.2배 스칼라이므로(ρ=0.998) 같은 비율로 나뉜다고 본다."),
            exponent_used=dict(physical=4.0, as_measured=n_asis,
                               why_ko=("물리는 1/r⁴ 이지만 **생산 격자 λ/12 에서 실제로 재면** "
                                       f"근접장 고유항이 r^−{n_asis:.2f} 로만 떨어진다 — 격자가 두 날개를 "
                                       "다르게 표본화해서 1차항 상쇄가 깨지기 때문이다. 격자를 조이면 "
                                       "지수가 2.24→2.59→3.35→3.74 로 4 에 수렴한다.")),
            caveat_ko=("① 격자 잡음 몫은 **수치 인공물**이다 — 실물 표적에는 없다. "
                       "② 세 갈래가 직교하지 않으므로 이 나눗셈은 어림이다. "
                       "③ 가림 몫은 λ/48 판 값이라 아직 격자 잡음이 섞여 있다 → **상한**이고, "
                       "따라서 격자 잡음 몫 64 % 는 **하한**이다.")),
        rows=rows)

    # ── 판정 ───────────────────────────────────────────────────────────────
    w70 = doc["R3_window_robustness"]["ours/el-90"]["per_window"]["70"]
    doc["VERDICTS"] = {
        "claim1_fixed_band_beat_is_leakage": dict(
            verdict="살아남음 (SURVIVES) — 단, 반쪽만 참이다",
            evidence=dict(true_over_leakage_at_deck_window_db=w70["true_over_leakage_db"],
                          at_192_samples_db=doc["R3_window_robustness"]["ours/el-90"]["per_window"]["192"]["true_over_leakage_db"],
                          at_512_samples_db=doc["R3_window_robustness"]["ours/el-90"]["per_window"]["512"]["true_over_leakage_db"],
                          fullrecord_band_share_db=doc["R3_window_robustness"]["ours/el-90"]["fullrecord_band_share_db"],
                          lowpass_control_db=doc["R3_window_robustness"]["ours/el-90"]["fullrecord_band_share_lowpassed_db"]),
            corrected_statement_ko=(
                "덱이 쓴 70-표본 창에서는 고정대역 값이 **전부 누설**이다(0.01 dB). 그러나 창을 "
                "192 표본 이상으로 늘리면 진짜 대역 에너지가 누설 위로 올라온다(+1.8 → +19.3 dB). "
                "전체 기록 FFT 로는 대역 몫이 −51.6 dB 이고 저역통과 대조군은 −134.5 dB 다 — "
                "**대역 안에 진짜 에너지가 있다.** 즉 «인용된 숫자는 인공물» 은 맞고 "
                "«대역이 비어 있다» 는 틀렸다.")),
        "claim2_comb_is_real": dict(
            verdict="살아남음 (SURVIVES) — 빗살은 물리다. 단 전체 AC 의 64 % 는 격자 잡음이고 그것은 빗살 밖에 있다",
            evidence=dict(split=doc["R5_detection"]["nadir_ac_split"],
                          comb=doc["R4f_comb_attribution"]),
            corrected_statement_ko=(
                "126.67 Hz 빗살은 실재한다. ⭐이번 라운드가 정면으로 답한 것: 생산 격자 λ/12 에서 "
                "나딧 AC **전력의 약 64 % 는 광선 격자 표본화 잡음**이다(격자를 λ/48 로 조이면 "
                "원거리장 잔여가 −49 → −62 dB 로 무너진다). 그러나 그 잡음은 **빗살을 거의 안 만든다** — "
                "격자 잡음만 있는 계열의 on-comb 몫은 백색 기준선보다 1.7 dB 위인데 실측은 5.6 dB 위다. "
                "빗살 위 전력만 세면 격자 잡음 몫이 64 % → 43 % 로 내려간다. "
                "즉 **관측된 빗살이 격자 잡음에 묻혀 있지 않다** — "
                "다만 «AC/DC = −38.3 dB» 라는 **숫자**는 절반 이상이 인공물이라 그대로 인용하면 안 된다.")),
        "claim3_phase_beats_amplitude": dict(
            verdict="반증됨 (REFUTED) — 결론은 우연히 맞고 근거는 틀렸다",
            evidence=dict(measured=doc["R4b_cpu_kernel_replica"]["pm_am"],
                          per_element_doppler_hz=doc["R2_analytic"]["per_element"]["max_doppler_hz"]),
            corrected_statement_ko=(
                "2엽 상쇄가 남기는 인자 2cos(a·cosψ) 는 **실수**다 — 로터 페이저의 크기만 흔든다. "
                "그것이 AM 으로 보이나 PM 으로 보이나는 로터 페이저와 총 페이저의 사잇각이 정한다. "
                "증거: 같은 AC/DC(−38.6 dB)를 내는 패싯 대리모형은 PM/AM 이 **−12.1 dB**(진폭 우세)이고 "
                "커널 재현기는 **+7.25 dB**(위상 우세)다. 같은 기전, 반대 부호. "
                "«작은 도플러가 남는다» 는 결론 자체는 참이지만(허브 오프셋이 만드는 ±27.9 Hz), "
                "pm_over_am 은 그 근거가 아니다.")),
        "claim4_mechanism_is_nearfield_curvature": dict(
            verdict="부분 반증 (PARTLY REFUTED) — 기전은 실재하고 1/r⁴ 도 맞으나, 인용된 수치 일치는 우연이다",
            evidence=dict(
                ledger_fit_exponent=doc["R1_range_law_ledger"]["global_fit_exponent"],
                independent_facet_fit_exponent=doc["R4a_facet_proxy_no_grid_no_occlusion"]["fit_exponent"],
                replica_nearfield_only_fit_exponent=doc["R4b_cpu_kernel_replica"]["nearfield_only_fit_exponent"],
                exponent_vs_grid={k: v["nearfield_only_fit_exponent"]
                                  for k, v in doc["R4c_grid_ladder"]["rows"].items()},
                first_order_term_db=doc["R4a_facet_proxy_no_grid_no_occlusion"]["first_order_test"]["first_order_ac_db"],
                proxy_10m_db=doc["R4a_facet_proxy_no_grid_no_occlusion"]["range_sweep_ac_over_dc_db"]["10m"],
                proxy_10m_with_material_gamma_db=doc["R4a_facet_proxy_no_grid_no_occlusion"]["with_material_gamma"]["10m"],
                replica_nearfield_only_10m_db=doc["R4c_grid_ladder"]["rows"]["lambda/12"]["nearfield_only_ac_db"],
                measured_db=doc["R4c_grid_ladder"]["measured_ac_over_dc_db"]),
            corrected_statement_ko=(
                "① 1/r⁴ 는 **맞다** — 원장 표를 적합하면 지수 4.04, 내가 새로 짠 대리모형도 4.04, "
                "가림·격자까지 넣은 재현기의 근접장 고유항도 같은 기울기다. 이유도 확인했다: "
                "2엽 로터에서 1차항(∝1/R)이 **정확히 상쇄**되어(−319 dB) 2차항만 남는다 → 전력 ∝1/R⁴. "
                "⚠단 그것은 **격자가 없을 때**다. 생산 격자 λ/12 에서 실제로 재면 근접장 고유항이 "
                "r^−2.59 로만 떨어진다 — 격자가 두 날개를 다르게 표본화해 1차 상쇄를 깨기 때문이고, "
                "격자를 조이면 지수가 2.24→2.59→3.35→3.74 로 4 에 수렴한다. "
                "② 그러나 «구면파 10 m = −38.55 dB 가 실측 −38.31 dB 와 맞는다» 는 **우연이다**. "
                "그 대리모형은 |Γ|=1(프롭 과대평가)과 가림 없음의 두 오차가 서로를 가려 준 값이다. "
                "재질 |Γ| 를 넣으면 −45.9 dB 이고, 커널을 그대로 재현하면 근접장 고유항은 −54.3 dB 다. "
                "③ 실측 −38.3 dB 를 만드는 것은 [근접장 31 % + 격자잡음 64 % + 가림 5 %] 에 "
                "|Γ_prop| 눈금(×3.2) 이다.")),
        "claim5_blind_cone_is_very_narrow": dict(
            verdict="반증됨 (REFUTED)",
            evidence=dict(replica=doc["R4d_null_width"]["cpu_replica"],
                          old_proxy=doc["R4d_null_width"]["farfield_facet_proxy"]),
            corrected_statement_ko=(
                "«0.5° 만 벗어나도 −55.9 dB, 1° 에서 −44.1 dB» 는 가림도 격자도 없는 원거리장 "
                "모형의 성질이다. 그 모형은 나딧에서 **정확히 0**(−305 dB)에서 출발하므로 어떤 "
                "각도든 «급격한 회복» 으로 보인다. 커널을 그대로 재현하면 나딧이 −49.2 dB 에서 "
                "출발해 1° −47.0, 2° −44.1, 5° −32.5, 10° −23.7 dB 로 **완만하게** 찬다. "
                "즉 널의 **깊이**가 −305 dB 가 아니라 −49 dB(실측 눈금으로는 −38 dB)이고, "
                "«아주 좁은 원뿔» 이 아니라 «10° 규모로 회복되는 얕은 웅덩이» 다.")),
    }

    doc["_meta"] = dict(
        generator="benchmark/refute_nadir_mechanism_final.py",
        question_ko="verify_nadir_flash.json 의 주장 (1)~(5) 를 끝까지 반증한다",
        gpu_ko="⭐GPU 를 쓰지 않았다. mitsuba·sionna 를 import 조차 하지 않는다. 광선은 CPU z-버퍼.",
        inputs=dict(series="outputs/elevation_sweep_md.npz (phase_sign_v2=1)",
                    source_ledger="outputs/verify_nadir_flash.json",
                    unit_test="outputs/verify_po_elev_unit.json",
                    link_budget="outputs/md_range_sweep.json",
                    kinematics="outputs/report07_three_engines.json _meta"),
        gamma_table=GAM, gamma_source="outputs/material_sources.json (근거는 GAM 주석)",
        replica_limits_ko=[
            "각도의존 Γ(SIONNA2_ANGLE_GAMMA=1)를 못 넣었다 — materials.py 가 sionna.rt 를 끌어와 GPU 를 잡는다.",
            "|Γ| 표를 손으로 옮겨 적었다(원장 material_sources.json 기준). camera 0.85·pcb 0.9 는 추정.",
            "float64 로 계산했다(커널은 mitsuba float32). PTD 모서리항은 커널 기본값대로 끔.",
            "나딧(그리고 회전시킨 앙각)만 다룬다 — 방위 스윕·바이스태틱은 안 했다.",
            "⭐그럼에도 파형 상관 0.998·레벨 0.83 dB·PM/AM 0.18 dB 안으로 맞는다. AC 크기만 10.2 dB 낮다."],
        seconds=round(time.time() - t_start, 1))
    json.dump(doc, open(OUT_J, "w"), ensure_ascii=False, indent=1)
    print(f"✅ {OUT_J}  ({doc['_meta']['seconds']}s)")
    np.savez_compressed(f"{ROOT}/outputs/refute_nadir_mechanism_final.npz",
                        idxB=idxB, emul_sph10=base["10"], emul_plane=base["plane"],
                        meas=Em[idxB], facet_sph10=fx["10"])
    figure(doc, base, fx, Em, idxB, RS)


# ════════════════════════════════════════════════════════════════════════════
def figure(doc, base, fx, Em, idxB, RS) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(2, 3, figsize=(19.2, 10.4))
    fig.suptitle("Finishing the refutation: what really makes the residual blade line at nadir "
                 "(Matrice 4E, 3.5 GHz, el = -90 deg)", fontsize=15, fontweight="bold")

    # (a) 거리 법칙
    a = ax[0, 0]
    L = doc["R1_range_law_ledger"]["table_db"]
    Rl = sorted(float(k[:-1]) for k in L)
    a.semilogx(Rl, [L[f"{int(r)}m"] for r in Rl], "o", ms=11, mfc="none", mew=2,
               color="tab:purple", label="earlier ledger (verify_nadir_flash)")
    P = doc["R4a_facet_proxy_no_grid_no_occlusion"]["range_sweep_ac_over_dc_db"]
    Rp = sorted(float(k[:-1]) for k in P)
    a.semilogx(Rp, [P[f"{r:g}m"] for r in Rp], "s-", ms=6, color="tab:red", lw=1.6,
               label="this round, independent re-implementation")
    nfit = doc["R4a_facet_proxy_no_grid_no_occlusion"]["fit_exponent"]
    ref = P["10m"] - 40 * np.log10(np.array(Rp) / 10.0)
    a.semilogx(Rp, ref, "k:", lw=1.6, label="exact 1/r^4")
    a.annotate(f"fitted exponent n = {nfit:.2f}\n(power ~ 1/r^n),  residual < 0.4 dB\n"
               "-> the 1/r^4 claim SURVIVES",
               xy=(50, P["50m"]), xytext=(12, -105), fontsize=10, color="tab:red",
               arrowprops=dict(arrowstyle="->", color="tab:red", lw=1.3))
    a.set_xlabel("range [m]"); a.set_ylabel("modulated power / steady power [dB]")
    a.set_title("(a) The range law re-measured from scratch:\n"
                "2x range costs 12.0 dB, 2.5x costs 15.9 dB", fontsize=11.5, loc="left")
    a.legend(fontsize=9, loc="upper right"); a.grid(alpha=.25, which="both")

    # (b) 격자 사다리
    b = ax[0, 1]
    rows = doc["R4c_grid_ladder"]["rows"]
    divs = [8, 12, 24, 48]
    xs = [1e3 * LAM / d for d in divs]
    for key, col, lab, mk in (
            ("sph10_ac_over_dc_db", "tab:red", "total, spherical 10 m (occlusion on)", "o"),
            ("plane_ac_over_dc_db", "tab:orange", "far field (no near-field term left)", "s"),
            ("plane_no_occlusion_ac_db", "tab:brown", "far field, occlusion off = pure grid noise", "^"),
            ("nearfield_only_ac_db", "tab:blue", "near-field term alone (coherent difference)", "D")):
        b.plot(xs, [rows[f"lambda/{d}"][key] for d in divs], mk + "-", color=col, lw=1.7, label=lab)
    mv = doc["R4c_grid_ladder"]["measured_ac_over_dc_db"]
    b.axhline(mv, color="k", ls="--", lw=1.5)
    b.annotate("measured SBR kernel, lambda/12 production grid\n"
               "(10.2 dB above the replica: one |Gamma_prop| scale, see R4e)",
               xy=(4.2, mv), xytext=(9.2, mv + 4.5), fontsize=8.5,
               arrowprops=dict(arrowstyle="->", lw=1))
    b.set_ylim(-72, -30)
    for d in divs:
        b.annotate(f"$\\lambda$/{d}", xy=(1e3 * LAM / d, -31.4), fontsize=9.5, ha="center",
                   color="0.35")
    b.invert_xaxis()
    b.set_xlabel("ray grid spacing [mm]   (finer to the right)")
    b.set_ylabel("modulated power / steady power [dB]")
    b.set_title("(b) Refine the grid and watch which curves die:\n"
                "the far-field residual is grid noise, the near-field term is not",
                fontsize=11.5, loc="left")
    b.legend(fontsize=8.5, loc="lower left"); b.grid(alpha=.25)

    # (c) 재현기 대 측정
    c = ax[0, 2]
    r4b = doc["R4b_cpu_kernel_replica"]
    t = idxB / PRF * 1e3
    dm = np.real(ac_series(Em[idxB])); de = np.real(ac_series(base["10"]))
    g = r4b["ac_amplitude_ratio_meas_over_emul"]
    c.plot(t, 1e3 * dm, color="k", lw=1.4, label="measured SBR kernel (GPU)")
    c.plot(t, 1e3 * g * de, color="tab:red", lw=1.2, ls="--",
           label=f"CPU replica x {g:.2f}  (no GPU, no Mitsuba)")
    c.set_xlim(0, 12)
    c.set_xlabel("slow time [ms]"); c.set_ylabel("in-phase deviation from carrier [x1e-3]")
    c.set_title(f"(c) An independent CPU re-implementation reproduces the\n"
                f"residual waveform: rho = {r4b['corr_ac_sph10_vs_measured']:.3f} "
                f"(shift-null max {r4b['shift_null']['null_max']:.2f})", fontsize=11.5, loc="left")
    c.legend(fontsize=9); c.grid(alpha=.25)

    # (d) 창 길이
    d_ = ax[1, 0]
    for key, col, lab in (("ours/el-90", "tab:red", "el = -90 deg (nadir)"),
                          ("ours/el-15", "tab:blue", "el = -15 deg (deck case)")):
        w = doc["R3_window_robustness"][key]["per_window"]
        ns = sorted(int(k) for k in w)
        d_.plot(ns, [w[str(n)]["true_over_leakage_db"] for n in ns], "o-", color=col,
                lw=1.8, label=lab)
    d_.axvline(70, color="k", ls=":", lw=1.5)
    d_.annotate("deck window\n70 samples", xy=(70, 30), xytext=(86, 31), fontsize=9)
    d_.axhline(0, color="0.5", lw=1)
    d_.set_xlabel("STFT window length [samples]")
    d_.set_xscale("log"); d_.set_xticks([35, 70, 128, 256, 512])
    d_.set_xticklabels(["35", "70", "128", "256", "512"])
    d_.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    d_.tick_params(axis="x", which="minor", length=2)
    d_.set_ylabel("true in-band energy above window leakage [dB]")
    d_.set_title("(d) Was the fixed-band metric leakage? At the deck's window, yes\n"
                 "(0.0 dB). Real in-band energy only appears past ~192 samples",
                 fontsize=11.5, loc="left")
    d_.legend(fontsize=9); d_.grid(alpha=.25, which="both")

    # (e) 널의 폭
    e = ax[1, 1]
    cr = doc["R4d_null_width"]["cpu_replica"]
    ks = sorted(cr, key=lambda k: cr[k]["off_nadir_deg"])
    xs = [cr[k]["off_nadir_deg"] for k in ks]
    e.plot(xs, [cr[k]["sph10_ac_over_dc_db"] for k in ks], "o-", color="tab:red", lw=2,
           label="CPU replica (grid + occlusion + near field)")
    ff = doc["R4d_null_width"]["farfield_facet_proxy"]
    fx_ = sorted((v["off_nadir_deg"], v["ac_over_dc_db"]) for v in ff.values())
    e.plot([p[0] for p in fx_], [max(p[1], -70) for p in fx_], "s--", color="tab:green", lw=1.5,
           label="earlier proxy (far field, no occlusion, no grid)")
    ms = doc["R4d_null_width"]["measured_sweep_same_metric"]
    e.plot([90 + float(k[2:]) for k in ms], [ms[k] for k in ms], "*", color="k", ms=16,
           ls="none", label="measured sweep (only -90 and -75 deg fall in this window)")
    e.set_xlim(-0.5, 16); e.set_ylim(-72, 2)
    e.set_xlabel("angle away from nadir [deg]")
    e.set_ylabel("modulated power / steady power [dB]")
    e.set_title("(e) The blind cone is NOT a knife edge: with occlusion and a real\n"
                "ray grid the null is only ~13 dB deep and fills in over ~10 deg",
                fontsize=11.5, loc="left")
    e.legend(fontsize=8.5, loc="lower right"); e.grid(alpha=.25)

    # (f) 탐지
    f_ = ax[1, 2]
    rr = doc["R5_detection"]["rows"]
    Rd = sorted(float(k[:-1]) for k in rr)
    def g_(k): return [rr[f"{r:g}m"][k] for r in Rd]
    f_.semilogx(Rd, g_("el15_snr_blade_db"), "o-", color="tab:blue", lw=2,
                label="blade line, el = -15 deg")
    f_.semilogx(Rd, g_("nadir_snr_blade_as_measured_db"), "s--", color="tab:orange", lw=1.6,
                label="blade line at nadir, as the ledger stands")
    f_.semilogx(Rd, g_("nadir_snr_blade_physical_db"), "s-", color="tab:red", lw=2,
                label="blade line at nadir, numerical part removed")
    f_.axhline(0, color="k", lw=1.2)
    f_.text(11, 1.5, "noise floor", fontsize=9)
    f_.set_xlabel("range [m]"); f_.set_ylabel("blade-line SNR, slow-time sample [dB]")
    f_.set_title("(f) What it means for detection: at nadir the blade line is under\n"
                 "the noise past ~12 m, and it is 9-13 dB worse than at -15 deg",
                 fontsize=11.5, loc="left")
    f_.legend(fontsize=8.5); f_.grid(alpha=.25, which="both")

    fig.tight_layout(rect=(0, 0, 1, 0.955))
    fig.savefig(OUT_P, dpi=140)
    print(f"✅ {OUT_P}")


if __name__ == "__main__":
    main()
