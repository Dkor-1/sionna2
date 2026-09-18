#!/usr/bin/env python
"""0970 generator - P3, time sampling and interpolation fidelity (stage 1 of the 2026-09-18 GPU campaign).

Emits runners/jobs_0970_time_sampling_rate_ladder.txt deterministically. Nothing in the queue file is
hand-typed: the rate ladder comes from the campaign JSON, the geometry alts are checked against the
stored cells they must line up with, and every cost, size and spectral number in the header is
computed here from the repo code, the ledger and the stored shards/sidecars named beside it.

  run:  CUDA_VISIBLE_DEVICES="" SIONNA2_ALLOW_CPU=1 MPLBACKEND=Agg \
        /workspace/.venvs/py312/bin/python make_jobs_0970_time_sampling_rate_ladder.py [-o OUT.txt]

CPU only. It reads /workspace/sionna read-only and writes one text file. It never launches anything.

WHY A GENERATOR: anything under outputs/ or runners/ has to be rebuildable, and this file is the only
place the 0970 matrix exists. Change the matrix here, re-run, re-dry-run.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

REPO = "/workspace/sionna"
PLAN = "/workspace/sionna_gpu_campaign_plan_2026-09-18.json"
SHD = os.path.join(REPO, "outputs", "elev_sweep_shards")
PRV = os.path.join(REPO, "outputs", "path_provenance")

# ----------------------------------------------------------------------------------------------
# Fixed choices of this package. Everything else is computed.
# ----------------------------------------------------------------------------------------------
SW = "R0D0E0F1"          # diffuse on, refraction and diffraction off - the standing arm
SPP = 4_000_000_000      # the campaign's common ray budget
DEPTH = 2                # see the header block "Why depth 2 everywhere"
SHELL_MM, PROP_MM = 0.75, 1.43
ANT = "tr38901"
ENV_GROUND = "outdoor01_ground"

#: The eight geometries, in the order they are written to the queue file.
#  alt = the stored --env-alt of the matching ground cell; `stem_key` names the stored n4096
#  depth-2 cell that (a) fixes that alt and (b) IS this geometry's 19,700 Hz record (see REUSE).
GEOMETRIES = [
    # key,               range, el,  env,         alt,   short label
    ("r15_el15_sky",      15, -15, None,          None, "R15 el-15 sky"),
    ("r15_el15_gnd",      15, -15, ENV_GROUND,    5.4,  "R15 el-15 ground alt5.4"),
    ("r15_el5_sky",       15,  -5, None,          None, "R15 el-5  sky"),
    ("r15_el5_gnd",       15,  -5, ENV_GROUND,    2.81, "R15 el-5  ground alt2.81"),
    ("r30_el5_sky",       30,  -5, None,          None, "R30 el-5  sky"),
    ("r30_el5_gnd",       30,  -5, ENV_GROUND,    4.11, "R30 el-5  ground alt4.11"),
    ("r30_el15_sky",      30, -15, None,          None, "R30 el-15 sky"),
    ("r30_el15_gnd",      30, -15, ENV_GROUND,    9.26, "R30 el-15 ground alt9.26"),
]

#: The two anchors that get every rate a second time at --solver-seed 2. Named here, before any
#  shard of this file is read, so the repeat cannot be moved to wherever the answer looks best.
ANCHOR_SKY = "r15_el15_sky"    # the 0961 cell: the 19.7 -> 28.029 kHz residual that started P3
ANCHOR_GND = "r30_el5_gnd"     # the 0962/0965 cell: the ground-ghost geometry P2/P7 also use

RADAR_H_M = 1.5                # the mast height the stored ground alts were built around

#: ⚠Record of the dry run of the EMITTED file. Re-running the generator does NOT re-verify these -
#  they are results of running runners/filter_jobs.sh over the queue lines this script produced.
#  If the matrix above is changed, the file must be dry-run again and this block replaced.
DRYRUN = dict(
    when="2026-09-18 08:42:11-08:43:08 UTC (30 new lines), 08:43:14-08:43:58 UTC (20 reuse lines)",
    how='CPU, CUDA_VISIBLE_DEVICES="" SIONNA2_ALLOW_CPU=1 MPLBACKEND=Agg nice -n 19 taskset -c 8-15, '
        'runners/filter_jobs.sh at -P 4, run from /workspace/sionna, the lines below verbatim',
    new=30, done=0, stale=0, bad=0,
    reuse_new=0, reuse_done=20, reuse_stale=0, reuse_bad=0,
    stems_readback="30 stems read back from --dry-run 08:44-08:46 UTC; all 30 distinct; all 30 identical to the "
                   "names this generator predicts; none present in outputs/elev_sweep_shards/",
    flagscan="1,206 --engine lines in 55 runners/jobs_*.txt (commented and #HOLD included): 0 exact flag-set "
             "duplicates, 0 duplicates among the 30 new lines",
    nearest="the closest existing line anywhere is 3 flags away, and the three flags are exactly this file's axis "
            "(--n-poses, --prf, --dump-paths): runners/jobs_0961 line 119 (n4096 prf28029 nshards 2 - a 0.14613 s "
            "record, not a 0.1 s one), runners/jobs_0963 lines 117 and 142 (live n1024 ledger-rate lines), and the "
            "commented n1024 extension lines runners/jobs_0962:115 and runners/jobs_0967:199. None names a stem of "
            "this file",
)


def stem(rng_m, el, env, alt, n, prf, seed, nshards, shard):
    """Rebuild the shard name the way benchmark/elevation_sweep_md.py:511-545 builds it.

    Only the tokens this package can move are assembled; every other token is the default one the
    sweep writes for these flags. Used for a cross-check against the names --dry-run reads back.
    """
    s = f"sionna_p{SPP}_sw{SW}"
    s += f"_r{rng_m:g}"
    s += f"_n{n}"
    if prf is not None:
        s += f"_prf{float(prf):g}"
    if env:
        s += "_env" + env.replace(":", "-")
    if alt:
        s += f"_alt{float(alt):g}"
    if seed != 1:
        s += f"_ss{int(seed)}"
    s += f"_shell{SHELL_MM:g}mm_prop{PROP_MM:g}mm"
    s += "_mfixbatteryi5_blperairframe"
    s += f"_ant{ANT}"
    s += "_rt210"
    s += f"_d{DEPTH}"
    s += f"_el{el:+g}"
    s += f"_{shard:02d}.npz"
    return s


def job_line(rng_m, el, env, alt, n, prf, seed):
    """One queue line. Flag order copied from runners/jobs_0961 (the --prf precedent) and
    runners/jobs_0965 (the --dump-paths / shard tail). One shard per record: see the header."""
    p = ["--engine sionna", f"--n-poses {n}"]
    if prf is not None:
        p.append(f"--prf {prf:g}")
    p += [f"--range-m {rng_m:g}", f"--sw {SW}", f"--spp {SPP}",
          f"--max-depth {DEPTH}", f"--els={el:g}"]
    if env:
        p += [f"--env {env}", f"--env-alt {alt:g}"]
    p += [f"--ant-pattern {ANT}", f"--shell-mm {SHELL_MM:g}", f"--prop-mm {PROP_MM:g}"]
    if seed != 1:
        p.append(f"--solver-seed {int(seed)}")
    p += [f"--dump-paths {n}", "--shard 0", "--nshards 1"]
    return " ".join(p)


def reuse_line(rng_m, el, env, alt, seed, shard):
    """The stored n4096 cell that carries this geometry's 19,700 Hz record. Emitted only as a
    comment, for the DONE dry-run, never as a queue line."""
    p = ["--engine sionna", "--n-poses 4096", f"--range-m {rng_m:g}", f"--sw {SW}",
         f"--spp {SPP}", f"--max-depth {DEPTH}", f"--els={el:g}"]
    if env:
        p += [f"--env {env}", f"--env-alt {alt:g}"]
    p += [f"--ant-pattern {ANT}", f"--shell-mm {SHELL_MM:g}", f"--prop-mm {PROP_MM:g}"]
    if seed != 1:
        p.append(f"--solver-seed {int(seed)}")
    p += ["--dump-paths 2048", f"--shard {shard}", "--nshards 2"]
    return " ".join(p)


# ----------------------------------------------------------------------------------------------
# Measurements. Every number the header states comes from one of these.
# ----------------------------------------------------------------------------------------------
def measure_cell(rng_m, el, env, alt, seed):
    """meta[5]/len(idx) and the sidecar bytes of the stored n4096 depth-2 cell, both shards."""
    rows = []
    for sh in (0, 1):
        nm = stem(rng_m, el, env, alt, 4096, None, seed, 2, sh)
        f = os.path.join(SHD, nm)
        if not os.path.exists(f):
            raise SystemExit(f"STOP: stored cell missing, the matrix rests on it: {f}")
        z = np.load(f, allow_pickle=True)
        idx, meta = z["idx"], z["meta"]
        pf = os.path.join(PRV, nm.replace(".npz", "_prov.npz"))
        if not os.path.exists(pf):
            raise SystemExit(f"STOP: sidecar missing for the 19,700 Hz reuse: {pf}")
        y = np.load(pf, allow_pickle=True)
        rows.append(dict(
            name=nm, npos=int(idx.size), sec=float(meta[5]), prf=float(meta[4]), n=int(meta[3]),
            s_per_pose=float(meta[5]) / idx.size,
            n_dup=("n_dup" in z.files), build=str(z["solver_build"]),
            npz_B=os.path.getsize(f), prov_B=os.path.getsize(pf),
            prov_B_per_pose=os.path.getsize(pf) / idx.size,
            nret_med=float(np.median(y["n_paths"])), dumped=int(y["n_paths"].size),
            n_trunc=int(z["n_trunc"][0]), cap=int(z["n_trunc"][1]),
            idx0=int(idx[0]), idx1=int(idx[1]), idxmax=int(idx[-1]),
        ))
    return rows


def measure_ac_static(rng_m, el, env, alt, seed, n_keep):
    """ac_to_static_db over the first n_keep poses of the stored n4096 cell - the exact window the
    19,700 Hz leg reuses. Both shards are concatenated and sorted by idx first (the split is
    interleaved). static = |mean E|^2, ac = mean |E - mean E|^2, both over that window."""
    E, I = [], []
    for sh in (0, 1):
        f = os.path.join(SHD, stem(rng_m, el, env, alt, 4096, None, seed, 2, sh))
        z = np.load(f, allow_pickle=True)
        E.append(z["E"])
        I.append(z["idx"])
    E = np.concatenate(E)
    I = np.concatenate(I)
    o = np.argsort(I)
    E, I = E[o], I[o]
    keep = I < n_keep
    if int(keep.sum()) != n_keep:
        raise SystemExit(f"STOP: the reuse window is not complete: {int(keep.sum())} of {n_keep} poses")
    e = E[keep]
    m = e.mean()
    ac = float(np.mean(np.abs(e - m) ** 2))
    static = float(np.abs(m) ** 2)
    return dict(lvl_db=10 * np.log10(float(np.mean(np.abs(e) ** 2))),
                ac_to_static_db=10 * np.log10(ac / static),
                n=int(keep.sum()))


def rotor_scales():
    """Rotor spectral scales, from the ledger and src/drones.py, not from a note."""
    sys.path.insert(0, os.path.join(REPO, "src"))
    from drones import DRONES                                    # noqa: E402
    spec = DRONES["matrice4e"]
    tj = json.load(open(os.path.join(REPO, "outputs", "report07_three_engines.json")))["_meta"]
    rpms = np.asarray(tj["rpm_per_rotor"], float)
    B = int(spec.prop_blades)
    lam = 2.998e8 / float(tj["fc_hz"])                            # the constant f_tip_at() uses
    R = spec.prop_dia_mm / 2000.0
    f_rev = float(spec.hover_rpm) / 60.0
    return dict(
        rpms=rpms, blades=B, n_rotors=int(spec.num_rotors), prop_dia_mm=spec.prop_dia_mm,
        f_rev=f_rev, f_flash=rpms.mean() / 60.0 * B, f_flash_per_rotor=rpms / 60.0 * B,
        f_flash_ledger=float(tj["f_flash_hz"]), prf_default=float(tj["prf_hz"]),
        f_tip=lambda el: 2.0 * (2 * np.pi * f_rev * R) / lam * np.cos(np.radians(el)),
        lam=lam,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "jobs_0970_time_sampling_rate_ladder.txt"))
    a = ap.parse_args()

    # -- the matrix, read from the campaign JSON, not typed here ---------------------------------
    plan = json.load(open(PLAN))
    p3 = [p for p in plan["packages"] if p["id"] == "P3"]
    if len(p3) != 1:
        raise SystemExit("STOP: the campaign JSON does not hold exactly one P3 package")
    p3 = p3[0]
    rates = [int(r) for r in p3["rates_hz"]]
    npose = [int(n) for n in p3["n_poses_per_rate"]]
    win = float(p3["duration_s"])
    if len(rates) != len(npose):
        raise SystemExit("STOP: rates_hz and n_poses_per_rate disagree in length")
    #: the pose count each rate needs for the SAME window, computed, then checked against the JSON
    computed = [int(round(r * win)) for r in rates]
    if computed != npose:
        raise SystemExit(f"STOP: computed pose counts {computed} != JSON {npose}")
    if len(GEOMETRIES) != int(p3["geometry_count"]):
        raise SystemExit("STOP: geometry count disagrees with the campaign JSON")
    designed = len(GEOMETRIES) * len(rates) + int(p3["additional_repeat_geometry_count"]) * len(rates)
    if designed != int(p3["count"]):
        raise SystemExit(f"STOP: designed record count {designed} != JSON {p3['count']}")

    rot = rotor_scales()
    base_prf = rot["prf_default"]
    if int(base_prf) != rates[0]:
        raise SystemExit(f"STOP: the ledger prf {base_prf} is not the ladder's lowest rate {rates[0]}")

    # -- geometry check: the stored alts against the mast geometry they claim --------------------
    geo_rows = []
    for key, rng_m, el, env, alt, label in GEOMETRIES:
        implied = None if alt is None else alt - rng_m * np.sin(np.radians(abs(el)))
        geo_rows.append((key, rng_m, el, env, alt, label, implied))

    # -- measurements on the ten stored cells ----------------------------------------------------
    cells, acst = {}, {}
    for key, rng_m, el, env, alt, label in GEOMETRIES:
        cells[(key, 1)] = measure_cell(rng_m, el, env, alt, 1)
        acst[(key, 1)] = measure_ac_static(rng_m, el, env, alt, 1, npose[0])
    for key in (ANCHOR_SKY, ANCHOR_GND):
        _, rng_m, el, env, alt, _ = next(g for g in GEOMETRIES if g[0] == key)
        cells[(key, 2)] = measure_cell(rng_m, el, env, alt, 2)
        acst[(key, 2)] = measure_ac_static(rng_m, el, env, alt, 2, npose[0])

    # -- build the lines -------------------------------------------------------------------------
    new_rates = [(r, n) for r, n in zip(rates, npose) if r != int(base_prf)]
    lines, meta_rows = [], []
    order = [(k, 1) for k, *_ in GEOMETRIES] + [(ANCHOR_SKY, 2), (ANCHOR_GND, 2)]
    for key, seed in order:
        _, rng_m, el, env, alt, label = next(g for g in GEOMETRIES if g[0] == key)
        m = cells[(key, seed)]
        spp_lo = min(r["s_per_pose"] for r in m)
        spp_hi = max(r["s_per_pose"] for r in m)
        spp_mid = sum(r["s_per_pose"] for r in m) / len(m)
        bpp = sum(r["prov_B_per_pose"] for r in m) / len(m)
        for r, n in new_rates:
            lines.append(job_line(rng_m, el, env, alt, n, r, seed))
            meta_rows.append(dict(
                key=key, seed=seed, label=label, rate=r, n=n,
                stem=stem(rng_m, el, env, alt, n, r, seed, 1, 0),
                h_mid=n * spp_mid / 3600.0, h_lo=n * spp_lo / 3600.0, h_hi=n * spp_hi / 3600.0,
                prov_B=n * bpp, nret_med=m[0]["nret_med"],
                ram_GB=n * m[0]["nret_med"] * (16 + 18 * DEPTH) * 2 / 1e9,
            ))

    tot_h_mid = sum(r["h_mid"] for r in meta_rows)
    tot_h_lo = sum(r["h_lo"] for r in meta_rows)
    tot_h_hi = sum(r["h_hi"] for r in meta_rows)
    tot_prov = sum(r["prov_B"] for r in meta_rows)
    tot_poses = sum(r["n"] for r in meta_rows)
    npz_per_pose = sum(c["npz_B"] / c["npos"] for m in cells.values() for c in m) / (2 * len(cells))
    tot_npz = tot_poses * npz_per_pose
    if len({r["stem"] for r in meta_rows}) != len(meta_rows):
        raise SystemExit("STOP: two lines want the same stem")

    # ⛔Free disk is the only LIVE HOST input of this generator, and a header built on live state does not
    #   reproduce: the 2026-09-18 cross-check of the four stage-1 packages re-ran this file and got 969 GiB
    #   where the installed copy says 970 GiB, because queues 0963-0968 had written in between. So it is
    #   FROZEN at the value measured when the package was built and the live value is reported, never written.
    FREE_B_FROZEN = 1_041_336_623_104          # df /workspace, 2026-09-18 ~08:47 UTC
    st = os.statvfs("/workspace")
    free_live = st.f_bavail * st.f_frsize
    free_B = FREE_B_FROZEN
    if free_live != free_B:
        sys.stderr.write(f"note: /workspace free is {free_live/2**30:,.0f} GiB now "
                         f"({free_B/2**30:,.0f} GiB frozen); the file is unchanged by design.\n")

    # -- header ----------------------------------------------------------------------------------
    H = []
    a_ = H.append
    a_("# 0970 - P3, the time sampling rate ladder: is the time axis of an RT hover record set by the rotor, or by the rate we sampled")
    a_("#        it at? Eight geometries (R15/R30 m x el -5/-15 deg x open sky / outdoor ground) each recorded over the SAME 0.1 s window")
    a_(f"#        at {', '.join(f'{r:,} Hz' for r in rates)} - {len(rates)} rates x {len(GEOMETRIES)} geometries = {len(GEOMETRIES)*len(rates)} records, plus every rate a second time at")
    a_(f"#        --solver-seed 2 on two anchors named in advance (one sky, one ground) = {designed} records. Full path lists at every position.")
    a_("#        (2026-09-18, package P3 of /workspace/sionna_queue_recommendations_2026-09-18.md sec.6 and the campaign JSON packages[2])")
    a_("#        Rebuild: runners/make_jobs_0970_time_sampling_rate_ladder.py. Every number below is computed by that script from the")
    a_("#        campaign JSON, benchmark/elevation_sweep_md.py, src/drones.py, outputs/report07_three_engines.json and the stored")
    a_("#        shards named in each row. No number here was typed by hand.")
    a_("#")
    a_(f"#  {len(lines)} queue lines, {designed} records: {designed - len(lines)} of the {designed} are already on disk and are REUSED, not re-bought (see REUSE).")
    a_(f"#  About {tot_h_mid:.0f} worker-hours (band {tot_h_lo:.0f}-{tot_h_hi:.0f}), about {tot_prov/1e9:.2f} GB of path-list sidecars. Basis in COST.")
    a_("#")
    a_("# Launch preconditions (main session).")
    a_("#   (1) Path-list integrity (check 0 of the runners/jobs_0957 header) has passed on a GPU sidecar. Every line here carries path")
    a_("#       lists; without them T3 and the class table cannot be written and only the field-level readings survive.")
    a_(f"#   (2) ⭐Line 1 is deliberately first and is the PROBE: it is the cheapest line of the file ({meta_rows[0]['h_lo']*60:.0f}-{meta_rows[0]['h_hi']*60:.0f} min by the measured")
    a_(f"#       rate of its geometry) and the first cell anywhere with the shape --prf given + --nshards 1 + --dump-paths equal to")
    a_(f"#       --n-poses. No stored sidecar has it: the only stored --prf cell is runners/jobs_0961's n4096 prf28029 pair, which is")
    a_("#       --nshards 2 and dumps 2,048 of its 2,048 positions per shard. Run line 1, check 0 on its sidecar, and check its")
    a_("#       sidecar size against the DISK table below BEFORE the 29 others are committed. ⚠With several free workers the supervisor")
    a_("#       may launch lines 2-30 first; if the guard is to bite, the main session holds them until line 1 lands.")
    a_(f"#   (3) The n{npose[-1]:,} lines are the largest single records this repo has bought ({max(r['h_mid'] for r in meta_rows):.1f} h at the slowest geometry, about")
    a_(f"#       {max(r['ram_GB'] for r in meta_rows):.1f} GB of host RAM for the dump). Confirm free host RAM and the per-worker count before those lines run.")
    a_("#   (4) The ten stored cells of the REUSE table are on disk with their sidecars and n_dup. If any has been moved or deleted,")
    a_(f"#       its {rates[0]:,} Hz record no longer exists and that geometry's ladder is incomplete - it is re-bought as an n{npose[0]:,} line with")
    a_("#       NO --prf flag (see the naming rule in REUSE), not silently dropped.")
    a_("#")
    a_("# ============================================================================================================================")
    a_("# WHAT THE RATE LADDER IS, AND WHAT IT IS NOT")
    a_("# ============================================================================================================================")
    a_("# The question. runners/jobs_0961 compared a 19,700 Hz record with a 28,029 Hz one at R15 m el -15 sky and read a linear-")
    a_("#   interpolation residual of -13.11 dB, with 1.623 % of the high-rate record's AC power sitting above the 19,700 Hz Nyquist")
    a_("#   (readout_0918.json gates.0961.T1_T2: interp_resid_db_linear -13.112, above_nyq_share 0.016227). That is one cell, one pair")
    a_("#   of rates, and the residual cannot be split into interpolation error, solver spread and real rotor physics from two records.")
    a_("#   ⛔And its two records do NOT span the same window: that gate has n_used 4,096 at both rates, so the 19,700 Hz record is")
    a_(f"#   {4096/19700:.4f} s long and the 28,029 Hz one {4096/28029:.4f} s - a {100*(4096/19700)/(4096/28029)-100:.0f} % difference in window, hence in FFT bin, on top of the rate")
    a_("#   difference. ⭐This file holds the WINDOW fixed at 0.1 s and moves --n-poses with --prf instead, which is the whole design")
    a_(f"#   point of the ladder. The same gate already gives the solver floor at that cell: seed_floor_db {-1.2130595189953692:.2f} dB from its")
    a_(f"#   seed-1/seed-2 pair and rerun_floor_db {-59.0618492172659:.2f} dB from a same-seed rerun - the same residual measure computed")
    a_("#   between two seeds and between two runs of one seed. ⚠At that cell the two SEEDS differ by nearly as much as the signal")
    a_(f"#   itself ({-1.2130595189953692:.2f} dB), so any rate residual above that value there is inside the seed spread and says nothing about rate.")
    a_("#   That is why the two anchors below repeat every rate at --solver-seed 2 before any rate difference is read.")
    a_("#   Every later statement about observation gaps, micro-Doppler and coherent integration rests on the time axis, so the time")
    a_("#   axis is measured first, on more than one cell.")
    a_("#")
    a_("# HOW --prf AND --n-poses INTERACT, read from the code, not assumed.")
    a_("#   benchmark/elevation_sweep_md.py:370-371 takes prf from --prf when it is > 0 and otherwise from the ledger")
    a_(f"#   (outputs/report07_three_engines.json _meta.prf_hz = {base_prf:,.0f} Hz); :373 takes n from --n-poses; :405/:411 build the pose")
    a_("#   times as ph = rotor_phases(np.arange(n) / prf, ...). So the time grid is t_k = k / prf for k = 0 ... n-1: the SPACING is")
    a_("#   1/prf and the LENGTH is n/prf. :368 says it in the file itself - \"--n-poses is record LENGTH, not sample density; the pose")
    a_("#   spacing dt = 1/prf does not depend on n\". Raising --n-poses alone makes a LONGER record at the same rate, not a denser one.")
    a_("#   ⛔That is why every rate below carries its own --n-poses: the window is held at 0.1 s by n = round(rate x 0.1 s).")
    a_("#")
    a_("#   The four grids, computed here (dt = 1/prf, span = n/prf, last sample = (n-1)/prf, FFT bin = prf/n):")
    a_("#   | rate [Hz] | --n-poses | dt [us]   | n/prf [s]   | last sample [s] | FFT bin [Hz] | Nyquist [Hz] |")
    for r, n in zip(rates, npose):
        a_(f"#   | {r:9,} | {n:9,} | {1e6/r:9.4f} | {n/r:11.7f} | {(n-1)/r:15.7f} | {r/n:12.5f} | {r/2:12,.0f} |")
    common = min((n - 1) / r for r, n in zip(rates, npose))
    span_hi = max(n / r for r, n in zip(rates, npose))
    span_lo = min(n / r for r, n in zip(rates, npose))
    a_(f"#   Three of the four rates divide {win:g} s exactly ({', '.join(f'{r:,}' for r,n in zip(rates,npose) if abs(n/r-win)<1e-12)} Hz).")
    off = [(r, n) for r, n in zip(rates, npose) if abs(n / r - win) >= 1e-12]
    for r, n in off:
        a_(f"#   {r:,} Hz does not: {win:g} s x {r:,} = {win*r:,.1f} poses, so n = {n:,} spans {n/r:.7f} s, which is {(n/r-win)*1e6:+.2f} us")
        a_(f"#   ({(n/r-win)*r:+.2f} of its own sample) longer than the other three. The four records are therefore compared on the COMMON")
        a_(f"#   window [0, {common:.7f}] s - the last {rates[0]:,} Hz sample - and the {span_hi-span_lo:.2e} s of tail beyond it is not read.")
    a_(f"#   ⭐The property that makes the ladder readable: n/prf is the same {win:g} s at every rate, so the FFT bin is the SAME")
    a_(f"#   {rates[0]/npose[0]:.5f} Hz at all four (column above). A spectrum or a comb-contrast difference between two rates therefore")
    a_("#   cannot be a resolution difference. ⛔This is the opposite of the n-at-fixed-prf case that the runners/jobs_0965 header warns")
    a_("#   about (n1024 -> 19.238 Hz bin vs n8192 -> 2.405 Hz), and it holds ONLY because --n-poses moves with --prf here.")
    a_("#   ⚠What still differs across rates is the BAND, not the resolution: the comb harmonics that fit under Nyquist go from")
    a_(f"#   {rates[0]/2:,.0f} Hz to {rates[-1]/2:,.0f} Hz. Any contrast compared across rates is computed on the common band |f| < {rates[0]/2:,.0f} Hz")
    a_("#   with the same harmonic set; a contrast that counts more harmonics at the high rate is not a rate comparison.")
    a_("#")
    a_("# WHAT MOVES IN 0.1 s, computed from src/drones.py DRONES['matrice4e'] and the ledger _meta.")
    fl = rot["f_flash"]
    a_(f"#   {rot['n_rotors']} rotors, {rot['blades']} blades, prop diameter {rot['prop_dia_mm']} mm, hover {rot['f_rev']*60:,.0f} rpm = {rot['f_rev']:.4f} rev/s.")
    a_(f"#   Blade-flash rate (blades x rev/s) = {fl:.4f} Hz, which reproduces the ledger _meta.f_flash_hz = {rot['f_flash_ledger']:.4f} Hz.")
    a_(f"#   Per-rotor flash rates from the ledger rpm spread: {', '.join(f'{x:.3f}' for x in rot['f_flash_per_rotor'])} Hz, total spread")
    a_(f"#   {rot['f_flash_per_rotor'].max()-rot['f_flash_per_rotor'].min():.3f} Hz.")
    a_(f"#   ⛔So 0.1 s CANNOT separate the four rotors: the FFT bin is {rates[0]/npose[0]:.3f} Hz and the four flash lines lie inside")
    a_(f"#   {rot['f_flash_per_rotor'].max()-rot['f_flash_per_rotor'].min():.3f} Hz of each other; telling them apart needs about {1.0/(rot['f_flash_per_rotor'].max()-rot['f_flash_per_rotor'].min()):.1f} s. Every reading from this file is of the")
    a_("#   AGGREGATE comb, and no sentence from it may name a single rotor. The per-rotor question belongs to a longer record.")
    a_(f"#   The window holds {win*fl:.3f} blade-flash periods and {win*rot['f_rev']:.3f} rotor revolutions - neither is a whole number, so the")
    a_(f"#   comb lines fall between bins and leak. The leakage is identical at all four rates (same bin), so it does not confound the")
    a_("#   ladder; it does mean no absolute comb level from this file is quoted without its window.")
    a_(f"#   Blade-tip Doppler, f_tip_at() at elevation_sweep_md.py:1832-1859 with c = 2.998e8: {rot['f_tip'](-5.0):,.1f} Hz at el -5 deg and")
    a_(f"#   {rot['f_tip'](-15.0):,.1f} Hz at el -15 deg (the ledger prints {json.load(open(os.path.join(REPO,'outputs','report07_three_engines.json')))['_meta']['f_tip_hz']:.1f} Hz for el -15 because it used c = 3e8).")
    a_(f"#   ⚠f_tip is NOT the bandwidth of the record. It sits at harmonic {rot['f_tip'](-15.0)/fl:.1f} of the flash rate, far under even the")
    a_(f"#   lowest Nyquist ({rates[0]/2:,.0f} Hz holds {int((rates[0]/2)//fl)} flash harmonics). The blade flash is near-impulsive in time, so the comb runs")
    a_("#   well past f_tip, and that - not the tip Doppler - is what can alias. That is exactly what 0961's 1.623 % above Nyquist says.")
    a_("#")
    a_("# ⛔THE HIGH RATE IS NOT \"THE TRUTH\".")
    a_(f"#   {rates[-1]:,} Hz is the densest grid bought here and nothing more. It is one solver run with its own re-solve and seed spread,")
    a_("#   it is not a converged reference, and no reading from this file may call it ground truth, the true waveform, or the exact")
    a_("#   field. What the ladder can say is how a quantity MOVES as the grid is made denser, and whether that movement is larger or")
    a_("#   smaller than the solver spread measured beside it. If a quantity is still moving between the two highest rates by more than")
    a_("#   that spread, the honest statement is that this ladder did not reach a rate at which it stops moving - not that the top rate")
    a_("#   is right. Rate is also not the only axis: runners/jobs_0961 shows the same cell moves 2.25 dB in comb contrast between")
    a_("#   1e9 and 4e9 rays (gates.0961.R2), which is why the ray budget is P1's axis and is held fixed at 4e9 on every line here.")
    a_("#")
    a_("# ⛔A SMALL TOTAL-FIELD ERROR CAN HIDE A LARGE ROTOR-COMPONENT ERROR.")
    a_("#   The hover field is dominated by the static part - the airframe body, and at the ground cells the ground-reflected classes.")
    a_("#   The rotor lives in the AC part. HOW FAR below, measured by the generator on exactly the window this file reuses (the first")
    a_(f"#   {npose[0]:,} poses of the ten stored cells, both shards merged and sorted by idx; static = |mean E|^2, ac = mean|E - mean E|^2):")
    a_("#   | geometry                 | seed | lvl_db      | ac_to_static_db |")
    for key, seed in order:
        lbl = next(g[5] for g in GEOMETRIES if g[0] == key)
        a_(f"#   | {lbl:24} | {seed:4} | {acst[(key, seed)]['lvl_db']:11.2f} | {acst[(key, seed)]['ac_to_static_db']:15.2f} |")
    a_(f"#   So the AC part sits {-max(v['ac_to_static_db'] for v in acst.values()):.1f} to {-min(v['ac_to_static_db'] for v in acst.values()):.1f} dB below the static part across these eight geometries. A residual quoted")
    a_(f"#   against the TOTAL field is therefore quoted against a denominator up to {-min(v['ac_to_static_db'] for v in acst.values()):.0f} dB larger than the part that carries the rotor:")
    a_(f"#   a rate error that destroys the comb entirely would still read as about {min(v['ac_to_static_db'] for v in acst.values()):.0f} dB on resid_tot_db. ⛔No verdict in this file")
    a_("#   is written on a total-field residual. Every residual is written twice - once relative to the total field and once relative")
    a_("#   to the AC part after the per-record time mean is removed - and the AC one is the one that gates. This is the same trap the")
    a_("#   repo records as \"the static part leaks into the STFT band\": a plausible peak built out of a quantity that never carried the")
    a_("#   rotor at all. ⚠ac_to_static_db above is a property of the CELL, not a result of this file; it is written here only to size")
    a_("#   the denominator problem, and the ladder's own readings are the resid_* quantities below.")
    a_("#")
    a_("# ⭐WHAT THIS FIXES FOR LATER: THE MASTER TIME GRID OF THE MOVING-TRAJECTORY PACKAGE (P4).")
    a_("#   P4 computes 2 s episodes in which the body moves as well as the rotors, and it has to pick ONE rate for every episode,")
    a_(f"#   every scene and every shard before any of it is computed - the campaign budgets P4 at {plan['packages'][3].get('reference_rate_hz', 28029):,} Hz and says so. That")
    a_("#   choice is currently an assumption. This file is what turns it into a measurement: the rate at which the hover comb and the")
    a_("#   path-wise coefficients stop moving, at the geometry with the fastest time variation of the eight, is the floor for P4's")
    a_("#   master grid. ⚠It is a FLOOR and not the answer: P4 adds body motion, so its own Doppler bandwidth has to be added to")
    a_("#   whatever this file returns, and a moving scene has to be re-profiled for cost. If this file says 28,029 Hz is not enough for")
    a_("#   hover alone, P4's pose count and budget are recomputed before P4 is bought, not after.")
    a_("#")
    a_("# ============================================================================================================================")
    a_("# THE MATRIX")
    a_("# ============================================================================================================================")
    a_("# Geometry. benchmark/report15_probe.py place() puts the radar at center + range*(cos el*cos az, cos el*sin az, sin el) from the")
    a_("#   drone, and elevation_sweep_md.py:1071 calls it with baseline=0.0, so ⛔TX and RX are CO-LOCATED and report15_probe's module")
    a_("#   default BASELINE_M = 0.20 m is NOT used by this sweep. --env-alt is the drone's height above the ground plate")
    a_("#   (elevation_sweep_md.py:193, env_parts() lowers every environment part by it and leaves the drone at the origin), so the")
    a_(f"#   radar's height above the plate is --env-alt - range*sin|el|. The four stored ground alts imply a mast at:")
    a_("#   | geometry                 | --env-alt | range*sin|el| | implied radar height [m] | stored? |")
    for key, rng_m, el, env, alt, label, implied in geo_rows:
        if alt is None:
            a_(f"#   | {label:24} | {'-':>9} | {'-':>13} | {'open sky, no plate':>24} | {'n/a':>7} |")
        else:
            a_(f"#   | {label:24} | {alt:9.2f} | {rng_m*np.sin(np.radians(abs(el))):13.4f} | {implied:24.4f} | {'yes':>7} |")
    a_(f"#   ⚠Three of the four sit within 1 cm of a {RADAR_H_M:g} m mast; alt5.4 implies {5.4 - 15*np.sin(np.radians(15)):.4f} m, i.e. {100*(5.4 - 15*np.sin(np.radians(15)) - RADAR_H_M):+.2f} cm off {RADAR_H_M:g} m,")
    a_("#   because that alt was rounded to one decimal when it was first bought and every later cell inherited it. ⛔These four values")
    a_("#   are used AS STORED and are not re-rounded: changing alt5.4 to 5.38 would fork the name, throw away the 19,700 Hz records")
    a_("#   this file reuses, and orphan the runners/jobs_0960-0964 family that shares them. The 1.77 cm is carried as a known offset")
    a_("#   and no mast-height statement is made from this file - that is P2's question, which moves h alone.")
    a_("#   Verified against disk: every one of the eight alts/ranges/elevations above names an existing stored cell (REUSE table).")
    a_("#")
    a_("# Why depth 2 everywhere, sky AND ground.")
    a_("#   (1) It is the depth of the P3 representative CLI check that the campaign JSON records as dry-run passed.")
    a_("#   (2) It is the depth of all eight stored comparator cells, which is what makes the whole 19,700 Hz leg reusable (REUSE).")
    a_("#   (3) Depth is P1's axis, not P3's. Moving depth and rate at once would make a rate difference unreadable.")
    a_("#   ⛔What that costs, stated rather than hidden: at depth 2 the ground cells carry [d], [g,d], [d,g] and [g] but NOT [g,d,g]")
    a_("#   (the double ground bounce needs max_depth 3 - runners/jobs_0965 header). So this file measures the time sampling of the")
    a_("#   single-bounce ground classes only, and no sentence from it may be applied to [g,d,g]. If P1 or P2 shows the double bounce")
    a_("#   carries rotor modulation of its own, its rate sensitivity is a separate, later question.")
    a_("#")
    a_("# One shard per record (--nshards 1), on purpose. elevation_sweep_md.py:430 splits a cell as idx = np.arange(shard, n, nshards),")
    a_("#   i.e. INTERLEAVED: with --nshards 2 shard 0 holds the even poses and shard 1 the odd ones, so each shard on its own is a")
    a_("#   record at HALF the rate. ⛔In a package whose whole subject is the time grid, that is the one failure mode that would look")
    a_("#   exactly like the effect being measured - a lost or late shard would read as a rate-halved record. With --nshards 1, idx runs")
    a_(f"#   0 ... n-1 contiguously, t_k = k/prf directly, and no merge step sits between the solver and the time axis. The price is the")
    a_(f"#   longest single line: about {max(r['h_mid'] for r in meta_rows):.1f} h ({max(meta_rows, key=lambda r: r['h_mid'])['label']} at {max(meta_rows, key=lambda r: r['h_mid'])['rate']:,} Hz), against the 0.4-0.9 h of the stored n4096")
    a_("#   shards. ⚠That is longer than anything this project has run in one line; if a worker is lost the line is re-run whole.")
    a_(f"#   --dump-paths is set equal to --n-poses on every line: :894-897 selects min(N, idx.size) evenly spaced positions, so N = n")
    a_("#   with one shard dumps EVERY position. Path-wise delay and complex coefficient at common times is the point of the package,")
    a_("#   so a subsampled dump would defeat it.")
    a_("#")
    a_("# ============================================================================================================================")
    a_(f"# REUSE - the {designed - len(lines)} records of the {designed} that are NOT bought, because they are already on disk")
    a_("# ============================================================================================================================")
    a_(f"# The lowest rate of the ladder IS the ledger default. outputs/report07_three_engines.json _meta.prf_hz = {base_prf:,.0f} Hz, so a")
    a_(f"#   {rates[0]:,} Hz record over 0.1 s is the first {npose[0]:,} poses of ANY stored cell of the same geometry at the default rate. The")
    a_("#   pose grid does not depend on the record length (elevation_sweep_md.py:368 and :405/:411: with no --rotor-preset the constant-")
    a_("#   rpm branch is ph = rotor_phases(np.arange(n)/prf, rpms, fp.dirs)), so pose k is the SAME airframe pose in an n4096 record and")
    a_(f"#   in an n{npose[0]} one. ⛔Buying an n{npose[0]} cell would therefore re-buy field that is on disk, under a second name.")
    a_("#   The ten stored cells below are that leg - eight at seed 1 and both anchors at seed 2. All are n4096, --nshards 2 and")
    a_("#   INTERLEAVED, so the reader concatenates shard 00 (idx 0,2,4,...) and shard 01 (idx 1,3,5,...), sorts by idx and keeps")
    a_(f"#   idx 0 ... {npose[0]-1}. Every one has its full path-list sidecar, so the path-wise comparison is available at the low rate too.")
    a_("#   | # | record reused                            | stored stem (both shards, _00 and _01)")
    for i, ((key, seed), rows) in enumerate(cells.items(), 1):
        lbl = next(g[5] for g in GEOMETRIES if g[0] == key)
        a_(f"#   |{i:2} | {rates[0]:,} Hz {lbl:24} seed {seed} | {rows[0]['name'][:-7]}_{{00,01}}.npz")
    a_("#   Read back from those files by the generator (npz meta and the sidecars), and NOT copied from a note:")
    a_("#   | # | poses/shard | meta[4] prf | meta[3] n | n_dup | n_trunc | sidecar bytes 00 / 01     | nret median | solver_build")
    for i, ((key, seed), rows) in enumerate(cells.items(), 1):
        r0, r1 = rows
        a_(f"#   |{i:2} | {r0['npos']:11,} | {r0['prf']:11,.0f} | {r0['n']:9,} | {str(r0['n_dup'] and r1['n_dup']):5} | {r0['n_trunc']:7} | {r0['prov_B']:11,} / {r1['prov_B']:11,} | {r0['nret_med']:11,.0f} | {r0['build']}")
    a_(f"#   n_trunc[0] = 0 on every one, against the {cells[(GEOMETRIES[0][0],1)][0]['cap']:,} path cap - so no stored level is cap-limited and the reuse")
    a_("#   is sound. n_dup is present on all ten, which is what filter_jobs.sh calls DONE.")
    a_("#   ⚠What the reuse does NOT buy: the 19,700 Hz leg comes from a DIFFERENT solver run than the three new rates. That is not a")
    a_(f"#   penalty of reusing - all four rates are four separate solver runs in any case, and a freshly bought n{npose[0]} cell would carry")
    a_("#   the same re-solve difference. runners/jobs_0957 measures that re-solve spread at 2.1-2.3 % in path count. It is why the")
    a_("#   seed-2 anchors exist: they put a number on the spread before any rate-to-rate difference is read.")
    a_(f"#   ⛔And a naming rule for anyone extending this file: a {rates[0]:,} Hz line must NEVER be written as --prf {rates[0]}. The tag is")
    a_("#   added only when --prf is given (elevation_sweep_md.py:515), so `--prf 19700` and no --prf are the SAME data under two")
    a_(f"#   different names (..._n{npose[0]}_... vs ..._n{npose[0]}_prf{rates[0]}_...). The ledger value is inherited, never restated.")
    a_("#")
    a_("# The two anchors, named before any shard is read (not chosen after looking):")
    a_(f"#   sky    = {next(g[5] for g in GEOMETRIES if g[0]==ANCHOR_SKY)} - the cell runners/jobs_0961 measured the -13.11 dB interpolation residual on, i.e. the")
    a_("#            observation this package exists to explain. It is also the cheapest of the eight, so the seed repeat is cheap there.")
    a_(f"#   ground = {next(g[5] for g in GEOMETRIES if g[0]==ANCHOR_GND)} - the geometry runners/jobs_0962 and runners/jobs_0965 already characterise, and the one")
    a_("#            P2 and P7 both build on, so its solver spread is the most widely reused number this file can produce.")
    a_("#")
    a_("# ============================================================================================================================")
    a_("# COST, DISK AND NAMES")
    a_("# ============================================================================================================================")
    a_("# COST. Rate: meta[5]/len(idx) of the stored n4096 depth-2 shards of the SAME geometry, both shards, read by the generator.")
    a_("#   ⚠Those seconds are contended wall-clock on a shared host, not a pure cost: the two shards of one cell differ by up to")
    lo_r = min(cells.values(), key=lambda m: min(x["s_per_pose"] for x in m))
    worst_ratio = max(max(x["s_per_pose"] for x in m) / min(x["s_per_pose"] for x in m) for m in cells.values())
    a_(f"#   {worst_ratio:.2f}x for identical work. So the table gives lo / mid / hi from the two shards and the total is a band, not a figure.")
    a_(f"#   | geometry                 | seed | s/pose lo | s/pose hi | new poses | worker-h lo | worker-h mid | worker-h hi | sidecar")
    for key, seed in order:
        lbl = next(g[5] for g in GEOMETRIES if g[0] == key)
        rows = [r for r in meta_rows if r["key"] == key and r["seed"] == seed]
        m = cells[(key, seed)]
        a_(f"#   | {lbl:24} | {seed:4} | {min(x['s_per_pose'] for x in m):9.4f} | {max(x['s_per_pose'] for x in m):9.4f} | {sum(r['n'] for r in rows):9,} | {sum(r['h_lo'] for r in rows):11.2f} | {sum(r['h_mid'] for r in rows):12.2f} | {sum(r['h_hi'] for r in rows):11.2f} | {sum(r['prov_B'] for r in rows)/1e6:7.0f} MB")
    a_(f"#   | TOTAL                    |      |           |           | {tot_poses:9,} | {tot_h_lo:11.1f} | {tot_h_mid:12.1f} | {tot_h_hi:11.1f} | {tot_prov/1e6:7.0f} MB")
    a_(f"#   ⚠This is well under the campaign's P3 budget of {p3['worker_hours'][0]}-{p3['worker_hours'][1]} worker-hours, for two reasons that are both stated rather than")
    a_(f"#   banked: that budget used a flat 1.3-3.0 s/pose over all {p3['count']} records, while all eight geometries have a MEASURED rate here")
    a_(f"#   ({min(min(x['s_per_pose'] for x in m) for m in cells.values()):.3f}-{max(max(x['s_per_pose'] for x in m) for m in cells.values()):.3f} s/pose); and {designed-len(lines)} of the {designed} records are reused. The band above is the honest range; a")
    a_("#   busier host moves it up, and a new-shape line (n{:,}, one shard, full dump) has never been run, so the first line is a probe.".format(npose[-1]))
    a_("#")
    a_("# DISK. --dump-paths writes outputs/path_provenance/<stem>_prov.npz beside the shard. Its per-path record is")
    a_(f"#   a complex64 (8 B) + tau float64 (8 B) + part int16 x depth ({2*DEPTH} B) + obj_raw int64 x depth ({8*DEPTH} B) + prim int64 x depth ({8*DEPTH} B)")
    a_(f"#   = 16 + 18 x max_depth = {16+18*DEPTH} B per path UNCOMPRESSED at depth {DEPTH} (read off the sidecar dtypes; at depth 3 it would be {16+18*3} B).")
    a_("#   ⛔That number is the schema width, NOT the disk footprint: the sidecar is np.savez_compressed")
    bp = [c["prov_B"] / (c["nret_med"] * c["npos"]) for m in cells.values() for c in m]
    a_(f"#   (elevation_sweep_md.py:1253), and the measured on-disk cost over the ten stored cells is {min(bp):.2f}-{max(bp):.2f} B per path per")
    a_(f"#   position. The estimate above uses measured BYTES PER POSITION of the same geometry ({min(c['prov_B_per_pose'] for m in cells.values() for c in m):,.0f}-{max(c['prov_B_per_pose'] for m in cells.values() for c in m):,.0f} B/pose), which needs no")
    a_(f"#   path-count assumption at all. Total for this package: {tot_prov/1e6:,.0f} MB of sidecars plus about {tot_npz/1e6:.1f} MB of shard npz")
    a_(f"#   ({npz_per_pose:.0f} B/pose, measured on the same ten). df on /workspace at build time: {free_B/1e9:,.0f} GB = {free_B/2**30:,.0f} GiB free (what")
    a_(f"#   `df -h` prints), so this package is")
    a_(f"#   {100*(tot_prov+tot_npz)/free_B:.2f} % of it. ⚠Host RAM, computed: the dump is accumulated in memory and concatenated before writing, so the")
    a_(f"#   largest line ({max(meta_rows, key=lambda r: r['ram_GB'])['label']} at {max(meta_rows, key=lambda r: r['ram_GB'])['rate']:,} Hz, nret median {max(meta_rows, key=lambda r: r['ram_GB'])['nret_med']:,.0f}) peaks near {max(r['ram_GB'] for r in meta_rows):.1f} GB of host RAM,")
    a_("#   about twice the raw array total. That is one worker; with several such lines at once the host figure multiplies.")
    a_("#")
    a_("# NAMES. The sweep builds the stems; --dump-paths does not change a name. All distinct, none present in")
    a_(f"#   outputs/elev_sweep_shards/. Common to all {len(lines)}: prefix sionna_p{SPP}_sw{SW}_ and suffix")
    a_(f"#   _shell{SHELL_MM:g}mm_prop{PROP_MM:g}mm_mfixbatteryi5_blperairframe_ant{ANT}_rt210_d{DEPTH}_el<el>_00.npz")
    for i, r in enumerate(meta_rows, 1):
        a_(f"#   line {i:2}  {r['stem']}")
    a_("#")
    a_("# ============================================================================================================================")
    a_("# READ-OUT, fixed before any shard of this file is read")
    a_("# ============================================================================================================================")
    a_("# Metric names are the repo's fixed ones (docs/READOUT_0917.md sec.1: isolated_20xmedian, hampel_w51_k5,")
    a_("#   env_field_drop_halfmedian, env_path_missing, copy_k_ratio / copy_k_diff, contrast_raw / contrast_dedup / contrast_interp).")
    a_("#   E_B, drone paths, environment-only paths, contrast_gated, env_in_bin_db are defined in the runners/jobs_0957 header;")
    a_("#   lvl_db, ac_level_db, ac_to_static_db, hits_per_pose, path_class, class_power_db, seed_diff in the runners/jobs_0960 header.")
    a_("#   Four new quantities, each defined here where it first appears:")
    a_(f"#   t_common        the grid t_k = k/{rates[0]} s, k = 0 ... {npose[0]-1} - the only times at which two rates are compared directly. Only")
    a_(f"#                   {rates[2]:,} and {rates[3]:,} Hz land exactly on it; {rates[1]:,} Hz shares only t_0, so its comparison is interpolated and is")
    a_("#                   reported as such, never as a sample-to-sample difference.")
    a_("#   resid_tot_db    10*log10( mean_t |E_hi(t) - E_lo_interp(t)|^2 / mean_t |E_hi(t)|^2 ) on t_common, E_lo_interp = the lower rate")
    a_("#                   linearly interpolated up. The TOTAL-field residual. ⛔Written, never gated on (see the hiding rule above).")
    a_("#   resid_ac_db     the same ratio computed after subtracting each record's own time mean over t_common. The AC residual. This")
    a_("#                   is the one that gates.")
    a_("#   above_nyq_frac  the fraction of a record's AC power above the NEXT LOWER rate's Nyquist, per rate pair. 0961 reports 1.623 %")
    a_(f"#                   for the {rates[0]:,} -> {rates[1]:,} Hz pair at the sky anchor; this file re-measures it at eight geometries.")
    a_("#   S. Spread FIRST, before any rate-to-rate reading. seed_diff of resid_ac_db, lvl_db, ac_level_db, ac_to_static_db and")
    a_("#      contrast_raw at the two anchors, at each rate, from the seed-1/seed-2 pair. ⛔Any rate-to-rate change smaller than")
    a_("#      3 x seed_diff is written \"not told apart from a solver repeat\" and crosses nothing. The spread is a per-rate number: a")
    a_("#      spread measured at one rate is not carried to another.")
    a_("#   C. Cap, every shard: n_trunc[0] = 0 against the path cap. Any position at the cap and that record is dropped from T1-T3,")
    a_("#      per the standing rule that a saturating cap makes the axis unmeasurable. Expectation from the stored partners above")
    a_(f"#      (nret median {min(c['nret_med'] for m in cells.values() for c in m):,.0f}-{max(c['nret_med'] for m in cells.values() for c in m):,.0f}, n_trunc 0 everywhere) - an expectation, not a threshold.")
    a_("#   0. Integrity: check 0 of runners/jobs_0957 on the first sidecar of this file and on the first ground sidecar - at every")
    a_("#      position |sum_hit a*exp(-j2pi*fc*tau) - E| / |E| < 1e-4. Fails -> nothing further from this file launches.")
    a_(f"#   T1. Rate convergence of the AC part, per geometry: resid_ac_db between the two highest rates ({rates[2]:,} -> {rates[3]:,} Hz)")
    a_("#       <= -30 dB AND that residual smaller than the same-rate seed_diff at the anchors -> \"the AC part of the hover field is")
    a_(f"#       carried at {rates[2]:,} Hz at this geometry (threshold not crossed)\". -30 dB is fixed here in advance as the candidate")
    a_("#       tolerance the recommendations name; -20 dB is reported beside it so the choice can be seen, and the final tolerance is")
    a_("#       decided later by whether a detection or tracking choice changes, not here.")
    a_(f"#   T2. The rate the receiver actually gets: resid_ac_db of {rates[1]:,} Hz against {rates[3]:,} Hz, every geometry. Reported with")
    a_("#       above_nyq_frac for the pair. ⛔This is the number that decides P4's master grid, so it is read at ALL eight geometries")
    a_("#       and the WORST one is quoted, never the median - the median hides a mixture, and eight geometries is already few.")
    a_("#   T3. Path-wise, not just field: at t_common, for each path class, the delay and the complex coefficient at the two highest")
    a_("#       rates. A class whose delay moves by more than 1 cm or whose coefficient moves by more than the anchor seed_diff is")
    a_("#       named, with its class. ⛔A class present at one rate and absent at the other is reported as an appearance/disappearance")
    a_("#       count and NOT as a coefficient difference; pose-by-pose object index is not a persistent path ID.")
    a_("#   Written per cell, not gated, never a verdict: hits_per_pose; nret median, max, n_trunc[0]; lvl_db, ac_level_db,")
    a_(f"#   ac_to_static_db; contrast_raw / _dedup / _interp on the common band |f| < {rates[0]/2:,.0f} Hz with a fixed harmonic set; hampel_w51_k5;")
    a_("#   isolated_20xmedian with its normaliser; copy_k_ratio and copy_k_diff; class_power_db per class; and, at the ground cells")
    a_("#   only, env_in_bin_db and env_path_missing against the matched open-sky cell of the same range, elevation and rate.")
    a_("#   ⚠Scope in every sentence: constant-RPM rotor trajectory (no --rotor-preset, so rotor variability is P8's axis and not in")
    a_("#   this file), hover only, one azimuth, one carrier, co-located TX/RX, tr38901 as a stand-in and not the real antennas,")
    a_("#   3.5 GHz as a working assumption, sionna-rt 2.1.0, diffuse on / refraction and diffraction off, no receiver noise, no TX-RX")
    a_("#   leakage, one flat synthetic ground plate. A uniform rate ladder also does not stand in for NR symbol timing or CP structure.")
    a_("#")
    a_("# STOP / EXTEND.")
    a_("#   . check 0 fails -> nothing further launches; lines already running finish and are read on lvl_db only.")
    a_("#   . C fails anywhere -> that record is dropped from T1-T3 and re-read only after the cap is raised. No cap ladder here.")
    a_("#   . T1 and T2 both hold at all eight geometries -> STOP. The master grid for P4 is then the lowest rate that passed, and no")
    a_("#     further rate is bought for hover at any geometry inside this range.")
    a_(f"#   . T1 crossed at one or two geometries only -> ONE higher rate ({2*rates[3]:,} Hz, n {int(round(2*rates[3]*win)):,}) at THOSE geometries only, and nowhere")
    a_("#     else. It is a comment here, not a queue line, and it must be dry-run before use. Template (sky anchor):")
    _k, _r, _e, _v, _al, _lb = next(g for g in GEOMETRIES if g[0] == ANCHOR_SKY)
    a_(f"#     # {job_line(_r, _e, _v, _al, int(round(2*rates[3]*win)), 2*rates[3], 1)}")
    a_("#   . T1 holds but T3 names a class whose delay moves -> that is a path-return question, not a rate question: it goes to P1's")
    a_("#     diagnostics on the stored sidecars before any line is bought.")
    a_("#   . above_nyq_frac is large at the top rate too -> the ladder did not reach a converged rate, and that is what is written.")
    a_("#     ⛔No claim that the top rate is correct, and no rate ladder is extended more than one step without a new file.")
    a_("#   . In no outcome from this file: another geometry, azimuth, carrier, depth, ray budget or drone slab; a rotor preset; a third")
    a_("#     seed; an n-at-fixed-prf record-length ladder; walls or the full scene; a second anchor pair.")
    a_("#")
    a_("# Rules kept: open sky and outdoor ground only; R0D0E0F1 on every line (diffuse always on, refraction and diffraction off);")
    a_("#   no propeller-only arms; _rt210 added automatically by the builder; --inmem is the default and is not restated; cap 2e6 with")
    a_("#   no cap ladder; the canonical thin slab 0.75 / 1.43 mm on every line, so this file reads against the 0960-0965 families.")
    a_(f"# Dry run of the {len(lines)} lines below, {DRYRUN['when']}.")
    a_(f"#   {DRYRUN['how']}:")
    a_(f"#   {DRYRUN['new']}/{len(lines)} NEW, {DRYRUN['done']} DONE, {DRYRUN['stale']} STALE, {DRYRUN['bad']} BAD.")
    a_(f"#   {DRYRUN['stems_readback']}.")
    a_(f"#   The {designed - len(lines)} reuse cells of the REUSE table, dry-run as {designed - len(lines)} x 2 shard lines in the same pass:")
    a_(f"#   {DRYRUN['reuse_done']}/{(designed-len(lines))*2} DONE, {DRYRUN['reuse_new']} NEW, {DRYRUN['reuse_stale']} STALE, {DRYRUN['reuse_bad']} BAD - which is what \"reused, not re-bought\" rests on.")
    a_(f"#   Flag-set comparison: {DRYRUN['flagscan']}.")
    a_(f"#   ⚠Nearest neighbours: {DRYRUN['nearest']}.")
    a_("# ----------------------------------------------------------------------------------------------------------------------")

    body = []
    cur = None
    for ln, r in zip(lines, meta_rows):
        tag = (r["key"], r["seed"])
        if tag != cur:
            cur = tag
            m = cells[tag]
            _, g_rng, g_el, g_env, g_alt, _ = next(g for g in GEOMETRIES if g[0] == r["key"])
            reused = stem(g_rng, g_el, g_env, g_alt, 4096, None, r["seed"], 2, 0)[:-7]
            body.append(f"# {r['label']}"
                        + (f", --solver-seed {r['seed']} (anchor)" if r["seed"] != 1 else "")
                        + f" - {rates[0]:,} Hz reused from {reused}_{{00,01}}.npz"
                        + f" ; {min(x['s_per_pose'] for x in m):.3f}-{max(x['s_per_pose'] for x in m):.3f} s/pose measured")
        body.append(ln)

    txt = "\n".join(H + body) + "\n"
    with open(a.out, "w") as fh:
        fh.write(txt)
    n_lines = len([x for x in body if not x.startswith("#")])
    print(f"wrote {a.out}: {n_lines} queue lines, {designed} designed records, "
          f"{designed - n_lines} reused, {tot_h_mid:.1f} worker-h (band {tot_h_lo:.1f}-{tot_h_hi:.1f}), "
          f"{tot_prov/1e6:.0f} MB sidecars", file=sys.stderr)


if __name__ == "__main__":
    main()
