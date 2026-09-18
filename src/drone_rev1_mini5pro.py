# -*- coding: utf-8 -*-
"""drone_rev1_mini5pro.py — DJI Mini 5 Pro, mesh revision 1 (plan B.4, items M5P-1 … M5P-8).

What this file is
    The frame builder behind registry entry ("mini5pro", 1) in `src/mesh_rev_mini5pro.py`.
    `drone_cad.build_frame_cad` hands any spec with `mesh_rev >= 1` to `drone_rev.build_frame_rev`,
    which resolves the entry's `frame_builder` to `build_frame` below and then applies revision 0's
    union semantics (`drone_rev.finish_frame_assembly`). The propeller comes from
    `drone_parts_rev1.propeller_rev1` (P6); nothing here builds blades.

Frames and units
    Millimetres and degrees in this file; the meshes handed to `cadkit.Assembly` are in metres
    (`MM`). +x is forward, +y is left, +z is up, and z = 0 is the arm hub plane, the same datum
    revision 0 uses.

    ⭐ **Every z here is revision 0's REALIZED z.** Revision 0 builds the frame at its raw size and
    then multiplies every z by `frame_fit_scale(spec)[2]` = 1.2985461340272204 to meet the official
    91 mm props-included height. Plan B.0 forbids that fit in a revision (`envelope_mm=None`, so
    `frame_fit_scale` is exactly (1, 1, 1)), so revision 1 carries the same factor **inside the part
    dimensions**: the realized geometry's vertical layout — shell crown and keel, arm planes, bell
    base and top, prop mount plane, foot plane — is identical to revision 0's.

    ⚠ This is the M5P-1 decision of 2026-09-17 and it is **not** a claim that the layout is right.
    The B1 height report (scratch wf/b1_height.md) found the FCC photos sufficient for bell-top,
    prop-mount and arm-tip z but **insufficient** for the stagger and the hub height, and removing
    the stretch while moving only the motor stack would leave the model 28.5 mm short of 91 mm
    because the FCC photos put the resting shell top at 89.5 mm — i.e. the height belongs to the
    shell, not to the props. Revision 1 therefore keeps revision 0's vertical layout and the
    alternative is built here as a **named ablation variant** (`build_frame_ablation_fcc_height`,
    scratch only, never registered) so the user can compare the two.

What changes in revision 1 (and what does not)
    M5P-2  shell planform: x span and width stations measured on the owned top photo; straight
           arms at the measured headings (P1 + P4).
    M5P-3  motor can Ø18.8 mm (FCC photos, B1) instead of Ø28.6 mm (0.052·diagonal).
    M5P-4  one landing leg per front motor (manual p.14 item 9, FCC photos) instead of a
           two-prong A-frame (P5).
    M5P-5  battery box at its official size 86.10 × 54.89 × 24.85 mm (manual p.86-87) (P8).
    M5P-6  **dropped** — see `SOURCES_NOT_FOUND`. The FCC front photo shows the shell's upper
           outline is a twin-peaked brow with a central saddle, not one convex section, so a
           superellipse exponent fitted to it would not measure the shape the exponent sets.
           `npow` stays at revision 0's 3.2.
    M5P-7  the two accent cylinders (Ø15.6 × 16.5 mm plastic) are not built.
    M5P-8  P6 blade orientation and `rotor_dirs` = the measured spin pattern (B1 spin report).
    Unchanged: rotor xy (bit-identical to revision 0), wheelbase, prop diameter, blade count,
    rotor count, hover rpm, `base_ang`, and every z plane (see above).

Sources
    Every number below carries its source in a comment, and the same list is in
    `docs/mesh_rev1/mini5pro_sources.json` in machine-readable form with tolerances and grades.
"""
from __future__ import annotations

import math

import numpy as np
import trimesh

MM = 1e-3

#  ⭐ revision 0's realized-to-raw vertical factor. `drones.frame_fit_scale(DRONES["mini5pro"])`
#     returns (1.0, 1.0, this) with MESH_FIX and BLADE_LAW unset (measured 2026-09-17; the value is
#     checked against a live recomputation by `check_rev0_anchors()` below, which the acceptance
#     script calls, so a drifting revision 0 cannot pass unnoticed).
REV0_SZ = 1.2985461340272204

# --------------------------------------------------------------------------- #
#  Measured inputs
# --------------------------------------------------------------------------- #
#: Top-view planform, read from the owned DJI product photo
#:   /workspace/sionna/assets/photos/mini5pro/mini 5 pro_3.png
#: registered by an Umeyama similarity fit on the four prop hubs (the hub pixels recorded in
#: `src/drones.py`'s mini5pro note, 2026-07-31 tip-midpoint construction): 3.0271 px/mm, rotation
#: 0.01°, hub residuals ≤ 2.70 mm. The body mask is the background-distance segmentation of
#: `work/measure_planform.py`; `width` is the contiguous run through y = 0 at that station.
#: ⚠ Only stations where the arm fairings do NOT merge into that run are listed. In
#:   x ∈ [−46, −18] and x ∈ [+32, +52] the arm and the shell are one run in the top view, so the
#:   shell's own width there is not measurable from this photo; P1 spans those gaps with its
#:   straight ruled band between the two measured sections either side.
#: ⚠ The photo is a product render: its front-track and rear-track scales differ by 2.6 %, which is
#:   the ±2.7 mm hub residual. Tolerance on every width and on the x span is therefore ±3 mm.
SHELL_STATIONS_MM = (
    #  x,      width
    (-50.0,    51.2),
    (-16.0,    52.8),
    (  0.0,    52.8),
    ( 14.0,    53.8),
    ( 30.0,    56.5),
    ( 54.0,    76.2),
    ( 62.0,    75.0),
    ( 70.0,    75.0),
    ( 78.0,    74.8),
    ( 86.0,    70.2),
    ( 90.0,    64.5),
)
#: Dome cap lengths (tail, nose) in mm, so the shell's realized x span is [−54.0, +92.0]. The
#: measured centreline span of the pale shell is −54.0 … ≈ +92 (the run continues to +98, but the
#: crop `work/crops/top_nose.png` shows that +93 … +98 is the black nose grille module, which is
#: built separately below).
SHELL_CAP_LEN_MM = (4.0, 2.0)
SHELL_X_SPAN_MM = (-54.0, 92.0)

