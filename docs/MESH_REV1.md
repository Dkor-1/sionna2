# Mesh revisions — how to use one

> Design and acceptance plan: `docs/MESH_REV1_PLAN_0917.md`. This file is the operating manual.
> Status 2026-09-18 (b5 reconcile-and-freeze round): the mechanism is live. Four drones have a
> revision-1 builder registered. **Two fingerprints are now frozen — mini5pro and mavic4pro — so
> `--mesh-rev 1` runs for those two keys and is still refused for matrice4e and phantom4.** A
> frozen fingerprint fixes the GEOMETRY of that (key, revision); it does not approve any of the
> acceptance deviations, none of which the user has signed off. See “What is frozen” below.

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

## What is frozen, 2026-09-18 (b5 round)

Every number below was measured on one reconciled tree, in this round, with
`benchmark/mesh_rev1_acceptance.py`. The **without** column is the same table with each drone's
deviations undone — see “What a deviation means here” for how each drone's is undone.

| drone | acceptance, with deviations | without deviations | fingerprint |
|---|---|---|---|
| **mini5pro** | 67 gate rows, **67 pass, 0 fail**, 20 report | **5 fail** — 5 of the 67 gate rows are deviation-replaced and every one of their pre-deviation readings fails | **FROZEN** `395f01bc0795184c903efffda5ba69f0105486b8ecb8f9fbf735c76b1b80f394` |
| **mavic4pro** | 68 gate rows, **68 pass, 0 fail**, 15 report | **1 fail** — the C.7 inertia reading, 0.4961° against 0.2° | **FROZEN** `2d1824a68bb3e47c1d6000327dc56ef1456cf4ef912844bb44071c131b363d97` |
| **phantom4** | 139 scored, 138 pass, **1 fail**, 19 report | 138 scored, 121 pass, **17 fail** | `34e68d78…` **not frozen** — C.1 sliver fraction 0.02589 against rev0 0.01551 + 0.005 is an **undeclared** failure |
| **matrice4e** | 163 scored, 160 pass, **3 fail**, 43 report | 158 scored, 151 pass, **7 fail** | `7663a959…` **not frozen** — C.2c swept-disc clearance −0.744 mm, C.4 CAD→ours motors p99 9.116 mm and C.4 ours→CAD turret p99 1.717 mm all still fail **after** their deviations are applied |

⚠ On mini5pro and mavic4pro the “without” column counts **failing pre-deviation readings**, not a
second table: undoing a deviation there does not simply restore one row, because DEV-1, DEV-3 and
DEV-6 each replaced one frozen row with two or three scored rows. The reading that would fail is
printed under its row on every run, which is what the count is read from.

The freeze rule this round used: freeze only when every remaining gate failure is a **declared**
deviation carrying its evidence and its pre-deviation reading. A drone with even one failure that
no deviation covers keeps `fingerprint=None`, and `mesh_rev.run_spec` keeps refusing
`--mesh-rev 1` for it — the safe state, because no unaccepted geometry can then reach a shard name.

Verification behind the two frozen values:

* each reproduced in **6 processes** — `OMP_NUM_THREADS` / `MKL_NUM_THREADS` /
  `OPENBLAS_NUM_THREADS` 1, 2 and 4 × two processes — **1 distinct value each**;
* revision 0 re-proved bit-identical against a pristine `git archive HEAD` tree:
  `regress_mesh_rev0_bitidentical_0917.py hashes`, 10 keys × 4 environment states,
  **680 equal, 0 different**;
* 32 live queue lines from `runners/jobs_0964…0968` dry-run in both trees:
  **32/32 identical shard names, 0 BAD**;
* `--mesh-rev 1` accepted for the two frozen keys and refused for the other two; a fingerprint
  tampered in memory is refused by `guard_fingerprint` right after FastPoser; `--mesh-rev 1` with
  `MESH_FIX=none` is refused before FastPoser; `--mesh-rev 2` is refused for all four.

⚠ `run_spec` only checks that a frozen fingerprint **exists** — it runs before FastPoser does.
The value itself is checked by `guard_fingerprint`, which recomputes it from the built geometry.
Both must be in the path for the guard to mean anything; `elevation_sweep_md.py` calls them in
that order.

**To freeze another one:** set `fingerprint=` to the verified value in that drone's
`mesh_rev_<key>.py` and commit. From that moment the geometry of `(key, 1)` is fixed and any
change is revision 2.

## What a deviation means here

A deviation is a place where the acceptance row as first frozen cannot be scored as written. It
is **never** a wider bound. Every one of them is recorded in
`docs/mesh_rev1/<key>_acceptance_deviations.json`, which that drone's scorer reads, and every one
prints the reading it replaced as a report row on the same run — that is what makes the
pre-deviation pass/fail count recoverable. **None of them is approved by the user**; they carry a
2026-09-18 phase ruling only.

The four drones undo their deviations by two different mechanisms, and both are exercised above:

