# -*- coding: utf-8 -*-
"""
capdiag_0816.py — B3(로프트 끝단 캡) **진단**: 스무딩을 줄이면 가운데도 거칠어지는가?
=====================================================================================

무엇을 묻나
-----------
비프롭 감사(outputs/mesh_inspect_body_arms_0816.json, 발견 B3)는 «Taubin 스무딩 4회가
로프트 양 끝 캡의 테두리를 안쪽으로 당겨 실측 단면의 43 % 를 먹는다» 고 적었다.
값 적용 라운드의 조건은 «끝단만 살리고 가운데는 안 건드린다» 이다.

이 파일은 그 조건을 시험한다:
  ① 스무딩 횟수를 0~4 로 바꾸면 **가운데 4 스테이션**(−0.30/−0.05/+0.18/+0.38)의
     반폭·반높이·단면적·표면 거칠기가 얼마나 움직이나?
  ② 스무딩은 그대로 두고 **끝단 캡 삼각화만** 바꾸면(부채꼴 1장 → 동심 링 N장)
     끝단이 얼마나 살아나고 가운데는 얼마나 움직이나?

규약
----
* CPU 전용, GPU 0 회. 출하 코드는 **읽기만** 한다 — 캡 삼각화 후보는 이 파일 안에서
  `cadkit.loft` 를 복제해 시험한다(적용은 별건).
* 거칠기 잣대 = 인접 면 법선 사이 각(이면각)의 평균·95 백분위 [deg], 가운데 구간만.

산출: outputs/_capdiag_0816.json
실행:
  cd /workspace/sionna && CUDA_VISIBLE_DEVICES="" PYTHONPATH=src:benchmark \
    /workspace/.venvs/py312/bin/python benchmark/capdiag_0816.py
"""
from __future__ import annotations

import json
import os
import sys
import warnings

import numpy as np
import trimesh

warnings.filterwarnings("ignore", category=DeprecationWarning)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import drone_cad as dc                                        # noqa: E402
from cadkit import spline_sections, smooth                    # noqa: E402
from drones import DRONES                                     # noqa: E402

SHELL_KEYS = ["matrice4e", "mavic4pro", "mini5pro", "phantom4", "phantom3", "mini2"]
STATIONS = (-0.50, -0.30, -0.05, 0.18, 0.38, 0.50)


# --------------------------------------------------------------------------- #
#  후보 캡: 동심 링 N 장 (N=1 이면 출하 부채꼴과 같은 삼각형 집합)
# --------------------------------------------------------------------------- #
def _resample(poly, n):
    ring = poly.exterior
    d = np.linspace(0.0, ring.length, n, endpoint=False)
    return np.array([[p.x, p.y] for p in (ring.interpolate(t) for t in d)])


def loft_capk(sections, n_pts=48, cap_rings=1):
    """cadkit.loft 의 복제 + `cap_rings`. cap_rings=1 은 출하와 **같은 면 집합**이다."""
    xs = [s[0] for s in sections]
    rings = [_resample(s[1], n_pts) for s in sections]
    V, F = [], []
    for x, r in zip(xs, rings):
        V.append(np.c_[np.full(n_pts, x), r])
    V = np.vstack(V)
    for i in range(len(xs) - 1):
        a, b = i * n_pts, (i + 1) * n_pts
        for k in range(n_pts):
            k2 = (k + 1) % n_pts
            F.append([a + k, b + k, b + k2])
            F.append([a + k, b + k2, a + k2])
    nr = max(1, int(cap_rings))
    for end, ring, sgn in ((0, rings[0], -1), (len(xs) - 1, rings[-1], +1)):
        base = end * n_pts
        ctr = ring.mean(0)
        prev = base
        for j in range(1, nr):                       # 동심 링 (반경비 1−j/nr)
            t = 1.0 - j / nr
            cur = len(V)
            V = np.vstack([V, np.c_[np.full(n_pts, xs[end]), ctr[None, :] + t * (ring - ctr[None, :])]])
            for k in range(n_pts):
                k2 = (k + 1) % n_pts
                F.append([prev + k, cur + k, cur + k2][::sgn])
                F.append([prev + k, cur + k2, prev + k2][::sgn])
            prev = cur
        c = len(V)
        V = np.vstack([V, np.r_[xs[end], ctr][None, :]])
        for k in range(n_pts):
            k2 = (k + 1) % n_pts
            F.append([c, prev + k, prev + k2][::sgn])
    m = trimesh.Trimesh(vertices=np.asarray(V, float), faces=np.asarray(F, int), process=True)
    trimesh.repair.fix_normals(m)
    return m


def body_variant(bl, bw, bh, sh, smooth_iters=4, cap_rings=1, tail_w=0.95):
    """`_body_folding` 과 같은 로프트를 짓되 캡 삼각화·스무딩을 고를 수 있다."""
    L, W, H = bl, bw, bh
    xs = np.array(STATIONS) * L
    hw_f, hh_f, zo_f = sh["hw"], sh["hh"], sh["zo"]
    nd, npow = sh["ndrop"], sh["npow"]
    hw = np.array(hw_f if hw_f is not None else (0.30, 0.46, 0.50, 0.44, 0.28, 0.10)) * W * tail_w
    hh = np.array(hh_f if hh_f is not None else (0.30, 0.46, 0.50, 0.46, 0.34, 0.16)) * H
    zo = np.array(zo_f if zo_f is not None else (0.02, 0.01, 0.00, -0.04, -0.10, -nd)) * H
    m = loft_capk(spline_sections(xs, hw, hh, zo, n_pow=npow, n_sec=30, n_pts=72),
                  n_pts=72, cap_rings=cap_rings)
    return smooth(m, iters=int(smooth_iters)) if int(smooth_iters) > 0 else m


