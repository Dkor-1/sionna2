# Mesh revision 1 plan (2026-09-17)

> Status: approved design, implementation phase B1 started 2026-09-17 ~22:00 KST (mechanism E0 + shared parts E1 in isolated copies).
> Origin: user request 2026-09-17 «결과가 다소 달라지더라도 경향성만 유지되면 괜찮다 … Matrice 4E, Mini 5 Pro 등 우리가 만들어 둔 메쉬 개선까지 목표로 작업해줘»
> [changed numbers are acceptable if trends hold; improve our own meshes], and «메쉬는 버전별로 … 남겨두는 형식»
> [keep every mesh version]. Revision 0 = today's meshes, frozen as the default; revisions are added explicitly and never edited after release.
> Produced by a design workflow (four inventory agents → design lead → adversarial critique). The critique's problem list is kept
> above the corrected plan because every blocking item constrains the implementation. Scratch paths (/tmp/…) in the text are the
> design-phase working files and may no longer exist.

VERDICT: REVISE. Do not run the plan as written. The core idea is sound: put the revision inside the mfix value and keep revision 0 as today's objects. But 7 blocking defects and 9 major gaps must be fixed first. A few target labels and values have no owned source, listed under S1.

## Problems found (with evidence)

### Blocking

**B1. The planned tagmf rewrite breaks legacy names.**
- Plan A.1(4) replaces `/workspace/sionna/benchmark/elevation_sweep_md.py:448` `tagmf = "" if not _fixes else "_mfix" + "".join(_fixes)` with `tagmf = "_mfix" + "".join(_fixes) + (...)`.
- With `MESH_FIX=none`, `_fixes` is empty, so every legacy name gains a bare `_mfix`. `src/arm_grammar.py` cannot parse that (`mfix[A-Za-z0-9]+`).
- A.2(ii) would miss it, because job lines run with the environment unset.
- `benchmark/isac_plan_kernel_match_0915.py:1156` also quotes line 448 word for word.

**B2. The revision number is not tied to the geometry.**
- Shards are skipped by name (`shard_done(f) and not a.overwrite`).
- Any of these would produce different geometry under the same `…rev1` stems: D.5.2 ("revision 1 leaves that component out" after a break), a fix after acceptance, or a later agent tweak.
- Workers would then log "건너뜀" (skipped) and silently keep the old rev1 shards. This is the same accident the file documents for mfix (2026-08-17) and for solver builds (`build_tag` docstring).

**B3. Every kernel comparison mixes the mesh change with a grid change.**
- `elevation_sweep_md.py:724` `gref = grid_ref_from(probes, fc, spacing=d)` takes the grid centre and radius from the posed mesh's bounding box.
- `src/rcs_sbr.py:1196` places the spherical-wave source at `p_tx = ctr + range_m·û`.
- Any bounding-box change in rev1 therefore moves both the sample points and the source.
- The plan's own finding 0.4 measures up to 11.6 dB from grid phase at el 0. S1, F1, B1, C1, A1 and CPU-4 all compare revisions on different grids.

**B4. Running watchers would read the draft queue file.**
- PIDs 285665 and 285666 run `/workspace/sionna/runners/hold_window.py --queue-glob runners/jobs_09[5-9][0-9]_*.txt` until 09:00 KST 09-18.
- `pending_lines()` (:118) counts every non-comment line of a matching file with no supervisor log as pending. Canyon lines are costed at 225 min.
- A file `runners/jobs_09xx_mesh_rev1_validation.txt` (xx = 50–99) would move the GPU 1/2 take-back time even if nobody launched it. File names containing HOLD are excluded.

**B5. The isolated copy cannot build any shard names.**
- `build_tag()` reads `runners/SOLVER_BUILDS.json` (`elevation_sweep_md.py:1353`) and exits if it is missing. E.1 does not copy that file.
- Every dry-run in the copy would print BAD. Comparing BAD with BAD would pass without testing anything.

**B6. The report15_probe edit targets the wrong lines and adds risk.**
- `/workspace/sionna/benchmark/report15_probe.py:302-308` builds the per-process OBJ scratch folder name, not an output name.
- The real output is the fixed `OUT_JSON` (:113) `outputs/report15_probe.json`, keyed only by drone. Running it with `--mesh-rev 1` would overwrite the revision-0 results.
- Every PathSolver worker imports this file (`elevation_sweep_md.py:797`), so editing it widens what live workers load.

**B7. The claim that old readers exclude rev1 rests on two examples.**
- In src and benchmark, 72 files glob the shard folder and 74 read `outputs/elevation_sweep_md.json`. Only 21 import arm_grammar.
- Counter-example: `/workspace/sionna/benchmark/review_kernel_outdoor_0915.py:59` `shd.glob('*_rt210_*.npz')` would take rev1 shards.
- `analyse()` (:1862) merges every shard into the main ledger.

### Major

**M1. The swap test only covers "first k files swapped" states.**
- Workers import repo modules at different moments. A dry-run trace (`PYTHONPROFILEIMPORTTIME`) shows: drones, articulated_fast, cadkit, drone_cad, geom, materials, gpu, proc_scratch, scene_build and thread_guard; then arm_grammar at `build_tag`; then report15_probe. A real run also imports mesh_inmem and rcs_sbr.
- A worker can therefore hold old `drones.py` together with new `arm_grammar.py`, which is not one of the tested states.
- The plan swaps 10 files, and 5 of them are loaded by workers. `mesh_check`, `mesh_topo_check` and `mesh_dimref` are not loaded by workers and need no live swap.

**M2. Adding three fields to DroneSpec has side effects the plan mispredicts.**
- `benchmark/mesh_certify.py` seals the hashes of its code files (exit 1) and the declared spec fields (:291, exit 2). A.2(iv)'s "same exit code" cannot hold.
- Inserting fields at `drones.py:185` shifts every DRONES line. `benchmark/isac_plan_link_budget_0915.py` cites `("src/drones.py", 339, …)` by line number.

