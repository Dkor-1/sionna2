# -*- coding: utf-8 -*-
"""
build_volumes.py — ⭐**78 편의 조각을 15 권으로 묶는다** (사용자 지시 2026-08-10)

사용자:
> *"레포트를 지금 너무 심하게 잘게 쪼갠 거 같은데... 그래도 적당히 **하나의 메시지를 담아서**
>  해주면 좋겠어. 0~6 을 한 **20 개 이내로** 적당히 메시지가 담기게끔 구성해주면 좋겠고,
>  7 번도 7 번을 고집한다기보다는 **순서상 어울리는 위치로** 레포트 번호를 매겨서 만들어줘.
>  지금 77 개로 쪼갠 것은 너무 과해"*

왜 78 편이 됐나 — 그리고 왜 그게 규약 탓이 아닌가
--------------------------------------------------
분량 상한(§5.7 `MAX_MD_CELLS`)은 25 셀인데 실제 편들은 7~12 셀이다. 즉 상한에 밀려 쪼개진 게
아니라 «한 편에 한 주제» 라는 **편집 판단**이 너무 잘게 적용된 것이다. 그래서 고칠 곳은
규약이 아니라 **묶는 방식**이다.

설계 — 빌더는 그대로 두고 그 위에 «묶는 층» 을 얹는다
------------------------------------------------------
⭐ 조각들의 숫자는 전부 원장 JSON 에서 주입된다(`src/build_partNN_*.py`). 손으로 합치면
   그 사슬이 끊긴다. 그래서 이 스크립트는 **조각을 다시 쓰지 않는다** — 빌더가 만든 조각을
   읽어 **순서대로 잇고, 각주 번호만 권 단위로 다시 매기고, 권의 머리말을 앞에 붙인다.**
   ⇒ 재계산 → 빌더 재실행 → 이 스크립트 재실행이면 권의 숫자도 함께 갱신된다.

   조각:  reports/_parts/NN_anchor.ipynb   (빌더 산출 · 사람이 직접 읽는 문서가 아니다)
   권  :  reports/NN_slug.ipynb            (사람이 읽는 문서 · 15 권)

⚠ 각주 충돌 — 조각마다 `[^1]` 부터 다시 센다. 그대로 이으면 한 권 안에서 번호가 겹친다.
  그래서 조각을 이을 때 **오프셋을 더해 다시 매긴다**(정의 줄과 인용 둘 다).

    python src/build_volumes.py
"""
from __future__ import annotations

import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
PARTS = os.path.join(_ROOT, "reports", "_parts")
OUT = os.path.join(_ROOT, "reports")

