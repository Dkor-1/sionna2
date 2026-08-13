# -*- coding: utf-8 -*-
"""
build_das_fleet_prereg.py — Das 4기체 x 7 바이스태틱각 대조의 **사전등록(pre-registration)**

계산 전에 예측을 고정한다. 이 파일이 쓰는 outputs/das_fleet_prereg.json 은
대조 실행 **전에** 확정된 예측·합격규칙·실패해석만 담는다.

⛔ 이 스크립트는 outputs/das_fleet_prereg.json 한 파일만 쓴다.
   p3_*.json · phantom3/mavic4pro/matrice4e 산출물 · teammeeting_0804/* ·
   sigma_grid_regen.json · sigma_el_extend_progress.json · anchor_subband*.json 은
   읽기만 했다. src/drones.py · src/drone_cad.py · src/rcs_sbr.py 는 읽기만 했다.
"""
from __future__ import annotations

import json
import os
from datetime import datetime

import numpy as np

ROOT = "/workspace/sionna"
OUT = os.path.join(ROOT, "outputs", "das_fleet_prereg.json")
C0 = 299792458.0

# ---------------------------------------------------------------- 입력 상수 (읽기전용)
SPEC = json.load(open(os.path.join(ROOT, "outputs", "das_fleet_spec.json")))
P3V = json.load(open(os.path.join(ROOT, "outputs", "p3_validation.json")))

THETAS = [0, 15, 30, 45, 60, 75, 90]
BANDS = {"phantom2": (11.0, 26.0), "phantom3": (1.8, 18.2),
         "mini2": (21.0, 27.0), "m350rtk": (21.0, 27.0)}
FC = {k: 0.5 * (a + b) for k, (a, b) in BANDS.items()}
CONV_OFFSET_DB = 2.5068          # Das mu(dB영역) -> 선형평균 등가 (지수분기, reconcile 채택값)
CONV_SPREAD_DB = 0.9254          # 로그정규분기와의 차 = 해소 안 된 규약 불확도

# Das Table III 에서 유도한 각 기체의 theta_b 별 밴드중심 레벨이동 [dB]
DAS_TAPER = {k: SPEC["airframes"][k]["delta_mu_vs_mono_at_bandcentre_db"] for k in BANDS}
DAS_A = {k: {str(t): SPEC["table3"][k][str(t)][0] for t in THETAS} for k in BANDS}
DAS_MU_C = {k: SPEC["airframes"][k]["table3_abcd"]["0"]["mu_bandcentre_dbsm"] for k in BANDS}

# ---------------------------------------------------------------- ka 표 (구 PO-vs-Mie 로 환산)
_t = P3V["low_ka"]["sphere_po_vs_mie_db"]
_kr = np.array(sorted(float(k) for k in _t))
_er = np.array([_t["%g" % k if ("%g" % k) in _t else "%.1f" % k] for k in _kr])


def po_err_db(x):
    return float(np.interp(float(x), _kr, _er))


FEATURES = {
    "phantom2": {"airframe half-span": 0.1445, "shell half-height": 0.032,
                 "motor bell": 0.017, "landing-leg tube": 0.008},
    "phantom3": {"airframe half-span": 0.1445, "shell half-height": 0.032,
                 "motor bell": 0.017, "landing-leg tube": 0.008},
    "mini2": {"airframe half-span": 0.1017, "shell half-height": 0.0281,
              "motor bell": 0.010, "landing prong": 0.0026},
    "m350rtk": {"airframe half-span": 0.4475, "body half-height": 0.110,
                "motor bell": 0.028, "gear carbon tube": 0.0125},
}


def ka_table(af):
    lo, hi = BANDS[af]
    out = {}
    for name, r in FEATURES[af].items():
        k_lo = 2 * np.pi * r / (C0 / (lo * 1e9))
        k_hi = 2 * np.pi * r / (C0 / (hi * 1e9))
        out[name] = {"r_m": r, "ka_at_band_lo": round(float(k_lo), 2),
                     "ka_at_band_hi": round(float(k_hi), 2),
                     "sphere_po_minus_mie_db_at_lo": round(po_err_db(k_lo), 2),
                     "sphere_po_minus_mie_db_at_hi": round(po_err_db(k_hi), 2)}
    kas = {k: v["ka_at_band_lo"] for k, v in out.items() if not k.startswith("_")}
    smallest = min(kas, key=kas.get)
    out["_min_ka_in_band"] = round(min(kas.values()), 2)
    out["_smallest_part"] = smallest
    out["_min_ka_of_dominant_parts"] = round(
        min(v for k, v in kas.items() if k != smallest), 2)
    out["_dominant_parts_note"] = (
        "_min_ka_of_dominant_parts 는 가장 작은 부위(%s) 하나를 뺀 값이다. 그 부위는 기여 가중치가 "
        "미미하다고 보아 뺐고, 그 판단 자체는 검증되지 않았다 — 정직 표기." % smallest)
    return out


# ---------------------------------------------------------------- 예측 모수 (여기가 사전등록의 핵심)
#  DL(af, theta_b) = mu_ours_linear(f_c) - [a_das*f_c + b_das + 2.5068]
#  DL(theta_b) = DL0 + D_ours(theta_b) - D_das(theta_b)
DL0 = {   # (중앙값, 68% 하한, 68% 상한, 95% 하한, 95% 상한)
    "phantom2": (-3.0, -7.0, +1.0, -12.0, +6.0),
    "phantom3": (-3.1, -5.0, -1.0, -7.0, +1.0),
    "mini2":    (-3.5, -7.0,  0.0, -11.0, +3.0),
    "m350rtk":  (-4.0, -9.0, +1.0, -15.0, +5.0),
}

#  우리 커널 자신의 theta_b 표류 (모든 기체 공통 — 커널 성질이지 기체 성질이 아니다)
D_OURS = {0: (0.0, 0.0, 0.0), 15: (-0.2, -1.0, +0.5), 30: (-0.5, -2.0, +1.0),
          45: (-1.2, -3.5, +1.5), 60: (-2.5, -6.0, +2.0), 75: (-4.5, -10.0, +2.0),
          90: (-8.0, -16.0, +2.0)}

#  우리 기울기 a_ours 예측 [dB/GHz] (중앙값, 68% 하한, 68% 상한) 과 그 SE 예측
A_OURS = {"phantom2": (0.10, -0.15, 0.40), "phantom3": (0.42, 0.33, 0.50),
          "mini2": (0.05, -0.40, 0.45), "m350rtk": (0.05, -0.45, 0.50)}
A_SE_PRED = {"phantom2": 0.12, "phantom3": 0.066, "mini2": 0.28, "m350rtk": 0.28}


def obliquity_inflation_db(beta_deg):
    """표준 obliquity (n̂·û_i) 만 쓸 때 생기는 상반성 위반의 **방위평균 인플레이션 상한**.
    평판 실측(sbr_defect_fixes.d2_reciprocity_plate)에서 sigma(i,s)/sigma(s,i) = (cos_i/cos_s)^2
    = (cos beta)^-2 임이 rms 0.87 dB 로 확인됐다. 방위 전주기 평균은 두 순서를 다 지나므로
    선형영역에서 (r^2 + r^-2)/2, r = 1/cos(beta) 가 **상한**이다(모든 면이 최악 짝을 이룰 때)."""
    c = np.cos(np.radians(beta_deg))
    if c < 1e-9:
        return float("inf")
    return float(10 * np.log10((1 / c ** 2 + c ** 2) / 2))


