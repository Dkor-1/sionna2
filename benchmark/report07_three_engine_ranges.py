# -*- coding: utf-8 -*-
"""
report07_three_engine_ranges.py — ⭐그림 3(세 엔진 같은 격자)의 **Sionna 팔을 거리 3/8/15 m 로**.

사용자 요청(2026-08-10): 그림 3 이 3 m 하나뿐이니 3 / 8 / 15 m 세 버전으로.
  · 8 m 는 원거리장 경계(2D²/λ ≈ 8.0 m) **바로 위**라 절묘한 선택이다.
  · SBR+PO 두 팔은 표적 앵커 평면파라 거리 무관 — **다시 계산할 것이 Sionna 팔뿐**이다.
    (그 거리 불변이 이 그림의 절반이다 — 두 팔 맵은 세 줄에서 똑같이 반복된다.)

기존 report07_three_engines.npz 의 sbr·po 열과 **같은 슬로타임 격자·같은 로터 회전수**를
그대로 쓰고, Sionna 팔만 세 거리에서 다시 푼다. 기하는 2026-08-10 정정대로
**진짜 모노스태틱(기선 0)** — 원판 그림 3 의 Sionna 팔(기선 0.2 m·3.8°)과 그 점이 다르다
(3 m 줄이 원판과 미묘하게 다른 이유. 본문에 공개한다).

    python benchmark/report07_three_engine_ranges.py
"""
from __future__ import annotations

import json
import os
import sys
import time

os.environ.setdefault("SIONNA2_GPU", "2")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from gpu import pick                                                   # noqa: E402
pick(verbose=True)

import numpy as np                                                     # noqa: E402
import report15_probe as RP                                            # noqa: E402
from articulated_fast import FastPoser, rotor_phases                   # noqa: E402
from drones import DRONES, DRONE_GROUP_MAT, drone_colors               # noqa: E402

FC = 3.5e9
TJ = json.load(open(f"{ROOT}/outputs/report07_three_engines.json"))["_meta"]
RANGES = [3.0, 8.0, 15.0]
SPP = {3.0: 1_000_000, 8.0: 7_100_000, 15.0: 25_000_000}   # (R/3)² 보상


def main():
    spec = DRONES[TJ["drone"]] if "drone" in TJ else DRONES["matrice4e"]
    fp = FastPoser(spec)
    n_rot = len(fp.dirs)
    prf, n = float(TJ["prf_hz"]), int(TJ["n"])
    az, el = float(TJ.get("az_deg", 0.0)), float(TJ.get("el_deg", -15.0))
    rpm0 = float(getattr(spec, "hover_rpm", 6000.0))
    spread = float(TJ["rpm_spread_frac"])
    pattern = np.array([+1.0, -1.0, -0.55, +0.55])
    rpms = rpm0 * (1.0 + spread * np.resize(pattern, n_rot))
    t = np.arange(n) / prf
    ph = rotor_phases(t, rpms, fp.dirs)
    cols = drone_colors(spec)

    print(f"\n═══ {spec.name} · 그림3 격자 재사용(n {n} · PRF {prf:.0f} · 산포 ±{spread:.0%}) · "
          f"진짜 모노스태틱 · 거리 {RANGES} m ═══", flush=True)

    series, meta = {}, {}
    for rng in RANGES:
        spp = SPP[rng]
        E = np.zeros(n, complex)
        npaths = np.zeros(n, int)
        t0 = time.time()
        for i in range(n):
            mv = fp.pose(ph[i])
            m = mv.to_mesh()
            d = os.path.join(RP.SCRATCH, f"{spec.key}_TR{i % 2}")
            paths_obj = m.write_obj_per_group(d, spec.key)
            parts = [RP.Part(name=f"{spec.key}_{g}_{i%2}", obj=p,
                             mat_key=DRONE_GROUP_MAT[g][0], color=cols[g])
                     for g, p in paths_obj.items()]
            sc = RP.build_scene(parts, fc=FC)
            RP.place(sc, az=az, el=el, rng=rng, baseline=0.0)   # ⭐기선 0
            p = RP.rt.PathSolver()(sc, max_depth=1, los=True, specular_reflection=True,
                                   diffuse_reflection=True, refraction=False,
                                   samples_per_src=int(spp),
                                   max_num_paths_per_src=RP.MAX_PATHS, seed=1)
            try:
                aa, tau, _, O = RP.unpack(p)
            except ValueError:                                   # 경로 0 → 빈 배열 가드
                aa = np.zeros(0)
            if aa.size:
                hit = (O != RP.NO_OBJ).any(axis=0) if O.size else np.zeros(aa.size, bool)
                E[i] = complex(np.sum(aa[hit] * np.exp(-1j * 2 * np.pi * FC * tau[hit])))
                npaths[i] = int(hit.sum())
            RP.drop_scratch(d)
            if i and i % 256 == 0:
                elp = time.time() - t0
                print(f"    R={rng:4.0f} m  {i}/{n}  {elp:.0f}s  "
                      f"ETA {(n-i)/i*elp/60:.1f}분", flush=True)
        secs = time.time() - t0
        key = f"R{rng:.0f}"
        series[f"{key}/E"] = E
        series[f"{key}/npaths"] = npaths
        db = 20 * np.log10(np.abs(E) + 1e-30)
        meta[key] = {"range_m": rng, "spp": int(spp), "seconds": round(secs, 1),
                     "paths_median": float(np.median(npaths)),
                     "paths_zero_frac": float((npaths == 0).mean()),
                     "level_db": float(db.mean())}
        print(f"  ✅ R={rng:4.0f} m  {secs/60:.1f}분 · 경로 중앙 {np.median(npaths):.0f} · "
              f"빈 자세 {(npaths==0).mean():.1%}", flush=True)
        np.savez_compressed(f"{ROOT}/outputs/report07_three_engine_ranges.npz", **series)

    json.dump({"_meta": {"generated": time.strftime("%Y-%m-%d %H:%M:%S"),
                         "drone": spec.key, "name": spec.name, "fc_hz": FC,
                         "az_deg": az, "el_deg": el, "n": n, "prf_hz": prf,
                         "f_flash_hz": TJ["f_flash_hz"], "f_tip_hz": TJ["f_tip_hz"],
                         "rpm_spread_frac": spread, "baseline_m": 0.0,
                         "grid_note_ko": "그림3(report07_three_engines) 격자·회전수 재사용 — "
                                         "sbr·po 열은 거리 무관이라 그 원장을 그대로 쓴다",
                         "mono_note_ko": "기선 0 진짜 모노스태틱 — 원판 그림3 Sionna 팔"
                                         "(기선 0.2 m·3.8°)과 다른 점"},
               "ranges": meta},
              open(f"{ROOT}/outputs/report07_three_engine_ranges.json", "w"),
              ensure_ascii=False, indent=1)
    print(f"\n✅ outputs/report07_three_engine_ranges.npz / .json", flush=True)


if __name__ == "__main__":
    main()
