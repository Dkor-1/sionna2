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
#  링크버짓 — 거리에 따른 SNR
# --------------------------------------------------------------------------- #
#  ⚠ 아래 파라미터는 **선언값**이다(챔버급 저출력). 출처문서 없음 — JSON meta 에 provenance 로 기록.
DECLARED_EIRP_DBM = 12.0        # 챔버 실험 EIRP (benchmark/run_min_cell.EIRP_DBM 규약)
DECLARED_RX_GAIN_DBI = 10.0
DECLARED_NF_DB = 5.0
DECLARED_B_HZ = 100e6           # 수신 순시대역 (5G NR 100 MHz)
DECLARED_PRF_HZ = 20000.0       # 슬로타임 표본율(= PRI 반복률). experiment_md_range.PRF 와 같은 값
K_BOLTZ, T0 = 1.380649e-23, 290.0

# --------------------------------------------------------------------------- #
#  ⭐⭐ SNR 규약 v2 (2026-08-10) — 사다리 하나, 이름 다섯. 「SNR」 이라는 맨 이름 금지
# --------------------------------------------------------------------------- #
#  왜 규약이 필요했나 (2026-08-10 적대검증이 잡은 결함 둘):
#    ① 저장소에 SNR 기준이 **두 개** 있었다. `add_noise()` 는 **총전력**(몸체 DC 포함),
#       `md_classify_dataset.cmd_build` 는 **AC 만**(블레이드선). 둘은 기체별 17.3~37.2 dB
#       어긋나는데 같은 표에 나란히 놓여 있었다. → 이제 두 값을 **항상 병기**하고,
#       변환은 `dc_ac_offset_db()` 하나로만 한다.
#    ② **정합필터 이득 G_mf = 10log10(B/PRF) = 37 dB 가 통째로 빠져 있었다.**
#       `echo_over_noise_db()` 는 잡음을 kT0F·B (B = 100 MHz) 로 세는데, 그 값을 우리는
#       **슬로타임 표본 E[m] 의 SNR** 로 썼다. E[m] 은 PRI 하나를 기준신호와 상관해 나온
#       **정합필터 출력**이라 시간·대역폭 곱만큼 이득이 붙는다. → 거리 링크버짓이 37 dB
#       비관적이었다. `capture="full_waveform"` 이 그 이득을 붙인다.
#
#  사다리 (이름 → 정의):
#    ① snr_band_db     = P_echo / (k·T0·F·B)         정합필터 **전**, 수신 표본당
#    ② g_mf_db         = 10log10(B / PRF)            PRI 하나 상관의 처리이득 (풀 캡처에서만)
#    ③ snr_slow_db     = ① + ②                      슬로타임 표본 E[m] 의 **총전력** SNR
#    ③′snr_slow_ac_db  = ③ − dc_ac_off_db           ⭐**정본**. 블레이드(AC)선 SNR
#    ④ g_stft_db       = 10log10(N_seg) + L_win      STFT **한 조각**의 코히어런트 이득
#    ⑤ snr_map_ac_db   = ③′ + ④                     맵 위 블레이드선 첨두 SNR
#
#  ⚠⚠ **37 dB 짜리 양이 셋 있고 서로 다르다. 절대 뭉뚱그리지 마라**:
#     · ② 정합필터 이득(빠른시간, PRI 안)        = 10log10(1e8/2e4)  = 36.99 dB
#     · CPI 전체 슬로타임 코히어런트 적분(5000 표본) = 10log10(5000)  = 36.99 dB  ← 우연히 비슷
#     · ④ STFT 한 조각(70 표본·Hann)에서 실제로 얻는 이득          = 16.69 dB
#     맵에서 눈으로 보는 이득은 ④ 뿐이다. ② 는 «슬로타임 표본을 만드는 값», CPI 이득은
#     «전창 FFT 특징(분류기)이 얻는 값». 세 자리가 다르므로 세 이름을 따로 쓴다.
SNR_CONVENTION = "v2_2026-08"          # 원장 meta 에 그대로 박는 문자열
CANONICAL_SNR_KEY = "snr_slow_ac_db"   # 검출성 주장에 쓰는 정본 눈금

#: 창의 코히어런트 이득 손실 L_win = 10log10(|Σw|²/(N·Σw²)) [dB] — Braun(KIT 2014) 식 (3.77)
WINDOW_COH_LOSS_DB = {"boxcar": 0.0, "rect": 0.0, "hann": -1.76,
                      "hamming": -1.35, "blackman": -2.37}

