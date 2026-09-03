# -*- coding: utf-8 -*-
"""
report_style.py — 6편 리포트의 **서술 규약을 코드로 강제**한다
=========================================================================================
계약서: `docs/REBUILD_2026-07-30.md` §5 (2026-07-31 재정립판). 이 파일은 그 §5 의 *실행 가능한 구현*이다.
규약을 지키는 것이 "성실함"이 아니라 **함수를 부르면 자동으로 되는 일**이 되게 하는 것이 목적이다.

⭐ 이 판의 원리 — **주장의 크기를 맞추면 변명이 필요 없다**
------------------------------------------------------------------------------------------
방어적 표현이 필요하다는 것은 **문장이 실제보다 크게 말하고 있다는 신호**다.
고칠 곳은 표현이 아니라 주장의 크기다. 크기를 맞추면 그냥 사실이 되고, 사실은 방어할 필요가 없다.

| 방어적 (이 모듈이 막는다) | 크기를 맞춘 문장 (같은 정보, 방어 0) |
|---|---|
| "절대 σ 가 맞다고 주장하지 않는다" | "자세 패턴은 기하에서 계산했고 레벨은 Das 측정에 맞췄다" |
| "PO 근사라 한계가 있다" | "해석 PO 구 대비 0.201 dB 안에서 일치한다" |
| "이 결론은 잠정적이다" | "β ≤ 45° 에서 성립한다" |
| "편파를 통제하지 못했다" | "편파: VV 단일. 실측에서 2편파로 확장한다" |

오른쪽은 왼쪽보다 **정보가 더 많고 더 짧다.** 그것이 목표다.
불확실한 양은 **표에 숫자로** 넣는다 — `크기 전이 L² vs L⁴ = 9.50 dB` 는 사실이지 사과가 아니다.

무엇을 기계적으로 막는가
------------------------------------------------------------------------------------------
| 규약(§5)                          | 이 모듈의 장치                                          |
|---|---|
| 여는 블록 = 한 일/결과/방법/재현    | `header()` — 블록이 비면 **예외**                       |
| 한 일은 **질문이 아니라 한 일**     | `header()` — 물음표로 끝나면 **예외**                   |
| 결과는 3~5줄이고 숫자가 있다        | `header()` — 아니면 **예외**                            |
| 범위는 "방법"이 말한다              | `header(method=…)` — 2줄 이상 필수                      |
| 손으로 친 숫자 0개                  | `num()` — JSON 을 열어 키를 찾고 값을 **대조**, 어긋나면 예외 |
| 표 안의 숫자도 손으로 안 침         | `table_from()` — JSON 배열/딕셔너리에서 행을 직접 뽑는다 |
| 그림 1개 = 질문 1개                 | `caption()` — 물음표로 안 끝나거나 2개면 **예외**       |
| §마지막 = "다음 단계"(앞을 본다)    | `next_steps()` — 결정되는 것이 없는 행은 **예외**       |
| 재현 블록이 실제로 돌아야 함        | `header()` — 출력 JSON 이 디스크에 없으면 예외          |
| 분량 상한(25셀 / 12줄 / 8그림)      | `check_budget()` · `build_notebook(strict=True)`        |
| **부정문 3개 이하**(§5.8-1)         | `count_negatives()` → `check_budget()` **위반**         |
| **완충어 0건**(§5.8-3)              | `grep_hedges()` → `check_budget()` **위반**             |
| 과정 서사 금지(§5.5)                | `lint_prose()` → `check_budget()` 권고                  |
| 그림 글자는 영어                    | `assert_fig_text()`                                     |

⭐ 톤 검사(부정문·완충어)는 **권고가 아니라 위반**이다.
   오탐의 대가는 문장 하나 다시 쓰기이고, 미탐의 대가는 **사용자가 거부한 그 산문이 그대로 나가는 것**이다.
   대신 걸린 문장을 그대로 돌려주므로 고치는 데 1분이 걸리지 않는다.

⭐ 검증을 끄는 스위치는 **어디에도 없다**. 거짓말할 수 있는 출처 표시는 없느니만 못하다.
   JSON 값이 `null` 이면 `num()` 은 예외를 낸다 — "모른다"를 숫자로 위장시키지 않기 위해서다
   (`if_null="미상"` 으로 명시하면 그 말이 그대로 찍힌다).

⚠ 이 모듈은 **임포트해도 안전**하다(부작용 없음). `src/make_report0N_*.py` 와 다르다.

------------------------------------------------------------------------------------------
2026-07-31 계약 변경 — 옛 빌더가 고쳐야 할 것
------------------------------------------------------------------------------------------
| 폐지 | 대체 |
|---|---|
| `header(question=…)` | `header(did=…)` — 물음표가 아니라 **한 일**. 물음표로 끝나면 예외 |
| `header(conclusion_lines=…)` | `header(results=…)` |
| `header(claims=…, non_claims=…)` | `header(method=…)` — **어떻게 얻었는지**가 곧 범위다 |
| `limits([...])` | `next_steps([...])` — `다음에 할 일 \\| 그러면 결정되는 것 \\| 어디서` |

옛 이름을 부르면 `ContractError` 가 **무엇으로 바꿔야 하는지 적어서** 터진다(조용히 통과하지 않는다).

------------------------------------------------------------------------------------------
워크드 예제 — 규약을 통과하는 최소 빌더 (그대로 복사해서 시작할 것)
------------------------------------------------------------------------------------------
```python
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from report_style import (header, num, caption, next_steps, md, code,
                          table, table_from, build_notebook, from_json)

S = from_json("outputs/sbr_kr_sweep.json")          # 이 편의 근거 JSON

blocks = [
    header(
        num=2,
        title="표적 모델 — 메쉬 · 엔진 · 앵커",
        did="드론 7종의 메쉬에 광선추적 가림과 부품별 재질 PO 를 적용해 RCS 를 계산하고, "
            "레벨과 주파수 의존성을 Das 측정에 맞췄다.",
        results=[
            f"해석 PO 구 대비 최대 편차 "
            f"{S.num('summary_div16.max_abs_db_vs_po', 0.201, '{:.3f}', 'dB')} "
            f"(kr 21점 × 입사 {S.num('meta.n_incidence', 48, '{:.0f}')}방향).",
            "자세 패턴은 기하에서 계산했다 — 부품별 재질 + 광선추적 가림.",
            "레벨과 밴드 기울기는 Das 측정(IEEE WCL 2026 15:3731) 에 맞췄다.",
            "바이스태틱은 β ≤ 45° 에서 성립한다.",
        ],
        method=[
            ("자세 패턴", "Sionna 의 Mitsuba/OptiX 로 first-hit 가림, 조명면에 PO 적분"),
            ("절대 레벨", "Das 측정에 A(f)B1(φ)B2 분해로 맞춤 — B1 은 우리 계산 그대로"),
            ("검증", "해석 PO 구 · PEC 이면각 해석해와 대조"),
        ],
        prereq=[("01 §3", "게재 선행이 표적 산란을 어떻게 다뤘는지")],
        repro=dict(cmd="PYTHONPATH=src python benchmark/verify_sbr_kr_sweep.py",
                   out="outputs/sbr_kr_sweep.json",
                   runtime="약 18분 (GPU 1장)"),
    ),

    md("## §1. 메쉬", "",
       "부품별 재질을 유지한 채 watertight 로 만든다. 코드는 `src/drone_cad.py:120`."),

    # 숫자가 든 표는 JSON 에서 직접 뽑는다 — 손으로 치면 검증을 우회한다.
    md("## §4. 앵커가 통제한 것과 통제하지 않은 항목의 크기", "",
       table_from("outputs/sigma_anchor.json:uncontrolled",
                  [("항목", "term"), ("상태", "status"), ("크기", "size_db")],
                  fmt={"size_db": "{:+.2f} dB"}, null="미상")),

    # 그림은 **미리 그려둔 PNG 를 마크다운으로 끼운다**(viz 스크립트가 만든다).
    md("![sbr validate](outputs/figures/report2_sbr_validate.png)", "",
       caption(1, "SBR 이 해석 PO 와 몇 dB 안에서 일치하는가?")),

    next_steps([
        ("등가 모서리 전류(PTD)를 넣는다", "밴드 기울기가 기하만으로 서는지 결정된다",
         "`src/rcs_sbr.py` → 02편 §3 재측정"),
        ("VV/HH 2편파를 잰다", "편파 항의 크기가 수치로 확정된다", "06편 §2 측정 설계"),
    ]),
]

build_notebook("report02.ipynb", blocks, strict=True)
```

여섯 빌더가 공통으로 지킬 것
------------------------------------------------------------------------------------------
1. `md()` / `code()` / `header()` / `next_steps()` 는 **전부 그냥 문자열**(`Block`)이다.
   `print(header(...))`, `md("a") + "b"` 다 된다. `.kind` 만 얹혀 있어 셀 종류를 안다.
2. **숫자는 전부 `num()` 을 통과**시킨다. 값을 안 적고 `num(None, ...)` 로 두면 JSON 이
   유일한 진실이 된다. 값을 적으면 그건 *주장*이고, JSON 과 어긋나면 빌드가 멈춘다.
   표 안의 숫자도 예외가 아니다 — 칸마다 `num()` 을 넣거나 `table_from()` 으로 뽑는다.
3. 그림은 viz 스크립트가 만든 **PNG 를 마크다운으로 끼우고** 바로 밑에 `caption()` 한 줄.
   그림 안의 글자는 영어 — viz 쪽에서 `assert_fig_text()` 로 확인한다.
4. 마지막은 반드시 `next_steps()`. **무엇이 결정되는지**가 없으면 예외가 난다.
5. 다 만들고 `build_notebook(..., strict=True)` — §5.7 상한·§5.8 톤 검사를 넘으면 만들어지지 않는다.

`python src/report_style.py` 로 이 모듈 자체의 데모·자기검사를 돌려볼 수 있다.
`python src/report_style.py report01_prior.ipynb …` 로 기존 노트북들을 한 번에 측정한다.
"""
from __future__ import annotations

import json
import os
import re
import sys
from typing import Any, Iterable, Sequence

# --------------------------------------------------------------------------- #
#  경로 · 상수
# --------------------------------------------------------------------------- #
ROOT = os.environ.get(
    "SIONNA2_ROOT",
    os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))

#: ⛔ 2026-08-10 사용자 지시로 **셀 수 상한을 폐지**한다.
#   *"규약 상한 이런 거 만들지 마 / 그냥 적당히 핵심 메시지가 담기는 하나의 구성을 토대로
#    합친다만을 목표로 해서 제대로 구성해줘"*
#   왜 폐지가 옳은가 — 상한이 «넘치면 편을 쪼개라» 를 강제했고, 그 규칙이 78 편이라는
#   과잉 분할을 낳았다. 편의 크기는 **하나의 메시지가 끝나는 자리**가 정해야지 셀 수가
#   정해서는 안 된다. None 이면 검사는 통과하고 실제 셀 수만 보고된다.
MAX_MD_CELLS = None
MAX_LINES_PER_CELL = 12
MAX_FIGURES = 8

#: §5.8 톤 상한. 부정문은 편당 3개까지, 완충어는 0건.
MAX_NEGATIVES = 3
MAX_HEDGES = 0

#: 마크다운 블록 안에서 이 줄을 만나면 **셀을 나눈다**.
BREAK = "<!--cell-->"

#: 구조 블록 태그 — 12줄 상한에서 면제되고, 존재 여부가 검사된다.
TAG_HEADER = "header"
TAG_NEXT = "next_steps"
TAG_LIMITS = "limits"            # 폐지된 옛 태그. 옛 노트북을 **식별**하는 데만 쓴다.
#: 논문 참고자료 블록(`docs/PAPER_SPEC.md` §4 — 논문 대응·방어선·방법 문단·인용).
#  `src/paper_kit.py` 가 단다. 방어선 표가 길어서 **12줄 상한만** 면제한다 —
#  셀 수(§5.7)·톤(§5.8)·출처(§5.6-1) 검사는 다른 셀과 똑같이 받는다.
TAG_PAPER = "paper"
#: 편 끝의 «출처» 표. `build_notebook()` 이 **자동으로** 붙인다 — 손으로 쓰지 않는다.
#  본문의 출처 태그를 각주 번호로 바꾸고 그 원장을 여기 싣는다(§5.6-3).
#  12줄 상한·톤 검사·출처 없는 숫자 권고에서 면제된다: 이 셀은 산문이 아니라 기계 원장이다.
TAG_SOURCES = "sources"
_TAG_RE = re.compile(r"^<!--rs:([a-z_]+)-->\s*\n?")

