# -*- coding: utf-8 -*-
import json
d = json.load(open("/tmp/claude-0/-workspace/e9e31991-b542-4f3a-b8e2-570320d555ba/scratchpad/part2.json"))

# ── ⑤ 공표 부품치수 대조 ────────────────────────────────────────────────────
d["published_vs_mesh"] = {
    "method": "축을 크기순으로 정렬해 비교한다(상자 방향이 다를 수 있어서). 최대면 dB 는 평판극한 σ∝A².",
    "matrice4e": {
        "published_mm": [145.47, 60.6, 46.3], "mass_g": 400, "wh": 99.5,
        "source": "DJI Matrice 4 Series User Manual v1.2 p.103 · C2 표 (BPX345-6741-14.76)",
        "mesh_mm": [145.47, 60.6, 46.29], "err_pct": [0.0, 0.0, 0.0],
        "verdict": "✅ **정확히 일치**. 치수 축은 손댈 것이 없다.",
    },
    "mini5pro": {
        "published_mm": [86.10, 54.89, 24.85], "mass_g": 71.2, "wh": 19.52,
        "source": "DJI Mini 5 Pro User Manual p.86-87 · DJI 스펙 페이지 (저장소가 원문 대조까지 마친 값)",
        "mesh_mm": [68.98, 45.95, 32.17],
        "err_pct_sorted_axes": [-19.9, -16.3, 29.5],
        "volume_ratio": 0.868, "largest_face_ratio": 0.671, "largest_face_db": -3.47,
        "why": "mini5pro 는 drone_cad.INTERNALS 표에 **없어서** 공용 비율상자 경로를 탄다 "
               "(bl·0.50, bw·0.62, bh·0.55). 즉 이 기체의 최대 산란체가 형상 비율 추측이다.",
        "sigma_cost_measured": {
            "baseline_dbsm": {"el0": -19.488, "el-30": -22.682, "el-60": -23.478, "el-80": -22.850},
            "swap_to_published_box_same_place_delta_db":
                {"el0": -1.172, "el-30": 0.533, "el-60": 0.362, "el-80": 6.176},
            "also_move_to_rear_top_delta_db":
                {"el0": -1.348, "el-30": 0.183, "el-60": 2.946, "el-80": 11.309},
            "caveat": "«rear_top» 자리(−30, 0, +14)는 실물 서술(«윗면 뒤쪽 절반이 배터리 상면»)에서 "
                      "**내가 고른 값**이지 측정이 아니다. 인용은 same_place 쪽(+6.18 dB @ el−80)으로 할 것.",
        },
        "severity": "치명",
        "verdict": ("⭐**이 라운드에서 가장 큰 실행가능 dB.** 실측 표적 1순위인 Mini 5 Pro 의 배터리가 "
                    "공표 치수와 −20 %/−16 %/+30 % 어긋나 있고, 나디르 밴드(el−80) σ 가 **6.2 dB** 달라진다. "
                    "공표값이 저장소 안에 이미 원문 대조까지 끝난 채로 있다."),
    },
    "mavic4pro": {
        "published_mm": None, "mass_g": 332, "wh": 95.3,
        "source": "DJI 는 Mavic 4 Pro 배터리 **외형치수를 공개하지 않는다**(에너지·질량만).",
        "mesh_mm": [101.99, 73.21, 46.19],
        "verdict": ("치수 대조 불가 — **모른다**. 다만 **자리**는 성격이 다르다: 실물은 «동체 뒤쪽 윗면 "
                    "절반이 배터리 껍데기» 인 등짐형인데 우리 상자는 중심 z=+1.7 mm(중간 높이)에 있다. "
                    "부피만은 자기일관적이다(95.3 Wh / 345 cm³ = 276 Wh/L, matrice4e 244 Wh/L 와 같은 급)."),
        "severity": "중요",
    },
}

