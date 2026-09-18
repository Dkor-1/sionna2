#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""0972 generator — P2 coarse, the physical mast-height geometry map (2026-09-18).

Stage 1 of the GPU campaign, package P2 *coarse only*.
  brief  : /workspace/sionna_queue_recommendations_2026-09-18.md  section 5 (P2), 13 (stage 1), 14 (evaluation contract)
  matrix : /workspace/sionna_gpu_campaign_plan_2026-09-18.json     packages[1].coarse_dimensions, coarse_count = 216

WHY A GENERATOR AND NOT A HAND-TYPED LIST
  Anything that lands in runners/ or outputs/ has to be rebuildable from code. Every one of the 216 argument lines
  below is produced from the five lists in the campaign JSON by one nested loop plus the geometry conversion. The
  header table is computed here too, so the table and the lines cannot drift apart.

WHAT THIS FILE BUYS
  Horizontal distance D x drone height H x mast height h x azimuth x {open sky, ground plate}
  = 3 x 3 x 3 x 4 x 2 = 216 n1024 depth-3 records, path list dumped at every position, one solver seed
  (the default 1, no tag), constant-rpm rotor (no --rotor-preset anywhere), the canonical thin slab.

THE CONVERSION, AND WHY IT IS THE ONLY HONEST ONE
  runners/jobs_0965 moves the ground plate, so the drone height H and the radar height h move TOGETHER and only
  their sum changes; it cannot answer "how high should the tripod stand". The sweep's own geometry is:
    benchmark/report15_probe.py place()            radar = drone_centre + range * (cos el cos az, cos el sin az, sin el)
    benchmark/elevation_sweep_md.py:1071           place(..., baseline=0.0)  -> TX and RX are CO-LOCATED
    benchmark/elevation_sweep_md.py env_parts()    every environment part is lowered by --env-alt; the drone stays at the origin
  so, with the drone at the origin and the plate at z = -H,
    range   = sqrt(D^2 + (h - H)^2)
    el      = degrees(atan2(h - H, D))          (negative: the radar is BELOW the drone and looks up)
    env-alt = H
    radar height above the plate = H + range * sin(el) = H + (h - H) = h        <- asserted numerically below
  Only h changes between the three mast rows of one (D, H); D and H are held.

MEASURED INPUTS (all read by me from stored shards on 2026-09-18, not taken from any note)
  Every anchor below is runners/jobs_0965 at exactly the settings of this file (4e9 rays, R0D0E0F1, tr38901,
  shell 0.75 / prop 1.43 mm, max_depth 3, n1024, --dump-paths 1024, one shard), differing only in geometry:
    outputs/elev_sweep_shards/sionna_p4000000000_swR0D0E0F1_r30_n1024_envoutdoor01_ground_alt<A>_..._d3_el-5_00.npz
      meta[5]/len(idx) for A in 3.91 .. 4.31 and the ss2 repeat, ten shards:
      0.6139 1.2174 1.3848 1.5353 1.6652 1.7644 1.7655 1.7799 1.8173 1.8483 s/position  (median 1.7148)
      sidecars outputs/path_provenance/<same stem>_prov.npz: 3777.0 .. 4377.7 B/position (median 4023.8),
      538.0 .. 593.4 paths/position, 7.02 .. 7.38 B per stored path
    outputs/elev_sweep_shards/sionna_p4000000000_swR0D0E0F1_r30_n1024_..._d3_el-5_00.npz  (open sky, one shard)
      0.3256 s/position; sidecar 1743.1 B/position, 270.5 paths/position, 6.44 B per stored path
  Range and elevation scaling of the sidecar size is fitted from the depth-2 population at the same settings
  (see _DISK_FIT); the runtime is NOT scaled with range, because at a fixed 4e9-ray budget the stored s/position
  shows no range trend (open-sky depth 2, 4e9: r15 0.72-1.05, r30 0.74-0.76, r60 0.47-0.76, r100 0.36-0.76).

