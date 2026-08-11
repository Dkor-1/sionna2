# -*- coding: utf-8 -*-
"""verify_po_elev_nulls.py — ⭐**−30°·−60° 만 왜 튀나** 를 커널로 직접 판정한다.

사용자(2026-08-11)
> "30, 60 도에서 위상 변동폭이 커지는 이유가 뭐야? … 우리 PO 에 대해 제대로 검증 좀 해봐"

■ 무엇을 재나
앙각 스윕(elevation_sweep_md)의 계열 E(t) 는 «동체(안 도는 것) + 블레이드(도는 것)» 의 합이다.
   E(t) = E_dc  +  E_ac(t)          E_dc = 시간평균(정적) · E_ac = 변조분
«변조 깊이» 나 «0 Hz 몫» 은 **비율**이라 분모(E_dc)가 죽으면 분자가 커진 것처럼 보인다.
그래서 이 스크립트는 **절대 세기**를 갈라 재고, 그 다음 그 세기가 앙각에 어떻게 걸리는지를
**고정 자세**에서 곱게(0.5°) 훑어 널의 위치와 폭을 잰다.

■ 세 가닥 (모두 얼린 격자 · 같은 규약 · 같은 자세)
  total : 그대로              — 생산 경로와 같다
  body  : prop 면만 뺀다      — 도는 것을 없앤 대조군(정점은 그대로 → bbox·격자 동일)
  prop  : prop 면만 남긴다    — 동체를 없앤 대조군(= elevation_sweep_md 의 ours_free)
⚠ body+prop ≠ total 이다(서로의 그림자가 빠지므로). 그건 결함이 아니라 이 대조군의 정의다.

■ 격자 감사
`grid_used` 를 앙각마다 불러 (ctr, Rout, n, spacing) 이 **앙각과 무관하게 얼려 있는지** 를
같이 적는다. 얼려 있지 않으면 앙각 비교에 격자 차이가 섞이므로 그것이 먼저 원인이다.

    SIONNA2_GPU=2 PYTHONPATH=src:benchmark python benchmark/verify_po_elev_nulls.py
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

FC, RANGE_M, DIV = 3.5e9, 10.0, 12
ELS = (0.0, -15.0, -30.0, -45.0, -60.0, -75.0, -90.0)
OUT = f"{ROOT}/outputs/verify_po_elev_nulls.json"
TJ = json.load(open(f"{ROOT}/outputs/report07_three_engines.json"))["_meta"]


def los(az_deg: float, el_deg: float) -> np.ndarray:
    a, e = np.radians(az_deg), np.radians(el_deg)
    return np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])


def main() -> None:
    from gpu import pick
    pick(verbose=False)
    from articulated_fast import FastPoser, rotor_phases
    from drones import DRONES, DRONE_GROUP_MAT
    from rcs_sbr import sbr_field, grid_ref_from, grid_used, _grid_basis

    spec = DRONES[TJ.get("drone", "matrice4e")]
    fp = FastPoser(spec)
    prf, n = float(TJ["prf_hz"]), int(TJ["n"])
    az = float(TJ.get("az_deg", 0.0))
    rpms = np.asarray(TJ["rpm_per_rotor"], float)
    ph = rotor_phases(np.arange(n) / prf, rpms, fp.dirs)
    gm = {g: m for g, (m, _) in DRONE_GROUP_MAT.items()}
    d = (2.998e8 / FC) / DIV
    # ⭐생산과 **같은** 얼린 격자 (같은 64 자세 부분표본)
    gref = grid_ref_from([fp.pose(ph[i]) for i in range(0, n, max(1, n // 64))],
                         FC, spacing=d)

    # ── ① 격자 감사 — 앙각마다 격자가 다시 만들어지나 ────────────────────────
    mv0 = fp.pose(ph[0])
    grid_rows = []
    for el in ELS:
        u = los(az, el)
        gu = grid_used(mv0, FC, u, spacing=d, grid_ref=gref)
        e1, e2 = _grid_basis(u)
        gfree = grid_used(mv0, FC, u, spacing=d, grid_ref=None)
        grid_rows.append(dict(el_deg=el, frozen=gu, unfrozen=gfree,
                              basis_e1=[round(float(x), 6) for x in e1],
                              basis_e2=[round(float(x), 6) for x in e2],
                              basis_tmp_axis="z" if abs(u[2]) < 0.9 else "x"))
    same = all(g["frozen"]["n"] == grid_rows[0]["frozen"]["n"] and
               abs(g["frozen"]["Rout"] - grid_rows[0]["frozen"]["Rout"]) < 1e-12 and
               np.allclose(g["frozen"]["ctr"], grid_rows[0]["frozen"]["ctr"])
               for g in grid_rows)

    # ── ② 고정 자세 · 앙각 0.5° 미세 스윕 · 세 가닥 ─────────────────────────
    keep_prop = np.asarray(fp.g) == "prop"
    fine = np.arange(-90.0, 0.001, 0.5)
    cuts = {}
    t0 = time.time()
    for tag in ("total", "body", "prop"):
        mv = fp.pose(ph[0])
        if tag == "prop":
            mv.f, mv.g = fp.f[keep_prop], fp.g[keep_prop]
        elif tag == "body":
            mv.f, mv.g = fp.f[~keep_prop], fp.g[~keep_prop]
        E = np.zeros(fine.size, complex)
        for i, el in enumerate(fine):
            E[i] = sbr_field(mv, gm, FC, los(az, el), spacing=d,
                             grid_ref=gref, range_m=RANGE_M)
        cuts[tag] = E
        print(f"  ✅ {tag}: {fine.size} 앙각 · {(time.time()-t0)/60:.1f}분", flush=True)

    # ── ③ 널 폭 — 국소 최소와 −3 dB 폭 ──────────────────────────────────────
    def nulls(E, lo=10.0):
        a = 20 * np.log10(np.abs(E) + 1e-300)
        med = float(np.median(a))
        loc = np.where((a[1:-1] < a[:-2]) & (a[1:-1] < a[2:]))[0] + 1
        out = []
        for i in loc:
            if a[i] > med - lo:
                continue
            j = i
            while j > 0 and a[j] < a[i] + 3:
                j -= 1
            kk = i
            while kk < a.size - 1 and a[kk] < a[i] + 3:
                kk += 1
            out.append(dict(el_deg=round(float(fine[i]), 2),
                            depth_below_median_db=round(float(med - a[i]), 2),
                            width_3db_deg=round(float(fine[kk] - fine[j]), 2)))
        return med, out

    fine_rows = []
    for tag in ("total", "body", "prop"):
        med, nn = nulls(cuts[tag])
        fine_rows.append(dict(tag=tag, median_db=round(med, 2), nulls=nn))

    # ── ④ 생산 계열의 DC/AC 절대 분리 ───────────────────────────────────────
    Z = np.load(f"{ROOT}/outputs/elevation_sweep_md.npz")
    ser = []
    for el in ELS:
        E = Z[f"ours/el{el:+.0f}"]
        dc = E.mean(); ac = E - dc
        a = np.abs(E)
        dph = np.diff(np.angle(E))
        dph = (dph + np.pi) % (2 * np.pi) - np.pi
        # 고정 자세 미세 스윕에서 이 앙각의 세 가닥
        i = int(np.argmin(np.abs(fine - el)))
        ser.append(dict(
            el_deg=el,
            P_dc_db=round(float(20 * np.log10(abs(dc) + 1e-300)), 2),
            P_ac_db=round(float(10 * np.log10(np.mean(np.abs(ac) ** 2) + 1e-300)), 2),
            ac_over_dc_db=round(float(10 * np.log10(np.mean(np.abs(ac) ** 2) / abs(dc) ** 2)), 2),
            min_abs_over_mean=round(float(a.min() / a.mean()), 4),
            winding_turns=round(float(dph.sum() / (2 * np.pi)), 3),
            frozen_pose_total_db=round(float(20 * np.log10(abs(cuts["total"][i]) + 1e-300)), 2),
            frozen_pose_body_db=round(float(20 * np.log10(abs(cuts["body"][i]) + 1e-300)), 2),
            frozen_pose_prop_db=round(float(20 * np.log10(abs(cuts["prop"][i]) + 1e-300)), 2)))

    json.dump({"_meta": {
        "generator": "benchmark/verify_po_elev_nulls.py",
        "question_ko": "−30°·−60° 에서 위상변동·변조깊이가 튀는 것이 물리인가 아티팩트인가",
        "fc_hz": FC, "range_m": RANGE_M, "spacing_m": d, "drone": TJ.get("drone"),
        "grid_frozen_across_elevations": bool(same),
        "grid_note_ko": "얼린 격자의 (ctr, Rout, n, spacing) 은 정점만으로 정해지므로 앙각과 "
                        "무관하다. 앙각에 걸리는 것은 격자의 방향(basis)뿐이고 그건 광선이 "
                        "레이더 쪽에서 와야 하므로 물리적 필연이다.",
        "basis_switch_ko": "_grid_basis 는 |u_z|≥0.9(즉 |el|≥64.16°)에서 tmp 축을 z→x 로 "
                           "바꾼다. 즉 −75°·−90° 만 다른 in-plane 회전이다. −30°·−60° 는 "
                           "0°·−15°·−45° 와 **같은** 규약이라 이 전환은 −30/−60 이상의 원인이 "
                           "될 수 없다.",
        "controls_ko": "body = prop 면 제거 · prop = prop 면만 (정점은 그대로 → 격자 동일)"},
        "grid_audit": grid_rows,
        "fine_sweep": {"el_deg": [round(float(x), 2) for x in fine],
                       **{f"{t}_db": [round(float(v), 3) for v in
                                      20 * np.log10(np.abs(cuts[t]) + 1e-300)]
                          for t in ("total", "body", "prop")}},
        "fine_nulls": fine_rows,
        "series_split": ser},
        open(OUT, "w"), ensure_ascii=False, indent=1)

    print(f"\n격자가 앙각에 무관하게 얼려 있나: {same}")
    print(f"\n{'el':>5} {'P_dc':>8} {'P_ac':>8} {'AC−DC':>7} {'min|E|/평균':>11} "
          f"{'감김':>6} | {'고정자세 total':>13} {'body':>8} {'prop':>8}")
    for r in ser:
        print(f"{r['el_deg']:>5.0f} {r['P_dc_db']:>8.1f} {r['P_ac_db']:>8.1f} "
              f"{r['ac_over_dc_db']:>+7.1f} {r['min_abs_over_mean']:>11.3f} "
              f"{r['winding_turns']:>6.2f} | {r['frozen_pose_total_db']:>13.1f} "
              f"{r['frozen_pose_body_db']:>8.1f} {r['frozen_pose_prop_db']:>8.1f}")
    for fr in fine_rows:
        print(f"\n[{fr['tag']}] 중앙값 {fr['median_db']:.1f} dB · 깊은 널:")
        for x in fr["nulls"]:
            print(f"    el {x['el_deg']:>7.2f}°  −{x['depth_below_median_db']:.1f} dB  "
                  f"폭(3dB) {x['width_3db_deg']:.2f}°")
    print(f"\n✅ {OUT}")


if __name__ == "__main__":
    main()
