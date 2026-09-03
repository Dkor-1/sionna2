# -*- coding: utf-8 -*-
"""
build_volumes.py — ⭐**조각을 권으로 묶는다**

권 수와 조각 수는 이 파일이 손으로 적지 않는다 — 편성(`VOLUMES` + `EXTERNAL`)과 디스크에서
세어 `outputs/volumes_index.json` 의 `_meta` 에 적고, 본문은 그 값을 주입해 쓴다.

사용자:
> *"레포트를 지금 너무 심하게 잘게 쪼갠 거 같은데... 그래도 적당히 **하나의 메시지를 담아서**
>  해주면 좋겠어. 0~6 을 한 **20 개 이내로** 적당히 메시지가 담기게끔 구성해주면 좋겠고,
>  7 번도 7 번을 고집한다기보다는 **순서상 어울리는 위치로** 레포트 번호를 매겨서 만들어줘."*

⭐ 실행 순서 — 이 스크립트는 **맨 마지막**이다
------------------------------------------------
    ① 조각 빌더 전부         src/build_part00_map.py … src/build_part13_engine_physics.py
                             (개수는 `src/build_part*.py` 를 세어 본문에 주입한다)
                             → reports/_parts/NN_slug.ipynb
    ② 6 권 빌더              src/make_report08_microdoppler.py
                             → reports/06_1_scene.ipynb … 06_4_sampling.ipynb
    ②' 6-5 바이스태틱 빌더  src/make_report07b_bistatic.py → reports/06_5_bistatic.ipynb
    ②" 외부 별편 빌더        src/make_report11_2_two_channel.py → reports/08_2_two_channel.ipynb
                             src/build_report18_switch_grid.py  → reports/05_2_switch-grid.ipynb
    ③ **이 스크립트**        src/build_volumes.py
                             → reports/NN_slug.ipynb 권 파일 + 6 권 후처리 + 색인 + README
    ④ 검사                   benchmark/check_report_links.py

②가 아직 없으면 6 권 후처리를 **조용히 건너뛰고 경고만** 찍는다 — 빌드는 죽지 않는다.

설계 — 빌더는 그대로 두고 그 위에 «묶는 층» 을 얹는다
------------------------------------------------------
⭐ 조각의 숫자는 전부 원장 JSON 에서 주입된다(`src/build_partNN_*.py`). 손으로 합치면 그
   사슬이 끊긴다. 그래서 이 스크립트는 **조각을 다시 쓰지 않는다** — 빌더가 만든 조각을 읽어
   순서대로 잇고, 권 단위로 **각주를 다시 매기고**, 조각 사이 **상호참조를 새 권·절 번호로
   고쳐 쓰고**, 권의 머리말을 앞에 붙인다.
   ⇒ 재계산 → 조각 빌더 재실행 → 이 스크립트 재실행이면 권의 숫자도 함께 갱신된다.

   조각:  reports/_parts/NN_slug.ipynb   (빌더 산출 · **사람이 직접 읽는 문서가 아니다**)
   권  :  reports/NN_slug.ipynb          (사람이 읽는 문서 · 편성은 VOLUMES + EXTERNAL 이 정본 ·
                                          6 권만 그림이 무거워 여러 편 · 별편 지위는 COMPANIONS)

이 스크립트가 손대는 다섯 가지
------------------------------
1. **각주 재번호** — 조각마다 `[^1]` 부터 다시 세므로, 그냥 이으면 한 권 안에서 번호가 겹친다.
   조각을 이을 때 그 앞까지의 최대 번호만큼 밀어 정의·인용을 함께 옮긴다.
2. **상호참조 재배선** — 조각 본문의 `[편 22 «…»](22_po-knee.ipynb)` 는 78 편 시절의 주소다.
   조각은 이제 `_parts/` 에 살고 사람이 여는 문서가 아니므로, 그 링크를 새 주소로 고친다.
       다른 편을 가리키면 → `[리포트 2 절 5 «…»](02_kernel.ipynb)`
       같은 편을 가리키면 → `**절 5** «…»`  (자기 파일로 되돌아가는 링크를 만들지 않는다)
   같은 손질을 옛 12 부 참조(`[부 4 «산란 커널»](../README.md#…)`)와 인라인 코드 주소
   (`` `reports/37_md-rpm.ipynb` ``)에도 한다.
3. **지도 권 생성** — 1 권의 첫 절은 조각이 아니라 이 스크립트가 짓는다. 옛 조각 `00_map`
   은 «78 편 · 12 부» 라는 폐지된 구조 자체를 설명하는 글이라 재배선으로 살릴 수 없다.
   대신 여기서 전 권의 목차·조각 배치·읽는 경로를 **편성과 디스크에서 다시 만든다.**
4. **6 권 후처리** — 6 권은 그림이 무거워 다섯 편으로 나뉘고, 다른 빌더가 낸다(위 ②·②').
   이 스크립트는 그 다섯 편의 **주소만 고치고**, 옛 부 7 조각(34~39)을 `06_3_pattern.ipynb`
   뒤에 절로 **덧붙인다**. 덧붙인 셀에는 표식을 달아 두므로 다시 돌려도 겹쳐 쌓이지 않는다.
5. **색인과 목차** — `outputs/volumes_index.json`(기계용)과 `reports/README.md`(사람용).

    PYTHONPATH=src python src/build_volumes.py
"""
from __future__ import annotations

import datetime as _dt
import glob as _glob
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import report_style as RS                                              # noqa: E402

PARTS = os.path.join(_ROOT, "reports", "_parts")
OUT = os.path.join(_ROOT, "reports")
INDEX = os.path.join(_ROOT, "outputs", "volumes_index.json")
INDEX_REL = "outputs/volumes_index.json"

#: 덧붙인 절에 다는 표식 — 다시 돌릴 때 이 표식이 붙은 셀부터 걷어낸다(겹쳐 쌓이지 않게).
APPEND_TAG = "from_parts"

#: 편 수를 한글로 — 본문이 «네 편/열일곱 권» 을 손으로 적지 않게 한다.
#:  ⭐ 권이 늘면 여기까지 함께 늘려야 한다. 표에 없는 수는 아라비아 숫자로 떨어진다.
_KOR_COUNT = {1: "한", 2: "두", 3: "세", 4: "네", 5: "다섯", 6: "여섯", 7: "일곱",
              8: "여덟", 9: "아홉", 10: "열", 11: "열한", 12: "열두", 13: "열세",
              14: "열네", 15: "열다섯", 16: "열여섯", 17: "열일곱", 18: "열여덟",
              19: "열아홉", 20: "스무"}


def _kor(n: int) -> str:
    return _KOR_COUNT.get(n, str(n))


def _disp(no: str) -> str:
    """권 번호의 산문 표기 — "01"→"1", "01_2"→"1-2", "10_2"→"10-2".

    위계 번호("01_2")는 `int()` 에 넣으면 ValueError 다 — 표시 지점은 전부 이 함수를 쓴다.
    """
    h, _, t = no.partition("_")
    return str(int(h)) + (f"-{t}" if t else "")


def _no_key(no: str) -> tuple[int, int]:
    """권 번호의 수치 정렬 키 — "01"→(1,0), "01_2"→(1,2). 동률 판정 등 계산용이다."""
    h, _, t = no.partition("_")
    return (int(h), int(t) if t else 0)


def _part_builders() -> list[str]:
    """조각 빌더 파일 이름 — 디스크에서 센다. 조각이 늘면 재현 절차의 개수도 따라 는다."""
    return sorted(os.path.basename(p)
                  for p in _glob.glob(os.path.join(_HERE, "build_part*.py")))

