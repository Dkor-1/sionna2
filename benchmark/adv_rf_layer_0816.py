# -*- coding: utf-8 -*-
"""
adv_rf_layer_0816.py — 메쉬 감사(docs/MESH_AUDIT_0816.md)의 **RF 층** 적대검증
==============================================================================

무엇을 묻나
-----------
감사는 프롭 날 형상 오차를 «면적비 → 20·log10 → dB» 로 번역해 −2.97 / −3.10 / −3.55 /
−5.08 dB 같은 수를 문서에 박았고, 같은 문서의 §4-2 에서 스스로 «과대 번역» 이라 반증하면서
그 이유를 «비틀린 날의 정반사 띠(트위스트율)가 크기를 정한다» 로 설명했다.
이 파일은 그 **번역과 설명이 물리적으로 옳은지**를 3.5 GHz 에서 직접 잰다.

규약(전부 선언)
---------------
* **CPU 전용.** GPU 0 회. mitsuba/sionna import 0 회.
* **기존 코드 무변경.** 이 파일은 새로 추가한 읽기 전용 측정기다. 커널은 `src/rcs_po.py` 를
  그대로 import 해서 쓴다(모노스태틱). 바이스태틱만 표준 스칼라 PO 를 여기서 구현하고,
  β=0 에서 출하 커널과 상대오차 0 임을 매 실행마다 회귀로 확인한다.
* **주파수 3.5 GHz** (감사의 §3 렌즈는 4.0 GHz 였다 — 우리 대역으로 다시 잰다).
* **재질 |Γ| = 1 (PEC)** 이 기본이다. 이 파일이 재는 것은 **형상 → σ 의 지수(exponent)** 이고
  재질은 전 형상 공통 곱이라 지수를 안 바꾼다(K3c 에서 실제로 확인한다).

산출: outputs/mesh_adv_rf_layer_0816.json

실행:
  cd /workspace/sionna && PYTHONPATH=src:benchmark \
    /workspace/.venvs/py312/bin/python benchmark/adv_rf_layer_0816.py
"""
from __future__ import annotations

import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import drone_cad as dc                                       # noqa: E402
from drones import DRONES                                    # noqa: E402
from rcs_po import mesh_to_points, po_field_dir, C0          # noqa: E402

FC = 3.5e9
LAM = C0 / FC
K = 2 * np.pi / LAM
DIV = 24                       # 점 간격 λ/24 (수렴은 K0 에서 확인)
SPEC = DRONES["matrice4e"]
R_M = SPEC.prop_dia_mm / 1000.0 / 2.0          # 0.137 m
PITCH_M = float(SPEC.prop_pitch_in) * 0.0254   # 0.14478 m
AZ = np.arange(0.0, 360.0, 0.25)


class Shim:
    """trimesh → rcs_po.mesh_to_points 가 기대하는 최소 인터페이스(.v/.f/.g)."""

    def __init__(self, tm, g="prop"):
        self.v = np.asarray(tm.vertices, float)
        self.f = np.asarray(tm.faces, np.int64)
        self.g = [g] * len(self.f)


def blade(chord_scale=1.0, law="legacy", pitch_law=None, n_sec=22,
          chord_rr=None, chord_frac=None, R=R_M, div=DIV, tip_refine=None):
    """날 1장을 짓고 PO 점구름을 돌려준다. **출하 `_blade` 를 그대로 부른다.**"""
    cmax = 0.25 * chord_scale
    if law != "legacy":
        cmax = dc.CHORD_MAX_OVER_R_AREA_NEUTRAL * chord_scale if law == "dji_mini2_areaneutral" else cmax
    tm = dc._blade(R, root_frac=0.070, chord_max=cmax, pitch_m=PITCH_M, n_sec=n_sec,
                   law=("dji_mini2" if law.startswith("dji_mini2") else law),
                   pitch_law=pitch_law, tip_refine=tip_refine,
                   chord_rr=chord_rr, chord_frac=chord_frac)
    P, N, dA = mesh_to_points(Shim(tm), LAM / div)
    return tm, P, N, dA


def look(az_deg, el_deg):
    az = np.radians(np.atleast_1d(az_deg))
    el = np.radians(el_deg)
    return np.stack([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az),
                     np.full_like(az, np.sin(el))], axis=-1)


def field_mono(P, N, dA, U, chunk=400):
    """모노스태틱 PO **복소장** E(û) — rcs_po.po_field_dir 과 같은 식(벡터화)."""
    out = np.empty(len(U), complex)
    for s in range(0, len(U), chunk):
        u = U[s:s + chunk]
        NU = N @ u.T
        PU = P @ u.T
        out[s:s + chunk] = (np.where(NU > 0, NU, 0.0) * dA[:, None]
                            * np.exp(1j * 2 * K * PU)).sum(axis=0)
    return out


def field_bi(P, N, dA, Ui, Us, chunk=400):
    """바이스태틱 스칼라 PO. Ui=Us 면 모노와 **정확히 같은 식**."""
    out = np.empty(len(Ui), complex)
    for s in range(0, len(Ui), chunk):
        a, b = Ui[s:s + chunk], Us[s:s + chunk]
        NI, NS = N @ a.T, N @ b.T
        PH = P @ (a + b).T
        out[s:s + chunk] = (np.where((NI > 0) & (NS > 0), NI, 0.0) * dA[:, None]
                            * np.exp(1j * K * PH)).sum(axis=0)
    return out


def sig(E):
    return 4 * np.pi / LAM ** 2 * np.abs(E) ** 2


def db(x):
    return 10 * np.log10(np.maximum(np.asarray(x, float), 1e-30))


# =========================================================================== #
OUT = {}
t00 = time.time()

