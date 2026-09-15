#!/usr/bin/env python3
"""Start the 0939 leftover queue once the 0940 antenna queue has launched every line.

    setsid nohup /workspace/.venvs/py312/bin/python runners/watch_0939_after_0940.py \
        > runners/logs/watch_0939.nohup 2>&1 < /dev/null &

Why this replaces runners/watch_0939_after_0938.sh (review 2026-09-15):
- The shell watcher matched the fixed string "큐 30/30" anywhere in the log and gave up after 24 h,
  writing the give-up only to a nohup file nobody reads. 0939 could silently never start.
- This watcher reads only the segment of the supervisor log after its LAST start header
  ("큐 N 줄 · 규약 ..."), so a restarted supervisor or stale lines cannot trigger it early.
- It triggers on the latest status line showing "큐 K/N" with K == N (every line launched). That keeps
  the hand-off gap-free: 0939 starts while 0940 workers are still running and shares the per-card caps.
- No deadline. If the 0940 supervisor ends without launching every line, it does NOT start 0939 and
  writes the exact command to run by hand into runners/logs/watch_0939.log.
- It will not start 0939 twice: a lock file plus a /proc scan for an existing 0939 supervisor.
- Failed 0940 lines still advance the supervisor index and are not retried; the failure count from the
  status line is written to the watch log at hand-off.
"""
from __future__ import annotations

import os
import re
import time

ROOT = "/workspace/sionna"
PY = "/workspace/.venvs/py312/bin/python"
LOG = f"{ROOT}/runners/logs/sup_antenna_0940.log"
JOBS_NEXT = f"{ROOT}/runners/jobs_0939_leftover.txt"
LOG_NEXT = f"{ROOT}/runners/logs/sup_leftover_0939.log"
NOTE = f"{ROOT}/runners/logs/watch_0939.log"
LOCK = f"{ROOT}/runners/logs/.watch_0939.started"
POLL_S = 30
START_HDR = re.compile(r"큐 \d+ 줄 · 규약")
QUEUE = re.compile(r"큐 (\d+)/(\d+)")
FAILED = re.compile(r"실패 (\d+)")


def note(msg: str) -> None:
    with open(NOTE, "a", encoding="utf-8") as fh:
        fh.write(time.strftime("[%m-%d %H:%M:%S] ") + msg + "\n")


def supervisors_with(token: str) -> list[int]:
    """PIDs of worker_supervisor.py processes whose command line contains `token`.
    Scans /proc directly (pgrep -f would match this script's own command line)."""
    me = os.getpid()
    out = []
    for d in os.listdir("/proc"):
        if not d.isdigit() or int(d) == me:
            continue
        try:
            args = [a for a in open(f"/proc/{d}/cmdline", "rb").read().decode("utf-8", "replace").split("\0") if a]
        except OSError:
            continue
        if len(args) >= 2 and args[0].endswith("python") and args[1].endswith("worker_supervisor.py") \
                and any(token in a for a in args[2:]):
            out.append(int(d))
    return out


def latest_segment_state():
    """(launched, total, failed, ended) for the latest supervisor run in LOG, or None if not started."""
    try:
        lines = open(LOG, encoding="utf-8", errors="replace").read().splitlines()
    except OSError:
        return None
    starts = [i for i, ln in enumerate(lines) if START_HDR.search(ln)]
    if not starts:
        return None
    seg = lines[starts[-1]:]
    status = [ln for ln in seg if "상태 " in ln and QUEUE.search(ln)]
    ended = any("== 종료" in ln for ln in seg)
    if not status:
        return (0, None, 0, ended)
    m = QUEUE.search(status[-1])
    f = FAILED.search(status[-1])
    return (int(m.group(1)), int(m.group(2)), int(f.group(1)) if f else 0, ended)


def start_next(launched: int, total: int, failed: int) -> None:
    with open(LOCK, "w", encoding="utf-8") as fh:
        fh.write(f"{time.strftime('%F %T')} 0940 {launched}/{total} failed {failed}\n")
    note(f"0940 launched every line ({launched}/{total}, failed {failed}) -> starting 0939")
    env = dict(os.environ)
    env["PYTHONPATH"] = "src:benchmark"
    env["DRJIT_LIBOPTIX_PATH"] = "/workspace/.venvs/optix/libnvoptix.so.1"
    env["LD_LIBRARY_PATH"] = "/workspace/.venvs/optix:" + env.get("LD_LIBRARY_PATH", "")
    os.chdir(ROOT)
    os.execve(PY, [PY, "runners/worker_supervisor.py", JOBS_NEXT, LOG_NEXT], env)


def main() -> int:
    note(f"watcher started (pid {os.getpid()}), waiting for 0940 to launch every line")
    while True:
        if os.path.exists(LOCK):
            note(f"lock {LOCK} exists -> 0939 was already started once; exiting")
            return 0
        if supervisors_with("jobs_0939_leftover.txt"):
            note("a 0939 supervisor is already running -> exiting")
            return 0
        st = latest_segment_state()
        if st is not None:
            launched, total, failed, ended = st
            if total is not None and launched == total:
                start_next(launched, total, failed)
                return 0                                   # not reached: execve replaces us
            if ended and not supervisors_with("jobs_0940_antenna.txt"):
                note(f"0940 supervisor ended at {launched}/{total} (failed {failed}) without launching "
                     f"every line -> NOT starting 0939. Start it by hand:\n"
                     f"    cd {ROOT} && PYTHONPATH=src:benchmark setsid nohup {PY} runners/worker_supervisor.py "
                     f"{JOBS_NEXT} {LOG_NEXT} > {LOG_NEXT}.nohup 2>&1 < /dev/null &")
                return 1
        time.sleep(POLL_S)


if __name__ == "__main__":
    raise SystemExit(main())
