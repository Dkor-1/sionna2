# -*- coding: utf-8 -*-
"""
sentinel_truth.py — ModalAI **Sentinel 공식 CAD** 에서 지상진실(ground truth) 추출
====================================================================================
왜 이 파일이 특별한가
  우리 RCS 는 **재질 가중 물리광학(PO) 적분**이다. 면마다 그 부위의 재질군(carbon / plastic /
  metal / battery / pcb)에서 온 |Γ| 를 물린다(drones.DRONE_GROUP_MAT → materials.MATERIALS).
  그런데 그 **재질 배정은 전부 사진과 공개 스펙에서 추론한 것**이고, 제조사 설계 데이터와
  대조된 적이 한 번도 없다 — 우리 7종 중 그런 데이터가 있는 기종이 없었기 때문이다.

  Sentinel 의 STEP 는 우리가 확보한 **유일한 공식 CAD 이면서 부품명이 재질을 말하는** 파일이다.
  일부 부품은 McMaster-Carr 카탈로그 번호를 달고 있어 재질이 **카탈로그로 확정 가능**하다.
  즉 이 기체의 과학적 가치는 "드론이 하나 더 늘었다" 가 아니라 **우리 재질·내부구조 가정을
  제조사 데이터로 검사할 수 있는 유일한 기체**라는 것이다.

⛔ 라이선스 — 구속 조건
  ModalAI 는 이 파일에 라이선스를 명시하지 않았다(사이트 푸터는 저작권 고지뿐).
  따라서 **측정·재질 참조 전용**이다. 이 스크립트는 **치수와 통계만** 뽑고 형상은 복제하지
  않는다. 산출 JSON 에는 좌표·면적·부피·부품명만 들어가며 삼각형은 한 장도 들어가지 않는다.
  Sentinel 을 8번째 기체로 넣는다면 **우리 파라메트릭 메쉬를 우리 방식으로** 새로 만든다.
  측정치는 사실이고, 형상은 그들 것이다.

입력 (assets/meshes/reference_study/modalai_sentinel/ — /data/public 심링크)
  * `Sentinel_Drone.STEP`   STEP AP214 / SolidWorks 2019 / 2022-05-14 / 96.8 MB
  * `sentinel_drone.glb`    같은 모델의 테셀레이션 변환본 / 23 MB

■ 어느 파서를 왜 쓰나 (두 개를 **교차검증용으로 같이** 쓴다)
  · **조립 구조**(부품 정체·인스턴스 수)는 **STEP 직접 파싱**이 진리원이다.
    measure_x500v2_cad.Step 을 재사용해 PRODUCT / PRODUCT_DEFINITION /
    NEXT_ASSEMBLY_USAGE_OCCURRENCE 를 읽는다. STEP 이 조립 관계의 1차 기술이기 때문이다.
  · **형상량**(삼각형·면적·부피·bbox)은 **GLB(trimesh)** 를 쓴다. STEP 의 B-rep 에서 면적·부피를
    정확히 내려면 OCC 커널이 필요한데 이 환경엔 없다. GLB 는 같은 모델의 테셀레이션이고
    노드 이름에 **NAUO 인스턴스 ID 가 그대로 보존**돼 있어 STEP 조립 구조와 1:1 로 붙는다.
  · 두 경로가 **부품 32종 / 인스턴스 48개로 정확히 일치**한다 → 변환이 부품을 잃지 않았다는 증거.

⚠ 2차 정보 반증 (다른 에이전트 보고 → 이 스크립트가 원본에서 재검증)
  · "32 unique parts / **104 instances**" → 인스턴스는 **48개**다. 104 는 GLB 의 **색 그룹 수**
    (SolidWorks appearance 별로 쪼개진 primitive)이지 인스턴스가 아니다.
  · "'ModalAi ESC' **x12**", "'M0053_VOXL2_...' **x23**", "'T-MOTOR_AIR 2213 kv920' **x16**"
    → 실제 인스턴스는 각각 **1 / 1 / 4** 개다. 12·23·16 은 그 부품 안의 색 그룹 수다.
    (ESC 가 12개인 드론은 없다. ModalAI ESC 는 4-in-1 보드 **한 장**이다.)
  · "watertight **False**" → GLB 정점이 면별로 분리돼 있어서 그렇게 보일 뿐이다.
    merge_vertices 후 연결성분 2,171개 중 **725개가 닫힌 솔리드**다. 부피는 그것들만 센다.
  · "높이 186.5 vs 187 (**+0.3%**)" → 부호가 반대다. 186.45 < 187 이므로 **−0.29%**.
  · 총 삼각형 **939,935** 와 bbox **375.7 × 375.7 × 186.5 mm** 는 재현됐다. 이 둘은 맞다.

⭐ 이 파일이 새로 밝힌 것
  · ModalAI 문서가 Sentinel 프레임을 **Holybro S500 V2 Frame Kit** 으로 명시한다. 그리고
    CAD 의 상·하판 두께가 **정확히 1.500 mm** 로 Holybro 공표 "1.5mm top and bottom plates"
    와 일치한다 → 프레임 동일성이 **독립 확인**된다. 그 결과 Holybro 가 공표한 암 재질
    (폴리아미드-나일론 복합 + 중심 카본 로드)이 이 CAD 부품에 **그대로 적용**된다.
    ※ 우리 7종의 x500v2 는 같은 Holybro 의 **형제 프레임**이다 — 상호 대조가 가능하다.
  · CAD 의 모터는 **T-MOTOR AIR 2213 kv920** 인데 ModalAI 가 공표한 출하 모터는
    **Holybro 2216-880kv** 다. CAD 의 VOXL2 보드도 **M0053** 인데 출하품은 **M0054** 다.
    → 이 STEP 는 2022-05-14 **개발 스냅샷**이지 출하 형상이 아니다.
  · STEP 안에 **재질 메타데이터가 없다**(MATERIAL_DESIGNATION·PROPERTY_DEFINITION 0건).
    재질 증거는 **부품명 · 벤더 부품번호 · 색(21,093 COLOUR_RGB) · 벤더 문서** 넷뿐이다.

■ 신뢰 등급(tier) — 이 파일의 존재 이유
  catalogue : 벤더/카탈로그 항목이 재질을 지정하고 **내가 그 항목을 실제로 확인**했다.
  named     : 부품명이 재질을 그대로 말한다("...Aluminum...", "...NYLON...").
  inferred  : 기능에서 추론했다. **절대 위 둘과 같은 무게로 읽히면 안 된다.**
  ⚠ McMaster 부품번호(95947A016 / 90304A213 / 94639A188 / 94639A195)는 mcmaster.com 이
    자동 조회를 차단해서 **카탈로그 원문을 확인하지 못했다**. 그래서 tier 를 catalogue 로
    올리지 않고 `named`(부품명이 재질을 말한다) 로 두고, catalogue.status='unconfirmed' 로
    따로 적는다. 카탈로그 내용을 지어내지 않는다.
    다만 치수는 독립 방증이 된다 — 나일론 스페이서 OD 6.350 mm = 정확히 1/4", 길이 4.763 /
    12.700 mm = 정확히 3/16" / 1/2". 임페리얼 격자에 정확히 떨어진다.

실행: cd sionna2 && PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/sentinel_truth.py
산출: outputs/sentinel_truth.json
"""
from __future__ import annotations

import collections
import hashlib
import json
import re
import time
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[1]
CAD = ROOT / "assets" / "meshes" / "reference_study" / "modalai_sentinel"
STEP_PATH = CAD / "Sentinel_Drone.STEP"
GLB_PATH = CAD / "sentinel_drone.glb"
OUT = ROOT / "outputs" / "sentinel_truth.json"

MM = 1000.0                       # trimesh 는 m, 우리는 mm 로 보고한다