def build_predictions():
    pred = {}
    for af in BANDS:
        m0, l68, h68, l95, h95 = DL0[af]
        per_theta = {}
        for t in THETAS:
            dm, dl, dh = D_OURS[t]
            dd = DAS_TAPER[af][str(t)]
            per_theta[str(t)] = {
                "grade": SPEC["grades"][af]["theta_b_0" if t == 0 else "theta_b_15_90"],
                "level_error_db": {
                    "median": round(m0 + dm - dd, 2),
                    "p68": [round(l68 + dl - dd, 2), round(h68 + dh - dd, 2)],
                    "p95": [round(l95 + dl - dd, 2), round(h95 + dh - dd, 2)],
                },
                "slope_error_db_per_ghz": {
                    "median": round(A_OURS[af][0] - DAS_A[af][str(t)], 3),
                    "p68": [round(A_OURS[af][1] - DAS_A[af][str(t)], 3),
                            round(A_OURS[af][2] - DAS_A[af][str(t)], 3)],
                    "p95": [round(A_OURS[af][1] - 2 * A_SE_PRED[af] - DAS_A[af][str(t)], 3),
                            round(A_OURS[af][2] + 2 * A_SE_PRED[af] - DAS_A[af][str(t)], 3)],
                },
                "das_taper_removed_db": dd,
                "das_a_db_per_ghz": DAS_A[af][str(t)],
                "our_obliquity_inflation_upper_db": (round(obliquity_inflation_db(t), 2)
                                                     if t < 90 else "divergent"),
                # ⭐ 등급대상은 (i) 모든 기체의 theta_b=0, (ii) phantom2 의 theta_b=15..60 뿐이다.
                #    75·90 은 커널의 선언된 유효범위 밖이라 **사전에** 제외한다(사후 제외는 체리피킹).
                "gradeable": (t == 0) or (af == "phantom2" and t in (15, 30, 45, 60)),
                "gradeable_why_not": (None if (t == 0 or (af == "phantom2" and t in (15, 30, 45, 60)))
                                      else ("커널 유효범위 밖 — 상반성 위반 상한 %s, 게이트 교집합 축소"
                                            % ("발산" if t == 90 else "%.2f dB" % obliquity_inflation_db(t))
                                            if t in (75, 90) else
                                            "등급 D — 측정이 아니라 theta_b=0 적합에 씌운 해석 taper")),
            }
        pred[af] = {
            "band_ghz": list(BANDS[af]),
            "band_centre_ghz": FC[af],
            "comparand_das_mu_bandcentre_dbsm_as_published": DAS_MU_C[af],
            "comparand_das_mu_bandcentre_dbsm_linear_equivalent": round(
                DAS_MU_C[af] + CONV_OFFSET_DB, 3),
            "mesh_status": ("phantom3 메쉬를 대리로 씀 (Table I 이 P2·P3 에 같은 35x20 cm 를 준다)"
                            if af == "phantom2" else "자체 메쉬"),
            "ka_table": ka_table(af),
            "predicted_our_slope_a_db_per_ghz": {"median": A_OURS[af][0],
                                                 "p68": [A_OURS[af][1], A_OURS[af][2]],
                                                 "predicted_SE": A_SE_PRED[af]},
            "slope_test_is_powered": A_SE_PRED[af] < abs(DAS_A[af]["0"]) * 1.5,
            "per_theta_b": per_theta,
        }
    return pred


