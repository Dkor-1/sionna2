# -*- coding: utf-8 -*-
"""검증 ④-2 — i3 의 dB 가 «어느 그룹을 내부로 인정하나» 라는 **규칙 선택**에 얼마나 매달리나.

A판(출하) : defect = 셸 안이든 어디든, 그룹이 battery/pcb/fc 가 아니면 전부 뺀다.
B판(대안) : 위에서 **«셸 안에만» 들어 있는 camera·motor·gear·accent** 는 도로 남긴다
            (= rcs_po 가 스스로 적은 «반투명 셸 뒤의 금속은 보인다» 를 그룹 이름이 아니라
              **상황**으로 적용한 판).
두 판의 σ 차이가 곧 «규칙 선택의 값어치» 다.
"""
import json
import os
import sys

import numpy as np

os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ.pop("MESH_FIX", None)
sys.path.insert(0, "/workspace/sionna/src")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adv_mesh_impact_l2_sigma_0816 import sampler, sigma, stats, METAL_GAMMA_5G, FC, C0, DIV, GEOMS

import mesh_buried as mb
from drones import DRONES, DRONE_GROUP_MAT, build_drone
from materials import gamma_po

RESCUE = ("camera", "motor", "gear", "accent")
gm = {g: (METAL_GAMMA_5G if m == "metal" else gamma_po(m, FC))
      for g, (m, _) in DRONE_GROUP_MAT.items()}
spacing = C0 / FC / DIV

out = {}
for k in sys.argv[1].split(","):
    m = build_drone(DRONES[k])
    r = mb._cached(m, True, False, 0.0)
    G, area = r["G"], r["area"]
    only_shell = r["in_shell"] & (~r["in_other"])
    defA = r["defect"]
    rescue = defA & only_shell & np.isin(G, list(RESCUE))
    defB = defA & (~rescue)
    keepA, keepB = ~defA, ~defB
    rec = dict(rescued_faces=int(rescue.sum()),
               rescued_mm2=round(float(area[rescue].sum()) * 1e6, 1),
               defA_mm2=round(float(area[defA].sum()) * 1e6, 1))
    P0, N0, A0, W0, _ = sampler(m, spacing, gm)
    PA, NA, AA, WA, _ = sampler(m, spacing, gm, face_keep=keepA)
    PB, NB, AB, WB, _ = sampler(m, spacing, gm, face_keep=keepB)
    for name, el, beta in GEOMS:
        s0 = sigma(P0, N0, A0, W0, el, beta)
        sA = sigma(PA, NA, AA, WA, el, beta)
        sB = sigma(PB, NB, AB, WB, el, beta)
        rec[name] = dict(
            off_dbsm=round(float(10 * np.log10(s0.mean())), 3),
            i3A_dbsm=round(float(10 * np.log10(sA.mean())), 3),
            i3B_dbsm=round(float(10 * np.log10(sB.mean())), 3),
            deltaA_db=round(float(10 * np.log10(sA.mean()) - 10 * np.log10(s0.mean())), 3),
            deltaB_db=round(float(10 * np.log10(sB.mean()) - 10 * np.log10(s0.mean())), 3),
            규칙차_db=round(float(10 * np.log10(sB.mean()) - 10 * np.log10(sA.mean())), 3))
    out[k] = rec
    print(f"[{k}] 되살린 면 {rec['rescued_faces']}장 {rec['rescued_mm2']:.0f} mm² "
          f"(결함의 {100*rec['rescued_mm2']/rec['defA_mm2']:.0f} %) | "
          + " ".join(f"{n}: A{rec[n]['deltaA_db']:+.2f} B{rec[n]['deltaB_db']:+.2f} "
                     f"(차 {rec[n]['규칙차_db']:+.2f})" for n, _, _ in GEOMS), flush=True)
    with open("/tmp/claude-0/-workspace/e9e31991-b542-4f3a-b8e2-570320d555ba/"
              "scratchpad/verify2/i3_sens.json", "w") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
