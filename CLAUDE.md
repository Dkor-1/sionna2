# Working in this repository

> ⭐**If you are new here, start with [`docs/HANDOVER_MAP.md`](docs/HANDOVER_MAP.md).** It lays out on one page which document holds which convention, how the queue runs, and what to do every day.

## ⭐⭐Claim gate — no exceptions

Before putting a number or claim on a slide · report · briefing, pass it through **[`docs/CLAIM_GATE.md`](docs/CLAIM_GATE.md)**.

**ⓐ Factual support** — is this number a property of the **physics**, or a property of the **measurement setup**?
Saturated value · cut-off sweep · search floor · degenerate denominator · window/cell width · below the spread · no ledger · stale.

**ⓑ Over-concluding** — is this something I **saw**, or something I **judged**?
「X 가 Y 를 묻는다/덮는다/일으킨다」 [X buries/masks/causes Y], 「A 가 아니라 B 다」 [it is B, not A] are verdicts.
⛔Do not write them on the slide face — **move them down to the presenter notes.**

**3 layers**: ①self-check (every claim, no exceptions) ②knob shaking (headline numbers) ③adversarial verification +
**independent recomputation** (anything that gets fixed into a presentation · report). Details in CLAIM_GATE.md.

⭐**The check that extends the end of the range is the cheapest and catches the most.** The 2026-09-01 incident on slide 13 of the deck
could have been prevented by a single 30-second check that extended the sweep from +24 → +60 dB.

## Figures

⛔**Leave no overlaps** (user directive 2026-09-02). If the legend covers the data or text overlaps text,
the figure cannot do its job. `src/paper_kit.save_figure` checks with `src/figcheck.py` right before saving
and prints warnings — **if a warning appears, fix it and output again.**

| What it catches | How to fix |
|---|---|
| Legend covers the data | Place it **outside** the axes with `bbox_to_anchor`, or point `loc` at the empty side |
| Text inside the axes overlaps | Move it or delete one of them — writing shorter frees up room |
| y-axis label ↔ tick labels | Increase `labelpad` or use `subplots_adjust(left=)` |

Setting `FIGCHECK_STRICT=1` turns warnings into exceptions. The default is warnings —
some figures deliberately place a semi-transparent legend over the data, and stopping the builder means no figure comes out at all.

Show the phenomenon — **STFT · energy distribution · modulation spectrum**. Derived verdict figures do not
replace observation figures. ⛔Do not put verdict badges · boxes inside a figure. The figure speaks through curves,
and the presenter speaks the verdict.

## ⛔Reports are **Jupyter notebooks** — do not publish them as web pages

User directive (2026-09-07): 「레포트는 기존 레포트들처럼 **주피터로 만들어 마크다운 형식으로**」 [Make reports like the existing reports — built in Jupyter, in Markdown format].

When asked to summarize · report, build a **notebook** that follows the `src/report_style.py` conventions.
Do not publish it as an artifact (web page) — a report is an asset that stays in the repository and undergoes citation · rebuilding · footnote checks,
not a page you look at once and are done with.

| What | Where |
|---|---|
| Building functions | `src/report_style.py` — `header()` · `md()` · `figure_md()` · `build_notebook()` |
| Builders | `src/build_part*.py` (pieces) · `src/make_report*.py` (volumes) — **must be rebuildable** |
| Numbers | Cite from the ledger with `⟨파일 : 키⟩` tags. ⛔Do not type them by hand |
| Figures | Put them in `outputs/figures/` and have the notebook point to them |

⛔**Do not edit notebooks by hand** — fix the builder and rebuild.

## ⛔Team meetings are not managed in this repository

Presentation materials (decks · scripts · presentation figures) are made and kept **only in `/workspace/team_meeting/`**.
Do not keep `.pptx` · deck planning documents · deck-only builders in this repository.
On 2026-09-02, `decks/` (56 MB) · `teammeeting_0811/` · `DECK_0827_PLAN.md` were moved out —
user directive: 「시오나 디렉토리 내에 팀미팅 내용은 내부에서 다 없애버려」 [Get rid of all the team-meeting content inside the Sionna directory].

⚠**Having `deck` in the name does not make it a team-meeting asset.** The following are **analysis assets, so they stay**:

| Kept | Why |
|---|---|
| `benchmark/build_deck_maps.py` | `structure_bars` is the **canonical source of the definition of the rhythm-share window half-width of 8 Hz** — `build_md_atlas.py` · `build_atlas_toc.py` · `src/rx_noise.py` cite this definition |
| `benchmark/deck_facts.py` · `deck_ours_by_range.py` · `build_deck0811_*.py` · `build_physics_vs_deck_fig.py` | Called by sionna scripts · report builders |
| `outputs/deck*.json` | These are **ledgers**. 3 reports (05 · 06_2 · 06_4) cite them in footnotes |
| `docs/DECK_FACTS.md` | **Ledger cross-check table** for the numbers the deck cites — it is a verification record |

