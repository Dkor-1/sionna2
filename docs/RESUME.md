# ⭐Current status

> ## ⛔⛔**From 2026-09-17 on, this file is not the one — start reading from [`RESUME_0917.md`](RESUME_0917.md).**
> The 09-16 edition, [`RESUME_0916.md`](RESUME_0916.md), and the 09-08 edition, [`../work/sweep_0904/RESUME_0908.md`](../work/sweep_0904/RESUME_0908.md), are also superseded by it.
> The 09-06 edition below is stale in all of its queue numbers and deck versions (the 0906·0908 queues have finished and the deck is at v8).
> It is kept because the ledger list and the prohibition list from §5 onward are still in use.
>
> **What is in RESUME_0908.md** — the investigation of missing outdoor paths and the correction to the built-in scene comparison ·
> the limits of the Hampel filter comparison · the handover of the presentation materials and the queues.
> The latest additional check on the built-in scene comparison is in `outputs/builtin_scene_diagnosis_0908.json`.

---

# 2026-09-06 (Sun) night edition (stale — read the part above first)

> Python is **/workspace/.venvs/py312/bin/python**. For CPU work, put `CUDA_VISIBLE_DEVICES=""` in front.

## 0. One line
Full sweep done (900/900) · new file rules done · 09-10 deck draft done (v6) · **three GPU queues are running and a fourth is waiting on a chain**.
No human-run work is in progress right now. When the queue results arrive, the next touch-up is to raise deck page 5 from «two arms» → «five arms».

## 1. Queues — three supervisors + one chain
```
  jobs_0906.txt  큐 93/122   jobs_0907.txt  큐 3/118    jobs_0908.txt  큐 2/78   
  jobs_0909.txt  대기 — runners/chain_0909_after_0908.sh 가 0908 이 78/78 된 뒤 30 분 지나 띄운다
```
| Job order | Question |
|---|---|
| 0906 | Frontal overlap window — azimuth·elevation ladders · airframe · range · ray budget · depth 3 · thick poses |
| 0907 | Reference point on the ⓖ axis (4e9) · empty interval · narrowing the cliff · **angle or lateral distance (30·60·120 m)** · airframe size scale · reproduction · depth 3 |
| 0908 | ⭐**Near-axis for the two refraction-on arms**(→deck page 5 five arms) · truncated cells · 0.7° seed · 0.05°/0.07° reproduction · window width per budget |
| 0909 | **Outdoor clutter from multiple angles** — ground roughness S · someone else's scene · range · depth · azimuth · repeats across four arms |

Check:
```bash
cd /workspace/sionna
for f in 0906 0907 0908 0909; do printf "$f "; tail -1 runners/logs/sup_jobs_$f.log 2>/dev/null | grep -oE "큐 [0-9/]+ · 워커 [0-9]+"; echo; done
ps -eo pid,args | grep "[w]orker_supervisor" | grep -v "bash -c"      # 감독자 목록
ps -eo args | grep -c "[e]levation_sweep_md.py"                       # 워커 수 (정상 8~9)
cat runners/logs/chain_0909.log 2>/dev/null                            # 사슬이 0909 를 띄웠나
```
⛔**If a supervisor has died** — it reads the job file only once at startup, so just launch it again (finished shards are skipped):
```bash
setsid nohup /workspace/.venvs/py312/bin/python runners/worker_supervisor.py runners/jobs_09XX.txt runners/logs/sup_jobs_09XX.log > runners/logs/sup_jobs_09XX.boot 2>&1 < /dev/null &
```
⛔When killing, if you use `pgrep -f`, your own shell dies the moment that name appears on the same command line (exit 144) — extract the PID and use the number.
⛔If the workers drop to 4 and the supervisor log shows «⛔대기: CPU 사용률» [Waiting: CPU utilization], a process from **someone else's session** is eating the CPU — do not touch it; wait.
New job orders go in after `runners/filter_jobs.sh` sorts each line into NEW·DONE·STALE (make_jobs_0907 header).

