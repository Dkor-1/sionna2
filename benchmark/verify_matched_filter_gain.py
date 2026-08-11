# -*- coding: utf-8 -*-
"""
verify_matched_filter_gain.py — ⭐**정합필터 이득이 링크버짓에 들어갔나** 를 수로 증명한다
==================================================================================================
왜 이 스크립트가 있나 (2026-08-10 적대검증이 잡은 결함 ②)
------------------------------------------------------------------------------------------------
`microdoppler_nearfield.echo_over_noise_db()` 는 잡음을 `P_n = k·T0·F·B` (B = 100 MHz) 로 세운다.
그런데 그 반환값을 우리는 **슬로타임 표본 E[m] 의 SNR** 로 썼다(`experiment_md_range.py`).
E[m] 은 «PRI 한 개 분량의 대역 B 신호를 기준신호와 상관» 해서 나온 **정합필터 출력**이라,
시간·대역폭 곱만큼 이득이 붙는다:

    G_mf = 10·log10(B / PRF) = 10·log10(1e8 / 2e4) = 36.99 dB      (PRF 19.7 kHz 면 37.06 dB)

⇒ 거리 링크버짓이 **37 dB 비관적**이었다. 이 스크립트는 그 37 dB 가 «주장» 이 아니라
  **측정 가능한 양**임을 보인다.

무엇을 재나 — 게이트 넷
------------------------------------------------------------------------------------------------
  MF1  백색 가우시안 기준신호로 정합필터를 통과시켰을 때 출력 SNR 이 10log10(L) 만큼 오르나
       (L = B/PRF = PRI 안의 빠른시간 표본 수).                          합격 |오차| ≤ 0.3 dB
  MF2  같은 것을 **정모듈러스(QPSK) 기준신호**로. 실제 통신 파형에 가깝다.  합격 |오차| ≤ 0.3 dB
  MF3  ⭐**끝에서 끝까지**: 빠른시간 잡음을 P_n = kT0F·B 로 넣고 PRI 마다 상관해 슬로타임 열을
       만든 뒤, 그 열의 SNR 이 사다리의 `snr_slow_db` (= ① + ②) 와 맞나.
       ← 이것이 «링크버짓이 옳다» 의 직접 증명이다.                        합격 |오차| ≤ 0.3 dB
  MF4  잡음대역 표현의 항등식:  kT0F·B / (B/PRF) == kT0F·PRF              합격 rel ≤ 1e-12
       (즉 «G_mf 를 붙인다» 와 «잡음 대역을 PRF 로 둔다» 는 같은 말이다)

이론 (MF1·MF2)
------------------------------------------------------------------------------------------------
기준신호 r[n] (n = 0..L−1), 에코 a·r[n], 잡음 w[n] ~ CN(0, σ²).  입력 표본당 SNR = a²/σ².
정합필터 출력  y = Σ conj(r[n])·(a r[n] + w[n]) = a·Σ|r|² + Σ conj(r) w
    신호전력 = a²·(Σ|r|²)²,   잡음전력 = σ²·Σ|r|²
    ⇒ 출력 SNR = (a²/σ²)·Σ|r|²  = 입력 SNR × L      (단위전력 기준신호에서 E[Σ|r|²] = L)
⚠ 가우시안 기준신호는 Σ|r|² 자체가 흔들려 E[(Σ|r|²)²] = L²+L 이라 이득이 10log10(L+1) 이다
  (L = 5000 에서 +0.00087 dB — 게이트 여유 안). 정모듈러스면 Σ|r|² = L 로 정확하다.

⚠ **전제**: 이상적 정합필터 · 기준신호를 정확히 안다 · 표본 정렬이 맞다. 실제 패시브 사슬에서
  기준채널이 더러우면 그만큼 깎인다(`benchmark/passive_two_channel_md.py` 가 잰 절벽).
  그리고 이 이득은 **풀 웨이브폼 캡처 팔에만** 붙는다 — 상시 기준신호(LTE CRS 1 kHz ·
  5G SSB 50 Hz)로는 PRF 20 kHz 슬로타임을 만들 수 없다.

⚠⚠ **혼동 금지 — 37 dB 짜리 양이 셋이다**
     ② 정합필터 이득(빠른시간, PRI 안)      10log10(1e8/2e4)  = 36.99 dB   ← 이 스크립트가 재는 것
     CPI 전체 슬로타임 코히어런트 적분      10log10(5000)     = 36.99 dB   ← 우연히 같은 수
     ④ STFT 한 조각(70 표본·Hann) 이득      10log10(70)−1.76  = 16.69 dB   ← 맵에서 실제로 보는 것

실행 (CPU 수 초, GPU 불필요)
------------------------------------------------------------------------------------------------
    cd sionna2 && PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/verify_matched_filter_gain.py
산출: outputs/verify_matched_filter_gain.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "src"))

import microdoppler_nearfield as nf                                    # noqa: E402

OUT = os.path.join(_ROOT, "outputs", "verify_matched_filter_gain.json")

TOL_DB = 0.3          # G11 합격선 (설계서 §3-3)
TOL_REL = 1e-12       # 항등식 합격선


def _db(x):
    return float(10.0 * np.log10(max(float(x), 1e-300)))


def _mf_gain_trial(L, snr_in_db, n_real, rng, kind="gauss"):
    """정합필터 출력 SNR 을 몬테카를로로 잰다. 반환 (측정 dB, 예측 dB, 진단)."""
    a = 10.0 ** (float(snr_in_db) / 20.0)          # 잡음 표본 전력 1 기준 에코 진폭
    ps, pn = 0.0, 0.0
    for _ in range(int(n_real)):
        if kind == "gauss":                        # CN(0,1) 백색 기준신호
            r = (rng.normal(size=L) + 1j * rng.normal(size=L)) / np.sqrt(2.0)
        else:                                      # 정모듈러스 QPSK (|r| = 1)
            r = np.exp(1j * (np.pi / 4 + (np.pi / 2) * rng.integers(0, 4, size=L)))
        w = (rng.normal(size=L) + 1j * rng.normal(size=L)) / np.sqrt(2.0)
        rr = float(np.sum(np.abs(r) ** 2))
        y_sig = a * rr                             # 결정론 성분 (기준신호를 아는 전제)
        y_noi = complex(np.vdot(r, w))             # Σ conj(r)·w
        ps += abs(y_sig) ** 2
        pn += abs(y_noi) ** 2
    meas = _db(ps / max(pn, 1e-300)) - float(snr_in_db)
    pred = float(10.0 * np.log10(L))
    return meas, pred, dict(L=int(L), snr_in_db=float(snr_in_db), n_real=int(n_real),
                            reference=kind,
                            out_snr_measured_db=_db(ps / max(pn, 1e-300)),
                            out_snr_predicted_db=float(snr_in_db) + pred)


def gate_mf1_mf2(args, rng):
    gates = []
    for kind, gid in (("gauss", "MF1"), ("qpsk", "MF2")):
        meas, pred, diag = _mf_gain_trial(args.L, args.snr_in_db, args.n_real, rng, kind)
        gates.append(dict(
            id=gid, what=f"matched-filter gain, {kind} reference",
            measured_gain_db=round(meas, 4), predicted_gain_db=round(pred, 4),
            err_db=round(meas - pred, 4), tol_db=TOL_DB,
            passed=bool(abs(meas - pred) <= TOL_DB), **diag))
    return gates


def gate_mf3(args, rng):
    """끝에서 끝까지: 빠른시간 잡음 kT0F·B → PRI 상관 → 슬로타임 SNR vs 사다리 ③."""
    L = int(round(args.b_hz / args.prf))                # PRI 안 빠른시간 표본 수
    lad = nf.snr_ladder(10.0 ** (args.sigma_dbsm / 10.0), args.range_m, args.fc,
                        prf=args.prf, capture="full_waveform", b_hz=args.b_hz)
    snr_band_db = lad["snr_band_db"]                    # ① 정합필터 전, 빠른시간 표본당
    a = 10.0 ** (snr_band_db / 20.0)                    # 잡음 표본전력 1 정규화
    ps, pn = 0.0, 0.0
    for _ in range(int(args.n_pri)):
        r = np.exp(1j * (np.pi / 4 + (np.pi / 2) * rng.integers(0, 4, size=L)))
        w = (rng.normal(size=L) + 1j * rng.normal(size=L)) / np.sqrt(2.0)
        x = a * r + w                                   # 수신 빠른시간 표본 (에코 + 열잡음)
        y = complex(np.vdot(r, x)) / L                  # 정합필터 출력 = 슬로타임 표본 하나
        y_sig = a * float(np.sum(np.abs(r) ** 2)) / L
        ps += abs(y_sig) ** 2
        pn += abs(y - y_sig) ** 2
    meas = _db(ps / max(pn, 1e-300))
    pred = lad["snr_slow_db"]
    return dict(
        id="MF3", what="end-to-end: fast-time kT0F*B noise -> per-PRI correlation -> slow-time SNR",
        L_fast_samples=L, n_pri=int(args.n_pri),
        snr_band_db=round(snr_band_db, 4), g_mf_db=round(lad["g_mf_db"], 4),
        slow_snr_measured_db=round(meas, 4), slow_snr_predicted_db=round(pred, 4),
        err_db=round(meas - pred, 4), tol_db=TOL_DB,
        passed=bool(abs(meas - pred) <= TOL_DB),
        scenario=dict(sigma_dbsm=args.sigma_dbsm, range_m=args.range_m, fc_hz=args.fc,
                      eirp_dbm=nf.DECLARED_EIRP_DBM, rx_gain_dbi=nf.DECLARED_RX_GAIN_DBI,
                      nf_db=nf.DECLARED_NF_DB, b_hz=args.b_hz, prf_hz=args.prf,
                      geometry="monostatic_equivalent"))


def gate_mf4(args):
    """항등식: kT0F·B / (B/PRF) == kT0F·PRF  —  «이득을 붙인다» == «잡음대역이 PRF 다»."""
    f = 10.0 ** (nf.DECLARED_NF_DB / 10.0)
    pn_band = nf.K_BOLTZ * nf.T0 * f * args.b_hz
    g_mf = 10.0 ** (nf.matched_filter_gain_db(args.b_hz, args.prf) / 10.0)
    lhs = pn_band / g_mf
    rhs = nf.K_BOLTZ * nf.T0 * f * args.prf
    rel = abs(lhs - rhs) / rhs
    return dict(id="MF4", what="kT0F*B / (B/PRF) == kT0F*PRF (identity of the two formulations)",
                lhs_w=lhs, rhs_w=rhs, rel_err=rel, tol_rel=TOL_REL, passed=bool(rel <= TOL_REL),
                p_noise_band_dbm=round(_db(pn_band) + 30.0, 3),
                p_noise_prf_dbm=round(_db(rhs) + 30.0, 3))


def gate_mf5(args):
    """API 게이트: 기본 호출은 옛 값과 **비트동일**, full_waveform 은 정확히 G_mf 만큼 크다."""
    sig = 10.0 ** (args.sigma_dbsm / 10.0)
    old = float(nf.echo_over_noise_db(sig, args.range_m, args.fc))              # 기본 = pre_mf
    pilot = float(nf.echo_over_noise_db(sig, args.range_m, args.fc,
                                        capture="always_on_pilot", prf=args.prf))
    full = float(nf.echo_over_noise_db(sig, args.range_m, args.fc,
                                       capture="full_waveform", prf=args.prf))
    terms = nf.echo_over_noise_db(sig, args.range_m, args.fc, prf=args.prf,
                                  capture="full_waveform", return_terms=True)
    g = nf.matched_filter_gain_db(args.b_hz, args.prf)
    ok = (old == pilot) and (full == old + g) and (float(terms["snr_band_db"]) == old) \
        and (float(terms["snr_slow_db"]) == full)
    return dict(id="MF5", what="echo_over_noise_db(): default bit-identical; full_waveform = default + G_mf; "
                               "return_terms carries BOTH (old snr_band_db, new snr_slow_db)",
                default_db=old, always_on_pilot_db=pilot, full_waveform_db=full,
                g_mf_db=g, terms_snr_band_db=float(terms["snr_band_db"]),
                terms_snr_slow_db=float(terms["snr_slow_db"]),
                passed=bool(ok))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--L", type=int, default=5000, help="PRI 안 빠른시간 표본 수 = B/PRF")
    ap.add_argument("--snr-in-db", type=float, default=-30.0)
    ap.add_argument("--n-real", type=int, default=4000)
    ap.add_argument("--n-pri", type=int, default=2000)
    ap.add_argument("--b-hz", type=float, default=nf.DECLARED_B_HZ)
    ap.add_argument("--prf", type=float, default=nf.DECLARED_PRF_HZ)
    ap.add_argument("--fc", type=float, default=3.5e9)
    ap.add_argument("--range-m", type=float, default=10.0)
    ap.add_argument("--sigma-dbsm", type=float, default=-18.879,
                    help="matrice4e 3.5 GHz 방위평균 σ (md_range_sweep.json)")
    ap.add_argument("--seed", type=int, default=20260810)
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()

    t0 = time.time()
    rng = np.random.default_rng(a.seed)
    gates = gate_mf1_mf2(a, rng)
    gates.append(gate_mf3(a, rng))
    gates.append(gate_mf4(a))
    gates.append(gate_mf5(a))

    n_pass = sum(1 for g in gates if g["passed"])
    doc = dict(
        _meta=dict(
            title="matched-filter processing gain — numeric gate for the range link budget",
            generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
            script="benchmark/verify_matched_filter_gain.py",
            defect="2026-08-10: G_mf = 10log10(B/PRF) was missing from the range link budget "
                   "(echo_over_noise_db counted noise over B=100 MHz but its output was used as the "
                   "slow-time sample SNR, i.e. as a matched-filter output)",
            convention=nf.SNR_CONVENTION,
            capture_precondition="full-waveform capture only; always-on pilots (LTE CRS 1 kHz, "
                                 "5G SSB 50 Hz) cannot form a 20 kHz slow-time stream, so G_mf = 0 there",
            do_not_confuse={
                "g_mf_db (fast-time, one PRI)": round(nf.matched_filter_gain_db(a.b_hz, a.prf), 3),
                "cpi_coherent_gain_db (slow-time, 5000 samples)": round(float(10 * np.log10(5000)), 3),
                "g_stft_db (one STFT frame, 70 samples, Hann)": round(
                    float(10 * np.log10(70)) + nf.WINDOW_COH_LOSS_DB["hann"], 3),
                "note": "three different quantities; two of them happen to be ~37 dB"},
            gpu_used=False, runtime_s=round(time.time() - t0, 2)),
        summary=dict(n_gates=len(gates), n_pass=n_pass, all_pass=bool(n_pass == len(gates)),
                     g_mf_db=round(nf.matched_filter_gain_db(a.b_hz, a.prf), 4),
                     b_hz=a.b_hz, prf_hz=a.prf, L=int(round(a.b_hz / a.prf))),
        gates=gates,
    )
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    tmp = a.out + ".tmp"
    with open(tmp, "w") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
    os.replace(tmp, a.out)

    for g in gates:
        mark = "PASS" if g["passed"] else "FAIL"
        extra = g.get("err_db", g.get("rel_err", ""))
        print(f"  [{mark}] {g['id']}  {g['what'][:62]:62s}  err={extra}")
    print(f"\n{n_pass}/{len(gates)} pass   G_mf = {doc['summary']['g_mf_db']} dB "
          f"(B={a.b_hz:.3g} Hz, PRF={a.prf:.6g} Hz, L={doc['summary']['L']})")
    print(f"→ {a.out}  ({time.time() - t0:.1f} s)")
    return 0 if n_pass == len(gates) else 1


if __name__ == "__main__":
    sys.exit(main())
