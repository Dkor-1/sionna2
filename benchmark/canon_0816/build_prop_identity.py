# -*- coding: utf-8 -*-
"""prop_identity_0816.json 생성 — 기체 10종이 «실제로 다는» 프로펠러의 신원 원장.

이 스크립트는 계산을 하지 않는다. 조사 결과를 한 곳에 못박아 두는 것이 전부다.
값의 출처는 전부 url 필드에 있고, 근거가 없는 칸은 null 로 남긴다(가짜 수로 채우지 않는다).
"""
import json
import datetime

DJI_TABLE = ("https://support.dji.com/help/content?customId=01700006559&spaceId=17"
             "&re=US&lang=en&documentType=&paperDocType=ARTICLE")

meta = {
    "generated_kst": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    "purpose_ko": (
        "기체 10종이 실제로 다는 순정 프로펠러의 «신원» — 제품 모델명·규격(지름×피치)·날 개수 — 을 "
        "1차 출처까지 붙여 확정한다. 형상(시위분포·두께)을 재는 것은 이 원장의 일이 아니고, "
        "여기서는 «그 형상을 어디서 얻어야 하는가»(best_source)와 그 등급만 정한다."),
    "why_ko": (
        "2026-08-16 재질 판정이 «움직이는 성분(AC)은 사실상 전부 프로펠러» 를 실측했고, "
        "감사(docs/MESH_AUDIT_0816.md I2)가 «날 폭 상수 CHORD_MAX_OVER_R=0.25 하나를 10기종 전부에 "
        "걸고 있다 — 실물은 0.177~0.273» 를 찾아냈다. 즉 지금은 모든 기체에 같은 프롭이 달려 있다. "
        "기종 비교(=분류)가 그 위에 서 있으므로, 먼저 «무엇이 달리는가» 를 확정해야 한다."),
    "scope_ko": "식별만 한다. 코드 무변경·GPU 미사용·git 미사용.",
    "primary_source_ko": (
        "DJI 공식 지원 문서 «Aircraft Propeller Materials, Dimensions, and Models» 한 장이 "
        "DJI 7기종(mini5pro·mavic4pro·matrice4e·phantom4·phantom3·m350rtk(간접)·mini2)의 "
        "모델명·재질·지름×피치를 동시에 못박는다. 이 원장의 뼈대다."),
    "primary_source_url": DJI_TABLE,
    "grading_scale": {
        "A":  "그 프롭 «자체» 의 3D 기하 — 제조사 공식 CAD/GLB",
        "A-": "그 프롭 자체의 3D 기하이긴 하나 제조사 공식임이 «문서로» 확인되지 않음(시뮬레이터 자산 등)",
        "B":  "그 프롭 «실물/공식 렌더» 사진의 정밀 계측(물리 스케일 또는 공칭 지름으로 축척 고정)",
        "B-": "같은 사진이지만 투영오차·겹침·워터마크로 정밀도가 떨어짐",
        "C":  "같은 계열 «다른» 프롭에서 유추(같은 회사·같은 세대)",
        "D":  "대리 — 다른 회사 프롭. 원장에 «대리» 라고 못박고 예상 오차를 함께 적는다",
    },
    "rules_ko": [
        "⛔엉뚱한 프롭을 입히지 마라. 크기만 늘린다고 같은 물건이 되지 않는다 "
        "(실측 c_max/R 이 크기와 반비례한다: 4.7 in 0.262 → 10.8 in 0.190).",
        "근거가 없으면 null 로 남긴다. 빈칸이 가짜 값보다 낫다.",
        "변종(표준/저소음 등)이 있으면 어느 쪽을 모사할지 정하고 이유를 적는다. 기본은 «순정 동봉품».",
    ],
}

A = {}

A["mini5pro"] = {
    "name": "DJI Mini 5 Pro",
    "is_primary_target": True,
    "prop": {
        "model": "6028F",
        "variants": [],
        "variant_note_ko": "DJI 공식 프롭 표에 Mini 5 Pro 는 6028F 한 줄뿐 — 저소음/표준 갈래가 없다.",
        "dia_mm": 152.4, "dia_in": 6.0,
        "pitch_mm": 71.12, "pitch_in": 2.8,
        "blades": 2, "folding": True,
        "mass_g_each": 2.8,
        "material_dji": "Nylon + Rubber",
        "part_number": "CP.MA.00000920.01 (1쌍 소매 SKU)",
    },
    "evidence": [
        {"grade": "official", "what_ko": "DJI 공식 프롭 표 행: «DJI Mini 5 Pro | 6028F | Nylon + Rubber | 15.2×7.1 cm»",
         "url": DJI_TABLE},
        {"grade": "official", "what_ko": "DJI 스토어 제품 페이지: «직경 × 나사산 피치: 152.4 mm x 71.12 mm (6.0 x 2.8″)», «무게(1개당): 약 2.8 g»",
         "url": "https://store.dji.com/product/dji-mini-5-pro-propellers"},
        {"grade": "secondary", "what_ko": "판매점 스펙 블록(part CP.MA.00000920.01, 6 x 2.8\" = 15.24 x 7.11 cm, 2.8 g)",
         "url": "https://volatusdrones.com/products/dji-mini-5-pro-propellers"},
        {"grade": "repo", "what_ko": "저장소 기존 링크(DRONE_SPECS.md §3)도 같은 값 — 6028F, 15.2×7.1 cm",
         "url": "https://support.dji.com/help/content?customId=en-us03400006559"},
    ],
    "registry_check_ko": "src/drones.py mini5pro: prop_dia_mm 152.4 ✓ · prop_pitch_in 2.8 ✓ · prop_blades 2 ✓ — 전부 공식과 일치.",
    "geometry": {
        "grade": "B",
        "best_source": "assets/photos/mini5pro/mini 5 pro_3.png — 프롭 4장 전개된 «상면 평면» 공식 렌더. 축척은 공칭 디스크 152.4 mm 로 고정.",
        "cross_check": "assets/photos/mini5pro/mini 5 pro_1.png (전방 3/4, 시위 확인용) — 투영 심해 계측용 아님.",
        "have_3d": False,
        "caveats_ko": [
            "DJI 는 Mini 5 Pro 3D 모델을 공개하지 않는다 — [A] 경로가 없다.",
            "⚠ 이 폴더에는 SOURCES.md 가 «없다». 사진 3장의 출처·해상도·촬영조건이 기록돼 있지 않다 "
            "(다른 폴더 8곳은 전부 있다). 계측 전에 출처를 먼저 적을 것.",
            "제품 «렌더» 지 사진이 아니다 — 날이 이상화됐을 수 있다. 오차 밴드를 넉넉히 잡을 것.",
            "⛔mini2(4726FM, 4.7 in) 평면형을 6.0 in 으로 늘려 쓰지 말 것 — c_max/R 이 크기와 반비례한다.",
        ],
        "expected_band_ko": "c_max/R 은 mini2 실측 0.262(4.7 in)와 mavic4pro 실측 0.181(10.5 in) 사이 — 6.0 in 이면 0.22~0.25 대로 «예상»되나 이는 추정이지 측정이 아니다.",
    },
}

