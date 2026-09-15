#!/usr/bin/env python3
"""read_dropout_paths_0916.py - environment-only paths present at a neighbour pose but missing at an isolated pose.

Reads outputs/dropout_paths_0916.json and outputs/dropout_paths_0916_paths.npz (written by
benchmark/dropout_paths_0916.py) and writes outputs/dropout_paths_0916_diff.json.

For every isolated pose i and each non-isolated computed neighbour j in {i-1, i+1}: the environment-only paths
(class env_only: every interaction on an environment object) of j whose key is absent at i ("missing") and those of i
absent at j ("new"). Path key = the per-interaction sequence (object name, interaction type, primitive index); the
delay is reported, not matched. Control: the same diff between the two neighbours i-1 and i+1 when both are
non-isolated. Simulation bookkeeping only; no RF measurement is involved, and the listing does not say why the
solver omits a path.

    CUDA_VISIBLE_DEVICES="" taskset -c 8 /workspace/.venvs/py312/bin/python -B benchmark/read_dropout_paths_0916.py
"""
from __future__ import annotations

import collections
import datetime as dt
import hashlib
import json
import os
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC_JSON = ROOT / "outputs" / "dropout_paths_0916.json"
SRC_NPZ = ROOT / "outputs" / "dropout_paths_0916_paths.npz"
OUT = ROOT / "outputs" / "dropout_paths_0916_diff.json"
TYPES = {1: "specular", 2: "diffuse", 4: "refraction", 8: "diffraction"}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    with np.load(SRC_NPZ, allow_pickle=False) as zf:
        z = {k: zf[k] for k in zf.files}             # read each array once (NpzFile re-reads on every access)
    d = json.load(open(SRC_JSON, encoding="utf-8"))
    names = [str(x) for x in z["name_table"]]
    cls = [str(x) for x in z["class_names"]]
    off = np.concatenate([[0], np.cumsum(z["n_paths"])])
    index = {(int(c), int(p)): k for k, (c, p) in enumerate(zip(z["rec_cell"], z["rec_pose"]))}

    def env_paths(c: int, p: int) -> dict:
        k = index[(c, p)]
        out: dict = {}
        for q in range(off[k], off[k + 1]):
            if cls[z["path_class"][q]] != "env_only":
                continue
            key = tuple((names[z["object_name_index"][r, q]] if z["object_name_index"][r, q] >= 0 else "?",
                         TYPES.get(int(z["interaction_type"][r, q]), str(int(z["interaction_type"][r, q]))),
                         int(z["primitive"][r, q])) for r in range(int(z["n_interactions"][q])))
            out.setdefault(key, []).append((float(z["tau_s"][q]), complex(z["a_bb"][q])))
        return out

    def describe(items) -> list:
        return [dict(objects=[o for o, _, _ in k], interaction_types=[t for _, t, _ in k],
                     primitives=[pr for _, _, pr in k], n_paths=len(v), tau_s=v[0][0],
                     abs_sum_a=abs(sum(a for _, a in v))) for k, v in items]

    cells = []
    for c, cell in enumerate(d["cells"]):
        poses = {p["pose"]: p for p in cell["poses"]}
        iso = [p["pose"] for p in cell["poses"] if "isolated" in p["roles"]]
        pairs, counts, missing_keys = [], collections.Counter(), collections.Counter()
        for i in iso:
            for j in (i - 1, i + 1):
                if j not in poses or "isolated" in poses[j]["roles"]:
                    continue
                Pi, Pj = env_paths(c, i), env_paths(c, j)
                miss = [(k, v) for k, v in Pj.items() if k not in Pi]
                new = [(k, v) for k, v in Pi.items() if k not in Pj]
                counts[f"missing{len(miss)}_new{len(new)}"] += 1
                for k, _ in miss:
                    missing_keys[json.dumps(k)] += 1
                pairs.append(dict(isolated=i, neighbour=j, missing=describe(miss), new=describe(new)))
        ctrl = collections.Counter()
        for i in iso:
            a, b = i - 1, i + 1
            if a in poses and b in poses and "isolated" not in poses[a]["roles"] and "isolated" not in poses[b]["roles"]:
                Pa, Pb = env_paths(c, a), env_paths(c, b)
                ctrl[f"missing{sum(k not in Pb for k in Pa)}_new{sum(k not in Pa for k in Pb)}"] += 1
        cells.append(dict(arm=cell["arm"], el_deg=cell["el_deg"], n_isolated_listed=len(iso), n_pairs=len(pairs),
                          pair_counts=dict(counts), control_neighbour_pair_counts=dict(ctrl),
                          missing_path_keys_by_pairs=[dict(key=json.loads(k), n_pairs=n)
                                                      for k, n in missing_keys.most_common()],
                          pairs=pairs))
    meta = dict(generator="benchmark/read_dropout_paths_0916.py", created_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                inputs={str(SRC_JSON.relative_to(ROOT)): sha(SRC_JSON), str(SRC_NPZ.relative_to(ROOT)): sha(SRC_NPZ)},
                definitions=dict(env_only="every interaction of the path is on an environment object",
                                 key="per-interaction (object name, interaction type, primitive index); delay not matched",
                                 missing="key present at the neighbour pose and absent at the isolated pose",
                                 new="key present at the isolated pose and absent at the neighbour pose"),
                scope="PathSolver re-solve of production poses; simulation bookkeeping only, no RF measurement; "
                      "does not identify why a path is omitted")
    tmp = OUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(dict(_meta=meta, cells=cells), indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, OUT)
    for cc in cells:
        print(cc["arm"][:70], cc["el_deg"], cc["pair_counts"], "control", cc["control_neighbour_pair_counts"])
        for m in cc["missing_path_keys_by_pairs"][:3]:
            print("   missing", m)


if __name__ == "__main__":
    main()
