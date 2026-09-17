#!/usr/bin/env python
"""repeat_spread_0916.py — how far two identical runs drift apart, measured where the question is asked.

Why this exists. The hash/buffer contrast (outputs/dropout_hash_vs_buffer_0916.json) found that moving
the candidate buffer alone left no position gaining or losing the environment path, but did leave one
position moved by about 2e-5 of the median |E| and two positions returning one path fewer. The 09-16
review asked whether that is the buffer or what two identical runs do anyway. Queue 0947 bought the
repeats (rep2, and rep1 at 8e6; rep1 came from jobs_0933, rep3 from jobs_0949); this reads them.

⛔**Read the scope before the number.** This script has been wrong three times.
  1st edition: compared the maximum repeat difference over all 8,192 positions against a buffer
     difference measured on 42, and called it "inside the spread". Not like-for-like.
  2nd edition: matched the positions, found the buffer difference 9x larger, and called it "not
     explained by repeat variation". Also wrong — a whole-sweep re-run is not the right comparator.
  3rd edition (commit 5920e303): used the split ledger's production-setting re-solve as the comparator
     and described it as the same positions, the same run and the same card. Only the positions are the
     same. The comparator is the
     stored whole-sweep production output (GPU 1, 09-14, jobs_0931)
     vs fresh diagnostic re-solve (GPU 2, 09-16, 42 poses): a different process on a different card. Nothing here attributes the difference to the card; card and
     process change together in that comparison. (Corrected 2026-09-17 after the external review
     /workspace/sionna_review_2026-09-17_queues_figures.md §2.5 and its adversarial verification.)
  What that comparator does show: re-solving the production setting on those positions differs from the
     stored field by the same size, and with one-path flips at the same positions, as the buffer contrast.
     So nothing can be attributed to the buffer at that size. It does NOT show that this size is
     run-to-run noise — it is one path toggling at those positions.
  The identical-run scope is the whole-sweep repeats (production limit: plain, rep1, rep2, rep3; limit
     8e6: plain, rep1). They are read twice: at the contrast's positions, and over the whole cell, where
     the one-path flip rate says how much weight «no flip at those positions» can carry.
  The card, date, queue and position count in the comparator wording are read back at run time from the
     shards, the split ledger and runners/logs/sup_bridge_0931.log (_meta.comparator), not taken from this text.

⛔This measures the spread of the simulator's own output between identical runs. It says nothing about
which output is closer to reality, and nothing about a real radar.

    CUDA_VISIBLE_DEVICES="" /workspace/.venvs/py312/bin/python benchmark/repeat_spread_0916.py
"""
import glob
import itertools
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone

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

#: identical whole-sweep runs at the production limit — the same job line with only --rep changed
RUNS = [("run 1", GROUND), ("run 2 (rep1)", "rep1_" + GROUND),
        ("run 3 (rep2)", "rep2_" + GROUND), ("run 4 (rep3)", "rep3_" + GROUND)]
RUNS8 = [("limit 8e6, run 1", GROUND8), ("limit 8e6, run 2 (rep1)", "rep1_" + GROUND8)]

#: a whole-cell path-count flip is also counted separately when it moves the field by more than this
#  fraction of the cell's median |E| (the size class of the buffer contrast's largest move)
FLIP_MOVE_TOL = 1e-5

#: the comparator, in the words the 09-17 correction asked for; every number in it is checked at run time
COMPARATOR_WORDING = ("stored whole-sweep production output (GPU 1, 09-14, jobs_0931) vs fresh diagnostic "
                      "re-solve (GPU 2, 09-16, 42 poses)")
SUP_LOG_0931 = f"{ROOT}/runners/logs/sup_bridge_0931.log"
KST = timezone(timedelta(hours=9))                     # supervisor logs stamp local time (KST) without a year


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
    #: ⭐the ledger's production-setting re-solve — each chosen position solved again at the production
    #  setting and differenced against the field already on disk. Comparator: stored whole-sweep production
    #  output (GPU 1, 09-14, jobs_0931) vs fresh diagnostic re-solve (GPU 2, 09-16, 42 poses) — not the same
    #  run and not the same card; nothing here attributes the difference to the card (see _meta.comparator).
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
    diag = dict(ledger=os.path.relpath(SPLIT, ROOT),
                cuda_visible_devices=(d["_meta"].get("env") or {}).get("CUDA_VISIBLE_DEVICES"),
                started_utc=d["_meta"].get("started_utc"), finished_utc=d["_meta"].get("finished_utc"),
                n_positions=len(cell["meta"]["selected"]["solve_order"]),
                n_production_rows=len(replay),
                stored_shards=[s["file"] for s in cell["meta"]["shards"]])
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
                n_incremental_losses=con.get("n_incremental_losses")), diag


