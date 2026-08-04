# -*- coding: utf-8 -*-
"""
build_report00_po_case.py — 리포트 00 「왜 PO 인가」의 근거 JSON 을 만든다
=================================================================================================
산출: ``outputs/report00_po_case.json``

■ 무엇을 하는 파일인가
  리포트 00 은 **가르치는 편**이다(사용자 요청: *"시오나로 할 수 있고 없고가 명확히 구분이 안돼…
  최대한 쉽고 자세하게"*). 다른 편(01~06)이 압축돼 있는 것과 다르게 유도를 건너뛰지 않는다.
  그러려면 본문에 숫자가 많이 들어가는데, 이 저장소 규약은 **숫자를 손으로 치지 않는 것**이다
  (`src/report_style.py` §1 `num()`). 그래서 이 스크립트가 기존 산출물에서 값을 **읽어서**
  한 파일로 모은다. 리포트 빌더는 `num(None, "outputs/report00_po_case.json:<키>")` 로만 쓴다.

■ 이 파일이 지키는 규칙
  1. **모든 스칼라 옆에 `<이름>_src` 가 붙는다.** 값이 어디서 왔는지가 값과 같은 자리에 있다.
     · `outputs/x.json:키`  → 다른 산출물에서 읽었다(이 스크립트가 실제로 열어서 대조한다).
     · `code: src/x.py:N`   → 소스에 박힌 상수다.
     · `computed: 식`       → 이 스크립트가 두 값으로 계산했다.
     · `doc: docs/X.md §N`  → 문서에서 옮긴 문장이다(숫자가 아니라 문장일 때만).
  2. **읽기 전용**이다. 다른 산출물을 건드리지 않는다.
  3. 값을 못 읽으면 `report_style.ContractError` 로 **즉시 멈춘다** — 조용히 None 을 흘리지 않는다.

■ 공정성 규약 (이 편의 핵심)
  Sionna 를 부당하게 깎으면 그 자체가 결함이다. 이 파일의 §0 이 그 경계를 원문 인용으로 고정한다:
  Sionna 는 Fresnel 반사를 **정확히 계산하고**, **1차 UTD 쐐기회절이 구현돼 있으며**(설치본 기본값이
  off 일 뿐 — `docs/RETRACTION_LOG.md` R6), 환경·클러터에서는 **맞는 도구**다.
  틀린 것은 "Sionna 가 부실하다" 가 아니라 "전파용 도구에 표적 산란을 시켰다" 이다.

실행:
  cd /home/yunjung/workspace/sionna2
  PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/build_report00_po_case.py
"""
from __future__ import annotations

import datetime
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from report_style import fetch                                  # noqa: E402

OUT = os.path.join(ROOT, "outputs", "report00_po_case.json")

#: 출처 원장 — (이 파일의 필드, 읽어온 곳). 마지막에 `_provenance` 로 실린다.
LEDGER: list[dict] = []


def put(d: dict, name: str, source: str):
    """`d[name]` 에 다른 산출물의 값을 넣고 `d[name+'_src']` 에 출처를 적는다."""
    val = fetch(source)
    d[name] = val
    d[name + "_src"] = source
    LEDGER.append({"field": name, "src": source})
    return val


def putc(d: dict, name: str, value, how: str):
    """이 스크립트가 계산한 값."""
    d[name] = value
    d[name + "_src"] = f"computed: {how}"
    LEDGER.append({"field": name, "src": f"computed: {how}"})
    return value


def putl(d: dict, name: str, value, where: str):
    """소스 코드에 박힌 상수 / 설정."""
    d[name] = value
    d[name + "_src"] = f"code: {where}"
    LEDGER.append({"field": name, "src": f"code: {where}"})
    return value


def putd(d: dict, name: str, value, where: str):
    """문서에서 옮긴 **문장**(숫자가 아니다)."""
    d[name] = value
    d[name + "_src"] = f"doc: {where}"
    return value


RB = "outputs/runtime_benchmark.json"
LA = "outputs/lowfreq_anchor.json"
LG = "outputs/lowfreq_grid.json"
LK = "outputs/lowfreq_attack.json"
KR = "outputs/sbr_kr_sweep.json"
RA = "outputs/rcs_anchor.json"
DF = "outputs/sbr_defect_fixes.json"
RT = "outputs/rt_no_rcs_verify.json"
PC = "outputs/p3_control.json"
EV = "outputs/evasion_catalogue.json"
IV = "outputs/injection_verdict.json"
IS = "outputs/injection_standards.json"
SB = "outputs/sionnart_boundary.json"
W2 = "outputs/report2_waveform_rcs.json"


# ================================================================================================
#  §0  공정한 경계 — Sionna 가 하는 일 / 하지 않는 일 / 우리가 얹은 것
# ================================================================================================
def section0() -> dict:
    s: dict = {
        "_title": "Sionna 는 무엇을 계산하고 무엇을 계산하지 않는가 — 공정한 경계",
        "_why_this_section_first": (
            "이 편은 'Sionna 로 되는 것과 안 되는 것' 을 가르는 편이다. 그 경계를 우리 말이 아니라 "
            "**엔진 자신의 기술보고서 문장**으로 긋는다. 그래야 다음 절의 'PO 를 얹었다' 가 "
            "비난이 아니라 위치 설명이 된다."),
    }
    put(s, "sionna_rt_citation", f"{SB}:SOURCE_IDENTITY.primary.cite_string")
    put(s, "sionna_rt_pages", f"{SB}:SOURCE_IDENTITY.primary.pages")
    put(s, "sionna_rt_self_declared_purpose",
        f"{SB}:SOURCE_IDENTITY.primary.self_declared_purpose_p1")

    #  ── 엔진이 정확히 하는 것 ────────────────────────────────────────────────────────────
    s["what_the_engine_does_exactly"] = [
        {"mechanism": "정반사 필드",
         "detail": "교차점에서 (⊥,∥) 기저의 2×2 대각 Fresnel 행렬을 필드에 곱한다. 식 (127)(128) "
                   "계수, (129) 적용.",
         "why_it_is_correct": "평면파가 반평면 경계에 부딪힐 때의 반사계수는 Fresnel 식 그 자체다. "
                              "Sionna 는 이 값을 근사하지 않고 계산한다.",
         "src": f"{SB}:SECTION_1_BOUNDARY_TABLE.rows[0]"},
        {"mechanism": "굴절·투과",
         "detail": "Snell (121)(122), 투과계수 (127)(128), 두께가 주어지면 단일층 슬래브 (131)~(133) "
                   "로 에탈론 리플까지 낸다.",
         "why_it_is_correct": "벽처럼 측방으로 넓은 매질에 대해서는 이것이 옳은 모형이다.",
         "src": f"{SB}:SECTION_1_BOUNDARY_TABLE.rows[1]"},
        {"mechanism": "1차 UTD 쐐기회절",
         "detail": "Kouyoumjian–Pathak 을 Luebbers 가 유한도전율로 확장한 판이 기술보고서 p.47 에 "
                   "**구현돼 있다**. 우리 설치본 2.0.1 이 diffraction=False / edge_diffraction=False "
                   "로 기본값이 꺼져 있을 뿐이다.",
         "why_it_is_correct": "회절은 실제 물리이고 UTD 는 그 표준 고주파 처리다.",
         "src": "doc: docs/RETRACTION_LOG.md R6"},
        {"mechanism": "확산산란",
         "detail": "반사 에너지를 S²:R² 로 쪼개고 정규화된 산란패턴으로 반구에 재분배한다(식 164~174).",
         "why_it_is_correct": "거친 벽면의 전력 재분배 모형으로 설계된 그대로 작동한다.",
         "src": f"{SB}:SECTION_1_BOUNDARY_TABLE.rows[2]"},
    ]

    #  ── 우리가 이미 철회한 오류 ─────────────────────────────────────────────────────────
    s["errors_we_already_retracted"] = [
        {"we_said": "스톡 Sionna 에 회절이 없다",
         "truth": "1차 UTD 쐐기회절이 기술보고서 p.47 에 구현돼 있다. 설치본 기본값이 off 일 뿐이다.",
         "also_forbidden": "반대 방향 오류도 금지 — 'Sionna 의 UTD 가 우리 PTD 결손을 메운다' 도 거짓이다. "
                           "Sionna 의 D 는 전파경로의 필드 전달용이지 표적 산란단면 산출이 아니다.",
         "src": "doc: docs/RETRACTION_LOG.md R6"},
        {"we_said": "레이트레이싱은 RCS 를 못 낸다",
         "truth": "거짓이다. SBR(GO+PO)은 상용 EM 솔버의 표준 고주파 기법이고 우리가 쓰는 것이 바로 그것이다.",
         "src": f"{SB}:SECTION_3_THE_GAP_IN_THE_DOCUMENTS_OWN_TERMS.our_layer_stated_precisely."
                "what_we_do_not_claim[0]"},
    ]

    #  ── 문제 정의가 다르다 ─────────────────────────────────────────────────────────────
    put(s, "the_four_structural_facts",
        f"{SB}:SECTION_3_THE_GAP_IN_THE_DOCUMENTS_OWN_TERMS.the_four_structural_facts")
    put(s, "what_a_sensing_application_needs",
        f"{SB}:SECTION_3_THE_GAP_IN_THE_DOCUMENTS_OWN_TERMS."
        f"what_a_sensing_application_needs_that_this_does_not_provide.quantity")
    put(s, "why_the_engine_cannot_supply_it",
        f"{SB}:SECTION_3_THE_GAP_IN_THE_DOCUMENTS_OWN_TERMS."
        f"what_a_sensing_application_needs_that_this_does_not_provide."
        f"why_the_engine_cannot_supply_it_by_construction")
    put(s, "forbidden_sentence",
        f"{SB}:SECTION_3_THE_GAP_IN_THE_DOCUMENTS_OWN_TERMS."
        f"why_this_is_a_scope_decision_not_a_defect.the_forbidden_sentence")
    put(s, "permitted_sentence",
        f"{SB}:SECTION_3_THE_GAP_IN_THE_DOCUMENTS_OWN_TERMS."
        f"why_this_is_a_scope_decision_not_a_defect.the_permitted_sentence")
    put(s, "extensibility_counterweight",
        f"{SB}:SECTION_3_THE_GAP_IN_THE_DOCUMENTS_OWN_TERMS."
        f"why_this_is_a_scope_decision_not_a_defect.the_extensibility_counterweight")
    put(s, "our_layer_one_sentence",
        f"{SB}:SECTION_3_THE_GAP_IN_THE_DOCUMENTS_OWN_TERMS.our_layer_stated_precisely.one_sentence")
    put(s, "what_we_do_not_claim",
        f"{SB}:SECTION_3_THE_GAP_IN_THE_DOCUMENTS_OWN_TERMS.our_layer_stated_precisely."
        f"what_we_do_not_claim")

    #  ── 직접 실험: 엔진의 표적 경로에는 σ 정보가 없다 ────────────────────────────────────
    e: dict = {"_what": "표적 경로가 σ 를 실어 나르는지 직접 흔들어 본 실험(benchmark/verify_rt_no_rcs.py)."}
    put(e, "plate_side_min_m", f"{RT}:A_plate[0].side")
    put(e, "plate_side_max_m", f"{RT}:A_plate[4].side")
    sig_lo = put(e, "plate_sigma_min_dbsm", f"{RT}:A_plate[0].sigma_dbsm")
    sig_hi = put(e, "plate_sigma_max_dbsm", f"{RT}:A_plate[4].sigma_dbsm")
    putc(e, "plate_sigma_span_db", sig_hi - sig_lo,
         "A_plate[4].sigma_dbsm − A_plate[0].sigma_dbsm")
    r_lo = put(e, "plate_rt_ratio_at_min_db", f"{RT}:A_plate[0].ratio_db")
    r_hi = put(e, "plate_rt_ratio_at_max_db", f"{RT}:A_plate[4].ratio_db")
    putc(e, "plate_rt_ratio_spread_db", abs(r_hi - r_lo),
         "|A_plate[4].ratio_db − A_plate[0].ratio_db|")
    put(e, "plate_image_source_theory_db", f"{RT}:image_source_db")
    put(e, "sphere_S_lo", f"{RT}:B_sphere_S[0].S")
    put(e, "sphere_S_hi", f"{RT}:B_sphere_S[3].S")
    sl = put(e, "sphere_ratio_at_S_lo_db", f"{RT}:B_sphere_S[0].ratio_db")
    sh = put(e, "sphere_ratio_at_S_hi_db", f"{RT}:B_sphere_S[3].ratio_db")
    putc(e, "sphere_ratio_moved_by_S_db", sh - sl,
         "B_sphere_S[3].ratio_db − B_sphere_S[0].ratio_db")
    put(e, "pec_sphere_paths_r03_spp1M", f"{RT}:C_pec_sphere[0].n_paths")
    put(e, "pec_sphere_paths_r30_spp16M", f"{RT}:C_pec_sphere[5].n_paths")
    e["reading"] = ("평판 넓이를 바꿔 σ 를 52 dB 흔들어도 RT 진폭비는 소수 셋째 자리까지 그대로다 — "
                    "그 경로가 나르는 것은 이미지-소스 거울장이지 표적의 단면적이 아니다. 확산 경로는 "
                    "표적이 아니라 재질 파라미터 S 를 잰다. 그리고 물리적으로 옳은 설정(PEC 금속, S=0)에서는 "
                    "표적 경로가 아예 0 개다.")
    e["fairness_note"] = ("이것은 엔진의 버그가 아니다. 무한평면 거울장은 **전파 문제의 정답**이고, "
                          "표적 단면적은 그 문제의 출력 목록에 애초에 없다.")
    s["engine_carries_no_sigma_experiment"] = e

    #  ── 비유와 그 비유가 깨지는 곳 ───────────────────────────────────────────────────────
    s["analogies_and_where_they_break"] = [
        {"analogy": "Sionna 의 표면 처리는 **거울 한 장**이다 — 들어온 빛을 각도 맞춰 되돌린다.",
         "what_it_teaches": "그래서 반사의 세기(Fresnel)는 맞고, 방향도 맞다.",
         "where_it_breaks": "거울은 '크기' 가 없다. 우리 실험에서 평판 변을 20배 키워 σ 를 52 dB 바꿔도 "
                            "진폭이 안 움직인 것이 그 뜻이다. 진짜 물체는 크기·모양이 되돌리는 양을 정한다.",
         "anchor": "engine_carries_no_sigma_experiment.plate_sigma_span_db"},
        {"analogy": "PO 표면적분은 **조명된 면에 붙은 수많은 작은 안테나의 합**이다.",
         "what_it_teaches": "각 지점이 위상을 갖고 더해지므로, 모양이 바뀌면 보강·상쇄 패턴이 바뀐다 — "
                            "여기서 비로소 σ 가 창발한다.",
         "where_it_breaks": "그 '작은 안테나' 의 세기를 우리는 **국소 평면 반사**로 정한다. 특징 폭이 "
                            "파장보다 작아지면 그 가정이 깨지고, 실제 전류는 모서리 근방에서 다르게 흐른다. "
                            "그 깨짐의 크기가 §4 의 무릎(0.729λ)이다.",
         "anchor": "s4_limits.po_validity_knee_a_over_lambda"},
        {"analogy": "SBR 은 **손전등으로 물체를 비추고, 빛이 닿은 자리만 세는 것**이다.",
         "what_it_teaches": "가림(self-shadowing)이 공짜로 처리된다 — 안 닿은 면은 애초에 세지 않는다.",
         "where_it_breaks": "손전등 비유는 빛이 '모서리에서 휘는 것' 과 '매끄러운 몸통을 감아 도는 것'을 "
                            "설명하지 못한다. 전자가 PTD 항이고 후자(크리핑파)는 우리 커널에도, "
                            "Sionna 에도 없다.",
         "anchor": "s2_our_kernel.what_our_kernel_does_not_do"},
    ]
    return s


