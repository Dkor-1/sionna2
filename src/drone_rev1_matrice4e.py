# -*- coding: utf-8 -*-
"""drone_rev1_matrice4e.py — the Matrice 4E frame, mesh revision 1 (plan B.3, M4E-1 ... M4E-8).

What this module is
    The geometry of one (drone key, revision) pair. `src/mesh_rev_matrice4e.py` registers it;
    `src/drone_rev.build_frame_rev` calls `build_frame(spec)` and then applies revision 0's union
    semantics. Revision 0 never reaches this file.

Coordinate frame
    Millimetres inside the station tables, metres in every mesh (the repo convention). +x is the
    nose, +y is to the left, +z is up, and z = 0 is the arm hub plane.

Where the numbers come from
    Every dimension below is measured on DJI's official Matrice 4T STEP
    (`assets/meshes/reference/matrice4-M4T_v2.step`, gitignored; the 4T shares the airframe with
    the 4E), except the gimbal block width, which comes from owned 4E photos because the 4T
    gimbal carries a thermal camera the 4E does not have. `docs/mesh_rev1/matrice4e_sources.json`
    carries value, tolerance, source and evidence grade for each one. No dimension here was
    invented, and nothing was chosen to preserve an RF trend (plan B.0, D.5.4).

What changes against revision 0
    M4E-1  the unmeasured internal metal plate (142 x 67.6 x 7.1 mm) is gone.
    M4E-2  the flat 82 x 74 mm nose cap is gone. The shell's own floor now rises over the gimbal
           (z_bot 1.0 at x=+72 to 39.0 at x=+152), which is the beak, and a second loft carries
           the gimbal cradle below it.
    M4E-3  the tail closes around the battery; the pack keeps its official size and its CAD
           position and is contained by P8 (see the DEVIATION note on `_battery`).
    M4E-4  straight front arms from the CAD arm axis, reaching revision 0's rotor centres.
    M4E-5  fuselage sides and belly from the CAD section table (belly -30.81 instead of -34.74).
    M4E-6  the motor is a can plus a prop adapter from the CAD, and `rotor_z_mm` puts the blade
           plane on the adapter top (plan B.0's rotor-z rule).
    M4E-7  gimbal block width 59 -> 64 mm; its height, depth, yaw post and damping plate are
           revision 0's.
    M4E-8  the propeller comes from `drone_parts_rev1.propeller_rev1` (P6), and `rotor_dirs` is
           the measured pattern: front-left and rear-right clockwise.

Changed on 2026-09-18 after the adversarial review (scratch/wf/b2_matrice4e_verify.md)
    F-1  M4E-4a/b: the front arm axis takes the review's re-measured CAD heading, 67.58 deg. Its
         root x then comes out 84.02 mm, not the review's CAD 85.50, because revision 1 may not
         move the rotor centre and ours is 2.26 mm outboard in y of the CAD bell.
    F-2  M4E-4g (the review's new defect): each arm is now two P4 segments, a shaft with the CAD's
         near-constant section and a 20 mm motor-pad flare, instead of one segment whose linear
         taper smeared the pad flare over the whole arm.
    F-3  the boolean's sliver triangles are removed by a guarded half-edge collapse after the
         group union (`_repair_slivers`).

    Carried over from revision 0 unchanged: the landing legs, the four deck fisheyes, the two
    downward vision lenses, the beacon, the RTK turret (except that it now reaches the CAD
    91.70 mm instead of being cut off by the envelope fit) and the mainboard box.

Shape parameters vs dimensions
    `width`, `z_top` and `z_bot` are dimensions and are used exactly as measured. `z_mid` (the
    height of the section's widest line) and the superellipse exponents `n_up` / `n_dn` are shape
    parameters read off the same sections; they are noisy station to station, so they are
    smoothed with a 3-point moving average (`_smooth_shape`). The smoothing is declared, it
    touches no dimension, and it is deterministic.
"""
from __future__ import annotations

import math

import numpy as np

MM = 1e-3

