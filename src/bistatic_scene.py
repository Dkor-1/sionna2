# -*- coding: utf-8 -*-
"""
bistatic_scene.py — (report4) 바이스태틱 패시브 레이더 기하
============================================================

진짜 패시브 레이더는 **송신기(TX=주변 기지국/AP, illuminator of opportunity)** 와
**수신기(RX)** 가 떨어져 있고, 그 사이를 드론(표적)이 지난다. 측정량은 '바이스태틱':

  베이스라인  L  = |TX−RX|
  경로합      R1+R2 = |TX→표적| + |표적→RX|
  바이스태틱 거리 Rb = (R1+R2) − L   (직접파 대비 '추가 경로')  → 지연 τ = Rb/c
  바이스태틱 도플러 f_d = −(1/λ)·v·(û1+û2)   (û1=표적→TX, û2=표적→RX 단위벡터)
  바이스태틱 각  β  = û1, û2 사이 각

등Rb 면은 TX·RX 를 초점으로 하는 **타원체**(2D 에선 타원). 한 수신기로는 (Rb, f_d) 만,
거리분해능 ΔRb=c/B, 도플러분해능 Δf_d=1/T_CPI. (AoA 를 더하면 위치 확정 — report4 확장.)
"""
from __future__ import annotations
import numpy as np

C0 = 299792458.0


def bistatic_params(tx, rx, tgt, vel, fc):
    """TX/RX/표적 위치[m]·표적속도[m/s]·반송파[Hz] → 바이스태틱 파라미터 dict."""
    tx, rx, tgt, vel = (np.asarray(v, float) for v in (tx, rx, tgt, vel))
    lam = C0 / fc
    L = np.linalg.norm(tx - rx)
    d1 = tx - tgt; d2 = rx - tgt
    R1 = np.linalg.norm(d1); R2 = np.linalg.norm(d2)
    u1 = d1 / max(R1, 1e-9); u2 = d2 / max(R2, 1e-9)        # 표적→TX, 표적→RX
    Rb = R1 + R2 - L                                        # 바이스태틱(추가) 거리
    tau = Rb / C0                                           # 상대 지연(직접파 기준)
    fd = -float(vel @ (u1 + u2)) / lam                      # 바이스태틱 도플러
    beta = float(np.degrees(np.arccos(np.clip(u1 @ u2, -1, 1))))
    return dict(L=L, R1=R1, R2=R2, Rb=Rb, tau=tau, fd=fd, beta=beta, lam=lam,
                u1=u1, u2=u2)


def bistatic_velocity_to_doppler(v_radial_sum, fc):
    """경로변화율(dR1/dt+dR2/dt)[m/s] → 도플러[Hz]."""
    return v_radial_sum / (C0 / fc)


if __name__ == "__main__":
    # 예: TX(기지국) 100m 옆, RX 원점, 표적이 감시영역을 가로지름
    tx = (0.0, 120.0, 30.0); rx = (0.0, 0.0, 5.0)
    for (pos, vel) in [((60, 60, 40), (15, 0, 0)), ((30, 80, 50), (0, -12, 0))]:
        p = bistatic_params(tx, rx, pos, vel, 3.5e9)
        print(f"표적{pos} v{vel}: L={p['L']:.0f}m Rb={p['Rb']:.1f}m "
              f"τ={p['tau']*1e9:.0f}ns f_d={p['fd']:+.1f}Hz β={p['beta']:.0f}°")
