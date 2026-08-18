# -*- coding: utf-8 -*-
"""Assemble outputs/mesh_audit_0816_topology_physics.json from the audit passes."""
import json, os, subprocess, datetime
S = "/tmp/claude-0/-workspace/e9e31991-b542-4f3a-b8e2-570320d555ba/scratchpad"
L = lambda n: json.load(open(f"{S}/{n}.json"))
a1, a2, a3, a4 = L("a1_raw"), L("meshaudit_a2_slivers"), L("a3"), L("a4")
a5, a6, a7, a8 = L("a5"), L("a6"), L("a7"), L("a8")
a9c, a10, a11, a13 = L("a9c"), L("a10"), L("a11"), L("a13")
a14, a15 = L("a14"), L("a15")

now = subprocess.run(["date", "-d", "@" + str(int(datetime.datetime.now().timestamp())),
                      "+%Y-%m-%d %H:%M KST"], env={**os.environ, "TZ": "Asia/Seoul"},
                     capture_output=True, text=True).stdout.strip()

doc = {
  "_meta": {
    "title": "메쉬 위상·물리 타당성 감사 — 2026-08-16 적대적 라운드",
    "lens": "topology + physical plausibility (담당 렌즈)",
    "generated_kst": now,
    "engine_python": "/workspace/.venvs/py312/bin/python (trimesh 5.0.0)",
    "compute": "CPU only — GPU 금지 라운드",
    "scope_ko": "DRONES 레지스트리 10 기체 전수. 검사한 것: 닫힘(watertight)·법선 안팎·자기교차·"
                "퇴화/슬리버 삼각형·중복 정점·비다양체 모서리·부품 간 관통(전 그룹쌍)·"
                "좌표계/스케일·질량중심·부품 부피 대 실제 무게·프로펠러 형상 대 설계법칙/실측앵커.",
    "how_to_read_ko": "«확인됨»은 내가 직접 계산해 맞다고 확인한 것이다. «반증»은 내 자신의 중간 "
                      "결론이 틀렸다고 확인한 것이며 그대로 남겼다. 추측은 추측이라 적었다.",
    "raw_passes": {
      "a1_raw": "원시 위상(trimesh 정리 이전)", "a2": "이상점 국소화", "a3": "watertight 진실값",
      "a4": "구멍 출처 + 비다양체 정량", "a5": "전 그룹쌍 매몰면", "a6/a7": "캐노피 매몰 2법 교차검증",
      "a8": "스케일·질량·질량중심", "a9c/a10/a15": "프로펠러 형상", "a11/a13": "자기교차 + 사각지대 시연",
      "a14": "2026-07-01 수정 2건 회귀검사"}
  },

  "F01_meshcheck_reports_a_repaired_copy": {
    "severity": "치명",
    "claim_ko": "src/mesh_check.py 의 watertight 판정은 **출하되는 메쉬가 아니라 trimesh 가 방금 "
                "수리한 사본**을 본다. check_mesh() 55행 `tm.split(only_watertight=False)` 은 "
                "trimesh 5.0.0 에서 `repair=True` 가 기본이고, util.submesh 가 각 연결요소에 "
                "`fill_holes()` 를 **제자리로** 부른다.",
    "evidence": {
      "trimesh_source": "trimesh/graph.py split(only_watertight, repair=True) -> "
                        "mesh.submesh(..., repair=repair) -> "
                        "`watertight = [len(i.faces) >= 4 and i.fill_holes() for i in result]`",
      "live_case_mini2_body": {
        "mesh_check_says": a3["mini2"]["body"]["wt_meshcheck"],
        "truth_no_repair": a3["mini2"]["body"]["wt_honest"],
        "boundary_edges_in_shipped_mesh": a3["mini2"]["body"]["boundary_edges"],
        "trimesh_is_volume_as_shipped": a7["body_is_volume_as_shipped"]},
      "synthetic_proof": a11["blind_spot_demos"]["D5_single_triangle_hole"]},
    "impact_ko": "지금 전 기체 10/10 «통과» 는 **구멍 없음을 증명하지 않는다**. 실제로 mini2 body 는 "
                 "구멍이 뚫린 채 출하 중이고 검사는 통과로 보고한다. 검사기 자체가 회귀를 못 잡는다는 뜻이라 "
                 "다른 모든 통과 기록의 신뢰도가 함께 떨어진다.",
    "fix_ko": "check_mesh 의 split 호출에 `repair=False` 를 명시하고, 별도로 경계 모서리 수를 "
              "결과 dict 에 넣어 0 이 아니면 실패시킬 것."
  },

  "F02_mini2_body_has_a_hole": {
    "severity": "중요",
    "claim_ko": "mini2 의 body 그룹은 삼각형 1 장이 빠진 구멍이 있다. 출처는 cadkit.Assembly.add() 의 "
                "`m.update_faces(m.nondegenerate_faces())` — 면적 0 삼각형을 지우면서 껍질을 열었다.",
    "evidence": {
      "hole_triangle_vertices_mm": a4["mini2_body_hole"]["hole_tri_verts_mm"],
      "hole_area_mm2": a4["mini2_body_hole"]["hole_tri_area_mm2"],
      "boundary_edge_lengths_mm": [e["len_mm"] for e in a4["mini2_body_hole"]["boundary_edges"]],
      "smoking_gun_ko": "mini2 body 면 수 %d 는 **홀수**다. 같은 셸 경로의 다른 기체는 전부 짝수: %s"
                        % (a4["mini2_body_hole"]["body_face_count"],
                           a4["mini2_body_hole"]["face_counts_other_bodies"])},
    "impact_ko": {
      "rf_직접": "구멍 면적 4.96e-06 mm² = body 표면적 36298 mm² 의 1.4e-8 % — 산란 자체는 사실상 0.",
      "간접_이것이_진짜_피해": "구멍 때문에 `is_watertight=False` 라 **부피·contains() 가 무효**가 된다. "
                              "solid 내부판정을 쓰는 모든 검사가 이 부품을 조용히 건너뛴다. "
                              "mesh_check 자신의 check_prop_bell_solid 도 `if not c.is_watertight: continue` 로 건너뛴다. "
                              "내 캐노피 매몰 측정이 실제로 그 함정에 빠져 86.35 % 를 0.00 % 로 읽었다(F09 참조)."},
    "fix_ko": "구멍 난 삼각형은 슬리버였다. nondegenerate_faces() 로 지우지 말고 **정점을 병합해 붕괴**시키거나, "
              "지운 뒤 fill_holes() 로 다시 닫고 그 사실을 로그로 남길 것."
  },

  "F03_buried_faces_across_all_group_pairs_are_unchecked": {
    "severity": "중요",
    "claim_ko": "mesh_check 의 그룹 간 관통 검사는 **prop↔motor 단 한 쌍**만 본다. 나머지 모든 쌍은 "
                "아무도 안 본다. 전수 측정 결과 기체 표면적의 8.0~41.8 % 가 다른 부품 솔리드 **안에** 있다.",
    "evidence_pct_of_total_mesh_area": {k: v["buried_pct_of_mesh_area"] for k, v in a5.items()},
    "evidence_top_pairs": {k: dict(list(v["pairs"].items())[:3]) for k, v in a5.items()},
    "impact_ko": {
      "SBR(기본 엔진)": "대부분 **문제가 아니다** — first-hit 이 가림을 처리하고, battery/pcb 는 유전체 셸 "
                        "투과로 보는 것이 설계 의도다. 이 항목은 SBR 결과를 부정하지 않는다.",
      "PO(engine='po')": "가림이 없다(rcs_po.py 47행이 스스로 선언). 매몰면이 **전부 이중계상**된다. "
                         "mavic4pro 38.0 % · mini5pro 41.8 % 의 면적 과대. PO 를 비교/검증용으로 쓸 때 "
                         "이 편향이 그대로 들어간다.",
      "공통": "검사가 없다는 사실 자체가 결함이다 — 새 부품을 잘못 놓아도 아무 경고가 안 뜬다."},
    "declared_gap_ko": "drone_cad.py 193-195 행이 battery·pcb 가 union 목록에 없음을 이미 선언해 뒀다. "
                       "선언은 있으나 **검사는 없다**.",
    "fix_ko": "check_prop_bell_solid 를 일반화해 전 그룹쌍 매몰 면적을 재고, 기체별 예산표를 두라 "
              "(이미 prop↔motor 에 쓰는 방식 그대로)."
  },

  "F04_canopy_is_largely_or_entirely_buried": {
    "severity": "중요",
    "claim_ko": "셸형 7 기체 전부에서 canopy 그룹이 body 솔리드 안에 69~100 % 묻혀 있다. "
                "두 독립 방법(광선 contains, 부호거리)이 **면 단위로 100 % 일치**한다.",
    "evidence": {k: {"pct_area_inside_body_contains": v["pct_inside_contains"],
                     "pct_area_inside_body_signed_distance": v["pct_inside_signeddist"],
                     "methods_agree_faces": f"{v['agreement_faces']}/{v['n_faces']}",
                     "canopy_area_mm2": v["canopy_area_mm2"],
                     "canopy_top_mm": v["canopy_top_mm"], "body_top_mm": v["body_top_mm"]}
                 for k, v in a6.items()},
    "mini2_corrected": {"note_ko": "mini2 는 표에 0.00 % 로 찍히지만 그것은 F02 의 구멍 때문에 "
                                   "내 자신의 검사가 body 를 건너뛴 것이다. 구멍을 메우고 다시 재면 **86.35 %**.",
                        "value": a7["hole_patched"]["pct_canopy_area_inside"]},
    "declared_vs_undeclared_ko": {
      "선언됨": "phantom3(drone_cad.py 646-654행) · mini2(693-695행) — «이 기체엔 캐노피가 없는데 공용 경로가 "
                "항상 붙이므로 동체 안에 묻는다» 라고 명시.",
      "선언_안_됨": "mavic4pro(100.00 %) · phantom4(92.86 %) · mini5pro(85.13 %) · typhoonh480(74.66 %) · "
                    "matrice4e(69.19 %). 특히 **mavic4pro 는 100 % 이고 주력 표적**인데 근거 기록이 없다."},
    "impact_ko": {
      "SBR": "canopy 는 first-hit 이 될 수 없고(묻혀 있음), 동시에 투과 패스에서는 셸이라 씬에서 제외된다 "
             "(rcs_sbr.py 231행 exclude=_shells). 즉 **기여가 정확히 0** 이면서 메쉬 용량만 먹는다. "
             "mavic4pro 기준 2240 면 · 25659 mm² = 전체 면적의 7.8 % 가 죽은 무게다.",
      "PO": "가림이 없으므로 그 7.8 % 가 통째로 이중계상된다.",
      "재질": "canopy·body 둘 다 'plastic' 이라(drones.DRONE_GROUP_MAT) 재질 구분의 실익도 없다."},
    "falsified_hypothesis_ko": "⭐내 가설 반증: «묻힌 캐노피 때문에 투과 τ 가 두 번 곱해질 것» 이라고 의심했으나 "
                               "**틀렸다**. rcs_sbr 는 first-hit 셸 하나로 τ 를 정하고(326-333행) 내부 패스에서 "
                               "셸 그룹을 전부 제외하므로 τ 는 한 번만 적용된다. 기록으로 남긴다."
  },

  "F05_prop_thickness_is_one_scalar_but_the_fleet_spans_4x": {
    "severity": "중요",
    "claim_ko": "프롭이 표적 신호를 지배한다(2026-08-16 재질 판정). 그런데 재질 모형의 프롭 슬래브 두께는 "
                "**스칼라 하나**인데, 메쉬가 말하는 실제 블레이드 두께는 기체마다 4.3 배 벌어진다.",
    "evidence_chord_mean_thickness_mm": {k: v["span_mean_of_chordmean_mm"] for k, v in a15.items()},
    "canonical_check_ko": "material_verdict_0816.json 의 정본 «matrice4e 시위평균 1.43 mm» 는 메쉬에서 "
                          "재현된다 — 내 측정 1.484 mm(+3.8 %). 정의는 «시위평균 두께의 스팬 평균» 이 맞다. "
                          "⇒ 정본 자체는 **확인됨**.",
    "the_problem_ko": "그 1.43 mm 는 matrice4e 값이다. 실측 표적이 Mini 5 Pro 로 옮겨가는데(메모리: "
                      "실측 Matrice 4E→Mini 5 Pro) mini5pro 의 시위평균은 **0.833 mm** 로 1.72 배 얇다. "
                      "mini2 는 0.664 mm, m350rtk 는 2.879 mm.",
    "impact_db": {
      "source": "material_verdict_0816.json slab_predictions_3p5ghz.abs (45° 열)",
      "0.75mm": -18.21, "0.9mm": -16.65, "1.43mm": -12.71,
      "mini5pro_0.833mm_interpolated_db": -17.4,
      "delta_if_matrice4e_canonical_applied_to_mini5pro_db": 4.7,
      "note_ko": "0.75↔0.9 mm 사이 선형보간(추정). matrice4e 정본 1.43 mm 를 mini5pro 에 그대로 쓰면 "
                 "프롭 에코를 약 **4.7 dB 밝게** 본다. 실측 표적이 바뀌는 시점이라 지금 중요하다."},
    "fix_ko": "프롭 슬래브 두께를 기체별로 메쉬에서 뽑아 쓰라(계산법은 이 감사에 있다: 원통단면 → "
              "볼록껍질 최대캘리퍼 시위선 → 시위좌표계 상하면 차 → 시위평균 → 스팬평균)."
  },

  "F06_realized_prop_thickness_and_camber_exceed_the_design_parameters": {
    "severity": "사소",
    "claim_ko": "drone_cad.py 의 TC_ROOT/TC_TIP(9.5 %/6.5 %)·CAMBER_M(5.0 %)은 NACA **파라미터**이지 "
                "만들어진 형상의 **실측값**이 아니다. 참조 프롭을 잰 그 잣대로 우리 메쉬를 다시 재면 "
                "t/c 6.3~11.5 % · 캠버 6.4~7.3 % 가 나온다.",
    "method_ko": "benchmark/measure_reference_props.py 의 _blade_cluster/_section_metrics 를 **그대로 import** 해 "
                 "우리 메쉬에 적용했다(사과 대 사과).",
    "evidence": {k: {"t_over_c_min": v["t_over_c_min"], "t_over_c_max": v["t_over_c_max"],
                     "camber_over_c_max": v["camber_over_c_max"],
                     "chord_max_over_R": v["chord_max_over_R"],
                     "twist_max_deg": v["twist_max_deg"]} for k, v in a10["ours"].items()},
    "design_parameters": {"TC_ROOT": 0.095, "TC_TIP": 0.065, "CAMBER_M": 0.05,
                          "CHORD_MAX_OVER_R": 0.25},
    "reference_bands": a10["reference_bands"],
    "reading_ko": {
      "두께": "실현 t/c 최대 11.3~11.5 % 는 설정한 TC_ROOT 9.5 % 보다 **+19~21 %** 높다. 원인은 캠버 — "
              "캠버가 있는 익형은 시위좌표계 상하면 차가 NACA t 파라미터보다 커진다. "
              "그 결과 소비자용 참조 두 개(1345 최대 9.3 % · Solo 최대 8.2 %)보다 여전히 두껍다. "
              "drone_cad.py 96-98행이 «옛 값 9.2~13.5 % 는 참조 셋 중 어느 것보다 두꺼웠다» 며 고친 바로 그 축인데, "
              "**실현 형상은 아직 두 소비자기 위에 있다**(Typhoon 밴드 8.6~12.8 % 안에는 든다).",
      "캠버": "실현 6.4~7.3 % 는 설정한 5.0 % 보다 +29~46 %. 다만 참조 3종의 평균(6.50 %)에 가깝고 "
              "캠버 피크 위치 x/c=0.50 은 참조 0.49/0.52/0.51 과 일치한다 — **결과적으로는 타당한 자리**.",
      "시위": "chord_max/R 0.244~0.247 대 설정 0.250 (−1.3~−2.4 %). 스윕디스크 정규화의 부산물, 무해.",
      "트위스트": "13.3~24.2°, 참조 17.2/20.2/29.6° 밴드 안. **확인됨**."},
    "impact_ko": "얇은 판의 σ 는 면적 지배라 두께 자체의 σ 영향은 작다. 진짜 영향은 F05 경로 — 재질 슬래브 "
                 "두께를 메쉬에서 뽑을 때 **어느 정의로 뽑느냐**가 dB 를 만든다. 정의를 문서에 박아야 한다.",
    "caveat_ko": "이것이 «버그» 라고는 말하지 않는다. 파라미터와 실현값이 다르다는 사실이 어디에도 안 적혀 있다는 것이 문제다."
  },

  "F07_degenerate_face_threshold_is_absolute_and_catches_nothing": {
    "severity": "사소",
    "claim_ko": "mesh_check 의 퇴화면 잣대는 `area_faces < 1e-14` (m², 절대값)다. 전 기체에서 이 잣대에 "
                "걸리는 면은 **0 개**다. 그런데 상대 잣대로 보면 슬리버가 기체마다 49~142 개 있다.",
    "evidence": {
      "faces_below_1e14_m2": {k: v["faces_A_lt_1e14"] for k, v in a1.items()},
      "faces_with_min_angle_below_0p1deg": {k: v["total"] for k, v in a2["slivers"].items()},
      "sliver_area_fraction_of_mesh_pct": {k: v["area_frac_of_mesh_pct"] for k, v in a2["slivers"].items()},
      "smallest_interior_angle_deg": {k: v["min_angle_deg"] for k, v in a1.items()},
      "faces_with_aspect_ratio_over_100": {k: v["faces_aspect_gt_100"] for k, v in a1.items()},
      "groups_holding_slivers": {k: list(v["by_group"].keys()) for k, v in a2["slivers"].items()},
      "synthetic_proof": a11["blind_spot_demos"]["D2_sliver_triangles"]},
    "impact_ko": "슬리버가 차지하는 면적은 전체의 0.0001~0.03 % 라 **σ 자체에는 무해하다(확인됨)**. "
                 "문제는 법선이다 — 슬리버의 법선은 수치적으로 불안정한데 PO/SBR 의 조명판정이 n̂·û>0 이라 "
                 "부호가 흔들릴 수 있다. 다만 **흔들린다는 것을 이번에 측정하지는 않았다(추측)**. "
                 "그리고 이 슬리버들이 F02 의 구멍을 만든 그 삼각형들과 같은 부류다.",
    "fix_ko": "잣대를 상대값으로 바꿀 것 — 최소 내각(예: <0.5°)이나 종횡비(>100). 절대 면적은 기체 크기에 따라 뜻이 달라진다."
  },

  "F08_the_regression_gate_is_documented_as_running_but_is_not_wired": {
    "severity": "중요",
    "claim_ko": "`mesh_check.assert_ok()` 를 **호출하는 코드가 저장소에 하나도 없다**. 그런데 리포트는 "
                "그것이 상시 작동한다고 적는다.",
    "evidence": {
      "grep_ko": "repo 전체에서 assert_ok 는 정의(src/mesh_check.py:237)와 문자열 언급만 나온다. 호출부 0.",
      "claims_that_are_false": [
        "src/viz_report1.py:605 — \"assert_ok() runs inside the build pipeline as a hard gate: "
        "a mesh that fails any check cannot ship into the RCS/render stages.\"",
        "report_mesh/mesh07_verify_geometry.ipynb — \"부호부피 회귀 장치 `assert_ok` 상시 가동\"",
        "report_mesh/src/make_mesh07.py:242 — \"부피가 음수면 mesh_check.assert_ok() 가 예외를 던져 "
        "**빌드 자체가 실패**한다\""],
      "true_statement_ko": "src/mesh_check.py 22행 자신은 정직하다 — «assert_ok() 를 빌드 파이프라인에서 "
                           "**부르면** 회귀를 막는다»(조건문). 리포트가 그 조건을 사실로 바꿔 적었다."},
    "impact_ko": "회귀 방지 장치가 없다. F01 과 겹쳐 읽으면 더 나쁘다 — 있었어도 수리된 사본을 봤을 것이다.",
    "fix_ko": "build 파이프라인(예: build_drone 캐시 채우는 자리)에서 실제로 부르고, 리포트 문구는 "
              "현재 상태에 맞게 고칠 것."
  },

  "F09_my_own_intermediate_result_was_wrong_recorded_here": {
    "severity": "무해(확인됨)",
    "claim_ko": "⭐정직성 기록 — 이 라운드에서 내가 낸 중간 결론 중 **둘이 반증**됐다. 그대로 남긴다.",
    "refuted": [
      {"내_주장": "mini2 캐노피는 body 밖에 있다(매몰 0.00 %) — 코드 주석(«완전히 묻히도록»)과 모순된다.",
       "반증": "내 검사가 `is_watertight` 인 부품만 골랐는데 mini2 body 는 F02 의 구멍 때문에 탈락했다. "
               "구멍을 메우고 다시 재니 **86.35 %** — 코드 주석이 맞고 내가 틀렸다.",
       "교훈_ko": "수밀 필터를 건 검사는 «깨끗함» 이 아니라 «못 봄» 을 0 으로 보고할 수 있다."},
      {"내_주장": "전 기체에 자기교차 면쌍이 1504~2747 개 있다.",
       "반증": "내 Möller 구간겹침 구현이 **양성 대조를 통과하지 못했다**(교차하는 삼각형 쌍을 0 으로 보고). "
               "모서리-삼각형 관통(Möller–Trumbore) 방식으로 바꿔 양성·음성 대조를 모두 통과시킨 뒤 다시 재니 "
               "**전 기체 0 개**. 앞의 수치는 내 거짓양성이었다.",
       "교훈_ko": "검사기를 만들면 양성 대조부터 통과시킬 것. 음성 대조만으로는 «0 이 나오는 고장» 을 못 잡는다."}]
  },

  "F10_no_self_intersections_anywhere_confirmed": {
    "severity": "무해(확인됨)",
    "claim_ko": "검증된 검사기로 전 기체·전 그룹·전 연결요소를 재니 자기교차 면쌍 **0**.",
    "method_ko": "AABB 광역탐색 → 인접(정점 공유) 쌍 제외 → 모서리-삼각형 관통 Möller–Trumbore 양방향.",
    "controls_ko": "양성 대조 4 종(교차 삼각형·관통 삼각형·회전 상자쌍 18 hits·구쌍 84 hits) 통과, "
                   "음성 대조 5 종(구·상자·원통·먼 삼각형·위 삼각형) 전부 0.",
    "result": {k: v["total_pairs"] for k, v in a13.items()},
    "limitation_ko": "이 방식은 **완전 동일평면 겹침**은 못 본다(모서리가 상대 삼각형을 «관통» 하지 않으므로). "
                     "그 부류는 F11 에서 따로 잡았다.",
    "reading_ko": "cadkit.Assembly 의 정리 파이프라인(퇴화면 제거 → 정점 병합 → fix_normals)과 "
                  "manifold 불리언 union 이 실제로 잘 돌고 있다는 뜻이다. **확인됨.**"
  },

  "F11_x500v2_accent_and_arm_share_surfaces_and_interpenetrate": {
    "severity": "사소",
    "claim_ko": "x500v2 에서 accent 와 arm 이 정점 96 개를 **정확히 공유**하고(비트 동일), 웰딩하면 "
                "비다양체 모서리 172 개가 생긴다. 면적으로는 accent 의 10.7 % 가 arm 솔리드 안에, "
                "6.1 % 가 arm 표면 위(1 µm 이내)에 있다.",
    "evidence": {**a4["x500v2_accent_vs_arm"],
                 "dup_vertex_group_signature": a4["x500v2_dup_vertex_group_pairs"],
                 "nonmanifold_edges_after_1um_weld": a2["x500v2"]["nonmanifold"]["n"],
                 "nonmanifold_edge_groups": a2["x500v2"]["nonmanifold"]["groups"]},
    "impact_ko": "표면 위 동일평면 5408 mm² 는 **z-fighting 후보**다 — 광선이 어느 면을 먼저 맞을지가 "
                 "부동소수 반올림으로 갈린다. 두 그룹의 재질이 다르면(accent=plastic, arm=carbon, "
                 "|Γ| 0.28 ↔ 0.90) 같은 자리에서 **재질이 뒤집힐 수 있다**. "
                 "다만 이번에 σ 로 얼마인지는 재지 않았다(추측: 면적 비중 1.2 %라 크지 않을 것).",
    "fix_ko": "accent 를 arm 과 함께 불리언 union 하거나, 최소한 두 표면을 0.1 mm 이상 띄울 것."
  },

  "F12_mass_from_the_mesh_is_2_to_5_times_the_published_weight": {
    "severity": "중요",
    "claim_ko": "부품 부피 × gazebo_export.DENSITY 로 낸 총질량이 공표 이륙중량의 **1.10~5.18 배**다. "
                "동체(body) 하나가 기체 전체 무게를 넘는 기체가 6 종이다.",
    "evidence": {k: {"weight_spec_g": v["weight_spec_g"], "mass_from_mesh_g": v["mass_from_mesh_g"],
                     "err_pct": v["mass_err_pct"], "heaviest_group": list(v["per_group"])[0],
                     "heaviest_group_mass_g": list(v["per_group"].values())[0]["mass_g"]}
                 for k, v in a8.items()},
    "root_cause_ko": "메쉬의 body 는 **속이 꽉 찬 솔리드**인데 DENSITY['body']=1150 은 ABS **벌크** 밀도다. "
                     "실물 셸은 벽 두께 1 mm 안팎의 빈 껍데기다. DENSITY 주석은 «속이 빈 껍데기라 실효 밀도는 낮다» 고 "
                     "적어 놓고 정작 벌크 값을 쓴다 — 주석과 값이 어긋난다.",
    "impact_ko": {
      "RF": "**없다** — PO/SBR 은 표면만 본다. σ 축은 이 항목의 영향을 받지 않는다(확인됨).",
      "비행동역학": "gazebo_export 는 총질량을 공표 TOW 로 정규화하므로 절대질량은 맞는다. 그러나 "
                    "**질량 배분과 관성텐서는 틀린 채로 남는다** — body 가 40~54 % 를 가져가는데 실물 셸은 "
                    "그보다 훨씬 가볍다. 관성이 틀리면 자세 응답이 틀리고, 그것이 **로터 회전수 요동**으로 내려온다. "
                    "이번 라운드의 다른 축(비행로그 기반 rpm 모델링)과 직접 맞닿는 지점이다.",
      "declared_ko": "DENSITY 77-79행이 열린프레임 arm 이 솔리드 튜브라 4.3 배 과대라고 선언해 뒀다. "
                     "**셸 기체 body 에는 같은 선언이 없다** — 훨씬 큰 오차인데."},
    "center_of_mass_mm": {k: v["com_mm"] for k, v in a8.items()},
    "com_reading_ko": "typhoonh480 의 질량중심이 z −103.8 mm 로 암 평면보다 10 cm 아래다(카메라 2313 g + "
                      "착륙장치 배분 탓). 실물은 배터리가 동체 안이라 이렇게까지 낮지 않다 — 배분 왜곡의 증상.",
    "fix_ko": "body/canopy 를 실효 밀도로 낮추거나(벽두께 1 mm 등가), 셸을 껍데기로 모델링할 것. "
              "적어도 arm 처럼 **선언**은 해 둘 것."
  },

  "F13_scale_and_frame_conformance_confirmed": {
    "severity": "무해(확인됨)",
    "claim_ko": "좌표계·치수는 깨끗하다. z-up, 단위 m, 로터 대각과 프롭 스윕 지름이 스펙과 맞는다.",
    "evidence": {k: {"diag_spec_mm": v["diag_spec_mm"], "diag_mesh_mm": v["diag_mesh_mm"],
                     "diag_err_pct": v["diag_err_pct"]} for k, v in a8.items()},
    "prop_swept_diameter": {k: {"R_spec_mm": v["R_spec_mm"], "R_mesh_mm": v["R_mesh_mm"],
                                "err_pct": v["R_err_pct"]} for k, v in a9c.items()},
    "reading_ko": "로터 대각 오차는 mini5pro −9.72 % 를 빼면 −0.14~+1.98 %. mini5pro 는 스펙 note 가 "
                  "«diagonal_mm 275 는 로터 위치를 정하지 않는다, 실제 휠베이스는 248.3» 이라고 **이미 선언**한 "
                  "그 값이므로 결함이 아니다(확인됨). 프롭 스윕 지름은 전 기체 −0.000 % — "
                  "build_propeller_cad 의 스윕디스크 정규화가 정확히 작동한다.",
    "blind_spot_ko": "다만 mesh_check 에는 치수 검사가 **없다**. 단위를 1000 배 틀려도 통과한다(F14 D3)."
  },

  "F14_meshes_that_mesh_check_passes_but_are_wrong": {
    "severity": "중요",
    "claim_ko": "요청대로 «검사를 통과하는 나쁜 메쉬» 를 5 종 만들어 시험했다. **5/5 전부 통과**했다.",
    "demos": a11["blind_spot_demos"],
    "summary_ko": [
      "D1 두 상자가 80 % 겹쳐도 통과 — 그룹 **안**의 부품 간 겹침은 아무도 안 본다(union_group 이 "
      "실패해도 `except: pass` 로 조용히 넘어가므로 실제로 일어날 수 있다).",
      "D2 슬리버 삼각형 다발 통과 — 절대 면적 잣대 1e-14 m² 를 넘기 때문(F07).",
      "D3 단위를 1000 배 틀린 메쉬 통과 — 치수·좌표계 검사가 없다(F13).",
      "D4 좌우를 뒤집은(거울상) 기체 통과 — 프롭 회전방향·피치 부호가 물리적으로 반대인데 위상은 멀쩡하다.",
      "D5 삼각형 1 장 구멍 통과 — fill_holes 가 수리한 사본을 보기 때문(F01, mini2 실사례)."],
    "silent_failure_ko": "⚠ cadkit.Assembly.union_group() 은 `except Exception: pass` 다(81-82행). "
                         "불리언 union 이 실패하면 겹친 내부 면이 그대로 남는데 **예외도 로그도 없다**. "
                         "지금은 전 기체에서 union 이 성공하고 있다(prop 4 부품/4 로터 확인) — 즉 현재 결함은 아니고 "
                         "**미래의 조용한 실패 통로**다."
  },

  "F15_uv_sphere_pole_fix_held_but_leaves_duplicate_vertices": {
    "severity": "사소",
    "claim_ko": "2026-07-01 의 uv_sphere 극점 수정은 **유효하다** — 실제로 쓰이는 모든 테셀레이션에서 "
                "면적 0 삼각형 0 개. 다만 극점 정점이 seg 개씩 겹쳐 있어 중복 정점 178~358 개가 남고, "
                "인덱스 기준으로는 수밀이 아니다.",
    "evidence": a14["fix2_uv_sphere_poles"],
    "impact_ko": "PO 는 면 중심·법선·면적만 쓰고 Mitsuba 는 삼각형 수프를 받으므로 **RF 영향은 없다(확인됨)**. "
                 "다만 내보낸 OBJ 는 유효한 솔리드가 아니고, mesh_check 는 process=True 로 웰딩해 보므로 "
                 "이 사실을 영원히 보고하지 않는다. 구 부피는 해석값 대비 −0.051 %(seg180/rings90, 검증용) · "
                 "−4.416 %(모듈 기본 seg18/rings10) 다.",
    "note_ko": "src/geom.py 328행의 자체점검이 존재하지 않는 `blade()` 를 불러 **`python src/geom.py` 는 "
               "NameError 로 죽는다**. 무해하지만 죽은 코드다."
  },

  "F16_prop_normals_fix_held": {
    "severity": "무해(확인됨)",
    "claim_ko": "2026-07-01 의 prop_blade 안쪽 법선 수정은 **살아 있다**. trimesh 수리를 전혀 거치지 않고 "
                "출하 인덱스 목록에서 손으로 부호부피를 계산해 확인했다.",
    "evidence": a14["fix1_prop_normals_outward"],
    "all_groups_check": {"inward_or_zero_volume_components": a14["all_groups_inward_or_zero_volume"],
                         "reading_ko": "전 기체·전 그룹·전 부품에서 부호부피가 양수. 뒤집힌 부품 0."}
  },

  "F17_facet_size_versus_wavelength_on_the_prop": {
    "severity": "사소",
    "claim_ko": "프롭 삼각형의 최장 모서리가 λ(3.5 GHz, 85.7 mm) 대비 기체마다 크게 다르다 — "
                "mini2 λ/16.9 부터 m350rtk λ/3.8 까지.",
    "evidence": {k: {"max_edge_mm": None} for k in []},
    "numbers": "mini5pro λ/13.2 · mavic4pro λ/7.5 · matrice4e λ/7.4 · s1000plus λ/5.3 · phantom4 λ/8.4 · "
               "typhoonh480 λ/8.8 · x500v2 λ/7.9 · phantom3 λ/8.4 · m350rtk λ/3.8 · mini2 λ/16.9",
    "impact_ko": "PO 면적분은 삼각형 **안에서 위상을 상수로** 본다. 모서리가 λ/4 를 넘으면 그 근사가 깨진다. "
                 "지금은 최악이 λ/3.8(m350rtk)이라 **아직 λ/4 아래이긴 하다**. 다만 «전 기체 같은 면 수(12752)» 로 "
                 "고정돼 있어 큰 기체일수록 성기다 — 면 수가 아니라 **모서리 길이를 λ 로 묶는 것**이 맞다. "
                 "얼마나 틀리는지는 이번에 재지 않았다(추측).",
    "note_ko": "SBR 은 광선 간격이 λ/12 라 이 문제에서 자유롭다. 이 항목은 PO 경로에만 해당한다."
  },

  "_summary": {
    "checked_ok_ko": [
      "법선 방향 — 전 기체·전 그룹·전 부품 바깥(수리 없이 손계산). 2026-07-01 수정 유지.",
      "자기교차 — 검증된 검사기로 0 (양성·음성 대조 통과).",
      "비다양체 모서리 — x500v2 accent/arm 172 개 외에는 0.",
      "중복 정점 — 원시 메쉬에서 0~96 개, 전부 설명됨.",
      "좌표계·단위·로터 대각·프롭 스윕 지름 — 스펙과 일치.",
      "프롭 시위·트위스트 — 설계법칙 및 참조 프롭 밴드와 일치.",
      "프롭 두께 정본(matrice4e 1.43 mm) — 메쉬에서 재현됨(1.484, +3.8 %).",
      "uv_sphere 퇴화 극점 — 수정 유지(면적 0 삼각형 0 개)."],
    "must_fix_first_ko": [
      "F01 mesh_check 가 수리된 사본을 검사한다 (split repair=False) — 이걸 안 고치면 나머지 검사가 다 무의미하다.",
      "F08 assert_ok 를 실제로 배선하고 리포트의 거짓 문구를 고칠 것.",
      "F02 mini2 body 구멍 — F01 을 고치면 자동으로 드러난다.",
      "F05 프롭 슬래브 두께를 기체별로 뽑을 것 (실측 표적이 Mini 5 Pro 로 바뀌는 시점, ~4.7 dB)."],
    "not_touched_ko": "⛔ 지시대로 src/rotor_dynamics.py PRESETS 와 메쉬 생성 코드는 **읽기만** 했다. "
                      "이 문서는 발견과 권고까지다. git 작업 없음."
  }
}
p = "/workspace/sionna/outputs/mesh_audit_0816_topology_physics.json"
json.dump(doc, open(p, "w"), indent=1, ensure_ascii=False)
print("wrote", p, os.path.getsize(p), "bytes")