**M3. The rev1 frame builder skips the canonical repairs its name claims.**
- It bypasses `build_frame_cad`, including `union_groups` (`src/drone_cad.py:3377`), the battery union and the i5 repair. The name would still say `mfixbatteryi5rev1`.
- The canonical-repair guard exists only in the sweep CLI. CPU drivers and tools call `spec_for` under whatever `MESH_FIX` is set.

**M4. Envelope fitting and rotor placement are undefined for rev1.**
- `frame_fit_scale` would refit the rev1 bounding box to `envelope_mm` (Matrice 4E H 149.5, while the M4E target is CAD 151.5).
- `rotor_layout` multiplies rotor centres by that scale, yet C.8 requires unchanged rotor xy. P4-1 keeps a fit while M5P-1 removes it.
- Prop mounting z for the same key still comes from the per-key tables `MOTOR_BASE_Z`, `MOTOR_BELL_TOP_Z_M` and `PROP_STANDOFF_M` (`drone_cad.py:802-850`).
- There is no prop-seating test, although this repo once shipped props floating 3.6–13.2 mm above the bell (`drone_cad.py` comment).

**M5. The Mini 5 Pro height change reopens a closed decision without a z source.**
- `/workspace/sionna/outputs/mesh_apply_gimbal_then_height_0816.json` (`not_applied` H1) found 72 % of the height gap above the shell crown: arm tip, bell and prop mount z. None of these has a mm source. `src/geom.py:84-92` lists this as a permanent limit.
- The "estimate 14" rotor z offset is simply revision 0's raw value.
- Reaching 91 ±3 mm without measured z values would mean inventing them.

**M6. The trend metrics are not validated.**
- No null control (rev0 vs rev0 must pass) and no positive control (a known perturbation must fail).
- There are gaps between the pass and break bands. Example: G1 passes at ≤1 dB and is a hard break at >3 dB, and 1–3 dB is undefined.
- F1's τ ≥ 0.67 equals "one adjacent swap" only when n = 4. With n = 3, τ is 1 or 0.33.
- S1 has no minimum number of measurable cells.
- W1 requires ±0.01°, but G-2's steps are 0.05–0.15° and were chosen from revision-0 edges.
- G1's |ΔL(scene)| cannot see drone changes, because the scene dominates that level by construction.
- Isolated-pose counts mostly reflect the path cap. The `runners/jobs_0945_cap_ladder.txt` header records ground 90 poses at the default cap vs 34 at 8e6, and canyon 339 → 79.

**M7. D.5.2 picks components by result.** Dropping a low-grade component because it breaks a trend is choosing geometry to restore the old trend. Inclusion must be decided by evidence grade before any RF run.

**M8. The threshold rule has a loophole.** "Relax only before any RF run" still allows relaxing a threshold after seeing an acceptance failure.

**M9. GPU queue issues.**
- G-5 (Mini 5 Pro, el 0 only) feeds no D.1 metric.
- The canyon cells use the default cap, which has the largest isolated-pose artifact. Partners at `--max-paths 16000000` already exist for iso and tr38901 at el −60.
- G-2's elevations must come from the rev1 census.

### Sourcing and minor

**S1. Target spot-checks against owned sources.** Every target was traced to owned files.

Confirmed:
- **Matrice 4E battery** 145.47×60.6×46.3 mm and **max prop speed** 6130 RPM: `/tmp/claude-0/-workspace/8ed65148-4553-4ebc-8477-9670ae39b001/scratchpad/mesh_0917/matrice4e/m4_manual.txt` (manual v1.2). The battery table is on p.103, not p.102, and the manual prints "cm".
- **Mini 5 Pro** battery 86.10×54.89×24.85 mm, 6028F 152.4 mm, envelope 304×380×91 / 157×95×68: `…/dji_folding/web/mini5pro_um_en.txt` and `…/dji_folding/specs_json_extract.txt`.
- **S1000**: M1/M2 are the nose, M1/3/5/7 spin CCW, gear 305 mm high with 155 mm top width: `…/triage4/s1000_manual.txt`.
- **Phantom 4** (all from `…/phantom_family/data/p4_scan_analysis_datum.json`):
  - arm sections 24.0×37.4 at 120 mm and 19.3×29.7 at 140 mm;
  - waist 101 mm at x 0;
  - leg centre ±72.9 mm at z −80, section 13.0×11.8;
  - frame height 180.2 mm, can radius fit 14.09–14.1 mm, can top z 24.9;
  - top silhouette ratio 1.365.
- **Matrice 4E plate** 142×67.6×7.1 at `drone_cad.py:626`, where the code says it was never measured.
- **Mini 5 Pro shell height** 45.05 mm: `/workspace/sionna/outputs/mesh_inspect_body_arms_0816.json`.

Not traceable in owned files:
- Phantom 4 "manual 179.1" and "manual 28.1–28.5". The values themselves are covered by the scan numbers above.
- S1000 "arm incline 3° (manual)". The manual text only says "small frame arm incline".
- The facing-area targets 500, 6,000 and 1,500 mm². `matrice4e/facing_area.json` gives the CAD values: facing10 total 2,036 at az 0 el 0 (no group split), facing5 4,617 at el −90, and 726 at az 180.

**S2. The P6 references disagree on spin labels.** In `…/matrice4e/prop_section_0p7R_ours_vs_refs.png`, `solo_prop_ccw.stl` and `1345_prop_cw.stl` both have the raised thick edge on −y. Blade orientation must be defined against each rotor's own rotation, not the file labels.

**S3. Acceptance checks missing:** prop seating, swept-disc clearance, the symmetry and placement certificates, the material group of each new part, and connected-component counts.

**S4. Render scratch paths.** `src/scene_build.py:140` writes `<mesh_dir>/_scene/<key>__<group>.obj`. Rev1 renders must pass a scratch `mesh_dir`.

**S5. Swap timing.** `hold_window` evacuates GPUs at 08:40 and launches REDO supervisors (`hold_window.py:215`). Do not swap between 08:30 and 09:15 KST on 09-18.

**S6. Smaller inconsistencies.**
- A.1 puts the registry in `mesh_rev.py`; E.2 puts it in `mesh_rev_<key>.py`.
- Push only when the user asks.
- Rev1 phantom3 and mini2 must never enter the Das pre-registered comparison.
- CPU-1 uses 512 poses, so it needs one ladder cell at 8192.

