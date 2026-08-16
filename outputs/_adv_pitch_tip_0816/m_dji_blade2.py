# -*- coding: utf-8 -*-
"""DJI Mini 2 공식 GLB — 날 **1장씩 따로** 국소피치 k(r)·시위 c(r) 측정 (v2).

v1 의 실패 원인: 허브가 수밀이 아니라 trimesh 의 관성텐서가 무효였다.
v2 는 (a) 허브 정점 PCA 의 **최소분산 축** = 회전축, 중심 = 허브 정점 중심
        (b) 날 표면을 0.4 mm 로 세분해 촘촘한 점구름을 만든 뒤 원통 밴드로 자른다.
축 민감도: 허브축 ↔ 월드 ±y 두 번 잰다.
"""
import json
import numpy as np
import trimesh
from scipy.spatial import ConvexHull

GLB = "/workspace/sionna/assets/meshes/reference/WM161_zhankai_1k.glb"
OUT = "/tmp/claude-0/-workspace/e9e31991-b542-4f3a-b8e2-570320d555ba/scratchpad/dji_blade_raw.json"
P_NOM_M = 2.6 * 0.0254        # 0.06604 m


def dense_points(mesh, max_edge=4e-4):
    v, f = trimesh.remesh.subdivide_to_size(np.array(mesh.vertices, float),
                                            np.array(mesh.faces, np.int64), max_edge=max_edge)
    return v


def hub_axis(hub):
    V = np.array(hub.vertices, float)
    c = V.mean(0)
    ev, evec = np.linalg.eigh(np.cov((V - c).T))
    a = evec[:, 0]                     # 최소분산 = 납작한 원반의 대칭축
    return a / np.linalg.norm(a), c


def caliper(P):
    """(n,2) 점구름의 최대 캘리퍼 길이·방향각(0~90deg, |dz/ds|)."""
    if len(P) < 3:
        return np.nan, np.nan
    try:
        Q = P[ConvexHull(P).vertices]
    except Exception:
        Q = P
    D = Q[:, None, :] - Q[None, :, :]
    L = np.linalg.norm(D, axis=-1)
    i, j = np.unravel_index(np.argmax(L), L.shape)
    v = Q[j] - Q[i]
    return float(L[i, j]), float(np.arctan2(abs(v[1]), abs(v[0])))


def pca_angle(P):
    c = P.mean(0)
    ev, evec = np.linalg.eigh(np.cov((P - c).T))
    v = evec[:, -1]
    return float(np.arctan2(abs(v[1]), abs(v[0])))


def measure_blade(V, axis, centre, rr_grid, band_mm=0.35):
    a = axis / np.linalg.norm(axis)
    X = V - centre
    z = X @ a
    Xp = X - np.outer(z, a)
    r = np.linalg.norm(Xp, axis=1)
    R = r.max()
    e1 = np.array([1.0, 0.0, 0.0]) - a[0] * a
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(a, e1)
    phi = np.unwrap(np.arctan2(Xp @ e2, Xp @ e1))
    rows = {}
    for rr in rr_grid:
        r0 = rr * R
        m = np.abs(r - r0) <= band_mm * 1e-3
        if m.sum() < 8:
            rows[float(rr)] = dict(n=int(m.sum()))
            continue
        ph = phi[m]
        ph = ph - np.median(ph)
        ph = (ph + np.pi) % (2 * np.pi) - np.pi
        P = np.c_[r0 * ph, z[m] - np.median(z[m])]
        c_len, ang_cal = caliper(P)
        ang_pca = pca_angle(P)
        rows[float(rr)] = dict(n=int(m.sum()), c_over_R=c_len / R,
                               beta_cal_deg=np.degrees(ang_cal), beta_pca_deg=np.degrees(ang_pca),
                               k_cal=2 * np.pi * r0 * np.tan(ang_cal) / P_NOM_M,
                               k_pca=2 * np.pi * r0 * np.tan(ang_pca) / P_NOM_M)
    return rows, R


def main():
    S = trimesh.load(GLB)
    geoms = S.dump(concatenate=False)
    blades = [g for g in geoms if len(g.faces) in (1635, 1691)]
    hubs = [g for g in geoms if len(g.faces) == 1704]
    hub_ax = [hub_axis(h) for h in hubs]
    for i, (a, c) in enumerate(hub_ax):
        if a[1] < 0:
            a = -a
            hub_ax[i] = (a, c)
        print(f"hub{i} centre {np.round(c*1000,2)} mm  axis {a.round(4)}  "
              f"tilt {np.degrees(np.arccos(min(1,abs(a[1])))):.2f} deg")

    rr = np.concatenate([np.round(np.arange(0.25, 0.96, 0.05), 3),
                         np.array([0.92, 0.94, 0.96, 0.97, 0.98, 0.99, 0.995, 1.0])])
    rr = np.unique(rr)
    res = {"meta": dict(P_nom_m=P_NOM_M, glb=GLB, band_mm=0.35, subdiv_mm=0.4), "blades": []}
    for bi, b in enumerate(blades):
        V = dense_points(b)
        cb = V.mean(0)
        hi = int(np.argmin([np.linalg.norm(cb - c) for a, c in hub_ax]))
        for tag, ax in (("hub", hub_ax[hi][0]), ("worldy", np.array([0.0, 1.0, 0.0]))):
            rows, R = measure_blade(V, ax, hub_ax[hi][1], rr)
            res["blades"].append(dict(blade=bi, hub=hi, axis=tag, faces=len(b.faces),
                                      R_mm=R * 1000, n_pts=len(V), rows=rows))
    json.dump(res, open(OUT, "w"), indent=1)

    for tag in ("hub", "worldy"):
        rows = [b for b in res["blades"] if b["axis"] == tag]
        print(f"\n=== axis={tag}  R[mm] {[round(b['R_mm'],2) for b in rows]}")
        print(" r/R  " + "".join(f"  b{i:<4d}" for i in range(len(rows))) + "   mean   sd    min   max")
        for x in rr:
            v = np.array([b["rows"][float(x)].get("k_cal", np.nan) for b in rows], float)
            if np.all(~np.isfinite(v)):
                continue
            print(f"{x:5.3f} " + "".join(f" {q:6.3f}" for q in v) +
                  f"  {np.nanmean(v):6.3f} {np.nanstd(v):5.3f} {np.nanmin(v):6.3f} {np.nanmax(v):6.3f}")


if __name__ == "__main__":
    main()
