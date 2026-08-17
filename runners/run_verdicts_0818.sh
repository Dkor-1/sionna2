#!/usr/bin/env bash
# 판정 재실행 — 앙각 빈칸 41 칸을 채운 뒤 원장 위층을 상류부터 다시 짓는다 (2026-08-18).
#
# ⛔이 스크립트는 **빈칸 채우기 큐가 ALL DONE 된 뒤에만** 돌린다. 덜 찬 원장으로 판정을 내면
#   기체 비교가 각도마다 표본이 달라 결론이 흔들린다(docs/RESUME.md §1).
# ⛔GPU 를 쓰는 것은 detection_curves 뿐이고 나머지는 저장된 원장만 읽는다.
#
# 층 순서는 의존 그래프에서 나왔다(benchmark/canon_0816/README.md):
#   0 병합 → 1 완성표·재질판정 → 2 기체교차·H5·사다리 → 3 탐지·분류 → 4 재질정본 → 5 사전등록 → 6 아틀라스
#
# 사용:  bash runners/run_verdicts_0818.sh <층번호|all>
set -u
cd /workspace/sionna
export PYTHONPATH=src:benchmark
export DRJIT_LIBOPTIX_PATH=/workspace/.venvs/optix/libnvoptix.so.1
export LD_LIBRARY_PATH=/workspace/.venvs/optix:${LD_LIBRARY_PATH:-}
PY=/workspace/.venvs/py312/bin/python
LOG=${LOG:-/workspace/sionna/outputs/logs/verdicts_0818.log}
mkdir -p "$(dirname "$LOG")"

run() {  # run <이름> <명령…>
  local name="$1"; shift
  echo "[$(TZ=Asia/Seoul date +%H:%M:%S)] ▶ $name" | tee -a "$LOG"
  "$@" >>"$LOG" 2>&1
  local rc=$?
  echo "[$(TZ=Asia/Seoul date +%H:%M:%S)] $([ $rc -eq 0 ] && echo ✅ || echo ❌rc=$rc) $name" | tee -a "$LOG"
  return $rc
}

L=${1:-}
[ -z "$L" ] && { echo "층번호(0~6) 또는 all 을 준다"; exit 2; }

do0() { run "0 병합"                 $PY benchmark/elevation_sweep_md.py --merge; }
do1() { run "1 완성표"               $PY benchmark/canon_0816/frame_completion_0816.py &&
        run "1 재질판정"             $PY benchmark/canon_0816/build_material_verdict.py; }
do2() { run "2 기체교차"             $PY benchmark/canon_0816/build_airframe_canon_verdict.py
        run "2 H5 굴절"              $PY benchmark/canon_0816/write_h5.py
        run "2 두께사다리"           $PY benchmark/canon_0816/ladder_final.py; }
do3() { run "3 탐지곡선"             $PY benchmark/detection_curves.py
        run "3 분류"                 $PY benchmark/classify_airframe.py; }
do4() { run "4 재질정본"             $PY benchmark/canon_0816/build_material_canon.py; }
do5() { run "5 잡음 사전등록"        $PY benchmark/canon_0816/make_prereg.py; }
do6() { run "6 아틀라스 목차"        $PY benchmark/build_atlas_toc.py
        run "6 아틀라스 그림"        $PY benchmark/build_md_atlas.py
        run "6 아틀라스 갤러리"      $PY benchmark/build_atlas_gallery.py; }

case "$L" in
  0|1|2|3|4|5|6) "do$L" ;;
  all) do0 && do1 && { do2; do3; do4; do5; do6; } ;;
  *) echo "모르는 층: $L"; exit 2 ;;
esac
