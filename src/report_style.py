# -*- coding: utf-8 -*-
"""
report_style.py — 6편 리포트의 **공통 서술 규약을 코드로 강제**한다
=========================================================================================
계약서: `docs/REBUILD_2026-07-30.md` §5. 이 파일은 그 §5 의 *실행 가능한 구현*이다.
규약을 지키는 것이 "성실함"이 아니라 **함수를 부르면 자동으로 되는 일**이 되게 하는 것이 목적이다.

설계 동기(사용자 지시): **"함께 작업해오던 사람이 아니여도 리포트만 보고 인수인계 받을 수 있게"**.
독자는 이 프로젝트를 오늘 처음 본다. 그 사람이 리포트만 읽고 이어받을 수 있어야 한다.

무엇을 기계적으로 막는가
------------------------------------------------------------------------------------------
| 규약(§5)                        | 이 모듈의 장치                                        |
|---|---|
| 6블록 서두                       | `header()` — 블록이 비면 **예외**                     |
| 주장/비주장 2열 표(정직성 장치)   | `header()` — 한 열이라도 비면 **예외**                |
| 손으로 친 숫자 0개                | `num()` — JSON 을 열어 키를 찾고 값을 **대조**, 어긋나면 예외 |
| 표 안의 숫자도 손으로 안 침       | `table_from()` — JSON 배열/딕셔너리에서 행을 직접 뽑는다 |
| 그림 1개 = 질문 1개               | `caption()` — 물음표로 안 끝나거나 2개면 **예외**      |
| §마지막 = "이 편의 한계"          | `limits()` — '다음 사람이 이어받을 지점'이 없으면 예외 |
| 재현 블록이 실제로 돌아야 함      | `header()` — 출력 JSON 이 디스크에 없으면 예외        |
| 분량 상한(25셀 / 12줄 / 8그림)    | `check_budget()` · `build_notebook(strict=True)`      |
| 서두는 맨 앞 · 한계는 맨 뒤       | `check_budget()` — 순서가 틀리면 위반                 |
| 과정 서사 · 완충어 금지(§5.2)     | `lint_prose()` → `check_budget()` 권고                |
| 그림 글자는 영어                  | `assert_fig_text()`                                   |

⭐ 검증을 끄는 스위치는 **어디에도 없다**. 거짓말할 수 있는 출처 표시는 없느니만 못하다.
   JSON 값이 `null` 이면 `num()` 은 예외를 낸다 — "모른다"를 숫자로 위장시키지 않기 위해서다
   (`if_null="미상"` 으로 명시하면 그 말이 그대로 찍힌다).

⚠ 이 모듈은 **임포트해도 안전**하다(부작용 없음). `src/make_notebook*.py` 와 다르다.

------------------------------------------------------------------------------------------
워크드 예제 — 규약을 통과하는 최소 빌더 (그대로 복사해서 시작할 것)
------------------------------------------------------------------------------------------
```python
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from report_style import (header, num, caption, limits, md, code,
                          table, table_from, build_notebook, from_json)

S = from_json("outputs/sbr_kr_sweep.json")          # 이 편의 근거 JSON

blocks = [
    header(
        num=2,
        title="표적 모델 — 메쉬 · 엔진 · 앵커",
        question="드론 메쉬에서 계산한 RCS 중 무엇을 믿어도 되는가?",
        conclusion_lines=[
            f"엔진 수치는 건강하다. 해석 PO 대비 최대 편차 "
            f"{S.num('summary_div16.max_abs_db_vs_po', 0.201, '{:.3f}', 'dB')} "
            f"(kr 21점 × 입사 {S.num('meta.n_incidence', 48, '{:.0f}')}방향).",
            "따라서 **자세 구조**(각도에 따른 σ 의 모양)는 기하에서 나온 것으로 방어된다.",
            "반면 **절대 레벨**과 **주파수 기울기**는 기하가 아니라 측정 앵커에서 온다.",
            "PO 는 f² 정반사항만 남기고 회절항이 없어 기울기가 측정보다 3~8배 가파르다.",
        ],
        claims=[
            "자세에 따른 σ 의 **구조** — 부품별 재질 + 광선추적 가림에서 나온다",
            "엔진이 해석해(구 PO)를 재현한다 — 위 편차 수치",
        ],
        non_claims=[
            "**절대 σ 레벨** — 측정 앵커(Das, IEEE WCL 2026)에서 온다",
            "**주파수 기울기** — PTD 회절항이 없어 계통적으로 가파르다",
            "β>45° 바이스태틱 — 상반성 검사를 통과하지 못한다",
        ],
        prereq=[("01 §3", "선행연구가 표적 산란을 어떻게 회피했는지")],
        repro=dict(cmd="PYTHONPATH=src python benchmark/verify_sbr_kr_sweep.py",
                   out="outputs/sbr_kr_sweep.json",
                   runtime="약 18분 (GPU 1장)"),
    ),

    md("## §1. 메쉬", "",
       "부품별 재질을 유지한 채 watertight 로 만든다. 코드는 `src/drone_cad.py:120`."),

    # 숫자가 든 표는 JSON 에서 직접 뽑는다 — 손으로 치면 검증을 우회한다.
    md("## §4. 앵커가 통제하지 못한 것", "",
       table_from("outputs/sigma_anchor.json:uncontrolled",
                  [("미통제 항목", "term"), ("상태", "status"), ("크기", "size_db")],
                  fmt={"size_db": "{:+.2f} dB"}, null="미상")),

    # 그림은 **미리 그려둔 PNG 를 마크다운으로 끼운다**(viz 스크립트가 만든다).
    # check_budget 이 그 파일이 실제로 있는지까지 확인한다 — 깨진 링크 = 인수인계 실패.
    md("![sbr validate](outputs/figures/report2_sbr_validate.png)", "",
       caption(1, "SBR 이 해석 PO 와 몇 dB 안에서 일치하는가?")),

    limits([
        ("PTD 회절 보정이 없다", "`src/rcs_sbr.py` 에 등가 모서리 전류를 추가 → 기울기 재측정"),
        ("편파 통제가 없다", "06편 측정 설계의 편파 축을 먼저 확정"),
    ]),
]

build_notebook("report02.ipynb", blocks, strict=True)
```

여섯 빌더가 공통으로 지킬 것
------------------------------------------------------------------------------------------
1. `md()` / `code()` / `header()` / `limits()` 는 **전부 그냥 문자열**(`Block`)이다.
   `print(header(...))`, `md("a") + "b"` 다 된다. `.kind` 만 얹혀 있어 셀 종류를 안다.
2. **숫자는 전부 `num()` 을 통과**시킨다. 값을 안 적고 `num(None, ...)` 로 두면 JSON 이
   유일한 진실이 된다. 값을 적으면 그건 *주장*이고, JSON 과 어긋나면 빌드가 멈춘다.
   표 안의 숫자도 예외가 아니다 — 칸마다 `num()` 을 넣거나 `table_from()` 으로 뽑는다.
3. 그림은 viz 스크립트가 만든 **PNG 를 마크다운으로 끼우고** 바로 밑에 `caption()` 한 줄.
   그림 안의 글자는 영어 — viz 쪽에서 `assert_fig_text()` 로 확인한다.
4. 마지막은 반드시 `limits()`. **다음 사람이 어디서 이어받는지**가 없으면 예외가 난다.
5. 다 만들고 `build_notebook(..., strict=True)` — §5.4 상한을 넘으면 만들어지지 않는다.

`python src/report_style.py` 로 이 모듈 자체의 데모·자기검사를 돌려볼 수 있다.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Iterable, Sequence

# --------------------------------------------------------------------------- #
#  경로 · 상수
# --------------------------------------------------------------------------- #
ROOT = os.environ.get(
    "SIONNA2_ROOT",
    os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))

#: §5.4 분량 상한 — 넘치면 **내용을 줄이지 말고 편을 쪼개라**(다만 6편 골격은 유지).
MAX_MD_CELLS = 25
MAX_LINES_PER_CELL = 12
MAX_FIGURES = 8

#: 마크다운 블록 안에서 이 줄을 만나면 **셀을 나눈다**.
BREAK = "<!--cell-->"

#: 구조 블록 태그 — 12줄 상한에서 면제되고, 존재 여부가 검사된다.
TAG_HEADER = "header"
TAG_LIMITS = "limits"
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

    # 인용은 **값 하나**여야 한다 — 배열·딕셔너리를 통째로 본문에 붓지 않는다(§5.2 "산문 속 숫자 나열").
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
#  2) 서두 6블록 — `header()`
# --------------------------------------------------------------------------- #
def _rows(items: Sequence, what: str) -> list[tuple[str, str]]:
    """`[(a, b), ...]` 또는 `[{"a":..,"b":..}]` 를 2열 튜플 리스트로."""
    out = []
    for it in items:
        if isinstance(it, dict):
            vals = list(it.values())
            if len(vals) != 2:
                raise ContractError(f"{what}: 2열이 필요하다 — {it!r}")
            out.append((str(vals[0]), str(vals[1])))
        elif isinstance(it, (tuple, list)):
            if len(it) != 2:
                raise ContractError(f"{what}: 2열이 필요하다 — {it!r}")
            out.append((str(it[0]), str(it[1])))
        else:
            raise ContractError(f"{what}: (앞, 뒤) 쌍이어야 한다 — {it!r}")
    return out


def _md_escape_cell(s: str) -> str:
    return str(s).replace("|", r"\|").replace("\n", " ")


def header(num: int | str,                       # noqa: A002  (계약서의 인자 이름 그대로)
           title: str,
           question: str,
           conclusion_lines: Sequence[str],
           claims: Sequence[str],
           non_claims: Sequence[str],
           prereq: Sequence | None = None,
           repro: dict | None = None,
           allow_missing_output: bool = False) -> Block:
    """§5.1 의 **6블록 서두**를 만든다. 하나라도 비면 예외.

    블록: ① 한 줄 질문 ② 결론(3~5줄, 숫자 포함) ③ 주장/비주장 2열 표
          ④ 필요한 사전지식 ⑤ 재현(명령 + 출력 JSON + 소요시간) ⑥ 본문 시작

    ⭐ ③ 은 이 프로젝트의 **정직성 장치**다. 두 열 중 하나라도 비면 리포트가 만들어지지 않는다.

    반환: 마크다운 문자열(`Block`). `build_notebook()` 이 `<!--cell-->` 에서 2셀로 나눈다.
    """
    # ── ① 질문 ──────────────────────────────────────────────────────────────
    q = str(question).strip()
    if not q:
        raise ContractError("§5.1 ①: 이 편이 답하는 질문이 비었다.")
    if not q.endswith("?"):
        raise ContractError(f"§5.1 ①: 질문은 물음표로 끝나야 한다 — {q!r}")
    if q.count("?") > 1:
        raise ContractError(
            f"§5.1 ①: 한 편은 **질문 하나**에 답한다. 물음표가 {q.count('?')}개다 — {q!r}\n"
            "  → 두 질문이면 그건 편을 쪼개야 한다는 뜻이다(§5.4).")

    # ── ② 결론 ──────────────────────────────────────────────────────────────
    concl = [str(c).strip() for c in (conclusion_lines or []) if str(c).strip()]
    if not (3 <= len(concl) <= 5):
        raise ContractError(
            f"§5.1 ②: 결론은 3~5줄이다. 지금 {len(concl)}줄.\n"
            "  → 여기만 읽어도 결론을 알 수 있어야 하고, 그 이상은 본문이다.")
    if not any(re.search(r"\d", c) for c in concl):
        raise ContractError(
            "§5.1 ②: 결론에 **숫자가 하나도 없다**. 근거 수치를 `num()` 으로 넣어라.")

    # ── ③ 주장 / 비주장 ─────────────────────────────────────────────────────
    C = [str(c).strip() for c in (claims or []) if str(c).strip()]
    N = [str(c).strip() for c in (non_claims or []) if str(c).strip()]
    if not C or not N:
        raise ContractError(
            "§5.1 ③ **정직성 장치**: 주장/비주장 표는 두 열이 다 채워져야 한다 "
            f"(주장 {len(C)}개, 비주장 {len(N)}개).\n"
            "  → 주장하지 않는 것이 없다면, 그건 아직 경계를 안 그은 것이다. "
            "무엇이 이 편의 근거로 지지되지 **않는지** 적어라.")

    # ── ④ 사전지식 ──────────────────────────────────────────────────────────
    P = _rows(prereq or [], "§5.1 ④ 사전지식")

    # ── ⑤ 재현 ──────────────────────────────────────────────────────────────
    R = dict(repro or {})
    for need in ("cmd", "out"):
        if not str(R.get(need, "")).strip():
            raise ContractError(
                f"§5.1 ⑤ 재현: '{need}' 가 없다. 명령 한 줄 + 출력 JSON 경로 + 소요시간은 필수다.\n"
                "  → repro=dict(cmd='PYTHONPATH=src python benchmark/x.py', "
                "out='outputs/x.json', runtime='약 12분 (GPU 1장)')")
    outs = R["out"] if isinstance(R["out"], (list, tuple)) else [R["out"]]
    for o in outs:
        pth = o if os.path.isabs(o) else os.path.join(ROOT, o)
        if not os.path.exists(pth) and not allow_missing_output:
            raise ContractError(
                f"§5.3-4 재현 블록이 실제로 돌아야 한다 — 출력이 디스크에 없다: {o}\n"
                f"  → 실험을 먼저 돌리거나, 경로를 고쳐라. (기대: {pth})")
    if not str(R.get("runtime", "")).strip():
        R["runtime"] = "(미측정 — 재현 전에 채울 것)"

    n = f"{int(num):02d}" if str(num).strip().isdigit() else str(num)

    A = [f"<!--rs:{TAG_HEADER}-->",
         f"# 리포트 {n} — {title}", "",
         "> ### ❓ 이 편이 답하는 질문",
         f"> **{q}**", "",
         "### 결론"]
    A += [f"{i+1}. {c}" for i, c in enumerate(concl)]

    B = [f"<!--rs:{TAG_HEADER}-->",
         "### ✅ 주장하는 것 / ❌ 주장하지 않는 것", "",
         "| ✅ 이 편이 주장하는 것 | ❌ 이 편이 주장하지 않는 것 |", "|---|---|"]
    for i in range(max(len(C), len(N))):
        B.append(f"| {_md_escape_cell(C[i]) if i < len(C) else ''} "
                 f"| {_md_escape_cell(N[i]) if i < len(N) else ''} |")
    B += ["", "### 필요한 사전지식", ""]
    if P:
        B += ["| 어디서 | 무엇을 알고 와야 하나 |", "|---|---|"]
        B += [f"| {_md_escape_cell(a)} | {_md_escape_cell(b)} |" for a, b in P]
    else:
        B += ["없음. 이 편부터 읽어도 된다."]
    B += ["", "### 재현", "", "```bash",
          *(R["cmd"] if isinstance(R["cmd"], (list, tuple)) else [R["cmd"]]),
          "```", "",
          "| | |", "|---|---|",
          "| 출력 | " + ", ".join(f"`{o}`" for o in outs) + " |",
          f"| 소요 | {R['runtime']} |"]
    if R.get("note"):
        B += [f"| 비고 | {_md_escape_cell(R['note'])} |"]
    B += ["", "---"]

    return Block("\n".join(A) + f"\n\n{BREAK}\n\n" + "\n".join(B))


# --------------------------------------------------------------------------- #
#  3) 그림 캡션 — 그림 1개 = 질문 1개
# --------------------------------------------------------------------------- #
def caption(fig_no: int | str, question: str) -> str:
    """`**그림 3.** 질문?` — 그 그림이 답하는 **질문 하나**를 적는다(§5.2 마지막 줄)."""
    q = str(question).strip()
    if not q:
        raise ContractError("캡션이 비었다.")
    if not q.endswith("?"):
        raise ContractError(
            f"그림 {fig_no}: 캡션은 **그 그림이 답하는 질문**이다. 물음표로 끝나야 한다 — {q!r}")
    if q.count("?") > 1:
        raise ContractError(
            f"그림 {fig_no}: 그림 1개 = 질문 1개(§5.2). 물음표가 {q.count('?')}개다 — {q!r}\n"
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
#  4) 마지막 절 — "이 편의 한계"
# --------------------------------------------------------------------------- #
def limits(items: Sequence, sec: str | None = None) -> Block:
    """§5.3-3 **각 편의 마지막 절**. 무엇이 아직 안 되어 있고, 다음 사람이 어디서 이어받나.

    items: `[("아직 안 된 것", "다음 사람이 이어받을 지점"), ...]`
           두 번째 칸이 비면 예외 — **인수인계 지점 없는 한계는 그냥 변명이다.**
    """
    rows = _rows(items or [], "이 편의 한계")
    if not rows:
        raise ContractError(
            "§5.3-3: '이 편의 한계' 가 비었다. 아직 안 된 것이 정말 없을 리 없다.\n"
            "  → 다음 사람이 이어받을 지점을 적는 자리다.")
    for a, b in rows:
        if not a.strip() or not b.strip():
            raise ContractError(
                f"§5.3-3: 한계에는 **이어받을 지점**이 함께 있어야 한다 — ({a!r}, {b!r})")
    head = f"## {sec} 이 편의 한계" if sec else "## 이 편의 한계"
    L = [f"<!--rs:{TAG_LIMITS}-->", head, "",
         "| 아직 안 되어 있는 것 | 다음 사람이 이어받을 지점 |", "|---|---|"]
    L += [f"| {_md_escape_cell(a)} | {_md_escape_cell(b)} |" for a, b in rows]
    return Block("\n".join(L))


# --------------------------------------------------------------------------- #
#  5) 노트북 조립 — 빌더 6개가 짧고 똑같아지도록
# --------------------------------------------------------------------------- #
def md(*lines: str) -> Block:
    """마크다운 블록. 줄 하나가 `<!--cell-->` 이면 거기서 셀이 나뉜다."""
    return Block("\n".join(str(x) for x in lines), "markdown")


def code(*lines: str) -> Block:
    """코드 블록."""
    return Block("\n".join(str(x) for x in lines), "code")


def table(headers: Sequence[str], rows: Iterable[Sequence]) -> str:
    """마크다운 표. `table()` 자신은 **셀 내용을 검증하지 않는다.**

    ⚠ §5.2 는 산문 속 숫자를 표로 몰아넣으라고 한다. 그래서 리포트의 숫자 대부분이
      표 안에 산다. 그 칸을 손으로 치면 검증을 통째로 우회하게 된다. 그러니 숫자 칸은
      **둘 중 하나**로만 만든다.

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
    columns: `[(표머리, 필드경로), ...]`. 필드경로는 각 행 **안에서**의 점 경로다.
             `key_col` 을 쓸 땐 그 열의 필드경로 자리에 `None` 을 둔다.
    fmt    : `{필드경로: "{:+.2f}"}` — 숫자 포맷.
    null   : 값이 `null` 인 칸에 쓸 말. 기본 `"미상"`.
    key_col: 딕셔너리 원본일 때, 딕셔너리 **키**를 담을 열의 머리 이름.
    order  : 넣을 키(또는 인덱스)를 직접 고르고 순서를 정한다. 기본은 원본 순서.
    tag    : 표 밑에 출처 한 줄을 붙인다. 칸마다 태그를 다는 대신 **표 하나에 태그 하나**.

    예)
        table_from("outputs/sigma_anchor.json:uncontrolled",
                   [("미통제 항목", "term"), ("상태", "status"), ("크기", "size_db")],
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
                f"블록은 md(...) / code(...) / 문자열 이어야 한다 — {type(b).__name__}: {b!r}")
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