# ================================================================================================
#  §1  대안 지도 — 각각의 비용과 정확도
# ================================================================================================
def section1() -> dict:
    s: dict = {
        "_title": "표적 σ 를 얻는 다섯 갈래 — 비용과 정확도",
        "_axis": "행 = 방법, 열 = (무엇을 푸는가 · 비용 · 정확도 근거 · 이 프로젝트에서의 위치).",
    }

    # ── 우리 커널 런타임 (자세당) ────────────────────────────────────────────────────────
    o: dict = {"_what": "생산 커널 rcs_sbr_batch 의 **자세 1개당** 벽시계 시간. "
                        "자세 = (방위, 고도) 한 점 × 반송파 1개 → σ 한 값."}
    put(o, "ours_per_pose_ms_min", f"{RB}:answer.two_passes.headline_pass.min")
    put(o, "ours_per_pose_ms_median", f"{RB}:answer.two_passes.headline_pass.median")
    put(o, "ours_per_pose_ms_max", f"{RB}:answer.two_passes.headline_pass.max")
    put(o, "ours_least_contended_median_ms", f"{RB}:answer.least_contended_median_ms")
    put(o, "facets_smallest_airframe", f"{RB}:production_per_pose.rows[0].facets")
    put(o, "rays_per_pose_lte", f"{RB}:production_per_pose.rows[0].rays_per_pose")
    put(o, "rays_per_pose_wifi", f"{RB}:production_per_pose.rows[2].rays_per_pose")
    put(o, "passes_per_pose", f"{RB}:production_per_pose.rows[0].passes_per_pose")
    put(o, "hardware", f"{RB}:ladder[0].hardware")
    s["ours_runtime"] = o

    # ── 스톡 Sionna, 같은 카드 ──────────────────────────────────────────────────────────
    k: dict = {"_what": "스톡 sionna.rt.PathSolver 를 **우리 카드·우리 챔버 씬**에서 잰 대조군. "
                        "하드웨어 변수를 없앤다. ⚠ 재는 양이 다르다 — 전파 경로 대 표적 RCS."}
    put(k, "stock_sionna_ms_min", f"{RB}:answer.same_card_control.stock_sionna_pathsolver_ms.min")
    put(k, "stock_sionna_ms_median",
        f"{RB}:answer.same_card_control.stock_sionna_pathsolver_ms.median")
    put(k, "stock_sionna_ms_max", f"{RB}:answer.same_card_control.stock_sionna_pathsolver_ms.max")
    put(k, "stock_sionna_n_configs",
        f"{RB}:answer.same_card_control.stock_sionna_pathsolver_ms.n_configs")
    put(k, "ratio_ours_median_over_stock_median",
        f"{RB}:answer.same_card_control.ratio_ours_median_over_stock_median")
    put(k, "reading", f"{RB}:answer.same_card_control.reading")
    put(k, "caveat", f"{RB}:answer.same_card_control.caveat")
    s["stock_sionna_same_card"] = k

    # ── 공개 런타임 사다리 ─────────────────────────────────────────────────────────────
    lad: list = []
    for i, (what, key) in enumerate([
            ("스톡 Sionna RT solve — Luo arXiv:2603.16126 p.5 (RTX A5000)",
             f"{RB}:published_baselines.rows[2].value_s"),
            ("스톡 Sionna RT solve — oneTwin arXiv:2601.03216 p.8 (RTX 4090)",
             f"{RB}:published_baselines.rows[1].value_s"),
            ("스톡 Sionna RT solve — DeepRT-E arXiv:2607.11743 Table I (RTX 4090)",
             f"{RB}:published_baselines.rows[0].value_s"),
            ("SagittaSBR — SBR+PO, A380 162k 삼각형, 각도위치당 (MI250X 32장)",
             f"{RB}:published_baselines.rows[5].value_s")]):
        row = {"what": what}
        put(row, "seconds", key)
        lad.append(row)
    zrt = {"what": "Ziganshin RT only — PEC 차량 1496 facet, **각도점당** (CPU 32코어)"}
    put(zrt, "ms", f"{RB}:published_baselines.rows[3].per_angular_point_ms.RT")
    lad.append(zrt)
    zfull = {"what": "Ziganshin 전체 회절 사다리(+V+EE+EV/VE), **각도점당** (CPU 32코어)"}
    put(zfull, "ms", f"{RB}:published_baselines.rows[3].per_angular_point_ms.plus_EV_VE")
    lad.append(zfull)
    zmlfmm = {"what": "MLFMM full-wave 기준해 — 같은 Ziganshin 연구"}
    put(zmlfmm, "quote", f"{RB}:published_baselines.rows[4].quote")
    zmlfmm["seconds"] = None
    zmlfmm["seconds_src"] = "미인쇄 — 원문은 'several hours' 라고만 적는다"
    lad.append(zmlfmm)
    s["published_runtime_ladder"] = lad
    put(s, "apples_to_apples_fix_ziganshin",
        f"{RB}:published_baselines.rows[3].correction")

    # ── 캐스케이드 비용 반론에 대한 답 ──────────────────────────────────────────────────
    c: dict = {"_the_objection": (
        "Ziganshin arXiv:2604.05991v2 pp.1–2, 게재된 반론: "
        "'the need to cascade PO after RT negates the computational advantages of RT'")}
    put(c, "our_rt_trace_pct", f"{RB}:answer.cost_structure.rt_trace_pct")
    put(c, "our_po_integral_pct", f"{RB}:answer.cost_structure.po_integral_pct")
    put(c, "our_host_side_pct", f"{RB}:answer.cost_structure.host_side_pct")
    put(c, "our_po_over_rt", f"{RB}:answer.cost_structure.po_over_rt")
    put(c, "sagitta_po_over_raylaunch_A100_fp32",
        f"{RB}:published_baselines.rows[6].po_over_raylaunch.A100_fp32")
    put(c, "sagitta_po_over_raylaunch_MI250X_fp32",
        f"{RB}:published_baselines.rows[6].po_over_raylaunch.MI250X_gcd_fp32")
    put(c, "ours_ns_per_ray_median", f"{RB}:answer.cost_per_ray.ours_ns_per_ray_median")
    put(c, "ours_po_ns_per_ray_median", f"{RB}:answer.cost_per_ray.ours_po_ns_per_ray_median")
    put(c, "sagitta_po_ns_per_ray", f"{RB}:answer.cost_per_ray.sagitta_A100_po_ns_per_ray")
    put(c, "verdict", f"{RB}:answer.verdict")
    put(c, "what_it_does_not_support", f"{RB}:answer.what_the_measurement_does_NOT_support")
    c["honest_concession"] = ("반론의 절반은 맞다 — **우리 구현에서** PO 적분이 광선캐스팅의 16 배다. "
                              "우리 적분이 아직 호스트 numpy 라서다. 게재된 유일한 GPU 커널 분해"
                              "(SagittaSBR Table 1)는 같은 캐스케이드가 광선발사의 1.9~6.5% 라고 적는다.")
    s["cascade_cost_objection"] = c

    # ── 대안 5갈래 ──────────────────────────────────────────────────────────────────────
    alts: list = []

    a1 = {"method": "① 완전파 (MoM / MLFMM / FDTD)",
          "what_it_solves": "맥스웰 방정식을 근사 없이 푼다. 크리핑파·다중산란·편파를 전부 포함한다.",
          "accuracy": "참값. 이 라운드의 2D EFIE MoM 자체검사는 정확 원기둥 고유함수해 대비 "
                      "worst 0.00027 dB 다.",
          "our_position": "우리 **검증 과녁**으로 쓴다(§3 3층). 생산 계산으로는 쓰지 않는다."}
    put(a1, "mom2d_selftest_worst_db", f"{LA}:thin_plate.mom_selftest.worst_abs_db_at_240seg")
    put(a1, "cost_quote_mlfmm", f"{RB}:published_baselines.rows[4].quote")
    a1["cost_reading"] = ("표를 못 만든다. 회당 several hours 면 우리 격자 16,200 셀은 불가능하다. "
                          "이 추론은 두 비용 수치에서 나온 **가설**이며 어떤 논문도 이렇게 말하지 않는다.")
    a1["cost_reading_src"] = "doc: docs/INJECTION_PRECEDENT.md §4.2"
    alts.append(a1)

    a2 = {"method": "② SBR + PO (우리)",
          "what_it_solves": "광선으로 '어느 면이 실제로 조명되는가' 를 찾고, 그 면에서 PO 표면적분으로 "
                            "σ 를 낸다. 상용 EM 솔버(FEKO/CST/HFSS SBR+)의 고주파 표준 방법이다.",
          "accuracy": "해석 PO 대비 수치수렴은 소수 셋째 자리(§3). 참값 대비는 특징/λ 의 함수(§4).",
          "our_position": "생산 경로."}
    put(a2, "per_pose_ms_median", f"{RB}:answer.two_passes.headline_pass.median")
    alts.append(a2)

    a3 = {"method": "③ 통계 RCS 주입 (3GPP 표 조회)",
          "what_it_solves": "σ 를 규격 표에서 읽어 각도 섹터로 조회하고 경로전력에 곱한다.",
          "our_position": "우리 격자와 **같은 구조**다. 갈리는 곳은 '표를 누가 만드는가' 뿐이다."}
    put(a3, "tr38901_small_uav_dbsm",
        f"{IS}:the_specification.the_shipped_numbers.table_7.9.2.1-1.UAV with small size."
        f"10lg(sigma_M)_dBsm")
    put(a3, "tr38901_sigma_S_std_db",
        f"{IS}:the_specification.the_shipped_numbers.table_7.9.2.1-1.UAV with small size."
        f"sigma_S_std_dB")
    put(a3, "no_frequency_axis",
        f"{IS}:the_specification.what_the_standard_deliberately_left_out.no_frequency_axis")
    put(a3, "company_spread_is_the_field_precision", f"{IS}:what_this_means_for_us[5]")
    a3["accuracy"] = ("주파수축이 없고 각도는 섹터 단위다. 같은 크기급에 대해 제출된 회사값이 "
                      "−10 ~ −19.78 dBsm 로 벌어져 있었다 — 그 산포가 이 분야의 합의 정밀도다.")
    alts.append(a3)

    a4 = {"method": "④ 기하 대리표적 (큐브·박스·구)",
          "what_it_solves": "표적을 정육면체·직육면체·구로 바꾼다. 선행에서 가장 흔한 회피다.",
          "our_position": "대조군으로 **같은 자로** 재봤다(benchmark/p3_control.py, 같은 PO 커널·"
                          "같은 방위격자·같은 실측 앵커)."}
    for nm, key in [("ours_mesh", "ours_p3_mesh"), ("box_bbox", "box_bbox_lit"),
                    ("cube_eqvol", "cube_eqvol_bbox"), ("cube_side_max", "cube_side_max"),
                    ("sphere_eqvol_mie", "sphere_eqvol_mie")]:
        put(a4, nm + "_mean_delta_db", f"{PC}:comparison.{key}.mean_delta_db")
        put(a4, nm + "_rms_delta_db", f"{PC}:comparison.{key}.rms_delta_db")
        put(a4, nm + "_slope_err_db_per_ghz", f"{PC}:comparison.{key}.slope_err")
    a4["reading"] = ("박스·큐브는 전부 **크게 과대평가**한다 — 최대치수 큐브는 +19.5 dB, 100 배 가깝다. "
                     "⚠ 그러나 등가부피 PEC 구는 밴드평균 레벨에서 우리보다 낫다(+0.90 vs −4.91 dB). "
                     "구가 사지 못하는 것은 주파수 의존(기울기 오차 −0.348 vs 우리 +0.061)과 "
                     "각도 구조(ε=0)이고, 그 +0.90 dB 는 등가반지름 규칙 4개가 6.51 dB 를 벌리는 "
                     "**자유 손잡이**를 돌려 나온 값이다.")
    a4["reading_src"] = "doc: docs/MESH_VALIDATION.md §6.2·§6.3"
    alts.append(a4)

    a5 = {"method": "⑤ 실측",
          "what_it_solves": "무향실·CATR 에서 직접 잰다. 절대 앵커의 최종 출처다.",
          "our_position": "우리 절대 레벨의 앵커. 자체 측정이 아니라 **공개 문헌 RCS** 다."}
    put(a5, "das_slope_db_per_ghz", f"{RA}:literature.mu_eps.das_phantom3_mono.mu_a")
    put(a5, "das_band_ghz", f"{RA}:literature.mu_eps.das_phantom3_mono.band_ghz")
    put(a5, "yuan_az_plane_slope_db_per_ghz",
        f"{RA}:literature.mu_eps.yuan_phantom3_azplane.mu_a")
    a5["caveat"] = ("Das WCL 2026 은 Yuan EuCAP 2025 **원자료의 재분석**이다(사사에 명시) — "
                    "'독립 앵커 2건' 이 아니라 측정 1건이다.")
    a5["caveat_src"] = "doc: docs/RETRACTION_LOG.md 추가정정 A2"
    alts.append(a5)

    s["alternatives"] = alts

    # ── 이 분야가 실제로 무엇을 인쇄하는가 ────────────────────────────────────────────────
    f: dict = {"_what": "원문 정독 18편의 진폭 정당화 인구조사(outputs/evasion_catalogue.json)."}
    put(f, "papers_read_in_full_text", f"{EV}:counts.papers_read_in_full_text")
    put(f, "absolute_dbsm_as_computed_output", f"{EV}:counts.absolute_dbsm_as_computed_output")
    put(f, "absolute_dbsm_for_a_drone_target_computed",
        f"{EV}:counts.absolute_dbsm_for_a_drone_target_computed")
    put(f, "sionna_based_subset", f"{EV}:counts.sionna_based_subset")
    put(f, "sionna_based_that_print_computed_absolute_dbsm",
        f"{EV}:counts.sionna_based_that_print_computed_absolute_dbsm")
    put(f, "headline_findings", f"{EV}:headline_findings_ko")
    s["what_the_field_actually_prints"] = f
    return s


