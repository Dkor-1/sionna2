#!/usr/bin/env python
"""lend_once.py — lend a card for exactly N workers, once, then take it back from new launches.

User, 2026-09-17: 「GPU 1,2번도 임시로 쓰자 각각 작업 3개만 한 번 올리고 그 뒤에는 추가로 싣지 않는
조건으로 올려줄래?」 [use GPU 1 and 2 too — put exactly three jobs on each, once, and add nothing after].

The supervisors water-fill every free slot, so simply releasing a card would refill it every time a job
finished. This releases the card, waits until N of our workers are on it, and then puts the hold back.
A hold blocks new launches only, so the N that started run to the end and nothing replaces them.

⛔It never stops a worker. ⛔It edits only the `gpus` list, through hold_window's lock, so it cannot race
the other hold watchers. If N never arrive (a slot cap, a queue running out) it holds the card anyway
after --timeout-min, because "add nothing after" is the instruction that has to hold.

    nohup .../python runners/lend_once.py --card 1 --card 2 --n 3 --log runners/logs/lend_once.log &
"""
import argparse
import datetime as dt
import os
import subprocess
import time

import hold_window as HW

KST = dt.timezone(dt.timedelta(hours=9))


def ours_on(card):
    """How many of our sweep workers the kernel says are on this card (CUDA_VISIBLE_DEVICES)."""
    n = 0
    try:
        pids = subprocess.run(["pgrep", "-f", "benchmark/elevation_sweep_md.py"],
                              capture_output=True, text=True).stdout.split()
    except OSError:
        return 0
    me = str(os.getpid())
    for p in pids:
        if p == me:
            continue
        try:
            with open(f"/proc/{p}/environ", "rb") as f:
                env = dict(kv.split(b"=", 1) for kv in f.read().split(b"\0") if b"=" in kv)
            with open(f"/proc/{p}/cmdline", "rb") as f:
                if b"python" not in f.read().split(b"\0")[0]:
                    continue
        except OSError:
            continue
        if env.get(b"CUDA_VISIBLE_DEVICES", b"").decode() == str(card):
            n += 1
    return n


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--card", type=int, action="append", required=True)
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--timeout-min", type=int, default=15)
    ap.add_argument("--log", default=None)
    a = ap.parse_args()

    base = {c: ours_on(c) for c in a.card}
    HW.say(a.log, f"lend once: cards {a.card}, {a.n} worker(s) each, then no more "
                  f"(ours already there: {base})")
    for c in a.card:
        HW.set_card(c, False, a.log)

    pending = set(a.card)
    t_end = time.time() + 60 * a.timeout_min
    while pending:
        for c in sorted(pending):
            k = ours_on(c) - base[c]
            if k >= a.n:
                HW.set_card(c, True, a.log)
                HW.say(a.log, f"GPU {c}: {k} worker(s) started — held again, nothing more will be added")
                pending.discard(c)
        if pending and time.time() > t_end:
            for c in sorted(pending):
                HW.set_card(c, True, a.log)
                HW.say(a.log, f"⚠GPU {c}: only {ours_on(c) - base[c]} started in {a.timeout_min} min — "
                              "held anyway, as instructed")
            pending.clear()
        time.sleep(5)
    HW.say(a.log, "done — the workers that started run to the end; the cards stay held")


if __name__ == "__main__":
    main()
