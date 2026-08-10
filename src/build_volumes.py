# -*- coding: utf-8 -*-
"""
build_volumes.py — ⭐**조각 78 편을 15 권으로 묶는다**

사용자:
> *"레포트를 지금 너무 심하게 잘게 쪼갠 거 같은데... 그래도 적당히 **하나의 메시지를 담아서**
>  해주면 좋겠어. 0~6 을 한 **20 개 이내로** 적당히 메시지가 담기게끔 구성해주면 좋겠고,
>  7 번도 7 번을 고집한다기보다는 **순서상 어울리는 위치로** 레포트 번호를 매겨서 만들어줘."*

⭐ 실행 순서 — 이 스크립트는 **맨 마지막**이다
------------------------------------------------
    ① 조각 빌더 12 개        src/build_part00_map.py … src/build_part11_measurement.py
                             → reports/_parts/NN_slug.ipynb
    ② 8 권 빌더              src/make_report08_microdoppler.py
                             → reports/08_1_scene.ipynb … 08_4_sampling.ipynb
    ②' 8-5 바이스태틱 빌더  src/make_report07b_bistatic.py → reports/08_5_bistatic.ipynb
    ③ **이 스크립트**        src/build_volumes.py
                             → reports/NN_slug.ipynb 14 권 + 8 권 후처리 + 색인 + README
    ④ 검사                   benchmark/check_report_links.py

②가 아직 없으면 8 권 후처리를 **조용히 건너뛰고 경고만** 찍는다 — 빌드는 죽지 않는다.

설계 — 빌더는 그대로 두고 그 위에 «묶는 층» 을 얹는다
------------------------------------------------------
⭐ 조각의 숫자는 전부 원장 JSON 에서 주입된다(`src/build_partNN_*.py`). 손으로 합치면 그
   사슬이 끊긴다. 그래서 이 스크립트는 **조각을 다시 쓰지 않는다** — 빌더가 만든 조각을 읽어
   순서대로 잇고, 권 단위로 **각주를 다시 매기고**, 조각 사이 **상호참조를 새 권·절 번호로
   고쳐 쓰고**, 권의 머리말을 앞에 붙인다.
   ⇒ 재계산 → 조각 빌더 재실행 → 이 스크립트 재실행이면 권의 숫자도 함께 갱신된다.

   조각:  reports/_parts/NN_slug.ipynb   (빌더 산출 · **사람이 직접 읽는 문서가 아니다**)
   권  :  reports/NN_slug.ipynb          (사람이 읽는 문서 · 15 권 · 8 권만 다섯 편으로 나뉜다 · 별편은 COMPANIONS)

이 스크립트가 손대는 다섯 가지
------------------------------
1. **각주 재번호** — 조각마다 `[^1]` 부터 다시 세므로, 그냥 이으면 한 권 안에서 번호가 겹친다.
   조각을 이을 때 그 앞까지의 최대 번호만큼 밀어 정의·인용을 함께 옮긴다.
2. **상호참조 재배선** — 조각 본문의 `[편 22 «…»](22_po-knee.ipynb)` 는 78 편 시절의 주소다.
   조각은 이제 `_parts/` 에 살고 사람이 여는 문서가 아니므로, 그 링크를 새 주소로 고친다.
       다른 편을 가리키면 → `[리포트 5 절 5 «…»](05_kernel.ipynb)`
       같은 편을 가리키면 → `**절 5** «…»`  (자기 파일로 되돌아가는 링크를 만들지 않는다)
   같은 손질을 옛 12 부 참조(`[부 4 «산란 커널»](../README.md#…)`)와 인라인 코드 주소
   (`` `reports/37_md-rpm.ipynb` ``)에도 한다.
3. **지도 권 생성** — 1 권의 첫 절은 조각이 아니라 이 스크립트가 짓는다. 옛 조각 `00_map`
   은 «78 편 · 12 부» 라는 폐지된 구조 자체를 설명하는 글이라 재배선으로 살릴 수 없다.
   대신 여기서 열다섯 권의 목차·조각 배치·읽는 경로를 **편성과 디스크에서 다시 만든다.**
4. **8 권 후처리** — 8 권은 그림이 무거워 다섯 편으로 나뉘고, 다른 빌더가 낸다(위 ②·②').
   이 스크립트는 그 다섯 편의 **주소만 고치고**, 옛 부 7 조각(34~39)을 `08_3_pattern.ipynb`
   뒤에 절로 **덧붙인다**. 덧붙인 셀에는 표식을 달아 두므로 다시 돌려도 겹쳐 쌓이지 않는다.
5. **색인과 목차** — `outputs/volumes_index.json`(기계용)과 `reports/README.md`(사람용).

    PYTHONPATH=src python src/build_volumes.py
"""
from __future__ import annotations