# --------------------------------------------------------------------------- #
#  CAD measurements (millimetres). Raw, as measured — see the module docstring.
# --------------------------------------------------------------------------- #
#: Fuselage shell, CAD solids 109 / 124 / 119 / 116 / 123 / 120, 4 mm x-bands every 8 mm.
#: z_top uses only z-bins at least 22 mm wide, so the narrow RTK turret stem is not counted as
#: deck; the turret is a separate part. z_bot uses bins at least 6 mm wide.
SHELL_STATIONS = (
    # x,      width,  z_top,  z_bot,  z_mid,  n_up,  n_dn
    (-72.0,   52.71,   19.0,  -13.0,    2.5,  2.55,  2.50),
    (-64.0,   70.01,   48.0,  -24.0,    4.5,  1.80,  2.25),
    (-56.0,   72.38,   57.0,  -29.0,   -1.5,  2.90,  2.15),
    (-48.0,   76.12,   59.0,  -29.0,   45.5,  3.75,  1.95),
    (-40.0,   75.99,   58.0,  -31.0,   47.5,  3.50,  1.90),
    (-32.0,   74.68,   58.0,  -31.0,   47.5,  1.95,  2.15),
    (-24.0,   73.72,   59.0,  -30.0,   48.0,  2.05,  1.85),
    (-16.0,   72.95,   60.0,  -30.0,   46.5,  2.10,  1.95),
    (-8.0,    74.26,   61.0,  -30.0,   44.0,  1.90,  1.90),
    (0.0,     76.00,   62.0,  -28.0,   43.5,  1.80,  1.75),
    (8.0,     77.88,   62.0,  -28.0,   43.0,  1.85,  1.85),
    (16.0,    79.71,   63.0,  -29.0,   42.5,  1.75,  1.60),
    (24.0,    81.05,   63.0,  -29.0,   41.5,  1.80,  1.60),
    (32.0,    82.88,   64.0,  -27.0,   41.5,  1.75,  1.70),
    (40.0,    84.62,   64.0,  -28.0,   41.5,  1.70,  1.65),
    (48.0,    86.06,   65.0,  -28.0,   40.0,  1.85,  1.65),
    (56.0,    87.40,   65.0,  -27.0,   42.0,  2.00,  1.60),
    (64.0,    92.60,   66.0,  -27.0,   21.5,  3.25,  1.60),
    (72.0,    94.15,   66.0,    1.0,   22.0,  3.75,  1.60),
    (80.0,    93.59,   66.0,    1.0,   21.5,  3.35,  1.60),
    (88.0,    87.62,   65.0,    0.0,   40.5,  3.95,  3.50),
    (96.0,    86.24,   64.0,    8.0,   47.0,  3.75,  2.25),
    (104.0,   85.14,   64.0,   29.0,   46.5,  3.55,  3.40),
    (112.0,   83.83,   64.0,   30.0,   45.5,  4.00,  3.45),
    (120.0,   82.67,   63.0,   32.0,   46.5,  3.80,  4.00),
    (128.0,   81.09,   62.0,   33.0,   48.0,  4.20,  3.60),
    (136.0,   78.32,   62.0,   34.0,   47.5,  3.90,  4.35),
    (144.0,   74.22,   60.0,   35.0,   44.5,  2.60,  4.10),
    (152.0,   61.12,   57.0,   39.0,   41.5,  2.20,  3.00),
)
#: Tail dome: the CAD shell tail ends at x = -75.59, i.e. 3.59 mm ahead of the last station.
SHELL_TAIL_DOME_MM = 3.59
#: Nose dome: the CAD nose-top cover (solid 123) ends at x = +157.73.
SHELL_NOSE_DOME_MM = 5.73

#: Gimbal cradle block, CAD solids 49 / 56 / 57 / 58, same measurement.
NOSE_STATIONS = (
    (80.0,    43.52,   28.0,  -17.0,    0.0,  1.60,  4.05),
    (88.0,    44.00,   35.0,  -17.0,   12.5,  2.65,  2.55),
    (96.0,    53.63,   41.0,  -19.0,   35.5,  1.60,  1.60),
    (104.0,   61.72,   43.0,  -21.0,   36.5,  1.60,  1.60),
    (112.0,   63.63,   43.0,  -19.0,   -7.5,  1.60,  2.25),
    (120.0,   74.91,   43.0,  -17.0,   -6.5,  1.60,  4.20),
    (128.0,   80.34,   51.0,  -17.0,   -7.5,  2.50,  3.00),
    (136.0,   82.05,   51.0,  -17.0,   -7.0,  2.65,  3.00),
    (144.0,   82.05,   44.0,  -19.0,   -6.0,  2.45,  3.00),
    (152.0,   82.05,    5.0,  -19.0,   -7.5,  3.00,  3.00),
)
NOSE_TAIL_DOME_MM = 4.0       # blends back into the shell at x = 76
NOSE_FRONT_DOME_MM = 7.0      # CAD cradle solid 49 ends at x = 159.01