#: Arm axis headings from +x, measured on the same photo.
#:
#: ⭐ 2026-09-18 REVIEW FIX — the front heading was rebuilt. The first revision-1 build used
#:   `work/arm_axis.py`, which reads only the arm's OUTER silhouette and subtracts an assumed half
#:   width (w/2)/sin θ with w = 11.6 … 16.5 mm taken from `drone_cad._ARM_WIDTH`. The band measured
#:   perpendicular to the true axis is 10.6 … 11.0 mm wide, so that subtraction over-corrects and
#:   biases θ LOW; it gave 65.34°, which the adversarial review flagged as a measurement error.
#:
#:   The value below comes from a MID-LINE estimator that uses both edges of the arm band, so the
#:   arm's own width cancels and no width assumption enters (`fix/arm_midline.py`, ledger
#:   `fix/arm_midline.json`): at 1 mm steps along a candidate axis pinned through the revision-0
#:   rotor centre, walk perpendicular to it, take the centre of the contiguous mask run, refit,
#:   iterate. 24 independent fits — 2 front rotors × 3 foreground thresholds (14/18/22 colour
#:   distance, propeller pixels rejected) × 4 station ranges (25-62, 20-50, 30-70, 28-55 mm inboard
#:   of the hub):
#:       FL 68.672° ± 0.021 (sd),  FR 69.270° ± 0.112,  both sides 68.971° ± 0.316
#:   The same reading of the rear arms gives RL 130.54° ± 1.47 and RR 130.47° ± 1.32 — a 20×
#:   larger spread, because the rear band merges into the shell — so the rear stays at 129.98°,
#:   which is inside one standard deviation and has the lowest residual of the candidates tested.
#:
#:   Perpendicular mid-offset of the band about the axis (threshold 18, 25-62 mm, rms / max, mm):
#:       front built at 65.34° → FL 2.605 / 3.625, FR 3.068 / 4.000
#:       front built at 68.97° → FL 0.209 / 0.450, FR 0.261 / 0.525    (≈ 12× better)
#:   An independent review of the same photo by a different agent gave 68.9° (68.6-69.6), and the
#:   plan's own row M5P-2 asks for 69 ± 3, so the previous "DEVIATION from the plan" is withdrawn:
#:   revision 1 now meets the plan target. Revision 0 is 56.33° (the rotor azimuth, not an arm
#:   measurement), which predicts an outer silhouette 26 mm wider than the photo at x = +46.
ARM_HEADING_DEG = dict(front=68.97, rear=129.98)

#: Arm section (width, height) in mm at root and tip, realized.
#:   width  — `drone_cad._ARM_WIDTH["mini5pro"]` = (16.5, 11.6), photo-measured 2026-07-30
#:   height — revision 0's `h_ratio` 1.55 gives height = width × 0.775 raw; × REV0_SZ realized.
ARM_SECTION_ROOT_MM = (16.5, 16.5 * 0.775 * REV0_SZ)      # (16.5, 16.605)
ARM_SECTION_TIP_MM = (11.6, 11.6 * 0.775 * REV0_SZ)       # (11.6, 11.674)

#: Motor can outer diameter [mm]. FCC SS3-MT5MFND25 external photos, fitted in the B1 height round
#: (scratch mesh_rev1/height/work/m5p_height_ledger.json, `nominal_fit.bell_dia` = 18.975 mm over
#: 4 rotors × 4 views, 120 Monte-Carlo draws). Revision 0 used 0.052 × 275 mm = Ø28.6 mm, which is
#: a diagonal proportion, not a measurement.
MOTOR_CAN_DIA_MM = 18.8
#: Motor can height [mm], realized. ⚠ **Revision-0 carry-over, no new source.** Revision 0 builds
#: the bell 0.048 × diagonal = 13.2 mm tall and then stretches it; 13.2 × REV0_SZ = 17.141 mm.
#: The FCC photos put the bell top 10–12.5 mm above the arm-tip centre, i.e. about 6 mm of visible
#: can, but that reading belongs to the un-stretched layout and is used only in the ablation.
MOTOR_CAN_H_MM = 13.2 * REV0_SZ
#: Prop adapter on top of the can: it realises revision 0's 1.0 mm raw prop standoff
#: (`drone_cad.PROP_STANDOFF_M["mini5pro"]`) so the prop hub seats with zero gap, and its diameter
#: is the propeller's own hub diameter (2 × 0.085 R = 12.954 mm), not an invented number.
PROP_ADAPTER_H_MM = 1.0 * REV0_SZ
PROP_ADAPTER_DIA_MM = 2.0 * 0.085 * 152.4 / 2.0

#: Battery pack, official size [mm]. DJI Mini 5 Pro User Manual (2025-09-11) p.86-87:
#: "86.10×54.89×24.85 mm, 71.2 g".
BATTERY_LWH_MM = (86.10, 54.89, 24.85)

