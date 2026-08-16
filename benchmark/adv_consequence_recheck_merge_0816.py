# -*- coding: utf-8 -*-
"""
adv_consequence_recheck_merge_0816.py — 조각을 원장에 합치고 «판정» 절을 쓴다 (2026-08-16)
===========================================================================================

조각(J8·J8b·J9·J10)은 동시 실행 중 서로 덮어쓰지 않으려고 따로 떨어뜨렸다.
이 스크립트가 그것들을 `outputs/mesh_adv_refute_consequence_0816.json` 에 합치고,
이 라운드의 **판정 절 K** 를 쓴다. 계산은 하지 않는다 — 값의 출처는 전부 조각 파일이다.
"""
from __future__ import annotations

import json
import os
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "outputs", "mesh_adv_refute_consequence_0816.json")
FRAGS = {
    "J8_engine_shape_ruler": "_J8_engine_shape_ruler_0816.json",
    "J8b_ruler_vs_elevation": "_J8b_ruler_split_0816.json",
    "J9_sixclass_separation": "_J9_sixclass_0816.json",
    "J10_azimuth_and_estimator_ruler": "_J10_azimuth_r50_0816.json",
}


def main():
    led = json.load(open(OUT, encoding="utf-8"))
    for key, fn in FRAGS.items():
        p = os.path.join(ROOT, "outputs", fn)
        led[key] = json.load(open(p, encoding="utf-8"))

    J1 = led["J1_planform_three_laws"]["common_mode"]
    J5 = led["J5_r50"]
    J6 = led["J6_engine_margin"]
    J7 = led["J7_sigma_anchor"]
    J8 = led["J8_engine_shape_ruler"]
    J9 = led["J9_sixclass_separation"]
    J10 = led["J10_azimuth_and_estimator_ruler"]

    led["K_verdicts_round2"] = {
        "question_ko": "감사의 형상 지적이 맞다 치고, 그 오차가 «우리가 실제로 내리는 판정» "
                       "을 바꾸는가 — 2 라운드(독립 재측정 + 앞 라운드 자체를 공격)",
        "what_changed_since_round1_ko":
            "앞 라운드(13:19)는 판 후보를 `dji_mini2` 하나로 봤다. 그 뒤 13:43~13:44 에 저장소에 "
            "**세 번째 판 `per_airframe`** 이 올라왔다 — `drones.PROP_LAW_0816` 에 기체별 곡선 8 개와 "
            "기체별 c_max/R 이 들어 있다. 즉 **지금 유력한 후보에는 아무도 값을 매기지 않은 상태**였다. "
            "아래는 두 판을 다 매긴 값이다.",

        "0_reproduction_check": {
            "verdict_ko": "앞 라운드의 수치는 **독립 구현으로 재현됐다** — 옮겨 적은 것이 아니다.",
            "reproduced": [
                "평면형 공통모드: fleet_span 1.703 dB · classify_trio_span 0.503 dB (dji_mini2) — 소수 3자리 일치",
                "슬로타임 Δ빗살: mini5pro el−30 +1.088 dB · matrice4e el+0 +0.544 dB · s1000plus el−30 +0.075 dB — 일치",
                "전력 코사인: mini5pro el−30 0.8393 · matrice4e el−30 0.9241 — 일치",
                "PathSolver 면적 무관성: rt_no_rcs_verify.json A_plate — 판 0.2→4 m 에서 σ 52.04 dB 스윙에 "
                "반환 진폭비 −7.913447→−7.913448 dB (1.9e-6 dB)",
            ],
            "method_ko": "같은 저장소 원시함수(`drones.build_propeller` · `rcs_po.mesh_to_points/po_field_dir`)를 "
                         "쓰되 배치 PO·통계·판정은 새로 짰다. 배치판↔출하 커널 상대오차 0.0 (`verify_batch`).",
        },

        "a_engine_comparison": {
            "verdict_ko": "⭐ **판정은 안 바뀐다. 그리고 앞 라운드가 «흔들린다» 고 적은 근거 하나는 자[尺] 탓이었다.**",
            "level_axis": {
                "ruler_definition_ko": "⚠ **내 J6 절을 내가 정정한다.** 원장의 `level_db` 는 "
                                       "`elevation_sweep_md.py:581` 에서 `20·log10(mean|E|)` — 즉 "
                                       "**총 레벨**이지 AC(변조) 레벨이 아니다(report07 의 `levels_db` 도 "
                                       "`report07_three_engine_maps.py:193` 에서 같은 정의). 그러니 엔진 "
                                       "간격과 견줄 값은 AC 이동이 아니라 **총 σ 이동**이다.",
                "our_total_level_move_db": {
                    k: {law: {el: v[law][el]["d_sigma_total_db"] for el in v[law]}
                        for law in v}
                    for k, v in led["J2_slowtime_three_laws"]["delta"].items()},
                "our_total_level_move_max_db": 0.148,
                "our_max_ac_move_db": J6["our_max_ac_move_db"],
                "ledger_engine_gap_db_range": [J6["min_engine_gap_db"],
                                               max(v for g in J6["ledger_engine_gap_db"].values()
                                                   for v in g.values())],
                "worst_ratio_on_ledger_ruler_pct": 1.96,
                "worst_ratio_if_ac_used_pct": J6["move_over_min_gap_pct"],
                "reading_ko": "원장 자신의 잣대(총 레벨)로 재면 판 교체가 우리 수치를 움직이는 최대치는 "
                              "**0.148 dB** 이고 엔진 간격은 7.54~79.23 dB — 가장 얇은 칸의 **2.0 %** 다. "
                              "AC(변조) 채널로 바꿔 재면 최대 2.18 dB(mini5pro·per_airframe·el 0)라 그 얇은 "
                              "칸의 29 % 가 되지만, **저장소는 AC 채널 엔진 간격을 발표한 적이 없다** — "
                              "발표된 변조 축 잣대는 무늬 코사인이고 그것은 아래에서 사과-대-사과로 쟀다.",
            },
            "shape_axis": {
                "published_ruler": "크기 코사인, |f| ≤ f_tip (report07_three_engines.json :: verdict.cosine_in_ftip)",
                "published_values": J8["published_engine_cosine_in_ftip"],
                "law_swap_same_ruler_same_arm": {
                    k: v["per_law"] for k, v in J8["law_swap_cosine"].items()},
                "refutation_ko": "⭐ 앞 라운드는 «판 교체가 우리 스펙트럼을 코사인 0.839~0.990 흔드는데 이는 "
                                 "발표된 엔진 일치도와 같은 크기» 라고 적었다. 그 0.839 는 **전력 스펙트럼** "
                                 "코사인이고 발표값은 **크기 스펙트럼** 코사인이며, 앙각도 el −30 대 el −15 로 "
                                 "다르다. 같은 신호쌍에 발표 자를 대면 0.8393 → 0.9589 로 올라간다"
                                 "(J8b). 발표 팔(matrice4e·el −15)에서는 판 교체가 0.9917(dji) · 0.9956"
                                 "(per_airframe) 로, **우리 두 커널끼리의 일치도 0.9550 보다도 1 에 가깝다.**",
                "surviving_caveat_ko": "⚠ 보편적이지는 않다 — mini5pro·el −30·per_airframe 은 크기 코사인 "
                                       "0.8924 로 SBR↔PO 의 0.9550 보다 낮다. 즉 «판 교체 < 엔진 불일치» 는 "
                                       "**발표된 팔에서 참**이고 모든 칸에서 참은 아니다.",
            },
            "structural_leg_ko": "«PathSolver 는 산란적분이 없어 σ 를 못 낸다» 는 메쉬와 무관한 구조 판정이라 "
                                 "형상 교체와 독립이다(위 A_plate 실측이 그 근거).",
        },

        "b_classification": {
            "verdict_ko": "⭐ **살아남는다. 앞 라운드의 «클래스 간격의 92 % 를 먹는다» 는 잘못된 잣대였다.**",
            "why_the_old_test_was_wrong_ko":
                "앞 라운드는 «한 기체가 판 교체로 얼마나 움직이나(z)» 를 «클래스 간 거리» 와 나란히 놨다. "
                "그런데 판을 갈면 **세 기체가 다 같이** 움직인다. 분류가 사는지는 «간격 자체가 좁아지나» 가 "
                "정하지, 한 점이 얼마나 움직이나가 정하지 않는다. 게다가 그들이 든 최악값(h8, 11.5σ)은 "
                "**클래스를 전혀 못 가르는 특징**이다 — 같은 표의 h8 클래스 간 거리가 0.016σ 다.",
            "between_class_six_published_classes": {
                "classes": J9["classes"],
                "el-30": J9["between_class"]["-30"],
                "el+0": J9["between_class"]["+0"],
            },
            "headline_numbers_ko":
                "발표된 6 클래스로 다시 지어 잰 **최소 클래스쌍 거리**(전 27 특징, el −30): "
                "legacy 6.13 → dji_mini2 6.40(+4.4 %) → per_airframe 5.90(−3.8 %). "
                "형상만 쓰는 팔(geometry_only 23 특징): 4.07 → 3.90(−4.3 %) → 3.63(−11.0 %), "
                "중앙값은 11.41 → 9.81 → 8.29(−27 %).",
            "comb_matcher": {
                "flips": led["J4_comb_classifier"]["flips_vs_legacy"],
                "accuracy_by_law": {k: v["accuracy"]
                                    for k, v in led["J4_comb_classifier"]["per_law"].items()},
                "why_ko": "판별식이 f_flash(날개수 × 회전수)라 날 형상과 독립이다.",
            },
            "concession_ko": "⚠ **공통 오차가 아니다.** `per_airframe` 은 기체마다 다른 곡선을 쓰므로 함대 "
                             "면적 산포가 2.285 dB(dji_mini2 는 1.703), 분류 3기체 산포가 1.125 dB"
                             "(dji_mini2 0.503)로 커진다. 그래서 형상 유래 특징의 클래스 간격이 "
                             "11 %(최소쌍)~27 %(중앙값) 줄어든다. 그래도 클래스는 3.6~8σ 떨어져 있다.",
            "undecided_ko": "발표된 geometry_only 정확도 79.5 % 가 실제로 내려가는지는 **못 정한다** — "
                            "12,096 행 데이터셋을 새 판으로 다시 지어야 한다. 최근접 클래스평균 대리시험은 "
                            "**무효**였다(legacy 자신이 6 중 3~5 만 맞힌다 — 순수 PO·단일 방위 팔이 "
                            "발표 데이터셋의 클래스 평균을 애초에 재현하지 못한다).",
        },

        "c_absolute_range": {
            "verdict_ko": "한 자릿수 % 다. 방위를 바꿔도 부호가 안 바뀌므로 **인공물이 아니라 실제 이동**이고, "
                          "그래도 어떤 발표 주장도 안 뒤집는다.",
            "chain_ko": "detection_curves.py 는 c_anchor = σ_ref/⟨σ⟩ 로 총 σ 를 문헌값에 고정한다 ⇒ "
                        "**총 σ 의 공통 이동은 정확히 지워진다**(합성열 실증: 장을 +1/+3 dB 키워도 앵커 "
                        "후 σ 평균과 AC 에너지가 1e-6 dB 안에서 동일). 남는 것은 빗살/⟨σ⟩ 의 비뿐이다.",
            "d_R50_pct_by_law": {k: {law: {el: v[law][el]["d_R50_pct"] for el in v[law]}
                                     for law in v} for k, v in J5.items() if k != "anchor_cancellation"},
            "azimuth_robustness": J10["azimuth_sweep"],
            "estimator_ruler": J10["estimator_ruler"],
            "reading_ko": "발표 R50 팔(matrice4e·el −30)은 +3.7 %(dji) · +2.2 %(per_airframe)이고 방위 "
                          "0/23/45/90° 에서 +2.8~+3.9 % / +1.4~+2.5 % 로 부호가 유지된다. 자를 대면 그 "
                          "추정기 자신의 흔들림은 부트스트랩 95 % 구간 ±0.8~1.5 %, 씨앗을 바꾸면 −0.9~+2.7 % 다. "
                          "즉 **추정기 잡음보다 크지만 엔진 간 R50 격차(+13.9 %)보다는 작다.** mini5pro 는 "
                          "+3.3~+8.0 % 로 더 크다.",
            "no_claim_flips_ko": "빗살 > 단순대역, ours el−30 > el 0·el −60, Sionna R50 > ours — 셋 다 "
                                 "판 교체로 안 뒤집힌다(가장 큰 이동 +8.0 % < 격차 13.9 %).",
        },

        "d_anchor_blindness": {
            "verdict_ko": "⭐ **새 법칙은 σ 앵커를 좋게도 나쁘게도 못 만든다 — 앵커가 프롭을 못 본다.** "
                          "따라서 «고치면 좋아진다» 도 «나빠진다» 도 이 앵커로는 **검증 불가**다.",
            "total_sigma_move_at_el0_db": {
                k: {law: v["delta"][law]["+0"]["d_sigma_lin_db"] for law in v["delta"]}
                for k, v in J7["per_airframe"].items()},
            "prop_share_at_el0_db": {k: v["per_law"]["legacy"]["+0"]["prop_minus_total_db"]
                                     for k, v in J7["per_airframe"].items()},
            "anchor_state_now": J7["anchor_state_now"],
            "reading_ko": "문헌 앵커가 있는 유일한 기체(Phantom 3)에서 방위평균 총 σ 는 판을 갈아도 "
                          "+0.0012 dB(per_airframe) 움직인다 — 프롭이 총 σ 보다 24.9 dB 아래이기 때문이다. "
                          "지금 앵커 오차는 우리 대역 평균 −5.16 dB(3.5 GHz 에서 −7.35 dB)이고 함대 "
                          "검증은 산포 16.27 dB 로 NOT_VALIDATED 다. 0.001 dB 대 5~7 dB — 잡음도 안 된다. "
                          "게다가 생산 앵커는 slope_only 라 레벨을 아예 안 움직인다.",
        },

        "e_audit_price_tag_is_for_a_different_prop": {
            "verdict_ko": "⭐ 확인 — 감사 C5 의 «+0.2~+1.3 dB» 는 **지금 얹혀 있는 판이 아닌 프롭**의 값이다. "
                          "부호가 반대다.",
            "audit_arm": "감사 C5/§4-2 는 DJI 분포로 다시 지으면서 c_max/R 은 0.25 로 뒀다 → 날 표면적 "
                         "128.33 → 153.34 cm² (**+19.5 %**).",
            "staged_arm_measured_by_me": {
                "matrice4e": {"d_planform_db": led["J1_planform_three_laws"]["per_airframe"]
                              ["matrice4e"]["d_planform_db"],
                              "d_mesh_area_db": led["J1_planform_three_laws"]["per_airframe"]
                              ["matrice4e"]["d_mesh_db"]},
                "fleet_common_mode": J1,
            },
            "reading_ko": "실제 판은 c_max/R 도 같이 바꾸므로 matrice4e 날 면적이 **−0.503 dB(dji) · "
                          "−0.375 dB(per_airframe)** 로 **줄어든다**. 감사의 dB 가격표를 교체 근거로 "
                          "인용하면 안 된다.",
        },

        "f_limits_of_this_round_ko": [
            "순수 PO(가림 없음)·모노스태틱이다. 생산 마이크로도플러 팔은 SBR 바이스태틱이다 — "
            "감사 스스로 바이스태틱에서 형상 민감도가 커진다고 적었고(β=120° 에서 ±2.5 dB), "
            "나는 그 축을 **다시 재지 않았다**(앞 라운드 H 절이 β 0/81/120° 에서 R50 +3.6/+2.0/+2.4 % 를 잰다).",
            "J2·J3·J9 는 단일 방위(az 0)·단일 창이다. R50 만 방위 4 개로 흔들어 봤다(J10).",
            "피치 법칙(PITCH_K)은 세 판 모두 legacy 다 — 감사 I7 이 스스로 «어림이 과했을 가능성» 이라 "
            "적었고 코드도 기본으로 안 켠다. 즉 **피치 교체의 대가는 이 라운드에서 안 쟀다.**",
            "분류 축의 최종 판정(정확도 79.5 % 가 움직이나)은 데이터셋 재생성 없이는 못 낸다.",
        ],
    }

    led["_meta_K"] = dict(
        generated=time.strftime("%Y-%m-%d %H:%M:%S"),
        generator="benchmark/adv_consequence_recheck_merge_0816.py",
        scripts=["benchmark/adv_consequence_recheck_0816.py",
                 "benchmark/adv_consequence_recheck_J8_0816.py",
                 "benchmark/adv_consequence_recheck_J8b_0816.py",
                 "benchmark/adv_consequence_recheck_J9_0816.py",
                 "benchmark/adv_consequence_recheck_J10_0816.py"],
        gpu="사용 안 함(CPU 전용)", code_changes="기존 소스 무변경(읽기 전용 측정기만 추가)",
        concurrency_check_ko="⚠ 이 라운드가 도는 동안 다른 세션이 `src/drones.py` 를 14:02 에 "
                             "고쳤다(내 J1 은 13:53, J9·J10 은 14:04~14:07). 세대가 섞였는지 "
                             "확인하려고 **J1 을 끝나고 다시 돌려** 전 10기체·3판의 면적 dB 를 "
                             "대조했다 — 차이 0 건. 즉 이 파일의 수치는 한 세대다.")
    json.dump(led, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("merged →", OUT, "keys:", len(led))


if __name__ == "__main__":
    main()
