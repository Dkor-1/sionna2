# -*- coding: utf-8 -*-
"""mesh_rev_phantom4.py — registry entries for the DJI Phantom 4 (plan A.1, B.5).

`mesh_rev._load_key('phantom4')` imports this module and reads `ENTRIES`. Revision 0 is not
listed: it is `drones.DRONES['phantom4']` itself and stays the default.

Revision 1 is the plan's rows P4-1 … P4-8, built by `drone_rev1_phantom4.build_frame` with the
shared parts of `drone_parts_rev1`. Every dimension it uses is traced in
docs/mesh_rev1/phantom4_sources.json; that file's sha256 and the acceptance thresholds' sha256
are recorded here so that neither can drift away from the geometry this entry names.
"""
from __future__ import annotations

from mesh_rev import Component, RevEntry

_SCAN = ("scratchpad/mesh_0917/phantom_family/data/p4_scan_analysis_datum.json "
         "(owned CC-BY Phantom 4 scan, datum frame; producer scripts/scan_analysis.py)")
_SCAN_RAW = ("scratchpad/mesh_0917/phantom_family/data/p4_datum_scan_samples.npy "
             "(2e6 surface samples of the same scan; measured by work/scan_measure.py)")
_QSG = "Phantom_4_Quick_Start_Guide_v1.2_en_160317.pdf p.7 dimension figure (196 / 289.5 mm)"
_UM8 = "Phantom_4_User_Manual_en_v1.2_160328.pdf p.8 Aircraft Diagram (front, rear, side, bottom)"
_UM20 = "Phantom_4_User_Manual_en_v1.2_160328.pdf p.20 Obstacle and Vision Positioning System"
_SPIN = ("scratchpad/wf/b1_spin.md — User Manual v1.2 p.7 propeller figure and p.23 ring-colour "
         "rule; front-left and rear-right clockwise seen from above (grade medium-high)")

