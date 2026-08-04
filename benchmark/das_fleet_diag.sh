#!/usr/bin/env bash
# das_fleet_diag.sh — 진단 실행기 (상반성 위반 · exit_vis 몫)
#   사용: bash benchmark/das_fleet_diag.sh <airframe> <n_az> <freqs> <nshard> <gpus>
set -u
cd /home/yunjung/workspace/sionna2
export PYTHONPATH=src:benchmark
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
PY=~/.venvs/py312/bin/python
AF=$1; NAZ=$2; FR=$3; NS=$4; IFS=',' read -r -a GPUS <<< "${5:-2,3}"
DIR=outputs/partial/das_fleet_0803; mkdir -p "$DIR"
LOG=$DIR/diag_$AF.log
for mode in recip exitvis; do
  pids=()
  for ((k=0;k<NS;k++)); do
    SIONNA2_GPU=${GPUS[$((k % ${#GPUS[@]}))]} nohup $PY benchmark/das_fleet_sigma.py \
      --airframe "$AF" --mode $mode --n-az "$NAZ" --freqs "$FR" \
      --shard $k --nshard $NS >> "$LOG" 2>&1 &
    pids+=($!); echo $! >> "$DIR/worker_diag.pids"; sleep 2
  done
  wait "${pids[@]}"
done
echo "[$(date +%H:%M:%S)] diag $AF done" >> "$LOG"