import datetime as _dt
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

# --------------------------------------------------------------------------- #
#  이 스크립트가 조립하는 권 — 한 권 = 하나의 메시지
#    (번호, 슬러그, 제목, 한 줄 논지, [조각 번호…], 결론 조각)
#  ⭐ 순서는 «묻는 것 → 도구를 믿을 근거 → 표적 → 신호 → 처리 → 결과 → 실측» 이다.
#     마이크로도플러는 «7 번» 을 고집하지 않고 이 흐름에서 제 자리인 **8 권**이다(사용자 지시).
#     그 8 권만 아래 EXTERNAL 이 맡는다 — 그림이 무거워 다섯 편으로 나뉘기 때문이다.
#  ⭐ 마지막 칸은 «이 권을 한 절만 읽는다면 어디» — 빨리 훑는 경로가 여기서 만들어진다.
# --------------------------------------------------------------------------- #
VOLUMES = [
    ("01", "map", "이 연구가 묻는 것과 답한 방식",
     "패시브 바이스태틱으로 드론을 **탐지하고 마이크로도플러로 분류**하는 것이 태스크이고, "
     "RCS 는 그 인프라다. 이 권은 나머지 열네 권의 지도다.",
     ["13", "75"], "75"),
    ("02", "stock-engine", "스톡 Sionna 로는 왜 부족한가",
     "스톡 레이 트레이서는 경로를 풀지 **산란적분을 하지 않는다**. "
     "그 한 가지가 드론처럼 작은 표적에서 무엇을 무너뜨리는지 여덟 갈래로 잰다.",
     ["01", "02", "03", "04", "05", "06", "07"], "06"),
    ("03", "prior-work", "선행연구는 어디까지 왔고 우리는 어디 서는가",
     "공개 문헌과 오픈소스를 전수로 세어, 우리가 **새로 하는 것과 빌려 쓰는 것**을 갈라 적는다.",
     ["08", "09", "10", "11", "12", "14"], "08"),
    ("04", "target-mesh", "표적을 짓는다 — 메쉬와 재질",
     f"기체 {len(RS.fetch(('outputs/mesh_gallery.json', 'order_by_size')))} 대를 CAD 로 짓고, "
     f"그중 σ 를 내는 {RS.fetch(('outputs/report02_derived.json', 'mesh.n')):.0f} 대를 실물 "
     f"사진·도면과 대조한다. **재질은 측정이 아니라 선언**이고, 그 선언이 어디까지 미치는지 "
     f"함께 적는다.",
     ["15", "16", "17"], "16"),
    ("05", "kernel", "우리 커널 — 무엇이고, 무엇이 아닌가",
     "SBR + 물리광학이 무엇을 계산하고 무엇을 **계산하지 않는지**를 정의하고, "
     "해석해가 있는 과녁(구·평판·이면각)으로 잰다.",
     ["18", "19", "20", "21", "22", "23"], "21"),
    ("06", "anchor", "σ 를 무엇에 붙들어 매나",
     "우리 σ 의 절대 레벨을 붙드는 것은 **공개 문헌 한 기체·한 실험실**뿐이다. "
     "그 끈의 장력을 재고, 끊어질 자리를 먼저 적는다.",
     ["24", "25", "26", "27", "28", "29"], "24"),
    ("07", "size-law", "표적을 얼마나 거칠게 그려도 되나 — 사다리와 크기 법칙",
     "표적 모형을 구·정육면체·상자·평판으로 갈아 끼우는 사다리로 **단순화의 값**을 재고, "
     "앵커보다 크고 작은 두 기체로 **크기전이 법칙**을 가르는 계획을 적는다. "
     "**사다리의 답이 이르게 나오면 그것부터 의심한다.**",
     ["30", "31", "32", "33", "77"], "32"),
    # 08 은 EXTERNAL 이 맡는다
    ("09", "microdoppler-limits", "마이크로도플러 — 무엇이 그 무늬를 흐리나",
     "자세·보정·광선 예산·표본율 네 가지가 무늬를 지운다. "
     "각각을 **단일축으로 갈라** 얼마나 지우는지 잰다.",
     ["40", "41", "42", "43"], "43"),
    ("10", "illuminators", "무엇을 조명원으로 쓸 수 있나",
     "LTE·5G·WiFi 가 각각 **얼마나 자주, 얼마나 넓게** 신호를 내주는가. "
     "5G 는 대역이 넓은 대신 상시 신호가 드물어 **이중고**가 된다.",
     ["44", "45", "46", "47", "48", "49", "50"], "46"),
    ("11", "detector", "처리 사슬 — 직접파를 죽이고 표적을 세운다",
     "ECA 로 직접파를 지우고 CFAR 로 문턱을 세운다. "
     "**문턱을 어디에 두느냐가 결과를 정하므로** 그 교정을 먼저 적는다.",
     ["51", "52", "53", "54"], "53"),
    ("12", "observability", "관측가능성과 기하 — 어디에 서야 보이나",
     "송신기·수신기·표적의 배치가 검출을 정한다. "
     "**볼 수 없는 자리**를 먼저 지도로 그리고, 그 다음에 거리를 말한다.",
     ["55", "56", "57", "58"], "55"),
    ("13", "results", "결과 — 얼마나 멀리서 보이나",
     "R90 과 순위가 이 연구의 정량 결론이다. "
     "적분시간·잔류·σ 가정을 흔들어 **순위가 견디는지**까지 함께 적는다.",
     ["59", "60", "61", "62", "63"], "60"),
    ("14", "robustness", "결론이 무엇에 기대고 있나 — 강건성과 하드웨어",
     "표적 모형·수신 소자·장비를 바꿔 넣어 **결론이 어디서 흔들리는지** 본다.",
     ["64", "65", "66", "67", "68"], "64"),
    ("15", "measurement", "실측 계획 — 무엇을 재야 이 문서가 닫히나",
     "시뮬레이션이 선언으로 남겨 둔 것들의 목록과, 그것을 닫는 **야외 실측 규약**이다.",
     ["69", "70", "71", "72", "73", "74", "76"], "74"),
]