#: Arm axes. (root_xy, root_z, tip_z, root_section, tip_section) per rotor family.
#: The root is the point where the CAD arm axis crosses |y| = 47.08 mm, the CAD shell's largest
#: half width; the tip is revision 0's realized rotor centre in xy (plan B.0 keeps rotor xy).
#:
#: ⚠ REVIEW FIX F-1 (adversarial review 2026-09-18, target M4E-4b/M4E-4a). The review re-measured
#:   the CAD front-arm axis and got heading 67.58 deg (area-weighted principal axis) with the axis
#:   crossing |y| = 47.08 at x = 85.50 mm. Those two numbers belong together: they are the same
#:   line, anchored on the CAD's own bell centre (139.63, 179.11). Revision 1 may not move the
#:   rotor centre (plan B.0/C.3 pin rotor xy to revision 0's (139.4247, 181.3738), which is
#:   2.26 mm further outboard in y than the CAD bell), so the arm axis has exactly one free
#:   parameter — its heading — and the root x follows. At the review's heading 67.58 deg the axis
#:   through OUR rotor centre crosses |y| = 47.08 at x = 84.02 mm, not 85.50. 85.50 would need
#:   heading 68.12 deg, outside the plan's 66-68 band. So the heading is taken as measured
#:   (67.58) and the 1.48 mm of root x is reported as the consequence of the pinned rotor centre.
#:   Revision 1 as delivered used 82.72 / 67.11 deg.
ARM_ROOT_FRONT_MM = (84.02, 47.08, 11.11)
ARM_ROOT_REAR_MM = (-53.11, 47.08, -7.10)
ARM_TIP_Z_FRONT_MM = -15.14
ARM_TIP_Z_REAR_MM = -22.00
#: How far past the shell surface the root is pushed inboard, so the boolean union with the shell
#: closes. It moves the root along the measured axis and changes neither heading nor section.
ARM_ROOT_INSET_MM = 26.0
#: ⚠ REVIEW FIX F-2 (adversarial review 2026-09-18, target M4E-4g). The delivered revision 1 gave
#:   P4 one section at the root and one at the motor pad. P4 interpolates linearly, so the pad
#:   flare — which in the CAD is confined to the last ~20 mm — was smeared over the whole 145 mm
#:   arm and the mid-span shaft came out 22.8 mm wide against the CAD's 12.1 mm. Measured again
#:   here (fix_0918/cad_arm_sections.py, true plane sections normal to the fitted CAD arm axis
#:   every 2.5 mm, station d = distance back from the rotor axis):
#:       front, CAD solid 98:  d=115 12.69 x 14.64 | d=20 12.12 x 13.29 | d=0 27.61 x 12.16
#:       rear,  CAD solid 92:  d=120 14.81 x 15.78 | d=20 13.24 x 14.13 | d=0 27.55 x 12.27
#:   The arm is therefore built as two P4 segments on one axis: a shaft from the root to
#:   d = ARM_FLARE_LEN_MM, then the flare. P4's API is unchanged.
ARM_FLARE_LEN_MM = 20.0
#: (root, flare start at d = ARM_FLARE_LEN_MM, motor pad at d = 0), width x height in mm.
ARM_SECTION_FRONT_MM = ((12.70, 15.40), (12.12, 13.29), (27.61, 12.16))
ARM_SECTION_REAR_MM = ((14.80, 16.10), (13.24, 14.13), (27.55, 12.27))

#: Motor stack, CAD bell and prop-mount solids.
MOTOR_BASE_Z_MM = (-8.51, -16.33, -16.33, -8.51)   # rotor_deg order: FL, RL, RR, FR
MOTOR_CAN_D_MM = 27.0          # = spec.motor_dia_mm, unchanged
MOTOR_CAN_H_MM = 16.3          # = spec.motor_h_mm, unchanged
MOTOR_ADAPTER_D_MM = 27.0
#: Per rotor (FL, RL, RR, FR): the height that puts the stack top on the CAD prop-mount top,
#: 15.30 mm at the front rotors and 6.72 mm at the rear ones.
MOTOR_ADAPTER_H_MM = (7.51, 6.75, 6.75, 7.51)
MOTOR_STACK_TOP_Z_MM = (15.30, 6.72, 6.72, 15.30)      # CAD prop-mount solids 103/78 and 96/83
MOTOR_POD_D_MM = 27.3          # the plastic arm-end motor pad, CAD arm section at the motor

#: ⚠ DECLARED MESH-VALIDITY GAP, not a physical claim — the same construction the repository
#:   already carries as drone_cad.PROP_STANDOFF_M (mini2 2.81, phantom3 1.55, mini5pro 1.00 mm).
#:   The P6 blade's root loft hangs up to 1.93 mm below the hub underside inside r <= 13.5 mm, so
#:   seating the hub flat on a flat-topped CAD adapter puts 304 blade triangles (0.526 % of the
#:   propeller area) inside the motor solid, against a 0.1 % budget. 1.5 mm is the smallest
#:   0.5 mm step that brings mesh_check.check_prop_bell_solid to 0.000 %. It is folded into
#:   rotor_z_mm because PROP_STANDOFF_M is a revision-0 table this revision may not edit.
PROP_STANDOFF_MM = 1.5

#: Gimbal camera block (drone_cad._gimbal_sensor_v2 arguments, metres).
GIMBAL_W_M = 0.064             # M4E-7: 0.059 -> 0.064 (owned 4E front photo, 63-65 mm)
GIMBAL_H_M = 0.0612            # unchanged
GIMBAL_D_M = 0.052             # unchanged
GIMBAL_CX_M = 0.1483           # unchanged
GIMBAL_CZ_M = -0.01036         # unchanged
GIMBAL_MOUNT_H_M = 0.047       # unchanged
GIMBAL_MOUNT_CZ_M = -0.01716   # unchanged

#: RTK turret (drone_cad._rtk_cylinder), CAD cap solids 26/122.
RTK_CX_MM = -20.2
RTK_D_BASE_MM = 40.0
RTK_D_TOP_MM = 37.4
RTK_TOP_Z_MM = 91.70
RTK_SINK_MM = 2.0              # how far the base is sunk under the built deck, so it cannot float

#: Battery pack — official size, CAD position.
BATTERY_MM = (145.47, 60.6, 46.3)
BATTERY_CENTER_MM = (70.10 - 145.47 / 2.0, 0.0, -6.14 + 46.3 / 2.0)
BATTERY_CLEARANCE_MM = 1.0
#: The internal boxes are clipped against the body shrunk inward by this much, not against the
#: body itself. Without it the clip surface is *coincident* with the shell's outer surface, and
#: then the z-buffer, PO and SBR all see internal metal exactly where the shell is: the tail face
#: of the pack came back as 223 mm2 of metal facing az 180 and the belly showed the pack through
#: the shell. The offset is a containment margin, not a dimension: the box keeps its official
#: size and its CAD position, and plan C.2 asks for exactly this (">= 1 mm clearance").
CONTAIN_INSET_MM = 1.0

