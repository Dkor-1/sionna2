# -*- coding: utf-8 -*-
"""
hash_bucket_stat_0903.py — 흔들림을 «폭» 이 아니라 «발생률» 로 잰다.

왜 다시 재나
    `hash_bucket_sweep_0903.py` 를 판 6 개로 돌리니 통 수에 **단조가 아니었다**
    (1M 흔들림 · 2~8M 깨끗 · 16M 흔들림 · 32M 깨끗). ⛔그것을 「통 수는 안 듣는다」로
    읽으면 안 된다 — 흔들림이 **드문 사건**이라 판 6 개로는 순위를 못 매긴다.
    드문 사건은 폭이 아니라 **발생률**로 재야 한다.

무엇을 재나
    설정마다 판을 많이 돌려
      · 경로 수의 **최빈값**과, 최빈값과 다른 판의 **비율**  ← 이것이 발생률이다
      · 합 |h| 가 최빈값 판과 다른 판의 비율
      · 흔들릴 때의 폭 [dB]
    통 수(spec_counter_size)와 후보 수(samples_per_src) 두 축에서 이 발생률을 견준다.

⭐대조군이 핵심이다 — CPU(llvm) 판에는 **GPU 스레드 순서가 없다.**
  그래도 흔들리면 원인은 «순서» 가 아니라 **해시 충돌 자체**다.

⛔판정하지 않는다 — 수만 낸다(주장 게이트 ⓑ).

쓰는 법
    CUDA_VISIBLE_DEVICES="" PYTHONPATH=src:benchmark OMP_NUM_THREADS=6 \\
        ~/.venvs/py312/bin/python benchmark/hash_bucket_stat_0903.py --reps 30
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import re
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
OUT = os.path.join(ROOT, "outputs", "hash_bucket_stat_0903.json")


def bucket_floor() -> int | None:
    """설치본에서 통 수의 바닥값을 읽는다 — `MIN_SPEC_COUNT_SIZE = int(1e6)` 꼴이다."""
    try:
        import sionna.rt.path_solvers.sb_candidate_generator as m
        src = open(m.__file__, encoding="utf-8").read()
        g = re.search(r"MIN_SPEC_COUNT_SIZE\s*=\s*(?:int\()?\s*([0-9_.eE+]+)", src)
        return int(float(g.group(1))) if g else None
    except Exception:
        return None


def n_hash_fns() -> int | None:
    """해시 함수가 몇 개인지 — 충돌 확률이 이 수만큼 거듭제곱된다."""
    try:
        import sionna.rt.path_solvers.sb_candidate_generator as m
        src = open(m.__file__, encoding="utf-8").read()
        g = re.search(r"self\.plane_hash_functions\s*=\s*\[(.*?)\]", src, re.S)
        return g.group(1).count("Hasher(") if g else None
    except Exception:
        return None


def stat(ns: list[int], hs: list[float]) -> dict:
    """최빈값에서 벗어난 판의 비율 = 발생률."""
    mode_n = collections.Counter(ns).most_common(1)[0][0]
    off_n = [i for i, v in enumerate(ns) if v != mode_n]
    ref = float(np.median([hs[i] for i in range(len(hs)) if ns[i] == mode_n]))
    dev = [abs(20 * np.log10(h / ref)) for h in hs if h > 0 and ref > 0]
    return dict(n_reps=len(ns), mode_paths=int(mode_n),
                n_off=len(off_n), rate_off=round(len(off_n) / len(ns), 4),
                paths_seen=sorted(set(ns)),
                max_dev_db=round(float(max(dev)) if dev else 0.0, 5),
                n_dev_over_0p1db=int(sum(1 for d in dev if d > 0.1)))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=30)
    ap.add_argument("--n-side", type=int, default=24)
    ap.add_argument("--scat", type=float, default=0.7)
    ap.add_argument("--samples", type=int, default=40_000_000,
                    help="통 수 축을 볼 때 쓸 광선 수 — 흔들림이 보이는 자리로 잡는다")
    a = ap.parse_args()

    from minrepro_hash_0902 import build, probe
    import mitsuba as mi
    import sionna.rt as _rt                                   # noqa: F401

    variant, floor, nh = mi.variant(), bucket_floor(), n_hash_fns()
    print("⭐흔들림 발생률 — 드문 사건이라 폭 대신 비율로 잰다\n")
    print(f"  변형 {variant}"
          f"{'  ⭐CPU — GPU 스레드 순서가 없는 대조군' if variant.startswith('llvm') else '  (GPU)'}")
    print(f"  평판 {a.n_side**2} · 산란 {a.scat} · 판 {a.reps} · 통 바닥 "
          f"{f'{floor:,}' if floor else '?'} · 해시 함수 {nh}")

    sc, nf = build(a.n_side, a.scat)
    rows, t0 = [], time.time()

    print(f"\n  ── 축 1. 통 수 (광선 {a.samples:,} 고정) ──")
    print(f"  {'통 수':>12} {'최빈 경로':>10} {'흔들린 판':>10} {'발생률':>8} "
          f"{'최대 편차 dB':>12} {'본 경로 수':>16}")
    for B in (1_000_000, 2_000_000, 4_000_000, 8_000_000, 16_000_000, 32_000_000):
        ns, hs = probe(sc, a.reps, samples_per_src=a.samples, max_num_paths_per_src=B)
        s = stat(ns, hs)
        s.update(axis="buckets", buckets=B, samples_per_src=a.samples)
        rows.append(s)
        print(f"  {B:12,} {s['mode_paths']:10d} {s['n_off']:10d} {s['rate_off']:8.3f} "
              f"{s['max_dev_db']:12.5f} {str(s['paths_seen'])[:16]:>16}")

    print(f"\n  ── 축 2. 후보 수 (통 {2_000_000:,} 고정) ──")
    print(f"  {'광선 수':>12} {'최빈 경로':>10} {'흔들린 판':>10} {'발생률':>8} "
          f"{'최대 편차 dB':>12} {'본 경로 수':>16}")
    for S in (10_000_000, 20_000_000, 40_000_000, 80_000_000):
        ns, hs = probe(sc, a.reps, samples_per_src=S, max_num_paths_per_src=2_000_000)
        s = stat(ns, hs)
        s.update(axis="samples", buckets=2_000_000, samples_per_src=S)
        rows.append(s)
        print(f"  {S:12,} {s['mode_paths']:10d} {s['n_off']:10d} {s['rate_off']:8.3f} "
              f"{s['max_dev_db']:12.5f} {str(s['paths_seen'])[:16]:>16}")

    json.dump({"_meta": {
        "generator": "benchmark/hash_bucket_stat_0903.py",
        "question_ko": "흔들림의 발생률이 통 수와 후보 수를 어떻게 따라가나",
        "why_rate_ko": "흔들림은 드문 사건이라 판 몇 개의 «폭» 으로는 순위를 못 매긴다.",
        "scene_ko": f"합성 평판 {a.n_side**2} 장(삼각형 {nf}) · 산란 {a.scat} · 회절 끔 · 깊이 2 · 씨앗 고정",
        "mitsuba_variant": variant,
        "variant_note_ko": ("llvm 이면 CPU 판 — GPU 스레드 순서가 없는 대조군이다. "
                            "여기서도 흔들리면 원인이 «순서» 가 아니라는 뜻이다."),
        "min_spec_count_size": floor, "n_hash_functions": nh,
        "seconds": round(time.time() - t0, 1),
        "reads_ko": "⛔판정은 여기 적지 않는다 — 표를 보고 사람이 쓴다(주장 게이트 ⓑ).",
    }, "rows": rows}, open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"\n  ✅ {os.path.relpath(OUT, ROOT)}  ({time.time()-t0:.0f} 초)")


if __name__ == "__main__":
    main()
