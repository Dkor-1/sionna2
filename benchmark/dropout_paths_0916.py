#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dropout_paths_0916.py - which PathSolver paths change at the isolated poses of a production cell.

Purpose
    The corpus ledger (outputs/isac_plan_corpus_0915.json, section "dropout") labels "isolated poses":
    poses of a merged 8,192-pose field E where |E - m| > 20 x median_over_poses(|E - m|), m = complex
    (component-wise) median of E. This script re-solves chosen poses of production cells with the same
    scene, placement and PathSolver call as benchmark/elevation_sweep_md.py (engine sionna), lists every
    returned path with the objects it hits, splits the field into path classes and compares isolated poses
    with their neighbours and with random non-isolated poses.

    Poses per cell: the first --n-outliers isolated poses (recomputed from the stored shards, cross-checked
    against the ledger row), each one's neighbours i-1 and i+1, and --n-random random non-isolated poses
    (fixed --seed). Every pose is compared with the stored shard value E_stored, which is the trust gate
    for the listing: the summary reports the maximum relative error and does not hide it.

Production run (GPU; run by the main session, not by a CPU helper)
    cd /workspace/sionna && CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=2 \
        DRJIT_LIBOPTIX_PATH=/workspace/.venvs/optix/libnvoptix.so.1 \
        LD_LIBRARY_PATH=/workspace/.venvs/optix:$LD_LIBRARY_PATH taskset -c 12,13 \
        /workspace/.venvs/py312/bin/python -B benchmark/dropout_paths_0916.py
    (the two OptiX variables are the ones runners/worker_supervisor.py gives production workers; --device gpu
    refuses to start without them)
    (the taskset cores are the operator's choice; the script records its CPU affinity in _meta)
    Estimate: GPU memory about 1.3 GiB per process (production workers of these arms at 4e9 rays, depth 2
    show 1.23-1.30 GiB in nvidia-smi on 2026-09-16); allow 3 GiB. Runtime: at most 64 poses per cell
    (16 isolated + up to 32 neighbours + 16 random; with the defaults 63 poses for the ground cell and 61 for
    the street canyon, because some isolated poses share a neighbour); stored per-pose times are about 1.35 s
    (ground) and 3.3 s (street canyon), so about 1.5 min + 3.5 min of solving plus scene loading and kernel
    compilation, roughly 10 min in total. The script checkpoints after each pose (one npz per pose under
    outputs/partial/<out stem>_ckpt/ (gitignored), a few hundred kB each) and resumes from checkpoints whose stamp (arm, el, ray count,
    Mitsuba variant, solver build, path cap) matches. Expected outputs: JSON a few MB, per-path npz some tens of
    MB (about 3,000 paths per pose); the checkpoint directory can be removed after a complete run.

CPU smoke test (proves the script runs end to end; cannot reproduce E_stored)
    cd /workspace/sionna && CUDA_VISIBLE_DEVICES="" SIONNA2_ALLOW_CPU=1 OMP_NUM_THREADS=1 taskset -c 13 \
        /workspace/.venvs/py312/bin/python -B <this script> --root /workspace/sionna --device cpu \
        --spp 1000000 --n-outliers 1 --n-random 0 --max-poses 2 --out <scratch>/dropout_paths_smoke.json
    With --spp other than the arm's ray count, or on the LLVM (CPU) variant, the ray set differs from
    production, so E_recomputed does not reproduce E_stored; the output marks this as
    production_equivalent = false.

Arguments
    --root DIR        repository root (default: parent of this script's directory)
    --out FILE        output JSON (default ROOT/outputs/dropout_paths_0916.json); the complete per-path listing
                      goes to <out stem>_paths.npz and per-pose checkpoints to outputs/partial/<out stem>_ckpt/
    --cells ARM@EL    repeatable; default the two production sionna-rt 2.1.0 cells below at el -60
    --n-outliers N    first N isolated poses per cell (default 16)
    --n-random N      random non-isolated poses per cell (default 16)
    --seed S          seed of the random pose draw (default 20260916)
    --factor K        isolation factor (default 20, the ledger's primary factor)
    --spp N           ray count override (smoke test only; default = the arm's ray count)
    --device gpu|cpu  gpu requires a CUDA Mitsuba variant and an explicit CUDA_VISIBLE_DEVICES
    --max-poses N     cap on poses per cell (smoke test only; 0 = no cap)
    --json-paths K    strongest paths per pose written into the JSON (default 24; the npz has all of them)
    --tau-tol-s T     delay tolerance when matching a path between poses (default 1e-12 s)
    --cores LIST      optional CPU affinity (comma list) applied with os.sched_setaffinity

Reuse and copies (benchmark/elevation_sweep_md.py is imported, never modified)
    Imported: elevation_sweep_md.main's argument parser (run() is swapped for a capture while main() parses
    the production job line), elevation_sweep_md.run with --dry-run (checks that the job line rebuilds the
    exact shard file names, including the mesh-fix, blade-law and solver-build tags of this installation),
    carrier, env_parts, build_scene_builtin, require_cuda_variant, shard_done, SOLVER_BUILD, TJ;
    report15_probe (place, unpack, build_scene, Part, NO_OBJ, MAX_PATHS, rt, mi); articulated_fast
    (FastPoser, rotor_phases); drones (DRONES, DRONE_GROUP_MAT, drone_colors); mesh_inmem.InMemGroups;
    arm_grammar (parse, unparse).
    Copied (the pose loop lives inside run() and cannot be imported); line numbers refer to
    benchmark/elevation_sweep_md.py as last changed in commit d42a9fe6 and are repeated in _meta.copied.
    At start-up the script checks an anchor string at each copied range and stops if the file has moved:
      362-411   drone spec, FastPoser, PRF, pose count, azimuth, rpm and rotor phases (constant-rpm branch)
      433, 438  range and carrier
      792-822   ray count, depth and the --sw switch parsing (--sw branch only)
      834       drone colours
      953       PathSolver construction (non-deterministic branch)
      958-968   InMemGroups mesh cache
      969-1003  per-pose vertex update and drone Part list (in-memory branch)
      1012-1021 environment scene (outdoor01_* meshes or an NVIDIA built-in scene)
      1050-1057 transmitter/receiver placement and the PathSolver call
      1059      path unpacking
      1087-1088 per-pose object_id -> scene object name map
      1124-1125, 1144-1145  interaction mask and carrier-phase sum (no --det branch)

Scope
    Simulation bookkeeping only. Path classes are defined by scene object names; nothing here states which
    solver output is closer to a measurement (there is no RF measurement comparison), and differences between
    poses are reported as observations of the solver output, not as solver faults. Outdoor scenes only.
"""
from __future__ import annotations

import argparse
import os
import sys

DEFAULT_CELLS = (
    "sionna_p4000000000_swR0D0E0F1_r15_n8192_envoutdoor01_ground_mfixbatteryi5_blperairframe_rt210_d2@-60",
    "sionna_p4000000000_swR0D0E0F1_r15_n8192_envsionna-simple_street_canyon_mfixbatteryi5_blperairframe_rt210_d2@-60",
)
NAME = "dropout_paths_0916"


def _cli() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--cells", action="append", default=None, metavar="ARM@EL")
    ap.add_argument("--n-outliers", type=int, default=16)
    ap.add_argument("--n-random", type=int, default=16)
    ap.add_argument("--seed", type=int, default=20260916)
    ap.add_argument("--factor", type=float, default=20.0)
    ap.add_argument("--spp", type=int, default=0)
    ap.add_argument("--device", choices=("gpu", "cpu"), default="gpu")
    ap.add_argument("--max-poses", type=int, default=0)
    ap.add_argument("--json-paths", type=int, default=24)
    ap.add_argument("--tau-tol-s", type=float, default=1e-12)
    ap.add_argument("--cores", default="")
    return ap.parse_args()


ARGS = _cli()
if ARGS.device == "cpu":
    # Hide every GPU before any CUDA-capable module is imported; the solver then runs on the LLVM variant.
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    os.environ["SIONNA2_ALLOW_CPU"] = "1"
else:
    if not os.environ.get("CUDA_VISIBLE_DEVICES", "").strip():
        raise SystemExit("--device gpu needs an explicit CUDA_VISIBLE_DEVICES (for example CUDA_VISIBLE_DEVICES=1); "
                         "without it gpu.pick() would choose a card on its own.")
    if os.environ.get("DRJIT_LIBOPTIX_PATH") != "/workspace/.venvs/optix/libnvoptix.so.1":
        raise SystemExit("--device gpu needs the OptiX library production workers use "
                         "(runners/worker_supervisor.py). Run:\n  CUDA_VISIBLE_DEVICES=<card> "
                         "DRJIT_LIBOPTIX_PATH=/workspace/.venvs/optix/libnvoptix.so.1 "
                         "LD_LIBRARY_PATH=/workspace/.venvs/optix:$LD_LIBRARY_PATH "
                         "/workspace/.venvs/py312/bin/python -B benchmark/dropout_paths_0916.py")
if ARGS.cores:
    os.sched_setaffinity(0, {int(c) for c in ARGS.cores.split(",") if c.strip()})

import contextlib                                                      # noqa: E402
import datetime as _dt                                                 # noqa: E402
import hashlib                                                         # noqa: E402
import io                                                              # noqa: E402
import json                                                            # noqa: E402
import platform                                                        # noqa: E402
import re                                                              # noqa: E402
import subprocess                                                      # noqa: E402
import time                                                            # noqa: E402
from pathlib import Path                                               # noqa: E402

SCRIPT = Path(__file__).resolve()
ROOT = Path(ARGS.root).resolve() if ARGS.root else SCRIPT.parents[1]
OUT = Path(ARGS.out).resolve() if ARGS.out else ROOT / "outputs" / f"{NAME}.json"
OUT_NPZ = OUT.with_name(OUT.stem + "_paths.npz")
CKPT = ROOT / "outputs" / "partial" / (OUT.stem + "_ckpt")  # gitignored; delete after a complete run
for _p in (ROOT / "src", ROOT / "benchmark"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import numpy as np                                                     # noqa: E402

import arm_grammar as AG                                               # noqa: E402
import elevation_sweep_md as ESM                                       # noqa: E402  (applies the thread guard)

if Path(ESM.ROOT).resolve() != ROOT:
    raise SystemExit(f"elevation_sweep_md was imported from {ESM.ROOT}, not from --root {ROOT}")

ESM_REL = "benchmark/elevation_sweep_md.py"
COPIED = [
    dict(lines="362-411", what="drone spec, FastPoser, PRF, pose count, azimuth, rpm and rotor phases (constant-rpm branch)"),
    dict(lines="433, 438", what="range and carrier"),
    dict(lines="792-822", what="ray count, depth and --sw switch parsing (--sw branch only)"),
    dict(lines="834", what="drone colours"),
    dict(lines="953", what="PathSolver construction (non-deterministic branch)"),
    dict(lines="958-968", what="InMemGroups mesh cache"),
    dict(lines="969-1003", what="per-pose vertex update and drone Part list (in-memory branch)"),
    dict(lines="1012-1021", what="environment scene (outdoor01_* meshes or NVIDIA built-in scene)"),
    dict(lines="1050-1057", what="placement and PathSolver call"),
    dict(lines="1059", what="path unpacking"),
    dict(lines="1087-1088", what="per-pose object_id -> scene object name map"),
    dict(lines="1124-1125, 1144-1145", what="interaction mask and carrier-phase sum (no --det branch)"),
]
# (line, text that must appear on that line of benchmark/elevation_sweep_md.py) - guards the copied ranges.
ANCHORS = [
    (362, 'drone_key = str(getattr(a, "drone", "") or TJ.get("drone", "matrice4e"))'),
    (411, "ph = rotor_phases(np.arange(n) / prf, rpms, fp.dirs)"),
    (433, 'rng_m = float(getattr(a, "range_m", RANGE_M) or RANGE_M)'),
    (438, "fc, tagfc = carrier(a)"),
    (793, "spp = int(a.spp) if a.spp else rule_spp(rng_m)"),
    (803, 'm = _re.fullmatch(r"R([01])D([01])E([01])F([01])", swbits)'),
    (823, 'mdep = int(a.max_depth) if getattr(a, "max_depth", 0) else 1'),
    (835, "cols = drone_colors(spec)"),
    (954, "_solver = RP.rt.PathSolver()"),
    (962, "_lay = InMemGroups(_mv0.f, _mv0.g)"),
    (976, "_lay.update_vertices(RP.mi, _par_cache[g], mv.v, g)"),
    (1017, "sc, _ctr, _scene_obj_names = build_scene_builtin("),
    (1022, "sc = RP.build_scene(parts, fc=fc)"),
    (1051, "RP.place(sc, center=_ctr, az=az, el=el, rng=rng_m, baseline=0.0,"),
    (1058, 'samples_per_src=spp, max_num_paths_per_src=RP.MAX_PATHS'),
    (1061, "aa, tau, _, O = RP.unpack(p, want_doppler=False)"),
    (1089, "_id2nm = {int(_o.object_id): str(_nm)"),
    (1126, "hit = (O != RP.NO_OBJ).any(axis=0) if O.size else np.zeros(aa.size, bool)"),
    (1127, "_t = aa[hit] * np.exp(-1j * 2 * np.pi * fc * tau[hit])"),
    (1147, "E[j] = complex(np.sum(_t_sum))"),
]
_esm_lines = (ROOT / "benchmark" / "elevation_sweep_md.py").read_text(encoding="utf-8").splitlines()
_bad = [(ln, txt) for ln, txt in ANCHORS if ln > len(_esm_lines) or txt not in _esm_lines[ln - 1]]
if _bad:
    raise SystemExit(f"benchmark/elevation_sweep_md.py has moved; copied ranges no longer match at {_bad}. "
                     "Re-check the copied code before running.")

REUSED = [
    "elevation_sweep_md.main (argument parser; run swapped for a capture)",
    "elevation_sweep_md.run with dry_run=True (shard-name equivalence check)",
    "elevation_sweep_md.carrier, env_parts, build_scene_builtin, require_cuda_variant, shard_done, SOLVER_BUILD, TJ",
    "report15_probe.place, unpack, build_scene (via Part), NO_OBJ, MAX_PATHS, rt, mi",
    "articulated_fast.FastPoser, rotor_phases",
    "drones.DRONES, DRONE_GROUP_MAT, drone_colors",
    "mesh_inmem.InMemGroups",
    "arm_grammar.parse, unparse",
]
CLASSES = ("none", "env_only", "drone_only", "both", "unmapped")      # class code = index
TYPE_NAMES = {0: "none", 1: "specular", 2: "diffuse", 4: "refraction", 8: "diffraction"}
# Arm-name fields this script can rebuild into a job line; anything else is refused.
SUPPORTED_FIELDS = {"engine", "spp", "switches", "range_m", "n_poses", "rep", "env", "mesh_fix", "blade_law",
                    "solver_build", "max_depth"}

STARTED = _dt.datetime.now(_dt.timezone.utc)
T0 = time.time()


def log(msg: str) -> None:
    print(msg, flush=True)


def utc(t=None) -> str:
    return (t or _dt.datetime.now(_dt.timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def cpair(z) -> list:
    z = complex(z)
    return [float(z.real), float(z.imag)]


def g6(x):
    return None if x is None else float(f"{float(x):.6g}")


def git_head() -> str | None:
    try:
        r = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=20)
        return r.stdout.strip() or None
    except Exception:                                                  # noqa: BLE001
        return None


def atomic_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)
    os.replace(tmp, path)


def atomic_npz(path: Path, **arrays) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.stem + f".{os.getpid()}.tmp.npz")        # savez appends .npz otherwise
    np.savez_compressed(tmp, **arrays)
    os.replace(tmp, path)


# ----------------------------------------------------------------------------------------------- cells
def job_argv(arm: str, el: float) -> tuple[list, dict]:
    """Production job line for an arm name (read with arm_grammar, never with a regex)."""
    f = AG.parse(arm, strict=True)
    if AG.unparse(f) != arm:
        raise SystemExit(f"arm name does not round-trip through arm_grammar: {arm}")
    extra = sorted(k for k in f if k not in SUPPORTED_FIELDS and not k.startswith("_"))
    if extra or f.get("engine") != "sionna":
        raise SystemExit(f"arm {arm}: unsupported fields {extra} or engine {f.get('engine')} "
                         f"(this script rebuilds only {sorted(SUPPORTED_FIELDS)})")
    env = str(f.get("env", ""))
    if not env:
        raise SystemExit(f"arm {arm}: no environment; this study covers outdoor scenes only")
    # File names write the built-in scene prefix "sionna:" as "sionna-" (elevation_sweep_md.py tagr).
    env_arg = ("sionna:" + env[len("sionna-"):]) if env.startswith("sionna-") else env
    argv = ["--engine", "sionna", "--spp", str(f["spp"]), "--n-poses", str(f["n_poses"]),
            "--max-depth", str(f["max_depth"]), "--range-m", str(f["range_m"]), "--sw", str(f["switches"]),
            f"--els={el:g}", "--env", env_arg]
    if f.get("rep"):
        argv += ["--rep", str(f["rep"])]
    return argv, f


def production_namespace(argv: list) -> argparse.Namespace:
    """Parse a job line with elevation_sweep_md's own parser (defaults included)."""
    captured = {}
    orig_run, orig_argv = ESM.run, sys.argv
    try:
        ESM.run = lambda a: captured.setdefault("a", a)
        sys.argv = ["elevation_sweep_md.py"] + list(argv)
        ESM.main()
    finally:
        ESM.run, sys.argv = orig_run, orig_argv
    return captured["a"]


def dry_run_names(a: argparse.Namespace, nshards: int) -> list[str]:
    """Shard basenames that elevation_sweep_md.run(--dry-run) builds for this job line."""
    names = []
    for s in range(nshards):
        b = argparse.Namespace(**vars(a))
        b.dry_run, b.shard, b.nshards = True, s, nshards
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                ESM.run(b)
        except SystemExit as e:
            raise SystemExit(f"elevation_sweep_md.run --dry-run refused the job line: {e}\n{buf.getvalue()}")
        lines = [ln for ln in buf.getvalue().splitlines() if "[dry]" in ln]
        if len(lines) != 1:
            raise SystemExit(f"dry run printed {len(lines)} shard lines:\n{buf.getvalue()}")
        names.append(lines[0].split()[-1])
    return names


def load_cell_field(arm: str, el: float) -> dict:
    shd = ROOT / "outputs" / "elev_sweep_shards"
    files = sorted(shd.glob(f"{arm}_el{el:+g}_[0-9][0-9].npz"))
    if not files:
        raise SystemExit(f"no shards for {arm} el {el:+g} in {shd}")
    metas, parts = [], []
    for fp in files:
        if not ESM.shard_done(str(fp)):
            raise SystemExit(f"shard fails shard_done: {fp.name}")
        with np.load(fp) as z:
            zf = set(z.files)
            parts.append(dict(file=fp.name, idx=z["idx"].astype(np.int64), E=z["E"],
                              npaths=np.asarray(z["npaths"]) if "npaths" in zf else None,
                              nret=np.asarray(z["nret"]) if "nret" in zf else None,
                              meta=np.asarray(z["meta"], float).ravel(),
                              cfg=np.asarray(z["cfg"], float).ravel() if "cfg" in zf else None,
                              n_trunc=np.asarray(z["n_trunc"]).ravel().tolist() if "n_trunc" in zf else None,
                              solver_build=str(z["solver_build"]) if "solver_build" in zf else None,
                              t_start=float(np.asarray(z["t_start"]).ravel()[0]) if "t_start" in zf else None,
                              run_id=str(z["run_id"]) if "run_id" in zf else None,
                              sha256=sha256_file(fp)))
            metas.append(parts[-1]["meta"])
    nsh = {int(m[2]) for m in metas}
    n = {int(m[3]) for m in metas}
    if len(nsh) != 1 or len(n) != 1:
        raise SystemExit(f"{arm}: shards disagree on nshards {nsh} or pose count {n}")
    nsh, n = nsh.pop(), n.pop()
    if [p["file"] for p in parts] != [f"{arm}_el{el:+g}_{s:02d}.npz" for s in range(nsh)]:
        raise SystemExit(f"{arm}: shard files {[p['file'] for p in parts]} do not match nshards {nsh}")
    E = np.full(n, np.nan + 0j, complex)
    npaths = np.full(n, -1, np.int64)
    nret = np.full(n, -1, np.int64)
    cover = np.zeros(n, int)
    for p in parts:
        E[p["idx"]] = p["E"]
        cover[p["idx"]] += 1
        if p["npaths"] is not None:
            npaths[p["idx"]] = p["npaths"]
        if p["nret"] is not None:
            nret[p["idx"]] = p["nret"]
    if not np.all(cover == 1):
        raise SystemExit(f"{arm}: poses not covered exactly once (min {cover.min()}, max {cover.max()})")
    return dict(E=E, npaths=npaths, nret=nret, nshards=nsh, n=n, parts=parts)


def isolated_poses(E: np.ndarray, k: float):
    m = complex(np.median(E.real), np.median(E.imag))
    d = np.abs(E - m)
    sc = float(np.median(d))
    return (np.flatnonzero(d > k * sc) if sc > 0 else np.zeros(0, int)), m, sc


def ledger_row(arm: str, el: float):
    p = ROOT / "outputs" / "isac_plan_corpus_0915.json"
    if not p.exists():
        return None, str(p)
    with open(p, encoding="utf-8") as f:
        d = json.load(f)
    for r in d.get("dropout", {}).get("rows", []):
        if r.get("arm") == arm and abs(float(r.get("el_deg", 1e9)) - el) < 1e-9:
            return r, str(p.relative_to(ROOT))
    return None, str(p.relative_to(ROOT))


def rep_sibling(fields: dict) -> str | None:
    """Arm name of a repeat run (_rep<k>) of the same cell, if the grammar can build one."""
    if fields.get("rep"):
        return None
    g = dict(fields)
    g["rep"] = "1"
    try:
        return AG.unparse(g)
    except Exception:                                                  # noqa: BLE001
        return None


def select_poses(n: int, iso: np.ndarray, n_out: int, n_rand: int, seed: int, cap: int):
    iso_set = set(int(i) for i in iso)
    chosen_iso = [int(i) for i in iso[:max(0, n_out)]]
    roles: dict[int, dict] = {}
    for i in chosen_iso:
        roles.setdefault(i, dict(roles=set(), neighbour_of=set()))["roles"].add("isolated")
    for i in chosen_iso:
        for j in (i - 1, i + 1):
            if 0 <= j < n:
                r = roles.setdefault(j, dict(roles=set(), neighbour_of=set()))
                r["roles"].add("neighbour")
                r["neighbour_of"].add(i)
    pool = np.array([i for i in range(n) if i not in iso_set and i not in roles], np.int64)
    rng = np.random.default_rng(seed)
    rand = sorted(int(x) for x in rng.choice(pool, size=min(max(0, n_rand), pool.size), replace=False)) \
        if n_rand > 0 and pool.size else []
    for i in rand:
        roles.setdefault(i, dict(roles=set(), neighbour_of=set()))["roles"].add("random")
    # Solve order: each isolated pose followed by its neighbours, then the random poses.
    order = []
    for i in chosen_iso:
        for j in (i, i - 1, i + 1):
            if j in roles and j not in order:
                order.append(j)
    order += [i for i in rand if i not in order]
    if cap > 0:
        order = order[:cap]
    for i, r in roles.items():
        r["isolated_by_definition"] = i in iso_set
    return order, roles, chosen_iso, rand


# ----------------------------------------------------------------------------------------------- solver setup
class CellSolver:
    """Production scene and solver setup for one (arm, el) cell, built once per cell."""

    def __init__(self, a: argparse.Namespace, el: float, spp_override: int):
        import report15_probe as RP
        from articulated_fast import FastPoser, rotor_phases
        from drones import DRONES, DRONE_GROUP_MAT, drone_colors
        from mesh_inmem import InMemGroups
        self.RP, self.DRONE_GROUP_MAT = RP, DRONE_GROUP_MAT
        refuse = dict(rotor_preset=getattr(a, "rotor_preset", ""), det=getattr(a, "det", False),
                      solver_deterministic=getattr(a, "solver_deterministic", False),
                      parts=getattr(a, "parts", ""), physics=getattr(a, "physics", False),
                      stock=getattr(a, "stock", False), only=getattr(a, "only", ""),
                      max_paths=int(getattr(a, "max_paths", 0) or 0),
                      shell_mm=float(getattr(a, "shell_mm", 0) or 0), prop_mm=float(getattr(a, "prop_mm", 0) or 0),
                      env_alt=float(getattr(a, "env_alt", 0) or 0),
                      env_scat_set=float(getattr(a, "env_scat", -1.0)) >= 0,
                      ant_not_iso=str(getattr(a, "ant_pattern", "iso") or "iso") != "iso",
                      inmem_off=not bool(getattr(a, "inmem", True)))
        bad = {k: v for k, v in refuse.items() if v}
        if bad:
            raise SystemExit(f"job line uses options this script does not reproduce: {bad}")
        if ESM._ENV_ALT[0] != 0.0:
            raise SystemExit(f"elevation_sweep_md._ENV_ALT is {ESM._ENV_ALT[0]}, expected 0")
        TJ = ESM.TJ
        # --- copied from elevation_sweep_md.py:362-411 (constant-rpm branch; rotor presets are refused above)
        drone_key = str(getattr(a, "drone", "") or TJ.get("drone", "matrice4e"))
        spec = DRONES[drone_key]
        fp = FastPoser(spec, prop_scale=float(getattr(a, "prop_scale", 1.0) or 1.0),
                       frame_scale=float(getattr(a, "frame_scale", 1.0) or 1.0),
                       body_scale=float(getattr(a, "body_scale", 1.0) or 1.0))
        _prf_arg = float(getattr(a, "prf", 0.0) or 0.0)
        prf = _prf_arg if _prf_arg > 0 else float(TJ["prf_hz"])
        n = int(getattr(a, "n_poses", 0) or TJ["n"])
        _az_arg = float(getattr(a, "az_deg", float("nan")))
        az = float(TJ.get("az_deg", 0.0)) if np.isnan(_az_arg) else _az_arg
        rpms = np.asarray(TJ["rpm_per_rotor"], float)
        n_rot = len(fp.dirs)
        if (getattr(a, "drone", "") and drone_key != TJ.get("drone", "matrice4e")) or rpms.size != n_rot:
            base = float(getattr(spec, "hover_rpm", float(np.mean(rpms))))
            rel = rpms / np.mean(rpms)
            rel = np.resize(rel, n_rot)
            rpms = base * rel
        ph = rotor_phases(np.arange(n) / prf, rpms, fp.dirs)
        # --- copied from elevation_sweep_md.py:433, 438
        rng_m = float(getattr(a, "range_m", ESM.RANGE_M) or ESM.RANGE_M)
        fc, _tagfc = ESM.carrier(a)
        # --- copied from elevation_sweep_md.py:792-822 (--sw branch)
        spp_prod = int(a.spp) if a.spp else ESM.rule_spp(rng_m)
        swbits = str(getattr(a, "sw", "") or "").upper()
        import re as _re
        m = _re.fullmatch(r"R([01])D([01])E([01])F([01])", swbits)
        if not m:
            raise SystemExit(f"job line has no --sw R#D#E#F# switch set ({swbits!r}); only that branch is copied")
        r_, d_, e_, f_ = (bool(int(x)) for x in m.groups())
        sw = dict(refraction=r_, diffraction=d_, edge_diffraction=e_)
        diffuse = f_
        mdep = int(a.max_depth) if getattr(a, "max_depth", 0) else 1
        # --- copied from elevation_sweep_md.py:834
        cols = drone_colors(spec)
        self.spec, self.fp, self.ph, self.n, self.prf, self.az, self.el = spec, fp, ph, n, prf, az, float(el)
        self.rng_m, self.fc, self.sw, self.diffuse, self.mdep, self.cols = rng_m, fc, sw, diffuse, mdep, cols
        self.spp_prod = spp_prod
        self.spp = int(spp_override) if spp_override else spp_prod
        if self.spp > 4_294_967_295:
            raise SystemExit("--spp above the 32-bit sampler ceiling")
        self.env = str(getattr(a, "env", "") or "")
        self.antp, self.antc, self.aimo = "iso", float(getattr(a, "ant_cap", 30.0)), 0.0
        # --- copied from elevation_sweep_md.py:953
        self.solver = RP.rt.PathSolver()
        # --- copied from elevation_sweep_md.py:958-968 (the production cache starts from the shard's first pose;
        #     vertices are replaced before every solve, so the starting pose does not enter the scene)
        self.InMemGroups = InMemGroups
        self._lay = None
        self._mesh_cache, self._par_cache = {}, {}
        self._first_pose = None

    def _ensure_cache(self, i0: int):
        if self._lay is not None:
            return
        RP, spec = self.RP, self.spec
        _mv0 = self.fp.pose(self.ph[int(i0)])
        self._lay = self.InMemGroups(_mv0.f, _mv0.g)
        for g in self._lay.names:
            _m, _pp = self._lay.make_mesh(RP.mi, _mv0.v, g, name=f"{spec.key}_{g}")
            self._mesh_cache[g], self._par_cache[g] = _m, _pp
        self._first_pose = int(i0)

    def solve(self, i: int) -> dict:
        RP, spec = self.RP, self.spec
        self._ensure_cache(i)
        t0 = time.time()
        # --- copied from elevation_sweep_md.py:969-1003 (in-memory branch, no --parts)
        mv = self.fp.pose(self.ph[i])
        paths_obj = {g: None for g in self._lay.names}
        for g in self._lay.names:
            self._lay.update_vertices(RP.mi, self._par_cache[g], mv.v, g)
        mi_meshes = self._mesh_cache
        parts = [RP.Part(name=f"{spec.key}_{g}", obj=(p or ""),
                         mat_key=self.DRONE_GROUP_MAT[g][0], color=self.cols[g],
                         mi_mesh=mi_meshes[g])
                 for g, p in paths_obj.items()]
        drone_names = {p.name for p in parts}
        # --- copied from elevation_sweep_md.py:1012-1021
        _envn = self.env
        _ctr = (0.0, 0.0, 0.0)
        if _envn.startswith("sionna:"):
            sc, _ctr, _scene_obj_names = ESM.build_scene_builtin(RP, parts, _envn.split(":", 1)[1], self.fc)
        else:
            if _envn:
                parts = parts + ESM.env_parts(RP.Part, _envn)
            sc = RP.build_scene(parts, fc=self.fc)
        # --- copied from elevation_sweep_md.py:1050-1057
        RP.place(sc, center=_ctr, az=self.az, el=self.el, rng=self.rng_m, baseline=0.0,
                 pattern=self.antp, cap_db=self.antc, aim_offset_deg=self.aimo)
        p = self.solver(
            sc, los=True, specular_reflection=True, diffuse_reflection=self.diffuse,
            max_depth=self.mdep, **self.sw,
            samples_per_src=self.spp, max_num_paths_per_src=RP.MAX_PATHS, seed=1)
        t_solve = time.time() - t0
        # --- copied from elevation_sweep_md.py:1059
        try:
            aa, tau, _, O = RP.unpack(p, want_doppler=False)
        except ValueError:
            aa = np.zeros(0)
            tau = np.zeros(0)
            O = np.zeros((0, 0), int)
        # --- copied from elevation_sweep_md.py:1087-1088
        try:
            id2nm = {int(_o.object_id): str(_nm) for _nm, _o in sc.objects.items()}
        except Exception:                                              # noqa: BLE001
            id2nm = {}
        # Objects without a name in a built-in scene are called no-name-<counter> by Mitsuba, and the counter grows
        # with every scene load (a CPU smoke test gave no-name-1 at the first load and no-name-3 at the next). Replace
        # them by unnamed[r], r = rank of the counter within this pose's scene, so a path keeps its identity across poses.
        _raw_unnamed = sorted((nm for nm in set(id2nm.values()) if re.fullmatch(r"no-name-\d+", nm)),
                              key=lambda x: int(x.rsplit("-", 1)[1]))
        _alias = {nm: f"unnamed[{r}]" for r, nm in enumerate(_raw_unnamed)}
        id2nm = {k: _alias.get(v, v) for k, v in id2nm.items()}
        P = int(aa.size)
        D = int(O.shape[0]) if O.size else self.mdep
        extras = {}
        for key, getter in (("interactions", lambda: np.asarray(p.interactions)[:, 0, 0, :]),
                            ("primitives", lambda: np.asarray(p.primitives)[:, 0, 0, :]),
                            ("vertices", lambda: np.asarray(p.vertices)[:, 0, 0, :, :])):
            try:
                extras[key] = getter() if P else None
            except Exception as e:                                     # noqa: BLE001
                extras[key] = None
                extras[key + "_error"] = f"{type(e).__name__}: {e}"[:160]
        # --- copied from elevation_sweep_md.py:1124-1125, 1144-1145 (no --det branch)
        if P:
            hit = (O != RP.NO_OBJ).any(axis=0) if O.size else np.zeros(aa.size, bool)
            _t = aa[hit] * np.exp(-1j * 2 * np.pi * self.fc * tau[hit])
            _t_sum = _t
            E = complex(np.sum(_t_sum))
        else:
            hit = np.zeros(0, bool)
            E = 0j
        a_bb = aa * np.exp(-1j * 2 * np.pi * self.fc * tau) if P else np.zeros(0, complex)
        return dict(E=E, aa=aa, a_bb=a_bb, tau=tau, O=np.asarray(O, np.int64) if P else np.zeros((D, 0), np.int64),
                    hit=hit, D=D, P=P, id2nm=id2nm, drone_names=drone_names, unnamed_raw_names=_alias,
                    env_object_names=sorted(set(id2nm.values()) - drone_names),
                    t_solve_s=t_solve, t_total_s=time.time() - t0, **extras)


# ----------------------------------------------------------------------------------------------- per-pose analysis
def classify(res: dict, name_table: list) -> dict:
    """Per-path class, object-name indices and interaction counts."""
    RP_NO = 4294967295
    O, P, D = res["O"], res["P"], res["D"]
    kind = np.zeros((D, P), np.int8)                    # 0 none, 1 drone, 2 environment, 3 unmapped id
    name_idx = np.full((D, P), -1, np.int32)            # -1 no interaction, -2 id not in this pose's map
    n_unmapped = 0
    for v in (np.unique(O) if P else []):
        vi = int(v)
        if vi == RP_NO or vi < 0:
            continue
        sel = O == v
        nm = res["id2nm"].get(vi)
        if nm is None:
            kind[sel], name_idx[sel] = 3, -2
            n_unmapped += int(sel.sum())
            continue
        if nm not in name_table:
            name_table.append(nm)
        name_idx[sel] = name_table.index(nm)
        kind[sel] = 1 if nm in res["drone_names"] else 2
    valid = kind > 0
    hit = valid.any(axis=0) if P else np.zeros(0, bool)
    if P and not np.array_equal(hit, res["hit"]):
        raise RuntimeError("interaction mask from object ids differs from the production mask")
    has_d, has_e, has_u = ((kind == c).any(axis=0) for c in (1, 2, 3)) if P else (np.zeros(0, bool),) * 3
    cls = np.zeros(P, np.int8)
    cls[hit & has_e & ~has_d & ~has_u] = 1
    cls[hit & has_d & ~has_e & ~has_u] = 2
    cls[hit & has_d & has_e & ~has_u] = 3
    cls[hit & has_u] = 4
    return dict(cls=cls, name_idx=name_idx, n_inter=valid.sum(axis=0).astype(np.int8) if P else np.zeros(0, np.int8),
                n_unmapped_entries=n_unmapped)


def path_keys(name_idx, types, prims, n_inter, sel, name_table) -> list:
    """Identity of a path for matching across poses: per valid depth (object name, interaction type, primitive
    index). Types or primitives are None when the solver did not return them. Names (not table indices) keep the
    key stable when checkpoints are reloaded in a different order."""
    out = []
    for j in np.flatnonzero(sel):
        k = []
        for d in range(int(n_inter[j])):
            ni = int(name_idx[d, j])
            k.append((name_table[ni] if ni >= 0 else "unmapped_id", None if types is None else int(types[d, j]),
                      None if prims is None else int(prims[d, j])))
        out.append(tuple(k))
    return out


def describe_path(j, pa, name_table) -> dict:
    ni = int(pa["n_inter"][j])
    objs = [name_table[int(pa["name_idx"][d, j])] if pa["name_idx"][d, j] >= 0 else "unmapped_id"
            for d in range(ni)]
    types = None if pa["types"] is None else [TYPE_NAMES.get(int(pa["types"][d, j]), str(int(pa["types"][d, j])))
                                              for d in range(ni)]
    prims = None if pa["prims"] is None else [int(pa["prims"][d, j]) for d in range(ni)]
    verts = None if pa["verts"] is None else [[round(float(x), 4) for x in pa["verts"][d, j]] for d in range(ni)]
    return dict(index=int(j), a_bb=cpair(pa["a_bb"][j]), abs_a=g6(abs(pa["a_bb"][j])), tau_s=float(pa["tau"][j]),
                path_length_m=g6(float(pa["tau"][j]) * 299792458.0), n_interactions=ni,
                interaction_types=types, objects=objs, primitives=prims, vertices_m=verts,
                path_class=CLASSES[int(pa["cls"][j])])


def pose_record(i, roles, res, cl, cell_field, name_table, m_cell, scale_cell, E_rep, json_k) -> tuple[dict, dict]:
    P = res["P"]
    types = res.get("interactions")
    prims = res.get("primitives")
    verts = res.get("vertices")
    pa = dict(a_bb=res["a_bb"], a_raw=res["aa"], tau=res["tau"], cls=cl["cls"], name_idx=cl["name_idx"],
              n_inter=cl["n_inter"], types=None if types is None else np.asarray(types, np.int64),
              prims=None if prims is None else np.asarray(prims, np.int64),
              verts=None if verts is None else np.asarray(verts, np.float32), obj_raw=res["O"])
    E_rec, E_st = complex(res["E"]), complex(cell_field["E"][i])
    sums = {}
    for c, nm in enumerate(CLASSES):
        sel = cl["cls"] == c
        s = complex(np.sum(res["a_bb"][sel])) if P else 0j
        sums[nm] = dict(n_paths=int(sel.sum()), sum=cpair(s), abs_sum=g6(abs(s)),
                        power=g6(float(np.sum(np.abs(res["a_bb"][sel]) ** 2))) if P else 0.0)
    cls_total = sum(complex(*sums[nm]["sum"]) for nm in CLASSES[1:])
    env_sel = cl["cls"] == 1
    strongest_env = None
    if P and env_sel.any():
        j = int(np.flatnonzero(env_sel)[np.argmax(np.abs(res["a_bb"][env_sel]))])
        strongest_env = describe_path(j, pa, name_table)
        strongest_env["key"] = [list(t) for t in path_keys(pa["name_idx"], pa["types"], pa["prims"], pa["n_inter"],
                                                           np.arange(P) == j, name_table)[0]]
    order = np.argsort(-np.abs(res["a_bb"])) if P else np.zeros(0, int)
    kk = P if json_k < 0 else min(P, json_k)
    rec = dict(
        pose=int(i), roles=sorted(roles["roles"]), neighbour_of=sorted(roles["neighbour_of"]),
        isolated_by_definition=bool(roles["isolated_by_definition"]),
        E_recomputed=cpair(E_rec), E_stored=cpair(E_st),
        rel_err=g6(abs(E_rec - E_st) / abs(E_st)) if abs(E_st) > 0 else None,
        abs_err_over_abs_cell_median=g6(abs(E_rec - E_st) / abs(m_cell)) if abs(m_cell) > 0 else None,
        dev_recomputed_over_scale=g6(abs(E_rec - m_cell) / scale_cell) if scale_cell > 0 else None,
        dev_stored_over_scale=g6(abs(E_st - m_cell) / scale_cell) if scale_cell > 0 else None,
        E_repeat_stored=None if E_rep is None else cpair(E_rep),
        rel_diff_stored_vs_repeat=None if E_rep is None or abs(E_st) == 0 else g6(abs(E_st - E_rep) / abs(E_st)),
        n_paths_returned=P, n_paths_summed=int(res["hit"].sum()) if P else 0,
        npaths_stored=int(cell_field["npaths"][i]), nret_stored=int(cell_field["nret"][i]),
        n_unmapped_object_entries=int(cl["n_unmapped_entries"]),
        unnamed_raw_names=res.get("unnamed_raw_names", {}),
        class_sums=sums,
        class_sum_closure_rel=g6(abs(cls_total - E_rec) / abs(E_rec)) if abs(E_rec) > 0 else None,
        strongest_env_only_path=strongest_env,
        strongest_paths=[describe_path(int(j), pa, name_table) for j in order[:kk]],
        interactions_available=types is not None, primitives_available=prims is not None,
        vertices_available=verts is not None,
        extras_errors={k: v for k, v in res.items() if k.endswith("_error")},
        t_solve_s=round(res["t_solve_s"], 3), t_total_s=round(res["t_total_s"], 3))
    return rec, pa


# ----------------------------------------------------------------------------------------------- summary
def cell_summary(poses: dict, pas: dict, name_table: list, tau_tol: float) -> dict:
    recs = list(poses.values())
    if not recs:
        return dict(n_poses=0)

    def mx(key, sel=lambda r: True):
        v = [r[key] for r in recs if sel(r) and r.get(key) is not None]
        return (g6(max(v)) if v else None), len(v)

    out = {}
    out["max_rel_err_all"], out["n_rel_err"] = mx("rel_err")
    out["max_rel_err_non_isolated"], _ = mx("rel_err", lambda r: not r["isolated_by_definition"])
    out["max_rel_err_isolated"], _ = mx("rel_err", lambda r: r["isolated_by_definition"])
    out["max_abs_err_over_abs_cell_median"], _ = mx("abs_err_over_abs_cell_median")
    out["max_rel_diff_stored_vs_repeat"], out["n_repeat_poses"] = mx("rel_diff_stored_vs_repeat")
    out["n_poses_paths_summed_ne_stored"] = sum(1 for r in recs if r["n_paths_summed"] != r["npaths_stored"])
    out["max_abs_paths_summed_minus_stored"] = max(abs(r["n_paths_summed"] - r["npaths_stored"]) for r in recs)
    out["n_poses_recomputed_isolation_label_differs"] = sum(
        1 for r in recs if r["dev_recomputed_over_scale"] is not None
        and (r["dev_recomputed_over_scale"] > ARGS.factor) != r["isolated_by_definition"])
    out["max_class_sum_closure_rel"], _ = mx("class_sum_closure_rel")

    groups = dict(isolated=[r for r in recs if "isolated" in r["roles"]],
                  neighbour=[r for r in recs if "neighbour" in r["roles"] and not r["isolated_by_definition"]],
                  random=[r for r in recs if "random" in r["roles"]])
    by_group = {}
    for gname, rr in groups.items():
        d = dict(n_poses=len(rr))
        if rr:
            d["median_abs_E_recomputed"] = g6(np.median([abs(complex(*r["E_recomputed"])) for r in rr]))
            d["median_n_paths_returned"] = g6(np.median([r["n_paths_returned"] for r in rr]))
            for nm in CLASSES[1:]:
                d[nm] = dict(median_abs_sum=g6(np.median([r["class_sums"][nm]["abs_sum"] for r in rr])),
                             median_n_paths=g6(np.median([r["class_sums"][nm]["n_paths"] for r in rr])),
                             median_power=g6(np.median([r["class_sums"][nm]["power"] for r in rr])))
            d["n_poses_with_env_only_path"] = sum(1 for r in rr if r["strongest_env_only_path"] is not None)
        by_group[gname] = d
    out["by_group"] = by_group

    def env_keys(i):
        pa = pas[i]
        sel = pa["cls"] == 1
        return path_keys(pa["name_idx"], pa["types"], pa["prims"], pa["n_inter"], sel, name_table), pa["tau"][sel], \
            np.abs(pa["a_bb"][sel])

    def match(i_ref, i_tgt):
        """Is the strongest environment-only path of pose i_ref present among the environment-only paths of
        pose i_tgt (same key, |delay difference| <= tau_tol)? Returns a dict."""
        sref = poses[i_ref]["strongest_env_only_path"]
        if sref is None:
            return None
        key = tuple(tuple(x) for x in sref["key"])
        keys, taus, absa = env_keys(i_tgt)
        cand = [j for j, k in enumerate(keys) if k == key]
        if not cand:
            return dict(present=False, n_same_key=0, nearest_dtau_s=None, abs_ratio=None)
        dt = np.abs(taus[cand] - sref["tau_s"])
        jj = cand[int(np.argmin(dt))]
        return dict(present=bool(dt.min() <= tau_tol), n_same_key=len(cand), nearest_dtau_s=float(dt.min()),
                    abs_ratio=g6(absa[jj] / sref["abs_a"]) if sref["abs_a"] else None)

    per_iso, cls_most = [], {nm: 0 for nm in CLASSES[1:]}
    dvals = {nm: [] for nm in CLASSES[1:]}
    absent_all, absent_pairs, n_pairs, n_iso_scored = 0, 0, 0, 0
    ctrl_present, ctrl_n = 0, 0
    for r in groups["isolated"]:
        i = r["pose"]
        nbrs = [j for j in (i - 1, i + 1) if j in poses and not poses[j]["isolated_by_definition"]]
        row = dict(pose=i, neighbours_used=nbrs)
        if nbrs:
            dc = {}
            for nm in CLASSES[1:]:
                mean_n = np.mean([complex(*poses[j]["class_sums"][nm]["sum"]) for j in nbrs])
                dc[nm] = abs(complex(*r["class_sums"][nm]["sum"]) - mean_n)
                dvals[nm].append(dc[nm])
            tot = sum(dc.values())
            best = max(dc, key=dc.get) if tot > 0 else None
            if best is None:
                cls_most["all_zero"] = cls_most.get("all_zero", 0) + 1
            else:
                cls_most[best] += 1
            row.update(class_abs_diff_to_neighbour_mean={k: g6(v) for k, v in dc.items()},
                       class_share_of_abs_diff={k: (g6(v / tot) if tot > 0 else None) for k, v in dc.items()},
                       class_differing_most=best)
            ms = [match(j, i) for j in nbrs]
            ms_ok = [m_ for m_ in ms if m_ is not None]
            row["neighbour_strongest_env_path_at_isolated_pose"] = ms
            if ms_ok:
                n_iso_scored += 1
                absent_all += int(all(not m_["present"] for m_ in ms_ok))
                absent_pairs += sum(int(not m_["present"]) for m_ in ms_ok)
                n_pairs += len(ms_ok)
            if len(nbrs) == 2:
                c = match(nbrs[0], nbrs[1])
                row["control_left_neighbour_strongest_env_path_at_right_neighbour"] = c
                if c is not None:
                    ctrl_n += 1
                    ctrl_present += int(c["present"])
            if r["strongest_env_only_path"] is not None:
                row["strongest_env_only_path_at_isolated_pose"] = {
                    k: r["strongest_env_only_path"][k] for k in ("objects", "interaction_types", "tau_s", "abs_a")}
        per_iso.append(row)
    out["isolated_vs_neighbours"] = per_iso
    out["class_differing_most_counts"] = cls_most
    out["median_class_abs_diff_to_neighbour_mean"] = {k: (g6(np.median(v)) if v else None) for k, v in dvals.items()}
    out["n_isolated_scored_for_env_path"] = n_iso_scored
    out["fraction_isolated_where_neighbours_strongest_env_path_absent"] = \
        g6(absent_all / n_iso_scored) if n_iso_scored else None
    out["fraction_neighbour_pairs_strongest_env_path_absent_at_isolated"] = g6(absent_pairs / n_pairs) if n_pairs else None
    out["control_fraction_left_neighbour_strongest_env_path_present_at_right_neighbour"] = \
        g6(ctrl_present / ctrl_n) if ctrl_n else None
    out["control_n_pairs"] = ctrl_n
    # Random-pose control: the most common strongest environment-only path key among the random poses and the
    # fraction of random poses where that path is present.
    rr = [r for r in groups["random"] if r["strongest_env_only_path"] is not None]
    if rr:
        keys = [json.dumps(r["strongest_env_only_path"]["key"]) for r in rr]
        mode = max(sorted(set(keys)), key=keys.count)
        ref = next(r for r in rr if json.dumps(r["strongest_env_only_path"]["key"]) == mode)
        pres = [match(ref["pose"], r["pose"]) for r in groups["random"]]
        out["random_control"] = dict(reference_pose=ref["pose"], n_random_with_same_strongest_key=keys.count(mode),
                                     fraction_random_poses_reference_path_present=g6(
                                         np.mean([bool(p_ and p_["present"]) for p_ in pres])),
                                     reference_path={k: ref["strongest_env_only_path"][k]
                                                     for k in ("objects", "interaction_types", "tau_s", "abs_a")})
    else:
        out["random_control"] = None
    return out


# ----------------------------------------------------------------------------------------------- main
def meta_block(status: str, variant: str | None, cells_meta: list) -> dict:
    prod_eq = [c.get("production_equivalent") for c in cells_meta]
    return dict(
        generator=f"benchmark/{NAME}.py",
        command="python -B benchmark/" + NAME + ".py " + " ".join(sys.argv[1:]),
        argv=sys.argv[1:],
        started_utc=utc(STARTED), finished_utc=utc() if status == "complete" else None,
        wall_time_s=round(time.time() - T0, 1), status=status,
        git_head=git_head(),
        versions=dict(solver_build=ESM.SOLVER_BUILD, python=platform.python_version(), numpy=np.__version__,
                      mitsuba_variant=variant, thread_guard=getattr(ESM, "_TG", None)),
        env=dict(CUDA_VISIBLE_DEVICES=os.environ.get("CUDA_VISIBLE_DEVICES"),
                 OMP_NUM_THREADS=os.environ.get("OMP_NUM_THREADS"),
                 SIONNA2_MAX_PATHS=os.environ.get("SIONNA2_MAX_PATHS"),
                 DRJIT_LIBOPTIX_PATH=os.environ.get("DRJIT_LIBOPTIX_PATH"),
                 LD_LIBRARY_PATH=os.environ.get("LD_LIBRARY_PATH"),
                 MESH_FIX=os.environ.get("MESH_FIX"), BLADE_LAW=os.environ.get("BLADE_LAW"),
                 cpu_affinity=sorted(os.sched_getaffinity(0))),
        device=ARGS.device, spp_override=int(ARGS.spp) or None,
        production_equivalent=all(bool(x) for x in prod_eq) if prod_eq else None,
        scope=("Re-solve of chosen poses of production PathSolver cells (outdoor scenes) with the production scene, "
               "placement and solver call; lists every returned path. Simulation bookkeeping only: no RF measurement "
               "comparison; differences between poses are observations of the solver output and are not called "
               "solver faults. A run with spp or device different from production cannot reproduce E_stored."),
        seeds=dict(random_pose_draw=int(ARGS.seed), solver_seed=1),
        parameters=dict(n_outliers=ARGS.n_outliers, n_random=ARGS.n_random, factor=ARGS.factor,
                        max_poses=ARGS.max_poses, json_paths=ARGS.json_paths, tau_tol_s=ARGS.tau_tol_s),
        reused_by_import=REUSED,
        copied=[dict(source=ESM_REL, **c) for c in COPIED],
        copied_source_sha256=sha256_file(ROOT / ESM_REL),
        copied_anchor_check=dict(n_anchors=len(ANCHORS), all_match=True),
        script_sha256=sha256_file(SCRIPT),
        outputs=dict(json=str(OUT.relative_to(ROOT)) if OUT.is_relative_to(ROOT) else OUT.name,
                     paths_npz=OUT_NPZ.name, checkpoints=CKPT.name),
        definitions={
            "complex numbers": "written as [real, imag].",
            "cell complex median m": "median(Re E) + 1j*median(Im E) over all poses of the merged stored field.",
            "scale": "median over poses of |E - m| (stored field).",
            "isolated pose": "|E - m| > factor * scale on the stored field (factor 20 as in the ledger's primary factor).",
            "roles": "isolated = among the first n_outliers isolated poses; neighbour = pose i-1 or i+1 of a chosen "
                     "isolated pose; random = drawn without replacement from poses that are neither isolated nor "
                     "chosen, generator numpy default_rng(seeds.random_pose_draw + cell index). A pose can carry several roles.",
            "E_recomputed": "sum over paths with at least one interaction of a*exp(-j*2*pi*fc*tau), path order as "
                            "returned (elevation_sweep_md.py:1124-1125, 1144-1145).",
            "a_bb": "a*exp(-j*2*pi*fc*tau) per path (the production summand); a is the solver's passband coefficient.",
            "rel_err": "|E_recomputed - E_stored| / |E_stored|.",
            "abs_err_over_abs_cell_median": "|E_recomputed - E_stored| / |m| (useful where |E_stored| is small).",
            "rel_diff_stored_vs_repeat": "|E_stored - E_rep1| / |E_stored| for the stored repeat run (_rep1) of the "
                                         "same cell when it exists: run-to-run spread of production at that pose.",
            "objects": "scene object name per interaction, from the per-pose object_id -> name map "
                       "(elevation_sweep_md.py:1087-1088); drone parts are the Part names <drone>_<group> placed in "
                       "the scene, every other mapped name is an environment object.",
            "unnamed[r]": "an object without a name in a built-in scene; Mitsuba calls it no-name-<counter> and the "
                          "counter grows with every scene load, so the listing uses r = rank of the counter within "
                          "the pose's scene; the raw names are kept per pose in unnamed_raw_names.",
            "path classes": "none = no interaction (not in E); env_only = only environment objects; drone_only = "
                            "only drone parts; both = at least one of each; unmapped = an object id missing from the "
                            "pose's map.",
            "class_sum_closure_rel": "|sum of class sums (env_only+drone_only+both+unmapped) - E_recomputed| / |E_recomputed|.",
            "path key": "per interaction (object name, interaction type, primitive index); used to match a "
                        "path between poses together with |delay difference| <= tau_tol_s.",
            "class_differing_most": "for an isolated pose i with non-isolated computed neighbours N: the class c "
                                    "maximising |S_c(i) - mean_{j in N} S_c(j)|, S_c = complex class sum; None (counted as all_zero) when "
                                    "every class difference is zero.",
            "fraction_isolated_where_neighbours_strongest_env_path_absent": "over isolated poses with at least one "
                "non-isolated neighbour carrying an environment-only path: share of isolated poses at which the "
                "strongest environment-only path of every such neighbour has no match.",
            "control_fraction_left_neighbour_strongest_env_path_present_at_right_neighbour": "for isolated poses with "
                "two non-isolated neighbours: share where the strongest environment-only path of pose i-1 has a match "
                "at pose i+1 (two poses apart, no isolated label).",
            "random_control": "most common strongest environment-only path key among random poses and the share of "
                              "random poses where that path has a match.",
            "production_equivalent": "device variant is CUDA and the ray count equals the arm's ray count.",
            "interaction types": TYPE_NAMES,
        },
        assumptions=[
            "The production pose loop builds the in-memory drone meshes from the shard's first pose and replaces "
            "the vertices before every solve; this script starts the cache from its first solved pose.",
            "The production process solved thousands of poses before a given pose; this process solves few. Mitsuba "
            "object ids differ with that history; the equivalence check against E_stored measures whether that matters.",
            "Accessing Paths.interactions, primitives and vertices after unpack does not change a or tau.",
        ],
        cells=cells_meta,
    )


def main() -> None:
    cells_arg = ARGS.cells or list(DEFAULT_CELLS)
    cells = []
    for c in cells_arg:
        arm, _, el = c.rpartition("@")
        if not arm:
            raise SystemExit(f"--cells expects ARM@EL, got {c!r}")
        cells.append((arm, float(el)))

    variant = None
    out_cells, cells_meta = [], []
    all_pa = []                                        # (cell index, pose, pa) for the npz
    name_table: list[str] = []
    CKPT.mkdir(parents=True, exist_ok=True)

    for ci, (arm, el) in enumerate(cells):
        log(f"== cell {ci}: {arm} el {el:+g}")
        argv, fields = job_argv(arm, el)
        field = load_cell_field(arm, el)
        a = production_namespace(argv)
        names = dry_run_names(a, field["nshards"])
        want = [p["file"] for p in field["parts"]]
        if names != want:
            raise SystemExit(f"dry-run shard names differ from the stored shards:\n  dry {names}\n  disk {want}")
        import mitsuba as _mi                                           # already imported by the dry run
        variant = _mi.variant()
        if ARGS.device == "gpu":
            ESM.require_cuda_variant()
            if not str(variant).startswith("cuda"):
                raise SystemExit(f"--device gpu but the Mitsuba variant is {variant!r}")
        elif not str(variant).startswith("llvm"):
            raise SystemExit(f"--device cpu but the Mitsuba variant is {variant!r}")
        import report15_probe as RP
        caps = {tuple(p["n_trunc"]) if p["n_trunc"] else None for p in field["parts"]}
        builds = {p["solver_build"] for p in field["parts"]}
        if any(cap is None or int(cap[1]) != int(RP.MAX_PATHS) for cap in caps):
            raise SystemExit(f"shard path cap {caps} differs from RP.MAX_PATHS {RP.MAX_PATHS}")
        if builds != {ESM.SOLVER_BUILD}:
            raise SystemExit(f"shard solver build {builds} differs from this installation {ESM.SOLVER_BUILD}")

        iso, m_cell, scale = isolated_poses(field["E"], ARGS.factor)
        row, ledger_path = ledger_row(arm, el)
        ledger = None
        if row is not None:
            li = [int(x) for x in row.get("outlier_pose_indices", [])]
            nkey = f"f{ARGS.factor:g}"
            ledger = dict(file=ledger_path, n_outlier_poses=(row.get("n_outlier_poses") or {}).get(nkey),
                          n_isolated_recomputed=int(iso.size),
                          count_matches=(row.get("n_outlier_poses") or {}).get(nkey) == int(iso.size),
                          listed_indices=len(li), listed_truncated=row.get("outlier_pose_indices_truncated"),
                          listed_indices_match=li == [int(x) for x in iso[:len(li)]])
            if not (ledger["count_matches"] and ledger["listed_indices_match"]):
                raise SystemExit(f"isolated poses recomputed from the shards differ from the ledger row: {ledger}")
        rep_arm = rep_sibling(fields)
        E_rep = None
        rep_info = None
        if rep_arm:
            try:
                fr = load_cell_field(rep_arm, el)
                if fr["n"] == field["n"]:
                    E_rep = fr["E"]
                    rep_info = dict(arm=rep_arm, files=[p["file"] for p in fr["parts"]])
            except SystemExit as e:
                rep_info = dict(arm=rep_arm, unavailable=str(e)[:200])

        order, roles, chosen_iso, rand = select_poses(field["n"], iso, ARGS.n_outliers, ARGS.n_random,
                                                      ARGS.seed + ci, ARGS.max_poses)
        cs = CellSolver(a, el, ARGS.spp)
        ESM._check_runtime_build()
        if cs.n != field["n"]:
            raise SystemExit(f"pose count {cs.n} differs from the stored field {field['n']}")
        prod_eq = str(variant).startswith("cuda") and cs.spp == cs.spp_prod
        stamp = dict(arm=arm, el=el, spp=cs.spp, variant=variant, solver_build=ESM.SOLVER_BUILD,
                     max_paths=int(RP.MAX_PATHS), seed=1, factor=ARGS.factor, json_paths=ARGS.json_paths,
                     shard_sha256=[p.get("sha256") for p in field["parts"]], script_sha256=sha256_file(SCRIPT),
                     optix=os.environ.get("DRJIT_LIBOPTIX_PATH"))
        cmeta = dict(arm=arm, el_deg=el, job_argv=argv, env_argument=a.env, n_poses=field["n"],
                     nshards=field["nshards"],
                     shards=[{k: v for k, v in p.items() if k in ("file", "sha256", "n_trunc", "solver_build",
                                                                  "t_start", "run_id")} for p in field["parts"]],
                     dry_run_shard_names_match=True, spp_production=cs.spp_prod, spp_used=cs.spp,
                     production_equivalent=bool(prod_eq), max_paths=int(RP.MAX_PATHS),
                     carrier_hz=cs.fc, range_m=cs.rng_m, az_deg=cs.az, prf_hz=cs.prf, max_depth=cs.mdep,
                     switches=cs.sw, diffuse=cs.diffuse, drone=cs.spec.key,
                     cell_complex_median=cpair(m_cell), scale=g6(scale), factor=ARGS.factor,
                     n_isolated=int(iso.size), isolated_indices=[int(x) for x in iso],
                     ledger_check=ledger, repeat_cell=rep_info,
                     selected=dict(isolated=chosen_iso, random=rand, solve_order=order))
        cells_meta.append(cmeta)
        if not prod_eq:
            log("  NOTE: spp or device differs from production; E_recomputed cannot reproduce E_stored.")
        log(f"  isolated {iso.size} · solving {len(order)} poses · spp {cs.spp:,} · variant {variant}")

        ck_dir = CKPT / f"c{ci}_{hashlib.sha1(f'{arm}@{el:+g}'.encode()).hexdigest()[:10]}"
        ck_dir.mkdir(parents=True, exist_ok=True)
        poses, pas = {}, {}
        cell_out = dict(arm=arm, el_deg=el, poses=[], summary=None)
        out_cells.append(cell_out)
        for k, i in enumerate(order):
            ck = ck_dir / f"pose_{i:05d}.npz"
            rec = pa = None
            if ck.exists():
                try:
                    with np.load(ck, allow_pickle=False) as z:
                        if json.loads(str(z["stamp_json"])) == stamp:
                            rec = json.loads(str(z["record_json"]))
                            nt = json.loads(str(z["name_table_json"]))
                            remap = np.array([name_table.index(nm) if nm in name_table
                                              else (name_table.append(nm) or len(name_table) - 1) for nm in nt]
                                             + [0], np.int32)
                            ni = z["name_idx"]
                            ni = np.where(ni >= 0, remap[np.clip(ni, 0, None)], ni)
                            pa = dict(a_bb=z["a_bb"], a_raw=z["a_raw"], tau=z["tau"], cls=z["cls"], name_idx=ni,
                                      n_inter=z["n_inter"],
                                      types=z["types"] if bool(z["has_types"]) else None,
                                      prims=z["prims"] if bool(z["has_prims"]) else None,
                                      verts=z["verts"] if bool(z["has_verts"]) else None, obj_raw=z["obj_raw"])
                            rec["roles"], rec["neighbour_of"] = sorted(roles[i]["roles"]), sorted(roles[i]["neighbour_of"])
                            log(f"  [{k + 1}/{len(order)}] pose {i} from checkpoint")
                except Exception as e:                                 # noqa: BLE001
                    log(f"  checkpoint {ck.name} unreadable ({type(e).__name__}); solving again")
                    rec = pa = None
            if rec is None:
                res = cs.solve(i)
                cl = classify(res, name_table)
                rec, pa = pose_record(i, roles[i], res, cl, field, name_table, m_cell, scale,
                                      None if E_rep is None else complex(E_rep[i]), ARGS.json_paths)
                D, P = res["D"], res["P"]
                atomic_npz(ck, stamp_json=np.array(json.dumps(stamp)), record_json=np.array(json.dumps(rec)),
                           name_table_json=np.array(json.dumps(name_table)),
                           a_bb=pa["a_bb"], a_raw=pa["a_raw"], tau=pa["tau"], cls=pa["cls"], name_idx=pa["name_idx"],
                           n_inter=pa["n_inter"], obj_raw=pa["obj_raw"],
                           has_types=np.array(pa["types"] is not None),
                           types=pa["types"] if pa["types"] is not None else np.zeros((D, P), np.int64),
                           has_prims=np.array(pa["prims"] is not None),
                           prims=pa["prims"] if pa["prims"] is not None else np.zeros((D, P), np.int64),
                           has_verts=np.array(pa["verts"] is not None),
                           verts=pa["verts"] if pa["verts"] is not None else np.zeros((D, P, 3), np.float32))
                log(f"  [{k + 1}/{len(order)}] pose {i} {','.join(rec['roles'])}: paths {P} "
                    f"(summed {rec['n_paths_summed']}, stored {rec['npaths_stored']}) · rel_err {rec['rel_err']} · "
                    f"env_only |S| {rec['class_sums']['env_only']['abs_sum']} · drone_only |S| "
                    f"{rec['class_sums']['drone_only']['abs_sum']} · both |S| {rec['class_sums']['both']['abs_sum']} · "
                    f"{rec['t_total_s']} s")
            poses[i], pas[i] = rec, pa
            cell_out["poses"] = [poses[j] for j in order if j in poses]
            atomic_json(OUT, dict(_meta=meta_block("partial", variant, cells_meta), name_table=name_table,
                                  cells=out_cells))
        cell_out["summary"] = cell_summary(poses, pas, name_table, ARGS.tau_tol_s)
        all_pa += [(ci, i, pas[i]) for i in order]
        s = cell_out["summary"]
        log(f"  summary: max rel_err {s.get('max_rel_err_all')} (non-isolated {s.get('max_rel_err_non_isolated')}, "
            f"isolated {s.get('max_rel_err_isolated')}) · isolation label differs "
            f"{s.get('n_poses_recomputed_isolation_label_differs')} · repeat spread max {s.get('max_rel_diff_stored_vs_repeat')} · "
            f"class differing most {s.get('class_differing_most_counts')} · neighbours' strongest env path absent "
            f"at isolated {s.get('fraction_isolated_where_neighbours_strongest_env_path_absent')}")
        atomic_json(OUT, dict(_meta=meta_block("partial", variant, cells_meta), name_table=name_table, cells=out_cells))

    # Complete per-path listing: paths of all poses concatenated in (cell, solve order); offsets from n_paths.
    Dmax = max([pa["name_idx"].shape[0] for _, _, pa in all_pa] + [1])

    def padD(x, fill, dtype, tail=()):
        D, P = x.shape[0], x.shape[1]
        y = np.full((Dmax, P) + tail, fill, dtype)
        y[:D] = x
        return y

    NO_ID = 4294967295
    cat = lambda xs, axis=0: np.concatenate(xs, axis=axis) if xs else np.zeros(0)  # noqa: E731
    atomic_npz(
        OUT_NPZ,
        cells=np.array([f"{arm}@{el:+g}" for arm, el in cells]), name_table=np.array(name_table),
        class_names=np.array(CLASSES),
        rec_cell=np.array([c for c, _, _ in all_pa], np.int32), rec_pose=np.array([i for _, i, _ in all_pa], np.int32),
        n_paths=np.array([pa["a_bb"].size for _, _, pa in all_pa], np.int64),
        a_bb=cat([pa["a_bb"].astype(np.complex128) for _, _, pa in all_pa]),
        a_raw=cat([pa["a_raw"].astype(np.complex64) for _, _, pa in all_pa]),
        tau_s=cat([pa["tau"].astype(np.float64) for _, _, pa in all_pa]),
        path_class=cat([pa["cls"] for _, _, pa in all_pa]),
        n_interactions=cat([pa["n_inter"] for _, _, pa in all_pa]),
        object_name_index=cat([padD(pa["name_idx"], -1, np.int16) for _, _, pa in all_pa], axis=1),
        object_id_raw=cat([padD(pa["obj_raw"], NO_ID, np.uint32) for _, _, pa in all_pa], axis=1),
        interaction_type=cat([padD(pa["types"] if pa["types"] is not None
                                   else np.full(pa["name_idx"].shape, -1), -1, np.int8) for _, _, pa in all_pa], axis=1),
        primitive=cat([padD(pa["prims"] if pa["prims"] is not None
                            else np.full(pa["name_idx"].shape, NO_ID), NO_ID, np.uint32) for _, _, pa in all_pa], axis=1),
        vertex_m=cat([padD(pa["verts"] if pa["verts"] is not None
                           else np.full(pa["name_idx"].shape + (3,), np.nan), np.nan, np.float32, (3,))
                      for _, _, pa in all_pa], axis=1),
        note=np.array("Per-path listing. Path axis concatenates poses in record order (rec_cell, rec_pose; offsets = "
                      "cumsum of n_paths). Depth-indexed arrays are [depth, path]; object_name_index -1 = no "
                      "interaction, -2 = object id missing from the pose's map; object_id_raw and primitive use 4294967295 for no "
                      "interaction or not available; interaction_type -1 = not available. object_id_raw values are "
                      "per-pose Mitsuba ids (use object_name_index). a_bb = a*exp(-j*2*pi*fc*tau) (complex128); "
                      "a_raw is the solver coefficient a stored as complex64. path_class indexes class_names."),
    )
    atomic_json(OUT, dict(_meta=meta_block("complete", variant, cells_meta), name_table=name_table, cells=out_cells))
    log(f"wrote {OUT} and {OUT_NPZ}")


if __name__ == "__main__":
    main()
