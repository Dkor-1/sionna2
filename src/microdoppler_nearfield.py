# -*- coding: utf-8 -*-
"""
microdoppler_nearfield.py — **거리 의존** 마이크로도플러 (구면파 PO)
=====================================================================
질문: **"거리에 따라 마이크로 도플러 패턴이 망가지거나 달라지는가?"** (1 / 5 / 10 / 20 m)

기존 `microdoppler.py` 는 **완전 평면파**다 — 시선 단위벡터 û 하나만 받는다
(`rcs_po.po_field_dir`, `microdoppler_series`). 평면파 가정에서 거리는 **진폭을 상수배**할 뿐이라
스펙트로그램 **모양이 원리적으로 변하지 않는다**. 즉 옛 코드로는 이 질문에 답할 수 없다.

이 모듈은 그래서 **같은 점구름 위에서 파면 모델만 바꾼 A/B** 를 제공한다:

  * `WAVEFRONT="plane"`  : exp(+j2k·P·û)                      ← 기존과 동일 (기준군)
  * `WAVEFRONT="spherical"`: exp(−jk(r_t+r_r)) · (R_tR_r)/(r_t r_r)   ← 신규 (실험군)

점구름·재질가중·가림여부·회전 운동학이 **완전히 동일**하고 오직 파면만 다르므로,
두 팔의 차이는 **파면 곡률(근거리장) 효과 하나로 귀속된다.** 이것이 통제실험의 핵심이다.

---------------------------------------------------------------------------
왜 근거리장에서 패턴이 변하는가
---------------------------------------------------------------------------
평면파에서는 표면 모든 점이 **같은 시선방향**을 보고 **같은 감쇠**를 받는다.
구면파에서는 점마다 시선 û_i·거리 r_i 가 다르다. 전개하면 2차(프레넬) 위상항
    k·ρ²/(2R)      (ρ = 시선에 수직한 방향의 표면 오프셋)
이 살아난다. 이 항이 π/8 을 넘지 않을 조건이 정확히 **원거리장 판정 R ≥ 2D²/λ** 다.
그 아래에서는 블레이드가 시선에 수직으로 정렬돼도 전 스팬이 동시에 위상정합되지 못한다.

⚠ **f_tip 자체는 순수 운동학**(f_tip = 2·v_tip·cos(el)/λ)이라 거리에 무관하다.
   변하는 것은 플래시 **구조**지 도플러 확산 **폭**이 아니다. 이 구분이 이 실험의 판정선이다.

⚠ **설계 예측 하나가 측정에 반증됐다 (2026-07-28, 기록 보존)**
   최초 docstring 은 "근거리장에서 **플래시가 뭉개진다**" 고 단정했다. **데이터는 지지하지 않는다.**
   단일자세(az=0)만 보면 flash_contrast 가 오히려 **올라가고**(mavic4pro ∞→2 m: 10.16 → 12.83 dB),
   기종마다 부호가 달랐다(matrice4e 는 반대, s1000plus 는 비단조).
   자세 12점 평균으로 다시 재면 Δflash_contrast = **−1.32 ± 2.36 dB (R=1 m)**, +0.37 ± 0.25 dB (R=20 m)
   — **평균이 산포보다 작아 유의하지 않다.** "뭉개진다" 도 "뾰족해진다" 도 근거 없다.
   자세평균에서 **유의하게 살아남는 결론은 셋뿐**이다:
     (1) 패턴 상관이 R_ff 를 따라 떨어진다 (AC 0.334±0.096 @1 m -> 0.995±0.004 @20 m; 효과 >> 산포)
     (2) 도플러 폭은 사실상 불변 (자세평균 축소 <=7%, 비단조 = 지표 자체 산포 수준)
     (3) 레벨 편차는 방위평균에서 1/R 로 사라진다

---------------------------------------------------------------------------
σ_eq 의 정확한 의미 (⚠ 오독 금지)
---------------------------------------------------------------------------
근거리장에서 **RCS 는 정의되지 않는다**(σ 는 원거리장 평면파 입사 기준의 표적 고유값).
여기서 돌려주는 `sigma_eq` 는 그래서 **"구면파로 계산한 원거리장 등가 σ"** 라는 진단량이다:
기준거리 (R_t,R_r) 로 정규화해 두었으므로 R→∞ 에서 평면파 σ 로 **수렴한다**
(`verify_md_nearfield.py` 의 CONVERGE 게이트가 이를 강제한다).
절대 RCS 앵커로 인용하지 말 것 — 용도는 **평면파 대비 상대 편차**뿐이다.

---------------------------------------------------------------------------
회전 운동학 (평면파·구면파 공통, 정확)
---------------------------------------------------------------------------
로터 k 의 블레이드를 z축(허브축) 둘레로 θ 만큼 돌리는 것은, **안테나를 −θ 만큼 돌려**
허브 로컬 좌표에서 보는 것과 **엄밀히 등가**다 (평면파에서만 성립하는 근사가 아니다):

    |A − (Rz(θ)P_local + C)| = |Rz(−θ)(A − C) − P_local|

법선도 같이 돌아가므로 n̂·û 도 로컬에서 그대로 계산된다. 즉 **A′_k(θ) = Rz(−θ)(A − C_k)**
하나만 시간에 따라 움직이면 되고, 무거운 점구름은 한 번만 만들면 된다.

φ ∈ [0, period_deg) 를 `n_phase` 개로 잘라 복소장 테이블을 만들고 슬로타임으로 보간한다.

⚠ **period_deg 기본값은 360°(1회전)다 — 360/n_blades 가 아니다.**
   기존 `microdoppler.microdoppler_sbr` 는 "n-블레이드 프로펠러는 360/n 회전에 불변" 이라며
   period = 360/n 을 쓴다. **이 가정은 실제로 깨진다.** 측정(mavic4pro, λ/11 점구름):
   프로펠러 점구름을 180° 돌려 최근접대응시키면 p50 0.000 / p95 **1.23** / max **2.84 mm**
   어긋난다(메쉬 기하가 아니라 **삼각분할·바리센트릭 샘플링**이 2회 대칭이 아니다).
   3.5 GHz 에서 2.84 mm 는 λ/30 이고 왕복 위상 2k·d ≈ **23°** 라, 산란장은
   |E(θ+180°) − E(θ)|/|E| 가 **1.4~15.6%** 나 된다(θ=0/17/53/91° 측정).
   결과적으로 180° 주기 테이블은 로터 회전수의 **홀수 하모닉(60·(2m+1) Hz)** 을 통째로 버린다.
   ⚠ **크기 정정(2026-07-28 적대검증)**: 최초 판은 "AC 전력의 2.3% 가 사라진다" 고 적었으나
   2.3% 는 파형 불일치(1−corr²)이지 **전력 몫이 아니다** — 약 4× 과장이었다.
   위상테이블을 직접 FFT 해 잰 홀수 하모닉의 실제 AC 전력 몫은
   **0.600%**(평면파) / **0.495%**(구면, R=20 m) / **0.054%**(구면, R=1 m) 이고,
   최강 홀수 하모닉은 AC 첨두 대비 **−21.5 dB**(평면) ~ −33.1 dB(구면 R=1 m) 다.
   ⚠ 이 아티팩트는 **양 팔에 공통이 아니다**(11.6 dB 의 거리의존성) — 다만 R=1 m 의
   0.714 탈상관 중 1% 미만이라 결론을 바꾸지 않는다. 60·(2m+1) Hz 는 **진짜 단일블레이드/로터
   불균형 시그니처가 나타나는 자리**라, 1회전 테이블을 쓰는 이유는 크기가 아니라 **오염 위치**다.
   → 여기서는 **1회전 전체**를 테이블로 잡는다. 비용은 2배뿐이고 근사가 사라진다.
   (`period_deg=360.0/spec.prop_blades` 로 넘기면 옛 규약을 재현할 수 있다 — 비교용.)

---------------------------------------------------------------------------
한계 (정직하게)
---------------------------------------------------------------------------
* **가림(occlusion) 없음** — 두 팔 모두 순수 PO 다. 이는 결함이 아니라 **의도**다:
  가림을 넣으면 근거리장 효과와 가림 효과가 섞여 A/B 의 귀속이 깨진다.
  절대 레벨은 report07 기준 +4~5 dB 과대이지만, **두 팔에 동일하게** 걸리므로 차이는 상쇄된다.
* 편파 미보존(복소 스칼라 E, 스칼라 |Γ|) — 저장소 전체 규약과 동일.
* 다중반사 없음. 모서리/정점 회절 없음.
* 구면파 팔도 **입사 obliquity (n̂·û_i) 만** 쓴다(저장소 규약, rcs_sbr.py:319-322 와 동일).
"""
from __future__ import annotations