#: 원장(`outputs/snr_convention.json`)이 그대로 싣는 자기기술
SNR_RUNGS = [
    dict(id="snr_band_db", formula="P_echo / (k*T0*F*B)",
         ref="pre-matched-filter, per Rx sample", condition="always"),
    dict(id="g_mf_db", formula="10*log10(B/PRF)",
         ref="fast-time matched-filter (one PRI) processing gain",
         condition="capture=full_waveform only; 0 dB for always_on_pilot"),
    dict(id="snr_slow_db", formula="snr_band_db + g_mf_db",
         ref="slow-time sample E[m], TOTAL power (body DC included)"),
    dict(id="snr_slow_ac_db", formula="snr_slow_db - dc_ac_off_db",
         ref="slow-time sample, AC (blade line) only", canonical=True),
    dict(id="g_stft_db", formula="10*log10(nperseg) + L_win",
         ref="coherent gain of ONE STFT frame (NOT the whole CPI)"),
    dict(id="snr_map_ac_db", formula="snr_slow_ac_db + g_stft_db",
         ref="peak SNR of the blade line on the spectrogram"),
]

# --------------------------------------------------------------------------- #
#  ⚠ 사다리에 **없는** 제3의 눈금 — 「에코 첨두 기준 SNR」 (2026-08-11 정리)
# --------------------------------------------------------------------------- #
#  저장소에 SNR 눈금이 ③(총전력)·③′(AC) 둘만 있는 게 아니었다. **셋째**가 있다:
#
#      src/radar_process.py:57-59   make_echo(..., snr_db)
#      src/passive_process.py:84-86 make_cpi(..., snr_db, abs_noise=False)
#
#  둘 다 잡음전력을 **에코의 첨두 표본 전력**에 건다 (x = 표적 에코, 잡음·DPI·클러터 전):
#
#      σ_n² = max_n |x[n]|² · 10^(−snr_db/10)
#   ⇒  snr_peak_pre_mf_db ≜ 10log10( max_n|x[n]|² / σ_n² ) = snr_db  (정의상 항등)
#
#  사다리 ① 은 **평균**전력 기준이므로 둘의 차이는 그 기록의 PAPR 이다:
#
#      snr_peak_pre_mf_db = (평균전력 기준 SNR) + PAPR_db,
#      PAPR_db = 10log10( max_n|x[n]|² / mean_n|x[n]|² )
#
#  ⛔ **사다리 rung 으로 승격하지 않는다 — 「폐기 예정」으로만 적는다.** 근거 다섯,
#     전부 측정(`benchmark/verify_snr_convention.py` 게이트 SC7):
#   1) 절대 잡음바닥이 없다. ① 은 kT0F·B 라는 물리 잡음에 걸리지만 이 눈금은 **에코 자신**에
#      걸린다. make_echo 에서 전압이득 α 가 에코와 잡음에 똑같이 곱해지므로 **거리 R 과 RCS σ
#      가 상쇄된다** — σ 를 40 dB 바꿔도 정규화 거리프로파일의 상대편차가 3.3e−16(부동소수
#      반올림)이다(SC7-P3). 즉 이 눈금에는 탐지성 정보가 0 이다. 「멀면 어려워진다」를 못 그린다.
#   2) 오프셋 PAPR 이 상수가 아니다. 상시 기준신호 3종에서 26.29 / 14.38 / 16.10 dB
#      (**11.91 dB 벌어진다**). 점유모드마다 다르고(WiFi G1 26.29 → G3 18.29 dB),
#      파형 시드마다 p-p 최대 1.01 dB, 기록 길이에 따라서도 움직인다(상시 5G 를 1/8·1/4·1/2·1
#      로 잘라 재면 11.39 / 10.77 / 13.09 / 16.10 dB — **단조도 아니다**).
#      ⇒ 「세 표준에 같은 snr_db 를 줬으니 공정하다」가 **거짓**이다.
#   3) 정합필터 뒤에서도 안 맞는다. 같은 snr_db=20 을 주고 잰 MF 출력 첨두/바닥이
#      WiFi 28.78 · LTE 22.03 · 5G 20.26 dB — **8.52 dB** 벌어진다(SC7-P6).
#   4) passive 쪽은 SINR 이 아니다. make_cpi 의 첨두는 **표적 에코만** 보고 DPI·클러터를 빼고
#      잰다. dpi_amp=55 를 켜도 잡음은 그대로라, 「SNR 12 dB」 라벨이 붙은 감시신호의 실제
#      평균/잡음은 **31.23 dB** 다(상시 5G 기준신호·M=8·클러터 1탭).
#   5) 헤드라인 경로가 안 쓴다 — `live_use` 참조. 그래서 «고칠 것»이 아니라 «폐기»다.
#: 원장(`outputs/snr_convention.json`)의 `non_ladder_conventions` 가 그대로 싣는 자기기술
NON_LADDER_CONVENTIONS = [
    dict(
        id="snr_peak_pre_mf_db",
        status="deprecated",
        label="echo-peak-referenced SNR (NOT on the v2 ladder)",
        formula="sigma_n^2 = max_n|x[n]|^2 * 10^(-snr_db/10)  =>  "
                "snr_peak_pre_mf_db = 10log10(max_n|x[n]|^2 / sigma_n^2) == snr_db",
        ref="peak sample of the TARGET ECHO ONLY, before matched filtering; the noise floor is "
            "defined by the echo itself, not by k*T0*F*B",
        where=["src/radar_process.py:57-59  make_echo(..., snr_db)",
               "src/passive_process.py:84-86  make_cpi(..., snr_db, abs_noise=False)"],
        to_ladder=("snr_peak_pre_mf_db - papr_db(echo record) = mean-power SNR per Rx sample "
                   "(the FORM of rung 1, never its VALUE - the floor is fictitious). "
                   "Then + g_mf_db -> snr_slow_db, - dc_ac_off_db -> snr_slow_ac_db."),
        needs_to_convert=["papr_db of the echo record (waveform-, occupancy-, seed- and "
                          "record-length dependent; measured in gate SC7)",
                          "P_echo and k*T0*F*B, to reach ANY absolute rung - the peak convention "
                          "cancels range and RCS entirely"],
        why_not_a_rung=[
            "no absolute noise floor: alpha multiplies echo AND noise, so R and sigma cancel "
            "(gate SC7-P3: normalized range profile agrees to 3.3e-16 for sigma 40 dB apart)",
            "the offset to rung 1 is PAPR, which is not a constant: 11.91 dB spread across the "
            "three always-on standards, and occupancy-, seed- and record-length dependent",
            "after the matched filter the three standards still differ by 8.52 dB at the same "
            "requested snr_db (gate SC7-P6)",
            "in make_cpi the peak excludes DPI and clutter, so it is not an SINR",
        ],
        live_use=("figure/demo only. Every production make_cpi call site passes abs_noise=True "
                  "(noise supplied absolutely), so snr_db is a dead argument there - gate SC7-P5 "
                  "proves it bit-identically. The only abs_noise=False caller is the "
                  "passive_process.py __main__ demo (src/viz_bistatic.py:95 legacy_cpi wraps it but "
                  "is never called). radar_process.make_echo is reached only from src/viz_radar.py, "
                  "src/viz_occupancy.py, src/viz_animations.py and its own __main__ demo; those "
                  "figures/GIFs are not embedded in any reports/*.ipynb of the current set."),
        disposition="do not promote, do not extend; migrate any new use to snr_slow_ac_db",
    ),
]


