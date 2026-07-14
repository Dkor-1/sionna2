# -*- coding: utf-8 -*-
"""
cadkit.py — **라이브러리를 제대로 쓰는** 3D 모델링 툴킷 (trimesh + manifold3d + shapely + scipy)
==================================================================================================
왜 새로 만드나
  `geom.py` 는 의존성 없이 삼각형을 쌓는 도구다. 그래서:
    · **불리언(CSG)이 없다** → 오목부·홈·리세스를 못 판다. 프리미티브를 겹쳐 놓을 뿐이라
      **속에 파묻힌 면**이 그대로 남는다.
    · **로프트(loft)가 없다** → 단면이 변하는 매끈한 동체(눈물방울·허리 잘록)를 못 만든다.
    · **스무딩/서브디비전이 없다** → 각진 다각기둥밖에 안 된다.
    · **검증이 없다** → 프로펠러 캡 법선이 뒤집힌 걸 몇 달간 못 잡았다.
  실제 드론 외형에 맞추려면 이게 다 필요하다. 그래서 라이브러리를 쓴다.

무엇을 쓰나
  trimesh      메쉬 컨테이너 · 프리미티브 · 스무딩 · 서브디비전 · 검증(watertight/winding/법선)
  manifold3d   **불리언 엔진** (union / difference / intersection) — trimesh 가 백엔드로 씀
  shapely      2D 단면 폴리곤(버퍼·오프셋·불리언) → 로프트/압출의 입력
  scipy        스플라인(단면 보간·암 스윕 경로)

핵심 규약
  · 모든 파트는 **watertight** 로 만든다(불리언·부피·법선 검증이 가능해진다).
  · 파트마다 **그룹 이름**(body/canopy/arm/motor/prop/gear/camera/battery/pcb/accent)을 단다
    → materials.py 가 그룹별로 Sionna RadioMaterial 과 PO |Γ| 를 붙인다(단일 진리원).
  · 마지막에 geom.Mesh 로 변환한다 → 기존 파이프라인(scene_build/rcs_sbr/microdoppler)이 그대로 돈다.
"""
from __future__ import annotations

import numpy as np
import trimesh
from scipy.interpolate import CubicSpline
from shapely.geometry import Polygon
from shapely import affinity as _aff


# --------------------------------------------------------------------------- #
#  파트 모음 — 그룹별로 trimesh 를 모았다가 geom.Mesh 로 내보낸다
# --------------------------------------------------------------------------- #
class Assembly:
    """그룹(재질) → trimesh 리스트. 마지막에 geom.Mesh 로 변환."""

    def __init__(self):
        self.parts: dict[str, list[trimesh.Trimesh]] = {}

    def add(self, mesh: trimesh.Trimesh, group: str):
        """파트를 담으며 **정리한다**: 퇴화면 제거 → 정점 병합 → 법선 바깥 정렬.
        (여기서 걸러야 PO/SBR 의 조명판정(n̂·û>0)이 오염되지 않는다.)"""
        if mesh is None or len(mesh.faces) == 0:
            return self
        m = mesh.copy()
        m.update_faces(m.nondegenerate_faces())   # 면적 0 삼각형 제거
        m.merge_vertices()
        m.remove_unreferenced_vertices()
        if len(m.faces) == 0:
            return self
        trimesh.repair.fix_normals(m)             # winding 일관화 + 바깥 정렬
        if m.is_watertight and m.volume < 0:
            m.invert()
        self.parts.setdefault(group, []).append(m)
        return self

    def add_many(self, meshes, group: str):
        for m in meshes:
            self.add(m, group)
        return self

    def union_group(self, group: str):
        """한 그룹 안의 파트들을 **불리언 합집합**으로 녹여 하나의 껍질로 만든다.
        → 겹친 부분의 **내부 면이 사라진다**(PO/SBR 이 헛세지 않는다)."""
        ms = self.parts.get(group)
        if not ms or len(ms) == 1:
            return self
        try:
            u = trimesh.boolean.union(ms, engine="manifold")
            u.update_faces(u.nondegenerate_faces())
            u.merge_vertices(); u.remove_unreferenced_vertices()
            trimesh.repair.fix_normals(u)
            if u.is_watertight and u.volume < 0:
                u.invert()
            if len(u.faces):
                self.parts[group] = [u]
        except Exception:
            pass                                   # 실패하면 그냥 둔다(합집합은 최적화일 뿐)
        return self

    def subtract(self, group: str, tool: trimesh.Trimesh):
        """그룹 전체에서 tool 을 **깎아낸다**(리세스·홈·구멍)."""
        ms = self.parts.get(group)
        if not ms:
            return self
        out = []
        for m in ms:
            try:
                r = trimesh.boolean.difference([m, tool], engine="manifold")
                out.append(r if len(r.faces) else m)
            except Exception:
                out.append(m)
        self.parts[group] = out
        return self

    def bounds(self):
        allv = np.vstack([np.asarray(m.vertices) for ms in self.parts.values() for m in ms])
        return allv.min(0), allv.max(0)

    def scaled(self, sx, sy, sz):
        S = np.diag([sx, sy, sz, 1.0])
        for g, ms in self.parts.items():
            self.parts[g] = [m.copy().apply_transform(S) for m in ms]
        return self

    def to_geom(self):
        """geom.Mesh 로 변환 (면별 그룹 이름 보존) — 기존 파이프라인이 그대로 쓴다."""
        from geom import Mesh
        out = Mesh()
        for g, ms in self.parts.items():
            for m in ms:
                base = len(out.v)
                V = np.asarray(m.vertices, float)
                F = np.asarray(m.faces, int)
                out.v.extend([tuple(map(float, p)) for p in V])
                out.f.extend([tuple(map(int, f + base)) for f in F])
                out.g.extend([g] * len(F))
        return out

    def check(self):
        """파트별 검증 — watertight / winding / 법선방향."""
        bad = []
        for g, ms in self.parts.items():
            for i, m in enumerate(ms):
                if not m.is_watertight:
                    bad.append(f"{g}[{i}] not watertight")
                elif m.volume < 0:
                    bad.append(f"{g}[{i}] inward normals")
                if not m.is_winding_consistent:
                    bad.append(f"{g}[{i}] winding inconsistent")
        return bad


