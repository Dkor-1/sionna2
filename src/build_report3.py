# -*- coding: utf-8 -*-
"""build_report3.py — report3(분절 드론 + 마이크로도플러) 산출물 한 번에 생성.

2026-07-14: 마이크로도플러를 **SBR(가림 포함)** 로 갈아끼웠다.
  · 분절 검증 도해(mpl)      → viz_articulation.py   (공학 도해라 mpl 유지)
  · 마이크로도플러(SBR)      → viz_report3.py        (Mitsuba 광선 + PO 적분)
  · 분절 드론 렌더/애니메이션 → viz_report3.py        (**Sionna 자체 렌더러**)
GPU 사용 (Mitsuba/OptiX). 소요 ~8분."""
import os
import sys
import time


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

    print("\n" + "=" * 64, "\n▶ 2) 마이크로도플러 제원 + SBR/PO 교차검증\n", "=" * 64)
    #   기하: 대각 로터쌍은 위상이 같다 — base_ang 이 180° 차이 나고, dir 이 같고,
    #   2엽 프로펠러는 180° 대칭이라 (base+180) 자세 = base 자세.
    from drones import rotor_layout
    rl = rotor_layout(DRONES["mavic4pro"])
    print("  mavic4pro 로터: " + " · ".join(
        f"[{i}] base {r['base_ang']:.0f}° dir {r['dir']:+d}" for i, r in enumerate(rl)))
    print("     → 대각쌍(0,2)/(1,3)은 base 180° 차 + 같은 dir + 2엽 180° 대칭 ⇒ **위상 동일**(함께 번쩍)")

    #   viz_report3 의 테이블 조회가 microdoppler.microdoppler_sbr 과 같은 신호를 주는지 확인
    from microdoppler import microdoppler_sbr
    import viz_report3 as V3
    tab, info = V3.sbr_phase_table(DRONES["mavic4pro"], n_phase=120, div=12)
    _, E1 = V3.series_from_table(tab, info, prf=20000.0, n_t=1024)
    _, E2, _ = microdoppler_sbr(DRONES["mavic4pro"], fc=V3.FC, az=V3.AZ, el=V3.EL,
                                prf=20000.0, n_t=1024, n_phase=120)
    rel = float(np.max(np.abs(E1 - E2)) / np.max(np.abs(E2)))
    print(f"  교차검증 series_from_table vs microdoppler_sbr : 최대 상대오차 {rel:.2e} (같은 신호)")

    print("\n" + "=" * 64, "\n▶ 3) 분절 검증 도해 (mpl)\n", "=" * 64)
    import viz_articulation; viz_articulation.build_all()

    print("\n" + "=" * 64, "\n▶ 4) SBR 마이크로도플러 + Sionna 렌더 (GPU)\n", "=" * 64)
    js = V3.build_all()
    h = js["headline"]
    print(f"\n  ★ 헤드라인: |DC|/std(AC)  PO {h['po']['ratio']:.1f}(+{h['po']['ratio_db']:.1f} dB) → "
          f"SBR {h['sbr']['ratio']:.1f}(+{h['sbr']['ratio_db']:.1f} dB)  ⇒ 가림으로 {h['gain_db']:.1f} dB 이득")
    print(f"     f_tip = {h['f_tip']:.0f} Hz (v_tip {h['v_tip']:.0f} m/s), 플래시 = {h['flash_hz']:.1f} Hz "
          f"(= 2엽 프롭이 1회전에 2번 브로드사이드 ⇒ {h['rpm']/60:.1f} rev/s × 2)")

    print("\n" + "=" * 64, "\n▶ 5) report3.ipynb 생성\n", "=" * 64)
    import subprocess
    subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "make_notebook3.py")], check=True)
    print(f"\n✅ report3 완료 ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
