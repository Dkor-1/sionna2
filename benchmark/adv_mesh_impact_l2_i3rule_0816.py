# -*- coding: utf-8 -*-
"""검증 ④ — i3 «결함» 판정 규칙이 저장소 자신의 물리 근사와 일치하나.

물음: `rcs_po` 는 «반투명 셸을 통과해 **내부 금속이 보인다**» 를 1차 근사로 쓴다고 스스로 적는다.
      `mesh_buried` 는 그 «보이는 내부» 를 **battery·pcb·fc 세 그룹만** 인정한다
      (INTERNAL_GROUPS). 그러면 **셸 안에만 들어 있는 camera·motor·accent·gear** 면은
      같은 상황인데도 «결함» 으로 지워진다. 얼마나 지워지나?
"""
import json
import os
import sys

import numpy as np

os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ.pop("MESH_FIX", None)
sys.path.insert(0, "/workspace/sionna/src")

import mesh_buried as mb
from drones import DRONES, build_drone

KEYS = sys.argv[1].split(",") if len(sys.argv) > 1 else ["mavic4pro"]
out = {}
for k in KEYS:
    m = build_drone(DRONES[k])
    r = mb._cached(m, True, False, 0.0)
    G, area = r["G"], r["area"]
    only_shell = r["in_shell"] & (~r["in_other"])       # 셸 **안에만** 들어 있다
    defect = r["defect"]
    tot_def = float(area[defect].sum()) * 1e6
    rec = dict(defect_area_mm2=round(tot_def, 1), defect_faces=int(defect.sum()))
    rows = {}
    for g in sorted(set(G.tolist())):
        sel = defect & (G == g)
        if not sel.any():
            continue
        sel_shell = sel & only_shell
        rows[g] = dict(
            defect_mm2=round(float(area[sel].sum()) * 1e6, 1),
            그중_셸안에만_mm2=round(float(area[sel_shell].sum()) * 1e6, 1),
            faces=int(sel.sum()))
    rec["그룹별"] = rows
    rec["셸안에만_있는데_지워지는_면적_mm2"] = round(
        float(area[defect & only_shell].sum()) * 1e6, 1)
    rec["그_비중_pct"] = round(100 * float(area[defect & only_shell].sum())
                             / max(float(area[defect].sum()), 1e-30), 2)
    out[k] = rec
    print(f"[{k}] 결함 {rec['defect_area_mm2']:.0f} mm² 중 «셸 안에만» "
          f"{rec['셸안에만_있는데_지워지는_면적_mm2']:.0f} mm² ({rec['그_비중_pct']} %)", flush=True)
    for g, v in sorted(rows.items(), key=lambda kv: -kv[1]["defect_mm2"]):
        print(f"    {g:10s} 결함 {v['defect_mm2']:9.1f} mm²  그중 셸안에만 "
              f"{v['그중_셸안에만_mm2']:9.1f} mm²")
with open("/tmp/claude-0/-workspace/e9e31991-b542-4f3a-b8e2-570320d555ba/"
          "scratchpad/verify2/i3_rule.json", "w") as fh:
    json.dump(out, fh, ensure_ascii=False, indent=1)
