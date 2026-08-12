#!/usr/bin/env python
"""근접장 파면 곡률 주장에 대한 반증 시험 (CPU 전용, GPU 미사용, 기존 원장 미변경).

주장: «10 m 구면파를 넣는 순간에만 변조가 생기고, 그 크기가 실측과 0.24 dB 로 맞는다»
      (outputs/verify_nadir_flash.json → C_D_geometry)

원장에는 구면파 대리모형의 AC/DC 가 **나딧 한 점**에만 있다. 즉 설명하려는 바로 그 점
말고는 검증점이 없다. 이 스크립트는 같은 대리모형을 **다른 앙각에도** 돌려
표본 밖 일치를 본다. 추가로 (a) 평면파 갈래의 각도 등가치, (b) 진폭/위상 갈래,
(c) 사소한 선택(중심·RPM·위상원점)에 대한 0.24 dB 의 견고성을 잰다.
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

TJ = json.load(open(f"{ROOT}/outputs/report07_three_engines.json"))["_meta"]
PRF = float(TJ["prf_hz"]); N = int(TJ["n"]); FFL = float(TJ["f_flash_hz"])
RPMS = np.asarray(TJ["rpm_per_rotor"], float)
FC, RANGE_M = 3.5e9, 10.0
K = 2 * np.pi / (2.998e8 / FC)
ELS = (0.0, -15.0, -30.0, -45.0, -60.0, -75.0, -90.0)
OUT = f"{ROOT}/outputs/falsify_nearfield_curvature.json"


def acdc(x):
    x = np.asarray(x, complex)
    return round(float(10 * np.log10(np.mean(np.abs(x / x.mean() - 1.0) ** 2) + 1e-300)), 2)


def ampphase(x):
    """진폭 갈래 / 위상 갈래 분리 — verify_nadir_flash.decompose 와 같은 규약."""
    d = np.asarray(x, complex) / np.asarray(x, complex).mean() - 1.0
    am, pm = d.real.std(), d.imag.std()
    return dict(am_rms=round(float(am), 5),
                pm_rms_deg=round(float(np.degrees(pm)), 3),
                pm_over_am_db=round(float(20 * np.log10(pm / (am + 1e-300))), 2))


def facets(v, f):
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    n = np.cross(b - a, c - a)
    ar2 = np.linalg.norm(n, axis=1)
    return n / (ar2[:, None] + 1e-300), 0.5 * ar2, (a + b + c) / 3.0


def main():
    from articulated_fast import FastPoser, rotor_phases
    from drones import DRONES
    fp = FastPoser(DRONES[TJ.get("drone", "matrice4e")])
    f = np.asarray(fp.f); g = np.asarray(fp.g)
    isp = g == "prop"
    c0 = 0.5 * (fp.v.min(0) + fp.v.max(0))
    ph = rotor_phases(np.arange(N) / PRF, RPMS, fp.dirs)
    # 변형판: RPM 균일(산포 제거), 위상원점 90° 이동
    ph_eq = rotor_phases(np.arange(N) / PRF, np.full(4, RPMS.mean()), fp.dirs)

    U = {e: np.array([np.cos(np.radians(e)), 0.0, np.sin(np.radians(e))]) for e in ELS}
    # 나딧 주변 평면파 미세각 (등가 각도오차 찾기용)
    FINE = (-90.0, -89.75, -89.5, -89.25, -89.0, -88.5, -88.0, -87.0, -86.0, -85.0)
    UF = {e: np.array([np.cos(np.radians(e)), 0.0, np.sin(np.radians(e))]) for e in FINE}

    Ssph = {e: np.zeros(N, complex) for e in ELS}       # 구면파 10 m, 앙각별
    Spl = {e: np.zeros(N, complex) for e in ELS}        # 평면파, 앙각별
    Sfine = {e: np.zeros(N, complex) for e in FINE}     # 평면파 미세각
    Ssph_eq = np.zeros(N, complex)                      # 나딧, RPM 균일
    Ssph_c = np.zeros(N, complex)                       # 나딧, 중심을 무게중심으로
    Ssph_prop_eq = np.zeros(N, complex)                 # 나딧, 프롭만 + RPM 균일

    TX = {e: c0 + RANGE_M * U[e] for e in ELS}
    t0 = time.time()
    for i in range(N):
        v = fp.pose(ph[i]).v
        nn, ar, cen = facets(v, f)
        cg = (cen * ar[:, None]).sum(0) / ar.sum()
        for e in ELS:
            u = U[e]
            w = np.maximum(nn @ u, 0.0) * ar
            Ssph[e][i] = (w * np.exp(-1j * 2 * K *
                                     np.linalg.norm(cen - TX[e], axis=1))).sum()
            Spl[e][i] = (w * np.exp(-1j * 2 * K * (cen @ u))).sum()
        for e in FINE:
            u = UF[e]
            w = np.maximum(nn @ u, 0.0) * ar
            Sfine[e][i] = (w * np.exp(-1j * 2 * K * (cen @ u))).sum()
        # 중심 선택 민감도 (나딧, 구면 10 m, 송신점을 무게중심 기준으로)
        u = U[-90.0]; w = np.maximum(nn @ u, 0.0) * ar
        Ssph_c[i] = (w * np.exp(-1j * 2 * K *
                                np.linalg.norm(cen - (cg + RANGE_M * u), axis=1))).sum()
        # RPM 균일판
        v2 = fp.pose(ph_eq[i]).v
        n2, a2, c2 = facets(v2, f)
        w2 = np.maximum(n2 @ u, 0.0) * a2
        q2 = w2 * np.exp(-1j * 2 * K * np.linalg.norm(c2 - TX[-90.0], axis=1))
        Ssph_eq[i] = q2.sum(); Ssph_prop_eq[i] = q2[isp].sum()
        if i and i % 512 == 0:
            print(f"  {i}/{N}  {time.time()-t0:.0f}s", flush=True)

    z = np.load(f"{ROOT}/outputs/elevation_sweep_md.npz")
    led = json.load(open(f"{ROOT}/outputs/verify_nadir_flash.json"))

    oos = {}
    for e in ELS:
        key = f"ours/el{e:+.0f}"
        meas = acdc(z[key])
        oos[f"el{e:+.0f}"] = dict(
            measured_sbr_ac_over_dc_db=meas,
            proxy_spherical_10m_db=acdc(Ssph[e]),
            proxy_planewave_db=acdc(Spl[e]),
            error_spherical_db=round(acdc(Ssph[e]) - meas, 2),
            measured_pm_over_am_db=ampphase(z[key])["pm_over_am_db"],
            proxy_spherical_pm_over_am_db=ampphase(Ssph[e])["pm_over_am_db"])

    errs = [abs(v["error_spherical_db"]) for k, v in oos.items() if k != "el-90"]
    out = {
        "_meta": {
            "generator": "benchmark/falsify_nearfield_curvature.py",
            "gpu_ko": "GPU 미사용 — sbr_field 호출 없음, 순수 CPU 기하 대리모형.",
            "claim_ko": "«근접장 파면 곡률이 유일한 기전이고 실측과 0.24 dB 로 맞는다»",
            "ledger_under_test": "outputs/verify_nadir_flash.json → C_D_geometry",
            "same_proxy_ko": "verify_nadir_flash.geometry() 와 같은 평면패싯 PO 대리모형·같은 acdc 정의.",
        },
        "A_out_of_sample": {
            "note_ko": ("원장은 구면 대리모형 AC/DC 를 **나딧에만** 냈다. 같은 대리모형을 "
                        "다른 앙각에도 돌려 표본 밖 일치를 본다."),
            "rows": oos,
            "abs_error_excluding_nadir_db": {
                "median": round(float(np.median(errs)), 2),
                "max": round(float(np.max(errs)), 2),
                "min": round(float(np.min(errs)), 2)},
            "nadir_abs_error_db": abs(oos["el-90"]["error_spherical_db"]),
        },
        "B_planewave_angle_equivalent": {
            "note_ko": ("곡률이 없어도(순수 평면파) 나딧에서 몇 도만 벗어나면 같은 −38 dB 가 "
                        "나온다. 즉 이 잣대는 «곡률» 과 «작은 각도오차» 를 못 가른다."),
            "fine": {f"{e:+.2f}": dict(off_nadir_deg=round(90 + e, 2),
                                       ac_over_dc_db=acdc(Sfine[e])) for e in FINE},
        },
        "C_robustness_of_0p24dB": {
            "note_ko": "0.24 dB 라는 일치가 사소한 선택에 얼마나 견디는가.",
            "baseline_nadir_spherical_db": acdc(Ssph[-90.0]),
            "ledger_value_db": led["C_D_geometry"]["nadir_spherical_10m_ac_over_dc_db"],
            "measured_db": led["C_D_geometry"]["measured_ours_el90_ac_over_dc_db"],
            "tx_ref_centroid_instead_of_bbox_db": acdc(Ssph_c),
            "equal_rpm_no_spread_db": acdc(Ssph_eq),
            "equal_rpm_props_only_db": acdc(Ssph_prop_eq),
        },
        "D_amplitude_vs_phase": {
            "note_ko": ("실측 나딧은 위상 갈래가 진폭 갈래보다 7.37 dB 크다"
                        "(verify_nadir_flash.json B_decomposition['ours/el-90'].pm_over_am_db). "
                        "대리모형이 그 성격까지 재현하는가."),
            "measured_el90": ampphase(z["ours/el-90"]),
            "proxy_spherical_el90": ampphase(Ssph[-90.0]),
        },
    }
    json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1)
    print(json.dumps(out["A_out_of_sample"], ensure_ascii=False, indent=1))
    print(json.dumps(out["B_planewave_angle_equivalent"], ensure_ascii=False, indent=1))
    print(json.dumps(out["C_robustness_of_0p24dB"], ensure_ascii=False, indent=1))
    print(json.dumps(out["D_amplitude_vs_phase"], ensure_ascii=False, indent=1))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