# --------------------------------------------------------------------------- #
# K0 — 커널이 실제로 쓰는 양 + 수렴
# --------------------------------------------------------------------------- #
print("[K0] 커널 항등식 · 수렴", flush=True)
k0 = {}
#  (a) 평판 정면입사 = 완전 코히런트 → σ ∝ A²  (지수 2)
from geom import Mesh                                        # noqa: E402
plate_n = []
for a in (0.20, 0.24, 0.28, 0.32):
    m = Mesh("plate"); h = a / 2
    i = [m.add_vertex(*p) for p in [(-h, -h, 0), (h, -h, 0), (h, h, 0), (-h, h, 0)]]
    m.add_quad(*i)
    P, N, dA = mesh_to_points(m, LAM / 12)
    s = sig(field_mono(P, N, dA, look([0.0], 90.0)))[0]
    plate_n.append((a * a, s, 4 * np.pi * (a * a) ** 2 / LAM ** 2))
A = np.log([p[0] for p in plate_n]); S = np.log([p[1] for p in plate_n])
k0["plate_exponent_n"] = round(float(np.polyfit(A, S, 1)[0]), 4)
k0["plate_vs_closed_form_db"] = [round(float(10 * math.log10(p[1] / p[2])), 4) for p in plate_n]
#  (b) 구 = 완전 비코히런트(한 점만 정반사) → σ = πr² ∝ A^1 (지수 1)
from geom import uv_sphere                                   # noqa: E402
sph = []
for r in (0.20, 0.25, 0.30, 0.35):
    P, N, dA = mesh_to_points(uv_sphere(r, seg=90, rings=46), LAM / 8)
    s = sig(field_mono(P, N, dA, look([0.0], 0.0)))[0]
    sph.append((4 * np.pi * r * r, s, np.pi * r * r))
A = np.log([p[0] for p in sph]); S = np.log([p[1] for p in sph])
k0["sphere_exponent_n"] = round(float(np.polyfit(A, S, 1)[0]), 4)
k0["sphere_vs_pir2_db"] = [round(float(10 * math.log10(p[1] / p[2])), 3) for p in sph]
#  (c) 점 간격 수렴(날)
conv = {}
for d in (12, 24, 48):
    _, P, N, dA = blade(div=d)
    s = sig(field_mono(P, N, dA, look(AZ, -30.0)))
    s2 = sig(field_mono(P, N, dA, look(AZ, -72.0)))
    conv[f"lam_over_{d}"] = dict(npts=int(len(dA)),
                                 mean_dbsm_el30=round(float(db(s.mean())), 3),
                                 mean_dbsm_el72=round(float(db(s2.mean())), 3))
k0["blade_spacing_convergence"] = conv
k0["kernel_reads"] = ("rcs_po.rcs_from_points/po_field_dir: "
                      "E = Σ_{n̂·û>0} |Γ|·(n̂·û)·ΔA·exp(j2k P·û), σ=(4π/λ²)|E|². "
                      "쓰는 양은 ①면적요소 ΔA ②법선·시선 내적(비스듬함) ③위치의 위상. "
                      "곡률·두께는 **직접 안 들어간다** — 위상 항을 통해서만 들어온다.")
OUT["K0_kernel_identity"] = k0
print("   ", k0["plate_exponent_n"], k0["sphere_exponent_n"], flush=True)

# --------------------------------------------------------------------------- #
# K1 — 정반사 고각은 어디인가 (감사의 «el −30 은 면적축이 죽는다» 의 진짜 원인)
# --------------------------------------------------------------------------- #
print("[K1] 정반사 고각", flush=True)
_, P, N, dA = blade()
el_grid = np.arange(0.0, -90.5, -2.0)
peak, mean = [], []
for el in el_grid:
    s = sig(field_mono(P, N, dA, look(AZ, float(el))))
    peak.append(float(s.max())); mean.append(float(s.mean()))
peak = np.array(peak); mean = np.array(mean)
el_flash = float(el_grid[int(np.argmax(peak))])
#  이론: 날 국소 피치 θ(r)=atan(k(r)·P/(2πr)) — 면 정반사는 |el| = 90° − θ 에서
rr = np.linspace(0.10, 1.0, 200)
kloc = np.interp(rr, dc.PITCH_RR, dc.PITCH_K)
th = np.degrees(np.arctan(kloc * PITCH_M / (2 * np.pi * rr * R_M)))
#  면적가중(시위)으로 대표 피치
c_rr = np.interp(rr, dc.CHORD_RR, dc.CHORD_FRAC)
th_bar = float((th * c_rr).sum() / c_rr.sum())
OUT["K1_flash_elevation"] = dict(
    el_of_peak_deg=el_flash,
    peak_dbsm_by_el={f"{e:.0f}": round(float(db(p)), 2) for e, p in zip(el_grid, peak)},
    mean_dbsm_by_el={f"{e:.0f}": round(float(db(m)), 2) for e, m in zip(el_grid, mean)},
    local_pitch_deg={f"{r:.2f}R": round(float(np.interp(r, rr, th)), 2)
                     for r in (0.2, 0.3, 0.5, 0.7, 0.9, 1.0)},
    chord_weighted_pitch_deg=round(th_bar, 2),
    predicted_flash_el_deg=round(-(90.0 - th_bar), 1),
    note_ko=("면 정반사(플래시)는 |el| = 90° − θ_local 에서 일어난다. 날 피치가 8~20° 이므로 "
             "플래시는 |el| 70~82° 다. ⇒ 헤드라인 밴드 el −30 은 정반사에서 **40~50° 떨어진** "
             "비정반사 영역이다."))
print("    flash el =", el_flash, " 예측", round(-(90.0 - th_bar), 1), flush=True)

# --------------------------------------------------------------------------- #
# K2 — 면적 → dB 지수 n (핵심). σ ∝ A^n 이면 dB = 10·n·log10(A비)
# --------------------------------------------------------------------------- #
print("[K2] 면적 지수", flush=True)
scales = [0.7, 0.85, 1.0, 1.2, 1.4]
els = [0.0, -15.0, -30.0, -45.0, -60.0, -72.0, -90.0]
areas, cache = {}, {}
for sc in scales:
    _, P, N, dA = blade(chord_scale=sc)
    areas[sc] = float(dA.sum())
    for el in els:
        s = sig(field_mono(P, N, dA, look(AZ, el)))
        cache[(sc, el)] = (float(s.max()), float(s.mean()))
