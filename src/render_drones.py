# -*- coding: utf-8 -*-
"""
render_drones.py — 드론 & 전체 장면의 Sionna RT 사진풍 렌더(PNG)
================================================================

생성물 (outputs/renders/)
  studio_<key>.png : 드론 1대 단독, 스튜디오 바닥 위 3/4 시점 (카탈로그용)
  lineup_floor.png : 전 기종을 차폐시설 바닥에 '실제 축척'으로 나란히 (앞벽 cutaway)
  flight_scene.png : 여러 드론이 시설 안 여러 높이에서 비행하는 모습 (사진 같은 시점)

실행:
  PY=/home/yunjung/.venvs/py312/bin/python
  CUDA_VISIBLE_DEVICES=2 $PY render_drones.py --spp 128   # GPU 2번 사용
"""
from __future__ import annotations

import os
import argparse
import numpy as np

from drones import DRONES, build_drone, drone_order
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
# (과거에 방이 '조각난 것'처럼 보이던 원인은 카메라가 아니라 scene_build 의 position 재배치
#  버그였다 — 수정 후 컷어웨이 3/4 뷰가 의도대로 '한 덩어리 방'으로 나온다.)
HERO_CAM = ((-26, -30, 22), (14, 9, 4.0))         # 컷어웨이 실내 3/4 (일체형 방)
HERO_CAM2 = ((-24, -26, 17), (15, 10, 5.0))       # 닫힌 외관 3/4 (금속 차폐 박스 + 골조)


def render_facility(spp=160, res=(1280, 960)):
    """차폐시설만(드론 없음) — 컷어웨이 실내 히어로 + 닫힌 외관 2종."""
    cparts, info = chamber_parts(CMESH, cutaway=True)
    out = render_views(build_scene(cparts), {"facility_hero": HERO_CAM}, OUT,
                       resolution=res, num_samples=spp)
    cparts2, _ = chamber_parts(CMESH, cutaway=False)      # 외관은 컷어웨이 없이 통짜
    out += render_views(build_scene(cparts2), {"facility_corner": HERO_CAM2}, OUT,
                        resolution=res, num_samples=spp)
    return out


def render_lineup(spp=160, res=(1280, 960)):
    """**전 기종**을 차폐시설 바닥에 실제 축척으로 나란히 — '30m 방에서 얼마나 작은지' 스케일감."""
    cparts, info = chamber_parts(CMESH, cutaway=True)
    W, D, H = info["W"], info["D"], info["H"]
    #  ⭐ 2026-07-30 (Phase 3): 5종 하드코딩 → 레지스트리 유도(앞머리는 옛 크기 내림차순 유지).
    #     x 간격은 `len(order)` 로 나뉘므로 기종이 늘면 자동으로 좁혀진다.
    order = drone_order(("s1000plus", "phantom4", "matrice4e", "mavic4pro", "mini5pro"))
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
    cam = ((3.2, 4.2, 1.7), (11.5, y + 0.6, 0.45))   # 실내 근접 로우앵글 — 원근으로 크기 비교
    return render_views(scene, {"lineup_floor": cam}, OUT,
                        resolution=res, num_samples=spp)


def render_flight(spp=160, res=(1280, 960)):
    """여러 드론이 시설 안 여러 높이에서 비행하는 모습 (시설 활용 장면)."""
    cparts, info = chamber_parts(CMESH, cutaway=True)
    W, D, H = info["W"], info["D"], info["H"]
    # (key, x, y, z) — 밝은 -x 절반에 모으고 높이를 다양하게. **손으로 고른 좌표**다:
    # ※ matrice4e 는 (5, 11, 1.6) 이면 카메라 축에서 42° — 화각(반각 ~25°) **밖**이라 프레임에서
    #   잘려 나갔다("Matrice 는 어디 있죠?"). (9, 8, 1.6) 이면 축에서 9°로 확실히 들어온다.
    # ⭐ 2026-07-30 (Phase 3): 좌표가 없는 기종(신규 등록분)은 **조용히 빠지지 않는다** —
    #   화각 안쪽 여유 지점에 자동 배치한다. 프레임 안에 드는지는 좌표를 손으로 고를 때만
    #   보장되므로, 렌더 결과를 보고 위 표에 정식 좌표를 넣는 것이 옳다(자동배치는 안전망).
    POSED = {
        "mini5pro":  (7,  7,  3.2),
        "mavic4pro": (13, 9,  2.4),
        "matrice4e": (9,  8,  1.6),
        "phantom4":  (15, 7,  2.8),
        "s1000plus": (10, 10, 0.0),     # 바닥에 착륙
    }
    placement = [(k, *POSED[k]) for k in drone_order(tuple(POSED)) if k in POSED]
    extra = [k for k in drone_order() if k not in POSED]
    for i, k in enumerate(extra):
        placement.append((k, 11.0 + 2.2 * i, 6.0, 1.1 + 0.9 * (i % 2)))
    parts = list(cparts)
    for key, x, y, z in placement:
        spec = DRONES[key]
        zb, _, _ = drone_bottom_top(spec)
        lift = z if z > 0 else (-zb + 0.02)
        d = os.path.join(DMESH, key)
        p, _ = drone_parts(spec, position=(x, y, lift), yaw_deg=135, mesh_dir=d)
        parts += p
    scene = build_scene(parts)
    cam = ((3.0, 3.2, 3.4), (12.5, 9.5, 2.3))        # 실내 근접 — 드론 군집 + 방 배경
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
