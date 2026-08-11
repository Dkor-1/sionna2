# -*- coding: utf-8 -*-
"""verify_po_elev_tsladder.py — ⭐**시계열 격자 사다리** (반증 라운드).

앞선 판정은 「AC(블레이드)는 격자에 안 흔들린다 — 격자 오차가 슬로타임 **공통 모드**라
차분인 P_ac 에서 상쇄된다」 고 **주장만** 했다. 재본 적이 없다. 격자 사다리는 **고정 자세
동체 전용**으로만 돌았기 때문에 P_ac 도 winding 도 사다리를 탄 적이 없다.

여기서는 **생산과 같은 전체 표적·전체 자세 계열**을 격자만 바꿔 다시 돌린다.
  · 자세는 생산 4096 중 **8 배 데시메이션**(512 점, 유효 prf 2462.5 Hz).
    −60°(f_tip 636 Hz)·−30°(1102 Hz) 둘 다 나이퀴스트(1231 Hz) 아래라 안전하다.
  · 격자 3 판: λ/12(생산) · λ/12+셀 0.5 이동 · λ/16
  · 판정 대상: P_dc · P_ac · AC−DC · winding(원점 감김) · |f|>4 kHz(“수치 바닥”)

⚠ λ/12 무이동 판은 생산 계열과 **비트 동일**해야 한다(재현 게이트).
"""
from __future__ import annotations
import json, os, sys, time

os.environ.setdefault("SIONNA2_GPU", "2")
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path: sys.path.insert(0, _p)
import numpy as np                                                      # noqa: E402

FC, RANGE_M, LAM = 3.5e9, 10.0, 2.998e8 / 3.5e9
DEC = 8
ELS = (-60.0, -30.0, -15.0)
OUT = f"{ROOT}/outputs/verify_po_elev_tsladder.json"
TJ = json.load(open(f"{ROOT}/outputs/report07_three_engines.json"))["_meta"]
MJ = json.load(open(f"{ROOT}/outputs/elevation_sweep_md.json"))
FTIP = {int(r["el_deg"]): r["f_tip_hz"] for r in MJ["rows"] if r["engine"] == "ours"}


def los(az_deg, el_deg):
    a, e = np.radians(az_deg), np.radians(el_deg)
    return np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])


def stats(E, prf_eff, ftip):
    dc = E.mean(); A = E - dc; n = E.size
    f = np.fft.fftshift(np.fft.fftfreq(n, 1 / prf_eff))
    w = np.hanning(n); w /= np.sqrt((w ** 2).mean())
    S = np.fft.fftshift(np.abs(np.fft.fft(A * w)) ** 2) / n ** 2
    hi = np.abs(f) > 0.9 * (prf_eff / 2)          # 스펙트럼 가장자리 = “바닥” 대용
    Pdc, Pac = abs(dc) ** 2, float(np.mean(np.abs(A) ** 2))
    wind = float(np.sum(np.diff(np.unwrap(np.angle(E)))) / (2 * np.pi))
    return dict(P_dc_db=round(10 * np.log10(Pdc), 2),
                P_ac_db=round(10 * np.log10(Pac), 2),
                ac_over_dc_db=round(10 * np.log10(Pac / Pdc), 2),
                winding_turns=round(wind, 3),
                unwrap_ptp_deg=round(float(np.ptp(np.unwrap(np.angle(E)))) * 180 / np.pi, 1),
                min_abs_over_mean=round(float(np.abs(E).min() / np.abs(E).mean()), 4),
                edge_floor_db=round(10 * np.log10(float(S[hi].sum()) + 1e-300), 2),
                f_tip_hz=round(ftip, 1))


