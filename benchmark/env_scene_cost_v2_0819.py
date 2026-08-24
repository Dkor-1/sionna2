# -*- coding: utf-8 -*-
"""
env_scene_cost_v2_0819.py — 환경 씬·확산 산란의 **진짜 비용** (실측 2판)
================================================================================

1 판(env_scene_cost_0819.py)의 결함 — 스스로 잡았다
---------------------------------------------------
  ⛔ Tx·Rx 를 bbox 로 자동 배치했더니 **경로가 0~4 개**밖에 안 났다(etoile 은 0 개).
     즉 «아무것도 못 찾는 시간» 을 쟀다.
  ⛔ 확산 on/off 비가 0.65~1.7 로 **무작위**였다. 씬 재질의 **산란계수 S 가 0** 이면
     스위치를 켜도 아무 일이 안 일어난다 — 그걸 확인 안 했다.

이 판이 고치는 것
-----------------
  ① **S 를 먼저 읽는다.** 0 이면 «확산 스위치는 무동작» 이라고 적고, 별도로 S 를 올려서 다시 잰다.
  ② **경로가 나는 배치**를 쓴다 — 지상 50 m 두 점(우리 패시브 기하와 비슷하다).
     경로 수를 산출에 남겨 «찾은 게 있는 시간» 임을 보인다.
  ③ ⭐**비용의 진짜 축을 분리한다** — 씬 크기(삼각형)냐, 광선 수냐, 깊이냐.
     광선 수와 깊이를 **사다리로** 재서 무엇이 지배하는지 보인다.

⛔GPU 1 장. 산출: outputs/env_scene_cost_v2_0819.json
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

OUT = os.path.join(ROOT, "outputs", "env_scene_cost_v2_0819.json")

SCENES = [("floor_wall", "바닥+벽"), ("simple_street_canyon", "도심 협곡(6채)"),
          ("etoile", "파리 개선문"), ("munich", "뮌헨"), ("san_francisco", "샌프란시스코")]
FC, N_REP = 3.5e9, 3
SPS_BASE, DEPTH_BASE = 1_000_000, 2


def f(x):
    """drjit/numpy 스칼라 → 파이썬 float."""
    try:
        return float(np.asarray(x).reshape(-1)[0])
    except Exception:                                              # noqa: BLE001
        return float(np.array(x, dtype=float).reshape(-1)[0])


def build(name, s_override=None):
    import sionna.rt as rt
    sc = rt.load_scene(getattr(rt.scene, name))
    sc.frequency = FC
    sc.tx_array = rt.PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="V")
    sc.rx_array = rt.PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="V")

    mats = {}
    for n, m in sc.radio_materials.items():
        try:
            mats[n] = round(f(m.scattering_coefficient), 4)
        except Exception:                                          # noqa: BLE001
            mats[n] = None
        if s_override is not None:
            try:
                m.scattering_coefficient = s_override
            except Exception:                                      # noqa: BLE001
                pass

    lo = np.array(sc.mi_scene.bbox().min, float)
    hi = np.array(sc.mi_scene.bbox().max, float)
    ctr = 0.5 * (lo + hi)
    span = float(np.linalg.norm(hi[:2] - lo[:2]))
    # ⭐지상 위 높은 두 점 — 우리 패시브 기하(높은 조명원 + 높은 수신기)와 비슷하고,
    #   LoS 가 살아 있어 경로가 확실히 난다.
    sep = float(min(float(span) / 3.0, 200.0))
    # ⚠numpy 스칼라가 섞이면 Mitsuba Point3f 가 거부한다 — 통째로 float 으로 굳힌다
    z = float(float(lo[2]) + min(max(float(hi[2] - lo[2]) * 0.8, 3.0), 50.0))
    sc.add(rt.Transmitter("tx", position=[float(ctr[0] - sep / 2), float(ctr[1]), z]))
    sc.add(rt.Receiver("rx",    position=[float(ctr[0] + sep / 2), float(ctr[1]), z]))

    ntri = sum(int(sh.face_count()) for sh in sc.mi_scene.shapes()
               if hasattr(sh, "face_count"))
    return sc, ntri, dict(span_m=round(span, 1), tx_rx_sep_m=round(sep, 1),
                          height_m=round(z - float(lo[2]), 1),
                          scattering_coefficients=mats)


def timeit(solver, sc, sps, depth, **kw):
    import drjit as dr
    ts, npath = [], None
    for i in range(N_REP):
        t0 = time.time()
        p = solver(sc, max_depth=depth, samples_per_src=sps, **kw)
        dr.sync_thread()
        ts.append(time.time() - t0)
        try:
            npath = int(np.asarray(p.a[0]).size)
        except Exception:                                          # noqa: BLE001
            npath = None
        del p
    return round(float(np.median(ts[1:])), 4), npath


def main():
    import sionna.rt as rt
    t00 = time.time()
    solver = rt.PathSolver()
    rows, notes = {}, []

    for name, ko in SCENES:
        sc, ntri, geo = build(name)
        r = dict(label_ko=ko, n_triangles=ntri, **geo)
        S = [v for v in geo["scattering_coefficients"].values() if v is not None]
        r["S_all_zero"] = bool(S) and all(abs(v) < 1e-9 for v in S)

        # ── ① 기준 · 확산 on/off (씬 원래 재질 그대로) ────────────────────
        for tag, kw in (("base", dict(diffuse_reflection=False)),
                        ("diffuse_on", dict(diffuse_reflection=True))):
            t, n = timeit(solver, sc, SPS_BASE, DEPTH_BASE, **kw)
            r[tag] = dict(s=t, n_paths=n)
        r["diffuse_x_S_asis"] = round(r["diffuse_on"]["s"] / r["base"]["s"], 2)

        # ── ② 광선 수 사다리 — 비용이 여기 붙나 ──────────────────────────
        r["rays_ladder"] = {}
        for sps in (250_000, 1_000_000, 4_000_000, 16_000_000):
            t, n = timeit(solver, sc, sps, DEPTH_BASE, diffuse_reflection=False)
            r["rays_ladder"][f"{sps//1000}k"] = dict(s=t, n_paths=n)

        # ── ③ 깊이 사다리 ───────────────────────────────────────────────
        r["depth_ladder"] = {}
        for dp in (1, 2, 3, 4):
            t, n = timeit(solver, sc, SPS_BASE, dp, diffuse_reflection=False)
            r["depth_ladder"][f"d{dp}"] = dict(s=t, n_paths=n)

        rows[name] = r
        print(f"  {name:24s} tri {ntri:8,d}  기준 {r['base']['s']:7.3f} s "
              f"(경로 {r['base']['n_paths']})  확산×{r['diffuse_x_S_asis']}"
              f"  {'⚠S=0 → 스위치 무동작' if r['S_all_zero'] else ''}")

    # ── ④ ⭐S 를 실제로 올려서 확산 비용을 다시 잰다 ────────────────────
    s_test = {}
    for name in ("simple_street_canyon", "munich"):
        for S in (0.0, 0.3, 0.7):
            sc, ntri, geo = build(name, s_override=S)
            t_off, n_off = timeit(solver, sc, SPS_BASE, DEPTH_BASE, diffuse_reflection=False)
            t_on, n_on = timeit(solver, sc, SPS_BASE, DEPTH_BASE, diffuse_reflection=True)
            s_test.setdefault(name, {})[f"S={S}"] = dict(
                off_s=t_off, on_s=t_on, x=round(t_on / t_off, 2),
                n_paths_off=n_off, n_paths_on=n_on)
            print(f"  [확산] {name:22s} S={S}  off {t_off:.3f} → on {t_on:.3f} s "
                  f"(×{t_on/t_off:.2f})  경로 {n_off} → {n_on}")

    doc = {"_meta": {
        "generator": "benchmark/env_scene_cost_v2_0819.py",
        "generated_kst": time.strftime("%Y-%m-%d %H:%M:%S (UTC+9)",
                                       time.gmtime(time.time() + 9 * 3600)),
        "role_ko": "환경 씬 크기·광선 수·깊이·확산 산란이 각각 비용을 얼마나 늘리나 — 실측",
        "gpu_used": True, "cuda_visible": os.environ.get("CUDA_VISIBLE_DEVICES", "(전체)"),
        "sionna": __import__("sionna").__version__,
        "protocol_ko": (f"기준 = max_depth {DEPTH_BASE} · samples_per_src {SPS_BASE:,} · "
                        f"{N_REP} 회 중 첫 판(컴파일) 버리고 중앙값 · Tx·Rx 는 지상 위 두 점"),
        "supersedes": "outputs/env_scene_cost_0819.json (경로 0~4 개 · S 미확인 — 폐기)",
        "elapsed_s": round(time.time() - t00, 1)},
        "scenes": rows, "diffuse_with_S_override": s_test, "notes": notes}
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
    print(f"\nsaved {OUT}")


if __name__ == "__main__":
    main()
