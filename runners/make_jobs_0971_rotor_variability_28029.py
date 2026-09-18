# -*- coding: utf-8 -*-
"""make_jobs_0971_rotor_variability_28029.py — emit runners/jobs_0971 from the campaign matrix.

Stage 1, package P8A (rotor variability only).  The job file is a BUILD PRODUCT: every
argument line below is derived from `packages[7]` of /workspace/sionna_gpu_campaign_plan_2026-09-18.json
(P8, `geometry_anchors` / `rotor_presets` / `rotor_seeds` / `rotor_n_poses` / `rotor_rate_hz`),
never hand-typed, so the file can be rebuilt from the plan at any time.

⛔The mesh-revision bridge (P8's `mesh_records`, 8B of the recommendations §11) is NOT stage 1 and
  is NOT emitted here.  The generator asserts that it emits zero mesh-revision lines.

Every number printed into the header is computed here, from the repo code or from stored shards on
disk, and the source of each one is named in the header beside it.  Nothing is copied from the
recommendations document.

Run (CPU only, no GPU):
    CUDA_VISIBLE_DEVICES="" SIONNA2_ALLOW_CPU=1 MPLBACKEND=Agg \
      /workspace/.venvs/py312/bin/python make_jobs_0971_rotor_variability_28029.py

Optional second pass: if `stems_0971.json` sits next to this script (written by the dry-run pass,
a mapping {line -> stem}), the header gains the read-back stem table.  Without it the header says
the stems have not been read back yet.  Stems are NEVER assembled by hand here — elevation_sweep_md.py
:494-503 records the 2026-08-18 incident where a second copy of the name rule silently produced the
wrong arm — they are only ever quoted from the sweep's own `--dry-run`.
"""
from __future__ import annotations

import glob
import json
import os
import re
import shutil
import sys

import numpy as np

ROOT = "/workspace/sionna"
PLAN = "/workspace/sionna_gpu_campaign_plan_2026-09-18.json"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "jobs_0971_rotor_variability_28029.txt")
STEMS = os.path.join(HERE, "stems_0971.json")

sys.path.insert(0, os.path.join(ROOT, "src"))

# --------------------------------------------------------------------------------------------- #
#  Fixed choices of this package, each with the reason it is fixed (repeated in the header)
# --------------------------------------------------------------------------------------------- #
# --------------------------------------------------------------------------------------------- #
#  FROZEN HOST STATE. These four numbers are the only inputs of this generator that are not the
#  campaign JSON, the repo source or a stored shard. They were measured when this package was
#  built (2026-09-18 ~08:50 UTC) and are frozen so that re-running the generator reproduces the
#  job file byte for byte while queues 0963-0968 are still landing shards. The live values are
#  read anyway and any drift is printed on stderr, never into the file.
FROZEN = dict(free_bytes=1_041_336_623_104,   # shutil.disk_usage("/workspace").free
              mem_avail_gb=156.0,             # /proc/meminfo MemAvailable
              n_prov_files=85,                # sidecars in outputs/path_provenance with a matching shard
              bpp_min=5.52, bpp_max=8.71)     # B per returned path per position, over those sidecars

SPP = 4_000_000_000          # the campaign's standing ray budget and the ceiling of the P1 ladder
SW = "R0D0E0F1"              # refraction off, diffraction off, edge diffraction off, diffuse ON
MAX_DEPTH = 2                # see header: the only depth all six geometries already have on disk
SHELL_MM, PROP_MM = 0.75, 1.43
ANT = "tr38901"
NSHARDS = 2                  # 8,192 positions -> 4,096 per shard
BLADES_DEFAULT = 2           # elevation_sweep_md.py:404 getattr(spec, "blades", 2); matrice4e has none


def load_plan() -> dict:
    with open(PLAN) as fh:
        plan = json.load(fh)
    pkgs = [p for p in plan["packages"] if p.get("id") == "P8"]
    if len(pkgs) != 1:
        raise SystemExit(f"⛔ expected exactly one P8 package in {PLAN}, found {len(pkgs)}")
    p8 = pkgs[0]
    for key, want in (("rotor_n_poses", 8192), ("rotor_rate_hz", 28029),
                      ("rotor_records", 54)):
        if int(p8[key]) != want:
            raise SystemExit(f"⛔ {PLAN} packages P8 {key} = {p8[key]}, this generator was written for {want}")
    if len(p8["geometry_anchors"]) != 6:
        raise SystemExit("⛔ P8 must carry exactly 6 geometry anchors")
    return p8


def geometries(p8: dict) -> list[dict]:
    """The six anchors, in the plan's own order, with a short label and the computed radar height."""
    out = []
    for i, g in enumerate(p8["geometry_anchors"], start=1):
        rng_m = float(g["range_m"])
        el = float(g["elevation_deg"])
        az = float(g["azimuth_deg"])
        ground = str(g["scene"]) == "ground"
        alt = g.get("env_alt_m")
        if ground and alt is None:
            raise SystemExit(f"⛔ anchor {i} is a ground cell with no env_alt_m")
        if (not ground) and alt is not None:
            raise SystemExit(f"⛔ anchor {i} is a sky cell but carries env_alt_m")
        # report15_probe.place(): radar at centre + range*(cos el cos az, cos el sin az, sin el),
        # baseline 0.0 at elevation_sweep_md.py:1071 -> TX and RX co-located.
        # env_parts() lowers the plate by --env-alt, so H = --env-alt is the drone height above it
        # and the radar height is h = H + range*sin(el); the horizontal separation is range*cos(el).
        h = (float(alt) + rng_m * np.sin(np.radians(el))) if ground else None
        d_horiz = rng_m * np.cos(np.radians(el))
        out.append(dict(i=i, label=f"G{i}", range_m=rng_m, el=el, az=az, ground=ground,
                        env_alt=(float(alt) if ground else None), radar_h=h, d_horiz=d_horiz,
                        name=(f"R{rng_m:g} el{el:+g}"
                              + ("" if az == 0 else f" az{az:g}")
                              + (f" ground alt{float(alt):g}" if ground else " sky"))))
    return out


def line_for(g: dict, n_poses: int, prf: int, preset: str | None, rseed: int | None,
             shard: int) -> str:
    """One argument line.  Flag ORDER follows runners/jobs_0961 / 0965 so the files read alike."""
    parts = ["--engine sionna",
             f"--n-poses {n_poses}",
             f"--prf {prf}",
             f"--range-m {g['range_m']:g}",
             f"--sw {SW}",
             f"--spp {SPP}",
             f"--max-depth {MAX_DEPTH}",
             f"--els={g['el']:g}"]
    if g["az"] != 0:
        parts.append(f"--az-deg {g['az']:g}")
    if g["ground"]:
        parts.append("--env outdoor01_ground")
        parts.append(f"--env-alt {g['env_alt']:g}")
    parts += [f"--ant-pattern {ANT}", f"--shell-mm {SHELL_MM:g}", f"--prop-mm {PROP_MM:g}"]
    if preset:
        parts.append(f"--rotor-preset {preset}")
        parts.append(f"--rotor-seed {int(rseed)}")
    parts += [f"--dump-paths {n_poses // NSHARDS}", f"--shard {shard}", f"--nshards {NSHARDS}"]
    return " ".join(parts)


