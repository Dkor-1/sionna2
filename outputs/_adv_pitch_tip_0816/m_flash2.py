# -*- coding: utf-8 -*-
"""플래시 폭이 «비틀림» 때문인가 «회절» 때문인가 — 고각·주파수·기체를 바꿔 가른다.

감사 I7 의 어림은 기하광학 그림(«반경마다 다른 회전각에서 번쩍인다»)에 서 있다. 그 그림이
성립하려면 날이 파장보다 충분히 길어 정반사 띠가 회절한계보다 좁아야 한다.
3.5 GHz 에서 matrice4e 날은 반지름 137 mm = 1.6 λ 뿐이다. 그래서 주파수를 올려 가며
「플래시 폭 ↔ λ/L 회절한계」와 「비틀림 폭」 중 어느 쪽을 따라가는지 본다.
"""
import json
import sys
import numpy as np

sys.path[:0] = ["/workspace/sionna/src", "/workspace/sionna/benchmark"]
import drone_cad                                     # noqa: E402
import drones                                        # noqa: E402
from rcs_po import mesh_to_points, C0                # noqa: E402

OUT = "/tmp/claude-0/-workspace/e9e31991-b542-4f3a-b8e2-570320d555ba/scratchpad/flash2.json"


def look(az_deg, el_deg):
    az, el = np.radians(az_deg), np.radians(el_deg)
    return np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])


def theta_of(k_rr, k_val, rr, P, R):
    return np.arctan(np.interp(rr, k_rr, k_val) * P / (2 * np.pi * rr * R))


def make_gradient_law(name, g, spec):
    R = spec.prop_dia_mm / 2000.0
    P = float(spec.prop_pitch_in) * 0.0254
    rr = np.linspace(0.05, 1.0, 96)
    th = theta_of(drone_cad.PITCH_RR, drone_cad.PITCH_K, rr, P, R)
    th75 = np.interp(0.75, rr, th)
    thg = np.clip(th75 + g * (th - th75), np.radians(0.5), np.radians(80.0))
    drone_cad.PITCH_LAWS[name] = dict(rr=tuple(rr),
                                      k=tuple(2 * np.pi * rr * R * np.tan(thg) / P),
                                      source=f"scratch g={g}")
    return name


def sigma_phi(spec, pitch_law, el_deg, fc, n_phi=3600, blade_div=11.0):
    lam = C0 / fc
    k = 2 * np.pi / lam
    m = drones.build_propeller(spec, n=26, pitch_law=pitch_law)
    P, N, dA = mesh_to_points(m, lam / blade_div)
    u = look(0.0, el_deg)
    phis = np.linspace(0.0, 360.0 / spec.prop_blades, n_phi, endpoint=False)
    E = np.empty(n_phi, complex)
    for a in range(0, n_phi, 150):
        b = min(a + 150, n_phi)
        th = np.radians(phis[a:b])
        c, s = np.cos(-th), np.sin(-th)
        U = np.stack([c * u[0] - s * u[1], s * u[0] + c * u[1], np.full(b - a, u[2])], 1)
        NU = N @ U.T
        E[a:b] = (np.where(NU > 0, NU, 0.0) * dA[:, None]
                  * np.exp(2j * k * (P @ U.T))).sum(0)
    sig = (4 * np.pi / lam ** 2) * np.abs(E) ** 2
    return phis, sig


def stats(phis, sig):
    pk = sig.max()
    d = phis[1] - phis[0]
    return dict(peak_db=float(10 * np.log10(pk)), mean_db=float(10 * np.log10(sig.mean())),
                w3=float((sig >= pk / 2).sum() * d), w10=float((sig >= pk / 10).sum() * d))


def main():
    res = []
    for key in ("matrice4e", "mini2"):
        spec = drones.DRONES[key]
        R = spec.prop_dia_mm / 2000.0
        laws = ["legacy", "dji_mini2", make_gradient_law("g0", 0.0, spec),
                make_gradient_law("g2", 2.0, spec)]
        for fc in (3.5e9, 10e9, 30e9):
            for el in (-30.0, -60.0, 0.0):
                row = dict(drone=key, fc_ghz=fc / 1e9, el=el,
                           R_over_lam=float(R / (C0 / fc)))
                for law in laws:
                    ph, sg = sigma_phi(spec, law, el, fc)
                    row[law] = stats(ph, sg)
                base = row["legacy"]["peak_db"]
                row["d_peak_db"] = {q: round(row[q]["peak_db"] - base, 3) for q in laws}
                res.append(row)
                print(f"{key:10s} {fc/1e9:5.1f} GHz el {el:+5.0f}  R/λ {row['R_over_lam']:5.2f} | "
                      f"peak legacy {base:7.2f}  Δ(dji) {row['d_peak_db']['dji_mini2']:+6.2f}  "
                      f"Δ(g0) {row['d_peak_db']['g0']:+6.2f}  Δ(g2) {row['d_peak_db']['g2']:+6.2f} | "
                      f"w3 legacy {row['legacy']['w3']:5.2f}° g0 {row['g0']['w3']:5.2f}° "
                      f"g2 {row['g2']['w3']:5.2f}°  (λ/2R = {np.degrees(C0/fc/(2*R)):5.2f}°)",
                      flush=True)
    json.dump(res, open(OUT, "w"), indent=1)


if __name__ == "__main__":
    main()