# --------------------------------------------------------------------------- #
#  권 구성 — 한 권 = 하나의 메시지
#    (번호, 슬러그, 제목, 한 줄 논지, [조각 번호...])
#  ⭐ 순서는 «묻는 것 → 도구를 믿을 근거 → 표적 → 신호 → 처리 → 결과 → 실측» 이다.
#     마이크로도플러 표지(옛 report07_microdoppler.ipynb)는 «7 번» 을 고집하지 않고
#     이 흐름에서 제 자리인 **8 권**의 표지로 들어간다(사용자 지시).
# --------------------------------------------------------------------------- #
VOLUMES = [
    ("01", "map", "이 연구가 묻는 것과 답한 방식",
     "패시브 바이스태틱으로 드론을 **탐지하고 마이크로도플러로 분류**하는 것이 태스크이고, "
     "RCS 는 그 인프라다. 이 권은 나머지 열네 권의 지도다.",
     ["00", "13", "75"]),
    ("02", "stock-engine", "스톡 Sionna 로는 왜 부족한가",
     "스톡 레이 트레이서는 경로를 풀지 **산란적분을 하지 않는다**. "
     "그 한 가지가 드론처럼 작은 표적에서 무엇을 무너뜨리는지 여덟 갈래로 잰다.",
     ["01", "02", "03", "04", "05", "06", "07"]),
    ("03", "prior-work", "선행연구는 어디까지 왔고 우리는 어디 서는가",
     "공개 문헌과 오픈소스를 전수로 세어, 우리가 **새로 하는 것과 빌려 쓰는 것**을 갈라 적는다.",
     ["08", "09", "10", "11", "12", "14"]),
    ("04", "target-mesh", "표적을 짓는다 — 메쉬와 재질",
     "기체 아홉 대를 CAD 로 짓고 실물 사진·도면과 대조한다. "
     "**재질은 측정이 아니라 선언**이고, 그 선언이 어디까지 미치는지 함께 적는다.",
     ["15", "16", "17"]),
    ("05", "kernel", "우리 커널 — 무엇이고, 무엇이 아닌가",
     "SBR + 물리광학이 무엇을 계산하고 무엇을 **계산하지 않는지**를 정의하고, "
     "해석해가 있는 과녁(구·평판·이면각)으로 잰다.",
     ["18", "19", "20", "21", "22", "23"]),
    ("06", "anchor", "σ 를 무엇에 붙들어 매나",
     "우리 σ 의 절대 레벨을 붙드는 것은 **공개 문헌 한 기체·한 실험실**뿐이다. "
     "그 끈의 장력을 재고, 끊어질 자리를 먼저 적는다.",
     ["24", "25", "26", "27", "28", "29"]),
    ("07", "size-law", "크기 법칙 — 작아지면 얼마나 어려워지나",
     "기체 크기를 사다리로 놓고 σ 와 검출거리가 어떻게 따라오는지 본다. "
     "**사다리의 답이 이르게 나오면 그것부터 의심한다.**",
     ["30", "31", "32", "33", "77"]),
    ("08", "microdoppler", "마이크로도플러 — 도는 로터가 남기는 무늬",
     "호버링하는 드론은 제자리에 있지만 **프로펠러는 돈다**. "
     "그 회전이 남기는 시간-주파수 무늬가 이 연구의 분류 축이다.",
     ["34", "35", "36", "37", "38", "39"]),
    ("09", "microdoppler-limits", "마이크로도플러 — 무엇이 그 무늬를 흐리나",
     "자세·보정·광선 예산·표본율 네 가지가 무늬를 지운다. "
     "각각을 **단일축으로 갈라** 얼마나 지우는지 잰다.",
     ["40", "41", "42", "43"]),
    ("10", "illuminators", "무엇을 조명원으로 쓸 수 있나",
     "LTE·5G·WiFi 가 각각 **얼마나 자주, 얼마나 넓게** 신호를 내주는가. "
     "5G 는 대역이 넓은 대신 상시 신호가 드물어 **이중고**가 된다.",
     ["44", "45", "46", "47", "48", "49", "50"]),
    ("11", "detector", "처리 사슬 — 직접파를 죽이고 표적을 세운다",
     "ECA 로 직접파를 지우고 CFAR 로 문턱을 세운다. "
     "**문턱을 어디에 두느냐가 결과를 정하므로** 그 교정을 먼저 적는다.",
     ["51", "52", "53", "54"]),
    ("12", "observability", "관측가능성과 기하 — 어디에 서야 보이나",
     "송신기·수신기·표적의 배치가 검출을 정한다. "
     "**볼 수 없는 자리**를 먼저 지도로 그리고, 그 다음에 거리를 말한다.",
     ["55", "56", "57", "58"]),
    ("13", "results", "결과 — 얼마나 멀리서 보이나",
     "R90 과 순위가 이 연구의 정량 결론이다. "
     "적분시간·잔류·σ 가정을 흔들어 **순위가 견디는지**까지 함께 적는다.",
     ["59", "60", "61", "62", "63"]),
    ("14", "robustness", "결론이 무엇에 기대고 있나 — 강건성과 하드웨어",
     "표적 모형·수신 소자·장비를 바꿔 넣어 **결론이 어디서 흔들리는지** 본다.",
     ["64", "65", "66", "67", "68"]),
    ("15", "measurement", "실측 계획 — 무엇을 재야 이 문서가 닫히나",
     "시뮬레이션이 선언으로 남겨 둔 것들의 목록과, 그것을 닫는 **야외 실측 규약**이다.",
     ["69", "70", "71", "72", "73", "74", "76"]),
]

_FN_DEF = re.compile(r"^\[\^(\d+)\]:", re.M)     # 각주 정의 줄
_FN_REF = re.compile(r"\[\^(\d+)\]")             # 각주 인용


def _shift_footnotes(src: str, off: int) -> str:
    """각주 번호를 off 만큼 민다 — 정의와 인용을 함께."""
    if off == 0:
        return src
    return _FN_REF.sub(lambda m: f"[^{int(m.group(1)) + off}]", src)


