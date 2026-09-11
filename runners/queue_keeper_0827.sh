#!/usr/bin/env bash
# 큐 지킴이 — 감독자가 없으면 사슬의 다음 잡 파일을 띄운다. 큐가 마르지 않게 한다.
# ⛔사슬에 적힌 파일만 띄운다. 감독자가 돌고 있으면 아무것도 안 한다.
#
# ══ 2026-09-11 정정 — «띄우기 전에 done 에 적던» 것을 고쳤다 ══
#  ⛔전에는 이 차례였다:  done 에 적는다 → 띄운다 → 60 초 잔다.
#    띄우기가 한 번이라도 실패하면 되돌릴 길이 없다. 다음 바퀴에서 그 줄은 이미 «했음»
#    이라 건너뛰고 그 다음 파일로 간다 — 90 초(sleep 60 + sleep 30)마다 한 줄씩.
#    사슬이 다섯 줄이면 **7.5 분 만에 전체가 «했음»** 이 되고, 복구는 done 파일을
#    손으로 고치는 것뿐이다. 실제로 그런 적은 없지만 한 번이면 큐 전체가 죽는다.
#  ⭐지금 차례:  띄운다 → **떴는지 확인한다** → 확인됐을 때만 done 에 적는다.
#    · 떴다는 증거 두 가지 중 하나면 된다 —
#        ⓐ 그 잡 파일을 물고 있는 감독자 프로세스가 살아 있다
#        ⓑ 그 감독자의 로그 파일이 띄운 뒤에 쓰였다 (아주 빨리 끝난 경우)
#    · 못 뜨면 done 에 **안 적고** 60 초 뒤 다시 해 본다. 세 번까지.
#    · 세 번 다 실패하면 그때만 done 에 적고 다음으로 넘어간다 — 한 파일이 고장 났다고
#      지킴이가 영원히 그 자리에 서 있지 않게.
#  ⛔⛔**그래도 사슬을 다 태우게 두지 않는다.** 재시도만 넣으면 태우는 데 걸리는 시간이
#    7.5 분에서 30 분으로 늘 뿐, 계통적 고장(파이썬이 깨졌다 · 디스크가 찼다)에서는
#    결국 전부 «했음» 이 된다. ⇒ **연달아 두 파일이 세 번씩 다 실패하면 지킴이가 멈춘다.**
#    남은 사슬은 건드리지 않은 채로 남아 사람이 보면 된다. 잃는 것은 많아야 두 파일이다.
#
#  ⛔pgrep -f 를 안 쓴다(규약) — 같은 명령줄 어디든 그 이름이 있으면 내 셸이 죽는다.
#    감시견을 찾을 때도 ps 의 args 를 **통째로 견주고** 내 PID 를 뺀다.
CHAIN=/workspace/sionna/runners/queue_chain_0910.txt
LOG=/workspace/sionna/runners/logs/queue_keeper_0910.log
DONE=/workspace/sionna/runners/logs/queue_chain_0910_done.txt
cd /workspace/sionna
export PYTHONPATH=src:benchmark
export DRJIT_LIBOPTIX_PATH=/workspace/.venvs/optix/libnvoptix.so.1
export LD_LIBRARY_PATH=/workspace/.venvs/optix:${LD_LIBRARY_PATH:-}
V=/workspace/.venvs/py312/bin/python
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M:%S')] $*" >> "$LOG"; }

#: 감시견 PID — args 를 통째로 견주고 내 PID 는 뺀다(pgrep -f 안 쓴다)
guard_pids(){
  ps -eo pid=,args= | awk -v me="$$" '
    $1 != me { pid=$1; $1=""; sub(/^[ \t]+/,"");
               if ($0 == "bash runners/guard_0827.sh") print pid }'
}
#: 이 잡 파일을 물고 있는 감독자가 살아 있나
sup_for(){ ps -eo args= | grep -F "runners/worker_supervisor.py $1" | grep -q "python"; }
#: 감독자가 하나라도 도나
any_sup(){ [ "$(ps -eo args= 2>/dev/null | grep -cE '^[^ ]*python[0-9.]* +runners/worker_supervisor')" -ne 0 ]; }

