# -*- coding: utf-8 -*-
"""
extract_part_docs.py — 부 6·7·11 의 **논문 조각**과 **재현 절차**를 리포트 밖으로 옮긴다
==========================================================================================
사용자 지시: *"논문 작성 측면, 재현 관련은 아예 별도로 각각 따로 메모를 하고 레포트에 쓸
필요는 없을 것 같아"*. 그래서 두 종류를 리포트에서 빼되 **지우지 않는다**.

만드는 것
    docs/paper/06_measurement.md      ← report06_measurement.ipynb 셀 23 (논문 부록) 통째로
    docs/repro/part06_ladder.md       ← reports/30~33 의 재현 블록
    docs/repro/part07_microdoppler.md ← reports/34~43 의 재현 블록
    docs/repro/part11_measurement.md  ← reports/67~77 의 재현 블록 + 옛 셀 24 코드

⚠ 읽기만 한다. 옛 노트북·옛 빌더·근거 JSON 을 한 줄도 고치지 않는다.
⚠ `docs/REPRODUCE.md` 전체 병합은 다른 단계가 한다 — 여기서는 이 묶음의 조각만 낸다.

실행
    cd /home/yunjung/workspace/sionna2
    ~/.venvs/py312/bin/python src/extract_part_docs.py
"""
from __future__ import annotations

import json
import os
import re

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
RPT = os.path.join(_ROOT, "reports")

PARTS = {
    "part06_ladder": ("부 6 · 표적 사다리", [
        ("30", "ladder-three"), ("31", "ladder-calibrated"),
        ("32", "ladder-answer"), ("33", "ladder-premature")]),
    "part07_microdoppler": ("부 7 · 마이크로도플러", [
        ("34", "md-paths-doppler"), ("35", "md-slowtime"), ("36", "md-two-engines"),
        ("37", "md-rpm"), ("38", "md-occlusion"), ("39", "md-blade-vs-body"),
        ("40", "md-attitude"), ("41", "md-calibration"), ("42", "md-ray-budget"),
        ("43", "md-prf")]),
    "part11_measurement": ("부 11 · 실측 설계", [
        ("67", "hardware"), ("68", "sigma-checklist"), ("69", "site-geometry"),
        ("70", "calibration-sphere"), ("71", "subband"), ("72", "attitude"),
        ("73", "three-layers"), ("74", "sim-vs-meas"), ("75", "decision-matrix"),
        ("76", "session-drift"), ("77", "size-law-differential")]),
}

_H1 = re.compile(r"^#\s*리포트\s*(\S+)\s*—\s*(.+)$", re.M)
_BASH = re.compile(r"```bash\n(.*?)```", re.S)
_OUT = re.compile(r"^\|\s*출력\s*\|\s*(.+?)\s*\|$", re.M)
_TIME = re.compile(r"^\|\s*소요\s*\|\s*(.+?)\s*\|$", re.M)


def _cells(path: str) -> list[str]:
    with open(path, encoding="utf-8") as f:
        nb = json.load(f)
    return ["".join(c.get("source", [])) for c in nb["cells"]]


def _repro_row(no: str, anchor: str) -> dict:
    src = _cells(os.path.join(RPT, f"{no}_{anchor}.ipynb"))
    head = "\n".join(src[:2])
    title = _H1.search(head)
    cmds = _BASH.search(head)
    outs = _OUT.search(head)
    secs = _TIME.search(head)
    return dict(no=no, anchor=anchor,
                title=title.group(2).strip() if title else "",
                cmds=[c for c in (cmds.group(1).strip().splitlines() if cmds else []) if c],
                out=outs.group(1).strip() if outs else "",
                runtime=secs.group(1).strip() if secs else "")


def _ladder_provenance() -> list[str]:
    """부 6 의 입력 지문 표 — 옛 `docs/TARGET_LADDER.md` 마지막 절이 담고 있던 것.

    리포트 본문에는 안 싣는다(재현 자료다). 값은 산출물에서 직접 읽는다.
    """
    p = os.path.join(_ROOT, "outputs", "report16_synthesis.json")
    with open(p, encoding="utf-8") as f:
        syn = json.load(f)
    L = ["", "## 입력 지문 (sha256 앞 12자리)", "",
         "*출처 `outputs/report16_synthesis.json : meta.provenance`. 사다리 여섯 단이 "
         "서로 다른 파일에서 오므로, 어느 판을 이어 붙였는지가 여기서 확인된다.*", "",
         "| 입력 | sha256 (앞 12) |", "|---|---|"]
    for _k, v in syn["meta"]["provenance"].items():
        rel = os.path.relpath(v["path"], _ROOT)
        L.append(f"| `{rel}` | `{v['sha256'][:12]}` |")
    gates = syn.get("gates", {})
    verdicts = " · ".join(f"{k.split('_')[0]} {v.get('verdict')}" for k, v in gates.items())
    L += ["", f"게이트: {verdicts}"]
    return L