import numpy as np

from drones import build_frame, build_propeller, rotor_layout, drone_gamma_map
from rcs_po import mesh_to_points, C0

WAVEFRONTS = ("plane", "spherical")


# --------------------------------------------------------------------------- #
#  기하 헬퍼
# --------------------------------------------------------------------------- #
def look_unit(az_deg, el_deg):
    """표적중심 → 안테나 방향 단위벡터 û."""
    az, el = np.radians(float(az_deg)), np.radians(float(el_deg))
    return np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])


def antenna_pos(range_m, az_deg, el_deg, ctr=(0.0, 0.0, 0.0)):
    """표적중심에서 거리 range_m, 방위/고각 (az,el) 에 놓인 안테나 좌표."""
    return np.asarray(ctr, float) + float(range_m) * look_unit(az_deg, el_deg)


def _rz(theta_rad):
    c, s = np.cos(theta_rad), np.sin(theta_rad)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def farfield_range_m(extent_m, fc):
    """원거리장 판정거리 2D²/λ [m] (저장소 `radar_scene.farfield_distance` 와 동일 규약)."""
    return 2.0 * float(extent_m) ** 2 / (C0 / float(fc))


# --------------------------------------------------------------------------- #
#  코어 커널 — 한 점구름 + 안테나(들) → 복소 산란장 E
# --------------------------------------------------------------------------- #
def _field_plane(P, N, dA_w, k, u_t, u_s):
    """평면파 PO.  E = Σ (n̂·û_t)_+ · [n̂·û_s>0] · |Γ|ΔA · exp(jk(û_t+û_s)·P)

    모노스태틱(û_t=û_s=û)이면 exp(j2k P·û) 로 기존 `po_field_dir` 와 정확히 일치한다."""
    nt = N @ u_t                                     # (Np,)
    ns = N @ u_s
    ph = np.exp(1j * k * (P @ (u_t + u_s)))
    integ = np.where((nt > 0) & (ns > 0), nt, 0.0) * dA_w * ph
    return integ.sum()


