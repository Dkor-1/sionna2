#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""⭐ 나머지 6종 프로펠러 정밀 계측 — s1000plus · phantom4 · phantom3 · typhoonh480 · x500v2 · m350rtk
================================================================================================
2026-08-16.  «기종마다 그 기체의 진짜 프롭» 라운드의 **계측 담당** 산출물.

**무엇을 재는가**
  프로펠러 날 하나의 **평면형(planform)** — 반경 r 에서의 시위(chord, 날의 폭) c(r) — 과,
  3D 기하가 있는 경우에는 **두께비 t/c** 와 **비틀림(twist)** 까지.

⭐ **규약 선언 — 이게 다르면 비교가 무의미하다** (파일 머리에 박아 둔다)
--------------------------------------------------------------------------------
① **R 의 정의** = 디스크 반경 = «회전축 → 날개 끝(tip)» 거리.
   - 3D/펼친 사진: 데이터에서 직접 잰다(`R_measured`).
   - **접힌 날 사진**: 접이식 프롭은 힌지(경첩) 볼트를 축으로 날이 **같은 평면 안에서** 돈다.
     따라서 평면형 자체는 접혀도 안 변하고, 반경 매핑만 바뀐다.
     힌지 오프셋 e(회전축→힌지)와 날 길이 L(힌지→팁)을 재서 **R = e + L** 로 복원한다.
     ⚠ 이 복원은 «펼치면 날 축이 회전축을 지난다» 는 가정 위에 선다(접이식 프롭의 정의).
   - 공칭 R(제원 지름/2)은 **항상 병기**하되 절대 몰래 대입하지 않는다.

② **날 뿌리 시작점** = 시위 곡선은 `r/R ≥ hub_guard` 에서만 유효하다고 선언한다.
   허브/클램프/브래킷은 날이 아니다. 기본 hub_guard 는 원장에 기종마다 적는다.
   추가로 `coverage(r)`(그 반경 고리에서 실루엣이 차지하는 비율)을 같이 내보내
   «여기부터는 허브다» 를 독자가 직접 볼 수 있게 한다.

③ **시위 두 정의를 섞지 마라.**
   - `c_arc` (**투영 시위**) = 회전면에 투영한 날 폭 = r·Δθ.  **사진이 재는 건 이것**이다.
   - `c_cal` (**진짜 시위**) = 원통 단면을 펼친 (r·θ, z) 평면에서의 최대 캘리퍼.
     비틀린 날은 축방향으로도 뻗어 있어 c_cal ≥ c_arc 다. **3D 기하만 낼 수 있다.**
   - `projection_factor` = c_arc / c_cal ≈ cos(국소 피치각). 원장에 같이 낸다.
   ⇒ **사진 값을 메쉬의 c_cal 과 나란히 놓지 마라.** 사진 ↔ c_arc 가 사과-대-사과다.

④ **두 방법으로 재서 일치도를 보고한다**(사용자 규약).
   - 메쉬:  M1 점구름 각폭  vs  M2 래스터 실루엣(전혀 다른 구현 경로).
   - 사진:  M1 중심기준 각폭(저장소 관례)  vs  M2 날-국소 좌표계 수직폭(중심 추정에 면역).

⛔ GPU 미사용 · ⛔ 저장소 코드 무변경(이 파일은 **새로 추가**) · ⛔ git 무접촉.
실행: cd /workspace/sionna && PYTHONPATH=src:benchmark /workspace/.venvs/py312/bin/python \
        benchmark/prop_measure_others_0816.py
산출: outputs/prop_measure_others_0816.json
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import zipfile
from pathlib import Path

import numpy as np

ROOT = Path("/workspace/sionna")
REF = ROOT / "assets/meshes/reference"
RS = ROOT / "assets/meshes/reference_study"
PHOTO = ROOT / "assets/photos"
DRONES_MESH = ROOT / "assets/meshes/drones"
OUT = ROOT / "outputs/prop_measure_others_0816.json"
UIUC_ZIP = Path(os.environ.get("UIUC_ZIP", "/data/public/sionna/uiuc_propdb/UIUC-propDB.zip"))

# 비교 격자 — 저장소 관례(adv_multiref_planform_0816.GRID)와 **같은 격자**를 쓴다.
GRID = np.round(np.arange(0.20, 0.9601, 0.05), 3)
GRID_KEYS = [f"{g:.2f}" for g in GRID]


# ================================================================= #
#  0. 공용 소도구
# ================================================================= #
def _arcs(theta, gap_deg=12.0):
    """원형 각도 표본 → 연속 구간(원호) 목록 [(lo, hi), ...]."""
    if len(theta) == 0:
        return []
    t = np.sort(np.mod(theta, 2 * np.pi))
    gap = np.radians(gap_deg)
    d = np.diff(np.r_[t, t[0] + 2 * np.pi])
    br = np.where(d > gap)[0]
    if len(br) == 0:
        return [(t[0], t[-1])]
    out = []
    for k in range(len(br)):
        i0 = (br[k] + 1) % len(t)
        i1 = br[(k + 1) % len(br)]
        lo = t[i0]
        hi = t[i1] if i1 >= i0 else t[i1] + 2 * np.pi
        out.append((lo, hi))
    return out


def _caliper(P):
    """평면 점집합의 최대 캘리퍼(가장 먼 두 점 거리) — 볼록껍질 위에서."""
    if len(P) < 3:
        return float(np.linalg.norm(P[0] - P[-1])) if len(P) == 2 else 0.0
    try:
        from scipy.spatial import ConvexHull
        Q = P[ConvexHull(P).vertices]
    except Exception:
        Q = P
    D = Q[:, None, :] - Q[None, :, :]
    return float(np.sqrt((D ** 2).sum(-1)).max())