def records(p8: dict, geo: list[dict]) -> list[dict]:
    """54 records: 6 geometries x (2 presets x 4 seeds + 1 constant-RPM control)."""
    n = int(p8["rotor_n_poses"])
    prf = int(p8["rotor_rate_hz"])
    presets = list(p8["rotor_presets"])
    seeds = [int(s) for s in p8["rotor_seeds"]]
    if "outdoor_v2_eff" in presets:
        raise SystemExit("⛔ outdoor_v2_eff is a 0.25 s-window-only preset and must not appear here")
    recs = []
    for g in geo:
        for preset in presets:
            for s in seeds:
                recs.append(dict(g=g, preset=preset, seed=s, n=n, prf=prf))
        recs.append(dict(g=g, preset=None, seed=None, n=n, prf=prf))   # constant-RPM control
    if len(recs) != int(p8["rotor_records"]):
        raise SystemExit(f"⛔ built {len(recs)} records, plan says {p8['rotor_records']}")
    return recs


# --------------------------------------------------------------------------------------------- #
#  Measurements from the repo — every header number comes from one of these
# --------------------------------------------------------------------------------------------- #
def shard_family(g: dict) -> str:
    """Glob for the stored shards of exactly this geometry, depth and material, any length/seed/rate.

    The `_az` and `_fc` tags are part of the geometry, so a sky cell at az 0 must not match an
    az-swept cell and a 3.45/3.55 GHz cell must not match a 3.5 GHz one."""
    base = f"{ROOT}/outputs/elev_sweep_shards/sionna_p{SPP}_sw{SW}_r{g['range_m']:g}_n*"
    mid = (f"_envoutdoor01_ground_alt{g['env_alt']:g}" if g["ground"] else "")
    az = (f"_az{g['az']:g}" if g["az"] else "")
    # a free `*` before the azimuth tag so that a --solver-seed partner (`_ss2`, which the sweep
    # writes between the altitude and the azimuth) is not silently dropped; _match_no_extra_tags()
    # then rejects anything the wildcard swallowed that is not part of this geometry.
    return (base + mid + "*" + az +
            f"_shell{SHELL_MM:g}mm_prop{PROP_MM:g}mm_mfixbatteryi5_blperairframe"
            f"_ant{ANT}_rt210_d{MAX_DEPTH}_el{g['el']:+g}_*.npz")


def _match_no_extra_tags(path: str, g: dict) -> bool:
    """Reject files whose name carries a tag the glob's `n*` swallowed (fc, az, env, drone...)."""
    b = os.path.basename(path)
    head = b.split("_shell")[0]
    tail = head.split(f"_r{g['range_m']:g}_", 1)[1]        # e.g. "n4096_prf28029" or "n1024_az12"
    bits = tail.split("_")
    allowed_prefix = ("n", "prf", "rep", "ss")
    if g["ground"]:
        allowed = {"envoutdoor01", "ground", f"alt{g['env_alt']:g}"}
    else:
        allowed = set()
    if g["az"]:
        allowed.add(f"az{g['az']:g}")
    for b_ in bits:
        if b_ in allowed:
            continue
        if any(b_.startswith(p) and b_ != p for p in allowed_prefix):
            continue
        return False
    return True


def measure(g: dict) -> dict:
    """Wall seconds per pose (meta[5]/len(idx)) and sidecar bytes per position, from stored shards."""
    files = [f for f in sorted(glob.glob(shard_family(g))) if _match_no_extra_tags(f, g)]
    sp, side, names, sidenames, nret_med, npz_bytes = [], [], [], [], [], []
    for f in files:
        try:
            z = np.load(f)
            npos = len(z["idx"])
            sec = float(np.asarray(z["meta"]).ravel()[5])
        except Exception:                                   # noqa: BLE001
            continue
        sp.append(sec / npos)
        names.append(os.path.basename(f))
        npz_bytes.append(os.path.getsize(f) / npos)
        nret_med.append(float(np.median(np.asarray(z["nret"]))))
        pv = (f"{ROOT}/outputs/path_provenance/"
              + os.path.basename(f).replace(".npz", "_prov.npz"))
        if os.path.exists(pv):
            side.append(os.path.getsize(pv) / npos)
            sidenames.append(os.path.basename(pv))
    if not sp:
        raise SystemExit(f"⛔ no stored shard matches {g['name']} — cost cannot be computed")
    if not side:
        raise SystemExit(f"⛔ no stored path-provenance sidecar for {g['name']}")
    return dict(sec_per_pose=sorted(sp), files=names, nret_med=sorted(nret_med),
                side_b_per_pos=sorted(side), side_files=sidenames,
                npz_b_per_pos=sorted(npz_bytes))


