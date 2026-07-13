# -*- coding: utf-8 -*-
"""build_report4.py — report4(무반사 챔버 내부 바이스태틱 패시브 레이더 탐지) 산출물 한 번에 생성.
기하·거리도플러·검출성능 그림 → report4.ipynb. (GPU 불필요: 기하+DSP)"""
import os, sys, time


def main():
    t0 = time.time()
    print("=" * 64, "\n▶ 1) 무반사 챔버 바이스태틱 기하 점검\n", "=" * 64)
    from bistatic_scene import bistatic_params, TX, RX, CH_CLUTTER   # 챔버 내부 배치(양벽 TX/RX)
    for pos, vel in [((21, 10, 5.5), (-3, 2, 0.5)), ((24, 13, 5), (2, -3, 0))]:
        p = bistatic_params(TX, RX, pos, vel, 3.5e9)
        print(f"  표적{pos} v{vel}: L={p['L']:.1f}m Rb={p['Rb']:.1f}m "
              f"τ={p['tau']*1e9:.0f}ns f_d={p['fd']:+.0f}Hz β={p['beta']:.0f}°")

    print("\n" + "=" * 64, "\n▶ 2) 처리 체인 점검 (ECA → CAF → CFAR)\n", "=" * 64)
    import numpy as np
    from waveforms import nr_downlink
    from bistatic_scene import C0
    from passive_process import make_cpi, eca, range_doppler, ca_cfar_2d, peak_detection
    wf = nr_downlink(occupancy="G3"); fs = wf.fs_hz; M = 48
    p = bistatic_params(TX, RX, (21, 10, 5.5), (-3, 2, 0.5), wf.carrier_hz)
    surv, ref = make_cpi(wf.tx, M, fs, p["tau"], p["fd"], a_tgt=1.0, dpi_amp=55,
                         clutter=CH_CLUTTER, snr_db=14, rng=np.random.default_rng(3))
    Rb, f_d, rd = range_doppler(eca(surv, ref, 40), ref, fs, M, n_range=int(45 / (C0 / fs)))
    det, _, _ = ca_cfar_2d(rd, pfa=1e-4); pk = peak_detection(Rb, f_d, rd, det)
    print(f"  참 표적 (Rb={p['Rb']:.1f}m, f_d={p['fd']:+.0f}Hz) → 검출 "
          f"{(round(pk['Rb']), round(pk['fd'])) if pk else '없음'}")

    print("\n" + "=" * 64, "\n▶ 3) 그림 생성 (기하·거리도플러·검출성능·추적 애니메이션)\n", "=" * 64)
    import viz_bistatic; viz_bistatic.build_all(); viz_bistatic.gif_bistatic_tracking()

    print("\n" + "=" * 64, "\n▶ 4) report4.ipynb 생성\n", "=" * 64)
    import subprocess
    subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "make_notebook4.py")],
                   check=True)
    print(f"\n✅ report4 완료 ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