la = np.log([areas[s] / areas[1.0] for s in scales])
k2 = {"area_ratio": {str(s): round(areas[s] / areas[1.0], 4) for s in scales}, "by_el": {}}
for el in els:
    row = {}
    for qi, qn in ((0, "peak"), (1, "az_mean")):
        v = np.array([cache[(s, el)][qi] for s in scales])
        n = float(np.polyfit(la, np.log(v), 1)[0])
        row[qn] = dict(exponent_n=round(n, 3),
                       db_rel_to_1x={str(s): round(float(10 * math.log10(cache[(s, el)][qi]
                                                                        / cache[(1.0, el)][qi])), 2)
                                     for s in scales},
                       db_if_20log10_rule=round(float(20 * math.log10(areas[1.4] / areas[1.0])), 2),
                       db_measured_at_1p4=round(float(10 * math.log10(cache[(1.4, el)][qi]
                                                                     / cache[(1.0, el)][qi])), 2))
    k2["by_el"][f"{el:.0f}"] = row
#  ── K2b: 지수는 **날의 전기적 크기**에 달렸다 (기종별 R/λ)
k2b = {}
for key, Rk, Pk in (("mini2", 0.05955, 2.6 * 0.0254), ("mini5pro", 0.0762, 3.2 * 0.0254),
                    ("matrice4e", 0.137, 5.7 * 0.0254), ("m350rtk", 0.2667, 10.0 * 0.0254)):
    vals = {el: [] for el in (-30.0, -60.0, -72.0)}
    ars = []
    for sc in scales:
        tm = dc._blade(Rk, root_frac=0.070, chord_max=0.25 * sc, pitch_m=Pk, n_sec=22, law="legacy")
        Pv, Nv, dAv = mesh_to_points(Shim(tm), LAM / DIV)
        ars.append(float(dAv.sum()))
        for el in vals:
            vals[el].append(float(sig(field_mono(Pv, Nv, dAv, look(AZ, el))).mean()))
    lg = np.log(np.array(ars) / ars[2])
    k2b[key] = dict(R_over_lambda=round(Rk / LAM, 3),
                    exponent_n={f"el{e:.0f}": round(float(np.polyfit(lg, np.log(np.array(v)), 1)[0]), 3)
                                for e, v in vals.items()})
k2["K2b_exponent_vs_electrical_size"] = k2b
#  ── K2c: 재질(각도의존 |Γ|)이 지수를 바꾸나 — ITU 벌크 프레넬 모양을 직접 얹어 본다
EPS0_ = 8.8541878128e-12
eps_c = complex(2.7, -0.02 / (2 * np.pi * FC * EPS0_))


def gshape(cosi):
    ci = np.clip(cosi, 0.0, 1.0)
    ap = np.sqrt(eps_c - (1 - ci ** 2))
    rte = (ci - ap) / (ci + ap)
    rtm = (eps_c * ci - ap) / (eps_c * ci + ap)
    s = np.sqrt(0.5 * (np.abs(rte) ** 2 + np.abs(rtm) ** 2))
    ap0 = np.sqrt(eps_c)
    s0 = np.sqrt(0.5 * (abs((1 - ap0) / (1 + ap0)) ** 2 + abs((eps_c - ap0) / (eps_c + ap0)) ** 2))
    return s / s0


k2c = {}
for el in (-30.0, -72.0):
    vv = []
    for sc in scales:
        tm = dc._blade(R_M, root_frac=0.070, chord_max=0.25 * sc, pitch_m=PITCH_M, n_sec=22)
        Pv, Nv, dAv = mesh_to_points(Shim(tm), LAM / DIV)
        U = look(AZ, el)
        NU = Nv @ U.T
        PU = Pv @ U.T
        E = (np.where(NU > 0, NU, 0.0) * gshape(NU) * dAv[:, None]
             * np.exp(1j * 2 * K * PU)).sum(axis=0)
        vv.append(float(sig(E).mean()))
    k2c[f"el{el:.0f}"] = dict(
        exponent_n_with_angle_gamma=round(float(np.polyfit(la, np.log(np.array(vv)), 1)[0]), 3),
        exponent_n_PEC=k2["by_el"][f"{el:.0f}"]["az_mean"]["exponent_n"])
k2["K2c_angle_dependent_gamma"] = k2c
k2["verdict_ko"] = ("지수 n 은 고각에 따라 0.1 → 2.0 으로 변한다. n=2 여야만 «면적비 20log10» 이 "
                    "맞는데, 그 조건은 **정반사 근처(el −60~−90)** 에서만 성립한다. "
                    "el −30 에서는 n≈0.9 라 20log10 은 **정확히 2배 과대**이고, el 0 에서는 "
                    "n≈0.1~0.6 이라 면적이 사실상 안 먹는다.")
OUT["K2_area_exponent"] = k2

# --------------------------------------------------------------------------- #
# K3 — 왜 그런가: 코히런스 비율(면적 중 실제로 «쓰이는» 몫)
# --------------------------------------------------------------------------- #
print("[K3] 코히런스", flush=True)
_, P, N, dA = blade()
k3 = {}
for el in (0.0, -30.0, -60.0, -72.0, -90.0):
    U = look(AZ, el)
    E = field_mono(P, N, dA, U)
    ia = int(np.argmax(np.abs(E)))
    u = U[ia]
    NU = N @ u
    a = np.where(NU > 0, NU, 0.0) * dA           # 위상을 뺀 «비간섭 합» (전부 양수)
    A_proj = float(a.sum())                      # 투영면적
    A_coh = float(abs(E[ia]))                    # 코히런트 실효 투영면적
    k3[f"el{el:.0f}"] = dict(
        az_of_peak=float(AZ[ia]),
        A_proj_mm2=round(A_proj * 1e6, 1),
        A_coh_mm2=round(A_coh * 1e6, 1),
        coherence_ratio=round(A_coh / A_proj, 4),
        sigma_peak_dbsm=round(float(db(sig(E[ia:ia + 1])[0])), 2))
