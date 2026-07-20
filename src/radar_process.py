# -*- coding: utf-8 -*-
"""
radar_process.py — (report2) 에코 생성 + 정합필터 + RCS 추정/비교
==================================================================

흐름 (모노스태틱 능동 레이더)
  1) 표적 RCS σ(θ, fc) ← rcs_po (물리광학, 신뢰성 검증됨)
  2) 송신 파형 s(t) ← waveforms (WiFi/LTE/5G 실제 구조)
  3) 에코 y(t) = α·s(t−τ)·e^{j2π f_D t} + 잡음     (레이더 방정식으로 α 결정)
        τ = 2R/c (왕복지연),  f_D = 2v·fc/c (도플러),
        전압이득 α ∝ G·λ·√σ / R²   (단방향 거리, 단조정합)
  4) 정합필터: r(ℓ) = Σ y(n) s*(n−ℓ)  → 거리 프로파일 |r|  (피크폭 = c/B, 바이스태틱 Rb)
  5) RCS 추정: 기준 금속구(σ=πr²)를 똑같이 처리해 절대값 보정

세 표준 비교 포인트
  * 거리분해능(바이스태틱): 피크 폭 = c/(**상관에 쓴 기준신호의 점유대역**) — 명목 채널대역이 아님. 모노 등가는 절반.
      패시브(passive=True, 본 보고서의 기본): 상시 기준신호로 비교하면
      WiFi VHT-LTF 76MHz(ΔR_b 3.9m) > LTE CRS 18MHz(16.7m) > 5G SSB 7.2MHz(41.6m) — 유휴 5G 가 가장 뭉툭(바이스태틱 c/B).
      5G 가 1.5m 로 날카로워지는 건 PRS(측위 세션)가 켜졌을 때뿐.
  * 반송파 의존: λ 와 σ(fc) 가 표준마다 달라 에코 세기/추정 RCS 가 달라짐
  * 탐지 SNR: 대역·신호길이에 따른 처리이득
"""
from __future__ import annotations

import numpy as np
from scipy.signal import fftconvolve

C0 = 299792458.0


def _delay_doppler(s, fs, R, fc, vel=0.0):
    """s(t) 를 왕복지연 τ=2R/c (분수표본, 주파수영역) + 도플러로 변환."""
    n = len(s)
    tau = 2.0 * R / C0
    f = np.fft.fftfreq(n, d=1 / fs)
    sd = np.fft.ifft(np.fft.fft(s) * np.exp(-1j * 2 * np.pi * f * tau))  # 분수지연
    if vel:
        fd = 2.0 * vel * fc / C0
        t = np.arange(n) / fs
        sd = sd * np.exp(1j * 2 * np.pi * fd * t)
    return sd


def radar_voltage_gain(R, fc, sigma_m2, G_lin=1.0):
    """단조정합 레이더 전압이득 α ∝ G·λ·√σ / R²  (상수는 보정으로 제거)."""
    lam = C0 / fc
    return G_lin * lam * np.sqrt(max(sigma_m2, 0.0)) / (R * R)


def make_echo(wf, R, sigma_m2, vel=0.0, snr_db=20.0, rng=None):
    """파형 wf 로 표적(거리 R, RCS σ, 속도 v)의 에코+잡음을 만든다."""
    rng = rng or np.random.default_rng(0)
    s = wf.tx
    a = radar_voltage_gain(R, wf.carrier_hz, sigma_m2)
    echo = a * _delay_doppler(s, wf.fs_hz, R, wf.carrier_hz, vel)
    # 잡음: 에코 피크전력 기준 SNR
    pk = np.max(np.abs(echo)) + 1e-30
    npow = pk**2 * 10 ** (-snr_db / 10)
    noise = np.sqrt(npow / 2) * (rng.standard_normal(len(echo)) + 1j * rng.standard_normal(len(echo)))
    return echo + noise


def _fft_upsample(x, up):
    """대역제한 복소신호를 FFT 제로패딩으로 up 배 보간(정보 왜곡 없음)."""
    n = len(x); h = n // 2
    X = np.fft.fft(x)
    Xu = np.zeros(n * up, complex)
    Xu[:h] = X[:h]; Xu[-(n - h):] = X[h:]
    return np.fft.ifft(Xu) * up


