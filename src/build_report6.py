# -*- coding: utf-8 -*-
"""build_report6.py — report6(검증 리포트) 산출물 생성.

전제 — 측정 스크립트 3개 (전부 GPU; gpu.pick 이 알아서 고른다):
  python benchmark/verify_rt_no_rcs.py   → outputs/rt_no_rcs_verify.json   (§3~§5)
  python benchmark/verify_rt_rays.py     → outputs/rt_ray_budget.json      (§2 — 4억 발)
  python benchmark/verify_floor_ghost.py → outputs/floor_ghost_verify.json (§10, GPU 불필요)
그리고 §6 의 마이크로도플러 수치는 report3 이 남긴 outputs/report3_microdoppler.json 에서 읽는다.

실행:  python src/build_report6.py            (측정 JSON 이 있으면 그림+노트북만)
       python src/build_report6.py --force    (§6·§7 측정을 다시 함 — SBR/PO 재계산, 수 분)
"""
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
_OUT = os.path.abspath(os.path.join(HERE, "..", "outputs"))

NEEDS = {
    "rt_no_rcs_verify.json": "python benchmark/verify_rt_no_rcs.py",
    "rt_ray_budget.json": "python benchmark/verify_rt_rays.py",
    "floor_ghost_verify.json": "python benchmark/verify_floor_ghost.py",
    "report3_microdoppler.json": "python src/build_report3.py",
}


def main():
    t0 = time.time()
    force = "--force" in sys.argv
    missing = [f"  {cmd}" for j, cmd in NEEDS.items()
               if not os.path.exists(os.path.join(_OUT, j))]
    if missing:
        sys.exit("먼저 실행:\n" + "\n".join(missing))

    print("=" * 72, "\n▶ 1) RT 검증 그림 (σ 없음 · 디스코볼 · 지연)\n", "=" * 72)
    import viz_verify_rt
    viz_verify_rt.build_all()

    print("=" * 72, "\n▶ 2) 🆕 광선예산(4억 발) · SBR · 메쉬/재질 버그\n", "=" * 72)
    import viz_verify_sbr
    viz_verify_sbr.build_all(force=force)

    print("=" * 72, "\n▶ 3) PO 검증 그림 (진단력·수렴성·널)\n", "=" * 72)
    import viz_verify_po
    viz_verify_po.build_all()

    print("=" * 72, "\n▶ 4) 챔버 바닥 (semi-anechoic · 죽은 클러터 · 유령)\n", "=" * 72)
    import viz_verify_clutter
    viz_verify_clutter.main()

    print("=" * 72, "\n▶ 5) report6.ipynb 생성 (수치는 전부 측정 JSON 에서 주입)\n", "=" * 72)
    subprocess.run([sys.executable, os.path.join(HERE, "make_notebook6.py")], check=True)

    print(f"\n✅ report6 완료 ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
