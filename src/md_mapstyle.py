# -*- coding: utf-8 -*-
"""
md_mapstyle.py — 마이크로도플러 **맵 표시 규약** 한 자리

왜 한 자리에 모으나
--------------------
2026-08-07 하루에 마이크로도플러 맵을 여섯 번 다시 그렸다. 매번 조각 길이·겹침·색역을
그림마다 따로 정해서, 같은 물리가 그림마다 다르게 보였다. 사용자가 «모든 그림을 같은
해상도로» 라고 한 것이 그 뜻이다. 그래서 규약을 **함수 하나**로 굳힌다.

⭐ 규약 — 무엇을 왜 그렇게 정했나
    조각 길이   **블레이드 0.6 주기**
                플래시는 한 주기 안의 사건이라, 조각이 한 주기를 넘으면 그 안에서
                **시간평균되어 지워진다.** 우리가 6.5 주기로 잡아 놓고 «플래시가 안 보인다»
                고 했던 것이 그 때문이다.
    겹침(hop)   **2 표본**
                hop 이 크면 시간 슬롯이 적어 계단처럼 보인다("빈이 너무 크다").
                ⚠ 겹침은 정보를 늘리지 않는다 — 같은 정보를 촘촘히 다시 읽을 뿐이다.
                  시간 분해능은 여전히 조각 길이가 정한다.
    제로패딩    **8 배**
                주파수축을 매끈하게 보간한다. ⚠ 표시 화소보다 빈이 많아지면 렌더러가
                솎아내며 얼룩(모아레)이 생기므로, 그리는 도플러 범위를 함께 좁힌다.
    음영        **gouraud** — 격자 칸 경계를 지워 문헌 그림처럼 이어 보이게 한다.
    색·색역     **jet · 0 ~ −40 dB** — 문헌 규약.
    0 도플러    **지우지 않는다** — 동체 선이 읽기의 기준이다.

⚠ 대가를 숨기지 않는다. 조각이 짧으면 **주파수 분해능이 나빠진다**(능선이 굵어진다).
  시간·주파수는 맞바꿈이고 둘 다 동시에는 원리적으로 못 본다.
  능선을 재는 그림은 `ridge_spec()` 을 따로 쓴다.

⭐⭐ 상시 지시(2026-08-10, 사용자): **주파수 분해능보다 시간 분해능이 우선이다.**
  플래시가 보여야 데이터를 알아본다. 그래서 `flash_spec()` 이 기본이고,
  `ridge_spec()` 은 **보조 패널로만** 쓴다 — 단독으로 내지 않고, 낼 때도 플래시를 왼쪽에 둔다.
  마이크로도플러 그림을 새로 만들 때 이 모듈을 우회하지 마라 — 우회하면 규약이 갈라진다.
"""
from __future__ import annotations

import numpy as np
from scipy.signal import spectrogram as _spec

FLASH_PERIODS = 0.6       # 조각 길이 = 블레이드 주기의 이만큼
FLASH_HOP = 2             # 겹침 — 시간 슬롯을 촘촘히
FLASH_PAD = 8             # 제로패딩
RIDGE_PERIODS = 6.5       # 능선을 재는 그림용(대조군)
RIDGE_HOP = 4
RIDGE_PAD = 2

CMAP = "jet"
VMIN, VMAX = -40.0, 0.0
SHADING = "gouraud"
YLIM_FTIP = 1.9           # 도플러축을 f_tip 의 이 배까지

