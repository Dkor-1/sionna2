#!/bin/bash
# One sweep job at a time on GPU 2, taken from the END of a queue file, so the supervisor on that file (which launches
# lines in order) is unlikely to reach the same line while it runs.
#
# Why: user, 2026-09-17 ~20:30 KST: «GPU 1,2번에 올린건 비우면 속도 차이가 많이 날까?? … 차이 많이나면 1개 유지»
#   [if clearing GPU 1/2 slows the queue a lot, keep one job]. Estimate at that time: ~82 slot-h left on cards 3/4
#   (6 slots, about 14 h); one extra job on a card of its own ran a street-canyon shard in ~155 min vs ~204 min on the
#   shared cards, so keeping one job ends the queue about 2-2.5 h earlier. GPU 1 is cleared; GPU 2 keeps one job.
#
# Guards, checked before every launch (the running job is never killed):
#   · stop file runners/STOP_gpu2_sequential → exit;
#   · GPU 2 must still be in runners/GPU_HOLD.json "gpus" (otherwise supervisors may use it) → exit;
#   · none of our sweep workers already on GPU 2;
#   · supervisor margin: line k is launched only if k − (lines the supervisor has launched) ≥ MARGIN → otherwise exit;
#   · runners/filter_jobs.sh must say NEW (shard not on disk);
#   · no running sweep process with the same arguments.
# Worker environment copied from runners/worker_supervisor.py launch(). No CPU affinity (the supervisor sets none).
#
# Run: setsid nohup bash runners/gpu2_sequential_0917.sh > runners/logs/gpu2_sequential_0917.nohup 2>&1 < /dev/null &
set -u
cd /workspace/sionna || exit 1
GPU=${GPU:-2}
LOG=runners/logs/gpu2_sequential_0917.log
PY=/workspace/.venvs/py312/bin/python
MARGIN=4
STOP=runners/STOP_gpu2_sequential
WAIT_PID="${WAIT_PID:-}"
# queue:k — k counts non-comment job lines from 1, longest shards first from the end of the file
CANDIDATES="0954:12 0954:11 0954:10 0954:9 0954:8 0954:7"

log() { echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M:%S')] $*" >> "$LOG"; }

if [ -n "$WAIT_PID" ]; then
  log "waiting for pid $WAIT_PID (the hand-started job already on GPU $GPU) to exit"
  while kill -0 "$WAIT_PID" 2>/dev/null; do sleep 60; done
  log "pid $WAIT_PID exited"
fi

for c in $CANDIDATES; do
  q=${c%%:*}; k=${c##*:}
  if [ -e "$STOP" ]; then log "stop file present — exit"; exit 0; fi
  if ! $PY -c "import json,sys; sys.exit(0 if $GPU in json.load(open('runners/GPU_HOLD.json')).get('gpus',[]) else 1)"; then
    log "GPU $GPU no longer held — supervisors may use it — exit"; exit 0
  fi
  f=$(ls runners/jobs_${q}_*.txt | grep -v HOLD | head -1)
  L=$(grep -vE '^\s*(#|$)' "$f" | sed -n "${k}p")
  if [ -z "$L" ]; then log "$q:$k no such line — skip"; continue; fi
  i_sup=$(grep -o '큐 [0-9]*/' "runners/logs/sup_${q}.log" | tail -1 | grep -o '[0-9]*')
  if [ -z "$i_sup" ] || [ $((k - i_sup)) -lt $MARGIN ]; then
    log "$q:$k supervisor has launched ${i_sup:-?} lines (margin $MARGIN not met) — exit"; exit 0
  fi
  busy=$($PY - "$GPU" <<'EOF'
import os, sys
gpu = sys.argv[1]; n = 0
for p in os.listdir("/proc"):
    if not p.isdigit() or int(p) == os.getpid():
        continue
    try:
        argv = open(f"/proc/{p}/cmdline", "rb").read().split(b"\0")
        if len(argv) < 2 or not argv[1].endswith(b"elevation_sweep_md.py"):
            continue
        env = open(f"/proc/{p}/environ", "rb").read().split(b"\0")
        if f"CUDA_VISIBLE_DEVICES={gpu}".encode() in env:
            n += 1
    except OSError:
        pass
print(n)
EOF
)
  if [ "$busy" != "0" ]; then log "$busy sweep worker(s) already on GPU $GPU — exit"; exit 0; fi
  st=$(runners/filter_jobs.sh "$L" | cut -d'|' -f1)
  if [ "$st" != "NEW" ]; then log "$q:$k filter says $st — skip"; continue; fi
  dup=$($PY - "$L" <<'EOF'
import os, sys
want = sys.argv[1].split(); n = 0
for p in os.listdir("/proc"):
    if not p.isdigit() or int(p) == os.getpid():
        continue
    try:
        argv = [a.decode() for a in open(f"/proc/{p}/cmdline", "rb").read().split(b"\0") if a]
        if len(argv) >= 2 and argv[1].endswith("elevation_sweep_md.py") and argv[2:] == want:
            n += 1
    except OSError:
        pass
print(n)
EOF
)
  if [ "$dup" != "0" ]; then log "$q:$k already running elsewhere — skip"; continue; fi
  if [ "${DRY:-0}" = "1" ]; then log "DRY: would launch $q:$k (supervisor at $i_sup): $L"; continue; fi
  t=2
  out=runners/logs/gpu2_sequential_0917_${q}_${k}.log
  log "launch $q:$k on GPU $GPU (supervisor at $i_sup): $L"
  t0=$(date +%s)
  CUDA_VISIBLE_DEVICES=$GPU PYTHONPATH=src:benchmark \
  DRJIT_LIBOPTIX_PATH=/workspace/.venvs/optix/libnvoptix.so.1 \
  LD_LIBRARY_PATH="/workspace/.venvs/optix:${LD_LIBRARY_PATH:-}" \
  OMP_NUM_THREADS=$t OPENBLAS_NUM_THREADS=$t MKL_NUM_THREADS=$t NUMEXPR_NUM_THREADS=$t VECLIB_MAXIMUM_THREADS=$t \
  DRJIT_NUM_THREADS=$t MI_NUM_THREADS=$t RAYON_NUM_THREADS=$t OMP_WAIT_POLICY=PASSIVE KMP_BLOCKTIME=0 \
  TOKENIZERS_PARALLELISM=false \
    $PY benchmark/elevation_sweep_md.py $L >> "$out" 2>&1 < /dev/null
  rc=$?
  log "end $q:$k rc=$rc $(( ($(date +%s) - t0) / 60 )) min"
done
log "candidates exhausted — exit"
