#!/usr/bin/env bash
# run_gaps_pinned.sh — ⭐워커마다 **GPU 한 장만** 보여주는 드라이버 (2026-08-19)
#
# 왜 새로 만들었나
# ----------------
# 기존 드라이버는 CUDA_VISIBLE_DEVICES=0,1,2,3,4 로 **다섯 장을 전부** 보여준다.
# 그러면 Dr.Jit 이 보이는 장마다 CUDA 문맥을 열어 **놀고 있는 카드에도 554 MB 씩** 잡는다.
# 실측(2026-08-19): CVD="0,1,2,3,4" → 문맥 3 개(554+552 MiB 는 놀고 있음)
#                   CVD="4"        → 문맥 1 개
# 워커 9 개면 빈 껍데기만 약 20 GB 다.
#
# ⛔돌고 있는 드라이버(run_gaps_0817/B/C.sh)는 **고치지 않는다** — bash 는 스크립트를
#   조금씩 읽어 가며 실행해서, 도는 중에 파일을 고치면 실행이 깨진다. 이건 새 파일이다.
#
# ⭐적응형 배치는 유지한다 — 매 작업 직전에 **여유 메모리가 가장 많은 카드 한 장**을 골라
#   그 장만 보여준다(카드 고정이 아니다).
#
# 사용: bash runners/run_gaps_pinned.sh <jobs.txt> <워커수> <로그>
cd /workspace/sionna
export PYTHONPATH=src:benchmark
export DRJIT_LIBOPTIX_PATH=/workspace/.venvs/optix/libnvoptix.so.1
export LD_LIBRARY_PATH=/workspace/.venvs/optix:$LD_LIBRARY_PATH
PY=/workspace/.venvs/py312/bin/python
[ -x "$PY" ] || PY=$HOME/.venvs/py312/bin/python
JOBS="$1"; NW="${2:-3}"; LOG="${3:-runners/pinned.log}"

pick_gpu() {   # 여유 메모리가 가장 많은 카드의 인덱스
  nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits \
    | sort -t, -k2 -n | head -1 | cut -d, -f1 | tr -d ' '
}

i=0
while IFS= read -r line; do
  case "$line" in ''|'#'*) continue;; esac
  case "$line" in '--help'*) continue;; esac
  i=$((i+1))
  G=$(pick_gpu)
  ( echo "[$(date -u +%H:%M:%S)] START #$i gpu=$G $line" >> "$LOG"
    CUDA_VISIBLE_DEVICES="$G" $PY benchmark/elevation_sweep_md.py $line >> "$LOG" 2>&1
    echo "[$(date -u +%H:%M:%S)] DONE  #$i rc=$?" >> "$LOG" ) &
  while [ "$(jobs -rp | wc -l)" -ge "$NW" ]; do wait -n 2>/dev/null || sleep 5; done
done < "$JOBS"
wait
echo "[$(date -u +%H:%M:%S)] ALL DONE ($i 줄)" >> "$LOG"