#  트위스트가 정한다는 «정반사 띠» 의 이론 폭 — Δr = λ/(2·u⊥·θ'·c)
th_p = np.gradient(np.radians(th), rr * R_M)     # dθ/dr [rad/m]
c_abs = c_rr * 0.25 * R_M
band = LAM / (2.0 * np.abs(th_p) * np.maximum(c_abs, 1e-6))
k3["twist_specular_band_theory"] = dict(
    formula="Δr_half = λ / (2·u⊥·|dθ/dr|·c)  (시위 방향 sinc 의 첫 영점)",
    dtheta_dr_rad_per_m={f"{r:.1f}R": round(float(np.interp(r, rr, th_p)), 2)
                         for r in (0.3, 0.5, 0.7, 0.9)},
    band_half_width_mm={f"{r:.1f}R": round(float(np.interp(r, rr, band)) * 1e3, 1)
                        for r in (0.3, 0.5, 0.7, 0.9)},
    blade_span_mm=round(float(R_M * (1 - 0.070)) * 1e3, 1),
    verdict_ko=("3.5 GHz·matrice4e 급에서 트위스트가 정하는 정반사 띠의 반폭은 **날 전체보다 "
                "몇 배 넓다** ⇒ 트위스트는 날을 자르지 않는다. 감사가 든 «트위스트율이 정반사 "
                "띠 크기를 정한다» 는 이 크기 급에서 성립하지 않는다."))
#  ⭐진짜 포화 기제 — **시위 방향 위상 기울기**. 정반사에서 벗어나면 시위 적분이
#    c·sinc(α c/2) 가 되어 α c/2 ≳ π 부터 «시위를 넓혀도 안 는다».
_, P, N, dA = blade()
chord_diag = {}
for el in (0.0, -15.0, -30.0, -45.0, -60.0, -72.0, -90.0):
    U = look(AZ, el)
    E = field_mono(P, N, dA, U)
    u = U[int(np.argmax(np.abs(E)))]
    #  대표 반경 0.5R 에서의 시위 방향 단위벡터(피치각 θ 로 기운다)
    th05 = math.radians(float(np.interp(0.5, rr, th)))
    chat = np.array([0.0, math.cos(th05), math.sin(th05)])
    c05 = float(np.interp(0.5, dc.CHORD_RR, dc.CHORD_FRAC)) * 0.25 * R_M
    alpha = 2 * K * abs(float(np.dot(chat, u)))
    chord_diag[f"el{el:.0f}"] = dict(
        u_dot_chord=round(float(abs(np.dot(chat, u))), 4),
        alpha_c_over_2_rad=round(float(alpha * c05 / 2), 3),
        sinc_factor=round(float(abs(np.sinc(alpha * c05 / 2 / np.pi))), 4),
        measured_exponent_n=k2["by_el"][f"{el:.0f}"]["az_mean"]["exponent_n"])
k3["chordwise_phase_gradient"] = dict(
    table=chord_diag,
    verdict_ko=("정반사 고각(el≈−72)에서 û·ĉ→0 ⇒ 시위 전체가 동위상 ⇒ 지수 n→2(면적² 법칙 성립). "
                "고각이 정반사에서 멀어질수록 û·ĉ 가 커져 시위 적분이 sinc 로 눌리고 n 이 1 아래로 "
                "떨어진다. ⇒ **포화를 만드는 것은 트위스트가 아니라 «정반사에서 얼마나 벗어났나»** 다."))
OUT["K3_coherence"] = k3

# --------------------------------------------------------------------------- #
# K4 — 감사가 실제로 쓴 두 비교(법칙 교체·팁)의 3.5 GHz 재측정
# --------------------------------------------------------------------------- #
print("[K4] 법칙 교체 · 팁", flush=True)
k4 = {}
_, Pl, Nl, dAl = blade(law="legacy")
_, Pd, Nd, dAd = blade(law="dji_mini2")                       # c_max 0.25 그대로 → 면적 +19.5 %
_, Pn, Nn, dAn = blade(law="dji_mini2_areaneutral")           # 면적중립 c_max
tip = list(dc.CHORD_FRAC); tip[-1] = 0.20
_, Pt, Nt, dAt = blade(chord_frac=tuple(tip), chord_rr=dc.CHORD_RR)
sets = {"legacy": (Pl, Nl, dAl), "dji_planform_same_cmax": (Pd, Nd, dAd),
        "dji_planform_area_neutral": (Pn, Nn, dAn), "legacy_blunt_tip_0p20": (Pt, Nt, dAt)}
k4["surface_area_mm2"] = {kk: round(float(v[2].sum()) * 1e6, 1) for kk, v in sets.items()}
k4["area_ratio_vs_legacy"] = {kk: round(float(v[2].sum() / dAl.sum()), 4) for kk, v in sets.items()}
k4["delta_db_by_el"] = {}
for el in els:
    base = sig(field_mono(Pl, Nl, dAl, look(AZ, el)))
    row = {}
    for kk, (Pv, Nv, dAv) in sets.items():
        s = sig(field_mono(Pv, Nv, dAv, look(AZ, el)))
        row[kk] = dict(d_mean_db=round(float(db(s.mean()) - db(base.mean())), 2),
                       d_peak_db=round(float(db(s.max()) - db(base.max())), 2))
    k4["delta_db_by_el"][f"{el:.0f}"] = row
k4["audit_20log10_claims_db"] = {"blade_area_-29pct": round(20 * math.log10(0.71), 2),
                                 "tip_band_0.700": round(20 * math.log10(0.700), 2),
                                 "outer_band": -3.55}
