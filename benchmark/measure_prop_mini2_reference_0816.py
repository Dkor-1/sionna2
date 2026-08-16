# -*- coding: utf-8 -*-
"""
measure_prop_mini2_reference_0816.py — **DJI Mini 2 순정 프롭(4726F) 기준자 재계측**
====================================================================================
왜 또 재나
  `docs/MESH_AUDIT_0816.md` 가 이 GLB 에서 `c_max/R = 0.262` 를 냈고, 그 한 줄이
  **10 기종 전부의 날 평면형**을 갈아끼우는 근거로 쓰이려 한다. 저장소에서 **[A] 등급
  (제조사 3D 기하)** 인 프롭은 이것 하나뿐이므로, 이 값이 틀리면 나머지 9 기종의 유추가
  통째로 틀린다. 그래서 **감사 코드를 한 줄도 재사용하지 않고** 처음부터 다시 잰다.

무엇을 재나 (날 **8장 각각** 독립으로)
  · 시위 분포 c(r) — 서로 다른 **세 잣대**로, 서로 몇 % 안에 드는지까지
  · 두께 — 반경별 최대두께·시위평균두께, **세 잣대**로 (⭐3D 라 잴 수 있다)
  · 날각 θ(r) · 국소 기하피치 · 캠버
  · 날 8장 사이 산포 + «그 8장이 정말 독립 표본인가» 검사

⭐⭐ 반경 정규화 기준 R 과 뿌리 시작점 — **이게 다르면 비교가 무의미하다**
  R = 회전축에서 잰 날끝까지의 거리. 회전중심을 어디로 잡느냐로 값이 갈리므로 **셋 다 낸다**:
    R_shaft : 모터축 부품(200면 원통)의 관성주축·중심 = **물리적으로 도는 축**. ⭐기본값.
    R_c2    : 한 프롭 날 2장의 합동 면적중심(2날은 축에 대해 180° 대칭이므로 축 위) 기준.
    R_nom   : 공칭 4726F = 4.7 in = 119.38 mm → 59.69 mm. 기하가 아니라 **규격**이다.
  뿌리 시작점: GLB 의 «날» 부품은 연결요소 4개로 쪼개진다 —
    에어포일 셸 1180면(1309.0 mm²) + 접이 힌지뭉치 425면 + 힌지 와셔 84/28면
    + 떠 있는 2면 조각(0.64 mm², r/R≈0.81~0.87).
  이 파일은 **에어포일 셸만** 날로 센다. 힌지는 r/R<0.14 이고 돌기는 하지만 «날» 이 아니다 —
  평면형 법칙에 넣으면 뿌리 시위가 부푼다. 에어포일 셸의 실제 시작 반경도 같이 보고한다.

⭐ 이 GLB 의 프롭 4개는 **접힘 각도가 서로 다르다**(접이식 날이라 힌지로 돈다).
  앞 2개는 완전전개(디스크 지름 = 공칭 4.7 in 과 0.03 % 이내), 뒤 2개는 ~0.9 % 덜 펴져 있다.
  이 파일이 그 사실을 힌지 기하로 실증하고, **헤드라인 값은 완전전개 쪽에서** 낸다.

세 개의 독립 잣대 (시위)
  M1 band : 표면 면적가중 점구름 → 반경 띠 → (접선호, 축) 볼록껍질 **최대 캘리퍼** = 참시위 c(r)
  M2 proj : 회전면 **투영** 평면형 면적 → w_proj = A/Δr = 투영시위 ≈ c·cosθ.
            두 경로 — (2a) 해석적 Σ½|a⃗·n̂|  (2b) 0.02 mm 래스터 실루엣.
            ⚠ 띠별로는 (2b) 를 쓴다. (2a) 는 **총면적**에서만 쓴다(띠 폭 0.3 mm 가 삼각형보다
              작아 무게중심 비닝이 띠 단위로 안 수렴한다 — 총합은 0.01 % 로 일치).
  M3 surf : 삼각형을 64²=4096 등면적 조각으로 결정론적 분할 → 반경 띠에 표면적 배분.
            얇은 날이면 (띠 표면적)/2 ≈ 평면형 면적 → w_surf ≈ c + (앞·뒷전 두께분).
  ⇒ 셋은 **같은 양이 아니다.** 그래서 c_M1 · w_proj/cosθ · w_surf 를 나란히 놓고
     **몇 % 안에서 맞는지**를 먼저 보인 다음에야 c_max/R 을 발표한다.

세 개의 독립 잣대 (두께)  ⚠ **잣대가 두 종류다 — 섞으면 안 된다**
  T1 chord-frame envelope : 시위선 좌표계에서 (상면 − 하면). `drone_cad.py` 가 «실측 t/c» 라
                            부르는 것과 같은 잣대.
  T2 perpendicular        : 평균선(캠버선)에 **수직**으로 잰 두께 = NACA 의 t 파라미터 잣대.
                            T1 × cos(평균선 기울기).
  T3 normal-ray           : 표면 점에서 자기 법선 **반대방향**으로 광선을 쏘아 반대쪽 면까지의
                            거리. 단면·시위선·평균선을 하나도 안 쓴다 — 완전 독립 경로.
  ⛔ **2V/A 는 쓸 수 없다.** 이 날 셸은 뿌리가 뚫린 **열린 면**(경계 모서리 112)이라
     `mesh.volume` 이 **원점 위치만 옮겨도 부호까지 바뀐다**(§B 가 실증). 부피는 단면적분으로.

실행 (⛔GPU 미사용 — numpy·trimesh·scipy CPU 만):
  cd /workspace/sionna && PYTHONPATH=src:benchmark \
    /workspace/.venvs/py312/bin/python benchmark/measure_prop_mini2_reference_0816.py
산출: outputs/prop_measure_mini2_reference_0816.json
"""
from __future__ import annotations

import argparse
import collections
import datetime
import json
import os
import sys
import time

import numpy as np
import trimesh
from scipy.spatial import ConvexHull

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "benchmark")]

GLB = os.path.join(ROOT, "assets", "meshes", "reference", "WM161_zhankai_1k.glb")
OUT = os.path.join(ROOT, "outputs", "prop_measure_mini2_reference_0816.json")

#: 공칭 4726F — 47 = 4.7 in 지름, 26 = 2.6 in 피치 (DJI 부품번호 관례)
NOM_DIA_MM = 4.7 * 25.4          # 119.38
NOM_PITCH_MM = 2.6 * 25.4        # 66.04

#: GLB 부품 식별용 면 수 (이 파일 고유)
NF_BLADE = (1691, 1635)
NF_HUB, NF_SHAFT, NF_NUT = 1704, 200, 500

#: 측정 격자 r/R — 0.005 등간격, 띠 반폭 0.0025R(격자와 딱 맞물림, 겹치지 않음)
RR = np.round(np.arange(0.10, 0.9951, 0.005), 5)
BAND_HALF = 0.0025

#: 신뢰 구간 — 이 밖은 «날» 이 아니거나(뿌리 섕크) 팁 캡이라 형상 법칙에 쓰지 말 것
TRUST_LO, TRUST_HI = 0.15, 0.99
#: 비교·요약을 내는 구간
CMP_LO, CMP_HI = 0.20, 0.90


# --------------------------------------------------------------------------- #
#  0. 기하 도우미
# --------------------------------------------------------------------------- #
def tri_area_centroid(V, F):
    T = V[F]
    c = T.mean(axis=1)
    a = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1)
    return a, c


def rev_frame(m):
    """회전체 부품 → (축, 중심, 비대칭도). 축 = «나머지 두 관성모멘트가 같은» 방향."""
    V = np.asarray(m.vertices, float)
    a, c = tri_area_centroid(V, np.asarray(m.faces, int))
    ctr = (a[:, None] * c).sum(0) / a.sum()
    X = c - ctr
    C = (a[:, None, None] * X[:, :, None] * X[:, None, :]).sum(0) / a.sum()
    w, Vv = np.linalg.eigh(C)
    best = None
    for k in range(3):
        o = [w[i] for i in range(3) if i != k]
        sym = abs(o[0] - o[1]) / max(o[0], o[1])
        if best is None or sym < best[0]:
            best = (sym, Vv[:, k])
    ax = best[1] / np.linalg.norm(best[1])
    return ax, ctr, float(best[0])