# --------------------------------------------------------------------------- #
#  다른 빌더가 내는 권 — 이 스크립트는 주소를 고치고 조각을 덧붙일 뿐이다
#    ⭐ 8 권은 그림이 무거워(애니메이션 GIF 포함) 한 파일에 담기지 않는다. 그래서 다섯 편이다.
#    ⚠ 08_5(바이스태틱)만 빌더가 다르다 — src/make_report07b_bistatic.py 다.
# --------------------------------------------------------------------------- #
EXTERNAL = [
    dict(no="08", title="마이크로도플러 — 도는 로터가 남기는 무늬",
         thesis="호버링하는 드론은 제자리에 있지만 **프로펠러는 돈다**. "
                "그 회전이 남기는 시간-주파수 무늬가 이 연구의 분류 축이다. "
                "그림이 무거워 **다섯 편**으로 나뉜다.",
         builder="src/make_report08_microdoppler.py "
                 "(08_5 만 src/make_report07b_bistatic.py)",
         files=[("08_1_scene.ipynb", "무엇을 보고 있나 — 시나리오와 신호의 정체"),
                ("08_2_engines.ipynb", "어떻게 계산하나 — 세 엔진과 거리"),
                ("08_3_pattern.ipynb", "무엇이 무늬를 정하나 — 회전수·가림·산포"),
                ("08_4_sampling.ipynb", "무엇을 잴 수 있나 — 광선 비용과 반복률"),
                ("08_5_bistatic.ipynb",
                 "송수신이 갈라지면 — 바이스태틱 도플러·플래시·에코")],
         append_to="08_3_pattern.ipynb",
         parts=["34", "35", "36", "37", "38", "39"],
         headline="36"),
]

