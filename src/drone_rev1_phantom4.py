# -*- coding: utf-8 -*-
"""drone_rev1_phantom4.py — DJI Phantom 4, mesh revision 1 (plan B.5, rows P4-1 … P4-8).

Frame of reference
    Every number here is in the **scan datum frame** of
    `scratchpad/mesh_0917/phantom_family/data/p4_datum.json`: +x is the nose, +y is the left
    side, +z is up, and z = −153.37 mm is the plane the four feet stand on. That frame is the
    one revision 0 already builds in (its own feet are at −153.39 mm), and the datum alignment
    scaled the owned CC-BY scan so that its motor-axis diagonal is the published 350 mm and its
    lowest foot point is our lowest gear point. Distances quoted as "scan" below are therefore
    directly comparable with a mesh built by this file.

What changes against revision 0 (docs/mesh_rev1/phantom4_sources.json carries every source)
    P4-1  The 196 mm height is no longer forced onto the props-off frame. `envelope_mm=None`,
          so `frame_fit_scale` is exactly (1, 1, 1) instead of revision 0's (1, 1, 0.93731).
          The props-off frame is built to the scan's own 180.2 mm (feet −153.37 → crown +26.8).
          196 mm is the **props-included** height: the Quick Start Guide v1.2 p.7 dimension line
          runs from the foot plane to the top of a propeller hub cap, and the User Manual v1.2
          p.8 front elevation reproduces it (195.6 mm measured on that drawing when its scale is
          set by the scan's crown-to-feet 180.21 mm).
    P4-2  The oval pod becomes an X-shaped fairing (P2): one centre pod lofted from the scan's
          own y = 0 centre-line sections, plus four arm fairings lofted from the scan's sections
          taken perpendicular to each 45° arm axis, plus (review fix R10) the narrow keel rib
          the scan shows under each arm outboard of r ≈ 113 mm.
    P4-3  The camera is where the manual's elevations put it: three blocks (P7) on a yaw post,
          x −13.0 … +62.2, bottom 28.5 mm above the feet, instead of revision 0's block buried
          in the shell with its bottom 83 mm above the feet.
    P4-4  The flat disc motors become cans (P3): a plastic pod built as a barrel from the scan's
          own radial profile (review fix R8; the delivery's single cone measured 35.03 mm where
          the scan reads 37.8), a metal can Ø28.2 with a 23 mm straight wall, and a prop adapter
          whose top is the scan's +24.9 mm mount plane.
    P4-5  The legs are attached (P5) and cut against the fairing, so the gap is 0. Each side is
          two struts plus the skid that joins them, all in the `gear` group.
    P4-6  The GPS puck and the Pro-only sensors (rear stereo pair, side infrared pair) are gone.
          The base Phantom 4 of User Manual v1.2 has forward obstacle sensing and a downward
          vision system only; rear vision and the infrared side sensors arrived with the P4 Pro.
          The four sensors that stay are cut against the part they sit on (review fix R11), so
          none of them is held by interpenetration alone.
    P4-7  The internal metal and the board are contained (P8): wholly inside the shell with at
          least 1 mm of clearance.
    P4-8  P6 propeller orientation, and `rotor_dirs` = the measured spin pattern (front-left and
          rear-right clockwise seen from above).

What this file does **not** change (plan B.0)
    Rotor xy, wheelbase, prop diameter, blade count, rotor count, hover rpm and `base_ang`.
    Rotor z is explicit: `rotor_z_mm` is set so the propeller hub's underside lands on the
    scan's measured +24.9 mm mount plane.
"""
from __future__ import annotations

import numpy as np

import drone_parts_rev1 as P

MM = P.MM

#: The plane the feet stand on, scan datum frame [mm]. Source: p4_scan_analysis_datum.json
#  `scan_z.feet_min_mm` = −153.4 (our own gear reaches −153.39, which is what the datum matched).
FEET_Z_MM = -153.37

#: Rotor centres in xy [mm] — revision 0's realized positions, which plan B.0 freezes.
#  `drones.rotor_layout` rebuilds them from diagonal_mm/2 with frame_fit_scale (1, 1, 1), so this
#  table is only used for placing the motor stacks and is checked against rotor_layout in C.3.
ROTOR_XY_MM = ((+123.7436867076458, +123.7436867076458),
               (-123.7436867076458, +123.7436867076458),
               (-123.7436867076458, -123.7436867076458),
               (+123.7436867076458, -123.7436867076458))

#: Measured spin, seen from above: +1 = counter-clockwise, −1 = clockwise, in rotor order
#  (front-left, rear-left, rear-right, front-right). Source: scratchpad/wf/b1_spin.md
#  (User Manual v1.2 p.7 propeller figure + p.23 ring-colour rule), grade medium-high.
ROTOR_DIRS = (-1, +1, -1, +1)

