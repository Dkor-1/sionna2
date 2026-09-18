# -*- coding: utf-8 -*-
"""mesh_rev_mavic4pro.py — registry entries for the DJI Mavic 4 Pro (plan A.1, E.2).

`src/mesh_rev.py` imports this module the first time revision >= 1 is asked for on the key
"mavic4pro" and reads the module-level list `ENTRIES`. Revision 0 is `drones.DRONES["mavic4pro"]`
and is never listed here.

The geometry lives in `src/drone_rev1_mavic4pro.py`; this file holds only what the registry needs:
the spec overrides, the component list with an evidence grade and owned sources per component, and
the frozen fingerprint. ⛔ Once `fingerprint` is set, the geometry of ("mavic4pro", 1) is fixed —
any later change is revision 2 with a new pre-registration (plan B.0, C.14).
"""
from __future__ import annotations

from mesh_rev import Component, RevEntry

import drone_rev1_mavic4pro as G

#: Plan B.0: `rotor_z_mm` = target mount z − `motor_bell_top_z_m(spec)` − standoff, where the
#: target is the top of the revision-1 motor stack. `drone_cad.PROP_STANDOFF_M` has no mavic4pro
#: entry, so the standoff is 0 and the bell top is `MOTOR_BASE_Z` (default 0.014 · diagonal) plus
#: the spec's `motor_h_mm` — which the overrides below set to revision 0's REALIZED bell height,
#: so the bell top is 6.174 + 33.819 = 39.993 mm with no fit. The target is revision 0's realized
#: prop mount plane, (0.014 + 0.048) × 441 mm × REV0_SZ = 43.68343 mm, so the offset is 3.690 mm.
#: `mesh_rev1_acceptance` checks the realized mount z against revision 0's to 1e-3 mm.
_BELL_TOP_MM = 0.014 * 441.0 + G.MOTOR_CAN_H_MM
#: `drones.rotor_layout` reads `rotor_z_mm` as a per-rotor sequence, so all four
#: rotors get the same offset: this aircraft has no front/rear stagger (declared).
ROTOR_Z_MM = (round(G.ROTOR_MOUNT_Z_MM - _BELL_TOP_MM, 9),) * 4

#: Measured rotor spin, seen from above: FL and RR clockwise, FR and RL counter-clockwise.
#: `drones.rotor_layout` calls +1 counter-clockwise, so in `rotor_deg` order (FL, RL, RR, FR) the
#: measured pattern is (−1, +1, −1, +1) — the exact opposite of revision 0's (+1, −1, +1, −1).
#: Grade **high** for this aircraft: the B1 spin round read 4/4 rotors on the product render
#: (width ratios 1.8, 1.8, 4.0, 4.1), 2/4 on a real production-unit photo (p08, 5.3× and 6.4×),
#: the hub colour marks A at FR+RL and B at FL+RR on the same photo, A CCW / B CW directly on the
#: loose propellers c10 and c11, and the same A/B positions plus lock directions in manual v1.0
#: p.54. It is the only aircraft in the round whose lock-to-spin rule was confirmed on hardware.
ROTOR_DIRS = (-1, 1, -1, 1)

_SRC_PHOTO_TOP = (
    "assets/photos/mavic4pro/mavic4pro_c02_arm_positions_topview_labelled.jpg (owned top view); "
    "registration and profile: scratch mesh_rev1/impl/mavic4pro/work/measure_planform.py + "
    "planform_c02.json, 0.57912 mm/px from B1's ruler-scaled front track 363.92 mm over the "
    "measured 628.4 px front hub separation; image axes = aircraft axes to 0.03 deg; scale "
    "cross-checked against the official 267 mm propeller (tip-to-tip 260.3-264.1 mm) and the "
    "official unfolded width 390.5 mm (front track + can = 393.2 mm). "
    "⚠ third-party product image (djioemparts.com watermark) held in our photo set; tolerance "
    "+-3 mm on every width and span")
_SRC_ARM = (
    "same photo; mid-line axis fit scratch mesh_rev1/impl/mavic4pro/work/arm_axis.py + "
    "arm_axis.json (front 68.28-68.66 deg, rms 0.35-0.43 mm over 52-64 stations; rear "
    "128.52-130.16 deg, rms 0.70-1.18 mm). Both arm edges enter the estimator, so no arm "
    "half-width is assumed")
_SRC_B1_HEIGHT = (
    "B1 height round, scratch wf/b1_height.md and mesh_rev1/height/work/m4p_height_ledger.json — "
    "a ruler-scaled rigid multi-view fit of the FCC SS3-L3AB2410 external photos "
    "(p02/p05/p06) over 4 rotors x 3 views, 40 Monte-Carlo draws plus systematic variants")
