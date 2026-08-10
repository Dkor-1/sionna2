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


def _spectro(E, prf, nper, hop, pad):
    nper = max(8, int(nper))
    f, t, S = _spec(np.asarray(E, complex), fs=prf, nperseg=nper,
                    noverlap=nper - max(1, int(hop)), nfft=pad * nper, detrend=False,
                    window="hann", return_onesided=False, scaling="spectrum",
                    mode="magnitude")
    return np.fft.fftshift(f), t, np.fft.fftshift(S, axes=0), nper


FLASH_PERIODS_FINE = 0.2  # ⭐고 PRF 원장용 — 조각을 더 짧게(시간 분해능을 더 산다)
MIN_SEG_SAMPLES = 24      # 조각이 이보다 적은 표본이면 주파수축이 무너진다


def auto_periods(prf, f_flash, min_samples: int = MIN_SEG_SAMPLES) -> float:
    """⭐원장이 허락하는 **가장 짧은 조각**을 고른다 — 시간 분해능 우선 규약의 자동화.

    조각의 시간 길이 = periods × 블레이드 주기다. 짧을수록 좋지만, 표본이 너무 적으면
    주파수축이 무너진다. 그래서 PRF 가 높은 원장에서만 짧은 조각으로 내려간다.
    ⚠ 이 함수 덕에 **빌더는 손대지 않아도** 고 PRF 원장이 오면 자동으로 좋아진다."""
    per = prf / f_flash                                   # 블레이드 한 주기 = 표본 수
    for p in (FLASH_PERIODS_FINE, 0.3, 0.45, FLASH_PERIODS):
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


def draw(ax, t, f, S, f_tip, *, t_scale=1e3, ref=None):
    """규약대로 한 패널을 그린다. 반환은 컬러메시(공통 컬러바용)."""
    ref = S.max() if ref is None else ref
    m = ax.pcolormesh(t * t_scale, f, 20 * np.log10(S / (ref + 1e-30) + 1e-12),
                      cmap=CMAP, vmin=VMIN, vmax=VMAX, shading=SHADING)
    for s in (+1, -1):
        ax.axhline(s * f_tip, color="w", ls="--", lw=1.0, alpha=0.8)
    ax.set_ylim(-YLIM_FTIP * f_tip, YLIM_FTIP * f_tip)
    return m


def caption(prf, f_flash, nper, n_slots) -> str:
    """그림 밖에 붙일 규약 한 줄(영어 — 하우스 규약)."""
    per = prf / f_flash
    return (f"{nper}-sample Hann segments = {nper/per:.2f} blade periods "
            f"({prf/nper:.0f} Hz resolution), hop {FLASH_HOP} "
            f"({FLASH_HOP/prf*1e3:.2f} ms) = {n_slots} time slots, "
            f"{FLASH_PAD}x zero-padded.  Zero Doppler is the body.")
