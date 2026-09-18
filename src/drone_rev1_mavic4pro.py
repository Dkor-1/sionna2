# -*- coding: utf-8 -*-
"""drone_rev1_mavic4pro.py — DJI Mavic 4 Pro, mesh revision 1 (plan B.6 mavic4pro row).

What this file is
    The frame builder behind registry entry ("mavic4pro", 1) in `src/mesh_rev_mavic4pro.py`.
    `drone_cad.build_frame_cad` hands any spec with `mesh_rev >= 1` to `drone_rev.build_frame_rev`,
    which resolves the entry's `frame_builder` to `build_frame` below and then applies revision 0's
    union semantics (`drone_rev.finish_frame_assembly`). The propeller comes from
    `drone_parts_rev1.propeller_rev1` (P6); nothing here builds blades.

Frames and units
    Millimetres and degrees in this file; the meshes handed to `cadkit.Assembly` are in metres
    (`MM`). +x is forward, +y is left, +z is up, and z = 0 is the arm hub plane, the same datum
    revision 0 uses.

    ⭐ **Every z here is revision 0's REALIZED z.** Revision 0 builds the frame at its raw size and
    then multiplies every z by `frame_fit_scale(spec)[2]` = 1.59766775121646 to meet the official
    135.2 mm unfolded height. Plan B.0 forbids that fit in a revision (`envelope_mm=None`, so
    `frame_fit_scale` is exactly (1, 1, 1)), so revision 1 carries the same factor **inside the
    part dimensions**: the realized vertical layout — shell crown and keel, arm planes, bell base
    and top, prop mount plane, foot plane, gimbal floor — is identical to revision 0's.

    ⚠ This is the 2026-09-18 decision for this aircraft and it is **not** a claim that the layout
    is right. The B1 height report (scratch wf/b1_height.md) fitted the FCC elevation photos with
    their steel rules and found the tallest resting feature is about 100 mm, so removing the
    ×1.598 stretch would leave the model **≈35 mm short (95 %: 32.7–37.3 mm)** of the official
    135.2 mm and **no measured feature carries that 35 mm**. Revision 1 therefore keeps revision
    0's vertical layout and records the shortfall, exactly as mini5pro does. The same report's
    measured z values are carried in `HEIGHT_SHORTFALL` below and printed by the acceptance
    script, so the error is never silent.

What changes in revision 1 (and what does not)
    M4P-1  shell planform: x span and width stations measured on the owned top photo; the shell
           moves 39.0 mm forward and loses 26–49 mm of width (P1).
    M4P-2  motor can Ø29.33 mm (B1's ruler-scaled FCC fit) instead of Ø45.86 mm (0.052·diagonal
           used as a radius). The can height is revision 0's realized carry-over (P3).
    M4P-3  the gimbal moves out in front of the nose, where every owned photo puts it, and takes
           its measured size instead of revision 0's sphere (P7).
    M4P-4  one tapered landing leg per FRONT motor instead of a two-prong A-frame, with the foot
           at B1's measured position (P5).
    M4P-5  internal battery box at its official size 128 × 62 × 44 mm (manual p.88) placed at the
           tail, where the bottom-plan and teardown photos put the pack (P8).
    M4P-6  straight arms at the measured headings, 13–14 mm wide instead of 18.5–26.5 mm (P4).
    M4P-7  `rotor_dirs` = the measured spin pattern (B1 spin report, grade **high** for this
           aircraft: FL and RR clockwise seen from above).
    M4P-8  P6 blade orientation — the raised, thick edge leads for each rotor's own rotation.
    Unchanged: rotor xy (bit-identical to revision 0), wheelbase, prop diameter, blade count,
    rotor count, hover rpm, `base_ang`/`rotor_deg`, and every z plane (see above).

Sources
    Every number below carries its source in a comment, and the same list is in
    `docs/mesh_rev1/mavic4pro_sources.json` in machine-readable form with tolerances and grades.
"""
from __future__ import annotations

import math

import numpy as np
import trimesh

MM = 1e-3

#  ⭐ revision 0's realized-to-raw vertical factor, `drones.frame_fit_scale(DRONES["mavic4pro"])`
#     with MESH_FIX and BLADE_LAW unset. `check_rev0_anchors()` recomputes it from the live
#     revision-0 code and refuses a mismatch, so a drifting revision 0 cannot pass unnoticed.
REV0_SZ = 1.59766775121646