def build_notebook(path: str, blocks: Iterable, kernel: dict | None = None,
                   strict: bool = False, quiet: bool = False) -> dict:
    """블록 리스트 → `.ipynb` 파일. 쓰고 나서 §5.4 예산을 검사해 결과를 돌려준다.

    strict=True 면 예산 위반 시 **예외**(파일은 이미 쓰인 뒤이므로 확인 후 줄이면 된다).
    """
    cells = _to_cells(blocks)
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
            f"§5.4 예산 위반 — {rep['path']}\n  "
            + "\n  ".join(rep["violations"])
            + "\n  → 내용을 줄이지 말고 **편을 쪼개라**. 쪼갤 만큼이면 두 질문을 답하고 있는 것이다.")
    return rep


# --------------------------------------------------------------------------- #
#  6) 분량·필수블록 검사 — `check_budget()`
# --------------------------------------------------------------------------- #
_FIG_CAP = re.compile(r"^\s*\*\*(?:그림|Figure)\s*([0-9]+(?:[.\-][0-9]+)?)\s*[.)]", re.M)
_SAVEFIG = re.compile(r"\b(?:savefig|plt\.show)\s*\(")
#: 리포트는 미리 그려둔 PNG 를 마크다운으로 끼워 넣는다 — 그것도 '그림'으로 센다.
_MD_IMG = re.compile(r"!\[[^\]]*\]\(\s*([^)\s]+)[^)]*\)|<img[^>]+src=[\"']([^\"']+)[\"']")
_PROV = re.compile(r"⟨[^⟩]+?\.(?:json|npz)\s*:\s*[^⟩]+⟩")
#: 출처 태그 **와 그 앞의 값**(단위 포함)을 통째로 지운다 — 그 숫자는 손으로 친 게 아니다.
_PROV_VALUE = re.compile(r"[-+]?[\d][\d,.eE+\-]*\s*(?:[%°]|[A-Za-z·/]{0,8})?\s*"
                         r"⟨[^⟩]+?\.(?:json|npz)\s*:\s*[^⟩]+⟩")
