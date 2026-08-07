#!/usr/bin/env python
"""측정한 meshdef_spec.json 위에 **판정 층**을 얹는다 — 후보표·충돌·순서·검사·무효화·비용.

숫자는 전부 이 파일이 읽어 오는 곳(측정 결과 또는 다섯 라운드의 JSON)에서 가져온다.
"""
from __future__ import annotations
import json, os, re, subprocess, time

ROOT = "/home/yunjung/workspace/sionna2"
SPEC = os.path.join(ROOT, "outputs", "meshdef_spec.json")
D = json.load(open(SPEC, encoding="utf-8"))
rounds = {k: json.load(open(os.path.join(ROOT, "outputs", f"meshdef_{k}.json"), encoding="utf-8"))
          for k in ("floating", "gimbal", "ground", "mini2_glb", "prop_gap")}

NC = D["nose_conflict"]
V = {v["tag"]: v for v in NC["variants"]}
IL = D["interlocks"]


def var(tag, key="down_pair_min_dist_to_rest_mm"):
    return V[tag][key]


# ══════════════════════════════════════════════════════════════════════════
# 근거 등급 — 이 명세 전체가 쓰는 눈금
# ══════════════════════════════════════════════════════════════════════════
GRADES = {
    "E1_official_cad": "제조사 공식 CAD(STEP/GLB)를 우리가 직접 임포트해 잰 값. 가장 세다.",
    "E2_photo": "제품 사진·렌더를 축척 앵커를 걸어 잰 값. 각도·원근·앵커 선택에 흔들린다.",
    "E3_published_spec": "제조사가 공표한 제원 숫자. 무엇을 재는지(기준면)가 안 적혀 있는 경우가 많다.",
    "E4_inherited": "저장소가 옛 라운드에서 물려받은 값·LLM 조사 서술문. 1차 출처가 없으면 가장 약하다.",
    "E0_engine_measurement": "우리 엔진이 실제로 만드는 메쉬를 이번 라운드가 직접 잰 값. "
                             "'무엇이 옳은가'가 아니라 '지금 무엇이 있는가'의 최종 심판이다.",
}