# --------------------------------------------------------------------------- #
#  Measured inputs
# --------------------------------------------------------------------------- #
#: Top-view planform, read from the owned top photo
#:   /workspace/sionna/assets/photos/mavic4pro/mavic4pro_c02_arm_positions_topview_labelled.jpg
#: The four rotor axes are the midpoints of each propeller's two orange blade tips (a two-blade
#: propeller's tips are 180° apart by construction, so the midpoint is the axis and the tip-to-tip
#: distance is a scale bar lying in the propeller plane). The image axes are the aircraft axes to
#: within 0.03°, so no rotation is applied. The scale, 0.57912 mm/px, comes from B1's ruler-scaled
#: front track 363.92 mm over the measured 628.4 px front hub separation
#: (`work/measure_planform.py` → `work/planform_c02.json`).
#: Cross-checks of that scale:
#:   · tip-to-tip 264.1 / 263.9 / 260.6 / 260.3 mm against the official 267.0 mm propeller
#:     (manual p.88, "1158F 267×147 mm"). The deficit is the orange tip patch's own centroid
#:     bias, which sits a few pixels inboard of the extreme point.
#:   · front track 363.9 + can Ø29.3 = 393.2 mm against the official unfolded width 390.5 mm.
#: ⚠ Reading conflicts this photo cannot settle, all recorded in the sources file:
#:   · rear track reads 312.6 mm here against B1's ruler-scaled 301.6 mm [296.7, 306.5];
#:   · fore-aft rotor spacing reads 273.7 mm here against B1's 275.7 mm [272.2, 277.8];
#:   · plan B.0 freezes the rotor xy at revision 0's square 344.7 mm track and 275.1 mm spacing,
#:     so neither measurement enters the mesh. Both are declared, not applied.
#: The width is the contiguous run of the airframe mask through the symmetry axis at that station.
#: ⚠ Stations where the arm fairings merge into that run are NOT listed: x ∈ [+65, +104] (the run
#:   jumps to 168 mm at x = +86) and x ∈ [−54.5, −30] (134 mm at x = −53). The WIDTH across those
#:   two gaps is still the straight line between the measured sections either side — nothing is
#:   invented. Since 2026-09-18 the gaps carry filled-in stations at `SHELL_BAND_STEP_MM` so the
#:   crown and keel follow the declared section law instead of being chorded across the gap.
#: Tolerance ±3 mm on every width and on the x span — the photo is a product image, and the
#: measured front/rear track ratio differs from B1's by 3.5 %.
SHELL_STATIONS_MM = (
    #  x,     width
    (-71.0,   40.5),
    (-68.0,   48.1),
    (-64.0,   56.2),
    (-61.0,   63.1),
    (-58.0,   69.5),
    (-54.5,   75.9),
    #  ---- ruled band: the rear arm fairings merge here ----
    (-30.0,   92.1),
    (-24.0,   89.8),
    (-18.0,   84.0),
    (-12.0,   76.4),
    ( -6.0,   69.5),
    (  0.0,   68.9),
    (  6.0,   69.5),
    ( 12.0,   70.1),
    ( 18.0,   70.1),
    ( 24.0,   70.7),
    ( 30.0,   71.2),
    ( 36.0,   71.2),
    ( 42.0,   71.8),
    ( 48.0,   72.4),
    ( 54.0,   73.0),
    ( 60.0,   73.6),
    ( 65.0,   75.3),
    #  ---- ruled band: the front arm fairings merge here ----
    (104.0,   86.9),
    (108.0,   84.6),
    (112.0,   82.8),
    (116.0,   81.7),
    (120.0,   79.9),
    (123.0,   77.6),
)
#: Dome cap lengths (tail, nose) in mm, so the shell's realized x span is [−72.5, +126.0] — the
#: measured outline. The nose is blunt: the airframe outline is still 77.0 mm wide at x = +126,
#: where the black gimbal shroud begins, so the nose cap is a 3 mm dome, not a long point.
SHELL_CAP_LEN_MM = (1.5, 3.0)
SHELL_X_SPAN_MM = (-72.5, 126.0)
#: Longest gap allowed between two loft stations, in mm. The measured stations are 3–6 mm apart
#: everywhere except the two bands the arm fairings hide; those are filled in at this step with a
#: straight-line WIDTH (exactly the ruled band that was there before — the photo says nothing
#: about the width there) and with (z_top, z_bot) read off the same revision-0 section law every
#: measured station already uses.
#: ⭐ The value is the 10 mm station spacing `drone_parts_rev1.section_loft_shell` already names
#: as the plan's own standard ("plan B.3/B.4 fill this from CAD or photo sections every 10 mm"),
#: taken as written rather than chosen from a result. What it buys, measured
#: (`work/law_error.py`, `work/sliver_ladder.py`): the crown/keel chord error inside the 39.0 mm
#: front band falls 1.594 → 0.177 mm and the keel 1.245 → 0.14 mm, the over-estimating facet
#: reading falls 2.209 → 1.741 mm, and the loft grows 29 → 34 stations, 7,580 → 7,874 faces.
#: ⚠ On the record, because it is a free parameter: the boolean seam sliver count is NOT
#: monotone in this step (84 at 10–12 and 20–25 mm, 95 at 13–18, 92 at 6–7, 100–118 below 5), a
#: ±12 spread over choices that are all equally valid. The step was not picked for that number.
SHELL_BAND_STEP_MM = 10.0
#: Revision 0's shell for comparison: 203.98 mm long × 118.08 mm wide, centred at x = −12.24
#: (`_SHELL_SHAPE["mavic4pro"]`, fl 0.62 · fw 0.302 · cx0 −0.06). Revision 1's centre is +26.75,
#: i.e. the shell moves **39.0 mm forward** and loses 26–49 mm of width.

#: Arm axis headings from +x toward +y, measured on the same photo by the MID-LINE of the arm
#: band (`work/arm_axis.py` → `work/arm_axis.json`): walk perpendicular to a candidate axis pinned
#: at the rotor centre, take the centre of the mask run, minimise the rms offset over 50–64
#: stations 32–108 px out from the hub. Both edges enter, so the arm's own width cancels and no
#: half width is assumed — this is the estimator the 2026-09-18 mini5pro review showed is
#: unbiased, and the defect it found there (an outer-silhouette fit minus an assumed half width,
#: 3.6° low) cannot occur here.
#:   front  FL 68.28–68.66°, FR 291.66–291.98° (= −68.02…−68.34)  → 68.3°, rms 0.35–0.43 mm
#:   rear   RL 129.94–130.16°, RR 230.88–231.48° (= −129.12…−128.52) → 129.4°, rms 0.70–1.18 mm
#: ⚠ The rear fit's rms is 2–3× the front's and the two rear arms disagree by 1.2°, so the rear
#:   heading carries ±1.5° while the front carries ±0.3°.
#: Revision 0 uses the rotor azimuths 51.4° / 128.6° as arm headings: the rear happens to be
#: right to within 0.8°, the front is 16.9° off.
ARM_HEADING_DEG = dict(front=68.3, rear=129.4)

#: Arm width (y, in the top view) at the two ends of the measured band, mm, from the same fit.
#:   front  hub end 13.2–13.9, body end 13.7–14.9  → tip 13.4, root 14.3
#:   rear   hub end 11.7–14.7, body end 10.9–13.7  → 12.9 at both ends (the spread is the fit's)
#: Revision 0's `drone_cad._ARM_WIDTH["mavic4pro"]` is (26.5, 18.5) — 1.4–2.0× too wide; the
#: inventory measured the realized section at 0.62 r as 22.7 × 28.1 mm.
#: ⚠ The arm's HEIGHT is not measurable in a top view. Revision 0's rule height = width × 0.775
#:   (raw), realized × REV0_SZ, is carried over unchanged; only the width changes.
ARM_WIDTH_FRONT_MM = (14.3, 13.4)      # (root, tip)
ARM_WIDTH_REAR_MM = (12.9, 12.9)
_ARM_H_RATIO = 0.775 * REV0_SZ         # revision-0 carry-over, realized

