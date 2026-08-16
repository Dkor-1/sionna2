#!/usr/bin/env python
"""기체 하나에 대해 **저장소의 모든 메쉬 검사**를 돌려 원자료를 그대로 뱉는다.

이 라운드(인증 매트릭스)는 검사기를 새로 만들지 않는다 — 이미 있는 여섯 검사기를
전 기체 × 전 검사로 돌려서 한 표에 모으는 것이 일이다.  ⛔형상 상수 무변경.

실행: PYTHONPATH=src:benchmark python benchmark/run_cert_matrix_one.py --key mini5pro --out X.json
"""
import argparse
import json
import os
import sys
import time
import traceback

import numpy as np


def _J(o):
    """numpy → 순수 파이썬(직렬화용)."""
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


def _timed(store, name, fn, *a, **kw):
    t = time.time()
    try:
        r = fn(*a, **kw)
        store[name] = _J(r)
        store.setdefault("_sec", {})[name] = round(time.time() - t, 2)
        return r
    except Exception:
        store[name] = {"_error": traceback.format_exc()[-1500:]}
        store.setdefault("_sec", {})[name] = round(time.time() - t, 2)
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    import drones
    spec = drones.DRONES[a.key]
    t0 = time.time()
    mesh = drones.build_drone(spec)
    out = {"key": a.key, "n_faces": int(len(mesh.f)), "n_verts": int(len(mesh.v)),
           "groups": sorted(set(map(str, mesh.g))), "_sec": {"build": round(time.time() - t0, 2)}}

    # ---------- 0층 검사기 (src/mesh_check.py) ----------
    import mesh_check as MC
    _timed(out, "mc_mesh", MC.check_mesh, mesh, a.key)
    _timed(out, "mc_dimensions", MC.check_dimensions, spec, mesh)
    _timed(out, "mc_handedness", MC.check_handedness, spec, mesh)
    _timed(out, "mc_prop_bell", MC.check_prop_bell, spec)
    _timed(out, "mc_prop_bell_solid", MC.check_prop_bell_solid, spec, mesh=mesh)
    _timed(out, "mc_buried", MC.check_buried_faces, spec, mesh=mesh)

    # ---------- 위상·이산화 (src/mesh_topo_check.py) ----------
    import mesh_topo_check as MT
    r = _timed(out, "topo", MT.check_topology, mesh, a.key, fc=MT.FC_DEFAULT_HZ,
               self_int=True, verbose=False)
    if r is not None:
        out["topo_fingerprint"] = MT.fingerprint(r)
    # 5.8 GHz 는 D1(사지타) 만 달라진다 — 자기교차는 껐다(같은 값, 90 초 절약)
    _timed(out, "topo_58", MT.check_topology, mesh, a.key, fc=5.8e9,
           self_int=False, verbose=False)
    _timed(out, "loft_caps", MT.check_loft_caps, spec)

    # ---------- 치수·외부참값 (src/mesh_dimref.py) ----------
    import mesh_dimref as MD
    try:
        _dec = json.load(open(os.path.join(
            MD._ROOT, "outputs", "mesh_cert_dimension_external_0816.json"),
            encoding="utf-8"))["seal"]["declared_residual_mm"]
    except Exception:
        _dec = None
    _timed(out, "dimref", MD.check_key, a.key, mesh=mesh, declared=_dec)
    try:
        out["dimref_fingerprint"] = MD.mesh_fingerprint(mesh)
    except Exception:
        out["dimref_fingerprint"] = None

    # ---------- 배치·겹침 (src/mesh_placement.py) ----------
    import mesh_placement as MP
    cen = _timed(out, "placement_census", MP.placement_census, mesh, a.key, verbose=False)
    if cen is not None:
        _timed(out, "placement", MP.check_placement, cen)
        #  원자료가 크다 — pairs_all 은 따로 떼어 크기만 남긴다
        c = out["placement_census"]
        c["n_pairs_all"] = len(c.get("pairs_all") or [])
        c.pop("pairs_all", None)
        c["relations_kept"] = len(c.get("relations") or [])
        c.pop("relations", None)

    # ---------- 대칭·파생량 (src/mesh_symmetry.py) ----------
    import mesh_symmetry as MS
    _timed(out, "symmetry", MS.check_one, spec, mesh=mesh, verbose=False)

    # ---------- 재질·라벨 (src/material_provenance.py) ----------
    import material_provenance as MPV
    _timed(out, "material_label", MPV.check_label_geometry, spec, mesh=mesh, verbose=False)

    out["_sec"]["total"] = round(time.time() - t0, 2)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(_J(out), f, ensure_ascii=False, indent=1)
    print(f"[{a.key}] done {out['_sec']['total']} s → {a.out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