touch "$DONE"
say "지킴이 시작 · 사슬 $CHAIN  (2026-09-11 판 — 뜬 것을 확인하고 done 에 적는다)"
LAST=""; TRY=0; FAILSTREAK=0
while :; do
  if ! any_sup; then
    NEXT=""
    while read -r jf; do
      [ -z "$jf" ] && continue
      case "$jf" in \#*) continue;; esac
      grep -qxF "$jf" "$DONE" && continue
      NEXT="$jf"; break
    done < "$CHAIN"
    if [ -z "$NEXT" ]; then say "사슬 소진 — 지킴이 종료"; exit 0; fi
    if [ ! -f "$NEXT" ]; then say "⛔파일 없음: $NEXT — 건너뛴다"; echo "$NEXT" >> "$DONE"; continue; fi
    #: 파일이 바뀌면 시도 횟수를 되돌린다
    [ "$NEXT" != "$LAST" ] && { LAST="$NEXT"; TRY=0; }
    LEFT=$(grep -cE '^[[:space:]]*[^#[:space:]]' "$NEXT")
    B=$(basename "$NEXT" .txt)
    SUPLOG="runners/logs/sup_${B}.log"
    T0=$(date +%s)
    TRY=$((TRY+1))
    say "▶ 다음 큐 띄움: $NEXT (실행 줄 ${LEFT}) · 시도 ${TRY}/3"
    SIONNA2_MAX_TOTAL=9 setsid nohup $V runners/worker_supervisor.py "$NEXT" \
      "$SUPLOG" >/dev/null 2>&1 &
    #: ⭐떴는지 볼 시간을 준다. 안 자고 보면 아직 파이썬이 올라오는 중이라 늘 «못 떴다» 가 된다.
    sleep 30
    OK=0
    sup_for "$NEXT" && OK=1
    #: ⓑ 아주 빨리 끝난 경우 — 로그가 띄운 뒤에 쓰였으면 뜬 것이다
    if [ "$OK" -eq 0 ] && [ -f "$SUPLOG" ]; then
      M=$(stat -c %Y "$SUPLOG" 2>/dev/null || echo 0)
      [ "$M" -ge "$T0" ] && OK=1 && say "   (감독자는 이미 끝났지만 로그가 쓰였다 — 뜬 것으로 본다)"
    fi
    if [ "$OK" -eq 1 ]; then
      echo "$NEXT" >> "$DONE"
      FAILSTREAK=0
      say "   ✅ 떴다 — done 에 적었다"
      #: 감시견을 띄우기 전에 **옛것을 죽인다**. 안 그러면 잡을 띄울 때마다 하나씩 쌓인다
      #   (2026-09-01 에 3 개까지 누적된 것을 발견). 관찰만 하므로 해는 없지만 전수조사에서
      #   «고아» 로 오독되고 로그가 여러 벌로 겹친다.
      for _g in $(guard_pids); do kill "$_g" 2>/dev/null || true; done
      setsid nohup bash runners/guard_0827.sh >/dev/null 2>&1 &
      sleep 30
    else
      say "   ⛔안 떴다 — done 에 **안 적는다**. 60 초 뒤 다시 해 본다"
      if [ "$TRY" -ge 3 ]; then
        FAILSTREAK=$((FAILSTREAK+1))
        if [ "$FAILSTREAK" -ge 2 ]; then
          say "   ⛔⛔연달아 ${FAILSTREAK} 파일이 세 번씩 다 실패했다 — **지킴이가 멈춘다.**"
          say "      남은 사슬은 그대로 둔다($DONE 에 적지 않았다). 사람이 보고 다시 띄운다:"
          say "      setsid nohup bash runners/queue_keeper_0827.sh >/dev/null 2>&1 &"
          exit 1
        fi
        say "   ⛔세 번 다 실패 — 이 파일만 done 에 적고 다음으로 넘어간다: $NEXT"
        echo "$NEXT" >> "$DONE"; TRY=0
      fi
      sleep 60
    fi
  fi
  sleep 30
done
