# -*- coding: utf-8 -*-
"""vmax_hardening.py — **헤드라인을 부수려는 시도**: v_max = λ·PRF/4 는 살아남는가
====================================================================================================

■ 공격 대상 (현 헤드라인)
    "패시브 수신기의 무모호 바이스태틱 시선속도는 상시 기준신호의 **반복률**이 정한다.
     v_max = λ·PRF/4.  5G SSB(50 Hz) → 1.07 m/s.  CPI 로는 못 고친다."

■ 이 스크립트의 임무는 **확인이 아니라 반증**이다.  심사자가 낼 탈출구를 하나씩 열어보고
  각각에 대해 "5G 를 구제하는가"를 숫자로 답한다.

    (a) 도플러 언폴딩 / 스태거 PRF            → §B
    (b) SSB 말고 5G 프레임의 다른 신호        → §C  ⭐ 가장 강한 공격
    (c) SS 버스트 안의 다중 빔                → §D
    (d) 긴 CPI + 운동보상 / TBD               → §E
    (e) 멀티스태틱 기하                       → §F
    (f) 캐리어 애그리게이션 / 다른 밴드       → §G
    (+) 식 자체의 정확성 (바이스태틱 cos(β/2)) → §A
    (+) ⭐ 대칭성 자기공격 — 같은 '상시' 잣대를 WiFi 에 대면 무슨 일이 나는가 → §H

■ 저장소 함수를 부른다(재구현 금지)
    freespace_scene.fs_params / target_pos / heading_velocity / folded_doppler /
                    nyquist_gate / blind_fractions / M_from_prf / cpi_feasibility / prf_hz
    waveforms.all_waveforms / PILOT_RATE_HZ
  새로 도입한 물리는 세 개뿐이고 전부 이 파일 안에서 정의·표시한다:
    ① 비균일 slow-time 격자의 도플러 점확산(NUDFT 주기도) — §B/§D
    ② 다중 RX 접힘격자의 유령해 탐색 — §F
    ③ 단일 버스트 주파수추정 CRLB — §D

■ 산출
    outputs/vmax_hardening.json      (그림 없음 — 그림 사양은 JSON `figure_specs` 에 적어둔다)

실행:  cd sionna2 && PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/vmax_hardening.py
       빠른 확인:  --smoke
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (os.path.join(_ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "4")

import numpy as np                                          # noqa: E402

import freespace_scene as fss                               # noqa: E402
from waveforms import PILOT_RATE_HZ                         # noqa: E402

C0 = fss.C0
OUT_JSON = os.path.join(_ROOT, "outputs", "vmax_hardening.json")

# --- 헤드라인이 쓰는 파형 상수 (저장소 단일 진리원에서 읽는다) ------------------------------- #
FC = {"W1": 5.21e9, "L1": 1.843e9, "G1": 3.5e9}             # experiment_freespace_range._BAND_BY_STD
LAM = {m: C0 / f for m, f in FC.items()}
PRF = {"W1": fss.prf_hz("wifi", "G1"), "L1": fss.prf_hz("lte", "G1"),
       "G1": fss.prf_hz("nr", "G1")}

# --- 장면 (report05/report13 헤드라인 셀과 동일) ---------------------------------------------- #
L_REF = fss.L_REF                 # 500 m
ALT_REF = fss.FS_ALT[0]           # 60 m
PHI_REF = fss.PHI_HEADLINE_DEG    # 90 deg
D_REF = 1000.0                    # 공통 거리
T_REF = fss.T_CPI_REF_S           # 0.1 s
V_SLOW, V_FAST = fss.FS_SPEED     # 5, 15 m/s

# 드론 속도 기준 (DJI 공개 스펙 — 값의 지위는 '제조사 스펙', 측정 아님)
DRONE_SPEED_MS = {"mini5pro_cruise": 6.0, "mini5pro_max_S": 19.0,
                  "mavic4pro_max_S": 25.0, "matrice4e_cruise": 15.0,
                  "typical_survey_transit": 12.0, "hover": 0.0}


# =========================================================================== #
#  공통 소도구
# =========================================================================== #
def v_max_mono(lam, prf):
    """모노스태틱 등가 무모호 속도 λ·PRF/4 [m/s].  헤드라인 식 그대로."""
    return float(lam) * float(prf) / 4.0


def bisector_h(d, phi, alt, L=L_REF):
    """수평 이등분선 벡터 크기 |(u1+u2)_h| — 수평비행 도플러의 기하계수.

    f_d = v·(u1+u2)/λ 이고 heading_velocity 는 수평만 만든다(freespace_scene 규약).
    따라서 헤딩 최대 도플러는 |f_d|_max = v·|(u1+u2)_h|/λ 다.
    모노스태틱 등가식 f_d = 2v/λ 는 |(u1+u2)_h| = 2 인 특수해다.
    """
    P = fss.target_pos(d, phi, L, alt)
    p = fss.fs_params(fss.FS_TX, fss.FS_RX(L), P, (0.0, 0.0, 0.0), C0 / 0.1)
    b = np.asarray(p["u1"], float) + np.asarray(p["u2"], float)
    return float(np.linalg.norm(b[..., :2], axis=-1)), float(np.asarray(p["beta"]))


def nudft_psd(t, w, fgrid, fd_true, amp=None, phase=None):
    """비균일 slow-time 격자의 **도플러 점확산**.

    y_k = amp_k · exp(j·phase_k) · exp(j2π f_d t_k)     (표적 응답, 잡음 없음)
    S(f) = |Σ_k conj(w_k) y_k exp(−j2π f t_k)|          (수신기가 쓰는 정합 가중 w)

    `amp`/`phase` 를 주면 송신 빔 등으로 생기는 **수신기가 모르는** 진폭·위상을 실어 보내고,
    `w` 는 수신기가 실제로 쓸 수 있는 가중(보통 1)을 준다.  둘이 다르면 부정합 손실과
    가짜 선이 생긴다 — 그것이 이 함수가 재려는 양이다.
    """
    t = np.asarray(t, float)
    a = np.ones_like(t) if amp is None else np.asarray(amp, float)
    ph = np.zeros_like(t) if phase is None else np.asarray(phase, float)
    y = a * np.exp(1j * ph) * np.exp(2j * np.pi * float(fd_true) * t)
    w = np.ones_like(t) if w is None else np.asarray(w, float)
    E = np.exp(-2j * np.pi * np.asarray(fgrid, float)[:, None] * t[None, :])
    return np.abs(E @ (np.conj(w) * y))


#  판정 기준 — 알리아스 억압 몇 dB 면 '풀렸다'고 할 것인가
#    검출 문턱 SNR 이 11.86 dB(⟨outputs/report13_freespace.json : solve.G1.snr90_db⟩)인 계에서
#    가짜 봉우리를 잡음변동 위로 안정적으로 가르려면 봉우리비가 10 dB 는 되어야 한다.
#    3~10 dB 는 '한계적'(표적이 문턱보다 그만큼 위일 때만), 3 dB 미만은 '못 푼다'.
UNFOLD_DB_STRONG = 10.0
UNFOLD_DB_MARGINAL = 3.0
SNR90_DB = 11.86143572621035          # ⟨outputs/report13_freespace.json : solve.G1.snr90_db⟩


def unfold_tier(rej_db):
    if not np.isfinite(rej_db):
        return "degenerate"
    if rej_db >= UNFOLD_DB_STRONG:
        return "unfolds"
    if rej_db >= UNFOLD_DB_MARGINAL:
        return "marginal"
    return "fails"


def alias_rejection_db(t, fgrid, fd_true, amp=None, phase=None, w=None, res_mult=1.5):
    """진짜 도플러 대비 **최강 가짜 봉우리**의 억압량 [dB].

    양수 = 진짜 봉우리가 이긴다(언폴딩 가능).  0 이하 = 가짜가 이긴다(언폴딩 실패).
    '진짜 근처'는 격자 전체 스팬의 분해능 1/span 의 `res_mult` 배로 정의한다.
    """
    t = np.asarray(t, float)
    span = float(t.max() - t.min())
    res = 1.0 / max(span, 1e-12)
    S = nudft_psd(t, w, fgrid, fd_true, amp=amp, phase=phase)
    fg = np.asarray(fgrid, float)
    near = np.abs(fg - float(fd_true)) <= res_mult * res
    if not near.any() or not (~near).any():
        return float("nan"), float("nan")
    s_true = float(S[near].max())
    s_ghost = float(S[~near].max())
    f_ghost = float(fg[~near][int(np.argmax(S[~near]))])
    if s_ghost <= 0:
        return float("inf"), f_ghost
    return float(20.0 * np.log10(s_true / s_ghost)), f_ghost


# =========================================================================== #
#  §A  식 감사 — 바이스태틱에서 λ·PRF/4 는 무엇의 특수해인가
# =========================================================================== #
def section_A_formula(smoke=False):
    """v_max = λ·PRF/4 는 |(u1+u2)_h| = 2 (모노스태틱·면내) 특수해다.

    일반형:  v_max(ψ 최악) = λ·PRF / (2·|(u1+u2)_h|) = λ·PRF / (4·cos(β/2)·cos δ_el)
    기하완화계수 G = 2/|(u1+u2)_h| ≥ 1 이므로 **헤드라인 식은 v_max 의 하한**이다.
    장면 격자에서 G 가 얼마나 커지는지 재고, 커지는 곳이 어디인지 본다.
    """
    ds = np.array([150., 200., 300., 500., 750., 1000., 1500., 2000., 3000., 5000.]) \
        if not smoke else np.array([200., 1000., 5000.])
    phis = np.linspace(0.0, 360.0, 12 if smoke else 36, endpoint=False)
    alts = (60.0, 120.0)
    rows = []
    for alt in alts:
        for d in ds:
            for phi in phis:
                h, beta = bisector_h(d, phi, alt)
                rows.append(dict(d_m=float(d), phi_deg=float(phi), alt_m=float(alt),
                                 beta_deg=beta, bisector_h=h, G=2.0 / max(h, 1e-9)))
    G = np.array([r["G"] for r in rows])
    beta = np.array([r["beta_deg"] for r in rows])
    ok = beta <= 90.0                                    # 스펙 §8.6 β 게이트 안쪽만
    vg = v_max_mono(LAM["G1"], PRF["G1"])

    def q(x, mask):
        x = x[mask]
        return dict(min=float(x.min()), p50=float(np.median(x)),
                    p90=float(np.percentile(x, 90)), max=float(x.max()))

    worst = rows[int(np.argmax(np.where(ok, G, -1)))]
    return dict(
        headline_form="v_max = lam*PRF/4",
        general_form="v_max = lam*PRF / (2*|(u1+u2)_h|) = lam*PRF / (4*cos(beta/2)*cos(delta_el))",
        special_case_of="|(u1+u2)_h| = 2, i.e. monostatic (beta=0) and in-plane (target at zero elevation)",
        headline_is="a LOWER BOUND on v_max; the geometric relief factor G = 2/|(u1+u2)_h| >= 1",
        relief_factor_G=dict(all_geometries=q(G, np.ones_like(ok, bool)),
                             beta_le_90_only=q(G, ok)),
        v_max_G1_ms=dict(headline=vg,
                         median_over_scene=float(vg * np.median(G[ok])),
                         best_in_scene=float(vg * G[ok].max()),
                         best_geometry=worst),
        at_reference_cell=dict(d_m=D_REF, phi_deg=PHI_REF, alt_m=ALT_REF,
                               bisector_h=bisector_h(D_REF, PHI_REF, ALT_REF)[0],
                               beta_deg=bisector_h(D_REF, PHI_REF, ALT_REF)[1],
                               G=2.0 / bisector_h(D_REF, PHI_REF, ALT_REF)[0],
                               v_max_G1_ms=vg * 2.0 / bisector_h(D_REF, PHI_REF, ALT_REF)[0]),
        coupling_warning=("G 가 커지는 곳은 이등분선이 수직에 가까워지는 곳이다. 같은 곳에서 "
                          "|f_d| 자체가 줄어 0-도플러 가드에 더 잘 걸린다 — 완화와 블라인드가 "
                          "같은 방향으로 움직인다(공짜가 아니다)."),
        rescues_5g=False,
        verdict=("식은 고쳐야 한다(하한임을 명시). 그러나 β≤90° 장면 전체에서 G 중앙값 "
                 "%.3f, 최대 %.3f 라 v_max 는 최대 %.2f m/s 로만 오른다 — 구제 아님."
                 % (float(np.median(G[ok])), float(G[ok].max()), float(vg * G[ok].max()))),
    )


# =========================================================================== #
#  §B  탈출구 (a) — 도플러 언폴딩 / 스태거·비균일 PRF
# =========================================================================== #
def section_B_unfolding(smoke=False):
    """패시브 수신기는 송신기를 제어하지 못한다. 그러면 남는 길은 두 가지다.

      B1  **송신기가 이미 비균일**인 경우를 이용한다(SSB + 다른 상시 occasion 의 합집합).
      B2  그래도 남는 모호성은 무엇인가 — NUDFT 주기도로 가짜봉우리 억압량을 직접 잰다.

    핵심 물리: 표본 집합이 주기 T_p 로 되풀이되면 격자로브 간격은 1/T_p 로 고정되고,
    그 격자로브를 눌러 주는 것은 **한 주기 안의 개구(aperture)** 뿐이다. 한 주기 안 개구가
    T_a 면 억압은 |A(Δf)| 이고 Δf ≪ 1/T_a 이면 사실상 억압이 없다.
    """
    lam, prf = LAM["G1"], PRF["G1"]
    kgeo = bisector_h(D_REF, PHI_REF, ALT_REF)[0] / lam        # Hz per (m/s), 실제 기하
    T_obs = 1.0                                                # 관측창 1 s (M=50 for SSB)
    fmax = 1.2 * kgeo * 20.0                                   # ±20 m/s 를 덮는 도플러축
    fgrid = np.linspace(-fmax, fmax, 4001 if smoke else 24001)

    def grid_uniform(period, T=T_obs, off=0.0):
        n = int(np.floor(T / period))
        return off + np.arange(n) * period

    grids = {
        "ssb_20ms_uniform": dict(
            t=grid_uniform(0.020), desc="SSB only, ssb-periodicityServingCell = 20 ms (default)",
            legal=True, always_on=True),
        "ssb_5ms_uniform_best_legal": dict(
            t=grid_uniform(0.005), desc="SSB at the shortest legal period, 5 ms -> uniform 200 Hz",
            legal=True, always_on=True),
        "ssb_160ms_uniform_worst_legal": dict(
            t=grid_uniform(0.160), desc="SSB at the longest legal period, 160 ms -> uniform 6.25 Hz",
            legal=True, always_on=True),
        "ssb20_plus_trs20_offset10": dict(
            t=np.sort(np.concatenate([grid_uniform(0.020), grid_uniform(0.020, off=0.010)])),
            desc="SSB 20 ms + Rel-17 idle/inactive TRS 20 ms offset 10 ms -> UNIFORM 100 Hz",
            legal=True, always_on=False),
        "ssb20_plus_trs40_offset7": dict(
            t=np.sort(np.concatenate([grid_uniform(0.020), grid_uniform(0.040, off=0.007)])),
            desc="SSB 20 ms + TRS 40 ms offset 7 ms -> NON-uniform, period 40 ms",
            legal=True, always_on=False),
        "ssb20_plus_sib1_160ms": dict(
            t=np.sort(np.concatenate([grid_uniform(0.020), grid_uniform(0.160, off=0.013)])),
            desc="SSB 20 ms + SIB1 window 160 ms -> nearly uniform, period 160 ms",
            legal=True, always_on=True),
        "random_jitter_20ms_pm5ms": dict(
            t=np.sort(grid_uniform(0.020) + np.random.default_rng(0).uniform(-0.005, 0.005, 50)),
            desc="HYPOTHETICAL non-3GPP control experiment: 20 ms mean rate with +-5 ms random "
                 "jitter. Shows the CEILING of what non-uniformity alone could buy.",
            legal=False, always_on=False),
    }
    speeds = (2.0, 5.0, 15.0) if smoke else (1.5, 2.0, 5.0, 10.0, 15.0, 20.0)
    out = {}
    for name, g in grids.items():
        t = np.asarray(g["t"], float)
        per = {}
        for v in speeds:
            fd = kgeo * v
            rej, fgh = alias_rejection_db(t, fgrid, fd)
            per[f"v_{v:g}"] = dict(v_ms=float(v), fd_hz=float(fd),
                                   alias_rejection_db=float(rej),
                                   strongest_ghost_hz=float(fgh),
                                   ghost_v_ms=float(fgh / kgeo),
                                   tier=unfold_tier(rej))
        eff_prf = float(len(t) / (t.max() - t.min())) if len(t) > 1 else 0.0
        out[name] = dict(desc=g["desc"], legal_3gpp=bool(g["legal"]),
                         always_on=bool(g["always_on"]),
                         n_samples=int(len(t)),
                         span_s=float(t.max() - t.min()),
                         mean_rate_hz=eff_prf,
                         v_max_from_mean_rate_ms=float(eff_prf / (2.0 * kgeo)),
                         by_speed=per)
    return dict(
        question="Can a passive receiver stagger or unfold, given it does not control the TX?",
        receiver_control=dict(
            can_stagger_prf=False,
            why=("스태거 PRF 는 송신 타이밍을 바꾸는 기법이다. 패시브 수신기는 gNB 의 "
                 "ssb-periodicityServingCell 을 바꿀 수 없다. 남는 것은 '송신기가 이미 "
                 "비균일하게 보내고 있는가' 뿐이다."),
            can_choose_which_occasions_to_use=True,
            note="occasion 을 버리는 것은 표본을 줄일 뿐 알리아스 간격을 넓히지 못한다."),
        geometry=dict(d_m=D_REF, phi_deg=PHI_REF, alt_m=ALT_REF, L_m=L_REF,
                      fd_hz_per_ms=float(kgeo)),
        grids=out,
        mechanism=("한 주기 T_p 안의 개구 T_a 가 격자로브 억압을 정한다. SSB+TRS(40 ms) 조합은 "
                   "T_p=40 ms·T_a=20 ms 라 1/T_a=50 Hz 안쪽의 알리아스를 거의 못 누른다. "
                   "게다가 부분격자들이 서로 정수배로 정렬되는 주파수(예 150 Hz = 3×50 Hz)에서는 "
                   "억압이 사실상 0 이 된다 — 오프셋이 두세 개뿐이면 그런 정렬을 피할 수 없다."),
        criterion=dict(strong_db=UNFOLD_DB_STRONG, marginal_db=UNFOLD_DB_MARGINAL,
                       basis=f"detection threshold SNR90 = {SNR90_DB:.2f} dB "
                             f"⟨outputs/report13_freespace.json : solve.G1.snr90_db⟩"),
        rescues_5g=None,      # 아래 verdict 에서 수치로 결정
    )


# =========================================================================== #
#  §C  탈출구 (b) — SSB 말고 5G 프레임의 다른 신호  ⭐ 가장 강한 공격
# =========================================================================== #
def section_C_frame_inventory():
    """5G NR 하향링크 신호 원장 — **무엇이 진짜 상시인가**.

    각 항목: 반복률 범위 / 전형값 / 대역 / 누가 켜는가 / 패시브 수신기가 협조 없이 쓸 수 있는가.
    ⚠ 규격 사실의 지위: 아래 `spec_source` 는 3GPP 규격 지식에서 적었고 이 실행에서
      규격 원문과 기계 대조하지 않았다. 논문 인용 전 원문 확인이 필요하다(플래그 유지).
    """
    lam = LAM["G1"]

    def row(name, always_on, who, per_ms, typ_ms, bw_mhz, passive_usable, spec, note):
        lo, hi = (min(per_ms), max(per_ms)) if per_ms else (None, None)
        prf_hi = 1000.0 / lo if lo else None
        prf_lo = 1000.0 / hi if hi else None
        prf_typ = 1000.0 / typ_ms if typ_ms else None
        return dict(
            signal=name, always_on=always_on, configured_by=who,
            period_ms_range=[lo, hi], period_ms_typical=typ_ms,
            prf_hz_range=[prf_lo, prf_hi], prf_hz_typical=prf_typ,
            ref_bw_mhz=bw_mhz,
            v_max_ms_typical=(v_max_mono(lam, prf_typ) if prf_typ else None),
            v_max_ms_best=(v_max_mono(lam, prf_hi) if prf_hi else None),
            passive_usable_without_cooperation=passive_usable,
            spec_source=spec, note=note)

    inv = [
        row("SSB (PSS+SSS+PBCH+PBCH-DMRS)", True, "gNB cell config",
            [5, 10, 20, 40, 80, 160], 20, 7.2, "yes",
            "TS 38.331 ssb-periodicityServingCell; TS 38.213 §4.1 (UE assumes 20 ms for initial access)",
            "셀 정의 신호. 유휴 셀이 반드시 내보내는 유일한 하향 기준. 20 RB = 7.2 MHz @30 kHz SCS."),
        row("PBCH-DMRS", True, "gNB cell config", [5, 10, 20, 40, 80, 160], 20, 7.2, "yes",
            "TS 38.211 §7.4.1.4",
            "SSB 안에 있다. 독립 반복률이 없다 — 같은 occasion 에 실린다. 대역폭도 SSB 와 같다. "
            "버스트 안 심볼 수를 늘려줄 뿐 PRF 를 올리지 못한다."),
        row("SIB1 (CORESET#0 PDCCH + PDSCH)", True, "gNB cell config",
            [20, 160], 20, 34.6, "yes-after-decode",
            "TS 38.331 §5.2.1 (SIB1 periodicity 160 ms, repetitions within a 20 ms window)",
            "⭐ 대역폭은 SSB 의 4.8배(CORESET#0 최대 96 RB)지만 반복률은 SSB 와 같은 창(20 ms)에 "
            "묶인다. 즉 ΔR_b 는 개선하고 v_max 는 개선하지 못한다. 내용은 복호 후 재생성 가능. "
            "⚠ non-cell-defining SSB 를 쓰는 셀은 SIB1 을 보내지 않는다 — '항상'에 예외가 있다."),
        row("TRS (NZP-CSI-RS with trs-Info), connected UE", False, "gNB RRC, per UE",
            [10, 20, 40, 80], 20, 52.0, "no",
            "TS 38.214 §5.1.6.1.1 (trs periodicities {10,20,40,80} ms)",
            "연결 UE 전용 RRC 설정이다. 셀에 연결 UE 가 없으면 존재하지 않는다."),
        row("TRS occasions for idle/inactive UEs (Rel-17)", False, "gNB, optional, SIB17",
            [10, 20, 40, 80], 20, 52.0, "conditional",
            "TS 38.331 SIB17 / TS 38.214 Rel-17 available TRS",
            "⭐ 셀 고유·브로드캐스트라 패시브가 쓸 수 있는 유일한 SSB 외 후보. 그러나 **선택 기능**이라 "
            "켜져 있다는 보장이 없고, 최선 10 ms 라도 100 Hz 다."),
        row("NZP-CSI-RS (non-TRS)", False, "gNB RRC, per UE",
            [2, 320], 20, 100.0, "no",
            "TS 38.331 CSI-ResourcePeriodicityAndOffset (4..640 slots)",
            "UE 전용. 4 슬롯 @μ=1 = 2 ms 가 하한이라 최대 500 Hz 지만 협조 없이는 존재도 위치도 모른다."),
        row("DL-PRS", False, "LMF positioning session",
            [2, 10240], 5, 98.28, "no",
            "TS 38.331 DL-PRS-Periodicity (4..10240 slots)",
            "측위 세션 옵션. 우리 G2/G3 가 쓰는 200 Hz 가 여기다. 상시가 아니다."),
        row("PDCCH (Type0 CSS, tied to SSB)", True, "gNB cell config", [20, 160], 20, 34.6,
            "yes-after-decode", "TS 38.213 §13 (Type0-PDCCH CSS monitoring occasions)",
            "SSB 와 같은 occasion 에 묶인다. 새 반복률 없음."),
        row("PDCCH/PDSCH user traffic", False, "scheduler, load-dependent", None, None, 100.0,
            "conditional-on-load", "TS 38.214",
            "⭐ 복조-재변조(demod-remod) 로 재생성하면 사실상 연속 기준이 된다. 그러나 (i) 트래픽이 "
            "있어야 하고 (ii) UE 별 검색공간·C-RNTI 를 눈먼 복호로 뚫어야 하며 (iii) 유휴 셀에서는 0 이다. "
            "센서가 통제하지 못하는 양이다."),
        row("SRS / PRACH (uplink)", False, "UE", None, None, 100.0, "no",
            "TS 38.211 §6.4.1.4 / §6.3.3",
            "상향링크다. 송신점이 UE 라 조명 기하가 매 순간 바뀌고 위치를 모른다."),
    ]
    always = [r for r in inv if r["always_on"]]
    best_always = max(r["prf_hz_typical"] for r in always if r["prf_hz_typical"])
    # 20 m/s 를 무모호로 재려면 필요한 PRF
    prf_needed_20 = 4.0 * 20.0 / lam
    prf_needed_15 = 4.0 * 15.0 / lam
    return dict(
        question="Can a passive receiver use more of the 5G frame than SSB?",
        provenance_flag=("spec_source 필드는 3GPP 규격 지식으로 적었고 이 실행에서 원문 대조를 "
                         "하지 않았다. 논문 인용 전 TS 38.211/213/214/331 원문 확인 필요."),
        inventory=inv,
        always_on_set=[r["signal"] for r in always],
        highest_always_on_prf_hz=float(best_always),
        highest_always_on_v_max_ms=float(v_max_mono(lam, best_always)),
        bandwidth_vs_rate=dict(
            text=("SIB1/CORESET#0 은 기준 대역을 7.2 → 최대 34.6 MHz 로 넓혀 ΔR_b 를 41.6 → 8.7 m 로 "
                  "줄인다. 반복률은 SSB 와 같은 창에 묶여 그대로다. **대역과 반복률은 독립 축이고 "
                  "헤드라인은 반복률 축의 명제다.**"),
            ssb_dRb_m=float(C0 / 7.2e6), sib1_dRb_m=float(C0 / 34.6e6)),
        requirement=dict(
            prf_hz_needed_for_15ms=float(prf_needed_15),
            prf_hz_needed_for_20ms=float(prf_needed_20),
            text=("3.5 GHz 에서 15 m/s 를 무모호로 재려면 PRF ≥ %.0f Hz, 20 m/s 면 ≥ %.0f Hz 가 "
                  "필요하다. 상시 집합의 최고치는 %.0f Hz 다."
                  % (prf_needed_15, prf_needed_20, best_always))),
        deep_cause=dict(
            text=("NR 은 설계상 **셀 고유 상시 광대역 기준신호를 없앴다**(lean / ultra-lean carrier). "
                  "LTE 의 CRS 는 모든 하향 서브프레임에 있었고, NR 은 에너지 절감을 위해 그것을 "
                  "제거하고 필요할 때만 켜는 UE 전용 기준신호로 대체했다. 패시브 레이더가 겪는 "
                  "반복률 손실은 그 설계 선택의 직접 귀결이다."),
            spec_source="3GPP lean carrier design principle; TS 38.211 has no cell-specific RS analogue of LTE CRS",
            why_this_matters="'5G 가 나쁘다'가 아니라 '상시 기준을 없앤 설계가 패시브 센싱의 전제를 깬다'가 명제다."),
        neighbour_cells=dict(
            text=("이웃 gNB 의 SSB 는 시간 오프셋이 달라 합치면 표본이 늘어 보인다. 그러나 그것은 "
                  "**다른 위치의 송신기**라 바이스태틱 기하가 달라진다 — 한 slow-time 수열이 아니라 "
                  "멀티스태틱 송신 다이버시티다. 처리 구조와 대가는 §F 와 같다(연관 필요)."),
            counts_as_higher_prf=False),
        rescues_5g=False,
        verdict=("SSB 밖으로 나가도 **상시**인 것은 SIB1/CORESET#0 뿐이고 그것은 같은 20 ms 창에 "
                 "묶인다. 반복률을 올리는 후보(TRS·CSI-RS·PRS·트래픽)는 전부 설정 또는 부하에 의존한다. "
                 "Rel-17 유휴 TRS 가 켜진 최선의 셀에서도 100 Hz = 2.14 m/s 다. 구제 아님."),
    )


# =========================================================================== #
#  §D  탈출구 (c) — SS 버스트 안의 다중 빔
# =========================================================================== #
def _ssb_case_c_offsets(n_beam=8, scs_khz=30.0):
    """Case C(30 kHz SCS, f>3 GHz, L=8) SSB 후보의 **첫 심볼** → 시각 [s].

    첫 심볼 인덱스 {2,8} + 14n, n=0..3.  심볼길이 = 0.5 ms / 14 (30 kHz SCS).
    spec_source: TS 38.213 §4.1 Case C.  ⚠ 규격 원문 대조는 하지 않았다.
    """
    sym = np.array([s + 14 * n for n in range(4) for s in (2, 8)], float)[:n_beam]
    tsym = (1e-3 / (scs_khz / 15.0)) / 14.0
    return np.sort(sym) * tsym


def _ula_af(theta_deg, steer_deg, n_el=8, d_lam=0.5):
    """N소자 λ/2 ULA 배열인자 크기(정규화) — 빔 b 가 표적/기준 방향에서 갖는 이득."""
    th = np.radians(np.asarray(theta_deg, float))
    st = np.radians(np.asarray(steer_deg, float))
    psi = 2 * np.pi * d_lam * (np.sin(th)[..., None] - np.sin(st)[None, ...])
    num = np.sin(n_el * psi / 2.0)
    den = n_el * np.sin(psi / 2.0)
    out = np.where(np.abs(den) < 1e-12, 1.0, num / np.where(np.abs(den) < 1e-12, 1.0, den))
    return np.abs(out)


def section_D_beamsweep(smoke=False):
    """SS 버스트 안 L=8 빔이 '한 위치의 수신기'에게 PRF 를 올려주는가.

    세 층으로 나눠 본다.
      D1 기하   — 표적과 기준(RX)이 **같은 빔**에 들어와야 그 빔이 slow-time 표본이 된다.
      D2 파형   — 버스트 안 개구(약 1.7 ms)가 눌러줄 수 있는 알리아스 간격은 1/1.7 ms 규모다.
                   50 Hz 알리아스는 그 안쪽이라 억압이 사실상 없다.
      D3 추정   — 버스트 하나만으로 주파수를 재서 알리아스 번호를 정할 수 있는가(CRLB).
    """
    lam = LAM["G1"]
    kgeo = bisector_h(D_REF, PHI_REF, ALT_REF)[0] / lam
    off = _ssb_case_c_offsets()
    steer = np.linspace(-52.5, 52.5, 8)                    # 120° 섹터 8빔

    # --- D1 기하: 표적 방위 × 기준(RX) 방위 → 쓸 수 있는 빔 수 ------------------------------- #
    def usable(theta_t, theta_r, floor_db=-10.0):
        """빔 b 가 slow-time 표본이 되려면 **표적과 기준(RX)이 동시에** 그 빔 안에 있어야 한다.

        패시브 바이스태틱의 한 표본은 (기준채널 신호) × (표적 에코) 의 상관이라 빔 b 의 기여는
        곱이득 p_b = AF(θ_target; b) · AF(θ_ref; b) 에 비례한다.  두 각이 벌어지면 모든 b 에서
        p_b 가 함께 떨어진다 — 그래서 '실효 표본 수'와 '조명 예산'을 함께 재야 한다.
        """
        at = _ula_af(np.array([theta_t]), steer)[0]        # (8,)
        ar = _ula_af(np.array([theta_r]), steer)[0]
        p = at * ar
        keep = p / max(p.max(), 1e-15) >= 10 ** (floor_db / 20.0)
        p2 = p ** 2
        eff = float((p2.sum() ** 2) / max((p2 ** 2).sum(), 1e-30))   # 참여비 = 실효 표본 수
        # 조명 예산: 표적과 기준이 같은 방향일 때(한 빔 이득 1) 대비 총 곱전력
        budget_db = float(10.0 * np.log10(max(p2.sum(), 1e-30) / 1.0))
        return dict(theta_target_deg=float(theta_t), theta_ref_deg=float(theta_r),
                    n_beams_within_10dB=int(keep.sum()),
                    effective_beams=eff,
                    # ⚠ 아래 두 값은 '빔 수만큼 PRF 가 오른다'는 **소박한 읽기**다.
                    #    §D2 가 이것을 반증한다 — 버스트 안 표본은 등간격이 아니라 뭉쳐 있어서
                    #    무모호 구간을 넓히지 못하고 격자로브 간격은 20 ms 주기가 그대로 정한다.
                    naive_effective_prf_hz=float(50.0 * eff),
                    naive_v_max_ms_REFUTED_BY_D2=float(v_max_mono(lam, 50.0 * eff)),
                    illumination_budget_db_rel_one_aligned_beam=budget_db,
                    gains_target=[float(x) for x in at],
                    gains_ref=[float(x) for x in ar])

    d1 = {
        "aligned_on_beam_7.5deg": usable(7.5, 7.5),
        "aligned_between_beams_0deg": usable(0.0, 0.0),
        "target_0_ref_30": usable(0.0, 30.0),
        "target_20_ref_-40": usable(20.0, -40.0),
        "target_45_ref_-45": usable(45.0, -45.0),
    }
    d1_worst = min((v for k, v in d1.items() if not k.startswith("aligned")),
                   key=lambda v: v["illumination_budget_db_rel_one_aligned_beam"])

    # --- D2 파형: 버스트 개구가 50 Hz 알리아스를 얼마나 누르나 ------------------------------- #
    n_burst = 25 if smoke else 50                          # 1 s 관측 = 50 버스트
    t_multi = np.concatenate([b * 0.020 + off for b in range(n_burst)])
    t_single = np.arange(n_burst) * 0.020 + off[0]
    fmax = 1.2 * kgeo * 20.0
    fgrid = np.linspace(-fmax, fmax, 4001 if smoke else 24001)
    rng = np.random.default_rng(7)
    beam_phase = rng.uniform(-np.pi, np.pi, len(off))      # 수신기가 모르는 빔별 위상
    speeds = (5.0, 15.0) if smoke else (2.0, 5.0, 10.0, 15.0, 20.0)
    d2 = {}
    for v in speeds:
        fd = kgeo * v
        amp_flat = np.ones(len(t_multi))
        ph_flat = np.zeros(len(t_multi))
        ph_beam = np.tile(beam_phase, n_burst)
        # 현실적 진폭: 표적 0°, 기준 30° → 빔별 곱이득
        g = (_ula_af(np.array([0.0]), steer)[0] * _ula_af(np.array([30.0]), steer)[0])
        g = g / max(g.max(), 1e-15)
        amp_real = np.tile(g, n_burst)
        cases = {
            "single_beam_only": (t_single, None, None, None),
            "all8_coherent_equal_gain_IDEAL": (t_multi, amp_flat, ph_flat, None),
            "all8_realistic_gain_known_phase": (t_multi, amp_real, ph_flat, amp_real),
            "all8_realistic_gain_unknown_phase": (t_multi, amp_real, ph_beam, amp_real),
        }
        row = {}
        for cname, (tt, aa, pp, ww) in cases.items():
            rej, fgh = alias_rejection_db(tt, fgrid, fd, amp=aa, phase=pp, w=ww)
            row[cname] = dict(alias_rejection_db=float(rej),
                              strongest_ghost_hz=float(fgh),
                              ghost_v_ms=float(fgh / kgeo),
                              unfolds=bool(rej > 3.0))
        d2[f"v_{v:g}"] = dict(v_ms=float(v), fd_hz=float(fd), cases=row)

    burst_span = float(off.max() - off.min())
    # 버스트 개구가 50 Hz 에서 갖는 이득 (등이득·동위상 가정 상한)
    A = lambda f: np.abs(np.sum(np.exp(-2j * np.pi * f * off)))          # noqa: E731
    supp = {f"{int(k*50)}Hz": float(20 * np.log10(max(A(k * 50.0), 1e-12) / A(0.0)))
            for k in (1, 2, 3, 5, 10)}

    # --- D3 추정: 버스트 한 개로 알리아스 번호를 정할 수 있나 (CRLB) ------------------------- #
    def crlb_sigma_f(t, snr_lin):
        """등간격 아닌 표본에서 단일톤 주파수 추정 CRLB 표준편차 [Hz].
        sigma_f = 1 / (2*pi*sqrt(2*SNR_per_sample*N)*sigma_t),  sigma_t = 표본시각 표준편차."""
        t = np.asarray(t, float)
        N = len(t)
        st = float(np.std(t))
        return float(1.0 / (2 * np.pi * np.sqrt(2.0 * snr_lin * N) * max(st, 1e-12)))

    need_hz = PRF["G1"] / 6.0        # 알리아스 번호를 3σ 로 가르려면 σ_f < PRF/6
    d3 = {}
    for label, tt in (("one_SSB_4symbols", off[:4]), ("one_burst_all8", off)):
        st = float(np.std(tt)); N = len(tt)
        snr_lin = (1.0 / (2 * np.pi * need_hz * st)) ** 2 / (2.0 * N)
        # 검출 문턱에서 실제로 쓸 수 있는 표본당 SNR: 총 SNR90 을 M 표본에 나눈 값
        by_T = {}
        for T in (0.1, 0.5, 1.0):
            M = int(fss.M_from_prf(T, PRF["G1"]))
            snr1_db = SNR90_DB - 10.0 * np.log10(M)
            sig_burst = crlb_sigma_f(tt, 10 ** (snr1_db / 10.0))
            sig_comb = sig_burst / np.sqrt(M)          # 버스트별 추정을 비코히런트 평균
            by_T[f"T_{T:g}s"] = dict(
                M_bursts=M, snr_per_sample_db=float(snr1_db),
                sigma_f_one_burst_hz=float(sig_burst),
                sigma_f_combined_over_bursts_hz=float(sig_comb),
                resolves_alias_index=bool(sig_comb <= need_hz),
                snr_shortfall_db=float(20.0 * np.log10(max(sig_comb / need_hz, 1e-12))))
        d3[label] = dict(n_samples=int(N), span_s=float(tt.max() - tt.min()),
                         sigma_t_s=st,
                         sigma_f_needed_hz=float(need_hz),
                         snr_per_sample_needed_db=float(10 * np.log10(max(snr_lin, 1e-30))),
                         sigma_f_at_0dB_hz=crlb_sigma_f(tt, 1.0),
                         sigma_f_at_10dB_hz=crlb_sigma_f(tt, 10.0),
                         sigma_f_at_20dB_hz=crlb_sigma_f(tt, 20.0),
                         at_detection_threshold=by_T,
                         assumptions=("모든 빔이 등이득·동위상이라는 물리적으로 성립하지 않는 상한 "
                                      "(D1·D2 가 이 가정을 깬다). 표본당 SNR 은 총 검출문턱 "
                                      f"{SNR90_DB:.2f} dB 를 M 표본에 나눈 값이다."))

    return dict(
        question="Does SSB beam sweeping raise the effective PRF for a receiver at one location?",
        model=dict(case="Case C, 30 kHz SCS, f>3 GHz, L=8",
                   ssb_offsets_s=[float(x) for x in off],
                   burst_span_s=burst_span,
                   array="8-element half-wavelength ULA, 8 beams over a 120 deg sector",
                   spec_source="TS 38.213 §4.1 Case C (SSB candidate first symbols {2,8}+14n)",
                   provenance_flag="규격 원문 대조 미실시"),
        D1_geometry=dict(
            text=("패시브 바이스태틱은 **기준 채널과 표적 에코가 같은 송신 빔에서 나와야** 그 빔을 "
                  "slow-time 표본으로 쓸 수 있다. 표적과 RX 가 다른 방위에 있으면 그 곱이득이 "
                  "빔마다 급락한다 — 빔 스위핑은 PRF 를 올리기는커녕 사용 가능한 조명을 쪼갠다."),
            worst_illumination_budget_db=float(
                d1_worst["illumination_budget_db_rel_one_aligned_beam"]),
            worst_case_key=[k for k, v in d1.items() if v is d1_worst][0],
            tradeoff=("표적과 기준이 벌어진 기하에서 실효 빔 수는 %.2f 로 늘어 보이지만 조명 예산은 "
                      "%.1f dB 깎인다. 그리고 그 '실효 빔 수' 조차 무모호 속도를 올리지 못한다 — §D2."
                      % (d1_worst["effective_beams"],
                         d1_worst["illumination_budget_db_rel_one_aligned_beam"])),
            cases=d1),
        D2_waveform=dict(
            text=("버스트가 주기 20 ms 로 되풀이되므로 격자로브 간격은 50 Hz 로 고정된다. 그것을 "
                  "눌러주는 것은 버스트 안 개구 %.2f ms 뿐이고 1/개구 = %.0f Hz 라 50 Hz 알리아스는 "
                  "주엽 안쪽이다." % (burst_span * 1e3, 1.0 / burst_span)),
            burst_aperture_s=burst_span,
            aperture_null_hz=float(1.0 / burst_span),
            ideal_alias_suppression_db=supp,
            by_speed=d2),
        D3_single_burst_estimation=d3,
        D3_text=("버스트 안 표본만 쓰면 모호는 없다(간격 %.0f µs → 무모호 ±%.0f Hz). 대신 분해능이 "
                 "1/개구 = %.0f Hz 로 거칠어져 알리아스 번호를 가르려면 SNR 이 필요하다. 검출 문턱 "
                 "%.2f dB 에서 8빔 이상상한 추정기는 %.1f dB 부족하다 — 즉 문턱보다 그만큼 위인 "
                 "표적(≈R90 의 %.2f배 거리 안)에서만 성립하고, 그것도 8빔 등이득·동위상 가정 위에서다."
                 % (float(np.diff(off).min()) * 1e6, 0.5 / float(np.diff(off).min()),
                    1.0 / burst_span, SNR90_DB,
                    d3["one_burst_all8"]["at_detection_threshold"]["T_1s"]["snr_shortfall_db"],
                    10 ** (-d3["one_burst_all8"]["at_detection_threshold"]["T_1s"]["snr_shortfall_db"] / 40.0))),
        rescues_5g=False,
        verdict=("빔 스위핑은 구제하지 않는다. (1) 표적과 기준이 같은 빔에 있어야 해서 벌어진 기하에서 "
                 "조명 예산이 %.1f dB 깎이며, (2) 등이득·동위상이라는 물리적으로 "
                 "불가능한 상한을 줘도 버스트 개구가 50 Hz 알리아스를 %.2f dB 밖에 못 누르고, "
                 "(3) 빔 가중은 수신기가 모르는 위상을 실어 코히런트 결합 자체를 깬다(억압 %.1f dB → "
                 "가짜가 이긴다). ⭐ 핵심은 (2) 다 — 버스트 안 표본은 뭉쳐 있어 무모호 구간을 넓히지 "
                 "못한다. 알리아스 간격은 빔 수가 아니라 **버스트 주기 20 ms** 가 정한다."
                 % (d1_worst["illumination_budget_db_rel_one_aligned_beam"],
                    supp["50Hz"],
                    d2[f"v_{(15.0 if not smoke else 15.0):g}"]["cases"]
                      ["all8_realistic_gain_unknown_phase"]["alias_rejection_db"])),
    )


# =========================================================================== #
#  §E  탈출구 (d) — 긴 CPI + 운동보상 / TBD
# =========================================================================== #
def section_E_long_cpi(smoke=False):
    """블라인드(검출 손실)와 모호(속도 추정)를 **분리**한다.

      E1  blind_hard(T) — CPI 로 줄어든다.  점근 2·g/M = 2·g/(T·PRF).
      E2  alias_frac(T) — CPI 와 무관.
      E3  Keystone/RFT 류 운동보상은 **거리 워크**를 단서로 쓴다. 5G SSB 는 ΔR_b=41.6 m 라
          그 단서가 CPI 안에 생기지 않는다. 필요 CPI 와 코히런스 한계를 나란히 놓는다.
      E4  TBD across aliases — 기동하면 알리아스 번호가 바뀐다. 헤딩 스윕에서 몇 번 바뀌나.
    """
    psi = np.linspace(0.0, 360.0, 720, endpoint=False)
    Tg = np.array([0.05, 0.1, 0.2, 0.5, 1.0, 2.0]) if smoke else \
        np.array([0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0])
    e1 = {}
    for m in ("W1", "L1", "G1"):
        rows = []
        for T in Tg:
            M = fss.M_from_prf(T, PRF[m])
            fr = fss.blind_fractions(psi, PHI_REF, D_REF, L_REF, ALT_REF, T,
                                     PRF[m], V_SLOW, LAM[m], M=M)
            rows.append(dict(T_cpi_s=float(T), M=int(M),
                             blind_hard=float(fr["blind_hard"]),
                             alias_frac=float(fr["alias_frac"]),
                             asymptote_2g_over_M=float(min(1.0, 2 * 1.5 / M))))
        e1[m] = rows

    # E1b — 거리에 따른 blind_hard 산포 (cpi_guard_sweep 이 인용한 0.636 과의 대조)
    e1b = {}
    for m in ("W1", "L1", "G1"):
        rows = []
        for d in (500., 1000., 2000., 4000., 6301.062944411723):
            M = fss.M_from_prf(T_REF, PRF[m])
            fr = fss.blind_fractions(psi, PHI_REF, d, L_REF, ALT_REF, T_REF,
                                     PRF[m], V_SLOW, LAM[m], M=M)
            rows.append(dict(d_m=float(d), blind_hard=float(fr["blind_hard"]),
                             alias_frac=float(fr["alias_frac"])))
        e1b[m] = dict(by_range=rows,
                      blind_hard_min=float(min(r["blind_hard"] for r in rows)),
                      blind_hard_max=float(max(r["blind_hard"] for r in rows)))

    # E5 — ⭐ 운영적으로 의미 있는 양: **검출되고 동시에 무모호한** 헤딩 비율
    speeds = np.array([0.0, 0.5, 1.0, 2.0, 5.0, 10.0, 15.0, 20.0, 25.0])
    e5 = {}
    for m in ("W1", "L1", "G1"):
        for T in (T_REF, 1.0):
            rows = []
            M = fss.M_from_prf(T, PRF[m])
            g_hz = 1.5 * PRF[m] / M
            for v in speeds:
                V = fss.heading_velocity(psi, float(v))
                P0 = fss.target_pos(D_REF, PHI_REF, L_REF, ALT_REF)
                p = fss.fs_params(fss.FS_TX, fss.FS_RX(L_REF), P0, V, FC[m])
                fd = np.asarray(p["fd"], float)
                unamb = fss.nyquist_gate(fd, PRF[m])
                det = np.abs(fss.folded_doppler(fd, PRF[m])) >= g_hz
                rows.append(dict(v_ms=float(v),
                                 detectable_frac=float(det.mean()),
                                 unambiguous_frac=float(np.mean(unamb)),
                                 detectable_and_unambiguous_frac=float(np.mean(det & unamb))))
            e5[f"{m}_T{T:g}"] = dict(mode=m, T_cpi_s=float(T), M=int(M), by_speed=rows)

    # E3 — 거리 워크로 알리아스 번호를 풀 수 있나
    B_ref = {"W1": 76.5625e6, "L1": 17.985e6, "G1": 7.2e6}   # waveforms.ref_bw_hz
    e3 = {}
    for m in ("W1", "L1", "G1"):
        dRb = C0 / B_ref[m]
        for v in (V_SLOW, V_FAST):
            # CPI 동안의 바이스태틱 거리 이동(헤딩 최대) — fs_params 로 실제 궤적을 푼다
            V = fss.heading_velocity(psi, v)
            P0 = fss.target_pos(D_REF, PHI_REF, L_REF, ALT_REF)
            def walk(T):
                t = np.array([-0.5 * T, 0.5 * T])
                P = P0[None, None, :] + V[:, None, :] * t[None, :, None]
                p = fss.fs_params(fss.FS_TX, fss.FS_RX(L_REF), P, V[:, None, :], FC[m])
                Rb = np.asarray(p["Rb"], float)
                return float(np.abs(Rb[:, 1] - Rb[:, 0]).max())
            # 워크 = 1 거리셀이 되는 CPI 를 이분법으로
            lo, hi = 0.01, 600.0
            for _ in range(60):
                mid = np.sqrt(lo * hi)
                if walk(mid) < dRb: lo = mid
                else: hi = mid
            T_walk = float(np.sqrt(lo * hi))
            # 도플러 코히런스 한계: CPI 안 f_d 변화 < 한 빈 (PRF/M)
            def dfd(T):
                t = np.linspace(-0.5 * T, 0.5 * T, 9)
                P = P0[None, None, :] + V[:, None, :] * t[None, :, None]
                p = fss.fs_params(fss.FS_TX, fss.FS_RX(L_REF), P, V[:, None, :], FC[m])
                fd = np.asarray(p["fd"], float)
                return float((fd.max(axis=1) - fd.min(axis=1)).max())
            lo, hi = 0.01, 600.0
            for _ in range(60):
                mid = np.sqrt(lo * hi)
                if dfd(mid) < PRF[m] / fss.M_from_prf(mid, PRF[m]): lo = mid
                else: hi = mid
            T_coh = float(np.sqrt(lo * hi))
            e3[f"{m}_v{v:g}"] = dict(
                mode=m, v_ms=float(v), dRb_res_m=float(dRb),
                T_cpi_for_one_range_cell_walk_s=T_walk,
                T_cpi_doppler_coherence_limit_s=T_coh,
                ratio_required_over_coherent=float(T_walk / max(T_coh, 1e-12)),
                keystone_feasible=bool(T_walk <= T_coh))

    # E4 — 기동 중 알리아스 번호 전이 횟수
    e4 = {}
    for m in ("W1", "L1", "G1"):
        for v in (V_SLOW, V_FAST):
            V = fss.heading_velocity(psi, v)
            P0 = fss.target_pos(D_REF, PHI_REF, L_REF, ALT_REF)
            p = fss.fs_params(fss.FS_TX, fss.FS_RX(L_REF), P0, V, FC[m])
            fd = np.asarray(p["fd"], float)
            n = np.rint(fd / PRF[m]).astype(int)
            e4[f"{m}_v{v:g}"] = dict(
                mode=m, v_ms=float(v),
                alias_index_range=[int(n.min()), int(n.max())],
                n_distinct_alias_indices=int(len(np.unique(n))),
                n_transitions_per_360deg_turn=int(np.count_nonzero(np.diff(np.r_[n, n[0]]))),
                fd_max_hz=float(np.abs(fd).max()))

    g1 = {r["T_cpi_s"]: r["blind_hard"] for r in e1["G1"]}
    return dict(
        question="Does a longer CPI with motion compensation, or track-before-detect, rescue 5G?",
        E1_blindness_falls_with_cpi=e1,
        E1b_range_spread=e1b,
        E1b_reconciliation=(
            "cpi_guard_sweep 가 인용한 blind_hard(G1, T=0.1 s) = 0.636 은 d = R90 = 6301 m 셀의 값이다. "
            "같은 규약을 d = 1000 m 에 적용하면 %.3f 이 나온다 — 접힘이 헤딩축을 여러 번 감기 때문에 "
            "정확한 비율이 기하에 민감하다(G1 산포 %.3f~%.3f). 논문에는 점근식 2·g/M 과 산포를 함께 써야 한다."
            % (g1[0.1], e1b["G1"]["blind_hard_min"], e1b["G1"]["blind_hard_max"])),
        E5_usable_heading_fraction=e5,
        E5_text=("검출 가능(가드 밖) **그리고** 무모호(|f_d| < PRF/2)인 헤딩 비율. 5G SSB 는 v 가 "
                 "v_max 를 넘는 순간 이 값이 0 으로 떨어진다 — 검출은 되지만 속도가 못 믿을 값이 된다. "
                 "호버(v=0)는 세 파형 모두 0 이다(0-도플러 가드)."),
        E1_law=("blind_hard → 2·g_bins/M = 2·g_bins/(T·PRF) — **접힘이 도플러를 무작위화하는 모드**의 "
                "점근값. 즉 검출 블라인드는 T·PRF 의 곱만 보므로 CPI 로 되살 수 있다."),
        E2_ambiguity_constant=("alias_frac 는 T 와 무관하다 — |f_d| ≥ PRF/2 는 표본화율 조건이다. "
                               "빈폭을 좁혀도 무모호 구간은 넓어지지 않는다."),
        E3_motion_compensation=e3,
        E3_text=("Keystone/RFT 로 알리아스 번호를 푸는 방법은 **거리 워크**를 단서로 쓴다. "
                 "5G SSB 는 기준대역 7.2 MHz → ΔR_b = 41.6 m 라 한 거리셀을 걸으려면 CPI 가 "
                 "코히런스 한계보다 훨씬 길어야 한다. 두 수를 나란히 놓으면 실현 불가가 읽힌다."),
        E4_track_before_detect=e4,
        E4_text=("TBD 는 알리아스 번호가 트랙 위에서 일정해야 성립한다. 360° 선회 한 번에 번호가 "
                 "여러 번 바뀌므로 5G 에서는 트랙 연속성 자체가 번호 전이로 끊긴다."),
        rescues_5g="partially — 검출 블라인드는 되살리지만 속도 모호는 못 푼다",
        verdict=("⭐ 헤드라인은 여기서 **정밀화되어야 한다**. 긴 CPI 는 blind_hard(G1) 를 %.3f(0.1 s) → "
                 "%.3f(1 s) 로 줄여 **검출을 되살린다**. 그러나 alias_frac 은 %.3f 로 고정이다. "
                 "즉 CPI 로 못 고치는 것은 '검출'이 아니라 '무모호 속도'다. Keystone/RFT 로 알리아스 "
                 "번호를 푸는 길도 5G 에서는 막힌다 — 한 거리셀을 걷는 데 필요한 CPI 가 도플러 코히런스 "
                 "한계의 %.2f배다."
                 % (g1[0.1], g1[1.0],
                    [r["alias_frac"] for r in e1["G1"]][0],
                    e3["G1_v15"]["ratio_required_over_coherent"])),
    )


# =========================================================================== #
#  §F  탈출구 (e) — 멀티스태틱 기하
# =========================================================================== #
def _n_clusters(pts, step, connect=1):
    """규칙격자 위 후보점의 **연결성분 개수** — 서로 다른 해가 몇 개인가.

    격자점 개수를 그대로 인용하면 격자를 촘촘히 할수록 유령이 늘어난 것처럼 보인다(분해능
    인공물). 정수 격자 좌표로 바꿔 8-이웃 flood fill 하면 격자 간격에 둔감한 양이 된다.
    """
    pts = np.asarray(pts, float)
    if len(pts) == 0:
        return 0
    idx = np.rint(pts / float(step)).astype(np.int64)
    todo = set(map(tuple, idx))
    nb = [(a, b) for a in range(-connect, connect + 1) for b in range(-connect, connect + 1)
          if (a, b) != (0, 0)]
    n = 0
    while todo:
        stack = [todo.pop()]
        n += 1
        while stack:
            i, j = stack.pop()
            for da, db in nb:
                k = (i + da, j + db)
                if k in todo:
                    todo.discard(k)
                    stack.append(k)
    return int(n)



def section_F_multistatic(smoke=False):
    """수신기를 여러 대 두면 알리아스가 풀리는가.

    같은 송신기를 보므로 **PRF 는 전 수신기 공통**이다. 그러나 접힘 계수 a_i = (u1+u2_i)_h/λ 는
    기하마다 다르다 → 접힘 격자가 서로 어긋난다. 이것은 '공간 스태거'다.

    F1 블라인드 : 모든 RX 가 동시에 블라인드일 확률.
    F2 모호     : 접힌 측정 m_i 를 동시에 만족하는 속도 유령해가 |v|≤25 m/s 안에 몇 개인가.
    """
    lam = LAM["G1"]
    prf = PRF["G1"]
    rx_sets = {
        "N1": [(L_REF, 0.0, 3.0)],
        "N2": [(L_REF, 0.0, 3.0), (0.0, L_REF, 3.0)],
        "N3": [(L_REF, 0.0, 3.0), (0.0, L_REF, 3.0), (-L_REF, 0.0, 3.0)],
        "N4": [(L_REF, 0.0, 3.0), (0.0, L_REF, 3.0), (-L_REF, 0.0, 3.0), (0.0, -L_REF, 3.0)],
        "N3_clustered_30m": [(L_REF, 0.0, 3.0), (L_REF, 30.0, 3.0), (L_REF, -30.0, 3.0)],
    }
    P0 = fss.target_pos(D_REF, PHI_REF, L_REF, ALT_REF)

    def coeff(rx):
        p = fss.fs_params(fss.FS_TX, rx, P0, (0.0, 0.0, 0.0), FC["G1"])
        b = np.asarray(p["u1"], float) + np.asarray(p["u2"], float)
        return b[:2] / lam                                    # (2,) Hz per (m/s)

    psi = np.linspace(0.0, 360.0, 360, endpoint=False)
    T = T_REF
    M = fss.M_from_prf(T, prf)
    g_hz = 1.5 * prf / M
    out = {}
    for name, rxs in rx_sets.items():
        A = np.stack([coeff(r) for r in rxs])                 # (N,2)
        # F1 — 전 RX 동시 블라인드
        blind_all = np.ones(len(psi), bool)
        blind_each = []
        for a in A:
            V = fss.heading_velocity(psi, V_SLOW)[:, :2]
            fd = V @ a
            fb = fss.folded_doppler(fd, prf)
            b = np.abs(fb) < g_hz
            blind_each.append(float(b.mean()))
            blind_all &= b
        # F2 — 유령해 탐색 (2D 속도벡터 격자) × 허용오차 스윕
        #    ⚠ N=1 은 방정식 1개·미지수 2개라 접힘이 없어도 속도**벡터**를 못 정한다.
        #      그 경우의 참된 모호량은 시선속도 1D 의 접힘주기 PRF/|a| 다(아래 radial 항).
        n_g = 121 if smoke else 401
        vx = np.linspace(-25.0, 25.0, n_g)
        VX, VY = np.meshgrid(vx, vx, indexing="ij")
        Vg = np.stack([VX.ravel(), VY.ravel()], axis=-1)      # (G,2)
        ghosts = []
        for v_true in ((V_FAST, 0.0), (0.0, V_FAST), (10.0, 10.0)):
            m_true = fss.folded_doppler(np.asarray(v_true) @ A.T, prf)     # (N,)
            fd_g = Vg @ A.T                                                # (G,N)
            resid = fss.folded_doppler(fd_g - m_true[None, :], prf)
            step = float(vx[1] - vx[0])
            by_tol = {}
            for tb in (0.25, 0.5, 1.0):
                tol = tb * (prf / M)
                ok = np.all(np.abs(resid) <= tol, axis=1)
                cand = Vg[ok]
                far = cand[np.linalg.norm(cand - np.asarray(v_true), axis=1) > 1.0]
                by_tol[f"tol_{tb:g}bin"] = dict(
                    n_grid_solutions=int(ok.sum()), n_ghost_grid_points=int(len(far)),
                    # ⭐ 격자·연결성에 둔감한 정본 지표: 속도탐색 상자에서 살아남은 부피 비율.
                    #    제약의 교집합이므로 N 이 늘면 **반드시** 줄어든다(단조).
                    ambiguity_volume_frac=float(ok.sum() / len(Vg)),
                    n_distinct_ghost_clusters=_n_clusters(far, step),
                    nearest_ghost_speed_error_ms=(
                        float(np.min(np.linalg.norm(far - np.asarray(v_true), axis=1)))
                        if len(far) else None),
                    unique=bool(len(far) == 0))
            ghosts.append(dict(v_true_ms=list(map(float, v_true)), by_tolerance=by_tol,
                               grid_step_ms=step,
                               unique_at_quarter_bin=by_tol["tol_0.25bin"]["unique"]))
        radial = [dict(rx_index=i,
                       fd_hz_per_ms=float(np.linalg.norm(a)),
                       radial_alias_period_ms=float(prf / np.linalg.norm(a)),
                       v_max_ms=float(0.5 * prf / np.linalg.norm(a)))
                  for i, a in enumerate(A)]
        # 기하 다양성 — 계수벡터 사이 최소 각
        ang = []
        for i in range(len(A)):
            for j in range(i + 1, len(A)):
                c = float(np.dot(A[i], A[j]) / (np.linalg.norm(A[i]) * np.linalg.norm(A[j])))
                ang.append(float(np.degrees(np.arccos(np.clip(c, -1, 1)))))
        out[name] = dict(n_rx=len(rxs), rx_positions=[list(map(float, r)) for r in rxs],
                         coeff_hz_per_ms=[[float(x) for x in a] for a in A],
                         min_pairwise_angle_deg=(float(min(ang)) if ang else None),
                         blind_frac_each=blind_each,
                         blind_frac_all_simultaneously=float(blind_all.mean()),
                         product_of_individual=float(np.prod(blind_each)),
                         radial_ambiguity_per_rx=radial,
                         ambiguity=ghosts)
    spread = {k: v for k, v in out.items() if k.startswith("N") and "cluster" not in k}
    clusters = {k: max(g["by_tolerance"]["tol_0.25bin"]["n_distinct_ghost_clusters"]
                       for g in v["ambiguity"]) for k, v in spread.items()}
    clusters_1bin = {k: max(g["by_tolerance"]["tol_1bin"]["n_distinct_ghost_clusters"]
                            for g in v["ambiguity"]) for k, v in spread.items()}
    vol = {tb: {k: max(g["by_tolerance"][f"tol_{tb}bin"]["ambiguity_volume_frac"]
                       for g in v["ambiguity"]) for k, v in out.items()}
           for tb in ("0.25", "1")}
    return dict(
        question="Do several receivers resolve the alias?",
        setup=dict(T_cpi_s=T, M=int(M), guard_hz=float(g_hz), prf_hz=float(prf),
                   speed_ms=float(V_SLOW),
                   note="PRF is common to all receivers (single transmitter); only the geometric "
                        "coefficient a_i differs. This is a SPATIAL stagger."),
        by_set=out,
        canonical_metric="ambiguity_volume_frac (속도탐색 상자에서 살아남은 부피 비율, N 에 단조감소)",
        ambiguity_volume_frac_by_set=vol,
        distinct_ghost_clusters_by_set=dict(at_quarter_bin=clusters, at_one_bin=clusters_1bin),
        cluster_count_caveat=("N=1 의 해집합은 **직선 다발**(1차원)이라 '덩어리 24개'는 직선 24개를 "
                              "뜻한다. N≥2 부터 해집합이 이산점이 되므로 덩어리 수는 N=1 과 직접 "
                              "비교하면 안 된다. 단조 비교는 ambiguity_volume_frac 으로 한다."),
        blind_all_by_set={k: float(v["blind_frac_all_simultaneously"]) for k, v in out.items()},
        tolerance_sensitivity=("허용오차를 1/4빈 → 1빈으로 넓히면(잡음 있는 실제 도플러 추정에 해당) "
                               "모호 부피가 %s → %s (N4) 로 커진다. 무잡음 판정의 유일성은 실제 유일성이 아니다."
                               % (f"{vol['0.25']['N4']:.2e}", f"{vol['1']['N4']:.2e}")),
        rescues_5g=("partially — 모호 부피를 %.2e(N1) → %.2e(N4) 로 줄이지만 1빈 허용오차에서는 "
                    "%.2e 로 되돌아가고 유령 덩어리 %d개가 남는다"
                    % (vol["0.25"]["N1"], vol["0.25"]["N4"], vol["1"]["N4"],
                       clusters_1bin.get("N4", -1))),
        cost=("(i) 표적이 N 개 수신기 전부에서 검출되어야 하고, (ii) 연관(association)이 선행해야 하며, "
              "(iii) 계수벡터가 각으로 벌어져야 한다 — 30 m 간격으로 뭉친 3대는 각분리 %.2f° 라 "
              "유령을 못 가른다(N1 과 같은 수준). 즉 '멀티스태틱'이 아니라 '넓게 벌린 멀티스태틱'이 조건이다."
              % out["N3_clustered_30m"]["min_pairwise_angle_deg"]),
        verdict=("⭐ 실질적 효과가 있는 유일한 탈출구다. 넓게 벌린 수신기를 1→4대로 늘리면 |v| ≤ 25 m/s "
                 "안의 모호 부피가 %.2e → %.2e 로 줄고, 전 수신기 동시 블라인드는 %.3f → %.3f 로 떨어진다. "
                 "그러나 (a) 무잡음 1/4빈 판정에서도 유령이 0 이 되지 않으며(덩어리 %d개), 도플러 추정오차 "
                 "1빈을 허용하면 모호 부피가 %.2e 로 되돌아가고, (b) 30 m 간격으로 뭉친 3대는 아무 도움이 "
                 "안 된다(동시 블라인드 %.3f — N1 과 같다), (c) 이것은 5G 를 구제하는 게 아니라 **모호를 "
                 "푸는 데 수신기 인프라를 더 요구한다**는 사실을 정량화한다 — LTE CRS 는 수신기 한 대로 "
                 "%.1f m/s 를 무모호로 낸다. 수신기 한 대의 시선속도 접힘주기는 여전히 %.2f m/s 다."
                 % (vol["0.25"]["N1"], vol["0.25"]["N4"],
                    out["N1"]["blind_frac_all_simultaneously"],
                    out["N4"]["blind_frac_all_simultaneously"],
                    clusters.get("N4", -1), vol["1"]["N4"],
                    out["N3_clustered_30m"]["blind_frac_all_simultaneously"],
                    v_max_mono(LAM["L1"], PRF["L1"]),
                    out["N1"]["radial_ambiguity_per_rx"][0]["radial_alias_period_ms"])),
    )


# =========================================================================== #
#  §G  탈출구 (f) — 밴드 / 캐리어 애그리게이션
# =========================================================================== #
def section_G_band(smoke=False):
    """λ 를 키우면 v_max 가 오른다. 얼마나 오르고, 그것이 PRF 결손 20배를 덮는가."""
    bands = {"n28 (700 MHz)": 0.7e9, "n8 (900 MHz)": 0.9e9, "n5 (850 MHz)": 0.85e9,
             "n3 (1800 MHz)": 1.8e9, "n1 (2100 MHz)": 2.1e9, "n41 (2500 MHz)": 2.5e9,
             "n78 (3500 MHz)": 3.5e9, "n79 (4700 MHz)": 4.7e9, "n257 (28 GHz)": 28.0e9}
    per = {}
    for name, fc in bands.items():
        lam = C0 / fc
        per[name] = dict(fc_hz=float(fc), lam_m=float(lam),
                         v_max_at_50Hz_ms=v_max_mono(lam, 50.0),
                         v_max_at_200Hz_ms=v_max_mono(lam, 200.0),
                         v_max_at_6p25Hz_ms=v_max_mono(lam, 6.25),
                         beats_lte_crs=bool(v_max_mono(lam, 50.0) >
                                            v_max_mono(LAM["L1"], PRF["L1"])))
    # 필요한 λ: 50 Hz 에서 15 m/s 를 내려면
    lam_needed = 4.0 * 15.0 / 50.0
    # CA / 이중밴드 CRT — 두 반송파는 접힘 주기가 다르다
    ca = {}
    grid = np.linspace(-25.0, 25.0, 2001 if smoke else 20001)
    for pair in (("n78 (3500 MHz)", "n28 (700 MHz)"), ("n78 (3500 MHz)", "n3 (1800 MHz)"),
                 ("n78 (3500 MHz)", "n79 (4700 MHz)")):
        l1, l2 = C0 / bands[pair[0]], C0 / bands[pair[1]]
        k1, k2 = 2.0 / l1, 2.0 / l2                    # 모노 등가 Hz per m/s
        res = {}
        for v_true in (5.0, 15.0):
            m1 = fss.folded_doppler(k1 * v_true, 50.0)
            m2 = fss.folded_doppler(k2 * v_true, 50.0)
            r1 = fss.folded_doppler(k1 * grid - m1, 50.0)
            r2 = fss.folded_doppler(k2 * grid - m2, 50.0)
            tol = 0.25 * (50.0 / fss.M_from_prf(T_REF, 50.0))
            ok = (np.abs(r1) <= tol) & (np.abs(r2) <= tol)
            cand = grid[ok]
            far = cand[np.abs(cand - v_true) > 0.5]
            res[f"v_{v_true:g}"] = dict(
                n_solutions=int(ok.sum()), n_ghosts=int(len(far)),
                nearest_ghost_ms=(float(far[np.argmin(np.abs(far - v_true))]) if len(far) else None),
                unambiguous_interval_ms=(float(np.min(np.abs(far - v_true))) if len(far)
                                         else float(grid.max() - v_true)))
        ca["+".join(pair)] = dict(lam1_m=float(l1), lam2_m=float(l2),
                                  v_amb_period_1_ms=float(l1 * 50.0 / 2.0),
                                  v_amb_period_2_ms=float(l2 * 50.0 / 2.0),
                                  by_speed=res)
    return dict(
        question="Does carrier aggregation or a different 5G band change lambda enough?",
        by_band=per,
        lam_needed_for_15ms_at_50Hz=float(lam_needed),
        fc_needed_for_15ms_at_50Hz_hz=float(C0 / lam_needed),
        text=("50 Hz 에서 15 m/s 를 무모호로 내려면 λ = %.2f m, 즉 반송파 %.0f MHz 가 필요하다 — "
              "5G 배치 밴드 어디에도 없다. 최저 밴드 n28(700 MHz)이 %.2f m/s 로 6.25배 올려주지만 "
              "LTE CRS 의 %.1f m/s 에는 여전히 못 미친다."
              % (lam_needed, C0 / lam_needed / 1e6, per["n28 (700 MHz)"]["v_max_at_50Hz_ms"],
                 v_max_mono(LAM["L1"], PRF["L1"]))),
        carrier_aggregation_crt=ca,
        ca_note=("두 성분반송파는 λ 가 달라 속도 접힘 주기가 다르다 → CRT 로 무모호 구간이 넓어진다. "
                 "조건: 같은 gNB(공통 클럭)·두 SSB 모두 검출·연관 성립·두 개의 RF 프론트엔드 "
                 "(n28 과 n78 은 한 400 MHz 창에 안 들어간다)."),
        rescues_5g="partially — 저밴드는 6.25배, CA-CRT 는 더 넓히지만 하드웨어를 더 요구한다",
        verdict=("λ 는 5G 의 PRF 결손 20배를 되사지 못한다. n28 로 6.25배까지 오르고 거기서 멈춘다. "
                 "CA-CRT 는 원리적으로 작동하지만 두 밴드 프론트엔드와 연관 문제를 새로 만든다."),
    )


# =========================================================================== #
#  §H  ⭐ 자기공격 — '상시' 잣대를 대칭으로 적용하면
# =========================================================================== #
def section_H_symmetry(smoke=False):
    """5G 에 'SSB 만 상시' 잣대를 대면, 같은 잣대를 WiFi 에도 대야 한다.

    WiFi 의 1000 Hz 는 **혼잡 AP 의 패킷률 가정**이지 규격이 보장하는 값이 아니다.
    규격이 보장하는 상시 신호는 **비콘**이고, 기본 비콘 주기는 100 TU = 102.4 ms → 9.766 Hz 다.
    (저장소도 이미 이 사실을 안다 — src/waveforms.py 주석 line 107.)
    """
    lam_w, lam_l, lam_g = LAM["W1"], LAM["L1"], LAM["G1"]
    beacon_hz = 1.0 / (100 * 1024e-6)
    floors = {
        "wifi_beacon_100TU": dict(prf_hz=float(beacon_hz), lam_m=float(lam_w),
                                  v_max_ms=v_max_mono(lam_w, beacon_hz),
                                  guaranteed=True,
                                  basis="IEEE 802.11 default beacon interval 100 TU = 102.4 ms"),
        "wifi_congested_ap_assumed": dict(prf_hz=1000.0, lam_m=float(lam_w),
                                          v_max_ms=v_max_mono(lam_w, 1000.0),
                                          guaranteed=False,
                                          basis="repo assumption (waveforms.PILOT_RATE_HZ wifi=1000, "
                                                "traffic-dependent free parameter, spec F9)"),
        "lte_crs_per_subframe": dict(prf_hz=float(PILOT_RATE_HZ["lte"]["CRS"]), lam_m=float(lam_l),
                                     v_max_ms=v_max_mono(lam_l, PILOT_RATE_HZ["lte"]["CRS"]),
                                     guaranteed=True,
                                     basis="CRS in every non-MBSFN downlink subframe (TS 36.211 §6.10.1); "
                                           "1 kHz counts one subframe as one slow-time sample — "
                                           "conservative, CRS occupies 4 OFDM symbols per subframe"),
        "nr_ssb_20ms": dict(prf_hz=float(PILOT_RATE_HZ["nr"]["PSS"]), lam_m=float(lam_g),
                            v_max_ms=v_max_mono(lam_g, PILOT_RATE_HZ["nr"]["PSS"]),
                            guaranteed=True,
                            basis="SSB burst set period 20 ms (default, TS 38.213 §4.1)"),
    }
    # WiFi 패킷률 감도 — 어디서 5G 를 앞지르나
    p_cross = 50.0 * lam_g / lam_w
    psi = np.linspace(0.0, 360.0, 720, endpoint=False)
    sens = []
    for p in ([9.766, 100.0, 1000.0] if smoke else [9.766, 10.0, 30.0, 74.42, 100.0, 300.0, 1000.0, 5000.0]):
        Mw = fss.M_from_prf(T_REF, p)
        fw = fss.blind_fractions(psi, PHI_REF, D_REF, L_REF, ALT_REF, T_REF, p,
                                 V_SLOW, lam_w, M=Mw)
        Mg = fss.M_from_prf(T_REF, PRF["G1"])
        fg = fss.blind_fractions(psi, PHI_REF, D_REF, L_REF, ALT_REF, T_REF, PRF["G1"],
                                 V_SLOW, lam_g, M=Mg)
        sens.append(dict(wifi_packet_rate_hz=float(p),
                         wifi_v_max_ms=v_max_mono(lam_w, p),
                         wifi_blind_hard=float(fw["blind_hard"]),
                         wifi_alias_frac=float(fw["alias_frac"]),
                         g1_blind_hard=float(fg["blind_hard"]),
                         ratio_G1_over_W1=float(fg["blind_hard"] / max(fw["blind_hard"], 1e-12)),
                         wifi_beats_5g=bool(v_max_mono(lam_w, p) >
                                            v_max_mono(lam_g, PRF["G1"]))))
    return dict(
        question="Does the 'ambient only' standard, applied symmetrically, still favour WiFi?",
        guaranteed_floor=floors,
        ranking_under_guaranteed_floor=sorted(
            [(k, v["v_max_ms"]) for k, v in floors.items() if v["guaranteed"]],
            key=lambda kv: -kv[1]),
        wifi_packet_rate_crossover_hz=float(p_cross),
        crossover_text=("WiFi 가 5G SSB 의 v_max 를 넘으려면 패킷률 > %.1f Hz 가 필요하다. "
                        "기본 비콘만 있는 유휴 AP 는 9.77 Hz 라 **5G 보다 나쁘다**." % p_cross),
        sensitivity=sens,
        multi_bssid_and_multi_ap=dict(
            text=("한 AP 가 BSSID 를 N 개 광고하면 비콘이 N 배로 나가고, 채널에 AP 가 여러 대면 "
                  "비콘이 더 잦아 보인다. 그러나 다른 AP 는 **다른 위치의 송신기**라 하나의 "
                  "slow-time 수열이 아니다(§F 의 멀티스태틱 문제로 넘어간다). 같은 AP 의 다중 "
                  "BSSID 만 PRF 를 진짜로 배수한다."),
            same_ap_multi_bssid_multiplies_prf=True,
            other_aps_multiply_prf=False),
        headline_ratio_is_contingent=("'5G 블라인드율은 WiFi 의 12.05배' 는 WiFi 패킷률 1000 Hz "
                                      "가정 위에서만 성립한다. 같은 '보장된 상시' 잣대를 대면 순위가 뒤집힌다."),
        implication=("⭐ 방어 가능한 명제는 '5G 가 나쁘다'가 아니라 **'상시 기준신호의 반복률이 "
                     "무모호 속도를 정하고, 그 반복률을 규격이 보장하는 조명원은 LTE CRS 뿐이다'** 다. "
                     "WiFi 는 트래픽이 있을 때만 좋고, 5G 는 측위 세션이 있을 때만 좋다."),
    )


# =========================================================================== #
#  종합
# =========================================================================== #
def build(smoke=False):
    t0 = time.time()
    A = section_A_formula(smoke)
    B = section_B_unfolding(smoke)
    C = section_C_frame_inventory()
    D = section_D_beamsweep(smoke)
    E = section_E_long_cpi(smoke)
    F = section_F_multistatic(smoke)
    G = section_G_band(smoke)
    H = section_H_symmetry(smoke)

    # B 의 판정을 수치에서 결정 — **3GPP 로 존재 가능한 격자만** 센다
    def _best(pred):
        b = -1e9
        for _n, g in B["grids"].items():
            if not pred(g):
                continue
            for _k, r in g["by_speed"].items():
                if r["v_ms"] >= 5.0:
                    b = max(b, r["alias_rejection_db"])
        return float(b)

    b_legal = _best(lambda g: g["legal_3gpp"])
    b_always = _best(lambda g: g["legal_3gpp"] and g["always_on"])
    b_hypo = _best(lambda g: not g["legal_3gpp"])
    B["best_alias_rejection_db_at_v_ge_5"] = dict(
        legal_3gpp=b_legal, legal_and_always_on=b_always, hypothetical_jitter_ceiling=b_hypo)
    B["rescues_5g"] = bool(b_legal >= UNFOLD_DB_STRONG)
    B["verdict"] = (
        "패시브는 스태거를 만들 수 없다 — ssb-periodicityServingCell 은 gNB 가 정한다. 송신기가 "
        "이미 만들어 준 비균일(SSB+TRS·SIB1 합집합)에서도 v ≥ 5 m/s 의 최대 알리아스 억압은 "
        "%.2f dB(상시 신호만 쓰면 %.2f dB)로 판정 기준 %.0f dB 에 한참 못 미친다. 3GPP 밖의 "
        "±5 ms 랜덤 지터를 가정한 통제실험조차 %.2f dB 에서 멈춘다 — 비균일성만으로는 못 푼다. "
        "실제로 v_max 를 올리는 것은 언폴딩이 아니라 **반복률 자체**다(SSB 5 ms 설정 = 200 Hz = "
        "4.28 m/s, Rel-17 유휴 TRS 병용 = 균일 100 Hz = 2.14 m/s)."
        % (b_legal, b_always, UNFOLD_DB_STRONG, b_hypo))

    lam_g, prf_g = LAM["G1"], PRF["G1"]
    verdict = dict(
        headline_under_test="v_max = lam * PRF / 4  (5G SSB: 1.07 m/s)",
        survives=True,
        survives_as="a statement about UNAMBIGUOUS VELOCITY, not about DETECTION",
        corrections_required=[
            dict(id="X1", what="식의 일반형",
                 text="v_max = lam*PRF/(4*cos(beta/2)*cos(delta_el)) 이고 lam*PRF/4 는 그 하한이다. "
                      "장면 격자(beta<=90 deg)에서 완화계수 중앙값 %.3f, 최대 %.3f."
                      % (A["relief_factor_G"]["beta_le_90_only"]["p50"],
                         A["relief_factor_G"]["beta_le_90_only"]["max"]),
                 source="§A"),
            dict(id="X2", what="'CPI 로 못 고친다'의 범위",
                 text="⭐ 검출 블라인드는 CPI 로 고쳐진다 — blind_hard(G1) %.3f @0.1 s → %.3f @1 s, "
                      "반면 alias_frac 은 %.3f 로 고정. 고쳐지지 않는 것은 무모호 속도뿐이다. "
                      "두 양을 분리해 써야 한다."
                      % ({r["T_cpi_s"]: r["blind_hard"] for r in
                          E["E1_blindness_falls_with_cpi"]["G1"]}[0.1],
                         {r["T_cpi_s"]: r["blind_hard"] for r in
                          E["E1_blindness_falls_with_cpi"]["G1"]}[1.0],
                         E["E1_blindness_falls_with_cpi"]["G1"][0]["alias_frac"]),
                 source="§E"),
            dict(id="X3", what="'모든 드론이 접힌다'",
                 text="접힘 ≠ 미검출이다. 접힌 표적도 잘못된 도플러 셀에서 검출된다 — 잃는 것은 "
                      "그 셀이 0-도플러 가드에 떨어질 때뿐이고 그 확률은 2*g/M 이다.",
                 source="§E"),
            dict(id="X4", what="⭐ WiFi 비교의 대칭성",
                 text="WiFi 1000 Hz 는 트래픽 가정이다. 규격이 보장하는 상시 신호는 비콘(9.77 Hz)이고 "
                      "그 경우 WiFi v_max = %.3f m/s 로 5G 보다 나쁘다. 교차 패킷률은 %.1f Hz."
                      % (v_max_mono(LAM["W1"], 1.0 / 0.1024), 50.0 * lam_g / LAM["W1"]),
                 source="§H"),
            dict(id="X5", what="멀티스태틱",
                 text="넓게 벌린 다중 수신기는 접힘 격자를 어긋나게 해 모호를 크게 줄인다(모호 부피 "
                      "%.2e → %.2e, N=1→4). '절대 못 푼다'로 쓰면 반박당한다 — 참인 문장은 "
                      "**'수신기 한 대로는 못 푼다'** 이고, 여러 대로도 도플러 추정오차 1빈에서는 "
                      "유령이 %d개 남는다."
                      % (F["ambiguity_volume_frac_by_set"]["0.25"]["N1"],
                         F["ambiguity_volume_frac_by_set"]["0.25"]["N4"],
                         F["distinct_ghost_clusters_by_set"]["at_one_bin"]["N4"]),
                 source="§F"),
            dict(id="X6", what="⭐ '5G 만의 문제'가 아니다",
                 text="WiFi 도 v_max=%.1f m/s 를 넘으면 접힌다 — 20 m/s 표적의 무모호 헤딩 비율은 "
                      "%.3f 다. 참인 명제는 파형 이름이 아니라 **λ·PRF 곱**에 대한 것이다."
                      % (v_max_mono(LAM["W1"], PRF["W1"]),
                         [r["unambiguous_frac"] for r in
                          E["E5_usable_heading_fraction"]["W1_T1"]["by_speed"]
                          if r["v_ms"] == 20.0][0]),
                 source="§E5"),
        ],
        escapes=dict(
            a_unfolding_stagger=dict(rescues=B["rescues_5g"], one_line=B["verdict"]),
            b_more_of_the_frame=dict(rescues=C["rescues_5g"], one_line=C["verdict"]),
            c_beam_sweep=dict(rescues=D["rescues_5g"], one_line=D["verdict"]),
            d_long_cpi_motion_comp=dict(rescues=E["rescues_5g"], one_line=E["verdict"]),
            e_multistatic=dict(rescues=F["rescues_5g"], one_line=F["verdict"]),
            f_band_carrier_aggregation=dict(rescues=G["rescues_5g"], one_line=G["verdict"]),
        ),
        configuration_dependence=dict(
            why_this_is_the_sharpest_attack=(
                "⭐ 1.07 m/s 는 **규격 상수가 아니라 설정 기본값**(SSB 20 ms)의 귀결이다. "
                "ssb-periodicityServingCell 은 {5,10,20,40,80,160} ms 를 갖고, 셀이 5 ms 로 "
                "설정되어 있으면 200 Hz = 4.28 m/s 다. 헤드라인 문장은 반드시 '기본 20 ms 주기에서' "
                "라는 조건절을 달아야 한다."),
            v_max_by_ssb_period={
                f"{p}ms": dict(prf_hz=float(1000.0 / p),
                               v_max_ms=v_max_mono(lam_g, 1000.0 / p),
                               covers_5ms_slow_flight=bool(v_max_mono(lam_g, 1000.0 / p) >= 5.0),
                               covers_15ms_transit=bool(v_max_mono(lam_g, 1000.0 / p) >= 15.0))
                for p in (5, 10, 20, 40, 80, 160)},
            even_best_legal_config_fails=(
                "가장 짧은 합법 주기 5 ms 에서도 v_max = %.2f m/s 로 저속비행 5 m/s 를 못 덮는다. "
                "즉 설정을 최선으로 가정해도 결론의 방향은 바뀌지 않고, 크기만 4배 완화된다."
                % v_max_mono(lam_g, 200.0)),
            unknown="상용 셀의 SSB 주기 분포는 우리가 측정하지 않았다 — X410 실측의 1순위 관측 항목.",
        ),
        strongest_true_statement=(
            "패시브 바이스태틱 수신기가 **수신기 한 대로** 얻는 무모호 시선속도는 상시 기준신호의 "
            "반복률과 반송파가 함께 정한다: v_max = lam*PRF/(4 cos(beta/2) cos(delta_el)). "
            "규격이 상시를 보장하는 하향 기준신호로 계산하면 LTE CRS %.1f m/s · 5G SSB %.2f m/s · "
            "WiFi 비콘 %.2f m/s 다. 즉 드론 속도대(5~20 m/s)를 모호 없이 덮는 상시 조명원은 "
            "LTE CRS 뿐이고, LTE 를 5G 로 갈아타는 인프라 전환이 그것을 없앤다."
            % (v_max_mono(LAM["L1"], PRF["L1"]), v_max_mono(lam_g, prf_g),
               v_max_mono(LAM["W1"], 1.0 / 0.1024))),
        infrastructure_framing=(
            "LTE CRS → 5G SSB 로 상시 기준의 반복률이 %.0f배 떨어지고, 무모호 속도는 %.1f → %.2f m/s "
            "로 %.0f배 줄어든다(반송파 차이까지 포함). 이것은 파형 품질이 아니라 **lean carrier 설계** "
            "의 귀결이며, 사업자의 LTE 종료 일정이 곧 패시브 드론 감시의 관측성 일정이 된다."
            % (PRF["L1"] / prf_g, v_max_mono(LAM["L1"], PRF["L1"]), v_max_mono(lam_g, prf_g),
               v_max_mono(LAM["L1"], PRF["L1"]) / v_max_mono(lam_g, prf_g))),
        what_would_falsify_this=[
            "SSB 를 5 ms 주기로 설정한 셀이 흔하다는 배치 통계 (그러면 4.28 m/s 로 오른다)",
            "Rel-17 유휴 TRS 가 상용 셀에서 기본 활성이라는 관측",
            "3.5 GHz 대에서 상시로 존재하는, SSB 보다 반복률 높은 브로드캐스트 신호의 발견",
            "넓게 벌린 다중 수신기를 논문의 기본 구성으로 채택 (그러면 모호는 해결되고 명제가 좁아진다)",
        ],
    )

    figure_specs = [
        dict(id="F1", question="Which ambient illuminator can measure drone speed without ambiguity?",
             plot="v_max = lam*PRF/4 as a bar/scatter over (WiFi beacon, WiFi busy, 5G SSB, "
                  "5G idle-TRS, 5G PRS, LTE CRS), with a shaded band for drone speeds 5-20 m/s",
             source="outputs/vmax_hardening.json : H_symmetry.guaranteed_floor, C_frame.inventory"),
        dict(id="F2", question="Does a longer CPI fix it?",
             plot="two curves vs CPI: blind_hard (falls) and alias_frac (flat) for W1/L1/G1",
             source="outputs/vmax_hardening.json : E_long_cpi.E1_blindness_falls_with_cpi"),
        dict(id="F3", question="Does beam sweeping raise the effective PRF?",
             plot="alias rejection (dB) vs target speed for single beam / ideal 8-beam / realistic 8-beam",
             source="outputs/vmax_hardening.json : D_beamsweep.D2_waveform.by_speed"),
    ]

    doc = dict(
        meta=dict(script="benchmark/vmax_hardening.py",
                  generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
                  question="v_max = lam*PRF/4 를 깨뜨릴 수 있는가 — 탈출구 (a)~(f) 전수 공격",
                  smoke=bool(smoke),
                  geometry=dict(L_m=L_REF, alt_m=ALT_REF, phi_deg=PHI_REF, d_m=D_REF,
                                T_cpi_ref_s=T_REF, speed_slow_ms=V_SLOW, speed_fast_ms=V_FAST),
                  waveform_constants={m: dict(fc_hz=FC[m], lam_m=LAM[m], prf_hz=PRF[m])
                                      for m in FC},
                  repo_functions_used=["freespace_scene.fs_params", "target_pos",
                                       "heading_velocity", "folded_doppler", "nyquist_gate",
                                       "blind_fractions", "M_from_prf", "prf_hz",
                                       "waveforms.PILOT_RATE_HZ"],
                  new_physics_introduced=["NUDFT Doppler point-spread (nudft_psd)",
                                          "multistatic fold-lattice ghost search (section_F)",
                                          "single-burst frequency CRLB (section_D.D3)"],
                  drone_speed_reference=DRONE_SPEED_MS,
                  runtime_s=None),
        A_formula=A, B_unfolding=B, C_frame=C, D_beamsweep=D,
        E_long_cpi=E, F_multistatic=F, G_band=G, H_symmetry=H,
        verdict=verdict, figure_specs=figure_specs,
    )
    doc["meta"]["runtime_s"] = float(time.time() - t0)
    return doc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    doc = build(a.smoke)
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print(f"[vmax_hardening] wrote {OUT_JSON}  ({doc['meta']['runtime_s']:.1f} s)")
    v = doc["verdict"]
    print("  헤드라인 생존:", v["survives"], "—", v["survives_as"])
    for k, e in v["escapes"].items():
        print(f"   {k:28s} rescues={e['rescues']}")
    print("  최강 참명제:", v["strongest_true_statement"][:120], "...")


if __name__ == "__main__":
    main()
