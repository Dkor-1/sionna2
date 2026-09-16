#!/usr/bin/env python3
"""dropout_knobs_0916.py - do the isolated poses of a production cell follow the path cap, the solver's
deterministic mode, the ray count or the ray sample set (solver seed)?

Reads the merged fields of the cells bought by runners/jobs_0942_dropout.txt, jobs_0943_seed.txt and
jobs_0944_canyon_seed.txt and reports, per cell, the isolated poses at the ledger's definition
(|E - m| > 20 x median|E - m|, m = component-wise median of E, as in outputs/isac_plan_corpus_0915.json),
their share of the pose-varying power, the Jaccard overlap with the reference cell of the same scene, and
whether one set is contained in another. Simulation bookkeeping only: no RF measurement is involved, and this
does not say why the solver omits a path at those poses (benchmark/dropout_paths_0916.py lists the paths).

    CUDA_VISIBLE_DEVICES="" taskset -c 8 /workspace/.venvs/py312/bin/python -B benchmark/dropout_knobs_0916.py
"""
from __future__ import annotations

import datetime as dt
import glob
import hashlib
import json
import os
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SH = ROOT / "outputs" / "elev_sweep_shards"
OUT = ROOT / "outputs" / "dropout_knobs_0916.json"
FACTOR = 20.0
BASE = "sionna_p{spp}_swR0D0E0F1_r15_n8192_{tag}mfixbatteryi5_blperairframe_rt210_d2_el-60"

CELLS = [
    # (name, scene group, stem)
    ("ground reference (4e9 rays, cap 2e6, seed 1)", "ground", BASE.format(spp=4000000000, tag="envoutdoor01_ground_")),
    ("ground repeat of the reference", "ground", BASE.format(spp=4000000000, tag="rep1_envoutdoor01_ground_")),
    ("ground solver seed 2", "ground", BASE.format(spp=4000000000, tag="envoutdoor01_ground_ss2_")),
    ("ground solver seed 3", "ground", BASE.format(spp=4000000000, tag="envoutdoor01_ground_ss3_")),
    ("ground path cap 1e6", "ground", BASE.format(spp=4000000000, tag="envoutdoor01_ground_mp1000000_")),
    ("ground path cap 8e6", "ground", BASE.format(spp=4000000000, tag="envoutdoor01_ground_mp8000000_")),
    ("ground path cap 16e6", "ground", BASE.format(spp=4000000000, tag="envoutdoor01_ground_mp16000000_")),
    ("ground path cap 32e6", "ground", BASE.format(spp=4000000000, tag="envoutdoor01_ground_mp32000000_")),
    ("ground 3e9 rays", "ground", BASE.format(spp=3000000000, tag="envoutdoor01_ground_")),
    ("ground 2e9 rays", "ground", BASE.format(spp=2000000000, tag="envoutdoor01_ground_")),
    ("ground 2e8 rays", "ground", BASE.format(spp=200000000, tag="envoutdoor01_ground_")),
    ("ground 2e8 rays, solver deterministic", "ground", BASE.format(spp=200000000, tag="envoutdoor01_ground_sdet_")),
    ("free sky seed 1", "free_sky", BASE.format(spp=4000000000, tag="")),
    ("free sky seed 2", "free_sky", BASE.format(spp=4000000000, tag="ss2_")),
    ("street canyon reference", "canyon", BASE.format(spp=4000000000, tag="envsionna-simple_street_canyon_")),
    ("street canyon path cap 8e6", "canyon",
     BASE.format(spp=4000000000, tag="envsionna-simple_street_canyon_mp8000000_")),
    ("street canyon path cap 16e6", "canyon",
     BASE.format(spp=4000000000, tag="envsionna-simple_street_canyon_mp16000000_")),
    ("street canyon path cap 32e6", "canyon",
     BASE.format(spp=4000000000, tag="envsionna-simple_street_canyon_mp32000000_")),
    ("street canyon solver seed 2", "canyon",
     BASE.format(spp=4000000000, tag="envsionna-simple_street_canyon_ss2_")),
    ("street canyon el -30 reference", "canyon_el30",
     BASE.format(spp=4000000000, tag="envsionna-simple_street_canyon_").replace("el-60", "el-30")),
    ("street canyon el -30 path cap 8e6", "canyon_el30",
     BASE.format(spp=4000000000, tag="envsionna-simple_street_canyon_mp8000000_").replace("el-60", "el-30")),
    ("street canyon el -30 solver seed 2", "canyon_el30",
     BASE.format(spp=4000000000, tag="envsionna-simple_street_canyon_ss2_").replace("el-60", "el-30")),
]
#: reference cell per scene group, by name (indices shifted when rungs were added)
REFERENCE_NAME = {"ground": "ground reference (4e9 rays, cap 2e6, seed 1)",
                  "free_sky": "free sky seed 1",
                  "canyon": "street canyon reference",
                  "canyon_el30": "street canyon el -30 reference"}
