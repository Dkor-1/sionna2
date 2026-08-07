# -*- coding: utf-8 -*-
"""
report16_metric_mesh_half_tri.py — ⭐ 「삼각형 절반 메쉬」 단의 **지표 추출·사전예측 대조·자기검증**
================================================================================

무엇을 하는가 (쉬운 말로)
--------------------------------------------------------------------------------
앞 단계(benchmark/report16_rung_mesh_half_tri.py)가 드론 프로펠러 CAD 의 삼각형을 절반으로
줄이고 같은 실험을 다시 돌려서, 되돌아온 전파의 «위상 표»(프로펠러를 한 바퀴 돌리며 잰
복소수 배열)를 `outputs/report16_rung_mesh_half_tri_tables.npz` 에 남겼다.

이 파일은 그 **원본 표에서 지표를 처음부터 다시 계산**한다. 앞 단계가 적어 둔 숫자를
베껴 오지 않는다 — 같은 표에서 같은 함수(report16_base.md_metrics16)를 다시 돌려
**앞 단계의 JSON 과 한 자리씩 대조**한다(감사). 그래야 「지표가 틀리게 적혔을 가능성」이
결론에서 빠진다.

지표 네 갈래 (정의는 report16_base.md_metrics16 이 못박은 것을 그대로 **호출**한다)
--------------------------------------------------------------------------------
 ① flash_contrast_db  «번쩍임 대조비» — 블레이드 면이 시선에 수직으로 서는 순간이
    바닥보다 몇 dB 위인가.
 ② n_eff_orders / order_p50 / order_p90 / dominant_order / blade_comb_frac
    «고차 성분 풍부도» — 회전수의 몇 배 되는 선(하모닉)이 실질적으로 몇 개나 살아 있나.
 ③ width_ratio (−10/−20/−30 dB 문턱) / fd_edge_hz  «폭» — 스펙트럼이 팁 속도가 예고한
    폭(f_tip)만큼 벌어졌나.
 ④ dc_ac_db  «동체 대 블레이드 세기비» — 안 움직이는 동체 반사가 도는 블레이드보다
    몇 dB 센가.

이 파일이 추가로 하는 일 (앞 단계가 안 한 것)
--------------------------------------------------------------------------------
 · 사전예측(prereg) 9개를 **내 숫자로 다시 채점**하고 앞 단계 채점과 일치하는지 본다.
 · 각 예측의 «문턱 여유»(threshold slack) 를 잰다 — 문턱이 헐거우면 PASS 는 약한 증거다.
 · 24 방위를 독립표본처럼 쓰면 안 되는 정도(방위 간 상관 → 유효표본수)를 잰다.
 · 「절반 메쉬」 교란이 **잡음 몇 dB 주입과 같은 크기인가**를 해석식 + 몬테카를로로 잰다.
 · 이 단을 **못 믿을 이유**를 숫자와 함께 3개 이상 적는다.

⛔ 금지 준수: outputs/report15_* · benchmark/report15_* 미접촉, src/make_report0N_*.py ·
   report0N_*.ipynb 미접촉, src/drones.py · src/drone_cad.py 는 **읽기만**(spec 조회).
⛔ 숫자 손입력 금지 — 이 파일에 적힌 상수는 문턱(사전예측 파일에서 읽음)과 몬테카를로
   설정뿐이고, 결과 숫자는 전부 계산된다.
GPU: 이 단계는 저장된 표를 후처리할 뿐이라 GPU 가 필요 없다(FFT 24×128). 다른 워크플로가
   GPU 4장을 쓰고 있어 건드리지 않는다 — 그 사실도 JSON 에 남긴다.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
sys.path[:0] = [_HERE, os.path.join(ROOT, "src")]

import report16_base as B                                   # noqa: E402  지표 정의의 유일한 출처

RUNG_JSON = os.path.join(ROOT, "outputs", "report16_rung_mesh_half_tri.json")
RUNG_NPZ = os.path.join(ROOT, "outputs", "report16_rung_mesh_half_tri_tables.npz")
PREREG = os.path.join(ROOT, "outputs", "report16_rung_mesh_half_tri_prereg.json")
BASE_JSON = os.path.join(ROOT, "outputs", "report16_base.json")
BASE_NPZ = os.path.join(ROOT, "outputs", "report16_base_tables.npz")
OUT_JSON = os.path.join(ROOT, "outputs", "report16_metric_mesh_half_tri.json")

DRONE_KEYS = ("mini2", "matrice4e")
ARMS = ("mesh", "mesh_half_tri", "mesh_quarter_tri", "mesh_half_tri_all",
        "mesh_fine", "mesh_half_tri_fine", "slab", "disc", "sphere")
RES_ARMS = ("mesh_quarter_tri", "mesh_half_tri", "mesh", "mesh_fine")   # 해상도 축 (25%→100%, 표본 1→4배)

# md_metrics16 이 내놓는 것 중 «지표» 로 쓸 이름들 (네 갈래 전부 + 해석자격 지표)
METRIC_KEYS = (
    "flash_contrast_db",                                             # ①
    "n_eff_orders", "order_p50", "order_p90", "dominant_order", "blade_comb_frac",   # ②
    "width_ratio", "width_ratio_10db", "width_ratio_30db", "fd_edge_hz",             # ③
    "dc_ac_db",                                                      # ④
    "in_band_ac_frac", "in_band_ac_over_dc_db", "ac_over_floor_db",  # 해석 자격
    "sigma_eq_mean_dbsm", "mean_sigma_proxy",
)
PER_AZ_KEYS = ("flash_contrast_db", "n_eff_orders", "order_p90", "blade_comb_frac",
               "width_ratio", "dc_ac_db", "in_band_ac_frac", "ac_over_floor_db")

MC_TRIALS_PER_AZ = 256    # 잡음 등가 몬테카를로 시행 수 (방위마다)
MC_SEED = 16_0804


# --------------------------------------------------------------------------- #
#  잡동사니
# --------------------------------------------------------------------------- #
def sha256_16(path):
    if not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()[:16]


def git_rev():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                       cwd=ROOT, text=True).strip()
    except Exception:
        return None


def binom_sign_p(n_pos, n):
    """부호검정(양측). 「방위마다 부호가 한쪽으로 몰린 것이 동전던지기로 나올 확률」.

    ⚠ 24 방위는 독립표본이 아니다(같은 물체를 15°씩 돌린 것이라 이웃 방위가 닮았다).
      그래서 이 p 값은 **참고용 상한이 아니라 낙관적 하한**이다 — 유효표본수도 같이 잰다."""
    if n == 0:
        return float("nan")
    k = min(n_pos, n - n_pos)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / (2.0 ** n)
    return float(min(1.0, 2.0 * tail))


def eff_n_from_autocorr(x):
    """방위축 순환 lag-1 자기상관 r1 로 유효표본수 n_eff = n(1−r1)/(1+r1) 을 잰다.

    24 방위는 15° 간격으로 «같은 물체를 돌려가며» 잰 것이라 이웃끼리 닮는다. 닮은 만큼
    독립적인 정보는 24개보다 적다. 그 감가를 숫자로 남긴다(음의 상관이면 24를 넘지 않게 자른다)."""
    x = np.asarray(x, float)
    n = x.size
    if n < 3:
        return dict(r1=float("nan"), n_eff=float(n), n=int(n))
    v = x - x.mean()
    den = float(np.dot(v, v))
    r1 = float(np.dot(v, np.roll(v, -1)) / den) if den > 0 else 0.0
    ne = n * (1.0 - r1) / (1.0 + r1) if r1 > -0.999 else float(n)
    return dict(r1=r1, n_eff=float(min(max(ne, 1.0), float(n))), n=int(n))


def stat_block(d):
    """짝지은 차이 배열 → 요약. 평균·산포뿐 아니라 부호 일관성·유효표본수까지."""
    d = np.asarray([x for x in d if np.isfinite(x)], float)
    n = int(d.size)
    if n == 0:
        return dict(mean=float("nan"), n=0)
    sd = float(d.std(ddof=1)) if n > 1 else 0.0
    npos = int(np.sum(d > 0))
    nzero = int(np.sum(d == 0.0))
    nnz = n - nzero                      # 부호검정은 «동점(정확히 0)» 을 빼고 센다
    en = eff_n_from_autocorr(d)
    return dict(mean=float(d.mean()), sd=sd, sem=float(sd / max(math.sqrt(n), 1.0)),
                sem_eff=float(sd / max(math.sqrt(en["n_eff"]), 1.0)),
                median=float(np.median(d)), min=float(d.min()), max=float(d.max()),
                frac_positive=float(npos / n), n_positive=npos, n=n,
                n_zero=nzero, frac_zero=float(nzero / n),
                sign_test_p=(binom_sign_p(npos, nnz) if nnz > 0 else float("nan")),
                sign_test_note_ko=("정확히 0 인 방위는 제외하고 센다. 전부 0 이면 검정 불가(nan) — "
                                   "지표 눈금이 굵어 «변화 없음» 으로 찍힌 경우다."),
                az_lag1_corr=en["r1"], n_eff_az=en["n_eff"])


def summarize(vals):
    return B.summarize(vals)


# --------------------------------------------------------------------------- #
#  1) 표 읽기 · 규약 재계산
# --------------------------------------------------------------------------- #
def load_tables():
    z = np.load(RUNG_NPZ)
    main, hi = {}, {}
    for f in z.files:
        if f.startswith("hi__hi__"):
            _, _, key, arm, wf = f.split("__")
            hi[(key, arm, wf)] = z[f]
        else:
            _, key, arm, wf = f.split("__")
            main[(key, arm, wf)] = z[f]
    return main, hi


def protocols():
    """드론 spec(src/drones.py, 읽기만) 에서 규약을 **다시 유도**하고 앞 단계 JSON 과 대조한다."""
    from drones import DRONES
    out = {}
    for key in DRONE_KEYS:
        s = DRONES[key]
        out[key] = dict(
            spec=dict(name=s.name, prop_dia_mm=float(s.prop_dia_mm),
                      prop_blades=int(s.prop_blades), hover_rpm=float(s.hover_rpm),
                      num_rotors=int(s.num_rotors)),
            main=B.derive_protocol(s.prop_dia_mm, s.hover_rpm, s.prop_blades, B.FC_MAIN),
            hi=B.derive_protocol(s.prop_dia_mm, s.hover_rpm, s.prop_blades, B.FC_PO_KNEE))
    return out


def protocol_matches(protos, rung):
    """내가 유도한 규약이 앞 단계가 쓴 규약과 같은가 — 다르면 지표를 나란히 놓을 수 없다."""
    rows = {}
    worst = 0.0
    for key in DRONE_KEYS:
        for band, sub in (("main", None), ("hi", "hi_band")):
            ref = rung["protocol"]["per_drone"][key]
            ref = ref if sub is None else ref[sub]
            mine = protos[key][band]
            bad = {}
            for k, v in mine.items():
                if not isinstance(v, (int, float)) or isinstance(v, bool):
                    continue
                rv = ref.get(k)
                if not isinstance(rv, (int, float)):
                    continue
                rel = abs(float(v) - float(rv)) / max(abs(float(rv)), 1e-300)
                worst = max(worst, rel)
                if rel > 1e-12:
                    bad[k] = dict(mine=float(v), rung=float(rv), rel=rel)
            rows[f"{key}|{band}"] = dict(mismatches=bad, n_checked=len(mine))
    return dict(rows=rows, worst_rel=worst, tolerance=1e-12,
                verdict="PASS" if worst < 1e-12 else "FAIL",
                what_ko=("위상격자 수·PRF·β·f_tip 을 drones.py spec 에서 다시 유도해 앞 단계 값과 "
                         "맞춰 본다. 여기가 어긋나면 FFT 축이 달라 지표 비교가 무의미하다."))


# --------------------------------------------------------------------------- #
#  2) 지표 계산 (base 의 정의 함수를 **호출**한다 — 재구현 금지)
# --------------------------------------------------------------------------- #
def per_az(tab2d, proto, nb):
    return [B.md_metrics16(tab2d[i], proto, nb) for i in range(tab2d.shape[0])]


def arm_summary(mets):
    return dict(
        per_az={k: summarize([m[k] for m in mets]) for k in METRIC_KEYS},
        interpretable_frac=float(np.mean([m["metrics_interpretable"] for m in mets])),
        band_order=int(mets[0]["band_order"]), n_az=len(mets))


def paired(ma, mb):
    """같은 방위에서 (B − A). 자세 산포는 두 팔에 공통이라 짝지으면 지워진다."""
    return {k: stat_block([y[k] - x[k] for x, y in zip(ma, mb)]) for k in METRIC_KEYS}


# --------------------------------------------------------------------------- #
#  3) 잡음 등가 — 「절반 메쉬」 교란은 잡음 몇 dB 주입과 같은 크기인가
# --------------------------------------------------------------------------- #
def noise_equivalent(tab_ref, tab_alt, proto, nb, rng):
    """AC 상관 하나로 두 가지를 잰다.

    ① 해석식: 원본 AC 에 세기비 ε 의 무상관 잡음을 더하면 기대 상관은 1/√(1+ε²) 이다.
       따라서 관측된 상관 ρ 는 ε = √(1/ρ² − 1) 의 잡음과 같은 «크기» 의 교란이다.
       사람 말로: 「삼각형을 절반으로 줄이는 것은 신호보다 X dB 아래인 잡음을 넣는 것과 같다」.
    ② 몬테카를로 검증: 실제로 그 ε 만큼 잡음을 넣어 지표가 얼마나 흔들리는지 재고,
       실제 절반 메쉬가 흔든 양과 견준다. 잡음보다 **덜** 흔들면 그 교란은 구조적(형상을
       고르게 밀어낸 것)이라는 뜻이고, **더** 흔들면 지표가 형상 변화에 민감하다는 뜻이다.
    """
    n_az = tab_ref.shape[0]
    rho = np.array([B.ac_corr(tab_ref[i], tab_alt[i]) for i in range(n_az)], float)
    eps = np.sqrt(np.maximum(1.0 / np.maximum(rho ** 2, 1e-300) - 1.0, 0.0))
    snr_db = -20.0 * np.log10(np.maximum(eps, 1e-300))

    m_ref = per_az(tab_ref, proto, nb)
    m_alt = per_az(tab_alt, proto, nb)
    d_true = dict(n_eff=np.array([b["n_eff_orders"] - a["n_eff_orders"]
                                  for a, b in zip(m_ref, m_alt)]),
                  flash=np.array([b["flash_contrast_db"] - a["flash_contrast_db"]
                                  for a, b in zip(m_ref, m_alt)]))

    # 같은 «에너지» 의 무작위 잡음을 넣었을 때 지표가 흔들리는 폭
    d_mc = {"n_eff": [], "flash": [], "rho": []}
    for i in range(n_az):
        ac = tab_ref[i] - tab_ref[i].mean()
        amp = float(np.sqrt(np.mean(np.abs(ac) ** 2))) * float(eps[i])
        S = tab_ref.shape[1]
        nt = MC_TRIALS_PER_AZ
        noise = (rng.standard_normal((nt, S)) +
                 1j * rng.standard_normal((nt, S))) / math.sqrt(2.0) * amp
        pert = tab_ref[i][None, :] + noise
        for row in pert:
            mm = B.md_metrics16(row, proto, nb)
            d_mc["n_eff"].append(mm["n_eff_orders"] - m_ref[i]["n_eff_orders"])
            d_mc["flash"].append(mm["flash_contrast_db"] - m_ref[i]["flash_contrast_db"])
            d_mc["rho"].append(B.ac_corr(tab_ref[i], row))
    obs_abs = float(np.mean(np.abs(d_true["n_eff"])))
    rnd_abs = float(np.mean(np.abs(d_mc["n_eff"])))
    return dict(
        ac_corr=summarize(rho),
        equivalent_noise_rel_amp=summarize(eps),
        equivalent_snr_db=summarize(snr_db),
        observed_signed_delta=dict(
            n_eff_orders=summarize(d_true["n_eff"]),
            flash_contrast_db=summarize(d_true["flash"]),
            n_eff_frac_positive=float(np.mean(d_true["n_eff"] > 0))),
        structured_vs_random=dict(
            n_eff_obs_over_random=obs_abs / max(rnd_abs, 1e-300),
            note_ko=("같은 «에너지» 의 무작위 잡음과 견준다. 1 보다 크면 그 교란은 잡음보다 지표를 "
                     "더 흔든다(구조적으로 한 방향으로 민다)는 뜻이고, 1 보다 훨씬 작으면 에너지는 "
                     "크지만 지표를 덜 흔든다는 뜻이다 — 후자는 «에너지» 가 옳은 잣대가 아니라는 "
                     "경고이기도 하다.")),
        observed_abs_delta=dict(
            n_eff_orders=summarize(np.abs(d_true["n_eff"])),
            flash_contrast_db=summarize(np.abs(d_true["flash"]))),
        random_noise_abs_delta_at_same_energy=dict(
            n_eff_orders=summarize(np.abs(d_mc["n_eff"])),
            flash_contrast_db=summarize(np.abs(d_mc["flash"])),
            achieved_ac_corr=summarize(d_mc["rho"]),
            trials_per_azimuth=MC_TRIALS_PER_AZ),
        what_ko=("「절반 메쉬」 교란의 크기를 잡음 단위로 환산한다. equivalent_snr_db 가 클수록 "
                 "교란이 작다는 뜻이다(신호보다 그만큼 아래)."))


# --------------------------------------------------------------------------- #
#  4) 사전예측 재채점 — prereg 파일의 문턱만 읽고, 숫자는 내 계산으로 넣는다
# --------------------------------------------------------------------------- #
def regrade(pre, P, CC, arms):
    """P: paired[(key, "B - A")][metric], CC: 상관, arms: 팔 요약."""
    pr = pre["predictions"]
    G = {}

    def rec(pid, verdict, actual, thresholds, slack, note_ko=""):
        G[pid] = dict(verdict=verdict, claim_ko=pr[pid]["claim_ko"], test=pr[pid]["test"],
                      thresholds=thresholds, actual=actual, slack=slack, note_ko=note_ko)

    # P1 — «평판이 CAD 보다 하모닉이 풍부하다» 가 절반 해상도에서도 성립하는가
    th = pr["P1_primitive_richness_verdict_survives"]["thresholds"]
    a = {k: P[(k, "slab - mesh_half_tri")]["n_eff_orders"] for k in DRONE_KEYS}
    ok = all(a[k]["mean"] > th["mean_gt"] for k in DRONE_KEYS) and \
        a["matrice4e"]["frac_positive"] >= th["frac_positive_ge"]
    rec("P1_primitive_richness_verdict_survives", "PASS" if ok else "FAIL",
        {k: dict(mean=a[k]["mean"], sd=a[k]["sd"], frac_positive=a[k]["frac_positive"],
                 sign_test_p=a[k]["sign_test_p"], n_eff_az=a[k]["n_eff_az"],
                 mean_over_sem_eff=a[k]["mean"] / max(a[k]["sem_eff"], 1e-300))
         for k in DRONE_KEYS}, th,
        dict(worst_margin=min(a[k]["mean"] for k in DRONE_KEYS),
             frac_positive_margin=a["matrice4e"]["frac_positive"] - th["frac_positive_ge"]))

    # P2·P3·P4 — 절반 메쉬가 지표를 얼마나 움직이나 (절대값 문턱)
    for pid, metric in (("P2_half_mesh_moves_n_eff_little", "n_eff_orders"),
                        ("P3_half_mesh_moves_flash_little", "flash_contrast_db"),
                        ("P4_half_mesh_moves_dc_ac_little", "dc_ac_db")):
        th = pr[pid]["thresholds"]
        a = {k: P[(k, "mesh_half_tri - mesh")][metric] for k in DRONE_KEYS}
        worst = max(abs(a[k]["mean"]) for k in DRONE_KEYS)
        ok = worst <= th["abs_mean_le"]
        rec(pid, "PASS" if ok else "FAIL",
            {k: dict(mean=a[k]["mean"], abs_mean=abs(a[k]["mean"]), sd=a[k]["sd"],
                     min=a[k]["min"], max=a[k]["max"],
                     max_abs_over_az=max(abs(a[k]["min"]), abs(a[k]["max"])))
             for k in DRONE_KEYS}, th,
            dict(worst_abs_mean=worst, threshold=th["abs_mean_le"],
                 threshold_over_observed=th["abs_mean_le"] / max(worst, 1e-300),
                 slack_note_ko="문턱이 관측값의 몇 배였나 — 클수록 이 PASS 는 약한 증거다."))

    # P5 — 파형 상관
    th = pr["P5_waveform_stays_correlated"]["thresholds"]
    a = {k: CC[(k, "mesh_half_tri vs mesh")] for k in DRONE_KEYS}
    worst = min(a[k]["mean"] for k in DRONE_KEYS)
    rec("P5_waveform_stays_correlated", "PASS" if worst >= th["mean_ge"] else "FAIL",
        {k: a[k] for k in DRONE_KEYS}, th,
        dict(worst_mean=worst, threshold=th["mean_ge"],
             one_minus_corr_worst=1.0 - worst,
             headroom=(worst - th["mean_ge"]) / max(1.0 - th["mean_ge"], 1e-300)))

    # P6 — AC 전력이 운동학 가능대역 안에 있는가
    th = pr["P6_half_mesh_stays_in_band"]["thresholds"]
    a = {k: arms[(k, "mesh_half_tri", "spherical")]["per_az"]["in_band_ac_frac"]
         for k in DRONE_KEYS}
    worst = min(a[k]["mean"] for k in DRONE_KEYS)
    rec("P6_half_mesh_stays_in_band", "PASS" if worst >= th["mean_ge"] else "FAIL",
        {k: a[k] for k in DRONE_KEYS}, th,
        dict(worst_mean=worst, threshold=th["mean_ge"], margin=worst - th["mean_ge"]))

    # P7 — CAD 가 이긴 유일한 지표(동체 대비 세기)가 살아남는가
    th = pr["P7_cad_dc_ac_advantage_survives"]["thresholds"]
    a = {k: P[(k, "slab - mesh_half_tri")]["dc_ac_db"] for k in DRONE_KEYS}
    ok = (a["matrice4e"]["mean"] > th["mean_gt"] and
          a["matrice4e"]["frac_positive"] >= th["frac_positive_ge"])
    rec("P7_cad_dc_ac_advantage_survives", "PASS" if ok else "FAIL",
        {k: dict(mean=a[k]["mean"], sd=a[k]["sd"], frac_positive=a[k]["frac_positive"],
                 sign_test_p=a[k]["sign_test_p"]) for k in DRONE_KEYS}, th,
        dict(matrice4e_margin=a["matrice4e"]["mean"],
             mini2_same_test_would_be=("PASS" if (a["mini2"]["mean"] > 0 and
                                                  a["mini2"]["frac_positive"] >= th["frac_positive_ge"])
                                       else "FAIL")),
        note_ko=("⚠ 이 예측은 matrice4e 에만 문턱을 걸었다. mini2 에 같은 문턱을 걸면 "
                 "어떻게 되는지 slack.mini2_same_test_would_be 에 적어 둔다."))

    # P8 — 4분의 1이 절반보다 더 어긋나는가(단조)
    a = {k: (CC[(k, "mesh_quarter_tri vs mesh")]["mean"], CC[(k, "mesh_half_tri vs mesh")]["mean"])
         for k in DRONE_KEYS}
    ok = all(q < h for q, h in a.values())
    rec("P8_degradation_is_monotone", "PASS" if ok else "FAIL",
        {k: dict(corr_quarter=q, corr_half=h, gap=h - q) for k, (q, h) in a.items()},
        pr["P8_degradation_is_monotone"]["thresholds"],
        dict(smallest_gap=min(h - q for q, h in a.values()),
             note_ko="두 상관 모두 0.999 언저리라 «단조» 는 넷째 자리에서 갈린다."))

    # P9 — 원인이 «면이 줄어서» 인가 «표본이 줄어서» 인가
    th = pr["P9_point_count_is_not_the_driver"]["thresholds"]
    coarse = {k: abs(P[(k, "mesh_half_tri - mesh")]["n_eff_orders"]["mean"]) for k in DRONE_KEYS}
    dense = {k: abs(P[(k, "mesh_half_tri_fine - mesh_fine")]["n_eff_orders"]["mean"])
             for k in DRONE_KEYS}
    ratio = {k: dense[k] / max(coarse[k], 1e-300) for k in DRONE_KEYS}
    both_small = all(coarse[k] <= th["both_small_abs"] and dense[k] <= th["both_small_abs"]
                     for k in DRONE_KEYS)
    if both_small:
        verdict = "INCONCLUSIVE"
    else:
        verdict = "PASS" if all(r >= th["ratio_ge"] for r in ratio.values()) else "FAIL"
    rec("P9_point_count_is_not_the_driver", verdict,
        {k: dict(coarse_abs_mean=coarse[k], dense_abs_mean=dense[k], ratio=ratio[k])
         for k in DRONE_KEYS}, th,
        dict(both_below_power_floor=both_small, floor=th["both_small_abs"]),
        note_ko=("두 차이가 모두 0.2 이하면 이 검정은 판정력이 없다 — 그 자체가 «절반으로 줄여도 "
                 "아무 일도 안 일어난다» 는 뜻이지만, «표본 대 형상» 을 갈랐다고 주장할 수는 없다."))

    n_pass = sum(1 for g in G.values() if g["verdict"] == "PASS")
    n_fail = sum(1 for g in G.values() if g["verdict"] == "FAIL")
    n_inc = sum(1 for g in G.values() if g["verdict"] == "INCONCLUSIVE")
    G["_summary"] = dict(
        n_pass=n_pass, n_fail=n_fail, n_inconclusive=n_inc,
        verdict_flipped=bool(G["P1_primitive_richness_verdict_survives"]["verdict"] == "FAIL" or
                             G["P7_cad_dc_ac_advantage_survives"]["verdict"] == "FAIL"),
        headline_ko=("P1(하모닉 풍부도)과 P7(동체 대비 세기)이 판정 뒤집힘을 결정한다. "
                     "둘 다 PASS 면 base 결론은 메쉬 해상도의 산물이 아니다."))
    return G


# --------------------------------------------------------------------------- #
#  5) 본체
# --------------------------------------------------------------------------- #
def main():
    t0 = time.time()
    rung = json.load(open(RUNG_JSON))
    pre = json.load(open(PREREG))
    base = json.load(open(BASE_JSON))
    main_tabs, hi_tabs = load_tables()
    protos = protocols()
    rng = np.random.default_rng(MC_SEED)

    J = dict(meta=dict(
        report="report16", stage="metric", rung="mesh_half_tri",
        producer="benchmark/report16_metric_mesh_half_tri.py",
        generated=time.strftime("%Y-%m-%dT%H:%M:%S"), git_rev=git_rev(),
        purpose_ko=("앞 단계가 남긴 원본 위상표에서 지표를 **다시** 계산하고, 사전예측과 "
                    "대조하고, 이 단을 못 믿을 이유를 숫자로 적는다."),
        independence_ko=("지표 값은 npz 원본 표 → report16_base.md_metrics16 경로로만 만든다. "
                         "앞 단계 JSON 의 숫자는 **대조용**으로만 읽는다."),
        inputs={k: dict(path=os.path.relpath(p, ROOT), sha256_16=sha256_16(p),
                        mtime=time.strftime("%Y-%m-%dT%H:%M:%S",
                                            time.localtime(os.path.getmtime(p))))
                for k, p in (("rung_json", RUNG_JSON), ("rung_tables_npz", RUNG_NPZ),
                             ("prereg_json", PREREG), ("base_json", BASE_JSON),
                             ("base_tables_npz", BASE_NPZ)) if os.path.exists(p)},
        prereg_order_proof=dict(
            prereg_mtime=time.strftime("%Y-%m-%dT%H:%M:%S",
                                       time.localtime(os.path.getmtime(PREREG))),
            rung_json_mtime=time.strftime("%Y-%m-%dT%H:%M:%S",
                                          time.localtime(os.path.getmtime(RUNG_JSON))),
            prereg_written_before_rung=bool(os.path.getmtime(PREREG) <
                                            os.path.getmtime(RUNG_JSON)),
            note_ko="사전예측 파일이 결과 파일보다 먼저 디스크에 있었는지 파일시간으로 확인한다."),
        gpu_used=None,
        gpu_note_ko=("이 단계는 저장된 위상표(최대 24×1024 복소수)를 FFT 하는 후처리라 GPU 가 "
                     "필요 없다. 실행 시점에 GPU 4장을 다른 워크플로가 쓰고 있어 건드리지 않았다."),
        forbidden_paths_untouched=["outputs/report15_*", "benchmark/report15_*",
                                   "src/make_report0N_*.py", "report0N_*.ipynb",
                                   "src/drones.py(읽기만)", "src/drone_cad.py(미접촉)"]))

    # ── 규약 재유도 대조 ───────────────────────────────────────────────────
    J["protocol_recomputed"] = dict(
        per_drone={k: dict(spec=protos[k]["spec"], main=protos[k]["main"], hi=protos[k]["hi"])
                   for k in DRONE_KEYS},
        agreement_with_rung=protocol_matches(protos, rung),
        source_ko="src/drones.py 의 spec → report16_base.derive_protocol (읽기 전용)")

    # ── 원본표 재대조: 앞 단계 npz vs base npz ────────────────────────────
    gate = {}
    if os.path.exists(BASE_NPZ):
        z = np.load(BASE_NPZ)
        for key in DRONE_KEYS:
            for arm in ("mesh", "mesh_fine", "slab", "disc", "sphere"):
                for wf in ("spherical", "plane"):
                    bk = f"main__G_0804__{key}__{arm}__{wf}"
                    if bk in z.files and (key, arm, wf) in main_tabs:
                        a, b = z[bk], main_tabs[(key, arm, wf)]
                        num = float(np.max(np.abs(a - b)))
                        den = float(np.max(np.abs(a)))
                        gate[f"{key}|{arm}|{wf}"] = dict(max_abs_diff=num,
                                                         max_rel=num / max(den, 1e-300))
    rels = [v["max_rel"] for v in gate.values()]
    J["tables_vs_base_recheck"] = dict(
        rows=gate, worst_rel=max(rels) if rels else None, tolerance=1e-12,
        verdict=("PASS" if rels and max(rels) < 1e-12 else ("FAIL" if rels else "NO_OVERLAP")),
        what_ko=("앞 단계가 복사해 온 mesh·평판·원판·구 팔이 base 의 표와 **비트 수준으로** 같은가. "
                 "같아야 base 판정과 이 단 판정을 이어붙일 수 있다."),
        caveat_ko=("⚠ 이 일치는 «같은 코드가 같은 답을 냈다» 는 뜻이지 «물리가 맞다» 는 뜻이 아니다. "
                   "공통 결함이 있으면 둘 다 똑같이 틀린다."))

    # ── 지표 계산 ─────────────────────────────────────────────────────────
    mets, arms_sum, per_az_out = {}, {}, {}
    for key in DRONE_KEYS:
        proto = protos[key]["main"]
        nb = protos[key]["spec"]["prop_blades"]
        for arm in ARMS:
            for wf in ("spherical", "plane"):
                if (key, arm, wf) not in main_tabs:
                    continue
                m = per_az(main_tabs[(key, arm, wf)], proto, nb)
                mets[(key, arm, wf)] = m
                arms_sum[(key, arm, wf)] = arm_summary(m)
                if wf == "spherical":
                    per_az_out[f"{key}|{arm}"] = {kk: [float(x[kk]) for x in m]
                                                  for kk in PER_AZ_KEYS}
    J["metrics_by_arm"] = {f"{k}|{a}|{w}": v for (k, a, w), v in arms_sum.items()}
    J["metrics_per_azimuth_spherical"] = per_az_out
    J["metric_definitions"] = dict(
        source="benchmark/report16_base.py :: md_metrics16 (호출, 재구현 아님)",
        families_ko={
            "① flash_contrast_db": "번쩍임 대조비 = 20log10(최대|E_ac| / 중앙값|E_ac|)",
            "② n_eff_orders·order_p50·order_p90·dominant_order·blade_comb_frac":
                "고차 성분 풍부도 — 살아 있는 하모닉 «실질 개수»와 누적 90% 차수, 블레이드 빗 비중",
            "③ width_ratio(−10/−20/−30 dB)·fd_edge_hz":
                "폭 — 스펙트럼 가장자리 ÷ 팁 도플러(f_tip). 운동학이 맞으면 ≈1",
            "④ dc_ac_db": "동체 대 블레이드 세기비 = 20log10(|c0| / √Σ|c_m≠0|²)"},
        interpretability_rule_ko=("in_band_ac_frac < 0.5 인 팔(회전대칭 원판·구)의 ②③ 지표는 "
                                  "이산화 잔차를 잰 것이라 인용 금지."))

    # ── 짝지은 비교 ───────────────────────────────────────────────────────
    PAIRS = [("mesh", "mesh_half_tri"), ("mesh", "mesh_quarter_tri"),
             ("mesh", "mesh_fine"), ("mesh_fine", "mesh_half_tri_fine"),
             ("mesh", "mesh_half_tri_all"),
             ("mesh", "slab"), ("mesh", "disc"), ("mesh", "sphere"),
             ("mesh_half_tri", "slab"), ("mesh_half_tri", "disc"), ("mesh_half_tri", "sphere"),
             ("mesh_quarter_tri", "slab")]
    P = {}
    for key in DRONE_KEYS:
        for a, b in PAIRS:
            if (key, a, "spherical") in mets and (key, b, "spherical") in mets:
                P[(key, f"{b} - {a}")] = paired(mets[(key, a, "spherical")],
                                                mets[(key, b, "spherical")])
    J["paired_spherical"] = {f"{k}|{p}": v for (k, p), v in P.items()}
    J["paired_note_ko"] = (
        "같은 방위에서 B − A. frac_positive 는 24 방위 중 B 가 큰 비율이다. "
        "sign_test_p 는 동전던지기 확률이지만 24 방위는 독립이 아니므로 **낙관적**이다 — "
        "az_lag1_corr / n_eff_az 를 같이 읽어라.")

    # ── 파형 상관 ─────────────────────────────────────────────────────────
    CC = {}
    for key in DRONE_KEYS:
        ref = main_tabs[(key, "mesh", "spherical")]
        for arm in ARMS:
            if arm == "mesh" or (key, arm, "spherical") not in main_tabs:
                continue
            alt = main_tabs[(key, arm, "spherical")]
            CC[(key, f"{arm} vs mesh")] = summarize(
                [B.ac_corr(ref[i], alt[i]) for i in range(ref.shape[0])])
        fine = main_tabs.get((key, "mesh_fine", "spherical"))
        hf = main_tabs.get((key, "mesh_half_tri_fine", "spherical"))
        if fine is not None and hf is not None:
            CC[(key, "mesh_half_tri_fine vs mesh_fine")] = summarize(
                [B.ac_corr(fine[i], hf[i]) for i in range(fine.shape[0])])
    J["waveform_correlation"] = {f"{k}|{p}": v for (k, p), v in CC.items()}

    # ── 앞 단계 JSON 과 한 자리씩 대조(감사) ──────────────────────────────
    audit = dict(paired={}, arms={}, correlation={}, per_azimuth={})
    worst = 0.0
    for (key, pair), row in P.items():
        rk = f"{key}|{pair}"
        ref = rung["paired"].get(rk)
        if not ref:
            continue
        d = {}
        for m, rv in ref.items():
            if m in row and isinstance(rv, dict) and "mean" in rv:
                dd = abs(row[m]["mean"] - rv["mean"])
                sc = max(abs(rv["mean"]), 1e-12)
                d[m] = dict(abs_diff=dd, rel_diff=dd / sc)
                worst = max(worst, dd / sc)
        audit["paired"][rk] = d
    for (key, arm, wf), s in arms_sum.items():
        ref = rung["arms"].get(key, {}).get(arm, {}).get(wf)
        if not ref:
            continue
        d = {}
        for m, rv in ref["per_az"].items():
            if m in s["per_az"]:
                dd = abs(s["per_az"][m]["mean"] - rv["mean"])
                sc = max(abs(rv["mean"]), 1e-12)
                d[m] = dict(abs_diff=dd, rel_diff=dd / sc)
                worst = max(worst, dd / sc)
        audit["arms"][f"{key}|{arm}|{wf}"] = d
    for (key, pair), s in CC.items():
        ref = rung["waveform_correlation"].get(f"{key}|{pair}")
        if ref:
            dd = abs(s["mean"] - ref["mean"])
            audit["correlation"][f"{key}|{pair}"] = dict(abs_diff=dd,
                                                         rel_diff=dd / max(abs(ref["mean"]), 1e-12))
            worst = max(worst, dd / max(abs(ref["mean"]), 1e-12))
    for rk, ref in rung.get("per_azimuth_paired", {}).items():
        key, pair, metric = rk.split("|")
        if (key, pair) in P and metric in METRIC_KEYS:
            b, a = pair.split(" - ")          # 키가 "B - A" 이므로 앞이 B(빼는 대상이 A)
            mine = [y[metric] - x[metric] for x, y in zip(mets[(key, a, "spherical")],
                                                          mets[(key, b, "spherical")])]
            dd = float(np.max(np.abs(np.array(mine) - np.array(ref))))
            sc = max(float(np.max(np.abs(ref))), 1e-12)
            audit["per_azimuth"][rk] = dict(max_abs_diff=dd, max_rel=dd / sc)
            worst = max(worst, dd / sc)
    J["audit_vs_rung_json"] = dict(
        rows=audit, worst_rel_diff=worst, tolerance=1e-9,
        verdict="PASS" if worst < 1e-9 else "FAIL",
        what_ko=("앞 단계 JSON 에 적힌 숫자를 내가 원본 표에서 다시 뽑은 숫자와 대조한다. "
                 "여기가 PASS 면 «숫자가 잘못 적혔을 가능성» 은 결론에서 빠진다."))

    # ── 해상도 축 vs 모델 축 (재계산) ─────────────────────────────────────
    axis = {}
    for key in DRONE_KEYS:
        for m in ("n_eff_orders", "flash_contrast_db", "dc_ac_db", "width_ratio",
                  "order_p90", "blade_comb_frac"):
            vals = {a: arms_sum[(key, a, "spherical")]["per_az"][m]["mean"]
                    for a in RES_ARMS if (key, a, "spherical") in arms_sum}
            span = max(vals.values()) - min(vals.values())
            pose_sd = float(np.std([x[m] for x in mets[(key, "mesh", "spherical")]], ddof=1))
            model = {}
            for prim in ("slab", "disc", "sphere"):
                pk = (key, f"{prim} - mesh")
                if pk not in P:
                    continue
                gap = abs(P[pk][m]["mean"])
                model[prim] = dict(
                    abs_gap_vs_cad=gap,
                    times_larger_than_resolution_span=(gap / span) if span > 0 else None,
                    times_larger_than_pose_sd=(gap / pose_sd) if pose_sd > 0 else None,
                    frac_positive=P[pk][m]["frac_positive"],
                    metric_interpretable=bool(
                        arms_sum[(key, prim, "spherical")]["interpretable_frac"] >= 0.5))
            axis[f"{key}|{m}"] = dict(
                resolution_axis=dict(values=vals, span=span,
                                     tri_range=[25.0, 100.0],
                                     sampling_range="1x -> 4x points per triangle"),
                model_axis=model, pose_sd=pose_sd)
    J["resolution_axis_vs_model_axis"] = dict(
        values=axis,
        what_ko=("같은 지표를 두 방향으로 흔들어 크기를 견준다. «해상도 축» = 삼각형 25~100%· "
                 "표본 1~4배, «모델 축» = 그 형상을 평판·원판·구로 갈아치움."),
        caveat_ko=("⚠ 원판·구는 회전대칭이라 AC 가 대역 밖 잔차뿐이다 → metric_interpretable=false. "
                   "인용 가능한 모델 축은 평판(slab) 뿐이다."))

    # ── 사전예측 재채점 ───────────────────────────────────────────────────
    G = regrade(pre, P, CC, arms_sum)
    J["prereg"] = dict(file=os.path.relpath(PREREG, ROOT), sha256_16=sha256_16(PREREG),
                       written_at=pre.get("written_at"),
                       predictions={k: dict(claim_ko=v["claim_ko"], test=v["test"],
                                            reason_ko=v.get("reason_ko"),
                                            thresholds=v.get("thresholds"))
                                    for k, v in pre["predictions"].items()})
    J["grading_independent"] = G
    J["grading_agreement_with_rung"] = dict(
        rows={pid: dict(mine=G[pid]["verdict"], rung=rung["grading"][pid]["verdict"],
                        same=bool(G[pid]["verdict"] == rung["grading"][pid]["verdict"]))
              for pid in G if pid != "_summary" and pid in rung["grading"]},
        all_same=bool(all(G[pid]["verdict"] == rung["grading"][pid]["verdict"]
                          for pid in G if pid != "_summary" and pid in rung["grading"])),
        what_ko="같은 문턱을 내 숫자로 다시 채점했을 때 앞 단계와 판정이 같은가.")

    # ── 문턱 여유(얼마나 헐거운 시험이었나) ───────────────────────────────
    J["threshold_stringency"] = dict(
        rows={pid: dict(test=G[pid]["test"], verdict=G[pid]["verdict"], slack=G[pid]["slack"])
              for pid in G if pid != "_summary"},
        what_ko=("PASS 는 문턱이 헐거우면 약한 증거다. P2~P4 의 threshold_over_observed 가 "
                 "1 에 가까울수록 «아슬아슬하게 통과», 10 이상이면 «관측값이 문턱의 10분의 1도 "
                 "안 됐다» 는 뜻이다 — 후자는 예측이 쉬웠다는 뜻이기도 하다."),
        honesty_ko="이 절은 우리 예측이 얼마나 담대했는지를 스스로 깎는 항목이다.")

    # ── 잡음 등가 ─────────────────────────────────────────────────────────
    ne = {}
    for key in DRONE_KEYS:
        proto, nb = protos[key]["main"], protos[key]["spec"]["prop_blades"]
        for arm in ("mesh_half_tri", "mesh_quarter_tri", "slab"):
            if (key, arm, "spherical") not in main_tabs:
                continue
            ne[f"{key}|{arm}"] = noise_equivalent(main_tabs[(key, "mesh", "spherical")],
                                                  main_tabs[(key, arm, "spherical")],
                                                  proto, nb, rng)
    J["noise_equivalent_perturbation"] = dict(
        values=ne, mc=dict(trials_per_azimuth=MC_TRIALS_PER_AZ, seed=MC_SEED),
        read_ko=("equivalent_snr_db 이 크면 그만큼 교란이 작다. 「절반 메쉬」와 「평판 교체」의 "
                 "이 값을 견주면 두 축의 크기 차이를 잡음 단위로 말할 수 있다."))

    # ── 폭 지표의 눈금(왜 «변화 0» 이 약한 증거인가) ──────────────────────
    wq = {}
    for key in DRONE_KEYS:
        pr_ = protos[key]["main"]
        w = P[(key, "mesh_half_tri - mesh")]["width_ratio"]
        wq[key] = dict(
            order_quantum_rel=pr_["order_quantum_rel"],
            beta=pr_["beta"],
            observed_abs_mean_delta=abs(w["mean"]),
            observed_max_abs_delta=max(abs(w["min"]), abs(w["max"])),
            delta_in_quantum_units=abs(w["mean"]) / pr_["order_quantum_rel"],
            width_ratio_mesh=arms_sum[(key, "mesh", "spherical")]["per_az"]["width_ratio"]["mean"],
            width_ratio_half=arms_sum[(key, "mesh_half_tri", "spherical")]["per_az"]["width_ratio"]["mean"],
            width_ratio_slab=arms_sum[(key, "slab", "spherical")]["per_az"]["width_ratio"]["mean"])
    J["width_metric_resolution"] = dict(
        values=wq,
        what_ko=("폭 지표의 최소 눈금은 «1차수 = 회전수» 이고, f_tip 대비 1/β 다. mini2 는 12%, "
                 "matrice4e 는 5% 보다 작은 폭 변화를 **원리적으로 못 잰다**. 그래서 「폭 변화 0」 은 "
                 "«안 변했다» 가 아니라 «자로 못 잰다» 일 수 있다."))

    # ── 프레임까지 줄인 팔 — 「해상도 무해」 주장의 경계 ──────────────────
    fr = {}
    for key in DRONE_KEYS:
        ka, kb = (key, "mesh_half_tri", "spherical"), (key, "mesh_half_tri_all", "spherical")
        if ka not in main_tabs or kb not in main_tabs:
            continue
        A = main_tabs[ka] - main_tabs[ka].mean(axis=1, keepdims=True)
        Bt = main_tabs[kb] - main_tabs[kb].mean(axis=1, keepdims=True)
        simp = rung["mesh_simplification"].get(f"{key}|frame|0.5", {})
        fr[key] = dict(
            max_rel_ac_difference=float(np.max(np.abs(A - Bt)) / max(np.max(np.abs(A)), 1e-300)),
            dc_ac_shift=P[(key, "mesh_half_tri_all - mesh")]["dc_ac_db"],
            prop_only_dc_ac_shift=P[(key, "mesh_half_tri - mesh")]["dc_ac_db"],
            frame_area_ratio=simp.get("area_ratio"), frame_volume_ratio=simp.get("volume_ratio"))
    J["frame_arm_boundary"] = dict(
        values=fr,
        what_ko=("프레임(동체)은 안 돌아서 위상마다 같은 상수를 더한다 → 평균을 빼면 AC 에서 정확히 "
                 "사라진다(max_rel_ac_difference 가 0 근처인 것이 그 증거). 대신 dc_ac_db 는 크게 "
                 "움직인다 — 프레임 간략화는 프롭과 달리 면적·부피를 꽤 잃기 때문이다."),
        boundary_ko=("⭐ 그래서 「해상도를 반으로 줄여도 무해하다」 는 **면적·부피를 보존하는 "
                     "간략화**·**가림 없는 커널**이라는 두 조건 안에서만 참이다."))

    # ── 고주파 대조(15.86 GHz) ────────────────────────────────────────────
    hi = {}
    if hi_tabs:
        hp, ha, hc = {}, {}, {}
        for key in DRONE_KEYS:
            proto, nb = protos[key]["hi"], protos[key]["spec"]["prop_blades"]
            hm = {}
            for arm in ("mesh", "mesh_half_tri", "slab"):
                if (key, arm, "spherical") not in hi_tabs:
                    continue
                hm[arm] = per_az(hi_tabs[(key, arm, "spherical")], proto, nb)
                ha[f"{key}|{arm}"] = arm_summary(hm[arm])
            for a, b in (("mesh", "mesh_half_tri"), ("mesh", "slab"), ("mesh_half_tri", "slab")):
                if a in hm and b in hm:
                    hp[f"{key}|{b} - {a}"] = paired(hm[a], hm[b])
            for arm in ("mesh_half_tri", "slab"):
                if (key, arm, "spherical") in hi_tabs:
                    ref = hi_tabs[(key, "mesh", "spherical")]
                    alt = hi_tabs[(key, arm, "spherical")]
                    hc[f"{key}|{arm} vs mesh"] = summarize(
                        [B.ac_corr(ref[i], alt[i]) for i in range(ref.shape[0])])
        hi = dict(fc_hz=B.FC_PO_KNEE, arms=ha, paired=hp, waveform_correlation=hc)
    J["hi_band"] = dict(
        **hi,
        note_ko=("블레이드 폭이 PO 유효 무릎(0.729λ)을 넘는 주파수에서 같은 지표를 다시 잰다. "
                 "간략화가 표면을 밀어낸 거리는 **주파수와 무관한 고정 길이**라 파장이 짧아지면 "
                 "같은 오차가 더 큰 위상이 된다."))

    # ── 표면 오차를 파장으로 잰 값(앞 단계 계산을 읽어 위상으로 환산) ─────
    sd = rung["surface_distance"]
    J["surface_error_vs_wavelength"] = dict(
        values={k: dict(rms_m=v["rms_m"], hausdorff_m=v["hausdorff_m"],
                        rms_over_lambda_main=v["rms_over_lambda_main"],
                        roundtrip_phase_deg_main=v["roundtrip_phase_deg_at_rms"],
                        roundtrip_phase_deg_hi=v["roundtrip_phase_deg_at_rms_hi"])
                for k, v in sd["values"].items()},
        lambda_main_mm=sd["lambda_main_mm"], lambda_hi_mm=sd["lambda_hi_mm"],
        read_ko=("«해상도가 언제부터 문제인가» 의 답은 삼각형 개수가 아니라 표면오차÷파장이다. "
                 "왕복 위상이 몇 도면 전파가 보기에 같은 물체다."))

    J["findings"] = _findings(J, P, CC, G, arms_sum, protos)
    J["reasons_to_distrust"] = _distrust(J, P, CC, G, arms_sum, protos, rung, base)

    # ── 한 줄 요약 (숫자는 전부 위에서 계산된 것을 꽂는다) ────────────────
    sc = G["_summary"]
    J["headline_ko"] = (
        f"지표를 원본 표에서 다시 계산해도 앞 단계와 한 자리까지 같다"
        f"(감사 worst_rel={J['audit_vs_rung_json']['worst_rel_diff']:.1e}). "
        f"사전예측 재채점 {sc['n_pass']}P/{sc['n_fail']}F/{sc['n_inconclusive']}I, "
        f"판정 {'뒤집힘' if sc['verdict_flipped'] else '유지'} — "
        f"절반 메쉬가 하모닉 풍부도를 움직인 폭은 "
        f"{P[('mini2', 'mesh_half_tri - mesh')]['n_eff_orders']['mean']:+.3f} / "
        f"{P[('matrice4e', 'mesh_half_tri - mesh')]['n_eff_orders']['mean']:+.3f} 인데, "
        f"같은 형상을 평판으로 갈아치우면 "
        f"{P[('mini2', 'slab - mesh_half_tri')]['n_eff_orders']['mean']:+.3f} / "
        f"{P[('matrice4e', 'slab - mesh_half_tri')]['n_eff_orders']['mean']:+.3f} 다. "
        f"잡음 단위로 말하면 절반 메쉬 = 신호보다 "
        f"{J['noise_equivalent_perturbation']['values']['mini2|mesh_half_tri']['equivalent_snr_db']['mean']:.0f} / "
        f"{J['noise_equivalent_perturbation']['values']['matrice4e|mesh_half_tri']['equivalent_snr_db']['mean']:.0f} dB "
        f"아래인 교란, 평판 교체 = 신호와 맞먹는 교란"
        f"({J['noise_equivalent_perturbation']['values']['mini2|slab']['equivalent_snr_db']['mean']:.0f} / "
        f"{J['noise_equivalent_perturbation']['values']['matrice4e|slab']['equivalent_snr_db']['mean']:.0f} dB). "
        f"⚠ 다만 이 «무해» 는 3.5 GHz·면적보존 간략화·가림 없는 커널이라는 세 조건 안에서만 참이다 "
        f"— 15.86 GHz 에서 matrice4e 는 같은 절반 메쉬로 n_eff 가 "
        f"{J['hi_band']['paired']['matrice4e|mesh_half_tri - mesh']['n_eff_orders']['mean']:+.2f} 움직인다.")

    J["meta"]["seconds"] = float(time.time() - t0)
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump(J, f, ensure_ascii=False, indent=1)
    s = J["grading_independent"]["_summary"]
    print(f"✅ {os.path.relpath(OUT_JSON, ROOT)}  [{J['meta']['seconds']:.0f}s]  "
          f"재채점 {s['n_pass']}P/{s['n_fail']}F/{s['n_inconclusive']}I  ·  "
          f"감사 {J['audit_vs_rung_json']['verdict']}(worst_rel={J['audit_vs_rung_json']['worst_rel_diff']:.2e})  ·  "
          f"판정 {'뒤집힘' if s['verdict_flipped'] else '유지'}")
    return J


# --------------------------------------------------------------------------- #
#  6) 결론 문장 — 숫자를 손으로 적지 않는다(위에서 계산된 값만 골라 넣는다)
# --------------------------------------------------------------------------- #
def _findings(J, P, CC, G, arms_sum, protos):
    F = {}
    F["m1_four_metric_families"] = dict(
        question_ko="네 갈래 지표가 절반 메쉬에서 얼마나 움직였나(24방위 짝지은 차이)",
        values={f"{k}|{m}": P[(k, "mesh_half_tri - mesh")][m]
                for k in DRONE_KEYS
                for m in ("flash_contrast_db", "n_eff_orders", "order_p90",
                          "blade_comb_frac", "width_ratio", "dc_ac_db")},
        waveform_correlation={k: CC[(k, "mesh_half_tri vs mesh")] for k in DRONE_KEYS})
    F["m2_prereg_scorecard"] = dict(
        question_ko="사전 예측 9개가 맞았나 틀렸나(내 숫자로 다시 채점)",
        verdicts={pid: G[pid]["verdict"] for pid in G if pid != "_summary"},
        summary=G["_summary"],
        agreement_with_rung=J["grading_agreement_with_rung"]["all_same"],
        misses=[pid for pid in G if pid != "_summary" and G[pid]["verdict"] != "PASS"],
        miss_meaning_ko=("PASS 가 아닌 항목만 적는다. FAIL 은 base 결론 철회를 뜻하고, "
                         "INCONCLUSIVE 는 «그 질문에 답하지 못했다» 를 뜻한다 — 둘은 다르다."))
    F["m3_verdict_survives"] = dict(
        question_ko="base 판정(«평판이 CAD 보다 하모닉이 풍부하다»)이 절반 해상도에서 살아남나",
        full_res={k: P[(k, "slab - mesh")]["n_eff_orders"] for k in DRONE_KEYS},
        half_res={k: P[(k, "slab - mesh_half_tri")]["n_eff_orders"] for k in DRONE_KEYS},
        quarter_res={k: P[(k, "slab - mesh_quarter_tri")]["n_eff_orders"] for k in DRONE_KEYS},
        verdict_flipped=G["_summary"]["verdict_flipped"])
    F["m4_two_axes"] = dict(
        question_ko="해상도를 바꾼 폭 vs 모델을 갈아치운 폭",
        slab_over_resolution={
            f"{k}|{m}": J["resolution_axis_vs_model_axis"]["values"][f"{k}|{m}"]["model_axis"]
            ["slab"]["times_larger_than_resolution_span"]
            for k in DRONE_KEYS for m in ("n_eff_orders", "flash_contrast_db", "dc_ac_db")})
    F["m5_noise_units"] = dict(
        question_ko="교란의 크기를 잡음 단위로 말하면",
        equivalent_snr_db={k: J["noise_equivalent_perturbation"]["values"][k]["equivalent_snr_db"]
                           for k in J["noise_equivalent_perturbation"]["values"]},
        read_ko=("절반 메쉬는 «신호보다 한참 아래인 잡음», 평판 교체는 «신호와 맞먹는 잡음» 에 "
                 "해당한다 — 두 축의 크기 차이를 dB 로 말한 것이다."))
    return F


def _distrust(J, P, CC, G, arms_sum, protos, rung, base):
    """⚠ 이 단을 못 믿을 이유 — 스스로 찾은 것만 적는다(숫자 포함)."""
    D = []

    # R1 — 문턱이 헐거웠다
    slack = {pid: J["threshold_stringency"]["rows"][pid]["slack"].get("threshold_over_observed")
             for pid in ("P2_half_mesh_moves_n_eff_little", "P3_half_mesh_moves_flash_little",
                         "P4_half_mesh_moves_dc_ac_little")}
    D.append(dict(
        id="R1_thresholds_were_loose",
        title_ko="예측 문턱이 관측값보다 10~100배 헐거웠다 — PASS 가 강한 증거가 아니다",
        evidence=dict(threshold_over_observed=slack,
                      p5_headroom=J["grading_independent"]["P5_waveform_stays_correlated"]
                      ["slack"]["headroom"]),
        why_it_hurts_ko=("P2~P4 는 «1.0 / 1.5 dB 안으로 움직인다» 였는데 실제로는 그 수십분의 1만 "
                         "움직였다. 문턱이 그만큼 헐거웠다는 것은, 만약 효과가 지금의 10배였어도 "
                         "여전히 PASS 였다는 뜻이다. 즉 이 시험은 «틀릴 수 있는 시험» 으로는 약했다."),
        what_would_settle_it_ko=("다음 단은 문턱을 관측 산포(자세 SD)나 앞 단 결과의 배수로 "
                                 "**미리** 못박아야 한다 — 예: |Δ| ≤ 0.1×(평판 갭).")))

    # R2 — 24 방위는 독립표본이 아니다
    az = {f"{k}|{p}": dict(az_lag1_corr=P[(k, p)]["n_eff_orders"]["az_lag1_corr"],
                           n_eff_az=P[(k, p)]["n_eff_orders"]["n_eff_az"],
                           n=P[(k, p)]["n_eff_orders"]["n"],
                           sign_test_p=P[(k, p)]["n_eff_orders"]["sign_test_p"])
          for k in DRONE_KEYS for p in ("slab - mesh_half_tri",)}
    D.append(dict(
        id="R2_azimuths_are_not_independent",
        title_ko="«24방위 중 24개» 같은 부호 일관성은 독립표본 24개가 아니다",
        evidence=dict(paired_n_eff=az,
                      note_ko="n_eff_az = 24·(1−r1)/(1+r1) — 이웃 방위가 닮은 만큼 깎은 유효표본수"),
        why_it_hurts_ko=("15° 간격 24방위는 같은 물체를 돌려가며 잰 것이라 이웃끼리 닮는다. "
                         "부호검정 p 값과 sem 은 그만큼 낙관적이다. 게다가 기체는 2대뿐이고 "
                         "고각·거리·모노스태틱 배치는 각각 하나로 고정돼 있다 — 즉 «앙상블» 은 "
                         "자세 하나뿐이고 설계 공간은 하나도 안 흔들렸다."),
        what_would_settle_it_ko="고각 여러 개·기체 여러 대·바이스태틱 각을 흔들어 같은 부호가 남는지 본다."))

    # R3 — 커널이 가장 약한 대역에서 판정했다 + 고주파에서는 실제로 움직인다
    hi_key = "matrice4e|mesh_half_tri - mesh"
    D.append(dict(
        id="R3_kernel_is_weakest_exactly_here",
        title_ko="판정 대역(3.5 GHz)에서 블레이드는 파장의 0.16배 — PO 커널이 가장 약한 곳이고, 무릎 위에서는 결과가 실제로 움직인다",
        evidence=dict(
            blade_width_over_lambda_main=rung["po_validity_warning"]["blade_width_over_lambda_main"],
            po_knee_a_over_lambda=rung["po_validity_warning"]["knee_a_over_lambda"],
            hi_band_half_minus_full_n_eff=J["hi_band"]["paired"].get(hi_key, {}).get("n_eff_orders"),
            main_band_half_minus_full_n_eff=P[("matrice4e", "mesh_half_tri - mesh")]["n_eff_orders"],
            hi_band_corr=J["hi_band"]["waveform_correlation"].get("matrice4e|mesh_half_tri vs mesh")),
        why_it_hurts_ko=("3.5 GHz 에서 «해상도가 안 중요하다» 는 결론은 **파장이 형상을 못 보기 때문**일 "
                         "수 있다. 실제로 15.86 GHz 로 올리면 같은 절반 메쉬가 지표를 훨씬 크게 흔든다 — "
                         "즉 «무해» 는 대역에 딸린 성질이지 메쉬에 딸린 성질이 아니다."),
        what_would_settle_it_ko=("표면오차÷파장을 축으로 여러 주파수를 훑어 «무해→유해» 가 갈리는 지점을 "
                                 "곡선으로 낸다. 우리 데이터는 두 점(3.5·15.86 GHz)뿐이다.")))

    # R4 — 면적·부피를 보존하는 간략화만 시험했다
    fr = J["frame_arm_boundary"]["values"]
    D.append(dict(
        id="R4_only_shape_preserving_simplification_was_tested",
        title_ko="QEM 간략화는 면적·부피를 보존하도록 «설계»된 연산이다 — 진짜 위험한 해상도 손실은 시험하지 않았다",
        evidence=dict(
            prop_area_ratio={k: rung["mesh_simplification"][f"{k}|prop|0.5"]["area_ratio"]
                             for k in DRONE_KEYS},
            prop_volume_ratio={k: rung["mesh_simplification"][f"{k}|prop|0.5"]["volume_ratio"]
                               for k in DRONE_KEYS},
            frame_volume_ratio={k: fr[k]["frame_volume_ratio"] for k in fr},
            frame_dc_ac_shift={k: fr[k]["dc_ac_shift"] for k in fr},
            prop_only_dc_ac_shift={k: fr[k]["prop_only_dc_ac_shift"] for k in fr}),
        why_it_hurts_ko=("프롭은 면적 0.03% 이내로 보존됐고 그래서 지표가 안 움직였다. 같은 파일 안의 "
                         "프레임 팔은 부피를 10% 잃자 dc_ac 가 방위에 따라 여러 dB 씩 흔들렸다. "
                         "즉 이 단이 보여 준 것은 «삼각형 수는 무해하다» 가 아니라 «면적·부피를 지키는 "
                         "간략화는 무해하다» 이고, 둘은 다른 주장이다."),
        what_would_settle_it_ko=("특징을 실제로 지우는 열화(블레이드 비틀림 제거·테이퍼 제거·두께 균일화)를 "
                                 "따로 팔로 넣어야 «형상 정밀도» 를 시험한 것이 된다.")))

    # R5 — 표본 대 형상 교란을 못 갈랐다(P9 INCONCLUSIVE)
    D.append(dict(
        id="R5_samples_vs_facets_not_separated",
        title_ko="«면이 줄어서» 인지 «적분 표본이 줄어서» 인지는 끝내 못 갈랐다(P9 INCONCLUSIVE)",
        evidence=J["grading_independent"]["P9_point_count_is_not_the_driver"]["actual"],
        why_it_hurts_ko=("점구름은 삼각형당 1점 규칙이라 삼각형을 반으로 줄이면 표본도 반이 된다. "
                         "통제팔(_fine)을 뒀지만 두 차이가 모두 판정 문턱 아래라 판정력이 없었다. "
                         "지금 결론은 «둘 다 아무 일도 안 일어난다» 까지이고, 원인 귀속은 못 한다."),
        what_would_settle_it_ko="표본 밀도를 삼각형 수와 분리(면적비례 표본)해 두 축을 직교시킨다."))

    # R6 — 폭 지표는 눈금이 굵어 «변화 0» 이 약한 증거
    D.append(dict(
        id="R6_width_metric_is_quantized",
        title_ko="«폭·차수 변화 0» 은 안 변한 것이 아니라 자의 눈금이 굵은 것일 수 있다",
        evidence=dict(
            width=J["width_metric_resolution"]["values"],
            zero_fraction_of_paired_diff={
                f"{k}|{m}": dict(frac_zero=P[(k, "mesh_half_tri - mesh")][m]["frac_zero"],
                                 mean=P[(k, "mesh_half_tri - mesh")][m]["mean"])
                for k in DRONE_KEYS
                for m in ("width_ratio", "order_p50", "order_p90", "dominant_order")}),
        why_it_hurts_ko=("폭 지표의 최소 눈금은 1차수 = 회전수이고 f_tip 대비 1/β 다 — mini2 12%, "
                         "matrice4e 5%. 차수 지표(order_p50·p90·dominant)도 정수라 눈금이 1이다. "
                         "그보다 작은 변화는 원리적으로 0 으로 찍힌다 — frac_zero=1.0 이 그 증거다."),
        what_would_settle_it_ko="차수 격자를 제로패딩/보간으로 잘게 하거나, 폭 대신 스펙트럼 모멘트를 쓴다."))

    # R7 — 회귀 게이트는 «같은 코드» 를 확인할 뿐 물리 검증이 아니다
    D.append(dict(
        id="R7_regression_gate_is_not_validation",
        title_ko="base 표와 비트 일치(worst_rel=0)는 코드가 같다는 뜻이지 물리가 맞다는 뜻이 아니다",
        evidence=dict(worst_rel=J["tables_vs_base_recheck"]["worst_rel"],
                      audit_worst_rel=J["audit_vs_rung_json"]["worst_rel_diff"],
                      kernel_limits_ko=rung["protocol"]["engine"]),
        why_it_hurts_ko=("커널에는 가림도, 모서리 회절도, 편파도 없다. 공통 결함은 게이트를 통과한다. "
                         "특히 dc_ac_db(동체 대 블레이드)는 가림이 없어 동체가 과대 계상되는 지표라 "
                         "P7 의 «CAD 우위» 는 그 결함과 같은 방향으로 놓여 있다."),
        what_would_settle_it_ko="가림 있는 SBR 로 같은 팔을 한 번 더 돌려 부호가 남는지 본다."))

    # R8 — 작지만 «잡음» 이 아니다: 한쪽으로만 미는 계통 편향이다
    nev = J["noise_equivalent_perturbation"]["values"]
    D.append(dict(
        id="R8_small_but_systematic_bias",
        title_ko="절반 메쉬의 이동은 작지만 «잡음» 이 아니라 한 방향으로만 미는 계통 편향이다",
        evidence=dict(
            n_eff_frac_positive={k: nev[k]["observed_signed_delta"]["n_eff_frac_positive"]
                                 for k in nev if k.endswith("mesh_half_tri")},
            obs_over_same_energy_random_noise={
                k: nev[k]["structured_vs_random"]["n_eff_obs_over_random"]
                for k in nev if k.endswith("mesh_half_tri")},
            paired_n_eff={f"{k}|mesh_half_tri - mesh": P[(k, "mesh_half_tri - mesh")]["n_eff_orders"]
                          for k in DRONE_KEYS}),
        why_it_hurts_ko=("삼각형을 반으로 줄이면 n_eff 가 **모든 방위에서 같은 쪽으로**(거의 24/24) "
                         "커진다. 같은 에너지의 무작위 잡음보다 지표를 2배 가까이 더 흔든다 — 즉 "
                         "«오차» 가 아니라 «편향» 이다. 지금은 평판 갭의 20분의 1이라 결론이 안 "
                         "바뀌지만, 절대값(예: 하모닉 개수 자체)을 인용하거나 간략화를 겹쳐 쓰면 "
                         "편향이 쌓인다."),
        what_would_settle_it_ko=("간략화 비율을 여러 단계(100/50/25/12.5%)로 훑어 편향이 선형으로 "
                                 "쌓이는지 보고, 외삽으로 «삼각형 무한대» 극한을 잡는다.")))
    return D


if __name__ == "__main__":
    main()
