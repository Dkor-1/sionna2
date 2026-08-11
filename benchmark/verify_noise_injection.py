# -*- coding: utf-8 -*-
"""
verify_noise_injection.py — 잡음 주입 배선의 게이트 (원장: outputs/verify_noise_injection.json)

무엇을 지키나
--------------
배선은 **opt-in** 이다. 기본값으로 부르면 2026-08-10 이전과 **비트동일**이어야 하고,
그것을 게이트로 증명한다. 그 위에 «넣은 잡음이 진짜 그 잡음인가» 와
«세 층위(표본당 SNR · 정합필터 이득 · STFT 조각 이득)가 맞나» 를 잰다.

 NI1  noisy_series(seed=int)  재현성 + add_noise 와 **비트동일**(구현이 하나뿐임을 증명)
 NI2  add_noise(ref="total")  == 2026-08-10 이전 구현                     **비트동일**
 NI3  md_mapstyle.draw(mode="peak")  == 변경 전 구현 (픽셀)               **비트동일**
 NI4  주입한 잡음의 통계 — 되잰 SNR · 실수/허수 대칭 · 원형성(circularity)
 NI5  한 그림 안 색역 공통성 (설계서 G15) — 그림 원장이 스칼라 하나를 선언하나
 NI6  사다리 ↔ 역함수 왕복 (모노 −40 dB/dec · 한 다리 −20 dB/dec)
 NI7  평면파 방위평균 σ 의 거리 무관성 — 스윕의 캐시가 비트동일한 근거
 NI8  ⭐**STFT 조각 이득(rung 4)의 실측** — 설계서가 «우리 유추» 라고 자백한 그 수
 NI9  ⭐시계열에 더한 잡음의 맵 바닥이 **지수분포(χ²₂)** 인가 (맵에 더하면 가우시안이 된다)

실행:
    cd sionna2 && PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/verify_noise_injection.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                    # noqa: E402
import numpy as np                                                 # noqa: E402
from scipy import stats                                            # noqa: E402
from scipy.signal import spectrogram as _spec                      # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(_ROOT, "src"))

import md_mapstyle as ms                                           # noqa: E402
import microdoppler_nearfield as nf                                # noqa: E402

OUT = os.path.join(_ROOT, "outputs", "verify_noise_injection.json")
FIG_LEDGER = os.path.join(_ROOT, "outputs", "md_noise_range_fig.json")


# --------------------------------------------------------------------------- #
#  얼린 옛 구현 — 비교 대상은 «기억» 이 아니라 코드여야 한다
# --------------------------------------------------------------------------- #
def _add_noise_v1(E, snr_db, rng):
    """2026-08-10 이전 `microdoppler_nearfield.add_noise()` 그대로."""
    p_sig = float(np.mean(np.abs(E) ** 2))
    p_n = p_sig / (10.0 ** (float(snr_db) / 10.0))
    s = np.sqrt(p_n / 2.0)
    n = rng.normal(0.0, s, size=E.shape) + 1j * rng.normal(0.0, s, size=E.shape)
    return E + n, float(np.sqrt(p_n))


def _draw_v1(ax, t, f, S, f_tip, *, t_scale=1e3, ref=None):
    """2026-08-11 이전 `md_mapstyle.draw()` 그대로."""
    ref = S.max() if ref is None else ref
    m = ax.pcolormesh(t * t_scale, f, 20 * np.log10(S / (ref + 1e-30) + 1e-12),
                      cmap=ms.CMAP, vmin=ms.VMIN, vmax=ms.VMAX, shading=ms.SHADING,
                      rasterized=True)
    for s in (+1, -1):
        ax.axhline(s * f_tip, color="w", ls="--", lw=1.0, alpha=0.8)
    ax.set_ylim(-ms.YLIM_FTIP * f_tip, ms.YLIM_FTIP * f_tip)
    return m


def _series(n=4096, dc_ac_db=17.3, f_ac=0.11, seed=3):
    """DC(동체) + AC(블레이드) 두 성분짜리 시험 신호. dc_ac_db 를 원하는 값으로 맞춘다."""
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    ac = np.exp(2j * np.pi * f_ac * t) + 0.3 * np.exp(-2j * np.pi * 0.07 * t)
    ac = ac / np.std(ac)
    dc = 10.0 ** (float(dc_ac_db) / 20.0)
    return dc + ac + 0.0 * rng.normal(size=n)


# --------------------------------------------------------------------------- #
def gate_ni1(a):
    E = _series()
    e1, p1 = nf.noisy_series(E, -3.0, a.seed, ref="total", n_real=4)
    e2, p2 = nf.noisy_series(E, -3.0, a.seed, ref="total", n_real=4)
    r = np.random.default_rng(a.seed)
    ref = np.asarray([nf.add_noise(E, -3.0, r, ref="total")[0] for _ in range(4)])
    e3, _ = nf.noisy_series(E, -3.0, a.seed + 1, ref="total", n_real=4)
    # 실현을 늘려도 앞쪽 실현이 그대로여야 한다(같은 스트림에서 이어 뽑는다)
    e4, _ = nf.noisy_series(E, -3.0, a.seed, ref="total", n_real=7)
    ok = (np.array_equal(e1, e2) and np.array_equal(e1, ref)
          and not np.array_equal(e1, e3) and np.array_equal(e1, e4[:4]))
    return dict(id="NI1", what="noisy_series(seed) is reproducible and IS add_noise (one impl)",
                same_seed_bitwise=bool(np.array_equal(e1, e2)),
                equals_add_noise_stream_bitwise=bool(np.array_equal(e1, ref)),
                different_seed_differs=bool(not np.array_equal(e1, e3)),
                prefix_stable_when_n_real_grows=bool(np.array_equal(e1, e4[:4])),
                seed_recorded=p1["seed"], reproducible_flag=p1["reproducible"],
                rng_object_records_no_seed=bool(
                    nf.noisy_series(E, 0.0, np.random.default_rng(1))[1]["seed"] is None),
                passed=bool(ok))


def gate_ni2(a):
    E = _series()
    e_old, s_old = _add_noise_v1(E, -5.0, np.random.default_rng(a.seed))
    e_new, s_new = nf.add_noise(E, -5.0, np.random.default_rng(a.seed))     # 기본 ref="total"
    ok = np.array_equal(e_old, e_new) and s_old == s_new
    return dict(id="NI2", what="add_noise(ref='total') default path == pre-2026-08-10 code",
                bitwise_identical=bool(ok), sigma_old=s_old, sigma_new=s_new, passed=bool(ok))


def gate_ni3(a):
    """맵 표시 규약의 기본 경로가 안 변했나 — 픽셀 배열을 비교한다."""
    rng = np.random.default_rng(a.seed)
    E = _series(n=2048) + rng.normal(0, 0.3, 2048) + 1j * rng.normal(0, 0.3, 2048)
    f, t, S, nper = ms.flash_spec(E, 20000.0, 126.667)
    fig = plt.figure()
    m_old = _draw_v1(fig.add_subplot(121), t, f, S, 1229.0)
    m_new = ms.draw(fig.add_subplot(122), t, f, S, 1229.0)                  # 기본 mode="peak"
    A, B = np.asarray(m_old.get_array()), np.asarray(m_new.get_array())
    same_scale = (m_old.get_clim() == m_new.get_clim())
    # ref 를 명시로 준 경로도 확인(공통 눈금 판에서 쓰는 길)
    m_o2 = _draw_v1(fig.add_subplot(223), t, f, S, 1229.0, ref=3.0)
    m_n2 = ms.draw(fig.add_subplot(224), t, f, S, 1229.0, ref=3.0)
    ok = (np.array_equal(A, B) and same_scale
          and np.array_equal(np.asarray(m_o2.get_array()), np.asarray(m_n2.get_array())))
    plt.close(fig)
    return dict(id="NI3", what="md_mapstyle.draw(mode='peak') pixels == pre-change implementation",
                n_pixels=int(A.size), bitwise_identical=bool(np.array_equal(A, B)),
                clim_identical=bool(same_scale),
                explicit_ref_path_identical=bool(
                    np.array_equal(np.asarray(m_o2.get_array()), np.asarray(m_n2.get_array()))),
                passed=bool(ok))


def gate_ni4(a):
    """넣은 잡음이 진짜 그 잡음인가 — 되잰 SNR · 실/허 대칭 · 원형성."""
    rows = []
    E = _series(n=262144, dc_ac_db=17.3)
    for ref in ("total", "ac"):
        for snr in (10.0, 0.0, -10.0):
            En, prov = nf.noisy_series(E, snr, a.seed, ref=ref, n_real=1)
            n = En[0] - E
            p_sig = (float(np.mean(np.abs(E - np.mean(E)) ** 2)) if ref == "ac"
                     else float(np.mean(np.abs(E) ** 2)))
            meas = 10.0 * np.log10(p_sig / float(np.mean(np.abs(n) ** 2)))
            rows.append(dict(ref=ref, requested_db=snr, measured_db=round(float(meas), 4),
                             err_db=round(float(meas - snr), 4),
                             re_im_var_ratio=round(float(np.var(n.real) / np.var(n.imag)), 5),
                             circularity=round(float(abs(np.mean(n ** 2)) /
                                                     np.mean(np.abs(n) ** 2)), 5)))
    worst = max(abs(r["err_db"]) for r in rows)
    worst_c = max(r["circularity"] for r in rows)
    worst_ri = max(abs(r["re_im_var_ratio"] - 1.0) for r in rows)
    ok = worst <= 0.05 and worst_c <= 0.02 and worst_ri <= 0.02
    return dict(id="NI4", what="injected noise: measured SNR, real/imag symmetry, circularity",
                rows=rows, worst_snr_err_db=worst, worst_circularity=worst_c,
                worst_re_im_ratio_dev=worst_ri,
                tol=dict(snr_db=0.05, circularity=0.02, re_im=0.02), passed=bool(ok))


def gate_ni5(a):
    """한 그림 안 색역 공통성(G15) — 그림 원장이 **스칼라 하나**를 선언해야 한다."""
    if not os.path.exists(FIG_LEDGER):
        return dict(id="NI5", what="one colour scale for every panel of a figure",
                    passed=False, why=f"{os.path.relpath(FIG_LEDGER, _ROOT)} 이 아직 없다 "
                                      "(benchmark/build_md_noise_range_fig.py 를 먼저 돌려라)")
    with open(FIG_LEDGER) as f:
        d = json.load(f)
    col = d["_meta"]["colour"]
    declared_one = isinstance(col.get("noise_rms"), (int, float))
    # mode="over_noise" 는 기준을 반드시 요구한다(빼먹을 수 없게 되어 있나)
    try:
        ms.draw(plt.figure().add_subplot(111), np.arange(3), np.arange(3),
                np.ones((3, 3)), 100.0, mode="over_noise")
        forces = False
    except ValueError:
        forces = True
    plt.close("all")
    ok = bool(declared_one and forces and col["mode"] == "over_noise"
              and col["vmin_db"] < col["vmax_db"])
    return dict(id="NI5", what="one colour scale for every panel of a figure (design gate G15)",
                figure=d["_meta"]["figure"], mode=col["mode"],
                noise_rms=col.get("noise_rms"), vmin_db=col["vmin_db"], vmax_db=col["vmax_db"],
                n_panels=len(d["panels"]),
                single_scalar_declared=declared_one,
                draw_refuses_over_noise_without_reference=forces, passed=ok)


def gate_ni6(a):
    """사다리 ↔ 역함수 왕복 + 기울기."""
    sig = 10.0 ** (-18.879 / 10.0)
    kw = dict(prf=20000.0, capture="full_waveform", dc_ac_db=17.26, nperseg=70, window="hann")
    rows = []
    for rung in ("snr_slow_db", "snr_slow_ac_db", "snr_map_ac_db"):
        for R in (3.0, 27.3, 100.0):
            v = float(nf.snr_ladder(sig, R, 3.5e9, **kw)[rung])
            Rb = nf.range_for_snr_db(v, sig, 3.5e9, rung=rung, **kw)
            rows.append(dict(rung=rung, R_m=R, snr_db=round(v, 6),
                             R_roundtrip_m=round(Rb, 9), rel_err=abs(Rb - R) / R))
    # 한 다리만 움직이는 경우(-20 dB/decade)
    v = float(nf.snr_ladder(sig, 30.0, 3.5e9, rx_range_m=10.0, **kw)["snr_slow_ac_db"])
    Rb = nf.range_for_snr_db(v, sig, 3.5e9, rung="snr_slow_ac_db", legs="one",
                             r_fixed_m=30.0, **kw)
    rows.append(dict(rung="snr_slow_ac_db(one leg, R_t=30 m)", R_m=10.0, snr_db=round(v, 6),
                     R_roundtrip_m=round(Rb, 9), rel_err=abs(Rb - 10.0) / 10.0))
    worst = max(r["rel_err"] for r in rows)
    return dict(id="NI6", what="snr_ladder <-> range_for_snr_db roundtrip (both geometries)",
                rows=rows, worst_rel_err=worst, tol_rel=1e-9, passed=bool(worst <= 1e-9))


def gate_ni7(a):
    """평면파 σ 는 거리에 무관한가 — 스윕이 그 값을 캐시하는 근거."""
    from drones import DRONES
    tabs = []
    for R in (1.0, 10.0, 1000.0):
        _, tab, _ = nf.phase_table(DRONES["mini5pro"], 3.5e9, R, 40.0, 15.0,
                                   wavefront="plane", n_phase=8)
        tabs.append(np.asarray(tab))
    ok = all(np.array_equal(tabs[0], t) for t in tabs[1:])
    # 대조군: 구면파는 거리에 따라 **달라야** 한다(캐시가 그쪽에 잘못 걸리면 잡힌다)
    sph = []
    for R in (10.0, 1000.0):
        _, tab, _ = nf.phase_table(DRONES["mini5pro"], 3.5e9, R, 40.0, 15.0,
                                   wavefront="spherical", n_phase=8)
        sph.append(np.asarray(tab))
    differs = not np.array_equal(sph[0], sph[1])
    return dict(id="NI7", what="plane-wave phase table is range invariant (bitwise) but the "
                               "spherical one is not - justifies caching the plane sigma",
                plane_bitwise_identical=bool(ok), spherical_differs=bool(differs),
                passed=bool(ok and differs))


def gate_ni8(a):
    """⭐ **rung 4 (STFT 한 조각의 이득) 를 실측한다.**

    설계서 §1-8 이 «1차 문헌 근거가 없는 우리 유추» 라고 자백한 수다. 순수 톤 + 잡음으로
    직접 재면 예측 `10log10(nperseg) + L_win` 이 맞는지 **끝에서 끝까지** 확인된다.
    (드론 신호로 재면 블레이드선이 톤이 아니라 플래시라 언제나 예측보다 낮게 나온다 —
     그 차이는 «에너지가 한 빈에 안 모인다» 는 뜻이지 사다리가 틀린 게 아니다.)"""
    prf, f_flash, n = 20000.0, 126.667, 6144
    periods = ms.auto_periods(prf, f_flash)
    t = np.arange(n) / prf
    rows = []
    for snr_ac in (10.0, 0.0, -10.0):
        tone = np.exp(2j * np.pi * 600.0 * t)                    # 단위전력 AC 톤
        En, prov = nf.noisy_series(tone, snr_ac, a.seed, ref="ac", n_real=1)
        x = En[0] / prov["sigma_n"]                              # 잡음 = 단위분산
        f, tt, S, nper = ms.flash_spec(x, prf, f_flash, periods)
        rng = np.random.default_rng(a.seed + 99)
        n0 = rng.normal(0, np.sqrt(0.5), n) + 1j * rng.normal(0, np.sqrt(0.5), n)
        _, _, SN, _ = ms.flash_spec(n0, prf, f_flash, periods)
        floor = ms.noise_rms_from(SN)
        #  ⭐ 편향 없는 추정: 잡음 몫을 빼고 시간평균으로 잰다(`line_level_over_noise_db`).
        #  ⚠ 같이 기록하는 raw max 는 **낙관 편향**을 보이려고 남긴다 — 잡음만 있는 맵의
        #    최대가 이미 11 dB 라, max 로 재면 저 SNR 에서 사다리를 5 dB 넘게 «이긴다».
        meas = ms.line_level_over_noise_db(S, floor)
        raw_max = float(20 * np.log10(S.max() / floor))
        noise_only_max = float(20 * np.log10(SN.max() / floor))
        pred = snr_ac + 10 * np.log10(nper) + nf.window_coh_loss_db("hann")
        rows.append(dict(snr_slow_ac_db=snr_ac, nperseg=int(nper),
                         predicted_map_line_db=round(float(pred), 4),
                         measured_line_db=round(meas, 4),
                         err_db=round(float(meas - pred), 4),
                         raw_max_db=round(raw_max, 4),
                         raw_max_bias_db=round(float(raw_max - pred), 4),
                         noise_only_map_max_db=round(noise_only_max, 4)))
    worst = max(abs(r["err_db"]) for r in rows)
    return dict(id="NI8", what="rung 4 (one STFT frame coherent gain) measured end to end on a "
                               "pure tone: 10log10(nperseg) + Hann loss",
                rows=rows, worst_err_db=worst, tol_db=0.6,
                estimator="time-averaged bin power minus the noise share (md_mapstyle."
                          "line_level_over_noise_db); the raw max is biased by up to +5.6 dB "
                          "at low SNR because a noise-only map already peaks ~11 dB over its rms",
                note="this is the rung the design doc flags as OUR extrapolation of Braun eq "
                     "(3.37); it is now measured, not assumed",
                passed=bool(worst <= 0.6))


def gate_ni9(a):
    """⭐ 시계열에 더한 잡음의 맵 **전력** 분포가 지수분포(χ²₂)인가.

    맵에 실수 가우시안을 직접 더하면 이 분포가 가우시안이 되고 CFAR 문턱
    η = −σ² ln p_FA 가 성립하지 않는다. 그래서 «시계열에 더하고 STFT» 가 규약이다.
    ⚠ 겹친 프레임(hop 2)은 서로 상관되어 KS 검정 전제가 깨지므로 **겹침 없는** STFT 로 잰다."""
    n, prf = 262144, 20000.0
    rng = np.random.default_rng(a.seed)
    z = rng.normal(0, np.sqrt(0.5), n) + 1j * rng.normal(0, np.sqrt(0.5), n)
    nper = 64
    _, _, S = _spec(z, fs=prf, nperseg=nper, noverlap=0, nfft=nper, detrend=False,
                    window="boxcar", return_onesided=False, scaling="spectrum",
                    mode="magnitude")
    P = (np.asarray(S) ** 2).ravel()
    P = P / P.mean()
    ks = stats.kstest(P, "expon")
    # 대조군: 맵에 직접 더한 잡음(설계서가 금지한 방식)은 지수분포가 아니다
    bad = np.abs(np.asarray(S) + rng.normal(0, np.asarray(S).std(), np.asarray(S).shape)) ** 2
    bad = (bad / bad.mean()).ravel()
    ks_bad = stats.kstest(bad, "expon")
    ok = bool(ks.pvalue > 0.01 and ks_bad.pvalue < 0.01)
    return dict(id="NI9", what="map power floor from time-domain noise is exponential (chi2_2); "
                               "adding noise to the map instead is not",
                n_bins=int(P.size), ks_stat=float(ks.statistic), ks_p=float(ks.pvalue),
                mean_over_median_db=round(float(10 * np.log10(P.mean() / np.median(P))), 3),
                theory_mean_over_median_db=round(float(10 * np.log10(1 / np.log(2))), 3),
                control_map_noise_ks_p=float(ks_bad.pvalue),
                passed=ok)


SWEEP_NEW = os.path.join(_ROOT, "outputs", "md_range_sweep_mf.json")
SWEEP_OLD = os.path.join(_ROOT, "outputs", "md_range_sweep.json")

#: 결정론(잡음과 무관) 부분 — 새 스윕에서도 **한 자리도 안 변해야** 하는 값들
_DET_KEYS = ("sigma_eq_plane_dbsm", "sigma_eq_sph_dbsm", "d_sigma_db",
             "d_sigma_aspect_mean_db", "sigma_eq_aspect_mean_sph_dbsm",
             "sigma_eq_aspect_mean_plane_dbsm")
_DET_ARM_KEYS = ("dc_ac_db", "fd_edge_hz", "flash_contrast_db", "harmonic_frac",
                 "ac_energy", "spec_peak_over_floor_db", "ac_corr_vs_ref", "spec_corr_vs_ref")


def gate_ni10(a):
    """⭐ 새 스윕의 **결정론 부분**이 옛 원장과 같은가 (평면 σ 캐시·거리격자 확장의 회귀 게이트).

    ⚠ 잡음 팔(A1/A3)은 **비교하지 않는다** — 옛 원장의 시드가 `hash()` 라 재현 불가능이라
      애초에 비교 대상이 아니다. 그것 자체가 이번 라운드가 고친 결함이고, 여기서는
      «잡음과 무관한 값은 하나도 안 움직였다» 만 증명한다."""
    if not (os.path.exists(SWEEP_NEW) and os.path.exists(SWEEP_OLD)):
        return dict(id="NI10", what="deterministic part of the sweep is unchanged",
                    passed=False, why="md_range_sweep_mf.json 이 아직 없다")
    with open(SWEEP_NEW) as f:
        new = json.load(f)
    with open(SWEEP_OLD) as f:
        old = json.load(f)
    idx = {(c["drone"], c["band"]): c for c in old["cells"]}
    worst, n_cmp, offenders = 0.0, 0, []
    for c in new["cells"]:
        oc = idx.get((c["drone"], c["band"]))
        if oc is None:
            continue
        orow = {float(r["R_m"]): r for r in oc["rows"]}
        for r in c["rows"]:
            o = orow.get(float(r["R_m"]))
            if o is None:
                continue
            for k in _DET_KEYS:
                if k in r and k in o:
                    d = abs(float(r[k]) - float(o[k])); n_cmp += 1
                    if d > worst:
                        worst = d
                    if d > 1e-9:
                        offenders.append(dict(cell=c["drone"], R_m=r["R_m"], key=k,
                                              new=r[k], old=o[k]))
            for arm in ("A0_reference", "A2_nearfield"):
                for k in _DET_ARM_KEYS:
                    a_new = r["arms"].get(arm, {}).get(k)
                    a_old = o["arms"].get(arm, {}).get(k)
                    if a_new is None or a_old is None:
                        continue
                    d = abs(float(a_new) - float(a_old)); n_cmp += 1
                    if d > worst:
                        worst = d
                    if d > 1e-9:
                        offenders.append(dict(cell=c["drone"], R_m=r["R_m"],
                                              arm=arm, key=k, new=a_new, old=a_old))
    return dict(id="NI10", what="deterministic (noise-free) values are bit-stable vs the "
                                "2026-07-28 ledger; noise arms are excluded because the old "
                                "seed was python hash() and is not reproducible",
                n_compared=n_cmp, worst_abs_diff=worst, tol=1e-9,
                offenders=offenders[:10], passed=bool(n_cmp > 0 and worst <= 1e-9))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20260811)
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()

    t0 = time.time()
    gates = [gate_ni1(a), gate_ni2(a), gate_ni3(a), gate_ni4(a), gate_ni5(a),
             gate_ni6(a), gate_ni7(a), gate_ni8(a), gate_ni9(a), gate_ni10(a)]
    n_pass = sum(1 for g in gates if g["passed"])
    doc = dict(
        _meta=dict(
            title="noise injection wiring - regression + statistics + ladder gates",
            generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
            script="benchmark/verify_noise_injection.py",
            convention=nf.SNR_CONVENTION, canonical=nf.CANONICAL_SNR_KEY,
            principle_ko="복소 가우시안을 슬로타임 시계열에 더하고 그 다음 STFT 한다. "
                         "맵·전력·dB 이미지에는 더하지 않는다(NI9 가 그 이유를 잰다).",
            entry_point="src/microdoppler_nearfield.py::noisy_series",
            opt_in_ko="기본값 경로는 전부 이전과 비트동일이어야 한다 - NI1/NI2/NI3 이 그것을 건다",
            gpu_used=False, runtime_s=round(time.time() - t0, 2)),
        summary=dict(n_gates=len(gates), n_pass=n_pass, all_pass=bool(n_pass == len(gates))),
        gates=gates)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    tmp = a.out + ".tmp"
    with open(tmp, "w") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False, default=float)
    os.replace(tmp, a.out)
    for g in gates:
        print(f"  [{'PASS' if g['passed'] else 'FAIL'}] {g['id']}  {g['what'][:78]}")
    print(f"\n{n_pass}/{len(gates)} pass  → {os.path.relpath(a.out, _ROOT)} "
          f"({time.time() - t0:.1f} s)")
    return 0 if n_pass == len(gates) else 1


if __name__ == "__main__":
    sys.exit(main())