REFERENCE = {g: [i for i, c in enumerate(CELLS) if c[0] == n][0] for g, n in REFERENCE_NAME.items()}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def merge(stem: str):
    """Merged field of one cell, or (None, reason). Every pose must be covered exactly once."""
    files = sorted(Path(p) for p in glob.glob(str(SH / f"{stem}_0*.npz")))
    if not files:
        return None, "no shard"
    E, npaths, nret, builds, hashes = {}, {}, {}, set(), {}
    for f in files:
        with np.load(f) as z:
            if "E" not in z.files or "idx" not in z.files:
                return None, f"{f.name}: no E/idx"
            idx = z["idx"].astype(np.int64).ravel()
            for i, v in zip(idx, z["E"].ravel()):
                if int(i) in E:
                    return None, f"pose {int(i)} in more than one shard"
                E[int(i)] = complex(v)
            if "npaths" in z.files:
                for i, v in zip(idx, np.asarray(z["npaths"]).ravel()):
                    npaths[int(i)] = int(v)
            if "nret" in z.files:
                for i, v in zip(idx, np.asarray(z["nret"]).ravel()):
                    nret[int(i)] = int(v)
            builds.add(str(z["solver_build"]) if "solver_build" in z.files else "unknown")
        hashes[f.name] = sha256_file(f)
    n = max(E) + 1
    if len(E) != n:
        return None, f"{n - len(E)} poses missing"
    if len(builds) != 1:
        return None, f"shards disagree on solver build {sorted(builds)}"
    return dict(E=np.array([E[i] for i in range(n)]),
                npaths=np.array([npaths.get(i, -1) for i in range(n)]),
                nret=np.array([nret.get(i, -1) for i in range(n)]),
                solver_build=builds.pop(), shards=hashes), None


def isolated(E: np.ndarray, k: float = FACTOR):
    m = complex(np.median(E.real), np.median(E.imag))
    d = np.abs(E - m)
    sc = float(np.median(d))
    mask = d > k * sc if sc > 0 else np.zeros(E.size, bool)
    return np.flatnonzero(mask), m, sc


def g4(x):
    return None if x is None else float(f"{float(x):.4g}")


def jaccard(a, b):
    a, b = set(map(int, a)), set(map(int, b))
    if not a and not b:
        return None
    return len(a & b) / len(a | b)


