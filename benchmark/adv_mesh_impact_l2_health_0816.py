# -*- coding: utf-8 -*-
"""검증 A/④ — 수리가 새 결함을 만들었나 · 실루엣(외형)을 바꿨나 · i4 판정 모드는 무엇인가."""
import json
import os
import sys

import numpy as np

os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ.pop("MESH_FIX", None)
sys.path.insert(0, "/workspace/sionna/src")


def geo(mesh):
    V = np.asarray(mesh.v, float)
    F = np.asarray(mesh.f, np.int64)
    G = np.asarray(mesh.g)
    T = V[F]
    cr = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    a = 0.5 * np.linalg.norm(cr, axis=1)
    #  최소 내각
    e = np.stack([np.linalg.norm(T[:, 1] - T[:, 0], axis=1),
                  np.linalg.norm(T[:, 2] - T[:, 1], axis=1),
                  np.linalg.norm(T[:, 0] - T[:, 2], axis=1)], 1)
    s = np.sort(e, 1)
    with np.errstate(invalid="ignore", divide="ignore"):
        cosmin = (s[:, 1] ** 2 + s[:, 2] ** 2 - s[:, 0] ** 2) / (2 * s[:, 1] * s[:, 2])
    ang = np.degrees(np.arccos(np.clip(cosmin, -1, 1)))
    lo, hi = V.min(0), V.max(0)
    return dict(n_faces=int(len(F)), n_verts=int(len(V)),
                area_mm2=round(float(a.sum()) * 1e6, 4),
                bbox_mm=[round(float(x) * 1000, 4) for x in (hi - lo)],
                bbox_lo_mm=[round(float(x) * 1000, 4) for x in lo],
                slivers_lt0p5deg=int((ang < 0.5).sum()),
                sliver_area_mm2=round(float(a[ang < 0.5].sum()) * 1e6, 6),
                groups={g: int((G == g).sum()) for g in sorted(set(G.tolist()))})


def build(key, fix):
    import drones as dr
    import geom
    dr._FIT_CACHE.clear()
    if fix:
        geom.set_mesh_fix(fix)
    else:
        os.environ.pop("MESH_FIX", None)
    m = dr.build_drone(dr.DRONES[key])
    os.environ.pop("MESH_FIX", None)
    return m


def main():
    import drones as dr
    import drone_cad as dc
    keys = list(dr.DRONES)
    out = {}
    #  i4 판정 모드 · 캐노피 부피 (build_frame_cad 를 직접 불러 로그를 본다)
    modes = {}
    for k in keys:
        s = dr.DRONES[k]
        try:
            A = dc.build_frame_cad(s, mesh_fix=("i5,i4" if k == "mini2" else "i4"))
            modes[k] = getattr(A, "mesh_fix_log", {}).get("i4", {})
        except Exception as e:
            modes[k] = dict(error=f"{type(e).__name__}: {e}")
    out["i4_모드"] = modes

    for k in keys:
        rec = {}
        rec["off"] = geo(build(k, ""))
        rec["i4"] = geo(build(k, "i5,i4" if k == "mini2" else "i4"))
        rec["all5"] = geo(build(k, "i5,m6,battery,i4,m4"))
        d = {}
        for tag in ("i4", "all5"):
            d[tag] = dict(
                dbbox_mm=[round(rec[tag]["bbox_mm"][i] - rec["off"]["bbox_mm"][i], 5)
                          for i in range(3)],
                dslivers=rec[tag]["slivers_lt0p5deg"] - rec["off"]["slivers_lt0p5deg"],
                darea_pct=round(100 * (rec[tag]["area_mm2"] / rec["off"]["area_mm2"] - 1), 4))
        rec["Δ"] = d
        out[k] = rec
        print(f"  {k:12s} bbox Δ(i4)={rec['Δ']['i4']['dbbox_mm']} "
              f"slivers {rec['off']['slivers_lt0p5deg']}→{rec['i4']['slivers_lt0p5deg']}"
              f" (all5 {rec['all5']['slivers_lt0p5deg']})", flush=True)
    with open("/tmp/claude-0/-workspace/e9e31991-b542-4f3a-b8e2-570320d555ba/"
              "scratchpad/verify2/health.json", "w") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("done")


if __name__ == "__main__":
    main()
