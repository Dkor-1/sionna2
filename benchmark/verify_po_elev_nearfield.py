# -*- coding: utf-8 -*-
"""verify_po_elev_nearfield.py — ⭐**널이 근거리장 근사의 산물인가**를 시험한다 (반증 라운드).

앞선 판정은 −60° 동체 널의 «위치» 를 물리로 올렸다. 근거는 두 개다 —
격자 사다리 6 판에서 살아남았고, 광선을 안 쏘는 기하 PO 도 같은 각을 냈다.
**둘 다 같은 조명 모형을 쓴다.** 스윕은 R = 10 m 구면파인데 원거리장 경계는 2D²/λ = 14.08 m 다.
게다가 `sbr_field(range_m=…)` 는 위상만 구면으로 주고 **광선은 평행**이며 1/r 확산도 없다 —
스스로 «혼합» 근사임을 문서에 적어 두었다. 그 근사의 2차 위상 오차 k·D²/(4R) 는 표적의
**시선 방향 투영 크기 D** 에 걸리므로 **앙각마다 다르다**(el 0° 는 폭 0.6 m, −90° 는 높이 0.15 m).
⇒ 널은 위상들의 코히어런트 합이 만드는 것이니, 조명 모형을 바꾸면 널이 움직일 수 있다.

시험: 같은 동체 전용 메쉬·같은 얼린 격자로 앙각을 0.5° 로 훑되 조명만 바꾼다.
  (a) range_m = 10.0   구면 위상 (생산과 같음)
  (b) range_m = None   평면파 (원거리장)
  (c) range_m = 30.0   원거리장 밖 구면 위상
널 위치가 널 폭(1~2.5°)보다 크게 움직이면 「위치는 물리」 주장은 성립하지 않는다.
"""
from __future__ import annotations
import json, os, sys, time

os.environ.setdefault("SIONNA2_GPU", "3")
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path: sys.path.insert(0, _p)
import numpy as np                                                      # noqa: E402

FC, LAM, DIV = 3.5e9, 2.998e8 / 3.5e9, 12
ELV = np.arange(-90.0, 0.001, 0.5)
OUT = f"{ROOT}/outputs/verify_po_elev_nearfield.json"
TJ = json.load(open(f"{ROOT}/outputs/report07_three_engines.json"))["_meta"]


def los(az, el):
    a, e = np.radians(az), np.radians(el)
    return np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])


def main():
    from gpu import pick; pick(verbose=False)
    from articulated_fast import FastPoser, rotor_phases
    from drones import DRONES, DRONE_GROUP_MAT
    from rcs_sbr import sbr_field, grid_ref_from

    fp = FastPoser(DRONES[TJ.get("drone", "matrice4e")])
    prf, n = float(TJ["prf_hz"]), int(TJ["n"]); az = float(TJ.get("az_deg", 0.0))
    ph = rotor_phases(np.arange(n) / prf, np.asarray(TJ["rpm_per_rotor"], float), fp.dirs)
    gm = {g: m for g, (m, _) in DRONE_GROUP_MAT.items()}
    d = LAM / DIV
    gref = grid_ref_from([fp.pose(ph[i]) for i in range(0, n, max(1, n // 64))],
                         FC, spacing=d)
    keep = np.asarray(fp.g) == "prop"
    mv = fp.pose(ph[0]); mv.f, mv.g = fp.f[~keep], fp.g[~keep]   # 동체 전용

    res, t0 = {}, time.time()
    for tag, rng in (("sph_10m", 10.0), ("plane_wave", None), ("sph_30m", 30.0)):
        E = np.array([sbr_field(mv, gm, FC, los(az, e), spacing=d,
                                grid_ref=gref, range_m=rng) for e in ELV])
        res[tag] = E
        print(f"  ✅ {tag}  [{(time.time()-t0)/60:.1f}분]", flush=True)

    def probe(E, lo, hi):
        a = 20 * np.log10(np.abs(E) + 1e-300); med = float(np.median(a))
        s = (ELV >= lo) & (ELV <= hi); i = int(np.where(s)[0][np.argmin(a[s])])
        j = i
        while j > 0 and a[j - 1] < a[i] + 3.0: j -= 1
        kk = i
        while kk < a.size - 1 and a[kk + 1] < a[i] + 3.0: kk += 1
        return dict(el_min_deg=round(float(ELV[i]), 2), depth_db=round(med - a[i], 2),
                    level_db=round(float(a[i]), 2), width_3db_deg=round(float(ELV[kk] - ELV[j]), 2))

    out = {"_meta": {
        "generator": "benchmark/verify_po_elev_nearfield.py",
        "question_ko": "−60°·−30° 동체 널이 근거리장 조명 근사의 산물인가",
        "why_ko": "격자 사다리도 기하 PO 도 **같은 조명 모형**을 쓴다. 스윕의 R=10 m 는 "
                  "원거리장 경계 14.08 m 안쪽이고 커널은 위상만 구면·광선은 평행이라 "
                  "혼합 근사다. 그 2차 위상 오차는 시선 투영 크기에 걸리므로 앙각마다 다르다.",
        "els": [float(x) for x in ELV], "body_only": True, "grid": "frozen λ/12"},
        "nulls": {}, "curves_db": {}}
    for tag, E in res.items():
        out["curves_db"][tag] = [round(float(v), 3) for v in 20 * np.log10(np.abs(E) + 1e-300)]
        out["nulls"][tag] = {"null_near_-60": probe(E, -70, -50),
                             "null_near_-30": probe(E, -40, -22),
                             "median_db": round(float(np.median(20 * np.log10(np.abs(E) + 1e-300))), 2)}
    for w in ("null_near_-60", "null_near_-30"):
        p = [out["nulls"][t][w]["el_min_deg"] for t in res]
        dp = [out["nulls"][t][w]["depth_db"] for t in res]
        out["nulls"][w + "_spread"] = dict(el_deg=p, el_spread_deg=round(max(p) - min(p), 2),
                                           depth_db=dp, depth_spread_db=round(max(dp) - min(dp), 2))
    json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1)
    for w in ("null_near_-60", "null_near_-30"):
        print(f"\n{w}:")
        for t in res:
            r = out["nulls"][t][w]
            print(f"   {t:>11}  el={r['el_min_deg']:>7.2f}  depth={r['depth_db']:>6.2f} dB  "
                  f"width3dB={r['width_3db_deg']:>5.2f}°")
        print(f"   → 위치 산포 {out['nulls'][w+'_spread']['el_spread_deg']}° · "
              f"깊이 산포 {out['nulls'][w+'_spread']['depth_spread_db']} dB")
    print(f"\n✅ {OUT}")


if __name__ == "__main__":
    main()
