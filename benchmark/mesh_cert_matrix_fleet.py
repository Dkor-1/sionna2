#!/usr/bin/env python
"""함대 단위(기체별로 나뉘지 않는) 검사 + 봉인 대조 + 원시값 스캔.

① M0 원시값 스캔 — NaN·무한·인덱스 범위·빈 라벨(전용 검사기가 없어 이 라운드가 직접 잰다)
② M18 분절 재현 — articulated_fast.FastPoser.verify (기체별)
③ 재질·출처 함대 검사 — group_table_closure · fallback_sites · constants · provenance · shared_plate · seal
④ 치수 가드 — guard_m4t_gimbal · guard_tolerance_provenance · audit_reference_provenance
⑤ 봉인 대조 — 네 인증서의 지문 ↔ 지금 메쉬
"""
import hashlib
import json
import os
import sys
import time
import traceback

import numpy as np

OUT = sys.argv[1] if len(sys.argv) > 1 else "fleet.json"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL = ROOT


def _J(o):
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, dict):
        return {str(k): _J(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_J(v) for v in o]
    return o


def guarded(store, name, fn, *a, **kw):
    t = time.time()
    try:
        store[name] = _J(fn(*a, **kw))
    except Exception:
        store[name] = {"_error": traceback.format_exc()[-1200:]}
    store.setdefault("_sec", {})[name] = round(time.time() - t, 2)


def main():
    import drones
    out = {"_sec": {}}

    # ---------------- ① M0 원시값 스캔 + ② M18 분절 ----------------
    raw, arti = {}, {}
    for k, spec in drones.DRONES.items():
        t = time.time()
        m = drones.build_drone(spec)
        V = np.asarray(m.v, float)
        F = np.asarray(m.f, np.int64)
        G = np.asarray(m.g)
        used = np.unique(F)
        raw[k] = dict(
            n_vert=int(len(V)), n_face=int(len(F)),
            nan_vert=int(np.isnan(V).sum()), inf_vert=int(np.isinf(V).sum()),
            max_abs_coord_m=round(float(np.abs(V).max()), 6),
            index_min=int(F.min()), index_max=int(F.max()),
            index_out_of_range=int((F < 0).sum() + (F >= len(V)).sum()),
            repeated_index_faces=int((
                (F[:, 0] == F[:, 1]) | (F[:, 1] == F[:, 2]) | (F[:, 0] == F[:, 2])).sum()),
            unused_vertices=int(len(V) - len(used)),
            empty_labels=int(sum(1 for g in G if str(g).strip() == "")),
            n_groups=int(len(set(G.tolist()))),
            groups=sorted(set(map(str, G.tolist()))),
            ok=bool(np.isnan(V).sum() == 0 and np.isinf(V).sum() == 0
                    and (F >= 0).all() and (F < len(V)).all()
                    and sum(1 for g in G if str(g).strip() == "") == 0),
        )
        raw[k]["_sec"] = round(time.time() - t, 2)
        # M18
        t = time.time()
        try:
            from articulated_fast import FastPoser
            fp = FastPoser(spec)
            arti[k] = _J(fp.verify())
        except Exception:
            arti[k] = {"_error": traceback.format_exc()[-800:]}
        arti[k]["_sec"] = round(time.time() - t, 2)
        print(f"  {k:12s} raw ok={raw[k]['ok']}  arti ok={arti[k].get('ok')}", flush=True)
    out["raw_scan"] = raw
    out["articulated"] = arti

    # ---------------- ③ 재질·출처 함대 검사 ----------------
    import material_provenance as MPV
    guarded(out, "mat_group_table", MPV.check_group_table_closure)
    guarded(out, "mat_fallback", MPV.check_fallback_sites)
    guarded(out, "mat_constants", MPV.check_constants)
    guarded(out, "mat_provenance", MPV.check_provenance)
    guarded(out, "mat_shared_plate", MPV.check_shared_plate)
    try:
        exp = json.load(open(os.path.join(REAL, "outputs",
                                          "mesh_cert_material_provenance_0816.json"),
                             encoding="utf-8"))["seal"]["fingerprints"]
    except Exception:
        exp = None
    guarded(out, "mat_seal", MPV.check_seal, exp)

    # ---------------- ④ 치수 가드 ----------------
    import mesh_dimref as MD
    guarded(out, "dim_guard_m4t_gimbal", MD.guard_m4t_gimbal)
    guarded(out, "dim_guard_tol_provenance", MD.guard_tolerance_provenance)
    guarded(out, "dim_ref_provenance", MD.audit_reference_provenance)
    guarded(out, "dim_grade_matrix", MD.grade_matrix)

    # ---------------- ⑤ 위상 봉인 ----------------
    import mesh_topo_check as MT
    guarded(out, "topo_seal", MT.check_seal,
            os.path.join(REAL, "outputs", "mesh_cert_topology_discretization_0816.json"))

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(_J(out), f, ensure_ascii=False, indent=1)
    print("fleet done →", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
