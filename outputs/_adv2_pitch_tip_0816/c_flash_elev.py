# -*- coding: utf-8 -*-
"""ⓑ 심화 — 비틀림 폭이 «플래시 봉우리» 를 깎는다면 **어느 앙각에서** 깎나.

앞의 b_flash.py 가 el −30·0·−60 에서 «폭을 0 으로 만들어도 봉우리가 0.5 dB밖에 안 움직인다»
를 냈다. 왜 그런지 손으로 따져 보면 이유가 분명하다:
  날의 면 법선은 회전축에서 θ(r)(≈7~20°) 만큼 기운 원뿔을 훑는다. 후방산란 정반사는
  «시선 = 법선» 일 때 나므로, 면 정반사가 가능한 앙각은 |el| ≈ 90° − θ ≈ 70~83° 뿐이다.
  el −30 에서는 **면 정반사가 애초에 불가능**하다 → 거기서 재면 비틀림에 둔감한 게 당연하다.
그래서 감사의 메커니즘이 사는 자리(나딧 근처)를 포함해 앙각을 훑는다. 폭 모형이 참이라면
그 근처에서 legacy(9.3°)가 dji(5.2°)보다 봉우리가 낮아야 한다.
⛔ 저장소 코드 무변경. GPU 미사용.
"""
import json
import sys

import numpy as np

sys.path[:0] = ["/workspace/sionna/src"]
import drone_cad as dc            # noqa: E402
import drones as dr               # noqa: E402
from rcs_po import mesh_to_points, C0   # noqa: E402

OUT = "/workspace/sionna/outputs/_adv2_pitch_tip_0816/c_flash_elev.json"
FC = 3.5e9
LAM = C0 / FC
KK = 2 * np.pi / LAM


def look(az_deg, el_deg):
    az, el = np.radians(az_deg), np.radians(el_deg)
    return np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])


def theta_deg(law, spec, rr):
    R = spec.prop_dia_mm / 2000.0
    P = float(spec.prop_pitch_in) * 0.0254
    pw = dc.PITCH_LAWS[law]
    k = np.interp(rr, pw["rr"], pw["k"])
    return np.degrees(np.arctan(k * P / (2 * np.pi * rr * R)))


def add_gradient_law(name, g, spec):
    R = spec.prop_dia_mm / 2000.0
    P = float(spec.prop_pitch_in) * 0.0254
    rr = np.linspace(0.05, 1.0, 120)
    th = np.radians(theta_deg("legacy", spec, rr))
    th75 = float(np.interp(0.75, rr, th))
    thg = np.clip(th75 + g * (th - th75), np.radians(0.3), np.radians(80.0))
    dc.PITCH_LAWS[name] = dict(rr=tuple(rr),
                               k=tuple(2 * np.pi * rr * R * np.tan(thg) / P),
                               source=f"scratch g={g}")
    return name


def prep(spec, law, div=16.0, n_sec=26, hub=True):
    m = dr.build_propeller(spec, n=n_sec, pitch_law=law)
    if not hub:
        # 허브 없이 날만 — 허브가 봉우리를 가리는지 가른다
        R = spec.prop_dia_mm / 2000.0
        P = float(spec.prop_pitch_in) * 0.0254
        bl = dc._blade(R, root_frac=0.070, chord_max=dc.CHORD_MAX_OVER_R, pitch_m=P,
                       n_sec=n_sec * 2, pitch_law=law)
        v = np.asarray(bl.vertices, float)
        f = np.asarray(bl.faces, np.int64)
        c, s = -1.0, 0.0
        Rz = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])

        class _M:
            pass
        m = _M()
        m.v = np.vstack([v, v @ Rz.T])
        m.f = np.vstack([f, f + len(v)])
    return mesh_to_points(m, LAM / div)


