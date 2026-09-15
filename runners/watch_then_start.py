#!/usr/bin/env python3
"""Start the next queue once the previous queue has launched every line (generic chain link).

    setsid nohup /workspace/.venvs/py312/bin/python runners/watch_then_start.py \
        --prev-log runners/logs/sup_leftover_0939.log --prev-jobs jobs_0939_leftover.txt \
        --next-jobs runners/jobs_0941_buffer.txt --next-log runners/logs/sup_buffer_0941.log \
        --name 0941 --idle-fallback-min 20 \
        > runners/logs/watch_0941.nohup 2>&1 < /dev/null &

Generalizes runners/watch_0939_after_0940.py (same log parsing, tested 2026-09-15 on five synthetic
logs), and adds an idle fallback for unattended nights:
- Trigger: in the segment of --prev-log after its LAST supervisor start header, the latest status line
  shows "큐 K/N" with K == N. The next supervisor then shares per-card caps with the previous one, so
  the hand-off has no idle gap.
- Idle fallback: if NO worker_supervisor.py and NO elevation_sweep_md.py process has existed for
  --idle-fallback-min consecutive minutes, start the next queue anyway (an earlier link broke and the
  GPUs would otherwise sit empty). 0 disables it.
- Never starts twice: lock file runners/logs/.watch_<name>.started plus a /proc scan for a supervisor
  already running --next-jobs.
- If the previous supervisor ends without launching every line and the idle fallback is disabled, it
  writes the manual start command into runners/logs/watch_<name>.log and exits.
Everything it does is logged to runners/logs/watch_<name>.log.
"""
from __future__ import annotations

import argparse
import os
import re
import time

ROOT = "/workspace/sionna"
PY = "/workspace/.venvs/py312/bin/python"
START_HDR = re.compile(r"큐 \d+ 줄 · 규약")
QUEUE = re.compile(r"큐 (\d+)/(\d+)")
FAILED = re.compile(r"실패 (\d+)")
POLL_S = 30


def _abs(p: str) -> str:
    return p if os.path.isabs(p) else os.path.join(ROOT, p)


def _procs() -> list[list[str]]:
    me = os.getpid()
    out = []
    for d in os.listdir("/proc"):
        if not d.isdigit() or int(d) == me:
            continue
        try:
            args = [a for a in open(f"/proc/{d}/cmdline", "rb").read().decode("utf-8", "replace").split("\0") if a]
        except OSError:
            continue
        if len(args) >= 2 and args[0].endswith("python"):
            out.append(args)
    return out


def supervisors_with(token: str) -> int:
    return sum(1 for a in _procs() if a[1].endswith("worker_supervisor.py") and any(token in x for x in a[2:]))


def anything_running() -> bool:
    for a in _procs():
        if a[1].endswith("worker_supervisor.py"):
            return True
        if a[1].endswith("elevation_sweep_md.py") and "--dry-run" not in a:
            return True
    return False


def latest_segment_state(log: str):
    """(launched, total, failed, ended) for the latest supervisor run in `log`, or None if not started."""
    try:
        lines = open(log, encoding="utf-8", errors="replace").read().splitlines()
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prev-log", required=True)
    ap.add_argument("--prev-jobs", required=True, help="token identifying the previous supervisor's job file")
    ap.add_argument("--next-jobs", required=True)
    ap.add_argument("--next-log", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--idle-fallback-min", type=float, default=20.0)
    a = ap.parse_args()

    prev_log, next_jobs, next_log = _abs(a.prev_log), _abs(a.next_jobs), _abs(a.next_log)
    note_path = _abs(f"runners/logs/watch_{a.name}.log")
    lock = _abs(f"runners/logs/.watch_{a.name}.started")

    def note(msg: str) -> None:
        with open(note_path, "a", encoding="utf-8") as fh:
            fh.write(time.strftime("[%m-%d %H:%M:%S] ") + msg + "\n")

    def start(reason: str) -> None:
        with open(lock, "w", encoding="utf-8") as fh:
            fh.write(f"{time.strftime('%F %T')} {reason}\n")
        note(f"starting {os.path.basename(next_jobs)}: {reason}")
        env = dict(os.environ)
        env["PYTHONPATH"] = "src:benchmark"
        env["DRJIT_LIBOPTIX_PATH"] = "/workspace/.venvs/optix/libnvoptix.so.1"
        env["LD_LIBRARY_PATH"] = "/workspace/.venvs/optix:" + env.get("LD_LIBRARY_PATH", "")
        os.chdir(ROOT)
        os.execve(PY, [PY, "runners/worker_supervisor.py", next_jobs, next_log], env)

    note(f"watcher started (pid {os.getpid()}): prev={a.prev_log} next={a.next_jobs} "
         f"idle_fallback={a.idle_fallback_min} min")
    idle_since = None
    while True:
        if os.path.exists(lock):
            note(f"lock {lock} exists -> already started once; exiting")
            return 0
        if supervisors_with(os.path.basename(next_jobs)):
            note("a supervisor for the next queue is already running -> exiting")
            return 0
        st = latest_segment_state(prev_log)
        if st is not None:
            launched, total, failed, ended = st
            if total is not None and launched == total:
                start(f"previous queue fully launched ({launched}/{total}, failed {failed})")
                return 0
        if a.idle_fallback_min > 0:
            if anything_running():
                idle_since = None
            else:
                idle_since = idle_since or time.time()
                if time.time() - idle_since >= a.idle_fallback_min * 60:
                    start(f"idle fallback: no supervisor or worker for {a.idle_fallback_min:g} min "
                          f"(previous state {st})")
                    return 0
        elif st is not None and st[3] and not supervisors_with(a.prev_jobs):
            note(f"previous supervisor ended at {st[0]}/{st[1]} without launching every line -> not "
                 f"starting. Manual: cd {ROOT} && PYTHONPATH=src:benchmark setsid nohup {PY} "
                 f"runners/worker_supervisor.py {next_jobs} {next_log} > {next_log}.nohup 2>&1 < /dev/null &")
            return 1
        time.sleep(POLL_S)


if __name__ == "__main__":
    raise SystemExit(main())