# --------------------------------------------------------------------------- #
#  P4-2 — the X fairing
# --------------------------------------------------------------------------- #
#: Centre-pod stations: (x, half width, z_top, z_bot) [mm].
#  z_top/z_bot are the scan's own y = 0 centre-line section (work/scan_measure_p4.json,
#  `centreline_y0`, 2 mm slab about y = 0). The half width is the free parameter of the loft:
#  it is anchored at x = 0 on the scan's measured waist (101.0 mm full width → 50.5 half) and
#  tapers to the nose and the tail, where the four arm fairings set the outline instead.
#  ⭐ Review fix 2026-09-18 (R9, the tail). The three aft rows and the tail dome below are new.
#  What was wrong: the delivery's last aft station was x = −70 with a 6.0 mm dome, so the shell
#  ran to x = −76.0 while the scan's tail ends at x = −74.57, and the dome carried the −70
#  section's full height aft, leaving the crown ~5.8 mm above the scan at x = −75. The half width
#  was also left on the "the arm fairings set the outline here" rule, which does not hold aft of
#  x ≈ −70: at x = −71 the rear arm fairings' inner edge is at |y| ≈ 43 mm while the scan's tail
#  is 35.95 mm half wide, so the delivery's 21.8 mm left a 14 mm notch on each side.
#  Re-measured on the scan before the change (fixwork/measure_targets.py, fixwork/sections.py,
#  2 e6 samples, x window ±0.5 mm for the centre line and ±0.75 mm for the sections):
#      x = −74.0  half width 21.82   centre line z −18.43 … +5.61
#      x = −72.0  half width 33.61   centre line z −24.35 … +13.19
#      x = −71.0  half width 35.95   centre line z −25.37 … +14.49
#      x = −70.0  half width ≥37.93  centre line z −26.04 … +15.32
#      x = −60.0  (tail and arms merge, no separable half width)  z −31.37 … +19.46
#      aft tip of the shell on the centre line: x = −74.57
POD_STATIONS = (
    #  x      hw     z_top    z_bot
    (-74.0, 21.8,   5.61, -18.43),
    (-72.0, 33.6,  13.19, -24.35),
    (-70.0, 38.0,  15.32, -26.04),
    #  Inboard of x ≈ −70 the scan cannot separate the pod from the rear arm fairings, so the
    #  half width is again the loft's free parameter: it is carried from the measured 38.0 at
    #  x = −70 to the delivered 40.0 at x = −50. The z values stay the scan's centre line.
    (-60.0, 39.0,  19.46, -31.37),
    (-50.0, 40.0,  21.07, -47.02),
    (-40.0, 46.0,  20.89, -54.03),
    (-30.0, 49.5,  24.55, -54.07),
    (-20.0, 50.5,  26.17, -54.48),
    (-10.0, 50.7,  26.75, -58.10),
    (0.0,   50.5,  26.75, -58.45),
    (10.0,  50.0,  26.80, -59.42),
    (20.0,  48.5,  26.38, -60.75),
    (30.0,  46.0,  24.86, -61.87),
    (40.0,  38.0,  19.49, -61.63),
    (48.0,  22.0,   8.00, -52.00),
)
POD_N_UP, POD_N_DN = 2.6, 2.4
#: Dome cap length at the two ends of the pod loft, (tail, nose) [mm]. The tail dome closes the
#  x = −74.0 section over 0.57 mm, which puts the aft tip on the scan's measured −74.57; the nose
#  is unchanged. Review fix 2026-09-18 (R9): the delivery used 6.0 mm at the tail.
POD_DOME_LEN_MM = (0.57, 4.0)
#: Height of the widest line of a pod section [mm]. The Phantom's widest line is the shoulder
#  the arms leave from, which the scan puts a little below the crown.
POD_Z_MID_MM = -5.0

