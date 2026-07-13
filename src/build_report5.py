# -*- coding: utf-8 -*-
"""build_report5.py — report5(공정 벤치마크: 링크버짓 → Pd 매트릭스 + RT 교차검증) 산출물 한 번에 생성.
benchmark/ 하네스를 순서대로 실행하고 노트북을 만든다.
  ① run_min_cell.py : 최소 셀 1개(5G100×mavic4pro×radial) — 물리 유도 SNR → 측정 SCR/Pd
  ② run_matrix.py   : 점유(A)·신호×드론(B)·시나리오(C)·RT 교차검증(D) → 그림/CSV/JSON
  ③ make_notebook5  : report5.ipynb (②의 JSON 수치를 마크다운에 삽입)
GPU: ②의 D 섹션(Sionna RT)이 1장 사용 — scene_build 기본값 CUDA_VISIBLE_DEVICES=2."""
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.abspath(os.path.join(HERE, "..", "benchmark"))


def main():
    t0 = time.time()
    print("=" * 64, "\n▶ 1) 최소 셀 (benchmark/run_min_cell.py)\n", "=" * 64)
    subprocess.run([sys.executable, os.path.join(BENCH, "run_min_cell.py")], check=True)

    print("\n" + "=" * 64, "\n▶ 2) 벤치마크 매트릭스 A~D (benchmark/run_matrix.py)\n", "=" * 64)
    subprocess.run([sys.executable, os.path.join(BENCH, "run_matrix.py")], check=True)

    print("\n" + "=" * 64, "\n▶ 3) report5.ipynb 생성\n", "=" * 64)
    subprocess.run([sys.executable, os.path.join(HERE, "make_notebook5.py")], check=True)
    print(f"\n✅ report5 완료 ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
