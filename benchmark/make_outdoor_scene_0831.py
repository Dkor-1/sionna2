# -*- coding: utf-8 -*-
"""make_outdoor_scene_0831.py — **실외 환경 메쉬**를 만들고 Sionna 로 렌더한다.

왜 만드나
---------
지금 스윕은 `rt.load_scene()` 빈 씬에 드론 부품만 넣는다 — **자유공간**이다.
그래서 지금까지 «클러터» 는 전부 드론 자신의 동체였다. 환경 클러터는 한 번도 없었다.

⛔**실외만 만든다**(사용자 지시 2026-08-31). 실내 챔버는 쓰지 않는다.

무엇을 세우나
-------------
  지면      120 × 120 m 콘크리트 판 (z=0)
  건물 넷   높이 9~24 m 상자. 드론을 둘러싸되 시선을 막지 않게 배치
  가로등 둘 금속 기둥 — 얇은 수직 산란체
  드론      matrice4e 정본 부품, 지상 12 m

⭐**지면이 요점이다.** 튀면서 드론에도 닿는 경로는 드론의 도플러를 같이 싣는다.
   그러면 정지 클러터 제거로 안 지워진다. 실외에서는 지면이 항상 있다.

산출: assets/meshes/outdoor01/*.obj · outputs/renders/outdoor01_*.png
"""
import os
import sys

import numpy as np

ROOT = "/workspace/sionna"
sys.path.insert(0, f"{ROOT}/src")
MESH = f"{ROOT}/assets/meshes/outdoor01"
OUT = f"{ROOT}/outputs/renders"
DRONE = f"{ROOT}/assets/meshes/drones/matrice4e"
os.makedirs(MESH, exist_ok=True)
os.makedirs(OUT, exist_ok=True)


def write_obj(path, V, F):
    """정점·면을 OBJ 로. ⛔면 색인은 1 부터다."""
    with open(path, "w") as f:
        f.write(f"# {os.path.basename(path)} — outdoor scene, generated\n")
        for v in V:
            f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
        for t in F:
            f.write(f"f {t[0]+1} {t[1]+1} {t[2]+1}\n")


def plane(cx, cy, z, sx, sy):
    V = np.array([[cx - sx/2, cy - sy/2, z], [cx + sx/2, cy - sy/2, z],
                  [cx + sx/2, cy + sy/2, z], [cx - sx/2, cy + sy/2, z]], float)
    return V, np.array([[0, 1, 2], [0, 2, 3]], int)


def box(cx, cy, z0, sx, sy, h):
    x0, x1, y0, y1, z1 = cx - sx/2, cx + sx/2, cy - sy/2, cy + sy/2, z0 + h
    V = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
                  [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]], float)
    F = np.array([[0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5],
                  [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7],
                  [4, 5, 6], [4, 6, 7], [3, 2, 1], [3, 1, 0]], int)
    return V, F


#: 건물 — (이름, cx, cy, sx, sy, 높이). ⚠드론↔Tx/Rx 시선을 막지 않게 옆으로 물린다
BUILDINGS = [("bldg_a", -26.0, 14.0, 14.0, 11.0, 15.0),
             ("bldg_b", 24.0, 20.0, 12.0, 12.0, 24.0),
             ("bldg_c", -20.0, -24.0, 10.0, 16.0, 9.0),
             ("bldg_d", 30.0, -16.0, 16.0, 10.0, 18.0)]
POLES = [("pole_a", -9.0, -7.0), ("pole_b", 11.0, 6.0)]
DRONE_Z = 12.0


def build_meshes():
    made = []
    V, F = plane(0, 0, 0.0, 120.0, 120.0)
    write_obj(f"{MESH}/ground.obj", V, F)
    made.append("ground")
    for nm, cx, cy, sx, sy, h in BUILDINGS:
        V, F = box(cx, cy, 0.0, sx, sy, h)
        write_obj(f"{MESH}/{nm}.obj", V, F)
        made.append(nm)
    for nm, cx, cy in POLES:
        V, F = box(cx, cy, 0.0, 0.35, 0.35, 7.0)
        write_obj(f"{MESH}/{nm}.obj", V, F)
        made.append(nm)
    print(f"  메쉬 {len(made)} 개 → {MESH}")
    return made


def main():
    build_meshes()
    import scene_build as RP                                    # noqa
    parts = [RP.Part(name="ground", obj=f"{MESH}/ground.obj",
                     mat_key="concrete_dark", color=(0.42, 0.40, 0.37))]
    for nm, *_ in BUILDINGS:
        parts.append(RP.Part(name=nm, obj=f"{MESH}/{nm}.obj",
                             mat_key="concrete_light", color=(0.78, 0.80, 0.84)))
    for nm, *_ in POLES:
        parts.append(RP.Part(name=nm, obj=f"{MESH}/{nm}.obj",
                             mat_key="metal", color=(0.45, 0.47, 0.5)))
    # ⭐드론 — 정본 부품을 그대로 얹고 지상 12 m 로 띄운다
    # ⛔재질 키는 materials.make_material 이 아는 것만 쓴다 — 모르면 조용히 plastic 으로 흐른다
    for g, mat, col in (("body", "plastic", (0.12, 0.12, 0.14)),
                        ("canopy", "plastic_blue", (0.15, 0.18, 0.30)),
                        ("gear", "plastic", (0.18, 0.18, 0.20)),
                        ("battery", "plastic", (0.22, 0.22, 0.25)),
                        ("pcb", "pcb", (0.10, 0.30, 0.15)),
                        ("prop", "prop_plastic", (0.05, 0.05, 0.05))):
        p = f"{DRONE}/matrice4e__{g}.obj"
        if os.path.exists(p):
            parts.append(RP.Part(name=f"drone_{g}", obj=p, mat_key=mat, color=col,
                                 position=(0.0, 0.0, DRONE_Z)))
    print(f"  부품 {len(parts)} 개")
    sc = RP.build_scene(parts, fc=3.5e9)

    # ⚠기체는 0.44 m 인데 장면은 120 m 다 — **한 컷에 둘 다 못 담는다.**
    #   그래서 «환경» 컷과 «기체» 컷을 따로 찍고 덱에서 나란히 붙인다.
    cams = {
        "outdoor01_wide": ((-52.0, -56.0, 30.0), (0.0, 0.0, 9.0)),
        "outdoor01_close": ((-5.2, -6.0, 13.4), (0.0, 0.0, DRONE_Z)),
        "outdoor01_grazing": ((-34.0, -4.0, 2.2), (4.0, 1.0, DRONE_Z - 1.0)),
    }
    RP.render_views(sc, cams, OUT, resolution=(1600, 1000), num_samples=256)


if __name__ == "__main__":
    print("═══ 실외 환경 메쉬 · 렌더 ═══")
    main()