def _field_spherical(P, N, dA_w, k, A_t, A_s, R_t, R_s):
    """구면파 PO (근거리장).

        E = Σ (n̂·û_ti)_+ · [n̂·û_si>0] · |Γ|ΔA · (R_t R_s)/(r_ti r_si)
                          · exp(−jk(r_ti + r_si − R_t − R_s))

    û_ti = (A_t − P_i)/r_ti  (점마다 다르다) — 이것이 평면파와의 유일한 차이다.
    (R_t R_s)/(r r) 정규화와 기준위상 (R_t+R_s) 차감 때문에 R→∞ 에서 `_field_plane` 로 수렴한다.
    """
    Dt = A_t[None, :] - P                            # (Np,3)
    rt = np.linalg.norm(Dt, axis=1)
    ut = Dt / rt[:, None]
    if A_s is A_t:
        Ds, rs, us = Dt, rt, ut
    else:
        Ds = A_s[None, :] - P
        rs = np.linalg.norm(Ds, axis=1)
        us = Ds / rs[:, None]
    nt = np.einsum("ij,ij->i", N, ut)
    ns = np.einsum("ij,ij->i", N, us)
    spread = (R_t * R_s) / (rt * rs)
    ph = np.exp(-1j * k * (rt + rs - R_t - R_s))
    integ = np.where((nt > 0) & (ns > 0), nt, 0.0) * dA_w * spread * ph
    return integ.sum()


# --------------------------------------------------------------------------- #
#  드론 1기 → 로터 위상 φ 에 대한 복소장 테이블
# --------------------------------------------------------------------------- #
def _nn_spacing(P, n_probe=4000, seed=0):
    """점구름의 **실측 최근접이웃 간격 중앙값**[m] — 요청한 λ/N 라벨이 참인지 확인용."""
    from scipy.spatial import cKDTree
    P = np.asarray(P, float)
    if len(P) < 4:
        return float("nan")
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(P), size=min(n_probe, len(P)), replace=False)
    d, _ = cKDTree(P).query(P[idx], k=2)
    return float(np.median(d[:, 1]))