def _profile_summary(rr, c, R, hub_guard=0.20, r_hi=0.96):
    """시위 곡선 → 표준 요약(저장소 adv_multiref.summarize 와 같은 지표 이름)."""
    ok = np.isfinite(c) & (rr >= hub_guard) & (rr <= r_hi)
    if ok.sum() < 8:
        return None
    x, y = rr[ok], c[ok]
    cmax = float(y.max())
    yn = y / cmax
    inside = lambda g: x[0] <= g <= x[-1]
    return dict(
        c_max_over_R=cmax / R,
        peak_r_over_R=float(x[int(np.argmax(y))]),
        cn={k: (float(np.interp(g, x, yn)) if inside(g) else None)
            for g, k in zip(GRID, GRID_KEYS)},
        c_over_R={k: (float(np.interp(g, x, y)) / R if inside(g) else None)
                  for g, k in zip(GRID, GRID_KEYS)},
        blade_area_over_R2=float(np.trapezoid(y / R, x)),      # ∫(c/R) d(r/R)
        area_centroid=float(np.trapezoid(y * x, x) / np.trapezoid(y, x)),
        outboard_share_0p6=float(np.trapezoid(y[x >= 0.6], x[x >= 0.6])
                                 / np.trapezoid(y, x)),
        tip_cn_at_0p95=float(np.interp(0.95, x, yn)) if inside(0.95) else None,
        r_range=[float(x[0]), float(x[-1])],
        n_valid=int(ok.sum()),
    )


def _agree(a, b):
    """두 요약의 일치도 — c_max/R 상대차 + cn 격자 RMS 차."""
    if a is None or b is None:
        return None
    out = dict(c_max_over_R_rel_pct=100.0 * (b["c_max_over_R"] - a["c_max_over_R"])
               / a["c_max_over_R"],
               peak_r_diff=b["peak_r_over_R"] - a["peak_r_over_R"])
    d = [b["cn"][k] - a["cn"][k] for k in GRID_KEYS
         if a["cn"].get(k) is not None and b["cn"].get(k) is not None]
    out["cn_rms_diff"] = float(np.sqrt(np.mean(np.square(d)))) if d else None
    out["cn_max_abs_diff"] = float(np.max(np.abs(d))) if d else None
    out["blade_area_rel_pct"] = (100.0 * (b["blade_area_over_R2"] - a["blade_area_over_R2"])
                                 / a["blade_area_over_R2"])
    return out


# ================================================================= #
#  1. 메쉬 → 평면형 (M1 점구름 각폭 · M2 래스터 실루엣)
# ================================================================= #
def _load_dae(path):
    """최소 COLLADA 판독기 — `pycollada` 가 없는 환경용.

    이 저장소의 시뮬 CAD(.dae)는 전부 «geometry 1개 + node 의 4x4 matrix» 라는 단순 형태다.
    POSITION float_array 와 triangles 의 p 배열만 읽고 node matrix 를 적용한다.
    ⚠ 여러 지오메트리를 인스턴스로 재사용하는 복잡한 DAE 는 지원하지 않는다(그런 파일은 안 쓴다)."""
    import xml.etree.ElementTree as ET
    import trimesh
    root = ET.parse(str(path)).getroot()
    ns = root.tag.split("}")[0].strip("{")
    q = lambda t: f"{{{ns}}}{t}"
    geoms = {}
    for g in root.iter(q("geometry")):
        mesh = g.find(q("mesh"))
        if mesh is None:
            continue
        src = {}
        for s in mesh.findall(q("source")):
            fa = s.find(q("float_array"))
            if fa is not None:
                src[s.get("id")] = np.fromstring(fa.text, sep=" ")
        vid, vsrc = None, None
        v = mesh.find(q("vertices"))
        if v is not None:
            vid = v.get("id")
            for i in v.findall(q("input")):
                if i.get("semantic") == "POSITION":
                    vsrc = i.get("source").lstrip("#")
        pos = src.get(vsrc)
        if pos is None:
            continue
        V = pos.reshape(-1, 3)
        F = []
        for prim in list(mesh.findall(q("triangles"))) + list(mesh.findall(q("polylist"))):
            ins = prim.findall(q("input"))
            stride = max(int(i.get("offset", 0)) for i in ins) + 1
            voff = next(int(i.get("offset", 0)) for i in ins
                        if i.get("semantic") == "VERTEX")
            p = np.fromstring(prim.find(q("p")).text, sep=" ", dtype=float).astype(int)
            idx = p.reshape(-1, stride)[:, voff]
            if prim.tag.endswith("polylist"):
                vc = np.fromstring(prim.find(q("vcount")).text, sep=" ").astype(int)
                if not np.all(vc == 3):
                    continue
            F.append(idx.reshape(-1, 3))
        if F:
            geoms[g.get("id")] = (V, np.vstack(F))
    out = trimesh.Scene()
    k = 0
    for node in root.iter(q("node")):
        mt = node.find(q("matrix"))
        T = (np.fromstring(mt.text, sep=" ").reshape(4, 4) if mt is not None else np.eye(4))
        for ig in node.iter(q("instance_geometry")):
            gid = (ig.get("url") or "").lstrip("#")
            if gid in geoms:
                V, F = geoms[gid]
                m = trimesh.Trimesh(vertices=V.copy(), faces=F.copy(), process=False)
                m.apply_transform(T)
                out.add_geometry(m, node_name=f"{node.get('name') or gid}_{k}")
                k += 1
    if k == 0:                                   # 노드가 없으면 지오메트리를 그대로
        for gid, (V, F) in geoms.items():
            out.add_geometry(trimesh.Trimesh(vertices=V, faces=F, process=False),
                             node_name=gid)
    return out