#  ── K4b: **출하 코드가 실제로 내놓는 판** (기종별 c_max + 기종별 곡선)
k4b = {}
for key in ("matrice4e", "mavic4pro", "mini5pro", "mini2"):
    sp = DRONES[key]
    Rk = sp.prop_dia_mm / 2000.0
    Pk = float(sp.prop_pitch_in) * 0.0254
    per = {}
    for lw in ("legacy", "dji_mini2", "per_airframe"):
        cm, _ = dc.resolve_chord_max_over_r(sp, lw)
        crr, cfr, _ = dc.resolve_chord_profile(sp, lw)
        tm = dc._blade(Rk, root_frac=0.070, chord_max=cm, pitch_m=Pk, n_sec=22,
                       law=lw, chord_rr=crr, chord_frac=cfr)
        Pv, Nv, dAv = mesh_to_points(Shim(tm), LAM / DIV)
        row = {"area_mm2": round(float(dAv.sum()) * 1e6, 1), "c_max_over_R": round(cm, 4)}
        for el in (-30.0, -60.0, -72.0):
            row[f"sigma_mean_dbsm_el{el:.0f}"] = round(
                float(db(sig(field_mono(Pv, Nv, dAv, look(AZ, el))).mean())), 2)
        per[lw] = row
    base = per["legacy"]
    for lw in ("dji_mini2", "per_airframe"):
        per[lw]["d_area_db_20log10"] = round(
            float(20 * math.log10(per[lw]["area_mm2"] / base["area_mm2"])), 2)
        per[lw]["d_sigma_db"] = {f"el{e:.0f}": round(per[lw][f"sigma_mean_dbsm_el{e:.0f}"]
                                                    - base[f"sigma_mean_dbsm_el{e:.0f}"], 2)
                                 for e in (-30.0, -60.0, -72.0)}
        per[lw]["R_over_lambda"] = round(Rk / LAM, 3)
    k4b[key] = per
k4["K4b_shipped_laws"] = k4b
OUT["K4_law_swap"] = k4

# --------------------------------------------------------------------------- #
# K5 — 바이스태틱: Kell 등가(유효 파장 λ/cos(β/2))가 맞나, 지수는 어떻게 변하나
# --------------------------------------------------------------------------- #
print("[K5] 바이스태틱 등가", flush=True)
k5 = {"regression_mono_rel_err": None, "kell_check": {}, "exponent_by_beta": {}}
_, P, N, dA = blade()
u0 = look([0.0], -30.0)
k5["regression_mono_rel_err"] = float(abs(po_field_dir(P, N, dA, FC, u0[0])
                                          - field_bi(P, N, dA, u0, u0)[0])
                                      / abs(po_field_dir(P, N, dA, FC, u0[0])))
for beta in (0.0, 60.0, 81.0, 120.0):
    Ui = look(AZ - beta / 2, -30.0)
    Us = look(AZ + beta / 2, -30.0)
    sb = sig(field_bi(P, N, dA, Ui, Us))
    #  Kell 등가: 이등분선 모노스태틱을 유효 파수 k·cos(β/2) 로 = 주파수 f·cos(β/2)
    fe = FC * math.cos(math.radians(beta / 2))
    ke = 2 * np.pi * fe / C0
    U = look(AZ, -30.0)
    NU = N @ U.T; PU = P @ U.T
    Em = (np.where(NU > 0, NU, 0.0) * dA[:, None] * np.exp(1j * 2 * ke * PU)).sum(axis=0)
    sm = 4 * np.pi / LAM ** 2 * np.abs(Em) ** 2          # 같은 λ 정규화로 비교
    k5["kell_check"][f"beta{beta:.0f}"] = dict(
        bistatic_mean_dbsm=round(float(db(sb.mean())), 2),
        kell_equivalent_mean_dbsm=round(float(db(sm.mean())), 2),
        diff_db=round(float(db(sb.mean()) - db(sm.mean())), 2),
        f_eff_ghz=round(fe / 1e9, 3))
    #  지수
    vals = []
    for sc in scales:
        _, Pv, Nv, dAv = blade(chord_scale=sc)
        vals.append(float(sig(field_bi(Pv, Nv, dAv, Ui, Us)).mean()))
    k5["exponent_by_beta"][f"beta{beta:.0f}"] = dict(
        exponent_n=round(float(np.polyfit(la, np.log(np.array(vals)), 1)[0]), 3),
        db_at_1p4=round(float(10 * math.log10(vals[-1] / vals[2])), 2))
k5["note_ko"] = ("바이스태틱 각 β 는 이등분선 방향에서 **유효 파장을 λ/cos(β/2) 로 늘린다**"
                 "(Kell 등가). 표적이 전기적으로 작아지므로 «평판처럼» 굴어 면적 민감도가 "
                 "커진다 — 감사가 관측한 «바이스태틱에서 형상 민감도 증가» 의 물리 원인이다.")
OUT["K5_bistatic"] = k5

# --------------------------------------------------------------------------- #
# K6 — 마이크로도플러 포락선: «시위 분포를 주파수축에 옮긴 것» 인가
# --------------------------------------------------------------------------- #
print("[K6] 마이크로도플러 포락선", flush=True)
NPH = 2048
k6 = {}
for el in (-30.0, -60.0):
    ph = np.arange(NPH) * 360.0 / NPH
    _, P, N, dA = blade()
    E = field_mono(P, N, dA, look(ph, el))       # 회전 = 시선 방위 스윕(동치)
    X = np.fft.fft(E - E.mean()) / NPH
    n_ax = np.fft.fftfreq(NPH, d=1.0 / NPH)
    pos = (n_ax >= 1) & (n_ax <= 60)
    n_pos = n_ax[pos].astype(int)
    S = np.abs(X[pos]) ** 2
    beta_tip = 2 * K * R_M * math.cos(math.radians(el))
    #  ── 모델 A(감사): 포락선 = 시위분포를 f 축에 옮김.  r = R·n/β_tip, S ∝ c(r)²
    rn = np.clip(n_pos / beta_tip, 0, 1)
    cA = np.interp(rn, dc.CHORD_RR, dc.CHORD_FRAC)
    A_model = cA ** 2
    #  ── 모델 B(아벨/베셀): S(n) ∝ ∫_{r:β(r)>n} w(r)²/√(β(r)²−n²) dr
    rg = np.linspace(0.07, 1.0, 400)
    wg = np.interp(rg, dc.CHORD_RR, dc.CHORD_FRAC)
    bg = 2 * K * rg * R_M * math.cos(math.radians(el))
    B_model = np.array([np.trapezoid(np.where(bg > n, wg ** 2 / np.sqrt(np.maximum(bg ** 2 - n ** 2, 1e-9)), 0.0), rg)
                        for n in n_pos])

    def fit_db(model, meas):
        m = (meas > meas.max() * 1e-6) & (model > 0)
        off = np.mean(10 * np.log10(meas[m]) - 10 * np.log10(model[m]))
        err = 10 * np.log10(meas[m]) - (10 * np.log10(model[m]) + off)
        return float(np.sqrt(np.mean(err ** 2))), float(np.corrcoef(10 * np.log10(meas[m]),
                                                                   10 * np.log10(model[m]))[0, 1])
    rmsA, corA = fit_db(A_model, S)
    rmsB, corB = fit_db(B_model, S)
    k6[f"el{el:.0f}"] = dict(
        beta_tip_harmonics=round(float(beta_tip), 2),
        n_harmonics_to_ftip=int(round(beta_tip)),
        model_A_chord_transposed=dict(rms_db=round(rmsA, 2), corr_db=round(corA, 3)),
        model_B_abel_bessel=dict(rms_db=round(rmsB, 2), corr_db=round(corB, 3)),
        measured_db_by_n={str(int(n)): round(float(10 * math.log10(max(v, 1e-30))), 2)
                          for n, v in zip(n_pos[:40], S[:40])},
        frac_power_beyond_ftip=round(float(S[n_pos > beta_tip].sum() / S.sum()), 4))