---

## CORRECTED PLAN: mesh revision 1 (2026-09-17)

Repo paths are relative to /workspace/sionna. Scratch = /tmp/claude-0/-workspace/8ed65148-4553-4ebc-8477-9670ae39b001/scratchpad/mesh_0917/. DL/ = scratch/design_lead/. No repo file is edited in this phase, everything runs on CPU cores 14–15, and nothing is committed.

### 0. Findings the plan rests on

1. **Revision-0 fingerprints are recorded** in DL/rev0_fingerprints_0917.json, for all 10 keys with MESH_FIX and BLADE_LAW unset. The revision-0 fit scales are (1, 1, sz) for every key except s1000plus, which is (0.99857, 0.99857, 0.929).
2. **The revision goes inside the mfix value** (`_mfixbatteryi5rev1_blperairframe`). This fails the two literal production-mesh selectors. It does not isolate readers that glob by build or prefix (B7), so A.2(viii) and the merge split are required.
3. **The specular census** (DL/specular_foot_census.py) matches the three el-0 level steps by position. It is used only to predict where windows move, not as proof of cause.
4. **Our kernel's level depends strongly on grid phase at el 0**, by up to 11.6 dB. The grid centre is the pose bounding-box centre (`elevation_sweep_md.py:724`), and the spherical-wave source sits at `ctr + R·û` (`rcs_sbr.py:1196`). Revision comparisons in our kernel must share one grid reference (D.0).
5. **Measured costs:**
   - kernel: 76 ms/pose at el 0 and 136 ms/pose at el −30 (2 cores);
   - production dry-run: about 4 s per line on 2 cores;
   - PathSolver slot-hours as in the ledger rows.
6. **What workers load.** Repo modules loaded by a PathSolver worker are drones, articulated_fast, cadkit, drone_cad, geom, materials, gpu, proc_scratch, scene_build, thread_guard, arm_grammar (at `build_tag`) and report15_probe; real runs add mesh_inmem and rcs_sbr. `mesh_check`, `mesh_topo_check` and `mesh_dimref` are not loaded.
7. **hold_window watchers** read `runners/jobs_09[5-9][0-9]_*.txt` every minute until 09:00 KST 09-18.

### A. Versioning

#### A.1 Mechanism: only three live files change

**1. `src/drones.py`** (same-line edits plus an appended block, so no existing line moves)
- `rotor_layout`, same line: `dir=(spec.rotor_dirs[k] if getattr(spec, "rotor_dirs", None) else (1 if k % 2 == 0 else -1))`.
- `_fit_cache_key`, same line: `return tuple(getattr(spec, f) for f in _SPEC_FIELDS) + tuple(getattr(spec, f, None) for f in ("mesh_rev", "rotor_dirs", "rev_drop"))`.
- `build_propeller` docstring, same line: the mirrored prop is the CW one.
- Appended just before `if __name__ == "__main__":`:
  - `@dataclass class DroneSpecRev(DroneSpec)` with `mesh_rev: int = 1`, `rotor_dirs: tuple | None = None`, `rev_drop: tuple = ()`.
  - `spec_for(key, mesh_rev=0)`:
    - rev 0 returns `DRONES[key]`, the same object;
    - rev ≥ 1 lazily imports `mesh_rev` and returns `mesh_rev.make_spec(key, rev)`;
    - an unknown pair raises `ValueError`.
- DroneSpec, DRONES and `_SPEC_FIELDS` stay unchanged, so declared fields in the mesh certificate do not change.

**2. `src/drone_cad.py`** (two hooks, each the first statement after the docstring)
- `build_frame_cad`: `if getattr(spec, "mesh_rev", 0): from drone_rev import build_frame_rev; return build_frame_rev(spec, mesh_fix=mesh_fix)`.
- `build_propeller_cad`: the same pattern to `build_propeller_rev(spec, n_sec=…, blade_law=…, pitch_law=…, max_edge_m=…, lambda_m=…, edge_over_lambda=…)`.
- No other change. Revision modules may import private drone_cad helpers but never edit them.

**3. `benchmark/elevation_sweep_md.py`**
- argparse: `--mesh-rev` (int, default 0). A.2(ii) checks existing abbreviations; today only `--merge` starts with `--me`.
- Top of `run()`, before FastPoser, when rev ≥ 1, exit (SystemExit) unless:
  - `sorted(mesh_fix_set()) == sorted(MESH_FIX_CANON)`;
  - `blade_law_canon() == BLADE_LAW_CANON`;
  - `(drone_key, rev)` is registered.
- :360/:363, same lines: import `spec_for`; `spec = DRONES[drone_key] if not _rev else spec_for(drone_key, _rev)`.
- **Fingerprint guard** right after the FastPoser build, before any name or dry-run exit, when rev ≥ 1:
  - sha256 over the FastPoser frame vertices, faces and groups, both prop meshes, and JSON of `rotor_layout`;
  - compared with the registry's frozen value for (key, rev), computed with the production venv (py312);
  - a mismatch stops the run, so filter_jobs.sh reports BAD.
- **Name tag:** one line inserted after :448, leaving :448 exactly as it is: `tagmf += f"rev{_rev}" if _rev else ""`. The result is `_mfixbatteryi5rev1_blperairframe`.
- **`analyse()`** routes arms whose mfix value carries a revision (via `mesh_rev.split_mesh_fix`) to `outputs/elevation_sweep_md_meshrev.json`. The main ledger stays as it is.

**New modules** (loaded only when rev ≥ 1):
- **`src/mesh_rev.py`**, the registry:
  - per (key, rev): overrides, component list with evidence grade and sources, and the frozen fingerprint;
  - hashability check on overrides;
  - `split_mesh_fix`, which accepts every fix id in `MESH_FIX_KNOWN` plus "all" and a trailing `rev<N>`;
  - per-drone entries loaded lazily from `src/mesh_rev_<key>.py`.
  - At E0 the live registry is empty, so `--mesh-rev 1` fails for every key.