_SRC_FCC = (
    "FCC ID SS3-L3AB2410 External Photos, saved in assets/photos/mavic4pro as p01-p07 with the "
    "laboratory steel rules in frame; see assets/photos/mavic4pro/SOURCES.md. "
    "⚠ the FCC unit is a pre-production (EVT) sample: shape and internal layout are usable, "
    "surface finish and colour are not")
_SRC_MANUAL = (
    "DJI Mavic 4 Pro User Manual v1.0 (2025-05), "
    "https://dl.djicdn.com/downloads/mavic-4-pro/20250513/DJI_Mavic_4_Pro_User_Manual_v1.0_en.pdf, "
    "sha256 ff577662dfb7163899ed8f365ef6b21c0b0fad7e6e3481457bfa2f3768170bf7, saved text "
    "scratch mesh_rev1/impl/mavic4pro/work/m4p_manual.txt")
_SRC_SPIN = (
    "B1 spin round, scratch wf/b1_spin.md and mesh_rev1/spin/spin_evidence_20260917.json "
    "(mavic4pro row, grade high): product render 4/4 rotors, production photo p08 2/4, hub "
    "colour marks, loose propellers c10/c11, manual v1.0 p.54")
_SRC_INVENTORY = (
    "mesh inventory round, scratch wf/mesh_inv_mini5pro.md and mesh_0917/dji_folding/ "
    "(metrics_mavic4pro.json, renders/, crops/); FCC p05 read at 0.3964 mm/px, +-1-2 mm")

COMPONENTS = (
    Component(
        id="M4P-1", grade="medium-high", groups=("body",),
        change="Shell planform replaced: x span -72.5 ... +126.0 mm with the measured width "
               "stations (68.9 mm at the waist, 92.1 mm at the rear shoulders, 86.9 mm at the "
               "front shoulders), instead of revision 0's -114.2 ... +89.8 mm and its constant "
               "118.08 mm width. The shell moves 39.0 mm forward and loses 26-49 mm of width. "
               "The vertical section law is revision 0's, carried across normalised fore-aft "
               "position (the height stretch stays, see the module docstring).",
        sources=(_SRC_PHOTO_TOP,)),
    Component(
        id="M4P-2", grade="medium-high", groups=("motor", "body"),
        change="Motor can diameter 45.86 -> 29.33 mm. Revision 0's value was 0.052 x diagonal "
               "used as a RADIUS, i.e. a diagonal proportion, not a measurement. The can height "
               "is revision 0's realized carry-over.",
        sources=(_SRC_B1_HEIGHT, _SRC_INVENTORY)),
    Component(
        id="M4P-3", grade="medium-high", groups=("camera",),
        change="The gimbal moves out in front of the nose: front face at x = +175.4 mm instead "
               "of revision 0's +106.9 mm, as a 58.0 x 64.0 mm block with a 30 mm lens barrel "
               "instead of a squashed sphere of which 65 % was buried in the shell. Its floor "
               "keeps revision 0's realized -77.73 mm, which revision 0 solved from the same FCC "
               "front photo so the housing clears the landing feet. "
               "⚠ the POSITION is the measured fact (grade medium-high); the 64 mm height is one "
               "reader's reading of one FCC view (grade medium) and the block/barrel depth split "
               "is construction.",
        sources=(_SRC_PHOTO_TOP, _SRC_INVENTORY, _SRC_FCC)),
    Component(
        id="M4P-4", grade="high", groups=("gear",),
        change="One tapered landing leg per FRONT motor instead of a two-prong A-frame; no rear "
               "legs (unchanged). The foot sits at the rotor axis -0.41 mm aft and +2.92 mm "
               "outboard, B1's fitted foot position, instead of revision 0's y = +-191.9 mm. The "
               "leg's own section is revision 0's carry-over.",
        sources=(_SRC_FCC + " — p05 front elevation and p07 bottom plan", _SRC_B1_HEIGHT)),
    Component(
        id="M4P-5", grade="high", groups=("battery",),
        change="Internal battery box at its official size 128 x 62 x 44 mm instead of revision "
               "0's proportional 118.31 x 80.30 x 54.57 mm box, seated at the tail on the "
               "centreline. ⚠ the SIZE is official (grade high); the axis assignment and the "
               "rearmost-seating rule are ours.",
        sources=(_SRC_MANUAL + " p.88 'Intelligent Flight Battery BWX341-6654-14.3, "
                 "62x44x128 mm, Approx. 331 g'",
                 _SRC_FCC + " — p07 bottom plan and teardown t01/t08/t16")),
    Component(
        id="M4P-6", grade="medium-high", groups=("body",),
        change="Straight arms at the measured headings (front 68.3 deg, rear 129.4 deg from +x) "
               "instead of revision 0's radial arms at the rotor azimuths (51.4 / 128.6 deg), "
               "and 13-14 mm wide instead of 18.5-26.5 mm. Arm tips stay on revision 0's "
               "realized rotor centres. The arm HEIGHT keeps revision 0's width x 0.775 rule.",
        sources=(_SRC_ARM, _SRC_PHOTO_TOP)),
    Component(
        id="M4P-7", grade="high", groups=("prop",),
        change="rotor_dirs set to the measured spin pattern: FL and RR clockwise seen from "
               "above, the exact opposite of revision 0 on all four rotors.",
        sources=(_SRC_SPIN,)),
    Component(
        id="M4P-8", grade="high", groups=("prop",),
        change="The propeller is built by drone_parts_rev1.propeller_rev1 so each blade leads "
               "with its raised, thick edge for its own rotor's rotation (P6). Revision 0's "
               "blades fly trailing-edge first.",
        sources=(_SRC_INVENTORY + " — prop_sections_ours.json, thick edge on the -phi side at "
                 "all 9 stations", _SRC_SPIN)),
)