# 산문 속 '손으로 친 숫자' 후보 — 소수점이 있거나 3자리 이상. §·그림·리포트 번호 등은 뺀다.
_BARE_NUM = re.compile(r"(?<![\w.\-/])(\d+\.\d+|\d{3,})(?![\w.])")
_YEAR = re.compile(r"^(?:19|20)\d{2}$")          # 인용 연도는 손으로 적는 게 맞다


# --------------------------------------------------------------------------- #
#  §5.2 금지 표현 — 과정 서사 · 완충어
#  사용자 지시: "지금 레포트 서술 방식이 너무 구구절절이라서 보기 안좋다".
#  리포트는 **현재 상태**만 쓴다. 어떻게 여기까지 왔는지는 코드 docstring 의 몫이다.
# --------------------------------------------------------------------------- #
#: 과정 서사 — "처음엔 …했다가 …로 바꿨다" 류. 버그·수정 이력도 여기 걸린다.
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
#: 완충어 — 단정하거나, 모른다고 쓰거나. 둘 중 하나만 한다.
_HEDGE = [
    (r"라고 볼 수 있다|볼 수 있다", "완충어"),
    (r"인 것 같다|같아 보인다", "완충어"),
    (r"생각된다|사료된다|판단된다", "완충어"),
    (r"어느 정도|다소|비교적", "완충어"),
    (r"으로 보인다|로 보인다", "완충어"),
    (r"할 수도 있다", "완충어"),
]
_SENT_END = re.compile(r"[.!?。]\s|\n")