KERNEL = {"display_name": "py312", "language": "python", "name": "py312"}


class ContractError(Exception):
    """서술 규약(§5) 위반. 리포트가 만들어지기 **전에** 터진다."""


class Block(str):
    """노트북 셀 하나(이상)가 될 텍스트. **str 그 자체**라서 그냥 출력·연결해도 된다.

    `.kind` 만 얹혀 있다(`"markdown"` / `"code"`). `build_notebook()` 이 그걸 보고 셀을 만든다.
    """
    kind = "markdown"

    def __new__(cls, text: str, kind: str = "markdown"):
        o = super().__new__(cls, text)
        o.kind = kind
        return o


# --------------------------------------------------------------------------- #
#  1) 출처 검증 — `num()`
#     "값 ⟨outputs/xxx.json : key⟩". 거짓말할 수 있는 출처 표시는 없느니만 못하다.
#     그래서 이 함수는 **실제로 JSON 을 열어** 키를 찾고 값을 대조한다.
# --------------------------------------------------------------------------- #
_JSON_CACHE: dict[str, Any] = {}


def load_json(path: str) -> Any:
    """`outputs/x.json`(또는 `.npz`) 을 읽는다. 상대경로는 리포지토리 루트 기준. 캐시한다."""
    p = path if os.path.isabs(path) else os.path.join(ROOT, path)
    p = os.path.normpath(p)
    if p not in _JSON_CACHE:
        if not os.path.exists(p):
            raise ContractError(
                f"출처 JSON 이 없다: {path}\n"
                f"  → 리포트를 쓰기 전에 그 실험을 먼저 돌려야 한다. (기대 경로: {p})")
        if p.endswith(".npz"):
            import numpy as _np                     # npz 를 인용할 때만 필요
            _JSON_CACHE[p] = dict(_np.load(p))      # NpzFile 은 lazy 라 dict 로 고정
        else:
            with open(p, encoding="utf-8") as f:
                _JSON_CACHE[p] = json.load(f)
    return _JSON_CACHE[p]


def _split_source(source) -> tuple[str, str]:
    """`"outputs/a.json:x.y"` 또는 `("outputs/a.json", "x.y")` → (path, key)."""
    if isinstance(source, (tuple, list)):
        if len(source) != 2:
            raise ContractError(f"source 튜플은 (경로, 키) 2개여야 한다: {source!r}")
        return str(source[0]), str(source[1])
    m = re.match(r"^\s*(.+?\.(?:json|npz))\s*:\s*(.+?)\s*$", str(source))
    if not m:
        raise ContractError(
            f"source 형식이 틀렸다: {source!r}\n"
            f"  → 'outputs/xxx.json:키.경로' 또는 ('outputs/xxx.json', '키.경로')")
    return m.group(1), m.group(2)


def _walk(node: Any, path: str, trail: list[str]) -> tuple[Any, list[str]]:
    """점(.)으로 이은 키 경로를 따라간다.

    ⚠ 이 프로젝트의 키에는 점이 들어간다(`"LTE 1.843 GHz"`, `"5G 3.5 GHz"`).
      그래서 단순 `split('.')` 이 아니라 **가장 긴 키부터 접두 일치**로 내려간다.
      리스트는 `rows[3].kr` 처럼 대괄호로 인덱싱한다.
    """
    path = path.strip()
    if not path:
        return node, trail

    m = re.match(r"^\[(-?\d+)\]\.?(.*)$", path)
    if m:
        # 리스트·튜플·numpy 배열(.npz 출처) 모두 인덱싱한다
        if isinstance(node, dict) or not hasattr(node, "__getitem__") \
                or not hasattr(node, "__len__"):
            raise ContractError(
                f"인덱싱 대상이 배열이 아니다: {'.'.join(trail) or '<root>'} "
                f"({type(node).__name__})")
        i = int(m.group(1))
        if not (-len(node) <= i < len(node)):
            raise ContractError(
                f"인덱스 범위 밖: {'.'.join(trail)}[{i}] (길이 {len(node)})")
        return _walk(node[i], m.group(2), trail + [f"[{i}]"])

    if isinstance(node, dict):
        cands = sorted(
            (k for k in node
             if path == k or path.startswith(f"{k}.") or path.startswith(f"{k}[")),
            key=len, reverse=True)
        for k in cands:
            rest = path[len(k):]
            rest = rest[1:] if rest.startswith(".") else rest
            try:
                return _walk(node[k], rest, trail + [k])
            except ContractError:
                continue
        keys = list(node.keys())
        shown = ", ".join(repr(k) for k in keys[:12]) + (" …" if len(keys) > 12 else "")
        raise ContractError(
            f"키를 못 찾았다: '{path}' (위치 {'.'.join(trail) or '<root>'})\n"
            f"  → 여기서 가능한 키: {shown}")

    raise ContractError(
        f"'{path}' 를 더 내려갈 수 없다 — {'.'.join(trail) or '<root>'} 는 "
        f"{type(node).__name__} 이다")


def _py(v: Any) -> Any:
    """numpy 스칼라(.npz 출처)를 파이썬 값으로. 그 외는 그대로."""
    if hasattr(v, "item") and getattr(v, "size", None) == 1:
        return v.item()
    return v


def fetch(source) -> Any:
    """JSON/npz 에서 값만 꺼낸다(태그 없이). 계산·그림 코드에서 쓴다."""
    p, k = _split_source(source)
    return _py(_walk(load_json(p), k, [])[0])


def _auto_fmt(v: Any) -> str:
    if isinstance(v, bool):
        return "예" if v else "아니오"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        if v == int(v) and abs(v) < 1e6:
            return f"{v:.0f}"
        return f"{v:.4g}"
    return str(v)


def _fmt(v: Any, fmt: str | None) -> str:
    if fmt is None:
        return _auto_fmt(v)
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return fmt.format(v)
    return str(v)


def num(value: Any, source, fmt: str | None = None, unit: str = "",
        tol: float | None = None, if_null: str | None = None) -> str:
    """`값 ⟨outputs/xxx.json : key⟩` 를 만든다. **출처를 실제로 검증한다.**

    파라미터
    --------
    value : 리포트에 쓰려는 값. **`None` 이면 JSON 값을 그대로 가져온다**(가장 안전).
            값을 적었다면 그것은 "이 숫자일 것이다"라는 *주장*이고, 어긋나면 예외가 난다.
    source: `"outputs/x.json:a.b.c"` 또는 `("outputs/x.json", "a.b.c")`.
    fmt   : `"{:.2f}"` 같은 포맷. 주면 **표시 반올림 기준으로 일치**를 판정한다
            (0.2005726 과 0.201 은 `{:.3f}` 아래서 같다).
    unit  : `"dB"`, `"%"` 처럼 값 뒤에 붙일 단위.
    tol   : 절대 허용오차를 직접 주고 싶을 때.
    if_null: JSON 값이 `null` 일 때 **대신 쓸 말**(예: `"미상"`). 안 주면 예외.
            `null` 은 "아직 모른다"는 뜻이지 숫자가 아니다 — 그걸 리포트에 숫자처럼
            흘려보내지 않기 위한 장치다(앵커의 미해소 항목들이 실제로 `null` 이다).

    표시되는 숫자는 **언제나 JSON 값**이다. `value` 는 대조용일 뿐이므로,
    JSON 이 바뀌면 리포트 숫자도 같이 바뀌고, 손으로 적은 값과 어긋나면 빌드가 멈춘다.

    ⚠ 검증을 끄는 스위치는 **없다**. 거짓말할 수 있는 출처 표시는 없느니만 못하다.
    """
    p, k = _split_source(source)
    jval = _py(_walk(load_json(p), k, [])[0])

    # null = "아직 모른다". 숫자로 위장시키지 않는다(그냥 두면 "None dB ⟨…⟩" 가 찍힌다).
    if jval is None:
        if if_null is None:
            raise ContractError(
                f"출처 값이 null 이다 — {p}:{k}\n"
                f"  → null 은 '아직 모른다'는 뜻이지 숫자가 아니다. "
                f"그 사실을 그대로 쓰려면 `if_null='미상'` 처럼 명시하라.")
        return f"{if_null} ⟨{p} : {k}⟩"

    # 인용은 **값 하나**여야 한다 — 배열·딕셔너리를 통째로 본문에 붓지 않는다(§5.5 "산문 속 숫자 나열").
    if isinstance(jval, (dict, list, tuple)) or getattr(jval, "ndim", 0):
        n = len(jval) if hasattr(jval, "__len__") else "?"
        raise ContractError(
            f"인용한 것이 값 하나가 아니다 — {p}:{k} 는 {type(jval).__name__}(길이 {n}) 다.\n"
            f"  → 원소를 집어라: '{k}[0]' 또는 '{k}.<키>'. "
            f"여러 값을 보여줄 거면 `table()` 로 표를 만들어라.")

    if value is not None:
        num_pair = (isinstance(jval, (int, float)) and not isinstance(jval, bool)
                    and isinstance(value, (int, float)) and not isinstance(value, bool))
        if num_pair:
            diff = abs(float(value) - float(jval))
            if tol is not None:
                ok = diff <= tol
            elif fmt is not None:
                ok = (fmt.format(value) == fmt.format(jval)
                      or diff <= 1e-9 * max(1.0, abs(float(jval))))
            else:
                ok = diff <= 1e-6 * max(1.0, abs(float(jval)))
            if not ok:
                raise ContractError(
                    f"숫자가 출처와 다르다 — {p}:{k}\n"
                    f"  리포트에 적은 값 : {value!r}\n"
                    f"  JSON 의 값       : {jval!r}\n"
                    f"  → 값을 고치거나, 아예 `num(None, ...)` 로 JSON 에서 직접 읽어라.")
        elif str(value) != str(jval):
            raise ContractError(
                f"값이 출처와 다르다 — {p}:{k}\n  적은 값: {value!r}\n  JSON: {jval!r}")

    shown = _fmt(jval, fmt)
    if unit:
        shown = f"{shown} {unit}" if unit not in "%°" else f"{shown}{unit}"
    return f"{shown} ⟨{p} : {k}⟩"


class Source:
    """한 JSON 을 반복해 참조할 때 쓰는 얇은 래퍼.

        S = from_json("outputs/sbr_kr_sweep.json")
        S.num("summary_div16.max_abs_db_vs_po", 0.201, "{:.3f}", "dB")
        S.get("meta.n_incidence")      # 값만 (계산·그림용)
    """

    def __init__(self, path: str):
        self.path = path
        load_json(path)            # 없으면 여기서 즉시 터진다

    def get(self, key: str) -> Any:
        return fetch((self.path, key))

    def num(self, key: str, value: Any = None, fmt: str | None = None,
            unit: str = "", tol: float | None = None,
            if_null: str | None = None) -> str:
        return num(value, (self.path, key), fmt=fmt, unit=unit, tol=tol,
                   if_null=if_null)

    def table(self, key: str, columns: Sequence, **kw) -> str:
        """이 JSON 안의 배열/딕셔너리를 표로. `table_from()` 참조."""
        return table_from((self.path, key), columns, **kw)

    def __repr__(self) -> str:            # pragma: no cover
        return f"Source({self.path!r})"


def from_json(path: str) -> Source:
    return Source(path)


# --------------------------------------------------------------------------- #
#  2) 톤 검사 — §5.8 자기검사를 **실행 가능한 검사**로
#
#     ⭐ 이것들은 권고가 아니라 위반이다. 오탐의 대가는 문장 하나 다시 쓰기이고,
#        미탐의 대가는 사용자가 거부한 그 산문이 그대로 나가는 것이다.
#        대신 **걸린 문장을 그대로 돌려준다** — 세기만 하면 고칠 수가 없다.
# --------------------------------------------------------------------------- #
#: §5.8-1 부정문 — "…않는다 / 못한다 / 아니다 / 없다" 로 **끝나는** 문장.
#  과거형 변형(않았다·못했다·없었다)도 같은 물건이라 함께 센다.
_NEG_ENDINGS = ("않는다", "않았다", "않다", "못한다", "못했다",
                "아니다", "없다", "없었다")

