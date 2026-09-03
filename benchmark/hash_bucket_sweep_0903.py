# -*- coding: utf-8 -*-
"""
hash_bucket_sweep_0903.py — 해시 통 수를 흔들면 낙차가 줄어드나.

물음
    `docs/DEEP_DROP_0902.md` 의 «다음» 2 번: 「max_num_paths_per_src 를 키워 해시 충돌을
    줄이면 얕은 계단이 줄어드나」. 기전 가설이 옳다면 **통이 많아질수록 유실이 줄어야** 한다.

기전 (설치본이 스스로 적어 둔 것)
    `sb_candidate_generator.py` 서문 43~45 — 「경로의 유일성을 해시로 보장한다.
    ⚠**해시 충돌 때문에 후보가 유실될 수 있다**」
    55~57 — 「이 배열은 충돌이 드물고 **후보가 충돌로 버려지지 않을 만큼** 커야 한다」
    통 수는 `spec_counter_size = max(max_num_paths_per_src, MIN_SPEC_COUNT_SIZE)` 다.

⚠**설계상의 함정** — `MIN_SPEC_COUNT_SIZE` 가 바닥이라, 그 아래로 내리면 **아무 일도 안 난다.**
  그래서 이 훑기는 바닥 **위로만** 흔든다. 바닥값은 실행 때 소스에서 읽어 함께 적는다.

무엇을 재나
    같은 씬·같은 씨앗으로 여러 판 돌려
      · n_paths 가 판마다 흔들리는 폭(종류 수 · 최대−최소)
      · 합 |h| 의 판 사이 폭 [dB]           ← 이것이 «낙차» 의 최소 재현판이다
    통 수를 바꿔 가며 이 둘이 **단조로 줄어드는지** 본다.
    ⭐대조축 — `samples_per_src`(후보 수를 바꾼다)도 함께 흔든다.
      충돌 가설이면 «후보 많을수록 나빠지고, 통 많을수록 좋아져야» 한다.

⛔판정하지 않는다 — 수를 내고 문장은 사람이 쓴다(주장 게이트 ⓑ).

쓰는 법
    CUDA_VISIBLE_DEVICES=<하나> PYTHONPATH=src \\
        ~/.venvs/py312/bin/python benchmark/hash_bucket_sweep_0903.py --reps 8
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

OUT = os.path.join(ROOT, "outputs", "hash_bucket_sweep_0903.json")
FC = 3.5e9
SEED = 1


def min_counter_size() -> int | None:
    """설치본에서 통 수의 **바닥값**을 읽어 온다 — 손으로 적지 않는다."""
    try:
        import sionna.rt.path_solvers.sb_candidate_generator as m
        src = open(m.__file__, encoding="utf-8").read()
        g = re.search(r"MIN_SPEC_COUNT_SIZE\s*=\s*([0-9_eE.+]+)", src)
        return int(float(g.group(1))) if g else None
    except Exception:
        return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=8, help="통 수마다 몇 판")
    ap.add_argument("--n-side", type=int, default=24, help="평판 격자 한 변")
    ap.add_argument("--scat", type=float, default=0.7, help="산란계수")
    a = ap.parse_args()

    from minrepro_hash_0902 import build, probe        # 최소 재현기를 그대로 쓴다

    import mitsuba as mi
    import sionna.rt as _rt                                   # noqa: F401  (변형을 정하게 한다)
    variant = mi.variant()
    floor = min_counter_size()
    print("⭐해시 통 수 훑기 — 같은 씬·같은 씨앗, 통 수만 바꾼다\n")
    print(f"  미츠바 변형 = {variant}"
          f"{'  (CPU — GPU 스레드 순서가 빠진 판)' if variant.startswith('llvm') else '  (GPU)'}")
    print(f"  평판 {a.n_side**2} 장 · 산란 {a.scat} · 판 {a.reps} · 씨앗 {SEED}")
    print(f"  통 수 바닥(MIN_SPEC_COUNT_SIZE) = "
          f"{f'{floor:,}' if floor else '⚠소스에서 못 읽음'}")
    print("  ⛔바닥 아래로는 아무 효과가 없다 — 위로만 흔든다\n")

    sc, nf = build(a.n_side, a.scat)
    rows = []

    BUCKETS = [1_000_000, 2_000_000, 4_000_000, 8_000_000, 16_000_000, 32_000_000]
    print(f"  {'통 수':>12} {'경로 수 종류':>13} {'경로 최대−최소':>14} {'|h| 폭 dB':>11}")
    for B in BUCKETS:
        ns, hs = probe(sc, a.reps, max_num_paths_per_src=B)
        spread = (20 * np.log10(max(hs) / min(hs))) if min(hs) > 0 else float("nan")
        rows.append(dict(axis="buckets", buckets=B, samples_per_src=20_000_000,
                         n_reps=a.reps, n_paths=sorted(set(ns)),
                         n_kinds=len(set(ns)), n_span=int(max(ns) - min(ns)),
                         h_spread_db=round(float(spread), 5)))
        print(f"  {B:12,} {len(set(ns)):13d} {max(ns)-min(ns):14d} {spread:11.5f}")

    print(f"\n  ⭐대조축 — 후보 수(samples_per_src)를 흔든다 (통 수는 2,000,000 고정)")
    print(f"  {'광선 수':>14} {'경로 수 종류':>13} {'경로 최대−최소':>14} {'|h| 폭 dB':>11}")
    for S in (5_000_000, 10_000_000, 20_000_000, 40_000_000):
        ns, hs = probe(sc, a.reps, samples_per_src=S, max_num_paths_per_src=2_000_000)
        spread = (20 * np.log10(max(hs) / min(hs))) if min(hs) > 0 else float("nan")
        rows.append(dict(axis="samples", buckets=2_000_000, samples_per_src=S,
                         n_reps=a.reps, n_paths=sorted(set(ns)),
                         n_kinds=len(set(ns)), n_span=int(max(ns) - min(ns)),
                         h_spread_db=round(float(spread), 5)))
        print(f"  {S:14,} {len(set(ns)):13d} {max(ns)-min(ns):14d} {spread:11.5f}")

    json.dump({"_meta": {
        "generator": "benchmark/hash_bucket_sweep_0903.py",
        "question_ko": "해시 통 수를 키우면 판 사이 흔들림(=낙차의 최소 재현판)이 줄어드나",
        "scene_ko": f"합성 평판 격자 {a.n_side**2} 장(삼각형 {nf}) · 산란 {a.scat} · "
                    f"회절 끔 · 깊이 2 · 씨앗 {SEED} 고정",
        "min_spec_count_size": floor,
        "mitsuba_variant": variant,
        "variant_note_ko": ("llvm 이면 CPU 판이다 — GPU 스레드 순서가 빠진 대조군이라, "
                            "여기서도 흔들리면 원인이 «순서» 가 아니라는 뜻이다."),
        "floor_note_ko": "통 수는 max(max_num_paths_per_src, MIN_SPEC_COUNT_SIZE) 라 "
                         "바닥 아래 값은 효과가 없다. 이 훑기는 바닥 위로만 흔든다.",
        "reads_ko": "⛔판정은 여기 적지 않는다 — 표를 보고 사람이 쓴다(주장 게이트 ⓑ).",
    }, "rows": rows}, open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"\n  ✅ {os.path.relpath(OUT, ROOT)}")


if __name__ == "__main__":
    main()