# --------------------------------------------------------------------------- #
#  이 스크립트가 조립하는 권 — 한 권 = 하나의 메시지
#    (번호, 슬러그, 제목, 한 줄 논지, [조각 번호…], 결론 조각)
#  ⭐ 본편 8박자 = «장면(01) → 커널(02) → 검증(03) → 앙각(04) → 스위치(05) →
#     마이크로도플러(06) → 디텍션(07~10) → 실측(11)». 마이크로도플러(06)만 아래
#     EXTERNAL 이 맡는다 — 그림이 무거워 다섯 편으로 나뉘기 때문이다.
#  ⭐ 번호에 `_` 가 든 권(01_2 류)은 **별편** — 부모 권 물음의 심화·지원·변주라
#     부모번호_K 로 내려가 있다. 조립 경로(_placement·_assemble)를 그대로 쓰려고
#     VOLUMES 에 남긴다 — 편성 지위의 정본은 COMPANIONS 다.
#  ⭐ 마지막 칸은 «이 권을 한 절만 읽는다면 어디» — 빨리 훑는 경로가 여기서 만들어진다.
# --------------------------------------------------------------------------- #
VOLUMES = [
    ("01", "map", "이 연구가 묻는 것과 답한 방식",
     "패시브 바이스태틱으로 드론을 **탐지하고 마이크로도플러로 분류**하는 것이 태스크이고, "
     "RCS 는 그 인프라다. 이 권은 나머지 ⟦권수-1⟧ 권과 거기 딸린 별편들의 지도다.",
     ["13", "75"], "75"),
    ("01_2", "prior-work", "선행연구는 어디까지 왔고 우리는 어디 서는가",
     "공개 문헌과 오픈소스를 전수로 세어, 우리가 **새로 하는 것과 빌려 쓰는 것**을 갈라 적는다.",
     ["08", "09", "10", "11", "12", "14"], "08"),
    ("02", "kernel", "우리 커널 — 무엇이고, 무엇이 아닌가",
     "SBR + 물리광학이 무엇을 계산하고 무엇을 **계산하지 않는지**를 정의하고, "
     "해석해가 있는 과녁(구·평판·이면각)으로 잰다.",
     ["18", "19", "20", "21", "22", "23"], "21"),
    ("02_2", "stock-engine", "스톡 Sionna 로는 왜 부족한가",
     "스톡 레이 트레이서는 경로를 풀지 **산란적분을 하지 않는다**. "
     "그 한 가지가 드론처럼 작은 표적에서 무엇을 무너뜨리는지 여덟 갈래로 잰다.",
     ["01", "02", "03", "04", "05", "06", "07"], "06"),
    ("02_3", "target-mesh", "표적을 짓는다 — 메쉬와 재질",
     f"기체 {len(RS.fetch(('outputs/mesh_gallery.json', 'order_by_size')))} 대를 CAD 로 짓고, "
     f"그중 σ 를 내는 {RS.fetch(('outputs/report02_derived.json', 'mesh.n')):.0f} 대를 실물 "
     f"사진·도면과 대조한다. **재질은 측정이 아니라 선언**이고, 그 선언이 어디까지 미치는지 "
     f"함께 적는다.",
     ["15", "16", "17"], "16"),
    ("03", "anchor", "σ 를 무엇에 붙들어 매나",
     "우리 σ 의 절대 레벨을 붙드는 것은 **공개 문헌 한 기체·한 실험실**뿐이다. "
     "그 끈의 장력을 재고, 끊어질 자리를 먼저 적는다.",
     ["24", "25", "26", "27", "28", "29"], "24"),
    ("03_2", "size-law", "표적을 얼마나 거칠게 그려도 되나 — 사다리와 크기 법칙",
     "표적 모형을 구·정육면체·상자·평판으로 갈아 끼우는 사다리로 **단순화의 값**을 재고, "
     "앵커보다 크고 작은 두 기체로 **크기전이 법칙**을 가르는 계획을 적는다. "
     "**사다리의 답이 이르게 나오면 그것부터 의심한다.**",
     ["30", "31", "32", "33", "77"], "32"),
    # ------------------------------------------------------------------ #
    #  앙각 축(04)과 엔진 물리 스위치(05).
    #  ⚠ 계획(`outputs/volumes_16_17_plan.json`)의 조각 81 `el-beat-vs-tip` 은 아직
    #    지어지지 않았고, 조각 87 은 예산 축이라 04 의 마지막 절로 세운다.
    #    조각 88 은 그 계획 밖에서 지은 05 의 범위 절이다.
    #  ⭐ 두 권은 무늬(마이크로도플러) 축을 6 권보다 먼저 쓴다 — 그래서 논지 끝에
    #    «무늬 축의 정의는 리포트 6» 한 줄을 달고 간다.
    # ------------------------------------------------------------------ #
    ("04", "elevation-coverage", "앙각 커버리지 — 어느 각도까지 유효한가",
     "관측 앙각을 0° 에서 −90° 까지 내리며 같은 표적을 재면, 커버리지를 정하는 것은 "
     "표적이 아니라 **우리가 고른 분석 대역과 잣대**다. 대역을 날개끝 주파수를 따라 옮기면 "
     "−75° 에서도 프로펠러 대역이 살아 있고, 8/11 덱의 대역을 고정한 채 내려가면 같은 "
     "자리가 바닥에 앉는다. 잣대를 고를 때마다 **광선 예산이 함께 움직인다**는 것이 이 권의 "
     "두 번째 결론이다. 여기서 재는 무늬 축의 정의는 **리포트 6** 에 있다.",
     ["78", "79", "80", "82", "87"], "79"),
    ("05", "engine-physics", "엔진의 물리 스위치 — 켜면 무엇이 달라지나",
     "스톡 PathSolver 의 굴절·회절·모서리회절·다중반사를 하나씩 켜서 **무엇이 결과를 "
     "만들었는지 귀속**한다. 나딧에서 레벨을 66 dB 올리는 것은 회절 하나이고, 그 상승은 "
     "표적 변조(분자)가 아니라 정적 성분(분모)을 키운다. 스위치가 남기는 몫은 **광선 예산을 "
     "맞춘 뒤에야** 읽을 수 있고, 이 비교가 세우는 것은 상대량뿐이다 — 절대 σ 는 이 권 "
     "밖이다. 여기서 재는 무늬 축의 정의는 **리포트 6** 에 있다.",
     ["83", "84", "85", "86", "88"], "83"),
    # 06 은 EXTERNAL 이 맡는다 — 별편 06_6 만 여기서 조립한다
    ("06_6", "microdoppler-limits", "마이크로도플러 — 무엇이 그 무늬를 흐리나",
     "자세·보정·광선 예산·표본율 네 가지가 무늬를 지운다. "
     "각각을 **단일축으로 갈라** 얼마나 지우는지 잰다.",
     ["40", "41", "42", "43"], "43"),
    ("07", "illuminators", "무엇을 조명원으로 쓸 수 있나",
     "LTE·5G·WiFi 가 각각 **얼마나 자주, 얼마나 넓게** 신호를 내주는가. "
     "5G 는 대역이 넓은 대신 상시 신호가 드물어 **이중고**가 된다.",
     ["44", "45", "46", "47", "48", "49", "50"], "46"),
    ("08", "detector", "처리 사슬 — 직접파를 죽이고 표적을 세운다",
     "ECA 로 직접파를 지우고 CFAR 로 문턱을 세운다. "
     "**문턱을 어디에 두느냐가 결과를 정하므로** 그 교정을 먼저 적는다.",
     ["51", "52", "53", "54"], "53"),
    ("09", "observability", "관측가능성과 기하 — 어디에 서야 보이나",
     "송신기·수신기·표적의 배치가 검출을 정한다. "
     "**볼 수 없는 자리**를 먼저 지도로 그리고, 그 다음에 거리를 말한다.",
     ["55", "56", "57", "58"], "55"),
    ("10", "results", "결과 — 얼마나 멀리서 보이나",
     "R90 과 순위가 이 연구의 정량 결론이다. "
     "적분시간·잔류·σ 가정을 흔들어 **순위가 견디는지**까지 함께 적는다.",
     ["59", "60", "61", "62", "63"], "60"),
    ("10_2", "robustness", "결론이 무엇에 기대고 있나 — 강건성과 하드웨어",
     "표적 모형·수신 소자·장비를 바꿔 넣어 **결론이 어디서 흔들리는지** 본다.",
     ["64", "65", "66", "67", "68"], "64"),
    ("11", "measurement", "실측 계획 — 무엇을 재야 이 문서가 닫히나",
     "시뮬레이션이 선언으로 남겨 둔 것들의 목록과, 그것을 닫는 **야외 실측 규약**이다.",
     ["69", "70", "71", "72", "73", "74", "76"], "74"),
]

# --------------------------------------------------------------------------- #
#  다른 빌더가 내는 권 — 이 스크립트는 주소를 고치고 조각을 덧붙일 뿐이다
#    ⭐ 6 권은 그림이 무거워(애니메이션 GIF 포함) 한 파일에 담기지 않는다. 그래서 다섯 편이다.
#       이것은 **분권**(한 권의 장)이지 별편이 아니다 — 지위는 아래 COMPANIONS 가 정한다.
#    ⚠ 06_5(바이스태틱)만 빌더가 다르다 — src/make_report07b_bistatic.py 다.
# --------------------------------------------------------------------------- #
EXTERNAL = [
    dict(no="06", title="마이크로도플러 — 도는 로터가 남기는 무늬",
         thesis="호버링하는 드론은 제자리에 있지만 **프로펠러는 돈다**. "
                "그 회전이 남기는 시간-주파수 무늬가 이 연구의 분류 축이다. "
                "그림이 무거워 **다섯 편**으로 나뉜다.",
         builder="src/make_report08_microdoppler.py "
                 "(06_5 만 src/make_report07b_bistatic.py)",
         files=[("06_1_scene.ipynb", "무엇을 보고 있나 — 시나리오와 신호의 정체"),
                ("06_2_engines.ipynb", "어떻게 계산하나 — 세 엔진과 거리"),
                ("06_3_pattern.ipynb", "무엇이 무늬를 정하나 — 회전수·가림·산포"),
                ("06_4_sampling.ipynb", "무엇을 잴 수 있나 — 광선 비용과 반복률"),
                ("06_5_bistatic.ipynb",
                 "송수신이 갈라지면 — 바이스태틱 도플러·플래시·에코")],
         append_to="06_3_pattern.ipynb",
         parts=["34", "35", "36", "37", "38", "39"],
         headline="36"),

    #: ⭐한 파일짜리 외부 권 — 이 스크립트가 **짓지 않고 자리만 잡아 준다.**
    #  ⛔2026-09-03 까지 편성에 없어서 지도(01_map)·목차(README)·색인 어디에도 안 걸렸다.
    #    그동안 셋 다 «노트북 23 개» 라고 적었는데 디스크에는 25 개가 있었다.
    dict(no="12", title="실외 장면 — 지면과 벽이 서면 무엇이 달라지나",
         thesis="자유공간에서 세운 판정이 **지면과 건물이 있는 자리**에서도 서는지 묻는다. "
                "실외 기록의 날개 박자는 솔버 인공물에 가려 있었고, 그 인공물의 정체는 "
                "지면 거울 반사였다.",
         builder="src/build_report12_outdoor.py",
         files=[("12_outdoor-scene.ipynb",
                 "실외 장면 — 지면과 벽이 서면 무엇이 달라지나")],
         #: parts 가 비어 있어 실제로 덧붙는 것은 없다 — 경로만 유효하면 된다.
         append_to="12_outdoor-scene.ipynb", parts=[], headline=None),
]


def _split_vols():
    """**분권** — 그림 무게로 여러 편에 나눈 한 권. 나뉜 것이 정의라 files 가 둘 이상이다.
    ⛔한 파일짜리 외부 권(12)을 여기 세면 «1 편으로 나뉜다» 같은 말이 생긴다."""
    return [e for e in EXTERNAL if len(e["files"]) > 1]

# --------------------------------------------------------------------------- #
#  권에 딸린 별편 — 편성 지위의 **정본**이다. {부모 번호: [별편…]}
#    별편 = 부모 권 물음의 **심화·지원·변주**이고, 번호가 «부모번호_K» 다.
#    ⭐ 분권(EXTERNAL 의 06_1~06_5)과는 지위가 다르다 — 분권은 그림 무게로 나눈 한 권의
#       장이고, 별편은 따로 선 문서다. 06_6 은 파일명만 분권 꼬리를 잇고 지위는 별편이다.
#    두 종을 함께 담는다:
#      · **조립 별편** `vol=` — VOLUMES 튜플을 가리키는 포인터. 이 스크립트가 조각으로
#        조립하고, 파일·표시번호·제목·설명은 그 튜플에서 자동 유도한다(`_companions`).
#      · **외부 별편** `file=`… — 다른 빌더가 자기 파일을 낸다. 표시값을 여기 적는다.
#    지도는 이것도 세어 적는다 — 세지 않으면 디스크에 있는 노트북이 목차에서 사라진다.
# --------------------------------------------------------------------------- #
COMPANIONS = {
    "01": [dict(vol="01_2")],
    "02": [dict(vol="02_2"), dict(vol="02_3")],
    "03": [dict(vol="03_2")],
    "05": [dict(file="05_2_switch-grid.ipynb",
                label="5-2",
                title="물리 스위치 격자 — 회절은 리듬을 지우지 않고 리듬 없는 에코로 덮는다",
                what="5 권이 단일축으로 귀속한 회절을 굴절·회절·모서리회절 7 조합 전수 "
                     "격자로 다시 재고, 절대 세기로 읽어 기전을 가른다 — 회절을 켠 판은 "
                     "끈 판을 계수 ≈1 로 품고 있고, 날개끝 위 바닥이 올라와 원래 빗살을 "
                     "덮는다(빗각 −15°~−75°)",
                builder="src/build_report18_switch_grid.py")],
    "06": [dict(vol="06_6")],
    "08": [dict(file="08_2_two_channel.ipynb",
                label="8-2",
                title="기준채널이 현실이면 얼마를 잃는가",
                what="8 권의 사슬을 한 줄도 안 고치고, 기준신호를 «송신 파형 그대로» 에서 "
                     "«잡음·다중경로가 섞인 측정 신호» 로 바꿔 손실을 잰다",
                builder="src/make_report11_2_two_channel.py")],
    "10": [dict(vol="10_2")],
}

