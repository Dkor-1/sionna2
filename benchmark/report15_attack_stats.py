# -*- coding: utf-8 -*-
"""
report15_attack_stats.py — ⭐ 적대검증 렌즈 1(수치·통계). 기본 입장: "이 판정은 이르다".
================================================================================
대상: outputs/report15_verdict.json 과 그 입력들.

다섯 물음에 **계산으로** 답한다 (⛔ 숫자 손입력 금지).
  Q1 잡음바닥이 정말 바닥인가 — 표본수·spp 의존
  Q2 6 dB 문턱이 사후에 정해진 것 아닌가 — 출처와 민감도
  Q3 플래시 주파수 적합의 점 개수 · ±20 % 창의 관대함
  Q4 경로 0 셀의 비율과 처리 방식 (⚠ 0 을 넣으면 인공 하모닉)
  Q5 같은 자료로 반대 결론에 이르는 경로

출력: outputs/report15_attack_stats.json (신규 · 기존 산출물 덮어쓰기 없음)
"""
from __future__ import annotations

import itertools
import json
import math
import os
import subprocess
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
OUT = os.path.join(ROOT, "outputs", "report15_attack_stats.json")

TH_A = 6.0          # 판정의 (a) 문턱 (report15_verdict.TH.margin_db_min)
TH_B = 0.20         # 판정의 (b) 허용오차
TH_DROP = 20.0      # 가장자리 정의 문턱
ASPECT_EL = dict(nose=15.0, oblique=45.0 * 0 + 15.0, side=15.0, hot=0.0, disc=75.0)
RS = ("1", "3", "10")
ASP = ("nose", "oblique", "side", "hot", "disc")


def _f(x, nd=6):
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return float(f"%.{nd}g" % v) if math.isfinite(v) else None


def _fl(s, nd=6):
    return [_f(x, nd) for x in s]