# ══════════════════════════════════════════════════════════════════════════
# 후보표 — 다섯 라운드 18건을 하나의 번호체계로
# ══════════════════════════════════════════════════════════════════════════
CANDIDATES = [
  # ── matrice4e 기수(어안·크래들) ────────────────────────────────────────
  dict(id="N1", was="floating F23", drone="matrice4e",
       what="기수 밑 짐벌 크래들이 통째로 없다 — 넣는다",
       where="src/drone_cad.py:2188 부근(신설 파트) 또는 :444-445 (_SHELL_SHAPE k3)",
       old=None, new="CAD 솔리드 #55/#56/#57 (바닥 z=−17.19)",
       grade="E1_official_cad", confidence="high(없다는 사실) / medium(넣을 형상)",
       verdict="APPLY — 단, x 범위를 잘라서",
       ko="CAD 는 이 자리에 z=−17.19 까지 내려오는 구조를 갖고 우리 셸은 그 자리에서 "
          "z=+0.24 에 끝난다(x 80~90 실측). 세 결함(N1·N2·N3) 중 이것만이 «없는 것을 넣는» 일이다."),
  dict(id="N2", was="floating F22", drone="matrice4e",
       what="하방 어안쌍 z 를 CAD 로 올린다",
       where="src/drone_cad.py:2207 (좌표) · :2192 (근거 주석)",
       old=-19.1, new=-13.64, unit="mm",
       grade="E1_official_cad", confidence="high",
       verdict="APPLY — N1 과 같은 커밋에서만",
       ko="독립 교차검증이 있다. 짐벌 라운드가 앵커 3개로 푼 z 변환 상수는 −5.41 이고, "
          "부양 라운드가 말하는 '두 번 뺀 datum' 은 5.272 다 — 0.14 mm 안에서 같은 값을 가리킨다."),
  dict(id="N3", was="floating F24", drone="matrice4e",
       what="어안 하우징 반지름을 CAD 치수로 줄인다",
       where="src/drone_cad.py:2208 `_fisheye(cx, cy, cz, 0.009)`",
       old=9.0, new={"하방쌍": 4.3, "전방쌍": 5.6, "후방쌍": 5.7}, unit="mm",
       grade="E1_official_cad", confidence="high(CAD 치수) / medium(구 하나로 근사할 등가반지름)",
       verdict="APPLY LAST — N1 없이는 **적용 금지**",
       ko="측정으로 확인: 이것만 넣으면 부양이 더 나빠진다(아래 X2)."),
  dict(id="N4", was="floating F25", drone="matrice4e",
       what="하방 어안이 좌우 한 쌍인가 앞뒤 한 쌍인가",
       where="src/drone_cad.py:2194-2195 (선언) · :2207 (좌표)",
       old="좌우 한 쌍 (x=+84.4, y=±17.75)", new="미정 — 사진은 중앙선 앞뒤(x≈+22/−56, y≈0)",
       grade="E1_official_cad vs E2_photo", confidence="low",
       verdict="⛔ BLOCKER — 먼저 판정. 코드 변경 없음",
       ko="이건 숫자 다툼이 아니라 «어느 물건인가» 다툼이라 등급만으로 못 가른다. "
          "N1·N2·N3 은 전부 x≈84 에 구조를 놓는데, 여기가 뒤집히면 셋 다 틀린 자리를 정성껏 고치는 일이 된다."),
  # ── matrice4e 짐벌 ────────────────────────────────────────────────────
  dict(id="G1", was="gimbal h", drone="matrice4e",
       what="짐벌 블록 높이", where="src/drone_cad.py:2178",
       old=47.0, new=61.2, unit="mm", grade="E2_photo (+E1 교차확인)", confidence="high",
       verdict="APPLY — 단 요·댐핑판 z 를 h 에서 떼어낸 뒤",
       ko="사진(4E) 58.1 · CAD(4T) 65.6 · 메쉬 44.65. 폭은 세 출처가 63~65 mm 로 모이는데 높이만 메쉬가 혼자 작다."),
  dict(id="G2", was="gimbal cz", drone="matrice4e",
       what="짐벌 블록 중심 높이(지상고 붙박이용 종속값)", where="src/drone_cad.py:2178",
       old=-17.16, new=-10.36, unit="mm", grade="E1_official_cad", confidence="high",
       verdict="APPLY — G1 과 한 쌍. 따로 넣으면 지상고가 틀어진다"),
  dict(id="G3", was="gimbal w", drone="matrice4e",
       what="짐벌 블록 폭", where="src/drone_cad.py:2178",
       old=59.0, new=62.9, unit="mm", grade="E2_photo", confidence="medium",
       verdict="APPLY — G1·G2 와 같은 커밋"),
  dict(id="G4", was="gimbal d, cx", drone="matrice4e",
       what="짐벌 블록 깊이와 중심 x", where="src/drone_cad.py:2178",
       old=[52.0, 148.3], new=[36.4, 156.1], unit="mm",
       grade="E1_official_cad(4T 차용)", confidence="low",
       verdict="DEFER — 4E 깊이를 잴 사진이 없다",
       ko="4T CAD 값을 빌려 쓰는 것 말고 방법이 없고, 아랫면이 줄어 바닥유령(report09) 계열이 함께 움직인다. "
          "짐벌 라운드 자신이 확신도를 low 로 적었다."),
  # ── matrice4e 접지·다리 ───────────────────────────────────────────────
  dict(id="R1", was="ground 후보1", drone="matrice4e",
       what="GEAR_SPIKE_H['matrice4e']", where="src/drone_cad.py:331",
       old=0.0529, new=0.0529, unit="m", grade="E1_official_cad", confidence="high",
       verdict="⛔ NO CHANGE",
       ko="독립 역산과 4.1 µm 차이다. 3.5 GHz 파장의 5×10⁻⁵ 이라 물리적으로 뜻이 없다."),
  dict(id="R2", was="ground 후보2", drone="matrice4e",
       what="발 높이를 앞뒤 평균으로 바꾸는 대안", where="src/drone_cad.py:331",
       old=0.0529, new=0.0527971, unit="m", grade="E1_official_cad", confidence="medium",
       verdict="⛔ REJECT",
       ko="딱딱한 바닥에서 실제로 닿는 곳은 최저점(앞발)이지 평균이 아니다. 게다가 공표높이 일치가 4배 나빠진다."),
  dict(id="R3", was="ground 후보3 ⭐", drone="matrice4e",
       what="앞·뒤 다리 길이를 따로 두고 암 평면을 앞뒤로 분리한다",
       where="src/drone_cad.py:331 · :2385 (z_arm) · :1063 (_gear_arm_spikes)",
       old="단일값(다리 1개 길이 · 암 평면 1개)",
       new={"front_leg_mm": 54.753, "rear_leg_mm": 45.407,
            "front_root_z_mm": -5.071, "rear_root_z_mm": -14.202,
            "front_bell_center_z_mm": -0.239, "rear_bell_center_z_mm": -8.263},
       grade="E1_official_cad", confidence="high",
       verdict="APPLY LAST — 엔진 시그니처 변경",
       ko="실물은 앞 암이 뒤 암보다 9.13 mm 높고 모터 벨 중심도 앞이 8.02 mm 높다. "
          "엔진은 넷을 한 평면에 놓아 이 비대칭을 표현할 수가 없다. 로터 4개 코히어런트 합이 "
          "5.8 GHz·앙각 60° 에서 3.55 dB 까지 갈린다(ground 라운드의 추정, σ 계산 아님)."),
  # ── 전 기체 프롭 간격 ─────────────────────────────────────────────────
  dict(id="P1", was="prop_gap C1", drone="fleet(10)",
       what="prop_z 를 벨 윗면에서 유도한다(단일 출처)", where="src/drones.py:1194",
       old="motor_h + arm_t/2 + 0.006",
       new="bell_top_z(spec, key) + standoff(spec) − blade_plane_offset(spec)",
       grade="E1_official_cad + E2_photo", confidence="high(두 식이 하나여야 한다) / medium(standoff 값)",
       verdict="APPLY FIRST (프롭 갈래에서)",
       ko="지금은 프롭이 벨 밑동을 안 읽고, 벨은 프롭이 안 읽는 밑동을 쓴다. 닫힌식이 10기체를 "
          "1 µm 안에 재현하므로 원인은 확정이다. 이걸 먼저 넣으면 나중에 벨을 내릴 때 프롭이 저절로 따라온다."),
  dict(id="P2", was="prop_gap C2", drone="mini5pro·mavic4pro·phantom4",
       what="벨 높이 대각비례식의 이중정의를 통일한다(0.045 vs 0.048)",
       where="src/drones.py:1181 ↔ src/drone_cad.py:2053",
       old="drones 0.045·diag / drone_cad 0.048·diag", new="0.048·diag 하나로",
       grade="E0_engine_measurement", confidence="high",
       verdict="APPLY — P1 보다 먼저 넣는 편이 깔끔하다",
       ko="같은 물건의 높이를 두 파일이 다르게 믿는다. mavic4pro 에서 그 차이 1.32 mm 가 간격에 그대로 실린다."),
  dict(id="P3", was="prop_gap C3", drone="mini5pro",
       what="mini5pro 앞 로터가 벨을 파고드는 문제",
       where="src/drone_cad.py:375 (ARM_Z_FOLLOWS_ROTOR) / src/drones.py:221 (rotor_z_mm)",
       old="{'mini2': True} / rotor_z_mm=(−12,+2,+2,−12)",
       new="{'mini2': True, 'mini5pro': True}  **또는**  rotor_z_mm=None",
       grade="E4_inherited", confidence="high(지금이 틀렸다) / low(어느 쪽이 옳은지)",
       verdict="⛔ BLOCKER — 1차 출처 확인 뒤",
       ko="앞 프롭 꼭짓점 313개·삼각형 526개가 벨 솔리드 **안에** 있다. 이건 반박 불가다. "
          "그런데 «앞 모터가 14 mm 낮다» 는 크기의 1차 출처가 저장소에 없다 — 지금 등급은 상속(E4)이다."),
  dict(id="P4", was="prop_gap C4", drone="fleet(10)",
       what="패치가 무엇을 맞출 것인가 — 허브 밑면인가 블레이드 중립면인가",
       where="src/drone_cad.py:40-77 build_propeller_cad / _prop_hub / _blade",
       old="블레이드 중립면 = 장착면 + 1.66 mm (matrice4e)",
       new="옵션 A: 블레이드면을 벨 윗면에 / 옵션 B: 허브 밑면을 벨 윗면에",
       grade="E2_photo", confidence="medium",
       verdict="DECIDE — 옵션 B 권고(잔차 1.66 mm, 새 겹침 없음)",
       ko="옵션 A 는 잔차 0 이지만 허브가 벨 캡을 1.66 mm 파고들어 면이 겹친다. "
          "build_drone 은 불리언 합집합을 안 하므로 그 겹침면이 살아남고, 가림 없는 PO 경로가 그대로 적분한다."),
  dict(id="P5", was="prop_gap C5", drone="fleet(10)",
       what="스탠드오프를 기체별 필드로 뺀다", where="새 spec 필드 prop_standoff_mm",
       old="6 mm 전 기체 공통", new={"matrice4e/mavic4pro": 0.0, "phantom3": 3.0, "x500v2": "현행 유지"},
       unit="mm", grade="E1_official_cad + E2_photo", confidence="medium",
       verdict="APPLY — P1 과 같은 커밋"),
  # ── mini2 ─────────────────────────────────────────────────────────────
  dict(id="M1", was="mini2 C1", drone="mini2",
       what="벨리 하방비전 렌즈 좌우 오프셋", where="src/drone_cad.py:2325",
       old=0.1077, new=0.102796, unit="bw 에 대한 무차원 비",
       grade="E1_official_cad", confidence="high",
       verdict="APPLY FIRST (전체에서) — 결합이 0 이고 이번 라운드가 독립 확인했다",
       ko="엔진이 실제로 렌즈를 놓는 자리를 직접 재니 y = 7.5434 mm 로, mini2 라운드의 계산과 "
          "소수 넷째 자리까지 같다. CAD 는 7.1999 다. 리터럴이 key=='mini2' 분기 안이라 파급이 없다."),
  dict(id="M2", was="mini2 C2·C3·C4·C5", drone="mini2",
       what="문서 4건(SOURCES.md 모터 대각거리·프롭 지름·접힘 부호·주장 강도)",
       where="assets/photos/mini2/SOURCES.md:126,128,129 · src/drones.py mini2 note",
       old="문서 서술", new="문서 서술", grade="E1_official_cad", confidence="high",
       verdict="APPLY — 메쉬 무변경, 무효화 0",
       ko="C2 가 특히 중요하다. 문서가 CAD 충실도를 17배 **과소**평가하고 있다(+0.4 % → +0.024 %). "
          "GLB 를 형상 근거로 쓸 자격을 주는 바로 그 문장이다."),
]