def lint_prose(text: str) -> list[str]:
    """§5.2 금지 항목을 찾아 **권고 문자열 목록**으로 돌려준다(예외는 안 낸다).

    검사: ①과정 서사 ②버그·수정 이력 ③완충어 ④3문장 넘는 문단.
    표·코드·인용 태그는 검사에서 뺀다(오탐이 많아서다).
    """
    t = re.sub(r"`[^`]*`", "", str(text))          # 코드 스팬
    t = _PROV.sub("", t)                            # 출처 태그
    body = "\n".join(ln for ln in t.splitlines()
                     if not ln.lstrip().startswith(("|", ">", "#", "!", "```")))
    hits: list[str] = []
    for pat, why in _NARRATIVE + _HEDGE:
        for m in re.finditer(pat, body):
            hits.append(f"{why}: '{m.group(0)}' (§5.2 금지)")
    # 3문장 넘는 문단 — "끊거나 표로".
    # ⚠ 목록(결론 3~5줄 등)은 이미 끊어 쓴 것이므로 문단으로 세지 않는다.
    prose = "\n".join(ln for ln in body.splitlines()
                      if not re.match(r"^\s*(?:\d+\.|[-*+])\s", ln))
    for para in re.split(r"\n\s*\n", prose):
        para = para.strip()
        if not para:
            continue
        n_sent = len([s for s in _SENT_END.split(para) if s.strip()])
        if n_sent > 3:
            hits.append(f"문단이 {n_sent}문장 > 3 (§5.2: 끊거나 표로) "
                        f"— \"{para[:40]}…\"")
    return sorted(set(hits))