Usage:  python3 make_jobs_0972_mast_height_coarse_geometry_map.py > jobs_0972_mast_height_coarse_geometry_map.txt
"""
from __future__ import annotations

import json
import math
import os
import sys

CAMPAIGN_JSON = "/workspace/sionna_gpu_campaign_plan_2026-09-18.json"

# --- fixed solver/material settings, identical on every line ---------------------------------------------------
SPP = 4_000_000_000
SW = "R0D0E0F1"
DEPTH = 3
NPOSES = 1024
ENV = "outdoor01_ground"
ANT = "tr38901"
SHELL_MM = "0.75"
PROP_MM = "1.43"

# --- the ground plate, read from benchmark/make_outdoor_scene_0831.py ------------------------------------------
#     plane(0, 0, 0.0, 120.0, 120.0) -> a 120 x 120 m square centred on the drone's nadir, so |x|, |y| <= 60 m.
PLATE_HALF_M = 60.0

# --- measured anchors (see the module docstring for the file names) --------------------------------------------
GROUND_SPP_S = [0.6139, 1.2174, 1.3848, 1.5353, 1.6652, 1.7644, 1.7655, 1.7799, 1.8173, 1.8483]
SKY_SPP_S = [0.3256]
SKY_D2_MEDIAN_S = 0.755          # open sky depth 2, r30, 4e9, median of the stored s/position
D2_TO_D3 = 1.237                 # measured in ground at r30 el-5, n2048: (1.737+1.763)/(1.389+1.441)
GROUND_B_PER_POS = 4023.75       # median of the ten depth-3 ground sidecars above
SKY_B_PER_POS = 1743.1           # the one depth-3 open-sky sidecar above
# sidecar scaling, fitted by me from the stored depth-2 sidecars at these settings:
#   range   bytes/position at r15 el-5 7960 vs r30 el-5 1608  -> exponent 2.31;  r15 el-15 10259 vs r30 el-15 2240 -> 2.20
#   el      r30 open sky: 1494 (2.5 deg) 1608 (5) 1905 (10) 2240 (15) -> +3.71 %/deg;  r15: 7960 (5) -> 10259 (15) -> +2.89 %/deg
#   azimuth r30 ground: az90/az0 = 1.20, az180/az0 = 1.03  -> a mean allowance of 1.06
_DISK_FIT = dict(range_exp=2.25, el_slope_per_deg=0.033, az_allowance=1.06)

# --- the dry-run I actually ran, recorded here so the header cannot claim more than was checked --------------------
#     cd /workspace/sionna && grep -vE "^\s*(#|$)" jobs_0972_....txt \
#       | xargs -d"\n" -P 4 -I{} env CUDA_VISIBLE_DEVICES="" SIONNA2_ALLOW_CPU=1 MPLBACKEND=Agg \
#           nice -n 19 taskset -c 8-15 runners/filter_jobs.sh {}
DRYRUN = dict(when="2026-09-18 08:35-08:52 UTC", new=216, done=0, stale=0, bad=0,
              stems_unique=216, stems_on_disk=0,
              dup_scan="1,139 argument-like lines, commented and #HOLD included")

# --- the independent re-check of all four stage-1 packages together (2026-09-18) ---------------------------------
#     Same command, same pinning, same -P 4; 579 lines = 225 (0969) + 30 (0970) + 108 (0971) + 216 (this file).
RECHECK = dict(when="2026-09-18 08:57-09:10 UTC", lines_all_four=579, stems_distinct=577, stems_on_disk=0)

# --- ⛔ CELLS THIS FILE SHARES WITH runners/jobs_0969 (package P1) -----------------------------------------------
#     Found by the 2026-09-18 adversarial cross-check of the four stage-1 packages, NOT by either generator on its
#     own: each of them compared itself only against runners/jobs_*.txt, so neither saw the other.
#     P1 (campaign JSON packages[0]) takes the steep corner of THIS grid as its anchors A11/A12 — the JSON stores
#     them as range 18.720042734993957 m, el -36.747470952863914 deg, az 0, open sky and ground with env-alt 12,
#     which is exactly (D 15, H 12, h 0.8) of this matrix — and crosses them with spp {1e9, 2e9, 4e9} x depth {2, 3}
#     x solver seed {1, 2, 3} at n1024. Its 4e9 / depth-3 / seed-1 rung therefore carries the SAME flags as two
#     lines of this file and, because `_r{:g}` keeps six significant digits, the SAME stem:
#         sionna_p4000000000_swR0D0E0F1_r18.72_n1024_..._d3_el-36.7475_00.npz                        (open sky)
#         sionna_p4000000000_swR0D0E0F1_r18.72_n1024_envoutdoor01_ground_alt12_..._d3_el-36.7475_00  (ground)
#     Same flags means same physics, so neither cell is wrong — but two queue lines naming one shard means the
#     second one to reach a worker is silently SKIPPED (elevation_sweep_md.py:870 「건너뜀」), not flagged.
#     ⇒ 0969 keeps them (it is the file that launches first and its anchor ladder needs the rung), and this file
#       REUSES them. The two records still belong to this matrix: the header still counts 216 records, and the
#       holdout arithmetic below is unchanged, because the split unit is the record and not the queue line.
REUSE_FROM_0969 = dict(queue="runners/jobs_0969_reproducibility_budget_depth_seed.txt",
                       spp=4_000_000_000, depth=3, n_poses=1024, solver_seed=1)


def cells_reused_from_0969(cells) -> list:
    """Which of the 216 cells are bought by P1's anchor ladder instead. Derived, never typed.

    A cell is reused when P1's campaign-JSON anchor list contains an anchor with the same range, elevation,
    azimuth and scene (and, on the ground, the same --env-alt), AND this file's fixed spp / depth / n_poses
    are the ones P1's 4e9 / depth-3 / seed-1 rung uses.  If P1's matrix ever stops covering that rung the
    function returns nothing and every line comes back automatically.
    """
    with open(CAMPAIGN_JSON) as fh:
        plan = json.load(fh)
    p1 = [p for p in plan["packages"] if p.get("id") == "P1"]
    if len(p1) != 1:
        raise SystemExit("stop: expected exactly one P1 package in the campaign JSON")
    p1 = p1[0]
    if (REUSE_FROM_0969["spp"] not in p1["spp"] or REUSE_FROM_0969["depth"] not in p1["depths"]
            or REUSE_FROM_0969["solver_seed"] not in p1["solver_seeds"]
            or int(p1["n_poses"]) != REUSE_FROM_0969["n_poses"]):
        return []                                    # P1 no longer buys this rung -> nothing to reuse
    if (REUSE_FROM_0969["spp"], REUSE_FROM_0969["depth"], REUSE_FROM_0969["n_poses"]) != (SPP, DEPTH, NPOSES):
        return []                                    # this file no longer writes that rung -> no overlap
    hit = []
    for i, (g, az, ground, line) in enumerate(cells):
        for a in p1["anchors"]:
            if abs(float(a["range_m"]) - g["rng"]) > 1e-9:
                continue
            if abs(float(a["elevation_deg"]) - g["el"]) > 1e-9:
                continue
            if abs(float(a["azimuth_deg"]) - az) > 1e-9:
                continue
            if ground != (a["env_alt_m"] is not None):
                continue
            if ground and abs(float(a["env_alt_m"]) - g["H"]) > 1e-9:
                continue
            hit.append(i)
            break
    return hit


# --- holdout, from the brief section 5 --------------------------------------------------------------------------
HOLDOUT_H_M = 8.0
HOLDOUT_AZ_DEG = 90.0
# the six (D, H) pairs the brief fixes for the LATER 1 cm fine sweep; their h = 1.50 m, az 0 cells live in this file
FINE_PAIRS = [(15, 4), (15, 8), (30, 4), (30, 8), (45, 4), (45, 12)]
FINE_CENTRE_H_M = 1.5


def load_matrix() -> dict:
    """The five axes, read from the campaign JSON. No axis is typed here."""
    with open(CAMPAIGN_JSON) as fh:
        plan = json.load(fh)
    pkgs = [p for p in plan["packages"] if p.get("id") == "P2"]
    if len(pkgs) != 1:
        raise SystemExit(f"stop: expected exactly one P2 package in {CAMPAIGN_JSON}, found {len(pkgs)}")
    p2 = pkgs[0]
    dims = p2["coarse_dimensions"]
    m = dict(D=[float(x) for x in dims["horizontal_m"]],
             H=[float(x) for x in dims["drone_height_m"]],
             h=[float(x) for x in dims["mast_height_m"]],
             az=[float(x) for x in dims["azimuth_deg"]],
             scene=list(dims["scene"]),
             coarse_count=int(p2["coarse_count"]),
             n_poses=int(p2["n_poses"]),
             worker_hours=p2["worker_hours"])
    n = len(m["D"]) * len(m["H"]) * len(m["h"]) * len(m["az"]) * len(m["scene"])
    if n != m["coarse_count"]:
        raise SystemExit(f"stop: the JSON axes give {n} cells but coarse_count says {m['coarse_count']}")
    if m["n_poses"] != NPOSES:
        raise SystemExit(f"stop: the JSON says n_poses = {m['n_poses']}, this file writes {NPOSES}")
    if m["scene"] != ["sky", "ground"]:
        raise SystemExit(f"stop: unexpected scene axis {m['scene']}")
    return m


def geom(D: float, H: float, h: float) -> dict:
    """(D, H, h) -> the two numbers the CLI takes, plus the checks that make them readable."""
    dz = h - H
    rng = math.hypot(D, dz)
    el = math.degrees(math.atan2(dz, D))
    radar_h = H + rng * math.sin(math.radians(el))          # must come back as h
    # ground specular point of the single-bounce drone-ground path, by the image method: it sits on the
    # drone-nadir -> radar segment, at D * H / (H + h) from the nadir and D * h / (H + h) from the radar.
    spec_from_nadir = D * H / (H + h)
    return dict(D=D, H=H, h=h, rng=rng, el=el, radar_h=radar_h,
                spec=spec_from_nadir,
                margin_radar=PLATE_HALF_M - D,
                margin_spec=PLATE_HALF_M - spec_from_nadir,
                grazing=math.degrees(math.atan2(H + h, D)))


def arm_tokens(g: dict) -> tuple:
    """The r and el tokens the builder will actually put in the file name (%g, 6 significant digits).

    benchmark/elevation_sweep_md.py writes `_r{rng_m:g}` (:517) and `_el{el:+g}` (:866), so the stem keeps only
    six significant digits of each. Two cells that share both tokens would silently become one shard; the caller
    checks that all of them are distinct.
    """
    return (f"{g['rng']:g}", f"{g['el']:+g}")


def line_for(g: dict, az: float, ground: bool) -> str:
    """One argument line, in the flag order of runners/jobs_0964 and runners/jobs_0965."""
    parts = ["--engine sionna",
             f"--n-poses {NPOSES}",
             f"--range-m {g['rng']:.10f}",
             f"--sw {SW}",
             f"--spp {SPP}",
             f"--max-depth {DEPTH}",
             f"--els={g['el']:.10f}"]
    if ground:
        # --env-alt is only legal with --env (elevation_sweep_md.py:623-625), so the open-sky lines carry neither.
        parts += [f"--env {ENV}", f"--env-alt {g['H']:g}"]
    if az != 0.0:
        # az 0 is the builder default (elevation_sweep_md.py:376 falls back to the ledger's az_deg = 0.0) and
        # `--az-deg 0` would add an `_az0` tag to an otherwise identical cell. az 0 lines therefore omit the flag.
        parts += [f"--az-deg {az:g}"]
    parts += [f"--ant-pattern {ANT}",
              f"--shell-mm {SHELL_MM}",
              f"--prop-mm {PROP_MM}",
              f"--dump-paths {NPOSES}",
              "--shard 0", "--nshards 1"]
    return " ".join(parts)


def est_seconds(ground: bool) -> tuple:
    """(low, point, high) seconds per position. Runtime is not scaled with range: see the module docstring."""
    if ground:
        s = sorted(GROUND_SPP_S)
        med = 0.5 * (s[len(s) // 2 - 1] + s[len(s) // 2]) if len(s) % 2 == 0 else s[len(s) // 2]
        return s[0], med, s[-1]
    lo = min(SKY_SPP_S)
    return lo, lo, SKY_D2_MEDIAN_S * D2_TO_D3


def est_sidecar_bytes(g: dict, ground: bool) -> float:
    b0 = GROUND_B_PER_POS if ground else SKY_B_PER_POS
    f_r = (30.0 / g["rng"]) ** _DISK_FIT["range_exp"]
    f_el = 1.0 + _DISK_FIT["el_slope_per_deg"] * (abs(g["el"]) - 5.0)
    return NPOSES * b0 * f_r * max(f_el, 0.5) * _DISK_FIT["az_allowance"]


def build():
    m = load_matrix()
    cells = []                       # (g, az, ground, line)
    for D in m["D"]:
        for H in m["H"]:
            for h in m["h"]:
                g = geom(D, H, h)
                if abs(g["radar_h"] - h) > 1e-9:
                    raise SystemExit(f"stop: radar height {g['radar_h']} != mast height {h} at D{D} H{H}")
                if g["el"] >= 0.0:
                    raise SystemExit(f"stop: el {g['el']} is not negative at D{D} H{H} h{h}; every mast here is "
                                     "below the drone, so the radar must look UP")
                if g["margin_radar"] <= 0 or g["margin_spec"] <= 0:
                    raise SystemExit(f"stop: D{D} H{H} h{h} falls off the {2*PLATE_HALF_M:g} m ground plate")
                for ground in (False, True):
                    for az in m["az"]:
                        cells.append((g, az, ground, line_for(g, az, ground)))
    if len(cells) != m["coarse_count"]:
        raise SystemExit(f"stop: built {len(cells)} records, the JSON says {m['coarse_count']}")
    reused = cells_reused_from_0969(cells)

    # --- the checks whose results go into the header -------------------------------------------------------------
    geoms = []
    seen = {}
    for D in m["D"]:
        for H in m["H"]:
            for h in m["h"]:
                g = geom(D, H, h)
                geoms.append(g)
                tok = arm_tokens(g)
                if tok in seen:
                    raise SystemExit(f"stop: {seen[tok]} and (D{D},H{H},h{h}) both name _r{tok[0]}_..._el{tok[1]}_")
                seen[tok] = (D, H, h)
    assert len(seen) == 27
    # exact (range, el) pairs: an open-sky record depends on these and on az only, never on env-alt
    sky_keys = {(round(g["rng"], 12), round(g["el"], 12)) for g in geoms}
    # how close do two stems come, measured in units of the %g token step, so the 6-digit rounding can be judged.
    # %g keeps six significant digits, so the step at |v| is 10**(floor(log10|v|) - 5).
    def step(v):
        return 10.0 ** (math.floor(math.log10(abs(v))) - 5)
    tight = {"r": (1e18, None, 0.0), "el": (1e18, None, 0.0)}
    for i, a in enumerate(geoms):
        for b in geoms[i + 1:]:
            for k, key in (("r", "rng"), ("el", "el")):
                d = abs(a[key] - b[key])
                st = max(step(a[key]), step(b[key]))
                if d / st < tight[k][0]:
                    tight[k] = (d / st, ((a["D"], a["H"], a["h"]), (b["D"], b["H"], b["h"])), d)
    # the largest distance between an argument and the rounded copy of it that lands in the file name
    name_err_r = max(abs(g["rng"] - float(f"{g['rng']:g}")) for g in geoms)
    name_err_el = max(abs(g["el"] - float(f"{g['el']:+g}")) for g in geoms)
    tight["name_err_r"] = name_err_r
    tight["name_err_el"] = name_err_el
    tight["phase_deg"] = 2.0 * name_err_r / (299792458.0 / 3.5e9) * 360.0

    lines = [c[3] for c in cells]
    if len(set(lines)) != len(lines):
        raise SystemExit("stop: duplicate argument lines")

    # --- cost and disk ------------------------------------------------------------------------------------------
    hours = {"lo": 0.0, "pt": 0.0, "hi": 0.0}
    disk = 0.0
    for g, az, ground, _ in cells:
        lo, pt, hi = est_seconds(ground)
        hours["lo"] += NPOSES * lo / 3600.0
        hours["pt"] += NPOSES * pt / 3600.0
        hours["hi"] += NPOSES * hi / 3600.0
        disk += est_sidecar_bytes(g, ground)

    n_ground = sum(1 for c in cells if c[2])
    n_sky = len(cells) - n_ground
    # holdout bookkeeping, from the brief section 5
    hold_H = sum(1 for g, az, gr, _ in cells if g["H"] == HOLDOUT_H_M)
    hold_az = sum(1 for g, az, gr, _ in cells if az == HOLDOUT_AZ_DEG)
    hold_both = sum(1 for g, az, gr, _ in cells if g["H"] == HOLDOUT_H_M and az == HOLDOUT_AZ_DEG)
    train = len(cells) - hold_H - hold_az + hold_both
    fine_centres = sum(1 for g, az, gr, _ in cells
                       if az == 0.0 and g["h"] == FINE_CENTRE_H_M and (int(g["D"]), int(g["H"])) in
                       [(int(a), int(b)) for a, b in FINE_PAIRS])

    return (m, cells, geoms, sky_keys, tight, hours, disk, n_sky, n_ground,
            (hold_H, hold_az, hold_both, train), fine_centres, reused)


def header(m, cells, geoms, sky_keys, tight, hours, disk, n_sky, n_ground, hold, fine_centres, reused) -> list:
    hold_H, hold_az, hold_both, train = hold
    W = []

    def w(s=""):
        W.append(("# " + s).rstrip() if s else "#")

    w("0972 — P2 coarse: the physical mast-height geometry map. Horizontal distance D {15, 30, 45} m x drone height")
    w("       H {4, 8, 12} m x mast height h {0.8, 1.5, 2.2} m x azimuth {0, 90, 180, 270} deg x {open sky, ground")
    w("       plate} = 216 n1024 depth-3 records with the path list dumped at every position. Only h moves between")
    w("       the three mast rows of one (D, H): this is the tripod-height question that runners/jobs_0965 cannot ask.")
    w("       (2026-09-18 ~16:20 KST, stage 1 of /workspace/sionna_queue_recommendations_2026-09-18.md sections 5 and 13,")
    w("        matrix /workspace/sionna_gpu_campaign_plan_2026-09-18.json packages[1].coarse_dimensions, coarse_count 216)")
    w()
    w("Rebuilt by: make_jobs_0972_mast_height_coarse_geometry_map.py (the five axes are READ from the campaign JSON,")
    w("  not typed; the geometry table below is computed by the same script, so table and lines cannot drift apart).")
    w()
    w("WHY THIS FILE, AND WHY IT IS NOT 0965 AGAIN.")
    w("  benchmark/elevation_sweep_md.py env_parts() lowers EVERY environment part by --env-alt and leaves the drone at")
    w("  the origin. So 0965, which sweeps --env-alt at a fixed range and elevation, moves the drone AND the radar")
    w("  relative to the ground by the same amount: the quantity it varies is the SUM H + h. A tripod ladder has to")
    w("  move h alone, which changes the slant range and the elevation as well. That is what the conversion below does,")
    w("  and it is why every mast height needs its own open-sky partner rather than sharing one.")
    w()
    w("GEOMETRY, COMPUTED FROM THE CODE, NOT FROM A NOTE.")
    w("  benchmark/report15_probe.py place() (:215) puts the radar at")
    w("      centre + range * (cos el cos az, cos el sin az, sin el)")
    w("  and benchmark/elevation_sweep_md.py:1071 — its only place() call — passes baseline=0.0, so TX and RX are")
    w("  CO-LOCATED and report15_probe's module default BASELINE_M = 0.20 m is NOT used by this sweep. The drone sits")
    w("  at the origin (elevation_sweep_md.py:1034 _ctr = (0,0,0)) and env_parts() puts the plate at z = -(--env-alt).")
    w("  Therefore, with --env-alt = H:")
    w("      range = sqrt(D^2 + (h-H)^2)      el = degrees(atan2(h-H, D))      radar height above plate = H + range*sin(el)")
    w("  Every mast here is below the drone, so h - H < 0 and el < 0 on all 216 lines: a NEGATIVE elevation means the")
    w("  radar is BELOW the drone and looking up. The generator asserts el < 0 and |H + range*sin(el) - h| < 1e-9 for")
    w("  all 27 geometries before a single line is written; the last column of the table is that computed radar height.")
    w()
    w("  D[m]  H[m]  h[m] |     range[m]        el[deg]   | radar h above plate[m] | specular pt from nadir[m]  plate margin[m]")
    w("  -----------------+-----------------------------+------------------------+------------------------------------------")
    for g in geoms:
        W.append("#  {:4.0f}  {:4.0f}  {:4.2f} | {:14.10f} {:14.10f} | {:22.12f} | {:12.4f} {:16.4f}".format(
            g["D"], g["H"], g["h"], g["rng"], g["el"], g["radar_h"], g["spec"],
            min(g["margin_radar"], g["margin_spec"])))
    w("  Each row is bought at four azimuths and in two scenes: 27 x 4 x 2 = 216 lines.")
    w()
    w("ARM-NAME PRECISION. The builder writes `_r{range:g}` (elevation_sweep_md.py:517) and `_el{el:+g}` (:866), i.e.")
    w("  six significant digits, so the stem carries a ROUNDED copy of the arguments; the exact arguments are the ten")
    w("  decimals on the lines below and in the generator. All 27 (r, el) token pairs are distinct — checked in the")
    w("  generator, which aborts on a collision. The two closest geometries of the whole matrix, measured in units of")
    w("  the token step itself — six significant digits, so the step is 1e-4 for a value in [10, 100) and 1e-5 in [1, 10):")
    w("    range      {:.1f} token steps apart ({:.6f} m: D{:g} H{:g} h{:g} vs D{:g} H{:g} h{:g})".format(
        tight["r"][0], tight["r"][2], *tight["r"][1][0], *tight["r"][1][1]))
    w("    elevation  {:.1f} token steps apart ({:.6f} deg: D{:g} H{:g} h{:g} vs D{:g} H{:g} h{:g})".format(
        tight["el"][0], tight["el"][2], *tight["el"][1][0], *tight["el"][1][1]))
    w("  The physics uses the full-precision argument on the line; only the NAME is rounded. Largest difference")
    w("  between an argument and the copy of it that lands in the stem: {:.2e} m in range and {:.2e} deg in".format(
        tight["name_err_r"], tight["name_err_el"]))
    w("  elevation, i.e. {:.2f} deg of two-way phase at 3.5 GHz. ⛔So (D, H, h) is recovered from the header table or".format(
        tight["phase_deg"]))
    w("  the generator, never by reading the stem back to ten decimals.")
    w("  The new stems parse and round-trip under src/arm_grammar.py with no warnings (checked on three of them,")
    w("  one per D, on 2026-09-18: parse() then unparse() gives the name back character for character), and every")
    w("  stem ends in _rt210 from build_tag(), so nothing here can be silently skipped onto an older solver build.")
    w()
    w(f"OPEN-SKY PARTNERS. An open-sky record has no ground, so it does not depend on --env-alt at all; it depends on")
    w(f"  range, elevation and azimuth. Those 27 (range, el) pairs are all distinct as exact floats ({len(sky_keys)} of 27), because")
    w("  the nine (H, h) combinations give nine distinct h - H values (-1.8, -2.5, -3.2, -5.8, -6.5, -7.2, -9.8, -10.5,")
    w("  -11.2 m). So every (D, H, h) needs its OWN sky partner and none of them can be shared — the file carries")
    w(f"  {n_sky} open-sky and {n_ground} ground lines. ⛔The open-sky lines carry no --env and therefore no --env-alt:")
    w("  elevation_sweep_md.py:623-625 rejects --env-alt without --env («--env-alt 는 --env 와 함께 준다»).")
    w()
    w("GROUND PLATE. benchmark/make_outdoor_scene_0831.py builds the ground as plane(0, 0, 0.0, 120.0, 120.0): a")
    w("  120 x 120 m square centred on the drone's nadir, so |x|, |y| <= 60 m. --env outdoor01_ground loads that plate")
    w("  and nothing else (ENV_SPECS[\"outdoor01_ground\"], elevation_sweep_md.py:139-141), so no building or pole is in")
    w("  any of these scenes and the only extent to check is the plate.")
    w("    · the radar stands at horizontal distance D from the nadir, so the worst case is D = 45 m: 15.0 m inside the edge;")
    w("    · the single-bounce ground point lies on the nadir-to-radar segment at D*H/(H+h) from the nadir, so the worst")
    w("      case is D = 45, H = 12, h = 0.8: 42.1875 m from the nadir, 17.8125 m inside the edge. Every ground")
    w("      interaction point of a radar-ground-drone path lies between the nadir and the radar and is therefore")
    w("      closer than the radar itself. Nothing in the matrix is dropped or flagged: the smallest margin over all")
    w("      216 lines is 15.00 m.")
    w("  ⚠This says the plate is large enough to hold the specular geometry. It does not say the plate EDGE is silent:")
    w("    the edge is a real discontinuity in this mesh and stays 15 m away at worst, about 2.4 range cells at 100 MHz.")
    w()
    w("HOLDOUT (brief section 5: «학습·선택에 쓰는 geometry와 최종 평가 geometry를 분리합니다…")
    w("  H8 m 및 az90°를 holdout으로 지정하고 교차된 (H8, az90)를 별도 평가합니다» — keep the geometry used to fit")
    w("  or choose separate from the geometry used to evaluate; H 8 m and az 90 deg are held out and their crossing")
    w("  is evaluated on its own).")
    w(f"    · selection / fitting set : {train} lines (H in {{4, 12}} m AND az in {{0, 180, 270}} deg)")
    w(f"    · held out, H = 8 m only  : {hold_H - hold_both} lines")
    w(f"    · held out, az = 90 deg only : {hold_az - hold_both} lines")
    w(f"    · the crossed cell (H 8 m, az 90 deg), evaluated separately : {hold_both} lines")
    w(f"    · {train} + {hold_H - hold_both} + {hold_az - hold_both} + {hold_both} = {len(cells)}")
    w("  ⛔Adjacent rotor poses of ONE geometry are never split into train and test. The unit of the split is the")
    w("    geometry (one line = one record = one 1,024-position rotor run); overlapping CPIs inside a record are not")
    w("    independent experiments (brief section 14, «인접 pose와 겹치는 CPI는 독립 실험 수가 아님»).")
    w()
    w("WHAT THIS FILE DOES NOT BUY.")
    w("  · the 1 cm fine mast sweep (h 1.40-1.60 m, 21 points, 6 (D,H) pairs, 240 further records). It is NOT stage 1.")
    w("    Its 12 centre cells ARE in this file already — the six (D, H) pairs "
      + ", ".join(f"({int(a)},{int(b)})" for a, b in FINE_PAIRS))
    w(f"    at h = 1.50 m, az 0, sky and ground, {fine_centres} lines — when the fine sweep is ordered it must skip them,")
    w("    exactly as the brief's")
    w("    «252개 조건 중 중심 h1.50 m의 12개는 coarse에서 재사용하므로 240개 추가» arithmetic assumes.")
    w("  · any second solver seed, any --rep repeat, any rotor preset or rotor seed (all lines take the constant-rpm")
    w("    branch, elevation_sweep_md.py:411), any depth-2 partner, any iso arm, any second carrier, any thickness")
    w("    other than the canonical 0.75 / 1.43 mm, any full outdoor01 scene, any --env-scat. P1 owns seed and budget")
    w("    spread; P7 owns thickness; this file owns geometry only, so that a difference here is a difference in geometry.")
    w("  · ⚠and therefore this file cannot separate a geometry effect from solver spread on its own. The 0963 seed")
    w("    difference of 5.85 dB and the 0961 ray-budget comb difference of 2.25 dB (outputs/readout_0918.json gates")
    w("    .0963.S1 / .0961.R2) are the reason P1 runs first and sets what may be read off these 216 records.")
    w()
    n_lines = len(cells) - len(reused)
    w("DRY-RUN, {} (CPU only, GPUs hidden, read-only): runners/filter_jobs.sh on all {} lines reports".format(
        DRYRUN["when"], len(cells)))
    w("  NEW {} · DONE {} · STALE {} · BAD {}. Nothing on disk is reused: every (range, el) of this matrix is a".format(
        DRYRUN["new"], DRYRUN["done"], DRYRUN["stale"], DRYRUN["bad"]))
    w("  new geometry. A second pass captured the {} stems the builder would write — all {} distinct, {} of them".format(
        DRYRUN["stems_unique"], DRYRUN["stems_unique"], DRYRUN["stems_on_disk"]))
    w("  present in outputs/elev_sweep_shards/. Separately, none of the {} lines duplicates a line in any".format(
        len(cells)))
    w(f"  runners/jobs_*.txt: {DRYRUN['dup_scan']} were compared as")
    w("  normalised flag sets (flag, value, numbers canonicalised) and gave 0 hits.")
    w("  ⭐RE-CHECKED {} across all four stage-1 packages together (0969 P1, 0970 P3, 0971 P8A, 0972): every one of".format(
        RECHECK["when"]))
    w("  the {} argument lines of the four files went through runners/filter_jobs.sh again — NEW {} · DONE 0 ·".format(
        RECHECK["lines_all_four"], RECHECK["lines_all_four"]))
    w("  STALE 0 · BAD 0 — and all {} stems were captured from the builder's own --dry-run namer. That pass is what".format(
        RECHECK["lines_all_four"]))
    w("  found the two shared cells below; {} of the {} stems are distinct and 0 are on disk.".format(
        RECHECK["stems_distinct"], RECHECK["lines_all_four"]))
    w()
    w("⛔TWO RECORDS OF THIS MATRIX ARE BOUGHT BY runners/jobs_0969, NOT BY THIS FILE — so it carries {} lines".format(
        n_lines))
    w("  for {} records. They are the steep corner (D 15 m, H 12 m, h 0.8 m) at az 0, open sky and ground:".format(
        len(cells)))
    for i in reused:
        g, az, ground, line = cells[i]
        w("    · D{:g} H{:g} h{:g} az{:g} {:<11s} = 0969's anchor {} at 4e9 / depth 3 / solver seed 1".format(
            g["D"], g["H"], g["h"], az, "ground plate" if ground else "open sky",
            "A12" if ground else "A11"))
        w("      {}".format(line))
    w("  ⚠The two lines are NOT the same TEXT — 0969 writes `--range-m 18.720042735` and this file wrote")
    w("  `--range-m 18.7200427350`, one trailing zero apart — which is exactly why a flag-set scan that compares")
    w("  strings misses them. The VALUES are identical and so is the stem: `_r{:g}` keeps six significant digits,")
    w("  so both name _r18.72 ... _el-36.7475. ⛔A duplicate check for this repo has to compare the stem the")
    w("  builder's own --dry-run prints, never the spelling of the line. Two queue lines naming one")
    w("  shard means the SECOND to reach a worker is silently SKIPPED (elevation_sweep_md.py:870 「건너뜀」) and")
    w("  nothing says so afterwards. 0969 keeps them because it launches first and its anchor ladder needs that")
    w("  rung; this file reads the two shards when they land. ⛔If 0969 is cancelled or its anchor list changes,")
    w("  re-run this generator — the exclusion is derived from packages[0] of the campaign JSON, so the two lines")
    w("  come back on their own. The record count, the 27-row table and the holdout arithmetic below are unchanged:")
    w("  the split unit is the record, not the queue line.")
    w()
    w("COST. About {:.0f} worker-hours, band {:.0f}-{:.0f}. Basis, from stored shards only:".format(
        hours["pt"], hours["lo"], hours["hi"]))
    w("  · ground, depth 3, n1024, 4e9, this slab, --dump-paths: the ten runners/jobs_0965 ground shards give")
    w("    meta[5]/len(idx) = 0.6139 .. 1.8483 s/position, median 1.7148 -> 0.175-0.526 h per shard, median 0.488 h.")
    w("  · open sky, depth 3, n1024: ONE stored shard (jobs_0965 line 1) at 0.3256 s/position -> 0.093 h. The upper end")
    w("    is an extrapolation, not a measurement: the open-sky depth-2 median at r30 (0.755 s/position) times the")
    w("    depth-2 -> depth-3 factor measured in ground at the same geometry ((1.737+1.763)/(1.389+1.441) = 1.237).")
    w("  ⛔THE OPEN-SKY HALF OF THAT POINT ESTIMATE RESTS ON ONE SHARD AND IS PROBABLY LOW. 0.3256 s/position is")
    w("    the fastest depth-3 measurement in the whole store; the matched depth-2/depth-3 PAIRS at n4096 (same")
    w("    geometry, same run, both shards: ground r30 el-5 1.296 and 1.234, ground r30 el-2.5 1.163 and 1.151)")
    w("    give a depth factor of about 1.20, which on the open-sky depth-2 median of 0.746 s/position (177 stored")
    w("    rt210 shards) puts open sky at about 0.88 s/position and this file at about 80 worker-hours, not 63.")
    w("    ⚠Both numbers are contended wall clock: the same class spans 0.255-1.097 s/position across stored")
    w("    shards, a 4.3x spread for identical work, which is larger than any axis being scaled here. Read the")
    w("    band, not the point, and re-measure on the first landed shard of this file.")
    w("  · range is NOT scaled: at a fixed 4e9-ray budget the stored s/position shows no range trend (open-sky depth 2:")
    w("    r15 0.72-1.05, r30 0.74-0.76, r60 0.47-0.76, r100 0.36-0.76 s/position).")
    w("  ⚠This is a sum of worker slot-hours, not elapsed time and not divided by the cards. The band is wide because")
    w("    the wall clock is set by how many workers share a card: two identical 0965 ground shards ran 0.614 and 1.848")
    w("    s/position the same morning, a factor of 3.0.")
    w("  The brief allocates P2 130-260 worker-hours for all 456 records, i.e. 62-123 h for the 216 coarse ones; the")
    w("  estimate above is the same measurement without a design margin and sits at or below that.")
    w()
    w("DISK. About {:.1f} GB of path-list sidecars (outputs/path_provenance/), band {:.1f}-{:.1f} GB.".format(
        disk / 1e9, 0.7 * disk / 1e9, 1.5 * disk / 1e9))
    w("  ⛔The brief's «about 52 B per path per position» does not match the store. Measured over all 85 stored")
    w("    sidecars in outputs/path_provenance/ on 2026-09-18: 5.65 - 8.85 B per stored path on disk (median 7.0),")
    w("    because the sidecar is a compressed npz and its two int64 arrays (obj_raw, prim) compress hard. The brief's")
    w("    own example is self-consistent with 7.4, not 52: 8,363,270 B / 2,048 positions = 4,084 B per position, and")
    w("    that shard stores 1,127,832 paths, i.e. 550.7 per position -> 7.42 B per path. The 70 B/path figure is")
    w("    the UNCOMPRESSED width")
    w("    (complex64 a + float64 tau + 3 x int16 part + 3 x int64 obj_raw + 3 x int64 prim). The estimate here uses")
    w("    the measured on-disk bytes per POSITION and scales those, which avoids the per-path question entirely.")
    w("  Basis: depth-3 n1024 at r30 el-5 measured at 1,743 B/position open sky and 4,024 B/position ground (median of")
    w("    ten), scaled by (30/range)^2.25 and by 1 + 0.033*(|el| - 5), with a x1.06 azimuth allowance. Both fits come")
    w("    from the stored depth-2 population at these settings (range: 7,960 vs 1,608 B/position at r15/r30 el-5;")
    w("    elevation: 1,494 / 1,608 / 1,905 / 2,240 B/position at el 2.5 / 5 / 10 / 15 at r30; azimuth: az90/az0 = 1.20")
    w("    and az180/az0 = 1.03 in ground at r30). ⚠The steepest cells here (el -36.7 deg at D 15 m) are well outside")
    w("    the measured elevation range, so the band is wide on purpose.")
    w("  Cross-check of that model against a shard it was not fitted on: it predicts 27.0 kB/position for ground at")
    w("  r15, el -15; the stored depth-2 shard there is 21.34 kB/position and the measured depth-2 -> depth-3 factor")
    w("  is 1.237, i.e. 26.4 kB/position. 2 % apart.")
    w("  df on /workspace, 2026-09-18 09:15 UTC: 1,041 GB free = 969 GiB, of a 3.5 TB filesystem 72 % used. ⚠The")
    w("  earlier «974 GB» in this header was `df -h`'s GiB figure printed as GB and read half an hour earlier; the two")
    w("  units are 7 % apart and the corrected pair is the one above. The upper end of the band is")
    w("  0.24 % of what is free (0.26 % counting the shard npz files), so the package is not disk-limited.")
    w("  threshold not crossed. ⭐All four stage-1 packages together add about 7.0 GB of sidecar and 38 MB of shard")
    w("  npz — 0.67 % of the same free space — re-measured on 2026-09-18 by the cross-check, with the same")
    w("  bytes-per-position model fitted independently on 68 stored depth-2 sidecars (measured/predicted 0.90-1.22).")
    w("  threshold not crossed.")
    w()
    w("ORDER OF LINES. D, then H, then h, then scene (open sky before ground), then azimuth — the same nested loop the")
    w("  generator runs, so line k is reproducible from the matrix alone. Nothing here depends on the launch order.")
    w()
    w("CARDS. No card restriction is written here. runners/GPU_HOLD.json is the single place that takes cards out and")
    w("  the supervisors re-read it every round; this file does not touch it, the running 0963-0968 queues, the")
    w("  supervisors, the watchers or the workers.")
    w()
    w("LINES {} for {} records ({} open sky + {} ground; {} bought by runners/jobs_0969, see above) ·"
      .format(len(cells) - len(reused), len(cells), n_sky, n_ground, len(reused)))
    w("  one shard each · every line dumps 1,024 path lists.")
    return W


def main() -> int:
    (m, cells, geoms, sky_keys, tight, hours, disk, n_sky, n_ground, hold,
     fine_centres, reused) = build()
    out = header(m, cells, geoms, sky_keys, tight, hours, disk, n_sky, n_ground, hold, fine_centres, reused)
    out.append("# " + "-" * 116)
    last = None
    for i, (g, az, ground, line) in enumerate(cells):
        if i in reused:
            continue
        key = (g["D"], g["H"], g["h"], ground)
        if key != last:
            out.append("#")
            out.append("# D{:g} m · H{:g} m · h{:g} m · {} — range {:.6g} m, el {:+.6g} deg, radar {:g} m above the plate"
                       .format(g["D"], g["H"], g["h"], "ground plate" if ground else "open sky",
                               g["rng"], g["el"], g["h"]))
            last = key
        out.append(line)
    sys.stdout.write("\n".join(out) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
