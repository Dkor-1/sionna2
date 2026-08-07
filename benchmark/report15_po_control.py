# -*- coding: utf-8 -*-
"""
report15_po_control.py — **대조군 A: 같은 위상 스텝을 우리 PO 커널로** (mini2 · matrice4e)
================================================================================================

`benchmark/report15_probe.py` 가 **스톡 Sionna PathSolver** 에 던진 질문을, **똑같은 격자**로
**우리 산란 커널**(PO / SBR)에 다시 던진다. 바꾸는 것은 **엔진 하나뿐**이다:

    기체 · 주파수 · 거리 · 자세 · 송수신 배치 · 로터 위상 격자 · 재질 · 위상 규약  ← 전부 동일
    산란 계산기                                                              ← 이것만 교체

⭐ 왜 이 대조가 필요한가
   Sionna 쪽 결론은 "확산(몬테카를로) 채널에서만 변조가 나오고, 정반사 채널은 통째로 비어 있다"
   였다(정반사 경로 0/576, 프롭 정반사 0/576). 그런데 그 변조가 **작다**(ptp 3.90 dB @ 잡음 σ
   1.83 dB). 두 가지 해석이 갈린다:
     (가) 이 기하·이 자세에서는 애초에 블레이드 변조가 거의 없다 → 엔진 탓이 아니다.
     (나) 블레이드 변조는 크게 있는데 **스톡 PathSolver 가 그것을 못 만든다**.
   ⇒ 같은 격자에 **표면적분을 하는 커널**을 넣어보면 갈린다. 그것이 이 파일이다.

■ 팔(arm) 구성 — 요인을 하나씩만 바꾼다
   A1 `po_plane_mono`         평면파 · 모노스태틱 · 가림 없음      (교과서 PO)
   A2 `po_spherical_mono`     구면파 · 모노스태틱 · 가림 없음      (A1 대비 = 파면 곡률 효과)
   A3 `po_spherical_bistatic` 구면파 · **실제 TX/RX 좌표** · 가림 없음  ⭐ Sionna 기하와 동일
   A4 `sbr_div{12,24,48}`     평면파 · 모노스태틱 · **가림 있음**   (A1 대비 = 가림 효과)
   S  (Sionna)                구면파 · 실제 TX/RX · 가림 있음 · **확률적 경로탐색**
   → A3 와 S 는 기하가 같고, 다른 것은 "표면적분을 하는가" 뿐이다.

■ 관측량 — 두 엔진을 **같은 축**에 올리는 법
   Sionna:  h(φ) = Σ_p a_p·exp(−j2πf_c·τ_p)      (probe 의 정의 그대로)
   우리:    E(φ) = 표면적분 복소 산란장 [m²]
   절대 스케일과 기준위상은 서로 다르다(우리 구면파 팔은 exp(−jk(R_t+R_s)) 를 이미 뺐다).
   **상수 복소배에 불변인 양**만 비교한다:
     · AC 상관  |⟨E−Ē, h−h̄⟩| / (‖·‖‖·‖)      — 파형이 같은가
     · |·| 의 dB 파형 ptp/std                    — 변조가 얼마나 큰가
     · φ 하모닉 스펙트럼                          — 변조가 **블레이드 도플러 자리**에 있는가
   ⛔ σ 로 무엇도 맞추지 않는다. 이건 파형 비교다.

■ 위상 규약이 정말 같은가
   probe.posed_mesh :  pose_articulated(rotor_phase_deg=[dir_k·φ])  → rotate("z", base+dir·φ)
   microdoppler_nearfield.phase_table : θ = base + dir·φ, 안테나를 Rz(−θ) 로 돌림 (엄밀히 등가)
   → 두 엔진의 φ 축은 정렬돼 있다. 아래 gate 에서 좌표·격자 일치를 **수치로** 확인해 남긴다.

■ 격자
   φ 는 **1회전(360°)** 을 128 등분해 계산하고, 거기서 잘라 쓴다:
     · matched32 = 인덱스 0,2,…,62  → φ = 0, 5.625, …, 174.375°  ⭐ Sionna 32 스텝과 **동일**
     · half64    = 인덱스 0..63     → 180° 구간을 2배 촘촘히
     · full128   = 360° 전체        → 홀수 하모닉(단일 블레이드 비대칭)까지 본다
   (2날 프로펠러의 180° 주기 가정은 삼각분할 탓에 mm 수준에서 깨진다 — 그 크기를 여기서 잰다.)

■ 잡음바닥의 대응물
   Sionna 의 바닥은 **확률적 경로탐색**의 시드 산포(σ=1.83 dB)다. 우리 커널은 결정론적이라
   같은 입력이면 **비트 단위로 같다**(반복 Δ = 0 을 실측해 남긴다). 그래서 우리 쪽의 정직한
   바닥은 "**이산화를 바꿔도 같은 파형이 나오는가**" 다 — 광선격자 λ/12·λ/24·λ/48, 점구름
   λ/11·λ/22, 블레이드 스팬분할 10·26 사이의 AC 상관으로 잰다.

⛔ src/drones.py · src/drone_cad.py 는 **읽기만** 한다.
⛔ 기존 산출물 덮어쓰기 금지 — 출력은 outputs/report15_po_control.json 하나뿐이다.
그림 없음(순수 측정). 주석·print 한국어.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (os.path.join(ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

#  ⭐ probe 모듈을 **기하·물리 상수의 단일 출처**로 삼는다(손으로 다시 타이핑하지 않기 위해).
#     import 시점에 gpu.pick() → mitsuba/sionna 초기화까지 probe 와 동일하게 일어난다.
import report15_probe as probe                                        # noqa: E402

from drones import (DRONES, DRONE_GROUP_MAT, build_frame,             # noqa: E402
                    pose_articulated, rotor_layout)
from rcs_sbr import sbr_field                                          # noqa: E402
import microdoppler_nearfield as mnf                                   # noqa: E402

FC = probe.FC
LAM = probe.LAM
C0 = probe.C0
AZ_DEG, EL_DEG = probe.AZ_DEG, probe.EL_DEG
RANGE_M, BASELINE_M = probe.RANGE_M, probe.BASELINE_M
KEYS = probe.KEYS

PROBE_JSON = probe.OUT_JSON
OUT_JSON = os.path.join(ROOT, "outputs", "report15_po_control.json")

#  φ 격자 (1회전 = 360°)
N_PHASE = 128                 # 360° 를 128 등분 → matched32 · half64 · full128 을 전부 포함
N_PHASE_FINE = 512            # PO 전용 세밀 격자 (진짜 스펙트럼의 꼬리를 본다)
SBR_DIVS = (12, 24, 48)       # 광선격자 λ/div (12 = 저장소 기본 DEFAULT_DIV)

#  PO 점구름 이산화 — matched 는 **Sionna 가 본 메쉬와 같은 프로펠러 분할**(build_propeller n=10)
PO_MATCHED = dict(blade_n=10, blade_div=11.0, frame_div=6.0)
PO_REFINED = dict(blade_n=26, blade_div=22.0, frame_div=12.0)

#  거리 스윕 (구면파 팔) — R=3 m 가 얼마나 극단적 근거리인지 자리매김한다
RANGE_SWEEP_M = (1.5, 3.0, 5.0, 10.0, 20.0, 100.0)

#  ⭐ 판정 문턱 — **선언값**이다. 결과를 보고 고르지 않으려고 코드에 박아 둔다.
THRESH = dict(
    ptp_db_min=1.0,             # |E| dB 위상변동 ptp 가 이보다 커야 '변조가 있다'
    refine_corr_min=0.90,       # 이산화(격자·점구름)를 바꿔도 AC 파형이 이만큼 같아야 '수렴'
    edge_over_ftip_min=0.5,     # 스펙트럼 −20 dB 가장자리가 f_tip 의 이 비율 이상이어야 '블레이드 도플러'
    edge_drop_db=20.0,          # 가장자리 정의(첨두 대비 −N dB)
)


# --------------------------------------------------------------------------- #
#  잡동사니
# --------------------------------------------------------------------------- #
def _j(o):
    """numpy 타입 → 순수 파이썬 (json 직렬화용)."""
    if isinstance(o, dict):
        return {str(k): _j(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_j(v) for v in o]
    if isinstance(o, (np.floating, np.integer)):
        o = o.item()
    if isinstance(o, float):
        return None if (math.isnan(o) or math.isinf(o)) else float(o)
    if isinstance(o, (np.bool_, bool)):
        return bool(o)
    if isinstance(o, complex):
        return dict(re=float(o.real), im=float(o.imag))
    return o


def db20(x):
    return float(20.0 * np.log10(abs(x) + 1e-300))


def sph_from_xyz(p):
    """직교좌표 → (거리, 방위[deg], 고각[deg]). `mnf.antenna_pos` 의 역함수."""
    p = np.asarray(p, float)
    r = float(np.linalg.norm(p))
    return r, float(np.degrees(np.arctan2(p[1], p[0]))), float(np.degrees(np.arcsin(p[2] / r)))


def antennas(az, el, rng=RANGE_M, baseline=BASELINE_M, ctr=(0.0, 0.0, 0.0)):
    """probe.place() 와 **같은 식**으로 TX/RX 좌표를 만든다 (씬 없이)."""
    u = probe.look_dir(az, el)
    e1, _ = probe.basis_perp(u)
    c = np.asarray(ctr, float)
    return c + rng * u + 0.5 * baseline * e1, c + rng * u - 0.5 * baseline * e1


# --------------------------------------------------------------------------- #
#  파형 지표
# --------------------------------------------------------------------------- #
def wave_metrics(E, keep_series=True):
    """복소 φ-파형 → 변조 크기 지표. (상수 복소배에 **불변인 양**만 판정에 쓴다)"""
    E = np.asarray(E, complex)
    amp = np.abs(E)
    adb = 20.0 * np.log10(amp + 1e-300)
    dc = complex(E.mean())
    ac = E - dc
    ac_rms = float(np.sqrt(np.mean(np.abs(ac) ** 2)))
    cs = probe._circ_stats(np.degrees(np.angle(E)))
    out = dict(
        n_phase=int(E.size),
        amp_db_mean=float(adb.mean()), amp_db_ptp=float(adb.max() - adb.min()),
        amp_db_std=float(adb.std(ddof=1)) if E.size > 1 else 0.0,
        amp_db_min=float(adb.min()), amp_db_max=float(adb.max()),
        dc_abs_db=db20(dc), ac_rms_db=float(20 * np.log10(ac_rms + 1e-300)),
        dc_ac_db=float(20 * np.log10((abs(dc) + 1e-300) / (ac_rms + 1e-300))),
        ac_over_dc_frac=float(ac_rms / (abs(dc) + 1e-300)),
        phase_circ_std_deg=cs["circ_std_deg"], phase_ptp_deg=cs["ptp_deg"],
    )
    if keep_series:
        out["amp_db"] = [float(x) for x in adb]
        out["phase_deg"] = [float(x) for x in np.degrees(np.angle(E))]
    return out


def phi_spectrum(E, span_deg, rot_hz, f_tip_hz, flash_hz, top_k=8,
                 edge_drop_db=THRESH["edge_drop_db"], keep_arrays=True):
    """φ 표 → **하모닉 스펙트럼**(= 슬로타임 도플러).

    표는 span_deg 를 N 등분한 **정확히 주기적인** 샘플이므로 창을 씌우지 않는다(누설 없음).
    φ 가 360° 도는 데 걸리는 시간은 1/rot_hz 초이므로, 하모닉 번호 m 의 도플러는
        f_m = m · (360/span_deg) · rot_hz          [Hz]
    (span=360° 면 f_m = m·rot_hz, span=180° 면 f_m = m·2·rot_hz = m·flash_hz — 2날 기준)
    나이퀴스트는 (N/2)·(360/span)·rot_hz 다.
    """
    E = np.asarray(E, complex)
    N = int(E.size)
    ac = E - E.mean()
    S = np.abs(np.fft.fftshift(np.fft.fft(ac))) ** 2
    m = np.fft.fftshift(np.fft.fftfreq(N, d=1.0 / N))          # 정수 하모닉 번호
    f = m * (360.0 / float(span_deg)) * float(rot_hz)
    tot = float(S.sum())
    nyq = float((N // 2) * (360.0 / float(span_deg)) * float(rot_hz))
    out = dict(n=N, span_deg=float(span_deg), harmonic_df_hz=float((360.0 / span_deg) * rot_hz),
               nyquist_hz=nyq, f_tip_hz=float(f_tip_hz), flash_hz=float(flash_hz),
               f_tip_over_nyquist=float(f_tip_hz / nyq) if nyq > 0 else None,
               ac_power=tot)
    if tot <= 0:
        return dict(out, empty=True)
    pk = float(S.max())
    ipk = int(np.argmax(S))
    thr = pk * 10.0 ** (-abs(edge_drop_db) / 10.0)
    above = np.where(S >= thr)[0]
    f_edge = float(np.max(np.abs(f[above]))) if above.size else 0.0
    ordr = np.argsort(S)[::-1][:top_k]
    inb = np.abs(f) <= float(f_tip_hz)
    even = (np.abs(m.astype(int)) % 2 == 0)
    out.update(
        peak_harmonic=int(round(float(m[ipk]))), peak_f_hz=float(f[ipk]),
        edge_f_hz=f_edge, edge_harmonic=int(round(f_edge / ((360.0 / span_deg) * rot_hz)))
        if rot_hz > 0 else None,
        edge_over_f_tip=float(f_edge / float(f_tip_hz)) if f_tip_hz > 0 else None,
        power_frac_within_f_tip=float(S[inb].sum() / tot),
        power_frac_beyond_f_tip=float(S[~inb].sum() / tot),
        power_frac_even_harmonics=float(S[even].sum() / tot),
        power_frac_odd_harmonics=float(S[~even].sum() / tot),
        top=[dict(m=int(round(float(m[i]))), f_hz=float(f[i]),
                  power_frac=float(S[i] / tot),
                  db_rel_peak=float(10 * np.log10(S[i] / pk + 1e-300))) for i in ordr],
    )
    if keep_arrays:
        out["spectrum_db_rel_peak"] = [float(x) for x in 10 * np.log10(S / pk + 1e-300)]
        out["spectrum_f_hz"] = [float(x) for x in f]
    return out


def spectrum_agreement(sp_a, sp_b, label_a="ours", label_b="sionna", m_show=6):
    """두 φ-스펙트럼의 **하모닉별** 대조. 같은 φ 격자·같은 span 일 때만 의미가 있다.

    ⭐ 왜 필요한가: AC 상관 하나는 "파형이 닮았다" 까지만 말한다. 그 닮음이 **어느 하모닉**에서
      오는지는 말하지 않는다. 변조가 m=±1(=블레이드 플래시 기본파) 하나뿐이면 그것은
      '회전하는 물체가 있다' 는 정보이지 **블레이드 도플러 확산**이 아니다. 그래서 하모닉별
      전력분율을 나란히 놓는다."""
    fa = np.asarray(sp_a.get("spectrum_f_hz", []), float)
    fb = np.asarray(sp_b.get("spectrum_f_hz", []), float)
    if fa.size == 0 or fa.size != fb.size or float(np.max(np.abs(fa - fb))) > 1e-6:
        return dict(applicable=False, reason="하모닉 축이 다르다 — 비교 불가")
    pa = 10.0 ** (np.asarray(sp_a["spectrum_db_rel_peak"], float) / 10.0)
    pb = 10.0 ** (np.asarray(sp_b["spectrum_db_rel_peak"], float) / 10.0)
    pa, pb = pa / pa.sum(), pb / pb.sum()
    df = float(sp_a["harmonic_df_hz"])
    m = np.round(fa / df).astype(int)
    rows = []
    for mm in range(1, int(m_show) + 1):
        sel = np.abs(m) == mm
        if sel.any():
            rows.append(dict(abs_m=int(mm), f_hz=float(mm * df),
                             frac_a=float(pa[sel].sum()), frac_b=float(pb[sel].sum())))
    return dict(applicable=True, label_a=label_a, label_b=label_b,
                pearson_r_power=float(np.corrcoef(pa, pb)[0, 1])
                if pa.std() > 0 and pb.std() > 0 else None,
                pearson_r_db=float(np.corrcoef(np.asarray(sp_a["spectrum_db_rel_peak"], float),
                                               np.asarray(sp_b["spectrum_db_rel_peak"], float))[0, 1]),
                harmonic_df_hz=df, by_abs_harmonic=rows,
                frac_a_in_first_harmonic=rows[0]["frac_a"] if rows else None,
                frac_b_in_first_harmonic=rows[0]["frac_b"] if rows else None)


def compare(Ea, Eb, label_a="a", label_b="b"):
    """두 φ-파형의 **형상 일치도**. 상수 복소배(이득·위상)에 불변인 양만 쓴다."""
    a = np.asarray(Ea, complex)
    b = np.asarray(Eb, complex)
    n = min(a.size, b.size)
    a, b = a[:n], b[:n]
    aa, bb = a - a.mean(), b - b.mean()
    na, nb = np.linalg.norm(aa), np.linalg.norm(bb)
    c = complex(np.vdot(aa, bb) / (na * nb)) if (na > 0 and nb > 0) else 0j
    da = 20 * np.log10(np.abs(a) + 1e-300)
    dbb = 20 * np.log10(np.abs(b) + 1e-300)
    r = (float(np.corrcoef(da, dbb)[0, 1])
         if (da.std() > 1e-12 and dbb.std() > 1e-12) else None)
    return dict(
        pair=f"{label_a} vs {label_b}", n=int(n),
        ac_corr_abs=float(abs(c)), ac_corr_phase_deg=float(np.degrees(np.angle(c))),
        db_waveform_pearson_r=r,
        ptp_db_a=float(da.max() - da.min()), ptp_db_b=float(dbb.max() - dbb.min()),
        level_delta_db=float(db20(a.mean()) - db20(b.mean())),
    )


# --------------------------------------------------------------------------- #
#  팔 ① — PO (가림 없음). 프레임/프롭 채널이 **해석적으로** 분리된다.
# --------------------------------------------------------------------------- #
def _po_frame_field(spec, wavefront, A_t, A_s, R_t, R_s, u_t, u_s, disc):
    """φ 무관 프레임 상수항 — `phase_table` 내부와 **같은 함수·같은 인자**로 계산한다.
    (phase_table 은 tab 을 E_frame 으로 초기화한 뒤 로터를 더한다 → 뺄셈이 정확히 프롭 채널이다.)"""
    k = 2.0 * np.pi / LAM
    (Pf, Nf, wf), _, _ = mnf._build_clouds(spec, LAM, disc["frame_div"], disc["blade_div"],
                                           disc["blade_n"])
    if wavefront == "plane":
        return complex(mnf._field_plane(Pf, Nf, wf, k, u_t, u_s)), int(len(wf))
    return complex(mnf._field_spherical(Pf, Nf, wf, k, A_t, A_s, R_t, R_s)), int(len(wf))


def arm_po(spec, az, el, *, wavefront, bistatic, n_phase, disc, rng=RANGE_M,
           baseline=BASELINE_M):
    """PO 팔 하나 → (phis, E_all, E_prop, info). E_prop = E_all − E_frame (해석적 분리).

    bistatic=True  : TX/RX 를 probe.place() 와 **같은 좌표**에 놓는다 (Sionna 기하와 동일).
    bistatic=False : 안테나 1개를 **시선(보어사이트) 위**에 놓는다 — SBR 팔의 û 와 같은 방향이라
                     '가림 효과' 대조가 각도 어긋남 없이 성립한다. (TX 위치를 쓰면 baseline 때문에
                     보어사이트에서 atan(0.1/R) 만큼 밀려 거리마다 자세가 달라진다 — 실제로
                     초안이 그 함정에 빠져 거리수렴이 가짜로 나빠졌다.)"""
    tx, rx = antennas(az, el, rng, baseline)
    if bistatic:
        r_t, az_t, el_t = sph_from_xyz(tx)
        r_r, az_r, el_r = sph_from_xyz(rx)
        kw = dict(rx_range_m=r_r, rx_az_deg=az_r, rx_el_deg=el_r)
    else:
        r_t, az_t, el_t = float(rng), float(az), float(el)
        tx = rx = mnf.antenna_pos(r_t, az_t, el_t)
        kw = {}
    t0 = time.time()
    phis, tab, info = mnf.phase_table(
        spec, FC, r_t, az_t, el_t, wavefront=wavefront, n_phase=int(n_phase),
        period_deg=360.0, frame_div=disc["frame_div"], blade_div=disc["blade_div"],
        blade_n=disc["blade_n"], **kw)
    A_t = mnf.antenna_pos(r_t, az_t, el_t)
    R_t = float(np.linalg.norm(A_t))
    if bistatic:
        A_s = mnf.antenna_pos(r_r, az_r, el_r)
        R_s = float(np.linalg.norm(A_s))
    else:
        A_s, R_s = A_t, R_t
    E_frame, n_frame_pts = _po_frame_field(spec, wavefront, A_t, A_s, R_t, R_s,
                                           A_t / R_t, A_s / R_s, disc)
    info = dict(info, seconds=float(time.time() - t0), bistatic_used=bool(bistatic),
                tx_xyz=[float(v) for v in tx], rx_xyz=[float(v) for v in rx],
                E_frame_abs_recomputed=float(abs(E_frame)),
                E_frame_match_db=float(abs(abs(E_frame) - info["E_frame_abs"])),
                disc=dict(disc), n_frame_pts=n_frame_pts)
    return np.asarray(phis, float), np.asarray(tab, complex), np.asarray(tab, complex) - E_frame, info


# --------------------------------------------------------------------------- #
#  팔 ② — SBR (가림 있음, 평면파 모노스태틱)
# --------------------------------------------------------------------------- #
def arm_sbr(spec, aspects, divs, n_phase, gmat, verbose=True):
    """φ 격자 × 자세 × 광선격자 → E(φ). 메쉬는 φ 당 **한 번만** 만들어 전부 재사용한다.

    반환 {(aspect_label, div): E[complex, n_phase]} + 진단.
    프레임 전용(프롭 제거) 씬도 한 번 재서 DC 맥락을 남긴다."""
    dirs = [r["dir"] for r in rotor_layout(spec)]
    phis = np.linspace(0.0, 360.0, int(n_phase), endpoint=False)
    us = {lab: probe.look_dir(a["az_deg"], a["el_deg"]) for lab, a in aspects.items()}
    tab = {(lab, d): np.zeros(int(n_phase), complex) for lab in aspects for d in divs}
    t0 = time.time()
    n_tris = None
    for i, ph in enumerate(phis):
        mesh = pose_articulated(spec, rotor_phase_deg=[d * float(ph) for d in dirs])
        if n_tris is None:
            n_tris = int(mesh.n_tris())
        for lab, u in us.items():
            for d in divs:
                tab[(lab, d)][i] = complex(sbr_field(mesh, gmat, FC, u, spacing=LAM / float(d)))
        if verbose and (i % 16 == 0 or i == len(phis) - 1):
            print(f"      [sbr/{spec.key}] φ={ph:7.3f}°  ({i+1}/{len(phis)})  "
                  f"{time.time()-t0:6.1f}s", flush=True)
    frame_mesh = build_frame(spec)          # 프롭을 뺀 비회전부만 (DC 맥락)
    fr = {}
    for lab in aspects:
        for d in divs:
            v = complex(sbr_field(frame_mesh, gmat, FC, us[lab], spacing=LAM / float(d)))
            fr[f"{lab}|div{d}"] = dict(abs=float(abs(v)), db=db20(v),
                                       deg=float(np.degrees(np.angle(v))))
    #  결정성 — 같은 입력 재실행이 **비트 단위로** 같은가 (Sionna 의 시드 산포에 대응하는 자리)
    m0 = pose_articulated(spec, rotor_phase_deg=[d * 0.0 for d in dirs])
    lab0 = list(aspects)[0]
    e1 = complex(sbr_field(m0, gmat, FC, us[lab0], spacing=LAM / float(divs[0])))
    e2 = complex(sbr_field(m0, gmat, FC, us[lab0], spacing=LAM / float(divs[0])))
    m0b = pose_articulated(spec, rotor_phase_deg=[d * 0.0 for d in dirs])
    e3 = complex(sbr_field(m0b, gmat, FC, us[lab0], spacing=LAM / float(divs[0])))
    diag = dict(seconds=float(time.time() - t0), n_tris=n_tris,
                frame_only=fr,
                determinism=dict(
                    repeat_delta_abs=float(abs(e2 - e1)),
                    remesh_delta_abs=float(abs(e3 - e1)),
                    repeat_delta_db=(db20(e2) - db20(e1)),
                    remesh_delta_db=(db20(e3) - db20(e1)),
                    note=("우리 커널은 결정론적이라 같은 입력 재실행·같은 위상 재메쉬가 "
                          "비트 단위로 같아야 한다. Sionna 는 여기서 σ=0.74~1.83 dB 였다.")))
    return phis, tab, diag


# --------------------------------------------------------------------------- #
#  Sionna 쪽 파형 복원 (probe JSON 에서)
# --------------------------------------------------------------------------- #
def sionna_waveform(J, key, which, mode="prod"):
    """probe JSON → Sionna h(φ) 복원.

    probe 는 run 마다 `amp_db`(=20log10|h|) 와 `phase_deg`(=arg h) 를 남겼으므로
    **복소 h 를 정확히 되살릴 수 있다**(all 채널). prop 채널은 진폭만 있어 |h| 만 쓴다.
    """
    R = J["airframes"][key].get(which)
    if not R:
        return None
    rows = R["by_mode"][mode]
    phases = np.array([r["phase_deg"] for r in rows], float)
    seeds = sorted({x["seed"] for r in rows for x in r["runs"]})
    H = np.full((len(seeds), len(rows)), np.nan + 0j)
    A = np.full((len(seeds), len(rows)), np.nan)
    npaths = np.zeros((len(seeds), len(rows)))
    for j, r in enumerate(rows):
        for x in r["runs"]:
            i = seeds.index(x["seed"])
            if x.get("amp_db") is not None and x.get("phase_deg") is not None:
                H[i, j] = 10.0 ** (x["amp_db"] / 20.0) * np.exp(1j * np.radians(x["phase_deg"]))
            if x.get("prop_amp_db") is not None:
                A[i, j] = 10.0 ** (x["prop_amp_db"] / 20.0)
            npaths[i, j] = float(x.get("n_paths") or 0)
    ok = np.isfinite(H).all(axis=0)
    out = dict(which=which, mode=mode, n_phase=int(len(rows)), seeds=[int(s) for s in seeds],
               phases_deg=[float(x) for x in phases],
               all_channel_complete=bool(ok.all()),
               n_paths_mean=float(npaths.mean()),
               geometry=R["geometry"], spp=int(R["spp"]))
    if not ok.all():
        return out
    Hm = H.mean(axis=0)                                  # 시드평균 **복소** (코히런트 평균)
    out["h_seed_mean"] = Hm
    out["h_by_seed"] = H
    out["prop_abs_by_seed"] = A
    #  ⭐ Sionna 파형의 **재현성** — 시드를 다시 뽑으면 같은 파형이 나오는가
    cs = []
    for i in range(len(seeds)):
        for j in range(i + 1, len(seeds)):
            a, b = H[i] - H[i].mean(), H[j] - H[j].mean()
            na, nb = np.linalg.norm(a), np.linalg.norm(b)
            if na > 0 and nb > 0:
                cs.append(float(abs(np.vdot(a, b)) / (na * nb)))
    dbw = 20 * np.log10(np.abs(H) + 1e-300)
    rs = []
    for i in range(len(seeds)):
        for j in range(i + 1, len(seeds)):
            if dbw[i].std() > 1e-12 and dbw[j].std() > 1e-12:
                rs.append(float(np.corrcoef(dbw[i], dbw[j])[0, 1]))
    out["seed_reproducibility"] = dict(
        n_pairs=len(cs),
        ac_corr_mean=float(np.mean(cs)) if cs else None,
        ac_corr_min=float(np.min(cs)) if cs else None,
        ac_corr_max=float(np.max(cs)) if cs else None,
        db_pearson_mean=float(np.mean(rs)) if rs else None,
        per_seed_ptp_db=[float(x.max() - x.min()) for x in dbw],
        note=("시드마다 얻은 32점 파형끼리의 AC 상관. 1 에 가까우면 '재현되는 파형', "
              "0 에 가까우면 '매번 다른 몬테카를로 실현'이다."))
    return out


# --------------------------------------------------------------------------- #
#  기체 하나 처리
# --------------------------------------------------------------------------- #
def run_airframe(key, J_probe, n_phase=N_PHASE, n_fine=N_PHASE_FINE, divs=SBR_DIVS,
                 do_range=True, do_fine=True):
    spec = DRONES[key]
    gmat = {g: m for g, (m, _) in DRONE_GROUP_MAT.items()}
    P = J_probe["airframes"][key]
    ph_matched = probe.airframe_physics(spec, 32)         # Sionna 가 실제로 쓴 스텝 수
    ph_fine = probe.airframe_physics(spec, n_phase)
    rot_hz = float(ph_matched["hover_rpm"]) / 60.0
    f_tip = float(ph_matched["f_tip_hz"])
    flash = float(ph_matched["flash_hz"])

    aspects = {"ref": dict(az_deg=AZ_DEG, el_deg=EL_DEG, label="기준자세",
                           sionna_key="D_sweep"),
               "hot": dict(az_deg=P["S_aspect"]["hot_aspect"]["az_deg"],
                           el_deg=P["S_aspect"]["hot_aspect"]["el_deg"],
                           label="정반사 hot 자세", sionna_key="D_sweep_hot")}

    #  ── gate ①: 기하가 Sionna 쪽과 정말 같은가 (좌표를 직접 대조) ──
    gates = dict(geometry={})
    for lab, a in aspects.items():
        tx, rx = antennas(a["az_deg"], a["el_deg"])
        g = P[a["sionna_key"]]["geometry"]
        r_t, az_t, el_t = sph_from_xyz(tx)
        gates["geometry"][lab] = dict(
            tx_max_abs_diff_m=float(np.max(np.abs(tx - np.array(g["tx"], float)))),
            rx_max_abs_diff_m=float(np.max(np.abs(rx - np.array(g["rx"], float)))),
            sph_roundtrip_max_m=float(np.max(np.abs(
                mnf.antenna_pos(r_t, az_t, el_t) - tx))),
            bistatic_deg_probe=float(g["bistatic_deg"]))

    #  ── gate ②: φ 격자가 Sionna 의 32 스텝을 정확히 포함하는가 ──
    phis_all = np.linspace(0.0, 360.0, int(n_phase), endpoint=False)
    idx_matched = np.arange(0, n_phase // 2, 2)            # 32 개 (180° 를 32 등분)
    idx_half = np.arange(0, n_phase // 2)                  # 64 개 (180°)
    sio_phis = np.array([float(r["phase_deg"]) for r in P["D_sweep"]["by_mode"]["prod"]], float)
    nc = min(idx_matched.size, sio_phis.size)
    gates["phase_grid"] = dict(
        n_phase=int(n_phase), n_matched=int(idx_matched.size),
        n_sionna=int(sio_phis.size), n_compared=int(nc),
        sionna_phases_deg=[float(x) for x in sio_phis],
        our_matched_phases_deg=[float(x) for x in phis_all[idx_matched]],
        max_abs_diff_vs_sionna_deg=float(np.max(np.abs(
            phis_all[idx_matched][:nc] - sio_phis[:nc]))),
        note="matched32 = 우리 128 격자의 0,2,…,62 번 → Sionna 32 스텝과 동일해야 한다")

    print(f"  기하 gate: tx Δ={max(v['tx_max_abs_diff_m'] for v in gates['geometry'].values()):.3e} m  "
          f"φ 격자 Δ={gates['phase_grid']['max_abs_diff_vs_sionna_deg']:.3e}°", flush=True)

    #  ── PO 팔들 ──
    arms = {}         # (aspect, arm) -> dict(E_all, E_prop, info)
    for lab, a in aspects.items():
        for arm, (wf, bis, disc) in {
            "po_plane_mono": ("plane", False, PO_MATCHED),
            "po_spherical_mono": ("spherical", False, PO_MATCHED),
            "po_spherical_bistatic": ("spherical", True, PO_MATCHED),
        }.items():
            phis, Ea, Ep, info = arm_po(spec, a["az_deg"], a["el_deg"], wavefront=wf,
                                        bistatic=bis, n_phase=n_phase, disc=disc)
            arms[(lab, arm)] = dict(E_all=Ea, E_prop=Ep, info=info)
            print(f"      [po/{key}/{lab}/{arm}] |E| ptp="
                  f"{np.ptp(20*np.log10(np.abs(Ea)+1e-300)):6.2f} dB  "
                  f"prop ptp={np.ptp(20*np.log10(np.abs(Ep)+1e-300)):6.2f} dB  "
                  f"[{info['seconds']:.0f}s]", flush=True)
    #  이산화 정밀화 팔 (기준자세만) — 우리 커널의 '바닥' 은 이산화 재현성이다
    phis, Ea, Ep, info = arm_po(spec, AZ_DEG, EL_DEG, wavefront="spherical", bistatic=True,
                                n_phase=n_phase, disc=PO_REFINED)
    arms[("ref", "po_spherical_bistatic_refined")] = dict(E_all=Ea, E_prop=Ep, info=info)
    print(f"      [po/{key}/ref/refined] |E| ptp={np.ptp(20*np.log10(np.abs(Ea)+1e-300)):6.2f} dB "
          f" [{info['seconds']:.0f}s]", flush=True)

    #  ── SBR 팔 (가림) ──
    sbr_phis, sbr_tab, sbr_diag = arm_sbr(spec, aspects, divs, n_phase, gmat)
    for (lab, d), E in sbr_tab.items():
        arms[(lab, f"sbr_div{d}")] = dict(E_all=E, E_prop=None,
                                          info=dict(engine="sbr", div=int(d),
                                                    spacing_m=float(LAM / d),
                                                    wavefront="plane", bistatic_used=False))

    #  ── 팔별 지표 (세 격자 위에서) ──
    grids = dict(matched32=(idx_matched, 180.0), half64=(idx_half, 180.0),
                 full128=(np.arange(n_phase), 360.0))
    results = {}
    for (lab, arm), d in arms.items():
        r = dict(info=_j(d["info"]), aspect=lab)
        for gname, (idx, span) in grids.items():
            keep = gname in ("matched32", "full128")       # half64 는 지표만 (파일 크기)
            E = d["E_all"][idx]
            cell = dict(wave=wave_metrics(E, keep_series=keep),
                        spectrum=phi_spectrum(E, span, rot_hz, f_tip, flash, keep_arrays=keep))
            if d["E_prop"] is not None:
                Ep = d["E_prop"][idx]
                cell["wave_prop"] = wave_metrics(Ep, keep_series=keep)
                cell["spectrum_prop"] = phi_spectrum(Ep, span, rot_hz, f_tip, flash,
                                                     keep_arrays=keep)
            r[gname] = cell
        results[f"{lab}/{arm}"] = r

    #  ── 팔 사이 대조 (요인 분해) ──
    def _E(lab, arm, idx):
        return arms[(lab, arm)]["E_all"][idx]

    cross = {}
    for lab in aspects:
        cc = {}
        cc["wavefront_plane_vs_spherical"] = compare(
            _E(lab, "po_plane_mono", idx_matched), _E(lab, "po_spherical_mono", idx_matched),
            "po_plane_mono", "po_spherical_mono")
        cc["bistatic_mono_vs_bistatic"] = compare(
            _E(lab, "po_spherical_mono", idx_matched), _E(lab, "po_spherical_bistatic", idx_matched),
            "po_spherical_mono", "po_spherical_bistatic")
        cc["occlusion_po_vs_sbr"] = compare(
            _E(lab, "po_plane_mono", idx_matched), _E(lab, f"sbr_div{divs[0]}", idx_matched),
            "po_plane_mono", f"sbr_div{divs[0]}")
        for i in range(len(divs) - 1):
            cc[f"sbr_div{divs[i]}_vs_div{divs[i+1]}"] = compare(
                _E(lab, f"sbr_div{divs[i]}", idx_matched),
                _E(lab, f"sbr_div{divs[i+1]}", idx_matched),
                f"sbr_div{divs[i]}", f"sbr_div{divs[i+1]}")
        if lab == "ref":
            cc["po_disc_matched_vs_refined"] = compare(
                _E(lab, "po_spherical_bistatic", idx_matched),
                _E(lab, "po_spherical_bistatic_refined", idx_matched),
                "po(blade_n=10,λ/11)", "po(blade_n=26,λ/22)")
        cross[lab] = cc

    #  ── Sionna 대조 ──
    sio = {}
    for lab, a in aspects.items():
        W = sionna_waveform(J_probe, key, a["sionna_key"], mode="prod")
        if not W or "h_seed_mean" not in W:
            sio[lab] = _j(W or {})
            continue
        Hm = W["h_seed_mean"]
        rec = dict({k: v for k, v in W.items()
                    if k not in ("h_seed_mean", "h_by_seed", "prop_abs_by_seed")})
        rec["wave_seed_mean"] = wave_metrics(Hm)
        rec["spectrum_seed_mean"] = phi_spectrum(Hm, 180.0, rot_hz, f_tip, flash)
        #  시드별 파형의 스펙트럼도 — 몬테카를로 실현이면 하모닉 구조가 없다
        rec["spectrum_seed1"] = phi_spectrum(W["h_by_seed"][0], 180.0, rot_hz, f_tip, flash,
                                             keep_arrays=False)
        Ap = W["prop_abs_by_seed"]
        if np.isfinite(Ap).all():
            rec["wave_prop_abs_seed_mean"] = wave_metrics(Ap.mean(axis=0) + 0j)
        #  ⭐ 엔진 대 엔진
        vs = {}
        for arm in ("po_spherical_bistatic", "po_plane_mono", f"sbr_div{divs[0]}",
                    f"sbr_div{divs[-1]}"):
            vs[arm] = compare(arms[(lab, arm)]["E_all"][idx_matched], Hm, arm, "sionna")
        #  prop 채널은 Sionna 가 진폭만 남겼다 → dB 파형 상관만
        if np.isfinite(Ap).all():
            pa = 20 * np.log10(np.abs(arms[(lab, "po_spherical_bistatic")]["E_prop"][idx_matched])
                               + 1e-300)
            pb = 20 * np.log10(Ap.mean(axis=0) + 1e-300)
            nn = min(pa.size, pb.size)
            pa, pb = pa[:nn], pb[:nn]
            vs["prop_db_only"] = dict(
                pair="po_spherical_bistatic(prop) vs sionna(prop, 진폭만)",
                db_waveform_pearson_r=(float(np.corrcoef(pa, pb)[0, 1])
                                       if pa.std() > 1e-12 and pb.std() > 1e-12 else None),
                ptp_db_a=float(pa.max() - pa.min()), ptp_db_b=float(pb.max() - pb.min()),
                note="Sionna 는 prop 채널의 위상을 남기지 않았다 — 복소 상관 불가")
        rec["vs_our_kernel"] = vs
        #  ⭐ 하모닉별 대조 — 닮음이 어느 주파수에서 오는가
        rec["spectrum_agreement"] = {
            arm: spectrum_agreement(results[f"{lab}/{arm}"]["matched32"]["spectrum"],
                                    rec["spectrum_seed_mean"], arm, "sionna")
            for arm in ("po_spherical_bistatic", f"sbr_div{divs[0]}")}
        sio[lab] = rec

    #  ── 세밀 φ 격자 (PO 전용) — 진짜 스펙트럼의 꼬리 ──
    fine = {}
    if do_fine:
        for wf, bis in (("spherical", True), ("plane", False)):
            phf, Eaf, Epf, inf = arm_po(spec, AZ_DEG, EL_DEG, wavefront=wf, bistatic=bis,
                                        n_phase=n_fine, disc=PO_MATCHED)
            nm = f"po_{wf}_{'bistatic' if bis else 'mono'}_n{n_fine}"
            fine[nm] = dict(info=_j(inf),
                            wave=wave_metrics(Eaf, keep_series=False),
                            spectrum=phi_spectrum(Eaf, 360.0, rot_hz, f_tip, flash),
                            wave_prop=wave_metrics(Epf, keep_series=False),
                            spectrum_prop=phi_spectrum(Epf, 360.0, rot_hz, f_tip, flash))
            #  세밀표 → 32 스텝으로 **격간추출**했을 때 무엇이 남는가 (Sionna 격자의 한계)
            step = max(1, n_fine // 64)
            sub = Eaf[np.arange(0, n_fine // 2, step)]
            #  같은 φ 를 512 격자와 128 격자에서 각각 계산한 값 — **수치 재현성 gate**
            twin = ("po_spherical_bistatic" if bis else "po_plane_mono")
            fine[nm]["subsample_matched32"] = dict(
                wave=wave_metrics(sub, keep_series=False),
                spectrum=phi_spectrum(sub, 180.0, rot_hz, f_tip, flash, keep_arrays=False),
                vs_128grid=compare(sub, arms[("ref", twin)]["E_all"][idx_matched],
                                   f"{nm}[matched32]", f"{twin}[matched32]"),
                note=("512 격자에서 뽑은 32 점과 128 격자의 matched32 는 **같은 φ** 다 — "
                      "AC 상관이 1 이 아니면 구현이 어긋난 것이다."))
            print(f"      [po/{key}/fine/{nm}] edge={fine[nm]['spectrum']['edge_f_hz']:.0f} Hz "
                  f"(f_tip={f_tip:.0f})  [{inf['seconds']:.0f}s]", flush=True)

    #  ── 거리 스윕 (구면파 팔) ──
    rng_sweep = {}
    if do_range:
        #  ⚠ 평면파 기준은 **모노스태틱**이다. 그래서 거리수렴은 모노 팔로 봐야 요인이 하나다
        #    (바이스태틱 팔을 평면파 모노와 대면 3.8° 오프셋 효과가 섞인다).
        ref_plane = arms[("ref", "po_plane_mono")]["E_all"]
        for R in RANGE_SWEEP_M:
            _, Em, _, infm = arm_po(spec, AZ_DEG, EL_DEG, wavefront="spherical",
                                    bistatic=False, n_phase=n_phase, disc=PO_MATCHED, rng=R)
            _, Eb, _, infb = arm_po(spec, AZ_DEG, EL_DEG, wavefront="spherical",
                                    bistatic=True, n_phase=n_phase, disc=PO_MATCHED, rng=R)
            rng_sweep[f"{R:g}"] = dict(
                range_m=float(R),
                range_over_farfield=float(R / ph_matched["farfield_m"]),
                in_farfield=bool(R >= ph_matched["farfield_m"]),
                wave_mono=wave_metrics(Em, keep_series=False),
                wave_bistatic=wave_metrics(Eb, keep_series=False),
                spectrum_mono=phi_spectrum(Em, 360.0, rot_hz, f_tip, flash, keep_arrays=False),
                vs_plane_limit_mono=compare(Em, ref_plane, f"spherical mono R={R:g} m",
                                            "plane mono"),
                vs_plane_limit_bistatic=compare(Eb, ref_plane, f"spherical bist R={R:g} m",
                                                "plane mono"),
                mono_vs_bistatic=compare(Em, Eb, f"mono R={R:g} m", f"bistatic R={R:g} m"),
                seconds=float(infm["seconds"] + infb["seconds"]))
        print(f"      [po/{key}/range] AC corr vs 평면파(모노): " +
              "  ".join(f"{k}m={v['vs_plane_limit_mono']['ac_corr_abs']:.3f}"
                        for k, v in rng_sweep.items()), flush=True)
        print(f"      [po/{key}/range] 모노 vs 바이스태틱: " +
              "  ".join(f"{k}m={v['mono_vs_bistatic']['ac_corr_abs']:.3f}"
                        for k, v in rng_sweep.items()), flush=True)

    #  ── 헤드라인 판정 (⛔ 손으로 고르지 않는다) ──
    def _hl(lab):
        base = results[f"{lab}/po_spherical_bistatic"]
        m32 = base["matched32"]
        f128 = base["full128"]
        refine = []
        if lab == "ref":
            refine.append(cross[lab]["po_disc_matched_vs_refined"]["ac_corr_abs"])
        refine += [cross[lab][k]["ac_corr_abs"] for k in cross[lab]
                   if k.startswith("sbr_div") and "_vs_div" in k]
        rmin = float(min(refine)) if refine else None
        edge_ratio = f128["spectrum"].get("edge_over_f_tip")
        ok = bool(m32["wave"]["amp_db_ptp"] > THRESH["ptp_db_min"]
                  and (rmin is not None and rmin > THRESH["refine_corr_min"])
                  and (edge_ratio is not None and edge_ratio >= THRESH["edge_over_ftip_min"]))
        sw = sio.get(lab, {})
        return dict(
            aspect=lab, az_deg=aspects[lab]["az_deg"], el_deg=aspects[lab]["el_deg"],
            our_ptp_db_matched32=m32["wave"]["amp_db_ptp"],
            our_ptp_db_prop_matched32=m32.get("wave_prop", {}).get("amp_db_ptp"),
            our_dc_ac_db=m32["wave"]["dc_ac_db"],
            our_edge_f_hz=f128["spectrum"].get("edge_f_hz"),
            our_edge_over_f_tip=edge_ratio,
            our_power_frac_within_f_tip=f128["spectrum"].get("power_frac_within_f_tip"),
            our_power_frac_odd_harmonics=f128["spectrum"].get("power_frac_odd_harmonics"),
            refine_ac_corr_min=rmin,
            sbr_vs_po_ac_corr=cross[lab]["occlusion_po_vs_sbr"]["ac_corr_abs"],
            sionna_ptp_db=(sw.get("wave_seed_mean") or {}).get("amp_db_ptp"),
            sionna_seed_ac_corr_mean=(sw.get("seed_reproducibility") or {}).get("ac_corr_mean"),
            sionna_edge_over_f_tip=(sw.get("spectrum_seed_mean") or {}).get("edge_over_f_tip"),
            ours_vs_sionna_ac_corr=((sw.get("vs_our_kernel") or {})
                                    .get("po_spherical_bistatic", {}).get("ac_corr_abs")),
            ptp_ratio_ours_over_sionna=(
                float(m32["wave"]["amp_db_ptp"] / sw["wave_seed_mean"]["amp_db_ptp"])
                if sw.get("wave_seed_mean") and sw["wave_seed_mean"]["amp_db_ptp"] > 0 else None),
            micro_doppler_present_our_kernel=ok,
            verdict=("우리 커널: 블레이드 마이크로도플러 있음(수렴·f_tip 까지 확장)" if ok
                     else "우리 커널: 세 조건 중 일부 미충족 — 아래 수치를 직접 볼 것"))

    return dict(
        physics=dict(matched32=ph_matched, fine=ph_fine,
                     rot_hz=rot_hz, note_ko=("hover_rpm·프롭지름은 drones.py 스펙에서 오고, "
                                             "f_tip·flash·나이퀴스트는 probe 와 같은 함수로 계산했다.")),
        aspects=_j(aspects), gates=_j(gates),
        arms=_j(results), factor_comparison=_j(cross), sionna=_j(sio),
        fine_grid=_j(fine), range_sweep=_j(rng_sweep),
        sbr_diag=_j(sbr_diag),
        headline={lab: _j(_hl(lab)) for lab in aspects})


# --------------------------------------------------------------------------- #
#  후처리 — "두 엔진의 불일치를 Sionna 의 몬테카를로 잡음 탓으로 돌릴 수 있는가"
# --------------------------------------------------------------------------- #
def add_disattenuation(J):
    """⭐ 잡음을 **완전히** 걷어냈을 때의 두 엔진 상관 상한(disattenuated bound).

    모형: Sionna 시드 i 의 AC 파형 x_i = s + n_i  (s = 재현되는 참 파형, n_i 는 독립·등분산).
        시드쌍 상관        r  = |s|²/(|s|²+|n|²)              → SNR = r/(1−r)
        시드평균과 s 의 상관 = sqrt(K·SNR/(K·SNR+1))            (K = 시드 수)
        관측된 corr(ours, x̄) = corr(ours, s) · sqrt(K·SNR/(K·SNR+1))
    ⇒ corr_true = corr_obs / sqrt(K·SNR/(K·SNR+1))

    이 상한이 **여전히 낮으면** 불일치는 잡음이 아니라 **물리(엔진 차이)** 다.
    (우리 커널은 결정론적이라 우리 쪽 잡음 항은 없다 — 그 가정도 여기 적어 둔다.)"""
    for key, R in J.get("airframes", {}).items():
        for lab, S in (R.get("sionna") or {}).items():
            sr = (S or {}).get("seed_reproducibility") or {}
            r = sr.get("ac_corr_mean")
            K = len(S.get("seeds") or [])
            h = (R.get("headline") or {}).get(lab)
            if h is None:
                continue
            if r is None or not (0.0 < r < 1.0) or K < 2:
                h["disattenuation"] = dict(applicable=False,
                                           reason="시드쌍 상관 또는 시드 수가 부족")
                continue
            snr = r / (1.0 - r)
            att = math.sqrt(K * snr / (K * snr + 1.0))
            out = dict(applicable=True, seed_pair_corr=float(r), n_seeds=int(K),
                       implied_snr=float(snr), attenuation_factor=float(att),
                       note=("attenuation_factor 는 '시드평균이 참 파형을 얼마나 잘 대표하는가' 다. "
                             "1 에 가까우면 잡음은 이미 평균으로 지워졌고, 남은 불일치는 물리다."))
            for arm, v in (S.get("vs_our_kernel") or {}).items():
                c = v.get("ac_corr_abs")
                if c is not None:
                    out[f"{arm}_corr_disattenuated"] = float(min(1.0, c / att))
            h["disattenuation"] = out
            h["ours_vs_sionna_ac_corr_disattenuated"] = out.get(
                "po_spherical_bistatic_corr_disattenuated")
    return J


def add_blade_electrical_size(J):
    """⭐ 도플러 확산의 **실제** 상한은 f_tip 이 아니라 **블레이드의 전기적 크기**다.

    f_tip = 2·v_tip/λ 는 '팁에 점산란체가 하나 있다면' 의 운동학 상한이다. 실제 산란체는 길이
    L 의 블레이드이고, 그 각도폭 ~λ/(2L) 안에서만 위상정합이 되므로 L 이 λ 수준이면 플래시가
    **날카로워지지 않는다** → 스펙트럼이 f_tip 까지 못 간다. 그래서 prop_radius/λ 를 함께 남긴다
    (전부 physics 에 이미 있는 값의 비율이다 — 손으로 적을 숫자가 아니다)."""
    for key, R in J.get("airframes", {}).items():
        p = (R.get("physics") or {}).get("matched32") or {}
        lam = p.get("lambda_m")
        rr = p.get("prop_radius_m")
        if not lam or not rr:
            continue
        R["physics"]["blade_electrical_size"] = dict(
            prop_radius_m=float(rr), lambda_m=float(lam),
            prop_radius_over_lambda=float(rr / lam),
            flash_beamwidth_deg=float(np.degrees(lam / (2.0 * rr))),
            note_ko=("prop_radius/λ 가 1 언저리면 블레이드는 전기적으로 '점' 에 가깝다 — "
                     "플래시 각폭이 넓어 도플러가 f_tip 까지 퍼지지 않는다. "
                     "flash_beamwidth 는 λ/(2L) 의 각도 환산(거친 눈금)이다."))
    return J


def add_arm_cross_matrix(J):
    """⭐ **모든 팔 × Sionna** 의 AC 상관 행렬 — 저장된 파형에서 다시 만든다.

    `arms[...]['matched32']['wave']` 는 amp_db·phase_deg 를 그대로 갖고 있으므로 복소 파형을
    되살릴 수 있다(광선을 다시 쏘지 않는다). 본문 factor_comparison 은 대표 쌍만 담았는데,
    거기서 SBR 은 λ/12(저장소 기본) 하나뿐이라 **SBR 의 미수렴이 '가림 효과' 로 오독될** 수 있다.
    수렴된 λ/48 을 포함한 전 쌍을 여기서 채운다. 파생값이니 손으로 옮겨 적을 일이 없다."""
    def _w(d):
        if not d or "amp_db" not in d or "phase_deg" not in d:
            return None
        a = np.asarray(d["amp_db"], float)
        p = np.radians(np.asarray(d["phase_deg"], float))
        return 10.0 ** (a / 20.0) * np.exp(1j * p)

    for key, R in J.get("airframes", {}).items():
        out = {}
        for lab in (R.get("aspects") or {}):
            W = {}
            for name, a in (R.get("arms") or {}).items():
                if not name.startswith(f"{lab}/"):
                    continue
                v = _w(((a.get("matched32") or {}).get("wave")))
                if v is not None:
                    W[name.split("/", 1)[1]] = v
            sm = _w(((R.get("sionna") or {}).get(lab) or {}).get("wave_seed_mean"))
            if sm is not None:
                W["sionna"] = sm
            names = sorted(W)
            mat = {}
            for i, na in enumerate(names):
                for nb in names[i + 1:]:
                    mat[f"{na} | {nb}"] = compare(W[na], W[nb], na, nb)["ac_corr_abs"]
            po_ref = None
            if "po_spherical_bistatic" in W and "po_spherical_bistatic_refined" in W:
                po_ref = mat.get("po_spherical_bistatic | po_spherical_bistatic_refined")
            out[lab] = dict(
                arms=names, ac_corr_pairs=mat,
                po_only_refine_corr=po_ref,
                note=("po_* 끼리는 점구름 이산화, sbr_div* 끼리는 광선격자 이산화 대조다. "
                      "sbr_div12 는 저장소 기본값이지만 얇은 블레이드에서는 수렴하지 않는다 — "
                      "'가림 효과' 를 논할 때는 반드시 수렴된 div 로 볼 것."))
        R["arm_cross_matrix"] = out
    return J


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drones", default=",".join(KEYS))
    ap.add_argument("--n-phase", type=int, default=N_PHASE)
    ap.add_argument("--n-fine", type=int, default=N_PHASE_FINE)
    ap.add_argument("--divs", default=",".join(str(d) for d in SBR_DIVS))
    ap.add_argument("--no-range", action="store_true")
    ap.add_argument("--no-fine", action="store_true")
    ap.add_argument("--quick", action="store_true")
    #  ⭐ 이미 만든 JSON 에 **파생 절**(disattenuation · 팔 교차행렬)만 다시 채운다. 광선을 다시
    #     쏘지 않는다 — 파생값은 전부 저장된 파형에서 나오므로 결과가 달라지지 않는다.
    ap.add_argument("--post-only", action="store_true")
    a = ap.parse_args()

    if a.post_only:
        with open(OUT_JSON) as f:
            Jp = json.load(f)
        add_disattenuation(Jp)
        add_arm_cross_matrix(Jp)
        add_blade_electrical_size(Jp)
        Jp["meta"]["post_stamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(OUT_JSON, "w") as f:
            json.dump(_j(Jp), f, ensure_ascii=False, indent=1)
        print(f"✅ 파생 절 갱신 → {OUT_JSON}")
        return Jp

    divs = tuple(int(x) for x in a.divs.split(",") if x.strip())
    n_phase, n_fine = int(a.n_phase), int(a.n_fine)
    if a.quick:
        n_phase, n_fine, divs = 16, 32, divs[:2]

    with open(PROBE_JSON) as f:
        J_probe = json.load(f)

    t0 = time.time()
    J = dict(meta=dict(
        script="benchmark/report15_po_control.py",
        role=("대조군 A — report15_probe.py 와 **완전히 같은 격자**에 우리 산란 커널(PO/SBR)을 "
              "넣는다. 바뀌는 것은 엔진 하나뿐이다."),
        question=("스톡 Sionna PathSolver 가 못 낸 블레이드 마이크로도플러를, 같은 위상 스텝에서 "
                  "표면적분 커널은 내는가 — 그리고 두 파형이 같은가."),
        observable=("우리: E(φ) = PO/SBR 복소 산란장 [m²] (구면파 팔은 exp(−jk(R_t+R_s)) 를 뺀 값). "
                    "Sionna: h(φ) = Σ a_p·exp(−j2πf_c·τ_p). 절대 스케일·기준위상이 다르므로 "
                    "**상수 복소배에 불변인 양**(AC 상관·dB ptp·하모닉 스펙트럼)만 비교한다."),
        fc_hz=FC, lambda_m=LAM, az_deg=AZ_DEG, el_deg=EL_DEG,
        range_m=RANGE_M, baseline_m=BASELINE_M,
        n_phase=n_phase, n_phase_fine=n_fine, phase_span_deg=360.0,
        matched_grid=("우리 128 격자의 인덱스 0,2,…,62 = φ 0…174.375° (5.625° 간격) "
                      "= Sionna 32 스텝과 동일"),
        sbr_divs=list(divs), po_disc_matched=PO_MATCHED, po_disc_refined=PO_REFINED,
        range_sweep_m=list(RANGE_SWEEP_M),
        thresholds=THRESH,
        engines=dict(
            po="src/microdoppler_nearfield.py — 평면파/구면파 PO, **가림 없음**, 바이스태틱 가능",
            sbr="src/rcs_sbr.py sbr_field — Mitsuba 광선 first-hit + PO 적분, **가림 있음**, 평면파 모노스태틱",
            sionna="benchmark/report15_probe.py — 스톡 sionna.rt.PathSolver (참조: outputs/report15_probe.json)"),
        limits_ko=[
            "PO 팔은 가림이 없다(설계). SBR 팔은 가림이 있으나 평면파·모노스태틱이라 "
            "Sionna 의 구면파·바이스태틱 기하와 정확히 같지는 않다 — 그 차이의 크기를 "
            "factor_comparison 에 수치로 남겼다.",
            "두 커널 모두 편파 미보존(복소 스칼라 E, 스칼라 |Γ|) — 저장소 전체 규약.",
            "PO/SBR 은 1차 산란만 쓴다(Sionna 쪽도 max_depth=1 이라 이 점은 대칭이다).",
            "matrice4e 는 R=3 m 에서 원거리장 미달(2D²/λ=8.26 m)이다. 구면파 팔은 그 조건에서 "
            "쓰라고 만든 것이지만, 여기 수치를 σ(RCS) 로 환산해 인용하면 안 된다.",
            "180° 주기 가정은 삼각분할 탓에 mm 수준에서 깨진다 — full128(360°) 스펙트럼의 "
            "power_frac_odd_harmonics 가 그 크기다."],
        probe_json=os.path.relpath(PROBE_JSON, ROOT),
        probe_stamp=J_probe["meta"].get("stamp"),
        gpu=os.environ.get("CUDA_VISIBLE_DEVICES", "?"),
        materials="production per-group (DRONE_GROUP_MAT) — Sionna 쪽과 동일 표",
        stamp=time.strftime("%Y-%m-%d %H:%M:%S")), airframes={})

    def _save():
        os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
        with open(OUT_JSON, "w") as f:
            json.dump(_j(J), f, ensure_ascii=False, indent=1)

    for key in [k.strip() for k in a.drones.split(",") if k.strip()]:
        spec = DRONES[key]
        print(f"\n══ {key} ({spec.name}) — 대조군 A ══", flush=True)
        R = run_airframe(key, J_probe, n_phase=n_phase, n_fine=n_fine, divs=divs,
                         do_range=not a.no_range, do_fine=not a.no_fine)
        J["airframes"][key] = R
        add_disattenuation(J)
        add_arm_cross_matrix(J)
        add_blade_electrical_size(J)
        def _p(v, fmt="%.2f"):
            return (fmt % v) if isinstance(v, (int, float)) else "n/a"
        for lab, h in R["headline"].items():
            print(f"    ▶ [{key}/{lab}] 우리 ptp={_p(h['our_ptp_db_matched32'])} dB "
                  f"(프롭 {_p(h['our_ptp_db_prop_matched32'])}) · edge="
                  f"{_p(h['our_edge_f_hz'], '%.0f')} Hz "
                  f"({_p(h['our_edge_over_f_tip'])}×f_tip) · "
                  f"이산화 AC corr={_p(h['refine_ac_corr_min'], '%.4f')} ‖ Sionna ptp="
                  f"{_p(h['sionna_ptp_db'])} dB · 시드 AC corr="
                  f"{_p(h['sionna_seed_ac_corr_mean'], '%.3f')} ‖ 두 엔진 AC corr="
                  f"{_p(h['ours_vs_sionna_ac_corr'], '%.3f')}", flush=True)
        _save()

    J["meta"]["seconds_total"] = float(time.time() - t0)
    _save()
    print(f"\n✅ 저장 → {OUT_JSON}   ({J['meta']['seconds_total']:.0f}s)")
    return J


if __name__ == "__main__":
    main()