def papr_db(x):
    """PAPR(첨두 대 평균 전력비) [dB] = 10log10( max|x|² / mean|x|² ).

    ⭐제3규약(첨두기준 SNR) ↔ 사다리(평균전력 기준)의 **변환 오프셋**이 정확히 이 값이다.
    상수가 아니다 — 파형·점유모드·시드·기록길이에 따라 변한다(`NON_LADDER_CONVENTIONS`)."""
    x = np.asarray(x)
    pk = float(np.max(np.abs(x)) ** 2)
    av = float(np.mean(np.abs(x) ** 2))
    return float(10.0 * np.log10(max(pk, 1e-300) / max(av, 1e-300)))


def peak_ref_snr_to_mean_db(snr_peak_db, papr_of_echo_db):
    """첨두기준 SNR → **평균전력 기준** SNR [dB] (같은 잡음전력에서).

        snr_mean = snr_peak − PAPR

    ⚠ 이것은 rung ① 의 **형식**이지 값이 아니다. 첨두규약의 잡음바닥은 kT0F·B 가 아니라
    에코 자신이라, 절대 사다리로 올리려면 P_echo 와 kT0F·B 를 따로 알아야 한다."""
    return float(snr_peak_db) - float(papr_of_echo_db)


def window_coh_loss_db(window="hann", n=None):
    """창 코히어런트 이득 손실 L_win [dB] (≤ 0). `n` 을 주면 그 길이에서 정확히 계산한다.

    L_win = 10log10( |Σ w|² / (N · Σ w²) ).  N→∞ 극한이 `WINDOW_COH_LOSS_DB` 표다
    (Hann −1.76 dB). 유한 N 은 조금 다르다 — 예: np.hanning(70) 은 −1.79 dB.
    기본(표) 을 쓰는 이유는 원장·설계서가 표 값으로 적혀 있어서다."""
    key = str(window).lower()
    if n is not None and int(n) > 1:
        f = {"hann": np.hanning, "hamming": np.hamming, "blackman": np.blackman,
             "boxcar": np.ones, "rect": np.ones}.get(key)
        if f is not None:
            w = np.asarray(f(int(n)), float)
            num = float(np.sum(w)) ** 2
            den = float(int(n)) * float(np.sum(w ** 2))
            return float(10.0 * np.log10(max(num, 1e-300) / max(den, 1e-300)))
    return float(WINDOW_COH_LOSS_DB.get(key, 0.0))