#: `table_from()` 이 표 밑에 붙이는 출처 한 줄. 그 표의 숫자는 JSON 에서 뽑은 것이다.
_TABLE_SRC = re.compile(r"^\s*출처\s*⟨[^⟩]+?\.(?:json|npz)\s*:\s*[^⟩]+⟩\s*$")


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


def _cell_text(c: dict) -> str:
    s = c.get("source", "")
    return s if isinstance(s, str) else "".join(s)


def _has_tag(c: dict, tag: str) -> bool:
    return tag in (c.get("metadata", {}).get("tags") or [])


def check_budget(nb_path: str) -> dict:
    """§5.4 상한(마크다운 25셀 / 셀당 12줄 / 그림 8개)과 필수 블록을 검사한다.

    반환: dict(md_cells, code_cells, figures, violations[], advisories[], ok, offenders[], …)

    - **줄 수**는 빈 줄을 뺀 실질 줄로 센다(표 위아래 빈 줄 때문에 억울하게 걸리지 않도록).
    - 서두(header)·한계(limits)는 **구조 블록**이라 줄 수 상한에서 면제된다. 다만 셀 수엔 포함된다.
    - 그림 수는 ①캡션 ②마크다운 이미지 ③`savefig`·`plt.show` ④저장된 이미지 출력 중 **최대**.
    - 끼워 넣은 PNG 가 **디스크에 없으면 위반**이다 — 깨진 그림 링크는 인수인계 실패다.
    - 출처 태그 없는 숫자는 **권고**(advisories)로만 알린다. 오탐(단위·§번호)이 있어서다.
    - 이 함수는 우리가 만들지 않은 옛 노트북에도 돈다(태그 없으면 표 모양으로 추정).
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
                # 노트북 위치 기준, 없으면 리포지토리 루트 기준으로도 찾아본다
                cands = ([src] if os.path.isabs(src)
                         else [os.path.join(os.path.dirname(p), src),
                               os.path.join(ROOT, src)])
                if not any(os.path.exists(x) for x in cands):
                    missing_imgs.append(f"셀 {i}: {src}")
            prov_tags += len(_PROV.findall(t))
            exempt = _has_tag(c, TAG_HEADER) or _has_tag(c, TAG_LIMITS)
            if not exempt and "| ✅" in t:            # 태그 없는 옛 노트북 대비
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
                    f"— `num()` 으로 바꿀 것인지 확인 (§5.3-1)")
            for h in lint_prose(t)[:3]:          # §5.2 금지 표현
                advisories.append(f"셀 {i}: {h}")
        else:
            savefigs += len(_SAVEFIG.findall(t))
            for o in c.get("outputs", []) or []:
                if any(k.startswith("image/") for k in (o.get("data") or {})):
                    img_outs += 1

    figures = max(len(fig_ids), savefigs, img_outs, len(md_imgs))

    all_md = "\n".join(_cell_text(c) for c in md_cells)
    has_header = any(_has_tag(c, TAG_HEADER) for c in md_cells) or "| ✅" in all_md
    has_limits = any(_has_tag(c, TAG_LIMITS) for c in md_cells) or "이 편의 한계" in all_md

    V = []
    if len(md_cells) > MAX_MD_CELLS:
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
            f"— 모든 그림에 `caption()` 한 줄 (§5.3-2)")
    if not has_header:
        V.append("필수 블록 없음: 서두 6블록(주장/비주장 표) — `header()` 를 쓸 것")
    if not has_limits:
        V.append("필수 블록 없음: 마지막 절 '이 편의 한계' — `limits()` 를 쓸 것")

    # 순서: 서두는 맨 앞(§5.1 "모든 편이 같은 6블록으로 시작한다"),
    #       한계는 맨 뒤(§5.3-3 "§마지막 = 이 편의 한계").
    if has_header and cells and not _has_tag(cells[0], TAG_HEADER) \
            and "| ✅" not in _cell_text(cells[0]):
        V.append("서두 6블록이 맨 앞이 아니다(§5.1) — `header()` 를 첫 블록으로")
    if has_limits:
        tail = [j for j, c in enumerate(cells)
                if _has_tag(c, TAG_LIMITS) or "이 편의 한계" in _cell_text(c)]
        if tail and tail[-1] < len(cells) - 2:
            V.append(f"'이 편의 한계' 가 마지막이 아니다(§5.3-3) — "
                     f"셀 {tail[-1]}/{len(cells) - 1}")

    shown = os.path.relpath(p, ROOT)
    if shown.startswith(".."):
        shown = p                       # 리포지토리 밖(스크래치패드 등)이면 절대경로 그대로
    return dict(path=shown, md_cells=len(md_cells),
                code_cells=len(code_cells), figures=figures,
                fig_captions=len(fig_ids), savefig_calls=savefigs,
                image_outputs=img_outs, md_images=len(md_imgs),
                missing_images=missing_imgs, provenance_tags=prov_tags,
                caps=dict(md_cells=MAX_MD_CELLS, lines_per_cell=MAX_LINES_PER_CELL,
                          figures=MAX_FIGURES),
                offenders=offenders, advisories=advisories,
                violations=V, ok=not V)


def _budget_text(rep: dict) -> str:
    mark = "✅" if rep["ok"] else "⛔"
    s = (f"{mark} {rep['path']} — 마크다운 {rep['md_cells']}/{MAX_MD_CELLS}셀 · "
         f"코드 {rep['code_cells']}셀 · 그림 {rep['figures']}/{MAX_FIGURES} · "
         f"출처태그 {rep['provenance_tags']}개")
    for v in rep["violations"]:
        s += f"\n   ⛔ {v}"
    for a in rep["advisories"][:5]:
        s += f"\n   ⚠ {a}"
    if len(rep["advisories"]) > 5:
        s += f"\n   ⚠ … 권고 {len(rep['advisories']) - 5}건 더"
    return s


def budget_report(nb_paths: Iterable[str]) -> str:
    """여러 편을 한 번에 검사해 사람이 읽을 표로. 재편 후 전체 점검용."""
    lines = ["| 리포트 | md셀 | 코드셀 | 그림 | 출처태그 | 판정 |", "|---|---|---|---|---|---|"]
    tot_md = tot_fig = 0
    for p in nb_paths:
        r = check_budget(p)
        tot_md += r["md_cells"]
        tot_fig += r["figures"]
        lines.append(f"| `{r['path']}` | {r['md_cells']}/{MAX_MD_CELLS} | {r['code_cells']} "
                     f"| {r['figures']}/{MAX_FIGURES} | {r['provenance_tags']} "
                     f"| {'✅' if r['ok'] else '⛔ ' + '; '.join(r['violations'])} |")
    lines.append(f"| **합계** | **{tot_md}** |  | **{tot_fig}** |  |  |")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
#  데모 · 자기검사 — `python src/report_style.py`
# --------------------------------------------------------------------------- #
def _demo_blocks():
    """규약을 통과하는 서두 한 벌. 여섯 빌더가 그대로 베껴 쓸 견본이다."""
    S = from_json("outputs/sbr_kr_sweep.json")

    return [
        header(
            num=2,
            title="표적 모델: 메쉬 · 엔진 · 앵커",
            question="드론 메쉬에서 계산한 RCS 중 무엇을 믿어도 되는가?",
            conclusion_lines=[
                f"엔진 수치는 건강하다 — 해석 PO 대비 최대 편차 "
                f"{S.num('summary_div16.max_abs_db_vs_po', 0.201, '{:.3f}', 'dB')}"
                f"(kr {S.num('summary_div16.n_points', 21, '{:.0f}')}점 × 입사 "
                f"{S.num('meta.n_incidence', 48, '{:.0f}')}방향, kr=1 까지 포함).",
                f"kr≥30 에서 해석 PO 대비 산포는 "
                f"{S.num('summary_div16.std_sbr_over_po_pct_kr_ge30', 0.885, '{:.3f}', '%')} 다.",
                "따라서 **자세 구조**(각도에 따른 σ 의 모양)는 기하에서 나온 것으로 방어된다.",
                "**절대 레벨**과 **주파수 기울기**는 기하가 아니라 측정 앵커에서 온다.",
            ],
            claims=[
                "자세에 따른 σ 의 **구조** — 부품별 재질 + 광선추적 가림에서 나온다",
                "엔진이 해석해(구 PO)를 재현한다 — 위 편차 수치",
            ],
            non_claims=[
                "**절대 σ 레벨** — 측정 앵커(Das, IEEE WCL 2026)에서 온다",
                "**주파수 기울기** — PTD 회절항이 없어 계통적으로 가파르다",
                "β>45° 바이스태틱 — 상반성 검사를 통과하지 못한다",
            ],
            prereq=[("01 §3", "선행연구가 표적 산란 계산을 어떻게 회피했는지")],
            repro=dict(cmd="PYTHONPATH=src ~/.venvs/py312/bin/python "
                           "benchmark/verify_sbr_kr_sweep.py",
                       out="outputs/sbr_kr_sweep.json",
                       runtime="(재현 시 측정해 채울 것)"),
            allow_missing_output=False,
        ),
        md("## §1. 무엇이 계산하고 무엇이 앵커인가", "",
           "기하는 **구조**를, 측정은 **레벨**을 준다. 경계는 아래 표가 전부다.", "",
           # 말(label)로만 된 표는 table() 로 충분하다.
           table(["축", "어디서 오나", "근거"],
                 [["자세 구조", "기하(SBR+PO)", "본 편 §2"],
                  ["절대 레벨", "측정 앵커", "외부 문헌"],
                  ["주파수 기울기", "측정 앵커", "외부 문헌"]])),

        # ⭐ 숫자가 들어가는 표는 **JSON 에서 직접 뽑는다** — 손으로 치면 검증을 우회한다.
        md("## §4. 앵커가 통제하지 못한 것", "",
           "가장 큰 미통제 항목이 적용한 보정보다 크다. 그 사실을 먼저 적는다.", "",
           table_from("outputs/sigma_anchor.json:uncontrolled",
                      [("미통제 항목", "term"), ("상태", "status"),
                       ("크기", "size_db")],
                      fmt={"size_db": "{:+.2f} dB"}, null="미상")),
        # 그림은 viz 스크립트가 미리 만든 PNG 를 끼우고 바로 밑에 캡션 한 줄.
        md("![sbr validate](outputs/figures/report2_sbr_validate.png)", "",
           caption(1, "SBR 이 해석 PO 와 몇 dB 안에서 일치하는가?")),
        # 코드 셀이 필요하면 이렇게. 그림 글자는 영어 — assert_fig_text 로 확인한다.
        code("from report_style import assert_fig_text",
             "assert_fig_text('RCS [dBsm]', 'kr = 2*pi*r/lambda')"),
        limits([
            ("PTD 회절 보정이 없다", "`src/rcs_sbr.py` 에 등가 모서리 전류 추가 → 기울기 재측정"),
            ("편파가 통제되지 않는다", "06편 측정 설계에서 편파 축을 먼저 확정"),
        ], sec="§9."),
    ]


def _selftest() -> None:
    """규약 장치가 **실제로 막는지** 확인한다. 막지 못하는 장치는 장치가 아니다."""
    cases = [
        ("질문에 물음표 없음",
         lambda: header(1, "t", "질문이다", ["a1", "b2", "c3"], ["c"], ["n"],
                        repro=dict(cmd="x", out="outputs/sbr_kr_sweep.json"))),
        ("결론 2줄(3~5줄 위반)",
         lambda: header(1, "t", "q?", ["a1", "b2"], ["c"], ["n"],
                        repro=dict(cmd="x", out="outputs/sbr_kr_sweep.json"))),
        ("결론에 숫자 없음",
         lambda: header(1, "t", "q?", ["a", "b", "c"], ["c"], ["n"],
                        repro=dict(cmd="x", out="outputs/sbr_kr_sweep.json"))),
        ("⭐ 비주장 열이 빔(정직성 장치)",
         lambda: header(1, "t", "q?", ["a1", "b2", "c3"], ["c"], [],
                        repro=dict(cmd="x", out="outputs/sbr_kr_sweep.json"))),
        ("재현 출력 JSON 이 없음",
         lambda: header(1, "t", "q?", ["a1", "b2", "c3"], ["c"], ["n"],
                        repro=dict(cmd="x", out="outputs/없는파일.json"))),
        ("⭐ 숫자가 출처와 다름",
         lambda: num(0.5, "outputs/sbr_kr_sweep.json:summary_div16.max_abs_db_vs_po",
                     "{:.3f}")),
        ("출처 키가 없음",
         lambda: num(None, "outputs/sbr_kr_sweep.json:summary_div16.없는키")),
        ("출처 파일이 없음",
         lambda: num(None, "outputs/없는파일.json:a")),
        ("배열을 통째로 인용(값 하나여야 함)",
         lambda: num(None, "outputs/sbr_kr_sweep.json:meta.kr_ladder")),
        ("딕셔너리를 통째로 인용",
         lambda: num(None, "outputs/sbr_kr_sweep.json:summary_div16")),
        ("캡션이 질문이 아님", lambda: caption(1, "SBR 과 PO 의 비교.")),
        ("캡션에 질문 2개", lambda: caption(1, "A 인가? B 인가?")),
        ("한계에 인수인계 지점 없음", lambda: limits([("PTD 없음", "")])),
        ("한계가 빔", lambda: limits([])),
        ("그림 텍스트에 한글", lambda: assert_fig_text("RCS [dBsm]", "입사각")),
        ("⭐ null 을 숫자처럼 인용(미해소 항목)",
         lambda: num(None, "outputs/sigma_anchor.json:uncontrolled[0].size_db",
                     "{:.2f}", "dB")),
        ("table_from 에 값 하나를 줌",
         lambda: table_from("outputs/sbr_kr_sweep.json:meta.n_incidence",
                            [("a", "b")])),
        ("table_from 에 없는 키",
         lambda: table_from("outputs/sigma_anchor.json:drones",
                            [("기체", None), ("없는필드", "존재하지_않음")])),
        ("검사할 노트북이 없음",
         lambda: check_budget("outputs/없는노트북.ipynb")),
    ]
    print("── 자기검사: 규약 위반이 실제로 막히는가 ──")
    bad = 0
    for name, fn in cases:
        try:
            fn()
        except ContractError as e:
            print(f"  ✅ 막힘  {name}  — {str(e).splitlines()[0][:72]}")
        else:
            bad += 1
            print(f"  ❌ 안 막힘 {name}")
    # 통과해야 하는 것들
    for name, fn in [
        ("정상 num(값 대조)",
         lambda: num(0.201, "outputs/sbr_kr_sweep.json:summary_div16.max_abs_db_vs_po",
                     "{:.3f}", "dB")),
        ("정상 num(값 생략 → JSON 에서 읽음)",
         lambda: num(None, "outputs/sbr_kr_sweep.json:meta.n_incidence", "{:.0f}")),
        ("점 들어간 키 해석",
         lambda: num(None, "outputs/rcs_anchor.json:meta.bands.5G 3.5 GHz", "{:.3e}", "Hz")),
        ("리스트 인덱싱", lambda: num(None, "outputs/sbr_kr_sweep.json:meta.kr_ladder[0]")),
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
            print(f"  ❌ 정상인데 터짐 {name}: {e}")
        else:
            print(f"  ✅ 통과  {name}  → {r if isinstance(r, str) else ''}")
    # §5.2 산문 검사 — 금지 표현을 실제로 잡는가
    caught = lint_prose(
        "처음엔 PO 만 썼다가 SBR 로 바꿨다. 그래서 버그를 수정했다. "
        "이 값은 타당하다고 볼 수 있다.")
    if len(caught) >= 3:
        print(f"  ✅ 통과  §5.2 산문 검사 — 금지 표현 {len(caught)}건 검출")
    else:
        bad += 1
        print(f"  ❌ §5.2 산문 검사가 못 잡았다: {caught}")
    if lint_prose("엔진 편차는 0.201 dB 다. 자세 구조는 기하에서 나온다."):
        bad += 1
        print("  ❌ §5.2 산문 검사 오탐 — 정상 문장을 잡았다")
    else:
        print("  ✅ 통과  §5.2 산문 검사 — 정상 문장은 통과")

    print(f"── 자기검사 {'성공' if bad == 0 else f'실패 {bad}건'} ──\n")


if __name__ == "__main__":
    _selftest()

    print("── 워크드 예제: 규약을 통과하는 서두 ──\n")
    blocks = _demo_blocks()
    # header() 는 **마크다운 문자열 그 자체**다 — 그대로 출력·연결할 수 있다.
    print(str(blocks[0]).replace(BREAK, "─" * 60))
    print()

    out = os.environ.get(
        "RS_DEMO_OUT",
        "/tmp/claude-1015/-home-yunjung-workspace/"
        "a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad/report_style_demo.ipynb")
    rep = build_notebook(out, blocks)
    print("\n── 예산 검사 ──")
    print(json.dumps({k: v for k, v in rep.items()
                      if k in ("md_cells", "code_cells", "figures", "provenance_tags",
                               "violations", "ok")}, ensure_ascii=False, indent=1))
