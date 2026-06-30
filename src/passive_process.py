# -*- coding: utf-8 -*-
"""
passive_process.py — (report4) 바이스태틱 패시브 레이더 처리 체인
==================================================================

문헌(LTE/5G/WiFi 패시브레이더)의 보편 파이프라인을 그대로 구현:

  감시신호 s_surv = 표적에코(지연 τ, 도플러 f_d) + 직접파누설(DPI) + 정적 클러터 + 잡음
  기준신호 s_ref  = 송신기가 보내는 '기지(known)' 파형(=직접파)
  ① ECA(직접파/클러터 제거)  →  ② CAF 거리-도플러 맵  →  ③ CA-CFAR 검출

CAF(교차모호함수) 거리-도플러는 **CPI 를 프레임(slow-time)으로 쪼개** 처리:
  · 프레임마다 기준과 정합필터(fast-time 상관) → 거리 프로파일
  · 프레임축(slow-time)으로 FFT → 도플러
  PRF = 프레임률 = fs/Lframe.  거리분해능 ΔRb=c/B,  도플러분해능 Δf_d=PRF/M,
  **최대 무모호 도플러 = ±PRF/2** → report2/3 의 파일럿률·v_max 와 동일한 한계!

지연↔거리: 바이스태틱은 왕복이 아니라 '추가 경로'이므로 Rb = lag·c/fs (모노스태틱의 /2 아님).
"""
from __future__ import annotations
import numpy as np

C0 = 299792458.0


# --------------------------------------------------------------------------- #
#  CPI(에코) 생성 — 기준 1프레임을 M번 반복, 표적/DPI/클러터/잡음 합성
# --------------------------------------------------------------------------- #
def make_cpi(ref_frame, M, fs, tau_s, fd_hz, a_tgt,
             dpi_amp=30.0, clutter=((0.0, 8.0), (40e-9, 5.0)), snr_db=10.0,
             abs_noise=False, noise_var=1.0, rng=None):
    """기준 1프레임 ref_frame 을 M번 반복한 CPI 에서 감시신호와 기준신호를 만든다.
      tau_s, fd_hz : 표적 지연[s]·도플러[Hz],  a_tgt : 표적 에코 전압이득
      dpi_amp      : 직접파누설 진폭(보통 표적보다 수십 dB 큼)
      clutter      : [(지연[s], 진폭), …] 정적(0-도플러) 반사체
      abs_noise=False: snr_db(표적피크 대비)로 잡음 — 데모/RD맵 시각화용.
      abs_noise=True : 잡음전력=noise_var(절대 고정), 표적은 a_tgt 절대값 — Pd 연구용
                       (처리이득이 파형/점유마다 달라 Pd 가 의미있게 갈림).
    반환: (surv, ref_cpi)  — 둘 다 길이 M*Lf 복소."""
    rng = rng or np.random.default_rng(0)
    Lf = len(ref_frame); N = M * Lf
    ref_cpi = np.tile(ref_frame, M)
    n = np.arange(N)

    def delayed(amp, tau):                         # 분수지연(주파수영역) + 진폭
        f = np.fft.fftfreq(N, d=1 / fs)
        return amp * np.fft.ifft(np.fft.fft(ref_cpi) * np.exp(-1j * 2 * np.pi * f * tau))

    surv = a_tgt * delayed(1.0, tau_s) * np.exp(1j * 2 * np.pi * fd_hz * n / fs)   # 표적
    surv = surv + dpi_amp * ref_cpi                                                # 직접파 누설(0지연·0도플러)
    for (ctau, camp) in clutter:                                                   # 정적 클러터(0-도플러)
        surv = surv + camp * delayed(1.0, ctau)
    if abs_noise:
        npow = noise_var                                                           # 절대 잡음전력
    else:
        pk = np.max(np.abs(a_tgt * delayed(1.0, tau_s))) + 1e-30
        npow = (pk ** 2) * 10 ** (-snr_db / 10)
    surv = surv + np.sqrt(npow / 2) * (rng.standard_normal(N) + 1j * rng.standard_normal(N))
    return surv, ref_cpi


# --------------------------------------------------------------------------- #
#  ① ECA — Extended Cancellation Algorithm (직접파 + 정적 클러터 제거)
# --------------------------------------------------------------------------- #
def eca(surv, ref, n_taps=40):
    """감시신호에서 '기준의 지연복제(0-도플러)' 부분공간을 최소제곱으로 투영·제거.
    직접파누설 + 정적 클러터(지연만 있고 도플러 0)를 없앤다. (Doppler 있는 표적은 보존)
      n_taps : 제거할 지연(거리) 탭 수 — 가까운 클러터 영역 폭.
    효율 구현: XᴴX 는 ref 자기상관의 Hermitian Toeplitz, Xᴴsurv 는 교차상관 → N×n_taps
    행렬을 만들지 않고(메모리 O(N)) 계산. 잔차 = surv − (ref ∗ w)."""
    from scipy.signal import fftconvolve
    N = len(surv)
    R = np.array([np.vdot(ref[:N - d], ref[d:]) for d in range(n_taps)])   # 자기상관 lag 0..n
    idx = np.arange(n_taps); D = idx[None, :] - idx[:, None]               # j−i
    XhX = np.where(D <= 0, R[np.abs(D)], np.conj(R[np.abs(D)])) + 1e-6 * np.eye(n_taps)
    C = np.array([np.vdot(ref[:N - i], surv[i:]) for i in range(n_taps)])  # 교차상관 Xᴴsurv
    w = np.linalg.solve(XhX, C)
    return surv - fftconvolve(ref, w)[:N]          # ref ∗ w (인과 FIR) 제거


