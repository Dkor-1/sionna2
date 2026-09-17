#!/usr/bin/env python
"""hold_window.py — lend a card for a while and take it back in time, without killing anything.

The user lends a card until a wall-clock time. A hold blocks **new launches only**, so to have the
card actually free at that time the hold has to go back on early enough for whatever is already
running there to finish. How early depends on what the queue is still launching:

    a street-canyon shard is about 225 min · a ground shard about 95 min (measured 2026-09-16)

So the cutoff is not one number. While canyon lines are still waiting to launch, the card is taken
back at `free_at − 225 min − margin`; once every canyon line in the watched queues has been launched,
the only thing that can start is a ground line and the cutoff moves out to `free_at − 95 min − margin`.
The watcher re-checks every minute and edits only the `gpus` list of runners/GPU_HOLD.json.

⛔It never stops a worker. Taking a card back from running work is runners/evacuate_gpu.py, and that
  needs the user to ask.
⛔It never touches any other card's hold, and it leaves the file's notes alone.

    nohup .../python runners/hold_window.py --card 1 --free-at 08:00 \
        --queue runners/jobs_0948_survivors_and_angles.txt \
        --queue runners/jobs_0949_antenna_by_angle.txt \
        --log runners/logs/hold_window_gpu1.log &
"""
import argparse
import contextlib
import datetime as dt
import fcntl
import json
import glob
import os
import re
import time

HERE = os.path.dirname(os.path.abspath(__file__))
HOLD = os.path.join(HERE, "GPU_HOLD.json")
#: ⭐one lock per hold file. More than one window can be open at a time (0, 1 and 2 have each been
#  lent on the same night), and every one of them does a read-modify-write of the same `gpus` list.
#  Without this, two watchers that tick in the same second can lose one card's change — and a hold
#  that quietly disappears is the failure this file exists to prevent.
LOCK = os.path.join(HERE, ".gpu_hold.lock")