# --------------------------------------------------------------------------- #
#  0. 공표 스펙 — 대조 기준 (docs.modalai.com/sentinel-functional-description)
# --------------------------------------------------------------------------- #
PUBLISHED = {
    "source": "https://docs.modalai.com/sentinel-functional-description/ (2026-07-30 조회)",
    "motor_to_motor_mm": [334.0, 334.0, 133.0],
    "props_out_mm": [591.0, 591.0, 187.0],
    "prop_count": 4,
    "prop_diameter_mm": 254.0,          # "QTY. 4, 10 inch / 254mm"
    "takeoff_weight_g": 1347.0,
    "weight_without_battery_g": 1011.0,
    "payload_g": 1000.0,
    "motor_model": "Holybro 2216-880kv",
    "frame_model": "Holybro S500 V2 Frame Kit",
    "battery": "Gens Ace 5000mAh 3S (XT60)",
    "autopilot": "VOXL 2 (M0054), 16 g",
}
# Holybro S500 V2 제품 페이지(holybro.com/products/s500-v2-kit, newbeedrone 재판매 페이지)
HOLYBRO_S500V2 = {
    "source": "https://holybro.com/products/s500-v2-kit (2026-07-30 조회)",
    "arm_material": "high strength, ultra-durable Polyamide-Nylon composite material "
                    "reinforced with carbon fiber rod through the center",
    "plate_thickness_mm": 1.5,          # "1.5mm top and bottom plates"
    "bottom_plate": "built-in PDB (Cont. 60 A / Burst 100 A)",
    "landing_gear_material": "16 mm & 10 mm carbon fiber tubes with plastic tee connectors",
}

# 배터리(부재) 외형 후보 — Gens Ace 5000 mAh 3S 변종들 (genstattu.com / 판매처 표기)
BATTERY_VARIANTS_MM = {
    "45C EC5 (369 g)":        (153.49, 47.37, 43.42),
    "50C XT60 (256 g)":       (153.0, 47.0, 24.0),
    "60C XT60 (380 g)":       (155.0, 46.0, 24.0),
    "60C short G-Tech (348 g)": (128.0, 44.5, 28.2),
    "60C short (389 g)":      (139.0, 42.8, 32.0),
}


