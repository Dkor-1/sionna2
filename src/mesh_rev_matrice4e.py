# -*- coding: utf-8 -*-
"""mesh_rev_matrice4e.py — registry entries for the Matrice 4E (plan A.1, E.2).

`src/mesh_rev.py` imports this module the first time revision >= 1 is asked for on this key and
reads the module-level `ENTRIES`. One row per (key, revision). A row is never edited after its
fingerprint is frozen — a changed geometry is the next revision number.

Revision 1 (2026-09-17)
    Builder     src/drone_rev1_matrice4e.py  (frame)   and
                src/drone_parts_rev1.py      (P6 propeller)
    Sources     docs/mesh_rev1/matrice4e_sources.json
    Thresholds  docs/mesh_rev1/matrice4e_acceptance_thresholds.json (frozen before the first
                acceptance run; its sha256 is recorded below)
    Plan rows   B.3 M4E-1 ... M4E-8, rules B.0 / B.1 / B.2.
"""
from __future__ import annotations

from mesh_rev import Component, RevEntry

_CAD = "assets/meshes/reference/matrice4-M4T_v2.step (DJI official Matrice 4T STEP, gitignored)"
_UM = "DJI Matrice 4 Series User Manual v1.2 (2025.04) EN"
_PHOTOS = "assets/photos/matrice4e/ (owned product and teardown photos, SOURCES.md)"
_SPIN = "scratch/wf/b1_spin.md + scratch/mesh_rev1/spin/ (owned photo reads, " + _UM + " p.20)"
_SRC = "docs/mesh_rev1/matrice4e_sources.json"

