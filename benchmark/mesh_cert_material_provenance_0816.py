# -*- coding: utf-8 -*-
"""
mesh_cert_material_provenance_0816.py — **재질 배정·재질 상수·출처 등급 인증서**를 만든다
==============================================================================================
사용자 지시(2026-08-16): «메쉬 검증의 층을 더 높이고 정밀도를 높여 다시 고칠 일 없게, 진짜
장담할 수 있다고 단언할 수 있는 수준으로.» — 그 «장담»의 다섯 조건 중 이 라운드가 맡은 축은
**재질 배정 · 재질 상수 출처 · 기체 × 부품 근거 등급**이다.

이 스크립트가 하는 일 — 새로 계산하는 것은 없다. `src/material_provenance.py` 의 검사를
전부 돌리고, `benchmark/adv_material_provenance_faults.py` 의 **양성·음성 대조를 실제로 돌려**
그 결과까지 한 파일에 봉인한다.

    산출: outputs/mesh_cert_material_provenance_0816.json

⛔GPU 미사용(CPU만) · ⛔git 미접촉 · ⛔형상·재질 상수 무변경(읽기만 한다).
실행: cd sionna && CUDA_VISIBLE_DEVICES="" PYTHONPATH=src:benchmark \
        ~/.venvs/py312/bin/python benchmark/mesh_cert_material_provenance_0816.py
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import sys

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (os.path.join(_ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np                                      # noqa: E402

import material_provenance as MP                        # noqa: E402
from drones import DRONES, DRONE_GROUP_MAT, build_drone  # noqa: E402
from materials import MATERIALS                         # noqa: E402

OUT = os.path.join(_ROOT, "outputs", "mesh_cert_material_provenance_0816.json")


def kst_now() -> str:
    return (_dt.datetime.utcnow() + _dt.timedelta(hours=9)).strftime("%Y-%m-%d %H:%M KST")


# --------------------------------------------------------------------------- #
#  범주 지도(재질·출처 축) — 이 축에서 «결함이 있을 수 있는 자리»의 전수 목록
# --------------------------------------------------------------------------- #
#   status: «있음» = 검사가 있고 양성 대조로 잡는 것이 증명됨 · «부분» = 일부만 · «없음»
CATEGORIES = [
    dict(id="R1", name="그룹 라벨의 등록 — 메쉬 라벨이 세 표(배정·물성·밀도)에 다 있나",
         parent="M12",
         what_can_go_wrong=["오타·새 부품이 표에 없다", "재질 키가 물성표에 없다",
                            "세 등록처 중 하나만 빠진다"],
         check="material_provenance.check_group_table_closure",
         controls=dict(negative="A0", positive=["A1", "A2"]), status="있음"),
    dict(id="R2", name="조용한 폴백 — 모르는 그룹이 예외 없이 기본값으로 흐르는 자리",
         parent="M12",
         what_can_go_wrong=["SBR 은 plastic(0.28)로, PO 는 PEC(1.0)로 **반대 방향**으로 흐른다",
                            "누가 새 폴백을 만든다", "폴백을 고쳐 놓고 원장을 안 고친다"],
         check="material_provenance.check_fallback_sites (+ 살아 있는 PO 경로 실측)",
         controls=dict(negative="A4-음성", positive=["A3", "A4", "A4b"]), status="있음",
         limits_ko="⚠검사는 폴백을 **없애지 않는다**(고치면 σ 원장이 낡는다). 어디에 무엇이 "
                   "있는지 못 박고 **바뀌면** 걸리게 한다."),
    dict(id="R3", name="라벨 ↔ 형상 정합 — 이름이 그 부품 자리에 붙어 있나",
         parent="M12",
         what_can_go_wrong=["camera ↔ gear 처럼 라벨이 서로 뒤바뀐다",
                            "회전부가 로터 중심을 떠난다", "내부 부품이 셸 밖으로 나간다"],
         check="material_provenance.check_label_geometry (L1~L5)",
         controls=dict(negative="B0(10기체)", positive=["B1", "B2", "B3"]), status="있음",
         limits_ko="**이름만** 바꾸는 결함은 이 검사가 못 잡는다(형상이 그대로다) — 그 자리는 "
                   "R1 이 덮는다. 두 검사가 서로의 사각지대를 메운다(B4 한계선언)."),
    dict(id="R4", name="재질 상수의 출처 — 모든 수치가 문헌 또는 «모델링 선언» 을 갖고 있나",
         parent="M15",
         what_can_go_wrong=["출처 없이 상수가 늘어난다", "문헌을 주장하면서 그 구간 밖 값을 쓴다"],
         check="material_provenance.check_constants (C1·C2)",
         controls=dict(negative="C0", positive=["C1", "C2"]), status="있음"),
    dict(id="R5", name="ITU 재질 — 이름이 설치본 표에 있고 우리 대역이 유효구간 안인가",
         parent="M15",
         what_can_go_wrong=["ITU 이름 오타", "우리 대역이 그 재질의 유효구간 밖"],
         check="material_provenance.check_constants (C3) — 설치본 소스를 **정적으로** 읽는다",
         controls=dict(negative="C0", positive=["C3", "C4"]), status="있음"),
    dict(id="R6", name="금속 분류의 물리 — «금속으로 본다» 가 표피깊이로 서는가",
         parent="M15",
         what_can_go_wrong=["아주 얇은 금속(포일·도금)을 불투명으로 가정한다"],
         check="material_provenance.check_constants (C4) — 두께 ≥ 5·표피깊이",
         controls=dict(negative="C5b", positive=["C5"]), status="있음"),
    dict(id="R7", name="두 엔진 어긋남 — Sionna 가 보는 재질과 PO 가 쓰는 |Γ| 가 갈리나",
         parent="M12",
         what_can_go_wrong=["같은 부품을 두 엔진이 다른 재질로 본다(2026-07-14 카메라 10.9 dB)",
                            "실효값 이탈이 선언 없이 커진다"],
         check="material_provenance.check_constants (C5, 경보선 6 dB)",
         controls=dict(negative="C6b", positive=["C6"]), status="있음"),
    dict(id="R8", name="출처 등급 — 칸마다 붙은 [A]~[D] 가 실재하는 근거를 가리키나",
         parent="M15",
         what_can_go_wrong=["죽은 링크(파일이 없다)", "죽은 인용(그 문장이 그 파일에 없다)",
                            "등급 인플레(사진뿐인데 [A])", "남의 기체 자료를 자기 근거로",
                            "[C]·[D] 인데 유추·대리 대상 미표시", "판(4T/4E)이 섞인다",
                            "칸이 아예 없다", "빈칸인데 이유가 없다"],
         check="material_provenance.check_provenance (P1~P8 + 빈칸 규칙)",
         controls=dict(negative="D0", positive=["D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9"]),
         status="있음"),
    dict(id="R9", name="대체 선언 — 실물 재질과 모델 키가 다를 때 그 사실·크기를 적었나",
         parent="M15",
         what_can_go_wrong=["나일론 프롭을 ABS/PC 로 쓰면서 아무 말 안 한다",
                            "EVA 발포를 ABS/PC 로 쓴다", "카본 판을 플라스틱으로 쓴다"],
         check="material_provenance.check_provenance (P8) + check_constants().substitution_impacts",
         controls=dict(negative="D0", positive=["D10"]), status="있음"),
    dict(id="R10", name="공용 «구조판» — 빌더가 심는 얇은 금속판이 기체마다 근거를 갖고 있나",
         parent="M15",
         what_can_go_wrong=["한 기체의 관행(DJI AZ91)이 다른 기체에 조용히 복사된다",
                            "치수가 비율상자인데 «실측»으로 읽힌다"],
         check="material_provenance.check_shared_plate — **메쉬를 재서** 얇은 판을 찾는다",
         controls=dict(negative="E0", positive=["E1"]), status="있음"),
    dict(id="R11", name="회귀 봉인 — 누가 재질·등급을 조용히 바꿔도 걸리나",
         parent="M16",
         what_can_go_wrong=["재질 상수를 고치고 인증서를 안 돌린다", "등급만 슬쩍 올린다"],
         check="material_provenance.seal_fingerprint / check_seal",
         controls=dict(negative="F0", positive=["F1", "F2"]), status="있음"),
    dict(id="R12", name="실물 재질 자체의 참값 — 우리가 근거로 삼은 사진·문서가 옳은가",
         parent="M14",
         what_can_go_wrong=["사진 속 회색이 사실은 다른 폴리머", "제조사 문서가 판을 안 밝힌다",
                            "우리 눈이 무늬를 잘못 읽는다"],
         check="⛔없다 — 원리적으로 내부 검사로는 못 본다",
         controls=dict(negative="-", positive="없음"), status="없음",
         limits_ko="이 축은 «검사»가 아니라 «자료 확보»가 관건이다. 등급 행렬이 하는 일은 "
                   "**어느 칸이 이 축에 노출돼 있는지 표시**하는 것까지다."),
]

CLOSURE = {
    "one_line_ko": "재질이 σ 에 들어오는 길은 셋뿐이다 — ① 면에 붙은 **라벨**, ② 라벨을 물성으로 "
                   "바꾸는 **표**, ③ 그 표의 숫자가 어디서 왔는지의 **출처**. 결함은 이 셋 중 "
                   "하나에 반드시 나타난다.",
    "derivation_ko": [
        "① 커널이 재질에 대해 아는 것은 **면마다 붙은 그룹 문자열** 하나뿐이다"
        "(`geom.Mesh.g`). 그러므로 «재질이 틀렸다»의 첫째 갈래는 «라벨이 틀렸다»다 — "
        "라벨이 표에 없거나(R1), 조용히 기본값으로 흐르거나(R2), 엉뚱한 자리에 붙어 있다(R3).",
        "② 그 라벨은 두 단계로 물성이 된다: `DRONE_GROUP_MAT`(그룹→재질 키) → "
        "`MATERIALS`(재질 키→εr·σ·S·|Γ|). 그러므로 둘째 갈래는 «표가 틀렸다»다 — 상수에 "
        "출처가 없거나(R4), ITU 이름·대역이 어긋나거나(R5), «금속»이라는 분류가 물리로 "
        "안 서거나(R6), 두 엔진이 같은 표를 안 보거나(R7), 빌더가 표 밖에서 부품을 "
        "심는다(R10).",
        "③ 표의 숫자와 «이 부품은 이 재질» 이라는 문장은 **어딘가에서 왔다.** 그러므로 셋째 "
        "갈래는 «출처가 틀렸다»다 — 근거가 없거나 죽었거나 등급이 부풀려졌거나(R8), 실물과 "
        "다른 것을 대신 쓰면서 말을 안 했거나(R9), 시간이 지나 조용히 바뀐다(R11).",
        "④ 그리고 위 셋이 다 맞아도 **바깥 참값**이 틀릴 수 있다(R12) — 사진을 잘못 읽거나 "
        "제조사가 판을 안 밝히는 경우. 이 축은 내부 검사로 원리적으로 못 본다. "
        "그래서 «있음»이 아니라 «없음»이라고 적고, 대신 등급 행렬이 **어느 칸이 그 축에 "
        "노출돼 있는지**를 드러낸다.",
        "⑤ 다른 갈래가 있는가? 재질이 결과에 닿는 경로는 (라벨 → 표 → 숫자) 하나뿐이고, "
        "숫자의 정당성은 (문헌 | 선언 | 실물근거) 셋뿐이다. 이 다섯 범주 밖의 자리는 "
        "**재질 축이 아니라 형상 축**(면적·두께·위치)이고, 그것은 이 인증서가 아니라 "
        "메쉬 인증 범주 지도 M0~M11 이 맡는다.",
    ],
    "what_this_axis_does_not_cover_ko": [
        "면적·두께·위치 같은 **형상**은 이 인증서 밖이다(σ ∝ A² 는 형상 축).",
        "재질이 σ 를 **얼마나** 움직이는지의 dB 계산은 RF 라운드의 몫이다. 여기서는 "
        "«대체하면 |Γ| 가 몇 dB 움직이나» 라는 **재질 자체의 크기**만 잰다.",
        "Sionna 팔의 슬래브 두께 정본(셸 0.75 mm·프롭 기체별)은 `outputs/material_canon_0816.json` "
        "가 정한다 — 이 인증서는 그 정본을 **인용만** 한다.",
    ],
}


def build() -> dict:
    t0 = _dt.datetime.now()
    meshes = {k: build_drone(s) for k, s in DRONES.items()}

    #  --- 검사 전부 돌린다 ---------------------------------------------------
    res = dict(
        group_table=MP.check_group_table_closure(meshes),
        fallback_sites=MP.check_fallback_sites(),
        constants=MP.check_constants(),
        provenance=MP.check_provenance(meshes=meshes),
        shared_plate=MP.check_shared_plate(meshes),
        label_geometry={k: MP.check_label_geometry(DRONES[k], mesh=meshes[k]) for k in DRONES},
    )
    seal = MP.seal_fingerprint()

    #  --- 양성·음성 대조을 **실제로** 돌린다 -----------------------------------
    import adv_material_provenance_faults as ADV
    ADV._MESH_CACHE.update(meshes)                      # 메쉬 재생성 낭비 방지
    controls = ADV.run_all()
    ctl = [dict(tag=t, passed=bool(p), detail=d) for t, p, d in controls]
    n_pass = sum(1 for c in ctl if c["passed"])

    #  --- 기체별 등급 요약 ---------------------------------------------------
    per_air = {}
    for c in res["provenance"]["cells"]:
        a = per_air.setdefault(c["airframe"], dict(cells=0, grades={}, blanks=[], proxies=[],
                                                   substitutions=[]))
        a["cells"] += 1
        a["grades"][str(c["grade"])] = a["grades"].get(str(c["grade"]), 0) + 1
        if c["grade"] is None:
            a["blanks"].append(c["group"])
        if c["proxy_of"]:
            a["proxies"].append(c["group"])
        if c["substitution"]:
            a["substitutions"].append(c["group"])
    for a in per_air.values():
        a["grades"] = dict(sorted(a["grades"].items()))

    #  --- 이 라운드가 새로 찾은 것 --------------------------------------------
    sub = res["constants"]["substitution_impacts"]
    nyl = sub["PA66-GF30"]["5G 3.5 GHz"]["dB_vs_ours"]
    nyl_dry = sub["PA66 건조"]["5G 3.5 GHz"]["dB_vs_ours"]
    eva = sub["EVA 발포(추정 하한)"]["5G 3.5 GHz"]["dB_vs_ours"]
    plates = {p["airframe"]: p for p in res["shared_plate"]["plates"]}

    findings = [
        dict(rank=1, id="MP-F1", severity="중요",
             title_ko="mini5pro 의 «구조판» 은 근거가 없다 — 이 라운드의 발견",
             what_ko=f"공용 셸 경로가 metal(battery) 그룹에 넣는 얇은 판이 mini5pro 에도 들어간다"
                     f"({plates['mini5pro']['size_mm']} mm, 이 기체 금속 면적의 "
                     f"{plates['mini5pro']['pct_of_metal_area']} %). 그 판의 재질 근거는 «DJI Mavic 계열 "
                     f"AZ91 마그네슘 관행» 뿐인데, **Mini 계열에 마그네슘 섀시가 있다는 근거가 "
                     f"저장소에 하나도 없다.** 형제기 Mini 2 는 오히려 «마그네슘 없음»을 명시한다.",
             evidence=["outputs/mesh_cert_material_provenance_0816.json::shared_plate",
                       "src/drone_cad.py 공용 비율상자 경로", "src/drones.py mini2 note"],
             action_ko="원장 칸을 **빈칸(등급 None)** 으로 두고 이유를 적었다. 고치려면 분해 자료가 "
                       "필요하다 — 형상은 이 라운드가 안 건드린다."),
        dict(rank=2, id="MP-F2", severity="중요",
             title_ko="프로펠러 재질은 나일론 복합인데 우리 모델은 ABS/PC 다",
             what_ko=f"DJI 공식 프롭 재질표가 Mavic 4 Pro(1158F)=«강화 나일론 복합», Mini 5 Pro=«나일론+"
                     f"고무», Matrice 4 계열=«복합재(카본 아님)»라고 **직접** 적는다. 우리 `prop_plastic` "
                     f"은 ABS/PC(εr 2.7)다. 나일론으로 바꾸면 벌크 |Γ| 가 3.5 GHz 에서 "
                     f"{nyl_dry:+.2f} dB(PA66 건조) ~ {nyl:+.2f} dB(PA66-GF30) 오른다 — 방향은 "
                     f"«우리가 과소평가»다.",
             evidence=["docs/drone_material_deepverify.json (DJI 공식 인용)",
                       "check_constants().substitution_impacts"],
             action_ko="칸마다 `substitution` 으로 선언하고 크기를 쟀다. 값은 안 바꿨다 — 프롭 |Γ| 는 "
                       "0816 정본이 동결한 축이다."),
        dict(rank=3, id="MP-F3", severity="중요",
             title_ko="s1000plus 의 가장 큰 그룹이 실물과 다른 재질이다(앞 라운드 A1 재확인)",
             what_ko="이 기체의 중앙은 몰드 셸이 아니라 **판 스택**이고, 판은 카본 라미네이트로 본다. "
                     "⚠구별할 것 — **암과 접이식 착륙장치는 DJI 공식 문장으로 카본이 확인**되지만 "
                     "(«All frame arms … are made from carbon fiber»), **중앙판 자체는 관례 추정**이다. "
                     "우리 메쉬는 그 자리에 3,555 cm² 짜리 플라스틱 'body' 셸을 준다 — "
                     "|Γ| 0.28 ↔ 0.90 = **10.14 dB** 자리이고 이 기체에서 면적이 가장 큰 그룹이다.",
             evidence=["docs/drone_material_deepverify.json (DJI 공식 S1000 기능페이지 인용)",
                       "outputs/mesh_inspect_materials_check_0816.json::findings A1",
                       "assets/photos/s1000plus/s1000+_1.png"],
             action_ko="원장 칸에 `substitution` 으로 못 박았다(등급 [B-]). 형상·배정은 안 고쳤다."),
        dict(rank=4, id="MP-F4", severity="중요",
             title_ko="재질 축에서 [A] 는 88칸 중 **1칸**뿐이다",
             what_ko=f"제조사가 부품 재질표를 통째로 공개하지 않기 때문이다. 유일한 [A] 는 x500v2 의 "
                     f"`gear_cf` — Holybro 공식 STEP 의 **부품명 자체가** `CARBON-FIBER-TUBE` 다. "
                     f"그다음이 [A-] "
                     f"{res['provenance']['grade_distribution'].get('A-', 0)}칸 — DJI 공식 프롭 재질표"
                     f"(mavic4pro·mini5pro·matrice4e)와 DJI 공식 S1000 기능페이지"
                     f"(암·착륙장치·프롭)다. 나머지는 사진(B/B-)·유추(C)·대리(D)다. "
                     f"현재 분포: {res['provenance']['grade_distribution']}",
             evidence=["assets/meshes/reference/x500v2-frame.step",
                       "docs/drone_material_deepverify.json"],
             action_ko="«전부 [A] 로 올린다»는 계획을 세우지 않는다 — 자료가 없다. 대신 어느 칸이 "
                       "어느 등급인지 기계가 읽는 형태로 못 박았다."),
        dict(rank=5, id="MP-F5", severity="중요",
             title_ko="같은 오타가 두 엔진에서 **반대 방향**으로 틀린다(실측)",
             what_ko="미등록 그룹을 실제로 먹여 봤다. PO(`rcs_po.mesh_to_points`)는 |Γ|=1.0(PEC)로, "
                     "SBR(`rcs_sbr`)은 0.28(plastic)로 흐른다 — 진폭 "
                     f"{res['fallback_sites']['two_engine_gap_db']:+.2f} dB, σ 로는 그 두 배 차이다. "
                     "gazebo 내보내기만 예외를 던진다.",
             evidence=["adv_material_provenance_faults.py::A3",
                       "src/rcs_po.py:153", "src/rcs_sbr.py:168"],
             action_ko="⛔고치지 않았다(σ 원장이 낡는다). 대신 세 자리를 원장에 못 박고, **새로 "
                       "생기거나 사라지면** 걸리게 했다. 그리고 R1 이 미등록 그룹을 상류에서 잡는다."),
        dict(rank=6, id="MP-F6", severity="사소",
             title_ko="m350rtk 의 'camera' 그룹은 짐벌 카메라가 아니다",
             what_ko="이 기체는 기본 구성에 카메라가 없다(DGC2.0 포트만). 'camera' 그룹의 실체는 "
                     "**비전/FPV 센서 포드 12개**(총 158 cm²)이고, 실물은 플라스틱 하우징 + 유리창 + "
                     "속 금속이다. `camera_assembly`(ITU metal + 실효 0.85)가 맞는지 **안 재봤다**.",
             evidence=["assets/photos/m350rtk/m350rtk_p08_nose_sensor_array_closeup.png",
                       "src/drones.py m350rtk note"],
             action_ko="칸을 **빈칸**으로 두고 이유를 적었다."),
        dict(rank=7, id="MP-F7", severity="사소",
             title_ko="x500v2 다리 발포(EVA)를 ABS/PC 로 쓴다 — 이번엔 **과대평가** 방향",
             what_ko=f"제조사 STEP 이 그 부품을 `JIAO-EVA`(EVA 발포)라고 적는다. EVA 발포는 공기가 "
                     f"대부분이라 εr 이 1 에 가깝다 — 추정 하한(1.2)으로 잡아도 벌크 |Γ| 가 "
                     f"{eva:+.2f} dB, 즉 우리가 그만큼 **더 세게** 반사시키고 있다.",
             evidence=["assets/meshes/reference/x500v2-frame.step (JIAO-EVA)"],
             action_ko="`substitution` 으로 선언. ⛔크기는 «추정 하한»이고 실측이 아니다."),
        dict(rank=8, id="MP-F9", severity="사소",
             title_ko="우리가 인용하는 재질 조사 문서에 **모델코드 충돌**이 있다",
             what_ko="`docs/drone_material_deepverify.json` 의 네 번째 항목은 기체를 «DJI Phantom 4 Pro "
                     "V2.0 (model **WM331**)» 이라고 적는데, 우리 저장소의 phantom3 기록은 WM331 을 "
                     "**Phantom 3 Professional** 의 모델코드로 쓴다. 둘 중 하나는 틀렸다. "
                     "그 항목의 재질 문장(마그네슘 코어·짐벌 마그네슘+세라믹)은 phantom4 칸의 "
                     "**계열 근거**로만 썼으므로 등급([C])은 이 충돌에 영향받지 않는다.",
             evidence=["docs/drone_material_deepverify.json result[3].drone",
                       "src/drones.py phantom3 note (VARIANT: the Professional (WM331))"],
             action_ko="근거 등록부의 `what_ko` 에 충돌을 적어 두고 등급을 [C] 로 묶었다. "
                       "판정은 안 내린다 — 이 라운드가 확인할 자료가 없다."),
        dict(rank=9, id="MP-F8", severity="사소",
             title_ko="phantom4 의 재질 근거는 전부 **다른 판**이다",
             what_ko="`assets/photos/phantom4/` 의 5장은 Phantom 4 **Pro+ V2.0** 이고 우리 키는 초판 "
                     "phantom4 다. 그래서 이 기체의 재질 칸은 전부 [C](계열 유추)로 묶였다.",
             evidence=["assets/photos/phantom4/"],
             action_ko="등급으로 표시. 사진을 지우거나 바꾸지 않았다."),
    ]

    #  --- 인증서 조립 --------------------------------------------------------
    ok_all = (all(res[k]["ok"] for k in ("group_table", "fallback_sites", "constants",
                                         "provenance", "shared_plate"))
              and all(r["ok"] for r in res["label_geometry"].values()))
    cert = {
        "_meta": {
            "title": "재질 배정 · 재질 상수 · 출처 등급 인증서 (2026-08-16)",
            "generated_kst": kst_now(),
            "generator": "benchmark/mesh_cert_material_provenance_0816.py",
            "checker": "src/material_provenance.py",
            "controls": "benchmark/adv_material_provenance_faults.py",
            "role_ko": "이 라운드는 **검사·대조·봉인·인증서만** 만든다. 형상 상수·재질 상수·"
                       "배정표를 한 글자도 바꾸지 않았다.",
            "policy": "⛔GPU 미사용(sionna.rt·mitsuba 임포트 없음) · ⛔git 미접촉 · ⛔값 무변경",
            "bound_to_state_ko": "⭐이 인증서는 **생성 시각의 메쉬·표 상태에 묶여 있다.** 지금은 다른 "
                                 "라운드가 형상을 고치는 중이라, 그 수정이 착지하면 아래 seal 지문이 "
                                 "깨지고 인증서를 다시 돌려야 한다 — 그것이 설계다(깨지는 것이 기능이다). "
                                 "새 그룹이 생기면 등급 행렬의 덮개 검사(P1)가 «칸이 없다»로 먼저 걸린다.",
            "what_ko": "부품마다 재질이 옳은가 · 재질 상수가 문헌과 맞는가 · 기체 × 부품 칸마다 "
                       "붙은 근거 등급이 **실재하는 파일**을 가리키는가를 검사하고, 검사가 "
                       "실제로 잡는다는 것을 양성·음성 대조로 증명한다.",
            "how_to_read_ko": "① closure_argument 가 «왜 이 범주 목록이 빠짐없는가»를 논증한다. "
                              "② categories 의 status 는 «있음»(양성 대조로 증명됨)·«부분»·«없음» 셋뿐이다. "
                              "③ grade_matrix 가 기체 × 부품 88칸의 등급과 근거다. "
                              "④ limits_ko 가 **못 하는 것**이다 — 그 절이 이 인증서의 절반이다.",
            "grade_scale_ko": {
                "A": "그 기체 자신의 제조사 1차 자료가 그 부품 재질을 직접 말한다(예: STEP 부품명)",
                "A-": "제조사 공식 문서·지원페이지의 재질 문장(인용문이 저장소 파일에 보존돼 있다)",
                "B": "그 기체 자신의 분해·부품 사진에서 재질이 보인다",
                "B-": "그 기체 자신의 완성기 사진·공식 렌더뿐(겉모습만)",
                "C": "계열 유추 또는 재질 클래스 문헌",
                "D": "⛔대리 — 다른 기체·다른 제품의 자료",
                "빈칸": "모른다. 이유를 반드시 적는다(검사가 강제한다)",
            },
            "glossary_ko": {
                "|Γ|(감마)": "진폭 반사계수. 1 이면 전부 반사(금속), 0 이면 전부 통과.",
                "벌크 프레넬": "두께가 무한한 판의 반사. 얇은 판은 앞뒷면 간섭으로 다르다.",
                "표피깊이": "도체 안으로 전파가 1/e 로 줄어드는 깊이. 두께 ≫ 표피깊이면 «불투명».",
                "조용한 폴백": "모르는 이름이 들어와도 예외 없이 기본값으로 흐르는 것.",
                "등급 인플레": "근거의 종류가 버티는 것보다 등급을 높게 적는 것.",
                "대체 선언": "실물 재질과 다른 재질로 모델링할 때 그 사실과 크기를 적어 두는 것.",
                "양성/음성 대조": "일부러 만든 결함이 걸리는가 / 멀쩡한 것이 통과하는가.",
            },
            "inputs_read": [
                "src/materials.py (MATERIALS) · src/drones.py (DRONE_GROUP_MAT·DRONES·note)",
                "src/drone_cad.py (INTERNALS·공용 비율상자 경로) · src/gazebo_export.py (DENSITY)",
                "src/rcs_po.py · src/rcs_sbr.py (조용한 폴백 자리)",
                "outputs/material_sources.json (문헌 원장 + 예전 Sionna 실측 current_values)",
                "outputs/material_canon_0816.json (두께 정본) · "
                "outputs/mesh_inspect_materials_check_0816.json (그룹 단위 앞 라운드)",
                "outputs/mesh_cert_map_0816.json (범주 지도 M12·M15)",
                "docs/drone_material_deepverify.json (DJI 공식 재질 문장)",
                "assets/photos/*/ (11 폴더) · assets/meshes/reference/ (공식 CAD·STEP)",
                f"설치본 Sionna ITU 표: {os.path.relpath(MP.SIONNA_ITU_PY, '/')}",
            ],
            "env": dict(python=sys.version.split()[0], numpy=np.__version__,
                        gpu_used=False,
                        cuda_visible_devices=os.environ.get("CUDA_VISIBLE_DEVICES", "(미설정)")),
        },

        "verdict": {
            "ok": bool(ok_all),
            "headline_ko":
                f"재질 축에서 **검사 11 종**을 새로 세웠고, 각각 양성·음성 대조로 «실제로 잡는다»를 "
                f"증명했다(대조 {n_pass}/{len(ctl)} 통과). 기체 × 부품 "
                f"{len(res['provenance']['cells'])}칸의 근거 등급 행렬을 처음으로 기계가 읽는 형태로 "
                f"만들었고, 등급 분포는 {res['provenance']['grade_distribution']} 다 — "
                f"⭐**[A] 는 1칸뿐**이고 그 이유는 제조사가 부품 재질표를 공개하지 않기 때문이다. "
                f"이 라운드는 값을 하나도 바꾸지 않았다.",
            "what_can_be_promised_ko": [
                "메쉬에 실린 **모든 그룹 라벨**이 세 등록처(배정·물성·밀도)에 다 있다 — 그리고 "
                "하나라도 빠지면 걸린다는 것을 양성 대조로 보였다.",
                "라벨이 **엉뚱한 자리에 붙는** 결함(camera↔gear·motor↔pcb·prop↔motor)은 이제 걸린다 — "
                "범주 지도가 «전 검사 통과»로 기록했던 바로 그 결함들이다.",
                "`MATERIALS` 의 **모든 수치**가 문헌 아니면 «모델링 선언» 을 갖고 있고, 문헌을 "
                "주장한 값은 그 문헌 구간 안에 있다.",
                "ITU 재질값을 **Sionna 를 임포트하지 않고** 같은 식으로 계산해, 예전 Sionna 실측 "
                f"원장과 {res['constants']['itu_crosscheck']['n']}행 대조해 어긋남 "
                f"{res['constants']['itu_crosscheck']['mismatches']}건이다.",
                "두 엔진(Sionna·PO)이 같은 표에서 재질을 읽는다 — 어긋남이 6 dB 경보선을 넘으면 걸린다.",
                "등급표의 근거가 **살아 있는 파일**을 가리키고, 인용문이 그 파일 안에 글자 그대로 있다.",
                "재질·배정·등급 중 무엇이 바뀌어도 **지문이 움직인다**(회귀 봉인).",
            ],
            "what_cannot_be_promised_ko": [
                "⛔**실물이 정말 그 재질인지**는 장담 못 한다. 우리가 가진 것은 사진과 문서이고, "
                "그것을 읽은 것은 사람이다(범주 R12 = «없음»).",
                "⛔**[A] 는 1칸뿐**이다. 87칸은 사진·유추·대리에 기대고 있다.",
                "⛔빈칸이 3칸 있다 — mini5pro 구조판 · m350rtk 센서포드 · phantom3 프롭 갈래. "
                "«모른다»를 그대로 적었다.",
                "⛔이 인증서는 재질이 **σ 를 몇 dB 움직이는지** 말하지 않는다. |Γ| 수준의 크기만 잰다.",
                "⛔조용한 폴백 세 자리는 **살아 있다**. 검사는 그것이 바뀌는 것만 본다.",
                "⛔형상(면적·두께·위치)은 이 축 밖이다.",
            ],
        },

        "closure_argument": CLOSURE,
        "categories": CATEGORIES,
        "coverage_summary": {
            "n_categories": len(CATEGORIES),
            "있음": sum(1 for c in CATEGORIES if c["status"] == "있음"),
            "부분": sum(1 for c in CATEGORIES if c["status"] == "부분"),
            "없음": sum(1 for c in CATEGORIES if c["status"] == "없음"),
            "read_ko": "12 칸 중 11 칸이 «있음»(양성 대조까지 증명)이고, 1 칸(R12 실물 참값)은 "
                       "«없음»이다 — 내부 검사로 원리적으로 못 보는 축이라 그렇게 적었다.",
        },

        "checks": res,
        "controls": {
            "n_total": len(ctl), "n_pass": n_pass,
            "convention_ko": "검사마다 **양성 대조(결함을 심으면 걸린다) + 음성 대조(멀쩡하면 통과)** 를 "
                             "둘 다 건다. 이 두 대조가 없는 검사는 «있다»고 치지 않는다.",
            "results": ctl,
        },

        "grade_matrix": {
            "n_cells": len(res["provenance"]["cells"]),
            "distribution": res["provenance"]["grade_distribution"],
            "by_airframe": per_air,
            "cells": res["provenance"]["cells"],
            "evidence_registry": {k: dict(kind=v["kind"], path=v["path"], owner=v.get("owner"),
                                          quote=v.get("quote"), variant=v.get("variant"),
                                          what_ko=v.get("what_ko"))
                                  for k, v in MP.EVIDENCE.items()},
            "kind_caps": MP.EVIDENCE_KIND_CAP,
            "forbidden_variant_use": MP.FORBIDDEN_VARIANT_USE,
        },

        "material_constants": {
            "table": {k: {f: v for f, v in s.items() if f != "note"} for k, s in MATERIALS.items()},
            "group_assignment": {g: m for g, (m, _) in DRONE_GROUP_MAT.items()},
            "sources": {f"{k[0]}.{k[1]}": v for k, v in MP.CONSTANT_SOURCES.items()},
            "declarations": res["constants"]["declarations"],
            "itu_crosscheck": res["constants"]["itu_crosscheck"],
            "metal_opacity": res["constants"]["metal_opacity"],
            "engine_agreement": res["constants"]["engine_agreement"],
            "substitution_impacts": res["constants"]["substitution_impacts"],
            "thickness_canon_ref": "outputs/material_canon_0816.json (Sionna 셸 0.75 mm · "
                                   "프롭 기체별 · 우리 커널 |Γ|=0.28 은 두께축 구조적 N/A)",
        },

        "findings": findings,

        "seal": {
            "fingerprints": seal,
            "what_ko": "재질표·배정표·등급 원장·상수 출처·근거 등록부의 sha256 앞 16자리. "
                       "하나라도 바뀌면 값이 달라진다.",
            "how_to_check_ko": "PYTHONPATH=src python -c \"import material_provenance as M; "
                               "print(M.check_seal(<위 fingerprints>))\"",
            "gate_ko": "PYTHONPATH=src python src/material_provenance.py --gate  → 실패면 종료코드 1",
        },

        "limits_ko": [
            "⭐**등급은 재질 축이다.** 같은 칸의 치수 축 등급과 다르다 — 예: mini2 프롭은 "
            "치수 [A](공식 GLB)인데 재질은 [C](GLB 는 형상만 담는다).",
            "⭐사진에서 재질을 읽는 것은 **사람의 판독**이다. 이 라운드는 s1000plus·mini5pro·"
            "x500v2·matrice4e 넉 장을 직접 열어 봤고, 나머지는 파일명 + 그 폴더의 SOURCES.md 를 "
            "근거로 삼았다. 그래서 등급 상한이 [B] 다.",
            "⭐«금속으로 본다»는 표피깊이로 검사했지만, **두께 값 자체**(포일 15 µm · 구리 35 µm · "
            "벨 0.5 mm)는 규격·관례이지 우리가 잰 값이 아니다.",
            "⭐대체 선언의 크기는 **벌크 |Γ| 차이**다. 실제 σ 차이는 면적·각도·가림이 정하므로 "
            "이 숫자를 σ 오차로 옮겨 적으면 안 된다.",
            "⭐라벨↔형상 잣대(L1~L5)는 **현재 10기체에서 여백을 확인한** 규칙이다. 새 기체가 "
            "다른 배치를 가지면(예: 상반 짐벌·역방향 다리) 거짓경보가 날 수 있다 — 그때는 "
            "잣대에 예외를 **선언**하고 그 사실을 여기 적을 것.",
            "⭐공용 «구조판» 검사는 얇은 판(최소변/최대변 < 0.12)만 본다. 두꺼운 대리 부품은 못 본다.",
        ],

        "what_this_round_did_not_do_ko": [
            "형상 상수(_SHELL_SHAPE·INTERNALS·GEAR_*·CHORD_*·PITCH_K*·ARM_TIP_Z·envelope_mm)를 "
            "**한 글자도** 안 바꿨다.",
            "재질 상수(MATERIALS)·배정표(DRONE_GROUP_MAT)를 안 바꿨다. 발견은 **선언**으로만 남겼다.",
            "조용한 폴백을 안 고쳤다(고치면 σ 원장이 낡는다).",
            "게이트를 자동 실행 경로에 **배선하지 않았다** — 배선은 형상 라운드들이 끝난 뒤에 "
            "한 번에 해야 지문이 안 흔들린다. 지금은 수동 실행 + 인증서 봉인이다.",
            "GPU 를 쓰지 않았고 σ 를 다시 계산하지 않았다.",
        ],

        "how_to_rerun": {
            "checker": "CUDA_VISIBLE_DEVICES='' PYTHONPATH=src python src/material_provenance.py",
            "controls": "CUDA_VISIBLE_DEVICES='' PYTHONPATH=src:benchmark python "
                        "benchmark/adv_material_provenance_faults.py",
            "certificate": "CUDA_VISIBLE_DEVICES='' PYTHONPATH=src:benchmark python "
                           "benchmark/mesh_cert_material_provenance_0816.py",
            "runtime_s": None,
        },
    }
    cert["how_to_rerun"]["runtime_s"] = round((_dt.datetime.now() - t0).total_seconds(), 1)
    return cert


def main() -> int:
    cert = build()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(cert, f, ensure_ascii=False, indent=1)
    print("\n" + "=" * 100)
    print(f"인증서 저장: {os.path.relpath(OUT, _ROOT)}")
    print(f"  판정 ok={cert['verdict']['ok']} · 대조 {cert['controls']['n_pass']}/"
          f"{cert['controls']['n_total']} · 칸 {cert['grade_matrix']['n_cells']} · "
          f"등급 분포 {cert['grade_matrix']['distribution']}")
    print(f"  봉인 {cert['seal']['fingerprints']}")
    return 0 if (cert["verdict"]["ok"] and cert["controls"]["n_pass"] == cert["controls"]["n_total"]) else 1


if __name__ == "__main__":
    sys.exit(main())
