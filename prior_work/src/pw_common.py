# -*- coding: utf-8 -*-
"""pw_common.py — prior_work 리포트 공통 헬퍼 (facts JSON 로더 + 셀 빌더)."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PW = os.path.abspath(os.path.join(HERE, ".."))
J = json.load(open(os.path.join(PW, "outputs", "prior_work.json"), encoding="utf-8"))
PAPERS = {p["key"]: p for p in J["papers"]}
TOOLS = {t["key"]: t for t in J["tools"]}
SYN = J["synthesis"]
GRADE = J["meta"]["verify_grades"]

# 검증등급 → 배지(그림 텍스트 아님, 본문 인라인이라 한글 OK)
BADGE = {"CONFIRMED": "✅검증", "WEB": "🔎직접확인", "SOURCE": "📄단일출처",
         "IMAGE_LEAD": "⚠미검증단서"}


def md(*lines):
    src = "\n".join(lines).splitlines(keepends=True)
    return {"cell_type": "markdown", "metadata": {}, "source": src or [""]}


def code(*lines):
    src = "\n".join(lines).splitlines(keepends=True)
    return {"cell_type": "code", "metadata": {}, "source": src or [""],
            "outputs": [], "execution_count": None}


def srclinks(item):
    return " · ".join(f"[{i+1}]({u})" for i, u in enumerate(item.get("sources", [])))


def write_nb(cells, name, tag):
    for i, c in enumerate(cells):
        c["id"] = f"{tag}-{i:02d}"
    nb = {"cells": cells,
          "metadata": {"kernelspec": {"display_name": "py312", "language": "python",
                                      "name": "py312"},
                       "language_info": {"name": "python"}},
          "nbformat": 4, "nbformat_minor": 5}
    out = os.path.join(PW, name)
    json.dump(nb, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("wrote", out, len(cells), "cells")