# --------------------------------------------------------------------------- #
#  권에 딸린 별편 — 권 파일과 따로 사는 노트북이고 빌더도 다르다.
#    권을 쪼갠 것(EXTERNAL)이 아니라, 권 하나의 가정을 하나만 풀어 본 **곁가지**다.
#    지도는 이것도 세어 적는다 — 세지 않으면 디스크에 있는 노트북이 목차에서 사라진다.
# --------------------------------------------------------------------------- #
COMPANIONS = {
    "11": [dict(file="11_2_two_channel.ipynb",
                label="11-2",
                title="기준채널이 현실이면 얼마를 잃는가",
                what="11 권의 사슬을 한 줄도 안 고치고, 기준신호를 «송신 파형 그대로» 에서 "
                     "«잡음·다중경로가 섞인 측정 신호» 로 바꿔 손실을 잰다",
                builder="src/make_report11_2_two_channel.py")],
}

#: 1 권 첫 절(지도)은 조각이 아니라 이 스크립트가 짓는다.
MAP_VOL = "01"
MAP_SECTION_TITLE = "열다섯 권의 지도 — 무엇이 어디에 있나"

#: 편 수를 한글로 — 지도 본문이 «네 편/다섯 편» 을 손으로 적지 않게 한다.
_KOR_COUNT = {1: "한", 2: "두", 3: "세", 4: "네", 5: "다섯", 6: "여섯", 7: "일곱",
              8: "여덟", 9: "아홉", 10: "열"}


def _kor(n: int) -> str:
    return _KOR_COUNT.get(n, str(n))


