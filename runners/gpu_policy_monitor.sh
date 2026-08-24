#!/usr/bin/env bash
# ⭐GPU 워커 규약 감시기 v3 (2026-08-16)
#
# ⭐판정의 눈금은 «카드 전체 util» 이 아니라 **남의 몫 SM%** 다.
#   ⚠남의 컨테이너 프로세스는 pmon/compute-apps 에 안 보인다(PID 네임스페이스, 실측).
#   그래서 직접 못 재고 **추정**한다: 외부SM ≈ max(0, 카드 util − 우리 pid 들의 SM 합).
#   우리 몫은 pmon 으로 정확히 보이므로, 우리 워커가 채운 몫 때문에 우리 워커를 빼는
#   자가당착(사용자 지적)은 이 추정에서도 안 생긴다.
#
# 기본 목표(외부 메모리): <2GB→3 · <10GB→2 · <30GB→1 · ≥30GB→0
# 종합:
#   · 외부SM 15분 평균 < 90 → +1 (상한 3) — 남의 작업이 연산을 다 안 쓰면 우리가 채운다
#   · 외부SM 평균 ≥ 50 이고 목표 > 1 → 한 단계 양보(남이 실계산 중)
#   · 온도 ≥ 80°C → 한 단계 내림
# ⛔줄일 때는 슬롯 루프만(계산 중 파이썬 보존). nohup 상주, 세션 무관.
SP=/tmp/claude-0/-workspace/e9e31991-b542-4f3a-b8e2-570320d555ba/scratchpad
Q=$SP/el15run_more/jobs.txt
LOG=$SP/gpu_policy.log
SLOT=$SP/add_slot_gen.sh
HIST=$SP/gpu_fsm_hist
mkdir -p "$HIST"
cd /workspace/sionna || exit 1

#: ⭐2026-08-18 사용자 확정 — **외부 메모리가 카드 절반 미만이면 무조건 1 개는 잡는다.**
#   카드 총량 97,887 MiB 의 50 % = 48,943. 다른 조건(외부SM·온도·표본수)을 안 본다.
#   «남이 반도 안 쓰고 있으면 우리도 한 자리는 쓴다» 는 규약이다.
MEM_HALF=48943

target_of() {
  if   [ "$1" -lt 2048 ];  then echo 3
  elif [ "$1" -lt 10240 ]; then echo 2
  elif [ "$1" -lt 30720 ]; then echo 1
  else echo 0; fi
}

