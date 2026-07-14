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
from scipy.linalg import cho_factor, cho_solve
from scipy.signal import fftconvolve

C0 = 299792458.0


# --------------------------------------------------------------------------- #
#  CPI(에코) 생성 — 기준 1프레임을 M번 반복, 표적/DPI/클러터/잡음 합성
# --------------------------------------------------------------------------- #
def make_cpi(ref_frame, M, fs, tau_s, fd_hz, a_tgt,
             dpi_amp=30.0, clutter=((15e-9, 8.0), (40e-9, 5.0)), snr_db=10.0,
             abs_noise=False, noise_var=1.0, rng=None, ghosts=()):
    """기준 1프레임 ref_frame 을 M번 반복한 CPI 에서 감시신호와 기준신호를 만든다.
      tau_s, fd_hz : 표적 지연[s]·도플러[Hz],  a_tgt : 표적 에코 전압이득
      dpi_amp      : 직접파누설 진폭(보통 표적보다 수십 dB 큼)
      clutter      : [(지연[s], 진폭), …] **정적(0-도플러)** 반사체
                     ※ 0-지연 탭은 DPI(dpi_amp, 0지연·0도플러)와 중복되므로 사용하지 않음
      ghosts       : [(지연[s], 도플러[Hz], 진폭), …] **도플러가 실린** 표적 경유 다중경로
                     (예: TX→표적→바닥→RX). 기본값 () — 켜지 않으면 기존 동작과 완전히 동일.
      abs_noise=False: snr_db(표적피크 대비)로 잡음 — 데모/RD맵 시각화용.
      abs_noise=True : 잡음전력=noise_var(절대 고정), 표적은 a_tgt 절대값 — Pd 연구용
                       (처리이득이 파형/점유마다 달라 Pd 가 의미있게 갈림).
    반환: (surv, ref_cpi)  — 둘 다 길이 M*Lf 복소.

    ⚠ **clutter 와 ghosts 는 ECA 앞에서 운명이 완전히 다르다** (측정으로 확인 — docs/VERIFY_CLUTTER.md):
      · clutter 는 지연된 기준신호의 **선형결합**이다(도플러 항이 없다). ECA 의 기저가 바로 그
        '지연된 기준신호들'이므로, ECA 의 사영이 **진폭과 무관하게 정확히 0 으로 지운다.**
        → 직접파보다 14 dB 센 클러터를 넣어도 SCR 이 2e-10 dB 밖에 안 움직인다.
        → 즉 이 하네스에서 **정적 클러터 진폭은 죽은 파라미터**다. 클러터 모델을 아무리 정교하게
          만들어도 Pd·SCR 은 안 바뀐다. (실제 ECA 는 유한 동적범위·클러터 도플러퍼짐 때문에
          이렇게 완벽하지 않다 — 그 한계는 아직 모델에 없다.)
      · ghosts 는 도플러가 있어 **그 부분공간 밖**이다 → ECA 가 못 지운다. 표적 근처에 **가짜
        검출**로 남는다. 챔버에서 실제로 문제되는 건 clutter 가 아니라 **이쪽**이다."""
    rng = rng or np.random.default_rng(0)
    Lf = len(ref_frame); N = M * Lf
    ref_cpi = np.tile(ref_frame, M)
    n = np.arange(N)

    def delayed(amp, tau):                         # 분수지연(주파수영역) + 진폭
        f = np.fft.fftfreq(N, d=1 / fs)
        return amp * np.fft.ifft(np.fft.fft(ref_cpi) * np.exp(-1j * 2 * np.pi * f * tau))

    surv = a_tgt * delayed(1.0, tau_s) * np.exp(1j * 2 * np.pi * fd_hz * n / fs)   # 표적
    surv = surv + dpi_amp * ref_cpi                                                # 직접파 누설(0지연·0도플러)
    for (ctau, camp) in clutter:                                                   # 정적 클러터(0-도플러) → ECA 가 정확히 소거
        surv = surv + camp * delayed(1.0, ctau)
    for (gtau, gfd, gamp) in ghosts:                                               # 표적 경유 유령(도플러 有) → ECA 통과
        surv = surv + gamp * delayed(1.0, gtau) * np.exp(1j * 2 * np.pi * gfd * n / fs)
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
class ECACanceller:
    """**참조 자기상관을 1회만** 계산해두고 여러 감시신호에 재사용하는 ECA.

    XᴴX(=ref 자기상관의 Hermitian Toeplitz)·그 Cholesky 인수는 ref 에만 의존하므로,
    같은 기준파형으로 N-trial Monte-Carlo 를 돌 때 **매 trial 재계산은 낭비**다. 여기서
    한 번 프리컴퓨트하면 per-trial 은 교차상관 Xᴴsurv + 후방대입 + FIR 제거만 남는다.
      n_taps : 제거할 지연(거리) 탭 수 — 가까운 클러터/직접파 영역 폭.
    (모듈 함수 eca() 는 이 클래스를 1회용으로 감싼 것 — 기존 호출부 호환.)"""

    def __init__(self, ref, n_taps=40):
        self.ref = np.asarray(ref)
        self.n_taps = int(n_taps)
        N = len(self.ref); n = self.n_taps
        R = np.array([np.vdot(self.ref[:N - d], self.ref[d:]) for d in range(n)])  # 자기상관 lag 0..n
        idx = np.arange(n); D = idx[None, :] - idx[:, None]                        # j−i
        XhX = np.where(D <= 0, R[np.abs(D)], np.conj(R[np.abs(D)])) + 1e-6 * np.eye(n)
        self._cho = cho_factor(XhX)                    # Hermitian PD → Cholesky 1회

    def cancel(self, surv):
        """감시신호에서 '기준의 지연복제(0-도플러)' 부분공간을 최소제곱 투영·제거.
        직접파누설 + 정적 클러터(지연만 있고 도플러 0)를 없앤다(도플러 있는 표적은 보존)."""
        surv = np.asarray(surv); N = len(surv)
        C = np.array([np.vdot(self.ref[:N - i], surv[i:]) for i in range(self.n_taps)])  # Xᴴsurv
        w = cho_solve(self._cho, C)
        return surv - fftconvolve(self.ref, w)[:N]     # ref ∗ w (인과 FIR) 제거