# --------------------------------------------------------------------------- #
#  세 팔의 이름 — 그림·표·산문이 **한 이름만** 쓴다
# --------------------------------------------------------------------------- #
#  ⭐ 같은 세 팔이 8-2(모노)와 8-5(바이스태틱)의 같은 표에 나오므로, 이름이 갈리면 같은
#     수가 다른 물건처럼 읽힌다. 그림 라벨(`benchmark/build_three_engine_fig.py` ·
#     `build_flash_zoom.py` · `build_engine_concept_fig.py`)과 **같은 문자열**이다.
#  ⚠ 그림 텍스트는 영어이므로 라벨도 영어로 둔다(집 규약).
ARM_SIONNA = "Sionna PathSolver"
ARM_SBR = "Ours (SBR+PO, 기본)"
ARM_PO = "Ours, nothing blocked (control)"
#: 원장 키 → 표시 이름. 세 팔을 도는 표는 이 순서를 쓴다(대조 → 스톡 → 우리 기본).
ARM_LABELS = {"po": ARM_PO, "sionna": ARM_SIONNA, "sbr": ARM_SBR}


def _spectro(E, prf, nper, hop, pad):
    nper = max(8, int(nper))
    f, t, S = _spec(np.asarray(E, complex), fs=prf, nperseg=nper,
                    noverlap=nper - max(1, int(hop)), nfft=pad * nper, detrend=False,
                    window="hann", return_onesided=False, scaling="spectrum",
                    mode="magnitude")
    return np.fft.fftshift(f), t, np.fft.fftshift(S, axes=0), nper


FLASH_PERIODS_SHARP = 0.45   # ⭐**실측으로 고른 값** — 아래 표 참조
MIN_SEG_SAMPLES = 24         # 조각이 이보다 적은 표본이면 주파수축이 무너진다


def auto_periods(prf, f_flash, min_samples: int = MIN_SEG_SAMPLES) -> float:
    """⭐**가장 뚜렷하게 보이는** 조각 길이를 고른다 (사용자: "STFT로 뚜렷하게").

    ⚠ 2026-08-10 실측이 내 예상을 뒤집었다. «시간 분해능 우선» 을 «조각을 최대한 짧게» 로
      옮긴 것이 틀렸다 — 조각을 줄이면 주파수축이 뭉개져 **플래시가 오히려 안 보인다**.
      같은 원장(PRF 19,700 Hz · 60 ms 창 · SBR 팔)에서 잰 값:

        조각      Δt        Δf       플래시 대비   동체선 폭
        0.15 주기  1.17 ms   857 Hz     2.6 dB     2034 Hz   ← 거의 안 보인다
        0.20 주기  1.57 ms   635 Hz     7.4 dB     1509 Hz
        0.30 주기  2.39 ms   419 Hz    16.1 dB     1048 Hz
        0.45 주기  3.55 ms   281 Hz  ⭐19.1 dB      739 Hz   ← 최대
        0.60 주기  4.72 ms   212 Hz    17.6 dB      583 Hz   ← 시간평균이 시작된다

      «플래시 대비» 는 날개끝 띠(0.35~1.0·f_tip)의 시간축 변동 폭이다 — 플래시가 또렷할수록
      크다. 0.45 를 지나 길어지면 한 조각 안에서 플래시가 **시간평균되어** 대비가 내려가고,
      짧아지면 도플러 번짐이 그 띠를 **뭉개서** 역시 내려간다. 양쪽이 만나는 자리가 0.45 다.

    ⭐ 규칙은 그대로다 — 목표는 «내가 데이터를 알아볼 수 있게» 이지 «파라미터를 한 방향으로
      미는 것» 이 아니다. 그 목표를 실측으로 푼 결과가 0.45 주기다.

    ⚠⚠ **이 표는 재현되지 않았다 — 인용하지 마라.** 2026-08-10 독립 재구현에서 같은 지표를
      다시 재니 0.60 주기가 더 컸다. 원인은 «플래시 대비» 의 정의가 위 산문 한 줄뿐이라
      띠의 범위·집계 방식이 사람마다 달라지기 때문이다. 원장 JSON 도 없다.
      ⇒ **0.45 는 유지한다**(0.6 대비 시간 분해능 4.7 → 3.6 ms 이고 플래시가 실제로 또렷하다).
        그러나 위 숫자를 **근거로 쓰지 마라** — 인용해야 하면 지표를 코드로 못 박고
        원장 JSON 으로 내는 것이 먼저다. 지금 인용해도 되는 사실은 «조각 70 표본 ·
        Δt 3.55 ms · Δf 281 Hz» 처럼 **정의가 하나뿐인 양**이다.
    ⚠ 다른 기체·PRF 에서는 최적점이 다를 수 있다."""
    per = prf / f_flash                                   # 블레이드 한 주기 = 표본 수
    for p in (FLASH_PERIODS_SHARP, FLASH_PERIODS):
        if round(p * per) >= min_samples:
            return p
    return FLASH_PERIODS