A["mavic4pro"] = {
    "name": "DJI Mavic 4 Pro",
    "is_primary_target": True,
    "prop": {
        "model": "1158F",
        "variants": [],
        "variant_note_ko": "DJI 공식 표에 1158F 한 줄뿐. 소매 SKU 가 1158F-1 / 1158F-2 로 갈리는데 이는 CW/CCW(및 색: 실버/오렌지) 구분이지 형상 변종이 아니다.",
        "dia_mm": 267.0, "dia_in": 10.5,
        "pitch_mm": 147.0, "pitch_in": 5.8,
        "blades": 2, "folding": True,
        "mass_g_each": 11.8,
        "material_dji": "Enhanced Nylon Composite Material",
        "part_number": "CP.MA.00000844.01 (1쌍 소매 SKU)",
    },
    "evidence": [
        {"grade": "official", "what_ko": "DJI 공식 프롭 표 행: «DJI Mavic 4 Pro | 1158F | Enhanced Nylon Composite Material | 26.7×14.7 cm»",
         "url": DJI_TABLE},
        {"grade": "authorized_dealer", "what_ko": "DJI 공인 판매점 스펙 블록: «Diameter × Pitch: 10.5 inch × 5.8 inch (26.7 cm × 14.7 cm)», «Weight (single): 11.8 g»",
         "url": "https://dji-retail.co.uk/products/dji-mavic-4-pro-propellers"},
        {"grade": "repo", "what_ko": "저장소 사진 원장이 이미 1158F 로 파일명을 박아 두었다 (assets/photos/mavic4pro/SOURCES.md 151행)",
         "url": None},
    ],
    "registry_check_ko": "src/drones.py mavic4pro: prop_dia_mm 267 ✓ · prop_pitch_in 5.8 ✓(14.7 cm = 5.787 in) · prop_blades 2 ✓.",
    "geometry": {
        "grade": "B",
        "best_source": ("assets/photos/mavic4pro/mavic4pro_p01_fcc_top_plan_ruler.jpg — FCC 외관사진. "
                        "실기체 상면, 1158F 4장이 «로터면 안에서» 접혀 평평하게 누워 있어 평면형이 정면으로 보이고, "
                        "프레임 안에 «강철자 2개»(cm)가 같은 평면에 있다. 물리 스케일이 사진 안에 있는 유일한 1158F 자료다."),
        "cross_check": ("assets/photos/mavic4pro/mavic4pro_c10_propeller_pair_1158F.jpg — 프롭 1쌍 제품사진. "
                        "감사가 c_max/R 0.181 을 여기서 냈다. 다만 3/4 투영 + 워터마크라 단독 1차 근거로는 약하다. "
                        "mavic4pro_c11_propeller_hub_detail.jpg 는 허브(뿌리 끝단) 전용."),
        "have_3d": False,
        "caveats_ko": [
            "p01 은 접힌 자세다 — 힌지에서 돌아가 있을 뿐 «로터면 안» 이라 평면형은 보존된다. 다만 카메라가 정중앙이 아니라 원근 보정이 필요하다(자 2개로 국소 축척을 잡을 것).",
            "c10 의 0.181 은 투영오차를 안 뺀 값이다 — p01 로 다시 재서 두 값을 대조할 것.",
            "DJI 는 Mavic 4 Pro CAD 를 공개하지 않는다 — [A] 없음.",
        ],
        "expected_band_ko": "감사 실측 c_max/R 0.181 (재확인 대상).",
    },
}