#: Motor can outer diameter [mm]. B1 height round (scratch mesh_rev1/height/work/
#: m4p_height_ledger.json, `nominal_fit.can_dia` = 29.330 mm; systematic variants 29.32–29.57),
#: a ruler-scaled rigid multi-view fit of the FCC SS3-L3AB2410 elevation photos over 4 rotors ×
#: 3 views with 40 Monte-Carlo draws plus systematic variants. Revision 0 used 0.052 × 441 mm as
#: a **radius**, i.e. Ø45.86 mm, which is a diagonal proportion, not a measurement.
#: Independent cross-check: the mesh_0917 inventory read Ø30.5 mm on FCC p05 at 0.3964 mm/px.
MOTOR_CAN_DIA_MM = 29.33
#: Motor can height [mm], realized. ⚠ **Revision-0 carry-over.** Revision 0 builds the bell
#: 0.048 × 441 = 21.168 mm tall and then stretches it: 21.168 × REV0_SZ = 33.815 mm.
#: Consistency note, not a source: the inventory's FCC p05 reading of the *un-stretched* can is
#: 19.8 mm, and 19.8 × REV0_SZ = 31.6 mm, i.e. within 7 % of the carried-over 33.8 mm. Keeping
#: revision 0's realized can height is therefore consistent with keeping the stretch.
MOTOR_CAN_H_MM = 0.048 * 441.0 * REV0_SZ
#: Prop seat on top of the can. `drone_cad.PROP_STANDOFF_M` has no entry for this aircraft, so
#: revision 0's prop mount plane **is** the bell top. The 2.0 mm seat is taken out of the can so
#: that the stack top lands exactly on revision 0's realized prop mount plane; its diameter is the
#: propeller's own hub diameter (0.085 × prop_dia_mm), not an invented number.
PROP_ADAPTER_H_MM = 2.0
PROP_ADAPTER_DIA_MM = 0.085 * 267.0

#: Battery pack, official size [mm]. DJI Mavic 4 Pro User Manual v1.0 (2025-05) p.88, "List of
#: Items, including qualified accessories": "Intelligent Flight Battery BWX341-6654-14.3,
#: 62×44×128 mm, Approx. 331 g". The manual prints no axis labels; the same table writes the
#: microSD card as 15×11×1.0 and the cellular dongle as 43.5×23.0×7.0, i.e. longest last is not
#: its convention. The axis assignment used here — 128 along x, 62 along y, 44 along z — is ours,
#: and it is the only one consistent with the owned photos: the standalone pack in
#: `mavic4pro_t16_flight_battery_standalone_ruler.jpg` has a 2.18:1 face (128/62 = 2.06) and the
#: pack slides in fore-and-aft (`mavic4pro_m05_manual_battery_removal_and_pack.png`).
#: Revision 0's box is 118.31 × 80.30 × 54.57 mm realized, a proportional box with no source.
BATTERY_LWH_MM = (128.0, 62.0, 44.0)

#: Gimbal, mm. Two owned readings:
#:   W 58.0  — the dark nose assembly's width at x = +161.5 on the top photo (work/planform_c02);
#:   front face x = +175.4 — the forward-most point of the same dark blob;
#:   H 64.0  — the mesh_0917 inventory's reading of FCC p05 at 0.3964 mm/px ("gimbal block
#:             ≈46 W × 64 H mm, hanging in front of the nose"). ⚠ grade medium: one view, one
#:             reader, and its width reading (46) disagrees with the top photo's 58.
#: The block's depth and the 10 mm lens barrel split the assembly between block and barrel, and
#: the block's rear 6 mm is buried in the shell nose so the gimbal is attached rather than
#: floating (plan C.2); both are construction, not measurements.
#: ⚠ The gimbal's z is a **revision-0 carry-over**: its floor sits at revision 0's realized
#:   housing floor, −77.73 mm (= cz −0.30·bh − 0.95·0.0316 m, all × REV0_SZ). Revision 0 solved
#:   that floor from the same FCC p05 photo, requiring the housing to clear the landing feet.
GIMBAL_W_MM = 58.0
GIMBAL_H_MM = 64.0
GIMBAL_REAR_X_MM = 120.0          # 6 mm inside the measured shell nose, so it attaches
GIMBAL_LENS_DIA_MM = 30.0
GIMBAL_LENS_LEN_MM = 10.0
GIMBAL_FRONT_X_MM = 175.4
GIMBAL_FLOOR_Z_MM = -77.73
GIMBAL_D_MM = GIMBAL_FRONT_X_MM - GIMBAL_LENS_LEN_MM - GIMBAL_REAR_X_MM
#: ⭐ 2026-09-18 (C.10 round). The head was built with a 4 mm corner radius and read on every
#: render as a square box, while FCC p05 shows a rounded housing. The corner radius is now
#: MEASURED on p05, as a RATIO so the photo's unknown mm/px and its perspective cannot bias it:
#: a rounded-rectangle outline is fitted by least squares to the 63 image rows of the head's
#: LOWER half (the pair of corners no part of the airframe hides in any owned view), giving
#:   R / W = 0.4502, rms 2.97 px = 2.28 % of the head width
#: against 13.52 px for a square-cornered box — a 4.6x worse fit, so the box is rejected on the
#: photo, not on taste (`work/gimbal_corner.py` -> `work/gimbal_corner_p05.json`).
#: ⚠ Only the LOWER corners are measured. The upper pair sits behind the nose shroud in p04,
#: p05 and p06, so top/bottom symmetry is assumed and declared; and the cylindrical collar where
#: the housing enters the nose (the "Infinity Gimbal" housing named in
#: assets/photos/mavic4pro/SOURCES.md) is NOT built — no owned view gives its diameter or length.
GIMBAL_CORNER_R_OVER_W = 0.4502
GIMBAL_CORNER_R_MM = round(GIMBAL_CORNER_R_OVER_W * GIMBAL_W_MM, 4)

