# -*- coding: utf-8 -*-
"""p3_validation.py — ⭐ 봉인 해제 대조: 우리 blind Phantom 3 σ(f) vs Das / Yuan 실측.

이 파일은 **사후에 메쉬를 고치지 않는다**. outputs/p3_ours.json 은 문헌값을 보지 않고 만든
산출물이고(그 파일의 blind_log 절), 여기서는 그것을 **그대로** 문헌과 맞대본다.

대조축 넷:
  1. 기울기 a  — 같은 창(1.8~18.2 GHz)에서만 비교한다. 창이 다르면 재적합한다.
  2. 레벨 b    — 통계 규약(선형평균 vs dB영역평균) 분기를 **두 갈래 다** 들고 다닌다.
  3. 잔차(f)   — 어느 주파수에서 벗어나는가. PO 저-ka 결손 방향인가.
  4. 분포      — ε(dB) ↔ Das ε, ε(선형진폭) ↔ Yuan ε, d_AD ↔ Das Table II.

실행 (GPU 불필요):
  cd /home/yunjung/workspace/sionna2
  PYTHONPATH=src:benchmark SIONNA2_CPU=1 ~/.venvs/py312/bin/python benchmark/p3_validation.py
"""
from __future__ import annotations

import json
import os

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OURS = os.path.join(ROOT, "outputs", "p3_ours.json")
OUT = os.path.join(ROOT, "outputs", "p3_validation.json")

import sigma_anchor as SA                                             # noqa: E402
from verify_comparability_yuan import extract as yuan_extract         # noqa: E402

BAND = (1.8, 18.2)                       # Das Table I Phantom 3 · Yuan §II-A — **같은 창**
COMM = {"LTE 1.843 GHz": 1.843, "5G 3.5 GHz": 3.5, "WiFi 5.21 GHz": 5.21}
FC = 10.0                                # 밴드 산술중심 — 레벨 비교의 기준점


def _fit(f, y):
    a, b = np.polyfit(np.asarray(f, float), np.asarray(y, float), 1)
    r = np.asarray(y, float) - (a * np.asarray(f, float) + b)
    r2 = 1.0 - r.var() / np.asarray(y, float).var()
    return float(a), float(b), float(r2), float(np.sqrt(np.mean(r ** 2)))


def _fit_se(f, y):
    """(a, b, SE(a), rmse) — 기울기의 **표준오차**까지. n=21 에 rmse 1.4 dB 면 SE 는 작지 않다."""
    f, y = np.asarray(f, float), np.asarray(y, float)
    n = f.size
    a, b = np.polyfit(f, y, 1)
    r = y - (a * f + b)
    s = np.sqrt((r ** 2).sum() / (n - 2))
    return float(a), float(b), float(s / np.sqrt(((f - f.mean()) ** 2).sum())), float(np.sqrt((r ** 2).mean()))


def load_ours():
    D = json.load(open(OURS))
    el0 = D["aspects"]["el0"]["freq"]
    f = np.array(sorted(float(k) for k in el0))
    key = {float(k): k for k in el0}
    mu = np.array([el0[key[x]]["mu_dbsm"] for x in f])
    eps = np.array([el0[key[x]]["eps_db"] for x in f])
    sig = {float(x): np.array(el0[key[x]]["sigma_dbsm_az"]) for x in f}
    return D, f, mu, eps, sig


def das_offset_db(f_ghz, kind):
    """Das μ(dB영역평균 가정) → 선형평균 규약으로 옮길 때 **더할** 값 [dB].

    ⚠ exponential 은 상수라 기울기에 안 닿지만, lognormal 은 ε(f) 를 통해 f 에 의존한다
      → 기울기도 바꾼다. A8 의 '오프셋은 기울기에서 완전히 상쇄된다' 는 exponential 에서만 참이다."""
    f = np.asarray(f_ghz, float)
    c, d = SA.DAS["table3"]["phantom3"][0][2], SA.DAS["table3"]["phantom3"][0][3]
    if kind == "exponential":
        return np.full_like(f, SA.LOG_TO_LIN_EXPONENTIAL_DB)
    if kind == "lognormal":
        return np.log(10.0) / 20.0 * (c * f + d) ** 2
    if kind == "none":
        return np.zeros_like(f)
    raise ValueError(kind)


def _az_window_control(f, sig_az, n_arc=91, step=2):
    """문헌 방위창(−90:2:90 = 180° 호 91점) vs 우리 방위창(360° 1° 360점) 대조.

    시작각이 원문에 없으므로 **모든 시작각**으로 잘라 μ 를 다시 내고 폭을 돌려준다.
    레벨 결손을 방위창 차이로 설명할 수 있는지 가리는 자다."""
    out = {}
    for x in f:
        lin = 10.0 ** (np.asarray(sig_az[float(x)]) / 10.0)
        n = lin.size
        full = 10.0 * np.log10(lin.mean())
        arcs = np.array([10.0 * np.log10(lin[[(o + step * k) % n for k in range(n_arc)]].mean())
                         for o in range(n)])
        out[f"{x:.2f}"] = dict(full_360_db=float(full), arc_mean_db=float(arcs.mean()),
                               arc_min_db=float(arcs.min()), arc_max_db=float(arcs.max()),
                               delta_mean_db=float(arcs.mean() - full),
                               delta_span_db=float(arcs.max() - arcs.min()))
    dm = [v["delta_mean_db"] for v in out.values()]
    ds = [v["delta_span_db"] for v in out.values()]
    return dict(per_freq=out, delta_mean_db_mean=float(np.mean(dm)),
                delta_mean_db_absmax=float(np.max(np.abs(dm))),
                delta_span_db_max=float(np.max(ds)),
                literature_az="-90:2:90 (91 pts, 180° arc) — Das Table I / Yuan §II-A",
                ours_az="0:1:359 (360 pts, full circle)")


