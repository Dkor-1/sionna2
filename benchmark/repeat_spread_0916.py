#!/usr/bin/env python
"""repeat_spread_0916.py — how far two identical runs drift apart, measured where the question is asked.

Why this exists. The hash/buffer contrast (outputs/dropout_hash_vs_buffer_0916.json) found that moving
the candidate buffer alone left no position gaining or losing the environment path, but did leave one
position moved by about 2e-5 of the median |E| and two positions returning one path fewer. The 09-16
review asked whether that is the buffer or what two identical runs do anyway. Queue 0947 bought the
repeats; this reads them.

⛔**Read the scope before the number.** This script has been wrong twice, in opposite directions.
  1st edition: compared the maximum repeat difference over all 8,192 positions against a buffer
     difference measured on 42, and called it "inside the spread". Not like-for-like.
  2nd edition: matched the positions, found the buffer difference 9x larger, and called it "not
     explained by repeat variation". Also wrong — a whole-sweep re-run is not the right comparator.
  ⭐The right comparator was inside the split ledger the whole time. That run re-solves each chosen
     position at the production setting and stores the difference against the field already on disk
     (`abs_err_over_abs_cell_median`). That IS "identical settings, same positions, re-solved", and it
     produces 1.97e-5 with two one-path flips — the same size and the same kind of difference as the
     buffer contrast. So nothing can be attributed to the buffer at that size.
  The whole-sweep repeats bought by 0947 are still reported, as a second, coarser scope.

⛔This measures the spread of the simulator's own output between identical runs. It says nothing about
which output is closer to reality, and nothing about a real radar.

    CUDA_VISIBLE_DEVICES="" /workspace/.venvs/py312/bin/python benchmark/repeat_spread_0916.py
"""
import glob
import json
import os
import time

import numpy as np

ROOT = "/workspace/sionna"
SHARDS = f"{ROOT}/outputs/elev_sweep_shards"
SPLIT = f"{ROOT}/outputs/dropout_hash_vs_buffer_0916.json"
OUT = f"{ROOT}/outputs/repeat_spread_0916.json"
BASE = "sionna_p4000000000_swR0D0E0F1_r15_n8192_"
GROUND = "envoutdoor01_ground_mfixbatteryi5_blperairframe_rt210_d2_el-60"
GROUND8 = "envoutdoor01_ground_mp8000000_mfixbatteryi5_blperairframe_rt210_d2_el-60"

#: the buffer-alone contrast is «buffer 2e6 -> 8e6 at a fixed hash counter of 8e6», i.e. hash8 -> both8
BUF_FROM, BUF_TO = "hash8", "both8"


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


def read_split():
    """The poses the split run solved, and the buffer-alone difference it measured — from the ledger."""
    with open(SPLIT, encoding="utf-8") as f:
        d = json.load(f)
    cell = d["cells"][0]
    groups = cell["summary"]["groups"]
    poses = sorted({p for v in groups.values() for p in v})
    by = {}
    for r in cell["rows"]:
        by.setdefault(r["grid_point"], {})[r["pose"]] = r
    a, b = by.get(BUF_FROM, {}), by.get(BUF_TO, {})
    shared = sorted(set(a) & set(b))
    moves, dpaths = [], []
    for p in shared:
        ea, eb = a[p].get("E_recomputed"), b[p].get("E_recomputed")
        if isinstance(ea, list) and isinstance(eb, list):
            za, zb = complex(*ea), complex(*eb)
            med = a[p].get("abs_E_recomputed", 0) / max(a[p].get("abs_E_over_abs_cell_median", 1), 1e-30)
            if med:
                moves.append((abs(za - zb) / med, p))
        na, nb = a[p].get("n_paths_returned"), b[p].get("n_paths_returned")
        if na is not None and nb is not None and na != nb:
            dpaths.append((p, na, nb))
    #: ⭐the ledger's own same-settings replay — each chosen position solved again at the production
    #  setting and differenced against the field already on disk. Same positions, same run, same card.
    replay = []
    for r in cell["rows"]:
        if r["grid_point"] != "production":
            continue
        e = r.get("abs_err_over_abs_cell_median")
        if e is not None:
            replay.append(dict(pose=r["pose"], move=float(e),
                               paths_now=r.get("n_paths_returned"),
                               paths_stored=r.get("npaths_stored")))
    replay.sort(key=lambda x: -x["move"])
    flips = [x for x in replay if x["paths_now"] is not None and x["paths_stored"] is not None
             and x["paths_now"] != x["paths_stored"]]

    con = next((c for c in cell["summary"]["paired_contrasts"]
                if c["frm"] == BUF_FROM and c["to"] == BUF_TO), {})
    return dict(poses=poses, n_poses_scored=len(shared),
                same_settings_replay=dict(
                    n=len(replay),
                    largest_move=replay[0]["move"] if replay else None,
                    largest_move_pose=replay[0]["pose"] if replay else None,
                    n_path_count_flips=len(flips),
                    path_count_flips=[[x["pose"], x["paths_stored"], x["paths_now"]] for x in flips]),
                largest_move=max(moves)[0] if moves else None,
                largest_move_pose=max(moves)[1] if moves else None,
                path_count_differences=dpaths,
                n_incremental_recoveries=con.get("n_incremental_recoveries"),
                n_incremental_losses=con.get("n_incremental_losses"))