#: Arm-fairing stations: (radius from the airframe axis, half width, z_top, z_bot) [mm].
#  Measured on the scan perpendicular to each 45° axis and averaged over the four arms
#  (work/scan_measure.py, |t| < 26 mm, motor can excluded). Stations are given only where the
#  scan could be read: between r = 75 and r = 105 the landing gear hides the arm's underside, so
#  that band is left to the loft's ruled surface rather than filled with invented sections.
#  ⭐ Review fix 2026-09-18 (R10, the arm underside). `z_bot` is the section's **lowest** point on
#  the arm's centre line. Outboard of r ≈ 113 the scan's arm is not a single smooth section: it
#  has a broad, nearly flat underside (the "flank") with a narrow rib (the "keel") hanging below
#  it on the centre line. The delivery gave every station the keel's z, so the whole underside
#  ran flat at the keel depth and the arm sat 3–5 mm below the scan over |t| = 4 … 11 mm.
#  Re-measured before the change (fixwork/keel.py: 4 arms averaged, station window ±1.0 mm,
#  offset window ±0.6 mm; keel = mean of |t| ≤ 1 mm, flank = mean of 5 ≤ |t| ≤ 8 mm):
#      r     106     110     114     116     120     128     136     140     148     152    156
#      flank −25.94 −25.00 −22.32 −21.59 −21.14 −20.18 −18.85 −18.17 −17.33 −17.08 −16.62
#      keel  −29.72 −27.88 −27.11 −26.65 −25.83 −24.26 −22.80 −22.13 −19.75 −19.10 −17.93
#      depth   3.78   2.88   4.79   5.06   4.69   4.08   3.95   3.96   2.42   2.02   1.31
#  So `z_bot` from r = 115 outward is now the **flank**, and KEEL_STATIONS below carries the rib.
#  Stations at r ≤ 110 are untouched: there the scan's section is a smooth U with no shoulder
#  (see fixwork/arm_sections_scan_vs_rev1.png, left panel), which is what the delivery built, and
#  between r = 75 and r = 105 the landing gear sits on the arm axis so the underside is unread.
#  r = 160 is untouched as well: it lies inside the motor pod's footprint (the pod spans
#  r = 155.7 … 194.3 mm about the rotor axis), so the scan there is a mixture, not the arm.
ARM_STATIONS = (
    #  r      hw     z_top    z_bot
    (45.0, 25.99,  23.98, -55.28),
    (50.0, 26.00,  23.30, -53.50),
    (55.0, 25.35,  22.58, -51.81),
    (60.0, 24.00,  21.83, -47.78),
    (65.0, 22.83,  21.09, -44.72),
    (70.0, 21.84,  20.32, -42.00),
    (75.0, 20.97,  19.55, -41.03),
    (105.0, 14.06, 14.26, -33.23),
    (110.0, 13.35, 13.32, -27.98),
    (115.0, 12.70, 12.29, -21.95),
    (120.0, 12.04, 11.46, -21.14),
    (130.0, 10.79,  9.49, -19.87),
    (140.0, 9.68,   7.44, -18.17),
    (150.0, 10.95,  5.14, -17.20),
    (160.0, 13.73, -1.06, -13.77),
)
ARM_ROOT_R_MM = ARM_STATIONS[0][0]
ARM_N_UP, ARM_N_DN = 3.0, 3.0
ARM_HEADINGS_DEG = (45.0, 135.0, 225.0, 315.0)

#: The keel rib under each arm: (radius from the airframe axis, half width, z_top, z_bot) [mm].
#  `z_bot` is the measured keel depth above; `z_top` is set about 2 mm above the local flank so
#  the rib overlaps the arm fairing and the P2 union welds the two into one solid rather than
#  leaving a tangent seam. The half width is the scan's own: the rib reads 2.0–3.0 mm half wide
#  between r = 118 and 132, where the flank band is clear of it. Inboard of r ≈ 112 the rib is
#  inside the arm fairing and contributes nothing; it is carried in so that the loft's root sits
#  deep inside the pod (which `x_blend_shell` requires) and so that it grows out of the arm
#  instead of starting at a step.
#  ⚠ The scan's rib fades out at r ≈ 155 (depth 1.31 mm at r = 156), but this one stops at
#  r = 144 and its dome cap closes there. Carrying it further put its tip 23 mm from the rotor
#  axis, where the rib, the arm's own tip dome and the motor pod all meet, and that corner cost
#  60 C.1 sliver faces for the last 2 mm of rib depth. The 2.4 mm of rib the model gives up over
#  r = 144 … 156 is stated here rather than built.
KEEL_STATIONS = (
    #  r      hw     z_top    z_bot
    (45.0,  3.0,  -20.00, -30.00),
    (90.0,  3.0,  -28.00, -34.00),
    (105.0, 3.0,  -24.00, -31.20),
    (112.0, 3.0,  -22.00, -27.50),
    (116.0, 3.0,  -19.50, -26.65),
    (120.0, 3.0,  -19.00, -25.83),
    (128.0, 3.0,  -18.00, -24.26),
    (136.0, 2.8,  -16.80, -22.80),
    (144.0, 2.6,  -15.50, -20.90),
)
KEEL_N_UP, KEEL_N_DN = 2.4, 2.4

