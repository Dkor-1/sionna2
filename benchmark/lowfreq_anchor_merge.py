# -*- coding: utf-8 -*-
"""
lowfreq_anchor_merge.py — 네 조각(sphere·plate·mom·slope)을 하나의 판정으로 합치고 그린다
================================================================================
판정 규칙은 **미리 등록**한다(사후에 문턱을 옮기지 않기 위해). 드론 라운드
(`outputs/lowfreq_grid.json` verdict_rule)와 같은 형식이다.

  ① sphere_lowka_improves_with_grid
       저 ka(≤3) 에서 평균 |커널 − 정확 Mie| 가
         λ/12 → 절대 최소격자 로 갈 때 **≥1.0 dB 이고 ≥30% 줄면** True (= 표본화였다)
         **<0.5 dB 이면** False (= PO 자체다).  그 사이는 MIXED 로 적고 False 로 보고한다.
  ② thin_plate_converges
       모든 폭에서 가장 촘촘한 두 계단의 |커널 − PO 닫힌형| 이 ≤0.15 dB 이고,
       계단을 조일수록 그 포락선이 줄면 True.
  ③ consistent_with_drone
       ①이 False(드론 판정 B와 같은 방향) · ②가 True(격자는 범인이 아니다) ·
       특징/λ ≲ 0.3 에서 PO−참값 간극이 폭발(드론의 blade/λ=0.2712 전이와 같은 자리) ·
       PO 의 저대역 dB/GHz 기울기가 참값보다 가파름(드론 증상과 같은 부호) — **넷 다** 맞을 때 True.

산출: outputs/lowfreq_anchor.json, outputs/figs/lowfreq_anchor.png
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (os.path.join(_ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

C0 = 299792458.0
PART = os.path.join(_ROOT, "outputs", "partial", "lowfreq_anchor")
OUT_JSON = os.path.join(_ROOT, "outputs", "lowfreq_anchor.json")
OUT_FIG = os.path.join(_ROOT, "outputs", "figs", "lowfreq_anchor.png")

LOWKA_MAX = 3.0                    # '저 ka' 의 정의 (PO−Mie 간극이 dB 급인 구간)
RULE_IMPROVE_DB = 1.0
RULE_IMPROVE_FRAC = 0.30
RULE_NOMOVE_DB = 0.5
RULE_PLATE_TOL_DB = 0.15

#  드론 쪽 관측 (outputs/lowfreq_grid.json) — 일치 검사의 상대편
DRONE = dict(
    source="outputs/lowfreq_grid.json",
    verdict="B_PO_LIMIT",
    ladder_total_spread_at_1p8_db=0.0837,       # 6 mm → 0.375 mm 16배 조이는 동안의 총 이동
    shift_conv_minus_lam12_db_at_1p8=0.857,
    shift_conv_minus_lam16_db_at_1p8=-0.3212,
    a_lowband_lam16=1.5634, a_lowband_converged=1.6319,
    a_highband_lam16=0.1986, a_highband_converged=0.2020,
    das_anchor_a=0.21,
    steep_ends_at_blade_over_lambda=0.2712,     # 국소 기울기가 0.5 dB/GHz 아래로 내려가는 곳
    feature_mm_at_1p8ghz=dict(prop=13.78, arm_tip=30.0, arm_root=45.0, body=81.51),
    lam_mm_at_1p8ghz=166.5514,
)


def _load(name):
    p = os.path.join(PART, f"{name}.json")
    if not os.path.exists(p):
        return None
    with open(p) as f:
        return json.load(f)


def _po_ptd_strip_norm(a, k):
    """정면입사 얇은 띠의 **PO+1차 PTD(Ufimtsev)** σ_2D.

    θ=0 에서 두 모서리의 프린지 계수는 극한 f¹=g¹=−1/2 이므로
        W_soft = a − j/k ,  W_hard = a + j/k  →  |W|² = a² + 1/k² (두 편파 **동일**)
    즉 1 차 PTD 는 정면입사에서 편파를 **가르지 못한다**. 참값(MoM)은 갈라진다."""
    return k * (a ** 2 + 1.0 / k ** 2)


def _fit(x, y, lo, hi):
    x, y = np.asarray(x, float), np.asarray(y, float)
    m = (x >= lo - 1e-9) & (x <= hi + 1e-9)
    if m.sum() < 2:
        return None
    a, b = np.polyfit(x[m], y[m], 1)
    return float(a)


# =========================================================================== #
def _null_guarded(pl, deg=3.0):
    """경사입사 행에서 **PO 싱크 널 근처를 뺀다**.

    ⚠ 왜 필요한가: PO 닫힌형은 sinθ = nλ/(2a) 에서 정확히 0 이라, 그 각도의 dB 비는
      물리가 아니라 0 나누기다(실측: a=1λ·θ=30° 에서 |−PO| 이 71 dB 로 튄다).
      `ptd_plate_validation.py` 도 같은 이유로 널 가드를 둔다."""
    keep = []
    for o in pl.get("oblique", []):
        a_lam, th = o["a_lam"], o["theta_deg"]
        nulls = [np.degrees(np.arcsin(n / (2 * a_lam)))
                 for n in range(1, int(2 * a_lam) + 1) if n / (2 * a_lam) <= 1.0]
        o = dict(o, near_null=bool(nulls and min(abs(th - x) for x in nulls) < deg),
                 null_distance_deg=(float(min(abs(th - x) for x in nulls)) if nulls else None))
        keep.append(o)
    return keep


def analyse():
    sph, pl, mom, slp = _load("sphere"), _load("plate"), _load("mom"), _load("slope")
    ptd, mf, jt = _load("ptd"), _load("momfine"), _load("jitter")
    missing = [n for n, v in (("sphere", sph), ("plate", pl), ("mom", mom), ("slope", slp)) if v is None]
    if missing:
        raise SystemExit(f"조각이 없다: {missing} — 먼저 해당 모드를 실행할 것")

    out = dict(_meta=dict(
        generated=time.strftime("%Y-%m-%d %H:%M:%S"),
        purpose=("드론에는 참값이 없다. 참값이 있는 두 물체(정확 Mie 가 있는 PEC 구, "
                 "PO 닫힌형과 2D MoM 정확해가 있는 얇은 띠)로 저주파 격차의 원인을 "
                 "표본화(A) 와 PO 근본한계(B) 로 다시 가른다."),
        engine="SBR+PO (Mitsuba first-hit + PO 면적분), rcs_sbr_batch, jitter=3, penetrate=False, |Γ|=1",
        references=("PEC 구: 정확 Mie 급수해 + 해석적 PO 닫힌형(benchmark/mie_pec_sphere.py) · "
                    "얇은 띠: PO 닫힌형 4πA²/λ²(정면입사에서 PO 의 **정확한** 답) + "
                    "2D EFIE MoM(benchmark/mom2d_reference.py, 근사 없음)"),
        decomposition="(커널 − 참값) = (커널 − 해석 PO) + (해석 PO − 참값)",
        gpu=dict(sphere=sph.get("gpu"), plate=pl.get("gpu")),
        cost_s=float(sum((p or {}).get("runtime_s", 0.0)
                         for p in (sph, pl, mom, slp, ptd, mf, jt))),
        parts={k: os.path.join("outputs/partial/lowfreq_anchor", f"{k}.json")
               for k in ("sphere", "plate", "mom", "slope", "ptd", "momfine", "jitter")},
        producers=dict(sphere="benchmark/lowfreq_anchor.py sphere",
                       plate="benchmark/lowfreq_anchor.py plate",
                       mom="benchmark/lowfreq_anchor.py mom",
                       slope="benchmark/lowfreq_anchor_slope.py",
                       momfine="benchmark/lowfreq_anchor_momfine.py",
                       ptd="benchmark/lowfreq_anchor_ptd.py",
                       jitter="benchmark/lowfreq_anchor_jitter.py",
                       merge="benchmark/lowfreq_anchor_merge.py")))

    # ── ① 구 ────────────────────────────────────────────────────────────── #
    rows = sph["rows"]
    kas = sorted({r["ka"] for r in rows})
    per_ka = {}
    for ka in kas:
        rr = [r for r in rows if r["ka"] == ka]
        lam12 = min((r for r in rr if r["kind"] == "rel" and abs(r["lam_over_d"] - 12) < 1e-6),
                    key=lambda r: r["d_m"])
        fine = min((r for r in rr if r["kind"] == "abs"), key=lambda r: r["d_m"])
        coarse_abs = max((r for r in rr if r["kind"] == "abs"), key=lambda r: r["d_m"])
        per_ka[f"{ka:g}"] = dict(
            ka=ka, f_ghz=rr[0]["fc_hz"] / 1e9, lam_mm=rr[0]["lam_m"] * 1e3,
            po_minus_mie_db=rr[0]["po_minus_mie_db"],
            lam12=dict(d_mm=lam12["d_mm"], rays_per_az=lam12["rays_per_az"],
                       sigma_dbsm=lam12["sigma_dbsm"], vs_po_db=lam12["vs_po_db"],
                       vs_mie_db=lam12["vs_mie_db"]),
            finest=dict(d_mm=fine["d_mm"], d_over_lam=fine["d_over_lam"],
                        rays_per_az=fine["rays_per_az"], sigma_dbsm=fine["sigma_dbsm"],
                        vs_po_db=fine["vs_po_db"], vs_mie_db=fine["vs_mie_db"]),
            grid_refine_factor=float(lam12["d_m"] / fine["d_m"]),
            ray_count_factor=float(fine["rays_per_az"] / max(1, lam12["rays_per_az"])),
            improvement_vs_mie_db=float(abs(lam12["vs_mie_db"]) - abs(fine["vs_mie_db"])),
            total_ladder_spread_db=float(max(r["sigma_dbsm"] for r in rr if r["kind"] == "abs")
                                         - min(r["sigma_dbsm"] for r in rr if r["kind"] == "abs")),
            abs_ladder=[dict(d_mm=r["d_mm"], sigma_dbsm=r["sigma_dbsm"],
                             vs_po_db=r["vs_po_db"], vs_mie_db=r["vs_mie_db"])
                        for r in sorted([r for r in rr if r["kind"] == "abs"],
                                        key=lambda r: -r["d_m"])],
            coarsest_abs_d_mm=coarse_abs["d_mm"])
    low = [v for v in per_ka.values() if v["ka"] <= LOWKA_MAX]
    imp = float(np.mean([v["improvement_vs_mie_db"] for v in low]))
    base = float(np.mean([abs(v["lam12"]["vs_mie_db"]) for v in low]))
    frac = imp / base if base > 0 else 0.0
    if imp >= RULE_IMPROVE_DB and frac >= RULE_IMPROVE_FRAC:
        sph_verdict, sph_improves = "A_SAMPLING", True
    elif imp < RULE_NOMOVE_DB:
        sph_verdict, sph_improves = "B_PO_LIMIT", False
    else:
        sph_verdict, sph_improves = "MIXED", False

    out["sphere"] = dict(
        radius_m=sph["radius_m"], mesh=sph["mesh"], incidence=sph["incidence"],
        jitter=sph["jitter"], per_ka=per_ka, verdict=sph_verdict,
        lowka_definition=f"ka <= {LOWKA_MAX}",
        lowka_mean_abs_err_vs_mie_at_lam12_db=base,
        lowka_mean_abs_err_vs_mie_at_finest_db=float(
            np.mean([abs(v["finest"]["vs_mie_db"]) for v in low])),
        lowka_mean_improvement_db=imp, lowka_improvement_fraction=frac,
        lowka_mean_abs_err_vs_analytic_po_at_finest_db=float(
            np.mean([abs(v["finest"]["vs_po_db"]) for v in low])),
        max_abs_err_vs_analytic_po_all_ka_at_finest_db=float(
            max(abs(v["finest"]["vs_po_db"]) for v in per_ka.values())),
        #  ⭐ **양성 대조군** — 이 진단이 무딘 게 아니라는 증거.
        #  같은 절대격자 사다리가 고 ka 에서는 σ 를 dB 단위로 움직인다(거기서는 d/λ 가 커서
        #  진짜로 덜 표본화되기 때문). 저 ka 에서 안 움직이는 것은 도구가 둔해서가 아니다.
        abs_ladder_spread_db_by_ka={k: v["total_ladder_spread_db"] for k, v in per_ka.items()},
        positive_control=dict(
            lowka_spread_db=float(np.mean([v["total_ladder_spread_db"] for v in low])),
            highka_spread_db=float(np.mean([v["total_ladder_spread_db"]
                                            for v in per_ka.values() if v["ka"] >= 10])),
            note=("절대격자 사다리(8 mm → 0.25 mm)가 만드는 σ 이동. 저 ka 에서는 사실상 0 이고 "
                  "고 ka 에서는 dB 급이다 — 같은 사다리, 같은 커널. 저 ka 의 무반응은 도구의 "
                  "둔감함이 아니라 이미 수렴했다는 뜻이다.")),
        mesh_ladder=sph["mesh_ladder"],
        mesh_ladder_spread_db={
            f"{ka:g}": float(max(m["sigma_dbsm"] for m in sph["mesh_ladder"] if m["ka"] == ka)
                             - min(m["sigma_dbsm"] for m in sph["mesh_ladder"] if m["ka"] == ka))
            for ka in sorted({m["ka"] for m in sph["mesh_ladder"]})},
        reading=("커널은 격자를 조이면 **해석 PO 로** 수렴한다. 정확 Mie 와의 간극은 그 수렴 뒤에도 "
                 "그대로 남고, 그 크기는 해석 PO−Mie 간극과 같다 — 즉 저 ka 오차는 표본화가 아니라 "
                 "PO 모델 자체다."),
        precision_note=("정확히 말하면: 격자를 조여서 **살 수 있는 것은 (커널 − 해석 PO) 뿐**이고 "
                        "생산 규약(jitter=3)에서 그 항은 λ/12 에서 이미 ≤0.2 dB 다. "
                        "(해석 PO − Mie) 는 격자가 건드리지 못한다. 아래 adversarial_jitter_control "
                        "참조 — 단일격자(jitter=1)로 재면 격자 정련이 최대 1.35 dB 를 벌지만, "
                        "그 이득은 정확히 PO 바닥에서 멈춘다."))

    # ── ①-b 적대 대조군: "격자가 아니라 jitter 가 가린 것 아니냐" ───────── #
    if jt is not None:
        j_low = []
        for ka in (1.0, 2.0, 3.0):
            g12 = {r["jitter"]: r for r in jt["rows"] if r["ka"] == ka and r["grid"] == "lam/12"}
            gfi = {r["jitter"]: r for r in jt["rows"] if r["ka"] == ka and r["grid"] != "lam/12"}
            if not (g12 and gfi):
                continue
            j_low.append(dict(ka=ka,
                              j1_improvement_vs_mie_db=abs(g12[1]["vs_mie_db"]) - abs(gfi[1]["vs_mie_db"]),
                              j3_improvement_vs_mie_db=abs(g12[3]["vs_mie_db"]) - abs(gfi[3]["vs_mie_db"]),
                              j1_lam12_vs_mie_db=g12[1]["vs_mie_db"],
                              j1_fine_vs_mie_db=gfi[1]["vs_mie_db"],
                              po_minus_mie_db=g12[1]["po_minus_mie_db"]))
        j1_imp = float(np.mean([r["j1_improvement_vs_mie_db"] for r in j_low]))
        j1_base = float(np.mean([abs(r["j1_lam12_vs_mie_db"]) for r in j_low]))
        j1_frac = j1_imp / j1_base if j1_base > 0 else 0.0
        j1_verdict = ("A_SAMPLING" if (j1_imp >= RULE_IMPROVE_DB and j1_frac >= RULE_IMPROVE_FRAC)
                      else ("B_PO_LIMIT" if j1_imp < RULE_NOMOVE_DB else "MIXED"))
        out["sphere"]["adversarial_jitter_control"] = dict(
            question=("λ/12 에서 광선이 121 발뿐인데 σ 가 최고격자와 0.05 dB 밖에 안 다르다 — "
                      "수렴한 것인가, 아니면 격자위상 평균(jitter)이 격자 오차를 지운 것인가?"),
            worst_abs_vs_analytic_po_db=dict(jitter1=jt["worst_abs_j1_vs_po_db"],
                                             jitter3=jt["worst_abs_j3_vs_po_db"]),
            answer=("**jitter 가 일을 하고 있다** — λ/12 단일격자(J=1)는 해석 PO 에서 최대 "
                    f"{jt['worst_abs_j1_vs_po_db']:.2f} dB 떨어져 있고 생산 규약 J=3 은 "
                    f"{jt['worst_abs_j3_vs_po_db']:.2f} dB 다. 그래서 '격자는 아무 상관 없다' 가 "
                    "아니라 **'생산 규약이 격자 오차를 이미 처리한다'** 가 정확한 진술이다."),
            but=("⭐ 그래도 결론은 안 바뀐다. 규칙을 **J=1 로 다시 채점해도** 저 ka 평균 개선은 "
                 f"{j1_imp:.3f} dB (비율 {j1_frac:.3f}) 로 판정이 {j1_verdict} 이다 — 격자 정련이 "
                 "버는 것은 (커널−해석PO) 뿐이고, 그 이득은 정확히 PO−Mie 바닥에서 멈춘다."),
            rescored_with_jitter1=dict(lowka_mean_improvement_db=j1_imp,
                                       lowka_improvement_fraction=j1_frac,
                                       verdict=j1_verdict, rows=j_low),
            rows=jt["rows"], source="outputs/partial/lowfreq_anchor/jitter.json")

    # ── ② 얇은 판 ───────────────────────────────────────────────────────── #
    prows = pl["rows"]
    a_list = sorted({r["a_lam"] for r in prows})
    per_a = {}
    for al in a_list:
        rr = sorted([r for r in prows if r["a_lam"] == al], key=lambda r: r["d_m"])
        two_finest = rr[:2]
        per_a[f"{al:g}"] = dict(
            a_lam=al, a_mm=rr[0]["a_m"] * 1e3, po_closed_dbsm=rr[0]["po_closed_dbsm"],
            ladder=[dict(d_mm=r["d_mm"], lam_over_d=r["div"],
                         samples_across_width=r["samples_across_width"],
                         sigma_dbsm=r["sigma_dbsm"], vs_po_db=r["vs_po_db"]) for r in rr[::-1]],
            vs_po_at_lam12_db=[r["vs_po_db"] for r in rr if r["div"] == 12][0],
            vs_po_at_finest_db=rr[0]["vs_po_db"],
            max_abs_vs_po_two_finest_db=float(max(abs(r["vs_po_db"]) for r in two_finest)),
            envelope_shrinks=bool(max(abs(r["vs_po_db"]) for r in rr[:3])
                                  < max(abs(r["vs_po_db"]) for r in rr[-3:])),
            #  ⚠ 규칙 보정(등록 후, 문턱 이동 아님): a=1λ·2λ 는 **모든 계단에서 오차가 정확히 0**
            #    이라(a/d 가 항상 정수) '포락선이 줄어든다' 는 절이 공허하다 — 줄어들 것이 없다.
            #    그래서 "이미 모든 계단이 허용치 이하" 를 수렴의 동치 조건으로 함께 인정한다.
            already_within_tol_everywhere=bool(max(abs(r["vs_po_db"]) for r in rr)
                                               <= RULE_PLATE_TOL_DB),
            samples_across_at_lam12=[r["samples_across_width"] for r in rr if r["div"] == 12][0])
    plate_conv = bool(all(v["max_abs_vs_po_two_finest_db"] <= RULE_PLATE_TOL_DB
                          and (v["envelope_shrinks"] or v["already_within_tol_everywhere"])
                          for v in per_a.values()))

    #  참값(2D MoM) — 폭마다 가장 조밀한 세그먼트 판만 쓴다
    mm = {}
    for al in a_list:
        cand = [r for r in mom["rows"] if abs(r["a_lam"] - al) < 1e-9]
        if not cand:
            continue
        best = max(cand, key=lambda r: r["n_seg"])
        prev = min(cand, key=lambda r: r["n_seg"])
        k = 2 * np.pi / pl["lam_m"]
        s_ptd = _po_ptd_strip_norm(best["a_m"], k)
        mm[f"{al:g}"] = dict(
            a_lam=al, n_seg=best["n_seg"], seg_per_lam=best["seg_per_lam"],
            mom_selfcheck_shift_db=float(10 * np.log10(best["sigma2d_tm"] / prev["sigma2d_tm"])),
            po_minus_tm_db=best["po_minus_tm_db"], po_minus_te_db=best["po_minus_te_db"],
            tm_minus_te_db=float(10 * np.log10(best["sigma2d_tm"] / best["sigma2d_te"])),
            po_ptd_minus_tm_db=float(10 * np.log10(s_ptd / best["sigma2d_tm"])),
            po_ptd_minus_te_db=float(10 * np.log10(s_ptd / best["sigma2d_te"])),
            sigma3d_po_dbsm=best["sigma3d_po_dbsm"], sigma3d_tm_dbsm=best["sigma3d_tm_dbsm"],
            sigma3d_te_dbsm=best["sigma3d_te_dbsm"])
    out["thin_plate"] = dict(
        fc_hz=pl["fc_hz"], lam_mm=pl["lam_m"] * 1e3, b_lam=pl["b_lam"], jitter=pl["jitter"],
        per_width=per_a, converges=plate_conv, tol_db=RULE_PLATE_TOL_DB,
        rule_amendment=("등록 규칙의 '포락선이 줄어든다' 절은 잔차가 **있는** 경우를 상정한 것이다. "
                        "a=1λ·2λ 는 모든 계단에서 a/d 가 정수라 오차가 정확히 0 이어서 그 절이 "
                        "공허해 False 가 나왔다 — 문턱을 옮긴 것이 아니라 퇴화 사례를 "
                        "'이미 모든 계단이 허용치 이하' 로 동치 인정했다. "
                        "0.15λ·0.3λ·0.6λ 는 보정 없이도 원래 규칙을 통과한다."),
        truth_2d_mom=mm, mom_selftest=mom["selftest"],
        truth_2d_mom_fine_width_grid=(dict(
            rows=mf["rows"], knee_a_over_lam=mf["knee_a_over_lam_interp_1db"],
            knee_rule=mf["knee_rule"], source=mf["part"]) if mf is not None else None),
        oblique=_null_guarded(pl),
        oblique_summary={
            f"{al:g}": {f"lam_over_{d}": float(np.mean([abs(o["vs_po_db"]) for o in _null_guarded(pl)
                                                        if o["a_lam"] == al and o["div"] == d
                                                        and not o["near_null"]]))
                        for d in sorted({o["div"] for o in pl["oblique"]})}
            for al in a_list} if pl.get("oblique") else {},
        oblique_note=("PO 싱크 널 ±3° 는 뺐다 — 닫힌형이 정확히 0 이라 dB 비가 발산한다"
                      "(가드 없이는 a=1λ·θ=30° 에서 71 dB 로 튄다)."),
        residual_mechanism=("남는 |커널−PO| 는 **판 가장자리의 격자 양자화**다 — 광선격자가 폭을 "
                            "몇 점으로 자르느냐에 따라 덮이는 면적이 ±d/2 만큼 떨어진다. "
                            "그 증거: a=1λ·2λ 는 모든 계단에서 a/d 가 정수라 오차가 **정확히 0** 이고, "
                            "0.15λ·0.3λ·0.6λ 는 부호가 계단마다 뒤집히며 포락선만 줄어든다."),
        reading=("커널은 폭 0.15λ 인 판에서도 PO 닫힌형으로 수렴한다(격자는 범인이 아니다). "
                 "그런데 그 PO 닫힌형 자체가 참값(2D MoM)과 TM −4.0 dB · TE +7.5 dB 어긋난다 — "
                 "게다가 참값은 편파에 따라 11.5 dB 갈라지는데 우리 PO 면적분은 스칼라라 "
                 "그 갈라짐을 **원리적으로** 낼 수 없다."))

    # ── ②-b 1차 PTD 를 얹으면 닫히는가 (드론 caveat 3 을 직접 검정) ────── #
    if ptd is not None:
        pr = {}
        for al in sorted({r["a_lam"] for r in ptd["rows"]}):
            fine = min([r for r in ptd["rows"] if r["a_lam"] == al], key=lambda r: r["d_mm"])
            key = f"{al:g}"
            t = mm.get(key)
            pr[key] = dict(
                a_lam=al, div=fine["div"], d_mm=fine["d_mm"],
                kernel_po_dbsm=fine["po_dbsm"], kernel_ptd_dbsm=fine["ptd_v_dbsm"],
                target_po_dbsm=fine["target_po_dbsm"],
                target_po_ptd_dbsm=fine["target_po_ptd_dbsm"],
                kernel_po_minus_target_db=fine["kernel_po_minus_target_db"],
                kernel_ptd_minus_target_db=fine["kernel_ptd_minus_target_db"],
                v_minus_h_db=fine["v_minus_h_db"],
                po_minus_tm_db=(t["po_minus_tm_db"] if t else None),
                po_minus_te_db=(t["po_minus_te_db"] if t else None),
                po_ptd_minus_tm_db=(t["po_ptd_minus_tm_db"] if t else None),
                po_ptd_minus_te_db=(t["po_ptd_minus_te_db"] if t else None))
        out["ptd_does_not_close_it"] = dict(
            per_width=pr, max_abs_v_minus_h_db=ptd["max_abs_v_minus_h_db"],
            kernel_reproduces_analytic_ptd_max_abs_db=float(
                max(abs(v["kernel_ptd_minus_target_db"]) for v in pr.values())),
            verdict=("1 차 PTD 는 정면입사에서 **편파를 못 가른다**(커널 V−H = "
                     f"{ptd['max_abs_v_minus_h_db']:.1e} dB). 0.15λ 에서 TM 쪽 간극은 "
                     f"{abs(pr['0.15']['po_minus_tm_db']):.2f} → "
                     f"{abs(pr['0.15']['po_ptd_minus_tm_db']):.2f} dB 로 좋아지지만 TE 쪽은 "
                     f"{abs(pr['0.15']['po_minus_te_db']):.2f} → "
                     f"{abs(pr['0.15']['po_ptd_minus_te_db']):.2f} dB 로 **더 나빠진다**. "
                     "드론 caveat 3(‘프린지가 저대역 기울기를 바꿀 수 있다’)은 "
                     "‘한 편파에서만, 다른 편파를 희생하고’ 라는 조건부로만 참이다."),
            note=("해석 과녁: σ_PO+PTD = 4πb²(a²+1/k²)/λ². 커널의 ptd=True 가 이 값을 재현하는지 "
                  "함께 적는다 — 우리 구현 확인이지 물리 주장이 아니다."))

    # ── ③ 기울기 (PO 가 저대역을 가파르게 만드는가) ────────────────────── #
    sl = {}
    for tag, v in slp["by_width"].items():
        sl[tag] = dict(
            w_mm=v["w_mm"], w_over_lam_at_1p8=v["w_over_lam"][0],
            a_po=v["fits"]["po"]["1.8-6.0"]["a_db_per_ghz"],
            a_tm=v["fits"]["tm"]["1.8-6.0"]["a_db_per_ghz"],
            a_te=v["fits"]["te"]["1.8-6.0"]["a_db_per_ghz"],
            a_po_high=v["fits"]["po"]["6.0-18.2"]["a_db_per_ghz"],
            a_tm_high=v["fits"]["tm"]["6.0-18.2"]["a_db_per_ghz"],
            a_te_high=v["fits"]["te"]["6.0-18.2"]["a_db_per_ghz"],
            excess_lowband=v["slope_excess_db_per_ghz"]["1.8-6.0"],
            excess_highband=v["slope_excess_db_per_ghz"]["6.0-18.2"])
    steeper = bool(all(s["excess_lowband"]["vs_tm"] > 0 for s in sl.values())
                   and all(abs(s["excess_lowband"]["vs_tm"]) > abs(s["excess_highband"]["vs_tm"])
                           for s in sl.values()))
    #  어느 편파가 **지배 채널**인가 — 이 진술의 조건이므로 숫자로 남긴다.
    dom = {}
    for tag, v in slp["by_width"].items():
        i0 = int(np.argmin(np.abs(np.array(v["f_ghz"]) - 1.8)))
        dom[tag] = dict(f_ghz=v["f_ghz"][i0], w_over_lam=v["w_over_lam"][i0],
                        tm_minus_te_db=float(v["sigma3d_tm_dbsm"][i0] - v["sigma3d_te_dbsm"][i0]))
    out["slope_mechanism"] = dict(
        by_width=sl, mom_convergence=slp["mom_convergence"],
        b_m_fixed_for_3d=slp.get("b_m_fixed_for_3d"),
        po_lowband_slope_steeper_than_truth=steeper,
        dominant_channel_at_1p8ghz=dom,
        note=("물리적 폭을 고정하고 드론과 같은 21 주파수를 쓸었다. w/λ 가 작을수록 PO 오차가 "
              "크고 f 가 오르면 사라지므로, PO 의 σ(f) 는 참값보다 **빠르게** 올라간다. "
              "드론의 저대역 기울기 초과(1.63 vs Das 0.21 → 1.42 dB/GHz)와 같은 부호의 메커니즘이다."),
        polarisation_condition=("⚠ 이 진술은 **지배 채널(TM)** 기준이다. 얇은 띠에서 σ_TM ≫ σ_TE "
                               "이므로(위 dominant_channel_at_1p8ghz) 절대 레벨을 만드는 쪽이 TM 이고, "
                               "PO 의 저대역 기울기는 그 TM 참값보다 가파르다. 약한 TE 채널만 보면 "
                               "부호가 반대다 — 숨기지 않고 slope_excess 의 vs_te 에 그대로 적어 둔다."),
        caveat=("크기 비교는 하지 않는다 — 여기는 단일 스트립, 드론은 여러 특징이 섞인 3D 기체에 "
                "방위 360 평균이다. 같은 것은 **부호와 메커니즘**이지 숫자가 아니다. "
                "또한 이 스트립 σ 는 2D MoM 의 3D 환산이지 3D MoM 이 아니다."))

    # ── ④ 드론과의 일치 ─────────────────────────────────────────────────── #
    lam_mm = DRONE["lam_mm_at_1p8ghz"]
    feat = {k: v / lam_mm for k, v in DRONE["feature_mm_at_1p8ghz"].items()}
    #  PO−참값 간극을 **드론의 특징 치수 바로 그 자리에서** 읽는다.
    #  ⚠ '무릎 하나' 로 요약하지 않는다 — 두 편파의 간극은 서로 다른 곳에서 커지고 TE 는
    #    0.3λ 부근에서 부호를 바꾸며 지나가므로, 단일 교차점은 규칙에 민감하다.
    #    스칼라 커널은 두 편파를 모두 감당해야 하므로 통계는 **나쁜 쪽(worst-pol)** 으로 잡는다.
    gap_src = mf["rows"] if mf is not None else [
        dict(a_lam=v["a_lam"], po_minus_tm_db=v["po_minus_tm_db"],
             po_minus_te_db=v["po_minus_te_db"]) for v in mm.values()]
    worst = sorted((r["a_lam"], max(abs(r["po_minus_tm_db"]), abs(r["po_minus_te_db"])))
                   for r in gap_src)

    def _gap_at(x):
        xs = np.array([w[0] for w in worst]); ys = np.array([w[1] for w in worst])
        return float(np.interp(x, xs, ys))

    at_drone = {nm: _gap_at(x) for nm, x in sorted(feat.items(), key=lambda t: t[1])}
    gap_small = float(max(y for x, y in worst if 0.05 <= x <= 0.30))
    gap_large = float(np.mean([y for x, y in worst if x >= 1.0]))
    knee = (mf["knee_a_over_lam_interp_1db"] or mf["knee_a_over_lam_last_above_1db"]) \
        if mf is not None else None
    knee_source = ("momfine (조밀 폭 격자, worst-pol 이 1 dB 를 마지막으로 가로지르는 점)"
                   if mf is not None else "없음(momfine 미실행)")
    gap_scales_ok = bool(gap_small >= 3.0 and gap_large <= 1.0
                         and at_drone["arm_root"] >= 1.0)
    consistent = bool((not sph_improves) and plate_conv and steeper and gap_scales_ok)
    out["consistency_with_drone"] = dict(
        drone=DRONE,
        drone_feature_over_lambda_at_1p8ghz=feat,
        checks=dict(
            sphere_excludes_sampling=dict(
                ok=not sph_improves,
                detail=(f"저 ka 평균 |커널−Mie| 가 λ/12 {base:.3f} dB → 최고격자 "
                        f"{out['sphere']['lowka_mean_abs_err_vs_mie_at_finest_db']:.3f} dB "
                        f"(이동 {imp:.3f} dB). 드론 판정 B 와 같은 방향.")),
            plate_converges_to_po=dict(
                ok=plate_conv,
                detail=(f"폭 0.15λ 에서 λ/12 는 폭을 가로질러 "
                        f"{per_a[f'{a_list[0]:g}']['samples_across_at_lam12']:.2f} 점밖에 안 찍는데도 "
                        f"|커널−PO| = {abs(per_a[f'{a_list[0]:g}']['vs_po_at_lam12_db']):.3f} dB 이고, "
                        f"조이면 {abs(per_a[f'{a_list[0]:g}']['vs_po_at_finest_db']):.3f} dB 로 간다. "
                        f"드론 사다리 총 이동 {DRONE['ladder_total_spread_at_1p8_db']:.3f} dB 와 같은 크기대.")),
            gap_lives_at_drone_feature_scales=dict(
                ok=gap_scales_ok,
                worst_pol_gap_db_at_drone_features=at_drone,
                max_gap_db_for_feature_0p05_to_0p30_lam=gap_small,
                mean_gap_db_for_feature_ge_1lam=gap_large,
                one_db_crossing_a_over_lam=knee, crossing_source=knee_source,
                rule=("worst-pol |PO−참값| 이 특징 0.05~0.30λ 에서 ≥3 dB, ≥1λ 에서 ≤1 dB, "
                      "그리고 드론 팔뿌리 폭(0.270λ)에서 ≥1 dB"),
                drone_steep_ends_at=DRONE["steep_ends_at_blade_over_lambda"],
                detail=(f"드론 블레이드 폭(0.083λ)에서 {at_drone['prop']:.2f} dB, "
                        f"팔끝(0.180λ) {at_drone['arm_tip']:.2f} dB, "
                        f"팔뿌리(0.270λ) {at_drone['arm_root']:.2f} dB, "
                        f"동체(0.489λ) {at_drone['body']:.2f} dB — 간극은 드론의 **작은** 특징들이 "
                        f"사는 자리에 있고, 1λ 이상에서는 평균 {gap_large:.2f} dB 로 사라진다. "
                        f"드론에서 가파른 기울기가 끝나던 blade/λ="
                        f"{DRONE['steep_ends_at_blade_over_lambda']:.4f} 도 그 안이다.")),
            slope_sign_matches=dict(
                ok=steeper,
                lowband_excess_db_per_ghz_vs_tm={k: v["excess_lowband"]["vs_tm"]
                                                 for k, v in sl.items()},
                highband_excess_db_per_ghz_vs_tm={k: v["excess_highband"]["vs_tm"]
                                                  for k, v in sl.items()},
                drone_lowband_excess_over_das=DRONE["a_lowband_converged"] - DRONE["das_anchor_a"],
                detail=("고정 폭 스트립에서 PO 의 저대역 기울기가 지배 채널(TM) 참값보다 가파르고, "
                        "고대역에서는 그 초과가 사라진다. 드론의 a_low=1.63 ≫ a_high=0.20 이고 "
                        "Das 앵커 0.21 대비 초과가 1.42 dB/GHz 였던 것과 같은 부호·같은 대역 구조다. "
                        "⚠ 약한 TE 채널만 보면 부호가 반대다(slope_mechanism.polarisation_condition)."))),
        consistent=consistent)

    # ── 최종 반환값 ─────────────────────────────────────────────────────── #
    out["verdict"] = dict(
        sphere_lowka_improves_with_grid=bool(sph_improves),
        thin_plate_converges=bool(plate_conv),
        consistent_with_drone=bool(consistent))
    ka1 = per_ka.get("1", list(per_ka.values())[0])
    a015 = per_a.get("0.15", list(per_a.values())[0])
    m015 = mm.get("0.15", list(mm.values())[0])
    out["bottom_line"] = (
        f"참값이 있는 두 물체가 드론의 판정을 확인한다. PEC 구 ka=1 에서 광선격자를 λ/12 "
        f"({ka1['lam12']['d_mm']:.1f} mm) → {ka1['finest']['d_mm']:.3f} mm 로 "
        f"{ka1['grid_refine_factor']:.0f} 배 조이면(광선 {ka1['ray_count_factor']:.0f} 배) "
        f"커널은 해석 PO 에 {abs(ka1['finest']['vs_po_db']):.3f} dB 로 딱 붙지만, 정확 Mie 와의 "
        f"간극은 {abs(ka1['lam12']['vs_mie_db']):.3f} → {abs(ka1['finest']['vs_mie_db']):.3f} dB 로 "
        f"{ka1['improvement_vs_mie_db']:.3f} dB 밖에 안 줄고 그 값은 해석 PO−Mie 간극 "
        f"{abs(ka1['po_minus_mie_db']):.3f} dB 그 자체다 — 저 ka 오차는 **표본화가 아니라 PO** 다. "
        f"폭 0.15λ 얇은 판도 같다: 격자는 PO 닫힌형으로 수렴하는데(최고격자 "
        f"{abs(a015['vs_po_at_finest_db']):.3f} dB), 그 PO 가 2D MoM 참값과 TM "
        f"{m015['po_minus_tm_db']:+.2f} dB · TE {m015['po_minus_te_db']:+.2f} dB 어긋나고 "
        f"참값 자체가 편파로 {abs(m015['tm_minus_te_db']):.1f} dB 갈라지는데 스칼라 PO 는 그걸 "
        f"낼 수 없다. 1 차 PTD 를 얹어도 TM 은 {abs(m015['po_ptd_minus_tm_db']):.2f} dB 로 좋아지지만 "
        f"TE 는 {abs(m015['po_ptd_minus_te_db']):.2f} dB 로 더 나빠진다(정면입사에서 1 차 프린지는 "
        f"편파를 못 가른다). 그 간극은 특징/λ 의 함수다 — 드론 블레이드 폭(0.083λ)에서 "
        f"{at_drone['prop']:.1f} dB, 팔뿌리(0.270λ)에서 {at_drone['arm_root']:.1f} dB 인데 "
        f"특징이 1λ 를 넘으면 평균 {gap_large:.2f} dB 로 사라진다. 즉 드론이 저대역에서 본 것은 "
        f"기체가 λ 에 비해 **가늘어지는 것**이고, 격자로는 못 고친다.")

    out["caveats"] = [
        "⚠ 구는 매끄러워 **특징 치수가 반경 하나**뿐이다 — 팔 0.18~0.27λ · 블레이드 0.083λ · "
        "동체 0.49λ 가 한 몸에 섞인 드론과 다르다. 그래서 얇은 판을 반드시 같이 본다.",
        "⚠ 2D MoM 은 **무한히 긴 띠**의 정확해다. 우리 3D 판은 b=6λ 로 유한하므로, 시선에 "
        "나란한 두 모서리(off-cone) 기여만큼 대응이 어긋난다. σ_3D=(2b²/λ)σ_2D 는 PO 항과 "
        "on-cone 모서리에 대해 정확하다.",
        "⚠ 정면입사만 참값과 나란히 놓았다. 경사입사는 PO 닫힌형과만 비교했다(oblique 항목).",
        "⚠ 우리 PO 면적분은 **스칼라**라 편파가 없다. TM/TE 참값의 중간 어디쯤이라고 말할 근거가 "
        "없으며, 이 라운드는 그 간극을 재기만 하고 고치지 않는다.",
        "⚠ 커널 규약은 생산과 같지만(jitter=3, penetrate=False, max_bounce=1) 구·판은 볼록이라 "
        "다중반사가 원래 없다 — 이 검증은 다중반사 경로를 재지 않는다.",
        "⚠ **격자 정련이 산 것은 (커널−해석PO) 뿐이다.** 생산 규약(jitter=3)에서 그 항은 λ/12 에서 "
        "이미 ≤0.2 dB 라 '격자를 조여도 안 움직인다' 로 보인다. 단일격자(jitter=1)로 재면 정련이 "
        "최대 1.35 dB 를 벌지만 정확히 PO−Mie 바닥에서 멈추고, 규칙을 J=1 로 재채점해도 판정은 "
        "그대로다(sphere.adversarial_jitter_control). 즉 정확한 진술은 '격자는 무관하다' 가 아니라 "
        "'격자로 살 수 있는 것에 상한이 있고 그 상한이 간극보다 훨씬 작다' 이다.",
        "⚠ 기울기 실험은 단일 스트립이고 드론은 다특징 3D 기체의 방위 360 평균이다. 비교한 것은 "
        "**부호와 메커니즘**이지 dB/GHz 숫자의 크기가 아니다.",
        "⚠ 'PO 가 저대역 기울기를 가파르게 만든다' 는 **지배 채널(TM) 기준** 진술이다. 얇은 띠에서 "
        "σ_TM ≫ σ_TE 라 절대 레벨은 TM 이 만들지만, 약한 TE 채널만 보면 기울기 초과의 부호가 반대다.",
        "⚠ 기울기 스윕의 3D 환산 span 은 **고정 물리 길이**(0.999 m)다. 처음에 b=6λ 로 두었더니 "
        "σ_3D 의 주파수 의존이 통째로 상쇄돼 a_PO 가 0.0000 dB/GHz 로 나왔고, 그 판은 폐기했다"
        "(outputs/partial/lowfreq_anchor/slope.json.blam_bug.bak). 기울기 **차이**는 그 버그에 무관했다.",
        "⚠ 구의 절대격자 사다리는 모든 ka 에서 8 mm → 0.25 mm 다. 한 계단 더(0.125 mm)는 뺐다 — "
        "ka=1 에서 0.25 mm 는 이미 λ/2513 이고 |커널−해석PO| = 0.000 dB 라 배울 것이 없는데, "
        "공용 GPU 에서 Dr.Jit 이 메모리를 터뜨렸다.",
        "⚠ 메쉬 사다리는 ka=1·3 두 점에서만 돌렸다. 테셀레이션이 별도 오차축이라는 것은 "
        "여기서 배제하지 않았고, 다만 그 축의 이동폭을 mesh_ladder_spread_db 로 적어 둔다.",
        "⚠ 드론 쪽 숫자는 outputs/lowfreq_grid.json 에서 그대로 인용했다. 그 스윕 이후 "
        "Phantom 3 CAD 가 개정됐다는 경고(그 파일 geometry_revised_after_run)가 여기에도 그대로 "
        "적용된다 — 이 라운드는 드론을 다시 재지 않았다.",
    ]
    return out, sph, pl, mom, slp, ptd, mf


# =========================================================================== #
def figure(out, sph, pl, mom, slp, ptd=None, mf=None):
    """8 판 진단 그림. **그림 안의 글자는 전부 영어**(저장소 규약)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mie_pec_sphere import mie_pec_backscatter_norm, po_sphere_norm

    plt.rcParams.update({"font.size": 8.2, "axes.grid": True, "grid.alpha": 0.25,
                         "figure.facecolor": "white", "savefig.facecolor": "white",
                         "axes.axisbelow": True, "legend.framealpha": 0.9})
    CK12, CKF, CPO, CMIE = "#e07b39", "#1f6fb4", "#8a8a8a", "#111111"
    CTM, CTE = "#1f6fb4", "#c0392b"
    fig, AX = plt.subplots(2, 4, figsize=(21.0, 9.6))

    pk = out["sphere"]["per_ka"]
    ka_v = [v["ka"] for v in pk.values()]
    pir2_db = 10 * np.log10(np.pi * out["sphere"]["radius_m"] ** 2)
    kk = np.geomspace(0.85, 22.5, 900)

    # ── A: 구 정규화 σ vs ka ─────────────────────────────────────────────
    a = AX[0, 0]
    a.plot(kk, 10 * np.log10(mie_pec_backscatter_norm(kk)), color=CMIE, lw=1.7,
           label="exact Mie  (truth)", zorder=3)
    a.plot(kk, 10 * np.log10(po_sphere_norm(kk)), color=CPO, lw=1.5, ls="--",
           label="analytic PO  (kernel's target)", zorder=2)
    a.plot(ka_v, [v["lam12"]["sigma_dbsm"] - pir2_db for v in pk.values()], "o", ms=6,
           mfc="none", mec=CK12, mew=1.5, label="kernel, ray grid $\\lambda/12$", zorder=4)
    a.plot(ka_v, [v["finest"]["sigma_dbsm"] - pir2_db for v in pk.values()], "s", ms=4.5,
           color=CKF, label="kernel, finest absolute grid", zorder=5)
    a.set_xscale("log"); a.set_xlabel("$ka$"); a.set_ylabel("$\\sigma / (\\pi r^2)$   [dB]")
    a.set_title("A · PEC sphere — the kernel rides analytic PO,\nnot the truth", fontsize=9.6)
    a.set_xticks([1, 2, 3, 5, 10, 20]); a.set_xticklabels(["1", "2", "3", "5", "10", "20"])
    a.legend(fontsize=7.0, loc="lower right")

    # ── B: |오차| vs 정확 Mie ────────────────────────────────────────────
    b = AX[0, 1]
    floor = np.abs(10 * np.log10(po_sphere_norm(kk) / mie_pec_backscatter_norm(kk)))
    b.fill_between(kk, 1e-3, floor, color=CPO, alpha=0.20,
                   label="|analytic PO $-$ Mie| : the model floor")
    b.plot(kk, floor, color=CPO, lw=1.2, ls="--")
    b.plot(ka_v, [max(abs(v["lam12"]["vs_mie_db"]), 1e-3) for v in pk.values()], "o", ms=6,
           mfc="none", mec=CK12, mew=1.5, label="|kernel $-$ Mie|,  grid $\\lambda/12$")
    b.plot(ka_v, [max(abs(v["finest"]["vs_mie_db"]), 1e-3) for v in pk.values()], "s", ms=4.5,
           color=CKF, label="|kernel $-$ Mie|,  finest grid")
    b.plot(ka_v, [max(abs(v["finest"]["vs_po_db"]), 1e-3) for v in pk.values()], "^", ms=5,
           color="#2e8b57", label="|kernel $-$ analytic PO|,  finest grid")
    k1 = pk["1"]
    b.annotate(f"$ka=1$:  grid $\\times${k1['grid_refine_factor']:.0f} finer\n"
               f"({k1['ray_count_factor']:.0f}$\\times$ more rays)\n"
               f"buys {k1['improvement_vs_mie_db']:+.3f} dB",
               xy=(1.0, abs(k1["finest"]["vs_mie_db"])), xytext=(1.6, 1.6),
               fontsize=7.4, arrowprops=dict(arrowstyle="->", lw=0.9, color="#444"))
    b.set_xscale("log"); b.set_yscale("log")
    b.set_xlabel("$ka$"); b.set_ylabel("|error| vs exact Mie   [dB]")
    b.set_title("B · Refining the ray grid does not move\nthe low-$ka$ error", fontsize=9.6)
    b.set_xticks([1, 2, 3, 5, 10, 20]); b.set_xticklabels(["1", "2", "3", "5", "10", "20"])
    b.set_ylim(1e-3, 30)
    b.legend(fontsize=7.0, loc="lower left")

    # ── C: 구 절대격자 사다리 ────────────────────────────────────────────
    c = AX[0, 2]
    for i, kt in enumerate(["1", "3", "20"]):
        if kt not in pk:
            continue
        L = pk[kt]["abs_ladder"]
        dmm = [r["d_mm"] for r in L]
        col = plt.cm.viridis(0.05 + 0.42 * i)
        c.plot(dmm, [r["vs_mie_db"] for r in L], "-o", ms=4.5, color=col, lw=1.7,
               label=f"$ka$={kt} :  kernel $-$ Mie")
        c.plot(dmm, [r["vs_po_db"] for r in L], "--s", ms=3.5, color=col, lw=1.1, alpha=0.9,
               label=f"$ka$={kt} :  kernel $-$ analytic PO")
    c.axhline(0, color="k", lw=0.8)
    pc = out["sphere"]["positive_control"]
    c.text(0.03, 0.40, "positive control: the same ladder moves $\\sigma$ by\n"
                       f"{pc['highka_spread_db']:.2f} dB at high $ka$ but "
                       f"{pc['lowka_spread_db']:.3f} dB at low $ka$\n"
                       "$\\rightarrow$ the instrument is not blunt, the answer is converged",
           transform=c.transAxes, va="center", ha="left", fontsize=6.9, color="#333",
           bbox=dict(fc="white", ec="#ccc", alpha=0.92, boxstyle="round,pad=0.3"))
    c.set_xscale("log"); c.set_xlim(11.0, 0.19); c.set_ylim(-8.2, 5.6)
    c.set_xticks([8, 4, 2, 1, 0.5, 0.25])
    c.set_xticklabels(["8", "4", "2", "1", "0.5", "0.25"])
    c.xaxis.set_minor_locator(matplotlib.ticker.NullLocator())
    c.set_xlabel("ray grid spacing $d$  [mm]      (finer $\\rightarrow$)")
    c.set_ylabel("error   [dB]")
    c.set_title("C · Absolute grid ladder — PO residual $\\to 0$,\nMie residual frozen",
                fontsize=9.6)
    c.legend(fontsize=6.6, loc="upper right", ncol=1)

    # ── D: 구 메쉬 사다리 (부차축) ───────────────────────────────────────
    d = AX[0, 3]
    ml = out["sphere"]["mesh_ladder"]
    for i, ka in enumerate(sorted({m["ka"] for m in ml})):
        rr = sorted([m for m in ml if m["ka"] == ka], key=lambda m: m["seg"])
        col = plt.cm.viridis(0.05 + 0.42 * i)
        d.plot([m["facet_mm"] for m in rr], [m["vs_mie_db"] for m in rr], "-o", ms=4.5,
               color=col, lw=1.7, label=f"$ka$={ka:g} :  kernel $-$ Mie")
        d.plot([m["facet_mm"] for m in rr], [m["vs_po_db"] for m in rr], "--s", ms=3.5,
               color=col, lw=1.1, alpha=0.9, label=f"$ka$={ka:g} :  kernel $-$ analytic PO")
    d.axhline(0, color="k", lw=0.8)
    d.set_xscale("log"); d.set_xlim(17.0, 0.33); d.set_ylim(-8.2, 5.6)
    d.set_xticks([13.09, 6.55, 3.27, 1.64, 0.87, 0.44])
    d.set_xticklabels(["13.1", "6.5", "3.3", "1.6", "0.87", "0.44"])
    d.xaxis.set_minor_locator(matplotlib.ticker.NullLocator())
    d.set_xlabel("mesh facet edge  [mm]      (finer $\\rightarrow$)")
    d.set_ylabel("error   [dB]")
    d.set_title("D · Second numerical axis: tessellation\n(ray grid held at "
                f"{ml[0]['d_mm']:.2f} mm)", fontsize=9.6)
    ms_sp = out["sphere"]["mesh_ladder_spread_db"]
    d.text(0.03, 0.40, "tessellation moves $\\sigma$ by "
           + " and ".join(f"{v:.3f} dB at $ka$={k}" for k, v in sorted(ms_sp.items()))
           + "\n$\\rightarrow$ the mesh axis is not hiding the gap either",
           transform=d.transAxes, va="center", ha="left", fontsize=6.9, color="#333",
           bbox=dict(fc="white", ec="#ccc", alpha=0.92, boxstyle="round,pad=0.3"))
    d.legend(fontsize=6.6, loc="upper right")

    # ── E: 얇은 판 수렴 ──────────────────────────────────────────────────
    e = AX[1, 0]
    widths = sorted(out["thin_plate"]["per_width"].items(), key=lambda x: x[1]["a_lam"])
    for i, (kt, v) in enumerate(widths):
        L = v["ladder"]
        col = plt.cm.plasma(0.05 + 0.72 * i / max(1, len(widths) - 1))
        e.plot([r["samples_across_width"] for r in L],
               [max(abs(r["vs_po_db"]), 3e-4) for r in L], "-o", ms=4.5, color=col, lw=1.5,
               label=f"$a$ = {v['a_lam']:.2f}$\\lambda$")
    s12 = out["thin_plate"]["per_width"]["0.15"]["samples_across_at_lam12"]
    e.axvline(s12, color="#b00", lw=1.1, ls=":")
    e.text(0.42, 0.97, f"production grid $\\lambda/12$ on a $0.15\\lambda$ strip:\n"
                       f"only {s12:.1f} ray samples across the width", transform=e.transAxes,
           fontsize=7.0, color="#b00", va="top", ha="left")
    e.axhline(RULE_PLATE_TOL_DB, color="#2e8b57", lw=1.0, ls="--")
    e.text(0.98, RULE_PLATE_TOL_DB * 1.2, f"pre-registered tolerance {RULE_PLATE_TOL_DB} dB",
           transform=e.get_yaxis_transform(), fontsize=6.8, color="#2e8b57", ha="right")
    e.set_xscale("log"); e.set_yscale("log")
    e.set_xlabel("ray samples across the width   $a/d$")
    e.set_ylabel("|kernel $-$ PO closed form|   [dB]")
    e.set_title("E · Thin plate — the kernel converges to the\nPO closed form", fontsize=9.6)
    e.text(0.985, 0.03, "$a=1\\lambda,\\,2\\lambda$ sit at $0$ identically:\n"
                        "$a/d$ is an integer at every rung,\nso edge quantisation cancels",
           transform=e.transAxes, ha="right", va="bottom", fontsize=6.6, color="#555",
           bbox=dict(fc="white", ec="#ddd", alpha=0.9, boxstyle="round,pad=0.25"))
    e.legend(fontsize=7.0, loc="lower left", ncol=2)

    # ── F: 모델 간극 vs 특징/λ  (드론과 겹쳐 보는 판) ────────────────────
    f = AX[1, 1]
    kk2 = np.geomspace(0.24, 4.2, 900)                      # sphere feature = 2r/λ = ka/π
    f.plot(kk2, np.abs(10 * np.log10(po_sphere_norm(kk2 * np.pi)
                                     / mie_pec_backscatter_norm(kk2 * np.pi))),
           color="#111", lw=0.9, alpha=0.75,
           label="sphere : |PO $-$ Mie|   (feature $=2r/\\lambda$)")
    tw = (sorted(mf["rows"], key=lambda v: v["a_lam"]) if mf is not None
          else sorted(out["thin_plate"]["truth_2d_mom"].values(), key=lambda v: v["a_lam"]))
    ms_ = 3.5 if mf is not None else 5.5
    f.plot([v["a_lam"] for v in tw], [abs(v["po_minus_tm_db"]) for v in tw], "-o", ms=ms_,
           color=CTM, label="strip : |PO $-$ MoM TM|   (feature $=a/\\lambda$)")
    f.plot([v["a_lam"] for v in tw], [abs(v["po_minus_te_db"]) for v in tw], "-s", ms=ms_,
           color=CTE, label="strip : |PO $-$ MoM TE|")
    f.plot([v["a_lam"] for v in tw], [abs(v["tm_minus_te_db"]) for v in tw], ":d", ms=ms_,
           color="#7d3c98", label="strip : truth's own TM/TE split\n(a scalar PO cannot span it)")
    G = out["consistency_with_drone"]["checks"]["gap_lives_at_drone_feature_scales"]
    if G.get("one_db_crossing_a_over_lam"):
        f.plot([G["one_db_crossing_a_over_lam"]], [1.0], "*", ms=13, color="#2e8b57", zorder=6,
               label=("worst-pol gap crosses 1 dB at $a/\\lambda$ = "
                      f"{G['one_db_crossing_a_over_lam']:.3f}"))
    fo = out["consistency_with_drone"]["drone_feature_over_lambda_at_1p8ghz"]
    f.axvspan(min(fo.values()), max(fo.values()), color="#ffd8a8", alpha=0.30, zorder=0)
    for nm, x in sorted(fo.items(), key=lambda t: t[1]):
        f.axvline(x, color="#999", lw=0.7, alpha=0.8)
        f.text(x, 0.35, f"drone {nm}", rotation=90, fontsize=6.4, color="#444",
               ha="right", va="bottom")
    f.axvline(DRONE["steep_ends_at_blade_over_lambda"], color="#b00", lw=1.4, ls="--")
    f.text(0.56, 0.66, "red dashed line = where the drone's steep\n"
                       "frequency band ended (blade/$\\lambda$="
           f"{DRONE['steep_ends_at_blade_over_lambda']:.3f})", transform=f.transAxes,
           fontsize=7.0, color="#b00", va="top", ha="left")
    f.axhline(1.0, color="#2e8b57", lw=0.9, ls=":")
    f.set_xscale("log"); f.set_xlabel("feature size / $\\lambda$")
    f.set_ylabel("|PO $-$ truth|   [dB]")
    f.set_ylim(0, 20.0); f.set_xlim(0.042, 4.3)
    f.set_xticks([0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 4.0])
    f.set_xticklabels(["0.05", "0.1", "0.2", "0.5", "1", "2", "4"])
    f.xaxis.set_minor_locator(matplotlib.ticker.NullLocator())
    f.set_title("F · The PO gap is set by feature/$\\lambda$ —\nsame knee the drone showed",
                fontsize=9.6)
    f.legend(fontsize=6.8, loc="upper right")

    # ── G: 1차 PTD 를 얹어도 닫히지 않는다 ───────────────────────────────
    g = AX[1, 2]
    if ptd is not None and "ptd_does_not_close_it" in out:
        P = out["ptd_does_not_close_it"]["per_width"]
        als = sorted(P, key=lambda k: P[k]["a_lam"])
        x = np.arange(len(als)); w = 0.38
        tm = [abs(P[k]["po_minus_tm_db"]) for k in als]
        tm2 = [abs(P[k]["po_ptd_minus_tm_db"]) for k in als]
        te = [abs(P[k]["po_minus_te_db"]) for k in als]
        te2 = [abs(P[k]["po_ptd_minus_te_db"]) for k in als]
        g.bar(x - w / 2, tm, w * 0.46, color=CTM, alpha=0.45, label="|PO $-$ MoM TM|")
        g.bar(x - w / 2 + w * 0.46, tm2, w * 0.46, color=CTM, label="|PO+PTD $-$ MoM TM|")
        g.bar(x + w / 2, te, w * 0.46, color=CTE, alpha=0.45, label="|PO $-$ MoM TE|")
        g.bar(x + w / 2 + w * 0.46, te2, w * 0.46, color=CTE, label="|PO+PTD $-$ MoM TE|")
        for i, k in enumerate(als):
            g.annotate("", xy=(x[i] - w / 2 + w * 0.46, tm2[i]), xytext=(x[i] - w / 2, tm[i]),
                       arrowprops=dict(arrowstyle="->", color="#0b4d82", lw=1.0))
            g.annotate("", xy=(x[i] + w / 2 + w * 0.46, te2[i]), xytext=(x[i] + w / 2, te[i]),
                       arrowprops=dict(arrowstyle="->", color="#7d2418", lw=1.0))
        g.set_xticks(x + w * 0.23)
        g.set_xticklabels([f"{P[k]['a_lam']:.2f}$\\lambda$" for k in als])
        g.set_xlabel("strip width  $a$")
        g.set_ylabel("|model $-$ truth|   [dB]")
        g.set_ylim(0, max(max(tm), max(te), max(tm2), max(te2)) * 1.42)
        g.text(0.63, 0.62, "first-order PTD at normal incidence\ncannot split polarisation:\n"
                            f"kernel V$-$H = {out['ptd_does_not_close_it']['max_abs_v_minus_h_db']:.0e} dB "
                            "$\\rightarrow$ TM improves, TE gets worse",
               transform=g.transAxes, va="top", ha="center", fontsize=7.0,
               bbox=dict(fc="white", ec="#bbb", alpha=0.94, boxstyle="round,pad=0.35"))
        g.set_title("G · Adding the PTD fringe term does not close it\n(drone caveat 3, tested)",
                    fontsize=9.6)
        g.legend(fontsize=6.8, loc="upper right", ncol=2)
    else:
        g.text(0.5, 0.5, "PTD part not available", ha="center", va="center",
               transform=g.transAxes)
        g.set_axis_off()

    # ── H: 기울기 메커니즘 ───────────────────────────────────────────────
    h = AX[1, 3]
    tag = "arm_tip_30mm" if "arm_tip_30mm" in slp["by_width"] else list(slp["by_width"])[0]
    v = slp["by_width"][tag]
    fg = np.asarray(v["f_ghz"])
    h.axvspan(1.8, 6.0, color="#ffd8a8", alpha=0.40, zorder=0)
    h.plot(fg, v["sigma3d_po_dbsm"], "-o", ms=4, color="#111", lw=1.6,
           label="PO closed form  (our target)")
    h.plot(fg, v["sigma3d_tm_dbsm"], "-s", ms=4, color=CTM, lw=1.4, label="exact MoM, TM")
    h.plot(fg, v["sigma3d_te_dbsm"], "-^", ms=4, color=CTE, lw=1.4, label="exact MoM, TE")
    s = out["slope_mechanism"]["by_width"][tag]
    h.text(0.035, 0.975,
           f"strip width {s['w_mm']:.1f} mm   ($w/\\lambda$ = {s['w_over_lam_at_1p8']:.3f} at 1.8 GHz)\n"
           f"slope [dB/GHz]        PO        MoM TM     MoM TE\n"
           f"  1.8$-$6.0 GHz     {s['a_po']:+7.3f}   {s['a_tm']:+7.3f}   {s['a_te']:+7.3f}\n"
           f"  6.0$-$18.2 GHz    {s['a_po_high']:+7.3f}   {s['a_tm_high']:+7.3f}   {s['a_te_high']:+7.3f}\n"
           f"PO excess over TM :  low {s['excess_lowband']['vs_tm']:+.3f}  "
           f"high {s['excess_highband']['vs_tm']:+.3f}",
           transform=h.transAxes, va="top", ha="left", fontsize=6.9, family="monospace",
           bbox=dict(fc="white", ec="#bbb", alpha=0.93, boxstyle="round,pad=0.35"))
    h.set_xlabel("frequency  [GHz]")
    h.set_ylabel("$\\sigma$   [dBsm]    (strip, $b = 6\\lambda$)")
    h.set_title("H · Why PO makes the low-band slope too steep\n(same sign as the drone)",
                fontsize=9.6)
    h.legend(fontsize=7.0, loc="lower right")

    vd = out["verdict"]
    fig.suptitle(
        "The low-frequency diagnosis, repeated on objects that HAVE an exact answer"
        "        |        "
        f"sphere: finer grid helps = {vd['sphere_lowka_improves_with_grid']}"
        f"        thin plate converges = {vd['thin_plate_converges']}"
        f"        consistent with the drone = {vd['consistent_with_drone']}",
        fontsize=11.5, y=0.988)
    fig.tight_layout(rect=(0, 0.006, 1, 0.955))
    fig.savefig(OUT_FIG, dpi=150)
    plt.close(fig)
    print(f"[fig] → {OUT_FIG}")


def merge():
    out, sph, pl, mom, slp, ptd, mf = analyse()
    os.makedirs(os.path.dirname(OUT_FIG), exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"[merge] → {OUT_JSON}")
    figure(out, sph, pl, mom, slp, ptd, mf)
    print("\n" + json.dumps(out["verdict"], ensure_ascii=False))
    print("\n" + out["bottom_line"])
    return out


if __name__ == "__main__":
    merge()
