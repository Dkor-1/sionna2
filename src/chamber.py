# -*- coding: utf-8 -*-
"""
chamber.py — 대형 차폐시설(전파무반사실 / anechoic chamber) 3D 모델
=====================================================================

사진(대형 차폐시설, 30 m × 20 m × 11 m)을 그대로 본떠 만듭니다.

차폐시설이 무엇인가요? (아주 쉽게)
  * "차폐(shield)"  : 바깥 전파를 막는 **금속 벽**. 안과 밖의 전파를 끊어 줍니다.
  * "무반사(anechoic)" : 안쪽 벽을 **뾰족한 전파흡수체(피라미드 폼)** 로 덮어,
                         쏜 전파가 벽에 부딪혀 되돌아오지 못하게(메아리 없게) 합니다.
  → 그래서 안에서는 마치 "끝없이 넓은 빈 하늘"처럼, 깨끗한 전파 측정이 가능합니다.
    드론 RCS(레이더 반사) 측정에 딱 맞는 환경이죠.

이 모델이 만드는 것 (사진의 구성요소 그대로)
  1) 바닥        : 체커보드(밝은/어두운 타일) — 사진의 격자 바닥
  2) 4면 벽 + 천장 : 안쪽을 향한 **피라미드 전파흡수체** 라이닝(흰색)
  3) 차폐 벽체    : 흡수체 뒤의 **금속 차폐판**(전파를 막는 실제 벽)
  4) 파란 띠      : 벽-천장 모서리의 파란 트림(사진의 파란 라인)
  5) 강철 골조    : 바깥의 회색 H-빔 외골격(사진의 철골 구조)
  6) 출입문 2개   : 뒷벽의 문 개구부

좌표계 : z-up, 단위 m. 실내 공간은 x∈[0,W], y∈[0,D], z∈[0,H].
출력   : 하나의 Mesh(부위별 그룹 이름 포함) + 부위→재질/색 매핑(manifest).
        scene 조립(scene_chamber.py)에서 그룹별로 OBJ를 나눠 Sionna 재질을 입힙니다.
"""
from __future__ import annotations

import numpy as np
from geom import Mesh, box, pyramid


# --------------------------------------------------------------------------- #
#  부위(그룹) → (Sionna 재질키, 화면표시 색 RGB, 한글 설명)
#  그룹 이름은 '접두어'로 종류를 구분한다(absorber_front, backing_left, ...).
#  - 재질키(mat_key)는 scene 조립 시 RadioMaterial 로 변환된다.
#  - 색(rgb)은 matplotlib 도식 및 Sionna 렌더의 표시색으로 쓰인다.
# --------------------------------------------------------------------------- #
def chamber_group_style(group: str) -> tuple[str, tuple, str]:
    """그룹 이름 → (재질키, 표시색 RGB, 한글설명). 접두어로 판별."""
    if group.startswith("absorber"):
        return ("absorber", (0.90, 0.90, 0.92), "전파흡수체(피라미드 폼)")
    if group.startswith("floor_light"):
        return ("concrete_light", (0.82, 0.82, 0.84), "바닥 밝은 타일")
    if group.startswith("floor_dark"):
        return ("concrete_dark", (0.42, 0.42, 0.45), "바닥 어두운 타일")
    if group.startswith("backing_ceiling"):
        return ("metal", (0.55, 0.57, 0.60), "금속 차폐 천장")
    if group.startswith("backing"):
        return ("metal", (0.62, 0.64, 0.68), "금속 차폐 벽체")
    if group.startswith("trim"):
        return ("plastic_blue", (0.16, 0.35, 0.78), "파란 모서리 트림")
    if group.startswith("frame"):
        return ("metal", (0.50, 0.52, 0.55), "강철 외골격 골조")
    if group.startswith("door"):
        return ("metal", (0.25, 0.26, 0.30), "출입문")
    return ("metal", (0.7, 0.7, 0.7), group)


# 실내(cutaway) 렌더에서 떼어내는 부위 — 앞벽/앞골조를 제거해 내부를 들여다봄
CUTAWAY_OMIT = {"absorber_front", "backing_front", "frame_front"}


