# -*- coding: utf-8 -*-
"""
microdoppler.py — (report3 토대) 회전 프로펠러의 **마이크로-도플러** 시그니처
=============================================================================

분절 드론 모델(drones.pose/build_frame/build_propeller)을 이용해, 표적이 정지(호버)해도
**회전하는 블레이드**가 만드는 시간변조 후방산란을 계산한다.

원리
  몸체(프레임)는 0 도플러(상수 산란장 E_frame). 각 로터의 블레이드는 ω로 회전하므로
  표면점 위치가 시간에 따라 변해 위상이 변조된다 → 슬로타임 복소장 E(t):
      E(t) = E_frame + Σ_rotor exp(j2k·c·û) · Σ_p [n̂·v>0]|Γ_g|(n̂·v)ΔA·exp(j2k·P_local·v(t))
  여기서 v(t)=Rz(−θ(t))·û 는 '블레이드를 돌리는 대신 시선을 반대로 돌린' 등가표현(벡터화).
  θ(t)=base+dir·ω·t,  ω=2π·rpm/60,  dir=±1(CW/CCW).

  스펙트로그램(STFT)으로 보면: **블레이드가 시선에 수직일 때 번쩍(blade flash)** → 주기적
  세로 줄무늬 + 팁속도까지 퍼진 도플러(±f_tip, f_tip≈2·ω·R_blade/λ·cos el).
  (스펙트로그램에선 강한 정적 몸체항을 0-도플러 클러터로 제거 — spectrogram(remove_dc=True).)

주의(현실 연결): f_tip 은 수백~수천 Hz라, **이를 모호 없이 보려면 PRF≳2·f_tip(수 kHz↑)** 필요.
  5G SSB(50Hz)·CSI-RS(200Hz)·LTE CRS(1kHz) 같은 파일럿 반복률로는 블레이드 마이크로도플러가
  접힌다 → LaSen 류가 '기준+데이터'로 샘플률을 끌어올리는 또 하나의 이유.
"""
from __future__ import annotations
import numpy as np

from drones import build_frame, build_propeller, rotor_layout, drone_gamma_map
import rcs_po as _rcs_po
from rcs_po import mesh_to_points, po_field_dir, point_mat_keys, C0


def _look(az_deg, el_deg):
    az, el = np.radians(az_deg), np.radians(el_deg)
    return np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])


