# -*- coding: utf-8 -*-
"""
ptd_drone_effect_addendum.py — 검증 3 부록 진단 (ptd_drone_effect.json 을 **덧붙여 갱신**)

세 가지를 더 묻는다. 셋 다 본 실험 결과의 **해석을 바꾸는** 것들이다.

  A. 어느 부위가 PTD 를 받는가 — 그룹별 금속 모서리 길이.
     (metal_only=True 이므로 |Γ|≥0.999 인 면만. carbon |Γ|=0.90 은 제외된다.)
  B. ⭐ **sharp_deg 문턱 민감도** — 유지된 '금속 모서리' 의 절반쯤은 |α−180°| 가 5~10° 인
     **모터 원통의 테셀레이션 이음매**다. 진짜 모서리가 아니라 매끄러운 곡면을 다면체로
     자른 자국이다. 문턱을 올려 그것들을 버렸을 때 Δσ 가 무너지면, 드론 수준의 PTD 효과는
     물리가 아니라 **메쉬 인공물**이라는 뜻이다. (docs §3.7 이 경고한 바로 그 실패양식)
  C. 모서리 추출 비용의 **정직한 상각** — 추출은 기체당 1회, 주파수 무관이다. 120 자세
     묶음에 상각하면 과대평가된다. 생산 격자(기체당 48,600 자세)에 상각한 값도 같이 낸다.

CPU 전용.
    PYTHONPATH=src python benchmark/ptd_drone_effect_addendum.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_SRC = os.path.join(ROOT, "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import ptd_edges as pe                                                    # noqa: E402
from rcs_po import C0, mesh_to_points, dbsm                               # noqa: E402
from drones import DRONES, build_drone, drone_gamma_map                   # noqa: E402
from geom import Mesh                                                     # noqa: E402

DST = os.path.join(ROOT, "outputs", "ptd_drone_effect.json")
AZ = np.arange(0.0, 360.0, 3.0)
EL = -2.0
FCS = [1.843e9, 3.500e9, 5.210e9]
SHARP = [5.0, 8.0, 10.0, 15.0, 20.0, 30.0]
PROD_POSES_PER_AIRFRAME = 48600      # runtime_benchmark.json whole_published_grid


def group_metal_edges(mesh, gm):
    V = np.asarray(mesh.v); F = np.asarray(mesh.f); G = list(mesh.g)
    out = Counter()
    for g in sorted(set(G)):
        idx = [i for i, gg in enumerate(G) if gg == g]
        sub = Mesh(g); vmap = {}
        for fi in idx:
            tri = []
            for vi in F[fi]:
                if vi not in vmap:
                    vmap[vi] = sub.add_vertex(*V[vi])
                tri.append(vmap[vi])
            sub.add_tri(*tri, group=g)
        e = pe.extract_edges(sub, gamma=gm)
        if e.stats["length_metal_m"] > 1e-6:
            out[g] = float(e.stats["length_metal_m"])
    return dict(out.most_common())


def main():
    with open(DST, encoding="utf-8") as fh:
        D = json.load(fh)

    add = {"note": ("addendum diagnostics written by benchmark/ptd_drone_effect_addendum.py; "
                    "they reinterpret the main table, they do not replace it")}

    for key in list(D["drones"]):
        spec = DRONES[key]
        mesh = build_drone(spec)
        gm = drone_gamma_map(spec)
        rec = {"gamma_by_group": {g: float(v) for g, v in gm.items()}}

        # ---- A. 그룹별 금속 모서리 ------------------------------------------------ #
        rec["metal_edge_length_m_by_group"] = group_metal_edges(mesh, gm)
        rec["metal_edge_note"] = (
            "PTD attaches only where BOTH adjacent faces have |Gamma| >= 0.999 (metal_only=True). "
            "carbon |Gamma|=0.90, plastic 0.28, pcb 0.80 are all excluded, so the open carbon "
            "truss of s1000plus contributes NOTHING. What remains is dominated by the motor "
            "cylinders and the battery box.")

        # ---- B. 문턱 민감도 --------------------------------------------------- #
        es5 = pe.extract_edges(mesh, gamma=gm)
        sel = es5.gmin >= 0.999
        dev = np.abs(np.degrees(es5.Nw[sel] * np.pi) - 180.0)
        L = es5.L[sel]
        rec["metal_edge_dihedral_deviation"] = {
            "definition": "|alpha - 180 deg| of the kept metal edges; 0 = perfectly flat seam",
            "length_m_total": float(L.sum()),
            "length_m_dev_5_10deg": float(L[(dev >= 5) & (dev < 10)].sum()),
            "length_m_dev_10_20deg": float(L[(dev >= 10) & (dev < 20)].sum()),
            "length_m_dev_20_45deg": float(L[(dev >= 20) & (dev < 45)].sum()),
            "length_m_dev_ge_45deg": float(L[dev >= 45].sum()),
            "pct_length_dev_below_10deg": float(100 * L[dev < 10].sum() / L.sum()),
            "median_segment_length_mm": float(1e3 * np.median(L)),
            "reading": ("edges with |alpha-180| of 5-10 deg on a MOTOR CYLINDER are tessellation "
                        "seams of a smooth surface, not physical edges. doc 3.7 predicts they are "
                        "weak individually but can stack coherently around the rim."),
        }

        sweep = {}
        edgesets = {sd: pe.extract_edges(mesh, gamma=gm, sharp_deg=sd) for sd in SHARP}
        for fc in FCS:
            lam = C0 / fc
            P, Nv, dA, w = mesh_to_points(mesh, lam / 7.0, gamma=gm)
            E = np.zeros(len(AZ), complex)
            for s in range(0, len(AZ), 24):
                E[s:s + 24] = pe._po_field_dirs(P, Nv, dA, fc, AZ[s:s + 24], EL, w=w)
            K = 4 * np.pi / lam ** 2
            sig_po = K * np.abs(E) ** 2
            U = pe._look_dirs(AZ, EL)
            row = {"sigma_po_mean_dbsm": float(dbsm(sig_po.mean()))}
            for sd in SHARP:
                es = edgesets[sd]
                A = np.zeros(len(AZ), complex)
                Lu = 0.0
                t0 = time.perf_counter()
                for i, u in enumerate(U):
                    A[i], m = pe.edge_field(es, fc, u, pol="V")
                    Lu += m["length_used_m"]
                t = time.perf_counter() - t0
                sig = K * np.abs(E + A) ** 2
                mL = float(es.L[es.gmin >= 0.999].sum())
                row[f"sharp_deg={sd:g}"] = dict(
                    n_metal_edges=int((es.gmin >= 0.999).sum()),
                    L_metal_m=mL,
                    L_used_m_per_pose=Lu / len(AZ),
                    sigma_ptd_mean_dbsm=float(dbsm(sig.mean())),
                    delta_mean_db=float(dbsm(sig.mean()) - dbsm(sig_po.mean())),
                    t_edge_ms_per_pose=1e3 * t / len(AZ))
            sweep[f"{fc/1e9:.3f}GHz"] = row
            print(f"  {key} {fc/1e9:.3f} GHz  PO {row['sigma_po_mean_dbsm']:+7.2f} | " +
                  "  ".join(f"sd{sd:g}: {row[f'sharp_deg={sd:g}']['delta_mean_db']:+6.2f} dB "
                            f"(L {row[f'sharp_deg={sd:g}']['L_metal_m']:.1f} m)" for sd in SHARP),
                  flush=True)
        rec["sharp_deg_sweep"] = sweep
        d5 = np.array([sweep[f"{fc/1e9:.3f}GHz"]["sharp_deg=5"]["delta_mean_db"] for fc in FCS])
        d30 = np.array([sweep[f"{fc/1e9:.3f}GHz"]["sharp_deg=30"]["delta_mean_db"] for fc in FCS])
        rec["sharp_deg_verdict"] = dict(
            mean_delta_db_at_5deg=float(d5.mean()), mean_delta_db_at_30deg=float(d30.mean()),
            collapse_db=float(d5.mean() - d30.mean()),
            artifact_dominated=bool(abs(d5.mean() - d30.mean()) > 3.0),
            reading=("if raising the sharp-edge gate from 5 to 30 deg collapses the effect, the "
                     "drone-level PTD result is governed by tessellation seams, not by physical "
                     "edges. 30 deg keeps only genuinely sharp features."))
        add[key] = rec

    # ---- C. 추출 비용 상각 정정 --------------------------------------------- #
    rows = D["cost"]["rows"]
    fix = {}
    for key, dd in D["drones"].items():
        tex = dd["t_extract_edges_s"]
        rr = [r for r in rows if r["drone"] == key and r["pol"] == "V"]
        edge = float(np.median([r["t_edge_ms_per_pose"] for r in rr]))
        po = float(np.median([r["po_only_ms_per_pose"] for r in rr]))
        fix[key] = dict(
            t_extract_s=tex,
            amortized_over_120_poses_ms=1e3 * tex / 120,
            amortized_over_production_grid_ms=1e3 * tex / PROD_POSES_PER_AIRFRAME,
            po_only_median_ms=po, edge_median_ms=edge,
            po_plus_ptd_median_ms_realistic=po + edge + 1e3 * tex / PROD_POSES_PER_AIRFRAME,
            increase_pct_realistic=100 * (edge + 1e3 * tex / PROD_POSES_PER_AIRFRAME) / po)
    fix["note"] = (f"edge extraction is ONE-OFF per airframe and frequency-independent. The main "
                   f"table amortized it over a single 120-pose batch, which over-charges it by "
                   f"{PROD_POSES_PER_AIRFRAME/120:.0f}x. The production grid is "
                   f"{PROD_POSES_PER_AIRFRAME} poses per airframe "
                   f"(outputs/runtime_benchmark.json whole_published_grid).")
    add["extraction_amortisation_correction"] = fix

    D["addendum"] = add
    with open(DST, "w") as fh:
        json.dump(D, fh, indent=1, ensure_ascii=False)
    print(f"\n갱신: {DST}")
    return add


if __name__ == "__main__":
    main()