⇒ The dividing criterion is not the name but **who uses it**. If a report or analysis uses it, keep it;
if only presentations use it, send it to `/workspace/team_meeting/`.

## Other standing conventions

| Document | What |
|---|---|
| [`docs/RESUME.md`](docs/RESUME.md) | Resume point — read it first at session start |
| [`docs/NEW_FILE_RULES.md`](docs/NEW_FILE_RULES.md) | ⭐⭐**Read before creating a new file · new memo.** The **16 items** that group the 900 findings of the exhaustive audit by root cause, and the **eight lines** to scan before saving. The gate is `benchmark/check_new_file_rules.py` (blocks only new ones after the baseline) |
| [`docs/CLAIM_GATE.md`](docs/CLAIM_GATE.md) | Claim gate (above) |
| [`docs/EQUIVALENCE_GATES.md`](docs/EQUIVALENCE_GATES.md) | 3 layers for judging 「같음」 [sameness]. ⛔Do not require «비트 동일» [bit-identical] of solver outputs |
| [`docs/DECK_FACTS.md`](docs/DECK_FACTS.md) | Ledger cross-check table for the numbers the deck cites |
| [`docs/GATES_0902.md`](docs/GATES_0902.md) | ⭐Results of the three gates — **az 0 is a special cell because the geometry is symmetric** (N is 3 only at az 0, 9~10 everywhere else. ⚠The number of drops is **not monotonic** in azimuth — 45° has 15, fewer than az 0's 36. Do not say 「az 0 이 가장 깨끗하다」 [az 0 is the cleanest]) · **our kernel at el 0 is not converged at λ/12** (a half-cell shift gives −11.9 dB; at λ/24, +1.45 dB). ⛔Citing el 0 «레벨·폭» [level · width] is prohibited. ✅The comb (present/absent) does not depend on the grid |
| [`docs/SIONNA_NONDETERMINISM_0902.md`](docs/SIONNA_NONDETERMINISM_0902.md) | ⭐**Separates public discussion (#1175 etc.) from our observation** — #1175 is the diffraction wedge (RadioMapSolver), so it disappears with `diffraction=False`, but **ours occurs even with diffraction off** (PathSolver candidate generator). ⛔`rr_depth`·`deterministic` **do not exist** in the 2.0.1 PathSolver |
| [`docs/DEEP_DROP_0902.md`](docs/DEEP_DROP_0902.md) | ⭐**Deep drop = the phenomenon of losing one path «non-deterministically» at a pose.** Whether a drop occurs flips between reruns with the same settings (154 poses). What drops out is **one fixed complex constant**, and \|E\| falls to exactly (N−1)/N. ⚠«비결정적으로» [non-deterministically] was overstated — **at some poses that one copy always drops out** (2026-09-04). ✅**Whose fault it is has been settled (2026-09-03)** — of 2,296 drop poses, poses discarded by our mask: **0** (`outputs/who_dropped_0903.json`). The harness is not guilty — ⚠this covers **45 cells**, and the elevation composition is −45° 15 ··· **el 0° is 2 cells**. ⚠The path **count at drop poses is normal** — it is the sum, not the count, that collapses. ⭐Reproducibility is measured with **true reruns** (`outputs/true_repeat_0903.json`) — our kernel 6/6 bit-identical (⚠**2 runs each** — PathSolver arms have 3~5 runs depending on the cell, so do not read cells with different run counts side by side), PathSolver does not match **even with** diffraction off (at el 0, 2 poses at 50 %). ⛔Citing the old E0↔E1 values (8~26 poses · 23 %) is prohibited. ⭐⭐**The thread count turns this wobble on and off (2026-09-03)** — with 1 thread, 40 runs have **the same path count (8,059) · \|h\| deviation 0.00000 dB**, and with 2 they diverge. ⛔Do not write this as «비트 동일» [bit-identical] — that test measures only the path count and the magnitude of the coherent sum (corrected 2026-09-10; it also contradicted the EQUIVALENCE_GATES convention above). ⛔**Do not nail it down as «원인은 병렬 축약 순서다» [the cause is the parallel reduction order]** — that is a candidate explanation, and this test cannot pinpoint which race it is. ⚠With 2 threads the most frequent path count **shifts** to 8,058 — recounted against the 1-thread baseline, the differing runs are not 1 but **39/40**, and at 192 it is back to 14/40, so it is **not monotonic**. ⚠**This was measured on a minimal reproducer (CPU · 576 synthetic flat plates)** — in the drone corpus the pose geometry mostly decides, and the parallel order only splits borderline poses. It is not the GPU · seed · hash bucket count (unchanged even when shaken 32×) (`outputs/thread_ladder_0903.json`). ⭐In the **outdoor cells (3/45)**, what drops out is the radar's own ground reflection (40 m · env_ground · static clutter) — ⚠**this is the result of dumping one pose from one cell** — the drone paths stay intact (`outputs/elephant_id_0903.json`). ⛔**97 % of the drops (42 cells · 2,236 poses) are in free space with no ground**, and their shape differs too (contiguous blocks · −20 dB ↔ a single isolated pose · −38 dB) — ⭐⭐⭐**the «0° 서든 드랍» [0° sudden drop] the deck spoke of is «the same path being present three times and one of them dropping out»** (2026-09-03) — the drop depth is **exactly 2/3** at all 58 poses. ⛔«재실행하면 안 난다» [it does not occur on rerun] is **retracted** (2026-09-04) — its basis was re-solving GPU records on CPU, so it changed the machine, not the run. Re-measured with 5 `_rep` runs, the drop poses mostly stay the same (Jaccard 0.947~1.000 · only 2 of 8,192 flip). ⚠The «정반사→카메라 셋» [three specular → camera entries] list for pose 47 belongs to the **canonical-mesh arm**, and in that arm pose 47 is **not** a drop (ratio 1.0000) — the 2/3 occurs in the **arm without mesh correction**. The two facts came from different arms. ⭐⭐**Counted directly on 2026-09-04** — across 32,768 poses, the number of remaining lines (1/2/3) exactly determines the depth (0.371/0.684/1.000) (156 drop poses). This is observation, not inference. ⚠It does not occur with CPU · 1e8 rays — the total path count is below the threshold (`outputs/el0_drop_0903.json`). ⛔«How many lines are physically correct» has not been asked yet. ⭐Drops at oblique angles (el −15/−45) are **something else** — blades occluding as they pass (2026-09-03) — the block spacing matches the blade beat period (155.5 poses) at **1.00×**, and the phase is concentrated 5~6×. Read it not as a defect but as **the signal we set out to measure** — ⚠**periodicity alone does not separate «physics» from «solver»** (the pose index is itself the blade angle, so solver losses determined by geometry also repeat with the same period). The verdict is made from the path list. ⚠These values were measured on **3 cells** (blocks 65·60·39) (`outputs/drop_blocks_0903.json`) |
| [`docs/RHO_IS_SMOOTHNESS_0902.md`](docs/RHO_IS_SMOOTHNESS_0902.md) | ⛔**ρ (envelope autocorrelation) measures «smoothness», not rhythm.** Straight lines · staircases · red noise all land in the 「박자」 [beat] cell (0.92~0.99). Do not judge beat from ρ alone — **also report the comb harmonic SNR** |
| [`docs/AUDIT_REPORTS_0901.md`](docs/AUDIT_REPORTS_0901.md) | ⭐Adversarial verification of 24 report volumes — **59 confirmed (5 fatal), 49 still alive**. Check the relevant volume before citing |

- Diffuse reflection (F) is **always on in every arm.** The comparison axis is the five arms only
- **Do not conclude** 「우리 커널이 맞고 PathSolver 가 틀렸다」 [our kernel is right and PathSolver is wrong] — both are approximations; judging realism is the job of real measurements
- Launch CPU-only jobs with `CUDA_VISIBLE_DEVICES=""`
- Python is **`/workspace/.venvs/py312/bin/python`** — ⛔`~/.venvs` does not exist on this machine
- ⛔**Do not hard-code paths that will disappear into the source** — `/tmp/…/scratchpad/…` disappears when the session ends,
  making that builder permanently unbuildable. If you need an input, move it into the repository and commit it
- ⛔⛔**말을 지어내지 않는다** [Do not invent words] (user directive 2026-09-03). Do not coin new words · abbreviations · symbols
  on the spot and use them — this applies to all of reports · documents · commits · **what you say to the user**.
  · If no suitable word exists, **spell it out** (「벌」 [sets/copies] ✗ → 「같은 줄이 몇 번 적히나」 [how many times the same line is written] ✓)
  · If a new name is truly required, **define it in one line where it is first used**, and record that definition in a document
  · Use existing words (path · pose · shard · arm) as they are. Do not create new ones that overlap them
  ⭐This is the parent convention of 「덱에 우리끼리 쓰는 말 금지」 [No insider words in decks] — it applies not only to decks but **everywhere**
- Because footnotes point to ledger rows with `rows[N]`, they shift when the ledger grows — check with `benchmark/check_row_pointers.py`, and if they are off, **rerun the piece builders**

## Language and experiment preferences

See [AGENTS.md](AGENTS.md) for the user's 2026-09-15 language preference and current
ISAC hardware scope: English progress/internal artifacts, Korean final responses
and reports; one X410 as the main platform with a Wi-Fi/LTE/5G NR benchmark.
