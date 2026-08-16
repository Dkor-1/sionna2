# -*- coding: utf-8 -*-
"""
geom.py — 아주 작은 "직접 만든" 3D 메쉬 도구 (의존성 없음, numpy만 사용)
=======================================================================

목적
----
이 파일은 외부 3D 라이브러리(trimesh 등) 없이, **삼각형(triangle)만으로**
3D 모델을 만드는 가장 단순한 도구입니다. 왜 직접 만들까요?

  * 서버 sionna 환경에 trimesh 가 없고(설치 권한도 없음),
  * 무엇보다 "도형이 어떻게 만들어지는지" 코드로 눈에 보이게 하기 위해서입니다.
    (사용자가 쉽게 이해하는 것이 이 프로젝트의 1순위 목표)

핵심 개념 — 메쉬(Mesh)는 딱 두 가지로 이루어집니다
  1) 꼭짓점(vertex) 목록 : 3D 점 (x, y, z) 들의 리스트
  2) 면(face) 목록       : "몇 번 꼭짓점 3개를 이어 삼각형을 만들지"

거기에 우리는 "그룹(group)" 하나를 더 붙입니다. 면마다 어떤 **재질 그룹**
(예: body / arm / motor / prop / absorber ...)에 속하는지 이름표를 답니다.
→ 나중에 (a) matplotlib 에서 부위별 색을 칠하거나,
         (b) Sionna 에서 부위별 전파재질(RadioMaterial)을 줄 때 사용합니다.

좌표계 (중요)
  Sionna / Mitsuba 와 동일하게 **z 축이 위(up)** 입니다.
  x, y 는 바닥 평면, z 는 높이. (바닥 z=0, 천장 z=높이)

단위
  전부 **미터(m)** 로 작업합니다. 드론 제원은 mm 로 들어오므로 /1000 해서 씁니다.
"""
from __future__ import annotations

import os
import math
import numpy as np


# --------------------------------------------------------------------------- #
#  Mesh : 꼭짓점 + 삼각형 + 그룹이름  (이게 전부입니다)
# --------------------------------------------------------------------------- #
class Mesh:
    """삼각형들의 모음. .v(꼭짓점), .f(삼각형 인덱스), .g(면별 그룹이름)."""

    def __init__(self, group: str = "default"):
        self.v: list[tuple[float, float, float]] = []   # 꼭짓점 좌표
        self.f: list[tuple[int, int, int]] = []          # 0-based 삼각형 (i, j, k)
        self.g: list[str] = []                           # 면별 그룹 이름
        self._group = group                              # add_* 호출 시 기본 그룹

    # ---- 가장 기본 동작 ---------------------------------------------------- #
    def add_vertex(self, x, y, z) -> int:
        """꼭짓점 하나 추가하고, 그 인덱스(0-based)를 돌려준다."""
        self.v.append((float(x), float(y), float(z)))
        return len(self.v) - 1

    def add_tri(self, a: int, b: int, c: int, group: str | None = None):
        """이미 추가된 꼭짓점 인덱스 3개로 삼각형 하나를 만든다."""
        self.f.append((a, b, c))
        self.g.append(group if group is not None else self._group)

    def add_quad(self, a: int, b: int, c: int, d: int, group: str | None = None):
        """사각형(4점) → 삼각형 2개로 쪼개서 추가. 점은 시계/반시계로 정렬돼 있어야 함."""
        self.add_tri(a, b, c, group)
        self.add_tri(a, c, d, group)

    def merge(self, other: "Mesh", group: str | None = None):
        """다른 메쉬를 통째로 합친다(꼭짓점 인덱스 자동 보정). group 주면 덮어쓴다."""
        base = len(self.v)
        self.v.extend(other.v)
        for (a, b, c), gg in zip(other.f, other.g):
            self.f.append((a + base, b + base, c + base))
            self.g.append(group if group is not None else gg)
        return self

    # ---- 좌표 변환 (numpy 로 4x4 행렬 적용) -------------------------------- #
    def transformed(self, M: np.ndarray) -> "Mesh":
        """4x4 동차변환 M 을 적용한 **새 메쉬**를 돌려준다(원본 보존)."""
        out = Mesh(self._group)
        if self.v:
            P = np.c_[np.array(self.v), np.ones(len(self.v))]   # (N,4)
            Q = (M @ P.T).T[:, :3]
            out.v = [tuple(map(float, p)) for p in Q]
        out.f = list(self.f)
        out.g = list(self.g)
        return out

    def translated(self, dx, dy, dz):
        return self.transformed(translate(dx, dy, dz))

    def scaled(self, sx, sy=None, sz=None):
        sy = sx if sy is None else sy
        sz = sx if sz is None else sz
        return self.transformed(scale(sx, sy, sz))

    def rotated(self, axis: str, deg: float):
        return self.transformed(rotate(axis, deg))

    # ---- 정보/내보내기 ----------------------------------------------------- #
    def bounds(self):
        """(min[x,y,z], max[x,y,z]) 바운딩박스."""
        a = np.array(self.v)
        return a.min(0), a.max(0)

    def groups(self) -> list[str]:
        """등장하는 그룹 이름들(등장 순서 유지)."""
        seen, out = set(), []
        for gg in self.g:
            if gg not in seen:
                seen.add(gg); out.append(gg)
        return out

    def n_tris(self) -> int:
        return len(self.f)

    def write_obj(self, path: str, only_group: str | None = None):
        """전체(또는 한 그룹만)를 .obj 파일로 저장. Mitsuba/Sionna 가 바로 읽는다."""
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        # 어떤 면을 쓸지 고르고, 거기에 쓰인 꼭짓점만 추려 다시 번호 매김
        keep = [i for i in range(len(self.f))
                if (only_group is None or self.g[i] == only_group)]
        used, remap = [], {}
        for fi in keep:
            for vi in self.f[fi]:
                if vi not in remap:
                    remap[vi] = len(used); used.append(vi)
        with open(path, "w") as fh:
            fh.write(f"# sionna2 mesh — {os.path.basename(path)}\n")
            fh.write(f"# group={only_group or 'ALL'}  verts={len(used)}  tris={len(keep)}\n")
            for vi in used:
                x, y, z = self.v[vi]
                fh.write(f"v {x:.6f} {y:.6f} {z:.6f}\n")
            for fi in keep:
                a, b, c = self.f[fi]
                fh.write(f"f {remap[a]+1} {remap[b]+1} {remap[c]+1}\n")  # OBJ 는 1-based
        return path

    def write_obj_per_group(self, out_dir: str, prefix: str) -> dict[str, str]:
        """그룹마다 따로 .obj 저장. {그룹이름: 파일경로} 를 돌려준다.
        Sionna 는 'OBJ 1개 = SceneObject 1개 = 재질 1개' 이므로, 부위별 재질을
        주려면 이렇게 부위별로 나눠 저장한다."""
        os.makedirs(out_dir, exist_ok=True)
        paths = {}
        for gg in self.groups():
            p = os.path.join(out_dir, f"{prefix}__{gg}.obj")
            self.write_obj(p, only_group=gg)
            paths[gg] = p
        return paths