# --------------------------------------------------------------------------- #
#  ② CAF 거리-도플러 맵 (프레임 정합필터 + slow-time FFT)
# --------------------------------------------------------------------------- #
def range_doppler(surv, ref, fs, M, n_range=None):
    """CPI(surv,ref) → (거리축 Rb[m], 도플러축 f_d[Hz], |RD| 맵[도플러,거리]).
    프레임마다 순환상관(정합필터)으로 거리, 프레임축 FFT 로 도플러."""
    Lf = len(ref) // M
    n_range = n_range or Lf
    S = surv[:M * Lf].reshape(M, Lf)
    Rf = np.conj(np.fft.fft(ref[:Lf]))             # 한 프레임 기준
    RP = np.fft.ifft(np.fft.fft(S, axis=1) * Rf[None, :], axis=1)   # (M, Lf) 거리프로파일
    RP = RP[:, :n_range]
    win = np.hanning(M)[:, None]                   # slow-time Hann (도플러 부엽 억제)
    RD = np.fft.fftshift(np.fft.fft(RP * win, axis=0), axes=0)      # (M, n_range) slow-time FFT
    prf = fs / Lf
    f_d = np.fft.fftshift(np.fft.fftfreq(M, d=1 / prf))             # 도플러축
    Rb = np.arange(n_range) * C0 / fs                              # 바이스태틱 거리축
    return Rb, f_d, np.abs(RD)


# --------------------------------------------------------------------------- #
#  ③ 2D CA-CFAR 검출
# --------------------------------------------------------------------------- #
def ca_cfar_2d(rd, guard=(2, 2), train=(6, 6), pfa=1e-4):
    """셀평균 CFAR. rd=|RD|(도플러×거리). 반환 (검출마스크, 임계맵, 추정잡음)."""
    P = rd ** 2                                    # 전력
    gd, gr = guard; td, tr = train
    nd, nr = P.shape
    det = np.zeros_like(P, bool); thr = np.zeros_like(P)
    win_d, win_r = gd + td, gr + tr
    # CA-CFAR 스케일: alpha = Ntrain (Pfa^(-1/N) − 1)
    for i in range(nd):
        for j in range(nr):
            d0, d1 = max(0, i - win_d), min(nd, i + win_d + 1)
            r0, r1 = max(0, j - win_r), min(nr, j + win_r + 1)
            blk = P[d0:d1, r0:r1].copy()
            gd0, gd1 = max(0, i - gd), min(nd, i + gd + 1)
            gr0, gr1 = max(0, j - gr), min(nr, j + gr + 1)
            # 학습셀 평균 = (전체블록합 − 가드블록합) / 학습셀수
            tot = blk.sum(); gblk = P[gd0:gd1, gr0:gr1].sum()
            ntr = blk.size - (gd1 - gd0) * (gr1 - gr0)
            if ntr <= 0:
                continue
            noise = (tot - gblk) / ntr
            alpha = ntr * (pfa ** (-1.0 / ntr) - 1.0)
            thr[i, j] = alpha * noise
            det[i, j] = P[i, j] > thr[i, j]
    return det, np.sqrt(thr), None


def peak_detection(Rb, f_d, rd, det):
    """검출 마스크에서 최댓값 셀의 (거리, 도플러, 값) 반환."""
    masked = np.where(det, rd, 0.0)
    if masked.max() <= 0:
        return None
    di, ri = np.unravel_index(np.argmax(masked), masked.shape)
    return dict(Rb=float(Rb[ri]), fd=float(f_d[di]), val=float(rd[di, ri]),
                di=int(di), ri=int(ri))


if __name__ == "__main__":
    from waveforms import lte_downlink
    wf = lte_downlink(occupancy="G3")
    fs = wf.fs_hz; ref_frame = wf.tx
    M = 48
    Lf = len(ref_frame); prf = fs / Lf
    # 표적: Rb=300m → τ, f_d=120Hz
    Rb_true = 300.0; tau = Rb_true / C0; fd_true = 120.0
    surv, ref = make_cpi(ref_frame, M, fs, tau, fd_true, a_tgt=1.0,
                         dpi_amp=50.0, snr_db=12.0)
    print(f"LTE CPI: M={M} 프레임, PRF={prf:.0f}Hz, 최대무모호도플러=±{prf/2:.0f}Hz, "
          f"Δf_d={prf/M:.1f}Hz, ΔRb={C0/wf.bw_hz:.1f}m")
    surv_c = eca(surv, ref, n_taps=40)
    for tag, sig in [("ECA 전", surv), ("ECA 후", surv_c)]:
        Rb, f_d, rd = range_doppler(sig, ref, fs, M, n_range=int(800 / (C0 / fs)))
        det, thr, _ = ca_cfar_2d(rd, pfa=1e-4)
        pk = peak_detection(Rb, f_d, rd, det)
        zd = np.argmin(np.abs(f_d))
        print(f"  {tag}: 0-도플러 최대={20*np.log10(rd[zd].max()+1e-9):.1f}dB  "
              f"검출={'(%.0fm, %+.0fHz)'%(pk['Rb'],pk['fd']) if pk else '없음'}")
