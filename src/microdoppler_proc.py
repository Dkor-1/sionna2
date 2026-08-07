# -*- coding: utf-8 -*-
"""
microdoppler_proc.py — 마이크로도플러 **전처리 체인** (선행 구현을 따른다)
==========================================================================
왜 이 파일이 생겼나
--------------------
2026-08-07 1차 그림은 전처리가 «복소 평균 빼기» 하나뿐이었다. 그건 **DC 한 빈**만 지우는 것이라
동체 정적 반사가 그대로 남고, 빈 선택도 없었다. 사용자 지적으로 선행 구현을 보고 다시 짰다.

따르는 것 — OpenISAC (arXiv:2601.03535v2, §III-B)
--------------------------------------------------
원문 p.6 그대로:

  · *"we apply an improved **moving target indication (MTI)** procedure to suppress static
    (near-zero-Doppler) clutter. In essence, MTI applies a **temporal high-pass filter along the
    slow-time index m**, thereby creating a **notch around zero Doppler**."*
  · *"To obtain a narrow stopband at low computational cost, we adopt a **causal IIR high-pass**
    implementation"* — 식 (18).
  · *"Stability is ensured by placing all poles strictly inside the unit circle, and the
    **notch cutoff should be set slightly above the maximum expected clutter Doppler**."*
  · 실험 설정: *"**Butterworth high-pass IIR** filter with normalized **stopband/passband edges
    0.005/0.01**, stopband attenuation **80 dB**, passband ripple **1 dB**, and filter **order 15**,
    ... in **second-order-section** form."*
  · *"After clutter rejection, the stream splits into two branches: one feeds **micro-Doppler
    sensing**"* — 즉 마이크로도플러는 **MTI 뒤에** 온다.
  · 주기도 식 (20) 은 **창 함수 w[n,m]** 과 **제로패딩**(N_Per ≥ N, M_Per ≥ M_s)을 쓴다.

배경 — Clutter-Aware ISAC (Proc. IEEE, DOI 10.1109/JPROC.2026.3675476)
  · *"**Cold clutter**, also known as self-echo or **slow-time clutter**, represents undesired
    backscatter from the environment of the ISAC transmitter's own waveform."*
  · *"clutter can **dominate the intended target echoes**"* — 우리 실측이 그 말과 정확히 맞는다:
    전체 드론 변조 2.84 dB ↔ 프롭만 32.32 dB (matrice4e, el −15, 3.5 GHz).

⚠ 우리 시나리오에서 달라지는 것
--------------------------------
· **거리 빈이 없다.** 우리는 표적의 산란장만 계산하므로 지연축이 없다. 선행의 «표적 거리 빈을
  고른다» 단계는 우리에게 **이미 골라진 상태**다. 야외 씬을 붙이면 그때 진짜 빈 선택이 생긴다.
· **표적이 호버**라 동체 벌크 도플러가 0 이다 — 클러터와 같은 빈에 앉는다. 그래서 MTI 노치가
  동체를 지우는데, 마이크로도플러 입장에서는 그게 **원하는 동작**이다(블레이드는 ±f_flash 위에 있다).
  ⚠ 같은 노치가 «호버하는 표적 자체를 못 본다»(hover blind)는 것도 뜻한다 — 탐지 축에서는 손해다.
· **노치 폭을 f_flash 아래로 둔다.** 첫 블레이드 조화를 살려야 하므로, 통과대역 가장자리가
  f_flash 보다 확실히 낮아야 한다. `notch_ok()` 가 그 조건을 검사한다.
"""
from __future__ import annotations

import numpy as np
from scipy import signal

# ── OpenISAC 실험 설정 그대로 (원문 p.6) ──────────────────────────────────── #
OPENISAC_WS = 0.005      # 정규화 저지대역 가장자리 (× 나이퀴스트)
OPENISAC_WP = 0.010      # 정규화 통과대역 가장자리 (× 나이퀴스트)
OPENISAC_GSTOP_DB = 80.0
OPENISAC_GPASS_DB = 1.0


def mti_sos(ws: float = OPENISAC_WS, wp: float = OPENISAC_WP,
            gstop_db: float = OPENISAC_GSTOP_DB, gpass_db: float = OPENISAC_GPASS_DB):
    """0 도플러 노치를 만드는 **Butterworth 고역통과** 를 SOS 로 돌려준다.

    ws < wp 라 고역통과가 된다(둘 다 나이퀴스트로 정규화). 반환 (sos, 차수)."""
    sos = signal.iirdesign(wp=wp, ws=ws, gpass=gpass_db, gstop=gstop_db,
                           ftype="butter", output="sos")
    return sos, 2 * sos.shape[0]


