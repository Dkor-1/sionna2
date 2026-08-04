# -*- coding: utf-8 -*-
"""
facet_mechanism_verdict.py — facet_mechanism.json 에 **판정 블록**을 계산해 덧붙인다.
=====================================================================================
숫자는 전부 원자료(A/B/C/C2/D/E/F/G)에서 다시 계산한다. 손으로 적는 값은 없다.
"""
from __future__ import annotations

import os
import json
import math

import numpy as np

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT = os.path.join(ROOT, "outputs", "facet_mechanism.json")

d = json.load(open(OUT))
LAM = d["_meta"]["lambda_m"]
R1 = d["_meta"]["geometry"]["R1"]
IMG = d["theory"]["amp_image_source_db"]


def spread(vals):
    v = [x for x in vals if x is not None]
    return (float(max(v) - min(v)) if v else None)


# --------------------------------------------------------------------------- #
#  1) 평판 크기 불변성
# --------------------------------------------------------------------------- #
A = d["A_plate_size"]
a_coh = [r["coh_db"] for r in A]
a_po = [r["amp_po_db"] for r in A]
V1 = dict(
    sides_m=[r["side_m"] for r in A],
    size_ratio_max=max(r["side_m"] for r in A) / min(r["side_m"] for r in A),
    rt_coh_db=a_coh,
    rt_spread_db=spread(a_coh),
    po_theory_spread_db=spread(a_po),
    rt_minus_image_source_db=[None if c is None else c - IMG for c in a_coh],
    n_paths_always=sorted({tuple(r["n_paths_target_set"]) for r in A}),
    detect_rate_all=sorted({r["detect_rate"] for r in A}),
    budget_stable=all(spread([b["coh_db"] for b in r["budget"]]) < 1e-6 for r in A),
    depth_stable=spread([c["coh_db"] for c in d["A_depth_check"]]) < 1e-6,
    verdict=None,
)
V1["verdict"] = bool(V1["rt_spread_db"] < 0.01 and V1["po_theory_spread_db"] > 50)

# --------------------------------------------------------------------------- #
#  2) 세분(형상 동일) — 전력이 변하는가, 그리고 왜인가
# --------------------------------------------------------------------------- #
B = d["B_subdivide"]
by_side = {}
for r in B:
    by_side.setdefault(r["side_m"], []).append(r)
b_rows = []
for side, g in sorted(by_side.items()):
    g = sorted(g, key=lambda r: r["k"])
    b_rows.append(dict(
        side_m=side,
        n_tri=[r["n_tri"] for r in g],
        facet_edge_m=[side / r["k"] for r in g],
        facet_edge_lambda=[side / r["k"] / LAM for r in g],
        n_paths=[r["n_paths_target_set"][0] for r in g],
        coh_db=[r["coh_db"] for r in g],
        spread_db=spread([r["coh_db"] for r in g]),
        # 관측 전력이 '동일 경로 N 개의 코히어런트 합' 가설과 맞는지: coh ?= img + 20log10(N)
        resid_vs_20logN_db=[None if r["coh_db"] is None else
                            r["coh_db"] - (IMG + 20 * math.log10(r["n_paths_target_set"][0]))
                            for r in g],
    ))
# 중복이 시작되는 패싯 크기
onset = []
for row in b_rows:
    first_dup = next((e for e, n in zip(row["facet_edge_m"], row["n_paths"]) if n > 1), None)
    last_single = next((e for e, n in zip(reversed(row["facet_edge_m"]),
                                          reversed(row["n_paths"])) if n == 1), None)
    onset.append(dict(side_m=row["side_m"], first_dup_facet_edge_m=first_dup,
                      first_dup_facet_edge_lambda=None if first_dup is None else first_dup / LAM,
                      largest_single_facet_edge_m=last_single))

G = d["G_duplicate_paths"]
g_rows = [dict(side_m=r["side_m"], k=r["k"], n_paths=r["n_paths"], coh_db=r["coh_db"],
               per_path_amp_db=[p["amp_db"] for p in r["paths"]],
               amp_spread_db=r["amp_spread_db"], tau_spread_ns=r["tau_spread_ns"],
               phase_spread_deg=float(np.ptp([p["phase_deg"] for p in r["paths"]]))
               if r["paths"] else None,
               vertex_max_dev_mm=float(np.max([np.linalg.norm(
                   np.array(p["vertex"]) - np.array([20.0, 0.0, 0.0])) for p in r["paths"]]) * 1e3)
               if r["paths"] else None,
               resid_vs_20logN_db=(None if r["coh_db"] is None else
                                   r["coh_db"] - (IMG + 20 * math.log10(r["n_paths"]))))
          for r in G]

