# -*- coding: utf-8 -*-
"""ⓑ 마무리 — 감사의 «플래시» 를 **저장소 자신의 플래시 잣대**로 잰다.

b_flash/c_flash_elev 는 σ(φ) 봉우리를 봤다. 감사가 말한 «플래시» 는 마이크로도플러의
시간축 사건이므로, 저장소가 실제로 쓰는 지표(microdoppler_nearfield.md_metrics 의
flash_contrast_db · fd_edge_hz · harmonic_frac)로도 같은 비교를 한다.
⛔ 저장소 코드 무변경. GPU 미사용.
"""
import json
import sys

import numpy as np

sys.path[:0] = ["/workspace/sionna/src", "/workspace/sionna/benchmark"]
import drone_cad as dc                        # noqa: E402
import drones as dr                           # noqa: E402
from rcs_po import mesh_to_points, C0         # noqa: E402
from microdoppler_nearfield import md_metrics  # noqa: E402

OUT = "/workspace/sionna/outputs/_adv2_pitch_tip_0816/f_pitch_md.json"
FC = 3.5e9
LAM = C0 / FC
KK = 2 * np.pi / LAM
PRF = 20000.0
N = 8192


def look(az, el):
    az, el = np.radians(az), np.radians(el)
    return np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])


def theta_deg(law, spec, rr):
    R = spec.prop_dia_mm / 2000.0
    P = float(spec.prop_pitch_in) * 0.0254
    pw = dc.PITCH_LAWS[law]
    return np.degrees(np.arctan(np.interp(rr, pw["rr"], pw["k"]) * P / (2 * np.pi * rr * R)))


def add_gradient(name, g, spec):
    R = spec.prop_dia_mm / 2000.0
    P = float(spec.prop_pitch_in) * 0.0254
    rr = np.linspace(0.05, 1.0, 120)
    th = np.radians(theta_deg("legacy", spec, rr))
    t75 = float(np.interp(0.75, rr, th))
    thg = np.clip(t75 + g * (th - t75), np.radians(0.3), np.radians(80.0))
    dc.PITCH_LAWS[name] = dict(rr=tuple(rr), k=tuple(2 * np.pi * rr * R * np.tan(thg) / P),
                               source=f"scratch g={g}")
    return name


def series(spec, law, el, rpm, beta=0.0):
    m = dr.build_propeller(spec, n=30, pitch_law=law)
    P, Nn, dA = mesh_to_points(m, LAM / 18.0)
    ut, us = look(0.0, el), look(beta, el)
    t = np.arange(N) / PRF
    ang = 2 * np.pi * (rpm / 60.0) * t
    E = np.empty(N, complex)
    for a0 in range(0, N, 256):
        b0 = min(a0 + 256, N)
        th = -ang[a0:b0]
        c, s = np.cos(th), np.sin(th)
        Rm = np.zeros((b0 - a0, 3, 3))
        Rm[:, 0, 0] = c; Rm[:, 0, 1] = -s; Rm[:, 1, 0] = s; Rm[:, 1, 1] = c; Rm[:, 2, 2] = 1.0
        Ut, Us = Rm @ ut, Rm @ us
        NT, NS = Nn @ Ut.T, Nn @ Us.T
        E[a0:b0] = (np.where((NT > 0) & (NS > 0), NT, 0.0) * dA[:, None]
                    * np.exp(1j * KK * (P @ (Ut + Us).T))).sum(0)
    return E


def main():
    spec = dr.DRONES["matrice4e"]
    rpm = float(spec.hover_rpm)
    R = spec.prop_dia_mm / 2000.0
    laws = ["legacy", "dji_mini2", add_gradient("g0", 0.0, spec), add_gradient("g2", 2.0, spec)]
    res = {"_meta": dict(drone="matrice4e", fc=FC, prf=PRF, n=N, rpm=rpm,
                         metric="src/microdoppler_nearfield.py::md_metrics (저장소 구현 그대로)")}
    RRs = np.array([0.6, 0.9])
    for el, beta in ((-30.0, 0.0), (-60.0, 0.0), (-30.0, 81.0)):
        f_tip = 2 * (2 * np.pi * (rpm / 60) * R) / LAM * np.cos(np.radians(el))
        tag = f"el{el:g}_beta{beta:g}"
        res[tag] = dict(f_tip_hz=round(f_tip, 2), rows={})
        for law in laws:
            E = series(spec, law, el, rpm, beta)
            mm = md_metrics(E, PRF, flash_hz=2 * (rpm / 60.0), f_tip=f_tip)
            th = theta_deg(law, spec, RRs)
            res[tag]["rows"][law] = dict(
                twist_spread_deg=round(float(th[0] - th[1]), 3),
                flash_contrast_db=round(float(mm["flash_contrast_db"]), 3),
                fd_edge_hz=round(float(mm["fd_edge_hz"]), 2),
                harmonic_frac=round(float(mm["harmonic_frac"]), 4),
                dc_ac_db=round(float(mm["dc_ac_db"]), 3),
                ac_energy_db=round(10 * np.log10(float(mm["ac_energy"])), 3),
                peak_sigma_dbsm=round(10 * np.log10((4 * np.pi / LAM ** 2)
                                                    * float(np.abs(E).max() ** 2)), 3))
            r = res[tag]["rows"][law]
            print(f"{tag:16s} {law:9s} Δθ={r['twist_spread_deg']:6.2f}° "
                  f"flashC {r['flash_contrast_db']:6.2f} dB  fd_edge {r['fd_edge_hz']:8.1f} "
                  f"harm {r['harmonic_frac']:.4f}  ACenergy {r['ac_energy_db']:8.2f} "
                  f"peakσ {r['peak_sigma_dbsm']:7.2f}", flush=True)
    json.dump(res, open(OUT, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