# --------------------------------------------------------------------------- #
#  로프트 — 단면(shapely 폴리곤)들을 이어 매끈한 껍질을 만든다
# --------------------------------------------------------------------------- #
def _resample(poly: Polygon, n: int) -> np.ndarray:
    """폴리곤 외곽선을 n 점으로 **등간격 재샘플** (로프트하려면 단면들의 점 수가 같아야 한다)."""
    ring = poly.exterior
    d = np.linspace(0.0, ring.length, n, endpoint=False)
    return np.array([[p.x, p.y] for p in (ring.interpolate(t) for t in d)])


def loft(sections: list[tuple[float, Polygon]], n_pts: int = 48, cap=True) -> trimesh.Trimesh:
    """단면들을 x 를 따라 이어 붙인다.  sections = [(x, shapely Polygon(y,z)), ...]
    폴리곤 좌표계는 (y, z). x 는 스팬(전후) 방향.

    ※ 이게 있어야 '눈물방울 동체', '허리가 잘록한 캐노피' 같은 **진짜 곡면**이 나온다."""
    xs = [s[0] for s in sections]
    rings = [_resample(s[1], n_pts) for s in sections]
    V, F = [], []
    for i, (x, r) in enumerate(zip(xs, rings)):
        V.append(np.c_[np.full(n_pts, x), r])
    V = np.vstack(V)
    for i in range(len(xs) - 1):
        a, b = i * n_pts, (i + 1) * n_pts
        for k in range(n_pts):
            k2 = (k + 1) % n_pts
            F.append([a + k, b + k, b + k2])
            F.append([a + k, b + k2, a + k2])
    if cap:
        # 앞/뒤 캡 — 팬 삼각화 (중심점 추가)
        for end, ring, sgn in ((0, rings[0], -1), (len(xs) - 1, rings[-1], +1)):
            c = len(V)
            V = np.vstack([V, np.r_[xs[end], ring.mean(0)][None, :]])
            base = end * n_pts
            for k in range(n_pts):
                k2 = (k + 1) % n_pts
                F.append([c, base + k, base + k2][::sgn])
    m = trimesh.Trimesh(vertices=np.asarray(V, float), faces=np.asarray(F, int), process=True)
    trimesh.repair.fix_normals(m)
    return m


def superellipse(a: float, b: float, n: float = 2.6, pts: int = 96, cx=0.0, cy=0.0) -> Polygon:
    """초타원(superellipse) 단면 — n=2 면 타원, n>2 면 모서리가 둥근 직사각(드론 동체 단면).
    실제 드론 단면은 순수 타원도 박스도 아니고 이 중간이다."""
    t = np.linspace(0, 2 * np.pi, pts, endpoint=False)
    x = np.abs(np.cos(t)) ** (2.0 / n) * np.sign(np.cos(t)) * a + cx
    y = np.abs(np.sin(t)) ** (2.0 / n) * np.sign(np.sin(t)) * b + cy
    return Polygon(np.c_[x, y])


