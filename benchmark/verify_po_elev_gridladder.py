# -*- coding: utf-8 -*-
"""verify_po_elev_gridladder.py — ⭐**−31°·−60° 의 깊은 널이 물리인가 격자인가.**

`verify_po_elev_nulls.py` 가 찾은 널(동체 전용, 3 dB 폭 1~2.5°)이 **표본격자의 산물**일
수 있다. 깊은 널은 «거의 완전한 상쇄» 라 이산 표본에 가장 민감한 양이기 때문이다.

■ 판정 규약 — 널을 두 축으로 흔든다
  (1) **격자 간격**  λ/12 → λ/16 → λ/20   (판을 각각 새로 얼린다)
  (2) **부분셀 오프셋(dither)**  같은 λ/12 판을 셀의 (0.25, 0.5, 0.37) 만큼 옮긴다
      — 물리는 그대로고 **표본 위상만** 달라진다. 이게 가장 깨끗한 아티팩트 시험이다.
  물리라면 널의 **위치**가 흔들리지 않는다(깊이는 흔들려도 된다 — 널 바닥은 원래 표본에
  민감하다). 위치가 ±0.5° 넘게 움직이거나 널 자체가 사라지면 그건 격자다.

■ 대상: **동체 전용**(prop 면 제거) — 계열의 DC 를 지배하는 것이 동체이므로.

    SIONNA2_GPU=2 PYTHONPATH=src:benchmark python benchmark/verify_po_elev_gridladder.py
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

import numpy as np                                                      # noqa: E402

FC, RANGE_M = 3.5e9, 10.0
LAM = 2.998e8 / FC
OUT = f"{ROOT}/outputs/verify_po_elev_gridladder.json"
TJ = json.load(open(f"{ROOT}/outputs/report07_three_engines.json"))["_meta"]

ELV = np.unique(np.concatenate([np.arange(-70.0, -24.99, 0.5),
                                np.arange(-62.0, -57.99, 0.1),
                                np.arange(-33.0, -28.99, 0.1)]))


def los(az_deg, el_deg):
    a, e = np.radians(az_deg), np.radians(el_deg)
    return np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])


def main() -> None:
    from gpu import pick
    pick(verbose=False)
    from articulated_fast import FastPoser, rotor_phases
    from drones import DRONES, DRONE_GROUP_MAT
    from rcs_sbr import sbr_field, grid_ref_from

    spec = DRONES[TJ.get("drone", "matrice4e")]
    fp = FastPoser(spec)
    prf, n = float(TJ["prf_hz"]), int(TJ["n"])
    az = float(TJ.get("az_deg", 0.0))
    ph = rotor_phases(np.arange(n) / prf, np.asarray(TJ["rpm_per_rotor"], float), fp.dirs)
    gm = {g: m for g, (m, _) in DRONE_GROUP_MAT.items()}
    poses = [fp.pose(ph[i]) for i in range(0, n, max(1, n // 64))]

    keep = np.asarray(fp.g) == "prop"
    mv = fp.pose(ph[0])
    mv.f, mv.g = fp.f[~keep], fp.g[~keep]          # ⭐동체 전용(정점은 그대로)

    runs = []
    for div in (12, 16, 20):
        d = LAM / div
        g0 = grid_ref_from(poses, FC, spacing=d)
        dithers = [(0.0, 0.0, 0.0)] if div != 12 else [
            (0.0, 0.0, 0.0), (0.25, 0.25, 0.25), (0.5, 0.5, 0.5), (0.37, -0.19, 0.43)]
        for dt in dithers:
            ctr = np.asarray(g0.ctr, float) + np.asarray(dt, float) * d
            ref = dict(ctr=[float(x) for x in ctr], Rout=float(g0.Rout),
                       n=int(g0.n) + 2, spacing=float(d))   # +2 칸: 이동분 덮개 확보
            runs.append((div, d, dt, ref))

    res = {}
    t0 = time.time()
    for div, d, dt, ref in runs:
        tag = f"div{div}" + ("" if dt == (0.0, 0.0, 0.0) else
                             f"_dith{dt[0]:+.2f}{dt[1]:+.2f}{dt[2]:+.2f}")
        E = np.zeros(ELV.size, complex)
        for i, el in enumerate(ELV):
            E[i] = sbr_field(mv, gm, FC, los(az, el), spacing=d,
                             grid_ref=ref, range_m=RANGE_M)
        res[tag] = E
        print(f"  ✅ {tag}  n={ref['n']}  rays={ref['n']**2}  "
              f"{(time.time()-t0)/60:.1f}분", flush=True)

    # ── 두 널을 각각 «국소 최소 위치·깊이» 로 잰다 ───────────────────────────
    def probe(E, lo, hi):
        a = 20 * np.log10(np.abs(E) + 1e-300)
        med = float(np.median(a))
        s = (ELV >= lo) & (ELV <= hi)
        i = int(np.where(s)[0][np.argmin(a[s])])
        return dict(el_min_deg=round(float(ELV[i]), 2),
                    depth_below_median_db=round(float(med - a[i]), 2),
                    level_db=round(float(a[i]), 2), median_db=round(med, 2))

    rows = []
    for tag, E in res.items():
        rows.append(dict(tag=tag,
                         null60=probe(E, -62.0, -58.0),
                         null31=probe(E, -33.0, -29.0),
                         ref15=round(float(20 * np.log10(abs(E[int(np.argmin(np.abs(ELV + 45.0)))]) + 1e-300)), 2)))

    base = res["div12"]
    for r, (tag, E) in zip(rows, res.items()):
        m = min(base.size, E.size)
        c = np.abs(np.vdot(base[:m], E[:m])) / (np.linalg.norm(base[:m]) * np.linalg.norm(E[:m]))
        r["coh_vs_div12"] = round(float(c), 4)

    e60 = [r["null60"]["el_min_deg"] for r in rows]
    e31 = [r["null31"]["el_min_deg"] for r in rows]
    d60 = [r["null60"]["depth_below_median_db"] for r in rows]
    d31 = [r["null31"]["depth_below_median_db"] for r in rows]
    verdict = dict(
        null60_el_spread_deg=round(float(max(e60) - min(e60)), 2),
        null31_el_spread_deg=round(float(max(e31) - min(e31)), 2),
        null60_depth_spread_db=round(float(max(d60) - min(d60)), 2),
        null31_depth_spread_db=round(float(max(d31) - min(d31)), 2),
        null60_persists_all=bool(min(d60) > 6.0),
        null31_persists_all=bool(min(d31) > 6.0))

    json.dump({"_meta": {
        "generator": "benchmark/verify_po_elev_gridladder.py",
        "question_ko": "동체 전용 앙각 패턴의 −31°·−60° 깊은 널이 물리인가 격자인가",
        "fc_hz": FC, "range_m": RANGE_M, "target": "body_only (prop 면 제거)",
        "criterion_ko": "물리면 널 **위치**가 격자를 바꿔도 안 움직인다(±0.5° 안). "
                        "깊이는 흔들려도 된다 — 널 바닥은 원래 이산표본에 민감하다.",
        "dither_ko": "같은 λ/12 판을 셀 단위로 옮긴 것 — 물리는 그대로, 표본 위상만 다르다"},
        "rows": rows, "verdict": verdict,
        "el_deg": [round(float(x), 2) for x in ELV],
        "curves_db": {t: [round(float(v), 3) for v in 20 * np.log10(np.abs(E) + 1e-300)]
                      for t, E in res.items()}},
        open(OUT, "w"), ensure_ascii=False, indent=1)

    print(f"\n{'판':>26} {'널@−60':>18} {'널@−31':>18} {'−45 기준':>9} {'coh':>6}")
    for r in rows:
        a, b = r["null60"], r["null31"]
        print(f"{r['tag']:>26} {a['el_min_deg']:>7.2f}° −{a['depth_below_median_db']:>5.1f}dB "
              f"{b['el_min_deg']:>9.2f}° −{b['depth_below_median_db']:>5.1f}dB "
              f"{r['ref15']:>9.1f} {r['coh_vs_div12']:>6.3f}")
    print("\n판정:", json.dumps(verdict, ensure_ascii=False))
    print(f"\n✅ {OUT}")


if __name__ == "__main__":
    main()
