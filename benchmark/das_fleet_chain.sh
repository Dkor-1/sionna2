#!/usr/bin/env bash
# das_fleet_chain.sh — 싼 두 기체(mini2·phantom2)가 최종격자를 채우면, 남는 일손을
#   **자동으로 m350rtk 로 돌린다**. (m350rtk 는 한 표본이 16 배 비싸 일손이 가장 아쉬운 곳이다.)
#   ⚠ 새 워커는 m350rtk 전용 사다리(0→1→6→2→3)를 쓴다 — 6=(41 주파수 x 90 방위) 를
#     2 단계(21f x 360az) 앞에 끼워 **방위보다 주파수를 먼저** 채우는 순서다.
set -u
cd /home/yunjung/workspace/sionna2
DIR=outputs/partial/das_fleet_0803
while true; do
  a=$(ls $DIR/mini2/*.json 2>/dev/null | wc -l)
  b=$(ls $DIR/phantom2/*.json 2>/dev/null | wc -l)
  [ "$a" -ge 984 ] && [ "$b" -ge 364 ] && break
  sleep 60
done
echo "[$(date +%H:%M:%S)] mini2·phantom2 완료 → m350rtk 로 일손 이동" >> $DIR/chain.log
~/.venvs/py312/bin/python benchmark/das_fleet_unlock.py >> $DIR/chain.log 2>&1
POOL=c bash benchmark/das_fleet_driver.sh 24 2,3 "m350rtk:0,m350rtk:1,m350rtk:6,m350rtk:2,m350rtk:3"