def main():
    from gpu import pick; pick(verbose=False)
    from articulated_fast import FastPoser, rotor_phases
    from drones import DRONES, DRONE_GROUP_MAT
    from rcs_sbr import sbr_field, grid_ref_from

    fp = FastPoser(DRONES[TJ.get("drone", "matrice4e")])
    prf, n = float(TJ["prf_hz"]), int(TJ["n"]); az = float(TJ.get("az_deg", 0.0))
    ph = rotor_phases(np.arange(n) / prf, np.asarray(TJ["rpm_per_rotor"], float), fp.dirs)
    gm = {g: m for g, (m, _) in DRONE_GROUP_MAT.items()}
    poses = [fp.pose(ph[i]) for i in range(0, n, max(1, n // 64))]
    idx = np.arange(0, n, DEC); prf_eff = prf / DEC

    lat = []
    for div, dt in ((12, (0., 0., 0.)), (12, (0.5, 0.5, 0.5)), (16, (0., 0., 0.))):
        d = LAM / div; g0 = grid_ref_from(poses, FC, spacing=d)
        if dt == (0., 0., 0.):
            ref = g0; tag = f"div{div}"
        else:
            ref = dict(ctr=[float(x) for x in np.asarray(g0.ctr, float) + np.asarray(dt) * d],
                       Rout=float(g0.Rout), n=int(g0.n) + 2, spacing=float(d))
            tag = f"div{div}_dith0.5"
        lat.append((tag, d, ref))

    Z = np.load(f"{ROOT}/outputs/elevation_sweep_md.npz")
    res, t0 = {}, time.time()
    for el in ELS:
        u = los(az, el); res[f"el{el:+.0f}"] = {}
        prod = Z[f"ours/el{el:+.0f}"][idx]
        res[f"el{el:+.0f}"]["production_div12_decimated"] = stats(prod, prf_eff, FTIP[int(el)])
        for tag, d, ref in lat:
            E = np.empty(idx.size, complex)
            for j, i in enumerate(idx):
                E[j] = sbr_field(fp.pose(ph[int(i)]), gm, FC, u,
                                 spacing=d, grid_ref=ref, range_m=RANGE_M)
            s = stats(E, prf_eff, FTIP[int(el)])
            if tag == "div12":
                s["bitexact_vs_production"] = bool(np.array_equal(E, prod))
            res[f"el{el:+.0f}"][tag] = s
            print(f"  ✅ el{el:+.0f} {tag}  P_dc={s['P_dc_db']:.2f} P_ac={s['P_ac_db']:.2f} "
                  f"AC-DC={s['ac_over_dc_db']:+.2f} wind={s['winding_turns']:.3f} "
                  f"[{(time.time()-t0)/60:.1f}분]", flush=True)

    spread = {}
    for el in ELS:
        k = f"el{el:+.0f}"; r = res[k]
        tags = [t for t in r if t != "production_div12_decimated"]
        for m in ("P_dc_db", "P_ac_db", "ac_over_dc_db", "winding_turns", "edge_floor_db"):
            v = [r[t][m] for t in tags]
            spread.setdefault(k, {})[m] = dict(vals=v, spread=round(float(max(v) - min(v)), 2))

    json.dump({"_meta": {
        "generator": "benchmark/verify_po_elev_tsladder.py",
        "question_ko": "P_ac(블레이드)·winding 이 격자에 정말 안 흔들리나 — 시계열로 사다리를 탄다",
        "why_ko": "앞선 판정의 「AC 는 공통 모드라 상쇄된다」 는 **주장**이었고 고정 자세 동체 "
                  "전용 사다리로는 검증할 수 없다. 여기서는 전체 표적·전체 자세 계열을 격자만 "
                  "바꿔 다시 돌린다.",
        "decimation": DEC, "prf_eff_hz": prf_eff, "n_poses": int(idx.size),
        "lattices": [t for t, _, _ in lat], "fc_hz": FC, "range_m": RANGE_M,
        "edge_floor_ko": "|f| > 0.9·(prf_eff/2) 의 전력 — 데시메이션 판의 «바닥» 대용"},
        "per_elevation": res, "lattice_spread": spread},
        open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"\n✅ {OUT}")


if __name__ == "__main__":
    main()