def matched_filter(rx, ref, fs, up=1):
    """정합필터(상관) → (거리축[m], 프로파일 |r|). FFT 상관으로 O(N log N).
    up>1 이면 거리축을 up 배로 보간한다 — 원 샘플간격 c/2fs 가 LTE 에선 4.9 m 나 되어
    **그리기용**으로만 쓴다(측정 -3dB 폭은 up=1 원격자에서 재는 것이 게시 수치와 일관)."""
    r = fftconvolve(rx, np.conj(ref[::-1]), mode="full")   # = correlate(rx, ref)
    if up > 1:
        r = _fft_upsample(r, up)
    idx = np.arange(len(r)) / up - (len(ref) - 1)           # 지연(샘플) — up=1 이면 정수격자
    rng_m = idx / fs * C0 / 2.0
    return rng_m, np.abs(r)


def range_profile(wf, R, sigma_m2, vel=0.0, snr_db=20.0, rng=None, passive=False, up=1):
    """에코 → 정합필터 거리 프로파일. (거리축, dB프로파일, 피크거리, 피크값).
    passive=True 면 수신기가 '기지 기준신호(wf.ref)'만 알고 상관한다(패시브레이더의 현실).
    에코 자체는 항상 실제 송신(wf.tx)에서 생성된다.
    up>1 은 거리축 보간(그리기용)."""
    rx = make_echo(wf, R, sigma_m2, vel, snr_db, rng)
    ref = wf.ref if passive else wf.tx
    rng_m, prof = matched_filter(rx, ref, wf.fs_hz, up=up)
    m = (rng_m > 0) & (rng_m < 3 * R + 50)
    rng_m, prof = rng_m[m], prof[m]
    pk = np.argmax(prof)
    return rng_m, prof, rng_m[pk], prof[pk]


def mainlobe_width_m(rng_m, prof):
    """피크 -3 dB 거리분해능[m]."""
    pk = np.argmax(prof); p = prof / prof[pk]
    lo = pk; hi = pk
    while lo > 0 and p[lo] > 0.707: lo -= 1
    while hi < len(p) - 1 and p[hi] > 0.707: hi += 1
    return rng_m[hi] - rng_m[lo]


def sphere_calib(wf, R, r_sphere=0.5, snr_db=60.0, passive=False, up=1):
    """기준 금속구(σ=πr²)를 똑같이 처리한 정합필터 피크값(절대 RCS 보정용).
    ⚠ 표적과 **완전히 같은 처리**(passive·up)로 재야 λ·R²·처리이득이 상쇄된다.
      특히 up 이 다르면 분수지연(예: WiFi 는 5.33샘플) 피크를 한쪽만 놓쳐 1~2 dB 편향이 생긴다."""
    sig = np.pi * r_sphere**2
    _, _, _, pk = range_profile(wf, R, sig, snr_db=snr_db, passive=passive, up=up,
                                rng=np.random.default_rng(123))
    return pk, sig


def estimate_rcs_dbsm(peak_val, calib_peak, calib_sigma):
    """정합필터 피크 → 절대 RCS[dBsm] (구 보정 기준)."""
    sigma = calib_sigma * (peak_val / calib_peak) ** 2
    return 10 * np.log10(max(sigma, 1e-30))


if __name__ == "__main__":
    from waveforms import all_waveforms
    from rcs_po import drone_rcs_pattern, dbsm
    R = 10.0
    print(f"== Phantom 4 단조정합 비교 @ R={R} m (정면 az=0) ==")
    wfs = all_waveforms()
    for key, wf in wfs.items():
        sig, _ = drone_rcs_pattern("phantom4", wf.carrier_hz, np.array([0.0]))
        sig = float(sig[0])
        rng_m, prof, pkr, pkv = range_profile(wf, R, sig, snr_db=20.0)
        res = mainlobe_width_m(rng_m, prof)
        cpk, csig = sphere_calib(wf, R)
        est = estimate_rcs_dbsm(pkv, cpk, csig)
        print(f"  {wf.name:15s} fc={wf.carrier_hz/1e9:.2f}GHz  참RCS={dbsm(sig):6.2f}dBsm  "
              f"추정={est:6.2f}dBsm  피크R={pkr:5.2f}m  분해능={res:5.2f}m")
