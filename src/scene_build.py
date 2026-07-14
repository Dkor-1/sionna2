# -*- coding: utf-8 -*-
"""
scene_build.py — 부위(Part) 목록 → Sionna RT 장면 조립 + 렌더(PNG) 엔진
=========================================================================

핵심 아이디어 (아주 단순)
  * 우리가 만든 모든 물체(차폐시설의 벽/바닥/흡수체, 드론의 동체/암/모터/프로펠러…)는
    "부위별 OBJ 파일 + 재질키 + 색 + 놓을 위치"로 표현됩니다. 이것을 Part 라고 부릅니다.
  * build_scene(parts) 는 Part 목록을 받아 Sionna 장면에 하나씩 올립니다.
    (OBJ 1개 = SceneObject 1개 = RadioMaterial 1개)
  * render_views(...) 는 카메라를 여러 각도로 놓고 사진(PNG)을 뽑습니다.

Sionna RT 2.0 좌표/관례
  - load_scene() 으로 빈 장면을 만들고 scene.frequency 설정
  - SceneObject(fname=OBJ, radio_material=...) 로 물체 생성 후 scene.edit(add=[...])
  - 물체는 .position / .orientation / .scaling 로 배치 (scaling 은 '단일 배율')
  - Camera(position, look_at) 후 scene.render_to_file(...) 로 PNG 저장 (headless OK)
"""
from __future__ import annotations

import os
from dataclasses import dataclass

# GPU 는 **2번**을 기본 사용(사용자 지정 시 존중). mitsuba/OptiX 가 import 시점에
# CUDA_VISIBLE_DEVICES 를 읽으므로 반드시 mitsuba import 전에 설정한다.
#   ⚠ 2026-07-14: 예전엔 "2" 로 하드코딩했다 — 다른 GPU 가 놀고 있어도 2번만 쓰고,
#      2번이 남의 작업으로 차 있으면 OOM 이 났다. 이제 **가장 한가한 GPU 를 자동 선택**한다.
#      강제하려면 SIONNA2_GPU=1 (또는 CUDA_VISIBLE_DEVICES 를 직접 세팅).
from gpu import pick as _pick_gpu    # noqa: E402
_pick_gpu(verbose=False)

import mitsuba as mi
import sionna.rt as rt

from materials import make_material


@dataclass
class Part:
    """장면에 올릴 물체 하나."""
    name: str                       # 고유 이름
    obj: str                        # OBJ 파일 경로
    mat_key: str                    # 재질키 (materials.make_material 참고)
    color: tuple = (0.7, 0.7, 0.7)  # 표시색 RGB
    position: tuple = (0., 0., 0.)  # OBJ 좌표 기준 **평행이동 벡터** [m] (0이면 그대로)
    orientation: tuple = (0., 0., 0.)  # 오일러 회전 [rad] (Sionna 관례)
    scaling: float = 1.0            # 단일 배율


def build_scene(parts: list[Part], fc: float = 3.5e9) -> rt.Scene:
    """Part 목록으로 Sionna 장면을 조립해 돌려준다."""
    scene = rt.load_scene()
    scene.frequency = fc
    # 렌더만 할 때도 배열 속성이 있으면 안전하므로 더미 안테나 배열 설정
    scene.tx_array = rt.PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="V")
    scene.rx_array = rt.PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="V")

    objs = []
    for p in parts:
        mat = make_material(p.mat_key, name=f"mat_{p.name}", color=p.color)
        o = rt.SceneObject(fname=p.obj, name=p.name, radio_material=mat)
        objs.append((o, p))
    scene.edit(add=[o for o, _ in objs])
    for o, p in objs:
        # ⚠ SceneObject.position 세터는 '평행이동'이 아니라 **AABB 중심을 그 좌표로 재배치**한다.
        #   절대좌표가 구워진 메쉬(챔버 부위 등)에 (0,0,0)을 대입하면 원점으로 끌려온다(과거 버그:
        #   천장이 바닥에 눕고 벽이 방 가운데 십자로 서던 렌더). 그래서 여기서는
        #   Part.position 을 '평행이동 벡터'로 해석해, 0이면 건드리지 않고
        #   0이 아니면 현재 중심 + 벡터로 옮긴다(원점 기준 메쉬의 lift 계산과 일치).
        if any(abs(float(v)) > 1e-12 for v in p.position):
            c = o.position
            o.position = mi.Point3f(float(c.x[0]) + float(p.position[0]),
                                    float(c.y[0]) + float(p.position[1]),
                                    float(c.z[0]) + float(p.position[2]))
        if any(abs(float(v)) > 1e-12 for v in p.orientation):
            o.orientation = mi.Point3f(*[float(v) for v in p.orientation])
        if abs(p.scaling - 1.0) > 1e-9:
            o.scaling = float(p.scaling)
    return scene