#: ⭐ 2026-09-18 REVIEW FIX — where the pack sits, and which way round it lies.
#:
#: The first revision-1 build had no source for the placement at all: it ran a scan over (x, z)
#: for the position where the most of the grown box lies inside the shell, which put the pack's
#: centre at x = +38.0 mm, i.e. in the NOSE half, under the gimbal, with nothing behind x = −5.
#: The owned FCC photos put it at the tail, so the scan's answer was "where it fits", not evidence.
#:
#: What the owned photos show (FCC ID SS3-MT5MFND25 External Photos, exhibit 8307184, saved at
#: scratch mesh_0917/dji_folding/web/m5p_fcc_ext_p{2,3,5}_img*.jpeg):
#:   * p3_img1, rear view — the pack is the rearmost and lowest block of the fuselage. Its rear
#:     face is the aircraft's rear face (it carries the pack's own serial 9E8WNIFCGE001Z and the
#:     "已加密" seal), and the body's rear-bottom shelf with the USB-C and microSD ports sits
#:     directly above it. Read off a 5 px grid (`fix/p3_pack.png`), that face is 258 × 116 px, so
#:     its aspect ratio is 2.22 ± 0.05 against the official 54.89 / 24.85 = 2.209. The face that
#:     shows at the tail is therefore the 54.89 × 24.85 mm face and the 86.10 mm dimension runs
#:     FORE-AFT — which is what the L-along-x assignment above already assumed, now measured
#:     rather than assumed. (Scale on that face: 258 px / 54.89 mm = 4.70 px/mm, 116 px /
#:     24.85 mm = 4.67 px/mm — the two agree to 0.6 %, which is why the ratio is trustworthy.)
#:   * p5_img1, bottom view with the pack removed and lying beside the aircraft — the empty bay is
#:     the tail cavity between the two rear-arm roots. There is no cavity anywhere forward of it.
#:   * p2_img1, top view — the tail of the upper surface carries the DJI logo, the cooling grilles
#:     and the power button, and the fuselage ends there.
#:   * owned inventory, scratch wf/mesh_inv_mini5pro.md row 6: "the official 86.1×54.9×24.9 mm
#:     pack, which slides in from the rear".
#:
#: So the pack's REAR FACE is the shell's own tail station and the centre follows from the
#: official length. Nothing here is fitted or searched in x.
BATTERY_REAR_FACE_X_MM = SHELL_X_SPAN_MM[0]                       # −54.0
BATTERY_CX_MM = BATTERY_REAR_FACE_X_MM + 0.5 * BATTERY_LWH_MM[0]  # −10.95
#: y = 0: the bay is on the centreline in both plan views, and plan C.11 requires the symmetry
#: certificate to hold on an aircraft that is symmetric by construction.
BATTERY_CY_MM = 0.0
#: ⚠ z has NO mm source. The rear view shows the pack's underside is the fuselage belly at the
#:   tail, i.e. the pack is the lowest internal object, but it gives no number against our datum.
#:   z is therefore the one axis still chosen by a rule rather than read: a deterministic 0.5 mm
#:   scan over z alone, at the sourced x and y, for the z that puts the most of the grown box
#:   inside the shell, tie-broken toward the shell's own keel (the lower z) so the result matches
#:   what the photo shows rather than floating at mid-height. Declared in SOURCES_NOT_FOUND.
BATTERY_Z_SCAN_STEP_MM = 0.5

#: Landing gear. Manual p.14 item 9 "Landing Gears (Built-in antennas)", one per FRONT motor, and
#: FCC photos p4_img1 / p2_img2 show one flat strut per front arm and none at the rear.
#: ⚠ The strut's own section and its 31 mm raw depth are revision-0 carry-overs (spec
#:   `gear_h_mm` = 31.0, `drone_cad.GEAR_LEG_W_M` default arm_r1 × 0.62); revision 1 changes the
#:   COUNT (2 prongs → 1) and nothing else about the leg.
LEG_N_PER_FRONT_ARM = 1

#: Gimbal block, mm. Sizes are the photo-measured design values in
#: `drone_cad._gimbal_compact3`'s docstring ("폭 ≈50 mm, 높이 ≈33 mm, 앞뒤 ≈30 mm", from
#: assets/photos/mini5pro/mini 5 pro_1.png, 2026-07-30 round). Revision 0 stretched the 33 mm to
#: 42.85 mm; revision 1 uses the measured 33 mm, which is the one dimension of the vertical layout
#: that has its own measurement.
GIMBAL_WHD_MM = (50.0, 33.0, 30.0)
GIMBAL_LENS_DIA_MM = 2.0 * 33.0 * 0.26        # revision 0's lens cylinder radius h·0.26
GIMBAL_LENS_LEN_MM = 30.0 * 0.22              # revision 0's lens cylinder length d·0.22
#: Gimbal centre z [mm], realized — revision-0 carry-over (cz = −0.30 · bh · REV0_SZ).
GIMBAL_CZ_MM = -0.30 * 45.045 * REV0_SZ
#: Official folded envelope, props off: 157 × 95 × 68 mm (https://www.dji.com/global/mini-5-pro/specs).
#: Revision 0's own shell table reads the folded length as "shell length + gimbal front
#: protrusion"; revision 1 uses the same reading to place the gimbal: the lens front sits at
#: shell tail + 157.0 mm.
FOLDED_L_MM = 157.0

#: Nose grille (the black ribbed module at the nose). Width measured on the top photo at x = +94:
#: 31.2 mm; it runs from about x = +88 (inside the shell) to x = +98 (the forward-most point of the
#: airframe outline). Its height is revision 0's realized 24.0 × REV0_SZ mm and its centre z is
#: revision 0's −0.06 · bh · REV0_SZ — both carry-overs.
GRILLE_W_MM = 31.2
GRILLE_D_MM = 10.0
GRILLE_CX_MM = 93.0
GRILLE_H_MM = 24.0 * REV0_SZ
GRILLE_CZ_MM = -0.06 * 45.045 * REV0_SZ