def rounded_rect(w: float, h: float, r: float, pts: int = 64, cx=0.0, cy=0.0) -> Polygon:
    """둥근 모서리 직사각 — shapely 의 buffer 로 만든다(정확한 오프셋)."""
    r = min(r, 0.49 * min(w, h))
    core = Polygon([(-w / 2 + r, -h / 2 + r), (w / 2 - r, -h / 2 + r),
                    (w / 2 - r, h / 2 - r), (-w / 2 + r, h / 2 - r)])
    p = core.buffer(r, quad_segs=max(4, pts // 8))
    return _aff.translate(p, cx, cy)


def spline_sections(xs, half_w, half_h, z_off=None, n_pow=2.6, n_sec=24, n_pts=64):
    """스플라인으로 매끈하게 보간된 단면열 → loft() 입력.
      xs      : 제어점 x 위치
      half_w  : 각 x 에서의 반폭(y)
      half_h  : 각 x 에서의 반높이(z)
      z_off   : 각 x 에서의 단면 중심 z (동체가 위로 부풀거나 코가 처지는 것)"""
    xs = np.asarray(xs, float)
    cw = CubicSpline(xs, np.asarray(half_w, float))
    ch = CubicSpline(xs, np.asarray(half_h, float))
    cz = CubicSpline(xs, np.asarray(z_off if z_off is not None else np.zeros_like(xs), float))
    xx = np.linspace(xs[0], xs[-1], n_sec)
    out = []
    for x in xx:
        w = max(1e-4, float(cw(x))); h = max(1e-4, float(ch(x))); z = float(cz(x))
        out.append((float(x), superellipse(w, h, n=n_pow, pts=n_pts, cy=z)))
    return out


# --------------------------------------------------------------------------- #
#  스윕 — 곡선 경로를 따라 단면을 밀어 만든다 (암·다리)
# --------------------------------------------------------------------------- #
def sweep(path: np.ndarray, profile_fn, n_pts: int = 24, cap=True) -> trimesh.Trimesh:
    """path[(N,3)] 를 따라 profile_fn(t)->shapely Polygon(로컬 y,z) 를 밀어 만든다.
    프레임은 path 접선 + 최소회전(parallel transport)."""
    P = np.asarray(path, float)
    T = np.gradient(P, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-12
    up = np.array([0.0, 0.0, 1.0])
    N = np.cross(up, T[0]); N /= np.linalg.norm(N) + 1e-12
    rings = []
    for i in range(len(P)):
        if i > 0:                                  # parallel transport
            v = np.cross(T[i - 1], T[i]); s = np.linalg.norm(v)
            if s > 1e-9:
                ax = v / s; ang = np.arctan2(s, float(np.dot(T[i - 1], T[i])))
                R = trimesh.transformations.rotation_matrix(ang, ax)[:3, :3]
                N = R @ N
            N -= float(np.dot(N, T[i])) * T[i]
            N /= np.linalg.norm(N) + 1e-12
        B = np.cross(T[i], N)
        prof = _resample(profile_fn(i / max(1, len(P) - 1)), n_pts)
        rings.append(P[i][None, :] + prof[:, 0:1] * N[None, :] + prof[:, 1:2] * B[None, :])
    V = np.vstack(rings); F = []
    for i in range(len(P) - 1):
        a, b = i * n_pts, (i + 1) * n_pts
        for k in range(n_pts):
            k2 = (k + 1) % n_pts
            F.append([a + k, b + k, b + k2]); F.append([a + k, b + k2, a + k2])
    if cap:
        for end, sgn in ((0, -1), (len(P) - 1, +1)):
            c = len(V)
            V = np.vstack([V, rings[end].mean(0)[None, :]])
            base = end * n_pts
            for k in range(n_pts):
                k2 = (k + 1) % n_pts
                F.append([c, base + k, base + k2][::sgn])
    m = trimesh.Trimesh(vertices=V, faces=np.asarray(F, int), process=True)
    trimesh.repair.fix_normals(m)
    return m


def revolve(profile_rz: np.ndarray, seg: int = 48, center=(0, 0, 0)) -> trimesh.Trimesh:
    """(r, z) 프로파일을 z 축으로 회전 → 회전체 (모터 벨, 짐벌 볼, RTK 돔...).
    profile_rz 는 아래→위 순서, r≥0.

    ⚠ **r=0 인 링은 하나의 꼭짓점(apex)으로 접는다.** 링으로 두면 같은 자리의 정점 seg개가
      생겨 **퇴화 삼각형(면적 0)** 이 seg개씩 쏟아진다 — trimesh 검증이 실제로 잡아냈다
      (모터 288개, 프로펠러 224개). 퇴화면은 법선이 정의되지 않아 PO/SBR 의 조명판정을 오염시킨다."""
    pr = np.asarray(profile_rz, float)
    a = np.linspace(0, 2 * np.pi, seg, endpoint=False)
    EPS = 1e-9

    V, F = [], []
    idx = []                                   # 각 프로파일 점의 정점 인덱스(링이면 리스트, apex 면 int)
    for r, z in pr:
        if r <= EPS:                           # 축 위의 점 → apex 하나
            idx.append(("apex", len(V)))
            V.append([0.0, 0.0, z])
        else:
            idx.append(("ring", len(V)))
            for k in range(seg):
                V.append([r * np.cos(a[k]), r * np.sin(a[k]), z])

    for i in range(len(pr) - 1):
        (t0, b0), (t1, b1) = idx[i], idx[i + 1]
        if t0 == "ring" and t1 == "ring":
            for k in range(seg):
                k2 = (k + 1) % seg
                F.append([b0 + k, b1 + k, b1 + k2])
                F.append([b0 + k, b1 + k2, b0 + k2])
        elif t0 == "apex" and t1 == "ring":    # 아래 apex → 링 (밖에서 봤을 때 시계 반대)
            for k in range(seg):
                k2 = (k + 1) % seg
                F.append([b0, b1 + k2, b1 + k])
        elif t0 == "ring" and t1 == "apex":    # 링 → 위 apex
            for k in range(seg):
                k2 = (k + 1) % seg
                F.append([b1, b0 + k, b0 + k2])
        # apex→apex 는 무의미(선분) → 건너뜀

    # 양끝이 링이면(옆면만 있는 원통) 평면 캡을 붙여 닫는다
    for end, sgn in ((0, -1), (len(pr) - 1, +1)):
        t, b = idx[end]
        if t == "ring":
            c = len(V)
            V.append([0.0, 0.0, float(pr[end, 1])])
            for k in range(seg):
                k2 = (k + 1) % seg
                F.append([c, b + k, b + k2][::sgn])

    m = trimesh.Trimesh(vertices=np.asarray(V, float), faces=np.asarray(F, int), process=True)
    m.update_faces(m.nondegenerate_faces())    # 남은 퇴화면 제거
    m.remove_unreferenced_vertices()
    m.apply_translation(np.asarray(center, float))
    trimesh.repair.fix_normals(m)
    return m


# --------------------------------------------------------------------------- #
#  후처리
# --------------------------------------------------------------------------- #
def smooth(m: trimesh.Trimesh, iters: int = 6, subdiv: int = 0) -> trimesh.Trimesh:
    """Taubin 스무딩(+선택 서브디비전) — 각진 로프트를 실물처럼 매끈하게."""
    out = m.copy()
    for _ in range(max(0, subdiv)):
        out = out.subdivide()
    if iters > 0:
        out = trimesh.smoothing.filter_taubin(out, iterations=iters)
    trimesh.repair.fix_normals(out)
    return out


def box(w, d, h, center=(0, 0, 0)) -> trimesh.Trimesh:
    m = trimesh.creation.box(extents=(w, d, h))
    m.apply_translation(np.asarray(center, float))
    return m


def cyl(r, h, center=(0, 0, 0), axis="z", seg=40) -> trimesh.Trimesh:
    m = trimesh.creation.cylinder(radius=r, height=h, sections=seg)
    if axis == "x":
        m.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]))
    elif axis == "y":
        m.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    m.apply_translation(np.asarray(center, float))
    return m


def sphere(r, center=(0, 0, 0), subdiv=3) -> trimesh.Trimesh:
    m = trimesh.creation.icosphere(subdivisions=subdiv, radius=r)
    m.apply_translation(np.asarray(center, float))
    return m


def capsule(r, h, center=(0, 0, 0), axis="z") -> trimesh.Trimesh:
    m = trimesh.creation.capsule(radius=r, height=h, count=[24, 24])
    if axis == "x":
        m.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]))
    elif axis == "y":
        m.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    m.apply_translation(np.asarray(center, float))
    return m


def rot_z(m: trimesh.Trimesh, deg: float) -> trimesh.Trimesh:
    return m.copy().apply_transform(
        trimesh.transformations.rotation_matrix(np.radians(deg), [0, 0, 1]))


def rot_y(m: trimesh.Trimesh, deg: float) -> trimesh.Trimesh:
    return m.copy().apply_transform(
        trimesh.transformations.rotation_matrix(np.radians(deg), [0, 1, 0]))


def mv(m: trimesh.Trimesh, x=0.0, y=0.0, z=0.0) -> trimesh.Trimesh:
    return m.copy().apply_translation([x, y, z])
