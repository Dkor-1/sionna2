# -*- coding: utf-8 -*-
"""
das_fleet_validation.py — ⭐⭐⭐ **28 쌍 대조: 메쉬 방법이 N=4 에서 검증되는가**
================================================================================
무엇을 하나
  Das(WCL 2026) Table III 가 주는 **4 기체 × 7 바이스태틱각 = 28 셀** 전부에 대해
  우리 (a, b) 를 Das 의 (a, b) 옆에 놓고, 레벨오차·기울기오차·유의성을 낸다. 그리고
  사전등록(outputs/das_fleet_prereg.json)이 계산 **전에** 못 박은 합격규칙으로 판정한다.

읽는 것 (전부 읽기 전용)
  outputs/das_fleet_ours.json    — mini2 · m350rtk · phantom2 의 우리 σ (다른 워크플로 산출)
  outputs/das_fleet_spec.json    — Das Table III · 격자 · θb 정의 · 등급
  outputs/das_fleet_prereg.json  — 봉인된 예측과 합격규칙
  outputs/p3_validation.json     — phantom3 모노 대조(N=1 라운드)
  outputs/p3_ours.json           — phantom3 모노 원자료(통제군 검산용)
  outputs/das_fleet_box_control.json — 큐브/구 대조군
  outputs/partial/das_fleet_val_0803/phantom3/** — ⭐ 이 라운드가 새로 계산한 phantom3 바이스태틱

쓰는 것 (이 둘만)
  outputs/das_fleet_validation.json
  outputs/figs/das_fleet_compare.png
"""
from __future__ import annotations