# ══════════════════════════════════════════════════════════════════════════
# 충돌 — 같은 상수·같은 자리를 서로 다르게 건드리려는 곳
# ══════════════════════════════════════════════════════════════════════════
CONFLICTS = [
  dict(id="X1", severity="HIGH", kind="같은 부피를 두 라운드가 각각 채우려 한다",
       between=["floating N1(크래들 신설)", "gimbal G1~G4(짐벌 블록)", "현 셸(body)"],
       measured=dict(
           tris_already_in_proposed_cradle_box=dict(
               body=V["baseline"]["tris_already_inside_F23_box"]["body"],
               gimbal_only_camera=16,
               note="camera 총계에는 하방 어안쌍 자신이 섞여 들어간다. 짐벌만 센 값이 16 이다."),
           gimbal_assembly_bbox_now_mm=NC["gimbal_helper"]["current"]["assembly_bbox_mm"],
           gimbal_assembly_bbox_after_G4_mm=NC["gimbal_helper"]["G1_to_G4"]["assembly_bbox_mm"],
           shell_belly_profile=NC["shell_belly_profile"]),
       adjudication="근거 등급이 아니라 산수로 갈린다 — 셸 배 프로파일을 직접 쟀다.",
       ruling="크래들 신설 파트의 x 범위를 71.59~146.34 에서 **71.6 ~ 약 118** 로 자른다.",
       why_ko="셸 배는 x 80~90 에서 z=+0.24 로 끝나지만(진짜 빈 자리), x 130 부터는 이미 "
              "z=−18.15 까지 내려와 크래들 지붕(−17.19)보다 낮다. 그리고 짐벌 조립체가 x=117.62 "
              "에서 시작한다. 그래서 제안된 상자 안에는 셸 삼각형 256개와 짐벌 삼각형 16개가 "
              "**이미 들어 있다**. build_drone 은 불리언 합집합을 하지 않으므로 이 겹침면은 "
              "살아남아 PO 가 두 번 센다."),
  dict(id="X2", severity="HIGH", kind="한 라운드 안에서 두 후보가 서로를 무효화한다",
       between=["floating N2 (어안 z 올리기)", "floating N3 (어안 반지름 줄이기)"],
       measured={t: var(t) for t in ("baseline", "F22 only  (down-pair z −19.1 → −13.64)",
                                     "F24 only  (down-pair r 9.0 → 4.3)", "F22 + F24")},
       measured_unit="하방 어안쌍 정점 → 나머지 메쉬 최단거리 [mm] (KD-tree, 정점→면 조밀샘플)",
       adjudication="측정. 부양 라운드는 두 후보를 따로따로만 봤다.",
       ruling="N3 은 **N1 없이 적용 금지**. 순서는 N1 → N2 → N3.",
       why_ko="지금 8.77 mm 떠 있다. z 만 올리면 5.82 로 줄지만 안 붙는다. 반지름만 줄이면 "
              "13.37 로 **더 나빠진다**(구가 작아지면 표면이 뒤로 물러난다). 둘 다 넣어도 "
              "10.44 로 지금보다 나쁘다. 세 후보 중 «없는 구조를 넣는» N1 만이 이 결함을 실제로 닫는다.",
       caveat_ko="내 8.77 mm 는 정점→조밀샘플 KD-tree 값이라 상한이다. 부양 라운드의 7.300 mm 는 "
                 "정확한 점-삼각형 거리다. 방향과 순서 판정은 두 눈금에서 같다."),
  dict(id="X3", severity="HIGH", kind="같은 CAD 양을 두 라운드가 다르게 쟀다",
       between=["floating 곁가지 C3 (CAD 발 −60.043 앞 / −59.80 뒤)",
                "ground Q1 (앞 −59.8231 / 뒤 −59.6149)"],
       adjudication="등급은 둘 다 E1(공식 CAD)이라 등급으로는 못 가른다 — **방법**으로 가른다.",
       ruling="ground 채택. 저장소의 −59.82 가 맞다. floating 곁가지 C3 은 철회.",
       why_ko="발 패드 바닥은 B-스플라인 면이고 OCC 바운딩박스는 그런 면을 제어점 껍질로 감싼다 — "
              "반드시 감싸지만 딱 맞지는 않는다. ground 는 면을 200×200 격자로 훑은 값과 모서리 "
              "32샘플 값이 소수 넷째 자리까지 일치함을 보였다. 차이 0.22 mm 는 전부 bbox 여유다.",
       residual_ko="⚠ ground 자신의 파일이 뒷발을 본문 −59.6090 · 후보표 −59.6149 로 두 번 다르게 "
                   "적었다(0.006 mm). 결론에는 영향이 없으나 적용 전에 한쪽으로 정리할 것."),
  dict(id="X4", severity="HIGH", kind="두 갈래가 서로를 끌고 간다(얽힘) — 방향이 기체마다 반대",
       between=["ground (다리·접지)", "prop_gap (프롭 장착 높이)"],
       measured=dict(
           matrice4e_gear_to_prop=dict(
               d_sz_per_mm_leg=IL["A_matrice4e_gear_drives_prop"]["d_sz_per_mm_leg"],
               d_belltop_mm_per_mm_leg=IL["A_matrice4e_gear_drives_prop"]["d_belltop_mm_per_mm_leg"],
               d_gap_mm_per_mm_leg=IL["A_matrice4e_gear_drives_prop"]["d_gap_mm_per_mm_leg"]),
           matrice4e_prop_to_gear=dict(
               sz_unchanged_under_prop_shift=IL["C_matrice4e_prop_has_no_feedback"]["sz_all_equal"],
               tested_shift_mm=[-5.0, 0.0, 5.0]),
           mini5pro_prop_to_gear=dict(
               d_sz_per_mm_prop=IL["B_mini5pro_prop_drives_gear"]["d_sz_per_mm_prop"],
               d_gear_zmin_mm_per_mm_prop=IL["B_mini5pro_prop_drives_gear"]["d_gearzmin_mm_per_mm_prop"])),
       adjudication="측정. 두 방향을 다 시험했다.",
       ruling="matrice4e 는 «다리 → 프롭» 한 방향뿐. mini5pro 는 «프롭 → 다리» 로 **반대**. 고리는 없다.",
       why_ko="matrice4e 는 공식 높이가 프롭을 안 포함해서(env_props_included=False) 배율 sz 를 "
              "프레임 bbox 로만 푼다 — 프롭을 ±5 mm 옮겨도 sz 가 소수 9자리까지 그대로다. "
              "반대로 다리를 1 mm 늘리면 sz 가 −0.00669 움직이고 그 배율이 벨 윗면을 0.150 mm, "
              "프롭 간격을 0.045 mm 끌고 간다. mini5pro 는 공식 높이가 프롭 포함이라 sz 를 "
              "프롭 장착높이로 푼다 — 프롭을 1 mm 올리면 다리 접지점이 0.784 mm 따라 올라간다.",
       consequence_ko="mini5pro 의 로터 z(P3)와 다리를 **같은 편집에 넣으면 안 된다**. 둘 다 움직이면 "
                      "어느 쪽이 무엇을 바꿨는지 못 가른다."),
  dict(id="X5", severity="MEDIUM", kind="파급 경고가 사실과 다르다(좋은 쪽으로)",
       between=["floating N2 breaks_what (σ 캐시에 형상 지문이 없다)", "benchmark/channel.py::_mesh_fp"],
       measured=D["sigma_cache_check"],
       adjudication="측정. 캐시 파일을 열어 키를 직접 파싱했다.",
       ruling="경고 철회 — 단, **더 큰 위험이 그 자리에 있다**.",
       why_ko="σ 디스크캐시 키는 `드론@지문|주파수|방위|고각` 이고 지문은 메쉬 정점에서 나온다. "
              "matrice4e 항목 5개는 이미 옛 지문이라 지금도 미스다. 손으로 지울 필요가 없다. "
              "그런데 이 보호는 50칸짜리 조회표에만 걸린다. **저장된** 격자(report13_sigma_grid*·"
              "das_fleet_*·report15_*·report16_*)에는 지문이 없어서 낡아도 아무 소리를 안 낸다."),
  dict(id="X6", severity="MEDIUM", kind="파급 경고가 과장됐다",
       between=["floating N3 breaks_what (0.009 는 mavic4pro·mini5pro 공용 리터럴)",
                "src/drone_cad.py 분기 구조"],
       measured=dict(matrice4e_branch_line=2162, literal_line=2208, literal_value=0.009,
                     mavic4pro_branch_line=2139, mavic4pro_literal_line=2155, mavic4pro_value=0.009,
                     mini5pro_branch_line=2267, mini5pro_literal_line=2288, mini5pro_value=0.008),
       adjudication="소스 판독.",
       ruling="2208 을 고쳐도 다른 기체는 비트동일이다. 값이 같을 뿐 공유 변수가 아니다.",
       why_ko="2208 은 `elif key == 'matrice4e'` 분기 안에 있다. 2155 는 mavic4pro 분기의 별도 "
              "리터럴이고, 2288 은 mini5pro 분기인데 값이 0.008 로 애초에 다르다. "
              "기종별 표로 빼는 것은 «격리를 위해» 가 아니라 «읽기 쉬우라고» 하는 일이다."),
  dict(id="X7", severity="MEDIUM", kind="같은 사진 파일을 두 라운드가 다르게 부른다",
       between=["gimbal 부수발견 (p01 은 후면뷰다 — p05 와 픽셀 수준으로 같은 각도)",
                "prop_gap ground_truth.photo (p01 좌측면 프로파일에서 블레이드 중립면을 쟀다)",
                "assets/photos/matrice4e/SOURCES.md:115 (좌측면 프로파일 ⭐)"],
       adjudication="두 라운드가 같은 파일을 열고 다른 각도라고 적었다. 나는 이번에 사진을 열지 않았다.",
       ruling="SOURCES.md:115 의 라벨을 먼저 확정한다. prop_gap 의 **높이** 측정은 살아남을 가능성이 크다.",
       why_ko="prop_gap 이 p01 에서 읽은 것은 z(높이)이고, 축척 앵커도 캔 **높이** 12.22 mm 다. "
              "정투영에 가까운 후면뷰에서도 높이는 보존되므로 그 숫자(+15.2~15.7 mm)는 살 공산이 크다. "
              "그러나 반경(r 20~50 mm)을 어느 축으로 읽었는지가 달라지므로 재확인이 필요하다. "
              "그리고 라벨이 틀렸다면 그 표를 믿고 잰 **다른** 값들이 전부 재검토 대상이다."),
  dict(id="X8", severity="MEDIUM", kind="같은 이름의 양을 두 곳이 다르게 정의한다",
       between=["prop_gap fleet_measurement (간격 = 허브 밑면 − 벨 윗면 = 6.656 mm)",
                "이번 라운드 측정 (프롭 메쉬 최저점 − 벨 윗면 = "
                + str(V["baseline"].get("_", "")) + "3.2614 mm)"],
       measured=dict(matrice4e_hub_bottom_minus_bell_top_mm=6.656,
                     matrice4e_propmesh_lowest_minus_bell_top_mm=
                     IL["A_matrice4e_gear_drives_prop"]["rows"]["base"]["gap_propmesh_minus_belltop_mm"]),
       adjudication="둘 다 맞는 측정인데 재는 대상이 다르다 — 블레이드 뿌리가 허브 밑면보다 아래로 처진다.",
       ruling="적용 전에 «간격» 의 기준면을 명세에 못 박는다. 그러지 않으면 «닫혔는가» 검사가 성립하지 않는다."),
  dict(id="X9", severity="LOW", kind="파급 경고를 재현하지 못했다",
       between=["gimbal G1 breaks_what (h 를 키우면 댐핑판이 기수 위로 삐져나온다)",
                "이번 라운드 측정"],
       measured=dict(damper_plate_now_mm=NC["gimbal_helper"]["current"]["damper_plate"],
                     damper_plate_after_G1G2_mm=NC["gimbal_helper"]["G1_G2"]["damper_plate"],
                     shell_body_z_in_that_footprint_mm=[-19.88, 63.96],
                     lowest_shell_face_above_z0_mm=1.25),
       adjudication="측정(바운딩박스 수준). 진짜 안/밖 판정은 아니다.",
       ruling="G1 의 장애물은 «삐져나온다» 가 아니라 «CAD 크래들 띠(z≈−20…+8)를 벗어나 뜻을 잃는다» 다. "
              "그래도 요·판 z 를 h 에서 떼어내라는 처방 자체는 유지한다.",
       why_ko="h=61.2 로 올리면 댐핑판이 z 33.09~39.21 로 간다. 그 발자국(x 117.6~164.4, |y|≤25.4)의 "
              "셸 body 면은 z −19.88~+63.96 에 걸쳐 있어 39.21 은 여전히 셸 높이 안이다. "
              "⚠ 나는 bbox 포함만 봤지 면 안/밖을 광선으로 판정하지는 않았다."),
  dict(id="X10", severity="LOW", kind="비용 표가 저장값과 2배 어긋난다",
       between=["benchmark/regen_mesh_dependents.py:81 (rcs_anchor 11407 s)",
                "outputs/rcs_anchor.json meta.runtime_s (22997.2 s)"],
       adjudication="파일 판독.",
       ruling="비용 추정에는 큰 쪽(22997 s ≈ 6.4 h)을 쓴다. 계획표 상수를 고칠 것."),
]