#: Vision sensors (6 fisheyes + LiDAR): revision 0's radius and its placement rule, re-evaluated on
#: revision 1's shell — each one is pushed out along its own axis until it meets the shell surface,
#: which is what revision 0's comment says it does ("본체 표면 밀착"). No new dimension is claimed.
FISHEYE_R_MM = 8.0
FISHEYE_LAT_MM = 0.26 * 74.1195               # revision 0's ±0.26 · bw
FISHEYE_LAT_REAR_MM = 0.24 * 74.1195
FISHEYE_FRONT_Z_MM = 0.06 * 45.045 * REV0_SZ
FISHEYE_REAR_Z_MM = 0.30 * 45.045 * REV0_SZ
FISHEYE_BELLY_X_MM = 0.20 * 92.0
LIDAR_W_MM = 8.0
LIDAR_Z_MM = 0.14 * 45.045 * REV0_SZ

#: Targets the plan asked for that this file does NOT implement, and why. Printed by the
#: acceptance script so the gap is never silent.
SOURCES_NOT_FOUND = {
    "M5P-1": "Removing the ×1.2986 height stretch. B1 (wf/b1_height.md): the FCC photos fix "
             "bell-top and prop-mount z (±1.5 mm) and arm-tip z (±3 mm) but NOT the front/rear "
             "stagger (±13 mm) or the hub height, and the un-stretched model would stand 28.5 mm "
             "short of 91 mm. Revision 1 keeps revision 0's vertical layout; the alternative is "
             "`build_frame_ablation_fcc_height`, scratch only.",
    "M5P-6": "Superellipse exponent by FCC overlay IoU. The FCC front photo "
             "(m5p_fcc_ext_p4_img1.jpeg, crop work/crops/front_shell_top.png) shows the shell's "
             "upper outline is two brow pods with a saddle between them, not one convex section, "
             "so an exponent fitted to that outline would not measure what the exponent sets. "
             "npow stays at revision 0's 3.2 for both halves.",
    "motor can height": "No FCC reading of the can height alone. Revision 0's 13.2 mm raw "
                        "(× REV0_SZ = 17.141 mm realized) is carried over.",
    "shell width, x ∈ [−46, −18] and [+32, +52]": "The arm fairings and the shell are one run in "
                                                  "the top view there. P1's straight ruled band "
                                                  "between the measured sections either side is "
                                                  "used; nothing is invented.",
    "leg section and depth": "No FCC reading. Revision 0's prong section and 31.0 mm raw depth "
                             "are carried over; only the count changes (2 → 1).",
    "battery placement, z only": "The FCC rear view (p3_img1) and bottom view with the pack "
                                 "removed (p5_img1) fix the pack's fore-aft station (its rear "
                                 "face is the aircraft's rear face) and its centreline, and the "
                                 "rear view's 258 x 116 px face confirms the 54.89 x 24.85 mm "
                                 "face shows at the tail. Neither gives a z against our datum, "
                                 "so z alone is chosen by a deterministic 0.5 mm scan for the "
                                 "most containment, tie-broken toward the keel. 2026-09-18 "
                                 "review fix: x and y are no longer scanned.",
}


# --------------------------------------------------------------------------- #
#  Revision 0's vertical layout, read back from revision 0's own code
# --------------------------------------------------------------------------- #
def _rev0_shell_mesh():
    """Revision 0's shell loft, with its realized (stretched) z — built by revision 0's own code.

    This is the single source of revision 1's vertical section law: revision 1 keeps revision 0's
    (z_top, z_bot) as a function of **normalized fore-aft position** and replaces only the planform.
    Reading it from `drone_cad._body_folding` instead of copying a table means a change in revision
    0's shell table cannot silently desynchronise revision 1 — the fingerprint guard catches it.
    """
    import drone_cad as dc
    from drones import DRONES
    spec0 = DRONES["mini5pro"]
    sh = dc._SHELL_SHAPE["mini5pro"]
    bl = spec0.body_l_mm * sh["fl"] / 1000.0
    bw = spec0.body_w_mm * sh["fw"] / 1000.0
    bh = spec0.body_h_mm * sh["fh"] / 1000.0
    m = dc._body_folding(bl, bw, bh, nose_drop=sh["ndrop"], n_pow=sh["npow"],
                         hw_f=sh["hw"], hh_f=sh["hh"], zo_f=sh["zo"],
                         smooth_iters=sh.get("smooth_iters", 4))
    V = np.asarray(m.vertices, float).copy()
    V[:, 2] *= REV0_SZ
    return trimesh.Trimesh(vertices=V, faces=np.asarray(m.faces).copy(), process=False), sh


def _rev0_section_law(n=61):
    """(x0_mm, z_top_mm, z_bot_mm) of revision 0's realized shell, sampled on a fixed grid."""
    m0, _ = _rev0_shell_mesh()
    V = np.asarray(m0.vertices, float) * 1000.0
    x_lo, x_hi = float(V[:, 0].min()), float(V[:, 0].max())
    xs = np.linspace(x_lo + 0.05, x_hi - 0.05, int(n))
    rows = []
    for x in xs:
        s = m0.section(plane_origin=[x * MM, 0, 0], plane_normal=[1, 0, 0])
        if s is None:
            continue
        P = np.asarray(s.vertices, float) * 1000.0
        rows.append((float(x), float(P[:, 2].max()), float(P[:, 2].min())))
    return np.asarray(rows, float), (x_lo, x_hi)


