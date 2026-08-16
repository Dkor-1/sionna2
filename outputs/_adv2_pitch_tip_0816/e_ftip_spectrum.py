# -*- coding: utf-8 -*-
"""ⓒ 반증 — «팁 밴드 면적 −3.10 dB 가 f_tip 지표에 그만큼 들어간다» 가 사실인가.

두 가지를 따로 본다.
  (1) **저장소의 f_tip 은 무엇인가** — 정의를 읽는다(benchmark/elevation_sweep_md.py:f_tip_at).
      운동학량이면 시위·팁 면적이 들어갈 자리가 없다.
  (2) **스펙트럼 세기**는 다른 이야기다 — 팁 끝값만 바꾼 날로 마이크로도플러 시계열을 짓고
      f_tip 근방 대역 전력을 잰다. 팁 밴드 면적비가 그대로 dB 로 나타나나?

⛔ 저장소 코드 무변경(끝값 변형은 이 프로세스 안 리스트). GPU 미사용 — 순수 PO·numpy.
"""
import json
import sys

import numpy as np

sys.path[:0] = ["/workspace/sionna/src", "/workspace/sionna/benchmark"]
import drone_cad as dc                       # noqa: E402
import drones as dr                          # noqa: E402
from rcs_po import mesh_to_points, C0        # noqa: E402
from microdoppler_nearfield import md_metrics  # noqa: E402

OUT = "/workspace/sionna/outputs/_adv2_pitch_tip_0816/e_ftip_spectrum.json"
FC = 3.5e9
LAM = C0 / FC
KK = 2 * np.pi / LAM
PRF = 20000.0
NSAMP = 8192


def look(az_deg, el_deg):
    az, el = np.radians(az_deg), np.radians(el_deg)
    return np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])


def blade_pair(spec, tip_end, law="dji_mini2", n_sec=60):
    """끝값만 바꾼 2날 프로펠러(허브 없음) — 다른 것은 전부 같다."""
    R = spec.prop_dia_mm / 2000.0
    P = float(spec.prop_pitch_in) * 0.0254
    cmax, _ = dc.resolve_chord_max_over_r(spec, law)
    c_rr, c_fr, _ = dc.resolve_chord_profile(spec, law)
    if c_rr is None:
        c_rr, c_fr = dc.BLADE_LAWS[law]["chord_rr"], dc.BLADE_LAWS[law]["chord_frac"]
    c_fr = tuple(list(c_fr)[:-1] + [float(tip_end)])
    bl = dc._blade(R, root_frac=0.070, chord_max=cmax, pitch_m=P, n_sec=n_sec,
                   law=law, chord_rr=c_rr, chord_frac=c_fr)
    v = np.asarray(bl.vertices, float)
    f = np.asarray(bl.faces, np.int64)
    Rz = np.array([[-1.0, 0, 0], [0, -1.0, 0], [0, 0, 1.0]])

    class M:
        pass
    m = M()
    m.v = np.vstack([v, v @ Rz.T])
    m.f = np.vstack([f, f + len(v)])
    return m, R


def band_area_frac(m, R, lo, hi):
    """투영 평면형 면적 중 [lo,hi]·R_max 밴드 몫 (a_tip_planform.py 와 같은 자)."""
    import trimesh
    v2, f2 = trimesh.remesh.subdivide_to_size(m.v, m.f, max_edge=3.5e-4)
    T = v2[f2]
    ar = 0.5 * np.abs(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])[:, 2])
    rc = np.linalg.norm(T.mean(1)[:, :2], axis=1)
    Rm = np.linalg.norm(v2[:, :2], axis=1).max()
    tot = ar.sum()
    sel = (rc >= lo * Rm) & (rc < hi * Rm)
    return float(ar[sel].sum() / tot), float(Rm)


def series(m, el_deg, rpm, beta_deg=0.0, n=NSAMP):
    P, N, dA = mesh_to_points(m, LAM / 18.0)
    ut, us = look(0.0, el_deg), look(beta_deg, el_deg)
    t = np.arange(n) / PRF
    ang = 2 * np.pi * (rpm / 60.0) * t
    E = np.empty(n, complex)
    for a0 in range(0, n, 256):
        b0 = min(a0 + 256, n)
        th = -ang[a0:b0]
        c, s = np.cos(th), np.sin(th)
        Rm = np.zeros((b0 - a0, 3, 3))
        Rm[:, 0, 0] = c; Rm[:, 0, 1] = -s; Rm[:, 1, 0] = s; Rm[:, 1, 1] = c; Rm[:, 2, 2] = 1.0
        Ut, Us = Rm @ ut, Rm @ us
        NT, NS = N @ Ut.T, N @ Us.T
        E[a0:b0] = (np.where((NT > 0) & (NS > 0), NT, 0.0) * dA[:, None]
                    * np.exp(1j * KK * (P @ (Ut + Us).T))).sum(0)
    return E, len(P)