def matched_filter_gain_db(b_hz=DECLARED_B_HZ, prf=DECLARED_PRF_HZ, *,
                           capture="full_waveform"):
    """⭐ 정합필터(빠른시간) 처리이득 G_mf = 10log10(B / PRF) [dB].

    슬로타임 표본 E[m] 은 «PRI 한 개 분량(1/PRF 초)의 대역 B 신호를 기준신호와 상관» 해서
    나온다. 시간·대역폭 곱 B·T_pri = B/PRF 만큼 이득이 붙는다(이상적 정합필터).

    ⭐ **같은 말을 잡음 쪽에서 쓰면**: 잡음 대역이 B 가 아니라 PRF 다 —

            P_echo / (k·T0·F·B) · (B/PRF)  =  P_echo / (k·T0·F·PRF)
            즉   k·T0·F·B / (B/PRF)  =  k·T0·F·PRF

      두 표현은 **정확히 같다**. 그래서 사다리는 ①+② 로도, B_eff = PRF 로도 쓸 수 있다.

    ⚠ 전제: **풀 웨이브폼 캡처**. PRF 19.7~20 kHz 로 슬로타임을 뽑으려면 매 PRI 마다 100 MHz 를
      통째로 상관해야 한다. 상시 기준신호(LTE CRS 1 kHz · 5G SSB 50 Hz)로는 그 PRF 가 안 나오므로
      `capture="always_on_pilot"` 은 **0 dB** 를 돌려준다(그 팔에서는 PRF 를 실제 반복률로 두고
      B_eff = B 로 센다).
    ⚠ 이 값은 «CPI 전체 코히어런트 적분 이득»(10log10(N_slow))도, «STFT 한 조각 이득»(④)도
      **아니다**. 모듈 상단 규약 주석의 «37 dB 짜리 셋» 경고를 볼 것."""
    if str(capture) in ("full_waveform", "fullwaveform", "full"):
        return float(10.0 * np.log10(float(b_hz) / float(prf)))
    return 0.0


def dc_ac_offset_db(dc_ac_db, *, exact=True):
    """⭐ **총전력 ↔ AC 변환량** [dB] ≥ 0.  snr_ac = snr_total − dc_ac_offset_db.

        P_tot = P_dc + P_ac 이므로  P_tot/P_ac = 1 + P_dc/P_ac = 1 + 10^(dc_ac_db/10)
        ⇒ 정확식:  dc_ac_off_db = 10·log10(1 + 10^(dc_ac_db/10))
        ⇒ 근사식:  dc_ac_off_db = dc_ac_db          (P_dc ≫ P_ac 일 때)

    `exact=False` 는 2026-08-10 이전 `ac_snr_db()` 가 쓰던 근사다. dc_ac_db ≥ 10 dB 면
    오차 ≤ 0.41 dB 이지만 dc_ac_db ≈ 0 이면 **3.0 dB 틀린다**(ECA 노치가 동체선을 지우면
    실제로 그 영역에 들어간다)."""
    d = float(dc_ac_db)
    if not exact:
        return d
    return float(10.0 * np.log10(1.0 + 10.0 ** (d / 10.0)))


def total_to_ac_db(snr_total_db, dc_ac_db, *, exact=True):
    """총전력 기준 SNR → AC(블레이드선) 기준 SNR [dB]."""
    return float(snr_total_db) - dc_ac_offset_db(dc_ac_db, exact=exact)


def ac_to_total_db(snr_ac_db, dc_ac_db, *, exact=True):
    """AC(블레이드선) 기준 SNR → 총전력 기준 SNR [dB]. `total_to_ac_db` 의 역."""
    return float(snr_ac_db) + dc_ac_offset_db(dc_ac_db, exact=exact)