#: 조립 별편의 «빌더» 칸 — 이 스크립트가 조각을 이어 짓는다는 뜻이다.
#: ⚠ 순수 스크립트 이름(`src/build_volumes.py`)으로 적지 마라 — README 가 빌더 이름으로
#:   별편을 되찾을 때 «조각 → 권» 단계와 충돌한다.
ASSEMBLED_BY = "src/build_volumes.py (조각 조립)"

#: 별편 총수 — 편성이 바뀔 때 **뜻을 정하고** 함께 고치는 자리다(아래 import assert 가 강제).
N_COMPANIONS = 8


def _comp_no(c: dict) -> str:
    """별편 항목의 권 번호 — `vol=` 포인터이거나 파일 이름 앞 두 자리(`08_2_…` → `08_2`)."""
    if c.get("vol"):
        return c["vol"]
    head, tail = os.path.basename(c["file"]).split("_")[:2]
    return f"{head}_{tail}"


def _vol_tuple(no: str) -> tuple:
    for v in VOLUMES:
        if v[0] == no:
            return v
    raise KeyError(no)


def _check_companions() -> None:
    """번호 문법을 **코드가 강제한다** — import 때 돈다.

    ① 편성의 `_` 번호는 전부 COMPANIONS 에 정확히 1 회 등재 ② 그 접두 = 부모 키
    ③ 부모 키에 `_` 없음(**별편의 별편 금지**) ④ 별편 합계 = `N_COMPANIONS`.
    """
    hosts = [v[0] for v in VOLUMES] + [e["no"] for e in EXTERNAL]
    seen: dict[str, str] = {}
    for parent, cs in sorted(COMPANIONS.items()):
        assert "_" not in parent, f"별편의 별편은 없다 — 부모 키 «{parent}» 에 `_` 가 있다"
        assert parent in hosts, f"부모 권 «{parent}» 이 편성(VOLUMES·EXTERNAL)에 없다"
        for c in cs:
            no = _comp_no(c)
            assert "_" in no, f"별편 번호 «{no}» 에 `_` 가 없다 — 별편은 «부모번호_K» 다"
            assert no not in seen, f"별편 «{no}» 이 두 번 등재됐다({seen[no]} · {parent})"
            seen[no] = parent
            assert no.partition("_")[0] == parent, \
                f"별편 «{no}» 의 접두가 부모 키 «{parent}» 와 다르다"
            if c.get("vol"):
                assert any(v[0] == no for v in VOLUMES), \
                    f"조립 별편 «{no}» 의 VOLUMES 튜플이 없다"
            else:
                assert c.get("label") == _disp(no), \
                    f"외부 별편 «{no}» 의 label 이 표기 규칙({_disp(no)})과 다르다"
    for no in hosts:
        if "_" in no:
            assert no in seen, f"위계 번호 «{no}» 이 COMPANIONS 에 없다 — 지위가 색인에서 빠진다"
    assert len(seen) == N_COMPANIONS, \
        f"별편이 {len(seen)} 편이다 — 편성을 바꿨으면 N_COMPANIONS 도 함께 고쳐라"


_check_companions()

# --------------------------------------------------------------------------- #
#  권 수는 편성에서 센다 — VOLUMES 나 EXTERNAL 에 권을 더하면 본문의 «몇 권» 이 함께 바뀐다.
#  ⭐ 세는 것은 **본편**(번호에 `_` 가 없는 권)뿐이다 — «열한 권» 은 본편 수이고,
#     별편 8 편은 따로 센다(`_n_companions`). 둘을 합치면 노트북 23 개다.
#  VOLUMES 의 논지에 박아 둔 ⟦권수⟧·⟦권수-1⟧ 자리를 여기서 채운다.
# --------------------------------------------------------------------------- #
def _trunk_nos() -> list[str]:
    """본편 번호 — 편성에서 `_` 가 없는 번호만. 지도·README 의 «몇 권» 이 이것이다."""
    return sorted([v[0] for v in VOLUMES if "_" not in v[0]]
                  + [e["no"] for e in EXTERNAL if "_" not in e["no"]])


N_VOLUMES = len(_trunk_nos())

VOLUMES = [v[:3] + (v[3].replace("⟦권수-1⟧", _kor(N_VOLUMES - 1))
                        .replace("⟦권수⟧", _kor(N_VOLUMES)),) + v[4:]
           for v in VOLUMES]

#: 1 권 첫 절(지도)은 조각이 아니라 이 스크립트가 짓는다.
MAP_VOL = "01"
MAP_SECTION_TITLE = f"{_kor(N_VOLUMES)} 권의 지도 — 무엇이 어디에 있나"


def _n_companions() -> int:
    return sum(len(v) for v in COMPANIONS.values())


def _kind(no: str) -> str:
    """권의 지위 — 본편이면 "trunk", 별편이면 "companion"."""
    return "companion" if "_" in no else "trunk"


def _parent_of(no: str) -> str | None:
    """별편이면 부모 권 번호("01_2"→"01"), 본편이면 None."""
    h, _, t = no.partition("_")
    return h if t else None


def _companions(parent: str) -> list[dict]:
    """부모 권에 딸린 별편 — 표시에 필요한 칸이 전부 찬 사전으로 돌려준다.

    조립 별편(`vol=`)은 파일·표시번호·제목·설명을 VOLUMES 튜플에서 유도한다. 그래서
    편성에서 슬러그나 제목을 고치면 지도·색인·README 가 손대지 않아도 따라온다.
    """
    out: list[dict] = []
    for c in COMPANIONS.get(parent, []):
        d = dict(c)
        no = _comp_no(c)
        if c.get("vol"):
            _no, slug, title, thesis, _parts, _hd = _vol_tuple(no)
            d.setdefault("file", f"{no}_{slug}.ipynb")
            d.setdefault("label", _disp(no))
            d.setdefault("title", title)
            d.setdefault("what", _th_short(thesis, 120).rstrip(" .·"))
            d.setdefault("builder", ASSEMBLED_BY)
        d["no"], d["parent"] = no, parent
        out.append(d)
    return out

#: 읽는 경로 ② «왜 믿을 수 있나» — 검증·대조·반증 조각만. (경로 ① 은 각 권의 결론 절이다)
VERIFY_PARTS = ["01", "04", "05", "21", "22", "26", "27", "28", "29", "33",
                "41", "53", "54", "61", "63", "76"]

#: 폐지된 조각 — 재배선으로 살릴 수 없어 권에 넣지 않는다(사유는 아래 표에 적는다).
SUPERSEDED = {
    "00": "«편 78 개 · 부 12 개» 라는 폐지된 편성 자체를 설명하는 글이라, 번호만 고쳐서는 "
          "말이 서지 않는다. 그 자리는 이 스크립트가 짓는 1 권 절 1 «지도» 가 대신한다.",
}

# --------------------------------------------------------------------------- #
#  정규식
# --------------------------------------------------------------------------- #
_FN_REF = re.compile(r"\[\^(\d+)\]")                       # 각주(정의·인용 공통)
#: 그림 번호 — 조각마다 «그림 1» 부터 다시 세므로 그냥 이으면 한 권 안에 «그림 1» 이 여럿이다.
#: 각주와 같은 방식으로 권 단위로 다시 매긴다. 캡션(`**그림 1.**`)과 산문의 참조(`그림 2 에서`)를
#: 같은 만큼 옮겨야 짝이 유지된다.
#: ⚠ «그림 3 개/장/편» 은 **수량**이지 번호가 아니다 — 건드리지 않는다.
_FIG_NUM = re.compile(r"그림\s*(\d+)(?!\s*(?:개|장|편))")
_FIG_CAP_NO = re.compile(r"\*\*그림\s*(\d+)\.\*\*")         # 캡션 — 그림 번호의 정의
#: 조각 사이 참조 — `[편 22 «…»](22_po-knee.ipynb)`
_XREF = re.compile(r"\[\s*편\s*(\d{2})\s*([^\]]*?)\s*\]\(\s*(\d{2})_([a-z0-9\-]+)\.ipynb"
                   r"(?:#[^)]*)?\s*\)")
#: 인라인 코드로 적힌 조각 주소 — `` `reports/37_md-rpm.ipynb` `` · `` `35_md-slowtime` ``
#: ⚠ 권 파일 이름도 같은 꼴(`07_illuminators.ipynb`)이다. 번호만 보고 고치면 **이미
#:   새 주소로 적힌 글을 옛 주소로 오인해 망가뜨린다.** 그래서 슬러그까지 조각 파일명과
#:   대조해서, 실제로 조각을 가리킬 때만 고친다(`_is_part_name`).
_CODEREF = re.compile(r"`(?:\.\./)?(?:reports/)?(\d{2})_([a-z0-9\-]+?)(?:\.ipynb)?`")
#: 옛 12 부 참조 — `[부 4 «산란 커널»](../README.md#부-4-산란-커널)`
_PARTREF = re.compile(r"\[\s*부\s*(\d{1,2})\s*([^\]]*?)\s*\]\(\s*\.\./README\.md#[^)]*\)")
#: 링크가 아닌 산문의 옛 부 번호 — `부 7 의 표지다`
_PARTPROSE = re.compile(r"(?<![가-힣\w])부\s*(\d{1,2})\s*(?=(?:의|가|는|를|에|다|와|과))")
_H1_LINE = re.compile(r"^#\s*리포트\s*\d+\s*—.*\n?")
_H1_TITLE = re.compile(r"#\s*리포트\s*\d+\s*—\s*(.+)")
_SEC_H2 = re.compile(r"^##\s*절\s*(\d+)\.", re.M)


