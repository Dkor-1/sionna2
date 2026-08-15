# -*- coding: utf-8 -*-
"""
make_legacy_stubs.py — 루트의 옛 리포트를 **«어디로 갔는지» 안내**로 바꾼다.

왜
--
재구성으로 새 편이 `reports/` 에 78개 섰는데, 루트의 옛 노트북 7개가 그대로 남아 있었다.
사용자가 리포트를 열면 그 옛 것을 보게 된다 — 그리고 그것은 한 편에 34~88분짜리다.
새 편은 8~13분이다. **읽는 사람이 옛 것을 붙잡고 있는 것이 문제였다.**

⛔ 지우지 않는다. 내용을 안내로 **바꾼다** — 노트북은 생성물이고 빌더는 그대로 남는다.
   되돌리려면 옛 빌더(`src/make_report0N_*.py`)를 다시 돌리면 된다.

근거: `docs/LEGACY_MIGRATION.md` — 옛 셀 174개 **전부** 새 편에 배치됐고 누락 0건이다.

    python src/make_legacy_stubs.py
"""
from __future__ import annotations

import json
import os
import re

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))

# 옛 편 → (제목, 새 편이 있는 부, 대표 편들)
MAP = {
    "report00_foundations": (
        "기초: Sionna 로 되는 것과, 표적 산란이 시작되는 자리",
        "부 1 「스톡 엔진이 하는 일과 안 하는 일」 · 부 4 「우리 커널」",
        ["01_stock-says", "02_engine-paths", "03_engine-amplitude", "04_eight-factors",
         "05_size-sweep", "06_decision-table", "07_why-po"]),
    "report01_prior": (
        "선행 연구가 표적 서명을 어디서 조달했나",
        "부 2 「선행 연구」",
        ["08_census-published", "09_census-preprint", "10_procurement",
         "11_procurement-catalog"]),
    "report02_target": (
        "메쉬 7종의 σ 를 광선 가림 + 재질 PO 로",
        "부 3 「표적 메쉬」 · 부 4 「우리 커널」 · 부 5 「앵커」",
        ["15_mesh-build", "16_mesh-photo", "18_kernel-po", "24_anchor-das"]),
    "report03_illuminators": (
        "세 파형을 한 표적·한 검출기로 비교",
        "부 8 「조명원」",
        ["51_illum-waveforms", "52_illum-occupancy"]),
    "report04_detector": (
        "검출 사슬의 경험 Pfa 와 CFAR 문턱",
        "부 9 「검출기」",
        ["57_det-chain", "58_det-cfar"]),
    "report05_results": (
        "세 조명원의 검출거리를 앵커 σ 위에서",
        "부 10 「결과」",
        ["63_res-r90", "64_res-multirx"]),
    "report06_measurement": (
        "X410 로 교정된 σ 를 얻는 세션 설계",
        "부 11 「측정 설계」",
        ["70_meas-hardware", "71_meas-farfield"]),
}


def md(*lines):
    return {"cell_type": "markdown", "metadata": {},
            "source": [l + "\n" for l in "\n".join(lines).split("\n")]}


def existing(cands):
    """실제로 있는 편만 남긴다 — 없는 편을 가리키면 안내가 거짓이 된다."""
    out = []
    for c in cands:
        for f in os.listdir(os.path.join(_ROOT, "reports")):
            if f.startswith(c.split("_")[0] + "_") and f.endswith(".ipynb"):
                out.append(f[:-6])
                break
    return out


def title_of(stem):
    """새 편의 첫 줄에서 제목을 읽는다 — 손으로 옮겨 적지 않는다."""
    p = os.path.join(_ROOT, "reports", stem + ".ipynb")
    nb = json.load(open(p))
    first = "".join(nb["cells"][0]["source"]).split("\n")[0]
    return re.sub(r"^#\s*리포트\s*\d+\s*—\s*", "", first).strip()


def main():
    n = 0
    for old, (subj, parts, cands) in MAP.items():
        stems = existing(cands)
        rows = [f"| [`{s}`](reports/{s}.ipynb) | {title_of(s)} |" for s in stems]
        cells = [
            md(f"# 이 편은 갈라졌습니다 — {subj}", "",
               "> ⭐ **새 편은 `reports/` 에 있습니다.** 이 파일은 안내만 남깁니다.", "",
               f"재구성으로 리포트가 **8편 → 78편**이 됐습니다. 한 편에 중심 메시지 하나만 "
               f"담고, 편당 **10분** 안에 읽히도록 나눴습니다(전에는 34~88분이었습니다).", "",
               f"이 편의 내용은 **{parts}** 로 갔습니다.", "",
               "| 새 편 | 제목 |",
               "|---|---|",
               *rows, "",
               "---", "",
               "**어디부터 읽나** — [`reports/01_map.ipynb`](reports/01_map.ipynb) 이 "
               "읽는 목적별로 순서를 안내합니다.", "",
               "**전체 목록** — [`README.md`](README.md) · "
               "**다시 돌리기** — [`docs/REPRODUCE.md`](docs/REPRODUCE.md) · "
               "**대조표** — [`docs/LEGACY_MIGRATION.md`](docs/LEGACY_MIGRATION.md)", "",
               "⚠ 옛 내용을 다시 보려면 옛 빌더를 돌리면 됩니다 — "
               f"`PYTHONPATH=src python src/make_{old}.py`"),
        ]
        nb = {"cells": cells, "metadata": {
            "kernelspec": {"display_name": "py312", "language": "python", "name": "py312"},
            "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}
        with open(os.path.join(_ROOT, old + ".ipynb"), "w") as f:
            json.dump(nb, f, ensure_ascii=False, indent=1)
        print(f"  ✅ {old}.ipynb → 안내 ({len(stems)} 편으로)")
        n += 1
    print(f"\n  옛 편 {n}개를 안내로 바꿨다. ⛔지우지 않았고, 빌더도 그대로다.")


if __name__ == "__main__":
    main()