def main() -> None:
    rows, sets = [], {}
    for k, (name, group, stem) in enumerate(CELLS):
        cell, why = merge(stem)
        if cell is None:
            rows.append(dict(name=name, group=group, stem=stem, available=False, reason=why))
            print(f"{name:42} unavailable ({why})")
            continue
        E = cell["E"]
        idx, m, sc = isolated(E)
        sets[k] = idx
        share = (float(np.sum(np.abs(E[idx] - m) ** 2) / np.sum(np.abs(E - m) ** 2)) if idx.size else None)
        npm = cell["npaths"]
        rows.append(dict(
            name=name, group=group, stem=stem, available=True, solver_build=cell["solver_build"],
            n_poses=int(E.size), n_isolated=int(idx.size), isolated_pose_indices=[int(x) for x in idx[:64]],
            isolated_indices_truncated=bool(idx.size > 64),
            share_of_pose_varying_power=g4(share),
            abs_complex_median=g4(abs(m)), median_abs_dev=g4(sc),
            npaths_median=int(np.median(npm)) if npm.max() > 0 else None,
            npaths_max=int(npm.max()) if npm.max() > 0 else None,
            shard_sha256=cell["shards"]))
        print(f"{name:42} isolated {idx.size:4d}  share {g4(share)}  npaths median/max "
              f"{rows[-1]['npaths_median']}/{rows[-1]['npaths_max']}")
    comps = []
    for k, (name, group, _s) in enumerate(CELLS):
        r = REFERENCE[group]
        if k == r or k not in sets or r not in sets:
            continue
        a, b = set(map(int, sets[k])), set(map(int, sets[r]))
        comps.append(dict(cell=name, reference=CELLS[r][0], jaccard=g4(jaccard(sets[k], sets[r])),
                          n_cell=len(a), n_reference=len(b), n_common=len(a & b),
                          cell_is_subset_of_reference=bool(a and a <= b),
                          reference_is_subset_of_cell=bool(b and b <= a)))
        print(f"  vs reference: {name:40} J={comps[-1]['jaccard']} common {len(a & b)} "
              f"subset={comps[-1]['cell_is_subset_of_reference']}")
    pairs = []
    idx = {c[0]: k for k, c in enumerate(CELLS)}
    PAIRS = [("ground 2e8 rays", "ground 2e8 rays, solver deterministic", "deterministic mode off vs on at 2e8 rays"),
             ("ground solver seed 2", "ground solver seed 3", "solver seed 2 vs seed 3"),
             ("ground path cap 1e6", "ground path cap 8e6", "path cap 1e6 vs 8e6"),
             ("ground path cap 8e6", "ground path cap 16e6", "path cap 8e6 vs 16e6"),
             ("ground path cap 16e6", "ground path cap 32e6", "path cap 16e6 vs 32e6"),
             ("ground reference (4e9 rays, cap 2e6, seed 1)", "ground repeat of the reference",
              "reference vs its same-seed repeat"),
             ("street canyon reference", "street canyon solver seed 2", "street canyon: reference vs solver seed 2"),
             ("street canyon path cap 8e6", "street canyon path cap 16e6", "street canyon: cap 8e6 vs 16e6"),
             ("street canyon path cap 16e6", "street canyon path cap 32e6", "street canyon: cap 16e6 vs 32e6"),
             ("street canyon el -30 reference", "street canyon el -30 solver seed 2",
              "street canyon el -30: reference vs solver seed 2"),
             ("street canyon el -30 reference", "street canyon el -30 path cap 8e6",
              "street canyon el -30: reference vs path cap 8e6")]
    for a_name, b_name, why in PAIRS:
        i, j = idx[a_name], idx[b_name]
        if i in sets and j in sets:
            a, b = set(map(int, sets[i])), set(map(int, sets[j]))
            pairs.append(dict(pair=why, a=CELLS[i][0], b=CELLS[j][0], jaccard=g4(jaccard(sets[i], sets[j])),
                              n_a=len(a), n_b=len(b), identical=bool(a == b),
                              b_subset_of_a=bool(b and b <= a)))
            print(f"  pair: {why:42} J={pairs[-1]['jaccard']} identical={pairs[-1]['identical']}")
    # ---- field stability: does the cap change anything outside the isolated poses? -------------
    stab = []
    ref_cell, _ = merge(CELLS[REFERENCE["ground"]][2])
    if ref_cell is not None:
        Er = ref_cell["E"]
        iso_r, _, _ = isolated(Er)
        med = float(np.median(np.abs(Er)))
        for name, group, stem in CELLS:
            if group != "ground" or name == CELLS[REFERENCE["ground"]][0]:
                continue
            cell, _why = merge(stem)
            if cell is None or cell["E"].size != Er.size:
                continue
            E = cell["E"]
            idx, _m, _s = isolated(E)
            union = set(map(int, idx)) | set(map(int, iso_r))
            keep = np.array([i for i in range(E.size) if i not in union])
            npm = cell["npaths"]
            stab.append(dict(cell=name, n_isolated=int(idx.size),
                             max_abs_diff_over_median_all=g4(np.abs(E - Er).max() / med),
                             max_abs_diff_over_median_outside_isolated=g4(np.abs(E[keep] - Er[keep]).max() / med),
                             n_poses_compared_outside_isolated=int(keep.size),
                             npaths_median=int(np.median(npm)) if npm.max() > 0 else None,
                             npaths_max=int(npm.max()) if npm.max() > 0 else None))
            print(f"  stability: {name:42} outside the isolated poses max|dE|/median|E| = "
                  f"{stab[-1]['max_abs_diff_over_median_outside_isolated']}")
    meta = dict(generator="benchmark/dropout_knobs_0916.py",
                created_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                factor=FACTOR,
                definitions=dict(
                    isolated_pose="|E - m| > 20 x median_over_poses(|E - m|), m = component-wise median of E "
                                  "(same definition as outputs/isac_plan_corpus_0915.json : dropout)",
                    share_of_pose_varying_power="sum of |E - m|^2 over the isolated poses / sum over all poses",
                    jaccard="|A and B| / |A or B| of two isolated-pose index sets"),
                scope="Merged production PathSolver cells (outdoor scenes, isotropic antenna, depth 2, el -60). "
                      "Simulation bookkeeping only: no RF measurement, no comparison of absolute levels between "
                      "engines, and no statement about why a path is missing.",
                max_paths_caveat="--max-paths sets both the candidate buffer (max_num_paths_per_src x num_sources) "
                                 "and the specular-chain hash counter size, max(max_num_paths_per_src, 1e6), in "
                                 "sionna/rt/path_solvers/sb_candidate_generator.py (lines 107, 59, 313-315); that "
                                 "generator's docstring says candidates can be lost to hash collisions. So a row "
                                 "labelled 'path cap N' moves two things at once, and the returned path count "
                                 "staying far below the cap does not show that nothing was dropped earlier. The "
                                 "rows below support 'raising --max-paths reduces the isolated poses in these "
                                 "cells' and nothing about which of the two effects does it.")
    meta["definitions"]["field_stability"] = (
        "per cell of the ground group: max |E - E_reference| / median |E_reference|, over all poses and over the "
        "poses that are isolated in neither cell. The second number says whether the knob changed anything "
        "outside the isolated poses.")
    tmp = OUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(dict(_meta=meta, cells=rows, vs_reference=comps, pairs=pairs,
                                   field_stability=stab), indent=1) + "\n",
                   encoding="utf-8")
    os.replace(tmp, OUT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
