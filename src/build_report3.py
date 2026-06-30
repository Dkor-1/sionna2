# -*- coding: utf-8 -*-
"""build_report3.py — report3(분절 드론 + 마이크로도플러) 산출물 한 번에 생성.
분절 검증/마이크로도플러 그림·GIF → report3.ipynb. (GPU 불필요: 메쉬+PO+DSP)"""
import os, sys, time


def main():
    t0 = time.time()
    print("=" * 64, "\n▶ 1) 분절 검증 (build_drone 동일성 + 몸체↔블레이드 분리)\n", "=" * 64)
    import numpy as np
    from drones import DRONES, build_drone, pose_articulated
    for k in DRONES:
        m = build_drone(DRONES[k]); pa = pose_articulated(DRONES[k])
        same = (m.n_tris() == pa.n_tris()) and np.allclose(m.bounds(), pa.bounds(), atol=1e-9)
        print(f"  {k:10s} build_drone==pose0: {same}  (tris={m.n_tris()})")
    spec = DRONES["phantom4"]
    base = pose_articulated(spec); spun = pose_articulated(spec, rotor_phase_deg=[90, 90, 90, 90])
    fv = sorted(set(i for f, g in zip(base.f, base.g) if g != "prop" for i in f))
    V0, V1 = np.array(base.v), np.array(spun.v)
    print(f"  블레이드 90° 스핀 시 프레임 정점 이동: {np.linalg.norm(V1[fv]-V0[fv],axis=1).mean():.8f} m (=0 이면 분리)")

    print("\n" + "=" * 64, "\n▶ 2) 마이크로도플러 제원\n", "=" * 64)
    from microdoppler import microdoppler_series
    for k in ("phantom4", "s1000plus"):
        _, _, info = microdoppler_series(DRONES[k], rpm=6000)
        print(f"  {k:10s} 로터{info['n_rotors']} v_tip={info['v_tip']:.0f}m/s "
              f"f_tip=±{info['f_tip']:.0f}Hz 플래시={info['flash_hz']:.0f}Hz")

    print("\n" + "=" * 64, "\n▶ 3) 그림/GIF 생성 (분절·마이크로도플러)\n", "=" * 64)
    import viz_articulation; viz_articulation.build_all()

    print("\n" + "=" * 64, "\n▶ 4) report3.ipynb 생성\n", "=" * 64)
    import subprocess
    subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "make_notebook3.py")])
    print(f"\n✅ report3 완료 ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