# --------------------------------------------------------------------------- #
#  P4-4 — the motor stack
# --------------------------------------------------------------------------- #
#: Scan radial profile about each rotor axis (p4_scan_analysis_datum.json `scan_motor_cans`):
#  r50 = 14.1 mm from z ≈ 0 to z ≈ +23 (the can), 8.7–9.3 mm at the +24.9 top (the adapter),
#  18.7–19.3 mm from z ≈ −11 to z ≈ −1 (the plastic pod under the can).
CAN_D_MM = 28.2          # 2 × can_radius_fit_mm 14.09…14.10 over the four rotors
CAN_H_MM = 23.0          # straight wall, scan r50 = 14.1 from z ≈ 0 to z ≈ 23
POD_D_MM = 38.1          # 2 × 19.05, the widest r50 below the can (see POD_PROFILE_RZ_MM)
POD_H_MM = 11.0          # z −11 → 0
ADAPTER_D_MM = 18.0      # 2 × 9.0, the r50 at the +24.9 top step
ADAPTER_H_MM = 1.9       # z 23.0 → 24.9
MOUNT_Z_MM = 24.9        # scan_motor_cans top_z_mm 24.8…25.0, mean 24.9 — the metal top
#  ⚠ The propeller is NOT put in this plane. mesh_rev_phantom4.PROP_SEAT_CLEARANCE_MM
#  lifts it 0.30 mm above the adapter so the P6 hub's flat underside and this adapter's
#  top disc are not coincident faces; see that file for the measurement and the reason.

#  ⭐ Review fix 2026-09-18 (R8, the motor pod). The delivery built the pod as one cone
#  (base Ø38.6 tapered 0.83), which measures **35.03 mm** on the scan's own r50 rule at z = −5 —
#  3.6 mm under its own source and 3.0 mm under the frozen 38.0 ± 3.0, i.e. it passed by 0.03 mm.
#  A cone is widest at one of its ends; the scan's pod is a barrel. Re-measured before the change
#  (fixwork/measure_targets.py: r50 of the scan samples within 35 mm of each rotor axis, z slab
#  ±1.0 mm, mean over the four rotors — the same rule benchmark/mesh_rev1_acceptance.py scores):
#      z    −11.0  −10.0  −9.0  −8.0  −7.0  −6.0  −5.0  −4.0  −3.0  −2.0  −1.0   0.0
#      r50   17.62 18.75 18.96 19.03 19.03 19.05 18.91 18.76 18.24 16.74 15.46 14.73
#  The profile below is those radii at four heights (z measured from the bottom of the pod, so
#  local z = global z + 11): the bottom 17.62, the barrel's own 19.0 plateau over z = −8 … −4,
#  and the 14.73 shoulder where the pod meets the can. Four rings, not the twelve the table has:
#  every extra ring is another line the P2 union has to cut through the arm fairing, and a
#  twelve-ring pod raised the C.1 sliver count by 54 faces for 0.1 mm of profile.
#  ⚠ r50 is a **median over a mixture** — the slab holds pod wall and arm fairing both. It is
#  used here because it is the rule the frozen threshold names, and because on this geometry the
#  pod wall is what the median lands on (the delivery's cone wall was 17.51 mm at z = −5 and the
#  same measurement returned 17.5), not because it is the pod's true radius.
POD_PROFILE_RZ_MM = ((17.62, 0.0), (19.02, 3.0), (18.83, 6.5), (14.73, 11.0))

# --------------------------------------------------------------------------- #
#  P4-5 — the landing gear
# --------------------------------------------------------------------------- #
#: Strut axis of the front-left leg: (x, y, z) [mm], from the scan's leg sections
#  (work/scan_measure.py, centre of the x and y span at each z). The first point is inside the
#  arm fairing so that the host cut leaves no gap; it continues the straight axis fitted to the
#  measured points between z = −50 and z = −135.
LEG_PATH_MM = (
    (64.0, 62.5, -30.0),     # extrapolated along the measured axis, inside the fairing
    (66.3, 65.8, -50.0),
    (69.2, 70.3, -60.0),
    (72.9, 74.6, -80.0),
    (75.6, 78.5, -110.0),
    (76.0, 80.0, -135.0),
    (76.0, 80.4, -143.0),
)
#: Section of the sweep at the first and last path point, in the **path frame** (width along the
#  horizontal normal, height along the binormal). The scored quantity is the realized horizontal
#  x and y span at z = −80 and z = −110, which the scan measures as 13.2 × 12.0 and 11.1 × 10.3
#  mm; the strut axis is tilted about 15° from vertical, so the path-frame section that
#  reproduces those spans is not numerically equal to them. These two pairs are the loft's free
#  parameters, fitted to the measured spans (C.3 leg_root_section / leg_tip_section).
LEG_ROOT_SECTION_MM = (14.2, 12.4)
LEG_TIP_SECTION_MM = (9.2, 7.8)
#: Skid joining the two struts of one side: the scan's lowest band, left side, near x = 0 is
#  y 76.1 … 85.8 (centre 80.95, width 9.7) and it runs from x ≈ +80 to x ≈ −80; its z reaches the
#  foot plane and its top is where the struts stop being separate (z ≈ −140).
SKID_Y_MM = 80.6
SKID_X_HALF_MM = 80.0
SKID_SECTION_MM = (9.7, 13.4)
SKID_Z_MID_MM = -146.7