def main():
    doc = {
        "_meta": {
            "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "generator": "benchmark/build_das_fleet_prereg.py (사전등록 생성기 — 재실행하면 같은 JSON 이 나온다)",
            "what": "Das 4기체 x 7 theta_b 대조의 **사전등록**. 계산 전에 예측·합격규칙·실패해석을 고정한다.",
            "inputs_read_only": [
                "outputs/das_fleet_spec.json (표 판독본·등급·대조계획)",
                "outputs/p3_validation.json (phantom3 결과: 레벨 -4.9 dB(Yuan 정합) / -3.01 dB(Das 지수분기), 기울기 1.6 sigma)",
                "outputs/mini2_mesh_audit.json · outputs/m350rtk_mesh_audit.json (새 기체 빌드 결과)",
                "outputs/sbr_defect_fixes.json (평판 상반성 위반 = -20log10(cos beta) 실측)",
                "outputs/geometry_benchmark.json (이등분선 근사 오차 rms 중앙 7.47 dB · p95 최대 20.04 dB)",
                "src/rcs_sbr.py:568,636-639 (obliquity 규약 주석) — 읽기만",
                "outputs/p3_ours.json/meta (div=16, jitter=2, max_bounce=1, penetrate=True, 선형 방위평균)",
            ],
            "wrote_only": "outputs/das_fleet_prereg.json",
            "metric_definition": (
                "DL(af, theta_b) = mu_ours_linear(f_c) - [a_das*f_c + b_das + 2.5068] [dB],  "
                "Da(af, theta_b) = a_ours - a_das [dB/GHz].  f_c = 밴드중심. "
                "+2.5068 은 Das mu(dB영역 방위평균)를 선형(전력) 방위평균으로 올리는 지수분기 오프셋이고, "
                "로그정규분기와의 차 0.9254 dB 가 해소 안 된 규약 불확도로 모든 예측에 딸려 있다."),
            "why_this_frame": (
                "phantom3 는 Yuan 실측곡선(고도·규약·추정량 전부 정합)이라는 A급 대조가 있지만 "
                "나머지 3 기체는 Das 계수뿐이다. 4 기체를 한 자로 재려면 전부 Das 프레임으로 통일해야 한다. "
                "그래서 phantom3 의 comparand 도 Yuan 의 -4.9 dB 가 아니라 Das 지수분기의 -3.01 dB 를 쓴다."),
        },

        # ------------------------------------------------------------------ 1. 기체·theta_b 별 예측
        "predictions": build_predictions(),

        "headline_prediction_theta_b_0": {
            "level_error_db_median": {k: round(DL0[k][0], 2) for k in BANDS},
            "predicted_spread_db": round(max(v[0] for v in DL0.values())
                                         - min(v[0] for v in DL0.values()), 2),
            "predicted_sign": "네 기체 모두 음(-). 부호 4/4 일치를 예측한다.",
            "the_sharpest_single_claim": (
                "⭐ 산포 예측 1.0 dB. 합격문턱 P3 는 6.0 dB 다 — 즉 우리는 문턱보다 6 배 좁게 예측하고 있다. "
                "이게 이 사전등록에서 가장 위험한 수다. 실제 산포가 3 dB 를 넘으면 예측이 틀린 것이고, "
                "6 dB 를 넘으면 방법이 검증되지 않은 것이다. 둘은 다른 실패다 — 앞은 내 예측의 실패, "
                "뒤는 파이프라인의 실패."),
            "how_i_could_be_wrong": (
                "네 중앙값을 -3.0~-4.0 으로 좁게 놓은 근거는 phantom3 한 점(-3.01 dB)뿐이다. "
                "N=1 을 N=4 로 외삽한 것이고, 그것이 정확히 이 라운드가 검사하는 가정이다. "
                "예측이 좁은 것은 자신감이 아니라 **반증가능성을 최대로 만들려는 선택**이다."),
        },

        "prediction_rationale": {
            "anchor_from_phantom3": {
                "measured_level_error_db": {
                    "vs_yuan_theta90_measured_curve_fully_matched": -4.913,
                    "vs_das_exponential_branch": -3.014,
                    "vs_das_lognormal_branch": -3.939,
                    "vs_das_as_published_convention_mismatched": -0.507,
                },
                "measured_slope_error_db_per_ghz": {"vs_das": 0.210, "vs_yuan_theta90": 0.105,
                                                    "our_SE": 0.066, "sigma_vs_yuan": 1.58},
                "structure": ("잔차가 1.8 GHz 에서 -8.0 dB, 18.2 GHz 에서 -0.6 dB(Das 선 기준) / "
                              "-5.8 -> -5.1 dB(Yuan 실측곡선 기준). 두 comparand 가 서로 다른 이야기를 한다."),
            },
            "the_two_competing_hypotheses": {
                "H_ka": {
                    "claim": "레벨 결손은 저 ka 에서 PO/PTD 가 지는 것이다. ka 가 커지면 사라진다.",
                    "support": ("Das 선 기준 잔차가 저주파 -8.0 -> 고주파 -0.6 dB 로 줄고, "
                                "1.8 GHz 에서 셸(ka 1.21)·모터벨(0.64)·다리튜브(0.30) 셋이 구 PO 가 "
                                "-4.8~-6.6 dB 지는 구간에 있다."),
                    "predicts_at_21_27ghz": "DL(mini2), DL(m350rtk) in [-2.5, +0.5] dB",
                    "prior_probability": 0.35,
                },
                "H_flat": {
                    "claim": "레벨 결손은 주파수와 무관한 스칼라 오프셋이다(재질 Gamma·편파·미모델 산란체·보정규약).",
                    "support": ("고도·규약·추정량이 전부 정합인 **유일한** 대조(Yuan theta90 실측곡선)에서 "
                                "잔차가 1.8~18.2 GHz 내내 -5.8 -> -5.1 dB 로 거의 평평하다. 주파수 10배, "
                                "작은 부위의 ka 가 0.3 -> 3 으로 10배 변하는 동안 0.7 dB 밖에 안 움직였다."),
                    "predicts_at_21_27ghz": "DL(mini2), DL(m350rtk) in [-6.5, -3.0] dB",
                    "prior_probability": 0.55,
                },
                "other": {"claim": "둘 다 아니고 기체별 메쉬 품질이 지배한다", "prior_probability": 0.10},
                "why_this_round_can_decide": (
                    "⭐ mini2·m350rtk 의 21-27 GHz 는 **모든 지배 부위가 ka >= 4.4** 다(아래 ka_table). "
                    "phantom3 가 1.8 GHz 에서 겪은 저-ka 결손이 구조적으로 불가능한 대역이다. "
                    "따라서 거기서 DL 이 여전히 -3~-6 dB 이면 H_ka 는 죽고, 0 근처로 올라오면 H_flat 이 죽는다. "
                    "N=1 이던 phantom3 라운드는 이 갈래를 가를 수 없었다."),
                "which_outcome_hurts_the_project_more": (
                    "H_ka 가 이기면 우리 커널은 광학영역에서만 맞는다는 뜻이고, report12 의 디텍션 결론이 사는 "
                    "1.8-6.0 GHz 는 교정되지 않은 채 남는다. p3_validation.our_operating_band 가 이미 "
                    "그 대역에서 레벨 -8.0~-3.4 dB · 기울기 3.8배를 쟀다. H_flat 이 이기면 형상·패턴은 맞고 "
                    "스칼라 하나만 틀린 것이라 훨씬 고치기 쉽다."),
            },
            "per_airframe": {
                "phantom2": {
                    "band": "11-26 GHz. 모든 부위 ka >= 1.84 (다리튜브 최소), 지배부위는 ka 3.9~78.7.",
                    "favourable": ["저-ka 결손이 거의 없는 대역", "방위격자 0:1:360 = 우리 전주기와 정합",
                                   "이 논문에서 유일하게 **실측된** 바이스태틱 7 각도"],
                    "adverse": [
                        "⭐ 메쉬가 없다 — phantom3 메쉬를 대리로 쓴다. 짐벌·카메라·랜딩기어가 다른 기체다.",
                        "근거리장 2.6 m (필요 9.0~28.2 m). 표적 횡단 위상오차가 26 GHz 에서 184~244도.",
                        "비무향 실내홀 — 시간영역 게이팅으로 걸러내지만 잔여 클러터가 남는다.",
                        "Das 의 mu 적합 정의역은 200 MHz 서브밴드 중심 150 점이지 원시 2001 점이 아니다.",
                    ],
                    "level_prediction_reason": (
                        "대리 메쉬 오차(±3 dB 급)와 근거리장 편향(부호 불명, ±3 dB 급)이 phantom3 의 "
                        "-3 dB 위에 겹친다 -> 중앙 -3.0, 68% [-7,+1], 95% [-12,+6]. "
                        "폭이 가장 넓은 기체이고, 그래서 합격판정에서 가중치가 가장 낮다."),
                    "slope_prediction_reason": (
                        "phantom3 의 10.0-18.2 GHz 부분대역 기울기가 0.149 dB/GHz 였다. 같은 형상을 "
                        "11-26 GHz 로 옮기면 비슷하거나 더 완만해야 한다 -> a_ours ~ 0.10 [-0.15, 0.40]. "
                        "Das 의 a(theta_b) 는 0.21/0.50/0.22/0.21/0.12/-0.13/0.08 로 흔들리므로 "
                        "Da(theta_b) 의 산포는 **거의 전부 Das 쪽에서 온다**."),
                },
                "phantom3": {
                    "band": "1.8-18.2 GHz. **이미 잰 셀이다 — 이 라운드에서는 통제군(control)이다.**",
                    "role": ("새 정보를 얻는 셀이 아니라 **프로토콜 검산**이다. 함대 규약(dB영역 평균 규칙, "
                             "Table I 방위격자 -90:2:90, 같은 창 적합)으로 다시 내도 p3_validation 의 "
                             "-3.01 dB 근처가 나와야 한다."),
                    "why_the_band_is_not_zero_width": (
                        "함대 규약은 방위창을 -90:2:90 (91점 180도 호)으로 바꾸는데 시작각이 미상이다. "
                        "p3_validation.window.azimuth_window 가 그 항을 직접 쟀다 — 평균편향 -0.10 dB, "
                        "시작각 미상 폭 최대 4.46 dB(±2.2 dB). 그래서 68% [-5,-1] 로 잡는다."),
                    "adverse": ["셸 단면법칙을 phantom4 에서 상속(자유도 비 12.8)",
                                "높이 185 mm 사용(문헌 200 mm)", "마그네슘 판 1장 과금속화"],
                },
                "mini2": {
                    "band": "21-27 GHz. ⭐ 전 부위 ka: 반스팬 44.8~57.6 · 셸 12.4~15.9 · 모터벨 4.4~5.7. "
                            "저-ka 구간에 걸리는 것은 착륙 프롱(1.14~1.47) 하나뿐이고 그건 기여가 미미하다.",
                    "favourable": [
                        "⭐ 함대에서 **가장 잘 구속된 메쉬**다 — 형상이 DJI 자신의 공표 GLB(59 파트/109,470 면)에서 왔고 "
                        "자유도 비 3.65 (phantom3 를 같은 규칙으로 다시 세면 12.76). 3.5 배 적다.",
                        "실루엣 IoU 가 상한 대비 77.3% 로 몰딩 셸 소비자기 중 1위(다른 DJI 4기보다 14~27점 높다).",
                        "방위격자 0:0.5:360 = 우리 전주기와 정합 -> phantom3 를 괴롭힌 180도 호 시작각 모호성(±2.2 dB)이 **사라진다**.",
                        "원거리장 필요거리 9.3~12.0 m 로 대형 챔버에서 실현 가능한 규모다(m350rtk 와 달리).",
                        "대역폭 6 GHz 에 501 점 -> 로브 평균이 잘 되고 레벨 추정이 안정적이다.",
                    ],
                    "adverse": [
                        "프레임 폭 193.8 mm vs 실측 203.4 (-4.5%) — 가장 넓은 치수에서 결손. 면적 ~-9% -> 레벨 -0.4~-0.8 dB 쪽.",
                        "캐노피 파트가 셸 안에 통째로 파묻혀 있다 -> PO/SBR 이 세는 내부면(부호는 +).",
                        "마그네슘 판(공유 셸-v2 경로) — Mini 2 에는 실물 대응(SoC 방열판)이 있으나 크기는 공유 비율이다.",
                        "편파 미확인 — Das 본문에 진술 없고 ref[7] 미판독. 우리는 무편파 스칼라 |Gamma| 다.",
                        "레인지 종류 미기술.",
                    ],
                    "level_prediction_reason": (
                        "phantom3 의 -3.0 dB(Das 지수분기)를 출발점으로, 메쉬 품질 개선(+1~2 dB 쪽)과 "
                        "방위창 모호성 제거(폭 축소), 폭 결손(-0.4~-0.8 dB), 파묻힌 캐노피(+)를 얹는다. "
                        "H_flat 이 맞으면 -6.5~-3.0, H_ka 가 맞으면 -2.5~+0.5 -> 두 갈래를 덮는 "
                        "중앙 -3.5, 68% [-7, 0], 95% [-11, +3]."),
                    "slope_prediction_reason": (
                        "⭐ **기울기 검정은 여기서 무력하다.** 창이 6 GHz 뿐이라 std(f)=1.73 GHz 이고, "
                        "우리 mu(f) 의 로브 잔차를 phantom3 el0 의 rmse 1.43 dB 에서 대역폭 비로 줄여 "
                        "~0.8 dB, 유효 독립 로브 ~3 개로 잡으면 SE(a) ~ 0.28 dB/GHz 다. "
                        "Das 의 a = 0.07 은 그 SE 의 1/4 이다 -> 어떤 결과가 나와도 구별 못 한다. "
                        "사전에 **등급대상에서 뺀다**(보고는 하되 합격판정에 안 쓴다)."),
                },
                "m350rtk": {
                    "band": "21-27 GHz. 전 부위 ka: 반스팬 197~253 · 동체 48~62 · 모터벨 12.3~15.8 · "
                            "다리 탄소튜브 5.5~7.1. **함대에서 가장 완전한 광학영역**이다.",
                    "favourable": ["ka 가 압도적으로 커서 PO 가 가장 유리한 조건",
                                   "wheelbase 895 mm 가 공표치와 정확히 일치",
                                   "watertight 전 파트 통과, 내향법선·퇴화삼각형 0",
                                   "방위격자 0:0.5:360 정합"],
                    "adverse": [
                        "⭐ 등록 사진이 **한 장뿐**이다(IoU 0.503 = 상한 대비 56.0%, 함대 최하위권). "
                        "자유도 비 5.53 으로 mini2 의 3.65 보다 나쁘다.",
                        "프레임 bbox 771x626 mm vs 공표 810x670 (-4.8% / -6.5%) — 로터 스테이션 오버행 결손.",
                        "⭐ TB65 배터리 두 팩이 실물에서는 셸 **밖**인데 커널은 주변 body 를 유전체 셸로 본다 -> "
                        "지배 금속체 앞에 없는 셸이 한 겹. |Gamma|_body=0.28 -> tau=0.9216 per pass, 왕복 0.849 "
                        "= **-0.71 dB** 의 부호가 정해진 음의 편향(그 그룹 기여분에 한해).",
                        "⭐ 2D^2/lambda = 155~199 m. 무향실 실거리로 불가능하고 CATR 이어야 하는데 Das 는 "
                        "레인지 종류를 안 적는다. 정적영역이 1.05 m 를 못 덮으면 **측정 쪽 sigma 가 낮게** 나오고, "
                        "그러면 우리 DL 이 부당하게 좋아 보인다(양의 방향 편향).",
                        "편파 미확인.",
                    ],
                    "level_prediction_reason": (
                        "ka 는 최선이지만 메쉬 증거가 가장 얇다. 배터리 셸 편향 -0.7 dB 와 bbox 결손 "
                        "(-4.8%/-6.5% -> 면적 ~-11% -> -0.5~-1.0 dB)이 부호가 정해진 음의 항이고, "
                        "CATR 정적영역 의심이 부호가 정해진 양의 항이다. 중앙 -4.0, 68% [-9,+1], 95% [-15,+5]."),
                    "slope_prediction_reason": "mini2 와 같다 — 6 GHz 창, SE(a) ~ 0.28. **등급대상 제외.**",
                },
            },
            "mesh_tessellation_check": {
                "why": "21-27 GHz 는 우리가 한 번도 안 돌려본 대역이다. 면 크기가 lambda 에 비해 커지면 곡면이 "
                       "다면체가 되어 위상오차가 생긴다 — 새 오차원이 생기는지 미리 잰다.",
                "lambda_mm_at_27ghz": 11.1,
                "ray_spacing_mm_at_27ghz_div16": 0.694,
                "ray_spacing_verdict": "광선 격자는 문제없다 — lambda/16 = 0.69 mm 로 충분히 촘촘하다.",
                "facet_size_estimate": {
                    "m350rtk_body": "5 파트 7560 면, 표면적 ~0.5 m^2 -> 평균 면적 ~66 mm^2 -> 변 ~12 mm ~ 1.1 lambda",
                    "m350rtk_motor_bell": "8 파트 2336 면, r=28 mm h~40 mm -> 변 ~8 mm ~ 0.7 lambda",
                },
                "phase_error_bound": {
                    "formula": "곡률반경 R 의 곡면을 현 c 로 다면체화하면 새기타 delta = c^2/(8R), 왕복 위상오차 2*k*delta",
                    "m350rtk_body_R150mm_c12mm": "delta=0.12 mm -> 2k*delta = 0.136 rad = 7.8 deg",
                    "m350rtk_bell_R28mm_c8mm": "delta=0.29 mm -> 2k*delta = 0.32 rad = 18.4 deg",
                    "verdict": "⭐ 위상오차가 20도 미만이므로 다면체화 손실은 **< 1 dB** 로 묶인다. "
                               "즉 21-27 GHz 결과를 '메쉬가 거칠어서' 로 변명할 수 없다. 미리 못 박아 둔다.",
                },
            },
        },

        # ------------------------------------------------------------------ 2. 바이스태틱 예측
        "bistatic_prediction": {
            "headline": (
                "⭐ theta_b 가 커질수록 우리 오차는 **커진다**. 부호는 두 힘의 경합이라 확신 못 하지만 "
                "크기는 단조증가한다고 예측한다. theta_b<=30 에서 |DL(theta_b)-DL(0)| <= 1 dB, "
                "theta_b=45 에서 <= 2.5 dB, theta_b=60 에서 <= 5 dB, theta_b=75~90 에서는 커널이 "
                "**유효범위 밖**이라 등급을 매기지 않는다."),
            "mechanism_1_obliquity_is_not_symmetric": {
                "code_evidence": (
                    "src/rcs_sbr.py:568 — '(4) obliquity 는 표준 PO 의 (n̂·û_i) 를 그대로 쓴다'. "
                    "src/rcs_sbr.py:636-639 — 'obliquity 는 û_i 개구 샘플링에 내재한 (n̂·û_i) 를 그대로 쓴다(표준 PO). "
                    "대칭 sqrt((n̂·û_i)(n̂·û_s)) 로 승격하면 이론상 상반성이 복원되나, grazing 조명면에서 "
                    "sqrt(cos_s/cos_i) 가 이산 격자를 폭발시켜 오히려 rms 오차가 커진다 -> 표준 (n̂·û_i) 유지.'"),
                "closed_form_consequence": (
                    "조명 격자를 û_i 로 쏘면 히트밀도가 투영면적을 재므로 E(i,s) = ∫ e^{jk(û_i+û_s)·p} (n̂·û_i) dS 이고 "
                    "역방향은 (n̂·û_s) 다. 위상항이 같으므로 sigma(i,s)/sigma(s,i) = (cos_i/cos_s)^2 가 **정확히** 예측된다."),
                "measured_on_a_plate": {
                    "source": "outputs/sbr_defect_fixes.json :: d2_reciprocity_plate (PEC 0.08x0.08 m, 3.5 GHz, div=32)",
                    "prediction": "10log10(sigma(i,s)/sigma(s,i)) = -20log10(cos beta)",
                    "violation_db_measured": {"5": 0.001, "15": 0.296, "30": 1.247, "45": 2.904,
                                              "60": 5.989, "75": 14.478},
                    "predicted_db": {"5": 0.033, "15": 0.301, "30": 1.249, "45": 3.010,
                                     "60": 6.021, "75": 11.740},
                    "rms_residual_db": 0.871,
                    "max_abs_residual_db_beta_le_60": 0.294,
                    "reading": "beta<=60 에서 닫힌형이 0.3 dB 안에서 맞는다. beta>=65 의 어긋남은 예측이 틀린 게 "
                               "아니라 역방향 투영개구가 a*cos(beta)/d 셀로 줄어 격자 양자화가 지배하기 때문이다 "
                               "(cells_across_reverse 30 -> 7.7).",
                },
                "what_it_does_in_the_das_geometry": (
                    "⭐ Das 기하는 입사 az=phi · 산란 az=phi+theta_b 로 **둘이 함께 돌고** phi 를 전주기 평균한다. "
                    "따라서 어떤 면이 (cos_i>cos_s) 인 phi 가 있으면 반대인 phi 도 반드시 있다. 선형(전력) 평균에서 "
                    "젠센 부등식으로 E[r^2]+E[r^-2] >= 2 이므로 그 짝짓기는 **평균 sigma 를 위로 부풀린다**. "
                    "상한(모든 면이 최악 짝을 이룰 때) = 10log10((sec^2 theta_b + cos^2 theta_b)/2):"),
                "inflation_upper_bound_db": {str(t): (round(obliquity_inflation_db(t), 2) if t < 90
                                                      else "divergent") for t in THETAS},
                "honest_caveat": (
                    "이건 **상한**이지 예측값이 아니다. 실제 기체는 법선이 분산돼 있어 최악 짝이 전부 성립하지 않는다. "
                    "그래서 이 항의 실제 크기는 상한의 1/3~1/2 로 본다: theta_b=45 에서 +0.3~0.5 dB, 60 에서 +1~1.6 dB, "
                    "75 에서 +3~4.5 dB. **양의 방향**이라는 것이 이 항의 핵심이다."),
            },
            "mechanism_2_gate_exclusion_pushes_the_other_way": {
                "what": "우리 lit-PO 는 조명게이트 (n̂·û_i>0) 와 수신게이트 (n̂·û_s>0) 를 둘 다 요구한다. "
                        "theta_b 가 커질수록 두 게이트의 교집합(법선 구면에서)이 좁아진다 — theta_b=90 에서는 "
                        "법선구의 1/4 만 남는다. 기여면이 줄면 sigma 가 내려간다.",
                "code_evidence": "src/rcs_sbr.py:560-562 — 'beta->180 에서 조명게이트와 수신게이트가 상호배타 -> sigma≡0. "
                                 "lit-PO 는 그림자복사(Babinet 전방로브)를 못 낸다 -> 후방~중간 바이스태틱각(beta<=90급)에만 유효.'",
                "sign": "negative",
            },
            "mechanism_3_single_illumination_grid_reuse": {
                "what": "조명 격자는 û_i 하나로만 쏜다. û_s 쪽으로 거의 스쳐 보이는 면은 표본이 성기게 잡히고, "
                        "코히런트 합에서 양자화 손실이 난다. 평판 실측에서 cells_across_reverse 가 "
                        "beta=5 의 29.8 에서 beta=75 의 7.7 로 줄었다.",
                "sign": "negative, 그리고 분산이 커진다",
            },
            "mechanism_4_exit_visibility_and_first_order_transmission": {
                "what": "출사 가시성 그림자광선(D4 정정)이 theta_b>0 에서만 실제로 면을 깎는다(모노에서는 no-op, 실측 0.000 dB). "
                        "투과 출사경로도 입사 tau 로 근사한 1차 투과라 바이스태틱 비대칭을 더 키운다(rcs_sbr.py:567).",
                "sign": "negative",
            },
            "net_prediction": {
                "magnitude": "|DL(theta_b) - DL(0)| 는 theta_b 에 단조증가. 0/15/30/45/60/75/90 에서 "
                             "0 / <=0.5 / <=1.0 / <=2.5 / <=5 / <=10 / <=16 dB.",
                "sign": ("theta_b<=45 에서는 obliquity 인플레이션(+)이 게이트배제(-)와 비슷한 크기라 부호를 못 정한다. "
                         "theta_b>=60 에서는 게이트배제와 표본손실이 이기므로 **음(-)** 으로 간다고 예측한다."),
                "why_75_and_90_are_ungradeable": (
                    "⭐ 75도에서 상반성 위반 상한이 8.75 dB, 90도에서는 발산한다. 게다가 90도에서는 "
                    "게이트 교집합이 법선구의 1/4 로 줄어 기하 자체가 다른 문제가 된다. "
                    "그 두 열에서 우리가 무엇을 내든 그것은 커널의 **알려진 유효범위 밖**이므로 "
                    "합격/불합격 판정에 넣지 않는다. 사전에 못 박는다 — 사후에 빼면 체리피킹이다."),
            },
            "we_will_not_reproduce_the_das_taper": {
                "claim": "⭐ Das 의 theta_b 의존(-0.6153*sin^2 theta_b, phantom3/mini2/m350rtk 공통)을 "
                         "우리가 재현하지 **못할 것**이라고 예측한다. 우리 Delta_mu(theta_b) 의 폭은 그보다 "
                         "적어도 3배 클 것이다(Das 는 theta_b=90 에서 -0.63 dB 뿐).",
                "why_that_is_not_a_failure": (
                    "그 21 셀은 das_fleet_spec 의 등급 D — **측정이 아니라** theta_b=0 적합에 씌운 해석 taper 다. "
                    "세 기체의 delta_b 가 0.01 dB 안에서 같고 eps 와 a 는 theta_b 에 걸쳐 완전히 동일하다. "
                    "거기에 맞대는 것은 Das 의 모델 가정을 검사하는 것이지 측정을 검사하는 게 아니다. "
                    "일치해도 물리 검증이 아니고, 불일치해도 반증이 아니다."),
                "independent_scale_evidence": {
                    "what": "우리가 이미 잰 이등분선 근사 오차 — beta=45 에서 rms 중앙 7.47 dB · p95 최대 20.04 dB "
                            "(outputs/geometry_benchmark.json :: readjudication.claims[17].evidence, "
                            "원천 geometry_grid.json :: sigma_transfer). beta=0 에서는 전부 정확히 0.",
                    "what_it_means_here": (
                        "그 7.47 dB 는 **자세별(aspect-wise) rms** 이지 방위평균 레벨이동이 아니다. 방위 전주기 평균은 "
                        "그 산포를 크게 깎는다. 그래도 그것이 말하는 바는 분명하다 — beta=45 에서 진짜 바이스태틱 sigma 는 "
                        "모노스태틱 sigma 와 자세마다 7 dB 규모로 다르다. Das 의 taper 가 주장하는 -0.29 dB 는 "
                        "그 물리와 **한 자릿수** 다르다. 즉 taper 는 물리량이 아니라 평활화 모델이다. "
                        "우리가 방위평균 후에도 1 dB 이상의 폭을 내면 그건 우리 오류가 아니라 taper 의 성질이다."),
                    "our_azimuth_averaged_prediction": "|Delta_mu_ours(45) - Delta_mu_ours(0)| in [0.3, 3.5] dB, 중앙 1.2 dB",
                },
            },
            "the_only_real_bistatic_test_is_phantom2": {
                "what": "phantom2 의 7 열만이 실측 바이스태틱이다(등급 C). 나머지 21 셀은 D 다.",
                "pre_registered_null": ("H0 = 'Das 의 a(theta_b) 산포(std 0.189 dB/GHz)는 적합잡음이다.' "
                                        "das_fleet_spec 의 chi2 검정이 상관길이 1.5~5.0 GHz 어느 값에서도 "
                                        "p = 0.50~0.95 로 이미 그렇게 말한다."),
                "our_prediction": ("우리 a_ours(theta_b) 의 표본표준편차 < 0.15 dB/GHz. 즉 **재현하지 못한다**. "
                                   "이것은 예측된 결과이고 H0 의 보강증거일 뿐 결정적 증거가 아니다."),
                "the_surprising_outcome_that_would_flip_it": (
                    "⭐ 만약 우리 a_ours(theta_b) 의 std >= 0.19 dB/GHz 이고 **동시에** Das 의 7 값과 "
                    "Pearson r > 0.7 로 상관하면, 요동은 물리다. 그 경우 das_fleet_spec 의 "
                    "finding_phantom2_slope_anomaly 를 우리가 반증한 것이 된다. 이 방향으로 검정을 건다."),
                "level_shape_prediction": (
                    "phantom2 의 실측 Delta_mu(theta_b) 는 밴드중심에서 0/-1.85/-1.02/-2.66/-3.75/-2.04/-0.71 dB 로 "
                    "**비단조**다(60도 최저, 90도에서 거의 복귀). 우리 시뮬은 단조에 가깝게 내려갈 것으로 예측한다 -> "
                    "theta_b=90 에서 가장 크게 어긋난다. 그 어긋남의 부호는 음(우리가 더 낮다)."),
            },
        },

        # ------------------------------------------------------------------ 3. 합격 규칙
        "pass_rule": {
            "what_is_being_claimed": (
                "'메쉬 방법이 검증됐다' = 우리 CAD/메쉬 파이프라인 + SBR+PO 커널이 **한 기체에 맞춘 것이 아니라** "
                "기체·대역이 바뀌어도 같은 크기의, 같은 부호의, 하나의 계통오차만 남긴다. "
                "정확도 주장이 아니라 **재현성·이전가능성** 주장이다."),
            "primary_gate_level_at_theta_b_0": {
                "N": 4,
                "P1_all": "4 기체 전부 |DL(0)| <= 6.0 dB",
                "P2_most": "4 중 **3 이상**이 |DL(0)| <= 4.0 dB",
                "P3_spread": "⭐ max(DL(0)) - min(DL(0)) <= 6.0 dB — 오차가 기체마다 흩어진 게 아니라 **공통 오프셋**일 것",
                "P4_sign": "4 중 3 이상이 같은 부호",
                "all_four_required": True,
                "why_not_all_four_at_4dB": (
                    "⭐ 합격선을 문헌 자신의 내부 불일치보다 좁게 잡을 수 없다. 같은 원자료를 쓴 Das 와 Yuan 이 "
                    "phantom3 레벨에서 4.1 dB 어긋나고(p3_validation.verdict.das_elevation_pooling_is_an_inference), "
                    "규약 분기가 0.93 dB, 고도항이 2.08 dB 다. 이 셋만으로 이미 ~4 dB 다. "
                    "따라서 개별 셀 4 dB · 전체 6 dB 가 물리적으로 가능한 가장 좁은 문턱이다."),
                "why_spread_is_the_decisive_one": (
                    "⭐⭐ phantom3 라운드(N=1)는 '레벨이 -4.9 dB 다' 까지밖에 못 말했다. 그 한 수가 "
                    "커널의 성질인지 그 기체 메쉬의 성질인지 구별할 수 없었다. N=4 에서 산포가 좁으면 "
                    "**커널의 성질**이고 스칼라 하나로 교정 가능하다. 산포가 넓으면 기체마다 다른 이야기이고, "
                    "그건 방법이 아니라 기체별 맞춤이었다는 뜻이다. 그래서 P3 를 못 넘기면 나머지가 다 통과해도 "
                    "'검증' 이라고 말하지 않는다."),
            },
            "slope_gate": {
                "graded_airframes": ["phantom3", "phantom2"],
                "excluded_and_why": {
                    "mini2": "창 6 GHz -> 예상 SE(a) ~ 0.28 dB/GHz 가 Das 의 a=0.07 의 4배. 검정력이 없다.",
                    "m350rtk": "같은 이유. Das 의 a=0.17 의 1.6배.",
                },
                "S1": "phantom3 와 phantom2 둘 다 |Da| <= 0.25 dB/GHz **또는** Da 가 우리 자신의 95% CI 안에서 0 과 구별 안 됨",
                "S2_required": "2/2",
                "note": ("phantom3 는 이미 Da = +0.210 (vs Das) / +0.105 (vs Yuan theta90) 로 잰 값이 있다. "
                         "0.25 문턱은 그것을 **간신히** 통과시킨다 — 일부러 그렇게 뒀다. 문턱을 0.15 로 잡으면 "
                         "이미 아는 값으로 실패가 확정되고, 0.35 로 잡으면 아무것도 못 거른다."),
                "underpowered_cells_are_reported_not_graded": True,
            },
            "bistatic_gate": {
                "D_grade_cells_are_not_graded": (
                    "phantom3·mini2·m350rtk 의 theta_b=15~90 (총 18 셀)은 판정에 안 쓴다. 측정이 아니다. "
                    "일치해도 물리 검증이 아니고 불일치해도 반증이 아니다."),
                "C_grade_phantom2_test": (
                    "B1 우리 a_ours(theta_b) 의 std < 0.15 dB/GHz 이면 'Das 의 산포는 적합잡음' 이라는 사전등록 H0 를 지지한다(예측대로). "
                    "B2 std >= 0.19 **이고** Das 7 값과 Pearson r > 0.7 이면 H0 반증 — 그건 우리가 놀란 것이고 기록에 남긴다. "
                    "B3 둘 다 아니면 무정보."),
                "ungradeable_by_construction": "모든 기체의 theta_b = 75, 90 — 커널의 선언된 유효범위 밖(상반성 위반 상한 8.75 dB / 발산)",
                "graded_bistatic_cells": "phantom2 theta_b = 15, 30, 45, 60 (4 셀). |DL(theta_b) - DL(0)| <= 5.0 dB 를 요구한다.",
            },
            "verdict_ladder": {
                "VALIDATED": "P1 & P2 & P3 & P4 & (슬로프 2/2) & (phantom2 바이스태틱 4셀 통과)",
                "PARTIAL": "P1 & P3 는 통과하나 P2 또는 슬로프 또는 바이스태틱에서 실패",
                "NOT_VALIDATED": "⭐ P3(산포 <= 6 dB) 실패 — 나머지가 다 통과해도 여기 걸리면 '검증' 이라 말하지 않는다",
                "REFUTED": "어느 기체든 |DL(0)| > 10 dB, 또는 부호가 2:2 로 갈리면서 양쪽 다 |DL(0)| > 4 dB",
            },
            "answer_to_all_or_3_of_4": (
                "⭐ 답: **전부도 아니고 3/4 도 아니다 — 두 문턱을 겹쳐 쓴다.** 개별 셀은 4 기체 전부 6 dB 를 넘으면 안 되고(P1), "
                "그중 3 이상이 4 dB 안에 들어야 하며(P2), 그 위에 **산포 6 dB**(P3)가 결정권을 갖는다. "
                "'전부 4 dB' 는 문헌 자신의 내부 불일치(4.1 dB)보다 좁아서 물리적으로 불가능하고, "
                "'3/4 만' 은 남은 하나가 -12 dB 여도 통과시켜 버린다. 레벨만/기울기만도 아니다 — "
                "레벨은 4 기체 전부, 기울기는 창이 긴 2 기체만, 바이스태틱은 실측인 1 기체만 등급을 매긴다."),
        },

        # ------------------------------------------------------------------ 4. 실패가 뜻하는 것
        "fail_means": {
            "phantom3": {
                "role": "통제군(control). 새 정보 없음.",
                "if_it_fails": ("함대 규약으로 다시 낸 DL(0) 이 p3_validation 의 -3.01 dB 에서 1.0 dB 넘게 움직이면 "
                                "실패한 것은 물리가 아니라 **우리 프로토콜**이다 — 규약 오프셋(+2.5068), 방위격자 "
                                "(-90:2:90, 시작각), 적합창 중 하나를 잘못 적용했다는 뜻이다. 다른 3 기체의 수를 "
                                "읽기 전에 여기부터 고쳐야 한다."),
                "cannot_conclude": "phantom3 하나로는 커널 오류와 메쉬 오류를 구별할 수 없다. 그게 이 라운드를 하는 이유다.",
            },
            "phantom2": {
                "role": "유일한 실측 바이스태틱(C급). 절대레벨은 가장 약한 증거.",
                "if_level_fails": ("|DL(0)| > 6 dB 는 **세 갈래로 갈리고 우리는 그것을 못 가른다** — "
                                   "(a) 근거리장 2.6 m 에서 잰 값이 표준적 의미의 sigma 가 아니거나, "
                                   "(b) phantom3 대리 메쉬가 다른 기체이거나, (c) 우리 커널. "
                                   "⛔ 따라서 phantom2 의 레벨 실패만으로 메쉬 방법을 반증하면 안 된다."),
                "diagnostic_direction": ("⭐ 부호가 정보를 준다. DL 이 크게 **양수**면 측정 쪽이 낮다는 뜻이고 "
                                         "그것은 근거리장 과소조명(표적 횡단 위상오차 184~244도)의 서명이다. "
                                         "크게 **음수**면 대리 메쉬나 우리 커널 쪽이다."),
                "if_bistatic_slope_scatter_fails": ("우리가 Das 의 a(theta_b) 산포를 재현해 버리면 "
                                                    "das_fleet_spec.finding_phantom2_slope_anomaly 가 틀린 것이고, "
                                                    "그 요동은 물리다. 그건 실패가 아니라 **발견**이다. 그렇게 기록한다."),
            },
            "mini2": {
                "role": "⭐⭐ 이 라운드에서 정보량이 가장 큰 셀.",
                "why": ("형상이 DJI 자신의 CAD 에서 왔고(자유도 비 3.65 vs phantom3 12.76), 실루엣이 상한 대비 "
                        "77.3% 로 몰딩 셸 기체 중 1위이며, 방위격자가 우리와 정확히 같아 phantom3 를 괴롭힌 "
                        "180도 호 시작각 모호성(±2.2 dB)이 없다. 게다가 모든 지배 부위가 ka >= 4.4 라 "
                        "저-ka 변명도 못 한다."),
                "if_it_fails": ("⭐ |DL(0)| > 6 dB 이면 오차는 **메쉬가 아니라 커널**이다. 메쉬 쪽 변명이 "
                                "구조적으로 다 막혀 있기 때문이다. 남는 후보는 PO 자체(PTD 결손), 재질 |Gamma| "
                                "(body 0.28 / prop 0.25 등), 무편파 스칼라 근사, 셸 투과 모델, 그리고 "
                                "선형-vs-dB 평균 규약이다. 그 경우 다음 라운드는 메쉬가 아니라 커널을 쳐야 한다."),
                "if_it_passes_while_phantom3_stays_at_minus_5": (
                    "⭐⭐ 이게 이 라운드가 낼 수 있는 **가장 값진 결과**다 — phantom3 의 결손이 "
                    "메쉬 문제였다는 뜻이 된다(P3 셸 단면법칙은 phantom4 에서 상속한 것이고 높이도 185 vs 200 mm 다). "
                    "그러면 '메쉬 방법' 은 검증되고 phantom3 개별 메쉬가 반증된다. 두 결론을 섞지 말 것."),
                "if_it_passes_at_21_27_but_H_ka_wins": (
                    "⚠ DL(mini2) ~ 0 인데 phantom3 의 1.8-6.0 GHz 가 여전히 -8~-3.4 dB 이면 "
                    "'우리 커널은 광학영역에서만 맞는다' 가 확정된다. 표면상 합격이지만 **report12 의 디텍션 결론이 "
                    "사는 대역은 교정되지 않은 채 남는다**. 합격 문구를 그 조건과 함께 적어야 한다."),
            },
            "m350rtk": {
                "role": "가장 큰 기체·가장 큰 ka. 그러나 증거가 가장 얇다(사진 1장, IoU 56.0%).",
                "if_it_fails": ("진단력이 약하다. 부호가 정해진 교란항이 셋이나 있다 — "
                                "(1) 배터리 앞의 없는 유전체 셸 -0.71 dB, (2) bbox -4.8%/-6.5% -> -0.5~-1.0 dB, "
                                "(3) CATR 정적영역 미확인(2D^2/lambda = 199 m) -> 측정 쪽이 낮으면 우리에게 유리한 방향. "
                                "⭐ 음의 실패면 (1)(2)를 먼저 의심하라 — 둘 다 **고칠 수 있는 설정 결함**이지 "
                                "방법의 반증이 아니다. 그 경우 '커널 설정 버그' 로 기록하고 재실행한다."),
                "if_it_alone_fails_while_the_other_three_pass": (
                    "P2(3/4 가 4 dB 안)는 살고 P1(전부 6 dB 안)이 걸릴 수 있다. 그 경우 판정은 PARTIAL 이고, "
                    "위 세 교란항을 제거한 재실행 전까지 '검증' 이라고 말하지 않는다."),
                "if_it_passes": ("ka 197~253 의 완전 광학영역에서 맞는다는 뜻이고, 이는 PO 의 홈그라운드다. "
                                 "⚠ 그것만으로 우리 운용대역(1.8-6.0 GHz, ka 0.3~5)이 검증되지는 **않는다**. "
                                 "das_fleet_spec 의 band_rule 이 외삽을 금지한 이유가 그것이다."),
            },
            "cross_airframe_patterns": {
                "uniform_minus_5_across_all_four": (
                    "1.8~27 GHz 15배 대역폭, 0.21~1.05 m 5배 크기에 걸쳐 같은 -5 dB 이면 H_flat 확정. "
                    "⭐ 이건 메쉬 방법에는 **좋은 소식**이다 — 형상과 각도패턴은 맞고 스칼라 하나가 틀린 것이다. "
                    "용의자는 재질 |Gamma| · 편파(VV vs 무편파 스칼라) · 보정규약이고 전부 단일 스칼라 교정 대상이다."),
                "shrinks_to_zero_at_21_27ghz": (
                    "H_ka 확정. 메쉬 방법은 광학영역에서만 검증되고, 우리 디텍션 대역은 미교정으로 남는다. "
                    "다음 과제는 PTD 항의 강화이지 메쉬 정밀화가 아니다."),
                "scattered_signs_and_magnitudes": (
                    "⭐ 최악의 결과. P3(산포) 실패 -> NOT_VALIDATED. 그건 '우리 파이프라인이 기체마다 다른 오차를 낸다' "
                    "= 방법이 아니라 기체별 맞춤이었다는 뜻이다. 이 경우 절대 sigma 주장을 전부 내려야 한다."),
            },
            "what_no_outcome_can_establish": [
                "⛔ 어떤 결과도 '우리 sigma 가 정확하다' 를 세우지 못한다. 앵커가 네 기체지만 측정체인은 둘뿐이고"
                "(오울루 = phantom2, Southeast Univ./Wei Fan = 나머지 셋), 후자 셋은 같은 제공자다.",
                "⛔ D 등급 18 셀에서의 일치는 어떤 것도 세우지 못한다. Das 의 taper 를 검사하는 것뿐이다.",
                "⛔ 21-27 GHz 에서의 합격은 1.8-6.0 GHz 로 외삽되지 않는다(외삽 배율 4~6배).",
                "⛔ 편파가 미확인인 mini2·m350rtk 에서 잘 맞아도 편파 무관성을 세우지 못한다.",
            ],
        },

        "execution_contract": {
            "geometry": "각 theta_b 에서 el=0, 입사 az=phi, 산란 az=phi+theta_b (표적 좌표계). ⛔ 이등분선 고정 방식 금지.",
            "azimuth_grids": {"phantom2": "0:1:360", "phantom3": "-90:2:90", "mini2": "0:0.5:360",
                              "m350rtk": "0:0.5:360"},
            "bands": {k: list(v) for k, v in BANDS.items()},
            "phantom2_fit_domain": "200 MHz 서브밴드 중심 150 점(11.0~25.9 GHz)",
            "statistic": "mu = 10log10(mean_phi sigma_lin) 로 내고 Das 쪽에 +2.5068 dB 를 얹어 맞춘다. "
                         "규약 불확도 0.9254 dB 를 모든 DL 에 병기한다.",
            "kernel_settings_frozen_now": {"div": 16, "jitter": 2, "max_bounce": 1, "penetrate": True,
                                           "ptd": "p3_ours 와 동일 설정을 쓴다 — 여기서 바꾸면 통제군이 깨진다",
                                           "symmetrize": False,
                                           "symmetrize_note": "⭐ 지금 켜지 않는다. 켜면 상반성은 성립하지만 "
                                                              "정확도 개선의 증거가 없고, 무엇보다 통제군(phantom3)과 "
                                                              "설정이 달라진다. theta_b>0 진단용으로 **별도 열**에 "
                                                              "부기할 수는 있다."},
            "phantom3_is_the_control": "먼저 돌려서 -3.01 dB 를 ±1.0 dB 로 재현하는지 확인한 뒤에만 나머지 3 기체를 읽는다.",
            "no_tuning": "⛔ 결과를 본 뒤 메쉬·재질·격자를 고쳐 다시 맞추지 않는다. 안 맞으면 안 맞는 채로 적는다.",
        },

        "sealed_summary_one_line": (
            "4 기체 theta_b=0 레벨오차는 -3~-4 dB 근처에 모일 것이고(산포 <= 6 dB), 기울기는 창이 긴 2 기체에서만 "
            "판정 가능하며, theta_b 가 커질수록 우리 오차는 커지되 75/90 도는 커널 유효범위 밖이라 등급을 안 매긴다. "
            "Das 의 -0.6153 sin^2 theta_b taper 는 재현되지 않을 것이며 그것은 실패가 아니다."),
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print("wrote", OUT, os.path.getsize(OUT), "bytes")
    return doc


if __name__ == "__main__":
    main()
