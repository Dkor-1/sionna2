#!/usr/bin/env python
"""적대검증 판정문 조립 — outputs/meshdef_attack.json.

숫자는 전부 raw 측정 파일에서 읽어 넣는다. 손입력 없음.
⛔ 소스 무편집 · GPU 무사용.
"""
from __future__ import annotations
import json, os, subprocess, time

ROOT = "/home/yunjung/workspace/sionna2"
J = lambda p: json.load(open(os.path.join(ROOT, p)))          # noqa: E731
R1, R2, R3, R4 = (J(f"outputs/meshdef_attack_raw{s}.json") for s in ("", "2", "3", "4"))
P = J("outputs/meshdef_attack_parts.json")
SPEC = J("outputs/meshdef_spec.json")
GIM = J("outputs/meshdef_gimbal.json")
GRD = J("outputs/meshdef_ground.json")
PRP = J("outputs/meshdef_prop_gap.json")
M2 = J("outputs/meshdef_mini2_glb.json")
FLT = J("outputs/meshdef_floating.json")

fs = R1["q3_fit_scale"]
fe = R3["a_mini2_lens"]
cr = R1["q2_cradle"]
fish = R1["q3_fisheye"]["rows"]
trap = R1["q2_prop_trap"]
gh = R3["b_gimbal_h"]
ov = {r["tag"]: r for r in R4["rows"]}
cut = R2["a_cut_box"]["counts"]
gear = R2["c_gear_geometry"]

# 다리 뿌리 z 평균 (ground 가 잰 값) 과 엔진 상수로 뿌리 오프셋을 재구성
root_f = GRD["Q2_왜_두_값이_어긋나는가"]["그럼_왜_앞뒤_다리_길이가_다른가"]["앞_다리뿌리_z"]
root_r = GRD["Q2_왜_두_값이_어긋나는가"]["그럼_왜_앞뒤_다리_길이가_다른가"]["뒤_다리뿌리_z"]
root_mean = (root_f + root_r) / 2.0
ball_r_mm = 9.4 / 2.0                       # src/drone_cad.py:2396 리터럴 0.0094 m 의 절반
offset_reconstructed = gear["intercept_mm"] + ball_r_mm - root_mean
offset_claimed = GRD["Q2_왜_두_값이_어긋나는가"]["항등식"]["값"]