A["matrice4e"] = {
    "name": "DJI Matrice 4E",
    "is_primary_target": True,
    "prop": {
        "model": "1157F",
        "variants": [
            {"model": "1157F", "role_ko": "표준(순정 동봉)", "dia_in": 10.8},
            {"model": "1154F", "role_ko": "저소음 — 별매 액세서리 «Matrice 4 Series Low-Noise Propellers (for C2)»", "dia_in": 10.8},
        ],
        "variant_decision_ko": (
            "⭐**1157F(표준)를 모사한다.** 근거 셋: "
            "(1) DJI 스펙 페이지가 이륙중량을 «표준 1219 g / 저소음 1229 g» 로 갈라 적는데 우리 레지스트리 weight_g 가 1219 다 — "
            "즉 저장소의 기존 기체 정의가 이미 표준 프롭 구성이다. "
            "(2) 박스 동봉품은 «프로펠러 3쌍» 이고 저소음은 별도 상품 페이지로 팔린다(순정 동봉 = 표준). "
            "(3) DJI 가 광고하는 49분/42분 호버는 표준 프롭 수치다. "
            "⚠ 유럽 C2 운용에서는 저소음이 사실상 기본이라는 서술이 저장소(assets/photos/matrice4e/SOURCES.md 38행)에 있으나 "
            "1차 출처가 붙어 있지 않다 — 미확인으로 남긴다."),
        "variant_cost_ko": "두 프롭은 같은 물건이 아니다: 감사 사진계측으로 날 면적 2411 → 3014 mm²(+25 %), c_max/R 0.190 → 0.212. 어느 쪽을 썼는지 안 적으면 σ·마이크로도플러가 갈린다.",
        "dia_mm": 274.0, "dia_in": 10.8,
        "pitch_mm": None, "pitch_in": None,
        "pitch_note_ko": "⚠ DJI 는 Matrice 4 계열 프롭의 «피치» 를 어디에도 공표하지 않는다(공식 표는 «10.8 inch» 만). "
                         "레지스트리의 prop_pitch_in=5.7 은 부품번호 1157F 의 뒷 두 자리를 피치로 읽은 «관례 해석» 이지 공표값이 아니다 — 등급 DERIVED.",
        "blades": 2, "folding": True,
        "mass_g_each": None,
        "material_dji": "Composite material",
        "part_number": None,
    },
    "evidence": [
        {"grade": "official", "what_ko": "DJI 공식 프롭 표 행: «Matrice 4E/4T | 1157F / 1154F | Composite material | 10.8 inch»",
         "url": DJI_TABLE},
        {"grade": "official", "what_ko": "DJI 엔터프라이즈 스펙 페이지: «1157F (표준 프로펠러)» · «1154F (저소음 프로펠러)», 이륙중량 1219 g(표준) / 1229 g(저소음), 최대비행 49분(표준) / 46분(저소음)",
         "url": "https://enterprise.dji.com/matrice-4-series/specs"},
        {"grade": "dealer", "what_ko": "저소음 1154F 는 «for C2» 별매 액세서리로 팔리고 표준 대비 소음 −3.5 dB 라고 적는다 — 즉 순정 동봉은 표준",
         "url": "https://www.heliguy.com/products/matrice-4-series-low-noise-propellers/"},
        {"grade": "dealer", "what_ko": "M4E 박스 동봉품에 «3x Propellers (Pair)» — 종류는 명시 안 됨",
         "url": "https://www.heliguy.com/products/dji-matrice-4e/"},
    ],
    "registry_check_ko": "src/drones.py matrice4e: prop_dia_mm 274 ✓(10.79 in) · prop_blades 2 ✓ · prop_pitch_in 5.7 은 DERIVED(공표 없음).",
    "geometry": {
        "grade": "B",
        "best_source": ("assets/photos/matrice4e/matrice4e_c02_prop_standard_1157F_pair.jpg — 표준 1157F 1쌍, "
                        "흰 배경에 날이 «정면으로 눕는» 거의 평면뷰. 감사가 여기서 날 4장을 재 ±1 % 로 일치시켰고 면적 2411±19 mm² 를 냈다. "
                        "축척은 공칭 디스크 274 mm 로 고정."),
        "cross_check": ("matrice4e_c01_prop_low_noise_1154F_pair.jpg(저소음 변종 — 대조군) · "
                        "matrice4e_p09_underside_plan.jpg / p10(기체에 장착·전개된 상태의 상면/저면 평면 렌더 — 허브 각도·장착 반경 확인용) · "
                        "matrice4e_m07_top_plan_prop_rotation_AB.png(매뉴얼 p.20, A/B 회전방향)."),
        "have_3d": False,
        "caveats_ko": [
            "⭐**공식 CAD 에 프로펠러가 없다.** assets/meshes/reference/matrice4-M4T_v2.step(솔리드 125)은 기체만이고 "
            "outputs/meshfix_matrice4e.json 이 «CAD 에 프롭이 없다» 고 이미 기록했다 — 주력 표적인데 [A] 경로가 막혀 있다.",
            "c01/c02 는 DJI 제품 이미지를 판매점 CDN 에서 받은 것 — 사진 안에 물리 자가 없다. 축척은 공칭 지름에 의존한다.",
            "두께는 사진으로 못 잰다 — matrice4e 실물 프롭 두께는 저장소에 실측이 «없다»(감사 ?2, 0.99~1.40 mm 로만 묶임).",
        ],
        "expected_band_ko": "감사 실측 c_max/R: 1157F 0.190 · 1154F 0.212 (재확인 대상).",
    },
}

A["s1000plus"] = {
    "name": "DJI Spreading Wings S1000+",
    "is_primary_target": False,
    "prop": {
        "model": "1552 / 1552R",
        "variants": [],
        "variant_note_ko": "1552(CW)와 1552R(CCW·역회전)은 같은 형상의 거울쌍이다. 옥토라 4+4 로 8장.",
        "dia_mm": 381.0, "dia_in": 15.0,
        "pitch_mm": 132.1, "pitch_in": 5.2,
        "blades": 2, "folding": True,
        "mass_g_each": None,
        "material_dji": "탄소섬유 강화 수지(접이식) — DJI 는 «stronger materials» 라고만 적는다",
        "part_number": "S1000+ Part 58 (프로펠러 팩)",
    },
    "evidence": [
        {"grade": "official", "what_ko": "DJI 뉴스룸 «DJI released the latest 1552 folding propeller»: «15 x 5.2 inch», 정격추력 1.2 kg·최대 2.8 kg, 신형 익형으로 효율 +10 %",
         "url": "https://www.dji.com/newsroom/news/dji-released-the-latest-1552-folding-propeller"},
        {"grade": "dealer", "what_ko": "S1000+ 전용 프로펠러 팩(Part 58) = 1552 접이 프롭 CW 4 + CCW 4 풀세트",
         "url": "https://www.buildyourowndrone.co.uk/dji-s1000-plus-propeller-pack"},
        {"grade": "repo", "what_ko": "레지스트리 note 가 1552 의 피치비 0.347 을 C_T 논증에 이미 쓰고 있다(hover_rpm 4467 정정 근거)",
         "url": None},
    ],
    "registry_check_ko": "src/drones.py s1000plus: prop_dia_mm 381 ✓ · prop_pitch_in 5.2 ✓ · prop_blades 2 ✓ · num_rotors 8 ✓.",
    "geometry": {
        "grade": "B-",
        "best_source": ("assets/photos/s1000plus/s1000+_1.png — 옥토 8장 전개된 상면 평면 이미지. "
                        "축척은 공표 대각 1045 mm 또는 공칭 디스크 381 mm 로 고정."),
        "cross_check": "assets/photos/s1000plus/s1000+_2.png",
        "have_3d": False,
        "caveats_ko": [
            "⚠ 이 폴더에도 SOURCES.md 가 «없다» — 두 이미지의 출처가 기록돼 있지 않다(워터마크 «XCOPTER» = 판매점 자산으로 보인다). 계측 전에 출처부터 적을 것.",
            "1552 는 «접이 탄소 블레이드 + 금속 브래킷» 이다 — 사출 소비자 프롭과 뿌리 형상이 근본적으로 다르다. 뿌리 쪽을 소비자 프롭 법칙으로 채우면 틀린다.",
            "단종 기체라 새 1차 자료를 구하기 어렵다. Part 58 판매 사진(단품 평면)이 더 나은 [B] 가 될 수 있다 — 아직 저장소에 없다.",
        ],
        "expected_band_ko": None,
    },
}

