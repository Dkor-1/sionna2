# -*- coding: utf-8 -*-
"""
link_budget.py — (benchmark) 바이스태틱 패시브 레이더 링크 버짓
================================================================
핵심 목적(공정성): 표적 에코 SNR/SCR 을 **손잡이로 주입하지 않고**, 고정된
조명예산(EIRP)·수신이득·잡음지수와 표적 RCS·기하·대역폭에서 **물리로 유도**한다.
그래서 신호(WiFi/LTE/5G)를 가르는 세 요소가 자동으로 반영된다:
  · 반송파(λ)  → 에코전력 ∝ λ² (그리고 RCS σ 도 반송파 의존)
  · 대역폭(B)  → 잡음전력 ∝ B   (넓을수록 잡음↑ = 공정성의 핵심 변수!)
  · 점유(에너지)→ 파형 자체 + 처리이득으로 반영(DSP 에서 자연히 나옴)

이것이 벤치마크 원칙 "SCR is measured, not swept" 를 코드로 옮긴 것이다.
(이전 report4 는 표적 SNR 을 직접 sweep 했음 → 공정성 위배. 여기서 바로잡는다.)

바이스태틱 레이더 방정식 (수신 에코전력):
    P_echo = EIRP · G_rx · λ² · σ_b / [ (4π)³ · R1² · R2² ]
직접파(Friis 편도, 베이스라인 L):
    P_dir  = EIRP · G_rx · λ² / [ (4π)² · L² ]
열잡음: P_n = k · T0 · F · B     (k=1.38e-23, T0=290K, F=잡음지수, B=수신대역)

반환값은 '잡음전력=1' 로 정규화한 전압이득(passive_process.make_cpi 규약):
    a_tgt   = sqrt(P_echo / P_n)     (표적 에코 전압이득)
    dpi_amp = sqrt(P_dir  / P_n)     (직접파 누설 전압이득)
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np

K_BOLTZ = 1.380649e-23        # 볼츠만 상수 [J/K]
T0 = 290.0                    # 기준 잡음온도 [K]
C0 = 299792458.0


def db2lin(db):
    return 10.0 ** (np.asarray(db, float) / 10.0)


def lin2db(x):
    return 10.0 * np.log10(np.maximum(x, 1e-300))


@dataclass
class LinkBudget:
    """고정하는 외부 예산(공정성의 '통제 변수'). **모든 신호에 동일 적용**한다."""
    eirp_dbm: float = 63.0         # 조명원 EIRP(기지국/AP). 63 dBm ≈ 2 kW(매크로 셀 대표값)
                                   # ※ 챔버 실험은 저출력 12 dBm 사용(run_min_cell.EIRP_DBM)
    rx_gain_dbi: float = 10.0      # 감시 수신 안테나 이득
    noise_figure_db: float = 5.0   # 수신 잡음지수
    sys_loss_db: float = 0.0       # 기타 시스템 손실(케이블·정합 등)

    # --- 개별 전력항 [W] ---
    def echo_power_w(self, lam, sigma_m2, R1, R2):
        eirp = db2lin(self.eirp_dbm) * 1e-3                 # dBm → W
        grx = db2lin(self.rx_gain_dbi)
        num = eirp * grx * lam ** 2 * sigma_m2
        den = (4 * np.pi) ** 3 * R1 ** 2 * R2 ** 2
        return num / den / db2lin(self.sys_loss_db)

    def direct_power_w(self, lam, L):
        eirp = db2lin(self.eirp_dbm) * 1e-3
        grx = db2lin(self.rx_gain_dbi)
        return eirp * grx * lam ** 2 / ((4 * np.pi) ** 2 * L ** 2) / db2lin(self.sys_loss_db)

    def noise_power_w(self, bw_hz):
        return K_BOLTZ * T0 * db2lin(self.noise_figure_db) * bw_hz


def link_terms(lb: LinkBudget, lam, sigma_m2, R1, R2, L, bw_hz):
    """물리량 → make_cpi 용 (a_tgt, dpi_amp) + 진단 dict. (잡음=1 정규화)

    반환 key:
      P_echo_w/P_direct_w/P_noise_w  물리 전력[W]
      snr_echo_db   = P_echo/P_n     (per-sample 에코 SNR — 물리로 유도된 값)
      snr_direct_db = P_dir/P_n
      dnr_db        = P_dir/P_echo   (직접파-에코비 → ECA 가 지워야 할 양)
      a_tgt, dpi_amp                 (전압이득; 참조파형 표본전력=1 정규화 전제)
    """
    Pe = lb.echo_power_w(lam, sigma_m2, R1, R2)
    Pd = lb.direct_power_w(lam, L)
    Pn = lb.noise_power_w(bw_hz)
    return dict(
        P_echo_w=Pe, P_direct_w=Pd, P_noise_w=Pn,
        snr_echo_db=float(lin2db(Pe / Pn)),
        snr_direct_db=float(lin2db(Pd / Pn)),
        dnr_db=float(lin2db(Pd / Pe)),
        a_tgt=float(np.sqrt(Pe / Pn)),
        dpi_amp=float(np.sqrt(Pd / Pn)),
    )


if __name__ == "__main__":
    # 챔버 데모: geometry 의 TX/RX/CENTER 기하 + 저출력 12 dBm + 5G NR 100 MHz(점유 B=98.28 MHz)
    from geometry import TX, RX, CENTER
    tx, rx, c = (np.asarray(p, float) for p in (TX, RX, CENTER))
    R1 = float(np.linalg.norm(tx - c))
    R2 = float(np.linalg.norm(rx - c))
    L = float(np.linalg.norm(tx - rx))
    lb = LinkBudget(eirp_dbm=12.0)
    lam = C0 / 3.5e9
    lt = link_terms(lb, lam, sigma_m2=10 ** (-1.8), R1=R1, R2=R2, L=L, bw_hz=98.28e6)
    print(f"5G NR 100MHz@3.5GHz, EIRP=12dBm, σ=-18dBsm, "
          f"R1={R1:.1f} R2={R2:.1f} L={L:.1f} (무반사 챔버):")
    for k, v in lt.items():
        print(f"  {k:14s} {v:.4g}")
