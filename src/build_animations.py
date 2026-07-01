# -*- coding: utf-8 -*-
"""build_animations.py — 실험 애니메이션(GIF) 한 번에 생성 (GPU 불필요, 느림).
report2 RCS 글린트·점유, report3 마이크로도플러 회전. (turntable/분절/추적은 각 report 빌드에 포함)"""
import time
import viz_animations


def main():
    t0 = time.time()
    viz_animations.build_all()
    print(f"✅ 애니메이션 완료 ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