#: Landing gear. FCC p05 (front elevation) and p07 (bottom plan) show **one tapered leg per FRONT
#: motor and none at the rear**; the manual overview `mavic4pro_m02` lists the front legs as the
#: built-in antenna housings. The foot position is B1's fit: (−0.41, ±184.88) mm against front can
#: centres at (0, ±181.96), i.e. Δ −0.41 mm aft and +2.92 mm outboard of the rotor axis.
#: Revision 0 builds a two-prong A-frame per front arm with its feet at y = ±191.9 mm.
#: ⚠ The leg's own section is a revision-0 carry-over: `drone_cad`'s default leg width rule
#:   arm_r1 × 0.62 evaluated on **revision 0's** arm radius, so the leg does not shrink with the
#:   corrected arm width. No owned reading of the leg section exists.
LEG_FOOT_DX_MM = -0.41
LEG_FOOT_DY_MM = 2.92
_LEG_W_MM = (18.5 / 2.0) * 0.62        # revision 0's arm_r1 · 0.62, realized in y

#: Vision sensors and LiDAR: revision 0's radii and its placement fractions, re-evaluated on
#: revision 1's shell — each is pushed out along its own axis until it meets the shell surface,
#: which is what revision 0's comment says it does ("본체 표면 밀착"). No new dimension is claimed.
FISHEYE_R_MM = 9.0
LIDAR_W_MM = 10.0
#: The two nose-deck vision eyes are the two dark round blobs on the deck in the top photo,
#: centred at (594.4, 502.3) and (688.1, 502.2) px → x = +88.9 mm, y = ±27.1 mm
#: (work/planform_c02.json's frame). Their radius is revision 0's.
NOSE_EYE_X_MM = 88.9
NOSE_EYE_Y_MM = 27.1

#: What B1's FCC-photo fit says the vertical layout should be, and what revision 1 builds instead.
#: The acceptance script prints this table so the largest remaining error is never silent.
#: All values mm above the landing feet; the 95 % bands are B1's Monte-Carlo draws.
HEIGHT_SHORTFALL = {
    "front_can_base": dict(measured=53.0, band=[51.6, 54.4]),
    "rear_can_base": dict(measured=62.5, band=[60.0, 65.0]),
    "front_stack_top": dict(measured=84.8, band=[83.7, 85.9]),
    "rear_stack_top": dict(measured=100.1, band=[97.9, 102.5]),
    "shell_outline_top": dict(measured=97.1, band=[93.0, 101.8]),
    "_note": ("B1 (wf/b1_height.md): the tallest resting feature is about 100 mm, so removing the "
              "×1.59767 stretch would leave the model ≈35 mm short (95 %: 32.7–37.3) of the "
              "official 135.2 mm unfolded height, and no measured feature carries that 35 mm. "
              "Revision 1 keeps the stretch. The model also has no front/rear stagger, while B1 "
              "measures the rear can base 9.5 mm and the rear stack top 15 mm higher than the "
              "front."),
}

#: Targets the plan or the sources asked for that this file does NOT implement, and why. Printed
#: by the acceptance script so the gap is never silent.
SOURCES_NOT_FOUND = {
    "height stretch (B.6 'stretch removal under the same condition as M5P-1')":
        "Not removed. B1's condition is not met: the FCC photos fix the can bases and stack tops "
        "to ±2–3 mm but the tallest measured feature is ~100 mm, so the unstretched model would "
        "stand ≈35 mm short of the official 135.2 mm and no measured feature carries that 35 mm. "
        "Revision 1 keeps revision 0's vertical layout and records the shortfall in "
        "HEIGHT_SHORTFALL, exactly as mini5pro does.",
    "rotor trapezoid": "Both owned readings say the front track is wider than the rear (B1 "
                       "363.9 / 301.6 mm; the top photo 363.9 / 312.6 mm), while revision 0 has "
                       "344.7 mm at both. Plan B.0 freezes rotor xy at revision 0's realized "
                       "values, so this is declared and NOT applied. It is the largest xy error "
                       "left in the mesh (±21 mm on the rear rotors, 0.41 λ at 5.8 GHz).",
    "front/rear rotor z stagger": "B1 measures the rear can base 9.5 mm and the rear stack top "
                                  "15 mm above the front; the model has both rotors on one "
                                  "plane. Changing it would move the prop mount planes, which "
                                  "plan B.0 keeps at revision 0's.",
    "arm height": "Not measurable in a top view. Revision 0's height = width × 0.775 (raw) rule "
                  "is carried over on the corrected width.",
    "shell width, x ∈ [+65, +104] and [−54.5, −30]": "The arm fairings and the shell are one run "
                                                     "in the top view there. P1's straight ruled "
                                                     "band between the measured sections either "
                                                     "side is used; nothing is invented.",
    "shell vertical sections": "Only the top outline was fitted by B1, from one side view. "
                               "Revision 0's realized (z_top, z_bot) law is carried across "
                               "normalised fore-aft position, so the crown and keel profile is "
                               "revision 0's on revision 1's planform.",
    "gimbal height and depth": "H 64 mm is one reader's reading of one FCC view (grade medium) "
                               "and the 36 + 10 mm depth split is construction. The gimbal is "
                               "built because its POSITION — in front of the nose, front face at "
                               "x = +175.4 — is the measured fact and is the large error; its "
                               "size carries the wider tolerance in the threshold file.",
    "leg section, taper and splay": "No owned reading. Revision 0's leg width rule is carried "
                                    "over; only the count (2 prongs → 1) and the foot position "
                                    "change.",
    "battery orientation and placement": "The manual gives 62×44×128 mm with no axis labels and "
                                         "no position. The axis assignment and the rearmost "
                                         "seating rule are ours and are recorded.",
    "PCB stack": "Revision 0's proportional box at revision 0's realized size and position, "
                 "carried over. No owned measurement; the teardown photos t06/t07/t09 show the "
                 "main board but were not scaled in this round.",
}


