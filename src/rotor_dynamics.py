# -*- coding: utf-8 -*-
"""
rotor_dynamics.py — **로터 회전 랜덤성 한 자리** (2026-08-11)
==============================================================================
설계서: `docs/NOISE_AND_ROTOR_PLAN.md` §2 · 조사: `prior_work/rotor_randomness_survey.md`
수치 원장: `outputs/rotor_jitter_model.json` · 게이트: `benchmark/verify_rotor_dynamics.py`

무엇을 고치나 — 셋
-------------------
지금까지 우리 로터 모델은 이랬다(`benchmark/report07_hover_long.py:113-120`):

    stat  = 0.0022 * PATTERN[k]                      # ← ⚠ 임의로 박은 결정론적 패턴
    phi0  = 2π k / n                                  # ← ⚠ 결정론적
    rpm_t = rpm0 * (1 + stat + 0.0015·sin(2π·2.7·t + phi0))   # ← ⚠ 정현파 한 톤
    ang   = cumsum(360·rpm_t/60 · dt)                 # ✅ 이건 옳다 — 그대로 둔다

셋이 틀렸다.

① **정적 산포가 «분포» 가 아니라 «패턴» 이었다.** `[+1, −1, −0.55, +0.55]` 는 요 균형
   직관 한 줄이 근거의 전부이고, 시행을 아무리 반복해도 같은 배치가 나온다.
   문헌 앵커: arXiv:2506.00497 이 로터 각속도를 i.i.d. 𝒩(ω̄, σ²) 로 두고 상대 산포
   **0.99 %** 다. 우리 실기 로그 앵커는 **0.54 %**(실내 NeuroBEM) · **2.35 %**(야외 CODEV)
   다(`outputs/rotor_rpm_web_anchor.json`). ⇒ **가우시안 추출 + 시드**로 바꾼다.

② **흔들림의 «모양» 이 틀렸다.** 정현파 한 톤은 선을 ±f_m 간격 **빗살로 가르고**,
   랜덤 과정은 선을 **넓힌다**. 그리고 백색도 아니다 — 자세제어 루프가 만드는 변동이라
   **저주파 지배**가 물리적으로 강제된다(조사 §3):
       · 자세각 P 루프 교차 0.64 Hz(PX4 `MC_ROLL_P=4.0`) / 0.72 Hz(ArduPilot `ATC_ANG_*_P=4.5`)
       · 자이로 저역통과 20~40 Hz 가 명령의 상한을 정한다
       · 로터 1차 시상수 τ = 5~72 ms(코너 2.2~32 Hz)가 한 번 더 깎는다
   우리 실측 앵커의 지배 성분 **0.3~2.2 Hz** 가 그 물리와 정확히 맞는다.
   ⇒ **백색 가우시안에 1극 저역통과 = OU(Ornstein–Uhlenbeck) 과정**이 맞는 모양이다.
   백색이면 PRF(19.7 kHz)까지 평평한 흔들림을 넣게 되고, 그 rpm 을 적분하면 위상이
   **랜덤워크**가 되어 선폭이 무한히 넓어진다 — 명백히 틀린 모양이다.
   로터 관성(2극, τ_m = 12.5~25 ms)은 **옵션으로만** 둔다: 8~20 dB 짜리 세부이고
   우리 표적 기체의 τ_m 을 못 찾았다(조사 §7-7).

③ **t=0 에 네 로터가 정렬돼 있었다.** `articulated_fast.rotor_phases()` 의 주석 자신이
   «실제 기체는 그럴 이유가 없다» 고 적어 두었다. 문헌은 이미 무작위화한다 —
   Costa(arXiv:2504.05168) *"propellers usually have random initial azimuth angles
   (φ₀ₚ = 𝒰(0, 2π))"*, Cai(RADAR 2019) *"random angle shift"*.
   ⇒ θ_k(0) ~ 𝒰(0, 360/blades). ⭐분류 팔은 이미 하고 있고, 안 하던 곳은 호버 맵뿐이었다.

⛔ 기본값은 지금 그대로다
-------------------------
`PRESETS["legacy"]` 가 **현행 식을 글자 그대로** 재현한다(패턴·정현파·정렬). 인자를 안 주면
기존 원장과 **비트 동일**이고, 그것을 게이트로 증명한다(`verify_rotor_dynamics.py` G4/G5).

⚠ 이 모듈이 **하지 않는** 것 (정직성)
--------------------------------------
- **산란 진폭의 요동은 여전히 미모델**이다. White(IEEE TRS 2024)도 자백한다 —
  *"sidebands fluctuated … The simulation model presented in this paper does not attempt
  to model such fluctuations"*. 우리도 못 한다.
- **σ_w(시간 흔들림)에 마이크로도플러 문헌 선례가 없다.** arXiv:2506.00497 조차 로터별
  각속도를 시간에 대해 상수로 둔다. 근거는 **실기 로그뿐**이다. 리포트에서 «문헌이 한다»
  라고 쓰면 안 된다.
- **블레이드 플렉싱·피치 변화는 안 넣는다.** 원문 확인 범위에서 사례 0 건.
- **우리 표적 기체(Mavic 4 Pro · Matrice 4E)의 rpm 통계는 못 찾았다.** DJI 가 최신 DAT 를
  암호화한다. 프리셋의 σ 는 **다른 기체의 로그**에서 왔다. 자체 실측이 유일한 경로다.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, replace
from typing import Optional, Tuple

import numpy as np

# --------------------------------------------------------------------------- #
#  상수 — 전부 1차 출처가 있다
# --------------------------------------------------------------------------- #
#: 자세각 루프 교차주파수 [Hz]. PX4 `MC_ROLL_P=4.0 1/s` → 0.64 Hz,
#: ArduPilot `ATC_ANG_*_P=4.5 1/s` → 0.72 Hz 의 중간. 레짐(실내/야외)에 무관하다 —
#: **제어기가 정하는 값**이지 바람이 정하는 값이 아니다.
F_CTL_HZ = 0.7
#: OU 시상수 T = 1/(2π·f_ctl) [s]
TAU_CTL_S = 1.0 / (2.0 * np.pi * F_CTL_HZ)          # 0.22736 s

#: 로터 1차 시상수(2극, 옵션). RotorS/PX4 기본값 τ_up 1/80 · τ_dn 1/40 s.
TAU_MOTOR_RANGE_S = (0.0125, 0.025)

#: OU 를 만드는 성근 표본율 [Hz]. 두 번째 극(6~13 Hz)보다 한참 위라 손실이 없고,
#: 같은 시드·같은 창길이면 **PRF 를 바꿔도 같은 물리 실현**을 준다(스윕 비교가 성립한다).
COARSE_HZ = 200.0
_MIN_COARSE = 8          # 이보다 적으면 성근 격자를 포기하고 곧바로 만든다


# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class RotorJitter:
    """로터 회전 랜덤성 파라미터 묶음. **네 개**가 본체다(σ_s · σ_w · T · τ_m)."""

    name: str = "custom"
    static_sigma: float = 0.0            # σ_s — 로터간 정적 산포(상대)
    wobble_sigma: float = 0.0            # σ_w — 시간 흔들림 std(상대). 0 이면 끔
    tau_ctl_s: float = TAU_CTL_S         # OU 시상수 [s]
    tau_motor_s: Optional[float] = None  # 2극(로터 관성). None 이면 끔
    random_phase: bool = True            # θ_k(0) ~ 𝒰(0, 360/blades)
    #: legacy 전용 — (진폭, Hz) 정현파 한 톤. 주면 OU 대신 이것을 쓴다.
    legacy_sine: Optional[Tuple[float, float]] = None
    #: legacy 전용 — 결정론적 정적 패턴. 주면 가우시안 추출 대신 이것을 쓴다.
    static_pattern: Optional[Tuple[float, ...]] = None
    source: str = ""                     # 원장에 그대로 실을 근거 문자열

    # -- 편의 -------------------------------------------------------------- #
    @property
    def is_legacy(self) -> bool:
        return self.legacy_sine is not None or self.static_pattern is not None

    @property
    def f_ctl_hz(self) -> float:
        return 1.0 / (2.0 * np.pi * self.tau_ctl_s)

    def asjson(self) -> dict:
        d = asdict(self)
        d["f_ctl_hz"] = round(self.f_ctl_hz, 4)
        d["is_legacy"] = self.is_legacy
        return d

    def with_(self, **kw) -> "RotorJitter":
        return replace(self, **kw)


# --------------------------------------------------------------------------- #
#  프리셋 — σ 값의 출처를 이름 옆에 붙여 둔다
# --------------------------------------------------------------------------- #
#  ⭐ σ_w 는 원장의 `wobble_*_amp_pct` 를 **그대로 쓰면 안 된다.** 그 값은 «등가 사인
#     진폭»(대역 rms × √2)이고 OU 의 파라미터는 σ 이므로 두 번 고친다:
#         rms_band = amp/√2
#         σ_w      = rms_band / √F ,  F = (2/π)[arctan(2πf₂T) − arctan(2πf₁T)]
#     (F = OU 총분산 중 측정대역 [f1,f2] 에 든 몫. PSD S(f)=4σ²T/(1+(2πfT)²) 적분.)
#     계산은 `sigma_w_from_band_amp()` 가 한다 — 프리셋 값이 그 함수와 맞는지도 게이트다.
PRESETS = {
    # ── ⭐기본값. 현행 코드를 글자 그대로 재현한다(비트동일 보장) ─────────────
    "legacy": RotorJitter(
        name="legacy", static_sigma=0.0022, wobble_sigma=0.0,
        random_phase=False,
        legacy_sine=(0.0015, 2.7),
        static_pattern=(1.0, -1.0, -0.55, 0.55),
        source="현행 report07_hover_long.py 값 그대로. 산포는 PX4 SITL 실측 0.07~0.29% "
               "중간값이지만 패턴 [+1,-1,-0.55,+0.55] 과 정현파 2.7 Hz 는 근거가 없다. "
               "비트동일 회귀 기준선으로만 쓴다."),
    # ── 옛 report07 `outdoor` (정현파). 기존 _outdoor 원장 재현용 ──────────────
    "legacy_outdoor": RotorJitter(
        name="legacy_outdoor", static_sigma=0.02, wobble_sigma=0.0,
        random_phase=False,
        legacy_sine=(0.025, 1.0),
        static_pattern=(1.0, -1.0, -0.55, 0.55),
        source="옛 report07_hover_long.py PRESETS['outdoor'] 그대로 — "
               "outputs/report07_hover_long_outdoor.npz 재현용. 모양(정현파)은 틀렸다."),
    # ── 통제군: 대칭·이상 하한 ────────────────────────────────────────────────
    "sitl": RotorJitter(
        name="sitl", static_sigma=0.0022, wobble_sigma=0.0,
        random_phase=True,
        source="PX4 SITL 실측 0.07~0.29% 중간값. 흔들림 없음. ⚠SITL 은 완전대칭 기체 + "
               "이상 제어할당기라 CG 오프셋·프롭 개체차·바람이 **구조적으로 없다** — "
               "실기체보다 한 자릿수 작은 것은 버그가 아니라 구조다(조사 §5)."),
    # ── 실내(무풍) ────────────────────────────────────────────────────────────
    "indoor": RotorJitter(
        name="indoor", static_sigma=0.0054, wobble_sigma=0.0065,
        random_phase=True,
        source="NeuroBEM(UZH RPG) 실내 무풍 호버 7창: 정적 산포 중앙 0.54%, "
               "흔들림 등가사인 0.74% @0.3-5 Hz → 대역몫 보정 σ_w 0.65%. "
               "⚠레이싱 쿼드(DJI 아님)."),
    # ── ⭐야외 — 실증이 야외이므로 헤드라인 후보 ──────────────────────────────
    "outdoor": RotorJitter(
        name="outdoor", static_sigma=0.0235, wobble_sigma=0.0245,
        random_phase=True,
        source="PX4 Flight Review CODEV AQUILA V3 야외 Position 홀드 39창: 정적 산포 "
               "중앙 2.35%, 흔들림 등가사인 2.52% @0.3-2 Hz → 대역몫 보정 σ_w 2.45%. "
               "⚠DJI 아님, 4 Hz 표집이라 앨리어싱 여지. DJI P3 DAT 명령환산 2.3~4.6% 와 같은 자리."),
    # ── 문헌 앵커 하나만으로 세운 팔 ─────────────────────────────────────────
    "lit_iid": RotorJitter(
        name="lit_iid", static_sigma=0.0099, wobble_sigma=0.0,
        random_phase=True,
        source="arXiv:2506.00497 — 로터 각속도를 i.i.d. N(ω̄,σ²) 로 두고 상대 산포 0.99%. "
               "⭐문헌이 실제로 쓰는 유일한 «분포» 앵커. 시간 변동은 그 논문도 안 넣는다."),
}
#: 기본 프리셋 이름 — 이것을 바꾸면 기존 원장이 깨진다.
DEFAULT_PRESET = "legacy"


def get(preset) -> RotorJitter:
    """이름이든 객체든 받아 `RotorJitter` 로 돌려준다."""
    if isinstance(preset, RotorJitter):
        return preset
    if preset is None:
        return PRESETS[DEFAULT_PRESET]
    return PRESETS[str(preset)]


# --------------------------------------------------------------------------- #
#  σ_w 보정 산술 — 원장의 «등가 사인 진폭» → OU 의 σ
# --------------------------------------------------------------------------- #
def ou_band_fraction(tau_s: float, f1_hz: float, f2_hz: float) -> float:
    """OU 총분산 중 대역 [f1, f2] 에 든 몫 F. S(f) = 4σ²T/(1+(2πfT)²) 를 적분한 닫힌 꼴."""
    a = np.arctan(2.0 * np.pi * f2_hz * tau_s) - np.arctan(2.0 * np.pi * f1_hz * tau_s)
    return float(2.0 / np.pi * a)


def sigma_w_from_band_amp(amp_equiv_sine: float, f1_hz: float, f2_hz: float,
                          tau_s: float = TAU_CTL_S) -> float:
    """«등가 사인 진폭»(대역 rms × √2) → OU 의 σ_w.

    원장 `rotor_rpm_web_anchor.json` 의 `wobble_*_amp_pct` 가 바로 그 등가 사인 진폭이라
    (method_note: *"대역 성분 rms × √2"*) OU 파라미터로 쓰려면 두 번 고쳐야 한다."""
    return float(amp_equiv_sine / np.sqrt(2.0) / np.sqrt(ou_band_fraction(tau_s, f1_hz, f2_hz)))


def window_mean_variance_fraction(tau_s: float, window_s: float) -> float:
    """길이 T_w 인 창으로 OU 를 보면 분산이 «창평균의 흔들림»(≈정적 오프셋)과
    «창 안 변화»로 갈린다. 그 중 **창평균 몫**을 돌려준다.

        (2T/T_w)·[1 − (T/T_w)(1 − e^(−T_w/T))]

    ⭐0.25 s(분류 헤드라인)에서 **0.716** — 흔들림의 71.6 % 가 정적 오프셋으로 보인다.
      그러니 분류에서 먼저 고칠 것은 흔들림이 아니라 **정적 산포 값 자체**다."""
    r = tau_s / window_s
    return float(2.0 * r * (1.0 - r * (1.0 - np.exp(-1.0 / r))))


# --------------------------------------------------------------------------- #
#  OU 과정 — 정확 이산화(근사 아님)
# --------------------------------------------------------------------------- #
def ou_process(n: int, dt: float, sigma: float, tau: float, rng,
               n_ch: int = 1, tau2: Optional[float] = None) -> np.ndarray:
    """정상상태에서 시작하는 OU 열 (n, n_ch).

        a = exp(−dt/T);   ε[n+1] = a·ε[n] + σ√(1−a²)·N(0,1);   ε[0] ~ N(0, σ)

    ⚠ **정상상태에서 시작해야 한다.** 0 에서 시작하면 앞 ~1 초가 «워밍업» 이 되어
      창 앞머리의 흔들림이 인위적으로 작아진다.

    tau2 : 주면 2극(로터 관성)을 직렬로 한 번 더 통과시키고 분산을 되돌린다.
      연속시간에서 출력 분산이 σ²·T₁/(T₁+T₂) 이므로 √((T₁+T₂)/T₁) 로 되돌린다.
      ⚠ 이산화 오차만큼 실현 std 가 σ 에서 살짝 벗어난다 — `summary()` 가 실측을 낸다."""
    if n <= 0:
        return np.zeros((0, n_ch))
    if sigma <= 0.0:
        return np.zeros((n, n_ch))
    a = float(np.exp(-dt / tau))
    s = float(sigma * np.sqrt(max(1.0 - a * a, 0.0)))
    w = rng.standard_normal((n, n_ch))
    e = np.empty((n, n_ch))
    e[0] = sigma * w[0]                       # ε[0] ~ N(0, σ) — 정상상태
    for i in range(1, n):
        e[i] = a * e[i - 1] + s * w[i]
    if tau2 is not None and tau2 > 0.0:
        b = float(np.exp(-dt / tau2))
        y = np.empty_like(e)
        y[0] = e[0]
        for i in range(1, n):
            y[i] = b * y[i - 1] + (1.0 - b) * e[i]
        e = y * np.sqrt((tau + tau2) / tau)    # 연속시간 분산 회복
    return e


def _wobble(n_t: int, prf: float, n_rotors: int, jit: RotorJitter, rng,
            coarse_hz: Optional[float] = COARSE_HZ) -> np.ndarray:
    """(n_t, n_rotors) 상대 흔들림 ε_k(t). 로터마다 **독립**이다."""
    if jit.wobble_sigma <= 0.0:
        return np.zeros((n_t, n_rotors))
    dur = n_t / prf
    if coarse_hz and coarse_hz > 0.0:
        n_c = int(np.ceil(dur * coarse_hz)) + 2
        if n_c >= _MIN_COARSE and coarse_hz < prf:
            from scipy.interpolate import CubicSpline
            dt_c = 1.0 / coarse_hz
            ec = ou_process(n_c, dt_c, jit.wobble_sigma, jit.tau_ctl_s, rng,
                            n_ch=n_rotors, tau2=jit.tau_motor_s)
            tc = np.arange(n_c) * dt_c
            t = np.arange(n_t) / prf
            return CubicSpline(tc, ec, axis=0)(t)
    return ou_process(n_t, 1.0 / prf, jit.wobble_sigma, jit.tau_ctl_s, rng,
                      n_ch=n_rotors, tau2=jit.tau_motor_s)


# --------------------------------------------------------------------------- #
#  정적 산포
# --------------------------------------------------------------------------- #
def static_offsets(n_rotors: int, jit: RotorJitter, rng) -> np.ndarray:
    """로터별 정적 상대 치우침 s_k. 평균 0 (평균 rpm 은 rpm0 로 유지).

    ⚠ 평균을 뺀 뒤 실현 std 는 σ_s·√((n−1)/n) 다 — n=4 면 0.866·σ_s.
      `md_classify_dataset._draw_trials` 가 이미 그 규약이라 **일부러 맞췄다**."""
    if jit.static_pattern is not None:                       # legacy — 결정론
        return jit.static_sigma * np.resize(np.asarray(jit.static_pattern, float), n_rotors)
    if jit.static_sigma <= 0.0:
        return np.zeros(n_rotors)
    d = rng.normal(0.0, jit.static_sigma, n_rotors)
    return d - d.mean()


def initial_phase_deg(n_rotors: int, jit: RotorJitter, rng,
                      period_deg: float = 180.0) -> np.ndarray:
    """θ_k(0). `random_phase` 면 𝒰(0, period_deg), 아니면 0(=현행 정렬).

    period_deg : 프로펠러 한 **주기**의 각도 = 360/blades. 2블레이드면 180°."""
    if not jit.random_phase:
        return np.zeros(n_rotors)
    return rng.uniform(0.0, period_deg, n_rotors)


# --------------------------------------------------------------------------- #
#  본체
# --------------------------------------------------------------------------- #
def rpm_series(rpm0: float, n_rotors: int, n_t: int, prf: float, jitter, rng,
               *, coarse_hz: Optional[float] = COARSE_HZ):
    """(n_t, n_rotors) rpm 열과 진단 dict.

    ⚠ **dt 가 아니라 prf 를 받는다** — 설계서(§2-3)는 `dt` 였지만 현행 코드가
      `t = np.arange(n)/prf` 로 시간축을 만들기 때문이다. `arange(n)*(1/prf)` 는
      마지막 ulp 에서 갈리므로 그대로는 **비트동일이 깨진다.** 정보는 같다(dt = 1/prf).

    legacy 프리셋이면 현행 식을 **글자 그대로** 계산한다(게이트 G4)."""
    jit = get(jitter)
    if jit.legacy_sine is not None:                       # ── 현행 식 재현 ──
        amp, hz = jit.legacy_sine
        stat = static_offsets(n_rotors, jit, rng)
        phi0 = 2 * np.pi * np.arange(n_rotors) / n_rotors
        t = np.arange(n_t) / prf
        rpm_t = rpm0 * (1.0 + stat[None, :]
                        + amp * np.sin(2 * np.pi * hz * t[:, None] + phi0[None, :]))
        diag = {"mode": "legacy_sine", "sine_amp": float(amp), "sine_hz": float(hz),
                "static_offsets": stat.tolist(), "coarse_hz": None}
        return rpm_t, diag

    stat = static_offsets(n_rotors, jit, rng)             # ── OU 판 ──
    eps = _wobble(n_t, prf, n_rotors, jit, rng, coarse_hz=coarse_hz)
    rpm_t = rpm0 * (1.0 + stat[None, :] + eps)
    diag = {"mode": "ou", "static_offsets": stat.tolist(),
            "static_sigma": float(jit.static_sigma),
            "wobble_sigma": float(jit.wobble_sigma),
            "tau_ctl_s": float(jit.tau_ctl_s),
            "tau_motor_s": jit.tau_motor_s,
            "coarse_hz": (float(coarse_hz) if (coarse_hz and coarse_hz < prf) else None)}
    return rpm_t, diag


def phases(rpm_t, prf: float, dirs, base_deg=None) -> np.ndarray:
    """rpm 열 → 로터별 회전각 θ_k(t) [deg], (n_t, n_rotors).

        θ_k(t) = θ_k(0) + dir_k · ∫ 360·rpm_k/60 dt

    rpm_t 가 **1차원**(로터별 상수)이면 선형 위상으로 — 현행 두 경로
    (`articulated_fast.rotor_phases`, `md_classify_dataset.synth`)와 **비트동일**이다.
    **2차원** (n_t, n_rotors) 이면 cumsum 으로 적분한다(현행 `report07_hover_long` 과 동일 식)."""
    r = np.asarray(rpm_t, float)
    d = np.asarray(dirs, float)
    n_rot = r.shape[-1]
    b = np.zeros(n_rot) if base_deg is None else np.asarray(base_deg, float)
    if r.ndim == 1:
        raise ValueError("phases(): 1차원 rpm 은 t 축이 필요하다 — "
                         "articulated_fast.rotor_phases(t, rpm, dirs) 를 써라")
    dt = 1.0 / prf
    ang = np.cumsum(360.0 * r / 60.0 * dt, axis=0)
    return b[None, :] + d[None, :] * ang


# --------------------------------------------------------------------------- #
#  진단 — 게이트와 원장이 같은 함수를 쓴다
# --------------------------------------------------------------------------- #
def summary(rpm_t, prf: float, jitter=None, *, bands=((0.3, 2.0), (0.3, 5.0))) -> dict:
    """생성된 rpm 열이 «정말 그 과정인가» 를 재는 진단.

    실측 σ_s · σ_w · 대역별 rms · PSD 기울기 · 지배 주파수 · lag-1 자기상관."""
    from scipy.signal import welch
    r = np.asarray(rpm_t, float)
    if r.ndim == 1:
        r = r[:, None]
    n_t, n_rot = r.shape
    mu_k = r.mean(axis=0)                       # 로터별 평균
    base = float(mu_k.mean())
    rel = r / base - 1.0                        # 상대 편차
    stat_std = float(mu_k.std() / base)         # 정적 산포(로터간)
    ac = rel - rel.mean(axis=0, keepdims=True)  # 시간 변동만
    wob_std = float(ac.std())
    if wob_std < 1e-12:            # 부동소수 잔재 — «흔들림 없음» 으로 본다
        wob_std = 0.0

    out = {"n_t": int(n_t), "n_rotors": int(n_rot), "prf_hz": float(prf),
           "base_rpm": base, "rotor_mean_rpm": mu_k.tolist(),
           "static_spread_std_rel": stat_std,
           "wobble_std_rel": wob_std,
           "wobble_std_per_rotor": ac.std(axis=0).tolist()}

    if n_t >= 4 and wob_std > 0:
        lags = [np.corrcoef(ac[:-1, k], ac[1:, k])[0, 1]
                for k in range(n_rot) if ac[:, k].std() > 0]
        out["wobble_lag1_autocorr"] = float(np.mean(lags)) if lags else float("nan")
    if wob_std > 0 and n_t >= 64:
        #  ⚠ 조각 길이가 곧 주파수 분해능이다. 우리가 재려는 것이 0.3~5 Hz 이므로
        #    조각은 **10 초 이상**이어야 Δf ≤ 0.1 Hz 다. 기록이 그보다 짧으면
        #    통째로 한 조각(평균 없음)으로 재고, 그 한계를 원장에 적는다.
        nps = int(min(n_t, max(256, int(round(prf * 10.0)))))
        f, P = welch(ac, fs=prf, axis=0, nperseg=nps, detrend="constant")
        out["psd_nperseg"] = nps
        out["psd_df_hz"] = float(prf / nps)
        out["psd_n_segments"] = float(max(1.0, (n_t - nps) / (nps / 2.0) + 1.0))
        Pm = P.mean(axis=1)
        out["band_rms_rel"] = {}
        for f1, f2 in bands:
            sel = (f >= f1) & (f <= f2)
            v = float(np.sqrt(np.trapezoid(Pm[sel], f[sel]))) if sel.sum() > 1 else float("nan")
            out["band_rms_rel"][f"{f1}-{f2}Hz"] = v
            out["band_rms_rel"][f"amp_equiv_sine_{f1}-{f2}Hz"] = v * np.sqrt(2.0)
        pos = f > 0
        if pos.sum() > 2:
            out["dominant_hz"] = float(f[pos][int(np.argmax(Pm[pos]))])
        jit = get(jitter) if jitter is not None else None
        fc = jit.f_ctl_hz if jit is not None else F_CTL_HZ
        sel = (f >= 4.0 * fc) & (f <= min(40.0 * fc, 0.4 * prf))
        if sel.sum() >= 4:
            lf, lp = np.log10(f[sel]), 10.0 * np.log10(Pm[sel] + 1e-300)
            out["psd_slope_db_per_decade"] = float(np.polyfit(lf, lp, 1)[0])
            out["psd_slope_band_hz"] = [float(f[sel][0]), float(f[sel][-1])]
    if jitter is not None:
        out["jitter"] = get(jitter).asjson()
    return out


# --------------------------------------------------------------------------- #
def preset_table() -> dict:
    """원장(`outputs/rotor_jitter_model.json`)에 그대로 실을 프리셋 표."""
    return {k: v.asjson() for k, v in PRESETS.items()}


if __name__ == "__main__":   # 손으로 훑어보는 용도 — 게이트는 verify_rotor_dynamics.py
    rng = np.random.default_rng(0)
    print(f"{'preset':16s} {'σ_s':>8s} {'σ_w':>8s} {'실측σ_s':>9s} {'실측σ_w':>9s} "
          f"{'지배Hz':>8s} {'기울기':>9s}")
    for k in PRESETS:
        jit = PRESETS[k]
        r, _ = rpm_series(3800.0, 4, 39400, 19700.0, jit, np.random.default_rng(7))
        s = summary(r, 19700.0, jit)
        print(f"{k:16s} {jit.static_sigma:8.4f} {jit.wobble_sigma:8.4f} "
              f"{s['static_spread_std_rel']:9.5f} {s['wobble_std_rel']:9.5f} "
              f"{s.get('dominant_hz', float('nan')):8.2f} "
              f"{s.get('psd_slope_db_per_decade', float('nan')):9.2f}")