#: Revision 0's realized vertical layout, in mm, at the datum z = 0 = arm hub plane. Every one of
#: these is `<revision-0 raw value> × REV0_SZ`, i.e. exactly what revision 0's meshes realize.
#: `check_rev0_anchors()` recomputes them from the live revision-0 code and refuses a mismatch.
Z = dict(
    arm_root_front=(-7.0) * REV0_SZ,                       # _arm_folding z0 = rotor_z_mm
    arm_root_rear=(+7.0) * REV0_SZ,
    arm_tip_front=(0.012 * 275.0 - 7.0) * REV0_SZ,         # _arm_folding z1 = 0.012·diag + dz
    arm_tip_rear=(0.012 * 275.0 + 7.0) * REV0_SZ,
    bell_base_front=(0.014 * 275.0 - 7.0) * REV0_SZ,       # MOTOR_BASE_Z default + dz
    bell_base_rear=(0.014 * 275.0 + 7.0) * REV0_SZ,
    # front arm underside at the tip, where the leg hangs from (drone_cad's z_arm expression)
    leg_top=(0.012 * 275.0 - (11.6 / 2.0) * 1.55 / 2.0 - 7.0) * REV0_SZ,
    leg_depth=31.0 * REV0_SZ,                              # spec.gear_h_mm
)
#: Revision 0's realized prop mount z per rotor (rotor_deg order FL, RL, RR, FR) — plan C.3 keeps
#: the rotor xy bit-identical, and this file keeps the rotor z identical too.
ROTOR_MOUNT_Z_MM = tuple(
    ((0.014 * 275.0 + 0.048 * 275.0 + 1.0) + dz) * REV0_SZ for dz in (-7.0, +7.0, +7.0, -7.0))
#: Revision 0's realized frame floor (the foot of the landing gear) and prop top, which together
#: make the official 91.0 mm props-included height. Revision 1 must land on the same two planes.
REV0_FRAME_MIN_Z_MM = -51.6145
REV0_TOTAL_H_MM = 91.0


def check_rev0_anchors(tol_mm=5e-4) -> dict:
    """Recompute every revision-0 anchor from the live revision-0 code and compare (C.3 input)."""
    from drones import DRONES, frame_fit_scale, build_frame, rotor_layout
    import drone_cad as dc
    spec0 = DRONES["mini5pro"]
    sz = float(frame_fit_scale(spec0)[2])
    V = np.asarray(build_frame(spec0).v, float) * 1000.0
    rl0 = rotor_layout(spec0)
    got = dict(sz=sz, frame_min_z_mm=float(V[:, 2].min()),
               mount_z_mm=[float(d["center"][2]) * 1000.0 for d in rl0],
               rotor_xy_mm=[[float(d["center"][0]) * 1000.0, float(d["center"][1]) * 1000.0]
                            for d in rl0],
               bell_top_raw_m=float(dc.motor_bell_top_z_m(spec0, spec0.diagonal_mm / 1000.0)),
               standoff_raw_m=float(dc.PROP_STANDOFF_M.get("mini5pro", 0.0)))
    bad = []
    if abs(sz - REV0_SZ) > 1e-12:
        bad.append(f"frame_fit_scale sz {sz!r} != REV0_SZ {REV0_SZ!r}")
    if abs(got["frame_min_z_mm"] - REV0_FRAME_MIN_Z_MM) > 1e-3:
        bad.append(f"revision-0 frame floor {got['frame_min_z_mm']:.4f} != {REV0_FRAME_MIN_Z_MM}")
    for k, (want, gotz) in enumerate(zip(ROTOR_MOUNT_Z_MM, got["mount_z_mm"])):
        if abs(want - gotz) > tol_mm:
            bad.append(f"rotor {k} mount z {gotz:.4f} != {want:.4f}")
    got["ok"] = not bad
    got["problems"] = bad
    return got


# --------------------------------------------------------------------------- #
#  Geometry helpers
# --------------------------------------------------------------------------- #
def _interp_section_law(law, x_span, x_mm):
    """(z_top, z_bot) of revision 0's realized shell at the normalized position of `x_mm`.

    Revision 1's shell spans SHELL_X_SPAN_MM; revision 0's spans `x_span`. The station's
    normalized fore-aft position u is carried across, so revision 1's shell has revision 0's
    height law at every fraction of its length. Nothing is interpolated beyond revision 0's own
    sampled section curve.
    """
    lo, hi = SHELL_X_SPAN_MM
    u = (float(x_mm) - lo) / (hi - lo)
    x0 = x_span[0] + u * (x_span[1] - x_span[0])
    z_top = float(np.interp(x0, law[:, 0], law[:, 1]))
    z_bot = float(np.interp(x0, law[:, 0], law[:, 2]))
    return z_top, z_bot


def _shell_stations(law, x_span, npow=3.2):
    st = []
    for x, w in SHELL_STATIONS_MM:
        z_top, z_bot = _interp_section_law(law, x_span, x)
        st.append(dict(x=float(x), width=float(w), z_top=z_top, z_bot=z_bot,
                       z_mid=0.5 * (z_top + z_bot), n_up=float(npow), n_dn=float(npow)))
    return st


def _ablation_stations(npow=3.2):
    """Ablation variant: the shell placed and tilted per the FCC outline (see module docstring).

    z_top(x) = SHELL_TOP_AT_FRONT_ROW − tan(20°)·(x_front_row − x), clamped forward of the front
    motor row, and a constant shell height of 45.05 mm (the photo-measured design value in
    `outputs/mesh_inspect_body_arms_0816.json`). The frame's foot plane is unchanged, so the
    resting shell top reaches 89.5 mm above the feet.
    ⚠ Only the TOP outline and the 45.05 mm height have a source. The keel profile, the constant
      20° slope over the whole length and the constant height are this variant's assumptions.
    """
    x_row = 75.804                       # front rotor row: B1 puts the outline peak here
    z_top_row = 89.5 + REV0_FRAME_MIN_Z_MM       # 89.5 mm above the feet
    slope = math.tan(math.radians(20.0))
    #  ⚠ B1's fitted top profile stops about 85 mm behind the peak (its last station is 59.0 mm
    #  above the table). Extrapolating the 20° slope over the remaining 44 mm of our shell put the
    #  tail keel 3 mm BELOW the landing feet, which is an artefact of the extrapolation, not a
    #  measurement. The slope is therefore clamped at the last measured station.
    x_last = x_row - 85.4
    st = []
    for x, w in SHELL_STATIONS_MM:
        z_top = z_top_row - slope * min(85.4, max(0.0, x_row - x))
        st.append(dict(x=float(x), width=float(w), z_top=z_top, z_bot=z_top - 45.045,
                       z_mid=z_top - 0.5 * 45.045, n_up=float(npow), n_dn=float(npow)))
    return st


