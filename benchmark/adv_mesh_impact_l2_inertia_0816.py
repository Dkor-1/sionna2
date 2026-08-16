# -*- coding: utf-8 -*-
"""검증 ⑤ — battery 합집합이 **부피·질량배분·관성텐서**를 바꾸나 (→ 로터 요동 모델로 내려간다)."""
import json
import os
import sys

import numpy as np

os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ.pop("MESH_FIX", None)
sys.path.insert(0, "/workspace/sionna/src")

from drones import DRONES
import gazebo_export as gx
import drone_cad as dc

out = {}
for k in sys.argv[1].split(","):
    s = DRONES[k]
    a = gx.inertia_from_mesh(s)
    b = gx.inertia_from_mesh(s, mesh_fix="battery")
    #  battery 그룹의 **부피** 직접 비교
    def vol(fix):
        A = dc.build_frame_cad(s, mesh_fix=fix)
        return round(sum(float(m.volume) for m in A.parts.get("battery", [])) * 1e9, 3), \
               len(A.parts.get("battery", []))
    v0, n0 = vol(None)
    v1, n1 = vol("battery")
    rec = dict(battery_vol_mm3=[v0, v1],
               battery_parts=[n0, n1],
               vol_delta_pct=round(100 * (v1 / v0 - 1), 3) if v0 else 0.0,
               mass_total_kg=[round(a["mass"], 6), round(b["mass"], 6)],
               density_scale=[round(a["density_scale"], 6), round(b["density_scale"], 6)],
               per_group_g={g: [round(a["per_group"].get(g, 0) * 1000, 2),
                                round(b["per_group"].get(g, 0) * 1000, 2)]
                            for g in sorted(set(a["per_group"]) | set(b["per_group"]))},
               com_mm=[[round(x * 1000, 3) for x in a["com"]],
                       [round(x * 1000, 3) for x in b["com"]]],
               I_diag=[[round(float(a["I"][i, i]), 8) for i in range(3)],
                       [round(float(b["I"][i, i]), 8) for i in range(3)]])
    rec["I_diag_delta_pct"] = [round(100 * (rec["I_diag"][1][i] / rec["I_diag"][0][i] - 1), 3)
                               if rec["I_diag"][0][i] else 0.0 for i in range(3)]
    rec["battery_mass_delta_g"] = round(rec["per_group_g"]["battery"][1]
                                        - rec["per_group_g"]["battery"][0], 2)
    out[k] = rec
    print(f"[{k}] battery 부피 {v0:.0f}→{v1:.0f} mm³ ({rec['vol_delta_pct']:+.2f} %) · "
          f"battery 질량 {rec['per_group_g']['battery'][0]:.1f}→"
          f"{rec['per_group_g']['battery'][1]:.1f} g ({rec['battery_mass_delta_g']:+.1f}) · "
          f"I 대각 Δ {rec['I_diag_delta_pct']} %", flush=True)
with open("/tmp/claude-0/-workspace/e9e31991-b542-4f3a-b8e2-570320d555ba/"
          "scratchpad/verify2/inertia.json", "w") as fh:
    json.dump(out, fh, ensure_ascii=False, indent=1)