def load_points(path, unit_scale=1.0, target_pts=400_000, pick=None, seed=0):
    """파일 → (표면 표본 점구름[mm], 면수, 지오메트리 이름들)."""
    import trimesh
    if str(path).lower().endswith(".dae"):
        obj = _load_dae(path)
    else:
        obj = trimesh.load(str(path), process=False, force="scene")
    geoms, names = [], []
    if isinstance(obj, trimesh.Scene):
        for node in obj.graph.nodes_geometry:
            T, gname = obj.graph[node]
            g = obj.geometry[gname]
            if not isinstance(g, trimesh.Trimesh) or not len(g.faces):
                continue
            gc = g.copy()
            gc.apply_transform(T)
            geoms.append(gc)
            names.append(f"{node}|{gname}")
    else:
        geoms.append(obj)
        names.append(Path(path).name)
    if pick is not None:
        keep = [i for i, (n, g) in enumerate(zip(names, geoms)) if pick(n, g)]
        geoms = [geoms[i] for i in keep]
        names = [names[i] for i in keep]
    V = np.vstack([np.asarray(g.vertices, float) for g in geoms]) * unit_scale
    F, off, nf = [], 0, 0
    for g in geoms:
        F.append(np.asarray(g.faces, int) + off)
        off += len(g.vertices)
        nf += len(g.faces)
    F = np.vstack(F)
    rng = np.random.default_rng(seed)
    a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
    tot = float(area.sum())
    cnt = rng.multinomial(int(target_pts), area / tot)
    idx = np.repeat(np.arange(len(F)), cnt)
    u1, u2 = rng.random(len(idx)), rng.random(len(idx))
    su = np.sqrt(u1)
    P = ((1 - su)[:, None] * a[idx] + (su * (1 - u2))[:, None] * b[idx]
         + (su * u2)[:, None] * c[idx])
    return np.vstack([np.unique(V, axis=0), P]), nf, names


def disc_frame(P):
    """점구름 → (회전축 단위벡터, 회전중심).  축 = 최소분산 방향, 중심 = 양 팁 중점."""
    C = P.mean(0)
    w, Vv = np.linalg.eigh(np.cov((P - C).T))
    axis = Vv[:, 0] / np.linalg.norm(Vv[:, 0])
    e1 = np.cross(axis, [1.0, 0, 0])
    if np.linalg.norm(e1) < 1e-6:
        e1 = np.cross(axis, [0, 1.0, 0])
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(axis, e1)
    P2 = np.c_[(P - C) @ e1, (P - C) @ e2]
    ctr = P2.mean(0)
    for _ in range(4):                       # 양 팁 중점으로 수렴
        d = np.linalg.norm(P2 - ctr, axis=1)
        p1 = P2[int(np.argmax(d))]
        p2 = P2[int(np.argmax(np.linalg.norm(P2 - p1, axis=1)))]
        ctr = 0.5 * (p1 + p2)
    ctr3 = C + ctr[0] * e1 + ctr[1] * e2
    return axis, ctr3, e1, e2


def planform_mesh(P, band_frac=0.006, gap_deg=12.0, n_sta=170):
    """M1 — 점구름에서 반경별 c_arc / c_cal / coverage / 두께 / 피치각."""
    axis, ctr, e1, e2 = disc_frame(P)
    Q = P - ctr
    x, y, z = Q @ e1, Q @ e2, Q @ axis
    r = np.hypot(x, y)
    th = np.arctan2(y, x)
    R = float(np.percentile(r, 100.0))
    rr = np.linspace(0.12, 0.99, n_sta)
    c_arc = np.full(n_sta, np.nan)
    c_cal = np.full(n_sta, np.nan)
    tmax = np.full(n_sta, np.nan)
    cov = np.full(n_sta, np.nan)
    narc = np.zeros(n_sta, int)
    theta_deg = np.full(n_sta, np.nan)
    band = band_frac * R
    for i, t in enumerate(rr):
        rt = t * R
        m = np.abs(r - rt) < band
        if m.sum() < 25:
            continue
        tt = th[m]
        aa = _arcs(tt, gap_deg)
        cov[i] = sum(h - l for l, h in aa) / (2 * np.pi)
        narc[i] = len(aa)
        if not aa:
            continue
        k = int(np.argmax([h - l for l, h in aa]))
        lo, hi = aa[k]
        c_arc[i] = rt * (hi - lo)
        sel = np.zeros(int(m.sum()), bool)
        for sh in (0.0, 2 * np.pi, -2 * np.pi):
            sel |= (tt + sh >= lo - 1e-12) & (tt + sh <= hi + 1e-12)
        idx = np.where(m)[0][sel]
        if len(idx) < 5:
            continue
        ref = 0.5 * (lo + hi)
        tl = ref + np.angle(np.exp(1j * (th[idx] - ref)))
        S = np.c_[rt * tl, z[idx]]                       # 원통면을 펼친 단면
        c_cal[i] = _caliper(S)
        # 시위선 = 최대 캘리퍼 축 → 그 좌표계에서 상하면 차 = 두께(시위선 기준)
        try:
            from scipy.spatial import ConvexHull
            H = S[ConvexHull(S).vertices]
        except Exception:
            H = S
        D = H[:, None, :] - H[None, :, :]
        dd = np.sqrt((D ** 2).sum(-1))
        a_, b_ = np.unravel_index(int(np.argmax(dd)), dd.shape)
        v = H[b_] - H[a_]
        v /= np.linalg.norm(v)
        n = np.array([-v[1], v[0]])
        proj = (S - H[a_]) @ n
        tmax[i] = float(proj.max() - proj.min())
        theta_deg[i] = float(np.degrees(np.arctan2(abs(v[1]), abs(v[0]))))
    return dict(rr=rr, c_arc=c_arc, c_cal=c_cal, t_max=tmax, cov=cov,
                n_arc=narc, theta_deg=theta_deg, R=R, axis=axis.tolist(),
                center=ctr.tolist())