def microdoppler_series(spec, fc=3.5e9, az=0.0, el=15.0, rpm=None,
                        prf=20000.0, n_t=2048, spacing=None, blade_n=26,
                        rpm_per_rotor=None, angle_gamma=False):
    """회전 블레이드의 슬로타임 복소장 E(t). 반환 (t[s], E[복소], info).
    rpm=None 이면 드론별 대표 호버 회전수(spec.hover_rpm) 사용 — 큰 프로펠러(S1000 15in)는
      느리게 돌아 v_tip 이 현실적(Mach≈0.2)으로 나온다(고정 6000rpm 은 대형기에 과대).
    blade_n : 블레이드 스팬 분할(촘촘할수록 도플러 트랙이 매끈 — 이산/블록 현상 완화).

    rpm_per_rotor (2026-08-07 신설) : 길이 n_rotors 배열이면 **로터마다 다른 회전수**를 쓴다.
      ⭐ 실제 기체는 무게중심 치우침과 요 토크 균형 때문에 네 모터가 서로 다른 추력을 내고,
        그만큼 rpm 이 갈린다. 전부 같으면 신호가 완전한 주기함수가 되어 **스펙트로그램이
        시간에 따라 변하지 않는다** — 그건 가정의 성질이지 물리가 아니다.
      ⚠ None 이면 예전과 **비트 단위로 같다**(전 로터 같은 rpm).

    angle_gamma (2026-08-10 신설) : True 면 **각도의존 |Γ(θ)|** 를 쓴다 — 프레임은
      po_field_dir(mats=…), 블레이드는 아래 인라인 적분에 rcs_po._angle_shape 를 곱한다
      (설계·공식은 rcs_sbr/materials.gamma_shape 와 동일: |Γ(θ)|=|Γ_보정|·|Γ_벌크(θ)|/|Γ_벌크(0)|).
      ⭐ 도는 날개는 대부분의 시간을 큰 입사각에서 보내는 플라스틱이라, SBR 실측에서 프롭 채널이
        +5.16/+6.48 dB(matrice4e/mini5pro) 올랐다 — 순수 PO 판도 같은 물리를 옵트인으로 제공한다.
      ⚠ False(기본)면 예전과 **비트 단위로 같다**. rcs_po 규약(옵트인·많은 하위 사용처)을 따르고,
        env SIONNA2_ANGLE_GAMMA=0 이면 True 여도 죽는다(전역 킬스위치, SBR 과 동일)."""
    if rpm is None:
        rpm = getattr(spec, "hover_rpm", 6000.0)
    lam = C0 / fc; k = 2 * np.pi / lam
    spacing = spacing or lam / 11.0                # 촘촘한 점구름(매끈한 도플러)
    u = _look(az, el); ux, uy, uz = u
    ag = bool(angle_gamma) and _rcs_po.ANGLE_GAMMA  # 각도의존 Γ — 옵트인 ∧ 킬스위치

    # 프레임(비회전) → 상수 산란장
    gm = drone_gamma_map(spec)                     # 부위 재질 |Γ| (셸 반투명 + 내부 금속)
    if ag:
        from drones import DRONE_GROUP_MAT
        _g2m = {g: m for g, (m, _) in DRONE_GROUP_MAT.items()}      # 그룹 → 재질 키
        Pf, Nf, dAf, wf, kf = mesh_to_points(build_frame(spec), lam / 6.0, gamma=gm,
                                             return_keys=True)
        Ef = po_field_dir(Pf, Nf, dAf, fc, u, w=wf, mats=point_mat_keys(kf, _g2m))
    else:
        Pf, Nf, dAf, wf = mesh_to_points(build_frame(spec), lam / 6.0, gamma=gm)
        Ef = po_field_dir(Pf, Nf, dAf, fc, u, w=wf)

    # 프로펠러 — **CW/CCW 두 벌**. 실물 멀티로터는 반대회전 로터에 거울상 프롭을 단다.
    # ⚠ 2026-07-28: 옛 코드는 한 벌을 전 로터가 공유해 네 로터가 **같은 손잡이**였다.
    #   `drones.build_drone`/`pose_articulated` 가 거울상을 쓰도록 바뀌었으므로(같은 날짜),
    #   여기 순수-PO 판도 맞춰야 한다. 안 맞추면 같은 파일 안에서 PO판(카이럴 없음)과
    #   SBR판(pose_articulated 경유 → 카이럴 있음)이 서로 어긋난다.
    if ag:
        Pp, Np_, dAp, wp, kp = mesh_to_points(build_propeller(spec, n=blade_n), spacing,
                                              gamma=gm, return_keys=True)
        Pm, Nm_, dAm, wm, km = mesh_to_points(build_propeller(spec, n=blade_n, mirror=True),
                                              spacing, gamma=gm, return_keys=True)
        mats_p, mats_m = point_mat_keys(kp, _g2m), point_mat_keys(km, _g2m)
    else:
        Pp, Np_, dAp, wp = mesh_to_points(build_propeller(spec, n=blade_n), spacing, gamma=gm)
        Pm, Nm_, dAm, wm = mesh_to_points(build_propeller(spec, n=blade_n, mirror=True),
                                          spacing, gamma=gm)
        mats_p = mats_m = None
    rl = rotor_layout(spec)

    t = np.arange(n_t) / prf
    omega = 2 * np.pi * rpm / 60.0
    # 로터별 각속도 — rpm_per_rotor 가 없으면 전부 같다(옛 거동과 비트 동일)
    if rpm_per_rotor is None:
        omegas = [omega] * len(rl)
    else:
        rr = np.asarray(rpm_per_rotor, float).ravel()
        if len(rr) != len(rl):
            raise ValueError(f"rpm_per_rotor 길이 {len(rr)} != 로터 수 {len(rl)}")
        omegas = list(2 * np.pi * rr / 60.0)
    E = np.full(n_t, Ef, complex)
    for rot, om in zip(rl, omegas):
        cx, cy, cz = rot["center"]; base = np.radians(rot["base_ang"]); d = rot["dir"]
        # dir=+1 은 CCW → 기준(비거울) 형상, dir=−1 은 CW → 거울상 (rotor_layout 규약)
        Pb, Nb, wb, mb = ((Pp, Np_, dAp * wp, mats_p) if d > 0 else (Pm, Nm_, dAm * wm, mats_m))
        th = base + d * om * t                                      # (n_t,)
        # v(t) = Rz(-θ)·û  (블레이드 회전 ≡ 시선 반대회전)
        vx = ux * np.cos(th) + uy * np.sin(th)
        vy = -ux * np.sin(th) + uy * np.cos(th)
        vz = np.full_like(th, uz)
        V = np.stack([vx, vy, vz], axis=1)                          # (n_t,3)
        NU = Nb @ V.T                                               # (Npts, n_t) = cos θ_i(t)
        PU = Pb @ V.T
        if ag:   # ⭐각도의존 Γ — NU 가 곧 입사 코사인이라 시간축까지 한 번에 얹는다
            integ = (np.where(NU > 0, NU, 0.0)
                     * (wb[:, None] * _rcs_po._angle_shape(mb, fc, NU))
                     * np.exp(1j * 2 * k * PU))
        else:
            integ = np.where(NU > 0, NU, 0.0) * wb[:, None] * np.exp(1j * 2 * k * PU)
        Eb = integ.sum(axis=0) * np.exp(1j * 2 * k * (cx * ux + cy * uy + cz * uz))
        E += Eb

    prop_R = spec.prop_dia_mm / 1000.0 / 2.0
    f_tip = 2.0 * (omega * prop_R) / lam * np.cos(np.radians(el))    # 최대 마이크로도플러[Hz]
    info = dict(rpm=rpm, prf=prf, fc=fc, lam=lam, az=az, el=el,
                f_tip=f_tip, flash_hz=spec.prop_blades * rpm / 60.0,
                v_tip=omega * prop_R, n_rotors=len(rl), angle_gamma=ag)
    return t, E, info