A["phantom4"] = {
    "name": "DJI Phantom 4 (원조, 2016)",
    "is_primary_target": False,
    "prop": {
        "model": "9450S",
        "model_repo_current": "9450",
        "variants": [
            {"model": "9450S", "role_ko": "퀵릴리즈 — Phantom 4 / 4 Pro / 4 Pro+ / 4 RTK", "dia_in": 9.4},
            {"model": "9455S", "role_ko": "⚠다른 기체용 — Phantom 4 Pro V2.0 / Multispectral 의 저소음 프롭(24 × 13.97 cm). P4 원조 것이 아니다.", "dia_in": 9.4},
        ],
        "variant_decision_ko": (
            "⚠**정정 후보**: 레지스트리는 «9450» 이라 적는데, 원조 Phantom 4(2016)가 실제로 동봉한 것은 "
            "**9450S 퀵릴리즈**다(P4 가 자동조임 9450 을 버리고 퀵릴리즈를 도입한 세대다). "
            "DJI 소매 부품이 «Phantom 4 Series Quick Release Propellers = 9450S», P4 Part 25(SKU CP.PT.000360.02), "
            "옵시디언판 Part 93 으로 팔린다. "
            "⛔단 **모순이 하나 있다**: DJI 자신의 프롭 표는 «Phantom 4 | 9450» / «Phantom Pro / 4 Advanced | 9450S» 로 적는다. "
            "두 갈래 다 공칭은 24 × 12.7 cm 로 같아서 «규격» 은 안 흔들리고, 갈리는 것은 **허브(자동조임 vs 퀵릴리즈)와 날 세부**뿐이다. "
            "→ 결론: 규격은 확정, 부품번호는 «9450S 유력·미해결» 로 남긴다."),
        "dia_mm": 240.0, "dia_in": 9.4,
        "pitch_mm": 127.0, "pitch_in": 5.0,
        "blades": 2, "folding": False,
        "mass_g_each": 11.0,
        "material_dji": "Glass fiber reinforced nylon",
        "part_number": "P4 Part 25 (CP.PT.000360.02) / Part 93 (Obsidian)",
    },
    "evidence": [
        {"grade": "official", "what_ko": "DJI 공식 프롭 표: «Phantom 4 | 9450 | Glass fiber reinforced nylon | 24 ×12.7 cm» · «Phantom Pro / 4 Advanced | 9450S | 24 ×12.7 cm» · «Phantom 4 Pro V2.0 / Multispectral | 9455S | 24 × 13.97 cm»",
         "url": DJI_TABLE},
        {"grade": "official_store", "what_ko": "DJI 스토어 «Phantom 4 Series Quick Release Propellers» = 9450S",
         "url": "https://store.dji.com/product/phantom-4-9450s-quick-release-propellers"},
        {"grade": "retail", "what_ko": "«DJI 9450S Quick Release Propeller Pair for Phantom 4 / Phantom 4 Pro / Phantom 4 Pro+», 1개 11 g, 24×12.7 cm, P4 Part 25 / Part 93",
         "url": "https://www.bhphotovideo.com/c/product/1236406-REG/dji_9450s_quick_release_propellers.html"},
    ],
    "registry_check_ko": "src/drones.py phantom4: prop_dia_mm 240 ✓ · prop_pitch_in 5.0 ✓ · prop_blades 2 ✓. 부품번호 문자열 «9450» 만 정정 후보(9450S).",
    "geometry": {
        "grade": "C",
        "best_source": ("[C] 같은 세대·같은 공칭(24 × 12.7 cm) 인 **phantom3 의 9450** 사진을 쓴다 — "
                        "assets/photos/phantom3/phantom3_p25_fccpro07_top_props_laid_tape.jpg(프롭 4장을 기체 옆에 평평히 눕히고 줄자 동봉) 와 "
                        "phantom3_p09_fccse_all_items_props_steelruler.jpg(강철자). 사진 안에 «물리 스케일» 이 있다."),
        "cross_check": "assets/photos/phantom2/phantom2_m03_manual_p2_v14_propeller_9450.png (매뉴얼 9450 도해)",
        "have_3d": False,
        "caveats_ko": [
            "⚠⚠**저장소의 phantom4 사진 폴더는 다른 기체다.** 파일명이 «Phantom 4 Pro+ V2.0» 이고, 그 기체는 **9455S**(24 × 13.97 cm, 저소음)를 단다 "
            "— 여기서 날 평면형을 재면 «다른 프롭» 을 P4 에 입히게 된다. 프롭 계측에 쓰지 말 것.",
            "9450(자동조임) vs 9450S(퀵릴리즈)는 허브가 다르고 날도 미세하게 다르다 — phantom3 사진을 쓰는 것은 «같은 계열 유추»[C]이지 그 프롭 자체가 아니다.",
            "phantom3 FCC 사진은 해상도가 낮다(640×480 / 1048×697) — 시위 정밀도 ±3~5 % 정도로 각오할 것.",
        ],
        "expected_band_ko": None,
    },
}