def planform_mesh_raster(P, n_px=1400, n_sta=170):
    """M2 — **전혀 다른 경로**: 회전면에 투영해 래스터 실루엣을 만들고 반경별 각폭을 센다.

    점구름 각폭(M1)이 표본 밀도·gap 임계값에 의존하는 데 반해 이건 픽셀 점유로만 판단한다."""
    axis, ctr, e1, e2 = disc_frame(P)
    Q = P - ctr
    x, y = Q @ e1, Q @ e2
    R = float(np.hypot(x, y).max())
    s = (n_px / 2 - 2) / R
    ix = np.clip((x * s + n_px / 2).astype(int), 0, n_px - 1)
    iy = np.clip((y * s + n_px / 2).astype(int), 0, n_px - 1)
    img = np.zeros((n_px, n_px), bool)
    img[iy, ix] = True
    from scipy import ndimage
    img = ndimage.binary_closing(img, np.ones((3, 3)))
    img = ndimage.binary_fill_holes(img)
    gy, gx = np.nonzero(img)
    px = (gx - n_px / 2) / s
    py = (gy - n_px / 2) / s
    r = np.hypot(px, py)
    th = np.arctan2(py, px)
    rr = np.linspace(0.12, 0.99, n_sta)
    c_arc = np.full(n_sta, np.nan)
    for i, t in enumerate(rr):
        rt = t * R
        m = np.abs(r - rt) < (1.6 / s)
        if m.sum() < 8:
            continue
        aa = _arcs(th[m], gap_deg=12.0)
        if aa:
            c_arc[i] = rt * max(h - l for l, h in aa)
    return dict(rr=rr, c_arc=c_arc, R=R)


# ================================================================= #
#  2. 사진 → 실루엣
# ================================================================= #
def silhouette(path, mode, crop=None, thr=None, min_frac=2e-4):
    """사진 → 이진 실루엣(마스크) + 연결요소 목록.

    mode: 'dark_on_light' | 'light_on_blue' | 'alpha_dark'
    """
    from PIL import Image
    from scipy import ndimage
    im = Image.open(path)
    im = im.convert("RGBA")
    if crop:
        im = im.crop(crop)
    a = np.asarray(im, float)
    rgb, al = a[..., :3], a[..., 3]
    lum = rgb.mean(2)
    mx, mn = rgb.max(2), rgb.min(2)
    sat = (mx - mn) / np.maximum(mx, 1.0)
    if mode == "alpha_dark":
        mask = (al > 128) & (lum < (thr if thr is not None else 200))
    elif mode == "dark_on_light":
        mask = lum < (thr if thr is not None else 200)
        if al.min() < 250:
            mask &= al > 128
    elif mode == "light_on_blue":
        # 파란 배경 위의 흰 물체: 밝고 채도 낮은 화소
        mask = (lum > (thr if thr is not None else 110)) & (sat < 0.35)
    else:
        raise ValueError(mode)
    mask = ndimage.binary_opening(mask, np.ones((2, 2)))
    lab, n = ndimage.label(mask)
    sizes = ndimage.sum(mask, lab, range(1, n + 1))
    keep = [(int(i + 1), int(sizes[i])) for i in np.argsort(sizes)[::-1]
            if sizes[i] > min_frac * mask.size]
    return mask, lab, keep


def comp_pts(lab, cid):
    ys, xs = np.where(lab == cid)
    return np.c_[xs.astype(float), ys.astype(float)]


def photo_disc_planform(P, n_sta=170, gap_deg=14.0, band_px=None):
    """M1(사진) — **완전한 2날 프롭**(허브 포함, 펼침)의 실루엣에서 중심기준 각폭.

    중심 = 가장 먼 두 점(= 양 팁)의 중점(저장소 관례)."""
    ctr = P.mean(0)
    for _ in range(4):
        d = np.linalg.norm(P - ctr, axis=1)
        p1 = P[int(np.argmax(d))]
        p2 = P[int(np.argmax(np.linalg.norm(P - p1, axis=1)))]
        ctr = 0.5 * (p1 + p2)
    d = P - ctr
    r = np.linalg.norm(d, axis=1)
    th = np.arctan2(d[:, 1], d[:, 0])
    R = float(r.max())
    band = band_px if band_px is not None else max(1.2, 0.008 * R)
    rr = np.linspace(0.12, 0.99, n_sta)
    c = np.full(n_sta, np.nan)
    cov = np.full(n_sta, np.nan)
    for i, t in enumerate(rr):
        m = np.abs(r - t * R) < band
        if m.sum() < 6:
            continue
        aa = _arcs(th[m], gap_deg)
        cov[i] = sum(h - l for l, h in aa) / (2 * np.pi)
        if aa:
            c[i] = t * R * max(h - l for l, h in aa)
    return dict(rr=rr, c=c, cov=cov, R=R, center=ctr.tolist())