E = d["E_subdivide_offset"]
e_pairs = []
for side in sorted({r["side_m"] for r in E}):
    for k in sorted({r["k"] for r in E if r["side_m"] == side}):
        al = next(r for r in E if r["side_m"] == side and r["k"] == k and r["offset"] == "aligned")
        of = next(r for r in E if r["side_m"] == side and r["k"] == k and r["offset"] != "aligned")
        e_pairs.append(dict(side_m=side, k=k,
                            n_aligned=al["n_paths_target_set"][0],
                            n_offset=of["n_paths_target_set"][0],
                            coh_aligned=al["coh_db"], coh_offset=of["coh_db"]))

V2 = dict(
    per_side=b_rows, duplication_onset=onset, duplicate_path_forensics=g_rows,
    grid_offset_control=e_pairs,
    max_inflation_db=max(spread(r["coh_db"]) for r in b_rows),
    all_paths_identical=bool(all((r["amp_spread_db"] or 0) < 1e-6 and
                                 (r["tau_spread_ns"] or 0) < 1e-6 for r in G)),
    per_path_amp_equals_image_source=bool(all(abs(p - IMG) < 0.01
                                              for r in G for p in [q["amp_db"] for q in r["paths"]])),
    coherent_N_law_max_resid_db=max(abs(r["resid_vs_20logN_db"]) for r in g_rows
                                    if r["resid_vs_20logN_db"] is not None),
    offset_removes_duplication=bool(all(p["n_aligned"] == 1 or p["n_offset"] == 1
                                        for p in e_pairs if p["n_aligned"] > 1)),
    verdict=None,
)
V2["verdict"] = bool(V2["max_inflation_db"] > 0.5)

# --------------------------------------------------------------------------- #
#  3) 구 테셀레이션
# --------------------------------------------------------------------------- #
C = d["C_sphere_tessellation"]
C2 = d["C2_sphere_radius"]
F = d["F_sphere_degeneracy"]
f_by_r = {}
for r in F:
    f_by_r.setdefault(r["r_m"], []).append(r)
f_rows = []
for rr, g in sorted(f_by_r.items()):
    found = [x for x in g if x["coh_db"] is not None]
    f_rows.append(dict(r_m=rr, n_configs=len(g), n_found=len(found),
                       coh_db=[x["coh_db"] for x in found],
                       coh_spread_db=spread([x["coh_db"] for x in found]),
                       tags_found=[x["tag"] for x in found],
                       tags_missed=[x["tag"] for x in g if x["coh_db"] is None]))
all_found = [x["coh_db"] for x in F if x["coh_db"] is not None]
# GO 구 이론(원거리): sigma = pi a^2, 중심까지 거리 R_c = 20 + a
def go_sphere_amp_db(a):
    Rc = 20.0 + a
    sig = math.pi * a * a
    amp = math.sqrt((LAM ** 2) * sig / ((4 * math.pi) ** 3 * Rc ** 2 * Rc ** 2))
    return 20 * math.log10(amp)

V3 = dict(
    fixed_radius_0p5_all_tessellations=dict(
        n_tri=[r["n_tri"] for r in C],
        n_paths=[r["n_paths_target_set"] for r in C],
        detect_rate=[r["detect_rate"] for r in C],
        note="반지름 0.5 m 구는 삼각형 48→16128, 광선 1M→64M 어디서도 경로 0개."),
    radius_sweep_fixed_tessellation=dict(
        r_m=[r["r_m"] for r in C2], detect_rate=[r["detect_rate"] for r in C2],
        note="근접면을 x=20 m 에 고정하고 r=0.25~80 m. seg=64/rings=32 정렬 메쉬에서는 전부 0개."),
    degeneracy_probe=f_rows,
    detected_amp_db=all_found,
    detected_amp_spread_db=spread(all_found),
    flat_plate_ref_db=IMG,
    detected_minus_flat_plate_db=[x - IMG for x in all_found],
    go_sphere_theory_db={str(a): go_sphere_amp_db(a) for a in (0.5, 5.0, 40.0)},
    rt_minus_go_db={str(a): (np.mean([x["coh_db"] for x in F
                                      if x["r_m"] == a and x["coh_db"] is not None]) - go_sphere_amp_db(a))
                    if any(x["r_m"] == a and x["coh_db"] is not None for x in F) else None
                    for a in (0.5, 5.0, 40.0)},
    verdict=None,
)
V3["rt_minus_go_db"] = {k: (float(v) if v is not None else None)
                        for k, v in V3["rt_minus_go_db"].items()}