def flash_spec(E, prf, f_flash, periods=None):
    """⭐ **플래시가 보이는** 스펙트로그램 — 이것이 기본 규약이다.

    periods : 조각 길이(블레이드 주기 배수). None 이면 규약값 0.6.
      ⭐ 2026-08-10 사용자 지시 «시간 해상도를 더 높여달라, 계산량을 더 넣더라도».
        조각의 **시간 길이**는 (periods × 블레이드 주기)라 PRF 와 무관하다 —
        즉 PRF 만 올려서는 시간 분해능이 안 좋아진다. periods 를 줄여야 한다.
        그런데 periods 를 줄이면 조각의 **표본 수**가 줄어(최소 8 로 클램프) 주파수축이
        무너지므로, **PRF 를 함께 올려야** 짧은 조각에도 표본이 남는다.
        예) PRF 5 kHz·0.6주기 = 24표본 = 4.7 ms  →  PRF 20 kHz·0.2주기 = 32표본 = 1.6 ms.
        ⚠ 대가는 주파수 분해능(208 → 625 Hz)과 계산량(자세 수 4배)이다."""
    per = prf / f_flash
    p = FLASH_PERIODS if periods is None else float(periods)
    return _spectro(E, prf, round(p * per), FLASH_HOP, FLASH_PAD)


def ridge_spec(E, prf, f_flash):
    """능선을 재는 스펙트로그램 — 주파수 분해능을 사고 플래시를 내준다."""
    per = prf / f_flash
    return _spectro(E, prf, round(RIDGE_PERIODS * per), RIDGE_HOP, RIDGE_PAD)


#: `mode="over_noise"` 의 색역 [dB above the estimated noise floor].
#: 0 이 **잡음 바닥**이다 — 패시브 레이더 관례(Remote Sens. 14:6146 "24 dB above noise").
NOISE_VMIN, NOISE_VMAX = -6.0, 40.0


def noise_rms_from(S_noise):
    """잡음만 통과시킨 스펙트로그램의 **rms 크기** — `draw(mode="over_noise")` 의 0 점.

    ⭐ 예측식이 아니라 **측정값**을 쓴다. 같은 창·같은 조각 길이·같은 제로패딩을 통과한
      잡음이라 창 손실·겹침 상관이 자동으로 들어간다(우리가 유추한 g_stft 를 안 믿어도 된다).
    ⚠ 반드시 **같은 `flash_spec` 설정**으로 만든 잡음 전용 맵을 넣어라."""
    S = np.asarray(S_noise, float)
    return float(np.sqrt(np.mean(S ** 2)))