#  팁 밴드가 f_tip 세기를 정하는가 — 팁만 0.10→0.20 으로 바꿔 재본다
tipdelta = {}
for el in (-30.0, -60.0):
    ph = np.arange(NPH) * 360.0 / NPH
    out2 = {}
    variants = [("legacy_tip0.10", dc.CHORD_RR, dc.CHORD_FRAC),
                ("blunt_tip0.20", dc.CHORD_RR, tuple(tip)),
                ("dji_planform", dc.CHORD_RR_DJI_MINI2, dc.CHORD_FRAC_DJI_MINI2)]
    for nm, crr, cf in variants:
        _, P, N, dA = blade(chord_frac=cf, chord_rr=crr)
        E = field_mono(P, N, dA, look(ph, el))
        X = np.abs(np.fft.fft(E - E.mean()) / NPH) ** 2
        n_ax = np.fft.fftfreq(NPH, d=1.0 / NPH)
        bt = 2 * K * R_M * math.cos(math.radians(el))
        m_tip = (n_ax >= 0.85 * bt) & (n_ax <= 1.05 * bt)
        m_all = (n_ax >= 1) & (n_ax <= 1.05 * bt)
        out2[nm] = dict(tipband_power=float(X[m_tip].sum()), total_power=float(X[m_all].sum()))
    a = out2["legacy_tip0.10"]
    row = {}
    for nm in ("blunt_tip0.20", "dji_planform"):
        row[nm] = dict(
            d_tipband_db=round(float(10 * math.log10(out2[nm]["tipband_power"]
                                                     / a["tipband_power"])), 2),
            d_total_db=round(float(10 * math.log10(out2[nm]["total_power"]
                                                   / a["total_power"])), 2))
    row["tip_band_0.90_0.96R_in_harmonics"] = round(float(0.06 * 2 * K * R_M
                                                          * math.cos(math.radians(el))), 2)
    tipdelta[f"el{el:.0f}"] = row
k6["tip_blunting_effect"] = tipdelta
#  ── K6c: «f ∝ r 이라 반경이 주파수에 일대일로 옮겨간다» 를 직접 반증
#     날의 바깥 10 % 만 남긴 것 / 안쪽 절반만 남긴 것의 스펙트럼 지지집합을 본다.
k6c = {}
_, P, N, dA = blade()
rad = np.hypot(P[:, 0], P[:, 1]) / R_M
ph = np.arange(NPH) * 360.0 / NPH
for el in (-30.0, -60.0):
    bt = 2 * K * R_M * math.cos(math.radians(el))
    sub = {}
    for nm, m in (("full", rad > 0), ("outer_r>0.9R", rad > 0.9), ("inner_r<0.5R", rad < 0.5)):
        E = field_mono(P[m], N[m], dA[m], look(ph, el))
        X = np.abs(np.fft.fft(E - E.mean()) / NPH) ** 2
        n_ax = np.fft.fftfreq(NPH, d=1.0 / NPH)
        tot = X[(n_ax >= 1) & (n_ax <= 3 * bt)].sum()
        sub[nm] = dict(
            frac_power_below_half_ftip=round(float(X[(n_ax >= 1) & (n_ax < 0.5 * bt)].sum() / tot), 4),
            frac_power_in_top_decade=round(float(X[(n_ax >= 0.9 * bt) & (n_ax <= bt)].sum() / tot), 4),
            frac_power_beyond_ftip=round(float(X[(n_ax > bt) & (n_ax <= 3 * bt)].sum() / tot), 4))
    k6c[f"el{el:.0f}"] = sub
k6["K6c_radius_to_frequency_support"] = dict(
    table=k6c,
    verdict_ko=("반경 r 의 산란체는 자기 «자기 주파수» f_r 에만 나타나지 않는다 — f_r **아래 전 "
                "대역**에 퍼진다(베셀 J_n(β) 의 n<β 영역). 그래서 팁만 남겨도 전력의 대부분이 "
                "f_tip 훨씬 아래에 있다. ⇒ «시위 분포를 주파수축에 옮긴 것» 은 일대일 사상이 "
                "아니라 **아벨형 적분변환**이다."))
k6["audit_claim_ko"] = ("감사 I8: «회전 날의 스펙트럼 포락선은 대략 시위분포를 주파수축에 옮긴 "
                        "것이라 f_tip 근방 세기를 팁 밴드가 정한다», 팁 밴드 면적비 0.700 → "
                        "−3.10 dB(두께까지 −5.08 dB).")
OUT["K6_microdoppler_envelope"] = k6

# --------------------------------------------------------------------------- #
# K7 — 두께 축이 정말 «13~17 dB» 인가 (잣대가 공정한가)
# --------------------------------------------------------------------------- #
print("[K7] 두께 축", flush=True)