ENTRIES = (
    RevEntry(
        key="phantom4",
        rev=1,
        overrides=(
            #  P4-1: no envelope fit. frame_fit_scale becomes exactly (1, 1, 1); revision 0 was
            #  (1, 1, 0.93731) because 196 mm was forced onto the props-off frame.
            ("envelope_mm", None),
            #  P4-8: the measured spin pattern (front-left / rear-right clockwise from above).
            ("rotor_dirs", (-1, 1, -1, 1)),
            #  P4-4 with plan B.0: rotor z is explicit. drones._arm_motor_dims puts the prop
            #  mount plane at motor_bell_top_z_m + standoff = 21.70 mm for this key, and the scan
            #  puts the real mount plane at +24.9 mm, so the offset is +3.20 mm.
            ("rotor_z_mm", (3.2, 3.2, 3.2, 3.2)),
            #  The one-piece X fairing carries the whole shell, so the revision-0 split into a
            #  'body' shell plus a raised 'canopy' is gone. Both groups are the same material
            #  (plastic); no material group is added.
            ("cad_version", "rev1"),
        ),
        components=(
            Component(
                id="P4-1", grade="high",
                change="envelope_mm=None: the props-off frame is built to the scan's 180.2 mm "
                       "(feet -153.37, crown +26.8) instead of being stretched to the official "
                       "196 mm, which the QSG dimension line measures to the top of a propeller.",
                sources=(_SCAN, _QSG, _UM8), groups=("body",)),
            Component(
                id="P4-2", grade="high",
                change="Oval pod -> X-shaped fairing (P2): centre pod from the scan's y=0 "
                       "centre-line sections, four arm fairings from the scan's sections "
                       "perpendicular to each 45 deg arm axis, and (review fix 2026-09-18) the "
                       "narrow keel rib the scan shows under each arm outboard of r = 113 mm, "
                       "with the arm stations from r = 115 outward carrying the measured flank "
                       "instead of the keel depth. The tail is rebuilt on the scan's own aft "
                       "sections: it ends at x = -74.57 instead of -76.0, its crown at x = -74 "
                       "is 3.6 mm lower, and it is no longer 14 mm per side narrower than the "
                       "scan between x = -74 and -70.",
                sources=(_SCAN, _SCAN_RAW), groups=("body",)),
            Component(
                id="P4-3", grade="medium-high",
                change="Camera and gimbal (P7 x3 on a yaw post) at the manual's position: "
                       "x -13.0 ... +62.2 mm, bottom 28.5 mm above the feet, no longer buried.",
                sources=(_UM8,), groups=("camera",)),
            Component(
                id="P4-4", grade="high",
                change="Disc motors -> cans (P3): plastic pod revolved from the scan's own "
                       "radial profile, a barrel 17.62 / 19.02 / 18.83 / 14.73 mm in radius "
                       "bottom to top, so it measures 37.44 mm on the scan's r50 rule at "
                       "z = -5 where the scan reads 37.8 (review fix 2026-09-18; the delivery's "
                       "single cone measured 35.03 mm and passed the frozen 38.0 +- 3.0 by "
                       "0.03 mm); metal can 28.2 mm with a 22.1 mm straight wall; prop "
                       "adapter topping out on the scan's +24.9 mm mount plane, which "
                       "rotor_z_mm then matches.",
                sources=(_SCAN,), groups=("body", "motor")),
            Component(
                id="P4-5", grade="high",
                change="Legs attached (P5): four struts on the scan's measured axis plus the two "
                       "skids that join them, each cut against the fairing so the gap is 0.",
                sources=(_SCAN, _SCAN_RAW), groups=("gear",)),
            Component(
                id="P4-6", grade="high",
                change="GPS puck and Pro-only sensors removed: the base Phantom 4 has forward "
                       "obstacle sensing and a downward vision system only; the rear stereo pair "
                       "and the side infrared pair arrived with the P4 Pro, and the puck came "
                       "from a P4 Pro+ V2.0 photo.",
                sources=(_UM8, _UM20, _SCAN), groups=("camera",)),
            Component(
                id="P4-7", grade="high",
                change="Internals contained (P8): every internal box is wholly inside the shell "
                       "with at least 1 mm of clearance. Their sizes stay revision 0's, shrunk "
                       "by the largest scale that fits; they are declared engine knobs, not "
                       "measurements (phantom4_sources.json, unsourced_engine_knobs).",
                sources=(_SCAN,), groups=("battery", "pcb")),
            Component(
                id="P4-8", grade="medium-high",
                change="P6 propeller orientation (the thick raised edge leads) and rotor_dirs = "
                       "the measured pattern, front-left and rear-right clockwise from above.",
                sources=(_SPIN,), groups=("prop",)),
        ),
        frame_builder="drone_rev1_phantom4:build_frame",
        prop_builder="drone_parts_rev1:propeller_rev1",
        #  ⛔ NOT FROZEN YET — plan C.14 freezes only after C.1…C.13 pass, and the merge stage
        #  freezes it, not this file.
        #  The value this geometry produces after the 2026-09-18 review fixes is
        #      087aae89eed1724193a102714f37f729d7e8acc7e2cb220c2a50903dde2cdf09
        #  (mesh_rev.fingerprint_for('phantom4', 1) on the production venv py312). The delivered
        #  geometry's value was f79cfcfee87f1b7f6a9b343aa7235edc7563b38ece721ed33eca94f533033a92;
        #  R8…R11 moved geometry, so it had to change. It stays out of this field until the four
        #  acceptance rows in docs/mesh_rev1/phantom4_acceptance_deviations.json →
        #  failures_left_standing are resolved: `mesh_rev.run_spec` refuses a run whose entry has
        #  no fingerprint, and that refusal is what keeps an unaccepted geometry out of the shard
        #  names.  FINGERPRINT_PLACEHOLDER
        #  -- MERGE STAGE 2026-09-18 ------------------------------------------------
        #  Verified in the merged tree (all four builders + the reconciled shared
        #  modules in one checkout, live HEAD 9425dfe8 + E0):
        #      087aae89eed1724193a102714f37f729d7e8acc7e2cb220c2a50903dde2cdf09
        #  Recomputed there with mesh_rev.fingerprint_for on the production venv and
        #  identical in 6 runs -- OMP/MKL/OpenBLAS threads 1, 2 and 4 x two processes.
        #  It equals the value this drone's own unit reported, so reconciling the
        #  shared modules moved no geometry.
        #  NOT FROZEN. Plan C.14 freezes only after C.1-C.13 pass, and
        #  9 of 139 scored rows fail; the four groups are the C.1 sliver fraction, C.2b prop area in the bell, C.5 camera visibility and C.7 blade angle.
        #  Plan critique M8 forbids relaxing a threshold after seeing a failure, so the
        #  merge stage cannot clear these by itself -- the user rules first. While this
        #  field is None, mesh_rev.run_spec refuses --mesh-rev 1 for this key, which is
        #  the safe state: no unaccepted geometry can reach a shard name.
        fingerprint=None,
        thresholds_sha256="086f93cf32b98b00d24332074cd74319452981b5b8769e59a1ace6a68c395d8b",
        note="Phantom 4 revision 1, 2026-09-17, review fixes 2026-09-18. Datum frame = "
             "p4_datum.json (feet at z = -153.37 mm, motor diagonal 350 mm). Rotor xy, "
             "wheelbase, prop diameter, blade count, rotor count, hover rpm and base_ang are "
             "revision 0's. Acceptance: 130 of 139 scored rows pass. The 9 failing rows are "
             "four checks: C.1 sliver fraction, C.2b prop area inside the bell, C.5 camera "
             "visible area and C.7 blade angle at r/R 0.3 and 0.7 on both propellers. The last "
             "three are properties of the shared P6 blade and of revision 0's oversized gimbal, "
             "not of this builder. The 2026-09-18 round fixed the motor pod (35.03 -> 37.44 mm), "
             "the tail (aft tip -76.0 -> -74.57 mm, and the 14 mm notch between tail and arms "
             "closed), the arm underside (flank + keel rib, 3-4 mm of error removed at "
             "r = 120-150) and the four vision sensors (now cut against their host, not held by "
             "interpenetration). It left C.1 at 0.02589 against the delivery's 0.02607, changed "
             "no threshold, and needed one additive keyword on the shared "
             "drone_parts_rev1.motor_can. See docs/mesh_rev1/phantom4_acceptance_deviations.json "
             "-> reviewer_2026_09_17 and review_fix_2026_09_18, and "
             "REVIEW_FIX_CHANGELOG_phantom4.md.",
    ),
)