def _build_clouds(spec, lam, frame_div, blade_div, blade_n):
    """프레임(월드좌표) · 프로펠러 **CW/CCW 두 벌**(허브 로컬좌표) 점구름을 한 번만 만든다.

    ⚠ 2026-07-28: 실물 멀티로터는 반대로 도는 로터에 **거울상 프롭**을 단다. `drones.build_drone`
      이 그렇게 바뀌었으므로 여기서도 로터 dir 에 맞춰 골라 써야 한다(안 그러면 이 모듈만
      전 로터가 같은 손잡이가 되어 저장소와 어긋난다).

    ⚠ **point_spacing 라벨 주의(적대검증 지적)**: `mesh_to_points` 는 삼각형당 최소 1점을 깔기
      때문에, 프로펠러 facet 이 이미 촘촘하면(중앙값 ~2.9 mm) 요청한 λ/N 이 **구속되지 않는다**
      — 실효 최근접간격은 ~λ/98 수준이고 λ/6~λ/24 구간에서 노브가 사실상 불활성이다.
      그래서 meta 에 'λ/11' 이라고만 적으면 거짓 라벨이다. 실측 간격을 함께 기록한다."""
    gm = drone_gamma_map(spec)
    Pf, Nf, dAf, wf = mesh_to_points(build_frame(spec), lam / frame_div, gamma=gm)
    Pp, Np_, dAp, wp = mesh_to_points(build_propeller(spec, n=blade_n), lam / blade_div, gamma=gm)
    Pm, Nm, dAm, wm = mesh_to_points(build_propeller(spec, n=blade_n, mirror=True),
                                     lam / blade_div, gamma=gm)
    return (Pf, Nf, dAf * wf), (Pp, Np_, dAp * wp), (Pm, Nm, dAm * wm)


def phase_table(spec, fc, range_m, az_deg=0.0, el_deg=15.0, *,
                wavefront="spherical", n_phase=480, period_deg=360.0,
                frame_div=6.0, blade_div=11.0, blade_n=26,
                rx_range_m=None, rx_az_deg=None, rx_el_deg=None):
    """로터 위상 φ∈[0, period_deg) 격자 위의 복소 산란장 테이블 E(φ) 를 만든다.

    range_m/az/el      : **TX(=조명) 안테나** 위치(표적중심 기준 구면좌표)
    rx_* (선택)        : **RX 안테나** 위치. 생략하면 모노스태틱(TX=RX).
    wavefront          : "plane" | "spherical"
    period_deg         : 기본 360°(1회전, 근사 없음). 360/n_blades 를 넘기면 옛 규약(근사).
    반환 (phis_deg, E_table[complex], info)
    """
    if wavefront not in WAVEFRONTS:
        raise ValueError(f"wavefront must be one of {WAVEFRONTS}, got {wavefront!r}")
    # ⚠ 반응장(reactive near-field) 가드 — 이 PO 는 방사항만 쓴다(1/(kr) 항 없음).
    #   안테나가 표적 표면에 너무 가까우면 그 근사가 깨진다. s1000plus 는 R=1 m 에서
    #   최근접 표면이 4.78λ 밖에 안 돼 버린 항이 점당 3.3% 다 — 경고를 남긴다.
    _lam_guard = C0 / float(fc)
    if float(range_m) < 12.0 * _lam_guard:
        import warnings as _w
        _w.warn(f"microdoppler_nearfield: range {range_m:.3g} m < 12λ ({12*_lam_guard:.3g} m) — "
                f"반응장 항 1/(kr) 이 무시 못 할 수 있다(방사항만 모델링). 결과를 그렇게 읽을 것.",
                RuntimeWarning, stacklevel=2)
    lam = C0 / float(fc)
    k = 2.0 * np.pi / lam

    A_t = antenna_pos(range_m, az_deg, el_deg)
    R_t = float(np.linalg.norm(A_t))
    if rx_range_m is None:
        A_s, R_s = A_t, R_t
        bistatic = False
    else:
        A_s = antenna_pos(rx_range_m,
                          az_deg if rx_az_deg is None else rx_az_deg,
                          el_deg if rx_el_deg is None else rx_el_deg)
        R_s = float(np.linalg.norm(A_s))
        bistatic = True
    u_t, u_s = A_t / R_t, A_s / R_s

    (Pf, Nf, wf), (Pp, Np_, wp), (Pm, Nm_, wm) = _build_clouds(
        spec, lam, frame_div, blade_div, blade_n)

    # --- 프레임(비회전): φ 무관 상수항 ---
    if wavefront == "plane":
        E_frame = _field_plane(Pf, Nf, wf, k, u_t, u_s)
    else:
        E_frame = _field_spherical(Pf, Nf, wf, k, A_t, A_s, R_t, R_s)

    # --- 로터: φ 격자 ---
    rl = rotor_layout(spec)
    period = float(period_deg)
    phis = np.linspace(0.0, period, int(n_phase), endpoint=False)
    tab = np.full(int(n_phase), E_frame, dtype=complex)

    for rot in rl:
        C = np.asarray(rot["center"], float)
        base = np.radians(float(rot["base_ang"]))
        d = float(rot["dir"])
        Pb, Nb, wb = (Pp, Np_, wp) if d > 0 else (Pm, Nm_, wm)   # 반대회전 로터 = 거울상 프롭
        # 안테나를 허브 로컬로 옮기고 −θ 회전 (블레이드 회전과 엄밀히 등가)
        At_c, As_c = A_t - C, A_s - C
        for i, ph in enumerate(phis):
            th = base + d * np.radians(ph)
            Rm = _rz(-th)
            At_l = Rm @ At_c
            if wavefront == "plane":
                # 평면파에선 위치가 아니라 방향만 회전하면 된다 (+ 허브 위상 오프셋)
                ut_l, us_l = Rm @ u_t, Rm @ u_s
                Eb = _field_plane(Pb, Nb, wb, k, ut_l, us_l) * np.exp(1j * k * (C @ (u_t + u_s)))
            else:
                As_l = At_l if not bistatic else Rm @ As_c
                Eb = _field_spherical(Pb, Nb, wb, k, At_l, As_l, R_t, R_s)
            tab[i] += Eb

    info = dict(fc=float(fc), lam=lam, range_m=float(range_m), az_deg=float(az_deg),
                el_deg=float(el_deg), wavefront=wavefront, n_phase=int(n_phase),
                period_deg=period, bistatic=bool(bistatic),
                R_t=R_t, R_s=R_s, n_frame_pts=int(len(wf)), n_blade_pts=int(len(wp)),
                n_rotors=len(rl), frame_div=float(frame_div), blade_div=float(blade_div),
                blade_spacing_requested_m=float(lam / blade_div),
                blade_spacing_actual_median_m=float(_nn_spacing(Pp)),
                E_frame_abs=float(abs(E_frame)))
    return phis, tab, info


