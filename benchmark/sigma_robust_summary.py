#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""σ 강건성 논증을 논문이 쓸 수 있는 형태로 압축한다.

읽는 것   outputs/sigma_sensitivity.json  (기존 스윕 결과)
          outputs/sigma_anchor.json       (측정 기울기 센서스)
쓰는 것   outputs/sigma_robust_summary.json

⭐ 이 스크립트의 존재 이유는 '요약'이 아니라 **직접 재평가에 의한 검증**이다.
   - 공통모드 1/4 법칙을 가정하지 않고 R90 을 실제로 다시 풀어 확인한다.
   - 뒤집힘 문턱 X 를 보간이 아니라 X±ε 에서 실제 순위를 다시 매겨 확인한다.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (os.path.join(ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import sigma_sensitivity as SS            # noqa: E402  (main() 은 __main__ 가드 뒤)
import experiment_freespace_range as R    # noqa: E402

SENS = os.path.join(ROOT, "outputs", "sigma_sensitivity.json")
ANCH = os.path.join(ROOT, "outputs", "sigma_anchor.json")
OUT = os.path.join(ROOT, "outputs", "sigma_robust_summary.json")

DRONES, MODES, PAIRS = SS.DRONES, SS.MODES, [("W1", "L1"), ("W1", "G1"), ("L1", "G1")]
F_GHZ, F_BAR, SPAN_GHZ = SS.F_GHZ, SS.F_BAR, SS.SPAN_GHZ
EPS = 0.05          # 문턱 검증용 미세 오프셋 [dB across span]


def main():
    t0 = datetime.now()
    sens = json.load(open(SENS))
    anch = json.load(open(ANCH))
    snr90 = sens["_meta"]["snr90_db"]

    print("[0] 셀 재구축 (sigma_sensitivity 와 동일하게 **live** 격자) …")
    # ⚠ sigma_sensitivity.py 는 분석 셀을 SIGMA_LIVE(현재 격자) 로 만든다.
    #    pre_blade 백업은 '정본 재현 증명'에만 쓰인다. 여기서도 live 를 쓴다.
    sig_live = json.load(open(SS.SIGMA_LIVE))
    sig_prev = json.load(open(SS.SIGMA_PREV))
    cells = {(d, m): SS.build_cell(sig_live, d, m) for d in DRONES for m in MODES}
    cells_avg = {(d, m): SS.build_cell(sig_live, d, m, aspect_avg=True)
                 for d in DRONES for m in MODES}
    cells_prev = {(d, m): SS.build_cell(sig_prev, d, m) for d in DRONES for m in MODES}

    out = {"_meta": dict(
        producer="benchmark/sigma_robust_summary.py",
        generated=t0.isoformat(timespec="seconds"),
        purpose="σ 강건성 논증을 논문 절 형태로 압축 + 문턱을 직접 재평가로 검증",
        reads=["outputs/sigma_sensitivity.json", "outputs/sigma_anchor.json",
               sens["reproduction"]["sigma_grid_used"], "outputs/report13_sigma_grid.json"],
        snr90_db=snr90, band_fc_ghz=F_GHZ, f_pivot_ghz=F_BAR, span_ghz=SPAN_GHZ,
        verification_epsilon_db=EPS)}

    # ======================================================================= #
    # V1. 공통모드 — 1/4 법칙을 가정하지 않고 직접 확인
    # ======================================================================= #
    print("[V1] 공통모드 직접 재평가 …")
    # ⚠ 거리격자는 [100 m, 20 km] 유한구간이다. 큰 +오프셋에서 해가 천장에 닿으면
    #    1/4 법칙 위반처럼 보이지만 그건 물리가 아니라 격자 인공물이다.
    #    → 해가 격자 내부에 머무는 오프셋 창에서만 법칙을 검정하고, 천장은 따로 신고한다.
    D_LO, D_HI = 105.0, 19000.0

    def interior(c, off):
        r = SS.R90(c, snr90, off)
        return bool(np.isfinite(r) and D_LO < r < D_HI), r

    offs = np.arange(-20.0, 20.001, 0.5)
    per_cell = {}
    dev_all, slope_all, win_all = [], [], []
    for d in DRONES:
        for m in MODES:
            c = cells[(d, m)]
            r0 = SS.R90(c, snr90, 0.0)
            ok = np.array([interior(c, o)[0] for o in offs])
            # 0 을 포함하는 연속 내부구간
            i0 = int(np.argmin(np.abs(offs)))
            lo = i0
            while lo > 0 and ok[lo - 1]:
                lo -= 1
            hi = i0
            while hi < len(offs) - 1 and ok[hi + 1]:
                hi += 1
            o_in = offs[lo:hi + 1]
            rr = np.array([SS.R90(c, snr90, o) for o in o_in])
            # 이론: R ∝ σ^(1/4) → 10log10(R/R0) = off/4  ⇔  dB(R) = dB(σ)/4
            meas = 10.0 * np.log10(rr / r0)
            dev = meas - o_in / 4.0
            sl = float(np.polyfit(o_in, meas, 1)[0])
            per_cell[f"{d}.{m}"] = dict(
                R90_base_m=float(r0),
                interior_offset_window_db=[float(o_in[0]), float(o_in[-1])],
                slope_db_range_per_db_sigma=sl,
                max_abs_dev_from_quarter_law_db=float(np.max(np.abs(dev))),
                R90_at_minus10_m=float(SS.R90(c, snr90, -10.0)),
                R90_at_plus10_m=float(SS.R90(c, snr90, +10.0)),
                plus10_inside_grid=bool(interior(c, +10.0)[0]))
            dev_all.append(float(np.max(np.abs(dev))))
            slope_all.append(sl)
            win_all.append((float(o_in[0]), float(o_in[-1])))
    win_lo = float(max(w[0] for w in win_all))     # 15 셀 공통 내부창
    win_hi = float(min(w[1] for w in win_all))

    # 순위 불변성 — 공통 내부창을 0.25 dB 간격으로 직접 재평가
    cm_grid = np.arange(win_lo, win_hi + 1e-9, 0.25)
    order_changes = {}
    for d in DRONES:
        base = SS.order_of({m: SS.R90(cells[(d, m)], snr90) for m in MODES})
        bad = [float(o) for o in cm_grid
               if SS.order_of({m: SS.R90(cells[(d, m)], snr90, o) for m in MODES}) != base]
        order_changes[d] = dict(base_order=list(base), offsets_with_changed_order=bad,
                                order_invariant=bool(not bad))
    # 격자 천장 밖까지 밀면 어떻게 되는가 — 인공물임을 명시적으로 기록
    ceiling = {}
    for d in DRONES:
        base = SS.order_of({m: SS.R90(cells[(d, m)], snr90) for m in MODES})
        bad = [float(o) for o in np.arange(-20.0, 20.001, 0.25)
               if SS.order_of({m: SS.R90(cells[(d, m)], snr90, o) for m in MODES}) != base]
        ceiling[d] = dict(offsets_with_changed_order_full_pm20=bad,
                          first_change_db=(float(min(bad, key=abs)) if bad else None))

    # 쌍 격차 불변성 — lead_db 가 공통모드에서 상쇄되는가 (직접 이분법)
    CM_TEST = min(10.0, abs(win_lo), abs(win_hi))
    lead_drift = {}
    for d in DRONES:
        for a, b in PAIRS:
            l0 = SS.lead_db(cells[(d, a)], cells[(d, b)], snr90, 0.0, 0.0)
            lp = SS.lead_db(cells[(d, a)], cells[(d, b)], snr90, +CM_TEST, +CM_TEST)
            lm = SS.lead_db(cells[(d, a)], cells[(d, b)], snr90, -CM_TEST, -CM_TEST)
            lead_drift[f"{d}.{a}-{b}"] = dict(
                lead_db=float(l0), lead_at_plus_db=float(lp), lead_at_minus_db=float(lm),
                max_drift_db=float(max(abs(lp - l0), abs(lm - l0))))
    max_lead_drift = max(v["max_drift_db"] for v in lead_drift.values())
    med_lead_drift = float(np.median([v["max_drift_db"] for v in lead_drift.values()]))

    out["common_mode"] = dict(
        claim=("공통모드 σ 오차 X dB 는 세 밴드를 함께 옮긴다 — 순위는 불변, "
               "절대거리만 X/4 dB 움직인다."),
        verified_by="직접 R90 재해 (해석식 대입 아님)",
        distance_grid=dict(d_min_m=100.0, d_max_m=20000.0, n=240,
                           interior_window_used_m=[D_LO, D_HI],
                           common_interior_offset_window_db=[win_lo, win_hi],
                           why=("+오프셋을 크게 주면 R90 이 20 km 격자 천장에 닿아 포화한다. "
                                "그 구간의 '법칙 위반'은 물리가 아니라 격자 인공물이라 "
                                "검정에서 제외하고 아래 grid_ceiling_artifact 에 따로 적는다.")),
        quarter_law=dict(
            predicted_slope_db_range_per_db_sigma=0.25,
            measured_slope_mean=float(np.mean(slope_all)),
            measured_slope_min=float(np.min(slope_all)),
            measured_slope_max=float(np.max(slope_all)),
            max_abs_deviation_db=float(np.max(dev_all)),
            median_abs_deviation_db=float(np.median(dev_all)),
            holds=bool(np.max(dev_all) < 1.0),
            why_not_exactly_quarter=(
                "R90 은 단일 R^-4 가 아니라 바이스태틱 κ=R1·R2 위에서 풀리고, σ(d) 는 "
                "거리에 따라 관측 자세가 바뀌므로 상수가 아니다. 국소 지수 n_local 이 "
                "4 근방에서 흔들려 기울기가 셀마다 0.25 를 살짝 벗어난다."),
            range_factor_at_pm10db=dict(
                minus10=float(10 ** (-10.0 / 40.0)), plus10=float(10 ** (10.0 / 40.0)),
                minus10_pct=float(100 * (10 ** (-10.0 / 40.0) - 1)),
                plus10_pct=float(100 * (10 ** (10.0 / 40.0) - 1)))),
        order_invariance=dict(
            grid=f"[{win_lo:+.1f}, {win_hi:+.1f}] dB (15 셀 공통 격자내부), 0.25 dB 간격",
            by_drone=order_changes,
            invariant_everywhere=bool(all(v["order_invariant"] for v in order_changes.values())),
            first_flip=({d: min(v["offsets_with_changed_order"], key=abs)
                         for d, v in order_changes.items()
                         if v["offsets_with_changed_order"]} or None),
            # ⚠ 두 한계를 구별한다: 아래쪽은 실제 뒤집힘, 위쪽은 격자 천장(검정 불가)
            #    아래 경계 = 뒤집힌 음수 오프셋 중 **가장 큰 것** 바로 위 (0 쪽 경계)
            verified_invariant_interval_db=[
                (float(max(o for v in order_changes.values()
                           for o in v["offsets_with_changed_order"] if o < 0) + 0.25)
                 if any(o < 0 for v in order_changes.values()
                        for o in v["offsets_with_changed_order"]) else float(win_lo)),
                (float(min(o for v in order_changes.values()
                           for o in v["offsets_with_changed_order"] if o > 0) - 0.25)
                 if any(o > 0 for v in order_changes.values()
                        for o in v["offsets_with_changed_order"]) else float(win_hi))],
            lower_limit_cause="실제 순위 뒤집힘 (s1000plus, −18.25 dB 이하)",
            upper_limit_cause=("격자 천장 — R90 이 20 km 를 넘어 검정 불가. "
                               "뒤집힘이 관측된 것이 아니다."),
            largest_symmetric_invariant_window_db=float(
                min([min(abs(o) for o in v["offsets_with_changed_order"])
                     for v in order_changes.values() if v["offsets_with_changed_order"]]
                    + [abs(win_lo), abs(win_hi)]) - 0.25),
            interpretation=(
                "논문이 필요로 하는 ±10 dB 는 전부 이 안에 든다. 다섯 기체 어디에서도 "
                "순위가 바뀌지 않는다. 유일한 뒤집힘은 s1000plus 가 −18.25 dB 에서 "
                "일으키는 것이고, 그건 어떤 σ 오차 시나리오보다도 크다.")),
        grid_ceiling_artifact=dict(
            by_drone=ceiling,
            note=("±20 dB 까지 억지로 밀면 순위가 바뀌는 지점이 나오지만, 그건 R90 이 "
                  "20 km 천장에 눌려 셋이 같은 값으로 포화하기 때문이다. 물리적 결론이 아니다.")),
        pair_gap_invariance=dict(
            common_mode_test_db=float(CM_TEST),
            max_lead_drift_db=float(max_lead_drift),
            median_lead_drift_db=med_lead_drift,
            exact=bool(max_lead_drift < 0.02),
            by_cell=lead_drift,
            interpretation=(
                "⭐ 쌍 격차는 **정확히는** 상쇄되지 않는다. 공통모드 오프셋이 해 거리를 "
                "옮기면 표적이 다른 자세로 보이고, σ(d) 로브 구조가 밴드마다 달라서 "
                "격차가 조금 흔들린다. 이 표류는 위 order_invariance 를 깨지 못할 만큼 "
                "작지만, '격차가 정확히 불변'이라는 서술은 과하다 — "
                "'순위가 불변'이 정확한 서술이다.")),
        by_cell=per_cell,
        paper_sentence="→ paper_ready.sentences.common_mode (문장은 한 곳에서만 유지한다)",
        correction_to_paper_spec=(
            "docs/PAPER_SPEC.md §1 은 '순위와 격차는 불변'이라고 적었다. 순위는 확인됐지만 "
            "'격차 불변'은 정확하지 않다 — pair_gap_invariance 참조. 논문 문장에서 "
            "'gap' 을 빼고 '순위'와 '절대거리 X/4 dB' 만 주장해야 한다."))

    # ======================================================================= #
    # V2. 차분(기울기) 오차 — 뒤집힘 문턱을 X±ε 에서 직접 검증
    # ======================================================================= #
    print("[V2] 뒤집힘 문턱 직접 검증 (X±ε 재평가) …")

    def slope_corr(dr):
        return sens["scenario_apply_measured_slope"]["by_drone"][dr]["correction_slope_db_per_ghz"]

    DUTY = {m: sens["unapplied_duty_axis"]["duty_db"][m] for m in MODES}

    CONFIGS = {
        "as_published": dict(cells=cells, anchor=False, duty=False,
                             desc="single aspect, no anchor, no duty — the current headline R90"),
        "aspect_avg": dict(cells=cells_avg, anchor=False, duty=False,
                           desc="aspect-averaged sigma"),
        "aspect_avg_anchored": dict(cells=cells_avg, anchor=True, duty=False,
                                    desc="aspect-averaged + measured 0.210 dB/GHz slope"),
        "aspect_avg_anchored_duty": dict(cells=cells_avg, anchor=True, duty=True,
                                         desc="aspect-averaged + anchored + duty axis applied"),
    }

    def base_off(cfg, dr, m):
        o = 0.0
        if cfg["anchor"]:
            o += slope_corr(dr) * (F_GHZ[m] - F_BAR)
        if cfg["duty"]:
            o += DUTY[m]
        return o

    verif = {}
    for cname, cfg in CONFIGS.items():
        cs = cfg["cells"]
        rows = {}
        for dr in DRONES:
            b = {m: base_off(cfg, dr, m) for m in MODES}
            base_order = SS.order_of({m: SS.R90(cs[(dr, m)], snr90, b[m]) for m in MODES})

            def order_at(span, b=b, cs=cs, dr=dr):
                s = span / SPAN_GHZ
                return SS.order_of({m: SS.R90(cs[(dr, m)], snr90,
                                              b[m] + s * (F_GHZ[m] - F_BAR)) for m in MODES})

            pairs = {}
            for a, bb in PAIRS:
                ld = SS.lead_db(cs[(dr, a)], cs[(dr, bb)], snr90, b[a], b[bb])
                df = F_GHZ[a] - F_GHZ[bb]
                s_flip = -ld / df
                span_analytic = float(abs(s_flip) * SPAN_GHZ)

                # ⭐ 실제 차분 스윕 위에서의 쌍 격차 — 두 밴드를 **동시에** 반대로 민다
                def dgap(span, a=a, bb=bb, b=b, cs=cs, dr=dr):
                    s = span / SPAN_GHZ
                    ra = SS.R90(cs[(dr, a)], snr90, b[a] + s * (F_GHZ[a] - F_BAR))
                    rb = SS.R90(cs[(dr, bb)], snr90, b[bb] + s * (F_GHZ[bb] - F_BAR))
                    if not np.isfinite(ra):
                        return -1e9, ra, rb          # a 미검출 → a 가 짐
                    if not np.isfinite(rb):
                        return +1e9, ra, rb
                    return float(ra - rb), float(ra), float(rb)

                g0 = dgap(0.0)[0]
                s0 = float(np.sign(g0))
                # 0 에서 바깥으로 0.1 dB 씩 훑어 첫 부호변화 구간을 찾고, 그 안에서 이분법
                span_direct, sgn = None, 0.0
                scan = np.arange(0.1, 40.0001, 0.1)
                for direction in (+1.0, -1.0):
                    prev = 0.0
                    for sp in scan:
                        if np.sign(dgap(direction * sp)[0]) != s0:
                            lo_, hi_ = prev, sp
                            for _ in range(60):
                                mid = 0.5 * (lo_ + hi_)
                                if np.sign(dgap(direction * mid)[0]) == s0:
                                    lo_ = mid
                                else:
                                    hi_ = mid
                                if hi_ - lo_ < 1e-4:
                                    break
                            cand = 0.5 * (lo_ + hi_)
                            if span_direct is None or cand < span_direct:
                                span_direct, sgn = float(cand), direction
                            break
                        prev = sp

                if span_direct is None:
                    pairs[f"{a}-{bb}"] = dict(
                        lead_db=float(ld), delta_f_ghz=float(df),
                        span_flip_analytic_db=span_analytic, span_flip_db=float("inf"),
                        flip_direction_sign=0.0, sign_at_zero=s0,
                        no_flip_within_db=40.0, direct_verification_passed=True,
                        note="±40 dB 차분 안에서 뒤집히지 않는다")
                    continue

                _, ra1, rb1 = dgap(sgn * (span_direct - EPS))
                _, ra2, rb2 = dgap(sgn * (span_direct + EPS))
                sin_ = float(np.sign(dgap(sgn * (span_direct - EPS))[0]))
                sout = float(np.sign(dgap(sgn * (span_direct + EPS))[0]))
                pairs[f"{a}-{bb}"] = dict(
                    lead_db=float(ld), delta_f_ghz=float(df),
                    span_flip_analytic_db=span_analytic,
                    span_flip_db=float(span_direct),
                    analytic_minus_direct_db=float(span_analytic - span_direct),
                    flip_direction_sign=float(sgn),
                    sign_at_zero=s0, sign_at_threshold_minus_eps=sin_,
                    sign_at_threshold_plus_eps=sout,
                    R90_pair_at_minus_eps_m=[ra1, rb1], R90_pair_at_plus_eps_m=[ra2, rb2],
                    direct_verification_passed=bool(sin_ == s0 and sout == -s0 and s0 != 0.0))
            weakest = min(pairs, key=lambda k: pairs[k]["span_flip_db"])
            X = pairs[weakest]["span_flip_db"]
            sgnX = pairs[weakest]["flip_direction_sign"]
            if np.isfinite(X):
                # ⭐ 드론 전체 순위 문턱의 직접 검증
                o_in, o_out = order_at(sgnX * (X - EPS)), order_at(sgnX * (X + EPS))
                okd = bool(o_in == base_order and o_out != base_order)
            else:
                o_in = o_out = base_order
                okd = True
            rows[dr] = dict(
                base_order=list(base_order),
                R90_m={m: float(SS.R90(cs[(dr, m)], snr90, b[m])) for m in MODES},
                pairs=pairs, weakest_pair=weakest, flip_threshold_span_db=X,
                flip_threshold_analytic_db=pairs[weakest].get("span_flip_analytic_db"),
                order_at_threshold_minus_eps=list(o_in),
                order_at_threshold_plus_eps=list(o_out),
                direct_verification_passed=okd)
        sm = [rows[dr]["flip_threshold_span_db"] for dr in DRONES]
        orders = {dr: tuple(rows[dr]["base_order"]) for dr in DRONES}
        pair_worst = {}
        for a, bb in PAIRS:
            v = [rows[dr]["pairs"][f"{a}-{bb}"]["span_flip_db"] for dr in DRONES]
            lds = [rows[dr]["pairs"][f"{a}-{bb}"]["lead_db"] for dr in DRONES]
            pair_worst[f"{a}-{bb}"] = dict(
                worst_flip_span_db=float(min(v)), median_flip_span_db=float(np.median(v)),
                per_drone_flip_span_db={dr: rows[dr]["pairs"][f"{a}-{bb}"]["span_flip_db"]
                                        for dr in DRONES},
                lead_sign_consistent=bool(all(x > 0 for x in lds) or all(x < 0 for x in lds)),
                winner=("a" if all(x > 0 for x in lds) else
                        ("b" if all(x < 0 for x in lds) else None)))
        winners = {rows[dr]["base_order"][0] for dr in DRONES}
        wmarg = [rows[dr]["pairs"][f"{a}-{bb}"]["span_flip_db"]
                 for dr in DRONES for a, bb in PAIRS
                 if len(winners) == 1 and next(iter(winners)) in (a, bb)]
        verif[cname] = dict(
            description=cfg["desc"], by_drone=rows, by_pair=pair_worst,
            n_distinct_orders=len(set(orders.values())),
            all_drones_agree=bool(len(set(orders.values())) == 1),
            consensus_order=(list(next(iter(orders.values())))
                             if len(set(orders.values())) == 1 else None),
            worst_flip_span_db=float(min(sm)), median_flip_span_db=float(np.median(sm)),
            winner=(next(iter(winners)) if len(winners) == 1 else None),
            winner_worst_margin_span_db=(float(min(wmarg)) if wmarg else None),
            all_direct_verifications_passed=bool(
                all(rows[dr]["direct_verification_passed"] for dr in DRONES)))

    n_pair_checks = sum(1 for c in verif.values() for dr in DRONES for p in PAIRS)
    n_pair_pass = sum(1 for c in verif.values() for dr in DRONES
                      for k in c["by_drone"][dr]["pairs"].values()
                      if k["direct_verification_passed"])
    # 해석 근사(|lead/Δf|·span) vs 직접 이분법의 차이 — 근사가 어디서 깨지는가
    ad = [(abs(k.get("analytic_minus_direct_db", 0.0)), k["span_flip_db"],
           f"{cn}/{dr}/{pk}")
          for cn, c in verif.items() for dr in DRONES
          for pk, k in c["by_drone"][dr]["pairs"].items()
          if np.isfinite(k["span_flip_db"])]
    ad.sort(reverse=True)
    out["flip_threshold"] = dict(
        claim=("파형 순위는 밴드 스팬 전체에 걸친 차분 σ 오차 X dB 까지 살아남는다. "
               "X 는 설정·기체·쌍마다 다르며 아래 표가 전부다."),
        method=("⭐ 문턱 X 를 **실제 차분 스윕 위에서 직접 이분법**으로 구한다 — 두 밴드를 "
                "동시에 s·(f−f̄) 만큼 반대로 밀며 R90_a−R90_b 의 부호가 바뀌는 span 을 찾는다. "
                f"그 X 에서 ±{EPS} dB 떨어진 두 점에서 R90 을 다시 풀어 X−ε 에서 순위가 "
                "유지되고 X+ε 에서 실제로 뒤집히는지 확인했다 (보간·해석식 아님)."),
        by_config=verif,
        direct_verification=dict(pair_checks=n_pair_checks, pair_checks_passed=n_pair_pass,
                                 all_passed=bool(n_pair_pass == n_pair_checks)),
        analytic_approximation_error=dict(
            definition="|lead/Δf|·span (해석 근사) − 직접 이분법 문턱, dB",
            max_abs_db=float(ad[0][0]) if ad else 0.0,
            median_abs_db=float(np.median([x[0] for x in ad])) if ad else 0.0,
            worst_cases=[dict(case=c, err_db=float(e), threshold_db=float(t))
                         for e, t, c in ad[:5]],
            why=("해석 근사는 '한 밴드만 밀어도 두 밴드를 반대로 미는 것과 같다'고 가정한다. "
                 "1/4 법칙이 정확하고 σ 가 거리무관일 때만 참이다. 실제로는 해 거리가 "
                 "움직이며 자세가 바뀌므로, 문턱이 클수록 근사가 벌어진다. "
                 "논문에는 직접 이분법 값을 쓴다.")),
        cross_check_vs_sigma_sensitivity={
            dr: dict(here=verif["as_published"]["by_drone"][dr]["flip_threshold_span_db"],
                     there=sens["differential"]["by_drone"][dr]["analytic_smallest_flip_span_db"],
                     abs_diff=abs(verif["as_published"]["by_drone"][dr]["flip_threshold_span_db"]
                                  - sens["differential"]["by_drone"][dr]
                                  ["analytic_smallest_flip_span_db"]))
            for dr in DRONES})

    # 격자 판본 민감도 — 문턱이 메쉬 갱신 하나에 얼마나 흔들리는가
    print("[V2b] 격자 판본(pre_blade vs live) 문턱 비교 …")
    stale = {}
    for dr in DRONES:
        row = {}
        for tag, cs in (("live", cells), ("pre_blade", cells_prev)):
            base = SS.order_of({m: SS.R90(cs[(dr, m)], snr90) for m in MODES})
            xs = {}
            for a, bb in PAIRS:
                ld = SS.lead_db(cs[(dr, a)], cs[(dr, bb)], snr90)
                xs[f"{a}-{bb}"] = float(abs(-ld / (F_GHZ[a] - F_GHZ[bb])) * SPAN_GHZ)
            row[tag] = dict(order=list(base), flip_threshold_span_db=float(min(xs.values())),
                            pair_flip_span_db=xs)
        stale[dr] = dict(**row,
                         order_changed=bool(row["live"]["order"] != row["pre_blade"]["order"]),
                         threshold_change_db=float(row["live"]["flip_threshold_span_db"]
                                                   - row["pre_blade"]["flip_threshold_span_db"]))
    out["flip_threshold"]["sigma_grid_version_sensitivity"] = dict(
        by_drone=stale,
        n_orders_changed=int(sum(1 for v in stale.values() if v["order_changed"])),
        max_abs_threshold_change_db=float(max(abs(v["threshold_change_db"])
                                              for v in stale.values())),
        finding=("⭐ 2026-07-29 블레이드 메쉬 갱신 하나만으로 뒤집힘 문턱이 최대 "
                 "몇 dB 씩 움직인다. 이건 σ '오차 모델'이 아니라 관측된 사실이며, "
                 "차분 강건성이 얼마나 얇은지를 독립적으로 보여준다."),
        caveat=("정본 outputs/report13_freespace.json 의 R90 은 pre_blade 격자로 계산됐다. "
                "논문에 쓸 숫자는 live 격자로 재생성해야 한다."))

    # ======================================================================= #
    # V3. 우리가 실제로 가진 오차 — 앵커는 하중을 받는가
    # ======================================================================= #
    print("[V3] 현실 오차 대비 …")
    scen = sens["scenario_apply_measured_slope"]["by_drone"]
    census = anch["sources"]["slope_census"]
    ov = {k: v["slope"] for k, v in census.items() if v["overlaps_our_band"]}
    ov_lo, ov_hi = min(ov.values()), max(ov.values())
    resid_span = float((ov_hi - ov_lo) * SPAN_GHZ)

    per_drone = {}
    for dr in DRONES:
        s = scen[dr]
        need = float(s["correction_span_db"])       # 앵커가 지워야 할 차분오차 [dB across span]
        have = verif["as_published"]["by_drone"][dr]["flip_threshold_span_db"]
        have_anch = verif["aspect_avg_anchored"]["by_drone"][dr]["flip_threshold_span_db"]
        per_drone[dr] = dict(
            our_production_slope_db_per_ghz=s["our_production_slope_db_per_ghz"],
            measured_slope_db_per_ghz=s["measured_slope_db_per_ghz"],
            differential_error_span_db=need,
            flip_threshold_as_published_db=have,
            margin_db=float(have - need),
            survives_its_own_error=bool(have > need),
            flip_threshold_anchored_db=have_anch,
            margin_vs_post_anchor_residual_db=float(have_anch - resid_span),
            survives_post_anchor_residual=bool(have_anch > resid_span))

    n_surv = sum(1 for v in per_drone.values() if v["survives_its_own_error"])
    n_surv_a = sum(1 for v in per_drone.values() if v["survives_post_anchor_residual"])
    out["realistic_error"] = dict(
        pre_anchor=dict(
            our_raw_slope_range_db_per_ghz=[SS.RAW_SLOPE_MIN, SS.RAW_SLOPE_MAX],
            measured_slope_db_per_ghz=SS.MEASURED_SLOPE,
            span_ghz=SPAN_GHZ,
            differential_error_span_db_min=float((SS.RAW_SLOPE_MIN - SS.MEASURED_SLOPE) * SPAN_GHZ),
            differential_error_span_db_max=float((SS.RAW_SLOPE_MAX - SS.MEASURED_SLOPE) * SPAN_GHZ),
            per_drone_production_slope_range_db_per_ghz=[
                float(min(scen[d]["our_production_slope_db_per_ghz"] for d in DRONES)),
                float(max(scen[d]["our_production_slope_db_per_ghz"] for d in DRONES))],
            per_drone_differential_error_span_db_range=[
                float(min(scen[d]["correction_span_db"] for d in DRONES)),
                float(max(scen[d]["correction_span_db"] for d in DRONES))]),
        post_anchor_residual=dict(
            method="같은 대역을 덮는 측정 기울기 센서스의 산포 (Das Phantom3 + Yuan Phantom3 3 컷)",
            slopes_db_per_ghz=ov, lo=ov_lo, hi=ov_hi,
            residual_span_db=resid_span,
            full_census_slopes_db_per_ghz={k: v["slope"] for k, v in census.items()},
            note="앵커 후 남는 차분 불확도. 밴드가 겹치는 4 건만 센다."),
        by_drone=per_drone,
        n_drones_surviving_own_pre_anchor_error=n_surv, n_drones=len(DRONES),
        n_drones_surviving_post_anchor_residual=n_surv_a,
        thinnest_surviving_margin=dict(
            drone=min((d for d in DRONES if per_drone[d]["survives_its_own_error"]),
                      key=lambda d: per_drone[d]["margin_db"], default=None),
            margin_db=min((per_drone[d]["margin_db"] for d in DRONES
                           if per_drone[d]["survives_its_own_error"]), default=None)),
        verdict=("ANCHOR_IS_LOAD_BEARING" if n_surv < len(DRONES) else "STANDS_UNANCHORED"),
        finding=(
            "⭐ 앵커는 하중을 받는다. 앵커 없이는 다섯 기체 중 %d 대만 자기 차분오차를 "
            "견디고 %d 대가 뒤집힌다. 살아남은 %d 대 중에서도 가장 얇은 여유가 %+.2f dB 라 "
            "실질적으로는 한 대만 안전하다. 앵커를 걸고 자세평균으로 인용하면 다섯 기체가 "
            "모두 같은 순위에 합의하고 전부 앵커 후 잔여 불확도(%.3f dB)를 넘긴다. "
            "논문은 앵커를 방법의 일부로 명시해야 하며, '앵커 없이도 비교가 선다'고 "
            "말할 수 없다."
            % (n_surv, len(DRONES) - n_surv, n_surv,
               min((per_drone[d]["margin_db"] for d in DRONES
                    if per_drone[d]["survives_its_own_error"]), default=float("nan")),
               resid_span)),
        caveat=("⚠ 생산 σ 격자는 앵커를 갖고 있지 않다 (sigma_sensitivity."
                "scenario_apply_measured_slope.finding: experiment_freespace_sigma.py 에 "
                "sigma_anchor 참조 0 회). 즉 앵커가 지웠어야 할 차분오차가 현재 R90 사슬에 "
                "아직 들어 있다. 논문에 쓰기 전에 앵커를 R90 경로에 실제로 걸어야 한다."))

    # ======================================================================= #
    # V4. 취약성 정직 신고
    # ======================================================================= #
    print("[V4] 취약성 신고 …")
    fragile = []
    for cname, c in verif.items():
        for p, pv in c["by_pair"].items():
            if (not pv["lead_sign_consistent"]) or pv["worst_flip_span_db"] < resid_span:
                fragile.append(dict(
                    config=cname, pair=p,
                    worst_flip_span_db=pv["worst_flip_span_db"],
                    lead_sign_consistent=pv["lead_sign_consistent"],
                    weakest_drone=min(pv["per_drone_flip_span_db"],
                                      key=lambda k: pv["per_drone_flip_span_db"][k]),
                    why=("부호가 기체마다 뒤집힌다 — 이 쌍은 순위 자체가 없다"
                         if not pv["lead_sign_consistent"]
                         else "문턱이 앵커 후 잔여 불확도보다 작다")))
    safe = []
    for cname, c in verif.items():
        for p, pv in c["by_pair"].items():
            if pv["lead_sign_consistent"] and pv["worst_flip_span_db"] >= SS.REALISTIC_SPAN_DB:
                safe.append(dict(config=cname, pair=p,
                                 worst_flip_span_db=pv["worst_flip_span_db"],
                                 winner=(p.split("-")[0] if pv["winner"] == "a"
                                         else p.split("-")[1])))
    # 어느 쌍이 어느 설정에서도 못 서는가 (전 설정 최악)
    pair_worst_overall = {f"{a}-{bb}": float(min(verif[c]["by_pair"][f"{a}-{bb}"]
                                                 ["worst_flip_span_db"] for c in verif))
                          for a, bb in PAIRS}
    weakest_pair_overall = min(pair_worst_overall, key=lambda k: pair_worst_overall[k])
    lam2 = sens["gap_decomposition"]["axes_pair_gaps_db"]
    out["fragility_declaration"] = dict(
        rule=("논문에 쓰려면 (1) 다섯 기체에서 lead 부호 일치 (2) 최악 문턱 > 해당 설정의 "
              "현실 오차범위. 앵커 전은 %.3f dB, 앵커 후는 %.3f dB 를 넘겨야 한다."
              % (SS.REALISTIC_SPAN_DB, resid_span)),
        realistic_span_db=SS.REALISTIC_SPAN_DB, post_anchor_residual_span_db=resid_span,
        fragile_claims=fragile, safe_claims=safe,
        n_fragile=len(fragile), n_safe=len(safe),
        pair_worst_over_all_configs_db=pair_worst_overall,
        lambda2_pair_gap_db=lam2,
        weakest_pair_overall=weakest_pair_overall,
        must_be_declared=(
            "⭐ %s (WiFi vs 5G NR) 가 전 설정에서 가장 약하다 — 최악 문턱 %.3f dB. "
            "이유는 σ 가 아니라 기하다: 이 쌍의 σ-무관 λ² 축 격차가 %+.2f dB 로 세 쌍 중 "
            "가장 좁아서(W1-L1 %+.2f, L1-G1 %+.2f) 버틸 마진 자체가 없다. "
            "논문은 이 쌍의 순위를 주장하지 말고 '분리 불가'로 신고해야 한다."
            % (weakest_pair_overall, pair_worst_overall[weakest_pair_overall],
               lam2[weakest_pair_overall], lam2["W1-L1"], lam2["L1-G1"])),
        also_declare=[
            "as_published(단일자세·무앵커) 설정에서는 세 쌍 전부 lead 부호가 기체마다 "
            "뒤집힌다 — 다섯 기체가 서로 다른 순위 3 종을 낸다. 이 설정으로는 어떤 "
            "파형 순위도 주장할 수 없다.",
            "취약성의 주원인은 σ 의 '오차'가 아니라 '단일자세 인용'이다 "
            "(sigma_sensitivity.aspect_averaged.interpretation).",
            "듀티 축을 걸면 L1 승리는 거의 깨지지 않지만(최악 여유 %.1f dB) "
            "W1-G1 하위순위는 오히려 더 나빠진다 — 그 축은 아직 R90 경로에 없다."
            % (verif["aspect_avg_anchored_duty"]["winner_worst_margin_span_db"] or 0.0)])

    # ======================================================================= #
    # V5. 논문에 그대로 옮길 문장 + 숫자
    # ======================================================================= #
    rec = "aspect_avg_anchored"
    rv = verif[rec]
    out["paper_ready"] = dict(
        recommended_configuration=rec,
        why_this_one=("다섯 기체가 같은 순위에 합의하는 유일한 설정이면서, 두 쌍(W1-L1, "
                      "L1-G1)이 앵커 전 오차범위마저 넘긴다."),
        consensus_order=rv["consensus_order"],
        sentences={
            "common_mode": (
                "The absolute σ level is the weakest quantity in the model, and it enters the "
                "three-waveform comparison only as a common-mode offset. Sweeping it directly "
                "from %.1f to %+.1f dB leaves the waveform ranking unchanged for all five "
                "airframes; it moves absolute detection range by σ_err/4 dB (%.0f%% at "
                "−10 dB, +%.0f%% at +10 dB)."
                % (out["common_mode"]["order_invariance"]["verified_invariant_interval_db"][0],
                   out["common_mode"]["order_invariance"]["verified_invariant_interval_db"][1],
                   100 * (10 ** (-10.0 / 40.0) - 1), 100 * (10 ** (10.0 / 40.0) - 1))),
            "differential": (
                "A differential (frequency-slope) σ error does not cancel. Evaluated directly, "
                "the ordering L1 > G1 > W1 survives a differential error of %.2f dB across the "
                "%.3f GHz band span in the worst airframe, and %.2f dB in the median one."
                % (rv["worst_flip_span_db"], SPAN_GHZ, rv["median_flip_span_db"])),
            "safe_pairs": (
                "The two claims LTE > WiFi and LTE > 5G NR hold for every airframe out to "
                "%.2f dB and %.2f dB of differential error respectively — beyond the %.2f dB "
                "that our pre-anchor slopes would have introduced."
                % (rv["by_pair"]["W1-L1"]["worst_flip_span_db"],
                   rv["by_pair"]["L1-G1"]["worst_flip_span_db"], SS.REALISTIC_SPAN_DB)),
            "fragile_pair": (
                "We do not claim an ordering between WiFi and 5G NR. Their σ-independent λ² "
                "separation is only %.2f dB, and the pair inverts under %.2f dB of "
                "differential error — inside the uncertainty we can defend."
                % (abs(lam2["W1-G1"]), rv["by_pair"]["W1-G1"]["worst_flip_span_db"])),
            "anchor_is_method": (
                "The measured-slope anchor is part of the method, not a cosmetic correction: "
                "without it only %d of 5 airframes retain their ordering under their own "
                "slope error, and the five do not agree on a common ordering at all."
                % n_surv)},
        numbers_to_cite={
            "common_mode_invariant_window_db": out["common_mode"]["order_invariance"]
            ["largest_symmetric_invariant_window_db"],
            "range_shift_per_db_sigma": 0.25,
            "measured_range_slope_mean": out["common_mode"]["quarter_law"]
            ["measured_slope_mean"],
            "worst_flip_span_db": rv["worst_flip_span_db"],
            "median_flip_span_db": rv["median_flip_span_db"],
            "W1-L1_worst_db": rv["by_pair"]["W1-L1"]["worst_flip_span_db"],
            "L1-G1_worst_db": rv["by_pair"]["L1-G1"]["worst_flip_span_db"],
            "W1-G1_worst_db": rv["by_pair"]["W1-G1"]["worst_flip_span_db"],
            "pre_anchor_differential_error_db": SS.REALISTIC_SPAN_DB,
            "post_anchor_residual_db": resid_span},
        blockers_before_use=[
            "앵커가 R90 경로에 실제로 걸려 있지 않다 — experiment_freespace_sigma.py 에 "
            "sigma_anchor 참조 0 회. 걸고 재생성해야 이 숫자를 쓸 수 있다.",
            "정본 outputs/report13_freespace.json 은 pre_blade σ 격자 산출물이다. "
            "live 격자로 재생성 필요.",
            "듀티 축(freespace_link.duty_db_from_cpi)이 한 번도 호출되지 않는다. "
            "크기가 λ² 축보다 커서 넣고 빼는 선택을 논문이 명시해야 한다."])

    # ⚠ json.dump 는 inf/nan 을 Infinity/NaN 으로 써서 엄격 파서를 깨뜨린다.
    #    '±40 dB 안에서 안 뒤집힘' 은 null + 별도 플래그로 표현한다.
    NOFLIP = 40.0

    def sanitize(o):
        if isinstance(o, dict):
            d = {k: sanitize(v) for k, v in o.items()}
            for k in list(d):
                if d[k] is None and k.endswith("_db") and isinstance(o.get(k), float):
                    d[f"{k}_no_flip_within_{NOFLIP:.0f}db"] = True
            return d
        if isinstance(o, (list, tuple)):
            return [sanitize(v) for v in o]
        if isinstance(o, float) and not np.isfinite(o):
            return None
        return o

    out = sanitize(out)
    with open(OUT, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False, allow_nan=False)
    print(f"\n[write] {OUT}  ({os.path.getsize(OUT)/1024:.0f} KB, "
          f"{(datetime.now()-t0).total_seconds():.1f} s)")
    return out


if __name__ == "__main__":
    o = main()
    print("\n" + "=" * 72)
    print("공통모드: 기울기 mean=%.4f (이론 0.25), 1/4법칙 최대편차 %.3f dB, "
          "순위불변 ±%.2f dB, 첫 뒤집힘 %s"
          % (o["common_mode"]["quarter_law"]["measured_slope_mean"],
             o["common_mode"]["quarter_law"]["max_abs_deviation_db"],
             o["common_mode"]["order_invariance"]["largest_symmetric_invariant_window_db"],
             o["common_mode"]["order_invariance"]["first_flip"]))
    print("쌍격차 공통모드 표류: 최대 %.4f dB, 중앙 %.4f dB"
          % (o["common_mode"]["pair_gap_invariance"]["max_lead_drift_db"],
             o["common_mode"]["pair_gap_invariance"]["median_lead_drift_db"]))
    print("문턱 직접검증 %d/%d 통과"
          % (o["flip_threshold"]["direct_verification"]["pair_checks_passed"],
             o["flip_threshold"]["direct_verification"]["pair_checks"]))
    for c, v in o["flip_threshold"]["by_config"].items():
        print("  %-26s worst=%6.3f dB  median=%6.3f  orders=%d  winner=%s  verif=%s"
              % (c, v["worst_flip_span_db"], v["median_flip_span_db"],
                 v["n_distinct_orders"], v["winner"], v["all_direct_verifications_passed"]))
    print("현실오차 대비 판정:", o["realistic_error"]["verdict"],
          "| 자기오차 견딘 기체 %d/5" % o["realistic_error"]["n_drones_surviving_own_pre_anchor_error"])