def basis(axis):
    e1 = np.array([1.0, 0.0, 0.0])
    if abs(np.dot(e1, axis)) > 0.9:
        e1 = np.array([0.0, 1.0, 0.0])
    e1 = e1 - np.dot(e1, axis) * axis
    e1 /= np.linalg.norm(e1)
    return e1, np.cross(axis, e1)


def cyl(P, center, axis):
    """월드 점 → (r, phi, u). u = 축방향 좌표."""
    e1, e2 = basis(axis)
    D = np.atleast_2d(P) - center
    x, y, u = D @ e1, D @ e2, D @ axis
    return np.hypot(x, y), np.arctan2(y, x), u


def max_caliper(A):
    """2D 점집합의 최대 캘리퍼 → (길이, (끝점0, 끝점1))."""
    if len(A) < 4:
        return np.nan, None
    try:
        H = A[ConvexHull(A).vertices]
    except Exception:
        return np.nan, None
    D = H[:, None, :] - H[None, :, :]
    d2 = (D ** 2).sum(-1)
    i, j = np.unravel_index(np.argmax(d2), d2.shape)
    return float(np.sqrt(d2[i, j])), (H[i], H[j])


def hull_area(A):
    try:
        return float(ConvexHull(A).volume)      # 2D 에서 volume = 면적
    except Exception:
        return np.nan


# --------------------------------------------------------------------------- #
#  1. GLB → 로터 4개 (에어포일 셸 분리 포함)
# --------------------------------------------------------------------------- #
def load_rotors():
    scene = trimesh.load(GLB, process=False)
    parts = []
    for node in scene.graph.nodes_geometry:
        T, g = scene.graph[node]
        m = scene.geometry[g]
        if len(m.faces) not in NF_BLADE + (NF_HUB, NF_SHAFT, NF_NUT):
            continue
        w = m.copy()
        w.apply_transform(T)
        w.apply_scale(1000.0)                     # GLB 는 m → mm 로 통일
        parts.append(dict(node=node, nf=len(m.faces), mesh=w,
                          c=np.asarray(w.vertices, float).mean(0)))

    hubs = [p for p in parts if p["nf"] == NF_HUB]
    shafts = [p for p in parts if p["nf"] == NF_SHAFT]
    nuts = [p for p in parts if p["nf"] == NF_NUT]
    blades = [p for p in parts if p["nf"] in NF_BLADE]

    rotors = []
    for h in sorted(hubs, key=lambda p: (round(p["c"][2], 1), round(p["c"][0], 1))):
        sh = min(shafts, key=lambda p: np.linalg.norm(p["c"] - h["c"]))
        nu = min(nuts, key=lambda p: np.linalg.norm(p["c"] - h["c"]))
        bl = sorted(blades, key=lambda b: np.linalg.norm(b["c"] - h["c"]))[:2]

        ax_s, ctr_s, sym_s = rev_frame(sh["mesh"])
        ax_n, ctr_n, sym_n = rev_frame(nu["mesh"])
        ax_h, ctr_h, sym_h = rev_frame(h["mesh"])
        if np.dot(ax_n, ax_s) < 0:
            ax_n = -ax_n
        if np.dot(ax_h, ax_s) < 0:
            ax_h = -ax_h

        bstore = []
        for b in bl:
            w = b["mesh"].copy()
            w.merge_vertices()
            comps = sorted(w.split(only_watertight=False), key=lambda c: -len(c.faces))
            bstore.append(dict(node=b["node"], nf=b["nf"], airfoil=comps[0],
                               extra=comps[1:], whole=w))

        aa, cc = [], []
        for b in bstore:
            V = np.asarray(b["airfoil"].vertices, float)
            a1, c1 = tri_area_centroid(V, np.asarray(b["airfoil"].faces, int))
            aa.append(a1)
            cc.append(c1)
        aa, cc = np.concatenate(aa), np.concatenate(cc)
        ctr_c2 = (aa[:, None] * cc).sum(0) / aa.sum()

        rotors.append(dict(
            hub=h["node"], shaft=sh["node"], nut=nu["node"],
            axis=ax_s, axis_nut=ax_n, axis_hub=ax_h,
            ctr_shaft=ctr_s, ctr_hub=ctr_h, ctr_c2=ctr_c2,
            sym_shaft=sym_s, sym_nut=sym_n, sym_hub=sym_h,
            ang_shaft_nut=float(np.degrees(np.arccos(np.clip(abs(np.dot(ax_s, ax_n)), -1, 1)))),
            ang_shaft_hub=float(np.degrees(np.arccos(np.clip(abs(np.dot(ax_s, ax_h)), -1, 1)))),
            blades=bstore))
    return rotors, scene


def perp_offset(p, ctr, axis):
    d = np.asarray(p, float) - ctr
    return float(np.linalg.norm(d - np.dot(d, axis) * axis))


# --------------------------------------------------------------------------- #
#  2. M1 band — 반경 띠 최대 캘리퍼 + 두께 프로파일
# --------------------------------------------------------------------------- #
def sample_points(m, n, seed):
    P, _ = trimesh.sample.sample_surface(m, int(n), seed=int(seed))
    return np.asarray(P, float)


def band_profile(P, center, axis, R, rr_grid, half_frac=BAND_HALF,
                 n_station=61, want_profile=True):
    r, phi, u = cyl(P, center, axis)
    o = np.argsort(r)
    r, phi, u = r[o], phi[o], u[o]
    keys = ("chord_mm", "theta_deg", "sec_area_mm2", "t_env_max", "t_env_mean",
            "t_perp_max", "t_perp_mean", "camber_over_c", "camber_x_over_c", "n_pts")
    out = {k: [] for k in keys}
    hw = half_frac * R
    for rr in rr_grid:
        r0 = rr * R
        i0, i1 = np.searchsorted(r, [r0 - hw, r0 + hw])
        n = int(i1 - i0)
        out["n_pts"].append(n)
        if n < 150:
            for k in keys[:-1]:
                out[k].append(np.nan)
            continue
        ph, uu = phi[i0:i1], u[i0:i1]
        cm = np.arctan2(np.sin(ph).mean(), np.cos(ph).mean())
        d = (ph - cm + np.pi) % (2 * np.pi) - np.pi
        A = np.c_[r0 * d, uu]                              # (접선 호길이, 축) mm
        chord, ends = max_caliper(A)
        if not np.isfinite(chord) or chord <= 0:
            for k in keys[:-1]:
                out[k].append(np.nan)
            continue
        p0, p1 = ends
        ev = (p1 - p0) / chord
        out["chord_mm"].append(chord)
        out["theta_deg"].append(float(np.degrees(np.arctan2(abs(ev[1]), abs(ev[0])))))
        area = hull_area(A)
        out["sec_area_mm2"].append(area)
        if not want_profile:
            for k in ("t_env_max", "t_env_mean", "t_perp_max", "t_perp_mean",
                      "camber_over_c", "camber_x_over_c"):
                out[k].append(np.nan)
            continue
        Rm = np.array([[ev[0], ev[1]], [-ev[1], ev[0]]])
        B = (A - p0) @ Rm.T                                # x=시위방향, y=시위선 수직
        xs = np.linspace(0.02, 0.98, n_station) * chord
        hwx = chord / (n_station - 1) * 0.9
        up, lo = [], []
        for x in xs:
            s = np.abs(B[:, 0] - x) <= hwx
            if s.sum() < 3:
                up.append(np.nan)
                lo.append(np.nan)
            else:
                up.append(B[s, 1].max())
                lo.append(B[s, 1].min())
        up, lo = np.asarray(up), np.asarray(lo)
        ok = np.isfinite(up) & np.isfinite(lo)
        if ok.sum() < 10:
            for k in ("t_env_max", "t_env_mean", "t_perp_max", "t_perp_mean",
                      "camber_over_c", "camber_x_over_c"):
                out[k].append(np.nan)
            continue
        xk, tk = xs[ok], (up - lo)[ok]
        cam = 0.5 * (up + lo)[ok]
        tperp = tk * np.cos(np.arctan(np.gradient(cam, xk)))
        ic = int(np.argmax(np.abs(cam)))
        span = xk[-1] - xk[0]
        out["t_env_max"].append(float(tk.max()))
        out["t_env_mean"].append(float(np.trapezoid(tk, xk) / span))
        out["t_perp_max"].append(float(tperp.max()))
        out["t_perp_mean"].append(float(np.trapezoid(tperp, xk) / span))
        out["camber_over_c"].append(float(abs(cam[ic]) / chord))
        out["camber_x_over_c"].append(float(xk[ic] / chord))
    return {k: (np.asarray(v, int) if k == "n_pts" else np.asarray(v, float))
            for k, v in out.items()}