EPS0 = 8.8541878128e-12
#  src/materials.py :: MATS["prop_plastic"] = eps_r 2.7, sigma 0.02 S/m
EPS_R, SIGMA = 2.7, 0.02


def slab_R(t_mm, theta, pol="TE"):
    """ITU-R P.2040 식 43/44 — 단층 슬래브 |R|. theta[rad] 배열 가능.
    (benchmark/slab_thickness_check.py 와 같은 식·같은 재질 상수의 독립 구현)"""
    e2 = complex(EPS_R, -SIGMA / (2 * np.pi * FC * EPS0))
    c1 = np.cos(theta); s1 = np.sin(theta)
    c2 = np.sqrt(1 - (s1 ** 2) / e2)
    if pol == "TE":
        r = (c1 - np.sqrt(e2) * c2) / (c1 + np.sqrt(e2) * c2)
    else:
        r = (np.sqrt(e2) * c1 - c2) / (np.sqrt(e2) * c1 + c2)
    q = 2 * np.pi * (t_mm * 1e-3) / LAM * np.sqrt(e2 - s1 ** 2)
    ex = np.exp(-2j * q)
    return np.abs(r * (1 - ex) / (1 - r ** 2 * ex))


#  각도평균 규약 = 저장소 것 그대로: 반구 균등 조명 ∫|R|² sinθcosθ dθ / ∫ sinθcosθ dθ
thf = np.radians(np.linspace(0.0, 89.9, 900))
wgt = np.sin(thf) * np.cos(thf)
tt = [0.478, 0.6, 0.833, 0.876, 0.9, 0.99, 1.40, 1.43, 1.456, 2.88, 100.0]
tab, tab45, tabn = {}, {}, {}
for t in tt:
    R2 = 0.5 * (slab_R(t, thf, "TE") ** 2 + slab_R(t, thf, "TM") ** 2)
    tab[f"{t}mm"] = round(float(10 * math.log10((R2 * wgt).sum() / wgt.sum())), 3)
    a45 = np.array([math.radians(45.0)])
    tab45[f"{t}mm"] = round(float(10 * math.log10(
        0.5 * (slab_R(t, a45, "TE")[0] ** 2 + slab_R(t, a45, "TM")[0] ** 2))), 3)
    tabn[f"{t}mm"] = round(float(20 * math.log10(slab_R(t, np.array([0.0]))[0])), 3)
lin = {f"{t}mm": round(float(20 * math.log10(t / 0.9)), 3) for t in tt}
OUT["K7_thickness_lever"] = dict(
    slab_sigma_db_angle_avg=tab, slab_sigma_db_at_45deg=tab45, slab_sigma_db_normal=tabn,
    pure_20log10_t_ratio_vs_0p9mm=lin,
    thin_slab_law_ko=("얇은 슬래브 극한에서 |R| ∝ t 다. 수직입사 실측(위 slab_sigma_db_normal)과 "
                      "순수 20log10(t비)가 0.5~1.5 mm 에서 0.1 dB 안에 붙는다 ⇒ **두께 축에서는 "
                      "20log10 이 옳다**. 형상 축과 결정적으로 다른 점이다(K2)."),
    levers_db={
        "감사가 쓴 «13~17 dB»": "슬래브 손잡이를 100 mm → 0.9 mm 로 끝에서 끝까지 돌린 폭. "
                                "100 mm 두께의 프로펠러 날은 존재하지 않으므로 이것은 «오차» 가 "
                                "아니라 «손잡이의 사거리» 다.",
        "정본1.43 → mini5pro실측0.833 (각도평균)": round(float(tab["1.43mm"] - tab["0.833mm"]), 2),
        "정본1.43 → mini5pro실측0.833 (45°)": round(float(tab45["1.43mm"] - tab45["0.833mm"]), 2),
        "정본1.43 → mini5pro실측0.833 (수직)": round(float(tabn["1.43mm"] - tabn["0.833mm"]), 2),
        "형상 축(감사 자신의 커널 폭)": 2.5,
        "형상 축(이 라운드 재측정: 출하 법칙교체 최대 |Δσ|)": round(float(max(
            abs(v["d_sigma_db"][e]) for a in k4b.values() for lw, v in a.items()
            if lw != "legacy" for e in v["d_sigma_db"])), 2),
        "형상 축(이 라운드 재측정: 시위 ±40 % 통제)": round(float(max(
            abs(k2["by_el"][f"{e:.0f}"]["az_mean"]["db_measured_at_1p4"]) for e in els)), 2)},
    coupling_warning_ko=("두께와 형상은 **직교축이 아니다.** |Γ| 는 입사각의 함수이고(플라스틱 "
                         "75° 에서 +6.7 dB), 피치 법칙을 바꾸면 날이 보는 입사각 분포가 통째로 "
                         "옮겨간다. «두께 축 13~17 dB / 형상 축 1~2 dB» 는 두 축이 독립이라는 "
                         "전제 위에서만 뜻이 있다."))

# --------------------------------------------------------------------------- #
# K8 — 감사의 §3 렌즈는 4.0 GHz 였다. 3.5 GHz 로 옮겨도 같은 결론인가
# --------------------------------------------------------------------------- #
print("[K8] 주파수 이식성", flush=True)
k8 = {}
for fghz in (3.5, 4.0):
    lam_f = C0 / (fghz * 1e9)
    k_f = 2 * np.pi / lam_f
    row = {}
    for el in (-30.0, -60.0, -72.0):
        vv = []
        for sc in scales:
            tm = dc._blade(R_M, root_frac=0.070, chord_max=0.25 * sc, pitch_m=PITCH_M, n_sec=22)
            Pv, Nv, dAv = mesh_to_points(Shim(tm), lam_f / DIV)
            U = look(AZ, el)
            NU = Nv @ U.T; PU = Pv @ U.T
            E = (np.where(NU > 0, NU, 0.0) * dAv[:, None] * np.exp(1j * 2 * k_f * PU)).sum(axis=0)
            vv.append(float((4 * np.pi / lam_f ** 2 * np.abs(E) ** 2).mean()))
        row[f"el{el:.0f}"] = dict(
            exponent_n=round(float(np.polyfit(la, np.log(np.array(vv)), 1)[0]), 3),
            db_at_1p4=round(float(10 * math.log10(vv[-1] / vv[2])), 2))
    k8[f"{fghz}GHz"] = dict(R_over_lambda=round(R_M / lam_f, 3), **row)
