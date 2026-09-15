#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""isac_plan_corpus_0915.py - what the existing PathSolver shard corpus implies for drone detection and tracking.

Purpose
    Reads the elevation-sweep shard corpus (outputs/elev_sweep_shards, read-only), selects the complete
    production PathSolver cells, and computes the blade-comb contrast, static and varying levels, and the
    derived tables that the ISAC detection+tracking plan report cites: inventory, per-cell rows, iso summary,
    metric-knob sensitivity, repeat-run spread, the ground-added varying floor, the ray-count ladder, dwell
    windows, drone height variants, directional-antenna pairs (with the queued antenna cells read from the
    job files, never executed), clutter-limited margins, the street-canyon solver-build change and a code
    check that every cell is a hovering drone. Also writes a spectra npz next to the JSON.

Run
    CUDA_VISIBLE_DEVICES="" /workspace/.venvs/py312/bin/python benchmark/isac_plan_corpus_0915.py
    Optional: --root DIR (repo root; default = parent of this script's directory),
              --out FILE (default ROOT/outputs/isac_plan_corpus_0915.json; the npz
              isac_plan_corpus_spectra_0915.npz is written in the same directory),
              --core N (the one CPU core to run on; default = lowest core in the current affinity).
    The script pins itself to one core (os.sched_setaffinity) and hides GPUs before importing numpy.

Runtime
    Seconds to a few minutes on one CPU core, depending on the file cache (opens only the production, repeat
    and ray-ladder shards, about 420 files).

Scope
    Simulation / code / bookkeeping checks only; there is no comparison against RF measurements.
    Levels are PathSolver level in dB (arbitrary reference), not RCS. The corpus is a hovering drone at one
    range with no thermal noise, so nothing here is a detection probability or a tracking accuracy.
"""
from __future__ import annotations

import argparse
import os
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = ""
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"


def _cli() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=None, help="repo root (default: parent of the script's directory)")
    ap.add_argument("--out", default=None, help="output JSON (default ROOT/outputs/isac_plan_corpus_0915.json)")
    ap.add_argument("--core", type=int, default=None, help="single CPU core (default: lowest allowed core)")
    return ap.parse_args()


ARGS = _cli()
_AFF = sorted(os.sched_getaffinity(0))
CORE = int(ARGS.core) if ARGS.core is not None else _AFF[0]
os.sched_setaffinity(0, {CORE})

import ast                                                              # noqa: E402
import datetime as _dt                                                  # noqa: E402
import hashlib                                                          # noqa: E402
import json                                                             # noqa: E402
import platform                                                         # noqa: E402
import re                                                               # noqa: E402
import shlex                                                            # noqa: E402
import subprocess                                                       # noqa: E402
import time                                                             # noqa: E402
from collections import Counter, defaultdict                            # noqa: E402
from pathlib import Path                                                # noqa: E402

import numpy as np                                                      # noqa: E402

NAME = "isac_plan_corpus_0915"
SCRIPT = Path(__file__).resolve()
ROOT = Path(ARGS.root).resolve() if ARGS.root else SCRIPT.parents[1]
OUT = Path(ARGS.out).resolve() if ARGS.out else ROOT / "outputs" / f"{NAME}.json"
OUT_NPZ = OUT.parent / "isac_plan_corpus_spectra_0915.npz"
sys.path.insert(0, str(ROOT / "src"))
import arm_grammar as AG                                                # noqa: E402

T0 = time.time()
STARTED = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# --------------------------------------------------------------------------------------------------
# Configuration inputs (not results). Every one is copied into _meta.assumptions.
# --------------------------------------------------------------------------------------------------
SHARD_DIR_REL = "outputs/elev_sweep_shards"
PROD = dict(engine="sionna", spp="4000000000", switches="R0D0E0F1", range_m="15", n_poses="8192",
            mesh_fix="batteryi5", blade_law="perairframe")
PROD_ORDER = ("engine", "spp", "switches", "range_m", "n_poses", "mesh_fix", "blade_law")
ALLOWED_AXES = ("env", "max_depth", "solver_build", "ant", "aim", "env_alt", "env_scat", "rep")
N_HARM = 12
HALF_WIDTH_BINS = 2
EL_WINDOW_DEG = (-0.15, 0.05)            # inclusive; the repo gate on el-0 level citations (task input)
EXCLUDED_ENV = "sionna-munich"           # repo rule: munich is not used as a result (task input)
SCENE_OF_ENV = {None: "free_sky", "outdoor01_bldg": "outdoor01_bldg", "outdoor01_ground": "outdoor01_ground",
                "outdoor01": "outdoor01", "sionna-simple_street_canyon": "street_canyon",
                "sionna-munich": "munich"}
SCENE_ORDER = ("free_sky", "outdoor01_bldg", "outdoor01_ground", "outdoor01", "street_canyon", "munich")
OUR_MESH_SCENES = ("outdoor01_bldg", "outdoor01_ground", "outdoor01")
GROUND_LIKE = ("outdoor01_ground", "outdoor01", "street_canyon")
ANT_BASE = "tr38901"
VARIANTS = {
    "hann": dict(win="hann"),
    "hw1": dict(hw=1),
    "hw3": dict(hw=3),
    "harm6": dict(nharm=6),
    "harm24": dict(nharm=24),
    "bandlimited_floor": dict(band_limit=True),
}
DWELL_WINDOWS = (512, 1024, 2048, 4096, 8192)
DWELL_ELS = (-15.0, -60.0)
DWELL_SERIES = (("free_sky", "iso"), ("outdoor01_ground", "iso"), ("outdoor01_ground", ANT_BASE))
PREFERRED_BUILD_DEPTH = ("2.1.0", 2)
RAY_LADDER_CELL = dict(scene="outdoor01_ground", build="2.0.1", depth=2, el_deg=-60.0)
WHITE_SEED = 20260915
TOP_SHARE_FRACTION_DIV = 100             # top 1 % of non-DC bins
JOB_FILES = ("runners/jobs_0938_antenna.txt", "runners/jobs_0940_antenna.txt", "runners/jobs_0941_buffer.txt")

#: External specification values (context only; the computation uses the repo code values quoted below).
SOURCES = [
    dict(id="3gpp_tr38901_element",
         url="https://portal.3gpp.org/desktopmodules/Specifications/SpecificationDetails.aspx?specificationId=3173",
         document="3GPP TR 38.901 V17.0.0 (2022-03), Study on channel model for frequencies from 0.5 to 100 GHz",
         locator="Section 7.3, Table 7.3-1 (radiation power pattern of a single antenna element)",
         values=dict(half_power_beamwidth_deg=65.0, side_lobe_and_front_back_limit_db=30.0,
                     max_directional_gain_dbi=8.0),
         note="Origin of the element pattern that the corpus uses as a stand-in directional antenna. "
              "Not used in any computation here: the default attenuation limit and peak gain are read from "
              "benchmark/report15_probe.py at run time (repo_quotes ant_cap_default, ant_peak_gain)."),
]

#: Repo facts quoted from text files. Each is verified at run time (path, line, quote, sha256).
REPO_QUOTES = [
    dict(id="ffl_source_json", path="benchmark/clutter_parts_ladder_0824.py", line=71,
         quote='_TJ = json.load(open(os.path.join(ROOT, "outputs", "switch_grid.json")))["_meta"]'),
    dict(id="ffl_constant", path="benchmark/clutter_parts_ladder_0824.py", line=73,
         quote='FFL = float(_TJ["f_flash_hz"])'),
    dict(id="shard_name_pattern", path="benchmark/elevation_sweep_md.py", line=1928,
         quote=r'_m = re.search(r"^(.*)_el([+-]\d+(?:\.\d+)?)_\d+\.npz$", _b)'),
    dict(id="shard_meta_layout", path="benchmark/elevation_sweep_md.py", line=1199,
         quote="meta=np.array([el, a.shard, a.nshards, n, prf,"),
    dict(id="shard_cfg_layout", path="benchmark/elevation_sweep_md.py", line=1208,
         quote="cfg=np.array([rng_m, mdep, spp,"),
    dict(id="ant_pattern_meta", path="benchmark/elevation_sweep_md.py", line=1196,
         quote='ant_pattern=np.array(tagant.split("_aim")[0][4:]),'),
    dict(id="build_baseline", path="benchmark/elevation_sweep_md.py", line=1318,
         quote='BUILD_BASELINE = "sionna=2.0.1 sionna-rt=2.0.1 mitsuba=3.8.0 drjit=1.3.1"'),
    dict(id="build_baseline_rt", path="benchmark/elevation_sweep_md.py", line=1319,
         quote='BUILD_BASELINE_RT = "2.0.1"'),
    dict(id="path_limit_default", path="benchmark/report15_probe.py", line=104,
         quote='MAX_PATHS = int(os.environ.get("SIONNA2_MAX_PATHS", 2_000_000))'),
    dict(id="path_limit_fraction", path="benchmark/elevation_sweep_md.py", line=1185,
         quote="_ntr = int(np.count_nonzero(np.asarray(nret) >= 0.99 * RP.MAX_PATHS))"),
    dict(id="ant_cap_default", path="benchmark/report15_probe.py", line=151,
         quote="_TR38901_STOCK_CAP = 30.0"),
    dict(id="ant_peak_gain", path="benchmark/report15_probe.py", line=179,
         quote="g_e_max = 8."),
    dict(id="radar_height_note", path="benchmark/report15_probe.py", line=143,
         quote="radar sits 20 + 15*sin(el) m above the ground"),
    dict(id="default_env_alt", path="benchmark/elevation_sweep_md.py", line=123,
         quote='dir=f"{ROOT}/assets/meshes/outdoor01", alt_m=20.0,'),
    dict(id="builtin_scene_alt", path="benchmark/elevation_sweep_md.py", line=119,
         quote="ENV_BUILTIN_ALT = 25.0"),
    dict(id="builtin_scene_centre", path="benchmark/elevation_sweep_md.py", line=171,
         quote="ctr = (0.0, 0.0, float(ENV_BUILTIN_ALT))"),
    dict(id="hover_centre", path="benchmark/elevation_sweep_md.py", line=1013,
         quote="_ctr = (0.0, 0.0, 0.0)"),
    dict(id="hover_place_call", path="benchmark/elevation_sweep_md.py", line=1050,
         quote="RP.place(sc, center=_ctr, az=az, el=el, rng=rng_m, baseline=0.0,"),
    dict(id="rotor_phase_time_axis", path="benchmark/elevation_sweep_md.py", line=411,
         quote="ph = rotor_phases(np.arange(n) / prf, rpms, fp.dirs)"),
    dict(id="rotor_rpm_source", path="benchmark/elevation_sweep_md.py", line=378,
         quote='rpms = np.asarray(TJ["rpm_per_rotor"], float)'),
    dict(id="solver_seed", path="benchmark/elevation_sweep_md.py", line=1057,
         quote="samples_per_src=spp, max_num_paths_per_src=RP.MAX_PATHS, seed=1)"),
    dict(id="jobs_0938_header", path="runners/jobs_0938_antenna.txt", line=1,
         quote="# SUPERSEDED 2026-09-15 by runners/jobs_0940_antenna.txt before any line was launched"),
    dict(id="jobs_0940_header", path="runners/jobs_0940_antenna.txt", line=1,
         quote="supersedes runners/jobs_0938_antenna.txt"),
]

# --------------------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------------------
_HASHES: dict[str, str] = {}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def track(rel: str) -> str:
    """sha256 of a repo file a value depends on; recorded in _meta.source_hashes."""
    if rel not in _HASHES:
        _HASHES[rel] = sha256_file(ROOT / rel)
    return _HASHES[rel]


def verify_quotes() -> dict:
    out = {}
    for q in REPO_QUOTES:
        p = ROOT / q["path"]
        lines = p.read_text(encoding="utf-8").splitlines()
        ok_line = 0 < q["line"] <= len(lines) and q["quote"] in lines[q["line"] - 1]
        found = q["line"] if ok_line else next((i + 1 for i, s in enumerate(lines) if q["quote"] in s), None)
        if found is None:
            raise SystemExit(f"repo quote not found: {q['id']} {q['path']}: {q['quote']!r}")
        out[q["id"]] = dict(path=q["path"], line=int(found), table_line=q["line"], line_matches_table=bool(ok_line),
                            quote=q["quote"], full_line=lines[found - 1].strip(), sha256=track(q["path"]))
    return out


def num_in(text: str) -> float:
    m = re.findall(r"-?\d[\d_]*(?:\.\d*)?", text)
    if len(m) != 1:
        raise SystemExit(f"expected exactly one number in quote {text!r}, got {m}")
    return float(m[0].replace("_", ""))


def db(x: float) -> float:
    return float(10.0 * np.log10(x))


def fin(x):
    """JSON-safe value: numpy scalars to python, non-finite floats to None."""
    if isinstance(x, dict):
        return {str(k): fin(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [fin(v) for v in x]
    if isinstance(x, (np.bool_,)):
        return bool(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (float, np.floating)):
        v = float(x)
        return v if np.isfinite(v) else None
    return x


def rnd(x, nd=3):
    return None if x is None else round(float(x), nd)


LEDGER: dict = {}
SHARD_HASHES: dict = {}                   # shard file name -> sha256, every shard opened so far


def write_ledger(status: str, section: str) -> None:
    LEDGER["_meta"]["status"] = status
    LEDGER["_meta"]["last_section"] = section
    LEDGER["_meta"]["finished_utc"] = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    LEDGER["_meta"]["wall_time_s"] = round(time.time() - T0, 1)
    LEDGER["_meta"]["source_hashes"] = [dict(path=k, sha256=v) for k, v in sorted(_HASHES.items())]
    if SHARD_HASHES:
        digest = hashlib.sha256("".join(f"{k}{v}" for k, v in sorted(SHARD_HASHES.items())).encode()).hexdigest()
        LEDGER["_meta"]["source_hashes"].append(dict(
            path=f"{SHARD_DIR_REL} ({len(SHARD_HASHES)} shard files read)",
            sha256=digest,
            note=("sha256 over the sorted concatenation of file name + sha256(file) of every shard opened up to "
                  "this checkpoint (production, repeat and ray-ladder cells); recomputed at every write")))
        inv = LEDGER.get("inventory")
        if inv:
            inv["n_shard_files_read"] = len(SHARD_HASHES)
            inv["shard_files_digest"] = digest
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(fin(LEDGER), ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, OUT)
    print(f"[{time.time() - T0:7.1f}s] checkpoint {section} -> {OUT}", flush=True)


def git_head() -> str | None:
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(ROOT), capture_output=True, text=True, timeout=30)
        return r.stdout.strip() or None
    except Exception:                                                   # noqa: BLE001
        return None


def extract_function(path: Path, name: str):
    """Compile one top-level function from a repo file without importing that module."""
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    ns = {"np": np, "os": os}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(path), "exec"), ns)   # noqa: S102
    seg = ast.get_source_segment(src, fn) or ""
    return ns[name], dict(path=str(path.relative_to(ROOT)), function=name, first_line=fn.lineno,
                          last_line=fn.end_lineno, source_sha256=hashlib.sha256(seg.encode()).hexdigest())


# --------------------------------------------------------------------------------------------------
# Spectral metrics
# --------------------------------------------------------------------------------------------------
_MASKS: dict = {}


def masks(n: int, prf: float, ffl: float, hw: int = HALF_WIDTH_BINS, nharm: int = N_HARM,
          band_limit: bool = False):
    key = (n, prf, ffl, hw, nharm, band_limit)
    if key not in _MASKS:
        df = prf / n
        comb = np.zeros(n, bool)
        for h in range(1, nharm + 1):
            c = int(round(h * ffl / df))
            for s in (1, -1):
                for o in range(-hw, hw + 1):
                    comb[(s * c + o) % n] = True
        non = ~comb
        non[0] = False
        if band_limit:
            non &= np.abs(np.fft.fftfreq(n, 1.0 / prf)) <= (nharm + 0.5) * ffl
        _MASKS[key] = (comb, non)
    return _MASKS[key]


def power_spectrum(E: np.ndarray, win: str | None = None) -> np.ndarray:
    """|FFT(w*(E-mean E))|^2 / n^2 (rectangular: sums to the varying power)."""
    n = E.size
    ac = E - E.mean()
    if win == "hann":
        ac = ac * np.hanning(n)
    return np.abs(np.fft.fft(ac)) ** 2 / float(n) ** 2


def contrast_db(E: np.ndarray, prf: float, ffl: float, hw: int = HALF_WIDTH_BINS, nharm: int = N_HARM,
                win: str | None = None, band_limit: bool = False) -> float:
    P = power_spectrum(E, win)
    comb, non = masks(E.size, prf, ffl, hw, nharm, band_limit)
    return db(P[comb].mean() / P[non].mean())


def levels(E: np.ndarray, prf: float, ffl: float) -> dict:
    mu = E.mean()
    var = float(np.mean(np.abs(E - mu) ** 2))
    P = power_spectrum(E)
    comb, non = masks(E.size, prf, ffl)
    return dict(static_db=db(abs(mu) ** 2), varying_db=db(var), sv_db=db(abs(mu) ** 2) - db(var),
                total_db=db(float(np.mean(np.abs(E) ** 2))), comb_contrast_db=db(P[comb].mean() / P[non].mean()),
                comb_bin_mean_db=db(P[comb].mean()), noncomb_bin_mean_db=db(P[non].mean()))


# --------------------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------------------
def main() -> None:
    LEDGER["_meta"] = dict(
        generator=f"benchmark/{NAME}.py",
        command=f'CUDA_VISIBLE_DEVICES="" /workspace/.venvs/py312/bin/python benchmark/{NAME}.py',
        argv=sys.argv[1:], core=CORE, started_utc=STARTED, git_head=git_head(),
        package_versions=dict(python=platform.python_version(), numpy=np.__version__),
        scope=("Simulation / code / bookkeeping checks on the existing PathSolver shard corpus. No comparison "
               "against RF measurements. Levels are PathSolver level in dB (arbitrary reference), not RCS. "
               "Hovering drone, one range, no thermal noise, single-antenna sum field: no detection "
               "probability, range, angle or tracking accuracy can be computed from it."),
        seeds=dict(white_reference_seed=WHITE_SEED,
                   white_reference_seed_rule="np.random.default_rng([WHITE_SEED, depth, round(100*el_deg)+100000, "
                                             "0 for 2.0.1 / 1 for 2.1.0])",
                   solver_seed_quote="repo_quotes.solver_seed"),
    )
    LEDGER["sources"] = SOURCES

    # ---------------------------------------------------------------- section 1: repo facts
    quotes = verify_quotes()
    LEDGER["repo_quotes"] = list(quotes.values())
    switch_grid = json.loads((ROOT / "outputs/switch_grid.json").read_text(encoding="utf-8"))
    track("outputs/switch_grid.json")
    ffl_key = re.search(r'_TJ\["(\w+)"\]', quotes["ffl_constant"]["full_line"]).group(1)
    FFL = float(switch_grid["_meta"][ffl_key])
    MAX_PATHS_DEFAULT = int(num_in(quotes["path_limit_default"]["full_line"].split(",", 1)[1]))
    LIMIT_FRAC = num_in(quotes["path_limit_fraction"]["full_line"].split(">=", 1)[1].split("*")[0])
    CAP_DEFAULT = num_in(quotes["ant_cap_default"]["full_line"].split("=", 1)[1])
    G_E_MAX = num_in(quotes["ant_peak_gain"]["full_line"].split("=", 1)[1])
    ALT_DEFAULT = num_in(quotes["default_env_alt"]["full_line"].split("alt_m=", 1)[1])
    ALT_BUILTIN = num_in(quotes["builtin_scene_alt"]["full_line"].split("=", 1)[1])
    shard_pat_text = re.search(r're\.search\(r"(.+?)", _b\)', quotes["shard_name_pattern"]["full_line"]).group(1)
    SHARD_PAT = re.compile(shard_pat_text)
    SHARD_NO = re.compile(r"_(\d+)\.npz$")
    baseline_build_str = re.search(r'"(.+)"', quotes["build_baseline"]["full_line"]).group(1)
    baseline_rt = re.search(r'"(.+)"', quotes["build_baseline_rt"]["full_line"]).group(1)
    registry = json.loads((ROOT / "runners/SOLVER_BUILDS.json").read_text(encoding="utf-8"))
    track("runners/SOLVER_BUILDS.json")
    BUILD_STRING = {None: baseline_build_str}
    BUILD_LABEL = {None: baseline_rt}
    for tag, s in registry["builds"].items():
        t = tag[len("_rt"):]
        BUILD_STRING[t] = s
        BUILD_LABEL[t] = re.search(r"sionna-rt=(\S+)", s).group(1)
    track("src/arm_grammar.py")
    track("benchmark/elevation_sweep_md.py")
    shard_done, shard_done_info = extract_function(ROOT / "benchmark/elevation_sweep_md.py", "shard_done")

    LEDGER["constants"] = dict(
        ffl_hz=FFL, ffl_source=dict(json="outputs/switch_grid.json", key=f"_meta.{ffl_key}",
                                    used_by="benchmark/clutter_parts_ladder_0824.py (repo_quotes ffl_constant)"),
        path_limit_default=MAX_PATHS_DEFAULT, path_limit_fraction=LIMIT_FRAC,
        ant_cap_default_db=CAP_DEFAULT, ant_peak_gain_dbi_in_code=G_E_MAX,
        default_env_alt_m_outdoor01_scenes=ALT_DEFAULT, builtin_scene_drone_offset_m=ALT_BUILTIN,
        build_labels=[dict(name_tag=("" if k is None else f"_rt{k}"), build=BUILD_LABEL[k],
                           shard_solver_build_string=BUILD_STRING[k]) for k in BUILD_STRING],
        shard_integrity_function=shard_done_info,
        n_harmonics=N_HARM, half_width_bins=HALF_WIDTH_BINS,
    )
    LEDGER["_meta"]["definitions"] = {
        "comb_contrast_db": ("Merged E over all poses (shards scattered back by idx, never concatenated); "
                             "P = |FFT(E - mean E)|^2 / n^2 with a rectangular window; PRF from shard meta[4]; "
                             f"comb bins = harmonics 1..{N_HARM} of FFL at +/- frequency, +/-{HALF_WIDTH_BINS} "
                             "bins each (bin index round(h*FFL/df)); non-comb bins = all other bins except DC; "
                             "contrast = 10log10(mean comb-bin power / mean non-comb-bin power)."),
        "static_db": "10log10(|mean E|^2), PathSolver level in dB (arbitrary reference).",
        "varying_db": "10log10(mean |E - mean E|^2), same reference.",
        "sv_db": "static_db - varying_db.",
        "total_db": "10log10(mean |E|^2).",
        "comb_bin_mean_db / noncomb_bin_mean_db": "10log10 of the mean of P over comb / non-comb bins (P as above).",
        "variant hann": "Hann window (np.hanning(n)) applied to E - mean E before the FFT; masks unchanged.",
        "variant hw1 / hw3": "comb half-width +/-1 or +/-3 bins instead of +/-2.",
        "variant harm6 / harm24": "harmonics 1..6 or 1..24 instead of 1..12.",
        "variant bandlimited_floor": (f"non-comb bins restricted to |f| <= ({N_HARM} + 0.5) * FFL; comb mask unchanged."),
        "knob delta": "variant contrast minus primary contrast for the same row, over every row.",
        "ground_like_max_contrast_db": ("max over the primary metric and all six variants, over every iso row "
                                        "(all drone heights) in outdoor01_ground, outdoor01 and street_canyon."),
        "ground_like_max_contrast_default_height_db": ("the same max restricted to iso rows at the default drone "
                                                       "height (no env_alt tag)."),
        "free_sky_min_contrast_db": "min over the primary metric and all six variants, over iso free_sky rows.",
        "repeat rel_rms_change": "sqrt(mean|E_rep - E_base|^2 / mean|E_base - mean E_base|^2), same poses.",
        "repeat contrast_spread_db": "max - min primary contrast among the base run and its rep runs.",
        "ground_floor field": "D = E(outdoor01_ground, iso) - E(free_sky, iso), same arm otherwise, same poses.",
        "flatness": "spectral flatness of D - mean D over non-DC bins: exp(mean log P) / mean P.",
        "top1pct_share": "share of the non-DC power held by the largest 1 % of non-DC bins (n_bins // 100).",
        "white_ref": "the same two statistics for one complex Gaussian draw of the same length (seed rule in _meta.seeds).",
        "added_varying_over_free_sky_db": "10log10(mean|D - mean D|^2 / mean|E_free - mean E_free|^2).",
        "dwell window": "the first N poses in time order (pose index = time index), same metric with df = PRF/N.",
        "comb_bins_fraction": "fraction of all bins that the comb mask covers at that window length.",
        "antenna deltas": ("ant cell minus its iso control (same scene, build, depth, el, env_alt): total, static, "
                           "varying levels; noncomb_delta_db / comb_delta_db = ratio of mean non-comb / comb bin power."),
        "ant_minus_free_sky": ("scene_total_minus_free_sky_*_db = total_db(scene cell) - total_db(free_sky cell) "
                               "for the same antenna setting, build, depth and el."),
        "clutter_limited": ("10log10(mean comb-bin power of the free_sky cell / mean non-comb-bin power of the scene "
                            "cell), same antenna setting, build, depth, el and n."),
        "radar_height_above_ground_m": ("env_alt_m + range_m*sin(el) for outdoor01* scenes (repo_quotes "
                                        "radar_height_note); null for free_sky and street_canyon."),
        "env_alt_m": ("_alt tag value if present; else outdoor01* default alt_m (repo_quotes default_env_alt); "
                      "street_canyon: ENV_BUILTIN_ALT, the drone offset above the scene origin (repo_quotes "
                      "builtin_scene_alt), not a height above local ground; free_sky: null."),
        "n_poses_at_path_limit": (f"poses with nret >= {LIMIT_FRAC} x path limit (n_trunc[1] when stored, else the "
                                  "default MAX_PATHS); null when the shard has no nret."),
        "queued cell status": ("landed_complete = a complete production cell with the same parsed fields exists at the "
                               "queue build (the build tag of the landed antenna cells); landed_incomplete = shards "
                               "exist but the cell is incomplete; not_landed = no shard. only_in_superseded_files = "
                               "every job line for the cell sits in a file whose first line says SUPERSEDED."),
        "spectra npz psd_db": ("10log10 of P = |FFT(E - mean E)|^2 / n^2 per bin, rectangular window, fftshifted, "
                               "one common absolute reference for all series (the PathSolver arbitrary level "
                               "reference; the bins of one series sum to its varying power). DC bin stored as NaN."),
    }
    LEDGER["_meta"]["assumptions"] = [
        dict(id="production_filter", value=PROD, flag="configuration input",
             note="Production tags; other tags allowed only on the axes " + ", ".join(ALLOWED_AXES) + "."),
        dict(id="el_window_deg", value=list(EL_WINDOW_DEG), flag="configuration input (task gate)",
             note="Inclusive window excluded from rows: repo gate on el 0 level citations (impulsive poses)."),
        dict(id="excluded_env", value=EXCLUDED_ENV, flag="configuration input (task rule)",
             note="munich is not used as a result."),
        dict(id="env_scat_excluded", value=True, flag="configuration input (task rule)",
             note="Roughness (env_scat) cells are folded as an axis; path-limit counts are recorded in the exclusion entry."),
        dict(id="metric", value=dict(n_harm=N_HARM, half_width_bins=HALF_WIDTH_BINS), flag="configuration input",
             note="Must match the earlier corpus investigation."),
        dict(id="dwell", value=dict(windows=list(DWELL_WINDOWS), els=list(DWELL_ELS),
                                    preferred_build_depth=list(PREFERRED_BUILD_DEPTH)), flag="configuration input"),
        dict(id="ray_ladder_cell", value=RAY_LADDER_CELL, flag="configuration input"),
        dict(id="white_seed", value=WHITE_SEED, flag="configuration input"),
        dict(id="build_from_name", value="no _rt tag = build of BUILD_BASELINE_RT; _rt<tag> = sionna-rt version in "
                                          "runners/SOLVER_BUILDS.json", flag="repo rule, read at run time",
             note="Shard solver_build strings are checked against it when recorded; old shards do not record it."),
        dict(id="queued_arm_reconstruction", flag="assumption",
             value="queued job lines are turned into arm names with the production mesh tags and the solver-build "
                   "tag shared by the landed antenna cells",
             note="The builder adds those tags at run time from its defaults; matching to landed cells uses parsed "
                  "fields (scene, el, depth, spp, n, range, switches, antenna, cap, aim, env_alt), not the name."),
        dict(id="street_canyon_env_alt", flag="assumption",
             value="ENV_BUILTIN_ALT is reported as env_alt_m for street_canyon",
             note="It is the drone offset above the scene origin; the local ground height under the drone is not read."),
    ]
    write_ledger("partial", "repo_facts")

    # ---------------------------------------------------------------- section 2: inventory + loading
    shard_dir = ROOT / SHARD_DIR_REL
    names = sorted(os.listdir(shard_dir))
    cells: dict = defaultdict(dict)
    n_nonmatch = 0
    for b in names:
        m = SHARD_PAT.search(b)
        mn = SHARD_NO.search(b)
        if not m or not mn:
            n_nonmatch += 1
            continue
        cells[(m.group(1), float(m.group(2)))][int(mn.group(1))] = shard_dir / b
    parsed: dict = {}
    parse_fail = []
    for (arm, el) in cells:
        if arm in parsed:
            continue
        try:
            parsed[arm] = AG.parse(arm, strict=True)
        except AG.ArmNameError as e:
            parse_fail.append(dict(arm=arm, error=str(e)[:200]))
    cell_keys = [k for k in cells if k[0] in parsed]
    n_ps = sum(1 for k in cell_keys if parsed[k[0]]["engine"] == "sionna")

    steps = [dict(step="all cells (arm, el) from file names", n_cells_remaining=len(cells)),
             dict(step="arm name parses with arm_grammar.parse(strict=True)", n_cells_remaining=len(cell_keys))]
    cur = cell_keys
    for k in PROD_ORDER:
        cur = [c for c in cur if parsed[c[0]].get(k) == PROD[k]]
        steps.append(dict(step=f"{k} == {PROD[k]}", n_cells_remaining=len(cur)))
    other_tags = Counter()
    cand = []
    for c in cur:
        extra = sorted(t for t in parsed[c[0]] if t not in PROD and t not in ALLOWED_AXES and not t.startswith("_"))
        if extra:
            other_tags[",".join(extra)] += 1
        else:
            cand.append(c)
    steps.append(dict(step="no tags outside the allowed axes", n_cells_remaining=len(cand)))

    E_of: dict = {}
    info_of: dict = {}
    shard_hashes = SHARD_HASHES

    def load_cell(key) -> tuple[bool, str | None]:
        """Complete = all shards 0..nshards-1 present, all pass shard_done, one meta layout, every pose covered
        exactly once (which rules out mixed generations), metadata consistent with the arm name."""
        if key in info_of:
            return info_of[key]["complete"], info_of[key].get("reason")
        arm, el = key
        f = parsed[arm]
        files = cells[key]
        nos = sorted(files)

        def fail(reason):
            info_of[key] = dict(complete=False, reason=reason, shards_present=nos)
            return False, reason

        for no in nos:
            if not shard_done(str(files[no])):
                return fail(f"shard {no:02d} fails shard_done")
        idxs, Es, metas, cfgs, nrets, caps, builds, antp, antc, aimo = [], [], [], [], [], [], [], [], [], []
        for no in nos:
            with np.load(files[no]) as z:
                zf = set(z.files)
                idxs.append(z["idx"].astype(np.int64))
                Es.append(z["E"])
                metas.append(np.asarray(z["meta"], float).ravel())
                cfgs.append(np.asarray(z["cfg"], float).ravel() if "cfg" in zf else None)
                nrets.append(np.asarray(z["nret"]) if "nret" in zf else None)
                nt = np.asarray(z["n_trunc"]).ravel() if "n_trunc" in zf else None
                caps.append(int(nt[1]) if nt is not None and nt.size > 1 else None)
                builds.append(str(z["solver_build"]) if "solver_build" in zf else None)
                antp.append(str(z["ant_pattern"]) if "ant_pattern" in zf else None)
                antc.append(float(np.asarray(z["ant_cap_db"]).ravel()[0]) if "ant_cap_db" in zf else None)
                aimo.append(float(np.asarray(z["aim_offset_deg"]).ravel()[0]) if "aim_offset_deg" in zf else None)
            shard_hashes[files[no].name] = sha256_file(files[no])
        nsh = {int(m[2]) for m in metas}
        if len(nsh) != 1:
            return fail(f"shards disagree on nshards {sorted(nsh)}")
        nsh = nsh.pop()
        if nos != list(range(nsh)):
            return fail(f"shards present {nos} of nshards {nsh}")
        n0 = {int(m[3]) for m in metas}
        if n0 != {int(f["n_poses"])}:
            return fail(f"meta n_poses {sorted(n0)} != name {f['n_poses']}")
        n0 = n0.pop()
        prf = {float(m[4]) for m in metas}
        if len(prf) != 1:
            return fail(f"shards disagree on PRF {sorted(prf)}")
        prf = prf.pop()
        if any(abs(float(m[0]) - el) > 1e-9 for m in metas):
            return fail("meta el differs from file name")
        if any(m.size > 6 and int(m[6]) != int(f["spp"]) for m in metas):
            return fail("meta spp differs from name")
        sw = f.get("switches")
        for c in cfgs:
            if c is None:
                continue
            if abs(c[0] - float(f["range_m"])) > 1e-9 or ("max_depth" in f and int(c[1]) != int(f["max_depth"])) \
                    or int(c[2]) != int(f["spp"]):
                return fail("cfg range/depth/spp differs from name")
            if sw and c.size > 6:
                bits = re.fullmatch(r"R([01])D([01])E([01])F([01])", sw).groups()
                if [int(c[4]), int(c[5]), int(c[6])] != [int(bits[0]), int(bits[1]), int(bits[2])]:
                    return fail("cfg switches differ from name")
        allidx = np.concatenate(idxs)
        cnt = np.bincount(allidx, minlength=n0)
        if cnt.size != n0 or (cnt != 1).any():
            return fail(f"pose coverage not exactly once (missing {int((cnt == 0).sum())}, "
                        f"repeated {int((cnt > 1).sum())})")
        tag = f.get("solver_build")
        if tag not in BUILD_STRING:
            return fail(f"unknown solver build tag {tag!r}")
        rec = [b for b in builds if b is not None]
        if any(b != BUILD_STRING[tag] for b in rec):
            return fail(f"shard solver_build {sorted(set(rec))} != expected {BUILD_STRING[tag]!r}")
        if tag is not None and len(rec) != len(builds):
            return fail("tagged build but shard does not record solver_build")
        ant = f.get("ant")
        if ant is None:
            if any(p is not None for p in antp):
                return fail("iso name but shard records an antenna pattern")
        else:
            cap = CAP_DEFAULT if ant == ANT_BASE else float(ant[len(ANT_BASE) + 1:])
            aim = float(f.get("aim") or 0.0)
            if any(p != ant for p in antp) or any(c is None or abs(c - cap) > 1e-9 for c in antc) \
                    or any(a is None or abs(a - aim) > 1e-9 for a in aimo):
                return fail("antenna metadata in shard differs from name")
        E = np.zeros(n0, complex)
        for ii, ee in zip(idxs, Es):
            E[ii] = ee
        nmax, nat, lim_src = None, None, None
        if all(r is not None for r in nrets):
            nr = np.concatenate(nrets)
            nmax = int(nr.max())
            capv = [c for c in caps if c is not None]
            lim = max(capv) if capv else MAX_PATHS_DEFAULT
            lim_src = "n_trunc[1]" if capv else "MAX_PATHS default"
            nat = int(np.count_nonzero(nr >= LIMIT_FRAC * lim))
        hc = hashlib.sha256()
        for no in nos:
            hc.update(files[no].name.encode())
            hc.update(shard_hashes[files[no].name].encode())
        E_of[key] = E
        info_of[key] = dict(complete=True, prf=prf, n_poses=n0, n_shards=nsh, nret_max=nmax,
                            n_poses_at_path_limit=nat, path_limit_source=lim_src,
                            solver_build_recorded=bool(rec), shards_sha256=hc.hexdigest())
        return True, None

    incomplete = []
    complete = []
    for c in sorted(cand, key=lambda k: (k[0], -k[1])):
        ok, why = load_cell(c)
        if ok:
            complete.append(c)
        else:
            incomplete.append(dict(arm=c[0], el_deg=c[1], reason=why))
    steps.append(dict(step="complete (all shards, shard_done, exactly-once coverage, metadata consistent)",
                      n_cells_remaining=len(complete)))

    def scene_of(f):
        return SCENE_OF_ENV.get(f.get("env"), None)

    excl = defaultdict(list)
    kept = []
    for c in complete:
        f = parsed[c[0]]
        if f.get("env") == EXCLUDED_ENV:
            excl["scene munich (repo rule: not used as a result)"].append(c)
        elif "env_scat" in f:
            excl["env_scat roughness cell (axis folded; path limit)"].append(c)
        elif EL_WINDOW_DEG[0] <= c[1] <= EL_WINDOW_DEG[1]:
            excl[f"el inside {EL_WINDOW_DEG[0]:+g}..{EL_WINDOW_DEG[1]:+g} deg (el 0 gate; impulsive poses)"].append(c)
        elif scene_of(f) is None:
            excl["unknown scene"].append(c)
        else:
            kept.append(c)
    n_excluded = []
    for reason in excl:
        ent = dict(reason=reason, n_cells=len(excl[reason]))
        if reason.startswith("env_scat"):
            at = [info_of[c]["n_poses_at_path_limit"] for c in excl[reason]]
            ent.update(n_poses_at_path_limit_min=min((a for a in at if a is not None), default=None),
                       n_poses_at_path_limit_max=max((a for a in at if a is not None), default=None),
                       nret_max=max((info_of[c]["nret_max"] or 0) for c in excl[reason]))
        if reason.startswith("el inside"):
            ent.update(n_rep_cells=sum(1 for c in excl[reason] if "rep" in parsed[c[0]]))
        n_excluded.append(ent)
    steps.append(dict(step="after exclusions (munich, env_scat, el window)", n_cells_remaining=len(kept)))

    def env_alt_of(f):
        sc = scene_of(f)
        if "env_alt" in f:
            return float(f["env_alt"]), "tag"
        if sc in OUR_MESH_SCENES:
            return ALT_DEFAULT, "default alt_m"
        if sc == "street_canyon":
            return ALT_BUILTIN, "ENV_BUILTIN_ALT (offset above scene origin)"
        return None, None

    def ant_of(f):
        ant = f.get("ant")
        if ant is None:
            return "iso", None, None
        cap = CAP_DEFAULT if ant == ANT_BASE else float(ant[len(ANT_BASE) + 1:])
        return ANT_BASE, cap, float(f.get("aim") or 0.0)

    rows = []
    row_of: dict = {}
    raw_of: dict = {}          # unrounded levels per cell; differences are taken on these, then rounded
    rep_cells = []
    for c in kept:
        f = parsed[c[0]]
        if "rep" in f:
            rep_cells.append(c)
            continue
        inf = info_of[c]
        E = E_of[c]
        lv = levels(E, inf["prf"], FFL)
        ant, cap, aim = ant_of(f)
        alt, alt_src = env_alt_of(f)
        sc = scene_of(f)
        el = c[1]
        r = dict(arm=c[0], scene=sc, build=BUILD_LABEL[f.get("solver_build")],
                 depth=(int(f["max_depth"]) if "max_depth" in f else None), el_deg=el,
                 ant=ant, ant_cap_db=cap, aim_offset_deg=aim, env_alt_m=alt, env_alt_source=alt_src,
                 default_height=("env_alt" not in f),
                 radar_height_above_ground_m=(rnd(alt + float(f["range_m"]) * np.sin(np.radians(el)), 3)
                                              if sc in OUR_MESH_SCENES else None),
                 comb_contrast_db=rnd(lv["comb_contrast_db"]), static_db=rnd(lv["static_db"]),
                 varying_db=rnd(lv["varying_db"]), sv_db=rnd(lv["sv_db"]), total_db=rnd(lv["total_db"]),
                 comb_bin_mean_db=rnd(lv["comb_bin_mean_db"]), noncomb_bin_mean_db=rnd(lv["noncomb_bin_mean_db"]))
        raw = dict(lv)
        for vn, kw in VARIANTS.items():
            raw[f"contrast_{vn}_db"] = contrast_db(E, inf["prf"], FFL, **kw)
            r[f"contrast_{vn}_db"] = rnd(raw[f"contrast_{vn}_db"])
        raw_of[c] = raw
        r.update(n_poses=inf["n_poses"], n_shards=inf["n_shards"], prf_hz=inf["prf"], nret_max=inf["nret_max"],
                 n_poses_at_path_limit=inf["n_poses_at_path_limit"], solver_build_recorded=inf["solver_build_recorded"],
                 shards_sha256=inf["shards_sha256"])
        rows.append(r)
        row_of[c] = r
    order = {s: i for i, s in enumerate(SCENE_ORDER)}
    rows.sort(key=lambda r: (order[r["scene"]], r["build"], r["depth"] or 0, r["ant"], r["ant_cap_db"] or 0,
                             r["aim_offset_deg"] or 0, r["env_alt_m"] or 0, -r["el_deg"]))

    by_scene = defaultdict(list)
    for r in rows:
        if r["ant"] == "iso" and r["default_height"]:
            by_scene[(r["scene"], r["build"], r["depth"])].append(r["el_deg"])
    inventory = dict(
        shard_dir=SHARD_DIR_REL, n_files=len(names), n_file_names_not_matching_pattern=n_nonmatch,
        n_cells=len(cells), n_arm_parse_failures=len(parse_fail), arm_parse_failures=parse_fail[:20],
        n_pathsolver_cells=n_ps, filter_steps=steps,
        non_production_tag_sets=[dict(tags=k, n_cells=v) for k, v in sorted(other_tags.items())],
        n_production_candidates=len(cand), n_production_complete=len(complete),
        n_production_incomplete=len(incomplete), incomplete=incomplete,
        n_excluded=n_excluded, n_rows=len(rows), n_rep_cells=len(rep_cells),
        n_rows_iso_default_height=sum(1 for r in rows if r["ant"] == "iso" and r["default_height"]),
        n_rows_height_variant=sum(1 for r in rows if not r["default_height"]),
        n_rows_antenna=sum(1 for r in rows if r["ant"] != "iso"),
        by_scene=[dict(scene=k[0], build=k[1], depth=k[2], n_cells=len(v), elevations=sorted(v, reverse=True))
                  for k, v in sorted(by_scene.items(), key=lambda kv: (order[kv[0][0]], kv[0][1], kv[0][2]))],
        by_scene_scope="iso rows at the default height, rep runs excluded",
        n_shard_files_read_by_inventory_step=len(shard_hashes),
        n_shard_files_read=len(shard_hashes),
        shard_files_digest=None,
        shard_files_scope=("n_shard_files_read and shard_files_digest cover every shard opened by the whole run "
                           "(refreshed at each checkpoint, so the final ledger includes the ray-ladder shards); "
                           "n_shard_files_read_by_inventory_step counts the shards opened for the production filter"),
    )
    LEDGER["inventory"] = inventory
    LEDGER["rows"] = rows
    write_ledger("partial", "inventory_rows")

    # ---------------------------------------------------------------- section 3: summaries
    summ = []
    for sc in SCENE_ORDER:
        rr = [r for r in rows if r["scene"] == sc and r["ant"] == "iso" and r["default_height"]]
        if not rr:
            continue
        summ.append(dict(scene=sc, n_cells=len(rr),
                         contrast_min_db=min(r["comb_contrast_db"] for r in rr),
                         contrast_max_db=max(r["comb_contrast_db"] for r in rr),
                         sv_min_db=min(r["sv_db"] for r in rr), sv_max_db=max(r["sv_db"] for r in rr),
                         el_min_deg=min(r["el_deg"] for r in rr), el_max_deg=max(r["el_deg"] for r in rr),
                         contrast_min_at_el_deg=min(rr, key=lambda r: r["comb_contrast_db"])["el_deg"],
                         contrast_max_at_el_deg=max(rr, key=lambda r: r["comb_contrast_db"])["el_deg"],
                         sv_min_at_el_deg=min(rr, key=lambda r: r["sv_db"])["el_deg"],
                         sv_max_at_el_deg=max(rr, key=lambda r: r["sv_db"])["el_deg"],
                         builds=sorted({r["build"] for r in rr}), depths=sorted({r["depth"] for r in rr})))
    LEDGER["summary_iso"] = summ

    variants = []
    for vn in VARIANTS:
        d = [raw_of[c][f"contrast_{vn}_db"] - raw_of[c]["comb_contrast_db"] for c in row_of]
        variants.append(dict(variant=vn, delta_min_db=rnd(min(d)), delta_max_db=rnd(max(d)),
                             delta_median_db=rnd(float(np.median(d))), n_rows=len(d)))
    keys = ["comb_contrast_db"] + [f"contrast_{vn}_db" for vn in VARIANTS]

    def extreme(rr, fn):
        best = None
        for r in rr:
            for k in keys:
                if best is None or fn(r[k], best[0]):
                    best = (r[k], r, k)
        return best

    gl = [r for r in rows if r["scene"] in GROUND_LIKE and r["ant"] == "iso" and r["default_height"]]
    gl_all = [r for r in rows if r["scene"] in GROUND_LIKE and r["ant"] == "iso"]
    fs = [r for r in rows if r["scene"] == "free_sky" and r["ant"] == "iso"]
    bl = [r for r in rows if r["scene"] == "outdoor01_bldg" and r["ant"] == "iso"]
    g1 = extreme(gl, lambda a, b: a > b)
    g2 = extreme(gl_all, lambda a, b: a > b)
    f1 = extreme(fs, lambda a, b: a < b)
    b1 = extreme(bl, lambda a, b: a < b)
    LEDGER["knob_sensitivity"] = dict(
        variants=variants,
        ground_like_max_contrast_db=g2[0],
        ground_like_max_at=dict(arm=g2[1]["arm"], scene=g2[1]["scene"], el_deg=g2[1]["el_deg"],
                                env_alt_m=g2[1]["env_alt_m"], metric=g2[2]),
        ground_like_max_contrast_default_height_db=g1[0],
        ground_like_max_default_height_at=dict(arm=g1[1]["arm"], scene=g1[1]["scene"], el_deg=g1[1]["el_deg"],
                                               env_alt_m=g1[1]["env_alt_m"], metric=g1[2]),
        free_sky_min_contrast_db=f1[0],
        free_sky_min_at=dict(arm=f1[1]["arm"], el_deg=f1[1]["el_deg"], metric=f1[2]),
        bldg_only_min_contrast_db=(b1[0] if b1 else None),
        n_rows_ground_like=len(gl_all), n_rows_ground_like_default_height=len(gl), n_rows_free_sky=len(fs),
    )

    base_by_key = {}
    for c in kept:
        f = parsed[c[0]]
        if "rep" not in f:
            base_by_key[(AG.key_without(f, ["rep"]), c[1])] = c
    groups = defaultdict(list)
    orphan = 0
    for c in rep_cells:
        k = (AG.key_without(parsed[c[0]], ["rep"]), c[1])
        if k in base_by_key:
            groups[k].append(c)
        else:
            orphan += 1
    rep_rows = []
    for k, reps in groups.items():
        b = base_by_key[k]
        Eb = E_of[b]
        vb = float(np.mean(np.abs(Eb - Eb.mean()) ** 2))
        cs = [raw_of[b]["comb_contrast_db"]]
        rels = []
        for c in reps:
            cs.append(contrast_db(E_of[c], info_of[c]["prf"], FFL))
            rels.append(float(np.sqrt(np.mean(np.abs(E_of[c] - Eb) ** 2) / vb)))
        rb = row_of[b]
        rep_rows.append(dict(scene=rb["scene"], build=rb["build"], depth=rb["depth"], el_deg=rb["el_deg"],
                             ant=rb["ant"], env_alt_m=rb["env_alt_m"], base_arm=b[0],
                             rep_ids=sorted(int(parsed[c[0]]["rep"]) for c in reps), n_runs=1 + len(reps),
                             contrast_min_db=rnd(min(cs)), contrast_max_db=rnd(max(cs)),
                             contrast_spread_db=rnd(max(cs) - min(cs)), rel_rms_change_max=float(f"{max(rels):.4g}")))
    rep_rows.sort(key=lambda r: (order[r["scene"]], r["build"], r["depth"] or 0, -r["el_deg"]))
    LEDGER["repeats"] = dict(
        n_groups=len(rep_rows), n_rep_cells=len(rep_cells), n_rep_cells_without_base=orphan,
        max_contrast_spread_db=(max(r["contrast_spread_db"] for r in rep_rows) if rep_rows else None),
        max_rel_rms_change=(max(r["rel_rms_change_max"] for r in rep_rows) if rep_rows else None),
        groups=rep_rows, scope="el window excluded; munich and env_scat excluded")
    write_ledger("partial", "summaries")

    # ---------------------------------------------------------------- section 4: ground floor, clutter, canyon, ladder
    def twin(c, vary, pred):
        """Kept non-rep cell whose parsed fields equal c's except on `vary`, same el, satisfying pred."""
        k = AG.key_without(parsed[c[0]], vary)
        hits = [d for d in row_of if d[1] == c[1] and AG.key_without(parsed[d[0]], vary) == k and pred(parsed[d[0]])]
        if len(hits) > 1:
            raise SystemExit(f"twin not unique for {c} vary {vary}: {hits}")
        return hits[0] if hits else None

    gf_rows = []
    by_scene_added = defaultdict(list)
    for c, r in row_of.items():
        f = parsed[c[0]]
        if r["ant"] != "iso" or not r["default_height"] or r["scene"] == "free_sky":
            continue
        t = twin(c, ["env"], lambda g: "env" not in g)
        if t is None:
            continue
        D = E_of[c] - E_of[t]
        Ef = E_of[t]
        added = db(float(np.mean(np.abs(D - D.mean()) ** 2)) / float(np.mean(np.abs(Ef - Ef.mean()) ** 2)))
        by_scene_added[r["scene"]].append(added)
        if r["scene"] != "outdoor01_ground":
            continue
        n = D.size
        P = power_spectrum(D)[1:]
        seed = [WHITE_SEED, int(r["depth"] or 0), int(round(100 * r["el_deg"])) + 100000,
                0 if r["build"] == BUILD_LABEL[None] else 1]
        rng = np.random.default_rng(seed)
        W = rng.standard_normal(n) + 1j * rng.standard_normal(n)
        Pw = power_spectrum(W)[1:]

        def flat(p):
            return float(np.exp(np.mean(np.log(p))) / p.mean())

        def top(p):
            k = p.size // TOP_SHARE_FRACTION_DIV
            return float(np.sort(p)[::-1][:k].sum() / p.sum())

        gf_rows.append(dict(scene=r["scene"], el_deg=r["el_deg"], build=r["build"], depth=r["depth"],
                            flatness=rnd(flat(P), 4), flatness_white_ref=rnd(flat(Pw), 4),
                            top1pct_share=rnd(top(P), 4), top1pct_share_white_ref=rnd(top(Pw), 4),
                            added_varying_over_free_sky_db=rnd(added),
                            added_total_over_free_sky_db=rnd(db(float(np.mean(np.abs(D) ** 2))
                                                                / float(np.mean(np.abs(Ef) ** 2)))),
                            free_sky_arm=t[0], scene_arm=c[0], white_ref_seed=seed))
    gf_rows.sort(key=lambda r: (r["build"], r["depth"], -r["el_deg"]))
    ga = by_scene_added.get("outdoor01_ground", [])
    LEDGER["ground_floor"] = dict(
        rows=gf_rows,
        added_varying_over_free_sky_min_db=(rnd(min(ga)) if ga else None),
        added_varying_over_free_sky_max_db=(rnd(max(ga)) if ga else None),
        n_matched_iso_pairs=len(ga),
        by_scene=[dict(scene=s, n_pairs=len(v), added_varying_min_db=rnd(min(v)), added_varying_max_db=rnd(max(v)))
                  for s, v in sorted(by_scene_added.items(), key=lambda kv: order[kv[0]])],
        scope="iso, default height, pairs matched on every arm field except env, same poses")

    cl_rows = []
    for c, r in row_of.items():
        if r["scene"] not in GROUND_LIKE or not r["default_height"]:
            continue
        t = twin(c, ["env"], lambda g: "env" not in g)
        if t is None:
            continue
        inf = info_of[c]
        Pf = power_spectrum(E_of[t])
        Ps = power_spectrum(E_of[c])
        comb, non = masks(E_of[c].size, inf["prf"], FFL)
        cl_rows.append(dict(scene=r["scene"], build=r["build"], depth=r["depth"], el_deg=r["el_deg"], ant=r["ant"],
                            ant_cap_db=r["ant_cap_db"], aim_offset_deg=r["aim_offset_deg"],
                            free_sky_comb_per_bin_minus_ground_noncomb_per_bin_db=rnd(db(Pf[comb].mean() / Ps[non].mean())),
                            free_sky_arm=t[0], scene_arm=c[0]))
    cl_rows.sort(key=lambda r: (order[r["scene"]], r["ant"], r["build"], r["depth"], -r["el_deg"]))

    def _group_cl(rr):
        g = defaultdict(list)
        for x in rr:
            if x["ant"] == "iso":
                g[(x["scene"], x["build"], x["depth"])].append(x["free_sky_comb_per_bin_minus_ground_noncomb_per_bin_db"])
        return g
    iso_cl = [r["free_sky_comb_per_bin_minus_ground_noncomb_per_bin_db"] for r in cl_rows if r["ant"] == "iso"]
    LEDGER["clutter_limited"] = dict(
        rows=cl_rows, iso_min_db=(min(iso_cl) if iso_cl else None), iso_max_db=(max(iso_cl) if iso_cl else None),
        n_iso_rows=len(iso_cl),
        iso_pooled_scope="iso_min_db / iso_max_db pool every ground-like scene, build and depth",
        iso_by_scene_build_depth=[dict(scene=k[0], build=k[1], depth=k[2], n_rows=len(v), min_db=min(v), max_db=max(v))
                                  for k, v in sorted(_group_cl(cl_rows).items(),
                                                     key=lambda kv: (order[kv[0][0]], kv[0][1], kv[0][2]))],
        scope="every ground-like scene row at the default height with a free_sky twin (same antenna setting)")

    cb_rows = []
    for c, r in row_of.items():
        if r["scene"] != "street_canyon" or r["ant"] != "iso" or r["build"] != BUILD_LABEL[None]:
            continue
        t = twin(c, ["solver_build"], lambda g: g.get("solver_build") is not None)
        if t is None:
            continue
        r2 = row_of[t]
        cb_rows.append(dict(el_deg=r["el_deg"], depth=r["depth"], build_new=r2["build"],
                            static_201_db=r["static_db"], static_210_db=r2["static_db"],
                            varying_201_db=r["varying_db"], varying_210_db=r2["varying_db"],
                            contrast_201_db=r["comb_contrast_db"], contrast_210_db=r2["comb_contrast_db"],
                            static_change_db=rnd(raw_of[t]["static_db"] - raw_of[c]["static_db"]),
                            varying_change_db=rnd(raw_of[t]["varying_db"] - raw_of[c]["varying_db"])))
    cb_rows.sort(key=lambda r: (r["depth"], -r["el_deg"]))
    other_bc = []
    for c, r in row_of.items():
        if r["scene"] in ("street_canyon",) or r["ant"] != "iso" or r["build"] != BUILD_LABEL[None]:
            continue
        t = twin(c, ["solver_build"], lambda g: g.get("solver_build") is not None)
        if t is None:
            continue
        r2 = row_of[t]
        other_bc.append(dict(scene=r["scene"], depth=r["depth"], el_deg=r["el_deg"],
                             static_change_db=rnd(raw_of[t]["static_db"] - raw_of[c]["static_db"]),
                             varying_change_db=rnd(raw_of[t]["varying_db"] - raw_of[c]["varying_db"])))
    LEDGER["canyon_build_change"] = dict(
        rows=cb_rows,
        other_scenes_abs_static_change_max_db=(max(abs(x["static_change_db"]) for x in other_bc) if other_bc else None),
        other_scenes_abs_varying_change_max_db=(max(abs(x["varying_change_db"]) for x in other_bc) if other_bc else None),
        other_scenes_n_pairs=len(other_bc), other_scenes=other_bc,
        scope="iso, default height; pairs matched on every arm field except the solver build tag")

    ladder_rows, ladder_incomplete = [], []
    base = [c for c, r in row_of.items() if r["scene"] == RAY_LADDER_CELL["scene"] and r["build"] == RAY_LADDER_CELL["build"]
            and r["depth"] == RAY_LADDER_CELL["depth"] and r["el_deg"] == RAY_LADDER_CELL["el_deg"]
            and r["ant"] == "iso" and r["default_height"]]
    if len(base) == 1:
        kb = AG.key_without(parsed[base[0][0]], ["spp"])
        for c in sorted(cell_keys):
            if c[1] != RAY_LADDER_CELL["el_deg"] or AG.key_without(parsed[c[0]], ["spp"]) != kb:
                continue
            ok, why = load_cell(c)
            spp = int(parsed[c[0]]["spp"])
            if not ok:
                ladder_incomplete.append(dict(spp=spp, arm=c[0], reason=why))
                continue
            lv = levels(E_of[c], info_of[c]["prf"], FFL)
            ladder_rows.append(dict(spp=spp, varying_db=rnd(lv["varying_db"]), static_db=rnd(lv["static_db"]),
                                    comb_contrast_db=rnd(lv["comb_contrast_db"]), n_poses=info_of[c]["n_poses"],
                                    production=(spp == int(PROD["spp"])), arm=c[0]))
    ladder_rows.sort(key=lambda r: r["spp"])
    hi = [r for r in ladder_rows if r["spp"] >= 10 ** 9]
    LEDGER["ray_ladder"] = dict(
        cell=RAY_LADDER_CELL, rows=ladder_rows, incomplete=ladder_incomplete,
        varying_min_db_at_or_above_1e9=(min(r["varying_db"] for r in hi) if hi else None),
        varying_max_db_at_or_above_1e9=(max(r["varying_db"] for r in hi) if hi else None),
        static_min_db=(min(r["static_db"] for r in ladder_rows) if ladder_rows else None),
        static_max_db=(max(r["static_db"] for r in ladder_rows) if ladder_rows else None),
        scope="arms equal to the production cell on every field except spp, iso, default height")
    write_ledger("partial", "ground_clutter_canyon_ladder")

    # ---------------------------------------------------------------- section 5: dwell, height, antenna
    def pick(scene, ant, el, cap=None, aim=0.0):
        cands = [c for c, r in row_of.items() if r["scene"] == scene and r["ant"] == ant and r["el_deg"] == el
                 and r["default_height"] and (ant == "iso" or (r["ant_cap_db"] == cap and r["aim_offset_deg"] == aim))]
        pref = [c for c in cands if (row_of[c]["build"], row_of[c]["depth"]) == PREFERRED_BUILD_DEPTH]
        if len(pref) == 1:
            return pref[0]
        alt = [c for c in cands if row_of[c]["depth"] == PREFERRED_BUILD_DEPTH[1]]
        return alt[0] if len(alt) == 1 else None

    dwell_rows, dwell_missing = [], []
    for scene, ant in DWELL_SERIES:
        for el in DWELL_ELS:
            c = pick(scene, ant, el, cap=(CAP_DEFAULT if ant != "iso" else None))
            if c is None:
                dwell_missing.append(dict(scene=scene, ant=ant, el_deg=el))
                continue
            E = E_of[c]
            prf = info_of[c]["prf"]
            for N in DWELL_WINDOWS:
                comb, non = masks(N, prf, FFL)
                segs = [contrast_db(E[i:i + N], prf, FFL) for i in range(0, E.size - N + 1, N)]
                dwell_rows.append(dict(scene=scene, ant=ant, el_deg=el, window_poses=N,
                                       window_s=rnd(N / prf, 4),
                                       comb_contrast_db=rnd(contrast_db(E[:N], prf, FFL)),
                                       nonoverlap_mean_db=rnd(float(np.mean(segs))), nonoverlap_min_db=rnd(min(segs)),
                                       nonoverlap_max_db=rnd(max(segs)), n_windows=len(segs),
                                       comb_bins_fraction=rnd(float(comb.mean()), 4),
                                       build=row_of[c]["build"], depth=row_of[c]["depth"],
                                       ant_cap_db=row_of[c]["ant_cap_db"], aim_offset_deg=row_of[c]["aim_offset_deg"],
                                       arm=c[0]))
    LEDGER["dwell"] = dict(rows=dwell_rows, missing=dwell_missing)

    h_rows, seen = [], set()
    for c, r in row_of.items():
        if r["default_height"]:
            continue
        ctrl = twin(c, ["env_alt"], lambda g: "env_alt" not in g)
        for d in ([c] + ([ctrl] if ctrl else [])):
            if d in seen:
                continue
            seen.add(d)
            rd = row_of[d]
            h_rows.append(dict(scene=rd["scene"], el_deg=rd["el_deg"], env_alt_m=rd["env_alt_m"],
                               default_height=rd["default_height"], ant=rd["ant"], ant_cap_db=rd["ant_cap_db"],
                               aim_offset_deg=rd["aim_offset_deg"], build=rd["build"], depth=rd["depth"],
                               radar_height_above_ground_m=rd["radar_height_above_ground_m"],
                               varying_db=rd["varying_db"], static_db=rd["static_db"],
                               comb_contrast_db=rd["comb_contrast_db"], sv_db=rd["sv_db"], arm=rd["arm"],
                               has_default_height_control=(True if rd["default_height"] else ctrl is not None)))
    h_rows.sort(key=lambda r: (order[r["scene"]], r["ant"], r["build"], r["depth"], -r["el_deg"], r["env_alt_m"]))
    LEDGER["height"] = dict(rows=h_rows,
                            scope="every height-variant row plus its default-height control (same other fields)")

    ap_rows, unmatched = [], []
    ant_cells = [c for c, r in row_of.items() if r["ant"] != "iso"]
    for c in ant_cells:
        r = row_of[c]
        iso = twin(c, ["ant", "aim"], lambda g: "ant" not in g and "aim" not in g)
        if iso is None:
            unmatched.append(dict(arm=c[0], el_deg=c[1], reason="no complete iso control with the same other fields"))
            continue
        ri = row_of[iso]
        Pa, Pi = power_spectrum(E_of[c]), power_spectrum(E_of[iso])
        comb, non = masks(E_of[c].size, info_of[c]["prf"], FFL)
        ap_rows.append(dict(scene=r["scene"], el_deg=r["el_deg"], ant=r["ant"], ant_cap_db=r["ant_cap_db"],
                            aim_offset_deg=r["aim_offset_deg"], env_alt_m=r["env_alt_m"], build=r["build"],
                            depth=r["depth"], contrast_iso_db=ri["comb_contrast_db"],
                            contrast_ant_db=r["comb_contrast_db"],
                            total_delta_db=rnd(raw_of[c]["total_db"] - raw_of[iso]["total_db"]),
                            static_delta_db=rnd(raw_of[c]["static_db"] - raw_of[iso]["static_db"]),
                            varying_delta_db=rnd(raw_of[c]["varying_db"] - raw_of[iso]["varying_db"]),
                            noncomb_delta_db=rnd(db(Pa[non].mean() / Pi[non].mean())),
                            comb_delta_db=rnd(db(Pa[comb].mean() / Pi[comb].mean())),
                            sv_iso_db=ri["sv_db"], sv_ant_db=r["sv_db"], ant_arm=c[0], iso_arm=iso[0]))
    ap_rows.sort(key=lambda r: (order[r["scene"]], r["build"], r["depth"], r["ant_cap_db"], r["aim_offset_deg"],
                                r["env_alt_m"] or 0, -r["el_deg"]))
    amf = []
    for c in ant_cells:
        r = row_of[c]
        if r["scene"] == "free_sky":
            continue
        fa = twin(c, ["env", "env_alt"], lambda g: "env" not in g)
        si = twin(c, ["ant", "aim"], lambda g: "ant" not in g and "aim" not in g)
        fi = twin(c, ["env", "env_alt", "ant", "aim"], lambda g: "env" not in g and "ant" not in g and "aim" not in g)
        if not (fa and si and fi):
            continue
        amf.append(dict(scene=r["scene"], el_deg=r["el_deg"], ant_cap_db=r["ant_cap_db"],
                        aim_offset_deg=r["aim_offset_deg"], env_alt_m=r["env_alt_m"], build=r["build"],
                        depth=r["depth"],
                        scene_total_minus_free_sky_iso_db=rnd(raw_of[si]["total_db"] - raw_of[fi]["total_db"]),
                        scene_total_minus_free_sky_ant_db=rnd(raw_of[c]["total_db"] - raw_of[fa]["total_db"]),
                        scene_varying_minus_free_sky_iso_db=rnd(raw_of[si]["varying_db"] - raw_of[fi]["varying_db"]),
                        scene_varying_minus_free_sky_ant_db=rnd(raw_of[c]["varying_db"] - raw_of[fa]["varying_db"])))
    amf.sort(key=lambda r: (order[r["scene"]], r["build"], r["ant_cap_db"], r["aim_offset_deg"], r["env_alt_m"] or 0,
                            -r["el_deg"]))

    # queued antenna job lines (parsed, never executed)
    ant_fields_landed = [parsed[c[0]] for c in ant_cells]
    rt_tags = {f.get("solver_build") for f in ant_fields_landed}
    rt_for_recon = rt_tags.pop() if len(rt_tags) == 1 else None
    known_flags = {"engine", "spp", "n-poses", "max-depth", "range-m", "sw", "els", "env", "ant-pattern", "ant-cap",
                   "aim-offset", "env-alt", "shard", "nshards"}
    queued: dict = {}
    file_status = []
    for jf in JOB_FILES:
        txt = (ROOT / jf).read_text(encoding="utf-8").splitlines()
        track(jf)
        first = txt[0] if txt else ""
        file_status.append(dict(job_file=jf, first_line=first.strip(), marked_superseded=("SUPERSEDED" in first),
                                n_job_lines=sum(1 for s in txt if s.strip() and not s.strip().startswith("#"))))
        for ln, s in enumerate(txt, 1):
            s = s.strip()
            if not s or s.startswith("#"):
                continue
            toks = shlex.split(s)
            fl, i = {}, 0
            while i < len(toks):
                t = toks[i]
                if t.startswith("--"):
                    if "=" in t:
                        k, v = t[2:].split("=", 1)
                        i += 1
                    elif i + 1 < len(toks) and not toks[i + 1].startswith("--"):
                        k, v = t[2:], toks[i + 1]
                        i += 2
                    else:
                        k, v = t[2:], True
                        i += 1
                    fl[k] = v
                else:
                    i += 1
            unknown = sorted(set(fl) - known_flags)
            env = fl.get("env")
            env_name = env.replace(":", "-") if isinstance(env, str) else None
            antp = fl.get("ant-pattern", "iso")
            cap = float(fl.get("ant-cap", CAP_DEFAULT)) if antp != "iso" else None
            aim = float(fl.get("aim-offset", 0.0)) if antp != "iso" else None
            alt = float(fl["env-alt"]) if "env-alt" in fl else None
            for el_s in str(fl.get("els", "")).split(","):
                if not el_s.strip():
                    continue
                el = float(el_s)
                key = (SCENE_OF_ENV.get(env_name, env_name), el, int(fl.get("max-depth", 0)), str(fl.get("spp")),
                       str(fl.get("n-poses")), str(fl.get("range-m")), str(fl.get("sw")), antp, cap, aim, alt)
                q = queued.setdefault(key, dict(job_lines=[], unknown_flags=set(), env_name=env_name))
                q["job_lines"].append(f"{jf}:{ln}")
                q["unknown_flags"].update(unknown)

    def cell_qkey(c):
        f = parsed[c[0]]
        ant, cap, aim = ant_of(f)
        return (scene_of(f), c[1], int(f.get("max_depth", 0)), f["spp"], f["n_poses"], f["range_m"],
                f.get("switches"), ant, cap, aim, float(f["env_alt"]) if "env_alt" in f else None)

    prod_like = defaultdict(list)
    for c in cand:
        if "rep" in parsed[c[0]] or "env_scat" in parsed[c[0]]:
            continue
        prod_like[cell_qkey(c)].append(c)
    superseded_files = {x["job_file"] for x in file_status if x["marked_superseded"]}
    q_rows = []
    for key, q in queued.items():
        scene, el, depth, spp, npz, rng_s, sw, antp, cap, aim, alt = key
        hits_all = prod_like.get(key, [])
        #: the queue writes at the build tag the landed antenna cells carry; other builds do not count as landed
        hits = [c for c in hits_all if parsed[c[0]].get("solver_build") == rt_for_recon]
        other = [c for c in hits_all if c not in hits and info_of.get(c, {}).get("complete")]
        comp = [c for c in hits if info_of.get(c, {}).get("complete")]
        superseded_only = all(jl.split(":")[0] in superseded_files for jl in q["job_lines"])
        status = "landed_complete" if comp else ("landed_incomplete" if hits else "not_landed")
        fields = dict(engine="sionna", spp=spp, switches=sw, range_m=rng_s, n_poses=npz)
        if q["env_name"]:
            fields["env"] = q["env_name"]
        if alt is not None:
            fields["env_alt"] = f"{alt:g}"
        fields.update(mesh_fix=PROD["mesh_fix"], blade_law=PROD["blade_law"])
        if antp != "iso":
            fields["ant"] = ANT_BASE if abs(cap - CAP_DEFAULT) < 1e-9 else f"{ANT_BASE}c{int(round(cap))}"
            if aim:
                fields["aim"] = f"{aim:g}"
        if rt_for_recon:
            fields["solver_build"] = rt_for_recon
        if depth:
            fields["max_depth"] = str(depth)
        recon = AG.unparse(fields)
        AG.parse(recon, strict=True)
        q_rows.append(dict(scene=scene, el_deg=el, depth=depth, ant=antp, ant_cap_db=cap, aim_offset_deg=aim,
                           env_alt_m=alt, status=status, job_lines=q["job_lines"],
                           unknown_flags=sorted(q["unknown_flags"]),
                           only_in_superseded_files=superseded_only, queue_build=BUILD_LABEL.get(rt_for_recon),
                           landed_arms=[c[0] for c in hits],
                           complete_at_other_builds=sorted({BUILD_LABEL[parsed[c[0]].get("solver_build")] for c in other}),
                           incomplete_reasons=[info_of.get(c, {}).get("reason") for c in hits if c not in comp],
                           reconstructed_arm=recon))
    q_rows.sort(key=lambda r: (r["ant"], order.get(r["scene"], 99), r["ant_cap_db"] or 0, r["aim_offset_deg"] or 0,
                               r["env_alt_m"] or 0, -r["el_deg"]))
    q_ant = [r for r in q_rows if r["ant"] != "iso"]
    q_iso = [r for r in q_rows if r["ant"] == "iso"]
    fs_gain = [r for r in ap_rows if r["scene"] == "free_sky" and r["aim_offset_deg"] == 0.0]
    LEDGER["antenna_pairs"] = dict(
        rows=ap_rows, unmatched_ant_cells=unmatched, ant_minus_free_sky=amf,
        n_ant_cells_landed=len(ant_cells),
        n_ant_cells_incomplete=sum(1 for x in incomplete if "ant" in parsed[x["arm"]]),
        incomplete_ant_cells=[x for x in incomplete if "ant" in parsed[x["arm"]]],
        code_expectation=dict(two_way_peak_gain_db=2.0 * G_E_MAX, from_quote="ant_peak_gain",
                              free_sky_total_delta_db=[dict(el_deg=r["el_deg"], build=r["build"], depth=r["depth"],
                                                            ant_cap_db=r["ant_cap_db"], total_delta_db=r["total_delta_db"])
                                                       for r in fs_gain]),
        queue_files=file_status,
        queued_ant_cells=q_ant,
        queued_but_not_landed_ant_arms=[r["reconstructed_arm"] + f"_el{r['el_deg']:+g}" for r in q_ant
                                        if r["status"] != "landed_complete" and not r["only_in_superseded_files"]],
        superseded_only_not_landed_ant_arms=[r["reconstructed_arm"] + f"_el{r['el_deg']:+g}" for r in q_ant
                                             if r["status"] != "landed_complete" and r["only_in_superseded_files"]],
        n_queued_ant_cells=len(q_ant),
        n_queued_ant_cells_landed_complete=sum(1 for r in q_ant if r["status"] == "landed_complete"),
        n_queued_ant_cells_not_landed_active=sum(1 for r in q_ant if r["status"] != "landed_complete"
                                                 and not r["only_in_superseded_files"]),
        n_queued_ant_cells_not_landed_superseded_only=sum(1 for r in q_ant if r["status"] != "landed_complete"
                                                          and r["only_in_superseded_files"]),
        queued_iso_cells=q_iso,
        queued_but_not_landed_iso_arms=[r["reconstructed_arm"] + f"_el{r['el_deg']:+g}" for r in q_iso
                                        if r["status"] != "landed_complete" and not r["only_in_superseded_files"]],
        reconstruction_solver_build_tag=rt_for_recon,
    )
    write_ledger("partial", "dwell_height_antenna")

    # ---------------------------------------------------------------- section 6: hover code check
    src_path = ROOT / "benchmark/elevation_sweep_md.py"
    tree = ast.parse(src_path.read_text(encoding="utf-8"))
    fns = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    mod_consts = {}
    for n in tree.body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name) \
                and isinstance(n.value, ast.Constant) and isinstance(n.value.value, (int, float)):
            mod_consts[n.targets[0].id] = n.value.value

    def const_tuple(v):
        if not isinstance(v, ast.Tuple):
            return False
        for e in v.elts:
            if isinstance(e, ast.Constant) and isinstance(e.value, (int, float)):
                continue
            if isinstance(e, ast.Call) and isinstance(e.func, ast.Name) and e.func.id == "float" and len(e.args) == 1 \
                    and isinstance(e.args[0], ast.Name) and e.args[0].id in mod_consts:
                continue
            return False
        return True

    checks = {}
    run_fn, bsb = fns.get("run"), fns.get("build_scene_builtin")
    ctr_assign = []
    for n in ast.walk(run_fn):
        if isinstance(n, (ast.AugAssign, ast.AnnAssign)) and isinstance(n.target, ast.Name) and n.target.id == "_ctr":
            ctr_assign.append(("other", n.lineno, False))
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name) and t.id == "_ctr":
                    ctr_assign.append(("constant_tuple", n.lineno, const_tuple(n.value)))
                elif isinstance(t, ast.Tuple) and any(isinstance(e, ast.Name) and e.id == "_ctr" for e in t.elts):
                    pos = [i for i, e in enumerate(t.elts) if isinstance(e, ast.Name) and e.id == "_ctr"][0]
                    ok = isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Name) \
                        and n.value.func.id == "build_scene_builtin"
                    ret_ok = False
                    if ok and bsb is not None:
                        ctr_vals = [a.value for a in ast.walk(bsb) if isinstance(a, ast.Assign)
                                    and any(isinstance(x, ast.Name) and x.id == "ctr" for x in a.targets)]
                        rets = [a.value for a in ast.walk(bsb) if isinstance(a, ast.Return)]
                        ret_ok = bool(ctr_vals) and all(const_tuple(v) for v in ctr_vals) and bool(rets) and all(
                            isinstance(v, ast.Tuple) and len(v.elts) > pos and isinstance(v.elts[pos], ast.Name)
                            and v.elts[pos].id == "ctr" for v in rets)
                    ctr_assign.append(("build_scene_builtin_return", n.lineno, bool(ok and ret_ok)))
    place_calls = []
    for n in ast.walk(run_fn):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "place":
            kw = {k.arg: k.value for k in n.keywords}
            place_calls.append((n.lineno, isinstance(kw.get("center"), ast.Name) and kw["center"].id == "_ctr"))
    checks["centre_assignments"] = [dict(kind=k, line=ln, constant=ok) for k, ln, ok in ctr_assign]
    checks["place_calls"] = [dict(line=ln, center_is__ctr=ok) for ln, ok in place_calls]
    position_fixed = bool(ctr_assign) and all(ok for _, _, ok in ctr_assign) and bool(place_calls) \
        and all(ok for _, ok in place_calls)
    LEDGER["hover"] = dict(
        position_fixed=position_fixed,
        code_checks=checks,
        rotor_phase_advances_with_pose_index=("np.arange(n) / prf" in quotes["rotor_phase_time_axis"]["full_line"]),
        production_filter_excludes_rotor_preset_and_other_drones=(
            not any(t in parsed[r["arm"]] for r in rows for t in ("rotor", "rotor_seed", "drone"))),
        n_cells_with_rotor_or_drone_tag_removed_by_filter=sum(
            v for k, v in other_tags.items() if any(t in ("rotor", "rotor_seed", "drone") for t in k.split(","))),
        rotor_drone_check_definition=("true when no row's parsed arm carries a rotor, rotor_seed or drone field; the "
                                      "count is the cells removed at the 'no tags outside the allowed axes' step "
                                      "because they carry one of those fields"),
        quotes=[quotes[k] for k in ("hover_centre", "builtin_scene_centre", "hover_place_call",
                                    "rotor_phase_time_axis", "rotor_rpm_source")],
        definition=("position_fixed is true when every assignment to the scene centre _ctr inside run() is a tuple of "
                    "numeric constants (or the build_scene_builtin return whose ctr is such a tuple) and every "
                    "place() call in run() uses center=_ctr, so the drone position does not depend on the pose."),
    )
    write_ledger("partial", "hover")

    # ---------------------------------------------------------------- section 7: spectra npz
    series_meta, psd, statics = [], [], []
    freq = None
    comb_s = non_s = None
    prf_used = None
    for scene, ant in DWELL_SERIES:
        for el in DWELL_ELS:
            c = pick(scene, ant, el, cap=(CAP_DEFAULT if ant != "iso" else None))
            sid = f"{scene}__{ant}__el{el:+g}"
            if c is None:
                series_meta.append(dict(series_id=sid, scene=scene, ant=ant, el_deg=el, arm=None, present=False))
                continue
            E = E_of[c]
            prf = info_of[c]["prf"]
            n = E.size
            if freq is None:
                freq = np.fft.fftshift(np.fft.fftfreq(n, 1.0 / prf))
                comb, non = masks(n, prf, FFL)
                comb_s, non_s = np.fft.fftshift(comb), np.fft.fftshift(non)
                prf_used, n_used = prf, n
            if (prf, n) != (prf_used, n_used):
                raise SystemExit("spectra series disagree on PRF or n")
            P = power_spectrum(E)
            with np.errstate(divide="ignore"):
                pd = 10 * np.log10(P)
            pd[0] = np.nan
            psd.append(np.fft.fftshift(pd))
            statics.append(db(abs(E.mean()) ** 2))
            r = row_of[c]
            series_meta.append(dict(series_id=sid, scene=scene, ant=ant, el_deg=el, arm=c[0], build=r["build"],
                                    depth=r["depth"], ant_cap_db=r["ant_cap_db"], aim_offset_deg=r["aim_offset_deg"],
                                    static_db=r["static_db"], varying_db=r["varying_db"], present=True,
                                    npz_row=len(psd) - 1))
    if psd:
        ids = np.array([s["series_id"] for s in series_meta if s["present"]])
        extra = {f"psd_db__{s}": psd[i] for i, s in enumerate(ids)}
        np.savez_compressed(OUT_NPZ, freq_hz=freq, psd_db=np.vstack(psd), series_id=ids,
                            static_db=np.array(statics), comb_bin_mask=comb_s, noncomb_bin_mask=non_s,
                            ffl_hz=np.array(FFL), prf_hz=np.array(prf_used), **extra)
    LEDGER["spectra_series"] = dict(npz=OUT_NPZ.name, series=series_meta,
                                    npz_keys=["freq_hz", "psd_db", "series_id", "static_db", "comb_bin_mask",
                                              "noncomb_bin_mask", "ffl_hz", "prf_hz", "psd_db__<series_id>"],
                                    reference="common absolute reference (PathSolver level in dB, arbitrary); "
                                              "no per-series normalisation")
    write_ledger("complete", "spectra")


if __name__ == "__main__":
    main()