# --------------------------------------------------------------------------- #
#  Revision 0's vertical layout, read back from revision 0's own code
# --------------------------------------------------------------------------- #
def _rev0_shell_mesh():
    """Revision 0's shell loft with its realized (stretched) z, built by revision 0's own code.

    This is the single source of revision 1's vertical section law: revision 1 keeps revision 0's
    (z_top, z_bot) as a function of **normalised fore-aft position** and replaces only the
    planform. Reading it from `drone_cad._body_folding` instead of copying a table means a change
    in revision 0's shell table cannot silently desynchronise revision 1 — the fingerprint guard
    catches it.
    """
    import drone_cad as dc
    from drones import DRONES
    spec0 = DRONES["mavic4pro"]
    sh = dc._SHELL_SHAPE["mavic4pro"]
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
_DIAG_MM = 441.0
Z = dict(
    arm_root=0.0,                                         # _arm_folding z0 = rotor_z_mm = 0
    arm_tip=0.012 * _DIAG_MM * REV0_SZ,                   # _arm_folding z1 = 0.012·diag
    bell_base=0.014 * _DIAG_MM * REV0_SZ,                 # MOTOR_BASE_Z default
    gimbal_floor=GIMBAL_FLOOR_Z_MM,
)
#: Revision 0's realized prop mount z (all four rotors share one plane on this aircraft).
ROTOR_MOUNT_Z_MM = (0.014 + 0.048) * _DIAG_MM * REV0_SZ
#: Revision 0's realized frame floor (the foot of the landing gear) and the official height.
REV0_FRAME_MIN_Z_MM = -50.783 * REV0_SZ
REV0_FRAME_H_MM = 135.2


def check_rev0_anchors(tol_mm=5e-4) -> dict:
    """Recompute every revision-0 anchor from the live revision-0 code and compare (C.3 input)."""
    from drones import DRONES, frame_fit_scale, build_frame, rotor_layout
    import drone_cad as dc
    spec0 = DRONES["mavic4pro"]
    sz = float(frame_fit_scale(spec0)[2])
    V = np.asarray(build_frame(spec0).v, float) * 1000.0
    rl0 = rotor_layout(spec0)
    got = dict(sz=sz, frame_min_z_mm=float(V[:, 2].min()), frame_max_z_mm=float(V[:, 2].max()),
               mount_z_mm=[float(d["center"][2]) * 1000.0 for d in rl0],
               rotor_xy_mm=[[float(d["center"][0]) * 1000.0, float(d["center"][1]) * 1000.0]
                            for d in rl0],
               bell_top_raw_m=float(dc.motor_bell_top_z_m(spec0, spec0.diagonal_mm / 1000.0)),
               standoff_raw_m=float(dc.PROP_STANDOFF_M.get("mavic4pro", 0.0) or 0.0))
    bad = []
    if abs(sz - REV0_SZ) > 1e-12:
        bad.append(f"frame_fit_scale sz {sz!r} != REV0_SZ {REV0_SZ!r}")
    if abs(got["frame_min_z_mm"] - REV0_FRAME_MIN_Z_MM) > 1e-3:
        bad.append(f"revision-0 frame floor {got['frame_min_z_mm']:.4f} != "
                   f"{REV0_FRAME_MIN_Z_MM:.4f}")
    for k, gz in enumerate(got["mount_z_mm"]):
        if abs(ROTOR_MOUNT_Z_MM - gz) > tol_mm:
            bad.append(f"rotor {k} mount z {gz:.4f} != {ROTOR_MOUNT_Z_MM:.4f}")
    got["ok"] = not bad
    got["problems"] = bad
    return got


# --------------------------------------------------------------------------- #
#  Geometry helpers
# --------------------------------------------------------------------------- #
def _interp_section_law(law, x_span, x_mm):
    """(z_top, z_bot) of revision 0's realized shell at the normalised position of `x_mm`."""
    lo, hi = SHELL_X_SPAN_MM
    u = (float(x_mm) - lo) / (hi - lo)
    x0 = x_span[0] + u * (x_span[1] - x_span[0])
    return (float(np.interp(x0, law[:, 0], law[:, 1])),
            float(np.interp(x0, law[:, 0], law[:, 2])))


def _station_x_list(step_mm: float = SHELL_BAND_STEP_MM):
    """Measured station x, with the two wide bands filled in at `step_mm` (returns x, and the
    measured width there, linearly interpolated inside a band — see `SHELL_BAND_STEP_MM`)."""
    xs_m = [float(x) for x, _ in SHELL_STATIONS_MM]
    ws_m = [float(w) for _, w in SHELL_STATIONS_MM]
    out = []
    for i, (x, w) in enumerate(zip(xs_m, ws_m)):
        out.append((x, w, True))
        if i + 1 < len(xs_m):
            gap = xs_m[i + 1] - x
            n = int(math.ceil(gap / float(step_mm))) if step_mm > 0 else 1
            for k in range(1, max(n, 1)):
                u = k / float(n)
                out.append((x + u * gap, w + u * (ws_m[i + 1] - w), False))
    return out


