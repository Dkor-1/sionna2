# -*- coding: utf-8 -*-
"""
env_scene_cost_v3_0819.py — 환경 씬의 비용, **운영 광선 수까지** 올려서 (실측 3판)
================================================================================

2 판의 결함 — 스스로 잡았다
---------------------------
  ⛔**컴파일 캐시를 쟀다.** 광선을 64 배 늘렸는데 시간이 **줄었다**(×0.3~0.5).
     Dr.Jit 이 설정마다 커널을 새로 컴파일하고 그 뒤로 캐시를 쓰기 때문이다.
     «첫 판 버리기» 로는 부족했다 — **설정마다** 예열해야 한다.
  ⛔**사다리가 너무 짧았다.** 1600 만까지만 쟀는데, 우리 큐는 `--spp 4000000000`
     = **40 억** 으로 돈다(250 배). 운영 지점을 안 재고 비용을 논한 셈이다.

이 판이 고치는 것
-----------------
  ① **설정마다 예열** 한 발을 먼저 쏘고 버린 뒤 잰다.
  ② 광선 사다리를 **40 억까지** 올린다 — 실제 운영 지점을 포함한다.
  ③ 비교 대상에 **자유공간(환경 없음)** 을 넣는다 — «환경을 더하면 얼마나 비싸지나» 는
     환경 없는 판이 있어야 답이 된다.

⛔GPU 1 장. 산출: outputs/env_scene_cost_v3_0819.json
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

OUT = os.path.join(ROOT, "outputs", "env_scene_cost_v3_0819.json")

FC, DEPTH = 3.5e9, 2
#: 광선 사다리 — ⭐마지막 둘이 **운영 지점**이다
SPS_LADDER = (1_000_000, 16_000_000, 256_000_000, 1_000_000_000, 4_000_000_000)
CASES = [("(자유공간 · 환경 없음)", "빈 씬 — 지금 우리 스윕이 쓰는 것"),
         ("floor_wall", "바닥+벽"), ("simple_street_canyon", "도심 협곡(6채)"),
         ("munich", "뮌헨 (실제 도시)"), ("san_francisco", "샌프란시스코 (실제 도시)")]


def build(name):
    import sionna.rt as rt
    sc = rt.load_scene() if name.startswith("(") else rt.load_scene(getattr(rt.scene, name))
    sc.frequency = FC
    sc.tx_array = rt.PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="V")
    sc.rx_array = rt.PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="V")
    bb = sc.mi_scene.bbox()
    lo, hi = np.array(bb.min, float), np.array(bb.max, float)
    if not np.all(np.isfinite(lo)) or name.startswith("("):
        lo, hi = np.zeros(3), np.array([100.0, 100.0, 30.0])       # 빈 씬은 기준 상자를 준다
    ctr = 0.5 * (lo + hi)
    span = float(np.linalg.norm(hi[:2] - lo[:2]))
    sep = float(min(span / 3.0, 200.0))
    z = float(float(lo[2]) + min(max(float(hi[2] - lo[2]) * 0.8, 3.0), 50.0))
    sc.add(rt.Transmitter("tx", position=[float(ctr[0] - sep / 2), float(ctr[1]), z]))
    sc.add(rt.Receiver("rx",    position=[float(ctr[0] + sep / 2), float(ctr[1]), z]))
    ntri = sum(int(s.face_count()) for s in sc.mi_scene.shapes() if hasattr(s, "face_count"))
    return sc, ntri, round(span, 1)


def timed(solver, sc, sps):
    """⭐**이 설정으로** 한 발 예열해 커널을 컴파일시킨 뒤, 두 발을 재서 중앙값."""
    import drjit as dr
    p = solver(sc, max_depth=DEPTH, samples_per_src=sps); dr.sync_thread(); del p   # 예열
    ts, npath = [], None
    for _ in range(2):
        t0 = time.time()
        p = solver(sc, max_depth=DEPTH, samples_per_src=sps)
        dr.sync_thread()
        ts.append(time.time() - t0)
        try:
            npath = int(np.asarray(p.a[0]).size)
        except Exception:                                          # noqa: BLE001
            npath = None
        del p
    return round(float(np.median(ts)), 4), npath


def main():
    import sionna.rt as rt
    t00 = time.time()
    solver = rt.PathSolver()
    rows, failed = {}, []
    print(f"  {'씬':26s}{'tri':>9s}" + "".join(f"{s//1_000_000:>10d}M" for s in SPS_LADDER))
    for name, ko in CASES:
        try:
            sc, ntri, span = build(name)
        except Exception as e:                                     # noqa: BLE001
            failed.append(dict(case=name, stage="load", err=str(e)[:200])); continue
        r = dict(label_ko=ko, n_triangles=ntri, span_m=span, ladder={})
        cells = []
        for sps in SPS_LADDER:
            try:
                t, n = timed(solver, sc, sps)
                r["ladder"][str(sps)] = dict(s=t, n_paths=n)
                cells.append(f"{t:11.3f}")
            except Exception as e:                                 # noqa: BLE001
                r["ladder"][str(sps)] = dict(error=str(e)[:160])
                failed.append(dict(case=name, stage=f"sps{sps}", err=str(e)[:160]))
                cells.append(f"{'실패':>11s}")
        print(f"  {name:26s}{ntri:9,d}" + "".join(cells))
        rows[name] = r

    # ── ⭐«환경을 더하면 얼마나 비싸지나» — 자유공간 대비 배수 ───────────
    base = rows.get("(자유공간 · 환경 없음)", {}).get("ladder", {})
    for r in rows.values():
        r["vs_free_space_x"] = {
            k: (None if not (base.get(k, {}).get("s") and v.get("s"))
                else round(v["s"] / base[k]["s"], 2))
            for k, v in r["ladder"].items()}

    doc = {"_meta": {
        "generator": "benchmark/env_scene_cost_v3_0819.py",
        "generated_kst": time.strftime("%Y-%m-%d %H:%M:%S (UTC+9)",
                                       time.gmtime(time.time() + 9 * 3600)),
        "role_ko": "환경 씬을 더하면 광선추적이 얼마나 비싸지나 — 운영 광선 수(40 억)까지",
        "gpu_used": True, "cuda_visible": os.environ.get("CUDA_VISIBLE_DEVICES", "(전체)"),
        "sionna": __import__("sionna").__version__,
        "protocol_ko": (f"max_depth {DEPTH} · **설정마다 예열 1 발** 후 2 발 중앙값 · "
                        f"확산 끔(내장 씬 재질 S=0 이라 어차피 무동작)"),
        "supersedes": ["outputs/env_scene_cost_0819.json (경로 0~4 개)",
                       "outputs/env_scene_cost_v2_0819.json (컴파일 캐시 오염 · 사다리 짧음)"],
        "elapsed_s": round(time.time() - t00, 1)},
        "cases": rows, "failed": failed}
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
    print(f"\nsaved {OUT}")


if __name__ == "__main__":
    main()