# ================================================================================================
#  §2  우리 PO 커널이 정확히 무엇인가
# ================================================================================================
def section2() -> dict:
    s: dict = {"_title": "우리 PO 커널 — src/rcs_sbr.py 를 수식으로 풀어 쓴다"}

    #  ── 유도 (건너뛰지 않는다) ──────────────────────────────────────────────────────────
    s["derivation"] = [
        {"step": 1,
         "statement": "모노스태틱 PO 의 출발점:  E(û) ∝ ∬_조명면 (n̂·û) · e^{j2k r·û} dS",
         "symbols": "û = 표적→레이더 단위벡터 · n̂ = 면의 바깥 법선 · k = 2π/λ · r = 면 위의 점 · "
                    "dS = 면적요소",
         "plain": "조명된 표면의 모든 점이 각자 위상 e^{j2k r·û} 를 갖고 더해진다. (n̂·û) 는 "
                  "'그 점이 레이더 쪽으로 얼마나 정면을 보고 있나' 를 재는 비스듬함(obliquity) 계수다."},
        {"step": 2,
         "statement": "û 에 수직인 평면으로 변수변환:  (n̂·û) dS = dA_투영",
         "symbols": "dA_투영 = 그 면적요소를 û 방향에서 본 **그림자 면적**",
         "plain": "면이 기울어져 있으면 실제 면적 dS 는 크지만 정면에서 본 넓이는 (n̂·û) 배로 줄어든다. "
                  "그 두 요인이 정확히 **상쇄**된다 — 이것이 이 커널의 핵심이다.",
         "why_it_matters": "비스듬함 계수를 따로 계산할 필요가 사라진다. 대신 '투영면에 균일 격자로 "
                           "광선을 쏘는 것' 자체가 구적법이 된다."},
        {"step": 3,
         "statement": "따라서  E(û) ∝ ∬ e^{j2k r·û} dA_투영",
         "plain": "적분이 표면 위가 아니라 **투영 평면 위**의 적분으로 바뀌었다."},
        {"step": 4,
         "statement": "투영면에 간격 d 의 균일 격자로 평행 광선을 쏜다. 광선 1발이 대표하는 투영면적은 d² 다.",
         "plain": "격자의 칸 하나가 dA_투영 하나다. 광선이 맞은 지점 p_i 마다 위상을 계산해 더하면 "
                  "적분이 합으로 바뀐다."},
        {"step": 5,
         "statement": "E = Σ_hits |Γ_i| · e^{j2k p_i·û} · d²      [단위 m²]",
         "symbols": "|Γ_i| = 그 지점 재질의 Fresnel 반사 진폭(materials.py, Sionna 와 같은 표) · "
                    "p_i = 광선이 맞은 점",
         "plain": "재질이 다른 부품(플라스틱 셸·카본·금속 모터·배터리)이 각자 다른 |Γ| 로 기여한다."},
        {"step": 6,
         "statement": "σ = (4π/λ²) · |E|²      [단위 m², dBsm 은 10log10]",
         "plain": "복소 산란장 E 를 레이더 단면적으로 바꾸는 표준 변환이다. 우리가 σ 가 아니라 "
                  "**복소 E** 를 내부에 갖고 있다는 점이 중요하다 — 마이크로도플러는 위상이 필요하다."},
        {"step": 7,
         "statement": "가림(self-shadowing)은 **공짜**다 — Mitsuba first-hit 이 뒤에 가려진 면을 "
                      "애초에 맞히지 않는다. 조명 게이트는 (n̂·û) > 1e-6 이다.",
         "plain": "이것이 SBR 이 '점구름 PO' 보다 나은 이유다. 팔에 가린 동체, 프로펠러에 가린 모터가 "
                  "자동으로 빠진다."},
        {"step": 8,
         "statement": "바이스태틱 일반형:  E ∝ Σ_hit |Γ| · e^{jk(û_i+û_s)·p} · d²",
         "symbols": "û_i = 표적→송신국 · û_s = 표적→수신국",
         "plain": "모노스태틱은 û_s = û_i 인 특수해이고, 그때 지수가 e^{j2k û·p} 로 정확히 돌아간다.",
         "extra_gate": "수신 가시성 — 법선 판정 (n̂·û_s)>0 에 더해 히트점마다 û_s 로 그림자광선을 "
                       "1발 더 쏜다(exit_vis). 모노스태틱에서는 정확한 no-op 다(실측 0.000 dB)."},
    ]

    #  ── 생산 설정 (코드에서 확인한 것) ──────────────────────────────────────────────────
    p: dict = {"_where": "src/experiment_freespace_sigma.py:92-96 · src/rcs_sbr.py:84 · "
                         "outputs/lowfreq_grid.json:_meta.convention"}
    put(p, "div", f"{RB}:meta.production_settings.div")
    put(p, "jitter", f"{RB}:meta.production_settings.jitter")
    put(p, "penetrate", f"{RB}:meta.production_settings.penetrate")
    put(p, "n_f_band_average", f"{RB}:meta.production_settings.n_f_band_average")
    put(p, "settings_source_line", f"{RB}:meta.production_settings.source")
    putl(p, "kernel_default_div", 12, "src/rcs_sbr.py:84 (DEFAULT_DIV)")
    putl(p, "max_bounce", 1, "src/experiment_freespace_sigma.py:28 (스펙 §9 다중반사 금지)")
    putl(p, "ptd", False, "src/rcs_sbr.py:185-187 (rcs_sbr_batch 시그니처 기본값 ptd=False)")
    put(p, "production_convention_line", f"{LG}:_meta.convention")
    p["spacing_meaning"] = "격자 간격 d = λ/div. div=16 이면 3.5 GHz 에서 d = 5.36 mm."
    p["jitter_meaning"] = ("J=2 면 서브셀 오프셋 J²=4 개를 평균한다. 격자 정렬이 우연히 유리·불리해지는 "
                           "위상 에일리어싱을 눌러 절대 σ 를 안정화한다.")
    p["penetrate_meaning"] = ("유전체 셸(body·canopy)을 왕복 투과 τ=1−|Γ|² 로 통과시켜 내부 금속"
                              "(배터리·PCB)을 코히어런트 가산한다. 셸 선언은 이름 규약이 아니라 "
                              "|Γ| ≤ 0.5 검사로 강제한다 — 카본 데크를 body 로 넣으면 즉시 예외.")
    s["production_settings"] = p

    #  ── 격자 산포 (절대레벨 불확실성) ───────────────────────────────────────────────────
    g: dict = {"_what": "서브셀 오프셋을 흔들었을 때의 **단일격자** σ 산포(peak-to-peak). "
                        "구 r=0.5 m·3.5 GHz. 수렴은 단조롭지 않다 — λ/12 가 λ/16 보다 작다."}
    for i, div in enumerate([8, 12, 16, 24]):
        put(g, f"dither_spread_div{div}_db", f"{W2}:sbr_validation.dither[{i}].spread")
    g["reading"] = ("이 산포가 절대 σ 에 붙는 격자 불확실성이다. 숫자를 인용할 때는 반드시 div 를 "
                    "함께 적는다. 자세 **간** 상대 패턴은 이보다 훨씬 안정하다.")
    s["grid_dither"] = g

    #  ── 같은 방법론인가 / 우리 것은 무엇을 안 하는가 ───────────────────────────────────
    s["same_methodology_as"] = {
        "statement": "그래픽 레이트레이서 위에 자기 PO 적분기를 얹는 것은 우리 발명이 아니라 "
                     "**이 문제의 표준 대응**이고, 두 팀이 독립적으로 같은 곳에 도달했다.",
        "quote_mc_sbr": "\"Our implementation is not simply a direct application of Mitsuba, which "
                        "does not currently support surface current calculation or physical optics "
                        "integration.\" — Monte-Carlo SBR (UMD), arXiv:2511.07586 p.7",
        "sagitta": "SagittaSBR(arXiv:2604.09243)은 독립 SBR+PO RCS 솔버이고 코드를 공개했다.",
        "how_to_write_it": "'우리는 이렇게 했다' 가 아니라 '이 구조가 이 문제의 표준 대응이고, "
                           "우리는 그것을 **부품별 재질을 가진 드론**에 처음 적용했다'.",
        "src": "doc: docs/HOW_OTHERS_SOLVED_IT.md §5",
    }
    s["what_our_kernel_does_not_do"] = [
        {"item": "모서리 프린지(PTD) 항", "state": "배선은 돼 있고 **생산에서는 꺼져 있다**(ptd=False). "
         "ptd=False 경로는 배선 이전과 비트 단위로 같다.",
         "note": "PTD 를 켜도 저대역이 닫히지 않는다는 것이 §4 의 결과다."},
        {"item": "2회 이상 다중반사", "state": "생산 σ 는 전부 1-bounce 다.",
         "note": "오목한 이면반사체에서는 2-bounce 가 필수다 — 그 검증은 §3 에 있고, 드론 생산 경로는 "
                 "아니다."},
        {"item": "편파", "state": "면적분이 **스칼라**라 VV/HH 를 가르지 못한다.",
         "note": "얇은 띠 참값이 0.15λ 에서 편파로 11.56 dB 갈라진다 — 그 갈라짐을 원리적으로 낼 수 없다."},
        {"item": "크리핑파·표면파", "state": "없다.",
         "note": "Sionna 에도 없다. 매끄러운 볼록체 그림자 경계를 감아 도는 성분이다."},
        {"item": "전방산란(β→180°)", "state": "σ ≡ 0 이 된다 — 조명 게이트와 수신 게이트가 상호배타다.",
         "note": "lit-PO 는 Babinet 전방로브를 못 낸다. 주장 창을 후방~중간 바이스태틱각으로 못박는다."},
        {"item": "셸 내부 흡수손실", "state": "τ=1−|Γ|² 는 반사되지 않은 전력이 전부 통과한다고 본다.",
         "note": "유전손실을 무시하는 **상한**이다."},
    ]
    return s


