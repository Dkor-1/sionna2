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
        else:  # y
            ring_b.append(m.add_vertex(cx + radius*ca, cy - h, cz + radius*sa))
            ring_t.append(m.add_vertex(cx + r_top*ca, cy + h, cz + r_top*sa))
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


def uv_sphere(radius, center=(0, 0, 0), seg=18, rings=10, group="sph") -> Mesh:
    """구. 짐벌 카메라 공/둥근 부품에 사용."""
    m = Mesh(group)
    cx, cy, cz = center
    grid = []
    for i in range(rings + 1):
        phi = math.pi * i / rings           # 0..pi (위->아래)
        row = []
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
            m.add_quad(grid[i][j], grid[i][j2], grid[i+1][j2], grid[i+1][j])
    return m


def blade(length, width, thick, group="prop") -> Mesh:
    """프로펠러 날개 한 장. +x 방향으로 length, 살짝 둥근 얇은 판."""
    m = Mesh(group)
    L, w, t = length, width / 2, thick / 2
    # 뿌리(좁게)→끝(넓다가 다시 좁아짐) 단순 8각 판을 위/아래 2겹으로
    prof = [(0.04*L, 0.35*w), (0.30*L, w), (0.70*L, w), (0.97*L, 0.5*w),
            (0.97*L, -0.5*w), (0.70*L, -w), (0.30*L, -w), (0.04*L, -0.35*w)]
    top = [m.add_vertex(x, y, t) for x, y in prof]
    bot = [m.add_vertex(x, y, -t) for x, y in prof]
    n = len(prof)
    # 위/아래 면 (팬 삼각형)
    for k in range(1, n - 1):
        m.add_tri(top[0], top[k], top[k+1])
        m.add_tri(bot[0], bot[k+1], bot[k])
    # 옆 테두리
    for k in range(n):
        k2 = (k + 1) % n
        m.add_quad(top[k], top[k2], bot[k2], bot[k])
    return m


def prop_blade(R, root=0.12, thick=None, pitch_deg=18.0, twist_deg=11.0,
               sweep=0.10, n=10, group="prop") -> Mesh:
    """**곡면·트위스트·테이퍼 프로펠러 날개 1장** (평면 8각판 blade() 의 사실적 버전).
    +x = 스팬(길이) 방향, y = 시위(chord), z = 두께. 루트→팁으로 시위가 변하고(테이퍼),
    피치가 줄며(워시아웃 트위스트), 회전방향으로 약간 휜다(scimitar sweep). 끝은 좁고 둥글다.
      R         : 날개 길이(=프로펠러 반경) [m]
      root      : 루트 시작 반경비(허브 안쪽 비움)
      pitch_deg : 루트 피치(받음각), twist_deg : 루트→팁 워시아웃 감소량
      sweep     : 후퇴 곡선량(반경 대비), n : 스팬 분할
    단면은 시위 방향 직사각(LE_top,TE_top,TE_bot,LE_bot) 링을 트위스트시켜 잇는다."""
    m = Mesh(group)
    r0 = root * R
    thick = thick if thick is not None else 0.012 * R

    def chord(t):                                    # 시위 분포(루트 좁→0.3R 최대→끝 둥글게)
        ts = [0.0, 0.15, 0.35, 0.80, 1.0]
        cs = [0.10, 0.20, 0.22, 0.16, 0.03]
        # 선형보간(numpy 없이)
        for j in range(len(ts) - 1):
            if t <= ts[j + 1]:
                f = (t - ts[j]) / (ts[j + 1] - ts[j] + 1e-12)
                return (cs[j] + f * (cs[j + 1] - cs[j])) * R
        return cs[-1] * R

    rings = []
    for i in range(n + 1):
        t = i / n
        x = r0 + (R - r0) * t
        c = chord(t)
        th = math.radians(pitch_deg - twist_deg * t)         # 워시아웃 트위스트
        cy = sweep * R * math.sin(math.pi / 2 * t)           # 후퇴 곡선
        ct, st = math.cos(th), math.sin(th)
        ring = []
        for s, zc in [(-0.5, +thick/2), (+0.5, +thick/2), (+0.5, -thick/2), (-0.5, -thick/2)]:
            yy, zz = s * c, zc                               # 시위(y)·두께(z)
            y = cy + yy * ct - zz * st                       # x축(스팬) 둘레 트위스트
            z = yy * st + zz * ct
            ring.append(m.add_vertex(x, y, z))
        rings.append(ring)
    for i in range(n):                                       # 스팬 방향으로 잇기
        a, b = rings[i], rings[i + 1]
        for k in range(4):
            k2 = (k + 1) % 4
            m.add_quad(a[k], a[k2], b[k2], b[k])
    m.add_quad(rings[0][0], rings[0][1], rings[0][2], rings[0][3])     # 루트 캡
    m.add_quad(rings[-1][3], rings[-1][2], rings[-1][1], rings[-1][0]) # 팁 캡
    return m


def hull(lx, ly, lz, sides=12, taper_top=0.72, center=(0, 0, 0), group="hull") -> Mesh:
    """**둥근 동체** — 타원 단면(반경 lx/2, ly/2)의 다각 기둥, 위로 갈수록 taper_top 배로 좁아짐.
    sides 를 크게 하면 매끈해진다(박스 대신). 드론 동체/캐노피에 사용."""
    m = Mesh(group)
    cx, cy, cz = center; hx, hy, hz = lx/2, ly/2, lz/2
    bot, top = [], []
    for k in range(sides):
        a = 2 * math.pi * k / sides; ca, sa = math.cos(a), math.sin(a)
        bot.append(m.add_vertex(cx + hx*ca, cy + hy*sa, cz - hz))
        top.append(m.add_vertex(cx + taper_top*hx*ca, cy + taper_top*hy*sa, cz + hz))
    for k in range(sides):
        k2 = (k + 1) % sides
        m.add_quad(bot[k], bot[k2], top[k2], top[k])
    cb = m.add_vertex(cx, cy, cz - hz); ct = m.add_vertex(cx, cy, cz + hz)
    for k in range(sides):
        k2 = (k + 1) % sides
        m.add_tri(cb, bot[k2], bot[k]); m.add_tri(ct, top[k], top[k2])
    return m


# --------------------------------------------------------------------------- #
#  편의: 평평한 사각 영역을 '피라미드 밭'으로 채우기 (전파흡수체 라이닝)
# --------------------------------------------------------------------------- #
def pyramid_field(u_len, v_len, pitch, height, group="absorber") -> Mesh:
    """xy 평면(z=0) 위, [0,u_len]x[0,v_len] 영역을 한 변 pitch 인 피라미드로 채운다.
    피라미드는 +z 로 뾰족. 만들어 두고 호출부에서 원하는 벽으로 회전/이동시킨다.
    (벽 라이닝은 chamber.py 에서 이 밭을 회전시켜 각 벽에 붙인다.)"""
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
    b = box(1, 2, 3)
    print("box tris", b.n_tris(), "bounds", b.bounds())
    p = pyramid_field(4, 3, 0.5, 0.3)
    print("pyramid_field tris", p.n_tris(), "bounds", p.bounds())
    bl = blade(0.12, 0.025, 0.003)
    print("blade tris", bl.n_tris())