while true; do
  qn=$(wc -l < "$Q" 2>/dev/null || echo 0)
  rn=$(ps -eo args --no-headers | grep -cE "elevation_sweep_md.py --engine|run_bridge_window.py")
  if [ "$qn" -eq 0 ] && [ "$rn" -eq 0 ]; then
    echo "[$(date +%H:%M:%S)] 큐·워커 소진 — 감시기 종료" >> "$LOG"; break
  fi
  declare -A OURSMEM=(); declare -A FSM=(); declare -A IDX=()
  while IFS=, read -r i u; do IDX[${u// /}]=${i// /}; done < <(
    nvidia-smi --query-gpu=index,uuid --format=csv,noheader)
  MYPIDS=" $(pgrep -f 'elevation_sweep_md.py --engine|run_bridge_window.py' | tr '\n' ' ') "
  while IFS=, read -r u p m; do
    u=${u// /}; p=${p// /}; m=${m%% MiB*}; m=${m// /}
    case "$MYPIDS" in *" $p "*) g=${IDX[$u]}; OURSMEM[$g]=$(( ${OURSMEM[$g]:-0} + m ));; esac
  done < <(nvidia-smi --query-compute-apps=gpu_uuid,pid,used_memory --format=csv,noheader)
  # ⭐우리 몫 SM — pmon 에 보이는 우리 pid 들의 sm 합(카드별)
  declare -A OURSM=()
  while read -r g p sm; do
    case "$g" in ''|\#*) continue;; esac
    [ "$sm" = "-" ] && sm=0
    case "$MYPIDS" in *" $p "*) OURSM[$g]=$(( ${OURSM[$g]:-0} + sm ));; esac
  done < <(nvidia-smi pmon -c 1 -s u 2>/dev/null | awk 'NR>2 {print $1, $2, $4}')

  while IFS=, read -r g used util temp; do
    g=${g// /}; used=${used%% MiB*}; used=${used// /}
    util=${util%% %*}; util=${util// /}; temp=${temp// /}
    foreign=$(( used - ${OURSMEM[$g]:-0} )); [ "$foreign" -lt 0 ] && foreign=0
    fsm=$(( util - ${OURSM[$g]:-0} ))
    [ "$fsm" -lt 0 ] && fsm=0; [ "$fsm" -gt 100 ] && fsm=100
    echo "$fsm" >> "$HIST/g$g"; tail -5 "$HIST/g$g" > "$HIST/g$g.t" && mv "$HIST/g$g.t" "$HIST/g$g"
    avg=$(awk '{s+=$1; n++} END {print (n? int(s/n) : 0)}' "$HIST/g$g")
    nsamp=$(wc -l < "$HIST/g$g")

    want=$(target_of "$foreign")
    note=""
    # ⭐⭐메모리 우선 오버라이드(사용자 확정 2026-08-15): **배치(메모리) 여유가 매우 크면
    #   다른 조건(외부SM·온도)을 보지 않고 그대로 올린다.** 외부 <10,000 MiB(총의 ~10 %)를
    #   «매우 큰 여유» 로 정의 — 이때 want 는 메모리 티어값 그대로(감산 없음).
    if [ "$foreign" -lt 10000 ]; then
      note=" (메모리 여유 — 조건 무시 승급)"
    else
      # ⭐승급(사용자 확정 2026-08-16): **메모리 기준 0 인 카드에 한해, 딱 1 개만.**
      #   외부SM 15분 평균 < 90 인 동안 1 개를 유지한다(mine 상태와 무관 → 진동 없음).
      #   이미 우리 워커가 있는(메모리 기준 ≥1) 카드에는 승급으로 더 쌓지 않는다.
      #   ⛔예외(사용자 추가): 외부 메모리 ≥ **80,000 MiB**(총 97,887 의 82 %)인 카드는 SM 이
      #     낮아도 승급하지 않는다 — 사용자 확정 문턱.
      if [ "$want" -eq 0 ] && [ "$foreign" -lt 80000 ] \
          && [ "$nsamp" -ge 5 ] && [ "$avg" -lt 90 ]; then
        want=1; note=" (빈 카드 승급 — 외부SM평균 ${avg}%)"
      fi
      if [ "$avg" -ge 50 ] && [ "$want" -gt 1 ]; then
        want=$(( want - 1 )); note="$note (외부 실계산 양보)"
      fi
      [ "$temp" -ge 80 ] && [ "$want" -gt 0 ] && { want=$(( want - 1 )); note="$note (온도 ${temp}°)"; }
    fi
    # ⭐하한(2026-08-18): 외부가 카드 절반도 안 쓰면 최소 1 개는 확보한다.
    #   온도·외부SM 감산이 0 으로 끌어내렸어도 여기서 다시 1 로 올린다.
    if [ "$foreign" -lt "$MEM_HALF" ] && [ "$want" -lt 1 ]; then
      want=1; note="$note (⭐외부 메모리 50% 미만 — 최소 1 확보)"
    fi
    [ "$qn" -eq 0 ] && want=0

    mine=$(ps -eo args --no-headers | grep -cE "add_slot_gen\.sh $g [A-Za-z0-9]+$")
    if [ "$mine" -gt "$want" ]; then
      n=$(( mine - want ))
      for pid in $(ps -eo pid,args --no-headers | grep -E "add_slot_gen\.sh $g [A-Za-z0-9]+$" \
                   | awk '{print $1}' | head -$n); do kill "$pid"; done
      echo "[$(date +%H:%M:%S)] GPU$g 외부 ${foreign}MiB 외부SM~${avg}% → $mine→$want$note" >> "$LOG"
    elif [ "$mine" -lt "$want" ] && [ "$qn" -gt 0 ]; then
      for k in $(seq $(( mine + 1 )) "$want"); do
        nohup bash "$SLOT" "$g" "m$k$(date +%s)" >/dev/null 2>&1 &
      done
      echo "[$(date +%H:%M:%S)] GPU$g 외부 ${foreign}MiB 외부SM~${avg}% → $mine→$want$note" >> "$LOG"
    fi
  done < <(nvidia-smi --query-gpu=index,memory.used,utilization.gpu,temperature.gpu --format=csv,noheader)
  unset OURSMEM OURSM FSM IDX
  sleep 180
done
