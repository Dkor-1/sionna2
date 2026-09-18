#!/usr/bin/env python3
"""Generator for runners/jobs_0969_reproducibility_budget_depth_seed.txt (campaign package P1).

Emits the queue file deterministically from the matrix stored in
/workspace/sionna_gpu_campaign_plan_2026-09-18.json (packages[0]).  Nothing is hand-typed:
the twelve anchors are RECOMPUTED here from the geometry rules written in
/workspace/sionna_queue_recommendations_2026-09-18.md section 4 and checked against the JSON,
and every cost number printed into the header is computed from stored shards and sidecars.

    /workspace/.venvs/py312/bin/python make_jobs_0969_reproducibility_budget_depth_seed.py

Writes the job file next to this script.  It does NOT touch /workspace/sionna/runners/.
"""
from __future__ import annotations

import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = "/workspace/sionna"
PLAN = "/workspace/sionna_gpu_campaign_plan_2026-09-18.json"
OUT = os.path.join(HERE, "jobs_0969_reproducibility_budget_depth_seed.txt")

# ----------------------------------------------------------------------------------------------
# 1. The matrix.  Read from the campaign JSON, recomputed here, and cross-checked.
# ----------------------------------------------------------------------------------------------

#: The fixed part of every line of this file.  Chosen once here so no line can drift.
COMMON = dict(engine="sionna", n_poses=1024, sw="R0D0E0F1", ant_pattern="tr38901",
              shell_mm=0.75, prop_mm=1.43, dump_paths=1024, shard=0, nshards=1)

#: The three axes crossed with the twelve anchors (campaign JSON packages[0]).
SPP = (1_000_000_000, 2_000_000_000, 4_000_000_000)
DEPTHS = (2, 3)
SEEDS = (1, 2, 3)
#: The true repeat: the same flags as the 4e9 / depth 3 / seed 1 cell, with --rep 1, which changes
#: the NAME only (elevation_sweep_md.py:516 appends _rep<N>; the help text at :2429 states the
#: physics is untouched).  --rep 1 is the repo's first-repeat number (20 lines across
#: runners/jobs_0922, 0933, 0947, 0948, 0949, 0952, 0953 use it).
REPEAT_AT = dict(spp=4_000_000_000, depth=3, seed=1, rep=1)

#: The ground scene name and the drone-relative ground offset convention:
#: --env-alt lowers every environment part by that many metres and leaves the drone at the origin
#: (elevation_sweep_md.py env_parts()), so --env-alt IS the drone height H above the plate, and the
#: radar height above the plate is h = H + R*sin(el)  (report15_probe.place() puts the radar at
#: centre + R*(cos el cos az, cos el sin az, sin el), and elevation_sweep_md.py:1071 calls it with
#: baseline=0.0, so TX and RX are co-located).
ENV = "outdoor01_ground"

#: Mast height held by the two anchor families that the doc defines by a radar height.
MAST_M = 1.5
#: The steep corner taken over from P2's coarse grid (recommendations section 5).
STEEP = dict(D=15.0, H=12.0, h=0.8)


def anchors():
    """The twelve P1 anchors, recomputed from the rules in recommendations section 4.

    Returns a list of dicts with: tag, range_m, el_deg, az_deg, scene, env_alt_m, radar_h_m.
    """
    out = []

    def add(tag, R, el, az, alt):
        """alt is None for open sky, else the drone height H above the plate."""
        h = None if alt is None else alt + R * math.sin(math.radians(el))
        out.append(dict(tag=tag, range_m=float(R), el_deg=float(el), az_deg=float(az),
                        scene="sky" if alt is None else "ground",
                        env_alt_m=None if alt is None else float(alt),
                        radar_h_m=h))

    # (a) the two 0960/0963 hub anchors at 15 m, and their stored ground partner alt 5.4 m.
    add("A01", 15, -15, 0, None)
    add("A02", 15, -15, 0, 5.4)
    # (b) the 0962/0965 ghost anchor at 30 m, az 0 and az 90, ground partner alt 4.11 m.
    add("A03", 30, -5, 0, None)
    add("A04", 30, -5, 0, 4.11)
    add("A05", 30, -5, 90, None)
    add("A06", 30, -5, 90, 4.11)
    # (c) 45 m, two elevations, with the ground plate placed so the radar keeps the 1.5 m mast:
    #     h = H + R sin(el) = 1.5  =>  H = 1.5 - 45 sin(el).
    for tag_sky, tag_gnd, el in (("A07", "A08", -5.0), ("A09", "A10", -15.0)):
        alt = MAST_M - 45.0 * math.sin(math.radians(el))
        add(tag_sky, 45, el, 0, None)
        add(tag_gnd, 45, el, 0, alt)
    # (d) the steep corner of the P2 coarse grid, D 15 m / H 12 m / h 0.8 m, converted with
    #     range = sqrt(D^2 + (h-H)^2), el = atan2(h-H, D), env-alt = H.
    D, H, h = STEEP["D"], STEEP["H"], STEEP["h"]
    R = math.sqrt(D * D + (h - H) ** 2)
    el = math.degrees(math.atan2(h - H, D))
    add("A11", R, el, 0, None)
    add("A12", R, el, 0, H)
    return out


def check_against_plan(anch):
    """Fail loudly if the recomputed anchors disagree with the stored campaign matrix."""
    with open(PLAN) as fh:
        plan = json.load(fh)
    p1 = plan["packages"][0]
    assert p1["id"] == "P1", p1["id"]
    ref = p1["anchors"]
    if len(ref) != len(anch):
        raise SystemExit(f"anchor count {len(anch)} != campaign JSON {len(ref)}")
    for got, want in zip(anch, ref):
        for key, jkey in (("range_m", "range_m"), ("el_deg", "elevation_deg"),
                          ("az_deg", "azimuth_deg")):
            if abs(got[key] - float(want[jkey])) > 1e-9:
                raise SystemExit(f"{got['tag']} {key}: {got[key]!r} != JSON {want[jkey]!r}")
        if (got["env_alt_m"] is None) != (want["env_alt_m"] is None):
            raise SystemExit(f"{got['tag']} scene mismatch against JSON")
        if got["env_alt_m"] is not None and abs(got["env_alt_m"] - float(want["env_alt_m"])) > 1e-9:
            raise SystemExit(f"{got['tag']} env_alt {got['env_alt_m']!r} != JSON {want['env_alt_m']!r}")
    for key, want in (("spp", SPP), ("depths", DEPTHS), ("solver_seeds", SEEDS)):
        if tuple(p1[key]) != tuple(want):
            raise SystemExit(f"{key}: {want} != JSON {p1[key]}")
    if int(p1["true_repeat_count"]) != len(anch):
        raise SystemExit("true_repeat_count != number of anchors")
    if int(p1["n_poses"]) != COMMON["n_poses"]:
        raise SystemExit("n_poses != JSON")
    upper = len(anch) * len(SPP) * len(DEPTHS) * len(SEEDS) + int(p1["true_repeat_count"])
    if upper != int(p1["count"]):
        raise SystemExit(f"line upper bound {upper} != JSON count {p1['count']}")
    return upper


