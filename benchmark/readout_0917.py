#!/usr/bin/env python3
"""readout_0917.py - one integrated readout of queues 0948-0956, the ground-only repeat/seed cells and the path-cap
ladders (external review 2026-09-17, section 7 P0/A).

CPU only; it never starts a ray trace and never writes a shard.

1. Manifest. Every job line of runners/jobs_0948..0956*.txt is named by benchmark/elevation_sweep_md.py itself
   (`--dry-run`, one subprocess per line, cached in outputs/readout_0917_stems.json and redone when that script or
   the installed sionna-rt changes). The lines of the other post-upgrade queue files (0931-0947, without 0938,
   which was superseded before launch) are named the same way, only to say which queue file has a line for a
   cell. The cells the views need beyond those queues are written below (VIEW_LINES) as job lines in the same
   grammar and named the same way. Per cell: shards expected and present, completeness (every pose index exactly
   once, E and E_dedup finite), solver_build, the fields read back from the name (src/arm_grammar.py) and checked
   against what the shard stores, shard mtimes, and whether a worker for one of its lines is running now (ps).
2. Metrics per complete cell, each in its own column (definitions in docs/READOUT_0917.md section 1):
   isolated_20xmedian, hampel_w51_k5, copy_k_ratio, copy_k_diff, n_dup, S, contrast_raw / contrast_dedup /
   contrast_interp, env_field_drop_halfmedian (only against an open-sky cell at the same build, elevation,
   azimuth, pattern, orientation, aim offset and cap; a second column uses the open-sky cell at the default cap
   and says so). env_path_missing is not computable from shards; the existing path-list ledger is read as is.
3. Views: (a) 0950 pattern x orientation per scene and cap, (b) 0952 open sky 0 deg cap ladder, (c) ground-only
   -60 deg cap ladder with the nesting of the three counts, (d) repeat and seed spread, (e) 0953-0956 status and
   complete cells, (f) 0948-0949 cells.

Simulation bookkeeping only: no RF measurement is involved, nothing is compared with real hardware, and nothing here
says why the solver omits or adds a path.

    cd /workspace/sionna
    CUDA_VISIBLE_DEVICES="" MPLBACKEND=Agg nice -n 19 taskset -c 8-15 /workspace/.venvs/py312/bin/python benchmark/readout_0917.py

Options: --refresh-stems (redo every dry-run), --max-cores N (CPU affinity and dry-run parallelism, default 4).
Writes outputs/readout_0917.json, outputs/readout_0917_stems.json (dry-run cache) and docs/READOUT_0917.md.
Re-running later picks up cells that have finished since.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import hashlib
import importlib.metadata
import inspect
import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEAM_0910 = Path("/workspace/team_meeting/teammeeting_0910")
for _p in (str(TEAM_0910), str(ROOT / "src"), str(ROOT / "benchmark")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

import numpy as np                                                      # noqa: E402

SHD = ROOT / "outputs" / "elev_sweep_shards"
SWEEP = ROOT / "benchmark" / "elevation_sweep_md.py"
RUNNERS = ROOT / "runners"
OUT_JSON = ROOT / "outputs" / "readout_0917.json"
OUT_STEMS = ROOT / "outputs" / "readout_0917_stems.json"
OUT_MD = ROOT / "docs" / "READOUT_0917.md"
PATHS_DIFF = ROOT / "outputs" / "dropout_paths_0916_diff.json"
PATHS_SRC = ROOT / "outputs" / "dropout_paths_0916.json"             # _meta of the re-solve behind PATHS_DIFF
LEDGER_DEFAULTS = ROOT / "outputs" / "report07_three_engines.json"   # elevation_sweep_md.py TJ (drone, az)

PRIMARY_QUEUES = tuple(range(948, 957))
SCAN_QUEUES = tuple(q for q in range(931, 957) if q != 938)          # 0938 superseded before launch (its line 1)
QUEUE_RE = re.compile(r"^jobs_(\d{4})(?:_.*)?\.txt$")
SHARD_RE = re.compile(r"^(?P<cell>(?P<arm>sionna_.+)_el(?P<el>[-+][\d.]+))_(?P<sh>\d{2,})\.npz$")
DRY_RE = re.compile(r"^\s*\[dry\]\s+\S+\s+([A-Za-z0-9_.+-]+\.npz)\s*$", re.M)

FACTOR = 20.0                      # isolated_20xmedian (dropout_knobs_0916.py FACTOR)
FACTORS_SHAKEN = (10.0, 20.0, 40.0)
HAMPEL_WIN, HAMPEL_K = 51, 5.0     # hampel_w51_k5 (bake_outdoor.hampel_mask / drop_outliers defaults)
ENV_DROP_FRACTION = 0.5            # env_field_drop_halfmedian: |scene - sky| < 0.5 * median
THR_FLOOR, THR_MULT = 5, 3         # jobs_0952 header: a value differs from 2e6 only when |dS| > max(5, 3 d)
REL_CHANGE_SMALL = 1e-5            # repeat view: positions with |E - E_ref| / median|E_ref| above this
IDX_SHOW = 40                      # indices printed in the markdown before "full list in JSON"

BASE = "--engine sionna --n-poses 8192 --range-m 15 --sw R0D0E0F1 --spp 4000000000 --max-depth 2"
SHARD0 = "--shard 0 --nshards 2"
TR = "--ant-pattern tr38901"
GND, CAN = "--env outdoor01_ground", "--env sionna:simple_street_canyon"


def _vl() -> dict:
    """Cells the views need, as job lines in the queue grammar (shard 0 only; the cell stem drops the shard)."""
    v = {}
    for cap in (None, 1000000, 8000000, 16000000, 32000000):
        mp = "" if cap is None else f" --max-paths {cap}"
        v[f"ground_el-60_cap{cap or 'default'}"] = f"--els=-60 {GND}{mp}"
        v[f"sky_el0_cap{cap or 'default'}"] = f"--els=0{mp}"
    for r in (1, 2, 3):
        v[f"ground_el-60_rep{r}"] = f"--els=-60 {GND} --rep {r}"
    v["ground_el-60_rep1_cap8000000"] = f"--els=-60 {GND} --rep 1 --max-paths 8000000"
    for s in (2, 3, 4):
        v[f"ground_el-60_ss{s}"] = f"--els=-60 {GND} --solver-seed {s}"
    v["sky_el0_rep1"] = "--els=0 --rep 1"
    v["canyon_el-60_rep1"] = f"--els=-60 {CAN} --rep 1"
    v["canyon_el-60_ss2"] = f"--els=-60 {CAN} --solver-seed 2"
    for scene, env in (("ground", GND), ("canyon", CAN)):
        for cap in (None, 16000000):
            mp = "" if cap is None else f" --max-paths {cap}"
            c = cap or "default"
            v[f"{scene}_el-60_cap{c}_iso_device"] = f"--els=-60 {env}{mp}"
            v[f"{scene}_el-60_cap{c}_iso_target"] = f"--els=-60 {env}{mp} --ant-orient target"
            v[f"{scene}_el-60_cap{c}_tr_target"] = f"--els=-60 {env}{mp} {TR}"
            v[f"{scene}_el-60_cap{c}_tr_device"] = f"--els=-60 {env}{mp} {TR} --ant-orient device"
    for aim in (0, 5, 10, 20):
        ao = "" if aim == 0 else f" --aim-offset {aim}"
        v[f"sky_el-60_tr_aim{aim}"] = f"--els=-60 {TR}{ao}"
        v[f"ground_el-60_tr_aim{aim}"] = f"--els=-60 {TR} {GND}{ao}"
        v[f"canyon_el-60_tr_aim{aim}"] = f"--els=-60 {TR} {CAN}{ao}"
    v["sky_el-60_iso"] = "--els=-60"
    v["zero_mini5pro"] = "--els=0 --drone mini5pro"
    v["zero_mavic4pro"] = "--els=0 --drone mavic4pro"
    v["zero_d1_default"] = "--els=0 --max-depth 1"
    v["zero_d1_cap32000000"] = "--els=0 --max-depth 1 --max-paths 32000000"
    v["zero_az180"] = "--els=0 --az-deg 180"
    for az in ("0.11", "0.12", "0.2"):
        v[f"window_az{az}"] = f"--els=0 --az-deg {az}"
    for el in ("-0.15", "-0.16"):
        v[f"window_el{el}"] = f"--els={el}"
    v["outdoor01_el-30"] = "--els=-30 --env outdoor01"
    v["outdoor01_el-60"] = "--els=-60 --env outdoor01"
    v["outdoor01_bldg_el-30"] = "--els=-30 --env outdoor01_bldg"
    for cap in (None, 8000000, 16000000, 32000000):
        mp = "" if cap is None else f" --max-paths {cap}"
        v[f"canyon_el-30_cap{cap or 'default'}"] = f"--els=-30 {CAN}{mp}"
    out = {}
    for k, s in v.items():
        toks = shlex.split(BASE) + shlex.split(s)
        if "--max-depth" in shlex.split(s):          # the later --max-depth wins in argparse; keep one
            i = toks.index("--max-depth")
            del toks[i:i + 2]
        out[k] = " ".join(toks + shlex.split(SHARD0))
    return out


VIEW_LINES = _vl()


# ═══ small helpers ══════════════════════════════════════════════════════════════════════════════════════
def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def norm_line(line: str) -> str:
    return " ".join(t for t in shlex.split(line) if t != "--inmem")


def utc(ts: float) -> str:
    return dt.datetime.fromtimestamp(ts, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def db20(x) -> float | None:
    return None if x is None or not x > 0 else float(20.0 * np.log10(x))


def jaccard(a, b):
    a, b = set(a), set(b)
    return None if not (a or b) else len(a & b) / len(a | b)


def hist(k: np.ndarray) -> dict:
    vals, cnt = np.unique(k, return_counts=True)
    return {str(int(v)): int(c) for v, c in zip(vals, cnt)}


def modal(k: np.ndarray):
    if k.size == 0:
        return None
    vals, cnt = np.unique(k, return_counts=True)
    return int(vals[np.argmax(cnt)])


# ═══ 1. queue lines and dry-run names ═══════════════════════════════════════════════════════════════════
def queue_files() -> dict:
    out = {}
    for p in sorted(RUNNERS.iterdir()):
        m = QUEUE_RE.match(p.name)
        if m and int(m.group(1)) in SCAN_QUEUES:
            out[int(m.group(1))] = p
    return out


def queue_lines(p: Path) -> list:
    rows = []
    for no, raw in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        s = raw.strip()
        if s and not s.startswith("#"):
            rows.append((no, s))
    return rows


def solver_rt_version() -> str:
    try:
        return importlib.metadata.version("sionna-rt")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def dry_run(line: str) -> dict:
    cmd = [sys.executable, str(SWEEP), *shlex.split(line), "--dry-run"]
    env = dict(os.environ, CUDA_VISIBLE_DEVICES="", SIONNA2_ALLOW_CPU="1", MPLBACKEND="Agg")
    try:
        p = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, timeout=300,
                           stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return dict(names=[], rc=124, why="dry-run timeout (300 s)")
    txt = p.stdout + "\n" + p.stderr
    names = DRY_RE.findall(txt)
    why = None
    if not names:
        why = next((ln.strip() for ln in txt.splitlines() if "⛔" in ln), None) \
            or next((ln.strip() for ln in reversed(txt.splitlines()) if ln.strip()), f"rc={p.returncode}")
    return dict(names=names, rc=p.returncode, why=why)


def name_lines(lines: set, refresh: bool, jobs: int) -> dict:
    key = dict(sweep_sha256=sha256_file(SWEEP), sionna_rt=solver_rt_version())
    cache = {}
    if OUT_STEMS.exists() and not refresh:
        try:
            old = json.loads(OUT_STEMS.read_text(encoding="utf-8"))
            if all(old.get("_meta", {}).get(k) == v for k, v in key.items()):
                cache = old.get("stems", {})
        except (json.JSONDecodeError, OSError):
            cache = {}
    # A line that named nothing (timeout, refusal, registry error) is tried again on every run instead of being
    # kept as "not named" until the sweep script or the build changes.
    todo = sorted(ln for ln in lines if ln not in cache or not cache[ln].get("names"))
    if todo:
        print(f"  dry-run naming {len(todo)} lines on {jobs} workers", flush=True)
        t0 = time.time()
        with cf.ThreadPoolExecutor(max_workers=jobs) as ex:
            for ln, res in zip(todo, ex.map(dry_run, todo)):
                cache[ln] = res
        print(f"  dry-runs done in {time.time() - t0:.0f} s", flush=True)
    meta = dict(generator="benchmark/readout_0917.py", role="dry-run name cache for outputs/readout_0917.json",
                created_utc=utc(time.time()), **key)
    tmp = OUT_STEMS.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(dict(_meta=meta, stems={k: cache[k] for k in sorted(cache)}), indent=1) + "\n",
                   encoding="utf-8")
    os.replace(tmp, OUT_STEMS)
    return cache


def running_workers() -> dict:
    try:
        txt = subprocess.run(["ps", "-eo", "pid=,etimes=,args="], capture_output=True, text=True, timeout=30).stdout
    except (OSError, subprocess.TimeoutExpired):
        return {}
    out = {}
    for row in txt.splitlines():
        if "elevation_sweep_md.py" not in row or "--dry-run" in row:
            continue
        parts = row.split(None, 2)
        if len(parts) < 3:
            continue
        tail = parts[2].split("elevation_sweep_md.py", 1)[-1]
        try:
            out[norm_line(tail)] = dict(pid=int(parts[0]), elapsed_s=int(parts[1]))
        except ValueError:
            continue
    return out


# ═══ 2. store index, cell loading ═══════════════════════════════════════════════════════════════════════
def store_index() -> dict:
    idx = {}
    for p in SHD.iterdir():
        m = SHARD_RE.match(p.name)
        if m and "_rt" in m.group("arm"):
            idx.setdefault(m.group("cell"), []).append(p)
    return {k: sorted(v) for k, v in idx.items()}


def split_cell(cell: str):
    m = re.match(r"^(?P<arm>.+)_el(?P<el>[-+][\d.]+)$", cell)
    return m.group("arm"), m.group("el")


def fields_of(cell: str, defaults: dict) -> dict:
    from arm_grammar import ArmNameError, parse
    arm, el = split_cell(cell)
    try:
        f = parse(arm)
    except ArmNameError as e:
        return dict(parse_error=str(e))
    pattern = f.get("ant", "iso")
    orient = {"Tgt": "target", "Dev": "device"}.get(f.get("orient"),
                                                    "device" if pattern == "iso" else "target")
    return dict(
        grammar=f, env=f.get("env"), el_deg=float(el), el_token=el,
        az_deg=float(f["az"]) if "az" in f else float(defaults["az_deg"]),
        drone=f.get("drone", defaults["drone"]), max_depth=int(f["max_depth"]),
        cap_from_name=int(f["max_paths"]) if "max_paths" in f else None,
        pattern=pattern, orientation=orient, orientation_tag=f.get("orient"),
        aim_offset_deg=float(f.get("aim", 0.0)), rep=int(f.get("rep", 0)),
        solver_seed=int(f.get("solver_seed", 1)), solver_build_tag=f.get("solver_build"),
        env_alt=f.get("env_alt"), spp=int(f["spp"]), switches=f.get("switches"))


def load_cell(files: list, expected: set, nshards_line: int | None) -> dict:
    now = time.time()
    rec = dict(shards_expected=sorted(expected), shards_present=[p.name for p in files],
               shard_mtime_utc={p.name: utc(p.stat().st_mtime) for p in files},
               shard_bytes={p.name: p.stat().st_size for p in files})
    rec["shards_missing"] = sorted(set(expected) - {p.name for p in files})
    E, Ed, nd, npaths, idxs = [], [], [], [], []
    builds, run_ids, trunc, caps, prfs, nposes, nsh = set(), [], 0, set(), set(), set(), set()
    trunc_stored, trunc_from_stored_value = 0, False
    depth, els, pats, aims, oris = set(), set(), set(), set(), set()
    for p in files:
        try:
            with np.load(p, allow_pickle=False) as z:
                files_ = set(z.files)
                idxs.append(z["idx"].astype(np.int64).ravel())
                E.append(z["E"].ravel())
                Ed.append(z["E_dedup"].ravel() if "E_dedup" in files_ else None)
                nd.append(z["n_dup"].ravel() if "n_dup" in files_ else None)
                npaths.append(z["npaths"].ravel() if "npaths" in files_ else None)
                builds.add(str(z["solver_build"]) if "solver_build" in files_ else "not stored")
                run_ids.append(str(z["run_id"]) if "run_id" in files_ else None)
                if "n_trunc" in files_:
                    # elevation_sweep_md.py merge rule: count nret >= 0.99 * stored cap again rather than adding the
                    # stored n_trunc[0], which older shards counted with a different threshold.
                    nt = np.asarray(z["n_trunc"]).ravel()
                    trunc_stored += int(nt[0])
                    if nt.size > 1:
                        caps.add(int(nt[1]))
                    if "nret" in files_ and nt.size > 1:
                        trunc += int(np.count_nonzero(np.asarray(z["nret"]) >= 0.99 * int(nt[1])))
                    else:
                        trunc += int(nt[0])
                        trunc_from_stored_value = True
                meta = z["meta"]
                els.add(float(meta[0])); nsh.add(int(meta[2])); nposes.add(int(meta[3])); prfs.add(float(meta[4]))
                depth.add(int(z["cfg"][1]))
                pats.add(str(z["ant_pattern"]) if "ant_pattern" in files_ else "iso")
                aims.add(float(z["aim_offset_deg"][0]) if "aim_offset_deg" in files_ else 0.0)
                oris.add(str(z["ant_orient"]) if "ant_orient" in files_ else "auto")
        except Exception as e:                                          # noqa: BLE001
            recent = now - p.stat().st_mtime < 120
            rec.update(complete=False, reason=f"{p.name} unreadable ({type(e).__name__})"
                       + (" - written in the last 2 min, may still be in progress" if recent else ""))
            return rec
    rec.update(solver_build=sorted(builds), run_ids=run_ids, n_trunc_positions=trunc, n_trunc_stored_sum=trunc_stored,
               n_trunc_uses_stored_value=trunc_from_stored_value, cap_from_shard=sorted(caps),
               meta_el_deg=sorted(els), meta_nshards=sorted(nsh), meta_n_poses=sorted(nposes),
               meta_prf_hz=sorted(prfs), cfg_max_depth=sorted(depth), shard_ant_pattern=sorted(pats),
               shard_aim_offset_deg=sorted(aims), shard_ant_orient=sorted(oris))
    if not files:
        rec.update(complete=False, reason="no shard on disk")
        return rec
    n_expect = nposes.pop() if len(nposes) == 1 else None
    want_sh = nshards_line or (nsh.copy().pop() if len(nsh) == 1 else None)
    i = np.concatenate(idxs)
    uniq = np.unique(i)
    rec.update(n_poses_expected=n_expect, n_index_rows=int(i.size), n_unique_idx=int(uniq.size),
               n_duplicate_idx=int(i.size - uniq.size))
    reasons = []
    if want_sh is not None and len(files) < want_sh:
        reasons.append(f"{len(files)} of {want_sh} shards present")
    if n_expect is None or not np.array_equal(uniq, np.arange(n_expect)):
        reasons.append("pose indices do not cover 0..n-1")
    if i.size != uniq.size:
        reasons.append(f"{i.size - uniq.size} duplicate pose indices")
    if len(builds) != 1:
        reasons.append(f"shards disagree on solver_build {sorted(builds)}")
    if any(x is None for x in Ed) or any(x is None for x in nd):
        reasons.append("E_dedup or n_dup not stored")
    Ecat = np.concatenate(E)
    rec["n_nonfinite_E"] = int((~np.isfinite(Ecat)).sum())
    if rec["n_nonfinite_E"]:
        reasons.append(f"{rec['n_nonfinite_E']} non-finite E")
    if not any(x is None for x in Ed):
        Edcat = np.concatenate(Ed)
        rec["n_nonfinite_E_dedup"] = int((~np.isfinite(Edcat)).sum())
        if rec["n_nonfinite_E_dedup"]:
            reasons.append(f"{rec['n_nonfinite_E_dedup']} non-finite E_dedup")
    if reasons:
        rec.update(complete=False, reason="; ".join(reasons))
        return rec
    order = np.argsort(i)
    arr = dict(E=Ecat[order], Ed=np.concatenate(Ed)[order], nd=np.concatenate(nd)[order].astype(np.int64))
    if not any(x is None for x in npaths):
        npm = np.concatenate(npaths)
        rec.update(npaths_median=int(np.median(npm)), npaths_max=int(npm.max()))
        arr["npaths"] = npm[order].astype(np.int64)
    rec.update(complete=True, reason=None, n_poses=int(Ecat.size), prf_hz=prfs.copy().pop())
    rec["_arrays"] = arr
    return rec


def cfg_checks(f: dict, rec: dict, default_cap: int | None) -> list:
    bad = []
    if not rec.get("complete"):
        return bad
    if rec["meta_el_deg"] != [f["el_deg"]]:
        bad.append(f"el: name {f['el_deg']} vs shard meta {rec['meta_el_deg']}")
    if rec["cfg_max_depth"] != [f["max_depth"]]:
        bad.append(f"max_depth: name {f['max_depth']} vs shard cfg {rec['cfg_max_depth']}")
    want_cap = f["cap_from_name"] if f["cap_from_name"] is not None else default_cap
    if want_cap is not None and rec["cap_from_shard"] and rec["cap_from_shard"] != [want_cap]:
        bad.append(f"cap: name {want_cap} vs shard n_trunc {rec['cap_from_shard']}")
    if rec["shard_ant_pattern"] != [f["pattern"]]:
        bad.append(f"pattern: name {f['pattern']} vs shard {rec['shard_ant_pattern']}")
    if rec["shard_aim_offset_deg"] != [f["aim_offset_deg"]]:
        bad.append(f"aim offset: name {f['aim_offset_deg']} vs shard {rec['shard_aim_offset_deg']}")
    want_or = {"Tgt": "target", "Dev": "device"}.get(f["orientation_tag"], "auto")
    if rec["shard_ant_orient"] != [want_or]:
        bad.append(f"orientation: name {want_or} vs shard {rec['shard_ant_orient']}")
    tag = f.get("solver_build_tag")
    if tag and rec["solver_build"] and ("sionna-rt=" + ".".join(tag)) not in rec["solver_build"][0]:
        bad.append(f"build: name _rt{tag} vs shard {rec['solver_build']}")
    return bad


# ═══ 3. metrics ═════════════════════════════════════════════════════════════════════════════════════════
def m_isolated(E: np.ndarray) -> dict:
    m = complex(np.median(E.real), np.median(E.imag))
    d = np.abs(E - m)
    sc = float(np.median(d))
    absm = abs(m)
    if not sc > 0:
        return dict(defined=False, reason="median |E - m| is 0", abs_m=absm)
    z = d / sc
    iso = np.flatnonzero(z > FACTOR)
    non = z[z <= FACTOR]
    below = iso[np.abs(E[iso]) < absm]
    above = iso[np.abs(E[iso]) >= absm]

    def lvl(ix):
        if ix.size == 0 or not absm > 0:
            return None
        v = 20.0 * np.log10(np.abs(E[ix]) / absm)
        return [float(v.min()), float(v.max())]
    return dict(
        defined=True, factor=FACTOR, n=int(iso.size), indices=iso.tolist(),
        counts_by_factor={f"{k:g}": int((z > k).sum()) for k in FACTORS_SHAKEN},
        normaliser_median_abs_dev=sc, abs_m=absm, normaliser_over_abs_m_db=db20(sc / absm) if absm > 0 else None,
        largest_non_isolated_normalised=float(non.max()) if non.size else None,
        smallest_isolated_normalised=float(z[iso].min()) if iso.size else None,
        median_normalised_isolated=float(np.median(z[iso])) if iso.size else None,
        median_abs_dev_over_abs_m_isolated=float(np.median(d[iso] / absm)) if iso.size and absm > 0 else None,
        n_level_below_abs_m=int(below.size), n_level_above_abs_m=int(above.size),
        indices_level_below_abs_m=below.tolist(), indices_level_above_abs_m=above.tolist(),
        level_db_rel_abs_m_below=lvl(below), level_db_rel_abs_m_above=lvl(above))


def m_hampel(E: np.ndarray, BO) -> dict:
    ix = np.flatnonzero(BO.hampel_mask(np.abs(E), HAMPEL_WIN, HAMPEL_K))
    return dict(n=int(ix.size), indices=ix.tolist())


def m_contrast(E, Ed, BO, BG) -> dict:
    R, nrep = BO.drop_outliers(E, HAMPEL_WIN, HAMPEL_K)
    return dict(contrast_raw=float(BG.contrast_db(E)), contrast_dedup=float(BG.contrast_db(Ed)),
                contrast_interp=float(BG.contrast_db(R)), n_replaced_interp=int(nrep))


def m_copy(E, Ed, nd, s_one: float | None) -> dict:
    aEd = np.abs(Ed)
    ok = aEd > 0
    k_ratio = np.full(E.size, -1, np.int64)
    k_ratio[ok] = np.rint(np.abs(E[ok]) / aEd[ok]).astype(np.int64)
    k_ndup = nd + 1
    mode_r = modal(k_ratio[ok])
    S_r = np.flatnonzero(ok & (k_ratio < mode_r)) if mode_r is not None else np.array([], np.int64)
    mode_n = modal(k_ndup)
    S_n = np.flatnonzero(k_ndup < mode_n)
    resid = np.abs(E[ok] - k_ratio[ok] * Ed[ok]) / aEd[ok]
    out = dict(
        n_positions_with_n_dup_gt0=int((nd > 0).sum()), n_dup_hist=hist(nd),
        copy_k_ratio=dict(hist=hist(k_ratio[ok]), n_undefined_E_dedup_zero=int((~ok).sum()), modal=mode_r,
                          max_abs_E_minus_k_Ededup_over_abs_Ededup=float(resid.max()) if resid.size else None,
                          n_ne_ndup_plus1=int((ok & (k_ratio != k_ndup)).sum())),
        S=dict(estimator="copy_k_ratio", n=int(S_r.size), indices=S_r.tolist(), modal_k=mode_r),
        S_from_ndup=dict(n=int(S_n.size), indices=S_n.tolist(), modal_k=mode_n,
                         same_set_as_S=bool(set(S_n.tolist()) == set(S_r.tolist()))),
    )
    if s_one is None or not s_one > 0:
        out["copy_k_diff"] = dict(defined=False, reason="no 0 deg reference cell with a repeated line")
        return out
    x = 1.0 + np.abs(E - Ed) / s_one
    k_diff = np.rint(x).astype(np.int64)
    mode_d = modal(k_diff)
    S_d = np.flatnonzero(k_diff < mode_d)
    out["copy_k_diff"] = dict(
        defined=True, one_copy_abs=s_one, hist=hist(k_diff), modal=mode_d,
        share_modal=float((k_diff == mode_d).mean()),
        p99_distance_from_integer=float(np.percentile(np.abs(x - k_diff), 99)),
        n_ne_copy_k_ratio=int((ok & (k_diff != k_ratio)).sum()), n_ne_ndup_plus1=int((k_diff != k_ndup).sum()),
        S_n=int(S_d.size), S_indices=S_d.tolist())
    return out


def m_envdrop(E, Esky) -> dict:
    D = E - Esky
    a = np.abs(D)
    med = float(np.median(a))
    ix = np.flatnonzero(a < ENV_DROP_FRACTION * med)
    return dict(n=int(ix.size), indices=ix.tolist(), median_abs_diff_db=db20(med),
                median_abs_sky_db=db20(float(np.median(np.abs(Esky)))),
                median_abs_scene_db=db20(float(np.median(np.abs(E)))))


# ═══ 4. references ══════════════════════════════════════════════════════════════════════════════════════
DROP_FOR_SKY = ("env", "env_alt", "rep", "solver_seed")
DROP_FOR_ZERO = ("env", "env_alt", "rep", "solver_seed", "max_paths", "ant", "aim", "orient", "az")


def sky_ref(cell: str, F: dict, complete: set, same_cap: bool):
    f = F[cell]
    if "grammar" not in f or not f["env"]:
        return None
    g = {k: v for k, v in f["grammar"].items() if k not in DROP_FOR_SKY + (() if same_cap else ("max_paths",))}
    hits = []
    for c in complete:
        h = F[c]
        if "grammar" not in h or h["env"] or h["el_token"] != f["el_token"] or h["rep"] or h["solver_seed"] != 1:
            continue
        hg = {k: v for k, v in h["grammar"].items() if k not in DROP_FOR_SKY + (() if same_cap else ("max_paths",))}
        if hg == g and (same_cap or "max_paths" not in h["grammar"]):
            hits.append(c)
    return sorted(hits)[0] if len(hits) == 1 else (None if not hits else f"ambiguous:{sorted(hits)}")


def zero_ref(cell: str, F: dict, complete: set):
    f = F[cell]
    if "grammar" not in f:
        return None
    g = {k: v for k, v in f["grammar"].items() if k not in DROP_FOR_ZERO}
    hits = [c for c in complete if "grammar" in F[c] and F[c]["el_deg"] == 0.0
            and not any(k in F[c]["grammar"] for k in DROP_FOR_ZERO) and F[c]["grammar"] == g]
    return sorted(hits)[0] if len(hits) == 1 else None


def one_copy_abs(arr) -> float | None:
    sel = arr["nd"] >= 1
    if not sel.any():
        return None
    return float(np.median(np.abs(arr["E"][sel] - arr["Ed"][sel]) / arr["nd"][sel]))


# ═══ 5. views ═══════════════════════════════════════════════════════════════════════════════════════════
def row(cells: dict, stem: str | None) -> dict:
    """Compact per-cell row used in every view (None fields when the cell is not complete)."""
    if stem is None or stem not in cells:
        return dict(cell=stem, present=False)
    c = cells[stem]
    r = dict(cell=stem, complete=bool(c["complete"] and "metrics" in c), shards_present=len(c["shards_present"]),
             shards_expected=len(c["shards_expected"]) or None, running=bool(c.get("running")),
             reason=c.get("reason"))
    if not r["complete"]:
        return r
    M = c["metrics"]
    iso = M["isolated_20xmedian"]
    r.update(isolated=iso.get("n"), isolated_by_factor=iso.get("counts_by_factor"),
             normaliser=iso.get("normaliser_median_abs_dev"), abs_m=iso.get("abs_m"),
             abs_m_db=db20(iso.get("abs_m")), normaliser_db=db20(iso.get("normaliser_median_abs_dev")),
             median_normalised_isolated=iso.get("median_normalised_isolated"),
             isolated_below_abs_m=iso.get("n_level_below_abs_m"), isolated_above_abs_m=iso.get("n_level_above_abs_m"),
             median_dev_over_abs_m_isolated=iso.get("median_abs_dev_over_abs_m_isolated"),
             gap=[iso.get("largest_non_isolated_normalised"), iso.get("smallest_isolated_normalised")],
             hampel=M["hampel_w51_k5"]["n"], S=M["copy"]["S"]["n"], modal_k=M["copy"]["S"]["modal_k"],
             contrast_raw=M["contrast"]["contrast_raw"], contrast_dedup=M["contrast"]["contrast_dedup"],
             contrast_interp=M["contrast"]["contrast_interp"],
             env_drop=(M["env_field_drop_halfmedian"] or {}).get("n"),
             env_drop_ref=(M["env_field_drop_halfmedian"] or {}).get("reference"),
             env_drop_sky_default_cap=(M["env_field_drop_halfmedian_sky_default_cap"] or {}).get("n"),
             env_drop_sky_default_cap_ref=(M["env_field_drop_halfmedian_sky_default_cap"] or {}).get("reference"),
             npaths_median=c.get("npaths_median"), n_trunc_positions=c.get("n_trunc_positions"),
             n_poses=c.get("n_poses"))
    return r


def iso_set(cells, stem):
    c = cells.get(stem)
    return None if not c or not c["complete"] else set(c["metrics"]["isolated_20xmedian"].get("indices", []))


def view_a(cells, V):
    out = []
    for scene in ("ground", "canyon"):
        for cap in ("default", 16000000):
            keys = {k: V[f"{scene}_el-60_cap{cap}_{k}"] for k in ("iso_device", "iso_target", "tr_target", "tr_device")}
            rows = {k: row(cells, s) for k, s in keys.items()}
            done = {k for k, r in rows.items() if r.get("complete")}
            # per-position path counts beside the isolated count (jobs_0950 header read-out line)
            base_np = cells[keys["iso_device"]]["_arr"].get("npaths") if "iso_device" in done else None
            for k in done:
                npk = cells[keys[k]]["_arr"].get("npaths")
                rows[k]["npaths_equal_iso_device"] = (None if base_np is None or npk is None
                                                      else int(np.count_nonzero(npk == base_np)))
            eff = []

            def diff(a, b, what):
                if a in done and b in done:
                    ra, rb = rows[a], rows[b]
                    eff.append(dict(effect=what, a=a, b=b,
                                    contrast_raw_db_a_minus_b=ra["contrast_raw"] - rb["contrast_raw"],
                                    contrast_interp_db_a_minus_b=ra["contrast_interp"] - rb["contrast_interp"],
                                    normaliser_ratio_a_over_b=ra["normaliser"] / rb["normaliser"],
                                    abs_m_db_a_minus_b=ra["abs_m_db"] - rb["abs_m_db"],
                                    isolated_a=ra["isolated"], isolated_b=rb["isolated"],
                                    same_isolated_indices=iso_set(cells, keys[a]) == iso_set(cells, keys[b])))
            diff("tr_target", "iso_target", "pattern effect at orientation target")
            diff("tr_device", "iso_device", "pattern effect at orientation device")
            diff("iso_target", "iso_device", "orientation effect at pattern iso")
            diff("tr_target", "tr_device", "orientation effect at pattern tr38901")
            inter = None
            if len(done) == 4:
                inter = dict(kind="same cap", contrast_raw_db=(rows["tr_target"]["contrast_raw"] - rows["iso_target"]["contrast_raw"])
                             - (rows["tr_device"]["contrast_raw"] - rows["iso_device"]["contrast_raw"]))
            jac = {}
            ks = sorted(done)
            for i, a in enumerate(ks):
                for b in ks[i + 1:]:
                    jac[f"{a}|{b}"] = jaccard(iso_set(cells, keys[a]), iso_set(cells, keys[b]))
            out.append(dict(scene=scene, cap=cap, cells=keys, rows=rows, simple_effects=eff,
                            interaction=inter, missing=sorted(set(keys) - done), isolated_jaccard=jac))
    # cross-cap stitch, contrast only, labelled as such
    for scene in ("ground", "canyon"):
        blocks = {b["cap"]: b for b in out if b["scene"] == scene}
        for cap, b in blocks.items():
            if b["interaction"] is not None:
                continue
            other = blocks[16000000 if cap == "default" else "default"]
            vals, used = {}, {}
            for k in ("iso_device", "iso_target", "tr_target", "tr_device"):
                if b["rows"][k].get("complete"):
                    vals[k], used[k] = b["rows"][k]["contrast_raw"], cap
                elif other["rows"][k].get("complete"):
                    vals[k], used[k] = other["rows"][k]["contrast_raw"], other["cap"]
            if len(vals) == 4:
                b["interaction"] = dict(kind="CROSS-CAP STITCH (contrast only; counts are never stitched)",
                                        caps_used=used,
                                        contrast_raw_db=(vals["tr_target"] - vals["iso_target"])
                                        - (vals["tr_device"] - vals["iso_device"]))
    return out


def view_b(cells, V):
    names = [("1000000", "sky_el0_cap1000000"), ("default", "sky_el0_capdefault"), ("8000000", "sky_el0_cap8000000"),
             ("16000000", "sky_el0_cap16000000"), ("32000000", "sky_el0_cap32000000"), ("default rep1", "sky_el0_rep1")]
    rows = []
    ref = cells.get(V["sky_el0_capdefault"])
    rep = cells.get(V["sky_el0_rep1"])
    S_ref = set(ref["metrics"]["copy"]["S"]["indices"]) if ref and ref["complete"] else None
    d = None
    if ref and rep and ref["complete"] and rep["complete"]:
        d = abs(ref["metrics"]["copy"]["S"]["n"] - rep["metrics"]["copy"]["S"]["n"])
    thr = max(THR_FLOOR, THR_MULT * d) if d is not None else None
    for lab, k in names:
        r = row(cells, V[k])
        r["label"] = lab
        c = cells.get(V[k])
        if c and c["complete"]:
            cp = c["metrics"]["copy"]
            S = set(cp["S"]["indices"])
            kd = cp["copy_k_diff"]
            r.update(S_indices=sorted(S), k_ratio_hist=cp["copy_k_ratio"]["hist"],
                     n_k_ratio_ne_ndup_plus1=cp["copy_k_ratio"]["n_ne_ndup_plus1"],
                     k_diff_ne_ratio=kd.get("n_ne_copy_k_ratio"), k_diff_ne_ndup=kd.get("n_ne_ndup_plus1"),
                     k_diff_one_copy_ref=kd.get("reference"),
                     S_from_ndup_same_set=cp["S_from_ndup"]["same_set_as_S"],
                     contrast_raw_reading="at floor while S>=1" if cp["S"]["n"] >= 1 else "S = 0",
                     S_subset_of_default=(S <= S_ref) if S_ref is not None else None,
                     S_same_as_default=(S == S_ref) if S_ref is not None else None,
                     abs_dS_vs_default=abs(cp["S"]["n"] - len(S_ref)) if S_ref is not None else None)
            if thr is not None and lab not in ("default", "default rep1"):
                r["threshold_crossed"] = r["abs_dS_vs_default"] > thr
        rows.append(r)
    return dict(rows=rows, d_default_vs_rep1=d, threshold=thr,
                threshold_rule=f"max({THR_FLOOR}, {THR_MULT}*d), d = |S(default) - S(rep1)|; pre-set working threshold "
                               "(jobs_0952 header), from one same-seed pair - not a seed spread")


def view_c(cells, V):
    rungs = [("1000000", "ground_el-60_cap1000000"), ("default", "ground_el-60_capdefault"),
             ("8000000", "ground_el-60_cap8000000"), ("16000000", "ground_el-60_cap16000000"),
             ("32000000", "ground_el-60_cap32000000"), ("default rep1", "ground_el-60_rep1"),
             ("8000000 rep1", "ground_el-60_rep1_cap8000000")]
    rows, prev = [], {}
    for lab, k in rungs:
        r = row(cells, V[k])
        r["label"] = lab
        c = cells.get(V[k])
        if c and c["complete"]:
            M = c["metrics"]
            I = set(M["isolated_20xmedian"].get("indices", []))
            H = set(M["hampel_w51_k5"]["indices"])
            dm = M["env_field_drop_halfmedian"] or M["env_field_drop_halfmedian_sky_default_cap"]
            Dd = set(dm["indices"]) if dm else None
            r.update(drop_column_used="same cap" if M["env_field_drop_halfmedian"] else
                     ("sky at default cap" if dm else "no reference"),
                     drops=len(Dd) if Dd is not None else None,
                     drops_subset_isolated=(Dd <= I) if Dd is not None else None,
                     isolated_subset_hampel=I <= H,
                     isolated_minus_drops=sorted(I - Dd) if Dd is not None else None,
                     hampel_minus_isolated_n=len(H - I),
                     level_db_isolated_minus_drops=None)
            if Dd is not None and I - Dd:
                E = c["_arr"]["E"]
                absm = M["isolated_20xmedian"]["abs_m"]
                v = 20 * np.log10(np.abs(E[sorted(I - Dd)]) / absm)
                r["level_db_isolated_minus_drops"] = [float(v.min()), float(v.max())]
            if "rep" not in lab:
                if prev:
                    r["drops_subset_of_previous_rung"] = (Dd <= prev["D"]) if Dd is not None and prev["D"] is not None else None
                    r["isolated_subset_of_previous_rung"] = I <= prev["I"]
                prev = dict(I=I, D=Dd)
        rows.append(r)
    return dict(rows=rows)


def field_stability(cells, a, ref):
    ca, cr = cells.get(a), cells.get(ref)
    if not (ca and cr and ca["complete"] and cr["complete"]):
        return None
    Ea, Er = ca["_arr"]["E"], cr["_arr"]["E"]
    med = float(np.median(np.abs(Er)))
    rel = np.abs(Ea - Er) / med
    union = iso_set(cells, a) | iso_set(cells, ref)
    keep = np.array([i for i in range(Er.size) if i not in union], np.int64)
    return dict(max_rel_all=float(rel.max()), max_rel_outside_isolated_union=float(rel[keep].max()),
                n_outside=int(keep.size), n_rel_gt_small=int((rel > REL_CHANGE_SMALL).sum()),
                n_rel_gt_small_outside=int((rel[keep] > REL_CHANGE_SMALL).sum()))


def view_d(cells, V):
    groups = [
        ("ground el -60, same seed reruns", "ground_el-60_capdefault",
         ["ground_el-60_rep1", "ground_el-60_rep2", "ground_el-60_rep3"]),
        ("ground el -60, solver seed changes", "ground_el-60_capdefault",
         ["ground_el-60_ss2", "ground_el-60_ss3", "ground_el-60_ss4"]),
        ("street canyon el -60, same seed rerun", "canyon_el-60_capdefault_iso_device", ["canyon_el-60_rep1"]),
        ("street canyon el -60, solver seed change", "canyon_el-60_capdefault_iso_device", ["canyon_el-60_ss2"]),
    ]
    out = []
    for name, refk, ks in groups:
        ref = V[refk]
        rr = row(cells, ref)
        rows = []
        Iref = iso_set(cells, ref)
        for k in ks:
            r = row(cells, V[k])
            r["label"] = k
            if r.get("complete") and rr.get("complete"):
                I = iso_set(cells, V[k])
                r.update(isolated_jaccard_vs_ref=jaccard(I, Iref), isolated_identical_to_ref=I == Iref,
                         contrast_raw_minus_ref=r["contrast_raw"] - rr["contrast_raw"],
                         contrast_dedup_minus_ref=r["contrast_dedup"] - rr["contrast_dedup"],
                         contrast_interp_minus_ref=r["contrast_interp"] - rr["contrast_interp"],
                         field_stability=field_stability(cells, V[k], ref))
            rows.append(r)
        done = [x for x in [rr] + rows if x.get("complete")]
        spread = {}
        for col in ("isolated", "hampel", "env_drop", "contrast_raw", "contrast_dedup", "contrast_interp"):
            vals = [x[col] for x in done if x.get(col) is not None]
            spread[col] = [min(vals), max(vals)] if vals else None
        out.append(dict(group=name, reference=dict(rr, label=refk), rows=rows, n_complete_including_ref=len(done),
                        range_including_ref=spread))
    return out


def view_offsets(cells, V):
    rows = []
    for aim in (0, 5, 10, 20):
        sky = row(cells, V[f"sky_el-60_tr_aim{aim}"])
        for scene in ("ground", "canyon"):
            r = row(cells, V[f"{scene}_el-60_tr_aim{aim}"])
            r.update(label=f"{scene} aim {aim}", sky_complete=sky.get("complete"),
                     sky_contrast_raw=sky.get("contrast_raw"))
            c = cells.get(V[f"{scene}_el-60_tr_aim{aim}"])
            if c and c["complete"] and c["metrics"]["env_field_drop_halfmedian"]:
                em = c["metrics"]["env_field_drop_halfmedian"]
                r.update(median_abs_diff_db=em["median_abs_diff_db"], median_abs_sky_db=em["median_abs_sky_db"])
            base = cells.get(V[f"{scene}_el-60_tr_aim0"])
            if aim and r.get("complete") and base and base["complete"]:
                r["contrast_raw_minus_aim0"] = r["contrast_raw"] - base["metrics"]["contrast"]["contrast_raw"]
            rows.append(r)
    return rows


def view_zero(cells, V):
    rows = []
    for k in ("sky_el0_capdefault", "zero_mini5pro", "zero_mavic4pro", "zero_d1_default", "zero_d1_cap32000000",
              "zero_az180", "window_az0.11", "window_az0.12", "window_az0.2", "window_el-0.15", "window_el-0.16"):
        r = row(cells, V[k])
        r["label"] = k
        c = cells.get(V[k])
        if c and r.get("complete"):
            cp = c["metrics"]["copy"]
            kd = cp["copy_k_diff"]
            r.update(k_ratio_hist=cp["copy_k_ratio"]["hist"], n_dup_hist=cp["n_dup_hist"],
                     n_k_ratio_ne_ndup_plus1=cp["copy_k_ratio"]["n_ne_ndup_plus1"],
                     S_indices=cp["S"]["indices"],
                     k_diff_modal=kd.get("modal"), k_diff_share_modal=kd.get("share_modal"),
                     k_diff_p99_int=kd.get("p99_distance_from_integer"),
                     k_diff_ne_ratio=kd.get("n_ne_copy_k_ratio"), k_diff_ne_ndup=kd.get("n_ne_ndup_plus1"),
                     k_diff_one_copy_ref=kd.get("reference"))
        rows.append(r)
    return rows


# ═══ 6. markdown ════════════════════════════════════════════════════════════════════════════════════════
def n_(x):
    return "–" if x is None else f"{x:,}"


def f_(x, nd=2):
    return "–" if x is None else f"{x:.{nd}f}"


def e_(x):
    return "–" if x is None else f"{x:.4g}"


def b_(x):
    return "–" if x is None else ("yes" if x else "no")


def idx_(ix):
    if ix is None:
        return "–"
    ix = list(ix)
    if len(ix) <= IDX_SHOW:
        return "{" + ", ".join(map(str, ix)) + "}"
    return "{" + ", ".join(map(str, ix[:IDX_SHOW])) + f", …}} (first {IDX_SHOW} of {len(ix):,}; full list in JSON)"


def status_(r):
    if not r.get("present", True) and r.get("cell") is None:
        return "not named"
    if r.get("complete"):
        return "complete"
    s = f"{r.get('shards_present', 0)}/{r.get('shards_expected') or '?'} shards"
    return s + (", running" if r.get("running") else "")


def label_cell(F: dict) -> str:
    bits = [F["env"] or "open sky", f"el {F['el_token']}"]
    if F["az_deg"]:
        bits.append(f"az {F['az_deg']:g}")
    bits.append(F["drone"])
    bits.append(f"d{F['max_depth']}")
    if F["cap_from_name"]:
        bits.append(f"cap {F['cap_from_name']:,}")
    bits.append(F["pattern"] + "/" + F["orientation"])
    if F["aim_offset_deg"]:
        bits.append(f"aim +{F['aim_offset_deg']:g}")
    if F["rep"]:
        bits.append(f"rep{F['rep']}")
    if F["solver_seed"] != 1:
        bits.append(f"seed {F['solver_seed']}")
    return " · ".join(bits)


def md(doc: dict) -> str:
    M, cells, F = doc["_meta"], doc["cells"], doc["fields"]
    D = doc["definitions"]
    L = []
    w = L.append
    w("# Integrated readout 0917 — queues 0948–0956, ground-only repeats and seeds, path-cap ladders")
    w("")
    w(f"Generated by `{M['generator']}` at {M['created_utc']} (git HEAD `{M['git_head'][:12]}`, script sha256 "
      f"`{M['script_sha256'][:16]}…`). Do not edit by hand — rerun:")
    w("")
    w(f"    {M['command']}")
    w("")
    w("Simulation bookkeeping only: every number below is recomputed from stored PathSolver shards; nothing is an RF "
      "measurement, nothing is compared with real hardware, and nothing here says why the solver omits or adds a path. "
      "Observations are the table values. Every reading rule used is marked with its origin: either pre-set in a "
      "queue header (quoted) or taken from the verified 09-17 review verdicts (not pre-set).")
    w("")
    w(f"Snapshot: {M['n_cells_manifest']:,} cells in the manifest, {M['n_cells_complete']:,} complete; "
      f"{M['n_workers_running']:,} sweep workers running at readout time (ps). A cell is complete when every pose index "
      f"0..n−1 is present exactly once across its shards, E and E_dedup are finite, and all shards carry one "
      f"solver_build.")
    w("")
    # ---- 1. definitions
    w("## 1. Metric definitions (used under these names everywhere below)")
    w("")
    w(f"Record: n = {D['record']['n_poses']:,} rotor positions at PRF {D['record']['prf_hz']:,.0f} Hz "
      f"= {D['record']['length_ms']:.0f} ms; one position = {D['record']['position_step_ms']:.4f} ms. "
      f"FFT bin = PRF/n = {D['record']['bin_hz']:.3f} Hz. Blade-flash rate f_flash = {D['record']['f_flash_hz']:.3f} Hz "
      f"(sionna benchmark/clutter_parts_ladder_0824.py FFL).")
    w("")
    w("| name | formula | source | notes |")
    w("|---|---|---|---|")
    for r in D["table"]:
        w(f"| `{r['name']}` | {r['formula']} | {r['source']} | {r['notes']} |")
    w("")
    # ---- 2. manifest
    w("## 2. Manifest")
    w("")
    w("### 2.1 Queue status (counted from shards on disk, not from supervisor counters)")
    w("")
    w("| queue file | in readout scope | job lines | unique shard names | shards present | cells | cells complete | lines running now | lines not named (BAD) |")
    w("|---|---|---|---|---|---|---|---|---|")
    for q in doc["queues"]:
        w(f"| `{q['file']}` | {'yes' if q['primary'] else 'scanned for bought-by only'} | {q['n_lines']:,} | {q['n_unique_shards']:,} | {q['n_shards_present']:,} | {q['n_cells']:,} | "
          f"{q['n_cells_complete']:,} | {q['n_running']:,} | {q['n_bad']:,} |")
    w("")
    ov = "; ".join(f"`{o['file_b']}` has {o['n_lines_b']:,} line(s) naming shards that `{o['file_a']}` also names"
                   for o in doc["queue_overlaps"]) or "none among the files in readout scope"
    w(f"Queue files scanned for the 'bought by' column: {', '.join(doc['scan_queue_files'])}. "
      "A cell's 'bought by' lists every scanned file with a line that elevation_sweep_md.py names to that cell under "
      f"the installed build ({doc['_meta']['inputs']['sionna_rt']}); overlapping files are listed together. Overlaps "
      f"between files in readout scope: {ov}. For a scanned file whose lines ran before the sionna-rt 2.1.0 install "
      "(2026-09-14, docs/SIONNA_UPGRADE_0914.md), its row counts the names the same lines get now, not what they "
      "wrote at the time.")
    w("")
    w("### 2.2 Cells")
    w("")
    w("| # | cell (fields read back from the name) | build (shard) | shards | complete | bought by (file:lines) | newest shard mtime (UTC) | name/shard checks |")
    w("|---|---|---|---|---|---|---|---|")
    for i, stem in enumerate(doc["manifest_order"]):
        c = cells[stem]
        f = F[stem]
        if "grammar" not in f:
            w(f"| {i} | `{stem}` (name not parsed) | – | – | – | – | – | – |")
            continue
        bb = "; ".join(f"{b['file'][5:9]}:{','.join(map(str, b['lines']))}" for b in c["bought_by"]) or "not in scanned files"
        mt = max(c["shard_mtime_utc"].values()) if c["shard_mtime_utc"] else "–"
        build = c.get("solver_build") or ["–"]
        chk = "ok" if c["complete"] and not c["cfg_mismatches"] else ("; ".join(c["cfg_mismatches"]) or "–")
        comp = "yes" if c["complete"] else f"no — {c.get('reason')}" + (" (worker running)" if c.get("running") else "")
        w(f"| {i} | {label_cell(f)} | {' / '.join(build)} | {len(c['shards_present'])}/{len(c['shards_expected']) or '?'} | "
          f"{comp} | {bb} | {mt} | {chk} |")
    w("")
    w("Full stems, shard file names, sizes, mtimes, run ids and per-shard stored fields are in the JSON (`cells`).")
    w("")
    # ---- 3a
    common = doc["common_scope"]
    w("## 3. Views")
    w("")
    w(f"Common to every cell below unless a column says otherwise: {common}.")
    w("")
    w("### (a) Queue 0950 — antenna pattern × device orientation, el −60")
    w("")
    w("Orientation here is pointing plus the rotation of the V polarisation basis that comes with it; the two are "
      "not separated in these cells (confounded). `iso/device` and `tr38901/target` are the older diagonal cells; "
      "`iso/target` (`_orTgt`) and `tr38901/device` (`_orDev`) are the 0950 cells. Counts from different caps are never "
      "put in one 2×2.")
    w("")
    for b in doc["views"]["a"]:
        cap = (f"default cap ({n_(doc['default_cap'])} per the shard n_trunc)" if b["cap"] == "default"
               else f"cap {b['cap']:,}")
        w(f"**{b['scene']} · {cap}**")
        w("")
        w("| pattern/orientation | status | isolated_20xmedian (×10/×20/×40) | normaliser median\\|E−m\\| [dB] | \\|m\\| [dB] | "
          "median z of isolated | median \\|E−m\\|/\\|m\\| of isolated | isolated with \\|E\\| < \\|m\\| / ≥ \\|m\\| | gap: largest non-isolated z / smallest isolated z | "
          "hampel_w51_k5 | env_field_drop_halfmedian (same cap) | positions with npaths = iso/device (same cap) | "
          "contrast_raw / dedup / interp [dB] |")
        w("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for k in ("iso_device", "iso_target", "tr_target", "tr_device"):
            r = b["rows"][k]
            lab = k.replace("tr_", "tr38901/").replace("iso_", "iso/")
            if not r.get("complete"):
                w(f"| {lab} | {status_(r)} | – | – | – | – | – | – | – | – | – | – | – |")
                continue
            npe = r.get("npaths_equal_iso_device")
            npe = "–" if npe is None else f"{npe:,} of {r['n_poses']:,}"
            byf = r["isolated_by_factor"]
            w(f"| {lab} | complete | {byf['10']:,}/{byf['20']:,}/{byf['40']:,} | {f_(r['normaliser_db'])} | {f_(r['abs_m_db'])} | "
              f"{f_(r['median_normalised_isolated'], 1)} | {e_(r['median_dev_over_abs_m_isolated'])} | "
              f"{n_(r['isolated_below_abs_m'])} / {n_(r['isolated_above_abs_m'])} | "
              f"{f_(r['gap'][0], 2)} / {f_(r['gap'][1], 1)} | {n_(r['hampel'])} | "
              f"{n_(r['env_drop']) if r['env_drop_ref'] else 'no reference'} | {npe} | "
              f"{f_(r['contrast_raw'], 4)} / {f_(r['contrast_dedup'], 4)} / {f_(r['contrast_interp'], 4)} |")
        w("")
        if b["simple_effects"]:
            w("| simple effect (same cap) | Δ contrast_raw [dB] | Δ contrast_interp [dB] | normaliser ratio | Δ\\|m\\| [dB] | isolated (a, b) | same isolated indices |")
            w("|---|---|---|---|---|---|---|")
            for e in b["simple_effects"]:
                w(f"| {e['effect']} ({e['a']} − {e['b']}) | {f_(e['contrast_raw_db_a_minus_b'], 4)} | "
                  f"{f_(e['contrast_interp_db_a_minus_b'], 4)} | {f_(e['normaliser_ratio_a_over_b'], 3)} | "
                  f"{f_(e['abs_m_db_a_minus_b'])} | {n_(e['isolated_a'])}, {n_(e['isolated_b'])} | {b_(e['same_isolated_indices'])} |")
            w("")
        if b["interaction"]:
            it = b["interaction"]
            extra = ("; caps used: " + ", ".join(
                f"{k.replace('tr_', 'tr38901/').replace('iso_', 'iso/')} {('default' if v == 'default' else f'{v:,}')}"
                for k, v in it["caps_used"].items())) if "caps_used" in it else ""
            w(f"Interaction on contrast_raw [(tr38901/target − iso/target) − (tr38901/device − iso/device)]: "
              f"{f_(it['contrast_raw_db'], 4)} dB — **{it['kind']}**{extra}.")
        else:
            w(f"Interaction: not computed — not complete at this cap: {', '.join(b['missing'])}; no complete cell to "
              "substitute at the other cap either.")
        if b["isolated_jaccard"]:
            w("")
            w("Same-pose Jaccard of isolated_20xmedian index sets across antenna settings (same scene, same cap): "
              + "; ".join(f"{k.replace('|', ' vs ')} {('–' if v is None else f'{v:.3f}')}" for k, v in b["isolated_jaccard"].items())
              + " (– = both sets empty).")
        w("")
    sd = doc["views"]["d"]

    def _rng(g, col):
        v = g["range_including_ref"][col]
        return "–" if not v else f"{v[0]:.4f} … {v[1]:.4f}"
    seed_groups = [g for g in sd if "solver seed" in g["group"]]
    w("Scale for the contrast differences above, from the solver-seed groups of view (d) (iso/device at the default "
      "cap; view (d) has no seed group for tr38901, for iso/target or for another cap): "
      + "; ".join(f"{g['group']}: contrast_raw {_rng(g, 'contrast_raw')} dB, contrast_interp {_rng(g, 'contrast_interp')} dB "
                  f"over {g['n_complete_including_ref']} complete cells (reference included)" for g in seed_groups)
      + ". Reading rule (from the 09-17 review verdicts, not pre-set in a queue header): a difference inside the "
        "seed spread of the same scene is not read as an effect.")
    w("")
    # ---- 3b
    vb = doc["views"]["b"]
    w("### (b) Queue 0952 — open sky, el 0, max_num_paths_per_src ladder")
    w("")
    w(f"S = short positions (copy_k_ratio below its modal value). Working threshold: {vb['threshold_rule']}; "
      f"d = {n_(vb['d_default_vs_rep1'])}, threshold = {n_(vb['threshold'])}. A change within the threshold is "
      "'threshold not crossed', not 'no effect'. contrast_raw is reported as at its floor while S ≥ 1; its value there "
      "depends on which positions are short.")
    w("")
    w("| cap | status | modal copy_k_ratio | S | S indices | S ⊆ S(default) | S = S(default) | \\|ΔS\\| vs default | threshold crossed | copy_k_ratio ≠ n_dup+1 | copy_k_diff ≠ copy_k_ratio / ≠ n_dup+1 | isolated_20xmedian | hampel_w51_k5 | contrast_raw | contrast_dedup | contrast_interp |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in vb["rows"]:
        if not r.get("complete"):
            w(f"| {r['label']} | {status_(r)} | – | – | – | – | – | – | – | – | – | – | – | – | – | – |")
            continue
        kdref = r.get("k_diff_one_copy_ref")
        kd = (f"{n_(r['k_diff_ne_ratio'])} / {n_(r['k_diff_ne_ndup'])}"
              + (" (self-referenced)" if kdref == r["cell"] else "")) if kdref else "not defined"
        w(f"| {r['label']} | complete | {r['modal_k']} | {n_(r['S'])} | {idx_(r['S_indices'])} | {b_(r['S_subset_of_default'])} | {b_(r['S_same_as_default'])} | "
          f"{n_(r['abs_dS_vs_default'])} | {b_(r.get('threshold_crossed')) if 'threshold_crossed' in r else '–'} | "
          f"{n_(r['n_k_ratio_ne_ndup_plus1'])} | {kd} | {n_(r['isolated'])} | {n_(r['hampel'])} | "
          f"{f_(r['contrast_raw'], 4)} ({r['contrast_raw_reading']}) | {f_(r['contrast_dedup'], 4)} | {f_(r['contrast_interp'], 4)} |")
    w("")
    w("2.0.1 counts are not recomputed here. Where a 2.0.1 zero-degree count is put next to these rows, name the cell "
      "(`_az0_` run of 09-04 vs the untagged run of 09-06); see the review verdicts for §2.4.")
    w("")
    # ---- 3c
    w("### (c) Ground only, el −60 — path-cap ladder: env_field_drop_halfmedian vs isolated_20xmedian vs hampel_w51_k5")
    w("")
    vc = doc["views"]["c"]["rows"]
    no_same = [r["label"] for r in vc if r.get("complete") and r.get("drop_column_used") == "sky at default cap"]
    w("Drop reference per rung (column 'drop reference'): 'same cap' where the store scan found a complete open-sky "
      "cell at the same build, el −60, antenna setting and cap; 'sky at default cap' where it did not and the open-sky "
      "cell at the default cap was used, so the reference differs from the scene in cap. Rungs using the default-cap "
      f"reference in this snapshot: {', '.join(no_same) or 'none'}.")
    w("")
    w("| cap | status | drop reference | env_field_drop_halfmedian | isolated_20xmedian | hampel_w51_k5 | drops ⊆ isolated | isolated ⊆ hampel | isolated − drops (indices) | level of isolated − drops rel. \\|m\\| [dB] | hampel − isolated | drops ⊆ previous rung | isolated ⊆ previous rung | contrast_raw / dedup / interp [dB] |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in doc["views"]["c"]["rows"]:
        if not r.get("complete"):
            w(f"| {r['label']} | {status_(r)} | – | – | – | – | – | – | – | – | – | – | – | – |")
            continue
        lv = r["level_db_isolated_minus_drops"]
        w(f"| {r['label']} | complete | {r['drop_column_used']} | {n_(r['drops'])} | {n_(r['isolated'])} | {n_(r['hampel'])} | "
          f"{b_(r['drops_subset_isolated'])} | {b_(r['isolated_subset_hampel'])} | {idx_(r['isolated_minus_drops'])} | "
          f"{'–' if lv is None else f'{lv[0]:+.2f} … {lv[1]:+.2f}'} | {n_(r['hampel_minus_isolated_n'])} | "
          f"{b_(r.get('drops_subset_of_previous_rung'))} | {b_(r.get('isolated_subset_of_previous_rung'))} | "
          f"{f_(r['contrast_raw'], 4)} / {f_(r['contrast_dedup'], 4)} / {f_(r['contrast_interp'], 4)} |")
    w("")
    w("--max-paths sets both the candidate buffer and the specular-chain hash counter size in sionna-rt "
      "(benchmark/dropout_knobs_0916.py max_paths_caveat), so each rung moves two things at once.")
    w("")
    # ---- 3d
    w("### (d) Repeat and seed spread of the references (default cap)")
    w("")
    w(f"Same-seed reruns (`--rep`) and solver-seed changes (`--solver-seed`) are separate groups. Field stability = "
      f"max |E − E_ref| / median|E_ref| over all positions and over positions isolated in neither cell; "
      f"'n > {REL_CHANGE_SMALL:g}' counts positions above that relative change. env_field_drop_halfmedian here uses the "
      "open-sky cell with rep 0 and solver seed 1 for every row, including rows whose scene cell has another rep or seed "
      "(the reference choice does not look for an open-sky cell with the same rep or seed).")
    w("")
    for g in sd:
        rr = g["reference"]
        w(f"**{g['group']}** — reference: {status_(rr)}; isolated_20xmedian {n_(rr.get('isolated'))}, hampel_w51_k5 {n_(rr.get('hampel'))}, "
          f"env_field_drop_halfmedian {n_(rr.get('env_drop'))}, contrast_raw/dedup/interp "
          f"{f_(rr.get('contrast_raw'), 4)} / {f_(rr.get('contrast_dedup'), 4)} / {f_(rr.get('contrast_interp'), 4)} dB")
        w("")
        w("| cell | status | isolated_20xmedian | Jaccard vs ref | identical set | hampel_w51_k5 | env_field_drop_halfmedian | Δ contrast_raw / dedup / interp vs ref [dB] | field max rel. change all / outside isolated | n > small (all / outside) |")
        w("|---|---|---|---|---|---|---|---|---|---|")
        for r in g["rows"]:
            r = dict(r, label=label_cell(F[r["cell"]]) if r.get("cell") in F and "grammar" in F[r["cell"]] else r["label"])
            if not r.get("complete"):
                w(f"| {r['label']} | {status_(r)} | – | – | – | – | – | – | – | – |")
                continue
            fs = r.get("field_stability") or {}
            w(f"| {r['label']} | complete | {n_(r['isolated'])} | {f_(r.get('isolated_jaccard_vs_ref'), 3)} | "
              f"{b_(r.get('isolated_identical_to_ref'))} | {n_(r['hampel'])} | {n_(r['env_drop'])} | "
              f"{f_(r.get('contrast_raw_minus_ref'), 4)} / {f_(r.get('contrast_dedup_minus_ref'), 4)} / {f_(r.get('contrast_interp_minus_ref'), 4)} | "
              f"{e_(fs.get('max_rel_all'))} / {e_(fs.get('max_rel_outside_isolated_union'))} | "
              f"{n_(fs.get('n_rel_gt_small'))} / {n_(fs.get('n_rel_gt_small_outside'))} |")
        rg = g["range_including_ref"]
        w("")
        w(f"Range over the {g['n_complete_including_ref']} complete cells including the reference: "
          + "; ".join(f"{METRIC_LABEL.get(k, k)} {('–' if v is None else (f'{v[0]:,}…{v[1]:,}' if isinstance(v[0], int) else f'{v[0]:.4f}…{v[1]:.4f}'))}"
                      for k, v in rg.items()) + ".")
        w("")
    # ---- 3e
    w("### (e) Queues 0953–0956")
    w("")
    w("**0954 + 0956 — tr38901 pointed off the drone toward the ground, el −60.** Offsets +5/+10/+20° are vertical tilts "
      "toward the ground at this elevation only (no negative or sideways offsets). The field difference due to the "
      "environment (scene − open sky at the same offset) is called a ground contribution only where path classes show it. "
      "Pre-set practical threshold from the 0954 header: under 1 dB is 'did not cross the threshold'. One run per cell. "
      "The single tr38901 model does not stand in for any real antenna.")
    w("")
    w("| scene · aim offset | status | contrast_raw [dB] | Δ vs aim 0 [dB] | open sky same offset: status, contrast_raw | env_field_drop_halfmedian | median \\|scene − sky\\| [dB] | median \\|sky\\| [dB] | isolated_20xmedian | hampel_w51_k5 |")
    w("|---|---|---|---|---|---|---|---|---|---|")
    for r in doc["views"]["e_offsets"]:
        sky = "complete, " + f_(r["sky_contrast_raw"], 4) if r["sky_complete"] else "not complete"
        if not r.get("complete"):
            w(f"| {r['label']} | {status_(r)} | – | – | {sky} | – | – | – | – | – |")
            continue
        w(f"| {r['label']} | complete | {f_(r['contrast_raw'], 4)} | {f_(r.get('contrast_raw_minus_aim0'), 4)} | {sky} | "
          f"{n_(r['env_drop']) if r['env_drop_ref'] else 'no reference'} | {f_(r.get('median_abs_diff_db'))} | "
          f"{f_(r.get('median_abs_sky_db'))} | {n_(r['isolated'])} | {n_(r['hampel'])} |")
    w("")
    w("**0953 and 0955 B — copy counts at and near 0°, open sky.** copy_k_diff uses |one copy| from the 0° cell of the "
      "same build, drone and max_depth (column 'one-copy reference'); the 0955 B rows are the 2.0.1 edge values "
      "re-checked on 2.1.0, not a 2.1.0 boundary.")
    w("")
    w("| cell | status | copy_k_ratio histogram | modal k (ratio) | S | S indices | ratio ≠ n_dup+1 | copy_k_diff modal (share) | diff p99 distance from integer | diff ≠ ratio / ≠ n_dup+1 | one-copy reference | isolated_20xmedian | hampel_w51_k5 |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in doc["views"]["e_zero"]:
        r = dict(r, label=label_cell(F[r["cell"]]) if r.get("cell") in F and "grammar" in F[r["cell"]] else r["label"])
        if not r.get("complete"):
            w(f"| {r['label']} | {status_(r)} | – | – | – | – | – | – | – | – | – | – | – |")
            continue
        ref = r["k_diff_one_copy_ref"]
        ref = "–" if ref is None else ("this cell (self-referenced)" if ref == r["cell"] else label_cell(F[ref]))
        sh = "–" if r["k_diff_share_modal"] is None else f"{r['k_diff_modal']} ({100 * r['k_diff_share_modal']:.2f} %)"
        w(f"| {r['label']} | complete | {r['k_ratio_hist']} | {r['modal_k']} | {n_(r['S'])} | {idx_(r['S_indices'])} | "
          f"{n_(r['n_k_ratio_ne_ndup_plus1'])} | {sh} | {e_(r['k_diff_p99_int'])} | "
          f"{n_(r['k_diff_ne_ratio'])} / {n_(r['k_diff_ne_ndup'])} | {ref} | {n_(r['isolated'])} | {n_(r['hampel'])} |")
    w("")
    for q in (953, 954, 955, 956):
        _queue_table(w, doc, q)
    w("### (f) Queues 0948–0949")
    w("")
    for q in (948, 949):
        _queue_table(w, doc, q)
    # ---- 4 path lists
    pm = doc["env_path_missing"]
    w("## 4. env_path_missing where path lists exist")
    w("")
    if pm is None:
        w("No path-list ledger found.")
    else:
        w(f"Source: `{pm['source']}` (sha256 `{pm['sha256'][:16]}…`, generator `{pm['generator']}`). Only the poses listed "
          "there have path lists; everything else in this readout is field-based. The path lists come from a separate "
          f"re-solve of those poses and their neighbours (`{pm['paths_generator']}`, started {pm['paths_run_utc']}, "
          f"{pm['paths_solver_build']}), not from the stored shards the other columns read; that run listed "
          f"the first {pm['paths_n_outliers']} isolated poses in index order per cell (factor {pm['paths_factor']:g}), "
          "so the listed poses are the low-index end of each isolated set, not a random sample of it.")
        w("")
        w("| cell | listed isolated poses (indices) | env-only path missing vs ≥1 neighbour | vs both computed neighbours | listed poses in env_field_drop_halfmedian (same cell) | listed poses with a missing path that are in that set |")
        w("|---|---|---|---|---|---|")
        for r in pm["cells"]:
            w(f"| {label_cell(F[r['cell']]) if r['cell'] in F and 'grammar' in F[r['cell']] else r['cell']} | {n_(r['n_listed'])} {idx_(r['listed'])} | "
              f"{n_(r['n_missing_any'])} | {n_(r['n_missing_all'])} | {n_(r['n_in_drops']) if r['n_in_drops'] is not None else 'no drop column'} | "
              f"{n_(r['n_missing_any_in_drops']) if r['n_missing_any_in_drops'] is not None else '–'} |")
        w("")
    # ---- 5 open
    w("## 5. Not read here / still open")
    w("")
    for s in doc["open_items"]:
        w(f"- {s}")
    w("")
    return "\n".join(L)


METRIC_LABEL = dict(isolated="isolated_20xmedian", hampel="hampel_w51_k5", env_drop="env_field_drop_halfmedian")


def _drop_cell(r):
    if r.get("env_drop_ref"):
        return n_(r["env_drop"])
    if r.get("env_drop_sky_default_cap_ref"):
        return f"no reference (sky at default cap: {n_(r['env_drop_sky_default_cap'])})"
    return "no reference"


def _queue_table(w, doc, q):
    qq = next((x for x in doc["queues"] if x["queue"] == q), None)
    if qq is None:
        return
    w(f"**`{qq['file']}`** — {qq['n_cells_complete']:,}/{qq['n_cells']:,} cells complete, "
      f"{qq['n_shards_present']:,}/{qq['n_unique_shards']:,} shards present, {qq['n_running']:,} lines running now.")
    w("")
    w("| cell | status | isolated_20xmedian | hampel_w51_k5 | modal copy_k_ratio / S | env_field_drop_halfmedian (same cap) | contrast_raw / dedup / interp [dB] | npaths median | positions at the cap |")
    w("|---|---|---|---|---|---|---|---|---|")
    for stem in qq["cells"]:
        r = row(doc["_cells_live"], stem)
        f = doc["fields"][stem]
        lab = label_cell(f) if "grammar" in f else stem
        if not r.get("complete"):
            w(f"| {lab} | {status_(r)} | – | – | – | – | – | – | – |")
            continue
        w(f"| {lab} | complete | {n_(r['isolated'])} | {n_(r['hampel'])} | {r['modal_k']} / {n_(r['S'])} | "
          f"{_drop_cell(r)} | "
          f"{f_(r['contrast_raw'], 4)} / {f_(r['contrast_dedup'], 4)} / {f_(r['contrast_interp'], 4)} | "
          f"{n_(r['npaths_median'])} | {n_(r['n_trunc_positions'])} |")
    w("")


# ═══ 7. main ════════════════════════════════════════════════════════════════════════════════════════════
def definitions(n_poses: int, prf: float, BG, BO) -> dict:
    sig = inspect.signature(BO.drop_outliers)
    assert sig.parameters["win"].default == HAMPEL_WIN and sig.parameters["k"].default == HAMPEL_K
    ffl = float(BG.FFL)
    band_hi = BG.NHARM * ffl
    return dict(
        record=dict(n_poses=n_poses, prf_hz=prf, length_ms=1e3 * n_poses / prf, position_step_ms=1e3 / prf,
                    bin_hz=prf / n_poses, f_flash_hz=ffl),
        table=[
            dict(name="isolated_20xmedian",
                 formula=f"m = component-wise median of E, median(Re E) + j·median(Im E); d = \\|E − m\\|; isolated ⟺ d > {FACTOR:g}·median(d). "
                         f"Also: counts at ×{FACTORS_SHAKEN[0]:g} and ×{FACTORS_SHAKEN[2]:g}; normaliser median(d); \\|m\\|; z = d/median(d); gap = largest z below the "
                         f"threshold vs smallest z above it; normaliser-free median \\|E−m\\|/\\|m\\| of isolated positions; "
                         "isolated positions with \\|E\\| below / at-or-above \\|m\\|.",
                 source="benchmark/dropout_knobs_0916.py isolated()",
                 notes="The normaliser is per cell, so the same count can mean very different event sizes between cells."),
            dict(name="hampel_w51_k5",
                 formula=f"on x = \\|E\\|: local median and MAD in a sliding window of {HAMPEL_WIN} positions "
                         f"({1e3 * HAMPEL_WIN / prf:.2f} ms), edges reflect-padded; marked ⟺ \\|x − local median\\| > {HAMPEL_K:g}·1.4826·MAD",
                 source="team_meeting/teammeeting_0910/bake_outdoor.py hampel_mask", notes="Uses \\|E\\| only (no phase)."),
            dict(name="env_field_drop_halfmedian",
                 formula=f"D = E_scene − E_open sky; drop ⟺ \\|D\\| < {ENV_DROP_FRACTION:g}·median(\\|D\\|)",
                 source="make_0917_v16.py notes / jobs_0954 header wording; reference cell chosen here",
                 notes="Column 'same cap': open-sky cell with the same build, elevation, azimuth, drone, depth, rays, pattern, "
                       "orientation, aim offset and cap (rep 0, seed 1), else 'no reference'. Column 'sky at default cap': "
                       "the same but the open-sky cell at the default cap; used only where labelled. A field-threshold count: "
                       "it is not a path list."),
            dict(name="env_path_missing",
                 formula="an environment-only path key present at a non-isolated neighbour position and absent at the position",
                 source="outputs/dropout_paths_0916_diff.json (benchmark/read_dropout_paths_0916.py)",
                 notes="From path lists only; not computable from shards. Section 4 reads the existing lists."),
            dict(name="copy_k_ratio",
                 formula="k = round(\\|E\\| / \\|E_dedup\\|); modal k over positions; also the count of positions with k ≠ n_dup + 1 "
                         "and max \\|E − k·E_dedup\\|/\\|E_dedup\\|",
                 source="jobs_0952 / jobs_0953 headers",
                 notes="Exact only when the removed copies dominate the field; mixed fields give non-integer ratios."),
            dict(name="copy_k_diff",
                 formula="k = 1 + \\|E − E_dedup\\| / \\|one copy\\|; \\|one copy\\| = median over positions with n_dup ≥ 1 of "
                         "\\|E − E_dedup\\|/n_dup in the 0° open-sky cell of the same build, drone, depth and rays (default cap, iso)",
                 source="team_meeting/teammeeting_0917/bake_repeat_count.py (that builder takes n_dup = 2 positions)",
                 notes="Meaningful where the removed line is the drone echo of that 0° cell."),
            dict(name="n_dup", formula="number of path rows removed as duplicates at the position (stored by the sweep)",
                 source="benchmark/elevation_sweep_md.py", notes="k = n_dup + 1 is the third copy-count estimator."),
            dict(name="S", formula="positions whose copy_k_ratio is below its modal value (index set kept); also S from n_dup + 1",
                 source="jobs_0952 header", notes="Short-position count; not an isolation count."),
            dict(name="contrast_raw / contrast_dedup / contrast_interp",
                 formula=f"10·log10(mean P over comb bins / mean P over other non-DC bins); P = \\|FFT(x − mean x)/n\\|², rectangular window, "
                         f"full record; comb = ± harmonics 1…{BG.NHARM} of f_flash, ±{BG.HALF} bins each (±{BG.HALF * prf / n_poses:.2f} Hz), "
                         f"i.e. up to ±{band_hi:.0f} Hz of the ±{prf / 2:,.0f} Hz span; x = E, E_dedup, or E with hampel_w51_k5 "
                         "positions replaced by linear interpolation of neighbours (drop_outliers)",
                 source="team_meeting/teammeeting_0910/bake_ground2.py contrast_db; bake_outdoor.py drop_outliers",
                 notes="Not a received SNR or a detection gain. Interpolation does not recover the true value at replaced positions."),
        ])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--refresh-stems", action="store_true", help="redo every dry-run instead of using the cache")
    ap.add_argument("--max-cores", type=int, default=4, help="CPU affinity and dry-run parallelism (default 4)")
    a = ap.parse_args()
    if a.max_cores > 0 and hasattr(os, "sched_setaffinity"):
        allowed = sorted(os.sched_getaffinity(0))
        os.sched_setaffinity(0, set(allowed[:max(1, min(a.max_cores, len(allowed)))]))
    t0 = time.time()
    import bake_ground2 as BG                                           # noqa: E402
    import bake_outdoor as BO                                           # noqa: E402
    defaults = json.loads(LEDGER_DEFAULTS.read_text(encoding="utf-8"))["_meta"]

    # 1. lines
    qf = queue_files()
    qlines = {q: queue_lines(p) for q, p in qf.items()}
    all_lines = {ln for rows in qlines.values() for _, ln in rows} | set(VIEW_LINES.values())
    names = name_lines(all_lines, a.refresh_stems, max(1, a.max_cores))
    running = running_workers()
    store = store_index()
    print(f"  store: {sum(len(v) for v in store.values()):,} rt-tagged shards in {len(store):,} cells", flush=True)

    def cells_of(line):
        out = []
        for nm in names.get(line, {}).get("names", []):
            m = SHARD_RE.match(nm)
            if m:
                out.append((m.group("cell"), nm))
        return out

    expected, bought, line_running, nshards_line = {}, {}, {}, {}
    queues, shard_sets, line_sets = [], {}, {}
    for q in sorted(qf):
        rows = qlines[q]
        cells_q, shards_q, bad, run_n = [], set(), 0, 0
        shard_sets[q], line_sets[q] = shards_q, []
        for no, ln in rows:
            cs = cells_of(ln)
            if not cs:
                bad += 1
                continue
            line_sets[q].append({nm for _, nm in cs})
            is_run = norm_line(ln) in running
            run_n += int(is_run)
            toks = shlex.split(ln)
            nsh = int(toks[toks.index("--nshards") + 1]) if "--nshards" in toks else None
            for cell, nm in cs:
                expected.setdefault(cell, set()).add(nm)
                shards_q.add(nm)
                b = bought.setdefault(cell, {})
                b.setdefault(qf[q].name, []).append(no)
                if is_run:
                    line_running.setdefault(cell, []).append(dict(file=qf[q].name, line=no, **running[norm_line(ln)]))
                if nsh:
                    nshards_line[cell] = nsh
                if cell not in cells_q:
                    cells_q.append(cell)
        queues.append(dict(queue=q, file=qf[q].name, primary=q in PRIMARY_QUEUES, n_lines=len(rows), n_bad=bad,
                           n_running=run_n, n_unique_shards=len(shards_q),
                           n_shards_present=sum(1 for nm in shards_q if (SHD / nm).exists()),
                           cells=cells_q, bad_lines=[dict(line=no, why=names.get(ln, {}).get("why"))
                                                     for no, ln in rows if not cells_of(ln)]))
    queue_overlaps = []
    prim = [q for q in sorted(qf) if q in PRIMARY_QUEUES]
    for i, qa in enumerate(prim):
        for qb in prim[i + 1:]:
            n_b = sum(1 for s in line_sets[qb] if s <= shard_sets[qa])
            if n_b:
                queue_overlaps.append(dict(file_a=qf[qa].name, file_b=qf[qb].name, n_lines_b=n_b))
    V = {}
    for k, ln in VIEW_LINES.items():
        cs = cells_of(ln)
        V[k] = cs[0][0] if cs else None
        if not cs:
            print(f"  ⚠view line not named: {k}: {names.get(ln, {}).get('why')}", flush=True)
    wanted = [c for q in queues if q["primary"] for c in q["cells"]]
    wanted += [c for c in V.values() if c and c not in wanted]

    # 2. load cells (wanted + every complete-able rt cell that could serve as a reference is loaded lazily)
    F, cells = {}, {}

    def ensure(cell):
        if cell in cells:
            return cells[cell]
        F[cell] = fields_of(cell, defaults)
        files = store.get(cell, [])
        rec = load_cell(files, expected.get(cell, set()), nshards_line.get(cell))
        rec["bought_by"] = [dict(file=f, lines=sorted(set(v))) for f, v in sorted(bought.get(cell, {}).items())]
        rec["running"] = line_running.get(cell, [])
        rec["cfg_mismatches"] = cfg_checks(F[cell], rec, None) if "grammar" in F[cell] else ["name not parsed"]
        cells[cell] = rec
        return rec

    for c in wanted:
        ensure(c)
    # candidate references: open-sky rt cells at the same elevation tokens, and 0 deg open-sky cells
    els_needed = {F[c]["el_token"] for c in wanted if "grammar" in F[c]}
    for cell in store:
        if cell in cells:
            continue
        arm, el = split_cell(cell)
        if "_env" in arm:
            continue
        if el in els_needed or el == "+0":
            ensure(cell)
    complete = {c for c, r in cells.items() if r.get("complete") and "grammar" in F[c]}
    default_caps = {r["cap_from_shard"][0] for c, r in cells.items()
                    if c in complete and F[c]["cap_from_name"] is None and r.get("cap_from_shard")}
    default_cap = default_caps.pop() if len(default_caps) == 1 else None
    for c in complete:
        cells[c]["cfg_mismatches"] = cfg_checks(F[c], cells[c], default_cap)

    # 3. metrics
    refs_used = set()
    prfs = set()
    for c in sorted(complete):
        rec = cells[c]
        arr = rec.pop("_arrays")
        rec["_arr"] = arr
    s_cache = {}
    for c in sorted(complete):
        rec, arr = cells[c], cells[c]["_arr"]
        prfs.add(rec["prf_hz"])
        zr = zero_ref(c, F, complete)
        if zr is not None and zr not in s_cache:
            s_cache[zr] = one_copy_abs(cells[zr]["_arr"])
        s_one = s_cache.get(zr) if zr else None
        cp = m_copy(arr["E"], arr["Ed"], arr["nd"], s_one)
        cp["copy_k_diff"]["reference"] = zr
        M = dict(isolated_20xmedian=m_isolated(arr["E"]), hampel_w51_k5=m_hampel(arr["E"], BO),
                 contrast=m_contrast(arr["E"], arr["Ed"], BO, BG), copy=cp,
                 env_field_drop_halfmedian=None, env_field_drop_halfmedian_sky_default_cap=None)
        for key, same in (("env_field_drop_halfmedian", True), ("env_field_drop_halfmedian_sky_default_cap", False)):
            ref = sky_ref(c, F, complete, same)
            if ref is None:
                M[key] = None
            elif ref.startswith("ambiguous:"):
                M[key] = dict(n=None, reference=None, note=ref)
            else:
                M[key] = dict(m_envdrop(arr["E"], cells[ref]["_arr"]["E"]), reference=ref,
                              reference_cap_differs=(F[ref]["cap_from_name"] != F[c]["cap_from_name"]))
                refs_used.add(ref)
        if M["env_field_drop_halfmedian"] and M["env_field_drop_halfmedian_sky_default_cap"] and \
                M["env_field_drop_halfmedian"]["reference"] == M["env_field_drop_halfmedian_sky_default_cap"]["reference"]:
            M["env_field_drop_halfmedian_sky_default_cap"] = dict(same_as="env_field_drop_halfmedian",
                                                                  **M["env_field_drop_halfmedian"])
        rec["metrics"] = M
    if zr_used := {cells[c]["metrics"]["copy"]["copy_k_diff"]["reference"] for c in complete} - {None}:
        refs_used |= zr_used
    if len(prfs) != 1 or abs(prfs.copy().pop() - float(BG.PRF)) > 1e-9:
        raise SystemExit(f"⛔ PRF differs between cells or from bake_ground2.PRF: {sorted(prfs)} vs {BG.PRF}")
    n_poses = {cells[c]["n_poses"] for c in complete}
    if len(n_poses) != 1:
        raise SystemExit(f"⛔ cells have different pose counts {sorted(n_poses)}")

    # manifest = wanted cells + references actually used
    manifest = list(dict.fromkeys(wanted + sorted(refs_used)))
    for q in queues:
        q["n_cells"] = len(q["cells"])
        q["n_cells_complete"] = sum(1 for c in q["cells"] if c in cells and cells[c].get("complete"))

    views = dict(a=view_a(cells, V), b=view_b(cells, V), c=view_c(cells, V), d=view_d(cells, V),
                 e_offsets=view_offsets(cells, V), e_zero=view_zero(cells, V))

    # env_path_missing from the existing path-list ledger
    pm = None
    if PATHS_DIFF.exists():
        pd = json.loads(PATHS_DIFF.read_text(encoding="utf-8"))
        rows = []
        for cc in pd["cells"]:
            cell = f"{cc['arm']}_el{cc['el_deg']:+g}"
            per = {}
            for p in cc["pairs"]:
                per.setdefault(int(p["isolated"]), []).append(bool(p["missing"]))
            listed = sorted(per)
            miss_any = [i for i in listed if any(per[i])]
            miss_all = [i for i in listed if all(per[i])]
            rec = cells.get(cell) or (ensure(cell) if cell in store else None)
            drops = None
            if rec and rec.get("complete") and rec.get("metrics", {}).get("env_field_drop_halfmedian"):
                drops = set(rec["metrics"]["env_field_drop_halfmedian"]["indices"])
            rows.append(dict(cell=cell, n_listed=len(listed), listed=listed, n_missing_any=len(miss_any),
                             n_missing_all=len(miss_all), missing_any=miss_any,
                             n_in_drops=None if drops is None else sum(1 for i in listed if i in drops),
                             n_missing_any_in_drops=None if drops is None else sum(1 for i in miss_any if i in drops)))
            if cell not in manifest and cell in cells:
                manifest.append(cell)
        pmeta = json.loads(PATHS_SRC.read_text(encoding="utf-8"))["_meta"] if PATHS_SRC.exists() else {}
        pm = dict(source=str(PATHS_DIFF.relative_to(ROOT)), sha256=sha256_file(PATHS_DIFF),
                  generator=pd["_meta"].get("generator"), cells=rows,
                  paths_generator=pmeta.get("generator"), paths_run_utc=pmeta.get("started_utc"),
                  paths_solver_build=(pmeta.get("versions") or {}).get("solver_build"),
                  paths_n_outliers=(pmeta.get("parameters") or {}).get("n_outliers"),
                  paths_factor=(pmeta.get("parameters") or {}).get("factor"))

    # common scope string, read from the manifest cells
    fs = [F[c] for c in manifest if "grammar" in F[c]]
    common = dict(drone=sorted({f["drone"] for f in fs}), spp=sorted({f["spp"] for f in fs}),
                  switches=sorted({f["switches"] for f in fs}),
                  range_m=sorted({f["grammar"].get("range_m") for f in fs}),
                  build=sorted({b for c in manifest for b in (cells[c].get("solver_build") or [])}))
    n0 = n_poses.copy().pop()
    prf0 = prfs.copy().pop()
    common_scope = (f"PathSolver, drone {'/'.join(common['drone'])} (0953 rows name their drone), range "
                    f"{'/'.join(common['range_m'])} m, rays {'/'.join(f'{int(s):,}' for s in common['spp'])}, switches "
                    f"{'/'.join(common['switches'])} (diffuse on, refraction/diffraction off), {n0:,} positions at "
                    f"{prf0:,.0f} Hz, build {' | '.join(common['build'])}, max_depth 2 unless the row says d1, "
                    f"default cap {n_(default_cap)} (read from shard n_trunc) unless the row gives a cap")

    open_items = [
        "0950: a same-cap 2×2 exists only where section 3(a) shows 'same cap'; elsewhere the interaction is either not "
        "computed or marked CROSS-CAP STITCH (contrast only).",
        "0950/0954: pointing and polarisation-basis rotation are not separated (no polarisation arm).",
        "0952: one run per cap value and one same-seed repeat; the working threshold carries no seed spread. Outcome "
        "(a)/(b)/(c)/(d) of the 0952 header is not named here.",
        "0953: depth 1 reuses the depth-2 working threshold (no depth-1 repeat).",
        "0954: 'under 1 dB' is a pre-set practical threshold, not a repeat-based uncertainty; one run per cell.",
        "0955 A: the 2.0.1 cells of the same scene/angle are not recomputed here.",
        "env_field_drop_halfmedian in view (c) uses an open-sky reference at the default cap for the rungs "
        + (", ".join(r["label"] for r in views["c"]["rows"]
                     if r.get("complete") and r.get("drop_column_used") == "sky at default cap") or "(none)")
        + " (no complete same-cap open-sky cell at el −60 was found in the store scan for them).",
        "env_path_missing covers only the poses listed in outputs/dropout_paths_0916_diff.json; 'without the ground "
        "reflection' for a whole drop set needs path lists for every pose in it.",
        "Nothing here identifies which solver candidate was lost or why.",
    ]

    git_head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    meta = dict(
        generator="benchmark/readout_0917.py",
        command='CUDA_VISIBLE_DEVICES="" MPLBACKEND=Agg nice -n 19 taskset -c 8-15 /workspace/.venvs/py312/bin/python '
                "benchmark/readout_0917.py" + ("" if len(sys.argv) < 2 else " " + " ".join(sys.argv[1:])),
        git_head=git_head, script_sha256=sha256_file(Path(__file__)), created_utc=utc(time.time()),
        inputs=dict(elevation_sweep_md_sha256=sha256_file(SWEEP), sionna_rt=solver_rt_version(),
                    bake_outdoor_sha256=sha256_file(Path(BO.__file__)), bake_ground2_sha256=sha256_file(Path(BG.__file__)),
                    stems_cache="outputs/readout_0917_stems.json"),
        n_cells_manifest=len(manifest), n_cells_complete=sum(1 for c in manifest if cells[c].get("complete")),
        n_workers_running=len(running), runtime_s=None,
        scope="Stored PathSolver shards only; simulation bookkeeping, no RF measurement, no statement about why a path "
              "is missing.")
    D = definitions(n0, prf0, BG, BO)

    def clean(rec):
        return {k: v for k, v in rec.items() if not k.startswith("_")}
    doc = dict(_meta=meta, definitions=D, queues=queues, scan_queue_files=[qf[q].name for q in sorted(qf)],
               queue_overlaps=queue_overlaps, default_cap=default_cap,
               view_cells=V, manifest_order=manifest, fields={c: F[c] for c in manifest}, common_scope=common_scope,
               cells={c: clean(cells[c]) for c in manifest}, views=views, env_path_missing=pm, open_items=open_items)
    text = md(dict(doc, _cells_live=cells, fields=F))
    meta["runtime_s"] = round(time.time() - t0, 1)
    for p, payload in ((OUT_JSON, json.dumps(doc, indent=1, default=_json_default) + "\n"), (OUT_MD, text + "\n")):
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_text(payload, encoding="utf-8")
        os.replace(tmp, p)
    print(f"wrote {OUT_JSON.relative_to(ROOT)} and {OUT_MD.relative_to(ROOT)} "
          f"({meta['n_cells_complete']}/{meta['n_cells_manifest']} cells complete, {meta['runtime_s']} s)")
    return 0


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, set):
        return sorted(o)
    raise TypeError(type(o))


if __name__ == "__main__":
    raise SystemExit(main())