#: Mainboard box — carried over from revision 0 unchanged (its size is unmeasured; see sources).
PCB_MM = (93.0, 53.6, 5.0)
PCB_CENTER_MM = (-2.9, 0.0, -12.0)

#: Ring resolution. Sized so the chord sagitta stays well under the plan's 2.58 mm ceiling while
#: the whole frame stays inside the 20,000-face budget of plan B.3.
SHELL_N_PTS = 48
NOSE_N_PTS = 36
ARM_N_PTS = 24
MOTOR_SEG = 24
DOME_RINGS = 3


# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #
def _smooth_shape(rows):
    """Smooth the shape parameters (z_mid, n_up, n_dn) of a station table; dimensions untouched.

    `z_mid` is carried as the fraction (z_mid - z_bot) / (z_top - z_bot) so the smoothing cannot
    push it outside the section. A 3-point moving average is applied once. The CAD's widest-line
    height jumps by up to 47 mm between neighbouring stations (the tail cover and the arm
    shoulder read as two different belt lines), and a loft through the raw values kinks there.
    """
    rows = [tuple(float(v) for v in r) for r in rows]
    frac = [(zm - zb) / (zt - zb) for _, _, zt, zb, zm, _, _ in rows]
    out = []
    n = len(rows)
    for i, (x, w, zt, zb, _zm, nu, nd) in enumerate(rows):
        lo, hi = max(0, i - 1), min(n - 1, i + 1)
        f = sum(frac[lo:hi + 1]) / (hi - lo + 1)
        u = sum(rows[j][5] for j in range(lo, hi + 1)) / (hi - lo + 1)
        d = sum(rows[j][6] for j in range(lo, hi + 1)) / (hi - lo + 1)
        out.append(dict(x=x, width=w, z_top=zt, z_bot=zb, z_mid=zb + f * (zt - zb),
                        n_up=u, n_dn=d))
    return out


#: ⚠ REVIEW FIX F-3 (adversarial review 2026-09-18, defects D3 and D4).
#: A sliver is a triangle whose smallest angle is under this many degrees. 1.0 deg is the value
#: the frozen threshold file names; the repository's own gate (mesh_check.SLIVER_MIN_ANGLE_DEG)
#: uses 0.5 deg, and both are measured and reported.
SLIVER_ANGLE_DEG = 1.0
#: Only an edge this short may be collapsed. The edge length is an upper bound on how far one
#: vertex moves; what the surface actually does is measured per group and recorded as
#: `max_surface_shift_mm`, because collapsing a sliver moves its vertex ALONG the sliver, which
#: already lies in the surface. Measured on this drone at 1.5 mm: body 0.329 mm, battery
#: 0.191 mm, gear 0.204 mm — at worst lambda/157 at 5.8 GHz, and 1/8 of the repository's own
#: facet rule (sagitta <= 2.58 mm).
SLIVER_MAX_EDGE_MM = 1.5
#: Hard cap on the measured surface movement. A group whose repair moves its surface further than
#: this keeps its unrepaired union. 0.5 mm is lambda/103 at 5.8 GHz.
SLIVER_MAX_SHIFT_MM = 0.5
#: A pass is kept only if the solid stays closed, consistently wound, positive, of the same
#: component count, and within this much of its volume.
SLIVER_MAX_DVOL_PCT = 0.5
SLIVER_MAX_PASSES = 8


def _sliver_counts(m):
    """(count < 0.5 deg, count < 1.0 deg, area < 0.5 deg mm2, area < 1.0 deg mm2)."""
    V = np.asarray(m.vertices, float) * 1000.0
    F = np.asarray(m.faces, np.int64)
    T = V[F]
    L = np.sort(np.stack([np.linalg.norm(T[:, 1] - T[:, 0], axis=1),
                          np.linalg.norm(T[:, 2] - T[:, 1], axis=1),
                          np.linalg.norm(T[:, 0] - T[:, 2], axis=1)], 1), 1)
    a, b, c = L[:, 0], L[:, 1], L[:, 2]
    ang = np.degrees(np.arccos(np.clip((b ** 2 + c ** 2 - a ** 2) / (2 * b * c + 1e-30),
                                       -1.0, 1.0)))
    ar = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1)
    return (int((ang < 0.5).sum()), int((ang < 1.0).sum()),
            float(ar[ang < 0.5].sum()), float(ar[ang < 1.0].sum()), ang, L)


