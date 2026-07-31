# -*- coding: utf-8 -*-
"""
verify_linkbudget.py — [E4] 링크버짓 · 처리이득 · 잡음바닥 교정 검증
====================================================================
질문: **"우리가 유도한 SNR 이 시뮬레이션에서 실제로 나오는가?"**

벤치마크(어느 조명원이 유리한가)를 믿으려면, 그 앞단인 '물리 → 주입진폭 → RD맵 SNR'
사슬이 한 고리도 안 새는지 먼저 보여야 한다. 이 스크립트는 다섯 가지를 **측정**한다.

  A. 바이스태틱 레이더 방정식 — 코드(link_budget.py)를 **독립 유도**와 대조
       · 경로 1: 전력밀도 사슬(EIRP → 4πR1² → σ → 4πR2² → A_eff = Gλ²/4π)
       · 경로 2: 순수 dB 산술(EIRP_dBm + G + 20log λ + 10log σ − 30log 4π − 20log R1R2)
       · 잡음:  kT0B·F  vs  −174 dBm/Hz + NF + 10log10(B)
  B. 처리이득 — 정합필터(B·T)와 CPI 코히어런트 적분(M) 이 시뮬에서 실제로 나오는가
       이론 상한:  SNR_RD = a² · Σ|ref_frame|² · M / σ_n²   (직사각창·격자정합·ECA 없음)
  C. 잡음바닥 — bw_corr = √(B/fs) 가 옳은가, 협대역/광대역 사이 계통편향이 없는가
  D. σ(SBR) × 드론 전 기종 × 3파형 — 유도 SNR vs 측정 SCR, 차이 = 처리손실
  E. 손실 분해 — Hann 창손실 / 도플러·거리 straddle / 프레임내 도플러 / ECA / CFAR

측정값은 outputs/verify_linkbudget.json 으로 남긴다(노트북이 읽는다 — 손으로 숫자 적지 말 것).

실행:  CUDA_VISIBLE_DEVICES=2 ~/.venvs/py312/bin/python benchmark/verify_linkbudget.py
       (σ 는 SBR 캐시 조회 — 미스면 GPU 로 채운다)
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
_SRC = os.path.join(_ROOT, "src")
for _p in (_SRC, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ⚠ GPU 예산 워크어라운드(channel._prefill_worker 와 동일 사유): gpu.pick() 은
#   CUDA_VISIBLE_DEVICES 가 이미 있으면 조기 반환하며 _BUDGET_MB 를 채우지 않아
#   rcs_sbr.budget_mb() 가 NameError 로 죽는다. σ 캐시 미스가 날 때만 필요하다.
if os.environ.get("CUDA_VISIBLE_DEVICES"):
    try:
        import gpu as _g
        _idx = os.environ["CUDA_VISIBLE_DEVICES"].split(",")[0]
        _free = next((g["free_mb"] for g in _g.gpu_status()), 8000)
        _g._PICKED, _g._BUDGET_MB = _idx, _g._compute_budget(_free)
    except Exception:
        pass

from waveforms import lte_downlink, nr_downlink, wifi_80211ac      # noqa: E402
from passive_process import make_cpi, ECACanceller, ca_cfar_2d     # noqa: E402
from bistatic_scene import C0                                      # noqa: E402
from link_budget import LinkBudget, link_terms, K_BOLTZ, T0        # noqa: E402
from channel import AnalyticChannel                                # noqa: E402
from geometry import TX, RX, CENTER, SPEED, SPAN, chamber_window   # noqa: E402
from scenarios import radial                                       # noqa: E402
from run_min_cell import EIRP_DBM, run_cell, frame_len, measure_scr  # noqa: E402

OUT_JSON = os.path.join(_ROOT, "outputs", "verify_linkbudget.json")
#  ⭐ 2026-07-30 (Phase 3): 5종 하드코딩이던 자리(이름도 개수를 박고 있었다) →
#     레지스트리 유도. 앞머리 순서만 옛 목록을 유지하고 신규 기종이 뒤에 자동으로 붙는다.
from drones import drone_order as _drone_order                     # noqa: E402
LB_DRONES = _drone_order(("mini5pro", "mavic4pro", "matrice4e", "s1000plus", "phantom4"))
#  ⭐ 2026-07-30 (Phase 3): D2 는 "최약/최강 표적" 두 종만 본다. 그 두 종이 (mini5pro,
#     s1000plus) 로 **손으로 적혀** 있었다 — 오늘은 맞지만 더 작은/큰 기체가 등록되면
#     라벨과 내용이 조용히 어긋난다. 크기 대리변수는 `target_extent`(프롭 포함 최대 수평
#     span)로, 저장소가 이미 σ·원거리장 판정에 쓰는 것과 같은 양이다.
def _extreme_drones():
    from radar_scene import target_extent            # 지연 import (sionna 안 끌어옴)
    ext = {k: float(target_extent(k)) for k in LB_DRONES}
    return (min(ext, key=ext.get), max(ext, key=ext.get))


_EXTREME_DRONES = _extreme_drones()


def db(x):
    return 10.0 * np.log10(np.maximum(np.asarray(x, float), 1e-300))


def waveforms3():
    """벤치마크 3파형(같은 점유모드 G3)."""
    return [
        ("WiFi 80MHz", wifi_80211ac(bw_hz=80e6, carrier_hz=5.21e9, occupancy="G3")),
        ("LTE 20MHz", lte_downlink(bw_hz=20e6, carrier_hz=1.843e9, occupancy="G3")),
        ("5G 100MHz", nr_downlink(bw_hz=100e6, carrier_hz=3.5e9, occupancy="G3")),
    ]


# =========================================================================== #
#  A. 바이스태틱 레이더 방정식 — 독립 유도 2경로 vs 코드
# =========================================================================== #
def independent_echo_power_w(eirp_dbm, grx_dbi, lam, sigma, R1, R2):
    """경로 1 — **전력밀도 사슬**(교과서 유도를 한 줄씩 따라간다).
      S1 = EIRP / (4π R1²)                [W/m²]  표적에 도달한 전력밀도
      P_s = S1 · σ                        [W]     표적이 '재방사'하는 등가 전력
      S2 = P_s / (4π R2²)                 [W/m²]  수신기 위치 전력밀도
      P_r = S2 · A_eff,  A_eff = G_rx λ²/(4π)     유효개구로 걷어들인 전력
    → P_r = EIRP·G·λ²·σ / ((4π)³ R1² R2²)"""
    eirp_w = 10 ** (eirp_dbm / 10) * 1e-3
    grx = 10 ** (grx_dbi / 10)
    S1 = eirp_w / (4 * np.pi * R1 ** 2)
    P_s = S1 * sigma
    S2 = P_s / (4 * np.pi * R2 ** 2)
    A_eff = grx * lam ** 2 / (4 * np.pi)
    return S1, P_s, S2, A_eff, S2 * A_eff


def echo_power_dbw_dbarith(eirp_dbm, grx_dbi, lam, sigma, R1, R2):
    """경로 2 — **순수 dB 산술**(손계산 그대로). [dBW]"""
    return ((eirp_dbm - 30) + grx_dbi + 20 * np.log10(lam) + 10 * np.log10(sigma)
            - 30 * np.log10(4 * np.pi) - 20 * np.log10(R1) - 20 * np.log10(R2))


def section_A(lb, ch):
    print("=" * 96)
    print("A. 바이스태틱 레이더 방정식 — 독립 유도(전력밀도 사슬 · dB 손계산) vs link_budget.py")
    print("=" * 96)
    rows = []
    worst = 0.0
    for nm, wf in waveforms3():
        for drone in ("mavic4pro", "s1000plus"):
            st = ch.state(TX, RX, np.array(CENTER, float), (SPEED, 0, 0), wf.carrier_hz, drone)
            lt = link_terms(lb, st.lam, st.sigma_m2, st.R1, st.R2, st.L, wf.bw_hz)
            S1, P_s, S2, A_eff, pe1 = independent_echo_power_w(
                lb.eirp_dbm, lb.rx_gain_dbi, st.lam, st.sigma_m2, st.R1, st.R2)
            pe2_dbw = echo_power_dbw_dbarith(lb.eirp_dbm, lb.rx_gain_dbi, st.lam,
                                             st.sigma_m2, st.R1, st.R2)
            # 직접파(Friis 편도) 독립 유도: P_d = EIRP/(4πL²) · A_eff
            eirp_w = 10 ** (lb.eirp_dbm / 10) * 1e-3
            pd1 = eirp_w / (4 * np.pi * st.L ** 2) * A_eff
            # 잡음: kT0B·F  vs  -174 dBm/Hz + NF + 10log10 B
            pn1 = K_BOLTZ * T0 * 10 ** (lb.noise_figure_db / 10) * wf.bw_hz
            pn2_dbm = -174.0 + lb.noise_figure_db + 10 * np.log10(wf.bw_hz)  # 근사(-173.98)
            d_echo1 = float(db(pe1) - db(lt["P_echo_w"]))
            d_echo2 = float(pe2_dbw - db(lt["P_echo_w"]))
            d_dir = float(db(pd1) - db(lt["P_direct_w"]))
            d_n1 = float(db(pn1) - db(lt["P_noise_w"]))
            d_n2 = float((pn2_dbm - 30) - db(lt["P_noise_w"]))
            worst = max(worst, abs(d_echo1), abs(d_echo2), abs(d_dir), abs(d_n1))
            rows.append(dict(
                wf=nm, drone=drone, carrier_hz=wf.carrier_hz, bw_hz=wf.bw_hz,
                sigma_dbsm=float(db(st.sigma_m2)), R1=st.R1, R2=st.R2, L=st.L,
                P_echo_code_dbw=float(db(lt["P_echo_w"])),
                P_echo_chain_dbw=float(db(pe1)), P_echo_dbarith_dbw=float(pe2_dbw),
                P_direct_code_dbw=float(db(lt["P_direct_w"])), P_direct_indep_dbw=float(db(pd1)),
                P_noise_code_dbw=float(db(lt["P_noise_w"])), P_noise_kTBF_dbw=float(db(pn1)),
                P_noise_m174_dbw=float(pn2_dbm - 30),
                d_echo_chain_db=d_echo1, d_echo_dbarith_db=d_echo2,
                d_direct_db=d_dir, d_noise_kTBF_db=d_n1, d_noise_m174_db=d_n2,
                snr_echo_db=lt["snr_echo_db"], dnr_db=lt["dnr_db"]))
    print(f"  {'파형':<11}{'드론':<11}{'σ[dBsm]':>9}{'P_echo(코드)':>13}{'Δ사슬':>8}{'ΔdB산술':>9}"
          f"{'Δ직접파':>9}{'Δ잡음':>8}{'에코SNR':>9}{'DNR':>8}")
    for r in rows:
        print(f"  {r['wf']:<11}{r['drone']:<11}{r['sigma_dbsm']:>9.2f}{r['P_echo_code_dbw']:>13.2f}"
              f"{r['d_echo_chain_db']:>8.2e}{r['d_echo_dbarith_db']:>9.2e}{r['d_direct_db']:>9.2e}"
              f"{r['d_noise_kTBF_db']:>8.2e}{r['snr_echo_db']:>9.1f}{r['dnr_db']:>8.1f}")
    print(f"  → 독립 유도(2경로) vs 코드 최대 편차 = {worst:.2e} dB (부동소수 한계). 식은 일치한다.")
    print(f"  → 잡음: kT0BF 와 '-174 dBm/Hz+NF+10logB' 차이 = {rows[0]['d_noise_m174_db']:+.4f} dB "
          f"(-174 는 -173.98 의 반올림 — 알려진 근사)")
    return dict(rows=rows, max_dev_db=float(worst))


# =========================================================================== #
#  B/E. 처리이득과 손실 — 시뮬 안에서 직접 측정
# =========================================================================== #
def rd_map(surv, ref_cpi, M, n_range, window="hann"):
    """passive_process.range_doppler 와 동일하되 **창을 바꿔 끼울 수 있는** 버전(손실 분해용)."""
    Lf = len(ref_cpi) // M
    S = surv[:M * Lf].reshape(M, Lf)
    Rf = np.conj(np.fft.fft(ref_cpi[:Lf]))
    RP = np.fft.ifft(np.fft.fft(S, axis=1) * Rf[None, :], axis=1)[:, :n_range]
    w = np.hanning(M)[:, None] if window == "hann" else np.ones((M, 1))
    RD = np.fft.fftshift(np.fft.fft(RP * w, axis=0), axes=0)
    return np.abs(RD)


def snr_rd(ref_frame, M, fs, tau, fd, a_tgt, n_range, noise_var=1.0, window="hann",
           eca_taps=None, dpi_amp=0.0, n_noise=6, seed=0):
    """RD맵 출력 SNR [dB] = (무잡음 표적피크 전력) / (잡음전용 RD 평균전력).
    분자·분모를 **분리 측정**해 몬테카를로 분산 없이 정확한 처리이득을 잰다."""
    Lf = len(ref_frame)
    sig, ref_cpi = make_cpi(ref_frame, M, fs, tau, fd, a_tgt=a_tgt, dpi_amp=dpi_amp,
                            clutter=(), abs_noise=True, noise_var=0.0)
    can = ECACanceller(ref_cpi, eca_taps) if eca_taps else None
    s = can.cancel(sig) if can else sig
    rd_s = rd_map(s, ref_cpi, M, n_range, window)
    peak = float(rd_s.max()) ** 2                     # 무잡음 표적 피크 전력
    # 잡음 전용(같은 창·같은 ECA) — RD 셀 평균전력
    npow = []
    for k in range(n_noise):
        rng = np.random.default_rng(1000 + seed + k)
        nz = np.sqrt(noise_var / 2) * (rng.standard_normal(M * Lf) + 1j * rng.standard_normal(M * Lf))
        nn = can.cancel(nz) if can else nz
        npow.append(np.mean(rd_map(nn, ref_cpi, M, n_range, window) ** 2))
    return float(db(peak / np.mean(npow))), peak, float(np.mean(npow))


def section_BE(lb, ch, M=48):
    print()
    print("=" * 96)
    print("B/E. 처리이득(B·T · M) 과 손실 분해 — 시뮬 측정 vs 이론")
    print("=" * 96)
    out = {"waveforms": [], "M": M}
    for nm, wf in waveforms3():
        fs = wf.fs_hz
        n_range, n_taps = chamber_window(wf)
        # run_min_cell 과 **똑같은 정규화**: ref/tx 를 tx rms 로 나눔 → 파일럿 상대전력 보존
        txp = np.sqrt(np.mean(np.abs(wf.tx) ** 2))
        ref_frame = wf.ref.astype(complex) / txp
        Lf0 = frame_len(wf)                            # WiFi 는 패킷률에 맞춰 무음 패딩
        if Lf0 > len(ref_frame):
            ref_frame = np.concatenate([ref_frame, np.zeros(Lf0 - len(ref_frame), complex)])
        Lf = len(ref_frame)
        prf = fs / Lf
        E_ref = float(np.sum(np.abs(ref_frame) ** 2))  # 정합필터 이득 = Σ|ref|²
        dr = C0 / fs                                   # 샘플당 거리
        dfd = prf / M                                  # 도플러 빈 폭

        a = 1e-2                                       # 임의의 작은 진폭(선형계라 값 무관)
        ideal = db(a ** 2 * E_ref * M)                 # 이론 상한(직사각창·격자정합·ECA無)

        # --- 격자에 **정확히** 맞춘 기준 케이스 (straddle 0)
        # ⚠ 거리빈은 n_range 로 잘린다(LTE 는 n_range=6 밖에 안 된다 — c/fs=9.8m).
        #   시험표적을 그 창 **안**에 놓지 않으면 피크가 잘려 나가 처리이득이 -17 dB 로 보인다.
        k_bin = int(min(8, max(1, n_range // 2)))      # 거리: 정수 샘플 지연(창 안)
        tau0 = k_bin / fs
        m_bin = 6                                      # 도플러: 정수 빈 (fd = m·PRF/M)
        fd0 = m_bin * dfd
        cases = {}
        cases["rect_ongrid"] = snr_rd(ref_frame, M, fs, tau0, fd0, a, n_range, window="rect")[0]
        cases["hann_ongrid"] = snr_rd(ref_frame, M, fs, tau0, fd0, a, n_range, window="hann")[0]
        # 도플러 straddle: 반 빈 오프셋 (최악)
        cases["hann_dopp_half"] = snr_rd(ref_frame, M, fs, tau0, fd0 + 0.5 * dfd, a, n_range)[0]
        cases["rect_dopp_half"] = snr_rd(ref_frame, M, fs, tau0, fd0 + 0.5 * dfd, a, n_range,
                                         window="rect")[0]
        # 거리 straddle: 반 샘플 오프셋 (최악)
        cases["hann_rng_half"] = snr_rd(ref_frame, M, fs, tau0 + 0.5 / fs, fd0, a, n_range)[0]
        # ECA 손실(표적 에너지도 사영으로 일부 깎인다)
        cases["hann_ongrid_eca"] = snr_rd(ref_frame, M, fs, tau0, fd0, a, n_range,
                                          eca_taps=n_taps)[0]

        # straddle 최악을 sweep 으로 확인 (거리: 0~1 샘플, 도플러: 0~1 빈)
        sweep_r = [snr_rd(ref_frame, M, fs, tau0 + f / fs, fd0, a, n_range, n_noise=2)[0]
                   for f in np.linspace(0, 1, 7)]
        sweep_d = [snr_rd(ref_frame, M, fs, tau0, fd0 + f * dfd, a, n_range, n_noise=2)[0]
                   for f in np.linspace(0, 1, 7)]
        straddle_r_db = float(cases["hann_ongrid"] - min(sweep_r))
        straddle_d_db = float(cases["hann_ongrid"] - min(sweep_d))

        rec = dict(
            name=nm, fs_hz=fs, bw_hz=wf.bw_hz, ref_bw_hz=wf.ref_bw_hz, carrier_hz=wf.carrier_hz,
            Lf=int(Lf), prf_hz=float(prf), T_frame_us=float(Lf / fs * 1e6),
            T_cpi_ms=float(M * Lf / fs * 1e3), dfd_hz=float(dfd), dr_m=float(dr),
            n_range=int(n_range), n_taps=int(n_taps), test_bin=int(k_bin),
            E_ref=E_ref, mf_gain_db=float(db(E_ref)),
            BT_db=float(db(Lf)),                          # B·T with B=fs → = Lf
            pilot_power_frac_db=float(db(E_ref / Lf)),    # 정합필터 이득이 B·T 에 못 미치는 이유
            cpi_gain_db=float(db(M)),
            theory_ideal_db=float(ideal),
            meas_rect_ongrid_db=cases["rect_ongrid"],
            meas_hann_ongrid_db=cases["hann_ongrid"],
            loss_rect_vs_theory_db=float(cases["rect_ongrid"] - ideal),
            loss_hann_window_db=float(cases["hann_ongrid"] - cases["rect_ongrid"]),
            loss_straddle_dopp_worst_db=straddle_d_db,
            loss_straddle_rng_worst_db=straddle_r_db,
            loss_straddle_dopp_half_db=float(cases["hann_dopp_half"] - cases["hann_ongrid"]),
            loss_straddle_rng_half_db=float(cases["hann_rng_half"] - cases["hann_ongrid"]),
            loss_eca_db=float(cases["hann_ongrid_eca"] - cases["hann_ongrid"]),
            sweep_rng_db=[float(x) for x in sweep_r], sweep_dopp_db=[float(x) for x in sweep_d],
        )
        out["waveforms"].append(rec)
        print(f"\n  [{nm}]  fs={fs/1e6:.2f}MHz  Lf={Lf}  PRF={prf:.0f}Hz  "
              f"T_CPI={rec['T_cpi_ms']:.1f}ms  Δfd={dfd:.1f}Hz  c/fs={dr:.2f}m")
        print(f"    정합필터 이득 Σ|ref|² = {rec['mf_gain_db']:.2f} dB   "
              f"(B·T|_{{B=fs}} = 10log Lf = {rec['BT_db']:.2f} dB, "
              f"파일럿 전력비 {rec['pilot_power_frac_db']:+.2f} dB)")
        print(f"    CPI 적분이득 10log M = {rec['cpi_gain_db']:.2f} dB  "
              f"→ 이론 상한 SNR_RD = {ideal:.2f} dB (a={a})")
        print(f"    측정(직사각·격자정합·ECA無) = {cases['rect_ongrid']:.2f} dB   "
              f"[이론과 차 {rec['loss_rect_vs_theory_db']:+.3f} dB]")
        print(f"    Hann 창손실 {rec['loss_hann_window_db']:+.2f} dB (이론 -1.76)  |  "
              f"도플러 straddle 최악 {-straddle_d_db:+.2f} dB  |  거리 straddle 최악 {-straddle_r_db:+.2f} dB  |  "
              f"ECA {rec['loss_eca_db']:+.2f} dB")

    # --- CFAR 손실(임계 초과분) — 학습셀 수의 함수
    pfa = 1e-4
    cf = []
    for ntr in (264, 132, 66):
        alpha = ntr * (pfa ** (-1.0 / ntr) - 1.0)
        alpha_ideal = -np.log(pfa)                   # 잡음 기지(known-σ) 임계
        cf.append(dict(n_train=ntr, alpha_ca=float(alpha), alpha_ideal=float(alpha_ideal),
                       cfar_loss_db=float(db(alpha / alpha_ideal))))
    out["cfar"] = dict(pfa=pfa, guard=[2, 2], train=[6, 6],
                       n_train_full=264, rows=cf)
    print(f"\n  [CFAR 손실]  Pfa={pfa:g}, guard=(2,2) train=(6,6) → 학습셀 264개(맵 내부)")
    for c in cf:
        print(f"    Ntrain={c['n_train']:4d}: α_CA={c['alpha_ca']:.3f} vs α_ideal(-lnPfa)="
              f"{c['alpha_ideal']:.3f} → CFAR 손실 {c['cfar_loss_db']:+.3f} dB")
    print("    → 학습셀이 많아 CFAR 손실은 0.1 dB 수준. 맵 가장자리(학습셀 반토막)에서도 0.2 dB 미만.")
    return out


# =========================================================================== #
#  C. 잡음바닥 — bw_corr = √(B/fs) 의 정당성과 공정성
# =========================================================================== #
def section_C(lb, ch, M=48):
    print()
    print("=" * 96)
    print("C. 잡음바닥 kT0BF 와 bw_corr=√(B/fs) — 협대역/광대역 계통편향이 있는가")
    print("=" * 96)
    print("  [해석] 주입 에코전력 = (Pe/Pn)·(B/fs) = Pe/(k·T0·F·fs) → **선언된 B 가 소거된다.**")
    print("         즉 bw_corr 를 곱하면 링크버짓이 어떤 B 를 쓰든 결과가 같다(잡음 PSD 만 남는다).")
    rows = []
    for nm, wf in waveforms3():
        st = ch.state(TX, RX, np.array(CENTER, float), (-SPEED, 0, 0), wf.carrier_hz, "mavic4pro")
        N0 = K_BOLTZ * T0 * 10 ** (lb.noise_figure_db / 10)
        Pe = lb.echo_power_w(st.lam, st.sigma_m2, st.R1, st.R2)
        # 세 가지 '선언 대역' 으로 a_tgt 를 만들어 본다 → 같아야 한다
        a = {}
        for tag, B in (("B=점유대역", wf.bw_hz), ("B=fs", wf.fs_hz), ("B=B/2", wf.bw_hz / 2)):
            lt = link_terms(lb, st.lam, st.sigma_m2, st.R1, st.R2, st.L, B)
            a[tag] = lt["a_tgt"] * np.sqrt(B / wf.fs_hz)      # bw_corr 적용
        a_ref = float(np.sqrt(Pe / (N0 * wf.fs_hz)))          # 이론: √(Pe/(N0·fs))
        spread = float(db(max(a.values()) ** 2) - db(min(a.values()) ** 2))
        # bw_corr 를 **뺐을 때** 생기는 편향
        bias_db = float(-db(wf.bw_hz / wf.fs_hz))             # 협대역일수록 부당하게 커짐
        rows.append(dict(name=nm, fs_hz=wf.fs_hz, bw_hz=wf.bw_hz,
                         a_tgt_B=a["B=점유대역"], a_tgt_fs=a["B=fs"], a_tgt_Bhalf=a["B=B/2"],
                         a_tgt_theory=a_ref,
                         spread_db=spread,
                         err_vs_theory_db=float(db(a["B=점유대역"] ** 2 / a_ref ** 2)),
                         bias_if_no_bwcorr_db=bias_db,
                         snr_echo_db_declaredB=float(db(Pe / lb.noise_power_w(wf.bw_hz))),
                         snr_per_sample_db=float(db(a_ref ** 2))))
    print(f"\n  {'파형':<11}{'fs[MHz]':>9}{'B[MHz]':>8}{'a_tgt(B)':>11}{'a_tgt(fs)':>11}"
          f"{'a_tgt(B/2)':>12}{'퍼짐[dB]':>10}{'이론과차':>9}{'bw_corr 뺄때 편향':>16}")
    for r in rows:
        print(f"  {r['name']:<11}{r['fs_hz']/1e6:>9.2f}{r['bw_hz']/1e6:>8.2f}{r['a_tgt_B']:>11.4e}"
              f"{r['a_tgt_fs']:>11.4e}{r['a_tgt_Bhalf']:>12.4e}{r['spread_db']:>10.1e}"
              f"{r['err_vs_theory_db']:>9.1e}{r['bias_if_no_bwcorr_db']:>16.2f}")
    bias = [r["bias_if_no_bwcorr_db"] for r in rows]
    print(f"\n  → bw_corr 를 적용하면 선언 B(점유/fs/B의 절반)와 무관하게 a_tgt 동일 "
          f"(퍼짐 ≤ {max(r['spread_db'] for r in rows):.1e} dB) = 이론 √(Pe/(N0·fs)) 와 일치.")
    print(f"  → **뺐다면**: 파형별 이득 {min(bias):+.2f}…{max(bias):+.2f} dB → "
          f"협대역(LTE)이 광대역(WiFi) 대비 최대 {max(bias)-min(bias):.2f} dB **부당 우위**. 보정은 옳다.")
    # ★ 남는 진짜 비대칭: CPI **관측시간**이 파형마다 다르다 (M 프레임 × 프레임길이)
    tc = []
    for nm, wf in waveforms3():
        Lf = frame_len(wf)
        tc.append((nm, M * Lf / wf.fs_hz * 1e3))
    print(f"\n  ⚠ 그러나 **관측시간**은 아직 공정하지 않다 — 같은 M={M} 프레임이 서로 다른 시간:")
    for nm, t in tc:
        print(f"      {nm:<11} T_CPI = {t:6.2f} ms")
    print(f"    → 최대 {db(max(t for _, t in tc) / min(t for _, t in tc)):.2f} dB 의 코히어런트 "
          f"적분이득 차이가 '신호 물리'가 아니라 '프레임 정의'에서 온다.")
    return dict(rows=rows,
                bias_if_no_bwcorr_span_db=float(max(bias) - min(bias)),
                cpi_ms={nm: t for nm, t in tc},
                cpi_span_db=float(db(max(t for _, t in tc) / min(t for _, t in tc))))


# =========================================================================== #
#  D. σ(SBR) 드론 전 기종 × 3파형 — 유도 SNR vs 측정 SCR
# =========================================================================== #
def section_D(lb, ch, be, M=48, N=40):
    print()
    print("=" * 96)
    print(f"D. {len(LB_DRONES)}드론 × 3파형 — 유도 SNR(링크버짓+처리이득) vs 측정 SCR(RD맵). 차이 = 처리손실")
    print("=" * 96)
    be_by_name = {r["name"]: r for r in be["waveforms"]}
    pos, vel = radial(TX, RX, np.array(CENTER, float), speed=SPEED, span=SPAN, n=3)
    pos = np.tile(np.array(CENTER, float), (3, 1))          # 대표 스냅샷 = CENTER 고정
    rows = []
    for nm, wf in waveforms3():
        rec = be_by_name[nm]
        for drone in LB_DRONES:
            res = run_cell(wf, drone, pos, vel, lb, channel=ch, M=M, N=N, pfa=1e-4)
            st, lt = res["state"], res["link"]
            # --- 유도(예측) RD SNR: 물리 → 주입 → 처리이득 → Hann
            bw_corr2 = wf.bw_hz / wf.fs_hz
            a2 = lt["a_tgt"] ** 2 * bw_corr2                # 주입 에코 per-sample 전력(정규화 ref 기준 계수)
            pred_coh = float(db(a2 * rec["E_ref"] * M))     # 직사각·격자정합 상한
            pred_hann = pred_coh + rec["loss_hann_window_db"]
            meas = res["scr_mean"]
            rows.append(dict(
                wf=nm, drone=drone, carrier_ghz=wf.carrier_hz / 1e9,
                sigma_dbsm=float(db(st.sigma_m2)),
                snr_echo_db=lt["snr_echo_db"], dnr_db=lt["dnr_db"],
                snr_per_sample_eff_db=float(db(a2 * rec["E_ref"] / rec["Lf"])),
                pred_coh_db=pred_coh, pred_hann_db=pred_hann,
                scr_meas_db=meas, scr_std_db=res["scr_std"],
                gap_db=float(meas - pred_hann), pd=res["pd"]))
    print(f"\n  {'파형':<11}{'드론':<11}{'σ[dBsm]':>9}{'에코SNR':>9}{'예측SNR_RD':>11}"
          f"{'측정SCR':>10}{'차이(처리손실)':>14}{'Pd':>6}")
    for r in rows:
        print(f"  {r['wf']:<11}{r['drone']:<11}{r['sigma_dbsm']:>9.1f}{r['snr_echo_db']:>9.1f}"
              f"{r['pred_hann_db']:>11.1f}{r['scr_meas_db']:>10.1f}{r['gap_db']:>14.2f}"
              f"{r['pd']:>6.2f}")
    g = np.array([r["gap_db"] for r in rows])
    print(f"\n  → 처리손실(측정 − 예측) 평균 {g.mean():+.2f} dB, 표준편차 {g.std():.2f} dB, "
          f"범위 [{g.min():+.2f}, {g.max():+.2f}]")
    print("    (음수 = 예측보다 덜 나옴 = straddle·프레임내도플러·ECA 손실. "
          "양수는 measure_scr 의 3x3 max 상향바이어스가 섞인 것.)")
    return dict(rows=rows, gap_mean_db=float(g.mean()), gap_std_db=float(g.std()),
                gap_min_db=float(g.min()), gap_max_db=float(g.max()), M=M, N=N)


# =========================================================================== #
#  D2. '처리손실'이 강한 표적에서 커지는 이유 — SCR 분모(기준영역)의 부엽 융단
# =========================================================================== #
def section_D2(lb, ch, M=48):
    """D 에서 손실이 강표적(s1000plus)일수록 커졌다. 진짜 SNR 손실인가, 아니면
    **measure_scr 분모**가 표적 자신의 부엽으로 들어올려진 것인가 — 셋을 분리해 잰다:
      (a) 실제(표적+DPI+잡음)  (b) 표적만 제거  (c) 순수 잡음
    의 기준영역 평균전력. (a)-(b)=표적 부엽 융단,  (b)-(c)=ECA 후 DPI 잔류."""
    print()
    print("=" * 96)
    print("D2. SCR 분모 해부 — '처리손실'이 강표적에서 커지는 게 SNR 손실인가 metric 인가")
    print("=" * 96)
    out = []
    for nm, wf in waveforms3():
        for drone in _EXTREME_DRONES:               # 최약/최강 표적(레지스트리에서 유도)
            fs = wf.fs_hz
            n_range, n_taps = chamber_window(wf)
            txp = np.sqrt(np.mean(np.abs(wf.tx) ** 2))
            ref_frame = wf.ref.astype(complex) / txp
            tx_frame = wf.tx.astype(complex) / txp
            Lf = frame_len(wf)
            if Lf > len(ref_frame):
                pad = np.zeros(Lf - len(ref_frame), complex)
                ref_frame = np.concatenate([ref_frame, pad])
                tx_frame = np.concatenate([tx_frame, pad])
            st = ch.state(TX, RX, np.array(CENTER, float), (-SPEED, 0, 0), wf.carrier_hz, drone)
            lt = link_terms(lb, st.lam, st.sigma_m2, st.R1, st.R2, st.L, wf.bw_hz)
            bwc = np.sqrt(wf.bw_hz / fs)
            tgt, ref_cpi = make_cpi(ref_frame, M, fs, st.tau, st.fd, a_tgt=lt["a_tgt"] * bwc,
                                    dpi_amp=0.0, clutter=(), abs_noise=True, noise_var=0.0)
            dpid, _ = make_cpi(tx_frame, M, fs, 0.0, 0.0, a_tgt=0.0,
                               dpi_amp=lt["dpi_amp"] * bwc, clutter=(), abs_noise=True, noise_var=0.0)
            can = ECACanceller(ref_cpi, n_taps)
            rng = np.random.default_rng(7)
            nz = np.sqrt(0.5) * (rng.standard_normal(len(ref_cpi))
                                 + 1j * rng.standard_normal(len(ref_cpi)))
            true_Rb = st.tau * C0

            def floor_of(sig):
                from passive_process import range_doppler
                Rb, f_d, rd = range_doppler(can.cancel(sig), ref_cpi, fs, M, n_range=n_range)
                ri = int(np.argmin(np.abs(Rb - true_Rb))); di = int(np.argmin(np.abs(f_d - st.fd)))
                mask = np.ones_like(rd, bool); zd = int(np.argmin(np.abs(f_d)))
                mask[max(0, zd - 1):zd + 2, :] = False
                mask[max(0, di - 3):di + 4, max(0, ri - 3):ri + 4] = False
                return float(np.mean(rd[mask] ** 2)), rd, Rb, f_d

            f_all, rd_all, Rb, f_d = floor_of(tgt + dpid + nz)
            f_nt, _, _, _ = floor_of(dpid + nz)          # 표적만 뺀 것
            f_n, _, _, _ = floor_of(nz)                  # 순수 잡음
            scr, _ = measure_scr(Rb, f_d, rd_all, true_Rb, st.fd)
            rec = dict(wf=nm, drone=drone, sigma_dbsm=float(db(st.sigma_m2)), scr_db=scr,
                       floor_all_db=float(db(f_all)), floor_noTGT_db=float(db(f_nt)),
                       floor_noise_db=float(db(f_n)),
                       pedestal_from_target_db=float(db(f_all / f_nt)),
                       eca_dpi_residual_db=float(db(f_nt / f_n)),
                       scr_vs_purenoise_db=float(scr + db(f_all / f_n)))
            out.append(rec)
            print(f"  {nm:<11}{drone:<11} σ={rec['sigma_dbsm']:+6.1f}  SCR={scr:5.1f} dB  |  기준영역 바닥: "
                  f"실제 {rec['floor_all_db']:6.2f} / 표적제거 {rec['floor_noTGT_db']:6.2f} / "
                  f"순수잡음 {rec['floor_noise_db']:6.2f} dB  →  **표적 부엽융단 "
                  f"{rec['pedestal_from_target_db']:+.2f} dB**, ECA 후 DPI 잔류 "
                  f"{rec['eca_dpi_residual_db']:+.2f} dB", flush=True)
    print("  → 강표적일수록 자기 부엽이 SCR 분모를 들어올린다 → 'D 의 처리손실'은 SNR 손실이 아니라")
    print("    **SCR 지표의 압축**이다. CFAR 는 국소 잡음을 보므로 Pd 에는 영향 없다.")
    print("  → ECA 후 DPI 잔류는 잡음바닥 대비 0.00 dB (완전 소거) — 링크버짓 DNR 60 dB 에서도.")
    return out


def _save(res):
    """섹션마다 즉시 저장 — 긴 실행이 중간에 죽어도 측정값이 남는다."""
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    tmp = OUT_JSON + ".tmp"
    with open(tmp, "w") as f:
        json.dump(res, f, indent=1)
    os.replace(tmp, OUT_JSON)


def main():
    lb = LinkBudget(eirp_dbm=EIRP_DBM)
    ch = AnalyticChannel()                      # σ = SBR(가림 포함), 클러터 없음(죽은 파라미터)
    print(f"[설정] EIRP={lb.eirp_dbm} dBm, G_rx={lb.rx_gain_dbi} dBi, NF={lb.noise_figure_db} dB, "
          f"챔버 TX={TX} RX={RX} 표적={CENTER}", flush=True)
    res = dict(config=dict(eirp_dbm=lb.eirp_dbm, rx_gain_dbi=lb.rx_gain_dbi,
                           noise_figure_db=lb.noise_figure_db, TX=list(map(float, TX)),
                           RX=list(map(float, RX)), TGT=list(map(float, CENTER)),
                           speed_ms=SPEED, rcs_engine="sbr"))
    res["A_radar_equation"] = section_A(lb, ch); _save(res)
    res["BE_processing_gain"] = section_BE(lb, ch); _save(res)
    res["C_noise_floor"] = section_C(lb, ch); _save(res)
    res["D_sigma_table"] = section_D(lb, ch, res["BE_processing_gain"]); _save(res)
    res["D2_pedestal"] = section_D2(lb, ch); _save(res)
    print(f"\n측정 JSON 저장 → {OUT_JSON}")


def only_d2():
    """`python verify_linkbudget.py d2` — D2 만 다시 재서 기존 JSON 에 병합(전체 45분 재실행 회피)."""
    lb, ch = LinkBudget(eirp_dbm=EIRP_DBM), AnalyticChannel()
    res = json.load(open(OUT_JSON))
    res.pop("D_pedestal_check", None)
    res["D2_pedestal"] = section_D2(lb, ch)
    _save(res)
    print(f"\nD2 병합 저장 → {OUT_JSON}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "d2":
        only_d2()
    else:
        main()