# --------------------------------------------------------------------------- #
#  P4-3 — the gimbal and camera
# --------------------------------------------------------------------------- #
#  Measured on User Manual v1.2 p.8, front elevation (scale set by the scan's crown-to-feet
#  180.21 mm = 492 px) and left-side elevation (504 px for the same 180.21 mm). Centre of the
#  front elevation from the two feet, centre of the side elevation from the two motor cans.
CAM_HEAD = dict(w_mm=45.2, h_mm=33.7, d_mm=38.3, centre=(42.0, -0.7, -108.0),
                lens_d_mm=29.9, lens_len_mm=3.0)
#  The pitch arm is the piece that joins the yaw housing to the camera head. Its x and z spans
#  are stretched by ~5 mm at each end beyond the outline read off the side elevation so that it
#  overlaps its two neighbours by about 5 mm instead of 1-2 mm: a union seam between two boxes
#  that barely touch is a ring of very thin triangles (plan C.1 slivers), and the stretched part
#  is hidden inside the head and the housing.
CAM_ARM = dict(w_mm=21.5, h_mm=45.3, d_mm=42.0, centre=(7.0, 0.0, -98.65))
CAM_YAW = dict(w_mm=25.0, h_mm=19.3, d_mm=27.4, centre=(26.8, 0.0, -70.55),
               post_d_mm=25.0, post_top_z_mm=-50.0)

# --------------------------------------------------------------------------- #
#  P4-6 — the sensors that stay
# --------------------------------------------------------------------------- #
#  User Manual v1.2 p.8 callouts [6] and [12], p.20 and p.21: the base Phantom 4 has a forward
#  obstacle-sensing pair — "cameras that installed on landing gear" (p.21) — and a downward
#  vision system on the belly. Sizes are revision 0's own literals (r 6 × 8 mm and r 5 × 6 mm):
#  DJI publishes none, and this revision does not invent any; only the parts DJI never fitted
#  are removed. The forward pair's y = ±66.0 and z = −36.9 are read off the p.8 front elevation
#  with the scan's crown-to-feet scale; its x follows the measured leg axis at that z.
#  ⭐ Review fix 2026-09-18 (R11). The delivery added these four as bare `cadkit.cyl` solids that
#  simply overlapped their host (forward pair 2.2 and 4.2 mm into the landing gear, downward pair
#  5.1 mm into the shell) and were cut against nothing. They are their own closed components of
#  the `camera` group, so nothing held them but that overlap. They are now swept with the P5
#  `attached_leg(shape="tube", host=…)`, which is the one public part that cuts against a host:
#  `difference(sensor, host)` ends each sensor exactly on the host surface, gap 0, and the
#  interpenetration goes away. **Cut, not merged** — `drones.DRONE_GROUP_MAT` gives `camera` the
#  material `camera_assembly` (metal housing + glass lens) while the shell and the gear are
#  `plastic`, so merging a sensor into its host would silently change what it is made of.
#  The part that sticks out of the host is the same solid of revolution, at the same place and
#  the same diameter, as the delivery's: only the buried half is gone.
VISION_FWD_R_M, VISION_FWD_H_M = 0.006, 0.008
VISION_FWD_Y_MM, VISION_FWD_Z_MM = 66.0, -36.9
#: Extra length each sensor tube is given **behind** the delivery's cylinder before the host cut
#  [mm]. 0.0, so the tube before the cut is exactly the solid the delivery placed and the cut is
#  purely subtractive: the buried half goes and nothing is added. Two earlier tries (8.0 and
#  3.0 mm) drove the tube further through the strut, which only made the cut copy a larger patch
#  of the strut's own triangulation onto the sensor — 36 and 16 C.1 sliver faces against 0.0's
#  14 — and left that much unsourced tube hanging beside the strut on the side where the Ø12 mm
#  sensor overhangs the Ø~14 mm strut. `attached_leg` refuses a tube that does not reach its
#  host, so 0.0 is safe: if it ever stopped reaching, the build would stop with it.
VISION_CUT_DEPTH_MM = 0.0
VISION_DWN_R_M, VISION_DWN_H_M = 0.005, 0.006
#: Belly pair, User Manual v1.2 p.8 callout [12] / bottom elevation: two lenses just forward of
#  the gimbal mount on the centre line. Their z is set by the fairing's own belly at that xy, so
#  the part always meets the shell (plan C.2, no floating parts).
VISION_DWN_XY_MM = ((12.0, +20.0), (12.0, -20.0))

