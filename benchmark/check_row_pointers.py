# -*- coding: utf-8 -*-
"""
check_row_pointers.py — 각주의 «rows[N]» 이 아직 그 팔·그 앙각을 가리키나.

왜 필요한가
    각주는 「원장 | rows[52].level_db → sionna/el+0 | −59.65」 꼴로 적힌다.
    **행 번호와 «무엇인지» 를 함께** 적어 두므로 서로 대조할 수 있다.

    ⛔원장은 병합으로 자란다. 새 팔이 앞에 끼면 행이 통째로 밀린다. 그러면 각주의
      숫자는 그대로인데 **가리키는 자리가 다른 팔**이 된다 — 아무 오류도 안 나고,
      빌더도 안 죽고, 검산하려고 따라간 사람만 엉뚱한 행에 도착한다.

    2026-09-03 에 실제로 78 건이 이렇게 밀려 있었다. 값은 전부 옳았고 포인터만 틀렸다.
    조각을 다시 구우니 24 개 각주가 rows[52] → rows[424] 처럼 옮겨 붙으면서 다 나았다.
    ⇒ 고치는 법은 언제나 «해당 조각 빌더를 다시 돌린다» 이다. 손으로 번호를 고치지 마라.

쓰는 법
    CUDA_VISIBLE_DEVICES="" PYTHONPATH=src ~/.venvs/py312/bin/python \
        benchmark/check_row_pointers.py            # 어긋나면 종료코드 1
    --quiet 를 주면 어긋난 것만 찍는다.
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

#: 각주 한 줄: | [^N] | `outputs/….json` | `rows[i].필드 → 팔/el±NN` | 값 |
CITE = re.compile(
    r"\|\s*\[\^(\d+)\]\s*\|\s*`(outputs/[^`]+\.json)`\s*\|\s*"
    r"`rows\[(\d+)\]\.([^`→]+?)\s*→\s*([^`]+?)`\s*\|")
#: «팔/el±NN» 에서 팔 토막과 앙각을 가른다.
WANT = re.compile(r"(.*?)/el([+-]?[\d.]+)")

_LED: dict[str, list | None] = {}


def rows_of(rel: str):
    """원장의 rows 배열. 없거나 못 읽으면 None — 그런 각주는 판정하지 않는다."""
    if rel not in _LED:
        try:
            _LED[rel] = json.load(open(os.path.join(ROOT, rel), encoding="utf-8")).get("rows")
        except Exception:
            _LED[rel] = None
    return _LED[rel]


def md_of(path: str) -> str:
    """노트북의 마크다운을 한 덩이로."""
    nb = json.load(open(path, encoding="utf-8"))
    out = []
    for c in nb["cells"]:
        if c["cell_type"] != "markdown":
            continue
        s = c["source"]
        out.append("".join(s) if isinstance(s, list) else s)
    return "\n".join(out)


def main() -> int:
    quiet = "--quiet" in sys.argv
    books = (sorted(glob.glob(os.path.join(ROOT, "reports", "*.ipynb")))
             + sorted(glob.glob(os.path.join(ROOT, "reports", "_parts", "*.ipynb"))))

    ok, undecidable, bad = 0, 0, []
    for p in books:
        try:
            src = md_of(p)
        except Exception:
            continue
        for fn, led, n, _fld, want in CITE.findall(src):
            rows = rows_of(led)
            m = WANT.match(want.strip())
            if rows is None or not m:
                undecidable += 1                      # 원장이 없거나 «팔/el» 꼴이 아니다
                continue
            i = int(n)
            if i >= len(rows):
                bad.append((p, fn, i, want, f"범위 밖 — 원장은 {len(rows)} 행"))
                continue
            r = rows[i]
            arm, el = m.group(1).strip(), float(m.group(2))
            eng = str(r.get("engine", ""))
            got = r.get("el_deg")
            # 팔 이름은 접두 일치를 허용한다 — 각주는 짧은 별칭을 쓴다(«sionna» ↔ «sionna_p4e9_…»)
            if (arm == eng or eng.startswith(arm + "_") or arm in eng) \
                    and got is not None and abs(float(got) - el) < 1e-6:
                ok += 1
            else:
                bad.append((p, fn, i, want,
                            f"실제 {eng} / el{float(got):+g}" if got is not None
                            else f"실제 {eng}"))

    print(f"═══ 각주 행 포인터 — 맞음 {ok} · ⛔어긋남 {len(bad)} · 판정 불가 {undecidable} ═══")
    if bad:
        byfile: dict[str, list] = {}
        for p, fn, i, want, why in bad:
            byfile.setdefault(os.path.relpath(p, ROOT), []).append((fn, i, want, why))
        for f, v in sorted(byfile.items()):
            print(f"\n  ⛔{f}  ({len(v)} 건)")
            for fn, i, want, why in v[:5]:
                print(f"      [^{fn}] rows[{i}] 라고 적혀 있으나 — 적힌 것 «{want}» · {why}")
            if len(v) > 5:
                print(f"      … 외 {len(v) - 5} 건")
        print("\n  ⭐고치는 법: 손으로 번호를 고치지 마라. 그 조각의 빌더"
              "(src/build_part*.py)를 다시 돌리고 src/build_volumes.py 로 권을 다시 짠다.")
        return 1
    if not quiet:
        print("  ✅ 각주가 전부 제 행을 가리킨다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