* **matrice4e** — the scorer re-scores when the file is present, so the “without” count is
  measured by moving `docs/mesh_rev1/matrice4e_acceptance_deviations.json` aside and re-running:
  **163/160/3 with it, 158/151/7 without it.**
* **phantom4, mini5pro, mavic4pro** — the scorer recomputes each pre-deviation reading in the same
  run and prints it under its row. Moving those files aside removes only the report rows and
  changes **no gate verdict** (checked row by row this round for the two photo-scored drones), so
  the “without” count is read off the pre-deviation rows, not off a second run.

| id | drone | check | the row as frozen | what is scored instead | pre-deviation reading |
|---|---|---|---|---|---|
| DEV-1 | mini5pro | C.2 | one “buried plastic ≤ 2 % of shell area” row | plastic-in-plastic and plastic-in-the-camera scored apart | 9.002 % — **would fail** |
| DEV-2 | mini5pro | C.1 | camera group has 1 connected component | 6, the parts the group has always held (revision 0 measures 6 too) | 6 vs `== 1` — **would fail** |
| DEV-3 | mini5pro | C.11 | mirrored vertex → nearest vertex ≤ 0.01 mm | mirrored per-group **area** error, \|COM y\|, y bbox symmetry | 10.9225 mm — **would fail** (revision 0: 1.3935 mm) |
| DEV-4 | mini5pro | C.3 | front arm heading 65.34 ± 3° (the build's own reading) | the plan's own M5P-2 figure, 69 ± 3°, tolerance unchanged | 68.97 vs 65.34 ± 3 — **would fail** |
| DEV-5 | mini5pro | — | (no row covers the rear vision spheres) | nothing; a declared, measured report row | 5.895 mm aft of the tail station |
| DEV-6 | mini5pro | C.7 | blade angle from a cylindrical-section inertia reading | the constructed blade-angle law, same 0.2° bound | 0.4808° — **would fail** |
| DEV-1 | mavic4pro | C.7 | the same inertia reading | the same constructed law, same 0.2° bound | 0.4961° — **would fail** |
| D1–D10 | phantom4 | C.2, C.2b, C.2c, C.3, C.4, C.5, C.7, C.11 | ten rows, listed in its file | see the `[pre-dev Dn]` line under each row | 17 rows would fail; D5 is only **partly** recoverable and says so |
| DEV-5…DEV-10 | matrice4e | C.4, C.5, C.7, C.2c | six rows, listed in its file | see the file; DEV-9 makes a row that used to **pass** now **fail** | the failing rows stay in the table |

## What a C.6 or a C.7 pass means, per drone

Both of these used to mean different things on different drones. They no longer do, and this is
the record of what changed.

**C.6 — facet sagitta against λ/20 = 2.58 mm at 5.8 GHz.** All four now measure the **built**
mesh with `mesh_topo_check.facet_wavelength`, group by group plus the built propeller. Until the
b4 round the two photo-scored drones read the parts library's **declared** `mesh_sagitta_mm`, a
self-report a part could pass by declaring nothing. The two chord conventions the adversarial
review quoted were calibrated against an analytic cylinder (chord error `R(1−cos(π/N))` exactly):
the **edge**-chord convention reads 0.74×–95.9× the truth, the **span**-chord convention reads
exactly 2.00×, and `facet_wavelength` reads 1.00×. Both uncalibrated readings keep a report row.

| drone | C.6 gate | bound | the library's own number |
|---|---|---|---|
| matrice4e | 0.738 mm | ≤ 2.58 | — (measured from the start) |
| phantom4 | 0.734 mm | ≤ 2.58 | — (measured from the start) |
| mini5pro | 0.6729 mm | ≤ 2.58 | 0.9596 mm, now a report row |
| mavic4pro | 0.6804 mm | ≤ 2.58 | 0.6804 mm, now a report row |

**C.7 — the blade-angle law unchanged from revision 0, ±0.2°.** All four now score the
**constructed** law — `θ(r) = atan(k(r/R)·P/(2πr))` at every loft station, plus the chord law and
the whole set of inputs both builders resolve — at the plan's own unrelaxed 0.2° and 0.5 mm. All
four measure **0.000000** on it. The row it replaced read a section statistic of the built blade,
and P6 (the leading-edge flip) changes that section by construction, so no mesh applying P6 could
meet the bound: the readings were 0.469° (matrice4e), 0.32–0.88° (phantom4), 0.4808° (mini5pro)
and 0.4961° (mavic4pro), and each keeps its row as a report. On mavic4pro the estimator's own
noise floor — the spread between the two blades of **one** propeller, which are the same blade
rotated 180° — is **0.314°**, above the 0.2° bound it was being asked to resolve. This is one
shared parts-library property measured four times, not four aircraft defects.

⚠ A C.7 pass therefore says *the constructed law is unchanged*. It does **not** say the built
blade sections are within 0.2° of revision 0's; they are not, and the report row says so.

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