def write_repro(slug: str) -> str:
    name, items = PARTS[slug]
    rows = [_repro_row(no, a) for no, a in items]
    L = [f"# 재현 — {name}", "",
         "*생성: `src/extract_part_docs.py`. 이 표의 명령·출력·소요는 각 편의 여는 블록에서 "
         "기계적으로 뽑은 것이라 리포트와 어긋날 수 없다.*", "",
         "| 편 | 앵커 | 무엇을 만드나 | 출력 | 소요 |",
         "|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['no']} | `{r['anchor']}` | {r['title']} | {r['out']} | {r['runtime']} |")
    L += ["", "## 명령", ""]
    seen: set[str] = set()
    for r in rows:
        fresh = [c for c in r["cmds"] if c not in seen]
        if not fresh:
            continue
        seen.update(fresh)
        L += [f"### 편 {r['no']} `{r['anchor']}`", "", "```bash", *fresh, "```", ""]
    if slug == "part06_ladder":
        L += _ladder_provenance()
    body = "\n".join(L).rstrip() + "\n"
    path = os.path.join(_ROOT, "docs", "repro", f"{slug}.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    return path


def write_paper_06() -> str:
    """옛 report06 셀 23(논문 부록: 방법 문단 · 방어선 · 인용)을 통째로 옮긴다."""
    src = _cells(os.path.join(_ROOT, "report06_measurement.ipynb"))
    block = next((s for s in src if s.lstrip().startswith("<!--pk:methods")), None)
    if block is None:
        raise SystemExit("report06_measurement.ipynb 에서 논문 부록 셀을 못 찾았다")
    code = next((s for s in src if s.lstrip().startswith("# 이 편의 숫자를 직접 열어보기")), "")
    head = ["<!-- from: 부 11 실측 설계 (편 67~77) -->",
            "<!-- source: report06_measurement.ipynb 셀 23 · 생성기 src/extract_part_docs.py -->",
            "# 논문 조각 — VI. Validation (실측 설계)", "",
            "*이 문서는 리포트 밖에 산다. 옛 리포트 06 의 논문 부록(방법 문단 · 방어선 8행 · "
            "인용 3편)을 그대로 옮긴 것이고, 편 67~77 이 그 근거를 나눠 싣는다.*", "",
            "| 주장 | 그 주장을 세우는 편 |",
            "|---|---|",
            "| 캠페인이 검출 사슬과 파형 순위를 결판낸다 | 편 74 `sim-vs-meas` |",
            "| 세션 드리프트 예산이 뒤집힘 폭 아래에 있다 | 편 74 `sim-vs-meas` |",
            "| 교정구가 절대 레벨의 첫 측정 앵커를 세운다 | 편 70 `calibration-sphere` |",
            "| 세 밴드를 한 세션에서 재어 기울기를 판정한다 | 편 76 `session-drift` |",
            "| 원거리장 거리를 세 D 정의로 함께 싣는다 | 편 69 `site-geometry` |",
            "| 두 기체로 크기전이 법칙을 부호 하나로 고른다 | 편 77 `size-law-differential` |",
            "| Pfa 교정은 통제 몬테카를로가 세운다 | 편 75 `decision-matrix` |",
            "| 12-bit ADC 가 직접파 제거의 천장이다 | 편 67 `hardware` |", "",
            "---", ""]
    body = "\n".join(head) + block.rstrip() + "\n"
    if code:
        body += ("\n\n---\n\n## 숫자를 직접 열어보기 (옛 리포트 06 셀 24)\n\n"
                 "```python\n" + code.rstrip() + "\n```\n")
    path = os.path.join(_ROOT, "docs", "paper", "06_measurement.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    return path


def main() -> None:
    print("── 부 6·7·11 논문·재현 조각 추출 ──")
    for slug in PARTS:
        print("  ✅", os.path.relpath(write_repro(slug), _ROOT))
    print("  ✅", os.path.relpath(write_paper_06(), _ROOT))


if __name__ == "__main__":
    main()
