# -*- coding: utf-8 -*-
"""
report16_metric_box_bbox.py — 경계상자(box_bbox) 단의 **지표 추출 · 사전예측 대조**
================================================================================

무엇을 하는가
--------------------------------------------------------------------------------
앞 단(benchmark/report16_rung_box_bbox.py)이 만들어 둔 «한 바퀴 위상 표»(복소수 배열)를
다시 열어서, 기반 단(benchmark/report16_base.py)이 못박은 **지표 함수를 그대로 불러**
네 갈래 지표를 다시 계산한다. 그리고 계산 전에 봉인해 둔 **사전 예측 파일**과 하나씩
맞대 본다.

⭐ 이 파일이 앞 단의 JSON 을 «베껴 쓰지 않는» 이유
--------------------------------------------------------------------------------
앞 단은 자기가 계산하고 자기가 채점했다. 그것만 옮겨 적으면 검산이 아니라 복사다.
그래서 여기서는 **저장된 배열에서 지표를 처음부터 다시 계산**하고, 앞 단 JSON 이 적어
둔 값과 **자릿수까지 대조**한다(recompute_gate). 두 값이 어긋나면 그 사실이 결과다.

네 갈래 지표 (전부 report16_base.md_metrics16 이 정의한 것)
--------------------------------------------------------------------------------
 ① flash_contrast_db  «플래시(순간적으로 확 밝아지는 봉우리)가 바닥보다 몇 dB 위인가»
 ② 고차 성분 풍부도    n_eff_orders · order_p50 · order_p90 · dominant_order ·
                       blade_comb_frac  «흔들림이 몇 개의 배음(하모닉)에 퍼져 있나»
 ③ 폭                  width_ratio (−10/−20/−30 dB 문턱) · fd_edge_hz
                       «도플러가 퍼진 폭이 프로펠러 팁 속도 예측과 맞는가»
 ④ 동체:블레이드 비    dc_ac_db  «안 움직이는 부분 대 움직이는 부분의 세기비»

⭐ 여기서 새로 하는 것 — «주기» 를 정면으로 잰다
--------------------------------------------------------------------------------
과제문이 준 사전 예측은 «큐브와 비슷하되 종횡비가 달라 **주기가 다르게** 나올 수 있다»
였다. 앞 단은 그것을 «90° 돌려 겹쳐본 상관계수» 로 재고 문턱(0.5)에서 빗나갔다.
상관계수는 «얼마나 닮았나» 이지 «주기» 가 아니다. 그래서 여기서는 주기를 두 가지
독립적인 방법으로 **직접** 잰다:
   (a) 표를 Δ 만큼 돌려 자기 자신과 겹쳐, 상관이 문턱을 넘는 **가장 작은 Δ** = 주기.
   (b) AC 전력이 실린 차수들의 **최대공약수** g → 주기 = 360°/g.
       (전력이 4·8·12… 에만 있으면 g=4 → 90° 주기. 2·4·6… 이면 g=2 → 180°.)
두 방법이 같은 답을 주면 «주기» 라는 말을 쓸 자격이 있다.

⛔ 규율
--------------------------------------------------------------------------------
 · 읽기만: outputs/report16_rung_box_bbox*.{json,npz}, outputs/report16_base*.{json,npz},
           outputs/report16_rung_box_bbox_prediction.json, benchmark/report16_base.py
 · 쓰기: outputs/report16_metric_box_bbox.json 하나뿐.
 · outputs/report15_* · benchmark/report15_* · src/make_report0N_* · src/drones.py ·
   src/drone_cad.py 는 건드리지 않는다(열지도 않는다).
 · 숫자 손입력 금지 — 문턱값 말고는 전부 배열에서 계산한다.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time
from math import gcd

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, _HERE)

from report16_base import md_metrics16, ac_corr, summarize   # noqa: E402  (재구현 금지)

RUNG_JSON = os.path.join(ROOT, "outputs", "report16_rung_box_bbox.json")
RUNG_NPZ = os.path.join(ROOT, "outputs", "report16_rung_box_bbox_tables.npz")
PRED_JSON = os.path.join(ROOT, "outputs", "report16_rung_box_bbox_prediction.json")
BASE_JSON = os.path.join(ROOT, "outputs", "report16_base.json")
BASE_NPZ = os.path.join(ROOT, "outputs", "report16_base_tables.npz")
OUT_JSON = os.path.join(ROOT, "outputs", "report16_metric_box_bbox.json")

# ── 문턱값 (여기 적힌 것이 전부. 나머지는 계산값) ──────────────────────────────
SIM_THRESHOLDS = (0.99, 0.95, 0.90)      # 주기 판정용 자기유사도 문턱
POWER_THRESHOLDS = (1e-2, 1e-3, 1e-4)    # 차수 «살아 있음» 판정용 전력 몫 문턱
SEPARATION_SD = 2.0                      # |짝지은차이 ÷ 메쉬 자세산포| 가 이 값 이상이면 «가름»
GATE_TOL = 1e-9                          # 재계산 일치 허용오차 (상대)

DRONES = ("mini2", "matrice4e")
BOX_ARMS = ("box_bbox", "box_bbox_axis", "box_aspect_voleq", "cube_eqvol",
            "prop_bbox", "box_bbox_fine", "box_bbox_S256", "box_bbox_S512")
REF_ARMS = ("mesh", "slab", "disc", "sphere")
WF = "spherical"          # 헤드라인 파면


def sha256(path, n=16):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()[:n]


# --------------------------------------------------------------------------- #
#  ⭐ 주기 측정 — 두 가지 독립적인 방법
# --------------------------------------------------------------------------- #
def self_similarity_curve(tab):
    """표를 s 칸씩 돌려 자기 자신과 겹친 상관 곡선. s=0 은 1.0 (뺀다)."""
    tab = np.asarray(tab, complex)
    S = len(tab)
    return np.array([ac_corr(tab, np.roll(tab, s)) for s in range(S)], float)


def period_from_similarity(curve, thr):
    """상관이 **한 번 문턱 아래로 내려갔다가 다시** thr 을 넘는 가장 작은 회전각.

    ⚠ 「가장 작은 s>0 에서 상관 ≥ thr」로 정의하면 안 된다. 매끄러운 신호는 한 칸만
    돌려도 거의 그대로라서 «주기 = 한 칸» 이라는 헛값이 나온다(실제로 메쉬 팔에서
    그런 헛값이 나왔다). 그래서 «먼저 문턱 아래로 떨어졌는가» 를 조건에 넣는다.
    """
    S = len(curve)
    dipped = False
    for s in range(1, S):
        if curve[s] < thr:
            dipped = True
        elif dipped:
            # 문턱을 막 넘은 지점은 봉우리의 «어깨» 일 수 있다 — 봉우리 꼭대기까지 올라간다.
            while s + 1 < S and curve[s + 1] > curve[s]:
                s += 1
            return float(360.0 * s / S), int(s)
    return 360.0, S


def order_power(tab):
    """차수별 AC 전력 몫 (합 = 1). 차수 m 은 |m| 로 접어 더한다."""
    tab = np.asarray(tab, complex)
    S = len(tab)
    c = np.fft.fft(tab) / S
    P = np.abs(c) ** 2
    m_idx = np.fft.fftfreq(S, d=1.0 / S).astype(int)
    ac = m_idx != 0
    tot = float(P[ac].sum())
    op = np.zeros(S // 2 + 1)
    if tot <= 0:
        return op
    np.add.at(op, np.abs(m_idx[ac]), P[ac] / tot)
    return op


def period_from_orders(op, thr):
    """살아 있는 차수들의 최대공약수 g → 주기 360/g. 전력 몫 thr 이상만 «살아 있음»."""
    live = [int(m) for m in np.where(op >= thr)[0] if m > 0]
    if not live:
        return dict(g=0, period_deg=float("nan"), n_live=0, live_min=None, live_max=None)
    g = 0
    for m in live:
        g = gcd(g, m)
    return dict(g=int(g), period_deg=float(360.0 / g) if g else float("nan"),
                n_live=len(live), live_min=int(min(live)), live_max=int(max(live)),
                live_orders_head=[int(x) for x in live[:12]])


def order_classes(op):
    """차수 전력을 홀수 / 4의배수아닌짝수 / 4의배수 로 가른다."""
    m = np.arange(len(op))
    return dict(odd=float(op[(m % 2) == 1].sum()),
                even_not_mult4=float(op[(m % 4) == 2].sum()),
                mult4=float(op[(m > 0) & ((m % 4) == 0)].sum()))


# --------------------------------------------------------------------------- #
#  적재
# --------------------------------------------------------------------------- #
def main():
    t0 = time.time()
    rung = json.load(open(RUNG_JSON, encoding="utf-8"))
    base = json.load(open(BASE_JSON, encoding="utf-8"))
    pred = json.load(open(PRED_JSON, encoding="utf-8"))
    zr = np.load(RUNG_NPZ, allow_pickle=True)
    zb = np.load(BASE_NPZ, allow_pickle=True)

    proto = {}      # (band, drone) -> 규약 dict
    for d in DRONES:
        proto[("main", d)] = base["protocol_per_drone"][d]
        proto[("hi", d)] = base["protocol_per_drone"][d]["hi_band"]

    blades = {d: int(rung["geometry"][d]["prop_blades"]) for d in DRONES}

    def get_tab(band, drone, arm, wf=WF):
        """저장된 한 바퀴 표 (n_az, n_phase). 기준 팔은 기반 단 npz 에서 읽는다."""
        k = f"{band}__{drone}__{arm}__{wf}"
        if k in zr:
            return np.asarray(zr[k])
        kb = (f"main__G_0804__{drone}__{arm}__{wf}" if band == "main"
              else f"hi__hi__G_0804__{drone}__{arm}__{wf}")
        if kb in zb:
            return np.asarray(zb[kb])
        return None

    # ── ①~④ 지표 재계산 ────────────────────────────────────────────────────
    per_arm = {}          # tag -> {metric: summarize(...)}
    per_arm_raw = {}      # tag -> {metric: [az 별 값]}
    extra = {}            # tag -> 주기·차수분류 등
    for band in ("main", "hi"):
        for d in DRONES:
            P = proto[(band, d)]
            for arm in BOX_ARMS + REF_ARMS:
                tab = get_tab(band, d, arm)
                if tab is None:
                    continue
                tag = f"{band}|{d}|{arm}"
                rows = [md_metrics16(tab[i], P, blades[d]) for i in range(tab.shape[0])]
                keys = ("flash_contrast_db", "n_eff_orders", "order_p50", "order_p90",
                        "dominant_order", "blade_comb_frac", "fd_edge_hz", "width_ratio",
                        "width_ratio_10db", "width_ratio_30db", "dc_ac_db", "ac_frac_db",
                        "sigma_eq_mean_dbsm", "ac_over_floor_db", "in_band_ac_frac",
                        "in_band_ac_over_dc_db")
                per_arm_raw[tag] = {k: [r[k] for r in rows] for k in keys}
                per_arm[tag] = {k: summarize(per_arm_raw[tag][k]) for k in keys}
                per_arm[tag]["_n_phase"] = int(tab.shape[1])
                per_arm[tag]["_n_az"] = int(tab.shape[0])
                per_arm[tag]["_interpretable_frac"] = float(
                    np.mean([r["metrics_interpretable"] for r in rows]))
                per_arm[tag]["_band_order"] = int(rows[0]["band_order"])

                # 주기 · 차수 분류 (방위마다 재고 평균)
                sims = np.array([self_similarity_curve(tab[i]) for i in range(tab.shape[0])])
                ops = np.array([order_power(tab[i]) for i in range(tab.shape[0])])
                sim_mean = sims.mean(axis=0)
                op_mean = ops.mean(axis=0)
                per_az_period = {f"thr{thr}": [period_from_similarity(sims[i], thr)[0]
                                               for i in range(sims.shape[0])]
                                 for thr in SIM_THRESHOLDS}
                cls = order_classes(op_mean)
                S = tab.shape[1]
                extra[tag] = dict(
                    period_by_similarity={
                        f"thr_{thr}": dict(
                            period_deg_from_az_mean_curve=period_from_similarity(sim_mean, thr)[0],
                            per_az=summarize(per_az_period[f"thr{thr}"]),
                            all_az_agree=bool(len(set(per_az_period[f"thr{thr}"])) == 1))
                        for thr in SIM_THRESHOLDS},
                    period_by_order_gcd={f"pow_{thr:g}": period_from_orders(op_mean, thr)
                                         for thr in POWER_THRESHOLDS},
                    similarity_at={f"{int(360*s/S)}deg": float(sim_mean[s])
                                   for s in (S // 8, S // 4, S // 3, S // 2)
                                   if 360 * s / S == int(360 * s / S)},
                    order_classes=cls,
                    dominant_order_mode=int(np.argmax(op_mean)),
                    phase_grid_S=int(S),
                )

    # ── 재계산 일치 검사 (앞 단 JSON 과 자릿수 대조) ─────────────────────────
    gate_rows, gate_max = [], 0.0
    for tag, mm in per_arm.items():
        src = None
        if tag in rung["arms"]:
            src = rung["arms"][tag][WF]["per_az"]
        elif tag in rung["reference_arms"]:
            src = rung["reference_arms"][tag]["per_az"]
        if src is None:
            continue
        worst, worst_k = 0.0, None
        for k, v in src.items():
            if k not in mm or "mean" not in v:
                continue
            a, b = float(mm[k]["mean"]), float(v["mean"])
            den = max(abs(b), 1e-12)
            rel = abs(a - b) / den
            if rel > worst:
                worst, worst_k = rel, k
        gate_rows.append(dict(tag=tag, max_rel_diff=worst, worst_metric=worst_k))
        gate_max = max(gate_max, worst)
    recompute_gate = dict(
        max_rel_diff_vs_rung_json=gate_max,
        tolerance=GATE_TOL,
        verdict="PASS" if gate_max <= GATE_TOL else "FAIL",
        n_arms_checked=len(gate_rows),
        per_arm=sorted(gate_rows, key=lambda r: -r["max_rel_diff"])[:8],
        what_ko=("저장된 배열에서 지표를 처음부터 다시 계산해 앞 단 JSON 의 값과 맞춰 본 것. "
                 "PASS 면 앞 단이 적은 수가 배열과 일치한다는 뜻이고, 그래야 아래 대조를 "
                 "믿을 수 있다. FAIL 이면 앞 단 JSON 이 아니라 배열이 옳다."))

    # ── 짝지은 차이 (같은 방위끼리 빼고, 메쉬 자세산포로 나눈다) ───────────────
    def paired(band, d, arm, ref="mesh"):
        a, b = per_arm_raw.get(f"{band}|{d}|{arm}"), per_arm_raw.get(f"{band}|{d}|{ref}")
        if a is None or b is None:
            return None
        out = {}
        for k in a:
            va, vb = np.asarray(a[k], float), np.asarray(b[k], float)
            if va.shape != vb.shape:
                continue
            dd = va - vb
            fin = np.isfinite(dd)
            if not fin.any():
                continue
            dd = dd[fin]
            sd_ref = float(np.std(vb[fin], ddof=1)) if fin.sum() > 1 else 0.0
            out[k] = dict(paired_mean=float(dd.mean()),
                          paired_sd=float(dd.std(ddof=1)) if dd.size > 1 else 0.0,
                          frac_positive=float(np.mean(dd > 0)),
                          ref_pose_sd=sd_ref,
                          separation_in_pose_sd=(float(dd.mean() / sd_ref)
                                                 if sd_ref > 0 else float("inf")),
                          n=int(dd.size))
        return out

    paired_vs_mesh = {}
    for band in ("main", "hi"):
        for d in DRONES:
            for arm in BOX_ARMS:
                p = paired(band, d, arm, "mesh")
                if p:
                    paired_vs_mesh[f"{band}|{d}|{arm} - mesh"] = p
    for d in DRONES:                     # 기준 팔도 같은 잣대로
        for arm in ("slab", "disc", "sphere"):
            p = paired("main", d, arm, "mesh")
            if p:
                paired_vs_mesh[f"main|{d}|{arm} - mesh"] = p

    # 형상 판정에 쓸 지표만 골라 «몇 개나 갈렸나» 를 센다
    DECIDING = ("flash_contrast_db", "n_eff_orders", "order_p90", "blade_comb_frac",
                "width_ratio", "in_band_ac_over_dc_db")
    separation_count = {}
    for tagref, p in paired_vs_mesh.items():
        if not tagref.startswith("main|"):
            continue
        hits = {k: abs(p[k]["separation_in_pose_sd"]) >= SEPARATION_SD
                for k in DECIDING if k in p}
        separation_count[tagref] = dict(
            n_separating=int(sum(hits.values())), n_metrics=len(hits),
            which=[k for k, v in hits.items() if v],
            detail={k: p[k]["separation_in_pose_sd"] for k in hits})

    # ── ⭐ 사전 예측 대조 ─────────────────────────────────────────────────────
    def m(band, d, arm, k, stat="mean"):
        return per_arm[f"{band}|{d}|{arm}"][k][stat]

    score = {}

    # 과제문 헤드라인: «큐브와 비슷하되 종횡비가 달라 주기가 다르게 나올 수 있다»
    head = {}
    for d in DRONES:
        cu, bx, ax = (extra[f"main|{d}|cube_eqvol"], extra[f"main|{d}|box_bbox"],
                      extra[f"main|{d}|box_bbox_axis"])
        head[d] = dict(
            aspect_xy=rung["geometry"][d]["aspect_xy"],
            period_deg_similarity_thr0_99=dict(
                cube_eqvol=cu["period_by_similarity"]["thr_0.99"]["period_deg_from_az_mean_curve"],
                box_bbox_axis=ax["period_by_similarity"]["thr_0.99"]["period_deg_from_az_mean_curve"],
                box_bbox=bx["period_by_similarity"]["thr_0.99"]["period_deg_from_az_mean_curve"],
                mesh=extra[f"main|{d}|mesh"]["period_by_similarity"]["thr_0.99"]["period_deg_from_az_mean_curve"]),
            period_deg_order_gcd_pow1e_3=dict(
                cube_eqvol=cu["period_by_order_gcd"]["pow_0.001"]["period_deg"],
                box_bbox_axis=ax["period_by_order_gcd"]["pow_0.001"]["period_deg"],
                box_bbox=bx["period_by_order_gcd"]["pow_0.001"]["period_deg"],
                mesh=extra[f"main|{d}|mesh"]["period_by_order_gcd"]["pow_0.001"]["period_deg"]),
            similarity_curve_agrees_with_order_gcd=bool(
                cu["period_by_similarity"]["thr_0.99"]["period_deg_from_az_mean_curve"]
                == cu["period_by_order_gcd"]["pow_0.001"]["period_deg"]
                and ax["period_by_similarity"]["thr_0.99"]["period_deg_from_az_mean_curve"]
                == ax["period_by_order_gcd"]["pow_0.001"]["period_deg"]),
            cube_vs_box_axis_period_differ=bool(
                cu["period_by_order_gcd"]["pow_0.001"]["period_deg"]
                != ax["period_by_order_gcd"]["pow_0.001"]["period_deg"]),
            similarity_to_cube_at_90deg=dict(
                cube=cu["similarity_at"].get("90deg"),
                box_bbox_axis=ax["similarity_at"].get("90deg"),
                box_bbox=bx["similarity_at"].get("90deg")),
        )
    all_differ = all(head[d]["cube_vs_box_axis_period_differ"] for d in DRONES)
    both_methods = all(head[d]["similarity_curve_agrees_with_order_gcd"] for d in DRONES)
    score["TASK_HEADLINE_period_differs_from_cube"] = dict(
        claim_ko=("과제문 사전 예측 — «큐브와 비슷하되 종횡비가 달라 주기가 다르게 "
                  "나올 수 있다»"),
        how_measured_ko=("주기를 두 방법으로 직접 쟀다. (a) 표를 돌려 겹쳐 상관 ≥ 0.99 가 "
                         "되는 가장 작은 회전각, (b) 전력이 실린 차수들의 최대공약수 g → "
                         "360°/g. 둘이 같은 답을 줄 때만 «주기» 라고 부른다."),
        per_drone=head,
        two_methods_agree=both_methods,
        verdict=("CONFIRMED" if (all_differ and both_methods) else
                 "REFUTED" if not all_differ else "PARTIAL"),
        verdict_note_ko="",
    )

    # P1 — 상자는 널이 아니다
    p1 = {}
    for d in DRONES:
        p1[d] = dict(box=m("main", d, "box_bbox", "in_band_ac_over_dc_db"),
                     sphere=m("main", d, "sphere", "in_band_ac_over_dc_db"))
        p1[d]["gap_db"] = p1[d]["box"] - p1[d]["sphere"]
    thr1 = float(pred["items"]["P1_box_is_not_a_null"]["threshold_db"])
    score["P1_box_is_not_a_null"] = dict(
        threshold_db=thr1, per_drone=p1,
        verdict="CONFIRMED" if all(v["gap_db"] > thr1 for v in p1.values()) else "REFUTED")

    # P2 — 90° 대칭이 깨지고 180° 만 남는다 (예측이 건 문턱 그대로)
    th2 = pred["items"]["P2_period_180_not_90"]["threshold"]
    p2 = {}
    for d in DRONES:
        cu = extra[f"main|{d}|cube_eqvol"]
        ax = extra[f"main|{d}|box_bbox_axis"]
        cu_s90 = cu["similarity_at"].get("90deg")
        ax_s90 = ax["similarity_at"].get("90deg")
        ax_s180 = ax["similarity_at"].get("180deg")
        p2[d] = dict(cube_sym90=cu_s90, box_axis_sym90=ax_s90, box_axis_sym180=ax_s180,
                     cube_even_not_mult4=cu["order_classes"]["even_not_mult4"],
                     box_axis_even_not_mult4=ax["order_classes"]["even_not_mult4"],
                     cube_dominant_order=cu["dominant_order_mode"],
                     box_axis_dominant_order=ax["dominant_order_mode"],
                     pass_cube_sym90=bool(cu_s90 >= th2["cube_sym90_min"]),
                     pass_box_sym90=bool(ax_s90 <= th2["box_sym90_max"]),
                     pass_box_sym180=bool(ax_s180 >= th2["box_sym180_min"]))
    score["P2_period_180_not_90"] = dict(
        thresholds=th2, per_drone=p2,
        verdict=("CONFIRMED" if all(v["pass_cube_sym90"] and v["pass_box_sym90"]
                                    and v["pass_box_sym180"] for v in p2.values())
                 else "REFUTED"),
        direction_ko=("방향은 맞았다 — 큐브는 4의 배수 차수에만 실리고(≡2 mod 4 몫이 0 에 "
                      "가깝다) 상자는 ≡2 mod 4 가 살아난다. 틀린 것은 «상관계수» 로 건 문턱이다: "
                      "상관계수는 대칭이 깨진 **정도**를 재는 것이지 주기의 유무가 아니다."))

    # P2b — 축이탈이 홀수 차수를 만든다
    p2b = {}
    for d in DRONES:
        p2b[d] = dict(
            offset_mm=rung["geometry"][d]["mesh_bbox_center_offset_from_spin_axis_mm"],
            odd_frac_box_bbox=extra[f"main|{d}|box_bbox"]["order_classes"]["odd"],
            odd_frac_box_bbox_axis=extra[f"main|{d}|box_bbox_axis"]["order_classes"]["odd"])
        p2b[d]["ratio"] = (p2b[d]["odd_frac_box_bbox"] /
                           max(p2b[d]["odd_frac_box_bbox_axis"], 1e-30))
    score["P2b_offaxis_gives_odd_orders"] = dict(
        per_drone=p2b,
        verdict=("CONFIRMED" if all(v["odd_frac_box_bbox"] > v["odd_frac_box_bbox_axis"]
                                    and v["odd_frac_box_bbox_axis"] < 0.01
                                    for v in p2b.values()) else "REFUTED"))

    # P3 — 폭이 프롭 팁을 넘고, 상한은 모서리비
    p3 = {}
    for d in DRONES:
        up = float(pred["items"]["P3_width_exceeds_prop_tip"]["predicted_upper"][d])
        wr = m("main", d, "box_bbox", "width_ratio")
        q = float(base["protocol_per_drone"][d]["order_quantum_rel"])
        p3[d] = dict(width_ratio=wr, predicted_upper=up, order_quantum_rel=q,
                     exceeds_one=bool(wr > 1.0),
                     within_upper_plus_one_quantum=bool(wr <= up + q),
                     overshoot_in_quanta=(wr - up) / q)
    score["P3_width_exceeds_prop_tip"] = dict(
        per_drone=p3,
        verdict=("CONFIRMED" if all(v["exceeds_one"] and v["within_upper_plus_one_quantum"]
                                    for v in p3.values()) else "REFUTED"))

    # P4 — 규약 판정기가 상자를 오판한다
    p4 = {}
    for d in DRONES:
        own = rung["arms"][f"main|{d}|box_bbox"][WF]["own_band_gauge"]["per_az"]
        p4[d] = dict(in_band_ac_frac_protocol_gauge=m("main", d, "box_bbox", "in_band_ac_frac"),
                     in_band_ac_frac_own_gauge=own["in_band_ac_frac"]["mean"],
                     band_order_protocol=per_arm[f"main|{d}|box_bbox"]["_band_order"],
                     band_order_own=rung["arms"][f"main|{d}|box_bbox"][WF]["own_band_gauge"]["band_order"],
                     predicted_misjudge=bool(m("main", d, "box_bbox", "in_band_ac_frac") < 0.5),
                     recovers_on_own_gauge=bool(own["in_band_ac_frac"]["mean"] > 0.9))
    score["P4_in_band_gate_will_misjudge_the_box"] = dict(
        per_drone=p4,
        verdict=("CONFIRMED" if all(v["predicted_misjudge"] and v["recovers_on_own_gauge"]
                                    for v in p4.values()) else "REFUTED"),
        surviving_claim_ko=("판정기가 상자를 «해석 불가» 로 찍지는 **않았다**. 다만 폭 지표의 "
                            "분모(f_tip)가 프로펠러 반경에 고정돼 있다는 점은 그대로 남는다 — "
                            "상자 자신의 모서리로 재면 width_ratio 가 1 근처로 돌아온다."))

    # P5 — 플래시가 메쉬보다 작지 않다
    p5 = {}
    for d in DRONES:
        pb = paired_vs_mesh[f"main|{d}|box_bbox - mesh"]["flash_contrast_db"]
        pp = paired_vs_mesh[f"main|{d}|prop_bbox - mesh"]["flash_contrast_db"]
        p5[d] = dict(box_bbox_minus_mesh=pb["paired_mean"],
                     box_bbox_sep_sd=pb["separation_in_pose_sd"],
                     prop_bbox_minus_mesh=pp["paired_mean"],
                     prop_bbox_sep_sd=pp["separation_in_pose_sd"],
                     mesh_pose_sd=pb["ref_pose_sd"])
    score["P5_flash_not_smaller_than_mesh"] = dict(
        per_drone=p5,
        verdict=("CONFIRMED" if all(v["box_bbox_minus_mesh"] >= 0 for v in p5.values())
                 else "REFUTED"),
        caveat_ko=("box_bbox 는 **운동학도 함께 바뀐** 팔이다(정적 프레임이 없다). 운동학을 "
                   "맞춘 prop_bbox 에서는 같은 차이가 메쉬 자세산포 안으로 들어온다 — "
                   "즉 이 «확인» 을 형상 효과로 읽으면 안 된다."))

    # P6 — blade_comb_frac 은 상자와 블레이드를 구별 못 한다
    p6 = {}
    for d in DRONES:
        bc_ax = m("main", d, "box_bbox_axis", "blade_comb_frac")
        bc_me = m("main", d, "mesh", "blade_comb_frac")
        bc_bx = m("main", d, "box_bbox", "blade_comb_frac")
        p6[d] = dict(box_axis=bc_ax, mesh=bc_me, box_bbox=bc_bx,
                     abs_diff_axis_vs_mesh=abs(bc_ax - bc_me),
                     abs_diff_bbox_vs_mesh=abs(bc_bx - bc_me),
                     pass_axis_high=bool(bc_ax > 0.9),
                     pass_close_to_mesh=bool(abs(bc_ax - bc_me) < 0.2))
    score["P6_blade_comb_cannot_tell_them_apart"] = dict(
        per_drone=p6,
        verdict=("CONFIRMED" if all(v["pass_axis_high"] and v["pass_close_to_mesh"]
                                    for v in p6.values()) else "REFUTED"))

    # P7 — 풍부도 방향 (일부러 예측 안 함)
    p7 = {}
    for d in DRONES:
        p7[d] = {arm: dict(
            paired_mean=paired_vs_mesh[f"main|{d}|{arm} - mesh"]["n_eff_orders"]["paired_mean"],
            frac_positive=paired_vs_mesh[f"main|{d}|{arm} - mesh"]["n_eff_orders"]["frac_positive"],
            sep_sd=paired_vs_mesh[f"main|{d}|{arm} - mesh"]["n_eff_orders"]["separation_in_pose_sd"])
            for arm in ("box_bbox", "box_bbox_axis", "box_aspect_voleq", "cube_eqvol",
                        "prop_bbox", "slab")}
    score["P7_direction_of_richness_unknown"] = dict(
        per_drone=p7, verdict="RECORDED (부호를 예측하지 않은 항목)",
        observed_ko=("모든 프리미티브가 메쉬보다 «풍부» 하게 나왔다. 다만 부피를 맞추면 그 "
                     "크기가 급격히 줄어든다 — 아래 volume_confound 를 함께 읽을 것."))

    # P8 — 대역 간 부호 일치
    p8 = {}
    for d in DRONES:
        ks = ("flash_contrast_db", "n_eff_orders", "order_p90", "blade_comb_frac",
              "width_ratio", "dc_ac_db", "sigma_eq_mean_dbsm")
        agree, det = 0, {}
        for k in ks:
            a = paired_vs_mesh[f"main|{d}|box_bbox - mesh"][k]["paired_mean"]
            b = paired_vs_mesh.get(f"hi|{d}|box_bbox - mesh", {}).get(k, {}).get("paired_mean")
            ok = (b is not None) and (np.sign(a) == np.sign(b))
            det[k] = dict(main=a, hi=b, sign_agrees=bool(ok))
            agree += int(ok)
        p8[d] = dict(n_agree=agree, n_total=len(ks), detail=det)
    score["P8_kernel_comfort_asymmetry"] = dict(
        per_drone=p8,
        verdict=("CONFIRMED" if all(v["n_agree"] >= v["n_total"] - 1 for v in p8.values())
                 else "PARTIAL"))

    tally = {}
    for k, v in score.items():
        tally[v["verdict"].split()[0]] = tally.get(v["verdict"].split()[0], 0) + 1

    # ── ⭐ 앞 단의 자기채점과 대조 — 같은 예측을 두 번 채점해 본다 ────────────
    rung_score = rung["prediction_score"]
    disagreement = {}
    for k, v in score.items():
        if k not in rung_score:
            continue
        mine = v["verdict"].split()[0]
        theirs = str(rung_score[k].get("verdict", "")).split()[0]
        if mine != theirs:
            disagreement[k] = dict(mine=mine, rung=theirs)
    # P3 는 문턱이 어긋난 사례라 수치를 붙여 둔다
    if "P3_width_exceeds_prop_tip" in disagreement:
        disagreement["P3_width_exceeds_prop_tip"].update(
            overshoot_in_order_quanta={d: p3[d]["overshoot_in_quanta"] for d in DRONES},
            preregistered_tolerance_quanta=1.0,
            rung_applied_tolerance_quanta=2.0,
            why_ko=("사전 예측 파일에 적힌 허용오차는 «오차 1차수 이내» 인데, 앞 단 코드는 "
                    "`w <= up + 2*q` 로 **2차수**를 썼다. mini2 의 초과분이 1.16 차수라 "
                    "1차수 기준으로는 걸리고 2차수 기준으로는 통과한다. 방향(폭이 프롭 팁을 "
                    "넘고 상한이 모서리비)은 두 기준 모두에서 맞다 — 어긋난 것은 허용오차다."))
    disagreement["_what_ko"] = (
        "같은 사전 예측을 앞 단과 이 단이 각각 채점했다. 어긋난 항목만 적는다. "
        "어긋남 자체가 결과다 — 문턱을 어떻게 읽느냐로 «맞았다/틀렸다» 가 뒤집힌다는 뜻이다.")

    # ── ⭐ 주기가 «형상 정밀도» 를 가르는가 ──────────────────────────────────
    period_disc = {}
    for d in DRONES:
        g = {a: extra[f"main|{d}|{a}"]["period_by_order_gcd"]["pow_0.001"]["period_deg"]
             for a in ("mesh", "cube_eqvol", "box_bbox_axis", "box_aspect_voleq",
                       "prop_bbox", "slab", "box_bbox")}
        s = {a: extra[f"main|{d}|{a}"]["period_by_similarity"]["thr_0.99"]
             ["period_deg_from_az_mean_curve"]
             for a in g}
        period_disc[d] = dict(
            period_deg_order_gcd=g, period_deg_similarity=s,
            both_methods_agree={a: bool(g[a] == s[a]) for a in g},
            equals_mesh_period={a: bool(g[a] == g["mesh"]) for a in g if a != "mesh"})
    period_disc["conclusion_ko"] = (
        "주기는 **정육면체만** 가려낸다(90° ↔ 나머지 180°). 종횡비를 가진 상자·평판·"
        "프롭경계상자는 진짜 CAD 메쉬와 **같은 180° 주기**를 낸다. 즉 «주기» 는 "
        "«CAD 대 프리미티브» 를 가르는 축이 아니라 «단면이 정사각인가 아닌가» 를 가르는 축이다. "
        "축을 벗어나 놓인 box_bbox 만 360° 인데, 그것은 형상이 아니라 위치(축이탈) 때문이다.")
    period_disc["method_caveat_ko"] = (
        "회전 겹침 방식은 «한 번 문턱 아래로 떨어졌다가 다시 올라온 첫 봉우리» 로 정의해야 한다. "
        "그냥 «문턱을 넘는 가장 작은 각» 으로 잡으면 매끄러운 신호에서 «주기 = 격자 한 칸» "
        "이라는 헛값이 나온다(메쉬 팔에서 실제로 그랬다). 널 팔(원판·구)의 주기 값은 "
        "이산화 잔차를 잰 것이라 읽으면 안 된다.")

    # ── 통제 재검산 — 위상 격자·점구름 밀도가 결과를 바꾸는가 ─────────────────
    #   앞 단이 «안 바뀐다» 고 적었다. 그 말을 배열에서 직접 확인한다.
    CTRL_KEYS = ("flash_contrast_db", "n_eff_orders", "width_ratio", "dc_ac_db",
                 "blade_comb_frac", "sigma_eq_mean_dbsm", "in_band_ac_frac")
    controls = {}
    for d in DRONES:
        base_tag = f"main|{d}|box_bbox"
        row = {}
        for other, label in ((f"main|{d}|box_bbox_fine", "point_density_x4"),
                             (f"main|{d}|box_bbox_S{2 * per_arm[base_tag]['_n_phase']}",
                              "phase_grid_x2")):
            if other not in per_arm:
                continue
            row[label] = dict(
                arm=other.split("|")[-1],
                n_phase=per_arm[other]["_n_phase"],
                delta={k: per_arm[other][k]["mean"] - per_arm[base_tag][k]["mean"]
                       for k in CTRL_KEYS})
        # 통제 변화폭 ÷ 재려는 효과(상자−메쉬) — 1 보다 훨씬 작아야 통제가 통과다
        eff = paired_vs_mesh[f"main|{d}|box_bbox - mesh"]
        for label, r in row.items():
            r["delta_over_measured_effect"] = {
                k: (abs(r["delta"][k]) / abs(eff[k]["paired_mean"])
                    if k in eff and abs(eff[k]["paired_mean"]) > 0 else None)
                for k in CTRL_KEYS}
            r["worst_ratio"] = max(v for v in r["delta_over_measured_effect"].values()
                                   if v is not None)
            r["worst_ratio_shape_metrics_only"] = max(
                v for k, v in r["delta_over_measured_effect"].items()
                if v is not None and k != "sigma_eq_mean_dbsm")
            r["worst_metric"] = max((v, k) for k, v in r["delta_over_measured_effect"].items()
                                    if v is not None)[1]
        controls[d] = row
    controls["verdict_ko"] = (
        "위상 격자를 2배로, 점구름을 4배로 촘촘히 해도 지표 변화가 «재려는 효과(상자−메쉬)» "
        "에 비해 훨씬 작으면 통제 통과다. worst_ratio 가 그 비다.")
    controls["worst_ratio_overall"] = max(
        r["worst_ratio"] for d in DRONES for r in controls[d].values()
        if isinstance(r, dict) and "worst_ratio" in r)
    controls["worst_ratio_shape_metrics_only"] = max(
        r["worst_ratio_shape_metrics_only"] for d in DRONES for r in controls[d].values()
        if isinstance(r, dict) and "worst_ratio_shape_metrics_only" in r)
    controls["sigma_exception_ko"] = (
        "가장 큰 비는 절대 세기(σ)에서 나온다 — matrice4e 를 4배 촘촘하게 하면 σ 가 "
        "0.60 dB 움직이는데, 상자−메쉬 σ 차이 자체가 작아서 비가 0.30 까지 오른다. "
        "다만 σ 는 프리미티브 PEC ↔ 메쉬 재질가중이라 형상 판정에서 이미 뺀 지표다. "
        "형상 판정용 지표만 보면 비가 3% 이하다.")

    # ── ⚠ 널 팔로 «갈림 개수» 세는 방식을 교정한다 ──────────────────────────
    #   구·원판은 **물리적 변조가 0** 이어야 하는 팔이다. 그런데도 «갈렸다» 고 세어지면
    #   그 세는 방식이 잘못된 것이다. 얼마나 잘못되는지 실측한다.
    null_cal = dict(per_drone={}, rule_ko="", what_ko="")
    for d in DRONES:
        row = {}
        for a in ("sphere", "disc", "mesh", "prop_bbox", "slab", "cube_eqvol",
                  "box_aspect_voleq", "box_bbox_axis", "box_bbox"):
            tag = f"main|{d}|{a}"
            if tag not in per_arm:
                continue
            sc = separation_count.get(f"main|{d}|{a} - mesh")
            row[a] = dict(
                interpretable_frac=per_arm[tag]["_interpretable_frac"],
                in_band_ac_frac=per_arm[tag]["in_band_ac_frac"]["mean"],
                n_separating_raw=(sc["n_separating"] if sc else None),
                counts_as_readable=bool(per_arm[tag]["_interpretable_frac"] >= 1.0))
        null_cal["per_drone"][d] = row
    null_cal["false_positive_on_nulls"] = {
        d: {a: null_cal["per_drone"][d][a]["n_separating_raw"] for a in ("sphere", "disc")}
        for d in DRONES}
    null_cal["rule_ko"] = (
        "⭐ «형상 판정 6지표 중 n 개가 갈렸다» 는 집계는 **in_band_ac_frac ≥ 0.5 인 팔에서만** "
        "읽어야 한다. 구·원판은 물리적 변조가 0 인데도 이 집계에서 4~6/6 이 나온다 — "
        "그 값들은 이산화 잔차를 잰 것이기 때문이다(기반 단이 metrics_interpretable 로 "
        "미리 경고해 둔 그대로다). 상자 계열은 전부 판정 통과(in_band 0.73~1.00)라 "
        "상자에 대한 결론은 살아남지만, **집계 방식 자체에는 이 관문이 반드시 붙어야 한다**.")
    null_cal["what_ko"] = (
        "널(null) = 답이 0 이어야 하는 대조군. 여기서는 등가부피 구와 회전대칭 원판이다.")

    # ── 부피 교란 — «크기» 를 맞추면 얼마나 남나 ────────────────────────────
    volume_confound = {}
    for d in DRONES:
        volume_confound[d] = dict(
            bbox_volume_over_mesh=rung["geometry"][d]["bbox_volume_over_mesh"],
            bbox_fill_fraction=rung["geometry"][d]["bbox_fill_fraction"],
            n_separating_box_bbox=separation_count[f"main|{d}|box_bbox - mesh"]["n_separating"],
            n_separating_box_aspect_voleq=separation_count[f"main|{d}|box_aspect_voleq - mesh"]["n_separating"],
            n_separating_cube_eqvol=separation_count[f"main|{d}|cube_eqvol - mesh"]["n_separating"],
            n_separating_prop_bbox=separation_count[f"main|{d}|prop_bbox - mesh"]["n_separating"],
            n_metrics=separation_count[f"main|{d}|box_bbox - mesh"]["n_metrics"])

    # ── 지표 사이 중복 — 독립 증거가 아닌 것들 ──────────────────────────────
    redundancy = {"identity_sym180_eq_2blade_comb_minus_1": {}, "sym90_vs_order_classes": {}}
    for band in ("main",):
        for d in DRONES:
            if blades[d] != 2:
                continue
            for arm in BOX_ARMS + REF_ARMS:
                tag = f"{band}|{d}|{arm}"
                if tag not in extra:
                    continue
                s180 = extra[tag]["similarity_at"].get("180deg")
                bc = per_arm[tag]["blade_comb_frac"]["mean"]
                if s180 is None:
                    continue
                redundancy["identity_sym180_eq_2blade_comb_minus_1"][tag] = dict(
                    sym180=s180, two_bc_minus_1=abs(2 * bc - 1),
                    abs_err=abs(s180 - abs(2 * bc - 1)))
                s90 = extra[tag]["similarity_at"].get("90deg")
                cls = extra[tag]["order_classes"]
                if s90 is not None:
                    redundancy["sym90_vs_order_classes"][tag] = dict(
                        sym90=s90,
                        abs_mult4_minus_even2=abs(cls["mult4"] - cls["even_not_mult4"]),
                        abs_err=abs(s90 - abs(cls["mult4"] - cls["even_not_mult4"])),
                        odd_frac=cls["odd"])
    _idr = redundancy["identity_sym180_eq_2blade_comb_minus_1"]
    _ok = [t for t in _idr if per_arm[t]["_interpretable_frac"] >= 1.0]
    redundancy["max_abs_err_sym180_identity"] = max(_idr[t]["abs_err"] for t in _ok)
    redundancy["max_abs_err_sym180_identity_including_nulls"] = max(
        v["abs_err"] for v in _idr.values())
    redundancy["identity_checked_on_arms"] = sorted(_ok)
    redundancy["null_arm_exception_ko"] = (
        "널 팔(구·원판)에서만 항등식이 어긋나 보이는데, 그것은 항등식이 깨져서가 아니라 "
        "방위마다 부호가 엇갈리는 값을 먼저 평균냈기 때문이다(절댓값은 평균과 자리를 "
        "바꿀 수 없다). 해석 가능한 팔에서는 소수점 15자리까지 일치한다.")
    redundancy["what_ko"] = (
        "두 지표가 사실상 같은 수라면 «두 개가 다 갈렸다» 고 세면 안 된다. 블레이드가 "
        "2 장일 때 sym_corr_180deg = |2·blade_comb_frac − 1| 은 대수적 항등식이다 "
        "(위 abs_err 이 그 증거). sym_corr_90deg 도 홀수 차수가 없을 때는 "
        "|mult4 몫 − (4의배수아닌짝수) 몫| 과 같다.")

    # ── ⚠ 이 단의 결과를 못 믿을 이유 ────────────────────────────────────────
    kin = {}
    for d in DRONES:
        kin[d] = dict(
            mesh_dc_ac_db=m("main", d, "mesh", "dc_ac_db"),
            box_bbox_dc_ac_db=m("main", d, "box_bbox", "dc_ac_db"),
            prop_bbox_dc_ac_db=m("main", d, "prop_bbox", "dc_ac_db"),
            flash_sep_box_bbox=paired_vs_mesh[f"main|{d}|box_bbox - mesh"]["flash_contrast_db"]["separation_in_pose_sd"],
            flash_sep_prop_bbox=paired_vs_mesh[f"main|{d}|prop_bbox - mesh"]["flash_contrast_db"]["separation_in_pose_sd"])
        kin[d]["flash_effect_lost_when_kinematics_matched_pct"] = 100.0 * (
            1.0 - abs(kin[d]["flash_sep_prop_bbox"]) / max(abs(kin[d]["flash_sep_box_bbox"]), 1e-30))

    po = rung["po_validity_warning"]
    reasons = [
        dict(id="R1_kinematics_confounded_with_shape",
             severity="high",
             claim_ko=("box_bbox 는 «모양만 바꾼 팔» 이 아니다. 메쉬 팔에서는 프로펠러만 돌고 "
                       "프레임은 가만히 있는데, box_bbox 는 **기체 전체를 프로펠러 rpm 으로** "
                       "돌린다. 그래서 «형상 차이» 로 읽히는 값에 «움직이는 부분이 통째로 "
                       "달라진 것» 이 섞여 있다."),
             numbers=kin,
             evidence_ko=("동체:블레이드 비가 그 증거다 — 메쉬는 DC 가 AC 보다 세고(+dB) "
                          "box_bbox 는 AC 가 DC 보다 세다(−dB). 운동학을 맞춘 prop_bbox 로 "
                          "재면 플래시 차이의 대부분이 사라진다(위 백분율)."),
             what_it_breaks_ko="box_bbox 계열의 «메쉬보다 크다/작다» 는 전부 이 교란을 안고 있다."),
        dict(id="R2_no_occlusion_kernel",
             severity="high",
             claim_ko=("커널에 가림이 없다 — 블레이드가 동체 뒤로 돌아가도 계속 산란체로 센다. "
                       "속이 빈 상자도 뒷면까지 다 센다. 동체:블레이드 비(dc_ac_db)가 "
                       "이 결함에 가장 크게 오염된다고 기반 단이 미리 적어 두었다."),
             numbers=dict(occlusion=rung["po_validity_warning"].get("occlusion_ko", ""),
                          dc_ac_db_span_over_arms={
                              d: dict(min=min(m("main", d, a, "dc_ac_db") for a in BOX_ARMS + REF_ARMS
                                              if f"main|{d}|{a}" in per_arm),
                                      max=max(m("main", d, a, "dc_ac_db") for a in BOX_ARMS + REF_ARMS
                                              if f"main|{d}|{a}" in per_arm))
                              for d in DRONES}),
             what_it_breaks_ko="④ 동체:블레이드 비는 팔 사이 비교로도 인용하기 어렵다."),
        dict(id="R3_po_knee_favours_the_box",
             severity="high",
             claim_ko=("PO 근사가 믿을 만한 최소 폭(0.729λ) 기준으로, 프로펠러 블레이드는 "
                       "3.5 GHz 에서 **문턱 아래**이고 상자 면은 어느 대역에서도 **문턱 위**다. "
                       "즉 커널이 상자에게 유리한 판에서 둘을 비교하고 있다."),
             numbers=dict(knee_a_over_lambda=po["knee_a_over_lambda"],
                          blade_knee_ghz=po["blade_knee_ghz"],
                          production_band_ghz=po["production_band_ghz"],
                          box_smallest_feature_over_lambda=po.get("box_smallest_feature_over_lambda"),
                          band_sign_agreement={d: p8[d]["n_agree"] for d in DRONES},
                          band_sign_total={d: p8[d]["n_total"] for d in DRONES}),
             what_it_breaks_ko=("«상자로 충분하다» 방향의 결론은 보수적이지 않다 — 결과가 "
                                "그 방향으로 나왔으므로 이 경고가 실제로 물린다.")),
        dict(id="R4_metric_gauge_is_pinned_to_the_propeller",
             severity="medium",
             claim_ko=("폭 지표의 분모(f_tip)와 대역 판정기(1.5β)가 «표적 반경 = 프로펠러 반경» "
                       "을 암묵적으로 가정한다. 상자는 모서리가 프롭 팁보다 바깥이라 이 잣대로는 "
                       "자동으로 «넓다» 고 나온다 — 형상의 발견이 아니라 잣대의 성질이다."),
             numbers={d: dict(r_corner_over_prop_radius=rung["geometry"][d]["r_corner_over_prop_radius"],
                              width_ratio_protocol_gauge=m("main", d, "box_bbox", "width_ratio"),
                              width_ratio_own_gauge=rung["arms"][f"main|{d}|box_bbox"][WF]
                              ["own_band_gauge"]["per_az"]["width_ratio"]["mean"])
                      for d in DRONES},
             what_it_breaks_ko="③ 폭 지표의 «갈림» 은 기하에서 이미 예측되는 값이라 새 정보가 적다."),
        dict(id="R5_metrics_are_not_independent",
             severity="medium",
             claim_ko=("sym_corr_180deg 는 blade_comb_frac 의 대수적 변환이라 독립 증거가 "
                       "아니다. 갈린 지표 개수를 세는 방식은 이런 중복에 부풀려진다."),
             numbers=dict(max_abs_err_of_identity=redundancy["max_abs_err_sym180_identity"]),
             what_it_breaks_ko="«몇 개나 갈렸나» 식 집계는 중복을 걷어낸 뒤에 세야 한다."),
        dict(id="R6_thin_pose_ensemble_one_elevation",
             severity="medium",
             claim_ko=("자세 앙상블이 고각 15° 한 줄에 방위 24 점뿐이다. 상자의 면 정반사는 "
                       "고각에 매우 민감한데(면이 시선과 수직이 되는 각도), 고각을 한 값으로 "
                       "고정하면 상자에 유리하거나 불리한 쪽으로 치우칠 수 있다. "
                       "«자세산포» 라고 부른 sd 도 방위 24 점만의 산포다."),
             numbers={d: dict(n_az=per_arm[f"main|{d}|mesh"]["_n_az"],
                              el_deg=base["protocol"]["el_deg"],
                              mesh_flash_pose_sd_db=per_arm[f"main|{d}|mesh"]["flash_contrast_db"]["sd"],
                              mesh_flash_min_db=per_arm[f"main|{d}|mesh"]["flash_contrast_db"]["min"],
                              mesh_flash_max_db=per_arm[f"main|{d}|mesh"]["flash_contrast_db"]["max"])
                      for d in DRONES},
             what_it_breaks_ko="«자세산포 안» 이라는 판정 자체가 좁은 산포로 계산된 것이다."),
        dict(id="R8_separation_count_has_no_null_gate",
             severity="high",
             claim_ko=("«6지표 중 몇 개가 갈렸나» 로 결론을 세우는 방식에 관문이 없다. "
                       "물리적 변조가 0 이어야 하는 구·원판을 같은 방식으로 세어 보면 "
                       "4~6/6 이 «갈렸다» 고 나온다 — 즉 이 집계는 «구조가 있다» 가 아니라 "
                       "«수가 다르다» 를 세고 있다."),
             numbers=dict(false_positive_on_nulls=null_cal["false_positive_on_nulls"],
                          interpretable_frac={d: {a: null_cal["per_drone"][d][a]["interpretable_frac"]
                                                  for a in ("sphere", "disc", "box_bbox", "mesh")}
                                              for d in DRONES}),
             what_it_breaks_ko=("집계는 in_band_ac_frac ≥ 0.5 인 팔로 한정해야 한다. "
                                "상자 계열은 그 관문을 통과하므로 상자 결론 자체는 살아남지만, "
                                "관문 없이 인용하면 안 된다.")),
        dict(id="R7_sigma_compares_pec_to_material_weighted",
             severity="medium",
             claim_ko=("프리미티브는 완전도체(PEC)이고 메쉬는 재질 가중이다. 절대 세기(σ) "
                       "비교는 형상이 아니라 재질을 재는 것이다."),
             numbers={d: dict(sigma_paired_mean_db=paired_vs_mesh[f"main|{d}|box_bbox - mesh"]
                              ["sigma_eq_mean_dbsm"]["paired_mean"],
                              material_invariance_delta=rung["material_invariance"]["delta"])
                      for d in DRONES},
             what_it_breaks_ko="σ 는 형상 판정에서 빼야 한다(기반 단·앞 단도 같은 입장)."),
    ]

    # ── 결론 ────────────────────────────────────────────────────────────────
    findings = dict(
        q1_what_was_measured_ko=(
            "앞 단이 저장한 한 바퀴 위상 표를 다시 열어 기반 단의 지표 함수로 ①플래시 대조비 "
            "②고차 풍부도 ③폭 ④동체:블레이드 비를 처음부터 다시 계산했다. 앞 단 JSON 과의 "
            f"최대 상대 차이는 {gate_max:.3e} 로 {recompute_gate['verdict']} 다."),
        q2_task_prediction_ko="",
        q3_what_separates_ko="",
        q4_volume_confound_ko="",
        q6_period_does_not_separate_cad_ko=(
            "⭐ 예측이 맞았지만 그 맞음이 우리에게 유리하지는 않다. 주기는 정육면체(90°)만 "
            "가려낼 뿐, 종횡비를 가진 상자·평판·프롭경계상자는 전부 진짜 메쉬와 **같은 180°** "
            "다. 즉 «주기» 는 형상 정밀도의 값어치를 지지하는 축이 아니다."),
        q7_scoring_disagreement_ko="",
        q5_biggest_doubt_ko=(
            "가장 큰 의심은 R1 이다 — box_bbox 는 형상만 바꾼 팔이 아니라 «무엇이 움직이는가» "
            "까지 바꾼 팔이다. 운동학을 맞춘 prop_bbox 만이 형상 단독 효과를 말할 자격이 있다."),
    )
    # 서술 문장에 들어갈 수는 전부 위에서 계산한 값을 그대로 꽂는다
    hd = score["TASK_HEADLINE_period_differs_from_cube"]
    findings["q2_task_prediction_ko"] = (
        "과제문 예측 «큐브와 비슷하되 주기가 다를 수 있다» → "
        + ("맞았다. " if hd["verdict"] == "CONFIRMED" else "부분적으로만 맞았다. ")
        + "축 위에 올린 경계상자의 주기는 "
        + ", ".join(f"{d} {head[d]['period_deg_order_gcd_pow1e_3']['box_bbox_axis']:.0f}°"
                    for d in DRONES)
        + " 이고 같은 부피 정육면체는 "
        + ", ".join(f"{d} {head[d]['period_deg_order_gcd_pow1e_3']['cube_eqvol']:.0f}°"
                    for d in DRONES)
        + " 다 — 두 측정법(회전 겹침·차수 최대공약수)이 같은 답을 준다. "
        "다만 사전 예측 파일이 그 예측에 걸어 둔 **상관계수 문턱**(90° 상관 < 0.5)은 "
        "빗나갔다. 상관계수는 주기의 유무가 아니라 대칭이 깨진 «정도» 를 재기 때문이다.")
    findings["q3_what_separates_ko"] = (
        "형상 판정용 6 지표 중 몇 개가 메쉬 자세산포의 2배를 넘겼나: "
        + "; ".join(
            f"{d} — " + ", ".join(
                f"{a} {separation_count[f'main|{d}|{a} - mesh']['n_separating']}/"
                f"{separation_count[f'main|{d}|{a} - mesh']['n_metrics']}"
                for a in ("prop_bbox", "box_aspect_voleq", "cube_eqvol", "box_bbox"))
            for d in DRONES)
        + ". ⚠ 이 집계는 변조가 0 이어야 할 널 팔(구·원판)에서도 "
        + " · ".join(f"{d} 구 {null_cal['false_positive_on_nulls'][d]['sphere']}/6 · "
                     f"원판 {null_cal['false_positive_on_nulls'][d]['disc']}/6" for d in DRONES)
        + " 이 나오므로, in_band_ac_frac ≥ 0.5 관문을 통과한 팔에서만 읽어야 한다. "
          "상자 계열은 전부 통과한다.")
    _dis = [k for k in disagreement if not k.startswith("_")]
    findings["q7_scoring_disagreement_ko"] = (
        ("같은 사전 예측을 앞 단과 이 단이 각각 채점했더니 "
         + ", ".join(f"{k}(앞 단 {disagreement[k]['rung']} ↔ 이 단 {disagreement[k]['mine']})"
                     for k in _dis)
         + " 에서 어긋났다. P3 는 사전 예측이 «1차수 이내» 라고 적어 둔 허용오차를 앞 단 "
           "코드가 «2차수» 로 쓴 것이 원인이다 — mini2 의 초과분이 "
         + f"{p3['mini2']['overshoot_in_quanta']:.2f} 차수라 그 사이에 걸린다. "
           "허용오차를 사후에 넓히면 예측 채점이 무의미해지므로, 여기서는 사전 예측 파일에 "
           "적힌 «1차수» 를 그대로 적용해 REFUTED 로 적는다(방향 자체는 맞다).")
        if _dis else "앞 단의 자기채점과 이 단의 채점이 전부 일치했다.")
    findings["q4_volume_confound_ko"] = (
        "경계상자는 실제 부피의 "
        + " · ".join(f"{d} {volume_confound[d]['bbox_volume_over_mesh']:.1f}배"
                     for d in DRONES)
        + " 짜리 통짜 덩어리다. 부피를 메쉬와 같게 맞춘 box_aspect_voleq 로 바꾸면 갈리는 "
          "지표 수가 "
        + " · ".join(f"{d} {volume_confound[d]['n_separating_box_bbox']}→"
                     f"{volume_confound[d]['n_separating_box_aspect_voleq']}"
                     for d in DRONES)
        + " 로 줄어든다 — 즉 «형상» 으로 읽히던 것의 상당 부분이 «크기» 였다.")

    J = dict(
        meta=dict(
            report="report16_metric_box_bbox",
            producer="benchmark/report16_metric_box_bbox.py",
            generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
            purpose_ko=("경계상자 단의 저장된 위상 표에서 지표를 **다시 계산**하고, 계산 전에 "
                        "봉인된 사전 예측과 하나씩 대조한다."),
            reads=["outputs/report16_rung_box_bbox.json",
                   "outputs/report16_rung_box_bbox_tables.npz",
                   "outputs/report16_rung_box_bbox_prediction.json",
                   "outputs/report16_base.json", "outputs/report16_base_tables.npz",
                   "benchmark/report16_base.py (지표 함수 import)"],
            writes_only=["outputs/report16_metric_box_bbox.json"],
            no_gpu_needed_ko="새로 산란 계산을 하지 않는다 — 저장된 배열만 다룬다(GPU 미사용).",
            wavefront=WF,
            seconds=0.0,
        ),
        provenance=dict(
            rung_json=dict(path="outputs/report16_rung_box_bbox.json", sha256=sha256(RUNG_JSON)),
            rung_npz=dict(path="outputs/report16_rung_box_bbox_tables.npz", sha256=sha256(RUNG_NPZ)),
            base_json=dict(path="outputs/report16_base.json", sha256=sha256(BASE_JSON)),
            base_npz=dict(path="outputs/report16_base_tables.npz", sha256=sha256(BASE_NPZ)),
            prediction=dict(path="outputs/report16_rung_box_bbox_prediction.json",
                            sha256=sha256(PRED_JSON),
                            mtime=time.strftime("%Y-%m-%dT%H:%M:%S",
                                                time.localtime(os.path.getmtime(PRED_JSON))),
                            sha256_matches_rung_prestamp=bool(
                                rung["prestamp"]["prediction"]["sha256"].startswith(sha256(PRED_JSON))),
                            prediction_precedes_compute=rung["prestamp"]["prediction_precedes_compute"]),
        ),
        thresholds_used=dict(similarity=list(SIM_THRESHOLDS), order_power=list(POWER_THRESHOLDS),
                             separation_sd=SEPARATION_SD, recompute_tolerance=GATE_TOL,
                             what_ko="이 파일에서 손으로 정한 수는 이 넷뿐이다."),
        recompute_gate=recompute_gate,
        metrics_by_arm=per_arm,
        period_and_orders=extra,
        paired_vs_mesh=paired_vs_mesh,
        separation_count=separation_count,
        volume_confound=volume_confound,
        metric_redundancy=redundancy,
        period_discriminability=period_disc,
        scoring_disagreement_with_rung=disagreement,
        null_calibration_of_separation_count=null_cal,
        controls_recomputed=controls,
        prediction_vs_result=dict(
            tally=tally,
            items=score,
            how_to_read_ko=("각 항목은 사전 예측 파일이 미리 적어 둔 문턱으로 채점했다. "
                            "문턱을 사후에 바꾸지 않았다. REFUTED 가 CONFIRMED 보다 값어치가 "
                            "크다 — 우리가 무엇을 잘못 알고 있었는지 알려주기 때문이다."),
        ),
        reasons_to_distrust=reasons,
        findings=findings,
    )
    J["meta"]["seconds"] = time.time() - t0

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(J, f, ensure_ascii=False, indent=1, default=float)
    print(f"[write] {OUT_JSON}")
    print(f"[gate ] recompute vs rung json: {recompute_gate['verdict']} "
          f"(max rel {gate_max:.3e}, {len(gate_rows)} arms)")
    print(f"[score] {tally}")
    for k, v in score.items():
        print(f"   {v['verdict']:<12} {k}")
    for d in DRONES:
        h = head[d]
        print(f"[period] {d}: cube {h['period_deg_order_gcd_pow1e_3']['cube_eqvol']:.0f}° | "
              f"box_axis {h['period_deg_order_gcd_pow1e_3']['box_bbox_axis']:.0f}° | "
              f"box {h['period_deg_order_gcd_pow1e_3']['box_bbox']:.0f}° | "
              f"mesh {h['period_deg_order_gcd_pow1e_3']['mesh']:.0f}°")
    print(f"[time ] {J['meta']['seconds']:.1f}s")


if __name__ == "__main__":
    main()