def echo_over_noise_db(sigma_eq_m2, range_m, fc, *, eirp_dbm=DECLARED_EIRP_DBM,
                       rx_gain_dbi=DECLARED_RX_GAIN_DBI, nf_db=DECLARED_NF_DB,
                       b_hz=DECLARED_B_HZ, rx_range_m=None,
                       capture="pre_mf", prf=DECLARED_PRF_HZ, return_terms=False):
    """에코-대-잡음비 [dB]. **어느 사다리 칸인지는 `capture` 가 정한다.**

        P_echo = EIRP·G_rx·λ²·σ / ((4π)³·R_t²·R_r²)
        P_n    = k·T0·F·B                       (① snr_band_db, 정합필터 전)
        G_mf   = 10log10(B/PRF)                 (② 풀 캡처에서만)
        ⇒ ③ snr_slow_db = ① + ②  =  P_echo / (k·T0·F·PRF)   ← 같은 수의 두 표현

    capture
      "pre_mf"          (**기본, 2026-08-10 이전 동작과 비트동일**) — ① 만 돌려준다.
      "always_on_pilot" — ② 가 0 dB 라 값은 ① 과 같다. 이름만 규약에 맞춘 것.
      "full_waveform"   — ③ 을 돌려준다(② 를 붙인다). ⭐거리 링크버짓은 **이쪽이 옳다**.

    return_terms=True 면 **옛 값과 새 값을 한꺼번에** dict 로 돌려준다:
      snr_band_db(=옛 반환값) · g_mf_db · snr_slow_db · b_eff_hz · p_echo_w · p_noise_w.
      ⚠ 스칼라 반환은 배열도 될 수 있다(σ 를 배열로 주면). dict 의 전력항도 같은 모양이다."""
    lam = C0 / float(fc)
    eirp_w = 10.0 ** (float(eirp_dbm) / 10.0) * 1e-3
    g = 10.0 ** (float(rx_gain_dbi) / 10.0)
    f = 10.0 ** (float(nf_db) / 10.0)
    Rt = float(range_m)
    Rr = Rt if rx_range_m is None else float(rx_range_m)
    p_echo = eirp_w * g * lam ** 2 * np.asarray(sigma_eq_m2, float) / ((4 * np.pi) ** 3 * Rt ** 2 * Rr ** 2)
    p_n = K_BOLTZ * T0 * f * float(b_hz)
    band_db = 10.0 * np.log10(np.maximum(p_echo / p_n, 1e-300))
    g_mf = matched_filter_gain_db(b_hz, prf, capture=capture)
    if return_terms:
        return dict(snr_band_db=band_db, g_mf_db=float(g_mf), snr_slow_db=band_db + g_mf,
                    b_eff_hz=float(b_hz) / (10.0 ** (g_mf / 10.0)),
                    p_echo_w=p_echo, p_noise_band_w=float(p_n), capture=str(capture),
                    prf_hz=float(prf), convention=SNR_CONVENTION)
    if g_mf == 0.0:
        return band_db                      # ← 옛 경로 그대로(비트동일)
    return band_db + g_mf


def _f(x):
    """0차원이면 float, 아니면 배열 그대로 (사다리 dict 를 JSON 에 바로 실을 수 있게)."""
    a = np.asarray(x)
    return float(a) if a.ndim == 0 else a


