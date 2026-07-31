# -*- coding: utf-8 -*-
"""plan_measurement.py — **실측 캠페인 설계 수치**를 계산해 JSON 으로 굳힌다 (report06 의 근거)

무엇을 계산하나
---------------
1. **원거리장 거리** `R_ff = 2 D² / λ` — 기체(matrice4e · mini5pro)와 교정 기준체(구)에 대해
   세 밴드 전부. D 는 **회전 중인 프로펠러 디스크까지 포함한** 외접 상자의 대각선이다.
   (정지 기체 치수만 쓰면 D 를 과소평가한다 — 로터가 전기적 산란체다.)
2. **주파수 기울기 판별폭** — 우리 σ(f) 회귀 기울기 a[dB/GHz] 와 측정 문헌 앵커의 차이가
   LTE↔WiFi 밴드 구간에서 몇 dB 로 벌어지는가. 이 값이 **캠페인의 세션간 재현성 요구치**다.
3. **ADC 여유** — X410 12-bit 동적범위(74 dB) 에서 직접파 대 잡음비(DNR)를 뺀 값.
   0 dB 아래로 내려가면 양자화 바닥이 열잡음 위로 올라와 **직접파 제거가 ADC 로 막힌다**.
4. **자세 샘플링** — 원형 비행 반경·속도·CPI 가 주어졌을 때 CPI 하나 동안 번지는 방위각.

입력은 전부 이미 있는 `outputs/*.json` 이고, GPU 도 씬 빌드도 쓰지 않는다(1초 미만).

    PYTHONPATH=src:benchmark python benchmark/plan_measurement.py
    → outputs/report06_measurement.json
"""
from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (os.path.join(ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from experiment_x410 import X410, X410Scenario, aoa_resolution_deg  # noqa: E402

C0 = 299792458.0

#: 실측 대상 기체 2종 — 사용자 구매 확정(2026-07-30)
AIRFRAMES = ("matrice4e", "mini5pro")

#: 교정 기준체 — 문헌이 쓰는 두 금속구. 반지름 [m] → 라벨
CALIB_SPHERES = {"0.178": "sphere r=17.8 cm (mono3d)",
                 "0.25": "sphere r=25 cm (unified-rcs)"}

#: 자세 샘플링 설계값 — **선언값**이다(측정 계획의 입력이지 산출이 아니다)
ASPECT = dict(orbit_radius_m=100.0, speed_ms=5.0, t_cpi_s=0.1)


def _load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return json.load(f)


def _diag(v):
    return math.sqrt(sum(x * x for x in v))


def main():
    r1 = _load("outputs/report1.json")
    anc = _load("outputs/rcs_anchor.json")
    cfar = _load("outputs/verify_cfar.json")

    bands = anc["meta"]["bands"]                      # {"LTE 1.843 GHz": 1.843e9, ...}
    hw = X410()
    scn = X410Scenario()

    out = {
        "meta": {
            "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "producer": "benchmark/plan_measurement.py",
            "airframes_purchased": list(AIRFRAMES),
            "farfield_criterion": "R_ff = 2*D^2/lambda, D = diagonal of the "
                                  "bounding box INCLUDING the spinning rotor discs",
            "inputs": ["outputs/report1.json", "outputs/rcs_anchor.json",
                       "outputs/verify_cfar.json"],
            "declared": "aspect_sampling inputs (orbit radius, speed, T_CPI) are "
                        "DECLARED design values, not measured",
        },
        "bands": {b: {"fc_hz": f, "lam_m": C0 / f} for b, f in bands.items()},
    }

    # ── 1. 하드웨어 ────────────────────────────────────────────────────────────
    out["hw"] = dict(
        model="USRP X410 (+ 2x ZBX)",
        n_tx=hw.n_tx, n_rx=hw.n_rx,
        max_bw_hz=hw.max_bw_hz, max_bw_mhz=hw.max_bw_hz / 1e6,
        f_lo_hz=hw.f_lo_hz, f_hi_hz=hw.f_hi_hz,
        adc_bits=hw.adc_bits,
        dynamic_range_db=hw.dynamic_range_db,
        max_sample_rate_hz=hw.max_sample_rate_hz,
        n_reference_ch=1, n_surveillance_ch=scn.n_surv,
        aoa_beamwidth_deg=aoa_resolution_deg(scn),
        ula_spacing_m_at_3p5ghz=scn.elem_spacing_m,
        range_res_bistatic_m_at_max_bw=C0 / hw.max_bw_hz,
        source="src/experiment_x410.py:61 (ni.com / ettus.com 2024 spec)",
    )
    # 세 밴드가 하드웨어 범위 안인지 — 계획서가 스스로 검사한다
    out["hw"]["band_supported"] = {
        b: hw.supports(f, 100e6)[0] for b, f in bands.items()}

    # ── 2. 원거리장 ────────────────────────────────────────────────────────────
    ff = {}
    for key in AIRFRAMES:
        m = r1["meshes"]["drones"][key]
        lwh = [v / 1000.0 for v in m["lwh_full_mm"]]          # 기체 외접(정지)
        disc = [v / 1000.0 for v in m["prop_disc_lw_mm"]]     # 로터 디스크 지름
        env = [max(lwh[0], disc[0]), max(lwh[1], disc[1]), lwh[2]]
        D = _diag(env)
        ff[key] = dict(
            name=m["name"], lwh_full_m=lwh, prop_disc_lw_m=disc,
            envelope_m=env, D_m=D, D_max_extent_m=max(env),
            kind="airframe",
            bands={b: dict(lam_m=C0 / f,
                           R_ff_m=2.0 * D * D / (C0 / f),
                           R_reactive_m=0.62 * math.sqrt(D ** 3 / (C0 / f)),
                           kD=2 * math.pi * D / (C0 / f))
                   for b, f in bands.items()})
    for rs, label in CALIB_SPHERES.items():
        r = float(rs)
        D = 2.0 * r
        ff[f"sphere_r{rs}"] = dict(
            name=label, envelope_m=[D, D, D], D_m=D, D_max_extent_m=D,
            kind="calibration",
            bands={b: dict(lam_m=C0 / f,
                           R_ff_m=2.0 * D * D / (C0 / f),
                           R_reactive_m=0.62 * math.sqrt(D ** 3 / (C0 / f)),
                           kD=2 * math.pi * D / (C0 / f))
                   for b, f in bands.items()})
        # 기준체의 절대 σ 는 정확 Mie 로 이미 굳어 있다 — 그걸 그대로 가져온다
        for b in bands:
            sp = [s for s in anc["sphere_calibration"][b]["spheres"]
                  if abs(s["radius_m"] - r) < 1e-9]
            if sp:
                ff[f"sphere_r{rs}"]["bands"][b]["mie_dbsm"] = sp[0]["mie_dbsm"]
    out["farfield"] = ff
    out["farfield_max_m"] = max(v["bands"][b]["R_ff_m"]
                                for v in ff.values() for b in bands)

    # ── 3. 기울기 판별폭 ───────────────────────────────────────────────────────
    lit = anc["literature"]["mu_eps"]["multiband_phantom3"]
    f_lo = min(v["fc_hz"] for v in out["bands"].values()) / 1e9
    f_hi = max(v["fc_hz"] for v in out["bands"].values()) / 1e9
    span = f_hi - f_lo
    slope = dict(band_span_ghz=span, f_lo_ghz=f_lo, f_hi_ghz=f_hi,
                 lit_slope_db_per_ghz=lit["mu_a"],
                 lit_source="Das, IEEE WCL 15:3731 (2026) — DJI Phantom 3, measured",
                 note="required session-to-session amplitude repeatability must be "
                      "BETTER than gap_db, otherwise the slope claim is undecidable")
    per = {}
    for k, v in anc["drones"].items():
        a = v["regression"]["el0"]["a"]
        per[k] = dict(slope_db_per_ghz=a,
                      gap_db=(a - lit["mu_a"]) * span,
                      ratio_over_lit=a / lit["mu_a"],
                      R2=v["regression"]["el0"]["R2_mu"])
    slope["per_airframe"] = per
    slope["gap_db_min"] = min(p["gap_db"] for p in per.values())
    slope["gap_db_max"] = max(p["gap_db"] for p in per.values())
    slope["gap_db_measured_pair"] = {k: per[k]["gap_db"] for k in AIRFRAMES}
    out["slope_discrimination"] = slope

    # ── 4. ADC 여유 ────────────────────────────────────────────────────────────
    adc = dict(dynamic_range_db=hw.dynamic_range_db, bits=hw.adc_bits,
               definition="headroom_db = ADC dynamic range - DNR. "
                          "Below 0 dB the quantisation floor rises above thermal "
                          "noise and direct-path cancellation is ADC-limited.",
               dnr_source="outputs/verify_cfar.json:chain.<wf>.dnr_db (simulated "
                          "geometry, free space)")
    per_wf = {}
    for wf, ch in cfar["chain"].items():
        per_wf[wf] = dict(dnr_db=ch["dnr_db"],
                          headroom_db=hw.dynamic_range_db - ch["dnr_db"],
                          fs_hz=ch["fs_hz"], ref_bw_hz=ch["ref_bw_hz"])
    adc["per_waveform"] = per_wf
    adc["headroom_db_min"] = min(v["headroom_db"] for v in per_wf.values())
    adc["worst_waveform"] = min(per_wf, key=lambda k: per_wf[k]["headroom_db"])
    out["adc"] = adc

    # ── 5. 자세 샘플링 ─────────────────────────────────────────────────────────
    R, v, T = ASPECT["orbit_radius_m"], ASPECT["speed_ms"], ASPECT["t_cpi_s"]
    smear = math.degrees(v * T / R)
    out["aspect_sampling"] = dict(
        **ASPECT,
        az_smear_per_cpi_deg=smear,
        orbit_period_s=2 * math.pi * R / v,
        n_cpi_per_orbit=(2 * math.pi * R / v) / T,
        sim_n_az=anc["meta"]["n_az_band"],
        sim_az_step_deg=360.0 / anc["meta"]["n_az_band"],
        verdict_smear_below_sim_step=bool(smear < 360.0 / anc["meta"]["n_az_band"]),
    )

    p = os.path.join(ROOT, "outputs", "report06_measurement.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    print(f"[plan_measurement] 저장 → {os.path.relpath(p, ROOT)}")
    print(f"  원거리장 최대   : {out['farfield_max_m']:.1f} m "
          f"(모든 기체 × 모든 밴드 중 최대)")
    for k in AIRFRAMES:
        b = "WiFi 5.21 GHz"
        print(f"    {k:10s} D={ff[k]['D_m']:.3f} m → {b} 에서 "
              f"R_ff={ff[k]['bands'][b]['R_ff_m']:.1f} m")
    print(f"  기울기 판별폭   : {slope['gap_db_measured_pair']}")
    print(f"  ADC 여유 최소   : {adc['headroom_db_min']:.1f} dB "
          f"({adc['worst_waveform']})")
    print(f"  CPI 당 방위번짐 : {smear:.3f}° "
          f"(시뮬 격자 {out['aspect_sampling']['sim_az_step_deg']:.3f}°)")
    return out


if __name__ == "__main__":
    main()