def _collapse_pass(mesh, min_angle_deg, max_edge_mm):
    """One half-edge-collapse pass over the sliver triangles. Returns (mesh, n_collapsed)."""
    import trimesh as _tm
    V = np.asarray(mesh.vertices, float)
    F = np.asarray(mesh.faces, np.int64)
    ang = _sliver_counts(mesh)[4]
    bad = np.where(ang < float(min_angle_deg))[0]
    if not len(bad):
        return None, 0
    Vmm = V * 1000.0
    nbr = {}
    for f in F:
        for i in range(3):
            nbr.setdefault(int(f[i]), set()).update((int(f[(i + 1) % 3]), int(f[(i + 2) % 3])))
    cand = []
    for fi in bad:
        f = F[fi]
        e = sorted([(float(np.linalg.norm(Vmm[f[1]] - Vmm[f[0]])), int(f[0]), int(f[1])),
                    (float(np.linalg.norm(Vmm[f[2]] - Vmm[f[1]])), int(f[1]), int(f[2])),
                    (float(np.linalg.norm(Vmm[f[0]] - Vmm[f[2]])), int(f[2]), int(f[0]))])
        if e[0][0] <= float(max_edge_mm):
            cand.append(e[0])
    cand.sort(key=lambda t: (t[0], t[1], t[2]))
    used, remap = set(), {}
    for _L, u, v in cand:
        if u in used or v in used:
            continue
        #  Link condition for a closed 2-manifold: u and v may be merged only when they share
        #  exactly the two vertices opposite the edge. Anything else makes the mesh non-manifold.
        if len(nbr[u] & nbr[v]) != 2:
            continue
        used.add(u)
        used.add(v)
        remap[v] = u
    if not remap:
        return None, 0
    idx = np.arange(len(V))
    for v, u in remap.items():
        idx[v] = u
    F2 = idx[F]
    keep = (F2[:, 0] != F2[:, 1]) & (F2[:, 1] != F2[:, 2]) & (F2[:, 2] != F2[:, 0])
    out = _tm.Trimesh(vertices=V, faces=F2[keep], process=False)
    out.remove_unreferenced_vertices()
    out.merge_vertices()
    _tm.repair.fix_normals(out)
    if out.is_watertight and out.volume < 0:
        out.invert()
    return out, len(remap)


def _repair_slivers(mesh, group):
    """Remove the boolean's sliver triangles, or give the unrepaired union back unchanged.

    Why this exists (adversarial review 2026-09-18, defects D3 and D4). A boolean union or
    difference retriangulates every face it cuts. Where the cut runs nearly parallel to an edge of
    a large flat face — the battery pack's own 145 mm faces against the shell it almost touches,
    and the arm/shell and cradle/shell seams — the retriangulation is a fan of very thin triangles.
    The delivered revision 1 carried 370 triangles under 0.5 deg (2,294 mm2, 1.06 % of the frame
    surface) against revision 0's 95, plus 37 self-intersecting triangle pairs in the two clipped
    groups that revision 0 does not have. That is a defect of the **triangulation**, not of the
    shape, and the shape may not be changed to hide it (plan D.5.4).

    What this does: the standard half-edge collapse, restricted to sliver triangles and to edges
    at most SLIVER_MAX_EDGE_MM long, with the manifold link condition checked on every edge. It
    only ever removes triangles, so unlike a generic decimator it cannot answer a thin triangle
    with a large one. Measured on this drone: the body goes 132 -> 17 triangles under 0.5 deg and
    245 -> 11 mm2 of sliver area, with the surface moving at most 0.13 mm (lambda/398 at
    5.8 GHz) and the volume by 0.001 %.

    ⛔ It is never allowed to make things worse. A pass whose result is not closed, not
       consistently wound, of negative volume, of a different component count, more than
       SLIVER_MAX_DVOL_PCT off in volume, or worse at either sliver criterion is discarded and
       the previous mesh is kept. Every number goes into the build report.
    """
    n0_05, n0_10, a0_05, a0_10 = _sliver_counts(mesh)[:4]
    comp0 = int(len(mesh.split(only_watertight=False)))
    v0 = float(mesh.volume)
    info = dict(group=group, min_angle_deg=SLIVER_ANGLE_DEG, max_edge_mm=SLIVER_MAX_EDGE_MM,
                faces_before=int(len(mesh.faces)), slivers_before_0p5=n0_05,
                slivers_before_1p0=n0_10, sliver_area_before_0p5_mm2=round(a0_05, 4),
                sliver_area_before_1p0_mm2=round(a0_10, 4), components=comp0, passes=0,
                collapsed_edges=0)
    if n0_10 == 0:
        info.update(applied=False, why="no slivers")
        return mesh, info
    cur, total = mesh, 0
    for _p in range(SLIVER_MAX_PASSES):
        try:
            out, n = _collapse_pass(cur, SLIVER_ANGLE_DEG, SLIVER_MAX_EDGE_MM)
        except Exception as exc:                                 # pragma: no cover
            info["last_error"] = f"{type(exc).__name__}: {exc}"
            break
        if out is None or n == 0:
            break
        c05, c10 = _sliver_counts(out)[:2]
        p05, p10 = _sliver_counts(cur)[:2]
        dvol = 100.0 * (float(out.volume) - v0) / max(abs(v0), 1e-30)
        if (not out.is_watertight or not out.is_winding_consistent or float(out.volume) <= 0.0
                or abs(dvol) > SLIVER_MAX_DVOL_PCT
                or int(len(out.split(only_watertight=False))) != comp0
                or c05 > p05 or c10 > p10):
            info["stopped_because"] = (f"pass {_p + 1} would have left the solid worse "
                                       f"(closed {bool(out.is_watertight)}, wound "
                                       f"{bool(out.is_winding_consistent)}, dVol {dvol:+.4f} %, "
                                       f"slivers {p05}/{p10} -> {c05}/{c10})")
            break
        cur, total = out, total + n
        info["passes"] = _p + 1
    if total:
        import trimesh as _tm
        P = _tm.sample.sample_surface(mesh, 20000, seed=0)[0]
        shift = float(np.asarray(_tm.proximity.closest_point(cur, P)[1], float).max()) / MM
        info["max_surface_shift_mm"] = round(shift, 5)
        if shift > SLIVER_MAX_SHIFT_MM:
            info.update(applied=False, collapsed_edges=0, passes=0,
                        why=f"the repair moved the surface {shift:.3f} mm, over the "
                            f"{SLIVER_MAX_SHIFT_MM} mm cap; the unrepaired union is kept")
            return mesh, info
    n1_05, n1_10, a1_05, a1_10 = _sliver_counts(cur)[:4]
    info.update(collapsed_edges=total, faces_after=int(len(cur.faces)),
                slivers_after_0p5=n1_05, slivers_after_1p0=n1_10,
                sliver_area_after_0p5_mm2=round(a1_05, 4),
                sliver_area_after_1p0_mm2=round(a1_10, 4),
                dvolume_pct=round(100.0 * (float(cur.volume) - v0) / max(abs(v0), 1e-30), 6),
                watertight=bool(cur.is_watertight), winding=bool(cur.is_winding_consistent),
                applied=bool(total > 0), why="" if total else "no collapsible sliver edge")
    return cur, info