def blade_local_width(P, root_xy, n_sta=160, half_span_px=None):
    """M2(사진) — **날-국소 좌표계** 수직폭.  중심 추정에 면역이고 접힌 날에도 쓴다.

    root_xy : 날의 «뿌리 쪽» 기준점(힌지 또는 허브 중심). 여기서부터의 거리를 스팬으로 쓴다.
    방법 — ① 주축(PCA) 으로 대략의 스팬축을 잡고 ② 스팬 구간마다 중심선(질량중심)을 구해
           ③ 중심선의 **국소 접선**에 수직인 방향으로 폭을 잰다(스윕/굽힘에 면역).
    """
    root = np.asarray(root_xy, float)
    Q = P - root
    w, V = np.linalg.eigh(np.cov(Q.T))
    u = V[:, int(np.argmax(w))]
    if (Q @ u).mean() < 0:
        u = -u
    v = np.array([-u[1], u[0]])
    s = Q @ u
    t = Q @ v
    s_hi = float(np.percentile(s, 99.9))
    s_lo = float(max(0.0, np.percentile(s, 0.2)))
    ss = np.linspace(s_lo, s_hi, n_sta)
    hw = half_span_px if half_span_px is not None else max(1.0, 0.006 * (s_hi - s_lo))
    mid = np.full(n_sta, np.nan)
    for i, x0 in enumerate(ss):
        m = np.abs(s - x0) < hw
        if m.sum() >= 4:
            mid[i] = t[m].mean()
    good = np.isfinite(mid)
    if good.sum() > 12:                       # 중심선 평활화
        from numpy.polynomial import polynomial as Pl
        cf = Pl.polyfit(ss[good], mid[good], 3)
        midf = Pl.polyval(ss, cf)
        dmid = Pl.polyval(ss, Pl.polyder(cf))
    else:
        midf = np.nan_to_num(mid)
        dmid = np.zeros(n_sta)
    width = np.full(n_sta, np.nan)
    rad = np.full(n_sta, np.nan)
    for i, x0 in enumerate(ss):
        ang = np.arctan(dmid[i])
        un = np.array([np.cos(ang), np.sin(ang)])       # 국소 스팬 방향(u,v 좌표계)
        vn = np.array([-un[1], un[0]])
        c0 = np.array([x0, midf[i]])
        loc = np.c_[s, t] - c0
        m = np.abs(loc @ un) < hw
        if m.sum() < 4:
            continue
        pr = loc[m] @ vn
        width[i] = float(pr.max() - pr.min())
        rad[i] = float(np.hypot(x0, midf[i]))           # 뿌리 기준점에서의 거리
    return dict(s=ss, width=width, rad=rad, u=u.tolist(), v=v.tolist(),
                mid=midf, span=float(s_hi - s_lo))


def holes_in(lab, cid, mask):
    """연결요소 cid 안에 갇힌 배경 영역(구멍)들 → [(중심 x, 중심 y, 화소수), ...]."""
    from scipy import ndimage
    m = lab == cid
    filled = ndimage.binary_fill_holes(m)
    h = filled & ~m
    hl, hn = ndimage.label(h)
    out = []
    for i in range(1, hn + 1):
        ys, xs = np.where(hl == i)
        out.append((float(xs.mean()), float(ys.mean()), int(len(xs))))
    out.sort(key=lambda z: -z[2])
    return out


# ================================================================= #
#  3. UIUC 프로펠러 DB — 같은 «규격 급» 밴드
# ================================================================= #
def uiuc_rows(zip_path=UIUC_ZIP):
    if not Path(zip_path).exists():
        return None
    z = zipfile.ZipFile(str(zip_path))
    rows = []
    for n in z.namelist():
        if not n.endswith("_geom.txt"):
            continue
        dat = []
        for line in z.read(n).decode("utf8", "ignore").splitlines():
            p = line.split()
            if len(p) >= 3:
                try:
                    dat.append([float(p[0]), float(p[1]), float(p[2])])
                except ValueError:
                    continue
        if len(dat) < 8:
            continue
        a = np.array(dat)
        rr, cR, beta = a[:, 0], a[:, 1], a[:, 2]
        base = Path(n).name.replace("_geom.txt", "")
        m = re.match(r"([a-zA-Z0-9]+)_(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)", base)
        ok = (rr >= 0.20) & (rr <= 0.96)
        if ok.sum() < 8:
            continue
        x, y = rr[ok], cR[ok]
        cmax = float(y.max())
        rows.append(dict(
            name=base, family=(m.group(1) if m else base.split("_")[0]),
            dia_in=float(m.group(2)) if m else np.nan,
            pitch_in=float(m.group(3)) if m else np.nan,
            c_max_over_R=cmax, peak_r_over_R=float(x[int(np.argmax(y))]),
            cn={k: float(np.interp(g, x, y)) / cmax for g, k in zip(GRID, GRID_KEYS)},
            blade_area_over_R2=float(np.trapezoid(y, x)),
        ))
    return rows


