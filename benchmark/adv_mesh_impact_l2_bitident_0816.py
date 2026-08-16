# -*- coding: utf-8 -*-
"""검증 B — 인자를 안 주면 비트동일인가 + 수리 코드가 정말 안 밟히나(계측)."""
import hashlib
import json
import os
import sys

import numpy as np

os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ.pop("MESH_FIX", None)
sys.path.insert(0, "/workspace/sionna/src")

import cadkit
import drone_cad
import geom
from drones import DRONES, build_drone, build_frame, build_propeller


def fp(mesh) -> str:
    h = hashlib.sha256()
    h.update(np.ascontiguousarray(np.asarray(mesh.v, float)).tobytes())
    h.update(np.ascontiguousarray(np.asarray(mesh.f, np.int64)).tobytes())
    h.update("|".join(mesh.g).encode())
    return h.hexdigest()[:16]


CALLED = []
_c_collapse = cadkit.collapse_degenerate_faces
_c_i4 = drone_cad._fix_i4_canopy
_c_m4 = drone_cad._fix_m4_arm_clamp
_c_uv = geom.uv_sphere


def spy(name, fn):
    def w(*a, **k):
        CALLED.append(name)
        return fn(*a, **k)
    return w


cadkit.collapse_degenerate_faces = spy("i5:collapse", _c_collapse)
drone_cad._fix_i4_canopy = spy("i4:canopy", _c_i4)
drone_cad._fix_m4_arm_clamp = spy("m4:armclamp", _c_m4)

UNION_SEEN = []
_c_union = drone_cad.Assembly.union_group if hasattr(drone_cad, "Assembly") else None


out = {}
base = {}
for k, s in DRONES.items():
    base[k] = dict(drone=fp(build_drone(s)), frame=fp(build_frame(s)),
                   prop=fp(build_propeller(s)))
out["기본(환경변수없음)"] = base
out["수리코드_호출됨"] = sorted(set(CALLED))

# ① MESH_FIX="" (빈 문자열)
os.environ["MESH_FIX"] = ""
empty = {k: fp(build_drone(s)) for k, s in DRONES.items()}
os.environ.pop("MESH_FIX", None)
out["MESH_FIX=빈문자열_동일"] = all(empty[k] == base[k]["drone"] for k in base)

# ② 명시적으로 mesh_fix=False
false_ = {k: fp(build_drone(s, mesh_fix=False)) for k, s in DRONES.items()}
out["mesh_fix=False_동일"] = all(false_[k] == base[k]["drone"] for k in base)

# ③ 스위치를 켰다 껐다 해도 원상복귀되나(호출 시점 판정)
geom.set_mesh_fix("i5,m6,battery,i4,m4")
_ = build_drone(DRONES["mini2"])
geom.set_mesh_fix()
os.environ.pop("MESH_FIX", None)
after = {k: fp(build_drone(s)) for k, s in DRONES.items()}
out["켰다_끈_뒤_동일"] = all(after[k] == base[k]["drone"] for k in base)

# ④ 캐시 오염 — 수리 켠 상태의 결과가 캐시에 남아 기본 경로를 오염시키나
out["캐시_오염_검사"] = dict(
    fit_cache_len=len(getattr(__import__("drones"), "_FIT_CACHE", {})),
)

# ⑤ uv_sphere 기본값
s0 = geom.uv_sphere(1.0, seg=18, rings=10)
s_off = geom.uv_sphere(1.0, seg=18, rings=10, weld_poles=False)
s_on = geom.uv_sphere(1.0, seg=18, rings=10, weld_poles=True)
out["uv_sphere_기본=끔"] = (len(s0.v) == len(s_off.v) != len(s_on.v))

# ⑥ 수리 켰을 때 지문이 실제로 달라지나(= 스위치가 듣나)
onfp = {}
for tok in ("i5", "m6", "battery", "i4", "m4", "i5,m6,battery,i4,m4"):
    os.environ["MESH_FIX"] = tok
    d = {}
    for k, s in DRONES.items():
        try:
            d[k] = fp(build_drone(s))
        except Exception as e:                       # i4 단독은 mini2 에서 죽는다(선언됨)
            d[k] = f"ERR:{type(e).__name__}"
    onfp[tok] = {k: ("동일" if d[k] == base[k]["drone"] else d[k]) for k in d}
    os.environ.pop("MESH_FIX", None)
out["수리켠_지문"] = onfp

print(json.dumps(out, ensure_ascii=False, indent=1))
