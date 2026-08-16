# -*- coding: utf-8 -*-
"""
mesh_fix_i4_m4_addendum_0816.py — 본 측정에서 **안 갈린 두 가지**를 갈라낸다 (2026-08-16)
==========================================================================================

① I4 union 판의 «예측 ↔ 실제» 차이는 무엇인가
   본 측정의 예측은 «캐노피 면 중 body 안» 만 뺐다. 그런데 불리언 합집합은 **양쪽**의 내부
   면을 없앤다 — 캐노피 안에 든 **body 면**도 사라진다. 그래서 예측이 실제보다 밝게 나온다.
   여기서는 **양방향 매몰면**을 뺀 예측을 만들어, 남는 차이가 재이산화의 몫임을 보인다.

② m4 수리 뒤 «동일평면» 잣대가 왜 커졌나
   면 중심 잣대는 클램프 끝면(삼각형 하나 349 mm²) 전체를 «동일평면» 으로 세는데, 실제로
   맞닿은 것은 새로 생긴 튜브 마개(원 하나 201 mm²)뿐이다. 두 값을 따로 잰다.

산출: outputs/mesh_layer2_buried_canopy_0816.json 의 `부록` 절로 병합.
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from mesh_fix_i4_m4_0816 import (CONFIGS, OUT, area_by_group, build_with, compare,   # noqa: E402
                                 drop_faces, group_solid, measure, points, sigma_band,
                                 source_state)
from drones import DRONES                                                    # noqa: E402
import trimesh                                                               # noqa: E402

UNION_KEYS = ("phantom4", "mini2", "mini5pro", "typhoonh480", "matrice4e")
BASE_IDS = {"mini2": ("i5",)}


def two_way_mask(mesh, ga="canopy", gb="body"):
    """ga 안에 든 gb 면 **과** gb 안에 든 ga 면을 함께 뺀 마스크(= 불리언이 없애는 면)."""
    V = np.asarray(mesh.v, float); F = np.asarray(mesh.f, int); G = np.asarray(mesh.g)
    tri = V[F]
    cen = tri.mean(axis=1)
    area = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
    keep = np.ones(len(F), bool)
    got = {}
    for victim, container in ((ga, gb), (gb, ga)):
        idx = np.where(G == victim)[0]
        sol = group_solid(mesh, [container])
        ins = np.zeros(len(idx), bool)
        for c in sol.split(only_watertight=False):
            if c.is_watertight:
                ins |= c.contains(cen[idx])
        keep[idx[ins]] = False
        got[f"{victim}_in_{container}_mm2"] = round(float(area[idx[ins]].sum()) * 1e6, 3)
        got[f"{victim}_in_{container}_faces"] = int(ins.sum())
    return keep, got


def run_i4_addendum():
    out = {}
    for key in UNION_KEYS:
        t0 = time.time()
        spec = DRONES[key]
        base = BASE_IDS.get(key, ())
        m_def = build_with(spec, base)
        m_rep = build_with(spec, tuple(base) + ("i4",))
        keep, got = two_way_mask(m_def)
        m_pred2 = drop_faces(m_def, keep)
        cmp_, sig_ref, _ = measure(spec, {"결함": m_def, "예측_양방향": m_pred2,
                                          "실제_수리후": m_rep}, "결함")
        out[key] = dict(양방향_매몰=got, σ=cmp_,
                        재이산화_몫_db={c: round(cmp_["실제_수리후"][c]["azimuth_mean_db"]
                                            - cmp_["예측_양방향"][c]["azimuth_mean_db"], 4)
                                    for c, _, _ in CONFIGS})
        print(f"  {key:12s} 양방향예측 "
              f"{[cmp_['예측_양방향'][c]['azimuth_mean_db'] for c, _, _ in CONFIGS]} ↔ 실제 "
              f"{[cmp_['실제_수리후'][c]['azimuth_mean_db'] for c, _, _ in CONFIGS]} "
              f"({time.time()-t0:.0f}s)", flush=True)
    return out


def near_area(mesh, ga, gb, tol=1e-6, zsel=None):
    """ga 면 중 gb 표면에서 tol 안인 면적[mm²]·면 수 (zsel 로 z 범위를 좁힐 수 있다)."""
    A = group_solid(mesh, [ga]); B = group_solid(mesh, [gb])
    cen = A.triangles_center
    d = np.abs(trimesh.proximity.ProximityQuery(B).signed_distance(cen))
    sel = d < tol
    if zsel is not None:
        sel &= (cen[:, 2] > zsel[0]) & (cen[:, 2] < zsel[1])
    return round(float(A.area_faces[sel].sum()) * 1e6, 3), int(sel.sum())


def run_m4_addendum():
    spec = DRONES["x500v2"]
    m_def = build_with(spec, ())
    m_rep = build_with(spec, ("m4",))
    z_seat = (0.0035, 0.0045)          # 시트 윗면 ↔ 카본판 아랫면이 만나는 z=4.0 mm 평면
    res = {}
    for tag, m in (("수리전", m_def), ("수리후", m_rep)):
        res[tag] = dict(
            accent가_arm에_닿은_면적_mm2=near_area(m, "accent", "arm"),
            arm이_accent에_닿은_면적_mm2=near_area(m, "arm", "accent"),
            그중_z4평면_시트x카본판_accent=near_area(m, "accent", "arm", zsel=z_seat),
            그중_z4평면_시트x카본판_arm=near_area(m, "arm", "accent", zsel=z_seat),
            그밖_클램프쪽_accent=near_area(m, "accent", "arm", zsel=(-1, 0.0035)),
            그밖_클램프쪽_arm=near_area(m, "arm", "accent", zsel=(-1, 0.0035)))
    #  새로 생긴 튜브 마개의 **참 면적** — 원 단면 π·8² 이 몇 개인가로 교차확인
    a0 = area_by_group(m_def)["arm"]; a1 = area_by_group(m_rep)["arm"]
    res["튜브_마개"] = dict(arm_면적_전_mm2=a0, arm_면적_후_mm2=a1, 차_mm2=round(a1 - a0, 3),
                        원단면_pi_r2_mm2=round(np.pi * 8.0 ** 2, 3),
                        마개_이론개수=16, 마개_이론면적_mm2=round(16 * np.pi * 8.0 ** 2, 3))
    print("  m4 부록:", json.dumps(res["튜브_마개"], ensure_ascii=False), flush=True)
    return res


if __name__ == "__main__":
    t0 = time.time()
    print("I4 부록 — 양방향 매몰면 예측", flush=True)
    a = run_i4_addendum()
    print("m4 부록 — 동일평면 잣대 분해", flush=True)
    b = run_m4_addendum()
    p = OUT + ".part"
    d = json.load(open(p))
    d["부록"] = {"I4_양방향_예측": a, "m4_동일평면_분해": b,
               "소스지문": source_state(),
               "seconds": round(time.time() - t0, 1)}
    json.dump(d, open(p, "w"), ensure_ascii=False, indent=1)
    print("merged into", p, round(time.time() - t0, 1), "s")
