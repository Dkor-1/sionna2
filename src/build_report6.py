# -*- coding: utf-8 -*-
"""build_report6.py — report6(검증 리포트) 산출물 생성.
전제: benchmark/verify_rt_no_rcs.py 를 먼저 돌려 outputs/rt_no_rcs_verify.json 이 있어야 한다."""
import os, subprocess, sys, time


def main():
    t0 = time.time()
    j = os.path.join(os.path.dirname(__file__), "..", "outputs", "rt_no_rcs_verify.json")
    if not os.path.exists(j):
        sys.exit("먼저 실행: CUDA_VISIBLE_DEVICES=2 python benchmark/verify_rt_no_rcs.py")
    print("=" * 64, "\n▶ 1) RT 검증 그림 (측정 JSON 에서)\n", "=" * 64)
    import viz_verify_rt; viz_verify_rt.build_all()
    print("=" * 64, "\n▶ 2) PO 검증 그림 (커널 진단력·수렴성·널)\n", "=" * 64)
    import viz_verify_po; viz_verify_po.build_all()
    print("=" * 64, "\n▶ 3) report6.ipynb 생성\n", "=" * 64)
    subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "make_notebook6.py")], check=True)
    print(f"\n✅ report6 완료 ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