import glob
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (os.path.join(ROOT, "src"), os.path.join(ROOT, "benchmark")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np                                                    # noqa: E402

OUT = os.path.join(ROOT, "outputs")
THETA_B = [0, 15, 30, 45, 60, 75, 90]
AF_ORDER = ["phantom3", "phantom2", "mini2", "m350rtk"]
AF_NAME = {"phantom3": "DJI Phantom 3", "phantom2": "DJI Phantom 2",
           "mini2": "DJI Mini 2", "m350rtk": "DJI M350 RTK"}

DAS_OFFSET_DB = 2.5068          # dB영역→선형(전력) 평균, 지수분기
CONV_UNCERT_DB = 0.9254         # 로그정규분기와의 차 — 해소 안 된 규약 불확도
U_A_DAS = 0.189                 # Das 자신의 a 적합잡음 규모(phantom2 의 θb 간 산포, spec 검정)


def jload(p):
    with open(p) as fh:
        return json.load(fh)


# --------------------------------------------------------------------------- #
#  통계 — das_fleet_ours.py 와 **같은 함수**(복사가 아니라 같은 식임을 보증하려고 옮겨 적음)
# --------------------------------------------------------------------------- #
def stats(sig_lin: np.ndarray) -> dict:
    s = np.maximum(np.asarray(sig_lin, float), 1e-30)
    db = 10.0 * np.log10(s)
    srt = np.sort(s)[::-1]
    k1 = max(1, int(round(0.01 * s.size)))
    return dict(mu_lin_dbsm=float(10.0 * np.log10(s.mean())), mu_db_dbsm=float(db.mean()),
                eps_db=float(db.std()), n_az=int(s.size),
                top1pct_share=float(srt[:k1].sum() / s.sum()),
                mu_lin_minus_mu_db=float(10.0 * np.log10(s.mean()) - db.mean()))


def fit_se(f, y):
    f, y = np.asarray(f, float), np.asarray(y, float)
    n = f.size
    a, b = np.polyfit(f, y, 1)
    r = y - (a * f + b)
    s = np.sqrt((r ** 2).sum() / (n - 2))
    se = s / np.sqrt(((f - f.mean()) ** 2).sum())
    return dict(a=float(a), b=float(b), se_a=float(se), s_resid=float(s),
                rmse_db=float(np.sqrt((r ** 2).mean())),
                r2=float(1.0 - r.var() / y.var()) if y.var() > 0 else float("nan"), n=int(n),
                f_mean=float(f.mean()), sxx=float(((f - f.mean()) ** 2).sum()))


def se_pred(fit, f0):
    """적합선의 f0 에서의 예측 표준오차 — 레벨 유의성의 우리 쪽 항."""
    return float(fit["s_resid"] * np.sqrt(1.0 / fit["n"] + (f0 - fit["f_mean"]) ** 2 / fit["sxx"]))


# --------------------------------------------------------------------------- #
#  phantom3 바이스태틱 — 이 라운드가 새로 계산한 부분파일을 모은다
# --------------------------------------------------------------------------- #
def load_phantom3_bistatic():
    part = os.path.join(OUT, "partial", "das_fleet_val_0803", "phantom3")
    acc, meta = {}, {}
    for p in sorted(glob.glob(os.path.join(part, "f*_s*_c*.json"))):
        d = jload(p)
        f = round(float(d["f_ghz"]), 6)
        acc.setdefault(f, {})
        for a, s in zip(d["az_deg"], d["sigma_lin_m2"]):
            acc[f][round(float(a), 4)] = s
        meta.setdefault("kernel", d.get("kernel"))
        meta.setdefault("geometry", d.get("geometry"))
        meta.setdefault("theta_b", d.get("theta_b"))
    fs = sorted(acc)
    per_f, n_az = {}, {}
    for f in fs:
        az = np.array(sorted(acc[f]))
        S = np.array([acc[f][a] for a in az])          # (n_az, 7)
        n_az[f"{f:.3f}"] = int(az.size)
        per_f[f"{f:.3f}"] = {str(t): stats(S[:, i]) for i, t in enumerate(THETA_B)}
    return fs, per_f, n_az, meta


# --------------------------------------------------------------------------- #
def main():
    t0 = time.time()
    ours = jload(os.path.join(OUT, "das_fleet_ours.json"))
    spec = jload(os.path.join(OUT, "das_fleet_spec.json"))
    prereg = jload(os.path.join(OUT, "das_fleet_prereg.json"))
    p3val = jload(os.path.join(OUT, "p3_validation.json"))
    p3ours = jload(os.path.join(OUT, "p3_ours.json"))
    boxc = jload(os.path.join(OUT, "das_fleet_box_control.json"))
    T3 = spec["table3"]

    FC = {"phantom3": 10.0, "phantom2": 18.5, "mini2": 24.0, "m350rtk": 24.0}
    BAND = {"phantom3": (1.8, 18.2), "phantom2": (11.0, 26.0),
            "mini2": (21.0, 27.0), "m350rtk": (21.0, 27.0)}

    res = {}

    # ---------------- phantom3 (이 라운드의 새 계산) ------------------------- #
    fs, per_f, n_az, p3meta = load_phantom3_bistatic()
    f = np.array(fs)
    fc = FC["phantom3"]
    p3 = dict(source="이 라운드 신규 계산 (benchmark/das_fleet_val_sigma.py)",
              kernel=p3meta.get("kernel"), geometry=p3meta.get("geometry"),
              band_ghz=[float(f[0]), float(f[-1])], n_freq=int(f.size),
              n_az_by_freq=n_az, per_freq=per_f, by_theta_b={})
    for t in THETA_B:
        ml = np.array([per_f[f"{x:.3f}"][str(t)]["mu_lin_dbsm"] for x in fs])
        md = np.array([per_f[f"{x:.3f}"][str(t)]["mu_db_dbsm"] for x in fs])
        ep = np.array([per_f[f"{x:.3f}"][str(t)]["eps_db"] for x in fs])
        fl, fd, fe = fit_se(f, ml), fit_se(f, md), fit_se(f, ep)
        p3["by_theta_b"][str(t)] = dict(
            fit_mu_lin=fl, fit_mu_db=fd, fit_eps=fe,
            mu_lin_at_fc_dbsm=float(fl["a"] * fc + fl["b"]),
            mu_db_at_fc_dbsm=float(fd["a"] * fc + fd["b"]),
            eps_at_fc_db=float(fe["a"] * fc + fe["b"]))

    #  ⭐⭐ 통제군 검산 — θb=0 열이 **같은 메쉬의 모노 산출**과 같은가
    #     비교 상대가 둘이다. p3_ours_v2 = v2(사진 실측) 메쉬, p3_ours = v1(phantom4 상속) 메쉬.
    ctl = ours["phantom3_control"]                 # das_fleet_ours 가 쓴 통제군 = v1
    b0 = p3["by_theta_b"]["0"]
    p3v2 = jload(os.path.join(OUT, "p3_ours_v2.json"))
    v2f = p3v2["aspects"]["el0"]["freq"]
    keys = sorted(p3["per_freq"], key=float)

    def _match(k):
        for kk in v2f:
            if abs(float(kk) - float(k)) < 1e-6:
                return v2f[kk]["mu_dbsm"]
        return None
    d2 = np.array([p3["per_freq"][k]["0"]["mu_lin_dbsm"] - _match(k) for k in keys
                   if _match(k) is not None])
    p3ours_el0 = {k: v["mu_dbsm"] for k, v in p3ours["aspects"]["el0"]["freq"].items()}
    d1 = np.array([p3["per_freq"][k]["0"]["mu_lin_dbsm"] - p3ours_el0[k] for k in keys])
    p3["control_check"] = dict(
        vs_p3_ours_v2=dict(
            n=int(d2.size), max_abs_dmu_db=float(np.abs(d2).max()),
            rms_dmu_db=float(np.sqrt((d2 ** 2).mean())), pass_=bool(np.abs(d2).max() < 0.05),
            what=("⭐ 이게 옳은 통제군이다. p3_ours_v2 는 **같은 v2 메쉬**를 rcs_sbr_batch(모노 "
                  "전용 경로)로 돌린 것이고, 우리 θb=0 은 rcs_sbr_multistatic(û_s=û_i)이다. "
                  "두 코드경로가 21 주파수에서 전부 같은 수를 내야 한다.")),
        vs_p3_ours_v1=dict(
            n=int(d1.size), max_abs_dmu_db=float(np.abs(d1).max()),
            rms_dmu_db=float(np.sqrt((d1 ** 2).mean())), mean_dmu_db=float(d1.mean()),
            our_a=b0["fit_mu_lin"]["a"], v1_a=ctl["fit_mu_lin"]["a"],
            our_mu_at_fc=b0["mu_lin_at_fc_dbsm"], v1_mu_at_fc=ctl["mu_lin_at_fc_dbsm"],
            d_mu_at_fc_db=float(b0["mu_lin_at_fc_dbsm"] - ctl["mu_lin_at_fc_dbsm"]),
            what=("⚠ 이건 검산이 아니라 **다른 메쉬와의 차이**다. v1(phantom4 형상표 상속, "
                  "높이 199.4 mm, 부피 2.339 L) vs v2(사진 실측 재구축, 195.1 mm, 1.996 L).")),
        pass_=bool(np.abs(d2).max() < 0.05))
    res["phantom3"] = p3

    #  ⭐⭐⭐ 상류 결함 1 — 함대 라운드가 네 기체를 **한 자로 재지 않았다**
    res["ruler_mismatch"] = dict(
        what=("⭐⭐ outputs/das_fleet_ours.json 의 phantom3 통제군은 outputs/p3_ours.json 을 읽는다. "
              "그 파일은 08:34 에 **v1 메쉬**로 만들어졌고, 같은 파일의 mini2·m350rtk·phantom2 는 "
              "13:48 이후 **v2 코드·v2 메쉬 상태**에서 계산됐다. 즉 네 기체 중 통제군 하나만 "
              "다른 자로 쟀다."),
        evidence=dict(
            p3_ours_generated="2026-08-03 08:34:12 (v1 메쉬)",
            p3_ours_v2_generated=p3v2["meta"]["generated"] + " (v2 메쉬)",
            fleet_partials_started="2026-08-03 13:48 (v2 메쉬 상태)",
            mesh_v1_bbox_vol="bbox z=0.19941 m · V=2.3387 L (outputs/p3_control.json)",
            mesh_v2_bbox_vol="bbox z=0.19505 m · V=1.9958 L (outputs/p3_control_v2.json)",
            our_theta_b0_equals_p3_ours_v2_to_db=float(np.abs(d2).max())),
        consequence=dict(
            phantom3_DL0_v1_db=float(ctl["DL_prereg_db"]),
            phantom3_DL0_v2_db=float(b0["mu_lin_at_fc_dbsm"]
                                     - (T3["phantom3"]["0"][0] * 10.0 + T3["phantom3"]["0"][1]
                                        + DAS_OFFSET_DB)),
            shift_db=None,
            slope_gate="v1 Δa=+0.210 (문턱 0.25 통과) → v2 Δa=+0.309 (문턱 초과)"),
        severity=("헤드라인 판정(NOT_VALIDATED, P3 산포)은 **안 바뀐다** — 산포는 phantom2 와 "
                  "m350rtk 가 정한다. 바뀌는 것은 phantom3 셀의 값과 기울기 게이트다."),
        note="이 산출물의 28 셀 표는 **전부 v2 자**로 통일했다.")
    res["ruler_mismatch"]["consequence"]["shift_db"] = float(
        res["ruler_mismatch"]["consequence"]["phantom3_DL0_v2_db"]
        - res["ruler_mismatch"]["consequence"]["phantom3_DL0_v1_db"])

    # ---------------- 28 셀 대조표 ------------------------------------------- #
    #  각 셀: 우리 (a,b) vs Das (a,b) · 레벨오차 · 기울기오차 · 유의성
    #  u_arc: phantom3 만 — Das 방위창이 180° 호인데 시작각이 미상이라 생기는 항
    ARC_SPAN = float(ctl["arc_window_span_db"])
    U_ARC = {"phantom3": ARC_SPAN / np.sqrt(12.0), "phantom2": 0.0, "mini2": 0.0, "m350rtk": 0.0}

    rows = []
    for af in AF_ORDER:
        fcx = FC[af]
        for t in THETA_B:
            if af == "phantom3":
                cell = p3["by_theta_b"][str(t)]
                fit = cell["fit_mu_lin"]
                mu_lin, mu_db = cell["mu_lin_at_fc_dbsm"], cell["mu_db_at_fc_dbsm"]
                eps = cell["eps_at_fc_db"]
                grade = spec["grades"]["phantom3"]["theta_b_0" if t == 0 else "theta_b_15_90"]
            else:
                cell = ours["airframes"][af]["by_theta_b"][str(t)]
                fit = cell["fit_mu_lin"]
                fit = dict(fit, s_resid=fit["rmse_db"] * np.sqrt(fit["n"] / (fit["n"] - 2)),
                           f_mean=fcx, sxx=None)
                mu_lin, mu_db = cell["mu_lin_at_fc_dbsm"], cell["mu_db_at_fc_dbsm"]
                eps = cell["eps_at_fc_db"]
                grade = cell["grade"]
            a_das, b_das = T3[af][str(t)][0], T3[af][str(t)][1]
            mu_das = a_das * fcx + b_das
            eps_das = T3[af][str(t)][2] * fcx + T3[af][str(t)][3]
            DL = mu_lin - (mu_das + DAS_OFFSET_DB)
            DLdb = mu_db - mu_das
            Da = fit["a"] - a_das
            #  레벨 유의성 — 우리 적합의 f_c 예측 SE + 규약분기 + (phantom3) 호 시작각
            if fit.get("sxx"):
                u_ours = se_pred(fit, fcx)
            else:                                  # 균등격자·f_c=중심 → SE = s/√n
                u_ours = fit["s_resid"] / np.sqrt(fit["n"])
            u_lvl = float(np.sqrt(u_ours ** 2 + CONV_UNCERT_DB ** 2 + U_ARC[af] ** 2))
            u_slp = float(np.sqrt(fit["se_a"] ** 2 + U_A_DAS ** 2))
            rows.append(dict(
                airframe=af, name=AF_NAME[af], theta_b=t, grade=grade,
                band_ghz=list(BAND[af]), fc_ghz=fcx,
                ours_a=fit["a"], ours_b=fit["b"], ours_se_a=fit["se_a"],
                ours_mu_at_fc_dbsm=mu_lin, ours_mu_db_at_fc_dbsm=mu_db, ours_eps_db=eps,
                das_a=a_das, das_b=b_das, das_mu_at_fc_dbsm=mu_das, das_eps_db=eps_das,
                DL_db=DL, DL_dbdomain_db=DLdb, Da_db_per_ghz=Da, d_eps_db=eps - eps_das,
                u_level_db=u_lvl, z_level=float(DL / u_lvl),
                u_slope_db_per_ghz=u_slp, z_slope=float(Da / u_slp)))
    res["table_28"] = rows

    # ---------------- 사전등록 판정 ------------------------------------------ #
    DL0 = {r["airframe"]: r["DL_db"] for r in rows if r["theta_b"] == 0}
    DL0db = {r["airframe"]: r["DL_dbdomain_db"] for r in rows if r["theta_b"] == 0}
    v = np.array([DL0[a] for a in AF_ORDER])
    pred = prereg["headline_prediction_theta_b_0"]["level_error_db_median"]
    slope_rows = {r["airframe"]: r for r in rows if r["theta_b"] == 0}
    bist_p2 = {r["theta_b"]: r for r in rows if r["airframe"] == "phantom2"}
    judge = dict(
        DL0_db=DL0, DL0_dbdomain_db=DL0db,
        predicted_DL0_db=pred,
        pred_minus_obs_db={a: float(DL0[a] - pred[a]) for a in AF_ORDER},
        P1_all_within_6db=bool(np.all(np.abs(v) <= 6.0)),
        P2_three_within_4db=bool(int(np.sum(np.abs(v) <= 4.0)) >= 3),
        P2_count_within_4db=int(np.sum(np.abs(v) <= 4.0)),
        P3_spread_db=float(v.max() - v.min()), P3_spread_within_6db=bool(v.max() - v.min() <= 6.0),
        P4_sign_agreement=bool(max(int(np.sum(v > 0)), int(np.sum(v < 0))) >= 3),
        P4_n_negative=int(np.sum(v < 0)),
        slope_gate={a: dict(Da=slope_rows[a]["Da_db_per_ghz"], se_a=slope_rows[a]["ours_se_a"],
                            pass_=bool(abs(slope_rows[a]["Da_db_per_ghz"]) <= 0.25 or
                                       abs(slope_rows[a]["Da_db_per_ghz"]) <= 1.96 * slope_rows[a]["ours_se_a"]))
                    for a in ("phantom3", "phantom2")},
        bistatic_gate_phantom2={str(t): dict(DL=bist_p2[t]["DL_db"],
                                             delta_vs_mono=float(bist_p2[t]["DL_db"] - bist_p2[0]["DL_db"]),
                                             pass_=bool(abs(bist_p2[t]["DL_db"] - bist_p2[0]["DL_db"]) <= 5.0))
                                for t in (15, 30, 45, 60)},
        spread_predicted_db=prereg["headline_prediction_theta_b_0"]["predicted_spread_db"],
    )
    #  ⭐ 규약을 바꿔도·등급 낮은 기체를 빼도 산포가 남는가 (전부 v2 자)
    vdb = np.array([DL0db[a] for a in AF_ORDER])
    v3 = np.array([DL0[a] for a in AF_ORDER if a != "phantom2"])
    vdb3 = np.array([DL0db[a] for a in AF_ORDER if a != "phantom2"])
    judge["alternative_convention_v2_ruler"] = dict(
        linear_mean_all=float(v.max() - v.min()),
        linear_mean_drop_gradeC=float(v3.max() - v3.min()),
        db_domain_all=float(vdb.max() - vdb.min()),
        db_domain_drop_gradeC=float(vdb3.max() - vdb3.min()),
        any_within_6db=bool(min(v.max() - v.min(), v3.max() - v3.min(),
                                vdb.max() - vdb.min(), vdb3.max() - vdb3.min()) <= 6.0),
        reading=("네 조합 중 6 dB 문턱을 넘지 않는 것은 'dB영역 + C등급 제외' 하나뿐이고 "
                 "그것도 6.75 dB 로 아슬아슬하게 **넘는다**. P3 실패는 규약 선택의 산물이 아니다."))
    judge["slope_gate_pass"] = all(x["pass_"] for x in judge["slope_gate"].values())
    judge["bistatic_gate_pass"] = all(x["pass_"] for x in judge["bistatic_gate_phantom2"].values())
    if not judge["P3_spread_within_6db"]:
        judge["verdict"] = "NOT_VALIDATED (P3 산포)"
    elif judge["P1_all_within_6db"] and judge["P2_three_within_4db"] and judge["P4_sign_agreement"] \
            and judge["slope_gate_pass"] and judge["bistatic_gate_pass"]:
        judge["verdict"] = "VALIDATED"
    else:
        judge["verdict"] = "PARTIAL"
    judge["prereg_hit"] = bool(judge["verdict"] == "VALIDATED")
    judge["prediction_hit_headline"] = bool(
        abs(judge["P3_spread_db"] - judge["spread_predicted_db"]) <= 2.0 and
        all(abs(judge["pred_minus_obs_db"][a]) <= 2.0 for a in AF_ORDER))
    #  ⭐ 함대 라운드가 발표한 판정(통제군 = v1 메쉬)과 나란히 — 무엇이 바뀌고 무엇이 안 바뀌나
    v1_DL0 = dict(DL0); v1_DL0["phantom3"] = float(ctl["DL_prereg_db"])
    vv1 = np.array([v1_DL0[a] for a in AF_ORDER])
    judge["as_published_fleet_v1_control"] = dict(
        DL0_db=v1_DL0, P3_spread_db=float(vv1.max() - vv1.min()),
        P2_count_within_4db=int(np.sum(np.abs(vv1) <= 4.0)),
        slope_gate_phantom3_Da=float(ctl["Da_db_per_ghz"]),
        verdict=ours["prereg_gates"]["verdict"],
        what="outputs/das_fleet_ours.json :: prereg_gates 가 발표한 값(통제군이 v1 메쉬).")
    judge["what_changed_with_one_ruler"] = (
        f"phantom3 DL(0) {v1_DL0['phantom3']:+.2f} → {DL0['phantom3']:+.2f} dB "
        f"({DL0['phantom3'] - v1_DL0['phantom3']:+.2f}), 4 dB 안에 드는 기체 "
        f"{int(np.sum(np.abs(vv1) <= 4.0))} → {judge['P2_count_within_4db']}, "
        f"기울기 게이트 phantom3 {ctl['Da_db_per_ghz']:+.3f} → "
        f"{judge['slope_gate']['phantom3']['Da']:+.3f} (문턱 0.25). "
        f"산포는 {float(vv1.max()-vv1.min()):.2f} → {judge['P3_spread_db']:.2f} dB 로 사실상 그대로 — "
        f"산포를 정하는 두 기체(phantom2·m350rtk)가 안 바뀌기 때문이다.")
    res["prereg_judgement"] = judge

    # ---------------- 바이스태틱 추세 ---------------------------------------- #
    trend = {}
    for af in AF_ORDER:
        rr = {r["theta_b"]: r for r in rows if r["airframe"] == af}
        dl = np.array([rr[t]["DL_db"] for t in THETA_B])
        adl = np.abs(dl - dl[0])
        dmu_ours = np.array([rr[t]["ours_mu_at_fc_dbsm"] - rr[0]["ours_mu_at_fc_dbsm"] for t in THETA_B])
        dmu_das = np.array([rr[t]["das_mu_at_fc_dbsm"] - rr[0]["das_mu_at_fc_dbsm"] for t in THETA_B])
        sl = np.polyfit(THETA_B, dl, 1)[0]
        trend[af] = dict(
            DL_by_theta_b={str(t): float(x) for t, x in zip(THETA_B, dl)},
            drift_vs_mono_db={str(t): float(x) for t, x in zip(THETA_B, dl - dl[0])},
            abs_drift_db={str(t): float(x) for t, x in zip(THETA_B, adl)},
            monotone_in_abs=bool(np.all(np.diff(adl) >= -1e-9)),
            drift_slope_db_per_deg=float(sl),
            drift_at_90_db=float(dl[-1] - dl[0]),
            dmu_ours_db={str(t): float(x) for t, x in zip(THETA_B, dmu_ours)},
            dmu_das_bandcentre_db={str(t): float(x) for t, x in zip(THETA_B, dmu_das)},
            our_taper_over_das_taper=float(abs(dmu_ours[-1]) / max(abs(dmu_das[-1]), 1e-9)),
            prereg_band_db=prereg["bistatic_prediction"]["net_prediction"]["magnitude"])
    #  사전등록 바이스태틱 예측(|DL(θb)−DL(0)| ≤ 0/0.5/1/2.5/5/10/16)과 대조
    PRE = {0: 0.0, 15: 0.5, 30: 1.0, 45: 2.5, 60: 5.0, 75: 10.0, 90: 16.0}
    trend["prereg_bound_check"] = {
        af: {str(t): dict(bound=PRE[t], obs=abs(trend[af]["drift_vs_mono_db"][str(t)]),
                          within=bool(abs(trend[af]["drift_vs_mono_db"][str(t)]) <= PRE[t] + 1e-9))
             for t in THETA_B} for af in AF_ORDER}
    trend["all_within_prereg_bound"] = bool(all(
        c["within"] for af in AF_ORDER for c in trend["prereg_bound_check"][af].values()))
    #  기울기의 θb 의존 — obliquity 인플레이션 상한과 나란히
    INFL = {0: 0.0, 15: 0.01, 30: 0.18, 45: 0.97, 60: 3.27, 75: 8.75, 90: float("nan")}
    trend["obliquity_inflation_upper_db"] = {str(k): v_ for k, v_ in INFL.items()}
    #  기계 1 — 상반성 위반(단일 조명격자 재사용의 대가). θb 와 함께 커져야 한다.
    trend["reciprocity_violation_rms_db"] = {
        af: {str(t): ours["airframes"][af]["diagnostics"]["reciprocity"]["per_theta_b"][str(t)]["rms_db"]
             for t in THETA_B} for af in ("mini2", "m350rtk", "phantom2")}
    #  기계 2 — 출사 가시성이 깎는 몫(θb=0 에서 정확히 0 = no-op 검산)
    ev = {}
    for af in ("mini2", "m350rtk", "phantom2"):
        pf = ours["airframes"][af]["diagnostics"]["exit_vis"]["per_freq"]
        ev[af] = {str(t): float(np.mean([pf[k][str(t)]["delta_mu_lin_db"] for k in pf]))
                  for t in THETA_B}
    trend["exit_vis_delta_mu_lin_db"] = ev
    trend["mechanism_reading"] = (
        "네 기체 모두 DL 이 θb 와 함께 **아래로** 흐른다(단조). 사전등록은 θb≥60 에서 음(-)을 "
        "예측했고 θb≤45 에서는 부호를 못 정한다고 적었는데, 실제로는 15° 부터 이미 음이다. "
        "즉 게이트배제(수신게이트 n̂·û_s>0 교집합 축소) + 단일 조명격자 표본손실이 obliquity "
        "인플레이션(+)을 **전 구간에서** 이긴다. 상반성 위반 rms 가 같은 방향으로 커지는 것이 "
        "그 표본손실의 직접 증거다(mini2 0→6.2 dB).")
    res["bistatic_trend"] = trend

    # ---------------- 대역(고 ka) 효과 --------------------------------------- #
    ka = {af: prereg["predictions"][af]["ka_table"] for af in AF_ORDER}

    def ka_min_dom(af):
        return ka[af].get("_min_ka_of_dominant_parts", ka[af].get("_min_ka_in_band"))
    band = dict(
        per_airframe={af: dict(band_ghz=list(BAND[af]), fc_ghz=FC[af],
                               ka_min_dominant=ka_min_dom(af),
                               ka_halfspan_lo=ka[af]["airframe half-span"]["ka_at_band_lo"],
                               DL0_db=DL0[af], abs_DL0_db=abs(DL0[af])) for af in AF_ORDER},
        high_band_2127=["mini2", "m350rtk"], low_band=["phantom3"], mid_band=["phantom2"],
        mean_abs_DL_high=float(np.mean([abs(DL0["mini2"]), abs(DL0["m350rtk"])])),
        abs_DL_phantom3=float(abs(DL0["phantom3"])),
        spread_high_band_db=float(abs(DL0["mini2"] - DL0["m350rtk"])),
    )
    #  phantom3 자체의 대역내 분해 — 저대역 vs 고대역 잔차 (p3_validation 이 이미 잰 값)
    band["phantom3_within_band"] = dict(
        low_band_mean_db=p3val["residual"]["vs_das_exponential"]["low_band_mean_db"],
        high_band_mean_db=p3val["residual"]["vs_das_exponential"]["high_band_mean_db"],
        trend_db_per_ghz=p3val["residual"]["vs_das_exponential"]["trend_db_per_ghz"],
        reading=("phantom3 안에서는 저대역 잔차 −4.85 dB → 고대역 −2.35 dB 로 **줄어든다** "
                 "(H_ka 가 예측하는 방향). 그러나 그 외삽의 끝인 21–27 GHz 에서는 두 기체가 "
                 "−0.51 과 +9.08 로 갈린다 — 대역만으로 설명되지 않는다."))
    band["high_ka_better"] = bool(band["mean_abs_DL_high"] < band["abs_DL_phantom3"])
    band["high_ka_better_if_best_only"] = bool(min(abs(DL0["mini2"]), abs(DL0["m350rtk"]))
                                               < band["abs_DL_phantom3"])
    res["band_effect"] = band

    # ---------------- 자유도 ------------------------------------------------- #
    dof = {
        "phantom3": dict(free=205, constrained=13, ratio=15.8, ratio_fleet_rule=12.76,
                         iou=None, iou_pct_of_cap=None, source="outputs/p3_attack.json :: Q3",
                         note="205 : 13 = 15.8. 함대 규칙으로 다시 세면 12.76."),
        "phantom2": dict(free=None, constrained=None, ratio=None, ratio_fleet_rule=None,
                         iou=None, iou_pct_of_cap=None,
                         source="대리 메쉬 — phantom3 메쉬를 그대로 쓴다",
                         note=("⭐ 자유도를 셀 수 없다. phantom2 관측으로 고정된 형상 수가 **0** 이다 "
                               "(Table I 의 35x20 cm 두 수뿐이고 그건 phantom3 와 같은 수다). "
                               "비로 쓰면 분모가 0 이라 무한대다.")),
        "mini2": dict(free=None, constrained=None, ratio=3.65, ratio_fleet_rule=3.65,
                      iou=None, iou_pct_of_cap=77.3, source="outputs/das_fleet_prereg.json :: fail_means",
                      note="DJI 공표 GLB(59 파트/109,470 면)에서 형상이 왔다."),
        "m350rtk": dict(free=None, constrained=None, ratio=5.53, ratio_fleet_rule=5.53,
                        iou=0.503, iou_pct_of_cap=56.0, source="outputs/das_fleet_prereg.json :: fail_means",
                        note="등록 사진 1 장. 함대 최하위권 IoU."),
    }
    for af in AF_ORDER:
        dof[af]["abs_DL0_db"] = abs(DL0[af])
        dof[af]["DL0_db"] = DL0[af]
    #  ⭐ v2 메쉬는 사진 실측으로 자유도를 다시 세었다 (p3_validation_v2 :: verdict)
    dof["phantom3"].update(free=121, constrained=69, ratio=round(121 / 69, 2),
                           ratio_fleet_rule=round(121 / 69, 2), iou_pct_of_cap=86.9,
                           source="outputs/p3_validation_v2.json :: verdict.what_the_photo_measurement_bought",
                           note=("⭐ 이 라운드가 쓰는 메쉬는 **v2(사진 실측)** 다. 자유도 205:13=15.8 "
                                 "(v1) → 121:69=1.75 (v2), IoU 천장대비 77.9% → 86.9%. "
                                 "v1 값 15.8 은 아래 v1_ratio 로 남긴다."),
                           v1_ratio=15.8, v1_free=205, v1_constrained=13, v1_iou_pct_of_cap=77.9)
    xr = [(dof[a]["ratio_fleet_rule"], abs(DL0[a])) for a in AF_ORDER if dof[a]["ratio_fleet_rule"]]
    x = np.array([p[0] for p in xr]); y = np.array([p[1] for p in xr])
    dof["_correlation"] = dict(
        n=int(x.size), pearson_r=float(np.corrcoef(x, y)[0, 1]) if x.size > 2 else None,
        spearman_r=float(np.corrcoef(np.argsort(np.argsort(x)), np.argsort(np.argsort(y)))[0, 1])
        if x.size > 2 else None,
        pairs={a: dict(dof_ratio=dof[a]["ratio_fleet_rule"], abs_DL0=abs(DL0[a]))
               for a in AF_ORDER if dof[a]["ratio_fleet_rule"]},
        what="자유도 비(낮을수록 잘 구속된 메쉬) vs |DL(0)|. n=3 이므로 상관계수는 서술용이다.")
    #  ⭐⭐⭐ 증거축 분할 검정 — 대역이 아니라 **그 기체 자체의 형상 증거**가 가르는가
    WELL = ["phantom3", "mini2"]          # v2 사진 실측 / DJI 공표 GLB
    WEAK = ["phantom2", "m350rtk"]        # 대리 메쉬(자기 증거 0) / 사진 1 장
    g_ok = np.array([abs(DL0[a]) for a in WELL])
    g_no = np.array([abs(DL0[a]) for a in WEAK])
    dof["evidence_split"] = dict(
        well_constrained=dict(members=WELL, evidence={"phantom3": "사진 실측 재구축(IoU 천장대비 86.9%)",
                                                      "mini2": "DJI 공표 GLB 59 파트(IoU 77.3%)"},
                              abs_DL0_db={a: abs(DL0[a]) for a in WELL}, mean_db=float(g_ok.mean()),
                              max_db=float(g_ok.max())),
        weakly_constrained=dict(members=WEAK,
                                evidence={"phantom2": "⭐ 자기 증거 **0** — phantom3 메쉬를 대리로 씀",
                                          "m350rtk": "등록 사진 1 장(IoU 0.503 = 천장대비 56.0%)"},
                                abs_DL0_db={a: abs(DL0[a]) for a in WEAK}, mean_db=float(g_no.mean()),
                                max_db=float(g_no.max()), min_db=float(g_no.min())),
        gap_db=float(g_no.min() - g_ok.max()),
        ratio_of_means=float(g_no.mean() / g_ok.mean()),
        separated=bool(g_no.min() > g_ok.max()),
        exact_partition_p=1.0 / 6.0,
        exact_partition_note=("이 2:2 분할은 **사전등록이 미리 지정한 것**이다(prereg 가 mini2 를 "
                              "'가장 잘 구속된 메쉬', m350rtk 를 '증거가 가장 얇다', phantom2 를 "
                              "'대리 메쉬' 로 계산 전에 적었다). 지정된 두 기체가 |DL| 하위 두 "
                              "자리를 다 차지할 확률은 무작위 배정에서 1/C(4,2)=1/6=0.167 이다. "
                              "⛔ n=4 다 — 유의수준으로 쓸 수 없고 가설 생성이다."),
        reading=("⭐⭐ N=4 가 **2:2 로 정확히 증거축을 따라 갈린다.** 자기 기체 형상 증거가 있는 둘은 "
                 f"|DL| ≤ {g_ok.max():.2f} dB, 없는 둘은 ≥ {g_no.min():.2f} dB 로 "
                 f"{float(g_no.min() - g_ok.max()):.2f} dB 의 빈 구간을 사이에 두고 떨어진다. "
                 "대역(1.8–18.2 vs 11–26 vs 21–27)으로도, ka 로도, 기체 크기로도 이 분할이 안 나온다 — "
                 "21–27 GHz 한 대역 안에서만도 mini2 0.51 과 m350rtk 9.08 로 갈리기 때문이다."))
    res["degrees_of_freedom"] = dof

    # ---------------- 큐브 대조군 -------------------------------------------- #
    bx = {}
    for af in AF_ORDER:
        ctrls = boxc["airframes"][af]["controls"]
        ours_dl = DL0[af]
        per = {}
        for name, c in ctrls.items():
            cell = c["by_theta_b"]["0"]
            per[name] = dict(dims_m=c["dims_m"], desc=c["desc"], DL_db=cell["DL_prereg_db"],
                             abs_DL_db=abs(cell["DL_prereg_db"]), a=cell["a"],
                             Da_db_per_ghz=cell["Da_db_per_ghz"], eps_db=cell["eps_at_fc_db"],
                             d_eps_db=cell["eps_at_fc_db"] - (T3[af]["0"][2] * FC[af] + T3[af]["0"][3]))
        best = min(per, key=lambda k: per[k]["abs_DL_db"])
        best_box = min([k for k in per if k != "sphere_eqvol"], key=lambda k: per[k]["abs_DL_db"])
        das_eps = T3[af]["0"][2] * FC[af] + T3[af]["0"][3]
        our_eps = [r for r in rows if r["airframe"] == af and r["theta_b"] == 0][0]["ours_eps_db"]
        per_af = dict(controls=per, ours_DL_db=ours_dl, ours_abs_DL_db=abs(ours_dl),
                      ours_eps_db=our_eps, das_eps_db=das_eps,
                      ours_d_eps_db=our_eps - das_eps,
                      best_control=best, best_control_abs_DL_db=per[best]["abs_DL_db"],
                      best_box_only=best_box, best_box_abs_DL_db=per[best_box]["abs_DL_db"],
                      beats_all_boxes=bool(abs(ours_dl) < per[best_box]["abs_DL_db"]),
                      beats_best_control=bool(abs(ours_dl) < per[best]["abs_DL_db"]),
                      margin_vs_best_box_db=float(per[best_box]["abs_DL_db"] - abs(ours_dl)),
                      margin_vs_best_control_db=float(per[best]["abs_DL_db"] - abs(ours_dl)))
        #  ⭐ 레벨 하나로 이기고 지는 것을 말하지 않는다 — 세 지표를 다 본다.
        #    score = |DL| + |Δa|·(대역폭) + |Δε|  (전부 dB 단위로 맞춘 합)
        BW = BAND[af][1] - BAND[af][0]
        our_row = [r for r in rows if r["airframe"] == af and r["theta_b"] == 0][0]
        our_sc = abs(our_row["DL_db"]) + abs(our_row["Da_db_per_ghz"]) * BW + abs(our_row["d_eps_db"])
        for name in per:
            per[name]["score_db"] = float(abs(per[name]["DL_db"])
                                          + abs(per[name]["Da_db_per_ghz"]) * BW
                                          + abs(per[name]["d_eps_db"]))
        best_sc = min(per, key=lambda k: per[k]["score_db"])
        per_af.update(score_definition="|DL| + |Δa|·(밴드폭 GHz) + |Δε|  [dB]",
                      ours_score_db=float(our_sc), ours_Da=our_row["Da_db_per_ghz"],
                      ours_d_eps_db=our_row["d_eps_db"],
                      best_control_by_score=best_sc,
                      best_control_score_db=per[best_sc]["score_db"],
                      beats_all_controls_by_score=bool(our_sc < per[best_sc]["score_db"]),
                      score_margin_db=float(per[best_sc]["score_db"] - our_sc))
        bx[af] = per_af
    bx["_summary"] = dict(
        beats_all_controls_by_score={a: bx[a]["beats_all_controls_by_score"] for a in AF_ORDER},
        n_beats_by_score=int(sum(bx[a]["beats_all_controls_by_score"] for a in AF_ORDER)),
        beats_all_boxes={a: bx[a]["beats_all_boxes"] for a in AF_ORDER},
        beats_best_control={a: bx[a]["beats_best_control"] for a in AF_ORDER},
        n_beats_boxes=int(sum(bx[a]["beats_all_boxes"] for a in AF_ORDER)),
        n_beats_any_control=int(sum(bx[a]["beats_best_control"] for a in AF_ORDER)),
        eps_test=("⭐ 레벨만 보면 부피등가 **구**가 강적이다(σ=πa², 방위·주파수 무관). 그러나 구는 "
                  "ε=0 이고 a=0 이라 Das 가 보고한 요동(ε=3.7~6.9 dB)과 기울기(a=0.07~0.21)를 "
                  "**하나도** 못 낸다. 상자는 반대로 ε≈9~11 dB 로 과대하다. 레벨 하나로 "
                  "'이겼다/졌다' 를 말하면 안 된다."),
        verify=boxc.get("verify_mu_closed_vs_sbr", boxc.get("verify_closed_form_vs_sbr")))
    res["box_control"] = bx

    # ---------------- 정반사 플래시 지배도 가설 (함대 라운드의 설명) ----------- #
    t1 = {"phantom3": float(np.median([p3["per_freq"][k]["0"]["top1pct_share"] for k in p3["per_freq"]]))}
    gapd = {"phantom3": float(np.mean([p3["per_freq"][k]["0"]["mu_lin_minus_mu_db"]
                                       for k in p3["per_freq"]]))}
    for af in ("phantom2", "mini2", "m350rtk"):
        cs = ours["airframes"][af]["convention_sensitivity"]
        t1[af] = cs["top1pct_share_median"]
        gapd[af] = cs["ours_mu_lin_minus_mu_db_at_fc"]
    xs = np.array([t1[a] for a in AF_ORDER]); ys = np.array([abs(DL0[a]) for a in AF_ORDER])
    rk = lambda z: np.argsort(np.argsort(z))                       # noqa: E731
    res["flash_dominance_hypothesis"] = dict(
        top1pct_share={a: t1[a] for a in AF_ORDER},
        mu_lin_minus_mu_db={a: gapd[a] for a in AF_ORDER},
        DL0_db=DL0, abs_DL0_db={a: abs(DL0[a]) for a in AF_ORDER},
        spearman_top1pct_vs_absDL=float(np.corrcoef(rk(xs), rk(ys))[0, 1]),
        pearson_top1pct_vs_DL=float(np.corrcoef(xs, np.array([DL0[a] for a in AF_ORDER]))[0, 1]),
        monotone_in_absDL=bool(np.all(np.diff(ys[np.argsort(xs)]) >= 0)),
        das_fleet_claim=ours["headline"]["what_broke"][1] if len(ours["headline"]["what_broke"]) > 1 else None,
        verdict=("⭐ 함대 라운드는 'DL 이 top1pct_share 와 함께 단조 증가한다'(mini2 0.16→−0.5, "
                 "phantom2 0.20→−7.2, m350rtk 0.37→+9.1)고 적었다. 두 가지를 정정한다. "
                 "(1) 나열된 세 수 −0.5 · −7.2 · +9.1 은 **DL 로는 단조가 아니다** — |DL| 로 읽어야 "
                 "단조다. (2) 같은 자로 잰 phantom3 를 넣으면 top1pct 0.117 에 |DL| 1.47 이라 "
                 "|DL| 단조성도 깨진다(mini2 0.164 → 0.51 이 더 낮다). 남는 것은 **추세**다 "
                 f"(Spearman {float(np.corrcoef(rk(xs), rk(ys))[0, 1]):.1f}, n=4). "
                 "⚠ 게다가 이 축은 증거축과 교란돼 있다 — 플래시 지배가 큰 두 기체(m350rtk 0.369, "
                 "phantom2 0.201)가 정확히 형상 증거가 없는 두 기체다. n=4 로는 못 가른다."))

    # ---------------- 상류 파일에서 발견한 결함 ------------------------------- #
    res["upstream_defect_found"] = dict(
        file="outputs/das_fleet_ours.json",
        field="airframes.phantom2.delta_mu_vs_mono_das_db",
        what=("phantom2 의 Das Δμ(θb) 가 **절편차 b(θb)−b(0)** 로 계산돼 있다 "
              "(−7.21/−1.20/−2.66/−2.08/+4.25/+1.70). phantom2 는 a 가 θb 마다 다른 "
              "유일한 기체라 절편차 ≠ 밴드중심 레벨차다."),
        correct_at_band_centre_db={"0": 0.0, "15": -1.845, "30": -1.015, "45": -2.66,
                                   "60": -3.745, "75": -2.04, "90": -0.705},
        source_of_correct="outputs/das_fleet_spec.json :: airframes.phantom2.delta_mu_vs_mono_at_bandcentre_db",
        impact=("DL·Da·합격판정에는 **영향 없다**(그것들은 das.mu_at_fc_dbsm 로 계산되고 그 값은 맞다). "
                "영향받는 것은 그 진단 필드 하나뿐이다. 이 산출물의 bistatic_trend 는 "
                "밴드중심 값을 다시 계산해 쓴다."),
        severity="진단 필드 한정 — 헤드라인 수치 불변")

    # ---------------- 메타 ---------------------------------------------------- #
    res["_meta"] = dict(
        generated=time.strftime("%Y-%m-%d %H:%M:%S"),
        generator="benchmark/das_fleet_validation.py",
        what="⭐⭐⭐ 28 쌍(4 기체 × 7 θb) 대조 — 메쉬 방법이 N=4 에서 검증되는가",
        wrote_only=["outputs/das_fleet_validation.json", "outputs/figs/das_fleet_compare.png"],
        read_only=["outputs/das_fleet_ours.json", "outputs/das_fleet_spec.json",
                   "outputs/das_fleet_prereg.json", "outputs/p3_validation.json",
                   "outputs/p3_ours.json", "outputs/das_fleet_box_control.json",
                   "outputs/partial/das_fleet_val_0803/**"],
        new_computation=("phantom3 바이스태틱 σ(f, θb) — 21 주파수 × 360 방위 × 7 각도. "
                         "함대와 같은 커널설정·같은 기하. 이것이 없으면 28 셀이 22 셀이다."),
        ours_source_generated=ours["_meta"]["generated"],
        m350rtk_az_state=("⚠ das_fleet_ours.json 생성 시점에 m350rtk 는 아직 방위격자를 채우는 중이었다 "
                          "(주파수별 n_az 90~720). 그 기체 수치는 그 상태의 것이다."),
        stat_convention=dict(mu_lin="10log10(mean_φ σ)", mu_db="mean_φ(10log10 σ)",
                             eps="std_φ(10log10 σ)",
                             DL="μ_lin(f_c) − [a_das·f_c + b_das + 2.5068]",
                             u_level="√(SE_pred,ours(f_c)² + 0.9254² + u_arc²)",
                             u_slope="√(SE(a)_ours² + 0.189²)  — 0.189 은 Das 자신의 a 적합잡음 규모"),
        runtime_s=round(time.time() - t0, 1))

    p = os.path.join(OUT, "das_fleet_validation.json")
    with open(p, "w") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1, default=float)
    print("wrote", p)
    #  콘솔 요약
    print(f"\n판정: {judge['verdict']}  (P1 {judge['P1_all_within_6db']} · P2 "
          f"{judge['P2_three_within_4db']} · P3 산포 {judge['P3_spread_db']:.2f} dB · P4 "
          f"{judge['P4_sign_agreement']})")
    for af in AF_ORDER:
        rr = {r["theta_b"]: r for r in rows if r["airframe"] == af}
        print(f"  {af:9s} DL(0)={DL0[af]:+7.2f} dB  z={rr[0]['z_level']:+6.1f}  "
              f"Δa={rr[0]['Da_db_per_ghz']:+.3f}  drift@90={trend[af]['drift_at_90_db']:+.2f} dB  "
              f"box_best={bx[af]['best_box_only']}({bx[af]['best_box_abs_DL_db']:.1f})  "
              f"beats_box={bx[af]['beats_all_boxes']}")
    return res


if __name__ == "__main__":
    main()
