#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dropout_hash_vs_buffer_0916.py - at the isolated poses of a production cell, which knob brings the
missing environment-only path back: the specular-chain hash counter, or the candidate buffer?

Why this script exists
    benchmark/dropout_knobs_0916.py showed that raising --max-paths removes most isolated poses of a
    production PathSolver cell (ground cell at el -60: 161 / 90 / 34 / 22 / 15 isolated poses at
    1e6 / 2e6 / 8e6 / 16e6 / 32e6, the sets nesting), and benchmark/dropout_paths_0916.py showed what
    changes at such a pose: one environment-only specular path that both neighbour poses carry is
    absent, and no new environment path appears.
    That ladder cannot say *which* mechanism does it, because in
    sionna/rt/path_solvers/sb_candidate_generator.py the argument max_num_paths_per_src sets two things
    at once:
      (a) the candidate buffer            max_num_paths = max_num_paths_per_src * num_sources   (line 107)
      (b) the specular-chain hash counter spec_counter_size = max(max_num_paths_per_src,
                                                                 MIN_SPEC_COUNT_SIZE = 1e6)     (lines 59, 313-315)
    and the generator's own docstring says candidates can be lost to hash collisions (lines 43-45).
    MIN_SPEC_COUNT_SIZE is a class attribute, so the hash counter can be made larger while the buffer
    stays at the production value. That is the separation this script runs.

How the grid separates the two knobs (read this before reading the numbers)
    spec_counter_size = max(buffer, MIN_SPEC_COUNT_SIZE), so a buffer above 1e6 raises the hash counter
    with it — but the grid still gives both single-knob contrasts, because two points can share a hash
    counter and differ only in the buffer:
      * hash alone, at a fixed buffer:   production (2e6, hash 2e6) -> hash8 (2e6, hash 8e6)
                                         production (2e6, hash 2e6) -> hash32 (2e6, hash 32e6)
      * buffer alone, at a fixed hash:   hash8 (buffer 2e6, hash 8e6)  -> both8 (buffer 8e6, hash 8e6)
                                         hash32 (buffer 2e6, hash 32e6) -> both32 (buffer 32e6, hash 32e6)
      * both at once (attributes nothing on its own): production -> both8 / both32, which are the
        ladder rungs bought by queue 0945.
    The ray set is identical at every grid point (the sampler is seeded from samples_per_src alone), and
    the allocated hash counter is measured, not assumed, so the pairs above differ in one knob only.
    summary.paired_contrasts carries these pairs. This reading rule is declared before the run and is
    written into _meta.reading_rule.