# --------------------------------------------------------------------------- #
#  P4-7 — internals
# --------------------------------------------------------------------------- #
#: Revision 0's internal boxes (its ratio path, `drone_cad.build_frame_cad`): battery
#  bl·0.50 × bw·0.62 × bh·0.55, board bl·0.38 × bw·0.54 × bh·0.06 and the v2 structural plate
#  bl·0.58 × bw·0.68 × bh·0.08, realized as the sizes below. ⚠ **None of these is measured** —
#  DJI publishes no dimension for the PH4-5350 pack or the boards, and the owned scan is an
#  outside surface. Revision 1 therefore keeps revision 0's shapes and only shrinks them by the
#  single largest factor from `INTERNAL_SCALES` that fits the revision-1 shell with 1 mm of
#  clearance, which is a rule, not a new dimension. They stay engine knobs, not measurements.
INTERNAL_BOXES = (
    ("battery", (101.6, 107.3, 42.2)),
    ("pcb", (77.2, 93.4, 4.6)),
)
INTERNAL_SCALES = (1.0, 0.95, 0.9, 0.85, 0.8, 0.75, 0.7, 0.65, 0.6, 0.55, 0.5, 0.45, 0.4)


def _pod_stations():
    out = []
    for x, hw, z_top, z_bot in POD_STATIONS:
        z_mid = min(max(POD_Z_MID_MM, z_bot + 1.0), z_top - 1.0)
        out.append(dict(x=float(x), width=2.0 * float(hw), z_top=float(z_top),
                        z_bot=float(z_bot), z_mid=float(z_mid), n_up=POD_N_UP, n_dn=POD_N_DN))
    return out


def _arm_sections():
    out = []
    for r, hw, z_top, z_bot in ARM_STATIONS:
        out.append(dict(s=float(r) - ARM_ROOT_R_MM, width=2.0 * float(hw), z_top=float(z_top),
                        z_bot=float(z_bot), z_mid=0.5 * (float(z_top) + float(z_bot)),
                        n_up=ARM_N_UP, n_dn=ARM_N_DN))
    return out


def _keel_sections():
    """The rib under one arm, as an extra arm loft of the same X blend (review fix R10)."""
    out = []
    for r, hw, z_top, z_bot in KEEL_STATIONS:
        out.append(dict(s=float(r) - ARM_ROOT_R_MM, width=2.0 * float(hw), z_top=float(z_top),
                        z_bot=float(z_bot), z_mid=0.5 * (float(z_top) + float(z_bot)),
                        n_up=KEEL_N_UP, n_dn=KEEL_N_DN))
    return out


def build_x_fairing(group: str = "body") -> P.Part:
    """P4-2 — the one-piece X fairing (pod ∪ four arm fairings ∪ four underside keels)."""
    def _axis(h):
        return dict(heading_deg=h,
                    root_mm=(ARM_ROOT_R_MM * np.cos(np.radians(h)),
                             ARM_ROOT_R_MM * np.sin(np.radians(h))),
                    z_mm=0.0)
    axes = [_axis(h) for h in ARM_HEADINGS_DEG] + [_axis(h) for h in ARM_HEADINGS_DEG]
    secs = [_arm_sections()] * 4 + [_keel_sections()] * 4
    return P.x_blend_shell(_pod_stations(), axes, secs, group=group,
                           name="p4_xfairing", root_transition_mm=10.0,
                           root_transition_scale=(1.0, 1.02),
                           pod_cap=("dome", "dome"), pod_dome_len_mm=POD_DOME_LEN_MM,
                           max_faces=P.FACE_BUDGET["P2_total"])


def build_motors(body_group: str = "body") -> list:
    """P4-4 — four motor stacks: plastic pod (body) + metal can + metal prop adapter."""
    parts = []
    base_z = MOUNT_Z_MM - ADAPTER_H_MM - CAN_H_MM - POD_H_MM
    for k, (cx, cy) in enumerate(ROTOR_XY_MM):
        parts += P.motor_can(CAN_D_MM, CAN_H_MM, POD_D_MM, POD_H_MM, ADAPTER_D_MM, ADAPTER_H_MM,
                             pod_group=body_group, center_xy_mm=(cx, cy), base_z_mm=base_z,
                             can_group="motor", adapter_group="motor",
                             chamfer_mm=0.8, pod_profile_rz_mm=POD_PROFILE_RZ_MM,
                             name=f"p4_motor{k}")
    return parts