def _union_and_repair(A, groups, report):
    """Revision 0's own group union (`cadkit.Assembly.union_group`), then `_repair_slivers`.

    The union itself is untouched — `union_group` is the revision-0 call that
    `drone_rev.finish_frame_assembly` makes, and running it here only means that
    `finish_frame_assembly` later finds one part per group and returns immediately. What is new is
    the repair pass between the two, which is declared here and reported per group.
    """
    log = report.setdefault("sliver_repair", {})
    for g in groups:
        ms = A.parts.get(g)
        if not ms:
            continue
        A.union_group(g)
        if len(A.parts[g]) != 1:
            log[g] = dict(group=g, applied=False, why=f"the union left {len(A.parts[g])} parts")
            continue
        fixed, info = _repair_slivers(A.parts[g][0], g)
        A.parts[g] = [fixed]
        log[g] = info
    return A


def _axis_point(root_xy_z, heading_deg, z_slope, s):
    """Point at arc length `s` along an arm axis that starts at `root_xy_z` (mm)."""
    x0, y0, z0 = root_xy_z
    a = math.radians(heading_deg)
    return (x0 + s * math.cos(a), y0 + s * math.sin(a), z0 + s * z_slope)


def _arm_axis(root_mm, tip_xy_mm, tip_z_mm, inset_mm):
    """(root, tip) of one arm in mm, with the root pushed `inset_mm` inboard along the axis.

    The tip is revision 0's realized rotor centre (plan B.0 and C.3 keep rotor xy), the root is
    the CAD arm axis where it crosses the shell side. Pushing the root inboard along that same
    line puts the arm end inside the shell so the boolean union closes; it changes neither the
    heading nor the bow, and the acceptance check reads the heading and the crossing x back off
    the built part.
    """
    rx, ry, rz = root_mm
    tx, ty = tip_xy_mm
    dx, dy = tx - rx, ty - ry
    L = math.hypot(dx, dy)
    ux, uy = dx / L, dy / L
    zslope = (tip_z_mm - rz) / L
    root = (rx - inset_mm * ux, ry - inset_mm * uy, rz - inset_mm * zslope)
    return root, (tx, ty, tip_z_mm), math.degrees(math.atan2(dy, dx))


