#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""isac_plan_kernel_match_0915.py -- matched two-engine blade-comb comparison from existing shards.

Run (CPU only, one core):
    CUDA_VISIBLE_DEVICES="" /workspace/.venvs/py312/bin/python benchmark/isac_plan_kernel_match_0915.py

Options:
    --root  repository root (default: the parent of this file's directory)
    --out   ledger path (default: ROOT/outputs/isac_plan_kernel_match_0915.json); the spectra
            file isac_plan_kernel_match_0915_spectra.npz is written next to it
    --core  CPU core to pin this process to (default: the lowest core in the current affinity)

Scope: simulation-only comparison of two approximations -- our SBR+PO kernel (src/rcs_sbr.py,
shards named ours_*) and the Sionna RT PathSolver (shards named sionna_*) -- using only shards
that already exist in outputs/elev_sweep_shards. No RF measurement is involved. Nothing here
states that either engine is right or wrong. Absolute levels are never differenced across
engines (the two engines write E in different units); only within-engine differences and
dimensionless spectrum-shape quantities are compared between engines.

What it does:
  1. Reads six arms (kernel free space, kernel flat ground, PathSolver free sky and PathSolver
     ground scene for sionna-rt 2.0.1 and 2.1.0). Arm names are read back only with
     src/arm_grammar.parse(strict=True).
  2. Merges each (arm, elevation) cell by scattering E into place by idx, and checks complete
     coverage and a single generation (shard count, pose count, PRF, solver build).
  3. Computes the same metrics with the same function for both engines: comb contrast,
     static / varying power and their difference, and the comb-harmonic shape.
  4. Records geometry and model facts for both engines with quotes verified at run time.

Nothing under ROOT is written except the --out ledger and its spectra file (when --out points
there). Bytecode writing is disabled so importing repository modules leaves no files behind.
"""
from __future__ import annotations

import os
import sys

sys.dont_write_bytecode = True


def _early_arg(name: str):
    for i, a in enumerate(sys.argv):
        if a == name and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
        if a.startswith(name + "="):
            return a.split("=", 1)[1]
    return None


#: CPU only, one core -- set before numpy is imported.
os.environ["CUDA_VISIBLE_DEVICES"] = ""
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"
_core_arg = _early_arg("--core")
_CORE = int(_core_arg) if _core_arg is not None else min(os.sched_getaffinity(0))
os.sched_setaffinity(0, {_CORE})

import argparse  # noqa: E402
import hashlib  # noqa: E402
import importlib.metadata as _md  # noqa: E402
import importlib.util  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import platform  # noqa: E402
import re  # noqa: E402
import subprocess  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402

GENERATOR = "benchmark/isac_plan_kernel_match_0915.py"
OUT_REL = "outputs/isac_plan_kernel_match_0915.json"
SPECTRA_NAME = "isac_plan_kernel_match_0915_spectra.npz"
SHARD_DIR_REL = "outputs/elev_sweep_shards"

#: The six arms of this comparison (verified to exist and parsed with arm_grammar at run time).
ARMS = {
    ("kernel", "free_sky", None): "ours_r15_n8192_mfixbatteryi5_blperairframe",
    ("kernel", "flat_ground", None): "ours_r15_n8192_gndconcrete20_mfixbatteryi5_blperairframe",
    ("pathsolver", "free_sky", "2.0.1"):
        "sionna_p4000000000_swR0D0E0F1_r15_n8192_mfixbatteryi5_blperairframe_d2",
    ("pathsolver", "free_sky", "2.1.0"):
        "sionna_p4000000000_swR0D0E0F1_r15_n8192_mfixbatteryi5_blperairframe_rt210_d2",
    ("pathsolver", "flat_ground", "2.0.1"):
        "sionna_p4000000000_swR0D0E0F1_r15_n8192_envoutdoor01_ground_mfixbatteryi5_blperairframe_d2",
    ("pathsolver", "flat_ground", "2.1.0"):
        "sionna_p4000000000_swR0D0E0F1_r15_n8192_envoutdoor01_ground_mfixbatteryi5_blperairframe_rt210_d2",
}
SCENES = ("free_sky", "flat_ground")
PS_BUILDS = ("2.0.1", "2.1.0")

#: Elevation exclusion window (inclusive) around el 0 -- repository gate on el 0 level citations.
EXCL_LO_DEG, EXCL_HI_DEG = -0.15, 0.05
N_HARM = 12
HALF_BINS = 2
#: Isolated-outlier pose diagnostic: a pose is flagged when |E - median_c(E)| exceeds FACTOR times the
#  median of |E - median_c(E)| over the cell (median_c = median of real part + j median of imaginary part).
#  The factor is a free choice, so three values are reported; OUTLIER_MAIN is the one carried into pairs.
OUTLIER_FACTORS = (10.0, 20.0, 50.0)
OUTLIER_MAIN = 20.0
#: Elevations and build for the spectra file.
SPECTRA_ELS = (-30.0, -60.0)
SPECTRA_BUILD = "2.0.1"
#: dB floor used only in the spectra file for bins whose normalised power is below 1e-30.
SPECTRA_FLOOR_DB = -300.0
#: Sensitivity knobs: (engine, scene, vary fields, declared scope of variant values).
SENS_KNOBS = [
    ("kernel", "free_sky", ("grid_div", "grid_shift"),
     "any tagged grid_div and/or grid_shift value; the untagged base (lambda/12, no shift) is the reference"),
    ("pathsolver", "free_sky", ("spp",), "tagged spp values only (untagged spp uses a range rule)"),
    ("pathsolver", "flat_ground", ("spp",), "tagged spp values only (untagged spp uses a range rule)"),
    ("pathsolver", "flat_ground", ("rep",), "tagged rep values; the untagged base (rep 0) is the reference"),
    ("pathsolver", "free_sky", ("max_depth",), "tagged max_depth values only (untagged depth uses a builder default)"),
    ("pathsolver", "flat_ground", ("max_depth",), "tagged max_depth values only (untagged depth uses a builder default)"),
]

SHARD_RE = re.compile(r"^(?P<arm>.+)_el(?P<el>[+-]\d+(?:\.\d+)?)_(?P<sh>\d+)\.npz$")

#: Words that must not appear in this ledger's own prose (quotes are chosen to avoid them too).
FORBIDDEN_PATTERNS = [r"\bRCS\b", r"dBsm", r"\bsigma\b", "σ", r"[Vv]alidated", r"[Cc]hamber",
                      "챔버"]


class LedgerError(RuntimeError):
    pass


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def r4(x) -> float:
    v = float(x)
    if not math.isfinite(v):
        raise LedgerError(f"non-finite value {x!r}")
    return round(v, 4)


class Sources:
    """Verified quotes: path, line, exact line text, sha256 of the file at run time."""

    def __init__(self, root: Path):
        self.root = root
        self.hashes: dict[str, str] = {}

    def _hash(self, key: str, p: Path) -> str:
        if key not in self.hashes:
            self.hashes[key] = sha256_file(p)
        return self.hashes[key]

    def quote(self, rel: str, needle: str, after: str | None = None, *, abs_path: Path | None = None,
              label: str | None = None) -> dict:
        p = abs_path if abs_path is not None else self.root / rel
        lines = p.read_text(encoding="utf-8").splitlines()
        start = 0
        if after is not None:
            hits = [i for i, row in enumerate(lines) if after in row]
            if not hits:
                raise LedgerError(f"anchor {after!r} not found in {rel}")
            start = hits[0] + 1
        hits = [i for i in range(start, len(lines)) if needle in lines[i]]
        if not hits:
            raise LedgerError(f"quote {needle!r} not found in {rel}" + (f" after {after!r}" if after else ""))
        i = hits[0]
        return {"path": label or rel, "line": i + 1, "quote": lines[i].strip(),
                "n_matches_from_anchor": len(hits), "sha256": self._hash(label or rel, p)}


# --------------------------------------------------------------------------- #
#  Shard index and merge
# --------------------------------------------------------------------------- #
def index_shards(shd: Path) -> dict:
    """{arm: {el_string: [(shard_no, filename), ...]}} from file names (the arm part is parsed later)."""
    out: dict = {}
    for fn in sorted(os.listdir(shd)):
        m = SHARD_RE.match(fn)
        if not m:
            continue
        out.setdefault(m.group("arm"), {}).setdefault(m.group("el"), []).append((int(m.group("sh")), fn))
    return out


def el_map(cells: dict) -> dict:
    """{rounded float el: el_string}; refuses two spellings of one elevation."""
    out = {}
    for s in cells:
        k = round(float(s), 6)
        if k in out and out[k] != s:
            raise LedgerError(f"two file spellings for elevation {k}: {out[k]!r} and {s!r}")
        out[k] = s
    return out


def excluded(el: float) -> bool:
    return EXCL_LO_DEG - 1e-9 <= el <= EXCL_HI_DEG + 1e-9


def load_cell(shd: Path, arm: str, el_str: str, files: list, sources: Sources) -> dict:
    """Merge one (arm, elevation) cell by scattering E into place by idx.

    Checks: every shard number 0..nshards-1 present exactly once, meta el / nshards / n_poses /
    PRF identical across shards, idx disjoint and covering every pose exactly once, one solver
    build string (or none recorded), identical cfg across shards.
    """
    el = float(el_str)
    recs = []
    for sh, fn in sorted(files):
        p = shd / fn
        with np.load(p, allow_pickle=False) as z:
            keys = sorted(z.files)
            d = {k: z[k] for k in keys}
        meta = np.asarray(d["meta"], float).ravel()
        cfg = np.asarray(d["cfg"], float).ravel() if "cfg" in d else None
        rec = dict(
            shard=sh, file=fn, sha256=sha256_file(p), keys=keys,
            idx=np.asarray(d["idx"]).astype(np.int64).ravel(),
            E=np.asarray(d["E"]).ravel(), meta=meta, cfg=cfg,
            E_dedup=(np.asarray(d["E_dedup"]).ravel() if "E_dedup" in d else None),
            solver_build=(str(d["solver_build"]) if "solver_build" in d else None),
            t_start=(float(np.asarray(d["t_start"], float).ravel()[0]) if "t_start" in d else None),
            npaths=(np.asarray(d["npaths"]).ravel() if "npaths" in d else None),
            nret=(np.asarray(d["nret"]).ravel() if "nret" in d else None),
            n_dup=(np.asarray(d["n_dup"]).ravel() if "n_dup" in d else None),
            n_trunc=(np.asarray(d["n_trunc"]).ravel() if "n_trunc" in d else None),
        )
        sources.hashes[f"{SHARD_DIR_REL}/{fn}"] = rec["sha256"]
        recs.append(rec)
    problems = []
    if not recs:
        raise LedgerError(f"no shards for {arm} el {el_str}")
    nsh = {int(r["meta"][2]) for r in recs}
    npo = {int(r["meta"][3]) for r in recs}
    prf = {float(r["meta"][4]) for r in recs}
    els = {float(r["meta"][0]) for r in recs}
    builds = {r["solver_build"] for r in recs}
    cfgs = {None if r["cfg"] is None else tuple("nan" if not np.isfinite(v) else float(v) for v in r["cfg"])
            for r in recs}
    if len(nsh) != 1:
        problems.append(f"meta nshards differ {sorted(nsh)}")
    if len(npo) != 1:
        problems.append(f"meta n_poses differ {sorted(npo)}")
    if len(prf) != 1:
        problems.append(f"meta PRF differ {sorted(prf)}")
    if any(abs(e - el) > 1e-9 for e in els):
        problems.append(f"meta el {sorted(els)} != file el {el}")
    if len(builds) != 1:
        problems.append(f"solver_build differs across shards {sorted(map(str, builds))}")
    if len(cfgs) != 1:
        problems.append("cfg differs across shards")
    n = max(npo)
    shard_nos = sorted(r["shard"] for r in recs)
    if len(nsh) == 1 and shard_nos != list(range(next(iter(nsh)))):
        problems.append(f"shard numbers {shard_nos} != 0..{next(iter(nsh)) - 1}")
    E = np.zeros(n, complex)
    has_dedup = all(r["E_dedup"] is not None for r in recs)
    E_dedup = np.zeros(n, complex) if has_dedup else None
    seen = np.zeros(n, np.int64)
    for r in recs:
        ii = r["idx"]
        if ii.size != r["E"].size:
            problems.append(f"{r['file']}: idx/E length mismatch")
            continue
        if ii.size and (ii.min() < 0 or ii.max() >= n):
            problems.append(f"{r['file']}: idx out of range")
            continue
        if not np.issubdtype(r["E"].dtype, np.complexfloating) or not np.isfinite(r["E"]).all():
            problems.append(f"{r['file']}: E not finite complex")
            continue
        E[ii] = r["E"]
        if has_dedup:
            E_dedup[ii] = r["E_dedup"]
        np.add.at(seen, ii, 1)
    n_missing = int((seen == 0).sum())
    n_multi = int((seen > 1).sum())
    if n_missing:
        problems.append(f"{n_missing} poses not covered")
    if n_multi:
        problems.append(f"{n_multi} poses written more than once")
    ts = [r["t_start"] for r in recs if r["t_start"] is not None]
    s_per_pose = [float(r["meta"][5]) / r["idx"].size for r in recs]
    npaths_max = max((int(r["npaths"].max()) for r in recs if r["npaths"] is not None), default=None)
    nret_max = max((int(r["nret"].max()) for r in recs if r["nret"] is not None), default=None)
    n_dup_poses = (sum(int((r["n_dup"] > 0).sum()) for r in recs)
                   if all(r["n_dup"] is not None for r in recs) else None)
    n_trunc = (sum(int(r["n_trunc"][0]) for r in recs)
               if all(r["n_trunc"] is not None for r in recs) else None)
    cfg0 = recs[0]["cfg"]
    return dict(
        arm=arm, el_deg=el, el_file=el_str, E=E, E_dedup=E_dedup, n_poses=n,
        n_shards=len(recs), meta_nshards=(next(iter(nsh)) if len(nsh) == 1 else None),
        prf_hz=(next(iter(prf)) if len(prf) == 1 else None),
        range_m=(float(cfg0[0]) if cfg0 is not None and np.isfinite(cfg0[0]) else None),
        cfg=([None if not np.isfinite(v) else float(v) for v in cfg0] if cfg0 is not None else None),
        solver_build=next(iter(builds)) if len(builds) == 1 else None,
        t_start_spread_s=(round(max(ts) - min(ts), 1) if len(ts) == len(recs) and ts else None),
        s_per_pose=s_per_pose, npaths_max=npaths_max, nret_max=nret_max,
        n_dup_poses=n_dup_poses, n_trunc_poses=n_trunc,
        shards=[{"file": r["file"], "sha256": r["sha256"], "n_idx": int(r["idx"].size),
                 "keys": r["keys"]} for r in recs],
        problems=problems, ok=not problems,
    )


# --------------------------------------------------------------------------- #
#  Metrics -- one function for both engines
# --------------------------------------------------------------------------- #
def comb_layout(n: int, prf: float, ffl: float) -> dict:
    df = prf / n
    comb = np.zeros(n, bool)
    lines = []
    for h in range(1, N_HARM + 1):
        for s in (+1, -1):
            k0 = int(round(s * h * ffl / df)) % n
            bins = np.array([(k0 + j) % n for j in range(-HALF_BINS, HALF_BINS + 1)])
            if comb[bins].any():
                raise LedgerError(f"comb windows overlap at harmonic {s * h}")
            comb[bins] = True
            lines.append((s * h, bins))
    #: order of the harmonic vector: +1..+12 then -1..-12
    lines.sort(key=lambda t: (t[0] < 0, abs(t[0])))
    dc = np.zeros(n, bool)
    dc[0] = True
    if comb[0]:
        raise LedgerError("comb window covers DC")
    noncomb = ~comb & ~dc
    return dict(df=df, comb=comb, dc=dc, noncomb=noncomb, lines=lines)


def _core_metrics(E: np.ndarray, lay: dict) -> dict:
    mu = E.mean()
    x = E - mu
    X = np.fft.fft(x)                     # rectangular window
    P = (X.real ** 2 + X.imag ** 2)
    total = float(P.sum())
    comb_mean = float(P[lay["comb"]].mean())
    non_mean = float(P[lay["noncomb"]].mean())
    line_pow = np.array([float(P[b].sum()) for _, b in lay["lines"]])
    static = float(abs(mu) ** 2)
    varying = float(np.mean(x.real ** 2 + x.imag ** 2))
    return dict(contrast_db=10 * math.log10(comb_mean / non_mean),
                static_db=10 * math.log10(static), varying_db=10 * math.log10(varying),
                sv_db=10 * math.log10(static) - 10 * math.log10(varying),
                harmonic_rel_db=10 * np.log10(line_pow / total))


def outlier_diagnostic(E: np.ndarray, lay: dict) -> dict:
    """Isolated poses far from the cell's complex median, their share of the varying power, and the
    same metrics after setting those poses to the complex median (one rule for both engines)."""
    med = complex(float(np.median(E.real)), float(np.median(E.imag)))
    dev = np.abs(E - med)
    scale = float(np.median(dev))
    x = E - E.mean()
    p = x.real ** 2 + x.imag ** 2
    out = {"median_abs_dev_over_abs_median": (scale / abs(med)) if abs(med) > 0 else None}
    for fct in OUTLIER_FACTORS:
        mask = dev > fct * scale
        k = int(mask.sum())
        Er = E.copy()
        Er[mask] = med
        core = _core_metrics(Er, lay) if k else None
        flagged = np.flatnonzero(mask)
        out[f"{fct:g}"] = {
            "n_poses": k,
            "n_flagged_with_flagged_neighbour": int(np.isin(flagged + 1, flagged).sum() + np.isin(flagged - 1, flagged).sum()),
            "varying_share": float(p[mask].sum() / p.sum()),
            "min_abs_E_over_abs_median": (float(np.abs(E[mask]).min() / abs(med)) if k and abs(med) > 0 else None),
            "max_abs_E_over_abs_median": (float(np.abs(E[mask]).max() / abs(med)) if k and abs(med) > 0 else None),
            "replaced": core,
        }
    return out


def cell_metrics(E: np.ndarray, prf: float, ffl: float, E_dedup: np.ndarray | None = None) -> dict:
    n = E.size
    lay = comb_layout(n, prf, ffl)
    mu = E.mean()
    x = E - mu
    X = np.fft.fft(x)                     # rectangular window
    P = (X.real ** 2 + X.imag ** 2)
    total = float(P.sum())
    comb_mean = float(P[lay["comb"]].mean())
    non_mean = float(P[lay["noncomb"]].mean())
    line_pow = np.array([float(P[b].sum()) for _, b in lay["lines"]])
    static = float(abs(mu) ** 2)
    varying = float(np.mean(x.real ** 2 + x.imag ** 2))
    return dict(
        contrast_db=10 * math.log10(comb_mean / non_mean),
        static_db=10 * math.log10(static), varying_db=10 * math.log10(varying),
        sv_db=10 * math.log10(static) - 10 * math.log10(varying),
        harmonic_rel_db=10 * np.log10(line_pow / total),
        harmonic_order=[h for h, _ in lay["lines"]],
        noncomb_floor_rel_db=10 * math.log10(non_mean / comb_mean),
        psd_rel=P / total, layout=lay,
        n_comb_bins=int(lay["comb"].sum()), n_noncomb_bins=int(lay["noncomb"].sum()),
        doppler_bin_hz=lay["df"],
        parseval_rel_err=abs(total / n - varying * n) / (varying * n),
        outliers=outlier_diagnostic(E, lay),
        e_dedup=(_core_metrics(E_dedup, lay) if E_dedup is not None else None),
    )


# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #
def pkg_versions() -> dict:
    out = {"python": platform.python_version()}
    for name in ("numpy", "sionna", "sionna-rt", "mitsuba", "drjit"):
        try:
            out[name] = _md.version(name)
        except Exception:  # noqa: BLE001
            out[name] = None
    return out


def git_head(root: Path) -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True,
                                       stderr=subprocess.DEVNULL).strip()
    except Exception:  # noqa: BLE001
        return None


def scan_forbidden(obj, path="$") -> list:
    hits = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            hits += scan_forbidden(k, f"{path}.<key>")
            hits += scan_forbidden(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            hits += scan_forbidden(v, f"{path}[{i}]")
    elif isinstance(obj, str):
        for pat in FORBIDDEN_PATTERNS:
            if re.search(pat, obj):
                hits.append((path, pat, obj[:120]))
    return hits


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--out", default=None)
    ap.add_argument("--core", type=int, default=None,
                    help="CPU core to pin to (applied before numpy import)")
    a = ap.parse_args()
    t_wall = time.time()
    started = utc_now()
    root = Path(a.root).resolve()
    out_path = Path(a.out).resolve() if a.out else root / OUT_REL
    spectra_path = out_path.parent / SPECTRA_NAME
    shd = root / SHARD_DIR_REL
    for p in (str(root / "src"), str(root / "benchmark")):
        if p not in sys.path:
            sys.path.insert(0, p)
    from arm_grammar import ArmNameError, matched_groups, parse  # noqa: E402

    S = Sources(root)
    Q = S.quote

    # ---- repository constants --------------------------------------------- #
    sw_meta = json.loads((root / "outputs/switch_grid.json").read_text(encoding="utf-8"))["_meta"]
    S.hashes["outputs/switch_grid.json"] = sha256_file(root / "outputs/switch_grid.json")
    FFL = float(sw_meta["f_flash_hz"])
    tj = json.loads((root / "outputs/report07_three_engines.json").read_text(encoding="utf-8"))["_meta"]
    S.hashes["outputs/report07_three_engines.json"] = sha256_file(root / "outputs/report07_three_engines.json")
    reg = json.loads((root / "runners/SOLVER_BUILDS.json").read_text(encoding="utf-8"))
    S.hashes["runners/SOLVER_BUILDS.json"] = sha256_file(root / "runners/SOLVER_BUILDS.json")
    ffl_sources = [
        Q("benchmark/clutter_parts_ladder_0824.py", '_TJ = json.load(open(os.path.join(ROOT, "outputs", "switch_grid.json")))'),
        Q("benchmark/clutter_parts_ladder_0824.py", 'FFL = float(_TJ["f_flash_hz"])'),
        Q("outputs/switch_grid.json", '"f_flash_hz"'),
    ]

    # ---- arm index and parse ---------------------------------------------- #
    idx_all = index_shards(shd)
    parsed, unparsable = {}, []
    for arm in sorted(idx_all):
        try:
            parsed[arm] = parse(arm, strict=True)
        except ArmNameError:
            unparsable.append(arm)

    def build_label(fields: dict) -> str:
        sb = fields.get("solver_build")
        if sb is None:
            return "2.0.1"
        bundle = reg["builds"].get(f"_rt{sb}")
        if not isinstance(bundle, str):
            raise LedgerError(f"solver build tag _rt{sb} not in runners/SOLVER_BUILDS.json")
        return dict(p.split("=", 1) for p in bundle.split())["sionna-rt"]

    arm_fields = {}
    for key, arm in ARMS.items():
        if arm not in idx_all:
            raise LedgerError(f"arm has no shards: {arm}")
        if arm not in parsed:
            raise LedgerError(f"arm does not parse with arm_grammar: {arm}")
        f = parsed[arm]
        eng, scene, build = key
        want_engine = "ours" if eng == "kernel" else "sionna"
        checks = {"engine": want_engine, "range_m": "15", "n_poses": "8192",
                  "mesh_fix": "batteryi5", "blade_law": "perairframe"}
        if eng == "kernel":
            checks.update(ground=("concrete20" if scene == "flat_ground" else None),
                          grid_div=None, grid_shift=None, env=None)
        else:
            checks.update(spp="4000000000", switches="R0D0E0F1", max_depth="2",
                          env=("outdoor01_ground" if scene == "flat_ground" else None))
        for k, v in checks.items():
            if f.get(k) != v:
                raise LedgerError(f"{arm}: parsed {k}={f.get(k)!r}, expected {v!r}")
        for k in ("fc", "drone", "az", "rotor", "rotor_seed", "prf", "rep", "env_alt", "env_scat", "ant", "aim",
                  "max_paths", "prop_scale", "frame_scale", "body_scale", "plane_wave", "shell_mm", "prop_mm",
                  "physics", "stock", "only", "parts", "ptd", "det", "solver_det", "nospread"):
            if f.get(k) not in (None, False):
                raise LedgerError(f"{arm}: unexpected tag {k}={f.get(k)!r}")
        if eng == "pathsolver" and build_label(f) != build:
            raise LedgerError(f"{arm}: build {build_label(f)} != {build}")
        arm_fields[arm] = f

    # ---- load main cells ---------------------------------------------------- #
    cache: dict = {}

    def get_cell(arm: str, el_str: str, strict: bool = True):
        k = (arm, el_str)
        if k not in cache:
            c = load_cell(shd, arm, el_str, idx_all[arm][el_str], S)
            if c["ok"]:
                c["metrics"] = cell_metrics(c["E"], c["prf_hz"], FFL, c["E_dedup"])
            cache[k] = c
        c = cache[k]
        if strict and not c["ok"]:
            raise LedgerError(f"cell {arm} el {el_str} failed checks: {c['problems']}")
        return c

    excluded_rows = []
    el_avail = {}
    for key, arm in ARMS.items():
        em = el_map(idx_all[arm])
        keep = {}
        for k, s in sorted(em.items()):
            if excluded(k):
                excluded_rows.append({"arm": arm, "el_deg": k, "reason": "inside exclusion window"})
            else:
                keep[k] = s
        el_avail[key] = keep

    expected_build_string = {"2.0.1": {None, "sionna=2.0.1 sionna-rt=2.0.1 mitsuba=3.8.0 drjit=1.3.1"},
                             "2.1.0": {reg["builds"]["_rt210"]}}

    def engine_label(eng, build):
        return "kernel" if eng == "kernel" else "pathsolver"

    def cell_row(c, eng, scene, build, role, extra=None):
        m = c["metrics"]
        row = {
            "arm": c["arm"], "el_deg": c["el_deg"], "engine": eng, "scene": scene,
            "build": build, "role": role,
            "n_poses": c["n_poses"], "n_shards": c["n_shards"], "prf_hz": c["prf_hz"],
            "range_m": c["range_m"],
            "contrast_db": r4(m["contrast_db"]), "static_db": r4(m["static_db"]),
            "varying_db": r4(m["varying_db"]), "sv_db": r4(m["sv_db"]),
            "level_units": ("kernel E [m^2] (surface integral)" if eng == "kernel"
                            else "PathSolver coherent path-coefficient sum (dimensionless)"),
            "solver_build_recorded": c["solver_build"], "t_start_spread_s": c["t_start_spread_s"],
            "npaths_max": c["npaths_max"], "nret_max": c["nret_max"],
            "n_trunc_poses": c["n_trunc_poses"], "n_dup_poses": c["n_dup_poses"],
            "cfg": c["cfg"],
            "median_s_per_pose": r4(float(np.median(c["s_per_pose"]))),
            "outliers": outlier_row(m["outliers"]),
            "E_dedup_metrics": (None if m["e_dedup"] is None else
                                {k: r4(m["e_dedup"][k]) for k in ("contrast_db", "static_db", "varying_db", "sv_db")}),
            "shards": c["shards"],
        }
        if extra:
            row.update(extra)
        return row

    def outlier_row(o):
        row = {"median_abs_dev_over_abs_median": (None if o["median_abs_dev_over_abs_median"] is None
                                                  else round(o["median_abs_dev_over_abs_median"], 6))}
        for fct in OUTLIER_FACTORS:
            d = o[f"{fct:g}"]
            rep = d["replaced"]
            row[f"factor_{fct:g}"] = {
                "n_poses": d["n_poses"], "varying_share": round(d["varying_share"], 6),
                "n_flagged_with_flagged_neighbour": d["n_flagged_with_flagged_neighbour"],
                "min_abs_E_over_abs_median": (None if d["min_abs_E_over_abs_median"] is None
                                              else round(d["min_abs_E_over_abs_median"], 6)),
                "max_abs_E_over_abs_median": (None if d["max_abs_E_over_abs_median"] is None
                                              else round(d["max_abs_E_over_abs_median"], 6)),
                "contrast_db_replaced": (None if rep is None else r4(rep["contrast_db"])),
                "sv_db_replaced": (None if rep is None else r4(rep["sv_db"])),
                "varying_db_replaced": (None if rep is None else r4(rep["varying_db"])),
            }
        return row

    def main_outlier(m):
        d = m["outliers"][f"{OUTLIER_MAIN:g}"]
        rep = d["replaced"] if d["replaced"] is not None else m
        return d, rep

    cells_rows = []
    main_cells = {}
    paired_els = {}
    for scene in SCENES:
        for build in PS_BUILDS:
            paired_els[(scene, build)] = sorted(set(el_avail[("kernel", scene, None)])
                                                & set(el_avail[("pathsolver", scene, build)]), reverse=True)
    unpaired = []
    for key, arm in ARMS.items():
        eng, scene, build = key
        use = (set().union(*[set(paired_els[(scene, b)]) for b in PS_BUILDS]) if eng == "kernel"
               else set(paired_els[(scene, build)]))
        for el in sorted(set(el_avail[key]) - use, reverse=True):
            unpaired.append({"arm": arm, "el_deg": el})
        for el, s in el_avail[key].items():
            if el not in use:
                continue
            c = get_cell(arm, s)
            if eng == "pathsolver" and c["solver_build"] not in expected_build_string[build]:
                raise LedgerError(f"{arm} el {s}: recorded build {c['solver_build']!r} not {build}")
            main_cells[(eng, scene, build, el)] = c

    # ---- pairs ------------------------------------------------------------- #
    pairs, shape_rows = [], []
    for scene in SCENES:
        for build in PS_BUILDS:
            for el in paired_els[(scene, build)]:
                ck, cp = main_cells[("kernel", scene, None, el)], main_cells[("pathsolver", scene, build, el)]
                mk, mp = ck["metrics"], cp["metrics"]
                pairs.append({
                    "scene": scene, "el_deg": el, "build": build,
                    "kernel_arm": ck["arm"], "pathsolver_arm": cp["arm"],
                    "kernel_contrast_db": r4(mk["contrast_db"]), "pathsolver_contrast_db": r4(mp["contrast_db"]),
                    "kernel_sv_db": r4(mk["sv_db"]), "pathsolver_sv_db": r4(mp["sv_db"]),
                    "prf_match": bool(ck["prf_hz"] == cp["prf_hz"]),
                    "n_poses_match": bool(ck["n_poses"] == cp["n_poses"]),
                    "range_match": bool(ck["range_m"] is not None and ck["range_m"] == cp["range_m"]),
                    "prf_hz": ck["prf_hz"] if ck["prf_hz"] == cp["prf_hz"] else None,
                    "n_poses": ck["n_poses"] if ck["n_poses"] == cp["n_poses"] else None,
                    "kernel_n_outlier_poses": main_outlier(mk)[0]["n_poses"],
                    "pathsolver_n_outlier_poses": main_outlier(mp)[0]["n_poses"],
                    "pathsolver_n_outlier_with_outlier_neighbour": main_outlier(mp)[0]["n_flagged_with_flagged_neighbour"],
                    "pathsolver_outlier_min_abs_E_over_abs_median": (
                        None if main_outlier(mp)[0]["min_abs_E_over_abs_median"] is None
                        else round(main_outlier(mp)[0]["min_abs_E_over_abs_median"], 6)),
                    "pathsolver_outlier_max_abs_E_over_abs_median": (
                        None if main_outlier(mp)[0]["max_abs_E_over_abs_median"] is None
                        else round(main_outlier(mp)[0]["max_abs_E_over_abs_median"], 6)),
                    "kernel_outlier_varying_share": round(main_outlier(mk)[0]["varying_share"], 6),
                    "pathsolver_outlier_varying_share": round(main_outlier(mp)[0]["varying_share"], 6),
                    "kernel_contrast_db_outliers_replaced": r4(main_outlier(mk)[1]["contrast_db"]),
                    "pathsolver_contrast_db_outliers_replaced": r4(main_outlier(mp)[1]["contrast_db"]),
                    "kernel_sv_db_outliers_replaced": r4(main_outlier(mk)[1]["sv_db"]),
                    "pathsolver_sv_db_outliers_replaced": r4(main_outlier(mp)[1]["sv_db"]),
                    "pathsolver_contrast_db_E_dedup": (None if mp["e_dedup"] is None else r4(mp["e_dedup"]["contrast_db"])),
                    "pathsolver_n_dup_poses": cp["n_dup_poses"],
                })
                hk, hp = mk["harmonic_rel_db"], mp["harmonic_rel_db"]
                if mk["harmonic_order"] != mp["harmonic_order"]:
                    raise LedgerError("harmonic order differs")
                corr = float(np.corrcoef(hk, hp)[0, 1])
                shape_rows.append({
                    "scene": scene, "el_deg": el, "build": build,
                    "harmonic_corr": round(corr, 6),
                    "max_abs_harmonic_diff_db": r4(np.max(np.abs(hk - hp))),
                    "noncomb_floor_rel_db_kernel": r4(mk["noncomb_floor_rel_db"]),
                    "noncomb_floor_rel_db_pathsolver": r4(mp["noncomb_floor_rel_db"]),
                    "kernel_harmonic_rel_db": [r4(v) for v in hk],
                    "pathsolver_harmonic_rel_db": [r4(v) for v in hp],
                    "harmonic_order": mk["harmonic_order"],
                    "harmonic_corr_outliers_replaced": round(float(np.corrcoef(
                        main_outlier(mk)[1]["harmonic_rel_db"], main_outlier(mp)[1]["harmonic_rel_db"])[0, 1]), 6),
                    "max_abs_harmonic_diff_db_outliers_replaced": r4(np.max(np.abs(
                        main_outlier(mk)[1]["harmonic_rel_db"] - main_outlier(mp)[1]["harmonic_rel_db"]))),
                })

    # ---- within-engine ground effect --------------------------------------- #
    within = []
    k_both = set(el_avail[("kernel", "free_sky", None)]) & set(el_avail[("kernel", "flat_ground", None)])
    ps_both = {b: set(el_avail[("pathsolver", "free_sky", b)]) & set(el_avail[("pathsolver", "flat_ground", b)])
               for b in PS_BUILDS}
    ps_any = set().union(*ps_both.values())

    def within_row(eng, build, el):
        cf = main_cells[(eng, "free_sky", build, el)]["metrics"]
        cg = main_cells[(eng, "flat_ground", build, el)]["metrics"]
        return {"engine": eng, "build": build, "el_deg": el,
                "free_arm": main_cells[(eng, "free_sky", build, el)]["arm"],
                "ground_arm": main_cells[(eng, "flat_ground", build, el)]["arm"],
                "contrast_free_db": r4(cf["contrast_db"]), "contrast_ground_db": r4(cg["contrast_db"]),
                "contrast_change_db": r4(cg["contrast_db"] - cf["contrast_db"]),
                "varying_ground_minus_free_db": r4(cg["varying_db"] - cf["varying_db"]),
                "static_ground_minus_free_db": r4(cg["static_db"] - cf["static_db"]),
                "sv_free_db": r4(cf["sv_db"]), "sv_ground_db": r4(cg["sv_db"]),
                "n_outlier_poses_free": main_outlier(cf)[0]["n_poses"],
                "n_outlier_poses_ground": main_outlier(cg)[0]["n_poses"],
                "contrast_change_db_outliers_replaced": r4(main_outlier(cg)[1]["contrast_db"]
                                                           - main_outlier(cf)[1]["contrast_db"]),
                "varying_ground_minus_free_db_outliers_replaced": r4(main_outlier(cg)[1]["varying_db"]
                                                                     - main_outlier(cf)[1]["varying_db"])}

    for el in sorted(k_both & ps_any, reverse=True):
        within.append(within_row("kernel", None, el))
    for b in PS_BUILDS:
        for el in sorted(ps_both[b] & k_both, reverse=True):
            within.append(within_row("pathsolver", b, el))

    # ---- summary ----------------------------------------------------------- #
    def scene_summary(scene, build):
        rows = [p for p in pairs if p["scene"] == scene and p["build"] == build]
        if not rows:
            return {"n_pairs": 0}
        return {"pathsolver_build": build, "n_pairs": len(rows),
                "el_deg": [p["el_deg"] for p in rows],
                "kernel_contrast_min_db": min(p["kernel_contrast_db"] for p in rows),
                "kernel_contrast_max_db": max(p["kernel_contrast_db"] for p in rows),
                "pathsolver_contrast_min_db": min(p["pathsolver_contrast_db"] for p in rows),
                "pathsolver_contrast_max_db": max(p["pathsolver_contrast_db"] for p in rows),
                "outlier_factor": OUTLIER_MAIN,
                "kernel_n_outlier_poses_max": max(p["kernel_n_outlier_poses"] for p in rows),
                "pathsolver_n_outlier_poses_min": min(p["pathsolver_n_outlier_poses"] for p in rows),
                "pathsolver_n_outlier_poses_max": max(p["pathsolver_n_outlier_poses"] for p in rows),
                "pathsolver_outlier_varying_share_min": min(p["pathsolver_outlier_varying_share"] for p in rows),
                "pathsolver_outlier_varying_share_max": max(p["pathsolver_outlier_varying_share"] for p in rows),
                "kernel_contrast_outliers_replaced_min_db": min(p["kernel_contrast_db_outliers_replaced"] for p in rows),
                "kernel_contrast_outliers_replaced_max_db": max(p["kernel_contrast_db_outliers_replaced"] for p in rows),
                "pathsolver_contrast_outliers_replaced_min_db": min(p["pathsolver_contrast_db_outliers_replaced"] for p in rows),
                "pathsolver_contrast_outliers_replaced_max_db": max(p["pathsolver_contrast_db_outliers_replaced"] for p in rows)}

    summary = {}
    for scene in SCENES:
        s = scene_summary(scene, "2.0.1")
        s["by_build"] = {b: scene_summary(scene, b) for b in PS_BUILDS}
        summary[scene] = s
    kw = [w for w in within if w["engine"] == "kernel"]
    pw = {b: [w for w in within if w["engine"] == "pathsolver" and w["build"] == b] for b in PS_BUILDS}
    summary["kernel_ground_contrast_change_min_db"] = min(w["contrast_change_db"] for w in kw)
    summary["kernel_ground_contrast_change_max_db"] = max(w["contrast_change_db"] for w in kw)
    summary["kernel_ground_contrast_change_n"] = len(kw)
    summary["pathsolver_ground_contrast_change_min_db"] = min(w["contrast_change_db"] for w in pw["2.0.1"])
    summary["pathsolver_ground_contrast_change_max_db"] = max(w["contrast_change_db"] for w in pw["2.0.1"])
    summary["pathsolver_ground_contrast_change_build"] = "2.0.1"
    summary["pathsolver_ground_contrast_change_by_build"] = {
        b: ({"n": len(pw[b]), "min_db": min(w["contrast_change_db"] for w in pw[b]),
             "max_db": max(w["contrast_change_db"] for w in pw[b]), "el_deg": [w["el_deg"] for w in pw[b]]}
            if pw[b] else {"n": 0}) for b in PS_BUILDS}
    summary["pairs_prf_all_match"] = all(p["prf_match"] for p in pairs)
    summary["pairs_n_poses_all_match"] = all(p["n_poses_match"] for p in pairs)
    summary["pairs_range_all_match"] = all(p["range_match"] for p in pairs)
    summary["n_pairs_total"] = len(pairs)
    shake = []
    for (eng, scene, build, el), c in sorted(main_cells.items(), key=lambda t: (t[0][0], t[0][1], str(t[0][2]), -t[0][3])):
        o = c["metrics"]["outliers"]
        shake.append({"engine": eng, "scene": scene, "build": build, "el_deg": el,
                      **{f"n_poses_factor_{f:g}": o[f"{f:g}"]["n_poses"] for f in OUTLIER_FACTORS},
                      **{f"contrast_db_replaced_factor_{f:g}": (r4(o[f"{f:g}"]["replaced"]["contrast_db"])
                                                               if o[f"{f:g}"]["replaced"] is not None
                                                               else r4(c["metrics"]["contrast_db"]))
                         for f in OUTLIER_FACTORS}})
    summary["outlier_factor_shake"] = shake
    ps_all = [p for p in pairs if p["build"] == "2.0.1"]
    summary["outlier_factor_shake_range"] = {
        f"{scene}|{eng}": {
            f"factor_{f:g}": {
                "n_poses_min": min(r[f"n_poses_factor_{f:g}"] for r in shake if r["scene"] == scene and r["engine"] == eng
                                   and r["build"] in (None, "2.0.1")),
                "n_poses_max": max(r[f"n_poses_factor_{f:g}"] for r in shake if r["scene"] == scene and r["engine"] == eng
                                   and r["build"] in (None, "2.0.1")),
                "contrast_db_replaced_min": min(r[f"contrast_db_replaced_factor_{f:g}"] for r in shake
                                                if r["scene"] == scene and r["engine"] == eng and r["build"] in (None, "2.0.1")),
                "contrast_db_replaced_max": max(r[f"contrast_db_replaced_factor_{f:g}"] for r in shake
                                                if r["scene"] == scene and r["engine"] == eng and r["build"] in (None, "2.0.1")),
            } for f in OUTLIER_FACTORS}
        for scene in SCENES for eng in ("kernel", "pathsolver")}
    del ps_all

    # ---- cells (main) ------------------------------------------------------ #
    for (eng, scene, build, el), c in sorted(main_cells.items(), key=lambda t: (t[0][0], t[0][1], str(t[0][2]), -t[0][3])):
        cells_rows.append(cell_row(c, eng, scene, build, "main"))

    # ---- cost -------------------------------------------------------------- #
    cost_rows = []
    used_els = {}
    for (scene, build), els in paired_els.items():
        used_els.setdefault(("kernel", scene, None), set()).update(els)
        used_els.setdefault(("pathsolver", scene, build), set()).update(els)
    for key, arm in ARMS.items():
        els = sorted(used_els.get(key, set()), reverse=True)
        spp = []
        for el in els:
            spp += main_cells[(key[0], key[1], key[2], el)]["s_per_pose"]
        cost_rows.append({"arm": arm, "engine": key[0], "scene": key[1], "build": key[2],
                          "n_shards": len(spp), "el_deg_used": els,
                          "median_s_per_pose": r4(float(np.median(spp))),
                          "min_s_per_pose": r4(min(spp)), "max_s_per_pose": r4(max(spp))})
    cost_meta_sources = {
        "kernel": [Q("benchmark/elevation_sweep_md.py", "E = np.zeros(idx.size, complex); t0 = time.time()"),
                   Q("benchmark/elevation_sweep_md.py", "meta=np.array([el, a.shard, a.nshards, n, prf,"),
                   Q("benchmark/elevation_sweep_md.py", "time.time() - t0]),")],
        "pathsolver": [Q("benchmark/elevation_sweep_md.py", "time.time() - t0, spp]),"),
                       Q("benchmark/elevation_sweep_md.py", "t0 = time.time()", after="E_dedup = np.zeros(idx.size, complex)")],
    }

    # ---- sensitivity (knob shaking, within engine) ------------------------- #
    sens_rows, sens_skipped = [], []
    parsable = sorted(parsed)
    for eng, scene, vary, scope in SENS_KNOBS:
        builds = [None] if eng == "kernel" else list(PS_BUILDS)
        for build in builds:
            base = ARMS[(eng, scene, build)]
            groups = matched_groups(parsable, vary=list(vary))
            bf = parsed[base]
            base_val = tuple(bf.get(v) for v in vary)
            grp = next((g for g in groups.values() if g.get(base_val) == base), None)
            if grp is None:
                raise LedgerError(f"base arm {base} not found in matched groups for {vary}")
            els = (paired_els[(scene, build)] if eng == "pathsolver"
                   else sorted(set().union(*[set(paired_els[(scene, b)]) for b in PS_BUILDS]), reverse=True))
            for val, arm in sorted(grp.items(), key=lambda t: str(t[0])):
                if arm == base:
                    continue
                if any(v is None for v in val) and vary != ("grid_div", "grid_shift"):
                    sens_skipped.append({"arm": arm, "reason": "untagged value outside declared scope"})
                    continue
                em = el_map(idx_all[arm])
                variant = "+".join(f"{k}={v}" for k, v in zip(vary, val) if v is not None)
                for el in els:
                    if el not in em:
                        continue
                    c = get_cell(arm, em[el], strict=False)
                    if not c["ok"]:
                        sens_skipped.append({"arm": arm, "el_deg": el, "reason": "; ".join(c["problems"])})
                        continue
                    ref = main_cells[(eng, scene, build, el)]
                    mc, mr = c["metrics"], ref["metrics"]
                    sens_rows.append({
                        "engine": eng, "scene": scene, "build": build, "el_deg": el,
                        "knob": "+".join(vary), "variant": variant, "arm": arm, "reference_arm": base,
                        "contrast_db": r4(mc["contrast_db"]), "reference_contrast_db": r4(mr["contrast_db"]),
                        "contrast_minus_reference_db": r4(mc["contrast_db"] - mr["contrast_db"]),
                        "n_outlier_poses": main_outlier(mc)[0]["n_poses"],
                        "reference_n_outlier_poses": main_outlier(mr)[0]["n_poses"],
                        "contrast_db_outliers_replaced": r4(main_outlier(mc)[1]["contrast_db"]),
                        "reference_contrast_db_outliers_replaced": r4(main_outlier(mr)[1]["contrast_db"]),
                        "contrast_minus_reference_db_outliers_replaced": r4(main_outlier(mc)[1]["contrast_db"]
                                                                            - main_outlier(mr)[1]["contrast_db"]),
                        "sv_db": r4(mc["sv_db"]), "reference_sv_db": r4(mr["sv_db"]),
                        "varying_minus_reference_db": r4(mc["varying_db"] - mr["varying_db"]),
                        "prf_match": bool(c["prf_hz"] == ref["prf_hz"]),
                        "n_poses_match": bool(c["n_poses"] == ref["n_poses"]),
                        "n_trunc_poses": c["n_trunc_poses"], "solver_build_recorded": c["solver_build"],
                    })
                    cells_rows.append(cell_row(c, eng, scene, build, "sensitivity",
                                               {"variant": variant}))
    sens_summary = {}
    for r in sens_rows:
        k = f"{r['engine']}|{r['scene']}|{r['build']}|{r['knob']}"
        d = sens_summary.setdefault(k, {"engine": r["engine"], "scene": r["scene"], "build": r["build"],
                                        "knob": r["knob"], "n_rows": 0, "max_abs_contrast_minus_reference_db": 0.0,
                                        "max_abs_contrast_minus_reference_db_outliers_replaced": 0.0,
                                        "el_deg": [], "variants": []})
        d["n_rows"] += 1
        d["max_abs_contrast_minus_reference_db"] = max(d["max_abs_contrast_minus_reference_db"],
                                                       abs(r["contrast_minus_reference_db"]))
        d["max_abs_contrast_minus_reference_db_outliers_replaced"] = max(
            d["max_abs_contrast_minus_reference_db_outliers_replaced"],
            abs(r["contrast_minus_reference_db_outliers_replaced"]))
        if r["el_deg"] not in d["el_deg"]:
            d["el_deg"].append(r["el_deg"])
        if r["variant"] not in d["variants"]:
            d["variants"].append(r["variant"])
    sens_summary_rows = sorted(sens_summary.values(), key=lambda d: (d["engine"], d["scene"], str(d["build"]), d["knob"]))

    # ---- kernel phase centre (recomputed with current pose code) ----------- #
    env_mesh = {k: os.environ.get(k) for k in ("MESH_FIX", "BLADE_LAW")}
    from articulated_fast import FastPoser, rotor_phases  # noqa: E402
    from drones import DRONES  # noqa: E402
    from geom import blade_law_canon, mesh_fix_set  # noqa: E402
    drone_key = str(tj.get("drone", "matrice4e"))
    spec = DRONES[drone_key]
    mf_now = "".join(sorted(mesh_fix_set()))
    bl_now = blade_law_canon().replace("_", "")
    n_k = int(arm_fields[ARMS[("kernel", "free_sky", None)]]["n_poses"])
    prf_k = float(tj["prf_hz"])
    rpms = np.asarray(tj["rpm_per_rotor"], float)
    fp = FastPoser(spec)
    ph = rotor_phases(np.arange(n_k) / prf_k, rpms, fp.dirs)
    lo = np.full(3, np.inf)
    hi = np.full(3, -np.inf)
    for i in range(0, n_k, max(1, n_k // 64)):
        V = np.asarray(fp.pose(ph[i]).v, float)
        lo = np.minimum(lo, V.min(0))
        hi = np.maximum(hi, V.max(0))
    ctr = 0.5 * (lo + hi)
    blades = int(getattr(spec, "prop_blades"))
    ffl_from_rpm = blades * float(np.mean(rpms)) / 60.0
    ffl_per_rotor = [blades * float(r) / 60.0 for r in rpms]
    df = prf_k / n_k
    harm_spread_bins = (N_HARM * (max(ffl_per_rotor) - min(ffl_per_rotor)) / 2.0) / df

    # ---- ground mesh and material tables ----------------------------------- #
    gobj = root / "assets/meshes/outdoor01/ground.obj"
    S.hashes["assets/meshes/outdoor01/ground.obj"] = sha256_file(gobj)
    gv = np.array([[float(t) for t in ln.split()[1:4]] for ln in gobj.read_text().splitlines()
                   if ln.startswith("v ")])
    ground_extent = (gv.max(0) - gv.min(0)).tolist()
    import freespace_link as _fl  # noqa: E402  (numpy-only helper; read a repository constant)
    k_eps = float(_fl.GROUND_REPO_CONCRETE["eps_r"])
    k_cond = 0.0462 * (3.5e9 / 1e9) ** 0.7822
    spec_s = importlib.util.find_spec("sionna")
    itu_quote = None
    ps_itu = None
    if spec_s is not None and spec_s.submodule_search_locations:
        itu_path = Path(list(spec_s.submodule_search_locations)[0]) / "rt/radio_materials/itu.py"
        if itu_path.exists():
            itu_quote = S.quote("", '"concrete"', abs_path=itu_path,
                                label=f"site-packages/sionna/rt/radio_materials/itu.py (sionna-rt {_md.version('sionna-rt')})")
            nums = re.findall(r"-?\d+(?:\.\d+)?", itu_quote["quote"].split(":", 2)[-1])
            a_, b_, c_, d_ = (float(x) for x in nums[-4:])
            ps_itu = {"eps_a": a_, "eps_b": b_, "cond_c": c_, "cond_d": d_,
                      "eps_r_at_3p5GHz": r4(a_ * 3.5 ** b_), "conductivity_S_per_m_at_3p5GHz": r4(c_ * 3.5 ** d_)}
    rd_depth = Q("site-packages", ":param max_depth: Maximum depth", abs_path=(
        Path(list(spec_s.submodule_search_locations)[0]) / "rt/path_solvers/path_solver.py"),
        label=f"site-packages/sionna/rt/path_solvers/path_solver.py (sionna-rt {_md.version('sionna-rt')})") \
        if spec_s is not None else None

    # ---- verified cfg facts from shards ------------------------------------ #
    def cfg_values(eng, scene, build):
        vals = {tuple(c["cfg"]) for (e, s, b, _), c in main_cells.items() if (e, s, b) == (eng, scene, build)}
        return [list(v) for v in sorted(vals, key=str)]

    ranges_all = sorted({c["range_m"] for c in main_cells.values()})
    prfs_all = sorted({c["prf_hz"] for c in main_cells.values()})
    npo_all = sorted({c["n_poses"] for c in main_cells.values()})

    # ---- geometry_match ---------------------------------------------------- #
    def num_in(q: dict, pattern: str) -> float:
        m = re.search(pattern, q["quote"])
        if not m:
            raise LedgerError(f"pattern {pattern!r} not in quote {q['quote']!r}")
        return float(m.group(1))

    q_alt = Q("benchmark/elevation_sweep_md.py", 'dir=f"{ROOT}/assets/meshes/outdoor01", alt_m=20.0,')
    ps_alt = num_in(q_alt, r"alt_m=(\d+(?:\.\d+)?)")
    q_fc = Q("benchmark/elevation_sweep_md.py", "FC, RANGE_M = 3.5e9, 10.0")
    fc_const = num_in(q_fc, r"=\s*([0-9.]+e[0-9]+)")
    q_div = Q("benchmark/elevation_sweep_md.py", "DIV = 12                            # 격자 간격 λ/12")
    div_const = int(num_in(q_div, r"DIV = (\d+)"))
    q_slab = Q("src/materials.py", 'itu="concrete", thickness=0.30, S=0.0,', after='"concrete_dark": dict(')
    slab_m = num_in(q_slab, r"thickness=([0-9.]+)")
    slab_S = num_in(q_slab, r"S=([0-9.]+)")
    lam = 299792458.0 / fc_const
    kgnd = arm_fields[ARMS[("kernel", "flat_ground", None)]]
    psf = arm_fields[ARMS[("pathsolver", "free_sky", "2.0.1")]]
    sw_m = re.fullmatch(r"R([01])D([01])E([01])F([01])", psf["switches"])
    sw_flags = dict(zip(("refraction", "diffraction", "edge_diffraction", "diffuse_reflection"),
                        (bool(int(g)) for g in sw_m.groups())))
    for (e_, s_, b_, el_), c_ in main_cells.items():
        if e_ != "pathsolver":
            continue
        cf = c_["cfg"]
        if (cf[1] != float(psf["max_depth"]) or cf[2] != float(psf["spp"])
                or [bool(v) for v in cf[4:7]] != [sw_flags["refraction"], sw_flags["diffraction"],
                                                  sw_flags["edge_diffraction"]]):
            raise LedgerError(f"PathSolver cfg {cf} disagrees with arm tags at {s_} {b_} {el_}")
    for (e_, s_, b_, el_), c_ in main_cells.items():
        if e_ == "kernel" and (c_["cfg"][1] is not None or c_["cfg"][2] is not None):
            raise LedgerError(f"kernel cfg {c_['cfg']} does not carry NaN depth/budget at {s_} {el_}")
    geom_rows = [
        {"item": "drone_height_above_ground_m",
         "kernel_value": float(re.fullmatch(r"[A-Za-z]+(-?\d+(?:\.\d+)?)", kgnd["ground"]).group(1)),
         "pathsolver_value": ps_alt,
         "same": True,
         "note": ("Kernel height is measured from its phase centre (frozen grid centre = bounding-box centre of "
                  "64 probe poses); PathSolver moves the ground mesh (z = 0 plane in the file) down by alt_m "
                  "relative to the drone mesh origin, and the radar is placed at origin + range * u. The two "
                  "reference points differ by kernel_phase_centre_offset_from_mesh_origin_m (recomputed with the "
                  "current pose code)."),
         "kernel_phase_centre_offset_from_mesh_origin_m": [r4(v) + 0.0 for v in ctr],
         "kernel_ground_plane_z_in_mesh_coordinates_m": r4(float(ctr[2]) - float(re.fullmatch(
             r"[A-Za-z]+(-?\d+(?:\.\d+)?)", kgnd["ground"]).group(1))),
         "pathsolver_ground_plane_z_in_mesh_coordinates_m": r4(float(gv[:, 2].max()) - ps_alt),
         "pathsolver_ground_mesh_extent_m": [r4(v) for v in ground_extent],
         "pathsolver_ground_mesh_z_in_file_m": r4(float(gv[:, 2].max())),
         "kernel_source": [
             Q("benchmark/elevation_sweep_md.py", "else f\"_gnd{a.ground}{float(getattr(a, 'ground_alt', 20.0)):g}\""),
             Q("benchmark/elevation_sweep_md.py", "mv, gm, fc, u, ground_alt_m=float(a.ground_alt),"),
             Q("src/rcs_sbr.py", "ground_alt_m : **위상 중심(ctr)** 이 지면 위로 뜬 높이 [m]"),
             Q("benchmark/elevation_sweep_md.py", "probes = [fp.pose(ph[i]) for i in range(0, n, max(1, n // 64))]"),
             Q("src/rcs_sbr.py", "ctr = 0.5 * (lo + hi)", after="def grid_ref_from"),
         ],
         "pathsolver_source": [
             q_alt,
             Q("benchmark/elevation_sweep_md.py", 'ENV_SPECS["outdoor01_ground"] = dict('),
             Q("benchmark/elevation_sweep_md.py", 'parts=[p for p in _O1["parts"] if p[0] == "ground"])'),
             Q("benchmark/elevation_sweep_md.py", 'dz = -float(_ENV_ALT[0] if _ENV_ALT[0] else spec["alt_m"])'),
             Q("assets/meshes/outdoor01/ground.obj", "v -60.000000 -60.000000 0.000000"),
             Q("benchmark/report15_probe.py", "tx = c + rng * u + 0.5 * baseline * e1"),
         ]},
        {"item": "ground_material_parameters",
         "kernel_value": {"name": kgnd["ground"].rstrip("0123456789."), "eps_r": k_eps,
                          "conductivity_model_S_per_m": "0.0462 * f_GHz ** 0.7822",
                          "conductivity_S_per_m_at_3p5GHz": r4(k_cond)},
         "pathsolver_value": {"material_key": "concrete_dark", "itu_type": "concrete", "slab_thickness_m": slab_m,
                              "itu_table_installed_build": ps_itu},
         "same": bool(ps_itu is not None and abs(ps_itu["eps_a"] - k_eps) < 1e-12 and ps_itu["eps_b"] == 0.0
                      and abs(ps_itu["cond_c"] - 0.0462) < 1e-12 and abs(ps_itu["cond_d"] - 0.7822) < 1e-12),
         "note": ("Kernel eps_r is read at run time from freespace_link.GROUND_REPO_CONCRETE (5.24, matching the "
                  "quoted benchmark/geometry.py constant); its conductivity model is the quoted return line. "
                  "Parameters compared against the ITU table of the installed sionna-rt only; the 2.0.1 table is not "
                  "installed on this machine and is not quoted. The release-notes line quoted below says the "
                  "material model changed in 2.1.0."),
         "kernel_source": [
             Q("benchmark/elevation_sweep_md.py", 'E[j] = sbr_field_ground('),
             Q("benchmark/elevation_sweep_md.py", "range_m=rng_m, ground=_gnd,"),
             Q("src/rcs_sbr.py", 'GROUND_DEFAULT = "concrete"'),
             Q("src/rcs_sbr.py", 'return float(g["eps_r"]), 0.0462 * (float(fc) / 1e9) ** 0.7822'),
             Q("benchmark/geometry.py", "FLOOR_EPS_R = 5.24"),
         ],
         "pathsolver_source": [x for x in [
             Q("benchmark/elevation_sweep_md.py", '("ground", "concrete_dark", (0.42, 0.40, 0.37)),'),
             q_slab,
             Q("src/materials.py", "return rt.ITURadioMaterial(name=name, itu_type=spec[\"itu\"],"),
             itu_quote,
             Q("docs/SIONNA_UPGRADE_0914.md", "ITU-R P.2040-4"),
         ] if x is not None]},
        {"item": "ground_reflection_model",
         "kernel_value": ("image method: Fresnel coefficient of a flat homogeneous half-space evaluated at one "
                          "reflection point (target centre), polarization 'v', spherical spreading ratio "
                          "R/R_img per ground leg (spread on: no _nospread tag)"),
         "pathsolver_value": ("ray-traced 120 m x 120 m ground mesh with an ITU concrete slab 0.30 m thick"),
         "same": False,
         "kernel_source": [
             Q("src/rcs_sbr.py", "Gam = complex(fresnel_gamma(psi, eps_r=eps_r, cond=sig, pol=pol, fc=fc))"),
             Q("src/rcs_sbr.py", "· Γ 는 **표적 중심의 반사점 하나**에서 잰 값을 쓴다."),
             Q("src/rcs_sbr.py", "_amp = (R / R_img) if spread else 1.0"),
             Q("benchmark/elevation_sweep_md.py", 'spread=bool(int(getattr(a, "ground_spread", 1))),'),
         ],
         "pathsolver_source": [
             q_slab,
             Q("benchmark/elevation_sweep_md.py", "sc = RP.build_scene(parts, fc=fc)"),
         ]},
        {"item": "ground_scattering_coefficient",
         "kernel_value": "none (specular ground only; no roughness term)",
         "pathsolver_value": slab_S,
         "same": bool(slab_S == 0.0),
         "note": ("Both ground models are specular only. PathSolver diffuse reflection is switched on (F1) but "
                  "the ground material scattering coefficient is 0.0: the ITU branch of make_material passes no "
                  "scattering coefficient, the Sionna default is 0.0, and the arm has no _S override tag."),
         "kernel_source": [Q("src/rcs_sbr.py", "거칠기(확산 산란)는 없다 — 정반사뿐이다.")],
         "pathsolver_source": [x for x in [
             Q("src/materials.py", "return rt.ITURadioMaterial(name=name, itu_type=spec[\"itu\"],"),
             Q("", "scattering_coefficient: float | mi.Float = 0.0,",
               abs_path=Path(list(spec_s.submodule_search_locations)[0]) / "rt/radio_materials/itu_material.py",
               label=f"site-packages/sionna/rt/radio_materials/itu_material.py (sionna-rt {_md.version('sionna-rt')})")
             if spec_s is not None else None,
             Q("benchmark/elevation_sweep_md.py", 'if _envn and _S >= 0.0:'),
         ] if x is not None]},
        {"item": "range_m",
         "kernel_value": float(arm_fields[ARMS[("kernel", "free_sky", None)]]["range_m"]),
         "pathsolver_value": float(arm_fields[ARMS[("pathsolver", "free_sky", "2.0.1")]]["range_m"]),
         "same": bool(len(ranges_all) == 1 and all(float(arm_fields[a]["range_m"]) == ranges_all[0] for a in ARMS.values())),
         "shard_cfg0_values_m": ranges_all,
         "kernel_source": [
             Q("benchmark/elevation_sweep_md.py", '+ ("" if abs(rng_m - RANGE_M) < 1e-9 else f"_r{rng_m:g}")'),
             Q("benchmark/elevation_sweep_md.py", "cfg=np.array([np.nan if plane else rng_m,"),
             Q("benchmark/elevation_sweep_md.py", "range_m=(None if plane else rng_m), ptd=bool(a.ptd))"),
         ],
         "pathsolver_source": [
             Q("benchmark/elevation_sweep_md.py", "cfg=np.array([rng_m, mdep, spp,"),
             Q("benchmark/elevation_sweep_md.py", "RP.place(sc, center=_ctr, az=az, el=el, rng=rng_m, baseline=0.0,"),
         ]},
        {"item": "carrier_hz",
         "kernel_value": fc_const, "pathsolver_value": fc_const,
         "same": bool(all(arm_fields[a].get("fc") is None for a in ARMS.values())),
         "note": "No arm carries an _fc tag, so both engines use the module constant FC.",
         "kernel_source": [
             q_fc,
             Q("benchmark/elevation_sweep_md.py", "if abs(fc - FC) <= 1.0:"),
             Q("benchmark/elevation_sweep_md.py", "d = (2.998e8 / fc) / div"),
         ],
         "pathsolver_source": [
             Q("benchmark/elevation_sweep_md.py", "sc = RP.build_scene(parts, fc=fc)"),
             Q("benchmark/elevation_sweep_md.py", "_t = aa[hit] * np.exp(-1j * 2 * np.pi * fc * tau[hit])"),
         ]},
        {"item": "elevation_sign_convention",
         "kernel_value": ("u = (cos el cos az, cos el sin az, sin el) points from target to radar; the radar sits "
                          "at phase centre + R*u, so el < 0 places the radar below the drone (radar looks up)"),
         "pathsolver_value": ("same unit vector from look_dir(); the transmitter/receiver sit at centre + range*u, "
                              "so el < 0 places the radar below the drone (radar looks up)"),
         "same": True,
         "radar_height_offset_at_el_minus30_m": r4(15.0 * math.sin(math.radians(-30.0))),
         "kernel_source": [
             Q("benchmark/elevation_sweep_md.py", "return np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])"),
             Q("benchmark/elevation_sweep_md.py", "u = los(az, el)"),
             Q("src/rcs_sbr.py", "û 는 표적 → 레이더 방향 단위벡터."),
             Q("src/rcs_sbr.py", "구면파        exp(j2k (R − |p−p_tx|)) ← p_tx = ctr + R·û"),
         ],
         "pathsolver_source": [
             Q("benchmark/report15_probe.py", "return np.array([math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)])"),
             Q("benchmark/report15_probe.py", "tx = c + rng * u + 0.5 * baseline * e1"),
         ]},
        {"item": "azimuth_deg",
         "kernel_value": float(tj.get("az_deg", 0.0)), "pathsolver_value": float(tj.get("az_deg", 0.0)),
         "same": bool(all(arm_fields[a].get("az") is None for a in ARMS.values())),
         "note": "No arm carries an _az tag; both engines take az from the same ledger before the engine branch.",
         "kernel_source": [Q("benchmark/elevation_sweep_md.py", 'az = float(TJ.get("az_deg", 0.0)) if np.isnan(_az_arg) else _az_arg'),
                           Q("outputs/report07_three_engines.json", '"az_deg": 0.0,')],
         "pathsolver_source": [Q("benchmark/elevation_sweep_md.py", 'az = float(TJ.get("az_deg", 0.0)) if np.isnan(_az_arg) else _az_arg')]},
        {"item": "rotor_rpm_per_rotor_and_blade_law",
         "kernel_value": {"rpm_per_rotor": [float(v) for v in rpms], "rotor_preset": None,
                          "blade_law": arm_fields[ARMS[("kernel", "free_sky", None)]]["blade_law"],
                          "blades_per_rotor": blades},
         "pathsolver_value": {"rpm_per_rotor": [float(v) for v in rpms], "rotor_preset": None,
                              "blade_law": arm_fields[ARMS[("pathsolver", "free_sky", "2.0.1")]]["blade_law"],
                              "blades_per_rotor": blades},
         "same": bool(len({arm_fields[a]["blade_law"] for a in ARMS.values()}) == 1
                      and all(arm_fields[a].get("rotor") is None for a in ARMS.values())),
         "note": ("Rotor phases are built once in run() before the engine branch, so both engines use the same "
                  "constant per-rotor rpm (no _rot tag). The blade law in the name is read back with arm_grammar; "
                  "the current default blade law also renders as the same tag."),
         "current_blade_law_tag": bl_now,
         "kernel_source": [
             Q("benchmark/elevation_sweep_md.py", 'rpms = np.asarray(TJ["rpm_per_rotor"], float)'),
             Q("benchmark/elevation_sweep_md.py", "ph = rotor_phases(np.arange(n) / prf, rpms, fp.dirs)"),
             Q("outputs/report07_three_engines.json", '"rpm_per_rotor": ['),
             Q("benchmark/elevation_sweep_md.py", 'tagmf += "" if _law == "legacy" else "_bl" + _law.replace("_", "")'),
             Q("src/geom.py", 'BLADE_LAW_CANON = "per_airframe"'),
         ],
         "pathsolver_source": [
             Q("benchmark/elevation_sweep_md.py", 'rpms = np.asarray(TJ["rpm_per_rotor"], float)'),
             Q("benchmark/elevation_sweep_md.py", 'if a.engine in ("ours", "ours_free", "ours_gpu"):'),
         ]},
        {"item": "mesh_tags",
         "kernel_value": {"drone": drone_key, "mesh_fix": arm_fields[ARMS[("kernel", "free_sky", None)]]["mesh_fix"],
                          "blade_law": arm_fields[ARMS[("kernel", "free_sky", None)]]["blade_law"]},
         "pathsolver_value": {"drone": drone_key, "mesh_fix": arm_fields[ARMS[("pathsolver", "free_sky", "2.0.1")]]["mesh_fix"],
                              "blade_law": arm_fields[ARMS[("pathsolver", "free_sky", "2.0.1")]]["blade_law"]},
         "same": bool(len({(arm_fields[a]["mesh_fix"], arm_fields[a]["blade_law"]) for a in ARMS.values()}) == 1
                      and all(arm_fields[a].get("drone") is None for a in ARMS.values())),
         "current_mesh_fix_tag": mf_now,
         "mesh_fix_and_blade_law_environment_overrides": env_mesh,
         "kernel_source": [
             Q("benchmark/elevation_sweep_md.py", 'tagmf = "" if not _fixes else "_mfix" + "".join(_fixes)'),
             Q("src/geom.py", 'MESH_FIX_CANON = ("battery", "i5")'),
             Q("benchmark/elevation_sweep_md.py", 'drone_key = str(getattr(a, "drone", "") or TJ.get("drone", "matrice4e"))'),
             Q("outputs/report07_three_engines.json", '"drone": "matrice4e",'),
         ],
         "pathsolver_source": [
             Q("benchmark/elevation_sweep_md.py", "+ tagfc + tagth + tagmf + tagant + build_tag()"),
         ]},
        {"item": "pathsolver_max_depth_and_switches",
         "kernel_value": ("not applicable: the kernel has no ray budget or path depth; its shards store NaN in "
                          "cfg[1] and cfg[2]"),
         "pathsolver_value": dict({"max_depth": int(psf["max_depth"]), "switches": psf["switches"],
                                   "samples_per_src": int(psf["spp"])}, **sw_flags),
         "same": False,
         "kernel_shard_cfg_values": {s: cfg_values("kernel", s, None) for s in SCENES},
         "pathsolver_shard_cfg_values": {f"{s}|{b}": cfg_values("pathsolver", s, b) for s in SCENES for b in PS_BUILDS},
         "kernel_source": [
             Q("benchmark/elevation_sweep_md.py", "# ⭐출처 — 우리 팔은 광선 예산·깊이가 없으므로 NaN 으로 둔다."),
             Q("src/rcs_sbr.py", "Etot = complex(E) * d * d"),
         ],
         "pathsolver_source": [x for x in [
             Q("benchmark/elevation_sweep_md.py", 'm = _re.fullmatch(r"R([01])D([01])E([01])F([01])", swbits)'),
             Q("benchmark/elevation_sweep_md.py", "sw = dict(refraction=r_, diffraction=d_, edge_diffraction=e_)"),
             Q("benchmark/elevation_sweep_md.py", "diffuse = f_"),
             Q("benchmark/elevation_sweep_md.py", 'mdep = int(a.max_depth) if getattr(a, "max_depth", 0) else 1'),
             Q("benchmark/elevation_sweep_md.py", "max_depth=mdep, **sw,"),
             Q("benchmark/elevation_sweep_md.py", "float(sw[\"edge_diffraction\"]),"),
             rd_depth,
         ] if x is not None]},
        {"item": "kernel_grid_spacing",
         "kernel_value": {"div": div_const, "spacing_m": r4(lam / div_const), "grid_frozen": True,
                          "grid_div_tag": arm_fields[ARMS[("kernel", "free_sky", None)]].get("grid_div"),
                          "grid_shift_tag": arm_fields[ARMS[("kernel", "free_sky", None)]].get("grid_shift")},
         "pathsolver_value": "not applicable: PathSolver uses no surface grid",
         "same": False,
         "note": ("Spacing uses lambda = c/fc with c = 299792458 m/s here; the builder uses 2.998e8 in its "
                  "spacing line. The same frozen grid (grid_ref) is passed to every pose and to all three "
                  "ground legs."),
         "kernel_source": [
             q_div,
             Q("benchmark/elevation_sweep_md.py", 'div = int(getattr(a, "div", 0) or DIV)'),
             Q("benchmark/elevation_sweep_md.py", "gref = grid_ref_from(probes, fc, spacing=d)"),
             Q("benchmark/elevation_sweep_md.py", "spacing=d, grid_ref=gref_el)"),
             Q("docs/GATES_0902.md", "**Our kernel's el 0 «level» and «width» cannot be used at λ/12.**"),
         ],
         "pathsolver_source": [
             Q("benchmark/elevation_sweep_md.py", 'raise SystemExit("⛔ --grid-shift 는 우리 커널 전용이다 — PathSolver 는 표면 격자를 "'),
         ]},
        {"item": "kernel_ground_terms_included",
         "kernel_value": ("E = E_dd + 2*Gamma*a*exp(-jk*Delta)*E_dg + (Gamma*a*exp(-jk*Delta))^2*E_gg: direct-direct, "
                          "one ground bounce counted once and doubled, two ground bounces; a = R/R_img. The factor 2 "
                          "is stated in the source as an approximation, not reciprocity."),
         "pathsolver_value": ("ground mesh placed in the traced scene; every returned path with at least one "
                              "interaction is summed coherently (max_depth 2)"),
         "same": False,
         "kernel_source": [
             Q("src/rcs_sbr.py", "E = E(û,û)  +  2Γ·E(û′,û)  +  Γ²·E(û′,û′)"),
             Q("src/rcs_sbr.py", "return complex(E_dd) + 2.0 * w * complex(E_dg) + (w * w) * complex(E_gg)"),
             Q("src/rcs_sbr.py", "여기서 «2» 는 상호성이 아니라 근사다"),
         ],
         "pathsolver_source": [
             Q("benchmark/elevation_sweep_md.py", "parts = parts + env_parts(RP.Part, _envn)"),
             Q("benchmark/elevation_sweep_md.py", "hit = (O != RP.NO_OBJ).any(axis=0) if O.size else np.zeros(aa.size, bool)"),
             Q("benchmark/elevation_sweep_md.py", "max_depth=mdep, **sw,"),
         ]},
        {"item": "kernel_ground_model_omissions",
         "kernel_value": ["the ground's own backscatter (the ground is not put into the kernel mesh; the grid covers "
                          "the drone only)",
                          "ground roughness (specular only)",
                          "buildings and poles",
                          "interaction orders beyond ground-drone-ground",
                          "Gamma varies across the drone (one reflection point is used)",
                          "the source says the absolute size of the ground terms is not cited"],
         "pathsolver_value": ["buildings and poles are removed in outdoor01_ground (ground part only)",
                              "ground scattering coefficient 0.0 (no diffuse ground return)",
                              "paths deeper than max_depth 2"],
         "same": False,
         "kernel_source": [
             Q("src/rcs_sbr.py", "왜 격자가 안 터지나 — 지면을 **메쉬에 넣지 않는다.**"),
             Q("src/rcs_sbr.py", "거칠기(확산 산란)는 없다 — 정반사뿐이다."),
             Q("src/rcs_sbr.py", "**건물·기둥은 없다.**"),
             Q("src/rcs_sbr.py", "지면-드론-지면 이상(3 회 이상)은 없다."),
             Q("src/rcs_sbr.py", "· Γ 는 **표적 중심의 반사점 하나**에서 잰 값을 쓴다."),
             Q("src/rcs_sbr.py", "⇒ **지면 항의 절대 크기를 인용하지 않는다.**"),
         ],
         "pathsolver_source": [
             Q("benchmark/elevation_sweep_md.py", 'parts=[p for p in _O1["parts"] if p[0] == "ground"])'),
             q_slab,
             Q("benchmark/elevation_sweep_md.py", "max_depth=mdep, **sw,"),
         ]},
        {"item": "slow_time_prf_and_n_poses",
         "kernel_value": {"prf_hz": sorted({c["prf_hz"] for (e, *_), c in main_cells.items() if e == "kernel"}),
                          "n_poses": sorted({c["n_poses"] for (e, *_), c in main_cells.items() if e == "kernel"})},
         "pathsolver_value": {"prf_hz": sorted({c["prf_hz"] for (e, *_), c in main_cells.items() if e == "pathsolver"}),
                              "n_poses": sorted({c["n_poses"] for (e, *_), c in main_cells.items() if e == "pathsolver"})},
         "same": bool(len(prfs_all) == 1 and len(npo_all) == 1),
         "kernel_source": [Q("benchmark/elevation_sweep_md.py", 'prf = _prf_arg if _prf_arg > 0 else float(TJ["prf_hz"])'),
                           Q("outputs/report07_three_engines.json", '"prf_hz": 19700.0,')],
         "pathsolver_source": [Q("benchmark/elevation_sweep_md.py", "meta=np.array([el, a.shard, a.nshards, n, prf,",
                                 after="np.savez_compressed(f, idx=idx, E=E, npaths=npaths, nret=nret,")]},
    ]

    # ---- spectra file ------------------------------------------------------ #
    spectra_series = []
    npz = {}
    lay_ref = None
    for el in SPECTRA_ELS:
        for eng, scene in (("kernel", "free_sky"), ("pathsolver", "free_sky"),
                           ("kernel", "flat_ground"), ("pathsolver", "flat_ground")):
            build = None if eng == "kernel" else SPECTRA_BUILD
            c = main_cells.get((eng, scene, build, el))
            if c is None:
                continue
            m = c["metrics"]
            lay = m["layout"]
            if lay_ref is None:
                lay_ref = (c["n_poses"], c["prf_hz"], lay)
            elif (c["n_poses"], c["prf_hz"]) != lay_ref[:2]:
                raise LedgerError("spectra series do not share one Doppler axis")
            name = f"psd_db__{eng}{'' if build is None else '_' + build.replace('.', '')}__{scene}__el{el:+g}"
            psd = np.maximum(m["psd_rel"], 10 ** (SPECTRA_FLOOR_DB / 10))
            npz[name] = np.fft.fftshift(10 * np.log10(psd)).astype(np.float64)
            spectra_series.append({"name": name, "engine": eng, "build": build, "scene": scene,
                                   "el_deg": el, "arm": c["arm"]})
    n0, prf0, lay0 = lay_ref
    npz["freq_hz"] = np.fft.fftshift(np.fft.fftfreq(n0, 1.0 / prf0))
    npz["comb_mask"] = np.fft.fftshift(lay0["comb"])
    npz["dc_mask"] = np.fft.fftshift(lay0["dc"])
    npz["series_names"] = np.array([s["name"] for s in spectra_series])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(spectra_path, **npz)

    # ---- definitions / assumptions / not computed --------------------------- #
    m_any = next(iter(main_cells.values()))["metrics"]
    definitions = {
        "merge": ("Each (arm, elevation) cell is rebuilt by scattering E[idx] into an 8,192-pose array. A cell is "
                  "used only if every shard 0..nshards-1 is present once, every pose is written exactly once, and "
                  "meta el / nshards / n_poses / PRF, cfg and the recorded solver build agree across its shards."),
        "comb_contrast_db": ("x = E - mean(E) over the merged poses; X = FFT(x) with a rectangular window; "
                             "P = |X|^2; Doppler bin = PRF / n_poses with PRF from shard meta. Comb bins: for "
                             f"harmonics h = 1..{N_HARM} at +h*FFL and -h*FFL, the nearest bin and +/-{HALF_BINS} "
                             "bins. Non-comb bins: all other bins except DC (bin 0). contrast_db = "
                             "10*log10(mean P over comb bins / mean P over non-comb bins)."),
        "static_db": "10*log10(|mean E|^2), in each engine's own E units",
        "varying_db": "10*log10(mean |E - mean E|^2), in each engine's own E units",
        "sv_db": "static_db - varying_db (dimensionless, within one cell)",
        "harmonic_rel_db": ("for each of the 24 comb lines (order +1..+12 then -1..-12) the summed P over its 5 bins "
                            "divided by the total P over all bins (= total varying power), in dB"),
        "harmonic_corr": "Pearson correlation of the two engines' 24-element harmonic_rel_db vectors",
        "max_abs_harmonic_diff_db": "max over the 24 lines of |kernel harmonic_rel_db - pathsolver harmonic_rel_db|",
        "noncomb_floor_rel_db": "10*log10(mean non-comb P / mean comb P) in the same engine; equals -contrast_db",
        "contrast_change_db": "contrast_ground_db - contrast_free_db within one engine and build",
        "varying_ground_minus_free_db": "varying_db(ground cell) - varying_db(free cell), same engine and build",
        "static_ground_minus_free_db": "static_db(ground cell) - static_db(free cell), same engine and build",
        "matched_elevations_within_engine": ("elevations where the engine (and build) has both scenes and the other "
                                             "engine also has both scenes for at least one build"),
        "pairs": ("every non-excluded elevation present in both the kernel arm and the PathSolver arm of the same "
                  "scene; one row per PathSolver build"),
        "summary_scene_fields": ("top-level fields of summary.free_sky and summary.flat_ground use the 2.0.1 "
                                 "PathSolver rows (the build with the full elevation set); by_build repeats them "
                                 "per build so the two builds are not mixed in one range"),
        "cost_median_s_per_pose": ("median over shards of meta[5] / len(idx), using the shards of the elevations "
                                   "that appear in pairs"),
        "sensitivity": ("same metrics on arms that differ from a main arm in the declared knob only "
                        "(arm_grammar.matched_groups), at elevations used in pairs; differences are within one engine"),
        "geometry_match_sources": "kernel_source and pathsolver_source are lists of verified quotes",
        "build": ("PathSolver build read from the arm name: no solver_build tag = 2.0.1 per arm_grammar; _rt210 = "
                  "the sionna-rt version in runners/SOLVER_BUILDS.json. Kernel rows carry build null."),
        "spectra_npz": ("freq_hz fftshifted; comb_mask and dc_mask fftshifted; each psd_db__* series is "
                        f"10*log10(P / total P) fftshifted, floored at {SPECTRA_FLOOR_DB} dB (only the DC bin reaches "
                        "the floor or near it)"),
        "doppler_bin_hz": r4(m_any["doppler_bin_hz"]),
        "n_comb_bins": m_any["n_comb_bins"], "n_noncomb_bins": m_any["n_noncomb_bins"],
        "ffl_hz": FFL,
        "outliers": ("median_c(E) = median(Re E) + j*median(Im E) over the merged poses; dev = |E - median_c|; a "
                     f"pose is an isolated outlier when dev > factor * median(dev), factor in {list(OUTLIER_FACTORS)}. "
                     "n_poses counts them; varying_share = their sum of |E - mean E|^2 over the cell total; "
                     "*_replaced metrics are the same metrics after setting those poses to median_c. The rule and "
                     "factors are identical for both engines. Pair and within-engine rows use factor "
                     f"{OUTLIER_MAIN:g}; summary.outlier_factor_shake lists all factors."),
        "E_dedup_metrics": ("the same metrics on the PathSolver E_dedup series (each identical path-list line "
                            "counted once), when every shard of the cell stores E_dedup"),
    }
    assumptions = [
        "Both engines' shards were produced by benchmark/elevation_sweep_md.py; the quoted lines are from the "
        "current file, which may be newer than the code that wrote older shards.",
        "The kernel phase-centre offset is recomputed with the current pose code and the default mesh-fix and "
        "blade-law settings; the arm tags match the current defaults (current_mesh_fix_tag, current_blade_law_tag).",
        "Timing in meta[5] is wall time written by the builder; kernel shards and PathSolver shards ran on "
        "different hardware and under unrecorded contention, so cost rows are indicative only.",
        "PathSolver E is used as stored for the headline metrics; E_dedup metrics and n_dup_poses are reported "
        "alongside where the shards store them.",
        "The outlier replacement is a diagnostic of what the metrics become without isolated poses; it is not a "
        "claim about what either engine should produce at those poses.",
        "The kernel source states that the absolute size of its ground terms is not cited; within-engine "
        "ground-minus-free level differences for the kernel carry that caveat.",
        "Levels are never differenced across engines: kernel E is a surface integral in m^2 and PathSolver E is a "
        "dimensionless coherent sum of path coefficients.",
        f"The exclusion window {EXCL_LO_DEG}..{EXCL_HI_DEG} deg was supplied with the task as the repository gate "
        "on el 0 level citations; the quoted GATES_0902 lines support excluding el 0 for the kernel, and no single "
        "source line with both bounds was found.",
        "Comb windows of +/-2 bins are wider than the spread of the four rotors' flash rates at harmonic 12 "
        "(recorded as rotor_flash_spread_half_width_bins_at_h12).",
    ]
    not_computed = [
        "No cross-engine absolute level difference (forbidden by the repository convention; units differ).",
        "Sionna 2.0.1 ITU concrete table is not quoted: only sionna-rt 2.1.0 is installed on this machine.",
        "No pair at el 0 (excluded), and none at kernel-only elevations -52, -68, -82 or PathSolver-only "
        "elevations (-1..-10, near-zero ladder), because the other engine has no cell there.",
        "No kernel flat-ground cells above el 0 exist, so free-sky +15/+30/+60 have no ground counterpart.",
        "No realism statement about either engine (no RF measurement in scope).",
        "The path list at the isolated outlier poses is not inspected here (no path-provenance dump was read), so "
        "which path is missing or changed at those poses is not identified by this ledger.",
        "No kernel flat-ground grid-spacing variants exist (the builder refuses --grid-shift with --ground and no "
        "_div ground arm is present), so the kernel ground cells have no grid sensitivity rows.",
    ]

    ffl_check = {"ffl_hz": FFL, "blades_times_mean_rpm_over_60_hz": r4(ffl_from_rpm),
                 "abs_diff_hz": float(abs(FFL - ffl_from_rpm)),
                 "rotor_flash_rates_hz": [r4(v) for v in ffl_per_rotor],
                 "rotor_flash_spread_half_width_bins_at_h12": r4(harm_spread_bins),
                 "comb_half_width_bins": HALF_BINS,
                 "sources": ffl_sources + [Q("src/drones.py", "prop_blades: int            # 날개 수")]}

    doc = {
        "_meta": {
            "generator": GENERATOR,
            "command": 'CUDA_VISIBLE_DEVICES="" /workspace/.venvs/py312/bin/python ' + GENERATOR,
            "command_arguments_note": (
                "default --root and --out" if (out_path == root / OUT_REL and a.root == str(Path(__file__).resolve().parents[1]))
                else ("--root pointed at " + str(root) + "; --out "
                      + ("inside the repository: " + str(out_path.relative_to(root)) if out_path.is_relative_to(root)
                         else "outside the repository (staging directory, path not recorded)"))),
            "core_argument": a.core,
            "started_utc": started, "finished_utc": None,
            "git_head": git_head(root), "versions": pkg_versions(),
            "cpu_affinity": sorted(os.sched_getaffinity(0)),
            "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
            "scope": ("Simulation-only comparison of two approximations (our SBR+PO kernel and Sionna RT "
                      "PathSolver) from existing shards. No RF measurement. No statement that either engine is "
                      "right or wrong. No cross-engine absolute level difference."),
            "definitions": definitions, "assumptions": assumptions,
            "arms": [{"engine": k[0], "scene": k[1], "build": k[2], "arm": v,
                      "parsed": {kk: vv for kk, vv in arm_fields[v].items() if vv not in (None, False)}}
                     for k, v in ARMS.items()],
            "elevation_exclusion": {"lo_deg": EXCL_LO_DEG, "hi_deg": EXCL_HI_DEG, "inclusive": True,
                                    "excluded_cells": excluded_rows,
                                    "sources": [Q("docs/GATES_0902.md", "⭐**Only el 0 moves by 12 dB.**"),
                                                Q("docs/GATES_0902.md", "**Our kernel's el 0 «level» and «width» cannot be used at λ/12.**")]},
            "flash_rate": ffl_check,
            "meta_layout": {
                "kernel": "meta = [el_deg, shard, nshards, n_poses, prf_hz, elapsed_s]; cfg = [range_m, NaN, NaN, 0.0]",
                "pathsolver": ("meta = [el_deg, shard, nshards, n_poses, prf_hz, elapsed_s, spp]; cfg = [range_m, "
                               "max_depth, spp, physics, refraction, diffraction, edge_diffraction, (det), (solver det)]"),
                "sources": cost_meta_sources},
            "unpaired_cells_not_loaded": unpaired,
            "outlier_context_sources": [
                Q("docs/DEEP_DROP_0902.md", "| 모양 | **연속된 블록**"),
                Q("docs/DEEP_DROP_0902.md", "**표적 에코의 낙차가 아니다.** 지면 클러터가 경로 목록에서 빠졌다 들어왔다 하는 것이다."),
                Q("docs/DEEP_DROP_0902.md", "⚠**표본은 한 칸·세 자세다.**"),
            ],
            "shard_index": {"n_files_matching_shard_pattern": sum(len(v2) for v in idx_all.values() for v2 in v.values()),
                            "n_arm_names": len(idx_all), "n_arm_names_unparsable": len(unparsable),
                            "arm_names_unparsable": unparsable},
            "source_hashes": None,
        },
        "geometry_match": geom_rows,
        "pairs": pairs,
        "within_engine_ground_effect": within,
        "spectrum_shape": shape_rows,
        "summary": summary,
        "cost": cost_rows,
        "sensitivity": sens_rows,
        "sensitivity_summary": sens_summary_rows,
        "sensitivity_scope": [{"engine": e, "scene": s, "knob": "+".join(v), "declared_scope": sc}
                              for e, s, v, sc in SENS_KNOBS],
        "sensitivity_skipped": sens_skipped,
        "cells": cells_rows,
        "spectra_series": spectra_series,
        "spectra_file": SPECTRA_NAME,
        "not_computed": not_computed,
    }
    hits = scan_forbidden(doc)
    if hits:
        raise LedgerError(f"forbidden wording in ledger: {hits[:5]}")
    doc["_meta"]["source_hashes"] = dict(sorted(S.hashes.items()))
    doc["_meta"]["finished_utc"] = utc_now()
    doc["_meta"]["wall_time_s"] = round(time.time() - t_wall, 2)
    out_path.write_text(json.dumps(doc, indent=1, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(f"wrote {out_path} and {spectra_path} in {doc['_meta']['wall_time_s']} s "
          f"({len(pairs)} pairs, {len(sens_rows)} sensitivity rows, {len(cells_rows)} cells)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
