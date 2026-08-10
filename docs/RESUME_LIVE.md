# RESUME_LIVE — 10분 자동 스냅샷 (수동 편집 금지, 갱신 2026-08-10 05:37:07)

## 프로세스
84448 /home/yunjung/.venvs/py312/bin/python benchmark/rcs_same_span_sweep.py
101312 /home/yunjung/.venvs/py312/bin/python src/experiment_freespace_sigma.py --drone matrice4e --backend direct --force
198615 bash -c for i in $(seq 1 144); do { echo "# RESUME_LIVE — 10분 자동 스냅샷 (수동 편집 금지, 갱신 $(date "+%F %T"))"; echo; echo "## 프로세스"; pgrep -af "report15b_microdoppler_recompute|experiment_freespace_sigma|rcs_same_span|hover_long" || echo "(없음)"; echo; echo "## GPU"; nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader; echo; echo "## 로그 후미"; for f in md15b3_meshfix sigma_force_m4e sigma_force_mini5 samespan sigma_chain; do echo "── $f.log:"; tail -2 /tmp/claude-1015/-home-yunjung-workspace/a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad/$f.log 2>/dev/null; done; echo; echo "## git"; git -C /home/yunjung/workspace/sionna2 log --oneline -1; echo "미커밋 $(git -C /home/yunjung/workspace/sionna2 status --porcelain | wc -l)건"; } > /home/yunjung/workspace/sionna2/docs/RESUME_LIVE.md 2>&1; sleep 600; done
361292 bash -c while kill -0 101312 2>/dev/null; do sleep 60; done; SIONNA2_GPU=2 PYTHONPATH=src ~/.venvs/py312/bin/python src/experiment_freespace_sigma.py --drone mini5pro --backend direct --force > /tmp/claude-1015/-home-yunjung-workspace/a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad/sigma_force_mini5_direct.log 2>&1; echo SIGMA_MINI5_DONE $(date +%H:%M:%S) >> /tmp/claude-1015/-home-yunjung-workspace/a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad/sigma_chain.log

## GPU
0, 22295 MiB, 100 %
1, 17738 MiB, 100 %
2, 11654 MiB, 28 %
3, 22030 MiB, 100 %

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
  DJI Matrice 4E    16.0 GHz  mu  -14.12 dBsm  (3737s)
  DJI Matrice 4E    16.5 GHz  mu  -13.93 dBsm  (4085s)
── sigma_chain.log:
SIGMA_CHAIN_DONE 05:01:18
HOVER_OUTDOOR_DONE 05:07:07

## git
bfd510e 0810 라운드3: 로터 산포 프리셋 이원화 실행 — f11 실내/야외 비교(야외 2%/2.5%@1Hz 웹앵커), report07 셀15/그림12, hover outdoor 원장
미커밋 8건
