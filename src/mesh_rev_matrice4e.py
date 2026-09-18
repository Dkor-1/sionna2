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
                #  ⚠ ADDED 2026-09-18 (b4 round, review fix F-4; plan C.1 "0 self-intersections").
                id="M4E-11",
                change="The host the internal boxes are clipped against is the fuselage alone "
                       "(the M4E-2 shell loft unioned with the M4E-2 cradle loft), offset inward "
                       "1 mm by a normal-compensated, fold-free offset instead of a plain "
                       "vertex-normal offset of the whole body union. The body union has 0 "
                       "self-intersecting triangle pairs but its plain 1 mm offset has 92, with "
                       "48 flipped triangles at the arm and motor-pod junctions, and the boolean "
                       "handed those folds to the clipped boxes: battery 3 pairs and mainboard "
                       "15, at the buried root of each rear arm. Now 0 and 0. Compensating the "
                       "offset (d / min(n_vertex . n_face)) also raises the share of internal "
                       "metal at 1 mm or more from the shell from 1.3 % to 83.7 % (battery) and "
                       "1.8 % to 97.2 % (mainboard). No dimension changes: the pack keeps its "
                       "official 145.47 x 60.6 x 46.3 mm and its CAD position, and its clipped "
                       "volume moves 5.398 -> 5.545 % (mainboard 19.319 -> 19.548 %).",
                grade="high",
                sources=("plan docs/MESH_REV1_PLAN_0917.md C.1 (0 self-intersections) and C.2 "
                         "(internal metal >= 1 mm inside the shell)",
                         "the `contain_host` block of the build report, which records the "
                         "realised offset per vertex, the number of clamped vertices and the "
                         "self-intersection count of the host",
                         "scratch/mesh_rev1/b4/matrice4e/work/diag_inset.py, proto_host*.py"),
                groups=("battery", "pcb"),
            ),
            Component(
                #  ⚠ ADDED 2026-09-18 (b4 round, review fix F-5; render defect "the legs are
                #  shorter and further outboard than the CAD's").
                id="M4E-12",
                change="Each landing leg stands on its measured CAD radius: front root 229.75 -> "
                       "foot 216.61 mm, rear root 217.10 -> foot 208.57 mm. Revision 0 put the "
                       "rear pair 10.7 mm inboard of the CAD at the root and 11.4 mm at the "
                       "foot. drone_cad._gear_arm_spikes is unchanged and is called once per "
                       "pair, because the splay that carries a pair from its root radius to its "
                       "foot radius is 15.74 deg at the front and 12.40 deg at the rear and the "
                       "helper takes one scalar splay. The cone, the root and tip diameters, the "
                       "attachment z and the leg length are revision 0's, so all four feet still "
                       "land on the CAD ground plane at -59.82 mm.",
                grade="high",
                sources=(_CAD + " leg solids (front 99, rear 90), sectioned in z",
                         "outputs/meshfix_matrice4e.json row F07 — the repository's own CAD "
                         "audit, which records these radii and says the value was left alone "
                         "only because changing it would move the revision-0 fingerprint",
                         "scratch/mesh_rev1/b4/matrice4e/work/diag_cad2.py (my own read of the "
                         "CAD leg feet: front (135.21, 168.88), rear (-139.39, 155.04))"),
                groups=("gear",),
            ),
            Component(
                #  ⚠ ADDED 2026-09-18 (b4 round, review fix F-6; render defect "the nose
                #  underside is a two-plane notch where the CAD sweeps one concave curve").
                id="M4E-13",
                change="The gimbal-cradle station table is measured every 4 mm over x = 80...120 "
                       "instead of every 8 mm, and its z_top / z_bot are no longer rounded to "
                       "the 1 mm z-bin's floor. The CAD's cradle underside is a FLAT shelf at "
                       "z = -20.62 mm from x = 92 to 110; at 8 mm spacing it was hit at one "
                       "station and the loft ran a V through it. 10 stations -> 15. Same rule, "
                       "same solids, same 4 mm x-band: the width column reproduces the committed "
                       "table to 0.00 mm at all ten original stations, which is the check that "
                       "the rule was reproduced. Every z moves by less than 1 mm except z_bot at "
                       "x = 96 (-19 -> -20.62), where the finer grid finds the shelf. The "
                       "refinement stops at x = 120: refining the whole table made the nose's "
                       "front face nearly vertical and C.5's `body facing az0 el0 (10 deg)` went "
                       "237 -> 1,162 mm2 against a 500 mm2 limit.",
                grade="high",
                sources=(_CAD + " gimbal-cradle solids 49/56/57/58, 4 mm x-bands",
                         "scratch/mesh_rev1/b4/matrice4e/work/cad_stations2.py, "
                         "make_nose_table.py, cad_crown.py",
                         _SRC + "#M4E-2b"),
                groups=("body",),
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
        #  ⏳ PLACEHOLDER — the value below is NOT frozen and the field stays None.
        #
        #  -- b4 ROUND 2026-09-18 (supersedes the delivery's 8cdbc9eb…935c and the merge stage's
        #     fc0bbae9…97ac) -----------------------------------------------------------------
        #  The geometry changed again: M4E-11 (fold-free fuselage containment host), M4E-12 (the
        #  legs on their CAD radii) and M4E-13 (the 4 mm nose underside table). The value is now
        #      7663a959a7a3cd9c9c51760c868049170b106bc34e33a7d7f0472a8d26d1768c
        #  computed with mesh_rev.fingerprint_for('matrice4e', 1) on /workspace/.venvs/py312 and
        #  identical in 6 processes — OMP/MKL/OpenBLAS threads 1, 2 and 4 x two processes.
        #  ⛔ This round does NOT freeze it. Acceptance is 163 scored / 160 passed / 3 FAILED:
        #     C.2c swept-disc clearance on the corrected surface measurement (-0.744 mm; the CAD
        #     airframe itself is -0.811 mm and revision 0 is -2.267 mm under the same discs),
        #     C.4 CAD->ours motors p99 and ours->CAD turret p99, both of which still fail after
        #     the interior-surface narrowing, i.e. they are real shape errors in the motor bell
        #     profile and the RTK cap top. Six deviations (DEV-5 ... DEV-10) are declared in
        #     docs/mesh_rev1/matrice4e_acceptance_deviations.json and await user approval.
        #     While this field is None, mesh_rev.run_spec refuses --mesh-rev 1 for this key,
        #     which is the safe state: no unaccepted geometry can reach a shard name.
        #  == b5 RECONCILE-AND-FREEZE ROUND, 2026-09-18 ==========================
        #  ⛔ NOT FROZEN. The b4 table reproduces exactly on the reconciled tree:
        #       163 scored / 160 passed / 3 FAILED (with the deviations file)
        #       158 scored / 151 passed / 7 FAILED (with the file moved aside)
        #     Fingerprint 7663a959… reproduced in 6 processes (OMP/MKL/OPENBLAS 1, 2, 4 x two).
        #     Revision 0 re-proved bit-identical against a pristine HEAD archive, 10 keys x 4
        #     environment states, 680 equal / 0 different.
        #  The three failing rows are NOT rescued by any declared deviation — DEV-7 narrows two
        #     of them to the visible surface and they still fail, and DEV-9 makes the swept-disc
        #     row fail on a corrected measurement that used to pass on a broken one. Under this
        #     phase's freeze rule (freeze only when every remaining failure is a declared
        #     deviation with evidence) the fingerprint stays None and run_spec keeps refusing
        #     --mesh-rev 1 for this key.
        #  The deviations file was renamed to the common name in the b4 round; two in-code
        #     comments in benchmark/mesh_rev1_acceptance_matrice4e.py still cited the old
        #     matrice4e_deviations_0918.json name and were corrected in this round (the
        #     loader's fallback to the old name is kept).
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
