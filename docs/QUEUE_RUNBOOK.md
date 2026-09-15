# Running the queue by hand — terminal runbook

> ⛔⛔**Do not use `pgrep -f`.** The moment that name appears on the same command line, your own shell dies
> (exit 144 · `docs/RESUME.md:45`). On 2026-09-10 this runbook was switched entirely to `ps` + `[대괄호]` [brackets].
> ⭐The queue has **2 tiers** — above the supervisor (runs one queue) sits the keeper (starts the next queue when a queue runs dry).
> Read section 1 first.

> How to write, run and stop the supervisor (`runners/worker_supervisor.py`) and the workers (`benchmark/elevation_sweep_md.py`)
> **by hand**. Written as of 2026-08-25, against the code that is running now.

```bash
# Start with these two lines from anywhere
cd /workspace/sionna
PY=/workspace/.venvs/py312/bin/python
```

---

## 1. Structure — who does what

⭐**There are 2 tiers.** The lower box is the supervisor that «runs one queue», and the upper box is the keeper that
«starts the next queue when a queue runs dry». The 08-25 edition of this runbook had only the lower box (the keeper appeared on 08-27 — added 2026-09-10).

```
queue_chain_XXXX.txt ──► queue_keeper_XXXX.sh ─┐   (keeper: every 30 s checks «is there a supervisor»
 (list of job files      (starts the next line   │    and if not, starts the next line of the chain)
  to start next; # = comment)  only when 0 supervisors) │
                                                 ▼
jobs.txt  ──►  worker_supervisor.py  ──►  elevation_sweep_md.py  ──►  outputs/elev_sweep_shards/*.npz
 (one line =     (reads the queue alone     (the actual computation; holds       (shard files)
  one job)        and starts workers)        one GPU while running)
```

- **Only one supervisor** runs. It reads the queue alone and hands out jobs, so starting two **assigns the same job twice**.
- The supervisor **does not kill workers** (repository rule, the 0811 incident). It scales down only by «not refilling
  finished slots».
- The supervisor **reads the queue into memory at start** and advances a cursor. So if it dies it runs **from the beginning** —
  to continue, make a new file containing only the remaining lines and start that (`runners/QUEUE_STATE_0908.md`).

### Keeper — how queues continue on their own

| Item | File | What it does |
|---|---|---|
| Chain | `runners/queue_chain_XXXX.txt` | List of job files to start next. One per line, `#` is a comment |
| Keeper | `runners/queue_keeper_0827.sh` | Counts supervisors every 30 s and, **if there are 0**, starts the next line of the chain |
| Already-started list | `runners/logs/queue_chain_XXXX_done.txt` | A line started once is never looked at again |
| Keeper log | `runners/logs/queue_keeper_XXXX.log` | 「▶ 다음 큐 띄움」 [▶ next queue started] · 「사슬 소진 — 지킴이 종료」 [chain exhausted — keeper exiting] |

- ⛔It starts **only files written in the chain**. A missing file is logged as 「건너뜀」 [skipped] and never looked at again.
- ⛔**Create the file first**, then write it into the chain. Reverse the order and that line never runs.
- ⛔**Do not write** a hand-started queue into the chain — if you do, that queue starts twice.
- When the chain is empty the keeper **exits by itself**. From then on the GPUs sit idle — before it runs dry, create the next job file
  and write it into the chain.
- Supervisors started by the keeper use `SIONNA2_MAX_TOTAL=9` (hard-coded in the script). This may differ from the value
  used when starting by hand, so **trust the «상한» [cap] in the log**.

### Ordering flow — up to one job running

```
① runners/make_jobs_XXXX.py       writes the question · kill conditions · what it does not answer, and emits job lines
        │                          ⛔do not write only lines — also write «what it does not answer»
        ▼  python runners/make_jobs_XXXX.py > runners/jobs_XXXX.txt
② runners/jobs_XXXX.txt
        │
        ▼  ⭐always before ordering — runners/filter_jobs.sh
③ split into NEW · DONE · STALE    buying only NEW is the default. STALE is bought again with --overwrite
        │                          only when the question needs n_dup
        ▼
④ write that file name into runners/queue_chain_XXXX.txt   (⛔after creating the file first)
        │
        ▼
⑤ the keeper starts a supervisor → the supervisor starts workers → shards land
```

The one-liner that filters:

```bash
grep -vE "^\s*(#|$)" runners/jobs_XXXX.txt \
  | xargs -d"\n" -P 4 -I{} runners/filter_jobs.sh {} | cut -d"|" -f1 | sort | uniq -c
```

---

## 2. Writing a job file

One line is one job, and that line becomes the arguments of `elevation_sweep_md.py` as is.
Lines starting with `#` and blank lines are skipped.

```bash
cat > runners/jobs_mine.txt <<'EOF'
# My queue — 2026-08-25
--engine sionna --spp 4000000000 --sw R0D1E1F1 --max-depth 2 --drone mini5pro \
  --range-m 15 --n-poses 8192 --els=0,-30 --shard 0 --nshards 2 --inmem
--engine sionna --spp 4000000000 --sw R0D1E1F1 --max-depth 2 --drone mini5pro \
  --range-m 15 --n-poses 8192 --els=0,-30 --shard 1 --nshards 2 --inmem
EOF
```