def series_from_table(phis_deg, tab, spec, rpm=None, prf=20000.0, n_t=6144):
    """φ 테이블 → 슬로타임 복소장 E(t). 반환 (t[s], E, info_add)."""
    if rpm is None:
        rpm = float(getattr(spec, "hover_rpm", 6000.0))
    period = float(phis_deg[-1] - phis_deg[0]) + float(phis_deg[1] - phis_deg[0])
    n_phase = len(tab)
    t = np.arange(int(n_t)) / float(prf)
    phi_t = (360.0 * rpm / 60.0) * t                       # [deg]
    idx = np.mod(phi_t / period * n_phase, n_phase)
    i0 = np.floor(idx).astype(int) % n_phase
    i1 = (i0 + 1) % n_phase
    f = idx - np.floor(idx)
    E = tab[i0] * (1.0 - f) + tab[i1] * f
    return t, E, dict(rpm=float(rpm), prf=float(prf), n_t=int(n_t))


def microdoppler_nf(spec, fc=3.5e9, range_m=10.0, az_deg=0.0, el_deg=15.0, *,
                    wavefront="spherical", rpm=None, prf=20000.0, n_t=6144,
                    n_phase=480, period_deg=360.0, frame_div=6.0, blade_div=11.0, blade_n=26,
                    rx_range_m=None, rx_az_deg=None, rx_el_deg=None):
    """한 방에: (t, E, info). `microdoppler.microdoppler_series` 의 거리인식 판."""
    phis, tab, info = phase_table(spec, fc, range_m, az_deg, el_deg,
                                  wavefront=wavefront, n_phase=n_phase, period_deg=period_deg,
                                  frame_div=frame_div, blade_div=blade_div, blade_n=blade_n,
                                  rx_range_m=rx_range_m, rx_az_deg=rx_az_deg,
                                  rx_el_deg=rx_el_deg)
    t, E, add = series_from_table(phis, tab, spec, rpm=rpm, prf=prf, n_t=n_t)
    info.update(add)
    omega = 2 * np.pi * info["rpm"] / 60.0
    prop_R = spec.prop_dia_mm / 1000.0 / 2.0
    info.update(v_tip=omega * prop_R,
                f_tip=2.0 * (omega * prop_R) / info["lam"] * np.cos(np.radians(el_deg)),
                flash_hz=spec.prop_blades * info["rpm"] / 60.0,
                sigma_eq_mean_m2=float((4 * np.pi / info["lam"] ** 2) * np.mean(np.abs(E) ** 2)))
    return t, E, info