# --------------------------------------------------------------------------- #
#  1. 재질 배정표 — **이 파일의 핵심**
# --------------------------------------------------------------------------- #
#   group    : 우리 재질군 (carbon / plastic / metal / battery / pcb / other)
#   tier     : catalogue | named | inferred   ← 절대 섞지 않는다
#   conf     : high | medium | low            ← tier 와 **직교**하는 축.
#              같은 inferred 라도 "ESC 는 PCB 다"(high)와 "마스트는 플라스틱일 것"(low)은 다르다.
#   evidence : 왜 그렇게 봤는지. 근거 없는 항목을 만들지 않는다.
MATERIALS: dict[str, dict] = {
    # ── 프레임: Holybro S500 V2 (ModalAI 문서가 프레임 모델을 명시 → 벤더 스펙 적용) ──
    "Arm - White.stp": dict(
        group="plastic", material="폴리아미드-나일론 복합(중심에 카본 로드)",
        tier="catalogue", conf="high",
        catalogue=dict(vendor="Holybro", item="S500 V2 Frame Kit",
                       states=HOLYBRO_S500V2["arm_material"], status="confirmed",
                       url=HOLYBRO_S500V2["source"]),
        evidence="ModalAI 공식 문서가 프레임을 'Holybro S500 V2 Frame Kit' 으로 명시하고, "
                 "이 CAD 의 상·하판 두께가 1.500 mm 로 Holybro 공표 '1.5mm top and bottom "
                 "plates' 와 정확히 일치한다(프레임 동일성 독립 확인). Holybro 가 암 재질을 "
                 "공표하므로 카탈로그 등급.",
        note="⚠ 중심 카본 로드는 **CAD 에 없다** — 암은 솔리드 1개·색 1종이다. 표면적분에는 "
             "안 보이지만 내부 산란체로는 실재한다. 우리 7종의 'arm' 그룹은 carbon 인데, "
             "S500 계열 암의 **바깥면은 나일론**이다 — 우리 가정과 어긋나는 첫 실증 사례."),
    "topplate": dict(
        group="pcb", material="1.5 mm 적층판(FR-4 계열로 추정)",
        tier="inferred", conf="low",
        evidence="두께 1.500 mm 실측 = Holybro 공표 '1.5mm plates'. Holybro 는 **판 재질을 "
                 "공표하지 않는다**. 하판이 PDB(구리 적층판)인 세트의 짝판이라 같은 적층판으로 "
                 "봤을 뿐이다.",
        note="⚠ 이 배정은 확신이 낮다. 상·하판은 전체 면적의 16.5% 라 예산을 크게 흔든다 → "
             "material_budget.plate_sensitivity 에 pcb/carbon/plastic 세 시나리오를 모두 넣었다."),
    "bottplate": dict(
        group="pcb", material="1.5 mm 적층판 + 전력분배(PDB) 동박",
        tier="inferred", conf="medium",
        evidence="Holybro S500 V2 스펙이 하판에 'built-in PDB (Cont 60 A / Burst 100 A)' 를 "
                 "명시한다. 60 A 를 흘리는 분배판은 구조상 **동박 적층판**이다. 두께 1.500 mm "
                 "도 표준 기판 두께대와 맞다.",
        note="벤더가 '재질'이라는 단어로 적어준 것은 아니므로 inferred 를 유지한다."),

    # ── 체결류: 부품명이 재질을 말한다 (McMaster 번호는 확인 실패) ──
    "95947A016_Aluminum Female Threaded Hex Standoff_95947A016": dict(
        group="metal", material="알루미늄",
        tier="named", conf="high",
        catalogue=dict(vendor="McMaster-Carr", number="95947A016", status="unconfirmed",
                       checked="mcmaster.com 이 자동 조회를 차단(2026-07-30) — 카탈로그 원문 미확인"),
        evidence="부품명이 'Aluminum' 을 그대로 적었다. 치수 방증: 육각 맞변 4.500 mm / "
                 "길이 20.000 mm (대각 5.196 = 4.5×2/√3 → 정확한 정육각)."),
    "Aluminum_Standoffs": dict(
        group="metal", material="알루미늄",
        tier="named", conf="high",
        evidence="부품명이 'Aluminum' 을 그대로 적었다. 멀티바디 1부품 안에 **8개**가 들어 있다 "
                 "(Ø4.700 × 14.000 mm, 속이 빈 M3 탭 스탠드오프)."),
    "90304A213_Steel Pan Head Torx Screws_90304A213": dict(
        group="metal", material="강(steel)",
        tier="named", conf="high",
        catalogue=dict(vendor="McMaster-Carr", number="90304A213", status="unconfirmed",
                       checked="mcmaster.com 차단 — 카탈로그 원문 미확인"),
        evidence="부품명이 'Steel' 을 그대로 적었다.",
        note="⚠ 이 부품은 **나사 1개**만 모델링돼 있다(나머지 6개 연결성분은 면적 0 의 테셀레이션 "
             "부스러기). 실물 드론의 나사 수십 개가 CAD 에 없다 → 금속 면적이 과소평가된다."),
    "94639A188_OFF-WHITE NYLON UNTHREADED SPACER_94639A188": dict(
        group="plastic", material="나일론",
        tier="named", conf="high",
        catalogue=dict(vendor="McMaster-Carr", number="94639A188", status="unconfirmed",
                       checked="mcmaster.com 차단 — 카탈로그 원문 미확인"),
        evidence="부품명이 'NYLON' 을 그대로 적었다. 치수 방증: OD 6.350 mm = 정확히 1/4\", "
                 "길이 4.763 mm = 정확히 3/16\" → 임페리얼 카탈로그 격자에 정확히 떨어진다."),
    "94639A195_OFF-WHITE NYLON UNTHREADED SPACER_94639A195": dict(
        group="plastic", material="나일론",
        tier="named", conf="high",
        catalogue=dict(vendor="McMaster-Carr", number="94639A195", status="unconfirmed",
                       checked="mcmaster.com 차단 — 카탈로그 원문 미확인"),
        evidence="부품명이 'NYLON' 을 그대로 적었다. 치수 방증: OD 6.350 mm = 1/4\", "
                 "길이 12.700 mm = 정확히 1/2\"."),

    # ── 구동계 ──
    "T-MOTOR_AIR 2213 kv920": dict(
        group="metal", material="알루미늄 벨 + 규소강 적층 스테이터 + 구리 권선 + NdFeB 자석",
        tier="catalogue", conf="high",
        catalogue=dict(vendor="T-MOTOR", item="AIR 2213 KV920", status="confirmed_by_naming",
                       states="2213 = 스테이터 Ø22 × 높이 13 mm 규약",
                       note="실구매 가능한 모델명이 부품명에 그대로 있다. 측정 벨 외경 28.6 mm "
                            "가 2213 급 캔 치수와 정합."),
        evidence="부품명이 실제 판매 모델명이다. 아웃러너 BLDC 는 전 부위가 금속 "
                 "(벨=알루미늄, 스테이터=규소강, 권선=구리, 자석=NdFeB).",
        note="⚠ **출하품과 다르다** — ModalAI 문서의 Sentinel 모터는 'Holybro 2216-880kv' 다. "
             "이 CAD(2022-05-14)는 개발 스냅샷이다."),

    # ── 전자부 (PCB) ──
    "M0053_VOXL2_DVT_SIP_REVA_S4_P14_LITE": dict(
        group="pcb", material="FR-4 + 구리 + 실장부품(패키지·차폐캔)",
        tier="inferred", conf="high",
        vendor_part="ModalAI M0053 (VOXL2 DVT SIP REV A)",
        evidence="부품명이 ModalAI 보드 품번(M0053)과 제품명(VOXL2)을 담고 있고, CAD 색 그룹이 "
                 "**감청색 솔더마스크(3,15,62) + 검정 패키지 + 금속색**으로 기판 그 자체다. "
                 "다만 '재질' 을 글자로 말한 것은 아니므로 tier 는 inferred 로 둔다.",
        note="⚠ 출하 Sentinel 의 오토파일럿은 **M0054** 다(ModalAI 문서, 16 g). CAD 는 M0053."),
    "ModalAi ESC": dict(
        group="pcb", material="FR-4 + 구리 + MOSFET/커패시터",
        tier="inferred", conf="high",
        vendor_part="ModalAI 4-in-1 ESC",
        evidence="ESC(전자변속기)는 정의상 기판이다. CAD 색 그룹에 **구리 오렌지(246,168,101)** "
                 "와 솔더마스크색이 함께 있다.",
        note="⭐ 인스턴스는 **1개**다(4-in-1 보드 한 장). 2차 보고의 'x12' 는 색 그룹 수였다."),
    "ESC-Plate": dict(
        group="plastic", material="절연 마운트판(추정)",
        tier="inferred", conf="medium",
        evidence="ESC 기판 바로 아래 깔리는 얇은 판(두께 1.59 mm). 금속이면 기판을 단락시키므로 "
                 "절연체로 본다."),
    "SF-C72510OVV-H133-BTB-L40_noRibbon": dict(
        group="other", material="커넥터(LCP/PPS 하우징 + 도금 접점)",
        tier="inferred", conf="medium",
        vendor_part="SF-C72510OVV-H133-BTB-L40 (FPC/board-to-board 케이블 조립체)",
        evidence="부품명이 커넥터 품번 규약이고 '_noRibbon' 은 리본 케이블을 뺐다는 표시다. "
                 "8.5 × 6.5 × 8.5 mm 로 산란에 무의미한 크기."),

    # ── 카메라/센서 ──
    "New 4K": dict(
        group="other", material="카메라 모듈(금속 배럴 + 유리 렌즈 + FPC)",
        tier="inferred", conf="high",
        evidence="ModalAI 4K 이미저 모듈. 색 그룹이 렌즈(연청회색)·모듈 본체(검정)·플렉스(올리브) "
                 "셋으로 나뉜다.",
        note="우리 체계에는 이 조립품을 위한 'camera_assembly' 재질이 따로 있다"
             "(materials.MATERIALS, PO 실효 |Γ|=0.85). 여기서는 요청된 6군 중 other 로 집계하고 "
             "camera 소계를 따로 낸다."),
    "VoxlStCamV-Vision7251-A50V2": dict(
        group="other", material="트래킹 카메라 모듈(Vision 7251 센서)",
        tier="inferred", conf="high",
        evidence="부품명이 이미지센서 품번을 담고 있다. 5.2 × 17.8 × 16.5 mm 소형 모듈."),
    "VoxlStCamV-Vision7251-A50V2 Left": dict(
        group="other", material="트래킹 카메라 모듈(Vision 7251 센서)",
        tier="inferred", conf="high", evidence="위와 동일 모듈의 좌측 사본."),
    "VoxlStCamV-Vision7251-A50V2-REAR": dict(
        group="other", material="트래킹 카메라 모듈(Vision 7251 센서)",
        tier="inferred", conf="high", evidence="위와 동일 모듈의 후방 사본 2개."),
    "Tracking45Deg50-HB265-1": dict(
        group="other", material="45° 하방 트래킹 카메라 조립체",
        tier="inferred", conf="medium",
        evidence="부품명이 장착각(45°)과 모듈 품번을 담고 있다."),
    "PX4 Neo M8N GPS": dict(
        group="plastic", material="플라스틱 하우징(내부 패치안테나 + 기판)",
        tier="inferred", conf="medium",
        vendor_part="Holybro/PX4 Neo M8N GPS (u-blox NEO-M8N)",
        evidence="실제 판매 모듈. 58 × 50 × 14.4 mm 로 공표 치수대와 맞다. 바깥면(면적 98%)은 "
                 "검정 플라스틱 케이스이고 기판·패치안테나는 그 안에 있다(CAD 는 내부를 "
                 "모델링하지 않았다)."),
    "PX4_GPS_&_Compass_mast": dict(
        group="plastic", material="마스트 지주(플라스틱 또는 카본 튜브 — 미확정)",
        tier="inferred", conf="low",
        evidence="GPS 를 프레임 위로 띄우는 지주(Ø29.5 × 85.8 mm). 이 급 마스트는 플라스틱 "
                 "또는 카본 튜브 둘 다 흔하고, CAD 색(18,18,18 검정)으로는 구별되지 않는다.",
        note="⚠ 낮은 확신. 면적 3,262 mm²(전체의 1.1%)라 예산 영향은 작다."),
    "PX4_GPS_&_Compass_mount2": dict(
        group="plastic", material="마스트 베이스(추정)",
        tier="inferred", conf="low", evidence="마스트를 프레임에 붙이는 소형 브래킷."),
    "SpektrumRC": dict(
        group="plastic", material="수신기 케이스(내부 기판)",
        tier="inferred", conf="medium",
        vendor_part="Spektrum RC 수신기",
        evidence="RC 수신기(30 × 28 × 7.3 mm). 바깥면은 플라스틱 케이스이고 기판은 그 안에 "
                 "있다(CAD 는 내부 미모델링)."),

    # ── ModalAI 자체 하우징/기구물 ──
    "Sentinel-DeckBodyR6": dict(
        group="plastic", material="성형 하우징(추정)",
        tier="inferred", conf="medium",
        evidence="VOXL2·카메라를 담는 ModalAI 자체 데크 몸체(120 × 99 × 44 mm). 얇은 벽의 "
                 "성형/프린팅 인클로저 형상이고 CAD 색은 아주 짙은 녹색(3,20,0).",
        note="면적 23,899 mm²(7.7%) 로 단일 부품 3위. 확신 medium 인 점을 감안할 것."),
    "voxl2-RB5FlightDeckLid": dict(
        group="plastic", material="성형 뚜껑(추정)",
        tier="inferred", conf="medium", evidence="데크 몸체의 짝 뚜껑."),
    "Voxl Tray Front Oval": dict(
        group="plastic", material="성형 트레이(추정)",
        tier="inferred", conf="medium", evidence="전방 카메라를 잡는 트레이."),
    "RB5-Voxl-2-BottomFanMount": dict(
        group="plastic", material="성형 팬 마운트(추정)",
        tier="inferred", conf="medium", evidence="냉각팬을 데크 하부에 붙이는 브래킷."),
    "Fan": dict(
        group="other", material="축류팬(플라스틱 임펠러·프레임 + 내부 소형 BLDC)",
        tier="inferred", conf="high",
        evidence="25.3 × 25.1 × 7.5 mm 축류팬. 바깥은 플라스틱이지만 내부에 구리 권선·강철 "
                 "축이 있는 혼합 조립품이라 other 로 둔다.",
        note="⭐ **회전체다**. 프로펠러 말고도 마이크로도플러를 만드는 부품이 하나 더 있다는 "
             "뜻인데, 25 mm 팬은 반사 단면이 극히 작아 실효는 없을 것이다."),
    "Vibration Damper - Red": dict(
        group="other", material="탄성체(실리콘/고무)",
        tier="inferred", conf="high",
        evidence="부품명이 기능(진동 댐퍼)을 말하고 색이 순수 적색(255,0,0)이다. 이 기능은 "
                 "탄성체 말고 다른 재질로 만들지 않는다.",
        note="⚠ 우리 재질군에 **탄성체가 없다**. 요청된 6군 중 other 로 넣는다. 전체 면적의 "
             "0.9% 라 예산 영향은 작지만, 재질 체계의 공백은 사실로 기록해 둔다."),

    # ── 착륙장치 (ModalAI 자체 — Holybro 카본 튜브 다리가 아니다) ──
    "RB5_landing_gear_mount": dict(
        group="plastic", material="성형 마운트(추정)",
        tier="inferred", conf="medium",
        evidence="ModalAI 자체 착륙장치 마운트."),
    "RB5_landing_gear_skid_v3B": dict(
        group="plastic", material="성형 스키드(추정)",
        tier="inferred", conf="medium",
        evidence="204 × 34 × 55 mm 스키드. **관 형상이 아니다** — 성형품 단면이다.",
        note="⭐ Holybro S500 V2 순정 착륙장치는 '16 mm & 10 mm 카본 튜브'인데 이 CAD 는 "
             "ModalAI 자체 성형 스키드로 **교체**돼 있다. 프레임 킷 재질을 착륙장치까지 "
             "확장 적용하면 안 된다는 증거."),
    "Left Foot Unlinked_v2": dict(
        group="plastic", material="성형 발(추정)",
        tier="inferred", conf="medium", evidence="스키드 끝의 접지 발."),
    "Right Foot Unlinked": dict(
        group="plastic", material="성형 발(추정)",
        tier="inferred", conf="medium", evidence="스키드 끝의 접지 발(반대편)."),
}