- **`src/drone_rev.py`:** dispatch by (key, rev). It refuses any non-canonical `MESH_FIX` or `BLADE_LAW` and reproduces `build_frame_cad`'s union semantics, including the battery union and the closed body required by i5.
- `src/drone_rev1_<key>.py` and `src/drone_parts_rev1.py`.

**Not edited in E0:**
- `src/arm_grammar.py`: its regex already accepts the tag, and the helpers live in `mesh_rev.py`.
- `benchmark/report15_probe.py`: it is not a shard producer and has no mesh tag. Rev1 is unsupported there.
- Tool flags (`--mesh-rev` for `mesh_check`, `mesh_topo_check`, `mesh_dimref`) come in a later ordinary commit with A.2(iv), because workers do not load those tools.

#### A.2 Proof that defaults do not change

Script: `benchmark/regress_mesh_rev0_bitidentical_0917.py`. It exits nonzero on any failure.

- **(i) Mesh bytes.**
  - Keys and states: all 10 keys × 4 environment states (unset; `MESH_FIX=none`; `BLADE_LAW=legacy`; `MESH_FIX=all`).
  - Hashes: `build_frame`; `build_propeller` mirrored and not; `build_drone`; `pose_articulated` at phases 0/17/41.5/123; `FastPoser.pose` and `.verify()`; one FastPoser each with `body_scale`, `frame_scale` and `prop_scale` ≠ 1; JSON of `rotor_layout`; `frame_fit_scale`; `frame_envelope_mm`.
  - Compared against a baseline regenerated from the live tree in a fresh process just before the swap.
- **(ii) Names.**
  - All 754 unique lines of `runners/jobs_09*.txt` are dry-run in the old and new copies with the environment unset. The 88 lines of 0950–0959 are also run under the other three states.
  - Every line must produce a `[dry]` name in both trees. The name count must equal the line count, and any BAD fails the test.
  - Names must be identical, and argparse Namespaces identical apart from `mesh_rev=0`.
  - Search runners/, benchmark/ and docs/ for `--me ` abbreviations.
- **(iii) Grammar.** `benchmark/check_arm_names.py` and parsing of all shard stems and ledger engines give unchanged results.
- **(iv) Merge.** Old and new `analyse()` run with SHD pointing at the live shard folder (read only) and OUT/OUTN pointing at scratch. Outputs must match apart from timestamps. Time it once; if it takes more than 2 h on 2 cores, use a fixed 500-shard subset.
- **(v) Existing checks.**
  - The existing regression scripts and `mesh_check`/`mesh_topo_check` keep their exit codes.
  - `mesh_certify` may differ only in the hashes of drones.py and drone_cad.py (exit 1), plus consumer-census rows for new files.
  - Any change in shape, budget, reference, door verdict or declared fields fails.
  - Re-seal with `--reason` only after E0 lands.
- **(vi) Citation checkers.** Re-run the scripts that cite edited files by line number or quote them word for word (`isac_plan_link_budget_0915.py`, `isac_plan_kernel_match_0915.py`, plus a grep for others). Refresh them in a separate commit.
- **(vii) Positive controls**, using a test-only registry patched in memory:
  - rev 1 builds a different mesh and the stem contains `_mfixbatteryi5rev1_blperairframe`;
  - `MESH_FIX=none --mesh-rev 1` stops before FastPoser;
  - a tampered fingerprint stops the dry-run;
  - an unknown (key, rev) raises ValueError.
- **(viii) Reader census.**
  - Classify every file that reads shards or the ledger as (a) arm_grammar-based, (b) filtering on the literal production mesh string, or (c) mesh-blind glob or prefix, such as `review_kernel_outdoor_0915.py:59`.
  - Before any rev1 shard exists, each class-(c) reader either gets an explicit revision exclusion (ordinary commit, not worker-loaded) or is listed in `docs/MESH_REV1.md` as unsafe on a shard folder containing rev1 shards.

#### A.3 Why running queues are unaffected

- Lines without `--mesh-rev` build revision 0 with identical bytes and names.
- Running workers keep the modules they already imported.
- New workers see the three edited files in some mix of old and new. All 8 combinations are tested (E.3).
- Revision-1 names are tied to frozen geometry by the fingerprint guard.

### B. Per-drone changes

**B.0 Rules for all drones**
- **Inclusion by grade, before any RF run.** Only components with evidence grade medium-high or better, and with passing acceptance, enter revision 1. Medium or low components exist only as named ablation variants (`rev_drop`, scratch only). Nothing is added or removed based on RF results.
- **No envelope fit.** Every revision-1 spec sets `envelope_mm=None`, so `frame_fit_scale` is exactly (1, 1, 1). Official and CAD envelopes become C.3 checks.
- **Rotor xy** equals the revision-0 realized positions. For s1000plus, `rotor_r_mm` = the scaled revision-0 radii. Wheelbase, prop diameter, blade count, rotor count, rpm and `base_ang` are unchanged.
- **Rotor z** is explicit: `rotor_z_mm` = target mount z − `motor_bell_top_z_m(spec)` − standoff. The target mount z is the top of the revision-1 motor stack.
- **Any geometry change** after fingerprints are frozen (C.14) creates rev 2. A revision is never reused for different geometry.
- **No dimension without an owned source** (spec, manual, scan, CAD we hold, or scaled owned photo). No third-party licensed mesh or its derived numbers are used.
- λ/10 is 8.57 mm at 3.5 GHz and 5.17 mm at 5.8 GHz. dBsm figures are PEC upper bounds and were not simulated.

**B.1 Shared builders.** P1–P8 as in the original plan, with two changes:
- Every part row declares its group. Plastic parts use that drone's revision-0 plastic convention (body, gear or accent). The P3 motor pod never goes in `motor`, which is metal. No new groups are added.
- P6 is defined relative to each rotor's rotation. The leading edge is the raised edge, faces the direction of motion for that rotor's `dir`, and carries the thick, rounded section. Sweep is judged against Mini 2 GLB blades whose lift direction is computed from pitch, not against file labels. The Solo and 1345 STL labels disagree, per `prop_section_0p7R_ours_vs_refs.png`.