# ================================================================================================
#  §3  검증 3층
# ================================================================================================
def section3() -> dict:
    s: dict = {
        "_title": "검증 3층 — ① 해석 PO 수렴 ② PEC 구 Mie 정확해 ③ 얇은 판 2D MoM",
        "_the_decomposition": "(커널 − 참값) = (커널 − 해석 PO) + (해석 PO − 참값). "
                              "①이 앞항을, ②③이 뒷항을 잰다. 두 항은 성질이 다르다 — "
                              "앞항은 **구현 오차**(격자를 조이면 준다), 뒷항은 **모형 오차**"
                              "(격자로는 못 고친다).",
        "_decomposition_src": f"{LA}:_meta.decomposition",
    }

    # ── 1층: 해석 PO 수렴 (커널 구현 검증) ──────────────────────────────────────────────
    l1: dict = {"_what": "커널이 **PO 를 제대로 계산하는가**. 과녁은 정확 Mie 가 아니라 해석 PO 다 — "
                         "커널이 PO 이기 때문이다."}
    put(l1, "kr_sweep_max_abs_db_vs_po_div16", f"{KR}:summary_div16.max_abs_db_vs_po")
    put(l1, "kr_sweep_std_pct_vs_po_div16", f"{KR}:summary_div16.std_sbr_over_po_pct")
    put(l1, "kr_sweep_std_pct_vs_po_kr_ge30", f"{KR}:summary_div16.std_sbr_over_po_pct_kr_ge30")
    put(l1, "kr_sweep_n_points", f"{KR}:summary_div16.n_points")
    put(l1, "kr_sweep_kr_min", f"{KR}:summary_div16.kr_min")
    put(l1, "kr_sweep_kr_max", f"{KR}:summary_div16.kr_max")
    put(l1, "kr_sweep_n_incidence", f"{KR}:meta.n_incidence")
    put(l1, "kr_sweep_runtime_s", f"{KR}:meta.runtime_s")
    putc(l1, "kr_sweep_ms_per_incidence",
         1000.0 * fetch(f"{KR}:meta.runtime_s") / (2 * fetch(f"{KR}:meta.n_incidence")
                                                   * fetch(f"{KR}:summary_div16.n_points")),
         "meta.runtime_s ÷ (div 2개 × n_incidence × n_points) × 1000")
    put(l1, "sphere_ka1_kernel_vs_po_at_finest_db", f"{LA}:sphere.per_ka.1.finest.vs_po_db")
    put(l1, "sphere_ka1_finest_d_mm", f"{LA}:sphere.per_ka.1.finest.d_mm")
    put(l1, "sphere_ka1_grid_refine_factor", f"{LA}:sphere.per_ka.1.grid_refine_factor")
    put(l1, "sphere_ka1_ray_count_factor", f"{LA}:sphere.per_ka.1.ray_count_factor")
    put(l1, "thin_plate_0p15lam_vs_po_at_lam12_db",
        f"{LA}:thin_plate.per_width.0.15.vs_po_at_lam12_db")
    put(l1, "thin_plate_0p15lam_vs_po_at_finest_db",
        f"{LA}:thin_plate.per_width.0.15.vs_po_at_finest_db")
    put(l1, "plate_normal_incidence_note", f"{DF}:d3_multibounce_phase.exact_formula")
    l1["plate_is_exact_not_asymptotic"] = ("PEC 평판 정면입사에서 4πA²/λ² 는 점근이 아니라 **PO 의 "
                                           "정확한 답**이다. 그래서 이 과녁은 격자만 잰다.")
    l1["reading"] = ("격자를 209 배 조이면(광선 7087 배) 커널이 해석 PO 에 소수 넷째 자리로 붙는다. "
                     "'우리 PO 면적분이 PO 를 제대로 계산한다' 는 확립됐다.")
    s["layer1_analytic_po_convergence"] = l1

    # ── 2층: PEC 구 정확 Mie ───────────────────────────────────────────────────────────
    l2: dict = {"_what": "PO 라는 **모형** 이 참값에서 얼마나 떨어지는가. 구는 정확 Mie 급수해가 있다."}
    put(l2, "po_minus_mie_at_ka1_db", f"{LA}:sphere.per_ka.1.po_minus_mie_db")
    put(l2, "kernel_minus_mie_at_ka1_lam12_db", f"{LA}:sphere.per_ka.1.lam12.vs_mie_db")
    put(l2, "kernel_minus_mie_at_ka1_finest_db", f"{LA}:sphere.per_ka.1.finest.vs_mie_db")
    put(l2, "improvement_from_refining_grid_db", f"{LA}:sphere.per_ka.1.improvement_vs_mie_db")
    put(l2, "kr_sweep_std_pct_vs_mie_kr_ge30_div16",
        f"{KR}:summary_div16.std_sbr_over_mie_pct_kr_ge30")
    put(l2, "kr_sweep_max_abs_db_vs_mie", f"{KR}:summary_div16.max_abs_db_vs_mie")
    # 생산 밴드에서의 교정구 (Yuan 17.8 cm · 25 cm)
    put(l2, "cal_sphere_r178mm_lte_dev_vs_mie_db",
        f"{RA}:sphere_calibration.LTE 1.843 GHz.spheres[1].dev_db_vs_mie")
    put(l2, "cal_sphere_r178mm_lte_dev_vs_po_db",
        f"{RA}:sphere_calibration.LTE 1.843 GHz.spheres[1].dev_db_vs_po")
    put(l2, "cal_sphere_r178mm_lte_ka",
        f"{RA}:sphere_calibration.LTE 1.843 GHz.spheres[1].ka")
    put(l2, "cal_sphere_r250mm_5g_dev_vs_mie_db",
        f"{RA}:sphere_calibration.5G 3.5 GHz.spheres[0].dev_db_vs_mie")
    put(l2, "cal_sphere_r250mm_5g_ka",
        f"{RA}:sphere_calibration.5G 3.5 GHz.spheres[0].ka")
    l2["reading"] = ("ka=1 에서 커널−Mie 간극 6.53 dB 는 격자를 209 배 조여도 6.58 dB 로 "
                     "**0.05 dB 밖에 안 준다** — 그리고 그 값은 해석 PO−Mie 간극 그 자체다. "
                     "저 ka 오차는 표본화가 아니라 PO 다. 반대로 kr≥30(광학영역)에서는 Mie 대비 "
                     "산포가 1.8% 로 떨어진다.")
    l2["fairness"] = ("이 층은 '우리 커널이 나쁘다' 가 아니라 'PO 라는 근사가 언제 성립하는가' 를 잰다. "
                      "같은 자를 어떤 SBR+PO 솔버에 대도 같은 결과가 나온다.")
    s["layer2_pec_sphere_mie"] = l2

    # ── 3층: 얇은 판 2D MoM ────────────────────────────────────────────────────────────
    l3: dict = {"_what": "드론의 진짜 문제는 **가는 특징**이다. 폭 a 의 얇은 띠에서 PO 를 근사 없는 "
                         "2D EFIE MoM 참값과 맞댄다."}
    put(l3, "mom_selftest_worst_db", f"{LA}:thin_plate.mom_selftest.worst_abs_db_at_240seg")
    put(l3, "mom_selftest_reference", f"{LA}:thin_plate.mom_selftest.reference")
    put(l3, "po_minus_tm_at_0p15lam_db", f"{LA}:thin_plate.truth_2d_mom.0.15.po_minus_tm_db")
    put(l3, "po_minus_te_at_0p15lam_db", f"{LA}:thin_plate.truth_2d_mom.0.15.po_minus_te_db")
    put(l3, "tm_minus_te_at_0p15lam_db", f"{LA}:thin_plate.truth_2d_mom.0.15.tm_minus_te_db")
    put(l3, "po_minus_tm_at_1lam_db", f"{LA}:thin_plate.truth_2d_mom.1.po_minus_tm_db")
    put(l3, "po_minus_te_at_1lam_db", f"{LA}:thin_plate.truth_2d_mom.1.po_minus_te_db")
    put(l3, "po_minus_tm_at_2lam_db", f"{LA}:thin_plate.truth_2d_mom.2.po_minus_tm_db")
    # PTD 를 얹으면?
    put(l3, "po_ptd_minus_tm_at_0p15lam_db",
        f"{LA}:ptd_does_not_close_it.per_width.0.15.po_ptd_minus_tm_db")
    put(l3, "po_ptd_minus_te_at_0p15lam_db",
        f"{LA}:ptd_does_not_close_it.per_width.0.15.po_ptd_minus_te_db")
    put(l3, "ptd_v_minus_h_at_0p15lam_db",
        f"{LA}:ptd_does_not_close_it.per_width.0.15.v_minus_h_db")
    l3["ptd_reading"] = ("1차 프린지는 정면입사에서 편파를 못 가른다(V−H ≈ 1e-10 dB). 그래서 TM 을 "
                         "−4.02 → −0.75 dB 로 고치는 대신 TE 를 +7.53 → +10.81 dB 로 **악화**시킨다. "
                         "'PTD 를 켜면 저대역이 고쳐진다' 는 희망은 여기서 죽는다.")
    l3["scalar_po_structural_limit"] = ("참값이 0.15λ 에서 편파로 11.56 dB 갈라지는데 스칼라 면적분은 "
                                        "그 갈라짐을 **원리적으로** 낼 수 없다. 이것은 크기 귀속이 "
                                        "필요 없는 구조에 대한 주장이다.")
    s["layer3_thin_plate_2d_mom"] = l3

    # ── 보조: 오목부 다중반사 ──────────────────────────────────────────────────────────
    l4: dict = {"_what": "직각 이면반사체 — 볼록체 과녁 두 개가 못 잡는 **다중반사 위상**을 잡는 유일한 검증."}
    put(l4, "exact_formula", f"{DF}:d3_multibounce_phase.exact_formula")
    put(l4, "max_abs_err_2bounce_db", f"{DF}:d3_multibounce_phase.max_abs_err_db")
    put(l4, "a03_exact_dbsm", f"{DF}:d3_multibounce_phase.rows[2].exact_dbsm")
    put(l4, "a03_sbr_1bounce_dbsm", f"{DF}:d3_multibounce_phase.rows[2].sbr_1bounce_dbsm")
    put(l4, "a03_sbr_2bounce_dbsm", f"{DF}:d3_multibounce_phase.rows[2].sbr_2bounce_dbsm")
    l4["reading"] = ("1-bounce 로는 이면반사체가 −118 dBsm 으로 죽고, 2-bounce 를 켜면 해석해에 "
                     "0.08 dB 로 붙는다. 우리 **생산** 경로는 1-bounce 이므로, 드론에 깊은 오목부가 "
                     "있다면 그 성분이 빠진다.")
    s["layer4_dihedral_multibounce"] = l4

    # ── 상반성 (자기 커널 검사) ────────────────────────────────────────────────────────
    l5: dict = {"_what": "상반성 σ(û_i,û_s)=σ(û_s,û_i) 는 **정리**이므로 위반은 전부 모형오차다. "
                         "213편 중 자기 커널에 이 검사를 돌린 논문은 0편이다."}
    put(l5, "drone_worst_violation_db", f"{DF}:d2_reciprocity_drone.worst_db")
    put(l5, "drone_worst_without_exit_vis_db",
        f"{DF}:d2_exit_vis_effect_on_reciprocity.worst_without_exit_vis_db")
    put(l5, "drone_worst_after_symmetrize_db", f"{DF}:d2_reciprocity_drone.worst_after_symmetrize_db")
    put(l5, "symmetrize_honest_note", f"{DF}:d2_reciprocity_drone.honest_note")
    l5["reading"] = ("우리가 이 검사를 인쇄하는 것은 우리 커널이 나쁘다는 뜻이 아니라, 다른 커널들은 "
                     "같은 결함이 있어도 **보이지 않는다**는 뜻이다.")
    l5["reading_src"] = "doc: docs/HOW_OTHERS_SOLVED_IT.md §2 (P8)"
    s["layer5_reciprocity_selfcheck"] = l5
    return s


