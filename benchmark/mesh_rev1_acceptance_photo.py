# -*- coding: utf-8 -*-
"""mesh_rev1_acceptance.py — geometry acceptance for a mesh revision (plan C.1–C.13).

Usage
    python benchmark/mesh_rev1_acceptance.py --drone mini5pro [--rev 1]
        [--variant fcc_height] [--out <ledger.json>] [--thresholds <file.json>]

It builds revision 0 and the revision under test with the canonical mesh switches, runs plan
C.1–C.13 against the frozen threshold file `docs/mesh_rev1/<key>_acceptance_thresholds.json`, and
prints one pass/fail row per check. The JSON ledger goes wherever `--out` says (scratch).

⛔ The thresholds are read, never written. A row whose threshold is missing is reported as
   "no threshold" and fails, so a check can never pass by omission.
⛔ CPU only. Nothing here touches queues, shards or the live repository.
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

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (os.path.join(_ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

PLASTIC_GROUPS = ("body", "canopy", "gear", "accent")
METAL_GROUPS = ("motor", "battery")


def _work_dir(key: str, need: str) -> str | None:
    """MERGE FIX 2026-09-18 — find the scratch helper `need` (e.g. "top_iou.py") for `key`.

    ⚠ Why this is per drone. `work/top_iou.py` is NOT part of the installable tree, and mini5pro
    and mavic4pro each delivered their OWN `top_iou.py` with a different registration and a
    different `frame_mask_for` signature. Both deliveries resolved it as `<parent>/work`, which
    is one directory for both aircraft once the two builders live in one tree: whichever module
    landed there would silently score the other drone against the wrong photo and the wrong
    transform, and the row would still print a number. The per-key directory is searched first,
    and `MESHREV1_WORK` still overrides everything for a one-off run.
    """
    _parent = os.path.dirname(_ROOT)
    for cand in (os.environ.get("MESHREV1_WORK", ""),
                 os.path.join(_parent, "work", key),
                 os.path.join(_parent, "work"),
                 os.path.join(_parent, "fix")):
        if cand and os.path.isfile(os.path.join(cand, need)):
            return cand
    return None


# --------------------------------------------------------------------------- #
#  small helpers
# --------------------------------------------------------------------------- #
class Table:
    def __init__(self):
        self.rows = []

    def add(self, check, what, got, want, ok, mode="gate", note=""):
        self.rows.append(dict(check=check, what=what, got=got, want=want,
                              ok=(None if mode == "report" else bool(ok)),
                              mode=mode, note=note))

    def gate_ok(self):
        return all(r["ok"] for r in self.rows if r["mode"] == "gate")

    def render(self):
        w = max(len(r["what"]) for r in self.rows) + 1
        out = [f"{'check':<5} {'what':<{w}} {'got':<34} {'want':<30} verdict",
               "-" * (5 + w + 34 + 30 + 10)]
        for r in self.rows:
            v = "REPORT" if r["mode"] == "report" else ("PASS" if r["ok"] else "**FAIL**")
            out.append(f"{r['check']:<5} {r['what']:<{w}} {str(r['got'])[:33]:<34} "
                       f"{str(r['want'])[:29]:<30} {v}")
            if r["note"]:
                out.append(f"      {'':<{w}} {r['note']}")
        return "\n".join(out)


def _mesh_of(m):
    """geom.Mesh → trimesh."""
    return trimesh.Trimesh(vertices=np.asarray(m.v, float), faces=np.asarray(m.f, int),
                           process=False)


def _group_meshes(gm):
    """geom.Mesh → {group: trimesh} (one concatenated mesh per group)."""
    V = np.asarray(gm.v, float)
    F = np.asarray(gm.f, int)
    G = np.asarray(gm.g)
    out = {}
    for g in sorted(set(G.tolist())):
        f = F[G == g]
        used = np.unique(f)
        remap = -np.ones(V.shape[0], np.int64)
        remap[used] = np.arange(len(used))
        out[g] = trimesh.Trimesh(vertices=V[used], faces=remap[f], process=False)
    return out


def _inside(solid, pts_m):
    try:
        return np.asarray(solid.contains(pts_m), bool)
    except Exception:
        return np.zeros(len(pts_m), bool)


# --------------------------------------------------------------------------- #
#  checks
# --------------------------------------------------------------------------- #
def run(key, rev, thr, variant=None, verbose=True):
    import drones
    from drones import DRONES, build_frame, build_propeller, build_drone, rotor_layout, \
        frame_fit_scale, DRONE_GROUP_MAT, motor_radii, motor_angles
    import drone_cad as dc
    import mesh_check
    import mesh_topo_check
    from geom import mesh_fix_set, MESH_FIX_CANON, blade_law_canon, BLADE_LAW_CANON

    T = Table()
    led = dict(key=key, rev=rev, variant=variant, when=time.strftime("%Y-%m-%d %H:%M:%S %Z"),
               mesh_fix=sorted(mesh_fix_set()), blade_law=blade_law_canon())

    # --- build ------------------------------------------------------------- #
    spec0 = DRONES[key]
    spec1 = drones.spec_for(key, rev)
    G = __import__(f"drone_rev1_{key}")
    if variant:
        G1 = G
        import mesh_rev
        entry = mesh_rev.get_entry(key, rev)
        A1 = __import__("drone_rev").finish_frame_assembly(
            getattr(G1, f"build_frame_ablation_{variant}")(spec1), spec1)
        frame1 = A1.to_geom()
    else:
        A1 = dc.build_frame_cad(spec1)
        frame1 = build_frame(spec1)
    frame0 = build_frame(spec0)
    gm1 = _group_meshes(frame1)
    gm0 = _group_meshes(frame0)
    prop1 = build_propeller(spec1)
    prop0 = build_propeller(spec0)
    drone1 = build_drone(spec1)
    parts_log = getattr(A1, "mesh_rev1_parts", [])
    led["parts"] = parts_log

    # ------------------------------------------------------------------ C.1 --
    t1 = thr["C1_topology"]
    cm = mesh_check.check_mesh(frame1, name=key)
    tp = mesh_topo_check.check_topology(frame1, name=key, self_int=True)
    led["C1"] = dict(check_mesh=cm, topo={k: v for k, v in tp.items() if k != "groups"})
    bad_wt = [g for g, r in cm["groups"].items() if not r["watertight"].startswith(
        str(r["n_parts"]) + "/")]
    T.add("C.1", "every group watertight",
          {g: r["watertight"] for g, r in cm["groups"].items()},
          "all parts watertight", not bad_wt)
    T.add("C.1", "boundary edges",
          sum(r["boundary_edges"] for r in cm["groups"].values()), t1["boundary_edges_max"],
          sum(r["boundary_edges"] for r in cm["groups"].values()) <= t1["boundary_edges_max"])
    T.add("C.1", "non-manifold edges",
          sum(r["nonmanifold_edges"] for r in cm["groups"].values()),
          t1["non_manifold_edges_max"],
          sum(r["nonmanifold_edges"] for r in cm["groups"].values())
          <= t1["non_manifold_edges_max"])
    nsi = int(tp.get("self_intersections", tp.get("n_self_int", 0)) or 0)
    T.add("C.1", "self-intersections", nsi, t1["self_intersections_max"],
          nsi <= t1["self_intersections_max"])
    T.add("C.1", "outward winding / positive volume",
          dict(inward=sum(r["inward_normals"] for r in cm["groups"].values()),
               bad_winding=sum(r["bad_winding"] for r in cm["groups"].values()),
               raw_neg=sum(r["raw_negative_parts"] for r in cm["groups"].values())),
          "0 / 0 / 0",
          all(r["inward_normals"] == 0 and r["bad_winding"] == 0 and r["raw_negative_parts"] == 0
              for r in cm["groups"].values()))
    T.add("C.1", "sliver faces", cm["slivers"], f"<= {t1['sliver_faces_max']}",
          cm["slivers"] <= t1["sliver_faces_max"])
    comps = {g: int(r["n_parts"]) for g, r in cm["groups"].items()}
    want_comps = t1["components_per_group"]
    T.add("C.1", "connected components per group", comps, want_comps,
          all(comps.get(g) == n for g, n in want_comps.items()) and set(comps) == set(want_comps))

    # ------------------------------------------------------------------ C.2 --
    t2 = thr["C2_attachment"]
    shell = gm1["body"]
    #  attachment gaps: every part of every group must touch or overlap the body
    gaps = {}
    for g in ("gear", "motor", "camera"):
        if g not in gm1:
            continue
        for i, c in enumerate(gm1[g].split(only_watertight=False)):
            P = np.asarray(c.vertices, float)
            d = trimesh.proximity.closest_point(shell, P)[1].min() / 1e-3
            # inside the body counts as touching
            if _inside(shell, P).any():
                d = 0.0
            gaps[f"{g}[{i}]"] = round(float(d), 4)
    gap_max = max(gaps.values()) if gaps else 0.0
    T.add("C.2", "leg / motor / gimbal gap to body (mm)", gaps,
          f"<= {t2['leg_gap_mm_max']}", gap_max <= t2["leg_gap_mm_max"])
    T.add("C.2", "floating parts", int(sum(1 for v in gaps.values()
                                           if v > t2["leg_gap_mm_max"])),
          t2["floating_parts_max"],
          sum(1 for v in gaps.values() if v > t2["leg_gap_mm_max"]) <= t2["floating_parts_max"])

    #  internal metal inside the shell, with clearance
    met = {}
    for g in ("battery", "pcb"):
        if g not in gm1:
            continue
        c = gm1[g]
        P = np.asarray(c.vertices, float)
        #  ⚠ BUG FIX (first run): a clipped box has its vertices ON the shell surface, where
        #  `contains` is a coin flip (51.7 % was reported for a box that P8 had already
        #  intersected with the shell). Shrink each vertex 1 % toward the part centroid first.
        ctr = P.mean(axis=0)
        Ps = ctr[None, :] + 0.99 * (P - ctr[None, :])
        ins = _inside(shell, Ps)
        clr = trimesh.proximity.closest_point(shell, P)[1].min() / 1e-3
        met[g] = dict(inside_pct=round(100.0 * float(ins.mean()), 3),
                      clearance_mm=round(float(clr), 3))
    T.add("C.2", "internal metal inside shell (%)",
          {g: v["inside_pct"] for g, v in met.items()},
          f">= {t2['internal_metal_inside_shell_pct_min']}",
          all(v["inside_pct"] >= t2["internal_metal_inside_shell_pct_min"] - 1e-9
              for v in met.values()))
    T.add("C.2", "internal metal clearance (mm)",
          {g: v["clearance_mm"] for g, v in met.items()},
          f">= {t2['internal_metal_clearance_mm_min']}",
          all(v["clearance_mm"] >= t2["internal_metal_clearance_mm_min"] - 1e-6
              for v in met.values()))
    bat = next((p for p in parts_log if p.get("name") == "battery_placement"), None)
    clip = float(bat["info"].get("clipped_volume_pct", 0.0)) if bat else 0.0
    T.add("C.2", "battery clipped volume (%)", round(clip, 3),
          f"<= {t2['battery_clipped_volume_pct_max']}",
          clip <= t2["battery_clipped_volume_pct_max"],
          note=("" if bat is None else f"centre {bat['info'].get('center_mm')}"))

    #  buried plastic, split as the threshold file declares
    def buried_pct(src_groups, dst_groups, ref_area):
        area = 0.0
        for gs in src_groups:
            if gs not in gm1:
                continue
            m = gm1[gs]
            C = m.triangles_center
            for gd in dst_groups:
                if gd == gs or gd not in gm1:
                    continue
                ins = _inside(gm1[gd], C)
                area += float(m.area_faces[ins].sum())
        return 100.0 * area / ref_area if ref_area > 0 else 0.0

    shell_area = float(shell.area)
    bp = buried_pct(PLASTIC_GROUPS, PLASTIC_GROUPS, shell_area)
    bpc = buried_pct(PLASTIC_GROUPS, ("camera",), shell_area)
    gm0_area = float(gm0["body"].area)
    bp0 = 100.0 * sum(
        float(gm0[g].area_faces[_inside(gm0[gd], gm0[g].triangles_center)].sum())
        for g in PLASTIC_GROUPS if g in gm0 for gd in PLASTIC_GROUPS if gd != g and gd in gm0
    ) / gm0_area
    bpc0 = 100.0 * sum(
        float(gm0[g].area_faces[_inside(gm0["camera"], gm0[g].triangles_center)].sum())
        for g in PLASTIC_GROUPS if g in gm0
    ) / gm0_area if "camera" in gm0 else 0.0
    T.add("C.2", "buried plastic in plastic (% of shell area)", round(bp, 3),
          f"<= {t2['buried_plastic_pct_of_shell_area_max']}",
          bp <= t2["buried_plastic_pct_of_shell_area_max"],
          note=f"revision 0: {bp0:.3f} %")
    T.add("C.2", "buried plastic in camera (% of shell area)", round(bpc, 3),
          f"<= revision 0 ({bpc0:.3f})", bpc <= bpc0 + 1e-6,
          note="gimbal recess, see the threshold file's deviation entry")
    try:
        bf = mesh_check.check_buried_faces(spec1, mesh=drone1)
        T.add("C.2", "repo buried-face defect (%)", bf["defect_pct"],
              f"<= {t2['repo_buried_defect_pct_max']}",
              bf["defect_pct"] <= t2["repo_buried_defect_pct_max"])
        led["buried_census"] = bf
    except Exception as e:
        T.add("C.2", "repo buried-face defect (%)", f"error: {type(e).__name__}", "-", False)

    #  C.2b prop seating
    rl1 = rotor_layout(spec1)
    Pv = np.asarray(prop1.v, float) * 1000.0
    hub_bot = float(Pv[:, 2].min())
    stack_tops = []
    for p in parts_log:
        if p.get("plan_item") == "P3" and p.get("info", {}).get("role") == "pod":
            stack_tops.append(p["info"]["adapter_top_z_mm"])
    lo, hi = t2["C2b_prop_seating_gap_mm"]
    #  ⚠ BUG FIX (first run): this row first used the whole propeller's lowest vertex, which is the
    #  blade TIP droop 40 mm out in free air (-3.03 mm), not the hub underside. The hub is the
    #  cylinder of radius 0.085 R around the axis; inside 0.05 R only hub faces exist, so the hub
    #  underside is the minimum z there. The mount plane IS the stack top by construction.
    r_prop = np.hypot(Pv[:, 0], Pv[:, 1])
    hub_core = r_prop <= 0.05 * float(spec1.prop_dia_mm) / 2.0
    hub_bot = float(Pv[hub_core, 2].min())
    seat_gap = float(-hub_bot)
    T.add("C.2b", "prop hub underside to stack top (mm)", round(seat_gap, 4),
          f"in [{lo}, {hi}]", lo - 1e-6 <= seat_gap <= hi + 1e-6,
          note="negative would mean the hub is inside the adapter; blade-root droop into the "
               "adapter is scored by the next row")
    try:
        pb = mesh_check.check_prop_bell_solid(spec1, mesh=drone1)
        T.add("C.2b", "prop area inside the bell (%)", pb.get("inside_pct", pb.get("pct", 0.0)),
              f"<= {t2['C2b_prop_area_inside_bell_pct_max']}",
              float(pb.get("inside_pct", pb.get("pct", 0.0)))
              <= t2["C2b_prop_area_inside_bell_pct_max"] + 1e-9)
        led["prop_bell"] = pb
    except Exception as e:
        T.add("C.2b", "prop area inside the bell (%)", f"error: {type(e).__name__}", "-", False)

    #  C.2c swept-disc clearance
    R = float(spec1.prop_dia_mm) / 2.0
    zlo, zhi = float(Pv[:, 2].min()), float(Pv[:, 2].max())
    marg = float(t2["C2c_disc_margin_mm"])
    Vf = np.asarray(frame1.v, float) * 1000.0
    #  ⚠ BUG FIX (first run): the swept BLADE volume is the annulus outside the motor stack. The
    #  first version used the full disc, so every vertex of a rotor's own can and adapter — which
    #  stand at the disc centre by construction — counted as an intrusion (324 of them).
    r_in = 0.5 * float(getattr(spec1, "motor_dia_mm", 0.0) or 0.0)
    n_in = 0
    for d in rl1:
        cx, cy, cz = (float(v) * 1000.0 for v in d["center"])
        r = np.hypot(Vf[:, 0] - cx, Vf[:, 1] - cy)
        n_in += int(((r >= r_in + marg) & (r <= R + marg) & (Vf[:, 2] >= cz + zlo - marg)
                     & (Vf[:, 2] <= cz + zhi + marg)).sum())
    T.add("C.2c", "frame vertices inside a swept disc", n_in,
          t2["C2c_frame_vertices_in_swept_disc_max"],
          n_in <= t2["C2c_frame_vertices_in_swept_disc_max"])
    rl0 = rotor_layout(spec0)

    def disc_clearances(rl):
        C = np.array([[float(v) * 1000.0 for v in d["center"]] for d in rl])
        return {f"{i}-{j}": round(float(np.hypot(*(C[i, :2] - C[j, :2])) - 2 * R), 4)
                for i in range(len(C)) for j in range(i + 1, len(C))}
    dc0, dc1 = disc_clearances(rl0), disc_clearances(rl1)
    same = all(np.sign(dc0[k]) == np.sign(dc1[k]) for k in dc0)
    T.add("C.2c", "neighbouring-disc clearance sign", dc1, "same sign as revision 0", same)

    # ------------------------------------------------------------------ C.3 --
    t3 = thr["C3_dimensions"]
    fs = frame_fit_scale(spec1)
    T.add("C.3", "frame_fit_scale", [round(v, 12) for v in fs], t3["frame_fit_scale"],
          all(abs(a - b) <= t3["frame_fit_scale_tol"] for a, b in zip(fs, t3["frame_fit_scale"])))
    exy = max(abs(float(a["center"][i]) - float(b["center"][i])) * 1000.0
              for a, b in zip(rl1, rl0) for i in (0, 1))
    T.add("C.3", "rotor xy vs revision 0 (mm)", f"{exy:.3e}",
          f"<= {t3['rotor_xy_max_error_mm']}", exy <= t3["rotor_xy_max_error_mm"])
    ez = max(abs(float(a["center"][2]) - float(b["center"][2])) * 1000.0
             for a, b in zip(rl1, rl0))
    T.add("C.3", "rotor mount z vs revision 0 (mm)", f"{ez:.3e}",
          f"<= {t3['rotor_mount_z_max_error_mm']}", ez <= t3["rotor_mount_z_max_error_mm"],
          note="the M5P-1 decision: revision 1 keeps revision 0's vertical layout")
    unch = t3["unchanged"]
    got_unch = dict(prop_dia_mm=spec1.prop_dia_mm, prop_blades=spec1.prop_blades,
                    num_rotors=spec1.num_rotors, hover_rpm=spec1.hover_rpm)
    _C = np.array([[float(d["center"][i]) * 1000.0 for i in (0, 1)] for d in rl1])
    #  ⚠ BUG FIX (first run): the wheelbase is the distance between OPPOSITE rotors (the trapezoid
    #  diagonal FL-RR), not twice one rotor radius. The first version read 273.46 mm against the
    #  registered 248.3 mm and failed a target revision 1 does not change.
    wb = float(np.hypot(*(_C[0] - _C[2])))
    T.add("C.3", "prop dia / blades / rotors / rpm", got_unch,
          {k: unch[k] for k in got_unch}, all(got_unch[k] == unch[k] for k in got_unch))
    T.add("C.3", "wheelbase (mm)", round(wb, 4),
          f"{unch['wheelbase_mm']} +- {unch['wheelbase_tol_mm']}",
          abs(wb - unch["wheelbase_mm"]) <= unch["wheelbase_tol_mm"] + 0.05,
          note="FL-RR diagonal; revision 0 gives the same value (rotor xy are bit-identical)")

    #  measured geometry of the built mesh
    shellV = np.asarray(shell.vertices, float) * 1000.0
    bodyV = shellV
    meas = {}
    #  the shell alone is the first P1 part; read its realized span from the parts log
    p1 = next((p for p in parts_log if p.get("plan_item") == "P1"), None)
    meas["shell_x_lo"] = round(float(bodyV[:, 0].min()), 3)
    meas["shell_x_hi"] = None
    law, xs0 = G._rev0_section_law()
    st = G._ablation_stations() if variant else G._shell_stations(law, xs0)
    shell_only = __import__("drone_parts_rev1").section_loft_shell(
        st, group="body", name="shell_probe", cap=("dome", "dome"),
        dome_len_mm=G.SHELL_CAP_LEN_MM, sagitta_mm=1.0).mesh
    SV = np.asarray(shell_only.vertices, float) * 1000.0
    meas["shell_x_lo"] = round(float(SV[:, 0].min()), 3)
    meas["shell_x_hi"] = round(float(SV[:, 0].max()), 3)
    Vall = np.asarray(frame1.v, float) * 1000.0
    G_all = np.asarray(frame1.g)
    body_x_hi = float(np.asarray(gm1["body"].vertices)[:, 0].max()) * 1000.0
    meas["outline_x_hi_with_grille"] = round(body_x_hi, 3)
    meas["outline_centre_x"] = round(0.5 * (meas["shell_x_lo"] + body_x_hi), 3)

    def shell_width(x):
        s = shell_only.section(plane_origin=[x * 1e-3, 0, 0], plane_normal=[1, 0, 0])
        if s is None:
            return None
        P = np.asarray(s.vertices, float) * 1000.0
        return round(float(P[:, 1].max() - P[:, 1].min()), 3)
    if key == "mavic4pro":
        #  ---- mavic4pro C.3 (plan B.6) ------------------------------------ #
        for x in (-64, -30, 0, 30, 65, 104, 123):
            meas[f"width_x{x}"] = shell_width(float(x))
        arm_h = [p["info"]["heading_deg"] for p in parts_log if p.get("plan_item") == "P4"]
        meas["front_arm_heading"] = round(abs([h for h in arm_h if abs(h) < 90][0]), 3)
        meas["rear_arm_heading"] = round(abs([h for h in arm_h if abs(h) > 90][0]), 3)
        can = next(p for p in parts_log if p.get("plan_item") == "P3"
                   and p.get("info", {}).get("role") == "can")
        meas["motor_can_dia"] = round(max(can["bbox_mm"][0], can["bbox_mm"][1]), 3)
        meas["arm_width_front"] = round(max(
            p["info"]["root_section_mm"][0] for p in parts_log
            if p.get("plan_item") == "P4" and abs(p["info"]["heading_deg"]) < 90), 3)
        bbox = next(p["bbox_mm"] for p in parts_log if p.get("plan_item") == "P8")
        meas["battery_L"], meas["battery_W"], meas["battery_H"] = [round(v, 3) for v in bbox]
        meas["legs_per_front_arm"] = int(sum(1 for p in parts_log
                                             if p.get("plan_item") == "P5")) // 2
        meas["legs_per_rear_arm"] = 0
        cam = np.asarray(gm1["camera"].vertices, float) * 1000.0
        meas["gimbal_front_x"] = round(float(cam[:, 0].max()), 3)
        meas["gimbal_floor_z"] = round(float(cam[:, 2].min()), 3)
        Vf = np.asarray(frame1.v, float) * 1000.0
        meas["frame_height"] = round(float(Vf[:, 2].max() - Vf[:, 2].min()), 3)
        meas["frame_min_z"] = round(float(Vf[:, 2].min()), 3)
        Vd = np.asarray(drone1.v, float) * 1000.0
        R_tip = float(np.hypot(np.asarray(prop1.v, float)[:, 0],
                               np.asarray(prop1.v, float)[:, 1]).max()) * 1000.0
        _Cxy = np.array([[float(d["center"][i]) * 1000.0 for i in (0, 1)] for d in rl1])
        meas["width_props_included"] = round(2.0 * (float(np.abs(_Cxy[:, 1]).max()) + R_tip), 3)
        meas["prop_tip_radius"] = round(R_tip, 4)
        meas["frame_width_no_props"] = round(float(Vf[:, 1].max() - Vf[:, 1].min()), 3)
        meas["frame_length_no_props"] = round(float(Vf[:, 0].max() - Vf[:, 0].min()), 3)
        meas["frozen_blade_bbox_mm"] = [round(float(Vd[:, i].max() - Vd[:, i].min()), 3)
                                        for i in (0, 1, 2)]
    else:
        for x in (-50, 0, 30, 54, 70, 86):
            meas[f"width_x{x}"] = shell_width(float(x))
        arm_h = [p["info"]["heading_deg"] for p in parts_log if p.get("plan_item") == "P4"]
        meas["front_arm_heading"] = round(abs([h for h in arm_h if abs(h) < 90][0]), 3)
        meas["rear_arm_heading"] = round(abs([h for h in arm_h if abs(h) > 90][0]), 3)
        can = next(p for p in parts_log if p.get("plan_item") == "P3"
                   and p.get("info", {}).get("role") == "can")
        meas["motor_can_dia"] = round(max(can["bbox_mm"][0], can["bbox_mm"][1]), 3)
        bb = bat["info"] if bat else {}
        bbox = next(p["bbox_mm"] for p in parts_log if p.get("plan_item") == "P8")
        meas["battery_L"], meas["battery_W"], meas["battery_H"] = [round(v, 3) for v in bbox]
        meas["legs_per_front_arm"] = int(sum(1 for p in parts_log if p.get("plan_item") == "P5")) // 2
        meas["legs_per_rear_arm"] = 0
        meas["accent_parts"] = int((G_all == "accent").sum())
        Vd = np.asarray(drone1.v, float) * 1000.0
        meas["height_props_included"] = round(float(Vd[:, 2].max() - Vd[:, 2].min()), 3)
        #  ⚠ BUG FIX (first run): the official 304 x 380 mm envelope is the SWEPT one. build_drone
        #  freezes every blade at base_ang, so its bounding box depends on where the blades happen to
        #  point (measured 258.8 x 362.0 mm). The swept envelope is rotor centre + realized tip radius.
        R_tip = float(np.hypot(np.asarray(prop1.v, float)[:, 0],
                               np.asarray(prop1.v, float)[:, 1]).max()) * 1000.0
        _Cxy = np.array([[float(d["center"][i]) * 1000.0 for i in (0, 1)] for d in rl1])
        meas["width_props_included"] = round(2.0 * (float(np.abs(_Cxy[:, 1]).max()) + R_tip), 3)
        meas["length_props_included"] = round(2.0 * (float(np.abs(_Cxy[:, 0]).max()) + R_tip), 3)
        meas["prop_tip_radius"] = round(R_tip, 4)
        meas["frozen_blade_bbox_mm"] = [round(float(Vd[:, i].max() - Vd[:, i].min()), 3)
                                        for i in (0, 1, 2)]
        cam_x_hi = float(np.asarray(gm1["camera"].vertices)[:, 0].max()) * 1000.0
        meas["folded_length"] = round(cam_x_hi - meas["shell_x_lo"], 3)
    led["C3_measured"] = meas
    for row in t3["targets"]:
        i = row["id"]
        got = meas.get(i)
        if "value_mm" in row:
            want, tol, unit = row["value_mm"], row["tol_mm"], "mm"
        elif "value_deg" in row:
            want, tol, unit = row["value_deg"], row["tol_deg"], "deg"
        else:
            want, tol, unit = row["value"], row["tol"], ""
        ok = got is not None and abs(float(got) - float(want)) <= float(tol) + 1e-9
        T.add("C.3", f"{i} ({unit})" if unit else i, got, f"{want} +- {tol}", ok,
              note=row.get("note", ""))

    # ------------------------------------------------------------------ C.4 --
    t4 = thr["C4_silhouette"]
    try:
        #  REVIEW FIX 2026-09-18 (R1): C.4 lives in `work/top_iou.py`, which is NOT part of the
        #  installable tree. With MESHREV1_WORK unset the import raised ModuleNotFoundError and
        #  the row printed as a plain FAIL, indistinguishable from a real silhouette failure.
        #  Resolve the delivery's own work/ by default and label an import failure as such.
        #  MERGE FIX 2026-09-18: resolve per drone (see `_work_dir`), and drop a `top_iou` left
        #  in sys.modules by an earlier drone in the same process — the two aircraft ship
        #  different modules under that one name.
        _cand = _work_dir(key, "top_iou.py")
        if _cand is None:
            raise ModuleNotFoundError(
                f"no top_iou.py for {key}: looked in $MESHREV1_WORK, "
                f"{os.path.join(os.path.dirname(_ROOT), 'work', key)} and ../work")
        sys.modules.pop("top_iou", None)
        if _cand in sys.path:
            sys.path.remove(_cand)
        sys.path.insert(0, _cand)
        import top_iou
        R_, s_, t_ = top_iou.transform()
        ph, size = top_iou.photo_mask()
        m1 = top_iou.frame_mask_for(spec1, size, R_, s_, t_)
        iou1 = top_iou.iou(ph, m1)
        T.add("C.4", "top-view silhouette IoU vs photo", round(iou1, 4),
              f">= {t4['rev1_iou_min']}", iou1 >= t4["rev1_iou_min"],
              note=f"revision 0 (frozen): {t4['rev0_iou_frozen']}")
        led["C4"] = dict(rev1_iou=round(iou1, 4), rev0_iou=t4["rev0_iou_frozen"])
        if key == "mavic4pro":
            m0 = top_iou.frame_mask_for(spec0, size, R_, s_, t_)
            uu = np.abs(np.arange(ph.shape[1])[None, :] - s_) < (60.0 / R_)
            band = np.repeat(uu, ph.shape[0], axis=0)
            b1 = top_iou.iou(ph & band, m1 & band)
            b0 = top_iou.iou(ph & band, m0 & band)
            T.add("C.4", "top-view IoU, |y| < 60 mm (shell without the arms)",
                  round(b1, 4), f"report (revision 0: {b0:.4f})", True, mode="report")
            T.add("C.4", "top-view IoU, whole airframe, revision 0 recomputed",
                  round(top_iou.iou(ph, m0), 4), f"report (frozen: {t4['rev0_iou_frozen']})",
                  True, mode="report")
            led["C4"].update(rev1_iou_body_band=round(b1, 4), rev0_iou_body_band=round(b0, 4),
                             rev0_iou_recomputed=round(top_iou.iou(ph, m0), 4))
    except Exception as e:
        T.add("C.4", "top-view silhouette IoU vs photo",
              f"NOT MEASURED ({type(e).__name__}: {e}) — set MESHREV1_WORK to the delivery's work/",
              f">= {t4['rev1_iou_min']}", False)

    # ------------------------------------------------------------------ C.5 --
    def facing(gm, u, half_deg):
        out = {}
        u = np.asarray(u, float) / np.linalg.norm(u)
        for g, m in gm.items():
            n = m.face_normals
            a = m.area_faces
            sel = (n @ u) > math.cos(math.radians(half_deg))
            out[g] = round(float(a[sel].sum()) / 1e-6, 1)
        return out
    c5 = {}
    for az, el in ((0, 0), (90, 0), (180, 0), (0, -30), (0, -90)):
        u = np.array([math.cos(math.radians(el)) * math.cos(math.radians(az)),
                      math.cos(math.radians(el)) * math.sin(math.radians(az)),
                      math.sin(math.radians(el))])
        for cone, hd in (("5deg", 5.0), ("10deg", 10.0)):
            c5[f"az{az}_el{el}_{cone}"] = dict(rev1=facing(gm1, u, hd), rev0=facing(gm0, u, hd))
    led["C5_facing_area_mm2"] = c5
    T.add("C.5", "facing area by group (mm^2)",
          {k: sum(v["rev1"].values()) for k, v in list(c5.items())[:2]},
          "report only", True, mode="report")

    # ------------------------------------------------------------------ C.6 --
    t6 = thr["C6_facets"]
    sag = max((float(p.get("mesh_sagitta_mm", 0.0)) for p in parts_log
               if isinstance(p.get("mesh_sagitta_mm", None), (int, float))), default=0.0)
    sag = max(sag, max((float(p.get("curve_sagitta_mm", 0.0)) for p in parts_log
                        if isinstance(p.get("curve_sagitta_mm", None), (int, float))),
                       default=0.0))
    T.add("C.6", "max part sagitta (mm)", round(sag, 4), f"<= {t6['sagitta_mm_max']}",
          sag <= t6["sagitta_mm_max"])
    nf = int(len(np.asarray(frame1.f)))
    T.add("C.6", "frame faces", nf, f"<= {t6['frame_faces_max']}", nf <= t6["frame_faces_max"],
          note=f"revision 0: {len(np.asarray(frame0.f))}")
    npf = int(len(np.asarray(prop1.f)))
    T.add("C.6", "prop faces per rotor", npf, f"<= {t6['prop_faces_per_rotor_max']}",
          npf <= t6["prop_faces_per_rotor_max"], note=f"revision 0: {len(np.asarray(prop0.f))}")

    # ------------------------------------------------------------------ C.7 --
    t7 = thr["C7_props"]
    import drone_parts_rev1 as DP
    dch = 0.0
    p7 = {}
    ok7 = True
    for mirror in (False, True):
        pm = build_propeller(spec1, mirror=mirror)
        spin = -1 if mirror else +1
        for rr in t7["stations_r_over_R"]:
            o = DP.blade_orientation(_mesh_of(pm), spin, int(spec1.prop_blades), r_over_R=rr)
            p7[f"mirror{int(mirror)}_r{rr}"] = o["summary"] if "summary" in o else o
            ok7 = ok7 and bool(o.get("all_ok", o.get("summary", {}).get("all_ok", False)))
    led["C7"] = p7
    T.add("C.7", "thick edge raised and leading (0.3/0.5/0.7/0.9 R, both hands)",
          "all_ok" if ok7 else "not all blades", t7["thick_edge_raised_and_leading"], ok7)
    #  chord and blade angle against revision 0
    #  ⚠ the E1 API says to score plan C.7's +-0.2 deg with `angle_inertia_deg`, not with the
    #  convex-hull angle: mirroring the chord (P6) moves the hull's longest diagonal by a few
    #  tenths of a degree without changing the blade's set. Both are recorded.
    dan = dan_hull = 0.0
    ang_rows = {}
    for rr in t7["stations_r_over_R"]:
        o1 = DP.blade_orientation(_mesh_of(prop1), +1, int(spec1.prop_blades), r_over_R=rr)
        o0 = DP.blade_orientation(_mesh_of(prop0), +1, int(spec0.prop_blades), r_over_R=rr)
        for k1, k0 in zip(o1["blades"], o0["blades"]):
            dan = max(dan, abs(float(k1["angle_inertia_deg"]) - float(k0["angle_inertia_deg"])))
            dan_hull = max(dan_hull, abs(float(k1["angle_hull_deg"])
                                         - float(k0["angle_hull_deg"])))
            dch = max(dch, abs(float(k1.get("chord_mm", 0.0)) - float(k0.get("chord_mm", 0.0))))
        ang_rows[str(rr)] = dict(rev1=[round(float(b["angle_inertia_deg"]), 4)
                                       for b in o1["blades"]],
                                 rev0=[round(float(b["angle_inertia_deg"]), 4)
                                       for b in o0["blades"]])
    led["C7_blade_angles"] = ang_rows
    T.add("C.7", "chord vs revision 0 (mm)", round(dch, 4),
          f"<= {t7['chord_max_error_mm']}", dch <= t7["chord_max_error_mm"])
    T.add("C.7", "blade angle vs revision 0 (deg, inertia)", round(dan, 4),
          f"<= {t7['blade_angle_max_error_deg']}", dan <= t7["blade_angle_max_error_deg"],
          note=f"convex-hull reading of the same blades: {dan_hull:.4f} deg")
    try:
        hd = mesh_check.check_handedness(spec1, mesh=drone1)
        T.add("C.7", "check_handedness", hd.get("ok"), t7["check_handedness_pass"],
              bool(hd.get("ok")))
        led["handedness"] = hd
    except Exception as e:
        T.add("C.7", "check_handedness", f"error: {type(e).__name__}", "-", False)

    # ------------------------------------------------------------------ C.8 --
    t8 = thr["C8_kinematics"]
    dirs = [int(d["dir"]) for d in rl1]
    T.add("C.8", "rotor_dirs", dirs, t8["rotor_dirs"], dirs == list(t8["rotor_dirs"]),
          note=f"revision 0: {[int(d['dir']) for d in rl0]}")
    from articulated_fast import FastPoser
    fp = FastPoser(spec1)
    ver = fp.verify()
    #  ⚠ BUG FIX (first run): verify() returns a dict; the first version took the largest of ALL
    #  its values, which is n_vert (20,240), not the error.
    verv = float(ver["max_abs_vertex_diff_m"])
    T.add("C.8", "FastPoser.verify() max vertex diff (m)", f"{verv:.3e}",
          f"<= {t8['fastposer_verify_max']}", verv <= t8["fastposer_verify_max"],
          note=f"ok={ver['ok']}")

    # ------------------------------------------------------------------ C.9 --
    T.add("C.9", "specular census (pre-registration input)", "deferred to E3", "report only",
          True, mode="report",
          note="plan D.0 runs it on the common grid for both revisions; it does not gate geometry")

    # ----------------------------------------------------------------- C.11 --
    t11 = thr["C11_certificates"]
    #  ⚠ METRIC FIX (first run): the first version measured the distance from each MIRRORED vertex
    #  to the faceted surface. A vertex mirrored onto an asymmetric triangulation lies on the
    #  analytic surface but up to one sagitta (about 1 mm here) from the facets, so that number
    #  scored the tessellation, not the symmetry. The symmetry of the mesh is whether the mirrored
    #  vertex SET is the vertex set, which is exact for a symmetric build.
    from scipy.spatial import cKDTree
    Vv = np.asarray(frame1.v, float)
    mir = Vv.copy()
    mir[:, 1] *= -1.0
    d_mir = float(cKDTree(Vv).query(mir)[0].max()) / 1e-3
    V0 = np.asarray(frame0.v, float)
    m0mir = V0.copy(); m0mir[:, 1] *= -1.0
    d_mir0 = float(cKDTree(V0).query(m0mir)[0].max()) / 1e-3
    d_surf = float(trimesh.proximity.closest_point(_mesh_of(frame1), mir)[1].max()) / 1e-3
    d_surf0 = float(trimesh.proximity.closest_point(_mesh_of(frame0), m0mir)[1].max()) / 1e-3
    T.add("C.11", "mirrored vertex distances (mm)",
          dict(to_vertex=round(d_mir, 4), to_surface=round(d_surf, 4)),
          f"report (revision 0: {d_mir0:.4f} / {d_surf0:.4f})", True, mode="report",
          note="a vertex-level number scores the triangulation, not the geometry - see the "
               "threshold file's deviation entry")
    tmf = _mesh_of(frame1)
    com_y = abs(float(np.asarray(gm1["body"].center_mass)[1])) / 1e-3
    T.add("C.11", "|centre of mass y| of the body (mm)", round(com_y, 6),
          f"<= {t11['com_y_max_mm']}", com_y <= t11["com_y_max_mm"])
    yb = {g: round(abs(float(m.bounds[0][1] + m.bounds[1][1])) / 1e-3, 6) for g, m in gm1.items()}
    T.add("C.11", "y bounding box symmetry per group (mm)", yb,
          f"<= {t11['ybbox_symmetry_max_mm']}",
          max(yb.values()) <= t11["ybbox_symmetry_max_mm"])
    a_err = {}
    for g, m in gm1.items():
        mm = m.copy()
        V = np.asarray(mm.vertices).copy()
        V[:, 1] *= -1
        mm = trimesh.Trimesh(vertices=V, faces=np.asarray(mm.faces)[:, ::-1], process=False)
        a_err[g] = round(abs(float(mm.area) - float(m.area)) / max(float(m.area), 1e-12) * 100, 6)
    T.add("C.11", "per-group mirrored area error (%)", a_err,
          f"<= {t11['per_group_area_mirror_error_pct_max']}",
          max(a_err.values()) <= t11["per_group_area_mirror_error_pct_max"])
    T.add("C.11", "placement: rotor xy / z vs revision 0 (mm)",
          dict(xy=f"{exy:.2e}", z=f"{ez:.2e}"),
          f"<= {t11['placement_rotor_xy_max_error_mm']} / "
          f"{t11['placement_rotor_z_max_error_mm']}",
          exy <= t11["placement_rotor_xy_max_error_mm"]
          and ez <= t11["placement_rotor_z_max_error_mm"])

    # ----------------------------------------------------------------- C.12 --
    mat = {}
    for tag, gm in (("rev1", gm1), ("rev0", gm0)):
        mat[tag] = {g: dict(material=DRONE_GROUP_MAT.get(g, ["?"])[0],
                            area_mm2=round(float(m.area) / 1e-6, 1),
                            volume_mm3=round(float(m.volume) / 1e-9, 1))
                    for g, m in gm.items()}
    led["C12_material_table"] = mat
    unknown = [g for g in gm1 if g not in DRONE_GROUP_MAT]
    T.add("C.12", "material groups known", sorted(gm1), "all in DRONE_GROUP_MAT", not unknown)
    T.add("C.12", "area/volume per material", {g: v["area_mm2"] for g, v in mat["rev1"].items()},
          "report only", True, mode="report")

    # ----------------------------------------------------------------- C.13 --
    t13 = thr["C13_canonical_repairs"]
    inter = 0.0
    if "battery" in gm1 and "pcb" in gm1:
        C = gm1["pcb"].triangles_center
        inter = 100.0 * float(gm1["pcb"].area_faces[_inside(gm1["battery"], C)].sum()) \
            / max(float(gm1["pcb"].area), 1e-12)
    T.add("C.13", "battery/pcb interpenetration (%)", round(inter, 4),
          f"<= {t13['battery_pcb_plate_interpenetration_pct_max']}",
          inter <= t13["battery_pcb_plate_interpenetration_pct_max"] + 1e-9)
    T.add("C.13", "body closed", bool(all(c.is_watertight
                                          for c in gm1["body"].split(only_watertight=False))),
          t13["body_closed"],
          all(c.is_watertight for c in gm1["body"].split(only_watertight=False)))
    canon = (sorted(mesh_fix_set()) == sorted(MESH_FIX_CANON)
             and blade_law_canon() == BLADE_LAW_CANON)
    T.add("C.13", "canonical MESH_FIX / BLADE_LAW",
          dict(mesh_fix=sorted(mesh_fix_set()), blade_law=blade_law_canon()),
          dict(mesh_fix=sorted(MESH_FIX_CANON), blade_law=BLADE_LAW_CANON), canon)

    # ------------------------------------------------ REVIEW ROWS (2026-09-18, R1) --
    #  Three things no row above can see. All are REPORT rows: adding a gate after the first
    #  acceptance run would be exactly the threshold move plan M8 forbids. The numbers are
    #  measured on the BUILT mesh, not declared by the part builders.
    #
    #  R1a  facet sagitta measured on the mesh. C.6 above reads `mesh_sagitta_mm` /
    #       `curve_sagitta_mm` as the parts library DECLARES them, so a part that reports
    #       nothing contributes nothing and the row cannot fail. Measured here over face pairs
    #       whose dihedral angle is <= 40 deg (a tessellated smooth surface; above that the
    #       join is a designed edge), by two chord conventions:
    #         edge  — half the shared edge  x tan(theta/4)
    #         span  — half the perpendicular span across the shared edge x tan(theta/4)
    #       Both are exact for a circular arc; they differ on anisotropic tessellations, and
    #       the loft between two measured stations is ruled, so they differ here.
    def _sag(m, smooth_deg=40.0):
        m = m.copy(); m.merge_vertices()
        ang = m.face_adjacency_angles
        if len(ang) == 0:
            return 0.0, 0.0
        P, ed = m.vertices, m.face_adjacency_edges
        el = np.linalg.norm(P[ed[:, 0]] - P[ed[:, 1]], axis=1)
        spans = np.zeros(len(ang))
        tri = m.faces[m.face_adjacency]
        for i in range(len(ang)):
            a, b = P[ed[i, 0]], P[ed[i, 1]]
            u = b - a
            L = float(np.linalg.norm(u))
            if L == 0.0:
                continue
            u = u / L
            for t_ in tri[i]:
                opp = [v for v in t_ if v not in (ed[i, 0], ed[i, 1])]
                if opp:
                    p = P[opp[0]] - a
                    spans[i] += float(np.linalg.norm(p - (p @ u) * u))
        keep = ang <= math.radians(smooth_deg)
        if not keep.any():
            return 0.0, 0.0
        tq = np.tan(ang / 4.0)
        return (float((el / 2.0 * tq)[keep].max()) * 1e3,
                float((spans / 2.0 * tq)[keep].max()) * 1e3)
    _per = {g: [round(v, 4) for v in _sag(m)] for g, m in gm1.items()}
    _per["prop"] = [round(v, 4) for v in _sag(_mesh_of(prop1))]
    _se = max(v[0] for v in _per.values())
    _ss = max(v[1] for v in _per.values())
    _we = max(_per, key=lambda g: _per[g][0])
    _ws = max(_per, key=lambda g: _per[g][1])
    led["R1_measured_sagitta_mm"] = dict(per_group_edge_span=_per, max_edge_chord=round(_se, 4),
                                         max_span_chord=round(_ss, 4), worst_edge=_we,
                                         worst_span=_ws, smooth_join_max_deg=40.0)
    T.add("R1", "measured facet sagitta (mm, edge / span chord)",
          f"{round(_se, 3)} ({_we}) / {round(_ss, 3)} ({_ws})",
          f"C.6 declares {round(sag, 4)}; limit {t6['sagitta_mm_max']}", True, mode="report",
          note="the C.6 row above is the parts library's declared target, not a measurement of "
               "the built mesh; both chord conventions are exact for a circular arc and differ "
               "here because the loft between two measured stations is ruled")

    #  R1b  coincident faces across two material groups: same centroid within 20 um and
    #       parallel normals. A ray tracer has no defined answer for which material it hits.
    from scipy.spatial import cKDTree as _KD
    _C, _N, _A, _G = [], [], [], []
    for g, m in gm1.items():
        _C.append(m.triangles_center); _N.append(m.face_normals)
        _A.append(m.area_faces); _G.append(np.array([g] * len(m.faces)))
    _C = np.vstack(_C); _N = np.vstack(_N)
    _A = np.concatenate(_A); _G = np.concatenate(_G)
    _pr = _KD(_C).query_pairs(r=2e-5, output_type="ndarray")
    if len(_pr):
        _bad = _pr[(_G[_pr[:, 0]] != _G[_pr[:, 1]])
                   & (np.abs((_N[_pr[:, 0]] * _N[_pr[:, 1]]).sum(1)) > 0.999)]
    else:
        _bad = np.zeros((0, 2), int)
    led["R1_coincident_cross_group_faces"] = dict(
        n=int(len(_bad)), area_mm2=round(float(_A[_bad[:, 0]].sum()) / 1e-6, 3) if len(_bad) else 0.0,
        pairs=sorted({f"{_G[i]}|{_G[j]}" for i, j in _bad[:500]}) if len(_bad) else [])
    T.add("R1", "coincident faces across material groups",
          f"{len(_bad)} ({led['R1_coincident_cross_group_faces']['area_mm2']} mm^2) "
          f"{led['R1_coincident_cross_group_faces']['pairs']}",
          "0 is the only value a ray tracer can resolve", True, mode="report",
          note="two co-located, parallel triangles in different material groups; which one a "
               "ray hits is decided by floating-point tie-breaking")

    #  R1c  where the internal metal actually sits, and how much of it is welded to the shell
    #       surface. C.2 gates the clearance but not the placement, and the placement has no
    #       owned source (the manual gives the pack's size only).
    _rep = {}
    for g in ("battery", "pcb"):
        if g not in gm1:
            continue
        m = gm1[g]
        c = m.triangles_center
        sd = trimesh.proximity.signed_distance(gm1["body"], c)
        _rep[g] = dict(centre_x_mm=round(float(m.bounds[:, 0].mean()) * 1e3, 3),
                       x_span_mm=[round(float(m.bounds[0, 0]) * 1e3, 2),
                                  round(float(m.bounds[1, 0]) * 1e3, 2)],
                       area_on_shell_surface_mm2=round(
                           float(m.area_faces[np.abs(sd) <= 5e-5].sum()) / 1e-6, 2),
                       area_outside_shell_mm2=round(
                           float(m.area_faces[sd < 0].sum()) / 1e-6, 2))
    _rep["body_x_span_mm"] = [round(float(gm1["body"].bounds[0, 0]) * 1e3, 2),
                              round(float(gm1["body"].bounds[1, 0]) * 1e3, 2)]
    led["R1_internal_metal_placement"] = _rep
    T.add("R1", "internal metal placement (mm)",
          {g: v.get("centre_x_mm") for g, v in _rep.items() if isinstance(v, dict)},
          "no owned source fixes these centres", True, mode="report",
          note=f"battery faces welded to the shell surface: "
               f"{_rep.get('battery', {}).get('area_on_shell_surface_mm2')} mm^2; "
               f"body x span {_rep['body_x_span_mm']}")

    #  R1d  the BUILT arm axes measured against the owned top photo, not against the number the
    #       builder wrote down. The C.3 heading rows compare the build with a target in the
    #       threshold file; when that target is itself a reading of the same photo, the row cannot
    #       see a reading error — which is exactly how the 65.34 deg front heading passed on
    #       2026-09-18. This row re-runs the mid-line estimator (both edges of the arm band, so
    #       the arm's own width cancels) on the photo at the heading the mesh was actually built
    #       at, and also reports the heading that minimises the residual.
    if key == "mini5pro":
        try:
            #  MERGE FIX 2026-09-18: the delivery looked only in `<parent>/fix`, which is the
            #  mini5pro delivery's own layout. Use the shared per-drone resolver.
            _wk = _work_dir(key, "arm_midline.py")
            if _wk is None:
                raise ModuleNotFoundError("no arm_midline.py for mini5pro")
            if _wk not in sys.path:
                sys.path.insert(0, _wk)
            import arm_midline as _am
            _mask = _am.make_mask(18.0, True)
            #  the mesh is mirror-symmetric, so the right-hand arm carries the negated heading
            _built = {"FL": abs(meas["front_arm_heading"]),
                      "FR": -abs(meas["front_arm_heading"]),
                      "RL": abs(meas["rear_arm_heading"]),
                      "RR": -abs(meas["rear_arm_heading"])}
            _rows = {}
            for _k, _th in _built.items():
                _r = _am.resid_at(_mask, _k, _th, 25.0, 62.0)
                _f = _am.fit(_mask, _k, _th, 25.0, 62.0)
                _bf = (None if _f is None
                       else abs(((_f["theta_pinned_deg"] + 180.0) % 360.0) - 180.0))
                _rows[_k] = dict(built_deg=round(abs(_th), 3), at_built=_r,
                                 best_fit_deg=(None if _bf is None else round(_bf, 3)),
                                 best_rms_mm=(None if _f is None else _f["rms_pinned_mm"]),
                                 band_width_mm=(None if _f is None else _f["band_width_mm"]))
            led["R1_arm_axis_vs_photo"] = _rows
            for _nm, _pair in (("front", ("FL", "FR")), ("rear", ("RL", "RR"))):
                _v = [_rows[k2] for k2 in _pair]
                T.add("R1", f"{_nm} arm axis vs the photo mid-line (mm)",
                      "rms " + " / ".join(str(x["at_built"]["rms_mm"]) for x in _v)
                      + f" at {_v[0]['built_deg']} deg",
                      f"0 mm; band {_v[0]['band_width_mm']} mm wide", True, mode="report",
                      note=f"{_pair[0]} / {_pair[1]}, mid-line of the arm band on "
                           "assets/photos/mini5pro/mini 5 pro_3.png, 38 stations 25-62 mm inboard "
                           "of the hub, both edges used so the arm width cancels; best-fit "
                           "headings "
                           + " / ".join(f"{x['best_fit_deg']:.2f}" for x in _v)
                           + " deg. This row does not read the threshold file, so a wrong target "
                             "cannot hide a wrong build.")
        except Exception as _e:                                   # pragma: no cover
            T.add("R1", "front arm axis vs the photo mid-line (mm)", "NOT MEASURED",
                  f"{type(_e).__name__}: {_e}", True, mode="report",
                  note="needs fix/arm_midline.py beside the delivery, or MESHREV1_WORK pointing "
                       "at it, plus PIL and scipy")

    # ------------------------------------------------------------- fingerprint
    import mesh_rev
    led["fingerprint"] = mesh_rev.fingerprint_poser(fp)
    led["table"] = T.rows
    led["all_gates_pass"] = T.gate_ok()
    if verbose:
        print(T.render())
        print()
        print(f"fingerprint  {led['fingerprint']}")
        print(f"gates        {'ALL PASS' if led['all_gates_pass'] else 'FAILURES PRESENT'}")
        nf = [r for r in T.rows if r["mode"] == "gate" and not r["ok"]]
        for r in nf:
            print(f"  FAIL {r['check']} {r['what']}: got {r['got']} want {r['want']}")
        for k, v in getattr(G, "SOURCES_NOT_FOUND", {}).items():
            print(f"  not sourced — {k}: {v}")
    return led


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drone", required=True)
    ap.add_argument("--rev", type=int, default=1)
    ap.add_argument("--variant", default=None)
    ap.add_argument("--thresholds", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    thr_path = a.thresholds or os.path.join(
        _ROOT, "docs", "mesh_rev1", f"{a.drone}_acceptance_thresholds.json")
    thr = json.load(open(thr_path))
    led = run(a.drone, a.rev, thr, variant=a.variant)
    led["thresholds_file"] = thr_path
    led["thresholds_sha256"] = hashlib.sha256(open(thr_path, "rb").read()).hexdigest()
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        json.dump(led, open(a.out, "w"), indent=1, default=str)
        print(f"\nledger  {a.out}")
    sys.exit(0 if led["all_gates_pass"] else 1)


if __name__ == "__main__":
    main()