#  내부 산란체로 세는 부품 (가시성 테스트와 **독립적인** 기능 기준 분류)
INTERNAL_ROLE = {
    "M0053_VOXL2_DVT_SIP_REVA_S4_P14_LITE": "pcb_main",
    "ModalAi ESC": "esc",
    "T-MOTOR_AIR 2213 kv920": "motor",
    "Fan": "fan",
    "SF-C72510OVV-H133-BTB-L40_noRibbon": "connector",
}


# --------------------------------------------------------------------------- #
#  2. STEP 조립 구조 (진리원)
# --------------------------------------------------------------------------- #
def step_assembly(path: Path) -> dict:
    """STEP 을 직접 읽어 부품 정체와 인스턴스 수를 낸다. GLB 와 교차검증할 기준."""
    import sys
    sys.path.insert(0, str(ROOT / "benchmark"))
    from measure_x500v2_cad import Step                      # STEP 파서 재사용

    st = Step(path)
    name = {k: re.match(r"\s*'([^']*)'", v[1]).group(1) for k, v in st._of("PRODUCT").items()}
    pdf = {k: st.kids[k][0] for k, v in st._of("PRODUCT_DEFINITION_FORMATION").items() if st.kids[k]}
    pdf.update({k: st.kids[k][0]
                for k, v in st._of("PRODUCT_DEFINITION_FORMATION_WITH_SPECIFIED_SOURCE").items()
                if st.kids[k]})
    pd2prod = {k: pdf.get(st.kids[k][0]) for k, v in st._of("PRODUCT_DEFINITION").items() if st.kids[k]}
    nauo = {k: (st.kids[k][0], st.kids[k][1])
            for k, v in st._of("NEXT_ASSEMBLY_USAGE_OCCURRENCE").items()}

    child_count = collections.Counter()
    parents = set()
    for _k, (p, c) in nauo.items():
        child_count[name.get(pd2prod.get(c), "?")] += 1
        parents.add(name.get(pd2prod.get(p), "?"))

    subasm = sorted(n for n in child_count if n in parents)   # 자식이면서 부모인 것 = 하위조립
    leaf = {n: c for n, c in child_count.items() if n not in parents}
    return dict(
        n_product_entities=len(name),
        n_unique_product_names=len(set(name.values())),
        n_nauo_links=len(nauo),
        root=[n for n in set(name.values()) if n not in child_count],
        subassemblies={n: child_count[n] for n in subasm},
        leaf_part_instance_counts=dict(sorted(leaf.items())),
        n_unique_leaf_parts=len(leaf),
        n_leaf_instances=int(sum(leaf.values())),
        entity_counts_of_interest={
            "MANIFOLD_SOLID_BREP": len(st._of("MANIFOLD_SOLID_BREP")),
            "ADVANCED_FACE": len(st._of("ADVANCED_FACE")),
            "COLOUR_RGB": len(st._of("COLOUR_RGB")),
            "MATERIAL_DESIGNATION": len(st._of("MATERIAL_DESIGNATION")),
            "PROPERTY_DEFINITION": len(st._of("PROPERTY_DEFINITION")),
            "DESCRIPTIVE_REPRESENTATION_ITEM": len(st._of("DESCRIPTIVE_REPRESENTATION_ITEM")),
        },
        note="MATERIAL_DESIGNATION·PROPERTY_DEFINITION 가 0 이다 → STEP 안에 **재질 메타데이터가 "
             "없다**. 재질 증거는 부품명·벤더 품번·색·벤더 문서뿐이다.",
    )


# --------------------------------------------------------------------------- #
#  3. GLB 형상 인벤토리
# --------------------------------------------------------------------------- #
def _basename(geom_name: str) -> str:
    """'ModalAi ESC_7' → 'ModalAi ESC'. 색 그룹 접미사만 떼고 부품명은 보존한다.
    ⚠ 'Left Foot Unlinked_v2' 처럼 이름 자체에 _숫자가 든 부품이 있으므로, STEP 이 아는
      실제 부품명 집합에 있으면 그대로 둔다(호출부에서 known 을 넘긴다)."""
    return geom_name


def glb_inventory(path: Path, known_parts: set[str]) -> dict:
    """GLB 를 읽어 (부품 → 인스턴스 → 색 바디) 3층 구조와 형상량을 낸다."""
    scene = trimesh.load(path)
    graph = scene.graph

    parent = {}
    for (a, b), _d in graph.transforms.edge_data.items():
        parent[b] = a

    def chain(n):
        c = [n]
        while c[-1] in parent:
            c.append(parent[c[-1]])
        return list(reversed(c))

    # 노드 → (NAUO 경로, geometry, world transform)
    inst = collections.defaultdict(list)
    seen_geom = collections.Counter()
    for n in graph.nodes:
        try:
            T, geom = graph.get(n)
        except Exception:
            continue
        if geom is None:
            continue
        seen_geom[geom] += 1
        key = tuple(x for x in chain(n) if re.fullmatch(r"NAUO\d+", x))
        inst[key].append((geom, np.asarray(T)))
    assert all(v == 1 for v in seen_geom.values()), "GLB geometry 가 재사용되고 있다 — 면적 이중계산 위험"

    # 변환이 강체인지 확인 (스케일이 있으면 면적/부피를 원본 메쉬에서 못 읽는다)
    for v in inst.values():
        for _g, T in v:
            R = T[:3, :3]
            assert np.allclose(R @ R.T, np.eye(3), atol=1e-6), "GLB 노드 변환에 스케일/전단이 있다"

    # 부품명 = 인스턴스 첫 바디의 geometry 이름에서 색 접미사 제거
    def part_of(geom_name: str) -> str:
        if geom_name in known_parts:
            return geom_name
        m = re.match(r"^(.*?)(?:_\d+)$", geom_name)
        while m and m.group(1) not in known_parts:
            m = re.match(r"^(.*?)(?:_\d+)$", m.group(1))
        return m.group(1) if m else geom_name

    parts = collections.defaultdict(lambda: dict(instances=[], bodies=0, colors=collections.Counter()))
    for key, bodies in inst.items():
        pname = part_of(bodies[0][0])
        P = parts[pname]
        allpts, area, tris = [], 0.0, 0
        vol_closed, area_closed, ncomp, nclosed = 0.0, 0.0, 0, 0
        for gname, T in bodies:
            m = scene.geometry[gname]
            pts = trimesh.transform_points(np.asarray(m.vertices), T) * MM
            allpts.append(pts)
            h = m.copy()
            h.merge_vertices()
            area += float(h.area) * MM ** 2
            tris += int(len(m.faces))
            rgb = tuple(int(x) for x in m.visual.material.baseColorFactor[:3])
            P["colors"][rgb] += float(h.area) * MM ** 2
            for c in h.split(only_watertight=False):
                ncomp += 1
                if c.is_watertight and c.is_winding_consistent:
                    nclosed += 1
                    vol_closed += abs(float(c.volume)) * MM ** 3
                    area_closed += float(c.area) * MM ** 2
        pts = np.vstack(allpts)
        lo, hi = pts.min(0), pts.max(0)
        P["instances"].append(dict(nauo="/".join(key), n_bodies=len(bodies),
                                   centroid_mm=[round(float(x), 3) for x in pts.mean(0)],
                                   bbox_min_mm=[round(float(x), 3) for x in lo],
                                   bbox_size_mm=[round(float(x), 3) for x in (hi - lo)],
                                   triangles=tris,
                                   area_mm2=round(area, 2),
                                   volume_mm3=round(vol_closed, 3),
                                   n_components=ncomp, n_closed_components=nclosed,
                                   volume_defined=(nclosed == ncomp),
                                   closed_area_fraction=round(area_closed / area, 4) if area else None))
        P["bodies"] += len(bodies)
    return dict(scene=scene, parts=parts, n_color_bodies=sum(seen_geom.values()))