## 2. Thursday (09-10) deck
`teammeeting_0910/_out_0910_v6.pptx` 9 pages — done. For details, `teammeeting_0910/RESUME_0910.md`.
When queue 0908 ⓐ arrives, add the two arms to `ARMS` in `bake_window.py` and make v7. A new version gets a new number.

## 3. Full sweep — done
900/900 found and fixed · rebuilds 58/58 · four gates passed · `work/sweep_0904/`(STATE.json · findings · specs).
Gates:
```bash
for g in check_retracted check_stale_titles check_row_pointers check_new_file_rules; do printf "$g "; CUDA_VISIBLE_DEVICES="" PYTHONPATH=src:benchmark /workspace/.venvs/py312/bin/python benchmark/$g.py >/dev/null 2>&1 && echo ✅ || echo ⛔; done
```
⛔**Two builders that could not run on CPU — left for the user to run** (out of the 58 rebuilds):
- `benchmark/report16_base.py` — hangs when run on CPU (900s ×2 · even at 3600s, CPU 0.2%). It appears to be waiting on a GPU probe.
  `PYTHONPATH=src:benchmark /workspace/.venvs/py312/bin/python benchmark/report16_base.py`
- `src/experiment_md_range.py` — eats 14 cores with 11 processes and blocks the queue. It is a one-line docstring fix, so it is not urgent.
  `cd /workspace/sionna && PYTHONPATH=src /workspace/.venvs/py312/bin/python src/experiment_md_range.py` (when the queue is empty)
- `src/make_report02_target.py` — `assert worst < 5e-3` ledger drift, since before the full sweep.

## 4. New file rules
`docs/NEW_FILE_RULES.md` (900 cases → 16 kinds + eight lines before saving) · gate `benchmark/check_new_file_rules.py`(baseline 688, may only decrease).

## 5. Ledgers newly made this time (source of the deck numbers)
- `outputs/front_window_0906.json` — frontal window: per arm, the «fraction of overlapping poses» and the median.
  ⛔**The boundary differs per arm — do not write it as one.** The two diffuse-only·diffraction arms are azimuth **0.11↔0.12°** ·
  elevation **−0.15↔−0.16°**; the two refraction-on arms are azimuth 0.10↔0.15° · elevation −0.15↔−0.20°.
  Until 2026-09-07, this line and the conclusion line of deck v6 had the refraction-on arms' values written without arm names,
  while the deck figure was drawing the two diffuse-only·diffraction arms (it went out with the arms mismatched). The deck was fixed in v7.
  ⚠The diffraction arm's azimuth ladder is not monotonic — at 0.05° the number of overlapping rows jumps to 107 in one pose,
  drops to 1.0 % at 0.07°, and is 100 % again at 0.10~0.11°. That is why `edge()` gives
  {last_on 0.11, first_off 0.07}, and it is **a value that cannot be cited as the boundary**.
- `outputs/front_repeat_0906.json` — 0°/0.2° pair: for the diffuse-only arm at 0°, removing the repeats takes the width 9.5402 → 0.0063 dB, correlation 0.999990; at 0.2° the two arrays are bit-identical.
⛔«정확히 3 배» [exactly 3×] forbidden (max 2.9992) · «솔버가 틀렸다» [the solver is wrong] forbidden · size of the rhythm share forbidden (R29) · chamber forbidden.

## 6. Open investigation (lives only within the session)
A clutter experiment design investigation was running as a workflow (run `wf_a265209d-c0e`, script
`~/.claude/projects/-workspace-sionna/…/workflows/scripts/clutter-experiment-design-wf_a265209d-c0e.js`).
If it was cut off, look at journal.jsonl and attach only the knobs that are not in the 0909 job order (72 lines) as 0909b. If there are none, stop.
⛔Our kernel rejects `--env` (elevation_sweep_md.py:484) — outdoor «five arms» go up to four only.

- ⛔**Spot that cannot be baked again**: `src/make_report02_target.py` stops (the mesh gallery ledger is stale · phantom4 2.13 %). Diagnosis is in [`docs/MESH_GALLERY_STALE_0914.md`](MESH_GALLERY_STALE_0914.md). Do not mix it with the solver version change; fix it separately.
