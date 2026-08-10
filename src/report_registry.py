# -*- coding: utf-8 -*-
"""
report_registry.py — 앵커(anchor) 사전과 편 사이 참조 문법
==========================================================================================
계획 `outputs/restruct_exec_plan.json` 이 **번호의 유일한 정본**이고, 이 모듈은 그것을
읽어 `REPORTS` 사전을 만든다. 손으로 적은 사본을 두지 않는 이유는 하나다 —
부 에이전트 여러 명이 동시에 편을 지으므로, 사본을 각자 들면 마지막에 쓴 사람만 남는다.

쓰는 법
    from report_registry import ref, ref_fig, ref_part, ref_paper

    ref("kernel-what")          → [편 18 «가림 판정은 …»](18_kernel-what.ipynb)
    ref("kernel-what", short=1) → [편 18 «커널이 하는 일»](18_kernel-what.ipynb)   ← 표 칸 안
    ref_fig("kernel-what", 2)   → 편 18 그림 2
    ref_part(4)                 → [부 4 «산란 커널»](../README.md#부-4-산란-커널)
    ref_paper("02_target")      → [docs/paper/02_target.md](../docs/paper/02_target.md)

⭐ 없는 앵커를 부르면 `ContractError` 로 빌드가 멈춘다. 끊긴 링크는 조용히 실패하고,
   고치는 값은 사전 한 줄이며, 안 잡으면 77편에 흩어져 남는다.

⚠ 링크 경로는 `reports/` 안에서의 **상대경로**다 — 새 편은 전부 `reports/NN_<anchor>.ipynb`
   에 산다.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

from report_style import ContractError

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))

PLAN = os.path.join(ROOT, "outputs", "restruct_exec_plan.json")

#: ⭐조각이 사는 곳(2026-08-10). 옛 78 편은 `reports/_parts/` 로 옮겨졌고 **사람이 직접 읽는
#  문서가 아니다** — 사람이 읽는 것은 `reports/` 의 15 권이다(`src/build_volumes.py`).
#  ⚠이 상수가 `reports/` 를 가리키던 동안 두 가지가 조용히 어긋나 있었다:
#    ① `nb_path()` 가 조각을 권 디렉터리에 쏟아, 조각 빌더를 돌리면 78 개가 권과 섞였다.
#    ② `_built_title()` 이 조각을 못 찾아 «지어진 편의 제목이 정본» 규약이 죽고,
#       계획 JSON 의 낡은 제목 9 건이 되살아나 있었다.
#  ⚠ 링크 주소는 안 바뀐다 — `ref()`·`ref_fig()`·`ref_part()` 는 basename 만 쓴다.
REPORT_DIR = os.path.join(ROOT, "reports", "_parts")

_CUT = ("—", " — ", ",", "，")


def _short(title: str, width: int = 26) -> str:
    """표 칸 안에 넣을 짧은 제목. 첫 절만 남기고, 그래도 길면 자른다."""
    t = str(title).strip()
    for c in ("—", ","):
        if c in t:
            t = t.split(c)[0].strip()
            break
    if len(t) > width:
        t = t[: width - 1].rstrip() + "…"
    return t


#: 편 머리 «# 리포트 18 — 제목» 에서 제목만.
_H1 = re.compile(r'"#\s+(?:리포트|편)?\s*(\d{2})\s*[—–-]\s*(.*?)\\n"')

#: 계획에 없는 편(부 담당이 «한 편 = 한 메시지» 를 지키려고 새로 쪼갠 편)이 사는 곳.
SHARDS = os.path.join(ROOT, "outputs", "reports_index")


def _built_title(fname: str) -> str | None:
    """지어진 노트북의 H1 제목. 없으면 None.

    ⭐ **지어진 편이 있으면 그 제목이 정본이다.** 계획 JSON 이 아니라 노트북이 정본인 이유는
       하나다 — `ref()` 가 만든 링크의 글자와 독자가 열어서 보는 제목이 어긋나면, 링크가
       조용히 거짓말을 한다. 계획의 `titles_needing_fix` 를 빌더가 반영한 편이 실제로 넷 있다.
    """
    p = os.path.join(REPORT_DIR, fname)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        head = f.read(4000)              # 첫 셀이면 충분하다 — 여는 블록이 맨 앞이다(§5.2)
    m = _H1.search(head)
    if not m:
        return None
    try:
        return json.loads(f'"{m.group(2)}"').strip() or None
    except json.JSONDecodeError:
        return None


def _load() -> tuple[dict[str, dict], dict[int, dict]]:
    with open(PLAN, encoding="utf-8") as f:
        plan = json.load(f)
    reports: dict[str, dict] = {}
    for r in plan["reports"]:
        a = r["anchor"]
        fname = f"{r['no']}_{a}.ipynb"
        title = _built_title(fname) or r["title_ko"]
        reports[a] = dict(
            no=str(r["no"]),
            part=int(r["part"]),
            title=title,
            short=_short(title),
            file=fname,
            evidence=list(r.get("evidence_json") or []),
            from_cells=list(r.get("from_cells") or []),
            planned=True,          # 실제로 지어지면 exists() 가 True 로 읽는다
        )

    # ── 계획 밖에서 새로 쪼갠 편을 샤드에서 주워 온다 ─────────────────────────
    #    ⚠ 계획 JSON 은 여러 갈래가 동시에 읽으므로 손대지 않는다. 대신 이미 지어진
    #      편의 샤드를 읽어 사전을 늘린다 — 그래야 `ref()` 가 그 편도 가리킬 수 있다.
    if os.path.isdir(SHARDS):
        for fn in sorted(os.listdir(SHARDS)):
            if not fn.endswith(".json"):
                continue
            a = fn[:-5]
            if a in reports:
                continue
            with open(os.path.join(SHARDS, fn), encoding="utf-8") as f:
                sh = json.load(f)
            fname = os.path.basename(sh.get("file") or "") or f"{sh.get('no', '??')}_{a}.ipynb"
            title = _built_title(fname) or sh.get("title") or a
            reports[a] = dict(no=str(sh.get("no", "??")), part=int(sh.get("part", -1)),
                              title=title, short=_short(title), file=fname,
                              evidence=list(sh.get("evidence") or []),
                              from_cells=list(sh.get("from_cells") or []),
                              planned=False)

    parts = {int(p["part"]): dict(name=p["name"], question=p["question"],
                                 reports=list(p["reports"]))
             for p in plan["parts"]}
    for a, r in reports.items():                 # 계획 밖 편을 자기 부의 목록 끝에 붙인다
        p = parts.get(r["part"])
        if p is not None and r["no"] not in p["reports"]:
            p["reports"].append(r["no"])
    return reports, parts


REPORTS, PARTS = _load()


def get(anchor: str) -> dict:
    try:
        return REPORTS[anchor]
    except KeyError:
        near = [a for a in REPORTS if anchor.split("-")[0] in a][:6]
        raise ContractError(
            f"모르는 앵커다 — {anchor!r}\n"
            f"  → `outputs/restruct_exec_plan.json:reports[].anchor` 에 있는 이름만 쓴다.\n"
            f"  비슷한 것: {', '.join(near) if near else '(없음)'}") from None


def exists(anchor: str) -> bool:
    """그 편의 노트북이 디스크에 이미 있는가(= planned 가 아닌가)."""
    r = REPORTS.get(anchor)
    return bool(r) and os.path.exists(os.path.join(REPORT_DIR, r["file"]))


def ref(anchor: str, short: bool = False) -> str:
    """편 하나를 가리키는 마크다운 링크. 제목이 곧 그 편의 결론 문장이다."""
    r = get(anchor)
    t = r["short"] if short else r["title"]
    return f"[편 {r['no']} «{t}»]({r['file']})"


def ref_fig(anchor: str, k: int) -> str:
    """다른 편의 그림. 그림 번호는 **편 안에서 1부터** 다시 센다."""
    r = get(anchor)
    return f"[편 {r['no']}]({r['file']}) 그림 {int(k)}"


def ref_part(n: int) -> str:
    p = PARTS.get(int(n))
    if p is None:
        raise ContractError(f"모르는 부다 — {n!r} (0~{max(PARTS)})")
    slug = f"부-{int(n)}-" + p["name"].replace(" ", "-")
    # ⚠ 편은 `reports/` 안에 살고 README 는 리포지토리 루트에 있다 — 한 칸 올라가야 한다.
    return f"[부 {int(n)} «{p['name']}»](../README.md#{slug})"


def ref_paper(doc: str) -> str:
    """논문 조각 문서. 리포트 본문에서 «그 문단은 여기로 갔다» 를 가리킬 때."""
    name = doc if doc.endswith(".md") else f"{doc}.md"
    return f"[docs/paper/{name}](../docs/paper/{name})"


def ref_doc(rel: str, label: str | None = None) -> str:
    """리포지토리 안의 다른 문서(`docs/…`)를 `reports/` 기준 상대경로로."""
    return f"[{label or rel}](../{rel})"


def nb_path(anchor: str) -> str:
    """이 편의 노트북 절대경로 — 빌더가 `build_notebook()` 에 넘긴다."""
    return os.path.join(REPORT_DIR, get(anchor)["file"])


def index_shard(anchor: str, **extra: Any) -> str:
    """`outputs/reports_index/<anchor>.json` 샤드를 쓴다(부 에이전트끼리 안 부딪친다)."""
    r = dict(get(anchor))
    r.pop("planned", None)
    r["anchor"] = anchor
    r.update(extra)
    d = os.path.join(ROOT, "outputs", "reports_index")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, f"{anchor}.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(r, f, ensure_ascii=False, indent=1)
    return p


if __name__ == "__main__":                       # pragma: no cover
    print(f"앵커 {len(REPORTS)}개 · 부 {len(PARTS)}개 · 지어진 편 "
          f"{sum(1 for a in REPORTS if exists(a))}개")
    for a, r in REPORTS.items():
        mark = "✅" if exists(a) else "· "
        print(f"  {mark} {r['no']}  {a:24s}  {r['title'][:52]}")
