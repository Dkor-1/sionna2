# -*- coding: utf-8 -*-
"""공백 실측 2차 — 배치·개수·재질·좌표 축."""
from __future__ import annotations
import copy, sys
import numpy as np
sys.path.insert(0, "/workspace/sionna/src")
import mesh_check as mc
from drones import DRONES, build_drone, rotor_layout

KEY = "mavic4pro"
spec = DRONES[KEY]
BASE = build_drone(spec)
V0 = np.asarray(BASE.v, float); F = np.asarray(BASE.f, np.int64); G = np.asarray(BASE.g)
ctr = np.asarray([r["center"] for r in rotor_layout(spec)], float)
pidx = np.where(G == "prop")[0]
Cp = V0[F[pidx]].mean(1)
near = np.linalg.norm(Cp[:, None, :2] - ctr[None, :, :2], axis=2).argmin(1)


def verdict(m, name=KEY, do_bell=True, do_buried=False):
    out = {}
    r = mc.check_mesh(m, name)
    out["topo"] = bool(r["ok"]) and bool(r["sliver_ok"])
    d = mc.check_dimensions(spec, mesh=m); out["dim"] = bool(d["ok"]); out["dimf"] = d.get("failures")
    h = mc.check_handedness(spec, mesh=m); out["hand"] = bool(h["ok"])
    if do_bell:
        b = mc.check_prop_bell_solid(spec, mesh=m); out["bell"] = bool(b["ok"]); out["bellpct"] = b["area_pct"]
    if do_buried:
        bf = mc.check_buried_faces(spec, mesh=m); out["buried"] = bool(bf["ok"]); out["bpct"] = bf["defect_pct"]
    out["ALL"] = all(v is True for k, v in out.items() if k in ("topo", "dim", "hand", "bell", "buried"))
    return out


def show(tag, res):
    print(f"{'놓침 PASS ' if res['ALL'] else 'CAUGHT    '}| {tag:40s} | topo {str(res['topo'])[:5]:5s} "
          f"dim {str(res['dim'])[:5]:5s} hand {str(res['hand'])[:5]:5s} "
          f"bell {str(res.get('bell'))[:5]:5s}({res.get('bellpct')}) buried {str(res.get('buried'))[:5]}")
    if res.get("dimf"):
        print(f"            └ {res['dimf']}")


def with_v(V):
    m = copy.deepcopy(BASE); m.v = [tuple(map(float, p)) for p in V]; return m


print("=== 음성 대조 ===")
show("무결", verdict(BASE, do_buried=True))

# H2. 프롭 하나만 30 mm **아래로** (벨 속으로)
V = V0.copy(); V[np.unique(F[pidx[near == 0]]), 2] -= 0.030
show("H2 로터0 프롭 −30 mm(벨 속으로)", verdict(with_v(V)))

# M. 로터 반경 ±20 mm 서로 상쇄 (평균 반경 불변)
V = V0.copy()
for k, s in ((0, +0.020), (2, -0.020)):
    u = np.unique(F[pidx[near == k]])
    d = ctr[k, :2] / np.linalg.norm(ctr[k, :2])
    V[u, 0] += d[0] * s; V[u, 1] += d[1] * s
show("M 로터0 +20/로터2 −20 mm(평균불변)", verdict(with_v(V)))

# N. 프로펠러 하나 통째로 삭제
m = copy.deepcopy(BASE)
keep = np.ones(len(F), bool); keep[pidx[near == 0]] = False
m.f = [tuple(map(int, t)) for t in F[keep]]; m.g = list(G[keep])
show("N 프로펠러 1개 통째로 삭제", verdict(m))

# O. 그룹 이름만 바꾸기 (gear → landing_skid) — 겹침 예산과 무관한 깨끗한 그룹
m = copy.deepcopy(BASE)
m.g = ["landing_skid" if g == "gear" else g for g in BASE.g]
show("O 그룹명 gear→landing_skid", verdict(m))

# P. 카메라를 2 배로 (부품 치수)
V = V0.copy(); cam = np.unique(F[G == "camera"])
c0 = V[cam].mean(0); V[cam] = c0 + (V[cam] - c0) * 2.0
show("P 카메라 2배 확대", verdict(with_v(V), do_buried=True))

# Q. 배터리를 셸 밖으로 (내부 금속 노출)
V = V0.copy(); bat = np.unique(F[G == "battery"]); V[bat, 2] += 0.060
show("Q 배터리 60 mm 위로(셸 밖)", verdict(with_v(V), do_buried=True))

# R. z 를 뒤집기 (위아래 반전)
V = V0.copy(); V[:, 2] = -V[:, 2]
m = with_v(V); m.f = [(a, c, b) for (a, b, c) in BASE.f]
show("R 위아래 반전(z 뒤집기)", verdict(m))

# S. 프롭 피치(비틀림)를 0 으로 — 날을 평평하게
V = V0.copy()
for k in range(len(ctr)):
    u = np.unique(F[pidx[near == k]])
    V[u, 2] = ctr[k, 2] + (V[u, 2] - ctr[k, 2]) * 0.05
show("S 프롭 비틀림 20 분의 1(거의 평평)", verdict(with_v(V)))