# ================================================================================================
#  §4  한계 — 감추지 않고 정면으로
# ================================================================================================
def section4() -> dict:
    s: dict = {"_title": "⚠ 한계 — PO 유효 무릎과, 아직 크기를 못 정한 것"}

    # ── PO 유효 무릎 ──────────────────────────────────────────────────────────────────
    put(s, "po_validity_knee_a_over_lambda",
        f"{LA}:thin_plate.truth_2d_mom_fine_width_grid.knee_a_over_lam")
    put(s, "po_validity_knee_rule",
        f"{LA}:thin_plate.truth_2d_mom_fine_width_grid.knee_rule")
    put(s, "knee_establishing_sentence",
        f"{LK}:q5_blast_radius.po_validity_blast_radius_the_real_one.what_this_round_establishes")

    kf: dict = {"_what": "각 부품이 그 무릎(폭 ≥ 0.729λ)을 통과하는 주파수 [GHz]. "
                         "⚠ 적대검증 에이전트가 재계산한 값이며 crude 라고 스스로 표시했다."}
    base = (f"{LK}:q5_blast_radius.po_validity_blast_radius_the_real_one."
            f"recomputed_by_me_frequency_at_which_each_feature_passes_that_knee")
    for nm, key in [("body_81p51mm", "body_81.51mm"), ("arm_root_45mm", "arm_root_45mm"),
                    ("arm_tip_30mm", "arm_tip_30mm"), ("prop_blade_13p78mm", "prop_blade_13.78mm"),
                    ("motor_13p68mm", "motor_13.68mm"), ("canopy_6p22mm", "canopy_6.22mm"),
                    ("pcb_2p99mm", "pcb_2.99mm")]:
        put(kf, nm + "_ghz", f"{base}.{key}")
    s["feature_knee_frequencies"] = kf

    pb: dict = {"_what": "우리 생산 3 밴드. **body 를 뺀 모든 특징이 무릎 아래**다."}
    putl(pb, "lte_ghz", 1.843, "src/experiment_freespace_sigma.py:63 (BANDS)")
    putl(pb, "nr_ghz", 3.500, "src/experiment_freespace_sigma.py:64 (BANDS)")
    putl(pb, "wifi_ghz", 5.210, "src/experiment_freespace_sigma.py:65 (BANDS)")
    put(pb, "the_uncomfortable_corollary",
        f"{LK}:q5_blast_radius.po_validity_blast_radius_the_real_one."
        f"⭐_the_uncomfortable_corollary")
    put(pb, "sign_of_the_error",
        f"{LK}:q5_blast_radius.po_validity_blast_radius_the_real_one.sign_of_the_error")
    s["our_production_bands_vs_knee"] = pb

    # ── 드론 특징 스케일에서의 실제 간극 ────────────────────────────────────────────────
    gap: dict = {"_what": "1.8 GHz 에서 드론 부품 폭 / λ, 그리고 그 폭에서 잰 worst-pol |PO−참값|."}
    gbase = f"{LA}:consistency_with_drone"
    for nm in ["prop", "arm_tip", "arm_root", "body"]:
        put(gap, nm + "_over_lambda_at_1p8ghz",
            f"{gbase}.drone_feature_over_lambda_at_1p8ghz.{nm}")
        put(gap, nm + "_worst_pol_gap_db",
            f"{gbase}.checks.gap_lives_at_drone_feature_scales."
            f"worst_pol_gap_db_at_drone_features.{nm}")
    put(gap, "mean_gap_db_for_feature_ge_1lam",
        f"{gbase}.checks.gap_lives_at_drone_feature_scales.mean_gap_db_for_feature_ge_1lam")
    put(gap, "max_gap_db_for_feature_0p05_to_0p30_lam",
        f"{gbase}.checks.gap_lives_at_drone_feature_scales.max_gap_db_for_feature_0p05_to_0p30_lam")
    s["gap_at_drone_feature_scales"] = gap

    # ── 저주파 격자 수렴: 조여도 안 변한다 ──────────────────────────────────────────────
    gr: dict = {"_what": "1.8 GHz 에서 광선격자를 절대값[mm]으로 계단식으로 조였을 때 μ 가 움직이는가."}
    put(gr, "ladder_total_spread_at_1p8_db", f"{gbase}.drone.ladder_total_spread_at_1p8_db")
    put(gr, "shift_converged_minus_lam16_db", f"{gbase}.drone.shift_conv_minus_lam16_db_at_1p8")
    put(gr, "a_lowband_at_lam16", f"{gbase}.drone.a_lowband_lam16")
    put(gr, "a_lowband_converged", f"{gbase}.drone.a_lowband_converged")
    put(gr, "a_highband_converged", f"{gbase}.drone.a_highband_converged")
    put(gr, "das_anchor_a", f"{gbase}.drone.das_anchor_a")
    put(gr, "what_would_it_take_lowband_db", f"{LG}:what_would_it_take.lowband.delta_mu_at_lowest_freq_db")
    put(gr, "lowfreq_grid_bottom_line", f"{LG}:bottom_line")
    gr["interpretation_limit"] = ("격자 정련이 산 것은 (커널 − 해석 PO) 뿐이다. 정확한 진술은 "
                                  "'격자는 무관하다' 가 아니라 '격자로 살 수 있는 것에 상한이 있고 "
                                  "그 상한이 간극보다 훨씬 작다' 이다.")
    gr["interpretation_limit_src"] = f"{LA}:caveats[5]"
    s["low_frequency_grid_convergence"] = gr

    # ── ⭐ 정직한 라벨 ────────────────────────────────────────────────────────────────
    hv: dict = {"_what": "적대검증이 이 판정을 공격한 결과. **그대로 싣는다.**"}
    put(hv, "attacked_verdict_label", f"{LG}:verdict")
    put(hv, "adversarial_verdict", f"{LK}:verdict")
    put(hv, "why_not_SOUND", f"{LK}:verdict_reasoning.why_not_SOUND")
    put(hv, "why_not_BROKEN", f"{LK}:verdict_reasoning.why_not_BROKEN")
    put(hv, "one_line", f"{LK}:verdict_reasoning.one_line")
    put(hv, "the_structural_flaw", f"{LK}:verdict_reasoning.the_structural_flaw")
    hv["honest_labels"] = ["A_EXCLUDED", "B_CONTRIBUTES_SIGN_ONLY", "C_UNBOUNDED"]
    hv["honest_labels_src"] = f"{LK}:verdict_reasoning.why_not_SOUND"
    hv["honest_labels_meaning"] = {
        "A_EXCLUDED": "가설 A(광선 표본화)는 배제됐다 — 크기·부호·양성대조·독립복제·jitter 재채점까지 다 있다.",
        "B_CONTRIBUTES_SIGN_ONLY": "가설 B(PO 근본한계)는 **부호만** 확인됐다. 크기 귀속이 없다.",
        "C_UNBOUNDED": "세 번째 축(기하·테셀레이션·CAD)이 자기 데이터 안에서 이미 격자효과의 33 배로 "
                       "관측되는데 경계가 지어지지 않았다.",
    }
    put(hv, "what_survives_the_attack", f"{LK}:what_survives_the_attack")
    put(hv, "what_does_not_survive", f"{LK}:what_does_not_survive")
    put(hv, "must_fix", f"{LK}:must_fix")
    put(hv, "residual_holes", f"{LK}:residual_holes_i_could_not_close")
    put(hv, "what_must_not_be_said", f"{LK}:q5_blast_radius.what_must_not_be_said")
    put(hv, "sampling_blast_radius_size", f"{LK}:q5_blast_radius.sampling_blast_radius_actual.size")
    put(hv, "sampling_blast_radius_direction",
        f"{LK}:q5_blast_radius.sampling_blast_radius_actual.direction")
    put(hv, "affected_outputs_scoping_note", f"{LK}:q5_blast_radius.affected_outputs_scoping_note")
    s["adversarial_verdict_verbatim"] = hv

    # ── 그 밖의 열린 한계 ─────────────────────────────────────────────────────────────
    put(s, "anchor_caveats", f"{LA}:caveats")
    s["other_open_limits"] = [
        {"item": "생산 경로에 대한 참값 대조가 없다",
         "detail": "참값 앵커는 전부 penetrate=False · |Γ|=1 · 볼록(자기가림 없음)이다. 생산은 "
                   "penetrate=True · 재질 Γ · 자기가림 · 1-bounce 다. 이 라운드가 검증한 것은 "
                   "그 경로의 **부분집합**이다.",
         "src": f"{LK}:residual_holes_i_could_not_close[4]"},
        {"item": "테셀레이션 축이 무경계다",
         "detail": "메쉬 사다리는 앵커 물체 두 점에서만 돌렸다. 드론 본체에서 재테셀레이션 사다리를 "
                   "돌리지 않았고, 오차의 **부호조차** 모른다.",
         "src": f"{LK}:residual_holes_i_could_not_close[1]"},
        {"item": "outputs/ptd_drone_effect.json 은 SUPERSEDED 다",
         "detail": "부호 결함 커널로 생산된 판이라 **어떤 숫자도 인용하지 않는다**. PTD 가 드론 밴드 "
                   "기울기를 움직이는지에 대한 유효한 수치는 이 저장소에 현재 없다.",
         "src": "outputs/ptd_drone_effect.json:SUPERSEDED.status"},
    ]
    return s