# ── ⑥ 재질 — 배터리는 통짜 금속 상자인가 ─────────────────────────────────────
d["battery_material"] = {
    "question": "배터리 팩 **외피 전체**를 ITU metal(|Γ|=0.9998)로 두는 것이 맞나",
    "current": "DRONE_GROUP_MAT['battery'] = 'metal' — 상자 6면 전부 |Γ|=0.99980",
    "reality": ("실물 팩은 **플라스틱 케이스 + 그 안의 셀 스택**이다. 전파를 되쏘는 것은 셀의 "
                "알루미늄 라미네이트/캔이지 케이스 바깥면이 아니다."),
    "how_much_smaller_is_the_metal": {
        "method": "질량·에너지 밀도로 셀 스택 부피를 **역산**한다(측정 아님 — 가정 명시).",
        "assumptions": ["고에너지 파우치 셀 체적 에너지밀도 600~700 Wh/L", "셀 밀도 2.2~2.5 g/cm³"],
        "matrice4e": {"envelope_cm3": 408.1, "pack_mass_g": 400, "pack_density_g_cm3": 0.98,
                      "cell_volume_cm3_est": [142, 166], "cell_share_of_envelope": [0.35, 0.41]},
        "mini5pro": {"envelope_cm3": 117.4, "pack_mass_g": 71.2, "pack_density_g_cm3": 0.606,
                     "cell_volume_cm3_est": [28, 33], "cell_share_of_envelope": [0.24, 0.28]},
        "caveat": "⚠ 이것은 **추정이다**. 셀 포맷·화학을 DJI 가 공개하지 않는다. 다만 팩 밀도가 "
                  "0.6~1.0 g/cm³ 로 셀 밀도의 절반 이하라는 것 자체가 «상당한 공동» 을 말해 준다.",
    },
    "sigma_cost_measured": {
        "engine": "순수 PO, 방위평균",
        "matrice4e_baseline_dbsm": {"el0": -16.003, "el-30": -21.201, "el-60": -19.564, "el-80": -12.759},
        "inset_3mm_walls_139.5x54.6x40.3_delta_db": {"el0": -1.308, "el-30": -1.134, "el-60": -0.611},
        "cell_stack_136x52x25_delta_db": {"el0": -2.932, "el-30": -1.090, "el-60": -0.662, "el-80": -1.807},
        "cell_stack_130x50x22_delta_db": {"el0": -3.418, "el-30": -1.566, "el-60": -0.855, "el-80": -1.003},
        "reading": ("«팩 외피 = 통짜 금속» 가정의 값은 **1.1~3.4 dB 과대** 쪽이다. "
                    "정면(el0)에서 가장 크다 — 정면 거울의 절반이 배터리 앞면이기 때문."),
    },
    "verdict": ("⚠ **미해결로 선언한다.** 지금 고치지 않는 이유: 셀 스택의 실제 치수가 1차 출처 0 이고, "
                "추정으로 줄이면 «측정 아닌 값» 을 또 하나 심는다. 대신 **모든 절대 σ 인용에 "
                "«배터리는 팩 외피 전체를 금속으로 본 값(상한 쪽 1~3 dB)» 단서를 붙일 것.**"),
    "severity": "중요",
}

# ── ⑦ 확인됨 — 손댈 것 없는 것 ──────────────────────────────────────────────
d["verified_ok"] = {
    "matrice4e_battery_dimensions": "공표 145.47×60.6×46.3 을 메쉬가 그대로 낸다(오차 0.00 %).",
    "matrice4e_battery_fore_aft_position": "팩 앞면 x=+69.84 ↔ CAD 배터리 베이 앞끝 +70.10 (0.26 mm).",
    "matrice4e_pcb_containment": "메인보드 상자 93×53.6×5 는 셸 안에 **완전히** 들어 있다(밖 0.00 cm²).",
    "mavic4pro_and_phantom4_containment": "두 기체는 내부 금속이 100 % 셸 안이다(밖 0.00 cm²).",
    "motors": ("모터 4개 = 지름 27.0 mm · 높이 16.3 mm 금속 원통. CAD 실측(지름 26.9, 높이 16.53/16.13)과 "
               "0.4 %/1.4 % 안 — meshfix F14 로 이미 정정돼 있다. 표면적 79.23 cm². **손댈 것 없다.**"),
    "internal_boxes_are_watertight": "battery·pcb 상자는 전부 수밀이고 중복면·퇴화면 0.",
    "pcb_material": ("pcb 그룹 |Γ|=0.80(=FR-4 위 구리 그라운드플레인의 실효값). 분해사진 t06·t07 의 "
                     "메인보드가 실제로 **차폐캔으로 거의 전면을 덮은** 보드라 «구리면이 지배» 라는 "
                     "재질 서술과 어긋나지 않는다."),
    "sigma_insensitivity_to_box_alignment": "내부 상자를 3° 기울여도 방위평균 σ 는 0.29 dB 안(el0 0.001 dB).",
}

