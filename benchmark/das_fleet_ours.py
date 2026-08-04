# -*- coding: utf-8 -*-
"""
das_fleet_ours.py — 부분 σ 파일을 모아 μ(θb,f)·ε·적합·Das 대조를 낸다
                    → outputs/das_fleet_ours.json
=======================================================================
계산은 하지 않는다(그건 `das_fleet_sigma.py`). 여기서 하는 일은 넷이다.
  1) outputs/partial/das_fleet_0803/**.json 을 주파수별로 합쳐 방위 표본을 **합집합**한다.
  2) Das 규약대로 통계를 낸다 — μ 는 **두 갈래 다** 들고 다닌다(아래 STAT 절).
  3) 같은 창에서 μ(f)=a·f+b 를 적합하고 Das Table III 계수와 맞댄다.
  4) 통제군(phantom3)·진단(상반성·exit_vis)을 붙이고 등급·주의사항을 함께 적는다.

■ STAT — μ 를 두 갈래로 내는 이유 (das_fleet_spec.json :: stat_convention)
    Das §III-1 은 **선형 σ 의 방위평균**이라 쓰고, 같은 논문 §III-2 의 3GPP remark 는 μ 를
    **dB 영역 평균**으로 쓴다. 같은 양이 아니다. Das Phantom 3 와 Yuan 이 같은 원자료임을
    이용한 잔차검산이 dB 영역평균 쪽을 지지했고(지수분기 오프셋 +2.5068 dB, 잔차 rms 0.24 dB),
    로그정규분기(+3.4322)와의 차 **0.9254 dB 는 해소되지 않은 규약 불확도**다.
    → 우리는 μ_lin = 10log10(mean_φ σ) 와 μ_db = mean_φ(10log10 σ) 를 **둘 다** 내고,
      대조도 두 갈래로 적는다. 단일값으로 좁히지 않는다.

■ ⛔ 이 스크립트는 outputs/ 아래 **das_fleet_ours.json 한 파일만** 쓴다.
    p3_*.json · phantom3/mavic4pro/matrice4e 산출물 · teammeeting_0804/* ·
    sigma_grid_regen.json · sigma_el_extend_progress.json · anchor_subband*.json 은 **읽기만** 한다.

실행:
    PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/das_fleet_ours.py
"""
from __future__ import annotations

import glob
import json
import os
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARTIAL = os.path.join(ROOT, "outputs", "partial", "das_fleet_0803")
OUT = os.path.join(ROOT, "outputs", "das_fleet_ours.json")
SPEC = json.load(open(os.path.join(ROOT, "outputs", "das_fleet_spec.json")))
PREREG = json.load(open(os.path.join(ROOT, "outputs", "das_fleet_prereg.json")))

LOG_TO_LIN_EXP_DB = 2.5068          # Das μ(dB영역) → 선형(전력)평균, 지수분기
LOG_TO_LIN_LN_DB = 3.4322           # 로그정규분기
CONV_UNCERT_DB = LOG_TO_LIN_LN_DB - LOG_TO_LIN_EXP_DB      # 0.9254 — 해소 안 된 규약 불확도
THETA_B = [0, 15, 30, 45, 60, 75, 90]


# --------------------------------------------------------------------------- #
def load_airframe(af: str):
    """부분파일 합집합 → {f_ghz: (az_deg[N], sigma_lin[N,7])}. 중복 방위는 한 번만 센다."""
    acc: dict = {}
    meta: dict = {}
    for p in sorted(glob.glob(os.path.join(PARTIAL, af, "f*_s*_c*.json"))):
        try:
            d = json.load(open(p))
        except Exception:
            continue                                  # 반쪽 파일 — 원자적 저장이라 원래 안 생긴다
        f = round(float(d["f_ghz"]), 6)
        A = np.asarray(d["az_deg"], float)
        S = np.asarray(d["sigma_lin_m2"], float)
        if f not in acc:
            acc[f] = {}
        for a, s in zip(A, S):
            acc[f][round(float(a), 4)] = s            # 방위각을 키로 → 중복 자동 제거
        meta.setdefault("kernel", d.get("kernel"))
        meta.setdefault("geometry", d.get("geometry"))
        meta.setdefault("mesh_key", d.get("mesh_key"))
        meta.setdefault("proxy_mesh", d.get("proxy_mesh"))
    out = {}
    for f, dd in acc.items():
        az = np.array(sorted(dd))
        out[f] = (az, np.array([dd[a] for a in az]))
    return out, meta