def _rotor_xy(spec):
    """Revision 0's realized rotor centres (x, y) in mm — plan C.3 requires them bit-identical."""
    from drones import motor_angles, motor_radii
    out = []
    for ang, r in zip(motor_angles(spec), motor_radii(spec)):
        ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        out.append((r * 1000.0 * ca, r * 1000.0 * sa, ang))
    return out


def _march_root(tip_xy, heading_deg, shell_mesh, bury_mm=10.0, step=0.5, max_mm=140.0):
    """Walk back from the arm tip along the heading until inside the shell, then `bury_mm` more."""
    d = np.array([math.cos(math.radians(heading_deg)), math.sin(math.radians(heading_deg))])
    t = 0.0
    z = 0.0
    while t < max_mm:
        t += step
        p = np.array([tip_xy[0], tip_xy[1]]) - d * t
        q = np.array([[p[0] * MM, p[1] * MM, z * MM]])
        if bool(shell_mesh.contains(q)[0]):
            return float(t + bury_mm)
    raise RuntimeError(f"drone_rev1_mini5pro: the arm at heading {heading_deg}° from "
                       f"{tip_xy} never reaches the shell")


def _battery_centre(shell_mesh, box_lwh_mm, clearance_mm=1.0, step_mm=None,
                    cx_mm=None, cy_mm=None):
    """Placement of the internal pack: x and y from the owned photos, z by a 1-D scan.

    ⭐ 2026-09-18 REVIEW FIX. This used to scan (x, z) for the position where the most of the
    grown box lies inside the shell — "where it fits" — which put the pack 40.8 mm forward of
    revision 0's centre, into the nose half, against the owned FCC photos. x is now fixed by
    `BATTERY_CX_MM` (the pack's rear face is the aircraft's rear face, p3_img1/p5_img1) and y by
    `BATTERY_CY_MM` (the centreline), and only z is searched, because z is the one axis the
    photos do not give a number for.

    The z score is the fraction of the grown box's probe points (corners, edge midpoints, face
    centres and a light grid — the same probe set P8 uses) that lie inside the shell. Ties are
    broken toward the LOWER z, because the rear view shows the pack's underside is the fuselage
    belly at the tail. The result is recorded in the parts log and printed by the acceptance run.
    """
    L, W, H = (float(v) for v in box_lwh_mm)
    step = float(BATTERY_Z_SCAN_STEP_MM if step_mm is None else step_mm)
    cx = float(BATTERY_CX_MM if cx_mm is None else cx_mm)
    cy = float(BATTERY_CY_MM if cy_mm is None else cy_mm)
    g = np.array([[a, b, c] for a in (-0.5, 0.0, 0.5) for b in (-0.5, 0.0, 0.5)
                  for c in (-0.5, 0.0, 0.5)], float)
    extra = []
    for a in (-0.5, -0.25, 0.0, 0.25, 0.5):
        for b in (-0.5, -0.25, 0.0, 0.25, 0.5):
            extra += [[a, b, -0.5], [a, b, 0.5], [a, -0.5, b], [a, 0.5, b],
                      [-0.5, a, b], [0.5, a, b]]
    G = np.unique(np.vstack([g, np.asarray(extra, float)]), axis=0)
    G = G * np.array([L + 2 * clearance_mm, W + 2 * clearance_mm, H + 2 * clearance_mm])[None, :]
    lo, hi = np.asarray(shell_mesh.bounds, float) / MM
    best = (-1.0, 1e18, None)
    for z in np.arange(lo[2], hi[2] + 1e-9, step):
        c = np.array([cx, cy, float(z)])
        f = float(shell_mesh.contains((G + c[None, :]) * MM).mean())
        if (f > best[0] + 1e-12) or (abs(f - best[0]) <= 1e-12 and z < best[1]):
            best = (f, float(z), c)
    return tuple(round(float(v), 4) for v in best[2])


def _section_z(mesh, x_mm, frac):
    """z at a fraction of the shell's own section at station `x_mm` (0 = widest line, 1 = crown).

    Negative fractions run down toward the keel. Reading the seed from the local section is what
    lets one placement rule serve both the default shell and the tilted ablation shell.
    """
    s = mesh.section(plane_origin=[float(x_mm) * MM, 0, 0], plane_normal=[1, 0, 0])
    if s is None:
        raise RuntimeError(f"drone_rev1_mini5pro: the shell has no section at x = {x_mm} mm")
    P = np.asarray(s.vertices, float) / MM
    z_top, z_bot = float(P[:, 2].max()), float(P[:, 2].min())
    z_mid = 0.5 * (z_top + z_bot)
    return z_mid + float(frac) * ((z_top - z_mid) if frac >= 0 else (z_mid - z_bot))


def _surface_point(mesh, origin_mm, direction, max_mm=250.0):
    """Where a ray leaves `mesh` — used to sit the vision sensors flush on the shell."""
    o = np.asarray(origin_mm, float)[None, :] * MM
    d = np.asarray(direction, float)[None, :]
    loc, _, _ = mesh.ray.intersects_location(ray_origins=o, ray_directions=d)
    if len(loc) == 0:
        raise RuntimeError(f"drone_rev1_mini5pro: no shell surface from {origin_mm} along "
                           f"{direction}")
    t = ((loc - o[0]) @ d[0])
    return np.asarray(loc[int(np.argmax(t))], float) / MM


