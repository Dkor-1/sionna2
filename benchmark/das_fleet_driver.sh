#!/usr/bin/env bash
# das_fleet_driver.sh — Das 함대 σ(f,θb) 계산 워커 풀 (단계식·재개가능·동적 증감)
#
#  사용:  bash benchmark/das_fleet_driver.sh <워커수> <GPU목록,쉼표> [플랜]
#  예:    bash benchmark/das_fleet_driver.sh 12 2,3
#
#  ■ 작업 배분은 **잠금파일 선점**이다(정적 샤딩 아님) → 워커를 나중에 더 띄워도 되고,
#    죽여도 되고, 다른 워크플로가 GPU 를 물면 몇 개만 줄이면 된다. 조율이 필요 없다.
#  ■ 단계가 올라갈수록 격자가 배로 촘촘해지고 낮은 단계 표본은 부분집합이라 재사용된다
#    → 어느 시점에 끊겨도 그때까지의 결과가 완결형이다.
#  ■ ⚠ 스레드 고정 — numpy/BLAS 가 프로세스당 수십 코어를 잡으면 서로를 밀어낸다
#    (실측: 같은 계산이 3.0 s → 1.4 s). 병렬은 프로세스로만 낸다.
#  ■ ⚠ GPU 는 다른 워크플로와 공유한다. 카드를 독점하지 않는다.
set -u
cd /home/yunjung/workspace/sionna2

PY=~/.venvs/py312/bin/python
export PYTHONPATH=src:benchmark
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1

N=${1:-12}
IFS=',' read -r -a GPUS <<< "${2:-2,3}"
#  순서 = 우선순위. 싼 두 기체를 먼저 최종격자까지 올리고, 가장 비싼 m350rtk 는 뒤에 둔다.
#  (m350rtk 는 한 표본이 mini2 의 ~16 배다 — 같은 벽시계로 살 수 있는 정보량이 적다.)
PLAN=${3:-"mini2:0,phantom2:0,m350rtk:0,mini2:1,phantom2:1,m350rtk:1,mini2:2,phantom2:2,mini2:3,phantom2:3,m350rtk:2,m350rtk:3"}

DIR=outputs/partial/das_fleet_0803
POOL=${POOL:-a}                 # 풀 이름 — 풀마다 PID 파일이 따로다(따로 줄이고 늘리려고)
mkdir -p "$DIR"
LOG=$DIR/driver_$POOL.log

for ((k = 0; k < N; k++)); do
  g=${GPUS[$((k % ${#GPUS[@]}))]}
  SIONNA2_GPU=$g nohup $PY benchmark/das_fleet_sigma.py --plan "$PLAN" >> "$LOG" 2>&1 &
  echo "$!" >> "$DIR/worker_$POOL.pids"
  sleep 2                       # 동시 기동 폭주 방지(메쉬 빌드·CUDA 컨텍스트가 겹치지 않게)
done
echo "[$(date +%H:%M:%S)] pool $POOL: launched $N workers on GPUs ${GPUS[*]}" >> "$LOG"
wait
echo "[$(date +%H:%M:%S)] pool exhausted" >> "$LOG"
