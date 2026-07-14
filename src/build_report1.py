# -*- coding: utf-8 -*-
"""build_report1.py — report1 산출물 **전부** 를 한 번에 만든다.

  0) 메쉬 검증 게이트 (mesh_check.assert_ok) — 실패하면 여기서 멈춘다
  1) 챔버 (재질 표 · 기하 도해 · Sionna 렌더 6장)
  2) 라디오맵 (Sionna RadioMapSolver — 드론 그림자)
  3) 드론 메쉬 (외형 정합 · trimesh 전수검사 · 불리언 내부면 측정 · PO 편향)
  4) CAD 파이프라인 그림
  5) Sionna 갤러리 (5종 × 3뷰)
  6) 분절 + 호버 RPM 물리 유도
  7) SBR 마이크로도플러 (가림 포함, GPU — 가장 무겁다)
  8) 분절 애니메이션 GIF (Sionna 렌더)
  9) report1.ipynb 생성 (outputs/report1.json 만 읽는다)

실행:  ~/.venvs/py312/bin/python src/build_report1.py
GPU 는 src/gpu.py 가 여유 메모리를 보고 자동 선택한다. 전체 약 15~20분.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="chamber,radiomap,mesh,cad,gallery,art,md,gif")
    ap.add_argument("--phase", type=int, default=144, help="SBR 마이크로도플러 자세 표 크기")
    ap.add_argument("--frames", type=int, default=36, help="분절 GIF 프레임 수")
    ap.add_argument("--skip-gate", action="store_true")
    a = ap.parse_args()
    t0 = time.time()

    if not a.skip_gate:
        print("=" * 72)
        print("▶ 0) 메쉬 검증 게이트 — trimesh (watertight / winding / 법선 / 퇴화면)")
        print("=" * 72)
        from mesh_check import assert_ok
        assert_ok()
        print("  ✅ 드론 5/5 통과 — 회귀 없음\n")

    print("=" * 72)
    print("▶ 1~8) 측정 · 그림 · Sionna 렌더")
    print("=" * 72)
    import viz_report1 as V
    V.build_all(set(a.only.split(",")), n_phase=a.phase, n_frames=a.frames)

    print("\n" + "=" * 72)
    print("▶ 9) report1.ipynb 생성 (숫자는 outputs/report1.json 에서만 읽는다)")
    print("=" * 72)
    subprocess.run([sys.executable, os.path.join(HERE, "make_notebook1.py")], check=True)

    print(f"\n✅ report1 완료 ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