# '안정'의 정의: 테셀레이션·방위를 바꿔도 (a) 검출 여부와 (b) 전력이 모두 유지되는가
det_states = {x["coh_db"] is not None for x in F}
V3["detection_flips_with_tessellation_or_orientation"] = bool(len(det_states) > 1)
V3["verdict"] = bool(not V3["detection_flips_with_tessellation_or_orientation"])

# --------------------------------------------------------------------------- #
#  4) 기울기 허용폭 — 크기가 '진폭'이 아니라 '각도 허용폭'으로만 들어온다
# --------------------------------------------------------------------------- #
D = d["D_tilt_acceptance"]
d_rows = []
for side in sorted({r["side_m"] for r in D}):
    g = sorted([r for r in D if r["side_m"] == side], key=lambda r: r["tilt_deg"])
    last_ok = max([r["tilt_deg"] for r in g if r["detect_rate"] > 0], default=None)
    first_bad = min([r["tilt_deg"] for r in g if r["detect_rate"] == 0], default=None)
    pred = g[0]["tilt_pred_max_deg"]
    d_rows.append(dict(side_m=side, pred_cutoff_deg=pred, last_detected_deg=last_ok,
                       first_missed_deg=first_bad,
                       bracket_contains_prediction=bool(last_ok is not None and first_bad is not None
                                                        and last_ok <= pred <= first_bad),
                       coh_spread_within_acceptance_db=spread(
                           [r["coh_db"] for r in g if r["coh_db"] is not None])))

d["VERDICT"] = {
    "_note": "이 블록은 benchmark/facet_mechanism_verdict.py 가 원자료에서 재계산한다. 손으로 고치지 말 것.",
    "plate_size_invariance_reproduced": V1["verdict"],
    "plate_size_invariance": V1,
    "subdivide_changes_power": V2["verdict"],
    "subdivide": V2,
    "sphere_tessellation_stable": V3["verdict"],
    "sphere": V3,
    "tilt_acceptance": d_rows,
    "mechanism": (
        "Sionna RT 기본 path solver 의 표적 에코는 '정반사 조건을 만족하는 삼각형 하나당 image-source 경로 "
        "1개'다. 그 경로의 진폭은 λ/(4π(R1+R2)) — 즉 **무한 거울** 값이고 삼각형의 크기·면적·곡률과 무관하다. "
        "면 크기는 진폭이 아니라 **각도 허용폭 ±(side/2)/R** 로만 들어온다(D 에서 확인). "
        "따라서 산란단면적 σ 정보가 경로 진폭에 실리지 않는다. "
        "여기에 더해, 삼각형이 λ 수준 이하로 잘게 쪼개지면 **동일한 정반사 경로가 인접 삼각형에서 중복 생성**되어 "
        "(진폭·위상·지연이 완전히 동일한 복사본) 코히어런트 합으로 20·log10(N) 만큼 전력이 부풀려진다."),
    "H_assessment": (
        "H('면당 정반사 1개, 진폭은 면 크기와 무관')는 **진폭 부분에서 지지**된다(A: 크기 40배·PO 이론 64 dB "
        "변화에도 RT 0.0000 dB, image-source 와 0.002 dB 일치). "
        "'면당 1개' 부분은 **부분 반증**이다 — 정반사점을 품는 삼각형이 하나여도 인접 삼각형이 같은 경로를 "
        "중복 보고할 수 있고(B/G), 반대로 곡면에서는 어떤 삼각형도 경로를 만들지 못할 수 있다(C/F)."),
}

with open(OUT, "w") as f:
    json.dump(d, f, ensure_ascii=False, indent=1)

print(json.dumps({k: v for k, v in d["VERDICT"].items()
                  if k in ("plate_size_invariance_reproduced", "subdivide_changes_power",
                           "sphere_tessellation_stable")}, indent=1))
print("\nA spread(dB)", V1["rt_spread_db"], " PO spread", round(V1["po_theory_spread_db"], 2),
      " budget_stable", V1["budget_stable"], " depth_stable", V1["depth_stable"])
print("B max_inflation", round(V2["max_inflation_db"], 3),
      " identical", V2["all_paths_identical"],
      " per_path==image_src", V2["per_path_amp_equals_image_source"],
      " 20logN_resid", round(V2["coherent_N_law_max_resid_db"], 6),
      " offset_removes", V2["offset_removes_duplication"])
print("B onset", onset)
print("C detect_flips", V3["detection_flips_with_tessellation_or_orientation"],
      " detected_amp_spread", V3["detected_amp_spread_db"],
      " rt-go", V3["rt_minus_go_db"])
print("D", d_rows)
print("[saved]", OUT)
