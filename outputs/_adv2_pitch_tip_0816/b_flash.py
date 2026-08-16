# -*- coding: utf-8 -*-
"""ⓑ 반증 — «외곽 피치각 폭이 넓으면 플래시가 번져 봉우리 −2.2 dB» 대 «커널 민감도 +0.15~+0.82 dB».

감사가 스스로 «어림» 이라 적은 −2.2 dB 는 사실상 10log10(9.2/5.5)=2.24 dB, 즉 «폭에 반비례» 모형이다.
같은 감사가 인용한 커널 민감도(피치 ×1.25)는 **부호가 반대**(+)다. 어느 쪽이 맞는지 직접 잰다.

여기서 하는 것
  (1) 통제 가족 — θ(0.75R) 을 **고정**하고 비틀림 기울기만 g 배(0~2.0). 순수하게 «폭» 만 변한다.
      감사의 메커니즘 그 자체다. peak σ 를 폭에 대해 회귀한다 → «폭에 반비례» 가 맞나?
  (2) 감사가 인용한 통제 — 피치 ×1.25. 이건 폭도 같이 25 % 넓힌다. 폭모형이 맞다면 −0.97 dB
      여야 하는데 감사는 +0.15~+0.82 dB 라고 적었다. **부호가 다르다** — 직접 확인한다.
  (3) 실제 교체안 — pitch_law legacy ↔ dji_mini2 (시위 법칙은 legacy 로 고정해 피치만 본다).
  각각 회전위상 φ 를 촘촘히 훑어 σ(φ) 의 봉우리·폭·평균, 그리고 수렴(점간격 두 벌)을 잰다.

⛔ 저장소 코드 무변경(대안 피치는 이 프로세스 안에서만 PITCH_LAWS 에 임시 키). GPU 미사용.
"""
import json
import sys

import numpy as np

sys.path[:0] = ["/workspace/sionna/src"]
import drone_cad as dc            # noqa: E402
import drones as dr               # noqa: E402
from rcs_po import mesh_to_points, C0   # noqa: E402

OUT = "/workspace/sionna/outputs/_adv2_pitch_tip_0816/b_flash.json"


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
    """θ(0.75R) 고정, 기울기만 g 배 — 폭만 바꾸는 통제."""
    R = spec.prop_dia_mm / 2000.0
    P = float(spec.prop_pitch_in) * 0.0254
    rr = np.linspace(0.05, 1.0, 120)
    th = np.radians(theta_deg("legacy", spec, rr))
    th75 = float(np.interp(0.75, rr, th))
    thg = np.clip(th75 + g * (th - th75), np.radians(0.3), np.radians(80.0))
    k = 2 * np.pi * rr * R * np.tan(thg) / P
    dc.PITCH_LAWS[name] = dict(rr=tuple(rr), k=tuple(k), source=f"scratch g={g}")
    return name


def add_scaled_law(name, mul):
    dc.PITCH_LAWS[name] = dict(rr=dc.PITCH_RR, k=tuple(np.array(dc.PITCH_K) * mul),
                               source=f"scratch pitch x{mul}")
    return name


def sigma_phi(spec, pitch_law, fc, el_deg, beta_deg=0.0, n_phi=3600, div=20.0, n_sec=26):
    lam = C0 / fc
    kk = 2 * np.pi / lam
    m = dr.build_propeller(spec, n=n_sec, pitch_law=pitch_law)
    P, N, dA = mesh_to_points(m, lam / div)
    ut = look(0.0, el_deg)
    us = look(beta_deg, el_deg)
    phis = np.linspace(0.0, 360.0 / spec.prop_blades, n_phi, endpoint=False)
    E = np.empty(n_phi, complex)
    for a0 in range(0, n_phi, 300):
        b0 = min(a0 + 300, n_phi)
        t = np.radians(-phis[a0:b0])
        c, s = np.cos(t), np.sin(t)
        Rm = np.zeros((b0 - a0, 3, 3))
        Rm[:, 0, 0] = c; Rm[:, 0, 1] = -s; Rm[:, 1, 0] = s; Rm[:, 1, 1] = c; Rm[:, 2, 2] = 1.0
        Ut, Us = Rm @ ut, Rm @ us
        NT, NS = N @ Ut.T, N @ Us.T
        PH = np.exp(1j * kk * (P @ (Ut + Us).T))
        E[a0:b0] = (np.where((NT > 0) & (NS > 0), NT, 0.0) * dA[:, None] * PH).sum(0)
    sig = (4 * np.pi / lam ** 2) * np.abs(E) ** 2
    return phis, sig, len(P)


