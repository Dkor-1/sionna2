# -*- coding: utf-8 -*-
"""⭐ 감사 I8 의 «팁 밴드 −3.10 dB 가 f_tip 세기를 정한다» 를 **스펙트럼 축에서 직접 잰다**.

감사는 σ 축에서는 «소액» 이라 적고 스펙트럼 축은 «안 쟀다» 고 선언했다. 그리고 그 미측정
주장을 근거로 `CHORD_FRAC` 끝값 0.10 → 0.20 이 이미 코드에 들어갔다. 여기서 잰다.

무엇을 재나 — 저장소에 **실재하는** 잣대만 쓴다:
  · f_tip 자체 = 2·v_tip·cos(el)/λ  (순수 운동학. 시위와 무관 — 정의상 안 움직인다)
  · fd_edge_hz (microdoppler_nearfield.md_metrics) = 관측된 도플러 가장자리
  · OOB = f_tip 바깥 전력 몫 (report07b 가 쓰는 잣대)
  · 그리고 감사가 말한 «f_tip 근방 세기» 를 가장 우호적으로 해석한 밴드 전력 P(0.85~1.0 f_tip)
비교 형상: legacy / legacy+끝값0.20 / legacy+끝값0.30 / dji_mini2(코드에 들어간 판) /
          dji_mini2+**내 실측 팁 마디**(0.96~1.00R 을 GLB 실측값으로 채운 판)
"""
import json
import sys
import numpy as np

sys.path[:0] = ["/workspace/sionna/src", "/workspace/sionna/benchmark"]
import drone_cad                                     # noqa: E402
import drones                                        # noqa: E402
from rcs_po import mesh_to_points, C0                # noqa: E402
from microdoppler_nearfield import md_metrics        # noqa: E402

OUT = "/tmp/claude-0/-workspace/e9e31991-b542-4f3a-b8e2-570320d555ba/scratchpad/tip_spectrum.json"
FC = 3.5e9
LAM = C0 / FC


def look(az, el):
    az, el = np.radians(az), np.radians(el)
    return np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])


def add_law(name, rr, frac, base="legacy", tip_refine=None, chord_mode=None):
    b = dict(drone_cad.BLADE_LAWS[base])
    b.update(chord_rr=tuple(rr), chord_frac=tuple(frac))
    if tip_refine is not None:
        b["tip_refine"] = tip_refine
    if chord_mode is not None:
        b["chord_max_mode"] = chord_mode
    b["source"] = f"scratch {name}"
    drone_cad.BLADE_LAWS[name] = b
    return name


def build_laws():
    L_rr, L_fr = list(drone_cad.CHORD_RR), list(drone_cad.CHORD_FRAC)
    names = [("legacy", 0.25)]
    for tip in (0.20, 0.30):
        f = list(L_fr); f[-1] = tip
        names.append((add_law(f"legacy_tip{tip:.2f}", L_rr, f), 0.25))
    names.append(("dji_mini2", 0.190))
    names.append(("dji_mini2", 0.25))
    #  내 GLB 실측 팁 마디(정규화 c/c_max, band ±0.25 mm) 를 dji 표에 덧붙인다
    D_rr = list(drone_cad.CHORD_RR_DJI_MINI2)
    D_fr = list(drone_cad.CHORD_FRAC_DJI_MINI2)
    meas = [(0.96, 0.445), (0.97, 0.422), (0.98, 0.402), (0.99, 0.370), (1.00, 0.292)]
    rr2 = D_rr[:-1] + [m[0] for m in meas]
    fr2 = D_fr[:-1] + [m[1] for m in meas]
    names.append((add_law("dji_measured_tip", rr2, fr2, base="dji_mini2", tip_refine=4), 0.190))
    names.append(("dji_measured_tip", 0.25))
    return names


def series(spec, blade_law, el_deg, n_phi=2880, blade_div=11.0, cmax=None):
    #  ⚠ resolve_chord_max_over_r 는 판 **이름**이 'legacy' 인지로 c_max/R 을 고른다.
    #    그래서 이름이 다른 내 통제판은 자동으로 기종별 실측값(matrice4e 0.190)으로 떨어진다.
    #    통제 실험이 오염되므로 spec 필드로 **명시 지정**해 원하는 값을 박는다.
    import dataclasses
    sp = dataclasses.replace(spec, prop_chord_max_over_r=cmax) if cmax else spec
    m = drones.build_propeller(sp, n=26, blade_law=blade_law)
    P, N, dA = mesh_to_points(m, LAM / blade_div)
    k = 2 * np.pi / LAM
    u = look(0.0, el_deg)
    phis = np.linspace(0.0, 360.0 / spec.prop_blades, n_phi, endpoint=False)
    E = np.empty(n_phi, complex)
    for a in range(0, n_phi, 150):
        b = min(a + 150, n_phi)
        th = np.radians(phis[a:b])
        c, s = np.cos(-th), np.sin(-th)
        U = np.stack([c * u[0] - s * u[1], s * u[0] + c * u[1], np.full(b - a, u[2])], 1)
        NU = N @ U.T
        E[a:b] = (np.where(NU > 0, NU, 0.0) * dA[:, None] * np.exp(2j * k * (P @ U.T))).sum(0)
    return phis, E, m