def read_launches(log_path):
    """Supervisor launch lines: [(time KST without year, launch number, gpu)]. None when the log is absent."""
    if not os.path.exists(log_path):
        return None
    pat = re.compile(r"^\[(\d\d)-(\d\d) (\d\d):(\d\d):(\d\d)\]\s+띄움 #(\d+) pid=\d+ gpu=(\d+)")
    out = []
    with open(log_path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = pat.match(line)
            if m:
                mo, dd, hh, mi, ss, num, gpu = m.groups()
                out.append(((int(mo), int(dd), int(hh), int(mi), int(ss)), int(num), gpu))
    return out


def comparator_provenance(diag):
    """Where the two sides of the re-solve comparator came from, read back from shards, ledger and log."""
    launches = read_launches(SUP_LOG_0931)
    jobs_rel = "runners/jobs_0931_bridge.txt"
    jobs = []
    if os.path.exists(f"{ROOT}/{jobs_rel}"):
        with open(f"{ROOT}/{jobs_rel}", encoding="utf-8") as fh:
            jobs = [ln.strip() for ln in fh if ln.strip() and not ln.lstrip().startswith("#")]
    stored = []
    for name in diag["stored_shards"]:
        path = f"{SHARDS}/{name}"
        with np.load(path) as z:
            t0 = float(np.asarray(z["t_start"]).ravel()[0])
            run_id = str(z["run_id"])
        t0_kst = datetime.fromtimestamp(t0, KST)
        shard_no = int(re.search(r"_(\d\d)\.npz$", name).group(1))
        match = None
        if launches is not None:
            near = []
            for (mo, dd, hh, mi, ss), num, gpu in launches:
                tl = datetime(t0_kst.year, mo, dd, hh, mi, ss, tzinfo=KST)
                lag = (t0_kst - tl).total_seconds()
                if 0 <= lag <= 120:
                    line = jobs[num - 1] if 0 < num <= len(jobs) else ""
                    line_ok = ("--els=-60" in line and "--env outdoor01_ground" in line
                               and f"--shard {shard_no}" in line and "--rep" not in line
                               and "--max-paths" not in line)
                    near.append(dict(launch=num, gpu=gpu, lag_s=lag, jobs_line_matches=line_ok))
            match = [x for x in near if x["jobs_line_matches"]]
        stored.append(dict(file=name, run_id=run_id,
                           t_start_kst=t0_kst.strftime("%Y-%m-%d %H:%M:%S"),
                           launches_matching_start_and_job_line=match))
    gpus = sorted({x["gpu"] for s in stored for x in (s["launches_matching_start_and_job_line"] or [])})
    dates = sorted({s["t_start_kst"][5:10] for s in stored})
    diag_date = (datetime.strptime(diag["started_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                 .astimezone(KST).strftime("%m-%d")) if diag.get("started_utc") else None

    w = re.search(r"\(GPU (\d+), (\d\d-\d\d), (jobs_\d+)\) vs .*\(GPU (\d+), (\d\d-\d\d), (\d+) poses\)",
                  COMPARATOR_WORDING)
    s_gpu, s_date, s_jobs, d_gpu, d_date, d_n = w.groups()
    checks = dict(
        stored_gpu=(gpus == [s_gpu]) if launches is not None else None,
        stored_date=dates == [s_date],
        stored_queue=(bool(stored) and all(s["launches_matching_start_and_job_line"] for s in stored)
                      and s_jobs in jobs_rel) if launches is not None else None,
        re_solve_gpu=diag.get("cuda_visible_devices") == d_gpu,
        re_solve_date=diag_date == d_date,
        re_solve_positions=diag["n_positions"] == int(d_n) == diag["n_production_rows"])
    return dict(wording=COMPARATOR_WORDING,
                stored_side=dict(shards=stored, gpus=gpus, t_start_dates_kst=dates,
                                 supervisor_log=os.path.relpath(SUP_LOG_0931, ROOT),
                                 supervisor_log_on_disk=launches is not None, jobs_file=jobs_rel),
                re_solve_side=dict(diag, started_date_kst=diag_date),
                wording_checked=checks,
                wording_holds=all(v is not False for v in checks.values()))


def compare(name, a_stem, b_stem, sel):
    a, b = load(a_stem), load(b_stem)
    if a is None or b is None:
        return dict(pair=name, available=False, missing=a_stem if a is None else b_stem), None
    med = float(np.median(np.abs(a["E"])))
    d = np.abs(a["E"] - b["E"]) / med
    dn = np.abs(a["npaths"] - b["npaths"])
    flip = dn > 0
    sel = np.asarray(sel, int)
    return dict(pair=name, available=True, n_positions=int(a["n"]),
                all_positions=dict(
                    max_field_move_over_median=float(d.max()),
                    p99=float(np.percentile(d, 99)),
                    n_with_a_different_path_count=int(flip.sum()),
                    path_count_flip_rate=float(flip.mean()),
                    n_one_path_flips=int((dn == 1).sum()),
                    n_flips_moving_more_than_tol=int((flip & (d > FLIP_MOVE_TOL)).sum()),
                    max_field_move_at_a_flip=float(d[flip].max()) if flip.any() else 0.0,
                    max_path_count_difference=int(dn.max())),
                same_positions_as_the_contrast=dict(
                    n=int(sel.size),
                    max_field_move_over_median=float(d[sel].max()),
                    n_with_a_different_path_count=int(flip[sel].sum()),
                    max_path_count_difference=int(dn[sel].max()),
                    expected_flips_at_the_whole_cell_rate=float(flip.mean() * sel.size)),
                shards=dict(a=a["files"], b=b["files"])), set(np.where(flip)[0].tolist())


def main() -> None:
    t0 = time.time()
    split, diag = read_split()
    sel = split["poses"]
    comparator = comparator_provenance(diag)

    rows, flipsets = [], {}
    for (na, sa), (nb, sb) in itertools.combinations(RUNS, 2):
        r, fs = compare(f"production limit, {na} vs {nb}", sa, sb, sel)
        rows.append(r)
        flipsets[(na, nb)] = fs
    for (na, sa), (nb, sb) in itertools.combinations(RUNS8, 2):
        r, fs = compare(f"{na} vs {nb.replace('limit 8e6, ', '')}", sa, sb, sel)
        rows.append(r)
    got = [r for r in rows if r["available"]]
    if not got:
        raise SystemExit("⛔no repeat pair is on disk — nothing to read")

    #: the whole-cell flip rate of identical runs, read against run 1 (the stored production cell)
    first = RUNS[0][0]
    vs_first = [r for r in got if r["pair"].startswith(f"production limit, {first} vs ")]
    sets_first = [flipsets[k] for k in flipsets if k[0] == first and flipsets[k] is not None]
    n_sel = len(sel)
    whole_cell = None
    if vs_first:
        cnt = [r["all_positions"]["n_with_a_different_path_count"] for r in vs_first]
        rate = [r["all_positions"]["path_count_flip_rate"] for r in vs_first]
        big = [r["all_positions"]["n_flips_moving_more_than_tol"] for r in vs_first]
        seen = sum(r["same_positions_as_the_contrast"]["n_with_a_different_path_count"] for r in vs_first)
        whole_cell = dict(
            pairs=[r["pair"] for r in vs_first],
            n_positions=vs_first[0]["n_positions"],
            n_flipped=cnt, flip_rate_min=min(rate), flip_rate_max=max(rate),
            n_flipped_moving_more_than_tol=big, tol=FLIP_MOVE_TOL,
            n_flipped_in_every_pair=len(set.intersection(*sets_first)) if sets_first else None,
            contrast_positions=n_sel,
            expected_flips_per_repeat_at_those_positions=[min(rate) * n_sel, max(rate) * n_sel],
            observed_flips_at_those_positions_all_repeats=seen)

    wide = max(r["all_positions"]["max_field_move_over_median"] for r in got)
    matched = max(r["same_positions_as_the_contrast"]["max_field_move_over_median"] for r in got)
    matched_dn = max(r["same_positions_as_the_contrast"]["n_with_a_different_path_count"] for r in got)
    buf = split["largest_move"]
    rep = split["same_settings_replay"]
    same = rep["largest_move"]
    shared_flip_positions = sorted({p for p, *_ in split["path_count_differences"]}
                                   & {p for p, *_ in rep["path_count_flips"]})
    rate_txt = ""
    if whole_cell:
        rate_txt = (f" Identical whole-sweep runs (run 1 against each repeat) flip the path count at "
                    f"{min(whole_cell['n_flipped'])}-{max(whole_cell['n_flipped'])} of "
                    f"{whole_cell['n_positions']:,} positions ({whole_cell['flip_rate_min']:.1%}-"
                    f"{whole_cell['flip_rate_max']:.1%}), {min(whole_cell['n_flipped_moving_more_than_tol'])}-"
                    f"{max(whole_cell['n_flipped_moving_more_than_tol'])} of them moving the field by more "
                    f"than {FLIP_MOVE_TOL:g}. At that rate about "
                    f"{whole_cell['expected_flips_per_repeat_at_those_positions'][0]:.1f}-"
                    f"{whole_cell['expected_flips_per_repeat_at_those_positions'][1]:.1f} flips per repeat are "
                    f"expected among the {n_sel} contrast positions; "
                    f"{whole_cell['observed_flips_at_those_positions_all_repeats']} were seen there across "
                    f"{len(whole_cell['pairs'])} repeats. The same positions flip again and again "
                    f"({whole_cell['n_flipped_in_every_pair']} in every pair), so that count is too little to call "
                    f"those positions stable.")

    #: the verdict branches; the comparator is the production-setting re-solve (a process difference)
    if buf is None or same is None:
        verdict = ("The split ledger does not carry both a buffer-contrast move and a production-setting "
                   "re-solve, so this run cannot judge it.")
        calls_it = "cannot-judge"
    elif buf <= same:
        verdict = (f"The fresh diagnostic re-solve at the production setting on these {rep['n']} positions "
                   f"differs from the stored whole-sweep output by up to {same:.3e}, with "
                   f"{rep['n_path_count_flips']} position(s) changing path count. The buffer-alone contrast "
                   f"moves the field by {buf:.3e}, with {len(split['path_count_differences'])} — the same "
                   "size and the same kind of difference, and its path-count change sits at position(s) "
                   f"{shared_flip_positions} where the re-solve also flips one path. So nothing can be "
                   "attributed to the buffer at that size. That comparator is a difference between two "
                   "processes on two cards, not a measured run-to-run spread." + rate_txt +
                   " What the contrast does show is that no position gained or lost the environment path: "
                   f"{split['n_incremental_recoveries']} incremental recoveries and "
                   f"{split['n_incremental_losses']} incremental losses.")
        calls_it = "same-size-as-a-re-solve"
    else:
        verdict = (f"The buffer-alone contrast moves the field by {buf:.3e}, larger than the "
                   f"{same:.3e} by which the production-setting re-solve differs from the stored field on "
                   "the same positions. That is worth a dedicated run before anything is attributed to it."
                   + rate_txt)
        calls_it = "larger-than-a-re-solve"

    doc = {
        "_meta": {
            "generator": "benchmark/repeat_spread_0916.py",
            "question": "Is the buffer-alone difference bigger than what two identical runs do anyway?",
            "answer": verdict,
            "verdict_code": calls_it,
            "bought_by": ["runners/jobs_0933_repeat.txt (rep1)",
                          "runners/jobs_0947_repeat_spread.txt (rep2; rep1 at limit 8e6)",
                          "runners/jobs_0949_antenna_by_angle.txt (rep3)"],
            "asked_by": "docs/HASH_DIAGNOSTIC_REVIEW_0916.ipynb §2 ②",
            "corrected_by": [
                ("docs/RESULTS_QUEUE_REVIEW_0917.ipynb §2 B — the first edition of this script compared the "
                 "maximum over all 8,192 positions against a contrast measured on 42, and reached the "
                 "opposite conclusion"),
                ("/workspace/sionna_review_2026-09-17_queues_figures.md §2.5 and its adversarial verification "
                 "(2026-09-17) — the re-solve comparator is not the same run or the same card; rep3 added; "
                 "the whole-cell flip rate of identical runs reported next to the contrast's positions"),
            ],
            "comparator": comparator,
            "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "wall_time_s": round(time.time() - t0, 1),
            "cannot_say": [
                "that the buffer caused the difference — the production-setting re-solve differs from the "
                "stored field by the same size of move on the same positions",
                "that the re-solve comparator is run-to-run noise — it compares the stored whole-sweep "
                "production output with a fresh diagnostic re-solve (a different process on a different "
                "card), and its one-path flips sit at positions where the knob contrasts also flip one path",
                "that the card causes the comparator's difference — card and process change together there",
                ("that the contrast's positions are stable because identical whole-sweep repeats show no flip "
                 "there — at the whole-cell flip rate only a handful of flips per repeat are expected among "
                 "them (whole_cell_flip_rate)"),
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
                "the same selected positions in one process on one card, (buffer 2e6, hash 8e6) against "
                "(buffer 8e6, hash 8e6), repeated with the run order balanced, with a production-setting "
                "re-solve at the start and at the end of that same process, and each position's difference "
                "read against the repeat distribution of that same position"),
            "definitions": {
                "field move": "|E_a - E_b| at the same rotor position, divided by the median |E| of "
                              "the cell",
                "the contrast's positions": "the rotor positions the split run actually solved, read "
                                            "from the split ledger's own groups — not a fixed list",
                "identical runs": "the same job line with only --rep changed",
                "whole-cell flip": "a rotor position, anywhere in the cell, whose returned path count differs "
                                   "between two identical whole-sweep runs",
                "production-setting re-solve": "split-ledger rows at grid point «production»: a chosen "
                                               "position solved again in the diagnostic process and differenced "
                                               "against the stored whole-sweep field "
                                               "(abs_err_over_abs_cell_median); see _meta.comparator",
            },
        },
        "buffer_contrast_being_judged": dict(
            source=os.path.relpath(SPLIT, ROOT), knob=f"{BUF_FROM} -> {BUF_TO}",
            positions_where_buffer_and_re_solve_both_flip=shared_flip_positions, **split),
        "whole_cell_flip_rate": whole_cell,
        "summary_of_repeats": dict(max_move_all_positions=wide, max_move_at_contrast_positions=matched,
                                   max_path_count_flips_at_contrast_positions=matched_dn),
        "repeats": rows,
    }
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, OUT)

    print(f"✅ {os.path.relpath(OUT, ROOT)}")
    print(f"  comparator: {COMPARATOR_WORDING}")
    print(f"    wording checked against shards/ledger/log: {comparator['wording_checked']}")
    if not comparator["wording_holds"]:
        print("  ⛔the comparator wording does not match what the shards, ledger and log say — fix the text")
    print(f"  buffer contrast, {len(sel)} positions: {buf:.3e}, path-count changes "
          f"{split['path_count_differences']}")
    print(f"  production setting re-solved (diagnostic process) vs stored field, same positions: {same:.3e}, "
          f"{rep['n_path_count_flips']} path-count flip(s) {rep['path_count_flips']}")
    print(f"\n  {'pair':48} {'all 8,192':>11} {'flips all':>10} {'>tol':>5} {'those ' + str(len(sel)):>11} "
          f"{'dN>0 there':>11} {'expected':>9}")
    for r in rows:
        if not r["available"]:
            print(f"  {r['pair']:48}  ⛔missing {r['missing'][:52]}"); continue
        ap, sp = r["all_positions"], r["same_positions_as_the_contrast"]
        print(f"  {r['pair']:48} {ap['max_field_move_over_median']:11.3e} {ap['n_with_a_different_path_count']:10d} "
              f"{ap['n_flips_moving_more_than_tol']:5d} {sp['max_field_move_over_median']:11.3e} "
              f"{sp['n_with_a_different_path_count']:11d} {sp['expected_flips_at_the_whole_cell_rate']:9.2f}")
    print()
    print("  " + verdict.replace(". ", ".\n  "))


if __name__ == "__main__":
    main()