def build_gear(host, group: str = "gear") -> list:
    """P4-5 — four struts and two skids, each cut against the fairing (gap 0)."""
    parts = []
    for k, (sx, sy) in enumerate(((+1, +1), (-1, +1), (-1, -1), (+1, -1))):
        path = [(sx * x, sy * y, z) for (x, y, z) in LEG_PATH_MM]
        parts.append(P.attached_leg(path, LEG_ROOT_SECTION_MM, LEG_TIP_SECTION_MM, group=group,
                                    host=host, name=f"p4_leg{k}", shape="bar",
                                    n_up=3.0, n_dn=3.0, n_sec=14, declare_components=1))
    for k, sy in enumerate((+1, -1)):
        path = [(+SKID_X_HALF_MM, sy * SKID_Y_MM, SKID_Z_MID_MM),
                (0.0, sy * SKID_Y_MM, SKID_Z_MID_MM),
                (-SKID_X_HALF_MM, sy * SKID_Y_MM, SKID_Z_MID_MM)]
        parts.append(P.attached_leg(path, SKID_SECTION_MM, SKID_SECTION_MM, group=group,
                                    host=None, name=f"p4_skid{k}", shape="bar",
                                    n_up=3.0, n_dn=2.0, n_sec=8, declare_components=1))
    return parts


def build_camera(host, group: str = "camera") -> list:
    """P4-3 — the three-axis gimbal: yaw housing on its post, pitch arm, camera head with lens."""
    parts = []
    parts += P.gimbal_block(CAM_YAW["w_mm"], CAM_YAW["h_mm"], CAM_YAW["d_mm"],
                            lens_d_mm=1.0, lens_len_mm=1.0, n_lens=0, group=group,
                            center_xyz_mm=CAM_YAW["centre"],
                            yaw_post=dict(d_mm=CAM_YAW["post_d_mm"],
                                          top_z_mm=CAM_YAW["post_top_z_mm"]),
                            host=host, name="p4_gimbal_yaw", declare_post_components=1)
    parts += P.gimbal_block(CAM_ARM["w_mm"], CAM_ARM["h_mm"], CAM_ARM["d_mm"],
                            lens_d_mm=1.0, lens_len_mm=1.0, n_lens=0, group=group,
                            center_xyz_mm=CAM_ARM["centre"], name="p4_gimbal_arm")
    parts += P.gimbal_block(CAM_HEAD["w_mm"], CAM_HEAD["h_mm"], CAM_HEAD["d_mm"],
                            lens_d_mm=CAM_HEAD["lens_d_mm"], lens_len_mm=CAM_HEAD["lens_len_mm"],
                            n_lens=1, lens_axis="+x", group=group,
                            center_xyz_mm=CAM_HEAD["centre"], name="p4_gimbal_head")
    return parts


def build_internals(shell) -> list:
    """P4-7 — revision 0's internal boxes, shrunk by the largest scale that fits with 1 mm.

    The battery is placed first, by `contain`'s own search. The board then goes **under** it,
    1 mm clear of its underside and on its axis, so the two never share a volume (plan C.13
    wants 0 % interpenetration); only its scale is searched."""
    parts = []
    battery = None
    for name, dims in INTERNAL_BOXES:
        last = None
        for sc in INTERNAL_SCALES:
            box = tuple(float(v) * sc for v in dims)
            kw = dict(group=name, clearance_mm=1.0, name=f"p4_{name}", declare_components=1)
            if name != "battery" and battery is not None:
                bc = battery.info["center_mm"]
                bh = battery.info["box_mm"][2]
                kw["center_mm"] = (bc[0], bc[1], bc[2] - 0.5 * bh - 1.0 - 0.5 * box[2])
            try:
                part = P.contain(box, shell, **kw)
            except Exception:                       # a scale that cannot even meet the shell
                continue
            last = part
            if part.info.get("fits_with_clearance"):
                part.info["rev0_dims_mm"] = list(dims)
                part.info["scale_applied"] = sc
                break
        if last is None:
            raise RuntimeError(f"build_internals: no scale in INTERNAL_SCALES placed {name!r}")
        if last.name.endswith("battery"):
            battery = last
        parts.append(last)
    return parts