#: §5.8-3 완충어 — **0건**이어야 한다. (표현, 무엇으로 바꾸나)
_HEDGES: list[tuple[str, str]] = [
    (r"(?:라|다|으로|로)고?\s*볼 수 있",  "단정하라: '…이다' 또는 조건절 '…에서 …이다'"),
    (r"[가-힣]\s*편이(?:다|었|라)",        "수치로: '…는 X dB 다'"),
    (r"대체로",                            "범위를 조건절로: '…에서'"),
    (r"어느 정도",                          "크기를 숫자로"),
    (r"아마도?(?![가-힣])",                "확인하고 단정하거나, 다음 단계 표로 넘겨라"),
    (r"아쉽게도",                           "삭제. 사과는 정보가 0이다"),
    (r"불행히도",                           "삭제. 사과는 정보가 0이다"),
    (r"유의할 점",                          "그 양을 표에 숫자로 넣어라"),
    (r"잠정적",                             "성립 범위를 조건절로: 'β ≤ 45° 에서'"),
    (r"인 것 같다|같아 보인다",             "단정하라"),
    (r"생각된다|사료된다|판단된다",          "누가 무엇으로 판단했는지 방법 블록에"),
    (r"(?:으로|로)\s*보인다",               "측정값이면 '…로 측정된다'"),
    (r"할 수도 있다",                       "조건을 특정하라"),
    (r"다소|비교적",                        "차이를 숫자로"),
]

#: §5.5 과정 서사 — "처음엔 …했다가 …로 바꿨다" 류. 버그·수정 이력도 여기 걸린다(권고).
_NARRATIVE = [
    (r"처음(?:엔|에는)", "과정 서사"),
    (r"원래(?:는|,| )", "과정 서사"),
    (r"기존(?:에|에는)\b", "과정 서사"),
    (r"이전(?:엔|에는)", "과정 서사"),
    (r"바꾸었다|바꿨다|바뀌었다", "과정 서사"),
    (r"수정(?:했다|하였다|됐다|되었다)", "버그·수정 이력"),
    (r"버그|defect|오류를 발견", "버그·수정 이력"),
    (r"고쳤다|고치었다", "버그·수정 이력"),
    (r"이제(?:는)? 더 이상", "과정 서사"),
]

_CODE_FENCE = re.compile(r"```.*?```", re.S)
_CODE_SPAN = re.compile(r"`[^`]*`")
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)
_IMG_MD = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_LINK_MD = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_PROV_ANY = re.compile(r"⟨[^⟩]*⟩")
_EMPH = re.compile(r"[*_~]+")
_TABLE_SEP = re.compile(r"^\s*\|?[\s:\-|]+\|[\s:\-|]*$")
_LIST_MARK = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
_SENT_SPLIT = re.compile(r"(?<=[.!?。])\s+")
_SENT_END = re.compile(r"[.!?。]\s|\n")


def _plain(text: str) -> str:
    """마크다운에서 **산문만** 남긴다 — 코드·태그·이미지·강조를 걷어낸다."""
    t = _CODE_FENCE.sub(" ", str(text))
    t = _HTML_COMMENT.sub(" ", t)
    t = _CODE_SPAN.sub(" ", t)
    t = _IMG_MD.sub(" ", t)
    t = _LINK_MD.sub(r"\1", t)
    t = _PROV_ANY.sub(" ", t)        # 출처 태그는 산문이 아니다
    return _EMPH.sub("", t)


def _segments(text: str) -> list[str]:
    """산문을 **문장 단위**로 쪼갠다.

    표는 칸마다 한 문장으로 센다 — 방어적 표현은 표 안으로 숨는 일이 잦다.
    """
    out: list[str] = []
    for line in _plain(text).splitlines():
        if _TABLE_SEP.match(line):                     # |---|---| 구분줄
            continue
        parts = [c for c in line.split("|")] if "|" in line else [line]
        for part in parts:
            s = part.strip().lstrip(">#").strip()
            s = _LIST_MARK.sub("", s)
            if not s:
                continue
            out += [x.strip() for x in _SENT_SPLIT.split(s) if x.strip()]
    return out


_TRAIL = " \t.。!?)]}'\"’”*_`·…"


def _ends_negative(sentence: str) -> str | None:
    """문장이 부정 종결로 끝나면 그 어미를 돌려준다."""
    s = sentence.rstrip(_TRAIL)
    for e in _NEG_ENDINGS:
        if s.endswith(e):
            return e
    return None


def _as_cells(nb: Any) -> list[dict]:
    """노트북 경로 / 노트북 dict / 셀 리스트 / 생 텍스트 → 셀 리스트."""
    if isinstance(nb, dict) and "cells" in nb:
        return list(nb["cells"])
    if isinstance(nb, str):
        if nb.strip().endswith(".ipynb"):
            p = nb if os.path.isabs(nb) else os.path.join(ROOT, nb)
            if not os.path.exists(p):
                raise ContractError(f"검사할 노트북이 없다: {nb} (기대 경로: {p})")
            with open(p, encoding="utf-8") as f:
                return list(json.load(f).get("cells", []))
        return [{"cell_type": "markdown", "source": nb}]     # 생 텍스트·Block
    if isinstance(nb, (list, tuple)):
        cells = []
        for i, b in enumerate(nb):
            if isinstance(b, dict) and "cell_type" in b:
                cells.append(b)
            else:                                            # md()/문자열 블록
                kind = getattr(b, "kind", "markdown")
                cells.append({"cell_type": kind, "source": str(b)})
        return cells
    raise ContractError(f"검사 대상이 노트북이 아니다: {type(nb).__name__}")


def _cell_text(c: dict) -> str:
    s = c.get("source", "")
    return s if isinstance(s, str) else "".join(s)


def count_negatives(nb: Any) -> dict:
    """§5.8-1 **부정문 세기** — "않는다/못한다/아니다/없다" 로 끝나는 문장. 편당 3개 이하.

    입력: 노트북 경로 · 노트북 dict · 블록 리스트 · 생 텍스트 아무거나.
    반환: `dict(count, cap, ok, sentences=[{cell, ending, text}, …])`

    ⭐ **걸린 문장을 그대로 돌려준다.** 세기만 하면 고칠 수가 없다.
       고치는 법은 하나다 — 무엇을 **했는지**로 다시 쓴다(§5.0).
         "편파를 통제하지 못했다"  →  "편파: VV 단일. 실측에서 2편파로 확장한다"
    """
    hits = []
    for i, c in enumerate(_as_cells(nb)):
        if c.get("cell_type") != "markdown" or _has_tag(c, TAG_SOURCES):
            continue
        for s in _segments(_cell_text(c)):
            e = _ends_negative(s)
            if e:
                hits.append({"cell": i, "ending": e, "text": s})
    return {"count": len(hits), "cap": MAX_NEGATIVES,
            "ok": len(hits) <= MAX_NEGATIVES, "sentences": hits}


def grep_hedges(nb: Any) -> dict:
    """§5.8-3 **완충어 grep** — 0건이어야 한다.

    걸리는 것: ~라고 볼 수 있 · ~인 편 · 대체로 · 어느 정도 · 아마 · 아쉽게도 · 불행히도 ·
              유의할 점 · 잠정적 (+ 같은 물건인 변형들).
    반환: `dict(count, ok, hits=[{cell, hedge, fix, text}, …])`

    ⭐ 완충어가 필요하다는 것은 **문장이 실제보다 크게 말하고 있다는 신호**다(§5.0).
       표현을 부드럽게 하지 말고 **주장의 크기**를 줄여라. 크기가 맞으면 그냥 사실이 된다.
    """
    hits = []
    for i, c in enumerate(_as_cells(nb)):
        if c.get("cell_type") != "markdown" or _has_tag(c, TAG_SOURCES):
            continue
        for s in _segments(_cell_text(c)):
            for pat, fix in _HEDGES:
                m = re.search(pat, s)
                if m:
                    hits.append({"cell": i, "hedge": m.group(0),
                                 "fix": fix, "text": s})
                    break                       # 문장 하나에 한 번만 보고한다
    return {"count": len(hits), "ok": len(hits) <= MAX_HEDGES, "hits": hits}


def lint_prose(text: str) -> list[str]:
    """§5.5 **과정 서사·버그 이력**과 긴 문단을 찾아 권고 목록으로 돌려준다(예외는 안 낸다).

    완충어·부정문은 여기가 아니라 `grep_hedges()`·`count_negatives()` 가 맡는다(그쪽은 위반이다).
    """
    t = _plain(text)
    body = "\n".join(ln for ln in t.splitlines()
                     if not ln.lstrip().startswith(("|", ">", "#", "!", "```")))
    hits: list[str] = []
    for pat, why in _NARRATIVE:
        for m in re.finditer(pat, body):
            hits.append(f"{why}: '{m.group(0)}' (§5.5 금지)")
    # 3문장 넘는 문단 — "끊거나 표로".
    # ⚠ 목록(결과 3~5줄 등)은 이미 끊어 쓴 것이므로 문단으로 세지 않는다.
    prose = "\n".join(ln for ln in body.splitlines()
                      if not re.match(r"^\s*(?:\d+\.|[-*+])\s", ln))
    for para in re.split(r"\n\s*\n", prose):
        para = para.strip()
        if not para:
            continue
        n_sent = len([s for s in _SENT_END.split(para) if s.strip()])
        if n_sent > 3:
            hits.append(f"문단이 {n_sent}문장 > 3 (§5.4: 끊거나 표로) "
                        f"— \"{para[:40]}…\"")
    return sorted(set(hits))


def _assert_tone(where: str, *texts: str) -> None:
    """여는 블록·다음 단계 표처럼 **첫 화면에 걸리는 자리**는 톤 위반을 즉시 막는다."""
    for t in texts:
        for s in _segments(str(t)):
            for pat, fix in _HEDGES:
                m = re.search(pat, s)
                if m:
                    raise ContractError(
                        f"{where}: 완충어 '{m.group(0)}' (§5.8-3 완충어 0건)\n"
                        f"  문장: \"{s}\"\n"
                        f"  → {fix}\n"
                        f"  ⭐ 완충어가 필요하다는 건 문장이 실제보다 크게 말하고 있다는 신호다. "
                        f"표현이 아니라 **주장의 크기**를 고쳐라(§5.0).")


# --------------------------------------------------------------------------- #
#  3) 여는 블록 — `header()`
#     한 일 / 결과 / 방법 / 재현 (+ 앞 편에서). 전부 능동태.
# --------------------------------------------------------------------------- #
def _rows(items: Sequence, what: str, width: int = 2) -> list[tuple[str, ...]]:
    """`[(a, b), …]` 또는 `[{"a":…,"b":…}]` 를 width 열 튜플 리스트로."""
    out = []
    for it in items:
        if isinstance(it, dict):
            vals = list(it.values())
        elif isinstance(it, (tuple, list)):
            vals = list(it)
        else:
            raise ContractError(f"{what}: {width}열 짜리 행이어야 한다 — {it!r}")
        if len(vals) != width:
            raise ContractError(
                f"{what}: {width}열이 필요하다 (지금 {len(vals)}열) — {it!r}")
        out.append(tuple(str(v) for v in vals))
    return out


def _md_escape_cell(s: str) -> str:
    return str(s).replace("|", r"\|").replace("\n", " ")


_LEGACY_HEADER_ARGS = {
    "question": "did",
    "conclusion_lines": "results",
    "claims": "method",
    "non_claims": "method",
}