# --------------------------------------------------------------------------- #
#  조각 읽기
# --------------------------------------------------------------------------- #
def _part_file(no: str) -> str:
    hits = sorted(f for f in os.listdir(PARTS)
                  if f.startswith(f"{no}_") and f.endswith(".ipynb"))
    if not hits:
        raise FileNotFoundError(f"조각 {no} 를 {PARTS} 에서 못 찾았다 — 조각 빌더를 먼저 돌려라")
    return hits[0]


def _load_part(no: str) -> tuple[str, str, list]:
    """조각 하나 → (파일명, 제목, 셀들)."""
    fn = _part_file(no)
    nb = json.load(open(os.path.join(PARTS, fn), encoding="utf-8"))
    cells = nb["cells"]
    head = "".join(cells[0]["source"]) if cells else ""
    m = _H1_TITLE.match(head)
    return fn, (m.group(1).strip() if m else fn), cells


def _all_parts_on_disk() -> list[str]:
    return sorted(f[:2] for f in os.listdir(PARTS) if re.match(r"^\d{2}_.*\.ipynb$", f))


def _is_part_name(no: str, slug: str) -> bool:
    """`NN_slug` 가 진짜 조각 파일 이름인가. 권 파일 이름과 헷갈리지 않으려고 대조한다."""
    try:
        return _part_file(no)[:-len(".ipynb")] == f"{no}_{slug}"
    except FileNotFoundError:
        return False


def _text(c: dict) -> str:
    s = c.get("source", "")
    return s if isinstance(s, str) else "".join(s)


def _strip_appended(cells: list[dict]) -> list[dict]:
    """앞선 실행이 덧붙인 절을 걷어낸다 — 다시 돌려도 겹쳐 쌓이지 않게."""
    return [c for c in cells if APPEND_TAG not in (c.get("metadata", {}).get("tags") or [])]


# --------------------------------------------------------------------------- #
#  배치표 — 조각 → (권, 편 파일, 절)
# --------------------------------------------------------------------------- #
def _host_base(fname: str) -> int:
    """덧붙일 파일이 이미 들고 있는 «절 N» 의 개수. 파일이 없으면 0."""
    p = os.path.join(OUT, fname)
    if not os.path.exists(p):
        return 0
    try:
        cells = _strip_appended(json.load(open(p, encoding="utf-8"))["cells"])
    except Exception:                                                  # noqa: BLE001
        return 0
    ns = [int(n) for c in cells for n in _SEC_H2.findall(_text(c))]
    return max(ns) if ns else 0


def _placement() -> dict[str, dict]:
    """조각 번호 → {vol, file, sec, vol_title}. 절 번호는 생성 절까지 포함해 센다."""
    out: dict[str, dict] = {}
    for no, slug, title, _th, parts, _hd in VOLUMES:
        base = 1 if no == MAP_VOL else 0          # 1 권의 절 1 은 생성된 지도다
        for i, p in enumerate(parts, 1 + base):
            out[p] = dict(vol=no, file=f"{no}_{slug}.ipynb", sec=i, vol_title=title)
    for ex in EXTERNAL:
        base = _host_base(ex["append_to"])
        for i, p in enumerate(ex["parts"], 1 + base):
            out[p] = dict(vol=ex["no"], file=ex["append_to"], sec=i,
                          vol_title=ex["title"])
    return out


def _vol_entry(no: str) -> dict:
    """권 번호 → 표시용 {no, title, thesis, files, headline, external}."""
    for v in VOLUMES:
        if v[0] == no:
            return dict(no=no, title=v[2], thesis=v[3], external=False,
                        files=[(f"{v[0]}_{v[1]}.ipynb", v[2])], headline=v[5])
    for ex in EXTERNAL:
        if ex["no"] == no:
            return dict(no=no, title=ex["title"], thesis=ex["thesis"], external=True,
                        files=ex["files"], headline=ex["headline"])
    raise KeyError(no)


def _ordered_nos() -> list[str]:
    """편성의 모든 권 번호 — 본편과 **조립 별편**을 함께, 읽는 순서대로.

    문자열 정렬이 위계 번호에서도 옳다("01"<"01_2"<"02"<…<"06_6"<"07"<…<"10"<"10_2"<"11").
    «몇 권» 을 셀 때는 이것이 아니라 `_trunk_nos()` 다.
    """
    return sorted([v[0] for v in VOLUMES] + [e["no"] for e in EXTERNAL])


def _bu_to_vol(place: dict[str, dict]) -> dict[str, str]:
    """옛 «부 N» → 그 부의 조각이 가장 많이 들어간 권. 부 편성은 레지스트리가 정본이다."""
    try:
        from report_registry import PARTS as _BU                       # noqa: N811
    except Exception:                                                  # noqa: BLE001
        return {}
    out: dict[str, str] = {}
    for bu, meta in _BU.items():
        tally: dict[str, int] = {}
        for p in meta.get("reports", []):
            v = place.get(p, {}).get("vol")
            if v:
                tally[v] = tally.get(v, 0) + 1
        if tally:
            #  동률이면 앞 권 — 위계 번호가 섞이므로 int() 가 아니라 `_no_key` 로 센다.
            out[str(bu)] = max(tally.items(),
                               key=lambda kv: (kv[1], tuple(-x for x in _no_key(kv[0]))))[0]
    return out


# --------------------------------------------------------------------------- #
#  본문 손질
# --------------------------------------------------------------------------- #
def _shift_footnotes(src: str, off: int) -> str:
    if off == 0:
        return src
    return _FN_REF.sub(lambda m: f"[^{int(m.group(1)) + off}]", src)


def _max_footnote(src: str) -> int:
    ns = [int(m.group(1)) for m in _FN_REF.finditer(src)]
    return max(ns) if ns else 0


def _shift_figures(src: str, off: int) -> str:
    """그림 번호를 권 단위로 다시 매긴다 — 캡션과 산문의 참조를 함께 옮긴다."""
    if off == 0:
        return src
    return _FIG_NUM.sub(lambda m: f"그림 {int(m.group(1)) + off}", src)


def _max_figure(src: str) -> int:
    """이 조각이 정의한 그림의 마지막 번호 — **캡션**만 센다(참조는 정의가 아니다)."""
    ns = [int(m.group(1)) for m in _FIG_CAP_NO.finditer(src)]
    return max(ns) if ns else 0


def _relink(src: str, cur_file: str, place: dict[str, dict],
            bu2vol: dict[str, str], stat: dict) -> str:
    """78 편 시절 주소를 새 권·절 주소로 고쳐 쓴다. 같은 **파일** 안이면 링크를 안 만든다."""

    def _addr(tgt: str, rest: str, kind: str) -> str | None:
        p = place.get(tgt)
        if p is None:
            return None
        tail = f" {rest}" if rest else ""
        if p["file"] == cur_file:
            stat[f"{kind}_intra"] = stat.get(f"{kind}_intra", 0) + 1
            return f"**절 {p['sec']}**{tail}"
        stat[f"{kind}_cross"] = stat.get(f"{kind}_cross", 0) + 1
        return f"[리포트 {_disp(p['vol'])} 절 {p['sec']}{tail}]({p['file']})"

    def _x(m: re.Match) -> str:
        if not _is_part_name(m.group(3), m.group(4)):    # 권 파일이면 손대지 않는다
            return m.group(0)
        out = _addr(m.group(3), m.group(2).strip(), "xref")
        if out is not None:
            return out
        stat["xref_dropped"] = stat.get("xref_dropped", 0) + 1
        return f"**{m.group(2).strip()}**" if m.group(2).strip() else "이 문서"

    def _c(m: re.Match) -> str:
        if not _is_part_name(m.group(1), m.group(2)):    # 권 파일이면 손대지 않는다
            return m.group(0)
        out = _addr(m.group(1), "", "coderef")
        return out if out is not None else m.group(0)

    def _vol_link(v: str, rest: str, cur: str) -> str:
        e = _vol_entry(v)
        tail = f" {rest}" if rest else f" «{e['title']}»"
        if cur in [f for f, _t in e["files"]]:
            return f"**이 권**{tail}"
        return f"[리포트 {_disp(v)}{tail}]({e['files'][0][0]})"

    def _b(m: re.Match) -> str:
        v = bu2vol.get(str(int(m.group(1))))
        if v is None:
            return m.group(0)
        stat["buref"] = stat.get("buref", 0) + 1
        return _vol_link(v, m.group(2).strip(), cur_file)

    def _bp(m: re.Match) -> str:
        v = bu2vol.get(str(int(m.group(1))))
        if v is None:
            return m.group(0)
        stat["buprose"] = stat.get("buprose", 0) + 1
        e = _vol_entry(v)
        if cur_file in [f for f, _t in e["files"]]:
            return "이 권 "
        return f"리포트 {_disp(v)} "

    return _PARTPROSE.sub(_bp, _PARTREF.sub(_b, _CODEREF.sub(_c, _XREF.sub(_x, src))))


def _cell(src: str, ctype: str = "markdown", meta: dict | None = None) -> dict:
    return {"cell_type": ctype, "metadata": meta or {},
            "source": [l + "\n" for l in src.rstrip("\n").split("\n")]}


# --------------------------------------------------------------------------- #
#  권 머리말 · 절 구분자
# --------------------------------------------------------------------------- #
def _vol_intro(no: str, title: str, thesis: str,
               sections: list[tuple[str, str, str]], headline_sec: int | None) -> dict:
    """권의 머리말 — 하나의 메시지, 절 목록, 그 절이 어느 조각에서 왔나."""
    lines = [f"# 리포트 {_disp(no)} — {title}", "",
             f"> {thesis}", ""]
    #  ⭐별편은 자기 머리에 부모를 선언한다 — 이 편만 열어도 어디에 딸린 글인지 알게.
    par = _parent_of(no)
    if par is not None:
        pe = _vol_entry(par)
        lines += [f"이 편은 [리포트 {_disp(par)} «{pe['title']}»]({pe['files'][0][0]}) 의 "
                  "**별편**이다 — 그 권 물음의 심화·지원·변주이지, 그림 무게로 나눈 분권이 "
                  "아니다.", ""]
    lines += ["이 권은 아래 절로 이루어진다. 각 절은 **한 일 · 결과 · 방법 · 재현** 을 자기 앞에 "
              "달고 있어, 필요한 절만 따로 읽어도 된다.", "",
              "| 절 | 무엇을 말하나 | 만든 곳 |", "|---|---|---|"]
    for i, (part, t, fn) in enumerate(sections, 1):
        star = " ⭐" if headline_sec == i else ""
        where = "이 권을 조립할 때 생성" if part == "gen" else f"`_parts/{fn}`"
        lines.append(f"| {i}{star} | {t} | {where} |")
    lines += ["",
              "⭐ 표시한 절 하나만 읽어도 이 권의 결론은 선다.", "",
              "숫자는 전부 계산 결과 JSON(원장)에서 주입된다 — 절 끝 «출처» 표가 그 파일과 키다. "
              "원장이 다시 계산되면 빌더를 돌리는 것만으로 본문 숫자가 따라 바뀐다.", ""]
    comps = _companions(no)
    if comps:
        lines += [f"이 권에는 별편이 {_kor(len(comps))} 편 딸려 있다 — 이 권의 물음을 더 "
                  "파고들거나 받쳐 주는 글이다.", ""]
        lines += [f"- [리포트 {c['label']} «{c['title']}»]({c['file']}) — {c['what']}."
                  for c in comps]
        lines.append("")
    lines.append("전체 목차는 [reports/README.md](README.md) 다."
                 if no == MAP_VOL else
                 f"전체 목차는 [reports/README.md](README.md) 이고, {_kor(N_VOLUMES)} 권의 지도는 "
                 f"[리포트 {_disp(VOLUMES[0][0])} «{VOLUMES[0][2]}»]"
                 f"({VOLUMES[0][0]}_{VOLUMES[0][1]}.ipynb) 다.")
    return _cell("\n".join(lines))


