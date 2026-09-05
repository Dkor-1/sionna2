# -*- coding: utf-8 -*-
"""
check_stale_titles.py — **편 제목이 바뀌었는데 그 편을 가리키는 이름표가 안 따라왔나**
==========================================================================================
왜 이 관문이 필요한가
    2026-09-05 에 **내가 직접 저질렀다.** 편 27·53 의 제목을 빌더에서 고치고 관문 셋을
    통과시킨 뒤 커밋했는데, 그 편을 **링크로 가리키는 다른 권들**은 다시 굽지 않아서
    옛 제목이 여섯 자리에 남아 있었다:
        「리포트 8 절 3 «**운용 형상에서** 경험 Pfa 를 재니…»」   ← 제목은 «실내 통제 기하» 로 바뀜
        「"title": "메쉬가 사는 축은 **절대 크기가 아니라** 각도 구조다"」  ← 편 27 옛 제목
    ⛔기존 관문 셋은 이걸 못 본다 —
        `check_report_links`  링크가 **끊겼는지**만 본다(이름표는 안 본다)
        `check_row_pointers`  각주가 제 행을 가리키는지
        `check_retracted`     철회한 **수**가 다시 인용됐는지

무엇을 하나
    `report_registry.REPORTS` 가 정본이다. 발행면에서 `«...»` 로 편을 부르는 이름표와
    `outputs/reports_index/*.json` 의 `title`·`short` 를 그 정본과 대조한다.
    ⭐이름표는 길면 «…» 로 잘리므로 **앞부분 일치**로 본다.

⛔이 관문은 판정하지 않는다 — 정본과 다르면 «다시 구워라» 라고만 한다.

실행
    cd /workspace/sionna
    CUDA_VISIBLE_DEVICES="" PYTHONPATH=src:benchmark python benchmark/check_stale_titles.py
        --all  어긋난 자리를 전부 인쇄한다(기본은 파일마다 3 줄)
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from report_registry import REPORTS                                    # noqa: E402

#: `[편 53 «제목…»](53_cfar-calib.ipynb)` · `[리포트 8 절 3 «제목…»](08_detector.ipynb)`
_LABEL = re.compile(r"«([^»]{4,})»\]\(([0-9A-Za-z_./-]+\.ipynb)")
#: 이름표가 잘린 자리 — «…» 또는 «...»
_ELLIPSIS = ("…", "...")


def canon() -> dict:
    """파일 이름 → 정본 제목."""
    out = {}
    for anchor, r in REPORTS.items():
        out[os.path.basename(r["file"])] = r["title"]
    return out


def head_matches(label: str, title: str) -> bool:
    """이름표가 정본 제목의 **앞부분**인가(잘린 것을 감안한다)."""
    def norm(x: str) -> str:
        #: 노트북 JSON 은 `|` 를 `\\|` 로 이스케이프한다 — 비교 전에 푼다.
        return x.replace("\\|", "|").replace("\\", "").replace(" ", "")
    lab = norm(label.rstrip("".join(_ELLIPSIS)).strip())
    if not lab:
        return True
    return norm(title).startswith(lab)


def scan_labels() -> list:
    C = canon()
    hits = []
    for p in sorted(glob.glob(f"{ROOT}/reports/*.ipynb")
                    + glob.glob(f"{ROOT}/reports/_parts/*.ipynb")
                    + glob.glob(f"{ROOT}/reports/README.md")
                    + [f"{ROOT}/README.md"]):
        rel = os.path.relpath(p, ROOT)
        try:
            s = open(p, encoding="utf-8").read()
        except OSError:
            continue
        for m in _LABEL.finditer(s):
            label, target = m.group(1), os.path.basename(m.group(2))
            title = C.get(target)
            if title is None:
                continue                       # 계획 밖 조각 — 링크 관문이 따로 본다
            #: ⭐**자동으로 잘린 이름표만 본다.** 빌더는 `ref(anchor, "교정 사다리")` 처럼
            #  **일부러 짧은 이름표**를 붙이기도 한다 — 그건 낡은 게 아니라 의도다.
            #  자동 이름표는 `report_registry.ref()` 가 제목을 잘라 «…» 를 붙인 것이라
            #  끝에 말줄임이 있다. 그것만 정본과 대조한다.
            if not label.rstrip().endswith(_ELLIPSIS):
                continue
            if not head_matches(label, title):
                hits.append((rel, label[:60], target, title[:70]))
    return hits


def scan_index() -> list:
    C = {os.path.basename(r["file"]): r["title"] for r in REPORTS.values()}
    hits = []
    for p in sorted(glob.glob(f"{ROOT}/outputs/reports_index/*.json")):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        f, t = d.get("file"), d.get("title")
        if not f or not t:
            continue
        want = C.get(os.path.basename(f))
        if want and want != t:
            hits.append((os.path.relpath(p, ROOT), t[:60], os.path.basename(f), want[:70]))
    return hits


def main() -> int:
    show_all = "--all" in sys.argv
    lab, idx = scan_labels(), scan_index()
    print("── 편 제목이 바뀌었는데 이름표가 안 따라왔나 ──")
    print(f"  계획 편 {len(REPORTS)} · 어긋난 이름표 {len(lab)} · 어긋난 색인 {len(idx)}\n")
    if not lab and not idx:
        print("✅ 이름표와 색인이 모두 현행 제목과 맞는다")
        return 0
    for name, rows in (("이름표", lab), ("색인", idx)):
        if not rows:
            continue
        print(f"⛔ {name} {len(rows)}건")
        for rel, got, target, want in (rows if show_all else rows[:8]):
            print(f"   {rel}")
            print(f"     적힌 것: «{got}»")
            print(f"     정본  : «{want}»  ({target})")
        if not show_all and len(rows) > 8:
            print(f"   … 외 {len(rows) - 8}건 (`--all`)")
    print("\n⛔ 제목을 바꿨으면 **그 편을 가리키는 권까지** 다시 구워라 —")
    print("   src/build_volumes.py · src/make_readme.py · src/make_reports_index.py")
    return 1


if __name__ == "__main__":
    sys.exit(main())
