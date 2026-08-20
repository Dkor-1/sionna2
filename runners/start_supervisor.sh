#!/usr/bin/env bash
# ⭐감독자를 **세션에서 떼어** 띄운다. setsid 없이 & 만 쓰면 호출한 셸이 끝날 때 같이 죽는다.
cd /workspace/sionna
exec setsid /workspace/.venvs/py312/bin/python runners/worker_supervisor.py \
  "${1:-runners/jobs_sup_0819.txt}" "${2:-/workspace/sionna/runners/logs/supervisor.log}" \
  < /dev/null >> "${2:-/workspace/sionna/runners/logs/supervisor.log}.out" 2>&1