def _section_rule(idx: int, title: str, meta: dict | None = None) -> dict:
    return _cell(f"---\n\n## 절 {idx}. {title}", meta=meta)


# --------------------------------------------------------------------------- #
#  1 권 절 1 — 지도(생성물)
# --------------------------------------------------------------------------- #
def _map_cells(place: dict[str, dict], titles: dict[str, str]) -> list[dict]:
    n_vol = N_VOLUMES                          # 본편 수 — 별편은 아래에서 따로 센다
    bld = _part_builders()                     # 재현 절차의 «조각 빌더 N 개» 는 디스크에서 센다
    cells: list[dict] = []

    cells.append(_cell(
        "> ### 한 일\n"
        f"> **조각 빌더가 낸 편들을 «하나의 메시지 = 한 권» 기준으로 본편 {_kor(n_vol)} 권과 "
        f"거기 딸린 별편 {_n_companions()} 편에 배치하고, 권 안에서 각주와 상호참조를 다시 "
        "매겼다.**\n"
        "\n"
        "### 결과\n"
        f"1. 사람이 읽는 문서는 본편 ⟨{INDEX_REL} : _meta.n_volumes⟩ 권 + 별편 "
        f"⟨{INDEX_REL} : _meta.n_companions⟩ 편(노트북 "
        f"⟨{INDEX_REL} : _meta.n_notebooks⟩ 개)이고, 그 안에 들어간 조각은 "
        f"⟨{INDEX_REL} : _meta.n_parts_placed⟩ 편이다. 한 권이 물음 하나를 들고, "
        "권 제목이 그 물음이다.\n"
        f"2. `reports/_parts/` 의 조각 ⟨{INDEX_REL} : _meta.n_parts_on_disk⟩ 편은 "
        "**사람이 직접 읽는 문서가 아니다** — 빌더의 중간 산출물이고, 권을 조립하는 재료다. "
        "고칠 일이 생기면 조각이 아니라 그 조각을 만든 빌더를 고친다.\n"
        f"3. 조각 사이 상호참조 ⟨{INDEX_REL} : _meta.n_crossrefs⟩ 개는 «리포트 N 절 M» 주소로 "
        "다시 쓰였고, 각주는 편 단위로 다시 번호가 매겨졌다.\n"
        + "".join(
            f"4. 한 권이 한 파일인 것이 규칙이고, **{_disp(ex['no'])} 권만 그림이 무거워 "
            f"{_kor(len(ex['files']))} 편**이다 — 파일이 커지면 열리지 않기 때문이지 "
            f"메시지가 {_kor(len(ex['files']))} 개여서가 아니다. 이 나눔은 **분권**이라 "
            "별편과 지위가 다르다."
            + (f" 별편은 따로 {_n_companions()} 편이고, 번호가 «부모번호-K» 다.\n"
               if COMPANIONS else "\n")
            for ex in EXTERNAL)
        + "5. 읽는 목적이 셋이면 순서도 셋이다 — **빨리 훑기**(본편마다 결론 절 하나씩) · "
        "**왜 믿을 수 있나**(검증·대조·반증 절만) · **다시 돌리기**(리포트를 안 읽고 명령만 본다). "
        "논문 문장과 재현 절차는 리포트 밖에 산다 — [`docs/paper/`](../docs/paper/README.md) 와 "
        "[`docs/REPRODUCE.md`](../docs/REPRODUCE.md) 다.\n"))

    cells.append(_cell(
        "### 방법\n"
        "\n"
        "| 무엇을 | 어떻게 얻었나 |\n"
        "|---|---|\n"
        "| 권 하나 = 물음 하나 | 권의 논지 한 줄이 그 권이 답하는 물음이다. 그 물음에 답하는 "
        "절들만 그 권에 모인다 |\n"
        "| 절 = 옛 조각 하나 | 절의 제목과 본문은 조각 빌더가 원장 JSON 에서 낸 그대로다. "
        "묶는 층은 순서·각주·주소만 손댄다 |\n"
        "| 각주 | 조각마다 `[^1]` 부터 다시 세므로, 이을 때 그 앞까지의 최대 번호만큼 밀어 "
        "정의와 인용을 함께 옮긴다 |\n"
        "| 상호참조 | 조각이 들고 있던 옛 주소(`편 22` · `22_po-knee.ipynb`)를 배치표에서 "
        "찾아 새 권·절로 고쳐 쓴다. 같은 편 안이면 링크 대신 «절 N» 으로 적는다 |\n"
        "| 색인 | 어느 조각이 어느 권 몇 절인지를 "
        f"[`{INDEX_REL}`](../{INDEX_REL}) 에 기계용으로 적는다 |\n"
        "\n"
        "### 재현\n"
        "\n"
        "```bash\n"
        f"PYTHONPATH=src python src/{bld[0]:<33s}# ① 조각 빌더 {len(bld)} 개\n"
        f"#  … {bld[1]} … {bld[-1]}\n"
        "PYTHONPATH=src python src/make_report08_microdoppler.py    # ② 6 권 1~4 편\n"
        "PYTHONPATH=src python src/make_report07b_bistatic.py       # ②' 6 권 5 편\n"
        "PYTHONPATH=src python src/make_report11_2_two_channel.py   # ②\" 별편 8-2\n"
        "PYTHONPATH=src python src/build_report18_switch_grid.py    # ②\" 별편 5-2\n"
        "PYTHONPATH=src python src/build_volumes.py                 # ③ 조각 → 권\n"
        "PYTHONPATH=src python benchmark/check_report_links.py      # ④ 검사\n"
        "```\n"
        "\n"
        "| | |\n"
        "|---|---|\n"
        f"| 출력 | `reports/*.ipynb` 본편 {n_vol} 권 · 별편 {_n_companions()} 편 "
        f"(노트북 ⟨{INDEX_REL} : _meta.n_notebooks⟩ 개) · "
        f"`{INDEX_REL}` · `reports/README.md` |\n"
        "| 소요 | 약 3 초 (GPU 0 장) |\n"
        "| 비고 | ③ 은 맨 마지막이다 — ② 가 낸 6 권 파일 뒤에 조각을 덧붙이기 때문이다. "
        "②' 와 ②\" 는 자기 파일만 내므로 ③ 과 순서를 다투지 않는다 |\n"))

    # ── 처음 여는 사람을 위한 말 풀이 ────────────────────────────────────────
    #   ⭐이 권을 처음 여는 사람은 편성이 아니라 **무엇을 하는 연구인가**를 먼저 묻는다.
    #     권 표 앞에 그 한 화면을 둔다 — 뒤 권들이 이 낱말을 설명 없이 쓴다.
    cells.append(_cell(
        "## 처음 여는 사람에게 — 이 연구의 말 다섯\n"
        "\n"
        "레이더를 우리가 쏘지 않는다. 이동통신 기지국이 늘 내보내는 신호를 빌려, 떨어진 곳에 "
        "세운 수신기로 드론이 되돌린 메아리를 듣는다. 아래 다섯 낱말이 그 그림의 이름이다.\n"
        "\n"
        "| 말 | 뜻 |\n"
        "|---|---|\n"
        "| 패시브(passive) | 우리는 아무것도 송신하지 않고 남의 신호를 빌려 쓴다 |\n"
        "| 바이스태틱(bistatic) | 송신하는 곳과 받는 곳이 떨어져 있다. 둘이 같은 자리면 "
        "모노스태틱이다 |\n"
        "| RCS · σ | 표적이 되돌리는 에코의 세기를 넓이(m²)로 환산한 값. 기체의 모양·재질·보는 "
        "각도가 정한다 |\n"
        "| 마이크로도플러 | 도는 프로펠러가 에코에 남기는 시간-주파수 무늬. 기종을 가르는 축이 "
        "이것이다 |\n"
        "| 탐지 · 분류 | 있나 없나를 정하는 것이 탐지, 어느 기종인가를 정하는 것이 분류다 |\n"))

    # ── 본편 표 (두 셀로 나눠 화면에서 읽히게 · 나누는 자리도 권 수에서 센다) ──
    def _vol_rows(nos) -> str:
        out = ["| 권 | 이 권이 답하는 물음 | 절 | 한 절만 읽는다면 |", "|---|---|---|---|"]
        for no in nos:
            e = _vol_entry(no)
            n = _n_sections(no, place)
            p = place.get(e["headline"])
            hl = (f"[절 {p['sec']} «{titles.get(e['headline'], '')}»]({p['file']})"
                  if p else "—")
            out.append(f"| [{_disp(no)} «{e['title']}»]({e['files'][0][0]}) "
                       f"| {_th_short(e['thesis'])} | {n} | {hl} |")
        return "\n".join(out)

    nos = _trunk_nos()                          # 표는 본편만 — 별편은 아래 자기 표에 선다
    cut = (len(nos) + 1) // 2
    cells.append(_cell(f"## 본편 {_kor(n_vol)} 권 (앞 절반)\n\n" + _vol_rows(nos[:cut])))
    cells.append(_cell(f"## 본편 {_kor(n_vol)} 권 (뒤 절반)\n\n" + _vol_rows(nos[cut:])))

    for ex in EXTERNAL:
        rows = "\n".join(f"| [{f}]({f}) | {t} |" for f, t in ex["files"])
        n_files = len(ex["files"])
        cells.append(_cell(
            f"## {_disp(ex['no'])} 권은 {_kor(n_files)} 편이다 — 분권\n"
            "\n"
            "한 권이 한 파일인 것이 이 저장소의 규칙인데, 이 권만 예외다. 애니메이션과 "
            "스펙트로그램이 노트북 안에 그림으로 박혀 있어 한 파일에 담으면 열리지 않는다. "
            f"**나누는 축은 분량이 아니라 물음**이라, {_kor(n_files)} 편이 각각 하나씩 답한다.\n"
            "\n"
            "| 편 | 무엇에 답하나 |\n"
            "|---|---|\n" + rows + "\n"
            "\n"
            f"옛 부 7 조각(회전수·가림·동체 대 날개)은 `{ex['append_to']}` 뒤에 절로 이어 붙어 "
            "있다 — 무늬를 정하는 것이 무엇인가라는 같은 물음에 답하기 때문이다."))

    if COMPANIONS:
        rows = "\n".join(
            f"| [{c['label']} «{c['title']}»]({c['file']}) | {_disp(no)} 권 | {c['what']} "
            f"| `{c['builder']}` |"
            for no in sorted(COMPANIONS) for c in _companions(no))
        hosts = " · ".join(f"{_disp(no)} 권" for no in sorted(COMPANIONS))
        cells.append(_cell(
            "## 권에 딸린 별편\n"
            "\n"
            f"별편은 **부모 권 물음의 심화·지원·변주**다 — 부모가 던진 물음을 더 파고들거나"
            "(심화), 부모의 판정이 서는 근거를 전수로 깔거나(지원), 부모의 가정 하나만 바꿔 "
            f"다시 재는(변주) 편이고, 번호가 «부모번호-K» 다. 지금 {_n_companions()} 편이 "
            f"{hosts}에 붙어 있다.\n"
            "\n"
            f"⭐**분권과 지위가 다르다.** {' · '.join(_disp(e['no']) for e in _split_vols())} 권의 "
            "여러 편은 그림 무게 때문에 나눈 **한 권의 장**이라 번호가 «권-편» 이고, 별편은 "
            "따로 선 문서라 번호가 «부모-K» 다. 6-6 만 파일 이름이 분권 꼬리(_6)를 잇는데 "
            "— 앞자리 _1~_5 가 이미 분권이라 비켜 간 것이고 — 지위는 별편이다.\n"
            "\n"
            "| 별편 | 어느 권에 붙나 | 무엇을 하나 | 빌더 |\n"
            "|---|---|---|---|\n" + rows + "\n"))

    # ── 조각 배치표 ─────────────────────────────────────────────────────────
    def _place_rows(sub) -> str:
        out = ["| 권 | 절 | 조각 | 그 절의 제목 |", "|---|---|---|---|"]
        for p in sub:
            m = place[p]
            out.append(f"| {_disp(m['vol'])} | {m['sec']} | `{p}` | {titles.get(p, '')} |")
        return "\n".join(out)

    placed = sorted(place)
    half = (len(placed) + 1) // 2
    cells.append(_cell(
        "## 어느 조각이 어느 절이 되었나 (앞 절반)\n"
        "\n"
        f"조각 ⟨{INDEX_REL} : _meta.n_parts_placed⟩ 편의 배치표다. 왼쪽 두 칸이 새 주소이고, "
        "`조각` 칸은 `reports/_parts/` 안의 파일 앞 두 자리다. "
        "**이 표는 조각을 찾아가라는 뜻이 아니라, 옛 번호로 적힌 메모를 새 주소로 옮길 때 쓰는 "
        "환산표다.**\n\n" + _place_rows(placed[:half])))
    cells.append(_cell("## 어느 조각이 어느 절이 되었나 (뒤 절반)\n\n" + _place_rows(placed[half:])))

    if SUPERSEDED:
        rows = "\n".join(f"| `{k}` | {v} |" for k, v in sorted(SUPERSEDED.items()))
        cells.append(_cell(
            "## 권에 넣지 않은 조각\n"
            "\n"
            "| 조각 | 넣지 않은 이유 |\n"
            "|---|---|\n" + rows + "\n"
            "\n"
            "그 조각의 빌더는 그대로 남아 있다 — 지우지 않은 이유는, 지우는 판단이 조각 빌더의 "
            "소관이기 때문이다."))

    # ── 읽는 경로 ───────────────────────────────────────────────────────────
    def _link(p: str) -> str:
        m = place[p]
        return (f"[리포트 {_disp(m['vol'])} 절 {m['sec']} «{titles.get(p, '')}»]({m['file']})")

    chain = " → ".join(_link(_vol_entry(no)["headline"]) for no in nos
                       if _vol_entry(no)["headline"] in place)
    cells.append(_cell(
        "## ① 빨리 훑기 — 30 분\n"
        "\n"
        "**이 저장소가 무엇을 해냈는지만 알면 되는 사람.** 본편마다 결론 절 하나씩이다"
        "(별편은 이 경로에 넣지 않는다 — 부모를 읽은 뒤에 여는 글이다). "
        "제목만 읽어도 한 바퀴가 돌고, 막히는 데서만 그 절을 연다.\n"
        "\n" + chain))

    vchain = " → ".join(_link(p) for p in VERIFY_PARTS if p in place)
    cells.append(_cell(
        "## ② 왜 믿을 수 있나 — 2 시간\n"
        "\n"
        "**판정을 검사하려는 사람**(심사·적대검증). 검증·대조·반증 절만 모았다. 뼈대는 "
        "**눈감기 대조 · 사전등록 채점 · PREMATURE 판정 · 널 교정** 넷이다 — 우리가 틀렸을 수 "
        "있는 자리를 우리가 먼저 때린 절들이다.\n"
        "\n" + vchain))

    cells.append(_cell(
        "## 읽을 때 알아 두면 되는 규약 다섯\n"
        "\n"
        "| 규약 | 무슨 뜻인가 |\n"
        "|---|---|\n"
        "| 권 제목은 물음, 절 제목은 답 | 권은 물음 하나를 들고, 그 안의 절 제목은 «…다» 로 "
        "끝나는 평서문이다. 절 제목만 읽어도 그 절의 결론을 읽은 것이다 |\n"
        "| 숫자 옆의 `[^n]` | 그 숫자가 온 JSON 파일과 키다. 절 끝 «출처» 표에 파일·키·값이 "
        "있고, 그 값은 표를 만들 때 JSON 을 다시 열어 채운 것이다 |\n"
        "| 여는 블록 넷 | 한 일 · 결과 · 방법 · 재현. **결과만 읽어도** 그 절의 답을 알 수 있게 "
        "쓴다 |\n"
        "| 절의 마지막은 «다음 단계» | 한계 목록이 아니라 **앞을 보는 행동**이다. 가운데 칸이 "
        "«그러면 결정되는 것» 이고, 그 칸이 빈 행은 규약이 막는다 |\n"
        "| ⚠ 와 ⭐ | ⚠ 는 그 숫자가 서 있는 전제(사슬 세대·메쉬 판)를, ⭐ 는 그 절의 핵심 "
        "판단을 가리킨다 |\n"))

    cells.append(_cell(
        "## 다음 단계\n"
        "\n"
        "| 다음에 할 일 | 그러면 결정되는 것 | 어디서 |\n"
        "|---|---|---|\n"
        "| 조각이 늘거나 줄면 편성에 배치하고 권을 다시 조립한다 | 지도의 권 수·절 구성이 "
        "실제 디스크와 같아진다 | `src/build_volumes.py` |\n"
        "| 권 사이 참조를 매번 검사한다 | 끊긴 링크·없는 앵커·안 열리는 출처가 0 인 채로 "
        "유지된다 | `benchmark/check_report_links.py` |\n"
        f"| 저장소 최상단 목차를 본편 {n_vol} 권 + 별편 {_n_companions()} 편 편성으로 다시 낸다 "
        "| 바깥에서 들어오는 독자가 폐지된 78 편 주소로 새지 않는다 | `src/make_readme.py` |\n",
        meta={"tags": ["next_steps"]}))

    return RS._footnote_pass(cells)


