# RESUME_LIVE — 10분 자동 스냅샷 (수동 편집 금지, 갱신 2026-08-11 04:37:59)

## 프로세스
198615 bash -c for i in $(seq 1 144); do { echo "# RESUME_LIVE — 10분 자동 스냅샷 (수동 편집 금지, 갱신 $(date "+%F %T"))"; echo; echo "## 프로세스"; pgrep -af "report15b_microdoppler_recompute|experiment_freespace_sigma|rcs_same_span|hover_long" || echo "(없음)"; echo; echo "## GPU"; nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader; echo; echo "## 로그 후미"; for f in md15b3_meshfix sigma_force_m4e sigma_force_mini5 samespan sigma_chain; do echo "── $f.log:"; tail -2 /tmp/claude-1015/-workspace/a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad/$f.log 2>/dev/null; done; echo; echo "## git"; git -C /workspace/sionna log --oneline -1; echo "미커밋 $(git -C /workspace/sionna status --porcelain | wc -l)건"; } > /workspace/sionna/docs/RESUME_LIVE.md 2>&1; sleep 600; done
1529606 /workspace/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset indoor --sec 2.0 --tag _ou_indoor --shard 0 --nshards 8
1530066 /workspace/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset indoor --sec 2.0 --tag _ou_indoor --shard 1 --nshards 8
1530725 /workspace/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset indoor --sec 2.0 --tag _ou_indoor --shard 2 --nshards 8
1531301 /workspace/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset indoor --sec 2.0 --tag _ou_indoor --shard 3 --nshards 8
1531827 /workspace/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset indoor --sec 2.0 --tag _ou_indoor --shard 4 --nshards 8
1532402 /workspace/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset indoor --sec 2.0 --tag _ou_indoor --shard 5 --nshards 8
1533025 /workspace/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset indoor --sec 2.0 --tag _ou_indoor --shard 6 --nshards 8
1533604 /workspace/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset indoor --sec 2.0 --tag _ou_indoor --shard 7 --nshards 8
1534210 /workspace/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset outdoor --sec 2.0 --tag _ou_outdoor --shard 0 --nshards 8
1534694 /workspace/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset outdoor --sec 2.0 --tag _ou_outdoor --shard 1 --nshards 8
1535379 /workspace/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset outdoor --sec 2.0 --tag _ou_outdoor --shard 2 --nshards 8
1535944 /workspace/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset outdoor --sec 2.0 --tag _ou_outdoor --shard 3 --nshards 8
1536649 /workspace/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset outdoor --sec 2.0 --tag _ou_outdoor --shard 4 --nshards 8
1537206 /workspace/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset outdoor --sec 2.0 --tag _ou_outdoor --shard 5 --nshards 8
1537701 /workspace/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset outdoor --sec 2.0 --tag _ou_outdoor --shard 6 --nshards 8
1538318 /workspace/.venvs/py312/bin/python -W ignore benchmark/report07_hover_long.py --preset outdoor --sec 2.0 --tag _ou_outdoor --shard 7 --nshards 8

## GPU
0, 20534 MiB, 100 %
1, 19580 MiB, 100 %
2, 21943 MiB, 100 %
3, 22050 MiB, 100 %

## 로그 후미
── md15b3_meshfix.log:
✅ /workspace/sionna/outputs/report15b_microdoppler.json
✅ /workspace/sionna/outputs/report15b_series.npz  (1.8 MB)
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
49439ee ⭐선행연구 조사 완료 + 내 문서 오류 4 건 정정
미커밋 1건
