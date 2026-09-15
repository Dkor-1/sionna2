#!/bin/bash
#: 발주 전 거르기 — 줄 하나를 받아 NEW(없음)·DONE(있고 n_dup 있음)·STALE(있는데 n_dup 없음) 을 낸다.
#  쓰는 법: grep -vE "^\s*(#|$)" runners/jobs_XXXX.txt | xargs -d"\n" -P 4 -I{} runners/filter_jobs.sh {} > /tmp/chk.out
#  ⚠STALE 이 늘 «다시 산다»는 아니다 — n_dup 이 필요한 물음(되풀이 셈)에서만 --overwrite. 클러터·STFT 물음은 E 만 있으면 된다.
#
#  ⛔⛔**BAD 는 곧 발주 불가다** (2026-09-15 신설). 전에는 이름을 못 지으면 `?|` 하나만
#    냈고, 그것이 **시간초과**와 **인자 오류**를 구별하지 못해 사람이 그냥 넘겼다.
#    · 그날 사고 — `--env sionna-simple_street_canyon`(하이픈)은 당시 dry-run 이
#      검사를 안 해서 이름을 **그냥 지어 냈고** 10 줄이 NEW 로 통과해 GPU 에서 죽었다.
#      (빌더 쪽은 elevation_sweep_md.py 의 «환경 이름은 이름을 짓기 전에 확인한다» 로 막았다.)
#    ⇒ 여기서는 빌더가 낸 ⛔ 줄을 **그대로 물고 나온다.** 이유가 안 보이면 못 고친다.
# 한 줄의 목표 샤드가 이미 있는지, 있다면 n_dup 이 들었는지 본다.
L="$1"
PY=/workspace/.venvs/py312/bin/python
RAW=$(CUDA_VISIBLE_DEVICES="" SIONNA2_ALLOW_CPU=1 timeout 300 $PY benchmark/elevation_sweep_md.py $L --dry-run 2>&1 </dev/null)
RC=$?
OUT=$(echo "$RAW" | grep -E "^\s*\[dry\]")
NAME=$(echo "$OUT" | grep -oE '[A-Za-z0-9_.+-]+\.npz' | head -1)
if [ -z "$NAME" ]; then
  # 빌더가 낸 첫 ⛔ 줄을 이유로 단다. 없으면 마지막 한 줄, 그것도 없으면 rc 만.
  WHY=$(echo "$RAW" | grep -m1 '⛔' | tr -d '\n' | cut -c1-200)
  [ -z "$WHY" ] && WHY=$(echo "$RAW" | grep -v '^\s*$' | tail -1 | tr -d '\n' | cut -c1-200)
  [ -z "$WHY" ] && WHY="출력 없음 (rc=$RC · 300 초 시간초과면 rc=124)"
  echo "BAD|$WHY|$L"; exit
fi
F="outputs/elev_sweep_shards/$NAME"
if [ ! -e "$F" ]; then echo "NEW|$L"; exit; fi
HAS=$(CUDA_VISIBLE_DEVICES="" $PY -c "import numpy,sys;print('Y' if 'n_dup' in numpy.load(sys.argv[1]).files else 'N')" "$F" 2>/dev/null)
if [ "$HAS" = "Y" ]; then echo "DONE|$L"; else echo "STALE|$L"; fi
