# -*- coding: utf-8 -*-
"""검증 ② 보강 — «기본 경로 지문이 6기체에서 어긋난 것은 3층 값 몫이고 2층 스위치 몫은 0» 인가.

방법: 지금 저장소 src 를 통째로 복사한 뒤 **3층 값 5묶음만** 되돌린다(2층 스위치 코드는
      그대로 둔다). 되돌린 트리가 짓는 지문이 i5·m6 라운드가 적어 둔 «수리전코드» 지문과
      같으면, 2층 스위치가 기본 경로에 더한 변화는 **0** 이다.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

BASE = "/tmp/claude-0/-workspace/e9e31991-b542-4f3a-b8e2-570320d555ba/scratchpad/verify2"
SRC = "/workspace/sionna/src"
DST = os.path.join(BASE, "revsrc")

REVERT = [
    ("drone_cad.py", r"(?m)^(\s*)smooth_iters=0([,)])", r"\1smooth_iters=4\2", 6, True),
    ("drones.py", "envelope_mm=(None, None, 196.0)),",
     "envelope_mm=(289.5, 289.5, 196.0)),", 1, False),
    ("drone_cad.py", "_gimbal_hasselblad(0.0316, gx, -0.30 * bh)",
     "_gimbal_hasselblad(0.050, gx, -0.30 * bh)", 1, False),
    ("drone_cad.py", 'GEAR_SPIKE_INBOARD = {"matrice4e": (1.011, 1.034, 1.034, 1.011)}',
     'GEAR_SPIKE_INBOARD = {}', 1, False),
    ("drone_cad.py", 'GEAR_SPIKE_H = {"matrice4e": (0.04661, 0.03879, 0.03879, 0.04661)}',
     'GEAR_SPIKE_H = {"matrice4e": 0.0529}', 1, False),
    ("drone_cad.py", 'GEAR_TOP_Z = {"matrice4e": (-0.00851, -0.01633, -0.01633, -0.00851)}',
     'GEAR_TOP_Z = {}', 1, False),
    ("drone_cad.py",
     'MOTOR_BASE_Z = {"phantom3": 0.0110, "mini2": 0.007985, "matrice4e": -0.01242}',
     'MOTOR_BASE_Z = {"phantom3": 0.0110, "mini2": 0.007985}', 1, False),
    ("drone_cad.py",
     'ARM_Z_FOLLOWS_ROTOR = {"mini2": True, "mini5pro": True, "matrice4e": True}',
     'ARM_Z_FOLLOWS_ROTOR = {"mini2": True, "mini5pro": True}', 1, False),
    ("drone_cad.py", 'ARM_TIP_Z = {"matrice4e": (-0.01635, -0.02228, -0.02228, -0.01635)}',
     'ARM_TIP_Z = {}', 1, False),
    ("drones.py", "        rotor_z_mm=(3.91, -3.91, -3.91, 3.91),\n", "", 1, False),
]

if os.path.isdir(DST):
    shutil.rmtree(DST)
shutil.copytree(SRC, DST, ignore=shutil.ignore_patterns("__pycache__"))
log = []
for fn, old, new, n_exp, is_re in REVERT:
    p = os.path.join(DST, fn)
    t = open(p, encoding="utf-8").read()
    if is_re:
        t2, n = re.subn(old, new, t)
    else:
        n = t.count(old)
        t2 = t.replace(old, new)
    log.append(dict(file=fn, pat=old[:48], n=n, expect=n_exp, ok=(n == n_exp)))
    if n != n_exp:
        print(f"⚠ 표식 개수 불일치: {fn} {old[:40]!r} {n} ≠ {n_exp}")
    open(p, "w", encoding="utf-8").write(t2)

code = r'''
import hashlib, json, os, sys
import numpy as np
os.environ["CUDA_VISIBLE_DEVICES"]=""
os.environ.pop("MESH_FIX", None)
sys.path.insert(0, %r)
from drones import DRONES, build_drone
import geom
def fp(m):
    h=hashlib.sha256()
    h.update(np.ascontiguousarray(np.asarray(m.v,float)).tobytes())
    h.update(np.ascontiguousarray(np.asarray(m.f,np.int64)).tobytes())
    h.update("|".join(m.g).encode()); return h.hexdigest()[:16]
out={f"drone:{k}": fp(build_drone(s)) for k,s in DRONES.items()}
for seg,rings in ((18,10),(90,46),(120,60),(180,90)):
    out[f"uv_sphere:{seg}x{rings}"]=fp(geom.uv_sphere(1.0,seg=seg,rings=rings))
print(json.dumps(out))
''' % DST
r = subprocess.run(["/workspace/.venvs/py312/bin/python", "-c", code],
                   capture_output=True, text=True)
if r.returncode:
    print(r.stdout[-2000:], r.stderr[-3000:])
    sys.exit(1)
got = json.loads(r.stdout.strip().splitlines()[-1])
ref = json.load(open("/workspace/sionna/outputs/mesh_layer2_holes_poles_0816.json")
                )["회귀_비트동일"]["지문_수리전코드"]
bad = {k: (ref.get(k), got.get(k)) for k in ref if ref.get(k) != got.get(k)}
print(json.dumps(dict(치환로그=log, 어긋난_항목=bad, 칸수=len(ref),
                      결론=("2층 스위치 몫 = 0 (3층 값만 되돌리니 기준선 복귀)"
                            if not bad else "어긋남 남음 — 2층 몫이 있을 수 있다")),
                 ensure_ascii=False, indent=1))
