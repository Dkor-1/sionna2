# -*- coding: utf-8 -*-
"""팁 끝 1 % 를 아주 촘촘히 — 실물 DJI 날의 끝이 «뭉툭» 한가 «둥근» 가.

감사 H_tip 은 1.00R 에서 c/R 0.0206 을 적었고(정규화 0.078), 코드에 들어간 권고는 끝값 0.200 이다.
둘은 2.5 배 어긋난다. 어느 쪽이 맞는지 밴드 폭을 바꿔가며 재서 «측정 규약 의존» 인지 본다.
같은 자로 우리 legacy 날과 dji_mini2 판 날도 잰다.
"""
import numpy as np
import trimesh
from scipy.spatial import ConvexHull

GLB = "/workspace/sionna/assets/meshes/reference/WM161_zhankai_1k.glb"


def dense(mesh, e=2.5e-4):
    v, f = trimesh.remesh.subdivide_to_size(np.array(mesh.vertices, float),
                                            np.array(mesh.faces, np.int64), max_edge=e)
    return v


def caliper(P):
    if len(P) < 3:
        return np.nan
    try:
        Q = P[ConvexHull(P).vertices]
    except Exception:
        Q = P
    D = Q[:, None, :] - Q[None, :, :]
    return float(np.linalg.norm(D, axis=-1).max())


def profile(V, axis, centre, rr, band_m):
    a = axis / np.linalg.norm(axis)
    X = V - centre
    z = X @ a
    Xp = X - np.outer(z, a)
    r = np.linalg.norm(Xp, axis=1)
    R = r.max()
    e1 = np.array([1.0, 0, 0]) - a[0] * a
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(a, e1)
    phi = np.arctan2(Xp @ e2, Xp @ e1)
    out = []
    for x in rr:
        r0 = x * R
        m = np.abs(r - r0) <= band_m
        if m.sum() < 4:
            out.append(np.nan)
            continue
        ph = phi[m] - np.median(phi[m])
        ph = (ph + np.pi) % (2 * np.pi) - np.pi
        out.append(caliper(np.c_[r0 * ph, z[m] - np.median(z[m])]) / R)
    return np.array(out), R


def hub_axis(hub):
    V = np.array(hub.vertices, float)
    c = V.mean(0)
    ev, evec = np.linalg.eigh(np.cov((V - c).T))
    a = evec[:, 0]
    return (a / np.linalg.norm(a)) * (1 if a[1] > 0 else -1), c


S = trimesh.load(GLB)
geoms = S.dump(concatenate=False)
blades = [g for g in geoms if len(g.faces) in (1635, 1691)]
hubs = [hub_axis(g) for g in geoms if len(g.faces) == 1704]

rr = np.array([0.90, 0.95, 0.96, 0.97, 0.98, 0.985, 0.99, 0.992, 0.994, 0.996, 0.998, 0.999, 1.0])
print("DJI 실물 (밴드 폭을 바꿔가며) — c/R")
for band_mm in (0.5, 0.25, 0.12, 0.06):
    acc = []
    for b in blades:
        V = dense(b)
        hi = int(np.argmin([np.linalg.norm(V.mean(0) - c) for a, c in hubs]))
        p, R = profile(V, hubs[hi][0], hubs[hi][1], rr, band_mm * 1e-3)
        acc.append(p)
    A = np.nanmean(np.array(acc), axis=0)
    print(f" band ±{band_mm:4.2f} mm : " + " ".join(f"{x:.4f}" for x in A))
print("           r/R  = " + " ".join(f"{x:6.3f}" for x in rr))

# 정규화: c_max/R
acc = []
for b in blades:
    V = dense(b)
    hi = int(np.argmin([np.linalg.norm(V.mean(0) - c) for a, c in hubs]))
    p, R = profile(V, hubs[hi][0], hubs[hi][1], np.arange(0.30, 1.001, 0.01), 0.25e-3)
    acc.append(p)
A = np.nanmean(np.array(acc), axis=0)
cmax = np.nanmax(A)
print(f"\nc_max/R = {cmax:.4f} at r/R = {np.arange(0.30,1.001,0.01)[int(np.nanargmax(A))]:.2f}")
print("정규화 c/c_max (band ±0.25 mm):")
for x, v in zip(np.arange(0.30, 1.001, 0.01), A):
    if x >= 0.88:
        print(f"  {x:.2f}  {v/cmax:.3f}")