A["typhoonh480"] = {
    "name": "Yuneec Typhoon H (H480)",
    "is_primary_target": False,
    "prop": {
        "model": "Propeller A / Propeller B (Yuneec 부품번호 YUNTYH118A / YUNTYH118B)",
        "variants": [],
        "variant_note_ko": "헥사라 A 3장 + B 3장. A 는 허브 버튼이 검정·날에 «A» 각인, B 는 흰 버튼·«B» 각인이다. "
                           "⚠ Typhoon H **Plus**(520)는 다른 기체·다른 프롭이니 섞지 말 것.",
        "dia_mm": 228.6, "dia_in": 9.0,
        "pitch_mm": 152.4, "pitch_in": 6.0,
        "pitch_note_ko": "⚠ Yuneec 은 지름·피치를 한 번도 공표하지 않았다. 9.0 × 6.0 in 은 «호환 탄소 프롭 판매 스펙» 에서 온 것이라 등급 DERIVED 를 유지한다(레지스트리 note 와 동일 입장). 우리 CAD 실측 디스크는 230.19 / 230.95 mm 로 9.0 in 대비 +0.7 / +1.0 %.",
        "blades": 2, "folding": False,
        "mass_g_each": None,
        "material_dji": None,
        "part_number": "YUNTYH118A (A, 3 pcs) / YUNTYH118B (B, 3 pcs)",
    },
    "evidence": [
        {"grade": "manufacturer_shop", "what_ko": "Yuneec 유럽 공식 스페어파츠 상점: «Typhoon H Propeller \"A\" (3 pcs.)»",
         "url": "https://shop.yuneec.com/eu/spare-parts/typhoon-h/typhoon-h-propeller-a-3-pcs./"},
        {"grade": "retail", "what_ko": "OEM 부품번호 YUNTYH118A / YUNTYH118B (Typhoon H · H Pro 용). A=검정 버튼, B=흰 버튼",
         "url": "https://gravesrc.com/yuntyh118a-yuneec-propeller-rotor-blade-a-3-typhoon-h/"},
        {"grade": "repo", "what_ko": "저장소 CAD 실측: 디스크 230.19 mm(CW) / 230.95 mm(CCW), 날 2장 — assets/photos/typhoonh480/SOURCES.md §7",
         "url": None},
    ],
    "registry_check_ko": "src/drones.py typhoonh480: prop_dia_mm 230.2 (CAD 실측) · prop_pitch_in 6.0 (DERIVED) · prop_blades 2 ✓ · num_rotors 6 ✓.",
    "geometry": {
        "grade": "A-",
        "best_source": ("assets/meshes/reference/prop_cw_assembly_remeshed_v3.stl · prop_ccw_assembly_remeshed_v3.stl "
                        "— **그 프롭 자체의 3D 기하**. 출처 ethz-asl/rotors_simulator `typhoon_h480`(Apache-2.0), 단위 mm."),
        "cross_check": "assets/photos/typhoonh480/typhoonh480_y07_official_360.png · y01/y02 (공식 제품 이미지)",
        "have_3d": True,
        "caveats_ko": [
            "⚠**«Yuneec 공식 CAD» 라는 문서 근거가 없다.** 상류 저장소가 이 메쉬의 출처를 밝히지 않는다 — "
            "제조사 CAD 일 수도, 재현 모델일 수도 있다. 그래서 [A] 가 아니라 [A-] 다. "
            "저장소 문서가 이것을 «실물 CAD» 라고 부르는 문면은 이 한계를 적어 두는 게 정직하다.",
            "mini2 를 빼면 저장소에서 **기체별 프롭 3D 기하가 존재하는 유일한 기체**다 — 그래서 감사가 이걸 참조 밴드로 썼다(c_max/R 0.177).",
            "감사가 «Yuneec 형(늦게 정점 0.45R)» 이 DJI 실물과 닮았다고 했는데, 그 판정의 한쪽 끝이 바로 이 메쉬다 — 출처가 불확실하면 그 판정도 그만큼만 강하다.",
        ],
        "expected_band_ko": "기존 원장 outputs/reference_props.json: c_max/R 0.1769 @ r/R 0.450.",
    },
}

A["x500v2"] = {
    "name": "Holybro X500 V2",
    "is_primary_target": False,
    "prop": {
        "model": "1045",
        "variants": [],
        "variant_note_ko": "1045 는 특정 제조사 전용 부품이 아니라 «10 × 4.5 in» 를 뜻하는 범용 규격명이다 — 여러 회사가 같은 이름으로 판다. Holybro 킷 동봉품이 기준.",
        "dia_mm": 254.0, "dia_in": 10.0,
        "pitch_mm": 114.3, "pitch_in": 4.5,
        "blades": 2, "folding": False,
        "mass_g_each": None,
        "material_dji": "나일론/유리섬유 사출(셀프락킹)",
        "part_number": "Holybro «X500 V2 Kit — Propeller 1045»",
    },
    "evidence": [
        {"grade": "manufacturer", "what_ko": "Holybro 공식 킷 페이지 동봉품: «1045 Propellers (6 pcs) with retainer», 모터 «Holybro 2216 KV920 Motor (4 pcs)»",
         "url": "https://holybro.com/products/px4-development-kit-x500-v2"},
        {"grade": "dealer", "what_ko": "Holybro 스페어 «X500 V2 Kit - Propeller 1045 - 2 Pair»",
         "url": "https://www.readymaderc.com/products/details/85969-holybro-spare-parts-x500-v2-kit-propeller-1045-2-pair"},
        {"grade": "repo", "what_ko": "저장소가 이미 이 사실을 적어 두었다 — assets/meshes/reference/SOURCES.md 의 «X500 V2 킷은 1045(10×4.5 in = 254 mm)를 싣는다»",
         "url": None},
    ],
    "registry_check_ko": "src/drones.py x500v2: prop_dia_mm 254.0 ✓ · prop_pitch_in 4.5 ✓ · prop_blades 2 ✓.",
    "geometry": {
        "grade": "D",
        "best_source": ("⛔**현재 저장소에 1045 기하가 없다.** 지금 쓰이는 1345 STL 은 «다른 프롭» 이다 — "
                        "PX4-gazebo-models 의 13 in 급(실측 디스크 346.7 mm), 저장소 스스로 «X500 V2 의 프롭이 아니다» 라고 못박아 두었다. "
                        "→ 등급 [D] 대리. 예상 오차: 공칭 지름이 13 → 10 in 로 1.3 배 다르고 c_max/R 도 0.225(1345) 대 미지(1045)라 "
                        "시위분포를 그대로 쓰면 기종 비교가 오염된다."),
        "cross_check": ("승격 경로 [B]: assets/photos/x500v2/x500v2_10_prop_1045_on_2216.jpg(1045 + 2216 모터 근접) · "
                        "x500v2_01_arf_front34_props.jpg · x500v2_09_arf_iso34_props.jpg — 전부 투영이 있어 평면 계측엔 보정이 필요하다. "
                        "가장 확실한 길은 1045 단품의 평면 사진(또는 판매사 도면)을 새로 구하는 것."),
        "have_3d": False,
        "caveats_ko": [
            "⭐**Holybro 공식 STEP 에도 프로펠러가 없다** — assets/meshes/reference/x500v2-frame.step 의 부품명 57종을 전수 확인했고 "
            "(BOTTOM/TOP-PLATE-X500-V5 · CARBON-FIBER-TUBE · DJ-2216-KV880 · PCBA-PM06 …) 프롭에 해당하는 솔리드가 하나도 없다. "
            "즉 [A] 경로가 이 기체에도 막혀 있다.",
            "1045 는 범용 규격이라 «대리» 를 써도 죄가 가볍다 — 단 어느 회사 1045 를 썼는지 반드시 원장에 적을 것.",
        ],
        "expected_band_ko": None,
    },
}

