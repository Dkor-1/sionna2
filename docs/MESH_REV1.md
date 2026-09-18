# Mesh revisions — how to use one

> Design and acceptance plan: `docs/MESH_REV1_PLAN_0917.md`. This file is the operating manual.
> Status 2026-09-18: the mechanism is live (HEAD `9425dfe8`). Four drones have a revision-1
> builder registered. **No fingerprint is frozen, so `--mesh-rev 1` is refused for every key** —
> see “What is frozen” below.

## The idea in one paragraph

Revision 0 is the mesh this repository builds today. It is the frozen default, it is never listed
in the registry, and nothing about it changes: `drones.spec_for(key)` returns the very same
`DRONES[key]` object it always did. A revision is opted into per run, by number, and once its
fingerprint is frozen its geometry is fixed forever — a later change is the next revision number,
never an edit. The revision rides inside the mesh-fix tag of the shard name
(`_mfixbatteryi5rev1_blperairframe`), so every revision-0 name is unchanged and revision names
fail the two literal production-mesh selectors.

## Using a revision

```bash
#  build and inspect, from any driver (no fingerprint needed)
python -c "import drones; spec = drones.spec_for('matrice4e', 1)"

#  a sweep run (refused until the fingerprint is frozen)
python benchmark/elevation_sweep_md.py --drone matrice4e --mesh-rev 1 ...

#  acceptance for one drone
CUDA_VISIBLE_DEVICES="" SIONNA2_ALLOW_CPU=1 MPLBACKEND=Agg nice -n 19 taskset -c 14-15 \
  python benchmark/mesh_rev1_acceptance.py --drone <key> --rev 1 --out <scratch>/ledger.json
```

`--mesh-rev` defaults to 0. A line without it builds revision 0 with identical bytes and an
identical name, which is why running queues are unaffected by any of this.

### Three gates stand between `--mesh-rev 1` and a shard

1. **Canonical switches.** `run_spec` refuses unless `MESH_FIX` is the canonical set and
   `BLADE_LAW` is canonical. A revision is defined on top of the production mesh, not on top of
   an arbitrary switch state.
2. **Registration.** `(key, rev)` must exist in the registry, or `ValueError`.
3. **Fingerprint.** Right after the FastPoser is built, `guard_fingerprint` recomputes a sha256
   over the posed frame vertices, faces and groups, both propellers and `rotor_layout`, and stops
   the run if it differs from the frozen value. This is the whole point: shards are skipped by
   name, so without this guard a changed builder would quietly write new geometry under an old
   revision name and every worker would log “건너뜀”. That is the 2026-08-17 mfix accident and the
   solver-build accident, twice over.

An entry whose `fingerprint` is `None` fails gate 3 by design. Builders, renders and the whole
acceptance suite still work — only sweep runs are refused.

## Where things live

| what | path |
|---|---|
| registry, gates, merge split | `src/mesh_rev.py` |
| per-drone registry entries | `src/mesh_rev_<key>.py` (`ENTRIES`, loaded lazily) |
| dispatch by (key, rev) | `src/drone_rev.py` |
| shared parts library P1–P8 | `src/drone_parts_rev1.py` |
| per-drone frame builders | `src/drone_rev1_<key>.py` |
| sources and thresholds | `docs/mesh_rev1/<key>_{sources,acceptance_thresholds}.json` |
| acceptance entry point | `benchmark/mesh_rev1_acceptance.py` |
| revision-0 bit-identity proof | `benchmark/regress_mesh_rev0_bitidentical_0917.py` |

Only three live files carry the mechanism (`src/drones.py`, `src/drone_cad.py`,
`benchmark/elevation_sweep_md.py`); everything else above is a new file that nothing loads until
a revision is asked for.

### The acceptance entry point is a dispatcher

`benchmark/mesh_rev1_acceptance.py --drone <key>` routes to one of three implementations, because
each aircraft is scored against a different kind of reference and the three scoring codes are not
variants of one another:

| implementation | drones | reference |
|---|---|---|
| `mesh_rev1_acceptance_matrice4e.py` | matrice4e | the M4T STEP CAD (needs `--cad-scratch` / `$M0917`) |
| `mesh_rev1_acceptance_phantom4.py` | phantom4 | the owned CC-BY scan in the datum frame |
| `mesh_rev1_acceptance_photo.py` | mini5pro, mavic4pro | owned FCC / product photos |

A key that is not in `_IMPL` is **refused**, not scored by whichever implementation happened to be
imported — a wrong-reference table still prints a full page of plausible numbers.

Two rows need scratch helpers that are not part of the installable tree (`top_iou.py`,
`arm_midline.py`). They are looked up in `$MESHREV1_WORK`, then `../work/<key>`, then `../work`.
⚠ The per-key directory matters: mini5pro and mavic4pro each ship a **different** `top_iou.py`
under that one name, with different registrations and different signatures.

## What is frozen, 2026-09-18

| drone | acceptance | fingerprint | blocking |
|---|---|---|---|
| matrice4e | 159 scored, 152 pass, 7 fail | `fc0bbae9…` **not frozen** | 18 self-intersections (C.1 asks 0); 4 C.4 p99 rows; DEV-5/DEV-6 declared but unapproved; **DEV-1…DEV-4 are inside the frozen threshold file itself and are also unapproved**; C.7 blade angle |
| phantom4 | 139 scored, 130 pass, 9 fail | `087aae89…` **not frozen** | C.1 sliver fraction, C.2b prop area in the bell, C.5 camera visibility, C.7 blade angle; **8 post-run code deviations (D1–D8) are live in the committed scoring code; D1, D2, D3, D4, D6 and D8 each turn a failing or unscored row into a passing one** |
| mini5pro | 65 gates, 63 pass, 2 fail | `5575058136…` **not frozen** | C.2 battery metal clearance 0.0 mm (the official pack does not fit the photo-measured shell) — measured consequence: **4,846 mm² of metal face welded onto the shell and 71 coincident metal/plastic triangle pairs (3,038 mm²)**; C.7 blade angle; **7** unapproved threshold deviations |
| mavic4pro | 66 gates, 65 pass, 1 fail | `9359e1f0…` **not frozen** | C.7 blade angle is the only failing gate and `deviations[]` is empty — but **C.6 is scored on the parts library's own declared sagitta, and the measured facet sagitta is 3.451 mm against the 2.58 mm λ/20 bound** (report row R1), with 10 coincident cross-group triangles (22.8 mm²). mini5pro logged that same gap as a deviation; mavic4pro did not |

### ⚠ "C.6 passes" does not mean the same thing on all four drones

The dispatcher keeps three scoring implementations, and they do not measure C.6 the same way.
`mesh_rev1_acceptance_matrice4e.py` and `_phantom4.py` measure the sagitta on the **built mesh**
(0.738 mm and 0.734 mm). `mesh_rev1_acceptance_photo.py` reads the parts library's **declared**
`mesh_sagitta_mm` / `curve_sagitta_mm`, so a part that declares a small number cannot fail it; on
those two aircraft the measured value is printed as report row R1 and is **above** the λ/20 bound
(mini5pro 2.679 mm edge-chord / 2.796 mm span-chord, mavic4pro 3.451 / 2.72 mm). Read the gate
column together with R1 for mini5pro and mavic4pro, and do not compare a C.6 pass across drones.

Every one of those four values was recomputed in the merged tree and is identical across
`OMP_NUM_THREADS` 1, 2 and 4 in two processes each. **C.7 blade angle vs revision 0 fails on all
four** for one structural reason: what P6 changes *is* the leading/trailing-edge assignment that
the chord angle measures, so no mesh applying P6 can meet ±0.2°. Plan critique M8 forbids
relaxing a threshold after seeing it fail, so this needs a user ruling, not a merge-stage edit.

To freeze one: set `fingerprint=` to the verified value in that drone's `mesh_rev_<key>.py`
(the value is already recorded in the comment above the field) and commit. From that moment the
geometry of `(key, 1)` is fixed and any change is revision 2.

### ⚠ A deviations file can move the headline count — matrice4e