# ================================================================================================
#  §5  선행연구에서 빌려온 것 / 빌려올 수 있는 것
# ================================================================================================
def section5() -> dict:
    s: dict = {
        "_title": "선행에서 빌린 것과 아직 안 빌린 것",
        "_standing_rule": "저장소 상시규칙 — 리포트마다 선행 방법론을 최대한 가져오고, 우리 결과를 "
                          "선행 수치와 나란히 놓는다(사과-대-사과 검사 필수).",
    }

    # ── 이미 빌린 것 ──────────────────────────────────────────────────────────────────
    borrowed: list = []

    b1 = {"what": "분포적합 · μ/ε 회귀 · 금속구 교정 · 분위점 · RMSE",
          "from": "Das(IEEE WCL 2026) · Yuan(EuCAP 2025) 이 실제로 쓴 절차 그대로",
          "where_in_our_repo": "benchmark/rcs_anchor.py (docstring 첫 줄이 이 차용을 명시한다)",
          "what_it_bought": "report08 이 '보류(defer)' 로 남긴 절대 σ 판정을 문헌과 같은 자로 채웠다."}
    put(b1, "das_mu_a", f"{RA}:literature.mu_eps.das_phantom3_mono.mu_a")
    put(b1, "das_eps_d", f"{RA}:literature.mu_eps.das_phantom3_mono.eps_d")
    put(b1, "yuan_az_mu_a", f"{RA}:literature.mu_eps.yuan_phantom3_azplane.mu_a")
    put(b1, "statistic_convention_trap", f"{RA}:literature.mu_eps._convention.stat_ambiguity")
    borrowed.append(b1)

    b2 = {"what": "금속구 교정 (calibration sphere)",
          "from": "Das 절차 + Zhang(JSAC 2026)의 0.5 m 금속구 잔차 검사",
          "where_in_our_repo": "benchmark/rcs_anchor.py sphere_calibration · benchmark/mie_pec_sphere.py",
          "what_it_bought": "우리 커널이 생산 3 밴드에서 정확 Mie 대비 몇 dB 인지가 표가 됐다."}
    put(b2, "our_r178mm_lte_dev_vs_mie_db",
        f"{RA}:sphere_calibration.LTE 1.843 GHz.spheres[1].dev_db_vs_mie")
    b2["prior_number_to_stand_beside"] = ("Zhang JSAC 2026: 0.5 m 구, 이론 −7.07 dBsm ↔ 실측 −8.96 dBsm "
                                          "(2 dBsm 이내). 우리는 시뮬 대 해석해라 같은 양이 아니다 — "
                                          "그들 것은 sim-to-real, 우리 것은 kernel-to-theory 다.")
    b2["prior_number_src"] = "doc: docs/INJECTION_PRECEDENT.md §3.2(2)"
    borrowed.append(b2)

    b3 = {"what": "정규화 RCS σ/(πr²) 축과 kr 유효성 바닥",
          "from": "SagittaSBR(arXiv:2604.09243) — 독립 SBR+PO 솔버, 우리 최근친",
          "where_in_our_repo": "benchmark/verify_sbr_kr_sweep.py (Sagitta 와 **같은 축**: 입사방향 "
                               "평균 후 kr 스윕)",
          "what_it_bought": "'우리가 몇 배 나쁘다' 는 옛 헤드라인이 애초에 다른 양이었음이 드러났고, "
                            "kr≥30 에서 우리 산포가 그들과 같은 급이라는 것이 인쇄됐다."}
    put(b3, "our_std_pct_vs_mie_kr_ge30", f"{KR}:summary_div16.std_sbr_over_mie_pct_kr_ge30")
    put(b3, "axis_note", f"{KR}:meta.axis_note")
    b3["prior_floor"] = "Sagitta: kr ≥ 30 에서 ~2%, 면 이산화 ds ≤ λ/5."
    b3["prior_floor_src"] = "doc: docs/HOW_OTHERS_SOLVED_IT.md §1 표"
    borrowed.append(b3)

    b4 = {"what": "모노스태틱에서 출사 가시성 함수를 생략해도 되는 근거",
          "from": "SagittaSBR 각주 1 (원문 인용이 src/rcs_sbr.py:538-542 주석에 그대로 실려 있다)",
          "where_in_our_repo": "src/rcs_sbr.py rcs_sbr_multistatic(exit_vis=…)",
          "what_it_bought": "바이스태틱에만 그림자광선을 1발 더 쏘는 설계의 근거. 모노에서 정확한 "
                            "no-op 임을 실측으로 확인했다."}
    put(b4, "exit_vis_note", f"{DF}:d4_exit_visibility.note")
    borrowed.append(b4)

    b5 = {"what": "표적 서명을 밖에서 만들어 경로에 곱하는 **주입 아키텍처**",
          "from": "IEEE TAP(Schuler 2008) → IET RSN(Deep 2020) 계보, 그리고 3GPP TR 38.901 7.9.2.1",
          "where_in_our_repo": "outputs/report13_sigma_grid.json → src/sionna_chain.py",
          "what_it_bought": "우리 구조가 '발명' 이 아니라 '표준 구조' 라는 것. 기여 문장은 표를 "
                            "만든다가 아니라 **두 번째 것**을 이름 붙여야 한다."}
    put(b5, "injection_instances_found", f"{IV}:counts.injection_instances_in_the_master_table")
    put(b5, "injection_peer_reviewed", f"{IV}:counts.peer_reviewed")
    put(b5, "injection_standards_documents", f"{IV}:counts.standards_documents")
    borrowed.append(b5)

    s["already_borrowed"] = borrowed

    # ── 주입 아키텍처의 게재 전례와 각각의 검증 방식 ────────────────────────────────────
    prec: dict = {
        "_what": "⭐ 우리 구조의 게재 전례 — 그리고 **각각이 인쇄한 검증 방식**. "
                 "이 표의 오른쪽 열이 우리가 넘어야 할 바다.",
        "_src": "docs/INJECTION_PRECEDENT.md §1.1 · outputs/injection_verdict.json",
        "rows": [
            {"venue": "IEEE TAP 56(11):3543-3551 (2008)", "who": "Schuler 외",
             "signature_source": "저자 자체 광선추적기(IHE Karlsruhe), 상용 full-wave 아님",
             "target": "Ford Focus, 삼각형 12,100",
             "validation": "2중 — EC JRC Ispra 무향실 바이스태틱 측정 + 축약모델↔원본 광선추적 자기일관성",
             "role": "기여(파이프라인 자체가 결과)",
             "why_it_matters_to_us": "⭐ 가장 강한 구조적 전례. 세 단계가 우리와 같은 순서다 — "
                                     "자체 광선솔버 → 자세색인 표 → 하류로 넘김."},
            {"venue": "IEEE JSAC 44:702-716 (2026)", "who": "Zhang 외",
             "signature_source": "무향실 측정(10/15/20/28/36 GHz)",
             "target": "AAV(M350급)·인체·차량",
             "validation": "⭐ 최강 — 0.5 m 금속구(이론 −7.07 ↔ 실측 −8.96 dBsm) **+ 28 GHz 밴드 held-out**",
             "role": "기여(RAN1 #120 규격 채택)",
             "why_it_matters_to_us": "우리는 구 교정 **절반만** 갖고 있다. held-out 밴드 시험이 없다."},
            {"venue": "IET Radar Sonar Navig. 14(6):833-844 (2020)", "who": "Deep 외",
             "signature_source": "저자 **자체 SBR 솔버** (\"developed our solver in-house\")",
             "target": "보행자 폴리메쉬(MoCap)",
             "validation": "엔드투엔드 — 77 GHz 실장비 대비 NMSE < 10%, SSIM > 81%",
             "role": "기여",
             "why_it_matters_to_us": "자체 SBR 로 표를 만든 두 번째 전례. 소비처가 자유공간 FMCW "
                                     "신호모델이라 전파채널이 없다는 점만 우리와 다르다."},
            {"venue": "IEEE TMTT 70(3):1582-1593 (2022)", "who": "Abadpour 외",
             "signature_source": "고분해능 측정", "target": "보행자·VRU",
             "validation": "표 자체가 측정", "role": "기여(분해능)",
             "why_it_matters_to_us": "TAP 과 함께 '표를 만드는 절반만으로' 게재된 사례."},
            {"venue": "IEEE TAES 61:151-161 (2025)", "who": "Potter 외",
             "signature_source": "무향실 측정(Semkin, IEEE Access 2020)",
             "target": "7 기체(F450·M100·P4P 등), 26–40 GHz × 방위 0–180° / 고도 1° 스텝",
             "validation": "표 자체가 측정", "role": "방법선택(기여는 베이지안 융합 분류)",
             "why_it_matters_to_us": "드론 σ 표를 자세 색인 + 이중선형보간으로 소비하는 형태의 전례."},
            {"venue": "IEEE J-STEAP 1 (2025)", "who": "Costa 외",
             "signature_source": "BiRa 바이스태틱 측정 라이브러리",
             "target": "다중프로펠러 드론(Phantom 2 급)",
             "validation": "⚠ **형상만** — Pearson r=0.98, [0,1] 정규화 신호 기준. 절대 레벨 미정착. "
                           "몸통 반사도 스칼라는 본문에 'manually adjusted' 라고 적혀 있다.",
             "role": "방법선택", "why_it_matters_to_us": "절대 레벨을 주장하지 않고 게재된 사례."},
            {"venue": "Digital Commun. & Networks 11(5):1601-1613 (2025)", "who": "Zhang 외",
             "signature_source": "⭐ 자체 PO 계산",
             "target": "RIS 패널(+금속판·인체·UAV·차량)",
             "validation": "계산 σ ↔ 실측 채널전력, 0.11~7 dB",
             "role": "기여", "why_it_matters_to_us": "PO 계산값을 실측 채널전력으로 검증한 유일 사례."},
            {"venue": "NATO STO-MP-MSG-SET-183 #13 (2021)", "who": "—",
             "signature_source": "QuickWave-3D FDTD(상용)", "target": "Parrot AR.Drone 2.0",
             "validation": "❌ 주장했으나 인용이 깨져 있다(ref[3] 이 솔버 자체)",
             "role": "방법선택", "why_it_matters_to_us": "상용 full-wave → 표 경로의 드문 사례이고, "
                                                          "검증이 확인되지 않는다."},
            {"venue": "arXiv:2607.03826 (LAMBDA, 프리프린트)", "who": "—",
             "signature_source": "CADFEKO(상용 full-wave)",
             "target": "UAV", "validation": "❌ 없음. 표의 축·각스텝·주파수·dBsm 값이 전부 미인쇄",
             "role": "방법선택",
             "why_it_matters_to_us": "⛔ **전례로 인용 금지**(docs/INJECTION_PRECEDENT.md §7). "
                                     "아키텍처 전례는 Schuler → Deep 순으로만 인용한다."},
        ],
    }
    prec["what_this_retracts"] = ("우리가 '아무도 주입 σ 를 검증하지 않았으니 검증이 우리의 열린 축이다' "
                                  "라고 적었던 것은 **철회됐다**. 심사통과 5편이 검증했고 둘은 지금 "
                                  "우리보다 강하다.")
    prec["what_this_retracts_src"] = "doc: docs/INJECTION_PRECEDENT.md §6 C2"
    s["injection_precedent_and_their_validation"] = prec

    # ── 아직 안 빌린 것 ───────────────────────────────────────────────────────────────
    s["not_yet_borrowed"] = [
        {"rank": 1, "what": "세 유효성 바닥을 기체 × 밴드 표로 인쇄",
         "from": "Sagitta(kr≥30 @2%, ds≤λ/5) · Monte-Carlo SBR(10 rays/λ) · "
                 "Ziganshin(면 규칙 E>1.5λ, E²/(Rλ) 0.6–0.9)",
         "cost": "반나절, 새 실행 0",
         "what_it_buys": "'전기적 소형' 이 고백에서 **표**가 된다. 우리 kr 스윕은 kr≥30 에서 이미 "
                         "그 자리에 앉아 있고 인쇄한 적이 없다. 동시에 mini5pro@LTE(kr 8.38)가 "
                         "모든 공개 바닥 아래라는 것을 우리가 먼저 말한다.",
         "src": "doc: docs/HOW_OTHERS_SOLVED_IT.md §2 채택 #1"},
        {"rank": 2, "what": "정준체(구·원통)를 우리 커널에 통과 + 캠페인 패드에 2.8 dBsm 원통",
         "from": "Das 절차(IEEE Std 1502-2020) + Zhang 잔차",
         "cost": "커널 1일 + 원통 가공비",
         "what_it_buys": "절대 σ 에 처음으로 **실측** 검사가 붙는다. 목표 불확실도 약 2 dB.",
         "src": "doc: docs/HOW_OTHERS_SOLVED_IT.md §2 채택 #2"},
        {"rank": 3, "what": "PTD-EEC 가산 모서리 항을 **진단으로**",
         "from": "Kirik & Özdemir 2019(SBR 에 PTD 를 꽂는 전체 알고리즘) + Öztürk 2002(유도·닫힌형, "
                 "E_tot = E_PTDEEC + E_PO)",
         "cost": "1–2주",
         "what_it_buys": "회절 결손과 상반성 위반을 **동시에** 건드리는 유일한 항목. Öztürk p.70 이 "
                         "PO 의 상반성 위반과 PTD 를 한 문장에 묶는다.",
         "our_prediction_recorded_in_advance": "주파수 무관한 edge 항 하나로는 3.5–8배 기울기 초과를 "
                                               "설명하지 못한다. 기울기가 앵커까지 평탄해지면 절대 "
                                               "레벨이 6–12 dB 튀어 절대레벨 검증과 정면충돌한다.",
         "src": "doc: docs/HOW_OTHERS_SOLVED_IT.md §3"},
        {"rank": 4, "what": "SBR 마이크로도플러에 회전 불변성 적용",
         "from": "jees2021(MoM) — 같은 연산에서 156.8× 를 쟀다",
         "cost": "며칠",
         "what_it_buys": "우리 해석 PO 는 이미 이 트릭(시선 역회전)을 쓰고 SBR 만 안 쓴다.",
         "src": "doc: docs/HOW_OTHERS_SOLVED_IT.md §2 채택 #4"},
        {"rank": 5, "what": "스칼라 γ_po 5개 → MECA 유전체 등가전류",
         "from": "Monte-Carlo SBR (UMD, arXiv:2511.07586)",
         "cost": "1주",
         "what_it_buys": "'우리 모델링 선택 5개' 가 '명시된 상수를 쓴 **표준 유전체 PO**' 가 된다. "
                         "값 문제는 남는다.",
         "src": "doc: docs/HOW_OTHERS_SOLVED_IT.md §2 채택 #5"},
        {"rank": 6, "what": "미분가능 재질 보정",
         "from": "Hoydis 외(IEEE TMLCN 2024) — 경사하강 보정 4.93 → 2.16 → 1.00 dB",
         "cost": "큼. 실측 캠페인이 먼저다",
         "what_it_buys": "이 효과를 잰 **유일한 공개 숫자**를 우리 재질표에 적용한다.",
         "src": "doc: docs/HOW_OTHERS_SOLVED_IT.md §2 채택 #6"},
        {"rank": 7, "what": "held-out 밴드 시험",
         "from": "Zhang JSAC 2026 — 두 밴드로 정착시키고 세 번째를 예측",
         "cost": "새 실행 1회",
         "what_it_buys": "JSAC 심사자가 실제로 적용한 바를 우리가 넘는지가 결정된다.",
         "src": "doc: docs/INJECTION_PRECEDENT.md §7"},
    ]

    # ── 빌리지 않기로 한 것 ───────────────────────────────────────────────────────────
    s["deliberately_not_borrowed"] = [
        {"what": "Ziganshin 의 UTD + vertex 회절 이식",
         "why_not": "보정이 아니라 **대체**다. 그의 파이프라인에는 표면적분이 아예 없다. 전부 PEC 라 "
                    "부품별 재질 서사를 통째로 버린다. 공개 코드는 TF 시대 Sionna 0.17 포크이고 "
                    "우리는 2.0.1 이다. 두 문서 어디에도 주파수 스윕이 없어 밴드 기울기 근거로 "
                    "인용할 수 없다.",
         "src": "doc: docs/HOW_OTHERS_SOLVED_IT.md §2"},
        {"what": "Sionna stock diffraction=True 를 표적에 켜기",
         "why_not": "이미 쓸 수 있고 **잘못된 도구**다. D 를 켜도 Sionna 는 경로계수를 내지 σ 를 내지 "
                    "않는다 — D 가 먹일 산란적분이 없다. 게다가 wedge 각을 인접 두 면의 법선에서 "
                    "읽으므로(utils/wedges.py) 면분할된 셸에서 그 각은 드론의 성질이 아니라 "
                    "**우리 메싱의 성질**이다.",
         "src": "doc: docs/HOW_OTHERS_SOLVED_IT.md §2"},
        {"what": "상용 CADFEKO 표를 사서 주입 (LAMBDA 방식)",
         "why_not": "회당 several hours 인 full-wave 로는 조밀한 표를 못 만든다(가설). 그리고 그 유일 "
                    "사례가 표의 축·각스텝·dBsm 을 하나도 인쇄하지 않았다.",
         "src": "doc: docs/INJECTION_PRECEDENT.md §4.2"},
    ]

    # ── 아무도 안 푼 것 ──────────────────────────────────────────────────────────────
    s["nobody_solved_these"] = [
        {"problem": "표적 재질의 측정 출처", "corpus_count": "140편 중 0편",
         "reading": "이 분야에서 가장 깊이 들어간 저자가 현실 재질을 future work 로 적었다. "
                    "우리 γ_po 5개는 md-rt 의 stock \"Wood\"(출처 0)나 Costa 의 손튜닝보다 근거가 "
                    "많고, jees2021 의 인용 붙은 PEC 근사보다 근거가 적다."},
        {"problem": "자기 커널 상반성 검사", "corpus_count": "213편 중 0편",
         "reading": "우리가 그 검사를 돌리고 숫자를 인쇄한 것은 우리 커널이 나쁘다는 뜻이 아니라, "
                    "다른 커널들은 같은 결함이 있어도 보이지 않는다는 뜻이다."},
        {"problem": "엔진 안에서 회전 로터를 표현", "corpus_count": "213 PDF 중 0편",
         "reading": "md-rt 는 회전 프로펠러를 실제로 추적했으나 **방법을 적지 않았다** — "
                    "존재증명이지 레시피가 아니다."},
    ]
    s["nobody_solved_these_src"] = "doc: docs/HOW_OTHERS_SOLVED_IT.md §1·§2"
    return s


