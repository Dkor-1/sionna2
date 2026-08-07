# -*- coding: utf-8 -*-
"""
make_reports_index.py — 편 78개의 색인·재현·논문 목차를 짓는다
==========================================================================================
재구성으로 편이 8 → 78 이 되면서 «어느 편이 무엇을 쓰고 무엇을 내는가» 를 사람이 외울 수
없게 됐다. 그래서 세 문서를 **노트북에서 직접 읽어** 만든다 — 손으로 적은 사본을 두지 않는다.

    outputs/reports_index.json   편마다 근거 JSON · 그림 · 재현 명령 · 분량 (기계용)
    docs/REPRODUCE.md            읽기 경로 ③ «다시 돌리기» — 편 → 명령 → 출력 → 소요
    docs/paper/README.md         읽기 경로 ④ «논문 쓰는 사람» — 조각 목차
    docs/paper/02_target.md      옛 report02 의 논문 방법 문단(아무도 안 옮긴 조각)

⭐ 재현 정보의 정본은 **노트북의 여는 블록**이다(`header(repro=…)` 가 찍은 그 표).
   샤드가 아니라 노트북을 읽는 이유는 하나다 — 샤드는 빌더마다 담는 것이 다르지만
   여는 블록은 `report_style.header()` 가 강제하므로 78편 전부에 같은 모양으로 있다.

실행
    cd /home/yunjung/workspace/sionna2
    PYTHONPATH=src ~/.venvs/py312/bin/python src/make_reports_index.py

⚠ 근거 JSON(`outputs/*.json`)은 한 줄도 고치지 않는다. GPU 도 쓰지 않는다.
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

from report_registry import PARTS, REPORTS, REPORT_DIR                   # noqa: E402

OUT_INDEX = os.path.join(ROOT, "outputs", "reports_index.json")
OUT_REPRO = os.path.join(ROOT, "docs", "REPRODUCE.md")
OUT_PAPER = os.path.join(ROOT, "docs", "paper", "README.md")
OUT_P02 = os.path.join(ROOT, "docs", "paper", "02_target.md")

_BASH = re.compile(r"###\s*재현\s*\n+```bash\n(.*?)```", re.S)
_ROW = re.compile(r"^\|\s*(출력|소요|비고)\s*\|\s*(.*?)\s*\|\s*$", re.M)
_IMG = re.compile(r"!\[[^\]]*\]\(\s*([^)\s]+?)[^)]*\)")
_BACKTICK = re.compile(r"`([^`]+)`")
_FOOT_ROW = re.compile(r"^\|\s*\[\^\d+\]\s*\|\s*`([^`]+)`\s*\|", re.M)


def _text(c: dict) -> str:
    s = c.get("source", "")
    return s if isinstance(s, str) else "".join(s)


def scan(anchor: str, rec: dict) -> dict | None:
    """노트북 하나를 읽어 색인 한 줄을 만든다."""
    p = os.path.join(REPORT_DIR, rec["file"])
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        cells = json.load(f).get("cells", [])

    head = "\n".join(_text(c) for c in cells
                     if "header" in (c.get("metadata", {}).get("tags") or []))
    m = _BASH.search(head)
    cmd = [ln for ln in (m.group(1).splitlines() if m else []) if ln.strip()]
    meta = dict(_ROW.findall(head))
    out = _BACKTICK.findall(meta.get("출력", ""))

    figs, cites = [], []
    for c in cells:
        if c.get("cell_type") != "markdown":
            continue
        t = _text(c)
        if "sources" in (c.get("metadata", {}).get("tags") or []):
            cites += _FOOT_ROW.findall(t)
        else:
            figs += [os.path.normpath(os.path.join("reports", s)) for s in _IMG.findall(t)]

    return dict(no=rec["no"], anchor=anchor, part=rec["part"],
                part_name=PARTS.get(rec["part"], {}).get("name", ""),
                title=rec["title"], file=f"reports/{rec['file']}",
                md_cells=sum(1 for c in cells if c["cell_type"] == "markdown"),
                figures=sorted(set(figs)),
                evidence=sorted(set(cites)) or sorted(set(out)),
                repro=dict(cmd=cmd, out=out,
                           runtime=meta.get("소요", ""), note=meta.get("비고", "")))


def build_index() -> list[dict]:
    rows = [r for a, rec in REPORTS.items() if (r := scan(a, rec))]
    rows.sort(key=lambda r: r["no"])
    with open(OUT_INDEX, "w", encoding="utf-8") as f:
        json.dump(dict(
            _meta=dict(generator="src/make_reports_index.py",
                       what="편마다 근거 JSON · 그림 · 재현 명령. 정본은 각 편의 여는 블록이다.",
                       n_reports=len(rows), n_parts=len(PARTS)),
            parts=[dict(part=k, **v) for k, v in sorted(PARTS.items())],
            reports=rows), f, ensure_ascii=False, indent=1)
    return rows


def write_reproduce(rows: list[dict]) -> None:
    L = ["<!-- 생성물 — `src/make_reports_index.py` 가 각 편의 여는 블록에서 읽어 쓴다. -->",
         "", "# 다시 돌리기 — 편 → 명령 → 출력 → 소요", "",
         "읽기 경로 ③ 이다. **리포트를 읽지 않는다** — 어느 숫자를 재생산하려는지만 알면 된다.",
         "그 숫자가 사는 편을 아래 표에서 찾아 명령을 그대로 돌린다.", "",
         "```bash", "cd /home/yunjung/workspace/sionna2",
         "PY=~/.venvs/py312/bin/python", "```", "",
         "노트북만 다시 조립하려면(계산 없음 · 수 초):", "",
         "```bash",
         "for f in src/build_part*.py; do PYTHONPATH=src $PY \"$f\"; done",
         "PYTHONPATH=src $PY src/make_reports_index.py     # 색인·이 문서·논문 목차",
         "PYTHONPATH=src $PY src/make_readme.py            # README",
         "PYTHONPATH=src $PY benchmark/check_report_links.py   # 편 사이 참조 검사",
         "```", "",
         "기계용 사본은 [`outputs/reports_index.json`](../outputs/reports_index.json) 이다.",
         "부 단위 재현 메모는 [`docs/repro/`](repro/) 에 있다.", "", "---", ""]

    for k, part in sorted(PARTS.items()):
        sub = [r for r in rows if r["part"] == k]
        if not sub:
            continue
        L += [f"## 부 {k} — {part['name']}", ""]
        L += ["| 편 | 명령 | 출력 | 소요 |", "|---|---|---|---|"]
        for r in sub:
            cmd = "<br>".join(f"`{c.strip()}`" for c in r["repro"]["cmd"]) or "—"
            out = "<br>".join(f"`{o}`" for o in r["repro"]["out"]) or "—"
            L.append(f"| [{r['no']}]({os.path.relpath(os.path.join(ROOT, r['file']), os.path.dirname(OUT_REPRO))}) "
                     f"{r['anchor']} | {cmd} | {out} | {r['repro']['runtime'] or '—'} |")
        L.append("")

    with open(OUT_REPRO, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")


def write_paper_toc(rows: list[dict]) -> None:
    d = os.path.dirname(OUT_PAPER)
    have = sorted(f for f in os.listdir(d) if f.endswith(".md") and f != "README.md")
    known = {
        "00_novelty.md": ("무엇이 새로운가", "부 2 — 옛 report01 §0", 2),
        "01_prior.md": ("선행연구 문단", "부 2 — 옛 report01 §9", 2),
        "02_target.md": ("표적 모델 방법 문단", "부 3·4·5 — 옛 report02 methods", 4),
        "03_illuminators.md": ("조명원 방법 문단 + 그림 캡션", "부 8 — 옛 report03", 8),
        "04_detector.md": ("검출기 방법 문단 + 그림 캡션", "부 9 — 옛 report04", 9),
        "05_results.md": ("결과 방법 문단", "부 10 — 옛 report05", 10),
        "06_measurement.md": ("실측 설계 방법 문단 + 방어선", "부 11 — 옛 report06", 11),
        "figs_part10.md": ("부 10 그림의 완결 문장 캡션", "부 10", 10),
        "figs_part11.md": ("부 11 그림의 완결 문장 캡션", "부 11", 11),
    }
    L = ["<!-- 생성물 — `src/make_reports_index.py` 가 쓴다. 조각 본문은 각 부 빌더가 쓴다. -->",
         "", "# 논문 조각 — 목차", "",
         "읽기 경로 ④ 다. **리포트 본문에는 논문 문장이 없다** — 사용자 지시로 논문·재현 서술은",
         "리포트에서 빼고 여기 모았다. 조각마다 «어느 편에서 왔나» 가 붙어 있다.", "",
         "| 조각 | 무엇 | 어디서 왔나 |", "|---|---|---|"]
    for fn in have:
        what, where, _ = known.get(fn, ("—", "—", -1))
        L.append(f"| [`{fn}`]({fn}) | {what} | {where} |")
    L += ["", "## 규약", "",
          "- **그림 캡션이 두 벌이다.** 리포트 본문은 그림마다 **질문 한 줄**을 달고(하우스 규약),",
          "  논문에 그대로 붙일 **완결 문장 캡션**은 본문에서 빠진다. 부 8·9·11 은 그 캡션이",
          "  자기 방법 문단 문서 안에 있고, 부 10·11 은 `figs_part1N.md` 로 따로 서 있다.",
          "- **숫자는 여기서 손으로 고치지 않는다.** 조각은 생성물이고, 값을 바꾸려면 그 편의",
          "  빌더(`src/build_part*.py`)를 고치고 다시 돌린다.",
          "- 편 ↔ 조각 대응은 [`../REPRODUCE.md`](../REPRODUCE.md) 와",
          "  [`../../outputs/reports_index.json`](../../outputs/reports_index.json) 에 있다.", ""]
    with open(OUT_PAPER, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")


def write_paper_02() -> bool:
    """옛 `report02_target.ipynb` 의 논문 방법 문단을 옮긴다 — 아무 갈래도 안 가져간 조각이다."""
    src = os.path.join(ROOT, "report02_target.ipynb")
    if not os.path.exists(src) or os.path.exists(OUT_P02):
        return False
    with open(src, encoding="utf-8") as f:
        cells = json.load(f).get("cells", [])
    body = None
    for c in cells:
        t = _text(c)
        m = re.match(r"<!--pk:methods\s+(\{.*?\})-->", t, re.S)
        if m:
            body = json.loads(m.group(1))
            break
    if body is None:
        return False
    L = ["<!-- 생성물 — `src/make_reports_index.py:write_paper_02()` 가 옛 노트북에서 옮긴다. -->",
         "<!-- from: 옛 report02_target.ipynb c25 (pk:methods) -->", "",
         "# 논문 조각 — 표적 모델(방법 문단)", "",
         "옛 02편이 부 3 「표적 메쉬」 · 부 4 「산란 커널」 · 부 5 「앵커와 검증」 셋으로 갈렸다.",
         "이 문단은 그 셋을 한 문단으로 쓰는 논문용 서술이다.", "",
         "| 무엇을 대는가 | 어느 부 |", "|---|---|",
         "| 메쉬를 무엇에서 지었나 | 부 3 (편 15~17) |",
         "| 광선 가림 + PO 면적분 · 기준해 대조 | 부 4 (편 18~23) |",
         "| σ 를 측정에 맞추는 축과 그 검증 | 부 5 (편 24~29) |", "",
         "---", "", "## Methods", "", body.get("text", "").strip(), ""]
    with open(OUT_P02, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    return True


def main() -> int:
    rows = build_index()
    write_reproduce(rows)
    made = write_paper_02()
    write_paper_toc(rows)
    n_cmd = sum(1 for r in rows if r["repro"]["cmd"])
    print(f"✅ {os.path.relpath(OUT_INDEX, ROOT)} — 편 {len(rows)}개 · 부 {len(PARTS)}개")
    print(f"✅ {os.path.relpath(OUT_REPRO, ROOT)} — 재현 명령이 붙은 편 {n_cmd}/{len(rows)}")
    print(f"✅ {os.path.relpath(OUT_PAPER, ROOT)}"
          + (f" · 새로 옮긴 조각 {os.path.relpath(OUT_P02, ROOT)}" if made else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