**Facet rule:** curved-surface sagitta ≤ 2.58 mm (λ/20 at 5.8 GHz), target 1.0 mm.

**B.2 Rotor spin.** Evidence as in the original table.
- R-spin is read before the pre-registration: Matrice 4 manual p.20 line art, plus twist of resting props in owned photos, requiring at least 2 independent rotors that agree.
- phantom3 (high), s1000plus (high), phantom4 and mini2 (medium-high): the flip goes into revision 1.
- matrice4e, mini5pro, mavic4pro: flipped only if R-spin reaches medium-high. Otherwise `rotor_dirs` stays as today's pattern, stated explicitly, and the flip is ablation-only.
- m350rtk: no change.

**B.3 Matrice 4E revision 1.** Sources: the M4T STEP (gitignored; only derived section numbers enter the repo), the spec page, manual v1.2 (battery table p.103), and the owned teardown photos.

| # | Change | Target | Notes |
|---|---|---|---|
| M4E-1 | Remove the metal plate 142×67.6×7.1 mm | No internal metal outside the shell | Marked unmeasured at `drone_cad.py:626`; t13/t14 show no plate |
| M4E-2 | Replace the flat nose cap with the beak over the gimbal cradle | Nose/cradle error median ≤ 5, p90 ≤ 8.6 mm; body facing area at az 0 as in C.5 | — |
| M4E-3 | Close the tail shell; battery 145.47×60.6×46.3 contained with 1 mm clearance | Metal facing az 180 = 0 | — |
| M4E-4 | Straight front arms | Root x +85 ±5, heading 66–68°, bow ≤ 1 mm, same rotor centres | — |
| M4E-5 | Fuselage sides and belly | Side error ≤ 3 mm median; belly −30.8 ±1.5 | — |
| M4E-6 | Motor stack from CAD | Blade plane via `rotor_z_mm` per B.0 | — |
| M4E-7 | Gimbal width 64 ±2 | Height kept | — |
| M4E-8 | P6 orientation fix | Spin per B.2 | — |

- **Envelope check (C.3):** L/W within ±3 mm of CAD 328.3 / 387.4. Height is checked against CAD 151.5 ±3 and the official 149.5 is reported alongside. Choosing CAD over the official height is declared.
- **Declared, not changed:** O4 antennas inside the legs; 1157F vs 1154F (manual p.103 lists 1154F as a qualified accessory; ask the user); the `max_rpm` 7500 vs 6130 mismatch (separate docs commit); fisheyes and RTK dome.
- **Budget:** frame ≤ 20,000 faces; props unchanged.

**B.4 Mini 5 Pro revision 1.** Sources: spec page, manual (2025-09-11), FCC SS3-MT5MFND25 external photos with the steel ruler. Write `assets/photos/mini5pro/SOURCES.md` first.

- **M5P-1 (conditional; reopens a permanent limit, `geom.py:84-92`):** remove the ×1.2986 height stretch only if the ruler-corrected FCC side photos give arm-tip z, bell-top z and prop-mount z with stated uncertainty.
  - If they do: shell 45.05 ±2, total height with props 91 ±3, recorded as a C.3 check.
  - If they do not: revision 1 keeps today's vertical layout (stretch included). Taking the stretch out would leave the model short of 91 mm, and that gap cannot be filled without invented z values; the user decides at E4 whether to accept a declared shortfall.
  - Either way, update the certificate's `not_guaranteed` entry.
- **M5P-2 to M5P-7** as in the original plan:
  - shell x span, width stations, front arm heading 69 ±3;
  - motor size measured on the FCC photos;
  - one leg per front motor;
  - battery 86.10×54.89×24.85;
  - superellipse exponent judged by FCC overlay IoU only;
  - remove the accent cylinders.
- **M5P-8:** P6, and spin per B.2.
- **Budget:** frame ≤ 18,000 faces.

**B.5 Phantom 4 revision 1.** Sources: the owned CC-BY scan in the datum frame (`phantom_family/data/p4_scan_analysis_datum.json`), P4 UM v1.2, QSG v1.2, the DJI prop table.

| # | Change | Target (all from the scan file) |
|---|---|---|
| P4-1 | Stop forcing 196 onto the props-off frame | No fit; props-off frame height 180 ±3 (scan 180.2); crown +26.8 ±2. 196 ±3 checked as props-included height (declared inference). The "manual 179.1" label is dropped |
| P4-2 | Oval pod → X-shaped fairing | Belly −58.4 ±3; waist 101 ±4 at x 0; arm sections 24.0×37.4 at 120 mm, 19.3×29.7 at 140 mm (±3); top silhouette ratio 0.95–1.08 |
| P4-3 | Camera position and burial | Manual p.8: x −13…+62 ±4, bottom ≈27 ±4 above the feet; buried ≤ 10 % |
| P4-4 | Disc motors → cans | Can Ø28.2 ±1 (scan can_radius_fit 14.09–14.1 mm, 4 rotors); straight wall 24 ±2 and pod Ø38 ±3 from the scan's radial profile; top z +24.9 ±2 |
| P4-5 | Legs attached | Centre x ±72.9 ±3 at z −80; section 13×12 → 11×10 ±1.5; splay from the leg sections; gap ≤ 0.5 mm |
| P4-6 | Remove GPS puck and Pro-only cylinders | — |
| P4-7 | Containment | — |
| P4-8 | P6; spin FL/RR CW; label "9450" | — |

Budget: frame ≤ 20,000 faces.

**B.6 Other airframes** (cheap fixes on drones results already use)
- **mavic4pro:** as in the original plan, with its stretch removal under the same condition as M5P-1.
- **s1000plus:** plates → carbon `deck`; battery tray; gear 305 ±3 and top width 155 ±5; spin per manual p.10. The "arm incline 3°" enters only if measured from a manual figure and saved; otherwise not in revision 1.
- **m350rtk, phantom3, mini2:** as in the original plan. Revision-1 phantom3 and mini2 are never substituted into the Das pre-registered comparison (informational only).
- **typhoonh480, x500v2:** no revision 1.

### C. Geometry acceptance tests

Script: `benchmark/mesh_rev1_acceptance.py --drone <key>`.