# ----------------------------------------------------------------------------------------------
# 2. Line emission.
# ----------------------------------------------------------------------------------------------

def num(x):
    """Write a float the way the sweep's own %g name formatter will read it back."""
    s = f"{float(x):.10f}".rstrip("0").rstrip(".")
    return s if s else "0"


def line(a, spp, depth, seed, rep=0):
    """One argument line, in the flag order of runners/jobs_0963 and runners/jobs_0965."""
    p = [f"--engine {COMMON['engine']}",
         f"--n-poses {COMMON['n_poses']}",
         f"--range-m {num(a['range_m'])}",
         f"--sw {COMMON['sw']}",
         f"--spp {spp}",
         f"--max-depth {depth}",
         f"--els={num(a['el_deg'])}"]
    if a["az_deg"]:
        #: az 0 is the ledger value (outputs/report07_three_engines.json _meta.az_deg = 0.0), and
        #: passing --az-deg 0 would append an _az0 token and split one cell into two names
        #: (elevation_sweep_md.py:538).  So az 0 lines carry no --az-deg, as in runners/jobs_0963.
        p.append(f"--az-deg {num(a['az_deg'])}")
    if a["env_alt_m"] is not None:
        p.append(f"--env {ENV}")
        p.append(f"--env-alt {num(a['env_alt_m'])}")
    p.append(f"--ant-pattern {COMMON['ant_pattern']}")
    p.append(f"--shell-mm {num(COMMON['shell_mm'])}")
    p.append(f"--prop-mm {num(COMMON['prop_mm'])}")
    if seed != 1:
        #: seed 1 is the sweep default and adds no _ss token, so writing --solver-seed 1 would
        #: produce a line that LOOKS different from a stored seed-1 cell while naming the same
        #: shard.  runners/jobs_0960 and runners/jobs_0965 leave it out for the same reason.
        p.append(f"--solver-seed {seed}")
    if rep:
        p.append(f"--rep {rep}")
    p.append(f"--dump-paths {COMMON['dump_paths']}")
    p.append(f"--shard {COMMON['shard']}")
    p.append(f"--nshards {COMMON['nshards']}")
    return " ".join(p)


def all_records(anch):
    """Every record of the matrix, anchor block by anchor block, cheapest budget first."""
    recs = []
    for a in anch:
        for spp in SPP:
            for depth in DEPTHS:
                for seed in SEEDS:
                    recs.append((a, spp, depth, seed, 0))
        recs.append((a, REPEAT_AT["spp"], REPEAT_AT["depth"], REPEAT_AT["seed"],
                     REPEAT_AT["rep"]))
    return recs


# ----------------------------------------------------------------------------------------------
# 3. Cells already on disk.  Removed from the file; listed in the header as reused.
# ----------------------------------------------------------------------------------------------
#: Filled from the CPU dry-run of every generated line through runners/filter_jobs.sh
#: (2026-09-18 08:37:53-08:43:56 UTC = 17:37-17:43 KST, read-only, CUDA_VISIBLE_DEVICES="" SIONNA2_ALLOW_CPU=1
#: MPLBACKEND=Agg nice -n 19 taskset -c 8-15, xargs -P 4).  228 lines in, 4 DONE, 224 NEW,
#: 0 STALE, 0 BAD.
#: Key = (anchor tag, spp, depth, seed, rep).  Value = the stem the sweep gives that cell, without
#: the "_00.npz" suffix, plus whether outputs/path_provenance/<stem>_00_prov.npz is on disk.
#: ⛔Re-run the dry-run before installing: a cell that lands between now and then must be added
#: here, or the runner will silently skip the line (elevation_sweep_md.py:870 「건너뜀」).
_P4 = "sionna_p4000000000_swR0D0E0F1"
_SLAB = "shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210"
REUSED: dict = {
    ("A01", 4_000_000_000, 2, 1, 0): dict(
        stem=f"{_P4}_r15_n1024_{_SLAB}_d2_el-15", prov=False,
        by="runners/jobs_0963 line 142 (landed 2026-09-18 06:07 UTC)"),
    ("A03", 4_000_000_000, 3, 1, 0): dict(
        stem=f"{_P4}_r30_n1024_{_SLAB}_d3_el-5", prov=True,
        by="runners/jobs_0965 line 1"),
    ("A04", 4_000_000_000, 3, 1, 0): dict(
        stem=f"{_P4}_r30_n1024_envoutdoor01_ground_alt4.11_{_SLAB}_d3_el-5", prov=True,
        by="runners/jobs_0965 line 6"),
    ("A04", 4_000_000_000, 3, 2, 0): dict(
        stem=f"{_P4}_r30_n1024_envoutdoor01_ground_alt4.11_ss2_{_SLAB}_d3_el-5", prov=True,
        by="runners/jobs_0965 line 11"),
}

#: ⭐ONE line added beyond the campaign matrix, and the reason, stated here and in the header.
#: (A01, 4e9, depth 2, seed 1) exists on disk WITHOUT a path sidecar, and --dump-paths does NOT
#: change the stem (the runners/jobs_0967 header records the same trap for the same cell), so the
#: record the matrix asks for — path lists at every position — cannot be bought under that name.
#: --rep 1 gives it a name of its own and leaves runners/jobs_0963's aspect-library shard alone.
#: ⚠It is a re-solve of that cell, not the same draw, so any budget_step read against it carries
#: one rep_diff; gate R measures that.
SUBSTITUTES = [("A01", 4_000_000_000, 2, 1, 1)]


def load_reused():
    return REUSED


