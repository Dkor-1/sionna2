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
    ref_part(4)                 → [부 4 «산란 커널»](README.md#부-4-산란-커널)
    ref_paper("02_target")      → [docs/paper/02_target.md](../docs/paper/02_target.md)

⭐ 없는 앵커를 부르면 `ContractError` 로 빌드가 멈춘다. 끊긴 링크는 조용히 실패하고,
   고치는 값은 사전 한 줄이며, 안 잡으면 77편에 흩어져 남는다.

⚠ 링크 경로는 `reports/` 안에서의 **상대경로**다 — 새 편은 전부 `reports/NN_<anchor>.ipynb`
   에 산다.
"""
from __future__ import annotations

import json
import os
from typing import Any

from report_style import ContractError

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))

PLAN = os.path.join(ROOT, "outputs", "restruct_exec_plan.json")

#: 편이 사는 곳. 링크는 이 디렉터리 안에서의 상대경로다.
REPORT_DIR = os.path.join(ROOT, "reports")

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


def _load() -> tuple[dict[str, dict], dict[int, dict]]:
    with open(PLAN, encoding="utf-8") as f:
        plan = json.load(f)
    reports: dict[str, dict] = {}
    for r in plan["reports"]:
        a = r["anchor"]
        reports[a] = dict(
            no=str(r["no"]),
            part=int(r["part"]),
            title=r["title_ko"],
            short=_short(r["title_ko"]),
            file=f"{r['no']}_{a}.ipynb",
            evidence=list(r.get("evidence_json") or []),
            from_cells=list(r.get("from_cells") or []),
            planned=True,          # 실제로 지어지면 built_anchors() 가 False 로 읽는다
        )
    parts = {int(p["part"]): dict(name=p["name"], question=p["question"],
                                 reports=list(p["reports"]))
             for p in plan["parts"]}
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
    return f"[부 {int(n)} «{p['name']}»](README.md#{slug})"


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
