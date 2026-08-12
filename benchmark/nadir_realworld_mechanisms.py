# -*- coding: utf-8 -*-
"""nadir_realworld_mechanisms.py — **«실측에서 나딧 도플러가 남는다» 면 무엇이 만드나.**

배경(2026-08-12)
----------------
사용자가 «실제 실증 실험에서도 (직하방에서) 도플러가 남는 것 같더라» 고 전했다.
우리 원장(`outputs/verify_nadir_flash.json`)은 **모노스태틱·평면파**에서 나딧 변조가
정확히 0(−305 dB, float64 반올림)이라고 적어 두었다. 둘이 어긋난다.

⭐이 스크립트는 «사용자가 틀렸다» 를 증명하지 않는다. **우리 모형에 무엇이 빠졌나** 를 센다.

무엇을 재나
-----------
  G0. 게이트     기존 원장의 `C_D_geometry.offnadir_farfield` 를 **재현**한다(같은 대리모형).
  A.  기울기 사다리  나딧에서 벗어난 각 θ 를 촘촘히(0~30°) — 원거리장 평면파.
                     ac/dc·AM/PM·빗살 개수·도플러 폭. **거리 무관**이어야 한다.
  B.  거리 사다리   θ=0 은 1/r⁴ 로 죽고 θ>0 은 안 죽는다는 것을 확인.
  C.  허브 오프셋   해석식 — 팔 길이 L 이 만드는 근접장 항, 2엽 상쇄, 원거리장 소멸.
  D.  바람→기울기   DJI 공식 제원(최대피치 35° @ 21 m/s)에서 2차항력 상수를 뽑아
                     풍속별 호버 기울기 → A 사다리로 잔여 변조를 읽는다.
  E.  ⭐바이스태틱  패시브는 **이등분선**이 본다. Rx 가 바로 밑이어도 Tx 가 지상이면 널이 없다.
  F.  동체 상하운동 나딧에서는 수직 흔들림이 **100 % 시선방향**이다.
  G.  코닝·플래핑   정상 코닝은 나딧 도플러를 못 만든다(해석). 주기적 플래핑만 만든다.
  H.  편파          우리 커널은 **스칼라**다(rcs_sbr.py:214). 회전하는 얇은 날개의 편파변조는
                     원리적으로 못 낸다 — 원거리장·거리무관·1차 효과인데도.

⛔ GPU 를 쓰지 않는다. `sbr_field` 호출 없음 — verify_nadir_flash.py 와 **같은 평면패싯 PO
   대리모형**(재질·가림·다중반사 없음)만 CPU 로 돌린다. 절대값은 SBR 원장 쪽을 쓴다.

    PYTHONPATH=src:benchmark python benchmark/nadir_realworld_mechanisms.py
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

OUT_J = f"{ROOT}/outputs/nadir_realworld_mechanisms.json"

TJ = json.load(open(f"{ROOT}/outputs/report07_three_engines.json"))["_meta"]
PRF = float(TJ["prf_hz"])
FFL = float(TJ["f_flash_hz"])          # 126.667 Hz = 2 엽 × 63.333 rev/s
N = int(TJ["n"])                       # 4096
RPMS = np.asarray(TJ["rpm_per_rotor"], float)
FC = float(TJ["fc_hz"])                # 3.5 GHz
C0 = 2.998e8
LAM = C0 / FC
K = 2 * np.pi / LAM
DRONE = TJ.get("drone", "matrice4e")

# 원장이 쓰는 «날개끝 도플러»(el=0, 즉 시선이 로터면 안에 있을 때). microdoppler.py:128 규약
#   f_tip(el) = 2·(ω·R)/λ·cos(el)  →  나딧에서 벗어난 각 θ 로 바꾸면 f_tip0·sin(θ)
LEDGER = json.load(open(f"{ROOT}/outputs/verify_nadir_flash.json"))


def _facets(v, f):
    """verify_nadir_flash.py:_facets 와 동일."""
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    n = np.cross(b - a, c - a)
    ar2 = np.linalg.norm(n, axis=1)
    return n / (ar2[:, None] + 1e-300), 0.5 * ar2, (a + b + c) / 3.0


def acdc(x) -> float:
    x = np.asarray(x, complex)
    return round(float(10 * np.log10(np.mean(np.abs(x / x.mean() - 1.0) ** 2) + 1e-300)), 2)


def ampm(x) -> dict:
    """반송파(평균) 기준 진폭/위상 분해 — verify_nadir_flash.py:decompose 규약."""
    x = np.asarray(x, complex)
    r = x / x.mean()
    am = np.abs(r) - 1.0
    pm = np.angle(r)
    return dict(am_rms=round(float(am.std()), 6),
                pm_rms_deg=round(float(np.degrees(pm.std())), 3),
                pm_over_am_db=round(float(20 * np.log10(pm.std() / (am.std() + 1e-300))), 2))


def spectral(x) -> dict:
    """AC 전력이 어디까지 퍼져 있나. ⚠아래 «측정» 값은 **믿을 수 없다** — 이유는 반환 dict 참조."""
    x = np.asarray(x, complex)
    d = x / x.mean() - 1.0
    w = np.hanning(N)
    P = np.abs(np.fft.fftshift(np.fft.fft(d * w))) ** 2
    fr = np.fft.fftshift(np.fft.fftfreq(N, 1 / PRF))
    if P.max() <= 0:
        return dict(measured_f90_hz=0.0, measured_f99_hz=0.0, trust=False)
    o = np.argsort(np.abs(fr))
    c = np.cumsum(P[o]) / P.sum()
    return dict(
        measured_f90_hz=round(float(np.abs(fr[o])[np.searchsorted(c, 0.90)]), 1),
        measured_f99_hz=round(float(np.abs(fr[o])[np.searchsorted(c, 0.99)]), 1),
        trust=False,
        trust_note_ko=("⛔이 두 값을 인용하지 마라. 평면패싯 대리모형은 λ/12 격자를 안 쓴다 "
                       "→ PO 적분이 과소표본되어 **인공적인 광대역 성분**이 생긴다. "
                       "도플러 폭은 해석식(pred_peak_doppler_hz)으로만 말한다."))


# ═══════════════════════════════════════════════════════════════════════════
#  기하 대리모형 (CPU) — 평면파(원거리장) 기울기 사다리 + 구면파(근접장) 거리 사다리
# ═══════════════════════════════════════════════════════════════════════════
def run_geometry() -> dict:
    from articulated_fast import FastPoser, rotor_phases
    from drones import DRONES

    spec = DRONES[DRONE]
    fp = FastPoser(spec)
    ph = rotor_phases(np.arange(N) / PRF, RPMS, fp.dirs)
    f = np.asarray(fp.f)
    g = np.asarray(fp.g)
    isp = g == "prop"
    c0 = 0.5 * (fp.v.min(0) + fp.v.max(0))

    # ── 방향 목록 ────────────────────────────────────────────────────────
    #  el = −90 이 나딧(관측자가 바로 밑에서 올려다봄). off-nadir θ = 90 + el.
    GATE_EL = [-90.0, -89.5, -89.0, -88.0, -85.0, -80.0, -75.0]     # 원장 재현용
    TILTS = [0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0,
             7.0, 10.0, 15.0, 20.0, 30.0]                            # off-nadir [deg]
    els = sorted(set(GATE_EL + [-90.0 + t for t in TILTS]))
    UN = {e: np.array([np.cos(np.radians(e)), 0.0, np.sin(np.radians(e))]) for e in els}

    # 근접장 거리 사다리는 세 각도만
    RS = [10.0, 30.0, 100.0, 300.0, 1000.0]
    NEAR_EL = [-90.0, -89.0, -85.0]

    # ── ⭐가림(occlusion) 시험 — Ritchie 가 이름 붙인 1 번 가설 ──────────
    #  기존 대리모형은 «가림 없음» 이라 각 날개의 원거리장 나딧 응답이 **회전에 불변**이다.
    #  실제 기체는 관측자(아래)와 프롭 사이에 동체·암·짐벌이 있다. 날개 안쪽은 그 뒤로 들어갔다
    #  나왔다 하므로 **원거리장에서도** 반사가 주기적으로 변한다.
    #  z-버퍼로 근사한다: 시선 방향으로 가장 가까운 패싯만 살린다(픽셀 PIX m).
    PIX = 0.004
    OCC_EL = [-90.0, -89.0, -85.0]

    def zbuf_mask(cen, lit, uu, PIX=PIX):
        """시선 uu 로 볼 때 가려지지 않은 lit 패싯의 마스크."""
        # uu 는 표적 → 관측자. 관측자에서 본 깊이 = -(cen·uu) (클수록 멀다)
        e1 = np.array([1.0, 0.0, 0.0]) - uu * uu[0]
        if np.linalg.norm(e1) < 1e-6:
            e1 = np.array([0.0, 1.0, 0.0]) - uu * uu[1]
        e1 /= np.linalg.norm(e1)
        e2 = np.cross(uu, e1)
        idx = np.where(lit)[0]
        px = np.floor((cen[idx] @ e1) / PIX).astype(np.int64)
        py = np.floor((cen[idx] @ e2) / PIX).astype(np.int64)
        px -= px.min(); py -= py.min()
        key = px * (py.max() + 1) + py
        depth = -(cen[idx] @ uu)
        uk, inv = np.unique(key, return_inverse=True)
        best = np.full(uk.size, np.inf)
        np.minimum.at(best, inv, depth)
        keep = depth <= best[inv] + 1e-4          # 0.1 mm 공차
        m = np.zeros(cen.shape[0], bool)
        m[idx[keep]] = True
        return m

    Spl = {e: np.zeros(N, complex) for e in els}          # 전체
    Spl_p = {e: np.zeros(N, complex) for e in els}        # 프롭만
    Socc = {e: np.zeros(N, complex) for e in OCC_EL}      # ⭐가림 켬
    Socc_p = {e: np.zeros(N, complex) for e in OCC_EL}    # ⭐가림 켬 · 프롭만
    Ssph = {(e, R): np.zeros(N, complex) for e in NEAR_EL for R in RS}

    t0 = time.time()
    for i in range(N):
        v = fp.pose(ph[i]).v
        nn, ar, cen = _facets(v, f)
        for e in els:
            uu = UN[e]
            ww = np.maximum(nn @ uu, 0.0) * ar
            q = ww * np.exp(-1j * 2 * K * (cen @ uu))
            Spl[e][i] = q.sum()
            Spl_p[e][i] = q[isp].sum()
            if e in OCC_EL:
                vis = zbuf_mask(cen, ww > 0, uu)
                Socc[e][i] = q[vis].sum()
                Socc_p[e][i] = q[vis & isp].sum()
        for e in NEAR_EL:
            uu = UN[e]
            ww = np.maximum(nn @ uu, 0.0) * ar
            for R in RS:
                d = np.linalg.norm(cen - (c0 + R * uu), axis=1)
                Ssph[(e, R)][i] = (ww * np.exp(-1j * 2 * K * d)).sum()
        if i and i % 512 == 0:
            print(f"   geometry {i}/{N}  {time.time()-t0:.0f}s", flush=True)

    # ── G0 게이트 ────────────────────────────────────────────────────────
    led = LEDGER["C_D_geometry"]["offnadir_farfield"]
    gate = {}
    for e in GATE_EL:
        key = f"{e:+.1f}"
        mine = acdc(Spl[e])
        theirs = float(led[key]["ac_over_dc_db"])
        gate[key] = dict(ledger_db=theirs, recomputed_db=mine, delta_db=round(mine - theirs, 3))
    gate_max = max(abs(v["delta_db"]) for v in gate.values())

    # ── A. 기울기 사다리 ─────────────────────────────────────────────────
    f_tip0 = float(LEDGER["_meta"].get("_x", 0)) or None    # 안 쓴다 — 아래에서 직접 계산
    omega = 2 * np.pi * float(np.mean(RPMS)) / 60.0
    Rblade = spec.prop_dia_mm / 1000.0 / 2.0
    f_tip0 = 2.0 * (omega * Rblade) / LAM                   # microdoppler.py:128, cos(el)=1
    ladder = {}
    for t in TILTS:
        e = -90.0 + t
        row = dict(off_nadir_deg=t,
                   ac_over_dc_db=acdc(Spl[e]),
                   props_only_ac_over_dc_db=acdc(Spl_p[e]),
                   pred_peak_doppler_hz=round(f_tip0 * np.sin(np.radians(t)), 2),
                   pred_tip_phase_dev_rad=round(2 * K * Rblade * np.sin(np.radians(t)), 4))
        row.update(ampm(Spl[e]))
        row.update(spectral(Spl[e]))
        ladder[f"{t:g}"] = row

    # ── B. 거리 사다리 ───────────────────────────────────────────────────
    rng = {}
    for e in NEAR_EL:
        t = 90.0 + e
        rng[f"offnadir_{t:g}deg"] = dict(
            far_field_plane_wave_db=acdc(Spl[e]),
            by_range_db={f"{int(R)}m": acdc(Ssph[(e, R)]) for R in RS})

    # ── ⭐가림 시험 결과 ─────────────────────────────────────────────────
    occ = {}
    for e in OCC_EL:
        t = 90.0 + e
        occ[f"offnadir_{t:g}deg"] = dict(
            no_occlusion_ac_over_dc_db=acdc(Spl[e]),
            with_occlusion_ac_over_dc_db=acdc(Socc[e]),
            no_occlusion_props_only_db=acdc(Spl_p[e]),
            with_occlusion_props_only_db=acdc(Socc_p[e]),
            visible_area_note_ko="같은 평면파(원거리장). 가림만 켜고 끈다.")
    # ⚠픽셀 크기 민감도 — z-버퍼의 «과다 제거» 를 정직하게 드러낸다 (짧은 창 N2)
    N2 = 1024
    ph2 = ph[:N2]
    pixsens = {}
    for pix in (0.002, 0.004, 0.008, 0.016, 0.032):
        S = np.zeros(N2, complex)
        fr = np.zeros(N2)
        for i in range(N2):
            nn, ar, cen = _facets(fp.pose(ph2[i]).v, f)
            uu = UN[-90.0]
            ww = np.maximum(nn @ uu, 0.0) * ar
            q = ww * np.exp(-1j * 2 * K * (cen @ uu))
            m = zbuf_mask(cen, ww > 0, uu, pix)
            S[i] = q[m].sum()
            fr[i] = ar[m].sum() / ar[ww > 0].sum()
        pixsens[f"{pix*1e3:g}mm"] = dict(ac_over_dc_db=acdc(S),
                                         visible_area_fraction=round(float(fr.mean()), 4))
    ar0 = _facets(fp.pose(ph[0]).v, f)[1]
    occ["_pixel_sensitivity"] = dict(
        n_slow_time=N2, rows=pixsens,
        facet_median_side_mm=round(float(1e3 * np.sqrt(2 * np.median(ar0))), 2),
        honest_ko=("⚠**크기는 못 믿는다.** 픽셀을 2→32 mm 로 바꾸면 −34.9 ~ −18.3 dB 사이를 "
                   "돌아다니고, 보이는 면적 비율이 0.62→0.03 으로 떨어진다 — 즉 z-버퍼가 "
                   "**실제로 안 가려진 패싯까지 지운다**(한 픽셀에 여러 패싯이 정당하게 들어가는데 "
                   "하나만 남기기 때문). 패싯 중앙값 한 변이 3 mm 대라 2 mm 픽셀도 여유가 없다. "
                   "⇒ 이 시험이 증명하는 것은 **«정확히 0 이 아니다»(대칭 깨짐)** 뿐이고, "
                   "몇 dB 인지는 진짜 SBR 커널로 재야 한다."))
    occ["_method_ko"] = (
        f"z-버퍼 근사(기본 픽셀 {PIX*1e3:.0f} mm): 시선 방향으로 가장 가까운 패싯만 남긴다. "
        "레이 캐스팅이 아니라 **중앙점 래스터화**라 패싯이 픽셀보다 크면 과다 제거된다 — "
        "_pixel_sensitivity 를 반드시 같이 읽어라.")
    occ["_tension_with_sbr_ko"] = (
        "⚠원장 충돌: 진짜 SBR 커널(가림 포함, 재질 포함, 10 m)의 el−90 실측 ac/dc 는 "
        f"{LEDGER['B_decomposition']['ours']['el-90']['ac_over_dc_db']} dB 이고, 이는 "
        f"**가림 없는** 근접장 대리모형 {LEDGER['C_D_geometry']['nadir_spherical_10m_ac_over_dc_db']} dB "
        "와 거의 같다. 즉 우리 커널에서 가림 기여는 −38 dB 보다 **작다**. "
        "여기 z-버퍼 값(−28 dB)은 과대다. 결판은 **거리를 늘린 SBR 실행**이다 — "
        "근접장 항은 1/r⁴ 로 죽으니 100~1000 m 에서 남는 바닥이 곧 가림+원거리장 항이다. ⭐GPU 필요.")
    occ["_why_ko"] = (
        "가림이 없으면 나딧에서 각 날개의 원거리장 응답이 **회전에 정확히 불변**이다"
        "(회전축을 중심으로 한 회전은 시선방향 좌표를 안 바꾼다). 동체·암·짐벌이 날개 안쪽을 "
        "주기적으로 가리면 그 불변성이 깨진다 — **원거리장·거리무관·1차** 효과다.")

    return dict(gate=dict(rows=gate, max_abs_delta_db=round(gate_max, 3),
                          pass_=bool(gate_max < 0.05)),
                tilt_ladder=ladder, range_ladder=rng, occlusion_test=occ,
                kinematics=dict(f_tip0_hz=round(f_tip0, 1), f_flash_hz=round(FFL, 2),
                                f_rot_hz=round(FFL / spec.prop_blades, 3),
                                blade_R_m=round(Rblade, 4), lambda_m=round(LAM, 5),
                                omega_rad_s=round(omega, 2),
                                v_tip_m_s=round(omega * Rblade, 2)))


# ═══════════════════════════════════════════════════════════════════════════
#  C. 허브 오프셋 (해석)
# ═══════════════════════════════════════════════════════════════════════════
def hub_offset() -> dict:
    from drones import DRONES
    spec = DRONES[DRONE]
    Rb = spec.prop_dia_mm / 1000.0 / 2.0
    Ls = np.asarray(spec.rotor_r_mm, float) / 1000.0
    L = float(Ls.max())
    rows = {}
    for R in (3.0, 10.0, 30.0, 100.0, 300.0, 1000.0):
        dr = L * Rb / R                       # 편도 거리변동 진폭 [m] (1차)
        phi1 = 2 * K * dr                     # 왕복 위상 진폭 [rad] — **한 날개**
        # 2 엽은 φ 와 φ+180 이라 1차 항이 **정확히 상쇄**된다. 남는 것은 2차:
        #   d(φ) ≈ R + (L²+s²)/(2R) + L s cosφ/R − (L s cosφ)²/(2R³) + …
        dr2 = (L * Rb) ** 2 / (2 * R ** 3)
        phi2 = 2 * K * dr2
        rows[f"{int(R)}m"] = dict(
            first_order_path_amp_mm=round(dr * 1e3, 4),
            first_order_twoway_phase_deg=round(np.degrees(phi1), 3),
            second_order_path_amp_mm=round(dr2 * 1e3, 6),
            second_order_twoway_phase_deg=round(np.degrees(phi2), 5))
    return dict(
        arm_radius_L_m=round(L, 4), arm_radius_all_m=[round(x, 4) for x in Ls],
        blade_radius_r_m=round(Rb, 4), lambda_m=round(LAM, 5),
        geometry_ko=("레이다가 기체 **중심** 바로 위에 있어도 로터 허브는 수평으로 L 만큼 "
                     "떨어져 있다. 블레이드 요소(허브에서 s)의 수평거리는 "
                     "ρ(φ)=√(L²+s²+2Ls·cosφ) 로 φ 에 따라 변하고, 거리 R 에서 "
                     "d≈R+ρ²/(2R) 이므로 경로가 **L·s·cosφ/R** 만큼 흔들린다."),
        two_blade_ko=("⭐2 엽 프로펠러는 φ 와 φ+180° 라 cosφ 항이 **정확히 상쇄**된다. "
                      "그래서 남는 것은 2차항뿐이고, 진폭이 1/R² → 전력이 **1/r⁴** 로 죽는다. "
                      "원장의 range_sweep_nadir(10→100 m 에서 −40.8 dB, 이론 40log10(10)=40 dB)가 "
                      "바로 이것이다."),
        farfield_ko=("원거리장(평면파)에서는 ρ²/(2R) 항 자체가 0 이므로 **허브 오프셋 기여가 "
                     "완전히 사라진다.** 나딧에서 어떤 s·L 이어도 위상은 상수다 — "
                     "회전축을 중심으로 한 회전은 시선방향 좌표 z 를 바꾸지 않는다."),
        rows=rows)


# ═══════════════════════════════════════════════════════════════════════════
#  D. 바람 → 호버 기울기 (DJI 공식 제원에서 유도)
# ═══════════════════════════════════════════════════════════════════════════
def wind_tilt(ladder: dict) -> dict:
    from drones import DRONES
    spec = DRONES[DRONE]
    m = spec.weight_g / 1000.0
    W = m * 9.80665
    v_max, tilt_max = 21.0, 35.0          # DJI 공식: 최대 수평속도 21 m/s, 최대 피치각 35°
    kq = W * np.tan(np.radians(tilt_max)) / v_max ** 2      # 2차 항력계수 [N·s²/m²]

    # 사다리에서 ac/dc 를 로그-로그 보간해 읽는다
    xs = np.array([float(k) for k in ladder if float(k) > 0])
    xs.sort()
    ys = np.array([ladder[f"{x:g}"]["ac_over_dc_db"] for x in xs])

    def read(theta):
        if theta <= xs[0]:
            # 소각 영역은 전력 ∝ θ⁴ (2 엽 상쇄 뒤 2차항) — 사다리 첫 점에서 외삽
            return round(float(ys[0] + 40 * np.log10(max(theta, 1e-6) / xs[0])), 2)
        return round(float(np.interp(np.log10(theta), np.log10(xs), ys)), 2)

    rows = {}
    for w in (0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0):
        th = float(np.degrees(np.arctan(kq * w ** 2 / W)))
        rows[f"{w:g}m/s"] = dict(
            tilt_deg=round(th, 3),
            ac_over_dc_db=read(th),
            peak_doppler_hz=round(float(np.interp(0, [0], [0])) if th == 0 else
                                  float(2 * (2 * np.pi * np.mean(RPMS) / 60.0) *
                                        (spec.prop_dia_mm / 2000.0) / LAM * np.sin(np.radians(th))), 2))
    return dict(
        method_ko=("DJI 공식 제원 두 개(최대 수평속도 21 m/s, 최대 피치각 35°)에서 2차 항력 "
                   "상수를 뽑는다: k = m·g·tan(35°)/21² . 호버 중 풍속 w 를 버티려면 "
                   "tan θ = k·w²/(m·g). ⚠ 이건 **유도값**이지 실측 자세로그가 아니다 — "
                   "저속에서는 로터 유도류 항력 때문에 과소평가일 수 있다."),
        source_ko="docs/drone_specs_2026.json (matrice4e: 최대속도 21 m/s, 최대 피치 35°, 내풍 12 m/s)",
        mass_kg=round(m, 4), weight_N=round(W, 3),
        drag_const_N_s2_m2=round(float(kq), 5),
        max_wind_spec_m_s=12.0,
        rows=rows)


# ═══════════════════════════════════════════════════════════════════════════
#  E. ⭐바이스태틱 — 패시브는 «이등분선» 이 본다
# ═══════════════════════════════════════════════════════════════════════════
def bistatic(f_tip0: float) -> dict:
    rows = {}
    for h in (30.0, 60.0, 100.0, 200.0):          # 드론 고도 [m] (Rx 는 바로 밑 지상)
        for D in (100.0, 300.0, 500.0, 1000.0, 3000.0):   # Tx(기지국)까지 수평거리 [m]
            u_r = np.array([0.0, 0.0, -1.0])                    # 표적 → Rx (바로 아래)
            u_t = np.array([D, 0.0, -h]) / np.hypot(D, h)       # 표적 → Tx
            s = u_r + u_t
            beta = float(np.degrees(np.arccos(np.clip(u_r @ u_t, -1, 1))))
            b = s / (np.linalg.norm(s) + 1e-300)
            # 로터 축은 +z (기체 수평 가정). 이등분선이 축과 이루는 각:
            th_b = float(np.degrees(np.arccos(np.clip(abs(b[2]), 0, 1))))
            cb2 = float(np.cos(np.radians(beta / 2)))
            rows[f"h{int(h)}m_D{int(D)}m"] = dict(
                bistatic_angle_deg=round(beta, 2),
                cos_half_beta=round(cb2, 4),
                bisector_off_rotor_axis_deg=round(th_b, 2),
                peak_micro_doppler_hz=round(f_tip0 * cb2 * np.sin(np.radians(th_b)), 1),
                full_spread_hz=round(2 * f_tip0 * cb2 * np.sin(np.radians(th_b)), 1))
    return dict(
        formula=("f_d,max = f_tip0 · cos(β/2) · sin(ψ)   "
                 "[β = 바이스태틱 각, ψ = 이등분선과 로터 회전축이 이루는 각]"),
        prior_work=("Costa/Thomä (arXiv:2504.05168) 식: B_D = 4·ω·L_B·cos(β/2)·sin(ψ)/λ₀ "
                    "— 같은 식이다(그쪽 B_D 는 전폭 = 2·f_d,max). ⚠원문 HTML 로 확인, "
                    "PDF 원본 대조는 미완."),
        why_it_matters_ko=("널이 생기려면 **이등분선**이 로터 축과 나란해야 한다. "
                           "즉 Tx 와 Rx 가 **둘 다** 드론 바로 밑(또는 위)에 있어야 한다. "
                           "패시브 바이스태틱에서 조명원은 지상 기지국이라 거의 수평이므로 "
                           "Rx 를 정확히 표적 바로 밑에 놓아도 이등분선은 축에서 수십 도 벗어난다 "
                           "→ **나딧 널이 아예 존재하지 않는다.**"),
        rows=rows)


# ═══════════════════════════════════════════════════════════════════════════
#  F·G·H. 동체 상하운동 · 코닝/플래핑 · 편파
# ═══════════════════════════════════════════════════════════════════════════
def other_terms(f_tip0: float) -> dict:
    from drones import DRONES
    spec = DRONES[DRONE]
    Rb = spec.prop_dia_mm / 1000.0 / 2.0
    omega = 2 * np.pi * float(np.mean(RPMS)) / 60.0

    # F. 나딧에서는 수직 흔들림이 100 % 시선방향이다.
    body = {}
    for amp, fz in ((0.02, 0.3), (0.05, 0.5), (0.10, 0.5), (0.10, 1.0), (0.30, 0.5)):
        vz = 2 * np.pi * fz * amp
        body[f"amp{amp:g}m_at{fz:g}Hz"] = dict(
            peak_vertical_speed_m_s=round(vz, 4),
            peak_doppler_hz=round(2 * vz / LAM, 2))

    # G. 코닝은 정상항이라 나딧 도플러를 못 만든다. 주기적 플래핑만 만든다.
    flap = {}
    for a1_deg in (0.1, 0.25, 0.5, 1.0, 2.0):
        a1 = np.radians(a1_deg)
        vz = Rb * a1 * omega          # 팁의 축방향 속도 진폭
        flap[f"a1_{a1_deg:g}deg"] = dict(
            tip_axial_speed_m_s=round(vz, 4),
            peak_doppler_hz=round(2 * vz / LAM, 2))

    return dict(
        F_body_vertical=dict(
            why_ko=("나딧에서는 **수평 표류가 도플러를 0 으로 만들고 수직 흔들림이 전부 "
                    "시선방향**이 된다. 이건 마이크로도플러가 아니라 동체선이 흔들리는 것이지만 "
                    "스펙트로그램에서는 «0 Hz 선이 번진다» 로 보인다."),
            anchor_ko="DJI 호버링 정확도 제원(수직 ±0.1 m 급)은 위치 오차지 속도가 아니다 — 아래는 감도표다.",
            rows=body),
        G_coning_flapping=dict(
            steady_coning_ko=("⭐**정상 코닝(β₀ 일정)은 나딧에서 도플러를 만들지 못한다.** "
                              "원뿔 위를 도는 팁도 높이가 일정해 축방향 속도가 0 이다. "
                              "코닝이 바꾸는 것은 반사 **세기**(로브 방향)이지 도플러가 아니다."),
            cyclic_flapping_ko=("주기적 플래핑 β = a₀ − a₁cosψ − b₁sinψ 만이 축방향 속도를 만든다. "
                                "팁의 축방향 속도 진폭 = R·a₁·Ω → 도플러 = 2R a₁ Ω/λ."),
            measured_coning_ko=("실측 앵커: KTH/NASA 계열 학위논문(NTRS 20160014468) — "
                                "**DJI Phantom 3 플라스틱 블레이드 코닝 ≈ 2° @ 7500 rpm** "
                                "(팁 처짐 3.7 mm ± 0.16), 카본 T-motor 15×5 는 **1.1° @ 5000 rpm** "
                                "(2.2 mm). 같은 문헌: «For an isolated rotor in hover … "
                                "this effect [flapping] will not be present» — 즉 무풍 호버에서는 "
                                "**주기 성분이 없다**. 소형 멀티로터의 a₁ 실측치는 못 찾았다(미확인)."),
            sensitivity_per_deg_hz=round(2 * Rb * np.radians(1.0) * omega / LAM, 2),
            rows=flap),
        H_polarization=dict(
            our_kernel_ko=("⛔ 우리 커널은 **스칼라**다. `src/rcs_sbr.py:214` 주석 원문: "
                           "«면적분은 스칼라라 편파가 없다 → PO 는 두 편파에 공통». "
                           "즉 회전에 따른 편파 응답 변화를 **원리적으로 못 낸다**."),
            mechanism_ko=("얇고 긴 날개는 시선에 수직인 평면 안에서 **회전하는 막대**로 보인다. "
                          "선형편파 수신에서 동일편파 응답은 막대 축과 E 벡터가 이루는 각에 걸리므로 "
                          "회전각 2 배 주파수로 진폭이 변조된다. 2 엽 프로펠러는 180° 마주보아 "
                          "«막대 하나» 이므로 변조 주파수 = 2×f_rot = f_flash 다."),
            geometry_check=dict(
                blade_chord_max_m=round(0.25 * Rb, 4),   # drone_cad.CHORD_MAX_OVER_R = 0.25
                chord_over_lambda=round(0.25 * Rb / LAM, 3),
                blade_span_over_lambda=round(2 * Rb / LAM, 3),
                note_ko=("시위(가장 넓은 곳) ≈ 0.25·R. λ 대비 0.4 이면 **λ 보다 좁은 띠**라 "
                         "편파의존이 크다(넓은 평판이면 수직입사에서 편파무관).")),
            frequency_ko=("⭐이 변조는 f_flash = 126.67 Hz — 원장이 나딧에서 실제로 본 빗살과 "
                          "**같은 주파수**다. 그러나 우리 것은 근접장 곡률(1/r⁴ 로 소멸)이고 "
                          "편파 기전은 **원거리장·거리무관·1차**다."),
            circular_pol_ko=("원형편파를 쓰면 회전하는 막대는 진폭변조가 아니라 **주파수 이동**을 "
                             "만든다(교차편파 채널에서 ±2·f_rot). 즉 편파를 넣으면 나딧에서도 "
                             "진짜 «도플러» 가 나온다."),
            status="우리 시뮬레이션에 없음 — 벡터 PO(편파 다이애딕)로 승격해야 함"))


# ═══════════════════════════════════════════════════════════════════════════
#  선행연구 — ⭐원문을 직접 읽은 것만 verbatim 으로 적는다
# ═══════════════════════════════════════════════════════════════════════════
def prior_work() -> dict:
    return {
        "_rule_ko": ("verbatim 필드는 **내가 원문(PDF/HTML)에서 직접 뽑은 문장**이다. "
                     "요약 도구가 대신 읽어 준 것은 status='UNVERIFIED' 로 적었다."),
        "ritchie_uav_bird_chapter": dict(
            status="VERIFIED (PDF 원문 텍스트 추출)",
            cite=("M. Ritchie, C. Horne, N. Peters, «Chapter I — Radar UAV and Bird Signature "
                  "comparisons with Micro-Doppler», UCL Discovery eprint 10139175"),
            url="https://discovery.ucl.ac.uk/id/eprint/10139175/7/Ritchie_Bird_Drone%20Chapter%20v13.pdf",
            setup=dict(
                target="DJI Spark", chamber="anechoic",
                radar="X-band FMCW", fc_hz=10.25e9, bandwidth_hz=400e6, prf_hz=2000,
                chirp_period_s=4e-4, dwell_s=20,
                geometry_verbatim=("The physical arrangement of the experimental measurements is "
                                   "based on a boom which is initially placed horizontally (0°), and "
                                   "can be raised such that it forms an angle with the horizontal "
                                   "plane up to a maximum angle of 90°. … The target UAV is mounted "
                                   "on a small platform which pivots at the upper end of the boom "
                                   "such that the UAV can be operated in as close as possible to a "
                                   "normal horizontal hovering position"),
                angles_verbatim=("Measurements were taken at HH, HV, VH and VV polarisations, and "
                                 "with observation angles at 20º steps between 0º and 80º, and an "
                                 "additional measurement at 90º. The 0º angle observation represents "
                                 "the in-plane measurement where the radar sensor measures the UAV "
                                 "side-on. The 90º angle case is where the UAV is vertically above "
                                 "the radar sensor."),
                idle_verbatim="The UAV motors are started and allowed to run at the default idle rate.",
                herm_line_hz=175),
            headline_verbatim=("HERM lines are clearly visible at 90° elevation angle for all "
                               "polarisations. This is unexpected since there should be very little "
                               "motion along boresight in this configuration. However, the results "
                               "show not only that HERM lines are visible, but also that they are of "
                               "higher intensity than for mid-range elevation angles (with the "
                               "exception of VH)."),
            their_hypotheses_verbatim=(
                "A detailed explanation of this phenomenon is beyond the scope of this study, "
                "however, we hypothesise that there may be multiple contributing factors to HERM "
                "line creation. Although classical blade flash, as previously described in this "
                "chapter, is clearly one of them, by itself it does not explain the visibility of "
                "HERM lines at 90° elevation angle. Other possible factors could be obstruction of "
                "the blades by the drone body at a particular rotation angle leading to a periodic "
                "variation in target RCS, or a periodic modulation of target return caused by blades "
                "moving in and out of alignment with the system polarisation."),
            polarisation_verbatim=("Figure 16 and Figure 17 show that an HH polarisation "
                                   "configuration gives the highest intensity HERM lines across all "
                                   "viewing angles, and is therefore the most suitable configuration "
                                   "for C-UAV systems."),
            their_equation3_verbatim=("{f_d}max = (4πLΩ1/λ) cos θ … Where L is the blade length, λ "
                                      "the wavelength, and θ is the angle between the sensor and the "
                                      "plane of the UAV rotor."),
            why_it_matters_ko=("⭐**실측이 사용자 편이다.** 무향실·모노스태틱·기체 수평 고정·모터 "
                               "아이들 — 바람도 기울기도 없는 조건에서 90° 앙각(레이다가 로터 축 "
                               "위)에서 HERM 선이 «모든 편파에서 뚜렷하게» 보였고, 중간 앙각보다 "
                               "**더 셌다**. 그리고 저자들이 스스로 지목한 두 원인이 우리가 못 "
                               "넣은 두 가지와 **정확히 같다**: (1) 동체에 의한 날개 가림 → 주기적 "
                               "RCS 변조, (2) 날개가 편파와 정렬됐다 어긋났다 하는 변조."),
        ),
        "costa_2504_05168v2": dict(
            status="VERIFIED (arXiv HTML 원문 직접 파싱)",
            cite=("H. C. A. Costa et al., «Modeling Micro-Doppler Signature of Multi-Propeller "
                  "Drones in Distributed ISAC», arXiv:2504.05168v2 (TU Ilmenau, BIRA)"),
            eq4_phase_verbatim=("… L_B cos(ω t + φ_B(i)) cos(ψ) … where R_O is the range of the "
                                "rotation center O, ω is the angular velocity of the blades, ψ is the "
                                "elevation angle from the radar to the rotation center with respect "
                                "to the rotation plane"),
            eq_BD_verbatim=("the frequency domain signature of rotating propellers is a periodic "
                            "sequence of spikes separated by Δf = N_B ω/2π and distributed over a "
                            "Doppler spread of B_D = 4 ω L_B cos(β/2) sin(ψ)/λ_0"),
            our_finding_ko=("⭐**두 식이 서로 어긋난다.** 같은 ψ(로터 **면** 기준 앙각)를 쓰는데 "
                            "식 (4)는 cos(ψ), §II-F1 의 B_D 는 sin(ψ) 다. ψ=0(시선이 로터면 안)에서 "
                            "B_D=0 이 되는데 그건 물리적으로 틀렸다 — 로터면 안이 도플러 **최대**다. "
                            "물리적으로 맞는 쪽은 식 (4)이고, 그것은 우리 규약 "
                            "f_tip(el)=f_tip0·cos(el) 및 Ritchie 식 (3)과 **일치**한다. "
                            "⇒ B_D 식을 인용할 때는 각도 규약을 뒤집어 쓸 것."),
            vibration_verbatim=("Additionally, as can be seen in Fig. 7f, the contribution of the "
                                "static parts also presents some Doppler spread. That happens due to "
                                "the vibration of the target … Micro-Doppler due to vibration can be "
                                "emulated by adding a time-dependent change in phase due to fast "
                                "short-distance displacements. … D_v(t) = D_v(t−1) + D_0·U(−1,1)"),
            vibration_ko=("우리 후보 5 번(동체 진동)을 **실측이 확인**하고 동료가 이미 모형에 "
                          "넣었다. 그들은 «진동을 넣는 것이 동체 기여를 제대로 그리는 데 vital» "
                          "이라고 결론짓는다."),
            validation_target="Tarot IRON MAN 650, blade radius 16.55 cm, 2 blades, 1500/2000 rpm, 3.7 & 7 GHz",
        ),
        "nasa_cr_2017_219428": dict(
            status="VERIFIED (PDF 원문 텍스트 추출)",
            cite="NASA CR-2017-219428 (Nowicki), «Measurement and Modeling of Multicopter Blade Deflections»",
            url="https://rotorcraft.arc.nasa.gov/Publications/files/Nowicki_CR-2017-219428_Final.pdf",
            coning_verbatim=("For the plastic DJI Phantom 3 blades, the relative displacement at the "
                             "leading edge of the tip was once again found to be between 3.5–4 mm … "
                             "at 7500 RPM. The corresponding coning angle is then 1.8–2.1 degrees. … "
                             "For the carbon fiber T-motor blades, it was found that the deflection "
                             "reached up to a mean value of 1.3 mm and a coning angle of 0.4 degrees "
                             "for the highest measured RPM of 5500"),
            no_cyclic_verbatim=("For an isolated rotor in hover, which was tested here, this effect "
                                "will not be present. The coning angle is the flapping angle in hover "
                                "or the average flapping angle while in forward flight."),
            no_leadlag_verbatim=("Rotors that have hinges also experience lead-lag displacement, but "
                                 "due to the hingeless structure of the propellers used in "
                                 "multicopters, this phenomenon is not present"),
            ko=("소형 멀티로터 블레이드의 **정상 코닝은 0.4~2°** 다. 그러나 정상 코닝은 나딧 "
                "도플러를 못 만든다(축방향 속도 0). 주기 성분(a₁)은 무풍 호버에서 **원리적으로 "
                "없고**, 소형 멀티로터의 전진비행 a₁ 실측치는 **못 찾았다(미확인)**."),
        ),
        "dji_matrice4e_spec": dict(
            status="VERIFIED (docs/drone_specs_2026.json 및 DJI 공식 제원표)",
            max_wind_resistance_m_s=12.0, max_pitch_deg=35.0, max_horizontal_speed_m_s=21.0,
            hovering_accuracy="±0.1 m (Vision) / ±0.5 m (GNSS) / ±0.1 m (RTK)",
            ko="D 절의 바람→기울기 환산은 이 세 숫자(21 m/s, 35°, 1.219 kg)에서만 나온다.",
        ),
        "costa_2401_14448": dict(
            status="UNVERIFIED (요약 도구 경유 — 원문 미확인)",
            cite="arXiv:2401.14448, «Static Reflectivity and Micro-Doppler Signature of Drones for Distributed ICAS»",
            claim=("측정이 드론의 **하반구**만 덮었다고 요약됐다(β 10°~180°, 드론을 뒤집어 배치). "
                   "즉 로터 축 부근 기하는 **없다**. ⚠원문 대조 필요."),
        ),
    }


def verdict(geo: dict, wind: dict, bis: dict) -> dict:
    L = geo["tilt_ladder"]
    occ = geo["occlusion_test"]
    return {
        "question_ko": "«실측에서 나딧 도플러가 남는다» 면 가장 큰 기여자는 무엇이고 크기는 얼마인가",
        "answer_ko": (
            "**두 가지를 갈라서 답해야 한다.**\n"
            "① **우리 시스템(패시브 바이스태틱)에는 나딧 널이 애초에 없다.** 널은 **이등분선**이 "
            "로터 축과 나란할 때만 생기는데, 조명원이 지상 기지국이라 Rx 를 표적 바로 밑에 놓아도 "
            "이등분선은 축에서 13~45° 벗어난다. 그때 마이크로도플러 최대는 "
            f"**{min(v['peak_micro_doppler_hz'] for v in bis['rows'].values()):.0f}~"
            f"{max(v['peak_micro_doppler_hz'] for v in bis['rows'].values()):.0f} Hz** 다 — "
            "«잔여» 가 아니라 **온전한 신호**다.\n"
            "② **진짜 모노스태틱 나딧(레이다가 로터 축 위)에서도 실측은 도플러가 남는다고 말한다** "
            "— Ritchie 등의 무향실 실측(DJI Spark, 10.25 GHz, 기체 수평 고정, 모터 아이들)에서 "
            "90° 앙각의 HERM 선이 **모든 편파에서 뚜렷**했고 중간 앙각보다 **더 셌다**. "
            "그 조건에는 바람도 기울기도 없었으므로 남은 원인은 **기체에 의한 날개 가림**과 "
            "**편파 정렬 변조** 둘뿐이고, 저자들도 그 둘을 지목했다. "
            "우리 대리모형에서 가림만 켜면 나딧 변조가 "
            f"**{occ['offnadir_0deg']['no_occlusion_ac_over_dc_db']:.0f} dB → "
            f"{occ['offnadir_0deg']['with_occlusion_ac_over_dc_db']:.0f} dB** 로 살아난다"
            "(⚠크기는 못 믿는다 — _pixel_sensitivity 참조. 확실한 것은 «정확히 0 이 아니다»)."),
        "ranking_monostatic_nadir": [
            dict(rank=1, mechanism="날개가 편파와 정렬됐다 어긋났다 하는 변조(polarisation)",
                 size="정량 불가 — 우리 커널이 **스칼라**라 원리적으로 못 낸다",
                 range_dependence="없음(원거리장·1차)",
                 evidence="Ritchie 실측: 90°에서 편파마다 다르게 남음(HH 최강·VH 최약) + 저자 가설"),
            dict(rank=2, mechanism="동체·암·짐벌에 의한 날개 가림 → 주기적 RCS 변조",
                 size=f"{occ['offnadir_0deg']['with_occlusion_ac_over_dc_db']} dB (z-버퍼 추정, "
                      "픽셀에 따라 −34.9~−18.3 dB 로 흔들림; 진짜 SBR 10 m 실측은 −38.3 dB 이므로 "
                      "**과대일 가능성**)",
                 range_dependence="없음(원거리장·1차)",
                 evidence="이 원장 A_tilt_and_range.occlusion_test + Ritchie 저자 가설"),
            dict(rank=3, mechanism="기체 기울기(바람·자세오차) + 레이다 지향오차",
                 size=(f"바람 6 m/s → 기울기 {wind['rows']['6m/s']['tilt_deg']}° → "
                       f"{wind['rows']['6m/s']['ac_over_dc_db']} dB, 최대 도플러 "
                       f"{wind['rows']['6m/s']['peak_doppler_hz']} Hz; "
                       f"8 m/s → {wind['rows']['8m/s']['tilt_deg']}° → "
                       f"{wind['rows']['8m/s']['ac_over_dc_db']} dB"),
                 range_dependence="없음(원거리장·1차)",
                 evidence="이 원장 D_wind_to_tilt (DJI 공식 제원 유도) + A 사다리",
                 caveat_ko="Ritchie 무향실에는 이게 없었다 — 그러니 실측 관측의 **유일한** 설명은 못 된다"),
            dict(rank=4, mechanism="동체 진동·상하 흔들림(나딧에서는 100 % 시선방향)",
                 size="0.9~22 Hz 의 **0 Hz 선 번짐**(빗살이 아님)",
                 range_dependence="없음",
                 evidence="이 원장 FGH_other_terms.F + Costa 2504.05168v2 실측/모형"),
            dict(rank=5, mechanism="근접장 파면 곡률(허브 오프셋 2차항)",
                 size=(f"10 m 에서 {geo['range_ladder']['offnadir_0deg']['by_range_db']['10m']} dB → "
                       f"100 m 에서 {geo['range_ladder']['offnadir_0deg']['by_range_db']['100m']} dB → "
                       f"1 km 에서 {geo['range_ladder']['offnadir_0deg']['by_range_db']['1000m']} dB"),
                 range_dependence="⭐1/r⁴ — 야외 실측 거리에서는 **사실상 없다**",
                 evidence="이 원장 A_tilt_and_range.range_ladder (+ 기존 verify_nadir_flash 원장)"),
            dict(rank=6, mechanism="블레이드 주기 플래핑(cyclic flapping)",
                 size="a₁ 1° 당 22.2 Hz. ⚠소형 멀티로터의 a₁ 실측치를 **못 찾았다**",
                 range_dependence="없음",
                 evidence="해석 + NASA CR-2017-219428(정상 코닝 0.4~2°, 무풍 호버엔 주기성분 없음)"),
        ],
        "what_is_NOT_the_answer_ko": [
            "정상 코닝 — 원뿔 위를 도는 팁도 높이가 일정해 축방향 속도가 0 이다. 도플러를 못 만든다.",
            "허브 오프셋 그 자체 — 원거리장에서는 완전히 사라진다(회전축 둘레 회전은 시선좌표를 안 바꾼다).",
            f"근접장 곡률 — 100 m 에서 이미 {geo['range_ladder']['offnadir_0deg']['by_range_db']['100m']} dB 다.",
            "블레이드 비틀림/피치 — 회전하는 강체의 **투영 면적**은 회전각에 무관하다(원거리장). "
            "진폭변조를 만들려면 편파나 가림이 필요하다.",
        ],
        "what_to_add_upstream_first_ko": [
            "① [커널·GPU 필요·코드 0] **거리를 늘린 SBR 재실행**: el=−90 을 10/30/100/300/1000 m 로. "
            "근접장 항은 1/r⁴ 로 죽으니 남는 **바닥**이 곧 가림+원거리장 항이다. 지금 −38.3 dB "
            "라는 숫자가 근접장 인공물인지 실물인지 이것 하나로 갈린다.",
            "② [커널·큰 작업] **벡터(편파) PO 로 승격.** `rcs_sbr.py:214` 가 자백하듯 지금 면적분은 "
            "스칼라다. 회전하는 얇은 날개의 편파 변조는 원거리장·거리무관·1차 효과인데 "
            "**구조적으로 못 낸다**. 실측(Ritchie)이 90°에서 편파마다 다른 답을 준 이상, "
            "편파 없이는 나딧을 논할 수 없다.",
            "③ [기하] **기체 자세를 상태로 승격.** 지금 기체는 항상 수평이다. "
            "바람·자세루프에서 나오는 롤/피치(0.1~13°)를 rotor_dynamics 의 rpm 지터와 **같은 자리**에 "
            "넣어야 한다(같은 OU 과정, 같은 시드). 그러면 «나딧» 이 하나의 각도가 아니라 분포가 된다.",
            "④ [기하] **동체 진동/상하 흔들림**을 슬로타임 위상에 더한다(Costa 식 47 형태). "
            "나딧에서는 이것이 유일하게 100 % 시선방향인 운동이다.",
            "⑤ [서술] 리포트의 «머리 위 드론은 안 보인다» 는 **모노스태틱·스칼라·가림무시·"
            "완전수평·강체날개** 라는 다섯 이상화의 결론이라고 조건을 붙인다. "
            "우리 시스템은 바이스태틱이라 그 결론이 **적용되지 않는다**.",
        ],
        "needs_gpu_ko": ["①(SBR 거리 사다리 el=−90)", "②(벡터 PO 승격 후 검증)"],
    }


def main() -> None:
    print("기하 대리모형 (CPU, GPU 미사용) …", flush=True)
    geo = run_geometry()
    ft0 = geo["kinematics"]["f_tip0_hz"]
    wnd = wind_tilt(geo["tilt_ladder"])
    bis = bistatic(ft0)
    doc = {
        "_meta": {
            "generator": "benchmark/nadir_realworld_mechanisms.py",
            "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "question_ko": ("«실측에서 나딧(직하방) 도플러가 남는다» 면 무엇이 만드나 — "
                            "우리 시뮬레이션에 빠진 것을 센다"),
            "gpu_ko": "GPU 를 쓰지 않았다. sbr_field 호출 0 회 — 평면패싯 PO 대리모형만 CPU.",
            "inherits": {
                "kinematics": "outputs/report07_three_engines.json _meta",
                "ledger_being_extended": "outputs/verify_nadir_flash.json C_D_geometry",
                "geometry_source": "src/drones.py DRONES['matrice4e'] (공식 제원)"},
            "proxy_caveat_ko": ("verify_nadir_flash.py 와 **같은** 평면패싯 PO 대리모형이다 — "
                                "재질·가림·다중반사·λ/12 격자 없음. 절대 레벨은 SBR 원장을 쓰고, "
                                "여기서는 **비(ratio)와 기전**만 읽는다."),
        },
        "A_tilt_and_range": geo,
        "C_hub_offset": hub_offset(),
        "D_wind_to_tilt": wnd,
        "E_bistatic_bisector": bis,
        "FGH_other_terms": other_terms(ft0),
        "P_prior_work": prior_work(),
        "Z_verdict": verdict(geo, wnd, bis),
    }
    json.dump(doc, open(OUT_J, "w"), ensure_ascii=False, indent=1)
    print(f"✅ {OUT_J}")
    g = geo["gate"]
    print(f"G0 게이트 max|Δ| = {g['max_abs_delta_db']} dB  pass={g['pass_']}")
    for k, v in geo["tilt_ladder"].items():
        print(f"  θ={k:>5} deg  ac/dc {v['ac_over_dc_db']:>8.2f} dB  "
              f"props {v['props_only_ac_over_dc_db']:>8.2f}  "
              f"pred fd {v['pred_peak_doppler_hz']:>7.1f} Hz  "
              f"PM/AM {v['pm_over_am_db']:>6.2f} dB")
    print("--- 가림(occlusion) ---")
    for k, v in geo["occlusion_test"].items():
        if k.startswith("_"):
            continue
        print(f"  {k:>18}  가림없음 {v['no_occlusion_ac_over_dc_db']:>8.2f} dB  →  "
              f"가림켬 {v['with_occlusion_ac_over_dc_db']:>8.2f} dB")


if __name__ == "__main__":
    main()