# --------------------------------------------------------------------------- #
#  4x4 변환 행렬 (z-up). 회전은 deg(도) 단위로 받음.
# --------------------------------------------------------------------------- #
def identity() -> np.ndarray:
    return np.eye(4)


def translate(dx, dy, dz) -> np.ndarray:
    M = np.eye(4); M[:3, 3] = (dx, dy, dz); return M


def scale(sx, sy=None, sz=None) -> np.ndarray:
    sy = sx if sy is None else sy
    sz = sx if sz is None else sz
    M = np.eye(4); M[0, 0], M[1, 1], M[2, 2] = sx, sy, sz; return M


def rotate(axis: str, deg: float) -> np.ndarray:
    t = math.radians(deg); c, s = math.cos(t), math.sin(t)
    M = np.eye(4)
    if axis == "x":
        M[1, 1], M[1, 2], M[2, 1], M[2, 2] = c, -s, s, c
    elif axis == "y":
        M[0, 0], M[0, 2], M[2, 0], M[2, 2] = c, s, -s, c
    elif axis == "z":
        M[0, 0], M[0, 1], M[1, 0], M[1, 1] = c, -s, s, c
    else:
        raise ValueError("axis must be 'x','y','z'")
    return M


# --------------------------------------------------------------------------- #
#  기본 도형(primitive) 들 — 전부 Mesh 를 돌려준다. 중심은 기본적으로 원점.
# --------------------------------------------------------------------------- #
def box(lx, ly, lz, center=(0, 0, 0), group="box") -> Mesh:
    """직육면체. lx,ly,lz 는 각 축 '전체' 길이. center 는 중심좌표."""
    m = Mesh(group)
    cx, cy, cz = center
    hx, hy, hz = lx / 2, ly / 2, lz / 2
    # 8 꼭짓점
    P = [(cx-hx, cy-hy, cz-hz), (cx+hx, cy-hy, cz-hz),
         (cx+hx, cy+hy, cz-hz), (cx-hx, cy+hy, cz-hz),
         (cx-hx, cy-hy, cz+hz), (cx+hx, cy-hy, cz+hz),
         (cx+hx, cy+hy, cz+hz), (cx-hx, cy+hy, cz+hz)]
    idx = [m.add_vertex(*p) for p in P]
    b, t = idx[:4], idx[4:]
    m.add_quad(b[0], b[3], b[2], b[1])      # 바닥 (아래를 향함)
    m.add_quad(t[0], t[1], t[2], t[3])      # 천장
    m.add_quad(b[0], b[1], t[1], t[0])      # 옆면 4개
    m.add_quad(b[1], b[2], t[2], t[1])
    m.add_quad(b[2], b[3], t[3], t[2])
    m.add_quad(b[3], b[0], t[0], t[3])
    return m