ENTRIES = (
    RevEntry(
        key="matrice4e",
        rev=1,
        # ---- spec overrides -------------------------------------------------
        #  envelope_mm=None   : plan B.0, no fit; frame_fit_scale becomes exactly (1, 1, 1).
        #  rotor_z_mm         : plan B.0's rotor-z rule, target mount z minus
        #                       motor_bell_top_z_m(spec) (= -12.42 + 16.3 = 3.88 mm). The target
        #                       mount z is the CAD prop-adapter top (15.30 front, 6.72 rear) plus
        #                       the 1.5 mm standoff declared in drone_rev1_matrice4e.
        #                       PROP_STANDOFF_MM — a mesh-validity gap, not a physical claim.
        #  rotor_dirs         : plan B.2, the measured pattern — front-left and rear-right
        #                       clockwise, in rotor_deg order (FL, RL, RR, FR).
        #  Nothing else changes: wheelbase, rotor xy, prop diameter, blade count, rotor count,
        #  hover rpm and base_ang are all revision 0's (plan B.0, checked by C.3 and C.8).
        overrides=(
            ("envelope_mm", None),
            ("rotor_z_mm", (12.92, 4.34, 4.34, 12.92)),
            ("rotor_dirs", (-1, 1, -1, 1)),
        ),
        components=(
            Component(
                id="M4E-1",
                change="Remove the internal metal plate 142 x 67.6 x 7.1 mm from the battery "
                       "group. Revision 0 put 51.1 % of it outside the shell, up to 21.6 mm "
                       "through the belly, and it made 5,572 of the 9,149 mm2 facing nadir.",
                grade="medium-high",
                sources=("src/drone_cad.py:623-627 (the code's own comment records that the box "
                         "was never measured)",
                         _PHOTOS + " teardown t13/t14 (grey plastic frame, no metal plate)",
                         _SRC + "#M4E-1"),
                groups=("battery",),
            ),
            Component(
                id="M4E-2",
                change="Replace the flat 82 x 74 mm nose cap with the beak over the gimbal "
                       "cradle: the shell's own floor rises from z 1.0 at x=+72 to 39.0 at "
                       "x=+152, and a second CAD-measured loft carries the cradle below it.",
                grade="high",
                sources=(_CAD + " solids 109/124/123/120 (shell and nose top cover) and "
                                "49/56/57/58 (gimbal cradle), sectioned every 8 mm",
                         _SRC + "#M4E-2a,#M4E-2b,#M4E-2c"),
                groups=("body",),
            ),
            Component(
                id="M4E-3",
                change="Close the tail shell around the battery. The pack keeps its official "
                       "145.47 x 60.6 x 46.3 mm and its CAD bay position and is contained by P8 "
                       "with 1 mm clearance where the shell allows it (see the declared "
                       "deviation M4E-3c).",
                grade="high",
                sources=(_UM + " battery table p.103 (BPX345-6741-14.76)",
                         _CAD + " battery-bay solid 118 (front face x = +70.10, floor z = -6.14)",
                         _SRC + "#M4E-3a,#M4E-3b,#M4E-3c"),
                groups=("battery", "body"),
            ),
            Component(
                #  ⚠ REWRITTEN 2026-09-18 (review fixes F-1 and F-2). The delivered wording said
                #  "heading 67 deg, leaving the body side at x = +85 +/- 5" and one section law
                #  root -> motor pad. The heading is now the review's re-measured 67.58 deg and
                #  the root x that follows from it, with revision 0's rotor centre pinned, is
                #  84.02 mm; and the arm is two segments so that the pad flare stays at the pad.
                id="M4E-4",
                change="Straight front arms on the CAD arm axis: heading 67.58 deg, crossing the "
                       "body side |y| = 47.08 at x = 84.02 mm, bow 0 by construction (revision 0 "
                       "bowed 5.5 mm), reaching revision 0's rotor centres. Each arm is two P4 "
                       "segments: the CAD's near-constant shaft section (front 12.70 x 15.40 at "
                       "the root to 12.12 x 13.29) and a 20 mm motor-pad flare to 27.61 x 12.16. "
                       "The rear arms are rebuilt the same way from the CAD rear-arm solid.",
                grade="high",
                sources=(_CAD + " front-arm solid 98 and rear-arm solid 92, true plane sections "
                                "normal to the fitted arm axis every 2.5 mm",
                         "scratch/mesh_rev1/impl/matrice4e/fix_0918/cad_arm_sections.py and "
                         ".json (the 2026-09-18 re-measurement)",
                         _SRC + "#M4E-4a..#M4E-4g"),
                groups=("body",),
            ),
            Component(
                id="M4E-5",
                change="Fuselage sides and belly from the same CAD section table; the belly "
                       "comes up from -34.74 to the CAD -30.81 mm.",
                grade="high",
                sources=(_CAD + " belly cover solid 119", _SRC + "#M4E-5"),
                groups=("body",),
            ),
            Component(
                id="M4E-6",
                change="Motor stack from the CAD: a 27.0 x 16.3 mm can on the arm-end pad with a "
                       "27.0 mm prop adapter on top (7.51 front / 6.75 rear), so the stack top lands "
                       "on the CAD 15.30 / 6.72 mm; rotor_z_mm then seats the propeller there "
                       "plus a declared 1.5 mm mesh-validity standoff.",
                grade="high",
                sources=(_CAD + " bell solids 105/76 and 95/84, prop-mount solids 103/78 and "
                                "96/83",
                         _SRC + "#M4E-6a..#M4E-6d"),
                groups=("motor", "body"),
            ),
            Component(
                id="M4E-7",
                change="Gimbal camera block width 59 -> 64 mm. Height, depth, centre, yaw post "
                       "and damping plate are revision 0's.",
                grade="medium-high",
                sources=(_PHOTOS + " front product cut matrice 4E_1.png (63-65 mm, scale "
                                   "0.6249 mm/px)",
                         _SRC + "#M4E-7"),
                groups=("camera",),
            ),
            Component(
                id="M4E-8",
                change="Propeller from drone_parts_rev1.propeller_rev1 (P6): the thick rounded "
                       "edge leads and is raised for each rotor's own direction. Revision 0 "
                       "raised the +y edge while the blunt edge and the sweep were at -y.",
                grade="high",
                sources=("three owned reference propellers (solo_prop_ccw.stl, solo_prop_cw.stl, "
                         "1345_prop_cw.stl) and the DJI Mini 2 official GLB",
                         "scratch/mesh_0917/matrice4e/prop_section_0p7R_ours_vs_refs.png",
                         _SRC + "#M4E-8"),
                groups=("prop",),
            ),
            Component(
                #  ⚠ ADDED BY THE ADVERSARIAL REVIEW 2026-09-18 (review fix R-6). Revision 1
                #  drops revision 0's separate canopy loft: the `canopy` group falls from 2
                #  parts / 2,528 faces to 1 part / 288 faces and its plastic surface from
                #  33,614 to 6,313 mm2 (-81.2 %). That is a geometry change of the same size as
                #  several of the rows above, and it had no component row, no grade and no
                #  source. It is not a new decision — the CAD station table of M4E-2a already
                #  carries the upper shell (CAD solid 124, up to z 89.69), so the loft is
                #  absorbed rather than deleted — but it must be declared to be auditable.
                #  RF-neutral in material: `body` and `canopy` both map to DRONE_GROUP_MAT
                #  'plastic', so only the shape changes, not the material.
                id="M4E-9",
                change="Revision 0's separate canopy loft over the body is absorbed into the "
                       "M4E-2a shell station table, which now carries the upper shell itself. "
                       "The canopy group keeps only the RTK turret (2 parts -> 1, 33,614 -> "
                       "6,313 mm2). Both groups are material 'plastic', so nothing changes "
                       "material, only shape.",
                grade="high",
                sources=(_CAD + " upper-shell solid 124 (z up to 89.69), already the source of "
                                "the M4E-2a z_top stations",
                         _SRC + "#M4E-9"),
                groups=("canopy", "body"),
            ),
            Component(
                #  ⚠ ADDED 2026-09-18 (review fix F-3, review defects D3 and D4).
                id="M4E-10",
                change="After each group's revision-0 boolean union, the boolean's sliver "
                       "triangles are removed by a guarded half-edge collapse (edges <= 1.5 mm, "
                       "manifold link condition checked, any pass that opens the solid, changes "
                       "its component count, moves its volume by > 0.5 % or its surface by "
                       "> 0.5 mm is discarded). Frame slivers go 370 -> 16 under 0.5 deg "
                       "(revision 0: 95) and 640 -> 52 under 1.0 deg (revision 0: 170); sliver "
                       "area 2,294 -> 257 mm2. No station table, dimension or placement changes; "
                       "the worst measured surface movement is 0.329 mm (lambda/157 at 5.8 GHz, "
                       "1/8 of the repository's own facet rule).",
                grade="high",
                sources=("plan docs/MESH_REV1_PLAN_0917.md C.1 (slivers within revision-0 "
                         "budgets, 0 self-intersections)",
                         "src/mesh_check.py SLIVER_MIN_ANGLE_DEG = 0.5 and the per-airframe "
                         "sliver budget the repository already enforces",
                         "the per-group `sliver_repair` block of the build report, which records "
                         "every number the repair produced and every pass it refused",
                         _SRC + "#M4E-10"),
                groups=("body", "battery", "pcb", "gear", "camera", "motor", "canopy", "accent"),
            ),
            Component(
                id="R-SPIN",
                change="rotor_dirs = (-1, +1, -1, +1) in rotor_deg order: front-left and "
                       "rear-right clockwise seen from above, the opposite of revision 0's "
                       "alternating default.",
                grade="medium-high",
                sources=(_SPIN, _UM + " p.20 (prop A at front-right and rear-left, B at "
                                      "front-left and rear-right)",
                         _SRC + "#R-SPIN"),
                groups=("prop",),
            ),
        ),
        frame_builder="drone_rev1_matrice4e:build_frame",
        prop_builder="drone_parts_rev1:propeller_rev1",
        #  ⛔ Frozen only after plan C.1-C.13 pass (plan C.14). Until then the sweep CLI refuses
        #     to run this revision, while the builder and the acceptance tools still work.
        #  ⏳ PLACEHOLDER — plan C.14 freezes the fingerprint only after C.1-C.13 pass, and 7 of
        #     159 scored rows are still failing (see the acceptance ledger and the report). The
        #     geometry changed on 2026-09-18 (review fixes F-1, F-2, F-3), so the value is no
        #     longer the delivery's 8cdbc9eb…935c; it is now
        #         fc0bbae9716c291673d2fb37b3d63e261e3a8d4eb37c213a41e7a7d94b9997ac
        #     computed with mesh_rev.fingerprint_for('matrice4e', 1) on the production venv and
        #     reproduced bit-for-bit in four processes at OMP/MKL/OpenBLAS threads 1 and 2.
        #     ⛔ This unit does NOT freeze it: the merge stage does, after the shared modules are
        #     reconciled and the user has ruled on the 7 rows and the two deviations. With the
        #     field None, mesh_rev.run_spec refuses --mesh-rev 1 for this key, the safe state.
        #  -- MERGE STAGE 2026-09-18 ------------------------------------------------
        #  Verified in the merged tree (all four builders + the reconciled shared
        #  modules in one checkout, live HEAD 9425dfe8 + E0):
        #      fc0bbae9716c291673d2fb37b3d63e261e3a8d4eb37c213a41e7a7d94b9997ac
        #  Recomputed there with mesh_rev.fingerprint_for on the production venv and
        #  identical in 6 runs -- OMP/MKL/OpenBLAS threads 1, 2 and 4 x two processes.
        #  It equals the value this drone's own unit reported, so reconciling the
        #  shared modules moved no geometry.
        #  NOT FROZEN. Plan C.14 freezes only after C.1-C.13 pass, and
        #  7 of 159 scored rows fail (2 of them under DEV-5/DEV-6, which are declared but NOT approved), and plan C.1 asks for 0 self-intersections while the mesh has 18.
        #  Plan critique M8 forbids relaxing a threshold after seeing a failure, so the
        #  merge stage cannot clear these by itself -- the user rules first. While this
        #  field is None, mesh_rev.run_spec refuses --mesh-rev 1 for this key, which is
        #  the safe state: no unaccepted geometry can reach a shard name.
        fingerprint=None,
        #  sha256 of docs/mesh_rev1/matrice4e_acceptance_thresholds.json, frozen 2026-09-17
        #  21:30 UTC, before the first acceptance run.
        thresholds_sha256="58872e31193330861cc3220277fabf91046c9aef3df5872566b1afddf0333942",
        note="Revision 1, 2026-09-17. Plan docs/MESH_REV1_PLAN_0917.md B.3. The height target is "
             "the CAD 151.52 mm; the official 149.5 mm is reported alongside (declared choice). "
             "Carried over from revision 0 unchanged: legs, deck fisheyes, downward vision "
             "lenses, beacon, RTK turret (now reaching the CAD 91.70 mm because there is no "
             "envelope fit) and the mainboard box, whose size has no source and is an open "
             "question for the user.",
    ),
)