def snr_ladder(sigma_eq_m2, range_m, fc, *, rx_range_m=None,
               prf=DECLARED_PRF_HZ, capture="full_waveform",
               dc_ac_db=None, exact_ac=True,
               nperseg=None, window="hann", window_n=None,
               eirp_dbm=DECLARED_EIRP_DBM, rx_gain_dbi=DECLARED_RX_GAIN_DBI,
               nf_db=DECLARED_NF_DB, b_hz=DECLARED_B_HZ):
    """⭐ 규약 v2 사다리 전부를 dict 로. **원장 키 이름이 그대로 이 dict 의 키다.**

    반환 키
      convention, capture, prf_hz, b_hz, b_eff_hz,
      snr_band_db ①, g_mf_db ②, snr_slow_db ③,
      dc_ac_db, dc_ac_off_db, snr_slow_ac_db ③′  (dc_ac_db 를 줬을 때만)
      g_stft_db ④, snr_map_ac_db ⑤              (nperseg 를 줬을 때만)
      p_echo_w, p_noise_band_w, p_noise_eff_w

    ⚠ ① 은 **`echo_over_noise_db()` 를 불러서** 얻는다(재구현 금지 규약).
    ⚠ 기하: `rx_range_m=None` 이면 모노스태틱 등가(R_t = R_r = R) — 거리 기울기 −40 dB/decade.
      바이스태틱으로 한 다리만 움직이면 −20 dB/decade 다. 원장에 어느 쪽인지 반드시 적을 것."""
    d = echo_over_noise_db(sigma_eq_m2, range_m, fc, eirp_dbm=eirp_dbm,
                           rx_gain_dbi=rx_gain_dbi, nf_db=nf_db, b_hz=b_hz,
                           rx_range_m=rx_range_m, capture=capture, prf=prf,
                           return_terms=True)
    out = dict(convention=SNR_CONVENTION, capture=str(capture),
               prf_hz=float(prf), b_hz=float(b_hz), b_eff_hz=d["b_eff_hz"],
               geometry=("monostatic_equivalent" if rx_range_m is None else "bistatic"),
               R_t_m=float(range_m), R_r_m=float(range_m if rx_range_m is None else rx_range_m),
               snr_band_db=_f(d["snr_band_db"]), g_mf_db=d["g_mf_db"],
               snr_slow_db=_f(d["snr_slow_db"]),
               p_echo_w=_f(d["p_echo_w"]), p_noise_band_w=d["p_noise_band_w"],
               p_noise_eff_w=K_BOLTZ * T0 * 10.0 ** (float(nf_db) / 10.0) * d["b_eff_hz"])
    if dc_ac_db is not None:
        off = dc_ac_offset_db(dc_ac_db, exact=exact_ac)
        out.update(dc_ac_db=float(dc_ac_db), dc_ac_off_db=float(off),
                   dc_ac_exact=bool(exact_ac),
                   snr_slow_ac_db=_f(np.asarray(d["snr_slow_db"]) - off))
    if nperseg is not None:
        l_win = window_coh_loss_db(window, window_n)
        g_stft = float(10.0 * np.log10(float(nperseg)) + l_win)
        out.update(nperseg=int(nperseg), window=str(window), window_coh_loss_db=l_win,
                   g_stft_db=g_stft)
        if "snr_slow_ac_db" in out:
            out["snr_map_ac_db"] = _f(np.asarray(out["snr_slow_ac_db"]) + g_stft)
    #  ⭐ **세 층위를 항상 함께 낸다** — 키 이름에 층위가 박혀 있어야 원장만 보고 구별된다.
    #    snr_sample_db (정합필터 **전**, 수신 표본당) · gain_mf_db · gain_stft_db.
    #    ⚠ «표본» 이 둘이다: 수신 표본(①)과 슬로타임 표본(③). 별칭은 ① 이다.
    for alias, canon in LADDER_KEY_ALIASES.items():
        if canon in out:
            out[alias] = out[canon]
    return out


def ac_snr_db(E, snr_total_db, *, exact=False):
    """⭐ **블레이드선(AC)의 실효 SNR** [dB] = 총전력 SNR − DC/AC 오프셋.

    ⚠ 왜 필요한가(2026-07-28 적대검증이 잡아낸 결함): `echo_over_noise_db`/`add_noise` 의
      SNR 은 **총전력 기준**인데, 마이크로도플러 시계열은 비회전 몸체가 만드는 **0-도플러 DC 가
      지배**한다(측정 dc_ac_db = 17~37 dB). 그래서 총전력 SNR 은 "블레이드선이 보이는가" 의
      지표로는 그만큼 낙관적이고, 그 오프셋은 거리에 따라 4.15 dB 흔들려 **상쇄되지도 않는다**.
      → 검출성을 논할 때는 **반드시 이 값**을 쓸 것.

    exact : False(**기본, 옛 동작과 비트동일**) 면 `dc_ac_db` 를 그냥 뺀다.
            True 면 정확식 10log10(1+10^(dc_ac/10)) 을 쓴다 → `dc_ac_offset_db()`.
            차이는 dc_ac ≥ 10 dB 에서 ≤ 0.41 dB, dc_ac = 0 dB 에서 3.0 dB."""
    d = float(md_metrics(E, 1.0)["dc_ac_db"])
    if not exact:
        return float(snr_total_db) - d
    return total_to_ac_db(snr_total_db, d, exact=True)


