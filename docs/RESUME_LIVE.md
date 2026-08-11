# RESUME_LIVE — 10분 자동 스냅샷 (수동 편집 금지, 갱신 2026-08-11 04:27:59)

## 프로세스
198615 bash -c for i in $(seq 1 144); do { echo "# RESUME_LIVE — 10분 자동 스냅샷 (수동 편집 금지, 갱신 $(date "+%F %T"))"; echo; echo "## 프로세스"; pgrep -af "report15b_microdoppler_recompute|experiment_freespace_sigma|rcs_same_span|hover_long" || echo "(없음)"; echo; echo "## GPU"; nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader; echo; echo "## 로그 후미"; for f in md15b3_meshfix sigma_force_m4e sigma_force_mini5 samespan sigma_chain; do echo "── $f.log:"; tail -2 /tmp/claude-1015/-home-yunjung-workspace/a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad/$f.log 2>/dev/null; done; echo; echo "## git"; git -C /home/yunjung/workspace/sionna2 log --oneline -1; echo "미커밋 $(git -C /home/yunjung/workspace/sionna2 status --porcelain | wc -l)건"; } > /home/yunjung/workspace/sionna2/docs/RESUME_LIVE.md 2>&1; sleep 600; done
1529606 /home/yunjung/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset indoor --sec 2.0 --tag _ou_indoor --shard 0 --nshards 8
1530066 /home/yunjung/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset indoor --sec 2.0 --tag _ou_indoor --shard 1 --nshards 8
1530725 /home/yunjung/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset indoor --sec 2.0 --tag _ou_indoor --shard 2 --nshards 8
1531301 /home/yunjung/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset indoor --sec 2.0 --tag _ou_indoor --shard 3 --nshards 8
1531827 /home/yunjung/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset indoor --sec 2.0 --tag _ou_indoor --shard 4 --nshards 8
1532402 /home/yunjung/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset indoor --sec 2.0 --tag _ou_indoor --shard 5 --nshards 8
1533025 /home/yunjung/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset indoor --sec 2.0 --tag _ou_indoor --shard 6 --nshards 8
1533604 /home/yunjung/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset indoor --sec 2.0 --tag _ou_indoor --shard 7 --nshards 8
1534210 /home/yunjung/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset outdoor --sec 2.0 --tag _ou_outdoor --shard 0 --nshards 8
1534694 /home/yunjung/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset outdoor --sec 2.0 --tag _ou_outdoor --shard 1 --nshards 8
1535379 /home/yunjung/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset outdoor --sec 2.0 --tag _ou_outdoor --shard 2 --nshards 8
1535944 /home/yunjung/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset outdoor --sec 2.0 --tag _ou_outdoor --shard 3 --nshards 8
1536649 /home/yunjung/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset outdoor --sec 2.0 --tag _ou_outdoor --shard 4 --nshards 8
1537206 /home/yunjung/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset outdoor --sec 2.0 --tag _ou_outdoor --shard 5 --nshards 8
1537701 /home/yunjung/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset outdoor --sec 2.0 --tag _ou_outdoor --shard 6 --nshards 8
1538318 /home/yunjung/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset outdoor --sec 2.0 --tag _ou_outdoor --shard 7 --nshards 8

## GPU
0, 23952 MiB, 100 %
1, 23228 MiB, 100 %
2, 21943 MiB, 100 %
3, 22050 MiB, 99 %

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
fd1c45f 로터 2 초 맵 샤딩 배선 + 시드 사다리 산출물
미커밋 30건