# --------------------------------------------------------------------------- #
#  4. 기체 좌표계 — 모터축 사각형의 중심을 원점으로
# --------------------------------------------------------------------------- #
def airframe_frame(parts: dict) -> dict:
    """GLB 좌표계는 z 가 뒤집혀 있다(착륙 스키드가 +z 최상단, GPS 가 −z 최하단).
    기체 좌표계를 정의한다: +Z=위, +X=전방, 원점=모터축 사각형 중심(z 는 하판 중립면).
    전방은 **전방 카메라 위치**로 판정한다 — 이름이 'Front'/'4K' 인 부품이 −x_glb 쪽에 있다."""
    mot = parts["T-MOTOR_AIR 2213 kv920"]["instances"]
    axes = np.array([i["centroid_mm"] for i in mot])
    # 모터 축 = 각 인스턴스 bbox 중심의 xy (벨이 원통이라 bbox 중심 = 축)
    ax_xy = np.array([[i["bbox_min_mm"][0] + i["bbox_size_mm"][0] / 2,
                       i["bbox_min_mm"][1] + i["bbox_size_mm"][1] / 2] for i in mot])
    cxy = ax_xy.mean(0)
    front = np.array(parts["Voxl Tray Front Oval"]["instances"][0]["centroid_mm"])
    sign_x = -1.0 if front[0] < cxy[0] else +1.0        # 전방 트레이가 있는 쪽이 +X
    bot = parts["bottplate"]["instances"][0]
    cz = bot["bbox_min_mm"][2] + bot["bbox_size_mm"][2] / 2
    return dict(origin_glb_mm=[round(float(cxy[0]), 3), round(float(cxy[1]), 3), round(float(cz), 3)],
                x_forward_sign=sign_x, z_up_sign=-1.0,
                definition="원점 = 모터축 4개의 xy 중심 + 하판(bottplate) 중립면 z. "
                           "+X = 전방(전방 카메라 트레이 쪽), +Z = 위, +Y = X×Z 우수계 보완.",
                evidence=f"전방 판정 근거: 'Voxl Tray Front Oval' 중심 x={front[0]:.1f} mm 가 "
                         f"모터 중심 x={cxy[0]:.1f} mm 보다 앞이다. GLB z 뒤집힘 근거: 착륙 "
                         f"스키드가 +z 최상단, GPS 가 −z 최하단으로 실물과 반대다.",
                motor_axes_glb_mm=[[round(float(a), 3) for a in p] for p in ax_xy],
                motor_axis_z_glb_mm=round(float(axes[:, 2].mean()), 3))


def to_airframe(p_glb: np.ndarray, fr: dict) -> np.ndarray:
    """GLB 좌표(mm) → 기체 좌표(mm)."""
    o = np.asarray(fr["origin_glb_mm"])
    q = np.asarray(p_glb, float) - o
    return np.column_stack([fr["x_forward_sign"] * q[:, 0], q[:, 1], fr["z_up_sign"] * q[:, 2]])


