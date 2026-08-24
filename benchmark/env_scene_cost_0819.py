# -*- coding: utf-8 -*-
"""
env_scene_cost_0819.py — 환경 씬을 넣으면 연산이 얼마나 비싸지나 (**실측**)
================================================================================

물음 둘:
  ① 실제 도심 씬(뮌헨 등)을 불러오면 광선추적이 얼마나 느려지나?
  ② **확산 산란(diffuse_reflection)** 을 켜면 얼마나 더 비싸지나?

⭐추측하지 않는다 — 같은 조건(깊이·표본수)에서 씬만 갈아 끼우고 **시간을 잰다**.

규약
----
  · 표본수 samples_per_src 를 **고정** 한다 — 안 고정하면 씬 크기와 표본수가 뒤섞인다.
  · 팔은 우리 실험 규약과 같게 **max_depth 2**.
  · 확산은 Sionna 2.0.1 의 `diffuse_reflection` 스위치로 켠다(기본 False).
  · Tx·Rx 는 씬 bbox 로 자동 배치한다 — 씬마다 규모가 달라 절대 위치를 못 박을 수 없다.
  · ⭐첫 호출은 **컴파일 비용**이 섞이므로 버리고, 그 다음 두 번의 중앙값을 쓴다.

⛔GPU 1 장만 쓴다(CUDA_VISIBLE_DEVICES 로 제한). 큐를 방해하지 않는다.

산출: outputs/env_scene_cost_0819.json
실행: CUDA_VISIBLE_DEVICES=4 PYTHONPATH=src:benchmark python benchmark/env_scene_cost_0819.py
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

OUT = os.path.join(ROOT, "outputs", "env_scene_cost_0819.json")

#: 재 볼 씬 — 작은 것부터 실제 도시까지
SCENES = [
    ("floor_wall",                     "바닥 + 벽 한 장"),
    ("simple_street_canyon",           "도심 협곡 (건물 6채)"),
    ("simple_street_canyon_with_cars", "도심 협곡 + 자동차"),
    ("etoile",                         "파리 개선문 일대 (실제)"),
    ("munich",                         "뮌헨 시가지 (실제)"),
    ("san_francisco",                  "샌프란시스코 (실제)"),
]

FC = 3.5e9
DEPTH = 2
SPS = 1_000_000          # samples_per_src — **고정**
N_REP = 3                # 첫 판은 버린다


def build(name):
    """씬을 불러오고 Tx·Rx 를 bbox 기준으로 배치한다."""
    import sionna.rt as rt
    sc = rt.load_scene(getattr(rt.scene, name))
    sc.frequency = FC
    sc.tx_array = rt.PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="V")
    sc.rx_array = rt.PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="V")

    lo = np.array(sc.mi_scene.bbox().min, float)
    hi = np.array(sc.mi_scene.bbox().max, float)
    ctr = 0.5 * (lo + hi)
    span = float(np.linalg.norm(hi[:2] - lo[:2]))
    # Tx·Rx 를 중심 근처에 span 의 1/6 만큼 떨어뜨려 둔다 — 씬 규모에 비례
    d = max(span / 6.0, 5.0)
    z = float(lo[2]) + max((hi[2] - lo[2]) * 0.25, 2.0)
    # ⚠Mitsuba Point3f 는 numpy 스칼라를 안 받는다 — 파이썬 float 으로 바꿔 넘긴다
    sc.add(rt.Transmitter("tx", position=[float(ctr[0] - d), float(ctr[1]), float(z)]))
    sc.add(rt.Receiver("rx",    position=[float(ctr[0] + d), float(ctr[1]), float(z)]))

    # 삼각형 수 — Mitsuba 도형에서 직접 센다
    ntri = 0
    for sh in sc.mi_scene.shapes():
        ntri += int(getattr(sh, "face_count", lambda: 0)())
    return sc, ntri, dict(span_m=round(span, 1), tx_rx_sep_m=round(2 * d, 1),
                          bbox_min=[round(v, 1) for v in lo],
                          bbox_max=[round(v, 1) for v in hi])


def timeit(solver, sc, **kw):
    """N_REP 번 돌리고 **첫 판을 버린** 중앙값 [s] 과 경로 수를 낸다."""
    import drjit as dr
    ts, npath = [], None
    for i in range(N_REP):
        t0 = time.time()
        p = solver(sc, max_depth=DEPTH, samples_per_src=SPS, **kw)
        dr.sync_thread()
        ts.append(time.time() - t0)
        try:
            npath = int(np.asarray(p.a[0]).size)
        except Exception:
            npath = None
        del p
    return round(float(np.median(ts[1:])), 3), round(ts[0], 3), npath


def main():
    import sionna.rt as rt
    t00 = time.time()
    solver = rt.PathSolver()
    rows, failed = {}, []

    for name, ko in SCENES:
        try:
            sc, ntri, geo = build(name)
        except Exception as e:                                     # noqa: BLE001
            failed.append(dict(scene=name, stage="load", err=str(e)[:200]))
            continue
        r = dict(label_ko=ko, n_triangles=ntri, **geo)
        for tag, kw in (("diffuse_off", dict(diffuse_reflection=False)),
                        ("diffuse_on",  dict(diffuse_reflection=True))):
            try:
                med, first, npath = timeit(solver, sc, **kw)
                r[tag] = dict(median_s=med, first_call_s=first, n_paths=npath)
            except Exception as e:                                 # noqa: BLE001
                r[tag] = dict(error=str(e)[:200])
                failed.append(dict(scene=name, stage=tag, err=str(e)[:200]))
        a = r.get("diffuse_off", {}).get("median_s")
        b = r.get("diffuse_on", {}).get("median_s")
        r["diffuse_cost_x"] = (None if not (a and b) else round(b / a, 2))
        rows[name] = r
        print(f"  {name:32s} tri {ntri:8,d}  off {r.get('diffuse_off',{}).get('median_s','—')!s:>8} s"
              f"  on {r.get('diffuse_on',{}).get('median_s','—')!s:>8} s"
              f"  ×{r['diffuse_cost_x']}")

    base = rows.get("floor_wall", {}).get("diffuse_off", {}).get("median_s")
    for r in rows.values():
        m = r.get("diffuse_off", {}).get("median_s")
        r["vs_floor_wall_x"] = (None if not (base and m) else round(m / base, 2))

    doc = {"_meta": {
        "generator": "benchmark/env_scene_cost_0819.py",
        "generated_kst": time.strftime("%Y-%m-%d %H:%M:%S (UTC+9)",
                                       time.gmtime(time.time() + 9 * 3600)),
        "role_ko": "환경 씬 · 확산 산란이 광선추적 비용을 얼마나 늘리나 — 실측",
        "gpu_used": True, "cuda_visible": os.environ.get("CUDA_VISIBLE_DEVICES", "(전체)"),
        "sionna": __import__("sionna").__version__,
        "protocol_ko": (f"max_depth {DEPTH} · samples_per_src {SPS:,} **고정** · "
                        f"{N_REP} 회 중 첫 판(컴파일) 버리고 중앙값"),
        "caveat_ko": ("⚠Tx·Rx 를 bbox 로 자동 배치했다 — 씬마다 기하가 달라 «같은 상황» 이 아니다. "
                      "따라서 씬 사이 절대 비교보다 **씬 안에서의 확산 on/off 비율**이 더 믿을 만하다"),
        "elapsed_s": round(time.time() - t00, 1)},
        "scenes": rows, "failed": failed}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print(f"\nsaved {OUT}")


if __name__ == "__main__":
    main()
