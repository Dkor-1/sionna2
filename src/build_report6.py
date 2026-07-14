# -*- coding: utf-8 -*-
"""build_report6.py — report6(검증 리포트) 산출물 생성.
전제(둘 다 필요):
  CUDA_VISIBLE_DEVICES=2 python benchmark/verify_rt_no_rcs.py   → outputs/rt_no_rcs_verify.json
  python benchmark/verify_floor_ghost.py                        → outputs/floor_ghost_verify.json (GPU 불필요)"""
import os, subprocess, sys, time

_OUT = os.path.join(os.path.dirname(__file__), "..", "outputs")
NEEDS = {"rt_no_rcs_verify.json": "CUDA_VISIBLE_DEVICES=2 python benchmark/verify_rt_no_rcs.py",
         "floor_ghost_verify.json": "python benchmark/verify_floor_ghost.py"}


def main():
    t0 = time.time()
    missing = [f"  {cmd}" for j, cmd in NEEDS.items() if not os.path.exists(os.path.join(_OUT, j))]
    if missing:
        sys.exit("먼저 실행:\n" + "\n".join(missing))
    print("=" * 64, "\n▶ 1) RT 검증 그림 (측정 JSON 에서)\n", "=" * 64)
    import viz_verify_rt; viz_verify_rt.build_all()
    print("=" * 64, "\n▶ 2) PO 검증 그림 (커널 진단력·수렴성·널)\n", "=" * 64)
    import viz_verify_po; viz_verify_po.build_all()
    print("=" * 64, "\n▶ 3) 챔버 바닥 검증 그림 (semi-anechoic·죽은 클러터·유령)\n", "=" * 64)
    import viz_verify_clutter; viz_verify_clutter.main()
    print("=" * 64, "\n▶ 4) report6.ipynb 생성\n", "=" * 64)
    subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "make_notebook6.py")], check=True)
    print(f"\n✅ report6 완료 ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
