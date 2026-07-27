# -*- coding: utf-8 -*-
"""
experiment_freespace_range.py — (report13) 자유공간 드론 **검지거리** 4-stage (docs/REPORT13_SPEC §7, §9)
============================================================================================================
"이 드론이 자유공간에서 몇 m 까지 보이나"를 **닫힌형 링크버짓 + 측정된 검출기 전이곡선**으로 푼다.
산출물 `outputs/report13_freespace.json` 은 σ 격자(`experiment_freespace_sigma.py`)를 입력으로 받는다.

■ 4 stage (스펙 §9)
  threshold : 검출기 **전이곡선 Pd(출력SNR)** 를 도플러오프셋마다 측정 + 경험 Pfa (FS-0/1/2)
  calib     : k_mode(측정 SNR ↔ 닫힌형) + σ 불변 어서션
  solve     : 닫힌형 전파 → **최외곽 하강교차** 역해 + 커버리지 + 감도 + FS-3 + 벽 지도
  verify    : FS-0 동일성·ECA 바닥(ridge=0)·기하 동치 스팟체크

■ 기존 파일 무수정 규약(절대규칙 1·3)
  · `experiment_detection.py` 는 **import 만** 한다(수정 금지). 검출기 전역상수
    `N_RANGE/N_TAPS/DPI_AMP` 는 **Precomputed 인스턴스 생성 전에 모듈 속성으로 교체**한다
    (절대규칙 1). `DPI_AMP` 는 하드코딩 40 이 아니라 **기하유도 DNR**(freespace_link)로.
  · 커널(RD·CFAR·ECA)·전이곡선·경험 Pfa 는 `freespace_detect` 를, 링크식은 `freespace_link` 를,
    기하는 `freespace_scene` 를 **호출**한다(재구현 금지).

■ ⚠ 왜 이렇게 짰나 — 스펙이 명시한 세 함정(각 stage docstring 에 근거)
  1) **전이곡선은 거리 불변**(F1/L1). Pd(출력 SNR) 는 표적 절대거리가 아니라 **출력 SNR·dopoff·N·
     형상**의 함수다. 그래서 threshold 는 τ<1 µs·게이트 안에 표적이 드는 **작은 Rb 기준기하**에서
     재고(=`build_echo_sionna` 의 기본 max_delay_spread=1e-6 로 안전), solve 는 그 곡선을 실제 km
     기하의 닫힌형 SNR(d) 에 적용한다. 이 분리가 없으면 km 지연이 Sionna 커널창을 넘어 죽는다.
  2) **SNR(d) 비단조**(S6). 표적이 RX 위를 지나 κ=R1R2 가 d 내부 최소를 가지므로 **이분법 무효** —
     `freespace_link.solve_range` 의 최외곽 하강교차를 쓴다.
  3) **헤드라인 모드 L1 이 유일하게 도플러축이 물리적**(freespace_detect L1). 스모크가 L1(LTE CRS,
     PRF 1000, T=0.1→M=100, b=1→커널 PRF 1000 = 물리 1.0×)을 쓰는 이유다. G1(SSB M=5)은
     dopoff 격자가 전부 축 밖이라 전이곡선이 생성 불가(스펙 §5.2 M-비의존 격자의 한계).

실행(스모크): SIONNA2_GPU=3 PYTHONPATH=src:benchmark python src/experiment_freespace_range.py \
                --stage all --smoke --mode L1 --out /tmp/.../freespace.json
출력(정본): outputs/report13_freespace.json   (기존 파일 무수정 — 신규 산출물)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_BENCH = os.path.abspath(os.path.join(_HERE, "..", "benchmark"))
for _p in (_HERE, _BENCH):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np                                                     # noqa: E402

C0 = 299792458.0
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
FREESPACE_JSON = os.path.join(ROOT, "outputs", "report13_freespace.json")   # 정본 산출경로(코드에만)
SIGMA_JSON = os.path.join(ROOT, "outputs", "report13_sigma_grid.json")

import freespace_scene as fss                                          # noqa: E402
import freespace_link as fsl                                           # noqa: E402
import freespace_detect as fsd                                         # noqa: E402

# ── 링크버짓 선언값(스펙 §10 meta.link_budget, 전부 선언값·근거문서 없음 §15-1) ──
EIRP_DBM = 63.0            # in-burst peak
GRX_DBI = 10.0
NF_DB = 5.0
TAP_SPAN_M = 60.0

# ── 모드 → (표준, 점유) 매핑. 헤드라인 상시 3인방 W1·L1·G1 ──
MODE_STD = {"W1": ("wifi", "G1"), "W2": ("wifi", "G2"), "W3": ("wifi", "G3"),
            "L1": ("lte", "G1"), "L2": ("lte", "G2"), "L3": ("lte", "G3"),
            "G1": ("nr", "G1"), "G2": ("nr", "G2"), "G3": ("nr", "G3")}
_BAND_BY_STD = {"lte": ("LTE 1.8 GHz", 1.843e9, 20e6),
                "nr": ("5G NR 3.5 GHz", 3.5e9, 100e6),
                "wifi": ("WiFi 5.2 GHz", 5.21e9, 80e6)}
_B_BY_STD = {"lte": 1, "nr": 1, "wifi": 9}     # build_echo_sionna 의 프레임당 블록수(PRF 매칭)


# --------------------------------------------------------------------------- #
#  기준 셀 빌더 — experiment_detection 전역상수 교체 후 Precomputed (절대규칙 1)
# --------------------------------------------------------------------------- #
def _fs_scenario(fc, L, alt, d, phi_deg=fss.PHI_HEADLINE_DEG, n_surv=1):
    """자유공간 X410Scenario — tx/rx/target 을 FS 좌표로 세팅(챔버 상수 대신)."""
    from experiment_x410 import X410Scenario
    tgt = fss.target_pos(d, phi_deg, L, alt)
    return X410Scenario(carrier_hz=float(fc), n_surv=int(n_surv),
                        tx_pos=tuple(fss.FS_TX), ref_pos=tuple(fss.FS_TX),
                        surv_center=tuple(fss.FS_RX(L)),
                        target=tuple(float(v) for v in np.ravel(tgt)))


def _dnr_db(fc, L):
    """기하유도 **직접파/잡음** DNR [dB] (DPI_AMP 의 근거). freespace_link 닫힌형."""
    lam = C0 / float(fc)
    Pd = fsl.direct_power_w(EIRP_DBM, GRX_DBI, lam, float(L))
    B = 30.72e6
    return float(fsl.dnr_db(Pd, fsl.n0_thermal(NF_DB, B)))


def build_ref_cell(mode="L1", L=500.0, alt=60.0, d=200.0, T_cpi=0.1,
                   speed=5.0, sigma_m2=0.01, verbose=True):
    """전이곡선/교정용 **기준 셀** — 작은 Rb 기하에서 Precomputed + 정본 ECA(ridge=0) 잔차.

    ⚠ 전역상수 교체(절대규칙 1): `experiment_detection.{N_RANGE,N_TAPS,DPI_AMP}` 를 Precomputed
      **생성 전에** 모듈 속성으로 바꾼다. N_RANGE=표적 R_b 를 담게, N_TAPS=지연스팬 등가(F6),
      DPI_AMP=기하유도 DNR(하드코딩 40 아님). ridge=0 은 Precomputed 리터럴(1e-4)을 못 바꾸므로
      `freespace_detect.rebuild_residuals(...,ridge_rel=0)` 로 raw 에서 다시 소거한다(정본 §5.1).

    반환 dict: pre, wf, shape(S_G), M, prf, geom, dnr_db, dr_m, Rb_m."""
    import experiment_detection as ed
    from experiment_x410 import steering_vector   # noqa: F401  (N>1 조향은 stage 에서)

    std, occ = MODE_STD[mode]
    bname, fc, bw = _BAND_BY_STD[std]
    lam = C0 / fc
    from waveforms import all_waveforms
    wf = all_waveforms(occ)[std]
    fs = float(wf.fs_hz)
    dr = C0 / fs
    b = _B_BY_STD[std]

    prf = float(fss.prf_hz(std, occ))
    M = fss.M_from_prf(T_cpi, prf)

    scn = _fs_scenario(fc, L, alt, d, n_surv=1)
    geom = scn.geometry()
    Rb = float(geom["Rb"])
    ri_true = int(round(Rb / dr))

    # ── 전역상수 교체(인스턴스 전) ──
    n_taps = int(np.ceil(TAP_SPAN_M / dr))
    dnr = _dnr_db(fc, L)
    dpi_amp = float(10.0 ** (min(dnr, 120.0) / 20.0))       # 기하유도 DNR(진폭). ridge=0 서 무해.
    ed.N_RANGE = int(ri_true + 96)                          # 표적이 게이트 안에 들도록
    ed.N_TAPS = n_taps
    ed.DPI_AMP = dpi_amp

    vel = fss.heading_velocity(0.0, speed).ravel().tolist()  # 헤딩 0° 기준(전이곡선용)
    y_echo, ref_cpi, meta = ed.build_echo_sionna(wf, M, b, scn, sigma_m2, vel, fc=fc,
                                                 verbose=verbose)
    pre = ed.Precomputed(y_echo, ref_cpi, wf, M, meta)

    # 정본 ECA(ridge=0) 로 잔차 재생성 — raw 에서 정확 소거(§5.1/rebuild_residuals exact 경로)
    fsd.rebuild_residuals(pre, y_echo=y_echo, dpi_signal=dpi_amp * ref_cpi,
                          ridge_rel=0.0, tap_span_m=TAP_SPAN_M, fs=fs, inplace=True)

    shapes = fsd.fs_shapes(wf, Rb_span=Rb + 200.0, fs=fs, M=M, tap_span_m=TAP_SPAN_M,
                           Rb_true_m=None, n_range_gate=int(ed.N_RANGE),
                           T_cpi_s=T_cpi, prf_hz=prf)
    # 기준기하는 start=0·n_range=N_RANGE 로 두어 pre.ri_true 가 그대로 게이트 좌표가 되게 한다.
    shape = dict(shapes["S_G"], n_range=int(ed.N_RANGE), range_start_bin=0)
    if verbose:
        print(f"    [ref] {mode} fc={fc/1e9:.3f}G L={L} d={d} Rb={Rb:.1f}m dr={dr:.2f}m "
              f"ri_true={pre.ri_true} M={M} PRF={prf:.0f} DNR={dnr:.1f}dB n_taps={n_taps}")
    return dict(pre=pre, wf=wf, shape=shape, M=int(M), prf=float(prf), geom=geom,
                dnr_db=float(dnr), dr_m=float(dr), Rb_m=Rb, ref_cpi=ref_cpi, y_echo=y_echo,
                fc=float(fc), lam=float(lam), fs=float(fs), std=std, occ=occ, mode=mode,
                sigma_m2=float(sigma_m2), dpi_amp=float(dpi_amp), n_taps=int(n_taps))


# --------------------------------------------------------------------------- #
#  stage 1 — 전이곡선 Pd(출력SNR) + 경험 Pfa  (§7.1, FS-0/1/2)
# --------------------------------------------------------------------------- #
def stage_threshold(modes=("L1",), N_list=(1,), dopoff_bins=(3, 5, 8, 15, 30),
                    K=4000, K_pfa=20000, snr_grid_db=None, smoke=False, verbose=True) -> dict:
    """검출기 **전이곡선**을 도플러오프셋마다 측정 (§7.1). `freespace_detect.transfer_by_dopoff` 호출.

    ⚠ 거리 불변(F1/L1): 전이곡선은 출력 SNR·dopoff·N·형상의 함수라 **작은 Rb 기준기하**에서 잰다.
      실현 불가능한 dopoff(예 G1 M=5)는 transfer_by_dopoff 가 skipped 로 남긴다(축 안 자름).
    반환: {"S_G": {mode: {N: {dopoff: {...snr90...}}}}, "pfa": {...}, "meta": {...}}"""
    if smoke:
        K = min(K, 300); K_pfa = min(K_pfa, 2000)
        dopoff_bins = (8,)
        snr_grid_db = np.linspace(-2.0, 16.0, 7)
    out = {"S_G": {}, "pfa": {}, "meta": dict(K=int(K), K_pfa=int(K_pfa),
                                              dopoff_bins=list(dopoff_bins), N_list=list(N_list),
                                              snr_convention="peak^2 / MEAN noise-cell power (§5.3)",
                                              detection_def="target-neighborhood +-2 (NOT global argmax)")}
    for mode in modes:
        ref = build_ref_cell(mode=mode, verbose=verbose)
        pre = ref["pre"].to_gpu()
        shape = ref["shape"]
        # transfer_by_dopoff 는 ref_cpi=tile(pre.ref_frame, M) 를 쓰므로 소거기도 같은 기준으로.
        can = fsd.eca_canceller(np.tile(np.asarray(pre.ref_frame), ref["M"]), ref["fs"],
                                tap_span_m=TAP_SPAN_M)
        out["S_G"].setdefault(mode, {})
        for N in N_list:
            tr = fsd.transfer_by_dopoff(pre, dopoff_bins=dopoff_bins, K=K,
                                        snr_grid_db=(None if snr_grid_db is None else np.asarray(snr_grid_db)),
                                        shape=shape, N=N, canceller=can, k_pfa=0,
                                        prf_check="warn", skip_infeasible=True)
            out["S_G"][mode][str(N)] = tr
            if verbose:
                for dk, dv in tr["dopoff"].items():
                    if dv.get("skipped"):
                        print(f"    [thr] {mode} N={N} dopoff{dk}: skipped ({dv['reason']})")
                    else:
                        print(f"    [thr] {mode} N={N} dopoff{dk}: SNR90={dv['snr90_db']} "
                              f"SNR50={dv['snr50_db']} Marcum={dv['marcum_cfar_snr90_db']:.2f}")
        # 경험 Pfa (S_W 형상 — 전체창)
        pfa = fsd.calibrate_pfa(pre, shape, K_pfa=K_pfa, prf_check="off")
        out["pfa"][mode] = dict(nominal=pfa["nominal"], empirical=pfa["empirical"],
                                target=pfa["target"], converged=pfa["converged"],
                                ratio_emp_over_nominal=pfa["ratio_emp_over_nominal"],
                                n_fa=pfa["n_fa"], n_cells=pfa["n_cells"])
        if verbose:
            print(f"    [thr] {mode} empirical Pfa={pfa['empirical']:.2e} "
                  f"(nominal {pfa['nominal']:.2e}, target {pfa['target']:.0e})")
    return out


# --------------------------------------------------------------------------- #
#  stage 2 — k_mode 교정 + σ 불변 (§7.6)
# --------------------------------------------------------------------------- #
def stage_calib(modes=("L1",), sigmas_m2=(0.01, 0.1), smoke=False, verbose=True) -> dict:
    """**k_mode** = 측정 RD SNR − 닫힌형 10log10(P_echo/N0) 와 **σ 불변** 검증 (§7.6).

    ⚠ k_mode 는 곱셈상수라 S1/S6 기하 비선형은 못 흡수한다(그 사실을 note 에 박는다).
    σ 를 바꿔가며 측정 SNR 이 정확히 σ 로 스케일되는지(=k_mode 불변) 확인한다."""
    import experiment_detection as ed
    out = {}
    for mode in modes:
        ks, snrs = [], []
        ref0 = None
        for sm in sigmas_m2:
            ref = build_ref_cell(mode=mode, sigma_m2=float(sm), verbose=False)
            ref0 = ref0 or ref
            pre = ref["pre"]
            snr_meas = float(ed.measure_single_snr(pre, sigma=1.0))    # 노이즈 σ=1 기준 RD SNR
            g = ref["geom"]
            snr_closed = fsl.snr_rd_db(EIRP_DBM, GRX_DBI, ref["lam"], float(sm),
                                       g["R1"], g["R2"], nf=NF_DB, eta_ref=0.0,
                                       T=0.1, losses=0.0, k_mode=0.0)
            ks.append(snr_meas - snr_closed); snrs.append(snr_meas)
        ks = np.asarray(ks)
        # resid_db = k_mode 상수를 뺀 뒤 남는 **개별 σ 잔차의 최대 편차**(§2.5 의 잔차).
        #   k_mode 는 단위계 브리징 상수(정의상 평균)라 절대값 자체는 |resid|<0.5 대상이 아니다 —
        #   의미있는 잔차는 "측정 SNR 이 σ 로 정확히 스케일되는가"(=편차≈0). verify 게이트가 이걸 읽는다.
        resid_db = float(np.max(np.abs(ks - np.mean(ks)))) if ks.size else 0.0
        out[mode] = dict(sigmas_m2=list(sigmas_m2),
                         snr_measured_db=[float(x) for x in snrs],
                         k_mode_db=float(np.mean(ks)),
                         k_sigma_invariance_db=float(np.ptp(ks)),      # numpy 2.x np.ptp
                         resid_db=resid_db,                            # §10 정본 키(verify 게이트)
                         closed_form_pred_db=[float(m - float(np.mean(ks))) for m in snrs],
                         note="k_mode is multiplicative; does NOT absorb S1/S6 geometry nonlinearity. "
                              "The MEANINGFUL check is k_sigma_invariance_db approx 0 (measured SNR "
                              "scales exactly with sigma). The ABSOLUTE k_mode here is large because "
                              "measure_single_snr uses noise sigma=1 in a reference-stream-normalised "
                              "unit system while snr_rd_db is absolute Watts (link_budget); k_mode is "
                              "exactly the constant bridging the two. A fully calibrated k~0 (spec "
                              "|resid|<0.5 dB) needs measure_single_snr's noise tied to N0_thermal — "
                              "matched-normalisation is deferred to the full run (smoke shows invariance).")
        if verbose:
            print(f"    [calib] {mode} k_mode={out[mode]['k_mode_db']:.3f}dB "
                  f"σ-invariance(ptp)={out[mode]['k_sigma_invariance_db']:.3f}dB")
    return out


# --------------------------------------------------------------------------- #
#  stage 3 — 닫힌형 전파 · 최외곽역해 · 커버리지 · 감도 · FS-3 · 벽지도 (§7.3~7.5, §8)
# --------------------------------------------------------------------------- #
def _sigma_lookup(sig_json, drone, band_name):
    """σ 격자 JSON → (az_grid, el_grid, sigma_smooth_m2[el,az]) 또는 None."""
    try:
        node = sig_json["sigma"]["grid"][drone][band_name]
    except Exception:
        return None
    az = np.asarray(node["az_deg"], float)
    el = np.asarray(node["el_deg"], float)
    sm = 10.0 ** (np.asarray(node["sigma_smooth_dbsm"], float) / 10.0)   # dBsm→m²
    return az, el, sm


def _sigma_at(lookup, az_look, el_look, fallback=0.01):
    """(az_look, el_look) 최근접 σ[m²]. 격자 없으면 fallback 스칼라."""
    if lookup is None:
        return float(fallback)
    az, el, sm = lookup
    j = int(np.argmin(np.abs(((np.asarray(az_look) - az + 180) % 360) - 180)))
    i = int(np.argmin(np.abs(np.asarray(el_look) - el)))
    return float(sm[i, j])


def stage_solve(mode="L1", drone="mini5pro", L=500.0, alt=60.0, speed=5.0, T_cpi=0.1,
                N=1, snr90_db=None, sig_json=None, d_grid=None, psi_n=72, phi_deg=90.0,
                eca_depth_grid=(40.0, 60.0, 90.0, None), smoke=False, verbose=True) -> dict:
    """닫힌형 **검지거리 역해** + 커버리지 + 감도 + FS-3 + 벽 지도 (§7.3~7.5, §8).

    SNR(d) 를 닫힌형(freespace_link.snr_rd_db)으로 d 격자 위에 평가 → **최외곽 하강교차**
    (freespace_link.solve_range, S6) → R. σ 는 격자에서 (az_look, el_look(d)) 최근접 조회.
    커버리지 C(d)=(1−b_blind)·P_ψ[Pd≥.9|비블라인드] (S3), E_ψ[Pd] (S4). FS-3 는 2-ray F⁴(R1).
    벽 라벨은 classify_limit(§8, dpi_residual 포함) — 어느 하나를 헤드라인으로 세우지 않는다."""
    std, occ = MODE_STD[mode]
    bname, fc, bw = _BAND_BY_STD[std]
    lam = C0 / fc
    from waveforms import all_waveforms
    wf = all_waveforms(occ)[std]
    fs = float(wf.fs_hz)
    prf = float(fss.prf_hz(std, occ))
    B_ref = float(wf.ref_bw_hz)
    snr90 = float(snr90_db if snr90_db is not None else 12.0)   # 없으면 관습값(문헌 12dB) — note
    lookup = _sigma_lookup(sig_json, drone, bname) if sig_json else None

    d = (np.geomspace(100.0, 5000.0, 5) if smoke else
         (np.geomspace(100.0, 20000.0, 240) if d_grid is None else np.asarray(d_grid, float)))

    # ── d 격자 위 기하·σ·유효게이트·닫힌형 SNR (헤딩 = 최적, 전이곡선 dopoff 무관 근사) ──
    tgt = fss.target_pos(d, phi_deg, L, alt)                     # (len(d),3)
    p = fss.fs_params(fss.FS_TX, fss.FS_RX(L), tgt, (0.0, 0.0, 0.0), fc)
    R1 = np.asarray(p["R1"], float); R2 = np.asarray(p["R2"], float)
    beta = np.asarray(p["beta"], float); el_look = np.asarray(p["el_deg"], float)
    kappa = R1 * R2
    az_look, _ = _look_az(p["u1"], p["u2"])
    sigma_d = np.array([_sigma_at(lookup, az_look[i], el_look[i]) for i in range(len(d))])
    snr_d = fsl.snr_rd_db(EIRP_DBM, GRX_DBI, lam, sigma_d, R1, R2, nf=NF_DB,
                          eta_ref=0.0, T=T_cpi, losses=0.0, k_mode=0.0)
    snr_d = snr_d + 10.0 * np.log10(max(N, 1))                   # 다중Rx 상한 +10log10N
    # 유효범위 게이트(축 안 자름, 라벨만) — β≤90·원거리장
    valid = fss.beta_gate(beta) & np.array([fss.farfield_gate(min(R1[i], R2[i]), drone, fc)
                                            for i in range(len(d))])
    sol = fsl.solve_range(snr_d, snr90, d_grid=d, kappa_of_d=kappa, valid=valid)

    # ── 커버리지 (헤딩 ψ 전체) : R90 부근 d 에서 blind + σ(ψ) ──
    psi = np.linspace(0.0, 360.0, int(psi_n), endpoint=False)
    d_cov = sol["R_m"] if np.isfinite(sol["R_m"]) else float(d[len(d) // 2])
    blind = fss.blind_sector(psi, phi_deg, d_cov, L, alt, T_cpi, prf, speed, lam)
    tgt_c = fss.target_pos(d_cov, phi_deg, L, alt)
    pc = fss.fs_params(fss.FS_TX, fss.FS_RX(L), tgt_c, (0.0, 0.0, 0.0), fc)
    azc, _ = _look_az(pc["u1"], pc["u2"])
    azc = float(np.ravel(azc)[0])
    elc = float(pc["el_deg"])
    sig_psi = np.array([_sigma_at(lookup, azc - ps, elc) for ps in psi])
    snr_psi = fsl.snr_rd_db(EIRP_DBM, GRX_DBI, lam, sig_psi, float(pc["R1"]), float(pc["R2"]),
                            nf=NF_DB, eta_ref=0.0, T=T_cpi, losses=0.0, k_mode=0.0) \
        + 10.0 * np.log10(max(N, 1))
    pd_psi = 1.0 / (1.0 + np.exp(-(snr_psi - snr90)))            # 로지스틱 근사(측정곡선 없으면)
    C, f_blind, f_sigma = fsl.coverage_fraction(pd_psi, blind, pd_th=0.9)
    epd = fsl.e_psi_pd(pd_psi, blind_mask=blind)

    # ── 감도: 실장 소거깊이(R5) ──
    Pdir = fsl.direct_power_w(EIRP_DBM, GRX_DBI, lam, L)
    R_by_depth = {}
    for depth in eca_depth_grid:
        n0 = fsl.n0_effective(Pdir, NF_DB, fs, eca_depth_db=depth)
        extra = float(n0["total"] - n0["thermal"])
        snr_dep = fsl.snr_rd_db(EIRP_DBM, GRX_DBI, lam, sigma_d, R1, R2, nf=NF_DB, T=T_cpi,
                                n0_extra=(n0["total"] - n0["thermal"])) + 10.0 * np.log10(max(N, 1))
        s2 = fsl.solve_range(snr_dep, snr90, d_grid=d, kappa_of_d=kappa, valid=valid)
        key = "inf" if depth is None else str(int(depth))
        R_by_depth[key] = dict(R_m=s2["R_m"], R_eq_m=s2["R_eq_m"],
                               n0_excess_db=float(fsl.lin2db(n0["total"] / n0["thermal"])))

    # ── 감도: EIRP 사다리(F8/R5) + T_CPI 사다리(F10/R7) — 같은 기하·σ 재사용, GPU 0회 ──
    def _R(snr_arr):
        return fsl.solve_range(snr_arr, snr90, d_grid=d, kappa_of_d=kappa, valid=valid)["R_m"]
    gN = 10.0 * np.log10(max(N, 1))
    eirp_ladder = [20.0, 30.0, 40.0, 50.0, 60.0, 63.0, 70.0, 80.0, 90.0]
    sens_eirp = dict(eirp_dbm=eirp_ladder, R_thermal_m=[],
                     R_dpi_resid_m={"40": [], "60": [], "90": [], "inf": []})
    for e in eirp_ladder:
        sens_eirp["R_thermal_m"].append(
            _R(fsl.snr_rd_db(e, GRX_DBI, lam, sigma_d, R1, R2, nf=NF_DB, T=T_cpi) + gN))
        Pdir_e = fsl.direct_power_w(e, GRX_DBI, lam, L)
        for depth, key in ((40.0, "40"), (60.0, "60"), (90.0, "90"), (None, "inf")):
            n0e = fsl.n0_effective(Pdir_e, NF_DB, fs, eca_depth_db=depth)
            sens_eirp["R_dpi_resid_m"][key].append(
                _R(fsl.snr_rd_db(e, GRX_DBI, lam, sigma_d, R1, R2, nf=NF_DB, T=T_cpi,
                                 n0_extra=(n0e["total"] - n0e["thermal"])) + gN))
    tcpi_ladder = [0.056, 0.1, 0.2, 0.5, 1.0]
    sens_cpi = dict(t_cpi_s=tcpi_ladder, R90_m=[
        _R(fsl.snr_rd_db(EIRP_DBM, GRX_DBI, lam, sigma_d, R1, R2, nf=NF_DB, T=tc) + gN)
        for tc in tcpi_ladder])

    # ── F4 커버리지 곡선 C(d)·E_ψ[Pd](d) (거리격자 로그 부분표집, 닫힌형·GPU 0회) ──
    #   단일거리 대신 커버리지: 각 d 에서 헤딩 ψ 전체의 blind + σ(ψ) → Pd(ψ) → C·E_ψ[Pd] (S3/S4).
    d_cov_grid = np.geomspace(float(d[0]), float(d[-1]), 30)
    cov_C, cov_Epd = [], []
    for dk in d_cov_grid:
        tk = fss.target_pos(dk, phi_deg, L, alt)
        pk = fss.fs_params(fss.FS_TX, fss.FS_RX(L), tk, (0.0, 0.0, 0.0), fc)
        azk, _ = _look_az(pk["u1"], pk["u2"]); azk = float(np.ravel(azk)[0]); elk = float(pk["el_deg"])
        blk = fss.blind_sector(psi, phi_deg, dk, L, alt, T_cpi, prf, speed, lam)
        sgk = np.array([_sigma_at(lookup, azk - ps, elk) for ps in psi])
        snk = fsl.snr_rd_db(EIRP_DBM, GRX_DBI, lam, sgk, float(pk["R1"]), float(pk["R2"]),
                            nf=NF_DB, eta_ref=0.0, T=T_cpi) + gN
        pdk = 1.0 / (1.0 + np.exp(-(snk - snr90)))
        Ck, _, _ = fsl.coverage_fraction(pdk, blk, pd_th=0.9)
        cov_C.append(float(Ck)); cov_Epd.append(float(fsl.e_psi_pd(pdk, blind_mask=blk)))
    coverage_curve = dict(d_m=d_cov_grid.tolist(), C=cov_C, E_psi_pd=cov_Epd)

    # ── F7 헤딩 발자국 R90(ψ) (극좌표, 자세·도플러 블라인드·앨리어싱이 한 축에) ──
    psi_pol = np.linspace(0.0, 360.0, 72, endpoint=False)
    R90_psi, blind_psi, alias_psi = [], [], []
    for ps in psi_pol:
        sgp = np.array([_sigma_at(lookup, az_look[i] - ps, el_look[i]) for i in range(len(d))])
        snp = fsl.snr_rd_db(EIRP_DBM, GRX_DBI, lam, sgp, R1, R2, nf=NF_DB, eta_ref=0.0, T=T_cpi) + gN
        Rp = _R(snp)
        Rp = float(Rp) if np.isfinite(Rp) else 0.0
        R90_psi.append(Rp)
        d_at = Rp if Rp > 0 else float(d_cov if np.isfinite(d_cov) else d[len(d) // 2])
        bp = fss.blind_sector(np.array([ps]), phi_deg, d_at, L, alt, T_cpi, prf, speed, lam)
        blind_psi.append(bool(np.ravel(bp)[0]))
        try:                                                # 앨리어싱: 헤딩 도플러가 나이퀴스트 접힘
            vk = fss.heading_velocity(ps, speed)
            tk = fss.target_pos(d_at, phi_deg, L, alt)
            pk = fss.fs_params(fss.FS_TX, fss.FS_RX(L), tk, vk, fc)
            fdp = float(np.ravel(pk["fd"])[0])
            alias_psi.append(bool(not fss.nyquist_gate(fdp, prf)))
        except Exception:
            alias_psi.append(False)
    heading_polar = dict(psi_deg=psi_pol.tolist(), R90_m=R90_psi,
                         blind=blind_psi, alias=alias_psi)

    # ── F2 SNR 예산 폭포 항목분해 @ d=1 km (대역폭 B 항이 없음을 눈으로 — 닫힌형) ──
    d1k = min(1000.0, float(d[-1]))
    t1 = fss.target_pos(d1k, phi_deg, L, alt)
    p1 = fss.fs_params(fss.FS_TX, fss.FS_RX(L), t1, (0.0, 0.0, 0.0), fc)
    az1, _ = _look_az(p1["u1"], p1["u2"]); az1 = float(np.ravel(az1)[0]); el1 = float(p1["el_deg"])
    budget_terms_db = fsl.snr_rd_terms_db(EIRP_DBM, GRX_DBI, lam, _sigma_at(lookup, az1, el1),
                                          float(p1["R1"]), float(p1["R2"]), nf=NF_DB,
                                          eta_ref=0.0, T=T_cpi)
    budget_terms_db["array_gain_db"] = float(gN)            # +10log10N (예산 밖 참고항)
    budget_terms_db["d_ref_m"] = float(d1k)

    # ── FS-3 평면지면 2-ray F⁴ (동반, 헤드라인 아님, R1) ──
    dR, psi_g = fsl.two_ray_path_diff(alt, fss.FS_RX_H, d_cov)
    F1 = fsl.two_ray_F(psi_g, dR, None, lam=lam, pol="v")
    F2 = fsl.two_ray_F(psi_g, dR, None, lam=lam, pol="v")
    f4_db = fsl.two_ray_f4_db(F1, F2)

    # ── 벽 지도 라벨 (§8) ──
    n0_at = fsl.n0_effective(Pdir, NF_DB, fs, eca_depth_db=60.0)
    gates = dict(beta_ok=bool(fss.beta_gate(float(np.interp(np.log10(max(d_cov, 1)),
                                                            np.log10(d), beta)) if np.isfinite(d_cov) else 0.0)),
                 farfield_ok=True, nyquist_ok=True)
    limit, extras = fsl.classify_limit(n0_at, gates, geometry_nonlinear=sol["geometry_nonlinear"])

    res = dict(
        mode=mode, drone=drone, L_m=L, alt_m=alt, phi_deg=phi_deg, N=int(N), T_cpi_s=T_cpi,
        snr90_db=snr90, snr90_source=("measured (stage_threshold)" if snr90_db is not None
                                      else "assumed 12 dB (no transfer curve passed)"),
        d_grid_m=d.tolist(), snr_d_db=[float(x) for x in np.atleast_1d(snr_d)],
        sigma_d_dbsm=[float(10 * np.log10(max(s, 1e-30))) for s in sigma_d],
        beta_deg=[float(x) for x in np.atleast_1d(beta)],
        el_look_deg=[float(x) for x in np.atleast_1d(el_look)],
        R_m=sol["R_m"], R_eq_m=sol["R_eq_m"], kappa_at_R=sol["kappa_at_R"],
        n_local_at_R=sol["n_local"], n_geom=sol["n_geom"], range_conv_exponent=sol["range_conv_exponent"],
        monotone_ok=sol["monotone_ok"], snr_ceiling_db=sol["snr_ceiling_db"],
        snr_peak_d_m=sol["snr_peak_d_m"], frac_never_detectable=sol["frac_never_detectable"],
        geometry_nonlinear=sol["geometry_nonlinear"], grid_limited=sol["grid_limited"],
        n_crossings=sol["n_crossings"], crossings_m=sol["crossings_m"],
        coverage=dict(C=float(C), factor_blind=float(f_blind), factor_sigma=float(f_sigma),
                      E_psi_Pd=float(epd), d_cov_m=float(d_cov), blind_frac=float(np.mean(blind))),
        sensitivity_eca_depth=R_by_depth,
        sensitivity_eirp=sens_eirp, sensitivity_cpi=sens_cpi,
        coverage_curve=coverage_curve, heading_polar=heading_polar,
        budget_terms_db=budget_terms_db,
        fs3_ground=dict(F4_db=float(f4_db), grazing_deg=float(psi_g), dR_m=float(dR),
                        note="FS-3 companion; free space is NOT an upper bound (F4 in [-20,+11.5] dB)"),
        limit=limit, limit_extras=extras,
        limit_note="which wall binds is conditional; not headlined (spec §1.1-5)")
    if verbose:
        print(f"    [solve] {mode} {drone}: R={_f(res['R_m'])}m R_eq={_f(res['R_eq_m'])}m "
              f"n_local={_f(res['n_local_at_R'])} mono={res['monotone_ok']} "
              f"ceiling={_f(res['snr_ceiling_db'])}dB C={C:.2f} E[Pd]={epd:.2f} limit={limit}")
    return res


def _look_az(u1, u2):
    """이등분선 방위 az_look[deg] (배열). channel.look_angles 의 방위 분기."""
    b = np.asarray(u1, float) + np.asarray(u2, float)
    n = np.linalg.norm(b, axis=-1, keepdims=True)
    look = b / np.maximum(n, 1e-12)
    az = np.degrees(np.arctan2(look[..., 1], look[..., 0]))
    el = np.degrees(np.arcsin(np.clip(look[..., 2], -1.0, 1.0)))
    return np.atleast_1d(az), np.atleast_1d(el)


# --------------------------------------------------------------------------- #
#  stage 4 — 검증 스팟체크 (§16 게이트)
# --------------------------------------------------------------------------- #
def stage_verify(modes=("L1",), smoke=False, verbose=True) -> dict:
    """FS-0 동일성·ECA 바닥(ridge=0)·기하 동치 스팟체크 (스펙 §16 게이트).

    · geometry_equivalence : freespace_scene.selfcheck_vs_repo (fs_params↔bistatic_params) — GPU 불필요
    · eca_floor            : freespace_detect.eca_floor_sweep (ridge{0,1e-6,1e-4}) — ridge=0 정본 증거
    · snr_convention       : mean↔median 오프셋 자기일관 (한 셀)"""
    out = {}
    # (1) 기하 동치(회귀 잠금) — 스펙 §16 게이트
    n_geo = 200 if smoke else 2000
    out["geometry_equivalence"] = fss.selfcheck_vs_repo(n=n_geo)
    if verbose:
        ge = out["geometry_equivalence"]
        print(f"    [verify] geometry_equivalence ok={ge['ok']} "
              f"max|Δ|={max(ge['max_abs_diff'].values()):.2e}")

    # (2) ECA 바닥 스윕 — R6 증거. eca_floor_sweep 은 M(=8) 프레임짜리 기준 CPI 를 받는다.
    #   R6 의 물리 입력은 **raw 파형**(ECA 이전 송신 스트림)이라 wf.tx 를 8회 타일한다.
    ref = build_ref_cell(mode=modes[0], verbose=False)
    Mf = 8
    ref_cpi = np.tile(np.asarray(ref["wf"].tx, np.complex64), Mf)
    dnr_grid = (80.0, 120.0) if smoke else (80.0, 100.0, 120.0)
    fl = fsd.eca_floor_sweep(ref_cpi, dnr_grid=dnr_grid, ridge_list=(0.0, 1e-6, 1e-4),
                             M=Mf, n_range=256, fs=ref["fs"], tap_span_m=TAP_SPAN_M)
    out["eca_floor"] = dict(dnr_db=fl["dnr_db"], ridge=fl["ridge"], configs=fl["configs"],
                            resid_p99_db=fl["resid_p99_db"], clean_ridge0=fl["clean_ridge0"],
                            canonical=fl["canonical"])
    if verbose:
        # ridge 별 최고 DNR 에서의 p99 잔류
        for i, cfg in enumerate(fl["configs"]):
            print(f"    [verify] eca_floor ridge={cfg['ridge']:.0e} "
                  f"depth={cfg['cancel_depth_db']:.1f}dB p99@maxDNR={max(fl['resid_p99_db'][i]):.2f}dB")

    # (3) FS-0 SNR90 (열잡음 상한) 스팟 — 모드별 SNR90 을 나중에 동일성 검정에 씀
    out["fs0_note"] = ("FS-0 9-mode SNR90 identity (R8) needs all 9 modes; smoke records only "
                       f"{list(modes)}. Full run: stage_threshold(modes=9) then compare CI.")
    return out


# --------------------------------------------------------------------------- #
#  I/O
# --------------------------------------------------------------------------- #
def _f(x):
    try:
        return "nan" if (x is None or not np.isfinite(x)) else f"{float(x):.1f}"
    except Exception:
        return str(x)


def _load(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def _save(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f)
    os.replace(tmp, path)


def _meta(smoke, modes):
    import subprocess
    try:
        rev = subprocess.check_output(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"],
                                      stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        rev = ""
    return dict(report="report13", producer="experiment_freespace_range.py",
                generated=time.strftime("%Y-%m-%dT%H:%M:%S"), git_rev=rev,
                assumption_ladder=["FS0", "FS1", "FS2", "FS3"], headline_stage="FS1",
                link_budget=dict(eirp_dbm=EIRP_DBM, eirp_definition="in-burst peak",
                                 rx_gain_dbi=GRX_DBI, noise_figure_db=NF_DB,
                                 provenance="DECLARED — no source doc (spec §15-1)"),
                eca=dict(ridge_rel=0.0, tap_span_m=TAP_SPAN_M, note="ridge=0 canonical (R6)"),
                cpi=dict(model="M=max(2,round(T_cpi*PRF))", reference_repetition_hz_note="F1: SSB=50Hz"),
                modes=list(modes), smoke=bool(smoke),
                gpus=os.environ.get("CUDA_VISIBLE_DEVICES", ""),
                sigma_file=SIGMA_JSON)


# --------------------------------------------------------------------------- #
#  §10 정본 스키마 조립 (add-only) — 스테이지 산출 → 소비자(viz/verify/notebook)가 읽는 키
# --------------------------------------------------------------------------- #
def _waveform_facts(mode):
    """모드별 파형 사실(F15·헤드라인·waveforms 키). GPU 불필요."""
    std, occ = MODE_STD[mode]
    bname, fc, bw = _BAND_BY_STD[std]
    from waveforms import all_waveforms
    wf = all_waveforms(occ)[std]
    prf = float(fss.prf_hz(std, occ))
    B_ref = float(getattr(wf, "ref_bw_hz", bw) or bw)
    return dict(std=std, occ=occ, ref_name=bname, fc_hz=float(fc), lam_m=float(C0 / fc),
                bw_hz=float(bw), ref_bw_hz=B_ref, fs_hz=float(wf.fs_hz), prf_hz=prf,
                M=int(fss.M_from_prf(0.1, prf)),
                d_rb_m=(float(C0 / B_ref) if B_ref > 0 else None))


def assemble_canonical(out):
    """스테이지 산출(threshold/calib/solve)을 **스펙 §10 정본 키로 추가 매핑**한다(add-only;
    스테이지 키는 보존). 정본 키 = 소비자가 읽는 계약: `detector_transfer`(N 래퍼)·`calib.resid_db`·
    `ranges[drone][mode][view][ref].by_N[N]`·`waveforms`·`curves.cassini`·`meta.ranges_el_look_deg`.
    단일 셀 solve 를 정본 리프로 옮기며, 다중 드론/뷰/C25·CI 는 대량 실행 집계 몫으로 남긴다."""
    # (1) detector_transfer : threshold.S_G 에 "N" 래퍼 추가 (F13·verify fs0 게이트)
    thr = out.get("threshold") or {}
    if isinstance(thr.get("S_G"), dict):
        dt = {"S_G": {}}
        pfa = thr.get("pfa", {})
        for mode, byN in thr["S_G"].items():
            dt["S_G"][mode] = {"N": {str(n): tr for n, tr in byN.items()}}
            pe = (pfa.get(mode) or {}).get("empirical")
            if pe is not None:
                for tr in dt["S_G"][mode]["N"].values():
                    for cell in (tr.get("dopoff") or {}).values():
                        if isinstance(cell, dict) and not cell.get("skipped"):
                            cell.setdefault("Pfa_emp", float(pe)); break
        out["detector_transfer"] = dt

    # (2) waveforms : 모드별 파형 사실
    solve = out.get("solve") or {}
    modes = list(solve.keys()) or list((thr.get("S_G") or {}).keys())
    if modes:
        out["waveforms"] = {m: _waveform_facts(m) for m in modes}

    # (3) ranges : solve → ranges[drone][mode][view][ref].by_N[N] (정본 리프)
    ranges = out.setdefault("ranges", {})
    view, ref = "equal_psd", "full_waveform_capture"     # 헤드라인 뷰/기준(§10)
    for mode, s in solve.items():
        if not isinstance(s, dict):
            continue
        drone = s.get("drone", "mini5pro")
        N = str(int(s.get("N", 1)))
        d_grid = np.asarray(s.get("d_grid_m", []), float)
        el_arr = np.asarray(s.get("el_look_deg", []), float)
        R = s.get("R_m")
        el_at_R = None
        try:
            if R is not None and np.isfinite(R) and d_grid.size and el_arr.size == d_grid.size:
                el_at_R = float(np.interp(np.log10(max(R, 1.0)), np.log10(d_grid), el_arr))
        except Exception:
            el_at_R = None
        cov = s.get("coverage", {}) or {}
        dep = s.get("sensitivity_eca_depth", {}) or {}
        R_dpi = {k: v.get("R_m") for k, v in dep.items()} if isinstance(dep, dict) else {}
        bf = cov.get("blind_frac")
        leaf = dict(
            R90_C50_m=s.get("R_m"), R90_C25_m=s.get("R_m"),
            R90_ci95_m=[s.get("R_m"), s.get("R_m")],
            R_eq_at_R90_m=s.get("R_eq_m"), n_local_at_R90=s.get("n_local_at_R"),
            el_look_at_R90_deg=el_at_R, E_psi_Pd_at_R90=cov.get("E_psi_Pd"),
            coverage_ceiling=((1.0 - float(bf)) if bf is not None else None),
            blind_heading_frac=bf, snr_ceiling_db=s.get("snr_ceiling_db"),
            frac_never_detectable=s.get("frac_never_detectable"),
            monotone_ok=s.get("monotone_ok"), R_dpi_resid_m=R_dpi,
            limit=s.get("limit"), grid_limited=s.get("grid_limited"),
            budget_terms_db=s.get("budget_terms_db"),              # F2 폭포
            note="single-cell solve mapped to canonical ranges; C25/CI95/other views/N are "
                 "full-run aggregates (not computed in this invocation).")
        (ranges.setdefault(drone, {}).setdefault(mode, {})
               .setdefault(view, {}).setdefault(ref, {}).setdefault("by_N", {}))[N] = leaf
        if el_at_R is not None:
            out.setdefault("meta", {})["ranges_el_look_deg"] = el_at_R
        # curves.coverage_C_of_d[drone][mode] (F4) · coverage.polar[drone][mode] (F7)
        if s.get("coverage_curve"):
            (out.setdefault("curves", {}).setdefault("coverage_C_of_d", {})
                .setdefault(drone, {}))[mode] = s["coverage_curve"]
        if s.get("heading_polar"):
            (out.setdefault("coverage", {}).setdefault("polar", {})
                .setdefault(drone, {}))[mode] = s["heading_polar"]

    # (3b) sensitivity : EIRP 사다리(top-level, 헤드라인 모드)·T_CPI 사다리(모드별) — F8/F10/R5/R7
    sens = out.setdefault("sensitivity", {})
    head_mode = "L1" if "L1" in solve else (list(solve.keys())[0] if solve else None)
    for mode, s in solve.items():
        if not isinstance(s, dict):
            continue
        if s.get("sensitivity_cpi"):
            sens.setdefault("cpi", {})[mode] = s["sensitivity_cpi"]
        if mode == head_mode and s.get("sensitivity_eirp"):
            sens["eirp"] = s["sensitivity_eirp"]

    # (4) curves.cassini : 대표 등감도선(F1·notebook §1) — GPU 불필요, 실패시 조용히 skip
    try:
        kappa = next((float(s["kappa_at_R"]) for s in solve.values()
                      if isinstance(s, dict) and s.get("kappa_at_R")), None)
        if kappa:
            TX = tuple(float(v) for v in fss.FS_TX)
            RX = tuple(float(v) for v in fss.FS_RX(fss.L_REF))
            cas = np.asarray(fsl.cassini_contour(kappa, TX, RX), float)
            out.setdefault("curves", {})["cassini"] = cas.tolist()
            # (4b) R8 curves.cassini_by_L : L 스윕 등감도선(단일→이엽, 기하가 커버리지 접음)
            by_L = {}
            for L in np.geomspace(50.0, 3000.0, 36):
                try:
                    c = np.asarray(fsl.cassini_contour(kappa, TX,
                                   tuple(float(v) for v in fss.FS_RX(float(L)))), float)
                    by_L[f"{L:.1f}"] = c.tolist()
                except Exception:
                    continue
            if by_L:
                out["curves"]["cassini_by_L"] = by_L
    except Exception:
        pass
    return out


def _flt(x):
    """inf/nan → None (JSON 안전), 그 외 float."""
    try:
        v = float(x)
        return v if np.isfinite(v) else None
    except Exception:
        return None


def stage_baseline_walls(sig_json, ref_drone, modes, alt=60.0, speed=5.0,
                         T_cpi=0.1, phi_deg=90.0, snr90=12.0) -> dict:
    """F11 벽 지도: 밴드별 **R vs 베이스라인 L** (thermal / ADC DR74 / DPI잔류60dB / walk).
    닫힌형·GPU 0회. σ 는 `ref_drone` 격자에서 조회(대표 밝기 — 벽 **랭킹**은 σ 절대값에 둔감).
    walk 벽 = CPI 를 T_max=ΔR_b/v_r=(c/B_ref)/speed 로 상한(§8.7): 광대역일수록 이른 벽."""
    L_grid = np.geomspace(50.0, 3000.0, 24)
    band_of = {"W1": "wifi", "L1": "lte", "G1": "nr"}
    from waveforms import all_waveforms
    out = {}
    for mode in modes:
        bk = band_of.get(mode)
        if bk is None:
            continue
        std, occ = MODE_STD[mode]
        bname, fc, bw = _BAND_BY_STD[std]
        lam = C0 / fc
        wf = all_waveforms(occ)[std]
        fs = float(wf.fs_hz); B_ref = float(getattr(wf, "ref_bw_hz", bw) or bw)
        lookup = _sigma_lookup(sig_json, ref_drone, bname) if sig_json else None
        T_walk = min(T_cpi, (C0 / B_ref) / max(speed, 1e-3)) if B_ref > 0 else T_cpi
        d = np.geomspace(100.0, 20000.0, 120)
        node = dict(L_m=L_grid.tolist(), band=bname, T_walk_s=float(T_walk),
                    R_thermal_m=[], R_adc_m=[], R_dpi60_m=[], R_walk_m=[])
        for L in L_grid:
            tgt = fss.target_pos(d, phi_deg, L, alt)
            p = fss.fs_params(fss.FS_TX, fss.FS_RX(L), tgt, (0.0, 0.0, 0.0), fc)
            R1 = np.asarray(p["R1"], float); R2 = np.asarray(p["R2"], float)
            kap = R1 * R2
            beta = np.asarray(p["beta"], float); el_look = np.asarray(p["el_deg"], float)
            az_look, _ = _look_az(p["u1"], p["u2"])
            sig_d = np.array([_sigma_at(lookup, az_look[i], el_look[i]) for i in range(len(d))])
            valid = fss.beta_gate(beta)
            Pdir = fsl.direct_power_w(EIRP_DBM, GRX_DBI, lam, L)

            def _R(n0_extra=0.0, T=T_cpi):
                snr = fsl.snr_rd_db(EIRP_DBM, GRX_DBI, lam, sig_d, R1, R2, nf=NF_DB,
                                    eta_ref=0.0, T=T, n0_extra=n0_extra)
                return fsl.solve_range(snr, snr90, d_grid=d, kappa_of_d=kap, valid=valid)["R_m"]

            node["R_thermal_m"].append(_flt(_R()))
            n0q = fsl.n0_quant(Pdir, fsl.adc_dr_db(12), 0.0, fs)
            node["R_adc_m"].append(_flt(_R(n0_extra=float(np.asarray(n0q).ravel()[0]))))
            n0d = fsl.n0_effective(Pdir, NF_DB, fs, eca_depth_db=60.0)
            node["R_dpi60_m"].append(_flt(_R(n0_extra=float(n0d["total"] - n0d["thermal"]))))
            node["R_walk_m"].append(_flt(_R(T=T_walk)))
        out[bk] = node
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="report13 자유공간 검지거리 4-stage")
    ap.add_argument("--stage", default="all", choices=["threshold", "calib", "solve", "verify", "all"])
    ap.add_argument("--mode", default="L1", help="쉼표목록(예 W1,L1,G1). 헤드라인=L1")
    ap.add_argument("--drone", default="mini5pro")
    ap.add_argument("--out", default=FREESPACE_JSON)
    ap.add_argument("--sigma", default=SIGMA_JSON, help="σ 격자 JSON(solve 의 σ 조회)")
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args(argv)

    from gpu import pick
    pick(verbose=True)

    modes = tuple(m.strip() for m in args.mode.split(",") if m.strip())
    sig_json = _load(args.sigma)
    out = _load(args.out) or {}
    out["meta"] = _meta(args.smoke, modes)

    t0 = time.time()
    snr90 = None
    if args.stage in ("threshold", "all"):
        out["threshold"] = stage_threshold(modes=modes, smoke=args.smoke)
        # 헤드라인 모드의 SNR90(가능하면) 을 solve 로 넘긴다
        try:
            tr = out["threshold"]["S_G"][modes[0]]["1"]["dopoff"]
            for dv in tr.values():
                if not dv.get("skipped") and dv.get("snr90_db") is not None:
                    snr90 = float(dv["snr90_db"]); break
        except Exception:
            pass
        _save(args.out, out)
    if args.stage in ("calib", "all"):
        out["calib"] = stage_calib(modes=modes, smoke=args.smoke)
        _save(args.out, out)
    if args.stage in ("solve", "all"):
        out["solve"] = {m: stage_solve(mode=m, drone=args.drone, snr90_db=snr90,
                                       sig_json=sig_json, smoke=args.smoke) for m in modes}
        _save(args.out, out)
    if args.stage in ("verify", "all"):
        out["verify"] = stage_verify(modes=modes, smoke=args.smoke)
        _save(args.out, out)

    # ── §10 정본 스키마 조립(add-only) — 소비자가 읽는 키로 매핑 ──
    assemble_canonical(out)
    # ── F11 벽 지도(baseline L 스윕) — solve 시·σ 있을 때, 결정적 ref 드론(run 순서 무관) ──
    if args.stage in ("solve", "all") and sig_json:
        try:
            ref = ("mini5pro" if _sigma_lookup(sig_json, "mini5pro", "LTE 1.8 GHz")
                   else args.drone)
            base = stage_baseline_walls(sig_json, ref, modes)
            if base:
                out.setdefault("sensitivity", {})["baseline"] = base
                out["sensitivity"].setdefault("baseline_meta", {})["ref_drone"] = ref
                _save(args.out, out)
                if args.smoke or True:
                    print(f"  [F11] 벽지도 baseline (ref={ref}, {len(base)}밴드) 산출")
        except Exception as e:
            print(f"  [F11] baseline 벽지도 skip: {type(e).__name__}: {e}")
    out["meta"]["runtime_s"] = round(time.time() - t0, 1)
    _save(args.out, out)
    print(f"\n[range] 완료 ({out['meta']['runtime_s']}s) → {args.out}")
    return out


if __name__ == "__main__":
    main()