def uiuc_band(rows, dia_lo, dia_hi, pit_lo=None, pit_hi=None):
    """지름(인치) 구간(+선택적 피치 구간)으로 자른 UIUC 밴드 통계."""
    sel = [r for r in rows if np.isfinite(r["dia_in"]) and dia_lo <= r["dia_in"] <= dia_hi
           and (pit_lo is None or (np.isfinite(r["pitch_in"]) and pit_lo <= r["pitch_in"] <= pit_hi))]
    if not sel:
        return None
    v = np.array([r["c_max_over_R"] for r in sel])
    cn = {k: [r["cn"][k] for r in sel] for k in GRID_KEYS}
    return dict(
        n=len(sel), names=sorted({r["name"] for r in sel})[:40],
        c_max_over_R=dict(min=float(v.min()), p25=float(np.percentile(v, 25)),
                          median=float(np.median(v)), p75=float(np.percentile(v, 75)),
                          max=float(v.max()), mean=float(v.mean()),
                          sd=float(v.std(ddof=1)) if len(v) > 1 else 0.0),
        cn_median={k: float(np.median(cn[k])) for k in GRID_KEYS},
        cn_p25={k: float(np.percentile(cn[k], 25)) for k in GRID_KEYS},
        cn_p75={k: float(np.percentile(cn[k], 75)) for k in GRID_KEYS},
        peak_r_median=float(np.median([r["peak_r_over_R"] for r in sel])),
    )


if __name__ == "__main__":
    print("이 파일은 라이브러리 + 드라이버다. 드라이버는 아래 run() 에 있다.")


# ================================================================= #
#  4. 사진의 **원근 보정** — 로터 링(regular n-gon)을 앵커로 아핀 복원
# ================================================================= #
def affine_from_rotor_ring(seeds_xy, n=None, radius_mm=None):
    """로터가 **정n각형**으로 배치된 걸 알고 있을 때, 사진의 아핀 왜곡 A 를 복원한다.

    왜 필요한가 — 프롭 평면형을 사진에서 재면 카메라가 조금만 기울어도 스팬 방향이
    압축돼 c/R 이 부풀어 오른다. 로터 링은 **그 평면 위의 알려진 도형**이라 자를 대신한다.

    모델 :  p_k = c + A · [cos(φ + 2πk/n), sin(φ + 2πk/n)]
    미지수 :  c(2) + A(4) + φ(1).  n=8 이면 16개 식 → 넉넉히 과결정.
    되돌리기 :  q = A⁻¹ (p − c)  →  단위원 위의 로터 링(= 실제 회전면 좌표, 단위 = 로터 반경).
    잔차 = **아핀으로 설명 안 되는 성분**(= 원근/비대칭). 그 크기를 그대로 보고한다.
    """
    P = np.asarray(seeds_xy, float)
    n = n or len(P)
    c0 = P.mean(0)
    ang = np.arctan2(P[:, 1] - c0[1], P[:, 0] - c0[0])
    order = np.argsort(ang)
    P = P[order]
    ang = ang[order]

    def solve(phi):
        k = np.arange(n)
        u = np.c_[np.cos(phi + 2 * np.pi * k / n), np.sin(phi + 2 * np.pi * k / n)]
        # p = c + A u  →  [u_x u_y 1] · [a11 a12 cx ; a21 a22 cy]^T
        M = np.c_[u, np.ones(n)]
        sol, *_ = np.linalg.lstsq(M, P, rcond=None)
        A = sol[:2, :].T
        c = sol[2, :]
        res = P - (M @ sol)
        return A, c, float(np.sqrt((res ** 2).sum(1).mean())), res

    best = None
    for phi in np.linspace(0, 2 * np.pi / n, 721):
        A, c, rms, res = solve(phi)
        if best is None or rms < best[2]:
            best = (A, c, rms, res, phi)
    A, c, rms, res, phi = best
    sv = np.linalg.svd(A, compute_uv=False)
    out = dict(A=A.tolist(), center=c.tolist(), phi_deg=float(np.degrees(phi)),
               resid_rms_px=rms, resid_per_point_px=[float(np.hypot(*r)) for r in res],
               ring_radius_px_major=float(sv[0]), ring_radius_px_minor=float(sv[1]),
               anisotropy=float(sv[0] / sv[1]),
               order=[int(i) for i in order])
    if radius_mm:
        out["mm_per_px_along_major"] = float(radius_mm / sv[0])
        out["mm_per_unit"] = float(radius_mm)      # 되돌린 좌표계의 1 = radius_mm
    return out, A, c


def undistort(P_xy, A, c):
    """사진 좌표 → 아핀 복원된 회전면 좌표(단위 = 로터 링 반경)."""
    return (np.linalg.inv(np.asarray(A)) @ (np.asarray(P_xy, float) - np.asarray(c)).T).T


def ruler_period_px(path, p0, p1, n_samp=4000, crop=None, lo=2.0, hi=60.0):
    """자(눈금) 위의 선분 p0→p1 을 따라 밝기를 훑어 **눈금 주기(px)** 를 자기상관으로 찾는다.

    반환: (주기 px, 정규화 자기상관 봉우리 높이).  봉우리가 낮으면 못 읽은 것이다."""
    from PIL import Image
    im = Image.open(path).convert("L")
    if crop:
        im = im.crop(crop)
    a = np.asarray(im, float)
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float)
    t = np.linspace(0, 1, n_samp)
    xy = p0[None, :] + t[:, None] * (p1 - p0)[None, :]
    x = np.clip(xy[:, 0], 0, a.shape[1] - 2)
    y = np.clip(xy[:, 1], 0, a.shape[0] - 2)
    x0, y0 = x.astype(int), y.astype(int)
    fx, fy = x - x0, y - y0
    v = (a[y0, x0] * (1 - fx) * (1 - fy) + a[y0, x0 + 1] * fx * (1 - fy)
         + a[y0 + 1, x0] * (1 - fx) * fy + a[y0 + 1, x0 + 1] * fx * fy)
    v = v - np.convolve(v, np.ones(81) / 81, mode="same")     # 저주파 제거
    v[:60] = 0; v[-60:] = 0
    ac = np.correlate(v, v, mode="full")[len(v) - 1:]
    ac /= max(ac[0], 1e-9)
    L = float(np.linalg.norm(p1 - p0))
    step = L / (n_samp - 1)
    lag = np.arange(len(ac)) * step
    m = (lag > lo) & (lag < hi)
    if not m.any():
        return None, None
    k = int(np.argmax(ac[m]))
    return float(lag[m][k]), float(ac[m][k])


