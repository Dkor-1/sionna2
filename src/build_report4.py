# -*- coding: utf-8 -*-
"""build_report4.py — report4 (semi-anechoic 챔버 바이스태틱 패시브 레이더 탐지) 산출물 생성.

**GPU 필요** — 이제 report4 는 전부 Sionna 다:
  환경 경로 = Sionna RT / 표적 σ = SBR / 신호 합성 = Sionna PHY / 렌더 = Sionna RT 렌더러.
(ECA·CAF·CFAR 만 passive_process — 레이더 고유라 Sionna 에 없다.)

실행:  python src/build_report4.py              (그림 4장 + GIF + 노트북)
       python src/build_report4.py --no-gif     (GIF 생략 — 빠름)
       python src/build_report4.py --rt         (RT 환경경로 재측정)
"""
import argparse
import os
import subprocess
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (_HERE, os.path.abspath(os.path.join(_HERE, "..", "benchmark"))):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-gif", action="store_true")
    ap.add_argument("--rt", action="store_true", help="Sionna RT 환경경로 재측정")
    a = ap.parse_args()
    t0 = time.time()

    import numpy as np
    import viz_report4 as V
    from bistatic_scene import bistatic_params, TX, RX, TGT, VEL
    from geometry import floor_ghost

    print("=" * 70, "\n▶ 1) 챔버 바이스태틱 기하 + 바닥 유령\n", "=" * 70)
    for pos, vel in [(TGT, VEL), ((24, 13, 5.0), (2, -3, 0))]:
        p = bistatic_params(TX, RX, pos, vel, 3.5e9)
        g = floor_ghost(TX, RX, pos, vel, 3.5e9, pol="V")
        print(f"  표적{tuple(pos)} v{tuple(vel)}:  L={p['L']:.1f}m  Rb={p['Rb']:.2f}m  "
              f"f_d={p['fd']:+.0f}Hz  beta={p['beta']:.0f}deg")
        print(f"      바닥 유령 → Rb={g['rb_m']:.2f}m ({g['rb_m']-p['Rb']:+.2f}m)  "
              f"f_d={g['fd']:+.0f}Hz  {20*np.log10(g['amp_ratio']):+.1f}dB re echo  "
              f"(theta_i={g['theta_i_deg']:.0f}deg, |G|={g['gamma']:.2f})")

    print("\n" + "=" * 70, "\n▶ 2) Sionna RT — 챔버 환경 경로\n", "=" * 70)
    if a.rt or not os.path.exists(V.RT_ENV):
        V.measure_rt_env()
    tau, amp = V.rt_env(3.5e9)
    print(f"  RT 챔버 CIR: 반사경로 {len(tau)-1}개, 최강 {20*np.log10(amp[1:].max()):+.1f} dB")
    print("  ⚠ 전부 0-도플러(정적) → ECA 가 진폭과 무관하게 0 으로 지운다 = 죽은 파라미터.")
    print("  ⚠ 진짜 위협은 표적 경유 바닥 유령(위 §1) — 도플러가 실려 ECA 를 통과한다.")

    print("\n" + "=" * 70, "\n▶ 3) Sionna PHY 신호체인 검증 (↔ 손합성 make_cpi)\n", "=" * 70)
    V.crosscheck()

    print("\n" + "=" * 70, "\n▶ 4) 그림 (Sionna RT 렌더 + Sionna PHY 신호)\n", "=" * 70)
    V.fig_geometry()
    V.fig_rangedoppler()
    V.fig_ghost()
    V.fig_detection()
    if not a.no_gif:
        V.gif_tracking()

    print("\n" + "=" * 70, "\n▶ 5) report4.ipynb 생성\n", "=" * 70)
    subprocess.run([sys.executable, os.path.join(_HERE, "make_notebook4.py")], check=True)
    print(f"\n✅ report4 완료 ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
