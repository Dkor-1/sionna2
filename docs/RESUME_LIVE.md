# RESUME_LIVE — 10분 자동 스냅샷 (수동 편집 금지, 갱신 2026-08-10 06:27:10)

## 프로세스
84448 /home/yunjung/.venvs/py312/bin/python benchmark/rcs_same_span_sweep.py
101312 /home/yunjung/.venvs/py312/bin/python src/experiment_freespace_sigma.py --drone matrice4e --backend direct --force
198615 bash -c for i in $(seq 1 144); do { echo "# RESUME_LIVE — 10분 자동 스냅샷 (수동 편집 금지, 갱신 $(date "+%F %T"))"; echo; echo "## 프로세스"; pgrep -af "report15b_microdoppler_recompute|experiment_freespace_sigma|rcs_same_span|hover_long" || echo "(없음)"; echo; echo "## GPU"; nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader; echo; echo "## 로그 후미"; for f in md15b3_meshfix sigma_force_m4e sigma_force_mini5 samespan sigma_chain; do echo "── $f.log:"; tail -2 /tmp/claude-1015/-home-yunjung-workspace/a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad/$f.log 2>/dev/null; done; echo; echo "## git"; git -C /home/yunjung/workspace/sionna2 log --oneline -1; echo "미커밋 $(git -C /home/yunjung/workspace/sionna2 status --porcelain | wc -l)건"; } > /home/yunjung/workspace/sionna2/docs/RESUME_LIVE.md 2>&1; sleep 600; done
361292 bash -c while kill -0 101312 2>/dev/null; do sleep 60; done; SIONNA2_GPU=2 PYTHONPATH=src ~/.venvs/py312/bin/python src/experiment_freespace_sigma.py --drone mini5pro --backend direct --force > /tmp/claude-1015/-home-yunjung-workspace/a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad/sigma_force_mini5_direct.log 2>&1; echo SIGMA_MINI5_DONE $(date +%H:%M:%S) >> /tmp/claude-1015/-home-yunjung-workspace/a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad/sigma_chain.log
604230 /bin/bash -c source /home/yunjung/.claude/shell-snapshots/snapshot-bash-1786333760585-mvby99.sh 2>/dev/null || true && shopt -u extglob 2>/dev/null || true && { \builtin unalias -- 'unsetenv'; \builtin unset -f -- 'unsetenv'; } >/dev/null 2>&1 || true && eval 'S=/tmp/claude-1015/-home-yunjung-workspace/a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad nohup bash -c '"'"'until grep -q HIRES_ALLDONE '"'"'$S'"'"'/hires_marker.log 2>/dev/null; do sleep 30; done'"'"' >/dev/null 2>&1 # 고해상도 체인이 끝나면 호버(2초)도 고 PRF 로 — SBR 단독이라 GPU2 안에서 돈다 nohup bash -c '"'"'while pgrep -f "report07_three_engine" >/dev/null; do sleep 60; done; SIONNA2_GPU=2 PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report07_hover_long.py --sec 0.5 --tag _hires > '"'"'$S'"'"'/hover_hires.log 2>&1; echo HOVER_HIRES_DONE $(date +%H:%M:%S) >> '"'"'$S'"'"'/sigma_chain.log'"'"' > /dev/null 2>&1 & echo "체인 등록: 세엔진 고해상도 종료 → hover 고해상도(0.5s)"' < /dev/null && pwd -P >| /tmp/claude-ddf8-cwd

## GPU
0, 22717 MiB, 100 %
1, 14748 MiB, 100 %
2, 11948 MiB, 0 %
3, 21858 MiB, 100 %

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
  DJI Phantom 4     10.0 GHz  mu  -18.32 dBsm  (443s)
  DJI Phantom 4     10.5 GHz  mu  -16.25 dBsm  (514s)
── sigma_chain.log:
SIGMA_CHAIN_DONE 05:01:18
HOVER_OUTDOOR_DONE 05:07:07

## git
37828a6 0810 라운드7: ⭐시간 분해능 상향 체계 — PRF 배수 개방 + auto_periods 자동 규약, 전 스펙트로그램 그림 재계산 큐
미커밋 7건