def stats(phis, sig):
    pk = float(sig.max())
    d = float(phis[1] - phis[0])
    return dict(peak_dbsm=round(10 * np.log10(pk), 3),
                mean_dbsm=round(10 * np.log10(float(sig.mean())), 3),
                w3db_deg=round(float((sig >= pk / 2).sum() * d), 3),
                w10db_deg=round(float((sig >= pk / 10).sum() * d), 3),
                peak_over_mean_db=round(10 * np.log10(pk / float(sig.mean())), 3),
                n_local_peaks=int(((sig[1:-1] > sig[:-2]) & (sig[1:-1] > sig[2:])
                                   & (sig[1:-1] > 0.1 * pk)).sum()))


def main():
    key = sys.argv[1] if len(sys.argv) > 1 else "matrice4e"
    spec = dr.DRONES[key]
    RR = np.array([0.6, 0.7, 0.8, 0.9])
    laws = ["legacy", "dji_mini2"]
    for g in (0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0):
        laws.append(add_gradient_law(f"g{g:g}", g, spec))
    laws.append(add_scaled_law("x1.25", 1.25))
    laws.append(add_scaled_law("x0.80", 0.80))

    res = {"_meta": dict(drone=key, fc_hz=3.5e9, n_phi=3600, pt_div="lam/20",
                         note="단일 프로펠러·평면파·순수 PO·PEC. 시위 법칙은 legacy 고정 — 피치만 바뀐다.",
                         twist_metric="Δθ = θ(0.6R) − θ(0.9R) [deg] (감사가 쓴 잣대)"),
           "rows": []}
    cfgs = [("mono_el-30", 3.5e9, -30.0, 0.0), ("mono_el0", 3.5e9, 0.0, 0.0),
            ("mono_el-60", 3.5e9, -60.0, 0.0), ("bi81_el-30", 3.5e9, -30.0, 81.0),
            ("mono_el-30_10GHz", 10e9, -30.0, 0.0)]
    for law in laws:
        th = theta_deg(law, spec, RR)
        row = dict(law=law, theta_deg=[round(float(x), 3) for x in th],
                   twist_spread_deg=round(float(th[0] - th[-1]), 3),
                   theta_75R=round(float(theta_deg(law, spec, np.array([0.75]))[0]), 3))
        for tag, fc, el, be in cfgs:
            ph, sg, npts = sigma_phi(spec, law, fc, el, be)
            row[tag] = stats(ph, sg)
            row[tag]["n_pts"] = npts
        res["rows"].append(row)
        print(f"{law:8s} Δθ={row['twist_spread_deg']:6.2f}°  θ75={row['theta_75R']:5.2f}°  "
              f"mono-30 peak {row['mono_el-30']['peak_dbsm']:7.2f} w3 {row['mono_el-30']['w3db_deg']:5.2f}° "
              f"mean {row['mono_el-30']['mean_dbsm']:7.2f} | el0 peak {row['mono_el0']['peak_dbsm']:7.2f} "
              f"| 10GHz peak {row['mono_el-30_10GHz']['peak_dbsm']:7.2f}", flush=True)

    # 수렴: 점간격 두 벌 · 위상격자 두 벌
    conv = {}
    for div in (12.0, 20.0, 32.0):
        ph, sg, npts = sigma_phi(spec, "legacy", 3.5e9, -30.0, 0.0, n_phi=3600, div=div)
        conv[f"legacy_div{div:g}"] = dict(stats(ph, sg), n_pts=npts)
        ph, sg, npts = sigma_phi(spec, "dji_mini2", 3.5e9, -30.0, 0.0, n_phi=3600, div=div)
        conv[f"dji_div{div:g}"] = dict(stats(ph, sg), n_pts=npts)
    for nph in (1800, 7200):
        ph, sg, _ = sigma_phi(spec, "legacy", 3.5e9, -30.0, 0.0, n_phi=nph)
        conv[f"legacy_nphi{nph}"] = stats(ph, sg)
    res["convergence"] = conv
    json.dump(res, open(OUT, "w"), ensure_ascii=False, indent=1)
    print("\n수렴:", json.dumps({k: v["peak_dbsm"] for k, v in conv.items()}))


if __name__ == "__main__":
    main()
