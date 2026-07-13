# -*- coding: utf-8 -*-
"""
bistatic_scene.py — (report4) 바이스태틱 패시브 레이더 기하
============================================================

진짜 패시브 레이더는 **송신기(TX=주변 기지국/AP, illuminator of opportunity)** 와
**수신기(RX)** 가 떨어져 있고, 그 사이를 드론(표적)이 지난다. 측정량은 '바이스태틱':

  베이스라인  L  = |TX−RX|
  경로합      R1+R2 = |TX→표적| + |표적→RX|
  바이스태틱 거리 Rb = (R1+R2) − L   (직접파 대비 '추가 경로')  → 지연 τ = Rb/c
  바이스태틱 도플러 f_d = −(1/λ)·d(R1+R2)/dt = +(1/λ)·v·(û1+û2)
    (û1=표적→TX, û2=표적→RX 단위벡터. dR1/dt=−û1·v 이므로 경로가 길어지면=멀어지면 f_d<0)
  바이스태틱 각  β  = û1, û2 사이 각

등Rb 면은 TX·RX 를 초점으로 하는 **타원체**(2D 에선 타원). 한 수신기로는 (Rb, f_d) 만,
거리분해능 ΔRb=c/B, 도플러분해능 Δf_d=1/T_CPI. (AoA 를 더하면 위치 확정 — report4 확장.)
"""
from __future__ import annotations
import numpy as np

C0 = 299792458.0

# --- 무반사 챔버(30×20×11 m) 내부 바이스태틱 배치 — report4/benchmark 의 단일 출처 -------- #
#     (viz_bistatic·build_report4·benchmark 가 모두 여기서 import 한다)
CHAMBER = (30.0, 20.0, 11.0)      # 내부 치수 W(x)·D(y)·H(z)  (report1 과 동일)
TX = (4.0, 2.5, 8.0)              # 신호원(illuminator) 안테나 — 한쪽 측벽 상단
RX = (4.0, 17.5, 6.5)             # 패시브 수신 안테나 — 반대 측벽
TGT = (21.0, 10.0, 5.5)           # 표적 드론(quiet zone)
VEL = (-3.0, 2.0, 0.5)            # 표적 속도[m/s] — 실내 저속

# 무반사 잔향 클러터(약함): (지연[s], 진폭). DPI 대비 ~−25~−30 dB 수준(dpi_amp≈55~60 기준).
#   바닥/장비 반사·흡수체 불완전에서 오는 약한 0-도플러 잔향. ECA 가 DPI 와 함께 제거한다.
CH_CLUTTER = ((8e-9, 3.0), (22e-9, 2.0), (45e-9, 1.4))


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
    fd = float(vel @ (u1 + u2)) / lam                       # 바이스태틱 도플러(멀어지면 <0)
    beta = float(np.degrees(np.arccos(np.clip(u1 @ u2, -1, 1))))
    return dict(L=L, R1=R1, R2=R2, Rb=Rb, tau=tau, fd=fd, beta=beta, lam=lam,
                u1=u1, u2=u2)


def bistatic_velocity_to_doppler(v_radial_sum, fc):
    """경로변화율(dR1/dt+dR2/dt)[m/s] → 도플러[Hz].  f_d = −(1/λ)·d(R1+R2)/dt (멀어지면<0)."""
    return -v_radial_sum / (C0 / fc)


if __name__ == "__main__":
    # 예: 무반사 챔버(30×20×11) 내부 — TX/RX 를 양쪽 측벽에, 표적이 quiet zone 을 비행
    for (pos, vel) in [(TGT, VEL), ((24, 13, 5.0), (2, -3, 0))]:
        p = bistatic_params(TX, RX, pos, vel, 3.5e9)
        print(f"표적{pos} v{vel}: L={p['L']:.1f}m Rb={p['Rb']:.1f}m "
              f"τ={p['tau']*1e9:.0f}ns f_d={p['fd']:+.1f}Hz β={p['beta']:.0f}°")
