# -*- coding: utf-8 -*-
"""outputs/mesh_inspect_internal_metal_0816.json 를 쓴다."""
import json

OUT = "/workspace/sionna/outputs/mesh_inspect_internal_metal_0816.json"

d = {}

d["_meta"] = {
    "title": "내부 금속(배터리·PCB·모터·냉각) 정밀 검토 — 2026-08-16",
    "scope": ("프로펠러 **밖**의 내부 금속 축만 본다. 프롭(시위·피치·두께)은 다른 라운드가 정본이므로 "
              "이 원장은 손대지 않는다."),
    "rules_followed": ["GPU 미사용 — 전부 numpy/trimesh CPU. Mitsuba·Sionna RT import 없음",
                       "git 명령 0회",
                       "메쉬 생성 코드(src/drones.py · src/drone_cad.py) **무변경** — 기본 동작 그대로. "
                       "변형 메쉬는 측정 프로세스 안에서만 만들었고 저장하지 않았다",
                       "새로 만든 것은 **읽기 전용 검사기 파일 하나**뿐이다(benchmark/mesh_internal_metal_check.py)"],
    "engine_note": ("σ 는 전부 **순수 PO**(rcs_po, engine='po')로 쟀다. PO 는 자기차폐가 없다"
                    "(rcs_po.py 자기선언) — 내부 부품 기여는 **상한**으로 읽어야 한다. "
                    "기본 엔진 SBR 은 GPU 가 필요해 이 라운드에서 못 돌렸다."),
    "sigma_convention": ("표기는 전부 **방위평균 σ [dBsm]**, az 0~358° 2° 간격 180점, "
                         "fc 3.5 GHz, 점간격 λ/7, 재질 |Γ| 는 materials.MATERIALS 그대로."),
    "gamma_used": {"metal(battery·motor)": 0.9998026802895116, "pcb": 0.80,
                   "camera_assembly": 0.85, "plastic(body·canopy·gear·accent)": 0.28,
                   "prop_plastic": 0.25, "carbon(arm)": 0.90,
                   "how": "ITU metal(εr=1, σ=1e7 S/m) 은 프레넬로 직접 유도 — 문서에 적힌 0.99980 과 "
                          "소수 5자리까지 일치. 나머지는 MATERIALS 의 gamma_po 값 그대로."},
    "elevation_caveat": ("el −90 은 시선 벡터가 방위와 무관하게 (0,0,−1) 하나뿐이라 **방위평균이 아니라 "
                         "단일 코히런트 측정**이다. 간섭에 극도로 민감하니 인용하지 말 것. "
                         "나디르 밴드가 필요하면 **el −80**(방위 180점 평균)을 쓴다."),
    "sources": {
        "cad": "assets/meshes/reference/matrice4-M4T_v2.step (DJI 공식 STEP, **외장 모델** — 내부 보드·블로어 없음)",
        "published": "docs/drone_specs_2026.json (DJI User Manual 원문 대조 기록 포함)",
        "teardown_photos": "assets/photos/matrice4e/t01~t16 (JANGYAO M4T 분해영상 프레임)",
        "prior_ledger": "outputs/meshfix_matrice4e.json (F11·F12) · docs/MESH_AUDIT_0816.md",
    },
    "new_tool": "benchmark/mesh_internal_metal_check.py (읽기 전용 검사기, 결과 outputs/mesh_internal_metal_check_0816.json)",
    "how_to_reproduce": ["PYTHONPATH=src python benchmark/mesh_internal_metal_check.py --json outputs/mesh_internal_metal_check_0816.json",
                         "σ 실험은 src/rcs_po.py 를 그대로 부르고 변형 상자만 프로세스 안에서 붙였다 — "
                         "재현 절차는 이 원장의 각 항목 method 에 적었다."],
    "concurrency_warning": ("⚠ 이 라운드 도중 **다른 세션이 같은 저장소를 편집했다** — "
                            "src/drone_cad.py(12:11 UTC) · src/drones.py(12:08) · src/materials.py(12:01) · "
                            "src/mesh_check.py(11:43) 의 mtime 이 내 작업 시간대 안에 있다(프로펠러 라운드로 보인다). "
                            "그래서 편집 **전후로 같은 측정을 돌려 대조**했다 — matrice4e PO 방위평균 σ 가 "
                            "12:07(편집 전)과 12:13(편집 후)에 **비트동일**이었고"
                            "(el0 −16.003 · el−30 −21.201 · el−60 −19.564 · el−80 −12.759), "
                            "봉인 검사 수치도 소수점까지 재현됐다. _SHELL_SHAPE['matrice4e'] · "
                            "INTERNALS['matrice4e'] 는 변하지 않았다. ⇒ 이 원장의 수치는 편집의 영향을 "
                            "받지 않았다. ⭐그래도 인용할 때는 **src/drone_cad.py 의 그날 상태**를 함께 확인할 것."),
}

