# -*- coding: utf-8 -*-
"""
check_report_links.py — 편 사이 참조를 전수 검사한다
==========================================================================================
재구성으로 리포트가 8편 → 78편이 되면서 편 사이 링크가 수백 개 생겼다. 끊긴 링크는
**조용히 실패한다** — 읽는 사람만 막히고 빌드는 통과한다. 그래서 따로 센다.

무엇을 세나 (⛔ = 위반, ⚠ = 권고)

  ⛔ dead-link      `](…)` 가 가리키는 파일이 디스크에 없다
  ⛔ dead-image     `![](…)` 의 PNG 가 없다
  ⛔ bad-anchor     `report_registry` 가 모르는 앵커를 가리킨다
  ⛔ bad-provenance 출처 태그(또는 각주)의 파일·키가 안 열린다
  ⛔ title-mismatch 노트북 H1 과 레지스트리 제목이 다르다 — `ref()` 링크가 딴 말을 한다
  ⚠ not-built      계획에 있는데 아직 안 지어진 편을 가리킨다
  ⚠ old-report-ref 폐지된 옛 편 번호(`05편`, `report02_target.ipynb`)를 가리킨다
  ⚠ old-section    폐지된 옛 절 번호(`§4.6`)를 본문에서 가리킨다
                   (근거 JSON 이 데이터로 들고 있는 것은 세지 않는다 — 그건 못 고친다)
  ⚠ orphan         아무 편도 가리키지 않는 편(지도 편과 각 부 첫 편은 뺀다)

쓰는 법
    PYTHONPATH=src python benchmark/check_report_links.py            # 요약 + 위반 목록
    PYTHONPATH=src python benchmark/check_report_links.py --all      # 권고까지 전부
    PYTHONPATH=src python benchmark/check_report_links.py --json     # 기계용

종료 코드 = 위반(⛔) 개수. 권고는 종료 코드에 안 들어간다.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (os.path.join(ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import report_style as RS                                             # noqa: E402
from report_registry import PARTS, REPORTS                            # noqa: E402

REPORT_DIR = os.path.join(ROOT, "reports")

#: 마크다운 링크 — 이미지(`![…]`)는 뺀다.
_LINK = re.compile(r"(?<!\!)\[([^\]]*)\]\(\s*([^)\s]+?)\s*\)")
_IMG = re.compile(r"!\[[^\]]*\]\(\s*([^)\s]+?)[^)]*\)")
_H1 = re.compile(r"^#\s+(.+?)\s*$", re.M)
#: 편 머리는 «편 NN — 제목» 이다. 제목만 떼어낸다.
_H1_TITLE = re.compile(r"^(?:리포트|편)?\s*\d{2}\s*[—–-]\s*(.*)$")
#: 옛 편 번호 참조 — `05편 §3`, `report02_target.ipynb`
_OLD_NUM = re.compile(r"(?<![\d])(0[0-7])\s*편(?![가-힣])")
_OLD_FILE = re.compile(r"report0[0-7][_a-z]*\.ipynb")
#: 옛 절 번호 — `§4.6`, `§2-2`
_OLD_SEC = re.compile(r"§\s*\d+(?:[.\-]\d+[a-z]?)*")
#: 출처 표시 — 옛 태그와 각주 표의 행 둘 다에서 (파일, 키) 를 얻는다.
_PROV = re.compile(r"⟨\s*([^⟩:]+?\.(?:json|npz))\s*:\s*([^⟩]+?)\s*⟩")
_FOOT_ROW = re.compile(r"^\|\s*\[\^\d+\]\s*\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|", re.M)


def _cells(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f).get("cells", [])


def _text(c: dict) -> str:
    s = c.get("source", "")
    return s if isinstance(s, str) else "".join(s)


def _tags(c: dict) -> list[str]:
    return c.get("metadata", {}).get("tags") or []


def _rel(p: str) -> str:
    return os.path.relpath(p, ROOT)


def check() -> dict:
    bad: list[dict] = []
    warn: list[dict] = []
    incoming: dict[str, int] = {}
    by_file: dict[str, str] = {r["file"]: a for a, r in REPORTS.items()}
    nb_files = sorted(f for f in os.listdir(REPORT_DIR) if f.endswith(".ipynb"))

    # 계획에 있는데 안 지어진 편
    missing = [a for a, r in REPORTS.items()
               if not os.path.exists(os.path.join(REPORT_DIR, r["file"]))]

    n_links = n_imgs = n_prov = 0
    for fn in nb_files:
        p = os.path.join(REPORT_DIR, fn)
        cells = _cells(p)
        anchor = by_file.get(fn, fn)

        # ── H1 ↔ 레지스트리 제목 ────────────────────────────────────────────
        reg = REPORTS.get(anchor)
        if reg and cells:
            m = _H1.search(_text(cells[0]))
            if m:
                t = m.group(1).strip()
                mt = _H1_TITLE.match(t)
                if mt:
                    t = mt.group(1).strip()
                if t and t != reg["title"].strip():
                    bad.append(dict(kind="title-mismatch", where=f"reports/{fn}",
                                    detail=f"노트북 «{t}» ↔ 레지스트리 «{reg['title']}»"))

        for i, c in enumerate(cells):
            if c.get("cell_type") != "markdown":
                continue
            t = _text(c)
            is_ledger = RS.TAG_SOURCES in _tags(c)

            # ── 링크 ──────────────────────────────────────────────────────
            for label, target in _LINK.findall(t):
                if target.startswith(("http", "mailto:", "#", "data:")):
                    continue
                n_links += 1
                tgt = target.split("#")[0]
                full = os.path.normpath(os.path.join(REPORT_DIR, tgt))
                if tgt.endswith(".ipynb") and os.path.basename(tgt) in by_file:
                    a = by_file[os.path.basename(tgt)]
                    incoming[a] = incoming.get(a, 0) + 1
                if os.path.exists(full):
                    continue
                if tgt.endswith(".ipynb") and os.path.basename(tgt) in by_file:
                    warn.append(dict(kind="not-built", where=f"reports/{fn}:c{i}",
                                     detail=f"아직 안 지어진 편 — {tgt} «{label}»"))
                else:
                    bad.append(dict(kind="dead-link", where=f"reports/{fn}:c{i}",
                                    detail=f"{tgt} «{label}»"))

            # ── 그림 ──────────────────────────────────────────────────────
            for src in _IMG.findall(t):
                if src.startswith(("http", "data:")):
                    continue
                n_imgs += 1
                if not os.path.exists(os.path.normpath(os.path.join(REPORT_DIR, src))):
                    bad.append(dict(kind="dead-image", where=f"reports/{fn}:c{i}",
                                    detail=src))

            # ── 출처 ──────────────────────────────────────────────────────
            pairs = (_FOOT_ROW.findall(t) if is_ledger else _PROV.findall(t))
            for jf, key in pairs:
                n_prov += 1
                try:
                    RS._resolve_cite(jf, key)
                except Exception as e:                       # noqa: BLE001
                    bad.append(dict(kind="bad-provenance", where=f"reports/{fn}:c{i}",
                                    detail=f"⟨{jf} : {key}⟩ — "
                                           f"{str(e).splitlines()[0]}"))

            if is_ledger:
                continue          # 각주 원장은 «옛 번호» 검사 대상이 아니다(키 문자열이다)

            # ── 폐지된 옛 번호 ─────────────────────────────────────────────
            prose = re.sub(r"`[^`]*`", "", t)
            for m in _OLD_NUM.finditer(prose):
                warn.append(dict(kind="old-report-ref", where=f"reports/{fn}:c{i}",
                                 detail=f"옛 편 번호 «{m.group(0)}» — `ref(앵커)` 로 바꾼다"))
            for m in _OLD_FILE.finditer(t):
                warn.append(dict(kind="old-report-ref", where=f"reports/{fn}:c{i}",
                                 detail=f"옛 노트북 «{m.group(0)}»"))
            for m in _OLD_SEC.finditer(prose):
                warn.append(dict(kind="old-section", where=f"reports/{fn}:c{i}",
                                 detail=f"옛 절 번호 «{m.group(0)}»"))

    # ── README 의 링크 ──────────────────────────────────────────────────────
    readme = os.path.join(ROOT, "README.md")
    if os.path.exists(readme):
        with open(readme, encoding="utf-8") as f:
            rt = f.read()
        for label, target in _LINK.findall(rt):
            if target.startswith(("http", "mailto:", "#", "data:")):
                continue
            n_links += 1
            tgt = target.split("#")[0]
            if not os.path.exists(os.path.normpath(os.path.join(ROOT, tgt))):
                bad.append(dict(kind="dead-link", where="README.md",
                                detail=f"{tgt} «{label}»"))
            if tgt.startswith("reports/") and os.path.basename(tgt) in by_file:
                a = by_file[os.path.basename(tgt)]
                incoming[a] = incoming.get(a, 0) + 1

    # ── 아무도 안 가리키는 편 ────────────────────────────────────────────────
    first_of_part = {p["reports"][0] for p in PARTS.values() if p["reports"]}
    for a, r in REPORTS.items():
        if not os.path.exists(os.path.join(REPORT_DIR, r["file"])):
            continue
        if incoming.get(a, 0) == 0 and r["no"] not in first_of_part and r["no"] != "00":
            warn.append(dict(kind="orphan", where=f"reports/{r['file']}",
                             detail="아무 편도·README 도 이 편을 가리키지 않는다"))

    return dict(notebooks=len(nb_files), planned=len(REPORTS), missing=sorted(missing),
                n_links=n_links, n_images=n_imgs, n_provenance=n_prov,
                violations=bad, advisories=warn,
                ok=not bad)


def main() -> int:
    ap = argparse.ArgumentParser(description="편 사이 참조 전수 검사")
    ap.add_argument("--all", action="store_true", help="권고까지 전부 인쇄")
    ap.add_argument("--json", action="store_true", help="기계용 JSON")
    a = ap.parse_args()

    rep = check()
    if a.json:
        print(json.dumps(rep, ensure_ascii=False, indent=1))
        return len(rep["violations"])

    print(f"── 편 사이 참조 검사 ──")
    print(f"  노트북 {rep['notebooks']}개 / 계획 {rep['planned']}편"
          + (f"  ⚠ 안 지어진 편 {len(rep['missing'])}: {', '.join(rep['missing'])}"
             if rep["missing"] else "  (전부 지어졌다)"))
    print(f"  링크 {rep['n_links']}개 · 그림 {rep['n_images']}개 · "
          f"출처 {rep['n_provenance']}개")

    if rep["violations"]:
        print(f"\n⛔ 위반 {len(rep['violations'])}건")
        for v in rep["violations"]:
            print(f"   [{v['kind']}] {v['where']} — {v['detail']}")
    else:
        print("\n✅ 위반 0건 — 끊긴 링크·그림·출처가 없다")

    byk: dict[str, int] = {}
    for w in rep["advisories"]:
        byk[w["kind"]] = byk.get(w["kind"], 0) + 1
    if byk:
        print(f"\n⚠ 권고 {len(rep['advisories'])}건 — "
              + " · ".join(f"{k} {n}" for k, n in sorted(byk.items())))
        shown = rep["advisories"] if a.all else rep["advisories"][:12]
        for w in shown:
            print(f"   [{w['kind']}] {w['where']} — {w['detail']}")
        if not a.all and len(rep["advisories"]) > len(shown):
            print(f"   … 외 {len(rep['advisories']) - len(shown)}건 (`--all` 로 전부)")

    return len(rep["violations"])


if __name__ == "__main__":
    sys.exit(main())