# ══════════════════════════════════════════════════════════════════════════
# 적용 순서
# ══════════════════════════════════════════════════════════════════════════
ORDER = [
  dict(step=0, name="게이트 — 코드 변경 없음", items=["N4", "P3"],
       why_ko="둘 다 «어느 것이 옳은가» 가 미정이다. N4 가 뒤집히면 N1·N2·N3 이 전부 틀린 자리를 "
              "고치는 일이 되고, P3 는 어느 쪽으로 가든 mini5pro 의 배율 sz 를 다시 푼다. "
              "필요한 것은 계산이 아니라 **1차 출처**다.",
       cost="사람 시간. GPU 0"),
  dict(step=1, name="mini2 — M1 + M2", items=["M1", "M2"],
       why_ko="결합이 정확히 0 인 유일한 후보다(key=='mini2' 분기 안, sz 불변). 검사 하네스를 "
              "가장 싼 패치로 한 번 완주해 본다. 다른 9기가 비트동일로 남는지가 여기서 증명된다.",
       must_stay_bit_identical="mini2 를 뺀 9기 전부",
       cost="메쉬 재빌드 + 해시 검사 ≈ 100 s(측정) · GPU 0"),
  dict(step=2, name="matrice4e 기수 — N1(잘라서) → N2 → N3", items=["N1", "N2", "N3"],
       why_ko="한 커밋이어야 한다. X2 가 보였듯 따로 넣으면 중간 상태가 지금보다 나쁘다. "
              "N1 의 x 상한은 짐벌 조립체 앞끝(117.62 mm)이다.",
       must_stay_bit_identical="matrice4e 를 뺀 9기 전부",
       gate="N4 통과"),
  dict(step=3, name="matrice4e 짐벌 — G1+G2+G3 (G4 는 보류)", items=["G1", "G2", "G3"],
       why_ko="요 실린더·댐핑판의 z 를 h 에서 떼어내는 helper 수술이 선행한다. G4 는 4E 깊이 근거가 "
              "없고 바닥유령 계열을 흔들므로 근거가 생길 때까지 미룬다.",
       must_stay_bit_identical="matrice4e 를 뺀 9기 전부"),
  dict(step=4, name="프롭 갈래 — P2 → P1 → P5 → P4", items=["P2", "P1", "P5", "P4"],
       why_ko="P2(벨 높이 이중정의)를 먼저 없애야 P1 이 읽을 «벨 윗면» 이 하나로 정해진다. "
              "P1 이 들어가면 프롭이 벨에서 유도되므로, 나중에 벨을 움직이는 어떤 작업도 "
              "프롭을 자동으로 데려간다 — prop_gap 라운드의 N7 과 같은 결론이다.",
       must_stay_bit_identical="없음 — 10기 전부 움직인다(x500v2 는 tube 분기라 P1 영향 밖, 확인 필요)"),
  dict(step=5, name="mini5pro — P3 결정 적용", items=["P3"],
       why_ko="X4 가 잰 대로 mini5pro 는 프롭이 배율을 되먹인다(다리 접지 0.784 mm/mm). "
              "P1 이 먼저 들어가 있어야 이 변화가 «프롭 자리» 한 곳에서만 나온다.",
       gate="P3 1차 출처 확보"),
  dict(step=6, name="matrice4e 다리 비대칭 — R3", items=["R3"],
       why_ko="⭐ **마지막**. 엔진 시그니처가 바뀌고 프레임 최저점이 움직여 sz 가 다시 풀린다. "
              "P1 이 들어가 있으면 프롭이 저절로 따라오므로 프롭을 두 번 손대지 않는다. "
              "R1·R2 는 여기서도 손대지 않는다.",
       must_stay_bit_identical="matrice4e 를 뺀 9기 전부"),
]