def _add_pyramids_on_plane(m: Mesh, origin, u_vec, v_vec, normal,
                           pitch, height, group, skip=None):
    """평면 위([origin] 에서 u_vec, v_vec 로 펼쳐진 사각 영역)를 안쪽(normal)을
    향한 정사각뿔 전파흡수체로 촘촘히 채운다.

    origin : 영역의 한 모서리 (월드 좌표)
    u_vec, v_vec : 영역의 두 변 '전체' 벡터 (서로 수직, 평면 위)
    normal : 흡수체가 뾰족하게 향하는 '안쪽' 단위벡터
    skip   : (cx,cy,cz)->bool. True 면 그 자리 흡수체를 건너뜀(문 구멍 등)
    """
    origin = np.asarray(origin, float)
    u_vec = np.asarray(u_vec, float); v_vec = np.asarray(v_vec, float)
    normal = np.asarray(normal, float); normal = normal / np.linalg.norm(normal)
    ulen = np.linalg.norm(u_vec); vlen = np.linalg.norm(v_vec)
    uhat = u_vec / ulen; vhat = v_vec / vlen
    nu = max(1, int(round(ulen / pitch)))
    nv = max(1, int(round(vlen / pitch)))
    du = ulen / nu; dv = vlen / nv
    for i in range(nu):
        for j in range(nv):
            c = origin + (i + 0.5) * du * uhat + (j + 0.5) * dv * vhat  # 밑면 중심
            if skip is not None and skip(*c):
                continue
            # 밑면 4 모서리 (평면 위) + 꼭짓점(안쪽으로 height)
            hu, hv = du / 2, dv / 2
            p = [c - hu*uhat - hv*vhat, c + hu*uhat - hv*vhat,
                 c + hu*uhat + hv*vhat, c - hu*uhat + hv*vhat]
            apex = c + normal * height
            idx = [m.add_vertex(*pt) for pt in p]
            ai = m.add_vertex(*apex)
            for k in range(4):
                k2 = (k + 1) % 4
                m.add_tri(idx[k], idx[k2], ai, group=group)