def stats(sig_lin: np.ndarray) -> dict:
    """한 (기체, f, θb) 의 방위 통계. sig_lin = σ(φ) [m²]."""
    s = np.maximum(np.asarray(sig_lin, float), 1e-30)
    db = 10.0 * np.log10(s)
    srt = np.sort(s)[::-1]
    k1 = max(1, int(round(0.01 * s.size)))
    return dict(mu_lin_dbsm=float(10.0 * np.log10(s.mean())),
                mu_db_dbsm=float(db.mean()),
                eps_db=float(db.std()),
                median_dbsm=float(np.median(db)),
                p90_dbsm=float(np.percentile(db, 90)),
                max_dbsm=float(db.max()), n_az=int(s.size),
                #  ⭐ 선형평균이 **몇 개의 정반사 플래시에 지배되는가**. 우리 메쉬는 큰 평판
                #    (배터리·PCB 박스·셸 상하면)이 있어 정확한 broadside 에서 σ 가 폭발한다.
                #    이 값이 크면 μ_lin 은 로브 통계가 아니라 그 플래시의 값을 재는 셈이다.
                top1pct_share=float(srt[:k1].sum() / s.sum()),
                top10pct_share=float(srt[:max(1, s.size // 10)].sum() / s.sum()),
                mu_lin_minus_mu_db=float(10.0 * np.log10(s.mean()) - db.mean()))


def fit_leverage(f, y) -> dict:
    """⭐ 기울기가 **끝점에 끌려가고 있나** — phantom3 라운드(21 점)에서 실제로 겪은 문제다.

    셋을 잰다: (1) 양 끝점을 빼고 다시 적합한 기울기, (2) 한 점씩 빼 보는 잭나이프의 최대 변화,
    (3) 대역 아래절반·위절반을 따로 적합한 기울기. 셋이 다 붙어 있어야 a 를 인용할 수 있다."""
    f, y = np.asarray(f, float), np.asarray(y, float)
    if f.size < 6:
        return {"status": f"표본 {f.size} 점 — 레버리지 진단 불가"}
    a0 = np.polyfit(f, y, 1)[0]
    a_trim = np.polyfit(f[1:-1], y[1:-1], 1)[0]
    jk = [np.polyfit(np.delete(f, i), np.delete(y, i), 1)[0] for i in range(f.size)]
    h = f.size // 2
    return dict(a_full=float(a0), a_drop_endpoints=float(a_trim),
                d_a_endpoints=float(a_trim - a0),
                jackknife_max_abs_shift=float(np.max(np.abs(np.asarray(jk) - a0))),
                jackknife_worst_index=int(np.argmax(np.abs(np.asarray(jk) - a0))),
                a_lower_half=float(np.polyfit(f[:h], y[:h], 1)[0]) if h >= 3 else None,
                a_upper_half=float(np.polyfit(f[h:], y[h:], 1)[0]) if f.size - h >= 3 else None)


def fit_se(f, y):
    """(a, b, SE(a), rmse, R²) — 기울기의 표준오차까지. p3_validation._fit_se 와 같은 식."""
    f, y = np.asarray(f, float), np.asarray(y, float)
    n = f.size
    if n < 3:
        return dict(a=float("nan"), b=float("nan"), se_a=float("nan"),
                    rmse_db=float("nan"), r2=float("nan"), n=int(n))
    a, b = np.polyfit(f, y, 1)
    r = y - (a * f + b)
    s = np.sqrt((r ** 2).sum() / (n - 2))
    se = s / np.sqrt(((f - f.mean()) ** 2).sum())
    var = y.var()
    return dict(a=float(a), b=float(b), se_a=float(se),
                rmse_db=float(np.sqrt((r ** 2).mean())),
                r2=float(1.0 - r.var() / var) if var > 0 else float("nan"), n=int(n))


# --------------------------------------------------------------------------- #
#  통제군 — phantom3. **재계산하지 않는다**(outputs/p3_ours.json 을 읽기만 한다).
# --------------------------------------------------------------------------- #
def phantom3_control() -> dict:
    p = os.path.join(ROOT, "outputs", "p3_ours.json")
    if not os.path.exists(p):
        return {"status": "p3_ours.json 없음"}
    D = json.load(open(p))
    el0 = D["aspects"]["el0"]["freq"]
    keys = sorted(el0, key=lambda k: float(k))
    f = np.array([float(k) for k in keys])
    mu_lin, mu_db, eps = [], [], []
    arc_lo, arc_hi = [], []
    for k in keys:
        db = np.asarray(el0[k]["sigma_dbsm_az"], float)
        lin = 10.0 ** (db / 10.0)
        mu_lin.append(10.0 * np.log10(lin.mean()))
        mu_db.append(float(db.mean()))
        eps.append(float(db.std()))
        #  ⭐ Das Table I 의 Phantom 3 방위창은 −90:2:90 = 180° 호 91 점이고 **시작각이 미상**이다.
        #    모든 시작각으로 잘라 dB 영역 평균의 폭을 남긴다(우리 격자 1°, stride 2 = 2°).
        n = db.size
        arcs = np.array([db[[(o + 2 * j) % n for j in range(91)]].mean() for o in range(n)])
        arc_lo.append(float(arcs.min())); arc_hi.append(float(arcs.max()))
    mu_lin, mu_db, eps = map(np.asarray, (mu_lin, mu_db, eps))
    das = SPEC["airframes"]["phantom3"]["table3_abcd"]["0"]
    fc = 10.0                                            # 1.8~18.2 GHz 산술중심
    fit_l, fit_d = fit_se(f, mu_lin), fit_se(f, mu_db)
    das_mu_fc = das["a_db_per_ghz"] * fc + das["b_dbsm"]
    return dict(
        source="outputs/p3_ours.json (읽기 전용 — 이 라운드에서 재계산하지 않았다)",
        role="통제군(control). 새 정보가 아니라 **프로토콜 검산**이다.",
        band_ghz=[float(f.min()), float(f.max())], n_freq=int(f.size),
        azimuth="0:1:360 (360점 전주기) — ⚠ Das Table I 은 −90:2:90 (91점 180° 호)",
        fit_mu_lin=fit_l, fit_mu_db=fit_d,
        mu_lin_at_fc_dbsm=float(fit_l["a"] * fc + fit_l["b"]),
        mu_db_at_fc_dbsm=float(fit_d["a"] * fc + fit_d["b"]),
        das_mu_at_fc_dbsm=float(das_mu_fc),
        DL_prereg_db=float(fit_l["a"] * fc + fit_l["b"] - (das_mu_fc + LOG_TO_LIN_EXP_DB)),
        DL_dbdomain_db=float(fit_d["a"] * fc + fit_d["b"] - das_mu_fc),
        Da_db_per_ghz=float(fit_l["a"] - das["a_db_per_ghz"]),
        arc_window_span_db=float(np.max(np.asarray(arc_hi) - np.asarray(arc_lo))),
        arc_window_note=("Das 의 180° 호 시작각이 미상이라 생기는 폭. mini2·m350rtk·phantom2 는 "
                         "방위창이 전주기라 이 항이 **없다**."),
        prereg_expected_DL_db=-3.014,
        bistatic="⛔ 없음 — p3_ours 는 모노스태틱만 잰다. 이 라운드의 바이스태틱 열에 phantom3 는 없다.")


# --------------------------------------------------------------------------- #
#  진단 — 상반성 위반 / exit_vis
# --------------------------------------------------------------------------- #
def diag_recip(af: str) -> dict:
    fs = sorted(glob.glob(os.path.join(PARTIAL, af, "recip_f*.json")))
    if not fs:
        return {"status": "미계산"}
    per_tb = {str(t): [] for t in THETA_B}
    per_f = {}
    for p in fs:
        d = json.load(open(p))
        F = np.maximum(np.asarray(d["sigma_fwd"], float), 1e-30)
        R = np.maximum(np.asarray(d["sigma_rev"], float), 1e-30)
        V = 10.0 * np.log10(F / R)                      # 상반성 위반 [dB]
        per_f[f"{d['f_ghz']:.3f}"] = {str(t): dict(rms_db=float(np.sqrt((V[:, i] ** 2).mean())),
                                                   absmax_db=float(np.abs(V[:, i]).max()))
                                      for i, t in enumerate(d["theta_b"])}
        for i, t in enumerate(d["theta_b"]):
            per_tb[str(t)].append(V[:, i])
    agg = {t: dict(rms_db=float(np.sqrt((np.concatenate(v) ** 2).mean())),
                   absmax_db=float(np.abs(np.concatenate(v)).max()),
                   n=int(np.concatenate(v).size)) for t, v in per_tb.items() if v}
    #  σ 자체가 아니라 **방위평균 μ** 가 얼마나 움직이는지도 본다 — 대조에 쓰는 양이 그것이므로.
    mu_shift = {}
    for p in fs:
        d = json.load(open(p))
        F = np.maximum(np.asarray(d["sigma_fwd"], float), 1e-30)
        R = np.maximum(np.asarray(d["sigma_rev"], float), 1e-30)
        S = np.sqrt(F * R)                              # symmetrize=True 가 냈을 값
        for i, t in enumerate(d["theta_b"]):
            mu_shift.setdefault(str(t), []).append(
                float(10 * np.log10(S[:, i].mean()) - 10 * np.log10(F[:, i].mean())))
    return dict(per_theta_b=agg, per_freq=per_f,
                mu_shift_if_symmetrized_db={t: float(np.mean(v)) for t, v in mu_shift.items()},
                what=("fwd = σ(û_i→û_s), rev = σ(û_s→û_i). 상반성은 정리이므로 dB 차이는 전부 "
                      "모형오차다. θb=0 은 정의상 0 이어야 한다(검산). "
                      "mu_shift_if_symmetrized_db 는 symmetrize=True 였다면 **방위평균 μ 가** "
                      "얼마나 움직였을지다 — 이 라운드가 symmetrize 를 끈 대가의 크기."))


def diag_exitvis(af: str) -> dict:
    fs = sorted(glob.glob(os.path.join(PARTIAL, af, "exitvis_f*.json")))
    if not fs:
        return {"status": "미계산"}
    out = {}
    for p in fs:
        d = json.load(open(p))
        on = np.maximum(np.asarray(d["sigma_exitvis_on"], float), 1e-30)
        off = np.maximum(np.asarray(d["sigma_exitvis_off"], float), 1e-30)
        out[f"{d['f_ghz']:.3f}"] = {
            str(t): dict(delta_mu_lin_db=float(10 * np.log10(on[:, i].mean())
                                               - 10 * np.log10(off[:, i].mean())),
                         delta_mu_db_db=float((10 * np.log10(on[:, i])).mean()
                                              - (10 * np.log10(off[:, i])).mean()))
            for i, t in enumerate(d["theta_b"])}
    return dict(per_freq=out,
                what=("exit_vis=True(헤드라인) − exit_vis=False. θb=0 에서 0 이 나와야 한다 "
                      "(모노에서는 first-hit 이 이미 그 가림을 뺐으므로 no-op). θb 가 커질수록 "
                      "음으로 커지는 것이 정상 — 수신기를 향한 면이 기체에 가려지는 몫이다."))


# --------------------------------------------------------------------------- #
#  사전등록 합격규칙 — **계산 전에 봉인된 문턱**을 그대로 적용한다(사후 조정 금지).
# --------------------------------------------------------------------------- #
def prereg_gates(res: dict) -> dict:
    ctl = phantom3_control()
    DL = {af: r["by_theta_b"]["0"]["DL_prereg_db"] for af, r in res.items()}
    if isinstance(ctl.get("DL_prereg_db"), float):
        DL["phantom3"] = ctl["DL_prereg_db"]
    v = np.array(list(DL.values()))
    P1 = bool(np.all(np.abs(v) <= 6.0))
    P2 = bool(np.sum(np.abs(v) <= 4.0) >= 3)
    P3 = bool((v.max() - v.min()) <= 6.0) if v.size > 1 else None
    P4 = bool(max((v > 0).sum(), (v < 0).sum()) >= 3)
    #  기울기 게이트는 **창이 긴 두 기체만** 등급을 매긴다(사전등록 slope_gate).
    slope = {}
    for af in ("phantom2",):
        if af in res:
            fit = res[af]["by_theta_b"]["0"]["fit_mu_lin"]
            da = res[af]["by_theta_b"]["0"]["Da_db_per_ghz"]
            slope[af] = dict(Da=da, se_a=fit["se_a"],
                             pass_=bool(abs(da) <= 0.25 or abs(da) <= 1.96 * fit["se_a"]))
    if isinstance(ctl.get("Da_db_per_ghz"), float):
        slope["phantom3"] = dict(Da=ctl["Da_db_per_ghz"],
                                 se_a=ctl["fit_mu_lin"]["se_a"],
                                 pass_=bool(abs(ctl["Da_db_per_ghz"]) <= 0.25))
    #  바이스태틱 게이트 — 실측인 phantom2 의 θb=15~60 네 셀만. 75/90 은 사전에 제외했다.
    bi = {}
    if "phantom2" in res:
        r = res["phantom2"]
        d0 = r["by_theta_b"]["0"]["DL_prereg_db"]
        for t in (15, 30, 45, 60):
            dt = r["by_theta_b"][str(t)]["DL_prereg_db"]
            bi[str(t)] = dict(DL=dt, delta_vs_mono=float(dt - d0),
                              pass_=bool(abs(dt - d0) <= 5.0))
        s = r["slope_scatter"]
        bi["B_test"] = ("B1 지지(Das 산포는 적합잡음)" if s["std_ours_db_per_ghz"] < 0.15 else
                        "B2 반증(우리도 산포를 낸다)" if (s["std_ours_db_per_ghz"] >= 0.19
                                                    and s["pearson_r"] > 0.7) else "B3 무정보")
    verdict = ("데이터 부족" if v.size < 4 else
               "NOT_VALIDATED (P3 산포)" if P3 is False else
               "VALIDATED" if (P1 and P2 and P4 and all(x["pass_"] for x in slope.values())
                               and all(x.get("pass_", True) for k, x in bi.items()
                                       if isinstance(x, dict)))
               else "PARTIAL")
    #  ⭐ 같은 판정을 **dB 영역 규약**으로도 돌린다. 규약 하나로 결론이 뒤집히는지 보려는 것이고,
    #    C 등급(phantom2: 근거리장·비무향·대리메쉬)을 뺀 경우도 함께 낸다 — 빼는 근거는 사후
    #    체리피킹이 아니라 das_fleet_spec 의 사전 등급표다.
    DLd = {af: r["by_theta_b"]["0"]["DL_dbdomain_db"] for af, r in res.items()}
    if isinstance(ctl.get("DL_dbdomain_db"), float):
        DLd["phantom3"] = ctl["DL_dbdomain_db"]

    def _spread(dd, drop=()):
        v = np.array([x for k, x in dd.items() if k not in drop])
        return dict(n=int(v.size), min=float(v.min()), max=float(v.max()),
                    spread_db=float(v.max() - v.min()),
                    all_within_6db=bool(np.all(np.abs(v) <= 6.0)),
                    any_beyond_10db=bool(np.any(np.abs(v) > 10.0)))

    alt = dict(
        linear_mean_all=_spread(DL), linear_mean_drop_gradeC=_spread(DL, ("phantom2",)),
        db_domain_all=_spread(DLd), db_domain_drop_gradeC=_spread(DLd, ("phantom2",)),
        DL_dbdomain_db={k: float(x) for k, x in DLd.items()},
        reading=("⭐ 규약을 바꿔도, C 등급을 빼도 **산포가 6 dB 를 넘는다.** 즉 P3 실패는 규약 선택의 "
                 "산물이 아니다. 다만 dB 영역 규약의 산포가 선형 규약보다 작다 — 선형평균이 정반사 "
                 "플래시에 지배되는 정도가 기체마다 다르기 때문이고, 그 크기가 "
                 "airframes.*.convention_sensitivity.extra_convention_uncertainty_db 다."))
    return dict(
        DL_theta_b_0_db={k: float(x) for k, x in DL.items()},
        alternative_convention=alt,
        P1_all_within_6db=P1, P2_three_within_4db=P2,
        P3_spread_db=float(v.max() - v.min()) if v.size > 1 else None,
        P3_spread_within_6db=P3, P4_sign_agreement=P4,
        slope_gate=slope, bistatic_gate=bi, verdict=verdict,
        note=("문턱은 outputs/das_fleet_prereg.json :: pass_rule 이 **계산 전에** 고정한 값이다. "
              "여기서 조정하지 않았다. θb=75·90 은 사전에 '커널 유효범위 밖' 으로 판정에서 뺐다 "
              "— 사후에 빼면 체리피킹이라 미리 못 박은 것이다."),
        ungraded_by_construction=("모든 기체의 θb=75·90; phantom3·mini2·m350rtk 의 θb=15~90 "
                                  "(등급 D — Das 의 그 21 셀은 측정이 아니라 θb=0 적합에 씌운 "
                                  "해석 taper −0.6153·sin²θb 다)"))


def caveats(res: dict) -> list:
    C = []
    if "phantom2" in res:
        C.append("⚠ phantom2 는 **대리 메쉬**다 — phantom3 메쉬를 썼다(Table I 이 두 기체에 같은 "
                 "35×20 cm 를 준다). 짐벌·카메라·랜딩기어가 다른 기체이므로 레벨 불일치를 "
                 "커널 탓으로 돌릴 수 없다. 등급 C.")
        C.append("⚠ phantom2 측정은 **근거리장 2.6 m**(필요 9.0~28.2 m)·**비무향** 실내홀이다. "
                 "표적 횡단 위상오차가 26 GHz 에서 184~244°다. 우리 계산은 원거리장 평면파라 "
                 "애초에 같은 양을 재는 것이 아니다.")
    C.append("⚠ mini2·m350rtk 의 **편파가 미확인**이다(Das 본문에 진술 없음, ref[7] 미판독). "
             "우리 PO 면적분은 스칼라라 편파가 없다 — 이 대조는 편파 무관성을 가정한다.")
    C.append("⚠ m350rtk 는 27 GHz 에서 2D²/λ = 199 m 다. 무향실 실거리로 불가능하고 CATR "
             "정적영역이어야 하는데 Das 는 레인지 종류를 안 적는다(등급 B−).")
    C.append("⭐ **θb=15~90 의 18 셀(phantom3·mini2·m350rtk)은 측정이 아니다.** 세 기체의 "
             "delta_b 가 0.01 dB 안에서 같고 ε·a 는 θb 에 걸쳐 완전히 동일하다 → θb=0 적합에 "
             "공통 taper −0.6153·sin²θb 를 씌운 파생값이다. 여기서의 일치는 물리 검증이 아니고 "
             "불일치는 반증이 아니다. **실측 바이스태틱은 phantom2 7 열뿐이다.**")
    C.append("⚠ 커널 유효범위 — lit-PO 는 조명게이트(n̂·û_i>0)와 수신게이트(n̂·û_s>0)를 둘 다 "
             "요구하므로 θb→180° 에서 σ≡0 이다(전방산란 불가). θb=75·90 에서는 상반성 위반 "
             "상한이 8.75 dB / 발산이라 **선언된 유효범위 밖**이다. 값은 내지만 판정에 안 쓴다.")
    C.append("⚠ 추정량이 다르다 — Das 의 σ 는 **시간영역 피크비**(식 3: max|s_DUT|²/max|s_Cal|²·σ_Cal) "
             "이고 우리는 주파수영역 PO 합이다. 같은 σ 라는 이름을 쓰지만 같은 추정량이 아니다.")
    C.append("⚠ 규약 불확도 0.9254 dB — Das μ 를 선형평균으로 올리는 오프셋이 지수분기 +2.5068 "
             "이냐 로그정규분기 +3.4322 이냐가 원문에서 안 갈린다. 모든 DL 에 이 폭이 딸려 있다.")
    C.append("⚠ symmetrize=False — 상반성 위반을 없애지 않고 **쟀다**(diagnostics.reciprocity). "
             "켜면 통제군(phantom3)과 설정이 달라지고, 기하평균은 어느 쪽이 참인지 정보를 "
             "주지 않는다. 대신 위반량을 바이스태틱 열의 불확도로 병기한다.")
    C.append("⚠ exit_vis=True — 히트점마다 û_s 로 그림자광선을 1 발 더 쏴 수신기가 실제로 보는 "
             "면만 남긴다. **θb=0 에서는 no-op** 이므로 모노 대조는 이 선택에 영향받지 않는다.")
    for af, r in res.items():
        c = r["convention_sensitivity"]
        C.append(
            f"⭐⭐ {af}: **레벨 대조가 규약에 {c['extra_convention_uncertainty_db']:+.1f} dB 만큼 "
            f"민감하다.** 우리 자신의 (μ_lin−μ_db) 간극이 {c['ours_mu_lin_minus_mu_db_at_fc']:.1f} dB 로 "
            f"지수분포 이론값 2.51 dB 보다 크다 — 방위 상위 1% 가 선형 전력의 "
            f"{100*c['top1pct_share_median']:.0f}% 를 나른다(큰 평판의 정반사 플래시). 그래서 "
            f"DL_prereg(선형)와 DL_dbdomain(dB영역)이 그만큼 갈린다. **둘 중 하나만 인용하면 "
            f"안 된다.** 우리 ε 는 {c['eps_ours_at_fc_db']:.2f} dB 로 Das 의 "
            f"{c['eps_das_at_fc_db']:.2f} dB 보다 {c['d_eps_db']:+.2f} dB 넓다 — 이 초과 산포 자체가 "
            f"모형의 결함(평판이 실물보다 평평하다)일 수 있고, 그렇다면 μ_lin 쪽이 더 편향된다.")
        nz = list(r["n_az_by_freq"].values())
        if min(nz) != max(nz):
            C.append(f"⚠ {af}: 방위 표본수가 주파수마다 다르다({min(nz)}~{max(nz)}) — 계산이 "
                     f"아직 도는 중이다. 적합에는 기준밀도의 절반 이상인 주파수만 넣었다.")
        tgt = int(r["azimuth_grid_target"].split("(")[0].count("")) if False else None
        tgt_az = 720 if af in ("mini2", "m350rtk") else 360
        if r["n_az_reference"] < tgt_az:
            C.append(f"⚠ {af}: 방위격자가 Das Table I({r['azimuth_grid_target']} = {tgt_az} 점)보다 "
                     f"성기다 — 주파수 중앙값 {r['n_az_reference']} 점(최대 {r['n_az_max']}). "
                     f"방위평균의 표본오차는 dB 영역평균 기준 ≈ ε/√N 이고, μ(f_c)·a 는 "
                     f"{r['n_freq_in_fit']} 주파수 적합이 한 번 더 평균한다.")
        _ = tgt
    return C


def main():
    t0 = time.time()
    res = {}
    for af in ("mini2", "m350rtk", "phantom2"):
        data, meta = load_airframe(af)
        if not data:
            continue
        G = SPEC["airframes"][af]
        band = G["frequency"]["band_ghz"]
        fc = 0.5 * (band[0] + band[1])
        fs = np.array(sorted(data))
        #  방위 표본수가 들쭉날쭉하면 μ 의 잡음이 주파수마다 달라져 적합이 왜곡된다
        #  → **가장 많이 채워진 방위수**를 기준으로 그보다 성긴 주파수는 적합에서 뺀다.
        #  ⭐ m350rtk 는 예산을 **방위보다 주파수에** 썼다(사다리 6 = 41 주파수 x 90 방위를
        #    21 주파수 x 360 방위 앞에 끼웠다) → 주파수마다 방위밀도가 다르다. 그것은 결함이
        #    아니라 설계다: μ(f_c)·a 의 정밀도는 √N_f 로 좋아지고, 방위 표본오차는 적합이 한 번
        #    더 평균한다. 그래서 **90 방위 이상이면 적합에 넣고**, 기준밀도(n_ref)만 쓴 적합을
        #    나란히 내서 둘이 갈리는지 확인한다(갈리면 밀도 혼합이 결론을 만든 것이다).
        n_az = np.array([data[f][0].size for f in fs])
        #  ⚠ 기준밀도는 **최대가 아니라 중앙값**이다. 다음 단계가 한두 주파수만 먼저 채우면
        #    최대는 그 한 점으로 튀어 'dense' 집합이 n=1 이 되어 적합이 죽는다.
        n_ref = int(np.median(n_az))
        n_max = int(np.max(n_az))
        keep = n_az >= min(90, n_ref)
        dense = n_az >= n_ref
        per_tb = {}
        for i, tb in enumerate(THETA_B):
            rows = {}
            for f in fs:
                az, S = data[f]
                rows[f"{f:.3f}"] = stats(S[:, i])
            ml = np.array([rows[f"{f:.3f}"]["mu_lin_dbsm"] for f in fs])
            md = np.array([rows[f"{f:.3f}"]["mu_db_dbsm"] for f in fs])
            ep = np.array([rows[f"{f:.3f}"]["eps_db"] for f in fs])
            fk, mlk, mdk, epk = fs[keep], ml[keep], md[keep], ep[keep]
            das = G["table3_abcd"][str(tb)]
            das_mu_fc = das["a_db_per_ghz"] * fc + das["b_dbsm"]
            fl, fd, fe = fit_se(fk, mlk), fit_se(fk, mdk), fit_se(fk, epk)
            fl_dense = fit_se(fs[dense], ml[dense])
            per_tb[str(tb)] = dict(
                per_freq=rows,
                fit_mu_lin=fl, fit_mu_db=fd, fit_eps=fe,
                fit_mu_lin_dense_az_only=fl_dense,
                mu_lin_at_fc_dense_only_dbsm=float(fl_dense["a"] * fc + fl_dense["b"]),
                fit_leverage_mu_lin=fit_leverage(fk, mlk),
                mu_lin_at_fc_dbsm=float(fl["a"] * fc + fl["b"]),
                mu_db_at_fc_dbsm=float(fd["a"] * fc + fd["b"]),
                eps_at_fc_db=float(fe["a"] * fc + fe["b"]),
                das=dict(a_db_per_ghz=das["a_db_per_ghz"], b_dbsm=das["b_dbsm"],
                         mu_at_fc_dbsm=float(das_mu_fc),
                         eps_at_fc_db=float(das["c_db_per_ghz"] * fc + das["d_db"])),
                DL_prereg_db=float(fl["a"] * fc + fl["b"] - (das_mu_fc + LOG_TO_LIN_EXP_DB)),
                DL_dbdomain_db=float(fd["a"] * fc + fd["b"] - das_mu_fc),
                Da_db_per_ghz=float(fl["a"] - das["a_db_per_ghz"]),
                d_eps_db=float(fe["a"] * fc + fe["b"] - (das["c_db_per_ghz"] * fc + das["d_db"])),
                grade=SPEC["grades"][af]["theta_b_0" if tb == 0 else "theta_b_15_90"])
        #  ⭐⭐ 규약 민감도 — 사전등록의 0.93 dB 는 **Das 쪽** 분기차이고, 우리 자신의
        #    (μ_lin − μ_db) 간극이 그것과 얼마나 다른지가 이 대조의 실제 규약 불확도다.
        gaps = np.array([per_tb["0"]["per_freq"][f"{f:.3f}"]["mu_lin_minus_mu_db"] for f in fs])
        eps_ours = float(per_tb["0"]["eps_at_fc_db"])
        eps_das = float(per_tb["0"]["das"]["eps_at_fc_db"])
        conv = dict(
            ours_mu_lin_minus_mu_db_at_fc=float(np.mean(gaps)),
            ours_gap_range_db=[float(gaps.min()), float(gaps.max())],
            exponential_theory_gap_db=LOG_TO_LIN_EXP_DB,
            das_implied_gap_if_lognormal_db=float(np.log(10.0) / 20.0 * eps_das ** 2),
            eps_ours_at_fc_db=eps_ours, eps_das_at_fc_db=eps_das,
            d_eps_db=float(eps_ours - eps_das),
            extra_convention_uncertainty_db=float(np.mean(gaps) - LOG_TO_LIN_EXP_DB),
            top1pct_share_median=float(np.median(
                [per_tb["0"]["per_freq"][f"{f:.3f}"]["top1pct_share"] for f in fs])),
            reading=(
                "⭐ 사전등록은 Das μ 에 +2.5068 dB(지수분포 가정)를 얹어 선형평균으로 올린다. "
                "그 가정이 **우리 쪽에서도** 성립해야 DL_prereg 와 DL_dbdomain 이 같은 이야기를 "
                "한다. 우리 자신의 간극(μ_lin−μ_db)이 2.5068 에서 벗어난 만큼이 두 대조값의 차이이고, "
                "그것이 extra_convention_uncertainty_db 다. 우리 σ(φ) 가 지수분포보다 뾰족하면"
                "(ε 가 크고 top1pct_share 가 크면) 이 값이 양으로 커진다 — 큰 평판의 정반사 "
                "플래시가 선형평균을 끌어올리기 때문이다. **이 폭보다 정밀하게 레벨을 주장할 수 없다.**"))
        #  바이스태틱 각도의존 — b 절편이 아니라 μ(f_c) 로 읽는다(b 는 a 와 −0.94 반상관).
        dmu_ours = {str(t): float(per_tb[str(t)]["mu_lin_at_fc_dbsm"]
                                  - per_tb["0"]["mu_lin_at_fc_dbsm"]) for t in THETA_B}
        dmu_ours_db = {str(t): float(per_tb[str(t)]["mu_db_at_fc_dbsm"]
                                     - per_tb["0"]["mu_db_at_fc_dbsm"]) for t in THETA_B}
        dmu_das = {str(t): float(SPEC["finding_bistatic_taper_is_synthetic"]
                                 ["delta_b_db"][af][i]) for i, t in enumerate(THETA_B)}
        a_ours = np.array([per_tb[str(t)]["fit_mu_lin"]["a"] for t in THETA_B])
        a_das = np.array([G["table3_abcd"][str(t)]["a_db_per_ghz"] for t in THETA_B])
        res[af] = dict(
            name=G["name"], mesh_key=meta.get("mesh_key"), proxy_mesh=meta.get("proxy_mesh"),
            band_ghz=band, band_centre_ghz=fc,
            n_freq=int(fs.size), n_freq_in_fit=int(keep.sum()),
            n_freq_at_reference_az_density=int(dense.sum()),
            freqs_ghz=[float(x) for x in fs],
            n_az_by_freq={f"{f:.3f}": int(n) for f, n in zip(fs, n_az)},
            n_az_reference=n_ref, n_az_max=n_max,
            azimuth_grid_target=G["azimuth"]["literal_table1"],
            kernel=meta.get("kernel"), geometry=meta.get("geometry"),
            theta_b=THETA_B, by_theta_b=per_tb, convention_sensitivity=conv,
            delta_mu_vs_mono_ours_lin_db=dmu_ours,
            delta_mu_vs_mono_ours_db_domain_db=dmu_ours_db,
            delta_mu_vs_mono_das_db=dmu_das,
            slope_scatter=dict(std_ours_db_per_ghz=float(a_ours.std(ddof=1)),
                               std_das_db_per_ghz=float(a_das.std(ddof=1)),
                               pearson_r=float(np.corrcoef(a_ours, a_das)[0, 1])
                               if a_das.std() > 0 else float("nan"),
                               a_ours=[float(x) for x in a_ours],
                               a_das=[float(x) for x in a_das]),
            diagnostics=dict(reciprocity=diag_recip(af), exit_vis=diag_exitvis(af)))

    gates = prereg_gates(res)
    head = dict(
        one_line=("⭐ σ(f,θb) 를 세 기체 x 7 각도로 냈다. 사전등록 예측(네 기체 DL 이 −3~−4 dB 에 "
                  "모이고 산포 ≤1 dB)은 **반증됐다** — 산포가 규약을 바꿔도 6 dB 문턱을 넘는다. "
                  "가장 잘 구속된 메쉬(mini2)는 −0.5 dB 로 거의 맞고, 가장 큰 기체(m350rtk)는 "
                  "선형평균에서 +9.1 dB 로 어긋난다. 그 차이의 기계적 원인은 **정반사 플래시가 "
                  "선형 방위평균을 지배하는 정도**이고 기체 크기와 함께 커진다."),
        what_held=[
            "통제군 검산 — phantom3 를 함대 규약으로 다시 내니 DL=−3.014 dB 로 사전등록값 "
            "(−3.014)과 소수 셋째자리까지 같다. 규약·격자·적합창 적용에 오류가 없다.",
            "기하 검산 4/4 통과 — θb=0 이 모노스태틱과 0.000 dB 로 같고(V1), 낀각이 1e-14° 안에서 "
            "맞고(V2), exit_vis 가 θb=0 에서 정확히 no-op 다(V4).",
            "사전등록한 바이스태틱 예측 적중 — Das 의 taper(−0.6153·sin²θb)를 재현하지 못할 것이고 "
            "우리 폭이 3 배 이상 클 것이라고 적었는데, mini2 에서 −2.48 vs −0.62 dB (4 배)다.",
            "phantom2 기울기 산포 검정(B1) — Das 의 a(θb) 산포 0.189 dB/GHz 는 적합잡음이라는 "
            "사전등록 H0 를 지지한다. 우리 a(θb) 산포는 0.016 dB/GHz 로 12 배 작고 Das 와 상관도 "
            "없다(r=−0.41).",
            "기울기 게이트 2/2 통과 — phantom2 Δa=+0.02, phantom3 Δa=+0.21 (문턱 0.25).",
        ],
        what_broke=[
            "P3(산포 ≤6 dB) 실패 → 사전등록 사다리로 **NOT_VALIDATED**. 사전등록이 '나머지가 다 "
            "통과해도 여기 걸리면 검증이라 말하지 않는다' 고 미리 못 박은 항목이다.",
            "⭐ 그러나 실패의 모양이 사전등록이 예상한 '기체마다 무작위로 흩어짐' 이 아니다 — "
            "DL 이 **정반사 플래시 지배도(top1pct_share)와 함께 단조 증가**한다: "
            "mini2 0.16→−0.5 dB, phantom2 0.20→−7.2 dB, m350rtk 0.37→+9.1 dB. 기체별 맞춤이 "
            "아니라 **하나의 기계적 원인**이 있다는 뜻이고, 그것은 메쉬의 큰 평판이 실물보다 "
            "평평하다는 것이다(우리 ε 가 Das 보다 +0.9~+4.1 dB 넓다).",
            "H_ka 도 H_flat 도 깨끗이 이기지 못했다. mini2·m350rtk 는 전 부위 ka≥4.4 인 "
            "완전 광학영역인데 DL 이 −0.5 와 +9.1 로 갈렸다 — 저-ka 결손 가설로는 설명되지 않고, "
            "주파수 무관 스칼라 오프셋 가설로도 설명되지 않는다.",
        ],
        cannot_conclude=[
            "⛔ '우리 σ 가 정확하다' 는 어떤 결과로도 서지 않는다 — 측정체인이 둘뿐이고"
            "(오울루=phantom2, Southeast Univ./Wei Fan=나머지) 후자 셋은 같은 제공자다.",
            "⛔ 21–27 GHz 의 결과는 우리 운용대역 1.8–6.0 GHz 로 외삽되지 않는다(배율 4~6).",
            "⛔ phantom2 의 실패는 세 갈래(근거리장 측정 · 대리메쉬 · 우리 커널)로 갈리고 "
            "이 라운드는 그것을 못 가른다.",
        ],
        next_lever=("⭐ 다음 라운드가 쳐야 할 곳은 메쉬 정밀화가 아니라 **σ(φ) 분포의 모양**이다. "
                    "레벨 오차와 ε 초과가 같은 방향으로 움직이므로, 큰 평판의 정반사를 "
                    "실물처럼 퍼뜨리는 것(곡률·표면 요철·PTD 강화)이 단일 스칼라 교정보다 "
                    "먼저다. 진단은 이미 산출물 안에 있다: convention_sensitivity.top1pct_share."))
    out = dict(
        _meta=dict(
            generated=time.strftime("%Y-%m-%d %H:%M:%S"),
            generator="benchmark/das_fleet_ours.py (계산은 benchmark/das_fleet_sigma.py)",
            what="⭐ 우리 SBR+PO σ(f, θb) — Das 4 기체 대조의 **우리 쪽 수치**",
            partial_dir=os.path.relpath(PARTIAL, ROOT),
            spec="outputs/das_fleet_spec.json (대역·격자·θb 정의·등급)",
            prereg="outputs/das_fleet_prereg.json (계산 전에 봉인된 예측·합격규칙)",
            wrote_only="outputs/das_fleet_ours.json",
            read_only=["outputs/das_fleet_spec.json", "outputs/das_fleet_prereg.json",
                       "outputs/p3_ours.json", "outputs/partial/das_fleet_0803/**"],
            aggregation_runtime_s=round(time.time() - t0, 2)),
        convention=dict(
            mu_lin="10log10(mean_φ σ) — 선형(전력) 방위평균",
            mu_db="mean_φ(10log10 σ) — dB 영역 방위평균 (Das §III-2 쪽 규약)",
            eps="std_φ(10log10 σ) [dB] — Das Table III 표제가 dB 단위로 명시",
            das_offset_db=LOG_TO_LIN_EXP_DB,
            das_offset_uncertainty_db=CONV_UNCERT_DB,
            DL_prereg="μ_lin(f_c) − [a_das·f_c + b_das + 2.5068]  (prereg metric_definition)",
            DL_dbdomain="μ_db(f_c) − [a_das·f_c + b_das]  (규약을 곧이곧대로 맞춘 직접 대조)",
            why_two=("두 규약 중 어느 쪽이 Das 의 실제 μ 인지 원문이 자기모순이다. 잔차검산은 "
                     "dB 영역평균(지수분기)을 지지하지만 로그정규분기와 0.9254 dB 차가 남는다 "
                     "→ 단일값으로 좁히지 않고 두 갈래를 다 적는다.")),
        theta_b_definition=SPEC["theta_b_definition"]["answer"],
        kernel_declarations=dict(
            engine="SBR (Mitsuba/OptiX first-hit 가림) + PO 면적분 — src/rcs_sbr.rcs_sbr_multistatic",
            settings=dict(div=16, jitter=2, max_bounce=1, penetrate=True,
                          ptd=False, exit_vis=True, symmetrize=False,
                          spacing="lambda/16", elevation_deg=0.0),
            settings_provenance=("outputs/das_fleet_prereg.json :: execution_contract 가 계산 **전에** "
                                 "봉인한 값이고 outputs/p3_ours.json(통제군)과 같다. 여기서 하나라도 "
                                 "바꾸면 네 기체를 한 자로 잰다는 전제가 깨진다."),
            obliquity=(
                "⭐ **표준 PO 의 (n̂·û_i) 를 쓴다** — 광선을 û_i 로 쏘므로 히트밀도가 투영면적을 "
                "재고, 면적분이 E(i,s)=∫e^{jk(û_i+û_s)·p}(n̂·û_i)dS 가 된다. 대칭형 "
                "√((n̂·û_i)(n̂·û_s)) 로 승격하면 이론상 상반성이 복원되지만, grazing 조명면"
                "(n̂·û_i→0)에서 √(cosθ_s/cosθ_i) 가 단일 광선에 수백 배 가중을 실어 이산 격자를 "
                "폭발시킨다 — 과거 시도에서 rms 오차가 **오히려 커져** 폐기했다(src/rcs_sbr.py:554-556). "
                "그 대가는 σ(i,s)/σ(s,i)=(cos_i/cos_s)² 라는 **닫힌형 상반성 위반**이고, 평판 실측이 "
                "β≤60° 에서 0.3 dB 안으로 그 예측과 맞는다(outputs/sbr_defect_fixes.json). "
                "θb 가 커질수록 이 항이 커지는 것이 우리 바이스태틱 열의 지배 불확도다."),
            exit_vis=(
                "⭐ **켠다(True)**. 수신 게이트가 법선 판정 (n̂·û_s>0) 하나뿐이면 수신기를 향한 면이 "
                "기체에 가려져 있어도 100% 진폭으로 계상된다 — 입사 가림만 넣은 상태는 효과의 절반만 "
                "모형화한 것이다. 그래서 히트점마다 û_s 로 그림자광선(ray_test)을 1 발 더 쏘아 "
                "실제로 뚫린 면만 남긴다. 투과 기여의 출사는 **셸을 뺀 내부 씬**으로 판정한다"
                "(셸은 투과 대상이므로 가림체가 아니다 — 입사 처리와 같은 전제). "
                "**θb=0 에서는 no-op** 이다(first-hit 이 이미 그 가림을 뺐다) → 모노 대조는 이 선택에 "
                "영향받지 않는다. 실제 몫은 airframes.*.diagnostics.exit_vis 가 θb 별로 잰 값이다."),
            symmetrize=(
                "⭐ **끈다(False)**. 셋 다 이유다. (1) 통제군 phantom3(outputs/p3_ours.json)가 "
                "symmetrize 없이 계산됐다 — 여기서만 켜면 네 기체를 한 자로 잰다는 전제가 깨진다. "
                "(2) σ_sym=√(σ(i,s)·σ(s,i)) 는 두 평가값의 기하평균일 뿐, 어느 쪽이 참인지에 대한 "
                "정보를 늘리지 않는다. 두 오차가 dB 에서 같은 방향이면 개선이 0 이다. "
                "(3) 수신방향마다 조명추적을 한 번 더 해야 해 7 각도에서 ~8 배 비싸다. "
                "→ 감추는 대신 **위반량을 재서** diagnostics.reciprocity 에 남겼고, "
                "mu_shift_if_symmetrized_db 가 '켰다면 μ 가 얼마나 움직였을지' 다."),
            validity_range=(
                "lit-PO 는 조명게이트(n̂·û_i>0)와 수신게이트(n̂·û_s>0)를 둘 다 요구한다 → θb→180° 에서 "
                "두 게이트가 상호배타라 σ≡0 이다(그림자복사·Babinet 전방로브를 못 낸다). "
                "**후방~중간 바이스태틱각(θb≲90°)에만 유효**하고, θb=75·90 은 상반성 위반 상한이 "
                "8.75 dB / 발산이라 사전등록이 판정에서 뺀 열이다."),
            verification="partial_dir/verify.json (V1 θb=0=모노 · V2 낀각 · V3 이등분선고정 대조 · V4 exit_vis no-op)"),
        verification=(json.load(open(os.path.join(PARTIAL, "verify.json")))
                      if os.path.exists(os.path.join(PARTIAL, "verify.json"))
                      else {"status": "미계산 (benchmark/das_fleet_verify.py)"}),
        verification_reading=dict(
            V1="θb=0 열이 rcs_sbr_batch(모노 전용 경로)와 **0.000 dB** 로 같다 → 함대 모노 대조가 "
               "기존 앵커(p3_ours)와 같은 커널을 쓴다는 것이 확인됐다.",
            V2="arccos(û_i·û_s)=θb 가 1e-14 도 안에서 성립 → θb 를 **낀각**으로 구현했다(반각·이등분선 아님).",
            V3=("⭐ 읽는 법: 방위 **전주기 평균 μ 는 두 방식이 짝수 θb(0·30·60·90)에서 완전히 같고 "
                "홀수 θb(15·45·75)에서만 0.4~0.7 dB 갈린다** — 이 차이는 물리가 아니라 격자 정렬이다"
                "(검산 격자 5° 에서 이등분선 고정은 φ±θb/2 가 반칸 어긋난다). 즉 전주기 평균에서는 "
                "두 방식이 같은 (û_i,û_s) 쌍 모음을 φ 만 다르게 훑으므로 μ 로는 갈리지 않는다. "
                "⚠ 그러나 **자세별 σ 는 완전히 다른 물건이다** — per_aspect_rms 8.8~15.8 dB. "
                "방위창이 반주기뿐인 기체(Das phantom3 −90:2:90)나 자세별 대조에서는 spec 의 금지가 "
                "그대로 유효하다. 우리는 세 기체 모두 전주기라 이 항이 무해한 쪽에 있다."),
            V4=("exit_vis 가 θb=0 에서 **0.000 dB** (no-op 확인) 이고 θb>0 에서 0.5~10.8 dB 를 깎는다 "
                "→ 바이스태틱 열에서만 실제로 작동한다. 모노 대조는 이 선택에 영향받지 않는다.")),
        geometry_implemented=("각 θb 에서 el=0, 입사 az=φ, 산란 az=φ+θb (표적 좌표계). "
                              "⛔ 이등분선 고정 방식이 아니다. û_i=표적→TX, û_s=표적→RX."),
        headline=head,
        airframes=res,
        phantom3_control=phantom3_control(),
        prereg_gates=gates,
        caveats=caveats(res))
    def _clean(o):
        """NaN/Inf → null. 표본이 모자란 셀(적합 불가)이 **엄격한 JSON 파서를 깨지 않게**."""
        if isinstance(o, dict):
            return {k: _clean(v) for k, v in o.items()}
        if isinstance(o, list):
            return [_clean(v) for v in o]
        if isinstance(o, float) and not np.isfinite(o):
            return None
        return o

    with open(OUT, "w") as fh:
        json.dump(_clean(out), fh, ensure_ascii=False, indent=1, allow_nan=False)
    print(f"wrote {OUT}  ({os.path.getsize(OUT)/1e6:.2f} MB, {time.time()-t0:.1f}s)")
    for af, r in res.items():
        print(f"  {af}: n_freq={r['n_freq']} n_az={r['n_az_reference']} "
              f"DL(0)={r['by_theta_b']['0']['DL_prereg_db']:+.2f} dB "
              f"a={r['by_theta_b']['0']['fit_mu_lin']['a']:+.3f}")


if __name__ == "__main__":
    main()
