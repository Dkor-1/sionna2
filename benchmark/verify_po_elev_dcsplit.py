# -*- coding: utf-8 -*-
"""verify_po_elev_dcsplit.py — ⭐**P_dc 를 «동체» 라고 불러도 되나** (반증 라운드).

앞선 판정은 계열을 E(t) = E_dc(동체) + E_ac(t)(블레이드) 로 갈랐다. 그런데
**도는 블레이드도 DC 를 가진다** — 한 바퀴 평균 ⟨E_prop⟩ 은 0 이 아니다. 따라서
    P_dc = |⟨E_body⟩ + ⟨E_prop⟩|²
이고, 판정이 인용한 고정 자세 대조군은 −60° 에서 **prop(−67.3 dB) 이 body(−71.8 dB) 보다
4.5 dB 세다** — 즉 그 앙각에서 DC 를 동체라고 부를 근거가 자기 자료 안에 없다.

여기서는 **자세 평균된 DC 를 직접 갈라 잰다**: 같은 자세열·같은 얼린 격자로
  body 전용 계열 → ⟨E_body⟩ · prop 전용 계열 → ⟨E_prop⟩
을 따로 구해 생산 DC 와 맞춰 본다. 두 DC 가 서로 상쇄하고 있으면 「동체가 무너졌다」 는
읽기는 유일하지 않다.
⚠ body+prop ≠ total (서로의 그림자가 빠진다) — 크기 비교용이지 합산 검증용이 아니다.
"""
from __future__ import annotations
import json, os, sys, time

os.environ.setdefault("SIONNA2_GPU", "3")
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path: sys.path.insert(0, _p)
import numpy as np                                                      # noqa: E402

FC, RANGE_M, LAM, DIV = 3.5e9, 10.0, 2.998e8 / 3.5e9, 12
DEC = 16
ELS = (-60.0, -15.0)
OUT = f"{ROOT}/outputs/verify_po_elev_dcsplit.json"
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
    gref = grid_ref_from([fp.pose(ph[i]) for i in range(0, n, max(1, n // 64))], FC, spacing=d)
    isprop = np.asarray(fp.g) == "prop"
    idx = np.arange(0, n, DEC)
    Z = np.load(f"{ROOT}/outputs/elevation_sweep_md.npz")

    out = {"_meta": {
        "generator": "benchmark/verify_po_elev_dcsplit.py",
        "question_ko": "생산 DC 가 «동체» 인가, 동체 DC 와 블레이드 DC 의 상쇄인가",
        "decimation": DEC, "n_poses": int(idx.size), "grid": "frozen λ/12",
        "caveat_ko": "body+prop ≠ total (서로의 그림자). 크기 비교용이다."},
        "rows": {}}
    t0 = time.time()
    for el in ELS:
        u = los(az, el); r = {}
        for tag, sel in (("body", ~isprop), ("prop", isprop)):
            E = np.empty(idx.size, complex)
            for j, i in enumerate(idx):
                mv = fp.pose(ph[int(i)]); mv.f, mv.g = fp.f[sel], fp.g[sel]
                E[j] = sbr_field(mv, gm, FC, u, spacing=d, grid_ref=gref, range_m=RANGE_M)
            r[tag] = dict(P_dc_db=round(20 * np.log10(abs(E.mean())), 2),
                          P_ac_db=round(10 * np.log10(np.mean(np.abs(E - E.mean()) ** 2)), 2),
                          dc_phase_deg=round(float(np.degrees(np.angle(E.mean()))), 1))
            print(f"  ✅ el{el:+.0f} {tag}: P_dc={r[tag]['P_dc_db']:.2f} "
                  f"P_ac={r[tag]['P_ac_db']:.2f} arg={r[tag]['dc_phase_deg']:.1f}° "
                  f"[{(time.time()-t0)/60:.1f}분]", flush=True)
        tot = Z[f"ours/el{el:+.0f}"][idx]
        r["total_production"] = dict(P_dc_db=round(20 * np.log10(abs(tot.mean())), 2),
                                     dc_phase_deg=round(float(np.degrees(np.angle(tot.mean()))), 1))
        r["body_minus_prop_dc_db"] = round(r["body"]["P_dc_db"] - r["prop"]["P_dc_db"], 2)
        r["dc_phase_diff_deg"] = round(abs(((r["body"]["dc_phase_deg"] -
                                             r["prop"]["dc_phase_deg"]) + 180) % 360 - 180), 1)
        out["rows"][f"el{el:+.0f}"] = r
    json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"\n✅ {OUT}")


if __name__ == "__main__":
    main()