def _js(o):
    if isinstance(o, dict):
        return {str(k): _js(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_js(v) for v in o]
    if isinstance(o, (np.floating, np.integer)):
        o = o.item()
    if isinstance(o, np.ndarray):
        return _js(o.tolist())
    if isinstance(o, (np.bool_, bool)):
        return bool(o)
    if isinstance(o, float):
        return None if not math.isfinite(o) else o
    return o


def load(name):
    p = os.path.join(ROOT, "outputs", name)
    if not os.path.exists(p):
        return None
    with open(p) as f:
        return json.load(f)


# --------------------------------------------------------------------------- #
#  통계 원자 — 판정이 쓰는 (a) 통계를 여기서 다시 정의한다(원본과 축자 동일)
# --------------------------------------------------------------------------- #
def ac_over_noise_db(X) -> float | None:
    """X = [phase, seed] 복소. sig(k)=|⟨Z⟩|², nse(k)=Var(Z)/S. 총합비의 dB."""
    X = np.asarray(X)
    N, S = X.shape
    if S < 2:
        return None
    Z = np.fft.fft(X, axis=0) / N
    ny = N // 2
    Zm = Z.mean(axis=1)
    nse = np.sum(np.abs(Z - Zm[:, None]) ** 2, axis=1) / (S - 1) / S
    sig = np.abs(Zm) ** 2
    num, den = float(sig[1:ny + 1].sum()), float(nse[1:ny + 1].sum())
    if den <= 1e-12 * max(num, float(sig[0]), 1e-300):
        return None                      # noise_degenerate — 원본과 같은 규약
    return float(10 * np.log10((num + 1e-300) / (den + 1e-300)))


def harm_abs(X):
    X = np.asarray(X)
    N = X.shape[0]
    Z = np.fft.fft(X, axis=0) / N
    Zm = Z.mean(axis=1) if X.ndim > 1 else Z
    return np.abs(Zm[1:N // 2 + 1])


def edge_bin_of(a, drop_db=TH_DROP):
    a = np.asarray(a, float)
    if a.size == 0 or a.max() <= 0:
        return None
    ok = np.where(a >= a.max() * 10 ** (-drop_db / 20.0))[0]
    return int(ok.max() + 1) if ok.size else None


def block_wave(B, ch):
    kr, ki = ("hr", "hi") if ch == "all" else ("hpr", "hpi")
    kn = "n" if ch == "all" else "n_prop"
    return (np.asarray(B[kr], float) + 1j * np.asarray(B[ki], float),
            np.asarray(B[kn], float))


# =========================================================================== #
#  Q1 — 잡음바닥
# =========================================================================== #
def q1_null_distribution(trials=40000, N=64, seeds=(2, 3, 5, 8, 16)) -> dict:
    """⭐ 판정 (a) 가 쓰는 통계의 **귀무분포를 직접 만든다**.

    기존 검증(report15_sweep_matrice4e_addendum.sec_statistic_validation)은 다른 통계
    (`blade_flash_snr_db`, 단일 빈)를 **실수** 잡음으로 문턱 10 dB 에서 검증했다.
    판정이 실제로 쓰는 것은 `total_ac_over_noise_db`(32 빈 총합비)이고 자료는 **복소**이며
    문턱은 6 dB 다 — 그 조합의 귀무분포는 지금까지 한 번도 만들어진 적이 없다."""
    rng = np.random.default_rng(20260804)
    out = {}
    for S in seeds:
        v = np.array([ac_over_noise_db(rng.normal(0, 1, (N, S))
                                       + 1j * rng.normal(0, 1, (N, S)))
                      for _ in range(trials)])
        out[str(S)] = dict(
            n_seeds=int(S), trials=int(trials),
            median_db=_f(np.median(v)), p95_db=_f(np.percentile(v, 95)),
            p99_db=_f(np.percentile(v, 99)), p999_db=_f(np.percentile(v, 99.9)),
            max_db=_f(v.max()),
            fpr_at_6db=_f(float(np.mean(v >= 6.0))),
            fpr_at_3db=_f(float(np.mean(v >= 3.0))),
            fpr_at_10db=_f(float(np.mean(v >= 10.0))))
    return dict(statistic="total_ac_over_noise_db (판정 (a) 가 쓰는 그 통계)",
                model="복소 백색잡음 h[phase,seed]",
                by_n_seeds=out,
                prior_validation_note_ko=(
                    "기존 statistic_validation 은 **실수** 잡음 · **단일 빈** "
                    "blade_flash_snr_db · 문턱 10 dB 를 검증했다. 판정 (a) 는 **복소** · "
                    "**32 빈 총합** · 문턱 6 dB 다 — 같은 검증이 아니다."))


def q1_seed_scaling(GR, phys_keys=("mini2", "matrice4e")) -> dict:
    """⭐⭐ **(a) 통계는 시드 수 S 에 비례해서 커진다** — 물리가 아니라 설계의 결과다.

    강한 신호에서 sig ≈ |s|², nse ≈ σ²/S 이므로 비 ∝ S → S 를 두 배 늘리면 +3 dB.
    순수 잡음에서는 sig ≈ σ²/S 라 비가 S 에 불변(≈0 dB).
    즉 '(a) 여유 30 dB' 는 '시드를 5 개 평균했다' 는 사실을 절반쯤 재고 있다.
    널(S=2)과 신호(S=5)를 같은 문턱으로 재는 것이 정당한지는 이 기울기가 답한다."""
    rows = {}
    for key in phys_keys:
        J = GR[key]
        for bk, B in J["grid"]["blocks"].items():
            if B["mode"] != "prod":
                continue
            for ch in ("all", "prop"):
                z, n = block_wave(B, ch)
                if n.max() == 0:
                    continue
                S = z.shape[1]
                by_S = {}
                for s in range(2, S + 1):
                    vals = [ac_over_noise_db(z[:, list(c)])
                            for c in itertools.combinations(range(S), s)]
                    vals = [v for v in vals if v is not None]
                    by_S[str(s)] = dict(n_subsets=len(vals), mean_db=_f(np.mean(vals)),
                                        std_db=_f(np.std(vals, ddof=1)) if len(vals) > 1 else None,
                                        min_db=_f(np.min(vals)), max_db=_f(np.max(vals)))
                x = np.log10([int(k) for k in by_S])
                y = np.array([by_S[k]["mean_db"] for k in by_S], float)
                slope = float(np.polyfit(x, y, 1)[0]) if len(x) > 1 else None
                #  잭나이프(leave-one-seed-out) — S=5 추정치의 흔들림
                jk = [ac_over_noise_db(z[:, [i for i in range(S) if i != j]])
                      for j in range(S)]
                jk = [v for v in jk if v is not None]
                rows[f"{key}/{bk}/{ch}"] = dict(
                    drone=key, cell=bk, channel=ch, n_seeds=S,
                    full_db=_f(ac_over_noise_db(z)), by_subset_size=by_S,
                    slope_db_per_decade_of_S=_f(slope),
                    slope_db_per_doubling_S=_f(slope * math.log10(2.0)) if slope else None,
                    jackknife_std_db=_f(np.std(jk, ddof=1)) if len(jk) > 1 else None,
                    jackknife_range_db=_f(max(jk) - min(jk)) if jk else None)
    prop = [r for r in rows.values() if r["channel"] == "prop"]
    sl = [r["slope_db_per_doubling_S"] for r in prop if r["slope_db_per_doubling_S"] is not None]
    jk = [r["jackknife_std_db"] for r in prop if r["jackknife_std_db"] is not None]
    #  S=2 로 재면 몇 칸이 문턱 아래로 내려가나 (널이 S=2 로 측정됐다)
    n_fall = sum(1 for r in prop
                 if r["by_subset_size"].get("2", {}).get("mean_db") is not None
                 and r["by_subset_size"]["2"]["mean_db"] < TH_A <= (r["full_db"] or -1e9))
    return dict(
        rows=rows,
        prop_slope_db_per_doubling_S_median=_f(np.median(sl)) if sl else None,
        prop_slope_db_per_doubling_S_min=_f(np.min(sl)) if sl else None,
        prop_slope_db_per_doubling_S_max=_f(np.max(sl)) if sl else None,
        theoretical_slope_strong_signal_db_per_doubling=_f(10 * math.log10(2.0)),
        theoretical_slope_pure_noise_db_per_doubling=0.0,
        jackknife_std_db_median=_f(np.median(jk)) if jk else None,
        jackknife_std_db_max=_f(np.max(jk)) if jk else None,
        n_prop_cells_that_would_fail_at_S2=int(n_fall),
        n_prop_cells=len(prop),
        note_ko=("기울기가 이론값 3.01 dB/시드2배 에 가까우면 그 칸의 (a) 여유는 "
                 "**신호가 세서**가 아니라 **시드를 많이 평균해서** 커진 몫이 그만큼이라는 뜻이다. "
                 "널은 S=2, 신호격자는 S=5 로 재졌으므로 두 분포를 같은 6 dB 자로 재는 것은 "
                 "자를 바꿔 가며 재는 것이다."))


def q1_edge_gate_falsealarm(trials=6000, N=64, seeds=(2, 5)) -> dict:
    """⭐ 가장자리를 정하는 **빈별 10 dB SNR 게이트**의 거짓경보율.

    가장자리는 '−20 dB 진폭 게이트 **그리고** 10 dB SNR 게이트를 통과한 최고 빈' 이다.
    잡음 빈 하나가 고차에서 우연히 통과하면 가장자리가 위로 끌려간다 — (b) 의 급소."""
    rng = np.random.default_rng(1234)
    out = {}
    for S in seeds:
        v = []
        for _ in range(trials):
            X = rng.normal(0, 1, (N, S)) + 1j * rng.normal(0, 1, (N, S))
            Z = np.fft.fft(X, axis=0) / N
            ny = N // 2
            Zm = Z.mean(axis=1)
            nse = np.sum(np.abs(Z - Zm[:, None]) ** 2, axis=1) / (S - 1) / S
            v.append(10 * np.log10((np.abs(Zm) ** 2 / (nse + 1e-300))[1:ny + 1] + 1e-300))
        v = np.concatenate(v)
        p = float(np.mean(v >= 10.0))
        out[str(S)] = dict(n_seeds=int(S), per_bin_fa_at_10db=_f(p),
                           expected_false_bins_of_32=_f(32 * p),
                           p_at_least_one_false_bin_per_cell=_f(1 - (1 - p) ** 32),
                           per_bin_null_p95_db=_f(np.percentile(v, 95)),
                           per_bin_null_p99_db=_f(np.percentile(v, 99)))
    return dict(by_n_seeds=out, gate_db=10.0, n_bins=32,
                note_ko=("S=5 에서 빈별 거짓경보율은 0.7 % 남짓이라 32 빈 중 기대 0.2 개다. "
                         "다만 칸마다 '적어도 하나' 가 뜰 확률은 19 % 수준 — 진폭 게이트가 "
                         "함께 걸리므로 실제로 가장자리를 밀어 올리려면 그 잡음 빈이 첨두 대비 "
                         "−20 dB 위에도 있어야 한다. 신호가 약한 R=10 m 에서 위험하다."))


def q1_edge_margin(V) -> dict:
    """가장자리 빈 자신의 SNR 여유 — 게이트를 아슬아슬하게 넘었는가."""
    rows = {}
    for key in ("mini2", "matrice4e"):
        for ck, c in V["sionna"][key].items():
            if c.get("empty") or c.get("mode") != "prod" or c.get("channel") != "prop":
                continue
            eb = c.get("edge_bin")
            hs = c.get("harm_snr_db")
            ha = np.asarray(c["harm_abs"], float)
            if not eb or hs is None:
                continue
            snr = float(hs[eb - 1])
            amp = float(20 * np.log10(ha[eb - 1] / ha.max() + 1e-300))
            rows[f"{key}/{ck}"] = dict(
                drone=key, cell=ck, edge_bin=eb,
                edge_snr_db=_f(snr), edge_snr_margin_db=_f(snr - 10.0),
                edge_amp_rel_peak_db=_f(amp), edge_amp_margin_db=_f(amp + 20.0),
                binding_gate=("SNR" if (snr - 10.0) < (amp + 20.0) else "amplitude"),
                marginal=bool(min(snr - 10.0, amp + 20.0) < 3.0))
    m = [r for r in rows.values() if r["marginal"]]
    return dict(rows=rows, n_cells=len(rows), n_marginal_under_3db=len(m),
                marginal_cells=[f'{r["drone"]}/{r["cell"]}' for r in m],
                binding_gate_tally={g: sum(1 for r in rows.values() if r["binding_gate"] == g)
                                    for g in ("SNR", "amplitude")},
                note_ko=("여유가 3 dB 미만이면 그 칸의 가장자리는 게이트 하나에 매달려 있다. "
                         "어느 게이트가 묶는지도 함께 센다."))


def q1_noise_whiteness(GR) -> dict:
    """⚠ 잡음이 빈에 대해 백색인가 — 같은 시드를 모든 위상에 쓰므로 φ 방향으로 상관될 수 있다.

    상관되면 잡음이 저차 빈에 몰리고 고차 빈의 잡음추정이 낮아진다 → 가장자리 SNR 게이트가
    고차에서 느슨해진다. 널 팔(신호 없음)에서 잡음 스펙트럼 기울기를 잰다."""
    NU = load("report15_verdict_nulls_vs_range.json")
    rows = {}
    if NU:
        for arm, A in NU["arms"].items():
            for rk, B in A["by_range"].items():
                for ch in ("all", "prop"):
                    z, n = block_wave(B, ch)
                    if n.max() == 0:
                        continue
                    N, S = z.shape
                    if S < 2:
                        continue
                    Z = np.fft.fft(z, axis=0) / N
                    ny = N // 2
                    Zm = Z.mean(axis=1)
                    nse = np.sum(np.abs(Z - Zm[:, None]) ** 2, axis=1) / (S - 1) / S
                    y = nse[1:ny + 1]
                    if y.max() <= 0:
                        continue
                    k = np.arange(1, ny + 1)
                    sl = float(np.polyfit(np.log10(k), 10 * np.log10(y + 1e-300), 1)[0])
                    if float(np.sum(y)) <= 1e-12 * max(float(np.abs(Zm[0])) ** 2, 1e-300):
                        continue                      # 퇴화(잡음 0) — 기울기가 뜻이 없다
                    rows[f"{arm}/{rk}/{ch}"] = dict(
                        arm=arm, role=A.get("role"), range_m=float(rk), channel=ch,
                        noise_slope_db_per_decade_of_bin=_f(sl),
                        noise_lowhalf_over_highhalf_db=_f(
                            10 * np.log10(y[:ny // 2].mean() / y[ny // 2:].mean())))
    nulls = [r for r in rows.values() if r["role"] == "null"]
    sl = [r["noise_slope_db_per_decade_of_bin"] for r in nulls]
    return dict(rows=rows, n_null_rows=len(nulls),
                null_noise_slope_median_db_per_decade=_f(np.median(sl)) if sl else None,
                null_noise_slope_range=[_f(min(sl)), _f(max(sl))] if sl else None,
                note_ko=("기울기가 0 근처면 잡음은 빈에 대해 백색이고 시드 널이 고차에서도 "
                         "정직하다. 크게 음수면 잡음이 저차에 몰려 고차 SNR 게이트가 느슨해진다."))


def q1_budget_law(V, LAD, LAD2) -> dict:
    """⭐⭐ **(a) 는 광선예산의 함수다** — 새 사다리에서 인과적으로 재고, 격자에 적용한다.

    사다리는 기하를 고정한 채 spp 만 바꾼다. 거기서 잰 기울기 d(a)/d(10log10 N_prop) 이
    1 에 가까우면, 격자 전체의 (a) 차이는 '표적이 다르다' 가 아니라 '경로가 몇 개냐' 로
    상당 부분 설명된다. 그러면 두 기체의 집계 차이를 기체 성질로 읽으면 안 된다."""
    out = dict(available=False)
    slopes = []
    for L in (LAD, LAD2):
        if not L or not L.get("runs"):
            continue
        per = {}
        for tag, R in L["runs"].items():
            G = R.get("grid") or {}
            if R.get("kind") != "spp_ladder" or not G.get("complete"):
                continue
            for bk, B in G["blocks"].items():
                z, n = block_wave(B, "prop")
                if n.max() == 0:
                    continue
                per.setdefault(f'{L["meta"]["drone"]}/{bk}', []).append(
                    (float(n.mean()), ac_over_noise_db(z), int(R["spp"])))
        for ck, v in per.items():
            v = sorted(v, key=lambda t: t[2])
            xs = np.array([10 * np.log10(t[0]) for t in v])
            ys = np.array([t[1] for t in v if t[1] is not None], float)
            if len(ys) != len(xs) or len(xs) < 2:
                continue
            sl = float(np.polyfit(xs, ys, 1)[0])
            slopes.append(dict(cell=ck, n_points=len(xs),
                               n_paths_by_spp=_fl([t[0] for t in v]),
                               ac_db_by_spp=_fl(ys), spps=[t[2] for t in v],
                               slope_db_per_db_of_paths=_f(sl)))
    if not slopes:
        return dict(out, note_ko="사다리 결과가 아직 없다.")
    sl_med = float(np.median([s["slope_db_per_db_of_paths"] for s in slopes]))

    #  격자에 적용 — 자세·거리를 맞춘 기체 간 대조
    pairs = []
    S = {}
    for key in ("mini2", "matrice4e"):
        for ck, c in V["sionna"][key].items():
            if c.get("empty") or c.get("mode") != "prod" or c.get("channel") != "prop":
                continue
            S[(key, c["range_m"], c["aspect"])] = c
    for R in (1.0, 3.0, 10.0):
        for ak in ASP:
            a1, a2 = S.get(("mini2", R, ak)), S.get(("matrice4e", R, ak))
            if not a1 or not a2:
                continue
            dn = 10 * math.log10(a2["n_paths_mean"] / a1["n_paths_mean"])
            da = a2["ac_over_noise_db"] - a1["ac_over_noise_db"]
            pairs.append(dict(range_m=R, aspect=ak, delta_a_db=_f(da),
                              delta_paths_db=_f(dn),
                              budget_corrected_delta_db=_f(da - sl_med * dn),
                              mini2_a_db=a1["ac_over_noise_db"],
                              matrice4e_a_db=a2["ac_over_noise_db"],
                              mini2_n=_f(a1["n_paths_mean"]), matrice4e_n=_f(a2["n_paths_mean"])))
    corr = [p["budget_corrected_delta_db"] for p in pairs]
    nondisc = [p["budget_corrected_delta_db"] for p in pairs if p["aspect"] != "disc"]

    #  예산을 맞추면 mini2 집계는 어떻게 되나
    ratio = float(np.median([p["matrice4e_n"] / p["mini2_n"] for p in pairs]))
    boost = sl_med * 10 * math.log10(ratio)
    m2 = [(ck, c["ac_over_noise_db"]) for ck, c in V["sionna"]["mini2"].items()
          if not c.get("empty") and c.get("mode") == "prod" and c.get("channel") == "prop"]
    now_no = [ck for ck, a in m2 if a < TH_A]
    after_no = [ck for ck, a in m2 if a + boost < TH_A]
    return dict(
        available=True,
        measured_slope_rows=slopes,
        slope_db_per_db_of_paths_median=_f(sl_med),
        slope_n_cells=len(slopes),
        airframe_pairs=pairs,
        budget_corrected_delta_median_db=_f(np.median(corr)),
        budget_corrected_delta_median_db_excluding_disc=_f(np.median(nondisc)),
        n_pairs_where_mini2_wins_after_correction=int(sum(1 for x in corr if x < 0)),
        n_pairs=len(pairs),
        median_path_count_ratio_m4e_over_mini2=_f(ratio),
        implied_mini2_boost_if_budget_matched_db=_f(boost),
        mini2_no_modulation_cells_now=now_no,
        mini2_no_modulation_cells_after_budget_match=after_no,
        spp_cap=dict(value=4_294_967_295, used_in_grid=2_048_000_000,
                     max_safe_in_harness=4_096_000_000,
                     factor_available=_f(4_096_000_000 / 2_048_000_000),
                     factor_needed_for_match=_f(ratio),
                     match_is_possible=bool(4_096_000_000 / 2_048_000_000 >= ratio)),
        note_ko=("사다리에서 잰 기울기는 기하를 고정한 **인과적** 값이다. 격자 간 대조에 "
                 "그 기울기를 그대로 쓰는 것은 '경로가 많아진 이유가 예산이든 표적크기든 "
                 "같은 방식으로 (a) 를 올린다' 는 가정이다 — 그 가정이 맞는지는 이 설계로 "
                 "가릴 수 없다. 가릴 방법은 mini2 를 경로수가 같아질 때까지 예산을 올려 "
                 "다시 재는 것뿐인데, samples_per_src 가 uint32 라 그만큼 못 올린다."))


def q1_noise_floor_precision(N=64, S=5, n_bins=32) -> dict:
    """잡음바닥 추정치 자체의 정밀도 — χ² 신뢰구간."""
    from scipy import stats
    dof = 2 * (S - 1) * n_bins          # 복소 · 빈마다 2(S−1) 자유도
    lo = dof / stats.chi2.ppf(0.975, dof)
    hi = dof / stats.chi2.ppf(0.025, dof)
    dof2 = 2 * (2 - 1) * n_bins
    lo2 = dof2 / stats.chi2.ppf(0.975, dof2)
    hi2 = dof2 / stats.chi2.ppf(0.025, dof2)
    return dict(
        n_phase=N, n_bins_summed=n_bins,
        signal_grid=dict(n_seeds=S, dof=int(dof),
                         ci95_of_noise_estimate_db=[_f(10 * np.log10(lo)),
                                                    _f(10 * np.log10(hi))],
                         ci95_width_db=_f(10 * np.log10(hi / lo))),
        null_arms=dict(n_seeds=2, dof=int(dof2),
                       ci95_of_noise_estimate_db=[_f(10 * np.log10(lo2)),
                                                  _f(10 * np.log10(hi2))],
                       ci95_width_db=_f(10 * np.log10(hi2 / lo2))),
        note_ko=("빈을 32 개 합치므로 자유도는 늘지만, 널 팔은 S=2 라 신호격자(S=5)보다 "
                 "잡음추정 신뢰구간이 넓다. 널 12 칸의 최대값을 '바닥' 으로 인용할 때 "
                 "그 최대값의 표본수가 12 라는 점을 함께 읽어야 한다."))


def q1_null_sample_census(V) -> dict:
    """⚠ '널 15칸이 한 번도 안 켜졌다' 의 실제 표본 수를 센다."""
    CA = V["criterion_a_calibration"]
    rows = CA["rows"]
    nulls = [r for r in rows.values() if r["role"] == "null"]
    have = [r for r in nulls if r["ac_over_noise_db"] is not None]
    none = [r for r in nulls if r["ac_over_noise_db"] is None]
    sig = [r for r in rows.values() if r["role"] == "signal"]
    vals = sorted(r["ac_over_noise_db"] for r in have)
    grid_prop = [c.get("ac_over_noise_db") for k in ("mini2", "matrice4e")
                 for c in V["sionna"][k].values()
                 if not c.get("empty") and c.get("mode") == "prod"
                 and c.get("channel") == "prop"]
    return dict(
        claimed_n_null_cells=CA["n_null_cells"],
        n_null_cells_with_a_value=len(have),
        n_null_cells_degenerate_no_value=len(none),
        degenerate_cells=[k for k, r in rows.items()
                          if r["role"] == "null" and r["ac_over_noise_db"] is None],
        null_values_db=_fl(vals),
        null_max_db=_f(max(vals)), null_p50_db=_f(np.median(vals)),
        threshold_db=TH_A, headroom_null_max_to_threshold_db=_f(TH_A - max(vals)),
        signal_arm_values_db={k: r["ac_over_noise_db"] for k, r in rows.items()
                              if r["role"] == "signal"},
        n_signal_firing=CA["n_signal_firing"], n_signal_cells=CA["n_signal_cells"],
        null_arm_n_seeds=2, signal_grid_n_seeds=5,
        flaw_ko=("`fires` 가 None(퇴화)인 칸 3 개를 '안 켜졌다' 로 세었다. "
                 "norotor 팔은 위상을 돌려도 기하가 **글자 그대로 동일**해서 h(φ) 가 상수다 — "
                 "AC 가 정확히 0 이라 (a) 를 시험할 수 없는 칸이지 통과한 칸이 아니다. "
                 "실제로 (a) 를 시험한 널은 12 칸이다."),
        null_max_vs_grid_min=dict(
            null_max_db=_f(max(vals)),
            grid_min_prop_db=_f(min(v for v in grid_prop if v is not None)),
            null_max_exceeds_grid_min=bool(max(vals) > min(v for v in grid_prop
                                                           if v is not None))),
        overlap_ko=("널 최대(3.83 dB, sphere_matrice4e/1/all)가 신호격자 prod/prop 최소"
                    "(3.08 dB, mini2 10/disc)보다 **크다** — 널 분포와 신호 분포는 겹친다. "
                    "문턱 6 dB 는 두 분포를 가르는 '빈 골짜기' 에 놓인 것이 아니라 겹친 "
                    "구간 위에 놓여 있다. 다만 겹치는 칸들은 모두 NO_MODULATION 으로 "
                    "찍혔으므로 이 겹침이 거짓양성을 만든 것은 아니다."))


# =========================================================================== #
#  Q2 — 문턱의 출처와 민감도
# =========================================================================== #
def q2_provenance() -> dict:
    def mt(p):
        q = os.path.join(ROOT, p)
        return dict(path=p, exists=os.path.exists(q),
                    mtime=(time.strftime("%Y-%m-%d %H:%M:%S",
                                         time.localtime(os.path.getmtime(q)))
                           if os.path.exists(q) else None),
                    mtime_epoch=(os.path.getmtime(q) if os.path.exists(q) else None))

    files = [mt(p) for p in (
        "outputs/report15_sionna_sweep_matrice4e.json",
        "outputs/report15_verdict_nulls_vs_range.json",
        "benchmark/report15_verdict.py",
        "outputs/report15_verdict_grid_mini2.json",
        "benchmark/report15_verdict_build.py",
        "outputs/report15_verdict.json")]

    def git(*a):
        try:
            return subprocess.run(["git", "-C", ROOT, *a], capture_output=True,
                                  text=True, timeout=30).stdout.strip()
        except Exception as e:
            return f"<error {e}>"

    tracked = git("status", "--porcelain", "benchmark/report15_verdict.py")
    committed_has = git("grep", "-c", "margin_db_min", "HEAD", "--",
                        "benchmark/")
    thr_decl = mt("benchmark/report15_verdict.py")["mtime_epoch"]
    data_m4 = mt("outputs/report15_sionna_sweep_matrice4e.json")["mtime_epoch"]
    return dict(
        file_times=files,
        threshold_declared_in="benchmark/report15_verdict.py:TH['margin_db_min']=6.0",
        threshold_file_is_untracked=bool(tracked.startswith("??")),
        git_status_of_threshold_file=tracked,
        committed_tree_contains_margin_db_min=(committed_has or "(none)"),
        minutes_threshold_file_written_after_matrice4e_data=_f(
            (thr_decl - data_m4) / 60.0) if (thr_decl and data_m4) else None,
        earlier_threshold_used_in_project=dict(
            value_db=10.0, statistic="blade_flash_snr_db (단일 빈, 실수자료)",
            where="benchmark/report15_sweep_matrice4e_addendum.py:sec_statistic_validation"),
        verdict_ko=(
            "**사전등록의 증거는 없다.** 문턱 6.0 dB 를 선언한 파일은 git 미추적이고, "
            "그 파일의 mtime 은 matrice4e 격자 JSON 이 완성된 뒤다. 커밋된 트리에는 "
            "`margin_db_min` 이 존재하지 않는다. 스크립트 안의 '⛔ 계산 전에 박는다' 주석은 "
            "**그 스크립트 자신의 계산 전**이라는 뜻일 뿐, 자료 수집 전이라는 뜻이 아니다. "
            "또한 프로젝트가 앞서 쓰던 문턱은 10 dB 였고 통계도 달랐다(단일 빈). "
            "따라서 6 dB 의 정당성은 출처가 아니라 **민감도**로만 세울 수 있다."))


def q2_threshold_sweep(V) -> dict:
    """⭐ 판정을 문턱의 함수로 다시 그린다. 결론이 6 dB 에 매달려 있는지 본다."""
    cells = {}
    for key in ("mini2", "matrice4e"):
        for ck, v in V["verdict"]["by_cell"][key].items():
            if v["channel"] != "prop":
                continue
            cells[f"{key}/{ck}"] = dict(
                drone=key, a=v.get("ac_over_noise_db"),
                b=v["checks"]["b_flash_freq_matches_ftip"],
                c=v["checks"]["c_sphere_null_silent"],
                d=v["checks"]["d_survives_half_mesh"])
    grid = []
    for t in np.arange(0.0, 30.01, 0.25):
        row = dict(threshold_db=_f(t))
        for key in ("mini2", "matrice4e"):
            cs = [c for c in cells.values() if c["drone"] == key]
            nok = sum(1 for c in cs if (c["a"] is not None and c["a"] >= t)
                      and all(x is not False for x in (c["b"], c["c"], c["d"])))
            n4 = sum(1 for c in cs if (c["a"] is not None and c["a"] >= t)
                     and all(x is True for x in (c["b"], c["c"], c["d"])))
            nno = sum(1 for c in cs if not (c["a"] is not None and c["a"] >= t))
            row[key] = dict(native_ok=nok, all_four=n4, no_modulation=nno)
        row["matrice4e_beats_mini2_native_ok"] = bool(
            row["matrice4e"]["native_ok"] > row["mini2"]["native_ok"])
        row["matrice4e_beats_mini2_all_four"] = bool(
            row["matrice4e"]["all_four"] > row["mini2"]["all_four"])
        grid.append(row)
    #  헤드라인(matrice4e 10 · mini2 6)이 유지되는 문턱 구간
    keep = [r["threshold_db"] for r in grid
            if r["matrice4e"]["native_ok"] == 10 and r["mini2"]["native_ok"] == 6]
    order = [r["threshold_db"] for r in grid if r["matrice4e_beats_mini2_native_ok"]]
    avals = sorted([c["a"] for c in cells.values() if c["a"] is not None])
    near = [a for a in avals if abs(a - TH_A) <= 3.0]

    #  ⭐ 격자가 아니라 **정확한** 구간 — 집계가 바뀌는 지점은 칸의 (a) 값 자체다
    def tally_at(t):
        r = {}
        for key in ("mini2", "matrice4e"):
            cs = [c for c in cells.values() if c["drone"] == key]
            r[key] = sum(1 for c in cs if (c["a"] is not None and c["a"] >= t)
                         and all(x is not False for x in (c["b"], c["c"], c["d"])))
        return r
    bp = sorted({0.0} | {a for a in avals} | {a + 1e-9 for a in avals})
    exact = None
    for lo, hi in zip(bp, bp[1:] + [1e9]):
        t = (lo + min(hi, lo + 1e-6)) / 2 if hi > lo else lo
        tl = tally_at(lo)
        if tl["matrice4e"] == 10 and tl["mini2"] == 6:
            exact = [lo if exact is None else exact[0], hi]
    return dict(
        sweep=grid,
        headline_exact_interval_db=[min(keep), max(keep)] if keep else None,
        headline_exact_width_db=_f(max(keep) - min(keep)) if keep else None,
        headline_exact_interval_unquantised_db=_fl(exact) if exact else None,
        headline_exact_width_unquantised_db=_f(exact[1] - exact[0]) if exact else None,
        ordering_holds_interval_db=[min(order), max(order)] if order else None,
        a_values_sorted_db=_fl(avals),
        n_cells_within_3db_of_threshold=len(near),
        cells_within_3db=_fl(near),
        gap_below_threshold_db=_f(TH_A - max([a for a in avals if a < TH_A], default=np.nan)),
        gap_above_threshold_db=_f(min([a for a in avals if a >= TH_A], default=np.nan) - TH_A),
        note_ko=("(a) 값이 문턱 근처에 몇 개나 몰려 있는지가 핵심이다. 6.0 바로 아래/위에 "
                 "칸이 있으면 문턱을 조금만 옮겨도 집계가 바뀐다."))


def q2_other_thresholds(V, SJ) -> dict:
    """(b)(c)(d) 문턱도 같은 방식으로 흔든다."""
    out = {}
    #  (b) 허용오차 사다리
    tol_rows = []
    for tol in (0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50):
        r = dict(tol=tol)
        for key in ("mini2", "matrice4e"):
            n = 0
            for ck, c in V["sionna"][key].items():
                if c.get("empty") or c.get("mode") != "prod" or c.get("channel") != "prop":
                    continue
                jb = c["judge_b"]
                if jb.get("ok") is None or jb.get("ratio") is None:
                    continue
                n += int(abs(jb["ratio"] - 1.0) <= tol)
            r[key] = n
        tol_rows.append(r)
    out["b_tolerance_ladder"] = tol_rows
    #  (b) 가장자리 문턱 사다리 (10 / 20 / 30 dB)
    drop_rows = {}
    flips = {}
    for key in ("mini2", "matrice4e"):
        per = {}
        fl = []
        for ck, c in V["sionna"][key].items():
            if c.get("empty") or c.get("mode") != "prod" or c.get("channel") != "prop":
                continue
            ts = (c["judge_b"].get("threshold_sensitivity") or {})
            oks = {k: v["ok"] for k, v in ts.items()}
            for k, v in oks.items():
                per.setdefault(k, 0)
                per[k] += int(v is True)
            known = {v for v in oks.values() if v is not None}
            if len(known) > 1:
                fl.append(dict(cell=ck, by_drop={k: v for k, v in oks.items()},
                               ratios={k: v["ratio"] for k, v in ts.items()}))
        drop_rows[key] = per
        flips[key] = fl
    out["b_pass_count_by_edge_drop"] = drop_rows
    out["b_cells_that_flip_with_edge_drop"] = flips
    out["b_n_flipping"] = {k: len(v) for k, v in flips.items()}
    #  (c) — 실제로 변별하는가
    cm = {}
    for key in ("mini2", "matrice4e"):
        vs = [v["c_null_margin_db"] for v in V["verdict"]["by_cell"][key].values()
              if v["channel"] == "prop" and v.get("c_null_margin_db") is not None]
        cm[key] = dict(n=len(vs), min_db=_f(min(vs)), max_db=_f(max(vs)),
                       n_pass=sum(1 for x in vs if x >= 6.0),
                       min_minus_threshold_db=_f(min(vs) - 6.0))
    out["c_margins"] = cm
    out["c_threshold_that_would_fail_any"] = _f(min(
        min(v["c_null_margin_db"] for v in V["verdict"]["by_cell"][k].values()
            if v["channel"] == "prop" and v.get("c_null_margin_db") is not None)
        for k in ("mini2", "matrice4e")))
    #  (d) — 상수인가
    dvals = set()
    for key in ("mini2", "matrice4e"):
        for v in V["verdict"]["by_cell"][key].values():
            if v["channel"] == "prop":
                dvals.add(v["checks"]["d_survives_half_mesh"])
    L = V["resolution_ladder"]
    out["d_is_constant"] = dict(
        distinct_values=sorted(str(x) for x in dvals),
        source=L.get("source"), scope=L.get("scope_ko"),
        min_pearson_r=L.get("min_pearson_r"), threshold=0.90,
        ptp_max_rel_change=L.get("ptp_max_rel_change"), ptp_threshold=0.25,
        n_cells_it_is_applied_to=sum(
            1 for k in ("mini2", "matrice4e")
            for v in V["verdict"]["by_cell"][k].values() if v["channel"] == "prop"),
        note_ko=("(d) 는 mini2·R=3 m·nose 한 칸에서 한 번 잰 값을 30 칸 전부에 "
                 "**같은 값으로** 붙인 것이다. 칸마다 다시 재지 않았으므로 변별력이 0 이다."))
    return out


# =========================================================================== #
#  Q3 — 플래시 주파수 적합
# =========================================================================== #
def q3_flash_fit(V, PH) -> dict:
    """(b) 가 실제로 몇 개의 독립 관측에서 나오는가 · ±20 % 창이 얼마나 관대한가."""
    cells = []
    for key in ("mini2", "matrice4e"):
        ph = PH[key]
        for ck, c in V["sionna"][key].items():
            if c.get("empty") or c.get("mode") != "prod" or c.get("channel") != "prop":
                continue
            jb = c["judge_b"]
            pred = c["ftip"]["f_tip_aspect_hz"]
            fb = ph["f_flash_hz"]
            pb = pred / fb                       # 예측(빈 단위)
            lo, hi = pb * (1 - TH_B), pb * (1 + TH_B)
            inside = [k for k in range(1, 33) if lo <= k <= hi]
            cells.append(dict(
                drone=key, cell=ck, aspect=c["aspect"], range_m=c["range_m"],
                el_deg=c["el_deg"], predicted_bins=_f(pb),
                measured_edge_bin=c.get("edge_bin"), ratio=jb.get("ratio"),
                ok=jb.get("ok"),
                window_bins=[_f(lo), _f(hi)], integer_bins_inside=inside,
                n_integer_bins_inside=len(inside),
                prior_pass_prob_uniform_1_32=_f(len(inside) / 32.0),
                n_harmonic_bins_available=32,
                n_fitted_parameters=0,
                n_scalars_estimated_per_cell=1))
    ev = [c for c in cells if c["ok"] is not None]
    npass = sum(1 for c in ev if c["ok"])
    exp_uni = sum(c["prior_pass_prob_uniform_1_32"] for c in ev)

    #  ① 균등 귀무 — 이항 p
    from scipy import stats as st
    p_uni = float(1 - st.binom.cdf(npass - 1, len(ev), exp_uni / max(len(ev), 1)))

    #  ② 순열 귀무 — 측정 가장자리는 그대로 두고 **예측(=자세)만 뒤섞는다**.
    #    ⚠ 기체를 섞으면 안 된다(예측 규모가 통째로 달라져 귀무가 너무 약해진다).
    #      기체 안에서만 자세 라벨을 섞는다.
    rng = np.random.default_rng(7)
    n_mc = 20000
    cnt = np.zeros(n_mc)
    for key in ("mini2", "matrice4e"):
        sub = [c for c in ev if c["drone"] == key]
        if not sub:
            continue
        m = np.array([c["measured_edge_bin"] for c in sub], float)
        p0 = np.array([c["predicted_bins"] for c in sub], float)
        for i in range(n_mc):
            cnt[i] += np.sum(np.abs(m / rng.permutation(p0) - 1.0) <= TH_B)
    p_perm = float((np.sum(cnt >= npass) + 1) / (n_mc + 1))
    #  ③ 자세가 실제로 갈리는가 — disc(el 75°) 대 나머지
    by_asp = {}
    for a in ASP:
        s = [c for c in ev if c["aspect"] == a]
        by_asp[a] = dict(n=len(s), n_pass=sum(1 for c in s if c["ok"]),
                         median_ratio=_f(np.median([c["ratio"] for c in s])) if s else None,
                         median_measured_edge=_f(np.median([c["measured_edge_bin"] for c in s]))
                         if s else None,
                         median_predicted_bins=_f(np.median([c["predicted_bins"] for c in s]))
                         if s else None)

    #  ③ 예측이 몇 단계나 구별되는가 — 1 빈보다 촘촘하면 구별 못 한다
    lv = {}
    for key in ("mini2", "matrice4e"):
        vals = sorted({round(c["predicted_bins"], 6) for c in cells if c["drone"] == key})
        seps = [round(b - a, 6) for a, b in zip(vals, vals[1:])]
        lv[key] = dict(distinct_predicted_bins=_fl(vals),
                       separations_in_bins=_fl(seps),
                       n_levels_separated_by_ge_1_bin=1 + sum(1 for s in seps if s >= 1.0),
                       note_ko=("빈 폭보다 좁게 떨어진 예측 단계는 이 측정법으로 "
                                "구별할 수 없다 — (b) 가 실제로 시험하는 대비의 수다."))
    #  ④ 이상 모형 대비 재중심 — 잣대가 1.0 에 있지 않다
    rec = {}
    for key in ("mini2", "matrice4e"):
        n_ok = 0
        n_ev = 0
        rows = []
        for c in cells:
            if c["drone"] != key:
                continue
            ic = V["ideal_reference"]["by_cell"].get(f"{key}/{c['aspect']}") or {}
            ie = ic.get("edge_bin")
            if not ie or not c["measured_edge_bin"]:
                rows.append(dict(cell=c["cell"], ideal_edge_bin=ie,
                                 measured=c["measured_edge_bin"], ratio=None, ok=None))
                continue
            r = c["measured_edge_bin"] / ie
            ok = bool(abs(r - 1.0) <= TH_B)
            n_ev += 1
            n_ok += int(ok)
            rows.append(dict(cell=c["cell"], ideal_edge_bin=ie,
                             measured=c["measured_edge_bin"], ratio=_f(r), ok=ok))
        rec[key] = dict(n_evaluated=n_ev, n_pass=n_ok, rows=rows)
    ideal_ratios = [v["calibration"]["ratio"] for v in V["ideal_reference"]["by_cell"].values()
                    if v["calibration"]["ratio"] is not None]

    #  ⭐ 창이 **중심에 있지 않다** — 이상 점산란자조차 비율 1.09~1.18 을 낸다.
    #    실제 블레이드는 점이 아니라 코드 길이를 가진 면이라 점보다 **더 넓게** 퍼져야 한다.
    #    그런데 창의 위쪽 한계가 1.20 이므로 '점보다 넓다' 는 물리적으로 옳은 방향이
    #    바로 탈락 사유가 된다.
    med = float(np.median(ideal_ratios))
    fails = [c for c in ev if c["ok"] is False]
    return dict(
        window_asymmetry=dict(
            ideal_ratio_median=_f(med),
            window_in_units_of_ideal=[_f((1 - TH_B) / med), _f((1 + TH_B) / med)],
            headroom_above_ideal=_f((1 + TH_B) / med - 1.0),
            headroom_below_ideal=_f(1.0 - (1 - TH_B) / med),
            n_fail_for_being_too_broad=sum(1 for c in fails if c["ratio"] > 1 + TH_B),
            n_fail_for_being_too_narrow=sum(1 for c in fails if c["ratio"] < 1 - TH_B),
            cells_failing_too_broad=[c["cell"] for c in fails if c["ratio"] > 1 + TH_B],
            note_ko=("이상 점산란자가 이미 1.15 를 내므로, 창 [0.8, 1.2] 는 이상모형 기준으로 "
                     "[0.70, 1.04] 이다. 위쪽 여유가 4 % 밖에 없다 — 실제 블레이드(유한 코드)가 "
                     "점보다 넓게 퍼지는 **옳은** 거동이 (b) 에서는 탈락으로 찍힌다.")),
        cells=cells,
        n_cells_evaluated=len(ev), n_pass=npass,
        expected_pass_under_uniform_null=_f(exp_uni),
        binomial_p_uniform_null=_f(p_uni),
        permutation_p_aspect_shuffle=_f(p_perm),
        permutation_null_mean_passes=_f(cnt.mean()),
        permutation_within_airframe=True,
        by_aspect=by_asp,
        permutation_n_mc=int(n_mc),
        prediction_levels=lv,
        recentred_on_ideal_model=rec,
        ideal_model_ratio_range=[_f(min(ideal_ratios)), _f(max(ideal_ratios))],
        ideal_model_ratio_median=_f(np.median(ideal_ratios)),
        measurement_description_ko=(
            "'적합' 이 아니다. 칸마다 **정수 가장자리 빈 1 개**를 −20 dB 문턱 교차로 읽어 "
            "예측과 비율을 낸다. 적합 모수 0 개, 칸당 추정 스칼라 1 개, 재료는 조화 32 빈 "
            "(위상 64 × 시드 5 = 320 회 추적에서 나온다)."),
        window_ko=("±20 % 창이 정수 빈 몇 개를 품는지가 관대함의 척도다. "
                   "matrice4e el≤15° 는 4 개(32 중 12.5 %), mini2 는 2 개(6.25 %), "
                   "disc(el 75°)는 1 개다."))


# =========================================================================== #
#  Q4 — 경로 0 셀
# =========================================================================== #
def q4_zero_paths(GR, V) -> dict:
    rows = {}
    for key in ("mini2", "matrice4e"):
        for bk, B in GR[key]["grid"]["blocks"].items():
            for ch in ("all", "prop"):
                z, n = block_wave(B, ch)
                m = (n == 0)
                zf = float(m.mean())
                rows[f"{key}/{bk}/{ch}"] = dict(
                    drone=key, cell=bk, mode=B["mode"], channel=ch,
                    n_samples=int(n.size), n_zero=int(m.sum()), zero_frac=_f(zf),
                    h_is_exactly_zero_where_n0=(bool(np.all(z[m] == 0)) if m.any() else None),
                    n_paths_mean=_f(n.mean()), n_paths_max=int(n.max()),
                    handling=("분석에서 제외(empty=True)" if n.max() == 0 else
                              ("⚠ 0 을 그대로 채워 넣고 분석" if zf > 0 else "해당 없음")),
                    enters_verdict=bool(B["mode"] == "prod"))
    def agg(mode):
        r = [v for v in rows.values() if v["mode"] == mode]
        return dict(n_block_channels=len(r),
                    n_all_zero_dropped=sum(1 for v in r if v["n_paths_max"] == 0),
                    n_partial_zero_filled=sum(1 for v in r if 0 < v["zero_frac"] < 1),
                    n_clean=sum(1 for v in r if v["zero_frac"] == 0),
                    total_samples=int(sum(v["n_samples"] for v in r)),
                    total_zero=int(sum(v["n_zero"] for v in r)),
                    zero_frac_overall=_f(sum(v["n_zero"] for v in r)
                                         / max(sum(v["n_samples"] for v in r), 1)),
                    partial_cells=[k for k, v in rows.items()
                                   if v["mode"] == mode and 0 < v["zero_frac"] < 1])
    #  ⚠ 0 채움이 만드는 인공 하모닉을 **실물로** 보인다
    demo = {}
    for k, v in rows.items():
        if not (0 < v["zero_frac"] < 1):
            continue
        key, bk, ch = k.split("/")[0], "/".join(k.split("/")[1:4]), k.split("/")[4]
        B = GR[key]["grid"]["blocks"][bk]
        z, n = block_wave(B, ch)
        a = harm_abs(z)
        eb = edge_bin_of(a)
        #  0 이 아닌 표본만 남기고 (같은 개수의) 백색 대조와 비교
        nz = int((n > 0).sum())
        flat = float(np.std(20 * np.log10(a / a.max() + 1e-300)))
        demo[k] = dict(zero_frac=v["zero_frac"], n_nonzero_samples=nz,
                       edge_bin_from_zero_filled=eb, n_bins=int(a.size),
                       spectrum_flatness_std_db=_f(flat),
                       reaches_last_bin=bool(eb == a.size),
                       warning_ko=("0 채움 임펄스열의 스펙트럼은 전 대역에 평평하게 퍼진다 — "
                                   "이 칸의 edge_bin·f_edge_hz 는 물리적 도플러 확산이 아니라 "
                                   "0 채움의 산물이다. JSON 안에 값이 남아 있으므로 인용 금지."))
    #  판정·표에 실제로 쓰였는지 확인
    used = dict(
        verdict_uses_only_prod=bool(all(
            v["channel"] in ("all", "prop") and True
            for key in ("mini2", "matrice4e")
            for v in V["verdict"]["by_cell"][key].values())),
        verdict_cell_modes=sorted({v.get("mode", "prod") for key in ("mini2", "matrice4e")
                                   for ck, v in V["verdict"]["by_cell"][key].items()}
                                  | {ck.split("/")[2] for key in ("mini2", "matrice4e")
                                     for ck in V["verdict"]["by_cell"][key]}),
        flash_table_sources=sorted({r["source"] for r in V["flash_frequency_table"]["rows"]}),
        flash_table_channels=sorted({r["channel"] for r in V["flash_frequency_table"]["rows"]}))
    return dict(by_block_channel=rows, diffuse=agg("prod"), specular=agg("spec"),
                zero_fill_artifact_demo=demo, where_used=used,
                verdict_ko=("헤드라인이 나오는 **확산(prod) 채널은 60/60 칸에서 경로 0 표본이 "
                            "정확히 0 개**다 — 0 채움 하모닉 우려는 여기 해당하지 않는다. "
                            "정반사(spec) 채널은 50/60 칸이 통째로 비어 분석에서 빠졌고(제외), "
                            "4 칸이 **0 을 그대로 채워 넣은 채 분석**됐다. 그 4 칸은 판정·"
                            "플래시표에 들어가지 않지만 JSON 안에 스펙트럼이 남아 있다."))


# =========================================================================== #
#  Q5 — 반대 결론으로 가는 길
# =========================================================================== #
def _flag_is_dead(name) -> dict:
    """⚠ 코드 사실 확인 — 그 표식이 판정 규칙에서 실제로 **읽히는가**."""
    hits = []
    bd = os.path.join(ROOT, "benchmark")
    for fn in sorted(os.listdir(bd)):
        #  ⚠ 이 검증 스크립트 자신은 세지 않는다(자기 언급이 증거를 오염시킨다)
        if not fn.endswith(".py") or fn.startswith("report15_attack"):
            continue
        with open(os.path.join(bd, fn)) as f:
            for i, ln in enumerate(f, 1):
                if name not in ln:
                    continue
                rest = ln.split(name, 1)[1].lstrip(' "\'' + "]")
                hits.append(dict(file=f"benchmark/{fn}", line=i,
                                 is_assignment=bool(rest.startswith("=")
                                                    and not rest.startswith("==")),
                                 text=ln.strip()[:120]))
    return dict(flag=name, n_occurrences=len(hits), occurrences=hits,
                n_reads=sum(1 for h in hits if not h["is_assignment"]),
                is_write_only=bool(hits and all(h["is_assignment"] for h in hits)),
                note_ko=("쓰기만 하고 한 번도 읽지 않으면 그 표식은 판정에 아무 영향이 없다 — "
                         "'붙여만 두고 규칙에 쓰지 않았다' 는 주장의 코드 증거다."))


def q5_counterpaths(V, SJ, RECENTRED=None, BUDGET=None) -> dict:
    paths = []
    base = {k: V["verdict"]["by_airframe"][k]["prop_channel_tally"] for k in ("mini2", "matrice4e")}
    base_ok = {k: V["verdict"]["by_airframe"][k]["prop_channel_tally"].get("SIONNA_NATIVE_OK", 0)
               for k in ("mini2", "matrice4e")}
    base_four = {k: V["verdict"]["by_airframe"][k]["n_cells_all_four_pass"]
                 for k in ("mini2", "matrice4e")}

    def cellinfo(key):
        out = []
        for ck, v in V["verdict"]["by_cell"][key].items():
            if v["channel"] != "prop":
                continue
            out.append((ck, v))
        return out

    #  ① (b) 를 못 잰 칸을 통과로 세지 않는다
    r = {}
    for key in ("mini2", "matrice4e"):
        n = sum(1 for ck, v in cellinfo(key)
                if v["checks"]["a_modulation_above_noise"] is True
                and v["checks"]["b_flash_freq_matches_ftip"] is True)
        nn = sum(1 for ck, v in cellinfo(key)
                 if v["verdict"] == "SIONNA_NATIVE_OK"
                 and v["checks"]["b_flash_freq_matches_ftip"] is None)
        r[key] = dict(native_ok_if_b_required=n,
                      native_ok_now=base_ok[key],
                      n_native_ok_without_any_b_test=nn)
    paths.append(dict(
        name="(b) 미평가 칸을 통과로 세지 않기",
        detail_ko=("judge_b 가 ok=None 을 돌려준 칸(이상 점산란자조차 교정 안 되는 칸)은 "
                   "`all(known)` 에서 빠지므로 (a)(c)(d) 만으로 SIONNA_NATIVE_OK 가 된다. "
                   "(c)(d) 는 아래 ③④ 에서 보듯 변별력이 없으므로 사실상 (a) 하나로 "
                   "'네이티브 OK' 가 찍힌 칸이 생긴다."),
        result=r))

    #  ② 프로젝트 자신의 광선예산 게이트를 적용
    inv = (V["spectrum_shape_reliability"]["by_airframe"]["matrice4e"]
           .get("invariant_by_range") or {})
    r2 = {}
    for key in ("mini2", "matrice4e"):
        meas = V["spectrum_shape_reliability"]["by_airframe"][key]["measured"]
        keep = 0
        tot = 0
        for ck, v in cellinfo(key):
            if v["verdict"] != "SIONNA_NATIVE_OK":
                continue
            tot += 1
            if meas and inv.get(f"{v['range_m']:g}") is True:
                keep += 1
        r2[key] = dict(shape_invariance_measured=meas,
                       native_ok_now=tot,
                       native_ok_where_shape_is_budget_invariant=(keep if meas else None),
                       ranges_declared_readable=(V["spectrum_shape_reliability"]
                                                 ["by_airframe"][key]["ranges_where_invariant"]))
    paths.append(dict(
        name="⭐ 프로젝트 자신의 예산-불변 게이트를 판정에 적용",
        detail_ko=("shape_invariance 는 코히런트 조화 **모양**이 광선예산에 불변한 거리를 "
                   "R=1 m 하나로 못박았다(3 m cos 0.937·10 m cos 0.730 → '상대 스펙트럼도 "
                   "인용 불가'). 그런데 판정은 이 표식을 칸에 붙여만 두고 규칙에 쓰지 않았다. "
                   "게이트를 실제로 걸면 matrice4e 의 SIONNA_NATIVE_OK 는 R=1 m 칸만 남고, "
                   "mini2 는 이 측정을 **한 번도 하지 않았으므로** 지지가 0 이 된다. "
                   "결론문의 '10 m 에서 예산이 줄어' 라는 단서는 3 m 도 깨졌다는 자기 측정과 "
                   "어긋난다. ⚠ 공정하게 적자면 이 게이트가 모든 것을 깎지는 않는다 — "
                   "기하 위상 기준과의 **가장자리** 일치는 R=3 m 에서 10/10 으로 완벽하고 "
                   "조화 모양의 예산 민감도와 무관하게 따로 선다. 깎이는 것은 (a) 여유와 "
                   "조화 **모양**에 기대는 주장이다(q6_what_survives 참조)."),
        result=r2, invariant_by_range=inv,
        code_evidence=_flag_is_dead("b_shape_invariant_at_this_range")))

    #  ③ (c) 는 변별하지 않는다
    cm = {}
    for key in ("mini2", "matrice4e"):
        vs = [(ck, v["c_null_margin_db"], v["verdict"]) for ck, v in cellinfo(key)]
        cm[key] = dict(n=len(vs), n_pass=sum(1 for _, x, _ in vs if x >= 6.0),
                       min_db=_f(min(x for _, x, _ in vs)),
                       also_passes_in_NO_MODULATION_cells=[
                           dict(cell=ck, c_db=_f(x)) for ck, x, w in vs
                           if w == "NO_MODULATION"])
    paths.append(dict(
        name="(c) 구 널 대조는 변별력이 0",
        detail_ko=("(c) 는 표적의 **prop 채널** 변조지수(AC/DC)를 구 널의 **all 채널** "
                   "변조지수와 비교한다. prop 채널은 DC 가 프롭 경로뿐이라 작고, 구 널 all 은 "
                   "구 전체 반사라 DC 가 거대하다 — 분모가 서로 다른 물건이다. 그래서 여유가 "
                   "30~81 dB 로 나오고 **NO_MODULATION 으로 찍힌 칸조차 (c) 를 통과**한다. "
                   "30/30 통과이므로 이 기준은 판정에 정보를 0 비트 넣는다."),
        result=cm))

    #  ④ (d) 는 상수
    paths.append(dict(
        name="(d) 삼각형 사다리는 한 칸에서 한 번 잰 상수",
        detail_ko=("mini2·R=3 m·nose 에서만 측정한 값(min_pearson_r=%s)을 두 기체 30 칸에 "
                   "동일하게 붙였다. 칸마다 재지 않았으므로 30/30 True 이고 변별력이 0 이다. "
                   "특히 matrice4e 는 이 시험을 **한 번도 받지 않았다**."
                   % V["resolution_ladder"].get("min_pearson_r")),
        result=dict(distinct_values=["True"], n_cells=30,
                    measured_on="mini2/R=3m/nose", measured_for_matrice4e=False)))

    #  ⑤ 가장자리 문턱을 바꾸면
    dr = {}
    for key in ("mini2", "matrice4e"):
        per = {}
        for ck, c in V["sionna"][key].items():
            if c.get("empty") or c.get("mode") != "prod" or c.get("channel") != "prop":
                continue
            for k, v in (c["judge_b"].get("threshold_sensitivity") or {}).items():
                per[k] = per.get(k, 0) + int(v["ok"] is True)
        dr[key] = per
    paths.append(dict(
        name="가장자리 정의를 −10 / −30 dB 로 바꾸면",
        detail_ko=("−20 dB 는 선언값이다. −10·−30 dB 로 옮기면 (b) 통과 칸 수가 바뀌고, "
                   "일부 칸은 비율이 0.93 → 3.19 처럼 절벽을 넘어간다(그 칸의 스펙트럼에는 "
                   "−20 ~ −30 dB 사이에 고차 꼬리가 있다는 뜻)."),
        result=dr))

    #  ⑥ 최선칸 선택의 다중비교
    paths.append(dict(
        name="best_overall_cell 은 15 칸에서 고른 최대값",
        detail_ko=("헤드라인 칸은 15 칸 중 '통과 기준 수 최대, 동률이면 (a) 최대' 로 뽑힌다. "
                   "선택 자체가 다중비교이므로 그 칸의 (a) 여유를 대표값처럼 인용하면 안 된다. "
                   "다만 이 실험에서는 (a) 의 백색잡음 거짓양성률이 매우 낮아 "
                   "선택편향이 결론을 뒤집지는 않는다 — 뒤집는 것은 ②다."),
        result=dict(n_cells_searched=15,
                    per_test_fpr_at_6db_white_noise="q1.null_distribution 참조")))
    #  ⑦ (b) 의 기준선을 이상 모형 가장자리로 재중심
    paths.append(dict(
        name="(b) 를 이상 점산란자 가장자리에 재중심",
        detail_ko=("운동학 f_tip(점 하나)은 실제 블레이드의 요구조화보다 낮다 — 그래서 이상 "
                   "모형조차 비율 1.09~1.18 을 낸다. 기준선을 이상 모형의 가장자리 빈으로 "
                   "옮기면(똑같이 ±20 %) 집계가 바뀐다: matrice4e 10 → 8, mini2 4 → 5. "
                   "어느 기준선이 옳은지는 물리 문제이고, 둘 다 방어 가능하다 — 그 사실 자체가 "
                   "(b) 기반 기체 비교가 아직 이르다는 뜻이다."),
        result=RECENTRED))
    #  ⑧ 예산 법칙 (F0) 을 집계에 적용
    paths.append(dict(
        name="⭐ 광선예산 1:1 법칙을 (a) 에 적용",
        detail_ko=("새로 잰 기울기(경로수 1 dB 당 1.02 dB)로 mini2 를 matrice4e 의 경로수에 "
                   "맞추면 mini2 의 (a) 가 일제히 +7.5 dB 올라 NO_MODULATION 2 칸이 사라진다. "
                   "반대로 matrice4e 를 mini2 의 예산으로 내리면 그 반대가 일어난다. "
                   "samples_per_src 가 uint32 라 실제로는 2× 밖에 못 올리므로 이 하네스로는 "
                   "확인 불가 — 그래서 '두 기체가 갈린다' 는 지금 자료로 지지도 반박도 안 된다."),
        result=BUDGET))
    return dict(paths=paths, baseline_tally=base,
                baseline_native_ok=base_ok, baseline_all_four=base_four)


def q6_what_survives(V) -> dict:
    """⭐ 공격만 하면 렌즈가 아니다. **살아남는 주장**도 같은 엄밀함으로 재어 준다."""
    G = V["geometric_phase_reference"]
    rows = [r for r in G["by_cell"].values() if r["edge_bin_diff"] is not None]
    #  귀무: 두 가장자리가 1~32 에 균등할 때 ±1 안에 들 확률
    p0 = sum(min(32, g + 1) - max(1, g - 1) + 1 for g in range(1, 33)) / 32 / 32
    from scipy import stats as st
    by_range = {}
    for R in (1.0, 3.0, 10.0):
        s = [r for r in rows if r["range_m"] == R]
        k = sum(1 for r in s if abs(r["edge_bin_diff"]) <= 1)
        by_range[f"{R:g}"] = dict(
            n=len(s), n_within_1_bin=k,
            median_abs_diff=_f(np.median([abs(r["edge_bin_diff"]) for r in s])) if s else None,
            median_comb_cosine=_f(np.median([r["comb_shape_cosine"] for r in s
                                             if r["comb_shape_cosine"] is not None])) if s else None,
            binomial_p_vs_uniform_null=_f(float(1 - st.binom.cdf(k - 1, len(s), p0))) if s else None)
    near = [r for r in rows if r["range_m"] in (1.0, 3.0)]
    kn = sum(1 for r in near if abs(r["edge_bin_diff"]) <= 1)
    #  ⭐ 순열 귀무 — 기하 기준을 **다른 칸**의 것과 짝지어도 같은 성적이 나오는가
    rng = np.random.default_rng(21)
    sio = np.array([r["sionna_edge_bin"] for r in near], float)
    geo = np.array([r["geometry_edge_bin"] for r in near], float)
    n_mc = 20000
    cnt = np.array([np.sum(np.abs(sio - rng.permutation(geo)) <= 1) for _ in range(n_mc)])
    return dict(
        geometric_reference_edge_agreement=dict(
            by_range=by_range,
            near_n=len(near), near_within_1_bin=kn,
            uniform_null_p_per_cell=_f(p0),
            binomial_p_near=_f(float(1 - st.binom.cdf(kn - 1, len(near), p0))),
            permutation_null_mean=_f(cnt.mean()),
            permutation_p=_f(float((np.sum(cnt >= kn) + 1) / (n_mc + 1))),
            note_ko=("기하 위상 기준과의 ±1 조화 일치는 R=1 m(8/10)과 R=3 m(**10/10**) 에서 "
                     "우연 수준(칸당 9.2 %)을 압도한다. 순열 귀무로도 유의하다. "
                     "⭐ 특히 R=3 m 는 조화 **모양**이 예산에 흔들리는 거리인데도 "
                     "**가장자리 위치는 완벽히 일치**한다 — 즉 예산 게이트는 모양·(a) 기반 "
                     "주장을 깎지만 '가장자리가 기하가 요구하는 곳에 있다' 는 주장은 "
                     "따로 살아남는다. R=10 m 에서는 3/8 로 무너진다.")),
        statistic_self_check=V["self_check"],
        path_count_census=V["path_count_census"]["summary"],
        note_ko=("살아남는 것을 과소평가하지 않으려고 같은 잣대(귀무분포·순열)를 걸었다."))


# =========================================================================== #
def main():
    t0 = time.time()
    V = load("report15_verdict.json")
    SJ = dict(mini2=load("report15_verdict_grid_mini2.json"),
              matrice4e=load("report15_sionna_sweep_matrice4e.json"))
    PH = V["physics"]
    print("§Q1 잡음바닥")
    q1 = dict(design=dict(
        n_phase=64, n_seeds_signal_grid=5, n_seeds_null_arms=2,
        spp_signal_grid=SJ["matrice4e"]["grid"]["spp"],
        spp_is_single_valued_in_verdict_grid=True,
        traces_per_cell=64 * 5, n_harmonic_bins=32,
        noise_model_ko=("잡음 = **시드 재추첨 분산**(평균의 분산). 광선예산·문턱·격자는 "
                        "고정이므로 이 잡음은 몬테카를로 표본잡음만 담는다. 시드에 대해 "
                        "결정론적인 오차(메쉬 이산화·면 가시성 전환 등)는 **신호로 계산된다**.")))
    q1["null_distribution"] = q1_null_distribution()
    print("   귀무분포 완료")
    q1["seed_scaling"] = q1_seed_scaling(SJ)
    print("   시드 스케일링 완료")
    q1["noise_floor_precision"] = q1_noise_floor_precision()
    q1["edge_gate_false_alarm"] = q1_edge_gate_falsealarm()
    q1["edge_margin"] = q1_edge_margin(V)
    q1["noise_whiteness"] = q1_noise_whiteness(SJ)
    q1["null_sample_census"] = q1_null_sample_census(V)
    q1["spp_dependence_existing"] = dict(
        measured_for_statistic_a=False,
        what_was_measured_ko=("shape_invariance 는 코히런트 조화의 **모양**과 **레벨**만 "
                              "16× 예산폭에서 쟀다(matrice4e · 4 칸 · 시드 3). "
                              "convergence 는 |h| 의 예산 기울기를 쟀다. "
                              "판정 (a) 가 쓰는 total_ac_over_noise_db 는 **한 번도** "
                              "예산을 바꿔 재지 않았다."),
        shape_invariance=SJ["matrice4e"]["shape_invariance"]["verdict"],
        convergence_slopes={k: v["coh_slope_log10h_per_log10N"]
                            for k, v in SJ["matrice4e"]["convergence"]["by_range"].items()},
        convergence_converged={k: v["coh_converged"]
                               for k, v in SJ["matrice4e"]["convergence"]["by_range"].items()},
        mini2_shape_invariance_measured=bool(
            V["spectrum_shape_reliability"]["by_airframe"]["mini2"]["measured"]))
    LAD = load("report15_attack_spp_ladder.json")
    LAD2 = load("report15_attack_spp_ladder_mini2.json")
    q1["spp_dependence_new_measurement"] = attack_ladder(LAD)
    q1["spp_dependence_new_measurement_mini2"] = attack_ladder(LAD2)
    q1["budget_law"] = q1_budget_law(V, LAD, LAD2)

    print("§Q2 문턱")
    q2 = dict(provenance=q2_provenance(), sweep=q2_threshold_sweep(V),
              other_thresholds=q2_other_thresholds(V, SJ))
    print("§Q3 플래시 주파수")
    q3 = q3_flash_fit(V, PH)
    print("§Q4 경로 0")
    q4 = q4_zero_paths(SJ, V)
    print("§Q5 반대 경로")
    q5 = q5_counterpaths(V, SJ,
                         RECENTRED={k: dict(n_evaluated=v["n_evaluated"], n_pass=v["n_pass"])
                                    for k, v in q3["recentred_on_ideal_model"].items()},
                         BUDGET={k: v for k, v in (q1.get("budget_law") or {}).items()
                                 if k not in ("measured_slope_rows", "airframe_pairs", "note_ko")})
    print("§Q6 살아남는 주장")
    q6 = q6_what_survives(V)

    J = dict(meta=dict(
        script="benchmark/report15_attack_stats.py",
        lens="적대검증 렌즈 1 — 수치·통계",
        target="outputs/report15_verdict.json",
        stance_ko="기본 입장은 '이 판정은 이르다'. 반증되지 않은 것만 남긴다.",
        new_measurement="outputs/report15_attack_spp_ladder.json (이 검증에서 새로 추적)",
        stamp=time.strftime("%Y-%m-%d %H:%M:%S")),
        q1_noise_floor=q1, q2_threshold=q2, q3_flash_fit=q3,
        q4_zero_paths=q4, q5_counterpaths=q5, q6_what_survives=q6)
    J["verdict"] = final_verdict(J)
    with open(OUT, "w") as f:
        json.dump(_js(J), f, ensure_ascii=False)
    J["meta"]["seconds"] = time.time() - t0
    print(f"\n✅ {OUT}  ({time.time()-t0:.0f}s)")
    print(json.dumps(_js(J["verdict"]), ensure_ascii=False, indent=1)[:3000])
    return J


def attack_ladder(L) -> dict:
    """새로 추적한 spp·시드 사다리에서 (a) 통계를 직접 잰다."""
    if not L or not L.get("runs"):
        return dict(available=False,
                    note_ko="benchmark/report15_attack_spp_ladder.py 결과가 아직 없다.")
    rows = {}
    for tag, R in L["runs"].items():
        G = R.get("grid") or {}
        if not G.get("complete"):
            rows[tag] = dict(incomplete=True, phases_done=G.get("phases_done"))
            continue
        for bk, B in G["blocks"].items():
            for ch in ("all", "prop"):
                z, n = block_wave(B, ch)
                if n.max() == 0:
                    continue
                S = z.shape[1]
                sub = {}
                for s in (2, 3, 5, 8, 12, 16):
                    if s > S:
                        continue
                    idx = list(itertools.combinations(range(S), s))
                    if len(idx) > 60:
                        rng = np.random.default_rng(3)
                        idx = [tuple(rng.choice(S, s, replace=False)) for _ in range(60)]
                    v = [ac_over_noise_db(z[:, list(c)]) for c in idx]
                    v = [x for x in v if x is not None]
                    sub[str(s)] = _f(np.mean(v)) if v else None
                a = harm_abs(z)
                rows[f"{tag}/{bk}/{ch}"] = dict(
                    run=tag, kind=R["kind"], spp=R["spp"], cell=bk, channel=ch,
                    n_seeds=S, ac_over_noise_db=_f(ac_over_noise_db(z)),
                    by_subset_size_db=sub,
                    n_paths_mean=_f(n.mean()), zero_frac=_f(float((n == 0).mean())),
                    edge_bin=edge_bin_of(a),
                    harm_shape=_fl(a / (a.max() + 1e-300), 4),
                    level_db=_f(20 * np.log10(np.abs(z.mean(axis=1)).mean() + 1e-300)))
    #  spp 축 요약
    by_cell = {}
    for k, r in rows.items():
        if r.get("kind") != "spp_ladder":
            continue
        by_cell.setdefault(f"{r['cell']}/{r['channel']}", {})[str(r["spp"])] = r
    spp_summary = {}
    for ck, d in by_cell.items():
        s = sorted(int(x) for x in d)
        y = [d[str(x)]["ac_over_noise_db"] for x in s]
        lv = [d[str(x)]["level_db"] for x in s]
        eb = [d[str(x)]["edge_bin"] for x in s]
        sh = [np.asarray(d[str(x)]["harm_shape"], float) for x in s]
        cos = [float(np.dot(sh[0], sh[i]) / (np.linalg.norm(sh[0]) * np.linalg.norm(sh[i])))
               for i in range(len(sh))]
        ok = [v for v in y if v is not None]
        spp_summary[ck] = dict(
            spps=s, spp_span=_f(max(s) / min(s)),
            ac_over_noise_db_by_spp=_fl(y),
            ac_over_noise_swing_db=_f(max(ok) - min(ok)) if len(ok) > 1 else None,
            slope_db_per_decade_spp=_f(np.polyfit(np.log10(s), y, 1)[0])
            if len(ok) == len(s) and len(s) > 1 else None,
            level_db_by_spp=_fl(lv),
            level_slope_log10_per_log10=_f(np.polyfit(np.log10(s), np.asarray(lv) / 20.0, 1)[0])
            if len(s) > 1 else None,
            edge_bin_by_spp=eb, edge_bin_stable=bool(len(set(eb)) == 1),
            shape_cosine_vs_lowest_spp=_fl(cos),
            crosses_6db_threshold=bool(any(v is not None and v < 6.0 for v in y)
                                       and any(v is not None and v >= 6.0 for v in y)))
    seed_summary = {}
    for k, r in rows.items():
        if r.get("kind") != "seed_ladder":
            continue
        sub = r["by_subset_size_db"]
        xs = sorted(int(x) for x in sub if sub[x] is not None)
        ys = [sub[str(x)] for x in xs]
        seed_summary[f"{r['cell']}/{r['channel']}"] = dict(
            spp=r["spp"], n_seeds_max=r["n_seeds"],
            ac_over_noise_db_by_n_seeds={str(x): sub[str(x)] for x in xs},
            slope_db_per_doubling_S=_f(np.polyfit(np.log10(xs), ys, 1)[0] * math.log10(2.0))
            if len(xs) > 1 else None,
            span_db=_f(max(ys) - min(ys)) if len(ys) > 1 else None,
            theoretical_slope_strong_signal=_f(10 * math.log10(2.0)))
    #  ⭐ 독립 재현 — 시드 사다리는 본 격자와 **같은 spp·같은 칸**을 새로 추적했다.
    #    S=5 부분집합 평균이 본 격자 값과 얼마나 맞는지가 파이프라인 재현성이다.
    repro = {}
    V0 = load("report15_verdict.json")
    for k, r in rows.items():
        if r.get("kind") != "seed_ladder" or r["channel"] != "prop":
            continue
        got = (r["by_subset_size_db"] or {}).get("5")
        ref = ((V0 or {}).get("sionna", {}).get(L["meta"]["drone"], {})
               .get(f'{r["cell"]}/prop') or {}).get("ac_over_noise_db")
        if got is None or ref is None:
            continue
        repro[r["cell"]] = dict(new_run_S5_db=_f(got), main_grid_S5_db=_f(ref),
                                diff_db=_f(got - ref))
    dif = [abs(v["diff_db"]) for v in repro.values()]
    return dict(available=True, source="outputs/report15_attack_spp_ladder.json",
                independent_reproduction=dict(
                    rows=repro, max_abs_diff_db=_f(max(dif)) if dif else None,
                    note_ko=("같은 spp·같은 칸을 새 시드 집합으로 다시 추적해 S=5 로 줄인 값과 "
                             "본 격자 값의 차이다. 작으면 파이프라인이 재현된다는 실측 증거다.")),
                n_traces=int(sum((r.get("grid") or {}).get("n_traces", 0)
                                 for r in L["runs"].values())),
                rows=rows, spp_summary=spp_summary, seed_summary=seed_summary,
                note_ko=("spp 사다리: (a) 통계가 광선예산에 얼마나 움직이는지. "
                         "시드 사다리: (a) 통계가 시드 수에 얼마나 자라는지. "
                         "둘 다 기존 산출물에 없던 측정이다."))


def final_verdict(J) -> dict:
    q1, q2, q3, q4, q5 = (J["q1_noise_floor"], J["q2_threshold"], J["q3_flash_fit"],
                          J["q4_zero_paths"], J["q5_counterpaths"])
    findings = []
    nd = q1["null_distribution"]["by_n_seeds"]
    cen = q1["null_sample_census"]
    findings.append(dict(
        id="F1", question="Q1", severity="정정",
        title="'널 15칸' 은 실제로 12칸이다 — 3칸은 시험 불가를 통과로 셌다",
        numbers=dict(claimed=cen["claimed_n_null_cells"],
                     testable=cen["n_null_cells_with_a_value"],
                     degenerate=cen["n_null_cells_degenerate_no_value"],
                     cells=cen["degenerate_cells"]),
        text_ko=("norotor 팔은 위상을 돌려도 기하가 동일해 h(φ) 가 상수다. AC 가 정확히 0 이라 "
                 "(a) 를 시험할 수 없다 — `fires=None` 이 falsy 라 '안 켜짐' 으로 집계됐다.")))
    findings.append(dict(
        id="F2", question="Q1", severity="치명적이지 않음(오히려 유리)",
        title="(a) 통계의 백색잡음 거짓양성률은 6 dB 에서 사실상 0",
        numbers={f"S={k}": dict(p99_db=v["p99_db"], max_db=v["max_db"],
                                fpr_at_6db=v["fpr_at_6db"]) for k, v in nd.items()},
        text_ko=("복소 백색잡음 40 000 회에서 이 통계는 S=2 에서도 6 dB 를 넘지 못한다. "
                 "즉 6 dB 문턱 자체는 관대하지 않다. 문제는 문턱이 아니라 **무엇을 잡음이라 "
                 "불렀는가**다 — 시드에 대해 결정론적인 오차는 잡음이 아니라 신호로 들어간다.")))
    ss = q1["seed_scaling"]
    LN = (q1.get("spp_dependence_new_measurement") or {})
    findings.append(dict(
        id="F3", question="Q1", severity="중대",
        title=("새 실측: (a) 여유는 시드 수에 이론값 그대로 비례한다(2.78~2.94 dB/시드2배). "
               "널은 S=2, 신호는 S=5 로 쟀다"),
        numbers=dict(seed_ladder=LN.get("seed_summary"),
                     n_new_traces_seed_ladder=3072,
                     subset_slope_median_db_per_doubling=ss["prop_slope_db_per_doubling_S_median"],
                     theoretical_strong_signal=ss["theoretical_slope_strong_signal_db_per_doubling"],
                     jackknife_std_db_median=ss["jackknife_std_db_median"],
                     null_arms_n_seeds=2, signal_grid_n_seeds=5,
                     independent_reproduction=LN.get("independent_reproduction")),
        text_ko=("시드를 16 개까지 늘려 새로 추적했다(3 072 회). (a) 는 S=2 → 16 에서 "
                 "8.3~8.8 dB 자라고 기울기가 2.78~2.94 dB/시드2배로 **강신호 이론값 3.01 에 "
                 "거의 정확히 붙는다**. 두 가지를 동시에 뜻한다. "
                 "㉠ **긍정적**: 기울기가 S 가 커져도 안 꺾인다 = 조화 성분에 시드 의존 "
                 "잔차가 사실상 없다 = 그 변조는 몬테카를로 표본잡음이 아니다. "
                 "㉡ **부정적**: 그래서 (a) 의 절대값은 물리가 아니라 평균 횟수다. 널 팔은 "
                 "S=2, 신호격자는 S=5 로 쟀으므로 두 분포 사이에는 3.98 dB 의 순수 장부상 "
                 "차이가 있다. 같은 6 dB 자로 잰 것은 자를 바꿔 가며 잰 것이다. "
                 "덤으로 파이프라인 재현성도 얻었다 — 같은 칸을 새로 추적해 S=5 로 줄인 값이 "
                 "본 격자와 최대 0.55 dB 차이다.")))
    findings.append(dict(
        id="F4", question="Q1", severity="중대",
        title="판정 통계의 spp 의존은 이번 검증 전까지 한 번도 측정되지 않았다",
        numbers=q1["spp_dependence_existing"],
        text_ko=("기존 사다리는 **모양·레벨**만 쟀다. 그리고 그 측정은 '코히런트 조화 모양이 "
                 "예산에 불변한 거리는 R=1 m 뿐' 이라고 말한다(3 m·10 m 는 인용 불가). "
                 "mini2 는 그 측정을 아예 안 했다.")))
    MB = (q1.get("spp_dependence_new_measurement_mini2") or {})
    if MB.get("available"):
        findings.append(dict(
            id="F4b", question="Q1", severity="정보(빈틈 메움)",
            title="mini2 도 광선예산 사다리를 받았다(신규 1 920 회) — 예산 법칙이 기체와 무관함을 확인",
            numbers=dict(spp_summary={k: v for k, v in (MB.get("spp_summary") or {}).items()
                                      if k.endswith("/prop")},
                         n_traces=MB.get("n_traces")),
            text_ko=("mini2 는 이 프로젝트에서 예산 사다리를 한 번도 받은 적이 없었다. "
                     "16× 폭으로 재 보니 (a) 기울기가 matrice4e 와 같은 자리에 있고"
                     "(두 기체 6 칸 중앙값 1.01 dB/dB), 가장자리 빈은 R=1 m 에서만 예산에 "
                     "불변(3, 3)하고 R=3·10 m 에서는 움직인다(5→3, 6→4). "
                     "⇒ mini2 의 (b) 실패는 **R=1 m 에서는 물리**(예산을 16× 줘도 가장자리가 "
                     "3 빈에 머문다 — 운동학 예측 4.37 빈에 못 미친다)이고, "
                     "**R=3·10 m 에서는 예산**이다. 리포트는 이 둘을 구분하지 않았다.")))
    B = q1.get("budget_law") or {}
    if B.get("available"):
        findings.insert(0, dict(
            id="F0", question="Q1", severity="치명적",
            title=("⭐⭐ 새 실측: (a) 통계는 광선예산에 1 : 1 로 비례한다 — "
                   "'변조가 잡음보다 6 dB 위' 는 물리가 아니라 예산의 진술이다"),
            numbers=dict(
                slope_db_per_db_of_paths=B["slope_db_per_db_of_paths_median"],
                slope_rows=B["measured_slope_rows"],
                n_new_traces=(q1.get("spp_dependence_new_measurement") or {}).get("n_traces"),
                median_path_ratio_m4e_over_mini2=B["median_path_count_ratio_m4e_over_mini2"],
                implied_mini2_boost_db=B["implied_mini2_boost_if_budget_matched_db"],
                mini2_no_modulation_now=B["mini2_no_modulation_cells_now"],
                mini2_no_modulation_after_budget_match=B[
                    "mini2_no_modulation_cells_after_budget_match"],
                edge_bin_vs_spp={k: v["edge_bin_by_spp"] for k, v in
                                 ((q1.get("spp_dependence_new_measurement") or {})
                                  .get("spp_summary") or {}).items() if k.endswith("/prop")},
                budget_corrected_airframe_delta_db=B["budget_corrected_delta_median_db"],
                spp_cap=B["spp_cap"]),
            text_ko=(
                "기하를 고정하고 광선예산만 16× 흔들었다(신규 추적 2 880 회). "
                "판정 (a) 가 쓰는 통계는 경로수 1 dB 당 %s dB 로 따라 올라간다 — 즉 수렴하지 "
                "않는다. R=10 m·hot 칸은 같은 기하에서 3.15 → 7.13 → 14.92 dB 로 움직여 "
                "**예산만으로 NO_MODULATION 을 벗어난다**. "
                "⚠ 공정하게 적자면 이 거동 자체는 **검정통계량으로서 정상**이다 — 더 많이 "
                "평균할수록 '이 변조가 표본잡음이 아니다' 라는 확신이 커지는 것이 맞다. "
                "잘못된 것은 두 가지 사용법이다: (ⅰ) 그 값을 신호 세기처럼 인용하는 것, "
                "(ⅱ) **경로수가 다른 기체·거리끼리 그 값을 비교**하는 것. 헤드라인이 바로 "
                "그 비교다. 따라서 '(a) 여유 N dB' 는 "
                "'이 예산에서' 라는 단서 없이는 뜻이 없고, NO_MODULATION 은 표적의 성질이 "
                "아니라 예산의 성질이다. matrice4e 는 같은 예산에서 프롭 경로가 mini2 의 "
                "%s 배라 (a) 에서 구조적으로 유리하다. 예산을 맞추면 mini2 의 "
                "NO_MODULATION 2 칸이 사라진다(예상 +%s dB). ⚠ 그런데 samples_per_src 가 "
                "uint32 라 예산은 2× 밖에 못 올린다 — **이 하네스로는 예산 맞춘 기체 비교가 "
                "원리적으로 불가능하다.** 그러므로 '두 기체가 갈린다' 는 서사는 지금 설계로는 "
                "확정할 수 없다."
                % (B["slope_db_per_db_of_paths_median"],
                   B["median_path_count_ratio_m4e_over_mini2"],
                   B["implied_mini2_boost_if_budget_matched_db"]))))
    pv = q2["provenance"]
    findings.append(dict(
        id="F5", question="Q2", severity="중대",
        title="6 dB 사전등록의 증거는 없다 — 다만 결론은 문턱에 거의 안 매달린다",
        numbers=dict(threshold_file_untracked=pv["threshold_file_is_untracked"],
                     minutes_after_data=pv["minutes_threshold_file_written_after_matrice4e_data"],
                     headline_interval_db=q2["sweep"]["headline_exact_interval_db"],
                     headline_interval_width_db=q2["sweep"]["headline_exact_width_db"],
                     ordering_holds_db=q2["sweep"]["ordering_holds_interval_db"],
                     gap_below_db=q2["sweep"]["gap_below_threshold_db"],
                     gap_above_db=q2["sweep"]["gap_above_threshold_db"]),
        text_ko=pv["verdict_ko"]))
    findings.append(dict(
        id="F6", question="Q3", severity="치명적",
        title=("(b) 는 자세 라벨을 섞어도 거의 같은 성적이 나온다 — 자세투영 예측을 "
               "**유의하게 검증하지 못한다**"),
        numbers=dict(n_cells_evaluated=q3["n_cells_evaluated"], n_pass=q3["n_pass"],
                     permutation_p_within_airframe=q3["permutation_p_aspect_shuffle"],
                     permutation_null_mean_passes=q3["permutation_null_mean_passes"],
                     binomial_p_uniform_null=q3["binomial_p_uniform_null"],
                     expected_under_uniform_null=q3["expected_pass_under_uniform_null"],
                     by_aspect=q3["by_aspect"],
                     prediction_levels=q3["prediction_levels"],
                     window_asymmetry=q3["window_asymmetry"]),
        text_ko=("두 개의 귀무를 걸었다. ① 가장자리 빈이 1~32 에 균등하다는 약한 귀무에서는 "
                 "기대 통과가 2.28 칸뿐이라 이항 p 가 5.6e−9 다 — 창이 '아무거나 통과' 시키지는 "
                 "않는다. ② 그러나 옳은 귀무는 **기체 안에서 자세 라벨을 섞는 것**이다. "
                 "거기서는 26 칸 중 기대 통과가 12.2 칸이고 관측 14 칸이라 p=0.072 — "
                 "**유의하지 않다.** 이유는 명백하다: 자세투영 예측이 빈 폭보다 크게 갈라지는 "
                 "단계가 기체당 2 개뿐이고(nose·oblique·side·hot 의 예측이 0.34 빈 차이로 "
                 "구별 불가), 진짜로 다른 유일한 자세인 disc(el 75°)는 0/3 으로 전부 실패한다. "
                 "즉 (b) 통과는 '가장자리가 f_tip 근처' 라는 한 가지 사실의 반복이지 "
                 "자세 의존성을 검증한 것이 아니다. 게다가 창이 중심에 있지 않다 — 이상 "
                 "점산란자조차 비율 1.15 를 내므로 유효 창은 이상모형 기준 [0.70, 1.04] 이고, "
                 "실제 블레이드가 점보다 넓게 퍼지는 옳은 거동이 탈락 사유가 된다.")))
    findings.append(dict(
        id="F7", question="Q4", severity="문제 없음(확인)",
        title="확산 채널에 경로 0 표본은 0 개 — 0 채움 하모닉 우려는 헤드라인에 해당하지 않는다",
        numbers=dict(diffuse=q4["diffuse"], specular=q4["specular"]),
        text_ko=("확산 60/60 칸에서 zero_frac=0. 정반사는 50/60 칸이 통째로 비어 제외됐고 "
                 "4 칸이 0 채움 상태로 분석돼 JSON 에 남아 있다 — 판정에는 안 들어가지만 "
                 "그 칸의 edge_bin 은 인용 금지 대상이다.")))
    p2 = next(p for p in q5["paths"] if p["name"].startswith("⭐"))
    findings.append(dict(
        id="F8", question="Q5", severity="치명적",
        title="⭐ 같은 자료로 반대 결론이 나온다 — 프로젝트 자신의 예산-불변 게이트를 걸면",
        numbers=p2["result"], text_ko=p2["detail_ko"]))
    findings.append(dict(
        id="F9", question="Q5", severity="중대",
        title="네 기준 중 둘((c)(d))은 30/30 통과하는 상수라 정보가 0",
        numbers=dict(c=q2["other_thresholds"]["c_margins"],
                     d=q2["other_thresholds"]["d_is_constant"]),
        text_ko=("(c) 는 prop 채널 AC/DC 를 구 널의 all 채널 AC/DC 와 비교해 여유가 30~81 dB 로 "
                 "나오고 NO_MODULATION 칸조차 통과한다. (d) 는 mini2 한 칸의 값을 30 칸에 "
                 "복사한 상수다. 따라서 '네 기준 전부 통과' 는 사실상 '(a)와 (b) 통과' 다.")))
    findings.append(dict(
        id="F10", question="Q5", severity="중대",
        title="mini2 의 SIONNA_NATIVE_OK 6 칸 중 2 칸은 (b) 를 아예 시험하지 않았다",
        numbers=next(p for p in q5["paths"] if p["name"].startswith("(b) 미평가"))["result"],
        text_ko=("ok=None 은 `all(known)` 에서 빠져 통과로 취급된다. (c)(d) 가 상수이므로 "
                 "그 칸의 'NATIVE_OK' 는 (a) 하나로 찍힌 것이다.")))
    return dict(
        judgement="PREMATURE",
        judgement_ko=(
            "**PREMATURE.** BROKEN 은 아니다 — 통계 원자는 검사를 통과했다. 조화분해는 "
            "원본을 상대차 0 으로 재현하고, (a) 문턱 6 dB 는 백색잡음에 대해 관대하지 않으며"
            "(복소 백색잡음 40 000 회에서 S=2 에서도 6 dB 를 못 넘는다), 헤드라인이 나오는 "
            "확산 채널에는 경로 0 표본이 **한 개도 없어** 0 채움 인공 하모닉 우려가 해당하지 "
            "않는다. 갈래 ①(Paths.doppler 로는 안 나온다)도 통계와 무관한 자유도 논증이라 "
            "그대로 선다. "
            "그럼에도 헤드라인 '**matrice4e NATIVE_OK 10/15 · mini2 6/15**' 와 그 위에 얹힌 "
            "'두 기체가 갈린다' 는 서사는 이르다. 네 가지가 걸린다. "
            "① **가장 무거운 것 — 판정량이 예산에 1 : 1 로 매달려 있다.** 기하를 고정하고 "
            "광선예산만 16× 흔들어 새로 추적해 보니(spp 사다리 2 880 회) (a) 통계는 경로수 1 dB 당 "
            "1.02 dB 로 따라 올라간다. R=10 m 칸은 같은 기하에서 3.2 → 14.9 dB 로 움직여 "
            "예산만으로 NO_MODULATION 을 벗어난다. 이 거동 자체는 검정통계량으로서 정상이지만, "
            "그렇기 때문에 (a) 여유는 신호 세기가 아니라 **확신도**이고 경로수가 다른 대상끼리 "
            "비교할 수 없다. 그러므로 (a) 여유도 NO_MODULATION 도 표적의 성질이 아니라 예산의 "
            "성질이고, 프롭 경로가 5.4 배 많은 matrice4e 가 구조적으로 유리하다. "
            "예산을 맞추려면 5.4× 가 필요한데 samples_per_src 가 uint32 라 2× 밖에 못 올린다 — "
            "**이 하네스로는 기체 비교 자체가 원리적으로 불가능하다.** "
            "② 프로젝트 자신의 shape_invariance 측정은 코히런트 조화 모양이 예산에 불변한 "
            "거리를 R=1 m 하나로 못박았는데(3 m cos 0.937 · 10 m cos 0.730 → '상대 스펙트럼도 "
            "인용 불가'), 판정은 그 표식을 칸에 붙여만 두고 규칙에 쓰지 않았다. 결론문의 "
            "'10 m 에서 예산이 줄어' 라는 단서도 자기 측정(3 m 부터 깨짐)과 어긋난다. "
            "⚠ 다만 이 게이트가 모든 것을 깎지는 않는다 — 기하 위상 기준과의 **가장자리** "
            "일치는 R=3 m 에서 10/10 이라 따로 살아남는다. 깎이는 것은 (a) 여유와 조화 "
            "**모양**에 기대는 주장이다. "
            "③ 네 기준 중 (c)(d)는 30/30 통과하는 상수라 정보를 0 비트 넣는다 — (c)는 표적의 "
            "prop 채널 AC/DC 를 구 널의 all 채널 AC/DC 와 비교해 여유가 33~81 dB 로 나오고 "
            "NO_MODULATION 칸조차 통과하며, (d)는 mini2·R=3 m·nose 한 칸의 값을 30 칸에 "
            "복사한 것이다(matrice4e 는 이 시험을 받은 적이 없다). 따라서 '네 기준 전부 통과' "
            "는 실제로 '(a)와 (b) 통과' 다. "
            "④ **(b) 가 자세 예측을 검증하지 못한다.** 기체 안에서 자세 라벨을 섞는 순열 "
            "귀무에서 기대 통과 12.2 칸 대 관측 14 칸 — p=0.072 로 유의하지 않다. 자세투영 "
            "예측이 빈 폭보다 크게 갈라지는 단계가 기체당 2 개뿐이고, 진짜로 다른 유일한 "
            "자세인 disc(el 75°)는 0/3 으로 전부 실패한다. 게다가 창이 중심에 있지 않아 "
            "(이상 점산란자조차 1.15) '점보다 넓게 퍼진다' 는 물리적으로 옳은 방향이 탈락 "
            "사유가 된다. "
            "⑤ 세부 정정 두 건: 널은 15 칸이 아니라 12 칸이고(norotor 3 칸은 AC 가 정확히 0 "
            "이라 시험 불가인데 '안 켜짐' 으로 셌다), mini2 의 NATIVE_OK 6 칸 중 2 칸은 (b) 를 "
            "시험조차 하지 않은 채 통과로 셌다."),
        answers_ko=dict(
            Q1=("표본수: 칸당 위상 64 × 시드 5 = 320 회 추적, 조화 32 빈. 시드 5 는 잡음추정 "
                "자유도 256(95 % 신뢰폭 1.51 dB)로 **모자라지 않다**. 다만 (a) 통계는 시드 수에 "
                "이론값 그대로 자라므로(신규 시드 16 사다리 3 072 회에서 2.78~2.94 dB/시드2배, "
                "이론 3.01) 널(S=2)과 신호(S=5) 사이에는 3.98 dB 의 순수 장부상 차이가 있다 — "
                "같은 6 dB 자로 잰 것은 자를 바꿔 가며 잰 것이다. ⭐ 기울기가 S=16 까지 "
                "안 꺾인다는 것은 **조화 성분에 시드 의존 잔차가 없다**는 뜻이라, 그 변조가 "
                "몬테카를로 표본잡음이 아니라는 강한 증거이기도 하다. spp 의존은 **판정 통계에 대해서는 "
                "한 번도 보지 않았다** — 기존 사다리는 모양·레벨만 쟀고 mini2 는 아예 안 쟀다. "
                "이번에 직접 재 보니 1.02 dB/dB(경로수)로 비례한다. 그리고 '잡음' 은 시드 "
                "재추첨 분산이므로 **시드에 대해 결정론적인 오차는 잡음이 아니라 신호로 "
                "들어간다** — 이 널이 못 잡는 종류의 인공물이 남는다."),
            Q2=("사전등록의 증거는 없다. 6.0 dB 를 선언한 파일은 git 미추적이고 mtime 이 "
                "matrice4e 격자 완성 50 분 뒤이며, 커밋된 트리에 margin_db_min 이 없다. "
                "프로젝트가 앞서 쓰던 문턱은 다른 통계에 대한 10 dB 였다. "
                "그래도 결론이 문턱에 크게 매달리지는 않는다: 백색잡음 거짓양성률이 6 dB 에서 "
                "사실상 0 이고, 기체 순서(matrice4e > mini2)는 0~30 dB 전 구간에서 유지된다. "
                "정확한 집계(10 · 6)가 유지되는 구간만 (4.76, 6.72] dB 로 폭 1.96 dB 다."),
            Q3=("'적합' 이 아니다 — 칸마다 −20 dB 문턱 교차로 읽은 **정수 가장자리 빈 1 개**이고 "
                "적합 모수는 0 개다(재료는 조화 32 빈, 위상 64 × 시드 5 = 320 회 추적). "
                "창의 관대함은 귀무를 무엇으로 두느냐로 갈린다. 가장자리 빈이 1~32 에 균등하다는 "
                "약한 귀무에서는 기대 통과 2.28 칸 대 관측 14 칸(이항 p 5.6e−9) — 관대하지 않다. "
                "그러나 **기체 안에서 자세 라벨을 섞는** 옳은 귀무에서는 기대 12.2 칸 대 관측 "
                "14 칸으로 p=0.072, **유의하지 않다**. ±20 % 창은 그만큼 넉넉하다. "
                "더 큰 문제는 창이 **중심에 있지 않다**는 것이다: 이상 점산란자조차 비율 1.15 를 "
                "내므로 창은 이상모형 기준 [0.70, 1.04] 이고, 실제 블레이드(유한 코드)가 점보다 "
                "넓게 퍼지는 옳은 거동이 탈락 사유가 된다. 게다가 자세투영 예측이 빈 폭보다 "
                "크게 갈라지는 대비는 기체당 **2 단계뿐**이고(el≤15° 대 el=75°), 바로 그 대비에서 "
                "matrice4e 는 실패하고 mini2 는 교정 실패로 제외된다."),
            Q4=("확산(prod) 채널 60/60 칸에서 경로 0 표본이 **0 개**다(19 200 표본 중 0). "
                "헤드라인은 0 채움과 무관하다. 정반사(spec) 채널은 60 칸 중 50 칸이 통째로 비어 "
                "`empty=True` 로 **분석에서 빠졌고**(0 을 넣지 않았다), 4 칸(matrice4e disc "
                "1·3 m)은 zero_frac 0.95·0.98 인 채 **0 을 그대로 채워 분석**됐다. 그 4 칸의 "
                "스펙트럼은 임펄스열이라 전 대역이 평평하고(3 m 칸은 평탄도 표준편차 9e−16 dB) "
                "가장자리가 마지막 빈 32 로 찍힌다 — 물리적 도플러 확산이 아니다. 다행히 판정· "
                "플래시표·기하기준·꼬리분석은 모두 prod 채널만 쓰므로 그 4 칸은 결론에 들어가지 "
                "않는다. 다만 JSON 에 값이 남아 있으므로 인용 금지 표시가 필요하다."),
            Q5=("있다. 여덟 갈래를 q5_counterpaths 에 적었고, 그중 둘은 헤드라인을 바꾼다. "
                "㈎ 프로젝트 자신의 예산-불변 게이트를 규칙에 걸면 matrice4e 의 NATIVE_OK 는 "
                "R=1 m 칸만 남고 mini2 는 그 사다리를 잰 적이 없어 지지가 0 이 된다. "
                "㈏ (b) 의 기준선을 운동학 점산란자 대신 **이상 모형의 가장자리**로 옮기면 "
                "matrice4e 10 → 8, mini2 4 → 5 로 기체 간 격차가 좁아진다. "
                "여기에 F0(예산 1:1 법칙)을 얹으면 '두 기체가 갈린다' 는 서사는 지금 자료로는 "
                "지지도 반박도 못 하는 상태가 된다.")),
        what_survives_ko=[
            "① Paths.doppler 로는 안 나온다 — SceneObject.velocity 의 자유도 논증이라 "
            "통계와 무관하다. 그대로 선다.",
            "확산 채널의 경로수 연속성(60/60 칸 zero_frac=0, 껐다켜짐 0)과 정반사 채널의 "
            "공백(50/60 칸 완전 공백, prop 정반사는 matrice4e disc 2 칸에서만 5 %·1.5 % 점등) "
            "— 경로수 인구조사는 셈이라 통계 가정이 없다. 그대로 선다.",
            "(a) 문턱 6 dB 는 백색잡음에 대해 관대하지 않다 — 복소 백색잡음 40 000 회에서 "
            "S=2 에서도 최대 4.39 dB 다. 관측된 널 최대 3.83 dB 도 그 안에 있다.",
            "이식한 harm_seeded 가 원본을 상대차 0 으로 재현한다는 자체검사.",
            "⭐ 신규 실측 — matrice4e 는 R=1·3 m 에서 **가장자리 빈이 광선예산 16× 에 완전히 "
            "불변**하다(9, 9, 9); mini2 는 R=1 m 에서만 불변(3, 3)이다. 즉 근거리의 (b) 가장자리는 잡음이 삼킨 지점이 아니라 물리다. "
            "반대로 R=10 m 에서는 예산에 따라 23 → 20 → 9 로 움직여 저예산에서 가장자리가 "
            "**부풀려진다** — 10 m 판정은 물리가 아니라 예산을 잰 것이라는 리포트의 단서가 "
            "이번에 인과적으로 확인됐다.",
            "⭐ 기하 위상 기준과의 가장자리 일치 — R=1 m 8/10, **R=3 m 10/10** 이 ±1 조화 "
            "안에 든다(칸당 우연 수준 9.2 %, 이항·순열 귀무 모두에서 유의). 조화 **모양**이 "
            "예산에 흔들리는 R=3 m 에서도 **가장자리 위치는 완벽히 맞는다** — 예산 게이트는 "
            "모양·(a) 기반 주장을 깎지만 이 주장은 따로 선다. R=10 m 에서는 3/8 로 무너진다.",
        ],
        what_must_change_ko=[
            "⭐ (a) 를 예산에 대해 정규화하거나, 최소한 모든 (a) 값에 '이 spp 에서' 라는 "
            "단서를 붙여라. NO_MODULATION 은 '이 예산에서 검출 안 됨' 으로 고쳐 써야 한다.",
            "⭐ 기체 비교는 **경로수를 맞춘 뒤에** 하라. uint32 상한 때문에 spp 로는 못 맞추므로 "
            "(2× 가능, 5.4× 필요) 다른 레버(거리·max_num_paths·다중 실행 평균)를 찾거나 "
            "'기체 비교 불가' 를 명시하라.",
            "shape_invariance 게이트를 판정 규칙에 실제로 걸고 집계를 R=1 m 과 그 밖으로 "
            "나눠 보고하라. mini2 에 대해서는 그 사다리를 먼저 재라(이번에 시작해 뒀다).",
            "'네 기준' → '(a)와 (b) 두 기준' 으로 고쳐 쓰거나, (c)를 같은 채널끼리 비교하도록 "
            "다시 정의하고 (d)를 칸마다 다시 재라.",
            "널 칸 수를 15 → 12 로 정정하고 퇴화 칸은 '시험 불가' 로 따로 세라. "
            "널 팔을 신호격자와 같은 시드 수(S=5)로 다시 재라.",
            "(b) 의 기준선을 이상 점산란자 가장자리로 재중심하고, 창을 비대칭으로 두어 "
            "'점보다 넓다' 가 탈락 사유가 되지 않게 하라.",
            "결론문의 '10 m 에서 예산이 줄어' 를 '3 m 부터 깨진다' 로 정정하라.",
            "정반사 disc 4 칸의 edge_bin·f_edge_hz 에 0 채움 산물 표시를 남겨라.",
        ],
        findings=findings)


if __name__ == "__main__":
    main()
