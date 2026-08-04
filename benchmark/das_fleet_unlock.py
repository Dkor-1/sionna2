# -*- coding: utf-8 -*-
"""das_fleet_unlock.py — 죽은 워커가 남긴 잠금파일을 회수한다.

잠금파일에는 만든 워커의 PID 가 들어 있다. 그 PID 가 이미 없으면(워커가 죽었거나 내가
GPU 여유를 보고 줄였으면) 그 작업은 아무도 하고 있지 않다 → 잠금을 지워 다시 잡히게 한다.
결과 파일이 이미 있는 잠금도 지운다."""
import os, sys, glob
P = "/home/yunjung/workspace/sionna2/outputs/partial/das_fleet_0803"
alive = lambda pid: os.path.exists(f"/proc/{pid}")
n = 0
for lk in glob.glob(os.path.join(P, "*", "*.lock")):
    tgt = lk[:-5]
    try:
        pid = int(open(lk).read().strip() or -1)
    except Exception:
        pid = -1
    if os.path.exists(tgt) or pid < 0 or not alive(pid):
        os.remove(lk); n += 1
print(f"회수한 잠금 {n} 개")
