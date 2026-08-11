# RESUME_LIVE — 10분 자동 스냅샷 (수동 편집 금지, 갱신 2026-08-11 03:27:56)

## 프로세스
198615 bash -c for i in $(seq 1 144); do { echo "# RESUME_LIVE — 10분 자동 스냅샷 (수동 편집 금지, 갱신 $(date "+%F %T"))"; echo; echo "## 프로세스"; pgrep -af "report15b_microdoppler_recompute|experiment_freespace_sigma|rcs_same_span|hover_long" || echo "(없음)"; echo; echo "## GPU"; nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader; echo; echo "## 로그 후미"; for f in md15b3_meshfix sigma_force_m4e sigma_force_mini5 samespan sigma_chain; do echo "── $f.log:"; tail -2 /tmp/claude-1015/-home-yunjung-workspace/a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad/$f.log 2>/dev/null; done; echo; echo "## git"; git -C /home/yunjung/workspace/sionna2 log --oneline -1; echo "미커밋 $(git -C /home/yunjung/workspace/sionna2 status --porcelain | wc -l)건"; } > /home/yunjung/workspace/sionna2/docs/RESUME_LIVE.md 2>&1; sleep 600; done
1261774 /home/yunjung/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset legacy --sec 2.0 --tag _ou_legacy --shard 0 --nshards 8
1262263 /home/yunjung/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset legacy --sec 2.0 --tag _ou_legacy --shard 1 --nshards 8
1262873 /home/yunjung/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset legacy --sec 2.0 --tag _ou_legacy --shard 2 --nshards 8
1263374 /home/yunjung/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset legacy --sec 2.0 --tag _ou_legacy --shard 3 --nshards 8
1263980 /home/yunjung/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset legacy --sec 2.0 --tag _ou_legacy --shard 4 --nshards 8
1264490 /home/yunjung/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset legacy --sec 2.0 --tag _ou_legacy --shard 5 --nshards 8
1265012 /home/yunjung/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset legacy --sec 2.0 --tag _ou_legacy --shard 6 --nshards 8
1265563 /home/yunjung/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset legacy --sec 2.0 --tag _ou_legacy --shard 7 --nshards 8
1266069 /home/yunjung/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset sitl --sec 2.0 --tag _ou_sitl --shard 0 --nshards 8
1267832 /home/yunjung/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset sitl --sec 2.0 --tag _ou_sitl --shard 1 --nshards 8
1270370 /home/yunjung/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset sitl --sec 2.0 --tag _ou_sitl --shard 2 --nshards 8
1272890 /home/yunjung/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset sitl --sec 2.0 --tag _ou_sitl --shard 3 --nshards 8
1275014 /home/yunjung/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset sitl --sec 2.0 --tag _ou_sitl --shard 4 --nshards 8
1276442 /home/yunjung/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset sitl --sec 2.0 --tag _ou_sitl --shard 5 --nshards 8
1276906 /home/yunjung/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset sitl --sec 2.0 --tag _ou_sitl --shard 6 --nshards 8
1277376 /home/yunjung/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset sitl --sec 2.0 --tag _ou_sitl --shard 7 --nshards 8

## GPU
0, 18041 MiB, 100 %
1, 23304 MiB, 100 %
2, 21550 MiB, 100 %
3, 17955 MiB, 100 %

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
93e947c ⭐⭐시드 사다리 8 판 + 탐지 축 판정 — 내 수치 두 개 정정
미커밋 30건
