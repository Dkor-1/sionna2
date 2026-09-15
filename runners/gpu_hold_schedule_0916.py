#!/usr/bin/env python3
"""Restore the GPU 3·4-only hold in two steps (user windows for GPU 2 and GPU 1, 2026-09-16).

    setsid nohup /workspace/.venvs/py312/bin/python runners/gpu_hold_schedule_0916.py \
        > runners/logs/gpu_hold_schedule_0916.nohup 2>&1 < /dev/null &

User, 2026-09-16 00:57 KST: 「우선 한국시간 기준으로 아침 9시정도까지 GPU 1번 사용하고 그 이후 다시 3,4번만
사용하는 형태로 작업 들어가줘!」 [use GPU 1 until about 09:00 KST, then GPUs 3 and 4 only again].
A hold stops new launches only, and one job in queue 0940 took 47-110 min, so new launches on GPU 1 stop at
07:30 KST (2026-09-15T22:30:00Z) and workers already there finish around 09:00.

User, 2026-09-16 about 01:05 KST: 「오전 8시까지는 GPU 2번도 사용하는 형태로 부탁해!」 [also use GPU 2 until 08:00 KST].
Same reasoning: new launches on GPU 2 stop at 06:30 KST (2026-09-15T21:30:00Z).
User, 2026-09-16 ~01:25 KST: 「GPU 2번 사용은 지금 당장 멈추도록 해주고, 1번 사용 중지 시점도 8시로 땡겨줘」 [stop GPU 2 now; GPU 1
should stop at 08:00]. GPU 2 was held again by hand at once; GPU 1 new launches now stop at 06:10 KST (2026-09-15T21:10:00Z).
User, 2026-09-16 ~01:50 KST: 「오전 8시까지 GPU 0번도 사용하는걸로 해줘!」 [also use GPU 0 until 08:00 KST]. GPU 0 was released
at once. Queue 0941's remaining lines are street-canyon jobs of about 225 min per shard, longer than the 110 min assumed
above, so new launches on GPUs 0 and 1 stop at 03:50 KST (2026-09-15T18:50:00Z).

At each step this script adds the card to "gpus" in runners/GPU_HOLD.json (temporary file plus os.replace), keeps the
other keys, and records what it replaced in runners/logs/gpu_hold_schedule_0916.log; after the last step the file
holds [0, 1, 2] and the script exits. Every running supervisor re-reads the file on its next round (about 30 s); no
restart is needed. A card already held is only logged.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import time

ROOT = "/workspace/sionna"
HOLD = f"{ROOT}/runners/GPU_HOLD.json"
LOG = f"{ROOT}/runners/logs/gpu_hold_schedule_0916.log"
STEPS = [  # (UTC time, card to hold again)
    # GPU 2 was held again at once on 2026-09-16 ~01:25 KST (user: stop GPU 2 now).
    # GPU 0 released ~01:50 KST (user: use GPU 0 until 08:00). Queue 0941's remaining lines are street-canyon jobs
    # (~225 min per shard), so both cards stop new launches at 03:50 KST instead of 06:10.
    (dt.datetime(2026, 9, 15, 18, 50, 0, tzinfo=dt.timezone.utc), 0),   # 2026-09-16 03:50 KST -> free by 08:00
    (dt.datetime(2026, 9, 15, 18, 50, 0, tzinfo=dt.timezone.utc), 1),   # 2026-09-16 03:50 KST -> free by 08:00
]


def note(msg: str) -> None:
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(dt.datetime.now(dt.timezone.utc).strftime("[%Y-%m-%dT%H:%M:%SZ] ") + msg + "\n")


def hold_card(card: int) -> None:
    d = json.load(open(HOLD, encoding="utf-8"))
    before = list(d.get("gpus") or [])
    if card in before:
        note(f"GPU_HOLD.json already holds GPU {card} (gpus={before}); nothing to do")
        return
    d["gpus"] = sorted(set(before) | {card})
    if d["gpus"] == [0, 1, 2]:
        d["note"] = "임시 규약 — GPU 3·4 만 쓴다 (2026-09-15); the GPU 1/2 windows of 2026-09-16 have ended"
    tmp = HOLD + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(d, ensure_ascii=False, indent=2) + "\n")
    os.replace(tmp, HOLD)
    note(f"held GPU {card}: gpus {before} -> {d['gpus']}")


def main() -> int:
    note(f"scheduler started (pid {os.getpid()}); steps " + ", ".join(f"GPU {c} at {t.isoformat()}" for t, c in STEPS))
    for target, card in STEPS:
        while True:
            left = (target - dt.datetime.now(dt.timezone.utc)).total_seconds()
            if left <= 0:
                break
            time.sleep(min(60.0, left))
        hold_card(card)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