# ══════════════════════════════════════════════════════════════════════════
# 적용 전후 검사 목록
# ══════════════════════════════════════════════════════════════════════════
VERIFY = dict(
  before=[
    dict(id="B1", check="기준선 지문 고정",
         how="이 파일의 baseline_fingerprints 를 그대로 쓴다(drone_sha16 · frame_sha16 · prop_sha16 · sigma_cache_fp).",
         pass_when="패치 전 재계산 결과가 이 표와 전부 일치"),
    dict(id="B2", check="소스 파일 해시 기록",
         how="_meta.source_guard 의 sha256_16 을 커밋 메시지에 남긴다",
         pass_when="편집 시작 시점의 부모 해시가 이 값"),
    dict(id="B3", check="패치가 건드릴 기체를 **미리 선언**한다",
         how="apply_order 의 must_stay_bit_identical 을 커밋 전에 적는다",
         pass_when="선언과 실제가 일치(사후에 정하면 검사가 아니다)"),
    dict(id="B4", check="«간격» 과 «돌출» 의 기준면을 문서에 못 박는다",
         how="X8·gimbal open_questions 참조",
         pass_when="docs 에 정의가 있고 두 라운드가 같은 말을 쓴다"),
  ],
  after=[
    dict(id="A1", severity="⛔ 필수", check="손대지 않을 기체의 메쉬가 비트동일인가",
         how="열 기체 전부 build_drone/build_frame/build_propeller 를 다시 해시해 baseline 과 대조",
         pass_when="선언한 대상만 바뀌고 나머지는 sha16 3종이 전부 동일",
         cost_s=100.0,
         why_ko="공용 리터럴을 잘못 건드리면 여기서만 잡힌다. X6 이 보였듯 «공용처럼 보이지만 아닌» "
                "경우도, 그 반대도 있다."),
    dict(id="A2", severity="⛔ 필수", check="watertight · 안쪽법선 0 · 자기교차",
         how="src/mesh_check.py (엔진에 이미 있다)",
         pass_when="패치 전과 같거나 나아진다. **나빠지면 중단**",
         why_ko="N1(신설 파트)·R3(엔진 시그니처)는 새 면을 만든다. 안쪽을 향한 면은 예외를 안 내고 σ 만 틀린다."),
    dict(id="A3", severity="⛔ 필수", check="bbox 대 공표제원",
         how="drones.frame_envelope_mm(spec) 를 10기 전부",
         pass_when="공표값이 있는 축은 오차가 커지지 않는다",
         why_ko="⚠ 이 지표는 실루엣과 **같은 종류로 눈이 먼다** — 뜬 부품도 빈 자리도 앞뒤 비대칭도 못 본다. "
                "통과했다고 결함이 없다는 뜻이 아니다(ground Q5, floating R4)."),
    dict(id="A4", severity="⛔ 필수", check="fit 배율 sz 가 1.0 에 가까워지는가",
         how="frame_fit_scale(spec)[2] 를 10기 전부, baseline 과 나란히",
         pass_when="matrice4e 는 0.999873 근처를 유지(R3 전까지 불변이어야 한다). "
                   "mini5pro 는 P1/P3 에서 **반드시 움직인다** — 안 움직이면 패치가 안 걸린 것이다",
         predicted=dict(mini5pro_d_sz_per_mm_prop=IL["B_mini5pro_prop_drives_gear"]["d_sz_per_mm_prop"],
                        matrice4e_d_sz_per_mm_leg=IL["A_matrice4e_gear_drives_prop"]["d_sz_per_mm_leg"]),
         why_ko="sz 는 «맞았다» 의 지표가 아니라 «강제로 눌렀다» 의 지표다. 1.0 에서 멀면 엔진 형상이 "
                "공표 외형과 다르다는 뜻이고, 1.0 이라고 형상이 맞는 것은 아니다."),
    dict(id="A5", severity="⭐⭐ 이번 라운드의 핵심", check="프롭이 **실제로** 움직였는가",
         how="build_drone(spec) 의 `prop` **그룹 정점**의 z 최소/최대/평균을 baseline 과 대조",
         pass_when="P1·P3·P4·P5 이후 prop 그룹 z 가 예측한 만큼 이동",
         trap_ko="⛔ **build_propeller(spec) 를 보면 안 된다.** 소스를 읽어 확인했다 — build_propeller 는 "
                   "prop_z 를 인자로 받지 않고, rotor_layout 이 배율(sx,sy,sz)을 **로터 중심에만** "
                   "곱한다(drones.py rotor_layout · build_drone). 그래서 프롭 갈래를 전부 고쳐도 "
                   "prop_sha16 은 **바뀌지 않는다**. prop_sha16 을 지켜보는 검사는 아무 일도 "
                   "안 일어났는데 통과한다. 마이크로도플러가 보는 것은 프롭의 **자리**다.",
         baseline_field="baseline_fingerprints[*].prop_group_z_mm · prop_group_centroid_z_mm"),
    dict(id="A6", severity="⛔ 필수", check="σ 캐시 지문이 정확히 패치 대상 기체만 바뀌었는가",
         how="benchmark/channel.py::_mesh_fp 를 10기 전부",
         pass_when="선언한 기체만 지문이 바뀐다",
         why_ko="A1 과 겹쳐 보이지만 다르다. A1 은 우리 해시, 이건 **σ 파이프라인이 실제로 쓰는** 지문이다."),
    dict(id="A7", severity="필수", check="어안 부양이 닫혔는가",
         how="하방 어안쌍 정점 → 나머지 메쉬 최단거리(이 파일 nose_conflict 와 같은 방법)",
         pass_when="N1+N2+N3 이후 baseline 8.7712 mm 에서 **줄어든다**. 중간 상태는 검사하지 않는다",
         baseline_mm=var("baseline")),
    dict(id="A8", severity="필수", check="새 겹침이 생기지 않았는가",
         how="신설 크래들 상자·프롭 허브·벨 캡의 겹침 삼각형 수를 센다",
         pass_when="패치 전보다 늘지 않는다",
         why_ko="build_drone 은 merge 만 하고 불리언 합집합을 하지 않는다(prop_gap N6). 겹친 면은 "
                "살아남아 가림 없는 PO 경로가 두 번 적분한다 — mini5pro 는 이미 526 삼각형이 그 상태다."),
    dict(id="A9", severity="권장", check="실루엣 점수는 **판정에 쓰지 않는다**",
         how="계속 찍되 합격 조건에서 뺀다",
         why_ko="floating 이 직접 래스터화해 보인 대로 정면·상면 IoU 변화가 문자 그대로 0.000 이고, "
                "prop_gap 이 6.66 mm 를 통째로 닫아도 면적은 −2.21~+0.18 % 만 움직인다. "
                "이 결함들에 대해 실루엣은 침묵한다."),
  ])