# --------------------------------------------------------------------------- #
#  링크버짓 — 거리에 따른 SNR (arm ① 이 쓰는 부분)
# --------------------------------------------------------------------------- #
#  ⚠ 아래 파라미터는 **선언값**이다(챔버급 저출력). 출처문서 없음 — JSON meta 에 provenance 로 기록.
DECLARED_EIRP_DBM = 12.0        # 챔버 실험 EIRP (benchmark/run_min_cell.EIRP_DBM 규약)
DECLARED_RX_GAIN_DBI = 10.0
DECLARED_NF_DB = 5.0
DECLARED_B_HZ = 100e6           # 수신 순시대역 (5G NR 100 MHz)
K_BOLTZ, T0 = 1.380649e-23, 290.0


def echo_over_noise_db(sigma_eq_m2, range_m, fc, *, eirp_dbm=DECLARED_EIRP_DBM,
                       rx_gain_dbi=DECLARED_RX_GAIN_DBI, nf_db=DECLARED_NF_DB,
                       b_hz=DECLARED_B_HZ, rx_range_m=None):
    """슬로타임 **샘플당** 에코-대-잡음비 [dB].

        P_echo = EIRP·G_rx·λ²·σ / ((4π)³·R_t²·R_r²)
        P_n    = k·T0·F·B
    """
    lam = C0 / float(fc)
    eirp_w = 10.0 ** (float(eirp_dbm) / 10.0) * 1e-3
    g = 10.0 ** (float(rx_gain_dbi) / 10.0)
    f = 10.0 ** (float(nf_db) / 10.0)
    Rt = float(range_m)
    Rr = Rt if rx_range_m is None else float(rx_range_m)
    p_echo = eirp_w * g * lam ** 2 * np.asarray(sigma_eq_m2, float) / ((4 * np.pi) ** 3 * Rt ** 2 * Rr ** 2)
    p_n = K_BOLTZ * T0 * f * float(b_hz)
    return 10.0 * np.log10(np.maximum(p_echo / p_n, 1e-300))


def ac_snr_db(E, snr_total_db):
    """⭐ **블레이드선(AC)의 실효 SNR** [dB] = 총전력 SNR − DC/AC 비.

    ⚠ 왜 필요한가(2026-07-28 적대검증이 잡아낸 결함): `echo_over_noise_db`/`add_noise` 의
      SNR 은 **총전력 기준**인데, 마이크로도플러 시계열은 비회전 몸체가 만드는 **0-도플러 DC 가
      지배**한다(측정 dc_ac_db = 33~37 dB). 그래서 총전력 SNR 은 "블레이드선이 보이는가" 의
      지표로는 **33~37 dB 낙관적**이고, 그 오프셋은 거리에 따라 4.15 dB 흔들려 **상쇄되지도 않는다**.
      예: 총전력 SNR +7.5 dB @R=10 m 인데 실제 AC SNR 은 **−29.2 dB**(그래서 fd_edge 가 NaN 이다).
      → 검출성을 논할 때는 **반드시 이 값**을 쓸 것."""
    return float(snr_total_db) - float(md_metrics(E, 1.0)["dc_ac_db"])


def add_noise(E, snr_db, rng):
    """|E|² 의 **시간평균**이 snr_db 가 되도록 복소 백색잡음을 더한다. 반환 (E_noisy, sigma_n).

    ⚠ snr_db 는 **총전력 기준**이다(몸체 DC 포함). 블레이드선 검출성은 `ac_snr_db()` 를 쓸 것."""
    p_sig = float(np.mean(np.abs(E) ** 2))
    p_n = p_sig / (10.0 ** (float(snr_db) / 10.0))
    s = np.sqrt(p_n / 2.0)
    n = rng.normal(0.0, s, size=E.shape) + 1j * rng.normal(0.0, s, size=E.shape)
    return E + n, float(np.sqrt(p_n))