def build_chamber(W=30.0, D=20.0, H=11.0, pitch=0.6, ab_h=0.4,
                  tile=1.0, doors=True):
    """대형 차폐시설 전체 메쉬를 만든다.

    반환: (mesh, info)  — info 에 치수/통계가 담긴다.
    부위는 mesh.g(그룹 이름)으로 구분되며 CHAMBER_MATERIALS 의 키와 일치한다.
    """
    m = Mesh()

    # ----- 1) 바닥 : 체커보드 타일 ------------------------------------------ #
    nx, ny = int(round(W / tile)), int(round(D / tile))
    for i in range(nx):
        for j in range(ny):
            x0, y0 = i * tile, j * tile
            grp = "floor_light" if (i + j) % 2 == 0 else "floor_dark"
            a = m.add_vertex(x0,        y0,        0.0)
            b = m.add_vertex(x0 + tile, y0,        0.0)
            c = m.add_vertex(x0 + tile, y0 + tile, 0.0)
            d = m.add_vertex(x0,        y0 + tile, 0.0)
            m.add_quad(a, b, c, d, group=grp)

    # ----- 출입문 위치(뒷벽 y=D) : 흡수체에서 비워둘 사각형 ------------------ #
    door_rects = []
    if doors:
        dw, dh = 2.0, 3.2                       # 문 폭/높이 [m]
        for xc in (W * 0.40, W * 0.62):
            door_rects.append((xc - dw/2, xc + dw/2, 0.0, dh))   # (x0,x1,z0,z1)

    def _skip_backwall(cx, cy, cz):
        for (x0, x1, z0, z1) in door_rects:
            if x0 <= cx <= x1 and z0 <= cz <= z1:
                return True
        return False

    # ----- 2) 4면 벽 + 천장 흡수체 라이닝 ----------------------------------- #
    # 각 벽: origin, u_vec(가로), v_vec(세로=높이), inward normal.
    # 흡수체 그룹은 '벽별'로 분리 → 실내 렌더 시 앞벽만 떼어내는 cutaway 가능.
    #  앞벽 y=0  → 안쪽 +y
    _add_pyramids_on_plane(m, (0, 0, 0), (W, 0, 0), (0, 0, H), (0, 1, 0),
                           pitch, ab_h, "absorber_front")
    #  뒷벽 y=D  → 안쪽 -y  (문 구멍 비움)
    _add_pyramids_on_plane(m, (0, D, 0), (W, 0, 0), (0, 0, H), (0, -1, 0),
                           pitch, ab_h, "absorber_back", skip=_skip_backwall)
    #  좌벽 x=0  → 안쪽 +x
    _add_pyramids_on_plane(m, (0, 0, 0), (0, D, 0), (0, 0, H), (1, 0, 0),
                           pitch, ab_h, "absorber_left")
    #  우벽 x=W  → 안쪽 -x
    _add_pyramids_on_plane(m, (W, 0, 0), (0, D, 0), (0, 0, H), (-1, 0, 0),
                           pitch, ab_h, "absorber_right")
    #  천장 z=H  → 안쪽 -z
    _add_pyramids_on_plane(m, (0, 0, H), (W, 0, 0), (0, D, 0), (0, 0, -1),
                           pitch, ab_h, "absorber_ceiling")

    # ----- 3) 금속 차폐 벽체/천장 (흡수체 '뒤'의 실제 벽) -------------------- #
    eps = 0.05
    m.merge(box(W, eps, H, center=(W/2, -eps/2,     H/2), group="backing_front"))
    m.merge(box(W, eps, H, center=(W/2, D + eps/2,  H/2), group="backing_back"))
    m.merge(box(eps, D, H, center=(-eps/2,    D/2, H/2), group="backing_left"))
    m.merge(box(eps, D, H, center=(W + eps/2, D/2, H/2), group="backing_right"))
    m.merge(box(W, D, eps, center=(W/2, D/2, H + eps/2), group="backing_ceiling"))

    # ----- 4) 파란 모서리 트림 (벽-천장 경계 둘레) -------------------------- #
    tb = 0.25                                   # 트림 두께
    zc = H - tb/2
    m.merge(box(W, tb, tb, center=(W/2, tb/2,     zc), group="trim_blue"))
    m.merge(box(W, tb, tb, center=(W/2, D - tb/2, zc), group="trim_blue"))
    m.merge(box(tb, D, tb, center=(tb/2,     D/2, zc), group="trim_blue"))
    m.merge(box(tb, D, tb, center=(W - tb/2, D/2, zc), group="trim_blue"))

    # ----- 5) 강철 외골격 골조 (벽 바깥) ----------------------------------- #
    off = 0.35                                  # 벽에서 바깥으로 떨어진 거리
    col = 0.30                                  # 기둥 단면
    top = H + 0.7                               # 골조가 벽보다 살짝 높음
    xs = list(np.linspace(0, W, int(round(W / 7.5)) + 1))   # 기둥 x 위치
    ys = list(np.linspace(0, D, int(round(D / 7.5)) + 1))   # 기둥 y 위치
    # 모서리/둘레 기둥. 앞면(y=-off) 골조는 'frame_front'로 따로 → cutaway 가능.
    for x in xs:
        m.merge(box(col, col, top, center=(x, -off,    top/2), group="frame_front"))
        m.merge(box(col, col, top, center=(x, D + off, top/2), group="frame_steel"))
    for y in ys:
        m.merge(box(col, col, top, center=(-off,    y, top/2), group="frame_steel"))
        m.merge(box(col, col, top, center=(W + off, y, top/2), group="frame_steel"))
    # 상단 둘레 보(beam)
    m.merge(box(W + 2*off, col, col, center=(W/2, -off,    top), group="frame_front"))
    m.merge(box(W + 2*off, col, col, center=(W/2, D + off, top), group="frame_steel"))
    m.merge(box(col, D + 2*off, col, center=(-off,    D/2, top), group="frame_steel"))
    m.merge(box(col, D + 2*off, col, center=(W + off, D/2, top), group="frame_steel"))

    # ----- 6) 출입문 패널 (뒷벽 개구부 안쪽) -------------------------------- #
    for (x0, x1, z0, z1) in door_rects:
        m.merge(box(x1 - x0, 0.06, z1 - z0,
                    center=((x0+x1)/2, D - 0.06, (z0+z1)/2), group="door"))

    info = dict(W=W, D=D, H=H, pitch=pitch, ab_h=ab_h, tile=tile,
                n_tris=m.n_tris(), groups=m.groups(),
                door_rects=door_rects,
                interior_clear=(W - 2*ab_h, D - 2*ab_h, H - ab_h))
    return m, info


if __name__ == "__main__":
    import os
    m, info = build_chamber()
    print("== 대형 차폐시설 ==")
    for k, v in info.items():
        print(f"  {k}: {v}")
    out = os.path.join(os.path.dirname(__file__), "..", "assets", "meshes", "chamber")
    paths = m.write_obj_per_group(os.path.abspath(out), "chamber")
    print("부위별 OBJ 저장:")
    for g, p in paths.items():
        print(f"  {g:16s} -> {os.path.relpath(p)}")