def compare(name, a_stem, b_stem, sel):
    a, b = load(a_stem), load(b_stem)
    if a is None or b is None:
        return dict(pair=name, available=False, missing=a_stem if a is None else b_stem)
    med = float(np.median(np.abs(a["E"])))
    d = np.abs(a["E"] - b["E"]) / med
    dn = np.abs(a["npaths"] - b["npaths"])
    sel = np.asarray(sel, int)
    return dict(pair=name, available=True, n_positions=int(a["n"]),
                all_positions=dict(
                    max_field_move_over_median=float(d.max()),
                    p99=float(np.percentile(d, 99)),
                    n_with_a_different_path_count=int((dn > 0).sum()),
                    max_path_count_difference=int(dn.max())),
                same_positions_as_the_contrast=dict(
                    n=int(sel.size),
                    max_field_move_over_median=float(d[sel].max()),
                    n_with_a_different_path_count=int((dn[sel] > 0).sum()),
                    max_path_count_difference=int(dn[sel].max())),
                shards=dict(a=a["files"], b=b["files"]))


def main() -> None:
    t0 = time.time()
    split = read_split()
    sel = split["poses"]
    rows = [
        compare("production limit, run 1 vs run 2", GROUND, "rep1_" + GROUND, sel),
        compare("production limit, run 1 vs run 3", GROUND, "rep2_" + GROUND, sel),
        compare("production limit, run 2 vs run 3", "rep1_" + GROUND, "rep2_" + GROUND, sel),
        compare("limit 8e6, run 1 vs run 2", GROUND8, "rep1_" + GROUND8, sel),
    ]
    got = [r for r in rows if r["available"]]
    if not got:
        raise SystemExit("⛔no repeat pair is on disk — nothing to read")

    wide = max(r["all_positions"]["max_field_move_over_median"] for r in got)
    matched = max(r["same_positions_as_the_contrast"]["max_field_move_over_median"] for r in got)
    matched_dn = max(r["same_positions_as_the_contrast"]["n_with_a_different_path_count"] for r in got)
    buf = split["largest_move"]
    rep = split["same_settings_replay"]
    same = rep["largest_move"]

    #: the verdict branches, and the primary comparator is the ledger's own same-settings replay
    if buf is None or same is None:
        verdict = ("The split ledger does not carry both a buffer-contrast move and a same-settings "
                   "replay, so this run cannot judge it.")
        calls_it = "cannot-judge"
    elif buf <= same:
        verdict = (f"Re-solving the identical setting on these same {rep['n']} positions already moves "
                   f"the field by {same:.3e}, with {rep['n_path_count_flips']} position(s) changing "
                   f"path count. The buffer-alone contrast moves it by {buf:.3e}, with "
                   f"{len(split['path_count_differences'])} — the same size and the same kind of "
                   "difference. So nothing can be attributed to the buffer at that size. What the "
                   "contrast does show is that no position gained or lost the environment path: "
                   f"{split['n_incremental_recoveries']} incremental recoveries and "
                   f"{split['n_incremental_losses']} incremental losses.")
        calls_it = "same-size-as-a-re-solve"
    else:
        verdict = (f"The buffer-alone contrast moves the field by {buf:.3e}, larger than the "
                   f"{same:.3e} that re-solving the identical setting on the same positions produces. "
                   "That is worth a dedicated run before anything is attributed to it.")
        calls_it = "larger-than-a-re-solve"

    doc = {
        "_meta": {
            "generator": "benchmark/repeat_spread_0916.py",
            "question": "Is the buffer-alone difference bigger than what two identical runs do anyway?",
            "answer": verdict,
            "verdict_code": calls_it,
            "bought_by": "runners/jobs_0947_repeat_spread.txt",
            "asked_by": "docs/HASH_DIAGNOSTIC_REVIEW_0916.ipynb §2 ②",
            "corrected_by": ("docs/RESULTS_QUEUE_REVIEW_0917.ipynb §2 B — the first edition of this "
                             "script compared the maximum over all 8,192 positions against a contrast "
                             "measured on 42, and reached the opposite conclusion"),
            "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "wall_time_s": round(time.time() - t0, 1),
            "cannot_say": [
                "that the buffer caused the difference — a re-solve at the identical setting produces "
                "the same size of move on the same positions",
                "that the 09-16 wording «two positions returning one path fewer» described the buffer: "
                "on this ledger the buffer-alone contrast changes the path count at ONE position and "
                "that position GAINS a path (8015: 2810 -> 2811). The 8016 case, 2794 -> 2793, is a "
                "production-versus-re-solve difference that was mislabelled as a buffer effect",
                "which of two identical runs is closer to reality — both are the simulator's output",
                "that the buffer never matters: it was moved at one hash size only, and the largest "
                "pair of settings ran out of memory and was not run again",
                "anything about a real radar measurement",
            ],
            "what_would_settle_it": (
                "the same selected positions, the same card, (buffer 2e6, hash 8e6) against "
                "(buffer 8e6, hash 8e6), repeated with the run order balanced, and each position's "
                "difference read against the repeat distribution of that same position"),
            "definitions": {
                "field move": "|E_a - E_b| at the same rotor position, divided by the median |E| of "
                              "the cell",
                "the contrast's positions": "the rotor positions the split run actually solved, read "
                                            "from the split ledger's own groups — not a fixed list",
                "identical runs": "the same job line with only --rep changed",
            },
        },
        "buffer_contrast_being_judged": dict(
            source=os.path.relpath(SPLIT, ROOT), knob=f"{BUF_FROM} -> {BUF_TO}", **split),
        "repeats": rows,
    }
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, OUT)

    print(f"✅ {os.path.relpath(OUT, ROOT)}")
    print(f"  buffer contrast, {len(sel)} positions: {buf:.3e}, path-count changes "
          f"{split['path_count_differences']}")
    print(f"  the SAME setting re-solved, same positions: {same:.3e}, "
          f"{rep['n_path_count_flips']} path-count flip(s) {rep['path_count_flips']}")
    print(f"\n  {'pair':34} {'all 8,192':>11} {'those ' + str(len(sel)):>11} {'dN>0 there':>11}")
    for r in rows:
        if not r["available"]:
            print(f"  {r['pair']:34}  ⛔missing {r['missing'][:52]}"); continue
        print(f"  {r['pair']:34} {r['all_positions']['max_field_move_over_median']:11.3e} "
              f"{r['same_positions_as_the_contrast']['max_field_move_over_median']:11.3e} "
              f"{r['same_positions_as_the_contrast']['n_with_a_different_path_count']:11d}")
    print()
    print("  " + verdict.replace(". ", ".\n  "))


if __name__ == "__main__":
    main()