def sigma_phi(pts, el_deg, blades=2, n_phi=720, beta_deg=0.0):
    P, N, dA = pts
    ut, us = look(0.0, el_deg), look(beta_deg, el_deg)
    phis = np.linspace(0.0, 360.0 / blades, n_phi, endpoint=False)
    E = np.empty(n_phi, complex)
    for a0 in range(0, n_phi, 240):
        b0 = min(a0 + 240, n_phi)
        t = np.radians(-phis[a0:b0])
        c, s = np.cos(t), np.sin(t)
        Rm = np.zeros((b0 - a0, 3, 3))
        Rm[:, 0, 0] = c; Rm[:, 0, 1] = -s; Rm[:, 1, 0] = s; Rm[:, 1, 1] = c; Rm[:, 2, 2] = 1.0
        Ut, Us = Rm @ ut, Rm @ us
        NT, NS = N @ Ut.T, N @ Us.T
        E[a0:b0] = (np.where((NT > 0) & (NS > 0), NT, 0.0) * dA[:, None]
                    * np.exp(1j * KK * (P @ (Ut + Us).T))).sum(0)
    sig = (4 * np.pi / LAM ** 2) * np.abs(E) ** 2
    pk = float(sig.max())
    d = float(phis[1] - phis[0])
    return dict(peak_dbsm=round(10 * np.log10(pk), 3),
                mean_dbsm=round(10 * np.log10(float(sig.mean())), 3),
                contrast_db=round(10 * np.log10(pk / float(sig.mean())), 3),
                w3db_deg=round(float((sig >= pk / 2).sum() * d), 3))


def main():
    key = "matrice4e"
    spec = dr.DRONES[key]
    laws = ["legacy", "dji_mini2", add_gradient_law("g0", 0.0, spec),
            add_gradient_law("g0.5", 0.5, spec), add_gradient_law("g1.5", 1.5, spec),
            add_gradient_law("g2", 2.0, spec)]
    els = [0, -15, -30, -45, -55, -60, -65, -70, -72.5, -75, -77.5, -80, -82.5, -85, -87.5, -90]
    res = {"_meta": dict(drone=key, fc_hz=FC, n_phi=720, div="lam/16",
                         q="비틀림 폭이 봉우리를 깎는다면 어느 앙각에서 깎나",
                         geometry_note="면 정반사 가능 앙각 |el| ≈ 90° − θ(r)")}
    RR = np.array([0.3, 0.5, 0.6, 0.7, 0.75, 0.8, 0.9, 1.0])
    res["theta_profile_deg"] = {law: [round(float(x), 2) for x in theta_deg(law, spec, RR)]
                                for law in laws}
    res["theta_rr"] = RR.tolist()
    res["twist_spread_0p6_0p9_deg"] = {
        law: round(float(theta_deg(law, spec, np.array([0.6]))[0]
                         - theta_deg(law, spec, np.array([0.9]))[0]), 3) for law in laws}
    res["specular_el_window_deg"] = {
        law: [round(90.0 - float(theta_deg(law, spec, np.array([0.9]))[0]), 2),
              round(90.0 - float(theta_deg(law, spec, np.array([0.3]))[0]), 2)] for law in laws}
    for hub in (True, False):
        tag = "with_hub" if hub else "blades_only"
        res[tag] = {}
        for law in laws:
            pts = prep(spec, law, hub=hub)
            res[tag][law] = {f"el{e:g}": sigma_phi(pts, e) for e in els}
            print(f"[{tag}] {law:8s} " + " ".join(
                f"{e:g}:{res[tag][law][f'el{e:g}']['peak_dbsm']:.1f}" for e in els), flush=True)
    json.dump(res, open(OUT, "w"), ensure_ascii=False, indent=1)

    print("\n=== 봉우리 dB — legacy 대비 (양수 = 그 법칙이 더 밝다) ===")
    for tag in ("with_hub", "blades_only"):
        print(f"[{tag}]  Δθ:", res["twist_spread_0p6_0p9_deg"])
        for law in laws[1:]:
            d = [res[tag][law][f"el{e:g}"]["peak_dbsm"] - res[tag]["legacy"][f"el{e:g}"]["peak_dbsm"]
                 for e in els]
            print(f"  {law:9s} " + " ".join(f"{e:g}:{x:+.2f}" for e, x in zip(els, d)))


if __name__ == "__main__":
    main()