def eca(surv, ref, n_taps=40):
    """단발 ECA — ECACanceller(ref, n_taps).cancel(surv) 와 동일.
    반복 호출(같은 ref)이면 ECACanceller 를 만들어 .cancel() 을 재사용하라(자기상관 프리컴퓨트)."""
    return ECACanceller(ref, n_taps).cancel(surv)


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
    """셀평균 CFAR. rd=|RD|(도플러×거리). 반환 (검출마스크, 임계맵, 추정잡음전력).
      - 임계맵은 sqrt(전력임계) — 입력 rd(|RD|)와 같은 **진폭 스케일**.
      - 추정잡음전력은 셀별 훈련셀 박스평균(전력 스케일) 배열.

    적분영상(summed-area table)으로 **완전 벡터화** — 셀마다 학습창이 가장자리에서
    잘리는 것(가변 Ntrain)까지 정확히 반영해, 기존 이중 for-loop 구현과 **동일 출력**이며
    맵이 커질수록 크게 빠르다(Monte-Carlo·매트릭스에서 CFAR 를 수천 번 부를 때 중요)."""
    P = rd ** 2                                    # 전력
    gd, gr = guard; td, tr = train
    nd, nr = P.shape
    win_d, win_r = gd + td, gr + tr

    S = np.zeros((nd + 1, nr + 1))                 # 적분영상: S[a,b]=sum(P[:a,:b])
    S[1:, 1:] = np.cumsum(np.cumsum(P, axis=0), axis=1)

    def box_sum(r0, r1, c0, c1):                   # 합(P[r0:r1, c0:c1]), 경계 브로드캐스트
        return S[r1, c1] - S[r0, c1] - S[r1, c0] + S[r0, c0]

    i = np.arange(nd); j = np.arange(nr)
    r0 = np.clip(i - win_d, 0, nd)[:, None]; r1 = np.clip(i + win_d + 1, 0, nd)[:, None]
    c0 = np.clip(j - win_r, 0, nr)[None, :]; c1 = np.clip(j + win_r + 1, 0, nr)[None, :]
    gr0 = np.clip(i - gd, 0, nd)[:, None]; gr1 = np.clip(i + gd + 1, 0, nd)[:, None]
    gc0 = np.clip(j - gr, 0, nr)[None, :]; gc1 = np.clip(j + gr + 1, 0, nr)[None, :]

    tot = box_sum(r0, r1, c0, c1)                  # 전체 창 합 (가드 포함)
    gblk = box_sum(gr0, gr1, gc0, gc1)             # 가드 창 합
    ntr = (r1 - r0) * (c1 - c0) - (gr1 - gr0) * (gc1 - gc0)   # 학습셀 수(가변)
    ok = ntr > 0
    noise = np.where(ok, (tot - gblk) / np.where(ok, ntr, 1), 0.0)
    ntr_safe = np.where(ok, ntr, 1)
    alpha = ntr_safe * (pfa ** (-1.0 / ntr_safe) - 1.0)       # CA-CFAR: α=Ntr(Pfa^(−1/Ntr)−1)
    thr = alpha * noise
    det = ok & (P > thr)
    return det, np.sqrt(thr), noise