def header(num: int | str,                       # noqa: A002  (계약서의 인자 이름 그대로)
           title: str,
           did: str | None = None,
           results: Sequence[str] | None = None,
           method: Sequence | None = None,
           repro: dict | None = None,
           prereq: Sequence | None = None,
           method_cols: tuple[str, str] = ("무엇을", "어떻게 얻었나"),
           allow_missing_output: bool = False,
           **legacy) -> Block:
    """§5.2 **여는 블록**을 만든다 — 한 일 / 결과 / 방법 / 재현 (+ 앞 편에서). 하나라도 비면 예외.

    파라미터
    --------
    did     : **한 일**. 한 문장, 능동태, `…했다` 로 끝난다. **물음표로 끝나면 예외다.**
              ⚠ 옛 계약은 여기에 *질문*을 요구했다. 새 계약은 **한 일**을 요구한다.
              그 뒤집힘이 이 함수가 가장 먼저 막는 것이다.
    results : **결과** 3~5줄. 숫자가 있어야 한다(`num()` 으로 넣어라).
              여기만 읽어도 결과를 알 수 있어야 한다.
    method  : **방법**. `["…"]` 또는 `[("무엇을", "어떻게 얻었나"), …]`, 2개 이상.
              ⭐ 이것이 옛 "주장하지 않는 것" 표를 대신한다. **어떻게 얻었는지**를 정확히 쓰면
                 무엇을 말할 수 있는지가 따라 나온다 — "Das 측정에 맞췄다" 가 곧 "레벨은 측정 출처" 다.
    repro   : `dict(cmd=…, out=…, runtime=…)`. `out` 이 디스크에 없으면 예외.
    prereq  : **앞 편에서** `[("01 §3", "무엇을 알고 와야 하나"), …]`. 없으면 생략된다.

    막는 것
    -------
    · 한 일이 물음표로 끝남 · 결과가 3~5줄이 아님 · 결과에 숫자가 없음
    · 방법이 2줄 미만 · 재현 출력이 디스크에 없음
    · 여는 블록 안의 완충어(0건) · 한 일의 부정 종결 · 결과의 부정 종결 2개 이상
    """
    # ── 옛 계약의 인자를 부르면, 무엇으로 바꿔야 하는지 적어서 막는다 ──────────
    if legacy:
        bad = {k: _LEGACY_HEADER_ARGS[k] for k in legacy if k in _LEGACY_HEADER_ARGS}
        if bad:
            raise ContractError(
                "옛 계약(2026-07-31 이전)의 인자다 — " +
                ", ".join(f"`{k}=` → `{v}=`" for k, v in bad.items()) + "\n"
                "  · `question=` 은 폐지됐다. 여는 블록은 질문이 아니라 **한 일**로 연다.\n"
                "  · `claims=`/`non_claims=` 표는 폐지됐다(§5.0). **방법**이 그 일을 한다 —\n"
                "    어떻게 얻었는지 정확히 쓰면 무엇을 말할 수 있는지가 따라 나온다.\n"
                "  → header(num=…, title=…, did='…했다', results=[…], method=[…], repro=…)")
        raise ContractError(f"header(): 모르는 인자 {sorted(legacy)}")

    # ── ① 한 일 ─────────────────────────────────────────────────────────────
    d = str(did or "").strip()
    if not d:
        raise ContractError(
            "§5.2 ①: **한 일**이 비었다. 이 편이 해낸 일을 한 문장으로 적어라.\n"
            "  예) '드론 7종의 메쉬에 광선추적 가림과 부품별 재질 PO 를 적용해 RCS 를 계산했다.'")
    if d.endswith("?") or "?" in d:
        raise ContractError(
            f"§5.2 ①: **한 일은 질문이 아니다.** 물음표가 있다 — {d!r}\n"
            "  ⚠ 옛 계약은 여기에 질문을 요구했다. 새 계약은 **한 일**을 요구한다.\n"
            "  → '…를 했다' 로 끝나는 한 문장으로 바꿔라.\n"
            "     '무엇을 믿어도 되는가?'  →  '해석해 대조로 엔진을 검증하고 레벨을 측정에 맞췄다.'")
    core = d.rstrip(_TRAIL)
    if not core.endswith("다"):
        raise ContractError(
            f"§5.2 ①: 한 일은 능동태·완료형 한 문장이다 — '…했다' 로 끝나야 한다. 지금: {d!r}")
    if _ends_negative(d):
        raise ContractError(
            f"§5.2 ①: 한 일이 **부정문**이다 — {d!r}\n"
            "  → 첫 문장은 해낸 일이다(§5.8-2 첫 화면 시험). 무엇을 **했는지**로 다시 써라.")
    if len([s for s in _segments(d) if s]) > 1:
        raise ContractError(
            f"§5.2 ①: 한 일은 **한 문장**이다. 지금 여러 문장이다 — {d!r}\n"
            "  → 나머지는 결과(3~5줄)로 내려라.")

    # ── ② 결과 ─────────────────────────────────────────────────────────────
    R_lines = [str(c).strip() for c in (results or []) if str(c).strip()]
    if not (3 <= len(R_lines) <= 5):
        raise ContractError(
            f"§5.2 ②: 결과는 3~5줄이다. 지금 {len(R_lines)}줄.\n"
            "  → 여기만 읽어도 결과를 알 수 있어야 하고, 그 이상은 본문이다.")
    if not any(re.search(r"\d", c) for c in R_lines):
        raise ContractError(
            "§5.2 ②: 결과에 **숫자가 하나도 없다**. 근거 수치를 `num()` 으로 넣어라.\n"
            "  → 불확실한 양도 산문이 아니라 숫자로 쓴다 — '크기 전이 L² vs L⁴ = 9.50 dB'(§5.1).")
    neg_lines = [c for c in R_lines if _ends_negative(c)]
    if len(neg_lines) > 1:
        raise ContractError(
            f"§5.2 ②: 결과에 부정 종결 문장이 {len(neg_lines)}개다(첫 화면은 해낸 일이다).\n  "
            + "\n  ".join(f"- {c}" for c in neg_lines)
            + "\n  → 무엇을 했는지로 다시 써라. "
              "'절대 σ 를 주장하지 않는다' → '레벨은 Das 측정에 맞췄다'")

    # ── ③ 방법 ─────────────────────────────────────────────────────────────
    M_raw = list(method or [])
    if len(M_raw) < 2:
        raise ContractError(
            f"§5.2 ③: **방법**이 {len(M_raw)}줄이다 — 2줄 이상 적어라.\n"
            "  ⭐ 방법이 옛 '주장하지 않는 것' 표를 대신한다. 어떻게 얻었는지 정확히 쓰면\n"
            "     무엇을 말할 수 있는지가 따라 나온다 — 그래서 변명 절이 필요 없다(§5.0).\n"
            "  → method=[('절대 레벨', 'Das 측정에 맞춤'), ('자세 패턴', 'SBR+PO 기하 계산')]")
    M_table = all(isinstance(m, (tuple, list, dict)) for m in M_raw)
    M_rows = _rows(M_raw, "§5.2 ③ 방법", 2) if M_table else None
    M_bullets = None if M_table else [str(m).strip() for m in M_raw if str(m).strip()]
    if M_bullets is not None and len(M_bullets) < 2:
        raise ContractError("§5.2 ③: 방법이 2줄 이상이어야 한다.")

    # ── ④ 앞 편에서 ────────────────────────────────────────────────────────
    P = _rows(prereq or [], "§5.2 ⑤ 앞 편에서", 2)

    # ── ⑤ 재현 ─────────────────────────────────────────────────────────────
    Rp = dict(repro or {})
    for need in ("cmd", "out"):
        if not str(Rp.get(need, "")).strip():
            raise ContractError(
                f"§5.2 ④ 재현: '{need}' 가 없다. 명령 한 줄 + 출력 JSON 경로 + 소요시간은 필수다.\n"
                "  → repro=dict(cmd='PYTHONPATH=src python benchmark/x.py', "
                "out='outputs/x.json', runtime='약 12분 (GPU 1장)')")
    outs = Rp["out"] if isinstance(Rp["out"], (list, tuple)) else [Rp["out"]]
    for o in outs:
        pth = o if os.path.isabs(o) else os.path.join(ROOT, o)
        if not os.path.exists(pth) and not allow_missing_output:
            raise ContractError(
                f"§5.6-4 재현 블록이 실제로 돌아야 한다 — 출력이 디스크에 없다: {o}\n"
                f"  → 실험을 먼저 돌리거나, 경로를 고쳐라. (기대: {pth})")
    if not str(Rp.get("runtime", "")).strip():
        Rp["runtime"] = "(미측정 — 재현 전에 채울 것)"

    # ── 톤: 여는 블록은 첫 화면이다. 완충어 0건 ──────────────────────────────
    _assert_tone("§5.2 여는 블록", d, *R_lines,
                 *[" ".join(m) for m in (M_rows or [])], *(M_bullets or []))

    n = f"{int(num):02d}" if str(num).strip().isdigit() else str(num)

    A = [f"<!--rs:{TAG_HEADER}-->",
         f"# 리포트 {n} — {title}", "",
         "> ### 한 일",
         f"> **{d}**", "",
         "### 결과"]
    A += [f"{i+1}. {c}" for i, c in enumerate(R_lines)]

    B = [f"<!--rs:{TAG_HEADER}-->", "### 방법", ""]
    if M_rows:
        B += [f"| {method_cols[0]} | {method_cols[1]} |", "|---|---|"]
        B += [f"| {_md_escape_cell(a)} | {_md_escape_cell(b)} |" for a, b in M_rows]
    else:
        B += [f"- {m}" for m in (M_bullets or [])]
    B += ["", "### 재현", "", "```bash",
          *(Rp["cmd"] if isinstance(Rp["cmd"], (list, tuple)) else [Rp["cmd"]]),
          "```", "",
          "| | |", "|---|---|",
          "| 출력 | " + ", ".join(f"`{o}`" for o in outs) + " |",
          f"| 소요 | {Rp['runtime']} |"]
    if Rp.get("note"):
        B += [f"| 비고 | {_md_escape_cell(Rp['note'])} |"]
    if P:
        B += ["", "### 앞 편에서", "",
              "| 어디서 | 무엇을 알고 와야 하나 |", "|---|---|"]
        B += [f"| {_md_escape_cell(a)} | {_md_escape_cell(b)} |" for a, b in P]
    B += ["", "---"]

    return Block("\n".join(A) + f"\n\n{BREAK}\n\n" + "\n".join(B))


# --------------------------------------------------------------------------- #
#  4) 그림 캡션 — 그림 1개 = 질문 1개
# --------------------------------------------------------------------------- #
def caption(fig_no: int | str, question: str) -> str:
    """`**그림 3.** 질문?` — 그 그림이 답하는 **질문 하나**를 적는다(§5.6-2).

    (여는 블록의 '한 일' 과 반대다. 본문 서술은 한 일을 쓰고, 그림 캡션은 그 그림이 답하는
     질문을 쓴다 — 독자가 그림을 볼 이유가 캡션이기 때문이다.)
    """
    q = str(question).strip()
    if not q:
        raise ContractError("캡션이 비었다.")
    if not q.endswith("?"):
        raise ContractError(
            f"그림 {fig_no}: 캡션은 **그 그림이 답하는 질문**이다. 물음표로 끝나야 한다 — {q!r}")
    if q.count("?") > 1:
        raise ContractError(
            f"그림 {fig_no}: 그림 1개 = 질문 1개(§5.5). 물음표가 {q.count('?')}개다 — {q!r}\n"
            "  → 그림을 나눠라.")
    return f"**그림 {fig_no}.** {q}"


_HANGUL = re.compile(r"[가-힣ㄱ-ㆎ]")


def assert_fig_text(*labels: str) -> None:
    """하우스 규약: **그림 안의 글자(제목·축·범례·주석)는 전부 영어**. 한글이 있으면 예외.

    (본문 산문·주석·print 는 한국어다. 이 검사는 그림 텍스트에만 쓴다.)
    """
    bad = [s for s in labels if s and _HANGUL.search(str(s))]
    if bad:
        raise ContractError(
            "그림 텍스트에 한글이 있다(하우스 규약: 그림은 전부 영어): "
            + "; ".join(repr(b) for b in bad))


# --------------------------------------------------------------------------- #
#  5) 닫는 블록 — `next_steps()` (옛 `limits()` 를 대체한다)
# --------------------------------------------------------------------------- #
def next_steps(rows: Sequence, sec: str | None = None) -> Block:
    """§5.3 **각 편의 마지막 절 — "다음 단계"**. 같은 정보를 **앞을 보며** 쓴다.

    rows: `[(다음에 할 일, 그러면 결정되는 것, 어디서), …]`

    ⭐ 가운데 칸이 이 표의 존재 이유다. **아무것도 결정하지 못하는 다음 단계는 다음 단계가 아니라
       그냥 한계 목록이다** — 그 한계 목록이 바로 폐지된 것이다(§5.3).

        ("VV/HH 2편파를 잰다", "편파 항의 크기가 수치로 확정된다", "06편 §2")
        ("기준 구를 함께 잰다", "σ 절대값의 자체 앵커가 선다",     "06편 §3")
    """
    R = _rows(rows or [], "§5.3 다음 단계", 3)
    if not R:
        raise ContractError(
            "§5.3: '다음 단계' 가 비었다.\n"
            "  → `다음에 할 일 | 그러면 결정되는 것 | 어디서` 로 한 행 이상 적어라.")
    for todo, decides, where in R:
        if not todo.strip():
            raise ContractError("§5.3: '다음에 할 일' 칸이 비었다.")
        if not decides.strip():
            raise ContractError(
                f"§5.3: '{todo}' 에 **그러면 결정되는 것**이 없다.\n"
                "  ⭐ 아무것도 결정하지 못하는 다음 단계는 다음 단계가 아니다 — 그냥 한계 목록이고,\n"
                "     그 한계 목록이 폐지된 바로 그것이다.\n"
                "  → 그 일을 하면 **무엇이 확정되는지** 적어라. "
                "예) '편파 항의 크기가 수치로 확정된다'")
        if not where.strip():
            raise ContractError(
                f"§5.3: '{todo}' 에 **어디서**가 없다 — 파일:줄 또는 '06편 §2' 처럼 적어라.\n"
                "  → 인수인계 지점이 없으면 다음 사람이 이어받을 수 없다(§5.6-5).")
        if _ends_negative(todo):
            raise ContractError(
                f"§5.3: '다음에 할 일' 칸이 **한계 서술**이다 — {todo!r}\n"
                "  → 앞을 보는 행동으로 뒤집어라.\n"
                "     '편파가 통제되지 않는다' → '실측에서 VV/HH 2편파를 잰다'\n"
                "     '다중반사를 1회까지만 본다' → '2회 반사를 켜고 이면각 오차를 다시 잰다'")
        if todo.strip() == decides.strip():
            raise ContractError(
                f"§5.3: '할 일' 과 '결정되는 것' 이 같은 문장이다 — {todo!r}")
    _assert_tone("§5.3 다음 단계", *[" ".join(r) for r in R])

    head = f"## {sec} 다음 단계" if sec else "## 다음 단계"
    L = [f"<!--rs:{TAG_NEXT}-->", head, "",
         "| 다음에 할 일 | 그러면 결정되는 것 | 어디서 |", "|---|---|---|"]
    L += [f"| {_md_escape_cell(a)} | {_md_escape_cell(b)} | {_md_escape_cell(c)} |"
          for a, b, c in R]
    return Block("\n".join(L))