def _max_footnote(src: str) -> int:
    ns = [int(m.group(1)) for m in _FN_REF.finditer(src)]
    return max(ns) if ns else 0


def _load_part(no: str) -> tuple[str, list]:
    """조각 하나를 읽어 (제목, 셀들) 로 돌려준다."""
    hits = [f for f in os.listdir(PARTS) if f.startswith(f"{no}_") and f.endswith(".ipynb")]
    if not hits:
        raise FileNotFoundError(f"조각 {no} 를 {PARTS} 에서 못 찾았다 — 빌더를 먼저 돌려라")
    nb = json.load(open(os.path.join(PARTS, hits[0]), encoding="utf-8"))
    cells = nb["cells"]
    head = "".join(cells[0]["source"]) if cells else ""
    m = re.match(r"#\s*리포트\s*\d+\s*—\s*(.+)", head)
    title = m.group(1).strip() if m else hits[0]
    return title, cells


def _vol_intro(no: str, slug: str, title: str, thesis: str,
               sections: list[tuple[str, str]]) -> dict:
    """권의 머리말 — 하나의 메시지와 그 안의 절 목록."""
    lines = [f"# 리포트 {int(no)} — {title}", "",
             f"> {thesis}", "",
             "이 권은 아래 절로 이루어진다. 각 절은 **한 일 · 결과 · 방법 · 재현**을 자기 앞에 "
             "달고 있어, 필요한 절만 따로 읽어도 된다.", "",
             "| 절 | 무엇을 말하나 |", "|---|---|"]
    for i, (_, t) in enumerate(sections, 1):
        lines.append(f"| {i} | {t} |")
    lines += ["",
              "⭐ 숫자는 전부 계산 결과 JSON(원장)에서 주입된다 — 각주가 그 출처다. "
              "원장이 다시 계산되면 빌더를 돌리는 것만으로 본문 숫자가 따라 바뀐다."]
    return {"cell_type": "markdown", "metadata": {},
            "source": [l + "\n" for l in lines]}


def _section_rule(idx: int, title: str) -> dict:
    """절 구분자 — 조각의 원래 여는 블록 앞에 놓는다."""
    return {"cell_type": "markdown", "metadata": {},
            "source": [f"---\n", f"\n", f"## 절 {idx}. {title}\n"]}


def main() -> None:
    if not os.path.isdir(PARTS):
        print(f"⚠ {PARTS} 가 없다. 먼저 조각을 그리로 옮기거나 빌더 OUT 을 바꿔라.")
        sys.exit(1)
    os.makedirs(OUT, exist_ok=True)
    made = []
    for no, slug, title, thesis, parts in VOLUMES:
        loaded = [_load_part(p) for p in parts]
        sections = [(p, t) for p, (t, _) in zip(parts, loaded)]
        cells = [_vol_intro(no, slug, title, thesis, sections)]
        off = 0
        for i, (p, (t, cs)) in enumerate(zip(parts, loaded), 1):
            cells.append(_section_rule(i, t))
            hi = 0
            for c in cs:
                src = "".join(c["source"])
                hi = max(hi, _max_footnote(src))
                src = _shift_footnotes(src, off)
                # 조각의 «# 리포트 NN —» 제목 줄은 절 구분자가 대신하므로 지운다
                src = re.sub(r"^#\s*리포트\s*\d+\s*—.*\n?", "", src, count=1)
                if not src.strip():
                    continue
                cells.append({"cell_type": c["cell_type"], "metadata": c.get("metadata", {}),
                              "source": [l + "\n" for l in src.rstrip("\n").split("\n")]})
            off += hi
        nb = {"cells": cells,
              "metadata": {"kernelspec": {"display_name": "py312", "language": "python",
                                          "name": "py312"},
                           "language_info": {"name": "python"}},
              "nbformat": 4, "nbformat_minor": 5}
        path = os.path.join(OUT, f"{no}_{slug}.ipynb")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(nb, f, ensure_ascii=False, indent=1)
        nmd = sum(1 for c in cells if c["cell_type"] == "markdown")
        made.append((path, len(parts), nmd, off))
        print(f"  ✅ {os.path.relpath(path, _ROOT):34s} 조각 {len(parts):2d}개 · "
              f"셀 {nmd:3d} · 각주 {off:3d}")
    print(f"\n✅ {len(made)} 권 → reports/   (조각 {sum(m[1] for m in made)} 개를 묶었다)")


if __name__ == "__main__":
    main()
