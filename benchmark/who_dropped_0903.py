# -*- coding: utf-8 -*-
"""
who_dropped_0903.py — 깊은 낙차에서 **누가 버렸나** 를 가른다.

물음
    `docs/DEEP_DROP_0902.md` ⓔ 가 열어 둔 것: 「PathSolver 가 못 찾았다」와
    「돌려줬는데 우리 하네스가 버렸다」의 **서명이 똑같다.**
    `elevation_sweep_md.py:695-707` 이 `O != NO_OBJ` 로 거른 뒤에야 합과 `npaths` 를 내므로,
    옛 샤드만으로는 둘을 못 가른다.

    ⭐2026-09-02 에 `nret`(마스크 **전**, 돌려받은 경로 수)을 샤드에 함께 적게 했다.
      그것을 담은 샤드에서는 이렇게 갈린다:

        nret ≈ npaths  → 솔버가 애초에 그 경로를 **안 돌려줬다** (우리 탓 아님)
        nret >  npaths → 솔버는 돌려줬는데 **우리 마스크가 버렸다** (우리 탓)

무엇을 하나
    nret 을 담은 샤드를 모두 열어, 그 팔·앙각의 **깊은 낙차 자세**(|E| 가 중앙값의 10 % 아래)를
    찾고, 그 자세에서 nret 과 npaths 를 견준다. 낙차 자세와 정상 자세를 나란히 낸다.

⛔판정하지 않는다 — 수를 내고, 문장은 사람이 쓴다(주장 게이트 ⓑ).

쓰는 법
    CUDA_VISIBLE_DEVICES="" PYTHONPATH=src \\
        ~/.venvs/py312/bin/python benchmark/who_dropped_0903.py
"""
from __future__ import annotations

import collections
import glob
import json
import os
import re

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SHD = os.path.join(ROOT, "outputs", "elev_sweep_shards")
OUT = os.path.join(ROOT, "outputs", "who_dropped_0903.json")

NAME = re.compile(r"^(?P<arm>.+)_el(?P<el>[+-][\d.]+)_(?P<sh>\d+)\.npz$")
DEEP = 0.1          # |E| 가 중앙값의 이 비율 아래면 «깊은 낙차»


def main() -> None:
    #: (팔, 앙각) 마다 샤드를 이어 붙인다 — nret 이 있는 것만.
    bucket: dict[tuple[str, float], list] = collections.defaultdict(list)
    n_files = n_with = 0
    for f in glob.glob(os.path.join(SHD, "*.npz")):
        n_files += 1
        m = NAME.match(os.path.basename(f))
        if not m:
            continue
        try:
            z = np.load(f)
        except Exception:
            continue
        if "nret" not in z.files:
            continue
        n_with += 1
        bucket[(m.group("arm"), float(m.group("el")))].append(
            (z["idx"], z["E"], z["npaths"], z["nret"]))

    cells, tot_deep, tot_ours = [], 0, 0
    for (arm, el), parts in sorted(bucket.items()):
        idx = np.concatenate([p[0] for p in parts])
        E = np.concatenate([p[1] for p in parts])
        npa = np.concatenate([p[2] for p in parts])
        nre = np.concatenate([p[3] for p in parts])
        o = np.argsort(idx)
        E, npa, nre = E[o], npa[o], nre[o]

        a = np.abs(E)
        med = float(np.median(a))
        if med <= 0:
            continue
        deep = np.where(a / med < DEEP)[0]
        if deep.size == 0:
            continue
        norm = np.setdiff1d(np.arange(a.size), deep)

        #: ⭐가르는 수 — 낙차 자세에서 «돌려받았는데 버린» 경로가 몇 개인가.
        masked_deep = int(np.sum((nre - npa)[deep]))
        masked_norm = int(np.sum((nre - npa)[norm])) if norm.size else 0
        n_ours = int(np.sum((nre > npa)[deep]))
        tot_deep += int(deep.size)
        tot_ours += n_ours

        cells.append(dict(
            arm=arm, el_deg=el, n_poses=int(a.size), n_deep=int(deep.size),
            npaths_median_normal=float(np.median(npa[norm])) if norm.size else None,
            npaths_median_deep=float(np.median(npa[deep])),
            nret_median_normal=float(np.median(nre[norm])) if norm.size else None,
            nret_median_deep=float(np.median(nre[deep])),
            masked_paths_in_deep=masked_deep,
            masked_paths_in_normal=masked_norm,
            n_deep_poses_where_we_masked=n_ours,
        ))

    cells.sort(key=lambda c: -c["n_deep"])
    print(f"═══ 샤드 {n_files} 장 중 nret 있는 것 {n_with} 장 · "
          f"낙차가 있는 칸 {len(cells)} ═══\n")
    print(f"  {'조합·앙각':46s} {'낙차':>5s} {'경로중앙(정상)':>13s} {'경로중앙(낙차)':>13s} "
          f"{'우리가 버린 경로':>15s}")
    for c in cells[:20]:
        tag = f"{c['arm'][-38:]} el{c['el_deg']:+.0f}"
        print(f"  {tag:46s} {c['n_deep']:5d} "
              f"{c['npaths_median_normal'] or 0:13.0f} {c['npaths_median_deep']:13.0f} "
              f"{c['masked_paths_in_deep']:15d}")
    if len(cells) > 20:
        print(f"  … 외 {len(cells) - 20} 칸")

    print(f"\n  ⭐낙차 자세 {tot_deep} 개 가운데 **우리 마스크가 경로를 버린 자세**: {tot_ours} 개")

    json.dump({"_meta": {
        "generator": "benchmark/who_dropped_0903.py",
        "question_ko": "깊은 낙차에서 경로가 «안 돌아온 것» 인가 «돌아왔는데 우리가 버린 것» 인가",
        "how_ko": "샤드의 nret(마스크 전)과 npaths(마스크 후)를 낙차 자세에서 견준다. "
                  "nret > npaths 면 우리 하네스가 버린 것이고, 같으면 솔버가 안 준 것이다.",
        "deep_rule_ko": f"|E| < 중앙값 × {DEEP}",
        "n_shards_with_nret": n_with, "n_shards_total": n_files,
        "verdict_ko": "⛔여기서 판정하지 않는다 — 수만 낸다(주장 게이트 ⓑ).",
    }, "cells": cells,
        "summary": dict(n_deep_poses=tot_deep, n_deep_poses_we_masked=tot_ours)},
        open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"  ✅ {os.path.relpath(OUT, ROOT)}")


if __name__ == "__main__":
    main()
