# -*- coding: utf-8 -*-
"""refute_nearfield_curvature.py — «근접장 파면 곡률이 진짜 기전이고 실측과 0.24 dB 로 맞는다» 반증 시험.

GPU 안 씀. sbr_field 호출 없음. 기존 원장 안 건드리고 outputs/refute_nearfield_curvature.json 새로 씀.

시험 항목
  T1  원장 숫자 재현 (proxy nadir spherical 10 m, measured el−90)
  T2  ⭐같은 대리모형을 **모든 앙각**에 적용 — 나딧에서만 맞는 것인지
  T3  동체·프롭 분해의 실제 의미 (DC 상쇄 여부)
  T4  «구면파일 때만» 이 참인가 — 평면파 + 미세 조준오차
  T5  대리모형의 임의 선택(위상중심 c0)에 0.24 dB 가 견디는가
"""
from __future__ import annotations
import json, os, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

TJ = json.load(open(f"{ROOT}/outputs/report07_three_engines.json"))["_meta"]
PRF = float(TJ["prf_hz"]); FFL = float(TJ["f_flash_hz"]); N = int(TJ["n"])
RPMS = np.asarray(TJ["rpm_per_rotor"], float)
FC, RANGE_M = 3.5e9, 10.0
LAM = 2.998e8 / FC
K = 2 * np.pi / LAM


def _facets(v, f):
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    n = np.cross(b - a, c - a)
    ar2 = np.linalg.norm(n, axis=1)
    return n / (ar2[:, None] + 1e-300), 0.5 * ar2, (a + b + c) / 3.0


def acdc(x):
    x = np.asarray(x, complex)
    return round(float(10 * np.log10(np.mean(np.abs(x / x.mean() - 1.0) ** 2) + 1e-300)), 2)


def main():
    from articulated_fast import FastPoser, rotor_phases
    from drones import DRONES
    fp = FastPoser(DRONES[TJ.get("drone", "matrice4e")])
    ph = rotor_phases(np.arange(N) / PRF, RPMS, fp.dirs)
    f = np.asarray(fp.f); g = np.asarray(fp.g)
    isp = g == "prop"
    c0 = 0.5 * (fp.v.min(0) + fp.v.max(0))
    ELS = [0.0, -15.0, -30.0, -45.0, -60.0, -75.0, -90.0]
    U = {e: np.array([np.cos(np.radians(e)), 0.0, np.sin(np.radians(e))]) for e in ELS}
    # T4: 평면파 미세 조준오차 (곡률 0)
    TILT = [-90.0, -89.8, -89.5, -89.0, -88.5, -88.0, -87.0, -86.0]
    UT = {e: np.array([np.cos(np.radians(e)), 0.0, np.sin(np.radians(e))]) for e in TILT}
    # T5: 위상중심 대안 (bbox 중심 대신 면적가중 중심 / 원점)
    C_ALT = {"bbox": c0, "origin": np.zeros(3)}

    Ssph = {e: np.zeros(N, complex) for e in ELS}
    Spl_t = {e: np.zeros(N, complex) for e in TILT}
    Sprop = np.zeros(N, complex); Sbody = np.zeros(N, complex)
    Salt = {k: np.zeros(N, complex) for k in C_ALT}
    t0 = time.time()
    for i in range(N):
        v = fp.pose(ph[i]).v
        nn, ar, cen = _facets(v, f)
        for e in ELS:
            uu = U[e]
            w = np.maximum(nn @ uu, 0.0) * ar
            d = np.linalg.norm(cen - (c0 + RANGE_M * uu), axis=1)
            q = w * np.exp(-1j * 2 * K * d)
            Ssph[e][i] = q.sum()
            if e == -90.0:
                Sprop[i] = q[isp].sum(); Sbody[i] = q[~isp].sum()
        u90 = U[-90.0]
        w90 = np.maximum(nn @ u90, 0.0) * ar
        for k, cc in C_ALT.items():
            d = np.linalg.norm(cen - (cc + RANGE_M * u90), axis=1)
            Salt[k][i] = (w90 * np.exp(-1j * 2 * K * d)).sum()
        for e in TILT:
            uu = UT[e]
            ww = np.maximum(nn @ uu, 0.0) * ar
            Spl_t[e][i] = (ww * np.exp(-1j * 2 * K * (cen @ uu))).sum()
        if i and i % 512 == 0:
            print(f"  {i}/{N} {time.time()-t0:.0f}s", flush=True)

    z = np.load(f"{ROOT}/outputs/elevation_sweep_md.npz")
    meas = {e: acdc(z[f"ours/el{int(e):+d}"]) for e in ELS}
    prox = {e: acdc(Ssph[e]) for e in ELS}

    # T3 : DC 상쇄 여부
    mb, mp, mt = Sbody.mean(), Sprop.mean(), (Sbody + Sprop).mean()
    t3 = dict(
        abs_mean_body=float(abs(mb)), abs_mean_prop=float(abs(mp)),
        abs_mean_total=float(abs(mt)),
        total_over_prop_dc_db=round(float(20 * np.log10(abs(mt) / abs(mp))), 2),
        ac_rms_prop=float(np.sqrt(np.mean(np.abs(Sprop - mp) ** 2))),
        ac_rms_body=float(np.sqrt(np.mean(np.abs(Sbody - mb) ** 2))),
        ac_rms_total=float(np.sqrt(np.mean(np.abs(Sbody + Sprop - mt) ** 2))),
    )

    out = dict(
        _meta=dict(
            generator="benchmark/refute_nearfield_curvature.py",
            gpu_ko="GPU 미사용. sbr_field 호출 없음. 기존 원장 미변경.",
            proxy_ko="verify_nadir_flash.py 의 geometry() 와 동일한 평면패싯 PO 대리모형",
            range_m=RANGE_M, fc_hz=FC, n=N, prf_hz=PRF),
        T1_reproduce=dict(proxy_nadir_spherical_10m_db=prox[-90.0],
                          measured_el90_db=meas[-90.0],
                          gap_db=round(prox[-90.0] - meas[-90.0], 2)),
        T2_all_elevations=dict(
            measured_ac_over_dc_db={str(int(e)): meas[e] for e in ELS},
            proxy_spherical_10m_ac_over_dc_db={str(int(e)): prox[e] for e in ELS},
            gap_db={str(int(e)): round(prox[e] - meas[e], 2) for e in ELS},
            abs_gap_median_db=round(float(np.median(
                [abs(prox[e] - meas[e]) for e in ELS])), 2),
            abs_gap_max_db=round(float(np.max(
                [abs(prox[e] - meas[e]) for e in ELS])), 2)),
        T3_body_prop=t3,
        T4_planewave_tilt={f"{e:+.1f}": dict(off_nadir_deg=round(90 + e, 2),
                                             ac_over_dc_db=acdc(Spl_t[e]))
                           for e in TILT},
        T5_phase_center={k: acdc(v) for k, v in Salt.items()},
    )
    p = f"{ROOT}/outputs/refute_nearfield_curvature.json"
    json.dump(out, open(p, "w"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("wrote", p)


if __name__ == "__main__":
    main()