def _shell_stations(law, x_span, npow=3.1, step_mm: float = SHELL_BAND_STEP_MM):
    """The P1 station list: measured widths, revision 0's vertical section law (npow is its own).

    ⭐ 2026-09-18 (C.6 round). The two bands the arm fairings hide — x ∈ [+65, +104] (39.0 mm)
    and x ∈ [−54.5, −30] (24.5 mm) — used to be spanned by a single ruled strip, and that strip
    cut the CROWN AND KEEL off the section law by up to 1.594 mm (top) / 1.245 mm (bottom)
    mid-band (`work/law_error.py`). The band is now filled in at `step_mm`:
      * the WIDTH at a filled-in station is the same straight line the ruled strip already was —
        the top photo says nothing there and nothing is invented;
      * (z_top, z_bot) come from `_interp_section_law`, the same revision-0 section law that
        every measured station already uses, so the crown and keel follow their declared source
        instead of being chorded across 39 mm.
    This changes no width, no C.3 target and no plan silhouette; it changes the vertical profile
    inside the two bands, so the geometry fingerprint moves and has to be recomputed."""
    st = []
    for x, w, measured in _station_x_list(step_mm):
        z_top, z_bot = _interp_section_law(law, x_span, x)
        st.append(dict(x=float(x), width=float(w), z_top=z_top, z_bot=z_bot,
                       z_mid=0.5 * (z_top + z_bot), n_up=float(npow), n_dn=float(npow),
                       measured=bool(measured)))
    return st


def _rotor_xy(spec):
    """Revision 0's realized rotor centres (x, y, azimuth) in mm — C.3 requires them unchanged."""
    from drones import motor_angles, motor_radii
    out = []
    for ang, r in zip(motor_angles(spec), motor_radii(spec)):
        ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        out.append((r * 1000.0 * ca, r * 1000.0 * sa, ang))
    return out


def _march_root(tip_xy, heading_deg, shell_mesh, bury_mm=10.0, step=0.5, max_mm=220.0):
    """Walk back from the arm tip along the heading until inside the shell, then `bury_mm` more."""
    d = np.array([math.cos(math.radians(heading_deg)), math.sin(math.radians(heading_deg))])
    t = 0.0
    while t < max_mm:
        t += step
        p = np.array([tip_xy[0], tip_xy[1]]) - d * t
        if bool(shell_mesh.contains(np.array([[p[0] * MM, p[1] * MM, 0.0]]))[0]):
            return float(t + bury_mm)
    raise RuntimeError(f"drone_rev1_mavic4pro: the arm at heading {heading_deg}° from {tip_xy} "
                       f"never reaches the shell")


def _inside_fraction_grid(box_lwh_mm, clearance_mm):
    """The probe points P8 uses, as offsets from a box centre."""
    L, W, H = (float(v) for v in box_lwh_mm)
    g = np.array([[a, b, c] for a in (-0.5, 0.0, 0.5) for b in (-0.5, 0.0, 0.5)
                  for c in (-0.5, 0.0, 0.5)], float)
    extra = []
    for a in (-0.5, -0.25, 0.0, 0.25, 0.5):
        for b in (-0.5, -0.25, 0.0, 0.25, 0.5):
            extra += [[a, b, -0.5], [a, b, 0.5], [a, -0.5, b], [a, 0.5, b],
                      [-0.5, a, b], [0.5, a, b]]
    G = np.unique(np.vstack([g, np.asarray(extra, float)]), axis=0)
    return G * np.array([L + 2 * clearance_mm, W + 2 * clearance_mm,
                         H + 2 * clearance_mm])[None, :]


def _aabb_overlap(c1, l1, c2, l2):
    """Do two axis-aligned boxes (centre, LWH) overlap?"""
    return all(abs(float(c1[i]) - float(c2[i])) < 0.5 * (float(l1[i]) + float(l2[i])) - 1e-9
               for i in range(3))


def _nearest_fitting_centre(shell_mesh, box_lwh_mm, prefer_mm, clearance_mm=1.0, step_mm=1.0,
                            avoid=(), window_mm=80.0):
    """The placement CLOSEST TO `prefer_mm` at which the grown box is wholly inside the shell and
    clear of every box in `avoid` (each a (centre_mm, lwh_mm) pair).

    Used for the PCB stack, whose size and revision-0 position are both carry-overs: revision 1's
    shell is 23-49 mm narrower than revision 0's, so revision 0's z leaves the board 0.905 mm from
    the shell where plan C.2 wants 1.0 mm. Only the position moves, and it moves as little as the
    1 mm grid allows. y stays pinned to 0 so the symmetry certificate (C.11) cannot break, and the
    battery (placed first, at its official size) is an obstacle, not something to move: plan C.13
    requires 0 % battery/pcb interpenetration.
    """
    G = _inside_fraction_grid(box_lwh_mm, clearance_mm)
    lo, hi = np.asarray(shell_mesh.bounds, float) / MM
    cand = []
    for x in np.arange(max(lo[0], prefer_mm[0] - window_mm),
                       min(hi[0], prefer_mm[0] + window_mm) + 1e-9, step_mm):
        for z in np.arange(max(lo[2], prefer_mm[2] - window_mm),
                           min(hi[2], prefer_mm[2] + window_mm) + 1e-9, step_mm):
            c = (float(x), 0.0, float(z))
            if any(_aabb_overlap(c, box_lwh_mm, ac, al) for ac, al in avoid):
                continue
            cand.append((float(np.hypot(x - prefer_mm[0], z - prefer_mm[2])), c))
    cand.sort()
    if not cand:
        raise RuntimeError("drone_rev1_mavic4pro: no PCB placement clears the battery")
    best = None
    for d, c in cand:
        f = float(shell_mesh.contains((G + np.asarray(c)[None, :]) * MM).mean())
        if f >= 1.0 - 1e-12:                      # the first fully-inside candidate is the nearest
            return tuple(round(v, 4) for v in c), f
        if best is None or f > best[0]:
            best = (f, c)
    return tuple(round(v, 4) for v in best[1]), float(best[0])


def _battery_centre(shell_mesh, box_lwh_mm, clearance_mm=1.0, step_mm=1.0):
    """Seat the pack at the tail, on the centreline, low: what the owned photos show.

    The pack slides in fore-and-aft (manual m05) and forms the rear belly (FCC p07 bottom plan,
    teardown t01/t08), so the rule is: among (x, z) on a 1 mm grid with y pinned to 0, take the
    placements whose grown box lies wholly inside the shell and pick the **rearmost**, breaking
    ties by the **lowest**. Only the position is chosen; the size stays the manual's.
    If nothing is wholly inside, the best containment fraction wins with the same tie-breaks, and
    the fraction is recorded.
    """
    L, W, H = (float(v) for v in box_lwh_mm)
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
    xs = np.arange(lo[0], hi[0] + 1e-9, step_mm)
    zs = np.arange(lo[2], hi[2] + 1e-9, step_mm)
    best = None
    for x in xs:
        for z in zs:
            c = np.array([x, 0.0, z])
            f = float(shell_mesh.contains((G + c[None, :]) * MM).mean())
            key = (round(f, 6), -x, -z)          # more inside, then rearmost, then lowest
            if best is None or key > best[0]:
                best = (key, c, f)
    return tuple(round(float(v), 4) for v in best[1]), float(best[2])


