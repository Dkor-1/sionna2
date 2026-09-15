# Running the queue by hand — terminal runbook

> ⛔⛔**Do not use `pgrep -f`.** The moment that name appears on the same command line, your own shell dies
> (exit 144 · `docs/RESUME.md:45`). On 2026-09-10 this runbook was switched entirely to `ps` + `[대괄호]` [brackets].
> ⭐The queue has **2 tiers**: the supervisor (runs one job file) and, above it, whatever starts the next job file.
> As of 2026-09-15 that is one watcher process per hand-off: `runners/watch_then_start.py`, or its fixed-name form
> `runners/watch_0939_after_0940.py` for the 0940 → 0939 hand-off. A watcher starts the next supervisor as soon as the
> previous supervisor's log shows every line launched (`큐 K/N` with K = N), while the previous workers are still running.
> `watch_then_start.py` also starts it if no supervisor and no worker has run for `--idle-fallback-min` minutes.
> ⚠The keeper (`runners/queue_keeper_0827.sh`) starts the next queue only when no supervisor is running. It used up its
> chain (`queue_chain_0910.txt`) on 2026-09-14 and is not running.
> Read section 1 first.

> How to write, run and stop the supervisor (`runners/worker_supervisor.py`) and the workers (`benchmark/elevation_sweep_md.py`)
> **by hand**. Written as of 2026-08-25; brought up to date with the code on 2026-09-15 (a section-by-section audit
> against `runners/` and `benchmark/elevation_sweep_md.py`, each change checked by a second reader).

```bash
# Start with these two lines from anywhere
cd /workspace/sionna
PY=/workspace/.venvs/py312/bin/python
```

---

## 1. Structure — who does what

⭐**There are 2 tiers.** The lower box is the supervisor that «runs one job file». The upper box starts the next job file.
Since 2026-09-15 that is a watcher, one per hand-off: `runners/watch_then_start.py` (named by `--name`), or the fixed-name
`runners/watch_0939_after_0940.py` for the 0940 → 0939 hand-off (log `watch_0939.log`, lock `.watch_0939.started`).
From 08-27 this was done by the keeper `runners/queue_keeper_0827.sh`. Its chain path is fixed inside the script
(`runners/queue_chain_0910.txt`), and it starts the next chain line only when 0 supervisors are running. On 09-14 19:02 it
logged 「사슬 소진 — 지킴이 종료」 [chain exhausted, keeper exiting], and it is not running now. The 08-25 edition of this
runbook had only the lower box.

```
runners/logs/sup_<prev>.log ──► watch_then_start.py ─┐  (watcher: every 30 s reads the previous supervisor's log after its LAST
 (previous supervisor's log)     (--prev-log --prev-jobs  │   start header; when the latest status line shows «큐 K/N» with K = N,
                                  --next-jobs --next-log  │   it turns itself into the next supervisor, while the previous workers
                                  --name                  │   are still running.
                                  --idle-fallback-min)    │   ⚠ It also starts the next supervisor if no supervisor and no worker
                                                          │   has existed for --idle-fallback-min minutes (default 20; 0 = off).
                                                          │   Starts once: lock runners/logs/.watch_<name>.started.
                                                          │   Log: runners/logs/watch_<name>.log)
                                                          ▼
jobs.txt  ──►  worker_supervisor.py  ──►  elevation_sweep_md.py  ──►  outputs/elev_sweep_shards/*.npz
 (one line =     (reads its job file into memory      (the actual computation; holds       (shard files)
  one job)        at start and starts workers;         one GPU while running)
                  every 30 s re-reads
                  runners/GPU_HOLD.json and counts
                  every worker on each card, other
                  supervisors' workers included)
```

- ⛔**One supervisor per job file.** Supervisors on *different* job files may run at the same time. `runners/watch_then_start.py`
  starts the next supervisor as soon as the previous one logs `큐 N/N`, while its last workers are still running. (The keeper
  `queue_keeper_0827.sh` still waits for 0 supervisors.) Each supervisor counts every `elevation_sweep_md.py` process in `ps` per
  card, reading `CUDA_VISIBLE_DEVICES` from each one. It holds its own per-card targets and its own `SIONNA2_HARD_TOTAL` against
  that combined count, so supervisors started with the same settings share the caps instead of stacking them. Two supervisors on
  the **same** file, or on files with overlapping lines, **launch the same job twice**. A supervisor does not look at what another
  supervisor has launched. A worker skips a shard only if a complete shard file is already there when it reaches that shard, and
  nothing marks a shard as in progress.
- The supervisor **does not kill workers** (repository rule, the 0811 incident). It scales down only by «not refilling
  finished slots».
- The supervisor **reads the queue into memory at start** and advances a cursor. So if it dies it runs **from the beginning** —
  to continue, make a new file containing only the remaining lines and start that (worked example: `/workspace/archive/2026-09/sionna/runners/QUEUE_STATE_0908.md`).

### Watchers — how queues continue on their own (current)