# --------------------------------------------------------------------------- #
#  잣대
# --------------------------------------------------------------------------- #
def section_at(m, x0):
    """x=x0 단면의 (반폭[mm], 반높이[mm], 면적[mm²]). 못 자르면 None."""
    try:
        s = m.section(plane_origin=[x0, 0, 0], plane_normal=[1, 0, 0])
        if s is None:
            return None
        p, _ = s.to_planar()
        polys = p.polygons_full
        if len(polys) == 0:
            return None
        pg = max(polys, key=lambda q: q.area)
        c = np.array(pg.exterior.coords)
        # to_planar 축 순서가 (z, y) 로 나올 수 있어 두 폭 중 큰 쪽을 반폭으로 못 박지 않는다 —
        # 원본 3D 로 되돌려 y·z 를 직접 읽는다.
        P3 = np.asarray(s.vertices, float)
        return (float(np.ptp(P3[:, 1]) / 2 * 1000), float(np.ptp(P3[:, 2]) / 2 * 1000),
                float(pg.area * 1e6))
    except Exception:
        return None


def roughness(m, x_lo, x_hi):
    """가운데 구간 [x_lo, x_hi] 의 이면각(deg) 평균·p95 — 면 중심 x 로 고른다."""
    fc = m.triangles_center[:, 0]
    keep = (fc > x_lo) & (fc < x_hi)
    adj = m.face_adjacency
    ang = m.face_adjacency_angles
    sel = keep[adj[:, 0]] & keep[adj[:, 1]]
    if sel.sum() < 10:
        return None
    a = np.degrees(ang[sel])
    return dict(mean_deg=float(a.mean()), p95_deg=float(np.percentile(a, 95)),
                max_deg=float(a.max()), n=int(sel.sum()))


def measure(m, bl, targets):
    out = {}
    for st in STATIONS:
        x0 = st * bl
        if st == -0.50:
            x0 += 1e-6
        elif st == 0.50:
            x0 -= 1e-6
        r = section_at(m, x0)
        out[f"{st:+.2f}"] = None if r is None else dict(
            half_w_mm=round(r[0], 3), half_h_mm=round(r[1], 3), area_mm2=round(r[2], 2),
            err_w_pct=round(100 * (r[0] / targets[st][0] - 1), 2),
            err_h_pct=round(100 * (r[1] / targets[st][1] - 1), 2))
    out["len_mm"] = round(float(np.ptp(m.vertices[:, 0])) * 1000, 3)
    out["rough_mid"] = roughness(m, -0.30 * bl, 0.38 * bl)
    out["n_tri"] = int(len(m.faces))
    out["watertight"] = bool(m.is_watertight)
    return out


def main():
    res = {}
    for key in SHELL_KEYS:
        sp = DRONES[key]
        sh = dc._SHELL_SHAPE.get(key, dc._SHELL_DEFAULT)
        L, W, H = sp.body_l_mm / 1000, sp.body_w_mm / 1000, sp.body_h_mm / 1000
        bl, bw, bh = L * sh["fl"], W * sh["fw"], H * sh["fh"]
        hw_f = sh["hw"] if sh["hw"] is not None else (0.30, 0.46, 0.50, 0.44, 0.28, 0.10)
        hh_f = sh["hh"] if sh["hh"] is not None else (0.30, 0.46, 0.50, 0.46, 0.34, 0.16)
        targets = {st: (hw_f[i] * bw * 0.95 * 1000, hh_f[i] * bh * 1000)
                   for i, st in enumerate(STATIONS)}
        d = {"bl_bw_bh_mm": [round(bl * 1000, 3), round(bw * 1000, 3), round(bh * 1000, 3)],
             "target_halfw_halfh_mm": {f"{st:+.2f}": [round(targets[st][0], 3), round(targets[st][1], 3)]
                                       for st in STATIONS},
             "variants": {}}
        for it in (0, 1, 2, 3, 4):
            d["variants"][f"fan_it{it}"] = measure(body_variant(bl, bw, bh, sh, it, 1), bl, targets)
        for nr in (3, 6, 10, 16):
            d["variants"][f"disk{nr}_it4"] = measure(body_variant(bl, bw, bh, sh, 4, nr), bl, targets)
        res[key] = d
        print(f"[{key}] done", flush=True)

    #  출하 경로와의 동일성 회귀 — fan_it4 == _body_folding 기본
    same = {}
    for key in SHELL_KEYS:
        sp = DRONES[key]
        sh = dc._SHELL_SHAPE.get(key, dc._SHELL_DEFAULT)
        bl, bw, bh = (sp.body_l_mm / 1000 * sh["fl"], sp.body_w_mm / 1000 * sh["fw"],
                      sp.body_h_mm / 1000 * sh["fh"])
        a = dc._body_folding(bl, bw, bh, nose_drop=sh["ndrop"], n_pow=sh["npow"],
                             hw_f=sh["hw"], hh_f=sh["hh"], zo_f=sh["zo"])
        b = body_variant(bl, bw, bh, sh, 4, 1)
        same[key] = dict(v=int(len(a.vertices) == len(b.vertices)),
                         max_dv_mm=float(np.abs(np.sort(a.vertices, axis=0) -
                                                np.sort(b.vertices, axis=0)).max() * 1000)
                         if len(a.vertices) == len(b.vertices) else None)
    res["_replica_check"] = same
    out = os.path.join(ROOT, "outputs", "_capdiag_0816.json")
    with open(out, "w") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print("wrote", out)


if __name__ == "__main__":
    main()