def notch_edges_hz(prf: float, ws: float = OPENISAC_WS, wp: float = OPENISAC_WP):
    """노치의 저지·통과 가장자리를 Hz 로. 나이퀴스트 = prf/2."""
    nyq = prf / 2.0
    return ws * nyq, wp * nyq


def notch_ok(prf: float, f_flash: float, margin: float = 3.0,
             wp: float = OPENISAC_WP) -> dict:
    """⭐ 노치가 첫 블레이드 조화를 안 먹는지 검사한다.

    통과대역 가장자리가 f_flash 보다 `margin` 배 이상 낮아야 통과로 본다."""
    _, f_pass = notch_edges_hz(prf, wp=wp)
    return {"f_pass_edge_hz": f_pass, "f_flash_hz": f_flash,
            "ratio_flash_over_edge": f_flash / max(f_pass, 1e-9),
            "margin_required": margin,
            "ok": f_flash >= margin * f_pass}


def settle_samples(sos, tol_db: float = 60.0, n_max: int = 20000) -> int:
    """인과 IIR 의 **과도구간** 길이 — 임펄스응답이 최대에서 tol_db 아래로 떨어질 때까지.

    ⚠ OpenISAC 은 연속 스트림이라 과도가 시작 한 번뿐이지만, 우리 창은 유한하다.
      그래서 앞의 이만큼을 버려야 스펙트로그램 왼쪽 끝에 가짜 구조가 안 생긴다."""
    x = np.zeros(n_max)
    x[0] = 1.0
    h = np.abs(signal.sosfilt(sos, x))
    thr = h.max() * 10 ** (-tol_db / 20.0)
    idx = np.where(h > thr)[0]
    return int(idx[-1] + 1) if len(idx) else 0