def bandpower(E, f_tip):
    ac = E - E.mean()
    w = np.hanning(len(ac))
    S = np.abs(np.fft.fftshift(np.fft.fft(ac * w))) ** 2
    f = np.fft.fftshift(np.fft.fftfreq(len(ac), 1.0 / PRF))
    out = {}
    for name, lo, hi in [("0.2-0.6ft", 0.2, 0.6), ("0.6-0.8ft", 0.6, 0.8),
                         ("0.8-1.0ft", 0.8, 1.0), ("0.9-1.0ft", 0.9, 1.0),
                         ("1.0-1.2ft", 1.0, 1.2), ("above_ft", 1.0, 8.0),
                         ("total_ac", 0.0, 8.0)]:
        msk = (np.abs(f) >= lo * f_tip) & (np.abs(f) < hi * f_tip)
        out[name] = float(S[msk].sum())
    return out


def main():
    key = "matrice4e"
    spec = dr.DRONES[key]
    rpm = float(spec.hover_rpm)
    R = spec.prop_dia_mm / 2000.0
    res = {"_meta": dict(
        drone=key, fc_hz=FC, prf_hz=PRF, n=NSAMP, rpm=rpm,
        repo_f_tip_definition="f_tip = 2·(2π f_rev R)/λ·cos(el)  — benchmark/elevation_sweep_md.py:f_tip_at()",
        note="시위 법칙은 dji_mini2 곡선 고정, **끝값만** 바꾼다. 허브 없음. 순수 PO·PEC.")}
    tips = [0.05, 0.10, 0.20, 0.30]
    for el in (-30.0, -60.0, 0.0):
        f_tip = 2.0 * (2 * np.pi * (rpm / 60.0) * R) / LAM * np.cos(np.radians(el))
        rows = {}
        for te in tips:
            m, Rb = blade_pair(spec, te)
            a98, Rm = band_area_frac(m, Rb, 0.98, 1.00)
            a90, _ = band_area_frac(m, Rb, 0.90, 1.00)
            a96, _ = band_area_frac(m, Rb, 0.96, 1.00)
            E, npts = series(m, el, rpm)
            bp = bandpower(E, f_tip)
            mm = md_metrics(E, PRF, flash_hz=2 * (rpm / 60.0), f_tip=f_tip)
            rows[f"tip{te:.2f}"] = dict(
                area_frac_0p98_1p00=round(a98, 5), area_frac_0p96_1p00=round(a96, 5),
                area_frac_0p90_1p00=round(a90, 5), n_pts=npts,
                band_db={k: round(10 * np.log10(max(v, 1e-300)), 3) for k, v in bp.items()},
                fd_edge_hz=round(float(mm["fd_edge_hz"]), 2),
                flash_contrast_db=round(float(mm["flash_contrast_db"]), 3),
                harmonic_frac=round(float(mm["harmonic_frac"]), 4),
                dc_ac_db=round(float(mm["dc_ac_db"]), 3))
        base = rows["tip0.10"]
        for k, v in rows.items():
            v["delta_vs_tip0.10_db"] = {kk: round(v["band_db"][kk] - base["band_db"][kk], 3)
                                        for kk in v["band_db"]}
            v["delta_area_0p98_db"] = round(
                10 * np.log10(v["area_frac_0p98_1p00"] / base["area_frac_0p98_1p00"]), 3)
        res[f"el{el:g}"] = dict(f_tip_hz=round(f_tip, 2), rows=rows)
        print(f"\nel {el:g}  f_tip {f_tip:.1f} Hz")
        for k, v in rows.items():
            print(f"  {k}  A(0.98-1)={v['area_frac_0p98_1p00']*100:5.2f}% "
                  f"(Δ{v['delta_area_0p98_db']:+5.2f} dB)  "
                  f"Δ0.8-1.0ft {v['delta_vs_tip0.10_db']['0.8-1.0ft']:+6.2f} dB  "
                  f"Δ0.9-1.0ft {v['delta_vs_tip0.10_db']['0.9-1.0ft']:+6.2f}  "
                  f"Δabove {v['delta_vs_tip0.10_db']['above_ft']:+6.2f}  "
                  f"Δtot {v['delta_vs_tip0.10_db']['total_ac']:+6.2f}  "
                  f"fd_edge {v['fd_edge_hz']:7.1f}  flashC {v['flash_contrast_db']:5.2f}", flush=True)
    json.dump(res, open(OUT, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