# ----------------------------------------------------------------------------------------------
# 4. Cost, computed from stored shards and sidecars — never from a rule of thumb.
# ----------------------------------------------------------------------------------------------
#: seconds/pose at 4e9 rays, thin slab, sionna-rt 2.1.0, median over every stored shard of that
#: class (meta[5] / len(idx)).  Counts: d2 sky 113 shards, d2 ground 26, d3 ground 14.
#: Measured 2026-09-18 from outputs/elev_sweep_shards/*rt210*.npz.
SEC_PER_POSE_4E9 = {(2, "sky"): 0.737, (2, "ground"): 1.365, (3, "ground"): 1.737}
#: depth 3 open sky has ONE stored shard (0.326 s/pose, the 30 m el-5 n1024 cell of
#: runners/jobs_0965 line 1), too few to take a median from, so it is carried as the depth-2 open
#: sky median times the measured depth-3/depth-2 ground ratio 1.737/1.365 = 1.2725.
SEC_PER_POSE_4E9[(3, "sky")] = SEC_PER_POSE_4E9[(2, "sky")] * (1.737 / 1.365)

#: On-disk sidecar bytes per position at 4e9 rays, depth 2, measured from
#: outputs/path_provenance/*_prov.npz (file size / len(n_paths)).  Keys are (range, el, scene).
BYTES_PER_POS_4E9_D2 = {
    (15, -15, "sky"): 10283, (15, -15, "ground"): 21339,
    (30, -5, "sky"): 1610, (30, -5, "ground"): 3313,
    (30, -15, "sky"): 2226, (30, -15, "ground"): 4564,
    (60, -5, "sky"): 510, (60, -5, "ground"): 921,
}
#: Measured depth-3 / depth-2 sidecar ratios at one geometry each.
D3_OVER_D2 = {"ground": 4084 / 3313, "sky": 1743 / 1610}


def bytes_per_pos(a, depth, spp):
    """Estimated on-disk sidecar bytes per position for one anchor, depth and ray budget."""
    R, el, scene = a["range_m"], a["el_deg"], a["scene"]
    key = (int(round(R)), int(round(el)), scene)
    if key in BYTES_PER_POS_4E9_D2:
        base = BYTES_PER_POS_4E9_D2[key]
    else:
        #: no stored sidecar at this anchor.  Take the nearest measured elevation at the nearest
        #: measured range and scale by R^-2 (the solid angle the drone subtends).  The one stored
        #: pair that tests it: 30 m el-5 sky 1610 B/pos x (30/60)^2 = 402 against 510 measured at
        #: 60 m (az 45), i.e. 21 % low.  ⚠An extrapolation, stated as one in the header.
        ref_R, ref_el = (30, -5) if abs(el) < 10 else (30, -15)
        if abs(el) > 25:                      # the steep corner: nearest stored elevation is -15
            ref_R, ref_el = (15, -15)
        base = BYTES_PER_POS_4E9_D2[(ref_R, ref_el, scene)] * (ref_R / R) ** 2
    if depth == 3:
        base *= D3_OVER_D2[scene]
    #: path count, and therefore sidecar size, scales with the ray budget: the 30 m el-15 open-sky
    #: depth-2 pair measures 1052 B/pos at 2e9 against 2226 B/pos at 4e9 (ratio 0.473, median
    #: n_paths 158 against 321).  Linear in spp is used, which is 6 % above that measurement.
    return base * (spp / 4e9)


def sec_per_pose(a, depth, spp):
    return SEC_PER_POSE_4E9[(depth, a["scene"])] * (spp / 4e9)


#: per-shard scene build and startup, added on top of the per-pose solve time.  0.5 min is the
#: figure the runners/jobs_0965 header used for the same scenes; it is an allowance, not a
#: measurement of this file.
BUILD_S = 30.0
#: The 1e9 / 2e9 lines are priced linearly in spp.  The 15 m el -15 pair suggests they can cost up
#: to 1.7x that (0.43 of the 4e9 median instead of 0.25); that factor sets the upper band.
SUBLINEAR_UPPER = 1.7


def cost(recs):
    """Sidecar bytes, point-estimate solve seconds and upper-band solve seconds."""
    n = COMMON["n_poses"]
    byt = sum(bytes_per_pos(a, d, s) * n for a, s, d, _sd, _r in recs)
    sec = sum(sec_per_pose(a, d, s) * n + BUILD_S for a, s, d, _sd, _r in recs)
    hi = sum(sec_per_pose(a, d, s) * n * (SUBLINEAR_UPPER if s < 4e9 else 1.0) + BUILD_S
             for a, s, d, _sd, _r in recs)
    return byt, sec, hi


# ----------------------------------------------------------------------------------------------
# 5. Header.
# ----------------------------------------------------------------------------------------------

