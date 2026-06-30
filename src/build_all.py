# -*- coding: utf-8 -*-
"""
build_all.py — 한 번에 전부 생성하는 진입점
=============================================
이 한 줄이면 차폐시설·드론 메쉬, 모든 도면/그래프/회전GIF, Sionna 렌더,
카탈로그 몽타주까지 outputs/ 아래에 전부 다시 만들어진다.

실행:
  PY=/home/yunjung/workspace/jeong/miniforge3/envs/sionna/bin/python
  CUDA_VISIBLE_DEVICES=0 $PY build_all.py            # 전체
  CUDA_VISIBLE_DEVICES=0 $PY build_all.py --no-render # 렌더 빼고(빠름)
"""
from __future__ import annotations
import os, sys, time, argparse


def step(msg):
    print("\n" + "=" * 70 + f"\n▶ {msg}\n" + "=" * 70)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-render", action="store_true", help="Sionna 렌더 건너뜀")
    ap.add_argument("--no-anim", action="store_true", help="회전 GIF 건너뜀")
    ap.add_argument("--spp", type=int, default=192)
    args = ap.parse_args()
    t0 = time.time()

    step("1) 메쉬 생성 — 차폐시설 + 드론 5종 (OBJ)")
    import chamber, drones
    m, info = chamber.build_chamber()
    cdir = os.path.join(os.path.dirname(__file__), "..", "assets", "meshes", "chamber")
    m.write_obj_per_group(os.path.abspath(cdir), "chamber")
    print(f"  차폐시설: {info['n_tris']} 삼각형, 실내 {info['W']}×{info['D']}×{info['H']} m")
    ddir = os.path.join(os.path.dirname(__file__), "..", "assets", "meshes", "drones")
    for key, spec in drones.DRONES.items():
        dm = drones.build_drone(spec)
        dm.write_obj_per_group(os.path.abspath(os.path.join(ddir, key)), key)
        print(f"  {spec.name:26s} {dm.n_tris():5d} 삼각형  ({spec.release})")

    step("2) 도면/그래프 (matplotlib)")
    import viz_diagram
    viz_diagram.chamber_schematic()
    viz_diagram.size_comparison()
    for k in drones.DRONES:
        viz_diagram.drone_card(k)

    if not args.no_anim:
        step("3) 회전 GIF (turntable)")
        import viz_anim
        for k in drones.DRONES:
            viz_anim.turntable(k)
        viz_anim.turntable_all()

    if not args.no_render:
        step("4) Sionna RT 렌더 (PNG)")
        import render_drones
        render_drones.render_facility(spp=args.spp)
        for k in drones.DRONES:
            render_drones.render_studio(drones.DRONES[k], spp=args.spp)
        render_drones.render_lineup(spp=args.spp)
        render_drones.render_flight(spp=args.spp)

        step("5) 카탈로그/시설뷰 몽타주")
        import viz_montage
        viz_montage.catalog()
        viz_montage.facility_views()

    print(f"\n✅ 완료 ({time.time()-t0:.0f}s).  결과 → sionna2/outputs/")


if __name__ == "__main__":
    main()
