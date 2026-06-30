# -*- coding: utf-8 -*-
"""build_report2.py — report2(레이더) 산출물 한 번에 생성.
검증(PO 평판/구) → 레이더/RCS/파형 그림 → report2.ipynb."""
import os, sys, time


def main():
    t0 = time.time()
    print("="*64, "\n▶ 1) PO RCS 검증 (평판·구)\n", "="*64)
    import rcs_po; rcs_po.validate(3.5e9)

    print("\n" + "="*64, "\n▶ 2) 파형 제원 (WiFi/LTE/5G)\n", "="*64)
    from waveforms import all_waveforms
    for k, wf in all_waveforms().items():
        print(f"  {wf.name:15s} fc={wf.carrier_hz/1e9:.2f}GHz B={wf.bw_hz/1e6:.0f}MHz "
              f"분해능={wf.range_resolution_m:.2f}m 기준={wf.ref_name}")

    print("\n" + "="*64, "\n▶ 3) report2 그림 생성 (RCS·파형·비교)\n", "="*64)
    import viz_radar; viz_radar.build_all()

    print("\n" + "="*64, "\n▶ 3b) 점유상태(G1/G2/G3) 그리드 사진 + 실험(거리×속도)\n", "="*64)
    import viz_occupancy; viz_occupancy.build_all()

    print("\n" + "="*64, "\n▶ 3c) 메쉬 기반 실험 시각화 (셋업·RCS풍선·조명면·도플러)\n", "="*64)
    import viz_mesh; viz_mesh.build_all()

    print("\n" + "="*64, "\n▶ 4) report2.ipynb 생성\n", "="*64)
    import subprocess
    subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "make_notebook2.py")])
    print(f"\n✅ report2 완료 ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