def limits(*_a, **_kw) -> Block:                       # noqa: D401  (폐지된 이름의 묘비)
    """**폐지됨(2026-07-31).** `next_steps()` 를 써라. 부르면 예외가 난다.

    옛 '이 편의 한계' 절은 모든 편을 사과로 끝나게 만들었다. 같은 정보를 앞을 보며 쓴다.
    """
    raise ContractError(
        "`limits()` 는 폐지됐다(§5.3) — '이 편의 한계' 절이 모든 편을 사과로 끝나게 만들었다.\n"
        "  → `next_steps([(다음에 할 일, 그러면 결정되는 것, 어디서), …])` 로 바꿔라.\n"
        "     같은 정보를 **앞을 보며** 쓰는 것이다.\n"
        "       '편파가 미통제다'        → ('VV/HH 2편파를 잰다', '편파 항이 수치로 확정된다', '06편 §2')\n"
        "       'σ 절대값이 미검증이다'  → ('기준 구를 함께 잰다', '자체 앵커가 선다', '06편 §3')")


# --------------------------------------------------------------------------- #
#  6) 노트북 조립 — 빌더 6개가 짧고 똑같아지도록
# --------------------------------------------------------------------------- #
def md(*lines: str) -> Block:
    """마크다운 블록. 줄 하나가 `<!--cell-->` 이면 거기서 셀이 나뉜다."""
    return Block("\n".join(str(x) for x in lines), "markdown")


def code(*lines: str) -> Block:
    """코드 블록."""
    return Block("\n".join(str(x) for x in lines), "code")


def table(headers: Sequence[str], rows: Iterable[Sequence]) -> str:
    """마크다운 표. `table()` 자신은 **셀 내용을 검증하지 않는다.**

    ⚠ §5.1 은 불확실한 양을 산문이 아니라 **표에 숫자로** 넣으라고 한다. 그래서 리포트의
      숫자 대부분이 표 안에 산다. 그 칸을 손으로 치면 검증을 통째로 우회하게 된다.
      그러니 숫자 칸은 **둘 중 하나**로만 만든다.

      ① 칸마다 `num()`  — 칸을 골라 쓸 때. 칸마다 출처 태그가 붙는다.
         `table(["파형","ΔR"], [["WiFi", num(None, (J, "wifi.dR_m"), "{:.2f}", "m")]])`
      ② `table_from()`   — 행이 JSON 에 이미 배열/딕셔너리로 있을 때. 표 하나에 태그 하나.

      말(label)로만 된 표라면 `table()` 을 그냥 써도 된다.
    """
    H = [str(h) for h in headers]
    out = ["| " + " | ".join(H) + " |", "|" + "---|" * len(H)]
    for r in rows:
        cells = [_md_escape_cell(c) for c in r]
        if len(cells) != len(H):
            raise ContractError(f"표의 열 수가 안 맞는다: {cells!r} vs 머리 {H!r}")
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def table_from(source, columns: Sequence, fmt: dict | None = None,
               null: str = "미상", key_col: str | None = None,
               order: Sequence | None = None, tag: bool = True) -> str:
    """**JSON 배열/딕셔너리에서 표를 직접 뽑는다** — 표 안의 숫자도 손으로 치지 않도록.

    파라미터
    --------
    source : 표의 원본을 가리킨다. 리스트(행들) 또는 딕셔너리(키→행) 여야 한다.
             예) `"outputs/sigma_anchor.json:uncontrolled"`
    columns: `[(표머리, 필드경로), …]`. 필드경로는 각 행 **안에서**의 점 경로다.
             `key_col` 을 쓸 땐 그 열의 필드경로 자리에 `None` 을 둔다.
    fmt    : `{필드경로: "{:+.2f}"}` — 숫자 포맷.
    null   : 값이 `null` 인 칸에 쓸 말. 기본 `"미상"`.
    key_col: 딕셔너리 원본일 때, 딕셔너리 **키**를 담을 열의 머리 이름.
    order  : 넣을 키(또는 인덱스)를 직접 고르고 순서를 정한다. 기본은 원본 순서.
    tag    : 표 밑에 출처 한 줄을 붙인다. 칸마다 태그를 다는 대신 **표 하나에 태그 하나**.

    예)
        table_from("outputs/sigma_anchor.json:uncontrolled",
                   [("항목", "term"), ("상태", "status"), ("크기", "size_db")],
                   fmt={"size_db": "{:+.2f} dB"})
    """
    p, k = _split_source(source)
    node = _walk(load_json(p), k, [])[0]

    cols: list[tuple[str, Any]] = []
    for c in columns or []:
        if not (isinstance(c, (tuple, list)) and len(c) == 2):
            raise ContractError(
                f"table_from: 열은 (표머리, 필드경로) 쌍이어야 한다 — {c!r}")
        cols.append((str(c[0]), c[1]))          # 필드경로 None = 키 열
    if not cols:
        raise ContractError("table_from: 열이 하나도 없다.")

    # 원본을 (키, 행) 목록으로 정규화
    if isinstance(node, dict):
        keys = list(order) if order is not None else list(node.keys())
        items = []
        for kk in keys:
            if kk not in node:
                raise ContractError(
                    f"table_from: '{kk}' 가 {p}:{k} 에 없다. "
                    f"가능: {', '.join(map(repr, list(node)[:10]))}")
            items.append((str(kk), node[kk]))
    elif isinstance(node, (list, tuple)):
        idx = list(order) if order is not None else list(range(len(node)))
        items = [(str(i), node[int(i)]) for i in idx]
    else:
        raise ContractError(
            f"table_from: {p}:{k} 는 {type(node).__name__} 다 — 표로 뽑으려면 "
            f"리스트(행들)나 딕셔너리(키→행)여야 한다. 값 하나면 `num()` 을 써라.")

    F = dict(fmt or {})
    out = ["| " + " | ".join(str(h) for h, _ in cols) + " |",
           "|" + "---|" * len(cols)]
    for kk, row in items:
        cells = []
        for _h, field in cols:
            if field is None or (key_col is not None and _h == key_col):
                cells.append(_md_escape_cell(kk))
                continue
            v = _py(_walk(row, str(field), [f"{k}[{kk}]"])[0])
            if v is None:
                cells.append(_md_escape_cell(null))
            else:
                cells.append(_md_escape_cell(_fmt(v, F.get(str(field)))))
        out.append("| " + " | ".join(cells) + " |")
    if tag:
        out += ["", f"출처 ⟨{p} : {k}⟩"]
    return "\n".join(out)


def _to_cells(blocks: Iterable) -> list[dict]:
    cells: list[dict] = []
    for b in blocks:
        if b is None:
            continue
        if isinstance(b, Block):
            kind, text = b.kind, str(b)
        elif isinstance(b, str):                              # 맨 문자열 = 마크다운
            kind, text = "markdown", b
        elif isinstance(b, dict) and "cell_type" in b:        # 이미 만들어진 셀
            cells.append(b)
            continue
        elif isinstance(b, (tuple, list)) and len(b) == 2:
            kind, text = str(b[0]).lower(), str(b[1])
        else:
            raise ContractError(
                f"블록은 md(…) / code(…) / 문자열 이어야 한다 — {type(b).__name__}: {b!r}")
        if kind.startswith("m"):
            segs = re.split(rf"^\s*{re.escape(BREAK)}\s*$", text, flags=re.M)
        else:
            segs = [text]
        for seg in segs:
            seg = seg.strip("\n")
            if not seg.strip():
                continue
            meta: dict = {}
            m = _TAG_RE.match(seg)
            if m:
                meta["tags"] = [m.group(1)]
                seg = seg[m.end():]
            src = seg.splitlines(keepends=True)
            if kind.startswith("m"):
                cells.append({"cell_type": "markdown", "metadata": meta, "source": src})
            else:
                cells.append({"cell_type": "code", "metadata": meta,
                              "execution_count": None, "outputs": [], "source": src})
    return cells


# --------------------------------------------------------------------------- #
#  6b) 출처를 각주로 — 화면 글자의 37.9%가 출처 태그였다
#      본문의 `값 ⟨outputs/x.json : key⟩` 를 `값[^7]` 로 바꾸고, 편 끝에 «출처» 표를 붙인다.
#      ⭐ 검증은 1비트도 안 약해진다 — `num()` 이 이미 JSON 을 열어 값을 대조했고,
#         여기서 **한 번 더** 열어 각주 표의 값을 채운다(왕복 검사). 키가 안 풀리면 빌드가 멈춘다.
#      같은 (파일, 키) 는 같은 번호다 — 재인용이 번호를 새로 먹지 않는다.
# --------------------------------------------------------------------------- #
#: `⟨outputs/x.json : a.b.c⟩` 를 경로와 키로 가른다.
_PROV_PARTS = re.compile(r"⟨\s*([^⟩:]+?\.(?:json|npz))\s*:\s*([^⟩]+?)\s*⟩")

#: 각주 번호 표시. 본문에서 출처 태그를 대신한다.
_FOOTMARK = re.compile(r"\[\^(\d+)\]")


def _foot_value(v: Any) -> str:
    """각주 표의 «값» 칸. 스칼라는 그대로, 묶음은 크기만 적는다(본문에 붓지 않는다)."""
    v = _py(v)
    if v is None:
        return "null"
    if isinstance(v, dict):
        return f"({len(v)}항목 묶음)"
    if isinstance(v, (list, tuple)) or getattr(v, "ndim", 0):
        n = len(v) if hasattr(v, "__len__") else "?"
        return f"({n}행 표)"
    s = _auto_fmt(v)
    return s if len(s) <= 56 else s[:55].rstrip() + "…"


def _resolve_cite(path: str, key: str) -> str:
    """출처 하나를 **다시 열어** 각주 표의 «값» 칸을 만든다. 못 열면 `ContractError`.

    키에는 두 가지 파생 표기가 섞여 있다 — 둘 다 «어느 칸에서 왔나» 를 그대로 적은 것이다.
      `a.b → 15칸 평균`   기준 키를 연 뒤 사람이 한 연산. **기준 키까지는 검사한다.**
      `ranges.*.*.R90_m`  기체·밴드를 가로지르는 칸 묶음. 파일이 열리는지까지 검사한다.
    """
    base = key.split("→")[0].strip()
    doc = load_json(path)                       # 파일이 없으면 여기서 터진다
    if "*" in base:
        return "(여러 칸)"
    # ⭐한 태그가 **여러 칸**을 가리키는 두 표기 — « · » 로 이은 여러 키, «[]» 로 가리킨 배열
    #   전체. 값은 하나로 못 적지만, **키가 실재하는지는 전부 검사한다**(그냥 통과시키면
    #   태그가 낡아도 안 잡힌다).
    if " · " in base or "[]" in base:
        for seg in base.split(" · "):
            seg = seg.strip()
            if not seg or "*" in seg:
                continue
            head, _, tail = seg.partition("[]")
            node = _walk(doc, head, [])[0] if head else doc
            if tail:                             # «pairs[].필드» — 첫 원소에서 이어 걷는다
                if not hasattr(node, "__len__") or isinstance(node, dict) or not len(node):
                    raise ContractError(f"«{head}[]» 가 비었거나 배열이 아니다")
                _walk(node[0], tail.lstrip("."), [])
        return "(여러 칸)"
    v = _foot_value(_walk(doc, base, [])[0])
    return f"{v} (파생)" if base != key.strip() else v


