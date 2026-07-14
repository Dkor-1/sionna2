# -*- coding: utf-8 -*-
"""
sionna_chain.py — **완전 Sionna 신호 체인**: RT 경로 → Sionna PHY 채널 → 감시신호
====================================================================================
지금까지 우리는 `passive_process.make_cpi()` 로 **직접** 감시신호를 합성했다
(지연복제 + 도플러 + 잡음을 손으로 더함). 이제 **Sionna PHY 가 그 일을 한다.**

    Sionna RT PathSolver ──► (a, τ) ──► sionna.phy.channel.cir_to_time_channel
                                                    │  (sinc 펄스정형 포함)
                                                    ▼
    파형(WiFi/LTE/5G) ──────────────────► ApplyTimeChannel ──► 감시신호
                                                    │
                                                    ▼
                                    ECA → 거리-도플러 → CFAR  (레이더 고유 — Sionna 에 없음)

■ 하이브리드는 그대로 유지된다 (docs/VERIFY_RT_VS_PO.md)
    · **환경 경로(직접파·벽·바닥)** = Sionna RT 가 준 (a, τ) 를 **그대로** 쓴다.
      RT 는 큰 면에서 정확하다 — 바닥 반사가 프레넬 예측과 0.02 dB 로 일치했다.
    · **표적 경로(에코·유령)** = 기하는 거울상, 진폭은 **SBR**(rcs_sbr) 로 만든 (a, τ) 를 **주입**한다.
      RT 는 18 m 의 60 cm 표적을 못 본다(광선 4억 발에도 수렴 안 함, 산란계수 S 에 비례).

■ 왜 이게 나은가 (make_cpi 대비)
    · 지연 보간을 우리가 안 짠다 — Sionna 의 sinc 필터가 정확히 처리한다.
    · 도플러도 Sionna 가 시간축으로 준다(a 가 시간 의존).
    · RT 가 찾은 **모든** 환경 경로가 자동으로 들어온다 (우리가 상위 8개만 고르지 않는다).
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from gpu import pick as _pick_gpu    # noqa: E402  (mitsuba/torch import 전에!)
_pick_gpu(verbose=False)

import numpy as np                   # noqa: E402
import torch                         # noqa: E402
from sionna.phy.channel import (cir_to_time_channel, ApplyTimeChannel,   # noqa: E402
                                time_lag_discrete_time_channel)

C0 = 299792458.0


# --------------------------------------------------------------------------- #
#  (a, τ) 를 Sionna 가 기대하는 텐서 모양으로
# --------------------------------------------------------------------------- #
def as_cir(a, tau, n_time: int = 1):
    """복소이득 a[(P,) 또는 (P, T)] · 지연 tau[(P,)] → Sionna CIR 텐서.

    Sionna 규약:
      a   : [batch, num_rx, num_rx_ant, num_tx, num_tx_ant, num_paths, num_time_steps]
      tau : [batch, num_rx, num_tx, num_paths]
    우리는 단일 송수신(1×1) 이므로 앞의 축은 전부 1."""
    a = np.asarray(a)
    if a.ndim == 1:
        a = a[:, None] * np.ones((1, n_time))
    tau = np.asarray(tau, float)
    A = torch.from_numpy(a.astype(np.complex64))[None, None, None, None, None]  # (1,1,1,1,1,P,T)
    T = torch.from_numpy(tau.astype(np.float32))[None, None, None]              # (1,1,1,P)
    return A, T


def channel_taps(a, tau, bandwidth: float, max_delay_spread: float = 1e-6,
                 n_time: int = 1):
    """RT/SBR 경로 → **이산시간 채널 탭** (Sionna 의 sinc 펄스정형).
    반환: (h[…, l_tot], l_min, l_max)"""
    l_min, l_max = time_lag_discrete_time_channel(bandwidth, max_delay_spread)
    A, T = as_cir(a, tau, n_time=n_time)
    h = cir_to_time_channel(bandwidth, A, T, l_min, l_max, normalize=False)
    return h, l_min, l_max


def n_time_steps(n_samples: int, bandwidth: float, max_delay_spread: float = 1e-6) -> int:
    """ApplyTimeChannel 이 요구하는 **채널 시점 수** = N + l_tot − 1.
    (출력 샘플마다 채널이 한 번씩 평가되므로 신호 길이보다 l_tot−1 만큼 길다.)
    도플러가 실린 a 를 만들 때 이 길이로 만들어야 한다."""
    l_min, l_max = time_lag_discrete_time_channel(bandwidth, max_delay_spread)
    return int(n_samples + (l_max - l_min + 1) - 1)


def apply(x, a, tau, bandwidth: float, max_delay_spread: float = 1e-6):
    """파형 x[(N,) 복소] 에 채널 (a, τ) 를 **Sionna 로** 적용 → 감시신호 y[(N,)].
      a : (P,) 정지 채널  또는  (P, T) 시간가변(도플러).
          T 는 n_time_steps(N, bandwidth) 여야 한다 — 안 맞으면 여기서 알려준다."""
    x = np.asarray(x, np.complex64)
    N = x.shape[0]
    a = np.asarray(a)
    l_min, l_max = time_lag_discrete_time_channel(bandwidth, max_delay_spread)
    l_tot = l_max - l_min + 1
    T_need = N + l_tot - 1

    if a.ndim == 1:                                     # 정지 → 시간축 브로드캐스트
        a = a[:, None] * np.ones((1, T_need))
    elif a.shape[1] != T_need:
        raise ValueError(
            f"a 의 시간축이 {a.shape[1]} 인데 {T_need} 여야 합니다 "
            f"(= 신호길이 {N} + l_tot {l_tot} − 1). n_time_steps() 로 미리 구하세요.")

    A, T = as_cir(a, tau)
    h = cir_to_time_channel(bandwidth, A, T, l_min, l_max, normalize=False)
    app = ApplyTimeChannel(num_time_samples=N, l_tot=l_tot)
    X = torch.from_numpy(x)[None, None, None, :]          # (1,1,1,N)
    y = app(X, h)
    return y.detach().cpu().numpy().reshape(-1)[:N]


# --------------------------------------------------------------------------- #
#  표적 경로 → (a, τ) — 진폭은 **SBR**, 기하는 거울상
# --------------------------------------------------------------------------- #
def target_paths(tx, rx, tgt, vel, fc, sigma_m2, fs, n_time,
                 floor_ghost=True, eps_r=5.24, sigma_c=0.1231):
    """표적 에코 + (선택) 바닥 유령 → (a, tau).  **도플러는 시간축 a 에 실어 준다.**

      sigma_m2 : 표적 RCS [m²] — rcs_sbr 에서 온다(가림 포함).
    반환: a[(P, n_time)] 복소, tau[(P,)] — **직접파 기준 상대지연**."""
    tx, rx, tgt, vel = (np.asarray(v, float) for v in (tx, rx, tgt, vel))
    lam = C0 / fc
    L = np.linalg.norm(rx - tx)
    n = np.arange(n_time) / fs

    def one(rx_eff, gamma=1.0):
        R1 = np.linalg.norm(tgt - tx)
        R2 = np.linalg.norm(rx_eff - tgt)
        u1 = (tx - tgt) / R1
        u2 = (rx_eff - tgt) / R2
        fd = float(vel @ (u1 + u2)) / lam                    # bistatic_scene 과 동일 규약
        tau = (R1 + R2 - L) / C0
        # 바이스태틱 레이더방정식(직접파 대비 진폭비)
        amp = gamma * np.sqrt(sigma_m2) * L / (np.sqrt(4 * np.pi) * R1 * R2)
        return amp * np.exp(1j * 2 * np.pi * fd * n), tau, fd

    a0, t0, fd0 = one(rx)
    A, T = [a0], [t0]
    if floor_ghost:
        rx_img = rx.copy(); rx_img[2] = -rx_img[2]          # 바닥(z=0) 거울상
        d = rx_img - tgt
        th = np.arctan2(np.linalg.norm(d[:2]), abs(d[2]))
        eps = eps_r - 1j * sigma_c / (2 * np.pi * fc * 8.8541878128e-12)
        ct, root = np.cos(th), np.sqrt(eps - np.sin(th) ** 2)
        g = abs((eps * ct - root) / (eps * ct + root))       # V편파 = 입사면 평행(TM)
        a1, t1, _ = one(rx_img, gamma=g)
        A.append(a1); T.append(t1)
    return np.array(A), np.array(T)


if __name__ == "__main__":
    from bistatic_scene import TX, RX, TGT
    fs, fc, N = 122.88e6, 3.5e9, 4096
    print("Sionna PHY 신호 체인 자기점검\n" + "=" * 66)
    T = n_time_steps(N, fs)
    a, tau = target_paths(TX, RX, TGT, (-3.0, 0, 0), fc, sigma_m2=10 ** (-2.2), fs=fs, n_time=T)
    print(f"표적 경로 {len(tau)}개  (채널 시점 {T} = 신호 {N} + l_tot−1):")
    for i, t in enumerate(tau):
        nm = "표적 에코" if i == 0 else "바닥 유령"
        print(f"  {nm:10s} Rb={t*C0:6.2f} m  |a|={20*np.log10(abs(a[i,0])):+7.1f} dB (직접파 대비)")
    print(f"  → 유령/에코 = {20*np.log10(abs(a[1,0])/abs(a[0,0])):+.1f} dB, "
          f"거리차 {(tau[1]-tau[0])*C0:+.2f} m")
    x = (np.random.randn(N) + 1j * np.random.randn(N)).astype(np.complex64) / np.sqrt(2)
    y = apply(x, a, tau, bandwidth=fs)
    print(f"\nApplyTimeChannel: 입력 {x.shape} → 출력 {y.shape}  "
          f"(전력비 {20*np.log10(np.std(y)/np.std(x)):+.1f} dB — 표적경로만이라 매우 약함)")
    print("✅ Sionna PHY 가 RT/SBR 경로를 신호에 먹였습니다. make_cpi 를 대체합니다.")
