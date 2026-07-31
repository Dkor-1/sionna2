# -*- coding: utf-8 -*-
"""
passive_process.py — (report4) 바이스태틱 패시브 레이더 처리 체인
==================================================================

문헌 표준 파이프라인 — Martelli·Murgia·Colone·Bongioanni·Lombardo(Sapienza),
"Detection and 3D localization of ultralight aircrafts and drones with a WiFi-based Passive Radar"
가 정리한 체인(방해 제거 → 바이스태틱 거리-속도 맵 → CA-CFAR → 다중프레임 판정 → Kalman)의
**앞 세 단계**를 구현한다. LTE/5G 패시브레이더 문헌(예: Maksymiuk 외, "5G Network-Based Passive
Radar for Drone Detection", IRS 2023)도 같은 골격이다.
⚠ 단, 우리 제거단은 **standard ECA** 다 — 아래 ECACanceller 는 CPI 전체에 대한 1회 최소제곱 사영
(지연 부분공간만, 배치·슬라이딩 없음)이다. 위 Sapienza 논문이 쓰는 것은 sliding 판 **ECA-S**
(Colone·Palmarini·Martelli·Tilli, IEEE TAES 52(3):1309-1326, 2016)이고, ECA-S 의 장점으로 인용되는
'low-Doppler 표적 보존'은 standard ECA 에 그대로 주장할 수 없다(챔버 드론이 수 m/s 대 저도플러라
이 구분이 특히 중요하다). 다중프레임 판정·Kalman 은 미구현 = 범위 밖.

구현하는 체인:

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

    def __init__(self, ref, n_taps=40, ridge_rel=0.0):
        """ridge_rel>0: **상대 대각로딩** — 대역제한(가드/DC 널) 기준신호의 자기상관 행렬이
        준특이라 Cholesky 가 깨질 때 R[0](신호전력)의 ridge_rel 배를 더한다. 기본 0 이면
        기존 동작(절대 1e-6)과 완전히 동일 — 다른 리포트 재현성 불변."""
        self.ref = np.asarray(ref)
        self.n_taps = int(n_taps)
        N = len(self.ref); n = self.n_taps
        R = np.array([np.vdot(self.ref[:N - d], self.ref[d:]) for d in range(n)])  # 자기상관 lag 0..n
        idx = np.arange(n); D = idx[None, :] - idx[:, None]                        # j−i
        load = 1e-6 + float(ridge_rel) * abs(R[0])
        XhX = np.where(D <= 0, R[np.abs(D)], np.conj(R[np.abs(D)])) + load * np.eye(n)
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


# --------------------------------------------------------------------------- #
#  ⚠ CFAR 교정 — report4 [E1] 이 측정한 것 (2026-07-14)
# --------------------------------------------------------------------------- #
#  **경험적 오경보율은 명목값과 다르다. 그리고 파형마다 다르다.**
#
#  구현·alpha 식 자체는 완벽하다 — 이상적 백색 맵(5.76e8 셀)에서 배율 1.00,
#  alpha 가 이론식 N(Pfa^(-1/N) - 1) 와 상대오차 7.6e-16 로 일치한다.
#  그런데 **실제 거리-도플러 맵은 백색이 아니다**:
#    · slow-time **Hann 창**이 도플러축 인접셀을 상관시킨다 (rho ≈ +0.46, 전 파형 공통)
#    · 기준신호 대역이 fs 보다 좁으면 **거리축이 과표본**돼 상관된다
#      (LTE CRS 18 MHz << fs 30.7 MHz → rho ≈ +0.28)
#    · 유효 독립 훈련셀 비율: WiFi 0.49 / NR 0.40 / **LTE 0.31**
#  → CA-CFAR 의 "훈련셀은 독립" 가정이 깨져 잡음 추정이 낮아지고 **문턱이 느슨해진다.**
#
#  운용 형상(DPI + ECA, 챔버 거리창)에서 측정한 배율 (경험/명목):
#      명목 1e-4 :  WiFi **1.45x**  ·  LTE **2.47x**  ·  NR **1.56x**
#      명목 1e-6 :  WiFi 2.83x      ·  LTE 4.43x      ·  NR 2.22x
#
#  ❗ **이것이 벤치마크의 공정성을 깨뜨린다.** "같은 명목 Pfa 에서 조명원 비교" 는
#     실제로는 **LTE 에게 5G 보다 1.6배 느슨한 문턱**을 준 비교였다.
#     → Pd 를 비교하려면 **경험적 Pfa 를 맞춰야 한다.** 아래 표를 쓰거나,
#       ROC 를 **경험적 Pfa 축**에 그릴 것.
#
#  대조군이 원인을 확정했다(NR100, 9.6e7 셀): Hann 제거 → 배율 1.02,
#  백색화 정합필터 → 1.19, 둘 다 → **1.00**.
#
#  재현: python benchmark/verify_cfar.py  → outputs/verify_cfar.json
# ⚠ **이 표는 측정값의 사본이다 — 원본은 outputs/verify_cfar.json 이다.**
#   2026-07-29: 사본이 원본과 어긋난 것을 발견했다. 새 CFAR 측정(15919 s) 대비
#     LTE 1e-4  3.28e-5 → 2.9046e-5  (**-11.4 %**)
#     LTE 1e-5  2.16e-6 → 1.8772e-6  (**-13.1 %**)
#   나머지 밴드는 5 % 안. 그런데 report12 가 이 표를 소비하므로, 사본이 낡으면 **문턱이 명목과
#   다른 지점에 찍히고 Pd 비교의 공정성이 깨진다** — 이 표가 존재하는 이유 자체가 무력화된다.
#   → 값을 갱신하는 것만으로는 또 낡는다. **원본 JSON 을 우선 읽고, 리터럴은 폴백**으로 둔다.
#     JSON 이 있으면 자동으로 최신이 되고, 어긋나면 경고한다.
_PFA_FALLBACK = {
    # 파형 -> {목표 경험적 Pfa : 줘야 할 명목 Pfa}   (운용 형상: DPI+ECA, op 창, 0-도플러 마스킹 width=1,
    #  guard 2x2 / train 6x6). 값 출처: outputs/verify_cfar.json 2026-07-29 실측(외삽 없음).
    "wifi": {1e-3: 7.726e-4, 1e-4: 6.518e-5, 1e-5: 4.885e-6},
    "lte":  {1e-3: 4.868e-4, 1e-4: 2.905e-5, 1e-5: 1.877e-6},   # ← 가장 많이 조여야 한다
    "nr":   {1e-3: 7.602e-4, 1e-4: 6.460e-5, 1e-5: 5.533e-6},
}
_PFA_JSON_MAP = {"wifi": "WiFi80", "lte": "LTE20", "nr": "NR100"}
_PFA_CACHE = None


def _load_pfa_calibration(warn=True):
    """`outputs/verify_cfar.json` 의 **측정 원본**에서 교정표를 읽는다. 없으면 폴백.

    운용 형상 규약: `chain[밴드]['dpi_eca']['calib_op_mask1']['points']`
      — DPI+ECA, op(운용) 거리창, 0-도플러 마스킹 width=1. 이 세 가지가 report4/5/12 의 형상이다.
    `extrapolated=True` 인 점은 **버린다**(측정 구간 밖은 근거가 없다)."""
    global _PFA_CACHE
    if _PFA_CACHE is not None:
        return _PFA_CACHE
    import json as _json
    import os as _os
    p = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                      "outputs", "verify_cfar.json")
    out = {k: dict(v) for k, v in _PFA_FALLBACK.items()}
    try:
        with open(p, encoding="utf-8") as f:
            d = _json.load(f)
        for std, band in _PFA_JSON_MAP.items():
            pts = d["chain"][band]["dpi_eca"]["calib_op_mask1"]["points"]
            meas = {float(q["pfa_target_emp"]): float(q["pfa_nominal_needed"])
                    for q in pts if not q.get("extrapolated")}
            if not meas:
                continue
            if warn:
                for t, v in out[std].items():
                    m = next((mv for mt, mv in meas.items() if abs(mt - t) / t < 1e-6), None)
                    if m is not None and abs(m / v - 1.0) > 0.02:
                        print(f"[pfa] ⚠ 사본이 낡았다: {std} Pfa={t:.0e} 리터럴 {v:.4e} vs "
                              f"측정 {m:.4e} ({(m/v-1)*100:+.1f}%). _PFA_FALLBACK 을 갱신할 것.",
                              flush=True)
            out[std] = meas
        out["_source"] = "outputs/verify_cfar.json"
        out["_generated"] = d.get("meta", {}).get("generated")
    except Exception as e:                                    # JSON 없음/형식 변경 → 폴백
        out["_source"] = f"_PFA_FALLBACK (원본 못 읽음: {type(e).__name__})"
    _PFA_CACHE = out
    return out


class _PfaCalibration(dict):
    """`PFA_CALIBRATION[std]` 처럼 쓰이던 기존 코드를 그대로 두기 위한 지연 로딩 dict."""

    def __missing__(self, key):
        return _load_pfa_calibration().get(key)

    def get(self, key, default=None):
        return _load_pfa_calibration().get(key, default)

    def __contains__(self, key):
        return key in _load_pfa_calibration()


PFA_CALIBRATION = _PfaCalibration()


def pfa_nominal_for(std: str, pfa_target: float) -> float:
    """**경험적** Pfa 목표 → ca_cfar_2d 에 줘야 할 **명목** Pfa.
    파형(std = 'wifi'|'lte'|'nr')마다 다르다 — 이걸 안 쓰면 Pd 비교가 공정하지 않다."""
    tab = PFA_CALIBRATION.get(str(std).lower())
    if not tab:
        return float(pfa_target)
    if pfa_target in tab:
        return tab[pfa_target]
    # 로그-로그 보간 (측정 구간 밖은 외삽 — 주의)
    ks = sorted(tab)
    lx = np.log10(ks); ly = np.log10([tab[k] for k in ks])
    return float(10 ** np.interp(np.log10(pfa_target), lx, ly))


def doppler_guard_mask(det, f_d, width=3, also_exclude_from_training=True):
    """**0-도플러 능선 가드** — report4 [E2/E1] 이 찾은 지뢰를 막는다 (2026-07-14).

    왜 필요한가:
      slow-time **Hann 창의 DFT 는 ±1 빈에서 −5.75 dB 밖에 안 떨어진다**(±2 는 −42.5 dB).
      그래서 직접파(DPI) 잔류가 0-도플러 행(zd)뿐 아니라 **zd±1 행에도 거의 그대로 실린다.**
      기존 코드의 `det[zd, :] = False` 는 그 두 행을 **못 지운다.**

    얼마나 위험한가 (측정, benchmark/verify_cfar.py):
      거리창이 ECA 탭 수(n_taps) 너머로 넓어지면 경험적 Pfa 가
        명목 1e-4 에서 **41~59배**,  명목 1e-6 에서 **1015~2328배** 로 폭발한다.
      지금까지 이 지뢰를 안 밟은 건 `chamber_window()` 가 n_taps = n_range + 8 로 잡아
      **거리창이 항상 ECA 탭 안에 들어오기 때문**이다 — **설계가 아니라 운(암묵적 의존)이다.**
      챔버가 커지거나 Rb 창을 넓히는 순간 무너진다.

      width=3(zd±1 까지) 로 마스킹하면 배율이 41~59배 → **0.65~0.82** 로 즉시 정상화된다.

    ⚠ 다만 width=3 만으로는 **과보정**(배율 0.65~0.82 < 1)이 된다 — 뜨거운 zd±1 행을
      *검출*에서만 빼고 *훈련셀*에는 그대로 두면 이웃 행의 잡음 추정이 부풀어 문턱이 과하게
      올라가기 때문이다. **제대로 하려면 훈련창에서도 배제**해야 한다(also_exclude_from_training).
      → 그 경우 ca_cfar_2d 를 그 행들을 뺀 부분맵에 적용하라. 이 함수는 검출 마스크만 다룬다.

    반환: 마스킹된 det (in-place 아님)."""
    det = np.asarray(det).copy()
    zd = int(np.argmin(np.abs(np.asarray(f_d))))
    h = int(width) // 2
    lo, hi = max(0, zd - h), min(det.shape[0], zd + h + 1)
    det[lo:hi, :] = False
    return det


def check_detector_config(wf, n_range, n_taps, M, pfa, verbose=True) -> list[str]:
    """**다음 벤치마크가 report4 의 결함을 조용히 반복하지 못하게** 하는 검사기.

    report4 가 측정으로 확정한 차단 결함 4개를 검사한다. 경고 목록을 돌려준다."""
    warn = []
    CFAR_WIN = 2 * (2 + 6) + 1          # guard 2 + train 6 → 한 축 훈련창 17 빈

    if n_range < CFAR_WIN:
        warn.append(
            f"[R2] 거리빈 {n_range}개 < CFAR 훈련창 {CFAR_WIN}빈 → **CFAR 가 1D 로 퇴화**한다. "
            f"파형 간 CFAR 형상이 달라지면 Pd 비교가 불공정하다. (LTE 가 실제로 6빈이었다)")
    if n_range > n_taps:
        warn.append(
            f"[R3] 거리창({n_range})이 ECA 탭({n_taps})보다 넓다 → DPI 잔류가 거리창 밖으로 새어 "
            f"**경험적 Pfa 가 41~2300배 폭발**한다. doppler_guard_mask(width=3) 를 반드시 쓸 것.")
    std = getattr(wf, "std", "").lower()
    if std in PFA_CALIBRATION:
        need = pfa_nominal_for(std, pfa)
        if abs(np.log10(need / max(pfa, 1e-30))) > 0.05:
            warn.append(
                f"[R1] 명목 Pfa {pfa:.1e} 를 그대로 쓰면 {std} 의 **경험적** Pfa 는 다르다. "
                f"경험적 {pfa:.1e} 를 원하면 명목 **{need:.2e}** 를 줄 것 "
                f"(pfa_nominal_for). 안 그러면 파형 간 Pd 비교가 서로 다른 오경보율에서 이뤄진다.")
    T_cpi = M * (len(wf.tx) / wf.fs_hz) if hasattr(wf, "tx") else None
    if T_cpi is not None:
        warn.append(
            f"[R4] 이 파형의 T_CPI = {T_cpi*1e3:.1f} ms (M={M}). **M 이 아니라 T_CPI 를 맞춰야** "
            f"공정하다 — M 고정은 프레임 길이가 다른 파형에 서로 다른 관측시간을 준다"
            f"(5G 24 ms vs WiFi/LTE 48 ms → 물리가 아닌 규약에서 3.01 dB 차이).")
    if verbose and warn:
        print("⚠ 검출기 설정 경고 (report4 근거):")
        for w in warn:
            print("   -", w)
    return warn
