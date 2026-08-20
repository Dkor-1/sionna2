# -*- coding: utf-8 -*-
"""
verify_optimization.py — 최적화가 **결론을 바꾸는가**를 잰다 (2026-08-20)
================================================================================

왜 σ 비교로는 모자란가
-----------------------
σ 하나가 1e-15 만 달라도 안심하면 안 된다. 우리가 실제로 쓰는 것은 σ 가 아니라
**자세 8,192 개를 이어 붙인 마이크로도플러 무늬**이고, 자세마다 **무작위로** 생기는
작은 오차는 슬로우타임에서 **백색 잡음**으로 얹혀 빗살 대비를 깎을 수 있다.
⇒ 그래서 **하류 잣대**(빗살 대비·리듬 몫·AC 세기)를 직접 견준다.

⭐잣대 식은 다시 구현하지 않는다 — `build_md_atlas`(정본) 함수를 그대로 쓴다.
  (다시 구현하면 «검사기가 틀린 것» 과 «코드가 틀린 것» 을 못 가른다.)

⭐**검사기 자체 검증**이 먼저다
------------------------------
같은 코드로 두 번 낸 샤드를 넣어 **잡음 바닥**을 먼저 잰다. 그 바닥보다 작으면 통과다.
⛔이 단계를 빼면 «검사기가 고장 나서 다 통과» 하는 사고가 난다.

판정선
------
  · σ·E : 잡음 바닥(같은 코드 재실행)의 **3 배** 이내
  · 하류 잣대 : 판정 막대 **2.68 dB** (귀무분포 p99.9, 20,000 시행)의 **1/100** 이내
    ⇒ 빗살 대비 0.027 dB. 이 정도면 어떤 결론도 안 흔든다.

사용:
    python benchmark/verify_optimization.py <A.npz> <B.npz> [--floor <C.npz> <D.npz>]
        A,B : 견줄 두 판   ·   C,D : 같은 코드 두 판(잡음 바닥). 없으면 A,B 만 본다.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import build_md_atlas as A                                      # noqa: E402

FFL = 126.66666666666667          # f_flash 규약값(matrice4e)
#: 판정 막대 2.68 dB 의 1/100
METRIC_TOL_DB = 0.0268
METRIC_TOL_PP = 0.0268


def f_tip_at(el: float) -> float:
    """앙각별 날개끝 도플러 — 스윕과 같은 규약."""
    return 1101.6 / np.cos(np.radians(-30.0)) * np.cos(np.radians(el))


def load(p):
    d = np.load(p)
    E = d["E"]
    meta = np.asarray(d["meta"], float) if "meta" in d else None
    el = float(meta[0]) if meta is not None and meta.size else -30.0
    return E, d.get("npaths"), el


def _f(v):
    if v is None:
        return None
    return float(v[0]) if isinstance(v, (tuple, list)) else float(v)


def metrics(E: np.ndarray, el: float) -> dict:
    """정본 잣대 — 다시 구현하지 않고 build_md_atlas 를 그대로 부른다."""
    ft = f_tip_at(el)
    ac = float(10 * np.log10((np.abs(E - E.mean()) ** 2).mean()))
    return dict(ac_db=ac,
                rhythm_pct=_f(A.rhythm_share(E, FFL, ft)),
                comb_db=_f(A.comb_contrast_db(E, FFL, ft)))


def compare(pa: str, pb: str) -> dict:
    Ea, na, el = load(pa)
    Eb, nb, _ = load(pb)
    if Ea.shape != Eb.shape:
        return dict(error=f"자세 수가 다르다 {Ea.shape} vs {Eb.shape}")
    rel = float((np.abs(Eb - Ea) / np.maximum(np.abs(Ea), 1e-300)).max())
    sa = 20 * np.log10(np.abs(Ea) + 1e-300)
    sb = 20 * np.log10(np.abs(Eb) + 1e-300)
    ma, mb = metrics(Ea, el), metrics(Eb, el)
    dm = {}
    for k in ma:
        if ma[k] is None or mb[k] is None:
            dm[k] = None
        else:
            dm[k] = round(abs(mb[k] - ma[k]), 6)
    return dict(
        n_poses=int(Ea.size), el_deg=el,
        bit_equal=bool(Ea.tobytes() == Eb.tobytes()),
        max_rel=rel, sigma_max_ddb=float(np.abs(sb - sa).max()),
        npaths_equal=(None if na is None or nb is None else bool(np.array_equal(na, nb))),
        metrics_a=ma, metrics_b=mb, metric_delta=dm)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--floor", nargs=2, metavar=("C", "D"),
                    help="⭐같은 코드로 낸 두 판 — 잡음 바닥을 여기서 잰다")
    ap.add_argument("--json", default="")
    a = ap.parse_args()

    out = {"_meta": {"generator": "benchmark/verify_optimization.py",
                     "role_ko": "최적화가 하류 잣대를 흔드는가 — σ 가 아니라 잣대를 본다",
                     "metric_source_ko": "build_md_atlas(정본) 함수를 그대로 씀",
                     "tol_ko": f"σ: 잡음 바닥×3 · 잣대: {METRIC_TOL_DB} dB (판정 막대 2.68 의 1/100)"}}

    floor = None
    if a.floor:
        floor = compare(*a.floor)
        out["noise_floor"] = floor
        print("═══ ① 검사기 자체 검증 — 같은 코드 두 판 (잡음 바닥) ═══")
        print(f"  최대 상대차 {floor['max_rel']:.3e} · σ최대차 {floor['sigma_max_ddb']:.3e} dB")
        print(f"  잣대 차: " + " · ".join(
            f"{k} {v}" for k, v in floor["metric_delta"].items()))

    r = compare(a.a, a.b)
    out["test"] = r
    if "error" in r:
        print("⛔", r["error"])
        raise SystemExit(2)

    print("\n═══ ② 본 시험 ═══")
    print(f"  자세 {r['n_poses']} · 앙각 {r['el_deg']:.0f}°")
    print(f"  E 비트 동일 {r['bit_equal']} · 최대 상대차 {r['max_rel']:.3e} "
          f"· σ최대차 {r['sigma_max_ddb']:.3e} dB · 경로수 동일 {r['npaths_equal']}")
    print(f"  {'잣대':14s}{'옛':>12s}{'새':>12s}{'차':>12s}{'허용':>10s}  판정")
    ok = True
    for k, tol in (("ac_db", METRIC_TOL_DB), ("rhythm_pct", METRIC_TOL_PP),
                   ("comb_db", METRIC_TOL_DB)):
        va, vb, d = r["metrics_a"][k], r["metrics_b"][k], r["metric_delta"][k]
        if d is None:
            print(f"  {k:14s}{'—':>12s}{'—':>12s}{'—':>12s}{tol:10.4f}  (정의 안 됨)")
            continue
        p = d <= tol
        ok &= p
        print(f"  {k:14s}{va:12.5f}{vb:12.5f}{d:12.6f}{tol:10.4f}  {'✅' if p else '⛔'}")

    # σ 판정 — 잡음 바닥이 있으면 그 3 배, 없으면 절대선 1e-12
    lim = (max(floor["max_rel"], 1e-16) * 3) if floor else 1e-12
    sig_ok = r["max_rel"] <= lim
    ok &= sig_ok
    print(f"\n  σ 판정: {r['max_rel']:.3e} {'≤' if sig_ok else '>'} {lim:.3e} "
          f"({'잡음 바닥×3' if floor else '절대선'})  {'✅' if sig_ok else '⛔'}")
    out["verdict"] = dict(pass_=bool(ok), sigma_limit=lim,
                          reading_ko=("최적화가 결론을 흔들지 않는다" if ok else
                                      "⛔흔든다 — 도입하면 안 된다"))
    print(f"\n  ⭐판정: {'✅ 통과 — 결론을 안 흔든다' if ok else '⛔ 실패 — 도입 금지'}")
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        print(f"  saved {a.json}")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