def _footnote_pass(cells: list[dict]) -> list[dict]:
    """마크다운 셀의 출처 태그 → 각주 번호. 편 끝에 «출처» 표 셀을 붙여 돌려준다.

    태그가 하나도 없으면 아무것도 하지 않는다(옛 노트북·표지 편이 그렇다).
    """
    order: list[tuple[str, str]] = []
    seen: dict[tuple[str, str], int] = {}

    def _mark(m: re.Match) -> str:
        key = (m.group(1).strip(), m.group(2).strip())
        n = seen.get(key)
        if n is None:
            order.append(key)
            n = seen[key] = len(order)
        return f"[^{n}]"

    out: list[dict] = []
    for c in cells:
        if c.get("cell_type") != "markdown":
            out.append(c)
            continue
        text = _cell_text(c)
        if "⟨" in text:
            text = _PROV_PARTS.sub(_mark, text)
            # ⚠ `[^7](mavic4pro)` 는 마크다운이 **링크로 읽는다**. 한 칸 띄워 끊는다.
            text = re.sub(r"(\[\^\d+\])\(", r"\1 (", text)
            c = dict(c, source=text.splitlines(keepends=True))
        out.append(c)

    if not order:
        return out

    rows = []
    for n, (p, k) in enumerate(order, 1):
        try:                       # ⭐ 왕복 검사 — 각주 표의 값은 JSON 을 **다시 읽어** 채운다
            shown = _resolve_cite(p, k)
        except ContractError as e:
            raise ContractError(
                f"각주 {n} 의 출처를 다시 열 수 없다 — ⟨{p} : {k}⟩\n  {e}\n"
                f"  → 태그의 파일·키를 고쳐라. 못 여는 출처는 출처가 아니다.") from None
        rows.append(f"| [^{n}] | `{_md_escape_cell(p)}` | `{_md_escape_cell(k)}` | "
                    f"{_md_escape_cell(shown)} |")

    body = "\n".join(
        [f"<!--rs:{TAG_SOURCES}-->",
         "## 출처", "",
         f"본문의 `[^n]` 은 아래 {len(order)}개 중 하나를 가리킨다. 값은 이 표를 만들 때 "
         f"JSON 을 다시 열어 채웠다 — 본문 숫자와 같은 파일, 같은 키다.", "",
         "| | 파일 | 키 | 값 |", "|---|---|---|---|"] + rows)
    out.append({"cell_type": "markdown", "metadata": {"tags": [TAG_SOURCES]},
                "source": body.splitlines(keepends=True)})
    return out


def build_notebook(path: str, blocks: Iterable, kernel: dict | None = None,
                   strict: bool = False, quiet: bool = False) -> dict:
    """블록 리스트 → `.ipynb` 파일. 쓰고 나서 §5.7 예산 + §5.8 톤을 검사해 결과를 돌려준다.

    strict=True 면 위반 시 **예외**(파일은 이미 쓰인 뒤이므로 확인 후 고치면 된다).
    """
    cells = _footnote_pass(_to_cells(blocks))
    nb = {"cells": cells,
          "metadata": {"kernelspec": kernel or KERNEL,
                       "language_info": {"name": "python"}},
          "nbformat": 4, "nbformat_minor": 5}
    p = path if os.path.isabs(path) else os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)

    rep = check_budget(p)
    if not quiet:
        print(_budget_text(rep))
    if strict and not rep["ok"]:
        raise ContractError(
            f"규약 위반 — {rep['path']}\n  "
            + "\n  ".join(rep["violations"])
            + "\n  → 톤이면 **주장의 크기를 맞춰라**(§5.0). ⛔분량으로 편을 쪼개지 마라.")
    return rep


# --------------------------------------------------------------------------- #
#  7) 한 번에 다 보는 검사 — `check_budget()`
#     구조(여는 블록·다음 단계) + 분량(§5.7) + 톤(§5.8) 을 한 함수가 본다.
# --------------------------------------------------------------------------- #
_FIG_CAP = re.compile(r"^\s*\*\*(?:그림|Figure)\s*([0-9]+(?:[.\-][0-9]+)?)\s*[.)]", re.M)
_SAVEFIG = re.compile(r"\b(?:savefig|plt\.show)\s*\(")
#: 리포트는 미리 그려둔 PNG 를 마크다운으로 끼워 넣는다 — 그것도 '그림'으로 센다.
_MD_IMG = re.compile(r"!\[[^\]]*\]\(\s*([^)\s]+)[^)]*\)|<img[^>]+src=[\"']([^\"']+)[\"']")
_PROV = re.compile(r"⟨[^⟩]+?\.(?:json|npz)\s*:\s*[^⟩]+⟩")
#: 출처 한 개 — 옛 표기(⟨…⟩)와 각주 표기(`[^7]`) 둘 다. 각주는 렌더만 바뀐 같은 물건이다.
_CITE = r"(?:⟨[^⟩]+?\.(?:json|npz)\s*:\s*[^⟩]+⟩|\[\^\d+\])"
#: 출처 표시 **와 그 앞의 값**(단위 포함)을 통째로 지운다 — 그 숫자는 손으로 친 게 아니다.
#  ⚠ 단위에 한글이 붙는 자리(`296 개[^3]`)까지 함께 잡는다.
_PROV_VALUE = re.compile(r"[-+]?[\d][\d,.eE+\-]*\s*"
                         r"(?:[%°]|[A-Za-z·/]{0,8}|[가-힣]{1,3})?\s*" + _CITE)
# 산문 속 '손으로 친 숫자' 후보 — 소수점이 있거나 3자리 이상. §·그림·리포트 번호 등은 뺀다.
_BARE_NUM = re.compile(r"(?<![\w.\-/])(\d+\.\d+|\d{3,})(?![\w.])")
_YEAR = re.compile(r"^(?:19|20)\d{2}$")          # 인용 연도는 손으로 적는 게 맞다

#: `table_from()` 이 표 밑에 붙이는 출처 한 줄. 그 표의 숫자는 JSON 에서 뽑은 것이다.
#  각주로 바뀐 뒤에도 같은 줄이다 — 표기만 `출처 [^7]` 로 달라진다.
_TABLE_SRC = re.compile(r"^\s*출처\s*" + _CITE + r"(?:\s*[·,]\s*" + _CITE + r")*\s*$")

#: 폐지된 옛 계약의 흔적 — 남아 있으면 위반이고, 무엇으로 바꾸는지 알려준다.
_LEGACY_MARKS = [
    ("주장하지 않는 것", "옛 '주장/비주장' 표(§5.0 폐지) — `header(method=…)` 로 대체"),
    ("이 편의 한계", "옛 '이 편의 한계' 절(§5.3 폐지) — `next_steps()` 로 대체"),
    ("이 편이 답하는 질문", "옛 '질문' 여는 블록(§5.2 폐지) — `header(did=…)` 로 대체"),
]


def _strip_sourced_tables(text: str) -> str:
    """출처 태그가 달린 표(= `table_from()` 산출물)의 행을 지운다.

    그 칸의 숫자는 손으로 친 것이 아니라 JSON 에서 뽑은 것이므로 '출처 없는 숫자'
    검사 대상이 아니다. 반면 손으로 친 `table()` 은 태그가 없으니 그대로 걸린다.
    """
    lines = text.splitlines()
    drop: set[int] = set()
    for i, ln in enumerate(lines):
        if not _TABLE_SRC.match(ln):
            continue
        drop.add(i)
        j = i - 1
        while j >= 0 and not lines[j].strip():        # 표와 태그 사이 빈 줄
            drop.add(j)
            j -= 1
        while j >= 0 and lines[j].lstrip().startswith("|"):
            drop.add(j)
            j -= 1
    return "\n".join(ln for i, ln in enumerate(lines) if i not in drop)


def _has_tag(c: dict, tag: str) -> bool:
    return tag in (c.get("metadata", {}).get("tags") or [])


