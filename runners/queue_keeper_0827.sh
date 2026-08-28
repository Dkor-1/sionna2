#!/usr/bin/env bash
# 큐 지킴이 — 감독자가 없으면 사슬의 다음 잡 파일을 띄운다. 큐가 마르지 않게 한다.
# ⛔사슬에 적힌 파일만 띄운다. 감독자가 돌고 있으면 아무것도 안 한다.
CHAIN=/workspace/sionna/runners/queue_chain_0828.txt
LOG=/workspace/sionna/runners/logs/queue_keeper_0827.log
DONE=/workspace/sionna/runners/logs/queue_chain_0828_done.txt
cd /workspace/sionna
export PYTHONPATH=src:benchmark
export DRJIT_LIBOPTIX_PATH=/workspace/.venvs/optix/libnvoptix.so.1
export LD_LIBRARY_PATH=/workspace/.venvs/optix:${LD_LIBRARY_PATH:-}
V=/workspace/.venvs/py312/bin/python
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M:%S')] $*" >> "$LOG"; }
touch "$DONE"
say "지킴이 시작 · 사슬 $CHAIN"
while :; do
  SUP=$(ps -eo args= 2>/dev/null | grep -cE '^[^ ]*python[0-9.]* +runners/worker_supervisor')
  if [ "$SUP" -eq 0 ]; then
    NEXT=""
    while read -r jf; do
      [ -z "$jf" ] && continue
      case "$jf" in \#*) continue;; esac
      grep -qxF "$jf" "$DONE" && continue
      NEXT="$jf"; break
    done < "$CHAIN"
    if [ -z "$NEXT" ]; then say "사슬 소진 — 지킴이 종료"; exit 0; fi
    if [ ! -f "$NEXT" ]; then say "⛔파일 없음: $NEXT — 건너뛴다"; echo "$NEXT" >> "$DONE"; continue; fi
    LEFT=$(wc -l < "$NEXT")
    say "▶ 다음 큐 띄움: $NEXT (${LEFT}줄)"
    echo "$NEXT" >> "$DONE"
    B=$(basename "$NEXT" .txt)
    SIONNA2_MAX_TOTAL=9 setsid nohup $V runners/worker_supervisor.py "$NEXT" \
      "runners/logs/sup_${B}.log" >/dev/null 2>&1 &
    sleep 60
    setsid nohup bash runners/guard_0827.sh >/dev/null 2>&1 &
  fi
  sleep 120
done