def spectrogram(E, prf, nperseg=256, noverlap=None, nfft=None, remove_dc=True):
    """복소 E(t) → (도플러축 f[Hz], 시간축 t[s], |STFT| dB). 양측(±) 도플러.
    remove_dc=True: **정적 0-도플러(몸체 프레임) 성분을 빼고** 회전 블레이드 마이크로도플러만 본다
    (패시브레이더의 '정적 클러터 제거'에 해당). E(t) 자체엔 몸체가 강한 0-도플러 상수항으로 들어 있고
    |DC|/std(AC) 는 **드론·시선기하에 따라 ~1 에서 100 이상까지** 크게 다르다.
    (기본 기하 az=0°/el=15°: mini5pro 12.5, mavic4pro 20.1, matrice4e 32.8, s1000plus 62.1, phantom4 121.1
     — 대체로 몸체가 클수록 크지만 엄밀한 순서는 아니고, 같은 드론도 시선각을 바꾸면 한 자릿수까지 떨어진다:
     phantom4 는 az=30°/el=60° 에서 0.7, mini5pro 는 el=0° 에서 133.)
    → 몸체가 클수록/저앙각일수록 블레이드가 묻히므로 DC 제거는 기본으로 켜 두는 편이 안전하다.
    평균 제거 후 detrend=False 로 STFT.
    nfft : 제로패딩 FFT 크기(>nperseg) — 도플러축을 더 매끈하게(보간) 표시. 큰 noverlap → 시간 매끈."""
    from scipy.signal import spectrogram as _spec
    E = np.asarray(E)
    if remove_dc:
        E = E - E.mean()                                # 정적(몸체) 0-도플러 클러터 제거
    noverlap = noverlap if noverlap is not None else nperseg - max(1, nperseg // 16)
    nfft = nfft or nperseg
    f, tt, Sxx = _spec(E, fs=prf, nperseg=nperseg, noverlap=noverlap, nfft=nfft, detrend=False,
                       window=("hann"), return_onesided=False, scaling="spectrum", mode="magnitude")
    f = np.fft.fftshift(f); Sxx = np.fft.fftshift(Sxx, axes=0)
    Sdb = 20 * np.log10(Sxx / (Sxx.max() + 1e-30) + 1e-12)
    return f, tt, Sdb


if __name__ == "__main__":
    from drones import DRONES
    for k in ("phantom4", "s1000plus"):
        t, E, info = microdoppler_series(DRONES[k])      # 드론별 hover_rpm 사용
        print(f"{k:10s} 로터{info['n_rotors']} rpm{info['rpm']:.0f} "
              f"f_tip={info['f_tip']:.0f}Hz flash={info['flash_hz']:.0f}Hz "
              f"v_tip={info['v_tip']:.0f}m/s  |E|평균={np.abs(E).mean():.2e} 변동={np.std(np.abs(E)):.2e}")


# --------------------------------------------------------------------------- #
#  SBR 기반 마이크로도플러 (2026-07-14) — 가림(occlusion)이 들어간다
# --------------------------------------------------------------------------- #
#  왜 필요한가:
#    위 microdoppler_series() 는 순수 PO 다 — **가림이 없다**. 블레이드가 동체·모터 뒤로
#    돌아가도 계속 산란체로 계상된다. 실제로는 가려진다. 그리고 프로펠러는 **신호 그 자체**다.
#
#  핵심 통찰 — **드론 전체 자세는 단일 각도 φ = ωt 의 함수다.**
#    로터 k 의 스핀 위상 = dir_k · φ (base_ang 은 rotor_layout 이 이미 갖고 있다).
#    n-블레이드 프로펠러는 360/n 도 회전에 불변 → **φ 의 주기 = 360/n_blades**.
#    그래서 φ ∈ [0, 360/n) 를 n_phase 개로 잘라 SBR 을 **미리 계산**해 두고,
#    E(t) = E_table[φ(t) mod (360/n)] 로 조회하면 된다. 시간 스텝마다 광선을 쏘지 않는다.
def microdoppler_sbr(spec, fc=3.5e9, az=0.0, el=15.0, rpm=None, prf=20000.0,
                     n_t=6144, n_phase=240, spacing=None):
    """회전 블레이드의 슬로타임 복소장 E(t) — **SBR(가림 포함)**. 반환 (t, E, info).

    microdoppler_series() 의 SBR 판. 인터페이스 동일."""
    import numpy as _np
    from drones import pose_articulated, rotor_layout, DRONE_GROUP_MAT
    from rcs_sbr import sbr_field, grid_ref_from, freeze_grid_enabled

    if rpm is None:
        rpm = getattr(spec, "hover_rpm", 6000.0)
    lam = C0 / fc
    u = _look(az, el)
    gmat = {g: mat for g, (mat, _) in DRONE_GROUP_MAT.items()}
    rl = rotor_layout(spec)
    dirs = [r["dir"] for r in rl]

    period = 360.0 / max(1, spec.prop_blades)          # φ 의 주기 [deg]
    phis = _np.linspace(0.0, period, n_phase, endpoint=False)

    # φ 별 복소장 테이블 (여기서만 광선을 쏜다)
    #
    # ⭐⭐2026-08-10 — **광선 격자를 얼린다.**
    #   그전까지 `sbr_field` 는 자세마다 표적 경계상자에서 격자 중심·반경·칸수를 다시
    #   잡았다. 프로펠러가 돌면 경계상자가 바뀌므로 **자(모눈종이)가 프레임마다 움직였고**,
    #   마이크로도플러는 «프레임 사이 위상차» 로 재는 양이라 그 움직임이 표적의 운동으로
    #   기록됐다(시선방향 39.9 mm = 0.47 λ = 5.85 rad p-p 의 가짜 변조).
    #   ⭐결정적 증거 — 서로 안 가리는 로터의 PO 적분은 E = E₀ + Σ ΔE_j(φ_j) 로 정확히
    #     쪼개져야 하는데, 얼린 격자는 잔차 1e-15(기계정밀도), 움직이는 격자는 O(1) 이다.
    #     즉 물리적으로 결합할 수 없는 로터 사이에 결합을 지어냈다.
    #   ⇒ 로터 한 바퀴 전 구간의 **합집합 경계상자**로 판을 한 번 만들고 모든 자세에 쓴다.
    #     커널이 자세마다 덮개를 검사하므로 표적이 판 밖으로 나가면 예외가 난다.
    #   ⭐ 스위치 SIONNA2_FREEZE_GRID=0 이면 gref=None → 옛 동작(자세마다 격자 재정의)으로
    #     되돌아간다. 전후 비교를 **같은 코드**로 돌리기 위한 것이다.
    meshes = [pose_articulated(spec, rotor_phase_deg=[d * ph for d in dirs]) for ph in phis]
    gref = grid_ref_from(meshes, fc, spacing=spacing) if freeze_grid_enabled() else None
    tab = _np.zeros(n_phase, complex)
    for i, mesh in enumerate(meshes):
        tab[i] = sbr_field(mesh, gmat, fc, u, spacing=spacing, grid_ref=gref)

    # 시간축으로 조회 — φ(t) = 360·rpm/60 · t  (deg)
    t = _np.arange(n_t) / prf
    phi_t = (360.0 * rpm / 60.0) * t
    idx = _np.mod(phi_t / period * n_phase, n_phase)
    i0 = _np.floor(idx).astype(int) % n_phase
    i1 = (i0 + 1) % n_phase
    f = idx - _np.floor(idx)
    E = tab[i0] * (1 - f) + tab[i1] * f                 # 선형보간(테이블 사이)

    omega = 2 * _np.pi * rpm / 60.0
    prop_R = spec.prop_dia_mm / 1000.0 / 2.0
    info = dict(rpm=rpm, prf=prf, fc=fc, lam=lam, az=az, el=el,
                f_tip=2.0 * (omega * prop_R) / lam * _np.cos(_np.radians(el)),
                flash_hz=spec.prop_blades * rpm / 60.0,
                v_tip=omega * prop_R, n_rotors=len(rl),
                engine="sbr", n_phase=n_phase, period_deg=period)
    return t, E, info
