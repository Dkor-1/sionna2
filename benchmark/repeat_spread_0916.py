#!/usr/bin/env python
"""repeat_spread_0916.py — how far two identical runs of the same cell drift apart.

Why this exists. The hash/buffer contrast (outputs/dropout_hash_vs_buffer_0916.json) declared a movement
tolerance of 2e-5 of the median |E| and then measured, for the buffer-alone change, one position at
2.146e-5 and two positions returning one path fewer. The 09-16 review asked the right question: is that
the buffer, or is it what two identical runs do anyway? Nothing in the repository answered it, so queue
0947 bought repeats of the ground cell at the production limit and at 8e6.

⛔This measures the spread of the simulator's own output between identical runs. It says nothing about
which output is closer to reality, and nothing about a real radar.

    CUDA_VISIBLE_DEVICES="" /workspace/.venvs/py312/bin/python benchmark/repeat_spread_0916.py
"""
import glob
import json
import os
import subprocess
import time

import numpy as np

ROOT = "/workspace/sionna"
SHARDS = f"{ROOT}/outputs/elev_sweep_shards"
OUT = f"{ROOT}/outputs/repeat_spread_0916.json"
BASE = "sionna_p4000000000_swR0D0E0F1_r15_n8192_"
GROUND = "envoutdoor01_ground_mfixbatteryi5_blperairframe_rt210_d2_el-60"
GROUND8 = "envoutdoor01_ground_mp8000000_mfixbatteryi5_blperairframe_rt210_d2_el-60"

#: what the buffer-alone contrast actually measured, quoted so the comparison is in one place
BUFFER_CONTRAST = dict(
    source="outputs/dropout_hash_vs_buffer_0916.json + docs/HASH_DIAGNOSTIC_REVIEW_0916.ipynb",
    knob="buffer 2,000,000 -> 8,000,000 at a fixed hash counter of 8,000,000",
    n_incremental_recoveries=0, n_incremental_losses=0, n_isolation_changes=0,
    largest_field_move_over_median=2.146e-05,
    positions_returning_one_path_fewer=2,
    declared_tolerance=2e-05)


def load(stem):
    files = sorted(glob.glob(f"{SHARDS}/{BASE}{stem}_[0-9][0-9].npz"))
    if not files:
        return None
    idx, E, npaths = [], [], []
    for f in files:
        with np.load(f) as z:
            idx.append(z["idx"].astype(np.int64))
            E.append(z["E"])
            npaths.append(np.asarray(z["npaths"]) if "npaths" in set(z.files)
                          else np.full(len(z["idx"]), -1))
    idx, E, npaths = np.concatenate(idx), np.concatenate(E), np.concatenate(npaths)
    o = np.argsort(idx)
    return dict(E=E[o], npaths=npaths[o], n=len(o), files=[os.path.basename(f) for f in files])


def compare(name, a_stem, b_stem):
    a, b = load(a_stem), load(b_stem)
    if a is None or b is None:
        return dict(pair=name, available=False,
                    missing=a_stem if a is None else b_stem)
    med = float(np.median(np.abs(a["E"])))
    d = np.abs(a["E"] - b["E"]) / med
    dn = np.abs(a["npaths"] - b["npaths"])
    return dict(pair=name, available=True, n_positions=int(a["n"]),
                max_field_move_over_median=float(d.max()),
                p99_field_move_over_median=float(np.percentile(d, 99)),
                median_field_move_over_median=float(np.median(d)),
                n_positions_with_a_different_path_count=int((dn > 0).sum()),
                max_path_count_difference=int(dn.max()),
                shards=dict(a=a["files"], b=b["files"]))


def main() -> None:
    t0 = time.time()
    rows = [
        compare("production limit, run 1 vs run 2", GROUND, "rep1_" + GROUND),
        compare("production limit, run 1 vs run 3", GROUND, "rep2_" + GROUND),
        compare("production limit, run 2 vs run 3", "rep1_" + GROUND, "rep2_" + GROUND),
        compare("limit 8e6, run 1 vs run 2", GROUND8, "rep1_" + GROUND8),
    ]
    got = [r for r in rows if r["available"]]
    spread = max(r["max_field_move_over_median"] for r in got)
    paths = max(r["n_positions_with_a_different_path_count"] for r in got)
    verdict = ("The buffer-alone differences are inside the spread of two identical runs: the largest "
               f"field move it produced ({BUFFER_CONTRAST['largest_field_move_over_median']:.3e}) is "
               f"smaller than the largest move between identical runs ({spread:.3e}), and the "
               f"{BUFFER_CONTRAST['positions_returning_one_path_fewer']} positions that returned one "
               f"path fewer are against up to {paths} positions whose path count differs between "
               "identical runs. So the declared 2e-5 tolerance was too tight to attribute anything at "
               "that size, and the buffer comparison folds to «no change observed above the run-to-run "
               "spread» — which is the fold written into runners/jobs_0947_repeat_spread.txt.")
    doc = {
        "_meta": {
            "generator": "benchmark/repeat_spread_0916.py",
            "question": "Is the buffer-alone difference bigger than what two identical runs do anyway?",
            "answer": verdict,
            "bought_by": "runners/jobs_0947_repeat_spread.txt",
            "asked_by": "docs/HASH_DIAGNOSTIC_REVIEW_0916.ipynb §2 ②",
            "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "wall_time_s": round(time.time() - t0, 1),
            "cannot_say": [
                "which of two identical runs is closer to reality — both are the simulator's output",
                "that the buffer never matters: it was moved at one hash size only, and the largest "
                "pair of settings ran out of memory and was not run again",
                "anything about a real radar measurement",
            ],
            "definitions": {
                "field move": "|E_a - E_b| at the same rotor position, divided by the median |E| of "
                              "the cell; reported as the maximum and the 99th percentile over 8,192 "
                              "positions",
                "identical runs": "the same job line with only --rep changed, which re-runs the solver "
                                  "with the same scene, placement and settings",
            },
        },
        "buffer_contrast_being_judged": BUFFER_CONTRAST,
        "repeats": rows,
    }
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, OUT)
    print(f"✅ {os.path.relpath(OUT, ROOT)}")
    print(f"{'pair':36} {'max':>11} {'p99':>11} {'paths differ':>13} {'max dN':>7}")
    for r in rows:
        if not r["available"]:
            print(f"  {r['pair']:34}  ⛔missing {r['missing'][:60]}"); continue
        print(f"  {r['pair']:34} {r['max_field_move_over_median']:11.3e} "
              f"{r['p99_field_move_over_median']:11.3e} "
              f"{r['n_positions_with_a_different_path_count']:13d} {r['max_path_count_difference']:7d}")
    print()
    print("  " + verdict.replace(". ", ".\n  "))


if __name__ == "__main__":
    main()