def _section_z(mesh, x_mm, frac):
    """z at a fraction of the shell's own section at station `x_mm` (0 = widest line, 1 = crown)."""
    s = mesh.section(plane_origin=[float(x_mm) * MM, 0, 0], plane_normal=[1, 0, 0])
    if s is None:
        raise RuntimeError(f"drone_rev1_mavic4pro: the shell has no section at x = {x_mm} mm")
    P = np.asarray(s.vertices, float) / MM
    z_top, z_bot = float(P[:, 2].max()), float(P[:, 2].min())
    z_mid = 0.5 * (z_top + z_bot)
    return z_mid + float(frac) * ((z_top - z_mid) if frac >= 0 else (z_mid - z_bot))


def _surface_point(mesh, origin_mm, direction, max_mm=300.0):
    """Where a ray leaves `mesh` — used to sit the vision sensors flush on the shell."""
    o = np.asarray(origin_mm, float)[None, :] * MM
    d = np.asarray(direction, float)[None, :]
    loc, _, _ = mesh.ray.intersects_location(ray_origins=o, ray_directions=d)
    if len(loc) == 0:
        raise RuntimeError(f"drone_rev1_mavic4pro: no shell surface from {origin_mm} along "
                           f"{direction}")
    t = ((loc - o[0]) @ d[0])
    return np.asarray(loc[int(np.argmax(t))], float) / MM


