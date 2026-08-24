# -*- coding: utf-8 -*-
"""adv_refute_hashlottery_0824.py — 「--inmem 이 회절 팔을 깨뜨렸다」를 반증한다
================================================================================

무엇을 묻나
-----------
`coverage_verify_0820.json` 은 16 칸 중 **한 칸만** 떨어뜨렸다:

    R1D1E1F1 · el −90 :  relf 4.22e-16  →  relt 8.19e-4   (12 자릿수 위)
                         rhythm 차 0.1469 pp  (잣대 0.0268)

떨어진 칸이 하필 **회절 팔**(D1E1)이다. 그런데 2026-08-18 NVlabs/sionna Discussion #1175
에서 Sionna 유지보수자(merlinND)가 이렇게 답했다:

  · "Sionna RT is **not guaranteed to be deterministic**" — 대규모 병렬 실행에서 스레드가
    끝나는 순서가 무작위라 IEEE 부동소수 합의 순서가 달라진다.
  · 회절 웨지 중복제거용 **해시 테이블에 항목이 들어가는 순서**가 이후의 무작위 웨지
    표집에 영향을 준다. 씨앗만으로 통제되지 않는다.
  · 그 해시 테이블은 **`PathSolver()` 에서 쓰인다** (우리가 쓰는 바로 그 솔버다).
  · 제보자 실측: 층 대부분 0.000015 dB 인데 **한 층만 3.07 dB** — ⭐**간헐적**이다.

⛔그렇다면 `coverage_verify_0820.py` 가 **옛×2 단 두 판**으로 세운 «잡음 바닥» 은
  간헐적 꼬리를 잡을 수 없다. 바닥이 4.22e-16 이었다는 것은 «차이가 없다» 가 아니라
  «두 번 뽑았는데 둘 다 조용했다» 일 수 있다.

무엇을 하나
-----------
떨어진 그 칸 하나에서 **옛 경로만 6 판**, **새 경로(--inmem) 3 판** 을 돌려
  ① 옛↔옛 상대차 분포 (진짜 바닥, 쌍 15 개)
  ② 새↔새 상대차 분포 (쌍 3 개)
  ③ 옛↔새 상대차 분포 (쌍 18 개)
를 낸다. ⭐그리고 판마다 **`npaths` 를 기록한다** — 판별 경로 수가 판마다 다르면
해시 복권이 직접 확인되는 것이다.

판정
----
  · 옛↔옛 최대 상대차가 8.19e-4 급에 닿는다 → **복권이다. `--inmem` 은 무죄.**
  · 옛↔옛 이 항상 1e-15 아래인데 옛↔새만 1e-4 급 → **`--inmem` 의 진짜 회귀다.**

⛔GPU 0 만 쓴다(2·3 번은 남이 쓰는 중). 워커는 한 번에 하나다.
산출: outputs/adv_refute_hashlottery_0824.json
실행: python benchmark/adv_refute_hashlottery_0824.py [--n-old 6] [--n-new 3] [--gpu 0]
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import coverage_verify_0820 as C           # noqa: E402  (run_cell·metrics·dmet 재사용)

ARM = "R1D1E1F1"
EL = -90
NPOSE = 528                                #: 떨어진 칸과 같은 자세 수
OUT = os.path.join(C.ROOT, "outputs", "adv_refute_hashlottery_0824.json")


def relmax(Ea, Eb) -> float:
    """두 복소 필드의 최대 **상대** 차 — coverage_verify_0820 과 같은 정의."""
    return float((np.abs(Eb - Ea) / np.maximum(np.abs(Ea), 1e-300)).max())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-old", type=int, default=6)
    ap.add_argument("--n-new", type=int, default=3)
    ap.add_argument("--gpu", default="0")
    ap.add_argument("--spp", type=int, default=250_000_000)
    ap.add_argument("--drone", default="matrice4e")
    a = ap.parse_args()

    os.makedirs(C.TMP, exist_ok=True)
    print(f"  칸 {ARM} el{EL} · 기체 {a.drone} · 자세 {NPOSE} · 광선 {a.spp:,} · GPU {a.gpu}")
    print(f"  옛 {a.n_old} 판 + 새(--inmem) {a.n_new} 판 = {a.n_old + a.n_new} 판\n")

    runs, t0 = [], time.time()
    plan = [("old", [])] * a.n_old + [("new", ["--inmem"])] * a.n_new
    for i, (kind, extra) in enumerate(plan):
        tag = f"lot{i}"
        t1 = time.time()
        p, err = C.run_cell(ARM, EL, a.drone, NPOSE, a.spp, extra, tag, a.gpu)
        if not p:
            print(f"  [{i + 1}/{len(plan)}] {kind:3s} ⛔ 실패 — {err[:120]}")
            continue
        z = np.load(p)
        m, E = C.metrics(p, EL)
        runs.append(dict(i=i, kind=kind, path=p, E=E,
                         npaths=int(z["npaths"].max()), metric=m))
        print(f"  [{i + 1}/{len(plan)}] {kind:3s} · {time.time() - t1:5.1f}s "
              f"· npaths={int(z['npaths'].max()):5d} "
              f"· ac_db={m['ac_db']:.9f} rhythm={m['rhythm_pct']:.6f}")

    if len(runs) < 3:
        print("\n  ⛔ 판이 3 개 미만이라 판정 불가")
        return 2

    olds = [r for r in runs if r["kind"] == "old"]
    news = [r for r in runs if r["kind"] == "new"]

    def pairs(xs, ys=None):
        it = itertools.combinations(xs, 2) if ys is None else itertools.product(xs, ys)
        out = []
        for x, y in it:
            out.append(dict(a=x["i"], b=y["i"],
                            rel=relmax(x["E"], y["E"]),
                            dmet=C.dmet(x["metric"], y["metric"])))
        return out

    groups = {"old_vs_old": pairs(olds), "new_vs_new": pairs(news),
              "old_vs_new": pairs(olds, news)}

    print(f"\n  {'짝':12s}{'쌍':>4s}{'rel 최소':>12s}{'rel 중앙':>12s}{'rel 최대':>12s}"
          f"{'rhythm 최대':>13s}")
    summary = {}
    for name, ps in groups.items():
        if not ps:
            continue
        rel = np.array([p["rel"] for p in ps])
        rh = np.array([p["dmet"]["rhythm_pct"] or 0.0 for p in ps])
        summary[name] = dict(n_pairs=len(ps), rel_min=float(rel.min()),
                             rel_med=float(np.median(rel)), rel_max=float(rel.max()),
                             rhythm_max=float(rh.max()))
        print(f"  {name:12s}{len(ps):4d}{rel.min():12.2e}{np.median(rel):12.2e}"
              f"{rel.max():12.2e}{rh.max():13.6f}")

    npaths = sorted({r["npaths"] for r in runs})
    npaths_old = sorted({r["npaths"] for r in olds})
    print(f"\n  npaths — 전체 {npaths} · 옛만 {npaths_old}")
    lottery_npaths = len(npaths_old) > 1

    ref = 8.187348815977586e-04                 # 원 판정의 relt
    oo = summary.get("old_vs_old", {}).get("rel_max", 0.0)
    verdict = ("REFUTED — 옛↔옛 만으로도 같은 크기로 갈린다. 해시 복권이다"
               if oo >= ref * 0.1 else
               "NOT_REFUTED — 옛↔옛 은 조용한데 옛↔새만 갈린다. --inmem 의 실제 차이다")
    print(f"\n  옛↔옛 최대 {oo:.3e}  vs  원 판정 relt {ref:.3e}")
    print(f"  ⭐판정: {verdict}")
    if lottery_npaths:
        print("  ⭐npaths 가 옛 판들 사이에서도 달라진다 — 후보 집합 복권이 직접 확인됨")

    doc = {"_meta": {
        "generator": "benchmark/adv_refute_hashlottery_0824.py",
        "generated_kst": time.strftime("%Y-%m-%d %H:%M:%S (UTC+9)",
                                       time.gmtime(time.time() + 9 * 3600)),
        "role_ko": "회절 팔 한 칸에서 옛 경로를 여러 판 돌려 «잡음 바닥» 의 진짜 분포를 낸다",
        "why_ko": "NVlabs/sionna Discussion #1175 — PathSolver 해시테이블 순서가 웨지 표집에 "
                  "영향을 주고 그 효과가 간헐적이다. 옛×2 로 세운 바닥은 꼬리를 못 잡는다",
        "cell": dict(arm=ARM, el=EL, drone=a.drone, n_poses=NPOSE, spp=a.spp),
        "n_old": len(olds), "n_new": len(news),
        "reference_relt_from_coverage_0820": ref,
        "elapsed_s": round(time.time() - t0, 1)},
        "runs": [dict(i=r["i"], kind=r["kind"], npaths=r["npaths"], metric=r["metric"])
                 for r in runs],
        "pairs": {k: [dict(a=p["a"], b=p["b"], rel=p["rel"], dmet=p["dmet"]) for p in v]
                  for k, v in groups.items()},
        "summary": summary,
        "npaths_distinct_all": npaths,
        "npaths_distinct_old": npaths_old,
        "npaths_lottery": bool(lottery_npaths),
        "verdict_ko": verdict}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print(f"\n  saved {OUT}  ({time.time() - t0:.0f}s)")

    for r in runs:
        try:
            os.remove(r["path"])
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
