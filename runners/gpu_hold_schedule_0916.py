#!/usr/bin/env python3
"""Restore the GPU 3·4-only hold at a fixed time (user window for GPU 1, 2026-09-16).

    setsid nohup /workspace/.venvs/py312/bin/python runners/gpu_hold_schedule_0916.py \
        > runners/logs/gpu_hold_schedule_0916.nohup 2>&1 < /dev/null &

User, 2026-09-16 00:57 KST: 「우선 한국시간 기준으로 아침 9시정도까지 GPU 1번 사용하고 그 이후 다시 3,4번만
사용하는 형태로 작업 들어가줘!」 [use GPU 1 until about 09:00 KST, then GPUs 3 and 4 only again].
A hold stops new launches only, and one job in queue 0940 took 47-110 min, so new launches on GPU 1 stop at
07:30 KST (2026-09-15T22:30:00Z) and workers already there finish around 09:00.

At the target time this script sets "gpus" in runners/GPU_HOLD.json back to [0, 1, 2] (temporary file plus
os.replace), keeps the other keys, records what it replaced in runners/logs/gpu_hold_schedule_0916.log, and exits.
Every running supervisor re-reads the file on its next round (about 30 s); no restart is needed.
If the file already holds 1 (someone restored it earlier), it only logs that and exits.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import time

ROOT = "/workspace/sionna"
HOLD = f"{ROOT}/runners/GPU_HOLD.json"
LOG = f"{ROOT}/runners/logs/gpu_hold_schedule_0916.log"
TARGET_UTC = dt.datetime(2026, 9, 15, 22, 30, 0, tzinfo=dt.timezone.utc)   # 2026-09-16 07:30 KST


def note(msg: str) -> None:
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(dt.datetime.now(dt.timezone.utc).strftime("[%Y-%m-%dT%H:%M:%SZ] ") + msg + "\n")


def main() -> int:
    note(f"scheduler started (pid {os.getpid()}); will restore gpus [0, 1, 2] at {TARGET_UTC.isoformat()}")
    while True:
        left = (TARGET_UTC - dt.datetime.now(dt.timezone.utc)).total_seconds()
        if left <= 0:
            break
        time.sleep(min(60.0, left))
    d = json.load(open(HOLD, encoding="utf-8"))
    before = d.get("gpus")
    if isinstance(before, list) and 1 in before:
        note(f"GPU_HOLD.json already holds GPU 1 (gpus={before}); nothing to do")
        return 0
    d["gpus"] = [0, 1, 2]
    d["note"] = "임시 규약 — GPU 3·4 만 쓴다 (2026-09-15); the GPU 1 window of 2026-09-16 ended at 07:30 KST"
    tmp = HOLD + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(d, ensure_ascii=False, indent=2) + "\n")
    os.replace(tmp, HOLD)
    note(f"restored gpus {before} -> [0, 1, 2]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