def render_views(scene: rt.Scene, cameras: dict, out_dir: str,
                 resolution=(1280, 960), num_samples=128, show_devices=False):
    """카메라 사전 {이름: (position, look_at)} 마다 PNG 를 저장."""
    os.makedirs(out_dir, exist_ok=True)
    saved = []
    for name, (pos, look) in cameras.items():
        cam = rt.Camera(position=[float(v) for v in pos],
                        look_at=[float(v) for v in look])
        fn = os.path.join(out_dir, f"{name}.png")
        scene.render_to_file(camera=cam, filename=fn, resolution=resolution,
                             num_samples=num_samples, show_devices=show_devices)
        saved.append(fn)
        print("[render]", os.path.relpath(fn))
    return saved


# --------------------------------------------------------------------------- #
#  차폐시설 → Part 목록
# --------------------------------------------------------------------------- #
def chamber_parts(mesh_dir: str, cutaway: bool = False) -> tuple[list[Part], dict]:
    """차폐시설 메쉬를 부위별 OBJ 로 저장하고 Part 목록을 만든다.
    cutaway=True 면 앞벽/앞골조를 빼서 내부를 들여다볼 수 있게 한다."""
    from chamber import build_chamber, chamber_group_style, CUTAWAY_OMIT
    m, info = build_chamber()
    paths = m.write_obj_per_group(mesh_dir, "chamber")
    parts = []
    for g, p in paths.items():
        if cutaway and g in CUTAWAY_OMIT:
            continue
        mat_key, color, _ = chamber_group_style(g)
        parts.append(Part(name=g, obj=p, mat_key=mat_key, color=color))
    return parts, info


# --------------------------------------------------------------------------- #
#  드론 → Part 목록  /  바닥판 Part
# --------------------------------------------------------------------------- #
def drone_parts(spec, position=(0., 0., 0.), yaw_deg=0.0, mesh_dir=None):
    """드론 1대를 부위별 OBJ 로 저장하고 Part 목록을 만든다.
    yaw_deg 로 수평 회전(메쉬를 직접 회전시켜 export — 좌표계 혼동 방지).
    장면용 OBJ 는 mesh_dir/_scene/ 에 저장한다 — 정본 자산(assets/meshes/drones/<key>/*.obj)을
    회전된 메쉬로 덮어쓰면 '마지막 렌더의 yaw' 에 따라 자산 내용이 달라지는 오염이 생긴다."""
    from drones import build_drone, drone_colors, DRONE_GROUP_MAT
    m = build_drone(spec)
    if abs(yaw_deg) > 1e-9:
        m = m.rotated("z", yaw_deg)
    paths = m.write_obj_per_group(os.path.join(mesh_dir, "_scene"), spec.key)
    cols = drone_colors(spec)
    parts = []
    for g, p in paths.items():
        mat_key, _ = DRONE_GROUP_MAT[g]
        parts.append(Part(name=f"{spec.key}_{g}", obj=p, mat_key=mat_key,
                          color=cols[g], position=position))
    return parts, m


def ground_part(mesh_dir, half=4.0, z=0.0, color=(0.80, 0.80, 0.82),
                mat_key="concrete_light", name="studio_ground"):
    """간단한 정사각 바닥판 한 장(드론 단독 렌더용 스튜디오 바닥)."""
    from geom import quad
    q = quad((-half, -half, z), (half, -half, z), (half, half, z), (-half, half, z),
             group=name)
    p = os.path.join(mesh_dir, f"{name}.obj")
    q.write_obj(p)
    return Part(name=name, obj=p, mat_key=mat_key, color=color)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--spp", type=int, default=96)
    ap.add_argument("--res", type=int, nargs=2, default=[1280, 960])
    args = ap.parse_args()

    HERE = os.path.dirname(os.path.abspath(__file__))
    MESH = os.path.join(HERE, "..", "assets", "meshes", "chamber")
    OUT = os.path.join(HERE, "..", "outputs", "renders")

    # (1) 외부 — 강철 골조가 보이는 전체 모습
    parts_full, info = chamber_parts(os.path.abspath(MESH), cutaway=False)
    W, D, H = info["W"], info["D"], info["H"]
    scene = build_scene(parts_full)
    render_views(scene, {
        "chamber_exterior": ((-20, -26, 16), (W/2, D/2, 4)),
    }, os.path.abspath(OUT), resolution=tuple(args.res), num_samples=args.spp)

    # (2) 내부(cutaway) — 앞벽을 떼고 들여다본 모습 (사진과 같은 시점)
    parts_cut, _ = chamber_parts(os.path.abspath(MESH), cutaway=True)
    scene2 = build_scene(parts_cut)
    render_views(scene2, {
        "chamber_interior":  ((4, -16, 13), (18, 11, 1.5)),
        "chamber_interior2": ((-8, -10, 14), (20, 12, 1)),
    }, os.path.abspath(OUT), resolution=tuple(args.res), num_samples=args.spp)
    print("done.")