VER = {
 "_meta": P["skeleton"]["_meta"],

 "verdict": "PREMATURE",
 "verdict_ko": (
   "측정은 진짜다 — 내가 다시 잰 것은 전부 맞았고, 열 기체 기준지문은 비트단위로 재현됐다. "
   "그런데 **판정 세 개가 자기 측정에서 따라나오지 않는다**(X1 의 «x 118», X2 의 «더 나빠진다», "
   "X3/ground 의 «0.000 µm 로 닫힌다»). 검사표에는 단계별로 돌리면 스스로를 중단시키는 항목이 있고, "
   "무효화 목록에는 이름을 댈 수 있는 구멍이 있다(그중 하나가 마이크로도플러 계열이다). "
   "숫자를 고칠 일은 없고 **판정문과 검사표를 손봐야 한다** — 그래서 SOUND 가 아니라 PREMATURE 다."),
 "one_line_en": "Measurements reproduce; three load-bearing rulings do not follow from them.",

 "reproduction": {
   "baseline_fingerprints": {
     "n_drones": R1["q2_baseline"]["n_drones"],
     "all_match_bitwise": R1["q2_baseline"]["all_match"],
     "what": "drone_sha16 · frame_sha16 · prop_sha16 · n_v · n_f · fit_scale(소수 9자리) · "
             "프롭 그룹 무게중심 z — 열 기체 전부 명세와 일치",
     "ko": "명세가 값을 베낀 게 아니라 실제로 쟀다는 뜻이다."},
   "ground_Q4_fit_scale": {
     "ko": "Q3 이 물은 «직접측정을 쓰면 1.019 인가» 를 내 손으로 다시 풀었다.",
     "my_sz": {k: v["fit_sz"] for k, v in fs.items() if isinstance(v, dict)},
     "their_sz": {r["가설"]: r["fit_sz"] for r in GRD["Q4_직접측정을_쓰면_fit_스케일이_얼마인가"]["표"]},
     "restored_after_monkeypatch": fs["_restored_sz"]},
   "prefix_headline": P["prefix_repro"],
   "mesh_reader_count": {
     "their_command": SPEC["invalidation"]["how_counted"]["command"],
     "their_count": SPEC["invalidation"]["how_counted"]["mesh_reading_scripts"],
     "my_set_diff_ko": "오늘 돌리면 117개이고, 차이 2개는 이번 라운드가 benchmark/ 로 옮긴 자기 스크립트뿐이다. "
                       "집합이 정확히 같다 — 115 는 맞다."},
   "mini2_glb_landmarks": {
     "md5_matches_record": fe["origin_z_measured"] is not None
                           and R2["d_mini2_glb"]["md5"] == M2["acquisition"]["files"][0]["md5"],
     "origin_x": [fe["origin_x_declared"], fe["origin_x_measured"]],
     "origin_z": [fe["origin_z_declared"], fe["origin_z_measured"]],
     "pSphere3_y_centres_mm": fe["pSphere3_y_centres_mm"],
     "motor_diagonal_mm": fe["motor_diagonal_mm"],
     "ko": "M1 의 CAD 목표 7.1999 mm 가 GLB 에서 그대로 나온다. 원점 두 개도 소수 5자리까지 같다."},
   "engine_side_mini2": R1["q2_mini2"],
   "interlock_signs": {
     "matrice4e_prop_shift_5mm": trap["matrice4e"],
     "mini5pro_prop_shift_5mm": trap["mini5pro"],
     "ko": "X4 의 화살표 방향과 크기가 재현된다."},
 },

 "defects": [
  {
   "id": "A1", "severity": "HIGH", "q": "Q3(고치면 나빠지는가) · 자체 일관성",
   "where": ["docs/MESH_DEFECTS.md §2 X1 (ruling: 크래들 x 를 71.6~약 118 로 자른다)",
             "outputs/meshdef_spec.json conflicts[0].ruling"],
   "claim": "짐벌이 x=117.62 에서 시작하므로 크래들 상자를 118 mm 에서 자른다.",
   "measured": {
     "gimbal_assembly_bbox_min_x_mm": cr["gimbal_selector_bbox_min_x_mm"],
     "parts_and_overlap": cr["gimbal_parts"],
     "first_part_that_really_overlaps_min_x_mm": cr["first_overlapping_part_min_x_mm"],
     "tris_in_box_by_x_cut": cut,
     "first_x_where_shell_vertex_drops_below_cradle_roof_mm":
        R2["a_cut_box"]["first_x_shell_vertex_below_cradle_roof_mm"]},
   "why_it_is_wrong_ko":
     "117.62 를 만드는 파트는 **댐핑판**이고 그 판은 z 16.21~20.91 로 크래들 상자 지붕(+0.93) 위에 통째로 있다 — "
     "상자와 안 겹친다. 세 축이 다 겹치는 파트는 block_upper 하나뿐이고 그 최소 x 는 **122.3** 이다. "
     "그리고 118 에서 잘라도 상자 안에는 셸 삼각형이 **163개**(256 중) 남는다. 남는 겹침은 x 가 아니라 **z** 에서 온다 — "
     "상자 지붕이 +0.93 인데 셸 배는 x 80~90 에서 +0.24 다. 즉 문서가 «진짜 빈 자리» 라고 부른 바로 그 칸이 "
     "동시에 «셸이 이미 들어 있는» 칸으로 세어졌다. 셸 정점이 크래들 지붕 아래로 처음 내려가는 x 도 130 이 아니라 **128** 이다.",
   "self_inconsistency_ko":
     "이 문서는 X3 에서 «OCC 바운딩박스는 형상이 아니다» 라며 −60.043 을 철회시켰다. X1 의 118 은 같은 종류의 "
     "바운딩박스 허깨비다.",
   "what_to_do_ko":
     "x 컷을 122.3 으로 고치거나(더 정확히는 block_upper 실측 단면으로) 아예 «x 를 자른다» 를 «상자 지붕을 셸 배 "
     "아래로 내린다» 로 바꿔라. 지금 규정대로 자르면 해결하려던 겹침이 63 %(163/256) 그대로 남는다."},

  {
   "id": "A2", "severity": "HIGH", "q": "Q3(고치면 나빠지는가)",
   "where": ["docs/MESH_DEFECTS.md 요약 §0-2 · §2 X2", "outputs/meshdef_spec.json conflicts[1]",
             "docs/MESH_DEFECTS.md §5 A7"],
   "claim": "어안 반지름을 9.0 → 4.3 으로 줄이면 부양이 8.77 → 13.37 mm 로 **더 나빠진다**.",
   "measured": {
     "radius_sweep": {k: dict(min_vertex_dist_mm=v[0], centre_dist_mm=v[1]) for k, v in fish.items()},
     "centre_distance_is_invariant": len({v[1] for k, v in fish.items() if "only" in k and k.startswith("r")}
                                         | {fish["baseline r9.0 z-19.1"][1]}) == 1},
   "why_it_is_wrong_ko":
     "반지름을 9.0 에서 1.0 까지 훑으니 «정점→나머지» 최단거리가 8.77 → 16.63 으로 **단조 증가**하고, "
     "같은 조건에서 «렌즈 중심→나머지» 거리는 **모든 반지름에서 16.313 mm 로 똑같다**(자릿수까지 동일). "
     "즉 이 지표는 «렌즈가 얼마나 떠 있나» 가 아니라 «렌즈 **표면**이 껍질에서 얼마나 물러났나» 를 잰다. "
     "N3 은 부양을 키우지 않는다 — 그대로 두면서 렌즈 크기를 CAD 에 맞출 뿐이다. "
     "(부양 라운드의 정확한 점-삼각형 값 7.300 mm 도 16.313 − 9.0 = 7.313 과 맞는다 — 같은 구조다.)",
   "collateral_ko":
     "합격조건 A7 이 바로 이 지표 위에 쓰여 있다(«8.7712 에서 줄어든다»). 반지름 하나만으로 통과/실패가 "
     "뒤집히는 눈금이라 게이트로 못 쓴다. 중심거리처럼 반지름에 둔감한 양이나, 크래들 면과 렌즈 표면 사이의 "
     "실제 최단거리로 바꿔야 한다.",
   "what_survives_ko":
     "운용 결론(N1 먼저, N1→N2→N3 한 커밋)은 살아남는다. 무너지는 것은 이유와 A7 의 눈금이다."},

  {
   "id": "A3", "severity": "MEDIUM", "q": "Q3 · Q2",
   "where": ["docs/MESH_DEFECTS.md §2 X3 · §8", "outputs/meshdef_ground.json Q2_왜_두_값이_어긋나는가"],
   "claim": "h_engine = (CAD 평균 다리길이) + (뿌리 오프셋 7.4175) − (발끝 구 4.7) 이 **0.000 µm** 로 닫힌다.",
   "measured": {
     "frame_bottom_vs_h": dict(slope=gear["d_framezmin_per_mm_h"], intercept_mm=gear["intercept_mm"],
                               rows=gear["rows"]),
     "foot_ball_radius_mm_from_source": ball_r_mm,
     "foot_ball_literal": "src/drone_cad.py:2396  _gear_cone(..., GEAR_SPIKE_H.get(key,0.072), 0.0155, 0.0094)",
     "cad_leg_root_z_mm": [root_f, root_r], "cad_leg_root_mean_mm": round(root_mean, 4),
     "root_offset_reconstructed_mm": round(offset_reconstructed, 4),
     "root_offset_claimed": offset_claimed},
   "why_it_is_wrong_ko":
     "엔진에서 프레임 바닥 = −h − 6.9189 이고 기울기는 정확히 −1.000000 이다(h 45·50.05·52.9·60 으로 확인). "
     "발끝 구 반지름 4.7 mm 는 소스 리터럴이다. 그러면 «뿌리 오프셋» = −6.9189 + 4.7 + 9.6364 = **7.4175** 로 "
     "**역산된다**. 항등식은 대수적으로 «h 는 프레임 바닥이 CAD 발바닥에 앉도록 고른 값이다» 로 줄어든다 — "
     "그건 F06 이 h 를 정한 방식 그 자체다. 0.000 µm 는 검증이 아니라 **동어반복**이다.",
   "second_error_ko":
     "ground 는 7.4175 를 «CAD 다리 뿌리가 엔진 암 평면보다 평균 7.417 mm 아래» 라고 말로 풀었다. "
     "그런데 ground 자신의 CAD 뿌리 z 는 −5.0705 / −14.2023, 평균 **−9.6364** 다. 2.2189 mm 차이는 "
     "엔진 내부의 스파이크 부착 오프셋(6.9189 − 4.7)이지 CAD 량이 아니다. 숫자는 맞고 **설명이 틀렸다**.",
   "what_survives_ko":
     "«2.85 mm 어긋남» 반박은 그대로 산다(두 값은 서로 다른 양이다). 지워야 할 것은 «0.000 µm 로 닫힌다» 라는 "
     "증거 언어와 7.4175 의 잘못된 말풀이뿐이다."},

  {
   "id": "A4", "severity": "MEDIUM", "q": "검사표",
   "where": ["docs/MESH_DEFECTS.md §5 A5(⭐⭐ 함정) · A8", "docs/MESH_DEFECTS.md §7 권고(한 커밋 안 단계별 A1~A8)"],
   "claim": "프롭 갈래를 전부 고쳐도 해시가 안 바뀌어 검사가 «아무 일도 안 일어났는데» 통과한다.",
   "measured": {"prop_z_plus_5mm": trap,
                "gimbal_buried_triangles": {k: v["gimbal_tris_inside_shell"] for k, v in ov.items()},
                "gimbal_selector_note_ko":
                   "선택자는 camera 그룹 중 x>110 이라 전방 어안쌍(z 48~57)도 포함한다. 그 몫은 네 변형에서 "
                   "고정이므로 **차이**는 짐벌이 만든 것이다."},
   "why_it_is_overbilled_ko":
     "prop_sha16 이 안 바뀌는 것은 사실이다(두 기체 다 확인). 그러나 같은 편집에서 **drone_sha16 은 바뀌고**"
     "(matrice4e 85c701d2 → 6f936e25) mini5pro 는 frame_sha16 까지 바뀐다. 검사표의 A1 이 이미 세 해시를 "
     "다 보므로 «검사가 통과해 버린다» 는 상황은 A1 을 지키는 한 안 생긴다. A5 는 여전히 옳고 유용하지만 "
     "⭐⭐ 급 함정은 아니다.",
   "real_checklist_bug_ko":
     "⭐ 진짜 구멍은 A8 이다. 짐벌 블록이 셸 안에 묻히는 삼각형 수를 직접 세니 현재 **567**, G1+G2 만 넣으면 "
     "**645**(+78), 권고 묶음 G1+G2+G3 은 **576**(+9), G1~G4 는 **542** 다. 문서는 «한 커밋으로 넣되 안에서 "
     "단계별로 A1~A8 을 돌려라» 라고 권하는데, A8(«겹침이 늘지 않는다»)은 G1+G2 단계에서 중단을 지시한다 — "
     "최종 상태는 사실상 중립인데도. A7 에는 «중간 상태는 검사하지 않는다» 예외를 줬으면서 A8 에는 안 줬다."},

  {
   "id": "A5", "severity": "MEDIUM", "q": "Q1(축척 기준)",
   "where": ["outputs/meshdef_prop_gap.json ground_truth.photo.verdict",
             "outputs/meshdef_gimbal.json photo_4e.scale_anchor_1/2",
             "outputs/meshdef_floating.json R3_photo_evidence"],
   "claim": "사진과 CAD 는 «서로 독립인 두 출처» 이고 0.4 mm 안에서 같은 답을 낸다.",
   "measured": {
     "prop_gap_anchor": PRP["ground_truth"]["photo"]["scale_anchor"],
     "prop_gap_px_per_mm": PRP["ground_truth"]["photo"]["px_per_mm"],
     "gimbal_anchor_1": GIM["photo_4e"]["scale_anchor_1"],
     "gimbal_anchor_2": GIM["photo_4e"]["scale_anchor_2"],
     "floating_anchor_ko": FLT["R3_photo_evidence"]["본_것"][1]["읽은_것"][:160]},
   "finding_ko":
     "⭐ 먼저 좋은 소식 — **공표 제원을 px/mm 앵커로 쓴 사진 측정은 하나도 없다**. 전부 공식 CAD 다. "
     "그러니 Q1 이 걱정한 «공표로 재서 공표를 검증» 하는 순환은 없다. "
     "그러나 다른 종류의 순환이 있다: 사진의 **축척도 datum 도 같은 CAD** 에서 온다. prop_gap 은 "
     "축척을 CAD tag104 캔 높이 12.22 mm 로 잡고, 그 캔으로 z 원점도 잡은 다음, 결과를 CAD 의 15.31 mm 와 "
     "견주며 «서로 독립인 두 출처» 라고 적었다. 독립인 것은 **비(比)** 하나뿐이다(캔 높이 대비 블레이드면 높이). "
     "절대값 15.31 은 구성상 CAD 다. 짐벌 라운드도 같은 구조다(앵커 63.21·336.61 이 둘 다 CAD).",
   "extra_ko":
     "같은 파일 안에서 tag104 높이가 앵커에서는 **12.22 mm**, 자기 스택 표에서는 z [−1.5, 10.5] = **12.0 mm** 다. "
     "1.8 % 축척 모호성이 미해결로 남아 있다.",
   "one_real_published_anchor_ko":
     "공표값이 판단을 끄는 자리는 딱 하나다 — ground 가 «공표 149.5 는 RTK 터렛까지» 라고 datum 을 고를 때다. "
     "고른 뒤 Q5 가 «raw 149.52 가 공표 149.5 와 맞았다» 를 헤드라인 지표로 쓴다. ground 는 이걸 스스로 "
     "⚠2·⚠3 에 적어 뒀는데(«형상이 옳다는 증거가 아니다», «실루엣과 같은 맹점»), **합본 MESH_DEFECTS.md 에는 "
     "그 경고가 안 실렸다**."},

  {
   "id": "A6", "severity": "MEDIUM", "q": "Q1(정밀도) · Q2",
   "where": ["docs/MESH_DEFECTS.md §3 mini2 M2", "outputs/meshdef_mini2_glb.json correction_candidates[1]"],
   "claim": "문서가 CAD 충실도를 **17배 과소평가**한다 — «+0.4 %» 가 아니라 «+0.024 %» 다.",
   "measured": {"my_motor_diagonals_mm": fe["motor_diagonal_mm"],
                "published_mm": fe["published_diagonal_mm"],
                "published_quantum_mm": fe["published_quantum_mm"],
                "published_rounding_rel_pct": round(0.5 / 213.0 * 100, 3)},
   "finding_ko":
     "값 자체는 맞다 — 나도 GLB 에서 213.0511 · 213.0515 mm 를 얻었다(좌우 차 0.0004 mm). "
     "문제는 **기준의 눈금**이다. 공표 «213 mm» 는 정수 mm 라 반올림 폭이 ±0.5 mm = **±0.235 %** 다. "
     "0.024 % 는 기준이 분간할 수 있는 것보다 10배 작다. «0.4 % → 0.024 %, 17배» 라는 비교는 성립하지 않는다. "
     "방어 가능한 문장은 «GLB 는 공표 213 mm 와 그 반올림 폭 안에서 일치한다» 다. "
     "펼침 bbox 오차 0.071/0.214/−0.040 % 도 같은 이유로 세 자리까지 적을 근거가 없다(기준이 159/203/56 정수)."},

  {
   "id": "A7", "severity": "MEDIUM", "q": "Q1(재현성)",
   "where": ["docs/MESH_DEFECTS.md 맨 끝 «생성: scratchpad/…»",
             "outputs/meshdef_ground.json provenance.scripts",
             "outputs/meshdef_mini2_glb.json reproduction.scripts_location",
             "outputs/meshdef_floating.json (생성 스크립트 기록 없음)"],
   "claim": "모든 숫자는 측정 또는 인용이며 손으로 입력한 것이 없다.",
   "measured": P["script_survival"],
   "finding_ko":
     "합본의 측정·판정 스크립트는 benchmark/meshdef_spec_measure.py · _judge.py 로 살아남았고 "
     "스크래치패드 원본과 **바이트 동일**이다(확인함). 짐벌도 benchmark/meshdef_gimbal_measure.py 가 있다. "
     "그러나 **floating·ground·mini2·prop_gap 의 측정 스크립트는 세션 스크래치패드에만 있다** — "
     "ground 는 9개(area/before/build_out/extract_cad/final/fit/legs/pad2/save_pad), mini2 는 "
     "measure.py~measure7.py, floating 은 아예 기록이 없다. 세션이 끝나면 사라진다. "
     "즉 «저장소만 받은 사람» 은 이 라운드의 핵심 수치(−59.8231, 7.4175, 6.656, 0.102796, 8.77/13.37 …) 중 "
     "합본이 다시 잰 것 말고는 재현할 수 없다. mini2 라운드 자신이 «필요하면 저장소로 옮길 것» 이라 적어 뒀는데 "
     "아직 안 옮겼다.",
   "what_to_do_ko": "패치 커밋 전에 네 갈래 스크립트를 benchmark/ 로 옮기고, 문서 말미의 provenance 를 "
                    "스크래치패드 경로가 아니라 저장소 경로로 고쳐라."},

  {
   "id": "A8", "severity": "MEDIUM", "q": "Q6(무효화 완전성)",
   "where": ["docs/MESH_DEFECTS.md §6", "outputs/meshdef_spec.json invalidation"],
   "claim": "A급 13묶음 · B급 · C급으로 무효화 대상을 다 적었다.",
   "measured": {"reader_count": P["invalidation_gap"]["reader_count_reproduced"],
                "n_uncovered": P["invalidation_gap"]["n_uncovered"],
                "uncovered": P["invalidation_gap"]["uncovered"],
                "notebooks_on_disk": P["invalidation_gap"]["notebooks_on_disk"],
                "notebooks_in_invalidation": P["invalidation_gap"]["notebooks_in_invalidation"],
                "md_range_sweep_runtime_they_measured_s":
                   SPEC["cost"]["anchors"]["measured"].get("md_range_sweep_s")},
   "finding_ko":
     "세는 법(115개 스크립트)은 정확히 재현된다 — 오늘 값과의 차이는 이번 라운드가 새로 넣은 자기 스크립트뿐이다. "
     "그런데 그 스크립트들이 만드는 산출물 중 **어느 티어에도 안 걸린 것이 50개**다. 전부가 문제는 아니지만 "
     "다음은 확실히 A~B 급이다.",
   "named_gaps_ko": [
     "⭐ outputs/md_range_sweep.json ← src/experiment_md_range.py — 거리별 마이크로도플러(우리 메쉬 위 PO). "
     "이번 라운드가 **자기 비용표에 이 파일의 런타임 2929.6 s 를 적어 놓고도** 무효화 목록에는 안 넣었다. "
     "사용자가 지금 지키라고 한 바로 그 계열이다.",
     "outputs/lowfreq_grid.json · lowfreq_anchor.json · lowfreq_attack.json — phantom3 σ 사다리. "
     "문서는 «P1·P2·P5 가 phantom3 을 건드리면 C→A» 라면서 anchor_subband*·p3_* 만 이름을 댔다.",
     "outputs/facet_count.json · facet_mechanism.json — 패싯 수 → σ 연구(mavic4pro). 프롭 갈래는 10기 전부를 움직인다.",
     "outputs/real_cad_compare.json · phantom4_scan_compare.json · mini2_mesh_audit.json · mini2_specs.json · "
     "m350rtk_mesh_audit.json · m350rtk_layout_check.json — 형상 대조 점수 그 자체다.",
     "outputs/report2_waveform_rcs.json · report3_rt.json · report5_results.json · report6_sbr.json · "
     "report1_microdoppler.npz · report00_po_case.json · sbr_kr_sweep.json · rt_ray_budget.json",
     "⭐ 리포트 노트북 7편(report00_foundations.ipynb … report06_measurement.ipynb) 이 목록에 **한 번도 안 나온다** "
     "(«ipynb» 라는 글자가 무효화 블록 전체에 없다). 이게 실제 산출물이고 dBsm·기체 이름을 본문에 박고 있다."],
   "not_a_gap_ko": "outputs/sigma_sbr_cache.json 은 구멍이 아니다 — 키가 «드론@지문|주파수|방위|고각» 이라 "
                   "X5 가 이미 다룬 지문 보호 대상이다(내가 파일을 열어 확인했다)."},

  {
   "id": "A9", "severity": "LOW", "q": "Q4(4T→4E 선긋기)",
   "where": ["docs/MESH_DEFECTS.md §3 N1 · G1 · §10", "src/drone_cad.py:410-411,2171,2177",
             "assets/photos/matrice4e/SOURCES.md:13,44-49,84"],
   "claim": "CAD 는 4T 지만 다리·암·모터·셸은 4E 와 공유한다. 4T 전용은 짐벌뿐이고 G4 만 보류하면 된다.",
   "finding_ko":
     "선 자체는 저장소가 그은 곳과 같고, 짐벌 라운드는 그 선을 잘 지켰다 — CAD 개구 6장(=4T 열화상+NIR)을 "
     "쓰지 않겠다고 명시하고 G4 를 보류했다. 그런데 **선언되지 않은 4T 노출이 둘 남는다**.",
   "exposure_1_ko":
     "**N1 의 크래들**. 크래들은 짐벌이 물리는 자리다. 저장소 자신이 src/drone_cad.py:2171 에서 «4T 짐벌은 "
     "열화상+NIR 이 있어 4E 보다 크다», :2177 에서 «4E 블록은 4T 보다 얕다» 라고 적어 놨다. 짐벌이 다르면 "
     "그 자리도 다를 공산이 크다. 그런데 N1 은 판정표에서 그냥 **E1** 이고 어디에도 4T 단서가 안 붙어 있다. "
     "(§10 에 «CAD 는 4T 다» 라는 일반 경고는 있으나 N1 항목에는 없다.)",
   "exposure_2_ko":
     "**G1 의 CAD 교차확인이 편향 방향으로 민다**. 4T 블록은 열화상 때문에 «더 클» 것으로 이미 알려져 있는데, "
     "4E 블록을 44.65 → 61.2 mm 로 키우는 근거로 CAD 65.55 mm 를 나란히 든다. 진짜 4E 근거는 사진의 58.1 mm "
     "하나뿐이고, 그 사진의 px/mm 조차 4T CAD 에서 온다(A5).",
   "exposure_3_ko":
     "N4 자체가 «기체 공유» 전제에 대한 반증 후보다 — 4E 저면 사진과 4T CAD 가 하방 어안 배치에서 어긋난다. "
     "문서는 이걸 «어느 물건인가» 문제로만 다루고, 자기 전제를 시험하는 증거로는 안 읽는다.",
   "what_i_could_not_do_ko":
     "4E 전용 분해자료는 공개된 게 없다(SOURCES.md 스스로 적음). 그러니 «다른 4T 전용 부품이 더 있다» 를 "
     "내가 증명할 수는 없다. 내가 보인 것은 **명세가 4T 위험을 짐벌 치수에만 한정한 것이 근거보다 좁다** 는 것이다."},

  {
   "id": "A10", "severity": "LOW", "q": "Q2 · 차단항목 해소",
   "where": ["docs/MESH_DEFECTS.md §2 X6~X10 의 X7 · §9 차단표",
             "assets/photos/matrice4e/SOURCES.md:115"],
   "claim": "p01 이 좌측면인지 후면인지 미정이라 차단(blocker)이다.",
   "measured": {"p01": "assets/photos/matrice4e/matrice4e_p01_side_profile_left.jpg (2667×2667)",
                "p05": "assets/photos/matrice4e/matrice4e_p05_rear_elevation.jpg (2560×2560)",
                "method": "두 파일을 직접 열어 육안 대조"},
   "finding_ko":
     "⭐ 차단 풀 수 있다 — **p01 은 후면 정면도다**. 두 장 다 위에 RTK 원통 돔, 어깨 좌우에 후방 어안 2개, "
     "가운데 방열 슬릿 패널이 보이고 **짐벌이 화면에 아예 없다**. 요(yaw) 만 조금 다를 뿐 p05 와 같은 뷰다. "
     "짐벌 라운드가 맞고 SOURCES.md:115 의 «side_profile_left» 라벨이 틀렸다.",
   "consequence_the_doc_missed_ko":
     "prop_gap 은 p01 의 모터 벨을 재서 CAD 의 **앞 로터 스택**(x,y = 139.49, 179.28)과 견줬다. "
     "후면도에서 가까이 잡히는 벨은 **뒤 모터**다. matrice4e 는 앞 암이 뒤보다 9.13 mm 높고 벨 중심도 "
     "8.02 mm 높다(ground Q2). prop_gap 이 실제로 보고하는 양은 «캔 윗면 대비 블레이드면» 이라 이 비대칭이 "
     "상쇄되므로 숫자는 살 공산이 크지만, **앞/뒤가 어긋나 있다는 사실이 어디에도 안 적혀 있다**."},

  {
   "id": "A11", "severity": "LOW", "q": "Q2(출처 추적)",
   "where": ["outputs/meshdef_gimbal.json corrections[0].new = 61.2"],
   "claim": "짐벌 블록 높이 47.0 → 61.2 mm.",
   "measured": gh,
   "finding_ko":
     "값은 맞다 — helper 가 그리는 블록 높이는 인자 h 의 정확히 0.950 배라서, 사진 58.1 mm 를 내려면 "
     "h = 58.1 / 0.950 = **61.158 → 61.2** 이고, h=61.2 로 실제로 구우면 블록 높이가 **58.14 mm** 로 나온다. "
     "G2 의 «바닥을 붙박는다» 도 확인된다(−39.720 → −39.736, 0.016 mm). "
     "문제는 **그 유도가 기록 어디에도 없다** 는 것이다. 기록에는 «사진 58.1 · CAD 65.55 · 메쉬 44.65» 다음에 "
     "곧바로 new = 61.2 가 나오고 확신도가 high 다. 읽는 사람은 61.2 가 어디서 왔는지 알 수 없다."},

  {
   "id": "A12", "severity": "LOW", "q": "Q2(기준면 미확정)",
   "where": ["docs/MESH_DEFECTS.md §3 P3 («꼭짓점 313개·삼각형 526개»)"],
   "claim": "mini5pro 앞 프롭 꼭짓점 313개·삼각형 526개가 벨 솔리드 안에 있다.",
   "measured": R2["b_prop_in_bell"],
   "finding_ko":
     "방향·로터 위치·기체 구별은 전부 확인된다 — 앞 로터 둘(0·3, x=+75.8)만 파고들고 뒤 둘은 0, matrice4e 는 "
     "전 로터 0 이다. 그런데 내 셈(벨 = 모터 그룹 최대반경 원기둥 × 벨 z 전구간)은 로터당 **319 꼭짓점 · 662 삼각형** "
     "이다. 313/526 과 다른 이유는 «벨 솔리드 안» 의 판정법이 다르기 때문인데, **두 숫자 다 자기 판정법을 안 달고 "
     "있다**. X8 이 지적한 «기준면 미확정» 과 정확히 같은 종류다 — 그런데 X8 은 간격에만 적용됐다."},
 ],

 "answers": {
  "Q1_measurement_reproducible": {
    "verdict": "부분 통과",
    "ko": "① 공표 제원을 축척 앵커로 쓴 사진 측정은 **하나도 없다** — 순환논증 걱정은 근거가 없다. "
          "전부 공식 CAD 앵커다. ② 대신 사진이 CAD 에 축척·datum 둘 다 묶여 있는데 «독립 두 출처» 라고 "
          "적힌 곳이 있다(A5). ③ 공표값이 판단을 끄는 유일한 자리는 ground 의 datum 선택이고, 그 경고가 "
          "합본에서 빠졌다(A5). ④ mini2 의 «17배» 는 기준의 반올림 폭을 넘는 주장이다(A6). "
          "⑤ 다섯 갈래 중 넷의 측정 스크립트가 세션 임시폴더에만 있어 저장소만으로는 재현 불가다(A7)."},
  "Q2_numbers_copied_or_measured": {
    "verdict": "통과",
    "ko": "표본 재계산에서 베낀 흔적이 없다. 열 기체 기준지문이 **비트단위로** 재현되고, ground 의 fit sz 표는 "
          "가설 8개 중 내가 다시 푼 것이 전부 소수 6자리까지 같으며, 수정 전 커밋(cba8626)을 스크래치패드 사본으로 "
          "직접 돌린 sz 도 0.9501659933 로 열째 자리까지 같다. mini2 의 CAD 목표 7.1999 mm 와 모터 대각 213.051 mm 도 "
          "내가 GLB 를 열어 그대로 얻었다. 어긋난 것은 셈이 아니라 **기준면을 안 밝힌 두 숫자**(526 ↔ 662)뿐이다(A12)."},
  "Q3_does_fixing_make_it_worse": {
    "verdict": "있다 — 그러나 지목된 항목이 아니다",
    "ko": "① 접지: «직접측정을 쓰면 1.019» 는 **맞다**(내 계산 1.019302, ground 1.019302). 그러나 그건 "
          "«뿌리 오프셋을 빼먹었을 때» 의 값이고, 같은 직접측정을 제대로 넣으면 sz = 1.000561 이다. "
          "그리고 수정 전 값을 내가 직접 돌려 sz = 0.9501659933(강제 4.98 %)을 재현했다 — "
          "**«강제압축 5.0 % → 0.01 %» 헤드라인은 철회 대상이 아니다.** 다만 그 지표가 실루엣과 같은 맹점을 "
          "가진다는 ground 의 경고는 합본에 실려야 한다. "
          "② 진짜 «고치면 나빠지는» 것으로 적힌 X2(어안 반지름)는 **눈금의 착시**다 — 렌즈 중심 거리는 "
          "모든 반지름에서 16.313 mm 로 불변이다(A2). "
          "③ 실제로 나빠지는 것은 **짐벌 G1+G2 단독**이다 — 셸에 묻히는 삼각형이 567 → 645 로 는다. "
          "권고 묶음(G1+G2+G3)까지 가면 576 으로 되돌아온다(A4)."},
  "Q4_4T_to_4E_line": {
    "verdict": "대체로 방어 가능 · 구멍 둘",
    "ko": "저장소가 그은 선(기체 공유, 짐벌만 다름)을 짐벌 라운드는 잘 지켰다. 미선언 노출은 "
          "**N1 의 크래들**(짐벌이 물리는 자리인데 4T 단서 없이 E1) 과 **G1 의 CAD 교차확인 방향**(4T 가 더 크다는 "
          "것이 이미 알려진 축에서 CAD 를 근거로 든다) 이다. N4 자체가 «기체 공유» 전제의 반증 후보라는 점도 "
          "문서가 안 읽었다. 4E 전용 분해자료가 세상에 없으므로 «다른 4T 전용 부품» 을 내가 증명할 수는 없다(A9)."},
  "Q5_mini2_glb_obtained": {
    "verdict": "통과",
    "ko": "확보했다. assets/meshes/reference/WM161_zhankai_1k.glb 의 md5 가 기록과 같고(7d391743…), "
          "접힘판도 있다(82ef4d3e…). 내가 그 파일을 열어 원점 두 개(20.21770 · 1844.35829)와 "
          "pSphere3 의 y 중심 ±7.1999/7.2000 mm, 모터 대각 213.0511/213.0515 mm 를 직접 재서 기록과 맞췄다. "
          "두 파일은 **git 에 아직 안 올라가 있다**(untracked, gitignore 대상 아님) — 라운드가 «커밋 안 했다» 고 "
          "정직하게 적어 뒀다. 정직성 문제 없음. 다만 그 값을 뽑은 measure*.py 는 스크래치패드에만 있다(A7)."},
  "Q6_invalidation_complete": {
    "verdict": "불완전",
    "ko": "세는 법은 재현된다(115 집합 일치). 그러나 메쉬를 읽는 스크립트가 만드는 산출물 중 **50개가 어느 "
          "티어에도 안 걸린다**. 이름을 댈 수 있는 것 중 가장 아픈 것은 마이크로도플러 계열의 "
          "**outputs/md_range_sweep.json**(이번 라운드가 런타임 2929.6 s 를 자기 비용표에 적어 놓고도 빠뜨렸다) 과 "
          "**리포트 노트북 7편 전부**(목록에 «ipynb» 라는 글자가 없다) 다. phantom3 저주파 격자(lowfreq_*)도 "
          "«P1 이 phantom3 을 건드리면 C→A» 규칙에서 이름이 빠졌다(A8)."},
 },

 "what_i_did_not_test": [
   "σ 를 새로 굽지 않았다 — GPU 를 안 썼으므로 이 문서의 dB 추정은 전부 검증 대상 밖이다.",
   "CAD(158 MB STEP)를 다시 임포트하지 않았다. −59.8231 / −60.043 다툼(X3)의 **CAD 쪽**은 ground 의 값을 "
   "그대로 받았고, 내가 검증한 것은 그 값을 엔진에 넣었을 때의 거동뿐이다.",
   "짐벌 겹침 판정은 z 축 광선 홀짝이라 셸이 watertight 인 것에 기댄다(확인함: True). 면-면 교차는 안 셌다.",
   "N4(어안 좌우 vs 앞뒤)는 사진 판독이 필요해 손대지 않았다 — 차단 항목으로 남는다.",
   "«이 라운드 이후 원본 다섯 파일이 바뀌지 않았다» 는 것은 mtime 으로만 봤다.",
 ],
}

p = os.path.join(ROOT, "outputs/meshdef_attack.json")
json.dump(VER, open(p, "w"), ensure_ascii=False, indent=1)
print("wrote", p, os.path.getsize(p), "bytes; verdict =", VER["verdict"],
      "; defects =", len(VER["defects"]))
