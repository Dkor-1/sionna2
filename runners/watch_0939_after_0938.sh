#!/bin/bash
# Start the 0939 leftover queue once 0938 has launched every line (queue 30/30).
# Detached with setsid+nohup so it survives a dropped session. Gives up after 24 h.
cd /workspace/sionna
export PYTHONPATH=src:benchmark
export DRJIT_LIBOPTIX_PATH=/workspace/.venvs/optix/libnvoptix.so.1
export LD_LIBRARY_PATH=/workspace/.venvs/optix:${LD_LIBRARY_PATH:-}
LOG=runners/logs/sup_antenna_0938.log
for i in $(seq 1 2880); do
  if grep -qE "큐 30/30" "$LOG" 2>/dev/null; then
    echo "[$(date '+%m-%d %H:%M:%S')] 0938 fully launched -> starting 0939"
    exec /workspace/.venvs/py312/bin/python runners/worker_supervisor.py \
         runners/jobs_0939_leftover.txt runners/logs/sup_leftover_0939.log
  fi
  sleep 30
done
echo "[$(date '+%m-%d %H:%M:%S')] gave up waiting for 0938 (24 h)"
