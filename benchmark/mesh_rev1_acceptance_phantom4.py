# -*- coding: utf-8 -*-
"""mesh_rev1_acceptance.py — the plan C acceptance tests for one mesh revision.

    mesh_rev1_acceptance.py --drone phantom4 [--rev 1] [--out <ledger.json>]

Runs C.1 … C.13 for (drone, revision), prints a pass/fail table and writes a JSON ledger.
Thresholds come from docs/mesh_rev1/<key>_acceptance_thresholds.json, which plan C freezes
**before** the first run: this script never writes that file and never relaxes a value in it.

Nothing here touches the live repository. Renders and OBJ output belong to the caller's scratch;
this script only reads meshes it builds in memory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time

import numpy as np
import trimesh

MM = 1e-3
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCAN_DIR = ('/tmp/claude-0/-workspace/8ed65148-4553-4ebc-8477-9670ae39b001/scratchpad/'
            'mesh_0917/phantom_family/data')


# --------------------------------------------------------------------------- #
#  small helpers
# --------------------------------------------------------------------------- #
class Table:
    def __init__(self):
        self.rows = []

    def add(self, check, item, got, want, ok, note=""):
        self.rows.append(dict(check=check, item=item, got=got, want=want,
                              ok=None if ok is None else bool(ok), note=note))

    def report(self):
        scored = [r for r in self.rows if r["ok"] is not None]
        bad = [r for r in scored if not r["ok"]]
        w = max([len(r["item"]) for r in self.rows] + [20])
        out = []
        out.append(f"{'':4s} {'check':6s} {'item':{w}s} {'measured':>26s}   {'required':<34s}")
        out.append("-" * (4 + 7 + w + 30 + 36))
        for r in self.rows:
            mark = "  · " if r["ok"] is None else ("PASS" if r["ok"] else "FAIL")
            got = r["got"] if isinstance(r["got"], str) else _fmt(r["got"])
            want = r["want"] if isinstance(r["want"], str) else _fmt(r["want"])
            out.append(f"{mark:4s} {r['check']:6s} {r['item']:{w}s} {got:>26s}   {want:<34s}"
                       + (f"  {r['note']}" if r["note"] else ""))
        out.append("-" * (4 + 7 + w + 30 + 36))
        out.append(f"scored {len(scored)}   PASS {len(scored) - len(bad)}   FAIL {len(bad)}   "
                   f"report-only {len(self.rows) - len(scored)}")
        return "\n".join(out), len(bad)


def _fmt(v):
    if isinstance(v, float):
        return f"{v:.4g}"
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(_fmt(x) for x in v) + "]"
    return str(v)


def _tri(V, F):
    return trimesh.Trimesh(vertices=np.asarray(V, float), faces=np.asarray(F), process=False)


def groups_of(mesh):
    V = np.asarray(mesh.v, float)
    F = np.asarray(mesh.f)
    G = np.asarray(mesh.g).astype(str)
    out = {}
    for g in sorted(set(G)):
        sel = F[G == g]
        m = trimesh.Trimesh(vertices=V, faces=sel, process=True)
        m.remove_unreferenced_vertices()
        out[g] = m
    return out


def sample_mesh(m, n, seed=0):
    return trimesh.sample.sample_surface(m, int(n), seed=seed)[0]


# --------------------------------------------------------------------------- #
#  C.1 topology
# --------------------------------------------------------------------------- #
def c1_topology(T, gm, thr, rev0_gm):
    import mesh_topo_check as tc
    decl = thr["C1_topology"]["declared_components"]
    lim = float(thr["C1_topology"]["sliver_aspect_ratio_limit"])
    margin = float(thr["C1_topology"]["sliver_frac_margin"])
    rev0_frac = _sliver_frac(rev0_gm, lim)
    for g, m in gm.items():
        ec = tc.edge_census(np.asarray(m.faces), len(m.vertices))
        nb = int(ec["n_boundary"])
        nnm = int(ec["n_nonmanifold"])
        si = tc.self_intersections(np.asarray(m.vertices), np.asarray(m.faces))
        n_si = int(si["n_hits"] or 0)
        T.add("C.1", f"{g}: watertight", bool(m.is_watertight), True, m.is_watertight)
        T.add("C.1", f"{g}: boundary edges", nb, 0, nb == 0)
        T.add("C.1", f"{g}: non-manifold edges", nnm, 0, nnm == 0)
        T.add("C.1", f"{g}: self-intersections", n_si, 0, n_si == 0)
        T.add("C.1", f"{g}: winding + outward", bool(m.is_winding_consistent and m.volume > 0),
              True, m.is_winding_consistent and m.volume > 0)
        got = int(len(m.split(only_watertight=False)))
        T.add("C.1", f"{g}: components", got, decl.get(g, "declared?"),
              got == decl.get(g))
        dup = int(tc.duplicate_faces(np.asarray(m.faces)))
        T.add("C.1", f"{g}: duplicate faces", dup, 0, dup == 0)
    f1 = _sliver_frac(gm, lim)
    T.add("C.1", "sliver fraction (aspect > 50)", f1, f"<= rev0 {rev0_frac:.4g} + {margin}",
          f1 <= rev0_frac + margin)
    #  diagnostics for the same quantity, not scored: the frozen row above is a **fraction** of
    #  the mesh, and revision 1's frame has 39 % fewer faces, so the same amount of boolean-seam
    #  sliver geometry is a larger share. The absolute count and the repository's own sliver
    #  definition (min angle < 0.5 deg, mesh_topo_check.SLIVER_MIN_ANGLE_DEG) are reported too.
    n1 = int(round(f1 * sum(len(m.faces) for m in gm.values())))
    n0 = int(round(rev0_frac * sum(len(m.faces) for m in rev0_gm.values())))
    T.add("C.1", "sliver faces, absolute (diagnostic)", n1, f"rev0 {n0}", None)
    s1 = sum(int(tc.triangle_quality(np.asarray(m.vertices),
                                     np.asarray(m.faces))["n_sliver"]) for m in gm.values())
    s0 = sum(int(tc.triangle_quality(np.asarray(m.vertices),
                                     np.asarray(m.faces))["n_sliver"]) for m in rev0_gm.values())
    T.add("C.1", "repo slivers, min angle < 0.5 deg (diagnostic)", s1, f"rev0 {s0}", None)
    z1 = sum(int(tc.triangle_quality(np.asarray(m.vertices),
                                     np.asarray(m.faces))["n_zero_area"]) for m in gm.values())
    T.add("C.1", "zero-area faces", z1, "0", z1 == 0)


def _sliver_frac(gm, lim):
    n_bad = n_all = 0
    for m in gm.values():
        V = np.asarray(m.vertices)
        F = np.asarray(m.faces)
        a = np.linalg.norm(V[F[:, 1]] - V[F[:, 0]], axis=1)
        b = np.linalg.norm(V[F[:, 2]] - V[F[:, 1]], axis=1)
        c = np.linalg.norm(V[F[:, 0]] - V[F[:, 2]], axis=1)
        s = 0.5 * (a + b + c)
        area = np.sqrt(np.maximum(s * (s - a) * (s - b) * (s - c), 0.0))
        longest = np.maximum.reduce([a, b, c])
        h = np.where(area > 0, 2.0 * area / np.maximum(longest, 1e-30), 0.0)
        aspect = np.where(h > 0, longest / np.maximum(h, 1e-30), np.inf)
        n_bad += int((aspect > lim).sum())
        n_all += len(F)
    return float(n_bad) / max(n_all, 1)


# --------------------------------------------------------------------------- #
#  C.2 attachment
# --------------------------------------------------------------------------- #
def c2_attachment(T, parts, gm, thr, spec, rev0_gm, frame_mesh):
    tc2 = thr["C2_attachment"]
    gaps = [(p.name, p.info.get("host_gap_mm")) for p in parts
            if p.info.get("cut_against_host") or p.info.get("host_gap_mm") is not None]
    worst = max([g for _, g in gaps if g is not None], default=0.0)
    T.add("C.2", "host-cut gap, worst part", worst, f"<= {tc2['leg_gap_mm_max']}",
          worst <= tc2["leg_gap_mm_max"], note=f"{len(gaps)} cut parts")
    #  motor pods sit on the arm fairing: they are unioned into 'body', so the pod is attached
    #  iff 'body' is one component, which C.1 already scores.
    shell = gm["body"]
    for g in ("battery", "pcb"):
        if g not in gm:
            continue
        P = np.asarray(gm[g].vertices)
        inside = shell.contains(P)
        d = trimesh.proximity.signed_distance(shell, P)
        clear = float(np.min(d)) / MM
        T.add("C.2", f"{g}: vertices inside shell", 100.0 * float(inside.mean()), "100 %",
              bool(inside.all()))
        T.add("C.2", f"{g}: clearance to shell", clear,
              f">= {tc2['internal_metal_clearance_mm_min']} mm",
              clear >= tc2["internal_metal_clearance_mm_min"])
    #  floating parts (frozen threshold `floating_parts_max`, plan C.2 "no floating parts").
    #  Reviewer 2026-09-17: the threshold existed in the frozen file but no row scored it.
    #  A structural component counts as attached when it either interpenetrates another group's
    #  solid or its surface comes within `leg_gap_mm_max` of one. battery and pcb are excluded:
    #  they are meant to sit free inside the shell and the containment rows above score them.
    struct = [g for g in gm if g not in ("battery", "pcb")]
    floating = []
    for g in struct:
        for i, c in enumerate(gm[g].split(only_watertight=False)):
            best = np.inf
            attached = False
            for g2 in struct:
                if g2 == g:
                    continue
                sd = trimesh.proximity.signed_distance(gm[g2], np.asarray(c.vertices))
                if float(sd.max()) > 0.0:          # a vertex inside g2's solid
                    attached = True
                    best = 0.0
                    break
                best = min(best, float(-sd.max()) / MM)
            if not attached and best > tc2["leg_gap_mm_max"]:
                floating.append(f"{g}[{i}] gap {best:.3f} mm")
    T.add("C.2", "floating parts (structural groups)", len(floating),
          f"<= {tc2['floating_parts_max']}", len(floating) <= int(tc2["floating_parts_max"]),
          note=("; ".join(floating) if floating
                else f"{sum(len(gm[g].split(only_watertight=False)) for g in struct)} components"))
    #  buried plastic
    import mesh_buried
    import drones as _d
    cen = mesh_buried.buried_census(frame_mesh, name="rev1")
    #  The threshold is buried **plastic** as a share of the plastic (shell) area: the internal
    #  metal is meant to be buried, and counting it would make the check meaningless.
    plastic = [g for g, row in cen["by_group"].items()
               if _d.DRONE_GROUP_MAT.get(g, ("?",))[0] in ("plastic", "prop_plastic")]
    a_tot = sum(cen["by_group"][g]["area_mm2"] for g in plastic)
    a_bur = sum(cen["by_group"][g]["buried_area_mm2"] for g in plastic)
    frac = 100.0 * a_bur / max(a_tot, 1e-30)
    cen = {k: v for k, v in cen.items() if k in ("name", "n_faces", "total_area_mm2",
                                                 "buried_pct", "buried_area_mm2",
                                                 "defect_area_mm2", "by_group")}
    T.add("C.2", "buried plastic area", frac, f"<= {tc2['buried_plastic_pct_of_shell_area_max']} %",
          frac <= tc2["buried_plastic_pct_of_shell_area_max"])
    return cen


def _whole(gm):
    Vs, Fs, off = [], [], 0
    for m in gm.values():
        Vs.append(np.asarray(m.vertices))
        Fs.append(np.asarray(m.faces) + off)
        off += len(m.vertices)
    return _tri(np.vstack(Vs), np.vstack(Fs))


def c2b_prop_seating(T, spec, thr, gm, prop_area_mm2, rev0_bell_mm2):
    import drones
    lo, hi = thr["C2_attachment"]["C2b_prop_seating_gap_mm"]
    prop = drones.build_propeller(spec)
    pm = _tri(np.asarray(prop.v, float), np.asarray(prop.f))
    Vp = np.asarray(prop.v, float)
    #  The seat is the hub's underside, not the blade root: drone_cad._prop_hub is the revolve
    #  within r <= 0.085 R, and the aerofoil twist carries the blade root below it on purpose.
    R_m = float(spec.prop_dia_mm) / 2.0 * MM
    #  the blade root starts at root_frac = 0.070 R, so r < 0.065 R is hub only
    in_hub = np.hypot(Vp[:, 0], Vp[:, 1]) <= 0.065 * R_m
    hub_bottom_mm = float(Vp[in_hub, 2].min()) / MM
    blade_bottom_mm = float(Vp[:, 2].min()) / MM
    rl = drones.rotor_layout(spec)
    mount_z = float(np.asarray(gm["motor"].vertices)[:, 2].max()) / MM
    rotor_z = float(rl[0]["center"][2]) / MM
    gap = rotor_z + hub_bottom_mm - mount_z
    T.add("C.2b", "prop hub underside - adapter top", gap, f"in [{lo}, {hi}] mm",
          lo - 1e-6 <= gap <= hi + 1e-6,
          note=f"hub bottom {hub_bottom_mm:+.2f}, blade root {blade_bottom_mm:+.2f} mm in the prop frame")
    #  prop volume that sits inside the motor can
    can = gm["motor"]
    P = sample_mesh(pm, 60000, seed=3) + np.array([[rl[0]["center"][0], rl[0]["center"][1], 0.0]])
    P[:, 2] += rotor_z * MM
    inside = can.contains(P)
    area1 = float(prop_area_mm2) * float(inside.mean())
    T.add("C.2b", "prop area inside the bell", area1, f"<= rev0 {rev0_bell_mm2:.1f} mm^2",
          area1 <= rev0_bell_mm2 + 1e-6)
    return dict(area_mm2=round(area1, 2), frac=round(float(inside.mean()), 5),
                rev0_area_mm2=round(rev0_bell_mm2, 2))


def c2c_swept_disc(T, spec, thr, gm):
    """Plan C.2c. The swept blade volume is **radius dependent**: a two-blade propeller reaches
    its lowest point at the root and its highest near mid span, so one global z band over the
    whole disc reports intrusions that no blade can ever reach. z_lo(r) and z_hi(r) are read off
    the propeller itself in 2 mm radial bins."""
    import drones
    tol = float(thr["C2_attachment"]["C2c_swept_disc_frame_clearance_mm"])
    prop = drones.build_propeller(spec)
    Vp = np.asarray(prop.v, float)
    rad = np.hypot(Vp[:, 0], Vp[:, 1])
    R = float(rad.max())
    r_in = 0.085 * float(spec.prop_dia_mm) / 2.0 * MM * 1.02
    edges = np.arange(0.0, R + 0.002, 0.002)
    lo = np.full(len(edges) - 1, np.nan)
    hi = np.full(len(edges) - 1, np.nan)
    idx = np.clip(np.digitize(rad, edges) - 1, 0, len(edges) - 2)
    for k in range(len(edges) - 1):
        m = idx == k
        if m.any():
            lo[k] = Vp[m, 2].min()
            hi[k] = Vp[m, 2].max()
    ok = ~np.isnan(lo)
    rl = drones.rotor_layout(spec)
    worst = 0.0
    n_in = 0
    for rot in rl:
        cx, cy, cz = rot["center"]
        for g, m in gm.items():
            if g == "prop":
                continue
            V = np.asarray(m.vertices)
            rr = np.hypot(V[:, 0] - cx, V[:, 1] - cy)
            k = np.clip(np.digitize(rr, edges) - 1, 0, len(edges) - 2)
            good = ok[k] & (rr < R) & (rr > r_in)
            #  a rotor's own motor stack is under its own propeller by construction; how far the
            #  blade root reaches into that bell is C.2b's business, not a disc clearance
            good &= rr >= 0.030
            inside = good & (V[:, 2] > cz + lo[k]) & (V[:, 2] < cz + hi[k])
            if inside.any():
                n_in += int(inside.sum())
                depth = np.minimum(V[inside, 2] - (cz + lo[k][inside]),
                                   (cz + hi[k][inside]) - V[inside, 2])
                worst = min(worst, -float(depth.max()) / MM)
    T.add("C.2c", "frame inside a swept disc", worst,
          f">= -{tol} mm (none inside, own motor stack excluded)", worst >= -tol,
          note=f"{n_in} vertices inside")
    C = np.array([r["center"][:2] for r in rl])
    d = float(np.linalg.norm(C[0] - C[1])) / MM
    clr = d - float(spec.prop_dia_mm)
    T.add("C.2c", "neighbour disc clearance", clr, "> 0 mm (sign unchanged)", clr > 0)
    return dict(worst_mm=round(worst, 4), n_inside=n_in)


# --------------------------------------------------------------------------- #
#  C.3 dimensions
# --------------------------------------------------------------------------- #
def c3_dimensions(T, spec, gm, thr, meas):
    sc = thr["C3_dimensions"]["scored"]
    ex = thr["C3_dimensions"]["exact"]
    for key, got in meas.items():
        if key not in sc:
            continue
        row = sc[key]
        if isinstance(row, dict) and "target" in row:
            tol = float(row["tol"])
            T.add("C.3", key, got, f"{row['target']} +- {tol}",
                  abs(got - float(row["target"])) <= tol, note=row.get("source", ""))
        elif isinstance(row, dict) and "min" in row:
            T.add("C.3", key, got, f"[{row['min']}, {row['max']}]",
                  row["min"] <= got <= row["max"], note=row.get("source", ""))
        elif isinstance(row, (int, float)):
            T.add("C.3", key, got, f"<= {row}", got <= float(row))
    import drones
    fs = drones.frame_fit_scale(spec)
    T.add("C.3", "frame_fit_scale", list(np.round(fs, 12)), str(ex["frame_fit_scale"]),
          all(abs(float(a) - float(b)) < 1e-12 for a, b in zip(fs, ex["frame_fit_scale"])))
    env = drones.frame_envelope_mm(spec)
    T.add("C.3", "wheelbase", float(env["wheelbase_opposite_mm"]), f"{ex['wheelbase_mm']} mm",
          abs(float(env["wheelbase_opposite_mm"]) - ex["wheelbase_mm"]) < 1e-6)
    for f in ("prop_dia_mm", "prop_blades", "num_rotors"):
        T.add("C.3", f, getattr(spec, f), ex[f], float(getattr(spec, f)) == float(ex[f]))
    rev0 = drones.DRONES[spec.key]
    C1 = np.array([r["center"][:2] for r in drones.rotor_layout(spec)])
    C0 = np.array([r["center"][:2] for r in drones.rotor_layout(rev0)])
    dxy = float(np.abs(C1 - C0).max()) / MM
    T.add("C.3", "rotor xy vs revision 0", dxy, f"<= {ex['rotor_xy_max_abs_diff_mm_vs_rev0']} mm",
          dxy <= float(ex["rotor_xy_max_abs_diff_mm_vs_rev0"]))
    for key, row in thr["C3_dimensions"]["report_only"].items():
        if key in meas:
            T.add("C.3", key + " (report-only)", meas[key],
                  f"{row['target']} +- {row['tol']} (not scored)", None, note=row["why_report_only"][:60])


# --------------------------------------------------------------------------- #
#  measurement of the built frame
# --------------------------------------------------------------------------- #
def measure_frame(spec, gm, parts, full_drone):
    import drones
    V = np.vstack([np.asarray(m.vertices) for m in gm.values()]) / MM
    body = np.asarray(gm["body"].vertices) / MM
    out = {}
    out["frame_height_props_off_mm"] = float(V[:, 2].max() - V[:, 2].min())
    r = np.hypot(body[:, 0], body[:, 1])
    out["crown_z_mm"] = float(body[r < 50, 2].max())
    out["feet_z_mm"] = float(V[:, 2].min())
    Pb = sample_mesh(gm["body"], 400000, seed=11) / MM
    sl = np.abs(Pb[:, 0]) < 1.5
    out["belly_z_at_x0_mm"] = float(Pb[sl, 2].min())
    sl2 = sl & (Pb[:, 2] > -45) & (Pb[:, 2] < 60) & (np.abs(Pb[:, 1]) < 120)
    out["waist_width_at_x0_mm"] = float(Pb[sl2, 1].max() - Pb[sl2, 1].min())
    for r0, tag in ((120.0, "r120"), (140.0, "r140")):
        ws, hs = [], []
        for ang in (45, 135, 225, 315):
            a = np.radians(ang)
            ua = np.array([np.cos(a), np.sin(a)])
            ub = np.array([-np.sin(a), np.cos(a)])
            sv = Pb[:, :2] @ ua
            tv = Pb[:, :2] @ ub
            s = (np.abs(sv - r0) < 1.5) & (np.abs(tv) < 26) & (Pb[:, 2] > -45)
            if s.sum() < 20:
                continue
            ws.append(float(tv[s].max() - tv[s].min()))
            hs.append(float(Pb[s, 2].max() - Pb[s, 2].min()))
        out[f"arm_section_at_{tag}_w_mm"] = float(np.mean(ws))
        out[f"arm_section_at_{tag}_h_mm"] = float(np.mean(hs))
    mot = sample_mesh(gm["motor"], 300000, seed=19) / MM
    c = np.array([123.7436867076458, 123.7436867076458])
    rr = np.hypot(mot[:, 0] - c[0], mot[:, 1] - c[1])
    near = rr < 30
    out["motor_top_z_mm"] = float(mot[near, 2].max())
    wall = near & (mot[:, 2] > 2.0) & (mot[:, 2] < out["motor_top_z_mm"] - 4.0)
    out["motor_can_diameter_mm"] = 2.0 * float(np.quantile(rr[wall], 0.999))
    r_can = 0.5 * out["motor_can_diameter_mm"]
    onwall = near & (rr > r_can - 0.35) & (rr < r_can + 0.35)
    out["motor_can_straight_wall_mm"] = float(mot[onwall, 2].max() - mot[onwall, 2].min())
    #  same rule as the scan's radial profile: r50 of the points within 35 mm of the rotor axis
    pod = sample_mesh(gm["body"], 600000, seed=23) / MM
    dp = np.hypot(pod[:, 0] - c[0], pod[:, 1] - c[1])
    sel = (dp < 35) & (np.abs(pod[:, 2] + 5.0) < 1.0)
    out["motor_pod_diameter_mm"] = 2.0 * float(np.median(dp[sel]))
    gear = sample_mesh(gm["gear"], 300000, seed=13) / MM
    s = (np.abs(gear[:, 2] + 80) < 1.2) & (gear[:, 0] > 25) & (gear[:, 1] > 40)
    out["leg_centre_x_at_z80_mm"] = float(0.5 * (gear[s, 0].min() + gear[s, 0].max()))
    out["leg_root_section_w_mm"] = float(gear[s, 0].max() - gear[s, 0].min())
    out["leg_root_section_h_mm"] = float(gear[s, 1].max() - gear[s, 1].min())
    s = (np.abs(gear[:, 2] + 110) < 1.2) & (gear[:, 0] > 25) & (gear[:, 1] > 40)
    out["leg_tip_section_w_mm"] = float(gear[s, 0].max() - gear[s, 0].min())
    out["leg_tip_section_h_mm"] = float(gear[s, 1].max() - gear[s, 1].min())
    gimbal = [p for p in parts if p.plan_item == "P7"]
    if gimbal:
        Vg = np.vstack([np.asarray(p.mesh.vertices) for p in gimbal]) / MM
        out["camera_x_min_mm"] = float(Vg[:, 0].min())
        out["camera_x_max_mm"] = float(Vg[:, 0].max())
        out["camera_bottom_above_feet_mm"] = float(Vg[:, 2].min() - V[:, 2].min())
        #  the mesh that exists in the frame is the union of the camera group; the gimbal is its
        #  lowest-hanging connected piece. Sampling the pre-union parts would count the faces the
        #  union removes where the three blocks overlap each other.
        comps = gm["camera"].split(only_watertight=False)
        gim = min(comps, key=lambda c: float(np.asarray(c.vertices)[:, 2].min()))
        Pg = sample_mesh(gim, 200000, seed=17)
        out["camera_buried_pct_max"] = 100.0 * float(gm["body"].contains(Pg).mean())
    full = np.asarray(full_drone.v, float) / MM
    out["height_props_included_mm"] = float(full[:, 2].max() - full[:, 2].min())
    return out


# --------------------------------------------------------------------------- #
#  C.4 reference distance and silhouettes (against the owned scan)
# --------------------------------------------------------------------------- #
def c4_reference(T, gm, thr, ledger):
    from scipy.spatial import cKDTree
    t = thr["C4_reference_distance"]
    Ps = np.load(f"{SCAN_DIR}/p4_datum_scan_samples.npy").astype(float)
    Ns = np.load(f"{SCAN_DIR}/p4_datum_scan_normals.npy").astype(float)
    use = [g for g in ("body", "canopy", "gear", "motor") if g in gm]
    Vs, Fs, lab, off = [], [], [], 0
    for g in use:
        m = gm[g]
        Vs.append(np.asarray(m.vertices))
        Fs.append(np.asarray(m.faces) + off)
        off += len(m.vertices)
        lab += [g] * len(m.faces)
    whole = _tri(np.vstack(Vs), np.vstack(Fs))
    lab = np.array(lab)
    Po, _, fi = _sample_with_faces(whole, 400000, seed=9)
    treeS = cKDTree(Ps)
    d1, j1 = treeS.query(Po)
    sgn1 = np.sign(np.einsum("ij,ij->i", Po - Ps[j1], Ns[j1]))
    treeO = cKDTree(Po)
    d2, j2 = treeO.query(Ps)
    med1 = float(np.median(np.abs(d1))) / MM
    med2 = float(np.median(np.abs(d2))) / MM
    cham = float(0.5 * (d1.mean() + d2.mean())) / MM
    T.add("C.4", "ours -> scan median", med1, f"<= {t['ours_to_scan_median_mm_max']} mm",
          med1 <= t["ours_to_scan_median_mm_max"],
          note=f"rev0 {t['rev0_baseline']['ours_to_scan_median_mm']}")
    T.add("C.4", "scan -> ours median", med2, f"<= {t['scan_to_ours_median_mm_max']} mm",
          med2 <= t["scan_to_ours_median_mm_max"],
          note=f"rev0 {t['rev0_baseline']['scan_to_ours_median_mm']}")
    T.add("C.4", "chamfer mean", cham, f"<= {t['chamfer_mean_mm_max']} mm",
          cham <= t["chamfer_mean_mm_max"], note=f"rev0 {t['rev0_baseline']['chamfer_mean_mm']}")
    #  by region, with the revision-0 labels
    reg = _region(Po)
    g_o = lab[fi]
    lab_o = np.where(np.isin(g_o, ["motor", "gear", "canopy"]), g_o, reg)
    base = t["rev0_baseline"]["by_part_ours_to_scan_median_mm"]
    worst = []
    for k in sorted(set(lab_o.tolist())):
        if k not in base:
            continue
        v = float(np.median(np.abs(d1[lab_o == k]))) / MM
        ok = v <= base[k] + t["region_no_worse_margin_mm"]
        worst.append((k, v, base[k], ok))
        T.add("C.4", f"region {k}", v, f"<= rev0 {base[k]} + {t['region_no_worse_margin_mm']}", ok)
    #  silhouettes, scan pixels 0.5 mm as in the revision-0 baseline
    def sil(P, axes, px=0.0005):
        ij = np.floor(P[:, axes] / px).astype(np.int64)
        return len(np.unique(ij[:, 0] * 1000003 + ij[:, 1])) * (px / MM) ** 2
    #  the revision-0 baseline used 3e6 samples for ours against the scan's 2e6; a 0.5 mm pixel
    #  grid is sampling-limited, so the same count has to be used or the ratio is not comparable
    Po_sil = _sample_with_faces(whole, 3_000_000, seed=9)[0]
    for name, ax, key in (("top_xy", [0, 1], "silhouette_ratio_top_xy"),
                          ("front_yz", [1, 2], "silhouette_ratio_front_yz"),
                          ("side_xz", [0, 2], "silhouette_ratio_side_xz")):
        a_o = sil(Po_sil, ax)
        a_s = sil(Ps, ax)
        ratio = a_o / a_s
        lo, hi = t[key]
        T.add("C.4", f"silhouette {name} ours/scan", ratio, f"[{lo}, {hi}]", lo <= ratio <= hi,
              note=f"rev0 {t['rev0_baseline']['silhouette_ours_over_scan'][name]}")
        ledger.setdefault("silhouette_mm2", {})[name] = dict(ours=round(a_o, 1),
                                                             scan=round(a_s, 1),
                                                             ratio=round(ratio, 4))
    ledger["c4_regions"] = [dict(region=k, rev1=round(v, 3), rev0=b, ok=o) for k, v, b, o in worst]
    ledger["c4"] = dict(ours_to_scan_median_mm=round(med1, 3),
                        scan_to_ours_median_mm=round(med2, 3), chamfer_mean_mm=round(cham, 3))


def _sample_with_faces(m, n, seed=0):
    rng = np.random.default_rng(seed)
    V = np.asarray(m.vertices)
    F = np.asarray(m.faces)
    A = V[F[:, 1]] - V[F[:, 0]]
    B = V[F[:, 2]] - V[F[:, 0]]
    area = 0.5 * np.linalg.norm(np.cross(A, B), axis=1)
    cdf = np.cumsum(area)
    cdf /= cdf[-1]
    k = np.searchsorted(cdf, rng.random(n))
    r1 = np.sqrt(rng.random(n))
    r2 = rng.random(n)
    FF = F[k]
    P = (V[FF[:, 0]] * (1 - r1)[:, None] + V[FF[:, 1]] * (r1 * (1 - r2))[:, None]
         + V[FF[:, 2]] * (r1 * r2)[:, None])
    return P, None, k


def _region(P):
    rxy = np.hypot(P[:, 0], P[:, 1])
    u = np.array([[1, 1], [-1, 1]]) / np.sqrt(2)
    dist_axis = np.min(np.abs(np.stack([P[:, :2] @ np.array([-u[k, 1], u[k, 0]])
                                        for k in range(2)], 1)), 1)
    out = np.full(len(P), "shell_other", dtype=object)
    out[(rxy < 0.085)] = "shell_core_r<85"
    out[(rxy >= 0.085) & (rxy < 0.150) & (dist_axis < 0.040)] = "arm_r85-150"
    out[(rxy >= 0.150) & (dist_axis < 0.040)] = "arm_tip_r>150"
    return out


# --------------------------------------------------------------------------- #
#  C.5 facing area · C.6 facets · C.7 props · C.8 kinematics
# --------------------------------------------------------------------------- #
def _visible_area_mm2(gm, group, u, px_mm=0.5):
    """Area of `group` that a viewer along -u actually sees, with the rest of the frame in the
    way. A parallel ray grid is cast from outside the bounding sphere; a pixel counts when the
    FIRST surface it meets belongs to `group`. This is what plan C.5 means by 'visible'."""
    Vs, Fs, lab, off = [], [], [], 0
    for g, m in gm.items():
        Vs.append(np.asarray(m.vertices))
        Fs.append(np.asarray(m.faces) + off)
        off += len(m.vertices)
        lab += [g] * len(m.faces)
    whole = _tri(np.vstack(Vs), np.vstack(Fs))
    lab = np.array(lab)
    u = np.asarray(u, float)
    u = u / np.linalg.norm(u)
    #  an orthonormal frame with u as the view axis
    a = np.array([0.0, 0.0, 1.0]) if abs(u[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    e1 = np.cross(u, a)
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(u, e1)
    C = whole.vertices.mean(0)
    R = float(np.linalg.norm(whole.vertices - C, axis=1).max()) * 1.05
    n = int(np.ceil(2 * R / (px_mm * MM)))
    g1, g2 = np.meshgrid(np.linspace(-R, R, n), np.linspace(-R, R, n))
    org = C + u[None, :] * (2 * R) + g1.reshape(-1, 1) * e1[None, :] + g2.reshape(-1, 1) * e2[None, :]
    idx, ray_i, _ = whole.ray.intersects_id(org, np.tile(-u, (len(org), 1)),
                                            multiple_hits=False, return_locations=True)
    if len(ray_i) == 0:
        return 0.0
    cell = (2 * R / (n - 1) / MM) ** 2
    return float((lab[idx] == group).sum()) * cell


def _lowest_component(gm, group):
    """`gm` with `group` reduced to its lowest-hanging connected piece (the gimbal)."""
    comps = gm[group].split(only_watertight=False)
    pick = min(comps, key=lambda c: float(np.asarray(c.vertices)[:, 2].min()))
    out = dict(gm)
    out[group] = pick
    return out


def c5_facing(T, gm, gm0, thr):
    t = thr["C5_facing_area"]
    for el in t["camera_visible_area_must_increase_at_el_deg"]:
        import mesh_symmetry as ms
        u = ms.view_dir(t["az_deg"], float(el))
        a1 = _visible_area_mm2(gm, "camera", u)
        a0 = _visible_area_mm2(gm0, "camera", u)
        T.add("C.5", f"camera visible area el {el:+.0f}", a1, f"> rev0 {a0:.1f} mm^2", a1 > a0)
        #  diagnostic (not scored): the gimbal assembly alone, i.e. the connected piece of the
        #  camera group that hangs lowest. P4-6 removes six other members of the same group in
        #  the same revision, so the group-level row above cannot isolate what P4-3 changed.
        g1 = _visible_area_mm2(_lowest_component(gm, "camera"), "camera", u)
        g0 = _visible_area_mm2(_lowest_component(gm0, "camera"), "camera", u)
        T.add("C.5", f"gimbal-only visible area el {el:+.0f} (diagnostic)", g1,
              f"rev0 {g0:.1f} mm^2", None)


def c6_facets(T, gm, thr, n_faces, prop_faces):
    import mesh_topo_check as tc
    t = thr["C6_facets"]
    worst = 0.0
    for g, m in gm.items():
        fw = tc.facet_wavelength(np.asarray(m.vertices), np.asarray(m.faces), 51.69e-3)
        worst = max(worst, float(fw["max_sagitta_mm"]))
    T.add("C.6", "sagitta, worst group", worst, f"<= {t['sagitta_mm_max']} mm",
          worst <= t["sagitta_mm_max"])
    T.add("C.6", "frame faces", n_faces, f"<= {t['frame_faces_max']}",
          n_faces <= t["frame_faces_max"])
    T.add("C.6", "prop faces per rotor", prop_faces, f"<= {t['prop_faces_per_rotor_max']}",
          prop_faces <= t["prop_faces_per_rotor_max"])


def c7_props(T, spec, thr, ledger):
    import drone_parts_rev1 as P
    import drones
    import mesh_check
    t = thr["C7_props"]
    rev0 = drones.DRONES[spec.key]
    rows = []
    for mirror, spin in ((False, +1), (True, -1)):
        tag = "CW" if mirror else "CCW"
        m1 = _tri(*_vf(drones.build_propeller(spec, mirror=mirror)))
        m0 = _tri(*_vf(drones.build_propeller(rev0, mirror=mirror)))
        for rr in t["r_over_R_stations"]:
            o1 = P.blade_orientation(m1, spin, int(spec.prop_blades), r_over_R=float(rr))
            o0 = P.blade_orientation(m0, spin, int(rev0.prop_blades), r_over_R=float(rr))
            T.add("C.7", f"P6 r/R {rr} {tag}", f"{o1['n_ok']}/{o1['n_blades']} blades ok",
                  "all blades", bool(o1["all_ok"]))
            c1 = float(np.mean([b["chord_mm"] for b in o1["blades"]]))
            c0 = float(np.mean([b["chord_mm"] for b in o0["blades"]]))
            T.add("C.7", f"chord r/R {rr} {tag}", c1, f"{c0:.3f} +- {t['chord_tol_mm_vs_rev0']} mm",
                  abs(c1 - c0) <= t["chord_tol_mm_vs_rev0"])
            a1 = float(np.mean([b["angle_inertia_deg"] for b in o1["blades"]]))
            a0 = float(np.mean([b["angle_inertia_deg"] for b in o0["blades"]]))
            T.add("C.7", f"blade angle r/R {rr} {tag}", a1,
                  f"{a0:.3f} +- {t['blade_angle_tol_deg_vs_rev0']} deg",
                  abs(a1 - a0) <= t["blade_angle_tol_deg_vs_rev0"])
            rows.append(dict(mirror=mirror, r_over_R=rr, ok=bool(o1["all_ok"]),
                             chord_rev1=round(c1, 4), chord_rev0=round(c0, 4),
                             angle_rev1=round(a1, 4), angle_rev0=round(a0, 4)))
    h = mesh_check.check_handedness(spec)
    ok = bool(h.get("ok", False))
    T.add("C.7", "check_handedness", ok, "true", ok)
    ledger["c7"] = dict(rows=rows, handedness={k: v for k, v in h.items() if k != "rows"})


def _vf(mesh):
    return np.asarray(mesh.v, float), np.asarray(mesh.f)


def _chord_mm(m, r_over_R, R_mm):
    P = trimesh.sample.sample_surface(m, 200000, seed=5)[0]
    rad = np.hypot(P[:, 0], P[:, 1])
    R = float(rad.max())
    band = np.abs(rad - r_over_R * R) < 0.002
    if band.sum() < 50:
        return float("nan")
    Q = P[band]
    th = np.arctan2(Q[:, 1], Q[:, 0])
    th = np.sort(th)
    gaps = np.diff(np.r_[th, th[0] + 2 * np.pi])
    start = int(np.argmax(gaps))
    blade = np.sort(th)[: start + 1]
    span = float(blade.max() - blade.min())
    return span * r_over_R * R / MM


def c8_kinematics(T, spec, thr):
    import drones
    from articulated_fast import FastPoser
    t = thr["C8_kinematics"]
    rl = drones.rotor_layout(spec)
    dirs = [int(r["dir"]) for r in rl]
    T.add("C.8", "rotor_dirs", dirs, str(t["rotor_dirs"]), dirs == list(t["rotor_dirs"]))
    ang = [float(r["base_ang"]) for r in rl]
    T.add("C.8", "base_ang", ang, str(t["base_ang_deg"]),
          all(abs(a - b) < 1e-9 for a, b in zip(ang, t["base_ang_deg"])))
    fp = FastPoser(spec)
    v = fp.verify()
    err = float(v["max_abs_vertex_diff_m"])
    T.add("C.8", "FastPoser.verify", err, f"<= {t['fastposer_verify_max']}",
          err <= float(t["fastposer_verify_max"]))
    for f in ("prop_dia_mm", "prop_blades", "num_rotors", "hover_rpm"):
        T.add("C.8", f, getattr(spec, f), t[f], float(getattr(spec, f)) == float(t[f]))
    return fp


# --------------------------------------------------------------------------- #
#  C.11 certificates · C.12 materials · C.13 canonical repairs
# --------------------------------------------------------------------------- #
def c11_certificates(T, gm, thr, ledger, frame_mesh, frame_mesh0):
    import mesh_symmetry as ms
    import mesh_placement as mp
    t = thr["C11_certificates"]
    whole = _whole(gm)
    V = np.asarray(whole.vertices)
    F = np.asarray(whole.faces)
    Vm = V.copy()
    Vm[:, 1] *= -1.0
    Fm = F[:, ::-1]
    a0 = float(_tri(V, F).area)
    am = float(_tri(Vm, Fm).area)
    rel = abs(a0 - am) / max(a0, 1e-30)
    T.add("C.11", "mirror-symmetry area", rel, f"<= {t['symmetry_area_rel_tol']}",
          rel <= float(t["symmetry_area_rel_tol"]))
    com = _tri(V, F).center_mass / MM
    T.add("C.11", "centre of mass |y|", abs(float(com[1])), f"<= {t['symmetry_com_abs_tol_mm']} mm",
          abs(float(com[1])) <= float(t["symmetry_com_abs_tol_mm"]))
    try:
        cen = mp.placement_census(frame_mesh, name="rev1")
        cen0 = mp.placement_census(frame_mesh0, name="rev0")
        a1 = float(cen["crossing"]["area_pct"])
        a0 = float(cen0["crossing"]["area_pct"])
        T.add("C.11", "mesh_placement crossing area", a1, f"<= rev0 budget {a0:.4g} %", a1 <= a0,
              note=f"pairs rev1 {cen['crossing']['n_pairs']} vs rev0 {cen0['crossing']['n_pairs']}")
        n_self = int(cen["self_intersection"]["n_pairs"])
        n_self0 = int(cen0["self_intersection"]["n_pairs"])
        T.add("C.11", "mesh_placement self-intersecting pairs", n_self,
              f"<= rev0 {n_self0}", n_self <= n_self0)
        ledger["c11_placement_rev0"] = dict(crossing=cen0["crossing"],
                                            self_intersection={k: cen0["self_intersection"][k]
                                                               for k in ("n_parts", "n_pairs", "area_mm2")})
        ledger["c11_placement"] = dict(relations=cen["relations"], crossing=cen["crossing"],
                                       self_intersection={k: cen["self_intersection"][k]
                                                          for k in ("n_parts", "n_pairs", "area_mm2")})
    except Exception as exc:
        T.add("C.11", "mesh_placement", f"error: {type(exc).__name__}", "runs", None)


def c12_materials(T, gm, gm0, ledger):
    import drones
    rows = []
    for g in sorted(set(list(gm) + list(gm0))):
        m1 = gm.get(g)
        m0 = gm0.get(g)
        rows.append(dict(group=g, material=drones.DRONE_GROUP_MAT.get(g, ("?",))[0],
                         area_mm2_rev1=round(float(m1.area) / MM ** 2, 1) if m1 else 0.0,
                         area_mm2_rev0=round(float(m0.area) / MM ** 2, 1) if m0 else 0.0,
                         vol_mm3_rev1=round(float(m1.volume) / MM ** 3, 1) if m1 else 0.0,
                         vol_mm3_rev0=round(float(m0.volume) / MM ** 3, 1) if m0 else 0.0))
    ledger["c12_materials"] = rows
    T.add("C.12", "material table", f"{len(rows)} groups", "report", None)


def c13_repairs(T, gm, thr):
    t = thr["C13_canonical_repairs"]
    T.add("C.13", "body closed", bool(gm["body"].is_watertight), "true", gm["body"].is_watertight)
    if "battery" in gm:
        n = int(len(gm["battery"].split(only_watertight=False)))
        T.add("C.13", "battery one piece", n, "1", n == 1)
    if "battery" in gm and "pcb" in gm:
        P = sample_mesh(gm["pcb"], 60000, seed=21)
        f = 100.0 * float(gm["battery"].contains(P).mean())
        T.add("C.13", "battery/pcb interpenetration", f,
              f"<= {t['battery_pcb_interpenetration_pct_max']} %",
              f <= float(t["battery_pcb_interpenetration_pct_max"]))


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drone", required=True)
    ap.add_argument("--rev", type=int, default=1)
    ap.add_argument("--out", default=None)
    ap.add_argument("--thresholds", default=None)
    a = ap.parse_args()

    import drones
    import drone_cad
    import mesh_rev

    thr_path = a.thresholds or os.path.join(ROOT, "docs", "mesh_rev1",
                                            f"{a.drone}_acceptance_thresholds.json")
    thr = json.load(open(thr_path))
    thr_sha = hashlib.sha256(open(thr_path, "rb").read()).hexdigest()

    t0 = time.time()
    spec = drones.spec_for(a.drone, a.rev)
    rev0 = drones.DRONES[a.drone]
    A = drone_cad.build_frame_cad(spec)
    parts = list(getattr(A, "rev1_parts", []))
    frame1 = drones.build_frame(spec)
    frame0 = drones.build_frame(rev0)
    full1 = drones.build_drone(spec)
    gm = groups_of(frame1)
    gm0 = groups_of(frame0)
    prop1 = drones.build_propeller(spec)

    T = Table()
    ledger = dict(drone=a.drone, rev=a.rev, thresholds_sha256=thr_sha,
                  thresholds_path=os.path.abspath(thr_path),
                  utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    c1_topology(T, gm, thr, gm0)
    ledger["buried"] = c2_attachment(T, parts, gm, thr, spec, gm0, frame1)
    prop0 = drones.build_propeller(rev0)
    pa1 = float(_tri(np.asarray(prop1.v, float), np.asarray(prop1.f)).area) / MM ** 2
    m0 = _tri(np.asarray(prop0.v, float), np.asarray(prop0.f))
    rl0 = drones.rotor_layout(rev0)
    P0 = sample_mesh(m0, 60000, seed=3) + np.array([[rl0[0]["center"][0], rl0[0]["center"][1],
                                                     rl0[0]["center"][2]]])
    bell0 = float(m0.area) / MM ** 2 * float(gm0["motor"].contains(P0).mean())
    ledger["prop_seating"] = c2b_prop_seating(T, spec, thr, gm, pa1, bell0)
    ledger["swept_disc"] = c2c_swept_disc(T, spec, thr, gm)
    meas = measure_frame(spec, gm, parts, full1)
    ledger["measured"] = {k: round(float(v), 4) for k, v in meas.items()}
    c3_dimensions(T, spec, gm, thr, meas)
    c4_reference(T, gm, thr, ledger)
    c5_facing(T, gm, gm0, thr)
    c6_facets(T, gm, thr, int(len(np.asarray(frame1.f))), int(len(np.asarray(prop1.f))))
    c7_props(T, spec, thr, ledger)
    fp = c8_kinematics(T, spec, thr)
    T.add("C.9", "specular census", "see pre-registration", "report", None)
    T.add("C.10", "visual review", "render sheet + notes", "report", None)
    c11_certificates(T, gm, thr, ledger, frame1, frame0)
    c12_materials(T, gm, gm0, ledger)
    c13_repairs(T, gm, thr)

    ledger["fingerprint"] = mesh_rev.fingerprint_poser(fp)
    txt, n_bad = T.report()
    print(txt)
    print(f"\nfingerprint(FastPoser({a.drone}, rev {a.rev})) = {ledger['fingerprint']}")
    print(f"thresholds sha256 = {thr_sha}")
    print(f"elapsed {time.time() - t0:.1f} s")
    ledger["rows"] = T.rows
    ledger["n_fail"] = n_bad
    if a.out:
        json.dump(ledger, open(a.out, "w"), indent=1, default=str)
        print(f"ledger -> {a.out}")
    return 1 if n_bad else 0


if __name__ == "__main__":
    sys.exit(main())