What the result can and cannot say
    CAN: which knob, when moved, makes the solver return again the environment-only path that the
         neighbour poses carry, and how the pose's field E, its path count and its per-class complex
         sums move with each knob; and that the poses which are not isolated do not move when the
         knobs move (a control that must hold, or the whole comparison is meaningless).
    CANNOT: why a candidate is lost. This script never looks inside the shoot-and-bounce loop; it does
         not count hash collisions, does not instrument the buffer's fill, and does not show that the
         lost candidate is the same object as the missing path. "The hash counter restores it" is a
         statement about a knob, not about a mechanism, and certainly not about the solver being wrong
         (both engines in this repository are approximations; realism is for measurement, of which
         there is none here).
    CANNOT: anything about a radio measurement, a detector, or a real radar. Simulation bookkeeping only.
    CANNOT: reproduce production numbers when run with --device cpu or with --spp different from the
         arm's ray count; such a run is marked production_equivalent = false and its isolation labels
         are meaningless (they are computed against the stored production field's median and scale).

Grid (default)
    name        buffer (max_num_paths_per_src)   MIN_SPEC_COUNT_SIZE   hash counter = max(buffer, MIN)
    production  2e6                              stock (1e6)           2e6     <- reproduces production
    hash8       2e6                              8e6                   8e6     <- hash only
    hash32      2e6                              32e6                  32e6    <- hash only
    both8       8e6                              stock (1e6)           8e6     <- the 8e6 ladder rung
    both32      32e6                             stock (1e6)           32e6    <- the 0945 ladder rung
    Both knobs are read back after every solve from the arguments the candidate generator actually
    received and from the buffer it actually allocated (KnobProbe below); a mismatch stops the run.

Poses (chosen from the stored shards, a few tens per cell, all counts are CLI options)
    recovered  isolated at the production cap but not at the relief cap (--relief-cap, default 32e6)
    core       isolated at both caps
    neighbour  poses i-1 and i+1 of every chosen recovered/core pose
    control    random poses isolated at neither cap and not neighbours of a chosen pose
    Every pose is solved at every grid point.

Precondition (checked, and refused with the exact fix if it does not hold)
    benchmark/dropout_paths_0916.py verifies at import time that its copied ranges still sit where its
    ANCHORS table says they do in benchmark/elevation_sweep_md.py, and stops the process if they do not.
    That table went stale twice: on 2026-09-16 (--solver-seed, one or two lines) and on 2026-09-17
    (--ant-orient, commit 5d3329d6, +20 lines); both tables were re-anchored on 2026-09-17. If it goes
    stale again this script refuses to start and prints the new line numbers; re-anchor that table first.
    The copied code itself is unchanged, except that the production solver call now reads
    seed=int(getattr(a, "solver_seed", 1)) over two lines, which equals the copied seed=1 only for job lines
    without --ss (this script checks that on the parsed job namespace and refuses otherwise), and that the
    builder's placement call now passes orient=_orient, which is "auto" for the iso cells this script takes.

Production run (GPU; run by the main session)
    cd /workspace/sionna && CUDA_VISIBLE_DEVICES=<free card> OMP_NUM_THREADS=2 \
        DRJIT_LIBOPTIX_PATH=/workspace/.venvs/optix/libnvoptix.so.1 \
        LD_LIBRARY_PATH=/workspace/.venvs/optix:$LD_LIBRARY_PATH taskset -c 12,13 \
        /workspace/.venvs/py312/bin/python -B benchmark/dropout_hash_vs_buffer_0916.py
    Refuses to start without those two OptiX variables, on a card listed in runners/GPU_HOLD.json, on a
    solver build different from the shards, or when the isolated poses recomputed from the shards
    disagree with the ledgers (outputs/isac_plan_corpus_0915.json and outputs/dropout_knobs_0916.json).
    Cost with the defaults (ground cell, 5 grid points, up to 6+6 chosen poses + their neighbours + 6
    controls = at most 42 poses): about 210 solves at roughly 1.35 s each, so around 10 min of solving
    plus scene loading and kernel compilation per grid point; call it 20-25 min. GPU memory: about
    1.3 GiB at the production point (measured on production workers of this arm) and about 4-5 GiB at the
    32e6 points (the candidate buffer is roughly 90 B per path at depth 2, plus 2 x 32e6 x 4 B of hash
    counters), so run it on a card with at least 8 GiB free. The street canyon has no 32e6 shards; for
    that cell pass --relief-cap 8000000 (its runtime is about 2.5x the ground cell's).

CPU smoke test (proves the script runs end to end; it CANNOT reproduce production E, and at 1e6 rays the
dropout does not occur at all, so the per-grid-point counts of such a run mean nothing)
    CUDA_VISIBLE_DEVICES="" SIONNA2_ALLOW_CPU=1 OMP_NUM_THREADS=1 taskset -c 11 \
      /workspace/.venvs/py312/bin/python -B benchmark/dropout_hash_vs_buffer_0916.py \
      --root /workspace/sionna --device cpu --out <scratch>/smoke.json --spp 1000000 \
      --n-recovered 1 --n-core 0 --n-random 1 --neighbours 1 \
      --grid production:2000000:stock --grid hash32:2000000:32000000

Arguments
    --root DIR          repository root (default: parent of this script's directory)
    --out FILE          output JSON (default ROOT/outputs/dropout_hash_vs_buffer_0916.json)
    --cells ARM@EL      repeatable; default the production ground cell at el -60
    --relief-cap N      path cap of the stored cell that defines "recovered" vs "core" (default 32000000)
    --grid SPEC         repeatable NAME:BUFFER:MINSPEC, MINSPEC "stock" leaves the class attribute alone
    --n-recovered N     recovered poses per cell (default 6)
    --n-core N          core poses per cell (default 6)
    --n-random N        random non-isolated control poses per cell (default 6)
    --neighbours 0|1    also solve poses i-1 and i+1 of every chosen pose (default 1)
    --pick MODE         spread | first | random - how the N poses are taken from the list (default spread)
    --seed S            seed of the random pose draw (default 20260916)
    --factor K          isolation factor (default 20, the ledger's primary factor)
    --noise-tol T       a pose "moved" when |E(grid) - E(production grid)| / |cell median| > T
                        (default 2e-5, the repeat noise of the ladder)
    --tau-tol-s T       delay tolerance when matching a path between poses (default 1e-12 s)
    --spp N             ray count override (smoke test only; default = the arm's ray count)
    --device gpu|cpu    gpu requires a CUDA Mitsuba variant and an explicit CUDA_VISIBLE_DEVICES
    --max-poses N       cap on poses per cell (smoke test only; 0 = no cap)
    --json-paths K      strongest paths per pose written into the JSON (default 4)
    --keep-paths        also store the full per-path arrays in every checkpoint (large; default off)
    --cores LIST        optional CPU affinity (comma list) applied with os.sched_setaffinity

Reuse (nothing in the repository is modified; benchmark/dropout_paths_0916.py is imported)
    From benchmark/dropout_paths_0916.py: CellSolver (production scene, placement and PathSolver call,
    itself copied from benchmark/elevation_sweep_md.py), load_cell_field, isolated_poses, job_argv,
    production_namespace, dry_run_names, ledger_row, classify, pose_record, path_keys, describe_path,
    atomic_json, atomic_npz, sha256_file, cpair, g6, CLASSES.
    dropout_paths_0916.py parses its CLI at import time, so this script sets sys.argv before importing
    it and restores sys.argv afterwards. That works, and its device guard (hiding the GPUs before any
    CUDA-capable module is imported) then runs for this script too.
    Not reused: dropout_paths_0916.cell_summary and meta_block read that script's own ARGS namespace.
    The pose selection is written here because the roles differ (recovered / core / neighbour / control).

Scope
    Outdoor scenes only. Simulation bookkeeping. No RF measurement is involved and none is implied.
"""
from __future__ import annotations

import argparse
import os
import sys

NAME = "dropout_hash_vs_buffer_0916"
DEFAULT_CELLS = (
    "sionna_p4000000000_swR0D0E0F1_r15_n8192_envoutdoor01_ground_mfixbatteryi5_blperairframe_rt210_d2@-60",
)
DEFAULT_GRID = ("production:2000000:stock", "hash8:2000000:8000000", "hash32:2000000:32000000",
                "both8:8000000:stock", "both32:32000000:stock")
OPTIX_LIB = "/workspace/.venvs/optix/libnvoptix.so.1"
OPTIX_DIR = "/workspace/.venvs/optix"
#: stock value of SBCandidateGenerator.MIN_SPEC_COUNT_SIZE in sionna-rt 2.1.0; checked against the class.
STOCK_MIN_SPEC = 1_000_000


def _cli() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--cells", action="append", default=None, metavar="ARM@EL")
    ap.add_argument("--relief-cap", type=int, default=32_000_000)
    ap.add_argument("--grid", action="append", default=None, metavar="NAME:BUFFER:MINSPEC")
    ap.add_argument("--n-recovered", type=int, default=6)
    ap.add_argument("--n-core", type=int, default=6)
    ap.add_argument("--n-random", type=int, default=6)
    ap.add_argument("--neighbours", type=int, choices=(0, 1), default=1)
    ap.add_argument("--pick", choices=("spread", "first", "random"), default="spread")
    ap.add_argument("--seed", type=int, default=20260916)
    ap.add_argument("--factor", type=float, default=20.0)
    ap.add_argument("--noise-tol", type=float, default=2e-5)
    ap.add_argument("--tau-tol-s", type=float, default=1e-12)
    ap.add_argument("--spp", type=int, default=0)
    ap.add_argument("--device", choices=("gpu", "cpu"), default="gpu")
    ap.add_argument("--max-poses", type=int, default=0)
    ap.add_argument("--json-paths", type=int, default=4)
    ap.add_argument("--keep-paths", action="store_true")
    ap.add_argument("--cores", default="")
    return ap.parse_args()


ARGS = _cli()

# --------------------------------------------------------------------------------------------- device
# Same guard as benchmark/dropout_paths_0916.py, applied here first so that nothing CUDA-capable is
# imported before the GPUs are hidden on a CPU run.
if ARGS.device == "cpu":
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    os.environ["SIONNA2_ALLOW_CPU"] = "1"
else:
    if not os.environ.get("CUDA_VISIBLE_DEVICES", "").strip():
        raise SystemExit("--device gpu needs an explicit CUDA_VISIBLE_DEVICES (for example "
                         "CUDA_VISIBLE_DEVICES=3); without it the card is chosen for you.")
    if os.environ.get("DRJIT_LIBOPTIX_PATH") != OPTIX_LIB:
        raise SystemExit(
            f"--device gpu needs DRJIT_LIBOPTIX_PATH={OPTIX_LIB} (what runners/worker_supervisor.py gives "
            "production workers). Run:\n"
            f"  CUDA_VISIBLE_DEVICES=<card> DRJIT_LIBOPTIX_PATH={OPTIX_LIB} "
            f"LD_LIBRARY_PATH={OPTIX_DIR}:$LD_LIBRARY_PATH "
            f"/workspace/.venvs/py312/bin/python -B benchmark/{NAME}.py")
    if OPTIX_DIR not in [p for p in os.environ.get("LD_LIBRARY_PATH", "").split(":") if p]:
        raise SystemExit(f"--device gpu needs {OPTIX_DIR} on LD_LIBRARY_PATH (production workers get "
                         f"LD_LIBRARY_PATH={OPTIX_DIR}:... from runners/worker_supervisor.py); it is "
                         f"{os.environ.get('LD_LIBRARY_PATH')!r}")
if ARGS.cores:
    os.sched_setaffinity(0, {int(c) for c in ARGS.cores.split(",") if c.strip()})

import ast                                                             # noqa: E402
import datetime as _dt                                                 # noqa: E402
import hashlib                                                         # noqa: E402
import json                                                            # noqa: E402
import platform                                                        # noqa: E402
import time                                                            # noqa: E402
from pathlib import Path                                               # noqa: E402

SCRIPT = Path(__file__).resolve()
ROOT = Path(ARGS.root).resolve() if ARGS.root else SCRIPT.parents[1]
OUT = Path(ARGS.out).resolve() if ARGS.out else ROOT / "outputs" / f"{NAME}.json"
CKPT = ROOT / "outputs" / "partial" / (OUT.stem + "_ckpt")             # gitignored
for _p in (ROOT / "src", ROOT / "benchmark"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import numpy as np                                                     # noqa: E402

STARTED = _dt.datetime.now(_dt.timezone.utc)
T0 = time.time()
SB_REL = "sionna/rt/path_solvers/sb_candidate_generator.py"
ESM_REL = "benchmark/elevation_sweep_md.py"
DP_REL = "benchmark/dropout_paths_0916.py"


def log(msg: str) -> None:
    print(msg, flush=True)


def sha256_file(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def utc(t=None) -> str:
    return (t or _dt.datetime.now(_dt.timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------------------- refusals (1)
# Everything that can be checked from files alone, before any heavy import.

def refuse(msg: str) -> "None":
    raise SystemExit("REFUSED: " + msg)


def check_gpu_hold() -> dict:
    """Refuse to run on a card that runners/GPU_HOLD.json takes out of service."""
    p = ROOT / "runners" / "GPU_HOLD.json"
    vis = [c.strip() for c in os.environ.get("CUDA_VISIBLE_DEVICES", "").split(",") if c.strip()]
    if not p.exists():
        # The documented way to remove the hold is to delete the file; that is not an error.
        return dict(file=str(p), present=False, held=[], visible=vis)
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        held = [int(x) for x in d.get("gpus", [])]
    except Exception as e:                                             # noqa: BLE001
        refuse(f"runners/GPU_HOLD.json exists but cannot be read ({type(e).__name__}: {e}). "
               "Not guessing which cards are free.")
    clash = [c for c in vis if c.isdigit() and int(c) in held]
    if clash and ARGS.device == "gpu":
        refuse(f"CUDA_VISIBLE_DEVICES={os.environ.get('CUDA_VISIBLE_DEVICES')!r} names card(s) {clash}, "
               f"which runners/GPU_HOLD.json holds ({held}). Note: {d.get('note', '')[:160]}")
    return dict(file=str(p.relative_to(ROOT)), present=True, held=held, visible=vis,
                note=str(d.get("note", ""))[:200])


#: (line, text that must appear on that line) in the installed sionna-rt, for the two knobs this script
#  moves. Verified against sionna-rt 2.1.0 on 2026-09-16. If the library moves, the separation may no
#  longer be the separation described above, so the run stops.
SB_ANCHORS = [
    (59, "MIN_SPEC_COUNT_SIZE = int(1e6)"),
    (107, "max_num_paths = max_num_paths_per_src*num_sources"),
    (115, "paths = PathsBuffer(max_num_paths, max_depth, diffraction)"),
    (313, "spec_counter_size = dr.maximum(max_num_paths_per_src,"),
    (314, "SBCandidateGenerator.MIN_SPEC_COUNT_SIZE)"),
    (315, "specular_chain_counters = [dr.zeros(mi.UInt, spec_counter_size*num_sources)"),
]

#: The same anchors benchmark/dropout_paths_0916.py declares for its copied ranges, at the line numbers
#  they occupy in benchmark/elevation_sweep_md.py as of 2026-09-17 (commit 5d3329d6, --ant-orient, inserted
#  20 lines at :492-511, so every entry after :489 moved by +20; the copied code did not change, the builder's
#  placement call only gained orient=_orient, which is "auto" for the production iso cells this script takes).
#  This script re-checks them itself so the copied production call is guarded by an up-to-date table.
#  ⚠ Difference from the table inside dropout_paths_0916.py: the production PathSolver call now reads
#  `seed=int(getattr(a, "solver_seed", 1))` over two lines, where the copy hard-codes `seed=1`. Those
#  agree only when the job line carries no --ss, which this script checks on the parsed namespace.
ESM_ANCHORS = [
    (362, 'drone_key = str(getattr(a, "drone", "") or TJ.get("drone", "matrice4e"))'),
    (411, "ph = rotor_phases(np.arange(n) / prf, rpms, fp.dirs)"),
    (433, 'rng_m = float(getattr(a, "range_m", RANGE_M) or RANGE_M)'),
    (438, "fc, tagfc = carrier(a)"),
    (813, "spp = int(a.spp) if a.spp else rule_spp(rng_m)"),
    (823, 'm = _re.fullmatch(r"R([01])D([01])E([01])F([01])", swbits)'),
    (843, 'mdep = int(a.max_depth) if getattr(a, "max_depth", 0) else 1'),
    (855, "cols = drone_colors(spec)"),
    (974, "_solver = RP.rt.PathSolver()"),
    (982, "_lay = InMemGroups(_mv0.f, _mv0.g)"),
    (996, "_lay.update_vertices(RP.mi, _par_cache[g], mv.v, g)"),
    (1037, "sc, _ctr, _scene_obj_names = build_scene_builtin("),
    (1042, "sc = RP.build_scene(parts, fc=fc)"),
    (1071, "RP.place(sc, center=_ctr, az=az, el=el, rng=rng_m, baseline=0.0,"),
    (1078, "samples_per_src=spp, max_num_paths_per_src=RP.MAX_PATHS,"),
    (1079, 'seed=int(getattr(a, "solver_seed", 1)))'),
    (1081, "aa, tau, _, O = RP.unpack(p, want_doppler=False)"),
    (1109, "_id2nm = {int(_o.object_id): str(_nm)"),
    (1146, "hit = (O != RP.NO_OBJ).any(axis=0) if O.size else np.zeros(aa.size, bool)"),
    (1147, "_t = aa[hit] * np.exp(-1j * 2 * np.pi * fc * tau[hit])"),
    (1167, "E[j] = complex(np.sum(_t_sum))"),
]


def check_anchors(path: Path, anchors: list, what: str) -> dict:
    lines = path.read_text(encoding="utf-8").splitlines()
    bad = []
    for ln, txt in anchors:
        if ln > len(lines) or txt not in lines[ln - 1]:
            found = [i + 1 for i, s in enumerate(lines) if txt in s]
            bad.append(dict(expected_line=ln, found_at=found, text=txt))
    if bad:
        detail = "\n".join(f"   line {b['expected_line']} -> now at {b['found_at'] or 'NOWHERE'}: {b['text'][:70]}"
                           for b in bad)
        refuse(f"{what} ({path}) has moved; this script's anchors no longer match:\n{detail}\n"
               "   Re-read the code before trusting anything this script prints.")
    return dict(file=str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
                n_anchors=len(anchors), all_match=True)


def check_dp_anchors() -> dict:
    """benchmark/dropout_paths_0916.py checks its own anchors at import time and stops the process when
    they have moved. Read its table first, so that a stale table produces an actionable message here
    instead of an opaque SystemExit from inside the import."""
    src = (ROOT / DP_REL).read_text(encoding="utf-8")
    try:
        tree = ast.parse(src)
        node = next(n for n in tree.body if isinstance(n, ast.Assign)
                    and any(getattr(t, "id", "") == "ANCHORS" for t in n.targets))
        table = [(int(a), str(b)) for a, b in ast.literal_eval(node.value)]
    except Exception as e:                                             # noqa: BLE001
        refuse(f"cannot read the ANCHORS table of {DP_REL} ({type(e).__name__}: {e})")
    lines = (ROOT / ESM_REL).read_text(encoding="utf-8").splitlines()
    stale = []
    for ln, txt in table:
        if ln > len(lines) or txt not in lines[ln - 1]:
            stale.append((ln, txt, [i + 1 for i, s in enumerate(lines) if txt in s]))
    if stale:
        fix = "\n".join(f"     ({ln}, ...) -> now at {found or 'NOWHERE (the line itself changed)'}: {txt[:64]}"
                        for ln, txt, found in stale)
        refuse(
            f"{DP_REL} cannot be imported: its ANCHORS table into {ESM_REL} is stale in {len(stale)} of "
            f"{len(table)} entries, so it stops the process at import time.\n{fix}\n"
            f"   This script is read-only on the repository, so it will not edit {DP_REL}.\n"
            "   The main session should re-anchor that table (the copied code itself is unchanged except\n"
            "   that the production solver call now reads seed=int(getattr(a, \"solver_seed\", 1)) over two\n"
            "   lines, which equals the copied seed=1 only for job lines without --ss), then run:\n"
            f"     cd {ROOT} && CUDA_VISIBLE_DEVICES=\"\" SIONNA2_ALLOW_CPU=1 OMP_NUM_THREADS=1 \\\n"
            f"       /workspace/.venvs/py312/bin/python -B -c 'import sys; sys.argv=[\"x\",\"--device\",\"cpu\"]; "
            f"sys.path.insert(0,\"benchmark\"); import dropout_paths_0916; print(\"anchors ok\")'")
    return dict(file=DP_REL, n_anchors=len(table), all_match=True)


# --------------------------------------------------------------------------------------------- grid
class GridPoint:
    """One (buffer, hash) setting. `min_spec` None means: leave the class attribute at its stock value."""

    def __init__(self, name: str, buffer: int, min_spec):
        self.name, self.buffer, self.min_spec = name, int(buffer), (None if min_spec is None else int(min_spec))

    @property
    def effective_min_spec(self) -> int:
        return STOCK_MIN_SPEC if self.min_spec is None else self.min_spec

    @property
    def hash_size(self) -> int:
        """spec_counter_size per source = max(max_num_paths_per_src, MIN_SPEC_COUNT_SIZE)."""
        return max(self.buffer, self.effective_min_spec)

    def as_dict(self) -> dict:
        return dict(name=self.name, buffer_max_num_paths_per_src=self.buffer,
                    min_spec_count_size=("stock" if self.min_spec is None else self.min_spec),
                    min_spec_count_size_effective=self.effective_min_spec,
                    hash_counter_entries_per_source=self.hash_size)


def parse_grid(specs: list) -> list:
    out, seen = [], set()
    for s in specs:
        parts = s.split(":")
        if len(parts) != 3:
            refuse(f"--grid expects NAME:BUFFER:MINSPEC, got {s!r}")
        nm, buf, ms = parts[0].strip(), parts[1].strip(), parts[2].strip().lower()
        if not nm or nm in seen:
            refuse(f"--grid names must be non-empty and unique; {nm!r} repeats")
        seen.add(nm)
        try:
            b = int(float(buf))
            m = None if ms == "stock" else int(float(ms))
        except ValueError:
            refuse(f"--grid {s!r}: BUFFER and MINSPEC must be integers (or MINSPEC 'stock')")
        if b < 1 or (m is not None and m < 1):
            refuse(f"--grid {s!r}: values must be >= 1")
        out.append(GridPoint(nm, b, m))
    return out


# ------------------------------------------------------------------------------------------ knob probe
class ZerosSpy:
    """Passthrough for the module-level drjit of sb_candidate_generator, recording the sizes of the
    mi.UInt arrays it allocates. The specular-chain counters are the only large mi.UInt zeros in
    _shoot_and_bounce (sb_candidate_generator.py:315), so the largest size recorded here IS
    spec_counter_size * num_sources, measured instead of recomputed."""

    def __init__(self, real):
        self._real, self.uint_sizes = real, []

    def __getattr__(self, k):
        return getattr(object.__getattribute__(self, "_real"), k)

    def zeros(self, dtype, shape=0, **kw):
        try:
            if getattr(dtype, "__name__", "") == "UInt":
                self.uint_sizes.append(int(shape))
        except Exception:                                              # noqa: BLE001
            pass
        return self._real.zeros(dtype, shape, **kw)


class KnobProbe:
    """Read-only wrapper around PathSolver's candidate generator.

    It changes nothing: it records the two knobs as the generator actually received them
    (max_num_paths_per_src, and SBCandidateGenerator.MIN_SPEC_COUNT_SIZE at the moment of the call) and
    the size of the buffer the generator actually allocated (PathsBuffer.buffer_size, read before
    PathSolver shrinks it), then hands the result straight back.
    """

    def __init__(self, inner, sbcg_class):
        self._inner, self._sbcg = inner, sbcg_class
        self.last = None

    def __getattr__(self, k):                                          # delegate everything else
        if k.startswith("_") and k not in ("_inner", "_sbcg"):
            raise AttributeError(k)
        return getattr(object.__getattribute__(self, "_inner"), k)

    def __call__(self, *a, **kw):
        if a:
            raise RuntimeError("the candidate generator was called with positional arguments; this probe "
                               "only understands the keyword call in sionna/rt/path_solvers/path_solver.py")
        import drjit as dr
        mnpps = int(kw["max_num_paths_per_src"])
        min_spec = int(self._sbcg.MIN_SPEC_COUNT_SIZE)
        try:
            nsrc = int(dr.width(kw["src_positions"]))
        except Exception:                                              # noqa: BLE001
            nsrc = None
        t0 = time.time()
        ret = self._inner(**kw)
        buf = int(getattr(ret, "buffer_size", -1))
        # Candidates the generator actually stored, read BEFORE PathSolver shrinks the buffer. This is the
        # only quantity the per-source cap acts on (sb_candidate_generator.py:510,
        # store &= num_path_per_src < max_num_paths_per_src). The returned path count is post-image-method
        # and says nothing about the cap.
        cands = None
        try:
            _pc = ret.paths_counter
            dr.eval(_pc)
            cands = int(dr.max(_pc)[0])
        except Exception as _e:                                        # noqa: BLE001
            log(f"    candidate counter unreadable ({type(_e).__name__}: {_e})")
        hs = max(mnpps, min_spec)
        self.last = dict(
            generator_class=type(self._inner).__name__,
            max_num_paths_per_src=mnpps, min_spec_count_size=min_spec, num_sources=nsrc,
            buffer_size_allocated=buf,
            candidates_stored=cands,
            candidates_over_buffer=(None if cands is None or buf <= 0 else round(cands / buf, 6)),
            buffer_was_binding=(None if cands is None else bool(cands >= buf)),
            buffer_matches_argument=(nsrc is not None and buf == mnpps * nsrc),
            hash_counter_entries_per_source=hs,
            hash_counter_entries_total=hs * (nsrc if nsrc else 1),
            hash_counter_bytes=hs * (nsrc if nsrc else 1) * 4 * 2,     # two hash functions, mi.UInt
            samples_per_src=int(kw["samples_per_src"]), max_depth=int(kw["max_depth"]),
            seed=int(kw.get("seed", 1)), t_candidates_s=round(time.time() - t0, 3))
        return ret


# ------------------------------------------------------------------------------------- pose selection
def pick(idx: list, n: int, mode: str, rng) -> list:
    """N indices out of a list: evenly spread (default), the first N, or a random draw."""
    n = max(0, min(int(n), len(idx)))
    if n == 0:
        return []
    if mode == "first":
        return list(idx[:n])
    if mode == "random":
        return sorted(int(x) for x in rng.choice(np.asarray(idx), size=n, replace=False))
    if n == 1:
        return [idx[len(idx) // 2]]
    pos = np.unique(np.round(np.linspace(0, len(idx) - 1, n)).astype(int))
    return [int(idx[p]) for p in pos]


def select_poses(n_poses: int, iso_prod: np.ndarray, iso_relief: np.ndarray, seed: int) -> tuple:
    """recovered / core / neighbour / control poses, and the order they are solved in."""
    sp, sr = set(int(i) for i in iso_prod), set(int(i) for i in iso_relief)
    recovered_all = sorted(sp - sr)
    core_all = sorted(sp & sr)
    rng = np.random.default_rng(seed)
    chosen_rec = pick(recovered_all, ARGS.n_recovered, ARGS.pick, rng)
    chosen_core = pick(core_all, ARGS.n_core, ARGS.pick, rng)
    roles: dict = {}

    def add(i, role, of=None):
        r = roles.setdefault(int(i), dict(roles=set(), neighbour_of=set()))
        r["roles"].add(role)
        if of is not None:
            r["neighbour_of"].add(int(of))

    for i in chosen_rec:
        add(i, "recovered")
    for i in chosen_core:
        add(i, "core")
    if ARGS.neighbours:
        for i in list(chosen_rec) + list(chosen_core):
            for j in (i - 1, i + 1):
                if 0 <= j < n_poses:
                    add(j, "neighbour", i)
    pool = [i for i in range(n_poses) if i not in sp and i not in sr and i not in roles]
    controls = sorted(int(x) for x in rng.choice(np.asarray(pool), size=min(ARGS.n_random, len(pool)),
                                                 replace=False)) if pool and ARGS.n_random > 0 else []
    for i in controls:
        add(i, "control")
    order = []
    for i in list(chosen_rec) + list(chosen_core):
        for j in (i - 1, i, i + 1):
            if j in roles and j not in order:
                order.append(j)
    order += [i for i in controls if i not in order]
    order += [i for i in sorted(roles) if i not in order]
    if ARGS.max_poses > 0:
        order = order[:ARGS.max_poses]
        roles = {i: roles[i] for i in order}
    for i, r in roles.items():
        r["isolated_by_definition"] = i in sp                          # at the production cap
        r["isolated_at_relief_cap"] = i in sr
    return order, roles, dict(recovered_all=len(recovered_all), core_all=len(core_all),
                              chosen_recovered=chosen_rec, chosen_core=chosen_core, controls=controls)


# ---------------------------------------------------------------------------------------- environment
def env_key_table(pa: dict, name_table: list, DP) -> dict:
    """Environment-only paths of one pose as (stable key hash, delay, |a|), for matching across grid
    points and poses. The key is dropout_paths_0916.path_keys: per interaction (object name,
    interaction type, primitive index)."""
    sel = pa["cls"] == 1
    keys = DP.path_keys(pa["name_idx"], pa["types"], pa["prims"], pa["n_inter"], sel, name_table)
    h = [hashlib.sha1(json.dumps(k).encode()).hexdigest()[:16] for k in keys]
    return dict(hash=h, tau=np.asarray(pa["tau"])[sel].astype(float),
                absa=np.abs(np.asarray(pa["a_bb"])[sel]).astype(float),
                keys=[json.dumps(k) for k in keys])


def present(env: dict, key_hash: str, tau_ref: float, tol: float) -> dict:
    cand = [j for j, k in enumerate(env["hash"]) if k == key_hash]
    if not cand:
        return dict(present=False, n_same_key=0, nearest_dtau_s=None, abs_a=None)
    dt = np.abs(env["tau"][cand] - float(tau_ref))
    j = cand[int(np.argmin(dt))]
    return dict(present=bool(dt.min() <= tol), n_same_key=len(cand), nearest_dtau_s=float(dt.min()),
                abs_a=float(env["absa"][j]))


# ------------------------------------------------------------------------------------------------ run
def main() -> None:
    hold = check_gpu_hold()
    import importlib.util as _ilu
    spec = _ilu.find_spec("sionna")            # top level: located, not imported
    if spec is None or not spec.origin:
        refuse("cannot locate the installed sionna package")
    sb_path = Path(spec.origin).parent / "rt" / "path_solvers" / "sb_candidate_generator.py"
    if not sb_path.exists():
        refuse(f"{sb_path} does not exist; this study is written against sionna-rt 2.1.0")
    sb_check = check_anchors(sb_path, SB_ANCHORS, "the installed sionna-rt candidate generator")
    esm_check = check_anchors(ROOT / ESM_REL, ESM_ANCHORS, "the production builder")
    dp_check = check_dp_anchors()
    grid = parse_grid(ARGS.grid or list(DEFAULT_GRID))

    # benchmark/dropout_paths_0916.py parses its CLI at import time; give it a job line of its own.
    dp_argv = ["dropout_paths_0916.py", "--root", str(ROOT), "--device", ARGS.device,
               "--out", str(OUT.with_name(OUT.stem + "_dp_unused.json"))]
    _keep = sys.argv
    try:
        sys.argv = dp_argv
        import dropout_paths_0916 as DP                                # noqa: N806
    finally:
        sys.argv = _keep
    if Path(DP.ROOT).resolve() != ROOT:
        refuse(f"dropout_paths_0916 was imported from {DP.ROOT}, not from --root {ROOT}")

    import elevation_sweep_md as ESM                                   # noqa: N806
    import arm_grammar as AG                                           # noqa: N806

    cells_arg = ARGS.cells or list(DEFAULT_CELLS)
    cells = []
    for c in cells_arg:
        arm, _, el = c.rpartition("@")
        if not arm:
            refuse(f"--cells expects ARM@EL, got {c!r}")
        cells.append((arm, float(el)))

    CKPT.mkdir(parents=True, exist_ok=True)
    out_cells, variant = [], None
    name_table: list = []

    for ci, (arm, el) in enumerate(cells):
        log(f"== cell {ci}: {arm} el {el:+g}")
        argv, fields = DP.job_argv(arm, el)
        if fields.get("max_paths"):
            refuse(f"--cells must name the production cell (no _mp tag); got {arm}")
        field = DP.load_cell_field(arm, el)
        a = DP.production_namespace(argv)
        if int(getattr(a, "solver_seed", 1)) != 1:
            refuse(f"the job line of {arm} carries solver seed {a.solver_seed}; the re-solve copied from "
                   "the production builder hard-codes seed=1")
        names = DP.dry_run_names(a, field["nshards"])
        want = [p["file"] for p in field["parts"]]
        if names != want:
            refuse(f"dry-run shard names differ from the stored shards:\n  dry {names}\n  disk {want}")

        import mitsuba as _mi                                          # imported by the dry run already
        variant = _mi.variant()
        if ARGS.device == "gpu":
            ESM.require_cuda_variant()
            if not str(variant).startswith("cuda"):
                refuse(f"--device gpu but the Mitsuba variant is {variant!r}")
        elif not str(variant).startswith("llvm"):
            refuse(f"--device cpu but the Mitsuba variant is {variant!r}")

        import report15_probe as RP                                    # noqa: N806
        prod_cap = int(RP.MAX_PATHS)
        caps = {tuple(p["n_trunc"]) if p["n_trunc"] else None for p in field["parts"]}
        if any(cap is None or int(cap[1]) != prod_cap for cap in caps):
            refuse(f"shard path cap {caps} differs from report15_probe.MAX_PATHS {prod_cap} "
                   "(SIONNA2_MAX_PATHS must not be set for this run)")
        builds = {p["solver_build"] for p in field["parts"]}
        if builds != {ESM.SOLVER_BUILD}:
            refuse(f"shard solver build {builds} differs from this installation {ESM.SOLVER_BUILD}")
        prod_pt = [g for g in grid if g.buffer == prod_cap and g.hash_size == max(prod_cap, STOCK_MIN_SPEC)]
        if len(prod_pt) != 1:
            refuse(f"the grid must contain exactly one point that reproduces production "
                   f"(buffer {prod_cap}, hash {max(prod_cap, STOCK_MIN_SPEC)}); it has {len(prod_pt)}. "
                   "Every comparison in this script is relative to that point.")
        prod_name = prod_pt[0].name

        # ---- the two stored fields that define "recovered" and "core"
        relief_fields = dict(fields)
        relief_fields["max_paths"] = str(int(ARGS.relief_cap))
        relief_arm = AG.unparse(relief_fields)
        try:
            relief = DP.load_cell_field(relief_arm, el)
        except SystemExit as e:
            refuse(f"the relief cell at cap {ARGS.relief_cap} is not on disk ({e}). Pass --relief-cap with "
                   "a cap whose shards exist for this cell (the street canyon at el -60 has 8000000).")
        if relief["n"] != field["n"]:
            refuse(f"relief cell has {relief['n']} poses, production cell {field['n']}")
        if {p["solver_build"] for p in relief["parts"]} != {ESM.SOLVER_BUILD}:
            refuse(f"relief cell solver build differs from this installation {ESM.SOLVER_BUILD}")

        iso_prod, m_cell, scale = DP.isolated_poses(field["E"], ARGS.factor)
        iso_relief, m_rel, scale_rel = DP.isolated_poses(relief["E"], ARGS.factor)

        # ---- ledger cross-checks (refuse on disagreement)
        row, ledger_path = DP.ledger_row(arm, el)
        ledger = None
        if row is not None:
            li = [int(x) for x in row.get("outlier_pose_indices", [])]
            nkey = f"f{ARGS.factor:g}"
            ledger = dict(file=ledger_path, n_outlier_poses=(row.get("n_outlier_poses") or {}).get(nkey),
                          n_isolated_recomputed=int(iso_prod.size),
                          count_matches=(row.get("n_outlier_poses") or {}).get(nkey) == int(iso_prod.size),
                          listed_indices=len(li),
                          listed_indices_match=li == [int(x) for x in iso_prod[:len(li)]])
            if not (ledger["count_matches"] and ledger["listed_indices_match"]):
                refuse(f"isolated poses recomputed from the shards differ from {ledger_path}: {ledger}")
        knobs_led = knobs_ledger_check(ROOT, arm, el, relief_arm, iso_prod, iso_relief)

        nesting = bool(set(int(i) for i in iso_relief) <= set(int(i) for i in iso_prod))
        if not nesting:
            log(f"  NOTE: the relief set is not a subset of the production set "
                f"({len(set(map(int, iso_relief)) - set(map(int, iso_prod)))} poses isolated only at the "
                f"relief cap); 'core' still means isolated at both.")

        order, roles, sel = select_poses(field["n"], iso_prod, iso_relief, ARGS.seed + ci)
        cs = DP.CellSolver(a, el, ARGS.spp)
        ESM._check_runtime_build()
        if cs.n != field["n"]:
            refuse(f"pose count {cs.n} differs from the stored field {field['n']}")
        prod_eq = str(variant).startswith("cuda") and cs.spp == cs.spp_prod
        if not prod_eq:
            log("  NOTE: device or ray count differs from production; E cannot reproduce the stored field "
                "and the isolation labels below are not production labels.")
        log(f"  isolated {iso_prod.size} at cap {prod_cap:,} · {iso_relief.size} at cap {ARGS.relief_cap:,}"
            f" · recovered {sel['recovered_all']} · core {sel['core_all']}")
        log(f"  solving {len(order)} poses x {len(grid)} grid points · spp {cs.spp:,} · variant {variant}")

        from sionna.rt.path_solvers.sb_candidate_generator import SBCandidateGenerator as SBCG
        if int(SBCG.MIN_SPEC_COUNT_SIZE) != STOCK_MIN_SPEC:
            refuse(f"SBCandidateGenerator.MIN_SPEC_COUNT_SIZE is {SBCG.MIN_SPEC_COUNT_SIZE}, not the stock "
                   f"{STOCK_MIN_SPEC} this script's grid assumes")
        gen = getattr(cs.solver, "_candidate_generator", None)
        if gen is None or type(gen) is not SBCG:
            refuse(f"PathSolver's candidate generator is {type(gen).__name__}, not SBCandidateGenerator; "
                   "the two knobs of this study only exist on that generator")

        cmeta = dict(
            arm=arm, el_deg=el, job_argv=argv, n_poses=field["n"], nshards=field["nshards"],
            shards=[{k: v for k, v in p.items() if k in ("file", "sha256", "n_trunc", "solver_build")}
                    for p in field["parts"]],
            relief_arm=relief_arm, relief_cap=int(ARGS.relief_cap),
            relief_shards=[p["file"] for p in relief["parts"]],
            production_cap=prod_cap, production_grid_point=prod_name,
            spp_production=cs.spp_prod, spp_used=cs.spp, production_equivalent=bool(prod_eq),
            carrier_hz=cs.fc, range_m=cs.rng_m, az_deg=cs.az, prf_hz=cs.prf, max_depth=cs.mdep,
            switches=cs.sw, diffuse=cs.diffuse, drone=cs.spec.key,
            cell_complex_median=DP.cpair(m_cell), scale=DP.g6(scale), factor=ARGS.factor,
            n_isolated_production=int(iso_prod.size), n_isolated_relief=int(iso_relief.size),
            relief_set_nested_in_production=nesting,
            n_recovered_all=sel["recovered_all"], n_core_all=sel["core_all"],
            selected=dict(recovered=sel["chosen_recovered"], core=sel["chosen_core"],
                          controls=sel["controls"], solve_order=order),
            ledger_check=ledger, knobs_ledger_check=knobs_led)

        cell_out = dict(arm=arm, el_deg=el, meta=cmeta, rows=[], summary=None)
        out_cells.append(cell_out)

        # ---- solve: grid point outer, pose inner
        rows: dict = {}                                                # (grid name, pose) -> record
        envs: dict = {}                                                # (grid name, pose) -> env key table
        for gp in grid:
            log(f"  -- grid point {gp.name}: buffer {gp.buffer:,} · MIN_SPEC_COUNT_SIZE "
                f"{gp.min_spec if gp.min_spec is not None else 'stock'} · hash {gp.hash_size:,}")
            probe = KnobProbe(gen, SBCG)
            saved_min, saved_cap = SBCG.MIN_SPEC_COUNT_SIZE, RP.MAX_PATHS
            try:
                if gp.min_spec is not None:
                    SBCG.MIN_SPEC_COUNT_SIZE = int(gp.min_spec)
                RP.MAX_PATHS = int(gp.buffer)
                cs.solver._candidate_generator = probe
                set_back = dict(min_spec_count_size_read_back=int(SBCG.MIN_SPEC_COUNT_SIZE),
                                buffer_read_back=int(RP.MAX_PATHS))
                if set_back["min_spec_count_size_read_back"] != gp.effective_min_spec \
                        or set_back["buffer_read_back"] != gp.buffer:
                    refuse(f"grid point {gp.name}: the knobs did not take effect {set_back}")
                for k, i in enumerate(order):
                    rec, env = solve_one(DP, cs, probe, gp, i, roles[i], field, name_table, m_cell, scale,
                                         ci, arm, el, variant, ESM, prod_cap)
                    rows[(gp.name, i)] = rec
                    envs[(gp.name, i)] = env
                    log(f"    [{k + 1}/{len(order)}] pose {i} ({','.join(rec['roles'])}): paths "
                        f"{rec['n_paths_returned']} · |E| {DP.g6(abs(complex(*rec['E_recomputed'])))} · "
                        f"dev/scale {rec['dev_recomputed_over_scale']} · env_only |S| "
                        f"{rec['class_sums']['env_only']['abs_sum']} · {rec['t_total_s']} s"
                        + ("  [ckpt]" if rec.get("from_checkpoint") else ""))
                    cell_out["rows"] = [rows[(g.name, j)] for g in grid for j in order
                                        if (g.name, j) in rows]
                    DP.atomic_json(OUT, ledger_obj("partial", grid, out_cells, variant, hold, sb_check,
                                                   esm_check, dp_check, name_table))
            finally:
                SBCG.MIN_SPEC_COUNT_SIZE = saved_min
                RP.MAX_PATHS = saved_cap
                cs.solver._candidate_generator = gen

        cell_out["summary"] = summarise(DP, grid, order, roles, rows, envs, prod_name, m_cell, scale)
        s = cell_out["summary"]
        for gname, d in s["by_grid_point"].items():
            log(f"  {gname:>11}: recovered no longer isolated {d['recovered']['n_no_longer_isolated']}"
                f"/{d['recovered']['n']} · core no longer isolated {d['core']['n_no_longer_isolated']}"
                f"/{d['core']['n']} · core moved {d['core']['n_moved']} · controls moved "
                f"{d['control']['n_moved']}/{d['control']['n']} · neighbour path present "
                f"{d['reference_env_path']['n_present']}/{d['reference_env_path']['n_scored']}")
        DP.atomic_json(OUT, ledger_obj("partial", grid, out_cells, variant, hold, sb_check, esm_check,
                                       dp_check, name_table))

    DP.atomic_json(OUT, ledger_obj("complete", grid, out_cells, variant, hold, sb_check, esm_check,
                                   dp_check, name_table))
    log(f"wrote {OUT}")


def knobs_ledger_check(root: Path, arm: str, el: float, relief_arm: str, iso_prod, iso_relief) -> dict:
    """Cross-check both isolated-pose sets against outputs/dropout_knobs_0916.json (the ladder read-out).
    Refuses when a count or a listed prefix disagrees."""
    p = root / "outputs" / "dropout_knobs_0916.json"
    if not p.exists():
        return dict(file=str(p.name), present=False)
    d = json.loads(p.read_text(encoding="utf-8"))
    by_stem = {c.get("stem"): c for c in d.get("cells", []) if c.get("stem")}
    out = dict(file=str(p.relative_to(root)), present=True, rows={})
    for tag, a_, iso in (("production", arm, iso_prod), ("relief", relief_arm, iso_relief)):
        c = by_stem.get(f"{a_}_el{el:+g}")
        if c is None or not c.get("available", True):
            out["rows"][tag] = dict(stem=f"{a_}_el{el:+g}", found=False)
            continue
        li = [int(x) for x in c.get("isolated_pose_indices", [])]
        r = dict(stem=c["stem"], found=True, n_isolated_ledger=c.get("n_isolated"),
                 n_isolated_recomputed=int(np.size(iso)), listed=len(li),
                 truncated=bool(c.get("isolated_indices_truncated")),
                 count_matches=(c.get("n_isolated") is not None
                                and int(c["n_isolated"]) == int(np.size(iso))),
                 listed_prefix_matches=li == [int(x) for x in np.asarray(iso)[:len(li)]])
        out["rows"][tag] = r
        if not (r["count_matches"] and r["listed_prefix_matches"]):
            refuse(f"isolated poses of the {tag} cell recomputed from the shards disagree with "
                   f"outputs/dropout_knobs_0916.json: {r}")
    return out


def solve_one(DP, cs, probe, gp: GridPoint, i: int, role: dict, field, name_table, m_cell, scale,
              ci: int, arm: str, el: float, variant, ESM, prod_cap: int) -> tuple:
    """One (grid point, pose): checkpoint, solve, verify the knobs, build the record."""
    stamp = dict(arm=arm, el=el, grid=gp.as_dict(), spp=cs.spp, variant=str(variant),
                 solver_build=ESM.SOLVER_BUILD, seed=1, factor=ARGS.factor, json_paths=ARGS.json_paths,
                 production_cap=prod_cap, script_sha256=DP.sha256_file(SCRIPT),
                 shard_sha256=[p.get("sha256") for p in field["parts"]],
                 optix=os.environ.get("DRJIT_LIBOPTIX_PATH"))
    ck = CKPT / f"c{ci}_{hashlib.sha1(f'{arm}@{el:+g}'.encode()).hexdigest()[:10]}" / gp.name
    ck.mkdir(parents=True, exist_ok=True)
    fp = ck / f"pose_{i:05d}.npz"
    if fp.exists():
        try:
            with np.load(fp, allow_pickle=False) as z:
                if json.loads(str(z["stamp_json"])) == stamp:
                    rec = json.loads(str(z["record_json"]))
                    rec["from_checkpoint"] = True
                    rec["roles"] = sorted(role["roles"])
                    env = dict(hash=json.loads(str(z["env_hash_json"])), tau=z["env_tau"],
                               absa=z["env_absa"], keys=json.loads(str(z["env_keys_json"])))
                    for nm in json.loads(str(z["name_table_json"])):
                        if nm not in name_table:
                            name_table.append(nm)
                    return rec, env
        except Exception as e:                                         # noqa: BLE001
            log(f"    checkpoint {fp.name} unreadable ({type(e).__name__}); solving again")

    probe.last = None                                                  # per pose, so the check below is per pose
    import drjit as _dr
    import sionna.rt.path_solvers.sb_candidate_generator as _SBM
    _measure = getattr(probe, "measured_gp", None) != gp.name          # first solve at this grid point
    _spy = ZerosSpy(_dr) if _measure else None
    if _measure:
        _SBM.dr = _spy
    try:
        res = cs.solve(i)
    finally:
        if _measure:
            _SBM.dr = _dr
    if _measure:
        _meas = max([n for n in _spy.uint_sizes if n > 1000], default=None)
        _want = gp.hash_size * int((probe.last or {}).get("num_sources") or 1)
        if _meas != _want:
            refuse(f"grid point {gp.name}: the specular-chain counter the generator allocated is {_meas} "
                   f"entries, not the {_want} the grid asks for (spec_counter_size x num_sources)")
        probe.measured_gp = gp.name
        if probe.last is not None:
            probe.last["hash_counter_entries_total_measured"] = _meas
    if not ARGS.keep_paths:
        res["vertices"] = None                                         # keeps the checkpoints small
    # --- the knobs, as the generator actually saw them
    pr = dict(probe.last or {})
    if not pr:
        refuse("the candidate generator was never called through the probe; the knob read-back is missing")
    ok = (pr["max_num_paths_per_src"] == gp.buffer and pr["min_spec_count_size"] == gp.effective_min_spec
          and pr["hash_counter_entries_per_source"] == gp.hash_size and pr["buffer_matches_argument"])
    if not ok:
        refuse(f"grid point {gp.name}: the solver ran with {pr}, not with {gp.as_dict()}")
    cl = DP.classify(res, name_table)
    rec, pa = DP.pose_record(i, role, res, cl, field, name_table, m_cell, scale, None, ARGS.json_paths)
    env = env_key_table(pa, name_table, DP)
    _E = complex(*rec["E_recomputed"])
    rec.update(grid_point=gp.name, grid=gp.as_dict(), knobs_read_back=pr,
               isolated_at_relief_cap=bool(role["isolated_at_relief_cap"]),
               abs_E_recomputed=DP.g6(abs(_E)),
               abs_E_over_abs_cell_median=DP.g6(abs(_E) / abs(m_cell)) if abs(m_cell) > 0 else None,
               abs_E_minus_median_over_abs_median=DP.g6(abs(_E - m_cell) / abs(m_cell)) if abs(m_cell) > 0 else None,
               n_env_only_paths=len(env["hash"]), from_checkpoint=False)
    arrays = dict(stamp_json=np.array(json.dumps(stamp)), record_json=np.array(json.dumps(rec)),
                  name_table_json=np.array(json.dumps(name_table)),
                  env_hash_json=np.array(json.dumps(env["hash"])),
                  env_keys_json=np.array(json.dumps(env["keys"])),
                  env_tau=env["tau"], env_absa=env["absa"])
    if ARGS.keep_paths:
        D, P = res["D"], res["P"]
        arrays.update(a_bb=pa["a_bb"], tau=pa["tau"], cls=pa["cls"], name_idx=pa["name_idx"],
                      n_inter=pa["n_inter"], obj_raw=pa["obj_raw"],
                      has_types=np.array(pa["types"] is not None),
                      has_prims=np.array(pa["prims"] is not None),
                      types=pa["types"] if pa["types"] is not None else np.zeros((D, P), np.int64),
                      prims=pa["prims"] if pa["prims"] is not None else np.zeros((D, P), np.int64))
    DP.atomic_npz(fp, **arrays)
    return rec, env


# -------------------------------------------------------------------------------------------- summary
def summarise(DP, grid: list, order: list, roles: dict, rows: dict, envs: dict, prod_name: str,
              m_cell: complex, scale: float) -> dict:
    """Per grid point: how the recovered / core / neighbour / control poses moved relative to the
    production grid point, and whether the neighbours' environment-only path is back."""
    absm = abs(m_cell)
    if absm <= 0:
        refuse("the cell's complex median is zero; 'moved' cannot be normalised by it")

    def E(g, i):
        return complex(*rows[(g, i)]["E_recomputed"])

    def moved(g, i):
        return abs(E(g, i) - E(prod_name, i)) / absm if absm > 0 else float("nan")

    def dev(g, i):
        return abs(E(g, i) - m_cell) / scale if scale > 0 else float("nan")

    groups = {r: [i for i in order if r in roles[i]["roles"]] for r in
              ("recovered", "core", "neighbour", "control")}

    # Reference path per chosen isolated pose: the strongest environment-only path of a non-isolated
    # neighbour AT THE PRODUCTION GRID POINT (so the reference does not move with the knobs).
    refs = []
    for i in groups["recovered"] + groups["core"]:
        for j in (i - 1, i + 1):
            if j not in roles or roles[j]["isolated_by_definition"]:
                continue
            s = rows[(prod_name, j)].get("strongest_env_only_path")
            if not s:
                continue
            kh = hashlib.sha1(json.dumps([list(t) for t in s["key"]]).encode()).hexdigest()[:16]
            # keep only reference paths the neighbour really carries and the isolated pose lacks at production
            at_iso = present(envs[(prod_name, i)], kh, s["tau_s"], ARGS.tau_tol_s)
            refs.append(dict(pose=i, neighbour=j, key_hash=kh, tau_s=s["tau_s"], abs_a=s["abs_a"],
                             objects=s["objects"], interaction_types=s["interaction_types"],
                             present_at_isolated_pose_in_production=at_iso["present"]))
    refs_missing = [r for r in refs if not r["present_at_isolated_pose_in_production"]]

    by_gp = {}
    for gp in grid:
        g = gp.name
        d = dict(grid=gp.as_dict(),
                 knobs_read_back=rows[(g, order[0])]["knobs_read_back"] if order else None)
        for gname, idx in groups.items():
            mv = [moved(g, i) for i in idx]
            dv = [dev(g, i) for i in idx]
            d[gname] = dict(
                n=len(idx),
                n_moved=int(sum(1 for x in mv if x > ARGS.noise_tol)),
                max_abs_dE_over_abs_median=DP.g6(max(mv)) if mv else None,
                median_abs_dE_over_abs_median=DP.g6(float(np.median(mv))) if mv else None,
                n_isolated=int(sum(1 for x in dv if x > ARGS.factor)),
                n_isolated_at_production_point=int(sum(1 for i in idx if dev(prod_name, i) > ARGS.factor)),
                n_scored=int(sum(1 for i in idx if roles[i]["isolated_by_definition"]
                                 and dev(prod_name, i) > ARGS.factor)),
                n_no_longer_isolated=int(sum(1 for i, x in zip(idx, dv)
                                             if roles[i]["isolated_by_definition"]
                                             and dev(prod_name, i) > ARGS.factor and x <= ARGS.factor)),
                median_dev_over_scale=DP.g6(float(np.median(dv))) if dv else None,
                median_n_paths_returned=DP.g6(float(np.median([rows[(g, i)]["n_paths_returned"]
                                                               for i in idx]))) if idx else None,
                max_n_paths_returned=int(max([rows[(g, i)]["n_paths_returned"] for i in idx])) if idx else None,
                poses_moved=[i for i, x in zip(idx, mv) if x > ARGS.noise_tol])
        # the reference environment-only path of the neighbours, at the isolated poses
        got = [dict(pose=r["pose"], neighbour=r["neighbour"],
                    **present(envs[(g, r["pose"])], r["key_hash"], r["tau_s"], ARGS.tau_tol_s))
               for r in refs_missing]
        d["reference_env_path"] = dict(
            n_scored=len(got), n_present=int(sum(1 for x in got if x["present"])),
            per_pose=got,
            definition="the strongest environment-only path of a non-isolated neighbour at the production "
                       "grid point, which the isolated pose does not carry at the production grid point; "
                       "'present' means same path key and |delay difference| <= tau_tol_s")
        # environment-only path keys gained / lost against the production grid point
        gl = []
        for i in order:
            a_, b_ = set(envs[(prod_name, i)]["hash"]), set(envs[(g, i)]["hash"])
            gl.append((i, len(b_ - a_), len(a_ - b_)))
        d["env_only_keys_vs_production"] = dict(
            n_poses_gained=int(sum(1 for _, gn, _ in gl if gn > 0)),
            n_poses_lost=int(sum(1 for _, _, ls in gl if ls > 0)),
            total_gained=int(sum(gn for _, gn, _ in gl)), total_lost=int(sum(ls for _, _, ls in gl)),
            per_pose={str(i): dict(gained=gn, lost=ls) for i, gn, ls in gl if gn or ls})
        # does the returned path count approach the buffer? (a saturating cap cannot be measured)
        mx = max([rows[(g, i)]["n_paths_returned"] for i in order]) if order else 0
        cnd = [rows[(g, i)]["knobs_read_back"].get("candidates_stored") for i in order]
        cnd = [int(c) for c in cnd if c is not None]
        d["buffer_saturation"] = dict(
            buffer=gp.buffer,
            max_candidates_stored=(max(cnd) if cnd else None),
            median_candidates_stored=(int(np.median(cnd)) if cnd else None),
            max_candidates_over_buffer=(DP.g6(max(cnd) / gp.buffer) if cnd and gp.buffer else None),
            n_poses_buffer_binding=int(sum(1 for c in cnd if c >= gp.buffer)),
            max_paths_returned=int(mx),
            note="candidates_stored is the pre-shrink PathsBuffer.paths_counter, the only quantity the "
                 "per-source cap acts on; max_paths_returned is post-image-method and cannot show "
                 "whether the cap was binding.")
        by_gp[g] = d

    # ---- single-knob contrasts: two grid points that differ in exactly one knob -------------------
    contrasts = []
    iso_idx = [i for i in order if roles[i]["isolated_by_definition"] and dev(prod_name, i) > ARGS.factor]
    for p in grid:
        for q in grid:
            if p.name == q.name:
                continue
            if p.hash_size == q.hash_size and p.buffer != q.buffer:
                kind = "buffer_alone"
                knob = f"buffer {p.buffer:,} -> {q.buffer:,} at hash {p.hash_size:,}"
            elif p.buffer == q.buffer and p.hash_size != q.hash_size:
                kind = "hash_alone"
                knob = f"hash {p.hash_size:,} -> {q.hash_size:,} at buffer {p.buffer:,}"
            else:
                continue
            gained = {i: len(set(envs[(q.name, i)]["hash"]) - set(envs[(p.name, i)]["hash"])) for i in iso_idx}
            lost = {i: len(set(envs[(p.name, i)]["hash"]) - set(envs[(q.name, i)]["hash"])) for i in iso_idx}
            # ⛔2026-09-16 (review): "no longer isolated" against the production point is CUMULATIVE — at
            #   hash8 -> both8 it counts the five poses the hash had already restored. The contrast's own
            #   question is the INCREMENTAL one: isolated at `frm`, not isolated at `to`. Both are reported,
            #   named apart, and the incremental one is what attributes an effect to this knob.
            iso_at = lambda g, i: dev(g, i) > ARGS.factor                               # noqa: E731
            contrasts.append(dict(
                kind=kind, knob=knob, frm=p.name, to=q.name, n_scored=len(iso_idx),
                n_isolated_at_from=int(sum(1 for i in iso_idx if iso_at(p.name, i))),
                n_incremental_recoveries=int(sum(1 for i in iso_idx
                                                 if iso_at(p.name, i) and not iso_at(q.name, i))),
                n_incremental_losses=int(sum(1 for i in iso_idx
                                             if not iso_at(p.name, i) and iso_at(q.name, i))),
                n_poses_gaining_env_path=int(sum(1 for v in gained.values() if v > 0)),
                n_poses_losing_env_path=int(sum(1 for v in lost.values() if v > 0)),
                n_no_longer_isolated_cumulative_vs_production=int(sum(1 for i in iso_idx
                                                                     if dev(q.name, i) <= ARGS.factor))))
    for c in contrasts:
        log(f"  contrast [{c['kind']:12}] {c['knob']}: incremental recoveries "
            f"{c['n_incremental_recoveries']}/{c['n_isolated_at_from']} (isolated at the starting point) · "
            f"env path gained at {c['n_poses_gaining_env_path']} · cumulative vs production "
            f"{c['n_no_longer_isolated_cumulative_vs_production']}")

    return dict(production_grid_point=prod_name, groups={k: v for k, v in groups.items()},
                reference_env_paths=refs, n_reference_env_paths_missing_at_production=len(refs_missing),
                paired_contrasts=contrasts, by_grid_point=by_gp)


# ----------------------------------------------------------------------------------------------- meta
def ledger_obj(status: str, grid: list, cells: list, variant, hold: dict, sb_check: dict,
               esm_check: dict, dp_check: dict, name_table: list) -> dict:
    import numpy as _np
    meta = dict(
        generator=f"benchmark/{NAME}.py",
        command=f"python -B benchmark/{NAME}.py " + " ".join(sys.argv[1:]),
        argv=sys.argv[1:],
        started_utc=utc(STARTED), finished_utc=utc() if status == "complete" else None,
        wall_time_s=round(time.time() - T0, 1), status=status,
        question="At the isolated poses of a production PathSolver cell, does the missing "
                 "environment-only path come back because the specular-chain hash counter got bigger, "
                 "or because the candidate buffer got bigger?",
        reading_rule=(
            "Declared before the run. Both single-knob contrasts exist in this grid: (a) production -> "
            "hash8 / hash32 moves the hash counter at a fixed buffer; (b) hash8 -> both8 and hash32 -> "
            "both32 move the buffer at a fixed hash counter (equal spec_counter_size, and the allocation "
            "is measured, not assumed); (c) production -> both8 / both32 moves both and attributes "
            "nothing on its own. Read summary.paired_contrasts: if (a) restores the neighbours' "
            "environment-only path and (b) adds nothing, the hash counter is the knob that acts; if (b) "
            "restores it and (a) does not, the buffer is; if both do, report both counts and pick "
            "neither. Whatever it says, it says which knob restores the path, never why a candidate was "
            "lost. buffer_saturation.n_poses_buffer_binding decides separately whether the per-source "
            "cap was ever reached at all."),
        cannot_say=[
            "that hash collisions are what dropped the candidate — the run shows that enlarging the hash "
            "counter at a fixed buffer restores the path, not that two candidates collided (nothing here "
            "counts collisions or ties a specific lost candidate to the missing path)",
            "anything about a grid point that did not complete — the buffer-never-binding statement covers "
            "the buffer values that ran to the end, not one that stopped on an allocation failure",
            "why a candidate is lost inside shoot-and-bounce (no collision counting, no buffer-fill "
            "instrumentation, no proof that the lost candidate is the missing path)",
            "anything about a radio measurement, a detector or a real radar",
            "which solver output is closer to reality (both engines here are approximations)",
            "production numbers when device is cpu or spp differs from the arm (production_equivalent)",
        ],
        versions=dict(solver_build=getattr(sys.modules.get("elevation_sweep_md"), "SOLVER_BUILD", None),
                      python=platform.python_version(), numpy=_np.__version__,
                      mitsuba_variant=str(variant) if variant else None),
        env=dict(CUDA_VISIBLE_DEVICES=os.environ.get("CUDA_VISIBLE_DEVICES"),
                 OMP_NUM_THREADS=os.environ.get("OMP_NUM_THREADS"),
                 SIONNA2_MAX_PATHS=os.environ.get("SIONNA2_MAX_PATHS"),
                 DRJIT_LIBOPTIX_PATH=os.environ.get("DRJIT_LIBOPTIX_PATH"),
                 LD_LIBRARY_PATH=os.environ.get("LD_LIBRARY_PATH"),
                 cpu_affinity=sorted(os.sched_getaffinity(0))),
        device=ARGS.device, spp_override=int(ARGS.spp) or None,
        grid=[g.as_dict() for g in grid],
        parameters=dict(relief_cap=ARGS.relief_cap, n_recovered=ARGS.n_recovered, n_core=ARGS.n_core,
                        n_random=ARGS.n_random, neighbours=ARGS.neighbours, pick=ARGS.pick,
                        seed=ARGS.seed, factor=ARGS.factor, noise_tol=ARGS.noise_tol,
                        tau_tol_s=ARGS.tau_tol_s, max_poses=ARGS.max_poses, json_paths=ARGS.json_paths,
                        keep_paths=bool(ARGS.keep_paths)),
        checks=dict(gpu_hold=hold, sionna_rt_anchors=sb_check, production_builder_anchors=esm_check,
                    dropout_paths_anchors=dp_check),
        reused=[
            f"{DP_REL}: CellSolver (production scene, placement and PathSolver call), load_cell_field, "
            "isolated_poses, job_argv, production_namespace, dry_run_names, ledger_row, classify, "
            "pose_record, path_keys, describe_path, atomic_json, atomic_npz, sha256_file, cpair, g6, CLASSES",
            f"{ESM_REL}: SOLVER_BUILD, require_cuda_variant, _check_runtime_build (through the import above)",
            "src/arm_grammar.py: parse/unparse, to build the relief cell's arm name",
        ],
        script_sha256=sha256_file(SCRIPT),
        copied_source_sha256={DP_REL: sha256_file(ROOT / DP_REL),
                              ESM_REL: sha256_file(ROOT / ESM_REL)},
        outputs=dict(json=str(OUT.relative_to(ROOT)) if OUT.is_relative_to(ROOT) else OUT.name,
                     checkpoints=str(CKPT.relative_to(ROOT)) if CKPT.is_relative_to(ROOT) else CKPT.name),
        definitions={
            "complex numbers": "written as [real, imag].",
            "buffer": "max_num_paths_per_src, the PathSolver argument; the candidate buffer holds "
                      "buffer x num_sources paths (sb_candidate_generator.py:107).",
            "hash counter": "spec_counter_size = max(buffer, SBCandidateGenerator.MIN_SPEC_COUNT_SIZE) "
                            "entries per source, two of them, one per hash function "
                            "(sb_candidate_generator.py:59, 313-315).",
            "knobs_read_back": "what the candidate generator actually received and allocated, recorded by "
                               "KnobProbe at every solve; a mismatch with the grid point stops the run.",
            "cell complex median m / scale": "median(Re E) + 1j median(Im E) and median|E - m| over all "
                                             "poses of the STORED production field; held fixed across grid "
                                             "points, so 'isolated' keeps the ledger's meaning. A full "
                                             "re-solve of all poses at another knob would move m and scale "
                                             "a little; only a few tens of poses are re-solved here.",
            "isolated": "|E - m| > factor x scale (factor 20, the ledger's primary factor).",
            "recovered": "isolated at the production cap and not at --relief-cap (stored fields).",
            "core": "isolated at both caps.",
            "neighbour": "pose i-1 or i+1 of a chosen recovered/core pose.",
            "control": "random pose isolated at neither cap and not a neighbour of a chosen pose.",
            "moved": "|E(grid point) - E(production grid point)| / |m| > noise_tol (default 2e-5, the "
                     "repeat noise measured by the cap ladder). The controls must not move.",
            "reference_env_path": "the strongest environment-only path of a non-isolated neighbour at the "
                                  "production grid point that the isolated pose does not carry there; "
                                  "'present' at a grid point means same path key (per interaction: object "
                                  "name, interaction type, primitive index) and |delay difference| <= "
                                  "tau_tol_s.",
            "env_only_keys_vs_production": "environment-only path keys gained and lost per pose relative "
                                           "to the production grid point (reference-free version of the "
                                           "same question).",
            "paired_contrasts": "two grid points differing in one knob. n_incremental_recoveries counts poses "
                                "isolated at frm and not at to — that is what this knob did. "
                                "n_no_longer_isolated_cumulative_vs_production counts every pose no longer "
                                "isolated at to relative to the production point, so a knob that changed "
                                "nothing still inherits the recoveries an earlier knob made; do not read it "
                                "as this knob's effect.",
            "buffer_saturation": "max candidates stored (pre-shrink paths_counter) / buffer. If this reaches "
                                 "1 the per-source cap was binding; if it stays far below 1 the buffer was "
                                 "never binding and only the hash counter could have acted.",
            "path classes": "none / env_only / drone_only / both / unmapped, as in " + DP_REL + ".",
        },
        scope="Re-solve of chosen poses of a production PathSolver cell (outdoor scene) at several "
              "(buffer, hash) settings, with the production scene, placement and solver call. Simulation "
              "bookkeeping only: no RF measurement, no claim about which output is more realistic, and no "
              "statement that the solver is wrong.",
    )
    return dict(_meta=meta, name_table=list(name_table), cells=cells)


if __name__ == "__main__":
    main()
