# -*- coding: utf-8 -*-
"""
thread_ladder_0903.py — 흔들림이 «병렬 순서» 때문인가.

여기까지 갈린 것
    · CPU(llvm) 판에서도 흔들린다 ⇒ **GPU 스레드 순서 탓이 아니다**
    · 해시 통 수를 1M → 32M 로 32 배 키워도 발생률이 안 준다(0.37 → 0.53)
      그리고 최대 편차가 통 수와 무관하게 **3.08419 dB 로 똑같다**
      ⇒ `max_num_paths_per_src` 는 이 흔들림의 손잡이가 **아니다**
    · 대신 후보 수에 문턱이 있다 — 광선 10M·20M 는 발생률 0.000, 40M·80M 는 0.40·0.43

    ⇒ 남은 후보: **병렬 축약 순서**. `dr.scatter_inc` 로 통을 먼저 올린 스레드가 이기는데,
      그 순서는 스레드 수에 좌우된다. CPU 든 GPU 든 «병렬» 이면 있는 일이다.

이 시험
    같은 씬·같은 씨앗·같은 광선 수에서 **스레드 수만** 바꾼다.
      스레드 1 에서 흔들림이 사라지면 ⇒ 원인은 병렬 순서다
      스레드 1 에서도 흔들리면    ⇒ 순서가 아니다. 다른 곳을 봐야 한다

⚠스레드 1 은 느리다. 판 수를 적게 잡고, 그 대신 «흔들림이 잘 보이는» 광선 수에서 잰다.
⛔판정하지 않는다 — 수만 낸다(주장 게이트 ⓑ).

쓰는 법
    CUDA_VISIBLE_DEVICES="" PYTHONPATH=src:benchmark \\
        /workspace/.venvs/py312/bin/python benchmark/thread_ladder_0903.py --reps 5
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
OUT = os.path.join(ROOT, "outputs", "thread_ladder_0903.json")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--n-side", type=int, default=24)
    ap.add_argument("--samples", type=int, default=40_000_000)
    ap.add_argument("--threads", type=int, nargs="*", default=[1, 4, 32, 192])
    a = ap.parse_args()

    import drjit as dr
    import mitsuba as mi
    import sionna.rt as _rt                                    # noqa: F401
    from minrepro_hash_0902 import build, probe

    native = dr.thread_count()
    print("⭐스레드 사다리 — 병렬 순서가 흔들림의 원인인가\n")
    print(f"  변형 {mi.variant()} · 기본 스레드 {native} · 평판 {a.n_side**2} · "
          f"광선 {a.samples:,} · 판 {a.reps}\n")
    sc, nf = build(a.n_side, 0.7)

    rows = []

    #: 첫 줄(보통 스레드 1)의 최빈값을 공통 기준으로 쓴다

    base_mode: list = [None]
    print(f"  {'스레드':>7} {'최빈 경로':>10} {'흔들린 판':>10} {'발생률':>8} "
          f"{'최대 편차 dB':>12} {'초/판':>8}")
    for T in a.threads:
        t = min(T, native)
        dr.set_thread_count(t)
        t0 = time.time()
        ns, hs = probe(sc, a.reps, samples_per_src=a.samples,
                       max_num_paths_per_src=2_000_000)
        dt = (time.time() - t0) / max(1, a.reps)
        mode = collections.Counter(ns).most_common(1)[0][0]
        ref = float(np.median([hs[i] for i in range(len(hs)) if ns[i] == mode]))
        #: ⛔hash_bucket_stat_0903.stat() 과 같은 병이 여기 인라인으로 복사돼 있었다 —
        #:   `h > 0` 이 표본을 말없이 버리고, ref 가 0·nan 이면 편차가 0.0 으로 날조된다.
        #:   2026-09-10 에 양쪽을 같이 고쳤다. 분모를 함께 적는다.
        _used = [h for h in hs if np.isfinite(h) and h > 0.0]
        _ok = np.isfinite(ref) and ref > 0.0
        _dv = [abs(20 * np.log10(h / ref)) for h in _used] if _ok else []
        dev = max(_dv) if _dv else None
        n_off = sum(1 for v in ns if v != mode)
        #: ⭐**첫 줄의 최빈값을 공통 기준으로** 함께 센다 (2026-09-10 신설).
        #:   rate_off 는 «각 줄 자기 최빈값» 기준이라 줄끼리 나란히 못 읽는다 —
        #:   실제로 스레드 1 은 8059, 2 는 8058 이 최빈이라 2 의 0.025 는
        #:   「1-스레드와 다른 판이 2.5 %」가 아니라 **39/40 = 97.5 %** 다.
        if base_mode[0] is None:
            base_mode[0] = int(mode)
        _nb = sum(1 for v in ns if v != base_mode[0])
        rows.append(dict(threads=t, n_reps=a.reps, mode_paths=int(mode),
                         n_off=n_off, rate_off=round(n_off / a.reps, 4),
                         #: ⭐공통 기준(첫 줄 최빈값) 대비
                         base_mode_paths=int(base_mode[0]),
                         n_off_vs_base=_nb, rate_off_vs_base=round(_nb / a.reps, 4),
                         paths_seen=sorted(set(ns)),
                         #: ⭐판별 값을 그대로 남긴다 — 없으면 역산해야 한다(192 줄은 역산 불가)
                         paths_per_rep=[int(v) for v in ns],
                         n_used=len(_dv), ref_ok=bool(_ok),
                         max_dev_db=(round(float(dev), 5) if dev is not None else None),
                         sec_per_rep=round(dt, 1)))
        print(f"  {t:7d} {mode:10d} {n_off:10d} {n_off/a.reps:8.3f} "
              f"{dev:12.5f} {dt:8.1f}")
    dr.set_thread_count(native)

    json.dump({"_meta": {
        "generator": "benchmark/thread_ladder_0903.py",
        "question_ko": "스레드 수만 바꿨을 때 흔들림 발생률이 어떻게 되나",
        "reads_ko": ("스레드 1 에서 발생률이 0 이면 원인은 **병렬 축약 순서**다. "
                     "1 에서도 흔들리면 순서가 아니다. ⛔판정은 여기 적지 않는다."),
        "mitsuba_variant": mi.variant(), "native_thread_count": native,
        "scene_ko": f"합성 평판 {a.n_side**2} 장(삼각형 {nf}) · 산란 0.7 · 회절 끔 · 깊이 2 · 씨앗 고정",
        "samples_per_src": a.samples, "buckets": 2_000_000,
    }, "rows": rows}, open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"\n  ✅ {os.path.relpath(OUT, ROOT)}")


if __name__ == "__main__":
    main()
