> ⛔**Historical — superseded by [`RESUME_0917.md`](RESUME_0917.md).** Kept as the dated 09-16 record; the scoped corrections of 2026-09-17 are marked «corrected 09-17» (metric names as defined in RESUME_0917 §4).

# Current status — 2026-09-16, 16:45 KST

> The in-repo edition. `/workspace/RESUME_NOW.md` was the top-level pointer to this file (it now points to RESUME_0917).
> Written so a fresh session can pick up without reading the transcript.
> The 2026-09-02 edition is at `/workspace/archive/2026-09/resume/RESUME_NOW_0902.md`.
> Python is **/workspace/.venvs/py312/bin/python**. For CPU work put `CUDA_VISIBLE_DEVICES=""` in front.
> Repo conventions: `../CLAUDE.md` (language policy, claim gate) and `HANDOVER_MAP.md`.

## 0. One line

Three GPU queues are running on cards 2/3/4 and will not dry out before tomorrow midday. The open
question is the **isolated poses** — ground only, el -60°, RT 2.1.0, max_depth 2, cap 2e6, isolated_20xmedian:
90/8,192, of which 82 fall below the cell (env_field_drop_halfmedian; the path-listed ones lack the ground specular
their neighbours have) and 8 rise about +0.96 dB above it (the 5 path-listed carry extra ground-propeller paths);
street canyon el -60°: 339 (4.1 %). Nothing needs a human right now.
*(Corrected 09-17: this line said «about 1 % of drone poses return a path set their neighbours have, and that 1 %
carries essentially all of the pose-to-pose change» — no scene, angle, cap or metric; the mechanism was inverted; the
share is close to circular.)*

## 1. GPU rules — read this before launching anything

`runners/GPU_HOLD.json` is the only switch. The supervisors **re-read it every round**, so a
change takes effect without restarting anything.

| Card | State | Note |
|---|---|---|
| 0 | held | on loan earlier today, **evacuated 15:55 KST at the user's request** |
| 1 | held | standing rule |
| 2 | held | was on loan; **evacuated 16:42 KST at the user's request** (「GPU 2번은 당장 비워줘」) |
| 3, 4 | ours | standing rule since 2026-09-15 |

**Only cards 3 and 4 are ours right now.** If a card is lent again, hand it back with one command:

```bash
cd /workspace/sionna && /workspace/.venvs/py312/bin/python runners/evacuate_gpu.py <card> --go
```

It holds the card, stops **only** the workers whose `/proc/<pid>/environ` says that card, and writes
the interrupted job lines to `runners/jobs_REDO_gpu2_<UTC>.txt` so they can be re-queued. Never
`pgrep -f` (it matches your own shell) and never kill a supervisor.

Two evacuations happened today, each leaving its interrupted lines in a REDO file:

* `runners/jobs_REDO_gpu0_20260916T065550Z.txt` — 3 lines, **already re-queued** inside `jobs_0947`
  (that is why `sup_cap_antenna_0946.log` shows `실패 3`).
* `runners/jobs_REDO_gpu2_20260916T074126Z.txt` — 3 lines, ⚠**not re-queued yet**. They are the three
  aimed-antenna cells, 43 minutes in when they were stopped. Re-buy them with a new jobs file once
  cards free up; `runners/filter_jobs.sh` first, so anything that did finish is skipped.

## 2. Queues — three supervisors, nothing waiting on a human

```
runners/jobs_0945_cap_ladder.txt      8 left   logs/sup_cap_0945.log
runners/jobs_0946_cap_antenna.txt     5 left   logs/sup_cap_antenna_0946.log   (3 = the GPU-0 lines, re-bought in 0947)
runners/jobs_0947_repeat_spread.txt   4 left   logs/sup_repeat_0947.log
```
Six workers are running, three on card 3 and three on card 4. The supervisors keep going on their
own; the GPU-2 evacuation did not touch them.

