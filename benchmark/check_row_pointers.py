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
    CUDA_VISIBLE_DEVICES="" PYTHONPATH=src /workspace/.venvs/py312/bin/python \
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

#: 각주 한 줄: | [^N] | `outputs/….json` | `rows[<자리>].필드 → 팔/el±NN` | 값 |
#:   <자리> 는 두 꼴이다 — 옛 꼴 `rows[132]`(배열 위치) · 새 꼴
#:   `rows[engine=…,el_deg=-15]`(조건). ⭐새 꼴이 기본이다.
CITE = re.compile(
    r"\|\s*\[\^(\d+)\]\s*\|\s*`(outputs/[^`]+\.json)`\s*\|\s*"
    r"`rows\[([^\]]+)\]\.([^`→]+?)\s*→\s*([^`]+?)`\s*\|")
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
            #: ⭐⭐**조건 인용**이면 원장에서 직접 골라 본다(2026-09-12).
            #  ⛔배열 위치는 병합마다 밀린다 — 조각·권을 다시 구워 80 곳을 고친 지
            #    몇 분 만에 큐가 25 행을 더해 18 곳이 또 어긋났다. 다시 굽는 것은
            #    해결이 아니라 쳇바퀴라, 빌더가 자리 대신 조건을 찍게 바꿨다.
            #  여기서는 **조건이 행 하나를 고르는지**만 본다. 못 고르면 어긋남이다.
            if "=" in n:
                want_kv = []
                for part in n.split(","):
                    k, _, v = part.partition("=")
                    want_kv.append((k.strip(), v.strip()))

                def _same(a, b):
                    try:
                        return abs(float(a) - float(b)) < 1e-9
                    except (TypeError, ValueError):
                        return str(a) == str(b)

                hits = [x for x in rows
                        if all(k in x and _same(x[k], v) for k, v in want_kv)]
                if len(hits) != 1:
                    bad.append((p, fn, n, want, f"조건이 행 {len(hits)} 개를 고른다"))
                    continue
                r = hits[0]
            else:
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
                bad.append((p, fn, n, want,
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
        print("  ⭐아직 `rows[132]` 처럼 **자리**로 적힌 각주가 남아 있으면 그 빌더를 "
              "`rows[engine=…,el_deg=…]` 꼴로 고친다 — 자리는 병합마다 밀린다.")
        return 1
    if not quiet:
        print("  ✅ 각주가 전부 제 행을 가리킨다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