# ================================================================================================
#  리포트 뼈대 — 빌더가 그대로 쓰는 인덱스
# ================================================================================================
def outline() -> dict:
    return {
        "_what": "리포트 00 빌더(src/make_report00_po_case.py, 미작성)가 num()/table_from() 으로 "
                 "찌를 자리. 이 편은 **가르치는 편**이라 다른 편보다 길어도 된다.",
        "tone": ["유도를 건너뛰지 않는다 — 기호를 처음 쓸 때마다 뜻을 적는다.",
                 "비유를 쓰되 **반드시** '이 비유가 어디서 깨지는가' 를 붙인다(s0.analogies_and_where_they_break).",
                 "Sionna 를 깎지 않는다 — s0.what_the_engine_does_exactly 가 먼저 나온다.",
                 "'무한평면 가정' 같은 거친 요약을 그대로 쓰지 않는다. 코드·원문에 실제로 있는 것을 인용한다.",
                 "본문·주석·print 는 한국어, 그림 안의 텍스트는 전부 영어."],
        "sections": [
            {"sec": "§0", "title": "Sionna 는 무엇을 하고 무엇을 안 하는가", "key": "s0_fair_boundary"},
            {"sec": "§1", "title": "표적 σ 를 얻는 다섯 갈래 — 비용과 정확도", "key": "s1_alternatives"},
            {"sec": "§2", "title": "우리 PO 커널을 수식으로 풀어 쓴다", "key": "s2_our_kernel"},
            {"sec": "§3", "title": "검증 3층", "key": "s3_validation"},
            {"sec": "§4", "title": "⚠ 한계", "key": "s4_limits"},
            {"sec": "§5", "title": "선행에서 빌린 것 / 빌릴 것", "key": "s5_prior_work"},
        ],
        "figure_candidates": [
            {"fig": 1, "question": "Does the ray-traced target path carry any RCS information?",
              "data": "s0_fair_boundary.engine_carries_no_sigma_experiment (plate σ span vs RT ratio)"},
            {"fig": 2, "question": "Where does the PO surface integral come from?",
              "data": "s2_our_kernel.derivation (다이어그램 — 투영면 격자 → 위상합)"},
            {"fig": 3, "question": "How close is the kernel to analytic PO, and PO to the truth?",
              "data": "s3_validation.layer1/layer2 (kr 사다리 2축)"},
            {"fig": 4, "question": "At which feature width does PO stop being usable?",
              "data": "s4_limits.po_validity_knee_a_over_lambda + feature_knee_frequencies"},
            {"fig": 5, "question": "How does one pose of our kernel cost against stock Sionna?",
              "data": "s1_alternatives.ours_runtime + stock_sionna_same_card + published_runtime_ladder"},
        ],
        "figure_text_rule": "그림 안의 모든 글자는 영어. report_style.assert_fig_text() 로 검사한다.",
    }