def check_budget(nb_path: str) -> dict:
    """구조 + 분량(§5.7) + 톤(§5.8) 을 한 번에 검사한다.

    반환: dict(md_cells, code_cells, figures, negatives[], hedges[], violations[],
               advisories[], ok, …)

    분량 — **줄 수**는 빈 줄을 뺀 실질 줄로 센다(표 위아래 빈 줄 때문에 억울하게 걸리지 않도록).
      여는 블록·다음 단계는 **구조 블록**이라 줄 수 상한에서 면제된다. 다만 셀 수엔 포함된다.
      그림 수는 ①캡션 ②마크다운 이미지 ③`savefig`·`plt.show` ④저장된 이미지 출력 중 **최대**.
      끼워 넣은 PNG 가 **디스크에 없으면 위반**이다 — 깨진 그림 링크는 인수인계 실패다.

    톤 — 부정문 3개 초과 · 완충어 1건 이상은 **위반**이고, 걸린 문장이 그대로 실려 나온다.
      ⭐ 권고가 아니다. 오탐의 대가는 문장 하나 다시 쓰기이고, 미탐의 대가는 사용자가
        거부한 그 산문이 그대로 나가는 것이다.

    권고 — 출처 태그 없는 숫자, 과정 서사(오탐이 있어 advisories 로만 알린다).
    """
    p = nb_path if os.path.isabs(nb_path) else os.path.join(ROOT, nb_path)
    if not os.path.exists(p):
        raise ContractError(f"검사할 노트북이 없다: {nb_path} (기대 경로: {p})")
    with open(p, encoding="utf-8") as f:
        nb = json.load(f)
    cells = nb.get("cells", [])

    md_cells = [c for c in cells if c.get("cell_type") == "markdown"]
    code_cells = [c for c in cells if c.get("cell_type") == "code"]

    fig_ids, savefigs, img_outs, prov_tags = set(), 0, 0, 0
    md_imgs: list[str] = []
    missing_imgs: list[str] = []
    offenders, advisories = [], []

    for i, c in enumerate(cells):
        t = _cell_text(c)
        if c.get("cell_type") == "markdown":
            fig_ids |= set(_FIG_CAP.findall(t))
            for a, b in _MD_IMG.findall(t):
                src = a or b
                md_imgs.append(src)
                if src.startswith(("http", "data:")):
                    continue
                # 노트북 위치 기준, 없으면 리포지토리 루트 기준으로도 찾아본다.
                # ⭐2026-08-10 세 번째 후보 — **권 디렉터리(reports/)** 기준.
                #   조각은 `reports/_parts/` 에 살지만 그 셀은 권(`reports/`)으로 옮겨져 읽히므로
                #   그림 경로 `../outputs/figures/…` 는 **권 기준으로 옳다.** 조각 자기 위치에서는
                #   한 층 모자라 깨져 보이는데, 그것은 조각을 직접 열지 않는다는 전제의 자연스러운
                #   결과다. 셋 중 하나라도 있으면 통과시킨다.
                cands = ([src] if os.path.isabs(src)
                         else [os.path.join(os.path.dirname(p), src),
                               os.path.join(ROOT, src),
                               os.path.join(ROOT, "reports", src)])
                if not any(os.path.exists(x) for x in cands):
                    missing_imgs.append(f"셀 {i}: {src}")
            if _has_tag(c, TAG_SOURCES):
                continue          # 각주 원장 — 인용이 아니라 인용의 목록이다(아래 검사 전부 면제)
            prov_tags += len(_PROV.findall(t)) + len(_FOOTMARK.findall(t))
            exempt = (_has_tag(c, TAG_HEADER) or _has_tag(c, TAG_NEXT)
                      or _has_tag(c, TAG_LIMITS) or _has_tag(c, TAG_PAPER))
            if not exempt and ("| ✅" in t or "다음에 할 일" in t):   # 태그 없는 손편집 대비
                exempt = True
            n_lines = sum(1 for ln in t.splitlines() if ln.strip())
            if not exempt and n_lines > MAX_LINES_PER_CELL:
                offenders.append(dict(cell=i, lines=n_lines,
                                      head=t.strip().splitlines()[0][:60]))
            # 출처 없는 숫자 — 위반이 아니라 권고(단위·§번호 오탐이 있으므로)
            stripped = _strip_sourced_tables(t)       # table_from() 표는 검증됨
            stripped = _PROV_VALUE.sub("", stripped)
            stripped = _PROV.sub("", stripped)
            stripped = re.sub(r"`[^`]*`", "", stripped)      # 코드·경로 안의 숫자는 제외
            bare = [b for b in _BARE_NUM.findall(stripped) if not _YEAR.match(b)]
            if bare:
                advisories.append(
                    f"셀 {i}: 출처 태그 없는 숫자 {sorted(set(bare))[:5]} "
                    f"— `num()` 으로 바꿀 것인지 확인 (§5.6-1)")
            for h in lint_prose(t)[:3]:          # §5.5 과정 서사(권고)
                advisories.append(f"셀 {i}: {h}")
        else:
            savefigs += len(_SAVEFIG.findall(t))
            for o in c.get("outputs", []) or []:
                if any(k.startswith("image/") for k in (o.get("data") or {})):
                    img_outs += 1

    figures = max(len(fig_ids), savefigs, img_outs, len(md_imgs))

    all_md = "\n".join(_cell_text(c) for c in md_cells
                       if not _has_tag(c, TAG_SOURCES))
    has_header = any(_has_tag(c, TAG_HEADER) for c in md_cells) or "### 한 일" in all_md
    has_next = (any(_has_tag(c, TAG_NEXT) for c in md_cells)
                or "다음에 할 일" in all_md)

    # ── §5.8 톤 검사 — 위반이다(권고가 아니다) ────────────────────────────────
    neg = count_negatives(cells)
    hed = grep_hedges(cells)

    V = []
    # 분량(§5.7)
    if MAX_MD_CELLS is not None and len(md_cells) > MAX_MD_CELLS:
        V.append(f"마크다운 셀 {len(md_cells)}개 > 상한 {MAX_MD_CELLS}")
    for o in offenders:
        V.append(f"셀 {o['cell']} 이 {o['lines']}줄 > 상한 {MAX_LINES_PER_CELL} "
                 f"— \"{o['head']}\"")
    if figures > MAX_FIGURES:
        V.append(f"그림 {figures}개 > 상한 {MAX_FIGURES}")
    for mi in missing_imgs:                    # 깨진 그림 링크 = 인수인계 실패
        V.append(f"그림 파일이 없다 — {mi}")
    if md_imgs and len(fig_ids) < len(set(md_imgs)):
        advisories.append(
            f"그림 {len(set(md_imgs))}개 중 캡션이 {len(fig_ids)}개뿐 "
            f"— 모든 그림에 `caption()` 한 줄 (§5.6-2)")

    # 구조
    if not has_header:
        V.append("필수 블록 없음: 여는 블록(한 일/결과/방법/재현) — `header()` 를 쓸 것")
    if not has_next:
        V.append("필수 블록 없음: 마지막 절 '다음 단계' — `next_steps()` 를 쓸 것")
    for mark, why in _LEGACY_MARKS:                  # 폐지된 옛 계약의 흔적
        if mark in all_md:
            V.append(f"폐지된 블록이 남아 있다: '{mark}' — {why}")

    # 순서: 여는 블록은 맨 앞(§5.2), 다음 단계는 맨 뒤(§5.3).
    if has_header and cells and not _has_tag(cells[0], TAG_HEADER) \
            and "### 한 일" not in _cell_text(cells[0]):
        V.append("여는 블록이 맨 앞이 아니다(§5.2) — `header()` 를 첫 블록으로")
    if has_next:
        tail = [j for j, c in enumerate(cells)
                if _has_tag(c, TAG_NEXT) or "다음에 할 일" in _cell_text(c)]
        if tail and tail[-1] < len(cells) - 2:
            V.append(f"'다음 단계' 가 마지막이 아니다(§5.3) — "
                     f"셀 {tail[-1]}/{len(cells) - 1}")

    # 톤(§5.8) — 걸린 문장을 그대로 실어 보낸다. 세기만 하면 고칠 수가 없다.
    if not neg["ok"]:
        V.append(f"부정문 {neg['count']}개 > 상한 {MAX_NEGATIVES} (§5.8-1) — "
                 "무엇을 **했는지**로 다시 써라:\n      "
                 + "\n      ".join(f"셀 {h['cell']}: \"{h['text']}\""
                                   for h in neg["sentences"][:6])
                 + (f"\n      … 외 {neg['count'] - 6}건"
                    if neg["count"] > 6 else ""))
    if not hed["ok"]:
        V.append(f"완충어 {hed['count']}건 (§5.8-3 은 0건이다) — "
                 "표현이 아니라 **주장의 크기**를 고쳐라:\n      "
                 + "\n      ".join(f"셀 {h['cell']}: '{h['hedge']}' → {h['fix']}"
                                   f"\n        \"{h['text'][:70]}\""
                                   for h in hed["hits"][:6])
                 + (f"\n      … 외 {hed['count'] - 6}건"
                    if hed["count"] > 6 else ""))

    shown = os.path.relpath(p, ROOT)
    if shown.startswith(".."):
        shown = p                       # 리포지토리 밖(스크래치패드 등)이면 절대경로 그대로
    return dict(path=shown, md_cells=len(md_cells),
                code_cells=len(code_cells), figures=figures,
                fig_captions=len(fig_ids), savefig_calls=savefigs,
                image_outputs=img_outs, md_images=len(md_imgs),
                missing_images=missing_imgs, provenance_tags=prov_tags,
                caps=dict(md_cells=MAX_MD_CELLS, lines_per_cell=MAX_LINES_PER_CELL,
                          figures=MAX_FIGURES, negatives=MAX_NEGATIVES,
                          hedges=MAX_HEDGES),
                negatives=neg["sentences"], n_negatives=neg["count"],
                hedges=hed["hits"], n_hedges=hed["count"],
                offenders=offenders, advisories=advisories,
                violations=V, ok=not V)


def _budget_text(rep: dict) -> str:
    mark = "✅" if rep["ok"] else "⛔"
    s = (f"{mark} {rep['path']} — 마크다운 {rep['md_cells']}셀 · "
         f"코드 {rep['code_cells']}셀 · 그림 {rep['figures']}/{MAX_FIGURES} · "
         f"출처태그 {rep['provenance_tags']}개 · "
         f"부정문 {rep['n_negatives']}/{MAX_NEGATIVES} · 완충어 {rep['n_hedges']}/0")
    for v in rep["violations"]:
        s += f"\n   ⛔ {v}"
    for a in rep["advisories"][:5]:
        s += f"\n   ⚠ {a}"
    if len(rep["advisories"]) > 5:
        s += f"\n   ⚠ … 권고 {len(rep['advisories']) - 5}건 더"
    return s


def budget_report(nb_paths: Iterable[str]) -> str:
    """여러 편을 한 번에 검사해 사람이 읽을 표로. 재편 후 전체 점검용."""
    lines = ["| 리포트 | md셀 | 코드셀 | 그림 | 출처태그 | 부정문 | 완충어 | 판정 |",
             "|---|---|---|---|---|---|---|---|"]
    tot_md = tot_fig = tot_neg = tot_hed = 0
    for p in nb_paths:
        r = check_budget(p)
        tot_md += r["md_cells"]
        tot_fig += r["figures"]
        tot_neg += r["n_negatives"]
        tot_hed += r["n_hedges"]
        verdict = "✅" if r["ok"] else "⛔ " + "; ".join(
            v.splitlines()[0] for v in r["violations"])
        lines.append(
            f"| `{r['path']}` | {r['md_cells']} | {r['code_cells']} "
            f"| {r['figures']}/{MAX_FIGURES} | {r['provenance_tags']} "
            f"| {r['n_negatives']}/{MAX_NEGATIVES} | {r['n_hedges']}/0 | {verdict} |")
    lines.append(f"| **합계** | **{tot_md}** |  | **{tot_fig}** |  "
                 f"| **{tot_neg}** | **{tot_hed}** |  |")
    return "\n".join(lines)


def tone_report(nb_path: str) -> str:
    """한 편의 톤 위반을 **고칠 수 있는 형태**로 나열한다 — 문장 그대로 + 어디를 고칠지."""
    r = check_budget(nb_path)
    out = [f"── {r['path']} — 부정문 {r['n_negatives']}/{MAX_NEGATIVES} · "
           f"완충어 {r['n_hedges']}/0 ──"]
    for h in r["negatives"]:
        out.append(f"  [부정문 {h['ending']}] 셀 {h['cell']}: {h['text']}")
    for h in r["hedges"]:
        out.append(f"  [완충어 {h['hedge']}] 셀 {h['cell']}: {h['text'][:90]}")
        out.append(f"      → {h['fix']}")
    if len(out) == 1:
        out.append("  (없음)")
    return "\n".join(out)


# --------------------------------------------------------------------------- #
#  8) 데모 · 자기검사 — `python src/report_style.py`
# --------------------------------------------------------------------------- #
def _demo_blocks():
    """규약을 통과하는 여는 블록 한 벌. 여섯 빌더가 그대로 베껴 쓸 견본이다."""
    S = from_json("outputs/sbr_kr_sweep.json")

    return [
        header(
            num=2,
            title="표적 모델: 메쉬 · 엔진 · 앵커",
            did="드론 메쉬에 광선추적 가림과 부품별 재질 PO 를 적용해 RCS 를 계산하고, "
                "레벨과 밴드 기울기를 Das 측정에 맞췄다.",
            results=[
                f"해석 PO 구 대비 최대 편차 "
                f"{S.num('summary_div16.max_abs_db_vs_po', 0.201, '{:.3f}', 'dB')}"
                f"(kr {S.num('summary_div16.n_points', 21, '{:.0f}')}점 × 입사 "
                f"{S.num('meta.n_incidence', 48, '{:.0f}')}방향, kr=1 까지 포함).",
                f"kr≥30 에서 해석 PO 대비 산포는 "
                f"{S.num('summary_div16.std_sbr_over_po_pct_kr_ge30', 0.885, '{:.3f}', '%')} 다.",
                "자세 패턴은 기하에서 계산했다 — 부품별 재질 + 광선추적 가림.",
                "레벨과 밴드 기울기는 Das 측정(IEEE WCL 2026 15:3731)에 맞췄다.",
            ],
            method=[
                ("자세 패턴", "Sionna 의 Mitsuba/OptiX 로 first-hit 가림, 조명면에 PO 적분"),
                ("절대 레벨", "Das 측정에 σ = A(f)B1(φ)B2 분해로 맞춤 — B1 은 우리 계산 그대로"),
                ("엔진 검증", "해석 PO 구 · PEC 이면각 해석해와 대조"),
            ],
            prereq=[("01 §3", "게재 선행이 표적 산란을 어떻게 다뤘는지")],
            repro=dict(cmd="PYTHONPATH=src ~/.venvs/py312/bin/python "
                           "benchmark/verify_sbr_kr_sweep.py",
                       out="outputs/sbr_kr_sweep.json",
                       runtime="(재현 시 측정해 채울 것)"),
            allow_missing_output=False,
        ),
        md("## §1. 기하가 주는 것과 측정이 주는 것", "",
           "기하는 **구조**를, 측정은 **레벨**을 준다. 경계는 아래 표가 전부다.", "",
           # 말(label)로만 된 표는 table() 로 충분하다.
           table(["축", "어디서 오나", "근거"],
                 [["자세 구조", "기하(SBR+PO)", "본 편 §2"],
                  ["절대 레벨", "측정 앵커", "Das, IEEE WCL 2026"],
                  ["밴드 기울기", "측정 앵커", "Das, IEEE WCL 2026"]])),

        # ⭐ 숫자가 들어가는 표는 **JSON 에서 직접 뽑는다** — 손으로 치면 검증을 우회한다.
        md("## §4. 앵커가 통제한 항목과 그 크기", "",
           "불확실한 양은 산문이 아니라 **표에 숫자로** 넣는다(§5.1).", "",
           table_from("outputs/sigma_anchor.json:uncontrolled",
                      [("항목", "term"), ("상태", "status"),
                       ("크기", "size_db")],
                      fmt={"size_db": "{:+.2f} dB"}, null="미상")),
        # 그림은 viz 스크립트가 미리 만든 PNG 를 끼우고 바로 밑에 캡션 한 줄.
        md("![sbr validate](outputs/figures/report2_sbr_validate.png)", "",
           caption(1, "SBR 이 해석 PO 와 몇 dB 안에서 일치하는가?")),
        # 코드 셀이 필요하면 이렇게. 그림 글자는 영어 — assert_fig_text 로 확인한다.
        code("from report_style import assert_fig_text",
             "assert_fig_text('RCS [dBsm]', 'kr = 2*pi*r/lambda')"),
        next_steps([
            ("등가 모서리 전류(PTD)를 넣는다",
             "밴드 기울기가 기하만으로 서는지 결정된다",
             "`src/rcs_sbr.py` → 02편 §3 재측정"),
            ("VV/HH 2편파를 잰다", "편파 항의 크기가 수치로 확정된다", "06편 §2 측정 설계"),
        ], sec="§9."),
    ]