**Threshold freeze.** `docs/mesh_rev1/<key>_acceptance_thresholds.json` is committed, with its sha256 in the registry, before the first acceptance run. Any relaxation afterwards needs user approval and is logged as a deviation.

1. **Topology:**
   - every group watertight, with 0 boundary edges, 0 non-manifold edges and 0 self-intersections;
   - outward winding;
   - slivers within revision-0 budgets;
   - connected components per group equal the declared count.
2. **Attachment:**
   - leg, gimbal post and motor pod gaps ≤ 0.5 mm; no floating parts;
   - internal metal 100 % inside the shell with ≥ 1 mm clearance;
   - buried plastic ≤ 2 % of shell area.
   - **2b. Prop seating:** the gap from hub underside to bell or adapter top is within [0, 0.5] mm; prop area inside the bell ≤ revision-0 budget.
   - **2c. Swept-disc clearance:** no frame vertex inside any rotor's swept blade volume ±1 mm; the sign of neighbouring-disc clearance is unchanged.
3. **Dimensions:**
   - every B target within its tolerance;
   - `frame_fit_scale` is exactly (1, 1, 1);
   - wheelbase, prop diameter, blade count and rotor count unchanged;
   - rotor xy within 1e-6 mm of revision 0.
4. **Reference distance and silhouettes:**
   - Matrice 4E vs CAD and Phantom 4 vs scan as in the original plan.
   - Every threshold states its rule: a λ-based value (5.17 / 8.57 / 4.28 mm), or "≥ 25 % reduction from revision 0 and no worse than revision 0 in any region".
   - Mini 5 Pro and Mavic 4 Pro vs FCC photos: revision-0 IoU is recorded and frozen before building; revision 1 must reach both the floor and revision 0 + 0.05.
   - Mini 2 must not regress vs its GLB.
5. **Facing area**, 5° and 10° cones, by group and by material, with the cone always stated:
   - Matrice 4E targets are ratios to the cited CAD values: az 0 el 0 facing10 total vs CAD 2,036; el −90 facing5 vs CAD 4,617; az 180 vs CAD 726. Ratio limits are set in the threshold file with a written rule.
   - Metal facing az 180 = 0.
   - Phantom 4: camera group visible from el −30…−90 increases.
6. **Facets:** sagitta ≤ 2.58 mm; face budgets.
7. **Props (P6):**
   - at 0.3/0.5/0.7/0.9R, for both mirrored and unmirrored props, the thick edge is the raised edge, which faces the rotation;
   - chord ±0.5 mm and blade angle ±0.2° against revision 0;
   - `check_handedness` passes.
8. **Kinematics:**
   - `rotor_dirs` equal the B.2 decision;
   - `FastPoser(spec_for(k, 1)).verify()` ≤ 1e-9;
   - `prop_dia_mm`, `prop_blades`, `num_rotors` and `hover_rpm` unchanged.
9. **Specular census** for revision 0 and revision 1 on every queue aspect, as a pre-registration input.
10. **Visual review:** a render sheet next to photos, CAD or scan; the builder writes notes per view; an independent agent re-reads the PNGs.
11. **Certificates:** `mesh_symmetry` and `mesh_placement` pass with revision-0 budgets.
12. **Material table:** area and volume per material, revision 0 vs revision 1; every new part's group listed.
13. **Canonical repairs hold:** battery/pcb/plate interpenetration 0 %; body closed.
14. **Freeze:** after C.1–C.13 pass, record the fingerprint in the registry. From then on, the geometry of (key, 1) is fixed.

Render or RT paths used for review pass a scratch `mesh_dir`, never `assets/meshes/drones/<key>`.

### D. Checking that trends hold

**D.0 Rules**
- **Pre-registration:** `outputs/mesh_rev1_prereg.json` holds metrics, cells, thresholds, census predictions, the grid-reference rule, control results and every revision-1 fingerprint. It is committed and its sha256 recorded before any RF run on revision 1.
- **Common grid reference.** For each (drone, az, el), one `gref = grid_ref_from(probes_rev0 + probes_rev1, fc, spacing=λ/12)` is shared by both revisions. Grid-phase shifts {0, 0.25, 0.5} are applied on top. `cache_key` is never set to a drone key when both revisions share a process.
- **Three-way outcome for every metric** (pass, soft, hard) with no gaps.
- **Null control N0:** revision 0 vs revision 0 (0.25-cell grid shift for the kernel; existing solver-seed shards for PathSolver where available) must pass every metric. A metric that fails its null is dropped before sealing.
- **Positive control P0:** revision 0 vs revision 0 with `body_scale 0.4` (existing knob, CPU) must fail at least one of B1 or C1. If nothing fails, the metrics are insensitive; redesign before sealing.
- **Isolated-pose counts** mostly reflect the path cap. They are report-only. Isolated poses are still separated out before C1.
- **Pose count:** one 8192-pose cell (Matrice 4E, el −30) checks that 512-pose mean levels are within 0.5 dB.
- **Noise floors:** PathSolver repeat spread, solver seed, and kernel grid phase. A kernel level cell whose revision-0 grid-phase spread is ≥ 6 dB is not measurable.

**D.1 Metrics**

| ID | Metric | Pass | Soft | Hard |
|---|---|---|---|---|
| K1 | Flash rate, f_tip, the 12 harmonic bins, autocorrelation lag | identical | — | any difference (code bug) |
| W1 | Level steps on the G-2 grid vs census edges | every step lies inside a bracketing pair that contains a census edge | — | a step with no census edge |
| W2 | L(el 0) − max L(el −15…−60), only where both censuses keep an el-0 face | ≥ 30 dB and ≥ 0.7 × revision 0 | 20–30 dB | < 20 dB |
| S1 | Spearman ρ over measurable elevations (at least 6 cells, else "not assessable") | ρ ≥ 0.7 | ρ < 0.7 | — |
| F1 | Discordant drone pairs at el {−30, −60, −90}, counted only where the revision-0 gap > max(3 dB, 2 × grid-phase spread) | 0 | ≥ 1 with revision-0 gap 3–6 dB | ≥ 1 with gap > 6 dB |
| B1 | D sign where \|D_rev0\| ≥ 6 dB; ρ(D) ≥ 0.7; \|Δ varying-part level\| ≤ 3 dB | all hold | any fails | — |
| C1 | Comb contrast (definition from `review_results_queue_0917.py`) | cells ≥ 3 dB stay ≥ 3; cells < 1 dB stay < 3; \|Δ\| ≤ 3 dB where revision 0 ≥ 10 dB (1–3 dB cells report-only) | any fails | — |
| C1-aim | Aimed minus iso contrast, ground and canyon, el −60 | ≥ 20 dB | — | < 20 dB |
| G1 | L(scene) − L(open sky), el −60 | ≥ 40 dB | — | < 40 dB |
| A1 | Spectral asymmetry, el −30 (only if spin changed) | az 0: \|Δ\| ≤ 0.1 | az 0: \|Δ\| > 0.1 | — |

