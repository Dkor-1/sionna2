#!/usr/bin/env bash
# ⭐영구 사본(세션 스크래치패드는 세션마다 사라진다). 정본 메쉬 원장의 앙각 빈 칸 41 칸을 채운다 (2026-08-17).
# ⭐정본 스위치(MESH_FIX/BLADE_LAW)는 인자를 안 주면 기본이라 그대로 둔다 — 파일명에
#   _mfixbatteryi5_blperairframe 이 붙고, 이미 난 샤드는 스크립트가 건너뛴다.
# ⛔GPU 2·3 만 쓴다(0·1·4 는 외부가 쓰는 중). 워커 3.
cd /workspace/sionna
export CUDA_VISIBLE_DEVICES=0,1,4
export PYTHONPATH=src:benchmark
# ⭐OptiX — 이걸 빼면 rt.load_scene() 에서 죽는다(우리 커널 팔도 재질 조회에 쓴다)
export DRJIT_LIBOPTIX_PATH=/workspace/.venvs/optix/libnvoptix.so.1
export LD_LIBRARY_PATH=/workspace/.venvs/optix:$LD_LIBRARY_PATH
PY=/workspace/.venvs/py312/bin/python
[ -x "$PY" ] || PY=$HOME/.venvs/py312/bin/python
JOBS="$1"; NW="${2:-3}"; LOG="$3"
i=0
while IFS= read -r line; do
  [ -z "$line" ] && continue
  i=$((i+1))
  ( echo "[$(date -u +%H:%M:%S)] START #$i $line" >> "$LOG"
    $PY benchmark/elevation_sweep_md.py $line >> "$LOG" 2>&1; rc=$?
    echo "[$(date -u +%H:%M:%S)] DONE  #$i rc=$rc" >> "$LOG" ) &
  while [ "$(jobs -rp | wc -l)" -ge "$NW" ]; do sleep 20; done
done < "$JOBS"
wait
echo "[$(date -u +%H:%M:%S)] ALL DONE" >> "$LOG"