# ══════════════════════════════════════════════════════════════════════════
# 무효화 목록
# ══════════════════════════════════════════════════════════════════════════
INVALIDATION = dict(
  how_counted=dict(mesh_reading_scripts=D["mesh_readers"]["n_files"],
                   command=D["mesh_readers"]["how"],
                   outputs_mentioning_a_drone=len(D["output_index"]),
                   note_ko="115개 스크립트가 메쉬를 읽는다. 전부가 σ 를 계산하지는 않지만, "
                           "«이 목록 밖» 이라고 말하려면 파일을 열어 봐야 한다."),
  tiers=[
    dict(tier="A", severity="⛔ 헤드라인 숫자가 움직인다",
         items=[
           dict(f="outputs/rcs_anchor.json", why="절대 σ 앵커·분포적합. 메쉬가 바뀌면 앵커가 바뀌고 "
                                                 "그 위의 모든 dBsm 이 따라 움직인다",
                cost_s=22997.2, cost_basis="meta.runtime_s"),
           dict(f="outputs/report13_sigma_grid.json (+ .matrice4e/.mavic4pro/.mini5pro/.phantom4/.s1000plus, _elext)",
                why="자세×밴드 σ 격자. 저장값이라 지문이 없어 **조용히 낡는다**",
                cost_s=570.0, cost_basis="meta.runtime_s (⚠ σ 캐시가 살아 있을 때만. 메쉬가 바뀌면 아래 참조)"),
           dict(f="outputs/report13_freespace.json", why="검지거리 4단계 — σ 를 그대로 먹는다",
                cost_s=564.9, cost_basis="meta.runtime_s"),
           dict(f="outputs/sigma_anchor.json · measurement_plan.json", why="측정 앵커 재보정",
                cost_s=60.0, cost_basis="planner est"),
           dict(f="outputs/das_fleet_ours.json · das_fleet_spec/validation/box_control/prereg/attack",
                why="함대 단위 비교 — matrice4e·mini2·mini5pro 가 전부 든다",
                cost_s=683.4, cost_basis="verification._meta.runtime_s"),
           dict(f="outputs/report15_* (verdict · probe · null_control · po_control · sionna_sweep · attack_*)",
                why="matrice4e·mini2 형상을 직접 굽는다", cost_s=4600.0,
                cost_basis="report15_sionna_sweep_matrice4e grid 3594.9 + shape_invariance 1005.9"),
           dict(f="outputs/report16_* (base · metric_* · rung_* · verify_* · synthesis)",
                why="표적 사다리 — mesh_full/half_tri/no_rotor 팔이 전부 메쉬를 읽는다",
                cost_s=1200.0, cost_basis="meta.seconds 합산(22~85 s × 12 arm) + 여유"),
           dict(f="outputs/report00_microdoppler.json", why="⭐ 마이크로도플러 사례편. matrice4e·mini2 "
                                                            "두 기체가 다 패치 대상이다",
                cost_s=None, cost_basis="report15_verdict/probe 재생성에 종속"),
           dict(f="outputs/mesh_compare_photo.json · mesh_compare_cad.json · mesh_compare_material.json",
                why="실물 대조 점수 — 형상이 바뀌면 점수가 바뀐다", cost_s=3038.4, cost_basis="_meta.runtime_s"),
           dict(f="outputs/report02_derived.json · report05_derived.json · report06_derived.json · report1.json",
                why="리포트 본문 표·그림이 읽는 파생 JSON", cost_s=120.0, cost_basis="planner est"),
           dict(f="outputs/sigma_sensitivity.json · sigma_robust_summary.json · sigma_grid_regen.json · sigma_regen_impact.json",
                why="σ 민감도·강건성 요약", cost_s=60.0, cost_basis="이전 라운드 실측 0.79~23.6 s"),
           dict(f="outputs/mono_link.json · mono_vs_passive.json · verify_monostatic.json",
                why="모노스태틱 대조가 σ 를 곱한다", cost_s=60.0, cost_basis="이전 라운드 실측"),
           dict(f="outputs/geometry_grid.json · geometry_benchmark.json",
                why="σ 를 읽는 칸만(순수 기하 칸은 무영향)", cost_s=60.0, cost_basis="이전 라운드 실측"),
         ]),
    dict(tier="B", severity="⚠ 그림·문서가 낡는다(숫자는 A 를 따라간다)",
         items=[
           dict(f="outputs/figures/report02_* · report05_* · report06_* · report13_* · mesh_gallery_*.png",
                why="전부 위 JSON 에서 나온다", cost_s=2000.0, cost_basis="planner 그림 단계 합"),
           dict(f="outputs/mesh_gallery.json + 갤러리 PNG 8장", why="형상 그림", cost_s=44.4,
                cost_basis="_meta.runtime_s"),
           dict(f="docs/MESH_VALIDATION.md · GEOMETRY_BENCHMARK.md · DRONE_SPECS.md · ENGINE_VALIDATION.md",
                why="형상 상수를 인용한다", cost_s=None, cost_basis="사람 시간"),
           dict(f="docs/drone_specs_2026.json specs[matrice4e].silhouette «30~40 mm 돌출»",
                why="⭐ 짐벌 라운드가 근거 없는 추정으로 판정했다. 지우거나 «미검증» 으로 표시할 것",
                cost_s=None, cost_basis="사람 시간"),
           dict(f="assets/photos/matrice4e/SOURCES.md:115 (p01 라벨)",
                why="X7 — 두 라운드가 다른 각도라고 적었다", cost_s=None, cost_basis="사람 시간"),
           dict(f="assets/photos/mini2/SOURCES.md:126,128,129",
                why="M2 — 문서 정정 4건", cost_s=None, cost_basis="사람 시간"),
           dict(f="outputs/meshfix_*.json (applied · attack · matrice4e · mini2 · x500v2)",
                why="옛 라운드의 판정이 이 명세로 갱신된다(F7·D02·D07·D08·D14)", cost_s=None,
                cost_basis="사람 시간"),
           dict(f="decks/* 중 형상 숫자를 인용한 슬라이드", why="발표물", cost_s=None, cost_basis="사람 시간"),
         ]),
    dict(tier="C", severity="영향 없음(그렇게 판정한 이유를 적어 둔다)",
         items=[
           dict(f="outputs/verify_eca.json · verify_cfar.json · verify_ambiguity.json · verify_observability.json",
                why="검출기 쪽. σ 는 곱셈 오프셋이라 문턱·Pfa 교정에 안 들어간다"),
           dict(f="outputs/prior_*.json · reference_library.json · reflib_read.json",
                why="선행연구 조사물 — 우리 메쉬를 안 읽는다"),
           dict(f="outputs/x500v2_score_v3.json · meshfix_x500v2.json",
                why="x500v2 는 arm_shape=='tube' 분기라 P1 의 접이식 식 밖에 있다. "
                    "⚠ 단 P5(스탠드오프 필드)가 spec 레코드를 건드리면 _FIT_CACHE 키가 바뀐다 — 확인 필요"),
           dict(f="outputs/anchor_subband*.json · p3_*.json",
                why="phantom3 전용. P1·P2·P5 가 phantom3 을 건드리면 **C 에서 A 로 올라간다**"),
         ]),
  ],
  hazard_ko="⭐ 가장 위험한 것은 목록에 없는 것이 아니라 **낡아도 소리를 안 내는 것**이다. "
            "σ 조회표는 메쉬 지문이 있어 저절로 미스가 나지만(X5), 저장된 격자 파일들은 지문이 "
            "없어 옛 형상 위의 숫자를 그대로 인용하게 된다. 적용 커밋에 그 파일들의 "
            "«어느 메쉬로 만들었는가» 를 찍는 일을 같이 넣을 것.",
)

