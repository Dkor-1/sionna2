# RESUME_LIVE — 10분 자동 스냅샷 (수동 편집 금지, 갱신 2026-08-10 09:37:16)

## 프로세스
198615 bash -c for i in $(seq 1 144); do { echo "# RESUME_LIVE — 10분 자동 스냅샷 (수동 편집 금지, 갱신 $(date "+%F %T"))"; echo; echo "## 프로세스"; pgrep -af "report15b_microdoppler_recompute|experiment_freespace_sigma|rcs_same_span|hover_long" || echo "(없음)"; echo; echo "## GPU"; nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader; echo; echo "## 로그 후미"; for f in md15b3_meshfix sigma_force_m4e sigma_force_mini5 samespan sigma_chain; do echo "── $f.log:"; tail -2 /tmp/claude-1015/-home-yunjung-workspace/a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad/$f.log 2>/dev/null; done; echo; echo "## git"; git -C /home/yunjung/workspace/sionna2 log --oneline -1; echo "미커밋 $(git -C /home/yunjung/workspace/sionna2 status --porcelain | wc -l)건"; } > /home/yunjung/workspace/sionna2/docs/RESUME_LIVE.md 2>&1; sleep 600; done
977291 bash -c while pgrep -f "report07_hover_long|report07_5g_waveform|report07_sionna_range_sweep|report15b_microdoppler" >/dev/null; do sleep 60; done; cd /home/yunjung/workspace/sionna2; SIONNA2_GPU=2 PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report07_ray_budget_test.py > /tmp/claude-1015/-home-yunjung-workspace/a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad/raybudget.log 2>&1; echo RAYBUDGET_DONE $(date +%H:%M:%S) >> /tmp/claude-1015/-home-yunjung-workspace/a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad/hires_queue.log
992956 bash -c while pgrep -f "report07_hover_long|report07_5g_waveform|report07_sionna_range_sweep|report15b_microdoppler|report07_ray_budget" >/dev/null; do sleep 60; done; cd /home/yunjung/workspace/sionna2; SIONNA2_GPU=2 SIONNA2_MD_PRF_MULT=16 PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report07_three_engine_maps.py --n 4096 > /tmp/claude-1015/-home-yunjung-workspace/a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad/te_mono.log 2>&1; echo TE_MONO_DONE >> /tmp/claude-1015/-home-yunjung-workspace/a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad/hires_queue.log
1578074 /home/yunjung/.venvs/py312/bin/python src/experiment_freespace_sigma.py --drone mini5pro --backend direct --force

## GPU
0, 21125 MiB, 100 %
1, 22180 MiB, 100 %
2, 10638 MiB, 100 %
3, 19986 MiB, 100 %

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
c69539c 0810 라운드14: ⭐⭐광선예산 결판 — 40m 붕괴는 «구조» 가 아니라 **내 예산 부족**이었다 (내 주장 정정)
미커밋 37건