def _leg_axis_at(z_mm: float) -> tuple:
    """(x, y) of the front-left strut axis at height `z_mm`, on the measured path."""
    zs = [p[2] for p in LEG_PATH_MM]
    xs = [p[0] for p in LEG_PATH_MM]
    ys = [p[1] for p in LEG_PATH_MM]
    return (float(np.interp(z_mm, zs[::-1], xs[::-1])),
            float(np.interp(z_mm, zs[::-1], ys[::-1])))


def _belly_z_mm(shell_mesh, x_mm: float, y_mm: float) -> float:
    """Lowest surface of the fairing under (x, y) [mm], by a ray cast straight down."""
    origin = np.array([[x_mm * MM, y_mm * MM, 0.0]])
    hits = shell_mesh.ray.intersects_location(origin, np.array([[0.0, 0.0, -1.0]]))[0]
    if len(hits) == 0:
        raise RuntimeError(f"_belly_z_mm: no shell under ({x_mm}, {y_mm}) mm")
    return float(hits[:, 2].min()) / MM


def build_vision(fairing, gear, group: str = "camera") -> list:
    """P4-6 — the four vision sensors, each cut against the part it sits on (review fix R11).

    Forward obstacle-sensing pair on the landing gear (User Manual v1.2 p.8 callout [6], p.21)
    and the downward vision pair on the belly (callout [12]); no GPS puck, no rear stereo pair,
    no side infrared boxes. `gear` is `build_gear`'s list, whose first four entries are the
    struts in the order (front-left, rear-left, rear-right, front-right)."""
    parts = []
    #  ⚠ The forward sensor sits in the corner where the front strut meets the arm fairing and the
    #  delivery's cylinder was buried in **both** — 5 of 26 vertices 2.2 mm into the gear and 7 of
    #  26 4.2 mm into the body. It is cut against the **strut**, which is what the manual mounts it
    #  on ("cameras that installed on landing gear", User Manual v1.2 p.21), so the strut is what
    #  holds it; the 4.2 mm that reaches into the fairing is left and is reported.
    #  Cutting against strut ∪ fairing was built and measured: it does drive every sensor's
    #  interpenetration to 0.000 mm, but `difference` against two separate closed shells left a
    #  2-face fragment and the `camera` group came back as 9 components instead of the declared 5,
    #  which is a frozen C.1 row. Rejected for that reason, at four different tube lengths.
    front = {+1: gear[0], -1: gear[3]}          # the two struts the forward pair sits on
    ax, _ay = _leg_axis_at(VISION_FWD_Z_MM)
    x_f = ax + 0.5 * LEG_ROOT_SECTION_MM[0] + VISION_FWD_H_M / MM / 2.0 - 2.0
    half = VISION_FWD_H_M / MM / 2.0
    for k, sy in enumerate((-1, +1)):
        y = sy * VISION_FWD_Y_MM
        path = [(x_f - half - VISION_CUT_DEPTH_MM, y, VISION_FWD_Z_MM),
                (x_f + half, y, VISION_FWD_Z_MM)]
        d = 2.0 * VISION_FWD_R_M / MM
        parts.append(P.attached_leg(path, (d, d), (d, d), group=group, host=front[sy],
                                    name=f"p4_vision_fwd{k}", shape="tube", n_pts=12, n_sec=2,
                                    declare_components=1))
    for k, (dx, dy) in enumerate(VISION_DWN_XY_MM):
        z_belly = _belly_z_mm(fairing.mesh, dx, dy)
        zc = z_belly + VISION_DWN_H_M / MM / 2.0 - 2.0
        half = VISION_DWN_H_M / MM / 2.0
        path = [(dx, dy, zc + half + VISION_CUT_DEPTH_MM), (dx, dy, zc - half)]
        d = 2.0 * VISION_DWN_R_M / MM
        parts.append(P.attached_leg(path, (d, d), (d, d), group=group, host=fairing,
                                    name=f"p4_vision_dwn{k}", shape="tube", n_pts=10, n_sec=2,
                                    declare_components=1))
    return parts


def build_frame(spec):
    """The revision-1 frame of `phantom4`, as `drone_rev.build_frame_rev` expects it.

    Returns a `cadkit.Assembly` whose parts were added with `Assembly.add`; the caller applies
    revision 0's union semantics (`drone_rev.finish_frame_assembly`)."""
    from cadkit import Assembly

    fairing = build_x_fairing("body")
    motors = build_motors("body")
    gear = build_gear(fairing)
    camera = build_camera(fairing)
    vision = build_vision(fairing, gear)
    internals = build_internals(fairing)

    A = Assembly()
    A.add(fairing.mesh, fairing.group)
    for p in motors + gear + camera + vision + internals:
        A.add(p.mesh, p.group)

    A.rev1_parts = [fairing] + motors + gear + camera + vision + internals
    return A