A["phantom3"] = {
    "name": "DJI Phantom 3 Professional",
    "is_primary_target": False,
    "prop": {
        "model": "9450",
        "variants": [
            {"model": "9450 (ABS 자동조임)", "role_ko": "순정 동봉", "dia_in": 9.4},
            {"model": "9450 Carbon Fiber Reinforced", "role_ko": "DJI 가 별매한 «재질 갈래» — 같은 형상·다른 재질(레지스트리 note 가 이미 «MATERIAL FORK, UNCONTROLLED» 로 선언)", "dia_in": 9.4},
        ],
        "variant_decision_ko": "순정 동봉인 표준 9450(유리섬유 강화 나일론/ABS)을 모사한다. 탄소강화판은 형상이 아니라 재질 갈래라 |Γ| 축에서만 갈린다.",
        "dia_mm": 240.0, "dia_in": 9.4,
        "pitch_mm": 127.0, "pitch_in": 5.0,
        "blades": 2, "folding": False,
        "mass_g_each": 12.0,
        "material_dji": "Glass fiber reinforced nylon (DJI 표는 P3 행 재질을 비워 두고, 같은 부품의 P4 행이 이 재질)",
        "part_number": "E305 추진계 9450 자동조임(Self-tightening)",
    },
    "evidence": [
        {"grade": "official", "what_ko": "DJI 공식 프롭 표 행: «Phantom 3 Series | 9450 | 24 x 12.7 cm»",
         "url": DJI_TABLE},
        {"grade": "retail", "what_ko": "정품 «DJI Phantom 3 E305 9450 Self-tightening Propellers» — P3 Pro/Adv·P2 계열·Flame Wheel·E310/E305/E300 호환, 1개 12 g",
         "url": "https://www.amazon.com/DJI-self-tightening-Propellers-Professional-propulsion/dp/B0118AVD42"},
        {"grade": "repo", "what_ko": "레지스트리 note 가 이미 «DJI 자신의 E305 추진계 표에서 9450 = 24 × 12.7 cm» 를 VERIFIED 로 적고 있다",
         "url": None},
    ],
    "registry_check_ko": "src/drones.py phantom3: prop_dia_mm 240.0 ✓ · prop_pitch_in 5.0 ✓ · prop_blades 2 ✓.",
    "geometry": {
        "grade": "B",
        "best_source": ("assets/photos/phantom3/phantom3_p25_fccpro07_top_props_laid_tape.jpg — FCC 외관사진. "
                        "9450 4장을 기체 옆에 «평평히 눕히고» 줄자를 같이 찍었다 — 사진 안에 물리 스케일이 있는 몇 안 되는 자료."),
        "cross_check": "assets/photos/phantom3/phantom3_p09_fccse_all_items_props_steelruler.jpg (강철자, 1048×697)",
        "have_3d": False,
        "caveats_ko": [
            "해상도가 낮다(640×480 · 1048×697) — 이 자료로 낼 수 있는 시위 정밀도는 ±3~5 % 정도다. 그 밴드를 적어 둘 것.",
            "phantom4(9450S)와 «공칭이 같다» 는 것이지 같은 부품이 아니다 — 두 기체에 같은 날을 입히려면 그 판단을 원장에 적을 것.",
        ],
        "expected_band_ko": None,
    },
}

A["m350rtk"] = {
    "name": "DJI Matrice 350 RTK",
    "is_primary_target": False,
    "prop": {
        "model": "2110s",
        "variants": [
            {"model": "2110s", "role_ko": "표준(순정). M300 RTK·M350 RTK 공용. 2110 의 후속 — 형상 동일, 공정·QC 강화판", "dia_in": 21.0},
            {"model": "2112", "role_ko": "고고도 저소음 별매 «High-Altitude Low-Noise Propellers»", "dia_in": 21.0},
        ],
        "variant_decision_ko": "표준 **2110s** 를 모사한다(순정 동봉·기본 운용). 2112 는 고고도 옵션이라 우리 시나리오와 무관하다.",
        "dia_mm": 533.4, "dia_in": 21.0,
        "pitch_mm": 254.0, "pitch_in": 10.0,
        "blades": 2, "folding": True,
        "mass_g_each": None,
        "material_dji": "Composite material",
        "part_number": "CP.EN.00000470.01 (2110s 1쌍: CCW 1 + CW 1 + M3 나사 6)",
    },
    "evidence": [
        {"grade": "official_indirect", "what_ko": "DJI 공식 프롭 표: «Matrice M300 RTK | 2110 / 2195 | 21 × 10 inch / 21 × 9.5 inch». "
                                                  "2110s 는 그 2110 의 후속이고 DJI 가 M300 RTK·M350 RTK 공용이라고 밝힌다 ⇒ 21 × 10 in 이 DJI 자신의 수치로 앵커된다.",
         "url": DJI_TABLE},
        {"grade": "dealer", "what_ko": "«DJI 2110s Propellers for Matrice 300/350 RTK (Pair)», 구성 CCW 1 + CW 1 + M3 나사 6, 53 cm × 25 cm",
         "url": "https://www.bhphotovideo.com/c/product/1768807-REG/dji_cp_en_00000470_01_propellers_for_matrice_350.html"},
        {"grade": "dealer", "what_ko": "2112 고고도 저소음 별매 변종",
         "url": "https://www.dslrpros.com/products/dji-matrice-350-rtk-2112-highaltitude-lownoise-propellers-pair"},
    ],
    "registry_check_ko": ("src/drones.py m350rtk: prop_dia_mm 533.4 ✓(21 in) · prop_pitch_in 10.0 ✓ · prop_blades 2 ✓. "
                          "⭐note 가 이 값을 «SECONDARY, not DJI — DJI 는 모델명(2110s)만 내고 기하는 안 낸다» 로 등급 매겨 두었는데, "
                          "DJI 공식 프롭 표의 2110 행(21 × 10 inch) + 2110s 의 M300/M350 공용 선언으로 **한 등급 올릴 근거가 생겼다**."),
    "warnings": [
        "⛔**DJI 공식 표 자신의 오류 하나**: «Matrice 350 RTK | 1345S / 1345T» 라고 적혀 있는데 1345 는 13 인치 Inspire 1 프롭이다 — "
        "21 인치 기체에 물리적으로 맞지 않는다. 같은 표의 M300 RTK 행(2110/2195)과 DJI 의 2110s 상품 설명이 정답이다. "
        "이 행을 그대로 인용하면 새 오류를 만든다.",
    ],
    "geometry": {
        "grade": "B-",
        "best_source": ("assets/photos/m350rtk/m350rtk_c01_prop_2110s_pair.png — DJI 제품사진. 2110s 1쌍(CW+CCW)이 "
                        "**접힌 채** 날 면을 정면으로 보이고 있다. 바깥 날 하나는 평면형이 온전히 보이므로 시위분포를 잴 수 있다."),
        "cross_check": ("m350rtk_p05_folded_top_ruler.png · p06_folded_top_props_stowed_ruler.png — 접힌 날 «길이» 를 자로 교차검증할 수 있다"
                        "(레지스트리 note 가 «아직 그 용도로 안 썼다» 고 적어 둔 바로 그 사진이다). "
                        "d07_arm_tip_motor_prop_hub.jpg 는 허브·장착부."),
        "have_3d": False,
        "caveats_ko": [
            "접힌 상태라 두 날이 겹친다 — 안쪽 날은 못 잰다. 바깥 날 1장으로 재고 좌우 쌍으로 반복성만 확인할 것.",
            "사진 안에 물리 자가 없다 — 축척은 공칭 디스크 533.4 mm 에 의존한다. p05/p06 의 자로 교차검증하면 이 의존이 풀린다.",
            "이 기체 프롭은 «접이 브래킷 + 긴 탄소성 블레이드» 라 뿌리 형상이 소비자 사출 프롭과 다르다.",
        ],
        "expected_band_ko": None,
    },
}

