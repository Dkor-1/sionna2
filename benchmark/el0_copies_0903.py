# -*- coding: utf-8 -*-
"""
el0_copies_0903.py — 0° 낙차의 «벌 수 N» 이 기체마다 다른가.

여기까지 갈린 것
    matrice4e · el 0° 에서 낙차 깊이가 **정확히 2/3** 이고, 경로 목록을 열어 보니
    진폭·지연·정점이 **똑같은 «정반사 → 카메라»** 항목이 **셋**이었다.
    3 × 2.298327e−04 = |E| 이므로, 셋 중 하나가 빠지면 2/3 다.

⭐이 스크립트가 묻는 것
    기체를 바꾸면 그 **벌 수 N** 이 달라지나. 낙차 깊이는 (N−1)/N 이므로,
    깊이만 재도 N 을 읽을 수 있다 — 솔버를 안 돌리고 디스크로 답한다.

무엇을 재나
    기체·팔마다 el 0° 기록에서
      · 낙차 깊이 \\|E\\|/중앙 의 **뭉치는 자리**
      · 그 자리에서 읽은 N = 1 / (1 − 깊이)
      · N 이 정수에 얼마나 가까운지 (가까우면 «벌 수» 읽기가 선다)

⛔판정하지 않는다 — 수를 내고 문장은 사람이 쓴다(주장 게이트 ⓑ).

쓰는 법
    CUDA_VISIBLE_DEVICES="" ~/.venvs/py312/bin/python benchmark/el0_copies_0903.py
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
OUT = os.path.join(ROOT, "outputs", "el0_copies_0903.json")
THR = 0.9                       # 덱 그림의 규칙


def airframe(arm: str) -> str:
    for k in ("mavic4pro", "mini5pro", "s1000plus", "matrice4e"):
        if k in arm:
            return k
    return "matrice4e(기본)"      # 꼬리표가 없으면 기본 기체다


def main() -> None:
    #: el 0 샤드를 팔별로 모은다
    by = collections.defaultdict(list)
    for f in glob.glob(os.path.join(SHD, "*_el+0_*.npz")):
        m = re.match(r"^(.+)_el\+0_\d+\.npz$", os.path.basename(f))
        if m:
            by[m.group(1)].append(f)

    rows = []
    for arm, fs in sorted(by.items()):
        i, e = [], []
        for f in sorted(fs):
            try:
                z = np.load(f)
            except Exception:
                continue
            i.append(z["idx"]); e.append(z["E"])
        if not i:
            continue
        i = np.concatenate(i); e = np.concatenate(e)
        o = np.argsort(i); a = np.abs(e[o])
        if a.size < 1000:
            continue
        med = float(np.median(a))
        if med <= 0:
            continue
        r = a / med
        d = r[r < THR]
        if d.size < 5:
            continue
        #: 깊이가 한 값에 뭉치나 — 표준편차가 작아야 «벌 수» 읽기가 선다
        q1, q3 = np.percentile(d, [25, 75])
        core = d[(d >= q1 - 1e-3) & (d <= q3 + 1e-3)]
        depth = float(np.median(core))
        N = 1.0 / (1.0 - depth) if depth < 1 else float("inf")
        rows.append(dict(arm=arm, airframe=airframe(arm), n_poses=int(a.size),
                         n_drop=int(d.size), frac=round(100 * d.size / a.size, 2),
                         depth_median=round(depth, 5),
                         depth_iqr=round(float(q3 - q1), 5),
                         N_read=round(N, 3), N_round=int(round(N)),
                         N_gap=round(abs(N - round(N)), 4)))

    rows.sort(key=lambda x: (x["airframe"], -x["n_drop"]))
    print(f"⭐문턱 |E|/중앙 < {THR} (덱 그림 규칙) · el 0° 기록 {len(rows)} 팔\n")
    print(f"  {'기체':16s} {'낙차%':>6s} {'깊이(중앙)':>10s} {'IQR':>8s} "
          f"{'N=1/(1−깊이)':>12s} {'정수와 차':>9s}  팔")
    for x in rows:
        flag = "⭐" if x["N_gap"] < 0.05 else "  "
        print(f"{flag}{x['airframe']:16s} {x['frac']:6.2f} {x['depth_median']:10.5f} "
              f"{x['depth_iqr']:8.5f} {x['N_read']:12.3f} {x['N_gap']:9.4f}  {x['arm'][:52]}")

    print("\n═══ 기체별 모음 (정수에 가까운 것만) ═══")
    g = collections.defaultdict(list)
    for x in rows:
        if x["N_gap"] < 0.05:
            g[x["airframe"]].append(x)
    for af, xs in sorted(g.items()):
        Ns = sorted({x["N_round"] for x in xs})
        dep = [x["depth_median"] for x in xs]
        print(f"  {af:16s} 팔 {len(xs):2d} · N = {Ns} · "
              f"깊이 {min(dep):.4f}~{max(dep):.4f}")

    json.dump({"_meta": {
        "generator": "benchmark/el0_copies_0903.py",
        "question_ko": "0° 낙차의 «벌 수 N» 이 기체마다 다른가",
        "how_ko": "낙차 깊이 = (N−1)/N 이므로 N = 1/(1−깊이). 깊이가 한 값에 뭉칠 때만 읽는다.",
        "threshold_ko": f"|E| / 중앙값 < {THR}",
        "reads_ko": "⛔판정은 여기 적지 않는다 — 표를 보고 사람이 쓴다(주장 게이트 ⓑ).",
    }, "rows": rows}, open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"\n  ✅ {os.path.relpath(OUT, ROOT)}")


if __name__ == "__main__":
    main()