def _selftest() -> int:
    """규약 장치가 **실제로 막는지** 확인한다. 막지 못하는 장치는 장치가 아니다."""
    OUT = "outputs/sbr_kr_sweep.json"
    ok_repro = dict(cmd="x", out=OUT)
    base = dict(num=1, title="t", results=["a1", "b2", "c3"],
                method=[("a", "b"), ("c", "d")], repro=ok_repro)

    def H(**kw):
        return header(**{**base, "did": "무엇을 했다", **kw})

    cases = [
        # ── 새 계약이 뒤집은 지점 ─────────────────────────────────────────
        ("⭐ 한 일이 질문이다(옛 계약의 역전)",
         lambda: H(did="무엇을 믿어도 되는가?")),
        ("⭐ 옛 인자 question= 을 부름",
         lambda: header(num=1, title="t", question="q?",
                        conclusion_lines=["a1", "b2", "c3"],
                        claims=["c"], non_claims=["n"], repro=ok_repro)),
        ("⭐ 옛 인자 claims/non_claims 를 부름",
         lambda: header(num=1, title="t", did="했다", results=["a1", "b2", "c3"],
                        claims=["c"], non_claims=["n"], repro=ok_repro)),
        ("⭐ limits() 는 폐지됨",
         lambda: limits([("a", "b")])),
        ("한 일이 비었음", lambda: H(did="")),
        ("한 일이 완료형이 아님", lambda: H(did="RCS 계산")),
        ("한 일이 부정문", lambda: H(did="절대 σ 를 주장하지 않는다")),
        ("한 일이 두 문장", lambda: H(did="계산했다. 그리고 맞췄다.")),
        ("결과 2줄(3~5줄 위반)", lambda: H(results=["a1", "b2"])),
        ("결과에 숫자 없음", lambda: H(results=["가", "나", "다"])),
        ("⭐ 결과가 부정문 투성이",
         lambda: H(results=["절대 σ 는 검증되지 않는다", "편파는 통제하지 못한다",
                            "편차 0.2 dB 다"])),
        ("방법이 1줄", lambda: H(method=["한 줄뿐"])),
        ("⭐ 여는 블록에 완충어",
         lambda: H(results=["편차는 0.2 dB 라고 볼 수 있다", "b2", "c3"])),
        ("⭐ 여는 블록에 '잠정적'",
         lambda: H(method=[("a", "이 결론은 잠정적이다"), ("c", "d")])),
        ("재현 출력 JSON 이 없음", lambda: H(repro=dict(cmd="x", out="outputs/없는파일.json"))),
        # ── 다음 단계 ────────────────────────────────────────────────────
        ("⭐ 다음 단계에 '결정되는 것' 이 없음",
         lambda: next_steps([("PTD 를 넣는다", "", "src/rcs_sbr.py")])),
        ("다음 단계에 '어디서' 가 없음",
         lambda: next_steps([("PTD 를 넣는다", "기울기가 결정된다", "")])),
        ("⭐ 다음 단계가 한계 서술이다",
         lambda: next_steps([("편파가 통제되지 않는다", "편파 항이 확정된다", "06편")])),
        ("다음 단계가 2열뿐(옛 limits 형식)",
         lambda: next_steps([("PTD 를 넣는다", "기울기가 결정된다")])),
        ("다음 단계가 빔", lambda: next_steps([])),
        ("다음 단계에 완충어",
         lambda: next_steps([("아마도 PTD 를 넣는다", "기울기가 결정된다", "06편")])),
        # ── 출처 검증(그대로 유지) ────────────────────────────────────────
        ("⭐ 숫자가 출처와 다름",
         lambda: num(0.5, f"{OUT}:summary_div16.max_abs_db_vs_po", "{:.3f}")),
        ("출처 키가 없음", lambda: num(None, f"{OUT}:summary_div16.없는키")),
        ("출처 파일이 없음", lambda: num(None, "outputs/없는파일.json:a")),
        ("배열을 통째로 인용(값 하나여야 함)", lambda: num(None, f"{OUT}:meta.kr_ladder")),
        ("딕셔너리를 통째로 인용", lambda: num(None, f"{OUT}:summary_div16")),
        ("캡션이 질문이 아님", lambda: caption(1, "SBR 과 PO 의 비교.")),
        ("캡션에 질문 2개", lambda: caption(1, "A 인가? B 인가?")),
        ("그림 텍스트에 한글", lambda: assert_fig_text("RCS [dBsm]", "입사각")),
        ("⭐ null 을 숫자처럼 인용(미해소 항목)",
         lambda: num(None, "outputs/sigma_anchor.json:uncontrolled[0].size_db",
                     "{:.2f}", "dB")),
        ("table_from 에 값 하나를 줌",
         lambda: table_from(f"{OUT}:meta.n_incidence", [("a", "b")])),
        ("table_from 에 없는 키",
         lambda: table_from("outputs/sigma_anchor.json:drones",
                            [("기체", None), ("없는필드", "존재하지_않음")])),
        ("검사할 노트북이 없음", lambda: check_budget("outputs/없는노트북.ipynb")),
    ]
    print("── 자기검사: 규약 위반이 실제로 막히는가 ──")
    bad = 0
    for name, fn in cases:
        try:
            fn()
        except ContractError as e:
            print(f"  ✅ 막힘  {name}  — {str(e).splitlines()[0][:70]}")
        else:
            bad += 1
            print(f"  ❌ 안 막힘 {name}")

    print("── 자기검사: 정상 입력은 통과하는가 ──")
    for name, fn in [
        ("정상 header(한 일/결과/방법/재현)", lambda: H()[:24].replace("\n", " ")),
        ("방법을 줄글 목록으로", lambda: H(method=["기하로 계산했다", "레벨은 측정에 맞췄다"])[:24]),
        ("결과에 부정문 1개는 허용",
         lambda: H(results=["게재 전례가 없다", "편차 0.2 dB 다", "c3"])[:24]),
        ("정상 next_steps", lambda: next_steps(
            [("2편파를 잰다", "편파 항이 수치로 확정된다", "06편 §2")])[:24]),
        ("정상 num(값 대조)",
         lambda: num(0.201, f"{OUT}:summary_div16.max_abs_db_vs_po", "{:.3f}", "dB")),
        ("정상 num(값 생략 → JSON 에서 읽음)",
         lambda: num(None, f"{OUT}:meta.n_incidence", "{:.0f}")),
        ("점 들어간 키 해석",
         lambda: num(None, "outputs/rcs_anchor.json:meta.bands.5G 3.5 GHz", "{:.3e}", "Hz")),
        ("리스트 인덱싱", lambda: num(None, f"{OUT}:meta.kr_ladder[0]")),
        ("npz 인용", lambda: num(None, "outputs/detection_arrays.npz:W1_Rb[0]", "{:.2f}", "m")),
        ("정상 캡션", lambda: caption(2, "밴드마다 기울기가 얼마나 다른가?")),
        ("영어 그림 텍스트", lambda: assert_fig_text("RCS [dBsm]", "Incidence angle [deg]")),
        ("null 을 '미상' 으로 명시",
         lambda: num(None, "outputs/sigma_anchor.json:uncontrolled[0].size_db",
                     if_null="미상")),
    ]:
        try:
            r = fn()
        except Exception as e:                                   # noqa: BLE001
            bad += 1
            print(f"  ❌ 정상인데 터짐 {name}: {str(e).splitlines()[0][:70]}")
        else:
            print(f"  ✅ 통과  {name}  → {r if isinstance(r, str) else ''}")

    # ── §5.8 톤 검사가 실제로 잡는가 ────────────────────────────────────────
    print("── 자기검사: §5.8 톤 검사 ──")
    neg_txt = ("절대 σ 가 맞다고 주장하지 않는다. 편파는 통제하지 못한다.\n"
               "| 항목 | 이 값은 검증되지 않는다 |\n"
               "다중반사는 2회까지 보지 않는다.")
    neg = count_negatives(neg_txt)
    if neg["count"] == 4 and not neg["ok"] and len(neg["sentences"]) == 4:
        print(f"  ✅ 통과  부정문 {neg['count']}개 검출(표 안 문장 포함) · 상한 초과 판정")
    else:
        bad += 1
        print(f"  ❌ 부정문 검사: {neg}")
    if count_negatives("자세 패턴은 기하에서 계산했다. 레벨은 Das 측정에 맞췄다.")["count"]:
        bad += 1
        print("  ❌ 부정문 검사 오탐 — 정상 문장을 잡았다")
    else:
        print("  ✅ 통과  부정문 검사 — 크기를 맞춘 문장은 통과")

    hedge_txt = ("정확하다고 볼 수 있다. 대체로 맞는 편이다. 어느 정도 차이가 난다. "
                 "아마 그럴 것이다. 아쉽게도 못 쟀다. 불행히도 자료가 적다. "
                 "다만 유의할 점은 편파다. 이 결론은 잠정적이다.")
    hed = grep_hedges(hedge_txt)
    if hed["count"] >= 8 and not hed["ok"]:
        print(f"  ✅ 통과  완충어 {hed['count']}건 검출(9종 전부) · 0건 규칙 위반 판정")
    else:
        bad += 1
        print(f"  ❌ 완충어 검사가 못 잡았다: {[h['hedge'] for h in hed['hits']]}")
    if grep_hedges("β ≤ 45° 에서 성립한다. 편파: VV 단일. 실측에서 2편파로 확장한다.")["count"]:
        bad += 1
        print("  ❌ 완충어 검사 오탐 — 정상 문장을 잡았다")
    else:
        print("  ✅ 통과  완충어 검사 — 조건절로 쓴 문장은 통과")
    if len(lint_prose("처음엔 PO 만 썼다가 SBR 로 바꿨다. 그래서 버그를 수정했다.")) >= 3:
        print("  ✅ 통과  §5.5 과정 서사 권고 — 검출")
    else:
        bad += 1
        print("  ❌ §5.5 과정 서사 검사가 못 잡았다")

    # ── check_budget 이 톤 위반을 **위반**으로 올리는가 ──────────────────────
    tmp = os.environ.get("RS_SELFTEST_OUT", os.path.join(
        "/tmp/claude-1015/-workspace/"
        "a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad", "rs_tone_probe.ipynb"))
    build_notebook(tmp, [md("### 한 일", "무엇을 했다."),
                         md("이것은 없다. 저것도 아니다. 그것은 못한다. 나머지는 않는다."),
                         md("대체로 맞는다."),
                         md("## 다음 단계", "", "| 다음에 할 일 | 그러면 결정되는 것 | 어디서 |",
                            "|---|---|---|", "| 잰다 | 확정된다 | 06편 |")],
                   quiet=True)
    rep = check_budget(tmp)
    fired = {"부정문": any("부정문" in v for v in rep["violations"]),
             "완충어": any("완충어" in v for v in rep["violations"])}
    if all(fired.values()) and not rep["ok"]:
        print(f"  ✅ 통과  check_budget 이 톤을 **위반**으로 올린다 "
              f"(부정문 {rep['n_negatives']} · 완충어 {rep['n_hedges']})")
    else:
        bad += 1
        print(f"  ❌ check_budget 이 톤을 안 올린다: {fired} / {rep['violations']}")
    os.path.exists(tmp) and os.remove(tmp)

    print(f"── 자기검사 {'성공' if bad == 0 else f'실패 {bad}건'} ──\n")
    return bad


if __name__ == "__main__":
    argv = sys.argv[1:]
    if argv:                       # 기존 노트북 측정: python src/report_style.py *.ipynb
        print(budget_report(argv))
        print()
        for a in argv:
            print(tone_report(a))
        raise SystemExit(0)

    fails = _selftest()

    print("── 워크드 예제: 규약을 통과하는 여는 블록 ──\n")
    blocks = _demo_blocks()
    # header() 는 **마크다운 문자열 그 자체**다 — 그대로 출력·연결할 수 있다.
    print(str(blocks[0]).replace(BREAK, "─" * 60))
    print()

    out = os.environ.get(
        "RS_DEMO_OUT",
        "/tmp/claude-1015/-workspace/"
        "a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad/report_style_demo.ipynb")
    rep = build_notebook(out, blocks)
    print("\n── 예산·톤 검사 ──")
    print(json.dumps({k: v for k, v in rep.items()
                      if k in ("md_cells", "code_cells", "figures", "provenance_tags",
                               "n_negatives", "n_hedges", "violations", "ok")},
                     ensure_ascii=False, indent=1))
    raise SystemExit(1 if fails else 0)
