# -*- coding: utf-8 -*-
"""
build_all.py — 한 번에 전부 생성하는 진입점
=============================================
이 한 줄이면 차폐시설·드론 메쉬, 모든 도면/그래프/회전GIF, Sionna 렌더,
카탈로그 몽타주까지 outputs/ 아래에 전부 다시 만들어진다.

실행:
  PY=/home/yunjung/.venvs/py312/bin/python
  CUDA_VISIBLE_DEVICES=2 $PY build_all.py            # 전체 (GPU 2번 사용)
  CUDA_VISIBLE_DEVICES=2 $PY build_all.py --no-render # 렌더 빼고(빠름)
"""
from __future__ import annotations
import os, sys, time, argparse, subprocess


_STEP = [0]


def step(msg):
    _STEP[0] += 1                                  # 옵션(--no-*)으로 건너뛰어도 번호가 이어짐
    print("\n" + "=" * 70 + f"\n▶ {_STEP[0]}) {msg}\n" + "=" * 70)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-render", action="store_true", help="Sionna 렌더 건너뜀")
    ap.add_argument("--no-anim", action="store_true", help="회전 GIF 건너뜀")
    ap.add_argument("--spp", type=int, default=192)
    args = ap.parse_args()
    t0 = time.time()

    step("메쉬 생성 — 차폐시설 + 드론 5종 (OBJ)")
    import chamber, drones
    # trimesh 검증을 **빌드에 붙인다** — 프로펠러 법선 뒤집힘 같은 버그의 회귀 방지.
    import mesh_check
    mesh_check.assert_ok()
    print("  메쉬 검증(trimesh): 5종 전 부위 통과 ✅")
    m, info = chamber.build_chamber()
    cdir = os.path.join(os.path.dirname(__file__), "..", "assets", "meshes", "chamber")
    m.write_obj_per_group(os.path.abspath(cdir), "chamber")
    print(f"  차폐시설: {info['n_tris']} 삼각형, 실내 {info['W']}×{info['D']}×{info['H']} m")
    ddir = os.path.join(os.path.dirname(__file__), "..", "assets", "meshes", "drones")
    for key, spec in drones.DRONES.items():
        dm = drones.build_drone(spec)
        dm.write_obj_per_group(os.path.abspath(os.path.join(ddir, key)), key)
        print(f"  {spec.name:26s} {dm.n_tris():5d} 삼각형  ({spec.release})")

    if not args.no_render:
        step("Sionna RT 렌더 (PNG) — 시설/스튜디오/라인업/비행")
        import render_drones
        render_drones.render_facility(spp=args.spp)
        for k in drones.DRONES:
            render_drones.render_studio(drones.DRONES[k], spp=args.spp)
        render_drones.render_lineup(spp=args.spp)
        render_drones.render_flight(spp=args.spp)

        # ★ report1 의 주력 그림 — 챔버/경로/라디오맵/드론 3뷰를 **Sionna 가 렌더**한다.
        #   (viz_diagram 의 카드가 여기서 만든 r1_drone_*_iso.png 를 3D 패널로 쓰므로 먼저 돈다)
        step("Sionna 렌더 그림 — 챔버·경로·라디오맵·드론 3뷰 (viz_report1)")
        import viz_report1
        viz_report1.render_chamber(); viz_report1.fig_chamber()
        viz_report1.render_paths();   viz_report1.fig_paths()
        viz_report1.render_radiomap(); viz_report1.fig_radiomap()
        viz_report1.render_drones()
        for k in drones.DRONES:
            viz_report1.fig_drone(k)
        viz_report1.fig_gallery()
        viz_report1.fig_envelope_fit()
        viz_report1.fig_mesh_check()

        step("카탈로그/시설뷰 몽타주")
        import viz_montage
        viz_montage.catalog()
        viz_montage.facility_views()

    step("치수 도면 (matplotlib — 렌더로 대체 불가)")
    import viz_diagram
    viz_diagram.chamber_schematic()
    viz_diagram.size_comparison()
    for k in drones.DRONES:
        viz_diagram.drone_card(k)          # 3D 패널 = Sionna 렌더(r1_drone_*_iso.png)

    if not args.no_anim and not args.no_render:
        step("회전 GIF (Sionna 턴테이블)")
        import viz_report1 as V1
        for k in drones.DRONES:
            V1.turntable(k)
        V1.turntable_all()

    step("report1.ipynb 생성")
    subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "make_notebook.py")], check=True)

    print(f"\n✅ 완료 ({time.time()-t0:.0f}s).  결과 → sionna2/outputs/")


if __name__ == "__main__":
    main()