⚠**One job must be exactly one line.** The `\` line breaks in the example above only continue inside a shell heredoc; the supervisor
reads the file **line by line**. To be safe, just write one long line.

### Frequently used arguments

| Argument | Meaning |
|---|---|
| `--sw R?D?E?F?` | Physics switches. **R**=refraction **D**=diffraction **E**=edge diffraction **F**=diffuse. `R0D1E1F1` = only refraction off |
| `--els=0,-30` | Elevation list. **One job runs every elevation written here** → it produces that many files |
| `--shard k --nshards n` | Split the poses into n parts and take only the k-th. Parts are shared **by skipping through the poses** |
| `--n-poses 8192` | Number of poses |
| `--range-m 15` · `--drone mini5pro` | Range · airframe |
| `--spp 4000000000` | Number of rays |
| `--max-depth 2` | Reflection depth. ⛔In combinations with diffraction on, 3 must not be dropped (R13) |
| `--inmem` | In memory, without intermediate files. The mode the current queue uses |
| `--overwrite` | Compute **again** even shards that already exist |
| `--dry-run` | Print only «present/absent», without computing |

### ⭐Always before running — see what already exists

Workers **skip shards that already exist** (without `--overwrite`). So even if the queue is rewritten,
finished work is not redone. To check in advance:

```bash
while read -r line; do
  [ -z "$line" ] && continue; case "$line" in \#*) continue;; esac
  $PY benchmark/elevation_sweep_md.py $line --dry-run
done < runners/jobs_mine.txt
```

---

## 3. Starting

```bash
setsid nohup $PY runners/worker_supervisor.py \
  runners/jobs_mine.txt \
  /workspace/sionna/runners/logs/sup_mine.log \
  >/dev/null 2>&1 &
echo "supervisor pid $!"
```

- `setsid` is the key — it keeps running even if the terminal or SSH disconnects.
- If the log path is omitted, it goes to `runners/logs/supervisor.log`.

### Resource discipline — tighten with environment variables

The defaults are already conservative for this container, but **if you want to tighten further**, prefix these:

```bash
SIONNA2_CPUS=8 SIONNA2_RAM_GB=24 SIONNA2_MAX_TOTAL=4 SIONNA2_HARD_TOTAL=6 \
SIONNA2_THREADS=2 \
setsid nohup $PY runners/worker_supervisor.py runners/jobs_mine.txt \
  runners/logs/sup_mine.log >/dev/null 2>&1 &
```

| Variable | Default | Meaning |
|---|---|---|
| `SIONNA2_MAX_TOTAL` | 8 | **Budget** cap for the target allocation (not a hard launch cut-off) ⚠The keeper starts with **9** (`queue_keeper_0827.sh`). A hand-started run may differ, so **trust the «상한» [cap] in the supervisor log** |
| `SIONNA2_HARD_TOTAL` | 12 | **Absolute line**. Nothing is started beyond it |
| `SIONNA2_THREADS` | 2 | Threads per worker. ⛔Do not raise it — the cause of thread runaways |
| `SIONNA2_CPUS` | auto | Number of CPU cores in our share. Denominator of the CPU brake |
| `SIONNA2_RAM_GB` | auto | RAM in our share. The container ceiling is 32 GiB |
| `SIONNA2_EXCLUDE_GPUS` | none | Like `"0,3"`. Cards never to use |

**Safety lines** (code constants, not environment variables): if free RAM is below `6 GB` or our CPU utilisation
exceeds `0.85`, **nothing new is started** (what is already running keeps running).

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
```

A log line looks like this:

```
[08-25 13:40] 상태 G0:2/2(상한3·남0G) ... · 큐 25/48 · 워커 4 · RAM 16.9G · CPU 0.88 · ⛔대기: ...
                    └ per card current/target └ ⚠«launch pointer», not a completion count
```

### ⛔Read progress in «shards» — this is the most confusing part

- `큐 25/48` is **how many jobs the supervisor has taken out** (the launch pointer). It is **not** a completion count.
- If one job runs two elevations with `--els=a,b`, **2 files** come out.
  So a 48-job queue totals **96** shards.
- `outputs/elev_sweep_shards/` **is full of output from old runs** (over 4,300 files now).
  To count only your queue's share, filter by **mtime after the supervisor start time**:

```bash
# ⛔Do not use pgrep -f — the moment that name is on the same command line, **your own shell dies** (exit 144).
#   Pick it out with ps and split the name with [brackets] so it does not catch itself.
SUP=$(ps -eo pid,args= | grep '[w]orker_supervisor.py' | awk '{print $1}' | head -1)
T0=$(( $(date +%s) - $(ps -o etimes= -p $SUP | tr -d ' ') ))
echo "shards produced by my queue: $(find outputs/elev_sweep_shards -name '*.npz' -newermt "@$T0" | wc -l)"
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
also count **other shells** that contain the name. `[대괄호]` [brackets] exclude your own shell, but if a subshell the keeper spawns every 30 s
(`grep -cE '…runners/worker_supervisor'` inside `queue_keeper_0827.sh`) is caught in the sample,
the count comes out one too high — on 2026-09-10, 1 supervisor was counted as 3 and 10 workers as 12.

⭐**A counting method that does not wobble** — count only processes whose executable is python and whose first argument is that script:

```bash
sup() { ps -eo pid,args= | awk '$2 ~ /\/python[0-9.]*$/ && $3 ~ /worker_supervisor\.py$/ {n++} END{print n+0}'; }
wrk() { ps -eo pid,args= | awk '$2 ~ /\/python[0-9.]*$/ && $3 ~ /elevation_sweep_md\.py$/ {n++} END{print n+0}'; }
echo "supervisors $(sup) · workers $(wrk) · zombies $(ps -eo stat= | grep -c '^Z')"
```

---

## 5. Stopping — ⛔this is the most dangerous part

```bash
SUP=$(ps -eo pid,args= | grep '[w]orker_supervisor.py' | awk '{print $1}' | head -1)   # ⛔pgrep -f forbidden
kill -TERM $SUP          # ⭐once only
```

| Signal | What happens |
|---|---|
| **1st** | Starts nothing new and **waits for running workers to finish.** This is the normal shutdown |
| **2nd** | ⛔**Abandons the drain and exits. Workers keep running → they become orphans.** Only in a real emergency |

If sent twice, the supervisor leaves the pid↔job mapping in `runners/logs/orphans_handoff.txt`.
That file lets you trace and clean up later, but **the right thing is never to send it twice in the first place.**

A worker with 2 elevations runs for **hours**. It is normal for a normal shutdown to take a long time.

⛔**Do not `kill` workers directly.** It is a repository rule (the 0811 incident). Killing one midway means the shard
is not written, and the next run sees «absent» and starts over from the beginning.

---

## 6. When you want to add more jobs

⛔**The job file is read only once, when the supervisor starts.** Lines added to the file while it is running
**are not read.** There is one way:

```bash
kill -TERM $SUP                      # 1) once only. Wait until the workers finish
# ... after waiting for every worker to finish ...
vi runners/jobs_mine.txt             # 2) add lines
setsid nohup $PY runners/worker_supervisor.py runners/jobs_mine.txt \
  runners/logs/sup_mine.log >/dev/null 2>&1 &   # 3) start it again
```

**Finished jobs are not redone** — workers see that the shard exists and skip it. So there is no need to delete old lines;
**leave them and just append new lines**.

---

## 7. Merging results

Shards are scattered. To merge them into one:

```bash
$PY benchmark/elevation_sweep_md.py --merge ...   # arguments the same as the target being merged
```

⛔⛔**Do not concatenate shards directly.** Shards share the poses **by skipping through them** —
each file's `idx` holds the pose numbers and `meta[3]` the total pose count. A plain `concatenate`
① breaks the time order so the rhythm disappears and ② misaligns poses between arms.
(Measured 2026-08-24: the concatenated edition gave el −30 as 2.47 %, while the canonical one was 80.5 %.)

The correct reassembly is **scattering back into place**:
```python
E = np.zeros(int(np.asarray(d["meta"], float)[3]), complex)
E[np.asarray(d["idx"]).astype(int)] = np.asarray(d["E"]).ravel()
```

---

## 8. Known traps

| Trap | Symptom | Response |
|---|---|---|
| Two supervisors | The same job runs twice | Before starting, confirm 0 with `sup()` above (⛔`pgrep -f` forbidden) |
| Hand-started queue written into the chain | That queue starts twice | Hand-started queues are **not written** into the chain |
| A file not yet created written into the chain | Silently skipped | **Create the file first**, then write it into the chain |
| Chain runs dry | The keeper exits by itself and the GPUs sit idle | Before it runs dry, create the next job file and write it into the chain |
| TERM twice | Orphan workers | Once only. Wait even if it takes long |
| Adding to the job file | Nothing happens | It is read only after a restart |
| Misreading `큐 i/N` | Overestimated progress | Read it by shard count |
| Concatenating shards | Values with the rhythm gone | Scatter by `idx` |
| KST/UTC | `find -newermt` finds 0 files | Use `@epoch` |
| `pgrep` self-match | Count one too high | Check with `ps -o args=` |
| `--help` crashes | argparse exception | Known bug. Look up arguments in this document or the source |

---

## 9. One-page summary

```bash
cd /workspace/sionna; PY=/workspace/.venvs/py312/bin/python
ps -eo args= | grep -c '[w]orker_supervisor.py'                     # must be 0 to start (⛔pgrep -f forbidden)
setsid nohup $PY runners/worker_supervisor.py runners/jobs_mine.txt \
  runners/logs/sup_mine.log >/dev/null 2>&1 &                      # start
tail -f runners/logs/sup_mine.log                                  # watch
kill -TERM $(ps -eo pid,args= | grep '[w]orker_supervisor.py' | awk '{print $1}' | head -1)   # stop (once only)
```
