#!/usr/bin/env bash
# 감시견 v2 — ①좀비·고아 ②호스트 부하 대비 우리 몫. 관찰·기록만 한다.
LOG=/workspace/sionna/runners/logs/guard_0827.log
CORES=$(nproc --all)
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M:%S')] $*" >> "$LOG"; }
say "감시견 v2 시작 · 호스트 코어 $CORES"
while :; do
  SUP=$(ps -eo pid=,args= 2>/dev/null | grep -E 'python[0-9.]* +runners/worker_supervisor' | awk '{print $1}' | head -1)
  W=$(ps -eo args= 2>/dev/null | grep -c 'benchmark/elevation_sweep_md\.py')
  Z=$(ps -eo stat= 2>/dev/null | grep -c '^Z')
  LOAD=$(awk '{print $1}' /proc/loadavg)
  IDLE=$(top -bn1 2>/dev/null | grep -m1 '%Cpu' | sed -E 's/.*, *([0-9.]+) id.*/\1/')
  OUR=$(python3 -c "
import time
def u():
    for l in open('/sys/fs/cgroup/cpu.stat'):
        if l.startswith('usage_usec'): return int(l.split()[1])
a=u(); t=time.time(); time.sleep(2); b=u()
print(f'{(b-a)/1e6/(time.time()-t):.1f}')" 2>/dev/null)
  GO=$(nvidia-smi --query-compute-apps=used_memory --format=csv,noheader,nounits 2>/dev/null | awk '{s+=$1} END{printf "%.1f", s/1024}')
  GA=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | awk '{s+=$1} END{printf "%.1f", s/1024}')
  if [ -z "$SUP" ]; then
    if [ "$W" -gt 0 ]; then say "⛔⛔ 감독자 사라짐 · 워커 ${W}개 → 고아"
    else say "✅ 큐 종료 — 감시견 끝"; exit 0; fi
  else
    ORPH=$(ps -eo ppid=,args= 2>/dev/null | grep 'benchmark/elevation_sweep_md\.py' | grep -v grep | awk -v s="$SUP" '$1!=s' | wc -l)
    M="감독자 $SUP · 워커 $W · 좀비 $Z · 고아 $ORPH | 호스트 load $LOAD/$CORES · idle ${IDLE}% · 우리 ${OUR}코어 | GPU 우리 ${GO}G/전체 ${GA}G"
    if [ "$ORPH" -gt 0 ] || [ "$Z" -gt 0 ]; then say "⛔ 이상 — $M"
    elif [ -n "$IDLE" ] && awk "BEGIN{exit !($IDLE < 20)}"; then say "⚠호스트 혼잡 — $M"
    else say "정상 · $M"; fi
  fi
  sleep 58
done
