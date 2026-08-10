# RESUME_LIVE — 10분 자동 스냅샷 (수동 편집 금지, 갱신 2026-08-10 07:47:12)

## 프로세스
198615 bash -c for i in $(seq 1 144); do { echo "# RESUME_LIVE — 10분 자동 스냅샷 (수동 편집 금지, 갱신 $(date "+%F %T"))"; echo; echo "## 프로세스"; pgrep -af "report15b_microdoppler_recompute|experiment_freespace_sigma|rcs_same_span|hover_long" || echo "(없음)"; echo; echo "## GPU"; nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader; echo; echo "## 로그 후미"; for f in md15b3_meshfix sigma_force_m4e sigma_force_mini5 samespan sigma_chain; do echo "── $f.log:"; tail -2 /tmp/claude-1015/-home-yunjung-workspace/a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad/$f.log 2>/dev/null; done; echo; echo "## git"; git -C /home/yunjung/workspace/sionna2 log --oneline -1; echo "미커밋 $(git -C /home/yunjung/workspace/sionna2 status --porcelain | wc -l)건"; } > /home/yunjung/workspace/sionna2/docs/RESUME_LIVE.md 2>&1; sleep 600; done
977291 bash -c while pgrep -f "report07_hover_long|report07_5g_waveform|report07_sionna_range_sweep|report15b_microdoppler" >/dev/null; do sleep 60; done; cd /home/yunjung/workspace/sionna2; SIONNA2_GPU=2 PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report07_ray_budget_test.py > /tmp/claude-1015/-home-yunjung-workspace/a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad/raybudget.log 2>&1; echo RAYBUDGET_DONE $(date +%H:%M:%S) >> /tmp/claude-1015/-home-yunjung-workspace/a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad/hires_queue.log
992956 bash -c while pgrep -f "report07_hover_long|report07_5g_waveform|report07_sionna_range_sweep|report15b_microdoppler|report07_ray_budget" >/dev/null; do sleep 60; done; cd /home/yunjung/workspace/sionna2; SIONNA2_GPU=2 SIONNA2_MD_PRF_MULT=16 PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report07_three_engine_maps.py --n 4096 > /tmp/claude-1015/-home-yunjung-workspace/a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad/te_mono.log 2>&1; echo TE_MONO_DONE >> /tmp/claude-1015/-home-yunjung-workspace/a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad/hires_queue.log
1043143 /bin/bash -c source /home/yunjung/.claude/shell-snapshots/snapshot-bash-1786333760585-mvby99.sh 2>/dev/null || true && shopt -u extglob 2>/dev/null || true && { \builtin unalias -- 'unsetenv'; \builtin unset -f -- 'unsetenv'; } >/dev/null 2>&1 || true && eval '~/.venvs/py312/bin/python -c "import ast;ast.parse(open('"'"'benchmark/rcs_same_span_sweep.py'"'"').read());print('"'"'구문 OK'"'"')" && SIONNA2_GPU=2 PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/rcs_same_span_sweep.py > /tmp/claude-1015/-home-yunjung-workspace/a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad/samespan_p3.log 2>&1' < /dev/null && pwd -P >| /tmp/claude-5834-cwd
1043170 /home/yunjung/.venvs/py312/bin/python benchmark/rcs_same_span_sweep.py

## GPU
0, 23769 MiB, 100 %
1, 23778 MiB, 100 %
2, 19056 MiB, 100 %
3, 21001 MiB, 100 %

## 로그 후미
── md15b3_meshfix.log:
✅ /home/yunjung/workspace/sionna2/outputs/report15b_microdoppler.json
✅ /home/yunjung/workspace/sionna2/outputs/report15b_series.npz  (1.8 MB)
── sigma_force_m4e.log:
    raise self._exception
concurrent.futures.process.BrokenProcessPool: A process in the process pool was terminated abruptly while the future was running or pending.
── sigma_force_mini5.log:
    raise self._exception
concurrent.futures.process.BrokenProcessPool: A process in the process pool was terminated abruptly while the future was running or pending.
── samespan.log:

✅ outputs/rcs_same_span.json
── sigma_chain.log:
HOVER_OUTDOOR_DONE 05:07:07
SIGMA_MINI5_DONE 07:13:45

## git
3649ca9 0810 라운드10: ⭐적대적 감사 처방 — 사실 오류 6건 정정 + 거짓해제 게이트 수정 + σ 세대 도장 + phantom3 같은구간
미커밋 2건
