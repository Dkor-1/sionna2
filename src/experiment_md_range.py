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

#  ⭐⭐ 2026-08-10 규약 v2 (`docs/NOISE_AND_ROTOR_PLAN.md` §1-2, `outputs/snr_convention.json`)
#     잡음 주입 눈금이 **어느 층**인가. 이 파일의 PRF 20 kHz 슬로타임 표본은 «PRI 하나(50 µs)
#     분량의 100 MHz 신호를 기준신호와 상관» 한 정합필터 출력이므로 G_mf = 10log10(B/PRF)
#     = 36.99 dB 가 붙는다. 2026-07-28 원장은 이것이 빠져 **37 dB 비관적**이었다.
#     "pre_mf" 로 두면 옛 원장과 같은 눈금으로 되돌아간다(비교·재현용).
CAPTURE = "full_waveform"                               # or "pre_mf" / "always_on_pilot"

# 상시 기준신호 반복률(저장소 waveforms.PILOT_RATE_HZ 규약) — PRF 실현가능성 판정용
MODE_PRF_HZ = {"WiFi VHT-LTF": 1000.0, "LTE CRS": 1000.0, "5G SSB": 50.0, "5G NR-PRS": 200.0}


ASPECT_AZ_DEG = list(range(0, 360, 10))     # 자세평균용 방위 격자(36점)
ASPECT_N_PHASE = 120                        # σ 평균만 필요하므로 성글게


