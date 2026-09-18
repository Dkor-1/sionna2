# -*- coding: utf-8 -*-
"""mesh_rev1_acceptance.py — plan C.1 ... C.13 for one mesh revision, with a pass/fail table.

Usage
    PYTHONPATH=<copy>/src:<copy>/benchmark CUDA_VISIBLE_DEVICES="" MPLBACKEND=Agg \
      nice -n 19 taskset -c 14-15 python benchmark/mesh_rev1_acceptance.py \
        --drone matrice4e --rev 1 --out <scratch>/acceptance_matrice4e_rev1.json

What it does
    * builds revision 0 and the revision under test with the same code path and the same
      environment, so every number is measured the same way for both;
    * reads `docs/mesh_rev1/<key>_acceptance_thresholds.json`, which is frozen before the first
      run, records its sha256 and never writes to it;
    * scores the rows the threshold file marks as scored and prints everything else as report;
    * writes the whole ledger (both revisions, every raw number) to `--out`, in the caller's
      scratch. Nothing is written under assets/ and no repo file is modified.

⛔ It never chooses a threshold from what it measured. A relaxation is a `deviations` row in the
   threshold file, written before the run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time

import numpy as np
import trimesh

MM = 1e-3
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

_METAL_GROUPS = ("battery", "motor")
_EXTERIOR_GROUPS = ("body", "canopy", "camera", "gear", "motor", "accent")
_INTERNAL_GROUPS = ("battery", "pcb")


# --------------------------------------------------------------------------- #
#  small helpers
# --------------------------------------------------------------------------- #
def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def tri_of(V, F):
    return trimesh.Trimesh(vertices=V, faces=F, process=True)


def _deviation(th, dev_id):
    """The post-run deviation entry `dev_id`, or None.

    Post-run deviations live in their OWN dated file, never in the frozen threshold file.
    `main()` loads it into `th["_deviations_after_the_run"]`; every entry it contains is printed
    before the table and copied into the ledger, and each one replaces exactly one scored row
    while the original row stays in the table as a report row.
    """
    for d in (th.get("_deviations_after_the_run") or {}).get("deviations", []):
        if d.get("id") == dev_id:
            return d
    return None


def sample_surface(V, F, n, seed=0):
    m = trimesh.Trimesh(vertices=V, faces=F, process=False)
    return trimesh.sample.sample_surface(m, int(n), seed=seed)[0]


def pct(a, q):
    return float(np.percentile(a, q)) if len(a) else float("nan")


class Table:
    """Collects rows and prints the pass/fail table."""

    def __init__(self):
        self.rows = []

    def add(self, section, name, value, target=None, ok=None, unit="", note=""):
        self.rows.append(dict(section=section, name=name, value=value, target=target,
                              ok=(None if ok is None else bool(ok)), unit=unit, note=note))

    def scored(self):
        return [r for r in self.rows if r["ok"] is not None]

    def failed(self):
        return [r for r in self.rows if r["ok"] is False]

    def render(self):
        w = max(len(f"{r['section']} {r['name']}") for r in self.rows) + 2
        out = []
        cur = None
        for r in self.rows:
            if r["section"] != cur:
                cur = r["section"]
                out.append("")
                out.append(f"── {cur} " + "─" * max(0, 76 - len(cur)))
            v = r["value"]
            if isinstance(v, float):
                vs = f"{v:.4g}"
            elif isinstance(v, (list, tuple)):
                vs = "[" + ", ".join(f"{x:.4g}" if isinstance(x, float) else str(x) for x in v) + "]"
            else:
                vs = str(v)
            t = "" if r["target"] is None else f"  target {r['target']}"
            mark = {True: "PASS", False: "FAIL", None: "    "}[r["ok"]]
            out.append(f"  {mark}  {r['name']:<{w}} {vs}{r['unit']}{t}"
                       + (f"   [{r['note']}]" if r["note"] else ""))
        return "\n".join(out)


# --------------------------------------------------------------------------- #
#  build
# --------------------------------------------------------------------------- #
def build(key, rev):
    import drones
    spec = drones.DRONES[key] if rev == 0 else drones.spec_for(key, rev)
    fr = drones.build_frame(spec)
    dm = drones.build_drone(spec)
    V = np.asarray(fr.v, float) * 1000.0
    F = np.asarray(fr.f, np.int64)
    G = np.asarray(fr.g).astype(str)
    #  ⚠ REVIEW FIX F-4 (2026-09-18): `cadkit.Assembly.to_geom()` builds a FRESH `geom.Mesh` and
    #  copies only vertices, faces and group names, so the builder's `rev1_report` never reached
    #  `b1["frame"]`. `getattr(frame, "rev1_report", None)` was therefore always None, and the
    #  three C.3 rows that read it — front arm heading, bow and root x, the three numbers plan
    #  row M4E-4 is about — silently never ran. Neither the build report nor the adversarial
    #  review noticed: the table simply had 21 C.3 rows instead of 24. The assembly is rebuilt
    #  here (about 11 s) so the record is available, and C.3 now ALSO measures the arm axis off
    #  the built mesh, which needs no record at all.
    rep = None
    if rev >= 1:
        try:
            import drone_rev
            rep = getattr(drone_rev.build_frame_rev(spec), "rev1_report", None)
        except Exception as exc:                                 # pragma: no cover
            print(f"  ⚠ could not rebuild the assembly for the builder record: {exc}", flush=True)
    return dict(spec=spec, frame=fr, drone=dm, V=V, F=F, G=G, report=rep,
                rl=drones.rotor_layout(spec),
                fit=tuple(float(v) for v in drones.frame_fit_scale(spec)),
                env=drones.frame_envelope_mm(spec))


def arm_axis_from_mesh(b, rotor_xy, r_lo=120.0, r_hi=205.0, half_ang_deg=25.0,
                       d_lo=25.0, d_hi=110.0, step=6.0):
    """Measure one arm's axis directly off the built body mesh (REVIEW FIX F-4).

    Independent of any builder record, and independent of where the loft happens to put its
    rings — a first version of this took the section centres from the vertex cloud, which needs
    a vertex in every 5 mm radius shell. Revision 1's arm is a 4-station loft, so most shells
    were empty, the function returned None and the three rows silently did not appear. Exactly
    the failure mode this fix exists to remove, so it is measured with true plane sections:

      1. a first direction from the principal axis of the body vertices in the annulus
         [r_lo, r_hi] within `half_ang_deg` of this rotor's azimuth;
      2. two refinement passes: cut the body with planes normal to the current direction at
         stations d = `d_lo` ... `d_hi` mm back from the rotor axis, keep the cut points that
         belong to this arm (within 40 mm of the axis laterally and in z), take the mid-point of
         their extremes as the section centre, and refit the direction through those centres.

    Returns the heading, the x where the axis crosses |y| = 47.08 mm, and the bow (the largest
    lateral distance from a section centre to the fitted axis).
    """
    Vb, Fb = group_mesh(b, ("body",))
    P = Vb[np.unique(Fb)]
    rot = np.asarray(rotor_xy, float)
    az0 = math.atan2(rot[1], rot[0])
    ang = np.arctan2(P[:, 1], P[:, 0])
    da = np.abs(np.arctan2(np.sin(ang - az0), np.cos(ang - az0)))
    r = np.hypot(P[:, 0], P[:, 1])
    k = (r >= r_lo) & (r <= r_hi) & (da <= math.radians(half_ang_deg))
    Q = P[k]
    if len(Q) < 20:
        return None
    u = np.linalg.svd(Q[:, :2] - Q[:, :2].mean(0), full_matrices=False)[2][0]
    if u @ rot < 0:
        u = -u
    m = trimesh.Trimesh(vertices=Vb, faces=Fb, process=True)
    z0 = float(Q[:, 2].mean())
    C = None
    for _ in range(2):
        u3 = np.array([u[0], u[1], 0.0])
        e1 = np.array([-u[1], u[0], 0.0])
        cen = []
        for d in np.arange(d_lo, d_hi + 1e-9, step):
            o = np.array([rot[0], rot[1], z0]) - d * u3
            try:
                sec = m.section(plane_origin=o, plane_normal=u3)
            except Exception:
                sec = None
            if sec is None:
                continue
            S = np.asarray(sec.vertices, float)
            lat = (S - o) @ e1
            keep = (np.abs(lat) < 40.0) & (np.abs(S[:, 2] - z0) < 60.0) \
                & (np.hypot(S[:, 0], S[:, 1]) > 105.0)
            if keep.sum() < 4:
                continue
            T = S[keep]
            cen.append([0.5 * (T[:, 0].min() + T[:, 0].max()),
                        0.5 * (T[:, 1].min() + T[:, 1].max()),
                        0.5 * (T[:, 2].min() + T[:, 2].max())])
        C = np.asarray(cen, float)
        if len(C) < 4:
            return None
        u = np.linalg.svd(C[:, :2] - C[:, :2].mean(0), full_matrices=False)[2][0]
        if u @ rot < 0:
            u = -u
        z0 = float(C[:, 2].mean())
    #  bow: the 3-D perpendicular distance of every section centre from the best-fit 3-D line
    #  through them, so a centreline that bends in z (revision 0 bends 5.5 mm upward) is caught
    #  as well as one that bends in plan.
    c3 = C.mean(0)
    u3f = np.linalg.svd(C - c3, full_matrices=False)[2][0]
    rr = (C - c3) - np.outer((C - c3) @ u3f, u3f)
    bow = float(np.linalg.norm(rr, axis=1).max())
    o = C[:, :2].mean(0)
    heading = math.degrees(math.atan2(u[1], u[0]))
    t = (math.copysign(47.08, o[1]) - o[1]) / u[1]
    return dict(heading_deg=heading, root_x_mm=float(o[0] + t * u[0]),
                bow_mm=bow, n_sections=int(len(C)))


def group_mesh(b, groups):
    k = np.isin(b["G"], list(groups))
    return b["V"], b["F"][k]


# --------------------------------------------------------------------------- #
#  C.1 topology
# --------------------------------------------------------------------------- #

def _tri_tri_hit(V0, V1, V2, U0, U1, U2, eps=1e-12):
    """Exact Moller triangle-triangle overlap (coplanar pairs are not reported)."""
    E1 = V1 - V0; E2 = V2 - V0
    N1 = np.cross(E1, E2); d1 = -N1 @ V0
    du = np.array([N1 @ U0 + d1, N1 @ U1 + d1, N1 @ U2 + d1])
    du[np.abs(du) < eps] = 0.0
    if (du > 0).all() or (du < 0).all():
        return False
    E1 = U1 - U0; E2 = U2 - U0
    N2 = np.cross(E1, E2); d2 = -N2 @ U0
    dv = np.array([N2 @ V0 + d2, N2 @ V1 + d2, N2 @ V2 + d2])
    dv[np.abs(dv) < eps] = 0.0
    if (dv > 0).all() or (dv < 0).all():
        return False
    D = np.cross(N1, N2)
    if (np.abs(D) < eps).all():
        return False
    mx = int(np.argmax(np.abs(D)))
    vp = np.array([V0[mx], V1[mx], V2[mx]]); up = np.array([U0[mx], U1[mx], U2[mx]])

    def interval(p, d):
        s_ = [0, 1, 2]
        i0 = None
        for i in range(3):
            j, k = [x for x in s_ if x != i]
            if (d[i] * d[j] < 0 and d[i] * d[k] < 0) or (d[i] == 0 and d[j] * d[k] > 0):
                i0 = i
                break
        if i0 is None:
            nz = [i for i in range(3) if d[i] != 0]
            if len(nz) < 2:
                return None
            i0 = nz[0]
        j, k = [x for x in s_ if x != i0]
        o_ = []
        for o in (j, k):
            if d[i0] - d[o] == 0:
                return None
            o_.append(p[i0] + (p[o] - p[i0]) * d[i0] / (d[i0] - d[o]))
        return (min(o_), max(o_))

    a = interval(vp, dv); b = interval(up, du)
    if a is None or b is None:
        return False
    return not (a[1] < b[0] or b[1] < a[0])


def _self_intersections(V, F, max_pairs=4000):
    """Self-intersecting triangle pairs inside one group (pairs sharing a vertex are skipped).

    Broad phase: a uniform grid over the triangle AABBs. Narrow phase: the exact Moller test.
    Added by the adversarial review; plan C.1 asks for this and the frozen file declared it
    unmeasured (DEV-4).
    """
    import itertools
    from collections import defaultdict
    V = np.asarray(V, float); F = np.asarray(F, np.int64)
    used = np.unique(F)
    rm = np.zeros(int(used.max()) + 1, np.int64); rm[used] = np.arange(len(used))
    Vg = V[used]; Fg = rm[F]
    tv = Vg[Fg]
    lo = tv.min(1); hi = tv.max(1)
    cell = max(float(np.median(hi - lo)) * 2.0, 1e-9)
    grid = defaultdict(list)
    for i, (a, b) in enumerate(zip(lo, hi)):
        for gx in range(int(np.floor(a[0] / cell)), int(np.floor(b[0] / cell)) + 1):
            for gy in range(int(np.floor(a[1] / cell)), int(np.floor(b[1] / cell)) + 1):
                for gz in range(int(np.floor(a[2] / cell)), int(np.floor(b[2] / cell)) + 1):
                    grid[(gx, gy, gz)].append(i)
    cand = set()
    for v in grid.values():
        if len(v) > 1:
            cand.update((i, j) for i, j in itertools.combinations(sorted(v), 2))
    ar = np.linalg.norm(np.cross(tv[:, 1] - tv[:, 0], tv[:, 2] - tv[:, 0]), axis=1) / 2.0
    hits = []
    for i, j in cand:
        if len(set(Fg[i]) & set(Fg[j])):
            continue
        if (lo[i] > hi[j]).any() or (lo[j] > hi[i]).any():
            continue
        if _tri_tri_hit(*tv[i], *tv[j]):
            hits.append((int(i), int(j)))
            if len(hits) >= max_pairs:
                break
    idx = sorted({i for p in hits for i in p})
    return dict(pairs=len(hits), tris=len(idx),
                area_mm2=float(ar[idx].sum()) if idx else 0.0,
                group_area_mm2=float(ar.sum()))


def _MC_ANG():
    from mesh_check import SLIVER_MIN_ANGLE_DEG
    return SLIVER_MIN_ANGLE_DEG


def c1_topology(T, b0, b1, th):
    thr = th["C1_topology"]
    out = {}
    for tag, b in (("rev0", b0), ("rev1", b1)):
        res = {}
        slivers = 0
        for g in sorted(set(b["G"])):
            Fg = b["F"][b["G"] == g]
            m = tri_of(b["V"], Fg)
            e = m.edges_sorted
            u, cnt = np.unique(e, axis=0, return_counts=True)
            comps = m.split(only_watertight=False, repair=False)
            A, B, C = m.vertices[m.faces[:, 0]], m.vertices[m.faces[:, 1]], m.vertices[m.faces[:, 2]]
            ang = []
            for P, Q, R in ((A, B, C), (B, C, A), (C, A, B)):
                u1 = Q - P; u2 = R - P
                cs = np.einsum("ij,ij->i", u1, u2) / (np.linalg.norm(u1, axis=1)
                                                     * np.linalg.norm(u2, axis=1) + 1e-30)
                ang.append(np.degrees(np.arccos(np.clip(cs, -1, 1))))
            amin = np.min(np.vstack(ang), axis=0)
            from mesh_check import SLIVER_MIN_ANGLE_DEG
            #  ⚠ METHOD CORRECTION, logged in the ledger: the frozen file says 1.0 deg but its
            #    revision-0 baseline (95) is mesh_check's own count, which uses 0.5 deg. The
            #    threshold NUMBER is unchanged; only the criterion is aligned with the baseline
            #    it was written against.
            #  ⚠⚠ REVIEW FIX R-2 (adversarial review 2026-09-18): switching the criterion after
            #    the first run makes the test EASIER (0.5 deg counts fewer triangles than 1.0),
            #    which is the loophole plan critique M8 closes. The count at the criterion the
            #    frozen file actually names is kept and SCORED alongside, so the reader sees the
            #    number the frozen threshold was written for as well as the repo-aligned one.
            ns = int((amin < SLIVER_MIN_ANGLE_DEG).sum())
            ns_frozen = int((amin < float(thr.get("sliver_min_angle_deg", 1.0))).sum())
            ar = m.area_faces
            res_extra = dict(slivers_at_frozen_angle=ns_frozen,
                             sliver_area_mm2=float(ar[amin < SLIVER_MIN_ANGLE_DEG].sum()),
                             area_mm2=float(ar.sum()),
                             degenerate_faces=int((ar < 1e-6).sum()),
                             min_face_area_mm2=float(ar.min()))
            slivers += ns
            res[g] = dict(faces=int(len(Fg)), components=len(comps),
                          watertight=bool(m.is_watertight),
                          winding=bool(m.is_winding_consistent),
                          is_volume=bool(m.is_volume),
                          volume_positive=bool(m.volume > 0),
                          boundary_edges=int((cnt == 1).sum()),
                          nonmanifold_edges=int((cnt > 2).sum()),
                          euler=int(m.euler_number), slivers=ns, **res_extra)
        res["_slivers_total"] = slivers
        res["_slivers_total_at_frozen_angle"] = sum(
            v["slivers_at_frozen_angle"] for v in res.values() if isinstance(v, dict))
        res["_sliver_area_mm2"] = sum(v["sliver_area_mm2"] for v in res.values()
                                      if isinstance(v, dict))
        res["_area_mm2"] = sum(v["area_mm2"] for v in res.values() if isinstance(v, dict))
        res["_degenerate_faces"] = sum(v["degenerate_faces"] for v in res.values()
                                       if isinstance(v, dict))
        out[tag] = res

    r1 = out["rev1"]
    for g, want in thr["declared_components"].items():
        got = r1.get(g, {}).get("components")
        T.add("C.1 topology", f"components[{g}]", got, want, got == want)
    for g in sorted(k for k in r1 if not k.startswith("_")):
        d = r1[g]
        T.add("C.1 topology", f"closed[{g}]",
              f"wt={d['watertight']} wind={d['winding']} vol+={d['volume_positive']} "
              f"bnd={d['boundary_edges']} nonmf={d['nonmanifold_edges']} euler={d['euler']}",
              "watertight, 0 boundary, 0 non-manifold, outward",
              d["watertight"] and d["winding"] and d["volume_positive"]
              and d["boundary_edges"] == 0 and d["nonmanifold_edges"] == 0)
    T.add("C.1 topology", "slivers total (rev1)", r1["_slivers_total"],
          f"<= {thr['sliver_total_max']}", r1["_slivers_total"] <= thr["sliver_total_max"],
          note=f"rev0 {out['rev0']['_slivers_total']}  [mesh_check's {_MC_ANG()} deg]")
    #  REVIEW FIX R-2: the same row at the angle the frozen threshold file names.
    fa = float(thr.get("sliver_min_angle_deg", 1.0))
    T.add("C.1 topology", f"slivers total (rev1) at the frozen {fa} deg",
          r1["_slivers_total_at_frozen_angle"], f"<= {thr['sliver_total_max']}",
          r1["_slivers_total_at_frozen_angle"] <= thr["sliver_total_max"],
          note=f"rev0 {out['rev0']['_slivers_total_at_frozen_angle']}")
    #  REVIEW FIX R-2b: the repository's own canonical gate on the WHOLE drone, which is what
    #  `mesh_check.assert_ok` enforces on any export path.
    try:
        import mesh_check as _MC
        _r = _MC.check_mesh(b1["drone"], name=b1["spec"].key)
        _r0 = _MC.check_mesh(b0["drone"], name=b0["spec"].key)
        T.add("C.1 topology", "repo mesh_check slivers, whole drone", int(_r["slivers"]),
              f"<= {int(_r['sliver_budget'])} (repo budget)", bool(_r["sliver_ok"]),
              note=f"rev0 {int(_r0['slivers'])} (ok={bool(_r0['sliver_ok'])})")
    except Exception as _e:                                   # pragma: no cover
        T.add("C.1 topology", "repo mesh_check slivers, whole drone", f"EXC {_e}", "report", None)
    for tag in ("rev0", "rev1"):
        r = out[tag]
        T.add("C.1 topology", f"sliver area share ({tag})",
              100.0 * r["_sliver_area_mm2"] / r["_area_mm2"], "report", None, " %",
              note=f"{r['_sliver_area_mm2']:.1f} mm2 of {r['_area_mm2']:.0f}")
    #  REVIEW FIX R-4 (adversarial review 2026-09-18): plan C.1 asks for 0 self-intersections.
    #  The frozen file's DEV-4 declared it "not measured", with the argument that a manifold
    #  boolean union cannot return a self-intersecting solid. Measured here, that argument is
    #  false for the P8 clip output: revision 1's battery and pcb groups DO self-intersect.
    for tag, b in (("rev0", b0), ("rev1", b1)):
        si = {}
        for g in sorted(set(b["G"])):
            si[g] = _self_intersections(b["V"], b["F"][b["G"] == g])
        out[tag]["_self_intersections"] = si
        out[tag]["_self_intersections_total"] = sum(v["pairs"] for v in si.values())
    s1 = out["rev1"]["_self_intersections"]
    tot1 = out["rev1"]["_self_intersections_total"]
    tot0 = out["rev0"]["_self_intersections_total"]
    T.add("C.1 topology", "self-intersecting triangle pairs (rev1)", tot1,
          f"<= {tot0} (rev0; plan C.1 asks for 0)", tot1 <= tot0,
          note=", ".join(f"{g} {v['pairs']}" for g, v in sorted(s1.items()) if v["pairs"]) or "none")
    for g, v in sorted(s1.items()):
        if v["pairs"]:
            T.add("C.1 topology", f"self-int area share [{g}]", 100.0 * v["area_mm2"] / v["group_area_mm2"],
                  "report", None, " %",
                  note=f"{v['pairs']} pairs over {v['tris']} triangles, "
                       f"{v['area_mm2']:.2f} mm2; rev0 {out['rev0']['_self_intersections'][g]['pairs']} pairs")
    T.add("C.1 topology", "degenerate faces (area < 1e-6 mm2)", out["rev1"]["_degenerate_faces"],
          "= 0", out["rev1"]["_degenerate_faces"] == 0,
          note=f"rev0 {out['rev0']['_degenerate_faces']}")
    return out


# --------------------------------------------------------------------------- #
#  C.2 attachment
# --------------------------------------------------------------------------- #
def c2_attachment(T, b0, b1, th, cad):
    thr = th["C2_attachment"]
    out = {}
    Vb, Fb = group_mesh(b1, ("body",))
    body = tri_of(Vb, Fb)

    # internal metal / plastic containment
    for g in _INTERNAL_GROUPS:
        k = b1["G"] == g
        if not k.any():
            continue
        Vg = b1["V"][np.unique(b1["F"][k])]
        d = trimesh.proximity.ProximityQuery(body).signed_distance(Vg)
        #  signed_distance is positive inside. A clipped part's vertices sit exactly on the
        #  shell, where trimesh.contains() is undefined, so the test is d >= -1e-3 mm.
        frac_out = 100.0 * float((d < -1e-3).mean())
        out[f"{g}_outside_pct"] = frac_out
        out[f"{g}_min_clearance_mm"] = float(np.min(d))
        out[f"{g}_clearance_ge1_frac"] = float((d >= 1.0).mean())
        T.add("C.2 attachment", f"{g} outside the shell", frac_out, "= 0", frac_out <= 1e-9, " %")
        T.add("C.2 attachment", f"{g} fraction with >= 1 mm clearance",
              float((d >= 1.0).mean()), "report (DEV-3)", None)

    # floating parts: every group component must touch the body (or be the body)
    float_bad = []
    pq = trimesh.proximity.ProximityQuery(body)
    for g in sorted(set(b1["G"])):
        if g in ("body", "prop") + _INTERNAL_GROUPS:
            continue
        Fg = b1["F"][b1["G"] == g]
        for c in tri_of(b1["V"], Fg).split(only_watertight=False, repair=False):
            d = np.abs(pq.signed_distance(np.asarray(c.vertices)))
            if float(d.min()) > thr["attach_gap_max_mm"]:
                float_bad.append((g, round(float(d.min()), 3)))
    out["floating_parts"] = float_bad
    T.add("C.2 attachment", "parts further than 0.5 mm from the shell", len(float_bad),
          f"<= {thr['floating_parts_max']}", len(float_bad) <= thr["floating_parts_max"],
          note=str(float_bad[:6]) if float_bad else "")

    # buried plastic: plastic (canopy/accent) area inside the body
    shell_area = float(tri_of(*group_mesh(b1, ("body",))).area)
    bur = 0.0
    for g in ("canopy", "accent"):
        Fg = b1["F"][b1["G"] == g]
        if not len(Fg):
            continue
        m = tri_of(b1["V"], Fg)
        cen = m.triangles.mean(1)
        ar = m.area_faces
        bur += float(ar[body.contains(cen)].sum())
    out["buried_plastic_pct"] = 100.0 * bur / shell_area
    T.add("C.2 attachment", "buried plastic / shell area", out["buried_plastic_pct"],
          f"<= {thr['buried_plastic_pct_of_shell_area_max']}",
          out["buried_plastic_pct"] <= thr["buried_plastic_pct_of_shell_area_max"], " %")

    # prop seating
    import mesh_check as MC
    pb = MC.check_prop_bell_solid(b1["spec"], mesh=b1["drone"])
    out["prop_bell_solid"] = pb
    T.add("C.2 attachment", "prop area inside the motor solid", pb["area_pct"],
          f"<= {thr['prop_area_inside_motor_pct_max']}",
          pb["area_pct"] <= thr["prop_area_inside_motor_pct_max"], " %")
    # hub underside vs adapter top
    Vm, Fm = group_mesh(b1, ("motor",))
    mot = tri_of(Vm, Fm)
    gaps = []
    for r in b1["rl"]:
        cx, cy, cz = (np.asarray(r["center"], float) * 1000.0)
        k = (np.hypot(mot.vertices[:, 0] - cx, mot.vertices[:, 1] - cy) < 20.0)
        gaps.append(float(cz - mot.vertices[k, 2].max()))
    out["prop_seat_gap_mm"] = gaps
    lo, hi = thr["prop_seat_gap_mm_range"]
    T.add("C.2 attachment", "prop hub underside above the adapter top", [round(g, 3) for g in gaps],
          f"in [{lo}, {hi}] (DEV-1)", all(lo - 1e-6 <= g <= hi + 1e-6 for g in gaps), " mm")

    # swept-disc clearance
    Vd = np.asarray(b1["drone"].v, float) * 1000.0
    Gd = np.asarray(b1["drone"].g).astype(str)
    Fd = np.asarray(b1["drone"].f, np.int64)
    pk = Gd == "prop"
    Pv = Vd[np.unique(Fd[pk])]
    fv = Vd[np.unique(Fd[~pk])]
    #  The swept volume is banded in radius: a blade is only a few millimetres thick at a given
    #  radius, and taking its whole z range would count the root droop as if it reached the tip.
    worst = 1e9
    hits = []
    for r in b1["rl"]:
        cx, cy, cz = (np.asarray(r["center"], float) * 1000.0)
        pr = np.hypot(Pv[:, 0] - cx, Pv[:, 1] - cy)
        own = pr <= 0.5 * float(b1["spec"].prop_dia_mm) + 1.0      # this rotor's propeller only
        sel = own & (pr > 0.25 * float(pr[own].max()))             # the blades, not the hub
        rlo, rhi = float(pr[sel].min()), float(pr[sel].max())
        edges = np.arange(np.floor(rlo), np.ceil(rhi) + 2.0, 2.0)
        bi = np.clip(np.digitize(pr[sel], edges) - 1, 0, len(edges) - 2)
        zl = np.full(len(edges) - 1, np.nan)
        zh = np.full(len(edges) - 1, np.nan)
        for i in range(len(edges) - 1):
            k = bi == i
            if k.any():
                zl[i] = Pv[sel][k, 2].min()
                zh[i] = Pv[sel][k, 2].max()
        fr_ = np.hypot(fv[:, 0] - cx, fv[:, 1] - cy)
        band = (fr_ >= rlo) & (fr_ <= rhi)
        fb = np.clip(np.digitize(fr_[band], edges) - 1, 0, len(edges) - 2)
        ok = ~np.isnan(zl[fb])
        zfl, zfh = zl[fb][ok], zh[fb][ok]
        zf = fv[band][ok][:, 2]
        clr = np.maximum(zfl - zf, zf - zfh)        # positive = outside the band
        if len(clr):
            worst = min(worst, float(clr.min()))
            if float(clr.min()) < 1.0:
                hits.append(dict(rotor=[round(float(cx), 1), round(float(cy), 1)],
                                 n_below_1mm=int((clr < 1.0).sum()),
                                 min_mm=round(float(clr.min()), 3)))
    out["swept_disc_hits"] = hits
    out["swept_disc_clearance_mm"] = None if worst >= 1e8 else worst
    T.add("C.2 attachment", "frame clearance to the swept blade volume",
          None if worst >= 1e8 else round(worst, 3),
          f">= {thr['swept_disc_frame_clearance_mm_min']}",
          worst >= thr["swept_disc_frame_clearance_mm_min"], " mm")

    # neighbouring-disc clearance sign, revision 0 vs revision 1
    def disc(b):
        C = np.array([r["center"] for r in b["rl"]], float) * 1000.0
        d = float(b["spec"].prop_dia_mm)
        outp = {}
        n = len(C)
        for i in range(n):
            for j in range(i + 1, n):
                outp[f"{i}-{j}"] = float(np.hypot(*(C[i, :2] - C[j, :2])) - d)
        return outp
    d0, d1 = disc(b0), disc(b1)
    same = all(np.sign(d0[k]) == np.sign(d1[k]) for k in d0)
    out["disc_clearance_rev0"] = d0
    out["disc_clearance_rev1"] = d1
    T.add("C.2 attachment", "neighbouring-disc clearance signs vs rev0", "same" if same else "CHANGED",
          "same", same)
    return out


# --------------------------------------------------------------------------- #
#  C.3 dimensions
# --------------------------------------------------------------------------- #
def c3_dimensions(T, b0, b1, th, cad):
    thr = th["C3_dimensions"]
    out = {}

    T.add("C.3 dimensions", "frame_fit_scale", list(b1["fit"]), thr["frame_fit_scale_exact"],
          all(abs(a - b) < 1e-12 for a, b in zip(b1["fit"], thr["frame_fit_scale_exact"])))

    def bbox(V, F, G, drop=()):
        k = ~np.isin(G, list(drop))
        Vv = V[np.unique(F[k])]
        return Vv.min(0), Vv.max(0)

    lo1, hi1 = bbox(b1["V"], b1["F"], b1["G"])
    lo0, hi0 = bbox(b0["V"], b0["F"], b0["G"])
    lo1c, hi1c = bbox(b1["V"], b1["F"], b1["G"], drop=("camera",))
    out["bbox_rev1_mm"] = [lo1.tolist(), hi1.tolist()]
    out["bbox_rev0_mm"] = [lo0.tolist(), hi0.tolist()]
    out["bbox_rev1_no_camera_mm"] = [lo1c.tolist(), hi1c.tolist()]

    sc = thr["envelope_airframe_scored"]
    for i, ax in enumerate("LWH"):
        v = float((hi1c - lo1c)[i]) if ax == "L" else float((hi1 - lo1)[i])
        tgt = sc[f"{ax}_mm"]["target"]
        tol = sc[f"{ax}_mm"]["tol"]
        T.add("C.3 dimensions", f"envelope {ax} (airframe, scored)", v, f"{tgt} +/- {tol}",
              abs(v - tgt) <= tol, " mm")
    wf = thr["envelope_whole_frame_reported"]
    for i, ax in enumerate("LWH"):
        v = float((hi1 - lo1)[i])
        tgt = wf[f"{ax}_mm"]["target"]
        tol = wf[f"{ax}_mm"]["tol"]
        T.add("C.3 dimensions", f"envelope {ax} (whole frame)", v, f"{tgt} +/- {tol}",
              (abs(v - tgt) <= tol) if wf[f"{ax}_mm"].get("scored", True) else None, " mm",
              note=("rev0 %.2f" % float((hi0 - lo0)[i])) + (
                  "; official 149.5" if ax == "H" else ""))

    u = thr["unchanged_from_rev0"]
    C0 = np.array([r["center"] for r in b0["rl"]], float) * 1000.0
    C1 = np.array([r["center"] for r in b1["rl"]], float) * 1000.0
    dxy = float(np.abs(C1[:, :2] - C0[:, :2]).max())
    T.add("C.3 dimensions", "rotor xy vs rev0", dxy, f"<= {u['rotor_xy_max_abs_diff_mm']}",
          dxy <= u["rotor_xy_max_abs_diff_mm"], " mm")
    out["rotor_xy_max_abs_diff_mm"] = dxy
    out["rotor_z_rev0_mm"] = C0[:, 2].tolist()
    out["rotor_z_rev1_mm"] = C1[:, 2].tolist()
    dwb = abs(b1["env"]["wheelbase_opposite_mm"] - b0["env"]["wheelbase_opposite_mm"])
    T.add("C.3 dimensions", "wheelbase vs rev0", dwb, f"<= {u['wheelbase_max_abs_diff_mm']}",
          dwb <= u["wheelbase_max_abs_diff_mm"], " mm",
          note=f"{b1['env']['wheelbase_opposite_mm']:.4f} mm")
    for f in ("prop_dia_mm", "prop_blades", "num_rotors", "hover_rpm"):
        v = getattr(b1["spec"], f)
        T.add("C.3 dimensions", f, v, u[f], v == u[f])
    dba = max(abs(a["base_ang"] - b["base_ang"]) for a, b in zip(b0["rl"], b1["rl"]))
    T.add("C.3 dimensions", "base_ang vs rev0", dba, f"<= {u['base_ang_max_abs_diff_deg']}",
          dba <= u["base_ang_max_abs_diff_deg"], " deg")

    tg = thr["targets"]
    Vb = b1["V"][np.unique(b1["F"][b1["G"] == "body"])]
    belly = float(Vb[np.abs(Vb[:, 0]) <= 50.0][:, 2].min())
    out["belly_z_mm"] = belly
    T.add("C.3 dimensions", "belly z", belly,
          f"{tg['belly_z_mm']['target']} +/- {tg['belly_z_mm']['tol']}",
          abs(belly - tg["belly_z_mm"]["target"]) <= tg["belly_z_mm"]["tol"], " mm",
          note="rev0 %.2f" % float(b0["V"][np.unique(b0["F"][b0["G"] == "body"])][
              np.abs(b0["V"][np.unique(b0["F"][b0["G"] == "body"])][:, 0]) <= 50.0][:, 2].min()))

    #  REVIEW FIX F-4: measured off the built body mesh, with no builder record involved, for
    #  every front rotor. These three rows are plan row M4E-4's own numbers and were missing
    #  from the table entirely until 2026-09-18.
    tgf = tg["front_arm_heading_deg"]
    meas = []
    for r in b1["rl"]:
        c = np.asarray(r["center"], float) * 1000.0
        if c[0] <= 0:
            continue
        m = arm_axis_from_mesh(b1, (c[0], c[1]))
        if m:
            meas.append(m)
    out["front_arm_axis_measured"] = meas
    meas0 = []
    for r in b0["rl"]:
        c = np.asarray(r["center"], float) * 1000.0
        if c[0] > 0:
            m0 = arm_axis_from_mesh(b0, (c[0], c[1]))
            if m0:
                meas0.append(m0)
    out["front_arm_axis_measured_rev0"] = meas0
    if meas:
        hd = [abs(m["heading_deg"]) for m in meas]
        band = tgf["band"]
        T.add("C.3 dimensions", "front arm heading (measured on the mesh)",
              [round(h, 3) for h in hd], f"in {band}",
              all(band[0] <= h <= band[1] for h in hd), " deg",
              note="rev0 " + ", ".join("%.2f" % abs(m["heading_deg"]) for m in meas0))
        bw = max(m["bow_mm"] for m in meas)
        T.add("C.3 dimensions", "front arm bow (measured on the mesh)", bw,
              f"<= {tg['front_arm_bow_mm']['max']}", bw <= tg["front_arm_bow_mm"]["max"], " mm",
              note="rev0 %.2f" % max([m["bow_mm"] for m in meas0] or [float('nan')]))
        rxm = [m["root_x_mm"] for m in meas]
        tgt, tol = tg["front_arm_root_x_mm"]["target"], tg["front_arm_root_x_mm"]["tol"]
        T.add("C.3 dimensions", "front arm x at |y| = 47.08 (measured on the mesh)",
              [round(v, 2) for v in rxm], f"{tgt} +/- {tol}",
              all(abs(v - tgt) <= tol for v in rxm), " mm",
              note="rev0 " + ", ".join("%.1f" % m["root_x_mm"] for m in meas0))

    # arm heading / root x / bow, from the builder's own record
    import drone_rev1_matrice4e as B
    rep = b1.get("report") or getattr(b1["frame"], "rev1_report", None)
    arms = []
    for k in range(4):
        info = None
        if rep and f"arm{k}" in rep:
            info = rep[f"arm{k}"]["info"]
        arms.append(info)
    out["arm_info"] = arms
    fronts = [a for a, r in zip(arms, b1["rl"]) if a and r["center"][0] > 0]
    if fronts:
        hd = [abs(a["heading_deg"]) for a in fronts]
        band = tg["front_arm_heading_deg"]["band"]
        T.add("C.3 dimensions", "front arm heading", [round(h, 3) for h in hd],
              f"in {band}", all(band[0] <= h <= band[1] for h in hd), " deg")
        bow = max(a["bow_mm"] for a in fronts)
        T.add("C.3 dimensions", "front arm bow", bow, f"<= {tg['front_arm_bow_mm']['max']}",
              bow <= tg["front_arm_bow_mm"]["max"], " mm")
        rx = []
        for a in fronts:
            r0 = np.asarray(a["root_mm"], float); t0 = np.asarray(a["tip_mm"], float)
            f = (47.08 - abs(r0[1])) / (abs(t0[1]) - abs(r0[1]))
            rx.append(float(r0[0] + f * (t0[0] - r0[0])))
        out["front_arm_root_x_mm"] = rx
        tgt, tol = tg["front_arm_root_x_mm"]["target"], tg["front_arm_root_x_mm"]["tol"]
        T.add("C.3 dimensions", "front arm x at |y| = 47.08", [round(v, 2) for v in rx],
              f"{tgt} +/- {tol}", all(abs(v - tgt) <= tol for v in rx), " mm")

    # motor stack
    Vm, Fm = group_mesh(b1, ("motor",))
    mot = tri_of(Vm, Fm)
    tops, hts = [], []
    for r in b1["rl"]:
        cx, cy, _ = np.asarray(r["center"], float) * 1000.0
        k = np.hypot(mot.vertices[:, 0] - cx, mot.vertices[:, 1] - cy) < 20.0
        tops.append(float(mot.vertices[k, 2].max()))
        hts.append(float(mot.vertices[k, 2].max() - mot.vertices[k, 2].min()))
    out["motor_stack_top_z_mm"] = tops
    out["motor_stack_height_mm"] = hts
    want = [tg["motor_stack_top_z_mm"]["front" if r["center"][0] > 0 else "rear"] for r in b1["rl"]]
    tol = tg["motor_stack_top_z_mm"]["tol"]
    T.add("C.3 dimensions", "motor stack top z", [round(v, 3) for v in tops],
          f"{want} +/- {tol}", all(abs(a - b) <= tol for a, b in zip(tops, want)), " mm")
    T.add("C.3 dimensions", "motor stack height", [round(v, 3) for v in hts],
          f"{tg['motor_stack_height_mm']['target']} +/- {tg['motor_stack_height_mm']['tol']}",
          all(abs(v - tg["motor_stack_height_mm"]["target"])
              <= tg["motor_stack_height_mm"]["tol"] for v in hts), " mm")

    # gimbal block
    Vc = b1["V"][np.unique(b1["F"][b1["G"] == "camera"])]
    k = (Vc[:, 0] >= 168.0) & (Vc[:, 0] <= 174.5)
    gw = float(Vc[k][:, 1].max() - Vc[k][:, 1].min()) if k.any() else float("nan")
    out["gimbal_block_width_mm"] = gw
    T.add("C.3 dimensions", "gimbal block width", gw,
          f"{tg['gimbal_block_width_mm']['target']} +/- {tg['gimbal_block_width_mm']['tol']}",
          abs(gw - tg["gimbal_block_width_mm"]["target"]) <= tg["gimbal_block_width_mm"]["tol"],
          " mm", note="rev0 59.0 nominal")
    gh = float(Vc[k][:, 2].max() - Vc[k][:, 2].min()) if k.any() else float("nan")
    out["gimbal_block_height_mm"] = gh
    T.add("C.3 dimensions", "gimbal block height", gh,
          f"{tg['gimbal_block_height_mm']['target']} +/- {tg['gimbal_block_height_mm']['tol']}",
          abs(gh - tg["gimbal_block_height_mm"]["target"])
          <= tg["gimbal_block_height_mm"]["tol"], " mm")

    # battery box as given, RTK top, nose apex
    if rep and "battery" in rep:
        bm = rep["battery"]["info"]["box_mm"]
        out["battery_box_mm"] = bm
        T.add("C.3 dimensions", "battery box as given", bm, tg["battery_box_mm"]["target"],
              all(abs(a - b) <= 1e-9 for a, b in zip(bm, tg["battery_box_mm"]["target"])), " mm",
              note=f"clipped {rep['battery']['info']['clipped_volume_pct']:.2f} % (DEV-3)")
    Vcn = b1["V"][np.unique(b1["F"][b1["G"] == "canopy"])]
    rtk = float(Vcn[:, 2].max())
    out["rtk_top_z_mm"] = rtk
    T.add("C.3 dimensions", "RTK turret top z", rtk,
          f"{tg['rtk_top_z_mm']['target']} +/- {tg['rtk_top_z_mm']['tol']}",
          abs(rtk - tg["rtk_top_z_mm"]["target"]) <= tg["rtk_top_z_mm"]["tol"], " mm",
          note="rev0 %.2f" % float(b0["V"][np.unique(b0["F"][b0["G"] == "canopy"])][:, 2].max()))
    nose = float(b1["V"][np.unique(b1["F"][b1["G"] == "body"])][:, 0].max())
    out["nose_apex_x_mm"] = nose
    T.add("C.3 dimensions", "body nose apex x", nose,
          f"{tg['nose_apex_x_mm']['target']} +/- {tg['nose_apex_x_mm']['tol']}",
          abs(nose - tg["nose_apex_x_mm"]["target"]) <= tg["nose_apex_x_mm"]["tol"], " mm")
    return out


# --------------------------------------------------------------------------- #
#  C.4 distance to the CAD, C.5 facing area  (render-based)
# --------------------------------------------------------------------------- #
def c4_distance(T, b0, b1, th, cad):
    from scipy.spatial import cKDTree
    thr = th["C4_reference_distance"]
    out = {}
    #  ⚠ DEVIATION DEV-5 (docs/mesh_rev1/matrice4e_deviations_0918.json, needs user approval).
    #  The frozen `nose_cradle` class mixes the exterior gimbal cradle (CAD solid 49) with three
    #  interior solids (56, 57, 58) that an exterior-only surface model has nothing to be near.
    #  Verified independently by rendering the whole CAD from 217 aspects: 56/57/58 never show a
    #  pixel from any direction. The SCORED class becomes solid 49; the frozen class and the
    #  interior solids are both measured and printed as report rows, so nothing disappears.
    dev5 = _deviation(th, "DEV-5")
    classes = dict(thr["cad_classes"])
    if dev5:
        classes["nose_cradle__frozen_class"] = list(classes["nose_cradle"])
        classes["nose_cradle"] = [49]
        classes["nose_interior"] = [56, 57, 58]
    Vc, Fc, Oc = cad["V"], cad["F"], cad["owner"]
    cadS, cadF_of_sample = trimesh.sample.sample_surface(
        trimesh.Trimesh(vertices=Vc, faces=Fc, process=False), 400_000, seed=1)
    cadS = np.asarray(cadS, float)
    cadF_of_sample = np.asarray(cadF_of_sample, np.int64)
    tree_cad = cKDTree(cadS)
    E = cad["edges"]                        # (n,3) CAD edge sample points
    Eo = cad["edge_owner"]

    for tag, b in (("rev0", b0), ("rev1", b1)):
        Vx, Fx = group_mesh(b, _EXTERIOR_GROUPS)
        S = sample_surface(Vx, Fx, 400_000, seed=2)
        tree_ours = cKDTree(S)
        res = {}
        d_all, _ = tree_ours.query(E, workers=2)
        res["cad_to_ours"] = {"all": dict(n=int(len(E)), median=float(np.median(d_all)),
                                          p90=pct(d_all, 90), p99=pct(d_all, 99),
                                          max=float(d_all.max()))}
        for cls, tags in classes.items():
            k = np.isin(Eo, tags)
            if k.sum() < 50:
                continue
            d = d_all[k]
            res["cad_to_ours"][cls] = dict(n=int(k.sum()), median=float(np.median(d)),
                                           p90=pct(d, 90), p99=pct(d, 99), max=float(d.max()))
        Vb, Fb = group_mesh(b, ("body",))
        Sb = sample_surface(Vb, Fb, 120_000, seed=3)
        db, _ = tree_cad.query(Sb, workers=2)
        res["ours_to_cad"] = {"body_group": dict(n=len(Sb), median=float(np.median(db)),
                                                 p90=pct(db, 90), p99=pct(db, 99),
                                                 max=float(db.max()))}
        #  REVIEW FIX R-3 (adversarial review 2026-09-18): the threshold file's own rule says
        #  "distances are measured BOTH ways", but only the whole body group was measured in the
        #  reverse direction. A one-sided CAD->ours distance cannot see our part being too BIG:
        #  every CAD point still finds a near neighbour on the larger surface. Measured here per
        #  CAD region, by attributing each of our sample points to the CAD class of its nearest
        #  CAD triangle. The camera group is left out on our side for the same reason as DEV-2
        #  (the 4T CAD gimbal is not the 4E gimbal).
        Vr, Fr = group_mesh(b, tuple(g for g in _EXTERIOR_GROUPS if g != "camera"))
        Sr = sample_surface(Vr, Fr, 400_000, seed=4)
        dr, ir = tree_cad.query(Sr, workers=2)
        own_of_sample = Oc[cadF_of_sample]
        cls_of = own_of_sample[ir]
        for cls, tags in classes.items():
            k = np.isin(cls_of, tags)
            if k.sum() < 50:
                continue
            d = dr[k]
            res["ours_to_cad"][cls] = dict(n=int(k.sum()), median=float(np.median(d)),
                                           p90=pct(d, 90), p99=pct(d, 99), max=float(d.max()))
        out[tag] = res

    for cls, lim in thr["cad_to_ours_mm"].items():
        r = out["rev1"]["cad_to_ours"].get(cls)
        r0 = out["rev0"]["cad_to_ours"].get(cls)
        if r is None:
            continue
        if "median_max" in lim:
            T.add("C.4 distance", f"CAD->ours {cls} median", r["median"],
                  f"<= {lim['median_max']}", r["median"] <= lim["median_max"], " mm",
                  note="rev0 %.2f" % r0["median"])
        if "p90_max" in lim:
            T.add("C.4 distance", f"CAD->ours {cls} p90", r["p90"],
                  f"<= {lim['p90_max']}", r["p90"] <= lim["p90_max"], " mm",
                  note="rev0 %.2f" % r0["p90"])
    if dev5:
        for cls, why in (("nose_cradle__frozen_class",
                          "DEV-5: the frozen class 49+56+57+58, kept visible"),
                         ("nose_interior",
                          "DEV-5: interior solids 56+57+58; 1.8-5.8 % of their triangles are visible per view against 17 % for the exterior solid 49")):
            r = out["rev1"]["cad_to_ours"].get(cls)
            r0 = out["rev0"]["cad_to_ours"].get(cls)
            if r is None:
                continue
            T.add("C.4 distance", f"CAD->ours {cls} median", r["median"], "report", None, " mm",
                  note=f"{why}; rev0 {r0['median']:.2f}")
            T.add("C.4 distance", f"CAD->ours {cls} p90", r["p90"], "report", None, " mm",
                  note=f"{why}; rev0 {r0['p90']:.2f}")
    lim = thr["ours_to_cad_mm"]["body_group"]
    r = out["rev1"]["ours_to_cad"]["body_group"]
    r0 = out["rev0"]["ours_to_cad"]["body_group"]
    T.add("C.4 distance", "ours->CAD body median", r["median"], f"<= {lim['median_max']}",
          r["median"] <= lim["median_max"], " mm", note="rev0 %.2f" % r0["median"])
    T.add("C.4 distance", "ours->CAD body p90", r["p90"], f"<= {lim['p90_max']}",
          r["p90"] <= lim["p90_max"], " mm", note="rev0 %.2f" % r0["p90"])

    #  REVIEW FIX R-3: the reverse direction, per CAD region, scored with the same limits the
    #  file already states for the forward direction of that region.
    for cls, cl in thr["cad_to_ours_mm"].items():
        r = out["rev1"]["ours_to_cad"].get(cls)
        r0 = out["rev0"]["ours_to_cad"].get(cls)
        if r is None:
            continue
        if "median_max" in cl:
            T.add("C.4 distance", f"ours->CAD {cls} median", r["median"],
                  f"<= {cl['median_max']}", r["median"] <= cl["median_max"], " mm",
                  note="rev0 %.2f" % r0["median"])
        if "p90_max" in cl:
            T.add("C.4 distance", f"ours->CAD {cls} p90", r["p90"], f"<= {cl['p90_max']}",
                  r["p90"] <= cl["p90_max"], " mm", note="rev0 %.2f" % r0["p90"])

    #  REVIEW FIX R-3b: plan C.4 requires "no worse than revision 0 in any region". The frozen
    #  file scores only medians and p90s, so a region whose worst error grew was invisible.
    #  The SCORED statistic is p99, not the max: a max over 400,000 random surface samples moves
    #  by a millimetre between seeds, so scoring it would fail on sampling noise. The max is
    #  printed next to it.
    TOL = 0.5
    for dirn in ("cad_to_ours", "ours_to_cad"):
        lbl = "CAD->ours" if dirn == "cad_to_ours" else "ours->CAD"
        for cls in sorted(out["rev1"][dirn]):
            if cls in ("nose_cradle__frozen_class", "nose_interior"):
                continue
            r = out["rev1"][dirn][cls]
            r0 = out["rev0"][dirn].get(cls)
            if r0 is None:
                continue
            T.add("C.4 distance", f"{lbl} {cls} p99", r["p99"],
                  f"<= rev0 {r0['p99']:.2f} + {TOL} (plan C.4 'no worse in any region')",
                  r["p99"] <= r0["p99"] + TOL, " mm",
                  note=f"max {r['max']:.2f} (rev0 {r0['max']:.2f})")

    #  REVIEW FIX R-3c: the one-sided and two-sided nearest-surface distances both stay small
    #  when our part is the RIGHT SHAPE but the WRONG SIZE, as long as the excess is under the
    #  lambda/10 limit. The arm shafts are such a case in revision 1, so their plan-view
    #  projected area is compared with the CAD's directly. Scored by the plan's own C.4 rule:
    #  revision 1 may not be further from the CAD than revision 0 is.
    try:
        arms = _arm_shaft_plan_area(b0, b1, cad, thr)
        T.add("C.4 distance", "arm-shaft plan-view area vs CAD", arms["rev1"],
              f"|rev1-CAD| <= |rev0-CAD| ; CAD {arms['cad']:.0f}", arms["ok"], " mm2",
              note=f"rev0 {arms['rev0']:.0f} (off by {arms['d0']:+.0f}), "
                   f"rev1 off by {arms['d1']:+.0f}; window |y|>55 mm, r<205 mm")
        out["arm_shaft_plan_area_mm2"] = arms
    except Exception as e:                                       # pragma: no cover
        T.add("C.4 distance", "arm-shaft plan-view area vs CAD", f"EXC {e}", "report", None)
    return out


def _plan_area_mm2(V, F, cell=1.0):
    """Top-view projected area of a triangle set, rasterised into `cell` mm squares."""
    tv = np.asarray(V, float)[np.asarray(F, np.int64)][:, :, :2]
    if not len(tv):
        return 0.0
    lo = np.floor(tv.reshape(-1, 2).min(0) / cell).astype(int)
    hi = np.ceil(tv.reshape(-1, 2).max(0) / cell).astype(int)
    img = np.zeros(tuple((hi - lo + 2)[::-1]), bool)
    for t in tv:
        a = np.floor(t.min(0) / cell).astype(int) - lo
        b = np.ceil(t.max(0) / cell).astype(int) - lo
        xs = np.arange(a[0], b[0] + 1); ys = np.arange(a[1], b[1] + 1)
        if not len(xs) or not len(ys):
            continue
        X, Y = np.meshgrid((xs + lo[0] + 0.5) * cell, (ys + lo[1] + 0.5) * cell)
        v0 = t[1] - t[0]; v1 = t[2] - t[0]; v2 = np.stack([X, Y], -1) - t[0]
        den = v0[0] * v1[1] - v1[0] * v0[1]
        if abs(den) < 1e-12:
            continue
        u = (v2[..., 0] * v1[1] - v1[0] * v2[..., 1]) / den
        v = (v0[0] * v2[..., 1] - v2[..., 0] * v0[1]) / den
        img[np.ix_(ys, xs)] |= (u >= 0) & (v >= 0) & (u + v <= 1)
    return float(img.sum()) * cell * cell


def _arm_shaft_plan_area(b0, b1, cad, thr):
    """Plan-view area of the arm shafts, ours vs the CAD, in one geometric window."""
    tags = list(thr["cad_classes"]["front_arms"]) + list(thr["cad_classes"]["rear_arms"])
    Fc = cad["F"][np.isin(cad["owner"], tags)]
    def win(V, F):
        c = np.asarray(V, float)[np.asarray(F, np.int64)].mean(1)
        r = np.hypot(c[:, 0], c[:, 1])
        return F[(np.abs(c[:, 1]) > 55.0) & (r < 205.0)]
    a_cad = _plan_area_mm2(cad["V"], win(cad["V"], Fc))
    res = {"cad": a_cad}
    for tag, b in (("rev0", b0), ("rev1", b1)):
        Fb = b["F"][b["G"] == "body"]
        res[tag] = _plan_area_mm2(b["V"], win(b["V"], Fb))
    res["d0"] = res["rev0"] - a_cad
    res["d1"] = res["rev1"] - a_cad
    res["ok"] = abs(res["d1"]) <= abs(res["d0"])
    return res


VIEWS = [("top", 0, 90, (-1, 0, 0)), ("bottom", 0, -90, (1, 0, 0)),
         ("left_side_el0", 90, 0, (0, 0, 1)), ("front_el0", 0, 0, (0, 0, 1)),
         ("rear_el0", 180, 0, (0, 0, 1)), ("front_elm30", 0, -30, (0, 0, 1)),
         ("front_elm60", 0, -60, (0, 0, 1)), ("side_elm30", 90, -30, (0, 0, 1)),
         ("side_elm60", 90, -60, (0, 0, 1)), ("az45_elm30", 45, -30, (0, 0, 1)),
         ("az45_elm15", 45, -15, (0, 0, 1))]
ASPECTS = [(0, 0), (0, -15), (0, -30), (0, -45), (0, -60), (0, -75), (0, -90),
           (90, 0), (90, -30), (90, -60), (45, -30), (180, 0), (180, -30)]
EXT, SIZE, CEN = 270.0, 1080, np.array([10.0, 0.0, 15.0])


def c4_silhouette(T, b0, b1, th, cad, cache):
    from render import render
    thr = th["C4_reference_distance"]
    px2 = (2 * EXT / (SIZE - 1)) ** 2
    out = {}
    masks = {}
    for nm, az, el, up in VIEWS:
        key = f"cad_{nm}"
        if key in cache:
            masks[nm] = cache[key]
        else:
            _, m, _, _ = render(cad["V"], cad["F"], [(0.5, 0.5, 0.5)] * len(cad["F"]), az, el,
                                size=SIZE, extent=EXT, center=CEN, up_hint=up, mask_only=True)
            masks[nm] = m
            cache[key] = m
            print(f"    CAD mask {nm} done", flush=True)
    for tag, b in (("rev0", b0), ("rev1", b1)):
        Vx, Fx = group_mesh(b, _EXTERIOR_GROUPS)
        res = {}
        for nm, az, el, up in VIEWS:
            _, mo, _, _ = render(Vx, Fx, [(0.5, 0.5, 0.5)] * len(Fx), az, el, size=SIZE,
                                 extent=EXT, center=CEN, up_hint=up, mask_only=True)
            mc = masks[nm]
            iou = float((mc & mo).sum() / max(1, (mc | mo).sum()))
            res[nm] = dict(iou=iou, ours_mm2=float(mo.sum() * px2), cad_mm2=float(mc.sum() * px2))
        out[tag] = res
    T.add("C.4 silhouette", "top-view IoU", out["rev1"]["top"]["iou"],
          f">= {thr['silhouette_iou_min']['top']}",
          out["rev1"]["top"]["iou"] >= thr["silhouette_iou_min"]["top"],
          note="rev0 %.3f" % out["rev0"]["top"]["iou"])
    worst = None
    for nm, _, _, _ in VIEWS:
        if nm == "top":
            continue
        d = out["rev1"][nm]["iou"] - out["rev0"][nm]["iou"]
        if worst is None or d < worst[1]:
            worst = (nm, d)
    T.add("C.4 silhouette", "worst IoU change vs rev0", f"{worst[0]} {worst[1]:+.3f}",
          ">= -0.02", worst[1] >= -0.02)
    return out


def _cad_facing_mm2(cad, thr_classes, cls, az, el, cone_deg=10):
    """Facing area of one CAD class at one aspect, measured exactly as `c5_facing` measures ours.

    The WHOLE CAD is rendered so that the rest of the aircraft occludes the class, then only the
    visible pixels whose triangle belongs to `cls` and whose normal is inside the cone are
    counted. Serves DEV-6: our metal motor cans need a reference of the same kind.
    """
    from render import render, camera
    px2 = (2 * EXT / (SIZE - 1)) ** 2
    Vc, Fc, Oc = cad["V"], cad["F"], cad["owner"]
    A, B, C = Vc[Fc[:, 0]], Vc[Fc[:, 1]], Vc[Fc[:, 2]]
    N = np.cross(B - A, C - A)
    N = N / (np.linalg.norm(N, axis=1)[:, None] + 1e-12)
    up = (0, 0, 1) if abs(el) < 89 else (1, 0, 0)
    ids = render(Vc, Fc, [(0, 0, 0)] * len(Fc), az, el, size=SIZE, extent=EXT, center=CEN,
                 up_hint=up, mask_only=True, want_ids=True)[-1]
    fwd, _, _ = camera(az, el, up)
    vis = ids[ids >= 0]
    cs = np.abs(N[vis] @ (-fwd))
    k = np.isin(Oc[vis], thr_classes[cls]) & (cs > math.cos(math.radians(cone_deg)))
    return float(k.sum() * px2)


def c5_facing(T, b0, b1, th, cad):
    from render import render, camera
    thr = th["C5_facing_area"]
    px2 = (2 * EXT / (SIZE - 1)) ** 2
    out = {}
    from drones import DRONE_GROUP_MAT
    for tag, b in (("rev0", b0), ("rev1", b1)):
        Vx, Fx = group_mesh(b, _EXTERIOR_GROUPS + ("battery", "pcb"))
        Gx = b["G"][np.isin(b["G"], list(_EXTERIOR_GROUPS + ("battery", "pcb")))]
        A, B, C = Vx[Fx[:, 0]], Vx[Fx[:, 1]], Vx[Fx[:, 2]]
        N = np.cross(B - A, C - A)
        N = N / (np.linalg.norm(N, axis=1)[:, None] + 1e-12)
        res = {}
        for az, el in ASPECTS:
            up = (0, 0, 1) if abs(el) < 89 else (1, 0, 0)
            _, msk, _, _, ids = render(Vx, Fx, [(0, 0, 0)] * len(Fx), az, el, size=SIZE,
                                       extent=EXT, center=CEN, up_hint=up, mask_only=True,
                                       want_ids=True)
            fwd, _, _ = camera(az, el, up)
            vis = ids[ids >= 0]
            cs = np.abs(N[vis] @ (-fwd))
            g = Gx[vis]
            r = dict(silhouette_mm2=float(msk.sum() * px2),
                     facing5_mm2=float((cs > math.cos(math.radians(5))).sum() * px2),
                     facing10_mm2=float((cs > math.cos(math.radians(10))).sum() * px2))
            r["facing10_by_group"] = {k: float(((g == k) & (cs > math.cos(math.radians(10)))).sum()
                                               * px2) for k in np.unique(g)}
            r["facing10_metal_mm2"] = sum(v for k, v in r["facing10_by_group"].items()
                                          if k in _METAL_GROUPS)
            res[f"az{az}_el{el}"] = r
        out[tag] = res

    h = thr["hard"]
    dev6 = _deviation(th, "DEV-6")
    v = out["rev1"]["az180_el0"]["facing10_metal_mm2"]
    if dev6:
        #  ⚠ DEVIATION DEV-6 (docs/mesh_rev1/matrice4e_deviations_0918.json, needs user
        #  approval). "metal facing az 180 = 0" cannot be met by an aircraft that has metal
        #  motor cans; what M4E-3 actually changed is the battery's rear face, and that is now 0.
        #  The frozen row is kept, unscored, next to the two rows that are testable.
        T.add("C.5 facing", "metal facing az180 el0 (10 deg), all metal groups (frozen row)", v,
              f"<= {h['metal_facing10_az180_el0_mm2_max']} — DEVIATION DEV-6, see the "
              f"deviations file", None, " mm2",
              note="rev0 %.0f" % out["rev0"]["az180_el0"]["facing10_metal_mm2"])
        by = out["rev1"]["az180_el0"]["facing10_by_group"]
        by0 = out["rev0"]["az180_el0"]["facing10_by_group"]
        nm = sum(val for k, val in by.items() if k in _METAL_GROUPS and k != "motor")
        nm0 = sum(val for k, val in by0.items() if k in _METAL_GROUPS and k != "motor")
        T.add("C.5 facing", "non-motor metal facing az180 el0 (10 deg)", nm,
              f"<= {h['metal_facing10_az180_el0_mm2_max']}",
              nm <= h["metal_facing10_az180_el0_mm2_max"], " mm2",
              note=f"rev0 {nm0:.0f} (the battery rear face M4E-3 closed over)")
        mot = by.get("motor", 0.0)
        cadm = _cad_facing_mm2(cad, thr_classes=th["C4_reference_distance"]["cad_classes"],
                               cls="motors", az=180, el=0, cone_deg=10)
        band = thr["cad_ratio_rows"]["az180_el0_facing5"]["band"]
        ratio = mot / cadm if cadm > 0 else float("inf")
        T.add("C.5 facing", "motor metal facing az180 el0 (10 deg) ratio to CAD motor solids",
              ratio, f"in [{band[0]}, {band[1]}] (DEV-6)", band[0] <= ratio <= band[1],
              note=f"ours {mot:.0f} mm2, CAD motor solids {cadm:.0f} mm2; rev0 "
                   f"{by0.get('motor', 0.0):.0f} mm2")
    else:
        T.add("C.5 facing", "metal facing az180 el0 (10 deg)", v,
              f"<= {h['metal_facing10_az180_el0_mm2_max']}",
              v <= h["metal_facing10_az180_el0_mm2_max"], " mm2",
              note="rev0 %.0f" % out["rev0"]["az180_el0"]["facing10_metal_mm2"])
    v = out["rev1"]["az0_el-90"]["facing10_metal_mm2"]
    T.add("C.5 facing", "metal facing nadir (10 deg)", v,
          f"<= {h['metal_facing10_az0_el-90_mm2_max']}",
          v <= h["metal_facing10_az0_el-90_mm2_max"], " mm2",
          note="rev0 %.0f" % out["rev0"]["az0_el-90"]["facing10_metal_mm2"])
    p = thr["plan_targets"]
    v = out["rev1"]["az0_el0"]["facing10_by_group"].get("body", 0.0)
    T.add("C.5 facing", "body facing az0 el0 (10 deg)", v,
          f"<= {p['body_group_facing10_az0_el0_mm2_max']}",
          v <= p["body_group_facing10_az0_el0_mm2_max"], " mm2",
          note="rev0 %.0f" % out["rev0"]["az0_el0"]["facing10_by_group"].get("body", 0.0))
    v = out["rev1"]["az180_el0"]["facing5_mm2"]
    T.add("C.5 facing", "total facing az180 el0 (5 deg)", v,
          f"<= {p['total_facing5_az180_el0_mm2_max']}",
          v <= p["total_facing5_az180_el0_mm2_max"], " mm2",
          note="rev0 %.0f" % out["rev0"]["az180_el0"]["facing5_mm2"])
    for row, cfg in thr["cad_ratio_rows"].items():
        asp, cone = row.rsplit("_", 1)
        k = "facing5_mm2" if cone == "facing5" else "facing10_mm2"
        r1 = out["rev1"][asp][k] / cfg["cad_mm2"]
        r0 = out["rev0"][asp][k] / cfg["cad_mm2"]
        lo, hi = cfg["band"]
        ok = (lo <= r1 <= hi) and abs(r1 - 1.0) < abs(r0 - 1.0)
        T.add("C.5 facing", f"{row} ratio to CAD", r1, f"in [{lo}, {hi}] and closer to 1 than rev0",
              ok, note="rev0 %.3f" % r0)
    return out


# --------------------------------------------------------------------------- #
#  C.6 / C.7 / C.8 / C.11 / C.12 / C.13
# --------------------------------------------------------------------------- #
def c6_facets(T, b0, b1, th):
    thr = th["C6_facets"]
    import drone_parts_rev1 as P
    out = {}
    nf = int(len(b1["F"]))
    T.add("C.6 facets", "frame faces", nf, f"<= {thr['frame_faces_max']}",
          nf <= thr["frame_faces_max"], note="rev0 %d" % len(b0["F"]))
    worst = 0.0
    for g in sorted(set(b1["G"])):
        m = tri_of(b1["V"] * MM, b1["F"][b1["G"] == g])
        s = P.mesh_sagitta_mm(m)
        out[g] = s
        worst = max(worst, s)
    #  REVIEW FIX R-5 (adversarial review 2026-09-18): the loop above walks b1["G"], which is
    #  the FRAME's groups — the propeller was never measured, although it is the most strongly
    #  curved part of the mesh and plan B.1's facet rule covers the whole mesh.
    import drones as _dr
    for _mir in (False, True):
        _p = _dr.build_propeller(b1["spec"], mirror=_mir)
        _m = trimesh.Trimesh(vertices=np.asarray(_p.v, float),
                             faces=np.asarray(_p.f, np.int64), process=False)
        out[f"prop{'_mirror' if _mir else ''}"] = P.mesh_sagitta_mm(_m)
        worst = max(worst, out[f"prop{'_mirror' if _mir else ''}"])
    T.add("C.6 facets", "worst whole-mesh sagitta", worst, f"<= {thr['sagitta_mm_max']}",
          worst <= thr["sagitta_mm_max"], " mm",
          note=max(out, key=out.get) + " (props included, review fix R-5)")
    rep = b1.get("report") or getattr(b1["frame"], "rev1_report", None) or {}
    for k, v in rep.items():
        if isinstance(v, dict) and "faces" in v and "plan_item" in v:
            key = {"P1": "P1_shell", "P3": "P3_motor", "P4": "P4_arm", "P8": "P8_box"}.get(v["plan_item"])
            lim = thr["part_face_budgets"].get(key)
            if lim is None:
                continue
            if v["plan_item"] == "P8":
                T.add("C.6 facets", f"faces {k}", v["faces"], f"<= {lim} (unclipped only)", None)
            else:
                T.add("C.6 facets", f"faces {k}", v["faces"], f"<= {lim}", v["faces"] <= lim)
    return out


def c7_props(T, b0, b1, th):
    thr = th["C7_props"]
    import drone_parts_rev1 as P
    import drones
    import mesh_check as MC
    out = {}
    for tag, b in (("rev0", b0), ("rev1", b1)):
        res = {}
        for mir in (False, True):
            p = drones.build_propeller(b["spec"], mirror=mir)
            spin = -1 if mir else +1
            rows = {}
            for rr in thr["r_over_R"]:
                try:
                    o = P.blade_orientation(p, spin=spin, n_blades=int(b["spec"].prop_blades),
                                            r_over_R=rr, n_sample=120_000)
                except Exception as e:
                    rows[str(rr)] = dict(error=repr(e))
                    continue
                rows[str(rr)] = o
            res["mirrored" if mir else "plain"] = rows
        res["handedness"] = MC.check_handedness(b["spec"], mesh=b["drone"])
        out[tag] = res
    ok_all = True
    for which in ("plain", "mirrored"):
        for rr in thr["r_over_R"]:
            o = out["rev1"][which][str(rr)]
            good = bool(o.get("all_ok", False))
            ok_all &= good
            T.add("C.7 propeller", f"P6 cues {which} r/R={rr}", "ok" if good else "NOT ok",
                  "thick edge raised and leading", good,
                  note=("rev0 " + ("ok" if out["rev0"][which][str(rr)].get("all_ok", False)
                                   else "NOT ok")))
    hd = out["rev1"]["handedness"]
    T.add("C.7 propeller", "check_handedness", hd.get("ok"), "True", bool(hd.get("ok")))
    # chord and blade angle vs rev0
    ch = {}
    for tag, b in (("rev0", b0), ("rev1", b1)):
        p = drones.build_propeller(b["spec"])
        row = {}
        for rr in thr["r_over_R"]:
            o = out[tag]["plain"][str(rr)]
            if "blades" in o:
                row[str(rr)] = dict(
                    chord_mm=float(np.mean([x["chord_mm"] for x in o["blades"]])),
                    angle_deg=float(np.mean([x["angle_inertia_deg"] for x in o["blades"]])))
        ch[tag] = row
    out["chord_angle"] = ch
    for rr in thr["r_over_R"]:
        k = str(rr)
        if k in ch["rev0"] and k in ch["rev1"]:
            dc = abs(ch["rev1"][k]["chord_mm"] - ch["rev0"][k]["chord_mm"])
            da = abs(ch["rev1"][k]["angle_deg"] - ch["rev0"][k]["angle_deg"])
            T.add("C.7 propeller", f"chord change r/R={rr}", dc,
                  f"<= {thr['chord_max_abs_diff_mm_vs_rev0']}",
                  dc <= thr["chord_max_abs_diff_mm_vs_rev0"], " mm")
            T.add("C.7 propeller", f"blade angle change r/R={rr}", da,
                  f"<= {thr['blade_angle_max_abs_diff_deg_vs_rev0']}",
                  da <= thr["blade_angle_max_abs_diff_deg_vs_rev0"], " deg")
    return out


def c8_kinematics(T, b0, b1, th):
    from articulated_fast import FastPoser
    thr = th["C8_kinematics"]
    dirs = [int(r["dir"]) for r in b1["rl"]]
    T.add("C.8 kinematics", "rotor_dirs", dirs, thr["rotor_dirs"], dirs == thr["rotor_dirs"],
          note="rev0 %s" % [int(r["dir"]) for r in b0["rl"]])
    fp = FastPoser(b1["spec"])
    v = fp.verify()
    T.add("C.8 kinematics", "FastPoser.verify", v["max_abs_vertex_diff_m"],
          f"<= {thr['fastposer_verify_max_m']}",
          v["max_abs_vertex_diff_m"] <= thr["fastposer_verify_max_m"], " m")
    for f in ("prop_dia_mm", "prop_blades", "num_rotors", "hover_rpm"):
        T.add("C.8 kinematics", f, getattr(b1["spec"], f), thr[f],
              getattr(b1["spec"], f) == thr[f])
    return dict(dirs=dirs, verify=v)


def c11_certificates(T, b0, b1, th):
    thr = th["C11_certificates"]
    out = {}
    #  The repository's own certificate is the one plan C.11 names ("mesh_symmetry and
    #  mesh_placement pass with revision-0 budgets"), so it is the scored row.
    import mesh_symmetry as MS
    for tag, b in (("rev0", b0), ("rev1", b1)):
        try:
            out[f"mesh_symmetry_{tag}"] = MS.check_lateral_symmetry(b["spec"], mesh=b["drone"])
        except Exception as e:
            out[f"mesh_symmetry_{tag}"] = dict(error=repr(e))
    r1 = out["mesh_symmetry_rev1"]
    r0 = out["mesh_symmetry_rev0"]
    T.add("C.11 certificates", "mesh_symmetry.check_lateral_symmetry", r1.get("ok"),
          "True (revision-0 budgets)", bool(r1.get("ok")),
          note="rev0 ok=%s" % r0.get("ok"))
    worst = 0.0
    #  ⚠ METHOD CORRECTION, logged in the ledger: the frozen file describes a nearest-neighbour
    #    distance to the original VERTEX cloud. That is not a symmetry test — a shape that is
    #    exactly symmetric but triangulated asymmetrically (which is what a manifold boolean
    #    returns) scores 15 mm on it. The distance is measured to the original SURFACE instead
    #    (point-to-triangle, exact). The threshold number is unchanged.
    for g in sorted(set(b1["G"])):
        m = tri_of(b1["V"], b1["F"][b1["G"] == g])
        M = np.asarray(m.vertices).copy(); M[:, 1] *= -1.0
        d = np.abs(trimesh.proximity.ProximityQuery(m).signed_distance(M))
        out[g] = float(d.max())
        worst = max(worst, float(d.max()))
    grp = {k: v for k, v in out.items() if not k.startswith("mesh_symmetry_")}
    #  ⚠ report-only: the camera head is NOT mirror-symmetric in revision 0 either (its four
    #    front apertures are four different sensors), so a 0.01 mm budget on it is a
    #    threshold-writing error, not a geometry defect. Both revisions are printed.
    T.add("C.11 certificates", "mirror residual, worst group (report)",
          f"{max(grp, key=grp.get)} {worst:.3f} mm", "report", None,
          note="airframe without camera: %.3f mm" % max(
              v for k, v in grp.items() if k != "camera"))
    C0 = np.array([r["center"] for r in b0["rl"]], float) * 1000.0
    C1 = np.array([r["center"] for r in b1["rl"]], float) * 1000.0
    d = float(np.abs(C1[:, :2] - C0[:, :2]).max())
    T.add("C.11 certificates", "rotor placement vs rev0", d,
          f"<= {thr['placement_rotor_xy_max_abs_diff_mm']}",
          d <= thr["placement_rotor_xy_max_abs_diff_mm"], " mm")
    return out


def c12_materials(T, b0, b1, th):
    from drones import DRONE_GROUP_MAT
    out = {}
    for tag, b in (("rev0", b0), ("rev1", b1)):
        per = {}
        for g in sorted(set(b["G"])):
            m = tri_of(b["V"], b["F"][b["G"] == g])
            mat = str(DRONE_GROUP_MAT[g])
            d = per.setdefault(mat, dict(area_mm2=0.0, volume_mm3=0.0, groups=[]))
            d["area_mm2"] += float(m.area)
            d["volume_mm3"] += float(m.volume) if m.is_watertight else 0.0
            d["groups"].append(g)
        out[tag] = per
    unknown = sorted(set(b1["G"]) - set(DRONE_GROUP_MAT))
    T.add("C.12 materials", "groups outside DRONE_GROUP_MAT", unknown, "[]", not unknown)
    for mat in sorted(set(out["rev0"]) | set(out["rev1"])):
        a0 = out["rev0"].get(mat, {}).get("area_mm2", 0.0)
        a1 = out["rev1"].get(mat, {}).get("area_mm2", 0.0)
        T.add("C.12 materials", f"area[{mat}]", a1, None, None, " mm2",
              note=f"rev0 {a0:.0f}  ({100*(a1-a0)/max(a0,1e-9):+.1f} %)")
    return out


def c13_repairs(T, b0, b1, th):
    thr = th["C13_canonical_repairs"]
    out = {}
    Vb, Fb = group_mesh(b1, ("body",))
    body = tri_of(Vb, Fb)
    T.add("C.13 repairs", "body closed", bool(body.is_watertight), "True",
          bool(body.is_watertight) == thr["body_closed"])
    nb = len(tri_of(*group_mesh(b1, ("battery",))).split(only_watertight=False, repair=False))
    T.add("C.13 repairs", "battery group parts", nb, f"<= {thr['battery_group_parts_max']}",
          nb <= thr["battery_group_parts_max"], note="rev0 2")
    # battery / pcb interpenetration
    mb = tri_of(*group_mesh(b1, ("battery",)))
    mp = tri_of(*group_mesh(b1, ("pcb",)))
    cen = mp.triangles.mean(1)
    inter = 100.0 * float(mb.contains(cen).mean()) if len(cen) else 0.0
    out["pcb_in_battery_pct"] = inter
    T.add("C.13 repairs", "pcb faces inside the battery", inter,
          f"<= {thr['battery_pcb_interpenetration_pct_max']}",
          inter <= thr["battery_pcb_interpenetration_pct_max"], " %")
    return out


# --------------------------------------------------------------------------- #
def load_cad(scratch):
    d = np.load(os.path.join(scratch, "cad_tris.npz"))
    e = np.load(os.path.join(scratch, "cad_edges.npz"))
    return dict(V=d["V"].astype(float), F=d["F"], owner=d["owner"],
                edges=e["P"].astype(float), edge_owner=e["owner"])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--drone", required=True)
    ap.add_argument("--rev", type=int, default=1)
    ap.add_argument("--out", required=True, help="JSON ledger path (scratch only)")
    ap.add_argument("--cad-scratch", default=os.environ.get("M0917", ""),
                    help="folder holding cad_tris.npz and cad_edges.npz")
    ap.add_argument("--skip", default="", help="comma-separated section ids to skip, e.g. C4,C5")
    a = ap.parse_args(argv)
    if a.drone != "matrice4e":
        raise SystemExit(f"⛔ only 'matrice4e' is implemented in this unit, got {a.drone!r}")
    skip = {s.strip().upper() for s in a.skip.split(",") if s.strip()}

    if a.cad_scratch and a.cad_scratch not in sys.path:
        sys.path.insert(0, a.cad_scratch)     # the scratch z-buffer renderer (render.py)
    thp = os.path.join(ROOT, "docs", "mesh_rev1", f"{a.drone}_acceptance_thresholds.json")
    th = json.load(open(thp))
    th_sha = sha256_file(thp)
    print(f"thresholds {thp}\n  sha256 {th_sha}\n  frozen  {th['_meta']['frozen_utc']}", flush=True)
    #  ⚠ Post-run deviations live in their OWN dated file. The frozen threshold file above is
    #  never edited; each deviation replaces one row that the model cannot reach, and the
    #  original row stays in the table as a report row. Every entry is printed here and copied
    #  into the ledger, so a reader always sees that a row was replaced and why.
    dvp = os.path.join(ROOT, "docs", "mesh_rev1", f"{a.drone}_deviations_0918.json")
    dev_sha = None
    if os.path.exists(dvp):
        th["_deviations_after_the_run"] = json.load(open(dvp))
        dev_sha = sha256_file(dvp)
        print(f"\n⚠ POST-RUN DEVIATIONS {dvp}\n  sha256 {dev_sha}")
        for d in th["_deviations_after_the_run"]["deviations"]:
            print(f"  {d['id']}: {d['from']}\n       -> {d['to']}")
        print("  These need user approval (plan critique M8). The frozen threshold file is "
              "unchanged.\n", flush=True)

    t0 = time.time()
    b0 = build(a.drone, 0)
    b1 = build(a.drone, a.rev)
    print(f"built rev0 and rev{a.rev} in {time.time()-t0:.1f} s", flush=True)

    cad = load_cad(a.cad_scratch) if a.cad_scratch else None
    #  REVIEW FIX R-1 (adversarial review 2026-09-18): without --cad-scratch (or $M0917) the
    #  reference sections C.4 and C.5 used to vanish from the table with no warning — 23 scored
    #  rows, including every shape comparison against the CAD, and the run still printed a clean
    #  "scored 77, passed 75". A missing reference is now a refusal unless it is asked for by
    #  name with --skip.
    if cad is None and not {"C4", "C5"} <= skip:
        raise SystemExit(
            "⛔ no CAD reference: pass --cad-scratch <folder with cad_tris.npz and "
            "cad_edges.npz> (or set $M0917). Without it sections C.4 and C.5 cannot run, and "
            "silently dropping them would turn a 100-row acceptance into a 77-row one that "
            "still reads as complete. To run without them on purpose: --skip C4,C5")
    T = Table()
    L = dict(_meta=dict(drone=a.drone, rev=a.rev, thresholds_sha256=th_sha,
                        thresholds_path=os.path.relpath(thp, ROOT),
                        utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        omp=os.environ.get("OMP_NUM_THREADS"),
                        deviations_after_the_run_path=(os.path.relpath(dvp, ROOT)
                                                       if dev_sha else None),
                        deviations_after_the_run_sha256=dev_sha,
                        deviations_after_the_run=th.get("_deviations_after_the_run"),
                        cad=bool(cad)))
    L["C1"] = c1_topology(T, b0, b1, th)
    L["C2"] = c2_attachment(T, b0, b1, th, cad)
    L["C3"] = c3_dimensions(T, b0, b1, th, cad)
    if cad is not None and "C4" not in skip:
        L["C4_distance"] = c4_distance(T, b0, b1, th, cad)
        L["C4_silhouette"] = c4_silhouette(T, b0, b1, th, cad, {})
    if cad is not None and "C5" not in skip:
        L["C5"] = c5_facing(T, b0, b1, th, cad)
    L["C6"] = c6_facets(T, b0, b1, th)
    if "C7" not in skip:
        L["C7"] = c7_props(T, b0, b1, th)
    L["C8"] = c8_kinematics(T, b0, b1, th)
    L["C9"] = dict(scored=False, note=th["C9_specular_census"]["note"])
    L["C11"] = c11_certificates(T, b0, b1, th)
    L["C12"] = c12_materials(T, b0, b1, th)
    L["C13"] = c13_repairs(T, b0, b1, th)

    print(T.render())
    sc = T.scored()
    bad = T.failed()
    print(f"\n{'='*84}\n  scored rows {len(sc)}   passed {len(sc)-len(bad)}   FAILED {len(bad)}")
    for r in bad:
        print(f"    FAIL  {r['section']}  {r['name']}: {r['value']}  target {r['target']}")
    #  The builder's own repair log (REVIEW FIX F-3), so the ledger carries what the sliver
    #  repair did per group and what it refused to do.
    L["sliver_repair"] = (b1.get("report") or {}).get("sliver_repair")
    L["table"] = T.rows
    L["summary"] = dict(scored=len(sc), passed=len(sc) - len(bad), failed=len(bad),
                        failed_rows=[f"{r['section']}/{r['name']}" for r in bad],
                        sections_skipped=sorted(skip) + ([] if cad is not None else ["C4", "C5"]),
                        cad_reference_loaded=bool(cad))
    if skip or cad is None:
        print(f"  ⚠ SECTIONS NOT RUN: {L['summary']['sections_skipped']} — "
              f"the row counts above are NOT the full acceptance.")

    def _j(o):
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return float(o)
        if isinstance(o, (np.bool_,)):
            return bool(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        return str(o)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(L, open(a.out, "w"), indent=1, default=_j)
    print(f"  ledger -> {a.out}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