# --------------------------------------------------------------------------- #
#  The frame
# --------------------------------------------------------------------------- #
def _build(spec, stations, parts_log):
    from cadkit import Assembly, box, cyl, sphere
    import drone_parts_rev1 as P
    import drone_cad as dc

    A = Assembly()
    rec = []

    def take(part, group=None):
        chk = P.check_part(part)
        chk["group"] = group or part.group
        chk["info"] = dict(part.info)
        rec.append(chk)
        if not chk["ok"]:
            raise RuntimeError(f"drone_rev1_mini5pro: part {part.name!r} failed check_part: {chk}")
        A.add(part.mesh, group or part.group)
        return part

    # ---- P1 shell ---------------------------------------------------------- #
    shell = P.section_loft_shell(stations, group="body", name="shell",
                                 cap=("dome", "dome"), dome_len_mm=SHELL_CAP_LEN_MM,
                                 sagitta_mm=1.0)
    take(shell)
    shell_m = shell.mesh

    # ---- P4 arms ----------------------------------------------------------- #
    rot = _rotor_xy(spec)
    arms = []
    for k, (rx, ry, ang) in enumerate(rot):
        front = math.cos(math.radians(ang)) > 0
        hdg = ARM_HEADING_DEG["front"] if front else ARM_HEADING_DEG["rear"]
        hdg = hdg if ry >= 0 else -hdg          # mirror for the right-hand side
        z_tip = Z["arm_tip_front"] if front else Z["arm_tip_rear"]
        z_root = Z["arm_root_front"] if front else Z["arm_root_rear"]
        L = _march_root((rx, ry), hdg, shell_m)
        d = np.array([math.cos(math.radians(hdg)), math.sin(math.radians(hdg))])
        root = (rx - d[0] * L, ry - d[1] * L, z_root)
        arm = P.straight_arm(root, (rx, ry, z_tip), ARM_SECTION_ROOT_MM, ARM_SECTION_TIP_MM,
                             group="body", name=f"arm{k}", n_sec=6, sagitta_mm=1.0)
        take(arm)
        arms.append(arm)

    # ---- P3 motor stacks --------------------------------------------------- #
    pods = []
    for k, (rx, ry, ang) in enumerate(rot):
        front = math.cos(math.radians(ang)) > 0
        z_tip = Z["arm_tip_front"] if front else Z["arm_tip_rear"]
        z_base = Z["bell_base_front"] if front else Z["bell_base_rear"]
        pod_bot = z_tip - 0.5 * ARM_SECTION_TIP_MM[1]          # the arm underside at the tip
        parts = P.motor_can(MOTOR_CAN_DIA_MM, MOTOR_CAN_H_MM,
                            ARM_SECTION_TIP_MM[0], max(0.5, z_base - pod_bot),
                            PROP_ADAPTER_DIA_MM, PROP_ADAPTER_H_MM,
                            pod_group="body", center_xy_mm=(rx, ry), base_z_mm=pod_bot,
                            pod_taper=1.0, name=f"motor{k}", sagitta_mm=1.0)
        for p in parts:
            take(p)
        pods.append(parts[0])
        top = parts[0].info["adapter_top_z_mm"]          # P3 rounds this to 4 decimals
        if abs(top - ROTOR_MOUNT_Z_MM[k]) > 1e-3:
            raise RuntimeError(f"drone_rev1_mini5pro: rotor {k} motor stack top {top:.6f} mm != "
                               f"revision-0 prop mount z {ROTOR_MOUNT_Z_MM[k]:.6f} mm")

    # ---- P5 legs (one per front motor) ------------------------------------- #
    for k, (rx, ry, ang) in enumerate(rot):
        ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        if ca <= 1e-9:
            continue
        spread = 0.95 * 0.5 * MOTOR_CAN_DIA_MM         # revision 0's `spread = mot_r · 0.95`
        w = (11.6 / 2.0) * 0.62                        # revision 0's `arm_r1 · 0.62`
        root_sec = (2.0 * w, 1.7 * w * REV0_SZ)
        tip_sec = (2.0 * w * 0.45, 1.7 * w * 0.45 * REV0_SZ)
        #  ⚠ The host must be ONE solid. A concatenation of the overlapping arm and pod is not a
        #  volume, and cutting against it left 4 needle faces whose shortest edge (0.283 mm)
        #  exceeds cadkit's 0.25 mm collapse cap, so the canonical i5 repair fell back to deleting
        #  them and opened the leg — and only on one of the two rotors (work/dbg_leg.py).
        host = trimesh.boolean.union([arms[k].mesh, pods[k].mesh], engine="manifold")
        z_foot = Z["leg_top"] - Z["leg_depth"]
        #  The path starts 2.0 mm above the pod's bottom face, so the whole top cap is well inside
        #  the host and away from any face of it. A cap that pokes past the pod top survives the
        #  difference as a second piece, and a cap that lands on the pod's mid-height left a
        #  zero-volume boolean shard on one of the two rotors (measured, work/dbg_leg.py).
        z_start = (Z["arm_tip_front"] - 0.5 * ARM_SECTION_TIP_MM[1]) + 2.0
        for _pass in range(2):
            leg = P.attached_leg([[rx, ry, z_start],
                                  [rx + 0.5 * spread * ca, ry + 0.5 * spread * sa,
                                   0.5 * (z_start + z_foot)],
                                  [rx + spread * ca, ry + spread * sa, z_foot]],
                                 root_sec, tip_sec, group="gear", host=host,
                                 name=f"leg{k}", n_sec=8, declare_components=1, sagitta_mm=1.0)
            low = float(np.asarray(leg.mesh.vertices)[:, 2].min()) / MM
            if abs(low - REV0_FRAME_MIN_Z_MM) < 1e-4:
                break
            z_foot += (REV0_FRAME_MIN_Z_MM - low)
        take(leg)

    # ---- P7 gimbal --------------------------------------------------------- #
    w_g, h_g, d_g = GIMBAL_WHD_MM
    cx = (SHELL_X_SPAN_MM[0] + FOLDED_L_MM) - (0.5 * d_g + GIMBAL_LENS_LEN_MM)
    gim = P.gimbal_block(w_g, h_g, d_g, GIMBAL_LENS_DIA_MM, GIMBAL_LENS_LEN_MM,
                         group="camera", center_xyz_mm=(cx, 0.0, GIMBAL_CZ_MM),
                         name="gimbal", corner_r_mm=2.0, sagitta_mm=1.0)
    for p in gim:
        take(p)

    # ---- nose grille, vision sensors (revision-0 shapes on revision 1's shell) ---- #
    for g, m in dc._nose_grille(GRILLE_CX_MM * MM, GRILLE_CZ_MM * MM,
                                GRILLE_W_MM * MM, GRILLE_H_MM * MM, GRILLE_D_MM * MM):
        A.add(m, g)
    #  Each sensor is seeded inside the shell at a station and at a fraction of that station's own
    #  section, then pushed out along its axis to the shell surface. The fractions reproduce
    #  revision 0's absolute placement on revision 1's default shell; expressing them against the
    #  local section is what lets the same rule work on the tilted ablation shell.
    x_lo, x_hi = SHELL_X_SPAN_MM
    x_front, x_rear = x_hi - 10.0, x_lo + 10.0
    sensors = []
    for sy in (+1.0, -1.0):
        sensors.append(("front", _surface_point(
            shell_m, (x_front, sy * FISHEYE_LAT_MM,
                      _section_z(shell_m, x_front, 0.46)), (1, 0, 0))))
        sensors.append(("rear", _surface_point(
            shell_m, (x_rear, sy * FISHEYE_LAT_REAR_MM,
                      _section_z(shell_m, x_rear, 0.65)), (-1, 0, 0))))
        sensors.append(("belly", _surface_point(
            shell_m, (FISHEYE_BELLY_X_MM, sy * FISHEYE_LAT_REAR_MM,
                      _section_z(shell_m, FISHEYE_BELLY_X_MM, 0.0)), (0, 0, -1))))
    for nm, q in sensors:
        axis = "x" if nm in ("front", "rear") else "z"
        for g, m in dc._fisheye(q[0] * MM, q[1] * MM, q[2] * MM, FISHEYE_R_MM * MM, axis=axis):
            A.add(m, g)
    pl = _surface_point(shell_m, (x_front, 0.0, _section_z(shell_m, x_front, 0.678)), (1, 0, 0))
    for g, m in dc._lidar(pl[0] * MM, pl[2] * MM, LIDAR_W_MM * MM):
        A.add(m, g)

    # ---- P8 internals ------------------------------------------------------ #
    #  ⚠ P8's own coordinate descent searches all three axes and put the pack 3.8 mm off the
    #  centreline, which breaks the symmetry certificate of plan C.11 on an aircraft that is
    #  symmetric by construction, so the centre is chosen here and P8 is called with it pinned.
    #  ⭐ 2026-09-18 REVIEW FIX: x and y now come from the owned FCC photos (the pack's rear face
    #  is the aircraft's rear face, on the centreline) instead of from a fit-inside-the-shell
    #  scan; only z is still scanned. See BATTERY_CX_MM above.
    bc = _battery_centre(shell_m, BATTERY_LWH_MM, clearance_mm=1.0)
    batt = P.contain(BATTERY_LWH_MM, shell, group="battery", clearance_mm=1.0, name="battery",
                     center_mm=bc, declare_components=1)
    take(batt)
    #  ⛔ M5P-9 — revision 0's magnesium structural plate is NOT built. It is a proportional box
    #  (0.58·bl × 0.68·bw × 0.08·bh = 80.0 × 50.4 × 4.7 mm) with no owned source, and on the
    #  revision-1 shell it no longer even fits: only 57 % of its vertices are inside, because the
    #  measured shell waist is 52.8 mm wide against revision 0's 70.4 mm. Plan B.0 forbids a
    #  dimension without an owned source, so it goes rather than being resized by guesswork.
    #  The PCB box is a revision-0 carry-over at revision 0's realized size and position; it is
    #  inside the revision-1 shell with 4.0 mm of clearance (measured).
    bl0, bw0, bh0 = 137.955, 74.1195, 45.045
    A.add(box(bl0 * 0.38 * MM, bw0 * 0.54 * MM, bh0 * 0.06 * REV0_SZ * MM,
              center=(0.02 * bl0 * MM, 0.0, 0.26 * bh0 * REV0_SZ * MM)), "pcb")

    parts_log.extend(rec)
    parts_log.append(dict(name="battery_placement", plan_item="P8", group="battery",
                          info=batt.info))
    return A


def build_frame(spec):
    """Registry `frame_builder` for ("mini5pro", 1) — plan B.4, default (M5P-1 = keep the layout)."""
    law, x_span = _rev0_section_law()
    log = []
    A = _build(spec, _shell_stations(law, x_span), log)
    A.mesh_rev1_parts = log
    return A


def build_frame_ablation_fcc_height(spec):
    """⚠ Scratch-only ablation: the shell placed and tilted per the FCC outline (M5P-1 alternative).

    Never registered. `benchmark/mesh_rev1_acceptance.py --drone mini5pro --variant fcc_height`
    builds it and records its own acceptance numbers; no shard may ever carry its name.
    """
    log = []
    A = _build(spec, _ablation_stations(), log)
    A.mesh_rev1_parts = log
    A.mesh_rev1_variant = "fcc_height"
    return A