def main():
    D, f, mu, eps_ours, sig_az = load_ours()
    a_das, b_das, c_das, d_das = SA.DAS["table3"]["phantom3"][0]
    a_y90, b_y90, c_y90, d_y90 = SA.YUAN["abcd"][90]

    # ── 0. 창 정합 확인 ────────────────────────────────────────────────────
    window = dict(
        ours_ghz=[float(f.min()), float(f.max())], ours_n=int(f.size),
        ours_spacing="uniform 0.82 GHz",
        das_ghz=list(SA.DAS["table1"]["phantom3"]["band_ghz"]), das_n=2801,
        yuan_ghz=list(SA.YUAN["band_ghz"]), yuan_n=2801,
        same_window=True,
        note=("우리 el=0 전대역 적합구간은 1.8~18.2 GHz 로 Das Table III · Yuan §IV 와 **같다**. "
              "재적합이 필요한 것은 구간이 아니라 **표본밀도**(21점 vs 2801점)뿐이고, "
              "그 영향은 아래 yuan_curve_refit_at_our_freqs 가 잰다."),
        azimuth_window=_az_window_control(f, sig_az),
        azimuth_window_note=(
            "⭐ **주파수창은 같지만 방위창은 다르다.** Das Table I(900 dpi 직접 판독) · Yuan §II-A 의 "
            "Phantom 3 방위축은 −90≤φ(=2°)≤90 = **180° 호를 2° 간격 91점**이고, 우리는 360° 전주기를 "
            "1° 간격 360점이다. 그래서 같은 우리 패턴에서 91점 180° 호를 **모든 시작각으로** 잘라 "
            "μ 를 다시 냈다. 시작각을 모르는 데서 오는 폭이 delta_span_db 이고, 평균 편향은 "
            "delta_mean_db 다. ⚠ 이 항은 레벨 결손(−4.9 dB)을 설명하지 못한다 — 평균 편향은 "
            "0.35 dB 미만(21주파수 평균 −0.10 dB)이고, 시작각 미상에 따른 최악 폭도 4.46 dB(≈±2.2 dB) 다."))

    # ── 1. 기울기 ─────────────────────────────────────────────────────────
    a_ours, b_ours, r2_ours, rmse_ours = _fit(f, mu)
    _, _, se_ours, _ = _fit_se(f, mu)

    curves, chk = yuan_extract()                       # Yuan Fig.5 실측곡선 복원
    fy90_raw, my90_raw = curves[90]
    # ⚠ θ90 복원곡선의 **마지막 한 표본**은 폴리라인 닫힘 아티팩트다 (18.192 GHz 에서 −8.22 →
    #    −13.28 dB 로 한 표본 만에 5 dB 낙하). 잘라낸다. 전대역 재적합은 0.3148 → 0.3159 로만
    #    바뀌므로(0.001 dB/GHz) 이 절단이 결론을 만들지 않는다. θ0·θ180 에는 같은 현상이 없다.
    fy90, my90 = fy90_raw[:-1], my90_raw[:-1]
    a_c90, b_c90, r2_c90, _ = _fit(fy90, my90)
    # 우리 21 주파수에서 실측곡선을 재표집. 1.8 / 18.2 GHz 는 복원구간(1.810~18.168)을 각각
    # 0.010 / 0.032 GHz 벗어나므로 **가장자리 값으로 클램프**한다 (외삽오차 < 0.01 dB).
    my90_at_ours = np.interp(f, fy90, my90)
    a_sub, b_sub, r2_sub, _ = _fit(f, my90_at_ours)
    inb = (f >= fy90.min()) & (f <= fy90.max())        # 클램프 없는 엄격 겹침구간 (19점)
    a_strict_ours = _fit(f[inb], mu[inb])[0]
    a_strict_meas = _fit(f[inb], my90_at_ours[inb])[0]

    fg = np.linspace(max(fy90.min(), curves[0][0].min(), curves[180][0].min()),
                     min(fy90.max(), curves[0][0].max(), curves[180][0].max()), 1200)
    from verify_comparability_yuan import pooled_linear
    pool = pooled_linear(curves, fg)
    a_pool, b_pool, r2_pool, _ = _fit(fg, pool)

    # Das 를 선형평균 규약으로 옮겼을 때의 **실효 기울기** (분기별)
    ff = np.linspace(*BAND, 400)
    a_das_eff = {}
    for k in ("none", "exponential", "lognormal"):
        aa, _, _, _ = _fit(ff, a_das * ff + b_das + das_offset_db(ff, k))
        a_das_eff[k] = aa

    loo = [float(np.polyfit(np.delete(f, i), np.delete(mu, i), 1)[0]) for i in range(f.size)]
    slope = dict(
        ours_el0_full_band=dict(a=a_ours, b=b_ours, R2=r2_ours, rmse_db=rmse_ours, n=int(f.size),
                                se_a=se_ours, ci95=[a_ours - 1.96 * se_ours, a_ours + 1.96 * se_ours]),
        ours_slope_robustness=dict(
            leave_one_out_min=min(loo), leave_one_out_max=max(loo),
            drop_both_endpoints=float(np.polyfit(f[1:-1], mu[1:-1], 1)[0]),
            strict_overlap_19pt=a_strict_ours,
            note=("⭐ n=21 에 rmse 1.43 dB 라 기울기의 SE 가 0.066 dB/GHz 다. 양 끝점 두 개를 빼면 "
                  "0.420 → 0.334 로 떨어진다. 우리 기울기 추정치는 **끝점이 끌고 간다** — "
                  "'2배 가파르다' 를 유효숫자 두 자리로 적으면 안 된다.")),
        significance=dict(
            z_vs_das_0p21=(a_ours - a_das) / se_ours,
            z_vs_yuan_theta90_0p315=(a_ours - a_y90) / se_ours,
            z_vs_yuan_curve_resampled=(a_ours - a_sub) / se_ours,
            reading=("Das 0.21 은 우리 95% 신뢰구간 밖(3.2σ)이지만 Das 는 고도풀링이다. "
                     "**고도정합 대조인 Yuan θ90 = 0.315 는 1.6σ — 95% 수준에서 구별되지 않는다.**")),
        sampling_density_aliasing=dict(
            measured_curve_full_refit=a_c90,
            measured_curve_full_refit_untrimmed=float(np.polyfit(fy90_raw, my90_raw, 1)[0]),
            published=a_y90,
            resampled_at_our_21_freqs_trimmed_edge=a_sub,
            resampled_at_our_21_freqs_untrimmed_edge=float(
                np.polyfit(f, np.interp(f, fy90_raw, my90_raw), 1)[0]),
            aliasing_span_db_per_ghz=float(abs(a_sub - np.polyfit(
                f, np.interp(f, fy90_raw, my90_raw), 1)[0])),
            note=("⚠ 같은 실측곡선을 우리 21점 성긴 격자로 재표집하면 기울기가 **가장자리 표본 "
                  "하나에** 0.28~0.36 dB/GHz 로 흔들린다(리플 에일리어싱). 전곡선 재적합은 "
                  "0.3148/0.3159 로 공표 0.315 와 붙으므로, 측정측 comparand 는 **0.315** 를 쓰고 "
                  "성긴격자 불확도 ±0.04 dB/GHz 를 우리 SE 0.066 과 함께 든다.")),
        das_published=dict(a=a_das, b=b_das, band=list(BAND),
                           statistic_as_published="angle-averaged mean (Das §III-1) / 규약 미해소"),
        das_effective_slope_after_convention=a_das_eff,
        yuan_theta90_published=dict(a=a_y90, b=b_y90, band=list(SA.YUAN["band_ghz"])),
        yuan_theta90_curve_refit=dict(a=a_c90, b=b_c90, R2=r2_c90, n=int(fy90.size),
                                      span=[float(fy90.min()), float(fy90.max())]),
        yuan_curve_refit_at_our_freqs=dict(a=a_sub, b=b_sub, R2=r2_sub, n=int(f.size),
                                           note="복원 실측곡선을 **우리 21주파수에서만** 재표집해 재적합. "
                                                "표본밀도가 기울기를 바꾸는지 보는 자."),
        yuan_elevation_pooled_curve_refit=dict(a=a_pool, b=b_pool, R2=r2_pool),
        strict_overlap_19pt=dict(ours=a_strict_ours, measured_curve=a_strict_meas,
                                 note="클램프 없이 우리 21점 중 복원구간 안 19점만. 끝점 민감도의 다른 얼굴."),
        ratios=dict(
            ours_over_das=a_ours / a_das,
            ours_over_das_exponential=a_ours / a_das_eff["exponential"],
            ours_over_das_lognormal=a_ours / a_das_eff["lognormal"],
            ours_over_yuan_theta90=a_ours / a_y90,
            ours_over_yuan_curve_at_our_freqs=a_ours / a_sub),
        differences_db_per_ghz=dict(
            ours_minus_das=a_ours - a_das,
            ours_minus_das_lognormal_branch=a_ours - a_das_eff["lognormal"],
            ours_minus_yuan_theta90=a_ours - a_y90,
            ours_minus_yuan_curve_at_our_freqs=a_ours - a_sub),
        elevation_matched_comparand="yuan_theta90 (방위면) = 우리 el=0. Das 는 고도풀링이라 정합이 아니다.",
        our_slope_across_elevation=D["elevation_lobe"]["a_mu_by_elevation_db_per_ghz"],
        subband=dict(ours=D["subband_fits"]["by_aspect"]["el0"],
                     yuan_theta90_curve={f"{lo}-{hi} GHz": _fit(fy90[(fy90 >= lo) & (fy90 <= hi)],
                                                                my90[(fy90 >= lo) & (fy90 <= hi)])[0]
                                         for lo, hi in [(1.8, 6.0), (6.0, 18.2), (10.0, 18.2)]},
                     note="⭐ 전대역 직선은 우리도 측정도 곡선을 억지로 편 것이다. 부분대역에서 둘 다 달라진다."),
    )

    # ── 2. 레벨 ───────────────────────────────────────────────────────────
    def das_mu(x, kind):
        return a_das * np.asarray(x, float) + b_das + das_offset_db(x, kind)

    def yuan90_mu(x):
        return a_y90 * np.asarray(x, float) + b_y90

    def ours_mu(x):
        return a_ours * np.asarray(x, float) + b_ours

    # Yuan 이 직접 말해주는 고도항: θ90(방위면) − 3면 선형풀링
    d_elev = float(np.interp(FC, fg, np.interp(FC, fy90, my90) - pool[np.argmin(abs(fg - FC))])
                   ) if False else float(np.interp(FC, fy90, my90) - pool[np.argmin(abs(fg - FC))])

    lvl_at = {}
    for name, x in [("band_center_10.0GHz", FC)] + [(k, v) for k, v in COMM.items()]:
        row = dict(
            ours=float(ours_mu(x)),
            ours_measured_point=float(np.interp(x, f, mu)),
            das_as_published=float(das_mu(x, "none")),
            das_exponential=float(das_mu(x, "exponential")),
            das_lognormal=float(das_mu(x, "lognormal")),
            yuan_theta90_model=float(yuan90_mu(x)),
        )
        if fy90.min() <= x <= fy90.max():
            row["yuan_theta90_measured_curve"] = float(np.interp(x, fy90, my90))
            row["yuan_elevation_pooled_curve"] = float(np.interp(x, fg, pool))
        row["ours_minus_das_exponential"] = row["ours"] - row["das_exponential"]
        row["ours_minus_das_lognormal"] = row["ours"] - row["das_lognormal"]
        row["ours_minus_das_as_published"] = row["ours"] - row["das_as_published"]
        row["ours_minus_yuan_theta90"] = row["ours"] - row["yuan_theta90_model"]
        lvl_at[name] = row

    # 밴드평균 오프셋(= 두 직선의 중점차)
    band_mean = {}
    for k in ("none", "exponential", "lognormal"):
        band_mean["das_" + k] = float(np.mean(ours_mu(ff) - das_mu(ff, k)))
    band_mean["yuan_theta90"] = float(np.mean(ours_mu(ff) - yuan90_mu(ff)))

    level = dict(
        intercept_b=dict(ours=b_ours, das=b_das, yuan_theta90=b_y90,
                         ours_minus_das=b_ours - b_das, ours_minus_yuan=b_ours - b_y90,
                         warning=("b 는 f=0 절편이라 **밴드 밖 외삽점**이다. 기울기가 다른 두 직선의 "
                                  "절편차는 레벨차가 아니다 — 아래 at_frequency 를 쓸 것.")),
        at_frequency=lvl_at,
        band_mean_offset_db=band_mean,
        elevation_term_from_yuan_db=dict(
            theta90_minus_pooled_at_10GHz=d_elev,
            note=("Das 는 고도풀링(추정)이고 우리 컷은 방위면 하나다. Yuan 이 그 차이를 직접 준다 — "
                  "Das 와 맞대려면 이 항을 더해야 하고, Yuan θ90 과 맞대면 필요 없다.")),
        convention_branches=dict(
            exponential_db=float(SA.LOG_TO_LIN_EXPONENTIAL_DB),
            lognormal_db_at_10GHz=float(das_offset_db(FC, "lognormal")),
            lognormal_db_range_over_band=[float(das_offset_db(BAND[0], "lognormal")),
                                          float(das_offset_db(BAND[1], "lognormal"))],
            spread_db=float(das_offset_db(FC, "lognormal") - SA.LOG_TO_LIN_EXPONENTIAL_DB),
            rule="A8 — 두 갈래를 언제나 함께 들고 다닌다. 조용한 단일값 금지."),
        our_convention_measured=dict(
            linear_minus_db_domain_mean_db=D["distribution_summary"]["linear_minus_dB_domain_mean_db"],
            note=("우리 패턴에서 **직접 잰** 규약차. 지수분포 이론 2.507 dB 와 비교하면 "
                  "우리 σ 분포가 그 가정에 얼마나 맞는지 나온다.")),
    )

    # ── 3. 주파수별 잔차 ──────────────────────────────────────────────────
    res = {}
    for name, ref in [("vs_das_exponential", das_mu(f, "exponential")),
                      ("vs_das_lognormal", das_mu(f, "lognormal")),
                      ("vs_das_as_published", das_mu(f, "none")),
                      ("vs_yuan_theta90_model", yuan90_mu(f))]:
        r = mu - ref
        res[name] = dict(resid_db=[float(x) for x in r], mean_db=float(r.mean()),
                         rms_db=float(np.sqrt((r ** 2).mean())),
                         worst_freq_ghz=float(f[np.argmax(np.abs(r))]),
                         worst_db=float(r[np.argmax(np.abs(r))]),
                         low_band_mean_db=float(r[f <= 6.0].mean()),
                         high_band_mean_db=float(r[f >= 12.0].mean()),
                         trend_db_per_ghz=float(np.polyfit(f, r, 1)[0]))
    rc = mu - my90_at_ours
    a_rc, _, se_rc, _ = _fit_se(f, rc)
    res["vs_yuan_theta90_measured_curve"] = dict(
        f_ghz=[float(x) for x in f], resid_db=[float(x) for x in rc],
        mean_db=float(rc.mean()), rms_db=float(np.sqrt((rc ** 2).mean())),
        std_db=float(rc.std(ddof=1)),
        worst_freq_ghz=float(f[np.argmax(np.abs(rc))]),
        worst_db=float(rc[np.argmax(np.abs(rc))]),
        best_freq_ghz=float(f[np.argmin(np.abs(rc))]), best_db=float(rc[np.argmin(np.abs(rc))]),
        low_band_mean_db=float(rc[f <= 6.0].mean()),
        high_band_mean_db=float(rc[f >= 12.0].mean()),
        low_minus_high_db=float(rc[f <= 6.0].mean() - rc[f >= 12.0].mean()),
        trend_db_per_ghz=a_rc, trend_se=se_rc, trend_sigma=a_rc / se_rc,
        strict_overlap_19pt=dict(mean_db=float(rc[inb].mean()),
                                 trend_db_per_ghz=float(np.polyfit(f[inb], rc[inb], 1)[0])),
        note=("⭐ 선형모델이 아니라 **실측곡선** 기준 잔차. 고도(θ90=el0)·통계규약(둘 다 방위 "
              "선형평균)·추정량(둘 다 단일주파수)이 모두 정합인 **유일한** 대조다. "
              "1.8 / 18.2 GHz 는 복원구간 가장자리로 클램프했다."))

    # PO 저-ka 방향 검증
    kr = json.load(open(os.path.join(ROOT, "outputs", "sbr_kr_sweep.json")))
    po_mie = {}
    for r_ in kr["rows"]:
        if r_["div"] == 16:
            po_mie[r_["kr"]] = r_["db_po_over_mie"]
    # ⚠ 2026-08-03 정정: 이전 판은 λ 를 **mm 로 계산해 놓고 m 로 이름 붙여** ka 가 1000 배
    #   작게 나왔다(1.8 GHz 기체 반경에서 0.0055). 그러면 전 주파수가 레일리로 보여
    #   "저주파에서만 진다" 라는 주장 자체가 성립하지 않는다. 아래는 λ[m] = c/f 로 고쳤다.
    lam_m = 0.299792458 / f                       # [m]  (f 는 GHz)
    feats = {"airframe half-span (0.1445 m)": 0.1445, "shell half-height (0.032 m)": 0.032,
             "motor bell (0.017 m)": 0.017, "landing-leg tube (0.008 m)": 0.008}
    ka_tab = {k: [float(2 * np.pi * v / lam) for lam in lam_m] for k, v in feats.items()}
    # 구 스윕의 PO/Mie 편차를 kr 축에서 보간해, 각 부위·주파수의 ka 에 **예상 PO 오차**를 붙인다.
    krx = np.array(sorted(po_mie)); kry = np.array([po_mie[k] for k in krx])
    po_pred = {k: [float(np.interp(v, krx, kry)) for v in vs] for k, vs in ka_tab.items()}
    ka_min_by_f = {f"{x:.2f}": float(min(ka_tab[k][i] for k in ka_tab))
                   for i, x in enumerate(f)}
    lowka = dict(
        f_ghz=[float(x) for x in f], lambda_m=[float(x) for x in lam_m], ka=ka_tab,
        sphere_po_vs_mie_db=po_mie,
        po_error_predicted_db=po_pred,
        smallest_feature_ka_by_freq=ka_min_by_f,
        reading=("우리 구 스윕(div=16)은 PO 가 kr=1 에서 Mie 대비 −6.58 dB(과소), kr=2~3 에서 "
                 "+1.97/+3.23 dB(과대), kr≥5 에서 ±0.2 dB 다. 즉 'PO 는 저 ka 에서 진다' 는 "
                 "**kr≲1.5 에서만 과소**라는 뜻이고 공진영역에서는 양방향으로 틀린다."),
        ka_reading=("⭐ 제대로 센 ka 는 이렇게 갈린다. **1.8 GHz**: 기체 반스팬 5.45 / 셸 반높이 "
                    "1.21 / 모터벨 0.64 / 다리튜브 0.30 — 부위 셋이 kr≲1.2 로 PO 가 −6.6 dB 까지 "
                    "지는 구간에 들어간다. **18.2 GHz**: 55.1 / 12.2 / 6.5 / 3.0 — 전부 kr≥3 이라 "
                    "가장 작은 부위 하나만 공진영역이고 나머지는 ±0.2 dB 다. 즉 잔차가 저주파에서 "
                    "크고 고주파에서 줄어드는 관측 방향과 ka 표가 **같은 쪽**을 가리킨다. "
                    "⚠ 단 구의 kr 곡선을 부위 ka 에 갖다 붙인 것은 **정황 일치이지 정량 예측이 "
                    "아니다** — 부위는 구가 아니고, 기여 가중치도 모른다."),
        mechanism=("더 큰 계통항은 PTD 결손이다. 모서리 회절 σ 는 f 에 거의 무관한데 PO 정반사항은 "
                   "∝f² 로 자란다 → 저주파일수록 빠진 몫의 비중이 커진다. 잔차가 저주파에서 더 "
                   "음(-)이면 그 방향이다."))

    # ── 4. 분포 ───────────────────────────────────────────────────────────
    eps_das = c_das * f + d_das
    lin = {x: 10.0 ** (v / 10.0) for x, v in sig_az.items()}
    eps_amp_ours = np.array([float(np.std(np.sqrt(lin[x]))) for x in f])
    eps_amp_yuan = c_y90 * f + d_y90
    el0f = D["aspects"]["el0"]["freq"]
    kk = {float(k): k for k in el0f}
    dad_amp = {m: float(np.mean([el0f[kk[x]]["distributions"]["amplitude"]["fits"][m]["d_AD_textbook"]
                                 for x in f])) for m in ("rician", "gamma", "lognormal")}
    dc_amp = {m: float(np.mean([el0f[kk[x]]["distributions"]["amplitude"]["fits"][m]["d_C"]
                                for x in f])) for m in ("rician", "gamma", "lognormal")}
    best_tally = {}
    for x in f:
        b = el0f[kk[x]]["distributions"]["amplitude"]["best_by_CvM"]
        best_tally[b] = best_tally.get(b, 0) + 1

    dist = dict(
        eps_db_ours=[float(x) for x in eps_ours],
        eps_db_das=[float(x) for x in eps_das],
        eps_db_diff=dict(mean=float(np.mean(eps_ours - eps_das)),
                         rms=float(np.sqrt(np.mean((eps_ours - eps_das) ** 2))),
                         max_abs=float(np.max(np.abs(eps_ours - eps_das)))),
        eps_db_slope=dict(ours_c=_fit(f, eps_ours)[0], das_c=c_das,
                          ours_d=_fit(f, eps_ours)[1], das_d=d_das),
        eps_amplitude_linear=dict(
            ours=[float(x) for x in eps_amp_ours], yuan_theta90=[float(x) for x in eps_amp_yuan],
            ratio_ours_over_yuan=[float(a / b) for a, b in zip(eps_amp_ours, eps_amp_yuan)],
            note=("Yuan ε 은 **선형 진폭 √σ 의 표준편차**(EPS_UNITS). 우리 패턴에서 같은 양을 "
                  "직접 계산했다. ⚠ 이 비는 레벨 오차를 그대로 물려받는다 — σ 가 낮으면 √σ 의 "
                  "표준편차도 낮다. 모양만 보려면 변동계수를 볼 것.")),
        coefficient_of_variation=dict(
            ours=[float(np.std(np.sqrt(lin[x])) / np.mean(np.sqrt(lin[x]))) for x in f],
            rayleigh_theory=float(np.sqrt(4.0 / np.pi - 1.0)),
            note="std(√σ)/mean(√σ). 레일리(=Swerling I/II) 이론 0.5227. 레벨과 무관한 모양 자."),
        goodness_of_fit=dict(
            ours_el0_amplitude_mean_dAD=dad_amp, ours_el0_amplitude_mean_dCvM=dc_amp,
            ours_el0_best_by_CvM_tally=best_tally,
            das_table2_phantom3_dAD=dict(lognormal=1.38, gamma=0.628, rician=0.436,
                                         best="rician", verified="page-3 render 500 dpi, 본 에이전트 직접 판독"),
            yuan_cvm_avg=dict(rician=0.28, gamma=0.31, lognormal=0.48, best="rician"),
            note=("⚠ Das/Yuan 은 **주파수·각도 전체 평균 통계량**이고 우리는 el=0·21주파수 평균이다. "
                  "d_AD 는 표본수 N 에 비례해 커지므로(N=360 vs 논문 N=91) 절대값 대조는 못 한다. "
                  "비교 가능한 것은 **순위**뿐이다.")),
        percentiles=D["distribution_summary"]["percentiles_norm_db"],
    )

    # ── 4b. ⭐ 우리가 실제로 쓰는 대역 (1.8~6.0 GHz) ────────────────────────
    #  이 저장소의 디텍션 작업은 전부 LTE/5G/WiFi 대역 안에 있다. 전대역 직선은 두 논문과
    #  맞추기 위한 규약일 뿐이고, **우리 결론이 걸린 곳은 여기다.**
    lo = f <= 6.0
    a_o_lo, b_o_lo, _, _ = _fit(f[lo], mu[lo])
    m_lo = my90_at_ours[lo]
    a_m_lo, b_m_lo, _, _ = _fit(f[lo], m_lo)
    fw = (fy90 >= 1.8) & (fy90 <= 6.0)
    a_mc_lo, b_mc_lo, _, _ = _fit(fy90[fw], my90[fw])
    r_lo = mu[lo] - m_lo
    opband = dict(
        band_ghz=[1.8, 6.0], n_ours=int(lo.sum()),
        ours=dict(a=a_o_lo, b=b_o_lo),
        measured_theta90_curve_dense=dict(a=a_mc_lo, b=b_mc_lo, n=int(fw.sum())),
        measured_theta90_curve_at_our_freqs=dict(a=a_m_lo, b=b_m_lo),
        level_error_db=dict(mean=float(r_lo.mean()), at_1p8=float(r_lo[0]),
                            at_5p9=float(r_lo[-1]), per_freq=[float(x) for x in r_lo]),
        slope_error_db_per_ghz=a_o_lo - a_mc_lo,
        slope_ratio=a_o_lo / a_mc_lo,
        comm_band_mu=dict(
            ours={k: float(np.interp(v, f, mu)) for k, v in COMM.items()},
            measured_theta90_curve={k: float(np.interp(v, fy90, my90)) for k, v in COMM.items()},
            yuan_theta90_model={k: float(yuan90_mu(v)) for k, v in COMM.items()},
            das_exponential={k: float(das_mu(v, "exponential")) for k, v in COMM.items()}),
        finding=("⭐ 우리 대역에서 어긋남이 **가장 크다**. 우리 μ 는 1.8~6.0 GHz 에서 "
                 f"{a_o_lo:.2f} dB/GHz 로 오르는데 같은 창의 실측은 {a_mc_lo:.2f} dB/GHz 다 "
                 f"({a_o_lo/a_mc_lo:.1f}배). 레벨은 1.8 GHz 에서 {r_lo[0]:.1f} dB, "
                 f"5.9 GHz 에서 {r_lo[-1]:.1f} dB 낮다 — 즉 우리 커널은 저주파에서 특히 죽고 "
                 "주파수와 함께 따라잡는다. 전대역 통계(레벨 −4.7 dB · 기울기 +0.10)는 이 "
                 "구조를 평균해서 감춘다."),
        consequence=("디텍션 벤치마크가 LTE 1.843 GHz 를 최악 대역으로 쓰는데, 바로 거기서 "
                     "우리 σ 가 실측 대비 가장 낮다 → 우리 Pd 는 **보수적(비관적)** 쪽으로 "
                     "치우쳐 있다. 이 방향은 결론을 뒤집지 않지만 마진을 과소평가한다."))

    # ── 5. 판정 ───────────────────────────────────────────────────────────
    lvl_exp = lvl_at["band_center_10.0GHz"]["ours_minus_das_exponential"]
    lvl_log = lvl_at["band_center_10.0GHz"]["ours_minus_das_lognormal"]
    lvl_y90 = lvl_at["band_center_10.0GHz"]["ours_minus_yuan_theta90"]
    rc_mean = res["vs_yuan_theta90_measured_curve"]["mean_db"]
    verdict = dict(
        headline=("⭐ **지배 오차는 레벨이다.** 고도·규약·추정량이 모두 정합인 유일한 대조"
                  "(우리 el=0 ↔ Yuan θ=90 실측곡선)에서 우리 σ 는 밴드 전체에 걸쳐 "
                  f"평균 {rc_mean:.1f} dB **낮다**. 기울기 초과는 +0.105 dB/GHz "
                  "(우리 0.420 ± 0.066 vs 측정 0.315) 로 **1.6σ — 95% 수준에서 유의하지 않다**. "
                  "'기울기가 2배 가파르다' 는 고도풀링 Das(0.21)와 맞댈 때만 나오는 수이고, "
                  "그 대조는 고도가 정합이 아니다."),
        which_error_dominates=("레벨 −4.6~−4.9 dB 대 기울기 +0.105 dB/GHz. 16.4 GHz 폭 전체에 "
                               "걸쳐 기울기 오차가 만드는 차이는 1.7 dB 이고 레벨 오차는 4.7 dB 다 "
                               "→ **레벨이 기울기보다 약 3배 큰 오차다.**"),
        but_in_our_own_band=(f"⚠ 단 전대역 평균이 구조를 감춘다. 1.8~6.0 GHz 에서는 우리 "
                             f"{a_o_lo:.2f} vs 실측 {a_mc_lo:.2f} dB/GHz = {a_o_lo/a_mc_lo:.1f}배이고 "
                             f"레벨 결손이 1.8 GHz {r_lo[0]:.1f} dB → 5.9 GHz {r_lo[-1]:.1f} dB 로 "
                             "줄어든다. 우리 디텍션 결론이 사는 대역은 여기다."),
        level_error_db=dict(
            das_exponential_branch=lvl_exp, das_lognormal_branch=lvl_log,
            das_as_published_no_offset=lvl_at["band_center_10.0GHz"]["ours_minus_das_as_published"],
            yuan_theta90_elevation_matched=lvl_y90,
            evaluated_at="band centre 10.0 GHz (두 직선의 중점 = 밴드평균 오프셋과 같다)",
            spread_note=("규약 분기가 0.93 dB, Das↔Yuan 고도항이 1.5 dB — 즉 '레벨 오차' 자체가 "
                         "±1 dB 규약 불확도를 달고 있다. 단일값으로 적으면 거짓 정밀이다.")),
        slope_error_db_per_ghz=dict(
            vs_das=a_ours - a_das, vs_das_lognormal_branch=a_ours - a_das_eff["lognormal"],
            vs_yuan_theta90=a_ours - a_y90,
            vs_yuan_elevation_pooled_curve=a_ours - a_pool,
            ours_se=se_ours, ours_ci95=[a_ours - 1.96 * se_ours, a_ours + 1.96 * se_ours],
            significant_at_95pct=dict(vs_das=bool(abs(a_ours - a_das) > 1.96 * se_ours),
                                      vs_yuan_theta90=bool(abs(a_ours - a_y90) > 1.96 * se_ours)),
            note=("⭐ 규약 오프셋은 exponential 분기에서 기울기에 안 닿는다 — 기울기는 규약 논쟁 "
                  "밖이다. ⚠ 단 lognormal 분기는 ε(f) 를 통해 f 에 의존하므로 Das 실효기울기를 "
                  f"0.210 → {a_das_eff['lognormal']:.3f} 으로 올린다. A8 의 '오프셋은 기울기에서 "
                  "완전히 상쇄된다' 는 exponential 분기에서만 참이다.")),
        what_is_ours_and_what_is_measured=(
            "각도패턴·상대구조는 우리 SBR+PO 기하에서 왔고, 이 대조가 재는 것은 그 위에 얹힌 "
            "**절대 레벨과 주파수의존** 두 스칼라뿐이다."),
        honesty=("이 산출물은 p3_ours.json 을 **한 줄도 고치지 않고** 만들었다. 맞추기 위한 "
                 "재계산·재적합·메쉬 수정은 없다. 안 맞는 항은 안 맞는 채로 적었다."),
        das_table_read_uncertainty=(
            "Das Table I·III 은 PDF 에 텍스트 레이어가 없다(fitz 추출 시 빈 문자열 — 표제만 텍스트다). "
            "1차 판독은 350 dpi 였고, **2026-08-03 두 번째 에이전트가 900/800 dpi 로 독립 재렌더해 "
            "재판독**했다. 결과: Table III Phantom 3 θb=0 = 'μ=0.21f−19.19, ε=0.03f+5.16' **일치**, "
            "Table III Phantom 3 행 전체가 θb 에 걸쳐 기울기 0.21 고정·절편만 −19.19→−19.82 이동 "
            "**일치**, Table I Phantom 3 열 = '35 cm×20 cm / 1.8 GHz–18.2 GHz / 2801 / "
            "−90°≤φ(=2°)≤90° / Far-field / Anechoic' **일치**. 900 dpi 에서 글리프는 모호하지 않다. "
            "남는 불확도는 판독이 아니라 **표 자체의 반올림**이다 — a 에 ±0.005 dB/GHz, b 에 "
            "±0.005 dB. a 의 ±0.005 는 우리 SE 0.066 의 8% 라 결론에 안 닿는다. Yuan 계수는 "
            "텍스트 레이어에서 그대로 추출돼('{0.315, −16.15, 0.0045, 0.07}') 이 불확도가 없다."),
        das_elevation_pooling_is_an_inference=(
            "⚠ **Das 가 고도를 풀링했다는 것은 추론이지 원문 진술이 아니다.** Das Table I 은 방위축만 "
            "적고 고도(θ)를 아예 언급하지 않는다. 풀링설의 근거는 오직 reconcile_das_yuan 잔차다 — "
            "Das+2.5068 dB 가 Yuan 3고도 선형풀링과 10 GHz 에서 0.09 dB 안에 든다. 대안 해석은 "
            "'Das 도 방위면 하나'인데, 그러면 **같은 원자료의 두 논문이 레벨 4.1 dB · 기울기 "
            "0.105 dB/GHz 어긋난다**는 뜻이 되고 그건 규약만으로 못 메운다. 어느 쪽이든 우리 "
            "레벨오차 −3.0(Das·exp) ~ −4.9 dB(Yuan θ90 곡선)의 **폭 자체가 문헌 내부 불일치**를 "
            "물려받은 것이다. 단일값으로 좁히지 말 것."),
        das_K_inconsistency=(
            "Das §III-2 는 방위표본을 'K = 360' 이라 적지만, 같은 논문 Table I 의 Phantom 3 열은 "
            "−90:2:90 = **91 점**이다. K=360 은 1° 전주기를 쓴 다른 세 기체에 맞는 값이다. "
            "우리 대조는 Table I 쪽(91점)을 사실로 본다."),
        residual_direction=("잔차는 저주파에서 가장 음(-)이고 고주파로 갈수록 줄어든다 → "
                            "PO 가 저주파에서 진다는 예측과 **같은 방향**이다. ka 표(정정판)가 "
                            "그 방향을 뒷받침한다: 1.8 GHz 에서 셸(1.21)·모터벨(0.64)·다리튜브(0.30) 가 "
                            "PO 가 −6.6 dB 까지 지는 kr≲1.2 구간에 있고, 18.2 GHz 에서는 가장 작은 "
                            "부위조차 ka=3.05 다. 단 지배 기전은 구의 저-kr 결손이 아니라 PTD(모서리 "
                            "회절) 결손일 가능성이 크다 — 회절 σ 는 f 에 무관하고 PO 정반사항만 "
                            "∝f² 로 자라기 때문. 둘을 가르는 직접 실험은 아직 안 했다."),
        caveats=[
            "앵커는 DJI Phantom 3 **한 대·한 실험실**이다(Das 는 Yuan 자료의 재분석). 독립 재현 아님.",
            "Das·Yuan 은 VV 편파, 우리 커널은 무편파 스칼라 |Γ| 다. 그 차이는 레벨에 흡수된다.",
            "방위창이 다르다(문헌 180° 호 91점 vs 우리 360° 360점). window.azimuth_window 가 그 "
            "항을 직접 쟀다 — 평균 |편향| <0.35 dB, 시작각 미상에 따른 최악 폭 4.46 dB. 레벨 결손을 "
            "설명하지 못한다.",
            "우리 메쉬는 P3 사진이 없어 셸 단면법칙을 phantom4 에서 상속했고, 높이 185 mm 를 쓴다"
            "(문헌은 200 mm). 마그네슘 판 1장이 과금속화 편향으로 들어가 있다(p3_ours.caveats).",
            "우리 μ 는 el=0 단면이고 Das 는 고도풀링(추정)이다. 고도 정합 대조는 Yuan θ=90 뿐이다.",
            "Das 추정량은 시간영역 피크(§II eq.3), 우리·Yuan 은 단일주파수 CW 비다.",
        ],
    )

    out = dict(
        _meta=dict(
            generated=__import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            what=("봉인 해제 대조 — blind 산출 outputs/p3_ours.json vs Das(WCL 2026) / Yuan(EuCAP 2025) "
                  "DJI Phantom 3 실측 계수 및 Yuan Fig.5 복원 실측곡선"),
            generator="benchmark/p3_validation.py",
            ours=OURS, ours_generated=D["meta"]["generated"], ours_blind=D["meta"]["blind"],
            das=SA.DAS["citation"], das_pdf=SA.DAS["pdf"],
            yuan=SA.YUAN["citation"], yuan_pdf=SA.YUAN["pdf"],
            source_relation=SA.SOURCE_RELATION, stat_ambiguity=SA.STAT_AMBIGUITY,
            eps_units=SA.EPS_UNITS),
        window=window, slope=slope, level=level, residual=res, low_ka=lowka,
        our_operating_band=opband, distribution=dist, verdict=verdict,
        ours_curve=dict(f_ghz=[float(x) for x in f], mu_dbsm=[float(x) for x in mu],
                        eps_db=[float(x) for x in eps_ours]),
        yuan_curve_theta90=dict(f_ghz=[float(x) for x in fy90], mu_dbsm=[float(x) for x in my90],
                                digitisation_selfcheck=chk[90]),
        yuan_curve_pooled=dict(f_ghz=[float(x) for x in fg], mu_dbsm=[float(x) for x in pool]),
    )
    json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1)
    print("wrote", OUT)
    print(f"a  ours {a_ours:+.4f}  das {a_das:+.4f} (x{a_ours/a_das:.2f})  "
          f"yuan90 {a_y90:+.4f} (x{a_ours/a_y90:.2f})  yuan-curve@ourfreqs {a_sub:+.4f}")
    print(f"level @10 GHz  ours {lvl_at['band_center_10.0GHz']['ours']:.2f}  "
          f"das+exp {lvl_at['band_center_10.0GHz']['das_exponential']:.2f} ({lvl_exp:+.2f})  "
          f"das+logn {lvl_at['band_center_10.0GHz']['das_lognormal']:.2f} ({lvl_log:+.2f})  "
          f"yuan90 {lvl_at['band_center_10.0GHz']['yuan_theta90_model']:.2f} ({lvl_y90:+.2f})")
    for k, v in res.items():
        print(f"  resid {k:38s} mean {v['mean_db']:+.2f}  rms {v['rms_db']:.2f}  "
              f"low<=6 {v['low_band_mean_db']:+.2f}  high>=12 {v['high_band_mean_db']:+.2f}  "
              f"trend {v['trend_db_per_ghz']:+.3f} dB/GHz  worst {v['worst_db']:+.2f} @ {v['worst_freq_ghz']:.2f}")
    return out


if __name__ == "__main__":
    main()
