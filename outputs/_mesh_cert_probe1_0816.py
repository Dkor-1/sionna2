# -*- coding: utf-8 -*-
"""검사 공백 실측 — 일부러 만든 결함을 현행 검사기에 먹여 «잡히나» 를 본다(읽기 전용)."""
from __future__ import annotations
import copy, sys
import numpy as np
sys.path.insert(0, "/workspace/sionna/src")
import mesh_check as mc
from geom import Mesh
from drones import DRONES, build_drone

KEY = "mavic4pro"
spec = DRONES[KEY]
BASE = build_drone(spec)


def _box(mesh, lo, hi, group):
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    idx = [mesh.add_vertex(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    def v(i, j, k):
        return idx[4 * i + 2 * j + k]
    quads = [((0, 0, 0), (0, 1, 0), (0, 1, 1), (0, 0, 1)),
             ((1, 0, 0), (1, 0, 1), (1, 1, 1), (1, 1, 0)),
             ((0, 0, 0), (0, 0, 1), (1, 0, 1), (1, 0, 0)),
             ((0, 1, 0), (1, 1, 0), (1, 1, 1), (0, 1, 1)),
             ((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)),
             ((0, 0, 1), (0, 1, 1), (1, 1, 1), (1, 0, 1))]
    for a, b, c, d in quads:
        mesh.add_quad(v(*d), v(*c), v(*b), v(*a), group=group)
    return mesh


def verdict(m, name=KEY, sp=spec, do_bell=False):
    out = {}
    r = mc.check_mesh(m, name)
    out["topo_ok"] = bool(r["ok"])
    out["sliver_ok"] = bool(r["sliver_ok"])
    out["nonmanifold"] = sum(g["nonmanifold_edges"] for g in r["groups"].values())
    out["bedge"] = sum(g["boundary_edges"] for g in r["groups"].values())
    out["overlap_max"] = max(g["overlap_pct"] for g in r["groups"].values())
    if sp is not None:
        try:
            d = mc.check_dimensions(sp, mesh=m)
            out["dim_ok"] = bool(d["ok"]); out["dim_fail"] = d.get("failures", [])
        except Exception as e:
            out["dim_ok"] = f"EXC {type(e).__name__}: {e}"
        try:
            h = mc.check_handedness(sp, mesh=m)
            out["hand_ok"] = bool(h["ok"])
        except Exception as e:
            out["hand_ok"] = f"EXC {type(e).__name__}: {e}"
    if do_bell and sp is not None:
        try:
            b = mc.check_prop_bell_solid(sp, mesh=m)
            out["bell_ok"] = bool(b["ok"]); out["bell_pct"] = b["area_pct"]
        except Exception as e:
            out["bell_ok"] = f"EXC {type(e).__name__}"
    keys = ["topo_ok", "sliver_ok"] + (["dim_ok", "hand_ok"] if sp is not None else [])
    if do_bell:
        keys.append("bell_ok")
    out["ALL_PASS"] = all(out.get(k) is True for k in keys)
    return out


def show(tag, res, note=""):
    print(f"{'놓침 PASS ' if res['ALL_PASS'] else 'CAUGHT    '}| {tag:38s} | "
          f"topo {str(res['topo_ok'])[:5]:5s} dim {str(res.get('dim_ok'))[:5]:5s} "
          f"hand {str(res.get('hand_ok'))[:5]:5s} nm {res['nonmanifold']:4d} "
          f"be {res['bedge']:4d} ov {res['overlap_max']:6.2f} {note}")
    if res.get("dim_fail"):
        print(f"            └ dim: {res['dim_fail']}")


print("=== 음성 대조 ===")
show("무결 mavic4pro", verdict(BASE))

# A. 삼각형 완전 중복
m = copy.deepcopy(BASE); m.f = list(m.f) + [m.f[0]]; m.g = list(m.g) + [m.g[0]]
show("A 삼각형 1장 완전중복", verdict(m))

# B. 나비넥타이 — 상자 2개가 «정점 하나»만 공유 (비다양체 정점, 모서리는 정상)
mb = Mesh("body")
_box(mb, (0.0, 0.0, 0.0), (0.1, 0.1, 0.1), "body")
_box(mb, (0.1, 0.1, 0.1), (0.2, 0.2, 0.2), "body")
show("B 나비넥타이(비다양체 정점)", verdict(mb, name="_synthetic", sp=None))

# C. 자기교차 — 닫힌 껍질 하나가 스스로를 관통(정점 1개를 반대편으로 밀기)
mc2 = Mesh("body")
_box(mc2, (0.0, 0.0, 0.0), (0.1, 0.1, 0.1), "body")
V = list(mc2.v); V[0] = (0.05, 0.05, 0.20)      # 한 꼭짓점을 상자 밖 반대편으로
mc2.v = V
show("C 자기교차(껍질이 스스로 관통)", verdict(mc2, name="_synthetic", sp=None))

# D. 기체 전체 180° 요(yaw) — 앞뒤 뒤집힘
m = copy.deepcopy(BASE)
m.v = [(-x, -y, z) for (x, y, z) in BASE.v]
show("D 기체 180° yaw (앞뒤 반대)", verdict(m))

# E. 원점 이동 — 기체가 z 로 +1 m
m = copy.deepcopy(BASE)
m.v = [(x, y, z + 1.0) for (x, y, z) in BASE.v]
show("E 원점 +1 m (좌표 기준 어긋남)", verdict(m))

# F. 그룹 이름 오염 — battery → 모르는 이름
m = copy.deepcopy(BASE)
m.g = ["unobtainium" if g == "battery" else g for g in BASE.g]
show("F 그룹 이름 오타(모르는 재질)", verdict(m))

# F2. 그룹 뒤바꿈 — camera ↔ gear (재질 배정 오류, 형상 동일)
m = copy.deepcopy(BASE)
sw = {"camera": "gear", "gear": "camera"}
m.g = [sw.get(g, g) for g in BASE.g]
show("F2 그룹 뒤바꿈 camera↔gear", verdict(m))

# G. 균일 배율 오차 +2 %
m = copy.deepcopy(BASE)
m.v = [(x * 1.02, y * 1.02, z * 1.02) for (x, y, z) in BASE.v]
show("G 전체 +2 % 배율", verdict(m))

# G2. 균일 배율 오차 +0.7 % (허용오차 바로 밑)
m = copy.deepcopy(BASE)
m.v = [(x * 1.007, y * 1.007, z * 1.007) for (x, y, z) in BASE.v]
show("G2 전체 +0.7 % 배율", verdict(m))

# H. 로터 한 개만 z 로 +30 mm (배치 결함)
m = copy.deepcopy(BASE)
V = np.asarray(BASE.v, float); F = np.asarray(BASE.f, np.int64); G = np.asarray(BASE.g)
from drones import rotor_layout
ctr = np.asarray([r["center"] for r in rotor_layout(spec)], float)
pidx = np.where(G == "prop")[0]
Cp = V[F[pidx]].mean(1)
near = np.linalg.norm(Cp[:, None, :2] - ctr[None, :, :2], axis=2).argmin(1)
used = np.unique(F[pidx[near == 0]])
V2 = V.copy(); V2[used, 2] += 0.030
m.v = [tuple(map(float, p)) for p in V2]
show("H 로터0 프롭만 +30 mm 위로", verdict(m, do_bell=True))

# I. 날 1장 삭제 (2날 중 1장) — 부품이 통째로 사라짐
m = copy.deepcopy(BASE)
keep = np.ones(len(F), bool)
sel = pidx[near == 0]
# 그 로터의 프롭 삼각형 중 y>중심인 절반 = 한쪽 날
cy = ctr[0, 1]
half = sel[Cp[near == 0][:, 1] > cy]
keep[half] = False
m.f = [tuple(map(int, t)) for t in F[keep]]
m.g = list(G[keep])
show("I 로터0 날 한 장 삭제", verdict(m))

# J. 프롭 지름만 5 % 크게 (부품 치수 오류, 위치·위상 정상)
m = copy.deepcopy(BASE)
V3 = V.copy()
for k in range(len(ctr)):
    u = np.unique(F[pidx[near == k]])
    V3[u, 0] = ctr[k, 0] + (V3[u, 0] - ctr[k, 0]) * 1.05
    V3[u, 1] = ctr[k, 1] + (V3[u, 1] - ctr[k, 1]) * 1.05
m.v = [tuple(map(float, p)) for p in V3]
show("J 프롭만 +5 % (치수)", verdict(m))

# K. 카메라를 30 mm 뒤로 (배치 오류)
m = copy.deepcopy(BASE)
V4 = V.copy()
cam = np.unique(F[G == "camera"])
V4[cam, 0] -= 0.030
m.v = [tuple(map(float, p)) for p in V4]
show("K 카메라 30 mm 이동", verdict(m))

# L. 이산화 — 프롭 삼각형 절반을 잘라내지 않고 «면을 뒤집지 않은 채» 정점 몇 개를 살짝 흔들기
m = copy.deepcopy(BASE)
rng = np.random.default_rng(0)
V5 = V.copy()
u = np.unique(F[pidx])
V5[u] += rng.normal(0, 0.0005, size=(len(u), 3))   # 0.5 mm 지터
m.v = [tuple(map(float, p)) for p in V5]
show("L 프롭 정점 0.5 mm 지터", verdict(m))
