# -*- coding: utf-8 -*-
"""⭐ 감사 I7 의 «어림 −2.2 dB» 를 **커널로 직접 잰다**.

감사 주장: 외곽(0.6~0.9R) 피치각 폭이 우리 9.2° ↔ DJI 5.5° 라, 폭이 넓으면 반경마다 다른
회전각에서 번쩍여 «플래시가 번지고 봉우리가 −2.2 dB 낮아진다». 감사 스스로 «어림» 이라 적었고,
같은 감사의 커널 민감도(피치 ×1.25)는 +0.15~+0.82 dB 였다 — 두 수가 5 배 어긋난다.

여기서 하는 것
  (1) **통제 가족**: 외곽 비틀림 «기울기» 만 g 배로 바꾼 날을 g=0(비틀림 없음)~1.4 까지 짓는다.
      0.75R 의 피치각은 **고정**한다 → 순수하게 «폭» 만 변한다. 감사의 메커니즘 그 자체다.
  (2) 실제 교체안: legacy 피치 ↔ dji_mini2 피치.
  (3) 감사가 인용한 통제: 피치 ×1.25(= 전 반경 균일 확대. **폭 변화가 아니다**).
  각각에 대해 회전위상 φ 를 0.1° 로 훑어 σ(φ) 를 재고 봉우리·폭·평균을 적는다.

⛔ 저장소 코드는 한 줄도 안 바꾼다. 대안 피치 법칙은 **이 프로세스 안에서만** PITCH_LAWS
   dict 에 임시 키로 넣는다(감사도 같은 방식으로 대안 형상을 지었다).
⛔ GPU 미사용 — numpy 만.
"""
import json
import sys
import numpy as np

sys.path[:0] = ["/workspace/sionna/src", "/workspace/sionna/benchmark"]
import drone_cad                                    # noqa: E402
import drones                                       # noqa: E402
from rcs_po import mesh_to_points, C0               # noqa: E402

FC = 3.5e9
LAM = C0 / FC
K = 2 * np.pi / LAM
OUT = "/tmp/claude-0/-workspace/e9e31991-b542-4f3a-b8e2-570320d555ba/scratchpad/flash_raw.json"


def look(az_deg, el_deg):
    az, el = np.radians(az_deg), np.radians(el_deg)
    return np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])


def theta_of(k_rr, k_val, rr, P, R):
    """국소 피치각 θ(r) [rad]"""
    kk = np.interp(rr, k_rr, k_val)
    return np.arctan(kk * P / (2 * np.pi * rr * R))


def k_from_theta(rr, th, P, R):
    return 2 * np.pi * rr * R * np.tan(th) / P


def make_gradient_law(name, g, spec):
    """legacy 비틀림을 0.75R 고정하고 기울기만 g 배 — 순수 «폭» 통제."""
    R = spec.prop_dia_mm / 2000.0
    P = float(spec.prop_pitch_in) * 0.0254
    rr = np.linspace(0.05, 1.0, 96)
    th = theta_of(drone_cad.PITCH_RR, drone_cad.PITCH_K, rr, P, R)
    th75 = np.interp(0.75, rr, th)
    th_g = th75 + g * (th - th75)
    th_g = np.clip(th_g, np.radians(0.5), np.radians(80.0))
    drone_cad.PITCH_LAWS[name] = dict(rr=tuple(rr), k=tuple(k_from_theta(rr, th_g, P, R)),
                                      source=f"scratch control g={g}")
    return name


def make_scaled_law(name, mul, spec):
    drone_cad.PITCH_LAWS[name] = dict(rr=drone_cad.PITCH_RR,
                                      k=tuple(np.array(drone_cad.PITCH_K) * mul),
                                      source=f"scratch control pitch x{mul}")
    return name


def twist_spread(law, spec):
    """0.6~0.9R 피치각 폭[deg] — 감사가 쓴 잣대"""
    R = spec.prop_dia_mm / 2000.0
    P = float(spec.prop_pitch_in) * 0.0254
    pw = drone_cad.PITCH_LAWS[law]
    rr = np.array([0.6, 0.7, 0.8, 0.9])
    th = np.degrees(theta_of(pw["rr"], pw["k"], rr, P, R))
    return float(th[0] - th[-1]), [round(x, 2) for x in th]


