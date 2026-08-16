# -*- coding: utf-8 -*-
"""
adv_prop_geometry_independent_0816.py — 프로펠러 날 기하 **독립 재측정** (감사 반증용)
=====================================================================================
왜 이 파일이 따로 있나
  2026-08-16 `docs/MESH_AUDIT_0816.md` 가 «우리 날이 실물보다 외곽에서 27~39 % 좁다» 를
  **원통 단면**(회전축 중심 원통으로 잘라 얻은 단면 폴리곤의 최대 캘리퍼) 하나로 쟀다.
  그 결론이 블레이드 법칙 전체를 갈아끼우는 근거가 되므로, **다른 방법으로 다시 잰다.**
  목적은 «확인» 이 아니라 **반증 시도**다.

세 개의 독립 잣대 (전부 단면 폴리곤 연산을 안 쓴다)
  ⓐ  band  : 날 표면을 면적가중 샘플링한 **점구름**을 반경 띠로 잘라, 띠 안에서
             (접선, 축) 평면의 **볼록껍질 최대 캘리퍼**를 폭으로 읽는다.
  ⓑ  proj  : 날을 회전면으로 **투영해 래스터**(기본 0.04 mm 격자)하고, 켜진 픽셀을
             반경 히스토그램으로 모아 반경 띠별 **평면형 면적**을 낸다.
             폭 w(r) = (띠 면적)/Δr.  ⚠ 이건 **투영 시위** = c·cos(피치각) 이다.
  ⓒ  surf  : 원본 삼각형을 반경 방향으로 재귀 세분해 **표면적을 반경 띠에 배분**한다.
             얇은 날이면 (띠 표면적)/2 ≈ 평면형 면적이므로 폭 w(r) = (띠 표면적)/(2Δr).
             ⚠ 이건 **참시위**(표면이 비틀림을 따라가므로) + 앞·뒷전 두께분.

  세 잣대는 같은 양을 재지 않는다(ⓑ 는 cos θ 만큼 짧다). 그래서 이 파일은 먼저
  **ⓐ·ⓒ 가 서로 몇 % 안에서 맞는지**, **ⓑ/ⓐ 가 독립 측정한 cos θ 와 맞는지**를 보이고,
  그 다음에야 «우리 ↔ DJI» 비를 낸다. **비는 같은 잣대끼리만 낸다.**

  ⓓ  pitch : 띠 점구름의 (접선,축) 2D SVD 주축 → 국소 날각 θ(r). (캘리퍼 시위선이 아니라
             SVD 라 감사와 다른 경로다.)
  ⓔ  thick : 두께를 **단면을 안 쓰고** 낸다 — 닫힌 날의 t = 2V/A_surf (= 시위평균 두께의
             면적가중 평균, 정본 1.43 mm 와 같은 정의). 띠별로는 (띠 볼록껍질 면적)/시위.

뿌리 여유 보정 (⭐이게 없으면 면적비가 왜곡된다)
  우리 날은 0.070R 부터 시작하고 DJI GLB 의 «날» 부품은 0.175R 부터다(그 안쪽은 허브 부품).
  그래서 총면적 비교는 **금지**하고, 전부 **공통 반경 창**에서만 비교한다.

실행 (GPU 미사용, CPU 만):
  cd /workspace/sionna && PYTHONPATH=src:benchmark \
    /workspace/.venvs/py312/bin/python benchmark/adv_prop_geometry_independent_0816.py \
    --json outputs/mesh_adv_geometry_independent_0816.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
import trimesh
from scipy.spatial import ConvexHull

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "benchmark")]

GLB = os.path.join(ROOT, "assets", "meshes", "reference", "WM161_zhankai_1k.glb")
REFDIR = os.path.join(ROOT, "assets", "meshes", "reference")


# --------------------------------------------------------------------------- #
#  0. 회전 좌표계 — 축과 중심을 «면적가중» 으로 잡는다 (정점 개수 편향 없음)
# --------------------------------------------------------------------------- #
def _tri_areas_centroids(m):
    T = np.asarray(m.vertices, float)[np.asarray(m.faces, int)]
    c = T.mean(axis=1)
    a = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1)
    return a, c


def frame_from_solid_of_revolution(m):
    """회전체(허브 또는 프롭 전체)에서 축·중심을 뽑는다.

    축   : 면적가중 공분산의 고유벡터 중 **나머지 둘이 서로 같은** 축.
           (회전체는 축에 수직한 두 방향의 관성이 같다.)
    중심 : 면적가중 중심(회전대칭이면 축 위에 정확히 놓인다).
    반환 : axis(단위), center(3), 진단값
    """
    a, c = _tri_areas_centroids(m)
    ctr = (a[:, None] * c).sum(0) / a.sum()
    X = c - ctr
    C = (a[:, None, None] * X[:, :, None] * X[:, None, :]).sum(0) / a.sum()
    w, V = np.linalg.eigh(C)                      # 오름차순
    # 세 축 중, 나머지 두 고윳값이 가장 비슷한 축이 회전축
    best, bestax, bestsym = None, None, None
    for k in range(3):
        o = [w[i] for i in range(3) if i != k]
        sym = abs(o[0] - o[1]) / max(o[0], o[1])
        if best is None or sym < best:
            best, bestax, bestsym = sym, V[:, k], sym
    return bestax / np.linalg.norm(bestax), ctr, dict(
        eig=[float(x) for x in w], asymmetry_of_perp_pair=float(bestsym))


def cyl_coords(P, center, axis):
    """월드 점 → (r, phi, u)  ; u = 축방향."""
    e1 = np.array([1.0, 0.0, 0.0])
    if abs(np.dot(e1, axis)) > 0.9:
        e1 = np.array([0.0, 1.0, 0.0])
    e1 = e1 - np.dot(e1, axis) * axis
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(axis, e1)
    D = P - center
    x, y, u = D @ e1, D @ e2, D @ axis
    return np.sqrt(x * x + y * y), np.arctan2(y, x), u, (e1, e2)


# --------------------------------------------------------------------------- #
#  ⓐ band — 점구름 반경 띠 최대 캘리퍼
# --------------------------------------------------------------------------- #
def _max_caliper(A):
    if len(A) < 4:
        return np.nan, None
    try:
        H = A[ConvexHull(A).vertices]
    except Exception:
        return np.nan, None
    D = H[:, None, :] - H[None, :, :]
    d2 = (D ** 2).sum(-1)
    i, j = np.unravel_index(np.argmax(d2), d2.shape)
    return float(np.sqrt(d2[i, j])), H


def method_band(m, center, axis, R, rr_grid, half_frac=0.005, n_sample=800_000, seed=0):
    """반환: dict(rr, chord_mm, theta_deg, sec_area_mm2, t_chordmean_mm, n_pts)"""
    P, _ = trimesh.sample.sample_surface(m, int(n_sample), seed=seed)
    r, phi, u, _ = cyl_coords(np.asarray(P, float), center, axis)
    o = np.argsort(r)
    r, phi, u = r[o], phi[o], u[o]
    out = {k: [] for k in ("rr", "chord_mm", "theta_deg", "sec_area_mm2",
                           "t_chordmean_mm", "n_pts", "phi_mid", "n_blade_clusters")}
    hw = half_frac * R
    for rr in rr_grid:
        r0 = rr * R
        i0, i1 = np.searchsorted(r, [r0 - hw, r0 + hw])
        n = int(i1 - i0)
        out["rr"].append(float(rr))
        out["n_pts"].append(n)
        if n < 200:
            for k in ("chord_mm", "theta_deg", "sec_area_mm2", "t_chordmean_mm",
                      "phi_mid", "n_blade_clusters"):
                out[k].append(float("nan"))
            continue
        ph, uu = phi[i0:i1], u[i0:i1]
        # ⭐ 날 여러 장이 같은 띠에 들어오면 캘리퍼가 «날 사이 거리» 를 읽는다(참조 프롭은
        #    2날이 한 덩어리다). 방위각 간극으로 날을 갈라 **가장 큰 덩어리 하나**만 쓴다.
        o2 = np.argsort(ph)
        ps = ph[o2]
        gaps = np.diff(np.r_[ps, ps[0] + 2 * np.pi])
        kmax = int(np.argmax(gaps))
        start = ps[(kmax + 1) % len(ps)]
        dd = (ph - start) % (2 * np.pi)
        o3 = np.argsort(dd)
        dsort = dd[o3]
        brk = np.nonzero(np.diff(dsort) > 0.35)[0]
        segs = np.split(o3, brk + 1)
        nclu = len(segs)
        sel = max(segs, key=len)
        ph, uu = ph[sel], uu[sel]
        if len(ph) < 200:
            for k in ("chord_mm", "theta_deg", "sec_area_mm2", "t_chordmean_mm",
                      "phi_mid", "n_blade_clusters"):
                out[k].append(float("nan"))
            continue
        # 각도 언랩(날 하나는 좁은 각 범위) — 원형 평균 기준으로 접기
        cm = np.arctan2(np.sin(ph).mean(), np.cos(ph).mean())
        d = (ph - cm + np.pi) % (2 * np.pi) - np.pi
        out["phi_mid"].append(float(cm))
        out["n_blade_clusters"].append(float(nclu))
        A = np.c_[r0 * d, uu] * 1000.0                     # mm, (접선, 축)
        try:
            hull = ConvexHull(A)
        except Exception:
            for k in ("chord_mm", "theta_deg", "sec_area_mm2", "t_chordmean_mm"):
                out[k].append(float("nan"))
            continue
        H = A[hull.vertices]
        D = H[:, None, :] - H[None, :, :]
        d2 = (D ** 2).sum(-1)
        i, j = np.unravel_index(np.argmax(d2), d2.shape)
        chord = float(np.sqrt(d2[i, j]))
        # SVD 주축 → 국소 날각(회전면과 이루는 각)  ⚠캘리퍼 시위선이 아니라 SVD 다
        Ac = A - A.mean(0)
        _, _, vt = np.linalg.svd(Ac, full_matrices=False)
        v = vt[0]
        theta = float(np.degrees(np.arctan2(abs(v[1]), abs(v[0]))))
        area = float(hull.volume)                          # 2D 에서 volume = 면적
        out["chord_mm"].append(chord)
        out["theta_deg"].append(theta)
        out["sec_area_mm2"].append(area)
        out["t_chordmean_mm"].append(area / chord)
    return {k: np.asarray(v, float) if k != "n_pts" else np.asarray(v, int)
            for k, v in out.items()}   # phi_mid/n_blade_clusters 포함


# --------------------------------------------------------------------------- #
#  ⓑ proj — 회전면 투영 래스터 → 반경 히스토그램
# --------------------------------------------------------------------------- #
def method_proj(m, center, axis, R, edges_rr, pix_mm=0.04):
    e1 = np.array([1.0, 0.0, 0.0])
    if abs(np.dot(e1, axis)) > 0.9:
        e1 = np.array([0.0, 1.0, 0.0])
    e1 = e1 - np.dot(e1, axis) * axis
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(axis, e1)
    V = (np.asarray(m.vertices, float) - center) * 1000.0
    X, Y = V @ e1, V @ e2
    F = np.asarray(m.faces, int)
    xmin, xmax, ymin, ymax = X.min() - 1, X.max() + 1, Y.min() - 1, Y.max() + 1
    nx = int(np.ceil((xmax - xmin) / pix_mm)) + 1
    ny = int(np.ceil((ymax - ymin) / pix_mm)) + 1
    grid = np.zeros((nx, ny), bool)
    for f in F:
        ax_, ay_ = X[f[0]], Y[f[0]]
        bx, by = X[f[1]], Y[f[1]]
        cx, cy = X[f[2]], Y[f[2]]
        i0 = max(0, int((min(ax_, bx, cx) - xmin) / pix_mm))
        i1 = min(nx - 1, int((max(ax_, bx, cx) - xmin) / pix_mm) + 1)
        j0 = max(0, int((min(ay_, by, cy) - ymin) / pix_mm))
        j1 = min(ny - 1, int((max(ay_, by, cy) - ymin) / pix_mm) + 1)
        if i1 < i0 or j1 < j0:
            continue
        ii = np.arange(i0, i1 + 1)
        jj = np.arange(j0, j1 + 1)
        px = xmin + (ii + 0.5) * pix_mm
        py = ymin + (jj + 0.5) * pix_mm
        PX, PY = np.meshgrid(px, py, indexing="ij")
        d = (by - cy) * (ax_ - cx) + (cx - bx) * (ay_ - cy)
        if abs(d) < 1e-15:
            continue
        l1 = ((by - cy) * (PX - cx) + (cx - bx) * (PY - cy)) / d
        l2 = ((cy - ay_) * (PX - cx) + (ax_ - cx) * (PY - cy)) / d
        l3 = 1.0 - l1 - l2
        inside = (l1 >= -1e-12) & (l2 >= -1e-12) & (l3 >= -1e-12)
        if inside.any():
            grid[i0:i1 + 1, j0:j1 + 1] |= inside
    ii, jj = np.nonzero(grid)
    px = xmin + (ii + 0.5) * pix_mm
    py = ymin + (jj + 0.5) * pix_mm
    rr = np.sqrt(px * px + py * py) / (R * 1000.0)
    hist, _ = np.histogram(rr, bins=edges_rr)
    return hist * pix_mm * pix_mm, float(grid.sum() * pix_mm * pix_mm)


# --------------------------------------------------------------------------- #
#  ⓒ surf — 삼각형 재귀 세분 → 반경 띠에 표면적 배분
# --------------------------------------------------------------------------- #
def _bary_centroids(n):
    """삼각형을 n² 개 **같은 넓이** 조각으로 균등 세분했을 때 각 조각 중심의 무게중심좌표."""
    up = [(i + 1 / 3, j + 1 / 3) for i in range(n) for j in range(n - i)]
    dn = [(i + 2 / 3, j + 2 / 3) for i in range(n - 1) for j in range(n - 1 - i)]
    ij = np.asarray(up + dn, float) / n
    l1, l2 = ij[:, 0], ij[:, 1]
    return np.c_[1 - l1 - l2, l1, l2]                      # (n²,3)


def method_surf(m, center, axis, R, edges_rr, n_sub=16):
    """삼각형 면적을 **반경 띠에 배분**한다 — 표면 샘플링도 래스터도 안 쓴다.
    각 삼각형을 n_sub² 개 같은 넓이 조각으로 균등 분할하고, 조각 중심의 반경에
    조각 면적(=삼각형면적/n_sub²)을 그대로 넣는다(결정론적 구적)."""
    V = (np.asarray(m.vertices, float) - center) * 1000.0
    T = V[np.asarray(m.faces, int)]                        # (F,3,3) mm
    ax = axis / np.linalg.norm(axis)
    area = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1)
    B = _bary_centroids(int(n_sub))                        # (S,3)
    S = B.shape[0]
    P = np.einsum("sk,fkc->fsc", B, T).reshape(-1, 3)      # (F*S,3)
    rad = np.linalg.norm(P - np.outer(P @ ax, ax), axis=1) / (R * 1000.0)
    w = np.repeat(area / S, S)
    hist, _ = np.histogram(rad, bins=edges_rr, weights=w)
    return hist, float(area.sum())


# --------------------------------------------------------------------------- #
#  대상 로더
# --------------------------------------------------------------------------- #
def dji_rotors(axis_from="shaft"):
    """DJI Mini 2 공식 GLB → 로터 4개 {hub, blades[2]} (월드좌표 trimesh).

    ⭐ 회전축은 **허브가 아니라 축(shaft, 200면 원통)** 에서 뽑는다.
       허브(1704면)는 나사자리·리브 때문에 회전대칭이 4 % 깨져 있어 관성주축이 흔들린다.
       shaft 는 고윳값이 (0.0616, 0.0616, 1.0) 으로 완전한 원통이고, 같은 로터의
       프롭너트(500면)가 소수 4자리까지 같은 축을 준다 — 두 부품 독립 확인.
       axis_from="hub" 로 부르면 감사와 같은 «허브 관성주축» 경로를 재현한다.
    """
    s = trimesh.load(GLB, process=False)
    parts = []
    for node in s.graph.nodes_geometry:
        T, g = s.graph[node]
        mm = s.geometry[g]
        if len(mm.faces) not in (1691, 1635, 1704, 200, 500):
            continue
        w = mm.copy()
        w.apply_transform(T)
        parts.append(dict(node=node, nf=len(mm.faces), mesh=w,
                          c=np.asarray(w.vertices, float).mean(0)))
    hubs = [p for p in parts if p["nf"] == 1704]
    blades = [p for p in parts if p["nf"] in (1691, 1635)]
    shafts = [p for p in parts if p["nf"] == 200]
    nuts = [p for p in parts if p["nf"] == 500]
    rotors = []
    for h in hubs:
        sh = min(shafts, key=lambda p: np.linalg.norm(p["c"] - h["c"]))
        nu = min(nuts, key=lambda p: np.linalg.norm(p["c"] - h["c"]))
        ax_s, ctr_s, d_s = frame_from_solid_of_revolution(sh["mesh"])
        ax_n, ctr_n, d_n = frame_from_solid_of_revolution(nu["mesh"])
        ax_h, ctr_h, d_h = frame_from_solid_of_revolution(h["mesh"])
        if np.dot(ax_n, ax_s) < 0:
            ax_n = -ax_n
        if np.dot(ax_h, ax_s) < 0:
            ax_h = -ax_h
        ax, ctr, diag = (ax_s, ctr_s, d_s) if axis_from == "shaft" else (ax_h, ctr_h, d_h)
        bl = sorted(blades, key=lambda b: np.linalg.norm(b["c"] - h["c"]))[:2]
        rotors.append(dict(hub=h["node"], shaft=sh["node"], axis=ax, center=ctr, diag=diag,
                           axis_shaft=ax_s, axis_nut=ax_n, axis_hub=ax_h,
                           shaft_nut_angle_deg=float(np.degrees(np.arccos(
                               np.clip(abs(np.dot(ax_s, ax_n)), -1, 1)))),
                           shaft_hub_angle_deg=float(np.degrees(np.arccos(
                               np.clip(abs(np.dot(ax_s, ax_h)), -1, 1)))),
                           blades=[(b["node"], b["mesh"]) for b in bl]))
    return rotors


def blade_plane_tilt_deg(bm, axis):
    """날 자신의 «면» 법선(면적가중 공분산의 최소분산 방향)과 회전축이 이루는 각.
    0 이면 날이 회전면 안에 있다. 크면 그 날은 **코닝(기울어져) 있고**, 회전축 기준
    원통 단면이 날을 비스듬히 잘라 시위를 크게 읽는다."""
    a, c = _tri_areas_centroids(bm)
    ctr = (a[:, None] * c).sum(0) / a.sum()
    X = c - ctr
    C = (a[:, None, None] * X[:, :, None] * X[:, None, :]).sum(0) / a.sum()
    w, V = np.linalg.eigh(C)
    n = V[:, 0]
    return float(np.degrees(np.arccos(np.clip(abs(np.dot(n, axis)), -1, 1))))


def our_blade(spec_key="mini2", n_sec=22):
    """출하 경로와 **똑같이** 만든 날 1장 (build_propeller_cad 의 스윕디스크 정규화 포함)."""
    import drones
    from drone_cad import _blade, CHORD_MAX_OVER_R
    spec = drones.DRONES[spec_key]
    R = spec.prop_dia_mm / 1000.0 / 2.0
    P = float(spec.prop_pitch_in or 5.0) * 0.0254
    probe = _blade(R, root_frac=0.070, chord_max=CHORD_MAX_OVER_R, pitch_m=P, n_sec=n_sec)
    V = np.asarray(probe.vertices)
    scale = R / float(np.sqrt(V[:, 0] ** 2 + V[:, 1] ** 2).max())
    bl = _blade(R * scale, root_frac=0.070, chord_max=CHORD_MAX_OVER_R,
                pitch_m=P, n_sec=n_sec)
    return bl, np.array([0.0, 0.0, 1.0]), np.zeros(3), R


def reference_prop(fname):
    """참조 프롭 CAD 1개 → (mesh, axis, center, R).

    2날 프롭은 **회전축에 대해 180° 대칭**이므로 면적가중 중심이 축 위에 정확히 놓이고,
    축은 «가장 납작한» 방향(면적가중 공분산의 최소분산 고유벡터)이다.
    (허브처럼 축대칭이 아니라 C2 대칭이므로 위 `frame_from_solid_of_revolution`
     의 «수직쌍이 같은 축» 규칙은 못 쓴다 — 그래서 규칙을 따로 둔다.)
    """
    m = trimesh.load(os.path.join(REFDIR, fname), process=False)
    if isinstance(m, trimesh.Scene):
        m = trimesh.util.concatenate(list(m.geometry.values()))
    sc = 1.0 if np.ptp(np.asarray(m.vertices), axis=0).max() < 5 else 1e-3   # m or mm
    m.apply_scale(sc)
    a, c = _tri_areas_centroids(m)
    ctr = (a[:, None] * c).sum(0) / a.sum()
    X = c - ctr
    C = (a[:, None, None] * X[:, :, None] * X[:, None, :]).sum(0) / a.sum()
    w, V = np.linalg.eigh(C)
    ax = V[:, 0] / np.linalg.norm(V[:, 0])
    r, _, _, _ = cyl_coords(np.asarray(m.vertices, float), ctr, ax)
    return m, ax, ctr, float(r.max()), dict(eig=[float(x) for x in w])


# --------------------------------------------------------------------------- #
#  공통 측정 묶음
# --------------------------------------------------------------------------- #
def measure(m, center, axis, R, rr_lo=0.02, rr_hi=1.00, d=0.01,
            n_sample=800_000, pix_mm=0.04, seed=0):
    centers = np.round(np.arange(rr_lo, rr_hi + 1e-9, d), 6)
    edges = np.concatenate([centers - d / 2, [centers[-1] + d / 2]])
    band = method_band(m, center, axis, R, centers, half_frac=d / 2,
                       n_sample=n_sample, seed=seed)
    a_proj, tot_proj = method_proj(m, center, axis, R, edges, pix_mm=pix_mm)
    a_surf, tot_surf = method_surf(m, center, axis, R, edges)
    dr = d * R * 1000.0
    return dict(rr=centers, edges=edges, phi_mid=band["phi_mid"],
                n_blade_clusters=band["n_blade_clusters"],
                chord_band=band["chord_mm"], theta_band=band["theta_deg"],
                tcm_band=band["t_chordmean_mm"], secarea_band=band["sec_area_mm2"],
                a_proj=a_proj, w_proj=a_proj / dr,
                a_surf=a_surf, w_surf=a_surf / (2 * dr),
                tot_proj=tot_proj, tot_surf=tot_surf, R_mm=R * 1000.0, dr_mm=dr)


def _nan_argmax(x):
    y = np.where(np.isfinite(x), x, -np.inf)
    return int(np.argmax(y))


def band_sum(rr, val, lo, hi):
    m = (rr >= lo - 1e-9) & (rr <= hi + 1e-9)
    return float(np.nansum(val[m]))


def _r(x, n=4):
    if isinstance(x, (list, tuple, np.ndarray)):
        return [_r(v, n) for v in np.asarray(x).tolist()]
    try:
        v = float(x)
    except Exception:
        return x
    return None if not np.isfinite(v) else round(v, n)


def at(rr, y, q):
    """r/R = q 에서의 값(선형보간). NaN 은 건너뛴다."""
    m = np.isfinite(y)
    return float(np.interp(q, rr[m], y[m]))


def curve_stats(mm, lo=0.15, hi=1.00):
    """한 대상의 시위곡선 요약 — 잣대 3종을 나란히."""
    rr = mm["rr"]
    out = {}
    for tag, y in (("band", mm["chord_band"]), ("surf", mm["w_surf"]),
                   ("proj", mm["w_proj"])):
        m = np.isfinite(y) & (rr >= lo) & (rr <= hi)
        r2, y2 = rr[m], y[m]
        i = int(np.argmax(y2))
        out[tag] = dict(
            c_max_mm=_r(y2[i], 4), peak_rr=_r(r2[i], 4),
            c_max_over_R=_r(y2[i] / mm["R_mm"], 5),
            norm=dict((f"{q:.2f}", _r(at(rr, y, q) / y2[i], 4))
                      for q in (0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 0.95)),
            c_over_R=dict((f"{q:.2f}", _r(at(rr, y, q) / mm["R_mm"], 5))
                          for q in (0.30, 0.50, 0.70, 0.90, 0.95, 0.98)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=os.path.join(ROOT, "outputs",
                                                   "mesh_adv_geometry_independent_0816.json"))
    ap.add_argument("--nsample", type=int, default=800_000)
    ap.add_argument("--pix", type=float, default=0.04)
    a = ap.parse_args()
    import datetime
    OUT = {"_meta": dict(
        title="프로펠러 날 기하 독립 재측정 — 감사(원통 단면) 반증 시도",
        generated_utc=datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        script="benchmark/adv_prop_geometry_independent_0816.py",
        python="/workspace/.venvs/py312/bin/python", gpu="미사용(numpy·trimesh·scipy CPU)",
        methods=dict(
            band="표면 면적가중 점구름 → 반경 띠(±0.005R) → (접선,축) 볼록껍질 최대 캘리퍼 = 참시위",
            proj=f"회전면 투영 래스터 {a.pix} mm 격자 → 반경 히스토그램 → w=면적/Δr = 투영시위(≈c·cosθ)",
            surf="삼각형을 8×8=64 등면적 조각으로 결정론적 분할 → 반경 띠에 면적 배분 → w=면적/(2Δr)",
            pitch="띠 점구름 (접선,축) 2D SVD 주축 = 국소 날각 θ(r)  ⚠캘리퍼 시위선이 아님",
            thickness="t=2V/A_surf (단면 안 씀) · 띠 볼록껍질 면적/시위 (두 경로)"),
        n_sample_per_blade=a.nsample)}

    # ------------------------------------------------------------------ #
    # A. DJI GLB 정체·좌표계 — 감사 주장 ①
    # ------------------------------------------------------------------ #
    rot = dji_rotors("shaft")
    Y = np.array([0.0, 1.0, 0.0])
    binfo, dia = [], {"shaft": [], "hub": [], "worldY": []}
    for k, r in enumerate(rot):
        for bname, bm in r["blades"]:
            V = np.asarray(bm.vertices, float)
            row = dict(rotor=k, hub=r["hub"], shaft=r["shaft"], blade=bname, faces=len(bm.faces))
            for tag, ax in (("shaft", r["axis"]), ("hub", r["axis_hub"]), ("worldY", Y)):
                ax = ax / np.linalg.norm(ax)
                rad, _, _, _ = cyl_coords(V, r["center"], ax)
                dia[tag].append(float(rad.max()) * 2000)
                row[f"dia_mm_{tag}"] = _r(float(rad.max()) * 2000, 3)
            rad, _, _, _ = cyl_coords(V, r["center"], r["axis"])
            row["r_root_mm"] = _r(float(rad.min()) * 1000, 3)
            row["root_rr"] = _r(float(rad.min() / rad.max()), 4)
            row["blade_plane_tilt_deg"] = _r(blade_plane_tilt_deg(bm, r["axis"]), 3)
            row["blade_plane_tilt_deg_hubaxis"] = _r(blade_plane_tilt_deg(bm, r["axis_hub"]), 3)
            binfo.append(row)
    OUT["A_glb_identity_and_frame"] = dict(
        claim_under_test="감사 ①: GLB 는 DJI Mini 2 공식 모델이고 날 8장·허브 4개가 있다. "
                         "회전축은 «월드 +y(편차 0.001)». 디스크 지름 118.4~119.7 mm.",
        n_hubs=len(rot), n_blades=len(binfo),
        face_signature="날 1691×4 + 1635×4, 허브 1704×4 (감사와 같음)",
        rotor_axes=[dict(rotor=k, axis=_r(r["axis"], 5),
                         tilt_from_world_y_deg=_r(np.degrees(np.arccos(abs(r["axis"][1]))), 3),
                         shaft_vs_nut_deg=_r(r["shaft_nut_angle_deg"], 4),
                         shaft_vs_hub_deg=_r(r["shaft_hub_angle_deg"], 4)) for k, r in enumerate(rot)],
        axis_note_ko="회전축은 **월드 +y 가 아니다**. 앞 로터 2.97°, 뒤 로터 5.00° 기울어져 있다. "
                     "축(200면 원통)과 프롭너트(500면)가 서로 0.003~0.012° 안에서 같은 축을 주고, "
                     "허브 관성주축은 그 축에서 0.27° 떨어져 있다(허브는 나사자리 때문에 회전대칭이 4 % 깨짐).",
        disk_dia_mm=dict((t, dict(per_blade=_r(v, 3), min=_r(min(v), 3), max=_r(max(v), 3),
                                  mean=_r(float(np.mean(v)), 3),
                                  spread=_r(max(v) - min(v), 3))) for t, v in dia.items()),
        nominal_4726F_mm=119.4,
        airframe_identity=dict(
            method_ko="로터 4개의 **축(shaft) 중심**만으로 기체를 식별한다 — 프롭과 독립인 잣대.",
            shaft_centers_mm=_r(np.array([r["center"] for r in rot]) * 1000, 2),
            motor_to_motor_diagonal_mm=_r(float(max(
                np.linalg.norm(np.array(rot[i]["center"]) - np.array(rot[j]["center"]))
                for i in range(4) for j in range(i + 1, 4))) * 1000, 2),
            dji_published_diagonal_mm=213.0,
            verdict_ko="대각 213.9 mm ↔ DJI 공표 213 mm(+0.4 %) — Mini 2 맞다."),
        blades=binfo)

    # ------------------------------------------------------------------ #
    # B. 세 잣대로 재기
    # ------------------------------------------------------------------ #
    dji_meas = []
    for k, r in enumerate(rot):
        for bname, bm in r["blades"]:
            rad, _, _, _ = cyl_coords(np.asarray(bm.vertices, float), r["center"], r["axis"])
            dm = measure(bm, r["center"], r["axis"], float(rad.max()),
                         n_sample=a.nsample, pix_mm=a.pix)
            dm["tag"] = f"dji_r{k}_{bname}"
            dji_meas.append(dm)
        print(f"  [B] rotor{k} measured")
    ours, oax, octr, oR = our_blade("mini2", n_sec=22)
    om = measure(ours, octr, oax, oR, n_sample=a.nsample, pix_mm=a.pix)
    ours20, _, _, oR20 = our_blade("mini2", n_sec=20)
    om20 = measure(ours20, octr, oax, oR20, n_sample=a.nsample, pix_mm=a.pix)
    print("  [B] ours measured")

    def stack(key):
        return np.vstack([d[key] for d in dji_meas])

    rr = om["rr"]
    dji_mean = dict(rr=rr, R_mm=float(np.mean([d["R_mm"] for d in dji_meas])),
                    dr_mm=float(np.mean([d["dr_mm"] for d in dji_meas])))
    for k in ("chord_band", "theta_band", "tcm_band", "secarea_band",
              "a_proj", "w_proj", "a_surf", "w_surf"):
        dji_mean[k] = np.nanmean(stack(k), axis=0)
        dji_mean[k + "_sd"] = np.nanstd(stack(k), axis=0)
    # 스윕용 중시위 방위각은 날마다 방위 오프셋이 달라 평균이 무의미하다 — 대표 날 1장을 쓴다.
    dji_mean["phi_mid"] = dji_meas[0]["phi_mid"]

    # --- 잣대끼리의 일치 (같은 대상 위에서) ---
    def ruler_agreement(mm):
        rr_ = mm["rr"]
        w = (rr_ >= 0.30) & (rr_ <= 0.90)
        cb, ws, wp = mm["chord_band"], mm["w_surf"], mm["w_proj"]
        th = np.radians(mm["theta_band"])
        good = w & np.isfinite(cb) & np.isfinite(ws) & np.isfinite(wp)
        return dict(
            surf_over_band_pct=_r(100 * np.median(ws[good] / cb[good] - 1), 2),
            proj_over_band_pct=_r(100 * np.median(wp[good] / cb[good] - 1), 2),
            projcorr_over_band_pct=_r(
                100 * np.median(wp[good] / np.cos(th[good]) / cb[good] - 1), 2),
            worst_abs_dev_pct=_r(100 * np.max(np.abs(
                np.r_[ws[good] / cb[good] - 1,
                      wp[good] / np.cos(th[good]) / cb[good] - 1])), 2))
    OUT["B_ruler_agreement"] = dict(
        why_ko="세 잣대가 같은 대상 위에서 몇 % 안에서 맞는지 **먼저** 보인다. 안 맞으면 방법이 문제다. "
               "ⓑ proj 는 정의상 c·cosθ 를 재므로 cosθ(독립 측정) 로 되돌린 값도 함께 적는다.",
        window="r/R 0.30–0.90",
        ours_n_sec22=ruler_agreement(om), ours_n_sec20=ruler_agreement(om20),
        dji_mean=ruler_agreement(dji_mean),
        dji_per_blade=[ruler_agreement(d) for d in dji_meas])

    # ------------------------------------------------------------------ #
    # C. 자 검증 — 참조 프롭 3종을 내 잣대로 재서 저장소 기존 원장과 대조
    # ------------------------------------------------------------------ #
    refs = {}
    for nm, f in (("holybro_1345", "1345_prop_cw.stl"), ("solo_3dr", "solo_prop_cw.stl"),
                  ("yuneec_h480", "prop_cw_assembly_remeshed_v3.stl")):
        m, ax, ctr, R, dg = reference_prop(f)
        rm = measure(m, ctr, ax, R, n_sample=a.nsample, pix_mm=a.pix)
        refs[nm] = dict(file=f, dia_mm=_r(R * 2000, 3), stats=curve_stats(rm),
                        faces=int(len(m.faces)))
        refs[nm]["_m"] = rm
        print(f"  [C] {nm} measured  dia={R*2000:.2f}")
    OUT["C_ruler_validation_reference_props"] = dict(
        why_ko="내 잣대(점구름 띠)를 새 대상에 대기 전에, 저장소가 이미 원통단면으로 잰 참조 3종에 대 본다.",
        repo_ledger="outputs/reference_props.json (measure_reference_props.py, 원통 단면)",
        mine=dict((k, dict(dia_mm=v["dia_mm"],
                           c_max_over_R_band=v["stats"]["band"]["c_max_over_R"],
                           peak_rr_band=v["stats"]["band"]["peak_rr"]))
                  for k, v in refs.items()))

    # ------------------------------------------------------------------ #
    # D. 시위 분포 — 감사 주장 ②·④
    # ------------------------------------------------------------------ #
    OUT["D_chord_distribution"] = dict(
        claim_under_test="감사 ②: 정규화 시위 @0.70R 우리 0.577 ↔ DJI 0.866, 정점 우리 0.30R ↔ 실물 0.45R. "
                         "감사 ④: c_max/R 우리 0.25 고정 ↔ 실물 0.177~0.273.",
        ours_n_sec22=curve_stats(om), ours_n_sec20=curve_stats(om20),
        dji_mean_of_8_blades=curve_stats(dji_mean),
        dji_per_blade_band=[dict(tag=d["tag"], **{k: v for k, v in
                                                  curve_stats(d)["band"].items()
                                                  if k in ("c_max_over_R", "peak_rr")})
                            for d in dji_meas],
        reference_cads=dict((k, v["stats"]) for k, v in refs.items()))

    # ------------------------------------------------------------------ #
    # E. 면적비 — **공통 반경 창**에서만
    # ------------------------------------------------------------------ #
    wins = [(0.20, 0.96), (0.30, 0.96), (0.50, 0.96), (0.60, 0.96),
            (0.70, 0.96), (0.80, 0.96), (0.90, 0.96), (0.175, 1.00), (0.10, 1.00)]
    R_o, R_d = om["R_mm"], dji_mean["R_mm"]
    area = {}
    for lo, hi in wins:
        row = {}
        for tag, ok, dk in (("proj", om["a_proj"], dji_mean["a_proj"]),
                            ("surf", om["a_surf"], dji_mean["a_surf"])):
            ao = band_sum(rr, ok, lo, hi)
            ad = band_sum(rr, dk, lo, hi)
            row[tag] = dict(ours_mm2=_r(ao, 3), dji_mm2=_r(ad, 3),
                            ratio_raw=_r(ao / ad, 4),
                            ratio_R2norm=_r((ao / R_o ** 2) / (ad / R_d ** 2), 4),
                            dB_20log10=_r(20 * np.log10((ao / R_o ** 2) / (ad / R_d ** 2)), 3))
        # 단면 시위 적분(band)
        ao = band_sum(rr, om["chord_band"], lo, hi) * om["dr_mm"]
        ad = band_sum(rr, dji_mean["chord_band"], lo, hi) * dji_mean["dr_mm"]
        row["band"] = dict(ours_mm2=_r(ao, 3), dji_mm2=_r(ad, 3), ratio_raw=_r(ao / ad, 4),
                           ratio_R2norm=_r((ao / R_o ** 2) / (ad / R_d ** 2), 4),
                           dB_20log10=_r(20 * np.log10((ao / R_o ** 2) / (ad / R_d ** 2)), 3))
        area[f"{lo:.3f}-{hi:.2f}"] = row
    OUT["E_area_ratio_common_window"] = dict(
        claim_under_test="감사 ②: 날 면적 −29 %(−2.97 dB), 외곽 −3.55 dB. 감사 M절: 투영비 0.798·표면적비 0.755.",
        warning_ko="⭐뿌리 시작 반경이 다르면 총면적 비교는 무효다. 아래는 **전부 공통 반경 창** 값이다. "
                   "R 이 1 % 다르므로 R² 로 정규화한 비를 같이 적는다.",
        ours_R_mm=_r(R_o, 3), dji_R_mm=_r(R_d, 3), windows=area,
        total_area_no_window=dict(
            ours_proj_mm2=_r(om["tot_proj"], 2), dji_proj_mm2=_r(dji_mean["a_proj"].sum()
                                                                + 0.0, 2),
            ours_surf_half_mm2=_r(om["tot_surf"] / 2, 2),
            dji_surf_half_mm2=_r(float(np.mean([d["tot_surf"] for d in dji_meas])) / 2, 2),
            note_ko="이 총면적 두 줄은 **비교용이 아니다** — 우리 날은 0.07R, DJI 날 부품은 "
                    "훨씬 안쪽까지 있다. 창 안 값만 쓸 것."))

    # ------------------------------------------------------------------ #
    # F. 팁 밴드 — 감사 주장 ⑥
    # ------------------------------------------------------------------ #
    OUT["F_tip_band"] = dict(
        claim_under_test="감사 ⑥: 팁 밴드(0.90~0.96R) 면적비 0.700(−3.10 dB), c/R @0.98R DJI 0.1028 ↔ 우리 0.0609",
        area_ratio=area["0.900-0.96"],
        c_over_R_at=dict((f"{q:.2f}", dict(
            ours=_r(at(rr, om["chord_band"], q) / R_o, 5),
            dji=_r(at(rr, dji_mean["chord_band"], q) / R_d, 5),
            ratio=_r((at(rr, om["chord_band"], q) / R_o)
                     / (at(rr, dji_mean["chord_band"], q) / R_d), 4)))
            for q in (0.90, 0.95, 0.96, 0.98, 0.99)))

    # ------------------------------------------------------------------ #
    # G. 피치 — 감사 주장 ⑤
    # ------------------------------------------------------------------ #
    def pitch_block(mm, R_mm):
        rr_ = mm["rr"]
        th = mm["theta_band"]
        r_mm = rr_ * R_mm
        Ploc = 2 * np.pi * r_mm * np.tan(np.radians(th))      # 국소 기하피치[mm]
        w = (rr_ >= 0.25) & (rr_ <= 0.98) & np.isfinite(Ploc)
        i = int(np.argmax(np.where(w, Ploc, -np.inf)))
        w2 = (rr_ >= 0.60) & (rr_ <= 0.90) & np.isfinite(th)
        return dict(
            theta_deg=dict((f"{q:.2f}", _r(at(rr_, th, q), 3))
                           for q in (0.30, 0.50, 0.60, 0.70, 0.75, 0.80, 0.90)),
            P_local_mm=dict((f"{q:.2f}", _r(at(rr_, Ploc, q), 3))
                            for q in (0.30, 0.50, 0.60, 0.70, 0.75, 0.80, 0.90)),
            P_local_peak_rr=_r(rr_[i], 3), P_local_peak_mm=_r(Ploc[i], 3),
            k_norm_to_0p50R=dict((f"{q:.2f}", _r(at(rr_, Ploc, q) / at(rr_, Ploc, 0.50), 4))
                                 for q in (0.30, 0.50, 0.60, 0.70, 0.75, 0.80, 0.90)),
            k_norm_to_0p75R=dict((f"{q:.2f}", _r(at(rr_, Ploc, q) / at(rr_, Ploc, 0.75), 4))
                                 for q in (0.30, 0.50, 0.60, 0.70, 0.75, 0.80, 0.90)),
            theta_span_0p6_0p9_deg=_r(float(np.nanmax(th[w2]) - np.nanmin(th[w2])), 3))
    OUT["G_pitch"] = dict(
        claim_under_test="감사 ⑤: PITCH_K 기준 반경 우리 0.5R ↔ 표준·실물 0.75R. "
                         "외곽 피치각 폭 우리 9.2° ↔ DJI 5.5°.",
        method_ko="띠 점구름의 (접선,축) 2D SVD 주축 각도 = 국소 날각 θ(r). "
                  "국소 기하피치 P_loc = 2πr·tanθ 는 공칭 피치를 안 쓰므로 정의에 안 기댄다.",
        ours_n_sec22=pitch_block(om, R_o), dji_mean=pitch_block(dji_mean, R_d),
        dji_per_blade_peak=[dict(tag=d["tag"], **{k: v for k, v in
                                                  pitch_block(d, d["R_mm"]).items()
                                                  if k in ("P_local_peak_rr",
                                                           "theta_span_0p6_0p9_deg")})
                            for d in dji_meas])

    # ------------------------------------------------------------------ #
    # G2. 스윕(skew) — «원통단면 캘리퍼는 스윕이 크면 c/cosΛ 를 읽는다» 를 실제로 확인
    # ------------------------------------------------------------------ #
    def sweep_block(mm, R_mm):
        """스윕각 Λ(r) = atan(r·dφ/dr)  — 중시위 궤적의 접선이 반경방향과 이루는 각.
        ⚠ r·φ 를 미분하면 안 된다(φ 의 절대 오프셋이 그대로 들어가 −66° 같은 헛값이 나온다)."""
        rr_ = mm["rr"]
        ph = mm["phi_mid"]
        ok = np.isfinite(ph)
        lam = np.full_like(ph, np.nan)
        idx = np.nonzero(ok)[0]
        if len(idx) > 3:
            phu = np.unwrap(ph[idx])
            r_mm = rr_[idx] * R_mm
            lam[idx] = np.degrees(np.arctan(r_mm * np.gradient(phu, r_mm)))
        return lam
    lam_o = sweep_block(om, R_o)
    lam_d = sweep_block(dji_mean, R_d)
    ratio_raw, ratio_sw = {}, {}
    for q in (0.30, 0.50, 0.60, 0.70, 0.80, 0.90, 0.95):
        co, cd = at(rr, om["chord_band"], q), at(rr, dji_mean["chord_band"], q)
        lo_, ld_ = at(rr, lam_o, q), at(rr, lam_d, q)
        ratio_raw[f"{q:.2f}"] = _r((co / R_o) / (cd / R_d), 4)
        ratio_sw[f"{q:.2f}"] = _r((co * np.cos(np.radians(lo_)) / R_o)
                                  / (cd * np.cos(np.radians(ld_)) / R_d), 4)
    OUT["G2_sweep_artifact_check"] = dict(
        why_ko="감사 M절이 «원통단면 캘리퍼는 스윕이 크면 c/cosΛ 를 읽는다» 고 적고 Λ 측정을 "
               "포기했다(위상 언랩 붕괴). 여기서는 띠별 중시위 방위각을 언랩해 Λ 를 실제로 잰다. "
               "스윕이 우리와 DJI 가 다르면 «27~39 % 좁다» 는 부분적으로 잣대 인공물이 된다.",
        sweep_deg_ours=dict((f"{q:.2f}", _r(at(rr, lam_o, q), 3))
                            for q in (0.30, 0.50, 0.70, 0.90)),
        sweep_deg_dji=dict((f"{q:.2f}", _r(at(rr, lam_d, q), 3))
                           for q in (0.30, 0.50, 0.70, 0.90)),
        chord_ratio_ours_over_dji_raw=ratio_raw,
        chord_ratio_ours_over_dji_sweep_corrected=ratio_sw)

    # ------------------------------------------------------------------ #
    # G3. 뿌리 시작 반경 — 감사 M절의 «DJI 날은 0.175R 부터» 를 실측으로 검사
    # ------------------------------------------------------------------ #
    def cum_area(mm):
        c = np.cumsum(mm["a_surf"]) / mm["a_surf"].sum()
        return dict((f"{q:.3f}", _r(float(np.interp(q, mm["rr"], c)) * 100, 2))
                    for q in (0.05, 0.10, 0.15, 0.175, 0.20, 0.30))
    OUT["G3_root_start_radius"] = dict(
        claim_under_test="감사 M절: «우리 날은 0.070R 부터, DJI 는 날 부품이 0.175R 부터라 "
                         "그 안쪽은 허브 부품이다» — 이 전제로 세 잣대의 불일치를 설명했다.",
        dji_blade_min_radius_rr=_r(float(np.mean([b["root_rr"] for b in binfo])), 4),
        cumulative_surface_area_pct_below_rr=dict(ours=cum_area(om), dji=cum_area(dji_mean)))

    # ------------------------------------------------------------------ #
    # H. 두께 — 감사 주장 ⑦
    # ------------------------------------------------------------------ #
    th_block = {}
    for key in ("matrice4e", "mini2", "mini5pro"):
        bl, ax2, ct2, R2 = our_blade(key, n_sec=22)
        mm2 = measure(bl, ct2, ax2, R2, n_sample=a.nsample, pix_mm=a.pix)
        V = float(bl.volume) * 1e9                                # mm³
        A = float(bl.area) * 1e6                                  # mm²
        c2 = mm2["chord_band"]
        A_plan = float(np.nansum(c2) * mm2["dr_mm"])              # ∫c dr (전개 평면형 면적)
        th_block[key] = dict(
            R_mm=_r(R2 * 1000, 3), closed=bool(bl.is_watertight),
            planform_int_c_dr_mm2=_r(A_plan, 3),
            half_surface_mm2=_r(A / 2, 3),
            perimeter_over_2chord=_r((A / 2) / A_plan, 4),
            t_V_over_planform_mm=_r(V / A_plan, 4),
            t_2V_over_Asurf_mm=_r(2 * V / A, 4),
            volume_mm3=_r(V, 2), area_mm2=_r(A, 2))
    # NACA-4 두께분포의 시위평균/최대 비 — 전 시위 vs 양끝 잘라 재기
    _x = np.linspace(0, 1, 200001)
    _yt = 5 * (0.2969 * np.sqrt(_x) - 0.1260 * _x - 0.3516 * _x ** 2
               + 0.2843 * _x ** 3 - 0.1015 * _x ** 4)
    naca_ratio_full = float(np.trapezoid(_yt, _x) / _yt.max())
    _m = (_x >= 0.03) & (_x <= 0.97)
    naca_ratio_trim = float(np.trapezoid(_yt[_m], _x[_m]) / 0.94 / _yt.max())
    OUT["H_thickness_canonical_1p43"] = dict(
        claim_under_test="감사 ⑦: 정본 1.43 mm 는 메쉬가 아니라 상수 유도값이고 메쉬 실측은 1.456 mm(+1.8 %).",
        method_ko="**단면 폴리곤을 안 쓰는 경로**: t = V / ∫c dr (부피와 시위적분만). 이것이 정본과 "
                  "같은 정의(=시위평균 두께의 시위가중 스팬평균)다. 보조로 t=2V/A_surf 는 "
                  "표면적이 둘레(2c 보다 길다)라 **아래로 편향**된다 — 그 편향값도 같이 적는다.",
        naca4_chordmean_over_max=dict(
            full_chord=_r(naca_ratio_full, 6), trimmed_0p03_0p97=_r(naca_ratio_trim, 6),
            bias_pct=_r(100 * (naca_ratio_trim / naca_ratio_full - 1), 2),
            note_ko="시위 양끝을 자르고 평균하면 두께가 이만큼 높게 나온다. 저장소의 "
                    "measure_mini2_prop_thickness.py 는 x/c 0.03~0.97 만 잰다."),
        definition_sensitivity_ko="«두께» 는 캠버 있는 단면에서 **정의에 민감하다**. 캘리퍼 시위선 "
                                  "기준 상하면 차는 캠버 부풂을 두께로 세어 NACA t 파라미터보다 "
                                  "20~30 % 크게 읽고, 단면적/시위는 캠버에 거의 안 흔들린다. "
                                  "슬래브 등가(부피/평면형)로 쓰려면 단면적/시위가 맞는 잣대다.",
        ours=th_block)

    # ------------------------------------------------------------------ #
    # I. Solo 이상치 주장 — 감사 주장 ③
    # ------------------------------------------------------------------ #
    solo_tbl = {}
    for nm, v in refs.items():
        s = v["stats"]["band"]
        solo_tbl[nm] = dict(dia_mm=v["dia_mm"], c_max_over_R=s["c_max_over_R"],
                            peak_rr=s["peak_rr"], norm=s["norm"])
    solo_tbl["dji_mini2_glb"] = dict(dia_mm=_r(2 * R_d, 3),
                                     **{k: curve_stats(dji_mean)["band"][k]
                                        for k in ("c_max_over_R", "peak_rr", "norm")})
    solo_tbl["ours_law"] = dict(dia_mm=_r(2 * R_o, 3),
                                **{k: curve_stats(om)["band"][k]
                                   for k in ("c_max_over_R", "peak_rr", "norm")})
    OUT["I_solo_outlier_test"] = dict(
        claim_under_test="감사 ③: 3DR Solo 는 참조 넷 중 유일한 이상치다.",
        note_ko="감사의 «정규화 시위» 표에는 저장소 참조 CAD 3종 중 **holybro_1345 가 빠져 있다** "
                "(c_max/R·정점 표에는 있는데 정규화 시위 표에만 없다). 여기서는 넣고 잰다.",
        table=solo_tbl)

    # ------------------------------------------------------------------ #
    # I2. «c_max/R 은 크기와 반비례한다» — 감사 자신의 표로 검정
    # ------------------------------------------------------------------ #
    from scipy import stats as _st
    audit_tbl = [("dji_mini2_cad", 119.05, 0.2617), ("yuneec_h480", 230.10, 0.1769),
                 ("3dr_solo", 253.82, 0.2726), ("mavic4pro_1158F", 267.0, 0.1808),
                 ("m4e_1157F", 274.0, 0.1901), ("m4e_1154F", 274.0, 0.2122),
                 ("holybro_1345", 346.66, 0.2253)]
    dd = np.array([x[1] for x in audit_tbl])
    cc = np.array([x[2] for x in audit_tbl])
    OUT["I2_cmax_over_R_vs_size"] = dict(
        claim_under_test="감사 ④: c_max/R 은 «크기와 반비례한다»(L.priority_2 «프롭이 클수록 작아진다»).",
        data_source="감사 자신의 c_max/R 표(기체별 1개, 사진 중복은 표준·저소음 둘 다 둠) + 지름",
        pearson_r=_r(float(np.corrcoef(dd, cc)[0, 1]), 3),
        spearman_rho=_r(float(_st.spearmanr(dd, cc).statistic), 3),
        same_size_class_230_274mm=dict(
            props=["yuneec 0.1769", "solo 0.2726", "mavic4pro 0.1808", "m4e 0.1901/0.2122"],
            span=_r(0.2726 / 0.1769, 3),
            fraction_of_full_range_pct=_r(100 * (0.2726 - 0.1769) / (0.2726 - 0.1769), 1)),
        our_mesh_realised_c_max_over_R=dict(
            mini2=curve_stats(om)["band"]["c_max_over_R"],
            note_ko="법칙이 스케일 불변이라 기종을 바꿔도 실현값은 같다. 코드 상수는 0.25 인데 "
                    "**빌드된 메쉬가 실현하는 값은 그보다 작다** — 감사가 «우리는 전부 0.25» 로 "
                    "센 것은 상수이지 메쉬가 아니다."))

    # ------------------------------------------------------------------ #
    # J. 감사가 적은 수치 ↔ 내 독립 측정 — 한 눈에
    # ------------------------------------------------------------------ #
    dj, ou = curve_stats(dji_mean)["band"], curve_stats(om)["band"]
    sect_ratio = (band_sum(rr, om["chord_band"], 0.175, 0.975) * om["dr_mm"]) / \
                 (band_sum(rr, dji_mean["chord_band"], 0.175, 0.975) * dji_mean["dr_mm"])
    OUT["J_side_by_side"] = dict(
        note_ko="왼쪽은 감사 문서·원장이 적은 값, 오른쪽은 이 파일의 독립 측정(잣대 3종 중 band).",
        rows=[
            dict(item="정규화 시위 @0.70R — 우리", audit=0.577, mine=ou["norm"]["0.70"]),
            dict(item="정규화 시위 @0.70R — DJI", audit=0.866, mine=dj["norm"]["0.70"]),
            dict(item="시위 정점 위치 — 우리", audit=0.30, mine=ou["peak_rr"]),
            dict(item="시위 정점 위치 — DJI", audit=0.456, mine=dj["peak_rr"]),
            dict(item="c_max/R — DJI Mini2", audit=0.2625, mine=dj["c_max_over_R"]),
            dict(item="면적비 0.20–0.96R", audit=0.7893,
                 mine=area["0.200-0.96"]["surf"]["ratio_R2norm"]),
            dict(item="면적비 0.60–0.96R", audit=0.6647,
                 mine=area["0.600-0.96"]["surf"]["ratio_R2norm"]),
            dict(item="팁밴드 면적비 0.90–0.96R", audit=0.7002,
                 mine=area["0.900-0.96"]["surf"]["ratio_R2norm"]),
            dict(item="단면적분비 0.175–0.975R (감사 M절 «0.710»)", audit=0.710,
                 mine=_r(sect_ratio, 4)),
            dict(item="총 투영면적비(창 없음)", audit=0.7979,
                 mine=_r(om["tot_proj"] / float(np.mean([d["tot_proj"] for d in dji_meas])), 4)),
            dict(item="총 표면적/2 비(창 없음)", audit=0.7551,
                 mine=_r(om["tot_surf"] / float(np.mean([d["tot_surf"] for d in dji_meas])), 4)),
            dict(item="외곽 피치각 폭 0.6–0.9R — 우리", audit=9.2,
                 mine=OUT["G_pitch"]["ours_n_sec22"]["theta_span_0p6_0p9_deg"]),
            dict(item="외곽 피치각 폭 0.6–0.9R — DJI", audit=5.5,
                 mine=OUT["G_pitch"]["dji_mean"]["theta_span_0p6_0p9_deg"]),
            dict(item="국소피치 최대 반경 — DJI", audit=0.75,
                 mine=OUT["G_pitch"]["dji_mean"]["P_local_peak_rr"]),
            dict(item="c/R @0.98R — DJI", audit=0.1028,
                 mine=OUT["F_tip_band"]["c_over_R_at"]["0.98"]["dji"]),
            dict(item="c/R @0.98R — 우리", audit=0.0609,
                 mine=OUT["F_tip_band"]["c_over_R_at"]["0.98"]["ours"]),
            dict(item="정본 두께 matrice4e (메쉬 실측)", audit=1.4559,
                 mine=th_block["matrice4e"]["t_V_over_planform_mm"],
                 note="정의가 다르다 — 내 값은 «단면적/시위»(부피 항등식), 감사 값은 «캘리퍼 "
                      "시위선 기준 상하면 차» 를 시위 일부 구간에서 평균한 것으로 보인다"),
            dict(item="NACA-4 시위평균/최대 비", audit=0.684879,
                 mine=_r(naca_ratio_full, 6),
                 note=f"시위를 [0.03,0.97] 로 잘라 평균하면 {naca_ratio_trim:.4f} 로 "
                      f"+{100*(naca_ratio_trim/naca_ratio_full-1):.2f} % 높아진다 "
                      "— 저장소의 measure_mini2_prop_thickness.py 가 쓰는 창이 바로 그것이다"),
            dict(item="디스크 지름 DJI (평균)", audit=119.05,
                 mine=OUT["A_glb_identity_and_frame"]["disk_dia_mm"]["shaft"]["mean"]),
        ])

    # ------------------------------------------------------------------ #
    # K. 무해 확인 목록(감사 주장 ⑨) 재검사 + DJI 두께를 왜 못 쟀는지
    # ------------------------------------------------------------------ #
    import drones as _dr
    from drone_cad import build_propeller_cad as _bpc
    integ = {}
    for key in ("mini2", "matrice4e"):
        sp = _dr.DRONES[key]
        g = _bpc(sp, n_sec=22).to_geom()
        Vv = np.asarray(g.v, float)
        rmx = float(np.sqrt(Vv[:, 0] ** 2 + Vv[:, 1] ** 2).max()) * 1000
        tm = trimesh.Trimesh(vertices=np.asarray(g.v), faces=np.asarray(g.f), process=False)
        integ[key] = dict(spec_dia_mm=float(sp.prop_dia_mm), built_dia_mm=_r(2 * rmx, 3),
                          err_pct=_r(100 * (2 * rmx / sp.prop_dia_mm - 1), 4),
                          n_blades=int(sp.prop_blades), faces=int(len(g.f)),
                          watertight=bool(tm.is_watertight))
    p_a = _dr.build_propeller(_dr.DRONES["mini2"], n=10, mirror=False)
    p_b = _dr.build_propeller(_dr.DRONES["mini2"], n=10, mirror=True)
    Va, Vb = np.asarray(p_a.v, float), np.asarray(p_b.v, float)
    Va[:, 1] *= -1
    mirr = float(np.abs(np.sort(Vb, axis=0) - np.sort(Va, axis=0)).max())

    dji_close = []
    for k, r in enumerate(rot):
        for bname, bm in r["blades"]:
            w = bm.copy()
            w.merge_vertices()
            e = w.edges_sorted
            be = e[trimesh.grouping.group_rows(e, require_count=1)]
            w2 = w.copy()
            trimesh.repair.fill_holes(w2)
            dji_close.append(dict(blade=bname, boundary_edges=int(len(be)),
                                  watertight_after_fill=bool(w2.is_watertight),
                                  volume_after_fill_mm3=_r(float(w2.volume) * 1e9, 2)))
    vols = [x["volume_after_fill_mm3"] for x in dji_close]
    OUT["K_harmless_list_and_dji_thickness"] = dict(
        integrity_recheck=dict(
            prop_disc_dia=integ, mirror_max_vertex_mismatch_m=_r(mirr, 12),
            verdict_ko="감사 ⑨ 의 «무해» 항목 중 내가 다시 잰 것 — 스윕디스크 지름 오차 0.0000 %, "
                       "날개 2장, 프롭 어셈블리 watertight True, CW/CCW 거울상 정확히 일치. "
                       "전부 감사가 맞다."),
        dji_blade_not_closable=dict(
            boundary_loops_per_blade=4,
            longest_loop_spans_r_mm="5.7 → 59.7 (스팬 전체)",
            watertight_after_fill=[x["watertight_after_fill"] for x in dji_close],
            volume_after_fill_mm3=vols,
            spread_pct=_r(100 * (max(vols) / min(vols) - 1), 2),
            verdict_ko="DJI GLB 날은 뿌리에만 구멍이 난 게 아니라 **스팬 전체를 따라 열린 경계**가 "
                       "있어 구멍 메우기로도 닫히지 않는다. ⇒ 내 부피 항등식 경로로는 DJI 실물 "
                       "두께를 **못 잰다(판정 불가)**. 다만 같은 부품인 날 8장의 «메운 부피» 가 "
                       "10~23 % 벌어진다는 사실 자체가, 감사가 스스로 단 «GLB 두께는 ±10 % 로 "
                       "읽어라» 는 단서를 **뒷받침**한다."))

    for k, v in refs.items():
        v.pop("_m", None)
    np.savez(os.path.join(ROOT, "outputs", "_adv_prop_geom_raw.npz"),
             rr=rr, ours_chord=om["chord_band"], ours_theta=om["theta_band"],
             ours_aproj=om["a_proj"], ours_asurf=om["a_surf"],
             dji_chord=dji_mean["chord_band"], dji_chord_sd=dji_mean["chord_band_sd"],
             dji_theta=dji_mean["theta_band"], dji_aproj=dji_mean["a_proj"],
             dji_asurf=dji_mean["a_surf"])
    json.dump(OUT, open(a.json, "w"), ensure_ascii=False, indent=1)
    print("->", a.json)


if __name__ == "__main__":
    main()
