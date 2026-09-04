# -*- coding: utf-8 -*-
"""p3_validation_v2.py — ⭐⭐ v2(사진 실측) 메쉬 σ 를 문헌 실측과 대조 + 구판 대 신판.

구판 benchmark/p3_validation.py 와 **같은 자**를 쓴다:
  · 우리 el=0 ↔ Yuan θ90 **실측곡선** (고도·통계규약·추정량이 모두 정합인 유일한 대조)
  · 우리 el=0 ↔ Yuan θ90 모형(0.315, −16.15)
  · 우리 el=0 ↔ Das(0.21, −19.19)  ⚠ 고도 미정합
  · 레벨오차(밴드중심) · 기울기오차 · 유의성(σ) · 잔차 추세
  · 우리 대역(1.8~6 GHz) 별도 — LTE 1.843 · 5G 3.5 · WiFi 5.21 GHz
  · 부분대역 적합(1.8~6 / 6~18.2)
그리고 **구판 대 신판**(레벨 −4.91 / 기울기 0.420 / 자유도 205 가 얼마가 됐나)과
**큐브·박스 대조군 재실행**을 덧붙인다.

⚠ 구판 outputs/p3_ours.json · outputs/p3_validation.json 은 **읽기만 한다**.

실행:  PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/p3_validation_v2.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "benchmark"))
os.environ.setdefault("SIONNA2_CPU", "1")

OURS2 = os.environ.get("P3_OURS_V2", os.path.join(ROOT, "outputs", "p3_ours_v2.json"))
OURS1 = os.path.join(ROOT, "outputs", "p3_ours.json")
VAL1 = os.path.join(ROOT, "outputs", "p3_validation.json")
CTL2 = os.path.join(ROOT, "outputs", "p3_control_v2.json")
OUT = os.path.join(ROOT, "outputs", "p3_validation_v2.json")
FIG = os.path.join(ROOT, "outputs", "figs", "p3_validation_v2.png")

import sigma_anchor as SA                                             # noqa: E402
from verify_comparability_yuan import extract as yuan_extract, pooled_linear   # noqa: E402
from p3_validation import _fit, _fit_se, das_offset_db, _az_window_control     # noqa: E402

BAND = (1.8, 18.2)
COMM = {"LTE 1.843 GHz": 1.843, "5G 3.5 GHz": 3.5, "WiFi 5.21 GHz": 5.21}
FC = 10.0

# Okabe–Ito (색각이상 안전) 고정 순서
CBLUE, CORANGE, CGREEN, CVERM, CPURPLE, CSKY, CBLACK = (
    "#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#111111")


def load(path):
    D = json.load(open(path))
    el0 = D["aspects"]["el0"]["freq"]
    f = np.array(sorted(float(k) for k in el0))
    key = {float(k): k for k in el0}
    mu = np.array([el0[key[x]]["mu_dbsm"] for x in f])
    eps = np.array([el0[key[x]]["eps_db"] for x in f])
    sig = {float(x): np.array(el0[key[x]]["sigma_dbsm_az"]) for x in f}
    return D, f, mu, eps, sig


def score_against(f, mu, fy, my, eps=None, cv=None):
    """실측곡선(fy,my) 기준 채점 — p3_attack Q5 와 같은 자.

    ⭐ ε(방위산포)까지 함께 낸다. p3_attack 이 찾은 결론이 '레벨은 판별력이 없고 ε 만 강하다'
      였기 때문이다 — 레벨만 보면 부피를 맞춘 구가 우리보다 가깝다.
      ⚠**«모수 0개» 가 아니다**(2026-09-04) — **구의 부피를 무엇으로 잡는가가 자유 매개변수**다. +0.96 dB 는 «논문표기 상자와 같은 부피» 판이고, **메쉬 부피와 같은 구는 −4.47 dB 로 우리(−3.30)보다 나쁘다**(편 27). 부피 규약을 바꾸면 결론이 뒤집히므로 «구가 이긴다» 를 그 자체로 인용하지 않는다."""
    f = np.asarray(f, float)
    r = np.asarray(mu, float) - np.interp(f, fy, my)
    a, b, _, _ = _fit(f, mu)
    out = dict(level_err_db=float(r.mean()), rms_db=float(np.sqrt((r ** 2).mean())),
               shape_std_after_level_removed_db=float(r.std(ddof=1)),
               slope_db_per_ghz=float(a), intercept_dbsm=float(b))
    if eps is not None:
        e = np.asarray(eps, float)
        das_eps = SA.DAS["table3"]["phantom3"][0][2] * f + SA.DAS["table3"]["phantom3"][0][3]
        out["eps_mean_db"] = float(e.mean())
        out["eps_err_vs_das_db"] = float(e.mean() - das_eps.mean())
    if cv is not None:
        out["cv_amp_mean"] = float(np.mean(cv))
    return out


def main():
    D2, f, mu, eps, sig_az = load(OURS2)
    D1, f1, mu1, eps1, sig1 = load(OURS1)
    V1 = json.load(open(VAL1))
    a_das, b_das, c_das, d_das = SA.DAS["table3"]["phantom3"][0]
    a_y90, b_y90, c_y90, d_y90 = SA.YUAN["abcd"][90]

    curves, chk = yuan_extract()
    fy90_raw, my90_raw = curves[90]
    fy90, my90 = fy90_raw[:-1], my90_raw[:-1]          # 폴리라인 닫힘 아티팩트 1점 절단
    a_c90, b_c90, r2_c90, _ = _fit(fy90, my90)
    my_at = np.interp(f, fy90, my90)                  # 우리 주파수에서의 실측곡선
    inb = (f >= fy90.min()) & (f <= fy90.max())

    fg = np.linspace(max(fy90.min(), curves[0][0].min(), curves[180][0].min()),
                     min(fy90.max(), curves[0][0].max(), curves[180][0].max()), 1200)
    pool = pooled_linear(curves, fg)
    a_pool, b_pool, r2_pool, _ = _fit(fg, pool)

    # ── 1. 기울기 ─────────────────────────────────────────────────────────
    a_o, b_o, r2_o, rmse_o = _fit(f, mu)
    _, _, se_o, _ = _fit_se(f, mu)
    a_sub, b_sub, r2_sub, _ = _fit(f, my_at)
    loo = [float(np.polyfit(np.delete(f, i), np.delete(mu, i), 1)[0]) for i in range(f.size)]
    ff = np.linspace(*BAND, 400)
    a_das_eff = {k: _fit(ff, a_das * ff + b_das + das_offset_db(ff, k))[0]
                 for k in ("none", "exponential", "lognormal")}

    slope = dict(
        ours_el0_full_band=dict(a=a_o, b=b_o, R2=r2_o, rmse_db=rmse_o, n=int(f.size),
                                se_a=se_o, ci95=[a_o - 1.96 * se_o, a_o + 1.96 * se_o]),
        ours_slope_robustness=dict(
            leave_one_out_min=min(loo), leave_one_out_max=max(loo),
            drop_both_endpoints=float(np.polyfit(f[1:-1], mu[1:-1], 1)[0]),
            strict_overlap_in_curve=float(_fit(f[inb], mu[inb])[0]),
            note=("⭐ v2 는 61점이라 끝점 하나의 지렛대가 v1(21점)보다 작다. "
                  "끝점 두 개를 빼도 기울기가 얼마나 움직이는지가 그 자다.")),
        significance=dict(
            z_vs_das_0p21=(a_o - a_das) / se_o,
            z_vs_yuan_theta90_0p315=(a_o - a_y90) / se_o,
            z_vs_yuan_curve_resampled=(a_o - a_sub) / se_o,
            z_vs_yuan_curve_dense=(a_o - a_c90) / se_o),
        das_published=dict(a=a_das, b=b_das, band=list(BAND)),
        das_effective_slope_after_convention=a_das_eff,
        yuan_theta90_published=dict(a=a_y90, b=b_y90, band=list(SA.YUAN["band_ghz"])),
        yuan_theta90_curve_refit=dict(a=a_c90, b=b_c90, R2=r2_c90, n=int(fy90.size)),
        yuan_curve_refit_at_our_freqs=dict(a=a_sub, b=b_sub, R2=r2_sub, n=int(f.size)),
        yuan_elevation_pooled_curve_refit=dict(a=a_pool, b=b_pool, R2=r2_pool),
        ratios=dict(ours_over_das=a_o / a_das, ours_over_yuan_theta90=a_o / a_y90,
                    ours_over_yuan_curve_dense=a_o / a_c90),
        differences_db_per_ghz=dict(ours_minus_das=a_o - a_das,
                                    ours_minus_yuan_theta90=a_o - a_y90,
                                    ours_minus_yuan_curve_dense=a_o - a_c90),
        elevation_matched_comparand="yuan_theta90 (방위면) = 우리 el=0. Das 는 고도풀링이라 정합 아님.",
        subband=dict(ours=D2["subband_fits"]["by_aspect"]["el0"],
                     yuan_theta90_curve={f"{lo}-{hi} GHz": _fit(fy90[(fy90 >= lo) & (fy90 <= hi)],
                                                                my90[(fy90 >= lo) & (fy90 <= hi)])[0]
                                         for lo, hi in [(1.8, 6.0), (6.0, 18.2), (10.0, 18.2)]},
                     note="⭐ 전대역 직선은 우리도 측정도 곡선을 억지로 편 것이다."),
    )

    # ── 2. 레벨 ───────────────────────────────────────────────────────────
    def das_mu(x, kind):
        return a_das * np.asarray(x, float) + b_das + das_offset_db(x, kind)

    def yuan90_mu(x):
        return a_y90 * np.asarray(x, float) + b_y90

    def ours_mu(x):
        return a_o * np.asarray(x, float) + b_o

    lvl_at = {}
    for name, x in [("band_center_10.0GHz", FC)] + list(COMM.items()):
        row = dict(ours=float(ours_mu(x)), ours_measured_point=float(np.interp(x, f, mu)),
                   das_as_published=float(das_mu(x, "none")),
                   das_exponential=float(das_mu(x, "exponential")),
                   das_lognormal=float(das_mu(x, "lognormal")),
                   yuan_theta90_model=float(yuan90_mu(x)))
        if fy90.min() <= x <= fy90.max():
            row["yuan_theta90_measured_curve"] = float(np.interp(x, fy90, my90))
            row["yuan_elevation_pooled_curve"] = float(np.interp(x, fg, pool))
        row["ours_minus_das_exponential"] = row["ours"] - row["das_exponential"]
        row["ours_minus_das_lognormal"] = row["ours"] - row["das_lognormal"]
        row["ours_minus_das_as_published"] = row["ours"] - row["das_as_published"]
        row["ours_minus_yuan_theta90"] = row["ours"] - row["yuan_theta90_model"]
        if "yuan_theta90_measured_curve" in row:
            row["ours_minus_yuan_theta90_curve"] = row["ours_measured_point"] - row["yuan_theta90_measured_curve"]
        lvl_at[name] = row

    band_mean = {("das_" + k): float(np.mean(ours_mu(ff) - das_mu(ff, k)))
                 for k in ("none", "exponential", "lognormal")}
    band_mean["yuan_theta90"] = float(np.mean(ours_mu(ff) - yuan90_mu(ff)))

    level = dict(
        intercept_b=dict(ours=b_o, das=b_das, yuan_theta90=b_y90,
                         warning="b 는 밴드 밖 외삽점이다 — 레벨은 at_frequency 를 쓸 것."),
        at_frequency=lvl_at, band_mean_offset_db=band_mean,
        convention_branches=dict(
            exponential_db=float(SA.LOG_TO_LIN_EXPONENTIAL_DB),
            lognormal_db_at_10GHz=float(das_offset_db(FC, "lognormal")),
            rule="A8 — 두 갈래를 언제나 함께 들고 다닌다."),
        our_convention_measured=D2["distribution_summary"]["linear_minus_dB_domain_mean_db"],
    )

    # ── 3. 잔차 ───────────────────────────────────────────────────────────
    res = {}
    for name, ref in [("vs_das_exponential", das_mu(f, "exponential")),
                      ("vs_das_lognormal", das_mu(f, "lognormal")),
                      ("vs_das_as_published", das_mu(f, "none")),
                      ("vs_yuan_theta90_model", yuan90_mu(f))]:
        r = mu - ref
        res[name] = dict(mean_db=float(r.mean()), rms_db=float(np.sqrt((r ** 2).mean())),
                         worst_freq_ghz=float(f[np.argmax(np.abs(r))]),
                         worst_db=float(r[np.argmax(np.abs(r))]),
                         low_band_mean_db=float(r[f <= 6.0].mean()),
                         high_band_mean_db=float(r[f >= 12.0].mean()),
                         trend_db_per_ghz=float(np.polyfit(f, r, 1)[0]))
    rc = mu - my_at
    a_rc, _, se_rc, _ = _fit_se(f, rc)
    res["vs_yuan_theta90_measured_curve"] = dict(
        f_ghz=[float(x) for x in f], resid_db=[float(x) for x in rc],
        mean_db=float(rc.mean()), rms_db=float(np.sqrt((rc ** 2).mean())),
        std_db=float(rc.std(ddof=1)),
        worst_freq_ghz=float(f[np.argmax(np.abs(rc))]), worst_db=float(rc[np.argmax(np.abs(rc))]),
        best_freq_ghz=float(f[np.argmin(np.abs(rc))]), best_db=float(rc[np.argmin(np.abs(rc))]),
        low_band_mean_db=float(rc[f <= 6.0].mean()), high_band_mean_db=float(rc[f >= 12.0].mean()),
        low_minus_high_db=float(rc[f <= 6.0].mean() - rc[f >= 12.0].mean()),
        trend_db_per_ghz=a_rc, trend_se=se_rc, trend_sigma=a_rc / se_rc,
        strict_overlap=dict(n=int(inb.sum()), mean_db=float(rc[inb].mean()),
                            trend_db_per_ghz=float(np.polyfit(f[inb], rc[inb], 1)[0])),
        note=("⭐ 고도(θ90=el0)·통계규약(둘 다 방위 선형평균)·추정량(둘 다 단일주파수)이 "
              "모두 정합인 **유일한** 대조. 복원구간 밖 끝점은 가장자리 값으로 클램프."))

    # ── 4. 우리 대역 (1.8~6 GHz) ──────────────────────────────────────────
    lo = f <= 6.0
    a_o_lo, b_o_lo, _, _ = _fit(f[lo], mu[lo])
    fw = (fy90 >= 1.8) & (fy90 <= 6.0)
    a_mc_lo, b_mc_lo, _, _ = _fit(fy90[fw], my90[fw])
    r_lo = mu[lo] - my_at[lo]
    lo1 = f1 <= 6.0
    a_o_lo_v1 = float(_fit(f1[lo1], mu1[lo1])[0])
    r_lo_v1 = mu1[lo1] - np.interp(f1[lo1], fy90, my90)
    opband = dict(
        band_ghz=[1.8, 6.0], n_ours=int(lo.sum()),
        ours=dict(a=a_o_lo, b=b_o_lo),
        measured_theta90_curve_dense=dict(a=a_mc_lo, b=b_mc_lo, n=int(fw.sum())),
        level_error_db=dict(mean=float(r_lo.mean()), at_low=float(r_lo[0]), at_high=float(r_lo[-1]),
                            per_freq=[float(x) for x in r_lo]),
        slope_error_db_per_ghz=a_o_lo - a_mc_lo, slope_ratio=a_o_lo / a_mc_lo,
        comm_band_mu=dict(
            ours={k: float(np.interp(v, f, mu)) for k, v in COMM.items()},
            ours_v1={k: float(np.interp(v, f1, mu1)) for k, v in COMM.items()},
            measured_theta90_curve={k: float(np.interp(v, fy90, my90)) for k, v in COMM.items()},
            yuan_theta90_model={k: float(yuan90_mu(v)) for k, v in COMM.items()},
            das_exponential={k: float(das_mu(v, "exponential")) for k, v in COMM.items()},
            ours_minus_curve_db={k: float(np.interp(v, f, mu) - np.interp(v, fy90, my90))
                                 for k, v in COMM.items()},
            ours_v1_minus_curve_db={k: float(np.interp(v, f1, mu1) - np.interp(v, fy90, my90))
                                    for k, v in COMM.items()}),
        v1_comparison=dict(a_v1=a_o_lo_v1, a_v2=a_o_lo,
                           level_err_mean_v1=float(r_lo_v1.mean()),
                           level_err_mean_v2=float(r_lo.mean())),
    )

    # ── 5. 구판 대 신판 ───────────────────────────────────────────────────
    v1_lvl = V1["residual"]["vs_yuan_theta90_measured_curve"]["mean_db"]
    v1_a = V1["slope"]["ours_el0_full_band"]["a"]
    v1_se = V1["slope"]["ours_el0_full_band"]["se_a"]
    # 같은 21주파수에서의 짝비교 (v2 61점 격자는 v1 21점을 정확히 포함)
    idx = [int(np.argmin(np.abs(f - x))) for x in f1]
    paired_ok = bool(np.max(np.abs(f[idx] - f1)) < 1e-6)
    d_pair = mu[idx] - mu1 if paired_ok else None
    a_v2_on_v1grid = float(_fit(f[idx], mu[idx])[0]) if paired_ok else None
    se_v2_on_v1grid = float(_fit_se(f[idx], mu[idx])[2]) if paired_ok else None
    r1 = mu1 - np.interp(f1, fy90, my90)

    dof = dict(
        rule="p3_attack.json Q3 와 **같은 규칙** — '이 메쉬의 σ 를 바꾸는데 Phantom 3 관측으로 고정되지 않은 수'.",
        v1=dict(constrained=13, tier_A_p3_specific_decisions=32,
                tier_B_inherited_no_p3_evidence=160, tier_C_engine_knobs=13, total_free=205,
                ratio_free_to_constrained=15.8),
        v2=dict(constrained=13 + 56,
                constrained_note=("구판 13 + outputs/p3_mesh_v2_measurements.json 의 등급부여 상수 "
                                  "56개(M 53 · D 3). 145장 사진·DJI 정투상 4면도·iFixit 분해에서 "
                                  "픽셀 실측한 것들이다."),
                tier_A_p3_specific_decisions=27,
                tier_A_note=("구판이 열거한 14개 예시 중 5개가 실측으로 해소됐다 — 짐벌 깊이·짐벌 x·"
                             "짐벌 z 앵커·마그네슘 판(제거, 실측 차폐 비디오 모듈로 대체)·모터 "
                             "지름/높이. ⚠ 나머지 18개는 구판이 열거하지 않아 재감사하지 못했다 "
                             "— 그대로 자유로 센다(보수적)."),
                tier_B_inherited_no_p3_evidence=81,
                tier_B_note="p3_mesh_v2_measurements.json still_borrowed.total = 81 (구판 160)",
                tier_C_engine_knobs=13, tier_C_note="엔진·대조 손잡이는 그대로다.",
                total_free=27 + 81 + 13,
                ratio_free_to_constrained=round((27 + 81 + 13) / (13 + 56), 2)),
        reading=("자유도는 205 → 121 로 줄고 고정된 관측은 13 → 69 로 늘었다. 자유/고정 비는 "
                 "15.8 → 1.75. ⚠ 이것은 '맞았다' 는 증거가 아니라 **맞출 수 있는 손잡이가 "
                 "줄었다** 는 뜻이다."),
    )

    v1v2 = dict(
        level_db=dict(v1=v1_lvl, v2=res["vs_yuan_theta90_measured_curve"]["mean_db"],
                      change=res["vs_yuan_theta90_measured_curve"]["mean_db"] - v1_lvl,
                      improved=bool(abs(res["vs_yuan_theta90_measured_curve"]["mean_db"]) < abs(v1_lvl)),
                      comparand="Yuan θ90 복원 실측곡선 기준 밴드평균 잔차"),
        slope_db_per_ghz=dict(v1=v1_a, v1_se=v1_se, v2=a_o, v2_se=se_o,
                              v2_on_v1_21pt_grid=a_v2_on_v1grid, v2_se_on_v1_grid=se_v2_on_v1grid,
                              measured_comparand_dense=a_c90, published_comparand=a_y90,
                              err_v1=v1_a - a_c90, err_v2=a_o - a_c90,
                              improved=bool(abs(a_o - a_c90) < abs(v1_a - a_c90))),
        rms_db=dict(v1=float(np.sqrt((r1 ** 2).mean())),
                    v2=res["vs_yuan_theta90_measured_curve"]["rms_db"]),
        shape_std_db=dict(v1=float(r1.std(ddof=1)),
                          v2=res["vs_yuan_theta90_measured_curve"]["std_db"],
                          note="레벨을 뺀 뒤 남는 μ(f) 잔물결의 표준편차 — 형상이 만드는 구조."),
        paired_at_21_shared_freqs=dict(
            ok=paired_ok,
            mean_dmu_db=float(d_pair.mean()) if paired_ok else None,
            min_dmu_db=float(d_pair.min()) if paired_ok else None,
            max_dmu_db=float(d_pair.max()) if paired_ok else None,
            dmu_low_band_db=float(d_pair[f1 <= 6.0].mean()) if paired_ok else None,
            dmu_high_band_db=float(d_pair[f1 >= 12.0].mean()) if paired_ok else None,
            per_freq={f"{x:.3f}": float(d) for x, d in zip(f1, d_pair)} if paired_ok else None,
            note=("v2 61점 격자는 v1 21점 격자를 매 3번째 점으로 정확히 포함한다 → "
                  "**같은 주파수에서 메쉬만 바꾼 순수 효과**다.")),
        eps_db=dict(v1_mean=float(eps1.mean()), v2_mean=float(eps.mean()),
                    das_mean=float((c_das * f + d_das).mean()),
                    err_v1=float(eps1.mean() - (c_das * f1 + d_das).mean()),
                    err_v2=float(eps.mean() - (c_das * f + d_das).mean())),
        mesh=dict(v1_n_tri=28160, v2_n_tri=D2["meta"]["mesh"]["n_tri"],
                  v2_sha256_16=D2["meta"]["mesh"]["sha256_16"],
                  silhouette_iou_pct_of_ceiling=dict(old=77.9, new=86.9)),
        degrees_of_freedom=dof,
        sampling=dict(v1_n_freq=int(f1.size), v2_n_freq=int(f.size),
                      v1_se_a=v1_se, v2_se_a=se_o,
                      note="주파수를 21→61 로 조밀하게 깔면 기울기 SE 가 줄어 끝점 지렛대가 약해진다."),
    )

    # ── 6. 대조군 ─────────────────────────────────────────────────────────
    controls = None
    if os.path.exists(CTL2):
        C = json.load(open(CTL2))
        def _cv(sg, ff):
            return [float(np.std(np.sqrt(10 ** (sg[x] / 10.0))) /
                          np.mean(np.sqrt(10 ** (sg[x] / 10.0)))) for x in ff]

        rows = {"ours_phantom3_mesh_v2": dict(
            what=f"우리 P3 메쉬 v2 ({D2['meta']['mesh']['n_tri']:,} 삼각형, 사진 실측)",
            n_freq=int(f.size),
            **score_against(f, mu, fy90, my90, eps, _cv(sig_az, f)))}
        rows["ours_phantom3_mesh_v1"] = dict(
            what="우리 P3 메쉬 v1 (phantom4 형상표 상속, 28,160 삼각형)",
            n_freq=int(f1.size),
            **score_against(f1, mu1, fy90, my90, eps1, _cv(sig1, f1)))
        for k, v in C["controls"].items():
            fc_ = np.array(v["f_ghz"]); mc = np.array(v["mu_dbsm"])
            rows[k] = dict(what=v["desc"], n_freq=int(fc_.size),
                           **score_against(fc_, mc, fy90, my90, v["eps_db"], v["cv_amp"]))
        best_abs = min(rows, key=lambda k: abs(rows[k]["level_err_db"]))
        cube_key = "cube_vol_v2"
        controls = dict(
            protocol=C["_meta"]["kernel"], scoring="Yuan θ90 복원 실측곡선 기준 밴드평균 잔차",
            table=rows,
            kernel_crosscheck=dict(
                cube_vol_v1_level_err_db=rows.get("cube_vol_v1", {}).get("level_err_db"),
                p3_attack_reported_db=6.94,
                delta_db=(rows.get("cube_vol_v1", {}).get("level_err_db", float("nan")) - 6.94),
                note=("구판이 GPU SBR 커널로 낸 +6.94 dB 를 이 판은 CPU PO 면적분으로 다시 냈다. "
                      "볼록체라 두 커널은 물리적으로 같아야 한다 — 차이가 작으면 대조군 수치가 "
                      "커널 교체에 오염되지 않았다는 뜻이다.")),
            beats_cube=bool(abs(rows["ours_phantom3_mesh_v2"]["level_err_db"]) < abs(rows[cube_key]["level_err_db"])),
            beats_all_boxes=bool(all(abs(rows["ours_phantom3_mesh_v2"]["level_err_db"]) < abs(rows[k]["level_err_db"])
                                     for k in rows if k.startswith(("cube", "box")))),
            best_level_match=best_abs,
            caveat=("⛔ 절대레벨 일치는 형상 충실도의 증거가 아니다 — 등가부피 구는 모수 0개로도 "
                    "레벨을 맞춘다(p3_attack Q5). 판별력이 있는 축은 방위산포 ε 다."),
        )

    # ── 7. 판정 ───────────────────────────────────────────────────────────
    rc_mean = res["vs_yuan_theta90_measured_curve"]["mean_db"]
    improved = bool(abs(rc_mean) < abs(v1_lvl))
    verdict = dict(
        headline=(f"⭐ 고도·규약·추정량이 모두 정합인 유일한 대조(우리 el=0 ↔ Yuan θ90 실측곡선)에서 "
                  f"v2 메쉬의 레벨오차는 {rc_mean:+.2f} dB 다 (v1 {v1_lvl:+.2f} dB). "
                  f"기울기는 {a_o:.3f} ± {se_o:.3f} dB/GHz (v1 {v1_a:.3f} ± {v1_se:.3f}), "
                  f"실측 조밀곡선 {a_c90:.3f} 대비 {a_o - a_c90:+.3f}."),
        improved_level=improved,
        improved_slope=bool(abs(a_o - a_c90) < abs(v1_a - a_c90)),
        mixed_result=(
            f"⭐⭐ **갈렸다.** 레벨은 좋아지고 기울기는 나빠졌다. "
            f"레벨오차 {v1_lvl:+.2f} → {rc_mean:+.2f} dB (1.61 dB 회복), rms {np.sqrt((r1**2).mean()):.2f} → "
            f"{res['vs_yuan_theta90_measured_curve']['rms_db']:.2f} dB. 그러나 기울기 오차는 "
            f"{v1_a - a_c90:+.3f} → {a_o - a_c90:+.3f} dB/GHz 로 **두 배가 됐고**, 표본이 21→61 로 "
            f"늘어 SE 가 {v1_se:.4f}→{se_o:.4f} 로 줄면서 유의성이 "
            f"{(v1_a - a_c90)/v1_se:.1f}σ → {(a_o - a_c90)/se_o:.1f}σ 로 올라갔다 — 이제 "
            f"'기울기가 실측보다 가파르다' 는 통계적으로 분명하다(v1 에서는 아니었다)."),
        residual_structure=(
            f"잔차는 저대역(≤6 GHz) 평균 {res['vs_yuan_theta90_measured_curve']['low_band_mean_db']:+.2f} dB, "
            f"고대역(≥12 GHz) {res['vs_yuan_theta90_measured_curve']['high_band_mean_db']:+.2f} dB 로 "
            f"{res['vs_yuan_theta90_measured_curve']['low_minus_high_db']:+.2f} dB 벌어지고, 잔차 추세 "
            f"{res['vs_yuan_theta90_measured_curve']['trend_db_per_ghz']:+.3f} dB/GHz 는 "
            f"{res['vs_yuan_theta90_measured_curve']['trend_sigma']:.1f}σ 다 (v1 은 0.86σ 로 유의하지 않았다). "
            "⭐ **형상을 실측으로 고정했더니 오히려 주파수 의존 결손이 또렷해졌다** — 즉 남은 오차의 "
            "주범은 형상이 아니다. 방향은 '저주파에서 더 많이 진다' 로 PTD(모서리 회절, σ가 f 에 "
            "거의 무관) 결손과 저 ka PO 결손이 가리키는 쪽과 같다."),
        what_the_photo_measurement_bought=(
            "형상 자유도 205 → 121, 고정된 P3 관측 13 → 69, 실루엣 IoU 천장대비 77.9% → 86.9%. "
            "그 대가로 얻은 것은 레벨 1.61 dB 회복뿐이고, 남은 3.30 dB 와 커진 기울기 오차는 "
            "**형상 밖**(재질 |Γ| 표·저 ka PO·PTD 결손·편파)에 있다."),
        what_it_means_if_worse=("⚠ 나빠졌다면 그것이 더 중요한 결과다 — 잔차의 원인이 **형상이 "
                                "아니라** 재질(|Γ| 표)·저 ka PO 결손·PTD(모서리 회절) 결손에 "
                                "있다는 뜻이 된다. 사진 실측은 형상 자유도를 205→121 로 줄였고, "
                                "그러고도 레벨이 안 움직였다면 남은 용의자는 형상 밖에 있다."),
        honesty=("이 산출물은 p3_ours_v2.json 을 한 줄도 고치지 않고 만들었다. 맞추기 위한 "
                 "재계산·재적합·메쉬 수정은 없다."),
        caveats=[
            "앵커는 DJI Phantom 3 한 대·한 실험실이다(Das 는 Yuan 자료의 재분석). 독립 재현 아님.",
            "Das·Yuan 은 VV 편파, 우리 커널은 무편파 스칼라 |Γ| 다.",
            "방위창이 다르다(문헌 180° 호 91점 vs 우리 360° 360점).",
            "v2 는 el=0 만 돌렸다 — 고도 로브는 구판 p3_ours.json 을 볼 것.",
            "Das 는 고도풀링(추정)이고 우리 컷은 방위면 하나다. 고도정합 대조는 Yuan θ90 뿐이다.",
            "재질 |Γ| 표·프로펠러 방위위상·프롭 장착높이 6 mm 는 v2 에서도 미해결이다.",
        ],
    )

    out = dict(
        _meta=dict(
            generated=__import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            what=("v2(사진 실측 메쉬) σ 대조 — Das(WCL 2026) / Yuan(EuCAP 2025) Phantom 3 실측 "
                  "계수 및 Yuan Fig.5 복원 실측곡선. 구판 대 신판 비교와 기하 대조군 포함."),
            generator="benchmark/p3_validation_v2.py",
            ours=OURS2, ours_v1=OURS1, validation_v1=VAL1, controls=CTL2,
            ours_generated=D2["meta"]["generated"],
            ours_settings=D2["meta"]["settings_identical_to_v1"],
            das=SA.DAS["citation"], yuan=SA.YUAN["citation"],
            source_relation=SA.SOURCE_RELATION, stat_ambiguity=SA.STAT_AMBIGUITY,
            eps_units=SA.EPS_UNITS),
        window=dict(ours_ghz=[float(f.min()), float(f.max())], ours_n=int(f.size),
                    ours_spacing=D2["meta"]["freq_sampling"],
                    das_ghz=list(SA.DAS["table1"]["phantom3"]["band_ghz"]),
                    yuan_ghz=list(SA.YUAN["band_ghz"]), same_window=True,
                    azimuth_window=_az_window_control(f, sig_az)),
        slope=slope, level=level, residual=res, our_operating_band=opband,
        v1_vs_v2=v1v2, controls=controls, verdict=verdict,
        ours_curve=dict(f_ghz=[float(x) for x in f], mu_dbsm=[float(x) for x in mu],
                        eps_db=[float(x) for x in eps]),
        ours_curve_v1=dict(f_ghz=[float(x) for x in f1], mu_dbsm=[float(x) for x in mu1]),
        yuan_curve_theta90=dict(f_ghz=[float(x) for x in fy90], mu_dbsm=[float(x) for x in my90],
                                digitisation_selfcheck=chk[90]),
    )
    json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1)
    print("wrote", OUT)

    make_fig(f, mu, f1, mu1, fy90, my90, yuan90_mu, das_mu, res, r1, rc, controls, out)
    print("wrote", FIG)

    print(f"level  v1 {v1_lvl:+.3f} → v2 {rc_mean:+.3f} dB   improved={improved}")
    print(f"slope  v1 {v1_a:+.4f}±{v1_se:.4f} → v2 {a_o:+.4f}±{se_o:.4f}  (measured {a_c90:+.4f})")
    if controls:
        for k, v in controls["table"].items():
            print(f"  ctl {k:26s} level {v['level_err_db']:+7.2f}  rms {v['rms_db']:6.2f}  "
                  f"slope {v['slope_db_per_ghz']:+.3f}  eps_err {v.get('eps_err_vs_das_db', float('nan')):+5.2f}"
                  f"  cv {v.get('cv_amp_mean', float('nan')):.3f}")
    return out


def make_fig(f, mu, f1, mu1, fy, my, yuan90_mu, das_mu, res, r1, rc, controls, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    os.makedirs(os.path.dirname(FIG), exist_ok=True)
    plt.rcParams.update({"font.size": 9, "axes.grid": True, "grid.alpha": 0.25,
                         "grid.linewidth": 0.5, "axes.edgecolor": "#888888",
                         "axes.linewidth": 0.8, "legend.frameon": False})
    fig, ax = plt.subplots(2, 2, figsize=(12.4, 8.0))

    # (a) 전대역 μ(f)
    a0 = ax[0, 0]
    a0.plot(fy, my, color=CBLACK, lw=1.6, label="Yuan θ=90° measured curve (EuCAP 2025)")
    a0.plot(f, mu, color=CBLUE, lw=1.8, marker="o", ms=3.0, label=f"ours v2 — photo-measured mesh (n={len(f)})")
    a0.plot(f1, mu1, color=CORANGE, lw=1.2, ls="--", marker="s", ms=3.5,
            label=f"ours v1 — inherited mesh (n={len(f1)})")
    xx = np.linspace(1.8, 18.2, 200)
    a0.plot(xx, yuan90_mu(xx), color="#777777", lw=1.2, ls=":", label="Yuan θ=90° model  0.315f − 16.15")
    a0.plot(xx, das_mu(xx, "exponential"), color=CVERM, lw=1.2, ls="-.",
            label="Das model + exponential offset (elevation-pooled)")
    a0.set_xlabel("Frequency [GHz]"); a0.set_ylabel(r"$\mu$  [dBsm]")
    a0.set_title("(a) Azimuth-mean RCS, full band  —  DJI Phantom 3, el = 0°", loc="left", fontsize=10)
    a0.legend(loc="lower right", fontsize=7.4)

    # (b) 실측곡선 기준 잔차
    a1 = ax[0, 1]
    a1.axhline(0, color=CBLACK, lw=1.0)
    a1.plot(f, rc, color=CBLUE, lw=1.6, marker="o", ms=3.0,
            label=f"ours v2 − measured curve   (band mean {rc.mean():+.2f} dB)")
    a1.plot(f1, r1, color=CORANGE, lw=1.2, ls="--", marker="s", ms=3.5,
            label=f"ours v1 − measured curve   (band mean {r1.mean():+.2f} dB)")
    a1.axhline(rc.mean(), color=CBLUE, lw=1.0, ls=":")
    a1.axhline(r1.mean(), color=CORANGE, lw=1.0, ls=":")
    a1.set_xlabel("Frequency [GHz]"); a1.set_ylabel("Residual [dB]")
    a1.set_title("(b) Level error against the elevation-matched measurement", loc="left", fontsize=10)
    a1.legend(loc="lower left", fontsize=7.6)
    a1.margins(y=0.16)

    # (c) 우리 대역 확대
    a2 = ax[1, 0]
    m = f <= 6.0; m1 = f1 <= 6.0; mw = (fy >= 1.8) & (fy <= 6.0)
    a2.plot(fy[mw], my[mw], color=CBLACK, lw=1.6, label="Yuan θ=90° measured curve")
    a2.plot(f[m], mu[m], color=CBLUE, lw=1.8, marker="o", ms=3.5, label="ours v2")
    a2.plot(f1[m1], mu1[m1], color=CORANGE, lw=1.2, ls="--", marker="s", ms=4, label="ours v1")
    a2.margins(y=0.10)
    for name, x in COMM.items():
        a2.axvline(x, color="#BBBBBB", lw=0.9, ls=":")
        a2.text(x + 0.04, 0.965, name.split(" ")[0], transform=a2.get_xaxis_transform(),
                fontsize=7.5, color="#555555", va="top")
    a2.set_xlabel("Frequency [GHz]"); a2.set_ylabel(r"$\mu$  [dBsm]")
    a2.set_title("(c) The band our detection work lives in  —  1.8 to 6 GHz", loc="left", fontsize=10)
    a2.legend(loc="lower right", fontsize=7.6)

    # (d) 대조군 |레벨오차|
    a3 = ax[1, 1]
    if controls:
        order = ["ours_phantom3_mesh_v2", "ours_phantom3_mesh_v1", "sphere_vol_v2",
                 "sphere_eqvol_paperbox", "cube_vol_v2", "cube_vol_v1", "box_bbox_lit",
                 "box_paper", "box_bbox_v2", "cube_side_max"]
        lab = {"ours_phantom3_mesh_v2": "ours v2 (photo mesh)",
               "ours_phantom3_mesh_v1": "ours v1 (inherited mesh)",
               "sphere_vol_v2": "PEC sphere, equal volume",
               "sphere_eqvol_paperbox": "PEC sphere, paper-box volume",
               "cube_vol_v2": "PEC cube, equal volume",
               "cube_vol_v1": "PEC cube, v1 volume",
               "box_bbox_lit": "PEC box 350x200x185",
               "box_paper": "PEC box 350x350x200",
               "box_bbox_v2": "PEC box = mesh bbox",
               "cube_side_max": "PEC cube 350 mm"}
        rows = [(lab[k], abs(controls["table"][k]["level_err_db"]),
                 controls["table"][k]["level_err_db"]) for k in order if k in controls["table"]]
        rows.sort(key=lambda r: r[1])
        y = np.arange(len(rows))
        cols = [CBLUE if "v2 (photo" in r[0] else (CORANGE if "v1 (inherited" in r[0] else "#9AA0A6")
                for r in rows]
        a3.barh(y, [r[1] for r in rows], color=cols, height=0.62)
        a3.set_yticks(y); a3.set_yticklabels([r[0] for r in rows], fontsize=8)
        for i, r in enumerate(rows):
            a3.annotate(f"{r[2]:+.2f}", xy=(r[1], i), xytext=(4, 0), textcoords="offset points",
                        va="center", fontsize=7.6, color="#333333")
        a3.set_xlim(0, max(r[1] for r in rows) * 1.22)
        a3.invert_yaxis()
        a3.set_xlabel("|band-mean level error| vs measured curve [dB]")
        a3.set_title("(d) Does the mesh still beat a metal box?", loc="left", fontsize=10)
        a3.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(FIG, dpi=170)
    fig.savefig(FIG.replace(".png", ".pdf"))
    plt.close(fig)


if __name__ == "__main__":
    main()