k8["note_ko"] = ("감사의 형상 σ 측정(§3·C5)은 4.0 GHz 였다. 지수는 R/λ 의 함수이므로 "
                 "주파수를 옮기면 값이 옮겨간다 — 인용할 때 주파수를 반드시 붙여야 한다.")
OUT["K8_frequency_transfer"] = k8

# --------------------------------------------------------------------------- #
# K9 — 피치 법칙(감사 I7): «외곽 트위스트 폭 9.2°↔5.5° 라 플래시가 번져 −2.2 dB» 를 직접 잰다
# --------------------------------------------------------------------------- #
print("[K9] 피치 법칙", flush=True)
k9 = {}
azf = np.arange(0.0, 360.0, 0.1)
for pl in ("legacy", "dji_mini2"):
    tm = dc._blade(R_M, root_frac=0.070, chord_max=0.25, pitch_m=PITCH_M, n_sec=22,
                   law="legacy", pitch_law=pl)
    Pv, Nv, dAv = mesh_to_points(Shim(tm), LAM / DIV)
    els9 = np.arange(-40.0, -90.5, -1.0)
    pk = np.array([float(sig(field_mono(Pv, Nv, dAv, look(azf, float(e)))).max()) for e in els9])
    i = int(np.argmax(pk))
    s = sig(field_mono(Pv, Nv, dAv, look(azf, float(els9[i]))))
    j = int(np.argmax(s)); half = s[j] / 2
    lo, hi = j, j
    while lo > 0 and s[lo] > half:
        lo -= 1
    while hi < len(s) - 1 and s[hi] > half:
        hi += 1
    kk = np.interp(rr, dc.PITCH_LAWS[pl]["rr"], dc.PITCH_LAWS[pl]["k"])
    thp = np.degrees(np.arctan(kk * PITCH_M / (2 * np.pi * rr * R_M)))
    #  마이크로도플러 빗살
    ph9 = np.arange(NPH) * 360.0 / NPH
    E = field_mono(Pv, Nv, dAv, look(ph9, -30.0))
    X = np.abs(np.fft.fft(E - E.mean()) / NPH) ** 2
    n9 = np.fft.fftfreq(NPH, d=1.0 / NPH)
    bt = 2 * K * R_M * math.cos(math.radians(-30.0))
    k9[pl] = dict(flash_el_deg=float(els9[i]), flash_peak_dbsm=round(float(db(pk[i])), 2),
                  flash_az_width_3db_deg=round(float(azf[hi] - azf[lo]), 2),
                  outer_twist_span_0p6_0p9R_deg=round(float(np.interp(0.6, rr, thp)
                                                            - np.interp(0.9, rr, thp)), 2),
                  md_band_power_el30=float(X[(n9 >= 1) & (n9 <= bt)].sum()),
                  md_tipband_power_el30=float(X[(n9 >= 0.85 * bt) & (n9 <= 1.05 * bt)].sum()),
                  sigma_mean_dbsm_el30=round(float(db(sig(field_mono(Pv, Nv, dAv,
                                                                    look(AZ, -30.0))).mean())), 3))
a9, b9 = k9["legacy"], k9["dji_mini2"]
k9["delta_dji_minus_legacy"] = dict(
    d_flash_peak_db=round(b9["flash_peak_dbsm"] - a9["flash_peak_dbsm"], 3),
    d_flash_el_deg=round(b9["flash_el_deg"] - a9["flash_el_deg"], 2),
    d_flash_width_deg=round(b9["flash_az_width_3db_deg"] - a9["flash_az_width_3db_deg"], 2),
    d_md_band_db=round(float(10 * math.log10(b9["md_band_power_el30"]
                                             / a9["md_band_power_el30"])), 2),
    d_md_tipband_db=round(float(10 * math.log10(b9["md_tipband_power_el30"]
                                                / a9["md_tipband_power_el30"])), 2),
    d_sigma_mean_db=round(b9["sigma_mean_dbsm_el30"] - a9["sigma_mean_dbsm_el30"], 3))
k9["verdict_ko"] = ("피치 법칙을 legacy → DJI 로 갈면 외곽 트위스트 폭이 9.2° → 5.2° 로 줄지만, "
                    "플래시 봉우리·플래시 고각·플래시 방위폭이 전부 사실상 안 움직인다. "
                    "감사 I7 의 «어림 −2.2 dB» 는 커널로 재면 성립하지 않는다(감사 자신이 "
                    "«어림이 과했을 가능성» 이라고 단서를 달아 뒀다).")
OUT["K9_pitch_law"] = k9

OUT["_meta"] = dict(
    generated=time.strftime("%Y-%m-%d %H:%M:%S"),
    generator="benchmark/adv_rf_layer_0816.py",
    role="메쉬 감사 RF 층 적대검증 — 형상 오차가 3.5 GHz 에서 진짜 보이는가",
    gpu="사용 안 함 — numpy 전용, sionna/mitsuba import 0 회",
    kernel="src/rcs_po.py 그대로(모노) + 표준 스칼라 바이스태틱 PO(β=0 회귀 확인)",
    fc_hz=FC, lam_m=LAM, spacing="λ/%d" % DIV, gamma="PEC(|Γ|=1) — 지수 측정이라 공통항",
    airframe="matrice4e (prop_dia 274 mm, pitch 5.7 in), 날 1장",
    elapsed_s=round(time.time() - t00, 1))

with open(os.path.join(ROOT, "outputs", "mesh_adv_rf_layer_0816.json"), "w") as f:
    json.dump(OUT, f, ensure_ascii=False, indent=1)
print("완료", round(time.time() - t00, 1), "s")
