#!/usr/bin/env bash
# das_fleet_val_driver.sh — phantom3 바이스태틱 워커 풀 (잠금선점·재개가능)
#
#  사용:  bash benchmark/das_fleet_val_driver.sh <워커수> <GPU목록,쉼표>
#  ⚠ nohup 이라 워크플로가 끝나도 살아남는다 → PID 를 worker_val.pids 에 남긴다.
#  ⚠ 스레드 고정 — BLAS 가 프로세스당 수십 코어를 잡으면 서로를 밀어낸다.
set -u
cd /home/yunjung/workspace/sionna2

PY=~/.venvs/py312/bin/python
export PYTHONPATH=src:benchmark
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1

N=${1:-8}
IFS=',' read -r -a GPUS <<< "${2:-2,3}"
PLAN=${3:-"phantom3:0,phantom3:1,phantom3:2,phantom3:3"}

DIR=outputs/partial/das_fleet_val_0803
mkdir -p "$DIR"
LOG=$DIR/driver_val.log

for ((k = 0; k < N; k++)); do
  g=${GPUS[$((k % ${#GPUS[@]}))]}
  SIONNA2_GPU=$g nohup $PY benchmark/das_fleet_val_sigma.py --plan "$PLAN" >> "$LOG" 2>&1 &
  echo "$!" >> "$DIR/worker_val.pids"
  sleep 2
done
echo "[$(date +%H:%M:%S)] val pool: launched $N workers on GPUs ${GPUS[*]}" >> "$LOG"
