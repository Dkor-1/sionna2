# -*- coding: utf-8 -*-
"""
experiment_md_range.py — 거리 스윕 마이크로도플러 **3-팔 분리 실험**
=====================================================================
질문: **"거리(1/5/10/20 m)에 따라 마이크로 도플러 패턴이 망가지는가?"**

거리는 두 가지 **서로 다른 경로**로 스펙트로그램에 들어온다. 섞어 놓으면 어느 쪽이
원인인지 말할 수 없다. 그래서 팔을 나눈다:

  A0  reference    평면파 · 무잡음                 ← 기준(원거리장 이상)
  A1  snr_only     평면파 · 거리별 잡음            ← **가시성**만 변한다(패턴 모양 불변)
  A2  nearfield    구면파 · 무잡음                 ← **모양**만 변한다(파면 곡률)
  A3  both         구면파 · 거리별 잡음            ← 실제로 보게 될 것

A1 은 정의상 A0 와 **같은 결정론적 신호**를 쓴다(거리는 잡음 크기만 바꾼다).
A2 는 잡음이 없으므로 A0 대비 차이가 **전부 파면 곡률**이다.
→ 두 효과의 귀속이 구조적으로 보장된다. 이것이 이 실험의 설계 근거다.

⚠ 전제·한계 (전부 JSON meta 에 기록)
  * 두 팔 모두 **가림 없는 순수 PO** — 의도적. 가림을 넣으면 A/B 귀속이 깨진다.
    절대 σ 는 report07 기준 +4~5 dB 과대이나 **양 팔에 동일**하게 걸려 상쇄된다.
  * σ_eq 는 "구면파로 계산한 원거리장 등가 σ" 진단량이다. 절대 앵커로 인용 금지.
  * PRF 20 kHz = **풀 웨이브폼 캡처** 조건(report01 마이크로도플러와 동일 규약).
    상시 기준신호(LTE CRS 1 kHz / 5G SSB 50 Hz)로는 f_tip 이 접힌다 —
    `prf_feasibility` 블록에 드론×모드별 판정을 함께 기록한다.
  * 링크버짓 파라미터(EIRP 12 dBm 등)는 **선언값**이다. provenance 로 표기.

실행:
    cd sionna2 && PYTHONPATH=src ~/.venvs/py312/bin/python src/experiment_md_range.py
    (옵션) --drones mavic4pro,s1000plus  --quick
산출: outputs/md_range_sweep.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)

from drones import DRONES, drone_order                      # noqa: E402
from radar_scene import target_extent                       # noqa: E402
import microdoppler_nearfield as nf                         # noqa: E402

OUT = os.path.join(_ROOT, "outputs", "md_range_sweep.json")

# --- 스윕 축 ---------------------------------------------------------------
RANGES_M = [1.0, 2.0, 5.0, 10.0, 20.0, 50.0, 1000.0]   # 1000 = 원거리장 수렴 앵커
BANDS = {"LTE 1.843 GHz": 1.843e9, "5G NR 3.5 GHz": 3.5e9, "WiFi 5.21 GHz": 5.21e9}
HEADLINE_BAND = "5G NR 3.5 GHz"
#  ⭐ 2026-07-30 (Phase 3): 5종 하드코딩이던 자리. `--drones` 기본값이 이 목록이라
#     기종을 추가해도 **에러 없이 스윕에서 빠졌다**. 이제 레지스트리에서 유도한다.
ALL_DRONES = drone_order(("mini5pro", "mavic4pro", "matrice4e", "s1000plus", "phantom4"))
AZ_DEG, EL_DEG = 0.0, 15.0
PRF, N_T, N_PHASE = 20000.0, 6144, 480     # 위상테이블은 **1회전 전체**(근사 없음) — 모듈 docstring 참조
N_NOISE = 8                                             # 잡음 실현 수(평균·표준편차 보고)
ARMS = ("A0_reference", "A1_snr_only", "A2_nearfield", "A3_both")

# 상시 기준신호 반복률(저장소 waveforms.PILOT_RATE_HZ 규약) — PRF 실현가능성 판정용
MODE_PRF_HZ = {"WiFi VHT-LTF": 1000.0, "LTE CRS": 1000.0, "5G SSB": 50.0, "5G NR-PRS": 200.0}


ASPECT_AZ_DEG = list(range(0, 360, 10))     # 자세평균용 방위 격자(36점)
ASPECT_N_PHASE = 120                        # σ 평균만 필요하므로 성글게


def _sigma_eq_aspect_mean(spec, fc, R, wavefront):
    """**방위평균** σ_eq [m²].

    ⚠ 왜 필요한가: 단일 자세(az=0)의 코히런트 σ 는 깊은 널을 타면 ±10 dB 씩 튄다.
    저장소 규약이 단일 자세 σ 를 비인용으로 정한 이유이고, 실제로 s1000plus·matrice4e 의
    Δσ_eq(R) 가 단일 자세에서 **비단조**로 나온다(이산화 아티팩트가 아님 — λ/11↔λ/22 에서
    최대 1.16 dB, AC 상관 0.9995). 방위평균하면 단조 수렴이 복원된다
    (s1000plus: 2 m +3.18 → 20 m +0.81 → 1000 m +0.00 dB).
    → **레벨 편차 인용은 이 값으로 한다.** 시간축 지표(패턴 상관·도플러 폭)는 자세평균과 무관하다.
    """
    lam = nf.C0 / fc
    acc = 0.0
    for az in ASPECT_AZ_DEG:
        _, tab, _ = nf.phase_table(spec, fc, R, float(az), EL_DEG, wavefront=wavefront,
                                   n_phase=ASPECT_N_PHASE)
        acc += float(np.mean(np.abs(tab) ** 2))
    return (4 * np.pi / lam ** 2) * acc / len(ASPECT_AZ_DEG)


def _cell(args):
    """(drone, band_name, fc) 한 칸: 전 거리 × 4팔 계산."""
    drone, band, fc = args
    spec = DRONES[drone]
    lam = nf.C0 / fc
    r_ff = nf.farfield_range_m(target_extent(drone), fc)
    rng = np.random.default_rng(abs(hash((drone, band))) % (2 ** 31))

    # A0 기준: 평면파·무잡음 (거리 무관 — 한 번만 계산)
    _, E0, i0 = nf.microdoppler_nf(spec, fc, 1000.0, AZ_DEG, EL_DEG, wavefront="plane",
                                   prf=PRF, n_t=N_T, n_phase=N_PHASE)
    m0 = nf.md_metrics(E0, PRF, flash_hz=i0["flash_hz"], f_tip=i0["f_tip"])
    sigma0 = i0["sigma_eq_mean_m2"]

    rows = []
    for R in RANGES_M:
        # --- A2/A3 의 결정론 신호: 구면파 ---
        _, Es, isp = nf.microdoppler_nf(spec, fc, R, AZ_DEG, EL_DEG, wavefront="spherical",
                                        prf=PRF, n_t=N_T, n_phase=N_PHASE)
        sigma_s = isp["sigma_eq_mean_m2"]

        # ⭐ 인용 가능한 레벨 편차 + 잡음 스케일: 방위평균 (단일 자세는 널 때문에 비단조)
        s_am_sph = _sigma_eq_aspect_mean(spec, fc, R, "spherical")
        s_am_pln = _sigma_eq_aspect_mean(spec, fc, R, "plane")

        # --- 거리별 SNR ---
        # ⚠ 2026-07-28 적대검증 정정: 예전에는 A1 이 sigma0(평면), A3 이 sigma_s(구면, **단일자세**)
        #   로 서로 다른 잡음전력을 받았다. 그러면 snr_A3 − snr_A1 = d_sigma_db 인데, 이 값은
        #   이 파일 자신의 docstring 이 **비인용**이라고 선언한 단일자세 널 민감량이고 ±9.6 dB 나
        #   흔들린다 → A1 vs A3 의 귀속이 깨진다. 이제 **방위평균 σ** 로 두 팔의 잡음을 정한다
        #   (차이가 단조·소폭이라 A/B 가 성립한다).
        snr_plane_db = float(nf.echo_over_noise_db(s_am_pln, R, fc))
        snr_sph_db = float(nf.echo_over_noise_db(s_am_sph, R, fc))

        entry = dict(
            R_m=float(R), in_farfield=bool(R >= r_ff), R_over_Rff=float(R / r_ff),
            sigma_eq_plane_dbsm=float(10 * np.log10(sigma0)),
            sigma_eq_sph_dbsm=float(10 * np.log10(sigma_s)),
            d_sigma_db=float(10 * np.log10(sigma_s / sigma0)),
            d_sigma_aspect_mean_db=float(10 * np.log10(s_am_sph / s_am_pln)),
            sigma_eq_aspect_mean_sph_dbsm=float(10 * np.log10(s_am_sph)),
            sigma_eq_aspect_mean_plane_dbsm=float(10 * np.log10(s_am_pln)),
            d_sigma_note="d_sigma_db is SINGLE-ASPECT (az=0) and can be non-monotone through nulls; "
                         "cite d_sigma_aspect_mean_db (36 azimuths) instead",
            snr_sample_plane_db=snr_plane_db, snr_sample_sph_db=snr_sph_db,
            # ⭐ 블레이드선(AC) 실효 SNR = 총전력 SNR − DC/AC. 검출성은 **이 값**으로 논한다.
            snr_ac_plane_db=float(nf.ac_snr_db(E0, snr_plane_db)),
            snr_ac_sph_db=float(nf.ac_snr_db(Es, snr_sph_db)),
            snr_note=("snr_sample_* is TOTAL-power referenced and is dominated by the non-rotating body "
                      "(dc_ac 33-43 dB). Use snr_ac_* for blade-line detectability."),
            arms={},
        )

        # A0 (거리 무관, 참조용으로 매 행에 기록)
        entry["arms"]["A0_reference"] = dict(
            ac_corr_vs_ref=1.0, spec_corr_vs_ref=1.0, **{k: float(v) for k, v in m0.items()})

        # A2: 구면파 · 무잡음
        m2 = nf.md_metrics(Es, PRF, flash_hz=isp["flash_hz"], f_tip=isp["f_tip"])
        entry["arms"]["A2_nearfield"] = dict(
            ac_corr_vs_ref=nf.ac_correlation(E0, Es),
            spec_corr_vs_ref=nf.spectrogram_corr(E0, Es, PRF),
            **{k: float(v) for k, v in m2.items()})

        # A1 / A3: 잡음 N_NOISE 실현
        for arm, Ebase, snr_db in (("A1_snr_only", E0, snr_plane_db),
                                   ("A3_both", Es, snr_sph_db)):
            acc = {}
            for _ in range(N_NOISE):
                En, _s = nf.add_noise(Ebase, snr_db, rng)
                mm = nf.md_metrics(En, PRF, flash_hz=isp["flash_hz"], f_tip=isp["f_tip"])
                mm["ac_corr_vs_ref"] = nf.ac_correlation(E0, En)
                mm["spec_corr_vs_ref"] = nf.spectrogram_corr(E0, En, PRF)
                for k, v in mm.items():
                    acc.setdefault(k, []).append(float(v))
            # NaN 은 결측이 아니라 "블레이드선이 잡음에 묻혔다" 는 **결과**다 →
            # nan-aware 평균 + 유효 실현 수를 함께 기록하고, JSON 에는 null 로 쓴다.
            def _fin(v):
                a = np.asarray(v, float)
                m_ = a[np.isfinite(a)]
                return (float(m_.mean()) if len(m_) else None,
                        float(m_.std()) if len(m_) else None, int(len(m_)))
            entry["arms"][arm] = {}
            for k, v in acc.items():
                mu, sd, n_ok = _fin(v)
                entry["arms"][arm][k] = mu
                entry["arms"][arm][k + "_sd"] = sd
                if n_ok < len(v):
                    entry["arms"][arm][k + "_n_valid"] = n_ok      # 일부만 관측됨
            entry["arms"][arm]["snr_sample_db"] = float(snr_db)
            entry["arms"][arm]["n_noise"] = int(N_NOISE)
        rows.append(entry)

    # PRF 실현가능성: 상시 기준신호로 f_tip 을 접히지 않고 볼 수 있는가
    need = 2.0 * float(i0["f_tip"])
    feas = {m: dict(mode_prf_hz=p, required_prf_hz=need, ok=bool(p >= need))
            for m, p in MODE_PRF_HZ.items()}

    return dict(
        drone=drone, band=band, fc_hz=float(fc), lam_m=float(lam),
        extent_m=float(target_extent(drone)), r_ff_m=float(r_ff),
        rpm=float(i0["rpm"]), flash_hz=float(i0["flash_hz"]), f_tip_hz=float(i0["f_tip"]),
        v_tip_ms=float(i0["v_tip"]), n_frame_pts=int(i0["n_frame_pts"]),
        n_blade_pts=int(i0["n_blade_pts"]), n_rotors=int(i0["n_rotors"]),
        prf_feasibility=feas, rows=rows,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drones", default=",".join(ALL_DRONES))
    ap.add_argument("--quick", action="store_true", help="헤드라인 밴드만")
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()

    drones = [d.strip() for d in a.drones.split(",") if d.strip()]
    # 전 드론 × 헤드라인 밴드 + (mavic4pro·s1000plus) × 전 밴드
    cells = [(d, HEADLINE_BAND, BANDS[HEADLINE_BAND]) for d in drones]
    if not a.quick:
        for d in ("mavic4pro", "s1000plus"):
            if d in drones:
                for b, f in BANDS.items():
                    if b != HEADLINE_BAND:
                        cells.append((d, b, f))

    t0 = time.time()
    print(f"cells={len(cells)}  ranges={len(RANGES_M)}  arms={len(ARMS)}  "
          f"n_phase={N_PHASE}  n_noise={N_NOISE}  workers={a.workers}")
    results = []
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        for i, r in enumerate(ex.map(_cell, cells), 1):
            results.append(r)
            print(f"  [{i}/{len(cells)}] {r['drone']:11s} {r['band']:15s} "
                  f"R_ff={r['r_ff_m']:6.2f} m  f_tip={r['f_tip_hz']:7.1f} Hz  "
                  f"({time.time() - t0:6.1f} s)")

    doc = dict(
        meta=dict(
            generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
            question="does the micro-Doppler pattern degrade with range (1/5/10/20 m)?",
            design="3-arm separation: A1 changes SNR only, A2 changes wavefront only, A3 both",
            arms={a_: d for a_, d in zip(ARMS, [
                "plane wave, noiseless (far-field ideal reference)",
                "plane wave + range-dependent noise (visibility only; shape invariant by construction)",
                "spherical wave, noiseless (wavefront curvature only)",
                "spherical wave + range-dependent noise (what you would actually observe)"])},
            engine="pure PO point cloud, NO occlusion (deliberate: occlusion would break A/B attribution)",
            sigma_eq_note="sigma_eq = far-field-EQUIVALENT sigma computed with spherical wavefronts; "
                          "diagnostic only, converges to plane-wave sigma as R->inf. NOT an absolute RCS anchor.",
            geometry=dict(monostatic=True, az_deg=AZ_DEG, el_deg=EL_DEG),
            slow_time=dict(prf_hz=PRF, n_t=N_T, n_phase=N_PHASE,
                           capture_condition="full-waveform capture (same convention as report01 micro-Doppler); "
                                             "always-on reference signals cannot reach this PRF - see prf_feasibility"),
            point_spacing=dict(frame_requested="lambda/6", blade_requested="lambda/11",
                               note=("REQUESTED, not realised: rcs_po.mesh_to_points floors at one point "
                                     "per CAD triangle, and the propeller facets are already ~2.9 mm, so the "
                                     "actual nearest-neighbour spacing is ~lambda/127 and the knob is inert "
                                     "over lambda/6..lambda/24. Realised spacing is recorded per cell as "
                                     "blade_spacing_actual_median_m."),),
            link_budget=dict(eirp_dbm=nf.DECLARED_EIRP_DBM, rx_gain_dbi=nf.DECLARED_RX_GAIN_DBI,
                             noise_figure_db=nf.DECLARED_NF_DB, noise_bw_hz=nf.DECLARED_B_HZ,
                             provenance="DECLARED (chamber-class low power); no source document"),
            ranges_m=RANGES_M, bands=BANDS, n_noise=N_NOISE,
            farfield_rule="R_ff = 2 D^2 / lambda, D = mesh bbox max horizontal extent (radar_scene.target_extent)",
            runtime_s=round(time.time() - t0, 1),
        ),
        cells=results,
    )
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    tmp = a.out + ".tmp"
    with open(tmp, "w") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
    os.replace(tmp, a.out)
    print(f"\n→ {a.out}  ({time.time() - t0:.1f} s)")


if __name__ == "__main__":
    main()