def add_noise(E, snr_db, rng, *, ref="total"):
    """복소 백색잡음을 더해 목표 SNR 을 맞춘다. 반환 (E_noisy, sigma_n).

    ⚠ **저수준 함수다.** 새 코드는 `noisy_series()` 를 써라 — 시드·눈금·층위를 원장에 남긴다.
      이 함수는 «잡음을 만드는 유일한 자리» 로 남기고(재구현 금지), 상위 배선은 전부 그쪽을 거친다.

    ref : ⭐**기준 전력을 무엇으로 잡나** — 저장소에 두 규약이 흩어져 있던 자리다.
      "total" (**기본, 옛 동작과 비트동일**) p_sig = mean|E|²        — 몸체 DC 포함(③ 눈금)
      "ac"                                   p_sig = mean|E−mean E|² — 블레이드선만(③′ 눈금)

    ⚠ 두 눈금은 `dc_ac_offset_db()` 만큼(기체별 17.3~37.2 dB) 다르다. **같은 표에 놓지 마라.**
      `md_classify_dataset` 는 "ac", `experiment_md_range` 는 "total" 을 쓴다 — 둘 다 이 함수를
      거치므로 원장의 `snr_reference` 필드만 보면 어느 눈금인지 알 수 있다."""
    if str(ref) == "ac":
        p_sig = float(np.mean(np.abs(E - np.mean(E)) ** 2))
    elif str(ref) == "total":
        p_sig = float(np.mean(np.abs(E) ** 2))
    else:
        raise ValueError(f"add_noise: ref must be 'total' or 'ac', got {ref!r}")
    p_n = p_sig / (10.0 ** (float(snr_db) / 10.0))
    s = np.sqrt(p_n / 2.0)
    n = rng.normal(0.0, s, size=E.shape) + 1j * rng.normal(0.0, s, size=E.shape)
    return E + n, float(np.sqrt(p_n))


# --------------------------------------------------------------------------- #
#  ⭐ 잡음 주입 입구 하나 — 시드를 받고 원장에 그대로 실을 provenance 를 돌려준다
# --------------------------------------------------------------------------- #
def stable_seed(*parts, base=0):
    """문자열/수를 **프로세스에 무관하게** 재현되는 32비트 시드로.

    ⚠ 왜 필요한가(2026-08-10 발견): `experiment_md_range.py` 가
      `abs(hash((drone, band))) % 2**31` 로 시드를 잡고 있었다. **파이썬 str 의 `hash()` 는
      실행마다 salt 가 달라진다**(PYTHONHASHSEED). 즉 그 원장의 잡음 실현은 **재현 불가능**했고
      시드가 어디에도 안 적혀 있었다. blake2b 는 프로세스·플랫폼에 무관하다."""
    import hashlib
    h = hashlib.blake2b("|".join(str(p) for p in parts).encode("utf-8"), digest_size=8)
    return int((int.from_bytes(h.digest(), "big") + int(base)) % (2 ** 31))


def _as_rng(seed_or_rng):
    """(rng, seed_recorded).  int → default_rng(int) 이고 시드가 기록된다.
    Generator 를 그대로 주면 재현 책임이 **호출자**에게 넘어간다(seed=None 으로 기록)."""
    if seed_or_rng is None:
        return np.random.default_rng(), None
    if isinstance(seed_or_rng, np.random.Generator):
        return seed_or_rng, None
    s = int(seed_or_rng)
    return np.random.default_rng(s), s


