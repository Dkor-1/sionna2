#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""기체별 «그 기체의 진짜 프로펠러» 법칙 확정 — 2026-08-16.

무엇을 하나
  같은 날 세 팀이 낸 계측 원장 넷을 한 자로 모아서, **기체 10종 각각에 그 기체의
  순정 프롭 평면형**을 세운다. 지금 코드는 c_max/R = 0.25 라는 상수 하나와 3DR Solo
  에서 베낀 시위 분포 하나를 10기종 전부에 걸고 있다 — 즉 «모든 드론에 같은 프로펠러를
  달아 놓은» 상태다.

입력 원장 (이 라운드가 새로 재지 않는다 — 모으고 한 자로 맞추는 일만 한다)
  outputs/prop_measure_mini2_reference_0816.json   [A]  DJI Mini 2 공식 3D
  outputs/prop_measure_mini2_xcheck_0816.json      [A]  위의 독립 교차검증
  outputs/prop_measure_matrice4e_0816.json         [B]  1157F / 1154F 제품 렌더
  outputs/prop_measure_mavic4pro_mini5pro_0816.json[B-/C] 1158F / 6028F 사진
  outputs/prop_measure_others_0816.json            [A-~D] Yuneec 3D · 1552 · 9450 · 2110s
  outputs/prop_identity_0816.json                  프롭 모델명 확정

