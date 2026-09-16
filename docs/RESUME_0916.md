# Current status — 2026-09-16, 16:40 KST

> The in-repo edition. `/workspace/RESUME_NOW.md` is the top-level pointer to this file.
> Written so a fresh session can pick up without reading the transcript.
> The 2026-09-02 edition is at `/workspace/archive/2026-09/resume/RESUME_NOW_0902.md`.
> Python is **/workspace/.venvs/py312/bin/python**. For CPU work put `CUDA_VISIBLE_DEVICES=""` in front.
> Repo conventions: `../CLAUDE.md` (language policy, claim gate) and `HANDOVER_MAP.md`.

## 0. One line

Three GPU queues are running on cards 2/3/4 and will not dry out before tomorrow midday. The open
question is the **isolated poses**: about 1 % of drone poses return a path set their neighbours have,
and that 1 % carries essentially all of the pose-to-pose change. Nothing needs a human right now.

## 1. GPU rules — read this before launching anything

`runners/GPU_HOLD.json` is the only switch. The supervisors **re-read it every round**, so a
change takes effect without restarting anything.

| Card | State | Note |
|---|---|---|
| 0 | held | on loan earlier today, **evacuated 15:55 KST at the user's request** |
| 1 | held | standing rule |
| 2 | **on loan** | user 15:58 KST: 「이제 gpu 2번을 한동안 임시로 쓰다가 내가 말하면 비워줘!! 0번 쓰던것처럼」 |
| 3, 4 | ours | standing rule since 2026-09-15 |

**To give card 2 back the moment the user asks** — one command, nothing else:

```bash
cd /workspace/sionna && /workspace/.venvs/py312/bin/python runners/evacuate_gpu.py 2 --go
```

It holds the card, stops **only** the workers whose `/proc/<pid>/environ` says that card, and writes
the interrupted job lines to `runners/jobs_REDO_gpu2_<UTC>.txt` so they can be re-queued. Never
`pgrep -f` (it matches your own shell) and never kill a supervisor.

The last evacuation left `runners/jobs_REDO_gpu0_20260916T065550Z.txt`; those 3 lines are already
re-queued inside `jobs_0947`, which is why `sup_cap_antenna_0946.log` shows `실패 3`.

## 2. Queues — three supervisors, nothing waiting on a human

```
runners/jobs_0945_cap_ladder.txt      8 left   logs/sup_cap_0945.log
runners/jobs_0946_cap_antenna.txt     5 left   logs/sup_cap_antenna_0946.log   (3 = the evacuated lines, re-bought in 0947)
runners/jobs_0947_repeat_spread.txt   4 left   logs/sup_repeat_0947.log
```

Check with `tail -2 runners/logs/sup_*.log` — the status line reads
`G<card>:<running>/<cap> · 큐 <done>/<total> · 워커 <n>`. A ground-cell shard is ~35-110 min, a
street-canyon shard ~225 min. Before adding a queue, split NEW/DONE/STALE/BAD with
`runners/filter_jobs.sh`; shard names carry the generation tag (`_rt210`, `_mp<N>`, `_ss<N>`, `_rep<N>`).

## 3. The isolated poses — what is established and what is not

Ledgers: `outputs/dropout_knobs_0916.json`, `outputs/dropout_hash_vs_buffer_0916.json`,
`outputs/dropout_paths_0916_diff.json`. Definition: a pose whose complex field sits more than
20 x median-absolute-deviation from the cell's complex median.

**Established** (ground cell, 8,192 poses, 0.044° apart, one shard each):

* 90 of 8,192 poses (1.1 %) are isolated, and they carry **99.96 %** of the pose-to-pose varying power.
  Street canyon 339, canyon at -30 deg elevation 96, **free sky 0** — the ground has to be in the scene.
* At 30 of 32 checked ground pairs, the pose is missing exactly one path the neighbour 0.044 deg away
  has: a single-bounce specular off `env_ground`, tau = 46.8 ns, |a| = 1.9e-4.
* Raising the solver's path limit thins them out but never to zero:
  cap 1e6 -> 161, 2e6 (production) -> 90, 8e6 -> 34, 16e6 -> 22, 32e6 -> 15.
* Outside the isolated poses the cap changes the field by 2.2e-5, against 2.0e-5 for **re-running the
  identical job**. So the cap is not quietly reshaping the rest of the cell.
* `--max-paths` moves two things at once: the candidate buffer and the specular-chain hash counter.
  Separating them (`benchmark/dropout_hash_vs_buffer_0916.py`): with the buffer fixed, hash 2e6 -> 8e6
  brings the missing path back at **5 of 12** isolated poses and 8e6 -> 32e6 at one more (6 of 12);
  with the hash fixed, buffer 2e6 -> 8e6 changes **nothing** (0 recoveries, 0 losses, both directions).
* Changing the solver seed moves the field outside the isolated poses by 2.2e-3 — a hundred times the
  repeat-run noise, and a hundred times what the cap does. The seed is the bigger lever on everything else.

**Not established — do not write these anywhere:**

* That hash collisions are the cause. Nothing counts collisions or ties a specific lost candidate to
  the missing path. Say **"enlarging the hash counter at a fixed buffer brings the path back"**.
* That the buffer is irrelevant in general — the buffer-alone contrast was run at hash 8e6 only, and
  the 32e6 x 32e6 grid point died of out-of-memory and was not repeated.
* That the isolated poses are wrong and the neighbours are right. Both are approximations; which one
  matches reality is a question for measurement (`memory: dont-call-sionna-wrong`).
* Anything about the 15 surviving "core" poses as a class. 6 of them were sampled, not all 15.

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

Nothing is blocked. The queue runs itself. The next piece of work in progress is a set of team-meeting
slides on the isolated poses, drawn from the ledgers in §3 — the numbers are ready, the figures are not.