def draw(ax, t, f, S, f_tip, *, t_scale=1e3, ref=None, mode="peak", noise_rms=None,
         vmin=None, vmax=None):
    """규약대로 한 패널을 그린다. 반환은 컬러메시(공통 컬러바용).

    mode : ⭐**무엇을 0 dB 로 잡나**
      "peak"       (**기본, 옛 동작과 비트동일**) 20log10(S/ref), ref 기본값은 이 맵의 최대값.
                   ⚠ ref=None 이면 **패널마다 자기 최대값**이라 거리 정보가 그림에서 사라진다.
                     여러 거리를 한 그림에 놓을 때는 ref 를 **공통 스칼라**로 주거나
                     mode="over_noise" 를 써라.
      "over_noise" 20log10(S/noise_rms). 0 = **추정 잡음 바닥**, 색역 NOISE_VMIN..NOISE_VMAX.
                   `noise_rms` 는 `noise_rms_from()` 로 잰다(같은 STFT 설정의 잡음 전용 맵).
    vmin/vmax : 색역을 직접 못 박고 싶을 때. None 이면 모드의 기본값."""
    md = str(mode)
    if md == "peak":
        ref = S.max() if ref is None else ref
        Z = 20 * np.log10(S / (ref + 1e-30) + 1e-12)
        lo = VMIN if vmin is None else float(vmin)
        hi = VMAX if vmax is None else float(vmax)
    elif md == "over_noise":
        if noise_rms is None:
            raise ValueError("draw(mode='over_noise') 는 noise_rms 가 필요하다 "
                             "(noise_rms_from(잡음 전용 스펙트로그램))")
        Z = 20 * np.log10(S / (float(noise_rms) + 1e-30) + 1e-12)
        lo = NOISE_VMIN if vmin is None else float(vmin)
        hi = NOISE_VMAX if vmax is None else float(vmax)
    else:
        raise ValueError(f"draw: mode must be 'peak' or 'over_noise', got {mode!r}")
    # ⚠ rasterized=True 는 **필수**다(2026-08-10 실측). gouraud 음영은 격자 칸마다 폴리곤을
    #   찍는데, 고해상도 원장(2,033 시간 슬롯 × 수천 주파수 빈)이면 PDF 가 **114 MB** 로
    #   불어나 GitHub 100 MB 한도에 막힌다. 래스터화하면 축·글자는 벡터로 남고 맵만 픽셀이 된다.
    m = ax.pcolormesh(t * t_scale, f, Z,
                      cmap=CMAP, vmin=lo, vmax=hi, shading=SHADING, rasterized=True)
    for s in (+1, -1):
        ax.axhline(s * f_tip, color="w", ls="--", lw=1.0, alpha=0.8)
    ax.set_ylim(-YLIM_FTIP * f_tip, YLIM_FTIP * f_tip)
    return m


def caption_snr(ladder) -> str:
    """사다리 세 층위를 **캡션 한 줄**로(그림 안이 아니라 밖에 붙인다 — 하우스 규약).

    ⚠ 「SNR」 이라는 맨 이름을 쓰지 않는다. 어느 칸인지 이름을 그대로 적는다."""
    g = ladder.get
    bits = [f"snr_sample {float(g('snr_band_db')):+.1f} dB (per Rx sample, pre-MF)"]
    if g("g_mf_db") is not None:
        bits.append(f"gain_mf {float(g('g_mf_db')):+.1f} dB")
    if g("snr_slow_db") is not None:
        bits.append(f"slow-time total {float(g('snr_slow_db')):+.1f} dB")
    if g("snr_slow_ac_db") is not None:
        bits.append(f"blade line (AC) {float(g('snr_slow_ac_db')):+.1f} dB")
    if g("g_stft_db") is not None:
        bits.append(f"gain_stft {float(g('g_stft_db')):+.1f} dB "
                    f"({int(g('nperseg'))}-sample {g('window')} frame)")
    if g("snr_map_ac_db") is not None:
        bits.append(f"blade line on the map {float(g('snr_map_ac_db')):+.1f} dB")
    return "  |  ".join(bits)


def caption(prf, f_flash, nper, n_slots) -> str:
    """그림 밖에 붙일 규약 한 줄(영어 — 하우스 규약)."""
    per = prf / f_flash
    return (f"{nper}-sample Hann segments = {nper/per:.2f} blade periods "
            f"({prf/nper:.0f} Hz resolution), hop {FLASH_HOP} "
            f"({FLASH_HOP/prf*1e3:.2f} ms) = {n_slots} time slots, "
            f"{FLASH_PAD}x zero-padded.  Zero Doppler is the body.")