# ── ① «정면 139 cm² 금속 거울» 해부 ─────────────────────────────────────────
d["front_metal_mirror"] = {
    "question": "0° 익사 서사의 주역 «정면 139 cm² 금속 거울(배터리·카메라·기판)» 이 실물과 맞나",
    "how_measured": ("az_falsify_ours.py ④ 와 **같은 경로**(FastPoser 자세, 같은 rotor_phases)로 "
                     "메쉬를 세우고 시선에 수직인 삼각형을 골라 **그룹별로** 나눴다."),
    "reproduced": {"az0_el0_front_only_cm2": 69.673, "n_tri": 90,
                   "note": "감사 I10④ 의 앞면 69.67 cm² 를 독립적으로 그대로 재현했다(양면 139.35 의 정확히 1/2)."},
    "decomposition_az0_el0": {
        "battery": {"area_cm2": 32.853, "share_pct": 47.2, "n_tri": 4,
                    "coherent_plates_cm2": [28.054, 4.799],
                    "plate_limit_sigma_dbsm": -18.58,
                    "what": "배터리 팩 앞면(60.6×46.3) + 구조판 앞면(67.6×7.1)"},
        "camera": {"area_cm2": 34.140, "share_pct": 49.0, "n_tri": 84,
                   "coherent_plates_cm2": [15.615, 10.404, 6.850, 1.271],
                   "plate_limit_sigma_dbsm": -21.64,
                   "what": "⭐**내부 금속이 아니다** — 밖에 달린 짐벌 카메라 블록이다"},
        "pcb": {"area_cm2": 2.680, "share_pct": 3.8, "n_tri": 2,
                "coherent_plates_cm2": [2.680], "plate_limit_sigma_dbsm": -39.10,
                "what": "메인보드 상자 앞면(53.6×5.0)"},
    },
    "verdict_wording": ("«배터리·카메라·기판» 이라는 나열은 **순서는 맞고 무게가 틀렸다**: "
                        "기판은 면적의 **3.8 %**(σ 로는 배터리보다 20.5 dB 아래)이고, "
                        "**절반(49 %)은 내부 금속이 아니라 외부 짐벌**이다. "
                        "내부 금속만 세면 35.53 cm² 다."),
    "is_it_a_mirror": {
        "lambda2_cm2": 73.37,
        "largest_single_coherent_plate_cm2": 28.054,
        "plate_over_lambda2": 0.382,
        "specular_null_check": {"L_mm": [60.6, 46.3], "lambda_over_L": [1.414, 1.851],
                                "reading": "둘 다 1 을 넘는다 ⇒ 가시영역 안에 **첫 널이 없다**. "
                                           "즉 이 판의 정반사 로브는 좁지 않다 — 광학 거울이 아니다."},
        "formula_validity": ("σ=4πA²/λ² 는 A ≫ λ² 에서만 옳다. 여기서 A/λ² = 0.38 이라 "
                             "**공식의 적용 한계 위**다. 위 plate_limit_sigma_dbsm 은 상한 표시로만 쓸 것."),
    },
    "does_our_sigma_care": {
        "test": "내부 상자 3개를 통째로 피치 1°·3° 기울여 PO σ 를 다시 쟀다(축정렬이 만든 것인지 확인)",
        "delta_db_pitch1": {"el0": 0.001, "el-30": -0.287, "el-60": 0.171, "el-80": -0.146},
        "delta_db_pitch3": {"el0": 0.001, "el-30": -0.294, "el-60": 0.240, "el-80": -0.234},
        "reading": ("⭐ 축정렬을 깨도 우리 σ 는 **el0 에서 0.001 dB**, 다른 밴드에서도 0.29 dB 안이다. "
                    "즉 «시선에 수직인 삼각형 90 장» 은 **거울/이미지소스 방식 솔버(Sionna PathSolver)의 "
                    "정반사 조건을 진단하는 수**이지 우리 σ 를 설명하는 수가 아니다. "
                    "리포트에서 이 면적을 σ 서사의 근거로 쓰면 엔진을 섞는 것이다."),
    },
    "other_aspects": {
        "az45_el0": {"n_tri": 2, "area_cm2": 0.097, "groups": ["canopy"]},
        "az0_el-30": {"n_tri": 0, "area_cm2": 0.0},
        "az0_el-60": {"n_tri": 0, "area_cm2": 0.0},
        "az0_el-90": {"n_tri": 360, "area_cm2": 306.190,
                      "by_group_cm2": {"battery": 184.147, "pcb": 49.848, "camera": 34.994,
                                       "prop": 16.306, "canopy": 12.503, "motor": 6.893, "accent": 1.500}},
        "reading": "el −30·−60 에서 수직 삼각형이 **정확히 0** 인 것이 위 판정을 뒷받침한다.",
    },
    "position_and_size_check": {
        "battery_front_face_x_mm": 69.84,
        "cad_battery_bay_front_x_mm": 70.10,
        "delta_mm": 0.26,
        "published_size_mm": [145.47, 60.6, 46.3],
        "mesh_size_mm": [145.47, 60.6, 46.29],
        "verdict": "matrice4e 배터리의 **치수와 앞뒤 위치는 맞다**(공표 제원 그대로, CAD 베이와 0.26 mm).",
    },
    "gamma_weighted_forward_budget_az0_el0": {
        "note": "조명면 투영면적[cm²] × |Γ| (코히런트 아님 — 위상 다 맞았을 때의 상한 배분)",
        "lit_projected_area_cm2_total": 422.18,
        "shares_pct": {"plastic_shell+canopy+gear": 38.6, "camera(gimbal)": 24.7,
                       "internal_metal+motor": 27.7, "prop": 8.9},
        "reading": "정면에서 내부 금속의 몫은 **약 1/4~1/3** 이지 «전부» 가 아니다.",
    },
}

json.dump(d, open("/tmp/claude-0/-workspace/e9e31991-b542-4f3a-b8e2-570320d555ba/scratchpad/part1.json", "w"),
          ensure_ascii=False, indent=1)
print("part1 ok")
