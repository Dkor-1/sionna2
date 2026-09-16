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
import os
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
    """Canyon lines that have not been launched yet, counted from the supervisors' own logs."""
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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--card", type=int, required=True)
    ap.add_argument("--free-at", required=True, help="HH:MM in KST, the time the card must be free")
    ap.add_argument("--queue", action="append", default=[], help="jobs file to watch, repeatable")
    ap.add_argument("--margin-min", type=int, default=15)
    ap.add_argument("--log", default=None)
    a = ap.parse_args()

    hh, mm = (int(x) for x in a.free_at.split(":"))
    now = dt.datetime.now(KST)
    free_at = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if free_at <= now:
        free_at += dt.timedelta(days=1)

    say(a.log, f"GPU {a.card} lent until {free_at:%m-%d %H:%M} KST · "
               f"cutoff = that minus the longest job still able to launch, minus {a.margin_min} min")
    set_card(a.card, False, a.log)

    last = None
    while True:
        now = dt.datetime.now(KST)
        n_canyon = pending_canyon(a.queue)
        longest = MIN_CANYON if n_canyon else MIN_GROUND
        cutoff = free_at - dt.timedelta(minutes=longest + a.margin_min)
        want_held = now >= cutoff
        state = (want_held, n_canyon > 0)
        if state != last:
            say(a.log, f"{'hold' if want_held else 'lend'} · {n_canyon} canyon line(s) still to launch"
                       f" → longest {longest} min → cutoff {cutoff:%H:%M}")
            last = state
        set_card(a.card, want_held, a.log)
        if now >= free_at:
            say(a.log, f"GPU {a.card} is past {free_at:%H:%M} and held — done")
            return
        time.sleep(60)


if __name__ == "__main__":
    main()