def _n_sections(no: str, place: dict[str, dict]) -> int:
    """그 권의 절 수 — 생성 절 + 조각 절 (+ 외부 편이 자기 것으로 들고 있는 절)."""
    for v in VOLUMES:
        if v[0] == no:
            return len(v[4]) + (1 if no == MAP_VOL else 0)
    for ex in EXTERNAL:
        if ex["no"] == no:
            return _host_base(ex["append_to"]) + len(ex["parts"])
    return 0


def _th_short(thesis: str, width: int = 62) -> str:
    """머리말의 한 줄 논지를 표 칸에 넣을 만큼 줄인다."""
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", thesis).replace("\n", " ").strip()
    t = re.sub(r"\s+", " ", t)
    return t if len(t) <= width else t[: width - 1].rstrip(" .,·") + "…"


# --------------------------------------------------------------------------- #
#  색인 · 목차
# --------------------------------------------------------------------------- #
def _count_xrefs(place: dict[str, dict]) -> int:
    """조각이 들고 있는 옛 주소의 개수 — 링크·옛 부·인라인 코드 셋을 합친다."""
    n = 0
    for p in place:
        t = json.dumps(json.load(open(os.path.join(PARTS, _part_file(p)),
                                     encoding="utf-8")), ensure_ascii=False)
        n += sum(1 for m in _XREF.finditer(t) if _is_part_name(m.group(3), m.group(4)))
        n += len(_PARTREF.findall(t))
        n += sum(1 for m in _CODEREF.finditer(t) if _is_part_name(m.group(1), m.group(2)))
    return n