G1's \|ΔL(scene)\| is reported only. A1 sign flips at az ≠ 0 are reported, not scored.

**Census-predicted changes** are pre-registered as expected, not as breaks: the Matrice 4E plastic-nose band, the az 180 battery window, and the near-nadir plate.

**D.2 CPU runs.** Cores 14–15, `CUDA_VISIBLE_DEVICES=""`, nice 19. A scratch driver runs from the isolated copy and writes only to scratch.

| Run | Content | Est. wall |
|---|---|---|
| CPU-0 | Census, facing and visible area, revisions 0 and 1 | minutes |
| CPU-N0 / CPU-P0 | Controls | ≈40 min |
| CPU-1 (S1, F1) | Common grid, 3 phases, 512 poses; plus the 8192-pose ladder cell | ≈2.6 h |
| CPU-2 (K1, B1, C1) | As in the original plan, common grid | ≈2 h |
| CPU-3 (A1) | Spin check | ≈25 min |
| CPU-4 (G1 proxy) | Common grid; time 16 poses first | ≈0.5 h |
| CPU-5 | Component ablation, only on a break (diagnosis only; never changes revision-1 content) | ≈1.3 h |
| CPU-6 (optional) | PathSolver on CPU: presence check only; measure actual CPU % after binding with sched_setaffinity | cap 2 h |

**D.3 Small GPU validation queue**
- **The draft stays in scratch.** No file matching `runners/jobs_09[5-9][0-9]_*.txt` is created while any hold_window watcher runs, and no file whose `sup_<num>.log` already exists.
- **Launch.** The user launches after approval. Every line goes through `runners/filter_jobs.sh` first (NEW/DONE/STALE/BAD).
- **Settings:** `--engine sionna --n-poses 8192 --range-m 15 --sw R0D0E0F1 --spp 4000000000 --max-depth 2 --mesh-rev 1 --nshards 2`; rt210 build; GPUs 3 and 4 only.

| Group | Cells | Revision-0 partner | Slot-h median (p90) |
|---|---|---|---|
| G-1 | Matrice 4E open sky, el 0/−15/−30/−45/−60 | exist: `sionna_p4000000000_swR0D0E0F1_r15_n8192_mfixbatteryi5_blperairframe_rt210_d2_el{+0,-15,-30,-45,-60}_{00,01}` | 8.0 (13.5) |
| G-2 | Matrice 4E `--n-poses 256`, elevations = every census edge ±0.01° from both revisions (names checked unique), revisions 0 and 1 | ordered together | ≈1.5–3 |
| G-3 | outdoor01_ground: el −60 iso, el −60 tr38901, el −30 iso | exist | 13.2 (38.7) |
| G-4 | simple_street_canyon at `--max-paths 16000000`: el −60 iso and tr38901 | exist (`…_mp16000000_…_rt210_d2_el-60`, iso and `anttr38901`) | re-time from partner meta; if > 1.5× the default-cap cost, use the default cap and make isolated-sensitive reads report-only |

- **G-5 is dropped** (no metric). Mini 5 Pro is checked on CPU.
- **Total:** ≈31.5 slot-h median, ≈80 p90.

**D.4 Breaks.** A hard break stops the work and triggers, in order:
1. rule out numerics (common grid, pose count, build, partner settings);
2. run CPU-5 ablation to find the component;
3. apply D.5.

Soft breaks go to the report and continue only with user approval.

Figures show STFT and the full-band modulation spectrum side by side, with the static part removed first. The claim gate applies (fact support, over-conclusion, independent re-check).

**D.5 Decisions after a break** (set in advance)
1. **The component has grade ≥ medium-high:** keep revision 1. Report that the old trend depended on that part. Old results stay valid as revision 0.
2. **Grade was already excluded by B.0:** it cannot be in revision 1, so this case does not arise.
3. **Unexplained:** run pairwise ablations; if still unexplained, stop and ask the user.
4. **Never:** change dimensions to restore a trend; tune toward any simulation or Das; reuse a revision number for changed geometry (any change = rev 2 with a new pre-registration).

### E. Implementation

**E.1 Isolated copies.** For each agent:

```bash
git -C /workspace/sionna archive HEAD src benchmark runners/filter_jobs.sh runners/SOLVER_BUILDS.json docs/drone_specs_2026.json \
  | tar -x -C scratch/impl/<agent>/sionna
```

- Also copy `outputs/report07_three_engines.json`.
- Record the sha256 of each live file at copy time.
- Smoke test: 3 dry-run lines must produce names before any other test.
- Never symlink `outputs/elev_sweep_shards`.
- Run with `PYTHONPATH=<copy>/src:<copy>/benchmark CUDA_VISIBLE_DEVICES="" MPLBACKEND=Agg nice -n 19 taskset -c 14-15`.

