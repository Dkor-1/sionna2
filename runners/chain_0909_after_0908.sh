#!/bin/bash
#: 0908(목요일 덱용) 발주가 다 띄워지고 그 워커가 빠질 때까지 기다렸다가 0909(클러터)를 띄운다.
#  ⛔pgrep -f 를 쓰지 않는다 — 같은 명령줄에 이름이 있으면 제 셸을 죽인다(memory: pgrep-self-kill).
cd /workspace/sionna
until tail -1 runners/logs/sup_jobs_0908.log 2>/dev/null | grep -q "큐 78/78"; do sleep 300; done
sleep 1800                                   # 마지막 워커들이 끝날 시간
setsid nohup /workspace/.venvs/py312/bin/python runners/worker_supervisor.py \
  runners/jobs_0909.txt runners/logs/sup_jobs_0909.log > runners/logs/sup_jobs_0909.boot 2>&1 < /dev/null &
echo "[$(date '+%m-%d %H:%M')] 0909 감독자 띄움" >> runners/logs/chain_0909.log