def clutter_suppress(E, prf: float, *, ws: float = OPENISAC_WS, wp: float = OPENISAC_WP,
                     drop_transient: bool = True,
                     zero_phase: bool = False) -> tuple[np.ndarray, dict]:
    """슬로타임 MTI — 정적(0 도플러) 성분을 지운다. 반환 (필터된 열, 정보).

    ⭐ 복소 신호라 실수·허수부에 같은 필터를 각각 건다(선형이므로 동등하다).

    zero_phase
      False (기본) — 원문 식 (18) 그대로 **인과 IIR**. ⚠ 앞쪽에 과도가 있어 잘라내야 한다.
        OpenISAC 은 연속 스트림이라 과도가 시작 한 번뿐이지만, 우리 창은 유한해서 비싸다
        (차수 16 기준 858 표본 — 505 ms 창의 1/3).
      True  — 순방향·역방향 두 번 걸어 **위상 왜곡과 과도를 없앤다**(`sosfiltfilt`).
        원문과 다른 선택이므로 산출물에 그렇게 적는다. 진폭응답이 제곱되어
        노치가 더 깊고 가장자리가 더 가파르다.
    """
    E = np.asarray(E, complex)
    sos, order = mti_sos(ws, wp)
    if zero_phase:
        y = (signal.sosfiltfilt(sos, E.real)
             + 1j * signal.sosfiltfilt(sos, E.imag))
        n_drop = 0
    else:
        y = signal.sosfilt(sos, E.real) + 1j * signal.sosfilt(sos, E.imag)
        n_drop = settle_samples(sos) if drop_transient else 0
        n_drop = min(n_drop, len(y) // 3)                # 창의 1/3 넘게는 안 버린다
    f_stop, f_pass = notch_edges_hz(prf, ws, wp)
    info = {
        "method": ("OpenISAC arXiv:2601.03535 §III-B eq(18) — Butterworth IIR high-pass, SOS"
                   + (" · zero-phase (sosfiltfilt, 원문과 다름)" if zero_phase else " · causal (원문 그대로)")),
        "zero_phase": bool(zero_phase),
        "order": order, "n_sections": int(sos.shape[0]),
        "ws_norm": ws, "wp_norm": wp,
        "gstop_db": OPENISAC_GSTOP_DB, "gpass_db": OPENISAC_GPASS_DB,
        "f_stop_edge_hz": f_stop, "f_pass_edge_hz": f_pass,
        "n_transient_dropped": int(n_drop),
        "suppression_db": float(20 * np.log10(
            (np.abs(np.mean(E)) + 1e-30) / (np.abs(np.mean(y[n_drop:])) + 1e-30))),
    }
    return y[n_drop:], info


def periodogram_spec(E, prf: float, f_flash: float, *, min_periods: int = 8,
                     zero_pad: int = 4, window: str = "hann"):
    """OpenISAC 식 (20) 형태의 주기도 — 창 함수 + 제로패딩.

    조각 길이를 **블레이드 min_periods 주기 이상**으로 잡는다. 그래야 조각당 분해능이
    f_flash/min_periods 가 되어 빗살 사이에 그만큼의 빈이 든다.
    반환 (f[Hz], t[s], |S| 선형, 정보)."""
    E = np.asarray(E, complex)
    nper = int(2 ** np.ceil(np.log2(max(16.0, min_periods * prf / f_flash))))
    nper = int(min(nper, max(16, len(E) // 3)))
    nov = nper - max(1, nper // 8)
    f, t, S = signal.spectrogram(E, fs=prf, nperseg=nper, noverlap=nov,
                                 nfft=zero_pad * nper, detrend=False, window=window,
                                 return_onesided=False, scaling="spectrum",
                                 mode="magnitude")
    info = {"nperseg": int(nper), "noverlap": int(nov), "nfft": int(zero_pad * nper),
            "window": window, "seg_periods": nper / (prf / f_flash),
            "seg_resolution_hz": prf / nper,
            "bins_between_harmonics": f_flash / (prf / nper),
            "n_segments": int(S.shape[1])}
    return np.fft.fftshift(f), t, np.fft.fftshift(S, axes=0), info


def select_bins(f, S, *, f_lo: float, f_hi: float):
    """⭐ **빈 선택** — 판정에 쓰는 도플러 대역만 남긴다.

    f_lo : MTI 통과대역 가장자리. 그 아래는 필터가 이미 지웠으므로 판정에 안 쓴다.
    f_hi : 운동학이 예측한 상한(보통 1.x·f_tip). 그 위는 블레이드가 만들 수 없는 자리다.
    반환 (마스크, 남은 비율, 안쪽 에너지 비율)."""
    a = np.abs(f)
    keep = (a >= f_lo) & (a <= f_hi)
    e_all = float((S ** 2).sum())
    e_keep = float((S[keep] ** 2).sum())
    return keep, float(keep.mean()), (e_keep / e_all if e_all > 0 else 0.0)


def process(E, prf: float, f_flash: float, f_tip: float, *,
            f_hi_factor: float = 1.6, **kw):
    """전처리 전체를 한 번에 — MTI → 주기도 → 빈 선택. 반환 (f, t, S, info)."""
    y, mti = clutter_suppress(E, prf, **{k: v for k, v in kw.items()
                                         if k in ("ws", "wp", "drop_transient", "zero_phase")})
    f, t, S, per = periodogram_spec(y, prf, f_flash,
                                    **{k: v for k, v in kw.items()
                                       if k in ("min_periods", "zero_pad", "window")})
    keep, frac, e_frac = select_bins(f, S, f_lo=mti["f_pass_edge_hz"],
                                     f_hi=f_hi_factor * f_tip)
    info = {"mti": mti, "periodogram": per,
            "bin_selection": {"f_lo_hz": mti["f_pass_edge_hz"],
                              "f_hi_hz": f_hi_factor * f_tip,
                              "kept_bin_fraction": frac,
                              "kept_energy_fraction": e_frac,
                              "why_ko": "아래는 MTI 가 이미 지웠고, 위는 운동학이 금지한다"},
            "notch_check": notch_ok(prf, f_flash)}
    return f, t, S, keep, info


if __name__ == "__main__":
    sos, order = mti_sos()
    print(f"  MTI  Butterworth 고역통과 · 차수 {order} · SOS {sos.shape[0]}단")
    print(f"       과도구간 {settle_samples(sos)} 표본")
    for prf, ffl, name in ((5000.0, 126.7, "Matrice 4E"), (4000.0, 183.3, "Mini 5 Pro")):
        fs_, fp_ = notch_edges_hz(prf)
        ck = notch_ok(prf, ffl)
        print(f"  {name:12s} PRF {prf:.0f} Hz → 노치 저지 {fs_:.1f} / 통과 {fp_:.1f} Hz · "
              f"f_flash {ffl:.1f} Hz ({ck['ratio_flash_over_edge']:.1f}배) "
              f"{'✅' if ck['ok'] else '❌ 첫 조화를 먹는다'}")
