#!/usr/bin/env python
"""적대검증 4부 — 「고치면 오히려 나빠지는가」를 짐벌 정정(G1+G2)에 대해 직접 시험한다.

  블록을 47 → 61.2 mm 로 키우면 블록 윗부분이 셸(동체) **안**으로 파고드는가.
  build_drone 은 불리언 합집합을 안 하므로 파고든 면은 살아남아 PO 가 두 번 센다.
  ⇒ 검사표 A8(«새 겹침이 생기지 않았나»)의 실제 값을 미리 잰다.

⛔ 소스 무편집 · GPU 무사용.
"""
from __future__ import annotations
import hashlib, json, os, sys, time

ROOT = "/home/yunjung/workspace/sionna2"
sys.path.insert(0, os.path.join(ROOT, "src")); sys.path.insert(0, os.path.join(ROOT, "benchmark"))
sys.path.insert(0, ROOT)
os.environ.setdefault("SIONNA2_NO_GPU", "1"); os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

import numpy as np, trimesh              # noqa: E402
import drone_cad as dc                   # noqa: E402
import drones as dr                      # noqa: E402

R = lambda x, n=4: round(float(x), n)     # noqa: E731
T0 = time.time()
G_IN = {p: hashlib.sha256(open(os.path.join(ROOT, p), "rb").read()).hexdigest()[:16]
        for p in ("src/drones.py", "src/drone_cad.py")}


def build(args=None):
    _gs = dc._gimbal_sensor_v2
    if args:
        dc._gimbal_sensor_v2 = lambda w, h, d, cx, cz: _gs(*args)
    dr._FIT_CACHE.clear()
    m = dr.build_frame(dr.DRONES["matrice4e"])
    dc._gimbal_sensor_v2 = _gs
    dr._FIT_CACHE.clear()
    return m


def overlap(m, tag):
    V = np.asarray(m.v, float) * 1000.0
    F = np.asarray(m.f, np.int64); G = np.asarray(m.g)
    C = V[F].mean(1)
    body = trimesh.Trimesh(vertices=V, faces=F[G == "body"], process=True)
    body.remove_unreferenced_vertices()
    wt = bool(body.is_watertight)
    # 카메라 그룹 중 짐벌(기수 앞쪽 x>110) 삼각형이 셸 안에 있는가 — z 축 광선 홀짝
    gim = (G == "camera") & (C[:, 0] > 110)
    P = C[gim]
    if len(P) == 0:
        return dict(tag=tag, n_gimbal_tris=0)
    origins = P.copy()
    dirs = np.tile(np.array([0.0, 0.0, 1.0]), (len(P), 1))
    inter = body.ray.intersects_id(ray_origins=origins, ray_directions=dirs,
                                   multiple_hits=True, return_locations=False)
    idx = inter[1] if isinstance(inter, tuple) else inter
    cnt = np.bincount(np.asarray(idx, int), minlength=len(P)) if len(np.asarray(idx)) else np.zeros(len(P), int)
    inside = (cnt % 2) == 1
    # 반대로 셸 삼각형이 짐벌 블록 bbox 안에 있는 수도 같이 낸다
    Vg = V[np.unique(F[gim])]
    lo, hi = Vg.min(0), Vg.max(0)
    inbb = ((C[:, 0] >= lo[0]) & (C[:, 0] <= hi[0]) & (C[:, 1] >= lo[1]) & (C[:, 1] <= hi[1])
            & (C[:, 2] >= lo[2]) & (C[:, 2] <= hi[2]) & (G == "body"))
    return dict(tag=tag, n_gimbal_tris=int(gim.sum()), body_watertight=wt,
                gimbal_tris_inside_shell=int(inside.sum()),
                gimbal_bbox_mm=[R(x, 2) for x in lo] + [R(x, 2) for x in hi],
                body_tris_in_gimbal_bbox=int(inbb.sum()),
                frame_bbox_mm=[R(x, 2) for x in (V.max(0) - V.min(0))])


rows = [overlap(build(), "current  h=47.0 cz=-17.16"),
        overlap(build((0.059, 0.0612, 0.052, 0.1483, -0.01036)), "G1+G2  h=61.2 cz=-10.36"),
        overlap(build((0.0629, 0.0612, 0.052, 0.1483, -0.01036)), "G1+G2+G3  w=62.9"),
        overlap(build((0.0629, 0.0612, 0.0364, 0.1561, -0.01036)), "G1..G4  d=36.4 cx=156.1")]

OUT = dict(rows=rows,
           ko="짐벌 블록을 키우면 블록 윗부분이 셸 안으로 들어가는지 z 광선 홀짝으로 직접 셌다. "
              "build_drone 은 합집합을 안 하므로 안으로 들어간 면은 살아남아 PO 가 이중으로 적분한다.",
           _meta=dict(generator="benchmark/meshdef_attack_verify4.py",
                      generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
                      src_guard_in=G_IN,
                      src_guard_out={p: hashlib.sha256(open(os.path.join(ROOT, p), "rb").read()).hexdigest()[:16]
                                     for p in ("src/drones.py", "src/drone_cad.py")},
                      elapsed_s=round(time.time() - T0, 1)))
p = os.path.join(ROOT, "outputs/meshdef_attack_raw4.json")
json.dump(OUT, open(p, "w"), ensure_ascii=False, indent=1)
for r in rows:
    print(r)
print("wrote", p)