# --------------------------------------------------------------------------- #
#  The frame
# --------------------------------------------------------------------------- #
def _build(spec, stations, parts_log):
    from cadkit import Assembly, box
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
            raise RuntimeError(f"drone_rev1_mavic4pro: part {part.name!r} failed check_part: "
                               f"{chk}")
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
        hdg = hdg if ry >= 0 else -hdg                     # mirror for the right-hand side
        w_root, w_tip = ARM_WIDTH_FRONT_MM if front else ARM_WIDTH_REAR_MM
        L = _march_root((rx, ry), hdg, shell_m)
        d = np.array([math.cos(math.radians(hdg)), math.sin(math.radians(hdg))])
        root = (rx - d[0] * L, ry - d[1] * L, Z["arm_root"])
        arm = P.straight_arm(root, (rx, ry, Z["arm_tip"]),
                             (w_root, w_root * _ARM_H_RATIO), (w_tip, w_tip * _ARM_H_RATIO),
                             group="body", name=f"arm{k}", n_sec=6, sagitta_mm=1.0)
        take(arm)
        arms.append(arm)

    # ---- P3 motor stacks --------------------------------------------------- #
    pods = []
    for k, (rx, ry, ang) in enumerate(rot):
        w_tip = (ARM_WIDTH_FRONT_MM if math.cos(math.radians(ang)) > 0 else ARM_WIDTH_REAR_MM)[1]
        pod_bot = Z["arm_tip"] - 0.5 * w_tip * _ARM_H_RATIO        # arm underside at the tip
        parts = P.motor_can(MOTOR_CAN_DIA_MM, MOTOR_CAN_H_MM - PROP_ADAPTER_H_MM,
                            w_tip, max(0.5, Z["bell_base"] - pod_bot),
                            PROP_ADAPTER_DIA_MM, PROP_ADAPTER_H_MM,
                            pod_group="body", center_xy_mm=(rx, ry), base_z_mm=pod_bot,
                            pod_taper=1.0, name=f"motor{k}", sagitta_mm=1.0)
        for p in parts:
            take(p)
        pods.append(parts[0])
        top = parts[0].info["adapter_top_z_mm"]                    # P3 rounds this to 4 decimals
        if abs(top - ROTOR_MOUNT_Z_MM) > 1e-3:
            raise RuntimeError(f"drone_rev1_mavic4pro: rotor {k} motor stack top {top:.6f} mm != "
                               f"revision-0 prop mount z {ROTOR_MOUNT_Z_MM:.6f} mm")

    # ---- P5 legs (one per front motor) ------------------------------------- #
    for k, (rx, ry, ang) in enumerate(rot):
        if math.cos(math.radians(ang)) <= 1e-9:
            continue
        sy = 1.0 if ry >= 0 else -1.0
        w = _LEG_W_MM
        root_sec = (2.0 * w, 1.7 * w * REV0_SZ)
        tip_sec = (2.0 * w * 0.55, 1.7 * w * 0.55 * REV0_SZ)
        #  ⚠ The host must be ONE solid: a concatenation of the overlapping arm and pod is not a
        #  volume, and cutting a leg against it leaves needle faces that the canonical i5 repair
        #  then deletes, opening the leg (measured on mini5pro, work/dbg_leg.py of that round).
        host = trimesh.boolean.union([arms[k].mesh, pods[k].mesh], engine="manifold")
        w_tip = ARM_WIDTH_FRONT_MM[1]
        z_start = (Z["arm_tip"] - 0.5 * w_tip * _ARM_H_RATIO) + 2.0
        foot = (rx + LEG_FOOT_DX_MM, ry + sy * LEG_FOOT_DY_MM)
        z_foot = REV0_FRAME_MIN_Z_MM
        for _pass in range(3):
            leg = P.attached_leg([[rx, ry, z_start],
                                  [0.5 * (rx + foot[0]), 0.5 * (ry + foot[1]),
                                   0.5 * (z_start + z_foot)],
                                  [foot[0], foot[1], z_foot]],
                                 root_sec, tip_sec, group="gear", host=host,
                                 name=f"leg{k}", n_sec=8, declare_components=1, sagitta_mm=1.0)
            low = float(np.asarray(leg.mesh.vertices)[:, 2].min()) / MM
            if abs(low - REV0_FRAME_MIN_Z_MM) < 1e-4:
                break
            z_foot += (REV0_FRAME_MIN_Z_MM - low)
        take(leg)

    # ---- P7 gimbal, in front of the nose ----------------------------------- #
    #  ⚠ P7's `yaw_post` is a VERTICAL post and this gimbal does not hang from one: every owned
    #  photo (p04, p05, p06, c02) shows it carried on a rear-facing mount inside the nose. The
    #  block's rear 6 mm is therefore buried in the shell instead, which is also what makes it a
    #  non-floating part for plan C.2.
    cx = GIMBAL_FRONT_X_MM - GIMBAL_LENS_LEN_MM - 0.5 * GIMBAL_D_MM
    cz = GIMBAL_FLOOR_Z_MM + 0.5 * GIMBAL_H_MM
    gim = P.gimbal_block(GIMBAL_W_MM, GIMBAL_H_MM, GIMBAL_D_MM,
                         GIMBAL_LENS_DIA_MM, GIMBAL_LENS_LEN_MM,
                         group="camera", center_xyz_mm=(cx, 0.0, cz),
                         name="gimbal", corner_r_mm=GIMBAL_CORNER_R_MM, sagitta_mm=1.0)
    for p in gim:
        take(p)

    # ---- vision sensors (revision-0 shapes on revision 1's shell) ---------- #
    #  Revision 0's six fisheyes sit at (0.96, 0.30, 0.30, −0.10, −0.10) × nose_x with ±0.24–0.26
    #  bw and ±0.02…0.40 bh. The same fractions are re-evaluated here on revision 1's own shell:
    #  each sensor is seeded inside the shell at the matching normalised station and at a fraction
    #  of that station's own section, then pushed out along its axis to the surface, so nothing
    #  floats and nothing is buried.
    x_lo, x_hi = SHELL_X_SPAN_MM
    lat = 0.24 * 118.082                                   # revision 0's ±0.24 · bw
    sensors = []
    for sy in (+1.0, -1.0):
        #  the two nose-deck eyes are visible in the top photo and are placed where it puts them
        sensors.append(_surface_point(
            shell_m, (NOSE_EYE_X_MM, sy * NOSE_EYE_Y_MM,
                      _section_z(shell_m, NOSE_EYE_X_MM, 0.0)), (0, 0, 1)))
        xb = x_lo + 0.55 * (x_hi - x_lo)
        sensors.append(_surface_point(
            shell_m, (xb, sy * lat, _section_z(shell_m, xb, 0.0)), (0, 0, -1)))
        xt = x_lo + 0.30 * (x_hi - x_lo)
        sensors.append(_surface_point(
            shell_m, (xt, sy * lat, _section_z(shell_m, xt, 0.0)), (0, 0, 1)))
    for q in sensors:
        for g, m in dc._fisheye(q[0] * MM, q[1] * MM, q[2] * MM, FISHEYE_R_MM * MM, axis="z"):
            A.add(m, g)
    pl = _surface_point(shell_m, (x_hi - 8.0, 0.0, _section_z(shell_m, x_hi - 8.0, 0.55)),
                        (1, 0, 0))
    for g, m in dc._lidar(pl[0] * MM, pl[2] * MM, LIDAR_W_MM * MM):
        A.add(m, g)

    # ---- P8 internals ------------------------------------------------------ #
    bc, frac_in = _battery_centre(shell_m, BATTERY_LWH_MM, clearance_mm=1.0)
    batt = P.contain(BATTERY_LWH_MM, shell, group="battery", clearance_mm=1.0, name="battery",
                     center_mm=bc, declare_components=1)
    take(batt)
    #  The PCB stack keeps revision 0's realized SIZE (0.38·bl × 0.54·bw × 0.06·bh) — a
    #  carry-over, not a measurement; the teardown photos t06/t07/t09 were not scaled this round.
    #  Its POSITION moves: revision 1's shell is 23–49 mm narrower, so revision 0's z left the
    #  board 0.905 mm from the shell where plan C.2 wants 1.0 mm. The board is put at the closest
    #  (x, z) on a 1 mm grid, y pinned to 0, at which the box grown by 1 mm is wholly inside.
    bl0, bw0, bh0 = 203.98, 118.082, 62.1
    PCB_LWH_MM = (bl0 * 0.38, bw0 * 0.54, bh0 * 0.06 * REV0_SZ)
    pcb_prefer = (0.02 * bl0, 0.0, 0.26 * bh0 * REV0_SZ)
    pc, pcb_frac = _nearest_fitting_centre(shell_m, PCB_LWH_MM, pcb_prefer, clearance_mm=1.0,
                                           avoid=((bc, BATTERY_LWH_MM),))
    pcb = P.contain(PCB_LWH_MM, shell, group="pcb", clearance_mm=1.0, name="pcb",
                    center_mm=pc, declare_components=1)
    take(pcb)

    parts_log.extend(rec)
    parts_log.append(dict(name="battery_placement", plan_item="P8", group="battery",
                          info=dict(batt.info, centre_mm=list(bc), inside_fraction=frac_in)))
    parts_log.append(dict(name="pcb_placement", plan_item="P8", group="pcb",
                          info=dict(pcb.info, centre_mm=list(pc), inside_fraction=pcb_frac,
                                    rev0_centre_mm=list(pcb_prefer),
                                    moved_mm=round(float(np.hypot(pc[0] - pcb_prefer[0],
                                                                  pc[2] - pcb_prefer[2])), 4))))
    return A


def build_frame(spec):
    """Registry `frame_builder` for ("mavic4pro", 1) — plan B.6, default (the stretch is kept)."""
    law, x_span = _rev0_section_law()
    log = []
    A = _build(spec, _shell_stations(law, x_span), log)
    A.mesh_rev1_parts = log
    return A