def sigma_phi(spec, pitch_law, el_deg, beta_deg=0.0, n_phi=1800, blade_div=11.0):
    """단일 프로펠러의 σ(φ) — 위상 0.1° 격자(2날 주기 180°)."""
    #  ⚠ 재질은 안 건다(PEC). 프로펠러는 재질 그룹이 'prop' 하나뿐이라 |Γ| 는 **상수 배수**이고
    #    이 실험이 보는 것은 전부 dB **차이**라 정확히 상쇄된다. (게다가 materials 는 Sionna RT
    #    씬을 열어 OptiX 를 요구한다 — 이 라운드는 GPU 금지다.)
    m = drones.build_propeller(spec, n=26, pitch_law=pitch_law)
    P, N, dA = mesh_to_points(m, LAM / blade_div)
    amp = dA
    u_t = look(0.0, el_deg)
    u_s = look(beta_deg, el_deg)
    phis = np.linspace(0.0, 360.0 / spec.prop_blades, n_phi, endpoint=False)
    E = np.empty(n_phi, complex)
    for a in range(0, n_phi, 200):
        b = min(a + 200, n_phi)
        th = np.radians(phis[a:b])
        c, s = np.cos(-th), np.sin(-th)
        Rm = np.zeros((b - a, 3, 3))
        Rm[:, 0, 0] = c; Rm[:, 0, 1] = -s; Rm[:, 1, 0] = s; Rm[:, 1, 1] = c; Rm[:, 2, 2] = 1
        Ut = Rm @ u_t                       # (nb,3)
        Us = Rm @ u_s
        NT = N @ Ut.T                        # (Np, nb)
        NS = N @ Us.T
        PH = np.exp(1j * K * (P @ (Ut + Us).T))
        E[a:b] = (np.where((NT > 0) & (NS > 0), NT, 0.0) * amp[:, None] * PH).sum(0)
    sig = (4 * np.pi / LAM ** 2) * np.abs(E) ** 2
    return phis, sig, len(P), m


def flash_stats(phis, sig):
    pk = float(sig.max())
    dphi = float(phis[1] - phis[0])
    w3 = float((sig >= pk / 2).sum() * dphi)
    w10 = float((sig >= pk / 10).sum() * dphi)
    return dict(peak_dbsm=10 * np.log10(pk), mean_dbsm=10 * np.log10(sig.mean()),
                median_dbsm=10 * np.log10(np.median(sig)),
                w3db_deg=w3, w10db_deg=w10,
                peak_over_mean_db=10 * np.log10(pk / sig.mean()))


def main():
    key = sys.argv[1] if len(sys.argv) > 1 else "matrice4e"
    el = float(sys.argv[2]) if len(sys.argv) > 2 else -30.0
    spec = drones.DRONES[key]
    laws = ["legacy", "dji_mini2"]
    for g in (0.0, 0.3, 0.6, 1.0, 1.4):
        laws.append(make_gradient_law(f"g{g}", g, spec))
    laws.append(make_scaled_law("x1.25", 1.25, spec))
    res = dict(meta=dict(drone=key, el_deg=el, fc=FC, lam=LAM,
                         n_phi=1800, blade_div=11.0, note="단일 프로펠러, 평면파, PO"),
               rows=[])
    for law in laws:
        sp, ths = twist_spread(law, spec)
        row = dict(law=law, twist_spread_0p6_0p9_deg=round(sp, 2), theta_deg=ths)
        for tag, beta in (("mono", 0.0), ("bi81", 81.0), ("bi120", 120.0)):
            phis, sig, npts, m = sigma_phi(spec, law, el, beta)
            row[tag] = flash_stats(phis, sig)
            row["n_pts"] = npts
            row["n_faces"] = len(m.f)
        res["rows"].append(row)
        print(f"{law:10s} Δθ={sp:5.2f}°  θ={ths}  "
              f"mono peak {row['mono']['peak_dbsm']:7.2f} w3 {row['mono']['w3db_deg']:5.2f}° "
              f"mean {row['mono']['mean_dbsm']:7.2f} | bi81 peak {row['bi81']['peak_dbsm']:7.2f} "
              f"mean {row['bi81']['mean_dbsm']:7.2f}", flush=True)
    json.dump(res, open(OUT.replace(".json", f"_{key}_el{int(el)}.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