| Watcher | When it starts the next queue |
|---|---|
| `runners/watch_then_start.py` | When the latest status line (after the previous log's last supervisor start header «큐 N 줄 · 규약» [N-line queue · rules]) shows `큐 K/N` with K = N, **or** ⚠after `--idle-fallback-min` minutes in a row (default 20) with no `worker_supervisor.py` of any queue and no `elevation_sweep_md.py` process (dry runs not counted). With `--idle-fallback-min 0` there is no fallback. If the previous supervisor exits before K = N and writes its `== 종료 … ==` line, the watcher writes the manual command to `runners/logs/watch_<name>.log` and exits. ⚠If the supervisor was killed without writing that line (SIGKILL, OOM), the watcher writes nothing and waits forever |
| `runners/watch_0939_after_0940.py` | Only when 0940 shows K = N. If the 0940 supervisor exits earlier and writes `== 종료`, it does not start 0939 and writes the manual command to `runners/logs/watch_0939.log`. ⚠If it was killed without that line, the watcher waits forever |

- ⛔A watcher writes `runners/logs/.watch_<name>.started` **before** it starts the supervisor, and it does not check that the job
  file exists. If the start fails (for example the job file is missing), it is **not retried**, and a new watcher with the same
  `--name` exits at once. Create the job file first.
- It starts nothing if a supervisor is already running a file with the `--next-jobs` name, and it starts only once.
- ⚠A wrong `--prev-log` fails in two ways. A path that never gets a start line leaves only the idle fallback. A path to an **older
  log that already ends with `큐 N/N`** (for example a keeper log `sup_jobs_0930.log`) starts the next supervisor on the first 30-s
  poll. Run `tail -n 2` on the path before you start the watcher.
- Watchers start no child processes. They read logs and `/proc`, then replace themselves with the supervisor (`execve`, same PID).
  Stopping a watcher **before** the hand-off leaves running work untouched. ⛔After the hand-off, the PID in `watch_<name>.log`
  («watcher started (pid N)») is the new supervisor. Find a watcher by its script name in `ps`, never by that PID.
- ⚠A supervisor started by a watcher gets the watcher's environment. `SIONNA2_MAX_TOTAL` is not set to 9 as the keeper did, so it
  is 8 unless you exported it. **Trust «전체 상한 N» [total cap] in the start header.**
- ⚠`watch_<name>.log` uses the container clock (UTC); supervisor logs are KST.

### The keeper — `queue_keeper_0827.sh` (not running since 2026-09-14)

⚠History: the keeper exited on its own at 2026-09-14 19:02 KST when chain 0910 ran out (last line of its log). No keeper process
runs now. The queues started on 2026-09-15 are chained by `runners/watch_then_start.py` (0941 after 0939) and
`runners/watch_0939_after_0940.py` (0939 after 0940).

| Item | File | What it does |
|---|---|---|
| Chain | `runners/queue_chain_0910.txt` | List of job files to start next. One per line, `#` is a comment. ⚠The path is fixed in the script (`CHAIN=`, line 25). A new chain file is not read unless you edit `CHAIN`/`LOG`/`DONE` (lines 25-27) |
| Keeper | `runners/queue_keeper_0827.sh` | Checks for supervisors every 30 s. **If there are 0**, it starts the next line of the chain, waits 30 s and checks that it started. A failed start is tried again about 90 s after the failed check (sleep 60 plus the 30-s loop sleep, so about 2 min between launches), only while there are still 0 supervisors, up to 3 tries. ⛔If two files in a row fail 3 tries each, the keeper exits and leaves the rest of the chain untouched. Start it from `/workspace/sionna` with `setsid nohup bash runners/queue_keeper_0827.sh >/dev/null 2>&1 &` |
| Already-started list | `runners/logs/queue_chain_0910_done.txt` | ⭐Since 2026-09-11 a line goes here only after its start is confirmed (a supervisor holding that file is alive, or its supervisor log was written after the launch), after 3 failed tries (except when it is the second file in a row to fail; then the keeper stops without writing it), or when the file does not exist. It is no longer written before the start. A line in this list is never looked at again |
| Keeper log | `runners/logs/queue_keeper_0910.log` | 「▶ 다음 큐 띄움」 [▶ next queue started] · 「✅ 떴다 — done 에 적었다」 [started — written to done] · 「⛔안 떴다」 [did not start] · 「사슬 소진 — 지킴이 종료」 [chain exhausted — keeper exiting] |

- ⛔It starts **only files written in the chain**. A missing file is logged as 「⛔파일 없음: … — 건너뛴다」 [file missing — skipping],
  written to the done list, and never looked at again.
- ⛔**Create the file first**, then write it into the chain. Reverse the order and that line never runs.
- ⛔**Do not write** a hand-started queue into the chain — if you do, that queue starts twice.
- When the chain is empty the keeper **exits by itself** (「사슬 소진 — 지킴이 종료」). ⛔Since 2026-09-11 it also **stops** (exit 1)
  when two files in a row each fail all three start tries (「⛔⛔연달아 … 지킴이가 멈춘다」). A try fails when, 30 s after starting,
  no supervisor holds that job file and its `runners/logs/sup_*.log` has not been written since. ⚠The first of the two files is
  already in `…_done.txt` and will not be retried. The second file and everything after it stay unmarked, and the keeper log
  prints the restart command. Either way the keeper starts nothing more (running workers are not touched).
- Supervisors started by the keeper use `SIONNA2_MAX_TOTAL=9` (hard-coded in the script). This may differ from the value
  used when starting by hand, so **trust «전체 상한 N» [total cap] in the start header**.

### Ordering flow — up to one job running

```
① runners/make_jobs_XXXX.py       writes the question · kill conditions · what it does not answer, and emits job lines
        │                          ⛔do not write only lines — also write «what it does not answer»
        ▼  python runners/make_jobs_XXXX.py > runners/jobs_XXXX.txt   (or write the file by hand with the same # header)
② runners/jobs_XXXX.txt
        │
        ▼  ⭐always before ordering — runners/filter_jobs.sh
③ split into NEW · DONE · STALE · BAD   buying only NEW is the default. STALE is bought again with --overwrite
        │                               only when the question needs n_dup
        │                               ⛔BAD = do not order. The dry-run did not produce a shard name
        │                               (an argument error such as an unknown --env, or the 300 s timeout).
        │                               The line reads BAD|<reason>|<job line>; the reason is the builder's
        │                               first ⛔ line, else its last output line, else «출력 없음 (rc=…)» (rc=124 = timeout)
        ▼
④ start a watcher for the hand-off   (⛔after creating the job file and filtering it)
     setsid nohup $PY runners/watch_then_start.py \
       --prev-log runners/logs/sup_<prev>.log --prev-jobs jobs_<prev>.txt \
       --next-jobs runners/jobs_XXXX.txt --next-log runners/logs/sup_XXXX.log \
       --name XXXX --idle-fallback-min 20 \
       > runners/logs/watch_XXXX.nohup 2>&1 < /dev/null &
        │
        ▼
⑤ the watcher becomes the next supervisor (same PID) when either
     · in sup_<prev>.log, after its last «큐 N 줄 · 규약» start line, the latest status line shows «큐 K/N» with K = N, or
     · no worker_supervisor.py and no elevation_sweep_md.py process has existed for --idle-fallback-min minutes in a row
   → the supervisor starts workers → shards land
```

⚠`queue_keeper_0827.sh` reads only `runners/queue_chain_0910.txt`, and that chain ran dry on 2026-09-14. Writing a file into a
chain starts nothing unless a keeper is running and reading that chain.

The one-liner that filters:

```bash
grep -vE "^\s*(#|$)" runners/jobs_XXXX.txt \
  | xargs -d"\n" -P 4 -I{} runners/filter_jobs.sh {} | cut -d"|" -f1 | sort | uniq -c
# ⛔If BAD shows up in the count, read those lines whole before ordering anything
#   (do not cut on "|" — some builder messages contain "|", e.g. the --sw format error)
grep -vE "^\s*(#|$)" runners/jobs_XXXX.txt \
  | xargs -d"\n" -P 4 -I{} runners/filter_jobs.sh {} | grep '^BAD'
```

---

## 2. Writing a job file

One line is one job, and that line becomes the arguments of `elevation_sweep_md.py` as is.
Lines starting with `#` and blank lines are skipped.

```bash
cat > runners/jobs_mine.txt <<'EOF'
# My queue — 2026-08-25
--engine sionna --spp 4000000000 --sw R0D1E1F1 --max-depth 2 --drone mini5pro --range-m 15 --n-poses 8192 --els=0,-30 --shard 0 --nshards 2
--engine sionna --spp 4000000000 --sw R0D1E1F1 --max-depth 2 --drone mini5pro --range-m 15 --n-poses 8192 --els=0,-30 --shard 1 --nshards 2
EOF
```

⚠**One job must be exactly one line.** Inside `<<'EOF'` a `\` line break is **not** joined — it is written into the file as is.
The supervisor reads the file **line by line** and turns each line into a job: the first half keeps the trailing `\` as an
argument and fails (rc=2), and the part after the break runs as its own job with the defaults (`--engine ours`). Always write one long line.

### Frequently used arguments

| Argument | Meaning |
|---|---|
| `--sw R?D?E?F?` | Physics switches. **R**=refraction **D**=diffraction **E**=edge diffraction **F**=diffuse. `R0D1E1F1` = only refraction off |
| `--els=0,-30` | Elevation list. **One job runs every elevation written here** → it produces that many files |
| `--shard k --nshards n` | Split the poses into n parts and take only the k-th. Parts are shared **by skipping through the poses** |
| `--n-poses 8192` | Number of poses |
| `--range-m 15` · `--drone mini5pro` | Range · airframe |
| `--spp 4000000000` | Number of rays |
| `--max-depth 2` | Reflection depth. ⛔In combinations with diffraction on, 3 must not be dropped (R13, docs/NEXT_EXPERIMENTS.md). ⚠The example lines above (`R0D1E1F1 --max-depth 2`) only show the format; check R13 before copying them |
| `--env outdoor01_ground` · `--env sionna:simple_street_canyon` | Outdoor scene (`--engine sionna` only). Built-in Sionna scenes take a **colon**. An unknown name stops the dry-run with ⛔ (filter_jobs.sh shows BAD). `--env-alt` sets the drone height above ground, for our scenes (`outdoor01*`) only; with a `sionna:` scene it stops with ⛔ (height fixed at 25 m) |
| `--ant-pattern tr38901` · `--ant-cap` · `--aim-offset` | Directional antenna aimed at the drone with a fixed `look_at`; attenuation cap in dB; aim offset in degrees. The shard name gets `_ant…` / `_aim…` |
| `--inmem` · `--no-inmem` | Meshes are loaded in memory, without intermediate files. ⭐**Default since 2026-08-29** — `--inmem` has no effect (kept so old job files still parse). `--no-inmem` restores the old path through OBJ files on disk (regression checks only). The shard name is the same either way |
| `--overwrite` | Compute **again** even shards that already exist |
| `--dry-run` | Print only «present/absent» and the shard file name, without computing |

### ⭐Always before running — see what already exists

Workers **skip a shard whose file exists and reads back intact** (without `--overwrite`); a truncated or damaged file is computed
again. So rewriting the queue does not redo finished work — ⚠**but only work finished under the same shard name.** Names carry the
solver build (`_rt210` under the installed sionna-rt 2.1.0). Shards from the baseline 2.0.1 build have no tag, so the same line
computes them again under the new name. ⚠`--dry-run`'s «있음» [present] checks only that the file exists, not that it is intact.

```bash
# ⛔Do not run the builder's --dry-run bare. Without CUDA_VISIBLE_DEVICES, gpu.pick() picks a card
#   (2·3 preferred; it does not read runners/GPU_HOLD.json) and importing sionna.rt opens CUDA on it.
#   runners/filter_jobs.sh hides the GPUs, sets SIONNA2_ALLOW_CPU=1 and gives each line 300 s.
grep -vE "^\s*(#|$)" runners/jobs_mine.txt \
  | xargs -d"\n" -P 4 -I{} runners/filter_jobs.sh {} > /tmp/chk_mine.out
cut -d"|" -f1 /tmp/chk_mine.out | sort | uniq -c   # NEW = absent · DONE = present with n_dup · STALE = present without n_dup
grep '^BAD' /tmp/chk_mine.out   # ⛔BAD = do not order. Reason = builder's first ⛔ line, else its last output line, else rc (124 = 300 s timeout)
```

⚠filter_jobs.sh judges a line by the **first** `[dry]` file name only — a line with `--els=0,-30` is judged by its first elevation's shard.
To look at one line by hand: `CUDA_VISIBLE_DEVICES="" SIONNA2_ALLOW_CPU=1 $PY benchmark/elevation_sweep_md.py <line> --dry-run`
(without `SIONNA2_ALLOW_CPU=1` a `--engine sionna` line stops at the CUDA check before it prints any `[dry]` line).

---

## 3. Starting

```bash
setsid nohup $PY runners/worker_supervisor.py \
  runners/jobs_mine.txt \
  /workspace/sionna/runners/logs/sup_mine.log \
  > runners/logs/sup_mine.nohup 2>&1 < /dev/null &
# ⚠Do not trust $! here: in an interactive terminal setsid forks and $! is a short-lived parent. Find the supervisor by its job file:
sleep 2; ps -eo pid,etimes,args= | awk '$3 ~ /\/python[0-9.]*$/ && $4 ~ /worker_supervisor\.py$/ && $5 ~ /jobs_mine\.txt$/ {print "supervisor pid", $1, $2"s"}'
```

- `setsid` is the key — it keeps running even if the terminal or SSH disconnects.
- If the log path is omitted, it goes to `runners/logs/supervisor.log`.
- ⚠Do not send output to `/dev/null`. If the supervisor cannot write its log file, it writes that message to stderr and keeps
  running (since 2026-09-14). A crash at startup, such as a wrong jobs-file path, also shows up only on stderr. Look in the
  `.nohup` file when the log has gone quiet. An empty `.nohup` file is normal. (When the disk is full, the `.nohup` file on the
  same disk cannot be written either.)

### Resource discipline — tighten with environment variables

The defaults are already conservative for this container, but **if you want to tighten further**, prefix these:

```bash
SIONNA2_CPUS=8 SIONNA2_MAX_TOTAL=4 SIONNA2_HARD_TOTAL=6 \
SIONNA2_THREADS=2 \
setsid nohup $PY runners/worker_supervisor.py runners/jobs_mine.txt \
  runners/logs/sup_mine.log > runners/logs/sup_mine.nohup 2>&1 < /dev/null &
```

| Variable | Default | Meaning |
|---|---|---|
| `SIONNA2_MAX_TOTAL` | 8 | **Budget** cap for the target allocation (not a hard launch cut-off) ⚠The keeper starts with **9** (`queue_keeper_0827.sh`). The watcher scripts (`watch_then_start.py`, `watch_0939_after_0940.py`) and hand starts pass on their own environment and do not set it, so without it they get 8. **Trust «전체 상한 N» [total cap] in the start header** («큐 N 줄 · 규약 … · 전체 상한 N»). The log is appended across restarts, so read the **last** header. ⚠The «상한N» inside each status line is the **per-card** cap (0 when the card is held, excluded or full), not this budget |
| `SIONNA2_HARD_TOTAL` | 12 | **Absolute line**. Nothing is started beyond it |
| `SIONNA2_THREADS` | 2 | Threads per worker. ⛔Do not raise it — the cause of thread runaways |
| `SIONNA2_CPUS` | auto | Number of CPU cores in our share. Denominator of the CPU brake |
| `SIONNA2_RAM_GB` | unused while the cgroup has a ceiling | Our RAM share in GiB. ⚠It is read **only** when `/sys/fs/cgroup/memory.max` is `max` (no ceiling). In that case it is required: without it free RAM reads 0 and nothing is ever started. Today the cgroup ceiling is **24 GiB**, so this variable is ignored |
| `SIONNA2_RAM_FLOOR_GB` | 4 | Free-RAM floor for new launches (see safety lines below) |
| `SIONNA2_EXCLUDE_GPUS` | none | Like `"0,3"`. Read **once at start**, for that supervisor only. Changing it needs a supervisor restart |

⭐**To take cards out without a restart, use `runners/GPU_HOLD.json`.** Every running supervisor re-reads it every round (about
30 s). `{"gpus": [0,1,2]}` holds those cards unconditionally. `{"gpus_if_external": [4], "external_mb": 5000}` holds card 4 only
while memory on it that is not ours (memory in use on the card minus what our processes use) is ≥ 5000 MB. Held cards show `⛔보류` [held] in the status
line. To lift the hold, delete the file, or write `"gpus": []` (any `gpus_if_external` entry still applies). ⚠A broken file, or
one with neither card key, does **not** lift the hold: the supervisor keeps the last hold it read correctly (also saved in
`runners/.gpu_hold_last.json`) and says so in the log. If it has never read the file correctly, it holds nothing. ⚠It stops only
**new** launches — workers already running on a held card keep running. ⛔As of 2026-09-15 the file holds GPUs 0·1·2 (user
instruction: use only GPUs 3·4). Keep it until the user says otherwise.

**Safety lines**: nothing new is started (what is already running keeps running) if any of these holds:
① free RAM is below `SIONNA2_RAM_FLOOR_GB` (default **4** GiB; it was 6 until 2026-09-02). Free RAM = cgroup `memory.max` −
(`memory.current` − droppable page cache `file − shmem − file_mapped`, counted this way since 2026-09-15). If `memory.max` reads
`max`, `SIONNA2_RAM_GB` is used as the ceiling instead. ⚠If it cannot be read, free RAM counts as 0, so nothing starts
② our cgroup's CPU utilisation is above `0.85` (a code constant; if it cannot be measured it counts as 1.0, so nothing starts)
③ the total number of live workers (orphans included) is at or above `SIONNA2_HARD_TOTAL`.
For ①–③ the log line shows the reason after «⛔대기:» [waiting]. Separately, a card whose memory is ≥ 90 % full gets a target of 0; it
shows only as `상한0` in the status line, with no reason and no marker.

---

## 4. Watching

```bash
# Current state in one line
tail -1 runners/logs/sup_mine.log

# As it flows
tail -f runners/logs/sup_mine.log

# Progress printed by workers
tail -f runners/logs/sup_mine.log.workerout
# Worker errors
tail -f runners/logs/sup_mine.log.workererr

# Hand-off state — what a watcher decided (started the next queue, gave up, or is still waiting) is written only here
tail -n 3 runners/logs/watch_*.log
tail -n 3 runners/logs/queue_keeper_*.log
```

⚠If the previous queue ends without launching every line, `watch_0939_after_0940.py` does **not** start the next queue. It writes
the command to start it by hand into `watch_0939.log`. `watch_then_start.py` writes that command only when started with
`--idle-fallback-min 0`. With the default (20), it starts the next queue itself once no supervisor or worker has run for 20 min,
and logs that as «idle fallback».

⚠The clocks differ between files. The supervisor log and the keeper log are **KST**. `watch_*.log` and the `# …` header lines of
`orphans_handoff.txt` are container time (**UTC**), 9 h behind.

A log line looks like this (the timestamp is KST: the code adds 9 h to the container's UTC clock):

```
[09-15 21:02:24] 상태 G0:0/0(상한0·남84G·⛔보류) ... G3:3/3(상한3·남0G) G4:2/2(상한2·남21G) · 큐 20/34 · 워커 5 · RAM 16.8G · CPU 0.33
                       └ per card current/target                                          └ ⚠«launch pointer», not a completion count
```

- `·⛔보류` [held]: `runners/GPU_HOLD.json` is holding this card, so it gets `상한0` and no new workers. Cards under `"gpus"` are held
  unconditionally. Cards under `"gpus_if_external"` are held only while memory that is not ours on that card is at or above
  `"external_mb"` (default 5000). The file is re-read on every cycle. A card excluded with `SIONNA2_EXCLUDE_GPUS` also shows `상한0`, but without
  the marker.
- `· 실패 N` [failed]: appears once any worker **this supervisor launched** exits with rc≠0.
- `· ⛔대기: …` [waiting]: the reason no new worker is launched on this cycle. Free RAM is below the floor, CPU use is above the cap,
  or the total worker count on the machine has reached `SIONNA2_HARD_TOTAL`.
- ⚠`워커 N` [workers] and each card's «current» count include **every process on the machine** whose command line contains
  `benchmark/elevation_sweep_md.py` and whose `CUDA_VISIBLE_DEVICES` is a single card number. That includes orphans and the
  workers of other supervisors. When two supervisors run at once, both logs show the same numbers. These are not your queue's count.

### ⛔Read progress in «shards» — this is the most confusing part

- `큐 25/48` is **how many jobs the supervisor has taken out** (the launch pointer). It is **not** a completion count.
- If one job runs two elevations with `--els=a,b`, **2 files** come out.
  So a 48-job queue totals **96** shards.
- `outputs/elev_sweep_shards/` **is full of output from old runs** (about 7,800 files on 2026-09-15).

⚠**More than one supervisor can be alive**: a draining one next to the queue that follows it (on 2026-09-15, 0934 · 0935 · 0937
overlapped). List them with their job files first:

```bash
# ⛔Do not use pgrep -f. python executable + script as first argument only
ps -eo pid,etimes,args= | awk '$3 ~ /\/python[0-9.]*$/ && $4 ~ /worker_supervisor\.py$/ {print $1, $2"s", $5}'
```

Shards finished by **this** supervisor's workers: each worker prints `✅ … el… sh…` after it saves a shard, and all workers of one
supervisor write to its `.workerout`:

```bash
grep -c '✅' runners/logs/sup_mine.log.workerout
```

⚠`.workerout` is opened for append and never truncated. A supervisor restarted with the same log name adds to the old count.

If you use mtime instead, pick the supervisor by job file (not `head -1`). The count then includes shards from **every** queue whose
workers were running after T0:

```bash
E=$(ps -eo etimes,args= | awk '$2 ~ /\/python[0-9.]*$/ && $3 ~ /worker_supervisor\.py$/ && $4 ~ /jobs_mine\.txt$/ {print $1}' | sort -n | tail -1)   # oldest supervisor on this job file
[ -n "$E" ] || echo "no supervisor for jobs_mine.txt"
T0=$(( $(date +%s) - E ))
echo "shards written since my supervisor started (all queues): $(find outputs/elev_sweep_shards -name '*.npz' -newermt "@$T0" | wc -l)"
```

⚠Using a **human-readable time** like `find -newermt '2026-08-25 16:40'` is a trap —
the container clock is UTC while your head is in KST, so it is off by 9 hours. Use `@epoch` as above, or
make a reference file with `touch -d` and use `-newer`.

### Health check (zombies · orphans)

```bash
# ⛔pgrep -f forbidden (see above). Count with ps + [brackets].
echo "supervisors $(ps -eo args= | grep -c '[w]orker_supervisor.py') · workers $(ps -eo args= | grep -c '[e]levation_sweep_md.py') · zombies $(ps -eo stat= | grep -c '^Z')"
# Whether every worker's parent is a supervisor (orphan check)
for p in $(ps -eo pid,args= | grep '[e]levation_sweep_md.py' | awk '{print $1}'); do
  echo "  $p ← ppid $(ps -o ppid= -p $p | tr -d ' ')"
done
```

⚠**Even counting alone gets it wrong.** Counting methods that look at command-line strings (`pgrep -f` · `ps | grep`)
also count **other processes** whose command line contains the name. `[대괄호]` [brackets] keep out only a command line where the
name appears in bracketed form. If your own shell's command text also holds the name without brackets, that shell and every
subshell it forks for a pipeline are counted.
The keeper's launch check `grep -F "runners/worker_supervisor.py $1"` (`queue_keeper_0827.sh:42`, run 30 s after each launch) is
also matched by `[w]orker_supervisor.py`. Its every-30 s check (`:44`, no `.py`) is not.
On 2026-09-10, 1 supervisor was counted as 3 and 10 workers as 12. The code and logs do not show which processes were caught.

⭐**A counting method that does not wobble** — count only processes whose executable is python and whose first argument is that script:

```bash
sup() { ps -eo pid,args= | awk '$2 ~ /\/python[0-9.]*$/ && $3 ~ /worker_supervisor\.py$/ {n++} END{print n+0}'; }
wrk() { ps -eo pid,args= | awk '$2 ~ /\/python[0-9.]*$/ && $3 ~ /elevation_sweep_md\.py$/ && !/ --dry-run( |$)/ {n++} END{print n+0}'; }   # dry-runs from filter_jobs.sh are not workers
echo "supervisors $(sup) · workers $(wrk) · zombies $(ps -eo stat= | grep -c '^Z')"
```

---

## 5. Stopping — ⛔this is the most dangerous part

⛔**Before stopping, check what starts the next queue.** Stopping a supervisor does not stop the chain:

```bash
ps -eo pid,args= | awk '$3 ~ /(watch_[^ ]*\.(py|sh)|chain_[^ ]*\.sh|queue_keeper_[^ ]*\.sh)$/ {$2=""; print}'   # pid + script + its arguments (--prev-log / --next-jobs tell you which queue it follows)
```

- A watcher without idle fallback (`watch_0939_after_0940.py`, or `watch_then_start.py --idle-fallback-min 0`) exits without
  starting its next queue once the watched supervisor ends before K = N; the start command is left in its watch log.
- ⚠A 1st signal does not cancel a hand-off that is already due. If the latest status line already shows K = N, or the signal lands
  mid-round and that round launches the last lines, the watcher still starts the next queue, because it checks K = N before it
  checks whether the supervisor ended. Otherwise the supervisor writes no further status line and K = N is never reached.
- A watcher that has an idle fallback still starts its queue once no `worker_supervisor.py` and no `elevation_sweep_md.py` process
  of any queue has existed for `--idle-fallback-min` minutes in a row. It does not fire while another queue is running.
- A running keeper starts the next chain line as soon as no supervisor is found.

```bash
# ⛔pgrep -f forbidden. ⚠Several supervisors can be alive — pick yours by job file, never `head -1`
ps -eo pid,etimes,args= | awk '$3 ~ /\/python[0-9.]*$/ && $4 ~ /worker_supervisor\.py$/ {print $1, $2"s", $5}'
SUP=$(ps -eo pid,args= | awk '$2 ~ /\/python[0-9.]*$/ && $3 ~ /worker_supervisor\.py$/ && $4 ~ /jobs_mine\.txt$/ {print $1}')
echo "$SUP"              # must be exactly one pid
kill -TERM $SUP          # ⭐once only
```

| Signal (SIGTERM or SIGINT — same handling) | What happens |
|---|---|
| **1st** | Stops launching (a round already running when the signal lands still finishes, may launch workers and writes one last `상태` line), then **waits for the workers this supervisor launched** to finish. This is the normal shutdown. ⚠It does not wait for orphans or for workers of other supervisors — if none of its own are running, it exits within about 30 s while those other workers keep running |
| **2nd** | ⛔**Abandons the drain and exits. Workers keep running → they become orphans.** Only in a real emergency |

⚠The supervisor writes `신호 15 받음` [signal received] at once, but acts on it only after its current round and 30-s wait end.
**Before doing anything else, wait for** `종료 중 — 워커 N 개가 끝나기를 기다린다` [waiting for N workers] or `== 종료 … ==` [exit].
A 2nd signal sent before that line skips the drain completely (2026-09-03: signals at +8 s and +20 s after the first → 12 workers
orphaned in the same second as `종료 중`).
After the 1st signal, at most one more `상태` [status] line appears (when the signal lands mid-round). After that the log shows only drain
lines: `종료 중 — 워커 N 개가 끝나기를 기다린다` [waiting for N workers], then `끝 pid=…` [finished] per worker (followed by `실패한 줄: …`
[failed line] when rc≠0). It ends with `== 종료 … ==`.

If sent twice, the supervisor leaves the pid↔job mapping in `runners/logs/orphans_handoff.txt`.
That file lets you trace and clean up later, but **the right thing is never to send it twice in the first place.**

A worker with 2 elevations runs for **hours**. It is normal for a normal shutdown to take a long time.

⛔**Do not `kill` workers directly.** It is a repository rule (the 0811 incident). Killing one midway means the shard
is not written, and the next run sees «absent» and starts over from the beginning.

---

## 6. When you want to add more jobs

⛔**The job file is read only once, when the supervisor starts.** Lines added to the file while it is running
**are not read.** Two ways:

⭐**A. Leave the running queue alone.** Put the new lines in a **new** job file and check it with `runners/filter_jobs.sh`
(usage in its header). Then either
- chain it with `runners/watch_then_start.py` (section 1, ordering flow ④). The watcher looks only at the part of `--prev-log`
  after the last start header («큐 N 줄 · 규약»). When the latest status line there shows `큐 N/N`, it starts the next supervisor.
  It will not start twice: it keeps a lock file `runners/logs/.watch_<name>.started` and exits if a supervisor for `--next-jobs`
  is already running. Everything it does goes to `runners/logs/watch_<name>.log`; or
- start the new supervisor right away (section 3). A supervisor counts **every** `elevation_sweep_md.py` process on each card,
  not only its own, so supervisors on different job files share the per-card caps.

**B. Stop once and restart the same file.** Pick the supervisor **by its job file**, because several supervisors may be running:
```bash
SUP=$(ps -eo pid,args= | awk '$2 ~ /\/python[0-9.]*$/ && $3 ~ /worker_supervisor\.py$/ && $4 ~ /jobs_mine\.txt$/ {print $1}')   # ⛔pgrep -f forbidden
kill -TERM $SUP                      # 1) once only. Wait until the workers finish
# ... after waiting for every worker to finish ...
vi runners/jobs_mine.txt             # 2) add lines
setsid nohup $PY runners/worker_supervisor.py runners/jobs_mine.txt \
  runners/logs/sup_mine.log > runners/logs/sup_mine.nohup 2>&1 < /dev/null &   # 3) start it again, with the same log path
```
⚠**Check for a watcher on this queue first** (`ps -eo pid,args= | grep '[w]atch_'`). Stopping the queue changes what the watcher does:
- `watch_then_start.py --idle-fallback-min 0` and `watch_0939_after_0940.py` **exit without starting the next queue** if they see
  that the watched supervisor has ended before `큐 N/N` and no supervisor for that job file is running. The exit note is in the
  watch log. Start the watcher again after the restart.
- With `--idle-fallback-min 20`, the watcher starts the **next** queue once no supervisor and no worker (of any queue) has existed
  for 20 minutes in a row. That can happen while you are still editing.

Restart with the **same log path**. The watcher reads only the part after the last start header, so it follows the new run.

**Finished jobs are not redone — but only when the shard name is exactly the same.** Without `--overwrite`, a worker skips a shard
that exists **and reads back intact** (`shard_done` in elevation_sweep_md.py). A file that cannot be read in full, or fails its
idx/E/meta checks, is baked again.
⛔**The name carries the solver build.** Since 2026-09-14 the installed stack is sionna-rt 2.1.0, so every new shard name contains
`_rt210`. Lines that finished under 2.0.1 (untagged names) are **not** skipped. Restart them and they are bought again under the new name.
⛔A line with `--overwrite` is computed again **every time** the file is restarted.
⇒ Before restarting, delete the lines you do not want to buy again, including `--overwrite` lines that have already run.
⚠`runners/filter_jobs.sh` does not find these for you: a line finished under 2.0.1 comes out as NEW, because the `_rt210` name is
absent. It also does not flag `--overwrite`.

---

## 7. Merging results

Shards are scattered. The script's merge rebuilds **every arm on disk at once**:

```bash
$PY benchmark/elevation_sweep_md.py --merge   # no target — other arguments are parsed but not used
```

`--merge` has no target. It reads every `*_el*.npz` in `outputs/elev_sweep_shards/` and groups the files by arm name (the text
before the final `_el<angle>_<NN>.npz`) and elevation. It then ⚠**overwrites** the shared ledger `outputs/elevation_sweep_md.json`
and `outputs/elevation_sweep_md.npz`. The series key is `<arm>/el<±angle>`. If it finds no shards it exits without writing.
⛔Many report and deck builders read that ledger, so decide before you run it.

⛔⛔**Do not concatenate shards directly.** Shards share the poses **by skipping through them** —
each file's `idx` holds the pose numbers and `meta[3]` the total pose count. A plain `concatenate`
① breaks the time order so the rhythm disappears and ② misaligns poses between arms.
(Measured 2026-08-24: the concatenated edition gave el −30 as 2.47 %, while the canonical one was 80.5 %.)

The correct reassembly is **scattering back into place**:
```python
E = np.zeros(int(np.asarray(d["meta"], float)[3]), complex)
E[np.asarray(d["idx"]).astype(int)] = np.asarray(d["E"]).ravel()
```
⚠Scatter only the files of **one arm name** (the exact text before `_el`, so `_rt210` arms stay separate) and **one bake**. If a cell
has shards from two bakes (for example `_00/_01` with `meta[2]`=2 and `_02/_03` with `meta[2]`=4) and overlapping poses differ, the
last file scattered wins and the cell becomes a mixture. In that case `--merge` keeps only one bake, the one covering the most poses
(`one_generation`), and writes a note into the ledger row's `mixed_generations`: kept_files, dropped_files and how the bake was chosen. It is null when no
overlapping pose differs.
⚠Mark written poses separately (`seen[idx] = True`). A stored zero field is data, not a missing pose.

---

## 8. Known traps

| Trap | Symptom | Response |
|---|---|---|
| Two supervisors **on the same job file** (or on files that share lines) | The same job runs twice | Before starting, run the first check line of section 9 (the `awk … $4 ~ /jobs_mine\.txt$/` line). It must print nothing for that file (⛔`pgrep -f` forbidden). Supervisors on **different** files may overlap, because each counts every worker on each card |
| Hand-started queue written into the chain | That queue starts twice | Hand-started queues are **not written** into the chain |
| A file not yet created written into the chain | Silently skipped | **Create the file first**, then write it into the chain |
| Chain runs dry | The keeper exits by itself (「사슬 소진 — 지킴이 종료」) and the GPUs sit idle | ⚠First check that a keeper is running at all. The last one (chain `queue_chain_0910.txt`, a path fixed inside `queue_keeper_0827.sh`) ran dry and exited on 2026-09-14, and without a keeper a line written into a chain starts nothing. ⭐The hand-offs armed on 2026-09-15 are watchers, one per link (section 1). ⛔Create the next job file first, then arm its watcher: the watcher writes its lock file before it starts the supervisor, so a missing job file is never retried |
| Watcher lock left by a failed start | A new watcher with the same `--name` exits at once | Check that no supervisor holds that job file, then remove `runners/logs/.watch_<name>.started` |
| TERM twice | Orphan workers | Once only. Wait for `종료 중` or `== 종료` in the log before anything else |
| Adding to the job file | Nothing happens | ⭐Leave the running queue alone: put the lines in a **new** job file and start `runners/watch_then_start.py` with `--prev-log` set to the log of the queue it should follow — it starts the new file once that queue has launched every line. Stopping and restarting (section 6) is the other way. ⚠If a watcher follows the queue you stop, a watcher without idle fallback exits without starting its next queue (the start command is left in `runners/logs/watch_<name>.log`); one with `--idle-fallback-min` starts its next queue after that many minutes with no supervisor or worker |
| Misreading `큐 i/N` | Overestimated progress | Read it by shard count |
| Concatenating shards | Values with the rhythm gone | Scatter by `idx` |
| KST/UTC | `find -newermt` finds 0 files; watch-log times look 9 h early | Use `@epoch`; supervisor and keeper logs are KST, watch logs UTC |
| Counting by command-line string (`pgrep -f` · `ps \| grep`) | Count too high (other shells, or the keeper's `grep` subshells, hold the name) | Count with `sup()` / `wrk()` from section 4 (python executable and the script as first argument) |
| `--help` | (checked 2026-09-15) prints the argument list, rc=0, no exception | Help text is in Korean. `--merge` (section 7) and `--overwrite` (argument table in section 2) have no help line. To see which shard a line will produce, run the dry run with the GPUs hidden, as runners/filter_jobs.sh does: `CUDA_VISIBLE_DEVICES="" SIONNA2_ALLOW_CPU=1 timeout 300 $PY benchmark/elevation_sweep_md.py <line> --dry-run`. It prints 있음/없음 [present/absent] and the shard file name without computing. ⛔Never run --dry-run bare (section 2) |
| Solver build changed (installed now: sionna-rt 2.1.0 → `_rt210`) | ① An old line that already finished shows NEW in `filter_jobs.sh` and is baked again under a `_rt210` name. The untagged 2.0.1 shard stays; it is neither skipped nor overwritten. ② Or every line, `--dry-run` included, stops, so `filter_jobs.sh` shows `BAD\|⛔처음 보는 솔버 판이다 …` or `BAD\|⛔같은 꼬리표 … 다른 판 묶음 …`. It also stops with ⛔ when the sionna-rt version cannot be read, when the tag cannot be read back by `src/arm_grammar.py`, or when the build registry cannot be read | `build_tag()` adds nothing only when all four packages equal the baseline `sionna=2.0.1 sionna-rt=2.0.1 mitsuba=3.8.0 drjit=1.3.1`. Otherwise it adds `_rt<sionna-rt digits>`, and that tag must map to exactly the installed package string in `runners/SOLVER_BUILDS.json`. For a new build, add the one line the error prints. ⭐Before re-queuing old lines, run `filter_jobs.sh` and read NEW on an old line as «baked again with the current build» |
| Keeping workers off a card | Setting `SIONNA2_EXCLUDE_GPUS` later does nothing to a running supervisor (it is read once at start; a supervisor the keeper or a watcher starts only sees it if the launcher's own environment had it) | ⭐Edit `runners/GPU_HOLD.json` (`{"gpus": [0, 1, 2]}`) — section 3. ⛔It blocks **new** launches only. ⚠In force now: GPUs 3·4 only (user rule 2026-09-15, keep until the user says otherwise) |

---

## 9. One-page summary

```bash
cd /workspace/sionna; PY=/workspace/.venvs/py312/bin/python
ps -eo pid,args= | awk '$2 ~ /\/python[0-9.]*$/ && $3 ~ /worker_supervisor\.py$/ && $4 ~ /jobs_mine\.txt$/'   # must print nothing for THIS job file (supervisors on other files may run alongside) (⛔pgrep -f forbidden)
grep -vE "^\s*(#|$)" runners/jobs_mine.txt | xargs -d"\n" -P 4 -I{} runners/filter_jobs.sh {} | cut -d"|" -f1 | sort | uniq -c   # ⭐NEW·DONE·STALE·BAD before starting (⛔BAD cannot be started; ⚠the verdict looks only at the FIRST shard name the dry run prints — for a multi-elevation line that is the first elevation in --els; NEW only means that shard is not on disk yet)
setsid nohup $PY runners/worker_supervisor.py runners/jobs_mine.txt \
  runners/logs/sup_mine.log > runners/logs/sup_mine.nohup 2>&1 < /dev/null &   # start (or chain it with runners/watch_then_start.py — section 1)
tail -f runners/logs/sup_mine.log                                  # watch
tail -n 3 runners/logs/watch_*.log                                # hand-off state (UTC)
# ⚠Several supervisors can be alive at once (a watcher starts the next one before the previous one ends). Pick yours by its job file; `head -1` picks the lowest pid, which may be another queue or one already draining (a 2nd TERM → orphans)
kill -TERM $(ps -eo pid,args= | awk '$2 ~ /\/python[0-9.]*$/ && $3 ~ /worker_supervisor\.py$/ && $4 ~ /jobs_mine\.txt$/ {print $1}')   # stop THIS queue (once only)
# ⚠A watcher chained after this queue: watch_0939_after_0940.py (or watch_then_start.py --idle-fallback-min 0) does not start the next queue and writes the start command into runners/logs/watch_<name>.log; watch_then_start.py with the default --idle-fallback-min 20 starts it anyway after 20 min with no supervisor and no worker
```
