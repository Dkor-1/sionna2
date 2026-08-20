#!/usr/bin/env bash
# cpu12_env.sh — ⭐**컨테이너가 CPU 12 개만 준다**는 사실에 맞춰 스레드를 조인다 (2026-08-20)
#
# 왜 필요한가 — 실측
# -------------------
#   cgroup 실제 할당 : /sys/fs/cgroup/cpu.max = 1200000 100000 → **12.0 CPU**
#   os.cpu_count()   : **192**  ← 파이썬·라이브러리가 보는 값
#
# 거의 모든 계산 라이브러리가 시작할 때 os.cpu_count() 를 보고 그만큼 스레드풀을 만든다
# (OpenMP · MKL · OpenBLAS · NumExpr · Dr.Jit · Mitsuba). 그래서 프로세스 하나가
# **스레드 322 개**를 띄우고 12 CPU 를 두고 서로 싸웠다(2026-08-19 실측).
# 일을 더 하는 게 아니라 **문맥 전환만 폭증**한다 — 서버가 느려지고 접속이 끊긴 원인이다.
#
# ⛔이 파일을 source 한 뒤에만 계산을 띄운다.
#   사용: source runners/cpu12_env.sh [스레드수]   (기본 2)
#
# 관련 기록: 랩 서버 담당자 지적(스레드 200×30) · [[no-auto-kill-processes]]

: "${SIONNA_THREADS:=${1:-2}}"

# ── ① 수치 라이브러리 스레드풀 ──────────────────────────────────────
export OMP_NUM_THREADS="$SIONNA_THREADS"
export OPENBLAS_NUM_THREADS="$SIONNA_THREADS"
export MKL_NUM_THREADS="$SIONNA_THREADS"
export NUMEXPR_NUM_THREADS="$SIONNA_THREADS"
export VECLIB_MAXIMUM_THREADS="$SIONNA_THREADS"
# OpenMP 가 남는 스레드를 바쁜대기(spin) 시키지 않게 — 12 코어에서 이게 특히 아프다
export OMP_WAIT_POLICY=PASSIVE
export OMP_DYNAMIC=TRUE
export KMP_BLOCKTIME=0

# ── ② Dr.Jit / Mitsuba ─────────────────────────────────────────────
#   ⚠환경변수 이름은 판마다 다르다. 코드에서 dr.set_thread_count() 로 한 번 더 못 박는다
#   (benchmark/thread_guard.py 참고). 여기서는 알려진 것만 건다.
export DRJIT_NUM_THREADS="$SIONNA_THREADS"
export MI_NUM_THREADS="$SIONNA_THREADS"

# ── ③ 기타 상주 스레드 ─────────────────────────────────────────────
export TOKENIZERS_PARALLELISM=false
export RAYON_NUM_THREADS="$SIONNA_THREADS"

# ── ④ 저장소 공통 ──────────────────────────────────────────────────
export PYTHONPATH=src:benchmark
export DRJIT_LIBOPTIX_PATH=/workspace/.venvs/optix/libnvoptix.so.1
export LD_LIBRARY_PATH=/workspace/.venvs/optix:${LD_LIBRARY_PATH:-}

echo "[cpu12] 스레드 $SIONNA_THREADS/프로세스 · CPU 할당 $(awk '{printf "%.0f",$1/$2}' /sys/fs/cgroup/cpu.max) 개" >&2