# ================================================================= #
#  5. 사진 — **부화소 시위**(임계값 없는 면적법)
# ================================================================= #
def soft_arc_chord(lum, center, R_max, sector_dir=None, sector_deg=55.0,
                   n_sta=180, n_theta=1441, band_frac=0.010, bg_hi=95.0, ob_lo=5.0):
    """반경별 **투영 시위 c_arc(r)** 를 부화소로 잰다 — 이진 임계값을 안 쓴다.

    왜 — 사진의 날 가장자리는 흐릿하다(안티에일리어싱·JPEG·그림자). 임계값을 110↔180 으로
    바꾸면 s1000+ 에서 c_max/R 이 0.164↔0.177 로 **8 % 흔들린다**. 그래서 임계값 대신
    **국소 대비로 정규화한 피복률 α 의 적분**을 쓴다. α 는 «이 화소가 날에 얼마나 덮였나» 다.

    각 반경 고리에서:  α(θ) = clip((bg − I)/(bg − obj), 0, 1),
      bg = 그 고리 각도 프로파일의 상위 백분위(배경), obj = 하위 백분위(날 속살).
      c_arc(r) = r · Σ α(θ) Δθ.
    ⇒ 결과는 «50 % 대비 지점» 을 가장자리로 잡은 것과 같고, 화소보다 잘게 잰다.
    """
    lum = np.asarray(lum, float)
    H, W = lum.shape
    cx, cy = float(center[0]), float(center[1])
    rr = np.linspace(0.10, 0.995, n_sta)
    th = np.linspace(-np.pi, np.pi, n_theta, endpoint=False)
    if sector_dir is not None:
        d = np.asarray(sector_dir, float)
        d /= np.linalg.norm(d)
        th0 = np.arctan2(d[1], d[0])
        keep = np.abs(np.angle(np.exp(1j * (th - th0)))) < np.radians(sector_deg)
        th = th[keep]
    dth = float(2 * np.pi / n_theta)
    c = np.full(n_sta, np.nan)
    cov = np.full(n_sta, np.nan)
    nb = max(1, int(round(band_frac * n_sta)))
    for i, t in enumerate(rr):
        rad = t * R_max
        prof = np.zeros(len(th))
        cnt = 0
        for dr in np.linspace(-0.5, 0.5, 3) * (band_frac * R_max * 2):
            x = cx + (rad + dr) * np.cos(th)
            y = cy + (rad + dr) * np.sin(th)
            ok = (x >= 0) & (x < W - 1) & (y >= 0) & (y < H - 1)
            if ok.mean() < 0.9:
                continue
            x0 = np.clip(x.astype(int), 0, W - 2)
            y0 = np.clip(y.astype(int), 0, H - 2)
            fx, fy = x - x0, y - y0
            prof += (lum[y0, x0] * (1 - fx) * (1 - fy) + lum[y0, x0 + 1] * fx * (1 - fy)
                     + lum[y0 + 1, x0] * (1 - fx) * fy + lum[y0 + 1, x0 + 1] * fx * fy)
            cnt += 1
        if cnt == 0:
            continue
        prof /= cnt
        sm = np.convolve(prof, np.ones(3) / 3.0, mode="same")
        sm[0] = sm[1]; sm[-1] = sm[-2]
        bg = np.percentile(prof, bg_hi)
        ob = float(sm.min())
        # ⚠ 옛 판: ob = percentile(prof, 5). 날이 부채꼴의 5 % 보다 좁아지는 **팁 근처**에서
        #   5 백분위가 날 속살이 아니라 가장자리 램프에 걸려 α 가 부풀었다(팁에서 +30 %).
        #   이제 «평활한 프로파일의 최솟값» = 날의 가장 짙은 속살을 쓴다.
        if bg - ob < 12.0:                       # 대비 없음 = 그 고리에 날이 없다
            c[i] = 0.0
            cov[i] = 0.0
            continue
        al = np.clip((bg - prof) / (bg - ob), 0.0, 1.0)
        c[i] = rad * float(al.sum()) * dth
        cov[i] = float(al.mean())
    return dict(rr=rr, c=c, cov=cov, R=float(R_max))


def soft_tip_radius(lum, center, r_guess, sector_dir, sector_deg=55.0, n_theta=2881,
                    frac=0.5):
    """날개 끝 반경을 부화소로 — 반경을 늘려가며 피복 면적이 0 이 되는 지점(50 % 대비)."""
    prof = soft_arc_chord(lum, center, r_guess * 1.6, sector_dir, sector_deg,
                          n_sta=260, n_theta=n_theta, band_frac=0.006)
    r, c = prof["rr"] * prof["R"], prof["c"]
    ok = np.isfinite(c)
    r, c = r[ok], c[ok]
    inb = r < 0.75 * r_guess
    if not inb.any():
        return None
    ref = float(np.nanmax(c[inb]))
    hit = np.where((r > 0.6 * r_guess) & (c < frac * 0.06 * ref))[0]
    if len(hit) == 0:
        return float(r[c > 0].max())
    i = hit[0]
    return float(r[i])