def header(anch, recs, reused, byt, sec, hi, upper):
    n = COMMON["n_poses"]
    kept = len(recs)
    gb = byt / 1e9
    h_lo, h_hi = sec / 3600.0, hi / 3600.0
    g = []                                                        # geometry table rows
    for a in anch:
        h = "open sky" if a["radar_h_m"] is None else f"{a['radar_h_m']:.4f}"
        alt = "—" if a["env_alt_m"] is None else f"{a['env_alt_m']:.10g}"
        D = a["range_m"] * math.cos(math.radians(a["el_deg"]))
        g.append(f"#   | {a['tag']} | {a['range_m']:>18.10g} | {a['el_deg']:>15.10g} | "
                 f"{a['az_deg']:>3.0f} | {a['scene']:>6s} | {alt:>14s} | {h:>8s} | {D:8.4f} |")
    geom = "\n".join(g)

    per_anchor = {}
    for a, spp, d, sd, r in recs:
        per_anchor.setdefault(a["tag"], []).append((a, spp, d, sd, r))
    cost_rows = []
    for a in anch:
        rs = per_anchor.get(a["tag"], [])
        if not rs:
            cost_rows.append(f"#   | {a['tag']} |   0 |        — |        — |")
            continue
        b, s, _hi = cost(rs)
        cost_rows.append(f"#   | {a['tag']} | {len(rs):3d} | {b/1e6:7.1f} MB | {s/3600.0:7.2f} h |")
    costs = "\n".join(cost_rows)

    if reused:
        rl = ["#   Reused, not re-bought — removed from this file by the dry-run above. Stems are given without the _00.npz suffix.",
              "#   | cell | bought by | path sidecar on disk |", "#   |---|---|---|"]
        for k in sorted(reused):
            v = reused[k]
            rl.append(f"#   | {k[0]} · {k[1]/1e9:g}e9 · depth {k[2]} · seed {k[3]} | {v['by']} | "
                      f"{'yes' if v['prov'] else '⛔NO'} |")
        rl.append("#   |   |   |   |")
        for k in sorted(reused):
            rl.append(f"#   {k[0]}: {reused[k]['stem']}")
        reuse_block = "\n".join(rl)
    else:
        reuse_block = "#   (none — every cell of the matrix is new)"
    sub_rows = []
    for tag, spp, dep, sd, rep in SUBSTITUTES:
        sub_rows.append(f"#   {tag} · {spp/1e9:g}e9 · depth {dep} · seed {sd} → the same flags plus --rep {rep}. ⭐It is the LAST argument line of this file.")
    subs = "\n".join(sub_rows)

    return f"""\
# 0969 — what a PathSolver number at these settings is worth: at twelve fixed anchors, does the ordered path-class table (its powers,
#        its delays and the ratios read off it) stop moving when the ray budget is doubled, when max_depth goes from 2 to 3, and when
#        the solver seed is changed — and how large is a plain re-run of the same cell against all three? {kept} n1024 records, path lists
#        at every position, 4e9 rays and below.
#        (2026-09-18 ~16:20 KST, package P1 of /workspace/sionna_queue_recommendations_2026-09-18.md section 4 and
#         /workspace/sionna_gpu_campaign_plan_2026-09-18.json packages[0]; stage 1 of that plan, approved by the user 2026-09-18.)
#
# What this file decides, in one sentence. Which class ratios and which delays are stable enough that a LATER file may read them as a
#   geometry effect — and at which ray budget and max_depth they become so — so that the hundreds of geometry records of P2, P5 and P7
#   are not spent measuring the solver instead of the scene.
#
# Why now, and what the stored results already say. Every number below is recomputed from stored shards, not from an RF measurement.
#   · runners/jobs_0961: at 15 m, el −15, open sky, the comb contrast moves 2.25 dB between 1e9 and 4e9 rays. A time metric that still
#     moves with the ray budget at 4e9 cannot carry a geometry verdict.
#   · runners/jobs_0962 at 30 m, el −5, ground: class_power_db([g,d]) and class_power_db([d,g]) — the same two-ray path taken in the two
#     orders — differ by 24.96 dB. Sionna builds specular candidates and diffuse paths differently (official PathSolver description,
#     https://nvlabs.github.io/sionna/rt/tech-report/S3.html), so ⛔this file does NOT write «non-reciprocal propagation» or «solver bug»
#     anywhere; it separates the two orders by interaction type and by repeat, and reports what the repeat spread is.
#   · runners/jobs_0963: at 15 m, el −5, the first ten azimuths spread 26.34 dB in the static level while the solver seed alone moves
#     5.85 dB at one azimuth. A 5.85 dB seed spread is larger than most of the effects P2 and P7 are meant to measure.
#   · Measured here from the stored sidecars, and the reason the budget axis is not optional: at 30 m, el −15, open sky, depth 2, the
#     median number of returned paths per position is 158 at 2e9 rays and 321 at 4e9 — the path LIST is still roughly doubling with the
#     ray budget at the top of the ladder (outputs/path_provenance/sionna_p{{2,4}}000000000_swR0D0E0F1_r30_n4096_…_d2_el-15_00_prov.npz,
#     n_paths arrays). Whether the FIELD has converged while the list has not is exactly what this file measures.
#   Sources: outputs/readout_0918.json gates.0961.R2, gates.0962.P1, gates.0963.S1; the two sidecars named above.
#
# ⛔Two things this file is not, written before any result.
#   (1) ⛔**Averaging over solver seeds is not a denser ray grid.** Three seeds at 4e9 are three draws from the same sampling process,
#       not one draw at 12e9. If a quantity still moves between 2e9 and 4e9, no seed average of 4e9 records repairs it, and no sentence
#       from this file may say it does. Building a target-directed or split ray launch is a separate piece of work that needs its own
#       checks (per-direction sampling weights, specular de-duplication, normalisation of the diffuse estimator); it is not bought here
#       and it is not «more GPU time».
#   (2) ⛔**A pass applies only to the strata tested.** Twelve anchors at one airframe, one carrier, one slab, one antenna, hover only,
#       ground = one flat plate. A P1 pass is written as «at the tested anchors», and any later file whose geometry, cap behaviour or
#       event rate leaves this range adds its own budget and repeat sentinel. Including 45 m here does NOT settle range sensitivity in
#       general; it settles it at 45 m, el −5 and −15, az 0.
#
# The matrix. Twelve anchors x spp {{1e9, 2e9, 4e9}} x max_depth {{2, 3}} x --solver-seed {{1, 2, 3}} = {len(anch)}x{len(SPP)}x{len(DEPTHS)}x{len(SEEDS)} = {len(anch)*len(SPP)*len(DEPTHS)*len(SEEDS)} records,
#   plus a true repeat (--rep 1, same flags, name only) of each anchor at 4e9 / depth 3 / seed 1 = {len(anch)} more; upper bound {upper}.
#   The four cells already on disk are removed (below), and one substitute is added, so the file carries {kept} lines.
#   Every line is n1024, --dump-paths 1024 (path lists at EVERY position),
#   --nshards 1 so idx runs 0…1023 contiguously, R0D0E0F1, tr38901 aimed, shell 0.75 mm / propeller 1.43 mm, matrice4e revision 0,
#   3.5 GHz, PRF 19,700 Hz (ledger), path cap 2e6 (the sweep default).
#   ⚠--solver-seed 1 is the sweep default and adds no name token, so seed-1 lines carry no --solver-seed flag: writing it would make a
#     line look different from a stored seed-1 cell while naming the same shard. Same convention as runners/jobs_0960 and 0965.
#   ⚠az 0 lines carry no --az-deg either. The ledger azimuth is 0.0 (outputs/report07_three_engines.json _meta.az_deg) and passing
#     --az-deg 0 appends an _az0 token (elevation_sweep_md.py:538), splitting one cell into two names.
#
# Geometry, computed here from the code and not from a note. benchmark/elevation_sweep_md.py env_parts() lowers every environment part
#   by --env-alt and leaves the drone at the origin; benchmark/report15_probe.py place() puts the radar at
#   centre + R·(cos el·cos az, cos el·sin az, sin el); ⚠the sweep calls place(…, baseline=0.0) at elevation_sweep_md.py:1071, so TX and
#   RX are CO-LOCATED and report15_probe's module default BASELINE_M = 0.20 m is NOT used. Therefore --env-alt is the drone height H
#   above the plate and the radar height is h = H + R·sin(el); a negative elevation means the radar is BELOW the drone looking up.
#   | anchor |            range_m |          el_deg |  az |  scene |   --env-alt H |  radar h | horiz. D |
#   |---|---:|---:|---:|---|---:|---:|---:|
{geom}
#   How the four computed alts were obtained, and what they are for:
#   · A08 and A10 keep a real 1.5 m mast at 45 m: h = H + R·sin(el) = 1.5  ⇒  H = 1.5 − 45·sin(el).
#     el −5°  ⇒ H = 1.5 + 3.9220084236 = 5.4220084236 m; el −15° ⇒ H = 1.5 + 11.6468570296 = 13.1468570296 m. Both give h = 1.5000 m
#     exactly, checked in the table above.
#   · A11 and A12 are the steep corner of P2's coarse grid (D 15 m, H 12 m, mast h 0.8 m), converted with the P2 identities
#     range = √(D² + (h−H)²) = √(225 + 125.44) = √350.44 = 18.7200427350 m and el = atan2(h−H, D) = atan2(−11.2, 15) = −36.7474709529°,
#     with --env-alt = H = 12 m. Check: 12 + 18.7200427350·sin(−36.7474709529°) = 0.8000 m, the mast height it came from.
#   · A02 (alt 5.4) and A04/A06 (alt 4.11) are the stored partners of runners/jobs_0960 and runners/jobs_0962; their radar heights are
#     1.5177 m and 1.4953 m, not 1.5000 m. They are kept at their stored values on purpose — changing them by 2 cm would throw away
#     every stored partner this file leans on.
#   ⛔**Two anchor names are lossy and this is the standing caution.** The sweep writes the range as _r{{value:g}} and the elevation as
#     _el{{value:+g}} (elevation_sweep_md.py:513 and :866), i.e. six significant figures. A11/A12 therefore name themselves _r18.72 and
#     _el-36.7475, and A08/A10 name themselves _alt5.42201 and _alt13.1469. A LATER line at exactly 18.72 m and −36.7475° would reuse
#     these shards silently. Checked for this file: no stored shard in outputs/elev_sweep_shards carries _r18.72 or _el-36.7475, and no
#     line in any runners/jobs_*.txt (commented and #HOLD included) does either.
#   ⭐⛔**And one line of stage 1 itself does** — found by the 2026-09-18 cross-check of the four stage-1 packages together, which neither
#     generator could see on its own because each compared itself only against runners/jobs_*.txt. A11/A12 ARE the steep corner of P2's
#     coarse grid (D 15 m, H 12 m, mast h 0.8 m), so this file's **A11 and A12 at 4e9 / depth 3 / seed 1 / az 0** and 0972's
#     «D15 H12 h0.8 az0» open-sky and ground lines are ONE record each, not two: same values, same stem
#     `sionna_p4000000000_swR0D0E0F1_r18.72_n1024[_envoutdoor01_ground_alt12]_…_d3_el-36.7475_00.npz`.
#     ⚠The two spellings differ — this file writes `--range-m 18.720042735`, 0972 wrote `--range-m 18.7200427350` — so a duplicate scan
#     that compares flag TEXT misses it. Compare the stem the builder's own --dry-run prints, never the spelling.
#     ⇒ **This file keeps both lines** (it launches first and its anchor ladder needs that rung) and
#     runners/jobs_0972 has REMOVED them and reads these two shards instead — its header records that, and its exclusion is derived from
#     packages[0] of the campaign JSON, so if this file's anchor list ever stops covering that rung the two lines come back there by
#     themselves. ⛔If 0969 is cancelled, 0972 must be regenerated before it is installed.
#
# Dry-run, every line, before this file was written. runners/filter_jobs.sh (read-only), 2026-09-18 08:37:53-08:43:56 UTC (17:37-17:43 KST), on CPU with
#   CUDA_VISIBLE_DEVICES="" SIONNA2_ALLOW_CPU=1 MPLBACKEND=Agg nice -n 19 taskset -c 8-15, xargs -P 4:
#   ⭐**228 lines in → NEW 224 · DONE 4 · STALE 0 · BAD 0.** The four DONE cells are removed below, and one substitute is added (its
#   own line was dry-run separately, 2026-09-18 08:48 UTC: NEW), so the file carries {kept} lines.
#   ⭐Names: all {kept} stems were then read back from the sweep's own --dry-run namer, one call per line, and they are DISTINCT
#   ({kept} lines → {kept} stems, 0 unnamed; 2026-09-18 08:45-08:52 UTC), and NONE of them is present in outputs/elev_sweep_shards
#   (re-checked 2026-09-18 08:53 UTC, fifteen minutes after the dry-run, with the queues still landing cells in between).
#   ⭐**Re-checked 2026-09-18 08:57-09:10 UTC across all four stage-1 packages at once** (0969 + 0970 P3 + 0971 P8A + 0972 P2, 579
#   argument lines): runners/filter_jobs.sh gave **NEW 579 · DONE 0 · STALE 0 · BAD 0**, and a second pass captured 579 stems from the
#   builder's own --dry-run namer — 577 distinct, 0 already on disk. The two that are not distinct are this file's A11/A12 at
#   4e9 / depth 3 / seed 1 against 0972; they are recorded above and 0972 no longer carries them.
#   ⛔Re-run the dry-run before installing anyway: runners/jobs_0963 and 0966-0968 are still running, and a cell that lands in between
#   would be silently SKIPPED by the runner (elevation_sweep_md.py:870 「건너뜀」), not flagged.
#
# What exists, and what this file does NOT buy again.
{reuse_block}
#   ⭐⛔**One reused cell has NO path lists, and that is the one real hole in this package.** A01 at 4e9 / depth 2 / seed 1 is on disk
#     as runners/jobs_0963 line 142, which ran WITHOUT --dump-paths, and ⛔--dump-paths does not change the stem
#     (elevation_sweep_md.py tagr at :513-541 has no dump token) — the runners/jobs_0967 header records exactly this trap for exactly
#     this cell: «The open-sky R line CANNOT be bought: its stem is 0963 line 142's stem and a dump does not change it.» So the record
#     the matrix asks for (path lists at every position) cannot be bought under that name, and A01 is the anchor where it matters most:
#     it has the largest path list of the twelve — median 1,319 returned paths per position at 4e9, depth 2, read from the n_paths
#     array of outputs/path_provenance/sionna_p4000000000_swR0D0E0F1_r15_n4096_shell0.75mm_…_d2_el-15_00_prov.npz (2,048 positions),
#     against 278 at the 30 m open-sky anchor — i.e. the hardest convergence case in this file.
#   ⭐**The substitute, and it is the one deviation from the campaign matrix in this file:**
{subs}
#     --rep 1 changes the NAME only (elevation_sweep_md.py:516 and the --rep help at :2429), so the substitute is the same physics under
#     a stem of its own, and runners/jobs_0963's stored aspect-library shard is left untouched. ⛔The alternative — re-running that line
#     with --overwrite — was NOT taken: it would replace a shard that the 0963 azimuth library reads, with a re-solve that differs from
#     it (the runners/jobs_0957 header, line 85: «2.1-2.3 % path-count differences per rerun seen before»), i.e. it would move a stored
#     result in order to buy a sidecar.
#     ⚠What the substitute is not: it is not the same DRAW as 0963 line 142, so a budget_step read against it carries one re-run
#     difference. Gate R measures that difference before any step is read, and 0963's stored shard becomes its E-only rep partner
#     (lvl_db, ac_level_db, contrast — no class quantity, because it has no path list).
#   ⚠Three conditional lines in OTHER queue files name a cell this file buys. They are commented templates, not launched, and whichever
#     lands first the other must not be launched:
#     · runners/jobs_0962 line 115 (fade-library template)  = A04 · 4e9 · depth 2 · seed 1;
#     · runners/jobs_0965 line 222 (seed-2 open-sky follow-up) = A03 · 4e9 · depth 3 · seed 2;
#     · runners/jobs_0967 line 199 (the R branch's ground line) = A02 · 4e9 · depth 2 · seed 1.
#     Checked by parsing every argument line of every runners/jobs_*.txt (1,206 lines, comments and #HOLD included) into a flag set with
#     the sweep's own defaults folded in, and comparing cell identities; those three, plus the four DONE cells above, are the only hits.
#   Not bought here, on purpose: any n4096 or n8192 version of these cells; a second azimuth, range or elevation beyond the twelve;
#   max_depth 4; an iso or aim-offset version (that is 0966); a carrier ladder (0967); env scattering (0968); a fourth seed; a second
#   repeat; the rotor-model axis (that is package P8) and the sampling-rate axis (package P3), both of which sit behind this file's gate.
#
# Read-out — fixed before any shard of this file is read. Metric names are the repo's fixed ones: isolated_20xmedian, hampel_w51_k5,
#   env_field_drop_halfmedian, env_path_missing, copy_k_ratio / copy_k_diff, contrast_raw / contrast_dedup / contrast_interp
#   (docs/READOUT_0917.md section 1); E_B, drone paths, environment-only paths, contrast_gated, env_in_bin_db, event positions,
#   event_in_bin, event_share (runners/jobs_0957 header); lvl_db, ac_level_db, ac_to_static_db, hits_per_pose, path_class,
#   class_power_db, seed_diff (runners/jobs_0960 header); D2, excess_cm, m_c (runners/jobs_0962 header); coh_tot_db, class_sum_db,
#   phi_c, resolve_diff, spread (runners/jobs_0965 header). B = 20 and 100 MHz, Hann window, rectangular as the knob; a verdict on which the two windows disagree
#   is not written. Four new names, each defined here where it first appears:
#   budget_step(q)   q at 4e9 minus q at 2e9, at the same anchor, depth and seed — the step between the two largest budgets.
#   depth_step(q)    q at max_depth 3 minus q at max_depth 2, at the same anchor, budget and seed.
#   seed_spread(q)   max over seeds 1, 2, 3 of q, minus the min, at the same anchor, budget and depth.
#   rep_diff(q)      |q(rep 1) − q(rep 0)| at 4e9 / depth 3 / seed 1 — one plain re-run of the identical cell. ⚠PathSolver is not
#                    deterministic (NVlabs issue #1175), so this is not zero and it is the floor under every other step above.
#   0.  integrity, first, on the first sidecar of each scene: at every position |Σ_hit a·exp(−j2π·fc·τ) − E| / |E| < 1e-4 (check 0 of
#       the runners/jobs_0957 header), with the n_dup > 0 count reported. Already passed on the eleven sidecars of runners/jobs_0965
#       (on disk 2026-09-18 06:33-07:30 UTC); repeated here on one open-sky and one ground sidecar because this file adds max_depth 3
#       in open sky and three new ranges.
#   C.  cap, EVERY shard: n_trunc[0] = 0 against the 2,000,000 path cap. Any position at the cap ⇒ no level is quoted from that shard
#       and that cell is dropped from every reading below — the standing rule that a saturating cap makes the axis unmeasurable. The
#       expectation, from the stored sidecars, is three orders of magnitude of headroom: the median n_paths per position of the stored
#       4e9 partners of these anchors runs 278 (30 m open sky, depth 3) to 2,464 (15 m ground alt 5.4, depth 2). It is an expectation,
#       not a threshold.
#   R.  repeat first, before any other reading, at every anchor: rep_diff and seed_spread of class_power_db per class, of the class
#       ratios, of excess_cm, of lvl_db, of ac_to_static_db and of coh_tot_db. ⛔Any budget_step or depth_step smaller than
#       max(rep_diff, seed_spread) at that anchor is written «not told apart from a re-run» and crosses nothing, whatever its sign.
#   G1. class ratio, the pre-set tolerance PROPOSED in the recommendations (section 4, «사전 제안 기준»). It is an engineering
#       tolerance of this project, ⛔not a statement about physical accuracy: at an anchor, |budget_step(class_power_db(c) −
#       class_power_db([d]))| ≤ 1 dB for every class c that carries at least 1 % of the in-bin power ⇒ «the class ratios at this
#       anchor are stable between 2e9 and 4e9 rays (threshold not crossed)». ⚠A step under 1 dB that is ALSO under max(rep_diff,
#       seed_spread) is written «not told apart from a re-run» (gate R) and is not counted as evidence of stability either: it means
#       only that this file cannot see it.
#   G2. main delay, same source: |budget_step(excess_cm(c))| ≤ 0.1 range bin at the same classes ⇒ «the class delays at this anchor are
#       stable between the two largest budgets (threshold not crossed)». One bin is c/B of round-trip path: 14.99 m at 20 MHz and
#       3.00 m at 100 MHz, so 0.1 bin is 149.9 cm and 30.0 cm. The 100 MHz figure is the one gated; the 20 MHz figure is printed beside
#       it and gates nothing.
#   G3. ⭐shake the two thresholds, per the same paragraph, and print the verdict at each rung BEFORE choosing one: the class-ratio
#       tolerance at 0.5 / 1 / 2 dB and the delay tolerance at 0.05 / 0.1 / 0.2 bin. If which anchors pass changes between 0.5 and
#       2 dB, or between 0.05 and 0.2 bin, then ⛔no single headline tolerance is written at all: the table of rungs is the result,
#       and the later files quote the rung they used.
#   G4. depth: depth_step of every quantity in R, at 4e9, separately for classes that exist at depth 2 and for classes that only
#       max_depth 3 can return ([g,d,g]). ⚠The question is not «did new paths appear» — they must — but how far the ALREADY PRESENT
#       lower-order classes move when the depth is raised. Both are reported, never merged.
#   G5. the two orders, [g,d] against [d,g], at every ground anchor and every budget: class_power_db, excess_cm, the count of listed
#       paths in each, and the specular/diffuse interaction split. ⛔The interaction TYPE per hit is not in today's sidecar (it stores
#       part, obj_raw, prim, a, tau — benchmark/elevation_sweep_md.py:1253-1271), so the specular/diffuse split needs the sidecar
#       schema extended first. Until it is, this file reports the two orders by count, power and delay only, and writes no cause.
#   G6. ⭐the spread against what the later files want to claim, the second half of the same paragraph: beside every anchor, print
#       max(rep_diff, seed_spread, |budget_step|) for the class ratios and for excess_cm next to the effect sizes the later files
#       intend to read. The ones already on record, read out of outputs/readout_0918.json: gates.0962.AS D2_minus_D2_az0 = 7.774 dB
#       (the az 0 → 90 change in D2, i.e. in the measured-minus-computed ghost/direct ratio, which is what P2 and P5 want to read),
#       gates.0963.S1 seed_diff_lvl_db = 5.848 dB and lvl_db_spread = 26.340 dB over ten azimuths, and gates.0961.R2 step
#       «15 m @ 1e9 → 15 m @ 4e9» delta_contrast_raw = 2.251 dB. ⛔A quantity whose spread here is not clearly under the effect a later file wants to
#       claim is listed «not readable at the planned effect size», and that later file drops it or raises its budget. It is not
#       carried forward with a footnote.
#   ⚠Every median in this read-out is written with the FRACTION of positions that cross the same threshold, never a median alone —
#     a median hides a mixture, and these records mix poses where a class exists with poses where it does not. Anchors are never
#     pooled with each other, and ground is never pooled with open sky.
#   Written per cell, not gated, and never used as a verdict: hits_per_pose; n_paths median, max and n_trunc[0]; lvl_db, ac_level_db,
#   ac_to_static_db; contrast_raw, contrast_dedup, contrast_interp; hampel_w51_k5; isolated_20xmedian with its normaliser and |m|;
#   copy_k_ratio and copy_k_diff; class_power_db for every listed class by part and delay; env_in_bin_db and contrast_gated; and, for
#   ground cells against the open-sky cell of the SAME anchor pair, budget, depth and seed, env_field_drop_halfmedian, env_path_missing
#   and scene − sky in the bin. ⚠Never against a different seed: the open-sky field moves with the seed (the 0960/0962/0965 rule).
#   ⚠contrast depends on record length. Every cell here is n1024, so the FFT bin is PRF/n = 19.238 Hz and each ±2-bin comb window is
#     38.5 Hz wide; the record is 51.98 ms, about 6.6 blade-flash periods. ⛔Never put an n1024 contrast beside an n4096 or n8192 one.
#
# Scope in every sentence: one airframe (matrice4e revision 0), one carrier (3.5 GHz), one slab (0.75 / 1.43 mm), one antenna model
#   (tr38901 as a stand-in until the real pattern arrives), aimed at the drone, hover only with constant RPM, ground = one flat
#   120 x 120 m plate with ITU concrete and scattering coefficient S = 0, diffraction and refraction off (R0D0E0F1). These are stored
#   simulation results; nothing here is an RF measurement, and no absolute level from these shards is converted to an RCS or a
#   detection range.
#
# Cost, per anchor. Sidecar bytes are on-disk, compressed bytes; solve seconds are worker seconds.
#   | anchor | lines | sidecars | solve |
#   |---|---:|---:|---:|
{costs}
# ----------------------------------------------------------------------------------------------------------------------
# Estimate {h_lo:.0f} slot-h, band {h_lo:.0f}-{h_hi:.0f}. Basis, all from stored shards, not from a rule of thumb:
#   · seconds/pose at 4e9 rays with this slab on sionna-rt 2.1.0, median of meta[5]/len(idx) over every stored shard of the class:
#     depth-2 open sky {SEC_PER_POSE_4E9[(2, 'sky')]:.3f} (113 shards), depth-2 ground {SEC_PER_POSE_4E9[(2, 'ground')]:.3f} (26), depth-3 ground {SEC_PER_POSE_4E9[(3, 'ground')]:.3f} (14).
#     ⭐Depth-3 OPEN SKY has exactly one stored shard (0.326 s/pose, runners/jobs_0965 line 1), too few for a median, so it is carried
#     as depth-2 open sky x the measured depth-3/depth-2 ground ratio 1.737/1.365 = 1.273 ⇒ {SEC_PER_POSE_4E9[(3, 'sky')]:.3f} s/pose. That single
#     number is an extrapolation and it is the largest soft spot in this estimate ({sum(1 for a, s, d, _sd, _r in recs if d == 3 and a['scene'] == 'sky')} of the {kept} lines use it).
#   · ⭐Cost at 4e9 rays does NOT depend on the range: the depth-2 open-sky medians are 0.722 / 0.745 / 0.751 / 0.747 s/pose at
#     15 / 30 / 60 / 100 m (83 / 18 / 6 / 4 shards). The ray launch sets the cost, not the number of paths found, which is why the
#     45 m and steep-corner anchors are not cheaper per pose than the 15 m ones.
#   · budget: taken as linear in spp. Support: 30 m el −15 open sky depth 2 ran 0.175 s/pose at 1e9 against a 0.737 median at 4e9
#     (0.237 of it, against 0.250 for linear). ⚠The 15 m el −15 pair disagrees — 0.309 / 0.340 at 1e9 against a ~0.75 median at 4e9,
#     i.e. 0.43 rather than 0.25 — so the 1e9 and 2e9 lines may cost up to 1.7x what is written. The upper band applies that 1.7x to
#     the 1e9 and 2e9 lines only and leaves the 4e9 lines alone. Both figures include 0.5 min per shard of scene build and startup,
#     the allowance the runners/jobs_0965 header used for the same scenes; that is 1.9 h over {kept} shards.
#   · ⛔This is a sum of worker slot-hours. It is NOT an elapsed time and it is not divided by the number of cards. The measured spread
#     at ONE setting is large and it is card sharing, not work: two 2,048-position depth-2 open-sky shards at 30 m el −5 with identical
#     flags store 1,562.5 s and 522.8 s of solve time (26.0 and 8.7 min) in meta[5], and the depth-2 open-sky class spans
#     0.255-1.048 s/pose (q1 0.597, q3 0.802) over 113 shards.
#   The 09-18 recommendations put P1 at 60-160 worker-hours for the full 228 records. This file is {kept} lines after dedup and its
#   arithmetic gives {h_lo:.0f}-{h_hi:.0f} h; the difference is that the recommendation carried a design margin and did not yet know that
#   cost is flat in range or that the ray budget scales it down. ⚠Neither figure is a measured run of these cells, and the measured
#   wall clock of a shard is set mostly by how many workers share its card.
# Disk. About {gb:.2f} GB of path sidecars (outputs/path_provenance/, git-ignored since 0957), plus the shard npz files themselves,
#   which are 36.9 kB each on average (measured over the eleven stored n1024 depth-3 cells of runners/jobs_0965: 36,481-37,802 B),
#   so {kept} x 36.9 kB = {kept*36910.7/1e6:.1f} MB. Free on /workspace, measured 2026-09-18 08:52 UTC: 1,041 GB (df), so this package is {gb/1041*100:.2f} % of it.
#   How the sidecar figure was obtained, and ⛔where the brief is wrong: the sidecars are written with np.savez_compressed
#   (elevation_sweep_md.py:1253), so the on-disk cost is NOT the raw array size. Measured on the 30 m el −5 ground alt 4.11 depth-3
#   n1024 sidecar: raw arrays 39,561,264 B for 564,758 paths = 70.0 B/path, file on disk 4,115,631 B = 7.29 B/path, i.e. 9.61x
#   compression. The «about 52 B per path per position» in the stage-1 brief is the RAW depth-2 per-path size
#   (a 8 + tau 8 + part 2x2 + obj_raw 2x8 + prim 2x8 = 52 B exactly); on disk it is 5.7-8.8 B/path across the nine stored 4e9 cells
#   that were measured. The brief's own parenthetical («an n4096 depth-3 ground shard is 8.4 MB for 2,048 positions») is the on-disk
#   number and it is right: 8,363,270 B / 2,048 = 4,084 B/position. This file's estimate uses the on-disk measurements only.
#   Per-position sidecar bytes used, all measured at 4e9 depth 2 from outputs/path_provenance: 15 m el −15 sky 10,283 / ground 21,339;
#   30 m el −5 sky 1,610 / ground 3,313; 30 m el −15 sky 2,226 / ground 4,564; 60 m el −5 sky 510 / ground 921. Depth 3 is x1.233
#   (ground, 4,084/3,313 at one geometry) and x1.083 (sky, 1,743/1,610). ⚠The 45 m and steep-corner anchors have NO stored sidecar and
#   are extrapolated by R^-2 from the nearest measured elevation. ⚠The one stored pair that tests that law says it is LOW: 30 m el −5
#   open sky 1,610 x (30/60)² predicts 402 B/position against 510 measured at 60 m, i.e. 21 % low — and that measured point is at a
#   different azimuth (45°), so it is not a clean test either. Read the eight extrapolated anchors' disk figures as ±30 %. Those six anchors (A07-A12) are {sum(1 for a, s, d, _sd, _r in recs if int(round(a['range_m'])) not in (15, 30)) / max(kept,1) * 100:.0f} % of the lines.
# Cards. No card restriction is requested here. runners/GPU_HOLD.json decides which cards are in play and the supervisors re-read it
#   every round; nothing in this file asks for a particular card, and nothing in it touches a queue, a supervisor or a worker.
"""