A["mini2"] = {
    "name": "DJI Mini 2",
    "is_primary_target": False,
    "prop": {
        "model": "4726FM",
        "model_repo_current": "4726F",
        "variants": [
            {"model": "4726FM", "role_ko": "DJI 공식 표가 Mini 2 / Mini 2 SE 에 붙이는 이름 (11.94 × 6.6 cm)", "dia_in": 4.7},
            {"model": "4726F", "role_ko": "⚠같은 «4726» 이지만 DJI 표에서 **Spark** 행에 붙고 피치가 다르다(11.94 × 7.62 cm). 소매에서는 Mavic Mini 용으로도 이 이름이 돈다.", "dia_in": 4.7},
        ],
        "variant_decision_ko": (
            "**4726FM 으로 적는 것이 옳다.** DJI 공식 프롭 표가 «DJI Mini 2 / Mini 2 SE | 4726 FM | Nylon + Glass fiber | 11.94 × 6.6 cm» 라고 "
            "기체를 지목해 적는다. 저장소는 FCC 사진(mini2_t28)에서 «4726 F» 를 읽었다고 기록하는데, 내가 그 사진을 확대해 보니 "
            "각인은 «… B 4726 F?» 로 끝 글자가 하나 더 있는 것처럼 보인다 — **FM 과 모순되지 않는다**. "
            "다만 어두운 색 위 음각이라 마지막 글자를 «단정할 만큼» 읽히지는 않는다. 정직하게: DJI 표(1차)를 따르고, 사진은 «모순 없음» 까지만 적는다."),
        "dia_mm": 119.4, "dia_in": 4.7,
        "pitch_mm": 66.0, "pitch_in": 2.6,
        "blades": 2, "folding": True,
        "mass_g_each": None,
        "material_dji": "Nylon + Glass fiber",
        "part_number": None,
    },
    "evidence": [
        {"grade": "official", "what_ko": "DJI 공식 프롭 표 행: «DJI Mini 2 / Mini 2 SE | 4726 FM | Nylon + Glass fiber | 11.94 × 6.6 cm»",
         "url": DJI_TABLE},
        {"grade": "repo_photo", "what_ko": "FCC MT2WD 인증기 사진의 날 각인 — assets/photos/mini2/mini2_t28_fcc_mt2wd_propeller_motor_view.jpg (확대 확인함, «4726 F?» 로 읽히고 FM 과 모순 없음)",
         "url": None},
        {"grade": "repo_cad", "what_ko": "DJI 공식 3D 모델에서 잰 디스크 지름 118.6~119.9 mm(평균 119.2) ↔ 공식 11.94 cm = −0.2 %",
         "url": None},
    ],
    "registry_check_ko": (
        "src/drones.py mini2: prop_dia_mm 119.1(GLB 실측) ↔ DJI 공표 119.4 = **−0.25 %** ✓ · prop_blades 2 ✓. "
        "⭐**prop_pitch_in 2.6 이 승격된다** — note 는 이것을 «MEASURED, 밴드 2.0~3.0, 부품명 4726F 가 함의하는 2.6 과 우연히 일치» 라고 적는데, "
        "DJI 공식 표가 피치를 **6.6 cm = 2.598 in** 로 직접 공표한다. 이제 추정이 아니라 공표값이다."),
    "geometry": {
        "grade": "A",
        "best_source": ("assets/meshes/reference/WM161_zhankai_1k.glb — **DJI 공식 3D 모델**(WM161 = Mini 2 내부코드), "
                        "프롭 날 8장·허브 4개 실재. 단위 미터·숨은 축척 없음(59 노드 전부 SVD 1.0)·좌우 대칭 0.0000 mm. "
                        "저장소 함대 전체에서 **유일한 [A]** 다."),
        "cross_check": "assets/photos/mini2/mini2_c07_fcc_mt2wd_propeller_2blade_ruler.jpg (cm 자 동봉 — CAD 를 실물 사진으로 검증하는 독립 경로)",
        "have_3d": True,
        "caveats_ko": [
            "접힘판(wm161_v11_zhedie_1k.glb)은 공표치와 −0.25 / +2.62 / −3.27 % 로 덜 맞는다 — 형상은 **펼침판에서만** 잴 것.",
            "⭐**이 프롭을 다른 기체에 늘려 쓰지 말 것.** 4.7 in 짜리의 c_max/R 0.262 는 10.8 in 짜리 0.190 과 1.4 배 다르다 — "
            "감사가 «크기와 반비례» 를 실측했다. mini2 는 «자기 자신의» 1차 근거이자, 다른 기체에는 **[C] 유추 재료일 뿐**이다.",
            "DJI 저작물이라 파일 재배포 금지(내부 형상 근거용).",
        ],
        "expected_band_ko": "감사 실측 c_max/R 0.262(공식 CAD) / 0.272(사진).",
    },
}

