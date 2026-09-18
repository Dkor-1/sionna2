#!/usr/bin/env python3
"""readout_0918.py - status ledger and pre-set readings for queues 0957-0963 (the queues benchmark/readout_0917.py
stops short of), plus the 0958 HOLD file.

CPU only; it never starts a ray trace and never writes a shard. benchmark/readout_0917.py is imported for the parts
that are already written (dry-run naming, shard loading, the metrics of docs/READOUT_0917.md section 1) and is never
edited; everything this file adds is defined here.

1. Manifest, per queue file runners/jobs_0957..0963. Every line - queued, «#HOLD », «#HOLD-rev1 » - is named by
   benchmark/elevation_sweep_md.py itself (`--dry-run`, cached in outputs/readout_0918_stems.json, redone when that
   script or the installed sionna-rt changes). Per cell: shards expected and present, completeness (every pose index
   exactly once, E and E_dedup finite), solver_build, the fields read back from the name (src/arm_grammar.py), shard
   mtimes, path-list sidecar coverage (outputs/path_provenance/<stem>_prov.npz: files, positions, median paths), and
   whether a worker for one of its lines is running now (ps).
2. Quantities. The names of docs/READOUT_0917.md section 1 keep their definitions and come from readout_0917
   (isolated_20xmedian, hampel_w51_k5, copy_k_ratio / copy_k_diff, contrast_raw / contrast_dedup / contrast_interp,
   env_field_drop_halfmedian). The names the 0957-0963 headers define are implemented here, each in one place:
   lvl_db, ac_level_db, ac_to_static_db, hits_per_pose, path_class, class_power_db, E_B, contrast_gated,
   env_in_bin_db, event positions, event_in_bin, event_share, thickness_delta, seed_diff, D2, excess_cm, w_err,
   fade_env_db, lvl_at_15m_db, interp_resid_db, above_nyq_share, rerun_floor_db, seed_floor_db, replay_diff_db.
3. Gates, applied literally as the headers write them, with their own wording («threshold not crossed», never «no
   effect»): 0957 check 0 / 1 / 2 / P / A / B / C, 0959 (b), 0960 G0 / T1 / T2, 0961 R0 / R1 / R2 / R3 / T1 / T2,
   0962 P1 / P2 / P2d / M2 / M3 / P3 / W / AS / P6 / F, 0963 S1. A gate whose inputs have not landed is written as
   «not computable yet» with the cells it waits for; a gate is never written from a partial series.

Simulation bookkeeping only: no RF measurement is involved, nothing is compared with real hardware, and nothing here
says why the solver lists or omits a path.

    cd /workspace/sionna
    CUDA_VISIBLE_DEVICES="" MPLBACKEND=Agg nice -n 19 taskset -c 8-15 /workspace/.venvs/py312/bin/python benchmark/readout_0918.py

Options: --refresh-stems (redo every dry-run), --max-cores N (CPU affinity and dry-run parallelism, default 4),
--no-paths (skip the path-list layer). Writes outputs/readout_0918.json, outputs/readout_0918_stems.json (dry-run
name cache) and docs/READOUT_0918.md. Re-running later picks up cells that have finished since.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (str(ROOT / "src"), str(ROOT / "benchmark")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

import numpy as np                                                      # noqa: E402

import readout_0917 as R7                                               # noqa: E402
from readout_0917 import (SHARD_RE, db20, dry_run, fields_of, hist, jaccard, load_cell,   # noqa: E402
                          m_contrast, m_copy, m_envdrop, m_hampel, m_isolated, modal, norm_line,
                          running_workers, sha256_file, solver_rt_version, split_cell, store_index, utc)

SHD = ROOT / "outputs" / "elev_sweep_shards"
PRV = ROOT / "outputs" / "path_provenance"
SWEEP = ROOT / "benchmark" / "elevation_sweep_md.py"
RUNNERS = ROOT / "runners"
OUT_JSON = ROOT / "outputs" / "readout_0918.json"
OUT_STEMS = ROOT / "outputs" / "readout_0918_stems.json"
OUT_MD = ROOT / "docs" / "READOUT_0918.md"
LEDGER_DEFAULTS = ROOT / "outputs" / "report07_three_engines.json"

QUEUES = (957, 958, 959, 960, 961, 962, 963)
QUEUE_RE = re.compile(r"^jobs_(\d{4})(?:_.*)?\.txt$")
HOLD_RE = re.compile(r"^#\s*(HOLD(?:-rev1)?)\s+(--.*)$")

FC = 3.5e9                         # carrier of every cell here (3.5 GHz working assumption, AGENTS.md 2026-09-18)
C0 = 299792458.0
B_LIST = (20e6, 100e6, 200e6)      # runners/jobs_0957 header: B = 20, 100, 200 MHz
WINDOWS = ("hann", "rect")         # Hann is the reading, rectangular is the knob
EVENT_RATIO = 3.0                  # event_share: share of event positions whose ratio exceeds 3
REL_REPLAY = 1e-5                  # 0957 reading 1: positions with |dE| / median|E| above this

# ─ computed inputs the headers fix before any shard is read (their own numbers, copied, not recomputed here) ─
P2_COMPUTED = {"A": -9.61, "B": -6.98, "C": -16.28, "E": -16.59, "F": -6.80}          # jobs_0962 table, dB
RPRIME_MINUS_R_CM = {"A": 40.7, "B": 28.0, "C": 66.4, "E": 55.3, "F": 33.6}           # jobs_0962 table, cm
P3_COMPUTED = {"A": -18.99, "B": -13.97}                                              # jobs_0962 table, dB
W_GAIN_DB = {"d": 16.00, "gd": 15.31, "dg": 15.31, "g": -44.00}                       # jobs_0962 w_err
NADIR_A_DB = {15: -105.3, 30: -104.9}                                                 # jobs_0957 P, aimed tr38901
ROT201 = dict(el30_total=-12.94, el30_ac_over_total=-0.08, el60_total=-16.50, el60_ac_over_total=+5.74)


# ═══ 0. queue lines (queued and held) ═══════════════════════════════════════════════════════════════════
def queue_files() -> dict:
    out = {}
    for p in sorted(RUNNERS.iterdir()):
        m = QUEUE_RE.match(p.name)
        if m and int(m.group(1)) in QUEUES:
            out[int(m.group(1))] = p
    return out


def queue_rows(p: Path) -> list:
    """(job-line index, file line number, job line, hold tag or None). The headers number their own job lines
    («job lines 1-2», «lines 74-163»), counting «#HOLD » lines as job lines, so that index is what the gates use;
    readout_0917.queue_lines drops every comment and would lose the held lines."""
    rows, k = [], 0
    for no, raw in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        s = raw.strip()
        if not s:
            continue
        if s.startswith("#"):
            m = HOLD_RE.match(s)
            if m:
                k += 1
                rows.append((k, no, m.group(2).strip(), m.group(1)))
            continue
        k += 1
        rows.append((k, no, s, None))
    return rows


def name_lines(lines, refresh: bool, jobs: int) -> dict:
    key = dict(sweep_sha256=sha256_file(SWEEP), sionna_rt=solver_rt_version())
    cache = {}
    if OUT_STEMS.exists() and not refresh:
        try:
            old = json.loads(OUT_STEMS.read_text(encoding="utf-8"))
            if all(old.get("_meta", {}).get(k) == v for k, v in key.items()):
                cache = old.get("stems", {})
        except (json.JSONDecodeError, OSError):
            cache = {}
    todo = sorted(ln for ln in lines if ln not in cache or not cache[ln].get("names"))
    if todo:
        print(f"  dry-run naming {len(todo)} lines on {jobs} workers", flush=True)
        t0 = time.time()
        with cf.ThreadPoolExecutor(max_workers=jobs) as ex:
            for ln, res in zip(todo, ex.map(dry_run, todo)):
                cache[ln] = res
        print(f"  dry-runs done in {time.time() - t0:.0f} s", flush=True)
    meta = dict(generator="benchmark/readout_0918.py", role="dry-run name cache for outputs/readout_0918.json",
                created_utc=utc(time.time()), **key)
    tmp = OUT_STEMS.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(dict(_meta=meta, stems={k: cache[k] for k in sorted(cache)}), indent=1) + "\n",
                   encoding="utf-8")
    os.replace(tmp, OUT_STEMS)
    return cache


# ═══ 1. quantities the 0957-0963 headers define ═════════════════════════════════════════════════════════
def lvl_db(E) -> float | None:
    """runners/jobs_0960: 20*log10|mean_t E| over the record (the static level)."""
    return db20(abs(complex(np.mean(E))))


def ac_level_db(E) -> float | None:
    """runners/jobs_0960: 10*log10(mean_t |E - mean_t E|^2)."""
    v = float(np.mean(np.abs(E - np.mean(E)) ** 2))
    return None if not v > 0 else float(10.0 * np.log10(v))


def ac_to_static_db(E) -> float | None:
    a, l = ac_level_db(E), lvl_db(E)
    return None if a is None or l is None else a - l


def h_window(x, window: str):
    """Range-bin response at offset x = B*(tau - 2R/c) cells. Hann over bandwidth B, rectangular as the knob;
    h(0) = 1 in both."""
    if window == "rect":
        return np.sinc(x)
    return np.sinc(x) + 0.5 * (np.sinc(x - 1.0) + np.sinc(x + 1.0))


CLASSES = ("d", "gd", "dg", "gdg", "g")


def path_class(part: np.ndarray, part_names) -> np.ndarray:
    """runners/jobs_0960 path_class: the ordered interaction sequence with consecutive drone-part hits written once.
    g = any env_* object, d = any drone part; -1 in the sidecar is «no interaction» at that depth."""
    kind = np.array([2 if str(n).startswith("env_") else 1 for n in part_names], np.int64)
    D, N = part.shape
    code = np.zeros(N, np.int64)
    for k in range(D):
        v = part[k]
        code += np.where(v >= 0, kind[np.clip(v, 0, kind.size - 1)], 0) * (3 ** k)
    lut = {}
    for c in np.unique(code):
        seq = []
        for k in range(D):
            d = (int(c) // 3 ** k) % 3
            if d:
                ch = "d" if d == 1 else "g"
                if not seq or seq[-1] != ch:
                    seq.append(ch)
        lut[int(c)] = "".join(seq)
    keys = np.array(sorted(lut))
    vals = np.array([lut[int(k)] for k in keys], dtype="<U10")
    return vals[np.searchsorted(keys, code)]



def group_median(gid: np.ndarray, x: np.ndarray, n_groups: int) -> np.ndarray:
    """Median of x within each group id 0..n_groups-1; NaN where a group is empty."""
    out = np.full(n_groups, np.nan)
    if gid.size == 0:
        return out
    o = np.lexsort((x, gid))
    g, v = gid[o], x[o]
    lo = np.searchsorted(g, np.arange(n_groups), side="left")
    hi = np.searchsorted(g, np.arange(n_groups), side="right")
    ok = hi > lo
    if not ok.any():
        return out
    a = (lo[ok] + hi[ok] - 1) // 2
    b = (lo[ok] + hi[ok]) // 2
    out[ok] = 0.5 * (v[a] + v[b])
    return out


def gated_cell(files, range_m: float, window: str) -> dict | None:
    """Per-position gated sums E_B by path class, from the path-list sidecars of one cell.
    E_B(t) = sum over listed paths with any interaction of a*exp(-j2pi fc tau)*h_B(B*(tau - 2R/c))."""
    sc = [PRV / (nm[:-4] + "_prov.npz") for nm in files]
    if not all(p.exists() for p in sc):
        return None
    tau0 = 2.0 * range_m / C0
    poses, cols, cls_count, tau_med, names_seen = [], {}, {}, {}, None
    n_unknown = 0
    for p in sc:
        with np.load(p, allow_pickle=False) as z:
            names = [str(s) for s in z["part_names"]]
            names_seen = names if names_seen is None else names_seen
            n_unknown += int(np.asarray(z["n_unknown_id"]).ravel()[0])
            npp = z["n_paths"].astype(np.int64)
            pid = np.repeat(np.arange(npp.size), npp)
            cls = path_class(z["part"], names)
            tau = z["tau"]
            ph = z["a"].astype(np.complex128) * np.exp(-1j * 2 * np.pi * FC * tau)
            hit = cls != ""
            drone = np.char.find(cls, "d") >= 0
            envonly = hit & ~drone
            base = len(poses)
            poses.extend(int(v) for v in z["pose"])
            for key, sel in (("hit", hit), ("drone", drone)):
                cols.setdefault("n_" + key, []).append(np.bincount(pid[sel], minlength=npp.size))
            for c in CLASSES:
                m = cls == c
                cls_count.setdefault(c, []).append(np.bincount(pid[m], minlength=npp.size))
                tau_med.setdefault(c, []).append(group_median(pid[m], tau[m], npp.size))
            for B in B_LIST:
                w = h_window(B * (tau - tau0), window)
                g = ph * w
                tag = f"B{int(B / 1e6)}"
                for c in CLASSES:
                    m = cls == c
                    cols.setdefault(f"{tag}_{c}", []).append(
                        np.bincount(pid[m], weights=g[m].real, minlength=npp.size)
                        + 1j * np.bincount(pid[m], weights=g[m].imag, minlength=npp.size))
                for key, sel in (("drone", drone), ("envonly", envonly), ("all", hit)):
                    cols.setdefault(f"{tag}_{key}", []).append(
                        np.bincount(pid[sel], weights=g[sel].real, minlength=npp.size)
                        + 1j * np.bincount(pid[sel], weights=g[sel].imag, minlength=npp.size))
            cols.setdefault("_E_all", []).append(
                np.bincount(pid[hit], weights=ph[hit].real, minlength=npp.size)
                + 1j * np.bincount(pid[hit], weights=ph[hit].imag, minlength=npp.size))
            del base
    P = np.asarray(poses)
    o = np.argsort(P)
    out = {k: np.concatenate(v)[o] for k, v in cols.items()}
    out["pose"] = P[o]
    out["n_class"] = {c: np.concatenate(v)[o] for c, v in cls_count.items()}
    out["ctau_class"] = {c: np.concatenate(v)[o] * C0 for c, v in tau_med.items()}
    out["part_names"] = names_seen
    out["n_unknown_id"] = n_unknown
    out["window"] = window
    out["range_m"] = range_m
    return out


def class_power_db(G, c: str, B: float) -> float | None:
    """runners/jobs_0960: 10*log10(mean_t |E_B over the paths of path_class c|^2)."""
    v = G[f"B{int(B / 1e6)}_{c}"]
    p = float(np.mean(np.abs(v) ** 2))
    return None if not p > 0 else float(10.0 * np.log10(p))


def env_in_bin_db(G, B: float) -> float | None:
    """runners/jobs_0957: 10*log10( mean_t|E_B env-only|^2 / mean_t|E_B drone - its time mean|^2 )."""
    tag = f"B{int(B / 1e6)}"
    num = float(np.mean(np.abs(G[f"{tag}_envonly"]) ** 2))
    d = G[f"{tag}_drone"]
    den = float(np.mean(np.abs(d - np.mean(d)) ** 2))
    return None if not (num > 0 and den > 0) else float(10.0 * np.log10(num / den))


def event_readings(G, events: np.ndarray, B: float) -> dict:
    """runners/jobs_0957 event_in_bin / event_share on E_B over all listed paths."""
    E = G[f"B{int(B / 1e6)}_all"]
    r = np.full(E.size, np.nan)
    r[1:-1] = np.abs(E[1:-1] - 0.5 * (E[:-2] + E[2:]))
    fin = np.isfinite(r)
    med_all = float(np.median(r[fin]))
    ev = np.array([i for i in events if 0 < i < E.size - 1], np.int64)
    if ev.size == 0 or not med_all > 0:
        return dict(defined=False, n_events=int(events.size), median_all=med_all)
    ratio = r[ev] / med_all
    return dict(defined=True, n_events=int(events.size), n_events_used=int(ev.size), median_all=med_all,
                event_in_bin=float(np.median(ratio)),
                event_share=float(np.mean(ratio > EVENT_RATIO)))


def sinc_offsets(G, B: float, window: str) -> list:
    """For every environment-only path class present: its offset x = B*(tau - 2R/c) and |h_B(x)|."""
    rows = []
    for c in ("g", "gdg"):
        n = G["n_class"][c]
        if not n.any():
            continue
        ct = G["ctau_class"][c]
        ok = np.isfinite(ct)
        if not ok.any():
            continue
        x = float(np.median(B * (ct[ok] / C0 - 2.0 * G["range_m"] / C0)))
        rows.append(dict(path_class=f"[{','.join(c)}]", median_paths_per_position=float(np.median(n)),
                         offset_cells=x, h_abs_db=db20(abs(float(h_window(np.array([x]), window)[0]))),
                         median_ctau_m=float(np.median(ct[ok]))))
    return rows


def fade_env_db(G, B: float) -> dict:
    """runners/jobs_0962 fade_env_db, computed from listed classes, never read as a measured fade."""
    tag = f"B{int(B / 1e6)}"
    md = complex(np.mean(G[f"{tag}_d"]))
    mg = complex(np.mean(G[f"{tag}_gd"])) + complex(np.mean(G[f"{tag}_dg"]))
    if not abs(md) > 0:
        return dict(defined=False)
    r = abs(mg) / (2.0 * abs(md))
    d2 = [db20(abs(1 + 2 * r)), db20(abs(1 - 2 * r))]
    d3 = [db20(abs((1 + r) ** 2)), db20(abs((1 - r) ** 2))]
    return dict(defined=True, r=r, depth2_max_min_db=d2, depth3_max_min_db=d3)


# ═══ 2. cell store ══════════════════════════════════════════════════════════════════════════════════════
def sidecar_rec(cell: str, files: list, idx_expected: int | None, dump_paths: int | None = None) -> dict:
    """Path-list coverage of one cell. A line without --dump-paths asks for no sidecar, so its expected count is 0
    and the ledger does not show it as a gap."""
    exp = [nm[:-4] + "_prov.npz" for nm in files] if dump_paths else []
    have = [n for n in exp if (PRV / n).exists()]
    rec = dict(requested=bool(dump_paths), dump_paths=dump_paths, expected=len(exp), present=len(have), files=have,
               bytes=sum((PRV / n).stat().st_size for n in have))
    if not have:
        return rec
    pos, npth, unk = [], [], 0
    for n in have:
        with np.load(PRV / n, allow_pickle=False) as z:
            pos.append(z["pose"].astype(np.int64))
            npth.append(z["n_paths"].astype(np.int64))
            unk += int(np.asarray(z["n_unknown_id"]).ravel()[0])
    p = np.concatenate(pos)
    rec.update(n_positions=int(p.size), n_unique_positions=int(np.unique(p).size),
               position_min=int(p.min()), position_max=int(p.max()),
               covers_record=bool(idx_expected is not None and np.array_equal(np.unique(p), np.arange(idx_expected))),
               median_paths_per_position=int(np.median(np.concatenate(npth))), n_unknown_id=unk)
    return rec


class Cells:
    """Loads a cell once: shards through readout_0917.load_cell, sidecars through gated_cell."""

    def __init__(self, store, expected, nshards_line, defaults, use_paths=True, dump_of=None):
        self.store, self.expected, self.nshards_line = store, expected, nshards_line
        self.defaults, self.use_paths, self.dump_of = defaults, use_paths, dump_of or {}
        self.rec, self.F, self._g = {}, {}, {}

    def get(self, cell):
        if cell in self.rec:
            return self.rec[cell]
        self.F[cell] = fields_of(cell, self.defaults)
        files = self.store.get(cell, [])
        r = load_cell(files, self.expected.get(cell, set()), self.nshards_line.get(cell))
        r["sidecars"] = sidecar_rec(cell, [p.name for p in files], r.get("n_poses"), self.dump_of.get(cell))
        if r.get("complete"):
            arr = r.pop("_arrays")
            r["_arr"] = arr
            E = arr["E"]
            r["lvl_db"] = lvl_db(E)
            r["ac_level_db"] = ac_level_db(E)
            r["ac_to_static_db"] = ac_to_static_db(E)
            r["hits_per_pose"] = int(np.median(arr["npaths"])) if "npaths" in arr else None
        self.rec[cell] = r
        return r

    def arr(self, cell):
        r = self.get(cell)
        return r.get("_arr")

    def gated(self, cell, window="hann"):
        if not self.use_paths:
            return None
        key = (cell, window)
        if key in self._g:
            return self._g[key]
        r = self.get(cell)
        g = None
        if r.get("complete"):
            files = [p.name for p in self.store.get(cell, [])]
            rng = self.F[cell]["grammar"].get("range_m") if "grammar" in self.F[cell] else None
            try:
                rng = float(rng)
            except (TypeError, ValueError):
                rng = None
            if rng is not None:
                t0 = time.time()
                g = gated_cell(files, rng, window)
                if g is not None:
                    print(f"    paths {cell[:70]} [{window}] {time.time() - t0:.0f} s", flush=True)
        self._g[key] = g
        return g

    def complete(self, cell):
        return bool(self.store.get(cell)) and bool(self.get(cell).get("complete"))


def metrics_of(C: Cells, cell: str, sky: str | None, BO, BG, with_contrast=True) -> dict:
    """The docs/READOUT_0917.md section 1 metrics, plus the level names of runners/jobs_0960."""
    a = C.arr(cell)
    if a is None:
        return {}
    M = dict(isolated_20xmedian=m_isolated(a["E"]), hampel_w51_k5=m_hampel(a["E"], BO),
             copy=m_copy(a["E"], a["Ed"], a["nd"], None),
             lvl_db=C.get(cell)["lvl_db"], ac_level_db=C.get(cell)["ac_level_db"],
             ac_to_static_db=C.get(cell)["ac_to_static_db"], hits_per_pose=C.get(cell)["hits_per_pose"])
    if with_contrast:
        M["contrast"] = m_contrast(a["E"], a["Ed"], BO, BG)
    if sky and C.complete(sky):
        b = C.arr(sky)
        if b["E"].size == a["E"].size:
            M["env_field_drop_halfmedian"] = dict(m_envdrop(a["E"], b["E"]), reference=sky)
            D = a["E"] - b["E"]
            M["median_abs_scene_minus_sky_db"] = db20(float(np.median(np.abs(D))))
            M["median_abs_D_minus_meanD_db"] = db20(float(np.median(np.abs(D - D.mean()))))
    return M


def events_of(M: dict) -> np.ndarray:
    """runners/jobs_0957: event positions = env_field_drop_halfmedian union isolated_20xmedian."""
    a = set(M.get("isolated_20xmedian", {}).get("indices", []) or [])
    d = M.get("env_field_drop_halfmedian")
    if d:
        a |= set(d.get("indices", []) or [])
    return np.array(sorted(a), np.int64)


def thr_word(value, thr, crossed_text, not_crossed_text):
    """Every header: below a threshold write «threshold not crossed», never «no effect» or «equivalent»."""
    if value is None or thr is None:
        return None
    return crossed_text if abs(value) >= thr else not_crossed_text


# ═══ 3. gates, one function per queue ═══════════════════════════════════════════════════════════════════
FLOOR_DB, FLOOR_COUNT = 1.0, 5      # runners/jobs_0960 T1 floors


def _d(a, b):
    return None if a is None or b is None else float(a - b)


def _pair_levels(C, cell, ref, BO, BG, sky=None, sky_ref_cell=None):
    """thickness_delta / difference of the E-only level names between two complete cells."""
    if not (C.complete(cell) and C.complete(ref)):
        return None
    M1 = metrics_of(C, cell, sky, BO, BG)
    M0 = metrics_of(C, ref, sky_ref_cell, BO, BG)
    out = dict(cell=cell, ref=ref)
    for q in ("lvl_db", "ac_level_db", "ac_to_static_db"):
        out[q] = dict(cell=M1[q], ref=M0[q], delta=_d(M1[q], M0[q]))
    out["contrast_raw"] = dict(cell=M1["contrast"]["contrast_raw"], ref=M0["contrast"]["contrast_raw"],
                               delta=_d(M1["contrast"]["contrast_raw"], M0["contrast"]["contrast_raw"]))
    out["isolated_20xmedian"] = dict(cell=M1["isolated_20xmedian"]["n"], ref=M0["isolated_20xmedian"]["n"],
                                     delta=M1["isolated_20xmedian"]["n"] - M0["isolated_20xmedian"]["n"])
    out["hits_per_pose"] = dict(cell=M1["hits_per_pose"], ref=M0["hits_per_pose"],
                                rel_change=None if not M0["hits_per_pose"] else
                                abs(M1["hits_per_pose"] - M0["hits_per_pose"]) / M0["hits_per_pose"])
    for k, M in (("cell", M1), ("ref", M0)):
        if "env_field_drop_halfmedian" in M:
            out.setdefault("env_field_drop_halfmedian", {})[k] = M["env_field_drop_halfmedian"]["n"]
    if "env_field_drop_halfmedian" in out and len(out["env_field_drop_halfmedian"]) == 2:
        out["env_field_drop_halfmedian"]["delta"] = (out["env_field_drop_halfmedian"]["cell"]
                                                     - out["env_field_drop_halfmedian"]["ref"])
    out["_M"] = dict(cell=M1, ref=M0)
    return out


def _gated_pair(C, cell, ref, window="hann"):
    """contrast_gated, env_in_bin_db and class powers of a cell and its partner, per B."""
    Gc, Gr = C.gated(cell, window), C.gated(ref, window)
    if Gc is None or Gr is None:
        return None
    from readout_0917 import m_contrast as _mc                                 # noqa: F401  (contrast_db via BG)
    return dict(cell=Gc, ref=Gr)


def gate_0960(C, Q, BO, BG) -> dict:
    """runners/jobs_0960 G0 (thickness flags changed the cell) and T1 (does the slab move receiver-facing
    quantities). Pairs: 0960 lines 1-2/3-4/5-6/7-8 against runners/jobs_0957 lines 1-2/9-10/3-4/7-8."""
    pair_def = [("15 m open sky", 1, 957, 1), ("15 m ground alt 5.4", 3, 957, 9),
                ("30 m open sky", 5, 957, 3), ("30 m ground alt 9.26", 7, 957, 7)]
    sky_for = {3: 1, 7: 5}                     # scene - sky only within one thickness (0960 header)
    sky_ref_for = {9: 1, 7: 3}                 # the 0.1 m partners' own open sky (0957 line numbers)
    out = dict(pairs=[], seed_diff={}, G0=None, T1=None, T2=None)
    seed = None
    c_seed, c_base = Q.cell(960, 9), Q.cell(960, 1)
    if c_seed and c_base and C.complete(c_seed) and C.complete(c_base):
        Ms, Mb = metrics_of(C, c_seed, None, BO, BG), metrics_of(C, c_base, None, BO, BG)
        seed = {q: abs(_d(Ms[q], Mb[q])) for q in ("lvl_db", "ac_level_db", "ac_to_static_db")}
        seed["contrast_raw"] = abs(_d(Ms["contrast"]["contrast_raw"], Mb["contrast"]["contrast_raw"]))
        seed["isolated_20xmedian"] = abs(Ms["isolated_20xmedian"]["n"] - Mb["isolated_20xmedian"]["n"])
        out["seed_diff"] = dict(cells=[c_seed, c_base], values=seed)
    for label, ln, qref, lnref in pair_def:
        cell, ref = Q.cell(960, ln), Q.cell(qref, lnref)
        sky = Q.cell(960, sky_for[ln]) if ln in sky_for else None
        skyr = Q.cell(957, sky_ref_for[lnref]) if lnref in sky_ref_for else None
        r = _pair_levels(C, cell, ref, BO, BG, sky, skyr)
        if r is None:
            out["pairs"].append(dict(label=label, cell=cell, ref=ref, complete=False,
                                     cell_complete=bool(cell and C.complete(cell)),
                                     ref_complete=bool(ref and C.complete(ref))))
            continue
        r["label"] = label
        r["thresholds"] = {}
        for q in ("lvl_db", "ac_level_db", "ac_to_static_db", "contrast_raw"):
            s = (seed or {}).get(q)
            r["thresholds"][q] = max(FLOOR_DB, 3 * s) if s is not None else FLOOR_DB
        r["thresholds"]["isolated_20xmedian"] = max(FLOOR_COUNT, 3 * (seed or {}).get("isolated_20xmedian", 0))
        # path-list quantities, only against the 0957 partner (both carry sidecars)
        g = {}
        for window in WINDOWS:
            Gc, Gr = C.gated(cell, window), C.gated(ref, window)
            if Gc is None or Gr is None:
                continue
            ev_c = events_of(r["_M"]["cell"]), events_of(r["_M"]["ref"])
            w = {}
            for B in (20e6, 100e6):
                tag = f"{int(B / 1e6)} MHz"
                row = dict(contrast_gated=dict(
                    cell=float(BG.contrast_db(Gc[f"B{int(B / 1e6)}_all"])),
                    ref=float(BG.contrast_db(Gr[f"B{int(B / 1e6)}_all"]))))
                row["contrast_gated"]["delta"] = _d(row["contrast_gated"]["cell"], row["contrast_gated"]["ref"])
                for key, fn in (("env_in_bin_db", env_in_bin_db),):
                    a, b = fn(Gc, B), fn(Gr, B)
                    row[key] = dict(cell=a, ref=b, delta=_d(a, b))
                row["class_power_db"] = {}
                for c in CLASSES:
                    a, b = class_power_db(Gc, c, B), class_power_db(Gr, c, B)
                    if a is None and b is None:
                        continue
                    row["class_power_db"][f"[{','.join(c)}]"] = dict(cell=a, ref=b, delta=_d(a, b))
                e1 = event_readings(Gc, ev_c[0], B)
                e0 = event_readings(Gr, ev_c[1], B)
                row["events"] = dict(cell=e1, ref=e0)
                w[tag] = row
            g[window] = w
        r["gated"] = g
        r.pop("_M")
        out["pairs"].append(r)
    # G0
    p0 = next((p for p in out["pairs"] if p.get("label") == "15 m open sky" and p.get("lvl_db")), None)
    if p0:
        dl, da = p0["lvl_db"]["delta"], p0["ac_level_db"]["delta"]
        failed = abs(dl) < 0.5 and abs(da) < 1.0
        out["G0"] = dict(delta_lvl_db=dl, delta_ac_level_db=da,
                         hits_per_pose=p0["hits_per_pose"],
                         hits_within_3pct=bool(p0["hits_per_pose"]["rel_change"] is not None
                                               and p0["hits_per_pose"]["rel_change"] <= 0.03),
                         passed=not failed,
                         verdict=("the thickness flags did not change the cell - remove every unlaunched line of "
                                  "0960-0963 and diagnose on CPU" if failed else
                                  "the thickness flags changed the cell (G0 passed); 0961-0963 may read"))
    # T1 verdict
    if all(p.get("lvl_db") for p in out["pairs"]):
        sky_pairs = [p for p in out["pairs"] if "open sky" in p["label"]]
        gnd_pairs = [p for p in out["pairs"] if "ground" in p["label"]]
        hits, why = [], []
        for p in sky_pairs:
            T = p["thresholds"]["ac_to_static_db"]
            d = p["ac_to_static_db"]["delta"]
            if d is not None and abs(d) >= max(3.0, T):
                hits.append(p["label"]); why.append(f"ac_to_static_db {d:+.2f} dB >= max(3, {T:.2f})")
        for p in gnd_pairs:
            for window, w in (p.get("gated") or {}).items():
                if window != "hann":
                    continue
                for tag, row in w.items():
                    d = row["env_in_bin_db"]["delta"]
                    if d is not None and abs(d) >= 3.0:
                        hits.append(f"{p['label']} @ {tag}")
                        why.append(f"env_in_bin_db {d:+.2f} dB at {tag}")
        out["T1"] = dict(crossed=bool(hits), where=hits, why=why,
                         verdict=("the drone slab thickness changes receiver-facing quantities at this geometry "
                                  "(threshold crossed)" if hits else
                                  "threshold not crossed at this geometry"))
    # T2: ghost class ratio at the canonical slab beside the computed -32.4 / -26.8 dB
    t2 = []
    for label, ln, computed in (("15 m ground alt 5.4", 3, -32.4), ("30 m ground alt 9.26", 7, -26.8)):
        cell = Q.cell(960, ln)
        G = C.gated(cell, "hann") if cell else None
        if G is None:
            t2.append(dict(label=label, cell=cell, computed_db=computed, measured=None))
            continue
        gd, d = class_power_db(G, "gd", 20e6), class_power_db(G, "d", 20e6)
        dg = class_power_db(G, "dg", 20e6)
        t2.append(dict(label=label, cell=cell, computed_db=computed,
                       class_gd_minus_d_db=_d(gd, d), class_dg_minus_d_db=_d(dg, d),
                       n_paths_per_position={c: float(np.median(G["n_class"][c])) for c in CLASSES}))
    out["T2_ghost"] = t2
    out["expectation_2_0_1"] = ROT201
    return out


def gate_0961(C, Q, BO, BG) -> dict:
    """runners/jobs_0961 R0/R1/R2/R3 (range and ray density) and T1/T2 (symbol-rate record vs interpolation)."""
    # (A) cells: (label, queue, first line, spp, range)
    A = [("15 m @ 4e9", 960, 1, 4.0e9, 15.0), ("15 m @ 1e9", 961, 1, 1.0e9, 15.0),
         ("15 m @ 2.5e8", 961, 3, 2.5e8, 15.0), ("15 m @ 9e7", 961, 11, 9.0e7, 15.0),
         ("30 m @ 4e9", 960, 5, 4.0e9, 30.0), ("30 m @ 1e9", 961, 5, 1.0e9, 30.0),
         ("60 m @ 4e9", 961, 7, 4.0e9, 60.0), ("100 m @ 4e9", 961, 13, 4.0e9, 100.0)]
    rows = []
    for label, q, ln, spp, R in A:
        cell = Q.cell(q, ln)
        r = dict(label=label, cell=cell, spp=spp, range_m=R,
                 complete=bool(cell and C.complete(cell)))
        if r["complete"]:
            M = metrics_of(C, cell, None, BO, BG)
            r.update(hits_per_pose=M["hits_per_pose"], lvl_db=M["lvl_db"], ac_level_db=M["ac_level_db"],
                     ac_to_static_db=M["ac_to_static_db"], contrast_raw=M["contrast"]["contrast_raw"],
                     isolated_20xmedian=M["isolated_20xmedian"]["n"],
                     lvl_at_15m_db=None if M["lvl_db"] is None else M["lvl_db"] + 40.0 * np.log10(R / 15.0),
                     hits_over_spp_over_R2=None if not M["hits_per_pose"] else
                     M["hits_per_pose"] / (spp / R ** 2))
        rows.append(r)
    done = [r for r in rows if r.get("hits_over_spp_over_R2")]
    R0 = dict(n_cells=len(done), listed=[r["label"] for r in rows if not r["complete"]])
    if done:
        med = float(np.median([r["hits_over_spp_over_R2"] for r in done]))
        R0.update(median=med, per_cell={r["label"]: r["hits_over_spp_over_R2"] / med - 1.0 for r in done},
                  outside_10pct=[r["label"] for r in done if abs(r["hits_over_spp_over_R2"] / med - 1.0) > 0.10])
        R0["passed"] = not R0["outside_10pct"] and len(done) == len(rows)
        R0["verdict"] = ("R0 premise holds for the cells that have landed" if not R0["outside_10pct"]
                         else "R0 premise fails - no range reading is written; cells listed")
    by = {r["label"]: r for r in rows}
    # seed differences
    seeds = {}
    for label, q, ln, lnref in (("15 m @ 4e9", 960, 9, 1), ("60 m @ 4e9", 961, 9, 7), ("100 m @ 4e9", 961, 17, 13)):
        cs, cb = Q.cell(q, ln), Q.cell(961 if q == 961 else 960, lnref)
        if cs and cb and C.complete(cs) and C.complete(cb):
            Ms, Mb = metrics_of(C, cs, None, BO, BG), metrics_of(C, cb, None, BO, BG)
            seeds[label] = dict(
                cells=[cs, cb],
                lvl_at_15m_db=abs(_d(Ms["lvl_db"], Mb["lvl_db"])),
                ac_to_static_db=abs(_d(Ms["ac_to_static_db"], Mb["ac_to_static_db"])),
                contrast_raw=abs(_d(Ms["contrast"]["contrast_raw"], Mb["contrast"]["contrast_raw"])))
        else:
            seeds[label] = dict(cells=[cs, cb], not_landed=True)
    groups = {"1e9": ["15 m @ 1e9", "30 m @ 4e9"],
              "2.5e8": ["15 m @ 2.5e8", "30 m @ 1e9", "60 m @ 4e9"],
              "9e7": ["15 m @ 9e7", "100 m @ 4e9"]}
    seed_for = {"1e9": ["15 m @ 4e9"], "2.5e8": ["15 m @ 4e9", "60 m @ 4e9"],
                "9e7": ["15 m @ 4e9", "60 m @ 4e9", "100 m @ 4e9"]}
    R1 = []
    for g, labels in groups.items():
        cells = [by[l] for l in labels if by[l]["complete"]]
        row = dict(group=g, members=labels, complete=[c["label"] for c in cells],
                   missing=[l for l in labels if not by[l]["complete"]])
        if len(cells) >= 2:
            for q in ("lvl_at_15m_db", "ac_to_static_db", "contrast_raw"):
                v = [c[q] for c in cells if c.get(q) is not None]
                sp = float(max(v) - min(v)) if len(v) >= 2 else None
                sd = [seeds[s].get(q if q != "lvl_at_15m_db" else "lvl_at_15m_db")
                      for s in seed_for[g] if not seeds[s].get("not_landed")]
                sd = [x for x in sd if x is not None]
                T = max(1.0, 3 * max(sd)) if sd else None
                row[q] = dict(values={c["label"]: c[q] for c in cells}, largest_pairwise_abs=sp,
                              T=T, seed_inputs=[s for s in seed_for[g] if not seeds[s].get("not_landed")],
                              crossed=None if (sp is None or T is None) else bool(sp >= T))
            cr = [row[q].get("crossed") for q in ("lvl_at_15m_db", "ac_to_static_db", "contrast_raw")]
            if all(c is not None for c in cr):
                row["verdict"] = ("with matched rays on the drone, range did not cross the threshold "
                                  "(open sky, 15 deg up)" if not any(cr) else
                                  "range changes the open-sky cell beyond ray density at 15 deg up")
        R1.append(row)
    ladder = ["15 m @ 9e7", "15 m @ 2.5e8", "15 m @ 1e9", "15 m @ 4e9"]
    R2 = dict(steps=[], verdict=None)
    for a, b in zip(ladder, ladder[1:]):
        ra, rb = by[a], by[b]
        st = dict(step=f"{a} -> {b}", complete=bool(ra["complete"] and rb["complete"]))
        if st["complete"]:
            st.update(delta_contrast_raw=_d(rb["contrast_raw"], ra["contrast_raw"]),
                      delta_ac_to_static_db=_d(rb["ac_to_static_db"], ra["ac_to_static_db"]))
        R2["steps"].append(st)
    top = next((s for s in R2["steps"] if s["step"].startswith("15 m @ 1e9") and s["complete"]), None)
    if top:
        steep = max(abs(top["delta_contrast_raw"]), abs(top["delta_ac_to_static_db"])) > 2.0
        R2["verdict"] = ("steep in rays between the 30 m and 15 m densities - runners/jobs_0962 reads its 30 m cells "
                         "only as class mean-level ratios (P1-P3, W)" if steep else
                         "the 1e9 -> 4e9 step at 15 m did not cross the 2 dB working threshold "
                         "(threshold not crossed); never written as convergence")
        R2["steep"] = steep
    # T1 / T2 (B)
    T1 = dict(defined=False)
    c28, c197 = Q.cell(961, 15), Q.cell(960, 1)
    if c28 and c197 and C.complete(c28) and C.complete(c197):
        E28 = C.arr(c28)["E"]
        E19 = C.arr(c197)["E"]
        prf28 = C.get(c28)["prf_hz"]
        prf19 = C.get(c197)["prf_hz"]
        t28 = np.arange(E28.size) / prf28
        t19 = np.arange(E19.size) / prf19
        inside = t28 <= t19[-1]
        Eh = (np.interp(t28[inside], t19, E19.real) + 1j * np.interp(t28[inside], t19, E19.imag))
        x = E28[inside]
        num = float(np.mean(np.abs(x - Eh) ** 2))
        den = float(np.mean(np.abs(x - np.mean(x)) ** 2))
        # band-limited FFT interpolation as the knob
        X = np.fft.fft(E19)
        f = np.fft.fftfreq(E19.size, d=1.0 / prf19)
        Eb = (np.exp(2j * np.pi * np.outer(t28[inside], f)) @ X) / E19.size
        numb = float(np.mean(np.abs(x - Eb) ** 2))
        T1 = dict(defined=True, cells=dict(symbol_rate=c28, base=c197), n_used=int(inside.sum()),
                  prf=[prf28, prf19],
                  interp_resid_db_linear=float(10 * np.log10(num / den)),
                  interp_resid_db_bandlimited=float(10 * np.log10(numb / den)))
        # rerun_floor_db: 0957 lines 1-2 (n4096) vs positions 0-4095 of the stored n8192 cell, 0.1 m slab
        c4096, c8192 = Q.cell(957, 1), Q.n8192_partner(Q.cell(957, 1))
        if c4096 and c8192 and C.complete(c4096) and C.complete(c8192):
            a = C.arr(c4096)["E"]
            b = C.arr(c8192)["E"][:a.size]
            da = a - a.mean(); db_ = b - b.mean()
            T1["rerun_floor_db"] = float(10 * np.log10(np.mean(np.abs(da - db_) ** 2) / np.mean(np.abs(da) ** 2)))
            T1["rerun_floor_cells"] = [c4096, c8192]
        cs = Q.cell(960, 9)
        if cs and C.complete(cs):
            a = C.arr(c197)["E"]; b = C.arr(cs)["E"]
            da = a - a.mean(); db_ = b - b.mean()
            T1["seed_floor_db"] = float(10 * np.log10(np.mean(np.abs(da - db_) ** 2) / np.mean(np.abs(da) ** 2)))
            T1["seed_floor_cells"] = [c197, cs]
        floor = T1.get("rerun_floor_db")
        lab = "rerun_floor_db"
        if floor is None:
            floor, lab = T1.get("seed_floor_db"), "seed_floor_db (an upper bound)"
        r = T1["interp_resid_db_linear"]
        if floor is not None and r <= floor + 3.0:
            T1["verdict"] = ("the interpolation residual is not told apart from re-solving the same positions "
                             f"(against {lab}): the receiver interpolates, and the per-position floor is carried "
                             "as a labelled model floor")
        elif r <= -20.0:
            T1["verdict"] = ("19.7 kHz records interpolated to the pilot symbol times stay 20 dB below the rotor "
                             "part (threshold not crossed): the receiver interpolates")
        elif r > -10.0:
            T1["verdict"] = ("rotor-part readouts at the pilot symbol rate need symbol-rate records "
                             "(threshold crossed)")
        else:
            T1["verdict"] = ("between -20 and -10 dB: both numbers written; the receiver uses symbol-rate records "
                             "for rotor-part readouts and interpolation for levels")
        d = x - np.mean(x)
        X28 = np.fft.fft(E28 - E28.mean())
        f28 = np.fft.fftfreq(E28.size, d=1.0 / prf28)
        P = np.abs(X28) ** 2
        P[0] = 0.0
        T1["above_nyq_share"] = float(P[np.abs(f28) > prf19 / 2.0].sum() / P.sum())
        T1["T2_verdict"] = ("at least 1 % of the rotor-part power lies above the 19.7 kHz Nyquist limit at 15 deg up"
                            if T1["above_nyq_share"] >= 0.01 else "threshold not crossed")
        T1["shared_position_rel_diff"] = float(abs(E28[0] - E19[0]) / abs(np.mean(E19)))
        del d
    return dict(cells=rows, R0=R0, R1=R1, R2=R2, seed_diff=seeds, T1_T2=T1)


G62 = {  # runners/jobs_0962 geometry table: label -> (open-sky first line, ground first line, range, el, alt)
    "A": (1, 3, 30.0, -5.0, 4.11), "B": (5, 7, 30.0, -2.5, 2.81), "C": (13, 15, 30.0, -10.0, 6.71),
    "E": (17, 19, 15.0, -5.0, 2.81), "F": (37, 39, 60.0, -5.0, 6.73),
}
G62_EXTRA = {"A depth 3": (None, 9), "B depth 3": (None, 11), "A-img open sky": (21, None),
             "A seed 2": (23, 25), "A iso pointed (orTgt)": (None, 27),
             "A az 90": (29, 31), "A az 180": (33, 35)}


def gate_0962(C, Q, BO, BG) -> dict:
    """runners/jobs_0962 P1/P2/P2d/M2/M3/P3/W/AS/P6 on the matched pairs that are complete."""
    out = dict(cells=[], P1=[], P2=[], P2d=[], P3=[], W=None, AS=[], P6=None, M2=None, M3=None,
               per_cell=[], not_computable=[])
    D2 = {}
    for key, (lo, lg, R, el, alt) in G62.items():
        sky, gnd = Q.cell(962, lo), Q.cell(962, lg)
        rec = dict(key=key, range_m=R, el_deg=el, env_alt=alt, open_sky=sky, ground=gnd,
                   open_sky_complete=bool(sky and C.complete(sky)),
                   ground_complete=bool(gnd and C.complete(gnd)))
        out["cells"].append(rec)
        if not rec["ground_complete"]:
            out["not_computable"].append(f"{key}: ground cell {gnd} not complete")
            continue
        Gh = C.gated(gnd, "hann")
        Gr = C.gated(gnd, "rect")
        if Gh is None:
            out["not_computable"].append(f"{key}: no path-list sidecar for {gnd}")
            continue
        n_cls = {c: float(np.median(Gh["n_class"][c])) for c in CLASSES}
        row = dict(key=key, cell=gnd, median_paths_per_class=n_cls)
        for B in (20e6, 100e6):
            tag = f"{int(B / 1e6)} MHz"
            cp = {c: class_power_db(Gh, c, B) for c in CLASSES}
            cpr = {c: class_power_db(Gr, c, B) for c in CLASSES} if Gr else {}
            row[tag] = dict(class_power_db={f"[{','.join(c)}]": cp[c] for c in CLASSES},
                            class_power_db_rect={f"[{','.join(c)}]": cpr.get(c) for c in CLASSES},
                            env_in_bin_db=env_in_bin_db(Gh, B),
                            env_only_classes=sinc_offsets(Gh, B, "hann"),
                            fade_env_db=fade_env_db(Gh, B))
            if B == 20e6:
                p1 = _d(cp["gd"], cp["dg"])
                out["P1"].append(dict(key=key, cell=gnd, value=p1,
                                      median_paths_gd=n_cls["gd"], median_paths_dg=n_cls["dg"],
                                      verdict=("not defined: no [d,g] path is listed at any position of this cell"
                                               if p1 is None else
                                               ("the two one-bounce classes are reciprocal" if abs(p1) <= 1.0
                                                else "|class_power_db([g,d]) - class_power_db([d,g])| above 1 dB"))))
                if key in P2_COMPUTED:
                    d2 = None if cp["gd"] is None or cp["d"] is None else cp["gd"] - cp["d"] - P2_COMPUTED[key]
                    D2[key] = d2
                    out["P2"].append(dict(key=key, cell=gnd, measured_gd_minus_d=_d(cp["gd"], cp["d"]),
                                          computed_P2_db=P2_COMPUTED[key], D2_db=d2,
                                          verdict=(None if d2 is None else
                                                   ("the ghost follows the computed two-ray level at psi "
                                                    "(threshold not crossed)" if abs(d2) <= 3.0 else
                                                    "|D2| above 3 dB - the listed ghost level does not follow the "
                                                    "computed two-ray level at psi"))))
                    ct = Gh["ctau_class"]
                    fin_d = np.isfinite(ct["d"]); fin_g = np.isfinite(ct["gd"])
                    if fin_d.any() and fin_g.any():
                        ex = 100.0 * (float(np.median(ct["gd"][fin_g])) - float(np.median(ct["d"][fin_d])))
                        dd = ex - RPRIME_MINUS_R_CM[key]
                        out["P2d"].append(dict(key=key, cell=gnd, excess_cm=ex,
                                               computed_cm=RPRIME_MINUS_R_CM[key], diff_cm=dd,
                                               verdict=("the ghost delay follows the two-ray excess "
                                                        "(threshold not crossed)" if abs(dd) <= 10.0 else
                                                        "|excess_cm - 100*(R'-R)| above 10 cm")))
        if rec["open_sky_complete"]:
            M = metrics_of(C, gnd, sky, BO, BG)
            row["contrast_raw"] = M["contrast"]["contrast_raw"]
            row["isolated_20xmedian"] = dict(n=M["isolated_20xmedian"]["n"],
                                             normaliser=M["isolated_20xmedian"]["normaliser_median_abs_dev"],
                                             abs_m=M["isolated_20xmedian"]["abs_m"])
            if "env_field_drop_halfmedian" in M:
                row["env_field_drop_halfmedian"] = M["env_field_drop_halfmedian"]["n"]
                row["median_abs_scene_minus_sky_db"] = M["median_abs_scene_minus_sky_db"]
            Gs = C.gated(sky, "hann")
            if Gs is not None:
                row["contrast_gated_20MHz"] = float(BG.contrast_db(Gh["B20_all"]))
                row["field_difference_due_to_environment_20MHz_db"] = db20(
                    float(np.median(np.abs(Gh["B20_all"] - Gs["B20_all"]))))
                ev = events_of(M)
                row["events_20MHz"] = event_readings(Gh, ev, 20e6)
                row["events_100MHz"] = event_readings(Gh, ev, 100e6)
                if key == "A":
                    e = row["events_20MHz"]
                    out["P6"] = dict(cell=gnd, reference=sky, **e,
                                     verdict=(None if not e.get("defined") else
                                              ("events stay outside the drone's bin (threshold not crossed)"
                                               if e["event_in_bin"] <= 3.0 and e["event_share"] <= 0.10
                                               else "P6 crossed - both numbers and the 100 MHz values written")))
        out["per_cell"].append(row)
    # M2 / M3
    got = {k: v for k, v in D2.items() if v is not None}
    need = ("A", "B", "C", "E")
    if all(k in got for k in need):
        ok = all(abs(got[k]) <= 3.0 for k in need)
        out["M2"] = dict(D2={k: got[k] for k in need}, all_within_3db=ok,
                         verdict=("at tripod height with tr38901 aimed, the ghost level may be computed from the "
                                  "two-ray formula for psi 8.2-16.1 deg (computed, labelled)" if ok else
                                  "P2 crossed - the tracker's fade model takes the listed class ratios, "
                                  "interpolated in psi; nothing outside psi 8.2-16.1 deg is modelled from these cells"))
    else:
        out["M2"] = dict(not_computable=[k for k in need if k not in got])
    if "C" in got and "E" in got:
        d = got["C"] - got["E"]
        out["M3"] = dict(D2_C=got["C"], D2_E=got["E"], diff=d,
                         verdict=("range did not move D2 beyond threshold at psi 15.5-16.1 deg"
                                  if abs(d) <= 2.0 else
                                  "|D2(C) - D2(E)| above 2 dB - psi alone is not the model input; range and aspect "
                                  "are named together"))
    else:
        out["M3"] = dict(not_computable=[k for k in ("C", "E") if k not in got])
    # P3 depth 3
    for key, d3_line, d2_line, ref in (("A", 9, 3, 21), ("B", 11, 7, None)):
        c3 = Q.cell(962, d3_line); c2 = Q.cell(962, d2_line)
        rec = dict(key=key, depth3_cell=c3, depth2_cell=c2,
                   depth3_complete=bool(c3 and C.complete(c3)), depth2_complete=bool(c2 and C.complete(c2)))
        if rec["depth3_complete"]:
            G3 = C.gated(c3, "hann")
            if G3 is not None:
                rec["class_power_db_20MHz"] = {f"[{','.join(c)}]": class_power_db(G3, c, 20e6) for c in CLASSES}
                rec["median_paths_per_class"] = {c: float(np.median(G3["n_class"][c])) for c in CLASSES}
                if key == "A" and ref:
                    cimg = Q.cell(962, ref)
                    if cimg and C.complete(cimg):
                        Gi = C.gated(cimg, "hann")
                        if Gi is not None:
                            tot = float(np.mean(np.abs(Gi["B20_drone"]) ** 2))
                            v = class_power_db(G3, "gdg", 20e6)
                            m = None if v is None or not tot > 0 else v - 10 * np.log10(tot)
                            rec["measured_gdg_minus_img_all_drone_db"] = m
                            rec["computed_db"] = P3_COMPUTED["A"]
                            rec["diff_db"] = None if m is None else m - P3_COMPUTED["A"]
                            rec["verdict"] = (None if m is None else
                                              ("within +-2 dB of the computed value" if abs(rec["diff_db"]) <= 2.0
                                               else "outside +-2 dB of the computed value"))
                if key == "B":
                    v, d = class_power_db(G3, "gdg", 20e6), class_power_db(G3, "d", 20e6)
                    m = _d(v, d)
                    rec["measured_gdg_minus_d_db"] = m
                    rec["computed_db"] = P3_COMPUTED["B"]
                    rec["diff_db"] = None if m is None else m - P3_COMPUTED["B"]
                    rec["verdict"] = (None if m is None else
                                      ("within +-3 dB of the computed value" if abs(rec["diff_db"]) <= 3.0
                                       else "outside +-3 dB of the computed value"))
                if rec["depth2_complete"]:
                    G2 = C.gated(c2, "hann")
                    if G2 is not None:
                        rec["depth3_minus_depth2_db"] = {
                            f"[{','.join(c)}]": _d(class_power_db(G3, c, 20e6), class_power_db(G2, c, 20e6))
                            for c in ("d", "gd", "dg")}
                        ds = [v for v in rec["depth3_minus_depth2_db"].values() if v is not None]
                        rec["other_classes_within_1db"] = bool(ds and max(abs(v) for v in ds) <= 1.0)
        out["P3"].append(rec)
    # W pattern re-weighting: A ground tr38901 (lines 3-4) vs iso pointed (lines 27-28)
    ctr, ciso = Q.cell(962, 3), Q.cell(962, 27)
    if ctr and ciso and C.complete(ctr) and C.complete(ciso):
        Gt, Gi = C.gated(ctr, "hann"), C.gated(ciso, "hann")
        if Gt is not None and Gi is not None:
            w = {}
            for c, gain in W_GAIN_DB.items():
                a, b = class_power_db(Gt, c, 20e6), class_power_db(Gi, c, 20e6)
                e = None if a is None or b is None else a - b - gain
                w[f"[{','.join(c)}]"] = dict(tr38901=a, iso=b, computed_gain_db=gain, w_err=e,
                                             tol_db=0.5 if c == "d" else 1.0,
                                             within=None if e is None else bool(abs(e) <= (0.5 if c == "d" else 1.0)))
            ok = all(v["within"] for v in w.values() if v["within"] is not None) and \
                all(v["within"] is not None for v in w.values())
            out["W"] = dict(cells=[ctr, ciso], per_class=w, passed=ok,
                            verdict=("per-class re-weighting reproduces the aimed pattern at this geometry "
                                     "(threshold not crossed)" if ok else
                                     "w_err outside tolerance - no pattern-weighted number is written"))
    else:
        out["W"] = dict(not_computable=True, cells=[ctr, ciso])
    # AS aspect
    for key, lg in (("az 90", 31), ("az 180", 35)):
        cg = Q.cell(962, lg)
        rec = dict(aspect=key, cell=cg, complete=bool(cg and C.complete(cg)))
        if rec["complete"]:
            G = C.gated(cg, "hann")
            if G is not None:
                for B in (20e6, 100e6):
                    tag = f"{int(B / 1e6)} MHz"
                    gd, d = class_power_db(G, "gd", B), class_power_db(G, "d", B)
                    d2 = None if gd is None or d is None else gd - d - P2_COMPUTED["A"]
                    rec[tag] = dict(gd_minus_d=_d(gd, d), D2=d2)
        out["AS"].append(rec)
    base = next((p for p in out["P2"] if p["key"] == "A"), None)
    if base and base.get("D2_db") is not None:
        for rec in out["AS"]:
            if rec.get("20 MHz", {}).get("D2") is not None:
                for tag in ("20 MHz", "100 MHz"):
                    if rec.get(tag, {}).get("D2") is not None:
                        rec[tag]["D2_minus_D2_az0"] = rec[tag]["D2"] - base["D2_db"]
        vals = [rec[t]["D2_minus_D2_az0"] for rec in out["AS"] for t in ("20 MHz", "100 MHz")
                if rec.get(t, {}).get("D2_minus_D2_az0") is not None]
        if vals:
            out["AS_verdict"] = ("the ghost ratio did not follow aspect beyond threshold at psi 10.6 deg "
                                 "(three aspects)" if max(abs(v) for v in vals) <= 3.0 else
                                 "the fade model carries aspect at this psi")
    return out


def gate_0963(C, Q, BO, BG) -> dict:
    """runners/jobs_0963 S1 coarse gate (lines 1-10, el -5, az 0-162 in 18 deg) and the T_s inputs."""
    rows = []
    for ln in range(1, 31):
        cell = Q.cell(963, ln)
        if not cell:
            continue
        r = dict(line=ln, cell=cell, complete=bool(C.complete(cell)))
        if r["complete"]:
            E = C.arr(cell)["E"]
            r.update(n_poses=int(E.size), lvl_db=lvl_db(E), ac_to_static_db=ac_to_static_db(E),
                     hits_per_pose=C.get(cell)["hits_per_pose"])
        rows.append(r)
    by_line = {r["line"]: r for r in rows}
    seed = None
    pairs = [(11, 1), (12, 4), (13, 6)]                # lines 11-13: seed 2 at az 0 / 54 / 90
    sd = []
    for a, b in pairs:
        ra, rb = by_line.get(a), by_line.get(b)
        if ra and rb and ra["complete"] and rb["complete"]:
            sd.append(dict(pair=[ra["cell"], rb["cell"]], lvl_db=abs(_d(ra["lvl_db"], rb["lvl_db"]))))
    if sd:
        seed = max(x["lvl_db"] for x in sd)
    replay = []
    for ln, partner in ((26, ("0960 lines 1-2",)), (1, ("0962 lines 17-18",))):
        rr = by_line.get(ln)
        pc = Q.cell(960, 1) if ln == 26 else Q.cell(962, 17)
        if rr and rr["complete"] and pc and C.complete(pc):
            E4 = C.arr(pc)["E"][:rr["n_poses"]]
            replay.append(dict(line=ln, cell=rr["cell"], partner=pc,
                               replay_diff_db=abs(rr["lvl_db"] - lvl_db(E4))))
    T_s = max([0.5] + ([3 * seed] if seed is not None else []) +
              [3 * r["replay_diff_db"] for r in replay])
    s1_lines = list(range(1, 11))
    have = [by_line.get(l) for l in s1_lines]
    landed = [h for h in have if h and h["complete"]]
    S1 = dict(series="el -5, az 0-162 in 18 deg (lines 1-10)", n_lines=len(s1_lines), n_landed=len(landed),
              missing=[l for l in s1_lines if not (by_line.get(l) and by_line[l]["complete"])],
              T_s=T_s, seed_diff_lvl_db=seed, replay=replay)
    if landed:
        lv = [h["lvl_db"] for h in landed]
        ac = [h["ac_to_static_db"] for h in landed]
        S1.update(lvl_db_spread=float(max(lv) - min(lv)), ac_to_static_db_spread=float(max(ac) - min(ac)),
                  lvl_db={h["cell"]: h["lvl_db"] for h in landed})
    S1["computable"] = len(landed) == len(s1_lines)
    if S1["computable"]:
        crossed = not (S1["lvl_db_spread"] < max(3.0, T_s) and S1["ac_to_static_db_spread"] < 3.0)
        S1["verdict"] = ("heading crossed the 3 dB fade threshold at el -5 at 18 deg sampling" if crossed else
                         "at 18 deg sampling, heading did not cross the 3 dB fade threshold at el -5 "
                         "- remove unlaunched lines 31-50 and 74-133")
    else:
        S1["verdict"] = ("not computable yet: the S1 gate is written on the complete 18 deg series (lines 1-10); "
                         "the landed subset is listed as a provisional spread and no verdict is written from it")
    # S4 mirror (lines 14-18 against 2-6), S5 heading-0 elevation series (19-25), S6 rotor-to-body
    S4 = dict(pairs=[], T=max(1.0, T_s))
    for a, b, az in ((14, 2, 18), (15, 3, 36), (16, 4, 54), (17, 5, 72), (18, 6, 90)):
        ra, rb = by_line.get(a), by_line.get(b)
        if ra and rb and ra["complete"] and rb["complete"]:
            S4["pairs"].append(dict(az=az, mirror_cell=ra["cell"], cell=rb["cell"],
                                    mirror_diff_db=_d(ra["lvl_db"], rb["lvl_db"])))
    if len(S4["pairs"]) == 5:
        ok = all(abs(x["mirror_diff_db"]) <= S4["T"] for x in S4["pairs"])
        S4["verdict"] = ("the mirror pairs stay within threshold at el -5 - az 180-358 is read as the mirror of "
                         "az 0-178, labelled «mirror assumed within threshold»" if ok else
                         "mirror not assumed - |mirror_diff_db| above max(1 dB, T_s) at one or more of the five pairs")
    else:
        S4["verdict"] = f"not computable yet: {len(S4['pairs'])} of 5 mirror pairs complete"
    S5 = dict(lines=list(range(19, 26)), rows=[])
    for ln in range(19, 26):
        r = by_line.get(ln)
        if r and r["complete"]:
            S5["rows"].append(dict(line=ln, cell=r["cell"], lvl_db=r["lvl_db"],
                                   ac_to_static_db=r["ac_to_static_db"]))
    if len(S5["rows"]) == 7:
        lv = [x["lvl_db"] for x in S5["rows"]]
        S5["lvl_db_spread"] = float(max(lv) - min(lv))
    else:
        S5["note"] = f"not computable yet: {len(S5['rows'])} of 7 elevation cells complete"
    S6 = dict(series="el -5, az 0-162 in 18 deg (lines 1-10)")
    if landed:
        ac = [h["ac_to_static_db"] for h in landed]
        S6.update(n=len(landed), share_ac_ge_0db=float(np.mean([v >= 0 for v in ac])),
                  spread=float(max(ac) - min(ac)), complete_series=len(landed) == 10)
        if S6["complete_series"]:
            S6["verdict"] = ("the rotor-to-body ratio follows heading at el -5 (threshold crossed) -> the n4096 "
                             "extension at the headings of its maximum and minimum" if S6["spread"] >= 6.0 else
                             "max - min of ac_to_static_db below 6 dB at el -5 (threshold not crossed)")
        else:
            S6["verdict"] = "not computable yet: the 18 deg series is incomplete"
    return dict(cells=rows, S1=S1, S4=S4, S5=S5, S6=S6)


def gate_0957(C, Q, BO, BG) -> dict:
    """runners/jobs_0957 check 0, reading 1 (replay), reading 2, P, A, B, C."""
    cells = {"15 m open sky": 1, "30 m open sky 4e9": 3, "30 m open sky 2e9": 5,
             "30 m ground alt 9.26": 7, "15 m ground alt 5.4": 9}
    sky_of = {7: 3, 9: 1}
    radar_h = {7: 9.26 + 30.0 * np.sin(np.deg2rad(-15.0)), 9: 5.4 + 15.0 * np.sin(np.deg2rad(-15.0))}
    out = dict(cells=[], check0=[], replay=[], reading2=[], P=[], A=None, B=[], C=None)
    for label, ln in cells.items():
        cell = Q.cell(957, ln)
        rec = dict(label=label, line=ln, cell=cell, complete=bool(cell and C.complete(cell)))
        if rec["complete"]:
            rec["sidecars"] = C.get(cell)["sidecars"]
        out["cells"].append(rec)
        if not rec["complete"]:
            continue
        G = C.gated(cell, "hann")
        if G is None:
            out["check0"].append(dict(cell=cell, done=False, why="no sidecar"))
            continue
        E = C.arr(cell)["E"]
        rel = np.abs(G["_E_all"] - E) / np.abs(E)
        out["check0"].append(dict(cell=cell, done=True, max_rel_diff=float(rel.max()),
                                  n_positions=int(rel.size), threshold=1e-4,
                                  passed=bool(rel.max() < 1e-4),
                                  n_dup_gt0=int((C.arr(cell)["nd"] > 0).sum())))
        sky = Q.cell(957, sky_of[ln]) if ln in sky_of else None
        M = metrics_of(C, cell, sky, BO, BG)
        ev = events_of(M)
        r2 = dict(label=label, cell=cell, contrast_raw=M["contrast"]["contrast_raw"],
                  n_event_positions=int(ev.size), lvl_db=M["lvl_db"], ac_level_db=M["ac_level_db"],
                  ac_to_static_db=M["ac_to_static_db"], hits_per_pose=M["hits_per_pose"])
        for window in WINDOWS:
            Gw = C.gated(cell, window)
            if Gw is None:
                continue
            Gs = C.gated(sky, window) if sky else None
            per = {}
            for B in B_LIST:
                tag = f"{int(B / 1e6)} MHz"
                d = dict(contrast_gated=float(BG.contrast_db(Gw[f"B{int(B / 1e6)}_all"])),
                         env_in_bin_db=env_in_bin_db(Gw, B),
                         env_only_classes=sinc_offsets(Gw, B, window),
                         **event_readings(Gw, ev, B))
                if Gs is not None:
                    d["field_difference_due_to_environment_db"] = db20(
                        float(np.median(np.abs(Gw[f"B{int(B / 1e6)}_all"] - Gs[f"B{int(B / 1e6)}_all"]))))
                per[tag] = d
            r2[window] = per
        out["reading2"].append(r2)
        # P, for lines 7-10 (the ground cells)
        if ln in radar_h:
            h = radar_h[ln]
            ng = G["n_class"]["g"]
            ct = G["ctau_class"]["g"]
            mask = np.ones(ng.size, bool)
            mask[ev[ev < ng.size]] = False
            one = (ng == 1) & np.array([G["n_class"][c][i] == 0 for i, _ in enumerate(ng)]
                                       if False else np.ones(ng.size, bool))
            other_env = G["n_class"]["gdg"]
            one = (ng == 1) & (other_env == 0)
            within_1cm = np.abs(ct - 2.0 * h) <= 0.01
            share = float(np.mean(one[mask] & within_1cm[mask])) if mask.any() else None
            pr = dict(label=label, cell=cell, radar_height_m=float(h),
                      share_single_env_path_outside_events=share,
                      median_ctau_env_only_m=float(np.nanmedian(ct)),
                      two_h_m=float(2 * h), predicted_a_db=NADIR_A_DB[15 if ln == 9 else 30], per_B={})
            ok = []
            for window in WINDOWS:
                Gw = C.gated(cell, window)
                if Gw is None:
                    continue
                for B in (20e6, 100e6):
                    x = float(np.nanmedian(B * (Gw["ctau_class"]["g"] / C0 - 2.0 * Gw["range_m"] / C0)))
                    hb = float(h_window(np.array([x]), window)[0])
                    pred = pr["predicted_a_db"] + db20(abs(hb))
                    meas = class_power_db(Gw, "g", B)
                    d = None if meas is None else meas - pred
                    pr["per_B"][f"{window} {int(B / 1e6)} MHz"] = dict(
                        offset_cells=x, h_abs_db=db20(abs(hb)), predicted_db=pred, measured_db=meas, diff_db=d)
                    ok.append(None if d is None else abs(d) <= 3.0)
            pr["within_3db_all"] = bool(ok) and all(v for v in ok if v is not None) and None not in ok
            pr["verdict"] = ("in ground only, the environment term in the drone's range bin is the radar's own "
                             "ground reflection seen through the range window (threshold not crossed)"
                             if pr["within_3db_all"] else
                             "P not met at every window and bandwidth - the environment-only paths are listed")
            out["P"].append(pr)
            # B: events at 20 MHz
            e = next((v for v in [r2.get("hann", {}).get("20 MHz")] if v), None)
            if e and e.get("defined"):
                out["B"].append(dict(label=label, cell=cell, event_in_bin=e["event_in_bin"],
                                     event_share=e["event_share"], n_events=e["n_events"],
                                     verdict=("events stay outside the drone's bin (threshold not crossed)"
                                              if e["event_in_bin"] <= 3.0 and e["event_share"] <= 0.10
                                              else "B failed - both numbers are written")))
        # reading 1 replay
        if ln in (1, 9):
            c8 = Q.n8192_partner(cell)
            if c8 and C.complete(c8):
                a = C.arr(cell); b = C.arr(c8)
                n = a["E"].size
                dE = np.abs(a["E"] - b["E"][:n]) / float(np.median(np.abs(a["E"])))
                dn = a["npaths"].astype(np.int64) - b["npaths"][:n].astype(np.int64)
                out["replay"].append(dict(
                    cell=cell, n8192_cell=c8, n=int(n),
                    n_positions_rel_change_above_1e_5=int((dE > REL_REPLAY).sum()),
                    max_rel_change=float(dE.max()), median_rel_change=float(np.median(dE)),
                    n_positions_path_count_differs=int((dn != 0).sum()),
                    path_count_diff_share=float(np.mean(dn != 0)),
                    median_abs_path_count_diff=float(np.median(np.abs(dn))),
                    mean_abs_path_count_share=float(np.mean(np.abs(dn) / np.maximum(b["npaths"][:n], 1)))))
    # A
    g9, g1 = Q.cell(957, 9), Q.cell(957, 1)
    if g9 and g1 and C.complete(g9) and C.complete(g1):
        rows, verdicts = {}, {}
        for window in WINDOWS:
            Gg, Gs = C.gated(g9, window), C.gated(g1, window)
            if Gg is None or Gs is None:
                continue
            for B in (20e6, 100e6):
                t = f"{int(B / 1e6)} MHz"
                cg = float(BG.contrast_db(Gg[f"B{int(B / 1e6)}_all"]))
                cs = float(BG.contrast_db(Gs[f"B{int(B / 1e6)}_all"]))
                rows[f"{window} {t}"] = dict(ground=cg, open_sky=cs, delta=cg - cs)
                v = ("the all-delay contrast deficit of the aimed tripod cell does not reach the drone's bin at B "
                     "(threshold not crossed)" if abs(cg - cs) <= 1.0 else
                     "part of it remains in the bin at B" if cs - cg >= 3.0 else
                     "unresolved at one run per cell")
                verdicts.setdefault(t, {})[window] = v
        agree = {t: (len(set(v.values())) == 1) for t, v in verdicts.items()}
        out["A"] = dict(cells=[g9, g1], contrast_gated=rows, per_window_verdict=verdicts,
                        hann_rect_agree=agree,
                        verdict={t: (list(v.values())[0] if agree[t] else
                                     "Hann and rect disagree - A is not written") for t, v in verdicts.items()})
    # C
    c4, c2 = Q.cell(957, 3), Q.cell(957, 5)
    if c4 and c2 and C.complete(c4) and C.complete(c2):
        M4, M2 = metrics_of(C, c4, None, BO, BG), metrics_of(C, c2, None, BO, BG)
        rec = dict(cells=dict(rays_4e9=c4, rays_2e9=c2),
                   contrast_raw=dict(rays_4e9=M4["contrast"]["contrast_raw"],
                                     rays_2e9=M2["contrast"]["contrast_raw"]))
        rec["contrast_raw"]["delta"] = _d(M4["contrast"]["contrast_raw"], M2["contrast"]["contrast_raw"])
        G4, G2 = C.gated(c4, "hann"), C.gated(c2, "hann")
        if G4 is not None and G2 is not None:
            a, b = float(BG.contrast_db(G4["B20_all"])), float(BG.contrast_db(G2["B20_all"]))
            rec["contrast_gated_20MHz"] = dict(rays_4e9=a, rays_2e9=b, delta=a - b)
        rec["lvl_db"] = dict(rays_4e9=M4["lvl_db"], rays_2e9=M2["lvl_db"], delta=_d(M4["lvl_db"], M2["lvl_db"]))
        rec["ac_to_static_db"] = dict(rays_4e9=M4["ac_to_static_db"], rays_2e9=M2["ac_to_static_db"],
                                      delta=_d(M4["ac_to_static_db"], M2["ac_to_static_db"]))
        ds = [abs(rec["contrast_raw"]["delta"])] + \
             ([abs(rec["contrast_gated_20MHz"]["delta"])] if "contrast_gated_20MHz" in rec else [])
        rec["steep"] = bool(max(ds) > 2.0)
        rec["verdict"] = ("steep in rays at 30 m - no 30 m cell is read further and 0958 is not launched"
                          if rec["steep"] else
                          "the 2e9 -> 4e9 step at 30 m did not cross the 2 dB working threshold (threshold not "
                          "crossed); every 30 m level or contrast carries the ray-density note and a small change "
                          "is never written as convergence")
        out["C"] = rec
    return out


def gate_0959(C, Q, V, BO, BG) -> dict:
    """runners/jobs_0959 (b): the 0950 pattern x pointing 2x2 at cap 2e6, each cell against its own open sky."""
    out = dict(scenes=[], held_lines=[])
    for scene in ("ground", "canyon"):
        rows, sets = [], {}
        for key in ("iso_device", "iso_target", "tr_target", "tr_device"):
            cell = V.get(f"{scene}_el-60_capdefault_{key}")
            rec = dict(antenna=key, cell=cell, complete=bool(cell and C.complete(cell)))
            if rec["complete"]:
                sky = R7.sky_ref(cell, C.F, {c for c in C.rec if C.complete(c)}, True)
                if isinstance(sky, str) and sky.startswith("ambiguous:"):
                    sky = None
                M = metrics_of(C, cell, sky, BO, BG)
                rec.update(open_sky=sky, contrast_raw=M["contrast"]["contrast_raw"],
                           isolated_20xmedian=M["isolated_20xmedian"]["n"],
                           normaliser=M["isolated_20xmedian"]["normaliser_median_abs_dev"],
                           abs_m=M["isolated_20xmedian"]["abs_m"],
                           abs_m_db=db20(M["isolated_20xmedian"]["abs_m"]))
                d = M.get("env_field_drop_halfmedian")
                if d:
                    rec.update(env_field_drop_halfmedian=d["n"],
                               median_abs_scene_minus_sky_db=M["median_abs_scene_minus_sky_db"],
                               median_abs_D_minus_meanD_db=M["median_abs_D_minus_meanD_db"])
                    sets[key] = set(d["indices"])
            rows.append(rec)
        base = sets.get("iso_device")
        for r in rows:
            if r["antenna"] in sets and base is not None:
                r["jaccard_with_iso_device"] = jaccard(sets[r["antenna"]], base)
        rec = dict(scene=scene, rows=rows)
        if scene == "ground":
            ok = [r for r in rows if r.get("jaccard_with_iso_device") is not None]
            if len(ok) == 4:
                good = all(r["jaccard_with_iso_device"] >= 0.97 and 82 <= r["env_field_drop_halfmedian"] <= 84
                           for r in ok)
                rec["verdict"] = ("the field-drop set did not follow pattern or orientation at 2e6 "
                                  "(threshold not crossed)" if good else
                                  "a Jaccard below 0.97 or a count outside 82-84 - path lists at those positions")
            else:
                rec["verdict"] = "not computable yet: not all four antenna cells are complete"
        else:
            rec["note"] = "street canyon iso/device has 0 drops (0959 header), so the canyon row is read on level only"
        out["scenes"].append(rec)
    return out


# ═══ 4. index from job line to cell ═════════════════════════════════════════════════════════════════════
class QIndex:
    def __init__(self, store):
        self.line_cell, self.store = {}, store

    def add(self, q, no, cell):
        self.line_cell.setdefault((q, no), cell)

    def cell(self, q, no):
        return self.line_cell.get((q, no))

    def n8192_partner(self, cell):
        if not cell or "_n4096_" not in cell:
            return None
        c = cell.replace("_n4096_", "_n8192_")
        return c if c in self.store else None


# ═══ 5. markdown ════════════════════════════════════════════════════════════════════════════════════════
def n_(x, nd=2):
    if x is None:
        return "–"
    if isinstance(x, bool):
        return "yes" if x else "no"
    if isinstance(x, (int, np.integer)):
        return f"{int(x):,}"
    return f"{float(x):,.{nd}f}"


def md(doc: dict) -> str:
    w = []
    a = w.append
    m = doc["_meta"]
    a("# Readout 0918 — queues 0957-0963 (generated)\n")
    a(f"`{m['generator']}` · {m['created_utc']} · git `{m['git_head'][:12]}` · "
      f"sionna-rt {m['inputs']['sionna_rt']} · runtime {n_(m['runtime_s'], 1)} s\n")
    a("> Simulation bookkeeping from stored PathSolver shards and their path-list sidecars. No RF measurement, no "
      "comparison with hardware, and nothing here says why the solver lists or omits a path. Every verdict below is "
      "the queue header's own pre-set working rule applied to the numbers in the same row; a threshold that is not "
      "reached is written «threshold not crossed», never «no effect».\n")
    a(f"**Scope of every number.** {doc['common_scope']}\n")
    a("## 1. Queue manifest\n")
    a("| queue | file | lines (queued / held) | named stems | cells | shards present / expected | complete cells | "
      "sidecars present / expected | running now |")
    a("|---|---|---:|---:|---:|---:|---:|---:|---:|")
    for q in doc["queues"]:
        a(f"| {q['queue']} | `{q['file']}` | {q['n_lines_queued']} / {q['n_lines_held']} | {q['n_named_stems']} | "
          f"{q['n_cells']} | {q['n_shards_present']} / {q['n_shards_expected']} | {q['n_cells_complete']} | "
          f"{q['n_sidecars_present']} / {q['n_sidecars_expected']} | {q['n_running']} |")
    a("")
    for q in doc["queues"]:
        a(f"### {q['queue']} — `{q['file']}`\n")
        if q.get("bad_lines"):
            a(f"⚠ {len(q['bad_lines'])} line(s) named nothing: "
              + "; ".join(f"job line {b['job_line']}: {b['why']}" for b in q["bad_lines"]) + "\n")
        a("| job lines | hold | cell | shards | complete | sidecars | positions | median paths | reason |")
        a("|---|---|---|---:|---|---:|---:|---:|---|")
        for c in q["cells"]:
            sc = c.get("sidecars") or {}
            a(f"| {c['lines']} | {c['hold'] or '–'} | `{c['cell']}` | "
              f"{c['n_shards_present']}/{c['n_shards_expected']} | {n_(c['complete'])} | "
              + (f"{sc.get('present', 0)}/{sc.get('expected', 0)}" if sc.get("requested")
                 else "no --dump-paths") + f" | {n_(sc.get('n_unique_positions'))} | "
              f"{n_(sc.get('median_paths_per_position'))} | {c.get('reason') or ''} |")
        a("")
    a("## 2. What each header's gate says now\n")
    for key in ("0957", "0958", "0959", "0960", "0961", "0962", "0963"):
        a(f"### {key}\n")
        for line in doc["verdicts"].get(key, []):
            a(f"- {line}")
        a("")
    a("## 3. Still missing\n")
    for line in doc["open_items"]:
        a(f"- {line}")
    a("")
    a("## 4. Tables\n")
    a("The full numbers, index sets and per-window values are in `outputs/readout_0918.json` "
      "(`gates.0957`, `gates.0959`, `gates.0960`, `gates.0961`, `gates.0962`, `gates.0963`).\n")
    for title, rows in doc["md_tables"]:
        a(f"### {title}\n")
        a("| " + " | ".join(rows[0]) + " |")
        a("|" + "|".join("---" for _ in rows[0]) + "|")
        for r in rows[1:]:
            a("| " + " | ".join(r) + " |")
        a("")
    return "\n".join(w)



def build_text(G, queues):
    """The per-queue verdict lines and the markdown tables, straight from the gate records."""
    V, T = {}, []

    def f(x, nd=2, unit=""):
        return "–" if x is None else (f"{x:,.{nd}f}{unit}" if isinstance(x, float) else f"{x:,}{unit}")

    def short(cell):
        """Cell name with the parts every row of these tables shares removed (full names in the manifest/JSON)."""
        t = cell
        for junk in ("sionna_", "swR0D0E0F1_", "_shell0.75mm_prop1.43mm", "_mfixbatteryi5",
                     "_blperairframe", "_anttr38901", "_rt210"):
            t = t.replace(junk, "")
        return t

    # ---- 0957
    g = G["0957"]
    L = []
    for c in g["check0"]:
        if c.get("done"):
            L.append(f"**check 0** `{c['cell']}`: max |Σ_hit a·exp(−j2πf_cτ) − E|/|E| = {c['max_rel_diff']:.2e} over "
                     f"{c['n_positions']:,} positions (threshold 1e−4) → "
                     + ("passed" if c["passed"] else "**failed**") + f"; n_dup > 0 at {c['n_dup_gt0']} positions.")
    for r in g["replay"]:
        L.append(f"**reading 1 (replay)** `{r['cell']}` against positions 0-{r['n'] - 1} of `{r['n8192_cell']}`: "
                 f"{r['n_positions_rel_change_above_1e_5']:,} of {r['n']:,} positions with |ΔE|/median|E| > 1e−5 "
                 f"(max {r['max_rel_change']:.3g}); path counts differ at {r['n_positions_path_count_differs']:,} "
                 f"positions ({100 * r['path_count_diff_share']:.1f} %), mean |Δn|/n "
                 f"{100 * r['mean_abs_path_count_share']:.2f} %.")
    for p_ in g["P"]:
        rows = p_["per_B"]
        worst = max((abs(v["diff_db"]) for v in rows.values() if v["diff_db"] is not None), default=None)
        L.append(f"**P** `{p_['cell']}` (radar {p_['radar_height_m']:.3f} m): a single environment-only path of "
                 f"length 2h within 1 cm at {100 * (p_['share_single_env_path_outside_events'] or 0):.2f} % of the "
                 f"positions outside event positions; measured − predicted in-bin power at most "
                 f"{f(worst)} dB over Hann/rect × 20/100 MHz → {p_['verdict']}")
    for b in g["B"]:
        L.append(f"**B** `{b['cell']}`: event_in_bin {b['event_in_bin']:.2f}, event_share "
                 f"{100 * b['event_share']:.1f} % over {b['n_events']} event positions (20 MHz Hann) → {b['verdict']}")
    if g.get("A"):
        for t, v in g["A"]["verdict"].items():
            d = g["A"]["contrast_gated"].get(f"hann {t}", {})
            L.append(f"**A** at {t}: contrast_gated ground {f(d.get('ground'))} dB vs open sky "
                     f"{f(d.get('open_sky'))} dB (Δ {f(d.get('delta'))} dB) → {v}")
    if g.get("C"):
        c = g["C"]
        L.append(f"**C** 30 m open sky, 2e9 → 4e9 rays: Δcontrast_raw {f(c['contrast_raw']['delta'])} dB, "
                 f"Δcontrast_gated(20 MHz) {f(c.get('contrast_gated_20MHz', {}).get('delta'))} dB, "
                 f"Δlvl_db {f(c['lvl_db']['delta'])} dB → {c['verdict']}")
    V["0957"] = L

    # ---- 0958
    g = G["0958"]
    V["0958"] = [f"{g['status']}: {g['n_lines']} job lines, "
                 f"{sum(c['shards'] for c in g['cells'])} shards on disk. Readings G and F are not computable.",
                 "Release triggers (any one): " + "; ".join(g["release_triggers"]) + "."]
    if g.get("superseded_note"):
        V["0958"].append(g["superseded_note"])

    # ---- 0959
    g = G["0959"]
    L = []
    for sc in g["scenes"]:
        done = [r for r in sc["rows"] if r["complete"]]
        bits = "; ".join(
            f"{r['antenna']}: env_field_drop_halfmedian {f(r.get('env_field_drop_halfmedian'))}, Jaccard with "
            f"iso/device {f(r.get('jaccard_with_iso_device'), 4)}, median |scene − sky| "
            f"{f(r.get('median_abs_scene_minus_sky_db'))} dB, isolated_20xmedian {f(r.get('isolated_20xmedian'))}, "
            f"contrast_raw {f(r.get('contrast_raw'))} dB" for r in done)
        L.append(f"**(b) {sc['scene']}**: {len(done)} of 4 antenna cells complete. " + bits
                 + (f" → {sc['verdict']}" if sc.get("verdict") else "")
                 + (f" ({sc['note']})" if sc.get("note") else ""))
    L.append("**(a)** lines 1-4 are «#HOLD »; the seed-pair threshold T of the 0952 cap comparison stays unavailable.")
    V["0959"] = L

    # ---- 0960
    g = G["0960"]
    L = []
    if g.get("G0"):
        z = g["G0"]
        L.append(f"**G0** (15 m open sky, canonical slab vs 0.1 m): thickness_delta(lvl_db) "
                 f"{f(z['delta_lvl_db'])} dB, thickness_delta(ac_level_db) {f(z['delta_ac_level_db'])} dB, "
                 f"hits_per_pose {z['hits_per_pose']['cell']} vs {z['hits_per_pose']['ref']} "
                 f"({100 * (z['hits_per_pose']['rel_change'] or 0):.1f} % apart, "
                 + ("within" if z["hits_within_3pct"] else "**outside**") + " 3 %) → " + z["verdict"] + ".")
    if g.get("seed_diff", {}).get("values"):
        s = g["seed_diff"]["values"]
        L.append("**seed_diff** (0960 lines 9-10 vs 1-2): lvl_db " + f(s["lvl_db"]) + " dB, ac_level_db "
                 + f(s["ac_level_db"]) + " dB, ac_to_static_db " + f(s["ac_to_static_db"]) + " dB, contrast_raw "
                 + f(s["contrast_raw"]) + " dB, isolated_20xmedian " + f(s["isolated_20xmedian"])
                 + " positions → T_q = max(floor, 3·seed_diff).")
    if g.get("T1"):
        L.append("**T1** → " + g["T1"]["verdict"] + (": " + "; ".join(g["T1"]["why"]) if g["T1"]["why"] else "."))
    for t in g.get("T2_ghost", []):
        L.append(f"**T2 (ghost, written not gated)** {t['label']}: class_power_db([g,d]) − class_power_db([d]) = "
                 f"{f(t.get('class_gd_minus_d_db'))} dB at 20 MHz beside the computed {t['computed_db']} dB.")
    V["0960"] = L

    # ---- 0961
    g = G["0961"]
    L = []
    r0 = g["R0"]
    if r0.get("passed") is not None:
        L.append(f"**R0** hits_per_pose / (spp/R²) over {r0['n_cells']} landed cells: median {r0['median']:.3g}, "
                 f"outside ±10 %: " + (", ".join(r0["outside_10pct"]) or "none") + f" → {r0['verdict']}"
                 + (f" (still waiting for {', '.join(r0['listed'])})" if r0.get("listed") else "") + ".")
    for row in g["R1"]:
        if row.get("verdict"):
            parts = []
            for q in ("lvl_at_15m_db", "ac_to_static_db", "contrast_raw"):
                parts.append(f"{q} {f(row[q]['largest_pairwise_abs'])} dB vs T {f(row[q]['T'])} dB")
            cav = ("" if r0.get("passed") else
                   " ⚠ R0 has not passed, so under the header's own rule no range reading is written: this row is "
                   "listed as data, not read as a result.")
            L.append(f"**R1** group {row['group']} ({', '.join(row['complete'])}): " + "; ".join(parts)
                     + f" → {row['verdict']}.{cav}")
        else:
            L.append(f"**R1** group {row['group']}: not computable yet "
                     f"(missing {', '.join(row['missing']) or 'a seed pair'}).")
    if g["R2"].get("verdict"):
        st = ", ".join(f"{s['step']}: Δcontrast_raw {f(s.get('delta_contrast_raw'))} dB, Δac_to_static_db "
                       f"{f(s.get('delta_ac_to_static_db'))} dB" for s in g["R2"]["steps"] if s["complete"])
        L.append(f"**R2** {st} → {g['R2']['verdict']}.")
    if g.get("R3"):
        r3 = g["R3"]
        L.append(f"**R3** 0957 reading C Δcontrast_raw {f(r3['jobs_0957_C_delta_contrast_raw'])} dB "
                 f"(Δcontrast_gated 20 MHz {f(r3['jobs_0957_C_delta_contrast_gated_20MHz'])} dB) beside the 15 m "
                 f"1e9 → 4e9 step Δcontrast_raw {f(r3['step_15m_1e9_to_4e9_delta_contrast_raw'])} dB and the 15 m "
                 f"seed difference of contrast_raw {f(r3['seed_diff_contrast_raw_15m'])} dB — {r3['note']}.")
    t = g["T1_T2"]
    if t.get("defined"):
        L.append(f"**T1 (B)** interp_resid_db (linear) {f(t['interp_resid_db_linear'])} dB, band-limited "
                 f"{f(t['interp_resid_db_bandlimited'])} dB; rerun_floor_db {f(t.get('rerun_floor_db'))} dB, "
                 f"seed_floor_db {f(t.get('seed_floor_db'))} dB → {t['verdict']}.")
        L.append(f"**T2 (B)** above_nyq_share {100 * t['above_nyq_share']:.3f} % → {t['T2_verdict']}; "
                 f"|E28(0) − E19.7(0)|/|mean E| = {t['shared_position_rel_diff']:.3g}.")
    V["0961"] = L

    # ---- 0962
    g = G["0962"]
    L = []
    for p_ in g["P1"]:
        L.append(f"**P1** {p_['key']}: class_power_db([g,d]) − class_power_db([d,g]) = {f(p_['value'])} dB "
                 f"(median paths per position: [g,d] {p_['median_paths_gd']:.0f}, [d,g] {p_['median_paths_dg']:.0f}) "
                 f"→ {p_['verdict']}.")
    L.append("Written beside P1, not a verdict: the two one-bounce orderings are not listed in equal numbers in "
             "these depth-2 sidecars (see the medians above). Nothing here says why.")
    for p_ in g["P2"]:
        L.append(f"**P2** {p_['key']}: measured [g,d] − [d] = {f(p_['measured_gd_minus_d'])} dB, computed "
                 f"{p_['computed_P2_db']} dB, D2 = {f(p_['D2_db'])} dB → {p_['verdict']}.")
    for p_ in g["P2d"]:
        L.append(f"**P2d** {p_['key']}: excess_cm {f(p_['excess_cm'])} cm against the computed "
                 f"{p_['computed_cm']} cm (Δ {f(p_['diff_cm'])} cm) → {p_['verdict']}.")
    if g["M2"].get("verdict"):
        L.append("**M2** → " + g["M2"]["verdict"] + ".")
    elif g["M2"].get("not_computable"):
        L.append("**M2** not computable yet: D2 missing at " + ", ".join(g["M2"]["not_computable"]) + ".")
    if g["M3"].get("verdict"):
        L.append(f"**M3** D2(C) {f(g['M3']['D2_C'])} dB, D2(E) {f(g['M3']['D2_E'])} dB, Δ {f(g['M3']['diff'])} dB "
                 f"→ {g['M3']['verdict']}.")
    elif g["M3"].get("not_computable"):
        L.append("**M3** not computable yet: missing " + ", ".join(g["M3"]["not_computable"]) + ".")
    for p_ in g["P3"]:
        if p_.get("verdict"):
            L.append(f"**P3** {p_['key']}: measured {f(p_.get('measured_gdg_minus_img_all_drone_db') or p_.get('measured_gdg_minus_d_db'))} dB "
                     f"vs computed {p_['computed_db']} dB (Δ {f(p_.get('diff_db'))} dB) → {p_['verdict']}"
                     + ("; depth 3 − depth 2 of [d], [g,d], [d,g] "
                        + ("within" if p_.get("other_classes_within_1db") else "**outside**") + " ±1 dB ("
                        + ", ".join(f"{k} {f(v)} dB" for k, v in (p_.get("depth3_minus_depth2_db") or {}).items())
                        + ")" if "other_classes_within_1db" in p_ else "")
                     + "; median listed paths per position "
                     + ", ".join(f"[{','.join(k)}] {v:.0f}" for k, v in
                                 (p_.get("median_paths_per_class") or {}).items()) + ".")
        else:
            L.append(f"**P3** {p_['key']}: not computable yet (depth-3 cell complete: {p_['depth3_complete']}).")
    if g["W"] and not g["W"].get("not_computable"):
        bits = ", ".join(f"{k} w_err {f(v['w_err'])} dB (tol ±{v['tol_db']})" for k, v in g["W"]["per_class"].items())
        L.append(f"**W** {bits} → {g['W']['verdict']}.")
    else:
        L.append("**W** not computable yet: the iso pointed cell or its tr38901 partner is not complete.")
    if g.get("AS_verdict"):
        bits = []
        for rec in g["AS"]:
            for t in ("20 MHz", "100 MHz"):
                if rec.get(t, {}).get("D2") is not None:
                    bits.append(f"{rec['aspect']} {t}: D2 {f(rec[t]['D2'])} dB, "
                                f"D2 − D2(az 0) {f(rec[t]['D2_minus_D2_az0'])} dB")
        L.append("**AS** " + "; ".join(bits) + " → " + g["AS_verdict"] + ".")
    else:
        L.append("**AS** not computable yet: az 90 / az 180 ground cells or the az 0 D2 are missing.")
    if g.get("P6"):
        L.append(f"**P6** event_in_bin {f(g['P6'].get('event_in_bin'))}, event_share "
                 f"{f(100 * (g['P6'].get('event_share') or 0))} % → {g['P6']['verdict']}.")
    for nc in g["not_computable"]:
        L.append("not computable: " + nc + ".")
    r2 = G["0961"]["R2"]
    if r2.get("steep"):
        L.append("⚠ precondition (3) of the 0962 header: runners/jobs_0961 R2 is «steep», so the 30 m cells of this "
                 "file are read only on P1-P3 and W (class mean-level ratios). contrast_raw, contrast_gated and the "
                 "event readings (P6) at 30 m are written as data below, not read as results.")
    L.append("**F** (60 m, psi 7.84 deg) is read only if runners/jobs_0961 R1 did not cross in group 2.5e8. R0 has "
             "not passed, so no R1 reading is written and F is not read; its cells are listed.")
    V["0962"] = L

    # ---- 0963
    g = G["0963"]
    s = g["S1"]
    L = [f"**S1** {s['series']}: {s['n_landed']} of {s['n_lines']} cells landed"
         + (f", missing lines {', '.join(str(x) for x in s['missing'])}" if s["missing"] else "")
         + f"; T_s = {f(s['T_s'])} dB (seed_diff {f(s.get('seed_diff_lvl_db'))} dB, "
         + ("replay_diff_db " + ", ".join(f"{r['replay_diff_db']:.3f}" for r in s["replay"]) if s["replay"]
            else "no replay landed") + ") → " + s["verdict"] + "."]
    if s.get("lvl_db_spread") is not None:
        lab = "" if s["computable"] else "Provisional over the landed subset only (not a verdict): "
        L.append(f"{lab}max − min lvl_db {f(s['lvl_db_spread'])} dB, max − min ac_to_static_db "
                 f"{f(s['ac_to_static_db_spread'])} dB.")
    if g.get("S4"):
        s4 = g["S4"]
        L.append("**S4** " + (", ".join(f"az {x['az']}: {f(x['mirror_diff_db'])} dB" for x in s4["pairs"])
                              or "no pair complete") + f" (T = {f(s4['T'])} dB) → {s4['verdict']}.")
    if g.get("S6", {}).get("verdict"):
        s6 = g["S6"]
        L.append(f"**S6** max − min ac_to_static_db {f(s6.get('spread'))} dB over {s6.get('n')} cells; share with "
                 f"ac_to_static_db ≥ 0 dB {f(100 * (s6.get('share_ac_ge_0db') or 0))} % → {s6['verdict']}.")
    if g.get("S5", {}).get("note"):
        L.append("**S5** " + g["S5"]["note"] + ".")
    elif g.get("S5", {}).get("lvl_db_spread") is not None:
        L.append(f"**S5** heading-0 elevation series: max − min lvl_db {f(g['S5']['lvl_db_spread'])} dB "
                 "(no trend is read beyond the series).")
    V["0963"] = L

    # ---- tables
    rows = [["pair", "Δ lvl_db", "Δ ac_level_db", "Δ ac_to_static_db", "Δ contrast_raw",
             "Δ env_in_bin_db 20 MHz", "Δ contrast_gated 20 MHz", "T(ac_to_static)"]]
    for p_ in G["0960"]["pairs"]:
        if not p_.get("lvl_db"):
            rows.append([p_.get("label", "?"), "not complete", "", "", "", "", "", ""])
            continue
        h = (p_.get("gated") or {}).get("hann", {}).get("20 MHz", {})
        rows.append([p_["label"], f(p_["lvl_db"]["delta"]), f(p_["ac_level_db"]["delta"]),
                     f(p_["ac_to_static_db"]["delta"]), f(p_["contrast_raw"]["delta"]),
                     f(h.get("env_in_bin_db", {}).get("delta")), f(h.get("contrast_gated", {}).get("delta")),
                     f(p_["thresholds"]["ac_to_static_db"])])
    T.append(("0960 T1 — thin-slab bridge (canonical slab − 0.1 m slab, dB)", rows))

    rows = [["cell", "spp", "R m", "hits_per_pose", "hits/(spp/R²)", "lvl_db", "lvl_at_15m_db",
             "ac_to_static_db", "contrast_raw"]]
    for r in G["0961"]["cells"]:
        if not r["complete"]:
            rows.append([r["label"], f"{r['spp']:.3g}", f(r["range_m"], 1), "not complete", "", "", "", "", ""])
            continue
        rows.append([r["label"], f"{r['spp']:.3g}", f(r["range_m"], 1), f(r["hits_per_pose"]),
                     f"{r['hits_over_spp_over_R2']:.4g}", f(r["lvl_db"]), f(r["lvl_at_15m_db"]),
                     f(r["ac_to_static_db"]), f(r["contrast_raw"])])
    T.append(("0961 (A) — open-sky range and ray-density cells", rows))

    rows = [["cell", "ψ row", "[d]", "[g,d]", "[d,g]", "[g]", "[g,d,g]", "env_in_bin_db", "D2"]]
    d2 = {p_["key"]: p_["D2_db"] for p_ in G["0962"]["P2"]}
    for r in G["0962"]["per_cell"]:
        c = r.get("20 MHz", {}).get("class_power_db", {})
        rows.append([short(r["cell"]), r["key"], f(c.get("[d]")), f(c.get("[g,d]")),
                     f(c.get("[d,g]")), f(c.get("[g]")), f(c.get("[g,d,g]")),
                     f(r.get("20 MHz", {}).get("env_in_bin_db")), f(d2.get(r["key"]))])
    T.append(("0962 — class_power_db at 20 MHz Hann (dB) and D2", rows))

    rows = [["cell", "B", "contrast_raw", "contrast_gated", "env_in_bin_db", "event_in_bin", "event_share %",
             "field difference due to the environment"]]
    for r in G["0957"]["reading2"]:
        for tag, d in (r.get("hann") or {}).items():
            rows.append([short(r["cell"]), tag, f(r["contrast_raw"]),
                         f(d.get("contrast_gated")), f(d.get("env_in_bin_db")), f(d.get("event_in_bin")),
                         f(100 * d["event_share"]) if d.get("event_share") is not None else "–",
                         f(d.get("field_difference_due_to_environment_db"))])
    T.append(("0957 reading 2 — per cell and bandwidth (Hann; rect in the JSON)", rows))

    rows = [["line", "cell", "lvl_db", "ac_to_static_db"]]
    for r in G["0963"]["cells"]:
        rows.append([str(r["line"]), short(r["cell"]),
                     f(r.get("lvl_db")) if r["complete"] else "not complete", f(r.get("ac_to_static_db"))])
    T.append(("0963 — landed 1,024-position cells", rows))
    return V, T


# ═══ 6. main ════════════════════════════════════════════════════════════════════════════════════════════
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--refresh-stems", action="store_true")
    ap.add_argument("--max-cores", type=int, default=4)
    ap.add_argument("--no-paths", action="store_true", help="skip the path-list sidecar layer")
    A = ap.parse_args()
    if A.max_cores > 0 and hasattr(os, "sched_setaffinity"):
        allowed = sorted(os.sched_getaffinity(0))
        os.sched_setaffinity(0, set(allowed[:max(1, min(A.max_cores, len(allowed)))]))
    t0 = time.time()
    import bake_ground2 as BG                                           # noqa: E402
    import bake_outdoor as BO                                           # noqa: E402
    defaults = json.loads(LEDGER_DEFAULTS.read_text(encoding="utf-8"))["_meta"]

    qf = queue_files()
    rows = {q: queue_rows(p) for q, p in qf.items()}
    view = R7.VIEW_LINES
    all_lines = {ln for rr in rows.values() for _, _, ln, _ in rr} | set(view.values())
    names = name_lines(all_lines, A.refresh_stems, max(1, A.max_cores))
    running = running_workers()
    store = store_index()
    print(f"  store: {sum(len(v) for v in store.values()):,} rt-tagged shards in {len(store):,} cells", flush=True)

    def cells_of(line):
        out = []
        for nm in names.get(line, {}).get("names", []):
            mm = SHARD_RE.match(nm)
            if mm:
                out.append((mm.group("cell"), nm))
        return out

    Q = QIndex(store)
    expected, bought, nshards_line, line_running, hold_of, dump_of = {}, {}, {}, {}, {}, {}
    queues = []
    for q in sorted(qf):
        cells_q, bad, n_run, n_held, n_queued, stems, filelines = {}, [], 0, 0, 0, set(), {}
        for jno, no, ln, hold in rows[q]:
            n_held += int(bool(hold)); n_queued += int(not hold)
            cs = cells_of(ln)
            if not cs:
                bad.append(dict(job_line=jno, file_line=no, why=names.get(ln, {}).get("why")))
                continue
            toks = shlex.split(ln)
            nsh = int(toks[toks.index("--nshards") + 1]) if "--nshards" in toks else None
            ndump = int(toks[toks.index("--dump-paths") + 1]) if "--dump-paths" in toks else None
            is_run = norm_line(ln) in running
            n_run += int(is_run)
            for cell, nm in cs:
                stems.add(nm)
                Q.add(q, jno, cell)
                expected.setdefault(cell, set()).add(nm)
                filelines.setdefault(cell, []).append(no)
                bought.setdefault(cell, {}).setdefault(qf[q].name, []).append(jno)
                if nsh:
                    nshards_line[cell] = nsh
                if ndump:
                    dump_of[cell] = ndump
                if hold:
                    hold_of[cell] = hold
                if is_run:
                    line_running.setdefault(cell, []).append(dict(file=qf[q].name, job_line=jno,
                                                                  **running[norm_line(ln)]))
                cells_q.setdefault(cell, []).append(jno)
        queues.append(dict(queue=q, file=qf[q].name, n_lines_queued=n_queued, n_lines_held=n_held,
                           n_named_stems=len(stems), bad_lines=bad, n_running=n_run, _cells=cells_q,
                           _filelines=filelines))

    C = Cells(store, expected, nshards_line, defaults, use_paths=not A.no_paths, dump_of=dump_of)
    V = {}
    for k, ln in view.items():
        cs = cells_of(ln)
        V[k] = cs[0][0] if cs else None
    for q in queues:
        for cell in q["_cells"]:
            C.get(cell)
    for k, cell in V.items():
        if cell and cell in store:
            C.get(cell)
    # references the gates need
    for cell in list(C.rec):
        p = Q.n8192_partner(cell)
        if p:
            C.get(p)
    for cell in [c for c in store if c not in C.rec]:
        if "_el-60" in cell and "_n8192_" in cell and "_env" not in cell and "_rt210" in cell:
            C.get(cell)

    for q in queues:
        cc = []
        for cell, lns in q["_cells"].items():
            r = C.get(cell)
            sc = r.get("sidecars", {})
            cc.append(dict(lines="-".join(str(x) for x in (min(lns), max(lns))) if len(lns) > 1 else str(lns[0]),
                           line_numbers=sorted(set(lns)),
                           file_line_numbers=sorted(set(q["_filelines"].get(cell, []))),
                           hold=hold_of.get(cell), cell=cell,
                           n_shards_present=len(r["shards_present"]), n_shards_expected=len(r["shards_expected"]),
                           complete=bool(r.get("complete")), reason=r.get("reason"), sidecars=sc,
                           solver_build=r.get("solver_build"), running=line_running.get(cell, []),
                           shard_mtime_utc=r.get("shard_mtime_utc"),
                           cfg_mismatches=R7.cfg_checks(C.F[cell], r, None) if "grammar" in C.F[cell] else
                           ["name not parsed"]))
        cc.sort(key=lambda x: x["line_numbers"][0])
        q["cells"] = cc
        q["n_cells"] = len(cc)
        q["n_cells_complete"] = sum(1 for x in cc if x["complete"])
        q["n_shards_present"] = sum(x["n_shards_present"] for x in cc)
        q["n_shards_expected"] = sum(x["n_shards_expected"] for x in cc)
        q["n_sidecars_present"] = sum((x["sidecars"] or {}).get("present", 0) for x in cc)
        q["n_sidecars_expected"] = sum((x["sidecars"] or {}).get("expected", 0) for x in cc)
        q.pop("_cells"); q.pop("_filelines")

    print("  gates", flush=True)
    gates = dict(g0957=gate_0957(C, Q, BO, BG), g0959=gate_0959(C, Q, V, BO, BG),
                 g0960=gate_0960(C, Q, BO, BG), g0961=gate_0961(C, Q, BO, BG),
                 g0962=gate_0962(C, Q, BO, BG), g0963=gate_0963(C, Q, BO, BG))
    gates = {k[1:]: v for k, v in gates.items()}
    # R3 of runners/jobs_0961: the 0957 reading C step written beside the 1e9 -> 4e9 step and the 15 m seed difference
    c57 = gates["0957"].get("C")
    if c57:
        step = next((x for x in gates["0961"]["R2"]["steps"]
                     if x["step"].startswith("15 m @ 1e9") and x["complete"]), None)
        gates["0961"]["R3"] = dict(
            jobs_0957_C_delta_contrast_raw=c57["contrast_raw"]["delta"],
            jobs_0957_C_delta_contrast_gated_20MHz=(c57.get("contrast_gated_20MHz") or {}).get("delta"),
            step_15m_1e9_to_4e9_delta_contrast_raw=(step or {}).get("delta_contrast_raw"),
            step_15m_1e9_to_4e9_delta_ac_to_static_db=(step or {}).get("delta_ac_to_static_db"),
            seed_diff_contrast_raw_15m=gates["0961"]["seed_diff"].get("15 m @ 4e9", {}).get("contrast_raw"),
            note="written side by side (0961 R3); no verdict of its own")
    sup = (RUNNERS / "jobs_0964_full_scene_30m_thin_slab.txt")
    gates["0958"] = dict(status="HOLD - no line launched", n_lines=8, cells=[
        dict(cell=c["cell"], lines=c["lines"], shards=c["n_shards_present"]) for q in queues
        if q["queue"] == 958 for c in q["cells"]],
        release_triggers=["0957 check 0/2 pass, C is not steep, and the CPU receiver has run on the 0957 open-sky "
                          "and ground-only path lists", "an X410 capture shows a failure a wall return or wall "
                          "multipath could explain", "the user asks for it"],
        superseded_by=(sup.name if sup.exists() else None),
        superseded_note=("runners/jobs_0964_full_scene_30m_thin_slab.txt (2026-09-18) states that it replaces this "
                         "file and that 0958 is superseded, not released: the 8 held lines carry no --shell-mm / "
                         "--prop-mm and would buy the same four cells at the Sionna default 0.1 m slab."
                         if sup.exists() else None))

    verdicts, md_tables = build_text(gates, queues)
    fs = [C.F[c] for q in queues for cc in [q["cells"]] for x in cc for c in [x["cell"]] if "grammar" in C.F[c]]
    n_pos = sorted({C.get(x["cell"])["n_poses"] for q in queues for x in q["cells"] if x["complete"]})
    common_scope = (
        "PathSolver, drone " + "/".join(sorted({f["drone"] for f in fs})) + ", ranges " +
        "/".join(sorted({str(f["grammar"].get("range_m")) for f in fs})) + " m, rays " +
        "/".join(sorted({f"{int(f['spp']):,}" for f in fs})) + ", switches " +
        "/".join(sorted({f["switches"] for f in fs})) + " (diffuse on, refraction/diffraction off), record lengths " +
        "/".join(f"{n:,}" for n in n_pos) + " positions, max_depth 2 unless the row says d3, cap 2,000,000, "
        "3.5 GHz working assumption, tr38901 as a stand-in (not the six real antennas), flat mirror ground "
        "(scattering coefficient 0), hover at constant rpm, one run per cell except the named seed pairs; "
        "bandwidths 20 / 100 / 200 MHz, Hann range-bin window with the rectangular window as the knob.")
    open_items = [
        "0958: every line is still «#HOLD » - no shard, no sidecar; its readings G and F are not computable, and "
        "runners/jobs_0964_full_scene_30m_thin_slab.txt says it is superseded (the held lines are at the 0.1 m slab).",
        "0959 (a): lines 1-4 (seed 2 of open sky 0 deg at 2e6 and 32e6) are «#HOLD »; the 0952 T threshold from a "
        "seed pair is therefore still unavailable and the 0952 fall is read at one seed only.",
        "0963: lines 74-163 are «#HOLD-rev1 » (mesh revision 1); lines 1-73 are the revision-0 baseline.",
        "env_path_missing is not computable from shards or from these sidecars for the 0957-0963 cells: the existing "
        "path-list ledger outputs/dropout_paths_0916_diff.json covers other cells only.",
        "Nothing here identifies which solver candidate was lost or why, and no absolute level is a radar cross "
        "section (a PathSolver level is not sigma).",
    ]
    git_head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    meta = dict(generator="benchmark/readout_0918.py",
                command='CUDA_VISIBLE_DEVICES="" MPLBACKEND=Agg nice -n 19 taskset -c 8-15 '
                        "/workspace/.venvs/py312/bin/python benchmark/readout_0918.py"
                        + ("" if len(sys.argv) < 2 else " " + " ".join(sys.argv[1:])),
                git_head=git_head, script_sha256=sha256_file(Path(__file__)), created_utc=utc(time.time()),
                inputs=dict(elevation_sweep_md_sha256=sha256_file(SWEEP), sionna_rt=solver_rt_version(),
                            readout_0917_sha256=sha256_file(ROOT / "benchmark" / "readout_0917.py"),
                            bake_outdoor_sha256=sha256_file(Path(BO.__file__)),
                            bake_ground2_sha256=sha256_file(Path(BG.__file__)),
                            stems_cache="outputs/readout_0918_stems.json"),
                queues=list(QUEUES), n_workers_running=len(running), runtime_s=None,
                scope="Stored PathSolver shards and outputs/path_provenance sidecars only.")
    doc = dict(_meta=meta, queues=queues, gates=gates, verdicts=verdicts, md_tables=md_tables,
               common_scope=common_scope, open_items=open_items,
               fields={c: C.F[c] for q in queues for x in q["cells"] for c in [x["cell"]]},
               cells={c: {k: v for k, v in C.rec[c].items() if not k.startswith("_")} for c in C.rec})
    meta["runtime_s"] = round(time.time() - t0, 1)
    text = md(doc)
    for p, payload in ((OUT_JSON, json.dumps(doc, indent=1, default=R7._json_default) + "\n"),
                       (OUT_MD, text + "\n")):
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_text(payload, encoding="utf-8")
        os.replace(tmp, p)
    print(f"wrote {OUT_JSON.relative_to(ROOT)} and {OUT_MD.relative_to(ROOT)} ({meta['runtime_s']} s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