def _subbin(vm1, v0, vp1):
    """3점 포물선 피크의 서브빈 오프셋 δ∈[-0.5,0.5] (양자화된 빈 → 참 피크 위치 보간)."""
    den = vm1 - 2.0 * v0 + vp1
    if den >= 0:                                   # 볼록 피크가 아니면 보간 안 함
        return 0.0
    return float(np.clip(0.5 * (vm1 - vp1) / den, -0.5, 0.5))


def peak_detection(Rb, f_d, rd, det):
    """검출 마스크에서 최댓값 셀의 (거리, 도플러, 값) 반환.
    도플러·거리축에 **서브빈 포물선 보간**을 적용해, 참 표적이 DFT 빈 사이에 걸릴 때
    라벨이 실제 위치와 맞게 한다(빈 양자화 ±Δ/2 오차 완화)."""
    masked = np.where(det, rd, 0.0)
    if masked.max() <= 0:
        return None
    di, ri = np.unravel_index(np.argmax(masked), masked.shape)
    fd = float(f_d[di]); rb = float(Rb[ri])
    if 0 < di < rd.shape[0] - 1:                    # 도플러축 보간
        fd += _subbin(rd[di-1, ri], rd[di, ri], rd[di+1, ri]) * (f_d[1] - f_d[0])
    if 0 < ri < rd.shape[1] - 1:                    # 거리축 보간
        rb += _subbin(rd[di, ri-1], rd[di, ri], rd[di, ri+1]) * (Rb[1] - Rb[0])
    return dict(Rb=rb, fd=fd, val=float(rd[di, ri]), di=int(di), ri=int(ri))


if __name__ == "__main__":
    # 무반사 챔버(30×20×11 m) 내부 바이스태틱: Rb 는 수~수십 m (실외 수백 m 아님)
    from waveforms import nr_downlink
    wf = nr_downlink(occupancy="G3")
    fs = wf.fs_hz; ref_frame = wf.tx
    M = 48
    Lf = len(ref_frame); prf = fs / Lf
    # 챔버 표적: Rb≈22m → τ, f_d=65Hz. DPI 강하고 잔향(클러터)은 약함(무반사).
    Rb_true = 22.0; tau = Rb_true / C0; fd_true = 65.0
    surv, ref = make_cpi(ref_frame, M, fs, tau, fd_true, a_tgt=1.0, dpi_amp=55.0,
                         clutter=((8e-9, 3.0), (22e-9, 2.0), (45e-9, 1.4)), snr_db=12.0)
    print(f"5G 챔버 CPI: M={M} 프레임, PRF={prf:.0f}Hz, 최대무모호도플러=±{prf/2:.0f}Hz, "
          f"Δf_d={prf/M:.1f}Hz, ΔRb={C0/wf.bw_hz:.1f}m")
    surv_c = eca(surv, ref, n_taps=40)
    for tag, sig in [("ECA 전", surv), ("ECA 후", surv_c)]:
        Rb, f_d, rd = range_doppler(sig, ref, fs, M, n_range=int(45 / (C0 / fs)))
        det, thr, _ = ca_cfar_2d(rd, pfa=1e-4)
        pk = peak_detection(Rb, f_d, rd, det)
        zd = np.argmin(np.abs(f_d))
        print(f"  {tag}: 0-도플러 최대={20*np.log10(rd[zd].max()+1e-9):.1f}dB  "
              f"검출={'(%.0fm, %+.0fHz)'%(pk['Rb'],pk['fd']) if pk else '없음'}")
