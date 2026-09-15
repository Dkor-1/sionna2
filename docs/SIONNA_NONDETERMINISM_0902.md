# Sionna RT nondeterminism — how public material relates to our observation (2026-09-02)

Source document: `/workspace/Sionna_RT_Diffraction_Nondeterminism_Reproducibility_2026-09-02.md`
(summary of GitHub Discussions #1175 · #851 · #917 · #1142 and Issue #1071)

## ⭐In one line

**What we caught today is not #1175.** #1175 disappears with `diffraction=False`,
but **ours occurs with `diffraction=False`.** They are in different places.

## 1. Separating the two mechanisms

| | **#1175 (public report)** | **Our observation (2026-09-02)** |
|---|---|---|
| Where | Collection · sampling of **diffraction wedges** in `RadioMapSolver` | **Specular-chain deduplication** in `PathSolver` |
| File | `radio_map_solvers/radio_map_solver.py` | `path_solvers/sb_candidate_generator.py:484-498` |
| Mechanism | The **order** in which wedges enter the hash table depends on parallel execution → even with the same seed, different wedges are drawn | Only **the thread that first increments** a specular chain's hash bucket keeps that path (`dr.scatter_inc`) → paths **vanish entirely** |
| With diffraction off | **Disappears** (confirmed by the reporter) | ⛔**Still occurs** |
| Size | path_gain up to **~3.7 dB** | step **−3.5 dB** (2/3) · ground-reflection dropout **−51 dB** |
| Do we use it | ⛔No (`RadioMapSolver` is only for rendering) | ✅**Every measurement path goes through here** |

⭐**Confirmation that our arms run with diffraction off** (`elevation_sweep_md.py:566-568`):
```python
r_, d_, e_, f_ = bits            # R0D0E0F1
sw = dict(refraction=r_, diffraction=d_, edge_diffraction=e_)
diffuse = f_
```
⇒ `R0D0E0F1` = refraction **False** · diffraction **False** · edge **False** · diffuse **True**.
And `PathSolver.__init__` creates `SBCandidateGenerator()` (`path_solver.py:117`) —
it goes through the candidate generator **regardless of whether diffraction is on**.

⇒ **It is a PathSolver case that does not reproduce even with diffraction off**.

⛔⛔**Correction (2026-09-14) — 「공개 논의에 이 경우는 없다」 [public discussions do not have this case] was wrong.**
The public reproduction code in Discussion **#1142** is exactly that case — with NVIDIA's **built-in munich scene** set to
`los=False · specular_reflection=True · diffuse_reflection=False · refraction=False ·
diffraction=False · edge_diffraction=False · diffraction_lit_region=False`,
running twice with **the same seed (seed=1981)** gives diverging channel coefficients (reported relative difference > 0.1 %,
e.g. `5.0264234e-06+2.62638764e-06j` ↔ `5.0212852e-06+2.63619950e-06j`).
The maintainer explained it as 「병렬 축약의 비결정적 누산」 [nondeterministic accumulation in parallel reduction] and announced a «deterministic PathSolver
option» — that option arrived in 2.1.0 (the release notes name #1142).
⇒ **Our observation is not unique.** It is in a different place from #1175 (RadioMapSolver diffraction wedges), but
  in **the same place (PathSolver)** as #1142. Also drop the premise 「NVIDIA 기본 장면에서는 안 난다」 [it does not occur in NVIDIA's built-in scenes]
  — #1142 produces it in a built-in scene.
⚠**Still, do not assert that our observation is the same thing as #1142** — ours has the shape of a path dropping out
  entirely so that \|E\| falls to exactly (N−1)/N (`docs/DEEP_DROP_0902.md`), whereas #1142 is
  a relative difference in coefficients. Geometry · switches · observed quantity · thread count differ. Say only that it is the same solver.
Public evidence: https://github.com/NVlabs/sionna/discussions/1142

## 2. What the document recommends that **we cannot use**

All arguments of `PathSolver.__call__` in the installed `sionna 2.0.1`:
```
scene · max_depth · max_num_paths_per_src · samples_per_src · synthetic_array
los · specular_reflection · diffuse_reflection · refraction
diffraction · edge_diffraction · diffraction_lit_region · seed
```
⛔**There is no `rr_depth`** — the document's `rr_depth=-1` recommendation is on the `RadioMapSolver` side.
⛔**There is no `deterministic` option either** (it was announced in #1142 as «a future release»).

⚠Our `--det` (sorting paths by delay before summing) **cannot fix this problem** — it only fixes the order;
**a path that never came back cannot be revived.**

## 3. Our values against the document's «size criterion»

The document separates `~1e-5 dB` = floating-point reduction level from `≥ 1 dB` = algorithmic nondeterminism.

| Our value | dB | Verdict |
|---|---|---|
| Rerun difference between normal poses | `|ΔE|/|E|` median **1.57e-16** | Machine precision — floating-point reduction |
| Step (2/3) | **−3.52 dB** | ⚠**A property of the pose** — it occurs at the same poses even across runs (Jaccard 0.947~1.000). Only 2 of 8,192 differ between runs (`DEEP_DROP_0902.md` §2026-09-04 correction) |
| Ground-reflection dropout | **−51 dB** | ⚠**Mechanism unknown** — ⛔do not write «nondeterminism» |

⇒ By the document's **size** criterion it is at the algorithmic level, but ours is not «different in each run» but
**«fixed per pose»** — the canonical source is `docs/DEEP_DROP_0902.md`.
⚠Read with the «ground-reflection dropout» row excluded (correction below).
⛔**Correction (2026-09-04)** — classifying that −51 dB as «nondeterminism» was wrong.
  `docs/DEEP_DROP_0902.md` records the same number as 「**비결정성이 아니다. 기작 미상**」 [**not nondeterminism. Mechanism unknown**] and
  gives as evidence 「25 판 전부 \|E\| = 2.988340e−07 로 **비트 동일**」 [all 25 runs **bit-identical** at \|E\| = 2.988340e−07]. The ledger sides with that.
  It is the **ground clutter term with Doppler 0** of one outdoor cell and does not wobble between runs. And it is larger than #1175's 3.7 dB.

## 4. ⛔The recommendation to turn diffuse off **cannot be used for our task** (corrected 2026-09-02)

For reproducibility the document also recommends `diffuse_reflection=False`. **We cannot use it — the signal disappears entirely.**

Ledger `outputs/switch_factorial.json : cells.*.zero_echo` (a measurement that already existed):

| Arm | el +0 | el −15 | −30 | −45 | −60 | −75 | −90 |
|---|---|---|---|---|---|---|---|
| `R1D0E0F0` refraction only · **diffuse off** | false | **true** | **true** | **true** | **true** | **true** | **true** |
| `R0D0E0F0` **both off** | — | — | **true** (d1·d3) | — | — | — | — |

`zero_echo = true` means **`npaths = 0 · E ≡ 0`**. At oblique angles **literally nothing comes back.**

Mechanism (`docs/MATERIAL_CORRECTION.md`):
1. `src/materials.py` fixes the scattering coefficient of the ITU metal family (`metal` · `camera_assembly` · `pcb`) at **S = 0.0**
   → metal **in principle produces no diffuse scattering**
2. At oblique angles there are **0 triangles aligned with the line of sight** (`az_falsify_verdict_attack2.json : kill_3`)
   → no specular reflection either

⇒ ⛔**[Correction — scope narrowed]** The old sentence «빗각 PathSolver 에코는 원리적으로 100 % 플라스틱·탄소의 확산
   산란이다» [the oblique PathSolver echo is in principle 100 % diffuse scattering from plastic · carbon] **did not rule out the diffraction channel.** What 1 · 2 above rule out is only metal diffuse scattering (S = 0.0) and specular reflection
   (0 aligned triangles) ⇒ read it narrowed as «**restricted to the diffuse · specular channels**, what comes back at oblique angles is only
   diffuse scattering from plastic · carbon». **Arms with diffraction on keep an echo** — in the ⚠ paragraph below,
   `R0D1E0F0` · `R0D1E1F0` · `R1D1E1F0` · `R1D1E0F0`, and at el −30 the diffraction-only arm's AC −124.745 dB is
   **+10.9 dB above** the physics-off arm's −135.664 dB (ledger `outputs/material_verdict_0816.json` :
   `el_minus30.ref_onlydiffr_100mm` ↔ `el_minus30.base_100mm`).
   **With diffuse and diffraction both off** nothing remains. **Our task (oblique-angle micro-Doppler) does not hold.**

⛔**My mistake (2026-09-02)**: I wrote 「`R0D0E0F0` 를 한 번도 안 돌렸으니 진단으로 돌려 보자」 [R0D0E0F0 was never run, so let us run it as a diagnostic], but
   the ledger **already had it at el −30 d1 · d3, both with `zero_echo = true`**.
   I proposed it without looking at the ledger — exactly CLAIM_GATE's «no ledger» smell.

⚠The F0 shards on disk are **all at el −30** (176 of them), and the only ones with an echo are
   **the arms with diffraction on** (`R0D1E0F0` · `R0D1E1F0` · `R1D1E1F0` · `R1D1E0F0`).
   So in our data, 「확산 끔 + 회절 끔」 [diffuse off + diffraction off] **cannot be measured at all**.

⭐So the honest sentence that remains is this:
> **The reproducibility settings public discussions recommend (`diffraction=False` + `diffuse_reflection=False`)
> make the oblique-angle echo 0 on our target. We cannot follow that recommendation, and therefore
> cannot buy reproducibility through settings — instead we measure «how far it fails to match» and publish that alongside.**

## 6. ⭐Minimal reproducer — built (night of 2026-09-02)

`benchmark/minrepro_hash_0902.py` (130 lines). **It depends on nothing in our repository** —
only `numpy` · `mitsuba` · `sionna.rt`. A single synthetic mesh of small plates laid out on a grid is all there is.

| Plates | Triangles | Scattering S | Path-count variants (10 runs) | \|h\| spread |
|---|---|---|---|---|
| 64 | 128 | 0.7 | `[454]` | 0.0000 dB |
| 256 | 512 | 0.7 | `[1755, 1756]` | **1.0954 dB** |
| **576** | **1152** | **0.7** | **`[3997, 3998, 3999, 4000]`** | **4.7089 dB** |
| 1024 | 2048 | 0.7 | `[7101]` | 0.0000 dB |
| 576 | 1152 | 0.3 | `[758, 759, 760]` | **2.2585 dB** |
| 576 | 1152 | 1.0 | `[8200]` | 0.0000 dB |

Settings: `diffraction=False` · `edge_diffraction=False` · `seed=42` fixed ·
**same scene object · same solver object · consecutive calls**.

⭐**A control is measured too** — the stock scene `simple_street_canyon` has only **6** paths, so
it does not wobble, and its \|h\| spread is **0.0008 dB** (floating-point reduction level, matching the prediction in §16 of the document).
⇒ The reproducer's **4.7089 dB is about 5,900× that** (dividing the dB values directly). It is larger than #1175's 3.7 dB
too. ⛔«2,700×» does not follow from any reading and was fixed on 2026-09-04 (4.7089/0.0008 =
5,886). ⚠The control's 0.0008 dB has no ledger in `outputs/` — until it is rerun and a ledger is left,
this ratio is **a reference value only**. The same correction is in the header of `benchmark/minrepro_hash_0902.py`.

⚠With few paths (454) it does not wobble · with scattering S=1.0 it does not wobble (no specular chains remain).
It wobbles **when there are many paths and hash buckets overlap** — consistent with the collision hypothesis.
⚠The reproducer itself also gives different results from run to run (the 1024-plate case wobbled once and did not once).
**It is a stochastic process, so several runs are needed.**

## 7. To be raised at next week's team meeting (decided 2026-09-02)

⛔**Not included in tomorrow's (09-03) presentation.** Part 2 of tomorrow's deck is the **observation** 「튀는 자세가 있고 그것이 그림을
망친다」 [some poses spike and they ruin the figure], and the mechanism is only in the presenter notes. No claim goes outside.

⭐**To raise with the team next week**:
1. The minimal reproducer and its table (above) — 「부동소수점이 아니다」 [it is not floating point] together with the control
2. What caveat to attach to our results — reproducibility **cannot be bought through settings** (§4)
3. A way to publish the spread measured with repeated (rep) runs alongside the results
4. **Whether to report upstream** — a decision that carries the lab's name, so the team decides

## 5. What remains

1. Redo the hash bucket count (`max_num_paths_per_src`) ladder with more runs — with today's 40 runs,
   1e6 → 1/40, 2e6 → 3/40, 8e6 → 0/40, 32e6 → 0/40, which was **not significant**
2. To check in the next Sionna release: the #1175 wedge fix · the `deterministic` PathSolver option
3. ⭐**Worth raising in public discussion** — but written **with a narrowed scope** (corrected 2026-09-14).
   ⛔The old sentence 「회절을 꺼도 …는 사례는 #1175·#1071·#851·#917·**#1142** 어디에도 없다」 [a case where … even with diffraction off exists in none of #1175 · #1071 · #851 · #917 · #1142]
     **was wrong** — #1142 is a PathSolver case with diffraction · edge diffraction off (§1 correction above).
   ⭐What remains is **the shape**: #1142 reports a relative difference in coefficients (> 0.1 %), while in ours
     **a path drops out entirely** and \|E\| falls to exactly (N−1)/N (`docs/DEEP_DROP_0902.md` —
     over 32,768 poses, the number of remaining lines 1/2/3 exactly determines the depth 0.371/0.684/1.000).
     Whether that «dropping out entirely» exists in public discussions **has not been counted yet** — until it is counted,
     do not write 「없다」 [there is none].
   Reproducers already exist (`benchmark/probe_drop_0902.py` · `benchmark/minrepro_hash_0902.py`).
   ⭐And because we **cannot turn diffuse off**, we can also point out that their workaround
   does not work for us.
4. **Measure the spread** with repeated (rep) runs **and publish it with the results** — if it cannot be bought through settings, that is how we stay honest
