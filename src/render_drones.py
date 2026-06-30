# -*- coding: utf-8 -*-
"""
render_drones.py — 드론 & 전체 장면의 Sionna RT 사진풍 렌더(PNG)
================================================================

생성물 (outputs/renders/)
  studio_<key>.png : 드론 1대 단독, 스튜디오 바닥 위 3/4 시점 (카탈로그용)
  lineup_floor.png : 5종을 차폐시설 바닥에 '실제 축척'으로 나란히 (앞벽 cutaway)
  flight_scene.png : 여러 드론이 시설 안 여러 높이에서 비행하는 모습 (사진 같은 시점)

실행:
  PY=/home/yunjung/.venvs/py312/bin/python
  CUDA_VISIBLE_DEVICES=0 $PY render_drones.py --spp 128
"""
from __future__ import annotations

import os
import argparse
import numpy as np

from drones import DRONES, build_drone
from scene_build import (build_scene, render_views, drone_parts, ground_part,
                         chamber_parts)

HERE = os.path.dirname(os.path.abspath(__file__))
MESH = os.path.abspath(os.path.join(HERE, "..", "assets", "meshes"))
DMESH = os.path.join(MESH, "drones")
CMESH = os.path.join(MESH, "chamber")
OUT = os.path.abspath(os.path.join(HERE, "..", "outputs", "renders"))


def drone_bottom_top(spec):
    """드론 메쉬의 바닥/꼭대기 z (바닥에 앉히거나 띄울 때 사용)."""
    m = build_drone(spec)
    b0, b1 = m.bounds()
    return float(b0[2]), float(b1[2]), float((b1 - b0).max())


def render_studio(spec, spp=128, res=(1100, 850)):
    """드론 1대 단독 스튜디오 렌더."""
    zb, zt, span = drone_bottom_top(spec)
    lift = -zb + 0.02                                   # 바닥에 살짝 띄워 앉힘
    d = os.path.join(DMESH, spec.key)
    parts, _ = drone_parts(spec, position=(0, 0, lift), mesh_dir=d)
    g = ground_part(d, half=max(2.0, span * 1.6), z=0.0)
    scene = build_scene([g] + parts)
    cam = ((span * 1.7, -span * 2.0, span * 1.25), (0, 0, span * 0.25 + lift))
    return render_views(scene, {f"studio_{spec.key}": cam}, OUT,
                        resolution=res, num_samples=spp)


# Sionna 렌더 광원이 (-x,-y,위) 쪽에서 들어오므로, 이 코너에서 찍어야 실내가 고르게 밝다.
HERO_CAM = ((-26, -30, 22), (14, 9, 4.0))         # 메인 코너 시점(잘 검증됨)
HERO_CAM2 = ((-22, -24, 15), (14, 9, 3.0))        # 조금 더 낮고 가까운 변형


def render_facility(spp=160, res=(1280, 960)):
    """차폐시설만(드론 없음) — 시설 히어로 샷 2종."""
    cparts, info = chamber_parts(CMESH, cutaway=True)
    scene = build_scene(cparts)
    cams = {"facility_hero": HERO_CAM, "facility_corner": HERO_CAM2}
    return render_views(scene, cams, OUT, resolution=res, num_samples=spp)


def render_lineup(spp=160, res=(1280, 960)):
    """5종을 차폐시설 바닥에 실제 축척으로 나란히 — '30m 방에서 얼마나 작은지' 스케일감."""
    cparts, info = chamber_parts(CMESH, cutaway=True)
    W, D, H = info["W"], info["D"], info["H"]
    order = ["s1000plus", "phantom4", "matrice4e", "mavic4pro", "mini5pro"]
    xs = np.linspace(W * 0.22, W * 0.55, len(order))   # 밝은 -x 쪽에 모음
    y = D * 0.42
    parts = list(cparts)
    for key, x in zip(order, xs):
        spec = DRONES[key]
        zb, _, _ = drone_bottom_top(spec)
        d = os.path.join(DMESH, key)
        p, _ = drone_parts(spec, position=(float(x), y, -zb + 0.02),
                           yaw_deg=135, mesh_dir=d)     # 전방이 카메라 코너 쪽
        parts += p
    scene = build_scene(parts)
    cam = ((-24, -26, 16), (11, y, 1.2))
    return render_views(scene, {"lineup_floor": cam}, OUT,
                        resolution=res, num_samples=spp)


def render_flight(spp=160, res=(1280, 960)):
    """여러 드론이 시설 안 여러 높이에서 비행하는 모습 (시설 활용 장면)."""
    cparts, info = chamber_parts(CMESH, cutaway=True)
    W, D, H = info["W"], info["D"], info["H"]
    # (key, x, y, z) — 밝은 -x 절반에 모으고 높이를 다양하게
    placement = [
        ("mini5pro",  7,  7,  3.2),
        ("mavic4pro", 13, 9,  2.4),
        ("matrice4e", 5,  11, 1.6),
        ("phantom4",  15, 7,  2.8),
        ("s1000plus", 10, 10, 0.0),     # 바닥에 착륙
    ]
    parts = list(cparts)
    for key, x, y, z in placement:
        spec = DRONES[key]
        zb, _, _ = drone_bottom_top(spec)
        lift = z if z > 0 else (-zb + 0.02)
        d = os.path.join(DMESH, key)
        p, _ = drone_parts(spec, position=(x, y, lift), yaw_deg=135, mesh_dir=d)
        parts += p
    scene = build_scene(parts)
    cam = ((-24, -28, 18), (11, 9, 3.0))
    return render_views(scene, {"flight_scene": cam}, OUT,
                        resolution=res, num_samples=spp)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--spp", type=int, default=128)
    ap.add_argument("--only", type=str, default="all",
                    help="all | facility | studio | lineup | flight")
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    if args.only in ("all", "facility"):
        render_facility(spp=args.spp)
    if args.only in ("all", "studio"):
        for key in DRONES:
            render_studio(DRONES[key], spp=args.spp)
    if args.only in ("all", "lineup"):
        render_lineup(spp=args.spp)
    if args.only in ("all", "flight"):
        render_flight(spp=args.spp)
    print("드론/장면 렌더 완료 →", os.path.relpath(OUT))