def noisy_series(E, snr_db, seed=None, *, ref="ac", n_real=1, capture=None, layer=None):
    """⭐⭐ **잡음 주입의 유일한 입구.** 슬로타임 복소열 E 에 복소 백색 가우시안을 더한다.

    ⭐ 순서가 중요하다 — **시계열에 더하고 그 다음 STFT** 한다. 스펙트로그램·전력·dB 이미지에
      더하면 (a) 맵 잡음 바닥이 지수분포(χ²₂) 대신 가우시안이 되고 (b) 겹친 프레임 간 상관과
      창 색이 사라지고 (c) 신호×잡음 교차항 2Re(s·n*) 이 통째로 빠진다. Sionna 자신도
      `apply_time_channel.py` 에서 채널 컨볼루션 **뒤 시간영역**에 AWGN 을 더한다.

    E       : 슬로타임 복소열 (n_t,)  — 정합필터 **출력** 열이어야 한다(③ 층)
    snr_db  : 목표 SNR. **어느 눈금인지는 `ref` 가 정한다**(규약 v2)
    seed    : ⭐int 를 줘라. 원장에 그대로 적히고 같은 시드면 비트동일하게 재현된다.
              Generator 를 주면 seed=None 으로 기록되고 재현 책임은 호출자에게 있다.
    ref     : "ac"(**기본**, ③′ 블레이드선 = 정본) | "total"(③ 총전력)
    n_real  : 잡음 실현 수. 반환 배열의 첫 축.

    반환 (En, prov)
      En   : (n_real, n_t) 복소 배열 — n_real=1 이어도 2차원이다(모양이 조건에 안 흔들리게)
      prov : 원장에 **그대로 실을** dict — seed·ref·snr_db·sigma_n·p_sig_w·convention·layer

    ⚠ 실현마다 잡음이 다르고 신호는 같다. rng 를 실현 사이에 **재생성하지 않는다**(같은
      스트림에서 이어 뽑는다) — 그래야 n_real 을 늘려도 앞쪽 실현이 그대로 재현된다."""
    rng, seed_rec = _as_rng(seed)
    E = np.asarray(E)
    outs, sig = [], None
    for _ in range(int(n_real)):
        En, s = add_noise(E, snr_db, rng, ref=ref)
        outs.append(En)
        sig = s
    p_sig = (float(np.mean(np.abs(E - np.mean(E)) ** 2)) if str(ref) == "ac"
             else float(np.mean(np.abs(E) ** 2)))
    prov = dict(convention=SNR_CONVENTION, snr_db=float(snr_db), snr_reference=str(ref),
                snr_rung=("snr_slow_ac_db" if str(ref) == "ac" else "snr_slow_db"),
                seed=seed_rec, n_real=int(n_real), sigma_n=float(sig),
                p_signal_w=p_sig, p_noise_w=float(sig) ** 2,
                noise="circular complex white Gaussian, added to the SLOW-TIME series "
                      "BEFORE any STFT (never to the map)",
                layer=str(layer) if layer else "slow_time_post_matched_filter",
                capture=(str(capture) if capture else None),
                reproducible=bool(seed_rec is not None))
    return np.asarray(outs), prov


# --------------------------------------------------------------------------- #
#  ⭐ 거리 ↔ SNR 를 잇는 길 (사다리의 역함수)
# --------------------------------------------------------------------------- #
#: 세 층위를 원장 키 이름에 박기 위한 별칭(`snr_ladder` 가 함께 낸다).
#: ⚠ `snr_sample_db` 는 «정합필터 **전**, 수신 표본당» 이다 — 슬로타임 표본은 `snr_slow_db` 다.
LADDER_KEY_ALIASES = {"snr_sample_db": "snr_band_db",
                      "gain_mf_db": "g_mf_db",
                      "gain_stft_db": "g_stft_db"}

RANGE_SLOPE_DB_PER_DECADE = {"both": 40.0, "one": 20.0}


def range_for_snr_db(target_db, sigma_eq_m2, fc, *, rung="snr_slow_ac_db",
                     legs="both", r_fixed_m=None, r_ref_m=1.0, **kw):
    """⭐ **주어진 SNR 이 나오는 거리 R [m]** — `snr_ladder()` 의 닫힌형 역함수.

    사다리의 모든 칸은 거리에 대해 `−10·n·log10(R)` 로만 움직인다(σ·이득은 거리에 무관).
      legs="both" : 모노스태틱 등가 R_t = R_r = R → n = 4 (**−40 dB/decade**)
      legs="one"  : Tx 다리 `r_fixed_m` 고정, Rx 만 이동 → n = 2 (**−20 dB/decade**)
    그래서 기준거리 한 점만 계산하면 나머지는 산술이다.

        R = r_ref · 10^((SNR(r_ref) − target) / slope)

    kw 는 `snr_ladder` 로 그대로 넘어간다(dc_ac_db·nperseg·capture·eirp_dbm …).
    `rung` 이 사다리에 없으면(예: dc_ac_db 를 안 주고 snr_slow_ac_db 를 요구) KeyError 다."""
    slope = RANGE_SLOPE_DB_PER_DECADE[str(legs)]
    if str(legs) == "one":
        if r_fixed_m is None:
            raise ValueError("legs='one' 이면 고정된 Tx 다리 r_fixed_m 이 필요하다")
        lad = snr_ladder(sigma_eq_m2, float(r_fixed_m), fc, rx_range_m=float(r_ref_m), **kw)
    else:
        lad = snr_ladder(sigma_eq_m2, float(r_ref_m), fc, **kw)
    if rung not in lad:
        raise KeyError(f"rung {rung!r} not in ladder (keys: {sorted(lad)})")
    v0 = float(np.asarray(lad[rung]))
    return float(float(r_ref_m) * 10.0 ** ((v0 - float(target_db)) / slope))


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
