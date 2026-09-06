#!/bin/bash
#: 발주 전 거르기 — 줄 하나를 받아 NEW(없음)·DONE(있고 n_dup 있음)·STALE(있는데 n_dup 없음) 을 낸다.
#  쓰는 법: grep -vE "^\s*(#|$)" runners/jobs_XXXX.txt | xargs -d"\n" -P 4 -I{} runners/filter_jobs.sh {} > /tmp/chk.out
#  ⚠STALE 이 늘 «다시 산다»는 아니다 — n_dup 이 필요한 물음(되풀이 셈)에서만 --overwrite. 클러터·STFT 물음은 E 만 있으면 된다.
# 한 줄의 목표 샤드가 이미 있는지, 있다면 n_dup 이 들었는지 본다.
L="$1"
PY=/workspace/.venvs/py312/bin/python
OUT=$(CUDA_VISIBLE_DEVICES="" SIONNA2_ALLOW_CPU=1 timeout 300 $PY benchmark/elevation_sweep_md.py $L --dry-run 2>&1 </dev/null | grep -E "^\s*\[dry\]")
NAME=$(echo "$OUT" | grep -oE '[A-Za-z0-9_.+-]+\.npz' | head -1)
[ -z "$NAME" ] && { echo "?|$L"; exit; }
F="outputs/elev_sweep_shards/$NAME"
if [ ! -e "$F" ]; then echo "NEW|$L"; exit; fi
HAS=$(CUDA_VISIBLE_DEVICES="" $PY -c "import numpy,sys;print('Y' if 'n_dup' in numpy.load(sys.argv[1]).files else 'N')" "$F" 2>/dev/null)
if [ "$HAS" = "Y" ]; then echo "DONE|$L"; else echo "STALE|$L"; fi