def to_time(phis, Etab, rpm, prf=20000.0, n_t=8192):
    period = float(phis[-1] - phis[0]) + float(phis[1] - phis[0])
    t = np.arange(n_t) / prf
    idx = np.mod((360.0 * rpm / 60.0) * t / period * len(Etab), len(Etab))
    i0 = np.floor(idx).astype(int) % len(Etab)
    i1 = (i0 + 1) % len(Etab)
    f = idx - np.floor(idx)
    return t, Etab[i0] * (1 - f) + Etab[i1] * f


def band_powers(E, prf, f_tip):
    ac = E - E.mean()
    n = len(ac)
    win = np.hanning(n)
    S = np.abs(np.fft.fftshift(np.fft.fft(ac * win))) ** 2
    f = np.fft.fftshift(np.fft.fftfreq(n, 1.0 / prf))
    tot = S.sum()
    def bp(lo, hi):
        m = (np.abs(f) >= lo) & (np.abs(f) < hi)
        return float(S[m].sum())
    return dict(P_total=float(tot),
                P_tipband_085_100=bp(0.85 * f_tip, 1.00 * f_tip),
                P_tipband_090_100=bp(0.90 * f_tip, 1.00 * f_tip),
                P_oob=bp(f_tip, prf / 2),
                P_inband=bp(0.0, f_tip))


def main():
    key = sys.argv[1] if len(sys.argv) > 1 else "matrice4e"
    el = float(sys.argv[2]) if len(sys.argv) > 2 else -30.0
    spec = drones.DRONES[key]
    names = build_laws()
    rpm = float(spec.hover_rpm)
    R = spec.prop_dia_mm / 2000.0
    v_tip = 2 * np.pi * rpm / 60.0 * R
    f_tip = 2 * v_tip / LAM * np.cos(np.radians(el))
    prf = 20000.0
    res = dict(meta=dict(drone=key, el=el, rpm=rpm, f_tip_hz=f_tip, prf=prf,
                         v_tip=v_tip, lam=LAM,
                         note="단일 프로펠러 PO, 평면파. f_tip 은 운동학 정의(시위와 무관)."),
               rows=[])
    base = None
    for nm, cmax in names:
        phis, Etab, m = series(spec, nm, el, cmax=cmax)
        t, E = to_time(phis, Etab, rpm, prf)
        bp = band_powers(E, prf, f_tip)
        md = md_metrics(E, prf, flash_hz=spec.prop_blades * rpm / 60.0, f_tip=f_tip)
        # 형상 잣대: 팁 밴드 «면적» (감사가 dB 로 번역한 그 양)
        row = dict(law=nm, c_max_over_R=cmax, n_faces=len(m.f), sigma_mean_dbsm=float(
            10 * np.log10((4 * np.pi / LAM ** 2) * np.mean(np.abs(Etab) ** 2))), **bp)
        row.update(fd_edge_hz=md["fd_edge_hz"], flash_contrast_db=md["flash_contrast_db"],
                   harmonic_frac=md["harmonic_frac"], dc_ac_db=md["dc_ac_db"])
        if base is None:
            base = row
        for q in ("P_total", "P_tipband_085_100", "P_tipband_090_100", "P_oob"):
            row["d_" + q + "_db"] = float(10 * np.log10(max(row[q], 1e-300) /
                                                        max(base[q], 1e-300)))
        row["law"] = f"{nm}@{cmax:.3f}"
        res["rows"].append(row)
        print(f"{nm:22s} c_max/R {cmax:.3f}  σmean {row['sigma_mean_dbsm']:7.2f}  "
              f"ΔP_tot {row['d_P_total_db']:+6.2f}  "
              f"ΔP_tip(0.90-1.0) {row['d_P_tipband_090_100_db']:+6.2f}  "
              f"ΔP_oob {row['d_P_oob_db']:+6.2f}  "
              f"fd_edge {row['fd_edge_hz']:8.1f} (f_tip {f_tip:.1f})  "
              f"contrast {row['flash_contrast_db']:5.2f}", flush=True)
    json.dump(res, open(OUT.replace(".json", f"_{key}_el{int(el)}.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