def _n_companions() -> int:
    return sum(len(v) for v in COMPANIONS.values())

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
#: ⚠ 권 파일 이름도 같은 꼴(`09_microdoppler-limits.ipynb`)이다. 번호만 보고 고치면 **이미
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
            out[str(bu)] = max(tally.items(), key=lambda kv: (kv[1], -int(kv[0])))[0]
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
        return f"[리포트 {int(p['vol'])} 절 {p['sec']}{tail}]({p['file']})"

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
        return f"[리포트 {int(v)}{tail}]({e['files'][0][0]})"

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
        return f"리포트 {int(v)} "

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
    lines = [f"# 리포트 {int(no)} — {title}", "",
             f"> {thesis}", "",
             "이 권은 아래 절로 이루어진다. 각 절은 **한 일 · 결과 · 방법 · 재현** 을 자기 앞에 "
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
    for c in COMPANIONS.get(no, []):
        lines += [f"이 권에는 별편이 하나 딸려 있다 — [리포트 {c['label']} «{c['title']}»]"
                  f"({c['file']}) 다. {c['what']}.", ""]
    lines.append("전체 목차는 [reports/README.md](README.md) 다."
                 if no == MAP_VOL else
                 "전체 목차는 [reports/README.md](README.md) 이고, 열다섯 권의 지도는 "
                 f"[리포트 {int(VOLUMES[0][0])} «{VOLUMES[0][2]}»]"
                 f"({VOLUMES[0][0]}_{VOLUMES[0][1]}.ipynb) 다.")
    return _cell("\n".join(lines))


def _section_rule(idx: int, title: str, meta: dict | None = None) -> dict:
    return _cell(f"---\n\n## 절 {idx}. {title}", meta=meta)


# --------------------------------------------------------------------------- #
#  1 권 절 1 — 지도(생성물)
# --------------------------------------------------------------------------- #
def _map_cells(place: dict[str, dict], titles: dict[str, str]) -> list[dict]:
    n_vol = len(_ordered_nos())
    cells: list[dict] = []

    cells.append(_cell(
        "> ### 한 일\n"
        "> **조각 빌더가 낸 편들을 «하나의 메시지 = 한 권» 기준으로 열다섯 권에 배치하고, "
        "권 안에서 각주와 상호참조를 다시 매겼다.**\n"
        "\n"
        "### 결과\n"
        f"1. 사람이 읽는 문서는 ⟨{INDEX_REL} : _meta.n_volumes⟩ 권이고, 그 안에 들어간 조각은 "
        f"⟨{INDEX_REL} : _meta.n_parts_placed⟩ 편이다. 한 권이 물음 하나를 들고, "
        "권 제목이 그 물음이다.\n"
        f"2. `reports/_parts/` 의 조각 ⟨{INDEX_REL} : _meta.n_parts_on_disk⟩ 편은 "
        "**사람이 직접 읽는 문서가 아니다** — 빌더의 중간 산출물이고, 권을 조립하는 재료다. "
        "고칠 일이 생기면 조각이 아니라 그 조각을 만든 빌더를 고친다.\n"
        f"3. 조각 사이 상호참조 ⟨{INDEX_REL} : _meta.n_crossrefs⟩ 개는 «리포트 N 절 M» 주소로 "
        "다시 쓰였고, 각주는 편 단위로 다시 번호가 매겨졌다.\n"
        + "".join(
            f"4. 한 권이 한 파일인 것이 규칙이고, **{int(ex['no'])} 권만 그림이 무거워 "
            f"{_kor(len(ex['files']))} 편**이다 — 파일이 커지면 열리지 않기 때문이지 "
            f"메시지가 {_kor(len(ex['files']))} 개여서가 아니다."
            + (f" 그 밖에 권에 딸린 별편이 {_n_companions()} 편 있다.\n"
               if COMPANIONS else "\n")
            for ex in EXTERNAL)
        + "5. 읽는 목적이 셋이면 순서도 셋이다 — **빨리 훑기**(권마다 결론 절 하나씩) · "
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
        "PYTHONPATH=src python src/build_part00_map.py              # ① 조각 빌더 12 개\n"
        "PYTHONPATH=src python src/make_report08_microdoppler.py    # ② 8 권 1~4 편\n"
        "PYTHONPATH=src python src/make_report07b_bistatic.py       # ②' 8 권 5 편\n"
        "PYTHONPATH=src python src/make_report11_2_two_channel.py   # ②\" 11-2 별편\n"
        "PYTHONPATH=src python src/build_volumes.py                 # ③ 조각 → 권\n"
        "PYTHONPATH=src python benchmark/check_report_links.py      # ④ 검사\n"
        "```\n"
        "\n"
        "| | |\n"
        "|---|---|\n"
        f"| 출력 | `reports/*.ipynb` {n_vol} 권 (+ 별편 {_n_companions()} 편) · "
        f"`{INDEX_REL}` · `reports/README.md` |\n"
        "| 소요 | 약 3 초 (GPU 0 장) |\n"
        "| 비고 | ③ 은 맨 마지막이다 — ② 가 낸 8 권 파일 뒤에 조각을 덧붙이기 때문이다. "
        "②' 와 ②\" 는 자기 파일만 내므로 ③ 과 순서를 다투지 않는다 |\n"))

    # ── 처음 여는 사람을 위한 말 풀이 ────────────────────────────────────────
    #   ⭐이 권을 처음 여는 사람은 편성이 아니라 **무엇을 하는 연구인가**를 먼저 묻는다.
    #     열다섯 권 표 앞에 그 한 화면을 둔다 — 뒤 권들이 이 낱말을 설명 없이 쓴다.
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

    # ── 열다섯 권 표 (두 셀로 나눠 화면에서 읽히게) ──────────────────────────
    def _vol_rows(nos) -> str:
        out = ["| 권 | 이 권이 답하는 물음 | 절 | 한 절만 읽는다면 |", "|---|---|---|---|"]
        for no in nos:
            e = _vol_entry(no)
            n = _n_sections(no, place)
            p = place.get(e["headline"])
            hl = (f"[절 {p['sec']} «{titles.get(e['headline'], '')}»]({p['file']})"
                  if p else "—")
            out.append(f"| [{int(no)} «{e['title']}»]({e['files'][0][0]}) "
                       f"| {_th_short(e['thesis'])} | {n} | {hl} |")
        return "\n".join(out)

    nos = _ordered_nos()
    cells.append(_cell("## 열다섯 권 (앞 절반)\n\n" + _vol_rows(nos[:8])))
    cells.append(_cell("## 열다섯 권 (뒤 절반)\n\n" + _vol_rows(nos[8:])))

    for ex in EXTERNAL:
        rows = "\n".join(f"| [{f}]({f}) | {t} |" for f, t in ex["files"])
        n_files = len(ex["files"])
        cells.append(_cell(
            f"## {int(ex['no'])} 권은 {_kor(n_files)} 편이다\n"
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
            f"| [{c['label']}]({c['file']}) | {int(no)} 권 | {c['title']} — {c['what']} "
            f"| `{c['builder']}` |"
            for no in sorted(COMPANIONS) for c in COMPANIONS[no])
        hosts = " · ".join(f"{int(no)} 권" for no in sorted(COMPANIONS))
        cells.append(_cell(
            "## 권에 딸린 별편\n"
            "\n"
            "권을 쪼갠 것이 아니라 **곁가지**다 — 어떤 권이 세운 사슬을 그대로 두고 그 권의 "
            f"가정 **하나만** 풀어 본 편이고, 그래서 빌더도 파일도 따로다. 지금 붙어 있는 "
            f"곳은 {hosts} 다.\n"
            "\n"
            "| 별편 | 어느 권에 붙나 | 무엇을 하나 | 빌더 |\n"
            "|---|---|---|---|\n" + rows + "\n"))

    # ── 조각 배치표 ─────────────────────────────────────────────────────────
    def _place_rows(sub) -> str:
        out = ["| 권 | 절 | 조각 | 그 절의 제목 |", "|---|---|---|---|"]
        for p in sub:
            m = place[p]
            out.append(f"| {int(m['vol'])} | {m['sec']} | `{p}` | {titles.get(p, '')} |")
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
        return (f"[리포트 {int(m['vol'])} 절 {m['sec']} «{titles.get(p, '')}»]({m['file']})")

    chain = " → ".join(_link(_vol_entry(no)["headline"]) for no in nos
                       if _vol_entry(no)["headline"] in place)
    cells.append(_cell(
        "## ① 빨리 훑기 — 30 분\n"
        "\n"
        "**이 저장소가 무엇을 해냈는지만 알면 되는 사람.** 권마다 결론 절 하나씩이다. "
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
        "| 저장소 최상단 목차를 15 권 편성으로 다시 낸다 | 바깥에서 들어오는 독자가 폐지된 "
        "78 편 주소로 새지 않는다 | `src/make_readme.py` |\n",
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
    doc = {"_meta": {
        "n_volumes": len(_ordered_nos()),
        "n_notebooks": (sum(len(_vol_entry(n)["files"]) for n in _ordered_nos())
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
        #   적히는 것이 가장 잦은 어긋남이다). 8-5 와 별편도 권 파일을 내므로 여기 든다.
        order=["src/build_partNN_*.py", "src/make_report08_microdoppler.py",
               "src/make_report07b_bistatic.py", "src/make_report11_2_two_channel.py",
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
    doc["companions"] = {no: [dict(c) for c in cs] for no, cs in sorted(COMPANIONS.items())}
    doc["notes"] = {
        "parts": "reports/_parts/ 의 조각은 빌더 중간 산출물이다 — 사람이 읽는 문서가 아니고, "
                 "손으로 고치지 않는다. 고칠 곳은 그 조각을 만든 src/build_partNN_*.py 다.",
        "volumes": ("reports/ 의 권이 사람이 읽는 문서다. 한 권이 한 파일이고, "
                    + " · ".join(f"{int(e['no'])} 권만 그림이 무거워 "
                                 f"{len(e['files'])} 편으로 나뉜다" for e in EXTERNAL)
                    + (f". 그 밖에 권에 딸린 별편이 {_n_companions()} 편 있다"
                       f"({', '.join(c['file'] for v in COMPANIONS.values() for c in v)})."
                       if COMPANIONS else ".")),
        "companions": {no: [c["file"] for c in cs] for no, cs in sorted(COMPANIONS.items())},
        "rebuild": "① 조각 빌더 12 개 → ② src/make_report08_microdoppler.py + "
                   "src/make_report07b_bistatic.py + src/make_report11_2_two_channel.py → "
                   "③ src/build_volumes.py → ④ benchmark/check_report_links.py",
    }
    with open(INDEX, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)


def _write_readme(place: dict[str, dict], titles: dict[str, str],
                  built: list[dict]) -> None:
    by_no = {b["no"]: b for b in built}
    L = ["<!-- 생성물 — `src/build_volumes.py` 가 낸다. 손으로 고치지 말고 그 파일을 고쳐라. -->",
         "",
         "# 리포트 — 열다섯 권",
         "",
         "패시브 바이스태틱 드론 탐지 시뮬레이터의 본문이다. **한 권이 물음 하나를 들고, 권 "
         "제목이 그 물음이다.** 권 안의 절은 각각 «한 일 · 결과 · 방법 · 재현» 을 앞에 달고 "
         "있어 필요한 절만 따로 읽어도 된다.",
         "",
         "처음이면 [리포트 1 «이 연구가 묻는 것과 답한 방식»](01_map.ipynb) 부터다 — 열다섯 "
         "권의 지도와 읽는 경로 셋이 거기 있다.",
         "",
         "## 열다섯 권",
         "",
         "| 권 | 이 권이 답하는 물음 | 절 | 한 절만 읽는다면 |",
         "|---|---|---|---|"]
    for no in _ordered_nos():
        e = _vol_entry(no)
        b = by_no[no]
        p = place.get(e["headline"])
        hl = f"[절 {p['sec']} «{titles.get(e['headline'], '')}»]({p['file']})" if p else "—"
        L.append(f"| [{int(no)} «{e['title']}»]({e['files'][0][0]}) "
                 f"| {_th_short(e['thesis'])} | {b['n_sections']} | {hl} |")
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
        L += [f"### [{int(no)} «{e['title']}»]({e['files'][0][0]})", ""]
        if e["external"]:
            L += [f"그림이 무거워 **{len(e['files'])} 편**으로 나뉜다"
                  f"(빌더 `{next(x['builder'] for x in EXTERNAL if x['no'] == no)}`).", "",
                  "| 편 | 무엇에 답하나 |", "|---|---|"]
            L += [f"| [{f}]({f}) | {t} |" for f, t in e["files"]]
            L += ["", f"아래 절은 이 스크립트가 `{b['append_to']}` 뒤에 이어 붙인 것이다.", ""]
        for c in COMPANIONS.get(no, []):
            L += [f"별편 하나가 딸려 있다 — [{c['label']} «{c['title']}»]({c['file']}) "
                  f"(빌더 `{c['builder']}`). {c['what']}.", ""]
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
          "PYTHONPATH=src python src/build_part00_map.py              # ① 조각 빌더 12 개",
          "#  … build_part01_stock_engine.py … build_part11_measurement.py",
          "PYTHONPATH=src python src/make_report08_microdoppler.py    # ② 8 권 1~4 편",
          "PYTHONPATH=src python src/make_report07b_bistatic.py       # ②' 8 권 5 편",
          "PYTHONPATH=src python src/make_report11_2_two_channel.py   # ②\" 11-2 별편",
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
    return dict(no=no, file=fname, title=title, external=False,
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
    return dict(no=no, file=ex["files"][0][0], title=ex["title"], external=True,
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

    print(f"\n✅ {len(built)} 권 → reports/   (조각 {len(place)} 편 배치, "
          f"{len(SUPERSEDED)} 편 미배치)")
    print(f"   상호참조 재배선 — 다른 편 "
          f"{stat.get('xref_cross', 0) + stat.get('coderef_cross', 0)} · 같은 편 "
          f"{stat.get('xref_intra', 0) + stat.get('coderef_intra', 0)} · 옛 부 "
          f"{stat.get('buref', 0) + stat.get('buprose', 0)} · "
          f"버림 {stat.get('xref_dropped', 0)}")
    print(f"   색인 {os.path.relpath(INDEX, _ROOT)} · 목차 reports/README.md")


if __name__ == "__main__":
    main()