Check with `tail -2 runners/logs/sup_*.log` — the status line reads
`G<card>:<running>/<cap> · 큐 <done>/<total> · 워커 <n>`. A ground-cell shard is ~35-110 min, a
street-canyon shard ~225 min. Before adding a queue, split NEW/DONE/STALE/BAD with
`runners/filter_jobs.sh`; shard names carry the generation tag (`_rt210`, `_mp<N>`, `_ss<N>`, `_rep<N>`).

## 3. The isolated poses — what is established and what is not

Ledgers: `outputs/dropout_knobs_0916.json`, `outputs/dropout_hash_vs_buffer_0916.json`,
`outputs/dropout_paths_0916_diff.json`. Definition: a pose whose complex field sits more than
20 x median-absolute-deviation from the cell's complex median (= isolated_20xmedian; the centre is the component-wise
median of E, median(Re) + j·median(Im) — clarified 09-17).

**Established** (ground only, el -60°, RT 2.1.0, max_depth 2, cap 2e6 unless stated; 8,192 consecutive pulses,
≈1.16° of rotor turn apart at 3,800 rpm and 19.7 kHz; two shards per cell — corrected 09-17, it said «0.044° apart,
one shard each»):

* 90 of 8,192 poses (1.1 %) are isolated (isolated_20xmedian). The 99.96 % share of the pose-to-pose varying power
  they carry is close to circular (they were selected for being far from the median). Street canyon el -60° 339,
  canyon el -30° 96. Open sky (RT 2.1.0, 2e6, factor-20 rule): 0 at max_depth 2 el -15/-30/-45/-60°, max_depth 1 el -30/-45/-60°
  and max_depth 3 el -30/-60° (the cells on disk); at max_depth 2 el 0°, 37 (the same set in rep1; 2 at 32e6), a
  different signature (one of three copies of the drone echo missing).
  *(Corrected 09-17: this line said «free sky 0 — the ground has to be in the scene», which is false at 0°.)*
* At 30 of 32 checked ground pairs, the pose is missing exactly one path the neighbouring pulse (≈1.16° of rotor
  turn away) has: a single-bounce specular off `env_ground`, tau = 46.8 ns, |a| = 1.9e-4.
* Raising the solver's path limit thins them out but never to zero. Field-threshold drops (env_field_drop_halfmedian, every rung
  against open sky iso at cap 2e6, el -60°): cap 1e6 -> 153, 2e6 (production) -> 82, 8e6 -> 26, 16e6 -> 14, 32e6 -> 7.
  Path lists back «without the ground reflection» only at the sampled poses (`outputs/dropout_paths_0916_diff.json`,
  `outputs/dropout_hash_vs_buffer_0916.json`), not for every pose of these counts. All isolated poses (isolated_20xmedian) 161/90/34/22/15 add the same 8 rises at
  every cap. *(Corrected 09-17: the all-isolated ladder had been used for the missing ground reflection.)*
* Outside the isolated poses the cap changes the field by 2.2e-5, against 2.0e-5 for **re-running the
  identical job**. So the cap is not quietly reshaping the rest of the cell.
* `--max-paths` moves two things at once: the candidate buffer and the specular-chain hash counter.
  Separating them (`benchmark/dropout_hash_vs_buffer_0916.py`, 12 selected isolated poses): with the buffer fixed at
  2e6 (never more than 1.43 % full), raising only the hash counter restored the env_ground specular at **5/6 (8e6)
  and 6/6 (32e6)** of the poses chosen because cap 32e6 had recovered them; the one sampled pose cap 32e6 did not
  recover (8015) still lacked it at hash 32e6; the other 5 sampled core poses never lacked it.
  At hash 8e6, on the 12 selected isolated poses, buffer 2e6 -> 8e6 gave no incremental env-path recovery or loss.
  Its only path-count change (8015, +1 path, 1.97e-5 of |m|) is at the same pose where the diagnostic's own
  production-setting re-solve differs from the stored field by one path. Buffer tested at one hash size only.
  *(Corrected 09-17: this bullet said «5 of 12» and «6 of 12» — a denominator that mixed poses that never lacked the
  path — and that the buffer change altered nothing at all, which the ledger does not support.)*
* Changing the solver seed moves the field outside the isolated poses by 2.2e-3 — a hundred times the
  repeat-run noise, and a hundred times what the cap does. The seed is the bigger lever on everything else.