# ================================================================= #
#  6. 접힌 날(폴딩 프롭) — 힌지 모형
# ================================================================= #
def folded_blade_frame(hinge_xy, tip_xy, e_px):
    """접힌 날의 «가상 회전중심» O' 과 디스크 반경 R 을 낸다.

    접이식 프롭은 힌지 볼트를 축으로 **회전면 안에서** 돈다. 날은 강체이고 힌지는 날 축 위에
    있으므로, 펼친 상태에서 회전축은 «힌지에서 팁 반대쪽으로 e 만큼» 떨어진 점이다.
    ⇒ 접힌 사진에서도 그 점 O' = H − e·û 를 중심으로 각폭을 재면 **펼친 기하와 같다**.
       R = e + L,  L = |팁 − 힌지|.
    """
    H = np.asarray(hinge_xy, float)
    T = np.asarray(tip_xy, float)
    u = T - H
    L = float(np.linalg.norm(u))
    u /= L
    return dict(center=(H - e_px * u).tolist(), R=float(e_px + L), L=L,
                axis=u.tolist(), e=float(e_px))


def coverage_arc_chord(cov, center, R, n_sta=200, hub_guard=0.05, sector=None):
    """**피복률 영상**(0~1)에서 반경별 투영 시위를 면적법으로 낸다.

    c(r) = (그 고리 안의 피복 면적) / (고리의 반경 폭).  α 가 부화소라 결과도 부화소다.
    sector: (단위벡터, 반각[deg]) — 옆 날을 배제할 때.
    """
    cov = np.asarray(cov, float)
    H, W = cov.shape
    yy, xx = np.nonzero(cov > 0.01)
    w = cov[yy, xx]
    d = np.c_[xx - center[0], yy - center[1]]
    r = np.hypot(d[:, 0], d[:, 1])
    if sector is not None:
        u, half = sector
        u = np.asarray(u, float) / np.linalg.norm(u)
        cs = (d @ u) / np.maximum(r, 1e-9)
        k = cs > np.cos(np.radians(half))
        yy, xx, w, r = yy[k], xx[k], w[k], r[k]
    rr = np.linspace(hub_guard, 0.995, n_sta)
    h = 0.5 * (rr[1] - rr[0]) * R * 1.5
    c = np.full(n_sta, np.nan)
    for i, t in enumerate(rr):
        m = np.abs(r - t * R) < h
        c[i] = float(w[m].sum()) / (2 * h) if m.any() else 0.0
    return dict(rr=rr, c=c, R=float(R))


def crease_seam(lum, y0, y1, x_top, x_bot, win=13):
    """맞닿은 두 날 사이의 **골(어두운 주름)** 을 행마다 찾아 경계선 x_s(y) 를 만든다."""
    ys = np.arange(int(y0), int(y1) + 1)
    guess = np.interp(ys, [y0, y1], [x_top, x_bot])
    out = []
    for y, g in zip(ys, guess):
        a = int(max(0, g - win)); b = int(min(lum.shape[1] - 1, g + win))
        seg = lum[y, a:b + 1]
        sm = np.convolve(seg, np.ones(3) / 3, mode="same")
        out.append(a + int(np.argmin(sm[1:-1])) + 1)
    out = np.array(out, float)
    k = np.polyfit(ys, out, 3)                     # 매끈하게
    return ys, np.polyval(k, ys)


# ================================================================= #
#  7. 랜드마크 원장 — 사진에서 **사람이 읽은 점**(확대 격자로 판독)
#     ⚠ 여기 적힌 픽셀 좌표가 이 계측의 유일한 수작업 입력이다. 나머지는 전부 자동.
#     판독용 확대 이미지는 스크래치에 남겼고, 재판독하려면 같은 격자로 다시 그리면 된다.
# ================================================================= #
LANDMARKS = {
    "s1000plus_top": dict(
        photo="s1000plus/s1000+_1.png",
        what="옥토 8 로터 모터 중심(씨앗) — 정8각형 링 맞춤으로 재정렬된다",
        seeds=[(332.4, 207.8), (584.8, 207.0), (154.2, 386.8), (770.1, 383.1),
               (154.4, 638.3), (767.0, 638.4), (332.8, 815.4), (584.3, 816.2)],
        ring_radius_mm=522.5,          # 공표 대각축거 1045 mm / 2
        read_by="lum<70 무게중심(반경 22 px 창) → 링 맞춤이 다시 정렬"),
    "m350rtk_prop_pair": dict(
        photo="m350rtk/m350rtk_c01_prop_2110s_pair.png",
        what="2110S 프롭 2개(=1쌍)의 허브 브래킷 — 샤프트 구멍과 접이 힌지 보스",
        props=[dict(key="cw", shaft=(197.5, 512.0),
                    hinges=[(174.5, 512.0), (220.5, 512.0)], notch=(211.5, 233.0)),
               dict(key="ccw", shaft=(318.5, 512.0),
                    hinges=[(295.5, 512.0), (341.5, 512.0)], notch=(332.0, 233.0))],
        read_by="12배 확대 격자에서 판독. 샤프트 구멍은 두 힌지의 중점과 0.5 px 안에서 일치(자기검증)."),
    "phantom3_p25_motors": dict(
        photo="phantom3/phantom3_p25_fccpro07_top_props_laid_tape.jpg",
        what="기체 모터 4개 — **시야 왜곡(아핀) 측정용**. 프롭 자체는 아님",
        boxes=dict(TL=(185, 40, 245, 115), TR=(485, 50, 545, 125),
                   BL=(170, 340, 230, 415), BR=(480, 350, 545, 425)),
        ring_radius_mm=175.0,          # 공표 모터 대각 350 mm / 2
        read_by="상자 안 «저채도·중간밝기» 화소 무게중심"),
}
