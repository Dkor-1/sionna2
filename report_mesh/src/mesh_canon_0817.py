# -*- coding: utf-8 -*-
"""mesh_canon_0817.py — **정본 판(2026-08-17) 실측 원장**의 생성기 겸 로더.

왜 이 파일이 있나
  `report_mesh/src/mesh_facts_0816.py` 가 읽는 원장들은 **정본 전환 이전**에 잰 것이다.
  정본은 두 스위치가 기본으로 켜진 판이다 — `geom.MESH_FIX_CANON`(battery·i5) 와
  `geom.BLADE_LAW_CANON`(per_airframe). 형상이 다르므로 면 수·경계 모서리·매몰면이
  전부 다른 값이고, 옛 원장의 수를 그대로 실으면 리포트가 **다른 판의 메쉬**를 설명한다.

  ⇒ 정본 판에서 **다시 잰** 수를 한 파일에 모은다. 리포트 생성기는 여기서 받아 주입만 한다
    (손 숫자 금지 — 시리즈 하우스 규약).

⛔ 이 파일은 **아무 형상도 안 바꾼다.** 스위치를 건드리지 않고, 기본값(=정본) 그대로 짓고 잰다.
   GPU 도 git 도 안 쓴다.

쓰는 법
    # 원장 재생성(약 3~5 분, CPU)
    PYTHONPATH=src:benchmark python report_mesh/src/mesh_canon_0817.py
    # 리포트 생성기에서
    import mesh_canon_0817 as C ;  C.fleet_table(order, label, specs)
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RM = os.path.abspath(os.path.join(HERE, ".."))            # report_mesh/
ROOT = os.path.abspath(os.path.join(RM, ".."))            # 저장소 루트
LEDGER = os.path.join(RM, "outputs", "mesh_canon_0817.json")
LEDGER_REL = "report_mesh/outputs/mesh_canon_0817.json"

for _p in (os.path.join(ROOT, "src"), os.path.join(ROOT, "benchmark")):
    if _p not in sys.path:
        sys.path.insert(0, _p)


# =========================================================================== #
#  1. 측정 — `python report_mesh/src/mesh_canon_0817.py` 로만 돈다
# =========================================================================== #
def _tag() -> str:
    """정본 판의 **파일명 꼬리표**. `benchmark/elevation_sweep_md.py` 와 같은 규약이다."""
    from geom import mesh_fix_set, blade_law_canon
    fixes = sorted(mesh_fix_set())
    t = "" if not fixes else "_mfix" + "".join(fixes)
    law = blade_law_canon()
    t += "" if law == "legacy" else "_bl" + law.replace("_", "")
    return t


def measure() -> dict:
    import time

    import numpy as np

    import geom
    import mesh_check as MC
    from drones import DRONES, build_drone, frame_envelope_mm

    t0 = time.time()
    fixes = sorted(geom.mesh_fix_set())
    law = geom.blade_law_canon()
    print(f"[canon] MESH_FIX={fixes} · BLADE_LAW={law} · 꼬리표 {_tag() or '(없음)'}", flush=True)

    per: dict = {}
    for key, spec in DRONES.items():
        t = time.time()
        m = build_drone(spec)
        V = np.asarray(m.v, float)
        F = np.asarray(m.f, int)
        G = np.asarray(m.g)

        #  모서리 길이 [mm] — 전체 / 프롭만 / 프롭 뺀 나머지
        def _edges(sel):
            f = F[sel]
            if not len(f):
                return None
            E = np.concatenate([V[f[:, 1]] - V[f[:, 0]],
                                V[f[:, 2]] - V[f[:, 1]],
                                V[f[:, 0]] - V[f[:, 2]]])
            el = np.linalg.norm(E, axis=1) * 1000.0
            return dict(p50=float(np.percentile(el, 50)),
                        p95=float(np.percentile(el, 95)), max=float(el.max()))

        is_prop = G == "prop"
        chk = MC.check_mesh(m, key)
        dims = MC.check_dimensions(spec, mesh=m)
        env = frame_envelope_mm(spec)
        buried = MC.check_buried_faces(spec, mesh=m)
        pbs = MC.check_prop_bell_solid(spec, mesh=m)

        n_dup = len(V) - len(np.unique(np.round(V / 1e-9).astype(np.int64), axis=0))
        n_unused = len(V) - len(np.unique(F))

        per[key] = dict(
            n_verts=int(len(V)), n_faces=int(len(F)), n_groups=len(chk["groups"]),
            groups={g: dict(n_faces=v["n_faces"], n_parts=v["n_parts"],
                            watertight=v["watertight"],
                            boundary_edges=v["boundary_edges"],
                            boundary_edge_budget=v["boundary_edge_budget"],
                            nonmanifold_edges=v.get("nonmanifold_edges", 0),
                            degenerate=v["degenerate"], inward_normals=v["inward_normals"],
                            bad_winding=v["bad_winding"], slivers=v["slivers"],
                            overlap_pct=v["overlap_pct"],
                            overlap_budget_pct=v["overlap_budget_pct"], ok=v["ok"])
                    for g, v in chk["groups"].items()},
            ok=bool(chk["ok"]), slivers=int(chk["slivers"]),
            sliver_budget=int(chk["sliver_budget"]), sliver_ok=bool(chk["sliver_ok"]),
            dup_vertices=int(n_dup), unused_vertices=int(n_unused),
            edge_mm=_edges(np.ones(len(F), bool)),
            edge_mm_prop=_edges(is_prop),
            edge_mm_nonprop=_edges(~is_prop),
            prop_faces=int(is_prop.sum()),
            prop_face_pct=round(100.0 * float(is_prop.sum()) / len(F), 2),
            wheelbase_mm=round(float(env["wheelbase_opposite_mm"]), 2),
            diagonal_spec_mm=float(spec.diagonal_mm),
            diagonal_err_pct=round(100.0 * (float(env["wheelbase_opposite_mm"])
                                            / float(spec.diagonal_mm) - 1.0), 3),
            dimensions=dims, buried=buried, prop_bell_solid=pbs,
        )
        print(f"  [{key}] v {len(V):,} · f {len(F):,} · 슬리버 {chk['slivers']}/"
              f"{chk['sliver_budget']} · 매몰(결함) {buried['defect_pct']:.2f}/"
              f"{buried['budget_pct']} % · {time.time() - t:.1f}s", flush=True)

    #  ── 재질 가중 매몰(= PO 이중계상 대용치) ──────────────────────────────────── #
    #  ⚠ 원 구현(`benchmark/mesh_inspect_materials_check.scan_fleet`)은 |Γ| 를 Sionna RT
    #    프로브 씬에서 받아 오느라 GPU/OptiX 를 탄다. 이 라운드는 GPU 금지라, **같은 식**을
    #    쓰되 |Γ| 는 원장에 이미 적힌 값(`mesh_verify.json` `E_materials.*.gamma_map`)에서
    #    읽는다. |Γ| 는 재질 상수라 형상 판과 무관하다 — 바뀐 것은 «어느 면이 묻혔나» 뿐이다.
    print("[canon] 재질 가중 매몰 — 그룹쌍 내부판정, 몇 분 걸린다", flush=True)
    from mesh_inspect_materials_check import (OPAQUE_GAMMA, _split_norepair, _submesh,
                                              _tri_area_mm2)
    with open(os.path.join(RM, "outputs", "mesh_verify.json"), encoding="utf-8") as f:
        _V = json.load(f)
    from drones import DRONE_GROUP_MAT
    fleet = {}
    for key, spec in DRONES.items():
        t = time.time()
        gam = dict(_V["E_materials"][key]["gamma_map"])
        m = build_drone(spec)
        V = np.asarray(m.v, float) * 1000.0
        F = np.asarray(m.f, np.int64)
        G = np.asarray(m.g)
        ar = _tri_area_mm2(V, F)
        groups = sorted(set(G.tolist()))
        solids = {g: [c for c in _split_norepair(_submesh(V, F[G == g])) if c.is_watertight]
                  for g in groups}
        gi, tot_a, tot_w = {}, float(ar.sum()), 0.0
        for g in groups:
            sub = G == g
            C = V[F[sub]].mean(1)
            a = ar[sub]
            inside = np.zeros(len(C), bool)
            in_op = np.zeros(len(C), bool)
            in_di = np.zeros(len(C), bool)
            by = {}
            for h in groups:
                if h == g:
                    continue
                hit = np.zeros(len(C), bool)
                for c in solids[h]:
                    lo, hi = c.bounds
                    sel = np.all((C >= lo - 1e-9) & (C <= hi + 1e-9), axis=1)
                    if not sel.any():
                        continue
                    r = c.contains(C[sel])
                    hit[np.where(sel)[0][r]] = True
                if hit.any():
                    by[h] = round(100.0 * float(a[hit].sum()) / float(a.sum()), 2)
                (in_op if gam[h] >= OPAQUE_GAMMA else in_di)[:] |= hit
                inside |= hit
            in_di &= ~in_op
            gmm = float(gam[g])
            w = float(a.sum()) * gmm ** 2
            tot_w += w
            gi[g] = dict(material=DRONE_GROUP_MAT[g][0], gamma_po=round(gmm, 4),
                         n_faces=int(sub.sum()),
                         area_mm2=round(float(a.sum()), 2),
                         area_pct=round(100.0 * float(a.sum()) / tot_a, 3),
                         power_weight=round(w, 1),
                         buried_pct=round(100.0 * float(a[inside].sum()) / float(a.sum()), 2),
                         buried_by=by,
                         buried_power_weight=round(float(a[inside].sum()) * gmm ** 2, 1),
                         buried_in_opaque_pct=round(100.0 * float(a[in_op].sum())
                                                    / float(a.sum()), 2),
                         buried_in_opaque_weight=round(float(a[in_op].sum()) * gmm ** 2, 1),
                         buried_in_dielectric_pct=round(100.0 * float(a[in_di].sum())
                                                        / float(a.sum()), 2))
        for g in gi:
            gi[g]["power_weight_pct"] = round(100.0 * gi[g]["power_weight"] / tot_w, 3)
        bw = sum(v["buried_power_weight"] for v in gi.values())
        ow = sum(v["buried_in_opaque_weight"] for v in gi.values())
        fleet[key] = dict(
            n_faces=int(len(F)), total_area_mm2=round(tot_a, 2),
            total_power_weight=round(tot_w, 1),
            buried_power_weight_pct=round(100.0 * bw / tot_w, 2),
            buried_in_opaque_weight_pct=round(100.0 * ow / tot_w, 2),
            po_overcount_opaque_dB=round(10.0 * np.log10(tot_w / (tot_w - ow))
                                         if tot_w > ow else 0.0, 3),
            po_overcount_allburied_dB=round(10.0 * np.log10(tot_w / (tot_w - bw))
                                            if tot_w > bw else 0.0, 3),
            groups=gi)
        print(f"  [{key}] 매몰 전력가중 {fleet[key]['buried_power_weight_pct']:.1f} % "
              f"(불투명 안 {fleet[key]['buried_in_opaque_weight_pct']:.1f} % = "
              f"+{fleet[key]['po_overcount_opaque_dB']:.2f} dB) · {time.time() - t:.1f}s",
              flush=True)

    #  ── 내부 금속 포함 판정 — 셸이 닫히면 판정이 «정의»되므로 정본에서 다시 잰다 ── #
    print("[canon] 내부 금속 포함 판정", flush=True)
    from mesh_internal_metal_check import check_drone
    internal = {}
    for key in DRONES:
        r = check_drone(key)
        internal[key] = dict(verdict=r["verdict"], body_watertight=r.get("body_watertight"),
                             why=r.get("why", ""),
                             boxes=[dict(group=b.get("group"), name=b.get("name"),
                                         outside_pct=b.get("outside_pct"),
                                         protrusion_mm=b.get("protrusion_mm"))
                                    for b in r.get("boxes", [])])
        print(f"  [{key}] {r['verdict']}", flush=True)

    #  ── 예산표 스냅샷 — «지금 어떤 표가 걸려 있나» 를 원장에 못 박는다 ──────────── #
    budgets = dict(
        boundary_edge=dict(
            base={str(k): v for k, v in MC.BOUNDARY_EDGE_BUDGET.items()},
            fixed={str(k): v for k, v in MC.BOUNDARY_EDGE_BUDGET_FIXED.items()},
            active_default=MC._boundary_budget("_none_", "_none_")),
        sliver=dict(base={str(k): v for k, v in MC.SLIVER_BUDGET.items()},
                    blade_law={f"{k[0]}|{k[1]}": v
                               for k, v in MC.SLIVER_BUDGET_BLADE_LAW.items()},
                    mesh_fix={f"{k[0]}|{k[1]}": v
                              for k, v in MC.SLIVER_BUDGET_MESH_FIX.items()}),
        group_overlap=dict(base={str(k): v for k, v in MC.GROUP_OVERLAP_BUDGET_PCT.items()},
                           fixed={str(k): v for k, v in MC.GROUP_OVERLAP_BUDGET_FIXED.items()}),
        prop_bell_solid=dict(base=dict(MC.PROP_BELL_SOLID_AREA_PCT),
                             blade_law={f"{k[0]}|{k[1]}": v for k, v
                                        in MC.PROP_BELL_SOLID_AREA_PCT_BLADE_LAW.items()}),
        buried_face=dict(MC.BURIED_FACE_BUDGET_PCT),
        dim_tol=dict(MC.DIM_TOL_PCT), dim_diag_tol=dict(MC.DIM_DIAGONAL_TOL_PCT),
        handedness_min_abs=MC.HANDEDNESS_MIN_ABS,
        sliver_min_angle_deg=MC.SLIVER_MIN_ANGLE_DEG,
    )

    tot = dict(verts=sum(v["n_verts"] for v in per.values()),
               faces=sum(v["n_faces"] for v in per.values()),
               parts=sum(int(g["watertight"].split("/")[1])
                         for v in per.values() for g in v["groups"].values()),
               watertight=sum(int(g["watertight"].split("/")[0])
                              for v in per.values() for g in v["groups"].values()),
               slivers=sum(v["slivers"] for v in per.values()),
               dup_vertices=sum(v["dup_vertices"] for v in per.values()),
               unused_vertices=sum(v["unused_vertices"] for v in per.values()))

    out = dict(
        _meta=dict(
            what="정본 판(2026-08-17)에서 다시 잰 메쉬 실측 원장 — report_mesh 시리즈 주입용",
            generated_by="report_mesh/src/mesh_canon_0817.py",
            mesh_fix=fixes, mesh_fix_canon=list(geom.MESH_FIX_CANON),
            mesh_fix_known=list(geom.MESH_FIX_KNOWN),
            blade_law=law, blade_law_canon=geom.BLADE_LAW_CANON,
            filename_tag=_tag(), seconds=round(time.time() - t0, 1),
            gpu_used=False),
        per_drone=per, totals=tot, budgets=budgets, material_weighted=fleet,
        internal_metal=internal)
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LEDGER, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"[canon] wrote {LEDGER}  ({time.time() - t0:.0f}s)")
    return out


# =========================================================================== #
#  2. 로더 + 표 — 리포트 생성기가 쓰는 쪽
# =========================================================================== #
#  ⭐ 기하 원장은 **한 곳**이다 — 같은 라운드가 낸 `mesh_verify_canon_0817.json`
#    (`verify_mesh_canon_0817.py` 가 `verify_mesh_suite` 의 sec_* 를 그대로 불러 만든 것).
#    이 파일은 그 원장이 **안 담는 축**(재질 가중 매몰 · 스위치 · 인증서)만 맡는다.
#    두 원장이 같은 메쉬를 잰 것인지 로드할 때 면 수로 대조한다 — 갈리면 멈춘다.
VERIFY_CANON = os.path.join(RM, "outputs", "mesh_verify_canon_0817.json")
VERIFY_CANON_REL = "report_mesh/outputs/mesh_verify_canon_0817.json"


def _load(path: str, how: str):
    if not os.path.exists(path):
        raise SystemExit(f"⛔ 정본 원장이 없다: {path}\n   먼저 만들 것 — {how}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


if __name__ != "__main__":
    CANON = _load(LEDGER, "PYTHONPATH=src:benchmark python "
                          "report_mesh/src/mesh_canon_0817.py")
    VC = _load(VERIFY_CANON, "PYTHONPATH=src:benchmark python "
                             "report_mesh/src/verify_mesh_canon_0817.py")
    META = CANON["_meta"]
    PER = CANON["per_drone"]
    A = VC["A_geometry"]                 # ⭐ 기하 수는 전부 이쪽에서 읽는다
    VMETA = VC["_meta"]
    TOT = CANON["totals"]
    BUD = CANON["budgets"]
    MW = CANON["material_weighted"]
    TAG = META["filename_tag"]
    FIXES = tuple(META["mesh_fix"])
    LAW = META["blade_law"]

    #  두 원장이 **같은 판**을 잰 것인가 — 아니면 멈춘다(세대가 섞이는 것을 막는다).
    if VMETA.get("file_tag") != TAG:
        raise SystemExit(f"⛔ 원장 세대 불일치: {VERIFY_CANON_REL} 꼬리표 "
                         f"{VMETA.get('file_tag')!r} ↔ {LEDGER_REL} 꼬리표 {TAG!r}")
    _bad = [k for k in PER if A.get(k, {}).get("n_faces") != PER[k]["n_faces"]]
    if _bad:
        raise SystemExit(f"⛔ 두 정본 원장의 면 수가 다르다: {_bad} — 둘 다 다시 만들 것")


# --------------------------------------------------------------------------- #
#  2.1 정본 스위치 — 여덟 편이 같은 문장을 쓰게 한다
# --------------------------------------------------------------------------- #
def switch_table() -> str:
    """지금 기본으로 켜져 있는 것 — 스위치 두 개를 한 표로."""
    return "\n".join([
        "| 스위치 | 지금 기본값(정본) | 무엇이 달라지나 | 옛 판으로 되돌리는 법 |",
        "|---|---|---|---|",
        f"| `geom.MESH_FIX_CANON` | `{', '.join(FIXES)}` | `battery` = 배터리 팩 상자와 "
        "구조판 상자가 서로 파고든 것을 불리언 합집합으로 없앤다(4기체) · `i5` = mini2 "
        "셸의 구멍을 닫는다 | `MESH_FIX=none` |",
        f"| `geom.BLADE_LAW_CANON` | `{LAW}` | 기체마다 **그 기체의 순정 프로펠러** 평면형을 "
        "쓴다 | `BLADE_LAW=legacy` |",
        f"| 파일명 꼬리표 | `{TAG}` | 정본 판 산출물의 이름에 붙는다 | 옛 판은 꼬리표가 "
        "**없다** — 그래서 두 판이 이름만으로 갈린다 |",
    ])


def switch_note() -> list[str]:
    """스위치 표 아래에 붙는 공통 단서."""
    return [
        "⭐ **판정은 호출 시점에 한다.** `geom.mesh_fix_set()`·`geom.blade_law_canon()` 이 "
        "환경변수를 **부를 때마다** 읽으므로, import 뒤에 켜도 듣는다 "
        "← 출처: `src/geom.py` 두 함수의 docstring.",
        "",
        f"⭐ **꼬리표가 규약인 이유** — 정본 판 산출물은 이름에 `{TAG}` 가 붙는다. 이름이 "
        "같으면 계산기가 **옛 판 결과를 재사용**하고, 재계산이 «건너뜀» 으로 끝나 버린다 "
        "← 출처: `benchmark/elevation_sweep_md.py` 꼬리표 블록.",
        "",
        f"⛔ `MESH_FIX=none BLADE_LAW=legacy` 를 주면 옛 판이 **비트동일**하게 다시 나온다 "
        "← 출처: `benchmark/regress_blade_law_bitidentical.py` · `src/mesh_check.py` "
        "legacy 회귀. 전환 직전 산출물은 "
        "`/data/public/sionna/archive_pre_meshfix_20260817/` 에 있다(꼬리표 없는 샤드 "
        f"{ARCHIVE_SHARDS:,}개 + README).",
    ]


ARCHIVE_DIR = "/data/public/sionna/archive_pre_meshfix_20260817/"
ARCHIVE_SHARDS = 3813   # ← 출처: 위 디렉터리 `elev_sweep_shards/` 전수(2026-08-17 실측)


# --------------------------------------------------------------------------- #
#  2.2 함대 규모표 — mesh_facts_0816.fleet_table 의 정본판
# --------------------------------------------------------------------------- #
#  기체별 «지금 선언된 결함» — 정본 판 기준. 한 칸에 들어갈 만큼 줄인 것.
DECLARED = {
    "mini5pro": "세로 배율 1.2985(전 부품 늘림)",
    "mavic4pro": "세로 배율 1.3524 · 짐벌이 발보다 15.35 mm 아래",
    "matrice4e": "로터면이 CAD 보다 18.5 mm 위(F19~F21 보류)",
    "s1000plus": "카본 센터플레이트가 `plastic` 그룹 · 바깥 참값 0행",
    "phantom4": "착륙아치 8.3~8.5 mm 뜸",
    "typhoonh480": "—",
    "x500v2": "레일 4.0 mm 뜸 · accent↔arm 동일평면",
    "phantom3": "착륙아치 13.7~13.8 mm 뜸 · 짐벌 3조각이 떨어져 있음",
    "m350rtk": "프롭 허브가 벨 위 6.0 mm 뜸 · 바깥 참값 0행",
    "mini2": "—",
}


def fleet_table(order, label_fn, specs) -> str:
    rows = []
    for k in order:
        a = A[k]
        sp = specs[k]
        wt = sum(int(g["watertight"].split("/")[0]) for g in a["groups"].values())
        n_parts = sum(int(g["watertight"].split("/")[1]) for g in a["groups"].values())
        rows.append(
            f"| {label_fn(k)} | **[{GRADE_OF[k]}]** | {PER[k]['wheelbase_mm']:,.1f} "
            f"| {sp.prop_dia_mm:.0f}×{sp.num_rotors} | {a['n_verts']:,} | {a['n_faces']:,} "
            f"| {a['n_groups']} | {wt}/{n_parts} | {DECLARED[k]} |")
    return "\n".join(rows)


def fleet_totals(order) -> dict:
    tv = tf = tp = twt = 0
    for k in order:
        a = A[k]
        tv += a["n_verts"]
        tf += a["n_faces"]
        for g in a["groups"].values():
            w, n = g["watertight"].split("/")
            twt += int(w)
            tp += int(n)
    return dict(verts=tv, faces=tf, parts=tp, watertight=twt)


#  기체 단위 등급(형상 전체) — mesh_facts_0816.GRADES 와 같은 값을 여기서도 쓴다.
GRADE_OF = {"matrice4e": "A", "mini2": "A", "x500v2": "A", "typhoonh480": "A",
            "phantom4": "B", "phantom3": "B", "mini5pro": "B", "mavic4pro": "C",
            "s1000plus": "B", "m350rtk": "B"}


# --------------------------------------------------------------------------- #
#  2.3 예산 — 정본에서는 **법칙별로 갈린다**
# --------------------------------------------------------------------------- #
def budget_table() -> str:
    """«예산» 은 «이만큼이 옳다» 가 아니라 «지금 이만큼이다» 라는 선언이다.

    정본 전환으로 표가 **둘로 갈렸다** — 옛 판(legacy)의 스냅샷과, 정본 판의 스냅샷.
    아래는 **지금 걸려 있는 쪽**을 적는다."""
    sl_bl = BUD["sliver"]["blade_law"]
    sl_now = {k: PER[k]["sliver_budget"] for k in PER}
    sl_meas = {k: PER[k]["slivers"] for k in PER}
    pb_bl = BUD["prop_bell_solid"]["blade_law"]
    bf = BUD["buried_face"]
    ov = BUD["group_overlap"]
    dt, dd = BUD["dim_tol"], BUD["dim_diag_tol"]
    return "\n".join([
        "| 예산 | 지금 걸려 있는 값 | 무엇을 뜻하나 |",
        "|---|---|---|",
        f"| `BOUNDARY_EDGE_BUDGET_FIXED` | 기본 **{BUD['boundary_edge']['fixed']['_default']}** "
        "— 예외 없음 | 구멍은 원칙적으로 없어야 한다. 정본에서는 예외 칸이 비어 있다 |",
        f"| `SLIVER_BUDGET_BLADE_LAW` | {len(sl_bl)}기체에 별도 값 — 실측 "
        f"{min(sl_meas[k] for k in sl_bl_keys(sl_bl))}~"
        f"{max(sl_meas[k] for k in sl_bl_keys(sl_bl))} / 예산 "
        f"{min(sl_bl.values())}~{max(sl_bl.values())} "
        f"(나머지 기체는 기존 `SLIVER_BUDGET` 실측 {min(sl_meas[k] for k in sl_meas if k not in sl_bl_keys(sl_bl))}~"
        f"{max(sl_meas[k] for k in sl_meas if k not in sl_bl_keys(sl_bl))}) "
        "| 아주 뾰족한 삼각형 개수. 면적 비중이 0.0001~0.03 % 라 σ 에는 무해하고, "
        "감시하는 이유는 법선이 수치적으로 불안정한데 PO 조명 판정이 `n̂·û>0` 이기 때문이다 |",
        f"| `PROP_BELL_SOLID_AREA_PCT_BLADE_LAW` | "
        + " · ".join(f"{k.split('|')[1]} {v} %" for k, v in pb_bl.items())
        + " | 프로펠러가 모터 벨 솔리드 **안**에 든 면적 비율 |",
        f"| `GROUP_OVERLAP_BUDGET_FIXED` | 기본 {ov['fixed']['_default']} % "
        f"(battery 실측 {max(PER[k]['groups']['battery']['overlap_pct'] for k in PER if 'battery' in PER[k]['groups']):.1f} %) "
        "| 같은 그룹 안에서 부품이 파묻힌 비율 |",
        f"| `BURIED_FACE_BUDGET_PCT` | 기종별 {min(v for k, v in bf.items() if k != '_default')}~"
        f"{max(v for k, v in bf.items() if k != '_default')} % "
        f"(실측 {min(PER[k]['buried']['defect_pct'] for k in PER):.1f}~"
        f"{max(PER[k]['buried']['defect_pct'] for k in PER):.1f} %) "
        "| 다른 부품 솔리드 **안**에 든 면적 중 «진짜 결함» 몫 |",
        f"| `DIM_TOL_PCT` | 프롭 지름 {dt['prop_dia']:.0f} % · 외형 {dt['envelope']:.0f} % · "
        f"대각 {dt['diagonal']:.0f} % (mini5pro 예외 {dd['mini5pro']:.0f} %) "
        "| 공표 숫자와의 허용 오차 |",
        f"| `HANDEDNESS_MIN_ABS` | {BUD['handedness_min_abs']} | 날 비틀림 지표의 최소 크기. "
        "이보다 작으면 «비틀리지 않았다» 는 뜻이라 부호를 믿을 수 없다 |",
    ])


def sl_bl_keys(sl_bl) -> list:
    return [k.split("|")[1] for k in sl_bl]


def budget_note() -> list[str]:
    sl_bl = BUD["sliver"]["blade_law"]
    return [
        "⭐ **예산이 «법칙별» 로 갈렸다.** 옛 표(`SLIVER_BUDGET`·`PROP_BELL_SOLID_AREA_PCT`)는 "
        "전부 옛 날 법칙(`legacy`)에서 잰 스냅샷이다. 정본은 기체마다 다른 평면형으로 "
        "로프트를 다시 뜨므로 씨접합 슬리버 수와 뿌리 겹침이 달라진다 — 결함이 는 것이 아니라 "
        "**다른 형상**이다. 그래서 표를 덮어쓰지 않고 **법칙을 키에 넣어** 따로 선언한다"
        f"(`SLIVER_BUDGET_BLADE_LAW` {len(sl_bl)}행 · "
        f"`PROP_BELL_SOLID_AREA_PCT_BLADE_LAW` {len(BUD['prop_bell_solid']['blade_law'])}행).",
        "",
        "⭐ **값은 실측 + 10 % 로만 두고 실측치를 괄호에 남긴다.** «예산을 올려 통과시킨다» 는 "
        "인증서가 이름 붙인 안티패턴이라, 얼마를 올렸는지 소스에서 바로 읽히게 한다 "
        "← 출처: `src/mesh_check.py` 두 표의 주석 · `docs/MESH_CERTIFICATE.md` §1-③.",
    ]


# --------------------------------------------------------------------------- #
#  2.3b 검사기·검사 목록 — 정본 판
# --------------------------------------------------------------------------- #
CERT_DOC = "docs/MESH_CERTIFICATE.md"
CERT_SEAL = "benchmark/mesh_certify.py"

CHECKERS = [
    ("`src/cadkit.py` `Assembly.check`", "빌드 도중", "파트 하나를 붙일 때마다",
     "부품 단위 수밀·법선"),
    ("`src/mesh_check.py`", "출하 게이트", "11 검사 + 예산표",
     "`python src/drones.py`(OBJ 내보내기) 한 문에 배선. `MESH_GATE=off` 로 끌 수 있고, "
     "RCS·렌더가 쓰는 **인메모리 `build_drone()` 은 이 문을 안 지난다**"),
    ("`report_mesh/src/verify_mesh_suite.py`", "원장 생성", "A~I 9절",
     "이 시리즈의 숫자를 만든다. I 절(SBR)만 GPU"),
    ("`report_mesh/src/verify_mesh_canon_0817.py`", "원장 생성(정본)", "A·B·C·D·F·G",
     "같은 잣대(위 스위트의 `sec_*`)로 **정본 판**을 다시 잰다. 전부 CPU"),
    ("`benchmark/check_gimbal_sensors_0816.py`", "특수 검사", "짐벌·센서 게이트 A~D",
     "부착·삼킴·선언초과·재질 민감도"),
    ("`benchmark/mesh_internal_metal_check.py`", "특수 검사", "내부 금속 포함 판정",
     "«금속 상자가 정말 셸 안인가»"),
    (f"`{CERT_SEAL}`", "⭐골든 봉인", "형상·치수·예산·바깥참값·문·인증서 여섯 축",
     "«오늘이 어제와 같은가» 를 지킨다. 봉인 대조 약 9 초 · `--full` 약 295 초. "
     "⚠지키는 것은 «안 바뀜» 이지 «옳음» 이 아니다"),
]


def checker_table() -> str:
    rows = ["| 검사기 | 언제 도나 | 무엇을 보나 | 범위·단서 |", "|---|---|---|---|"]
    for a, b, c, d in CHECKERS:
        rows.append(f"| {a} | {b} | {c} | {d} |")
    return "\n".join(rows)


CHECKS = [
    ("수밀(watertight)", "부품이 닫힌 껍질인가"),
    ("경계 모서리", "삼각형 하나만 쓰는 모서리 = 구멍의 테두리. **원칙은 0**, 예산으로만 예외"),
    ("winding", "이웃한 면이 같은 방향으로 감겼는가"),
    ("법선 방향", "닫힌 부품의 부호있는 부피가 양수인가"),
    ("부호부피(원본 인덱스)", "trimesh 를 **전혀 안 거치고** 출하 인덱스에서 손계산"),
    ("퇴화면 — 절대 + 상대", "면적 잣대에 더해 **최소 내각 <0.5°** 슬리버를 센다"),
    ("그룹 안 겹침", "같은 그룹의 두 부품이 서로 파묻혔는가(PO 면적 이중계상)"),
    ("치수 대조", "프롭 지름·로터 대각·공표 외형을 `DroneSpec` 의 수와 대조"),
    ("손대칭성", "로터별 날 비틀림 방향이 회전방향과 맞는가 — **거울상 기체 탐지**"),
    ("프롭↔모터 벨 관통", "원통 근사(빠름) + 솔리드 내부판정(판정 기준)"),
    ("⭐ 매몰면 전수", "**전 부품쌍**에서 다른 부품 솔리드 안에 든 면적. "
     "«설계 의도»(셸 안의 배터리·기판)와 «진짜 결함» 을 갈라 뒤쪽만 예산에 건다 "
     "— `check_buried_faces` · `BURIED_FACE_BUDGET_PCT`"),
]


def checks_table() -> str:
    rows = ["| # | 검사 | 무엇을 묻나 |", "|---|---|---|"]
    for i, (a, b) in enumerate(CHECKS, 1):
        rows.append(f"| {i} | **{a}** | {b} |")
    return "\n".join(rows)


def blind_spots() -> list[str]:
    """검사기가 **아직 못 보는 것** — 정본 판 + 인증서가 새로 찾은 둘."""
    lo, hi, klo, khi = po_overcount_range()
    return [
        "**동일평면 겹침** — 두 부품 표면이 정확히 같은 자리에 있으면 관통 검사가 못 본다. "
        "9기체에서 34쌍이 그 상태다(가장 큰 것은 s1000plus body↔battery 16,745.8 mm²).",
        "**기종별 재질 분기** — `drone_gamma_map(spec, fc)` 이 `spec` 을 안 쓴다. "
        "지금은 재질이 기체와 무관해서 맞지만, 기종별 재질이 생기는 순간 조용히 틀린 답을 준다.",
        f"**PO 경로의 가림** — `rcs_po.py` 가 자기 docstring 에서 자기차폐·다중반사를 "
        f"무시한다고 선언한다. 부품 속에 묻힌 면이 그 경로에서는 이중계상된다"
        f"(재질 가중으로 +{lo:.2f}~+{hi:.2f} dB · 가장 작은 것 {klo} · 가장 큰 것 {khi}).",
        "⭐**출하한 파일 자체** — 검사는 메모리 배열에서 돌고 파일은 그 뒤에 쓰인다. "
        "되읽어 같은 검사를 먹이면 10기체 중 2기체가 실패한다(1 µm 격자 반올림) "
        f"← 출처: `{CERT_DOC}` §1-①.",
        "⭐**부품이 있는가** — 그룹이 통째로 사라져도 검사 10계열과 바깥 참값이 전부 조용하다 "
        f"← 출처: `{CERT_DOC}` §3.2.",
    ]


# --------------------------------------------------------------------------- #
#  2.3c 지금 남은 결함 지도 — 정본 판
# --------------------------------------------------------------------------- #
def defect_table() -> str:
    """톤 규칙: «고쳤다» 서사 없이 «지금 이렇다» 만. 수치는 전부 원장에서 뽑는다."""
    import mesh_facts_0816 as F
    g = F.GIMBAL["_summary"]
    fit_m5 = F.BODY["per_drone"]["mini5pro"]["fit"][2]
    fit_mv = F.BODY["per_drone"]["mavic4pro"]["fit"][2]
    sh_m5 = F.BODY["per_drone"]["mini5pro"]["shell_h_mm"]
    sh_mv = F.BODY["per_drone"]["mavic4pro"]["shell_h_mm"]
    cam = g["gate_A_fail"][0]
    plate = F.MAT["s1000plus_center_plate"]
    _fl = g["gate_B_floating"]
    _p3_gap_min = min(x["gap_to_other_camera_parts_mm"] for x in _fl)
    _p3_gap_max = max(x["gap_to_other_camera_parts_mm"] for x in _fl)
    _p3_air_min = min(x["gap_to_airframe_mm"] for x in _fl)
    _p3_air_max = max(x["gap_to_airframe_mm"] for x in _fl)
    _p3_area = sum(x["area_cm2"] for x in _fl)
    _gc_max = max(max(r["built_over_declared"]) for r in g["gate_C_over_declared"])
    ex = _load_external()
    rows = [
        "| 무엇 | 기체 | 지금 이만큼 | 어디에 실리나 |",
        "|---|---|---|---|",
        f"| 공표 높이를 **형상이 아니라 세로 배율**로 맞춘다 | mini5pro · mavic4pro "
        f"| 세로 배율 {fit_m5:.4f} / {fit_mv:.4f} — 형상표의 셸 높이 "
        f"{sh_m5['table']:.2f} / {sh_mv['table']:.2f} mm 가 메쉬에서 "
        f"{sh_m5['delivered']:.2f} / {sh_mv['delivered']:.2f} mm 로 나온다 "
        f"| 평판극한 σ 상한 +2.27 / +2.62 dB (방위평균, el 0°) |",
        f"| 짐벌이 착륙발보다 아래 | mavic4pro | 카메라 최저점이 발보다 "
        f"{abs(cam['camera_below_gear_mm']):.2f} mm 아래. 발을 바닥으로 놓고 같은 규칙을 풀면 "
        f"세로 배율이 {cam['sz_now']:.4f} → {cam['sz_if_bottom_were_the_feet']:.4f} "
        f"({cam['vertical_scale_error_pct']:.2f} %) | 위 세로 배율의 **원인** — 예산 구멍을 가린다 |",
        f"| 뜬 파트(기체에 안 닿는 부품) | phantom4 · phantom3 · m350rtk · x500v2 "
        f"| 착륙아치 8.3~8.5 / 13.7~13.8 mm · 프롭 허브 6.0 mm · 레일 4.0 mm "
        f"| 간극 0.05~0.16 λ @3.5 GHz — 면적은 그대로고 가림·다중반사·위상이 바뀐다 |",
        f"| 로터면이 공식 CAD 보다 위 | matrice4e | 18.5 mm = 0.216 λ @3.5 GHz. "
        f"명세가 F19~F21 로 «엔진 변경 필요» 라 미뤄 둔 자리 | 프롭 장착 높이가 함께 움직인다 |",
        f"| ⭐**바깥 참값(실물 치수)과 어긋나는 행** | 함대 "
        f"| {ex['rows']}행 중 **{ex['off']}행**. 가장 큰 것 — m350rtk 펼침 폭 −6.5 % · "
        f"길이 −4.8 % · mini5pro 배터리 높이 +29.5 % · 길이 −19.9 % "
        f"| «실물과 같은가» 축. 인증서가 **장담 못 한다**고 선언한 자리다 |",
        f"| 짐벌이 세 조각으로 떨어져 있다 | phantom3 | 방진판·요 샤프트·카메라 블록이 서로"
        f" {_p3_gap_min:.2f}~{_p3_gap_max:.2f} mm 씩 벌어져 있고, 기체 표면과도"
        f" {_p3_air_min:.2f}~{_p3_air_max:.2f} mm 떨어져 있다 — 잇는 구조가 없다"
        f" | 면적 {_p3_area:.0f} cm² 가 공중에 뜬다. 가림·다중반사가 달라지고,"
        f" PO 와 SBR 이 같은 메쉬를 다르게 읽는다 |",
        f"| 짐벌 헬퍼의 «선언 치수» ↔ 실제 크기 | mini5pro·matrice4e·phantom4·s1000plus 등"
        f" | 인자로 넣은 상자 위에 요크·렌즈·마운트가 더 붙어 최대 {_gc_max:.2f} 배로 지어진다"
        f" | 인자를 실물 치수로 인용하면 틀린다. mini2 처럼 **역산**해야 실물과 맞는다 |",
        f"| 카본 판이 `plastic` 그룹에 있다 | s1000plus | 판 2장만 세도 body 합집합 전 면적의"
        f" {plate['plates_only_share_of_body_pct']:.1f} % (스탠드오프 기둥까지 넣은 스택은"
        f" {plate['carbon_plate_share_of_body_pct']:.1f} %) | 면 반사율 +10.14 dB"
        f" (carbon 0.90 ↔ plastic 0.28) |",
        f"| 짐벌을 구속하는 바깥 검사가 없다 | 함대(특히 matrice4e) "
        f"| 짐벌 폭은 사진 계측 대비 +26 % 인데 판정이 **면제**돼 있다(참값이 사진뿐이고 "
        f"공식 CAD 는 4T 판이라 짐벌이 다른 물건이다) | 짐벌은 산란 기여가 큰 부품이라 "
        f"이 빈칸은 작지 않다 |",
    ]
    return "\n".join(rows)


def unresolved_list() -> list[str]:
    """«모른다» 를 그대로 옮긴다 — 빈칸이 가짜 값보다 낫다.

    ⚠ 정본에서 **닫힌** 항목(기체별 프로펠러 평면형)은 빼고, 아직 안 닫힌 축(날 두께)만
    구체적으로 다시 적는다. 닫힌 것을 «모른다» 로 남겨 두면 리포트가 자기 상태를 틀리게 말한다."""
    import mesh_facts_0816 as F
    out = [f"- {x}" for x in F.BODY["not_settled_this_round"]
           if "프로펠러 축 전부" not in x]
    bat = F.INTERNAL["battery_material"]
    out.append(f"- **배터리 재질** — {bat['verdict']}")
    cam = F.GIMBAL["material_review"]
    out.append("- **카메라 재질 0.85 의 출처** — "
               + cam["repo_prior"].replace("한 팔의 값이다", "한 조건에서 잰 값이다"))
    out.append("- **프로펠러 날 두께** — 사진으로는 **원리적으로** 못 잰다(겉보기 높이가 "
               "시위·피치각에 지배되고 두께 항은 그 5분의 1 아래다). 실제로 잰 기체는 "
               "mini2 하나뿐이고, typhoonh480 은 두께비만 있다. 나머지 여덟은 공용 상수를 쓴다. "
               "⚠ 평면형(시위 분포)은 기체별로 **닫혔다** — 안 닫힌 것은 두께 축뿐이다.")
    out.append("- **분절(움직이는) 메쉬 열의 정확도** — 인증서가 자기 범위 밖으로 선언한다"
               "(«자세 재현» 만 보고 양성 대조가 없다).")
    return out


def _load_external() -> dict:
    p = os.path.join(ROOT, "outputs", "mesh_cert_dimension_external_0816.json")
    if not os.path.exists(p):
        return dict(rows=None, off=None)
    with open(p, encoding="utf-8") as f:
        sm = json.load(f)["summary_by_airframe"]
    return dict(rows=sum(v["n_rows"] for v in sm.values()),
                off=sum(v["어긋남"] for v in sm.values()))


# --------------------------------------------------------------------------- #
#  2.4 매몰면 — 면적 자와 재질 가중 자
# --------------------------------------------------------------------------- #
def buried_table(order, label_fn) -> str:
    rows = ["| 기체 | 총 매몰 [%] | 설계 의도 [%] | **진짜 결함** [%] | 예산 [%] "
            "| 재질 가중 불투명 안 [%] | PO 과대계상 [dB] |",
            "|---|---|---|---|---|---|---|"]
    for k in order:
        b = PER[k]["buried"]
        f = MW[k]
        rows.append(f"| {label_fn(k)} | {b['buried_pct']:.1f} | {b['design_intent_pct']:.1f} "
                    f"| **{b['defect_pct']:.1f}** | {b['budget_pct']} "
                    f"| {f['buried_in_opaque_weight_pct']:.2f} "
                    f"| **+{f['po_overcount_opaque_dB']:.2f}** |")
    return "\n".join(rows)


def internal_metal_table(order, label_fn) -> str:
    """«내부» 금속이 정말 셸 안에 있나 — 정본 판에서 다시 잰 기체별 판정."""
    IM = CANON["internal_metal"]
    mean = {"PASS": "금속 상자가 전부 셸 안에 있다",
            "FAIL": "금속 상자의 일부가 셸 **밖**으로 나와 있다",
            "N/A": "설계상 열린 프레임이라 «셸 안» 이라는 물음이 성립하지 않는다",
            "UNKNOWN": "셸이 닫혀 있지 않아 안/밖 판정 자체가 정의되지 않는다"}
    rows = ["| 기체 | 판정 | 무엇을 뜻하나 |", "|---|---|---|"]
    for k in order:
        vd = IM.get(k, {}).get("verdict", "—")
        rows.append(f"| {label_fn(k)} | **{vd}** | {mean.get(vd, '—')} |")
    return "\n".join(rows)


def assignment_table() -> str:
    """부위(그룹) 배정표 — 뜻·재질은 재질 원장에서, **면적은 정본 판 실측**에서."""
    import mesh_facts_0816 as F
    AA = {g: v for g, v in F.MAT["assignment_audit"].items() if not g.startswith("_")}
    area = {}
    ndr = {}
    for k, f in MW.items():
        for g, v in f["groups"].items():
            area[g] = area.get(g, 0.0) + v["area_mm2"]
            ndr[g] = ndr.get(g, 0) + 1
    rows = ["| 부위(그룹) | 재질 키 | PO \\|Γ\\| | 쓰는 기체 | 함대 면적 [cm²] "
            "| 이 그룹이 무엇인가 |", "|---|---|---|---|---|---|"]
    for grp, v in sorted(AA.items(), key=lambda kv: -area.get(kv[0], 0.0)):
        flag = "" if v.get("verdict") == "ok" else " ⚠"
        rows.append(f"| `{grp}`{flag} | `{v.get('material','—')}` "
                    f"| {v.get('gamma_po', float('nan')):.2f} "
                    f"| {ndr.get(grp, 0)}종 | {area.get(grp, 0.0) / 100.0:,.0f} "
                    f"| {v.get('description','—')} |")
    return "\n".join(rows)


def po_overcount_range() -> tuple:
    v = [MW[k]["po_overcount_opaque_dB"] for k in MW]
    return min(v), max(v), min(MW, key=lambda k: MW[k]["po_overcount_opaque_dB"]), \
        max(MW, key=lambda k: MW[k]["po_overcount_opaque_dB"])


# --------------------------------------------------------------------------- #
#  2.5 프로펠러 — 정본 날 법칙(기체별)
# --------------------------------------------------------------------------- #
def _prop_law():
    with open(os.path.join(ROOT, "outputs", "prop_law_by_airframe_0816.json"),
              encoding="utf-8") as f:
        law = json.load(f)
    with open(os.path.join(ROOT, "outputs", "prop_law_verify_0816.json"),
              encoding="utf-8") as f:
        ver = json.load(f)
    return law, ver


PROP_LAW, PROP_VERIFY = _prop_law() if os.path.exists(
    os.path.join(ROOT, "outputs", "prop_law_by_airframe_0816.json")) else ({}, {})


def prop_law_table(order, label_fn) -> str:
    """기체별 정본 프로펠러 — 모델명 · 평면형 상수 · 근거 등급."""
    C = PROP_LAW.get("C_law_by_airframe", {})
    rows = ["| 기체 | 정본 프로펠러 | c_max/R | 시위 정점 r/R | 근거 | 대리 |",
            "|---|---|---|---|---|---|"]
    for k in order:
        v = C.get(k)
        if not v:
            continue
        proxy = v.get("proxy_of")
        rows.append(f"| {label_fn(k)} | {v['prop']} | {v['c_max_over_R']:.4f} "
                    f"| {v['peak_r_over_R']:.2f} | **[{v['grade']}]** "
                    f"| {'—' if not proxy else '⛔ ' + proxy + ' 대리'} |")
    return "\n".join(rows)


# --------------------------------------------------------------------------- #
#  2.6 메쉬 인증서 — 「무엇을 장담하고 무엇은 못 하는가」
# --------------------------------------------------------------------------- #
def _cert():
    """인증서가 근거로 삼은 원장에서 수를 직접 읽는다(문서의 수를 베끼지 않는다)."""
    def _j(rel):
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            return {}
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    mx = _j("outputs/mesh_cert_matrix_0816.json")
    mp = _j("outputs/mesh_cert_map_0816.json")
    ex = _j("outputs/mesh_cert_dimension_external_0816.json")
    s = mx.get("summary", {})
    gm = mx.get("grade_matrix", {}).get("coverage", {})
    sm = ex.get("summary_by_airframe", {})
    agree = sum(v["일치"] for v in sm.values()) if sm else None
    off = sum(v["어긋남"] for v in sm.values()) if sm else None
    return dict(
        n_cells=s.get("n_cells"), n_pass=s.get("n_pass"), n_fail=s.get("n_fail"),
        n_mismatch=s.get("n_mismatch"), n_blindspot=s.get("n_blindspot"),
        n_na=s.get("n_na"), n_blank=s.get("n_blank"),
        n_checks=s.get("n_checks"),
        n_pc=s.get("n_checks_with_positive_control"),
        n_no_pc=s.get("n_checks_without_positive_control"),
        no_pc=s.get("checks_without_positive_control", []),
        controls=s.get("controls_total"), controls_ok=s.get("controls_passed"),
        n_suites=s.get("n_suites"), seal_ok=s.get("seal_ok"), seal_total=s.get("seal_total"),
        n_categories=len(mp.get("categories", [])),
        cat_ids=[c.get("id") for c in mp.get("categories", [])],
        ref_rows=sum(v["n_rows"] for v in sm.values()) if sm else None,
        ref_agree=agree, ref_off=off,
        ref_zero=[k for k, v in sm.items() if v["n_rows"] == 0],
        grade_cells=gm.get("n_cells"), grade_with_ref=gm.get("n_with_reference"),
        grade_independent=gm.get("n_independent_rows"),
        #  ⚠«독립 행»(참값 77행 기준)과 «독립 칸»(기체×부품 120칸 기준)은 **다른 수**다.
        #    인증서 §3.3 이 쓰는 한계 수치는 뒤쪽(15칸)이므로 칸에서 직접 센다.
        grade_independent_cells=sum(
            1 for a in mx.get("grade_matrix", {}).get("matrix", {}).values()
            for cell in a.values()
            if cell.get("grade") and cell["grade"] != "모름"
            and (cell.get("independent") or 0) > 0),
    )


CERT = _cert()


def cert_headline() -> list[str]:
    """인증서 판정과 그 근거 — 여덟 편이 같은 문장을 쓰게 한다."""
    c = CERT
    return [
        f"판정은 ⭐**«조건부 장담»** 이다 ← 출처: `{CERT_DOC}` §0.",
        "",
        "| 무엇 | 지금 값 |",
        "|---|---|",
        f"| 결함이 있는 자리의 **범주 지도** | {c['n_categories']}개 "
        f"(`{c['cat_ids'][0]}`~`{c['cat_ids'][-1]}`) |",
        f"| 인증 매트릭스 | {c['n_cells']}칸 — 통과 {c['n_pass']} · **실패 "
        f"{c['n_fail']}** · 어긋남 {c['n_mismatch']} · 사각지대 {c['n_blindspot']} "
        f"· 해당없음 {c['n_na']} · 빈칸 {c['n_blank']} |",
        f"| 적대 대조(일부러 결함을 심어 «무는가» 를 본다) | **{c['controls_ok']}/"
        f"{c['controls']}**, {c['n_suites']}스위트 |",
        f"| 양성 대조가 걸린 검사 | 검사 {c['n_checks']}개 중 매트릭스 기준 "
        f"**{c['n_pc']}개**. 인증서 라운드가 넷(A8·A9·G2·R0)을 더 심어 "
        f"**남은 빈칸은 여섯**(A7·V7·Z1·Z3·G1·W1) |",
        f"| 골든 봉인 ↔ 지금 메쉬 | 형상 **10기체 전부 동일**(골든 지문). 별도로 인증서 4종 "
        f"지문이 기체마다 맞는지도 본다 — **{c['seal_ok']}/{c['seal_total']}** |",
        f"| 바깥 참값(실물 치수) | {c['ref_rows']}행 — 일치 {c['ref_agree']} · "
        f"**어긋남 {c['ref_off']}** |",
        f"| 근거 등급이 붙은 칸 | 기체×부품 {c['grade_cells']}칸 중 **{c['grade_with_ref']}칸**. "
        f"그중 **독립 근거가 있는 칸은 {c['grade_independent_cells']}칸**이다"
        f"(나머지 {c['grade_with_ref'] - c['grade_independent_cells']}칸은 독립 참값 행이 0개). "
        f"⚠ 별개 잣대인 «참값 행» 쪽에서 독립인 것은 {c['ref_rows']}행 중 {c['grade_independent']}행 — "
        "**칸 수와 행 수를 섞어 읽지 말 것** |",
    ]


CERT_NOT_GUARANTEED = [
    "**출하한 파일 자체** — 검사는 메모리 배열에서 돌고 파일은 그 뒤에 쓰인다. "
    "`geom.Mesh.write_obj` 가 1 µm 격자로 반올림하므로, 되읽어 같은 검사를 먹이면 "
    "**10기체 중 2기체(matrice4e·mini2)가 실패한다**(면적 0 삼각형 6장 · 비다양체 모서리 6개). "
    "물리 크기는 무시할 만하지만 «퇴화면 0 장» 은 출하물에 대해 참이 아니다.",
    "**부품이 있는가** — 그룹이 통째로 사라져도 검사 10계열과 바깥 참값이 전부 조용하다"
    "(canopy 표면적 8.4 % · gear 2.1 % 를 지워 확인).",
    "**매몰면 예산의 자기참조** — 잣대가 전체 표면적 대비 비율이라, 부품 하나를 통째로 "
    "묻어도 예산을 못 넘고 값이 거꾸로 가기도 한다. 지금 그 검사가 하는 일은 "
    "«오늘보다 나빠지지 않았다» 의 감시뿐이다.",
    "**실물 충실도** — 바깥 참값 77행 중 **24행이 어긋나 있다**"
    "(가장 큰 것: m350rtk 펼침 폭 −6.5 % · mini5pro 배터리 높이 +29.5 %).",
    "**독립 참값이 0행인 기체가 둘** — s1000plus · m350rtk. 이 둘의 «치수가 맞다» 는 "
    "**우리 상수를 우리가 다시 읽은 것**이다.",
    "**재질 물성값(εr·tanδ)의 옳음 · 커널(PO·SBR)의 옳음** — 인증서가 스스로 "
    "«이 인증서의 범위 밖» 이라고 선언한다.",
]


def prop_law_headline() -> dict:
    """이 편들이 인용하는 «한 줄» 수치들."""
    C = PROP_LAW.get("C_law_by_airframe", {})
    cm = [v["c_max_over_R"] for v in C.values()]
    ver = PROP_VERIFY or {}
    return dict(n_airframes=len(C), c_min=min(cm) if cm else None,
                c_max=max(cm) if cm else None,
                spread_pct=(max(cm) / min(cm) - 1.0) * 100.0 if cm else None,
                verify=ver)


if __name__ == "__main__":
    measure()