**E.2 Order**
1. **E0, lead:** A.1 mechanism (3 live files plus empty-registry modules) and all of A.2 green in the copy, then E.3, then commit c1.
2. **E1:** `src/drone_parts_rev1.py` with unit tests; API frozen.
3. **E2:** one agent per drone (Matrice 4E, Mini 5 Pro, Phantom 4; later Mavic 4 Pro and the cheap-fix set). Each owns `src/drone_rev1_<key>.py`, `src/mesh_rev_<key>.py`, `docs/mesh_rev1/<key>_sources.json` and `docs/mesh_rev1/<key>_acceptance_thresholds.json`, the thresholds committed before the first acceptance run. Deliverables: C.1–C.14 green and the independent visual re-check.
4. **E3, validator (not a builder):** controls, pre-registration (commit before any RF run), D.2 runs, `outputs/mesh_rev1_trends_cpu.json`.
5. **E4, user gate:** Korean report notebook; the user decides the D.3 queue and the E.6 questions.
6. **E5:** the queue file is placed per D.3 naming rules; the user launches; the validator reads with arm_grammar `matched_groups(vary=["mesh_fix"])`; a second agent re-checks the verdicts.
7. **E6:** `docs/MESH_REV1.md`; revision-1 OBJs only under `assets/meshes/drones_rev1/<key>/`; `mesh_certify` door verdicts updated and re-sealed with a reason; `mesh_check`/`topo`/`dimref` `--mesh-rev` flags as an ordinary commit.

**E.3 Applying to the live repo while supervisors run**
- **Scope:** only E0 touches files workers load, and only 3 of them. Everything else is new files or tools workers do not load.
- **Timing:** not between 08:30 and 09:15 KST 09-18 (evacuation and REDO launches). Check hold_window and supervisor logs read-only first.
- **Staging:** byte-compile, import-test, and dry-run one real line from the stage.
- **Combination test:** for all 8 old/new combinations of the three files, run A.2(i) (canonical state) and dry-run names for the 88 lines of 0950–0959.
- **Swap order:** new modules, then `drone_cad.py`, then `drones.py`, then `elevation_sweep_md.py`.
- **Swap script:**
  1. refuse if any live sha256 differs from the recorded base;
  2. back up;
  3. write temp, fsync, `os.replace`;
  4. immediately re-run A.2(i) and the 0950–0959 dry-run names on live;
  5. watch the next launches in supervisor logs, read-only.
- **Rollback trigger:** any A.2 mismatch, or any worker launched after the swap that exits rc≠0 within 10 min on a line that previously ran. Rollback is `os.replace` of the backups in reverse order, then report.
- Queues, supervisors, `GPU_HOLD.json` and watchers are never touched. Never edit live files in place.

**E.4 Commits** (heredoc and `git commit -F`, ending with the attribution line; only each unit's files; push only when the user asks)

| Commit | Content |
|---|---|
| c1 | Mechanism, regression script, fingerprints |
| c1b | Citation-anchor refresh |
| c2 | Shared parts |
| c3-k | Per drone: thresholds first, then builder, acceptance ledger, frozen fingerprint |
| c4 | Pre-registration |
| c5 | CPU trend ledger and notebook |
| c6 | Queue file (after approval) |
| docs | `docs/drone_specs_2026.json` corrections |

**E.5 Tests per commit**
- **c1:** all of A.2.
- **Every later commit:** A.2(i) on live, plus `check_arm_names.py`.
- **Per-drone commits:** also C.1–C.14.
- **c5 and c6:** independent re-check.

**E.6 Questions for the user** (at E4)
1. Which prop does the campaign Matrice 4E fly, 1157F or 1154F?
2. Is the tag `_mfixbatteryi5rev1` acceptable?
3. Is Mavic 4 Pro in this round?
4. Approve about 31.5 slot-h median (80 p90) on GPUs 3 and 4?
5. If the FCC photos cannot give Mini 5 Pro/Mavic 4 Pro arm and motor z: keep the stretch, or accept a declared height shortfall?
6. For medium-grade spin (matrice4e, mini5pro, mavic4pro): keep today's pattern in revision 1 with the flip as ablation only (default), or wait for more evidence?

### F. Cost, benefit, what not to do

**Cost**
- About 8–10 agent-days.
- CPU about 7–11 h on 2 cores.
- GPU about 31.5 slot-h median, about 80 p90.
- Risk to running queues is limited to 3 files, covered by A.2, the 8-combination test, the fingerprint guard and rollback.

**Benefit:** known non-physical scatterers are removed, and distances and silhouettes against owned references improve. We cannot claim that levels become more realistic: both engines are approximations and only measurement can judge that. Nothing here says Sionna was wrong.

**Largest trend risks:** the Matrice 4E el-0 plastic-nose window, and kernel near-nadir levels. Tell the user before any deck or report number that depends on them is reused.

**Do not**
- use any third-party licensed mesh or numbers derived from it, or copy triangulated DJI STEP data;
- guess any dimension;
- change the default mesh, `MESH_FIX_CANON` or `BLADE_LAW_CANON`, or add revision ids to `MESH_FIX`;
- reuse a revision number after a geometry change;
- create queue files that match watcher globs while watchers run;
- edit `arm_grammar.py` or `report15_probe.py` live in this round;
- pass a drone key as `cache_key` across revisions;
- write revision-1 OBJs into `assets/meshes/drones/<key>` (including `_scene`);
- change rpm, prop diameter, rotor xy or blade count;
- touch the `blades` getattr bug;
- build typhoonh480 or x500v2 revision 1;
- tune geometry or thresholds after seeing results.

**Files**
- DL/rev0_fingerprints_0917.json, DL/fingerprint_all.py, DL/specular_foot_census.py, DL/time_kernel_cpu.py.
- Inventories: scratch/matrice4e/, scratch/dji_folding/, scratch/phantom_family/, scratch/triage4/.
- Evidence cited above:
  - `benchmark/elevation_sweep_md.py`: :363, :448, :724, :797, :1353, :1862
  - `src/rcs_sbr.py:1196`
  - `src/drone_cad.py`: :626, :802-850, :3377
  - `src/drones.py`: `rotor_layout`, `_fit_cache_key`, `frame_fit_scale`
  - `runners/hold_window.py`: :118, :215, :226
  - `benchmark/report15_probe.py`: :112-113
  - `benchmark/review_kernel_outdoor_0915.py:59`
  - `benchmark/mesh_certify.py:291`
  - `src/scene_build.py:140`
  - `outputs/mesh_apply_gimbal_then_height_0816.json`
  - `runners/jobs_0945_cap_ladder.txt`