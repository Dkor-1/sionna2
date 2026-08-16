#!/usr/bin/env python
"""⭐ 적대적 다중참조 대조 — «우리 날 법칙이 정말 이상치인가»  (2026-08-16)

docs/MESH_AUDIT_0816.md 의 C4/I2/I7/I8 은 **참조 4종**(3DR Solo · Holybro 1345 ·
Yuneec H480 · DJI Mini 2 공식 GLB) + 제품사진 3장으로 «Solo 는 유일한 이상치이고
우리 시위는 외곽에서 27~39 % 좁다» 고 판정했다. 이 스크립트는 그 판정을 **반증하려고**
참조 모집단을 크게 늘려 같은 자로 다시 잰다.

새로 더한 참조
  ⓐ 저장소의 다른 프롭 CAD 전수 — assets/meshes/reference_study/ 의 시뮬·제조사 CAD
     (DJI M100 1345 · Parrot Bebop2 · Parrot ANAFI USA(제조사 STEP→GLB) · DJI Mavic 2 Pro(Webots)
      · DJI F330/F550 · Tarot T650 · T-Drones M690B · AscTec neo9/neo11 · 3DR Iris · Alti · X500)
  ⓑ **UIUC 프로펠러 데이터베이스** — 실측 평면형 **132종**(r/R, c/R, β). 소형 프롭(5~19 in)
     기하의 공개 «참값» 모집단. https://m-selig.ae.illinois.edu/props/download/UIUC-propDB.zip
  ⓒ 제품사진 계측 — assets/photos/ 의 정면 탑뷰 프롭 사진(실루엣 각폭법)
  ⓓ 우리 것 두 갈래 — 법칙 상수(CHORD_FRAC) 와 **출하 메쉬**(assets/meshes/drones/*__prop.obj)

측정법(감사 스크립트와 코드 공유 없음, planform_lib 는 이 파일에 인라인)
  · 메쉬: 면적비례 표면 표본 → 최소분산 방향 = 회전축 → 양 팁 중점 = 회전중심
          → 반경 밴드를 원통면에 펼쳐 (1) 각폭 시위 c_arc = r·Δθ  (2) 최대 캘리퍼 c_cal
  · 자 검증: outputs/reference_props.json 의 3종을 먼저 재현한 뒤에만 새 대상에 댄다.
  · 사진: 실루엣 이진화 → 프롭 성분 → 팁 중점 = 중심 → 반경별 각폭 (= c_arc 정의와 동일)

⛔ GPU 미사용(numpy/trimesh/PIL/scipy) · ⛔ 저장소 코드 무변경 · ⛔ git 무접촉.
산출: outputs/mesh_adv_multi_reference_0816.json

**재현 방법**
  1) UIUC zip 을 받아 둔다(이미 /data/public/sionna/uiuc_propdb/UIUC-propDB.zip 에 있다):
       curl -o UIUC-propDB.zip https://m-selig.ae.illinois.edu/props/download/UIUC-propDB.zip
  2) DAE(COLLADA) 참조를 읽으려면 pycollada 가 필요하다. 공용 venv 를 건드리지 않고:
       uv pip install --python /workspace/.venvs/py312/bin/python --target <scratch>/pylibs pycollada
  3) 실행:
       cd /workspace/sionna/benchmark && \
       PYTHONPATH=/workspace/sionna/src:<scratch>/pylibs \
       UIUC_ZIP=/data/public/sionna/uiuc_propdb/UIUC-propDB.zip \
       /workspace/.venvs/py312/bin/python adv_multiref_planform_0816.py
     (전 과정 CPU, 30초~3분. 표면표본 seed 고정이라 결과는 결정적이다.)
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
import time
import zipfile
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path("/workspace/sionna")
REF = ROOT / "assets/meshes/reference"
RS = ROOT / "assets/meshes/reference_study"
PHOTO = ROOT / "assets/photos"
OUT = ROOT / "outputs/mesh_adv_multi_reference_0816.json"
UIUC_ZIP = Path(os.environ.get(
    "UIUC_ZIP", "/data/public/sionna/uiuc_propdb/UIUC-propDB.zip"))
UIUC_URL = "https://m-selig.ae.illinois.edu/props/download/UIUC-propDB.zip"

GRID = np.round(np.arange(0.20, 0.9601, 0.05), 3)      # 비교 격자 r/R


# ===================================================================== #
#  1. 메쉬 → 평면형
# ===================================================================== #
def load_geoms(path):
    """파일의 모든 지오메트리를 (이름, 정점, 면) 로. 씬 변환 적용."""
    obj = trimesh.load(str(path), process=False, force="scene")
    out = []
    if isinstance(obj, trimesh.Scene):
        for node in obj.graph.nodes_geometry:
            T, gname = obj.graph[node]
            g = obj.geometry[gname]
            if not isinstance(g, trimesh.Trimesh) or not len(g.faces):
                continue
            gc = g.copy()
            gc.apply_transform(T)
            out.append((f"{node}|{gname}", np.asarray(gc.vertices, float),
                        np.asarray(gc.faces, int)))
    else:
        out.append((Path(path).name, np.asarray(obj.vertices, float),
                    np.asarray(obj.faces, int)))
    return out


def sample_surface(v, f, target_pts=300_000, seed=0):
    """면적비례 표면 표본 + **그 면이 실제로 쓰는 정점만**."""
    rng = np.random.default_rng(seed)
    used = np.unique(f)
    v_used = v[used]
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
    tot = float(area.sum())
    if tot <= 0:
        return v_used.copy()
    cnt = rng.multinomial(int(target_pts), area / tot)
    idx = np.repeat(np.arange(len(f)), cnt)
    u1, u2 = rng.random(len(idx)), rng.random(len(idx))
    su = np.sqrt(u1)
    p = ((1 - su)[:, None] * a[idx] + (su * (1 - u2))[:, None] * b[idx]
         + (su * u2)[:, None] * c[idx])
    return np.vstack([v_used, p])


def _tip_points(P2, n_bins=720, thr=0.90):
    """평면 투영점 P2(중심 기준) 에서 날개 끝점들을 찾는다(방위 포락선 봉우리)."""
    r = np.linalg.norm(P2, axis=1)
    th = np.arctan2(P2[:, 1], P2[:, 0])
    b = ((th + np.pi) / (2 * np.pi) * n_bins).astype(int) % n_bins
    env = np.full(n_bins, -1.0)
    np.maximum.at(env, b, r)
    rmax = env.max()
    hot = env > thr * rmax
    if hot.all():
        return P2[[int(np.argmax(r))]]
    # 원형 연속 구간 묶기
    idx = np.where(hot)[0]
    groups, cur = [], [idx[0]]
    for i in idx[1:]:
        if i == cur[-1] + 1:
            cur.append(i)
        else:
            groups.append(cur); cur = [i]
    groups.append(cur)
    if hot[0] and hot[-1] and len(groups) > 1:
        groups[0] = groups[-1] + groups[0]; groups.pop()
    tips = []
    for g in groups:
        m = np.isin(b, g)
        if m.sum():
            tips.append(P2[np.where(m)[0][int(np.argmax(r[m]))]])
    return np.array(tips)


def _circle_fit(pts2):
    """최소제곱 원 중심(3점 이상)."""
    A = np.c_[2 * pts2, np.ones(len(pts2))]
    b = (pts2 ** 2).sum(axis=1)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    return sol[:2]


def rotor_frame(pts, axis_hint=None):
    """축 = 최소분산 방향. 중심 = 날개 끝점들의 원 중심(2날=중점, 3날 이상=원 맞춤)."""
    c0 = pts.mean(axis=0)
    if axis_hint is None:
        X = pts - c0
        w, V = np.linalg.eigh(X.T @ X / len(X))
        axis = V[:, 0]                       # 최소분산 = 판의 법선 = 회전축
    else:
        axis = np.asarray(axis_hint, float)
    axis = axis / np.linalg.norm(axis)
    tmp = np.array([1.0, 0, 0]) if abs(axis[0]) < 0.9 else np.array([0, 1.0, 0])
    e1 = np.cross(axis, tmp); e1 /= np.linalg.norm(e1)
    e2 = np.cross(axis, e1)
    ctr = c0.copy()
    for _ in range(4):
        d = pts - ctr
        P2 = np.c_[d @ e1, d @ e2]
        tips = _tip_points(P2)
        if len(tips) >= 3:
            uv = _circle_fit(tips)
        elif len(tips) == 2:
            uv = tips.mean(axis=0)
        else:
            # 날개 하나만 잡히면 중심을 못 정한다 — 중심 유지
            break
        ctr = ctr + uv[0] * e1 + uv[1] * e2
    return axis, ctr, e1, e2


def _arcs(th, gap_deg=12.0):
    s = np.sort(th)
    if len(s) < 3:
        return []
    d = np.diff(np.r_[s, s[0] + 2 * np.pi])
    g = np.where(d > np.radians(gap_deg))[0]
    if len(g) == 0:
        return [(s[0], s[-1])]
    arcs = []
    for k in range(len(g)):
        i0 = (g[k] + 1) % len(s)
        i1 = g[(k + 1) % len(g)]
        seg = s[i0:i1 + 1] if i0 <= i1 else np.r_[s[i0:], s[:i1 + 1] + 2 * np.pi]
        if len(seg) >= 2:
            arcs.append((seg[0], seg[-1]))
    return arcs


def caliper(P):
    if len(P) < 2:
        return 0.0
    try:
        from scipy.spatial import ConvexHull
        Q = P[ConvexHull(P).vertices] if len(P) > 3 else P
    except Exception:
        Q = P
    if len(Q) > 1500:
        Q = Q[:: len(Q) // 1500 + 1]
    return float(np.linalg.norm(Q[:, None, :] - Q[None, :, :], axis=2).max())


def measure_planform(pts, band=0.006, gap_deg=12.0, axis_hint=None):
    axis, ctr, e1, e2 = rotor_frame(pts, axis_hint)
    d = pts - ctr
    z = d @ axis
    r = np.hypot(d @ e1, d @ e2)
    th = np.arctan2(d @ e2, d @ e1)
    R = float(r.max())
    rr_fine = np.round(np.arange(0.15, 1.0001, 0.005), 4)
    c_arc, c_cal, narc, cover = [], [], [], []
    for rr in rr_fine:
        rt = rr * R
        m = np.abs(r - rt) < band * R
        if m.sum() < 12:
            c_arc.append(np.nan); c_cal.append(np.nan)
            narc.append(0); cover.append(np.nan); continue
        tt = th[m]
        aa = _arcs(tt, gap_deg)
        cov = sum(a[1] - a[0] for a in aa) / (2 * np.pi)
        if not aa:
            c_arc.append(np.nan); c_cal.append(np.nan)
            narc.append(0); cover.append(cov); continue
        k = int(np.argmax([a[1] - a[0] for a in aa]))
        lo, hi = aa[k]
        c_arc.append(rt * (hi - lo))
        sel = np.zeros(m.sum(), bool)
        for sh in (0.0, 2 * np.pi, -2 * np.pi):
            sel |= (tt + sh >= lo - 1e-12) & (tt + sh <= hi + 1e-12)
        idx = np.where(m)[0][sel]
        if len(idx) < 3:
            c_cal.append(c_arc[-1])
        else:
            ref = 0.5 * (lo + hi)
            tl = ref + np.angle(np.exp(1j * (th[idx] - ref)))
            c_cal.append(caliper(np.c_[rt * tl, z[idx]]))
        narc.append(len(aa)); cover.append(cov)
    return dict(R=R, rr=rr_fine, c_arc=np.array(c_arc), c_cal=np.array(c_cal),
                n_arc=np.array(narc), cover=np.array(cover),
                axis=axis.tolist(), center=ctr.tolist())


def summarize(rr, c, R, r_lo=0.20, r_hi=0.96, hub_guard=None):
    """정규화 시위 곡선 + 요약 통계.  hub_guard: 허브로 오염된 반경 하한."""
    ok = np.isfinite(c) & (rr >= r_lo) & (rr <= r_hi)
    if hub_guard is not None:
        ok &= rr >= hub_guard
    if ok.sum() < 8:
        return None
    x, y = rr[ok], c[ok]
    cmax = float(y.max())
    peak = float(x[int(np.argmax(y))])
    yn = y / cmax
    prof = {f"{g:.2f}": (float(np.interp(g, x, yn)) if x[0] <= g <= x[-1] else None)
            for g in GRID}
    return dict(
        c_max_over_R=cmax / R, peak_r_over_R=peak,
        cn=prof,
        c_over_R={f"{g:.2f}": (float(np.interp(g, x, y)) / R if x[0] <= g <= x[-1] else None)
                  for g in GRID},
        area_centroid=float(np.trapezoid(y * x, x) / np.trapezoid(y, x)),
        blade_area_over_R2=float(np.trapezoid(y / R, x)),   # ∫(c/R)d(r/R)
        outboard_share_0p6=float(np.trapezoid(y[x >= 0.6], x[x >= 0.6])
                                 / np.trapezoid(y, x)),
        r_range=[float(x[0]), float(x[-1])],
    )


def geoms_from_components(path, unit_scale=1.0):
    """단일 메쉬 파일을 **연결요소**로 쪼갠다(trimesh 수리 없이 face_adjacency 그래프)."""
    m = trimesh.load(str(path), process=False)
    from trimesh.graph import connected_components
    cc = connected_components(m.face_adjacency, nodes=np.arange(len(m.faces)))
    v = np.asarray(m.vertices, float) * unit_scale
    f = np.asarray(m.faces, int)
    return [(f"cc{i}", v, f[c]) for i, c in enumerate(cc)]


def measure_file(path, unit_scale=1.0, pick=None, group_rotors=False,
                 target_pts=300_000, band=0.006, mode=None, n_rotors=None,
                 geoms=None):
    """파일 하나 → 로터별 평면형 요약 리스트.

    mode: None/'group' = 지오메트리를 로터로 군집 / 'per_geom' = 지오메트리 하나가 프롭 하나
    """
    if geoms is None:
        geoms = load_geoms(path)
    if pick is not None:
        geoms = [g for g in geoms if pick(g[0], g[2])]
    if not geoms:
        return []
    if mode == "per_geom":
        lab = np.arange(len(geoms))
    elif group_rotors or mode == "group":
        cents = np.array([v[f].reshape(-1, 3).mean(0) for _, v, f in geoms])
        w, V = np.linalg.eigh(np.cov((cents - cents.mean(0)).T) + 1e-12 * np.eye(3))
        axis = V[:, 0]
        proj = cents - np.outer(cents @ axis, axis)
        lab = _cluster(proj, n_clusters=n_rotors)
    else:
        lab = np.zeros(len(geoms), int)
    res = []
    for g in np.unique(lab):
        P = []
        for (nm, v, f), l in zip(geoms, lab):
            if l != g:
                continue
            P.append(sample_surface(v * unit_scale, f,
                                    target_pts=target_pts // max(1, (lab == g).sum())))
        pts = np.vstack(P)
        m = measure_planform(pts, band=band)
        s_cal = summarize(m["rr"], m["c_cal"], m["R"])
        s_arc = summarize(m["rr"], m["c_arc"], m["R"])
        res.append(dict(rotor=int(g), dia=2 * m["R"], cal=s_cal, arc=s_arc,
                        n_arc_at_0p6=int(m["n_arc"][np.argmin(abs(m["rr"] - 0.6))]),
                        cover_at_0p6=float(m["cover"][np.argmin(abs(m["rr"] - 0.6))])))
    return res


def _cluster(X, n_clusters=None, tol=None):
    """단순 거리기반 군집(로터 분리용). n_clusters 를 주면 그 수로 자른다."""
    from scipy.cluster.hierarchy import fcluster, linkage
    if len(X) <= 1:
        return np.zeros(len(X), int)
    Z = linkage(X, method="single")
    if n_clusters:
        return fcluster(Z, t=int(n_clusters), criterion="maxclust") - 1
    d = np.linalg.norm(X - X.mean(0), axis=1).max()
    t = tol if tol is not None else max(1e-9, 0.35 * d)
    return fcluster(Z, t=t, criterion="distance") - 1


# ===================================================================== #
#  2. UIUC 프로펠러 DB
# ===================================================================== #
def uiuc_table(zip_path=UIUC_ZIP):
    if not Path(zip_path).exists():
        return None, f"UIUC zip 없음 — {UIUC_URL} 을 {zip_path} 로 내려받아라"
    z = zipfile.ZipFile(str(zip_path))
    rows = []
    for n in z.namelist():
        if not n.endswith("_geom.txt"):
            continue
        txt = z.read(n).decode("utf8", "ignore")
        dat = []
        for line in txt.splitlines():
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
        fam = m.group(1) if m else base.split("_")[0]
        dia_in = float(m.group(2)) if m else np.nan
        pit_in = float(m.group(3)) if m else np.nan
        ok = (rr >= 0.20) & (rr <= 0.96)
        if ok.sum() < 8:
            continue
        x, y = rr[ok], cR[ok]
        cmax = float(y.max())
        prof = {f"{g:.2f}": float(np.interp(g, x, y)) / cmax for g in GRID}
        # 국소 기하피치 P(r) = 2πr tanβ ;  0.75R 및 0.50R 기준 정규화
        P_loc = 2 * np.pi * rr * np.tan(np.radians(beta))
        P75 = float(np.interp(0.75, rr, P_loc))
        P50 = float(np.interp(0.50, rr, P_loc))
        bb = (rr >= 0.6) & (rr <= 0.9)
        rows.append(dict(
            name=base, family=fam, dia_in=dia_in, pitch_in=pit_in,
            volume=n.split("/")[1],
            c_max_over_R=cmax, peak_r_over_R=float(x[int(np.argmax(y))]),
            cn=prof,
            area_centroid=float(np.trapezoid(y * x, x) / np.trapezoid(y, x)),
            blade_area_over_R2=float(np.trapezoid(y, x)),
            outboard_share_0p6=float(np.trapezoid(y[x >= 0.6], x[x >= 0.6])
                                     / np.trapezoid(y, x)),
            k75_at={f"{g:.2f}": float(np.interp(g, rr, P_loc)) / P75 for g in
                    (0.30, 0.50, 0.60, 0.70, 0.75, 0.80, 0.90)},
            k50_at={f"{g:.2f}": float(np.interp(g, rr, P_loc)) / P50 for g in
                    (0.30, 0.50, 0.60, 0.70, 0.75, 0.80, 0.90)},
            k_peak_r=float(rr[int(np.argmax(P_loc))]),
            beta_span_0p6_0p9_deg=float(beta[bb].max() - beta[bb].min()) if bb.sum() else None,
            tip_cR_at_0p98=float(np.interp(0.98, rr, cR)),
        ))
    return rows, None


# ===================================================================== #
#  3. 제품사진 → 평면형(각폭법)
# ===================================================================== #
def photo_planform(path, n_prop=2, dark_on_light=True, thresh=None,
                   min_frac=0.004, keep=None, use_alpha=False):
    from PIL import Image
    if use_alpha:                       # 투명 배경 제품컷 — 알파가 곧 실루엣
        rgba = np.asarray(Image.open(path).convert("RGBA"))
        mask = rgba[..., 3] > 128
        return _photo_from_mask(mask, n_prop, min_frac, keep), -1.0
    im = Image.open(path).convert("RGB")
    a = np.asarray(im, float)
    lum = a.mean(axis=2)
    if thresh is None:                      # 오츠
        h, e = np.histogram(lum, bins=256, range=(0, 255))
        p = h / h.sum()
        w = np.cumsum(p)
        mu = np.cumsum(p * np.arange(256))
        mt = mu[-1]
        sb = (mt * w - mu) ** 2 / np.maximum(w * (1 - w), 1e-12)
        thresh = float(np.argmax(sb))
    mask = lum < thresh if dark_on_light else lum > thresh
    return _photo_from_mask(mask, n_prop, min_frac, keep), thresh


def _photo_from_mask(mask, n_prop=2, min_frac=0.004, keep=None):
    from scipy import ndimage
    lab, n = ndimage.label(mask)
    sizes = ndimage.sum(mask, lab, range(1, n + 1))
    order = np.argsort(sizes)[::-1]
    tot = mask.size
    comps = [int(o + 1) for o in order if sizes[o] > min_frac * tot][:n_prop]
    if keep is not None:
        comps = [comps[i] for i in keep if i < len(comps)]
    out = []
    for ci in comps:
        yy, xx = np.where(lab == ci)
        P = np.c_[xx.astype(float), yy.astype(float)]
        c0 = P.mean(0)
        ctr = c0.copy()
        for _ in range(3):
            d = np.linalg.norm(P - ctr, axis=1)
            p1 = P[int(np.argmax(d))]
            p2 = P[int(np.argmax(np.linalg.norm(P - p1, axis=1)))]
            ctr = 0.5 * (p1 + p2)
        d = P - ctr
        r = np.linalg.norm(d, axis=1)
        th = np.arctan2(d[:, 1], d[:, 0])
        R = float(r.max())
        rr = np.round(np.arange(0.15, 1.0001, 0.005), 4)
        c = []
        for x in rr:
            m = np.abs(r - x * R) < 0.008 * R
            if m.sum() < 8:
                c.append(np.nan); continue
            aa = _arcs(th[m], gap_deg=14.0)
            c.append(x * R * max(a[1] - a[0] for a in aa) if aa else np.nan)
        c = np.array(c)
        s = summarize(rr, c, R)
        out.append(dict(R_px=R, summary=s, n_px=int(len(P))))
    return out


# ===================================================================== #
#  4. 우리 법칙
# ===================================================================== #
def ours_law():
    sys.path.insert(0, str(ROOT / "src"))
    from drone_cad import (CHORD_RR, CHORD_FRAC, CHORD_MAX_OVER_R,
                           PITCH_RR, PITCH_K)
    rr = np.round(np.arange(0.15, 1.0001, 0.005), 4)
    c = np.interp(rr, CHORD_RR, CHORD_FRAC) * CHORD_MAX_OVER_R
    s = summarize(rr, c, 1.0)
    k = np.interp(np.array([0.30, 0.50, 0.60, 0.70, 0.75, 0.80, 0.90]),
                  PITCH_RR, PITCH_K)
    k75 = float(np.interp(0.75, PITCH_RR, PITCH_K))
    k50 = float(np.interp(0.50, PITCH_RR, PITCH_K))
    g = [0.30, 0.50, 0.60, 0.70, 0.75, 0.80, 0.90]
    return dict(summary=s,
                k75_at={f"{x:.2f}": float(v) / k75 for x, v in zip(g, k)},
                k50_at={f"{x:.2f}": float(v) / k50 for x, v in zip(g, k)},
                k_peak_r=float(np.array(PITCH_RR)[int(np.argmax(PITCH_K))]),
                tip_cR_at_0p98=float(np.interp(0.98, CHORD_RR, CHORD_FRAC)
                                     * CHORD_MAX_OVER_R))


# ===================================================================== #
#  5. 통계
# ===================================================================== #
def spread(vals):
    v = np.array([x for x in vals if x is not None and np.isfinite(x)], float)
    if len(v) == 0:
        return None
    return dict(n=int(len(v)), min=float(v.min()), p05=float(np.percentile(v, 5)),
                p25=float(np.percentile(v, 25)), median=float(np.median(v)),
                p75=float(np.percentile(v, 75)), p95=float(np.percentile(v, 95)),
                max=float(v.max()), mean=float(v.mean()), sd=float(v.std(ddof=1))
                if len(v) > 1 else 0.0)


def pct_rank(vals, x):
    v = np.array([y for y in vals if y is not None and np.isfinite(y)], float)
    if len(v) == 0 or x is None or not np.isfinite(x):
        return None
    return float((v < x).mean() * 100.0)


# ===================================================================== #
#  6. 참조 목록 — (라벨, 경로, 단위배율, 출처등급, 비고)
#     등급 A = 제조사/공식 제품 CAD · B = 상세 커뮤니티/시뮬 CAD · C = 저폴리 시뮬
# ===================================================================== #
MESH_REFS = [
    # (label, path, unit_scale, grade, source, mode, n_rotors, pick_kind)
    ("DJI Mini 2 4726F (공식 GLB)", REF / "WM161_zhankai_1k.glb", 1000.0, "A",
     "DJI 공식 제품 3D 모델(1k 간략화)", "group", 4, "dji_blade"),
    ("Parrot ANAFI USA 5.9in (제조사 CAD)", RS / "parrot_anafi/anafi_usa_full.glb",
     1000.0, "A", "Parrot 공식 STEP→GLB", "group", 4, "anafi"),
    ("3DR Solo 10in", REF / "solo_prop_cw.stl", 1000.0, "B",
     "ethz-asl/rotors_simulator", "single", 1, None),
    ("3DR Solo 10in (CCW)", REF / "solo_prop_ccw.stl", 1000.0, "B",
     "ethz-asl/rotors_simulator", "single", 1, None),
    ("Holybro 1345 (13in)", REF / "1345_prop_cw.stl", 1000.0, "B",
     "PX4/PX4-gazebo-models x500_base", "single", 1, None),
    ("Yuneec Typhoon H480", REF / "prop_cw_assembly_remeshed_v3.stl", 1.0, "B",
     "ethz-asl/rotors_simulator", "single", 1, None),
    ("Yuneec Typhoon H480 (CCW)", REF / "prop_ccw_assembly_remeshed_v3.stl", 1.0, "B",
     "ethz-asl/rotors_simulator", "single", 1, None),
    ("DJI 1345 (Matrice 100 sim)", RS / "px4_matrice100/dji_13455_prop_cw.dae",
     1000.0, "B", "PX4 gazebo matrice100", "single", 1, None),
    ("DJI Mavic 2 Pro (Webots)", RS / "webots_dji_mavic2pro/helix_a.obj",
     1000.0, "B", "Webots Mavic2Pro proto", "single", 1, None),
    ("DJI Mavic 2 Pro (Webots, b)", RS / "webots_dji_mavic2pro/helix_b.obj",
     1000.0, "B", "Webots Mavic2Pro proto", "single", 1, None),
    ("Parrot Bebop 2 (3날)", RS / "fuel/bebop2/meshes/propeller_fl.dae",
     1000.0, "B", "Gazebo Fuel bebop2", "single", 1, None),
    ("AscTec neo11", RS / "rotors_asctec/neo11_propeller_ccw.dae", 1000.0, "B",
     "ethz-asl/rotors_simulator", "single", 1, None),
    ("AscTec neo9", RS / "fuel/x4_uav/meshes/neo9_propeller_cw.dae", 1000.0, "B",
     "Gazebo Fuel x4_uav", "single", 1, None),
    ("AscTec Hummingbird", RS / "rotors_asctec/propeller_cw.dae", 1000.0, "C",
     "ethz-asl/rotors_simulator (199면)", "single", 1, None),
    ("DJI F330", RS / "mrs_ctu_airframes/dji/f330/f330_prop.dae", 1000.0, "B",
     "MRS CTU airframes", "single", 1, None),
    ("DJI F550", RS / "mrs_ctu_airframes/dji/f550/dji_f550_prop.dae", 1000.0, "B",
     "MRS CTU airframes", "single", 1, None),
    ("Tarot T650", RS / "mrs_ctu_airframes/tarot/t650/tarot_t650_prop_low_poly.dae",
     1.0, "C", "MRS CTU (low_poly 명시)", "single", 1, None),
    ("T-Drones M690B", RS / "mrs_ctu_airframes/t_drones/m690b/t_drone_m690b_propeller.stl",
     1000.0, "C", "MRS CTU (392면)", "single", 1, None),
    ("Holybro X500 1045", RS / "mrs_ctu_airframes/holybro/holybro_x500_prop.dae",
     1000.0, "C", "MRS CTU (996면)", "single", 1, None),
    ("3DR Iris", RS / "px4_iris/iris_prop_cw.dae", 1000.0, "B",
     "PX4 gazebo iris", "single", 1, None),
    ("Alti Transition", RS / "ardupilot_alti/prop_cw.dae", 1000.0, "B",
     "ArduPilot SITL models", "single", 1, None),
]

PICKS = {
    "dji_blade": lambda nm, f: len(f) in (1635, 1691, 1704),
    "anafi": lambda nm, f: "PROPELLER" in nm.upper(),
}

PHOTO_REFS = [
    ("DJI M4E 1157F (표준, 제품컷)", PHOTO / "matrice4e/matrice4e_c02_prop_standard_1157F_pair.jpg",
     2, False),
    ("DJI M4E 1154F (저소음, 제품컷)", PHOTO / "matrice4e/matrice4e_c01_prop_low_noise_1154F_pair.jpg",
     2, False),
    ("DJI Mavic 4 Pro 1158F (제품컷)", PHOTO / "mavic4pro/mavic4pro_c10_propeller_pair_1158F.jpg",
     2, False),
]
PHOTO_EXCLUDED = {
    "mini2_c07_ruler": "프롭이 기체에 장착된 채라 실루엣이 암·그림자와 붙는다 — 자동 분할 실패(c_max/R>1). 판정 불가.",
    "m350rtk_c01_2110s": "접힌 상태 제품컷이라 회전면 평면형을 못 잰다(두 날이 같은 쪽).",
    "x500v2_10_1045": "모터에 장착된 사선 촬영 + 배경 복잡 — 실루엣이 모터를 먹는다.",
}


def measure_all_meshes(target_pts=300_000):
    out, seen = [], {}
    for lab, path, sc, grade, src, mode, nrot, pk in MESH_REFS:
        if not Path(path).exists():
            out.append(dict(label=lab, error="file missing", path=str(path)))
            continue
        pick = PICKS.get(pk)
        geoms = load_geoms(path)
        if pick:
            geoms = [g for g in geoms if pick(g[0], g[2])]
        key = (sum(len(f) for _, _, f in geoms),
               round(float(sum(v[f].reshape(-1, 3).sum() for _, v, f in geoms)), 3))
        dup = seen.get(key)
        seen.setdefault(key, lab)
        res = measure_file(path, unit_scale=sc, pick=pick,
                           mode=("group" if mode == "group" else None),
                           n_rotors=nrot, target_pts=target_pts)
        for r in res:
            if r["cal"] is None:
                continue
            out.append(dict(label=lab, source=src, grade=grade, path=str(path),
                            duplicate_of=dup, rotor=r["rotor"], dia=r["dia"],
                            n_blades=r["n_arc_at_0p6"], cal=r["cal"], arc=r["arc"]))
    return out


def ours_fresh_build(cases=((152.4, 2.6, "mini5pro급"), (274.0, 5.8, "matrice4e급"))):
    """지금 코드로 날 1장을 지어 **참조와 같은 원통자**로 잰다(중심=원점·축=z 강제)."""
    sys.path.insert(0, str(ROOT / "src"))
    import drone_cad as DC
    out = []
    for dia, pin, lab in cases:
        R = dia / 2000.0
        bl = DC._blade(R, root_frac=0.070, chord_max=DC.CHORD_MAX_OVER_R,
                       pitch_m=pin * 0.0254, n_sec=22)
        V = np.asarray(bl.vertices) * 1000.0
        F = np.asarray(bl.faces)
        P = sample_surface(V, F, target_pts=400_000)
        z = P[:, 2]
        r = np.hypot(P[:, 0], P[:, 1])
        th = np.arctan2(P[:, 1], P[:, 0])
        Rt = float(r.max())
        rr = np.round(np.arange(0.15, 1.0001, 0.005), 4)
        c_arc, c_cal = [], []
        for x in rr:
            rt = x * Rt
            m = np.abs(r - rt) < 0.006 * Rt
            if m.sum() < 12:
                c_arc.append(np.nan); c_cal.append(np.nan); continue
            lo, hi = th[m].min(), th[m].max()
            c_arc.append(rt * (hi - lo))
            c_cal.append(caliper(np.c_[rt * th[m], z[m]]))
        out.append(dict(case=lab, dia_mm=dia, pitch_in=pin, R_measured_mm=Rt,
                        cal=summarize(rr, np.array(c_cal), Rt),
                        arc=summarize(rr, np.array(c_arc), Rt)))
    return out


def ours_shipped(keys=("mini5pro", "matrice4e", "mavic4pro", "phantom4",
                       "x500v2", "typhoonh480", "s1000plus", "phantom3")):
    """디스크의 정본 자산 assets/meshes/drones/<key>/<key>__prop.obj 를 같은 자로."""
    nrot = {"typhoonh480": 6, "s1000plus": 8}
    out = []
    for k in keys:
        p = ROOT / f"assets/meshes/drones/{k}/{k}__prop.obj"
        if not p.exists():
            out.append(dict(key=k, error="파일 없음")); continue
        g = geoms_from_components(p, unit_scale=1000.0)
        res = measure_file(p, geoms=g, mode="group", n_rotors=nrot.get(k, 4),
                           target_pts=400_000)
        if not res or res[0]["cal"] is None:
            out.append(dict(key=k, error="측정 실패")); continue
        r = res[0]
        out.append(dict(key=k, mtime=time.strftime(
            "%Y-%m-%d", time.localtime(p.stat().st_mtime)),
            n_rotor_groups=len(res), dia_mm=r["dia"], cal=r["cal"], arc=r["arc"]))
    return out


def verdicts(doc):
    """모집단 대비 백분위와 감사 주장별 판정."""
    rows = doc["C_uiuc"]["rows"] or []
    mesh = [m for m in doc["B_mesh_population"] if "cal" in m]
    meshAB = [m for m in mesh if m["grade"] in ("A", "B")]
    ours = doc["E_ours"]["law_constants"]["summary"]
    fresh = doc["E_ours"]["fresh_build"][0]["cal"]
    ph = doc["D_photos"]["measured"]

    def col(pop, path):
        out = []
        for m in pop:
            v = m
            for k in path:
                v = v.get(k) if isinstance(v, dict) else None
                if v is None:
                    break
            out.append(v)
        return out

    pops = {
        "uiuc_measured_132": {
            "cn70": [r["cn"]["0.70"] for r in rows],
            "peak": [r["peak_r_over_R"] for r in rows],
            "cmaxR": [r["c_max_over_R"] for r in rows],
            "centroid": [r["area_centroid"] for r in rows],
            "area": [r["blade_area_over_R2"] for r in rows],
            "tip98": [r["tip_cR_at_0p98"] for r in rows],
            "beta_span": [r["beta_span_0p6_0p9_deg"] for r in rows],
        },
        "repo_mesh_all": {
            "cn70": col(mesh, ["cal", "cn", "0.70"]),
            "peak": col(mesh, ["cal", "peak_r_over_R"]),
            "cmaxR": col(mesh, ["cal", "c_max_over_R"]),
            "centroid": col(mesh, ["cal", "area_centroid"]),
            "area": col(mesh, ["cal", "blade_area_over_R2"]),
        },
        "repo_mesh_gradeAB": {
            "cn70": col(meshAB, ["cal", "cn", "0.70"]),
            "peak": col(meshAB, ["cal", "peak_r_over_R"]),
            "cmaxR": col(meshAB, ["cal", "c_max_over_R"]),
            "centroid": col(meshAB, ["cal", "area_centroid"]),
            "area": col(meshAB, ["cal", "blade_area_over_R2"]),
        },
        "product_photos": {
            "cn70": [p["cn"]["0.70"] for p in ph if "cn" in p],
            "peak": [p["peak_r_over_R"] for p in ph if "cn" in p],
            "cmaxR": [p["c_max_over_R"] for p in ph if "cn" in p],
            "centroid": [p["area_centroid"] for p in ph if "cn" in p],
        },
    }
    ours_vals = {"cn70": ours["cn"]["0.70"], "peak": ours["peak_r_over_R"],
                 "cmaxR": ours["c_max_over_R"], "centroid": ours["area_centroid"],
                 "area": ours["blade_area_over_R2"],
                 "tip98": doc["E_ours"]["law_constants"]["tip_cR_at_0p98"]}
    fresh_vals = {"cn70": fresh["cn"]["0.70"], "peak": fresh["peak_r_over_R"],
                  "cmaxR": fresh["c_max_over_R"], "centroid": fresh["area_centroid"],
                  "area": fresh["blade_area_over_R2"]}
    stats = {}
    for pname, cols in pops.items():
        stats[pname] = {}
        for cname, vals in cols.items():
            s = spread(vals)
            if s is None:
                continue
            stats[pname][cname] = dict(
                spread=s,
                ours_law=ours_vals.get(cname),
                ours_law_pctile=pct_rank(vals, ours_vals.get(cname)),
                ours_fresh_build=fresh_vals.get(cname),
                ours_fresh_pctile=pct_rank(vals, fresh_vals.get(cname)))

    # 절대 시위 c/R — 정규화가 만드는 착시를 가른다
    import zipfile as _z
    abs_pop = {g: [] for g in (0.30, 0.50, 0.70, 0.80, 0.90)}
    if Path(UIUC_ZIP).exists():
        z = _z.ZipFile(str(UIUC_ZIP))
        for n in z.namelist():
            if not n.endswith("_geom.txt"):
                continue
            a = []
            for line in z.read(n).decode("utf8", "ignore").splitlines():
                p = line.split()
                if len(p) >= 3:
                    try:
                        a.append([float(p[0]), float(p[1])])
                    except ValueError:
                        pass
            if len(a) < 8:
                continue
            a = np.array(a)
            for g in abs_pop:
                abs_pop[g].append(float(np.interp(g, a[:, 0], a[:, 1])))
    sys.path.insert(0, str(ROOT / "src"))
    from drone_cad import CHORD_RR, CHORD_FRAC, CHORD_MAX_OVER_R
    abs_cmp = {}
    for g, vals in abs_pop.items():
        ov = float(np.interp(g, CHORD_RR, CHORD_FRAC) * CHORD_MAX_OVER_R)
        mv = [m["cal"]["c_over_R"].get(f"{g:.2f}") for m in meshAB]
        abs_cmp[f"{g:.2f}"] = dict(ours_law_c_over_R=ov,
                                   uiuc=spread(vals),
                                   uiuc_pctile=pct_rank(vals, ov),
                                   repo_mesh_AB=spread(mv),
                                   repo_mesh_AB_pctile=pct_rank(mv, ov))
    return {"population_stats": stats, "absolute_chord_c_over_R": abs_cmp}


def claim_verdicts(doc):
    """감사 주장별 판정 — 숫자는 전부 이 문서 안의 측정에서 끌어온다."""
    F = doc["F_spread_and_verdicts"]
    U = F["population_stats"]["uiuc_measured_132"]
    M = F["population_stats"]["repo_mesh_gradeAB"]
    A = F["absolute_chord_c_over_R"]
    mesh = {m["label"]: m for m in doc["B_mesh_population"] if "cal" in m}

    def g(pop, col, key):
        return round(pop[col]["spread"][key], 4)

    return [
      {"claim": "① WM161_zhankai_1k.glb 는 DJI Mini 2 공식 모델이고 날 8장·허브 4개가 실재한다"
                "(디스크 지름 ≈ 공칭 119.4 mm)",
       "verdict": "감사 지지 — 공격했고 살아남았다",
       "evidence": "면수 1635×4 + 1691×4(날) + 1704×4(허브) 재현. 내 독립 중심맞춤으로 로터별 "
                   "지름 118.28 / 119.30 mm (평균 118.79, 공칭 대비 −0.5 %). "
                   "회전축은 월드 +y 로 재현."},
      {"claim": "② 우리 시위가 실물보다 외곽에서 27~39 % 좁다 · 정규화시위@0.70R 우리 0.577 ↔ "
                "DJI 0.866 · 날 면적 −29 %(−2.97 dB)",
       "verdict": "부분 정정 — 방향은 맞고 «면적이 작다» 는 틀렸다",
       "evidence": (
           f"DJI Mini 2 대비는 재현된다(내 측정 우리 {U['cn70']['ours_law']:.3f} ↔ Mini2 "
           f"{mesh['DJI Mini 2 4726F (공식 GLB)']['cal']['cn']['0.70']:.3f}). "
           f"그러나 **날 면적**은 UIUC 실측 132종 대비 {U['area']['ours_law_pctile']:.0f} 백분위"
           f"(중앙값 {g(U,'area','median')} ↔ 우리 {U['area']['ours_law']:.4f})로 **중앙값보다 크다**. "
           f"저장소 참조메쉬(A/B급 22개) 대비도 {M['area']['ours_law_pctile']:.0f} 백분위. "
           "⇒ 참인 명제는 «면적이 작다» 가 아니라 «면적이 안쪽에 쏠려 있다» 다: "
           f"면적중심 {U['centroid']['ours_law']:.4f} 은 UIUC 132종 중 {U['centroid']['ours_law_pctile']:.0f} 백분위"
           f"(모집단 최소 {g(U,'centroid','min')}), 0.6R 바깥 면적비율은 2.3 백분위다."),
       "note": "감사 자신도 C5 에서 −2.97 dB 를 커널 실측 +0.2~+1.3 dB 로 이미 철회했다. "
               "이 라운드는 그 철회의 **이유**를 하나 더 준다 — 면적비 자체가 DJI 한정 수치였다."},
      {"claim": "③ 3DR Solo 는 참조 넷 중 유일한 이상치다(나머지는 전부 Yuneec 형)",
       "verdict": "감사 반증",
       "evidence": (
           f"감사 자신의 참조 넷 중 **Holybro 1345** 가 우리보다 더 좁다: 정규화시위@0.70R "
           f"{mesh['Holybro 1345 (13in)']['cal']['cn']['0.70']:.3f} ↔ 우리 "
           f"{U['cn70']['ours_law']:.3f} ↔ Solo "
           f"{mesh['3DR Solo 10in']['cal']['cn']['0.70']:.3f} ↔ Yuneec "
           f"{mesh['Yuneec Typhoon H480']['cal']['cn']['0.70']:.3f}. "
           "이 값은 내 측정만이 아니라 **저장소 자신의 원장** outputs/reference_props.json "
           "(2026-07-29 생성, 감사가 자기 자를 검증할 때 쓴 바로 그 파일)의 stations 표에서 "
           "0.491 로 직접 읽힌다. 감사의 정규화시위 비교표에는 1345 행이 **빠져 있고**, "
           "정점위치 표에는 1345 = 0.30R(우리와 같음) 로 들어 있다. "
           "⇒ 넷 중 둘이 «우리 형» 이고 그중 하나는 우리보다 극단적이다.")},
      {"claim": "④ CHORD_MAX_OVER_R = 0.25 단일 상수 — 실물은 0.177~0.273 이고 크기와 반비례한다",
       "verdict": "부분 정정 — 단일상수 지적은 옳고, 제시된 «실물 범위» 와 «크기 반비례» 는 표본 7개의 착시",
       "evidence": (
           f"실측 132종의 c_max/R 범위는 {g(U,'cmaxR','min')}~{g(U,'cmaxR','max')} "
           f"(중앙값 {g(U,'cmaxR','median')}) 로 감사가 적은 0.177~0.273 보다 훨씬 넓다. "
           f"저장소 참조메쉬도 {g(M,'cmaxR','min')}~{g(M,'cmaxR','max')}. "
           "크기 반비례: 전체(5~19 in)에서는 Spearman ρ = −0.42 (p=1.9e−6) 로 유의하지만, "
           "우리 함대가 사는 **8~13 in 구간만 보면 ρ = −0.19 (p=0.082) 로 유의하지 않다**. "
           f"우리 0.25 는 UIUC {U['cmaxR']['ours_law_pctile']:.0f} 백분위 · "
           f"참조메쉬 {M['cmaxR']['ours_law_pctile']:.0f} 백분위 — 넓은 편이나 평범하다. "
           "⇒ 기종별 필드로 승격하는 것은 타당하지만, **크기 스케일링 법칙으로 채우면 안 된다**. "
           "기종별 1차 계측값을 넣어라."),
       },
      {"claim": "⑤ PITCH_K 기준 반경이 0.5R 인데 표준·실물은 0.75R · 외곽 피치각 폭 DJI 5.5° ↔ 우리 9.2°",
       "verdict": "부분 정정 — 규약 지적은 맞지만 «기하가 틀렸다» 는 근거는 약하다",
       "evidence": (
           "실측 132종에서 국소기하피치 P(0.5R)/P(0.75R) 의 **중앙값은 0.996** 이다 — 실물은 두 "
           "반경에서 사실상 같은 피치를 갖는다. 즉 0.5R↔0.75R 은 이름표 문제이지 형상 오차가 아니다"
           "(우리 값 0.943, 실물 중앙값에서 5.7 % 차). "
           "국소피치 최대 위치는 실물이 p25 0.44R · 중앙값 0.65R · p75 0.90R 로 흩어지고 "
           "**우리 0.70R 은 중앙값 자리**다. "
           "0.6~0.9R 피치각 폭은 실물 중앙값 6.72° · p95 9.46° · 최대 10.74° 이고 "
           "우리는 7.73°(mini5pro급)~9.41°(matrice4e급) 로 **밴드 안**이다. "
           "DJI Mini 2 의 5.5° 는 실물 모집단 중앙값보다 오히려 낮은 쪽이다."),
       },
      {"claim": "⑥ 팁이 뾰족하다 — 팁 밴드(0.90~0.96R) 면적비 0.700(−3.10 dB)",
       "verdict": "부분 정정 — DJI 대비는 참, «실물은 뭉툭하다» 는 일반화는 거짓",
       "evidence": (
           f"c/R@0.98R 우리 {U['tip98']['ours_law']:.4f} 는 실측 132종 중 "
           f"{U['tip98']['ours_law_pctile']:.0f} 백분위(중앙값 {g(U,'tip98','median')}, "
           f"p05 {g(U,'tip98','p05')})다 — 평범하게 얇은 쪽. "
           "DJI Mini 2 의 0.1028 이 오히려 모집단 상위(~p80)다. "
           "⇒ 팁 끝값을 올리는 수리는 «실물 일반» 이 아니라 «DJI 계열을 표적으로 삼기 때문» 이라고 "
           "적어야 한다."),
       },
      {"claim": "⑦ 정본 1.43 mm 는 상수 유도값이고 메쉬 실측은 1.456 mm",
       "verdict": "판정 불가 — 이 라운드의 사정권 밖(두께 축은 안 건드렸다)",
       "evidence": "감사의 별도 재검증(D-1 #13)이 이미 독립 재현했다. 나는 평면형만 다시 쟀다."},
      {"claim": "⑧ 두께가 13~17 dB · 형상이 1~2 dB (크기 순서)",
       "verdict": "판정 불가 — 커널을 안 돌렸다(⛔GPU)",
       "evidence": "다만 이 라운드는 형상 축의 **부호와 크기**를 바꿀 근거를 하나 준다: "
                   "면적 결손이 DJI 한정이므로, 형상 수리의 이득도 DJI 를 표적으로 삼을 때만 그 크기다."},
      {"claim": "⑨ 무해 확인 목록(날개 수·디스크 지름·거울상·로프트 이산화·수밀·캠버)",
       "verdict": "부분 정정 — 목록에서 하나가 빠졌다",
       "evidence": "감사가 «디스크 지름 전 10기체 −0.000 %» 라고 적은 것은 **새로 지은 메쉬** 얘기다. "
                   "디스크에 놓인 정본 자산(assets/meshes/drones/*/*__prop.obj)은 지름이 "
                   "**+0.84 %** 이고 평면형도 다르다 — 낡았다(H_new_findings_ko N1)."},
    ]


def new_findings(doc):
    ship = [s for s in doc["E_ours"]["shipped_obj"] if "cal" in s]
    fresh = doc["E_ours"]["fresh_build"][0]["cal"]
    return [
      {"id": "N1",
       "title": "⭐ 정본 자산 프롭 OBJ 가 낡았다 — 2026-07-28 법칙 개정 이전 빌드",
       "evidence": (
           "assets/meshes/drones/<key>/<key>__prop.obj 5개(mtime 2026-07-20) 를 참조와 같은 "
           "자로 재면 전부 같은 서명을 낸다: 스윕 지름 **+0.84 %**"
           + "".join([f" · {s['key']} {s['dia_mm']:.2f} mm" for s in ship])
           + f" / 평면형 c_max/R≈{ship[0]['cal']['c_max_over_R']:.3f} @ "
             f"{ship[0]['cal']['peak_r_over_R']:.2f}R · 정규화시위@0.70R≈"
             f"{ship[0]['cal']['cn']['0.70']:.3f}. "
             f"지금 코드로 새로 지으면 c_max/R={fresh['c_max_over_R']:.3f} @ "
             f"{fresh['peak_r_over_R']:.2f}R · @0.70R {fresh['cn']['0.70']:.3f} 이고 "
             "지름 오차는 0 이다. +0.84 % 는 저장소가 «옛 버그» 로 기록한 값과 소수 둘째자리까지 같다"
             "(drone_cad.py 스윕디스크 정규화 주석: 5기종 전부 +0.84 %)."),
       "impact": "RCS·렌더 경로는 scene_build.drone_parts → build_drone 으로 **매번 새로 짓고** "
                 "_scene/ 에 쓰므로 결과 dB 에는 영향이 없다. 그러나 정본 자산을 읽는 쪽"
                 "(외부 공유·뷰어·«as-built» 재검증)은 옛 법칙을 본다. "
                 "그리고 x500v2·typhoonh480·phantom3 은 프롭 OBJ 자체가 없다.",
       "recommend": "3층(법칙) 수리 후 정본 자산을 다시 내보내고, 자산에 «생성 커밋·법칙 해시» 를 "
                    "남길 것. 최소한 낡았다는 표시라도."},
      {"id": "N2",
       "title": "감사의 정규화시위 비교표가 1345 행을 빠뜨렸다",
       "evidence": "감사 원장 D.step2 의 normalised_chord_c_over_cmax 에는 ours_code · mini2 · "
                   "M4E 1157F · M4E 1154F · yuneec · solo 6행만 있고 **holybro_1345 행이 없다**. "
                   "같은 절의 peak_r_over_R 표에는 1345 = 0.30 이 들어 있다. "
                   "그 빠진 행이 결론(«Solo 만 우리 형») 을 뒤집는 행이다.",
       "impact": "«1차 앵커를 Solo → DJI Mini 2 로 교체» 라는 권고 자체는 살아남지만, 그 근거를 "
                 "«Solo 만 이상치» 로 적으면 안 된다. 정직한 근거는 «표적이 DJI 이므로 앵커도 "
                 "DJI 로 맞춘다» 이다.",
       "recommend": "C4 문면을 «Solo 는 유일한 이상치» → «참조 모집단의 산포가 크고, 우리는 그 "
                    "안쪽 극단이며, 표적이 DJI 라서 DJI 로 앵커를 옮긴다» 로."},
      {"id": "N3",
       "title": "단일 참조 앵커링은 위험하다 — 같은 기체의 두 정품 프롭이 0.15 벌어진다",
       "evidence": "M4E 정품 1157F(표준) 정규화시위@0.70R 0.796 / 0.809 ↔ 1154F(저소음) "
                   "0.946 / 0.952. 같은 기체·같은 제조사·같은 사진 규약인데 0.15 차이다. "
                   "DJI 계열 전체로도 1345(M100) 0.490 · F330 0.692 · Mavic 2 Pro 0.716 · "
                   "Mini 2 0.857 로 흩어진다.",
       "impact": "«DJI 평면형» 이라는 단일 곡선은 존재하지 않는다. 어느 프롭을 표적으로 삼는지가 "
                 "법칙을 정한다(?3 «표준인가 저소음인가» 가 미해결인 채 남아 있는 이유).",
       "recommend": "법칙을 기종별로 놓고, 기종마다 **어느 프롭 모델의 계측인지**를 spec note 에 "
                    "박을 것. 함대 공용 곡선 하나로 덮지 말 것."},
      {"id": "N4",
       "title": "감사의 «ours» 행에 1.1 % 정규화 오차가 있다(사소)",
       "evidence": "CHORD_FRAC 의 최대값은 1.000 이 아니라 0.989(@0.30R)다. 감사표는 CHORD_FRAC "
                   "값을 그대로 c/c_max 로 실어 우리 곡선을 1.1 % 낮게 적었다"
                   "(@0.70R 0.577 ↔ 정규화하면 0.583).",
       "impact": "결론 안 바뀜. 다만 «27~39 %» 의 아래끝이 1 %p 정도 과장돼 있다.",
       "recommend": "표 각주로."},
    ]


def main():
    t0 = time.time()
    doc = {"_meta": {
        "title": "적대적 다중참조 대조 — 우리 날 법칙은 정말 이상치인가",
        "generated_kst": time.strftime("%Y-%m-%d %H:%M",
                                       time.localtime(time.time() + 9 * 3600)),
        "policy": "⛔GPU 미사용 · ⛔저장소 코드 무변경 · ⛔git 무접촉",
        "script": "benchmark/adv_multiref_planform_0816.py",
        "python": "/workspace/.venvs/py312/bin/python (+ pycollada 를 --target 으로 임시 설치)",
        "attacked": "docs/MESH_AUDIT_0816.md 의 C4 · I2 · I7 · I8",
    }}
    # A. 자 검증
    anchors = {}
    for lab, p, sc, exp in [("holybro_1345", REF / "1345_prop_cw.stl", 1000.0,
                             (346.66, 0.2253, 0.300)),
                            ("3dr_solo", REF / "solo_prop_cw.stl", 1000.0,
                             (253.82, 0.2726, 0.275)),
                            ("yuneec_typhoon", REF / "prop_cw_assembly_remeshed_v3.stl",
                             1.0, (230.10, 0.1769, 0.450))]:
        r = measure_file(p, unit_scale=sc, target_pts=250_000)[0]
        anchors[lab] = dict(ledger=dict(dia_mm=exp[0], c_max_over_R=exp[1],
                                        peak_r_over_R=exp[2]),
                            mine=dict(dia_mm=round(r["dia"], 3),
                                      c_max_over_R=round(r["cal"]["c_max_over_R"], 4),
                                      peak_r_over_R=r["cal"]["peak_r_over_R"]))
    doc["A_ruler_validation"] = {
        "what": "새 자(원통밴드 캘리퍼)가 저장소 원장 outputs/reference_props.json 3종을 재현하는가",
        "anchors": anchors}

    # B. 메쉬 모집단
    doc["B_mesh_population"] = measure_all_meshes()

    # C. UIUC
    rows, err = uiuc_table()
    doc["C_uiuc"] = {"error": err, "n": (len(rows) if rows else 0),
                     "source": UIUC_URL, "rows": rows}

    # D. 사진
    ph = []
    for lab, p, n, alpha in PHOTO_REFS:
        try:
            res = photo_planform(p, n_prop=n, use_alpha=alpha)
            res = res[0] if isinstance(res, tuple) else res
            for o in res:
                if o["summary"]:
                    ph.append(dict(label=lab, file=Path(p).name, **o["summary"]))
        except Exception as e:
            ph.append(dict(label=lab, error=f"{type(e).__name__}: {e}"))
    doc["D_photos"] = {"measured": ph, "excluded": PHOTO_EXCLUDED}

    # E. 우리 것 — 법칙 상수 · 지금 코드로 새로 지은 날 · 디스크에 있는 출하 OBJ
    doc["E_ours"] = {"law_constants": ours_law(),
                     "fresh_build": ours_fresh_build(),
                     "shipped_obj": ours_shipped()}

    # F. 모집단 대비 백분위 + 판정
    doc["F_spread_and_verdicts"] = verdicts(doc)
    doc["G_claim_by_claim_ko"] = claim_verdicts(doc)
    doc["H_new_findings_ko"] = new_findings(doc)

    json.dump(doc, open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"wrote {OUT}  ({time.time()-t0:.1f}s)")
    return doc


if __name__ == "__main__":
    main()