# --------------------------------------------------------------------------- #
#  The builder
# --------------------------------------------------------------------------- #
def build_frame(spec):
    """Revision-1 Matrice 4E frame → `cadkit.Assembly` (parts only; drone_rev unions them)."""
    from cadkit import Assembly, cyl
    from drone_cad import (_fisheye, _gear_arm_spikes, _gimbal_sensor_v2, _rtk_cylinder,
                           _surface_z_at, GEAR_SPIKE_H, GEAR_SPIKE_INBOARD, GEAR_TOP_Z)
    from drones import motor_angles, motor_radii
    import drone_parts_rev1 as P

    if spec.key != "matrice4e":
        raise ValueError(f"drone_rev1_matrice4e: built for 'matrice4e', got {spec.key!r}")
    if spec.envelope_mm is not None:
        raise ValueError("drone_rev1_matrice4e: revision 1 sets envelope_mm=None (plan B.0)")

    A = Assembly()
    report = {}

    # ---- M4E-2 / M4E-3 / M4E-5 : the fuselage shell -------------------------
    shell = P.section_loft_shell(
        _smooth_shape(SHELL_STATIONS), group="body", name="m4e_shell",
        n_pts=SHELL_N_PTS, cap=("dome", "dome"),
        dome_len_mm=(SHELL_TAIL_DOME_MM, SHELL_NOSE_DOME_MM), dome_rings=DOME_RINGS)
    report["shell"] = P.check_part(shell)
    A.add(shell.mesh, shell.group)

    # ---- M4E-2 : the gimbal cradle under the beak ---------------------------
    cradle = P.section_loft_shell(
        _smooth_shape(NOSE_STATIONS), group="body", name="m4e_cradle",
        n_pts=NOSE_N_PTS, cap=("dome", "dome"),
        dome_len_mm=(NOSE_TAIL_DOME_MM, NOSE_FRONT_DOME_MM), dome_rings=DOME_RINGS)
    report["cradle"] = P.check_part(cradle)
    A.add(cradle.mesh, cradle.group)

    # ---- M4E-4 : straight arms ---------------------------------------------
    angles = list(motor_angles(spec))
    radii = list(motor_radii(spec))                       # metres
    rotor_xy = [(1000.0 * r * math.cos(math.radians(a)), 1000.0 * r * math.sin(math.radians(a)))
                for a, r in zip(angles, radii)]
    arms = []
    for k, (a, xy) in enumerate(zip(angles, rotor_xy)):
        front = math.cos(math.radians(a)) > 0.0
        left = math.sin(math.radians(a)) > 0.0
        rx, ry, rz = ARM_ROOT_FRONT_MM if front else ARM_ROOT_REAR_MM
        root_mm = (rx, ry if left else -ry, rz)
        tip_z = ARM_TIP_Z_FRONT_MM if front else ARM_TIP_Z_REAR_MM
        s_root, s_mid, s_pad = ARM_SECTION_FRONT_MM if front else ARM_SECTION_REAR_MM
        root, tip, heading = _arm_axis(root_mm, xy, tip_z, ARM_ROOT_INSET_MM)
        #  REVIEW FIX F-2: one axis, two P4 segments — a shaft that keeps the CAD's near-constant
        #  section out to d = ARM_FLARE_LEN_MM from the rotor axis, then the flare to the motor
        #  pad. The junction ring is the same section, the same exponents and the same n_pts on
        #  both segments, so the two lofts meet on identical rings and the union closes on them.
        rv = np.asarray(root, float)
        tv = np.asarray(tip, float)
        Lax = float(np.linalg.norm(tv - rv))
        if Lax <= ARM_FLARE_LEN_MM + 1.0:
            raise AssertionError(f"matrice4e rev1 arm{k}: axis is only {Lax:.2f} mm long")
        joint = tuple(float(v) for v in (rv + (tv - rv) * (1.0 - ARM_FLARE_LEN_MM / Lax)))
        shaft = P.straight_arm(root, joint, s_root, s_mid, group="body", name=f"m4e_arm{k}",
                               n_up=2.0, n_dn=2.0, n_pts=ARM_N_PTS, n_sec=4)
        flare = P.straight_arm(joint, tip, s_mid, s_pad, group="body", name=f"m4e_armpad{k}",
                               n_up=2.0, n_dn=2.0, n_pts=ARM_N_PTS, n_sec=3)
        report[f"arm{k}"] = P.check_part(shaft)
        report[f"arm{k}"]["heading_deg"] = heading
        #  The acceptance reads the arm axis off this record (C.3 heading / root x / bow), so it
        #  describes the WHOLE arm: root of the shaft, tip of the flare, one straight axis.
        report[f"arm{k}"]["info"] = dict(
            shaft.info, length_mm=round(Lax, 4), heading_deg=round(heading, 4), bow_mm=0.0,
            root_mm=[round(float(v), 4) for v in rv], tip_mm=[round(float(v), 4) for v in tv],
            root_section_mm=list(s_root), mid_section_mm=list(s_mid),
            tip_section_mm=list(s_pad), flare_len_mm=ARM_FLARE_LEN_MM,
            segments=["m4e_arm%d (shaft)" % k, "m4e_armpad%d (motor pad flare)" % k])
        report[f"armpad{k}"] = P.check_part(flare)
        report[f"armpad{k}"]["info"] = flare.info
        arms += [shaft, flare]
        A.add(shaft.mesh, shaft.group)
        A.add(flare.mesh, flare.group)

    # ---- M4E-6 : motor stacks ----------------------------------------------
    for k, (xy, base_z) in enumerate(zip(rotor_xy, MOTOR_BASE_Z_MM)):
        front = math.cos(math.radians(angles[k])) > 0.0
        arm_tip_z = ARM_TIP_Z_FRONT_MM if front else ARM_TIP_Z_REAR_MM
        pod_h = base_z - arm_tip_z                         # from inside the arm pad to the bell
        parts = P.motor_can(MOTOR_CAN_D_MM, MOTOR_CAN_H_MM, MOTOR_POD_D_MM, pod_h,
                            MOTOR_ADAPTER_D_MM, MOTOR_ADAPTER_H_MM[k],
                            pod_group="body", center_xy_mm=xy, base_z_mm=arm_tip_z,
                            can_group="motor", adapter_group="motor",
                            name=f"m4e_motor{k}", seg=MOTOR_SEG)
        for p in parts:
            report[f"{p.name}"] = P.check_part(p)
            A.add(p.mesh, p.group)
        report[f"motor{k}_top_z_mm"] = parts[-1].info["adapter_top_z_mm"]

    # ---- M4E-7 : gimbal, and the sensors revision 0 already places ----------
    for g, m in _gimbal_sensor_v2(GIMBAL_W_M, GIMBAL_H_M, GIMBAL_D_M, GIMBAL_CX_M, GIMBAL_CZ_M,
                                  mount_h=GIMBAL_MOUNT_H_M, mount_cz=GIMBAL_MOUNT_CZ_M):
        A.add(m, g)
    for (cx, cy, cz) in [(0.1462, -0.0304, 0.0485), (0.1462, 0.0304, 0.0485),
                         (-0.0536, -0.03025, 0.0494), (-0.0536, 0.03025, 0.0494)]:
        for g, m in _fisheye(cx, cy, cz, 0.009):
            A.add(m, g)
    for _dx in (0.04180, -0.03514):
        _bz = _surface_z_at(A, _dx, 0.0, groups=("body",), pick="min")
        if _bz is None:
            raise AssertionError(f"matrice4e rev1 downward vision: no shell underside at "
                                 f"x = {_dx * 1000:.2f} mm")
        for g, m in _fisheye(_dx, 0.0, _bz, 0.0072):
            A.add(m, g)

    # ---- RTK turret and beacon (carried over; the turret now reaches the CAD top) ----
    deck_z = max(z for z in (_surface_z_at(A, RTK_CX_MM * MM, dy, groups=("body",), pick="max")
                             for dy in (0.0, 0.012, -0.012))
                 if z is not None)
    rtk_base_mm = deck_z / MM - RTK_SINK_MM
    A.add(_rtk_cylinder(RTK_CX_MM * MM, rtk_base_mm * MM, RTK_D_BASE_MM * MM,
                        RTK_D_TOP_MM * MM, (RTK_TOP_Z_MM - rtk_base_mm) * MM), "canopy")
    report["rtk_base_z_mm"] = rtk_base_mm
    beacon_z = _surface_z_at(A, -0.0615, 0.0, groups=("body",), pick="max")
    if beacon_z is None:
        raise AssertionError("matrice4e rev1 beacon: no deck at x = -61.5 mm")
    A.add(cyl(0.007, 0.005, center=(-0.0615, 0.0, beacon_z - 0.0015), seg=16), "accent")

    # ---- landing legs (carried over from revision 0) ------------------------
    for g, m in _gear_arm_spikes(radii, angles, GEAR_TOP_Z["matrice4e"],
                                 GEAR_SPIKE_H["matrice4e"], 0.0155, 0.0094,
                                 splay_deg=-13.4, inboard=GEAR_SPIKE_INBOARD["matrice4e"]):
        A.add(m, g)

    # ---- M4E-1 / M4E-3 : internals -----------------------------------------
    #  The plate is gone (M4E-1). The pack keeps its official size and its CAD position.
    #  ⚠ DEVIATION, declared in docs/mesh_rev1/matrice4e_sources.json row M4E-3c: the official
    #    145.47 mm pack does not fit inside the CAD-shaped shell with 1 mm clearance at the CAD
    #    bay position — the CAD shell tail ends at x = -75.59 and is narrower than the pack
    #    behind x = -68. P8 therefore clips the pack against the shell and logs the clipped
    #    volume. Nothing about the pack's sourced size or position is changed.
    import trimesh
    #  REVIEW FIX F-3: the body is unioned with revision 0's own `union_group` and then repaired
    #  once, here, so that (a) the containment clip below cuts against the repaired shell instead
    #  of against a surface carrying 196 sliver triangles, and (b) `finish_frame_assembly` later
    #  finds a single body part and its own `union_group('body')` is a no-op.
    _union_and_repair(A, ("body",), report)
    body_union = A.parts["body"][0]
    inset = body_union.copy()
    inset.vertices = inset.vertices - inset.vertex_normals * (CONTAIN_INSET_MM * MM)
    inset.merge_vertices()
    trimesh.repair.fix_normals(inset)
    if not inset.is_watertight or inset.volume <= 0:
        raise RuntimeError("drone_rev1_matrice4e: the inward-offset body is not a closed solid; "
                           "the internal boxes cannot be contained with a margin")
    report["contain_host"] = dict(inset_mm=CONTAIN_INSET_MM,
                                  body_volume_mm3=round(float(body_union.volume) / MM ** 3, 3),
                                  inset_volume_mm3=round(float(inset.volume) / MM ** 3, 3))
    batt = P.contain(BATTERY_MM, inset, group="battery", clearance_mm=BATTERY_CLEARANCE_MM,
                     name="m4e_battery", center_mm=BATTERY_CENTER_MM)
    report["battery"] = P.check_part(batt)
    report["battery"]["info"] = batt.info
    A.add(batt.mesh, batt.group)
    #  The mainboard box is carried over from revision 0 unchanged, but revision 1's shell is the
    #  CAD's, which is narrower below the belt line than revision 0's loft: the box's rear corners
    #  stand 4.8 mm outside it. It goes through the same P8 containment as the pack, with its
    #  revision-0 size and centre pinned, so it can never be metal-adjacent geometry outside the
    #  shell. Its size still has no source — see docs/mesh_rev1/matrice4e_sources.json row CARRY-3.
    pcb = P.contain(PCB_MM, inset, group="pcb", clearance_mm=BATTERY_CLEARANCE_MM,
                    name="m4e_pcb", center_mm=PCB_CENTER_MM)
    report["pcb"] = P.check_part(pcb)
    report["pcb"]["info"] = pcb.info
    A.add(pcb.mesh, pcb.group)

    #  REVIEW FIX F-3: the same union-then-repair for every other group. `body` is already done
    #  above. The group list is `drone_rev.UNION_GROUPS_REV0` plus the two internal groups, which
    #  hold one part each, so the union is a no-op for them and only the repair runs.
    _union_and_repair(A, ("motor", "camera", "gear", "canopy", "accent", "battery", "pcb"),
                      report)

    A.rev1_report = report
    return A