def _write_bootstrap_index(place: dict[str, dict]) -> None:
    """지도 절이 인용할 구조 수치를 **먼저** 원장에 적는다(그 다음 지도를 짓는다)."""
    on_disk = _all_parts_on_disk()
    #  ⭐«권» 은 본편만 센다(11). 별편 8 편은 따로 세고, 둘을 합친 노트북 수가 23 이다 —
    #    본편 파일 15(06 권만 분권 5 편) + 별편 8.
    doc = {"_meta": {
        "n_volumes": len(_trunk_nos()),
        "n_notebooks": (sum(len(_vol_entry(n)["files"]) for n in _trunk_nos())
                        + _n_companions()),
        "n_companions": _n_companions(),
        "n_parts_on_disk": len(on_disk),
        "n_parts_placed": len(place),
        "n_parts_superseded": len(SUPERSEDED),
        "n_crossrefs": _count_xrefs(place),
        "generator": "src/build_volumes.py",
        "built_at": _dt.date.today().isoformat(),
    }}
    os.makedirs(os.path.dirname(INDEX), exist_ok=True)
    with open(INDEX, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    RS._JSON_CACHE.pop(os.path.normpath(INDEX), None)


def _write_index(place: dict[str, dict], titles: dict[str, str],
                 built: list[dict], stat: dict) -> None:
    doc = json.load(open(INDEX, encoding="utf-8"))
    doc["_meta"].update(
        n_cells=sum(b["cells"] for b in built),
        n_footnotes=sum(b["footnotes"] for b in built),
        n_figures=sum(b["figures"] for b in built),
        n_crossrefs_cross_file=stat.get("xref_cross", 0) + stat.get("coderef_cross", 0),
        n_crossrefs_same_file=stat.get("xref_intra", 0) + stat.get("coderef_intra", 0),
        n_partrefs_rewritten=stat.get("buref", 0) + stat.get("buprose", 0),
        # ⭐순서는 «권을 만드는 명령» 전부다 — 여기 없는 빌더는 README 의 재현 블록에서도
        #   빠지고, 그러면 reports/README.md 의 순서와 갈린다(같은 절차가 두 곳에서 다르게
        #   적히는 것이 가장 잦은 어긋남이다). 6-5 와 별편(8-2·5-2)도 권 파일을 내므로
        #   여기 든다 — 루트 README 는 별편 빌더를 이 목록에서 되찾는다.
        order=["src/build_partNN_*.py", "src/make_report08_microdoppler.py",
               "src/make_report07b_bistatic.py", "src/make_report11_2_two_channel.py",
               "src/build_report18_switch_grid.py",
               "src/build_volumes.py", "benchmark/check_report_links.py"])
    doc["volumes"] = built
    doc["parts"] = {p: dict(volume=m["vol"], file=m["file"], section=m["sec"],
                            title=titles.get(p, ""),
                            part_file=f"reports/_parts/{_part_file(p)}")
                    for p, m in sorted(place.items())}
    doc["superseded_parts"] = {k: dict(reason=v, part_file=f"reports/_parts/{_part_file(k)}")
                               for k, v in sorted(SUPERSEDED.items())}
    # ⭐별편의 제목·설명까지 색인에 넣는다 — 루트 README 가 목차를 이 색인 하나에서 만들기
    #   때문이다. 파일 이름만 넣으면 README 에 별편이 «이름 없는 파일» 로만 남거나 아예
    #   빠진다(실제로 그랬다).
    doc["companions"] = {no: _companions(no) for no in sorted(COMPANIONS)}
    doc["notes"] = {
        "parts": "reports/_parts/ 의 조각은 빌더 중간 산출물이다 — 사람이 읽는 문서가 아니고, "
                 "손으로 고치지 않는다. 고칠 곳은 그 조각을 만든 src/build_partNN_*.py 다.",
        "volumes": (f"reports/ 의 권이 사람이 읽는 문서다 — 본편 {len(_trunk_nos())} 권과 "
                    f"별편 {_n_companions()} 편. 한 권이 한 파일이고, "
                    + " · ".join(f"{_disp(e['no'])} 권만 그림이 무거워 "
                                 f"{len(e['files'])} 편으로 나뉜다(분권)" for e in _split_vols())
                    + (". 별편은 부모 권 물음의 심화·지원·변주이고 번호가 «부모번호_K» 다"
                       f"({', '.join(c['file'] for no in sorted(COMPANIONS) for c in _companions(no))})."
                       if COMPANIONS else ".")),
        "companions": {no: [c["file"] for c in _companions(no)] for no in sorted(COMPANIONS)},
        "rebuild": (f"① 조각 빌더 {len(_part_builders())} 개 → "
                    "② src/make_report08_microdoppler.py + "
                    "src/make_report07b_bistatic.py + src/make_report11_2_two_channel.py + "
                    "src/build_report18_switch_grid.py → "
                    "③ src/build_volumes.py → ④ benchmark/check_report_links.py"),
    }
    with open(INDEX, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)


def _write_readme(place: dict[str, dict], titles: dict[str, str],
                  built: list[dict]) -> None:
    by_no = {b["no"]: b for b in built}
    n_vol = N_VOLUMES
    n_comp = _n_companions()
    bld = _part_builders()
    L = ["<!-- 생성물 — `src/build_volumes.py` 가 낸다. 손으로 고치지 말고 그 파일을 고쳐라. -->",
         "",
         f"# 리포트 — 본편 {n_vol} 권 · 별편 {n_comp} 편",
         "",
         "패시브 바이스태틱 드론 탐지 시뮬레이터의 본문이다. **한 권이 물음 하나를 들고, 권 "
         "제목이 그 물음이다.** 권 안의 절은 각각 «한 일 · 결과 · 방법 · 재현» 을 앞에 달고 "
         "있어 필요한 절만 따로 읽어도 된다.",
         "",
         f"처음이면 [리포트 {_disp(VOLUMES[0][0])} «{VOLUMES[0][2]}»]"
         f"({VOLUMES[0][0]}_{VOLUMES[0][1]}.ipynb) 부터다 — {_kor(n_vol)} "
         "권의 지도와 읽는 경로 셋이 거기 있다.",
         "",
         f"## 본편 {_kor(n_vol)} 권",
         "",
         "| 권 | 이 권이 답하는 물음 | 절 | 한 절만 읽는다면 |",
         "|---|---|---|---|"]
    for no in _trunk_nos():
        e = _vol_entry(no)
        b = by_no[no]
        p = place.get(e["headline"])
        hl = f"[절 {p['sec']} «{titles.get(e['headline'], '')}»]({p['file']})" if p else "—"
        L.append(f"| [{_disp(no)} «{e['title']}»]({e['files'][0][0]}) "
                 f"| {_th_short(e['thesis'])} | {b['n_sections']} | {hl} |")
    if COMPANIONS:
        L += ["",
              f"## 권에 딸린 별편 {n_comp} 편",
              "",
              "별편은 **부모 권 물음의 심화·지원·변주**다 — 번호가 «부모번호-K» 이고, 부모를 "
              "읽은 뒤에 여는 글이다. "
              + " · ".join(f"{_disp(e['no'])} 권의 {_kor(len(e['files']))} 편"
                           for e in _split_vols())
              + "은 이것과 달리 그림 무게로 나눈 **분권**(한 권의 장)이다. "
              "6-6 만 파일 이름이 분권 꼬리를 잇고 지위는 별편이다.",
              "",
              "| 별편 | 어느 권에 붙나 | 무엇을 하나 | 빌더 |",
              "|---|---|---|---|"]
        for pno in sorted(COMPANIONS):
            for c in _companions(pno):
                L.append(f"| [{c['label']} «{c['title']}»]({c['file']}) | {_disp(pno)} 권 "
                         f"| {c['what']} | `{c['builder']}` |")
    L += ["",
          f"셀 {sum(b['cells'] for b in built)} 개 · 각주 {sum(b['footnotes'] for b in built)} 개 "
          f"· 그림 {sum(b['figures'] for b in built)} 개.",
          "",
          "## 각 권에 어느 조각이 들어갔나",
          "",
          "`조각` 칸은 `_parts/` 안의 파일이다. **조각은 사람이 직접 읽는 문서가 아니다** — "
          "조각 빌더(`src/build_partNN_*.py`)의 중간 산출물이고, 권을 조립하는 재료다. "
          "본문을 고칠 일이 생기면 조각이나 권이 아니라 **그 조각을 만든 빌더**를 고치고 다시 "
          "조립한다.",
          ""]
    for no in _ordered_nos():
        e = _vol_entry(no)
        b = by_no[no]
        par = _parent_of(no)
        head = "별편" if par else "권"
        L += [f"### {head} [{_disp(no)} «{e['title']}»]({e['files'][0][0]})", ""]
        if par is not None:
            pe = _vol_entry(par)
            L += [f"[리포트 {_disp(par)} «{pe['title']}»]({pe['files'][0][0]}) 의 **별편**이다.",
                  ""]
        if e["external"]:
            L += [f"그림이 무거워 **{len(e['files'])} 편**으로 나뉜다 — 별편이 아니라 **분권**, "
                  "곧 한 권의 장이다"
                  f"(빌더 `{next(x['builder'] for x in EXTERNAL if x['no'] == no)}`).", "",
                  "| 편 | 무엇에 답하나 |", "|---|---|"]
            L += [f"| [{f}]({f}) | {t} |" for f, t in e["files"]]
            L += ["", f"아래 절은 이 스크립트가 `{b['append_to']}` 뒤에 이어 붙인 것이다.", ""]
        comps = _companions(no)
        if comps:
            L += [f"별편이 {_kor(len(comps))} 편 딸려 있다.", ""]
            L += [f"- [{c['label']} «{c['title']}»]({c['file']}) (빌더 `{c['builder']}`) "
                  f"— {c['what']}." for c in comps]
            L.append("")
        L += ["| 절 | 제목 | 조각 |", "|---|---|---|"]
        for s in b["sections"]:
            src = ("(이 스크립트가 생성)" if s["part"] == "gen"
                   else f"`_parts/{s['part_file']}`")
            L.append(f"| {s['n']} | {s['title']} | {src} |")
        L.append("")
    if SUPERSEDED:
        L += ["## 권에 넣지 않은 조각", "", "| 조각 | 이유 |", "|---|---|"]
        for k, v in sorted(SUPERSEDED.items()):
            L.append(f"| `_parts/{_part_file(k)}` | {v} |")
        L.append("")
    L += ["## 다시 만들려면", "",
          "순서가 중요하다 — ③ 이 ② 의 산출물 뒤에 절을 덧붙이기 때문이다.",
          "",
          "```bash",
          f"PYTHONPATH=src python src/{bld[0]:<33s}# ① 조각 빌더 {len(bld)} 개",
          f"#  … {bld[1]} … {bld[-1]}",
          "PYTHONPATH=src python src/make_report08_microdoppler.py    # ② 6 권 1~4 편",
          "PYTHONPATH=src python src/make_report07b_bistatic.py       # ②' 6 권 5 편",
          "PYTHONPATH=src python src/make_report11_2_two_channel.py   # ②\" 별편 8-2",
          "PYTHONPATH=src python src/build_report18_switch_grid.py    # ②\" 별편 5-2",
          "PYTHONPATH=src python src/build_volumes.py                 # ③ 조각 → 권 + 색인 + 이 파일",
          "PYTHONPATH=src python benchmark/check_report_links.py      # ④ 검사",
          "```",
          "",
          f"기계용 색인은 [`{INDEX_REL}`](../{INDEX_REL}), 구조 설명서는 "
          "[`docs/REPORTS_VOLUMES.md`](../docs/REPORTS_VOLUMES.md) 다.",
          ""]
    with open(os.path.join(OUT, "README.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L))


# --------------------------------------------------------------------------- #
#  조립
# --------------------------------------------------------------------------- #
def _assemble(no, slug, title, thesis, parts, hd, place, bu2vol, titles, stat) -> dict:
    """이 스크립트가 통째로 짓는 권 하나."""
    fname = f"{no}_{slug}.ipynb"
    secs: list[tuple[str, str, str]] = []
    loaded: list[tuple[str, list]] = []
    if no == MAP_VOL:
        secs.append(("gen", MAP_SECTION_TITLE, ""))
        loaded.append((MAP_SECTION_TITLE, _map_cells(place, titles)))
    for p in parts:
        fn, t, cs = _load_part(p)
        secs.append((p, t, fn))
        loaded.append((t, cs))

    hl_sec = place[hd]["sec"] if hd in place else None
    cells = [_vol_intro(no, title, thesis, secs, hl_sec)]
    off = fig_off = 0
    for i, ((t, cs), (part, _t2, _fn)) in enumerate(zip(loaded, secs), 1):
        cells.append(_section_rule(i, t))
        hi = fig_hi = 0
        for c in cs:
            src = _text(c)
            hi = max(hi, _max_footnote(src))
            fig_hi = max(fig_hi, _max_figure(src))
            src = _shift_footnotes(src, off)
            src = _shift_figures(src, fig_off)
            if part != "gen":            # 생성된 절은 이미 새 주소로 쓰여 있다
                src = _relink(src, fname, place, bu2vol, stat)
            src = _H1_LINE.sub("", src, count=1)     # 절 구분자가 조각 H1 을 대신한다
            if not src.strip():
                continue
            cells.append(_cell(src, c["cell_type"], c.get("metadata", {})))
        off += hi
        fig_off += fig_hi

    nb = {"cells": cells,
          "metadata": {"kernelspec": {"display_name": "py312", "language": "python",
                                      "name": "py312"},
                       "language_info": {"name": "python"}},
          "nbformat": 4, "nbformat_minor": 5}
    with open(os.path.join(OUT, fname), "w", encoding="utf-8") as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)

    body = "\n".join(_text(c) for c in cells)
    return dict(no=no, no_disp=_disp(no), kind=_kind(no), parent=_parent_of(no),
                file=fname, title=title, external=False,
                thesis=re.sub(r"\s+", " ", thesis).strip(),
                files=[fname], headline_part=hd, headline_section=hl_sec,
                n_sections=len(secs), cells=len(cells), footnotes=off,
                figures=len(re.findall(r"!\[[^\]]*\]\(", body)),
                sections=[dict(n=i, part=p, title=t,
                               file=fname, part_file=(fn if p != "gen" else None))
                          for i, (p, t, fn) in enumerate(secs, 1)])


def _postprocess_external(ex, place, bu2vol, titles, stat) -> dict:
    """다른 빌더가 낸 편들 — 주소를 고치고, 지정한 편 뒤에 조각을 절로 덧붙인다."""
    no, host = ex["no"], ex["append_to"]
    present = [(f, t) for f, t in ex["files"] if os.path.exists(os.path.join(OUT, f))]
    missing = [f for f, _t in ex["files"] if not os.path.exists(os.path.join(OUT, f))]
    if missing:
        print(f"  ⚠ {no} 권 — 아직 없는 편 {len(missing)}개: {', '.join(missing)}\n"
              f"     → `{ex['builder']}` 를 먼저 돌려라. 이번 실행은 있는 편만 손댄다.")

    n_cells = n_fig = n_foot = 0
    host_secs: list[dict] = []
    for fname, _t in present:
        path = os.path.join(OUT, fname)
        nb = json.load(open(path, encoding="utf-8"))
        cells = _strip_appended(nb["cells"])          # 앞선 실행이 붙인 절을 걷어낸다
        # 주소 재배선 (그 편이 이미 들고 있는 셀)
        out = []
        for c in cells:
            src = _relink(_text(c), fname, place, bu2vol, stat)
            out.append(_cell(src, c["cell_type"], c.get("metadata", {}))
                       if src != _text(c) else c)
        cells = out
        off = max([_max_footnote(_text(c)) for c in cells] or [0])
        fig_off = max([_max_figure(_text(c)) for c in cells] or [0])

        # ⭐분권 권(EXTERNAL)의 **첫 편**에도 별편 선언을 넣는다(2026-08-15 검증에서 발견).
        #   조립 권은 _vol_intro 가 넣어 주지만 이 경로는 그 함수를 안 타서 06 권만 빠져 있었다.
        #   APPEND_TAG 를 붙여 두면 _strip_appended 가 다음 실행에서 걷어내므로 중복이 안 쌓인다.
        if fname == present[0][0]:
            comps = _companions(no)
            if comps:
                ln = [f"이 권에는 별편이 {_kor(len(comps))} 편 딸려 있다 — 이 권의 물음을 "
                      "더 파고들거나 받쳐 주는 글이다.", ""]
                ln += [f"- [리포트 {c['label']} «{c['title']}»]({c['file']}) — {c['what']}."
                       for c in comps]
                ln += ["", "⚠이 권의 편 1~5 는 **분권**이다 — 그림 무게 때문에 한 권을 다섯 "
                       "편으로 나눈 것이고, 별편과는 지위가 다르다."]
                cells.insert(1, _cell("\n".join(ln), meta={"tags": [APPEND_TAG]}))

        if fname == host:                              # ⭐ 조각을 절로 덧붙인다
            base = max([int(n) for c in cells for n in _SEC_H2.findall(_text(c))] or [0])
            cells.append(_cell(
                "---\n"
                "\n"
                "## 조각에서 이어붙인 절\n"
                "\n"
                f"아래 절 {base + 1}~{base + len(ex['parts'])} 는 `reports/_parts/` 의 조각을 "
                "그대로 이어 붙인 것이다 — 같은 물음(무엇이 무늬를 정하나)에 답하기 때문이다. "
                "각주는 이 편 안에서 다시 번호가 매겨졌다.\n"
                "\n"
                "⭐ 이 절들을 손으로 고치지 마라. 고칠 곳은 그 조각을 만든 "
                "`src/build_partNN_*.py` 이고, 고친 뒤 `src/build_volumes.py` 를 다시 돌리면 "
                "여기가 따라 바뀐다.",
                meta={"tags": [APPEND_TAG]}))
            for i, p in enumerate(ex["parts"], base + 1):
                _fn, t, cs = _load_part(p)
                cells.append(_section_rule(i, t, meta={"tags": [APPEND_TAG]}))
                hi = fig_hi = 0
                for c in cs:
                    src = _text(c)
                    hi = max(hi, _max_footnote(src))
                    fig_hi = max(fig_hi, _max_figure(src))
                    src = _shift_footnotes(src, off)
                    src = _shift_figures(src, fig_off)
                    src = _relink(src, fname, place, bu2vol, stat)
                    src = _H1_LINE.sub("", src, count=1)
                    if not src.strip():
                        continue
                    meta = dict(c.get("metadata", {}))
                    meta["tags"] = list(dict.fromkeys((meta.get("tags") or [])
                                                      + [APPEND_TAG]))
                    cells.append(_cell(src, c["cell_type"], meta))
                off += hi
                fig_off += fig_hi
                host_secs.append(dict(n=i, part=p, title=t, file=fname,
                                      part_file=_part_file(p)))

        nb["cells"] = cells
        with open(path, "w", encoding="utf-8") as f:
            json.dump(nb, f, ensure_ascii=False, indent=1)
        body = "\n".join(_text(c) for c in cells)
        figs = len(re.findall(r"!\[[^\]]*\]\(", body))
        n_cells += len(cells)
        n_fig += figs
        n_foot += off
        print(f"  ✅ reports/{fname:30s} 셀 {len(cells):3d} · 각주 {off:3d} · "
              f"그림 {figs:2d}"
              + (f"  ← 조각 {len(ex['parts'])} 편 덧붙임" if fname == host else ""))

    hd = ex["headline"]
    return dict(no=no, no_disp=_disp(no), kind=_kind(no), parent=_parent_of(no),
                file=ex["files"][0][0], title=ex["title"], external=True,
                thesis=re.sub(r"\s+", " ", ex["thesis"]).strip(),
                builder=ex["builder"], append_to=host,
                files=[f for f, _t in ex["files"]], missing_files=missing,
                notebooks=[dict(file=f, holds=t) for f, t in ex["files"]],
                headline_part=hd,
                headline_section=place[hd]["sec"] if hd in place else None,
                n_sections=_n_sections(no, place), cells=n_cells, footnotes=n_foot,
                figures=n_fig, sections=host_secs)


def main() -> None:
    if not os.path.isdir(PARTS):
        print(f"⚠ {PARTS} 가 없다. 조각 빌더의 출력 경로를 먼저 확인해라.")
        sys.exit(1)

    place = _placement()
    titles = {p: _load_part(p)[1] for p in place}
    bu2vol = _bu_to_vol(place)
    _write_bootstrap_index(place)

    stat: dict = {}
    built: list[dict] = []
    for no, slug, title, thesis, parts, hd in VOLUMES:
        b = _assemble(no, slug, title, thesis, parts, hd, place, bu2vol, titles, stat)
        built.append(b)
        print(f"  ✅ reports/{b['file']:30s} 절 {b['n_sections']:2d} · 셀 {b['cells']:3d} · "
              f"각주 {b['footnotes']:3d} · 그림 {b['figures']:2d}")
    for ex in EXTERNAL:
        built.append(_postprocess_external(ex, place, bu2vol, titles, stat))

    built.sort(key=lambda b: b["no"])
    _write_index(place, titles, built, stat)
    _write_readme(place, titles, built)

    print(f"\n✅ 본편 {N_VOLUMES} 권 · 별편 {_n_companions()} 편 → reports/   "
          f"(조각 {len(place)} 편 배치, {len(SUPERSEDED)} 편 미배치)")
    print(f"   상호참조 재배선 — 다른 편 "
          f"{stat.get('xref_cross', 0) + stat.get('coderef_cross', 0)} · 같은 편 "
          f"{stat.get('xref_intra', 0) + stat.get('coderef_intra', 0)} · 옛 부 "
          f"{stat.get('buref', 0) + stat.get('buprose', 0)} · "
          f"버림 {stat.get('xref_dropped', 0)}")
    print(f"   색인 {os.path.relpath(INDEX, _ROOT)} · 목차 reports/README.md")


if __name__ == "__main__":
    main()
