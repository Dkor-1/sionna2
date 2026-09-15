"""What Sionna RT 2.1.0 PathSolver and our kernel (src/rcs_sbr.py) can each contribute to an ISAC plan.

Purpose
    Build the ledger outputs/isac_plan_engines_0915.json for the ISAC detection+tracking plan report.
    Every number in it is computed here, from
      * small CPU PathSolver runs (installed sionna.rt, Mitsuba variant llvm_ad_mono_polarized):
        the Paths/cir contract (array axes, delay normalisation, angle frame), where Doppler comes from,
        a toy comparison of Doppler extrapolation against re-tracing, and a toy plate tilt (specular-only
        path count and level, plus a samples_per_src ladder for the diffuse-on level, which depends on it),
      * production sweep shards in outputs/elev_sweep_shards (read-only np.load of meta/npaths/idx):
        wall time per pose for PathSolver (2.0.1 baseline names and _rt210 names) and for our kernel,
      * the rotor settings in outputs/report07_three_engines.json _meta (f_tip there includes cos(el_deg) of its
        look; the generator lines are re-read and the value is reproduced from src/drones.py),
      * small CPU calls of our kernel on a flat plate (phase reference, single-frequency output),
      * code quotes that are re-read and checked line by line at run time
        (benchmark/elevation_sweep_md.py, src/rcs_sbr.py, the installed sionna paths.py),
      * a pointer (no recomputation) to the plate reciprocity rows in outputs/kernel_outdoor_review_0915.json.

Run
    CUDA_VISIBLE_DEVICES="" /workspace/.venvs/py312/bin/python benchmark/isac_plan_engines_0915.py
    optional: --core N (single CPU core; default = lowest core in the current affinity)
              --root DIR (repository root; default = parent of this script's directory)
              --out FILE (default ROOT/outputs/isac_plan_engines_0915.json)

Runtime
    About 20 seconds on one CPU core when the Dr.Jit kernel cache is warm (measured 2026-09-15, including the
    tilt ladder up to 16e6 rays); allow a few minutes when LLVM kernels must be compiled first. The shard scan
    reads about 300 small shards.

Scope
    These are simulation / code / bookkeeping checks with no comparison against RF measurements.
    PathSolver levels are "PathSolver level in dB (arbitrary reference)". Wall times are
    single-process wall time under shared-card conditions, as recorded by the production shards.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

NAME = "isac_plan_engines_0915"


def _parse_args():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--core", type=int, default=None,
                    help="CPU core to pin to (default: lowest core in current affinity)")
    ap.add_argument("--root", default=None,
                    help="repository root (default: parent of this script's directory)")
    ap.add_argument("--out", default=None,
                    help="output ledger (default: ROOT/outputs/isac_plan_engines_0915.json)")
    return ap.parse_args()


ARGS = _parse_args()
# Hide GPUs and pin to one core BEFORE numpy / mitsuba / drjit are imported.
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ.setdefault("SIONNA2_ALLOW_CPU", "1")
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"
_CORE = ARGS.core if ARGS.core is not None else min(os.sched_getaffinity(0))
os.sched_setaffinity(0, {_CORE})

import hashlib  # noqa: E402
import json  # noqa: E402
import re  # noqa: E402
import subprocess  # noqa: E402
import time  # noqa: E402
from importlib.metadata import version as _pkg_version  # noqa: E402
from importlib.util import find_spec  # noqa: E402

import numpy as np  # noqa: E402

ROOT = Path(ARGS.root).resolve() if ARGS.root else Path(__file__).resolve().parents[1]
OUT = Path(ARGS.out).resolve() if ARGS.out else ROOT / "outputs" / f"{NAME}.json"
sys.path[:0] = [str(ROOT / "src")]

# --------------------------------------------------------------------------------------------- #
# Configuration inputs (seeds, geometry, grids, sample counts). Not results.
# --------------------------------------------------------------------------------------------- #
CONFIG = {
    "fc_hz": 3.5e9,
    "pathsolver_seed": 42,
    "contract_probe": {"scene": "simple_street_canyon", "tx_pos_m": [0.0, 0.0, 1.0],
                       "rx_pos_m": [2.0, 0.0, 1.0], "rx_array_rows_cols": [1, 2],
                       "max_depth": 1, "samples_per_src": 10000, "deterministic": True,
                       "cfr_offsets_hz": [-50e6, 0.0, 50e6]},
    "angle_probe": {"scene": "empty", "tx_pos_m": [0.0, 0.0, 0.0], "tx_orientation_rad": [1.0, 0.5, 0.3],
                    "rx_pos_m": [3.0, 4.0, 5.0], "rx_orientation_rad": [-0.7, 0.2, 0.1],
                    "max_depth": 0, "samples_per_src": 1000},
    "doppler_probe": {"scene": "simple_reflector", "tx_pos_m": [0.0, 0.0, 10.0],
                      "rx_pos_m": [0.01, 0.0, 10.0], "object_velocity_mps": [0.0, 0.0, 2.0],
                      "max_depth": 1, "samples_per_src": 100000, "deterministic": True,
                      "los": False, "diffuse": False,
                      "second_velocity_test_xyz_components": [[0.0, 1.0], [0.0, 0.0], [1.0, 0.0]]},
    "txrx_velocity_probe": {"scene": "empty", "tx_pos_m": [0.0, 0.0, 0.0], "tx_velocity_mps": [3.0, 0.0, 0.0],
                            "rx_pos_m": [10.0, 0.0, 0.0], "rx_velocity_mps": [-1.0, 0.0, 0.0],
                            "max_depth": 0, "samples_per_src": 1000},
    "per_object_probe": {"scene": "simple_street_canyon", "tx_pos_m": [0.0, 0.0, 10.0],
                         "rx_pos_m": [0.01, 0.0, 10.0], "velocity_rule": "v_i = 0.5*(i+1)*[1,1,1] m/s, i = rank of the object after sorting by mesh bbox "
                                          "centre (x, then y, then z, rounded to bbox_round_decimals); "
                                          "scene.objects order is not stable between runs",
                         "bbox_round_decimals": 2,
                         "velocity_step_mps": 0.5, "max_depth": 1, "samples_per_src": 200000,
                         "deterministic": True, "los": False},
    "time_steps": {"sampling_frequency_hz": 1000.0, "num_time_steps": 50},
    "rotation_probe": {"scene": "simple_reflector", "scattering_coefficient": 0.3, "tilt_from_deg": 2.75,
                       "tilt_to_deg": 3.25, "tilt_axis": "orientation[2] (rotation about x)",
                       "max_depth": 1,
                       "specular_only": {"samples_per_src": 1000000, "diffuse": False, "seed": 1},
                       "diffuse_on_ladder": {"samples_per_src": [250000, 1000000, 4000000, 16000000],
                                             "seeds": [1, 2, 3], "diffuse": True}},
    "cost": {"shard_dir": "outputs/elev_sweep_shards",
             "pathsolver_base_fields": {"engine": "sionna", "spp": "4000000000", "switches": "R0D0E0F1",
                                        "range_m": "15", "n_poses": "8192", "mesh_fix": "batteryi5",
                                        "blade_law": "perairframe"},
             "allowed_extra_fields": ["env", "solver_build", "max_depth"],
             "production_depth": 2,
             "kernel_base_fields": {"engine": "ours", "range_m": "15", "n_poses": "8192",
                                    "mesh_fix": "batteryi5", "blade_law": "perairframe"},
             "trajectory_rates_hz": [1000, 10000, 19700], "trajectory_duration_s": 10},
    "rotor": {"pose_rates_hz": [1000, 10000, 19700], "body_speeds_mps": [0, 5, 10, 15]},
    "kernel": {"plate_side_m": 0.125, "gamma": 1.0, "u": [0.0, 0.0, 1.0], "spacing_div": 12,
               "move_fraction_of_lambda": 0.125, "penetrate": False,
               "freq_offsets_mhz": [-50, 0, 50], "range_m": 15.0},
}

# --------------------------------------------------------------------------------------------- #
# External specification / literature values (the only non-configuration literals).
# --------------------------------------------------------------------------------------------- #
SOURCES = [
    {"id": "speed_of_light", "value": 299792458.0, "unit": "m/s",
     "url": "https://www.bipm.org/en/publications/si-brochure",
     "document": "BIPM, The International System of Units (SI Brochure), 9th edition (2019)",
     "locator": "Section 2.2, Table 1 (defining constant c)",
     "note": "Exact by definition. Used for wavelength lambda = c / fc."},
]
C0 = next(s["value"] for s in SOURCES if s["id"] == "speed_of_light")

# Code quotes: (id, path-kind, relative path, expected line, quoted text). Verified at run time.
QUOTES = [
    ("paths_rx_array_shared", "sionna", "rt/path_solvers/paths.py", 55, "self._rx_array = scene.rx_array"),
    ("paths_tx_array_shared", "sionna", "rt/path_solvers/paths.py", 54, "self._tx_array = scene.tx_array"),
    ("paths_normalize_synthetic_min", "sionna", "rt/path_solvers/paths.py", 463, "min_tau = dr.min(tau, axis=-1)"),
    ("paths_normalize_subtract", "sionna", "rt/path_solvers/paths.py", 472, "tau -= min_tau"),
    ("paths_doppler_time_phase", "sionna", "rt/path_solvers/paths.py", 507, "phase = dr.two_pi*doppler*time_steps"),
    ("scene_object_single_velocity", "sionna", "rt/scene_object.py", 268,
     'raise ValueError("Only a single velocity vector must be provided")'),
    ("field_calculator_object_doppler", "sionna", "rt/path_solvers/field_calculator.py", 557,
     "v_effective = dr.dot(ko_world - ki_world, v_world)"),
    ("path_solver_synthetic_default", "sionna", "rt/path_solvers/path_solver.py", 169, "synthetic_array: bool = True,"),
    ("report15_unpack_reshape", "repo", "benchmark/report15_probe.py", 308,
     "a = (ar + 1j * ai).reshape(-1, ar.shape[-1])[0]"),
    ("report15_unpack_1x1_docstring", "repo", "benchmark/report15_probe.py", 301, "1×1 안테나 가정"),
    ("sweep_timer_start", "repo", "benchmark/elevation_sweep_md.py", 866, "t0 = time.time()"),
    ("sweep_pose_loop", "repo", "benchmark/elevation_sweep_md.py", 969, "for j, i in enumerate(idx):"),
    ("sweep_scene_builtin_rebuild", "repo", "benchmark/elevation_sweep_md.py", 1016,
     "sc, _ctr, _scene_obj_names = build_scene_builtin("),
    ("sweep_scene_rebuild", "repo", "benchmark/elevation_sweep_md.py", 1021, "sc = RP.build_scene(parts, fc=fc)"),
    ("sweep_meta_layout_head", "repo", "benchmark/elevation_sweep_md.py", 1199,
     "meta=np.array([el, a.shard, a.nshards, n, prf,"),
    ("sweep_meta_layout_tail", "repo", "benchmark/elevation_sweep_md.py", 1200, "time.time() - t0, spp]),"),
    ("sweep_kernel_meta_head", "repo", "benchmark/elevation_sweep_md.py", 765,
     "meta=np.array([el, a.shard, a.nshards, n, prf,"),
    ("sweep_kernel_meta_tail", "repo", "benchmark/elevation_sweep_md.py", 766, "time.time() - t0]),"),
    ("sweep_kernel_timer_start", "repo", "benchmark/elevation_sweep_md.py", 738,
     "E = np.zeros(idx.size, complex); t0 = time.time()"),
    ("sweep_build_baseline", "repo", "benchmark/elevation_sweep_md.py", 1318,
     'BUILD_BASELINE = "sionna=2.0.1 sionna-rt=2.0.1 mitsuba=3.8.0 drjit=1.3.1"'),
    ("sweep_build_tag_empty_for_baseline", "repo", "benchmark/elevation_sweep_md.py", 1333,
     "기준 판이면 **빈 글자**, 그 밖에는 `_rt<판>`(2.1.0 → `_rt210`)"),
    ("sweep_build_baseline_caveat", "repo", "benchmark/elevation_sweep_md.py", 1315,
     "「2.0.1 이 아닌 판으로 구웠다는 기록이 없다」"),
    ("sweep_env_refusal_branch", "repo", "benchmark/elevation_sweep_md.py", 656,
     'if a.engine in ("ours", "ours_free", "ours_gpu"):'),
    ("sweep_env_refusal_comment", "repo", "benchmark/elevation_sweep_md.py", 657,
     "# ⛔⛔**우리 커널에는 --env 를 줄 수 없다** (2026-09-01)."),
    ("sweep_env_refusal_if", "repo", "benchmark/elevation_sweep_md.py", 672, 'if getattr(a, "env", ""):'),
    ("sweep_env_refusal_raise", "repo", "benchmark/elevation_sweep_md.py", 673, "raise SystemExit("),
    ("sweep_env_refusal_message", "repo", "benchmark/elevation_sweep_md.py", 674,
     'f"⛔ --engine {a.engine} 에는 --env 를 줄 수 없다 — 우리 커널은 "'),
    ("sweep_env_refusal_reason", "repo", "benchmark/elevation_sweep_md.py", 675,
     'f"sbr_field(mv, ...) 로 **드론 메쉬만** 받아 환경이 도달하지 않는다. "'),
    ("sweep_env_refusal_grid_factor", "repo", "benchmark/elevation_sweep_md.py", 678,
     "합집합 bbox 로 정해지므로 온 지면은 79,483 배이고"),
    ("supervisor_workers_per_card_tiers", "repo", "runners/worker_supervisor.py", 63,
     "TIERS = [(10_000, 3), (20_000, 2), (70_000, 2), (float(\"inf\"), 1)]"),
    ("report07_ledger_path", "repo", "benchmark/report07_three_engine_maps.py", 61,
     'OUTJ = os.path.join(ROOT, "outputs", "report07_three_engines.json")'),
    ("report07_rpm0_hover", "repo", "benchmark/report07_three_engine_maps.py", 89,
     'rpm0 = float(getattr(spec, "hover_rpm", 6000.0))'),
    ("report07_wavelength", "repo", "benchmark/report07_three_engine_maps.py", 90, "lam = 3e8 / FC"),
    ("report07_radius", "repo", "benchmark/report07_three_engine_maps.py", 91, "R = spec.prop_dia_mm / 1000.0 / 2.0"),
    ("report07_f_rev", "repo", "benchmark/report07_three_engine_maps.py", 92, "f_rev = rpm0 / 60.0"),
    ("report07_f_tip_cos_el", "repo", "benchmark/report07_three_engine_maps.py", 94,
     "f_tip = 2.0 * (2 * np.pi * f_rev * R) / lam * np.cos(np.radians(a.el))"),
    ("report07_meta_el", "repo", "benchmark/report07_three_engine_maps.py", 187,
     '"az_deg": a.az, "el_deg": a.el, "range_m": a.range,'),
    ("report07_hover_long_f_tip_cos_el", "repo", "benchmark/report07_hover_long.py", 130,
     "f_tip = 2.0 * (2 * np.pi * f_rev * R) / lam * np.cos(np.radians(a.el))"),
    ("kernel_bbox_centre", "repo", "src/rcs_sbr.py", 1051, "ctr = 0.5 * (V.max(0) + V.min(0))"),
    ("kernel_plane_phase_reference", "repo", "src/rcs_sbr.py", 1194, "ph = np.exp(1j * 2.0 * k * ((P - ctr) @ u))"),
    ("kernel_spherical_phase_tx", "repo", "src/rcs_sbr.py", 1196, "p_tx = ctr + float(range_m) * np.asarray(u, float)"),
    ("kernel_spherical_phase", "repo", "src/rcs_sbr.py", 1200, "(float(range_m) - np.linalg.norm(P - p_tx, axis=1)))"),
]


# --------------------------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------------------------- #
def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sionna_pkg_dir() -> Path:
    spec = find_spec("sionna")
    return Path(spec.origin).resolve().parent


def sanitized_argv() -> list:
    """argv with paths shown relative to ROOT, or as <outside-root>/<name>, so no host path lands in the ledger."""
    out = []
    for a in sys.argv[1:]:
        if os.path.isabs(a):
            pa = Path(a).resolve()
            try:
                out.append(str(pa.relative_to(ROOT)) or ".")
            except ValueError:
                out.append(f"<outside-root>/{pa.name}")
        else:
            out.append(a)
    return out


LEDGER: dict = {}
T_START = time.time()


def checkpoint(section: str | None = None) -> None:
    if section:
        LEDGER["_meta"]["sections_done"].append({"section": section, "elapsed_s": round(time.time() - T_START, 3)})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(OUT.suffix + ".partial")
    tmp.write_text(json.dumps(LEDGER, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    tmp.replace(OUT)
    print(f"[checkpoint] {section} -> {OUT}", flush=True)


def add_hash(key: str, p: Path) -> str:
    h = sha256_file(p)
    LEDGER["_meta"]["source_hashes"][key] = h
    return h


def verify_quotes() -> dict:
    """Open each file and check the quoted text on the given line.

    If the quote moved, the nearest occurrence is recorded; a moved quote counts as verified only when it
    occurs exactly once in the file (otherwise a different statement could be matched)."""
    out = {}
    sdir = sionna_pkg_dir()
    for qid, kind, rel, line, quote in QUOTES:
        if kind == "sionna":
            p = sdir / rel
            key = f"installed:sionna/{rel}"
        else:
            p = ROOT / rel
            key = rel
        lines = p.read_text(encoding="utf-8").splitlines()
        at_line = 1 <= line <= len(lines) and quote in lines[line - 1]
        found = [i + 1 for i, s in enumerate(lines) if quote in s]
        actual = line if at_line else (min(found, key=lambda x: abs(x - line)) if found else None)
        out[qid] = {"id": qid, "path": key, "line": actual, "expected_line": line, "quote": quote,
                    "verified": bool(at_line or len(found) == 1),
                    "relocated": (actual is not None and not at_line),
                    "occurrences": len(found), "sha256": add_hash(key, p)}
    return out


def f3(v) -> list:
    """Plain Python floats for Mitsuba constructors (they reject numpy float64)."""
    return [float(x) for x in v]


def cx(t) -> np.ndarray:
    return np.asarray(t[0]) + 1j * np.asarray(t[1])


def phase_slope_hz(h: np.ndarray, fs: float) -> float:
    u = np.unwrap(np.angle(h))
    return float(np.polyfit(np.arange(len(h)) / fs, u, 1)[0] / (2 * np.pi))


# --------------------------------------------------------------------------------------------- #
# Section: cost from production shards (no solver import needed)
# --------------------------------------------------------------------------------------------- #
def section_cost(Q: dict) -> None:
    from arm_grammar import ArmNameError, parse
    add_hash("src/arm_grammar.py", ROOT / "src" / "arm_grammar.py")
    cc = CONFIG["cost"]
    shd = ROOT / cc["shard_dir"]
    name_re = re.compile(r"^(?P<arm>.*)_el(?P<el>[+-]?[\d.]+)_(?P<shard>\d+)\.npz$")
    ps_groups: dict = {}
    k_group: list = []
    skipped = {"name_shape": 0, "grammar": 0, "unreadable": 0}
    base_ps = cc["pathsolver_base_fields"]
    base_k = cc["kernel_base_fields"]
    for f in sorted(shd.glob("*.npz")):
        m = name_re.match(f.name)
        if not m:
            skipped["name_shape"] += 1
            continue
        arm = m.group("arm")
        if not (arm.startswith("sionna") or arm.startswith("ours")):
            continue
        try:
            fields = parse(arm)
        except ArmNameError:
            skipped["grammar"] += 1
            continue
        is_ps = all(fields.get(k) == v for k, v in base_ps.items()) and \
            set(fields) <= set(base_ps) | set(cc["allowed_extra_fields"])
        is_k = fields == base_k
        if not (is_ps or is_k):
            continue
        try:
            with np.load(f, allow_pickle=False) as z:
                meta = np.asarray(z["meta"], float)
                n_idx = int(z["idx"].size)
                npaths = np.asarray(z["npaths"]) if "npaths" in z.files else None
                cfg = np.asarray(z["cfg"], float) if "cfg" in z.files else None
                sb = str(z["solver_build"]) if "solver_build" in z.files else None
                ntr = np.asarray(z["n_trunc"]).tolist() if "n_trunc" in z.files else None
        except Exception:  # noqa: BLE001 - a shard being written by the live queue
            skipped["unreadable"] += 1
            continue
        rel = str(f.relative_to(ROOT))
        add_hash(rel, f)
        rec = {"file": f.name, "el_deg": float(meta[0]), "s_per_pose": float(meta[5]) / n_idx,
               "n_poses_in_shard": n_idx, "meta_spp": (float(meta[6]) if meta.size > 6 else None),
               "cfg_depth": (float(cfg[1]) if cfg is not None and cfg.size > 1 and np.isfinite(cfg[1]) else None),
               "median_paths": (float(np.median(npaths)) if npaths is not None else None),
               "solver_build_stamp": sb, "n_trunc": ntr}
        if is_ps:
            build = "rt210" if fields.get("solver_build") == "210" else (
                "2.0.1" if "solver_build" not in fields else f"rt{fields['solver_build']}")
            scene = fields.get("env", "free_sky")
            depth = int(fields["max_depth"])
            if rec["meta_spp"] is None or rec["meta_spp"] != float(base_ps["spp"]):
                skipped.setdefault("meta_spp_mismatch", 0)
                skipped["meta_spp_mismatch"] += 1
                continue
            if rec["cfg_depth"] is not None and int(rec["cfg_depth"]) != depth:
                skipped.setdefault("depth_mismatch", 0)
                skipped["depth_mismatch"] += 1
                continue
            ps_groups.setdefault((scene, build, depth, int(base_ps["spp"])), []).append((arm, rec))
        else:
            k_group.append((arm, rec))

    def summarise(key, recs):
        scene, build, depth, spp = key
        s = np.array([r["s_per_pose"] for _, r in recs])
        mp = [r["median_paths"] for _, r in recs if r["median_paths"] is not None]
        stamps = sorted({str(r["solver_build_stamp"]) for _, r in recs})
        trunc = [r["n_trunc"][0] for _, r in recs if r["n_trunc"] is not None]
        return {"scene": scene, "build": build, "depth": depth, "spp": spp, "n_shards": int(s.size),
                "median_s_per_pose": float(np.median(s)), "min_s_per_pose": float(s.min()),
                "max_s_per_pose": float(s.max()), "median_paths": (float(np.median(mp)) if mp else None),
                "elevations_deg": sorted({r["el_deg"] for _, r in recs}),
                "poses_per_shard": sorted({r["n_poses_in_shard"] for _, r in recs}),
                "arm": sorted({a for a, _ in recs}),
                "solver_build_stamps": stamps,
                "shards_with_truncated_poses": int(sum(1 for t in trunc if t)),
                "files": sorted(r["file"] for _, r in recs)}

    order = sorted(ps_groups, key=lambda k: (k[0] != "free_sky", k[0], k[1] != "rt210", k[2]))
    rows = [summarise(k, ps_groups[k]) for k in order if k[2] == cc["production_depth"]]
    other = [summarise(k, ps_groups[k]) for k in order if k[2] != cc["production_depth"]]
    traj = []
    for r in rows:
        if r["build"] != "rt210":
            continue
        for rate in cc["trajectory_rates_hz"]:
            n = rate * cc["trajectory_duration_s"]
            traj.append({"scene": r["scene"], "build": r["build"], "depth": r["depth"], "rate_hz": rate,
                         "duration_s": cc["trajectory_duration_s"], "n_snapshots": int(round(n)),
                         "median_s_per_pose_used": r["median_s_per_pose"], "n_shards_behind": r["n_shards"],
                         "single_process_wall_hours": n * r["median_s_per_pose"] / 3600.0,
                         "unit": "single-process wall-hours measured under shared-card conditions"})
    ks = np.array([r["s_per_pose"] for _, r in k_group]) if k_group else np.array([])
    kernel_cost = {"arm": sorted({a for a, _ in k_group}), "n_shards": int(ks.size),
                   "median_s_per_pose": (float(np.median(ks)) if ks.size else None),
                   "min_s_per_pose": (float(ks.min()) if ks.size else None),
                   "max_s_per_pose": (float(ks.max()) if ks.size else None),
                   "elevations_deg": sorted({r["el_deg"] for _, r in k_group}),
                   "device": "not recorded in the shard",
                   "timer_quote": Q["sweep_kernel_timer_start"], "meta_quotes": [Q["sweep_kernel_meta_head"],
                                                                                 Q["sweep_kernel_meta_tail"]]}
    # Is the per-pose scene rebuild inside the timed region? Check order and indentation of verified lines.
    src = (ROOT / "benchmark/elevation_sweep_md.py").read_text(encoding="utf-8").splitlines()

    def indent(q):
        ln = Q[q]["line"]
        return len(src[ln - 1]) - len(src[ln - 1].lstrip()) if ln else None

    lt, ll, lb1, lb2, lm = (Q[q]["line"] for q in ("sweep_timer_start", "sweep_pose_loop",
                                                    "sweep_scene_builtin_rebuild", "sweep_scene_rebuild",
                                                    "sweep_meta_layout_head"))
    between = [i + 1 for i in range(lt, lm - 1) if re.search(r"\bt0\s*=", src[i])] if all((lt, lm)) else None
    inside = bool(all((lt, ll, lb1, lb2, lm)) and lt < ll < lb1 < lm and lt < ll < lb2 < lm
                  and indent("sweep_scene_rebuild") > indent("sweep_pose_loop")
                  and indent("sweep_scene_builtin_rebuild") > indent("sweep_pose_loop") and not between)
    LEDGER["cost"] = {
        "label": "PathSolver wall time per pose from production shards: meta[5] / n_poses",
        "unit_note": "single-process wall time measured under shared-card conditions; device id and concurrency "
                     "are not recorded in the shards",
        "meta_layout": {"layout": ["el_deg", "shard", "nshards", "n_poses_total", "prf_hz", "elapsed_s", "spp"],
                        "elapsed_index": 5, "quotes": [Q["sweep_meta_layout_head"], Q["sweep_meta_layout_tail"]]},
        "timer_includes_scene_rebuild": inside,
        "comparability_note": "Build-to-build wall-time differences do not measure solver speed: the builds were run "
                              "at different elevation sets (rows[].elevations_deg), at different times and code "
                              "revisions (the 2.0.1 shards predate later changes to the sweep script), and under "
                              "unrecorded card sharing.",
        "live_directory_note": "Rows are recomputed from the shard directory at run time; n_shards and the medians "
                               "move when new shards land.",
        "row_selector_note": "A row is identified by scene AND build (and depth); rows[scene=...] alone can match "
                             "several rows.",
        "timer_quotes": [Q["sweep_timer_start"], Q["sweep_pose_loop"], Q["sweep_scene_builtin_rebuild"],
                         Q["sweep_scene_rebuild"]],
        "t0_reassignments_between_timer_and_meta": between,
        "build_naming_quotes": [Q["sweep_build_baseline"], Q["sweep_build_tag_empty_for_baseline"],
                                Q["sweep_build_baseline_caveat"]],
        "shared_conditions_quote": Q["supervisor_workers_per_card_tiers"],
        "selection": {"pathsolver_base_fields": CONFIG["cost"]["pathsolver_base_fields"],
                      "allowed_extra_fields": CONFIG["cost"]["allowed_extra_fields"],
                      "names_parsed_with": "src/arm_grammar.py parse()",
                      "build_rule": "name has solver_build 210 -> rt210; name without a build tag -> 2.0.1 "
                                    "(baseline naming rule, see build_naming_quotes)",
                      "skipped": skipped},
        "rows": rows,
        "other_depth_rows": other,
        "trajectory_rows": traj,
        "kernel_cost": kernel_cost,
    }
    reg = ROOT / "runners" / "SOLVER_BUILDS.json"
    if reg.exists():
        LEDGER["cost"]["build_registry"] = {"path": "runners/SOLVER_BUILDS.json",
                                            "builds": json.loads(reg.read_text(encoding="utf-8")).get("builds"),
                                            "sha256": add_hash("runners/SOLVER_BUILDS.json", reg)}


# --------------------------------------------------------------------------------------------- #
# Section: rotor settings and required pose rate
# --------------------------------------------------------------------------------------------- #
def section_rotor(Q: dict) -> None:
    from drones import DRONES
    add_hash("src/drones.py", ROOT / "src" / "drones.py")
    p = ROOT / "outputs" / "report07_three_engines.json"
    meta = json.loads(p.read_text(encoding="utf-8"))["_meta"]
    add_hash("outputs/report07_three_engines.json", p)
    rpm = np.asarray(meta["rpm_per_rotor"], float)
    fc_meta = float(meta["fc_hz"])
    fc = CONFIG["fc_hz"]
    lam = C0 / fc
    f_tip = float(meta["f_tip_hz"])
    el_src = float(meta["el_deg"])
    az_src = float(meta["az_deg"])
    cos_el = float(np.cos(np.radians(el_src)))

    # The generator of the source ledger computes f_tip with a cos(elevation) factor and its own
    # wavelength constant (verified quotes report07_*). Read that constant from the verified line.
    src_lines = (ROOT / "benchmark" / "report07_three_engine_maps.py").read_text(encoding="utf-8").splitlines()
    wl_line = src_lines[Q["report07_wavelength"]["line"] - 1] if Q["report07_wavelength"]["verified"] else ""
    m = re.search(r"lam\s*=\s*([0-9.]+(?:[eE][+-]?[0-9]+)?)\s*/\s*FC", wl_line)
    c_src = float(m.group(1)) if m else None
    lam_src = (c_src / fc_meta) if c_src else None

    spec = DRONES[meta["drone"]]
    rpm0 = float(spec.hover_rpm)
    radius_spec = float(spec.prop_dia_mm) / 1000.0 / 2.0
    omega0 = 2 * np.pi * rpm0 / 60.0
    f_tip_rep = (2.0 * (omega0 * radius_spec) / lam_src * cos_el) if lam_src else None
    f_flash_rep = float(spec.prop_blades) * rpm0 / 60.0

    f_tip_el0 = f_tip / cos_el
    v_tip_los_src = (f_tip * lam_src / 2.0) if lam_src else None
    v_tip = (f_tip * lam_src / (2.0 * cos_el)) if lam_src else None
    v_tip_exact_c = f_tip * lam / (2.0 * cos_el)
    look = f"source look: el_deg={el_src:g}, az_deg={az_src:g} (outputs/report07_three_engines.json _meta)"

    rows_rot = []
    for rate in CONFIG["rotor"]["pose_rates_hz"]:
        dmean = float(360.0 * rpm.mean() / 60.0 / rate)
        rows_rot.append({"rate_hz": rate,
                         "rotation_per_sample_deg": dmean,
                         "deg_per_sample_mean_rpm": dmean,
                         "deg_per_sample_max_rpm": float(360.0 * rpm.max() / 60.0 / rate),
                         "tip_doppler_within_two_sided_band_at_source_look": bool(rate >= 2.0 * f_tip),
                         "tip_doppler_within_two_sided_band_at_el0": bool(rate >= 2.0 * f_tip_el0)})
    rows_req, rows_req0 = [], []
    for v in CONFIG["rotor"]["body_speeds_mps"]:
        fb = 2.0 * v / lam
        rows_req.append({"body_speed_mps": v, "f_body_hz": fb, "f_tip_hz": f_tip, "f_tip_basis": look,
                         "required_rate_hz": 2.0 * (f_tip + fb)})
        rows_req0.append({"body_speed_mps": v, "f_body_hz": fb, "f_tip_el0_hz": f_tip_el0,
                          "f_tip_basis": "source formula at el_deg=0: f_tip_hz / cos(el_deg of source)",
                          "required_rate_hz": 2.0 * (f_tip_el0 + fb)})
    LEDGER["rotor"] = {
        "rpm_per_rotor": rpm.tolist(), "rpm_mean": float(rpm.mean()),
        "f_flash_hz": float(meta["f_flash_hz"]), "f_tip_hz": f_tip,
        "f_tip_hz_meaning": "line-of-sight blade-tip Doppler at the source look (includes cos(el_deg)); not the "
                            "full tip Doppler at every elevation",
        "source_el_deg": el_src, "source_az_deg": az_src, "source_cos_el": cos_el,
        "fc_hz_in_source": fc_meta, "prf_hz_in_source": float(meta["prf_hz"]), "drone_in_source": meta.get("drone"),
        "fc_matches_config": bool(fc_meta == fc),
        "source": {"path": "outputs/report07_three_engines.json",
                   "keys": ["_meta.rpm_per_rotor", "_meta.f_flash_hz", "_meta.f_tip_hz", "_meta.fc_hz",
                            "_meta.prf_hz", "_meta.el_deg", "_meta.az_deg", "_meta.drone"],
                   "generator_quotes": [Q["report07_ledger_path"], Q["report07_rpm0_hover"], Q["report07_wavelength"],
                                        Q["report07_radius"], Q["report07_f_rev"], Q["report07_f_tip_cos_el"],
                                        Q["report07_meta_el"]],
                   "same_formula_elsewhere_quote": Q["report07_hover_long_f_tip_cos_el"]},
        "source_formula_check": {
            "drone_spec_from": "src/drones.py DRONES[_meta.drone]",
            "hover_rpm": rpm0, "prop_dia_mm": float(spec.prop_dia_mm), "prop_blades": int(spec.prop_blades),
            "speed_of_light_constant_in_source_line": c_src,
            "source_wavelength_m": lam_src, "config_wavelength_m_exact_c": lam,
            "wavelength_rel_diff_source_vs_exact_c": ((lam_src - lam) / lam) if lam_src else None,
            "f_tip_hz_reproduced": f_tip_rep,
            "f_tip_reproduction_rel_err": (abs(f_tip_rep - f_tip) / f_tip) if f_tip_rep else None,
            "f_flash_hz_reproduced": f_flash_rep,
            "f_flash_reproduction_rel_err": abs(f_flash_rep - float(meta["f_flash_hz"])) / float(meta["f_flash_hz"]),
        },
        "f_tip_el0_hz": f_tip_el0,
        "tip_speed_los_component_at_source_look_mps": v_tip_los_src,
        "implied_tip_speed_mps": v_tip,
        "implied_tip_speed_mps_if_exact_c": v_tip_exact_c,
        "implied_tip_radius_m": (float(v_tip / omega0) if v_tip else None),
        "spec_prop_radius_m": radius_spec,
        "implied_tip_radius_rel_diff_vs_spec": ((v_tip / omega0 - radius_spec) / radius_spec) if v_tip else None,
        "rotation_deg_per_s_mean_rpm": float(360.0 * rpm.mean() / 60.0),
        "rotation_per_sample_deg": rows_rot,
        "required_pose_rate": rows_req,
        "required_pose_rate_el0": rows_req0,
        "required_rate_rule": "2*(f_tip + f_body), f_body = 2 v / lambda (monostatic, radial speed), lambda = c / fc. "
                              "required_pose_rate uses f_tip_hz at the source look only (el_deg and az_deg above); "
                              "required_pose_rate_el0 uses f_tip_hz / cos(el_deg), what the source formula gives at "
                              "el_deg = 0. f_body uses exact c while f_tip used the source wavelength constant "
                              "(see source_formula_check.wavelength_rel_diff_source_vs_exact_c).",
    }


# --------------------------------------------------------------------------------------------- #
# Section: PathSolver contract, Doppler, extrapolation (CPU)
# --------------------------------------------------------------------------------------------- #
def section_rt(Q: dict) -> None:
    import drjit as dr
    import mitsuba as mi
    import sionna.rt as rt
    LEDGER["_meta"]["mitsuba_variant"] = mi.variant()
    for scn in ("simple_reflector", "simple_street_canyon"):
        sdir_ = sionna_pkg_dir() / "rt" / "scenes" / scn
        for fpath in sorted(sdir_.rglob("*")):
            if fpath.is_file():
                add_hash(f"installed:sionna/{fpath.relative_to(sionna_pkg_dir())}", fpath)
    fc = CONFIG["fc_hz"]
    lam = C0 / fc
    seed = CONFIG["pathsolver_seed"]
    iso = dict(pattern="iso", polarization="V")

    # ---------------- contract ----------------
    cp = CONFIG["contract_probe"]
    res = {}
    for synth in (True, False):
        sc = rt.load_scene(rt.scene.simple_street_canyon)
        sc.frequency = fc
        sc.tx_array = rt.PlanarArray(num_rows=1, num_cols=1, **iso)
        sc.rx_array = rt.PlanarArray(num_rows=cp["rx_array_rows_cols"][0], num_cols=cp["rx_array_rows_cols"][1], **iso)
        sc.add(rt.Transmitter("tx", position=mi.Point3f(*cp["tx_pos_m"])))
        sc.add(rt.Receiver("rx", position=mi.Point3f(*cp["rx_pos_m"])))
        p = rt.PathSolver(deterministic=cp["deterministic"])(
            sc, max_depth=cp["max_depth"], samples_per_src=cp["samples_per_src"], synthetic_array=synth,
            los=True, specular_reflection=True, diffuse_reflection=False, seed=seed)
        a = cx(p.a)
        tau = np.asarray(p.tau, dtype=np.float64)
        ar, ai = np.asarray(p.a[0]), np.asarray(p.a[1])
        unpack = (ar + 1j * ai).reshape(-1, ar.shape[-1])[0]    # same expression as report15_probe.unpack
        ab, _ = p.cir(normalize_delays=False, out_type="numpy")
        abn, taun = p.cir(normalize_delays=True, out_type="numpy")
        ab, abn = np.asarray(ab)[..., 0], np.asarray(abn)[..., 0]
        valid = np.asarray(p.valid)
        if synth:
            valid = np.broadcast_to(valid[:, None, :, None, :], a.shape)
            taus = tau[:, None, :, None, :]
        else:
            taus = tau
        man = a * np.exp(-2j * np.pi * fc * taus)
        ratio = (abn / ab)[valid]
        ph = np.degrees(np.angle(ratio))
        min_tau = float(np.min(tau[tau > 0]))
        H = p.cfr(frequencies=mi.Float(np.asarray(cp["cfr_offsets_hz"], float)), normalize_delays=False, out_type="numpy")
        res[synth] = dict(
            a_shape=list(a.shape), tau_shape=list(tau.shape), doppler_shape=list(np.asarray(p.doppler).shape),
            theta_r_shape=list(np.asarray(p.theta_r).shape), unpack_len=int(unpack.shape[0]), a_size=int(a.size),
            cir_shape=list(np.asarray(p.cir(normalize_delays=False, out_type="numpy")[0]).shape),
            cfr_shape=list(np.asarray(H).shape),
            rx_ant_coeff_maxdiff=float(np.abs(a[:, 0] - a[:, 1]).max()),
            manual_vs_cir_rel_err=float(np.linalg.norm((ab - man)[valid]) / np.linalg.norm(man[valid])),
            min_tau_ns=min_tau * 1e9, normalized_min_tau_s=float(np.min(np.asarray(taun)[np.asarray(taun) >= 0])),
            phase_med=float(np.median(ph)), phase_min=float(ph.min()), phase_max=float(ph.max()),
            phase_expected=float(np.degrees(np.angle(np.exp(2j * np.pi * fc * min_tau)))),
            a_imag_max_abs=float(np.abs(a.imag).max()), a_real_max_abs=float(np.abs(a.real).max()))
    rs, rn = res[True], res[False]
    chord = float(abs(1 - np.exp(1j * np.radians(rs["phase_med"]))))
    ikr = ROOT / "outputs" / "isac_kernel_review_0915.json"
    ikr_val = None
    if ikr.exists():
        ikr_val = json.loads(ikr.read_text(encoding="utf-8")).get("checks", {}).get("pathsolver_cir", {}).get(
            "normalized_vs_absolute_relative_l2")
        add_hash("outputs/isac_kernel_review_0915.json", ikr)

    ap = CONFIG["angle_probe"]
    sc = rt.load_scene()
    sc.frequency = fc
    sc.tx_array = rt.PlanarArray(num_rows=1, num_cols=1, **iso)
    sc.rx_array = sc.tx_array
    sc.add(rt.Transmitter("tx", position=mi.Point3f(*ap["tx_pos_m"]), orientation=mi.Point3f(*ap["tx_orientation_rad"])))
    sc.add(rt.Receiver("rx", position=mi.Point3f(*ap["rx_pos_m"]), orientation=mi.Point3f(*ap["rx_orientation_rad"])))
    p = rt.PathSolver()(sc, max_depth=ap["max_depth"], samples_per_src=ap["samples_per_src"], seed=seed)
    d = np.asarray(ap["rx_pos_m"]) - np.asarray(ap["tx_pos_m"])
    rng = float(np.linalg.norm(d))
    ang = dict(theta_t_deg=float(np.degrees(np.asarray(p.theta_t).ravel()[0])),
               phi_t_deg=float(np.degrees(np.asarray(p.phi_t).ravel()[0])),
               theta_r_deg=float(np.degrees(np.asarray(p.theta_r).ravel()[0])),
               phi_r_deg=float(np.degrees(np.asarray(p.phi_r).ravel()[0])),
               expected_theta_t_deg=float(np.degrees(np.arccos(d[2] / rng))),
               expected_phi_t_deg=float(np.degrees(np.arctan2(d[1], d[0]))),
               expected_theta_r_deg=float(np.degrees(np.arccos(-d[2] / rng))),
               expected_phi_r_deg=float(np.degrees(np.arctan2(-d[1], -d[0]))),
               tx_orientation_rad=ap["tx_orientation_rad"], rx_orientation_rad=ap["rx_orientation_rad"],
               note="Devices have non-zero orientations; expected values are global-frame directions "
                    "(tx->rx for departure, rx->tx for arrival).")
    LEDGER["rt_contract"] = {
        "probe": {k: v for k, v in cp.items()},
        "a_shape": rs["a_shape"], "a_shape_nonsynthetic": rn["a_shape"],
        "a_axes": ["num_rx", "num_rx_ant", "num_tx", "num_tx_ant", "num_paths"],
        "tau_shape_synthetic": rs["tau_shape"], "tau_shape_nonsynthetic": rn["tau_shape"],
        "doppler_shape_synthetic": rs["doppler_shape"], "doppler_shape_nonsynthetic": rn["doppler_shape"],
        "cir_shape": rs["cir_shape"], "cfr_shape_three_frequencies": rs["cfr_shape"],
        "unpack_style_reshape_len": rs["unpack_len"],
        "unpack_style_kept_fraction_of_coefficients": rs["unpack_len"] / rs["a_size"],
        "unpack_style_quotes": [Q["report15_unpack_reshape"], Q["report15_unpack_1x1_docstring"]],
        "rx_antenna_coefficient_max_abs_difference": rs["rx_ant_coeff_maxdiff"],
        "manual_a_exp_minus_j2pi_f_tau_vs_cir_rel_err": rs["manual_vs_cir_rel_err"],
        "a_imag_max_abs": rs["a_imag_max_abs"], "a_real_max_abs": rs["a_real_max_abs"],
        "normalize_delays": {
            "min_tau_ns": rs["min_tau_ns"], "normalized_min_tau_s": rs["normalized_min_tau_s"],
            "phase_rotation_deg_measured": rs["phase_med"],
            "phase_rotation_deg_measured_min": rs["phase_min"], "phase_rotation_deg_measured_max": rs["phase_max"],
            "phase_rotation_deg_expected": rs["phase_expected"],
            "common_phase_chord_abs_1_minus_exp_j_phase": chord,
            "pointer_isac_kernel_review": {"key": "outputs/isac_kernel_review_0915.json:checks.pathsolver_cir."
                                                  "normalized_vs_absolute_relative_l2", "value": ikr_val},
            "nonsynthetic_phase_rotation_deg_measured": rn["phase_med"],
            "nonsynthetic_phase_rotation_deg_expected": rn["phase_expected"],
            "quotes": [Q["paths_normalize_synthetic_min"], Q["paths_normalize_subtract"]],
        },
        "receivers_share_rx_array_quote": Q["paths_rx_array_shared"],
        "transmitters_share_tx_array_quote": Q["paths_tx_array_shared"],
        "synthetic_array_default_quote": Q["path_solver_synthetic_default"],
        "angles_global_frame": ang,
    }
    checkpoint("rt_contract")

    # ---------------- Doppler ----------------
    dp = CONFIG["doppler_probe"]
    ts = CONFIG["time_steps"]

    def mk_reflector():
        s = rt.load_scene(rt.scene.simple_reflector)
        s.frequency = fc
        s.tx_array = rt.PlanarArray(num_rows=1, num_cols=1, **iso)
        s.rx_array = s.tx_array
        s.add(rt.Transmitter("tx", position=mi.Point3f(*dp["tx_pos_m"])))
        s.add(rt.Receiver("rx", position=mi.Point3f(*dp["rx_pos_m"])))
        return s, list(s.objects.values())[0]

    def solve_reflector(s):
        return rt.PathSolver(deterministic=dp["deterministic"])(
            s, max_depth=dp["max_depth"], samples_per_src=dp["samples_per_src"], los=dp["los"],
            specular_reflection=True, diffuse_reflection=dp["diffuse"], synthetic_array=True, seed=seed)

    sc, obj = mk_reflector()
    bb = obj.mi_mesh.bbox()
    bbmin = [float(dr.ravel(c)[0]) if hasattr(c, "__len__") else float(c) for c in (bb.min.x, bb.min.y, bb.min.z)]
    bbmax = [float(dr.ravel(c)[0]) if hasattr(c, "__len__") else float(c) for c in (bb.max.x, bb.max.y, bb.max.z)]
    vel = np.asarray(dp["object_velocity_mps"], float)
    obj.velocity = mi.Vector3f(*f3(vel))
    p = solve_reflector(sc)
    dop = np.asarray(p.doppler).ravel()
    try:
        obj.velocity = mi.Vector3f(*dp["second_velocity_test_xyz_components"])
        second_err = "accepted"
    except Exception as e:  # noqa: BLE001
        second_err = f"{type(e).__name__}: {e}"
    obj.velocity = mi.Vector3f(*f3(vel))
    fs, N = ts["sampling_frequency_hz"], ts["num_time_steps"]
    ab, _ = p.cir(sampling_frequency=fs, num_time_steps=N, normalize_delays=False, out_type="numpy")
    abn, _ = p.cir(sampling_frequency=fs, num_time_steps=N, normalize_delays=True, out_type="numpy")
    h_ext = np.asarray(ab).reshape(-1, N).sum(0)
    h_extn = np.asarray(abn).reshape(-1, N).sum(0)
    # separate re-traces with the plate moved by v*t
    sc2, o2 = mk_reflector()
    c0 = o2.position
    c0 = [float(dr.ravel(c)[0]) if hasattr(c, "__len__") else float(c) for c in (c0.x, c0.y, c0.z)]
    h_snap, h_snapn = [], []
    for n in range(N):
        t = n / fs
        o2.position = mi.Point3f(*f3(np.asarray(c0) + vel * t))
        q = solve_reflector(sc2)
        aa, _ = q.cir(normalize_delays=False, out_type="numpy")
        h_snap.append(np.asarray(aa).sum())
        aan, _ = q.cir(normalize_delays=True, out_type="numpy")
        h_snapn.append(np.asarray(aan).sum())
    h_snap, h_snapn = np.array(h_snap), np.array(h_snapn)

    tv = CONFIG["txrx_velocity_probe"]
    sc4 = rt.load_scene()
    sc4.frequency = fc
    sc4.tx_array = rt.PlanarArray(num_rows=1, num_cols=1, **iso)
    sc4.rx_array = sc4.tx_array
    sc4.add(rt.Transmitter("tx", position=mi.Point3f(*tv["tx_pos_m"]), velocity=mi.Vector3f(*tv["tx_velocity_mps"])))
    sc4.add(rt.Receiver("rx", position=mi.Point3f(*tv["rx_pos_m"]), velocity=mi.Vector3f(*tv["rx_velocity_mps"])))
    q = rt.PathSolver()(sc4, max_depth=tv["max_depth"], samples_per_src=tv["samples_per_src"], seed=seed)
    los_dir = np.asarray(tv["rx_pos_m"]) - np.asarray(tv["tx_pos_m"])
    los_dir = los_dir / np.linalg.norm(los_dir)
    txrx_expected = float((np.dot(tv["tx_velocity_mps"], los_dir) - np.dot(tv["rx_velocity_mps"], los_dir)) / lam)

    # per-object velocities in the street canyon
    po = CONFIG["per_object_probe"]
    sc5 = rt.load_scene(rt.scene.simple_street_canyon)
    sc5.frequency = fc
    sc5.tx_array = rt.PlanarArray(num_rows=1, num_cols=1, **iso)
    sc5.rx_array = sc5.tx_array
    sc5.add(rt.Transmitter("tx", position=mi.Point3f(*po["tx_pos_m"])))
    sc5.add(rt.Receiver("rx", position=mi.Point3f(*po["rx_pos_m"])))
    vel_of = {}
    id2name = {}
    centre_of = {}
    rank_of = {}
    for nm, o in sc5.objects.items():
        bb = o.mi_mesh.bbox()
        cen = [float(np.round(0.5 * (float(dr.ravel(lo)[0] if hasattr(lo, "__len__") else lo) +
                                     float(dr.ravel(hi)[0] if hasattr(hi, "__len__") else hi)),
                              po["bbox_round_decimals"]))
               for lo, hi in ((bb.min.x, bb.max.x), (bb.min.y, bb.max.y), (bb.min.z, bb.max.z))]
        centre_of[nm] = cen
    for i, nm in enumerate(sorted(centre_of, key=lambda n: tuple(centre_of[n]))):
        o = sc5.objects[nm]
        v = po["velocity_step_mps"] * (i + 1) * np.ones(3)
        o.velocity = mi.Vector3f(*f3(v))
        vel_of[nm] = v
        rank_of[nm] = i
        id2name[int(o.object_id)] = nm
    p5 = rt.PathSolver(deterministic=po["deterministic"])(
        sc5, max_depth=po["max_depth"], samples_per_src=po["samples_per_src"], los=po["los"],
        specular_reflection=True, diffuse_reflection=False, seed=seed)
    d5 = np.asarray(p5.doppler)            # [rx, tx, paths]
    O5 = np.asarray(p5.objects)            # [depth, rx, tx, paths]
    V5 = np.asarray(p5.vertices)           # [depth, rx, tx, paths, 3]
    val5 = np.asarray(p5.valid)
    txp, rxp = np.asarray(po["tx_pos_m"]), np.asarray(po["rx_pos_m"])
    by_obj: dict = {}
    for k in range(d5.shape[-1]):
        if not bool(val5[0, 0, k]):
            continue
        oid = int(O5[0, 0, 0, k])
        nm = id2name.get(oid)
        vtx = V5[0, 0, 0, k].astype(float)
        ki = (vtx - txp) / np.linalg.norm(vtx - txp)
        ko = (rxp - vtx) / np.linalg.norm(rxp - vtx)
        exp_hz = float(np.dot(ko - ki, vel_of[nm]) / lam) if nm is not None else None
        by_obj.setdefault(nm if nm is not None else f"unmapped_id_{oid}", []).append((float(d5[0, 0, k]), exp_hz))
    per_obj = []
    for nm in sorted(by_obj, key=str):
        vals = by_obj[nm]
        dd = np.array([v[0] for v in vals])
        ee = [v[1] for v in vals if v[1] is not None]
        per_obj.append({"object": nm, "velocity_mps": (vel_of[nm].tolist() if nm in vel_of else None),
                        "object_rank_by_bbox_centre": rank_of.get(nm), "bbox_centre_m": centre_of.get(nm),
                        "n_paths": len(vals), "doppler_hz": float(np.median(dd)),
                        "doppler_hz_min": float(dd.min()), "doppler_hz_max": float(dd.max()),
                        "expected_doppler_hz_from_vertices": (float(np.median(ee)) if ee else None),
                        "max_abs_error_hz": (float(np.max(np.abs(dd - np.array(ee)))) if len(ee) == len(dd) else None)})
    a1, _ = p5.cir(sampling_frequency=fs, num_time_steps=N, normalize_delays=True, out_type="numpy")
    a0, _ = p5.cir(sampling_frequency=fs, num_time_steps=N, normalize_delays=False, out_type="numpy")
    a1, a0 = np.asarray(a1), np.asarray(a0)
    nz = np.abs(a0[..., 0]) > 0
    rphase = np.unwrap(np.angle(a1 / np.where(a0 == 0, 1, a0)), axis=-1)
    spread = float(np.degrees(np.ptp(rphase, axis=-1))[nz].max()) if nz.any() else None

    LEDGER["rt_doppler"] = {
        "probe": dp, "reflector_bbox_m": {"min": bbmin, "max": bbmax},
        "object_velocity_mps": vel.tolist(),
        "object_speed_toward_radar_mps": float(np.linalg.norm(vel)),
        "n_paths": int(dop.size),
        "doppler_hz_measured": float(dop[0]),
        "doppler_hz_expected_2v_over_lambda": float(2 * np.linalg.norm(vel) / lam),
        "txrx_velocity_probe": tv,
        "txrx_velocity_case_hz": float(np.asarray(q.doppler).ravel()[0]),
        "txrx_expected_hz": txrx_expected,
        "second_velocity_error_message": second_err,
        "second_velocity_quote": Q["scene_object_single_velocity"],
        "object_doppler_quote": Q["field_calculator_object_doppler"],
        "per_object_probe": {k: v for k, v in po.items()},
        "per_object_n_objects_with_velocity": len(vel_of),
        "per_object_velocities": per_obj,
        "per_object_objects_with_velocity_on_no_valid_path": [
            {"object": nm, "object_rank_by_bbox_centre": rank_of[nm], "bbox_centre_m": centre_of[nm],
             "velocity_mps": vel_of[nm].tolist()} for nm in sorted(set(vel_of) - set(by_obj), key=lambda n: rank_of[n])],
        "per_object_name_note": "Object names are the scene's object names; names such as no-name-5 are assigned "
                                "automatically by Sionna when the scene file gives none.",
        "per_object_distinct_doppler_hz": sorted({round(r["doppler_hz"], 3) for r in per_obj}),
        "time_steps": ts,
        "normalize_within_cir_time_steps_doppler_hz": phase_slope_hz(h_extn, fs),
        "absolute_within_cir_time_steps_doppler_hz": phase_slope_hz(h_ext, fs),
        "normalized_over_absolute_phase_spread_across_time_steps_deg": spread,
        "separate_retrace_normalized_doppler_hz": phase_slope_hz(h_snapn, fs),
        "separate_retrace_absolute_doppler_hz": phase_slope_hz(h_snap, fs),
        "doppler_time_phase_quote": Q["paths_doppler_time_phase"],
    }
    checkpoint("rt_doppler")

    # ---------------- extrapolation (CPU toy) ----------------
    distance = float(np.linalg.norm(vel) * (N - 1) / fs)
    plate_z = 0.5 * (bbmin[2] + bbmax[2])
    trans = {"label": "CPU toy: 1 m plate (simple_reflector), near-monostatic, single specular path",
             "distance_m": distance, "duration_s": float((N - 1) / fs),
             "range_m": float(dp["tx_pos_m"][2] - plate_z),
             "extrapolated_doppler_hz": phase_slope_hz(h_ext, fs),
             "retraced_doppler_hz": phase_slope_hz(h_snap, fs),
             "max_rel_diff": float(np.max(np.abs(h_ext - h_snap)) / np.abs(h_snap).max()),
             "extrapolated_mag_ratio_last_first": float(abs(h_ext[-1]) / abs(h_ext[0])),
             "retraced_mag_ratio_last_first": float(abs(h_snap[-1]) / abs(h_snap[0])),
             "definition": "extrapolated = one solve + cir(num_time_steps, sampling_frequency, normalize_delays=False); "
                           "retraced = separate solves with the plate moved by v*t; both summed over paths"}
    rp = CONFIG["rotation_probe"]
    IT = rt.constants.InteractionType
    sc6 = rt.load_scene(rt.scene.simple_reflector)
    sc6.frequency = fc
    sc6.tx_array = rt.PlanarArray(num_rows=1, num_cols=1, **iso)
    sc6.rx_array = sc6.tx_array
    o6 = list(sc6.objects.values())[0]
    o6.radio_material.scattering_coefficient = rp["scattering_coefficient"]
    o6.velocity = mi.Vector3f(*f3(vel))
    sc6.add(rt.Transmitter("tx", position=mi.Point3f(*dp["tx_pos_m"])))
    sc6.add(rt.Receiver("rx", position=mi.Point3f(*dp["rx_pos_m"])))

    def tilt_solve(g, spp, diffuse, seed_):
        o6.orientation = mi.Point3f(0.0, 0.0, float(np.radians(g)))
        q6 = rt.PathSolver()(sc6, max_depth=rp["max_depth"], samples_per_src=spp, los=False,
                             specular_reflection=True, diffuse_reflection=diffuse, synthetic_array=True, seed=seed_)
        val = np.asarray(q6.valid).astype(bool)
        inter = np.asarray(q6.interactions)          # [depth, rx, tx, paths] (synthetic array)
        first = inter[0] if inter.ndim >= 1 and inter.shape[0] > 0 else np.zeros_like(val, dtype=int)
        aa, _ = q6.cir(normalize_delays=False, out_type="numpy")
        h = complex(np.asarray(aa).sum())
        return q6, {"n_valid_paths": int(val.sum()),
                    "n_specular_paths": int((val & (first == IT.SPECULAR)).sum()),
                    "n_diffuse_paths": int((val & (first == IT.DIFFUSE)).sum()),
                    "level_db": (float(20 * np.log10(abs(h))) if abs(h) > 0 else None)}

    so = rp["specular_only"]
    spec_rows = []
    ext_levels = None
    for g in (rp["tilt_from_deg"], rp["tilt_to_deg"]):
        q6, r = tilt_solve(g, so["samples_per_src"], so["diffuse"], so["seed"])
        spec_rows.append({"tilt_deg": g, "diffuse_reflection": so["diffuse"], "samples_per_src": so["samples_per_src"],
                          "seed": so["seed"], **r})
        if g == rp["tilt_from_deg"]:
            ae, _ = q6.cir(sampling_frequency=fs, num_time_steps=N, normalize_delays=False, out_type="numpy")
            he = np.asarray(ae).reshape(-1, N).sum(0)
            ext_levels = 20 * np.log10(np.abs(he))
    lad = rp["diffuse_on_ladder"]
    ladder_rows = []
    for g in (rp["tilt_from_deg"], rp["tilt_to_deg"]):
        for spp in lad["samples_per_src"]:
            for sd in lad["seeds"]:
                _, r = tilt_solve(g, spp, lad["diffuse"], sd)
                ladder_rows.append({"tilt_deg": g, "samples_per_src": spp, "seed": sd,
                                    "diffuse_reflection": lad["diffuse"], **r})
            checkpoint(None)
    ladder_summary = []
    for g in (rp["tilt_from_deg"], rp["tilt_to_deg"]):
        for spp in lad["samples_per_src"]:
            lv_ = [r["level_db"] for r in ladder_rows if r["tilt_deg"] == g and r["samples_per_src"] == spp
                   and r["level_db"] is not None]
            ladder_summary.append({"tilt_deg": g, "samples_per_src": spp, "n_seeds": len(lv_),
                                   "median_level_db": (float(np.median(lv_)) if lv_ else None),
                                   "min_level_db": (float(min(lv_)) if lv_ else None),
                                   "max_level_db": (float(max(lv_)) if lv_ else None),
                                   "median_n_specular_paths": float(np.median(
                                       [r["n_specular_paths"] for r in ladder_rows
                                        if r["tilt_deg"] == g and r["samples_per_src"] == spp])),
                                   "median_n_diffuse_paths": float(np.median(
                                       [r["n_diffuse_paths"] for r in ladder_rows
                                        if r["tilt_deg"] == g and r["samples_per_src"] == spp]))})
    budget_slope = []
    for g in (rp["tilt_from_deg"], rp["tilt_to_deg"]):
        pts = [(np.log(s_["samples_per_src"]) / np.log(4.0), s_["median_level_db"]) for s_ in ladder_summary
               if s_["tilt_deg"] == g and s_["median_level_db"] is not None]
        xs, ys = np.array([x for x, _ in pts]), np.array([y for _, y in pts])
        budget_slope.append({"tilt_deg": g,
                             "median_level_db_per_4x_samples_per_src": (float(np.polyfit(xs, ys, 1)[0])
                                                                        if xs.size >= 2 else None),
                             "median_level_span_db_across_ladder": (float(ys.max() - ys.min()) if ys.size else None)})
    sp_from = next(r for r in spec_rows if r["tilt_deg"] == rp["tilt_from_deg"])
    sp_to = next(r for r in spec_rows if r["tilt_deg"] == rp["tilt_to_deg"])
    half_w = 0.5 * (bbmax[0] - bbmin[0])
    height = float(dp["tx_pos_m"][2] - plate_z)
    rot = {"label": "CPU toy: 1 m plate tilt; PathSolver level in dB (arbitrary reference)",
           "tilt_from_deg": rp["tilt_from_deg"], "tilt_to_deg": rp["tilt_to_deg"],
           "level_before_db": sp_from["level_db"],
           "level_before_basis": "specular reflection only (diffuse_reflection=False)",
           "level_after_db": sp_to["level_db"],
           "level_after_basis": "specular reflection only; null when no specular path is found. With diffuse "
                                "reflection on, the after-tilt level is set by samples_per_src; see "
                                "diffuse_on_budget_ladder and diffuse_on_budget_slope.",
           "n_specular_paths_before": sp_from["n_specular_paths"], "n_specular_paths_after": sp_to["n_specular_paths"],
           "specular_only_rows": spec_rows,
           "plate_half_width_m": half_w, "radar_height_above_plate_m": height,
           "specular_foot_offset_m_before": float(height * np.sin(np.radians(rp["tilt_from_deg"]))),
           "specular_foot_offset_m_after": float(height * np.sin(np.radians(rp["tilt_to_deg"]))),
           "specular_cutoff_tilt_deg": float(np.degrees(np.arcsin(half_w / height))),
           "extrapolated_level_across_time_steps_db": {
               "basis": "specular-only solve at tilt_from_deg with the plate velocity of the Doppler probe; "
                        "cir(sampling_frequency, num_time_steps) summed over paths at each step",
               "sampling_frequency_hz": fs, "num_time_steps": N,
               "first_db": float(ext_levels[0]), "last_db": float(ext_levels[-1]),
               "max_minus_min_db": float(ext_levels.max() - ext_levels.min())},
           "diffuse_on_budget_ladder": ladder_rows,
           "diffuse_on_budget_summary": ladder_summary,
           "diffuse_on_budget_slope": budget_slope,
           "note": "An object carries one translational velocity, so cir() time steps keep |a| from the first solve "
                   "(extrapolated_level_across_time_steps_db). A re-trace loses the specular path when the specular "
                   "foot point leaves the plate; a rotation is not represented by extrapolation. With diffuse "
                   "reflection on, the remaining level after the tilt changes with samples_per_src, so no single "
                   "after-tilt level or level change is given for that case."}
    LEDGER["extrapolation"] = {"label": "CPU toy comparisons, not production settings", "translation": trans,
                               "rotation_tilt": rot}
    checkpoint("extrapolation")


# --------------------------------------------------------------------------------------------- #
# Section: our kernel (src/rcs_sbr.py) on a flat plate
# --------------------------------------------------------------------------------------------- #
def section_kernel(Q: dict) -> None:
    import rcs_sbr as ks
    from rcs_po import _plate_mesh
    for rel in ("src/rcs_sbr.py", "src/rcs_po.py", "src/geom.py", "src/materials.py", "src/gpu.py"):
        add_hash(rel, ROOT / rel)
    kc = CONFIG["kernel"]
    fc = CONFIG["fc_hz"]
    lam = C0 / fc
    sp = lam / kc["spacing_div"]
    u = np.asarray(kc["u"], float)
    m0 = _plate_mesh(kc["plate_side_m"])
    gm = {g: kc["gamma"] for g in set(m0.g)}
    mv = lam * kc["move_fraction_of_lambda"]
    rows_move = []
    for name, vec in (("along_look_direction", u * mv), ("perpendicular", np.array([mv, 0.0, 0.0]))):
        m1 = m0.translated(*vec)
        gref = ks.grid_ref_from([m0, m1], fc, spacing=sp)
        ec = [ks.sbr_field(m, gm, fc, u, spacing=sp, penetrate=kc["penetrate"]) for m in (m0, m1)]
        ef = [ks.sbr_field(m, gm, fc, u, spacing=sp, penetrate=kc["penetrate"], grid_ref=gref) for m in (m0, m1)]
        rows_move.append({"move": name, "move_m": vec.tolist(),
                          "recentred_phase_deg": float(np.degrees(np.angle(ec[1] / ec[0]))),
                          "frozen_grid_phase_deg": float(np.degrees(np.angle(ef[1] / ef[0]))),
                          "frozen_grid_mag_ratio": float(abs(ef[1] / ef[0])),
                          "expected_deg": float(np.degrees(np.angle(np.exp(1j * 4 * np.pi * float(np.dot(vec, u)) / lam))))})
    along = rows_move[0]
    gref0 = ks.grid_ref_from([m0], fc, spacing=sp)
    pvf = []
    for df in kc["freq_offsets_mhz"]:
        e = ks.sbr_field(m0, gm, fc + df * 1e6, u, spacing=sp, penetrate=kc["penetrate"], grid_ref=gref0,
                         range_m=kc["range_m"])
        pvf.append({"offset_mhz": df, "phase_deg": float(np.degrees(np.angle(e))), "magnitude": float(abs(e))})
    span = max(r["offset_mhz"] for r in pvf) - min(r["offset_mhz"] for r in pvf)
    exp_if_delay = 360.0 * span * 1e6 * 2 * kc["range_m"] / C0
    measured_span = max(r["phase_deg"] for r in pvf) - min(r["phase_deg"] for r in pvf)

    kor = ROOT / "outputs" / "kernel_outdoor_review_0915.json"
    pointer = None
    if kor.exists():
        pr = json.loads(kor.read_text(encoding="utf-8"))["checks"]["plate_reciprocity"]
        add_hash("outputs/kernel_outdoor_review_0915.json", kor)
        pointer = {"ledger": "outputs/kernel_outdoor_review_0915.json",
                   "generator": "benchmark/review_kernel_outdoor_0915.py",
                   "inputs": {k: pr.get(k) for k in ("side_m", "fc_hz", "theta_i_deg", "theta_s_deg", "gamma",
                                                     "ptd", "range")},
                   "continuum_ratio": pr.get("continuum_ratio"),
                   "recomputed": False,
                   "rows": [{"div": r["div"], "magnitude_ratio": r["magnitude_ratio"],
                             "key": f"outputs/kernel_outdoor_review_0915.json:checks.plate_reciprocity."
                                    f"rows[div={r['div']}].magnitude_ratio"} for r in pr["rows"]]}
    LEDGER["kernel"] = {
        "label": "Our kernel on a flat square plate, CPU; implementation checks, no RF comparison",
        "plate_side_m": kc["plate_side_m"], "gamma": kc["gamma"], "fc_hz": fc, "look_direction_u": kc["u"],
        "spacing_div": kc["spacing_div"], "spacing_m": sp, "module_default_div": int(ks.DEFAULT_DIV),
        "module_angle_gamma": bool(ks.ANGLE_GAMMA),
        "move_m": mv,
        "recentred_phase_deg_for_lambda_over_8_move": along["recentred_phase_deg"],
        "frozen_grid_phase_deg": along["frozen_grid_phase_deg"],
        "expected_deg": along["expected_deg"],
        "move_rows": rows_move,
        "phase_vs_frequency": pvf,
        "phase_vs_frequency_range_m": kc["range_m"],
        "phase_vs_frequency_measured_span_deg": measured_span,
        "phase_span_deg_if_output_carried_two_way_delay": exp_if_delay,
        "code_quotes": [Q["kernel_bbox_centre"], Q["kernel_plane_phase_reference"], Q["kernel_spherical_phase_tx"],
                        Q["kernel_spherical_phase"]],
        "plate_reciprocity_pointer": pointer,
    }


# --------------------------------------------------------------------------------------------- #
def main() -> None:
    started = utc_now()
    try:
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception as e:  # noqa: BLE001
        head = f"unavailable: {type(e).__name__}"
    LEDGER["_meta"] = {
        "generator": f"benchmark/{NAME}.py",
        "command": f'CUDA_VISIBLE_DEVICES="" /workspace/.venvs/py312/bin/python benchmark/{NAME}.py',
        "argv": sanitized_argv(),
        "started_utc": started, "finished_utc": None, "git_head": head,
        "versions": {pk: _pkg_version(pk) for pk in ("sionna", "sionna-rt", "mitsuba", "drjit", "numpy")},
        "python": sys.version.split()[0], "cpu_affinity": sorted(os.sched_getaffinity(0)),
        "scope": "Simulation / code / bookkeeping checks with no comparison against RF measurements. PathSolver "
                 "levels are PathSolver level in dB (arbitrary reference). Toy CPU probes are labelled as such.",
        "config": CONFIG,
        "definitions": {
            "median_s_per_pose": "median over shards of meta[5] / idx.size (elapsed seconds of the shard divided by "
                                 "its pose count); meta layout verified in cost.meta_layout.quotes",
            "median_paths": "median over shards of the per-shard median of npaths",
            "single_process_wall_hours": "rate_hz * duration_s * median_s_per_pose / 3600 (rt210, depth 2)",
            "doppler_hz_measured": "Paths.doppler of the single specular path",
            "per_object doppler_hz": "median Paths.doppler over valid paths whose first interaction is that object; "
                                     "expected = dot(k_out - k_in, v_object) / lambda from Paths.vertices",
            "phase slope Doppler": "slope of a linear fit to the unwrapped phase of the path-summed coefficient "
                                   "versus time, divided by 2*pi",
            "phase_rotation_deg_measured": "median over valid paths of angle(cir(normalize_delays=True) / "
                                           "cir(normalize_delays=False)) in degrees",
            "phase_rotation_deg_expected": "angle(exp(j 2 pi fc min_tau)) in degrees",
            "max_rel_diff": "max_t |h_extrapolated(t) - h_retraced(t)| / max_t |h_retraced(t)|",
            "level_db": "20 log10 |sum over paths of cir(normalize_delays=False)| ; PathSolver level in dB "
                        "(arbitrary reference)",
            "n_specular_paths / n_diffuse_paths": "valid paths whose first interaction type is "
                                                   "InteractionType.SPECULAR / InteractionType.DIFFUSE",
            "median_level_db_per_4x_samples_per_src": "slope of a linear fit of the per-budget median level_db "
                                                      "against log4(samples_per_src)",
            "f_tip_el0_hz": "f_tip_hz / cos(source el_deg)",
            "implied_tip_speed_mps": "f_tip_hz * source_wavelength_m / (2 cos(source el_deg))",
            "implied_tip_radius_m": "implied_tip_speed_mps / (2 pi hover_rpm / 60)",
            "recentred_phase_deg": "angle(E(moved) / E(original)) with the kernel grid centred on each mesh bbox",
            "frozen_grid_phase_deg": "same ratio with one grid_ref_from() frozen over both meshes",
            "required_rate_hz": "2 * (f_tip_hz + 2 v / lambda); required_pose_rate uses f_tip_hz at the source "
                                "look, required_pose_rate_el0 uses f_tip_el0_hz",
            "deg_per_sample": "360 * rpm / 60 / rate_hz",
        },
        "assumptions": [
            {"id": "speed_of_light", "flag": "external constant", "value": C0, "source": "SOURCES[speed_of_light]"},
            {"id": "carrier", "flag": "configuration", "value": CONFIG["fc_hz"],
             "note": "3.5 GHz; checked against outputs/report07_three_engines.json _meta.fc_hz (rotor.fc_matches_config)"},
            {"id": "unstamped_names_are_2.0.1", "flag": "naming rule, not a per-shard record",
             "note": "Shards without a build tag in the name are counted as build 2.0.1 per BUILD_BASELINE and "
                     "build_tag(); the same file states only that no record shows another build."},
            {"id": "shared_card_timing", "flag": "unmeasured conditions",
             "note": "Shards record neither device id nor concurrent workers; the supervisor allows several workers "
                     "per card. Wall times are single-process wall time under shared conditions."},
            {"id": "timer_includes_scene_rebuild", "flag": "verified from code order",
             "note": "cost.timer_includes_scene_rebuild is computed from verified line order and indentation."},
            {"id": "kernel_device", "flag": "unrecorded", "note": "ours shards do not record CPU or GPU."},
            {"id": "f_tip_is_source_look_projection", "flag": "taken from source ledger, formula verified",
             "note": "f_tip_hz in outputs/report07_three_engines.json includes cos(el_deg) for the source look "
                     "(rotor.source_el_deg, rotor.source_az_deg; quote report07_f_tip_cos_el) and uses the source "
                     "wavelength constant. required_pose_rate and tip_doppler_within_two_sided_band_at_source_look "
                     "hold for that look only; the _el0 variants use f_tip_hz / cos(el_deg). Body Doppler is added "
                     "as a radial speed with exact c."},
            {"id": "tilt_diffuse_budget", "flag": "ray-budget dependent",
             "note": "With diffuse reflection on, the level after the tilt changes with samples_per_src; it is "
                     "recorded only as a ladder (extrapolation.rotation_tilt.diffuse_on_budget_ladder)."},
            {"id": "toy_probes", "flag": "CPU toy",
             "note": "Translation and tilt probes use the 1 m simple_reflector plate at 10 m, not production settings "
                     "(depth 2, 4e9 rays)."},
        ],
        "source_hashes": {},
        "sections_done": [],
    }
    LEDGER["sources"] = SOURCES
    Q = verify_quotes()
    LEDGER["quote_checks"] = list(Q.values())
    LEDGER["_meta"]["quote_checks_failed"] = [q["id"] for q in Q.values() if not q["verified"]]
    LEDGER["_meta"]["quote_checks_relocated"] = [q["id"] for q in Q.values() if q["relocated"]]
    LEDGER["env_refusal_quote"] = {
        "lines": [Q[k] for k in ("sweep_env_refusal_branch", "sweep_env_refusal_comment", "sweep_env_refusal_if",
                                 "sweep_env_refusal_raise", "sweep_env_refusal_message", "sweep_env_refusal_reason",
                                 "sweep_env_refusal_grid_factor")],
        "all_verified": all(Q[k]["verified"] for k in Q if k.startswith("sweep_env_refusal")),
    }
    checkpoint("quotes")
    section_cost(Q)
    checkpoint("cost")
    section_rotor(Q)
    checkpoint("rotor")
    section_rt(Q)
    section_kernel(Q)
    LEDGER["_meta"]["finished_utc"] = utc_now()
    LEDGER["_meta"]["wall_time_s"] = round(time.time() - T_START, 3)
    checkpoint("kernel")


if __name__ == "__main__":
    main()
