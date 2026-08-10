# RESUME_LIVE — 10분 자동 스냅샷 (수동 편집 금지, 갱신 2026-08-10 05:17:06)

## 프로세스
84448 /home/yunjung/.venvs/py312/bin/python benchmark/rcs_same_span_sweep.py
101312 /home/yunjung/.venvs/py312/bin/python src/experiment_freespace_sigma.py --drone matrice4e --backend direct --force
198615 bash -c for i in $(seq 1 144); do { echo "# RESUME_LIVE — 10분 자동 스냅샷 (수동 편집 금지, 갱신 $(date "+%F %T"))"; echo; echo "## 프로세스"; pgrep -af "report15b_microdoppler_recompute|experiment_freespace_sigma|rcs_same_span|hover_long" || echo "(없음)"; echo; echo "## GPU"; nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader; echo; echo "## 로그 후미"; for f in md15b3_meshfix sigma_force_m4e sigma_force_mini5 samespan sigma_chain; do echo "── $f.log:"; tail -2 /tmp/claude-1015/-home-yunjung-workspace/a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad/$f.log 2>/dev/null; done; echo; echo "## git"; git -C /home/yunjung/workspace/sionna2 log --oneline -1; echo "미커밋 $(git -C /home/yunjung/workspace/sionna2 status --porcelain | wc -l)건"; } > /home/yunjung/workspace/sionna2/docs/RESUME_LIVE.md 2>&1; sleep 600; done

## GPU
0, 20169 MiB, 100 %
1, 23052 MiB, 100 %
2, 10111 MiB, 0 %
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
  DJI Matrice 4E    14.5 GHz  mu  -14.22 dBsm  (2790s)
  DJI Matrice 4E    15.0 GHz  mu  -14.58 dBsm  (3086s)
── sigma_chain.log:
SIGMA_CHAIN_DONE 05:01:18
HOVER_OUTDOOR_DONE 05:07:07

## git
676e448 0810 스프린트: Γ(θ) PO팔 배선·mini5pro 메쉬 무관통 수정·진짜 모노스태틱 거리스윕(3/10/20/40m)·5G파형 4팔·HQ렌더·report15b 재계산(±0.22%)·적대적검증 6부·덱 v2
미커밋 113건
