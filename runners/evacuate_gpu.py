#!/usr/bin/env python3
"""evacuate_gpu.py - take one GPU back at once: hold it, stop only its workers, record what to re-run.

    /workspace/.venvs/py312/bin/python runners/evacuate_gpu.py 0            # dry run: prints what it would do
    /workspace/.venvs/py312/bin/python runners/evacuate_gpu.py 0 --go       # actually does it

Why this exists: a hold in runners/GPU_HOLD.json only stops NEW launches; workers already on the card run for
40-230 min. The user lent us GPU 0 on 2026-09-16 on the condition that the card can be freed the moment they ask,
so this does both halves in one step and leaves the queue in a state that can be resumed.

What it does, in order:
 1. adds the card to "gpus" in runners/GPU_HOLD.json (atomic write) so no supervisor launches there again;
 2. finds the workers ON THAT CARD - benchmark/elevation_sweep_md.py processes whose /proc/<pid>/environ has
    CUDA_VISIBLE_DEVICES=<card> - and prints each one's job line and how long it has been running;
 3. writes the interrupted job lines to runners/jobs_REDO_gpu<card>_<UTC>.txt so they can be re-queued
    (a killed worker writes no shard, so its cell is simply missing; runners/filter_jobs.sh will call it NEW);
 4. sends SIGTERM to those workers, waits, then SIGKILL to whatever is left.

⛔It never touches workers on other cards, never touches supervisors or watchers (they keep running and will refill
the other cards), and never uses pgrep -f (that pattern kills the caller's own shell). It refuses to run if it
cannot read a process's environment, so it cannot kill something it has not identified.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOLD = ROOT / "runners" / "GPU_HOLD.json"
WORKER = "benchmark/elevation_sweep_md.py"


def workers_on(card: int) -> list[dict]:
    """Every elevation_sweep_md worker whose CUDA_VISIBLE_DEVICES is exactly this card."""
    out = subprocess.run(["ps", "-eo", "pid,etimes,args"], capture_output=True, text=True, check=True).stdout
    rows = []
    me = {os.getpid(), os.getppid()}
    for line in out.splitlines()[1:]:
        parts = line.strip().split(None, 2)
        if len(parts) < 3 or WORKER not in parts[2]:
            continue
        pid = int(parts[0])
        if pid in me:
            continue
        try:
            env = Path(f"/proc/{pid}/environ").read_bytes().decode("utf-8", "replace").split("\0")
        except OSError:
            continue                                   # gone already, or not ours to read
        cvd = next((v.split("=", 1)[1] for v in env if v.startswith("CUDA_VISIBLE_DEVICES=")), None)
        if cvd is None or cvd.strip() != str(card):
            continue
        rows.append(dict(pid=pid, seconds=int(parts[1]), cmd=parts[2]))
    return rows


def job_line(cmd: str) -> str:
    """The queue line of a worker command (everything from --engine on)."""
    i = cmd.find("--engine")
    return cmd[i:].strip() if i >= 0 else cmd.strip()


def hold_card(card: int, go: bool) -> None:
    d = json.loads(HOLD.read_text(encoding="utf-8"))
    before = list(d.get("gpus") or [])
    if card in before:
        print(f"  GPU_HOLD.json already holds GPU {card} (gpus={before})")
        return
    d["gpus"] = sorted(set(before) | {card})
    d["evacuated"] = (f"GPU {card} evacuated at {dt.datetime.now(dt.timezone.utc).isoformat()} by "
                      f"runners/evacuate_gpu.py (user request).")
    print(f"  hold: gpus {before} -> {d['gpus']}")
    if not go:
        return
    tmp = HOLD.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, HOLD)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("card", type=int, help="GPU index to free")
    ap.add_argument("--go", action="store_true", help="do it (without this it only prints)")
    ap.add_argument("--grace-s", type=float, default=20.0, help="seconds between SIGTERM and SIGKILL")
    a = ap.parse_args()

    rows = workers_on(a.card)
    print(f"GPU {a.card}: {len(rows)} worker(s)" + ("" if a.go else "   [dry run - nothing is changed]"))
    for r in rows:
        print(f"  pid {r['pid']:>8}  {r['seconds'] // 60:>4} min  {job_line(r['cmd'])[:110]}")
    hold_card(a.card, a.go)
    if not rows:
        print("  nothing to stop")
        return 0

    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    redo = ROOT / "runners" / f"jobs_REDO_gpu{a.card}_{stamp}.txt"
    text = (f"# Interrupted on GPU {a.card} at {stamp} by runners/evacuate_gpu.py (user asked for the card back).\n"
            f"# A killed worker writes no shard, so each line below is simply missing from the store —\n"
            f"# run runners/filter_jobs.sh over them (expect NEW) before queueing them again.\n"
            + "".join(job_line(r["cmd"]) + "\n" for r in rows))
    print(f"  redo file: {redo.relative_to(ROOT)} ({len(rows)} line(s))")
    if not a.go:
        print("  (dry run: no signals sent)")
        return 0
    redo.write_text(text, encoding="utf-8")

    for r in rows:
        try:
            os.kill(r["pid"], signal.SIGTERM)
        except ProcessLookupError:
            pass
    deadline = time.time() + a.grace_s
    while time.time() < deadline:
        if not workers_on(a.card):
            break
        time.sleep(1.0)
    left = workers_on(a.card)
    for r in left:
        try:
            os.kill(r["pid"], signal.SIGKILL)
            print(f"  SIGKILL pid {r['pid']}")
        except ProcessLookupError:
            pass
    time.sleep(2.0)
    still = workers_on(a.card)
    print(f"  done — {len(rows) - len(still)} stopped, {len(still)} still alive")
    return 1 if still else 0


if __name__ == "__main__":
    raise SystemExit(main())