# ══════════════════════════════════════════════════════════════════════════
# 비용
# ══════════════════════════════════════════════════════════════════════════
COST = dict(
  anchors=dict(
    planner=dict(file="benchmark/regen_mesh_dependents.py --list",
                 stages=29, serial_hours=9.1,
                 caveat_ko="σ 디스크캐시가 **살아 있을 때**의 값이다"),
    cold_cache_note_ko="같은 계획표의 경고: 메쉬를 고쳐 σ 캐시가 무효화되면 σ 격자 단계가 "
                       "9분 30초에서 **기종별 2.3~9.8 h × 5종 ≈ 23 h(GPU 분산)** 로 뛴다. "
                       "이번 패치는 전부 메쉬를 바꾸므로 **항상 이쪽**이다.",
    measured=dict(rcs_anchor_s=22997.2, report13_sigma_grid_s=570.0, report13_freespace_s=564.9,
                  das_fleet_ours_s=683.4, mesh_compare_photo_s=3038.4,
                  report15_sionna_sweep_matrice4e_s=4600.7, md_range_sweep_s=2929.6,
                  mesh_gallery_s=44.4, report16_base_s=22.1, report16_metric_mesh_full_s=85.3,
                  ten_drone_rebuild_and_hash_s=100.0),
  ),
  by_patch_group=[
    dict(group="mini2 (M1+M2)", drones=["mini2"],
         mesh_s=100, gpu_h_low=1.5, gpu_h_high=3.0,
         why_ko="mini2 는 report15/16 사다리와 das_fleet 에 든다. σ 격자 5종에는 안 든다."),
    dict(group="matrice4e 기수+짐벌 (N1·N2·N3·G1·G2·G3)", drones=["matrice4e"],
         mesh_s=100, gpu_h_low=8.0, gpu_h_high=14.0,
         why_ko="matrice4e 는 σ 격자 5종 중 하나이고 report15/16 의 주인공이다. "
                "σ 격자 기종 하나가 차가운 캐시에서 2.3~9.8 h 다."),
    dict(group="프롭 갈래 (P1·P2·P4·P5) — 전 기체", drones=["10기 전부"],
         mesh_s=100, gpu_h_low=26.0, gpu_h_high=34.0,
         why_ko="σ 격자 5종이 전부 미스가 난다(≈23 h) + rcs_anchor 6.4 h + 나머지."),
    dict(group="mini5pro (P3)", drones=["mini5pro"],
         mesh_s=100, gpu_h_low=3.0, gpu_h_high=10.0,
         why_ko="σ 격자 5종 중 하나. 프롭 갈래와 같은 커밋에 넣으면 추가 비용은 0 이다."),
    dict(group="matrice4e 다리 비대칭 (R3)", drones=["matrice4e"],
         mesh_s=100, gpu_h_low=8.0, gpu_h_high=14.0,
         why_ko="matrice4e 만. 단 엔진 시그니처가 바뀌므로 회귀 검사가 따로 붙는다."),
  ],
  totals=dict(
    if_split_into_five_commits=dict(gpu_h_low=46.5, gpu_h_high=75.0,
                                    why_ko="같은 σ 격자를 다섯 번 다시 굽는다"),
    if_one_commit=dict(gpu_h_low=30.0, gpu_h_high=40.0,
                       why_ko="⭐ σ 격자·rcs_anchor 를 **한 번만** 굽는다. 이것이 권고다"),
    wall_clock_note_ko="지금 쓸 수 있는 카드는 사실상 GPU2 한 장뿐이다(측정: GPU0 17.4/24.6 GB · "
                       "GPU1 19.8/24.6 · GPU2 1.5/24.6 · GPU3 20.4/24.6 — GPU3 은 금지). "
                       "한 장이면 30~40 GPU-h 가 그대로 벽시계 시간이다. 카드가 풀리면 "
                       "σ 격자는 기종별로 쪼개져 분산되므로 3~4장에서 10~14 h 로 준다.",
    what_is_free_ko="검사 자체는 공짜다 — 열 기체 재빌드+해시가 100 초, mesh_check 와 "
                    "frame_envelope_mm 은 그보다 싸다. 비싼 것은 오직 σ 재생성이다.",
  ),
  recommendation_ko="⭐ 게이트(N4·P3 1차 출처)를 통과시킨 뒤 **한 커밋**으로 다 넣고 σ 를 한 번만 다시 굽는다. "
                    "다만 커밋 안에서 단계별로 A1~A8 검사를 돌려, 어느 변경이 무엇을 움직였는지 "
                    "메쉬 수준에서는 분리해 둔다(메쉬 검사는 공짜다). σ 수준의 분리까지 원하면 "
                    "비용이 1.5~2.5배가 된다 — 그 값을 치를 이유가 있는지 먼저 물을 것.",
)