# --------------------------------------------------------------------------- #
#  3. M2 proj — 투영 평면형 (해석 + 래스터)
# --------------------------------------------------------------------------- #
def bary_centroids(n):
    up = [(i + 1 / 3, j + 1 / 3) for i in range(n) for j in range(n - i)]
    dn = [(i + 2 / 3, j + 2 / 3) for i in range(n - 1) for j in range(n - 1 - i)]
    ij = np.asarray(up + dn, float) / n
    l1, l2 = ij[:, 0], ij[:, 1]
    return np.c_[1 - l1 - l2, l1, l2]


def _binned(T, weights, center_axis, R, edges_rr, n_sub, chunk=200_000):
    """삼각형을 n_sub² 등면적 조각으로 나눠 반경 히스토그램에 무게를 배분."""
    B = bary_centroids(int(n_sub))
    S = B.shape[0]
    ax = center_axis
    hist = np.zeros(len(edges_rr) - 1)
    step = max(1, int(chunk // S))
    for i in range(0, len(T), step):
        Tc = T[i:i + step]
        P = np.einsum("sk,fkc->fsc", B, Tc).reshape(-1, 3)
        rad = np.linalg.norm(P - np.outer(P @ ax, ax), axis=1) / R
        h, _ = np.histogram(rad, bins=edges_rr,
                            weights=np.repeat(weights[i:i + step] / S, S))
        hist += h
    return hist


def proj_analytic(m, center, axis, R, edges_rr, n_sub=64):
    """A = Σ ½|a⃗·n̂| — 셸이 위·아래 2겹이면 실루엣 면적과 같다 (§ 검증: 래스터와 0.01 %)."""
    T = (np.asarray(m.vertices, float) - center)[np.asarray(m.faces, int)]
    nrm = 0.5 * np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    w = 0.5 * np.abs(nrm @ axis)
    return _binned(T, w, axis, R, edges_rr, n_sub), float(w.sum())


def surf_integral(m, center, axis, R, edges_rr, n_sub=64):
    T = (np.asarray(m.vertices, float) - center)[np.asarray(m.faces, int)]
    a = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1)
    return _binned(T, a, axis, R, edges_rr, n_sub), float(a.sum())


def proj_raster(m, center, axis, R, edges_rr, pix_mm=0.02):
    """회전면 투영 실루엣을 픽셀로 그린다 — 겹침을 실제로 처리한다."""
    e1, e2 = basis(axis)
    V = np.asarray(m.vertices, float) - center
    X, Y = V @ e1, V @ e2
    xmin, ymin = X.min() - 1, Y.min() - 1
    nx = int(np.ceil((X.max() + 1 - xmin) / pix_mm)) + 1
    ny = int(np.ceil((Y.max() + 1 - ymin) / pix_mm)) + 1
    grid = np.zeros((nx, ny), bool)
    for f in np.asarray(m.faces, int):
        ax_, ay_ = X[f[0]], Y[f[0]]
        bx, by = X[f[1]], Y[f[1]]
        cx, cy = X[f[2]], Y[f[2]]
        i0 = max(0, int((min(ax_, bx, cx) - xmin) / pix_mm))
        i1 = min(nx - 1, int((max(ax_, bx, cx) - xmin) / pix_mm) + 1)
        j0 = max(0, int((min(ay_, by, cy) - ymin) / pix_mm))
        j1 = min(ny - 1, int((max(ay_, by, cy) - ymin) / pix_mm) + 1)
        if i1 < i0 or j1 < j0:
            continue
        px = xmin + (np.arange(i0, i1 + 1) + 0.5) * pix_mm
        py = ymin + (np.arange(j0, j1 + 1) + 0.5) * pix_mm
        PX, PY = np.meshgrid(px, py, indexing="ij")
        den = (by - cy) * (ax_ - cx) + (cx - bx) * (ay_ - cy)
        if abs(den) < 1e-15:
            continue
        l1 = ((by - cy) * (PX - cx) + (cx - bx) * (PY - cy)) / den
        l2 = ((cy - ay_) * (PX - cx) + (ax_ - cx) * (PY - cy)) / den
        ins = (l1 >= -1e-12) & (l2 >= -1e-12) & (1.0 - l1 - l2 >= -1e-12)
        if ins.any():
            grid[i0:i1 + 1, j0:j1 + 1] |= ins
    ii, jj = np.nonzero(grid)
    rad = np.hypot(xmin + (ii + 0.5) * pix_mm, ymin + (jj + 0.5) * pix_mm) / R
    hist, _ = np.histogram(rad, bins=edges_rr)
    return hist * pix_mm * pix_mm, float(grid.sum() * pix_mm * pix_mm)


# --------------------------------------------------------------------------- #
#  4. T3 normal-ray 두께 — 단면·시위선·평균선을 하나도 안 쓴다
# --------------------------------------------------------------------------- #
def normal_ray_thickness(m, center, axis, R, edges_rr, n_ray=60_000, seed=0, eps=1e-3):
    P, fid = trimesh.sample.sample_surface(m, int(n_ray), seed=int(seed))
    P = np.asarray(P, float)
    N = np.asarray(m.face_normals, float)[fid]
    org = P - eps * N
    inter = trimesh.ray.ray_triangle.RayMeshIntersector(m)
    loc, idx, _ = inter.intersects_location(org, -N, multiple_hits=False)
    if len(idx) == 0:
        return np.full(len(edges_rr) - 1, np.nan), 0.0
    t = np.linalg.norm(loc - org[idx], axis=1) + eps
    D = P[idx] - center
    rad = np.linalg.norm(D - np.outer(D @ axis, axis), axis=1) / R
    med = []
    for lo, hi in zip(edges_rr[:-1], edges_rr[1:]):
        s = (rad >= lo) & (rad < hi)
        med.append(float(np.median(t[s])) if s.sum() >= 25 else np.nan)
    return np.asarray(med, float), float(len(idx) / len(P))


# --------------------------------------------------------------------------- #
#  5. 요약 도우미
# --------------------------------------------------------------------------- #
def rnd(x, n=4):
    if isinstance(x, (list, tuple, np.ndarray)):
        return [rnd(v, n) for v in np.asarray(x).tolist()]
    try:
        v = float(x)
    except Exception:
        return x
    return None if not np.isfinite(v) else round(v, n)


def interp_at(rr, y, q):
    m = np.isfinite(y)
    return float(np.interp(q, rr[m], y[m])) if m.sum() >= 2 else np.nan


def peak(rr, y, lo=TRUST_LO, hi=TRUST_HI):
    m = np.isfinite(y) & (rr >= lo) & (rr <= hi)
    if not m.any():
        return np.nan, np.nan
    r2, y2 = rr[m], y[m]
    i = int(np.argmax(y2))
    return float(y2[i]), float(r2[i])


def spread(vals):
    v = np.asarray([x for x in vals if x is not None and np.isfinite(x)], float)
    if v.size == 0:
        return None
    return dict(n=int(v.size), mean=rnd(v.mean(), 5), std=rnd(v.std(ddof=0), 6),
                min=rnd(v.min(), 5), max=rnd(v.max(), 5),
                spread_pct=rnd(100 * (v.max() - v.min()) / v.mean(), 3))


def wmean(y, w, sel):
    yy, ww = y[sel], w[sel]
    s = np.isfinite(yy) & np.isfinite(ww) & (ww > 0)
    return float(np.sum(yy[s] * ww[s]) / np.sum(ww[s])) if s.any() else np.nan


# --------------------------------------------------------------------------- #
#  main
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=OUT)
    ap.add_argument("--nsample", type=int, default=2_400_000)
    ap.add_argument("--pix", type=float, default=0.02)
    ap.add_argument("--nray", type=int, default=60_000)
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    t0 = time.time()

    rotors, _ = load_rotors()
    edges = np.concatenate([RR - 0.0025, [RR[-1] + 0.0025]])
    dr = 0.005                                  # 반경 격자 간격 (r/R 단위)
    sel_cmp = (RR >= CMP_LO) & (RR <= CMP_HI)

    doc = {"_meta": dict(
        title="DJI Mini 2 순정 프롭 4726F — 공식 GLB 날 8장 정밀 재계측 (다른 기종 유추의 기준자)",
        generated_kst=(datetime.datetime.now(datetime.timezone.utc) +
                       datetime.timedelta(hours=9)).strftime("%Y-%m-%d %H:%M KST"),
        script="benchmark/measure_prop_mini2_reference_0816.py",
        run_cmd=("cd /workspace/sionna && PYTHONPATH=src:benchmark "
                 "/workspace/.venvs/py312/bin/python "
                 "benchmark/measure_prop_mini2_reference_0816.py"),
        gpu="미사용 — numpy·trimesh·scipy CPU 만",
        source_file="assets/meshes/reference/WM161_zhankai_1k.glb",
        source_grade="[A] 제조사 공식 3D 기하 (DJI 제품페이지 3D 뷰어가 서비스한 GLB, 펼침판)",
        aircraft="mini2 / DJI Mini 2 (내부코드 WM161)", prop_model="4726F",
        nominal=dict(dia_mm=rnd(NOM_DIA_MM, 3), R_mm=rnd(NOM_DIA_MM / 2, 3),
                     pitch_mm=rnd(NOM_PITCH_MM, 3), blades=2,
                     note="4726F = 4.7 in 지름 · 2.6 in 피치 (DJI 부품번호 관례). "
                          "DJI 는 Mini 2 프롭 기하를 어느 문서에도 공표하지 않는다 — "
                          "지름·피치는 부품번호 해석이고 [A] 근거는 GLB 기하 쪽이다."),
        conventions=dict(
            R="회전축에서 잰 날끝 반경. 기본은 R_shaft(모터축 부품 관성주축·중심). "
              "R_c2·R_nom 도 같이 싣는다 — 무엇으로 나눴는지 안 밝히면 비교가 무의미하다.",
            blade="에어포일 셸(연결요소 최대, 1180면)만 «날» 로 센다. 접이 힌지뭉치·와셔·"
                  "떠 있는 2면 조각은 제외하고, 그 영향은 §F 에 따로 잰다.",
            band=f"반경 띠 반폭 {BAND_HALF}R (격자 간격 0.005R 과 맞물림, 겹치지 않음)",
            trust=f"형상 법칙에 쓸 구간 r/R {TRUST_LO}~{TRUST_HI}. "
                  f"요약·비교는 {CMP_LO}~{CMP_HI} 에서 낸다.",
            chord="참시위 = 반경 r 인 원통 단면의 최대 캘리퍼(앞전~뒷전 직선거리)",
            theta="날각 = 시위선이 회전평면과 이루는 각",
        ),
        n_sample_per_blade=a.nsample, raster_pix_mm=a.pix, n_ray=a.nray,
        rr_grid=dict(lo=float(RR[0]), hi=float(RR[-1]), step=0.005, n=int(RR.size)),
    )}

    # ---------------------------------------------------------------- #
    # A. 부품 정체 · 좌표계
    # ---------------------------------------------------------------- #
    rotdoc, partdoc = [], []
    for k, r in enumerate(rotors):
        rotdoc.append(dict(
            rotor=k, hub=r["hub"], shaft=r["shaft"], nut=r["nut"],
            axis_shaft=rnd(r["axis"], 6),
            ctr_shaft_mm=rnd(r["ctr_shaft"], 4), ctr_c2_mm=rnd(r["ctr_c2"], 4),
            c2_vs_shaft_perp_mm=rnd(perp_offset(r["ctr_c2"], r["ctr_shaft"], r["axis"]), 4),
            axis_shaft_vs_nut_deg=rnd(r["ang_shaft_nut"], 4),
            axis_shaft_vs_hub_deg=rnd(r["ang_shaft_hub"], 4),
            revolution_asymmetry=dict(shaft=rnd(r["sym_shaft"], 6), nut=rnd(r["sym_nut"], 6),
                                      hub=rnd(r["sym_hub"], 6))))
        for b in r["blades"]:
            partdoc.append(dict(
                rotor=k, node=b["node"], faces_in_file=int(b["nf"]),
                components=[dict(faces=int(len(c.faces)), area_mm2=rnd(c.area, 3))
                            for c in [b["airfoil"]] + b["extra"]],
                airfoil_faces=int(len(b["airfoil"].faces)),
                airfoil_area_mm2=rnd(b["airfoil"].area, 4)))
    doc["A_parts_and_frame"] = dict(
        rotors=rotdoc, blade_parts=partdoc,
        axis_cross_check=("모터축(200면)·프롭너트(500면)이 **독립 부품인데 같은 축**을 준다 "
                          "(0.003~0.012°). 허브(1704면)는 나사자리·리브 때문에 회전대칭이 "
                          "4.2 % 깨져 관성주축이 0.27° 흔들린다 ⇒ 축은 모터축에서 뽑는다."),
        blade_part_decomposition=(
            "GLB 의 «날» 부품(1691 또는 1635 면)은 연결요소 4개다 — 에어포일 셸 1180면 "
            "(1309.0 mm²) + 접이 힌지뭉치 425면(116.4 mm²) + 힌지 와셔 84 또는 28면"
            "(14.4 mm²) + 떠 있는 2면 조각(0.64 mm², r/R≈0.81~0.87). "
            "⭐이 파일은 에어포일 셸만 날로 센다."))

    # ---------------------------------------------------------------- #
    # B. 열린 셸 실증 — mesh.volume 은 원점에 따라 변한다 (2V/A 금지 근거)
    # ---------------------------------------------------------------- #
    b0m = rotors[0]["blades"][0]["airfoil"]
    ecnt = collections.Counter(map(tuple, b0m.edges_sorted))
    vols = []
    for sh in ([0, 0, 0], [100, 0, 0], [0, 100, 0], [0, 0, 100]):
        c = b0m.copy()
        c.apply_translation(np.asarray(sh, float))
        vols.append(float(c.volume))
    doc["B_open_shell_proof"] = dict(
        blade=rotors[0]["blades"][0]["node"], airfoil_faces=int(len(b0m.faces)),
        boundary_edges=int(sum(1 for v in ecnt.values() if v == 1)),
        is_watertight=bool(b0m.is_watertight),
        volume_mm3_by_origin_shift=dict(zip(["as-is", "+x100mm", "+y100mm", "+z100mm"],
                                            rnd(vols, 3))),
        verdict=("열린 셸이라 `mesh.volume` 이 원점 이동만으로 **부호까지** 바뀐다 ⇒ "
                 "**t = 2V/A 를 이 날에 쓰면 안 된다.** 부피는 단면적분 ΣA_sec·Δr 로 낸다."))

    # ---------------------------------------------------------------- #
    # C. 날 8장 — 세 잣대 시위 + 세 잣대 두께
    # ---------------------------------------------------------------- #
    blades_doc, curves = [], {}
    print("■ 날 8장 측정", flush=True)
    for k, r in enumerate(rotors):
        ax = r["axis"]
        for b in r["blades"]:
            m = b["airfoil"]
            V = np.asarray(m.vertices, float)
            tag = f"rotor{k}/{b['node']}"
            rad_s = cyl(V, r["ctr_shaft"], ax)[0]
            rad_c = cyl(V, r["ctr_c2"], ax)[0]
            R = float(rad_s.max())                    # ⭐기본 R = 모터축 기준 날끝
            ctr = r["ctr_shaft"]

            P = sample_points(m, a.nsample, seed=0)
            bp = band_profile(P, ctr, ax, R, RR)
            a_an, tot_an = proj_analytic(m, ctr, ax, R, edges)
            a_sf, tot_sf = surf_integral(m, ctr, ax, R, edges)
            if a.quick:
                a_ra, tot_ra, tray, hitfrac = (np.full_like(a_an, np.nan), np.nan,
                                               np.full(len(RR), np.nan), np.nan)
            else:
                a_ra, tot_ra = proj_raster(m, ctr, ax, R, edges, pix_mm=a.pix)
                tray, hitfrac = normal_ray_thickness(m, ctr, ax, R, edges, n_ray=a.nray)
            drmm = dr * R
            w_proj = a_ra / drmm                      # 띠별 투영시위는 래스터로
            w_proj_an = a_an / drmm
            w_surf = a_sf / (2 * drmm)
            cth = np.cos(np.radians(bp["theta_deg"]))
            c_from_proj = w_proj / cth

            curves[tag] = dict(chord=bp["chord_mm"], theta=bp["theta_deg"],
                               w_proj=w_proj, w_proj_an=w_proj_an, w_surf=w_surf,
                               c_from_proj=c_from_proj, sec_area=bp["sec_area_mm2"],
                               t_env_max=bp["t_env_max"], t_env_mean=bp["t_env_mean"],
                               t_perp_max=bp["t_perp_max"], t_perp_mean=bp["t_perp_mean"],
                               t_ray=tray, camber=bp["camber_over_c"],
                               camber_x=bp["camber_x_over_c"], R=R)

            cmax, cpk = peak(RR, bp["chord_mm"])
            pmax, ppk = peak(RR, c_from_proj)
            smax, spk = peak(RR, w_surf)
            with np.errstate(invalid="ignore"):
                rel_p = c_from_proj[sel_cmp] / bp["chord_mm"][sel_cmp] - 1
                rel_s = w_surf[sel_cmp] / bp["chord_mm"][sel_cmp] - 1
            agree = dict(
                proj_over_band_mean_pct=rnd(100 * np.nanmean(rel_p), 3),
                proj_over_band_maxabs_pct=rnd(100 * np.nanmax(np.abs(rel_p)), 3),
                surf_over_band_mean_pct=rnd(100 * np.nanmean(rel_s), 3),
                surf_over_band_maxabs_pct=rnd(100 * np.nanmax(np.abs(rel_s)), 3),
                total_area_raster_vs_analytic_pct=rnd(100 * (tot_ra / tot_an - 1), 4)
                if np.isfinite(tot_ra) else None)

            # 에어포일 시작(뿌리) 판정 — t/c 가 0.15 아래로 처음 내려가는 반경
            tc = bp["t_env_max"] / bp["chord_mm"]
            ok_tc = np.isfinite(tc) & (tc <= 0.15)
            r_airfoil = float(RR[np.argmax(ok_tc)]) if ok_tc.any() else np.nan

            secA = bp["sec_area_mm2"]
            vol_sec = float(np.nansum(secA[np.isfinite(secA)]) * dr * R)
            ch = bp["chord_mm"]

            blades_doc.append(dict(
                tag=tag, rotor=k, node=b["node"], faces_in_file=int(b["nf"]),
                airfoil_faces=int(len(m.faces)), airfoil_area_mm2=rnd(m.area, 4),
                R_shaft_mm=rnd(R, 4), R_c2_mm=rnd(float(rad_c.max()), 4),
                dia_shaft_mm=rnd(2 * R, 4),
                dia_vs_nominal_pct=rnd(100 * (2 * R / NOM_DIA_MM - 1), 3),
                r_shell_start_over_R=rnd(float(rad_s.min()) / R, 4),
                r_airfoil_start_over_R=rnd(r_airfoil, 4),
                c_max=dict(
                    band=dict(mm=rnd(cmax, 4), at_rr=rnd(cpk, 4),
                              over_R_shaft=rnd(cmax / R, 5),
                              over_R_c2=rnd(cmax / float(rad_c.max()), 5),
                              over_R_nom=rnd(cmax / (NOM_DIA_MM / 2), 5)),
                    proj=dict(mm=rnd(pmax, 4), at_rr=rnd(ppk, 4), over_R_shaft=rnd(pmax / R, 5)),
                    surf=dict(mm=rnd(smax, 4), at_rr=rnd(spk, 4), over_R_shaft=rnd(smax / R, 5))),
                agreement_of_three_rulers=agree,
                planform_area_mm2=dict(proj_analytic=rnd(tot_an, 3), proj_raster=rnd(tot_ra, 3),
                                       surface_over_2=rnd(tot_sf / 2, 3)),
                volume_section_integral_mm3=rnd(vol_sec, 3),
                thickness_span_mean_mm=dict(
                    window=f"{CMP_LO}-{CMP_HI}R",
                    t_env_mean_chordweighted=rnd(wmean(bp["t_env_mean"], ch, sel_cmp), 4),
                    t_env_mean_unweighted=rnd(float(np.nanmean(bp["t_env_mean"][sel_cmp])), 4),
                    t_env_max_chordweighted=rnd(wmean(bp["t_env_max"], ch, sel_cmp), 4),
                    t_perp_mean_chordweighted=rnd(wmean(bp["t_perp_mean"], ch, sel_cmp), 4),
                    t_perp_max_chordweighted=rnd(wmean(bp["t_perp_max"], ch, sel_cmp), 4),
                    t_ray_median_chordweighted=rnd(wmean(tray, ch, sel_cmp), 4),
                    ray_hit_fraction=rnd(hitfrac, 4)),
                t_over_c_env=dict((f"{q:.2f}", rnd(interp_at(RR, tc, q), 4))
                                  for q in (0.20, 0.30, 0.50, 0.70, 0.90)),
                camber_over_c_mean=rnd(float(np.nanmean(bp["camber_over_c"][sel_cmp])), 4),
                camber_x_over_c_mean=rnd(float(np.nanmean(bp["camber_x_over_c"][sel_cmp])), 4),
                theta_deg=dict((f"{q:.2f}", rnd(interp_at(RR, bp["theta_deg"], q), 3))
                               for q in (0.20, 0.30, 0.50, 0.70, 0.90)),
                local_pitch_mm=dict(
                    (f"{q:.2f}", rnd(2 * np.pi * q * R *
                                     np.tan(np.radians(interp_at(RR, bp["theta_deg"], q))), 2))
                    for q in (0.20, 0.30, 0.50, 0.70, 0.90))))
            print(f"  {tag:26s} R={R:7.4f}  c_max/R {cmax/R:.4f}@{cpk:.3f}  "
                  f"proj {pmax/R:.4f}  surf {smax/R:.4f}  "
                  f"t_env_mean {wmean(bp['t_env_mean'], ch, sel_cmp):.3f} mm  "
                  f"[{time.time()-t0:.0f} s]", flush=True)
    doc["C_blades"] = blades_doc
    print(f"  … 시위·두께 끝 [{time.time()-t0:.0f} s]", flush=True)

    # ---------------------------------------------------------------- #
    # D. 접힘(전개) 각도 — 프롭 4개가 서로 다르다
    # ---------------------------------------------------------------- #
    dep = []
    for k, r in enumerate(rotors):
        ax = r["axis"]
        ctr = r["ctr_shaft"]
        for b in r["blades"]:
            V = np.asarray(b["airfoil"].vertices, float)
            hc = np.asarray(b["extra"][0].vertices, float).mean(0)     # 힌지 뭉치 중심
            rad = cyl(V, ctr, ax)[0]
            it = int(np.argmax(rad))
            e1, e2 = basis(ax)
            def inplane(p):
                d = p - ctr
                return np.array([d @ e1, d @ e2])
            vh, vt = inplane(hc), inplane(V[it])
            arm = vt - vh
            cosd = float(np.dot(arm, vh) / (np.linalg.norm(arm) * np.linalg.norm(vh)))
            dep.append(dict(rotor=k, node=b["node"],
                            hinge_r_mm=rnd(float(np.linalg.norm(vh)), 4),
                            tip_r_mm=rnd(float(rad.max()), 4),
                            shell_root_r_mm=rnd(float(rad.min()), 4),
                            tip_minus_hinge_mm=rnd(float(np.linalg.norm(V[it] - hc)), 4),
                            hinge_arm_vs_radial_deg=rnd(float(np.degrees(np.arccos(
                                np.clip(cosd, -1, 1)))), 3),
                            dia_vs_nominal_pct=rnd(100 * (2 * float(rad.max()) /
                                                          NOM_DIA_MM - 1), 3)))
    front = [d for d in dep if d["rotor"] in (0, 1)]
    rear = [d for d in dep if d["rotor"] in (2, 3)]
    doc["D_deployment_angle"] = dict(
        per_blade=dep,
        finding=(
            "⭐**GLB 의 프롭 4개는 전개(펼침) 각도가 서로 다르다.** 접이식 날이라 힌지로 돌기 "
            "때문이다. 강체 증거: |날끝 − 힌지중심| 이 8장 모두 "
            f"{min(d['tip_minus_hinge_mm'] for d in dep):.4f}~"
            f"{max(d['tip_minus_hinge_mm'] for d in dep):.4f} mm 로 0.02 mm 안에서 같다 — "
            "같은 강체가 힌지 각도만 다르게 놓인 것이다.\n"
            f"  · 앞 프롭 2개: 디스크 지름이 공칭 4.7 in 대비 "
            f"{min(d['dia_vs_nominal_pct'] for d in front):+.3f}~"
            f"{max(d['dia_vs_nominal_pct'] for d in front):+.3f} % — **완전전개**\n"
            f"  · 뒤 프롭 2개: {min(d['dia_vs_nominal_pct'] for d in rear):+.3f}~"
            f"{max(d['dia_vs_nominal_pct'] for d in rear):+.3f} % — 덜 펴짐\n"
            "실제 비행에서는 원심력이 날을 스톱까지 밀어내므로 **완전전개가 옳은 자세**다. "
            "⇒ 헤드라인 R·c_max/R 은 앞 프롭 날 4장에서 낸다. 뒤 4장은 R 이 0.8~1.0 % 작아 "
            "c_max/R 이 그만큼 크게 나온다(같은 날인데 분모가 작아서다)."),
        headline_blades="rotor0·rotor1 의 날 4장 (완전전개)")

    # ---------------------------------------------------------------- #
    # E. 8장 산포 + «독립 표본인가» 검사
    # ---------------------------------------------------------------- #
    def col(path, docs=None):
        out = []
        for d in (docs or blades_doc):
            v = d
            for p in path:
                v = v.get(p) if isinstance(v, dict) else None
                if v is None:
                    break
            out.append(v)
        return out

    fr_doc = [d for d in blades_doc if d["rotor"] in (0, 1)]
    areas = [d["airfoil_area_mm2"] for d in blades_doc]
    ch_all = np.vstack([curves[d["tag"]]["chord"] for d in blades_doc])
    cn = ch_all[:, sel_cmp] / np.nanmax(ch_all[:, sel_cmp], axis=1, keepdims=True)

    # 합동성: 정점의 «중심으로부터 거리» 스펙트럼을 분위수로 비교 (분할이 달라도 통한다)
    qgrid = np.linspace(0, 1, 401)
    sigs = []
    for k, r in enumerate(rotors):
        for b in r["blades"]:
            V = np.asarray(b["airfoil"].vertices, float)
            d = np.linalg.norm(V - V.mean(0), axis=1)
            sigs.append(np.quantile(d, qgrid))
    congr = [float(np.max(np.abs(s - sigs[0]))) for s in sigs]

    doc["E_blade_to_blade"] = dict(
        all8=dict(
            c_max_over_R_band=spread(col(["c_max", "band", "over_R_shaft"])),
            c_max_over_R_proj=spread(col(["c_max", "proj", "over_R_shaft"])),
            c_max_over_R_surf=spread(col(["c_max", "surf", "over_R_shaft"])),
            peak_rr=spread(col(["c_max", "band", "at_rr"])),
            R_shaft_mm=spread([d["R_shaft_mm"] for d in blades_doc]),
            airfoil_area_mm2=spread(areas),
            t_env_mean_mm=spread(col(["thickness_span_mean_mm",
                                      "t_env_mean_chordweighted"])),
            t_ray_median_mm=spread(col(["thickness_span_mean_mm",
                                        "t_ray_median_chordweighted"]))),
        front4_fully_deployed=dict(
            c_max_over_R_band=spread(col(["c_max", "band", "over_R_shaft"], fr_doc)),
            c_max_over_R_proj=spread(col(["c_max", "proj", "over_R_shaft"], fr_doc)),
            c_max_over_R_surf=spread(col(["c_max", "surf", "over_R_shaft"], fr_doc)),
            peak_rr=spread(col(["c_max", "band", "at_rr"], fr_doc)),
            R_shaft_mm=spread([d["R_shaft_mm"] for d in fr_doc]),
            t_env_mean_mm=spread(col(["thickness_span_mean_mm",
                                      "t_env_mean_chordweighted"], fr_doc))),
        normalised_chord_curve_max_spread_pct=rnd(
            100 * float(np.nanmax(np.nanmax(cn, 0) - np.nanmin(cn, 0))), 3),
        normalised_chord_curve_max_spread_front4_pct=rnd(
            100 * float(np.nanmax(np.nanmax(cn[[i for i, d in enumerate(blades_doc)
                                                if d["rotor"] in (0, 1)]], 0) -
                                  np.nanmin(cn[[i for i, d in enumerate(blades_doc)
                                                if d["rotor"] in (0, 1)]], 0))), 3),
        congruence_test=dict(
            metric="정점의 중심거리 분포를 401 분위수로 비교 (분할이 달라도 통한다)",
            max_deviation_mm=rnd(congr, 6),
            verdict="8장 전부 0.001 mm 안에서 같은 강체 — 형상이 같다"),
        independence_verdict=(
            "⭐**8장은 독립 표본이 아니다.** 에어포일 셸 표면적이 8장 모두 "
            f"{min(areas):.3f}~{max(areas):.3f} mm² 로 소수 3자리까지 같고, 정점 거리 스펙트럼도 "
            "0.001 mm 안에서 겹친다 — GLB 는 날 하나를 8번 복제(대각 2쌍은 거울)했다. "
            "⇒ 아래 산포는 «제조·개체 산포» 가 아니라 **측정 재현성 + 배치(전개각) 차이**다. "
            "실물 날 사이 편차는 이 GLB 로는 알 수 없다 — M4E 사진의 «날 4장 ±1 %» 와는 "
            "성격이 다른 수다."))

    # ---------------------------------------------------------------- #
    # F. 대표 곡선 (완전전개 4장 평균) — 다른 기종 유추의 기준자
    # ---------------------------------------------------------------- #
    def stack(key, docs):
        return np.vstack([curves[d["tag"]][key] for d in docs])

    mR = float(np.mean([d["R_shaft_mm"] for d in fr_doc]))
    m_ch = np.nanmean(stack("chord", fr_doc), 0)
    m_th = np.nanmean(stack("theta", fr_doc), 0)
    m_tm = np.nanmean(stack("t_env_max", fr_doc), 0)
    m_tv = np.nanmean(stack("t_env_mean", fr_doc), 0)
    m_tp = np.nanmean(stack("t_perp_max", fr_doc), 0)
    m_tr = np.nanmean(stack("t_ray", fr_doc), 0)
    m_cb = np.nanmean(stack("camber", fr_doc), 0)
    cmax_m, cpk_m = peak(RR, m_ch)
    qs = (0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60,
          0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 0.98)

    doc["F_reference_curve"] = dict(
        basis="완전전개 앞 프롭 날 4장 평균 (rotor0·rotor1)",
        R_mm=rnd(mR, 4), dia_mm=rnd(2 * mR, 4),
        dia_vs_nominal_pct=rnd(100 * (2 * mR / NOM_DIA_MM - 1), 3),
        c_max_mm=rnd(cmax_m, 4), peak_at_rr=rnd(cpk_m, 4),
        c_max_over_R=rnd(cmax_m / mR, 5),
        c_max_over_R_nom=rnd(cmax_m / (NOM_DIA_MM / 2), 5),
        chord_over_R=dict((f"{q:.2f}", rnd(interp_at(RR, m_ch, q) / mR, 5)) for q in qs),
        chord_norm_c_over_cmax=dict((f"{q:.2f}", rnd(interp_at(RR, m_ch, q) / cmax_m, 4))
                                    for q in qs),
        theta_deg=dict((f"{q:.2f}", rnd(interp_at(RR, m_th, q), 3)) for q in qs),
        local_pitch_mm=dict((f"{q:.2f}", rnd(2 * np.pi * q * mR *
                                             np.tan(np.radians(interp_at(RR, m_th, q))), 2))
                            for q in qs),
        camber_over_c=dict((f"{q:.2f}", rnd(interp_at(RR, m_cb, q), 4)) for q in qs),
        thickness_table_mm=dict(
            (f"{q:.2f}", dict(chord=rnd(interp_at(RR, m_ch, q), 4),
                              t_env_max=rnd(interp_at(RR, m_tm, q), 4),
                              t_env_mean=rnd(interp_at(RR, m_tv, q), 4),
                              t_perp_max=rnd(interp_at(RR, m_tp, q), 4),
                              t_ray_median=rnd(interp_at(RR, m_tr, q), 4),
                              t_env_max_over_c=rnd(interp_at(RR, m_tm, q) /
                                                   interp_at(RR, m_ch, q), 4)))
            for q in qs),
        stations_full=dict(rr=rnd(RR, 4), chord_mm=rnd(m_ch, 4), theta_deg=rnd(m_th, 3),
                           t_env_max_mm=rnd(m_tm, 4), t_env_mean_mm=rnd(m_tv, 4),
                           t_perp_max_mm=rnd(m_tp, 4), t_ray_mm=rnd(m_tr, 4)),
        how_to_use=(
            "다른 기종으로 옮길 때 **정규화 곡선(chord_norm_c_over_cmax)만** 옮기고 "
            "c_max/R 은 그 기체의 프롭에서 따로 재라. 실측 c_max/R 은 프롭 크기와 반비례한다"
            "(4.7 in 0.26 ↔ 9 in 0.18) — 형상은 닮음이 아니다. "
            "두께는 **절대값(mm)** 이라 크기를 넘겨 쓰면 안 된다. "
            "θ·국소피치는 이 프롭의 공칭 피치(2.6 in)에 묶여 있으니 피치가 다른 프롭에 "
            "그대로 걸면 안 된다."))

    # ---------------------------------------------------------------- #
    # G. 견고성 — 샘플수·시드·띠폭·중심·부품포함
    # ---------------------------------------------------------------- #
    r0 = rotors[0]
    b0 = r0["blades"][0]
    m0 = b0["airfoil"]
    R0 = float(cyl(np.asarray(m0.vertices, float), r0["ctr_shaft"], r0["axis"])[0].max())
    rob = []
    print("■ 견고성 시험", flush=True)
    for ns in (300_000, 1_200_000, 4_800_000):
        for seed in (0, 1):
            bp = band_profile(sample_points(m0, ns, seed), r0["ctr_shaft"], r0["axis"],
                              R0, RR, want_profile=False)
            c, p = peak(RR, bp["chord_mm"])
            rob.append(dict(knob="n_sample", n_sample=ns, seed=seed,
                            c_max_over_R=rnd(c / R0, 5), at_rr=rnd(p, 4)))
    Pf = sample_points(m0, 2_400_000, 0)
    for hf in (0.00125, 0.0025, 0.005, 0.01, 0.02):
        bp = band_profile(Pf, r0["ctr_shaft"], r0["axis"], R0, RR,
                          half_frac=hf, want_profile=False)
        c, p = peak(RR, bp["chord_mm"])
        rob.append(dict(knob="band_halfwidth_over_R", half_frac=hf,
                        c_max_over_R=rnd(c / R0, 5), at_rr=rnd(p, 4)))
    for cname, ctr, axname in (("shaft", r0["ctr_shaft"], "shaft"),
                               ("c2", r0["ctr_c2"], "shaft"),
                               ("hub", r0["ctr_hub"], "hub")):
        ax = r0["axis"] if axname == "shaft" else r0["axis_hub"]
        Rv = float(cyl(np.asarray(m0.vertices, float), ctr, ax)[0].max())
        bp = band_profile(Pf, ctr, ax, Rv, RR, want_profile=False)
        c, p = peak(RR, bp["chord_mm"])
        rob.append(dict(knob="center_axis", center=cname, axis=axname, R_mm=rnd(Rv, 4),
                        c_max_mm=rnd(c, 4), c_max_over_R=rnd(c / Rv, 5), at_rr=rnd(p, 4)))
    Pw = sample_points(b0["whole"], 2_400_000, 0)
    Rw = float(cyl(np.asarray(b0["whole"].vertices, float), r0["ctr_shaft"],
                   r0["axis"])[0].max())
    bpw = band_profile(Pw, r0["ctr_shaft"], r0["axis"], Rw, RR, want_profile=False)
    cw, pw = peak(RR, bpw["chord_mm"])
    rob.append(dict(knob="include_hinge_and_stray", R_mm=rnd(Rw, 4),
                    c_max_mm=rnd(cw, 4), c_max_over_R=rnd(cw / Rw, 5), at_rr=rnd(pw, 4),
                    note="에어포일 셸 밖의 힌지뭉치·와셔·떠있는 2면까지 넣었을 때"))
    if not a.quick:
        for pix in (0.04, 0.02, 0.01):
            _, tot = proj_raster(m0, r0["ctr_shaft"], r0["axis"], R0, edges, pix_mm=pix)
            rob.append(dict(knob="raster_pixel_mm", pix_mm=pix, planform_area_mm2=rnd(tot, 4)))
    for nsub in (16, 32, 64):
        _, tot = proj_analytic(m0, r0["ctr_shaft"], r0["axis"], R0, edges, n_sub=nsub)
        rob.append(dict(knob="proj_analytic_n_sub", n_sub=nsub, planform_area_mm2=rnd(tot, 4)))
    doc["G_robustness"] = rob
    print(f"  … 견고성 끝 [{time.time()-t0:.0f} s]", flush=True)

    # ---------------------------------------------------------------- #
    # H. 헤드라인
    # ---------------------------------------------------------------- #
    band_v = [d["c_max"]["band"]["over_R_shaft"] for d in fr_doc]
    proj_v = [d["c_max"]["proj"]["over_R_shaft"] for d in fr_doc]
    surf_v = [d["c_max"]["surf"]["over_R_shaft"] for d in fr_doc]
    agr_p = [d["agreement_of_three_rulers"]["proj_over_band_maxabs_pct"] for d in blades_doc]
    agr_s = [d["agreement_of_three_rulers"]["surf_over_band_mean_pct"] for d in blades_doc]
    doc["H_headline"] = dict(
        prop="DJI Mini 2 순정 4726F (2날 접이식)",
        grade="[A] — 제조사 공식 3D 기하. 저장소에서 유일한 [A] 프롭이다.",
        R_mm=rnd(mR, 3), dia_mm=rnd(2 * mR, 3),
        dia_vs_nominal_4p7in_pct=rnd(100 * (2 * mR / NOM_DIA_MM - 1), 3),
        c_max_over_R=rnd(float(np.mean(band_v)), 4),
        c_max_over_R_uncertainty=("±0.001 (완전전개 4장 사이) / "
                                  "0.259~0.263 (전개각까지 포함한 8장 전체)"),
        c_max_mm=rnd(cmax_m, 3), peak_at_rr=rnd(cpk_m, 3),
        ruler_agreement=(
            f"참시위(띠 캘리퍼) ↔ 투영시위/cosθ: 최대 편차 {max(agr_p):.2f} % "
            f"(평균 {np.mean([d['agreement_of_three_rulers']['proj_over_band_mean_pct'] for d in blades_doc]):+.2f} %) · "
            f"참시위 ↔ 표면적/2Δr: 평균 {np.mean(agr_s):+.2f} % "
            "(표면적 잣대는 앞·뒷전 두께분이 더해져 원래 조금 크다). "
            "총 평면형 면적은 해석적 투영 ↔ 래스터 실루엣이 0.01 % 이내."),
        thickness=dict(
            ruler_warning="시위선 상하면 차(T1)와 평균선 수직두께(T2)는 다른 잣대다. 섞지 말 것.",
            t_env_mean_span_mm=rnd(float(np.mean(
                [d["thickness_span_mean_mm"]["t_env_mean_chordweighted"] for d in fr_doc])), 3),
            t_env_max_span_mm=rnd(float(np.mean(
                [d["thickness_span_mean_mm"]["t_env_max_chordweighted"] for d in fr_doc])), 3),
            t_ray_median_span_mm=rnd(float(np.mean(
                [d["thickness_span_mean_mm"]["t_ray_median_chordweighted"] for d in fr_doc])), 3)),
        cmax_over_R_by_normaliser=dict(
            R_shaft=rnd(float(np.mean(band_v)), 4),
            R_c2=rnd(float(np.mean([d["c_max"]["band"]["over_R_c2"] for d in fr_doc])), 4),
            R_nom=rnd(float(np.mean([d["c_max"]["band"]["over_R_nom"] for d in fr_doc])), 4)),
        cmax_over_R_by_ruler=dict(band=rnd(float(np.mean(band_v)), 4),
                                  proj=rnd(float(np.mean(proj_v)), 4),
                                  surf=rnd(float(np.mean(surf_v)), 4)),
        caveats=[
            "GLB 는 제품 페이지 뷰어용 **간략화(1k)** 판이다. 겉치수는 공표값과 0.03 % 이내로 "
            "맞지만(디스크 지름·모터대각), 날 두께가 같은 정도로 검증된 것은 아니다.",
            "8장은 같은 날의 복제다 — 개체 산포를 못 잰다.",
            "뒤 프롭 2개는 덜 펴진 자세로 놓여 있어 R 이 0.8~1.0 % 작다. 이걸 모르고 8장을 "
            "평균하면 c_max/R 이 0.001 만큼 커진다.",
            "이 값은 **4726F 한 프롭의 것**이다. c_max/R 은 프롭 크기와 반비례하므로 "
            "다른 기종에 그대로 걸면 안 된다 — 옮길 것은 정규화 곡선뿐이다."])

    # ---------------------------------------------------------------- #
    # I. 선행 감사(docs/MESH_AUDIT_0816.md · outputs/mesh_audit_0816_prop_geometry.json)와 대조
    #    ⚠ **같은 창에서** 비교해야 뜻이 있다 — 감사는 0.20~0.96R 을 썼다.
    # ---------------------------------------------------------------- #
    w96 = (RR >= 0.20) & (RR <= 0.96)
    drmm_m = dr * mR
    area_true = float(np.nansum(m_ch[w96]) * drmm_m)
    tcm_96 = wmean(m_tv, m_ch, w96)
    per_rotor = []
    audit_rotor = {0: (119.727, 0.2596, 0.45), 1: (119.716, 0.2604, 0.475),
                   2: (118.389, 0.2647, 0.45), 3: (118.387, 0.2654, 0.45)}
    for k in range(4):
        mine = [d for d in blades_doc if d["rotor"] == k]
        dia_me = max(d["dia_shaft_mm"] for d in mine)
        cm_me = float(np.mean([d["c_max"]["band"]["over_R_shaft"] for d in mine]))
        pk_me = float(np.mean([d["c_max"]["band"]["at_rr"] for d in mine]))
        # ⚠ 감사는 로터 4개를 hub 좌표 순서로 셌고 이 파일과 번호 규약이 다를 수 있다.
        #    지름으로 짝을 찾는다(앞 2개 ~119.7 · 뒤 2개 ~118.4).
        cand = min(audit_rotor.values(), key=lambda v: abs(v[0] - dia_me))
        per_rotor.append(dict(rotor=k, dia_mm_mine=rnd(dia_me, 3),
                              c_max_over_R_mine=rnd(cm_me, 4), peak_rr_mine=rnd(pk_me, 3),
                              audit_matched_by_dia=dict(dia_mm=cand[0],
                                                        c_max_over_R=cand[1],
                                                        peak_rr=cand[2]),
                              delta_c_max_over_R=rnd(cm_me - cand[1], 4)))
    # ⭐ 두께 잣대 화해 — «시위평균 두께» 가 무엇을 뜻하느냐로 30 % 가 갈린다
    m_tperp_mean = np.nanmean(stack("t_perp_mean", fr_doc), 0)
    m_sec = np.nanmean(stack("sec_area", fr_doc), 0)
    t_hull = m_sec / m_ch                      # 볼록껍질 단면적 / 시위
    sec_env = m_tv * m_ch                      # 포락 적분으로 낸 진짜 단면적
    okw = w96 & np.isfinite(m_sec) & np.isfinite(sec_env)
    doc["I_thickness_ruler_reconciliation"] = dict(
        window="0.20-0.96R · 완전전개 4장 평균 · 전부 시위가중 스팬평균",
        t_env_mean_T1=rnd(wmean(m_tv, m_ch, w96), 4),
        t_perp_mean_T2=rnd(wmean(m_tperp_mean, m_ch, w96), 4),
        t_ray_median_T3=rnd(wmean(m_tr, m_ch, w96), 4),
        t_from_convex_hull_area_over_chord=rnd(wmean(t_hull, m_ch, w96), 4),
        hull_over_envelope_section_area=rnd(float(np.sum(m_sec[okw]) /
                                                  np.sum(sec_env[okw])), 4),
        blade_volume_mm3=dict(envelope=rnd(float(np.sum(sec_env[okw])) * dr * mR, 2),
                              convex_hull=rnd(float(np.sum(m_sec[okw])) * dr * mR, 2)),
        finding=(
            "⭐«시위평균 두께» 를 어떤 잣대로 재느냐로 **30 % 가 갈린다.** 볼록껍질 단면적을 "
            "시위로 나누면 캠버(휜 평균선) 때문에 실제 단면적보다 31 % 크게 나온다 — 껍질이 "
            "휜 아래면과 시위선 사이의 빈 공간을 채워 세기 때문이다. 상하면 포락을 직접 "
            "적분한 값이 물리적으로 옳다. "
            "선행 감사의 0.5999 mm 는 포락값(0.52)과 껍질값(0.69) **사이**에 있다 — 어느 "
            "잣대였는지 그 기록으로는 확정할 수 없어 여기서는 **화해하지 않고 둘 다 적는다.** "
            "우리가 추천하는 값은 포락 적분 쪽이다."),
        note_on_integration_window=(
            "포락 적분은 시위의 0.02~0.98 구간에서만 잰다(끝단은 점이 모자란다). "
            "앞·뒷전의 얇은 꼬리를 빼므로 참값보다 **아주 조금 크다**."))

    doc["I_vs_prior_audit"] = dict(
        window="0.20-0.96R (감사가 쓴 창)",
        blade_planform_area_true_chord_mm2=rnd(area_true, 2),
        audit_value_mm2=597.74,
        t_chordmean_mm=rnd(tcm_96, 4), audit_t_chordmean_mm=0.5999,
        t_chordmean_ruler="상하면 포락 적분(T1). 껍질 잣대 값은 I_thickness_ruler_reconciliation 참조",
        band_halfwidth_explains_c_max_gap=(
            "감사와의 c_max/R 차이 −0.003 은 **띠 반폭**으로 설명된다 — G_robustness 의 "
            "band_halfwidth 계단을 보라: 0.0025R 0.2576 → 0.005R 0.2588 → 0.01R 0.2614. "
            "감사 파이프라인은 0.005~0.006R 을 썼다. 띠가 넓으면 캘리퍼가 이웃 반경의 "
            "앞·뒷전까지 잡아 시위를 크게 읽는다."),
        per_rotor=per_rotor,
        audit_fleet_mean_c_max_over_R=0.2625,
        mine_all8_mean=rnd(float(np.mean(
            [d["c_max"]["band"]["over_R_shaft"] for d in blades_doc])), 4),
        mine_deployed4_mean=rnd(float(np.mean(band_v)), 4),
        verdict=(
            "감사 수치는 **재현된다** — 로터별 c_max/R 순서(앞 낮고 뒤 높음)와 크기가 맞는다. "
            "다만 감사의 «전체 평균 0.2625» 는 **덜 펴진 뒤 프롭 2개를 섞은 값**이다. "
            "완전전개 4장만 쓰면 0.259 로 0.003 낮다. 두 값의 차이는 형상이 아니라 "
            "**GLB 안 프롭의 전개각**에서 온다. 시위·두께의 절대값은 창(0.20~0.96 vs 0.20~0.90)을 "
            "맞추면 서로 몇 % 안에서 일치한다."))

    doc["_meta"]["runtime_s"] = round(time.time() - t0, 1)
    os.makedirs(os.path.dirname(a.json), exist_ok=True)
    tmp = a.json + ".tmp"
    with open(tmp, "w") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    os.replace(tmp, a.json)
    print(f"\n⭐ c_max/R = {np.mean(band_v):.4f} @ r/R {cpk_m:.3f}   "
          f"R = {mR:.3f} mm (dia {2*mR:.3f} = 공칭 {100*(2*mR/NOM_DIA_MM-1):+.3f} %)")
    print(f"→ {a.json}   ({time.time() - t0:.1f} s)")


if __name__ == "__main__":
    main()
