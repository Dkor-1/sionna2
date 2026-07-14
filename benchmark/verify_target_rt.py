# -*- coding: utf-8 -*-
"""
verify_target_rt.py — **표적 에코를 Sionna RT 로 직접 뽑아 PO 예측과 대조**한다.
=================================================================================
문제 제기(정당함): "Sionna 시뮬레이션이 목적인데 표적 RCS·에코를 PO 로 구하면
Sionna 로 검증했다고 할 수 있나?"

그래서 이 스크립트는 **표적 에코 자체를 두 방법으로 각각 계산해 비교**한다.

  · Sionna RT : 챔버+드론 장면을 광선추적 → 표적 근방을 지나는 경로들의 복소이득 합
                a_echo 를 직접파 a_dir 로 나눈 **진폭비**(절대보정 무관).
  · PO+링크버짓 : 같은 기하에서 바이스태틱 레이더 방정식으로 같은 진폭비를 예측
                ratio = L·√(σ/4π) / (R1·R2)      (σ = 재질가중 PO)

핵심 질문 두 개:
  Q1. 두 값이 몇 dB 차이인가?  (일치하면 하이브리드 구성이 검증된다)
  Q2. RT 값이 **표본수(spp)** 에 따라 얼마나 흔들리는가?
      → 흔들림이 크면 "작은 드론의 절대 RCS 를 RT 로 뽑지 않는다"는 설계 결정의 정량 근거가 된다.
      (흔들리지 않으면 그 결정은 근거가 없는 것이므로 재고해야 한다 — 그 경우도 정직하게 보고한다.)

실행: CUDA_VISIBLE_DEVICES=2 python benchmark/verify_target_rt.py
"""
from __future__ import annotations
import os, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
sys.path.insert(0, HERE)

from bistatic_scene import TX, RX, TGT, bistatic_params          # noqa: E402
from channel import SionnaRTChannel, bistatic_rcs_m2             # noqa: E402

FC = 3.5e9
DRONE = "mavic4pro"
VEL = (-3.0, 1.8, 0.6)


def analytic_ratio(sigma_m2, p):
    """바이스태틱 레이더방정식의 (표적에코/직접파) **진폭비**.
      P_echo/P_dir = σ·L² / (4π·R1²·R2²)  →  진폭비 = L·√(σ/4π)/(R1·R2)
    """
    return p["L"] * np.sqrt(sigma_m2 / (4 * np.pi)) / (p["R1"] * p["R2"])


def main():
    p = bistatic_params(TX, RX, TGT, VEL, FC)
    sigma = bistatic_rcs_m2(DRONE, FC, p["u1"], p["u2"], az_span_deg=8.0, n_az=5)
    r_po = analytic_ratio(sigma, p)
    print("=" * 78)
    print("표적 에코: Sionna RT vs PO+링크버짓 — 같은 기하, 같은 양(직접파 대비 진폭비)")
    print("=" * 78)
    print(f"기하: L={p['L']:.2f} m  R1={p['R1']:.2f} m  R2={p['R2']:.2f} m")
    print(f"PO 재질가중 σ(bistatic) = {10*np.log10(sigma):.2f} dBsm")
    print(f"→ PO 예측 진폭비 = {r_po:.3e}  ({20*np.log10(r_po):+.2f} dB)\n")

    rows = []
    for chamber in (False, True):
        for spp in (200_000, 1_000_000, 4_000_000):
            t0 = time.time()
            ch = SionnaRTChannel(with_chamber=chamber, spp=spp, max_depth=3)
            st = ch.state(TX, RX, TGT, VEL, FC, DRONE)
            dt = time.time() - t0
            r_rt = st.rt_echo_ratio
            if r_rt is None:
                print(f"  {'챔버' if chamber else '자유공간'} spp={spp:>9,} → RT 표적경로 **0개** "
                      f"(에코 못 찾음, {dt:.0f}s)")
                rows.append((chamber, spp, None, None))
                continue
            d = 20 * np.log10(r_rt / r_po)
            print(f"  {'챔버' if chamber else '자유공간'} spp={spp:>9,} → RT 비 {r_rt:.3e} "
                  f"({20*np.log10(r_rt):+.2f} dB) · PO 대비 {d:+.2f} dB · 클러터 {len(st.clutter)}개 · {dt:.0f}s")
            rows.append((chamber, spp, r_rt, d))

    print("\n" + "=" * 78)
    print("판정")
    print("=" * 78)
    for chamber in (False, True):
        vals = [r for (c, s, r, d) in rows if c == chamber and r is not None]
        if len(vals) >= 2:
            db = 20 * np.log10(np.array(vals))
            print(f"  {'챔버' if chamber else '자유공간'}: RT 값의 spp 간 산포 = {db.max()-db.min():.2f} dB "
                  f"(min {db.min():+.1f} / max {db.max():+.1f} dB)")
        ds = [d for (c, s, r, d) in rows if c == chamber and d is not None]
        if ds:
            print(f"          PO 대비 편차 = {np.mean(ds):+.2f} dB (평균), 범위 {min(ds):+.1f}~{max(ds):+.1f} dB")
    print("\n해석 기준:")
    print("  · |PO 대비 편차| ≲ 3 dB 이고 spp 산포 ≲ 1 dB  → RT 와 PO 가 일치. 하이브리드 검증됨.")
    print("  · spp 산포가 크다(≳3 dB)              → RT 절대 RCS 불안정 = PO 를 쓰는 설계의 정량 근거.")
    print("  · 편차가 크고 산포는 작다              → 계통 차이. 원인(재질·편파·경로분류)을 규명해야 함.")


if __name__ == "__main__":
    main()
