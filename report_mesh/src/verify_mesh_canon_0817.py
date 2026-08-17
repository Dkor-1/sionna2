# -*- coding: utf-8 -*-
"""verify_mesh_canon_0817.py — **정본 판**에서 기하·치수 원장을 다시 재는 측정기.

왜 이 파일이 있나
  `report_mesh/outputs/mesh_verify.json` 은 2026-08-16 13:15 에 잰 원장이다. 그 뒤
  ① 치수 값 적용 라운드와 ② 정본 전환(`MESH_FIX_CANON=("battery","i5")` ·
  `BLADE_LAW_CANON="per_airframe"`)이 지나갔으므로, 그 원장의 A/B/C/D/F/G 절은
  **다른 세대의 메쉬**를 잰 수다. 리포트가 그 수를 현재형으로 쓰면 세대가 섞인다.

  ⇒ 이 스크립트는 **같은 잣대**(verify_mesh_suite 의 sec_* 함수를 그대로 부른다)로
     정본 판을 다시 재서 `mesh_verify_canon_0817.json` 에 남긴다. 정의가 갈리면
     사과-대-사과가 깨지므로 함수를 다시 짜지 않고 **그대로 재사용**한다.

무엇을 안 담나 (정직하게)
  · **H(PO 점간격 수렴)·I(SBR 이중검사)** — 이 라운드는 GPU 를 안 쓴다(정본 재계산이
    카드를 쓰는 중). H 는 CPU 로도 되지만 같은 라운드 규약으로 미룬다. 두 절의 결론은
    «적분기·광선기의 성질» 이라 형상 세대와 무관하고, 절대 면 수·σ 는 옛 세대의 수다.
  · 재질(E) — mesh06 이 쓰는 절이라 이 파일의 담당이 아니다.

⛔ 이 파일은 **읽기 전용 측정기**다. 형상 상수도, 검사기도, 기존 원장도 건드리지 않는다.

재현:
    PYTHONPATH=src:benchmark python report_mesh/src/verify_mesh_canon_0817.py
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RM = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(RM, ".."))
for p in (os.path.join(ROOT, "src"), HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

import geom                                    # noqa: E402  (정본 스위치의 단일 진리원)
import verify_mesh_suite as S                  # noqa: E402  (잣대 재사용 — 정의를 다시 안 짠다)
from drones import DRONES, build_drone         # noqa: E402
from mesh_check import (                       # noqa: E402
    check_buried_faces, check_mesh, check_prop_bell_solid,
    BURIED_FACE_BUDGET_PCT, SLIVER_BUDGET, SLIVER_BUDGET_BLADE_LAW,
    PROP_BELL_SOLID_AREA_PCT, PROP_BELL_SOLID_AREA_PCT_BLADE_LAW,
)

LAM_HI_MM = 299_792_458.0 / 5.21e9 * 1e3       # 최고 대역(WiFi 5.21 GHz) 파장 — suite 와 같은 잣대


def prop_triangle_stats(mesh) -> dict:
    """프로펠러 그룹 **만** 의 삼각형 크기. 함대 표에 섞어 읽으면 안 되는 축이라 따로 잰다.

    정의는 sec_A_geometry 의 엣지 잣대와 같다(세 변의 길이 [mm], 백분위수)."""
    V = np.asarray(mesh.v, float)
    F = np.asarray(mesh.f, int)
    G = np.asarray(mesh.g)
    sel = G == "prop"
    if not sel.any():
        return dict(has_prop=False)
    f = F[sel]
    E = np.concatenate([V[f[:, 1]] - V[f[:, 0]],
                        V[f[:, 2]] - V[f[:, 1]],
                        V[f[:, 0]] - V[f[:, 2]]])
    el = np.linalg.norm(E, axis=1) * 1000.0
    return dict(has_prop=True, n_faces=int(sel.sum()),
                share_pct=round(100.0 * float(sel.sum()) / len(F), 2),
                edge_mm=dict(p50=float(np.percentile(el, 50)),
                             p95=float(np.percentile(el, 95)), max=float(el.max())),
                edge_vs_lam=dict(p95_over_lam=float(np.percentile(el, 95) / LAM_HI_MM),
                                 max_over_lam=float(el.max() / LAM_HI_MM)))


def main():
    t0 = time.time()
    keys = list(DRONES.keys())
    print("정본 스위치 — MESH_FIX:", sorted(geom.mesh_fix_set()),
          "· BLADE_LAW:", geom.blade_law_canon(), flush=True)

    meshes, budgets, buried, propbell, proptri = {}, {}, {}, {}, {}
    for k in keys:
        t = time.time()
        m = build_drone(DRONES[k])
        meshes[k] = m
        r = check_mesh(m, k)
        budgets[k] = dict(
            slivers=r["slivers"], sliver_budget=r["sliver_budget"],
            sliver_ok=r["sliver_ok"],
            boundary_edges=int(sum(g["boundary_edges"] for g in r["groups"].values())),
            boundary_edge_budget=int(sum(g["boundary_edge_budget"]
                                         for g in r["groups"].values())),
            group_overlap_max_pct=max(g["overlap_pct"] for g in r["groups"].values()),
            nonmanifold_edges=int(sum(g["nonmanifold_edges"] for g in r["groups"].values())),
            ok=r["ok"],
        )
        b = check_buried_faces(DRONES[k], mesh=m)
        buried[k] = {kk: b[kk] for kk in
                     ("buried_pct", "design_intent_pct", "defect_pct", "defect_area_mm2",
                      "budget_pct", "blind_containers", "patched_containers", "ok")}
        pb = check_prop_bell_solid(DRONES[k], mesh=m)
        propbell[k] = {kk: pb.get(kk) for kk in
                       ("area_pct", "budget_pct", "nonwatertight_bell_parts", "ok")}
        proptri[k] = prop_triangle_stats(m)
        print(f"  {k:12s} 면 {len(m.f):6,} · 슬리버 {r['slivers']:4d}/{r['sliver_budget']:4d}"
              f" · 매몰(진짜결함) {buried[k]['defect_pct']:5.2f}/{buried[k]['budget_pct']:4.1f} %"
              f"  {time.time() - t:4.1f}s", flush=True)

    print("A_geometry …", flush=True); A = S.sec_A_geometry(meshes)
    print("B_symmetry …", flush=True); B = S.sec_B_symmetry(meshes)
    print("C_dims …", flush=True);     C = S.sec_C_dims(DRONES)
    print("D_volume …", flush=True);   D = S.sec_D_volume(meshes, DRONES)
    print("F_overlap …", flush=True);  F = S.sec_F_overlap(meshes)
    print("G_scan …", flush=True);     G = S.sec_G_scan(meshes)

    out = dict(
        _meta=dict(
            title="정본 판 기하·치수 원장 (A/B/C/D/F/G) — 2026-08-17",
            generated_kst=time.strftime("%Y-%m-%d %H:%M KST"),
            script="report_mesh/src/verify_mesh_canon_0817.py",
            mesh_fix=sorted(geom.mesh_fix_set()),
            blade_law=geom.blade_law_canon(),
            file_tag="_mfixbatteryi5_blperairframe",
            drones=keys,
            lam_hi_mm=LAM_HI_MM,
            fc_ghz=S.FC / 1e9,
            mesh_engine="trimesh+manifold3d (drone_cad)",
            reuses="report_mesh/src/verify_mesh_suite.py 의 sec_A/B/C/D/F/G 를 그대로 부른다",
            not_included=["H_po_convergence(이 라운드 GPU·계산 금지 규약으로 미룸)",
                          "I_sbr_subdiv(GPU)", "E_materials(mesh06 담당)"],
            legacy_ledger="report_mesh/outputs/mesh_verify.json (2026-08-16 13:15, 옛 세대)",
            compute="CPU only",
        ),
        A_geometry=A, B_symmetry=B, C_dims=C, D_volume=D, F_overlap=F, G_scan=G,
        budget_usage=budgets, buried_faces=buried, prop_bell_solid=propbell,
        prop_triangles=proptri,
        budget_tables=dict(
            sliver_budget={k: v for k, v in SLIVER_BUDGET.items() if not isinstance(k, tuple)},
            sliver_budget_blade_law={f"{a}|{b}": v
                                     for (a, b), v in SLIVER_BUDGET_BLADE_LAW.items()},
            buried_face_budget_pct=dict(BURIED_FACE_BUDGET_PCT),
            prop_bell_solid_pct=dict(PROP_BELL_SOLID_AREA_PCT),
            prop_bell_solid_pct_blade_law={f"{a}|{b}": v for (a, b), v
                                           in PROP_BELL_SOLID_AREA_PCT_BLADE_LAW.items()},
        ),
        runtime_s=round(time.time() - t0, 1),
    )
    p = os.path.join(RM, "outputs", "mesh_verify_canon_0817.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("wrote", p, f"({out['runtime_s']:.0f} s)")


if __name__ == "__main__":
    main()