def main():
    anch = anchors()
    upper = check_against_plan(anch)
    recs = all_records(anch)
    if len(recs) != upper:
        raise SystemExit(f"emitted {len(recs)} records, matrix says {upper}")

    reused = load_reused()
    for key in reused:
        if not any((r[0]["tag"], r[1], r[2], r[3], r[4]) == key for r in recs):
            raise SystemExit(f"⛔ reuse entry {key} is not a cell of the matrix")
    by_tag = {a["tag"]: a for a in anch}
    kept = [r for r in recs
            if (r[0]["tag"], r[1], r[2], r[3], r[4]) not in reused]
    for tag, spp, dep, sd, rep in SUBSTITUTES:
        sub = (by_tag[tag], spp, dep, sd, rep)
        if any((r[0]["tag"], r[1], r[2], r[3], r[4]) == (tag, spp, dep, sd, rep) for r in kept):
            raise SystemExit(f"⛔ substitute {tag} {spp} d{dep} s{sd} rep{rep} is already a line")
        kept.append(sub)

    lines = [line(a, s, d, sd, r) for a, s, d, sd, r in kept]
    if len(set(lines)) != len(lines):
        raise SystemExit("⛔ duplicate argument line inside this file")

    byt, sec, hi = cost(kept)
    txt = header(anch, kept, reused, byt, sec, hi, upper) + "\n".join(lines) + "\n"
    with open(OUT, "w") as fh:
        fh.write(txt)

    print(f"anchors {len(anch)}  matrix {upper}  reused {len(reused)}  written {len(kept)}")
    for a in anch:
        print(f"  {a['tag']}  R={a['range_m']:.10g}  el={a['el_deg']:.10g}  az={a['az_deg']:.0f}  "
              f"{a['scene']:6s}  env-alt={'-' if a['env_alt_m'] is None else format(a['env_alt_m'], '.10g')}"
              f"  radar h={'-' if a['radar_h_m'] is None else format(a['radar_h_m'], '.4f')}")
    print(f"sidecars {byt/1e9:.3f} GB   solve {sec/3600.0:.1f} slot-h (band to {hi/3600.0:.1f})")
    print(f"-> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
