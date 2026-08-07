# -*- coding: utf-8 -*-
"""
make_legacy_map.py — 옛 편·옛 빌더가 어디로 갔는지 한 장으로 적는다
==========================================================================================
재구성이 옛 8편을 78편으로 흩었다. **무엇을 지워도 되는지**는 «그 셀이 새 편 어딘가에
살아 있는가» 로만 정해진다. 그래서 옛 노트북의 셀을 하나씩 세고, 계획의 배치표
(`outputs/restruct_exec_plan.json : cell_disposition`)와 맞대 이관율을 낸다.

산출
    docs/LEGACY_MIGRATION.md

⛔ 이 문서는 **지우지 않는다** — 무엇을 지워도 되는지만 적는다. 철거는 대조가 끝난 뒤다.

실행
    PYTHONPATH=src ~/.venvs/py312/bin/python src/make_legacy_map.py
"""
from __future__ import annotations

import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from report_registry import REPORTS                                     # noqa: E402

OUT = os.path.join(ROOT, "docs", "LEGACY_MIGRATION.md")
PLAN = os.path.join(ROOT, "outputs", "restruct_exec_plan.json")

OLD = [
    ("report00_foundations", "src/make_report00_foundations.py", "부 1 · 4"),
    ("report01_prior", "src/make_report01_prior.py", "부 2"),
    ("report02_target", "src/make_report02_target.py", "부 3 · 4 · 5"),
    ("report03_illuminators", "src/make_report03_illuminators.py", "부 8"),
    ("report04_detector", "src/make_report04_detector.py", "부 9"),
    ("report05_results", "src/make_report05_results.py", "부 10"),
    ("report06_measurement", "src/make_report06_measurement.py", "부 11"),
    ("report07_microdoppler", "src/make_report07_microdoppler.py", "부 7"),
]

#: ⚠ 아직 끊으면 안 되는 옛 빌더 — 새 빌더가 **읽기 전용으로** 임포트한다.
STILL_IMPORTED = {
    "src/make_report05_results.py":
        "`src/build_part10_results.py` 가 `derived()`·`dnum()` 을 임포트한다 — 옛 편과 새 편의 "
        "파생 수치를 비트 단위로 같게 두려고 그렇게 뒀다. `derived()` 를 독립 모듈로 옮기면 끊긴다.",
}

#: 이 라운드에서 실측으로 잡은 계획의 오류. 지우기 전에 반드시 읽어야 한다.
CORRECTIONS = [
    ("`report00` 셀 번호가 c16 부터 +1 밀려 있었다",
     "계획의 `from_cells` 가 c16 이후로 한 칸씩 어긋났다. 실제 셀을 세어 맞췄다 — "
     "편 21 ← c18 · 편 22 ← c19 · 편 23 ← c22 다. 계획대로 c19/c20/c23 을 쓰면 편 21 이 "
     "«한계» 를, 편 23 이 `next_steps` 를 실었을 것이다."),
    ("`report02:c9`(가림 표) 는 편 18 로 갔다",
     "계획은 c9 를 편 19(kernel-vs-stock)에 붙였지만, c9 는 c8 의 가림 그림과 한 몸인 표다. "
     "«한 편 = 한 메시지» 를 지키려고 편 18(kernel-what)에 c8 과 함께 두었다."),
    ("`report02:c10` 을 둘로 쪼갰다",
     "앞쪽(바이스태틱 출사 가시성)은 편 20, 뒤쪽(§3 기준해 셋의 분해식)은 편 21 이다. "
     "계획의 분할 목록(c7·c20)에 없던 세 번째 분할이다."),
    ("`report02:c25`(논문 방법 문단)를 아무도 안 가져갔다",
     "`src/make_reports_index.py:write_paper_02()` 가 `docs/paper/02_target.md` 로 옮겼다."),
    ("편 77(`size-law-differential`)은 계획에 없다",
     "옛 `report06:c22` 에 중심 메시지가 둘이라 부 11 담당이 꼬리 번호로 신설했다. "
     "`src/report_registry.py` 가 색인 샤드에서 주워 사전에 넣으므로 `ref()` 가 가리킨다."),
]


def _md_cells(stem: str) -> int:
    p = os.path.join(ROOT, f"{stem}.ipynb")
    if not os.path.exists(p):
        return -1
    with open(p, encoding="utf-8") as f:
        return sum(1 for c in json.load(f).get("cells", [])
                   if c.get("cell_type") == "markdown")