corrections = [
    {"id": "P1", "target": "src/drones.py phantom4.note · docs/DRONE_SPECS.md §1 «프롭 부품번호»",
     "now": "«9450»",
     "should": "«9450S (퀵릴리즈)» — 단 DJI 자신의 프롭 표는 P4 행에 9450 을 적어 모순이 남는다. 공칭 24 × 12.7 cm 는 양쪽 동일하므로 규격은 안 흔들린다.",
     "impact_ko": "부품 신원만. 지름·피치·날 수는 그대로."},
    {"id": "P2", "target": "src/drones.py mini2.note(«4726F») · docs/DRONE_SPECS.md",
     "now": "«4726F»",
     "should": "«4726FM» (DJI 공식 표가 Mini 2 / Mini 2 SE 를 지목). 덤으로 **피치 2.6 in 이 MEASURED → 공표값(6.6 cm)으로 승격**되고 지름도 −0.25 % 로 대조된다.",
     "impact_ko": "신원 정정 + 등급 상승 2건."},
    {"id": "P3", "target": "src/drones.py m350rtk.note («prop 533.4 / 10.0 in / 2 blades is SECONDARY, not DJI»)",
     "now": "SECONDARY — «DJI 는 모델명만 내고 기하는 안 낸다»",
     "should": "DJI 공식 프롭 표의 **M300 RTK 행 «2110 → 21 × 10 inch»** + DJI 의 «2110s 는 M300/M350 공용» 선언으로 DJI 자신의 수치에 앵커된다 — 한 등급 올릴 근거. "
               "⛔단 같은 표의 «Matrice 350 RTK | 1345S/1345T» 행은 **DJI 의 오기**(1345 는 13 in Inspire 1 프롭)이니 인용 금지.",
     "impact_ko": "등급 상승. 값 자체는 변경 없음."},
    {"id": "P4", "target": "matrice4e — 어느 프롭을 모사하는가 (감사 미해결 ?3)",
     "now": "저장소에 기록 없음 (감사가 «표준인가 저소음인가 기록이 없다» 로 보류)",
     "should": "**1157F(표준)로 확정.** 근거: 레지스트리 weight_g=1219 가 DJI 의 «표준 프롭» 이륙중량이고(저소음은 1229), 저소음은 «for C2» 별매다. "
               "1154F 는 날 면적 +25 % 라 변종 표기를 spec note 에 남길 것.",
     "impact_ko": "감사 보류항목 ?3 해소."},
    {"id": "P5", "target": "assets/photos/phantom4/ 폴더의 용도",
     "now": "파일 5장 전부 «Phantom 4 Pro+ V2.0»",
     "should": "⚠**프롭 계측에 쓰지 말 것** — P4 Pro V2.0 은 9455S(24 × 13.97 cm, 저소음)를 단다. 우리 phantom4 는 원조 P4(9450S, 24 × 12.7 cm)다. "
               "폴더에 그 경고를 적을 것(현재 SOURCES.md 자체가 없다).",
     "impact_ko": "잘못된 프롭을 입히는 사고를 막는다."},
    {"id": "P6", "target": "assets/meshes/reference/SOURCES.md — Typhoon 프롭 STL 문면",
     "now": "«실물 3D CAD» / «Yuneec Typhoon H480 (실제 헥사콥터)»",
     "should": "«그 프롭의 3D 기하이나 **제조사 CAD 임이 문서로 확인되지 않았다**»(등급 A-). 상류 ethz-asl/rotors_simulator 가 출처를 밝히지 않는다.",
     "impact_ko": "감사가 이 메쉬를 «Yuneec 실물 참조 밴드» 로 쓴다 — 그 판정의 강도가 여기에 묶여 있다."},
]

open_q = [
    {"id": "Q1", "ko": "matrice4e·mavic4pro·mini5pro 셋 다 **프롭 3D 기하가 없다**(주력 표적 3종 전부). "
                       "DJI 가 Matrice 4 STEP 을 공개하지만 그 파일에 프로펠러가 빠져 있다 — 다른 공개 CAD 경로가 있는지는 아직 못 찾았다."},
    {"id": "Q2", "ko": "matrice4e 실물 프롭 **두께** 는 여전히 실측이 없다(감사 ?2, 0.99~1.40 mm). 사진으로는 못 잰다 — 실물 계측이나 단면 자료가 필요하다."},
    {"id": "Q3", "ko": "matrice4e 피치는 DJI 가 공표하지 않는다. 레지스트리 5.7 in 은 부품번호 «1157F» 의 뒷자리를 읽은 관례 해석이다 — "
                       "같은 관례가 mavic4pro(1158F → 5.8 in)에서는 DJI 공표 14.7 cm 와 맞아떨어지므로 «그럴듯» 하지만, matrice4e 에서는 확인되지 않았다."},
    {"id": "Q4", "ko": "mini5pro·s1000plus·phantom4 사진 폴더에 SOURCES.md 가 없다 — 사진의 출처·해상도·촬영조건이 미기록이다. "
                       "이 셋으로 형상을 재기 전에 출처부터 적어야 «재현 가능» 하다."},
    {"id": "Q5", "ko": "x500v2 의 1045 는 범용 규격이라 «어느 회사 1045 인가» 가 형상을 가른다. Holybro 동봉품의 단품 평면 사진/도면이 없다."},
    {"id": "Q6", "ko": "phantom4 = 9450 vs 9450S — DJI 자신의 두 기록(프롭 표 ↔ 소매 부품)이 어긋난다. 공칭은 같아 실무 영향은 작지만 미해결로 남긴다."},
]

summary_table = [
    {"key": k, "prop": A[k]["prop"]["model"],
     "dia_mm": A[k]["prop"]["dia_mm"], "pitch_in": A[k]["prop"]["pitch_in"],
     "blades": A[k]["prop"]["blades"], "geometry_grade": A[k]["geometry"]["grade"]}
    for k in ["mini5pro", "mavic4pro", "matrice4e", "s1000plus", "phantom4",
              "typhoonh480", "x500v2", "phantom3", "m350rtk", "mini2"]
]

doc = {"meta": meta, "summary": summary_table, "aircraft": A,
       "corrections_to_repo": corrections, "open_questions": open_q}

out = "/workspace/sionna/outputs/prop_identity_0816.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(doc, f, ensure_ascii=False, indent=1)
print("wrote", out, len(json.dumps(doc, ensure_ascii=False)), "chars")
for r in summary_table:
    print(f"  {r['key']:12s} {r['prop']:>34s}  {r['dia_mm']} mm  pitch {r['pitch_in']} in  x{r['blades']}  [{r['geometry_grade']}]")