def main() -> None:
    doc = {
        "_meta": {
            "file": "outputs/report00_po_case.json",
            "title": "리포트 00 「왜 PO 인가 · 우리 PO 는 납득 가능한가 · 선행에서 무엇을 빌릴 수 있나」의 근거",
            "generated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "generator": "benchmark/build_report00_po_case.py",
            "run": "cd /home/yunjung/workspace/sionna2 && PYTHONPATH=src "
                   "~/.venvs/py312/bin/python benchmark/build_report00_po_case.py",
            "reads_only": True,
            "value_rule": "모든 스칼라 옆에 <이름>_src 가 붙는다. outputs/…:키 = 다른 산출물에서 "
                          "읽었다 · code: = 소스 상수 · computed: = 이 스크립트가 계산 · "
                          "doc: = 문서 문장(숫자 아님).",
            "house_rules": "본문·주석·print 는 한국어, 그림 안 텍스트는 전부 영어. "
                           "숫자는 손으로 치지 않는다(src/report_style.py num()).",
            "fairness_rule": "Sionna 를 부당하게 깎으면 그 자체가 결함이다. Fresnel 반사는 정확히 "
                             "계산되고, 1차 UTD 쐐기회절은 구현돼 있으며(설치본 기본값 off), "
                             "환경·클러터에서는 맞는 도구다. 틀린 것은 '전파용 도구에 표적 산란을 "
                             "시킨 것' 이다.",
            "do_not_cite": ["outputs/ptd_drone_effect.json — SUPERSEDED, 어떤 숫자도 인용 금지"],
        },
        "s0_fair_boundary": section0(),
        "s1_alternatives": section1(),
        "s2_our_kernel": section2(),
        "s3_validation": section3(),
        "s4_limits": section4(),
        "s5_prior_work": section5(),
        "report_outline": outline(),
    }
    doc["_provenance"] = {
        "n_fields_traced": len(LEDGER),
        "source_files": sorted({e["src"].split(":")[0] for e in LEDGER
                                if e["src"].startswith("outputs/")}),
        "ledger": LEDGER,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print(f"[report00] wrote {OUT}")
    print(f"[report00] 추적된 필드 {len(LEDGER)}개, 출처 산출물 "
          f"{len(doc['_provenance']['source_files'])}개")


if __name__ == "__main__":
    main()