**Not established — do not write these anywhere:**

* That hash collisions are the cause. Nothing counts collisions or ties a specific lost candidate to
  the missing path. Say **"enlarging the hash counter at a fixed buffer brings the path back"**.
* That the buffer is irrelevant in general — the buffer-alone contrast was run at hash 8e6 only, and
  the 32e6 x 32e6 grid point died of out-of-memory and was not repeated.
* That the isolated poses are wrong and the neighbours are right. Both are approximations; which one
  matches reality is a question for measurement (`memory: dont-call-sionna-wrong`).
* Anything about the 15 surviving "core" poses (cap 32e6) as one class — field level and cap behaviour already split
  them into 7 falls (env_field_drop_halfmedian; the ladder above) and 8 rises that do not change with cap or repeat.
  The 6 sampled are 5 rises + 1 fall (8015); 9 were never diagnosed. *(Corrected 09-17: it said «6 of them were
  sampled, not all 15».)*

## 4. What the reviewer asked for next, in order

1. **All 15 residual core poses** with neighbours and controls — environment-only vs drone-only vs
   mixed paths, plus an occlusion check. Today only 6 were sampled.
2. **OFDM pilot on CPU first**, on a synthetic delay/Doppler channel: vary the payload, decide how null
   subcarriers are handled, calibrate the no-target case separately. Only then use rotor-pose fields.
3. **Cross-compare the raw metrics of 0946** once the queue finishes, and soften that file's header,
   which still reads as a verdict on the aimed antenna.

## 5. Waiting on the user — do not act on these without a word

* `git` history: dropping `refs/original` and expiring the reflog would return ~2.7 GB and change no
  commit hash. The user asked about it; approval was never given.
* Deferred cleanup units: `jihyuck/` plus the PX4 bridge scripts, the `work/sweep_0904` kit, the root
  legacy notebooks (report00/04/05/07), `docs/ENGINE_VALIDATION.md`, and the other session's ISAC
  draft set. Each needs a yes/no.
* The HW1 deck cover says «Team Meeting» and carries the 0910 deck's presenter name. If this talk is
  given in class rather than at the team meeting, the cover title, the date and the name all change.

## 6. Decks

```
/workspace/team_meeting/hw1_problem5/           CSE301 HW1 Problem 5, 5-minute talk
  hw1_problem5_inversions_v2.pptx    ⭐latest — 7 slides, pushed as 8609710
  make_hw1_p5_v2.py                  the source of truth; never edit the .pptx
  bake_figs.py                       five figures; SLOTS controls how large code reads on a slide
  preview_v2/p01..p07.png            layout check (../teammeeting_0910/preview.py <pptx> <outdir>)
/workspace/team_meeting/teammeeting_0910/       the 2026-09-14 team meeting deck (v43 was presented)
```

v2 fixed two things that were actually wrong in v1: the merge did not write back into `A`, and `mid`
was not floored. Both were found by an independent check, not by the build.

## 7. Right now

Nothing is blocked and nothing is half-finished. Both decks are built, previewed and pushed.

```
/workspace/team_meeting/teammeeting_0916/     ⭐new — the isolated-pose item for the next meeting
  teammeeting_0916_v1.pptx                    5 slides, pushed as 271cefc
  make_deck_0916_v1.py                        the source of truth; never edit the .pptx
  bake_figs.py                                reads the ledgers and shards directly, no hand-typed numbers
```

The four content slides are: the cell pose by pose against the same scene with no ground · the same
data as a distribution (two groups, 40 dB of nothing between) · the path-limit ladder · and what
changes in practice. The slide faces deliberately avoid the ledger's 99.96 % "share of pose-varying
power": the poses were selected for being far from the median, so that number is close to circular.
The 0.05 dB agreement of the other 8,102 poses and the 935x drop in the largest pose-to-pose step
are used instead — neither follows from the selection rule.

Left for whoever picks this up: re-queue the three GPU-2 lines (§2), then the reviewer's three steps
(§4). The deck is a draft — the user has not seen it yet.