# ── ⑧ 수리 명세(적용 안 함) ─────────────────────────────────────────────────
d["fix_spec_not_applied"] = {
    "why_not_applied": ("이 라운드의 규약이 «코드 기본 동작 변경 금지» 이고, INTERNALS 를 고치면 "
                        "모든 하류 σ 가 조용히 바뀐다(측정치로 0.2~1.1 dB). 게다가 같은 파일"
                        "(src/drone_cad.py)을 프로펠러 라운드가 동시에 만지고 있어 동시편집 위험이 있다. "
                        "그래서 **명세만 남기고 적용은 재계산 층이 순서대로** 한다."),
    "apply_order": ["1) 검사기부터 배선 — benchmark/mesh_internal_metal_check.py 를 회귀 게이트에 넣는다. "
                    "안 그러면 고쳐도 «되었는지» 확인할 방법이 없다(감사 0층 원칙).",
                    "2) N1 (matrice4e 구조판) — 가장 큰 기하 결함.",
                    "3) N2 (mini5pro 배터리 공표치수) — 가장 큰 dB.",
                    "4) 그 뒤에 σ 재계산. ⭐이 두 건은 report_mesh 의 재질·σ 절 수치를 바꾼다."],
    "N1": {
        "target": "src/drone_cad.py INTERNALS['matrice4e'] 세 번째 항목 (구조판)",
        "old": ["battery", [142.0, 67.6, 7.1], [-2.9, 0.0, -22.0]],
        "problem": "표면의 48.6 %(112.6 cm²)가 셸 밖, 최대 21.26 mm 돌출. 코·꼬리 면은 100 % 자유공간.",
        "measured_max_fit_mm": [69.6, 33.1, 7.1],
        "recommended": ("셸 안에 들어가는 크기로 줄이거나(중심 유지 시 최대 69.6 × 33.1 × 7.1), "
                        "z 를 올려(−22 → −14 근처) 셸 단면이 넓은 자리로 옮길 것. "
                        "⭐어느 쪽이든 **적용 후 mesh_internal_metal_check 를 다시 돌려 PASS 를 확인**한다."),
        "expected_sigma_shift_db": "0.2~1.1 (방위평균, 밴드에 따라 부호가 바뀜) — PO 실측",
        "honesty_note": "이 상자는 애초에 실측이 아니다. meshfix F12 가 «치수는 측정하지 않았다 … "
                        "리포트에 실측으로 적으면 안 된다» 고 스스로 선언한 엔진 손잡이다.",
    },
    "N2": {
        "target": "src/drone_cad.py INTERNALS 에 'mini5pro' 항목 신설",
        "recommended_battery_mm": {"size": [86.10, 54.89, 24.85],
                                   "source": "DJI Mini 5 Pro User Manual p.86-87(저장소 원문 대조 완료)"},
        "position": "⚠ **미정** — 실물은 «윗면 뒤쪽 절반이 배터리 상면» 인 등짐형이라 뒤·위로 가야 하는데, "
                    "정확한 x·z 는 이 라운드가 못 정했다. 자리를 정하기 전에 mini5pro 셸 단면과 "
                    "맞물리는지 검사기로 확인할 것.",
        "expected_sigma_shift_db": "el−80 +6.2 (자리 그대로 교체 시) · el0 −1.2 — PO 실측",
    },
    "N3": {
        "target": "matrice4e 배터리 팩의 옆·배·코 누출 21.09 cm²(최대 7.13 mm)",
        "recommended": "팩을 xy 로 0.85 배(123.6 × 51.5 × 46.3) 하면 셸 안에 들어간다 — 그러나 그러면 "
                       "**공표 치수를 버리게 된다.** 옳은 방향은 팩이 아니라 **셸 단면(hh/hw/zo)** 을 "
                       "다시 보는 것이다(팩 치수는 공표값이 정본이니까). 이 라운드는 셸 축을 안 건드렸다.",
        "severity": "중요 — 지금 고치지 말고 셸 라운드로 넘길 것",
    },
    "N4": {
        "target": "typhoonh480(36.1 %) · phantom3(18.2 %) · m350rtk(3.4 %) 노출",
        "recommended": "주력 표적 3종이 아니므로 이번 라운드 밖. 검사기가 이제 잡으니 목록만 넘긴다.",
    },
}

# ── ⑨ 모르는 것 ─────────────────────────────────────────────────────────────
d["not_settled"] = [
    "냉각 블로어의 **절대 치수·위치** — CAD 에 없고 분해사진에 축척 앵커가 없다. 비(ratio)만 남겼다.",
    "메인보드·차폐캔의 **절대 치수** — 같은 이유. 현재 pcb 상자 93×53.6×5 는 옛 비율상자를 옮긴 값이지 "
    "측정이 아니다(meshfix F12 가 그렇게 선언한다).",
    "배터리 **셀 스택**의 실제 치수 — 1차 출처 0. 질량·에너지 밀도 역산(35~41 %)은 추정이다.",
    "노출된 금속이 **SBR** 에서 얼마인지 — GPU 금지로 못 쟀다. 메커니즘(τ 관문을 건너뛴다)만 기록.",
    "mavic4pro 배터리 **외형치수** — DJI 미공개.",
    "mini5pro 배터리의 **정확한 자리** — 실물 서술(등짐형)만 있고 치수 기입 도면이 없다.",
    "mini2 는 셸이 수밀이 아니라 봉인 검사 자체가 **불가**(감사 I5 가 먼저다).",
    "다리 안테나의 **공진 산란** — 우리 커널의 표현 범위 밖(부하 걸린 도선). 2.4 GHz 팔에서 재검토.",
]

d["one_line"] = ("치수는 matrice4e 만 정확하고(공표값 그대로), **문제는 치수가 아니라 «어디에 있는가»** 였다 — "
                 "셸형 8기체 중 5기체가 내부 금속을 플라스틱 셸 밖으로 내밀고 있고 matrice4e 구조판은 "
                 "절반이 맨 금속으로 노출돼 있다. 반면 냉각 블로어는 후하게 잡아도 1.3 dB 이내라 "
                 "지금 넣을 이유가 없고, 다리 안테나는 3.5 GHz 에서 13~18 dB 아래다.")

json.dump(d, open("/workspace/sionna/outputs/mesh_inspect_internal_metal_0816.json", "w"),
          ensure_ascii=False, indent=1)
print("wrote outputs/mesh_inspect_internal_metal_0816.json")