# --------------------------------------------------------------------------- #
#  스펙트로그램 지표 — verify 와 experiment 가 **같은 구현**을 쓴다(재구현 금지)
# --------------------------------------------------------------------------- #
def md_metrics(E, prf, *, flash_hz=None, f_tip=None, nperseg=256, edge_drop_db=20.0):
    """마이크로도플러 시계열 → 패턴 지표 dict.

    dc_ac_db        : 20log10(|평균 E| / std(E))  — 저장소 기존 정의(report1.json sbr.ratio_db)
    fd_edge_hz      : DC 제거 후 도플러 주변분포가 최대 대비 −edge_drop_db 로 떨어지는 **바깥쪽** 주파수.
                      f_tip 의 관측판. **운동학량이라 거리에 불변**이어야 한다(판정선).
                      ⚠ **잡음 견고성**: 잡음이 우세하면 −20 dB 문턱을 잡음 스파이크가 만족해
                      나이퀴스트 가장자리(PRF/2)를 반환하는 결함이 있었다(2026-07-28 발견·수정).
                      이제 스펙트럼 중앙값을 잡음바닥으로 추정해 **빼고** 문턱을 적용하며,
                      잔여 첨두가 잡음바닥의 3배에 못 미치면 **NaN**(= 블레이드선 관측 불가)을 돌려준다.
                      NaN 은 결측이 아니라 "묻혔다" 는 결과다.
                      ⚠⚠ **분해능 양자(2026-07-28 적대검증)**: 이 지표는 도플러축의 **균일 재척도**는
                      0.1% 로 추적하지만(rpm 오차 진단엔 유효), **형상이 밀어내는 가장자리 이동**은
                      **flash_hz 통짜 계단**으로만 움직인다(측정: 각 셀이 전 거리에서 많아야 3개
                      값만 갖고 계단 간격이 정확히 flash_hz). flash_hz 는 f_tip 의 **7.4~18.5%** 라,
                      "근거리장 도플러 폭 축소 ≤7%" 같은 주장은 **이 계측기 자신의 바닥 아래**다.
                      방어 가능한 진술은 "도플러 폭이 flash_hz 한 계단 이상 움직이지 않는다" 까지.
    flash_contrast_db: 시간 주변분포(AC)의 최대/중앙값 비 [dB]. **플래시 선명도** — 근거리장에서
                      뭉개지면 여기가 떨어진다.
    harmonic_frac   : 플래시 하모닉(±m·flash_hz, m=1..M)에 실린 AC 에너지 비율.
    ac_energy       : Σ|E−mean|²  (레벨 비교용, 정규화 안 함)
    """
    E = np.asarray(E)
    ac = E - E.mean()
    p_ac = float(np.sum(np.abs(ac) ** 2))
    out = dict(
        dc_ac_db=float(20 * np.log10(max(abs(E.mean()), 1e-300) / max(np.std(E), 1e-300))),
        ac_energy=p_ac,
        mean_sigma_proxy=float(np.mean(np.abs(E) ** 2)),
    )
    # 양측 도플러 스펙트럼(정적 성분 제거)
    n = len(ac)
    win = np.hanning(n)
    S = np.abs(np.fft.fftshift(np.fft.fft(ac * win))) ** 2
    f = np.fft.fftshift(np.fft.fftfreq(n, d=1.0 / float(prf)))
    if S.max() <= 0:
        out.update(fd_edge_hz=float("nan"), flash_contrast_db=0.0, harmonic_frac=0.0,
                   spec_peak_over_floor_db=float("-inf"))
        return out
    # ── 잡음 견고화 ──
    # ① 주기도(periodogram)를 W빈 이동평균으로 평활한다. 평활 안 하면 지수분포 잡음의
    #    **최대 순서통계량**이 중앙값보다 ~11 dB 높아(N=6144 에서 ln N+γ ≈ 9.3μ / 0.693μ)
    #    −20 dB 문턱을 잡음 혼자 만족해 버린다(실측: 순수잡음에서 peak/floor 11.0~11.4 dB).
    #    W=33 평활이면 잡음의 max/median 이 ~2 dB 로 줄어 문턱이 의미를 갖는다.
    W = 33
    ker = np.ones(W) / W
    S_sm = np.convolve(S, ker, mode="same")
    floor = float(np.median(S_sm))
    pk = float(S_sm.max())
    out["spec_peak_over_floor_db"] = float(10 * np.log10(max(pk, 1e-300) / max(floor, 1e-300)))
    # ② 가장자리는 "첨두 대비 −edge_drop_db" **그리고** "잡음바닥 대비 +6 dB" 를 **동시에** 만족해야 한다.
    MARGIN_DB = 6.0
    if out["spec_peak_over_floor_db"] < 10.0:   # 블레이드선이 잡음에 묻혔다 → 결과가 NaN 이다
        out["fd_edge_hz"] = float("nan")
    else:
        thr = max(pk * 10 ** (-abs(edge_drop_db) / 10.0), floor * 10 ** (MARGIN_DB / 10.0))
        above = np.where(S_sm >= thr)[0]
        out["fd_edge_hz"] = (float(max(abs(f[above[0]]), abs(f[above[-1]])))
                             if len(above) else float("nan"))

    # 시간축 플래시 선명도: |E_ac| 포락선의 최대/중앙값
    env = np.abs(ac)
    out["flash_contrast_db"] = float(20 * np.log10(max(env.max(), 1e-300) /
                                                  max(np.median(env), 1e-300)))
    # 하모닉 집중도
    if flash_hz:
        df = float(prf) / n
        tol = max(2.0 * df, 0.02 * float(flash_hz))
        m_max = int(np.floor((float(prf) / 2.0) / float(flash_hz)))
        mask = np.zeros_like(S, dtype=bool)
        for m in range(1, max(1, m_max) + 1):
            mask |= np.abs(np.abs(f) - m * float(flash_hz)) <= tol
        out["harmonic_frac"] = float(S[mask].sum() / S.sum()) if S.sum() > 0 else 0.0
    else:
        out["harmonic_frac"] = float("nan")
    return out