`mesh_rev1_acceptance_matrice4e.py` auto-loads `docs/mesh_rev1/matrice4e_deviations_0918.json`
if it is present and re-scores with it. Measured by running the acceptance twice, once with the
file moved aside:

| | scored | passed | failed |
|---|---|---|---|
| without the deviations file | 158 | 150 | **8** |
| with it | 159 | 152 | **7** |

**DEV-5 flips two scored rows from FAIL to PASS** — `CAD->ours nose_cradle median` (10.56 mm
against a 5.0 mm limit) and `p90` (19.04 against 8.6) — by narrowing the scored `nose_cradle`
class to CAD solid 49. It is done in the open: the original definition stays in the table as the
report rows `nose_cradle__frozen_class median/p90` with their failing numbers, and a new scored
`p99` row fails. DEV-6 rescues nothing; it turns one unmeasurable row into one passing and one
failing row.

This is exactly the case plan critique M8 names: a threshold-equivalent change decided **after**
seeing the row fail. Nothing here is hidden, but the 7-failure headline is not comparable with
the 8-failure one. **Both deviations are declared and await user approval**, so the file is held
out of the first commit — see the commit list in the merge note.

## Readers that are NOT safe once revision shards exist

`analyse()` routes revision arms to `outputs/elevation_sweep_md_meshrev.json`, so the main ledger
and its 61 readers stay clean. The shard **folder** is the exposed surface. From the E0 reader
census (134 files; classes: arm_grammar-based, literal-production-string, mesh-blind):

**Must be patched before any revision shard is written** (11 files, mesh-blind glob or listdir;
prepared patches exist but are deliberately **not applied** — they are an ordinary commit, and
none of these files is loaded by a worker):

`benchmark/build_atlas_toc.py`, `benchmark/check_arm_names.py`,
`benchmark/coverage_verify_0820.py`, `benchmark/el0_copies_0903.py`,
`benchmark/fix_phase_sign_legacy.py`, `benchmark/outdoor_order_0907.py`,
`benchmark/probe_drop_0902.py`, `benchmark/review_kernel_outdoor_0915.py`,
`benchmark/true_repeat_0903.py`, `benchmark/verify_raybudget_meaning.py`,
`benchmark/who_dropped_0903.py`

Two of those are destructive, not merely wrong: `coverage_verify_0820.py` **moves** the first
glob match and **deletes** the rest, and `fix_phase_sign_legacy.py` **rewrites** shards in place
and would conjugate revision shards that are already born with the corrected sign.

**Correct as they are, but their counts will include revision shards** (13 files — inventories,
stamp checks, staleness and machine-load counters): `audit_isac_inventory_0915.py`,
`az_falsify_timing.py`, `check_solver_build.py`, `depth_axis_verdict_0816.py`, `freeze_0912.py`,
`isac_plan_corpus_0915.py`, `isac_plan_positioning_0915.py`, `remeasure_review_0915.py`,
`review_current_state_0911.py`, `review_remaining_0914.py`, `review_upgrade_0914.py`,
`switch_factorial.py`, `wideband_energy_fairbudget.py`.

The other 109 select by an exact arm name or a literal production mesh string and never match a
revision arm.

## Rules that do not bend

- **Revision 0 is never touched.** Proven per commit by
  `regress_mesh_rev0_bitidentical_0917.py hashes` — 10 keys × 4 environment states.
- **`envelope_mm=None`** for every revision-1 spec, so `frame_fit_scale` is exactly (1, 1, 1).
  Rotor xy, wheelbase, prop diameter, blade count, rotor count, hover rpm and `base_ang` stay at
  revision 0's values.
- **Every dimension needs an owned source** — spec, manual/QSG, our scan, CAD we hold, or an owned
  photo with a stated scale. No third-party licensed mesh. Anything below evidence grade
  medium-high is an ablation variant, never part of the revision.
- **Thresholds are frozen before the first acceptance run** and pinned by sha256 in the registry.
  A changed threshold is a deviation entry with its reason, and it needs user approval.
- **Ablation variants are scratch only** and never enter a pre-registered comparison.