def quad(p0, p1, p2, p3, group="quad") -> Mesh:
    """4점으로 평면 한 장(양면 아님). 점은 한 방향(시계/반시계)으로."""
    m = Mesh(group)
    i = [m.add_vertex(*p) for p in (p0, p1, p2, p3)]
    m.add_quad(*i)
    return m


def cylinder(radius, height, axis="z", center=(0, 0, 0), seg=24,
             caps=True, group="cyl", r_top=None) -> Mesh:
    """원기둥(또는 r_top 주면 원뿔대/frustum). axis 방향으로 height 만큼.
    center 는 '가운데' 좌표(축 방향 절반 위/아래)."""
    r_top = radius if r_top is None else r_top
    m = Mesh(group)
    cx, cy, cz = center
    h = height / 2
    ring_b, ring_t = [], []
    for k in range(seg):
        a = 2 * math.pi * k / seg
        ca, sa = math.cos(a), math.sin(a)
        if axis == "z":
            ring_b.append(m.add_vertex(cx + radius*ca, cy + radius*sa, cz - h))
            ring_t.append(m.add_vertex(cx + r_top*ca, cy + r_top*sa, cz + h))
        elif axis == "x":
            ring_b.append(m.add_vertex(cx - h, cy + radius*ca, cz + radius*sa))
            ring_t.append(m.add_vertex(cx + h, cy + r_top*ca, cz + r_top*sa))
        else:  # y — +y 축 기준 오른손 방향(z=-sin)으로 감아 법선이 바깥을 향하게(z/x축과 동일 규약)
            ring_b.append(m.add_vertex(cx + radius*ca, cy - h, cz - radius*sa))
            ring_t.append(m.add_vertex(cx + r_top*ca, cy + h, cz - r_top*sa))
    for k in range(seg):
        k2 = (k + 1) % seg
        m.add_quad(ring_b[k], ring_b[k2], ring_t[k2], ring_t[k])  # 옆면
    if caps:
        cb = m.add_vertex(*( (cx, cy, cz-h) if axis=="z" else (cx-h, cy, cz) if axis=="x" else (cx, cy-h, cz)))
        ct = m.add_vertex(*( (cx, cy, cz+h) if axis=="z" else (cx+h, cy, cz) if axis=="x" else (cx, cy+h, cz)))
        for k in range(seg):
            k2 = (k + 1) % seg
            m.add_tri(cb, ring_b[k2], ring_b[k])
            m.add_tri(ct, ring_t[k], ring_t[k2])
    return m


def pyramid(base, height, apex_up=True, center=(0, 0, 0),
            base_closed=False, group="pyr") -> Mesh:
    """정사각뿔(피라미드) — 전파흡수체(absorber) 한 개를 표현.
    base = 밑변 한 변 길이, height = 높이, apex_up=True 면 +z 로 뾰족.
    밑면은 보통 벽에 붙으므로 기본적으로 안 그림(base_closed=False)."""
    m = Mesh(group)
    cx, cy, cz = center
    h = base / 2
    z0 = cz                      # 밑면 z
    apex = (cx, cy, cz + height) if apex_up else (cx, cy, cz - height)
    c = [(cx-h, cy-h, z0), (cx+h, cy-h, z0), (cx+h, cy+h, z0), (cx-h, cy+h, z0)]
    ci = [m.add_vertex(*p) for p in c]
    ai = m.add_vertex(*apex)
    for k in range(4):
        k2 = (k + 1) % 4
        if apex_up:
            m.add_tri(ci[k], ci[k2], ai)
        else:
            m.add_tri(ci[k2], ci[k], ai)
    if base_closed:
        m.add_quad(ci[0], ci[3], ci[2], ci[1])
    return m


