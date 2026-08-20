#!/usr/bin/env bash
# run_gaps_spread.sh — ⭐카드를 **돌아가며 고정 배분**하는 드라이버 (2026-08-19)
#
# 앞판(run_gaps_pinned.sh)의 결함
# --------------------------------
# 작업 직전에 «가장 빈 카드» 를 고르게 했더니, 워커 넷이 **동시에** 뜨면서 넷 다 같은 답
# (GPU 2)을 봤다. 결과: 한 장에 넷이 몰림. «그 순간의 여유» 는 동시 기동에 취약하다.
#
# 이 판
# -----
#   ⭐**워커 자리(slot)마다 카드를 미리 못박는다** — slot i → GPU_LIST[i % N].
#     동시에 떠도 절대 안 겹치고, 저장소 규약(모든 GPU 최소 1 점유)이 **구조적으로** 지켜진다.
#   ⭐워커마다 **그 한 장만** 보여준다(CUDA_VISIBLE_DEVICES=단일) — 빈 문맥 554 MB 가 안 생긴다.
#     실측 근거: CVD="0,1,2,3,4" → 문맥 3 개 · CVD="4" → 1 개 (2026-08-19)
#
# 사용: bash runners/run_gaps_spread.sh <jobs.txt> <워커수> <로그> [카드목록]
#   예: bash runners/run_gaps_spread.sh q.txt 10 log.txt 0,1,2,3,4   → 카드마다 2 개씩
cd /workspace/sionna
export PYTHONPATH=src:benchmark
export DRJIT_LIBOPTIX_PATH=/workspace/.venvs/optix/libnvoptix.so.1
export LD_LIBRARY_PATH=/workspace/.venvs/optix:$LD_LIBRARY_PATH
PY=/workspace/.venvs/py312/bin/python
[ -x "$PY" ] || PY=$HOME/.venvs/py312/bin/python

JOBS="$1"; NW="${2:-10}"; LOG="${3:-runners/logs/spread.log}"
IFS=',' read -r -a GPUS <<< "${4:-0,1,2,3,4}"
NG=${#GPUS[@]}
mkdir -p "$(dirname "$LOG")"
echo "[$(date -u +%H:%M:%S)] 시작 — 워커 $NW · 카드 ${GPUS[*]} (자리마다 고정)" >> "$LOG"

# ⭐자리 → 카드 표를 먼저 찍어 둔다(사람이 눈으로 확인할 수 있게)
for ((i=0;i<NW;i++)); do echo "  slot $i → GPU ${GPUS[$((i%NG))]}" >> "$LOG"; done

slot=0; i=0
while IFS= read -r line; do
  case "$line" in ''|'#'*|'--help'*) continue;; esac
  i=$((i+1))
  G=${GPUS[$((slot%NG))]}
  ( echo "[$(date -u +%H:%M:%S)] START #$i slot=$slot gpu=$G $line" >> "$LOG"
    CUDA_VISIBLE_DEVICES="$G" $PY benchmark/elevation_sweep_md.py $line >> "$LOG" 2>&1
    echo "[$(date -u +%H:%M:%S)] DONE  #$i slot=$slot gpu=$G rc=$?" >> "$LOG" ) &
  slot=$((slot+1))
  while [ "$(jobs -rp | wc -l)" -ge "$NW" ]; do wait -n 2>/dev/null || sleep 5; done
done < "$JOBS"
wait
echo "[$(date -u +%H:%M:%S)] ALL DONE ($i 줄)" >> "$LOG"
