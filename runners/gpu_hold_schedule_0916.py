#!/usr/bin/env python3
"""Keep GPUs 0 and 1 free by 08:00 KST on 2026-09-16, then return to the GPU 3·4-only hold (user windows).

    setsid nohup /workspace/.venvs/py312/bin/python runners/gpu_hold_schedule_0916.py \
        > runners/logs/gpu_hold_schedule_0916.nohup 2>&1 < /dev/null &

User, 2026-09-16 00:57 KST: 「우선 한국시간 기준으로 아침 9시정도까지 GPU 1번 사용하고 그 이후 다시 3,4번만
사용하는 형태로 작업 들어가줘!」 [use GPU 1 until about 09:00 KST, then GPUs 3 and 4 only again].
User, 2026-09-16 about 01:05 KST: 「오전 8시까지는 GPU 2번도 사용하는 형태로 부탁해!」 [also use GPU 2 until 08:00 KST].
User, 2026-09-16 ~01:25 KST: 「GPU 2번 사용은 지금 당장 멈추도록 해주고, 1번 사용 중지 시점도 8시로 땡겨줘」 [stop GPU 2 now; GPU 1
should stop at 08:00]. GPU 2 was held again by hand at once.
User, 2026-09-16 ~01:50 KST: 「오전 8시까지 GPU 0번도 사용하는걸로 해줘!」 [also use GPU 0 until 08:00 KST]. GPU 0 released at once.
User, 2026-09-16 ~01:55 KST: 「새 발주는 03:50 KST 면 너무 이른거 아닌가? 8시쯤에 비워지려면 저렇게 빨리 멈춰야하니?」
[isn't 03:50 too early for new launches? must they stop that early to be free around 08:00?].

A hold blocks new launches only. Jobs measured so far: street canyon about 225 min per shard (3.3 s x 4,096 poses),
ground cells 65-110 min, free sky about 40 min, low-ray deterministic-mode cells shorter. So the cut-off depends on
the job:
  - before 03:50 KST: GPUs 0 and 1 open;
  - 03:50-06:10 KST: GPUs 0 and 1 held only while a running supervisor has a "long" line (street canyon or depth 3)
    among its next 3 unlaunched lines. A supervisor can launch several lines on one card in one round
    (worker_supervisor.py: `while cur < tgt[g]`), so the next 3 lines are checked, not just the next one;
  - from 06:10 KST: GPUs 0 and 1 held for good; the script exits.
Every 20 s it reads the running supervisors from `ps -eo args` (job file and log path from the command line), the
position `큐 i/N` from each log's latest status line after its last start header, and the job file with the same
filter the supervisor uses. It changes only cards 0 and 1 in "gpus" of runners/GPU_HOLD.json (temporary file plus
os.replace), keeps the other keys, and logs every change to runners/logs/gpu_hold_schedule_0916.log. Supervisors
re-read the hold file each round (about 30 s).
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import subprocess
import time

ROOT = "/workspace/sionna"
HOLD = f"{ROOT}/runners/GPU_HOLD.json"
LOG = f"{ROOT}/runners/logs/gpu_hold_schedule_0916.log"
CARDS = (0, 1)
T_LONG_ONLY = dt.datetime(2026, 9, 15, 18, 50, 0, tzinfo=dt.timezone.utc)   # 2026-09-16 03:50 KST
T_ALL = dt.datetime(2026, 9, 15, 21, 10, 0, tzinfo=dt.timezone.utc)         # 2026-09-16 06:10 KST
LOOKAHEAD = 3
LONG = re.compile(r"simple_street_canyon|--max-depth[ =]3\b")


def note(msg: str) -> None:
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(dt.datetime.now(dt.timezone.utc).strftime("[%Y-%m-%dT%H:%M:%SZ] ") + msg + "\n")


def job_lines(path: str) -> list[str]:
    return [l.strip() for l in open(path, encoding="utf-8")
            if l.strip() and not l.strip().startswith("#") and not l.strip().startswith("--help")]


def position(log_path: str) -> int | None:
    """Launched-line count from the latest status line after the last start header, or None if unreadable."""
    try:
        text = open(log_path, encoding="utf-8").read().splitlines()
    except OSError:
        return None
    start = max((k for k, l in enumerate(text) if re.search(r"큐 \d+ 줄 · 규약", l)), default=None)
    if start is None:
        return None
    for l in reversed(text[start:]):
        m = re.search(r"큐 (\d+)/(\d+)", l)
        if m:
            return int(m.group(1))
    return 0


def pending_long() -> list[str]:
    out = subprocess.run(["ps", "-eo", "args"], capture_output=True, text=True).stdout.splitlines()
    found = []
    for args in out:
        parts = args.split()
        if len(parts) < 4 or not parts[1].endswith("runners/worker_supervisor.py"):
            continue
        jobs, log = parts[2], parts[3]
        jobs = jobs if os.path.isabs(jobs) else os.path.join(ROOT, jobs)
        log = log if os.path.isabs(log) else os.path.join(ROOT, log)
        try:
            lines = job_lines(jobs)
        except OSError:
            found.append(f"{jobs}: unreadable job file")
            continue
        i = position(log)
        if i is None:
            found.append(f"{log}: position unknown")          # unknown counts as long: hold (safe side)
            continue
        nxt = lines[i:i + LOOKAHEAD]
        if any(LONG.search(l) for l in nxt):
            found.append(f"{os.path.basename(jobs)} at {i}/{len(lines)}")
    return found


def set_cards(hold: bool, why: str) -> None:
    d = json.load(open(HOLD, encoding="utf-8"))
    before = list(d.get("gpus") or [])
    after = sorted(set(before) | set(CARDS)) if hold else sorted(set(before) - set(CARDS))
    if after == before:
        return
    d["gpus"] = after
    if hold and after == [0, 1, 2] and why == "06:10 KST":
        d["note"] = "임시 규약 — GPU 3·4 만 쓴다 (2026-09-15); the GPU 0/1/2 windows of 2026-09-16 have ended"
    tmp = HOLD + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(d, ensure_ascii=False, indent=2) + "\n")
    os.replace(tmp, HOLD)
    note(f"{'held' if hold else 'released'} GPUs {list(CARDS)} ({why}): gpus {before} -> {after}")


def main() -> int:
    note(f"scheduler started (pid {os.getpid()}); long-line rule from {T_LONG_ONLY.isoformat()}, "
         f"all new launches on GPUs {list(CARDS)} stop at {T_ALL.isoformat()}")
    last = None
    while True:
        now = dt.datetime.now(dt.timezone.utc)
        if now >= T_ALL:
            set_cards(True, "06:10 KST")
            note("final hold written; exiting")
            return 0
        if now >= T_LONG_ONLY:
            found = pending_long()
            hold = bool(found)
            why = ("long line within the next 3: " + "; ".join(found)) if found else "no long line pending"
        else:
            hold, why = False, "before 03:50 KST"
        if (hold, why) != last:
            set_cards(hold, why)
            if last is None or last[0] != hold:
                note(f"state: hold={hold} ({why})")
            last = (hold, why)
        time.sleep(20)


if __name__ == "__main__":
    raise SystemExit(main())