def build() -> str:
    with open(PLAN, encoding="utf-8") as f:
        plan = json.load(f)
    disp = plan["cell_disposition"]
    cov = plan["cell_coverage"]

    per: dict[str, list[str]] = {}
    for key in disp:
        per.setdefault(key.split(":")[0], []).append(key)

    L = ["<!-- 생성물 — `src/make_legacy_map.py` 가 쓴다. -->", "",
         "# 옛 편은 어디로 갔나 — 철거 전 대조표", "",
         "재구성이 옛 **8편**을 **78편**으로 흩었다. 이 문서는 «무엇을 지워도 되는지» 하나만",
         "적는다. **⛔ 지금 지우지 않는다** — 셀 대조(Verify)가 끝난 뒤가 철거 시점이다.", "",
         f"계획의 배치표는 옛 셀 {cov['n_md_cells']}개(마크다운) + {cov['n_code_cells']}개(코드) "
         f"= **{cov['n_disposed']}개 전부**를 배치했고, 누락 {len(cov['missing'])}건 · "
         f"계획 밖 중복 {len(cov['duplicated_beyond_planned_splits'])}건이다.", "",
         "| 옛 노트북 | 옛 빌더 | md셀 | 배치된 셀 | 어디로 | 판정 |",
         "|---|---|---|---|---|---|"]

    for stem, builder, where in OLD:
        n_md = _md_cells(stem)
        n_disp = len(per.get(stem.split("_")[0], []))
        if stem.startswith("report07"):
            # 계획은 report07 을 셀 단위로 배치하지 않고 «부 7 이 된다» 로 통째 처리했다.
            n_disp, ok = n_md, "✅ 전부 이관 (부 7 통째)"
        else:
            ok = "✅ 전부 이관" if n_disp >= n_md > 0 else "⚠ 대조 필요"
        note = " (⚠ 임포트 중)" if builder in STILL_IMPORTED else ""
        L.append(f"| `{stem}.ipynb` | `{builder}`{note} | {n_md if n_md >= 0 else '—'} "
                 f"| {n_disp} | {where} | {ok} |")

    L += ["", "새 편을 짓는 빌더는 아래 13개다 — 옛 빌더 8개를 대신한다.", "",
          "```", "src/build_part00_map.py           부 0   편 00",
          "src/build_part01_stock_engine.py  부 1   편 01~07",
          "src/build_part02_prior_work.py    부 2   편 08~14",
          "src/build_part03_target_mesh.py   부 3   편 15~17",
          "src/build_part04_kernel.py        부 4   편 18~23",
          "src/build_part05_anchor.py        부 5   편 24~29",
          "src/build_part06_ladder.py        부 6   편 30~33",
          "src/build_part07_microdoppler.py  부 7   편 34~43",
          "src/build_part08_illuminators.py  부 8   편 44~50",
          "src/build_part09_detector.py      부 9   편 51~55",
          "src/build_part10_results.py       부 10  편 56~66",
          "src/build_part11_measurement.py   부 11  편 67~77",
          "```", "",
          "## ⚠ 아직 끊으면 안 되는 것", ""]
    for k, v in STILL_IMPORTED.items():
        L += [f"- **`{k}`** — {v}"]
    L += ["", "옛 노트북 8개는 전부 **대조용**으로 제자리에 있다. 새 편의 숫자가 옛 편과 같은지를",
          "확인할 마지막 기회이므로, Verify 가 셀 대조를 마치기 전에는 옮기지 않는다.", "",
          "## 계획에서 어긋났던 곳 (이 라운드에서 실측으로 잡았다)", ""]
    for what, why in CORRECTIONS:
        L += [f"### {what}", "", why, ""]

    L += ["## 철거 절차 (Verify 뒤)", "",
          "1. `PYTHONPATH=src python benchmark/check_report_links.py` 가 위반 0 인지 본다.",
          "2. 옛 편의 숫자와 새 편의 숫자를 셀 단위로 대조한다.",
          "3. `src/make_report05_results.py` 의 `derived()` 를 독립 모듈로 옮겨 임포트를 끊는다.",
          "4. 옛 노트북 8개와 옛 빌더 8개를 `_legacy_reports/` · `src/_legacy_builders/` 로 "
          "옮긴다(지우지 않는다).",
          "5. `PYTHONPATH=src python src/make_reports_index.py` · `src/make_readme.py` 를 다시 "
          "돌려 README 의 «옛 8편» 행을 지운다.", ""]
    return "\n".join(L) + "\n"


def main() -> int:
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(build())
    print(f"✅ {os.path.relpath(OUT, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
