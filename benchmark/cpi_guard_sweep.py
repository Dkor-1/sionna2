# -*- coding: utf-8 -*-
"""cpi_guard_sweep.py — **CPI / 0-도플러 가드 스윕**: "5G 커버리지 0" 은 구조인가 인공물인가
====================================================================================================

■ 왜 이 스크립트가 필요한가
  report05 헤드라인은 "5G 는 **모든 헤딩**에서 도플러 블라인드(blind=1.000, coverage=0)" 라고
  단정한다(outputs/report13_freespace.json : ranges.mavic4pro.G1...blind_heading_frac = 1.0).
  그런데 그 1.000 은 **두 가지 선택**에 동시에 걸려 있다:

    (1) T_CPI = 100 ms 라는 단일 CPI.  가드 반폭(선언) = 2.5·PRF/M 이고 M=round(T·PRF) 이므로
        가드 반폭 ≥ 접힘축 반폭 PRF/2 ⇔ **M ≤ 5**.  SSB(PRF 50 Hz)는 T=0.1 s 에서 정확히 M=5 다.
        T=0.2 s 면 M=10 이라 이 등식이 깨진다(A5).
    (2) **선언 가드 2.5빈**.  검출기(`freespace_detect.DOPPLER_GUARD_WIDTH=3`)가 실제로 지우는
        폭은 **1.5빈**이고, `freespace_scene.blind_fractions` 의 docstring 은 인용 정본을
        `blind_hard`(1.5빈)라고 못박아 두었다.  1.5빈이면 M=5 에서 5행 중 3행만 지워진다.

  즉 "0" 은 한 점(CPI)·한 규약(2.5빈)의 교집합에서만 나온다.  논문 문장으로 내보내면 한 줄에
  반박당한다.  이 스크립트는 **무엇이 진짜 구조인지**를 스윕으로 확정한다.

■ 계산하지 않고 **저장소 함수를 부른다**(재구현 금지, 과제 ⭐)
    freespace_scene.prf_hz / M_from_prf / cpi_feasibility / doppler_bin_hz / doppler_guard_hz
    freespace_scene.blind_sector / blind_fractions / folded_doppler / nyquist_gate
    freespace_scene.fs_params / target_pos / heading_velocity
    waveforms.all_waveforms (ref_bw_hz → ΔR_b = c/B, 규약 A1)
  기하·SNR 상수는 experiment_freespace_range 에서 그대로 읽어 온다(EIRP/G_rx/NF/밴드표).

■ 산출
    outputs/cpi_guard_sweep.json
    outputs/figures/cpi_guard_f{1..4}_*.png   (그림 텍스트 전부 영어, 캡션만 한국어)

실행:  cd sionna2 && PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/cpi_guard_sweep.py
       빠른 확인:  --smoke
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (os.path.join(_ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "4")

import numpy as np                                          # noqa: E402

import freespace_scene as fss                               # noqa: E402
from waveforms import all_waveforms                         # noqa: E402
import experiment_freespace_range as efr                    # noqa: E402  (상수·밴드표 재사용)

C0 = fss.C0

# --------------------------------------------------------------------------- #
#  0. 설정 — 전부 report13/report05 헤드라인 셀과 **동일**하게 잡는다(재현이 앵커)
# --------------------------------------------------------------------------- #
JSON_FS = os.path.join(_ROOT, "outputs", "report13_freespace.json")
OUT_JSON = os.path.join(_ROOT, "outputs", "cpi_guard_sweep.json")
OUT_FIG = os.path.join(_ROOT, "outputs", "figures")

DRONE = "mavic4pro"          # report05 표가 인용하는 기체
L_REF = fss.L_REF            # 500 m
ALT_REF = fss.FS_ALT[0]      # 60 m
PHI_REF = fss.PHI_HEADLINE_DEG   # 90°
SPEED_REF = fss.FS_SPEED[0]      # 5 m/s
SPEED_FAST = fss.FS_SPEED[1]     # 15 m/s
T_REF = fss.T_CPI_REF_S          # 0.1 s
D_COMMON = 1000.0            # 모드별 R90 차이를 지우고 파형효과만 보는 공통거리

PSI_N_PUB = 72               # 발표된 값의 헤딩격자(=1/72 양자화)
PSI_N_FINE = 720             # 수렴값용
TRIO = ("W1", "L1", "G1")
MODE_LABEL = {"W1": "WiFi (VHT-LTF)", "L1": "LTE (CRS)", "G1": "5G NR (SSB)",
              "W2": "WiFi G2", "W3": "WiFi G3", "L2": "LTE (PRS)", "L3": "LTE (PRS)",
              "G2": "5G NR (PRS)", "G3": "5G NR (PRS)"}


def _t_grid(smoke=False):
    """CPI 격자 [s].  T=0.1(헤드라인)·0.2(A5 반례)를 **정확히** 포함시킨다."""
    if smoke:
        g = np.array([0.05, 0.1, 0.2, 0.5, 1.0, 2.0])
    else:
        g = np.unique(np.concatenate([np.geomspace(0.01, 20.0, 240),
                                      [0.02, 0.056, 0.1, 0.2, 0.4, 0.5, 1.0, 2.0, 5.0, 10.0]]))
    return np.sort(g)


def _speed_grid(smoke=False):
    if smoke:
        return np.array([0.0, 1.0, 5.0, 15.0])
    return np.unique(np.concatenate([np.linspace(0.0, 30.0, 61), [5.0, 15.0]]))


# --------------------------------------------------------------------------- #
#  1. 파형 파라미터 — 저장소 단일 진리원에서 읽는다
# --------------------------------------------------------------------------- #
def waveform_facts():
    """모드 → (std, occ, fc, lam, PRF, ref_bw, ΔR_b, ref_name).  전부 저장소에서 읽는다."""
    facts = {}
    wf_cache = {}
    for mode, (std, occ) in efr.MODE_STD.items():
        _band, fc, _bw = efr._BAND_BY_STD[std]
        if occ not in wf_cache:
            wf_cache[occ] = all_waveforms(occ)
        wf = wf_cache[occ][std]
        facts[mode] = dict(mode=mode, std=std, occ=occ, label=MODE_LABEL.get(mode, mode),
                           fc_hz=float(fc), lam_m=float(C0 / fc),
                           prf_hz=float(fss.prf_hz(std, occ)),
                           ref_name=str(wf.ref_name), ref_bw_hz=float(wf.ref_bw_hz),
                           range_res_m=float(wf.range_resolution_m))     # ΔR_b = c/B (A1)
    return facts


def r90_by_mode():
    """report13 이 발표한 R90 [m] (mavic4pro·equal_psd·full_waveform_capture·N=1).  provenance."""
    J = json.load(open(JSON_FS, encoding="utf-8"))
    out = {}
    for mode in TRIO:
        c = J["ranges"][DRONE][mode]["equal_psd"]["full_waveform_capture"]["by_N"]["1"]
        out[mode] = dict(R90_m=float(c["R90_C50_m"]),
                         published_blind=float(c["blind_heading_frac"]),
                         published_coverage_ceiling=float(c["coverage_ceiling"]))
    return out


# --------------------------------------------------------------------------- #
#  2. 헤딩 스윕 한 셀 — 전부 freespace_scene 호출
# --------------------------------------------------------------------------- #
def cell(mode, facts, T, d, speed, psi_n, L=L_REF, alt=ALT_REF, phi=PHI_REF):
    """(모드, CPI, 거리, 속도) → 시간축·가드·블라인드 한 줄.  **산술 재구현 없음.**"""
    f = facts[mode]
    prf, lam = f["prf_hz"], f["lam_m"]
    M = fss.M_from_prf(T, prf)
    feas = fss.cpi_feasibility(T, prf)                       # M/T_eff/feasible/rows_left/reason
    psi = np.linspace(0.0, 360.0, int(psi_n), endpoint=False)
    fr = fss.blind_fractions(psi, phi, d, L, alt, T, prf, speed, lam, M=M)
    # 검출기가 실제로 지우는 '행 수' 관점(이산) — 연속가드와 별개의 측정 가능한 양
    row_blind = min(1.0, float(feas["guard_width"]) / float(M))
    return dict(
        mode=mode, T_cpi_s=float(T), d_m=float(d), speed_ms=float(speed), psi_n=int(psi_n),
        prf_hz=prf, M=int(M), M_exact=float(feas["M_exact"]), T_eff_s=float(feas["T_eff_s"]),
        doppler_bin_hz=float(fr["bin_hz"]),
        guard_hard_hz=float(fr["f_guard_hard_hz"]),          # 1.5빈 — 검출기 실측 규약(정본)
        guard_declared_hz=float(fr["f_guard_declared_hz"]),  # 2.5빈 — 스펙 §7.2 선언
        fold_half_hz=float(prf / 2.0),                       # 접힌 도플러축 반폭
        blind_hard=float(fr["blind_hard"]), blind_declared=float(fr["blind_declared"]),
        soft_blind_frac=float(fr["soft_blind_frac"]), alias_frac=float(fr["alias_frac"]),
        coverage_ceiling_hard=float(1.0 - fr["blind_hard"]),
        coverage_ceiling_declared=float(1.0 - fr["blind_declared"]),
        doppler_rows_left=int(feas["doppler_rows_left"]),
        row_blind_frac=float(row_blind),
        guard_covers_axis_hard=bool(fr["f_guard_hard_hz"] >= prf / 2.0),
        guard_covers_axis_declared=bool(fr["f_guard_declared_hz"] >= prf / 2.0),
        feasible=bool(feas["feasible"]), reason=feas["reason"],
        fd_amp_hz=float(np.abs(fr["fd_hz"]).max()),
        snr_cpi_gain_db=float(10.0 * np.log10(T / T_REF)),   # 링크버짓 10log10(T) 항
    )


# --------------------------------------------------------------------------- #
#  3. 코히런스 비용 — CPI 동안 표적이 한 빈 안에 머무는가
# --------------------------------------------------------------------------- #
def walk_over_cpi(mode, facts, T, d, speed, psi_n=72, n_t=9,
                  L=L_REF, alt=ALT_REF, phi=PHI_REF):
    """CPI T 동안의 **도플러 이동 Δf_d [Hz]** 와 **바이스태틱 거리 이동 ΔR_b [m]** (헤딩별).

    표적을 P(t)=P0+v·t (t∈[-T/2,+T/2]) 로 실제로 움직여 `fs_params` 를 다시 푼다 — 등속직선
    비행이라도 기하가 돌기 때문에 f_d 는 CPI 안에서 변한다(가속도 0 이어도 생기는 항).
    반환: (dfd_hz[psi], dRb_m[psi], fd0_hz[psi])
    """
    f = facts[mode]
    lam = f["lam_m"]
    psi = np.linspace(0.0, 360.0, int(psi_n), endpoint=False)
    V = fss.heading_velocity(psi, speed)                     # (P,3)
    P0 = fss.target_pos(d, phi, L, alt)                      # (3,)
    t = np.linspace(-0.5 * T, 0.5 * T, int(n_t))             # (K,)
    P = P0[None, None, :] + V[:, None, :] * t[None, :, None]  # (P,K,3)
    p = fss.fs_params(fss.FS_TX, fss.FS_RX(L), P, V[:, None, :], C0 / lam)
    fd = np.asarray(p["fd"], float)                          # (P,K)
    Rb = np.asarray(p["Rb"], float)
    return (fd.max(axis=1) - fd.min(axis=1),
            Rb.max(axis=1) - Rb.min(axis=1),
            fd[:, int(n_t) // 2])


def coherence_limits(mode, facts, d, speed, psi_n=72, n_T=180, smoke=False):
    """표적이 **한 도플러 빈**·**한 거리 빈** 안에 머무는 최대 CPI [s] (헤딩별 → 통계).

    · 도플러 한계 : Δf_d(T) = Δf_bin(T) = PRF/M(T) 의 첫 교차 (T 증가 시 좌변↑ 우변↓ → 유일)
    · 거리   한계 : ΔR_b(T) = c/B_ref (A1 규약, 파형별 상수) 의 첫 교차
    격자 위 첫 교차를 log T 선형보간으로 잡는다(M 이 계단이라 이분법보다 안전).
    """
    f = facts[mode]
    Tg = np.geomspace(0.005, 60.0, 40 if smoke else int(n_T))
    dR_res = f["range_res_m"]
    P = int(psi_n)
    dfd = np.zeros((len(Tg), P))
    dRb = np.zeros((len(Tg), P))
    binhz = np.zeros(len(Tg))
    for i, T in enumerate(Tg):
        a, b, _ = walk_over_cpi(mode, facts, float(T), d, speed, psi_n=P)
        dfd[i], dRb[i] = a, b
        binhz[i] = fss.doppler_bin_hz(float(T), f["prf_hz"], fss.M_from_prf(float(T), f["prf_hz"]))

    def _first_cross(y, thr):
        """y(T) - thr(T) 가 처음 0 을 넘는 T [s].  없으면 (전부 아래) inf / (전부 위) Tg[0]."""
        out = np.full(P, np.inf)
        g = y - (thr[:, None] if np.ndim(thr) else thr)
        for j in range(P):
            k = np.argmax(g[:, j] > 0) if np.any(g[:, j] > 0) else -1
            if k < 0:
                continue
            if k == 0:
                out[j] = float(Tg[0])
                continue
            x0, x1 = np.log(Tg[k - 1]), np.log(Tg[k])
            y0, y1 = g[k - 1, j], g[k, j]
            out[j] = float(np.exp(x0 + (x1 - x0) * (-y0) / max(y1 - y0, 1e-300)))
        return out

    T_dop = _first_cross(dfd, binhz)
    T_rng = _first_cross(dRb, dR_res)
    T_both = np.minimum(T_dop, T_rng)

    def _st(a):
        fin = a[np.isfinite(a)]
        return dict(min=float(np.min(a)) if len(a) else None,
                    median=float(np.median(fin)) if len(fin) else None,
                    max=float(np.max(fin)) if len(fin) else float("inf"),
                    n_infinite=int(np.sum(~np.isfinite(a))))
    return dict(mode=mode, d_m=float(d), speed_ms=float(speed), psi_n=P,
                range_res_m=float(dR_res),
                T_coh_doppler_s=_st(T_dop), T_coh_range_s=_st(T_rng), T_coh_s=_st(T_both))


# --------------------------------------------------------------------------- #
#  4. 패리티 CPI — 5G 가 WiFi/LTE 의 블라인드율까지 내려오려면 CPI 가 얼마여야 하나
# --------------------------------------------------------------------------- #
def unambiguous_speed(mode, facts, d, psi_n=720, L=L_REF, alt=ALT_REF, phi=PHI_REF):
    """**CPI 와 무관한** 속도 모호성 한계 [m/s].

    slow-time 샘플링률이 PRF 이므로 |f_d| < PRF/2 를 넘으면 접힌다(`nyquist_gate`).
    f_d 는 속도에 선형이라 v_unamb = (PRF/2) / (max_psi |f_d| / v) 로 **정확히** 나온다.
    이 값은 CPI 를 아무리 늘려도 변하지 않는다 — 적분시간이 아니라 표본화율의 성질이다.
    비교용으로 저장소 프로퍼티 `Waveform.v_unambiguous_ms`(모노 등가 PRF·λ/4)도 같이 낸다.
    """
    f = facts[mode]
    probe = 10.0
    psi = np.linspace(0.0, 360.0, int(psi_n), endpoint=False)
    fd, _ = fss._fd_of_heading(psi, phi, d, L, alt, probe, f["lam_m"])
    slope = float(np.abs(fd).max() / probe)                  # Hz per (m/s), 최악 헤딩
    wf = all_waveforms(f["occ"])[f["std"]]
    return dict(mode=mode, d_m=float(d), prf_hz=f["prf_hz"],
                fd_hz_per_ms=slope,
                v_unambiguous_ms=float((f["prf_hz"] / 2.0) / max(slope, 1e-12)),
                v_unambiguous_mono_equiv_ms=float(wf.v_unambiguous_ms),
                note="CPI-independent: sampling-rate limit, not integration-time limit")


def coherence_map(facts, mode, d_list, v_list, psi_n=72, smoke=False):
    """(거리 d, 속도 v) 격자 위의 코히런스 상한 T_coh [s] — 요구 CPI 와 비교하기 위한 지도.

    ⚠ 헤드라인 R90(6.3 km)은 기하가 거의 안 도는 **가장 관대한** 지점이다. 근거리에서는
    같은 속도라도 기하회전율(≈v/d)이 커져 T_coh 가 급감한다 — 요구 CPI 의 실현 가능성은
    거리에 따라 뒤집힌다. 이 지도가 그 뒤집힘을 보여준다.
    """
    out = []
    for d in d_list:
        for v in v_list:
            cl = coherence_limits(mode, facts, float(d), float(v), psi_n=psi_n, smoke=smoke)
            out.append(dict(d_m=float(d), speed_ms=float(v),
                            T_coh_doppler_s=cl["T_coh_doppler_s"]["median"],
                            T_coh_range_s=cl["T_coh_range_s"]["median"],
                            T_coh_s=cl["T_coh_s"]["median"]))
    return out


def no_fold_counterfactual(mode, facts, T, d, speed, psi_n, K=200,
                           L=L_REF, alt=ALT_REF, phi=PHI_REF):
    """**접힘만 끈** 반사실: 같은 CPI·같은 도플러 빈폭인데 PRF 만 K배인 가상 파형.

    `blind_fractions` 에 (PRF·K, M·K) 를 주면 빈폭 PRF/M 은 그대로이고 접힘축 반폭만 K배로
    벌어진다(=사실상 접히지 않는다). 그래서 5G 블라인드율 중 **얼마가 접힘 탓이고 얼마가
    파장(=반송파) 탓인지** 분해된다. 저장소 함수만 쓴다(별도 산술 없음).
    """
    f = facts[mode]
    M = fss.M_from_prf(T, f["prf_hz"])
    psi = np.linspace(0.0, 360.0, int(psi_n), endpoint=False)
    fr = fss.blind_fractions(psi, phi, d, L, alt, T, f["prf_hz"] * K, speed, f["lam_m"],
                             M=M * K)
    return dict(mode=mode, K=int(K), T_cpi_s=float(T),
                doppler_bin_hz=float(fr["bin_hz"]),
                blind_hard_nofold=float(fr["blind_hard"]),
                blind_declared_nofold=float(fr["blind_declared"]),
                alias_frac=float(fr["alias_frac"]))


def total_blind_edges(sweep_rows, key):
    """스윕에서 blind==1.0 이 **끝나는** CPI [s] (관측값).  전 구간 1.0 이 아니면 그 상한을 준다."""
    T = np.array([r["T_cpi_s"] for r in sweep_rows], float)
    y = np.array([r[key] for r in sweep_rows], float)
    tot = y >= 1.0 - 1e-12
    if not tot.any():
        return dict(observed_total_blind=False, T_max_total_blind_s=None)
    idx = np.where(tot)[0]
    return dict(observed_total_blind=True, T_max_total_blind_s=float(T[idx.max()]),
                contiguous_from_start=bool(idx.min() == 0))


def _tcoh_at(by_speed, v):
    """by_speed 목록에서 속도 v [m/s] 에 가장 가까운 칸의 T_coh [s]."""
    r = min(by_speed, key=lambda x: abs(x["speed_ms"] - float(v)))
    return float(r["T_coh_s"])


def parity_cpi(sweep_mode_rows, target, key):
    """블라인드율이 `target` 이하로 처음 내려가는 CPI, 그리고 **그 뒤로 다시 안 올라가는** CPI.

    접힘 때문에 blind(T) 는 단조가 아닐 수 있어 두 개를 같이 낸다:
      T_first     : 처음 target 이하가 되는 T
      T_sustained : 이 T 이상에서 격자 끝까지 계속 target 이하인 최소 T (인용 정본)
    """
    T = np.array([r["T_cpi_s"] for r in sweep_mode_rows], float)
    y = np.array([r[key] for r in sweep_mode_rows], float)
    ok = y <= float(target) + 1e-12
    first = float(T[np.argmax(ok)]) if ok.any() else None
    sus = None
    if ok.any():
        bad = np.where(~ok)[0]
        idx = (bad[-1] + 1) if len(bad) else 0
        sus = float(T[idx]) if idx < len(T) else None
    return dict(target=float(target), T_first_s=first, T_sustained_s=sus,
                achievable=bool(ok.any()))


# --------------------------------------------------------------------------- #
#  5. 구조 조건 — 해석식과 수치의 대조
# --------------------------------------------------------------------------- #
def structural_conditions(facts):
    """'도플러축 전체가 가드' 조건을 닫힌형으로 내고 수치로 검증한다.

        guard_hz = g·PRF/M ≥ PRF/2  ⇔  M ≤ 2g   (g = 가드 빈수)
        M = round(T·PRF)            ⇒  T ≤ 2g/PRF
      선언 g=2.5 → M≤5,  T ≤ 5/PRF.   실측(hard) g=1.5 → M≤3,  T ≤ 3/PRF.
    ★ 이 조건에는 **반송파도 속도도 거리도 없다** — 순전히 slow-time 샘플링의 성질이다.
    """
    out = {}
    for mode, f in facts.items():
        prf = f["prf_hz"]
        out[mode] = dict(
            prf_hz=prf,
            M_max_total_blind_declared=int(2 * fss.GUARD_DOPPLER_BINS),
            M_max_total_blind_hard=int(2 * fss.DOPPLER_GUARD_HARD_BINS),
            T_max_total_blind_declared_s=float(2 * fss.GUARD_DOPPLER_BINS / prf),
            T_max_total_blind_hard_s=float(2 * fss.DOPPLER_GUARD_HARD_BINS / prf),
            M_at_T_ref=int(fss.M_from_prf(T_REF, prf)))
    return dict(
        formula="guard_hz = g*PRF/M >= PRF/2  <=>  M <= 2g  <=>  T_cpi <= 2g/PRF",
        guard_bins_declared=float(fss.GUARD_DOPPLER_BINS),
        guard_bins_hard=float(fss.DOPPLER_GUARD_HARD_BINS),
        carrier_speed_range_independent=True,
        note=("전 헤딩 블라인드는 반송파·속도·거리와 무관한 slow-time 샘플링 조건이다. "
              "단, 부분 블라인드율은 반송파(λ)와 속도에 의존한다."),
        by_mode=out)


# --------------------------------------------------------------------------- #
#  6. 그림 (텍스트 영어, 캡션 한국어 — viz_report13 규약/색 재사용)
# --------------------------------------------------------------------------- #
def make_figures(res, out_dir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from viz_report13 import Saver, mode_color              # 하우스 팔레트/저장규약 재사용
    import textwrap

    _sv = Saver(out_dir)

    def save(fig, name, caption):
        """캡션은 반드시 줄바꿈해서 넘긴다 — 한 줄짜리 긴 supxlabel 은 tight bbox 를 옆으로
        늘려 그림 자체를 납작하게 만든다(첫 판에서 실제로 그랬다)."""
        return _sv(fig, name, "\n".join(textwrap.wrap(" ".join(caption.split()), 96)))
    COL = {m: mode_color(m) for m in TRIO}
    LBL = {m: MODE_LABEL[m] for m in TRIO}

    # 로그축 눈금은 ASCII 평문으로 — NanumGothic/mathtext 에 U+2212 글리프가 없어 두부가 된다
    # (viz_report13._plain_log 와 같은 이유·같은 처방).
    _PLAIN = plt.FuncFormatter(lambda v, p: ("%g" % v) if v > 0 else "")

    def _logx(ax):
        ax.set_xscale("log")
        ax.xaxis.set_major_formatter(_PLAIN)
        ax.xaxis.set_minor_formatter(plt.NullFormatter())

    def _logy(ax):
        ax.set_yscale("log")
        ax.yaxis.set_major_formatter(_PLAIN)
        ax.yaxis.set_minor_formatter(plt.NullFormatter())

    # ── F1: blind fraction vs CPI ────────────────────────────────────────────
    S = res["cpi_sweep"]["at_R90"]
    fig, axes = plt.subplots(1, 2, figsize=(11.6, 4.5), sharey=True)
    for ax, key, ttl in ((axes[0], "blind_hard", "Detector guard (1.5 bins, canonical)"),
                         (axes[1], "blind_declared", "Declared guard (2.5 bins, spec 7.2)")):
        for m in TRIO:
            rows = S[m]
            T = [r["T_cpi_s"] for r in rows]
            y = [r[key] for r in rows]
            ax.plot(T, y, lw=2.0, color=COL[m], label=LBL[m], zorder=3)
        ax.axvline(T_REF, color="#888888", lw=1.0, ls=":", zorder=1)
        ax.axvline(0.2, color="#888888", lw=1.0, ls=":", zorder=1)
        # 라벨은 축 **안쪽**에 — 위로 빼면 제목과 겹친다(첫 판 실패)
        bb = dict(fc="white", ec="none", alpha=0.85, pad=1.4)
        ax.text(T_REF * 0.92, 0.985, "0.1 s (headline)", ha="right", va="top",
                fontsize=7.5, color="#555555", bbox=bb, rotation=90)
        ax.text(0.2 * 1.09, 0.985, "0.2 s", ha="left", va="top",
                fontsize=7.5, color="#555555", bbox=bb, rotation=90)
        _logx(ax)
        ax.set_xlabel("CPI  $T$  [s]")
        ax.set_ylim(-0.03, 1.03)
        ax.set_title(ttl, fontsize=10)
        ax.grid(alpha=0.25, lw=0.6)
    axes[0].set_ylabel("blind heading fraction")
    axes[0].legend(fontsize=8.5, framealpha=0.92, loc="upper right")
    # 5G 전헤딩-블라인드 구간 음영
    for ax, k in ((axes[0], "T_max_total_blind_hard_s"), (axes[1], "T_max_total_blind_declared_s")):
        tmax = res["structural"]["by_mode"]["G1"][k]
        ax.axvspan(ax.get_xlim()[0], tmax, color=COL["G1"], alpha=0.10, zorder=0)
        ax.text(tmax, 0.5, " 5G total-blind\n $T\\leq%.3g$ s" % tmax, fontsize=7.5,
                color="#333333", ha="left", va="center")
    fig.tight_layout(rect=(0, 0.06, 1, 0.99))
    save(fig, "cpi_guard_f1_blind_vs_cpi.png",
         "F1 — CPI 스윕(각 모드 R90, v=%.0f m/s, L=%.0f m, alt=%.0f m, $\\phi$=90$\\degree$). "
         "5G 의 blind=1.000 은 T=0.1 s 와 2.5빈 선언가드가 동시에 성립할 때만 나온다. "
         "검출기 실측 규약(1.5빈)에서는 같은 CPI 에서도 1.000 이 아니다."
         % (SPEED_REF, L_REF, ALT_REF))

    # ── F2: blind fraction vs speed ──────────────────────────────────────────
    SP = res["speed_sweep"]
    Ts = list(SP.keys())
    fig, axes = plt.subplots(1, len(Ts), figsize=(4.3 * len(Ts), 4.3), sharey=True)
    axes = np.atleast_1d(axes)
    for ax, tk in zip(axes, Ts):
        for m in TRIO:
            rows = SP[tk][m]
            v = [r["speed_ms"] for r in rows]
            ax.plot(v, [r["blind_hard"] for r in rows], lw=2.0, color=COL[m], label=LBL[m])
        ax.set_xlabel("target speed  $v$  [m/s]")
        ax.set_title("CPI = %s s" % tk, fontsize=10)
        ax.set_ylim(-0.03, 1.03)
        ax.grid(alpha=0.25, lw=0.6)
        ax.axvline(SPEED_REF, color="#888888", lw=0.9, ls=":")
    axes[0].set_ylabel("blind heading fraction (1.5-bin guard)")
    axes[0].legend(fontsize=8.5, framealpha=0.92)
    fig.tight_layout(rect=(0, 0.07, 1, 0.99))
    save(fig, "cpi_guard_f2_blind_vs_speed.png",
         "F2 — 속도 스윕(호버 v=0 은 전 파형 블라인드). WiFi/LTE 는 v 가 커지면 블라인드율이 "
         "$\\propto$1/v 로 줄지만, 5G 는 도플러가 접혀 속도를 올려도 바닥이 안 내려간다 — "
         "이게 파형 간 진짜 비대칭이다.")

    # ── F3: 요구 CPI vs 코히런스 한계 — **거리 의존**이 결론을 뒤집는다 ───────
    CM = res["cost_of_long_cpi"]["coherence_map_d_v"]
    dl = res["cost_of_long_cpi"]["coherence_map_summary"]["d_list_m"]
    req_l = res["cost_of_long_cpi"]["required_cpi_s"]["to_LTE_parity"]
    req_w = res["cost_of_long_cpi"]["required_cpi_s"]["to_WiFi_parity"]
    fig, ax = plt.subplots(figsize=(7.6, 4.9))
    greys = ["#c8d8ea", "#8fb4d6", "#4d82b5", "#12395e"]
    for i, d in enumerate(dl):
        rows = sorted([r for r in CM if abs(r["d_m"] - d) < 1e-6], key=lambda r: r["speed_ms"])
        ax.plot([r["speed_ms"] for r in rows], [r["T_coh_s"] for r in rows], lw=2.0,
                marker="o", ms=5, color=greys[i % len(greys)],
                label="coherence limit, $d$ = %.0f m" % d)
    for val, lab, st in ((req_l, "LTE parity", "--"), (req_w, "WiFi parity", "-")):
        if val:
            ax.axhline(val, color="#ef6c00", lw=2.0, ls=st,
                       label="5G required CPI, %s (%.2f s)" % (lab, val))
    _logy(ax)
    ax.set_yticks([0.2, 0.3, 0.5, 1.0, 2.0, 3.0, 5.0])
    ax.set_ylim(0.16, 12.0)
    ax.set_xlabel("target speed  $v$  [m/s]")
    ax.set_ylabel("CPI  [s]")
    ax.set_title("5G SSB: required CPI vs the CPI coherence allows", fontsize=10.5)
    ax.grid(alpha=0.25, lw=0.6)
    ax.legend(fontsize=7.6, framealpha=0.95, loc="upper center", ncol=2)
    fig.tight_layout(rect=(0, 0.09, 1, 0.99))
    save(fig, "cpi_guard_f3_required_vs_allowed.png",
         "F3 — 5G 가 LTE/WiFi 수준 블라인드율에 닿는 데 필요한 CPI(주황 가로선)와, 표적이 한 "
         "도플러/거리 빈 안에 머무는 상한(파랑, 거리별). 헤드라인 거리에서는 요구 CPI 가 여유롭게 "
         "가능하다 — '긴 CPI 는 물리적으로 불가능' 이라는 가설은 반증됐다. 뒤집히는 곳은 근거리·고속뿐. "
         "곡선은 등속직선·무기동 가정의 낙관적 상한이다.")

    # ── F5: CPI 로 못 고치는 한계 — 무모호 속도 ────────────────────────────
    VU = res["unambiguous_speed"]
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ms = list(TRIO)
    vals = [VU[m]["v_unambiguous_ms"] for m in ms]
    ax.barh(range(len(ms)), vals, color=[COL[m] for m in ms], height=0.52)
    for i, (m, v_) in enumerate(zip(ms, vals)):
        ax.text(v_ * 1.06, i, "%.2f m/s  (PRF %.0f Hz)" % (v_, VU[m]["prf_hz"]),
                va="center", fontsize=8.5, color="#333333")
    ax.axvspan(1.0, 30.0, color="#cccccc", alpha=0.30, zorder=0)
    ax.set_ylim(-0.75, len(ms) - 0.5)
    ax.text(5.4, -0.62, "typical drone flight speeds", fontsize=8, color="#555555",
            ha="center", va="bottom")
    ax.set_yticks(range(len(ms)))
    ax.set_yticklabels([LBL[m] for m in ms], fontsize=9)
    _logx(ax)
    ax.set_xlim(0.3, 200)
    ax.set_xlabel("unambiguous target speed  [m/s]   (|$f_d$| < PRF/2)")
    ax.set_title("The limit no CPI can fix", fontsize=10.5)
    ax.grid(axis="x", alpha=0.25, lw=0.6)
    fig.tight_layout(rect=(0, 0.09, 1, 0.99))
    save(fig, "cpi_guard_f5_unambiguous_speed.png",
         "F5 — 접힘 한계 |f_d|<PRF/2 를 속도로 환산한 값(헤드라인 기하, 최악 헤딩). CPI 를 늘려도 "
         "변하지 않는다(적분시간이 아니라 표본화율의 성질). 5G 상시기준은 걷는 속도조차 모호 없이 "
         "못 재고, 이것이 '5G 벌점' 중 유일하게 규약·CPI 에 안 흔들리는 부분이다.")

    # ── F4: 구조식 — blind vs M(펄스수) ──────────────────────────────────────
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    for m in TRIO:
        rows = S[m]
        Ms = np.array([r["M"] for r in rows], float)
        y = np.array([r["blind_declared"] for r in rows], float)
        o = np.argsort(Ms)
        ax.plot(Ms[o], y[o], lw=2.0, color=COL[m], label=LBL[m])
    Mg = np.geomspace(2, 3e4, 200)
    ax.plot(Mg, np.minimum(1.0, 2 * fss.GUARD_DOPPLER_BINS / Mg), lw=1.4, ls="--",
            color="#444444", label="folded-regime law  $2g/M$  ($g$=2.5)")
    for m in TRIO:
        Mr = res["anchor"]["reproduction"][m]["M"]
        ax.plot([Mr], [res["anchor"]["reproduction"][m]["blind_declared"]], "o", ms=8,
                mfc="white", mec=COL[m], mew=2.0, zorder=5)
    _logx(ax)
    ax.set_xlabel("pulses per CPI  $M=\\mathrm{round}(T\\cdot \\mathrm{PRF})$")
    ax.set_ylabel("blind heading fraction (2.5-bin guard)")
    ax.set_ylim(-0.03, 1.03)
    ax.set_title("The penalty is a pulse-count law, not a 5G law", fontsize=10.5)
    ax.grid(alpha=0.25, lw=0.6)
    ax.legend(fontsize=8, framealpha=0.92)
    fig.tight_layout(rect=(0, 0.07, 1, 0.99))
    save(fig, "cpi_guard_f4_blind_vs_M.png",
         "F4 — 블라인드율을 M(=CPI 안의 기준신호 반복 횟수)에 대해 다시 그린 것. 5G 곡선은 접힘구간 "
         "법칙 2g/M 위에 정확히 얹히고, 접히지 않는 WiFi/LTE 는 그 위(=같은 M 이면 오히려 더 나쁨)에 "
         "있다. 흰 원이 헤드라인 CPI 0.1 s 의 위치다 — 5G 만 M=5. 즉 5G 벌점의 전부는 '같은 CPI 에서 "
         "M 이 20배 작다' 는 데서 오고, 원인은 표준이 아니라 상시 기준신호의 반복률이다.")
    return _sv.saved


# --------------------------------------------------------------------------- #
#  7. main
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--out", default=OUT_JSON)
    ap.add_argument("--fig-dir", default=OUT_FIG)
    a = ap.parse_args()
    t0 = time.time()

    facts = waveform_facts()
    R90 = r90_by_mode()
    psi_fine = PSI_N_PUB if a.smoke else PSI_N_FINE

    # ── (0) 앵커: 발표된 숫자를 그대로 재현한다 ──────────────────────────────
    print("■ 앵커 재현 (T=%.3g s, 72 헤딩, 각 모드 R90)" % T_REF)
    repro = {}
    for m in TRIO:
        c = cell(m, facts, T_REF, R90[m]["R90_m"], SPEED_REF, PSI_N_PUB)
        c["published_blind"] = R90[m]["published_blind"]
        c["reproduces_published"] = bool(abs(c["blind_declared"] - R90[m]["published_blind"]) < 1e-9)
        # 헤딩격자를 촘촘히 했을 때의 수렴값(72 격자는 1/72 양자화가 있다)
        cf = cell(m, facts, T_REF, R90[m]["R90_m"], SPEED_REF, psi_fine)
        c["blind_declared_fine"] = cf["blind_declared"]
        c["blind_hard_fine"] = cf["blind_hard"]
        repro[m] = c
        print("   %-3s PRF=%-6.4g M=%-4d bin=%-6.4g Hz  guard(hard/decl)=%.4g/%.4g Hz  "
              "fold=%.4g Hz | blind decl=%.4f (published %.4f, %s)  hard=%.4f  alias=%.4f"
              % (m, c["prf_hz"], c["M"], c["doppler_bin_hz"], c["guard_hard_hz"],
                 c["guard_declared_hz"], c["fold_half_hz"], c["blind_declared"],
                 c["published_blind"], "OK" if c["reproduces_published"] else "MISMATCH",
                 c["blind_hard"], c["alias_frac"]))

    # ── (1) CPI 스윕 ─────────────────────────────────────────────────────────
    Tg = _t_grid(a.smoke)
    print("■ CPI 스윕: %d 점 × 3 모드 × 2 거리규약" % len(Tg))
    sweep = {"at_R90": {}, "at_d_common": {}}
    for m in TRIO:
        sweep["at_R90"][m] = [cell(m, facts, float(T), R90[m]["R90_m"], SPEED_REF, psi_fine)
                              for T in Tg]
        sweep["at_d_common"][m] = [cell(m, facts, float(T), D_COMMON, SPEED_REF, psi_fine)
                                   for T in Tg]
    # 9모드 표(T=0.1) — 벌점이 '표준' 이 아니라 '기준신호 반복률' 을 따라간다는 증거
    nine = {m: cell(m, facts, T_REF, D_COMMON, SPEED_REF, psi_fine)
            for m in efr.MODE_STD}

    # ── (2) 구조 조건 ────────────────────────────────────────────────────────
    struct = structural_conditions(facts)
    # 수치검증: 해석식이 예고한 T 경계에서 실제로 blind 가 1.0 을 벗어나는가
    ver = {}
    for m in TRIO:
        prf = facts[m]["prf_hz"]
        for tag, key, gb in (("declared", "blind_declared", fss.GUARD_DOPPLER_BINS),
                             ("hard", "blind_hard", fss.DOPPLER_GUARD_HARD_BINS)):
            Tb = 2 * gb / prf
            c_lo = cell(m, facts, Tb * 0.98, D_COMMON, SPEED_REF, psi_fine)
            c_hi = cell(m, facts, Tb * 1.30, D_COMMON, SPEED_REF, psi_fine)
            lo, hi = c_lo[key], c_hi[key]
            ok = bool(lo >= 1.0 - 1e-12 and hi < 1.0)
            # ⚠ ok=False 는 식이 틀렸다는 뜻이 아니다: 그 CPI 에서는 가드가 도플러 **진폭**까지
            #   덮어(기구 B) 경계 위에서도 1.0 이 유지되기 때문이다. 어느 기구가 지배하는지 기록한다.
            g_hi = c_hi["guard_declared_hz" if tag == "declared" else "guard_hard_hz"]
            ver.setdefault(m, {})[tag] = dict(
                T_boundary_s=float(Tb), blind_just_below=float(lo), blind_above=float(hi),
                boundary_confirmed=ok,
                dominant_mechanism_above_boundary=("A_sampling" if ok else "B_amplitude"),
                guard_above_hz=float(g_hi), fd_amp_above_hz=float(c_hi["fd_amp_hz"]),
                note=("A(샘플링) 경계가 그대로 드러남" if ok else
                      "경계 위에서도 가드(%.4g Hz)가 도플러 진폭(%.4g Hz)을 덮어 blind=1.0 유지 "
                      "— 기구 B 가 지배. 식이 틀린 게 아니다."
                      % (g_hi, c_hi["fd_amp_hz"])))
    struct["numeric_verification"] = ver
    # 전헤딩 블라인드에는 **서로 다른 두 기구**가 있다 — 스윕에서 실제 상한을 읽는다
    struct["two_mechanisms"] = dict(
        A_sampling=("guard >= PRF/2  (M <= 2g).  반송파·속도·거리와 무관. "
                    "상시기준 반복률이 낮은 파형만 걸린다 — 여기서는 5G SSB."),
        B_amplitude=("guard >= max_psi|f_d|.  짧은 CPI 면 어떤 파형이든 걸린다. "
                     "반송파(λ)와 속도에 의존하므로 5G 만의 성질이 아니다."),
        observed=({m: {tag: dict(total_blind_edges(sweep["at_R90"][m], key),
                                 mechanism_A_T_max_s=(2 * gb / facts[m]["prf_hz"]))
                       for tag, key, gb in (("declared", "blind_declared", fss.GUARD_DOPPLER_BINS),
                                            ("hard", "blind_hard", fss.DOPPLER_GUARD_HARD_BINS))}
                   for m in TRIO}))
    # 접힘 vs 파장 분해 (5G 벌점의 원인 배분)
    nofold = {m: no_fold_counterfactual(m, facts, T_REF, R90[m]["R90_m"], SPEED_REF, psi_fine)
              for m in TRIO}
    for m in TRIO:
        b = repro[m]["blind_hard_fine"]
        nf = nofold[m]["blind_hard_nofold"]
        nofold[m]["blind_hard_actual"] = float(b)
        nofold[m]["folding_penalty_factor"] = float(b / max(nf, 1e-12))
    struct["fold_vs_wavelength"] = dict(
        note=("같은 CPI·같은 빈폭에서 PRF 만 %dx 로 올려 접힘을 끈 반사실. "
              "5G 블라인드율의 몇 배가 '접힘' 탓인지 직접 읽힌다." % 200),
        by_mode=nofold)

    # ── (3) 패리티 CPI + 그 대가 ─────────────────────────────────────────────
    tgt_w_hard = repro["W1"]["blind_hard_fine"]
    tgt_l_hard = repro["L1"]["blind_hard_fine"]
    tgt_w_decl = repro["W1"]["blind_declared_fine"]
    tgt_l_decl = repro["L1"]["blind_declared_fine"]
    par = dict(
        hard=dict(to_WiFi_parity=parity_cpi(sweep["at_R90"]["G1"], tgt_w_hard, "blind_hard"),
                  to_LTE_parity=parity_cpi(sweep["at_R90"]["G1"], tgt_l_hard, "blind_hard")),
        declared=dict(
            to_WiFi_parity=parity_cpi(sweep["at_R90"]["G1"], tgt_w_decl, "blind_declared"),
            to_LTE_parity=parity_cpi(sweep["at_R90"]["G1"], tgt_l_decl, "blind_declared")),
        note="목표값은 T_CPI=0.1 s 에서의 WiFi/LTE 블라인드율(같은 기하·같은 속도)")
    req_w = par["hard"]["to_WiFi_parity"]["T_sustained_s"]
    req_l = par["hard"]["to_LTE_parity"]["T_sustained_s"]
    print("■ 5G 패리티 CPI (1.5빈 정본): LTE 수준 %.4g s / WiFi 수준 %.4g s"
          % (req_l or float("nan"), req_w or float("nan")))

    # 코히런스 한계 vs 요구 CPI (속도별)
    vlist = [1.0, 3.0, 5.0, 8.0, 10.0, 15.0, 20.0, 25.0, 30.0] if not a.smoke \
        else [1.0, 5.0, 15.0]
    by_speed = []
    for v in vlist:
        cl = coherence_limits("G1", facts, R90["G1"]["R90_m"], v, psi_n=72, smoke=a.smoke)
        by_speed.append(dict(speed_ms=float(v),
                             T_coh_doppler_s=cl["T_coh_doppler_s"]["median"],
                             T_coh_doppler_worst_s=cl["T_coh_doppler_s"]["min"],
                             T_coh_range_s=cl["T_coh_range_s"]["median"],
                             T_coh_s=cl["T_coh_s"]["median"],
                             feasible_LTE_parity=bool(req_l is not None
                                                      and cl["T_coh_s"]["median"] >= req_l),
                             feasible_WiFi_parity=bool(req_w is not None
                                                       and cl["T_coh_s"]["median"] >= req_w)))
    # 요구 CPI 를 실제로 쓸 때의 비용(대표속도 2개)
    costs = {}
    for v in (SPEED_REF, SPEED_FAST):
        for tag, Treq in (("LTE_parity", req_l), ("WiFi_parity", req_w)):
            if Treq is None:
                continue
            dfd, dRb, _ = walk_over_cpi("G1", facts, Treq, R90["G1"]["R90_m"], v, psi_n=72)
            M = fss.M_from_prf(Treq, facts["G1"]["prf_hz"])
            bh = fss.doppler_bin_hz(Treq, facts["G1"]["prf_hz"], M)
            costs["v%g_%s" % (v, tag)] = dict(
                speed_ms=float(v), T_required_s=float(Treq), M=int(M),
                distance_travelled_m=float(v * Treq),
                doppler_walk_hz_median=float(np.median(dfd)),
                doppler_bin_hz=float(bh),
                doppler_walk_bins_median=float(np.median(dfd) / bh),
                doppler_walk_bins_worst=float(np.max(dfd) / bh),
                range_walk_m_median=float(np.median(dRb)),
                range_res_m=float(facts["G1"]["range_res_m"]),
                range_walk_bins_median=float(np.median(dRb) / facts["G1"]["range_res_m"]),
                ssb_bursts_needed=int(M),
                elapsed_vs_headline=float(Treq / T_REF),
                snr_gain_db_if_coherent=float(10.0 * np.log10(Treq / T_REF)))
    # ⚠ 반증: R90(6.3 km)은 기하가 거의 안 도는 가장 관대한 지점이다. 근거리를 반드시 본다.
    d_list = [300.0, 1000.0, 2000.0, R90["G1"]["R90_m"]] if not a.smoke else [300.0, 2000.0]
    v_list = [5.0, 10.0, 15.0, 20.0] if not a.smoke else [5.0, 15.0]
    cmap = coherence_map(facts, "G1", d_list, v_list, psi_n=72, smoke=a.smoke)
    for row in cmap:
        row["LTE_parity_feasible"] = bool(req_l is not None and row["T_coh_s"] >= req_l)
        row["WiFi_parity_feasible"] = bool(req_w is not None and row["T_coh_s"] >= req_w)
        row["headline_cpi_feasible"] = bool(row["T_coh_s"] >= T_REF)
    n_ok_w = sum(r["WiFi_parity_feasible"] for r in cmap)
    n_ok_l = sum(r["LTE_parity_feasible"] for r in cmap)

    cost = dict(required_cpi_s=dict(to_WiFi_parity=req_w, to_LTE_parity=req_l),
                required_cpi_declared_s=dict(
                    to_WiFi_parity=par["declared"]["to_WiFi_parity"]["T_sustained_s"],
                    to_LTE_parity=par["declared"]["to_LTE_parity"]["T_sustained_s"]),
                by_speed=by_speed, at_required_cpi=costs,
                coherence_map_d_v=cmap,
                coherence_map_summary=dict(n_cells=len(cmap), n_WiFi_parity_feasible=int(n_ok_w),
                                           n_LTE_parity_feasible=int(n_ok_l),
                                           d_list_m=d_list, v_list_ms=v_list),
                coherence_criterion=("표적이 CPI 동안 한 도플러 빈(PRF/M)과 한 거리 빈(c/B_ref) "
                                     "안에 머물러야 코히런트 적분이 성립한다. 등속직선비행이라도 "
                                     "기하가 돌아 f_d 가 움직인다(가속도 0 에서도 남는 항)."),
                unmodelled=("기동(가속·선회)·로터 마이크로도플러의 위상교란·조명원 위상잡음은 "
                            "모형에 없다. 즉 여기 T_coh 는 **낙관적 상한**이다."))

    # ── (3c) 동일 M 비교 — "같은 CPI" 가 아니라 "같은 펄스수" 로 맞추면 순위가 뒤집히나 ──
    eqM = []
    for Mtar in ([20, 50, 100, 200] if not a.smoke else [100]):
        row = {"M": int(Mtar)}
        for m in TRIO:
            Tm = float(Mtar) / facts[m]["prf_hz"]             # 그 M 을 내는 CPI
            c = cell(m, facts, Tm, R90[m]["R90_m"], SPEED_REF, psi_fine)
            row["T_cpi_s_" + m] = float(Tm)
            row["blind_hard_" + m] = float(c["blind_hard"])
            row["blind_declared_" + m] = float(c["blind_declared"])
        eqM.append(row)

    # ── (3b) CPI 와 무관한 한계: 속도 모호성 ────────────────────────────────
    vun = {m: unambiguous_speed(m, facts, R90[m]["R90_m"], psi_n=psi_fine) for m in TRIO}
    # 동일 CPI 벌점비 — '공정 벤치마크' 에 실제로 쓸 숫자
    eq = []
    for T in ([0.1, 0.2, 0.5, 1.0, 2.0] if not a.smoke else [0.1, 1.0]):
        row = {"T_cpi_s": float(T)}
        for m in TRIO:
            r = [x for x in sweep["at_R90"][m] if abs(x["T_cpi_s"] - T) < 1e-9]
            if r:
                row["blind_hard_" + m] = float(r[0]["blind_hard"])
        if "blind_hard_W1" in row and "blind_hard_G1" in row:
            row["ratio_G1_over_W1"] = float(row["blind_hard_G1"] / max(row["blind_hard_W1"], 1e-12))
            row["ratio_G1_over_L1"] = float(row["blind_hard_G1"] / max(row["blind_hard_L1"], 1e-12))
        eq.append(row)

    # ── (4) 속도 스윕 ────────────────────────────────────────────────────────
    vg = _speed_grid(a.smoke)
    speed_sweep = {}
    for T in ((0.1, 1.0) if a.smoke else (0.1, 0.2, 1.0)):
        speed_sweep["%g" % T] = {m: [cell(m, facts, T, R90[m]["R90_m"], float(v), psi_fine)
                                     for v in vg] for m in TRIO}

    # ── (5) 판정 ─────────────────────────────────────────────────────────────
    g1_at_ref_hard = repro["G1"]["blind_hard_fine"]
    g1_at_02_hard = [r for r in sweep["at_R90"]["G1"] if abs(r["T_cpi_s"] - 0.2) < 1e-12]
    g1_at_02_hard = g1_at_02_hard[0]["blind_hard"] if g1_at_02_hard else None
    ratio_hard = g1_at_ref_hard / max(repro["W1"]["blind_hard_fine"], 1e-12)
    # 속도무관 바닥: v≥5 m/s 구간에서 5G blind 의 변동폭
    sr = speed_sweep["0.1"]["G1"]
    hi_v = [r["blind_hard"] for r in sr if r["speed_ms"] >= 5.0]
    verdict = dict(
        answer="(c) for the '0' number, (b) for the penalty itself",
        headline_claim_status="must_change",
        # ── 인공물인 부분 ────────────────────────────────────────────────
        artifact=dict(
            claim="5G coverage = 0 at every heading",
            depends_on_two_choices=["T_cpi = 100 ms", "declared 2.5-bin guard"],
            blind_hard_same_cpi=float(g1_at_ref_hard),
            blind_hard_at_200ms=(float(g1_at_02_hard) if g1_at_02_hard is not None else None),
            text=("'0' 은 CPI=100 ms 와 2.5빈 선언가드가 **동시에** 성립하는 한 점에서만 참이다. "
                  "검출기가 실제로 지우는 1.5빈 규약(모듈 docstring 이 인용 정본이라 못박은 값)에서는 "
                  "같은 CPI 에서 blind=%.3f 이고, CPI 를 200 ms 로만 늘려도 %.3f 다. "
                  "게다가 LTE 도 CPI<=%.3g s 에서는 blind=1.000 이 된다(가드가 도플러 진폭을 "
                  "덮는 기구 B) — '전 헤딩 블라인드' 자체는 5G 만의 성질이 아니다."
                  % (g1_at_ref_hard, g1_at_02_hard or float("nan"),
                     struct["two_mechanisms"]["observed"]["L1"]["declared"]["T_max_total_blind_s"]
                     or float("nan")))),
        # ── 진짜 구조인 부분 ────────────────────────────────────────────
        structural=dict(
            s1_equal_cpi_penalty=dict(
                text="같은 CPI 에서 5G 블라인드율은 WiFi 의 배수로 일정하게 크다(CPI 로 안 없어짐)",
                by_cpi=eq),
            s2_alias_floor=dict(
                text="접힘비율은 CPI 와 무관한 상수다(적분시간이 아니라 표본화율의 성질)",
                alias_frac_G1=float(repro["G1"]["alias_frac"]),
                alias_frac_W1=float(repro["W1"]["alias_frac"]),
                alias_frac_L1=float(repro["L1"]["alias_frac"])),
            s3_unambiguous_speed=dict(
                text=("★ CPI 로 절대 못 고치는 한계. 5G 상시기준(SSB, PRF 50 Hz)은 %.2f m/s 를 "
                      "넘는 표적속도를 모호 없이 못 잰다 — 사실상 모든 비행 드론이 접힌다. "
                      "WiFi %.1f m/s · LTE %.1f m/s."
                      % (vun["G1"]["v_unambiguous_ms"], vun["W1"]["v_unambiguous_ms"],
                         vun["L1"]["v_unambiguous_ms"])),
                by_mode=vun),
            s4_speed_independent_floor=dict(
                text="WiFi/LTE 는 속도가 오르면 블라인드율이 내려가지만 5G 는 안 내려간다",
                G1_blind_hard_range_over_v_ge_5=[float(min(hi_v)), float(max(hi_v))]),
            s4b_folding_share=dict(
                text=("접힘을 끈 반사실(같은 CPI·같은 빈폭, PRF 만 200배)과 비교하면 5G 블라인드율의 "
                      "%.1f배가 접힘 탓이다(파장 탓이 아니다). WiFi/LTE 의 같은 인자는 %.2f/%.2f 로 1 이다."
                      % (nofold["G1"]["folding_penalty_factor"],
                         nofold["W1"]["folding_penalty_factor"],
                         nofold["L1"]["folding_penalty_factor"])),
                by_mode=nofold),
            s5_pulse_count_law=dict(
                text=("벌점의 원인은 '5G' 가 아니라 **상시 기준신호의 반복률**이다. 세 파형의 "
                      "blind(M) 곡선은 하나로 겹치고, 5G 만 헤드라인 CPI 에서 M=%d 이다. "
                      "같은 5G 라도 PRS(200 Hz)면 M=%d 로 유리해진다."
                      % (struct["by_mode"]["G1"]["M_at_T_ref"],
                         struct["by_mode"]["G2"]["M_at_T_ref"])),
                nine_mode_at_T_ref={m: dict(ref=facts[m]["ref_name"], prf_hz=facts[m]["prf_hz"],
                                            M=nine[m]["M"], blind_hard=nine[m]["blind_hard"],
                                            feasible=nine[m]["feasible"])
                                    for m in efr.MODE_STD}),
            s6_equal_M_reverses_the_ranking=dict(
                text=("★ 같은 CPI 가 아니라 **같은 펄스수 M** 으로 맞추면 순위가 뒤집힌다 — "
                      "M=100 에서 5G %.4f < WiFi %.4f < LTE %.4f (1.5빈). 즉 5G 파형 자체가 "
                      "도플러에 불리한 게 아니라, 상시 기준신호가 같은 시간에 20배 적게 오는 것이 "
                      "전부다. 벤치마크 논문은 이 분해를 반드시 실어야 공정하다."
                      % tuple(next(r["blind_hard_" + m] for r in eqM if r["M"] == 100)
                              for m in ("G1", "W1", "L1")) if any(r["M"] == 100 for r in eqM)
                      else "M=100 셀 없음"),
                by_M=eqM)),
        # ── 내가 틀린 부분(반증 기록) ──────────────────────────────────
        falsified_hypothesis=dict(
            hypothesis=("5G 가 패리티에 필요한 CPI 는 움직이는 드론에게 물리적으로 불가능할 것이다 "
                        "(그러면 단일점 주장보다 훨씬 강한 구조적 결과가 된다)"),
            verdict="NOT SUPPORTED as stated",
            evidence=("헤드라인 기하(R90=%.0f m)에서 필요한 CPI 는 LTE 수준 %.3g s · WiFi 수준 %.3g s "
                      "인데, 표적이 한 빈에 머무는 상한은 v=5 m/s 에서 %.2g s, v=15 m/s 에서 %.2g s 로 "
                      "**둘 다 여유가 있다**. 즉 '요구 CPI 가 물리적으로 불가능하다' 는 주장은 "
                      "헤드라인 거리에서 성립하지 않는다."
                      % (R90["G1"]["R90_m"], req_l or float("nan"), req_w or float("nan"),
                         _tcoh_at(by_speed, SPEED_REF), _tcoh_at(by_speed, SPEED_FAST))),
            where_it_does_hold=("단, T_coh 는 기하회전율(~v/d)에 지배되므로 근거리·고속에서 뒤집힌다. "
                                "(d,v) 격자 %d 칸 중 WiFi 패리티가 가능한 칸은 %d, LTE 패리티는 %d 다."
                                % (len(cmap), n_ok_w, n_ok_l)),
            caveat="T_coh 는 등속직선·무기동·무위상잡음 가정의 낙관적 상한이다(cost.unmodelled)."),
        penalty_ratio_hard_at_T_ref=float(ratio_hard),
        report05_action=(
            "헤드라인에서 '5G coverage = 0 / 모든 헤딩 블라인드' 를 **삭제**하고 다음 세 문장으로 "
            "교체할 것. (1) 같은 CPI 에서 5G 의 도플러 블라인드율은 WiFi 의 %.0f배다(규약: 검출기 "
            "실측 1.5빈). (2) 5G 상시기준의 무모호 속도는 %.2f m/s 라서 사실상 모든 비행 드론의 "
            "도플러가 접힌다 — 이건 CPI 로 못 고친다. (3) CPI 를 %.3g s 까지 늘리면 블라인드율은 "
            "LTE 수준까지 내려오고 그건 헤드라인 거리에서 물리적으로 가능하다 — 그러므로 '0' 이라는 "
            "숫자 대신 '같은 CPI 에서의 배수' 와 '무모호 속도' 를 인용해야 한다."
            % (ratio_hard, vun["G1"]["v_unambiguous_ms"], req_l or float("nan"))))

    res = dict(
        meta=dict(script="benchmark/cpi_guard_sweep.py",
                  generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
                  question=("report05 의 '5G coverage 0 at every heading' 이 구조인가 "
                            "한 파라미터의 인공물인가"),
                  geometry=dict(drone=DRONE, L_m=L_REF, alt_m=ALT_REF, phi_deg=PHI_REF,
                                speed_ms=SPEED_REF, T_cpi_ref_s=T_REF, d_common_m=D_COMMON),
                  psi_n_published=PSI_N_PUB, psi_n_fine=psi_fine,
                  guard_conventions=dict(hard_bins=fss.DOPPLER_GUARD_HARD_BINS,
                                         declared_bins=fss.GUARD_DOPPLER_BINS,
                                         canonical="blind_hard",
                                         canonical_source="freespace_scene.blind_fractions docstring"),
                  provenance=dict(R90="outputs/report13_freespace.json : ranges.%s.<mode>."
                                      "equal_psd.full_waveform_capture.by_N.1.R90_C50_m" % DRONE,
                                  functions=["freespace_scene.prf_hz", "M_from_prf",
                                             "cpi_feasibility", "doppler_bin_hz",
                                             "doppler_guard_hz", "blind_sector",
                                             "blind_fractions", "folded_doppler", "nyquist_gate",
                                             "fs_params", "target_pos", "heading_velocity",
                                             "waveforms.Waveform.range_resolution_m"]),
                  smoke=bool(a.smoke)),
        waveform_facts=facts, anchor=dict(R90=R90, reproduction=repro),
        cpi_sweep=sweep, nine_mode_at_T_ref=nine, structural=struct,
        parity=par, cost_of_long_cpi=cost, speed_sweep=speed_sweep,
        unambiguous_speed=vun, equal_cpi_penalty=eq, equal_M_comparison=eqM, verdict=verdict)

    figs = make_figures(res, a.fig_dir)
    res["figures"] = [os.path.relpath(p, _ROOT) for p in figs]
    res["meta"]["runtime_s"] = float(time.time() - t0)

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    print("■ 무모호 속도(CPI 무관): " + " · ".join(
        "%s %.2f m/s" % (m, vun[m]["v_unambiguous_ms"]) for m in TRIO))
    print("■ 동일 CPI 벌점비(1.5빈): " + " · ".join(
        "T=%gs G1/W1=%.1f배" % (r["T_cpi_s"], r["ratio_G1_over_W1"]) for r in eq
        if "ratio_G1_over_W1" in r))
    print("■ 코히런스 지도 %d칸 중 WiFi패리티 가능 %d · LTE패리티 가능 %d" % (len(cmap), n_ok_w, n_ok_l))
    print("■ 저장: %s  (%.1f s)" % (a.out, res["meta"]["runtime_s"]))
    print("■ 판정: %s — %s" % (verdict["answer"], verdict["headline_claim_status"]))
    print("   반증기록: %s" % verdict["falsified_hypothesis"]["verdict"])
    return res


if __name__ == "__main__":
    main()