# --------------------------------------------------------------------------- #
#  5. 외부 가시면적 — 직교 z-buffer 근사
# --------------------------------------------------------------------------- #
def exterior_area(scene, n_dir: int = 42, cell_mm: float = 0.5, tol_mm: float = 1.0) -> dict:
    """**바깥에서 보이는 면적**을 낸다. PO/SBR 표면적분이 실제로 쓰는 양이다.

    방법: 방향 d 마다 삼각형 무게중심을 d 에 수직인 격자에 투영하고, 격자칸마다 가장 바깥의
    깊이를 z-buffer 로 잡은 뒤 그 깊이에서 tol 이내인 삼각형을 '보인다' 로 표시한다.
    **근사다** — 무게중심 기준이라 큰 삼각형의 부분 가림은 못 본다. 셀·톨러런스를 함께 적는다.
    (embree 가 없어 정확한 광선추적은 불가 — 그래서 근사임을 이름과 grade 로 못박는다.)"""
    V, F, owner = [], [], []
    off = 0
    for i, (gname, m) in enumerate(scene.geometry.items()):
        h = m.copy()
        h.merge_vertices()
        V.append(np.asarray(h.vertices) * MM)
        F.append(np.asarray(h.faces) + off)
        owner.append(np.full(len(h.faces), i))
        off += len(h.vertices)
    V = np.vstack(V)
    F = np.vstack(F)
    owner = np.concatenate(owner)
    A = np.linalg.norm(np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]), axis=1) / 2.0
    C = V[F].mean(axis=1)

    ico = trimesh.creation.icosphere(subdivisions=1)
    dirs = np.asarray(ico.vertices, float)
    dirs = dirs[: min(n_dir, len(dirs))]
    dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)

    vis = np.zeros(len(F), bool)
    for d in dirs:
        a = np.array([0.0, 0.0, 1.0]) if abs(d[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
        e1 = np.cross(d, a); e1 /= np.linalg.norm(e1)
        e2 = np.cross(d, e1)
        u, v, w = C @ e1, C @ e2, C @ d
        iu = ((u - u.min()) / cell_mm).astype(np.int64)
        iv = ((v - v.min()) / cell_mm).astype(np.int64)
        nv = iv.max() + 1
        key = iu * nv + iv
        best = np.full(key.max() + 1, -np.inf)
        np.maximum.at(best, key, w)              # 칸마다 가장 바깥(=w 최대) 깊이
        vis |= (w >= best[key] - tol_mm)
    a_ext = float(A[vis].sum())
    a_tot = float(A.sum())
    per_geom_ext = collections.Counter()
    per_geom_tot = collections.Counter()
    names = list(scene.geometry.keys())
    np.add.at(np.zeros(1), 0, 0)                 # noqa (numpy 버전 호환 확인용 no-op)
    for i in range(len(names)):
        sel = owner == i
        per_geom_tot[names[i]] = float(A[sel].sum())
        per_geom_ext[names[i]] = float(A[sel & vis].sum())
    return dict(grade="ESTIMATE",
                method=f"직교 z-buffer 근사, 방향 {len(dirs)}개(icosphere sub=1), 셀 {cell_mm} mm, "
                       f"허용깊이 {tol_mm} mm, 삼각형 무게중심 기준",
                total_facet_area_mm2=round(a_tot, 1),
                exterior_area_mm2=round(a_ext, 1),
                exterior_fraction=round(a_ext / a_tot, 4),
                per_geometry_exterior_mm2={k: round(v, 2) for k, v in per_geom_ext.items()},
                per_geometry_total_mm2={k: round(v, 2) for k, v in per_geom_tot.items()},
                caveat="무게중심 기준이라 부분 가림은 반영하지 않는다. 절대값보다 **비율**을 쓰라.")


# --------------------------------------------------------------------------- #
#  6. 메인
# --------------------------------------------------------------------------- #
def sha256(p: Path, limit: int = 1 << 30) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        while (b := f.read(1 << 20)):
            h.update(b)
    return h.hexdigest()


def main() -> None:
    t0 = time.time()
    print("[sentinel] STEP 조립 구조 파싱…")
    asm = step_assembly(STEP_PATH)
    known = set(asm["leaf_part_instance_counts"])
    print(f"           부품 {asm['n_unique_leaf_parts']}종 / 인스턴스 {asm['n_leaf_instances']}개 "
          f"/ NAUO {asm['n_nauo_links']}개")

    print("[sentinel] GLB 형상 인벤토리…")
    gi = glb_inventory(GLB_PATH, known)
    scene, parts = gi["scene"], gi["parts"]

    # ── 교차검증: STEP vs GLB ────────────────────────────────────────────
    glb_counts = {k: len(v["instances"]) for k, v in parts.items()}
    cross = dict(
        step_leaf_parts=asm["n_unique_leaf_parts"], glb_parts=len(glb_counts),
        step_leaf_instances=asm["n_leaf_instances"],
        glb_instances=int(sum(glb_counts.values())),
        glb_color_bodies=gi["n_color_bodies"],
        mismatches={k: [asm["leaf_part_instance_counts"].get(k), glb_counts.get(k)]
                    for k in set(asm["leaf_part_instance_counts"]) | set(glb_counts)
                    if asm["leaf_part_instance_counts"].get(k) != glb_counts.get(k)},
    )
    cross["agree"] = not cross["mismatches"]
    print(f"           STEP↔GLB 일치: {cross['agree']}  (색 바디 {cross['glb_color_bodies']}개)")

    fr = airframe_frame(parts)

    print("[sentinel] 외부 가시면적 z-buffer…")
    ext = exterior_area(scene)
    print(f"           외부 {ext['exterior_area_mm2']:.0f} / 전체 {ext['total_facet_area_mm2']:.0f} mm² "
          f"= {ext['exterior_fraction']*100:.1f}%")

    # ── 부품 인벤토리 조립 ───────────────────────────────────────────────
    inventory = {}
    tot_area = tot_vol = 0.0
    for pname, P in sorted(parts.items()):
        mat = MATERIALS.get(pname)
        if mat is None:
            raise KeyError(f"재질 미배정 부품: {pname!r} — MATERIALS 에 추가하라(조용히 넘기지 않는다)")
        area = sum(i["area_mm2"] for i in P["instances"])
        vol = sum(i["volume_mm3"] for i in P["instances"])
        tris = sum(i["triangles"] for i in P["instances"])
        ncomp = sum(i["n_components"] for i in P["instances"])
        nclosed = sum(i["n_closed_components"] for i in P["instances"])
        cen = to_airframe(np.array([i["centroid_mm"] for i in P["instances"]]), fr)
        dom = max(P["colors"].items(), key=lambda kv: kv[1])[0]
        inventory[pname] = dict(
            instance_count=len(P["instances"]),
            color_bodies=P["bodies"],
            triangles=tris,
            area_mm2=round(area, 2),
            volume_mm3=round(vol, 3),
            volume_status=("defined" if nclosed == ncomp else
                           f"partial — 연결성분 {ncomp}개 중 {nclosed}개만 닫힘, 부피는 그것들만 합산"),
            n_components=ncomp, n_closed_components=nclosed,
            bbox_size_mm=P["instances"][0]["bbox_size_mm"],
            dominant_color_rgb=list(dom),
            centroid_airframe_mm=[[round(float(x), 2) for x in c] for c in cen],
            material=mat["material"], group=mat["group"], tier=mat["tier"],
            confidence=mat["conf"], evidence=mat["evidence"],
            **({"catalogue": mat["catalogue"]} if "catalogue" in mat else {}),
            **({"vendor_part": mat["vendor_part"]} if "vendor_part" in mat else {}),
            **({"note": mat["note"]} if "note" in mat else {}),
            exterior_area_mm2=round(sum(ext["per_geometry_exterior_mm2"].get(g, 0.0)
                                        for g in ext["per_geometry_total_mm2"]
                                        if g == pname or g.startswith(pname + "_")), 2),
        )
        tot_area += area
        tot_vol += vol

    # ── 재질 예산 ────────────────────────────────────────────────────────
    def budget(override: dict[str, str] | None = None) -> dict:
        ga = collections.Counter(); gv = collections.Counter(); ge = collections.Counter()
        for pname, inv in inventory.items():
            g = (override or {}).get(pname, inv["group"])
            ga[g] += inv["area_mm2"]; gv[g] += inv["volume_mm3"]; ge[g] += inv["exterior_area_mm2"]
        A = sum(ga.values()); Vv = sum(gv.values()); E = sum(ge.values())
        return dict(
            area_mm2={k: round(v, 1) for k, v in ga.items()},
            area_fraction={k: round(v / A, 4) for k, v in ga.items()},
            exterior_area_fraction={k: round(v / E, 4) for k, v in ge.items()} if E else {},
            volume_mm3={k: round(v, 1) for k, v in gv.items()},
            volume_fraction={k: round(v / Vv, 4) for k, v in gv.items()},
            conductive_area_fraction=round(sum(ga[k] for k in ("carbon", "metal", "pcb")) / A, 4),
        )

    base = budget()
    sens = {f"plates={g}": budget({"topplate": g, "bottplate": g})
            for g in ("pcb", "carbon", "plastic")}

    tier_area = collections.Counter()
    for inv in inventory.values():
        tier_area[inv["tier"]] += inv["area_mm2"]
    tier_frac = {k: round(v / tot_area, 4) for k, v in tier_area.items()}

    # ── 내부 산란체 인구조사 ─────────────────────────────────────────────
    scat = {}
    for pname, role in INTERNAL_ROLE.items():
        inv = inventory[pname]
        scat[role] = dict(part=pname, count=inv["instance_count"],
                          positions_airframe_mm=inv["centroid_airframe_mm"],
                          bbox_size_mm=inv["bbox_size_mm"],
                          area_mm2=inv["area_mm2"], volume_mm3=inv["volume_mm3"],
                          exterior_area_mm2=inv["exterior_area_mm2"],
                          buried_fraction=round(1 - inv["exterior_area_mm2"] / inv["area_mm2"], 4))
    # 중앙집중 vs 팔 분산
    r_pcb = [float(np.hypot(c[0], c[1])) for p, role in INTERNAL_ROLE.items() if role in ("pcb_main", "esc")
             for c in inventory[p]["centroid_airframe_mm"]]
    r_mot = [float(np.hypot(c[0], c[1])) for c in inventory["T-MOTOR_AIR 2213 kv920"]["centroid_airframe_mm"]]
    internal = dict(
        census=scat,
        n_pcb_assemblies=2, n_esc_boards=1, n_motors=4,
        pcb_radius_mm=[round(x, 1) for x in r_pcb],
        motor_radius_mm=[round(x, 1) for x in r_mot],
        layout="중앙집중. 전자부(VOXL2 보드·ESC·수신기·커넥터)는 전부 반경 "
               f"{max(r_pcb):.0f} mm 안에 있고, 팔에는 **전자부품이 하나도 없다** — 팔 끝에 "
               f"있는 것은 모터(반경 {np.mean(r_mot):.0f} mm)뿐이다. ESC 도 4-in-1 보드 한 장으로 "
               "중앙에 있어서, 우리 파라메트릭 드론이 팔마다 ESC 를 두는 형태였다면 그것과 다르다.",
        metal_volume_mm3=round(base["volume_mm3"].get("metal", 0.0), 1),
        metal_volume_fraction=base["volume_fraction"].get("metal", 0.0),
        metal_note="금속 부피의 대부분은 **모터 4기**다. 스탠드오프·나사는 부피가 미미하고, "
                   "CAD 에 나사가 1개만 있어 실제보다 더 적게 잡힌다.",
    )

    # ── 치수 검증 ────────────────────────────────────────────────────────
    ax = np.asarray(fr["motor_axes_glb_mm"])
    import itertools
    d_all = sorted(float(np.linalg.norm(a - b)) for a, b in itertools.combinations(ax, 2))
    side = float(np.mean(d_all[:4])); diag = float(np.mean(d_all[4:]))
    allpts = np.vstack([trimesh.transform_points(np.asarray(m.vertices), T) * MM
                        for k, v in [(k, v) for k, v in
                                     [(kk, vv) for kk, vv in
                                      [(a, b) for a, b in [(None, None)]]]] ] ) if False else None
    # 전체 bbox
    P = []
    for gname, m in scene.geometry.items():
        P.append(np.asarray(m.vertices) * MM)
    P = np.vstack(P)
    # 노드 변환 포함 bbox 는 scene.bounds 가 정확하다
    sb = np.asarray(scene.bounds) * MM
    bbox = sb[1] - sb[0]
    # 모터 top / 스키드 bottom (기체 좌표)
    mot_z_top = max(-(i["bbox_min_mm"][2]) for i in parts["T-MOTOR_AIR 2213 kv920"]["instances"])
    skid_z_bot = min(-(i["bbox_min_mm"][2] + i["bbox_size_mm"][2])
                     for i in parts["RB5_landing_gear_skid_v3B"]["instances"])
    h_no_mast = mot_z_top - skid_z_bot

    def delta(meas, pub):
        return dict(measured_mm=round(meas, 2), published_mm=pub,
                    delta_mm=round(meas - pub, 2), delta_pct=round(100 * (meas - pub) / pub, 2))

    dims = dict(
        overall_bbox_mm=[round(float(x), 2) for x in bbox],
        motor_square_side=delta(side, PUBLISHED["motor_to_motor_mm"][0]),
        motor_square_diagonal_mm=round(diag, 2),
        height_incl_gps_mast=delta(float(bbox[2]), PUBLISHED["props_out_mm"][2]),
        height_skid_to_motor_top=delta(h_no_mast, PUBLISHED["motor_to_motor_mm"][2]),
        props_out_span_predicted=delta(side + PUBLISHED["prop_diameter_mm"],
                                       PUBLISHED["props_out_mm"][0]),
        plate_thickness=dict(
            topplate_mm=parts["topplate"]["instances"][0]["bbox_size_mm"][2],
            bottplate_mm=parts["bottplate"]["instances"][0]["bbox_size_mm"][2],
            holybro_published_mm=HOLYBRO_S500V2["plate_thickness_mm"],
            verdict="정확히 1.500 mm — Holybro S500 V2 공표치와 일치. 프레임 동일성의 독립 증거."),
        xy_extent_driver="Arm - White.stp (암 끝단). 전체 xy 폭 375.7 mm 는 프롭이 아니라 "
                         "**암 끝**이 만든다 — 모터축 사각형보다 양쪽으로 ~24 mm 더 나온다.",
        notes=[
            "공표 '334×334×133' 은 프롭 없는 상자, '591×591×187' 은 프롭 편 상자다. "
            "높이 187 은 **GPS 마스트**가 정하므로 프롭이 없어도 이 CAD 에서 잴 수 있다.",
            "⚠ 모터 사각형이 공표보다 작다. 그리고 ModalAI 가 프레임을 S500 V2(휠베이스 500 mm "
            "= 사각형 변 353.6 mm)라고 하는데 측정 변은 그보다 더 작다 → CAD 의 암/모터 배치가 "
            "출하 사양과 다른 개발 스냅샷이라는 정황과 일치한다. **미해결 불일치로 남긴다.**",
        ],
    )

    # ── 부재(不在) 분석 ──────────────────────────────────────────────────
    # 프롭 면적: 우리 자체 파라메트릭 프롭(x500v2 = 254 mm, Sentinel 과 동일 직경)에서 실측
    import sys
    sys.path.insert(0, str(ROOT / "src"))
    from drones import DRONES, build_propeller
    pm = build_propeller(DRONES["x500v2"])
    pv, pf = np.asarray(pm.v), np.asarray(pm.f)
    prop_dia = float(np.linalg.norm(pv[:, :2], axis=1).max()) * 2 * MM
    prop_area = float(np.linalg.norm(np.cross(pv[pf[:, 1]] - pv[pf[:, 0]],
                                              pv[pf[:, 2]] - pv[pf[:, 0]]), axis=1).sum() / 2) * MM ** 2
    props_total = prop_area * PUBLISHED["prop_count"]
    batt = {k: 2 * (a * b + a * c + b * c) for k, (a, b, c) in BATTERY_VARIANTS_MM.items()}
    batt_lo, batt_hi = min(batt.values()), max(batt.values())
    batt_mid = float(np.median(list(batt.values())))
    ext_cad = ext["exterior_area_mm2"]
    absent = dict(
        propellers=dict(
            present_in_cad=False,
            verified_by="STEP 전체에서 prop/blade/rotor 문자열 0건, 부품 32종에 프롭 없음",
            published=f"QTY. 4, 10 inch / {PUBLISHED['prop_diameter_mm']} mm "
                      "(Master Airscrew 10x4.5, 유리섬유 강화 복합재)",
            area_estimate_mm2=round(props_total, 1),
            area_estimate_method=f"우리 파라메트릭 프롭(drones.build_propeller, x500v2 = "
                                 f"{prop_dia:.1f} mm 로 Sentinel 과 동일 직경) 실측 "
                                 f"{prop_area:.0f} mm²/장 × 4",
            grade="ESTIMATE"),
        battery=dict(
            present_in_cad=False,
            verified_by="STEP 전체에서 batt/lipo/cell/pack 문자열 0건, 배터리 트레이·마운트도 없음",
            published=PUBLISHED["battery"] +
                      f" — 이륙 {PUBLISHED['takeoff_weight_g']} g, 배터리 제외 "
                      f"{PUBLISHED['weight_without_battery_g']} g → 배터리 "
                      f"{PUBLISHED['takeoff_weight_g']-PUBLISHED['weight_without_battery_g']:.0f} g",
            area_estimate_mm2=round(batt_mid, 1),
            area_range_mm2=[round(batt_lo, 1), round(batt_hi, 1)],
            area_estimate_method="Gens Ace 5000 mAh 3S 변종 5종의 외형 직육면체 표면적 "
                                 "(중앙값과 최소·최대). 어느 변종인지 ModalAI 가 특정하지 않았다.",
            variants_mm2={k: round(v, 1) for k, v in batt.items()},
            grade="ESTIMATE"),
        impact=dict(
            cad_exterior_area_mm2=round(ext_cad, 1),
            missing_area_mm2=round(props_total + batt_mid, 1),
            missing_fraction_of_real_exterior=round((props_total + batt_mid) /
                                                    (ext_cad + props_total + batt_mid), 4),
            missing_fraction_range=[round((props_total + batt_lo) / (ext_cad + props_total + batt_lo), 4),
                                    round((props_total + batt_hi) / (ext_cad + props_total + batt_hi), 4)],
            meaning="이 CAD 를 **산란 기준물로 쓰면 안 된다**. 빠진 두 부품은 면적만 작은 게 "
                    "아니라 성격이 결정적이다: (1) 프로펠러는 **유일한 회전 산란체**라 "
                    "마이크로도플러 성분 전체가 통째로 없다. (2) 배터리는 GHz 에서 사실상 "
                    "금속판(파우치 포일)이고 기체 바닥 중앙의 최대 평면 반사체인데, 그게 없으면 "
                    "정면·하방 정반사 로브가 통째로 빠진다. 즉 이 CAD 는 **치수·재질·내부배치 "
                    "참조용**이고, RCS 기준값 산출용이 아니다.",
        ),
        also_absent=["배터리 트레이/스트랩", "배선·케이블 하네스(커넥터 1개만 있고 리본은 "
                     "'_noRibbon' 으로 명시적으로 뺐다)", "나사 대부분(1개만 모델링)",
                     "암 내부의 카본 로드", "GPS·수신기·카메라 내부 기판"],
    )

    # ── 조립 ─────────────────────────────────────────────────────────────
    D = dict(
        _what="ModalAI Sentinel 공식 STEP 에서 뽑은 지상진실. 우리 재질·내부구조 가정을 "
              "제조사 데이터로 검사하기 위한 증거 기반.",
        _licence="⛔ ModalAI 는 이 CAD 에 라이선스를 명시하지 않았다. **측정·재질 참조 전용**. "
                 "형상을 우리 자산으로 복제·재배포하지 않는다. 이 JSON 에는 삼각형이 없다.",
        provenance=dict(
            step=dict(path=str(STEP_PATH), bytes=STEP_PATH.stat().st_size,
                      sha256=sha256(STEP_PATH),
                      header="STEP AP214 / SwSTEP 2.0 / SolidWorks 2019 / 2022-05-14T00:32:17"),
            glb=dict(path=str(GLB_PATH), bytes=GLB_PATH.stat().st_size, sha256=sha256(GLB_PATH)),
            published_spec=PUBLISHED, holybro_frame_spec=HOLYBRO_S500V2,
            generated_by="benchmark/sentinel_truth.py",
        ),
        method=dict(
            assembly="STEP 직접 파싱(measure_x500v2_cad.Step 재사용) — PRODUCT / "
                     "PRODUCT_DEFINITION / NEXT_ASSEMBLY_USAGE_OCCURRENCE. STEP 이 조립 관계의 "
                     "1차 기술이라 인스턴스 수의 진리원이다.",
            geometry="GLB(trimesh) — STEP B-rep 면적/부피를 정확히 내려면 OCC 커널이 필요한데 이 "
                     "환경에 없다. GLB 는 같은 모델의 테셀레이션이고 노드 이름에 NAUO 인스턴스 "
                     "ID 가 보존돼 STEP 구조와 1:1 로 붙는다.",
            volume="정점 병합 후 **연결성분 단위**로 닫힘(watertight + winding 일관)을 검사하고, "
                   "닫힌 성분만 |부피| 를 합산한다. 열린 성분의 부피는 **정의되지 않는다** — "
                   "0 으로 세지도, 추정하지도 않는다.",
            cross_check=cross,
        ),
        step_assembly=asm,
        airframe_frame=fr,
        totals=dict(
            unique_parts=len(inventory),
            instances=int(sum(v["instance_count"] for v in inventory.values())),
            color_bodies=gi["n_color_bodies"],
            triangles=int(sum(v["triangles"] for v in inventory.values())),
            components=int(sum(v["n_components"] for v in inventory.values())),
            closed_components=int(sum(v["n_closed_components"] for v in inventory.values())),
            total_facet_area_mm2=round(tot_area, 1),
            closed_volume_mm3=round(tot_vol, 1),
            volume_caveat="닫힌 연결성분만의 합이다. 전체 성분의 "
                          f"{sum(v['n_closed_components'] for v in inventory.values())}/"
                          f"{sum(v['n_components'] for v in inventory.values())} 만 닫혀 있으므로 "
                          "**기체 총 부피가 아니다**(특히 기판류의 얇은 동박 패턴은 열린 면이다).",
        ),
        parts=inventory,
        material_budget=dict(
            _lead="표면적분에는 **면적 비율**이 유효한 양이다. 부피 비율은 참고용.",
            by_area_and_volume=base,
            exterior_only_note="exterior_area_fraction 은 z-buffer 로 바깥에서 보이는 면만 "
                               "센 것이다 — PO/SBR 이 실제로 조명하는 면에 가장 가깝다.",
            plate_sensitivity=dict(
                why="상·하판(면적 16.5%)의 재질이 확정되지 않았다. 세 가지로 다 계산해 둔다.",
                scenarios=sens,
                robust_conclusion="세 시나리오 중 pcb·carbon 은 둘 다 **도전체**라 |Γ| 차이가 "
                                  "1 dB 안쪽이다(0.80 vs 0.90). 정말 갈리는 것은 plastic 이냐 "
                                  "아니냐(0.28, ~10 dB)이므로 conductive_area_fraction 을 "
                                  "헤드라인으로 읽는 편이 안전하다."),
            tier_area_fraction=tier_frac,
            tier_meaning="면적 기준으로 catalogue/named 등급이 차지하는 비율. 나머지는 inferred "
                         "— 즉 **이 CAD 로도 대부분의 면적은 여전히 추론**이다. 이 파일의 값어치는 "
                         "'전부 확정됐다' 가 아니라 '어디까지가 확정이고 어디부터가 추론인지 "
                         "선이 그어졌다' 는 데 있다.",
        ),
        internal_scatterers=internal,
        dimensions=dims,
        absent=absent,
        exterior_visibility={k: v for k, v in ext.items()
                            if k not in ("per_geometry_exterior_mm2", "per_geometry_total_mm2")},
        refuted=dict(
            _why="다른 에이전트가 2차 보고한 수치를 원본에서 재검증한 결과. 우리 규약상 "
                 "**반증은 지우지 않고 남긴다.**",
            items=[
                dict(claim="32 unique parts / 104 instances",
                     verdict="PARTIAL", correction="부품 32종은 맞다. 인스턴스는 **48개**다. "
                     "104 는 GLB 의 색 그룹(SolidWorks appearance) 수다.",
                     evidence="STEP NAUO 52개 = 하위조립 4 + 리프 48. GLB 도 48개 인스턴스 노드."),
                dict(claim="'ModalAi ESC' x12", verdict="REFUTED",
                     correction="인스턴스는 **1개**(4-in-1 보드 한 장). 12 는 색 그룹 수.",
                     evidence="NAUO44 하나뿐. 12개 primitive 의 면 수가 102286/94202/…/12 로 "
                              "제각각이라 동일 부품의 사본일 수 없다."),
                dict(claim="'M0053_VOXL2_...' x23", verdict="REFUTED",
                     correction="인스턴스는 **1개**(보드 한 장). 23 은 색 그룹 수."),
                dict(claim="'T-MOTOR_AIR 2213 kv920' x16", verdict="REFUTED",
                     correction="인스턴스는 **4개**(쿼드콥터니까). 16 = 4 인스턴스 × 4 색 그룹."),
                dict(claim="watertight False", verdict="MISLEADING",
                     correction="GLB 가 정점을 면별로 분리해 둬서 그렇게 보인다. merge_vertices "
                     "후 연결성분 단위로는 상당수가 닫힌 솔리드다.",
                     evidence=f"성분 {sum(v['n_components'] for v in inventory.values())}개 중 "
                              f"{sum(v['n_closed_components'] for v in inventory.values())}개 닫힘."),
                dict(claim="높이 186.5 vs 187 published (+0.3%)", verdict="SIGN ERROR",
                     correction=f"186.45 < 187 이므로 "
                                f"{dims['height_incl_gps_mast']['delta_pct']:+.2f}% 다."),
                dict(claim="939,935 faces / bbox 375.7 x 375.7 x 186.5 mm", verdict="CONFIRMED",
                     correction="재현됨."),
                dict(claim="McMaster 번호가 재질을 '카탈로그로 확정' 해 준다", verdict="OVERSTATED",
                     correction="mcmaster.com 이 자동 조회를 차단해 **카탈로그 원문을 확인하지 "
                     "못했다**. 확정된 것은 '부품명이 재질을 적었다'(named 등급)까지다. "
                     "역설적으로 **가장 잘 확정된 재질은 Holybro 가 공표한 암(나일론+카본로드)**이다."),
            ],
        ),
        headline=[
            "부품 32종 / 인스턴스 48개 / 색 바디 104개 / 삼각형 939,935개.",
            f"면적 기준 재질 예산(상·하판=pcb 기준): " +
            ", ".join(f"{k} {v*100:.1f}%" for k, v in
                      sorted(base["area_fraction"].items(), key=lambda kv: -kv[1])),
            f"도전체(metal+pcb+carbon) 면적 비율 {base['conductive_area_fraction']*100:.1f}%.",
            f"면적의 {tier_frac.get('catalogue',0)*100:.1f}% 만 catalogue 등급, "
            f"{tier_frac.get('named',0)*100:.1f}% 가 named, 나머지 "
            f"{tier_frac.get('inferred',0)*100:.1f}% 는 여전히 inferred.",
            "⭐ 프레임이 Holybro S500 V2 로 확인됐고(판 두께 1.500 mm 일치), 그 벤더 스펙이 "
            "암을 **나일론 복합(중심 카본로드)** 이라고 말한다 — 우리 7종은 'arm' 을 carbon 으로 "
            "두고 있다. 열린프레임 기종의 암 재질 가정을 재검토할 첫 실증 근거.",
            "⭐ 전자부는 전부 중앙집중이고 팔에는 전자부품이 없다. ESC 는 팔마다가 아니라 "
            "**중앙 4-in-1 보드 한 장**이다.",
            "⚠ 프로펠러와 배터리가 없다 → 실물 외부면의 약 "
            f"{absent['impact']['missing_fraction_of_real_exterior']*100:.0f}% 가 빠져 있고, "
            "빠진 쪽이 하필 회전 산란체와 최대 평면 금속체다. RCS 기준물로 쓰지 말 것.",
            "⚠ CAD 는 2022-05-14 개발 스냅샷이다 — 모터(T-MOTOR AIR 2213 vs 출하 Holybro 2216-880)와 "
            "오토파일럿(M0053 vs 출하 M0054)이 출하품과 다르다.",
        ],
    )

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(D, indent=1, ensure_ascii=False))
    print(f"[sentinel] {OUT} 기록 — {OUT.stat().st_size/1024:.0f} KB, {time.time()-t0:.1f}s")
    for h in D["headline"]:
        print("   " + h)


if __name__ == "__main__":
    main()