def uv_sphere(radius, center=(0, 0, 0), seg=18, rings=10, group="sph",
              weld_poles=False) -> Mesh:
    """구. 짐벌 카메라 공/둥근 부품에 사용.

    ⭐ `weld_poles` (2026-08-16 신설, 감사 m6) — **기본은 False = 예전과 비트동일**.
      극(북/남)에서는 `seg` 개의 정점이 **같은 좌표에 겹쳐서** 쌓인다(seg=90 이면 178개,
      seg=180 이면 358개의 중복 정점). 면적 0 삼각형은 없고(2026-07-01 수정이 유효하다)
      PO 는 면 중심·법선·면적만 보므로 **RF 영향은 0** 이다. 다만 인덱스 기준으로는
      껍질이 안 닫혀 있어, 내보낸 OBJ 가 유효한 솔리드가 아니고
      `trimesh(process=False)` 로 열면 `is_watertight=False` 가 된다.
      True 로 주면 극을 **정점 1개로 공유**한다 — 삼각형의 개수·좌표·감김 방향은 그대로고
      정점 수만 2·(seg−1) 개 줄어 껍질이 인덱스 기준으로도 닫힌다.
      ⚠ 정점 인덱스가 바뀌므로 기존 OBJ 와 바이트 단위로 달라진다. 그래서 기본은 끔이다."""
    m = Mesh(group)
    cx, cy, cz = center
    grid = []
    for i in range(rings + 1):
        phi = math.pi * i / rings           # 0..pi (위->아래)
        row = []
        if weld_poles and i in (0, rings):
            # 극은 좌표가 하나뿐이다 — 정점 1개를 만들어 그 인덱스를 seg 번 재사용한다.
            z = radius * math.cos(phi)
            vi = m.add_vertex(cx, cy, cz + z)
            grid.append([vi] * seg)
            continue
        for j in range(seg):
            th = 2 * math.pi * j / seg
            x = radius * math.sin(phi) * math.cos(th)
            y = radius * math.sin(phi) * math.sin(th)
            z = radius * math.cos(phi)
            row.append(m.add_vertex(cx + x, cy + y, cz + z))
        grid.append(row)
    for i in range(rings):
        for j in range(seg):
            j2 = (j + 1) % seg
            # winding: 법선이 **바깥(outward)** 을 향하도록 (box/cylinder 와 동일 규약).
            # PO(rcs_po)는 조명면을 n̂·û>0 로 고르므로 법선 방향이 맞아야 한다.
            # 극점(i=0: φ=0, i=rings-1: φ=π) 밴드는 정점이 한 점으로 뭉쳐 사각형이면
            # 0-넓이 삼각형이 생긴다 → 삼각형 팬으로만 이어 degenerate 면을 없앤다.
            if i == 0:                                   # 북극 팬
                m.add_tri(grid[i][j], grid[i+1][j], grid[i+1][j2])
            elif i == rings - 1:                         # 남극 팬
                m.add_tri(grid[i][j], grid[i+1][j], grid[i][j2])
            else:
                m.add_quad(grid[i][j], grid[i+1][j], grid[i+1][j2], grid[i][j2])
    return m




def pyramid_field(u_len, v_len, pitch, height, group="absorber") -> Mesh:
    """xy 평면(z=0) 위, [0,u_len]x[0,v_len] 영역을 한 변 pitch 인 피라미드로 채운다.
    피라미드는 +z 로 뾰족. **독립 데모/자체점검용 프리미티브** — 챔버 벽 라이닝은
    chamber._add_pyramids_on_plane 이 벽 평면 위에 직접 생성하므로 이 함수를 쓰지 않는다."""
    m = Mesh(group)
    nu = max(1, int(round(u_len / pitch)))
    nv = max(1, int(round(v_len / pitch)))
    du, dv = u_len / nu, v_len / nv
    for i in range(nu):
        for j in range(nv):
            cx = (i + 0.5) * du
            cy = (j + 0.5) * dv
            one = pyramid(min(du, dv), height, apex_up=True,
                          center=(cx, cy, 0.0), group=group)
            m.merge(one)
    return m


if __name__ == "__main__":
    # 자체 점검: 도형 몇 개 만들어 삼각형 수와 바운딩박스 출력
    #  ⚠ 2026-08-16 — 예전 마지막 두 줄이 **존재하지 않는 `blade()`** 를 불러서
    #    `python src/geom.py` 가 NameError 로 죽었다(감사 m6 별건). 그 자리에
    #    실제로 있는 프리미티브 점검을 넣는다.
    b = box(1, 2, 3)
    print("box tris", b.n_tris(), "bounds", b.bounds())
    p = pyramid_field(4, 3, 0.5, 0.3)
    print("pyramid_field tris", p.n_tris(), "bounds", p.bounds())
    s0 = uv_sphere(1.0, seg=18, rings=10)
    s1 = uv_sphere(1.0, seg=18, rings=10, weld_poles=True)
    print(f"uv_sphere tris {s0.n_tris()} verts {len(s0.v)}  "
          f"| weld_poles=True tris {s1.n_tris()} verts {len(s1.v)} "
          f"(극점 공유로 정점 {len(s0.v)-len(s1.v)}개 감소, 삼각형은 동일)")