ENTRIES = [
    RevEntry(
        key="mavic4pro", rev=1,
        overrides=(
            #  plan B.0: no envelope fit in a revision — frame_fit_scale must be exactly (1,1,1).
            ("envelope_mm", None),
            #  plan B.0: rotor z explicit. This reproduces revision 0's realized prop mount plane
            #  (43.68343 mm) on top of the revision-1 motor stack, so the prop seats with a zero
            #  gap and the rotor z is unchanged.
            ("rotor_z_mm", ROTOR_Z_MM),
            ("rotor_dirs", ROTOR_DIRS),
            #  M4P-2 — the measured can, so every consumer of the spec sees the same motor the
            #  mesh has. motor_h_mm is revision 0's realized bell height (carry-over, declared).
            ("motor_dia_mm", round(G.MOTOR_CAN_DIA_MM, 6)),
            ("motor_h_mm", round(G.MOTOR_CAN_H_MM, 6)),
            ("cad_version", "rev1"),
            ("shape_source", "photo_fcc_manual_rev1"),
        ),
        components=COMPONENTS,
        frame_builder="drone_rev1_mavic4pro:build_frame",
        prop_builder="drone_parts_rev1:propeller_rev1",
        #: ⛔ NOT FROZEN YET — plan C.14 freezes the fingerprint only after C.1–C.13 all pass,
        #: and only at the merge stage, after the shared modules are reconciled. Until then
        #: `mesh_rev.run_spec` refuses `--mesh-rev 1` for this key.
        #  -- MERGE STAGE 2026-09-18 ------------------------------------------------
        #  Verified in the merged tree (all four builders + the reconciled shared
        #  modules in one checkout, live HEAD 9425dfe8 + E0):
        #      9359e1f0d8864dc5ec81c8a632f43150d19a978156aea45e1638b59709343c17
        #  Recomputed there with mesh_rev.fingerprint_for on the production venv and
        #  identical in 6 runs -- OMP/MKL/OpenBLAS threads 1, 2 and 4 x two processes.
        #  It equals the value this drone's own unit reported, so reconciling the
        #  shared modules moved no geometry.
        #  NOT FROZEN. Plan C.14 freezes only after C.1-C.13 pass, and
        #  1 of 66 gate rows fails: C.7 blade angle vs revision 0, 0.4961 deg against the 0.2 deg bound. No threshold was ever changed (deviations[] is empty).
        #  Plan critique M8 forbids relaxing a threshold after seeing a failure, so the
        #  merge stage cannot clear these by itself -- the user rules first. While this
        #  field is None, mesh_rev.run_spec refuses --mesh-rev 1 for this key, which is
        #  the safe state: no unaccepted geometry can reach a shard name.
        fingerprint=None,
        #: sha256 of docs/mesh_rev1/mavic4pro_acceptance_thresholds.json, frozen
        #: 2026-09-18 before the first acceptance run.
        thresholds_sha256="afb6b7de4ae586f3b59d44536d44aa9ac43c2dde6dd60d5a3ae489caf2614594",
    )
]