@contextlib.contextmanager
def hold_lock():
    with open(LOCK, "a+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
KST = dt.timezone(dt.timedelta(hours=9))

CANYON = "street_canyon"
MIN_CANYON = 225          # measured: 3.3 s x 4,096 rotor positions
MIN_GROUND = 95           # measured 2026-09-16: median 92, max 97 over 8 shards


def say(path, msg):
    line = f"[{dt.datetime.now(KST):%m-%d %H:%M}] {msg}"
    print(line, flush=True)
    if path:
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass


def pending_canyon(queues):
    """Canyon lines that have not been launched yet, counted from the supervisors' own logs.

    ⚠Kept for the old call pattern only. It never counted a launch: the supervisor logs a launch as
    `line[:88]`, which ends before `--env`, so `CANYON in l` was never true on a «띄움» line and this
    always returned the total (a conservative cutoff). pending_lines() below reads the supervisor's
    own `큐 i/N` counter instead (added 2026-09-17).
    """
    total = launched = 0
    for q in queues:
        try:
            lines = [l for l in open(q, encoding="utf-8")
                     if l.strip() and not l.lstrip().startswith("#")]
        except OSError:
            continue
        total += sum(1 for l in lines if CANYON in l)
        log = os.path.join(HERE, "logs", "sup_" + os.path.basename(q).split("_")[1] + ".log")
        try:
            launched += sum(1 for l in open(log, encoding="utf-8", errors="replace")
                            if "띄움" in l and CANYON in l)
        except OSError:
            pass
    return max(total - launched, 0)


#: Minutes per 8,192-position shard on a shared card, conservative (2026-09-17 sup logs: open sky
#  50-57, ground 88-110, full scene 149.8 per 4,096 positions, street canyon ~204-225). Lines with
#  --n-poses 4096 are half-length shards.
MIN_BY_CLASS = {"canyon": MIN_CANYON, "full_scene": 160, "ground": 100, "open_sky": 57}


def line_class(line):
    if CANYON in line:
        return "canyon"
    m = re.search(r"--env\s+(\S+)", line)
    if not m:
        return "open_sky"
    env = m.group(1)
    if env in ("outdoor01", "outdoor01_bldg"):
        return "full_scene"
    return "ground" if env.endswith("_ground") else "full_scene"


def line_minutes(line):
    m = re.search(r"--n-poses\s+(\d+)", line)
    n = int(m.group(1)) if m else 8192
    return MIN_BY_CLASS[line_class(line)] * n / 8192


def pending_lines(queue_files):
    """Lines not yet launched, exact: each supervisor launches its file in order and logs `큐 i/N`."""
    out = []
    for q in queue_files:
        try:
            lines = [l.strip() for l in open(q, encoding="utf-8")
                     if l.strip() and not l.lstrip().startswith("#")]
        except OSError:
            continue
        log = os.path.join(HERE, "logs", "sup_" + os.path.basename(q).split("_")[1] + ".log")
        i = 0
        try:
            for l in open(log, encoding="utf-8", errors="replace"):
                m = re.search(r"큐 (\d+)/(\d+)", l)
                if m and int(m.group(2)) == len(lines):
                    i = int(m.group(1))
        except OSError:
            pass                      # no supervisor log yet: every line is still pending
        out.extend(lines[i:])
    return out


def expand_queues(files, globs):
    qs = list(files)
    for g in globs:
        qs.extend(sorted(p for p in glob.glob(os.path.join(os.path.dirname(HERE), g))
                         if "HOLD" not in os.path.basename(p)))
    return sorted(set(qs))


def set_card(card, held, log):
    """Add or remove one card from the hold, leaving every other key exactly as it was."""
    with hold_lock():
        return _set_card_locked(card, held, log)


def _set_card_locked(card, held, log):
    try:
        with open(HOLD, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError) as e:
        say(log, f"⛔GPU_HOLD.json unreadable ({e}) — leaving it alone, will retry")
        return None
    gpus = [int(g) for g in d.get("gpus", []) if isinstance(g, (int, float))]
    now_held = card in gpus
    if now_held == held:
        return now_held
    gpus = sorted(set(gpus) | {card}) if held else sorted(set(gpus) - {card})
    d["gpus"] = gpus
    tmp = HOLD + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    os.replace(tmp, HOLD)
    say(log, f"{'held' if held else 'released'} GPU {card} · gpus now {gpus}"
             f" (the supervisors re-read this file every round)")
    return held


def our_workers_on(card):
    """(pid, seconds running) of benchmark/elevation_sweep_md.py processes with CUDA_VISIBLE_DEVICES=<card>."""
    out = []
    for p in os.listdir("/proc"):
        if not p.isdigit():
            continue
        try:
            argv = open(f"/proc/{p}/cmdline", "rb").read().split(b"\0")
            if len(argv) < 2 or not argv[1].endswith(b"elevation_sweep_md.py"):
                continue
            env = open(f"/proc/{p}/environ", "rb").read().split(b"\0")
            if f"CUDA_VISIBLE_DEVICES={card}".encode() not in env:
                continue
            start_ticks = int(open(f"/proc/{p}/stat").read().rsplit(")", 1)[1].split()[19])
            uptime = float(open("/proc/uptime").read().split()[0])
            out.append((int(p), int(uptime - start_ticks / os.sysconf("SC_CLK_TCK"))))
        except (OSError, ValueError, IndexError):
            pass
    return sorted(out)


def evacuate(card, log):
    """Last resort before --free-at (user asked for the card to be empty): evacuate_gpu.py --go, then re-queue."""
    import subprocess
    ws = our_workers_on(card)
    if not ws:
        say(log, f"evacuation check: no worker of ours on GPU {card} — nothing to do")
        return
    root = os.path.dirname(HERE)
    py = "/workspace/.venvs/py312/bin/python"
    before = set(glob.glob(os.path.join(HERE, f"jobs_REDO_gpu{card}_*.txt")))
    say(log, f"evacuation: {len(ws)} worker(s) still on GPU {card} → runners/evacuate_gpu.py {card} --go")
    r = subprocess.run([py, os.path.join(HERE, "evacuate_gpu.py"), str(card), "--go"],
                       cwd=root, capture_output=True, text=True)
    say(log, f"evacuate_gpu.py rc={r.returncode} · " + " | ".join((r.stdout + r.stderr).strip().splitlines()[-6:]))
    new = sorted(set(glob.glob(os.path.join(HERE, f"jobs_REDO_gpu{card}_*.txt"))) - before)
    for redo in new:
        tag = os.path.basename(redo)[len("jobs_"):-len(".txt")]
        slog = os.path.join(HERE, "logs", f"sup_{tag}.log")
        subprocess.Popen([py, os.path.join(HERE, "worker_supervisor.py"), redo, slog], cwd=root,
                         stdout=open(slog + ".nohup", "ab"), stderr=subprocess.STDOUT,
                         stdin=subprocess.DEVNULL, start_new_session=True)
        say(log, f"re-queued the interrupted lines: supervisor on {os.path.relpath(redo, root)} (log {os.path.relpath(slog, root)})")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--card", type=int, required=True)
    ap.add_argument("--free-at", required=True, help="HH:MM in KST, the time the card must be free")
    ap.add_argument("--queue", action="append", default=[], help="jobs file to watch, repeatable")
    ap.add_argument("--queue-glob", action="append", default=[],
                    help="glob relative to the repo, re-expanded every minute (files with HOLD in the name "
                         "are skipped); switches the cutoff to the exact per-line estimate of pending_lines()")
    ap.add_argument("--margin-min", type=int, default=15)
    ap.add_argument("--slowdown", type=float, default=1.0,
                    help="multiply the per-line minutes by this (lent cards carry other users' work)")
    ap.add_argument("--evacuate-at", default=None,
                    help="HH:MM KST before --free-at: if any of our workers are still on the card then, run "
                         "runners/evacuate_gpu.py <card> --go (hold, write a REDO file, stop only that card's "
                         "workers) and start a supervisor on the REDO file. Use only when the user asked for the "
                         "card to be empty by --free-at.")
    ap.add_argument("--log", default=None)
    a = ap.parse_args()

    hh, mm = (int(x) for x in a.free_at.split(":"))
    now = dt.datetime.now(KST)
    free_at = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if free_at <= now:
        free_at += dt.timedelta(days=1)

    evac_at = None
    if a.evacuate_at:
        eh, em = (int(x) for x in a.evacuate_at.split(":"))
        evac_at = free_at.replace(hour=eh, minute=em)
        if evac_at > free_at:
            evac_at -= dt.timedelta(days=1)
    say(a.log, f"GPU {a.card} lent until {free_at:%m-%d %H:%M} KST · "
               f"cutoff = that minus {a.slowdown:g} x the longest job still able to launch, minus {a.margin_min} min"
               + (f" · evacuation check at {evac_at:%m-%d %H:%M}" if evac_at else ""))
    set_card(a.card, False, a.log)
    evac_done = False
    last_report = None

    last = None
    while True:
        now = dt.datetime.now(KST)
        if a.queue_glob:
            pend = pending_lines(expand_queues(a.queue, a.queue_glob))
            longest = round(max((line_minutes(l) for l in pend), default=0))
            n_canyon = sum(1 for l in pend if line_class(l) == "canyon")
            what = f"{len(pend)} line(s) still to launch ({n_canyon} canyon)"
        else:
            n_canyon = pending_canyon(a.queue)
            longest = MIN_CANYON if n_canyon else MIN_GROUND
            what = f"{n_canyon} canyon line(s) still to launch"
        longest = round(longest * a.slowdown)
        cutoff = free_at - dt.timedelta(minutes=longest + a.margin_min)
        want_held = now >= cutoff or (evac_at is not None and now >= evac_at)
        state = (want_held, longest)
        if state != last:
            say(a.log, f"{'hold' if want_held else 'lend'} · {what}"
                       f" → longest {longest} min → cutoff {cutoff:%H:%M}")
            last = state
        set_card(a.card, want_held, a.log)
        if want_held and (last_report is None or now - last_report >= dt.timedelta(minutes=30)):
            ws = our_workers_on(a.card)
            say(a.log, f"card {a.card} held · our workers still there: {len(ws)}"
                       + "".join(f" · pid {p} {sec // 60} min" for p, sec in ws))
            last_report = now
        if evac_at is not None and not evac_done and now >= evac_at:
            evac_done = True
            evacuate(a.card, a.log)
        if now >= free_at:
            say(a.log, f"GPU {a.card} is past {free_at:%H:%M} and held — done")
            return
        time.sleep(60)


if __name__ == "__main__":
    main()