def rotor_facts(n: int, prf: int) -> dict:
    """Preset parameters and the length dependence of --rotor-seed, computed from src/rotor_dynamics."""
    import rotor_dynamics as rd
    from rotor_dynamics import get, initial_phase_deg, rpm_series

    tj = json.load(open(f"{ROOT}/outputs/report07_three_engines.json"))["_meta"]
    rpms = np.asarray(tj["rpm_per_rotor"], float)
    n_rot = rpms.size
    rpm0 = float(rpms.mean())
    out = {"rpm_per_rotor": rpms.tolist(), "rpm0": rpm0, "n_rot": n_rot,
           "coarse_hz": float(rd.COARSE_HZ), "presets": {}, "lenbind": {}}
    period_deg = 360.0 / float(BLADES_DEFAULT)
    for name in ("sitl", "outdoor_v2", "outdoor_v2_eff"):
        j = get(name)
        out["presets"][name] = dict(static_sigma=float(j.static_sigma),
                                    wobble_sigma=float(j.wobble_sigma),
                                    tau_ctl_s=float(j.tau_ctl_s),
                                    random_phase=bool(j.random_phase))
    for name in ("sitl", "outdoor_v2"):
        j = get(name)
        got = {}
        for nn in (n, n // 2, n // 4):
            rng = np.random.default_rng(1)
            rpm_t, diag = rpm_series(rpm0, n_rot, nn, prf, j, rng)
            b = initial_phase_deg(n_rot, j, rng, period_deg)
            got[nn] = (np.asarray(diag["static_offsets"]), np.asarray(b), rpm_t)
        same_stat = bool(np.allclose(got[n][0], got[n // 2][0], atol=0, rtol=0))
        same_ph = bool(np.array_equal(got[n][1], got[n // 2][1]))
        common = min(n // 2, got[n][2].shape[0])
        drpm = float(np.abs(got[n][2][:common] - got[n // 2][2][:common]).max())
        out["lenbind"][name] = dict(
            static_same=same_stat, phase_same=same_ph,
            phase_full=np.round(got[n][1], 4).tolist(),
            phase_half=np.round(got[n // 2][1], 4).tolist(),
            phase_quarter=np.round(got[n // 4][1], 4).tolist(),
            max_abs_rpm_diff_on_common_prefix=drpm,
            rel_rpm_diff=drpm / rpm0,
            n_coarse=int(np.ceil(nn / prf * rd.COARSE_HZ)) + 2 if j.wobble_sigma > 0 else 0,
            n_coarse_full=int(np.ceil(n / prf * rd.COARSE_HZ)) + 2 if j.wobble_sigma > 0 else 0)
    return out


def existing_flag_sets() -> dict[frozenset, list[str]]:
    """Every --engine line of every runners/jobs_*.txt, commented and #HOLD included, as a flag set."""
    seen: dict[frozenset, list[str]] = {}
    for path in sorted(glob.glob(f"{ROOT}/runners/jobs_*.txt")):
        for ln, raw in enumerate(open(path), start=1):
            t = raw.strip()
            # peel every layer of comment marker and the HOLD tags, so a #HOLD-rev1 line and a
            # doubly-commented extension template are both compared, not silently skipped
            while True:
                t2 = t
                if t2.startswith("#"):
                    t2 = t2.lstrip("#").strip()
                for tag in ("HOLD-rev1", "HOLD"):
                    if t2.startswith(tag):
                        t2 = t2[len(tag):].strip()
                if t2 == t:
                    break
                t = t2
            if not t.startswith("--engine"):
                continue
            seen.setdefault(frozenset(t.split()), []).append(f"{os.path.basename(path)}:{ln}|{t}")
    return seen


def fmt_band(v: list[float], unit: str = "", dp: int = 3) -> str:
    med = float(np.median(v))
    return (f"{min(v):.{dp}f} / {med:.{dp}f} / {max(v):.{dp}f}{unit} (n={len(v)})")


# --------------------------------------------------------------------------------------------- #
#  Header
# --------------------------------------------------------------------------------------------- #
def header(p8, geo, recs, meas, rot, stems, dup_note, totals) -> str:
    n = recs[0]["n"]
    prf = recs[0]["prf"]
    dur = n / prf
    bin_hz = prf / n
    nyq = prf / 2.0
    rpms = np.asarray(rot["rpm_per_rotor"])
    flash = rpms * BLADES_DEFAULT / 60.0
    L = []
    A = L.append

    A(f"# 0971 — rotor variability at {prf:,} Hz: does a rotor model and a rotor realisation move the")
    A("#        micro-Doppler quantities we read, at the six geometries stage 1 anchors on? Two rotor")
    A(f"#        models (sitl, outdoor_v2) x four rotor seeds, plus the canonical constant-RPM rotor as")
    A(f"#        the control, at one record length ({n:,} positions, {dur*1000:.2f} ms) and one rate.")
    A(f"#        {len(recs)} records, {len(recs)*NSHARDS} shard lines. Path lists on every position.")
    A("#        (2026-09-18 KST, package P8A / stage 1 of /workspace/sionna_queue_recommendations_2026-09-18.md §11 8A,")
    A("#         matrix from packages[7] of /workspace/sionna_gpu_campaign_plan_2026-09-18.json)")
    A("#")
    A("# BUILD PRODUCT — do not hand-edit. Rebuild with")
    A("#   CUDA_VISIBLE_DEVICES=\"\" SIONNA2_ALLOW_CPU=1 MPLBACKEND=Agg python make_jobs_0971_rotor_variability_28029.py")
    A("#   The six geometries, the two preset names, the four seeds, the length and the rate are read from the")
    A("#   campaign JSON; the generator refuses to run if any of them has changed. Every number below is computed")
    A("#   by the generator from the code or from stored shards, and the source is named beside it.")
    A("#")
    A("# ⛔What is NOT here. P8's second half — the Matrice 4E revision 0/1 mesh bridge (8B, 36 n1024 records) — is")
    A("#   not part of stage 1 and no line of it appears in this file. docs/MESH_REV1.md records that no airframe")
    A("#   fingerprint is frozen, and the standing rule is that acceptance is not lowered to fill a GPU queue.")
    A("#")
    A("# Launch preconditions (main session).")
    A("#   (1) Path-list integrity (check 0 of the runners/jobs_0957 header) has passed on a GPU sidecar. Every line")
    A("#       here carries path lists and the whole read-out below rests on them; without them only the total field")
    A("#       survives and the static/varying split (below) cannot be made. If check 0 has never passed, nothing here")
    A("#       launches.")
    A("#   (2) This file does NOT wait on P1. 8A of the recommendations says to use the anchors whose P1 gate has")
    A("#       passed; P1 has not run, so the rule is kept the other way round: this file buys the rotor axis at the")
    A("#       six anchors and writes NO verdict that P1 owns. Nothing here is read as a budget, depth or solver-seed")
    A("#       statement, and every reading below is made against this file's own constant-RPM control and its own")
    A("#       seed spread, never against a stored cell solved at another length or rate.")
    A("#   (3) Queues 0963-0968 are untouched by this file. It is queued behind them.")
    A("#")
    A("# Purpose. Everything the repo has read about rotor lines — comb contrast, the AC share, the blade-flash")
    A("#   picture — was solved with ONE rotor: the ledger's four constant rpm values, phase-aligned at t = 0")
    A("#   (elevation_sweep_md.py:411 takes the constant-rpm branch when --rotor-preset is absent). A real airframe")
    A("#   holds neither the constant speeds nor that alignment. src/rotor_dynamics.py exists to say so, and what")
    A("#   the PathSolver arm has of it is an old,")
    A("#   narrow slice, counted here from outputs/elev_sweep_shards/ at build time:")
    pr = totals["prior"]
    A(f"#     {pr['n_sionna']} distinct PathSolver stems carry a `_rot` tag (and {pr['n_ours']} more on our own kernel), but")
    A(f"#     the only preset among them is {', '.join(pr['presets'])} — `sitl` has never been solved with PathSolver at all;")
    A(f"#     {pr['with_rt210']} of the {pr['n_sionna']} carry the `_rt210` build tag, {pr['with_ant']} carry an antenna tag, {pr['with_slab']} carry the thin slab and")
    A(f"#     {pr['with_prf']} carry a `_prf` tag. So every one of them is the OLD solver build, the isotropic antenna, the")
    A(f"#     untouched 100 mm stock material and the default {19700:,} Hz rate;")
    A(f"#     their range is r{', r'.join(pr['ranges'])} m and their elevations are {', '.join(pr['els'])} deg — not one of the six anchors")
    A("#     of this campaign, and none with a ground plate under the drone (`envoutdoor01`, not `envoutdoor01_ground`).")
    A("#   ⇒ the rotor axis has never been crossed with the solver build, the antenna, the material and the rate this")
    A("#   campaign now reads on, and the second model (`sitl`) has never been run at all. This file buys that crossing")
    A("#   once, at the six anchors, and nothing else. ⛔None of the old `_rot` shards is a control for this file and")
    A("#   no number from them is put beside a number from here.")
    A("#   What the result changes: if the quantities we read move less across models and seeds than they move across")
    A("#   the six geometries, rotor realisation is not a confound for the placement question and the constant-RPM")
    A("#   library stays readable; if they move more, every rotor-line number in the campaign has to carry a")
    A("#   realisation spread beside it, and the classification and short-CPI work is re-planned around that spread.")
    A("#")
    A("# What --rotor-preset and --rotor-seed actually do, read from the code, not from a note.")
    A("#   elevation_sweep_md.py:398-411 — with a preset the run takes")
    A("#       _rng    = np.random.default_rng(--rotor-seed)")
    A("#       _rpm_t, = rpm_series(mean(ledger rpm), n_rotors, n, prf, preset, _rng)   # (n, 4) rpm column")
    A("#       _b      = initial_phase_deg(n_rotors, preset, _rng, 360/blades)          # blades defaults to 2")
    A("#       ph      = rotor_phases(arange(n)/prf, _rpm_t, dirs, base_deg=_b, dt=1/prf)")
    A("#     ⚠the preset REPLACES the ledger's per-rotor spread (only its mean is passed on), it does not add to it.")
    A("#     ⛔--rotor-seed without --rotor-preset is refused by the sweep (:647-653) — the seed is only read inside")
    A("#       the preset branch, so seed-only lines would name `s1`/`s2` files with identical content.")
    A("#   src/rotor_dynamics.py, values read from the module at build time:")
    for nm in ("sitl", "outdoor_v2", "outdoor_v2_eff"):
        pr = rot["presets"][nm]
        A(f"#     {nm:15s} static sigma {pr['static_sigma']:.4f} · wobble sigma {pr['wobble_sigma']:.4f} · "
          f"tau_ctl {pr['tau_ctl_s']:.4f} s · random initial phase {pr['random_phase']}")
    A("#     sitl is the symmetric lower bound (PX4 SITL: no wind, no CG offset, no propeller unit-to-unit spread),")
    A("#     outdoor_v2 is the outdoor corpus model (52 airframes, NOT DJI, hover only, absolute scale open ±30 %).")
    A("#     ⛔outdoor_v2_eff is NOT used here and appears on no line: rotor_dynamics.py:405-412 fixes it to a single")
    A(f"#       {float(getattr(__import__('rotor_dynamics'), 'SIGMA_EFF_WINDOW_S')):.2f} s window, and our records are {dur:.4f} s — longer than that window, so the folded")
    A("#       constant offset would not reproduce the same comb.")
    A("#")
    A("# ⚠Reproducibility of --rotor-seed, verified by running the generator itself (not quoted from a doc).")
    lb_s, lb_o = rot["lenbind"]["sitl"], rot["lenbind"]["outdoor_v2"]
    A(f"#   sitl   : wobble sigma is 0, so _wobble() returns zeros WITHOUT drawing (rotor_dynamics.py:473-474) and the")
    A(f"#            seed is consumed only by the 4 static offsets and the 4 initial phases. Same seed, lengths")
    A(f"#            {n}/{n//2}/{n//4}: static offsets identical {lb_s['static_same']}, initial phases identical {lb_s['phase_same']}.")
    A(f"#            ⇒ for sitl a record length change is safe.")
    A(f"#   outdoor_v2: wobble sigma > 0, so _wobble() draws an OU process on a {rot['coarse_hz']:g} Hz coarse grid of")
    A(f"#            n_c = ceil(n/prf x {rot['coarse_hz']:g}) + 2 samples — {lb_o['n_coarse_full']} samples at n={n} — BEFORE initial_phase_deg()")
    A("#            touches the same generator. The number of draws therefore depends on the record length:")
    A(f"#              initial phase, seed 1, n={n}     : {lb_o['phase_full']}")
    A(f"#              initial phase, seed 1, n={n//2}     : {lb_o['phase_half']}")
    A(f"#              initial phase, seed 1, n={n//4}     : {lb_o['phase_quarter']}")
    A(f"#            and the rpm column is not a prefix either: over the {n//2} samples the two records share, the")
    A(f"#            largest difference is {lb_o['max_abs_rpm_diff_on_common_prefix']:.4f} rpm ({lb_o['rel_rpm_diff']:.3e} of the mean) — the coarse OU samples are a")
    A("#            prefix but the cubic spline that lands them on the pose grid is not local.")
    A("#")
    A("# ⛔⚠`sitl` IS NOT IN src/arm_grammar.py's ROTOR TABLE — found by the 2026-09-18 cross-check of the four")
    A("#   stage-1 packages, not by this generator. The 48 `sitl` records name themselves `_rotsitls1` ... `_rotsitls4`;")
    A("#   src/arm_grammar.py parses them and they round-trip character for character (so the one reader that hard-fails")
    A("#   on a bad round trip, benchmark/dropout_paths_0916.py:312, is safe), but `warnings_for()` returns")
    A("#     \u314e\u314e")
    A("#     \"\ucc98\uc74c \ubcf4\ub294 \ub85c\ud130 'sitls1' (\uc544\ub294 \uac83 ['legacy', 'outdoor', 'outdoor_v2'] + \uc094\uc557)\"")
    A("#   on every one of them, because `_ROTOR_FORMS` / `KNOWN_VALUES[\"rotor\"]` list only legacy, outdoor and")
    A("#   outdoor_v2 with their seeds. Two real consequences: (1) any reader that treats an arm-grammar warning as a")
    A("#   defect flags 48 of the 54 records of this file; (2) the seed does not come back as its own field — for BOTH")
    A("#   presets parse() leaves it glued to the value (rotor = 'sitls1', rotor = 'outdoor_v2s1', rotor_seed = None),")
    A("#   which is the table's design for a KNOWN form but reaches `sitl` through the unknown-value path instead.")
    A("#   ⭐**Launch precondition for the main session:** add `sitl` and its seeds to `_ROTOR_FORMS` in")
    A("#   src/arm_grammar.py BEFORE these records are read, or every reading of this file carries a warning that has")
    A("#   nothing to do with the physics. Nothing in this file changes either way — the names the builder writes are")
    A("#   fixed by benchmark/elevation_sweep_md.py, not by the grammar.")
    A("#")
    A("#   ⇒ HOW A SHORT/LONG COMPARISON MUST BE DONE: generate ONE master realisation at the LONGEST length and CUT")
    A("#     it; never re-run the generator at a shorter --n-poses with the same --rotor-seed and call the two the same")
    A("#     realisation. The CLI has no flag for cutting, so the cut is made in the reader, on the stored record.")
    A(f"#     That is why EVERY record in this file is the same length ({n:,} positions) and the same rate ({prf:,} Hz):")
    A("#     the file is internally consistent by construction, and any short-CPI question below is answered by")
    A("#     cutting these records, not by a second, shorter queue line. Solver seed and rotor seed are different axes")
    A("#     and no line here moves --solver-seed.")
    A("#")
    A("# Matrix (from the campaign JSON, expanded by the generator).")
    A(f"#   6 geometries x 2 presets ({', '.join(p8['rotor_presets'])}) x 4 rotor seeds ({', '.join(str(s) for s in p8['rotor_seeds'])}) = 48 records")
    A(f"#   + 6 constant-RPM controls (no --rotor-preset, no --rotor-seed) = {len(recs)} records")
    A(f"#   x {NSHARDS} shards per record = {len(recs)*NSHARDS} argument lines.")
    A(f"#   Every line: --n-poses {n} --prf {prf} --spp {SPP:,} --sw {SW} --max-depth {MAX_DEPTH} --ant-pattern {ANT}")
    A(f"#   --shell-mm {SHELL_MM:g} --prop-mm {PROP_MM:g} --dump-paths {n//NSHARDS} --nshards {NSHARDS}. Nothing else varies.")
    A("#")
    A(f"# Record length and what it can resolve, computed here. {n} / {prf} Hz = {dur*1000:.3f} ms;")
    A(f"#   Doppler bin prf/n = {bin_hz:.4f} Hz; Nyquist prf/2 = {nyq:,.1f} Hz (against {19700/2:,.1f} Hz at the old 19,700 Hz rate).")
    A(f"#   Ledger rotor speeds (outputs/report07_three_engines.json _meta.rpm_per_rotor) {rot['rpm_per_rotor']} rpm,")
    A(f"#   2 blades ⇒ blade-flash rates {', '.join(f'{x:.2f}' for x in flash)} Hz, i.e. "
      f"{', '.join(f'{x*dur:.2f}' for x in flash)} flashes inside one record.")
    A(f"#   ⚠comb contrast depends on record length: the +-2-bin comb window here is {4*bin_hz:.2f} Hz wide. ⛔A contrast")
    A("#     from this file is never put beside an n1024, n4096 or 19,700 Hz contrast — only beside another line of")
    A("#     this file. The controls exist so that every comparison stays inside the file.")
    A("#")
    A("# Geometry, computed from the code, not from a note. report15_probe.place() puts the radar at")
    A("#   centre + range*(cos el cos az, cos el sin az, sin el), and elevation_sweep_md.py:1071 calls it with")
    A("#   baseline=0.0, so TX and RX are CO-LOCATED (report15_probe's module default BASELINE_M = 0.20 m is not used")
    A("#   by this sweep) and every path length here is monostatic. env_parts() lowers every environment part by")
    A("#   --env-alt and leaves the drone at the origin, so H = --env-alt is the drone height above the plate and the")
    A("#   radar height is h = H + range*sin(el).")
    A("#   | line group | geometry                         | horizontal D | radar height h | env |")
    for g in geo:
        A(f"#   | {g['label']:10s} | {g['name']:32s} | {g['d_horiz']:8.3f} m   | "
          + (f"{g['radar_h']:6.3f} m       " if g["ground"] else "n/a (free space)")
          + f" | {'outdoor01_ground' if g['ground'] else 'open sky':16s} |")
    A("#   The two ground heights are the campaign's standing ones and both put the radar within 2 cm of 1.5 m.")
    A("#")
    A(f"# Depth. Every line is --max-depth {MAX_DEPTH}, and that is a choice this file makes and states.")
    A("#   Reason: depth 2 is the only depth all six geometries already have a stored static partner at. At")
    A("#   R30 el-5 az0 ground the repo also has depth 3 (0962/0965), but at R15 el-15 ground alt5.4 and at both")
    A("#   az90 cells there is no depth-3 shard at any length, so a mixed-depth file could not be read across its own")
    A("#   six geometries. ⛔What is lost: the double-bounce class [g,d,g] needs depth 3 and does not exist in these")
    A("#   records. No sentence from this file may mention it, and the ground classes read here are [g,d] and [d,g]")
    A("#   only. If the rotor result turns on a class that needs depth 3, that is a new, separately costed line.")
    A("#")
    A("# Cost, computed from the stored shards of these exact geometries (meta[5] is wall seconds for the shard's pose")
    A("#   loop, so it carries GPU sharing and is a SLOT-hour basis, not a compute-hour one; the spread inside a pair of")
    A("#   interleaved shards is card sharing, not physics). Every basis shard listed carries a path-provenance sidecar,")
    A("#   so the dump cost is already inside these numbers.")
    A("#   | geometry   | wall s/pose min / median / max | basis shards | sidecar B/position | nret median |")
    for g in geo:
        m = meas[g["label"]]
        A(f"#   | {g['label']:10s} | {fmt_band(m['sec_per_pose']):30s} | {len(m['files']):2d} "
          f"| {min(m['side_b_per_pos']):9,.0f} - {max(m['side_b_per_pos']):9,.0f} | {int(np.median(m['nret_med'])):6d} |")
    A(f"#   Slot-hours for the {len(recs)} records = 9 records per geometry x {n} positions x s/pose, summed over the six:")
    A(f"#     {totals['h_min']:.1f} h (every geometry at its fastest stored shard) / {totals['h_med']:.1f} h (medians) /")
    A(f"#     {totals['h_max']:.1f} h (every geometry at its slowest). Per line ({n//NSHARDS} positions) that is")
    A(f"#     {totals['per_line_min_h']:.2f}-{totals['per_line_max_h']:.2f} h.")
    A(f"#   ⚠This is BELOW the {p8['worker_hours'][0]}-{p8['worker_hours'][1]} worker-hour band the campaign JSON carries for P8. That band covers P8's")
    A("#     54 rotor records AND its 36 mesh-bridge records and was built on a generic 1-2 s/pose; the measured medians")
    A("#     at these six geometries are lower. The band is not corrected here — it is the plan's number and this is the")
    A("#     measurement, and the difference is reported rather than hidden.")
    A("#")
    A("# Disk. --dump-paths writes a sidecar to outputs/path_provenance/<stem>_prov.npz (git-ignored since 0957).")
    A("#   ⚠The brief's «about 52 B per path per position» does NOT reproduce and is not used here. Measured on all")
    A(f"#   {totals['n_prov_files']} stored sidecars with a matching shard: {totals['bpp_min']:.2f}-{totals['bpp_max']:.2f} B per returned path per position after")
    A("#   np.savez_compressed. The same brief's own example (8.4 MB for a 2,048-position depth-3 ground shard) is")
    A(f"#   {totals['example_b_per_pos']:,.0f} B/position at nret median {totals['example_nret']:.0f}, i.e. {totals['example_b_per_path']:.2f} B/path — the 52 B figure and the 8.4 MB")
    A("#   example cannot both be right. The per-POSITION numbers in the table above are what this package is sized on.")
    A(f"#   Sidecar bytes this file adds: {totals['side_gb']:.2f} GB ({totals['side_bytes']:,} B), computed as 9 records x {n} positions x the")
    A("#   measured B/position of each geometry. Shard npz on top of that: about "
      f"{totals['npz_gb']:.2f} GB. Total about {totals['side_gb']+totals['npz_gb']:.2f} GB")
    A(f"#   against {totals['free_gb']:.0f} GB free on /workspace at build time ({totals['free_gib']:.0f} GiB, which is what `df -h` prints);")
    A(f"#   this package takes {totals['pct_free']:.2f} % of it. Every byte figure in this file is SI (10^9), like the sidecar sizes.")
    A("#   Held in host RAM while a shard runs: the provenance list is concatenated only at the end, so the peak is")
    A(f"#   about 2x the raw arrays. Measured raw (uncompressed) footprint of the worst geometry here is")
    A(f"#   {totals['raw_kb_per_pos']:.1f} kB/position ⇒ about {totals['raw_hold_mb']:,.0f} MB held per shard at {n//NSHARDS} positions. The largest")
    A(f"#   provenance ever written in this repo is {totals['max_prov_positions']:,} positions, so {n//NSHARDS} is {n//NSHARDS/totals['max_prov_positions']:.0f}x the proven")
    A(f"#   footprint and {n} (at --nshards 1) would be {n/totals['max_prov_positions']:.0f}x. That is why the split is --nshards {NSHARDS}: it keeps the held")
    A(f"#   arrays at about {totals['raw_hold_mb']:,.0f} MB per worker against {totals['mem_avail_gb']:.0f} GB available at build time, and it keeps a line to")
    A(f"#   {totals['per_line_min_h']:.2f}-{totals['per_line_max_h']:.2f} h so an interruption costs at most that. ⚠It is still above the proven footprint; the")
    A("#   first landed shard's peak RSS is checked before the rest of the file is released.")
    A("#")
    A("# Why --dump-paths is on every line, and what would be lost without it.")
    A("#   Three of the six geometries are ground cells, where the environment return is large and STATIC while the")
    A("#   rotor return is small and modulated. The repo's standing rule is that the static component leaks into the")
    A("#   STFT band and has to be subtracted before any rotor quantity is read. With path lists the record splits into")
    A("#   [d] (drone only), [g,d] and [d,g] (one ground leg) and [g] (ground only), so the modulated share can be")
    A("#   measured separately from the static one, per class and per part. Without them each shard stores only the")
    A("#   summed field E, the ground and the rotor are inseparable in it, and the whole comparison would be a comb")
    A("#   contrast computed on top of an unknown static pedestal — exactly the reading the repo has already recorded")
    A("#   as a fake peak generator. It would also make the sky and ground halves of this file unreadable against each")
    A("#   other, since the sky cells have no pedestal.")
    A("#   ⚠Sub-sampling the dump is not an option here. --dump-paths N spreads N positions evenly over the shard")
    A(f"#   (elevation_sweep_md.py:894-898), so N < {n//NSHARDS} would decimate the class time series; at a decimation of 8 the")
    A(f"#   effective rate is {prf/8:,.1f} Hz and its Nyquist {prf/16:,.1f} Hz, below the blade-flash harmonics this file exists to")
    A(f"#   measure ({min(flash):.1f} Hz fundamental). outputs/readout_0918.json gates.0961.T1_T2 puts")
    A(f"#   {totals['above_nyq_pct']:.3f} % of the rotor-part power above the 9,850 Hz Nyquist of the old 19,700 Hz rate at exactly the")
    A(f"#   geometry G1 of this file ({totals['above_nyq_cell']}),")
    A(f"#   verdict «{totals['above_nyq_verdict']}». So the class time series is kept at full rate and the cost above is paid.")
    A(f"#   Cost of the decision: {totals['side_gb']:.2f} GB, i.e. {totals['pct_free']:.2f} % of free space. Cost of not paying it: the ground half")
    A("#   of this file could not be read at all.")
    A("#")
    A("# Read-out — fixed before any shard of this file is read. Metric names are the repo's fixed ones")
    A("#   (docs/READOUT_0917.md §1: isolated_20xmedian, hampel_w51_k5, env_field_drop_halfmedian, env_path_missing,")
    A("#   copy_k_ratio / copy_k_diff, contrast_raw / contrast_dedup / contrast_interp); lvl_db, ac_level_db,")
    A("#   ac_to_static_db, hits_per_pose, path_class, class_power_db, seed_diff are defined in the runners/jobs_0960")
    A("#   header; E_B, drone paths, environment-only paths, contrast_gated, env_in_bin_db in the runners/jobs_0957")
    A("#   header. Two quantities are defined here where they first appear:")
    A("#   rotor_spread(q)   max over the 4 rotor seeds of q, minus the min over the same 4, at ONE geometry and ONE")
    A("#                     preset. It is a realisation spread, not a solver spread, and is never averaged with one.")
    A("#   model_gap(q)      q(outdoor_v2, seed s) - q(sitl, seed s), reported per seed and as the median over the 4;")
    A("#                     ⛔never reported without rotor_spread beside it.")
    A("#   0.  integrity: check 0 of runners/jobs_0957 on the first landed sidecar of this file, then on the first")
    A("#       ground sidecar: at every position |sum_hit a*exp(-j2pi*fc*tau) - E| / |E| < 1e-4. Fails -> see stop/extend.")
    A("#   C.  cap, every shard: n_trunc[0] = 0 against the path cap. Any position at the cap -> no level from that shard")
    A("#       is quoted and that cell is dropped, per the standing rule that a saturating cap makes the axis")
    A("#       unmeasurable. Expectation written before reading, from the stored constant-RPM partners of the same six")
    A(f"#       geometries: nret median {totals['nret_lo']:.0f}-{totals['nret_hi']:.0f} across the six, n_trunc[0] = 0 everywhere. It is an")
    A("#       expectation, not a threshold, and a rotor preset can move it.")
    A("#   S.  spread first: rotor_spread of ac_to_static_db, contrast_raw, lvl_db and class_power_db([d]) at every")
    A("#       geometry and preset, BEFORE any model comparison. Any model_gap within 3*rotor_spread is written «not")
    A("#       told apart from a rotor realisation» and crosses nothing.")
    A("#   R1. does the rotor MODEL move what we read: |model_gap(ac_to_static_db)| and |model_gap(contrast_raw)| at each")
    A("#       geometry, against 3*rotor_spread of the same quantity. Below at every geometry -> «the two rotor models")
    A("#       are not told apart at these six geometries by these quantities (threshold not crossed)».")
    A("#   R2. does the rotor REALISATION move it: rotor_spread(contrast_raw) and rotor_spread(ac_to_static_db) beside")
    A("#       the geometry-to-geometry spread of the same quantity across the six constant-RPM controls. Crossing is")
    A("#       defined as rotor_spread >= the geometry spread; below that -> «rotor realisation is smaller than geometry")
    A("#       at these anchors (threshold not crossed)».")
    A("#   R3. static/varying split, ground cells only, and only with path lists: the stationary share and the varying")
    A("#       share of the in-bin field are separated by class ([d] against [g,d]+[d,g]+[g]) before any rotor quantity")
    A("#       is quoted, and the rotor quantities of the ground cells are read on the varying share alone. ⛔No ground")
    A("#       rotor number is written from the summed field.")
    A("#   R4. the constant-RPM control against the models: every quantity is written for the control too, and any")
    A("#       sentence that compares this campaign's earlier constant-RPM results with a real rotor is written from")
    A("#       the control line of THIS file, never from a stored cell at another length or rate.")
    A("#   Written per cell, not gated, never used as a verdict: hits_per_pose; nret median, max and n_trunc[0];")
    A("#   lvl_db, ac_level_db, ac_to_static_db; contrast_raw, contrast_dedup, contrast_interp; hampel_w51_k5;")
    A("#   isolated_20xmedian with its normaliser; copy_k_ratio and copy_k_diff; class_power_db per class, part and")
    A("#   delay; env_in_bin_db and contrast_gated on the ground cells; and, for the ground cells only,")
    A("#   env_field_drop_halfmedian and env_path_missing against the matching sky cell of the same rotor line.")
    A("#   Scope in every sentence: one simulated airframe (Matrice 4E revision 0, canonical slab: shell 0.75 mm from")
    A("#   DJI Matrice 4T CAD, propeller 1.43 mm from our own mesh, recorded in docs/MATERIAL_CORRECTION.md §2-2 as")
    A("#   thicker than the real blade), one flat ITU-concrete ground plate, open sky otherwise, tr38901 as a stand-in")
    A("#   and not the real antennas, 3.5 GHz as a working assumption, sionna-rt 2.1.0, hover only, no receiver noise,")
    A("#   no TX-RX leakage, one run per cell. A rotor model fitted to 52 non-DJI airframes is not a measurement of")
    A("#   this airframe, and none of these records says anything about a real rotor's scattering-amplitude")
    A("#   fluctuation, which rotor_dynamics.py states is unmodelled.")
    A("#")
    A("# Names. The sweep builds the stems and --dump-paths does not change a name.")
    if stems:
        A(f"#   Read back from the sweep's own --dry-run ({stems['when']}), all {len(stems['map'])} distinct, none present in")
        A("#   outputs/elev_sweep_shards/. Common prefix and suffix of every stem:")
        A(f"#     sionna_p{SPP}_sw{SW}_ … _shell{SHELL_MM:g}mm_prop{PROP_MM:g}mm_mfixbatteryi5_blperairframe_ant{ANT}_rt210_d{MAX_DEPTH}_el<EL>_{{00,01}}.npz")
        for g in geo:
            ex = stems["by_geom"].get(g["label"], [])
            A(f"#   {g['label']} ({g['name']}): {len(ex)} stems. One of each kind, shard 00:")
            want = ("sitl seed 1, shard 00", "outdoor_v2 seed 1, shard 00", "constant-RPM control, shard 00")
            for w in want:
                for tag, st in ex:
                    if tag == w:
                        A(f"#     {tag:32s} {st}")
                        break
    else:
        A("#   ⚠NOT YET READ BACK — rebuild the file after the dry-run pass has written stems_0971.json beside the")
        A("#   generator. No stem is ever assembled by hand here (elevation_sweep_md.py:494-503 records what that cost).")
    A(f"#   Sidecars go to outputs/path_provenance/<stem>_prov.npz. Each record is split into {NSHARDS} INTERLEAVED shards")
    A(f"#   (idx = arange(shard, {n}, {NSHARDS}), elevation_sweep_md.py:430), so shard 00 holds the even positions and shard 01")
    A("#   the odd ones and BOTH are needed before any time-domain reading. ⛔A single shard of this file is a")
    A(f"#   {prf/NSHARDS:,.1f} Hz record, not a {prf:,} Hz one, and no spectrum, comb or STFT is computed from one shard alone.")
    A("#   The rotor realisation is built for the full length before the shard split (the rotor block runs at :398-411,")
    A("#   the split at :430), and the pose loop indexes ph[i] by the GLOBAL index (:993), so both shards of a record")
    A("#   carry the same realisation and merging them by idx reconstructs it exactly.")
    A("#")
    A("# Duplicates and neighbours.")
    A(dup_note)
    A("#")
    A("# Rules kept: open sky and outdoor01_ground only; R0D0E0F1 on every line (refraction, diffraction and edge")
    A("#   diffraction off, diffuse reflection on); no propeller-only arms; _rt210 added automatically by the build tag;")
    A("#   --inmem is the default; the canonical slab on every line; one run per cell; --solver-seed untouched, so")
    A("#   every line is solver seed 1 and the only randomness moved here is the rotor's.")
    A("#")
    A("# Stop / extend. Nothing below is queued from this file without a new, separately costed line.")
    A("#   · check 0 fails -> nothing further from this file launches; lines already running finish and are read on the")
    A("#     total field only; the dump is diagnosed on CPU and no line is re-bought to «try again».")
    A("#   · C fails anywhere -> that cell is dropped and re-read only after the cap is raised. No cap ladder here.")
    A("#   · R1 and R2 both below their thresholds -> STOP on the rotor axis: the constant-RPM library stays readable at")
    A("#     these anchors, and no further preset, seed or geometry is bought from this line of questions.")
    A("#   · R2 crosses at one geometry only -> at most FOUR more seeds at THAT geometry and that preset, nowhere else.")
    A("#   · R1 crosses -> the next question is which class carries the gap (R3 already splits it), answered on the")
    A("#     stored path lists on CPU, not by a new solve.")
    A("#   · In no outcome from this file: another rate or record length (see the reproducibility note — a shorter")
    A("#     record is a different realisation); outdoor_v2_eff; another preset; --solver-seed; another range, elevation")
    A("#     or azimuth; max_depth 3; another airframe or mesh revision; the 8B mesh bridge.")
    A("# " + "-" * 118)
    return "\n".join(L) + "\n"


def main() -> None:
    p8 = load_plan()
    geo = geometries(p8)
    recs = records(p8, geo)
    n, prf = recs[0]["n"], recs[0]["prf"]

    lines = []
    for r in recs:
        for sh in range(NSHARDS):
            lines.append(line_for(r["g"], r["n"], r["prf"], r["preset"], r["seed"], sh))
    if len(lines) != len(recs) * NSHARDS:
        raise SystemExit("⛔ line count does not match record count")
    if len(set(lines)) != len(lines):
        raise SystemExit("⛔ duplicate line inside this file")
    if any("mesh-rev" in ln or "rev1" in ln for ln in lines):
        raise SystemExit("⛔ a mesh-revision line leaked into a stage-1 file")
    if any("outdoor_v2_eff" in ln for ln in lines):
        raise SystemExit("⛔ outdoor_v2_eff leaked into a long-record file")

    meas = {g["label"]: measure(g) for g in geo}
    rot = rotor_facts(n, prf)

    # ---- cost and disk, all computed -------------------------------------------------------- #
    per_geom_records = len(recs) // len(geo)
    h_min = sum(per_geom_records * n * min(meas[g["label"]]["sec_per_pose"]) for g in geo) / 3600
    h_med = sum(per_geom_records * n * float(np.median(meas[g["label"]]["sec_per_pose"])) for g in geo) / 3600
    h_max = sum(per_geom_records * n * max(meas[g["label"]]["sec_per_pose"]) for g in geo) / 3600
    side_bytes = int(sum(per_geom_records * n * float(np.mean(meas[g["label"]]["side_b_per_pos"])) for g in geo))
    npz_bytes = int(sum(per_geom_records * n * float(np.mean(meas[g["label"]]["npz_b_per_pos"])) for g in geo))
    # ⛔Two inputs of this generator are LIVE HOST STATE, and a header built on live state is not reproducible.
    #   The 2026-09-18 cross-check of the four stage-1 packages ran this generator again and got a file that
    #   differed from the installed one in exactly two characters — the sidecar count (85 -> 86, one landed in
    #   between) and the free host RAM (156 -> 152 GB. So both are FROZEN here, at the values measured when the
    #   package was built, and the live value is compared against the frozen one and reported, never written.
    free = FROZEN["free_bytes"]
    free_live = shutil.disk_usage("/workspace").free

    # all stored sidecars: bytes per returned path, and the largest provenance ever written
    bpp, max_pos = [], 0
    n_prov = 0
    for pv in sorted(glob.glob(f"{ROOT}/outputs/path_provenance/*_prov.npz")):
        sh = f"{ROOT}/outputs/elev_sweep_shards/" + os.path.basename(pv).replace("_prov.npz", ".npz")
        if not os.path.exists(sh):
            continue
        z = np.load(sh)
        npos = len(z["idx"])
        max_pos = max(max_pos, npos)
        bpp.append(os.path.getsize(pv) / npos / float(np.median(np.asarray(z["nret"]))))
        n_prov += 1
    n_prov_live, bpp_live = n_prov, list(bpp)
    # frozen, for the same reason as `free`: a sidecar landing from a running queue must not change this file.
    n_prov = FROZEN["n_prov_files"]
    bpp = [FROZEN["bpp_min"], FROZEN["bpp_max"]]
    if (n_prov_live, round(min(bpp_live), 2), round(max(bpp_live), 2)) != \
            (n_prov, round(bpp[0], 2), round(bpp[1], 2)):
        sys.stderr.write(
            "note: the sidecar store has moved since this package was frozen — "
            f"{n_prov_live} sidecars now ({n_prov} frozen), "
            f"{min(bpp_live):.2f}-{max(bpp_live):.2f} B/path now "
            f"({bpp[0]:.2f}-{bpp[1]:.2f} frozen). The file is unchanged by design; "
            "re-freeze FROZEN only on purpose.\n")

    # the brief's own example, re-measured
    ex = (f"{ROOT}/outputs/path_provenance/sionna_p{SPP}_sw{SW}_r30_n4096_envoutdoor01_ground_alt4.11"
          f"_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_ant{ANT}_rt210_d3_el-5_00_prov.npz")
    exz = np.load(ex.replace("/path_provenance/", "/elev_sweep_shards/").replace("_prov.npz", ".npz"))
    ex_pos = len(exz["idx"])
    ex_nret = float(np.median(np.asarray(exz["nret"])))
    ex_bpos = os.path.getsize(ex) / ex_pos

    # raw (uncompressed) footprint of the heaviest geometry here
    worst = max(geo, key=lambda g: max(meas[g["label"]]["side_b_per_pos"]))
    wpv = f"{ROOT}/outputs/path_provenance/" + meas[worst["label"]]["side_files"][-1]
    wz = np.load(wpv, allow_pickle=True)
    raw = sum(wz[k].nbytes for k in wz.files)
    raw_per_pos = raw / len(wz["pose"])

    # the one number this file borrows from an earlier reading, taken from the ledger, not from the brief
    ro = json.load(open(f"{ROOT}/outputs/readout_0918.json"))["gates"]["0961"]["T1_T2"]
    above_nyq_pct = 100.0 * float(ro["above_nyq_share"])
    above_nyq_cell = ro["cells"]["base"]
    above_nyq_verdict = ro["T2_verdict"]

    mem_avail_live = 0.0
    for ln in open("/proc/meminfo"):
        if ln.startswith("MemAvailable:"):
            mem_avail_live = float(ln.split()[1]) / 1e6
    mem_avail = FROZEN["mem_avail_gb"]                      # frozen: see the note beside `free` above
    if abs(mem_avail_live - mem_avail) > 1.0 or free_live != free:
        sys.stderr.write(
            f"note: host state has moved — free {free_live/1e9:.0f} GB now ({free/1e9:.0f} frozen), "
            f"MemAvailable {mem_avail_live:.0f} GB now ({mem_avail:.0f} frozen).\n")

    # What rotor prior art the PathSolver arm already has, and at which settings.
    shard_names = os.listdir(f"{ROOT}/outputs/elev_sweep_shards")
    rot_sionna = sorted({re.sub(r"_\d\d\.npz$", "", p) for p in shard_names
                         if "_rot" in p and p.startswith("sionna")})
    rot_ours = sorted({re.sub(r"_\d\d\.npz$", "", p) for p in shard_names
                       if "_rot" in p and p.startswith("ours")})
    presets_seen = sorted({re.search(r"_rot([a-z_0-9]+?)(s\d+)?_mfix", p).group(1)
                           for p in rot_sionna if re.search(r"_rot([a-z_0-9]+?)(s\d+)?_mfix", p)})
    els_seen = sorted({re.search(r"_el([-+][0-9.]+)$", p).group(1) for p in rot_sionna
                       if re.search(r"_el([-+][0-9.]+)$", p)}, key=float)
    at_production = [p for p in rot_sionna
                     if "rt210" in p and f"ant{ANT}" in p and f"shell{SHELL_MM:g}mm" in p]
    if at_production:
        raise SystemExit("⛔ PathSolver rotor shards at the production settings already exist "
                         f"({len(at_production)}) — the header claim is stale: {at_production[:3]}")
    prior = dict(n_sionna=len(rot_sionna), n_ours=len(rot_ours), presets=presets_seen,
                 els=els_seen, with_rt210=len([p for p in rot_sionna if "rt210" in p]),
                 with_ant=len([p for p in rot_sionna if "ant" in p]),
                 with_slab=len([p for p in rot_sionna if "shell" in p]),
                 with_prf=len([p for p in rot_sionna if "_prf" in p]),
                 ranges=sorted({re.search(r"_r([0-9.]+)_n", p).group(1) for p in rot_sionna
                                if re.search(r"_r([0-9.]+)_n", p)}))

    nrets = [float(np.median(meas[g["label"]]["nret_med"])) for g in geo]
    totals = dict(h_min=h_min, h_med=h_med, h_max=h_max,
                  per_line_min_h=min(min(meas[g["label"]]["sec_per_pose"]) for g in geo) * (n // NSHARDS) / 3600,
                  per_line_max_h=max(max(meas[g["label"]]["sec_per_pose"]) for g in geo) * (n // NSHARDS) / 3600,
                  side_bytes=side_bytes, side_gb=side_bytes / 1e9, npz_gb=npz_bytes / 1e9,
                  free_gb=free / 1e9, free_gib=free / 2**30, pct_free=100.0 * side_bytes / free,
                  n_prov_files=n_prov, bpp_min=min(bpp), bpp_max=max(bpp),
                  example_b_per_pos=ex_bpos, example_nret=ex_nret, example_b_per_path=ex_bpos / ex_nret,
                  raw_kb_per_pos=raw_per_pos / 1e3,
                  raw_hold_mb=raw_per_pos * (n // NSHARDS) / 1e6,
                  max_prov_positions=max_pos, mem_avail_gb=mem_avail,
                  prior=prior,
                  nret_lo=min(nrets), nret_hi=max(nrets),
                  above_nyq_pct=above_nyq_pct, above_nyq_cell=above_nyq_cell,
                  above_nyq_verdict=above_nyq_verdict)

    # ---- duplicate / neighbour check against every queue file -------------------------------- #
    seen = existing_flag_sets()
    exact = [(ln, seen[frozenset(ln.split())]) for ln in lines if frozenset(ln.split()) in seen]
    near = {}
    mine = [frozenset(ln.split()) for ln in lines]
    for key, where in seen.items():
        for k2 in mine:
            d = len(key ^ k2)
            if 0 < d <= 2:
                near.setdefault(where[0], min(near.get(where[0], 99), d))
    dup = [f"#   Flag sets compared against every --engine line of all {len(glob.glob(f'{ROOT}/runners/jobs_*.txt'))} runners/jobs_*.txt files",
           f"#   ({sum(len(v) for v in seen.values())} lines; commented, doubly-commented and #HOLD / #HOLD-rev1 lines all peeled and",
           f"#   included): {len(exact)} exact duplicates, and {len(lines)} distinct lines inside this file.",
           f"#   Nearest neighbours anywhere, by flag-set difference (<= 2 flags):"]
    if not near:
        dup.append("#     none — every line of this file is at least 3 flags from anything on record.")
    for where, d in sorted(near.items(), key=lambda x: (x[1], x[0]))[:6]:
        loc, txt = where.split("|", 1)
        dup.append(f"#     {d} flags · {loc}")
        dup.append(f"#       {txt[:150]}")
    dup += ["#   Read those neighbours as follows: they differ from a line here only in --n-poses and --dump-paths, so the",
            "#   sweep writes `_n4096` where this file writes `_n8192` and no stored cell is overwritten. ⛔They are NOT a",
            "#   control for this file: a comb contrast at n4096 and one at n8192 use different Doppler bins and are never",
            "#   put side by side (record-length rule above)."]
    if exact:
        raise SystemExit(f"⛔ {len(exact)} lines already exist in a queue file: {exact[:3]}")

    stems = None
    if os.path.exists(STEMS):
        raw_s = json.load(open(STEMS))
        by_geom: dict[str, list[tuple[str, str]]] = {}
        for r in recs:
            for sh in range(NSHARDS):
                ln = line_for(r["g"], r["n"], r["prf"], r["preset"], r["seed"], sh)
                if ln in raw_s["map"]:
                    tag = (f"{r['preset']} seed {r['seed']}" if r["preset"] else "constant-RPM control")
                    by_geom.setdefault(r["g"]["label"], []).append((f"{tag}, shard {sh:02d}",
                                                                   raw_s["map"][ln]))
        stems = dict(when=raw_s["when"], map=raw_s["map"], by_geom=by_geom)

    body = header(p8, geo, recs, meas, rot, stems, "\n".join(dup), totals) + "\n".join(lines) + "\n"
    with open(OUT, "w") as fh:
        fh.write(body)

    print(f"wrote {OUT}")
    print(f"  records {len(recs)} · lines {len(lines)} · shards per record {NSHARDS}")
    print(f"  slot-hours {h_min:.1f} / {h_med:.1f} / {h_max:.1f}")
    print(f"  sidecar {side_bytes/1e9:.2f} GB + shards {npz_bytes/1e9:.2f} GB · free {free/1e9:.0f} GB")
    print(f"  stems embedded: {bool(stems)}")
    for g in geo:
        m = meas[g["label"]]
        print(f"  {g['label']} {g['name']:34s} s/pose {fmt_band(m['sec_per_pose'])} "
              f"sidecar {np.mean(m['side_b_per_pos']):,.0f} B/pos")


if __name__ == "__main__":
    main()