def ac_correlation(E_a, E_b):
    """두 시계열의 **AC 성분** 정규화 복소상관 |<a,b>|/(|a||b|). 1.0 = 패턴 동일."""
    a = np.asarray(E_a) - np.mean(E_a)
    b = np.asarray(E_b) - np.mean(E_b)
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na <= 0 or nb <= 0:
        return 0.0
    return float(np.abs(np.vdot(a, b)) / (na * nb))


def spectrogram_corr(E_a, E_b, prf, nperseg=256):
    """|STFT| 스펙트로그램(선형) 2D 정규화 상관 — '패턴이 같은가' 의 그림 대응 지표."""
    from microdoppler import spectrogram
    _, _, Sa = spectrogram(E_a, prf, nperseg=nperseg)
    _, _, Sb = spectrogram(E_b, prf, nperseg=nperseg)
    a = 10 ** (np.asarray(Sa) / 20.0)          # dB → 선형 크기
    b = 10 ** (np.asarray(Sb) / 20.0)
    a = (a - a.mean()).ravel(); b = (b - b.mean()).ravel()
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return float(np.dot(a, b) / (na * nb)) if na > 0 and nb > 0 else 0.0


if __name__ == "__main__":
    import sys
    from drones import DRONES
    from radar_scene import target_extent
    key = sys.argv[1] if len(sys.argv) > 1 else "mavic4pro"
    spec = DRONES[key]
    fc = 3.5e9
    rff = farfield_range_m(target_extent(key), fc)
    print(f"{key}  R_ff(2D²/λ) @3.5GHz = {rff:.2f} m")
    for R in (1.0, 5.0, 10.0, 20.0, 1000.0):
        _, Ep, ip = microdoppler_nf(spec, fc, R, wavefront="plane", n_phase=64, n_t=2048)
        _, Es, isp = microdoppler_nf(spec, fc, R, wavefront="spherical", n_phase=64, n_t=2048)
        sp = 10 * np.log10(ip["sigma_eq_mean_m2"]); ss = 10 * np.log10(isp["sigma_eq_mean_m2"])
        cc = np.abs(np.vdot(Ep - Ep.mean(), Es - Es.mean())) / (
             np.linalg.norm(Ep - Ep.mean()) * np.linalg.norm(Es - Es.mean()))
        print(f"  R={R:7.1f} m ({'far ' if R >= rff else 'NEAR'})  "
              f"sigma_eq plane={sp:7.2f}  sph={ss:7.2f} dBsm   AC-corr={cc:.4f}")