#  ⭐ 잡음 시드 — 프로세스에 무관하게 재현된다(`nf.stable_seed`, blake2b).
#  ⚠ 2026-08-10 발견: 예전에는 `abs(hash((drone, band)))` 였는데 파이썬 str `hash()` 는
#    실행마다 salt 가 달라진다(PYTHONHASHSEED). 즉 2026-07-28 원장의 잡음 실현은
#    **재현 불가능**했고 시드가 원장 어디에도 없었다. 이제 (drone, band, R, arm) 마다
#    결정론적 시드를 만들고 **그 값을 원장에 적는다**.
SEED_BASE = 20260811


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
    """(drone, band_name, fc[, capture[, ranges[, seed_base]]]) 한 칸: 전 거리 × 4팔 계산."""
    drone, band, fc = args[:3]
    capture = args[3] if len(args) > 3 else CAPTURE
    ranges = list(args[4]) if len(args) > 4 and args[4] else list(RANGES_M)
    seed_base = int(args[5]) if len(args) > 5 else SEED_BASE
    n_noise = int(args[6]) if len(args) > 6 else N_NOISE
    spec = DRONES[drone]
    lam = nf.C0 / fc
    r_ff = nf.farfield_range_m(target_extent(drone), fc)

    # A0 기준: 평면파·무잡음 (거리 무관 — 한 번만 계산)
    _, E0, i0 = nf.microdoppler_nf(spec, fc, 1000.0, AZ_DEG, EL_DEG, wavefront="plane",
                                   prf=PRF, n_t=N_T, n_phase=N_PHASE)
    m0 = nf.md_metrics(E0, PRF, flash_hz=i0["flash_hz"], f_tip=i0["f_tip"])
    sigma0 = i0["sigma_eq_mean_m2"]

    #  ⭐ 평면파 방위평균 σ 는 **거리에 무관**하다(`_field_plane` 은 R 을 아예 안 쓴다 —
    #    방향 û 와 위상만 쓴다). 예전 판은 거리마다 36 방위를 다시 돌려 계산의 40 % 를
    #    같은 수를 다시 내는 데 썼다. 한 번만 계산해 재사용한다 — **값은 비트동일**이고
    #    게이트 NI7 이 그것을 확인한다.
    s_am_pln = _sigma_eq_aspect_mean(spec, fc, float(ranges[0]), "plane")

    rows = []
    for R in ranges:
        # --- A2/A3 의 결정론 신호: 구면파 ---
        _, Es, isp = nf.microdoppler_nf(spec, fc, R, AZ_DEG, EL_DEG, wavefront="spherical",
                                        prf=PRF, n_t=N_T, n_phase=N_PHASE)
        sigma_s = isp["sigma_eq_mean_m2"]

        # ⭐ 인용 가능한 레벨 편차 + 잡음 스케일: 방위평균 (단일 자세는 널 때문에 비단조)
        s_am_sph = _sigma_eq_aspect_mean(spec, fc, R, "spherical")

        # --- 거리별 SNR ---
        # ⚠ 2026-07-28 적대검증 정정: 예전에는 A1 이 sigma0(평면), A3 이 sigma_s(구면, **단일자세**)
        #   로 서로 다른 잡음전력을 받았다. 그러면 snr_A3 − snr_A1 = d_sigma_db 인데, 이 값은
        #   이 파일 자신의 docstring 이 **비인용**이라고 선언한 단일자세 널 민감량이고 ±9.6 dB 나
        #   흔들린다 → A1 vs A3 의 귀속이 깨진다. 이제 **방위평균 σ** 로 두 팔의 잡음을 정한다
        #   (차이가 단조·소폭이라 A/B 가 성립한다).
        #
        # ⚠⚠ 2026-08-10 적대검증 정정 ②: 아래 두 값은 사다리 ① `snr_band_db` —
        #   **정합필터 전**, 대역 B=100 MHz 에 대한 수신 표본당 SNR 이다. 예전에는 이것을
        #   슬로타임 표본 E[m] 의 SNR 로 그대로 썼는데, E[m] 은 PRI 하나를 기준신호와 상관한
        #   **정합필터 출력**이라 G_mf = 10log10(B/PRF) = 37 dB 가 빠져 있었다.
        #   → 잡음 주입은 이제 사다리 ③ `snr_slow_db` 로 한다(`CAPTURE` 가 정한다).
        #     옛 값은 `snr_sample_*_db` 로 그대로 남긴다(연속성·추적성).
        snr_plane_db = float(nf.echo_over_noise_db(s_am_pln, R, fc))       # ① (옛 반환값)
        snr_sph_db = float(nf.echo_over_noise_db(s_am_sph, R, fc))         # ①

        # ⭐ 규약 v2 사다리 — 두 눈금(③ 총전력 · ③′ AC)을 **항상 병기**한다.
        #   dc_ac 는 각 팔의 결정론 신호에서 잰다(평면=E0, 구면=Es).
        m2 = nf.md_metrics(Es, PRF, flash_hz=isp["flash_hz"], f_tip=isp["f_tip"])
        lad_p = nf.snr_ladder(s_am_pln, R, fc, prf=PRF, capture=capture,
                              dc_ac_db=m0["dc_ac_db"], nperseg=N_T, window="hann")
        lad_s = nf.snr_ladder(s_am_sph, R, fc, prf=PRF, capture=capture,
                              dc_ac_db=m2["dc_ac_db"], nperseg=N_T, window="hann")

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
            # --- 옛 키(2026-07-28 원장과 같은 식·같은 층) — 연속성 때문에 남긴다 ---
            snr_sample_plane_db=snr_plane_db, snr_sample_sph_db=snr_sph_db,
            snr_ac_plane_db=float(nf.ac_snr_db(E0, snr_plane_db)),
            snr_ac_sph_db=float(nf.ac_snr_db(Es, snr_sph_db)),
            # --- ⭐ 규약 v2 사다리 (인용은 이쪽으로) ---
            snr_convention=nf.SNR_CONVENTION, capture=str(capture),
            g_mf_db=float(lad_p["g_mf_db"]),
            snr_band_plane_db=float(lad_p["snr_band_db"]),      # ① = snr_sample_plane_db
            snr_band_sph_db=float(lad_s["snr_band_db"]),
            snr_slow_plane_db=float(lad_p["snr_slow_db"]),      # ③ 총전력 (잡음 주입 눈금)
            snr_slow_sph_db=float(lad_s["snr_slow_db"]),
            snr_slow_ac_plane_db=float(lad_p["snr_slow_ac_db"]),   # ③′ ⭐정본(블레이드선)
            snr_slow_ac_sph_db=float(lad_s["snr_slow_ac_db"]),
            dc_ac_off_plane_db=float(lad_p["dc_ac_off_db"]),
            dc_ac_off_sph_db=float(lad_s["dc_ac_off_db"]),
            snr_map_ac_plane_db=float(lad_p["snr_map_ac_db"]),     # ⑤ 전창 FFT 뒤 첨두
            snr_map_ac_sph_db=float(lad_s["snr_map_ac_db"]),
            snr_ladder_plane=lad_p, snr_ladder_sph=lad_s,
            # --- ⭐ 세 층위를 **한 행에 함께** (키 이름에 층위가 박혀 있다) ---
            #   snr_sample_*_db = ① 정합필터 **전**, 수신 표본당 (위의 옛 키와 같은 수·같은 뜻)
            gain_mf_db=float(lad_p["g_mf_db"]),                     # ②
            gain_stft_db=float(lad_p["g_stft_db"]),                 # ④
            gain_stft_nperseg=int(lad_p["nperseg"]),
            gain_stft_window=str(lad_p["window"]),
            layer_note=("three layers, never one number: snr_sample_*_db (per Rx sample, BEFORE the "
                        "matched filter) + gain_mf_db (one PRI correlation) = snr_slow_*_db "
                        "(the slow-time sample the noise is injected into); "
                        "snr_slow_ac_*_db + gain_stft_db = snr_map_ac_*_db (peak on the map). "
                        "gain_stft_db here uses nperseg = n_t (md_metrics takes ONE full-record "
                        "Hann FFT); the flash_spec map frame is 70 samples = +16.69 dB."),
            snr_note=("snr_sample_*/snr_ac_* are the PRE-matched-filter rung (P_echo/(kT0F*B), B=100 MHz) "
                      "kept for continuity with the 2026-07-28 ledger - SUPERSEDED. Cite the ladder: "
                      "snr_band_* (1) -> snr_slow_* (3, total power, what is injected) -> "
                      "snr_slow_ac_* (3', AC/blade line, canonical for detectability). "
                      "snr_slow = snr_band + g_mf_db, g_mf = 10log10(B/PRF) and applies only to "
                      "full-waveform capture. snr_slow_ac = snr_slow - dc_ac_off_db, "
                      "dc_ac_off = 10log10(1+10^(dc_ac/10))."),
            arms={},
        )

        # A0 (거리 무관, 참조용으로 매 행에 기록)
        entry["arms"]["A0_reference"] = dict(
            ac_corr_vs_ref=1.0, spec_corr_vs_ref=1.0, **{k: float(v) for k, v in m0.items()})

        # A2: 구면파 · 무잡음  (m2 는 사다리에서 이미 계산했다 — 재계산 금지)
        entry["arms"]["A2_nearfield"] = dict(
            ac_corr_vs_ref=nf.ac_correlation(E0, Es),
            spec_corr_vs_ref=nf.spectrogram_corr(E0, Es, PRF),
            **{k: float(v) for k, v in m2.items()})

        # A1 / A3: 잡음 N_NOISE 실현
        # ⭐ 주입 눈금은 사다리 ③ `snr_slow_db` = **총전력**(add_noise 기본 ref="total") 이다.
        #   CAPTURE="full_waveform" 이면 여기 G_mf 37 dB 가 들어 있다 — 옛 원장 대비 그만큼
        #   잡음이 약해진다(= 옛 원장이 37 dB 비관적이었다).
        for arm, Ebase, snr_db, lad in (("A1_snr_only", E0, lad_p["snr_slow_db"], lad_p),
                                        ("A3_both", Es, lad_s["snr_slow_db"], lad_s)):
            #  ⭐ 잡음은 **입구 하나**(`nf.noisy_series`)로만 들어온다. 시드는 (드론·밴드·거리·팔)
            #    에서 결정론적으로 만들고 **원장에 적는다** — 같은 시드면 이 행이 재현된다.
            seed = nf.stable_seed(drone, band, f"{R:g}", arm, base=seed_base)
            Enoisy, prov = nf.noisy_series(Ebase, snr_db, seed, ref="total",
                                           n_real=n_noise, capture=str(capture))
            acc = {}
            for En in Enoisy:
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
            # ⭐ 주입 SNR 을 **두 눈금으로 병기**한다 — 어느 쪽인지 안 적힌 수는 인용 금지 규약.
            #  ⚠ 옛 키 `arms[].snr_sample_db` 는 **폐기**했다. 행 수준의 `snr_sample_*_db` 는
            #    사다리 ①(정합필터 전)인데 여기서는 같은 이름이 ③(슬로타임)을 뜻해서
            #    한 원장 안에 같은 이름 두 뜻이 있었다. 값이 같은 `snr_injected_db` 만 남긴다.
            entry["arms"][arm]["snr_injected_db"] = float(snr_db)
            entry["arms"][arm]["snr_injected_ref"] = "total"
            entry["arms"][arm]["snr_injected_layer"] = "slow_time_post_matched_filter"
            entry["arms"][arm]["snr_injected_ac_db"] = float(lad["snr_slow_ac_db"])
            entry["arms"][arm]["snr_pre_mf_db"] = float(lad["snr_band_db"])
            entry["arms"][arm]["g_mf_db"] = float(lad["g_mf_db"])
            entry["arms"][arm]["dc_ac_off_db"] = float(lad["dc_ac_off_db"])
            entry["arms"][arm]["gain_mf_db"] = float(lad["g_mf_db"])
            entry["arms"][arm]["n_noise"] = int(n_noise)
            #  ⭐ 재현 정보 — 이 행의 잡음을 그대로 다시 만들 수 있는 최소 집합
            entry["arms"][arm]["noise_seed"] = int(seed)
            entry["arms"][arm]["noise_prov"] = {k: prov[k] for k in
                                                ("seed", "snr_reference", "snr_rung", "sigma_n",
                                                 "p_signal_w", "p_noise_w", "layer", "noise",
                                                 "reproducible")}
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
    ap.add_argument("--capture", default=CAPTURE,
                    choices=["full_waveform", "pre_mf", "always_on_pilot"],
                    help="잡음 주입 눈금의 층. full_waveform 이면 G_mf=10log10(B/PRF) 를 붙인다 "
                         "(기본). pre_mf 는 2026-07-28 원장과 같은 층(37 dB 비관적).")
    ap.add_argument("--ranges", default="",
                    help="거리 격자 [m], 쉼표. 비우면 규약 기본값. 정합필터 이득을 넣으면 "
                         "블레이드선이 묻히는 자리가 수십 m 로 밀리므로 그 구간을 촘촘히 볼 때 쓴다.")
    ap.add_argument("--seed", type=int, default=SEED_BASE,
                    help="잡음 시드의 base. 실제 시드는 (drone,band,R,arm) 마다 결정론적으로 "
                         "유도되고 원장에 적힌다.")
    ap.add_argument("--n-noise", dest="n_noise", type=int, default=N_NOISE,
                    help="잡음 실현 수. 관측성 비율(fd_edge 유효 실현 몫)의 분해능을 정한다 — "
                         "8 이면 1/8=12.5 %% 단위라 R90 을 못 잰다.")
    a = ap.parse_args()

    ranges = ([float(x) for x in a.ranges.split(",") if x.strip()] if a.ranges
              else list(RANGES_M))
    drones = [d.strip() for d in a.drones.split(",") if d.strip()]
    # 전 드론 × 헤드라인 밴드 + (mavic4pro·s1000plus) × 전 밴드
    cells = [(d, HEADLINE_BAND, BANDS[HEADLINE_BAND], a.capture, ranges, a.seed, a.n_noise)
             for d in drones]
    if not a.quick:
        for d in ("mavic4pro", "s1000plus"):
            if d in drones:
                for b, f in BANDS.items():
                    if b != HEADLINE_BAND:
                        cells.append((d, b, f, a.capture, ranges, a.seed, a.n_noise))

    t0 = time.time()
    print(f"cells={len(cells)}  ranges={len(ranges)}  arms={len(ARMS)}  "
          f"n_phase={N_PHASE}  n_noise={a.n_noise}  workers={a.workers}")
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
            slow_time=dict(prf_hz=PRF, n_t=N_T, n_phase=N_PHASE, capture=a.capture,
                           capture_condition="full-waveform capture (same convention as report01 micro-Doppler); "
                                             "always-on reference signals cannot reach this PRF - see prf_feasibility"),
            #  ⭐⭐ SNR 규약 v2 — 어느 눈금·어느 층인지 원장 자신이 말한다
            snr=dict(
                convention=nf.SNR_CONVENTION, canonical=nf.CANONICAL_SNR_KEY,
                capture=a.capture, injected_reference="total",
                g_mf_db=round(float(nf.matched_filter_gain_db(nf.DECLARED_B_HZ, PRF,
                                                              capture=a.capture)), 4),
                ladder="snr_band_db (1, pre-MF, per Rx sample over B) -> +g_mf_db (2, 10log10(B/PRF), "
                       "full-waveform capture only) = snr_slow_db (3, slow-time sample, TOTAL power) "
                       "-> -dc_ac_off_db = snr_slow_ac_db (3', AC/blade line, CANONICAL) "
                       "-> +g_stft_db (4) = snr_map_ac_db (5)",
                g_stft_note=f"here rung (4) uses nperseg = n_t = {N_T} because md_metrics takes a "
                            "single full-record Hann FFT, i.e. the 'frame' IS the whole CPI. "
                            "This is NOT the flash_spec map frame (70 samples, +16.69 dB).",
                superseded_keys="snr_sample_*_db and snr_ac_*_db are rung (1) and rung (1)-dc_ac; "
                                "kept only for continuity with the 2026-07-28 ledger",
                fix_2026_08_10="the 2026-07-28 ledger injected rung (1) as if it were rung (3): the "
                               "matched-filter gain 10log10(B/PRF) = 36.99 dB was missing, so that "
                               "ledger is 37 dB pessimistic in range",
                doc="docs/NOISE_AND_ROTOR_PLAN.md#1-2 / outputs/snr_convention.json",
                gate="benchmark/verify_matched_filter_gain.py, benchmark/verify_snr_convention.py"),
            point_spacing=dict(frame_requested="lambda/6", blade_requested="lambda/11",
                               note=("REQUESTED, not realised: rcs_po.mesh_to_points floors at one point "
                                     "per CAD triangle, and the propeller facets are already ~2.9 mm, so the "
                                     "actual nearest-neighbour spacing is ~lambda/127 and the knob is inert "
                                     "over lambda/6..lambda/24. Realised spacing is recorded per cell as "
                                     "blade_spacing_actual_median_m."),),
            link_budget=dict(eirp_dbm=nf.DECLARED_EIRP_DBM, rx_gain_dbi=nf.DECLARED_RX_GAIN_DBI,
                             noise_figure_db=nf.DECLARED_NF_DB, noise_bw_hz=nf.DECLARED_B_HZ,
                             #  ⭐ 정합필터 뒤 실효 잡음대역: kT0F*B / (B/PRF) = kT0F*PRF
                             noise_bw_effective_hz=(PRF if a.capture == "full_waveform"
                                                    else nf.DECLARED_B_HZ),
                             provenance="DECLARED (chamber-class low power); no source document"),
            #  ⭐ 잡음 재현 — 시드 규약을 원장이 스스로 말한다
            noise=dict(
                entry_point="src/microdoppler_nearfield.py::noisy_series (the only injection path)",
                model="circular complex white Gaussian added to the SLOW-TIME series, then STFT "
                      "(never added to the map: that would give a Gaussian instead of an "
                      "exponential/chi2_2 map floor and would drop the signal x noise cross term)",
                reference="total", n_real=a.n_noise,
                seed_base=a.seed,
                seed_rule="nf.stable_seed(drone, band, f'{R:g}', arm, base=seed_base) - blake2b, "
                          "process independent; each arm records its own noise_seed",
                fix_2026_08_11="the 2026-07-28 ledger seeded with abs(hash((drone,band))), and "
                               "python's str hash is salted per process (PYTHONHASHSEED): those "
                               "noise realisations were NOT reproducible and no seed was recorded",
                thermal_only="no clutter, no direct-path residue, no ECA notch, no phase noise, "
                             "no quantisation - the micro-Doppler map arm is thermal noise only"),
            ranges_m=ranges, ranges_default_m=RANGES_M, bands=BANDS, n_noise=a.n_noise,
            n_noise_default=N_NOISE,
            three_layers=dict(
                snr_sample_db="rung 1: per Rx sample, BEFORE the matched filter, over B",
                gain_mf_db="rung 2: 10log10(B/PRF), one PRI correlation, full-waveform only",
                gain_stft_db="rung 4: 10log10(nperseg)+window loss, ONE STFT frame",
                warning=(
                    f"three ~37 dB quantities exist and are different: gain_mf "
                    f"(10log10(B/PRF)); whole-CPI coherent integration over this run's "
                    f"n_t = {N_T} slow-time samples ({10 * np.log10(N_T):.2f} dB, "
                    f"{10 * np.log10(N_T) - 1.76:.2f} dB with a Hann window); and the "
                    f"flash_spec map frame (70 samples, 16.69 dB). "
                    f"Never write one number called 'SNR'. "
                    f"⛔The old literal '5000 samples / 36.99 / 35.23 dB' was stale and, "
                    f"worse, 10log10(5000) = 36.99 equalled gain_mf - so the warning printed "
                    f"the same number twice while saying the three differ.")),
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