# ══════════════════════════════════════════════════════════════════════════
# 다섯 라운드에 대한 정정 — 내가 반증했거나 고쳐야 할 것
# ══════════════════════════════════════════════════════════════════════════
CORRECTIONS_TO_ROUNDS = [
  dict(round="floating", claim="σ 캐시 키에 형상 지문이 없다(D14) → 캐시를 지우지 않으면 옛 값이 재사용된다",
       verdict="REFUTED (2026-08-03 이후 사실이 아니다)", evidence="X5 · sigma_cache_check"),
  dict(round="floating", claim="0.009 는 mavic4pro·mini5pro 도 쓰는 공용 리터럴(:2155, :2288)",
       verdict="PARTLY WRONG — 2288 은 0.008 이고, 셋 다 각자 분기 안의 별도 리터럴이다",
       evidence="X6"),
  dict(round="floating", claim="곁가지 C3 — CAD 네 발이 −60.043(앞)/−59.80(뒤), 저장소 −59.82 는 둘 다 아니다",
       verdict="REFUTED — −60.043 은 B-스플라인 면의 OCC 바운딩박스다", evidence="X3 · ground Q1"),
  dict(round="floating", claim="F22 단독 적용으로 뜬 거리가 11.18 → 5.72 mm 로 줄기만 한다",
       verdict="CONFIRMED(방향) — 내 눈금으로는 8.77 → 5.82 mm", evidence="X2"),
  dict(round="floating", claim="F24(반지름 축소)는 부양과 무관한 별개 항목",
       verdict="REFUTED — 단독 적용하면 부양이 8.77 → 13.37 mm 로 **나빠진다**", evidence="X2"),
  dict(round="gimbal", claim="h 를 키우면 댐핑판이 기수 위로 삐져나온다",
       verdict="NOT REPRODUCED (bbox 수준) — 판은 z 39.21 로 가고 그 자리 셸은 63.96 까지 있다. "
               "처방(요·판 z 를 h 에서 분리)은 유지",
       evidence="X9"),
  dict(round="gimbal", claim="docs/drone_specs_2026.json 의 «30~40 mm 돌출» 은 근거 없는 추정",
       verdict="CONFIRMED — 그 파일 sources 에 치수 기입 도면이 없고 verification 항목이 짐벌을 안 다룬다",
       evidence="gimbal claim_trace"),
  dict(round="ground", claim="현 GEAR_SPIKE_H 를 건드리면 sz 가 바뀌어 메쉬 전체가 세로 재배율된다",
       verdict="CONFIRMED — 다리 1 mm 당 sz −0.00669, 벨 윗면 −0.150 mm",
       evidence="X4 · interlocks.A"),
  dict(round="ground", claim="뒷발 접지 z",
       verdict="INTERNALLY INCONSISTENT — 본문 −59.6090 · 후보표 −59.6149 (0.006 mm). 결론 무영향",
       evidence="X3 residual"),
  dict(round="mini2", claim="엔진의 bw 는 70.04109 mm 이고 F7 이 66.85 와 섞었다",
       verdict="CONFIRMED — 렌즈 자리를 직접 재니 y=7.5434 mm 로 계산과 소수 넷째 자리까지 같다",
       evidence="mini2_check"),
  dict(round="prop_gap", claim="viz_verify_sbr.py:188 의 하드코딩 사본을 같이 안 고치면 "
                               "«수정 전/후» 비교 그림이 거짓이 된다",
       verdict="AMBIGUOUS — 그 함수의 docstring 은 «frame_fit_scale 이 없던 시절» 만을 재현한다고 "
               "선언한다. 그 계약대로면 prop_z 는 따라가야 하고, 따라가면 그 그림의 «수정 전» 값이 "
               "바뀐다. 어느 쪽이든 **의도를 문서에 적고** 고를 것",
       evidence="src/viz_verify_sbr.py:180-193"),
  dict(round="prop_gap", claim="matrice4e 간격 6.656 mm",
       verdict="CONFIRMED(정의 안에서) — 다른 기준면(프롭 메쉬 최저점)으로 재면 3.2614 mm 다. "
               "기준면을 먼저 못 박을 것",
       evidence="X8"),
]

OPEN_BLOCKERS = [
  dict(id="N4", question="matrice4e 하방 어안이 좌우 한 쌍인가 앞뒤 한 쌍인가",
       need="4E 저면 정투영 사진 또는 4E 서비스 매뉴얼 도해. CAD 는 4T 이고 사진은 원근 렌더다",
       blocks=["N1", "N2", "N3"]),
  dict(id="P3", question="mini5pro 앞 모터가 뒤보다 14 mm 낮다는 1차 출처",
       need="drones.py:221 주석의 «조사 확인» 이 무엇을 봤는지. 없으면 rotor_z_mm 철회가 기본값",
       blocks=["P3"]),
  dict(id="X7", question="assets/photos/matrice4e/p01 은 좌측면인가 후면인가",
       need="파일을 열어 p05 와 대조. prop_gap 의 블레이드면 측정이 여기에 얹혀 있다",
       blocks=["P1(standoff 값의 근거)", "SOURCES.md 를 인용한 모든 값"]),
  dict(id="P4", question="프롭 허브 밑면인가 블레이드 중립면인가 — 그리고 «간격» 의 기준면",
       need="정의를 문서에 못 박기. 옵션 A 는 새 겹침을 만들고 옵션 B 는 잔차 1.66 mm 를 남긴다",
       blocks=["A7 검사의 합격 조건", "P1 의 standoff 부호"]),
  dict(id="G4", question="4E 짐벌 깊이", need="4E 정투영 측면 사진. 이 폴더에 없다", blocks=["G4"]),
]

# ══════════════════════════════════════════════════════════════════════════
D["evidence_grades"] = GRADES
D["candidates"] = CANDIDATES
D["conflicts"] = CONFLICTS
D["apply_order"] = ORDER
D["verification"] = VERIFY
D["invalidation"] = INVALIDATION
D["cost"] = COST
D["corrections_to_the_five_rounds"] = CORRECTIONS_TO_ROUNDS
D["open_blockers"] = OPEN_BLOCKERS
D["counts"] = dict(candidates=len(CANDIDATES), conflicts=len(CONFLICTS),
                   apply_steps=len(ORDER), checks_before=len(VERIFY["before"]),
                   checks_after=len(VERIFY["after"]),
                   corrections_to_rounds=len(CORRECTIONS_TO_ROUNDS),
                   open_blockers=len(OPEN_BLOCKERS),
                   mesh_reading_scripts=D["mesh_readers"]["n_files"])
D["headline_ko"] = (
  "18개 후보 중 **적용 2개(mini2)·조건부 6개(matrice4e)·보류 3개·기각 2개·차단 2개**. "
  "충돌 10건 중 진짜로 갈라야 하는 것은 셋이다 — ① 크래들과 짐벌이 같은 부피를 두고 다투고(X1), "
  "② 어안 반지름 축소는 단독으로 넣으면 부양을 **더 키우며**(X2, 측정), "
  "③ 접지와 프롭은 배율 sz 를 통해 얽혀 있는데 그 화살표가 matrice4e 와 mini5pro 에서 "
  "**서로 반대**다(X4, 측정). 그리고 이번 라운드가 새로 잡은 함정: 프롭 갈래를 전부 고쳐도 "
  "`build_propeller` 의 해시는 **안 바뀐다** — 프롭의 모양이 아니라 자리가 바뀌기 때문이다. "
  "그 해시를 지켜보는 검사는 아무 일도 안 일어났는데 통과한다.")

json.dump(D, open(SPEC, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("updated", SPEC, os.path.getsize(SPEC) // 1024, "KB")
print(json.dumps(D["counts"], ensure_ascii=False))