⛔ 정책: GPU 미사용 · git 미접촉 · 코드 «기본값» 미변경(새 법칙은 인자로 골라야 켜진다).
"""
from __future__ import annotations

import json
import math
import os
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
OUT = os.path.join(ROOT, "outputs")

T0 = time.time()

# --------------------------------------------------------------------------- #
#  0. 규약 — 이게 다르면 비교가 무의미하다
# --------------------------------------------------------------------------- #
#  · c_arc   : r·Δθ = 회전축에서 본 **투영 호폭**. 사진이 줄 수 있는 유일한 값.
#  · c_cal   : 반경 r 원통 단면의 최대 캘리퍼 = **설계(진짜) 시위**.
#              `drone_cad._airfoil` 이 익형을 세울 때 쓰는 길이이자 `CHORD_MAX_OVER_R`
#              가 뜻하는 값이다. ⇒ **코드 자리에는 c_cal 을 넣어야 한다.**
#  · 다리 B  : c_cal / c_arc. 사진 유래 값을 코드 자리로 옮기는 환산계수.
GRID = (0.00, 0.07, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50,
        0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 0.98, 1.00)
ROOT_FRAC = 0.070          # drone_cad.build_propeller_cad 가 쓰는 날 뿌리
BAND = (0.25, 0.95)        # 사진 계측의 공통 유효 밴드


def _load(name):
    with open(os.path.join(OUT, name), encoding="utf-8") as f:
        return json.load(f)


L_MINI2 = _load("prop_measure_mini2_reference_0816.json")
L_M4E = _load("prop_measure_matrice4e_0816.json")
L_MAV = _load("prop_measure_mavic4pro_mini5pro_0816.json")
L_OTH = _load("prop_measure_others_0816.json")
L_ID = _load("prop_identity_0816.json")

checks = []          # 원장에서 읽은 값이 내가 적은 값과 같은지 — 손으로 옮기다 틀리는 것을 막는다


def take(value, expect, what, tol=1e-6):
    ok = abs(float(value) - float(expect)) <= tol * max(1.0, abs(float(expect)))
    checks.append(dict(what=what, ledger=float(value), used=float(expect), ok=bool(ok)))
    if not ok:
        raise SystemExit(f"⛔ 원장과 어긋난다: {what} 원장={value} 내가쓴값={expect}")
    return float(expect)


# --------------------------------------------------------------------------- #
#  1. 다리(arc → cal) 감사 — «되돌리기» 를 참값 아는 프롭 둘에 대 본다
# --------------------------------------------------------------------------- #
#  왜: 사진은 c_arc 만 준다. 코드 자리는 c_cal 이다. 그 사이를 어떻게 건널지가
#      사진 유래 6기종의 값을 통째로 몇 % 움직인다. 두 갈래가 있다 —
#        (ⓐ) 기하 되돌리기: c_cal = c_arc / cos θ  (θ = 그 반경의 국소 피치각)
#        (ⓑ) 실측 다리   : 3D 가 있는 프롭에서 c_cal 과 c_arc 를 **둘 다 재서** 비율을 쓴다
#      3D 가 있는 프롭이 둘(Mini 2 4726F · Yuneec A/B) 이므로 ⓐ 를 ⓑ 로 검정할 수 있다.
mini2_theta = L_MINI2["F_reference_curve"]["theta_deg"]
mini2_peak_rr = float(L_MINI2["F_reference_curve"]["peak_at_rr"])
th_at_peak = float(np.interp(mini2_peak_rr,
                             [float(k) for k in mini2_theta],
                             [float(v) for v in mini2_theta.values()]))
mini2_geom_bridge = 1.0 / math.cos(math.radians(th_at_peak))

# 실측 다리 — Mini 2 는 로터마다 따로 있다. 뒤 2개는 힌지가 30° 덜 펴져 있어
# 투영이 오염된다(원장 D_deployment_angle) ⇒ **완전전개 로터만** 이 깨끗한 값이다.
m2_rot = L_MAV["A_ruler_validation"]["step1_cad_truth"]["per_rotor"]
m2_bridge_deployed = float(np.mean([r["c_cal_over_c_arc"] for r in m2_rot[:2]]))
m2_bridge_all8 = float(L_MAV["A_ruler_validation"]["step1_cad_truth"]
                       ["mean_bridge_c_cal_over_c_arc"])
yun_bridge = float(L_OTH["A_typhoonh480"]["cw"]["summary"]["cal_over_arc"]["mean"])

# Yuneec 쪽 기하 되돌리기 값 — 같은 방식으로 계산해 비교한다
yun_R_mm = float(L_OTH["A_typhoonh480"]["cw"]["summary"]["disc_dia_mm"]) / 2.0
yun_peak_rr = 0.445                      # 원장 c_over_cmax_arc 의 봉우리
yun_pitch_mm = 6.0 * 25.4
import drone_cad as DC                                                  # noqa: E402
k_yun = float(np.interp(yun_peak_rr, DC.PITCH_RR_DJI_MINI2, DC.PITCH_K_DJI_MINI2))
th_yun = math.degrees(math.atan(k_yun * yun_pitch_mm /
                                (2 * math.pi * yun_peak_rr * yun_R_mm)))
yun_geom_bridge = 1.0 / math.cos(math.radians(th_yun))

BRIDGE = 1.031                 # ⭐ 채택값 — 아래 A_bridge_audit 의 근거를 보라
BRIDGE_BAND = (1.020, 1.045)

A_bridge = dict(
    question="사진의 투영 호폭(c_arc)을 코드가 쓰는 설계 시위(c_cal) 로 어떻게 옮기나",
    route_geometric=dict(
        formula="c_cal = c_arc / cos θ(r)",
        mini2_predicted=round(mini2_geom_bridge, 4),
        mini2_theta_deg_at_peak=round(th_at_peak, 2),
        typhoon_predicted=round(yun_geom_bridge, 4),
        typhoon_theta_deg_at_peak=round(th_yun, 2),
    ),
    route_measured=dict(
        mini2_fully_deployed=round(m2_bridge_deployed, 4),
        mini2_all8=round(m2_bridge_all8, 4),
        mini2_all8_note_ko="뒤 로터 2개는 힌지가 30° 덜 펴져 투영이 오염됐다 — 깨끗한 값은 완전전개 쪽이다.",
        typhoon_3d=round(yun_bridge, 4),
    ),
    finding_ko=(
        f"⭐**기하 되돌리기는 참값 아는 프롭 둘에서 똑같이 +{100*(mini2_geom_bridge/m2_bridge_deployed-1):.1f} %·"
        f"+{100*(yun_geom_bridge/yun_bridge-1):.1f} % 높게 나온다.** 이유는 알 수 있다 — c_arc 는 «반경 r 에서의 "
        "각폭 r·Δθ» 라 (1) 두께가 있는 단면은 비틀려도 t·sinθ 만큼 폭을 남기고 (2) 스윕된 단면은 "
        "반경선에 비스듬히 놓여 각폭을 더 벌린다. 둘 다 c_arc 를 c·cosθ 보다 **크게** 만든다. "
        "1/cosθ 는 그 둘을 무시하므로 다리를 과대평가한다."),
    adopted=BRIDGE,
    adopted_band=list(BRIDGE_BAND),
    adopted_why_ko=(
        "실측 다리 두 개(Mini 2 완전전개 1.020 · Yuneec 1.045)의 가운데. 우연히 원장이 이미 쓴 "
        "Mini 2 8장 평균 1.031 과 같다 — 그래서 형제 원장이 발표한 mavic4pro 0.1824 가 그대로 살아난다. "
        "다리 불확실도 ±1.2 % 는 사진 계측 자체의 오차(3~10 %)보다 훨씬 작다."),
    what_this_costs_ko=(
        f"⛔matrice4e 원장이 권한 0.211 은 기하 되돌리기(0.2078)와 우리 로프트 되맞춤(0.2144)의 "
        f"가운데다. 위 감사대로면 기하 되돌리기 쪽이 ~3.8 % 높으므로, 실측 다리로는 "
        f"{0.19482154254164144 * BRIDGE:.4f} 가 된다. 이 라운드는 **실측 다리**를 정본으로 쓰고 "
        f"0.211 을 상단 대안으로 남긴다(차이 5 %)."),
)

# --------------------------------------------------------------------------- #
#  2. [A] 기준 곡선 — DJI Mini 2 공식 CAD. 나머지 기체의 «빈 구간 메우개» 로도 쓴다
# --------------------------------------------------------------------------- #
_m2 = L_MINI2["F_reference_curve"]["chord_norm_c_over_cmax"]
MINI2_A = {float(k): float(v) for k, v in _m2.items()}          # 0.15 ~ 0.98, [A]
#  0.15R 안쪽과 1.00R 은 **실측이 없다**. 그대로 적어 둔다:
#    · 0.00·0.07R — 코드의 dji_mini2 판(감사 C4) 값을 0.15R 에서 이어붙게 비례로 줄인 것. [D]
#      (이 구간은 허브 반경 0.085R 안쪽이라 실물에서도 허브에 파묻힌다)
#    · 1.00R      — 감사 I8 이 정한 «뭉툭한 팁» 0.200 을 같은 방식으로 이어붙인 것. [C]
_join_in = MINI2_A[0.15] / 0.550                                # 코드 dji_mini2 의 0.15R 값
MINI2_A[0.00] = round(0.300 * _join_in, 4)
MINI2_A[0.07] = round(0.420 * _join_in, 4)
MINI2_A[1.00] = round(0.200 * (MINI2_A[0.95] / 0.475), 4)

take(L_MINI2["H_headline"]["c_max_over_R"], 0.2575, "mini2 c_max/R", tol=2e-3)
take(L_OTH["H_headline"]["rows"][0]["use_c_max_over_R_caliper"], 0.17683,
     "typhoonh480 c_max/R (caliper)", tol=1e-3)


def _mini2_shape(rr):
    xs = sorted(MINI2_A)
    return float(np.interp(rr, xs, [MINI2_A[x] for x in xs]))


def build_curve(meas: dict[float, float]) -> tuple[dict, dict]:
    """계측 구간은 그대로 두고, 그 **바깥만** [A] 곡선의 모양으로 이어붙인다.

    규칙 하나로 양끝을 다 처리한다 — 계측 첫 점 r0 안쪽은 mini2 곡선을 r0 에서 만나도록
    비례로 줄여 쓰고, 마지막 점 r1 바깥도 같은 식으로 잇는다. 왜 mini2 인가: 저장소에서
    **스팬 전체가 [A] 인 유일한 프롭**이기 때문이다. 그 구간의 등급은 [C](바깥) / [D](뿌리) 다.
    """
    r0, r1 = min(meas), max(meas)
    out, grade = {}, {}
    for rr in GRID:
        if r0 - 1e-9 <= rr <= r1 + 1e-9:
            xs = sorted(meas)
            out[rr] = float(np.interp(rr, xs, [meas[x] for x in xs]))
            grade[rr] = "measured"
        elif rr < r0:
            out[rr] = meas[r0] * _mini2_shape(rr) / _mini2_shape(r0)
            grade[rr] = "root_filled_D"
        else:
            out[rr] = meas[r1] * _mini2_shape(rr) / _mini2_shape(r1)
            grade[rr] = "tip_filled_C"
    return out, grade


# --------------------------------------------------------------------------- #
#  3. 기체별 «그 기체의 진짜 프롭» — 계측 원장에서 그대로 옮긴다
# --------------------------------------------------------------------------- #
def _norm(d):
    return {float(k): float(v) for k, v in d.items()}


EV: dict[str, dict] = {}

# ── mini2 — [A] 공식 3D. 저장소 유일 -----------------------------------------
EV["mini2"] = dict(
    prop="DJI 4726F", nominal="119.4 × 66.0 mm (4.7 × 2.6 in), 2날 접이식",
    grade="A", axis="caliper",
    cmax=take(L_MINI2["F_reference_curve"]["c_max_over_R"], 0.2575, "mini2 cmax", 2e-3),
    meas={k: v for k, v in MINI2_A.items() if 0.15 <= k <= 0.98},
    source="assets/meshes/reference/WM161_zhankai_1k.glb (DJI 공식 3D, 완전전개 앞 프롭 날 4장)",
    ledger="outputs/prop_measure_mini2_reference_0816.json",
    unc_pct=0.4,
    t_mm=0.478, tc_max=0.058,
    t_note_ko="시위가중 평균 두께 0.478 mm (0.20~0.96R) · 최대 0.75 mm · 중앙부 t_max/c 0.055~0.058",
    caveat_ko="GLB 는 제품페이지용 1k 간략화판이다 — 겉치수는 0.03 % 로 맞지만 두께가 같은 정도로 "
              "검증된 것은 아니다. 코드·감사의 0.262 는 덜 펴진 뒤 프롭 2개를 섞어서 1.7 % 높았다.",
)

# ── typhoonh480 — [A-] 그 프롭 자체의 3D --------------------------------------
_ty_cw = L_OTH["A_typhoonh480"]["cw"]["summary"]["c_over_cmax_arc_mean"]
_ty_ccw = L_OTH["A_typhoonh480"]["ccw"]["summary"]["c_over_cmax_arc_mean"]
EV["typhoonh480"] = dict(
    prop="Yuneec Propeller A / B (YUNTYH118A / YUNTYH118B)",
    nominal="228.6 mm (9.0 in) × 피치 6.0 in [DERIVED], 2날 고정, 헥사 A3+B3",
    grade="A-", axis="caliper",
    cmax=take(L_OTH["A_typhoonh480"]["cw"]["summary"]["caliper_c_max_over_R"]["mean"],
              0.17683, "typhoon cmax", 1e-3),
    meas={float(k): 0.5 * (float(_ty_cw[k]) + float(_ty_ccw[k])) for k in _ty_cw},
    source="assets/meshes/reference/prop_cw_assembly_remeshed_v3.stl + prop_ccw…(CW·CCW 날 4장)",
    ledger="outputs/prop_measure_others_0816.json §A",
    unc_pct=1.0,
    t_mm=None, tc_max=0.128,
    t_note_ko="t/c 0.086~0.128 (0.30R 0.114 · 0.50R 0.090 · 0.70R 0.090 · 0.90R 0.091), "
              "캠버 6.8 % — outputs/reference_props.json 인용. 절대 두께[mm]는 원장에 없다.",
    caveat_ko="[A] 가 아닌 이유: 상류 저장소(ethz-asl/rotors_simulator)가 메쉬 출처를 안 밝혀 "
              "«Yuneec 공식 CAD» 라는 문서 근거가 없다. 시뮬레이터 자산이지 계측 스캔이 아니다.",
)

# ── matrice4e — [B] 1157F 제품 렌더 (주력 1순위) --------------------------------
_m4e_mm = L_M4E["B_1157F_standard"]["headline"]["table_c_mm"]
_m4e_cmax_mm = float(L_M4E["B_1157F_standard"]["headline"]["c_max_mm"])
EV["matrice4e"] = dict(
    prop="DJI 1157F (표준·순정 동봉)",
    nominal="274 mm (10.8 in) × 피치 5.7 in [DERIVED 부품번호 규약], 2날 접이 퀵릴리즈",
    grade="B", axis="arc",
    cmax_arc=take(L_M4E["B_1157F_standard"]["headline"]["c_max_over_R_projected"],
                  0.19482, "matrice4e arc cmax", 1e-3),
    meas={float(k): float(v) / _m4e_cmax_mm for k, v in _m4e_mm.items() if float(k) >= 0.20},
    source="assets/photos/matrice4e/matrice4e_c02_prop_standard_1157F_pair.jpg (DJI 스토어 제품 렌더, 날 4장)",
    ledger="outputs/prop_measure_matrice4e_0816.json",
    unc_pct=3.0,
    t_mm=None, tc_max=None,
    t_note_ko="⛔못 쟀다 — 사진으로는 원리적으로 불가(겉보기 높이 = c·sinβ + t·cosβ 이고 앞항이 두께의 5배).",
    caveat_ko="[A] 불가: 공식 CAD matrice4-M4T_v2.step 에 **프로펠러가 없다**. 저소음 1154F 는 "
              "별매 액세서리라 순정이 아니다(그 프롭이면 c_max/R 0.2144·날면적 +25 %). "
              "봉우리 0.29R 로 우리 함대에서 가장 안쪽이다.",
    alt=dict(name="1154F 저소음(별매)", cmax_arc=0.21445, area_ratio=1.254,
             meas={float(k): float(v) / float(L_M4E["C_1154F_low_noise"]["headline"]["c_max_mm"])
                   for k, v in L_M4E["C_1154F_low_noise"]["headline"]["table_c_mm"].items()
                   if float(k) >= 0.20}),
)

# ── mavic4pro — [B-] 1158F 제품 사진 (주력 2순위) -------------------------------
EV["mavic4pro"] = dict(
    prop="DJI 1158F",
    nominal="267 × 147 mm (10.5 × 5.8 in), 2날 접이식, 11.8 g",
    grade="B-", axis="arc",
    cmax_arc=take(L_MAV["D_conversion_and_code_comparison"]["results"]
                  ["mavic4pro_1158F"]["c_arc_over_R_measured"], 0.1769, "mavic arc cmax", 1e-3),
    meas=_norm(L_MAV["F_chord_law_shape_vs_code"]["measured"]["mavic4pro_1158F"]["profile"]),
    source="assets/photos/mavic4pro/mavic4pro_c10_propeller_pair_1158F.jpg (프롭 2개, 산포 1.6 %)",
    ledger="outputs/prop_measure_mavic4pro_mini5pro_0816.json §C",
    unc_pct=6.0,
    t_mm=None, tc_max=None,
    t_note_ko="⛔못 쟀다 — 사진은 두께를 줄 수 없다.",
    caveat_ko="3/4 투영이라 보정 전 값은 **하한**이다(사영은 c/R 을 아래로만 민다). 사영보정 상단은 "
              "0.201. p01(FCC 실기체)은 접힌 두 날이 겹쳐 못 쓰고, 'mavic 4 pro_1/_4.png' 는 "
              "**다른 기체**(Mavic 3 계열)다.",
)

# ── mini5pro — [C] 6028F, 기체 동일성 미확정 (주력 3순위) ------------------------
EV["mini5pro"] = dict(
    prop="DJI 6028F",
    nominal="152.4 × 71.1 mm (6.0 × 2.8 in), 2날 접이식, 2.8 g",
    grade="C", axis="arc",
    cmax_arc=take(L_MAV["D_conversion_and_code_comparison"]["results"]
                  ["mini5pro_6028F"]["c_arc_over_R_all_props"], 0.2049, "mini5 arc cmax", 1e-3),
    meas=_norm(L_MAV["F_chord_law_shape_vs_code"]["measured"]["mini5pro_6028F"]["profile"]),
    source="assets/photos/mini5pro/'mini 5 pro_3.png' (로터 4개; 평면형은 가장 정면인 프롭 0·1 평균)",
    ledger="outputs/prop_measure_mavic4pro_mini5pro_0816.json §B",
    unc_pct=14.0,
    t_mm=None, tc_max=None,
    t_note_ko="⛔못 쟀다.",
    caveat_ko="⭐⭐**사진 속 기체 동일성이 미확정이다** — 그 폴더에 SOURCES.md 가 없고, 같은 배치의 "
              "'mavic 4 pro_1/_4.png' 는 다른 기종으로 확인됐다. 프롭끼리 29 % 벌어진다"
              "(아래 두 로터는 암·다리에 가려 폭이 잘린다). 밴드 0.176~0.239. "
              "가장 정면인 프롭 0·1 만 쓰면 0.2175 로 +3 % 다.",
)

# ── s1000plus — [B-] DJI 1552 상면 사진 ----------------------------------------
EV["s1000plus"] = dict(
    prop="DJI 1552 / 1552R (거울쌍)",
    nominal="381 × 132.1 mm (15 × 5.2 in), 2날 접이 탄소 블레이드 + 금속 브래킷",
    grade="B-", axis="arc",
    cmax_arc=take(L_OTH["H_headline"]["rows"][1]["use_c_max_over_R_arc"], 0.17712,
                  "s1000 arc cmax", 1e-3),
    meas=_norm(L_OTH["B_s1000plus"]["primary"]["clean_blades"]["c_over_cmax_mean"]),
    source="assets/photos/s1000plus/s1000+_1.png (상면 평면, 로터 8개 중 뿌리를 본 «깨끗한» 날 9장)",
    ledger="outputs/prop_measure_others_0816.json §B",
    unc_pct=6.0,
    t_mm=None, tc_max=None,
    t_note_ko="⛔못 쟀다. 접이 탄소 블레이드라 사출 소비자 프롭의 t/c 를 대입해도 안 맞을 가능성이 크다.",
    caveat_ko="⭐이 폴더에 SOURCES.md 가 없다(워터마크 «XCOPTER» = 판매점 자산). 문턱값 감도가 "
              "지배 오차다(110/140/170 → 0.164/0.177/0.184). 로터마다 한쪽 날이 암에 가려 잘리므로 "
              "두 날 평균(0.143)은 쓰면 안 된다. 뿌리가 브래킷이라 0.3R 안쪽은 소비자 프롭 법칙으로 "
              "채우면 틀린다.",
)

# ── phantom3 — [B] DJI 9450 공식 상면 렌더 --------------------------------------
EV["phantom3"] = dict(
    prop="DJI 9450 (자동조임)",
    nominal="240 × 127 mm (9.4 × 5.0 in), 2날 고정, 12 g, 유리섬유강화 나일론",
    grade="B", axis="arc",
    cmax_arc=take(L_OTH["H_headline"]["rows"][2]["use_c_max_over_R_arc"], 0.26273,
                  "phantom3 arc cmax", 1e-3),
    meas=_norm(L_OTH["C_phantom3"]["primary"]["clean_blades"]["c_over_cmax_mean"]),
    source="assets/photos/phantom3/phantom3_d03_official_top.png (DJI 공식 상면 렌더, 날 4장, 산포 1.5 %)",
    ledger="outputs/prop_measure_others_0816.json §C",
    unc_pct=3.0,
    t_mm=None, tc_max=None,
    t_note_ko="⛔못 쟀다.",
    caveat_ko="⭐함대에서 **가장 통통한** 프롭이고, 유일하게 지금의 0.25 상수보다 **넓다**"
              "(다른 기종은 전부 0.25 가 과대였다). FCC 실물 사진은 흩어짐이 커서 교차검증에만 썼다.",
)

# ── m350rtk — [B-] DJI 2110s 접힌 쌍 사진 ---------------------------------------
EV["m350rtk"] = dict(
    prop="DJI 2110s",
    nominal="533.4 × 254 mm (21 × 10 in), 2날 접이식",
    grade="B-", axis="arc",
    cmax_arc=take(L_OTH["H_headline"]["rows"][4]["use_c_max_over_R_arc"], 0.18057,
                  "m350 arc cmax", 1e-3),
    meas=_norm(L_OTH["E_m350rtk"]["summary"]["c_over_cmax_mean"]),
    source="assets/photos/m350rtk/… (접힌 프롭 쌍 제품사진; 축척은 그림 안에서 조립 R = r_h + L)",
    ledger="outputs/prop_measure_others_0816.json §E",
    unc_pct=10.0,
    t_mm=None, tc_max=None,
    t_note_ko="⛔못 쟀다.",
    caveat_ko="⚠프롭 2개가 11 % 어긋난다(0.171 ↔ 0.190; 거울쌍이라 같아야 한다). 원본이 520×694 로 "
              "작고 겹친 날의 이음매 판정이 원인이다. ⭐이 프롭은 0.25R 에서도 시위가 아직 오르는 중이라 "
              "규약 최대가 참 최대보다 작다(규약 밖 최대 0.197 @0.23R) — 즉 이 값은 **하한**이다. "
              "뿌리(0.25R 안쪽)는 실제로 접이 브래킷이지 익형이 아니다.",
)

# ── phantom4 — [C] phantom3 의 9450 에서 계열 유추 -------------------------------
EV["phantom4"] = dict(
    prop="DJI 9450S (유력·미해결)",
    nominal="240 × 127 mm (9.4 × 5.0 in), 2날 고정",
    grade="C", axis="arc", proxy_of="phantom3",
    cmax_arc=0.26273,
    meas=_norm(L_OTH["C_phantom3"]["primary"]["clean_blades"]["c_over_cmax_mean"]),
    source="⚠자체 측정 없음 — phantom3 의 9450 을 그대로 쓴다(같은 세대·같은 공칭 9.4×5.0 in)",
    ledger="outputs/prop_measure_others_0816.json §D",
    unc_pct=5.0,
    t_mm=None, tc_max=None,
    t_note_ko="⛔못 쟀다.",
    caveat_ko="⛔저장소 phantom4 사진 폴더는 **다른 기체**(Phantom 4 Pro+ V2.0 = 9455S)다 — "
              "거기서 재면 «고침» 이 아니라 새 오류다. 9450 ↔ 9450S 갈래로 ±3 % 를 더 본다.",
)

# ── x500v2 — [D] 근거 없음. 대리를 쓰되 못 박는다 --------------------------------
EV["x500v2"] = dict(
    prop="1045 (범용 규격 — Holybro X500 V2 킷 동봉)",
    nominal="254 × 114.3 mm (10 × 4.5 in), 2날 고정",
    grade="D", axis="arc", proxy_of="phantom3",
    cmax_arc=0.26273,
    meas=_norm(L_OTH["C_phantom3"]["primary"]["clean_blades"]["c_over_cmax_mean"]),
    source="⛔**근거 없음.** 10인치급 실측 둘(DJI 9450 9.4in 0.271 · 3DR Solo 10in 0.273)이 "
           "붙는다는 것만 근거로 9450 의 평면형을 **대리**로 쓴다",
    ledger="outputs/prop_measure_others_0816.json §F",
    unc_pct=30.0,
    t_mm=None, tc_max=None,
    t_note_ko="⛔못 쟀다.",
    caveat_ko="⛔⛔**이 기체는 대리다.** 공식 CAD 에 프롭이 없고, 프롭 근접 사진은 양 날끝이 "
              "프레임 밖이라 R 을 정의할 수 없다. 1045 는 범용 사출품이라 DJI 몰드 프롭과 계열이 "
              "다르다 — 예상 오차 ±30 %. 정면 단품 사진 한 장이면 [B] 로 승격된다.",
)

# --------------------------------------------------------------------------- #
#  4. 법칙 조립 — 계측 → 코드 자리(c_cal) 로 옮기고, 그리드에 얹는다
# --------------------------------------------------------------------------- #
LAW: dict[str, dict] = {}
for key, ev in EV.items():
    curve, gmap = build_curve(ev["meas"])
    if ev["axis"] == "caliper":
        cmax_design = ev["cmax"]
        bridge_used = 1.0
    else:
        cmax_design = ev["cmax_arc"] * BRIDGE
        bridge_used = BRIDGE
    # c(r)/R 이 물리량이다. (c_max/R)×frac(r) 로 쪼개는 것은 장부일 뿐이므로,
    # 그리드 위의 최댓값이 정확히 1.000 이 되도록 **곱이 불변인 채로** 다시 나눈다.
    c_over_R = {rr: curve[rr] * cmax_design for rr in GRID}
    cmax_grid = max(c_over_R.values())
    frac = {rr: c_over_R[rr] / cmax_grid for rr in GRID}
    LAW[key] = dict(
        prop=ev["prop"], nominal=ev["nominal"], grade=ev["grade"],
        proxy_of=ev.get("proxy_of"),
        c_max_over_R=round(cmax_grid, 5),
        c_max_over_R_axis="caliper(설계 시위) — drone_cad.CHORD_MAX_OVER_R 와 같은 자",
        #  ⚠ 두 수가 조금 다르다. 원장 헤드라인은 «날마다 자기 봉우리를 찾아 평균» 이고
        #    법칙은 «평균 곡선의 봉우리» 다. 봉우리 위치가 날마다 다르면 평균 곡선의 봉우리가
        #    더 낮다(최대의 평균 ≥ 평균의 최대). 한 장의 대표 날을 짓는 데는 **후자가 맞다.**
        c_max_over_R_ledger=round(cmax_design, 5),
        c_max_over_R_grid_gap_pct=round(100 * (cmax_grid / cmax_design - 1), 2),
        measured_arc=ev.get("cmax_arc"), bridge_used=bridge_used,
        peak_r_over_R=round(max(GRID, key=lambda r: frac[r]), 3),
        chord_rr=tuple(GRID),
        chord_frac=tuple(round(frac[rr], 4) for rr in GRID),
        segment_grade={f"{rr:.2f}": gmap[rr] for rr in GRID},
        uncertainty_pct=ev["unc_pct"],
        t_mm=ev["t_mm"], tc_max=ev["tc_max"], t_note_ko=ev["t_note_ko"],
        source=ev["source"], ledger=ev["ledger"], caveat_ko=ev["caveat_ko"],
    )
    if "alt" in ev:
        acurve, _ = build_curve(ev["alt"]["meas"])
        ac = {rr: acurve[rr] * ev["alt"]["cmax_arc"] * BRIDGE for rr in GRID}
        am = max(ac.values())
        LAW[key]["alternative"] = dict(
            name=ev["alt"]["name"], c_max_over_R=round(am, 5),
            chord_frac=tuple(round(ac[rr] / am, 4) for rr in GRID),
            blade_area_ratio_vs_stock=ev["alt"]["area_ratio"],
            note_ko="순정이 아니다(별매 액세서리). 우리 기체는 표준 프롭으로 본다.")

# --------------------------------------------------------------------------- #
#  5. 지금 값 → 새 값 → 몇 % 바뀌나
# --------------------------------------------------------------------------- #
import drones as DR                                                     # noqa: E402
from shapely.geometry import Polygon                                    # noqa: E402
from shapely.ops import unary_union                                     # noqa: E402


def area_int(rr, frac, cmax, R_mm):
    """날 1장 **설계 평면형 면적** ∫ c dr [mm²] — 뿌리 0.070R ~ 팁."""
    x = np.linspace(ROOT_FRAC, 1.0, 4001)
    c = np.interp(x, rr, frac) * cmax * R_mm
    return float(np.trapezoid(c, x * R_mm))


def silhouette_mm2(spec, chord_rr, chord_frac, cmax):
    """**실제로 지어진 메쉬**를 회전축 방향으로 눌러 잰 날 1장 실루엣 면적 [mm²].

    설계 평면형과 달리 비틀림·스윕·두께가 다 들어간 «머리 위에서 본 그림자» 다.
    build_propeller_cad 와 같은 순서로 짓는다(스윕디스크 정규화 포함)."""
    R = spec.prop_dia_mm / 1000.0 / 2.0
    P = float(spec.prop_pitch_in or 5.0) * 0.0254

    def one(Rb):
        return DC._blade(Rb, root_frac=ROOT_FRAC, chord_max=cmax, pitch_m=P, n_sec=22,
                         law="legacy", chord_rr=chord_rr, chord_frac=chord_frac)

    probe = one(R)
    V = np.asarray(probe.vertices)
    scale = R / max(float(np.sqrt(V[:, 0] ** 2 + V[:, 1] ** 2).max()), 1e-12)
    m = one(R * scale)
    V = np.asarray(m.vertices)[:, :2] * 1000.0
    F = np.asarray(m.faces)
    polys = [Polygon(V[f]) for f in F]
    polys = [p for p in polys if p.is_valid and p.area > 0]
    return float(unary_union(polys).area)


rows = []
for key, law in LAW.items():
    spec = DR.DRONES[key]
    R_mm = spec.prop_dia_mm / 2.0
    n_blade_total = spec.prop_blades * spec.num_rotors
    old = dict(
        c_max_mm=max(DC.CHORD_FRAC) * DC.CHORD_MAX_OVER_R * R_mm,
        area=area_int(DC.CHORD_RR, DC.CHORD_FRAC, DC.CHORD_MAX_OVER_R, R_mm),
        sil=silhouette_mm2(spec, DC.CHORD_RR, DC.CHORD_FRAC, DC.CHORD_MAX_OVER_R),
    )
    new = dict(
        c_max_mm=law["c_max_over_R"] * R_mm,
        area=area_int(law["chord_rr"], law["chord_frac"], law["c_max_over_R"], R_mm),
        sil=silhouette_mm2(spec, law["chord_rr"], law["chord_frac"], law["c_max_over_R"]),
    )
    rows.append(dict(
        aircraft=key, prop=law["prop"], grade=law["grade"],
        n_blades_aircraft=n_blade_total,
        c_max_mm_old=round(old["c_max_mm"], 2), c_max_mm_new=round(new["c_max_mm"], 2),
        c_max_pct=round(100 * (new["c_max_mm"] / old["c_max_mm"] - 1), 1),
        blade_area_mm2_old=round(old["area"], 1), blade_area_mm2_new=round(new["area"], 1),
        blade_area_pct=round(100 * (new["area"] / old["area"] - 1), 1),
        silhouette_mm2_old=round(old["sil"], 1), silhouette_mm2_new=round(new["sil"], 1),
        silhouette_pct=round(100 * (new["sil"] / old["sil"] - 1), 1),
        aircraft_total_blade_area_mm2_old=round(old["area"] * n_blade_total, 1),
        aircraft_total_blade_area_mm2_new=round(new["area"] * n_blade_total, 1),
        peak_r_over_R_old=0.30, peak_r_over_R_new=law["peak_r_over_R"],
        db_blade_area=round(20 * math.log10(new["area"] / old["area"]), 2),
    ))

# 기종 사이가 얼마나 벌어지나 — «같은 프롭을 달아 놓은» 상태에서는 0 이어야 한다
sp_old = [r["c_max_mm_old"] / (DR.DRONES[r["aircraft"]].prop_dia_mm / 2) for r in rows]
sp_new = [r["c_max_mm_new"] / (DR.DRONES[r["aircraft"]].prop_dia_mm / 2) for r in rows]

# --------------------------------------------------------------------------- #
#  5b. 배선 검사 — 레지스트리에 들어간 값이 위에서 계산한 법칙과 같은가,
#      그리고 `blade_law='per_airframe'` 로 지으면 정말 그 곡선이 나오는가
# --------------------------------------------------------------------------- #
wiring = []
for key, law in LAW.items():
    spec = DR.DRONES[key]
    same = (spec.prop_law_cmax_over_r == law["c_max_over_R"]
            and tuple(spec.prop_law_chord_frac or ()) == law["chord_frac"]
            and spec.prop_law_grade == law["grade"])
    cm, cm_src = DC.resolve_chord_max_over_r(spec, "per_airframe")
    rr, fr, pf_src = DC.resolve_chord_profile(spec, "per_airframe")
    wiring.append(dict(aircraft=key, registry_matches_law=bool(same),
                       resolved_cmax=cm, resolved_cmax_source=cm_src,
                       resolved_profile_source=pf_src,
                       profile_is_per_airframe=bool(rr is not None)))
    if not same:
        raise SystemExit(f"⛔ 레지스트리가 법칙과 다르다: {key}")

#  «곡선 하나를 배율만 바꿔 쓰는 것» 이 아님을 수로 못 박는다 — 정규화 곡선끼리
#  겹쳐 보고 최대 편차를 잰다. 배율만 다르면 정규화 후 전부 0 % 여야 한다.
_keys = list(LAW)
_cmp = np.array([[np.interp(r, LAW[k]["chord_rr"], LAW[k]["chord_frac"])
                  for r in np.linspace(0.25, 0.95, 15)] for k in _keys])
_pair = []
for i in range(len(_keys)):
    for j in range(i + 1, len(_keys)):
        _pair.append(dict(a=_keys[i], b=_keys[j],
                          max_dev_pct=round(float(100 * np.max(np.abs(_cmp[i] / _cmp[j] - 1))), 1)))
_pair.sort(key=lambda d: -d["max_dev_pct"])

# --------------------------------------------------------------------------- #
#  6. 원장
# --------------------------------------------------------------------------- #
led = dict(
    _meta=dict(
        title="기체별 프로펠러 법칙 — 정본 후보 (2026-08-16)",
        generated_kst=time.strftime("%Y-%m-%d %H:%M", time.localtime(time.time() + 9 * 3600)),
        script="benchmark/prop_law_by_airframe_0816.py",
        policy="GPU 미사용 · git 미접촉 · 코드 기본값 미변경(새 법칙은 blade_law='per_airframe' 로만 켜진다)",
        what_ko="계측 원장 넷을 한 자로 모아 기체 10종 각각에 **그 기체의 순정 프롭 평면형**을 세운다.",
        chord_axis_ko="여기 실린 c_max/R 은 전부 **설계 시위(caliper)** 축이다 — drone_cad 의 "
                      "CHORD_MAX_OVER_R 이 뜻하는 바로 그 자. 사진 유래 값은 다리 ×1.031 이 이미 곱해져 있다.",
        grid=list(GRID), root_frac=ROOT_FRAC,
        ledgers=[e["ledger"] for e in EV.values()],
    ),
    A_bridge_audit=A_bridge,
    B_reference_curve_mini2_A={f"{k:.2f}": round(v, 4) for k, v in sorted(MINI2_A.items())},
    C_law_by_airframe=LAW,
    D_change_table=dict(
        rows=rows,
        legend_ko=dict(
            c_max_mm="최대 시위[mm] — 날이 얼마나 통통한가",
            blade_area_mm2="날 1장 **설계 평면형** 면적 ∫c dr [mm²] (0.070R~팁)",
            silhouette_mm2="**실제로 지어진 메쉬**를 회전축에서 눌러 잰 날 1장 그림자 면적 [mm²] "
                           "— 비틀림·스윕·두께가 다 들어간 값",
            aircraft_total_blade_area_mm2="기체 전체 = 날 1장 면적 × 날수 × 로터수",
            db_blade_area="면적비를 dB 로 (20·log10). σ 는 면적² 에 걸리는 구간이 있어 참고용으로만.",
        ),
        old_law_ko="지금(legacy): 3DR Solo 시위 분포 + c_max/R = 0.25 를 **10기종 전부에** 건다.",
        spread_ko=dict(
            c_max_over_R_old_min=round(min(sp_old), 4), c_max_over_R_old_max=round(max(sp_old), 4),
            c_max_over_R_new_min=round(min(sp_new), 4), c_max_over_R_new_max=round(max(sp_new), 4),
            headline_ko=f"기종 사이 c_max/R 산포: 지금 **0 %**(전부 같은 프롭) → 새 법칙 "
                        f"**{100 * (max(sp_new) / min(sp_new) - 1):.0f} %**.",
        ),
    ),
    E_cross_checks=checks,
    F_gaps=[
        "x500v2 [D] — 순정 1045 의 기하 근거가 저장소에 하나도 없다. 9450 평면형을 대리로 쓰고 ±30 % 를 붙였다.",
        "phantom4 [C] — 자체 측정 없음. phantom3 의 9450 을 그대로 쓴다(사진 폴더는 다른 기체다).",
        "mini5pro [C] — 사진 속 기체 동일성 미확정. 밴드 0.176~0.239 (±14 %).",
        "두께: 10기종 중 **두 기종만** 근거가 있다(mini2 [A] 절대 mm · typhoonh480 [A-] t/c). "
        "나머지 8기종은 빈칸이다 — 사진으로는 원리적으로 못 잰다.",
        "matrice4e 순정 확정(1157F)은 [DERIVED] 3근거(이륙중량 1219 g·별매 여부·49분 호버)이지 "
        "DJI 문서의 «동봉품» 문장이 아니다.",
        "다리(arc→cal) 1.031 은 실측 둘(1.020·1.045)의 가운데다. 프롭마다 스윕·두께가 달라 "
        "±1.2 % 는 남는다.",
    ],
)

with open(os.path.join(OUT, "prop_law_by_airframe_0816.json"), "w", encoding="utf-8") as f:
    json.dump(led, f, ensure_ascii=False, indent=1)

# 사람이 읽을 요약 + drones.py 에 붙일 리터럴
print(f"[다리 감사] 기하 되돌리기 mini2 {mini2_geom_bridge:.4f} / 실측 {m2_bridge_deployed:.4f}"
      f"  ·  typhoon {yun_geom_bridge:.4f} / 실측 {yun_bridge:.4f}  ⇒ 채택 {BRIDGE}")
print(f"{'기체':<13}{'프롭':<22}{'등':<4}{'c_max mm':>18}{'날면적 mm²':>22}{'실루엣 mm²':>22}")
for r in rows:
    print(f"{r['aircraft']:<13}{r['prop'][:20]:<22}{r['grade']:<4}"
          f"{r['c_max_mm_old']:7.1f}→{r['c_max_mm_new']:6.1f}({r['c_max_pct']:+5.1f}%)"
          f"{r['blade_area_mm2_old']:8.0f}→{r['blade_area_mm2_new']:7.0f}({r['blade_area_pct']:+6.1f}%)"
          f"{r['silhouette_mm2_old']:8.0f}→{r['silhouette_mm2_new']:7.0f}({r['silhouette_pct']:+6.1f}%)")
print(led["D_change_table"]["spread_ko"]["headline_ko"])

lit = []
for key, law in LAW.items():
    lit.append(f'    "{key}": dict(\n'
               f'        model={law["prop"]!r},\n'
               f'        cmax_over_r={law["c_max_over_R"]!r}, grade={law["grade"]!r},\n'
               f'        chord_rr={law["chord_rr"]!r},\n'
               f'        chord_frac={law["chord_frac"]!r},\n'
               f'        t_mm={law["t_mm"]!r}, tc_max={law["tc_max"]!r},\n'
               f'        source={law["source"]!r}),')
with open(os.path.join(OUT, "_prop_law_literals_0816.py"), "w", encoding="utf-8") as f:
    f.write("\n".join(lit))

print(f"\n원장: outputs/prop_law_by_airframe_0816.json   ({time.time() - T0:.1f} s)")
