# -*- coding: utf-8 -*-
"""
paper_kit.py — 리포트를 **논문 원고의 부품**으로 만드는 도구
=========================================================================================
계약서 두 장이 동시에 걸린다. 이 파일은 **두 번째 것의 실행 가능한 구현**이다.

| 계약 | 무엇을 정하나 | 강제하는 곳 |
|---|---|---|
| `docs/REBUILD_2026-07-30.md` §5 | 서술 규약(여는 블록·톤·분량) | `src/report_style.py` |
| `docs/PAPER_SPEC.md` §4 | **논문 참고자료 규격**(대응·방어선·그림·방법·인용) | 이 파일 |

`report_style.py` 는 "리포트로서 읽히는가"를 본다. 이 파일은 **"논문 원고로 그대로 옮겨지는가"**
를 본다. 그래서 이 모듈의 예외는 전부 `report_style.ContractError` 의 자식이다 — 빌더는
`try/except ContractError` 하나로 두 계약을 함께 받는다.

무엇을 기계적으로 강제하는가
------------------------------------------------------------------------------------------
| PAPER_SPEC §4 | 이 모듈의 장치 | 막는 것 |
|---|---|---|
| 4.1 논문 대응 블록 | `paper_map()` | 모르는 절 이름 · 근거 없는 주장 · "최초" 류 문구 |
| 4.2 방어선 표 | `defence()` | **공격·답이 빈 행** — 반론을 안 적은 주장은 생각하지 않은 주장이다 |
| 4.3 게재 품질 그림 | `paper_style()` · `save_figure()` · `check_figure()` | 8 pt 미만 글자 · **색만으로 구분된 계열** |
| 4.4 방법 문단 | `methods()` | 파라미터·버전이 없는 문단(재현 불가) |
| 4.5 논문 형식 인용 | `cite()` | **게재상태 누락** · arXiv ID 없는 프리프린트 |
| — | `extract_paper_kit()` | 위 전부를 `outputs/paper_kit.json` 으로 모은다 |

⭐ 이 모듈의 원리 — **원고를 쓸 사람이 노트북을 다시 열지 않아도 되게 한다**
------------------------------------------------------------------------------------------
`extract_paper_kit()` 이 만드는 JSON 하나로 절을 하나씩 초고까지 쓸 수 있어야 한다. 그래서
주장·방어선·방법 문단·인용·그림뿐 아니라 **출처 태그가 붙은 수치 전부**를 절 단위로 모은다.

⚠ 두 상한이 동시에 걸린다 — 셀 예산을 먼저 확인하라
------------------------------------------------------------------------------------------
여섯 편은 이미 마크다운 셀 21~24 개를 쓰고 있고 상한은 25 다(§5.7). 논문 블록을 **셀 3개로**
따로 붙이면 상한을 넘는다. 그래서 이 모듈은 **셀을 늘리지 않는 조립법**을 함께 준다.

    hdr = header(...)                                   # report_style
    hdr = attach(hdr, paper_map(...))                   # 셀 +0 (여는 블록 안으로 들어간다)
    ...
    blocks = [hdr, ..., paper_appendix(defence=..., methods=..., cites=[...]),  # 셀 +1
              next_steps([...])]

`paper_appendix()` 는 `<!--rs:paper-->` 태그를 달아 12줄 상한에서 면제된다(표가 길어서다).
셀 수·톤·출처 검사는 그대로 `build_notebook(..., strict=True)` 가 본다.

그림 규격(4.3) 을 쓰는 법
------------------------------------------------------------------------------------------
    from paper_kit import paper_style, save_figure
    with paper_style(width="single") as st:            # 3.5 in 1단 폭 · 9 pt 본문
        fig, ax = st.figure()
        for i, (name, y) in enumerate(series.items()):
            ax.plot(x, y, label=name, **st.series(i))  # 색 + 마커 + 선종 **이중부호화**
        ax.set_xlabel("Range [km]"); ax.set_ylabel("SNR [dB]")
        ax.legend()
    save_figure(fig, "outputs/figures/report05_f2_budget")   # PDF + 400 dpi PNG + 자체검사

`save_figure()` 는 벡터(PDF)와 300 dpi 이상 PNG 를 **한 번에** 저장하고, 저장 직전에
글자 크기·이중부호화·그림 속 한글을 검사한다. 검사 결과는 PDF 메타데이터에 심어 두므로
`check_figure("....pdf")` 로 **저장된 파일만 열어** 다시 확인할 수 있다.

`python src/paper_kit.py` 로 자기검사를, `python src/paper_kit.py extract` 로 추출을 돌린다.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import re
import sys
from contextlib import contextmanager
from typing import Any, Iterable, Sequence

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:                       # 빌더와 같은 임포트 규약
    sys.path.insert(0, _HERE)

from report_style import (                      # noqa: E402  (경로 삽입 뒤여야 한다)
    ROOT, Block, ContractError, assert_fig_text, grep_hedges, load_json, md,
)

__all__ = [
    "PaperError", "PAPER_TITLE", "CONTRIBUTION", "SECTIONS", "REPORT_SECTIONS",
    "PALETTE", "MARKERS", "LINESTYLES", "HATCHES", "COLUMN_IN", "MIN_FONT_PT",
    "MIN_PNG_DPI", "paper_rc", "paper_style", "series_style", "audit_figure",
    "save_figure", "check_figure", "greyscale_gaps", "figure_md",
    "paper_map", "defence", "methods", "cite", "REFERENCES", "cite_ref",
    "attach", "paper_appendix", "extract_paper_kit", "coverage_report",
    "DEFAULT_NOTEBOOKS", "PK_MARK",
]


class PaperError(ContractError):
    """논문 참고자료 규격(PAPER_SPEC §4) 위반. `ContractError` 의 자식이라 빌더는 한 번에 받는다."""


# --------------------------------------------------------------------------- #
#  0) 논문 좌표 — 좁힌 확정형(PAPER_SPEC §1·§3)
# --------------------------------------------------------------------------- #
PAPER_TITLE = ("Controlled Comparison of WiFi / LTE / 5G NR Illuminators of Opportunity "
               "for Passive Bistatic Drone Detection, with Calibrated False-Alarm Rates")

CONTRIBUTION = ("같은 표적·같은 검출기·교정된 Pfa 위에서 세 조명원을 통제 비교한다 "
                "— 기여는 엔진과 파이프라인 통합, 그리고 그 교정이다.")

#: PAPER_SPEC §3 의 절 이름. 여기 없는 이름을 쓰면 `paper_map()` 이 예외를 낸다.
SECTIONS: tuple[str, ...] = (
    "I. Introduction",
    "II. Related Work",
    "III-A. Target Model",
    "III-B. Illuminators",
    "IV. Detection Chain",
    "V. Results",
    "VI. Validation",
)

#: PAPER_SPEC §3 리포트 ↔ 절 대응. `extract_paper_kit()` 의 기본 배치이기도 하다.
REPORT_SECTIONS: dict[str, tuple[str, ...]] = {
    "report01_prior":        ("I. Introduction", "II. Related Work"),
    "report02_target":       ("III-A. Target Model",),
    "report03_illuminators": ("III-B. Illuminators",),
    "report04_detector":     ("IV. Detection Chain",),
    "report05_results":      ("V. Results",),
    "report06_measurement":  ("VI. Validation",),
}

#: 절 이름을 느슨하게 받아 정규형으로 바꾼다("V", "Results", "v. results" → "V. Results").
_SECTION_ALIAS: dict[str, str] = {}
for _s in SECTIONS:
    _num, _name = _s.split(". ", 1)
    for _a in (_s, _num, _name, f"{_num}.", _s.replace(". ", " ")):
        _SECTION_ALIAS[_a.strip().lower()] = _s
_SECTION_ALIAS["3a"] = _SECTION_ALIAS["iii-a"] = "III-A. Target Model"
_SECTION_ALIAS["3b"] = _SECTION_ALIAS["iii-b"] = "III-B. Illuminators"

#: PAPER_SPEC §2 가 뺀 것 — "최초" 류. 주장 문장에 있으면 막는다.
_BANNED_CLAIM = [
    (r"최초", "Rzewuski(NATO STO 2021)가 FDTD 로 같은 산출물을 냈다 — 우열은 엔진과 통합에 있다"),
    (r"처음으로", "같은 이유. '통제 비교를 했다' 로 크기를 맞춰라"),
    (r"세계 최초|국내 최초", "같은 이유"),
    (r"\bfirst\s+to\b", "PAPER_SPEC §2: any \"first to do X\" phrasing is OUT"),
    (r"\bthe\s+first\s+(?:work|paper|study)\b", "PAPER_SPEC §2 동일"),
]

#: H8(게재 전례 0편)을 건드리는 주장 — 두 단서(Q1·Q2)를 반드시 데리고 다녀야 한다.
_H8_TRIGGER = re.compile(
    r"전례가?\s*(?:0|없|하나도)|선례가?\s*(?:0|없)|게재된?\s*[^.]{0,12}0\s*편|"
    r"zero\s+published|no\s+published", re.I)
_H8_Q1 = "Rzewuski"
_H8_Q2 = re.compile(r"프리프린트|preprint|게재상태|published", re.I)
_H8_HELP = (
    "H8 은 **네 관문 그대로**(P1 게재 · P2 드론 표면메쉬 · P3 Sionna 급 GPU 광선엔진 · "
    "P4 진폭 검증) 일 때만 선다 ⟨outputs/prior_settled_h8.json⟩. 쓸 때마다 단서 두 개를 함께 적어라.\n"
    "  Q1 — Rzewuski(NATO STO-MP-MSG-SET-183, paper 13)가 FDTD 로 드론 바이스태틱 RCS 를 "
    "이미 냈다. '아무도 안 했다' 로 옮겨 적으면 그 자리에서 반박당한다.\n"
    "  Q2 — '게재'가 주장 전부를 진다. 프리프린트를 넣으면 간극은 이음매로 좁아진다"
    "(LAMBDA 는 UAV RCS 를 Sionna 경로 옆에 두고, Ziganshin 은 Sionna 안에서 메쉬 산란을 측정과 맞춘다).\n"
    "  → 두 단서를 `qualifications=[…]` 또는 근거 문장 안에 그대로 넣어라.")


def _canon_section(s: str) -> str:
    key = str(s).strip().lower().rstrip(".")
    if key in _SECTION_ALIAS:
        return _SECTION_ALIAS[key]
    raise PaperError(
        f"모르는 논문 절이다: {s!r}\n"
        f"  → PAPER_SPEC §3 의 절 이름 중 하나를 써라: {', '.join(SECTIONS)}")


def _no_hedge(where: str, *texts: str) -> None:
    """논문에 그대로 나갈 문장이다 — 완충어 0건(§5.8-3)."""
    for t in texts:
        h = grep_hedges(str(t))
        if h["count"]:
            first = h["hits"][0]
            raise PaperError(
                f"{where}: 완충어 '{first['hedge']}' (§5.8-3 은 0건이다)\n"
                f"  문장: \"{first['text'][:90]}\"\n"
                f"  → {first['fix']}\n"
                f"  ⭐ 논문에 그대로 옮길 문장이다. 표현이 아니라 **주장의 크기**를 고쳐라.")


def _check_claim(where: str, claim: str, support: Sequence[str] = ()) -> str:
    """논문에 쓸 문장 하나를 검사한다 — 빈 문장 · 질문 · '최초' 류 · H8 무단서 사용."""
    c = str(claim).strip()
    if not c:
        raise PaperError(f"{where}: 주장이 비었다. **논문에 쓸 문장 그대로** 적어라.")
    if c.endswith("?"):
        raise PaperError(
            f"{where}: 주장이 질문이다 — {c!r}\n"
            "  → 논문 본문에 들어갈 평서문으로 써라. 질문은 그림 캡션의 몫이다(`caption()`).")
    for pat, why in _BANNED_CLAIM:
        m = re.search(pat, c, re.I)
        if m:
            raise PaperError(
                f"{where}: PAPER_SPEC §2 가 뺀 '{m.group(0)}' 류 문구다 — {c!r}\n"
                f"  → {why}")
    if _H8_TRIGGER.search(c):
        joined = " ".join([c, *[str(s) for s in support]])
        missing = []
        if _H8_Q1 not in joined:
            missing.append("Q1(Rzewuski)")
        if not _H8_Q2.search(joined):
            missing.append("Q2(게재/프리프린트 구분)")
        if missing:
            raise PaperError(
                f"{where}: H8(게재 전례) 을 쓰면서 단서 {', '.join(missing)} 가 빠졌다 — {c!r}\n"
                + _H8_HELP)
    _no_hedge(where, c)
    return c


# --------------------------------------------------------------------------- #
#  1) 게재 품질 그림 (PAPER_SPEC §4.3)
#     · 벡터 PDF + 300 dpi 이상 PNG 를 **한 번에**
#     · 2단 축소 뒤에도 8 pt 이상
#     · 색맹 안전 팔레트 + **색 + 마커/선종 이중부호화**(흑백 인쇄에서 살아남는다)
# --------------------------------------------------------------------------- #
#: Okabe–Ito 색맹 안전 8색. 순서는 **앞 세 색의 흑백 명도차가 최대**가 되게 세웠다 —
#  이 논문의 기본형이 WiFi · LTE · 5G 세 계열이기 때문이다(앞 3색 최소 명도차 0.104).
#  4색을 넘어가면 명도차는 0.04 아래로 떨어진다. 그래서 색만으로는 절대 구분하지 않는다.
PALETTE: tuple[str, ...] = (
    "#0072B2",   # blue           L=0.153
    "#E69F00",   # orange         L=0.416
    "#009E73",   # bluish green   L=0.257
    "#CC79A7",   # reddish purple L=0.293
    "#56B4E9",   # sky blue       L=0.405
    "#D55E00",   # vermillion     L=0.222
    "#000000",   # black          L=0.000
    "#F0E442",   # yellow         L=0.744
)
#: 계열마다 **마커도 다르다** — 색을 잃어도 구분된다.
MARKERS: tuple[str, ...] = ("o", "s", "^", "D", "v", "P", "X", "*")
#: 계열마다 **선종도 다르다** — 마커 없는 선그림에서도 구분된다.
LINESTYLES: tuple[Any, ...] = (
    "-", "--", "-.", ":", (0, (5, 1, 1, 1)), (0, (3, 1, 1, 1, 1, 1)), (0, (7, 2)), (0, (1, 1)),
)
#: 막대·채움에는 해치를 겹친다.
HATCHES: tuple[str, ...] = ("", "//", "\\\\", "xx", "..", "++", "oo", "**")

#: IEEE 2단 조판 기준 폭(인치). `width=` 에 이 이름이나 숫자를 준다.
COLUMN_IN = {"single": 3.5, "double": 7.16, "half": 1.72}

#: 게재 하한 — 2단 축소 뒤에도 이 아래로 내려가면 되돌아온다.
MIN_FONT_PT = 8.0
MIN_PNG_DPI = 300
#: 흑백 인쇄에서 두 계열의 명도가 이보다 가까우면 색만으로는 못 가른다(참고 수치).
MIN_GREY_GAP = 0.10

PK_MARK = "pk"                    # `<!--pk:종류 {json}-->` 기계 판독 표지


def _width_in(width) -> float:
    if isinstance(width, str):
        if width not in COLUMN_IN:
            raise PaperError(
                f"모르는 폭 이름 {width!r} — {list(COLUMN_IN)} 중에서 고르거나 인치 숫자를 줘라.")
        return float(COLUMN_IN[width])
    w = float(width)
    if w <= 0:
        raise PaperError(f"그림 폭이 0 이하다: {w}")
    return w


def paper_rc(width="single", base_pt: float = 9.0, aspect: float = 0.66,
             **overrides) -> dict:
    """게재 규격 rcParams 를 **딕셔너리로** 돌려준다(`plt.rcParams.update()` 로도 쓸 수 있다).

    base_pt 는 축 라벨·본문 글자다. 눈금·범례는 그보다 1 pt 작게 잡되 `MIN_FONT_PT` 아래로는
    내려가지 않는다 — 그 아래는 조판 축소에서 살아남지 못한다.
    """
    if base_pt < MIN_FONT_PT:
        raise PaperError(
            f"본문 글자 {base_pt} pt < 하한 {MIN_FONT_PT} pt (PAPER_SPEC §4.3).\n"
            "  → 글자를 줄이지 말고 그림을 나누거나 폭을 double 로 키워라.")
    small = max(MIN_FONT_PT, base_pt - 1.0)
    w = _width_in(width)
    rc = {
        "figure.figsize": (w, w * aspect),
        "figure.dpi": 150,
        "savefig.dpi": 400,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.02,
        "savefig.facecolor": "white",
        "figure.facecolor": "white",
        # 그림 속 글자는 영어다(하우스 규약) — 한글 폰트를 걸지 않는다.
        "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans"],
        "font.size": base_pt,
        "axes.titlesize": base_pt,
        "axes.labelsize": base_pt,
        "xtick.labelsize": small,
        "ytick.labelsize": small,
        "legend.fontsize": small,
        "figure.titlesize": base_pt,
        "axes.unicode_minus": False,
        # 선·마커: 축소해도 보이는 두께
        "lines.linewidth": 1.4,
        "lines.markersize": 4.0,
        "lines.markeredgewidth": 0.8,
        "patch.linewidth": 0.8,
        "axes.linewidth": 0.8,
        "xtick.major.width": 0.8,
        "ytick.major.width": 0.8,
        "xtick.direction": "out",
        "ytick.direction": "out",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.linewidth": 0.5,
        "grid.alpha": 0.35,
        "legend.frameon": False,
        "legend.handlelength": 2.4,
        "legend.borderaxespad": 0.3,
        # ⭐ Type-3 금지: 학회 조판 검사가 되돌려 보내는 첫 번째 이유다.
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
        "pdf.compression": 6,
        "text.usetex": False,
    }
    from cycler import cycler                    # ⭐ 기본 순환에 마커·선종을 함께 실어
    n = len(PALETTE)                             #    그냥 plot() 해도 이중부호화가 된다
    rc["axes.prop_cycle"] = (cycler(color=list(PALETTE))
                             + cycler(marker=list(MARKERS[:n]))
                             + cycler(linestyle=list(LINESTYLES[:n])))
    rc.update(overrides)
    return rc


class PaperStyle:
    """`paper_style()` 이 넘겨주는 손잡이 — 폭·figsize·계열 스타일을 갖고 있다."""

    def __init__(self, width, base_pt, aspect, rc):
        self.width_in = _width_in(width)
        self.base_pt = base_pt
        self.aspect = aspect
        self.rc = rc
        self.figsize = rc["figure.figsize"]

    def figure(self, nrows: int = 1, ncols: int = 1, height: float | None = None, **kw):
        """`plt.subplots()` 를 규격 폭으로 부른다. 반환은 그대로 `(fig, ax…)`."""
        import matplotlib.pyplot as plt
        h = height if height is not None else self.width_in * self.aspect * (
            1.0 if nrows == 1 else 0.72 * nrows)
        kw.setdefault("figsize", (self.width_in, h))
        kw.setdefault("constrained_layout", True)
        return plt.subplots(nrows, ncols, **kw)

    def series(self, i: int, marker: bool = True) -> dict:
        """i 번째 계열의 **이중부호화** 스타일 — `dict(color=…, marker=…, linestyle=…)`."""
        return series_style(i, marker=marker)

    def color(self, i: int) -> str:
        return PALETTE[i % len(PALETTE)]

    def hatch(self, i: int) -> str:
        return HATCHES[i % len(HATCHES)]


@contextmanager
def paper_style(width="single", base_pt: float = 9.0, aspect: float = 0.66, **overrides):
    """게재 규격 rcParams 를 **그 블록 안에서만** 건다(§4.3).

        with paper_style(width="single") as st:
            fig, ax = st.figure()
            ax.plot(x, y, label="WiFi", **st.series(0))
        save_figure(fig, "outputs/figures/report05_f2_budget")

    ⚠ 그림 객체(글자 크기·색)는 **만들어질 때** rcParams 를 읽는다. 그리는 코드는 전부
      이 블록 안에 두어라. 저장은 밖에서 해도 된다 — `save_figure()` 가 값을 직접 넘긴다.
    """
    import matplotlib
    if matplotlib.get_backend().lower() not in ("agg", "module://matplotlib_inline.backend_inline"):
        matplotlib.use("Agg")                    # 헤드리스 저장
    import matplotlib.pyplot as plt
    rc = paper_rc(width, base_pt=base_pt, aspect=aspect, **overrides)
    with plt.rc_context(rc):
        yield PaperStyle(width, base_pt, aspect, rc)


def series_style(i: int, marker: bool = True) -> dict:
    """i 번째 계열: **색 + 마커 + 선종**. 흑백으로 찍어도 계열이 구분된다."""
    n = len(PALETTE)
    st = {"color": PALETTE[i % n], "linestyle": LINESTYLES[i % n]}
    if marker:
        st["marker"] = MARKERS[i % n]
    return st


# ── 명도(흑백 환산) ───────────────────────────────────────────────────────────
def _luminance(color) -> float:
    """sRGB 상대 휘도(0=검정, 1=흰색). 흑백 인쇄에서 그 색이 얼마나 진한가."""
    from matplotlib.colors import to_rgb
    r, g, b = to_rgb(color)

    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def greyscale_gaps(colors: Sequence = PALETTE) -> dict:
    """색 목록의 **흑백 환산 명도**와 이웃 간 최소 간격. 팔레트 점검용."""
    lums = [(str(c), round(_luminance(c), 4)) for c in colors]
    order = sorted(lums, key=lambda t: t[1])
    gaps = [round(order[i + 1][1] - order[i][1], 4) for i in range(len(order) - 1)]
    return {"luminance": lums, "sorted": order, "min_gap": min(gaps) if gaps else None,
            "gaps": gaps, "advice_min_gap": MIN_GREY_GAP}


# ── 살아있는 Figure 감사 ──────────────────────────────────────────────────────
def _marker_key(m) -> str:
    if m is None:
        return "none"
    s = str(m)
    return "none" if s in ("None", "none", "", " ") else s


def _ls_key(ls) -> str:
    if isinstance(ls, tuple):
        return f"dash{ls[1]}"
    s = str(ls)
    return {"solid": "-", "dashed": "--", "dashdot": "-.", "dotted": ":"}.get(s, s)


def _axes_series(ax) -> list[dict]:
    """한 축의 '계열'을 모은다 — 선 · 산점 · 막대. 밑줄(_)로 시작하는 라벨은 보조물로 본다."""
    from matplotlib.colors import to_hex
    out: list[dict] = []
    for ln in ax.get_lines():
        lbl = str(ln.get_label())
        if lbl.startswith("_"):
            continue
        try:
            col = to_hex(ln.get_color())
        except Exception:                                    # noqa: BLE001
            col = str(ln.get_color())
        out.append({"kind": "line", "label": lbl, "color": col,
                    "marker": _marker_key(ln.get_marker()),
                    "linestyle": _ls_key(ln.get_linestyle())})
    for coll in getattr(ax, "collections", []):
        lbl = str(coll.get_label())
        if lbl.startswith("_"):
            continue
        try:
            fc = coll.get_facecolor()
            col = to_hex(fc[0]) if len(fc) else "none"
        except Exception:                                    # noqa: BLE001
            col = "unknown"
        paths = getattr(coll, "get_paths", lambda: [])()
        pk = f"path{len(paths[0].vertices)}" if paths else "none"
        out.append({"kind": "scatter", "label": lbl, "color": col,
                    "marker": pk, "linestyle": "none"})
    for cont in getattr(ax, "containers", []):
        patches = list(getattr(cont, "patches", []) or [])
        if not patches:
            continue
        lbl = str(cont.get_label()) if hasattr(cont, "get_label") else "_bars"
        if lbl.startswith("_"):
            continue
        p = patches[0]
        try:
            col = to_hex(p.get_facecolor())
        except Exception:                                    # noqa: BLE001
            col = "unknown"
        out.append({"kind": "bar", "label": lbl, "color": col,
                    "marker": p.get_hatch() or "none", "linestyle": "bar"})
    return out


def _colour_only(series: Sequence[dict]) -> list[dict]:
    """**색만으로 구분된 계열**을 찾아낸다 — 흑백 인쇄에서 사라지는 바로 그 실패."""
    bad: list[dict] = []
    by_key: dict[tuple, list[dict]] = {}
    for s in series:
        by_key.setdefault((s["kind"], s["marker"], s["linestyle"]), []).append(s)
    for key, group in by_key.items():
        colors = {s["color"] for s in group}
        if len(group) >= 2 and len(colors) >= 2:
            lums = sorted(_luminance(c) for c in colors)
            bad.append({
                "labels": [s["label"] for s in group],
                "shared_encoding": {"kind": key[0], "marker": key[1], "linestyle": key[2]},
                "colors": sorted(colors),
                "min_greyscale_gap": round(min(b - a for a, b in zip(lums, lums[1:])), 4),
            })
    return bad


def audit_figure(fig, min_pt: float = MIN_FONT_PT) -> dict:
    """살아있는 Figure 를 감사한다 — **가장 작은 글자**와 **색만으로 구분된 계열**.

    반환 dict 의 `ok` 가 두 검사의 결론이다. 그림 속 한글은 여기서 예외로 막는다(하우스 규약).
    """
    import matplotlib.text as mtext
    fig.canvas.draw()                              # 눈금 라벨이 실제로 만들어지게 한다

    texts: list[dict] = []
    for t in fig.findobj(mtext.Text):
        s = t.get_text()
        if not s or not str(s).strip() or not t.get_visible():
            continue
        texts.append({"text": str(s), "pt": round(float(t.get_fontsize()), 3)})
    assert_fig_text(*[t["text"] for t in texts])   # 그림 글자는 전부 영어

    smallest = min((t["pt"] for t in texts), default=None)
    tiny = sorted([t for t in texts if t["pt"] < min_pt - 1e-9],
                  key=lambda t: t["pt"])[:8]

    series: list[dict] = []
    for ax in fig.get_axes():
        series += _axes_series(ax)
    colour_only = _colour_only(series)

    w_in, h_in = (float(x) for x in fig.get_size_inches())
    return {
        "n_texts": len(texts), "min_font_pt": smallest, "min_font_required_pt": min_pt,
        "too_small": tiny, "n_series": len(series), "series": series,
        "colour_only_series": colour_only,
        "figsize_in": [round(w_in, 3), round(h_in, 3)],
        "palette_is_cvd_safe": all(s["color"].upper() in {c.upper() for c in PALETTE}
                                   for s in series) if series else None,
        "ok": (smallest is None or smallest >= min_pt - 1e-9) and not colour_only,
    }


def _payload(obj: Any) -> str:
    """마크다운/메타데이터에 심을 JSON 한 줄. `-->` 로 표지가 끊기지 않게 막는다."""
    return json.dumps(obj, ensure_ascii=False).replace("-->", "--\\u003e")


def save_figure(fig, stem: str, dpi: int = 400, formats: Sequence[str] = ("pdf", "png"),
                caption: str | None = None, title: str | None = None,
                placed_width_in: float | None = None,
                strict: bool = True, close: bool = False) -> dict:
    """게재 규격으로 **한 번에** 저장한다 — 벡터 PDF + `dpi` PNG(§4.3).

    파라미터
    --------
    stem   : 확장자 없는 경로. `outputs/figures/report05_f2_budget` 처럼 준다.
    dpi    : PNG 해상도. `MIN_PNG_DPI`(300) 미만이면 예외.
    caption: **논문에 그대로 붙일 완결 문장**(§4.3). PDF 메타데이터에 심어 두므로 원고를
             쓸 때 `extract_paper_kit()` 이 그대로 실어 온다. (노트북 캡션은 그 그림이 답하는
             *질문*이다 — 둘은 다른 물건이고 둘 다 있어야 한다.)
    placed_width_in: 조판에서 이 그림이 놓일 폭(인치). 주면 **축소 후** 글자 크기로 판정한다
             — 7.16 in 그림을 1단(3.5 in)에 넣으면 8 pt 는 3.9 pt 가 된다.
    strict : 감사 실패(8 pt 미만 · 색만으로 구분된 계열)면 **저장 전에** 예외.

    반환: `dict(pdf=…, png=…, audit=…, check=…)`.
    감사 결과는 PDF 메타데이터(Keywords)에 심어 두므로 `check_figure()` 가 **파일만 열어**
    다시 확인한다 — 그림을 만든 코드가 사라져도 검증이 남는다.
    """
    if int(dpi) < MIN_PNG_DPI:
        raise PaperError(f"PNG {dpi} dpi < 하한 {MIN_PNG_DPI} dpi (PAPER_SPEC §4.3).")
    fmts = [f.lower().lstrip(".") for f in formats]
    if "pdf" not in fmts and "svg" not in fmts:
        raise PaperError("벡터 형식(pdf 또는 svg)을 함께 저장해야 한다 (PAPER_SPEC §4.3).")

    audit = audit_figure(fig)
    if placed_width_in:                          # 조판 축소를 미리 반영해 판정한다
        red = float(placed_width_in) / float(audit["figsize_in"][0])
        audit["placed_width_in"] = float(placed_width_in)
        audit["reduction"] = round(red, 4)
        audit["effective_min_font_pt"] = (round(audit["min_font_pt"] * red, 3)
                                          if audit["min_font_pt"] is not None else None)
        if audit["effective_min_font_pt"] is not None \
                and audit["effective_min_font_pt"] < MIN_FONT_PT - 1e-9:
            audit["too_small"] = audit["too_small"] or [
                {"text": "(축소 후)", "pt": audit["effective_min_font_pt"]}]
            audit["ok"] = False
    if strict and not audit["ok"]:
        why = []
        if audit["too_small"]:
            why.append(
                f"글자 {audit['min_font_pt']} pt"
                + (f" → 배치 폭 {placed_width_in} in 에서 "
                   f"{audit.get('effective_min_font_pt')} pt" if placed_width_in else "")
                + f" < {MIN_FONT_PT} pt — "
                + ", ".join(f"{t['text'][:18]!r}({t['pt']})" for t in audit["too_small"][:4]))
        for c in audit["colour_only_series"]:
            why.append(
                f"색만으로 구분된 계열 {c['labels']} — 같은 (마커={c['shared_encoding']['marker']}, "
                f"선종={c['shared_encoding']['linestyle']}), 흑백 명도차 {c['min_greyscale_gap']}")
        raise PaperError(
            "게재 품질 검사 실패 (PAPER_SPEC §4.3) — " + stem + "\n  " + "\n  ".join(why)
            + "\n  → 글자는 `paper_style(base_pt=…)` 로 키우고, 계열은 `st.series(i)` 로 "
              "**색 + 마커/선종** 이중부호화하라. 흑백 인쇄에서 색은 사라진다.")

    p = stem if os.path.isabs(stem) else os.path.join(ROOT, stem)
    p = os.path.splitext(p)[0]
    os.makedirs(os.path.dirname(p) or ".", exist_ok=True)

    meta = {"caption": caption, "audit": audit, "made_by": "src/paper_kit.py",
            "min_font_pt": audit["min_font_pt"], "dpi_png": int(dpi),
            "saved": _dt.datetime.now().strftime("%Y-%m-%d %H:%M")}
    payload = _payload(meta)

    out: dict = {"audit": audit, "caption": caption}
    for f in fmts:
        path = f"{p}.{f}"
        if f == "png":
            fig.savefig(path, dpi=int(dpi), bbox_inches="tight",
                        metadata={"Software": "sionna2/src/paper_kit.py",
                                  "Description": payload})
        elif f in ("pdf", "svg"):
            fig.savefig(path, bbox_inches="tight",
                        metadata={"Title": title or os.path.basename(p),
                                  "Creator": "sionna2/src/paper_kit.py",
                                  "Keywords": payload})
        else:
            fig.savefig(path, dpi=int(dpi), bbox_inches="tight")
        out[f] = os.path.relpath(path, ROOT) if not os.path.isabs(stem) else path
    if close:
        import matplotlib.pyplot as plt
        plt.close(fig)
    if "pdf" in out:
        out["check"] = check_figure(out["pdf"], placed_width_in=placed_width_in)
    return out


def figure_md(path: str, fig_no: int | str, question: str,
              paper_caption: str | None = None, report: str | None = None) -> Block:
    """그림 한 장을 노트북에 끼운다 — **질문 캡션**(리포트)과 **완결 문장 캡션**(논문)을 함께 단다.

    두 계약이 캡션에 서로 다른 것을 요구한다. 둘 다 만족시키는 것이 이 함수다.

    | 어디 | 무엇 | 근거 |
    |---|---|---|
    | 노트북 캡션 | 그 그림이 답하는 **질문** | REBUILD §5.6-2 (`caption()`) |
    | 논문 캡션 | 그대로 붙일 수 있는 **완결 문장** | PAPER_SPEC §4.3 |

    `paper_caption` 은 화면에 안 보이는 표지로 실려 `extract_paper_kit()` 이 절 단위로 모은다.
    """
    from report_style import caption as _caption
    p = path if os.path.isabs(path) else os.path.join(ROOT, path)
    if not os.path.exists(p):
        raise PaperError(f"§4.3: 그림 파일이 없다 — {path} (기대 경로: {p})")
    cap = _caption(fig_no, question)                     # 질문인지 여기서 검사된다
    pdf = os.path.splitext(p)[0] + ".pdf"
    pc = str(paper_caption).strip() if paper_caption else None
    if pc:
        if pc.endswith("?"):
            raise PaperError(
                f"§4.3: 논문 캡션은 **완결 문장**이다 — 질문이 아니다: {pc!r}\n"
                "  → 질문은 노트북 캡션(`question=`)이 맡는다. 여기엔 그림이 말하는 사실을 적어라.")
        if len(pc.split()) < 5:
            raise PaperError(f"§4.3: 논문 캡션이 너무 짧다(5낱말 이상) — {pc!r}")
        _no_hedge("§4.3 논문 캡션", pc)
    payload = {"kind": "figure", "path": path, "figure_no": str(fig_no),
               "question": str(question).strip(), "paper_caption": pc,
               "vector_pdf": os.path.relpath(pdf, ROOT) if os.path.exists(pdf) else None,
               "report": report}
    return Block("\n".join([f"<!--{PK_MARK}:figure {_payload(payload)}-->",
                            f"![{os.path.basename(path)}]({path})", "", cap]))


# ── 저장된 파일만 열어서 하는 검사 ────────────────────────────────────────────
def _pdf_text_sizes(page) -> list[float]:
    sizes = []
    for b in page.get_text("dict").get("blocks", []):
        for ln in b.get("lines", []):
            for sp in ln.get("spans", []):
                if str(sp.get("text", "")).strip():
                    sizes.append(round(float(sp.get("size", 0.0)), 3))
    return sizes


def _pdf_series_heuristic(page) -> dict:
    """메타데이터가 없는 PDF 를 **그림 자체에서** 읽는다(발견적).

    선 색깔별로 파선 패턴과 마커(작은 채움 도형) 유무를 모은다. 두 색이 같은 서명을 가지면
    **색만으로 구분된 계열**로 의심한다.
    """
    groups: dict[str, dict] = {}
    for d in page.get_drawings():
        col = d.get("color")
        if col is None or len(col) < 3:
            continue
        r, g_, b = (float(x) for x in col[:3])
        if abs(r - g_) < 1e-3 and abs(g_ - b) < 1e-3:
            continue                     # 축·눈금·격자는 무채색이다 — 계열 후보가 아니다
        key = f"{r:.3f},{g_:.3f},{b:.3f}"
        g = groups.setdefault(key, {"dashes": set(), "n": 0, "fills": 0})
        g["n"] += 1
        g["dashes"].add(str(d.get("dashes") or "[] 0"))
        if d.get("fill") is not None:
            g["fills"] += 1
    cand = groups
    sig: dict[tuple, list[str]] = {}
    for k, v in cand.items():
        sig.setdefault((tuple(sorted(v["dashes"])), v["fills"] > 0), []).append(k)
    suspect = [{"colors": v, "shared": {"dashes": list(s[0]), "has_marker": s[1]}}
               for s, v in sig.items() if len(v) >= 2]
    return {"method": "pdf-geometry (heuristic)", "n_stroke_colors": len(cand),
            "colour_only_suspected": suspect}


def check_figure(path: str, placed_width_in: float | None = None,
                 min_pt: float = MIN_FONT_PT) -> dict:
    """**저장된 그림 파일을 열어** 게재 규격을 잰다(§4.3).

    파라미터
    --------
    path            : `.pdf`(권장) · `.png`. 상대경로는 리포지토리 루트 기준.
    placed_width_in : 조판에서 그림이 놓일 폭(인치). 주면 **축소 후 유효 글자 크기**를 낸다
                      — 7.16 in 그림을 1단(3.5 in)에 넣으면 8 pt 는 3.9 pt 가 된다.

    반환 dict 의 두 열쇠가 "되돌아오는 이유" 그대로다.
      · `min_font_pt` / `effective_min_font_pt` — 가장 작은 글자
      · `colour_only_series`                    — 색만으로 구분된 계열
    """
    p = path if os.path.isabs(path) else os.path.join(ROOT, path)
    if not os.path.exists(p):
        raise PaperError(f"검사할 그림이 없다: {path} (기대 경로: {p})")
    ext = os.path.splitext(p)[1].lower()
    rep: dict = {"path": os.path.relpath(p, ROOT) if not os.path.isabs(path) else p,
                 "format": ext.lstrip("."), "min_font_required_pt": min_pt}

    if ext == ".png":
        from PIL import Image
        with Image.open(p) as im:
            dpi = im.info.get("dpi", (None, None))[0]
            rep.update(pixels=list(im.size), dpi=round(float(dpi), 1) if dpi else None)
        sib = os.path.splitext(p)[0] + ".pdf"
        V = [] if (rep["dpi"] or 0) >= MIN_PNG_DPI else [f"PNG {rep['dpi']} dpi < {MIN_PNG_DPI} dpi"]
        if os.path.exists(sib):
            # 벡터본이 있으면 글자·이중부호화 판정은 그쪽이 한다 — 여기서는 해상도만 본다.
            rep["vector_pdf"] = os.path.relpath(sib, ROOT)
            rep["hint"] = f"글자·이중부호화는 `check_figure({rep['vector_pdf']!r})` 로 본다"
        else:
            V.append("벡터본이 없다 — 같은 그림을 PDF 로도 저장하라 "
                     "(`save_figure()` 는 둘을 함께 만든다)")
        rep.update(min_font_pt=None, effective_min_font_pt=None,
                   colour_only_series="unknown (raster)", violations=V, ok=not V)
        return rep

    if ext not in (".pdf",):
        raise PaperError(f"검사할 수 있는 형식은 .pdf · .png 다 — {path}")

    import fitz
    doc = fitz.open(p)
    try:
        page = doc[0]
        w_in, h_in = page.rect.width / 72.0, page.rect.height / 72.0
        sizes = _pdf_text_sizes(page)
        smallest = min(sizes) if sizes else None
        scale = (float(placed_width_in) / w_in) if placed_width_in else 1.0
        eff = round(smallest * scale, 3) if smallest is not None else None

        embedded = None
        kw = (doc.metadata or {}).get("keywords") or ""
        if kw.strip().startswith("{"):
            try:
                embedded = json.loads(kw)
            except json.JSONDecodeError:
                embedded = None

        V: list[str] = []
        if smallest is None:
            V.append("PDF 안에 글자가 없다 — 텍스트가 곡선으로 변환됐는지 확인하라 "
                     "(`svg.fonttype='none'` · `pdf.fonttype=42`)")
        elif (eff or smallest) < min_pt - 1e-9:
            V.append(f"가장 작은 글자 {smallest} pt"
                     + (f" → 배치 폭 {placed_width_in} in 에서 {eff} pt" if placed_width_in else "")
                     + f" < {min_pt} pt")

        if embedded and isinstance(embedded.get("audit"), dict):
            a = embedded["audit"]
            colour_only = a.get("colour_only_series", [])
            source = "embedded audit (save_figure)"
            rep["series"] = a.get("series", [])
            rep["caption"] = embedded.get("caption")
        else:
            h = _pdf_series_heuristic(page)
            colour_only = h["colour_only_suspected"]
            source = h["method"]
            rep["n_stroke_colors"] = h["n_stroke_colors"]
        if colour_only:
            V.append(f"색만으로 구분된 계열 {len(colour_only)}건 ({source}) — "
                     "마커나 선종을 함께 바꿔라. 흑백 인쇄에서 색은 사라진다")

        png = os.path.splitext(p)[0] + ".png"
        if os.path.exists(png):
            from PIL import Image
            with Image.open(png) as im:
                d = im.info.get("dpi", (None, None))[0]
            rep["png_dpi"] = round(float(d), 1) if d else None
            if (rep["png_dpi"] or 0) < MIN_PNG_DPI:
                V.append(f"짝 PNG {rep['png_dpi']} dpi < {MIN_PNG_DPI} dpi")
        else:
            V.append("짝 PNG 가 없다 — 노트북에 끼울 래스터본을 함께 저장하라")

        rep.update(page_size_in=[round(w_in, 3), round(h_in, 3)],
                   n_text_spans=len(sizes), min_font_pt=smallest,
                   placed_width_in=placed_width_in, reduction=round(scale, 4),
                   effective_min_font_pt=eff, font_sizes=sorted(set(sizes)),
                   colour_only_series=colour_only, encoding_source=source,
                   embedded_audit=bool(embedded), violations=V, ok=not V)
        return rep
    finally:
        doc.close()


# --------------------------------------------------------------------------- #
#  2) 논문 대응 블록 (PAPER_SPEC §4.1)
# --------------------------------------------------------------------------- #
_EVIDENCE_OK = re.compile(
    r"(그림|표|Fig\.?|Table|§|outputs/[^\s]+\.(?:json|npz)|src/[^\s]+\.py:\d+)", re.I)
_EVIDENCE_JSON = re.compile(r"(outputs/[^\s:,·`]+\.(?:json|npz))")


def _evidence_exists(where: str, *items: str) -> None:
    """근거가 가리키는 `outputs/*.json` 이 **디스크에 있는지** 확인한다.

    ⭐ 아직 안 만들어진 산출물을 근거로 적으면, 그 주장은 지금 지지되지 않는 주장이다.
       그런 항목은 주장이 아니라 **다음 단계 표**로 간다(REBUILD §5.3).
    """
    for it in items:
        for m in _EVIDENCE_JSON.finditer(str(it)):
            rel = m.group(1)
            p = rel if os.path.isabs(rel) else os.path.join(ROOT, rel)
            if not os.path.exists(p):
                raise PaperError(
                    f"{where}: 근거로 적은 산출물이 디스크에 없다 — {rel}\n"
                    f"  (기대 경로: {p})\n"
                    "  → 그 실험을 먼저 돌리거나, 이 항목을 **다음 단계 표**로 옮겨라"
                    "(REBUILD §5.3: `다음에 할 일 | 그러면 결정되는 것 | 어디서`).\n"
                    "  ⭐ 아직 없는 파일을 근거로 단 주장은 지금 지지되지 않는 주장이다.")


def paper_map(section, claim: str, evidence: Sequence[str],
              qualifications: Sequence[str] = (), report: str | None = None) -> Block:
    """§4.1 **논문 대응 블록** — 이 편이 먹이는 절 · 그 절의 주장 · 그 주장을 지지하는 그림/표.

    파라미터
    --------
    section : `"V. Results"` 같은 절 이름(느슨하게 받는다: `"V"`, `"Results"`). 여러 절이면 리스트.
    claim   : **논문에 쓸 문장 그대로**. 질문·완충어·"최초" 류는 예외다(PAPER_SPEC §2).
    evidence: 그 주장을 지지하는 것들 — `["그림 3", "표 2", "outputs/verify_cfar.json:calib.pfa"]`.
              각 항목은 그림/표 번호 · § 번호 · `outputs/*.json` · `src/*.py:줄` 중 하나를 가리켜야 한다.
    qualifications: 함께 나가야 하는 단서. H8(게재 전례) 을 쓰면 Q1(Rzewuski)·Q2(게재/프리프린트)가 필수다.

    반환은 `Block` 이라 그대로 노트북에 넣어도 되고, `attach(header, …)` 로 여는 블록에
    합쳐 **셀을 늘리지 않고** 넣어도 된다.
    """
    secs = [section] if isinstance(section, str) else list(section or [])
    if not secs:
        raise PaperError("§4.1: 이 편이 먹이는 **논문 절**이 비었다. "
                         f"{', '.join(SECTIONS)} 중에서 골라라.")
    secs = [_canon_section(s) for s in secs]

    E = [str(e).strip() for e in (evidence or []) if str(e).strip()]
    if not E:
        raise PaperError(
            "§4.1: **근거가 비었다** — 주장 하나에는 그것을 지지하는 그림/표/JSON 이 붙는다.\n"
            "  → evidence=['그림 3', '표 2', 'outputs/verify_cfar.json:calibration.pfa_emp']")
    bad = [e for e in E if not _EVIDENCE_OK.search(e)]
    if bad:
        raise PaperError(
            f"§4.1: 근거가 무엇을 가리키는지 알 수 없다 — {bad}\n"
            "  → 그림/표 번호(`그림 3`·`표 2`) · 절 번호(`§3.2`) · "
            "`outputs/*.json:키` · `src/*.py:줄` 중 하나로 적어라.")

    _evidence_exists("§4.1 논문 대응", *E)
    Q = [str(q).strip() for q in (qualifications or []) if str(q).strip()]
    c = _check_claim("§4.1 논문 대응", claim, [*E, *Q])
    _no_hedge("§4.1 논문 대응", *E, *Q)

    payload = {"kind": "paper_map", "sections": secs, "claim": c,
               "evidence": E, "qualifications": Q, "report": report}
    L = [f"<!--{PK_MARK}:paper_map {_payload(payload)}-->",
         "> **논문 대응** · " + " · ".join(f"**{s}**" for s in secs),
         ">",
         f"> 주장 — {c}",
         "> 근거 — " + " · ".join(f"`{e}`" if _EVIDENCE_OK.match(e) and "/" in e else e
                                  for e in E)]
    if Q:
        L += ["> 단서 — " + " · ".join(Q)]
    return Block("\n".join(L))


# --------------------------------------------------------------------------- #
#  3) 방어선 표 (PAPER_SPEC §4.2)
# --------------------------------------------------------------------------- #
_DEF_COLS = ("주장", "근거", "공격", "답")
_NEG_END = ("않는다", "않았다", "않다", "못한다", "못했다", "아니다", "없다", "없었다")


def _ends_neg(s: str) -> str | None:
    t = str(s).rstrip(" \t.。!?)]}'\"’”*_`·…")
    for e in _NEG_END:
        if t.endswith(e):
            return e
    return None


def defence(rows: Sequence, sec: str | None = None, report: str | None = None) -> Block:
    """§4.2 **방어선 표** — `주장 | 근거 | 공격 | 답`. 각 편 끝에 붙인다.

    rows: `[(주장, 근거, 공격, 답), …]` 또는 같은 키를 가진 딕셔너리 목록.

    ⭐ **공격과 답이 이 표의 존재 이유다.** 심사자가 때릴 지점을 안 적은 주장은 아직 생각하지
       않은 주장이고, 그런 행은 예외로 막는다.

    걸리는 것
    ---------
    · 네 칸 중 하나라도 빔 · 근거가 그림/표/JSON 을 안 가리킴 · "최초" 류 문구
    · 주장·답이 **부정 종결**(§5.8-1: 리포트 전체 상한 3개를 이 표 혼자 태우게 두지 않는다)
    · 완충어(§5.8-3)
    """
    R: list[tuple[str, str, str, str]] = []
    for it in rows or []:
        if isinstance(it, dict):
            vals = [str(it.get(k, "")).strip() for k in _DEF_COLS]
        elif isinstance(it, (tuple, list)):
            vals = [str(v).strip() for v in it]
        else:
            raise PaperError(f"§4.2: 행은 (주장, 근거, 공격, 답) 4칸이다 — {it!r}")
        if len(vals) != 4:
            raise PaperError(
                f"§4.2: 행이 {len(vals)}칸이다 — `주장 | 근거 | 공격 | 답` 네 칸이어야 한다.\n"
                f"  {it!r}")
        R.append(tuple(vals))                                    # type: ignore[arg-type]
    if not R:
        raise PaperError(
            "§4.2: 방어선 표가 비었다.\n"
            "  → 각 편의 주장마다 한 행: (논문에 쓸 문장, 그림/표+JSON, 심사자의 반론, 우리 답).")

    for i, (claim, ev, atk, ans) in enumerate(R, 1):
        where = f"§4.2 방어선 {i}행"
        if not ev:
            raise PaperError(f"{where}: **근거**가 비었다 — 그림/표 번호와 `outputs/*.json` 키를 적어라.")
        if not atk:
            raise PaperError(
                f"{where}: **공격**이 비었다 — {claim!r}\n"
                "  ⭐ 심사자가 때릴 지점을 적지 않은 주장은 아직 생각하지 않은 주장이다. "
                "이 표는 그것을 미리 적어두려고 있는 것이다(PAPER_SPEC §4.2).\n"
                "  → 그 문장을 읽은 심사자가 가장 먼저 할 반론을 그대로 적어라.")
        if not ans:
            raise PaperError(
                f"{where}: **답**이 비었다 — 공격 \"{atk[:60]}\" 에 대한 우리 대응과 그 근거를 적어라.\n"
                "  → 답에는 반드시 근거가 붙는다: '…이고 그 크기는 X dB 다 ⟨outputs/….json : 키⟩'.")
        if not _EVIDENCE_OK.search(ev):
            raise PaperError(
                f"{where}: 근거가 무엇을 가리키는지 알 수 없다 — {ev!r}\n"
                "  → `그림 3` · `표 2` · `§3.2` · `outputs/*.json:키` · `src/*.py:줄`.")
        _evidence_exists(where, ev, ans)
        _check_claim(where + " 주장", claim, [ev, atk, ans])
        _no_hedge(where, ev, atk, ans)
        for col, txt in (("주장", claim), ("답", ans)):
            e = _ends_neg(txt)
            if e:
                raise PaperError(
                    f"{where}: '{col}' 이 부정 종결('{e}') 이다 — {txt!r}\n"
                    "  → 무엇을 **했는지**로 뒤집어라(§5.0). 리포트 전체 부정문 상한은 3개다.\n"
                    "     '절대 σ 는 검증되지 않았다' → '레벨은 Das 측정 기울기에 맞췄고 "
                    "절대 레벨은 세 밴드 공통이라 순위에서 상쇄된다'")

    payload = {"kind": "defence", "report": report,
               "rows": [dict(zip(_DEF_COLS, r)) for r in R]}
    head = f"## {sec} 방어선" if sec else "## 방어선 — 심사자가 때릴 지점과 우리 답"
    # 첫 줄의 `<!--rs:paper-->` 는 **셀 태그**다(표가 길어 12줄 상한에서 면제된다).
    L = ["<!--rs:paper-->",
         f"<!--{PK_MARK}:defence {_payload(payload)}-->",
         head, "",
         "| " + " | ".join(_DEF_COLS) + " |", "|---|---|---|---|"]
    L += ["| " + " | ".join(c.replace("|", r"\|").replace("\n", " ") for c in r) + " |"
          for r in R]
    return Block("\n".join(L))


# --------------------------------------------------------------------------- #
#  4) 방법 문단 (PAPER_SPEC §4.4)
# --------------------------------------------------------------------------- #
#: 재현에 필요한 **파라미터** 후보 — 숫자 + 단위, 또는 `이름 = 값`.
_PARAM_UNIT = re.compile(
    r"(?<![\w.])[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?\s*"
    r"(?:GHz|MHz|kHz|Hz|dBsm|dBm|dBi|dB|mm|cm|km|m|ms|µs|us|ns|s|deg|°|%|"
    r"samples?|points?|bits?|rays?|bounces?|frames?|CPI|spp)(?![\w])")
_PARAM_KV = re.compile(r"[A-Za-z_][\w.\-]*\s*=\s*[-+]?[\w.\-]+")
#: **버전** — 'Sionna 2.0.1' · 'Python 3.12' · 'Sionna-RT v0.19' · 'v1.2'
#  ⚠ 도구 이름은 대문자로 시작해야 하고, 뒤에 단위가 붙으면 버전이 아니다
#    ('measured 0.210 dB/GHz' 를 버전으로 세면 검사가 무력해진다).
_UNIT_AFTER = r"(?!\s*(?:dB|dBsm|dBm|dBi|GHz|MHz|kHz|Hz|mm|cm|km|m|ms|us|ns|s|deg|°|%)\b)"
_VERSION = re.compile(
    r"(?:[A-Z][A-Za-z0-9_+\-]*(?:[ \-][A-Z][A-Za-z0-9_+\-]*)?\s+v?\d+\.\d+(?:\.\d+)?"
    + _UNIT_AFTER + r")|(?<![\w])v\d+\.\d+(?:\.\d+)?" + _UNIT_AFTER)

MIN_METHOD_PARAMS = 3
MIN_METHOD_WORDS = 30


def methods(text: str, tools: Sequence[str] = (), report: str | None = None,
            sec: str | None = None) -> Block:
    """§4.4 **방법 문단** — 논문에 그대로 옮길 수 있는 재현 가능한 한 문단.

    그 문단만 읽고 재현이 되어야 한다. 그래서 이 함수는 두 가지를 **센다**.

    | 검사 | 하한 | 왜 |
    |---|---|---|
    | 파라미터(숫자+단위 · `이름=값`) | 3개 | 값 없는 방법은 재현할 수 없다 |
    | 버전(`Sionna 2.0.1` · `v0.19`) | 1개 | 엔진이 바뀌면 숫자가 바뀐다 |

    `tools=["Sionna 2.0.1", "Mitsuba 3.6.4"]` 로 버전을 따로 줄 수도 있다 — 그러면 문단 끝에
    함께 적히고 검사도 그것을 센다.

    ⚠ 언어는 강제하지 않는다. 이 문단은 **논문(영문)으로 그대로 이관**되는 유일한 산문이다.
    """
    t = " ".join(str(text).split())
    if not t:
        raise PaperError("§4.4: 방법 문단이 비었다.")
    n_words = len(t.split())
    if n_words < MIN_METHOD_WORDS:
        raise PaperError(
            f"§4.4: 방법 문단이 {n_words}낱말이다 — {MIN_METHOD_WORDS}낱말 이상 적어라.\n"
            "  → 그 문단만 읽고 재현되어야 한다: 무엇을 · 어떤 엔진으로 · 어떤 값으로 · 무엇과 대조해.")

    T = [str(x).strip() for x in (tools or []) if str(x).strip()]
    hay = t + " " + " ".join(T)
    params = sorted(set(m.group(0).strip() for m in _PARAM_UNIT.finditer(hay))
                    | set(m.group(0).strip() for m in _PARAM_KV.finditer(hay)))
    versions = []
    for m in _VERSION.finditer(hay):
        versions.append(m.group(0).strip())
    versions = sorted(set(versions))

    if len(params) < MIN_METHOD_PARAMS:
        raise PaperError(
            f"§4.4: 방법 문단에 **파라미터가 {len(params)}개**다 (하한 {MIN_METHOD_PARAMS}). "
            f"찾은 것: {params}\n"
            "  → 값을 그대로 적어라 — 'kr 1~100 을 21점, 입사 48방향, div=16' 처럼 "
            "숫자와 단위가 붙어야 재현된다.")
    if not versions:
        raise PaperError(
            "§4.4: 방법 문단에 **버전이 없다**.\n"
            "  → 엔진·라이브러리 버전을 적어라: 'Sionna 2.0.1', 'Sionna-RT v0.19', 'Python 3.12'.\n"
            "     `tools=['Sionna 2.0.1', 'PyTorch 2.6']` 로 넘겨도 된다. "
            "버전이 바뀌면 숫자가 바뀌므로 이것이 재현의 최소 조건이다.")
    _no_hedge("§4.4 방법 문단", t)

    payload = {"kind": "methods", "report": report, "text": t, "tools": T,
               "params": params, "versions": versions, "n_words": n_words}
    head = f"### {sec} 방법 문단 (논문 이관용)" if sec else "### 방법 문단 (논문 이관용)"
    L = [f"<!--{PK_MARK}:methods {_payload(payload)}-->", head, "", t]
    if T:
        L += ["", "버전 — " + " · ".join(f"`{x}`" for x in T)]
    return Block("\n".join(L))


# --------------------------------------------------------------------------- #
#  5) 논문 형식 인용 (PAPER_SPEC §4.5)
# --------------------------------------------------------------------------- #
#: 게재상태. **필수**다 — 프리프린트를 게재본과 섞어 적는 실수가 이 프로젝트에서 실제로 났다.
_STATUS = {
    "published":   "게재",
    "in press":    "게재 확정",
    "accepted":    "게재 확정",
    "preprint":    "프리프린트",
    "tech report": "기술보고서",
    "standard":    "표준문서",
    "thesis":      "학위논문",
    "software":    "소프트웨어",
}
_STATUS_ALIAS = {"게재": "published", "게재됨": "published", "peer-reviewed": "published",
                 "게재확정": "in press", "in-press": "in press",
                 "프리프린트": "preprint", "arxiv": "preprint", "arXiv": "preprint",
                 "technical report": "tech report", "techreport": "tech report",
                 "기술보고서": "tech report", "표준": "standard", "학위논문": "thesis"}
_ARXIV = re.compile(r"^\d{4}\.\d{4,5}(v\d+)?$")


def cite(authors: str, title: str, venue: str, volume=None, pages=None,
         year=None, status: str | None = None, arxiv: str | None = None,
         doi: str | None = None, note: str | None = None) -> str:
    """§4.5 논문 형식 인용 — `저자, "제목", 학회지 권:쪽, 연도 [게재상태]`.

    ⭐ `status` 는 **필수**다. 프리프린트를 게재본처럼 적은 실수가 이 프로젝트의 헤드라인을
       한 번 무너뜨렸다(⟨outputs/prior_settled_ziganshin.json⟩: 같은 저자의 회의판과 저널판이
       서로 다른 문서다). 상태가 없으면 이 함수는 인용을 만들지 않는다.

    · `status="preprint"` 면 `arxiv=` 가 **필수**다(`2604.05991` 형식).
    · 반환은 문자열이고, 끝에 기계 판독용 표지가 숨어 있어 `extract_paper_kit()` 이 모은다.
    """
    a, t, v = str(authors or "").strip(), str(title or "").strip(), str(venue or "").strip()
    for name, val in (("authors", a), ("title", t), ("venue", v)):
        if not val:
            raise PaperError(f"§4.5: 인용에 `{name}` 이 없다.")
    if status is None or not str(status).strip():
        raise PaperError(
            f"§4.5: **게재상태가 없다** — \"{t[:50]}\"\n"
            f"  → status= 를 반드시 적어라: {', '.join(sorted(_STATUS))}.\n"
            "  ⭐ 프리프린트와 게재본을 섞어 적은 실수가 이 프로젝트에서 실제로 났다. "
            "게재상태는 인용의 장식이 아니라 주장의 세기다.")
    s = str(status).strip().lower()
    s = _STATUS_ALIAS.get(s, _STATUS_ALIAS.get(str(status).strip(), s))
    if s not in _STATUS:
        raise PaperError(
            f"§4.5: 모르는 게재상태 {status!r} — {', '.join(sorted(_STATUS))} 중에서 골라라.")
    if s == "preprint":
        if not arxiv:
            raise PaperError(
                f"§4.5: 프리프린트는 **arXiv ID 가 필수**다 — \"{t[:50]}\"\n"
                "  → arxiv='2604.05991'. ID 가 없으면 어느 판인지 특정할 수 없고, "
                "판이 다르면 숫자가 다르다.")
        if not _ARXIV.match(str(arxiv).replace("arXiv:", "").strip()):
            raise PaperError(
                f"§4.5: arXiv ID 형식이 틀렸다 — {arxiv!r} (기대: `2604.05991` 또는 `2604.05991v2`)")
    aid = str(arxiv).replace("arXiv:", "").strip() if arxiv else None

    core = f'{a}, "{t}", {v}'
    if volume:
        core += f" {volume}"
        if pages:
            core += f":{pages}"
    elif pages:
        core += f", pp. {pages}"
    if year:
        core += f", {year}"
    core += f" [{_STATUS[s]}"
    if aid:
        core += f", arXiv:{aid}"
    core += "]"
    if doi:
        core += f" doi:{doi}"
    if note:
        core += f" ({note})"

    payload = {"kind": "cite", "authors": a, "title": t, "venue": v,
               "volume": volume, "pages": pages, "year": year, "status": s,
               "status_ko": _STATUS[s], "arxiv": aid, "doi": doi, "note": note,
               "text": core}
    return core + f"<!--{PK_MARK}:cite {_payload(payload)}-->"


#: 원문에서 확인된 핵심 인용 — 손으로 다시 치지 말고 `cite_ref("das")` 로 부른다.
#: 각 항목의 `verified` 는 그 서지가 **어느 정착 JSON 에서 확인됐는지**를 가리킨다.
REFERENCES: dict[str, dict] = {
    "das": dict(
        authors="Das et al.",
        title="Multiband Monostatic and Bistatic RCS Characterization of AAVs for ISAC Channel Modeling",
        venue="IEEE Wireless Communications Letters", volume="15", pages="3731-3735",
        year=2026, status="published", doi="10.1109/LWC.2026.3705634",
        note="Phantom 3 · Table III 기울기 앵커",
        verified="outputs/prior_settled_anchor.json:settlement.H2_Das"),
    "rzewuski": dict(
        authors="Rzewuski, Kulpa, Pachwicewicz, Malanowski, Salski",
        title="Drone Detectability Feasibility Study using Passive Radars Operating in WIFI and DVB-T Band",
        venue="NATO STO-MP-MSG-SET-183, paper 13", year=2021, status="published",
        note="FDTD 로 Parrot AR.Drone 모노·바이스태틱 RCS → 패시브 커버리지 · 50 m OTA 검출",
        verified="outputs/prior_settled_h8.json:counter_paper"),
    "ziganshin_journal": dict(
        authors="Ziganshin et al.",
        title="Curved-body scattering validated inside Sionna RT",
        venue="submitted to IEEE Open Journal of Antennas and Propagation",
        year=2026, status="preprint", arxiv="2604.05991",
        note="⚠ 회의판과 저널판은 서로 다른 문서다 — 반드시 판을 밝혀 인용한다",
        verified="outputs/prior_settled_ziganshin.json:ziganshin_version_registry"),
    "sionna_rt_techreport": dict(
        authors="Hoydis et al.",
        title="Sionna RT Technical Report",
        venue="NVIDIA technical report (document version 1.2)", year=2025,
        status="preprint", arxiv="2504.21719",
        note="SBR 48회 등장 · 표면전류 적분과 RCS 출력은 없음",
        verified="outputs/prior_settled_sionna.json:pdfs_opened"),
    "sionna_rt_founding": dict(
        authors="Hoydis et al.", title="Sionna RT: Differentiable Ray Tracing for Radio Propagation Modeling",
        venue="arXiv preprint", year=2023, status="preprint", arxiv="2303.11103",
        verified="outputs/prior_settled_sionna.json:pdfs_opened"),
}


def cite_ref(key: str, **override) -> str:
    """확인된 서지에서 인용을 만든다. `cite_ref("das")` · `cite_ref("das", note="Table III")`."""
    if key not in REFERENCES:
        raise PaperError(f"모르는 인용 열쇠 {key!r} — {', '.join(sorted(REFERENCES))}")
    d = {k: v for k, v in REFERENCES[key].items() if k != "verified"}
    d.update(override)
    return cite(**d)


# --------------------------------------------------------------------------- #
#  6) 조립 — 셀 예산을 넘기지 않고 붙이는 법
# --------------------------------------------------------------------------- #
def attach(block: Block, *extra: str, sep: str = "\n\n") -> Block:
    """블록 **안으로** 다른 블록을 넣는다 — 마크다운 셀을 늘리지 않는다.

    여는 블록(`header()`)은 두 셀로 쪼개지도록 `<!--cell-->` 을 품고 있다. 이 함수는 그 **마지막
    셀 끝**에 붙이므로, `논문 대응` 블록을 편 머리(§4.1)에 두면서도 셀 예산(§5.7 25개)을 안 쓴다.
    """
    body = str(block)
    add = sep.join(str(e) for e in extra if str(e).strip())
    if not add:
        return block
    if body.rstrip().endswith("---"):            # 여는 블록의 끝 구분선 **앞**에 넣는다
        i = body.rstrip().rfind("---")
        out = body[:i].rstrip() + sep + add + "\n\n---"
    else:
        out = body + sep + add
    return Block(out, getattr(block, "kind", "markdown"))


def paper_appendix(defence_block: str | None = None, methods_block: str | None = None,
                   paper_map_block: str | None = None,
                   citations: Sequence[str] = (), sec: str | None = None) -> Block:
    """논문 참고자료 블록들을 **셀 하나**로 묶는다(§5.7 셀 예산 때문에).

    `<!--rs:paper-->` 태그가 붙어 12줄 상한에서 면제된다 — 방어선 표가 길어서다.
    셀 수·톤·출처 검사는 그대로 `check_budget()` 이 본다.
    """
    parts = [p for p in (paper_map_block, methods_block, defence_block) if p]
    C = [str(c).strip() for c in (citations or []) if str(c).strip()]
    if C:
        head = f"### {sec} 인용" if sec else "### 인용 (논문 형식 · 게재상태 포함)"
        parts.append("\n".join([head, ""] + [f"{i+1}. {c}" for i, c in enumerate(C)]))
    if not parts:
        raise PaperError("paper_appendix(): 넣을 블록이 하나도 없다.")
    return Block("<!--rs:paper-->\n" + "\n\n".join(parts), "markdown")


# --------------------------------------------------------------------------- #
#  7) 추출 — `outputs/paper_kit.json` (PAPER_SPEC §4 전부를 한 파일로)
# --------------------------------------------------------------------------- #
_PK_RE = re.compile(rf"<!--{PK_MARK}:([a-z_]+)\s+(\{{.*?\}})-->", re.S)
_IMG_RE = re.compile(r"!\[[^\]]*\]\(\s*([^)\s]+)[^)]*\)|<img[^>]+src=[\"']([^\"']+)[\"']")
#  `**그림 2.** 질문?` — 닫는 `**` 가 마침표 뒤에 오는 형태까지 받는다.
_CAP_RE = re.compile(
    r"^\s*\*{0,2}(?:그림|Figure)\s*([0-9]+(?:[.\-][0-9]+)?)\s*[.)]\s*\*{0,2}\s*(.+?)\s*$", re.M)
_HEAD_RE = re.compile(r"^#{2,4}\s+(.+?)\s*$", re.M)
#: `값 ⟨outputs/x.json : 키⟩` — 값(숫자+단위)과 출처를 함께 집는다.
_FACT_RE = re.compile(
    r"([-+]?\d[\d,.eE+\-]*\s*(?:[%°]|[A-Za-zµΩ·/]{0,10})?)\s*"
    r"⟨\s*([^:⟩]+?\.(?:json|npz))\s*:\s*([^⟩]+?)\s*⟩")
_DID_RE = re.compile(r"###\s*한 일\s*\n>\s*\*\*(.+?)\*\*", re.S)
_RESULTS_RE = re.compile(r"###\s*결과\s*\n(.*?)(?=\n#{2,4}\s|\Z)", re.S)
_REPRO_RE = re.compile(r"###\s*재현\s*\n+```bash\n(.*?)```", re.S)
_NEXT_ROW_RE = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*$", re.M)
_NEXT_HEAD = ("다음에 할 일", "그러면 결정되는 것", "어디서")

DEFAULT_NOTEBOOKS = ("report01_prior.ipynb", "report02_target.ipynb",
                     "report03_illuminators.ipynb", "report04_detector.ipynb",
                     "report05_results.ipynb", "report06_measurement.ipynb")


def _cells(nb_path: str) -> list[dict]:
    p = nb_path if os.path.isabs(nb_path) else os.path.join(ROOT, nb_path)
    if not os.path.exists(p):
        raise PaperError(f"노트북이 없다: {nb_path} (기대 경로: {p})")
    with open(p, encoding="utf-8") as f:
        return list(json.load(f).get("cells", []))


def _text(c: dict) -> str:
    s = c.get("source", "")
    return s if isinstance(s, str) else "".join(s)


def _stem(nb: str) -> str:
    return os.path.splitext(os.path.basename(nb))[0]


def _pdf_caption(pdf_path: str) -> str | None:
    """`save_figure(caption=…)` 이 PDF 에 심어 둔 **논문 캡션**을 꺼낸다. 없으면 None."""
    if not os.path.exists(pdf_path):
        return None
    try:
        import fitz
        with fitz.open(pdf_path) as doc:
            kw = (doc.metadata or {}).get("keywords") or ""
        if kw.strip().startswith("{"):
            return json.loads(kw).get("caption")
    except Exception:                                    # noqa: BLE001  (그림은 있고 메타만 없을 수 있다)
        return None
    return None


def _sections_for(nb: str) -> list[str]:
    return list(REPORT_SECTIONS.get(_stem(nb), ()))


def _scan_notebook(nb: str) -> dict:
    """노트북 한 편에서 논문 부품을 전부 긁어낸다."""
    stem = _stem(nb)
    cells = _cells(nb)
    out: dict = {"notebook": nb, "report": stem,
                 "default_sections": _sections_for(nb),
                 "paper_map": [], "defence": [], "methods": [], "citations": [],
                 "figures": [], "facts": [], "headings": [], "next_steps": [],
                 "did": None, "results": [], "repro": None}
    heading = None
    seen_fact: set[tuple] = set()
    fig_marks: dict[str, dict] = {}          # `figure_md()` 가 남긴 표지(경로 → payload)

    for i, c in enumerate(cells):
        if c.get("cell_type") != "markdown":
            continue
        t = _text(c)
        tags = (c.get("metadata", {}) or {}).get("tags") or []

        # ── 기계 판독 표지 ────────────────────────────────────────────────
        for kind, blob in _PK_RE.findall(t):
            try:
                payload = json.loads(blob)
            except json.JSONDecodeError as e:
                raise PaperError(f"{nb} 셀 {i}: pk 표지 JSON 이 깨졌다 — {e}") from e
            payload["cell"] = i
            payload.setdefault("report", stem)
            if kind == "paper_map":
                out["paper_map"].append(payload)
            elif kind == "defence":
                out["defence"] += [dict(r, cell=i, report=stem)
                                   for r in payload.get("rows", [])]
            elif kind == "methods":
                out["methods"].append(payload)
            elif kind == "cite":
                out["citations"].append(payload)
            elif kind == "figure":
                fig_marks[payload["path"]] = payload

        # ── 여는 블록 ────────────────────────────────────────────────────
        if "header" in tags or "### 한 일" in t:
            m = _DID_RE.search(t)
            if m:
                out["did"] = " ".join(m.group(1).split())
            m = _RESULTS_RE.search(t)
            if m:
                out["results"] = [" ".join(x.split()) for x in
                                  re.findall(r"^\s*\d+\.\s*(.+?)\s*$", m.group(1), re.M)]
            m = _REPRO_RE.search(t)
            if m:
                out["repro"] = m.group(1).strip()
        if "next_steps" in tags or "다음에 할 일" in t:
            rows = [r for r in _NEXT_ROW_RE.findall(t)
                    if not set("".join(r)) <= set("-: ")          # |---|---|---| 구분줄
                    and tuple(x.strip() for x in r) != _NEXT_HEAD]  # 표 머리
            out["next_steps"] += [{"todo": a, "decides": b, "where": c_}
                                  for a, b, c_ in rows]

        # ── 절 제목 · 그림 · 수치 ────────────────────────────────────────
        for h in _HEAD_RE.findall(t):
            heading = " ".join(h.split())
            out["headings"].append({"cell": i, "heading": heading})
        caps = {no: q for no, q in _CAP_RE.findall(t)}
        cap_list = list(caps.items())
        for k, (a, b) in enumerate(_IMG_RE.findall(t)):
            src = a or b
            p_abs = src if os.path.isabs(src) else os.path.join(ROOT, src)
            pdf = os.path.splitext(p_abs)[0] + ".pdf"
            no, q = cap_list[k] if k < len(cap_list) else (None, None)
            mark = fig_marks.get(src, {})
            out["figures"].append({
                "cell": i, "report": stem, "path": src, "exists": os.path.exists(p_abs),
                "figure_no": mark.get("figure_no") or no,
                "caption": q or mark.get("question"), "heading": heading,
                # 논문 캡션(완결 문장)은 `figure_md()` 표지 → 없으면 PDF 메타데이터에서 찾는다
                "paper_caption": mark.get("paper_caption") or _pdf_caption(pdf),
                "vector_pdf": os.path.relpath(pdf, ROOT) if os.path.exists(pdf) else None,
            })
        for m in _FACT_RE.finditer(t):
            val, src, key = m.group(1), m.group(2), m.group(3)
            sig = (src, key.strip(), val.strip())
            if sig in seen_fact:
                continue
            seen_fact.add(sig)
            # 문맥 = 그 수치가 놓인 줄(표의 행이면 그 행) — 원고에 옮길 때 뜻을 잃지 않게
            line = t[:m.start()].split("\n")[-1] + t[m.start():].split("\n")[0]
            out["facts"].append({"cell": i, "report": stem, "value": val.strip(),
                                 "source": src, "key": key.strip(),
                                 "heading": heading,
                                 "context": " ".join(line.split())[:240]})
    return out


def extract_paper_kit(notebooks: Sequence[str] = DEFAULT_NOTEBOOKS,
                      out_path: str = "outputs/paper_kit.json",
                      write: bool = True) -> dict:
    """⭐ 여섯 편에서 **논문 부품 전부**를 긁어 `outputs/paper_kit.json` 으로 쓴다.

    모으는 것: 논문 대응 블록 · 방어선 행 · 방법 문단 · 인용 · 그림(캡션·벡터본 유무) ·
    **출처 태그가 붙은 수치 전부** · 여는 블록(한 일/결과/재현) · 다음 단계.

    키는 **논문 절**이다. `sections["V. Results"]` 만 열어도 그 절의 주장·근거·수치·그림·
    방어선이 다 있어서, 노트북을 다시 열지 않고 절 하나를 초고까지 쓸 수 있다.

    `coverage` 와 `todo` 가 아직 안 채워진 자리를 그대로 알려준다.
    """
    NBS = [str(n) for n in notebooks]
    per = {n: _scan_notebook(n) for n in NBS}

    sections: dict[str, dict] = {
        s: {"reports": [], "claims": [], "defence": [], "methods": [],
            "citations": [], "figures": [], "facts": []} for s in SECTIONS}
    unmapped: dict[str, list] = {"claims": [], "defence": [], "methods": [],
                                 "citations": [], "figures": [], "facts": []}

    def bucket(sec_names: Sequence[str], key: str, item):
        if not sec_names:
            unmapped[key].append(item)
            return
        sections[sec_names[0]][key].append(item)

    for nb, d in per.items():
        mapped = []
        for pm in d["paper_map"]:
            for s in pm.get("sections", []):
                s = _canon_section(s)
                mapped.append(s)
                sections[s]["claims"].append(
                    {"claim": pm["claim"], "evidence": pm.get("evidence", []),
                     "qualifications": pm.get("qualifications", []),
                     "report": d["report"], "cell": pm.get("cell")})
        home = mapped or d["default_sections"]
        for s in home:
            if d["report"] not in sections[s]["reports"]:
                sections[s]["reports"].append(d["report"])
        for k in ("defence", "methods", "citations", "figures", "facts"):
            for it in d[k]:
                bucket(home, k, it)

    cov, todo = {}, []
    for nb, d in per.items():
        c = {"paper_map": len(d["paper_map"]), "defence_rows": len(d["defence"]),
             "methods": len(d["methods"]), "citations": len(d["citations"]),
             "figures": len(d["figures"]),
             "figures_with_vector": sum(1 for f in d["figures"] if f["vector_pdf"]),
             "facts": len(d["facts"]), "next_steps": len(d["next_steps"])}
        cov[d["report"]] = c
        secs = " · ".join(d["default_sections"]) or "미배정"
        if not c["paper_map"]:
            todo.append(f"{nb}: 논문 대응 블록 없음 — `paper_map('{(d['default_sections'] or ['?'])[0]}', …)` "
                        f"(→ {secs}, PAPER_SPEC §4.1)")
        if not c["defence_rows"]:
            todo.append(f"{nb}: 방어선 표 없음 — `defence([(주장, 근거, 공격, 답), …])` (§4.2)")
        if not c["methods"]:
            todo.append(f"{nb}: 방법 문단 없음 — `methods('…')` (§4.4)")
        if not c["citations"]:
            todo.append(f"{nb}: 논문 형식 인용 없음 — `cite(…, status=…)` (§4.5)")
        if c["figures"] and c["figures_with_vector"] < c["figures"]:
            todo.append(f"{nb}: 그림 {c['figures']}개 중 벡터본 {c['figures_with_vector']}개 — "
                        f"`save_figure()` 로 PDF 를 함께 만들 것 (§4.3)")

    doc = {
        "meta": {
            "generated": _dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "generator": "src/paper_kit.py:extract_paper_kit",
            "contract": ["docs/PAPER_SPEC.md §4", "docs/REBUILD_2026-07-30.md §5"],
            "paper_title": PAPER_TITLE,
            "contribution": CONTRIBUTION,
            "sections_order": list(SECTIONS),
            "notebooks": NBS,
            "how_to_use": ("절 하나를 쓰려면 sections[절] 만 연다 — claims(주장·근거) → "
                           "facts(수치와 그 출처 JSON 키) → figures(캡션·벡터본) → "
                           "defence(예상 반론과 답) → citations 순으로 초고가 나온다. "
                           "숫자는 반드시 facts[].source/key 로 다시 확인하고 옮긴다."),
            "totals": {k: sum(len(v[k]) for v in sections.values())
                       for k in ("claims", "defence", "methods", "citations",
                                 "figures", "facts")},
        },
        "sections": sections,
        "unmapped": unmapped,
        "reports": per,
        "coverage": cov,
        "todo": todo,
        "references": REFERENCES,
    }
    if write:
        p = out_path if os.path.isabs(out_path) else os.path.join(ROOT, out_path)
        os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=1)
        doc["meta"]["path"] = os.path.relpath(p, ROOT)
    return doc


def coverage_report(doc: dict | None = None) -> str:
    """사람이 읽는 표 — 어느 편에 무엇이 아직 없는가."""
    d = doc or extract_paper_kit(write=False)
    L = ["| 리포트 | 논문절 | 대응 | 방어선 | 방법문단 | 인용 | 그림(벡터) | 수치 |",
         "|---|---|---|---|---|---|---|---|"]
    for nb, c in d["coverage"].items():
        secs = " · ".join(REPORT_SECTIONS.get(nb, ())) or "—"
        L.append(f"| `{nb}` | {secs} | {c['paper_map']} | {c['defence_rows']} | "
                 f"{c['methods']} | {c['citations']} | "
                 f"{c['figures']}({c['figures_with_vector']}) | {c['facts']} |")
    t = d["meta"]["totals"]
    L.append(f"| **합계** |  | **{t['claims']}** | **{t['defence']}** | **{t['methods']}** "
             f"| **{t['citations']}** | **{t['figures']}** | **{t['facts']}** |")
    return "\n".join(L)


# --------------------------------------------------------------------------- #
#  8) 자기검사 — 막지 못하는 장치는 장치가 아니다
# --------------------------------------------------------------------------- #
def _selftest() -> int:                                          # noqa: C901
    import tempfile
    bad = 0
    SP = os.environ.get("PK_SELFTEST_OUT", tempfile.mkdtemp(prefix="paper_kit_"))
    os.makedirs(SP, exist_ok=True)

    OKMAP = dict(section="V. Results",
                 claim="세 조명원을 같은 표적·같은 검출기·교정된 Pfa 위에서 비교했다.",
                 evidence=["그림 3", "outputs/report05_derived.json:r90.span_comparable_min_km"])
    OKROW = ("교정 문턱 위에서 세 파형의 검출거리를 비교했다.",
             "그림 3 · outputs/verify_cfar.json:calibration",
             "σ 절대값이 미검증인데 거리 비교가 성립하는가",
             "σ 오차는 세 밴드 공통이라 순위에서 상쇄되고 절대거리만 오차/4 dB 움직인다 "
             "⟨outputs/sigma_anchor.json : modes⟩")
    OKMETHOD = ("We computed the target scattering with a GPU shooting-and-bouncing-rays solver "
                "in Sionna 2.0.1 on Python 3.12, integrating physical optics over the first-hit "
                "lit surface of a per-part material mesh, sweeping kr from 1 to 100 at 21 points "
                "and 48 incidence directions with div=16, and anchored the band slope onto a "
                "measured 0.210 dB/GHz.")

    print("── 자기검사: 규격 위반이 실제로 막히는가 ──")
    cases = [
        # ── §4.1 논문 대응 ────────────────────────────────────────────────
        ("모르는 논문 절", lambda: paper_map("VII. Discussion", "했다.", ["그림 1"])),
        ("근거가 빔", lambda: paper_map("V", "했다.", [])),
        ("근거가 아무것도 안 가리킴", lambda: paper_map("V", "했다.", ["대충 잘 됐다"])),
        ("⭐ 아직 없는 산출물을 근거로 씀",
         lambda: paper_map("V", "했다.", ["outputs/아직없는실험.json:key"])),
        ("주장이 질문", lambda: paper_map("V", "무엇을 믿어도 되는가?", ["그림 1"])),
        ("⭐ '최초' 류 문구", lambda: paper_map("V", "세계 최초로 비교했다.", ["그림 1"])),
        ("⭐ 'first to' 문구", lambda: paper_map("V", "We are the first to compute it.", ["그림 1"])),
        ("⭐ H8 을 단서 없이 사용",
         lambda: paper_map("II", "드론 메쉬 산란을 계산해 게재된 전례가 0편이다.", ["그림 1"])),
        ("주장에 완충어", lambda: paper_map("V", "대체로 비교했다.", ["그림 1"])),
        # ── §4.2 방어선 ──────────────────────────────────────────────────
        ("⭐ 공격이 빔", lambda: defence([(OKROW[0], OKROW[1], "", OKROW[3])])),
        ("⭐ 답이 빔", lambda: defence([(OKROW[0], OKROW[1], OKROW[2], "")])),
        ("근거가 빔", lambda: defence([(OKROW[0], "", OKROW[2], OKROW[3])])),
        ("근거가 아무것도 안 가리킴",
         lambda: defence([(OKROW[0], "그냥 그렇다", OKROW[2], OKROW[3])])),
        ("행이 3칸", lambda: defence([(OKROW[0], OKROW[1], OKROW[2])])),
        ("표가 빔", lambda: defence([])),
        ("⭐ 답이 부정 종결",
         lambda: defence([(OKROW[0], OKROW[1], OKROW[2], "절대 σ 는 검증되지 않았다")])),
        ("주장이 '최초' 류",
         lambda: defence([("최초로 비교했다.", OKROW[1], OKROW[2], OKROW[3])])),
        # ── §4.4 방법 문단 ───────────────────────────────────────────────
        ("방법 문단이 짧음", lambda: methods("SBR 로 계산했다.")),
        ("⭐ 파라미터 없음",
         lambda: methods("We computed the target scattering with a ray solver and then "
                         "anchored the level onto a published measurement of a small "
                         "quadrotor, repeating the whole procedure for every band and "
                         "every airframe in the study using Sionna 2.0.1.")),
        ("⭐ 버전 없음",
         lambda: methods("We swept kr from 1 to 100 at 21 points over 48 incidence "
                         "directions with div=16 and integrated physical optics over the "
                         "lit surface, then anchored the band slope onto a measured "
                         "0.210 dB/GHz taken from a published letter, at 3.5 GHz.")),
        # ── §4.5 인용 ────────────────────────────────────────────────────
        ("⭐ 게재상태 누락", lambda: cite("Das et al.", "T", "IEEE WCL", "15", "3731", 2026)),
        ("모르는 게재상태", lambda: cite("A", "T", "V", status="maybe")),
        ("⭐ 프리프린트인데 arXiv ID 없음", lambda: cite("Z et al.", "T", "V", status="preprint")),
        ("arXiv ID 형식 오류",
         lambda: cite("Z", "T", "V", status="preprint", arxiv="26-05991")),
        ("저자 없음", lambda: cite("", "T", "V", status="published")),
        # ── §4.3 그림 ────────────────────────────────────────────────────
        ("본문 글자 8 pt 미만 프로파일", lambda: paper_rc(base_pt=6)),
        ("모르는 폭 이름", lambda: paper_rc(width="triple")),
        ("PNG 300 dpi 미만", lambda: save_figure(_probe_fig()[0], os.path.join(SP, "x"), dpi=150)),
        ("벡터 없이 저장", lambda: save_figure(_probe_fig()[0], os.path.join(SP, "x"),
                                              formats=("png",))),
        ("없는 그림 검사", lambda: check_figure("outputs/figures/없는그림.pdf")),
        ("⭐ 1단(1.7 in)에 넣으면 8 pt 가 깨짐",
         lambda: save_figure(_probe_fig()[0], os.path.join(SP, "x"), placed_width_in=1.7)),
        # ── §4.3 그림 캡션 ────────────────────────────────────────────────
        ("그림 파일이 없음", lambda: figure_md("outputs/figures/없다.png", 1, "무엇인가?")),
        ("노트북 캡션이 질문이 아님",
         lambda: figure_md("outputs/figures/report05_f2_budget.png", 1, "SNR 분해.")),
        ("⭐ 논문 캡션이 질문",
         lambda: figure_md("outputs/figures/report05_f2_budget.png", 1, "무엇인가?",
                           paper_caption="Where does the SNR come from?")),
        ("논문 캡션이 너무 짧음",
         lambda: figure_md("outputs/figures/report05_f2_budget.png", 1, "무엇인가?",
                           paper_caption="SNR budget.")),
    ]
    for name, fn in cases:
        try:
            fn()
        except ContractError as e:
            print(f"  ✅ 막힘  {name} — {str(e).splitlines()[0][:66]}")
        else:
            bad += 1
            print(f"  ❌ 안 막힘 {name}")

    print("── 자기검사: 정상 입력은 통과하는가 ──")
    oks = [
        ("paper_map", lambda: paper_map(**OKMAP)),
        ("paper_map 여러 절", lambda: paper_map(["I", "II. Related Work"],
                                                "회피전략을 여섯 갈래로 정리했다.",
                                                ["그림 1", "outputs/prior_census.json:funnel"])),
        ("⭐ H8 + 단서 두 개",
         lambda: paper_map("II", "네 관문(게재·표면메쉬·Sionna 급 엔진·진폭검증)을 함께 통과한 "
                                 "게재 전례가 0편이다.",
                           ["outputs/prior_settled_h8.json:prong_scorecard"],
                           qualifications=[
                               "Rzewuski(NATO STO 2021)가 FDTD 로 같은 산출물을 냈다 — 차이는 엔진이다",
                               "'게재' 가 주장 전부를 진다 — 프리프린트를 넣으면 간극은 이음매로 좁아진다"])),
        ("defence", lambda: defence([OKROW])),
        ("methods", lambda: methods(OKMETHOD, tools=["Sionna 2.0.1", "PyTorch 2.6"])),
        ("cite 게재본", lambda: cite("Das et al.", "Multiband RCS", "IEEE WCL", "15",
                                     "3731-3735", 2026, status="published")),
        ("cite 프리프린트", lambda: cite("Ziganshin et al.", "Curved-body scattering",
                                         "submitted to IEEE OJAP", year=2026,
                                         status="preprint", arxiv="2604.05991")),
        ("cite_ref('das')", lambda: cite_ref("das")),
        ("cite_ref('rzewuski')", lambda: cite_ref("rzewuski")),
        ("paper_rc 기본", lambda: paper_rc()["font.size"]),
        ("series_style 이중부호화", lambda: series_style(1)),
        ("greyscale_gaps", lambda: greyscale_gaps()["min_gap"]),
    ]
    for name, fn in oks:
        try:
            r = fn()
        except Exception as e:                                   # noqa: BLE001
            bad += 1
            print(f"  ❌ 정상인데 터짐 {name}: {str(e).splitlines()[0][:70]}")
        else:
            head = str(r).splitlines()[0][:72] if isinstance(r, str) else r
            print(f"  ✅ 통과  {name} → {head}")

    # ── §4.3 그림: 실제로 저장하고, **파일만 열어** 다시 검사한다 ──────────
    print("── 자기검사: §4.3 게재 품질 그림 ──")
    try:
        fig, _ = _probe_fig()
        res = save_figure(fig, os.path.join(SP, "probe_good"), caption="A good figure.",
                          close=True)
        chk = res["check"]
        ok = (chk["ok"] and chk["min_font_pt"] >= MIN_FONT_PT and chk["embedded_audit"]
              and not chk["colour_only_series"])
        print(f"  {'✅ 통과 ' if ok else '❌ 실패 '} 저장→재검사: 최소 글자 "
              f"{chk['min_font_pt']} pt · 계열 {len(chk.get('series', []))} · "
              f"PNG {chk.get('png_dpi')} dpi · 색만구분 {len(chk['colour_only_series'])}")
        bad += 0 if ok else 1

        red = check_figure(res["pdf"], placed_width_in=1.7)      # 절반으로 줄여 배치
        shrunk = red["effective_min_font_pt"] < MIN_FONT_PT and not red["ok"]
        print(f"  {'✅ 통과 ' if shrunk else '❌ 실패 '} 축소 판정: 폭 1.7 in 배치에서 "
              f"{red['min_font_pt']} → {red['effective_min_font_pt']} pt "
              f"(축소 {red['reduction']})")
        bad += 0 if shrunk else 1
    except Exception as e:                                       # noqa: BLE001
        bad += 1
        print(f"  ❌ 그림 저장/검사에서 터짐: {e}")

    try:                                                          # 색만으로 구분한 그림
        fig, ax = _probe_fig(dual=False)
        try:
            save_figure(fig, os.path.join(SP, "probe_colour_only"), close=True)
        except PaperError as e:
            caught = "색만으로 구분된 계열" in str(e)
            print(f"  {'✅ 막힘 ' if caught else '❌ 엉뚱 '} 색만으로 구분된 계열 — "
                  f"{str(e).splitlines()[1].strip()[:70]}")
            bad += 0 if caught else 1
        else:
            bad += 1
            print("  ❌ 안 막힘 색만으로 구분된 계열")
    except Exception as e:                                       # noqa: BLE001
        bad += 1
        print(f"  ❌ 이중부호화 검사에서 터짐: {e}")

    try:                                                          # 그림 속 한글
        import matplotlib.pyplot as plt
        with paper_style() as st:
            fig, ax = st.figure()
            ax.plot([1, 2], [1, 2], label="WiFi", **st.series(0))
            ax.set_xlabel("거리 [km]")
        try:
            audit_figure(fig)
        except ContractError:
            print("  ✅ 막힘  그림 속 한글(하우스 규약: 그림 글자는 영어)")
        else:
            bad += 1
            print("  ❌ 안 막힘 그림 속 한글")
        plt.close(fig)
    except Exception as e:                                       # noqa: BLE001
        bad += 1
        print(f"  ❌ 한글 검사에서 터짐: {e}")

    # ── 팔레트가 흑백에서 갈리는가 ────────────────────────────────────────
    g3, g6 = greyscale_gaps(PALETTE[:3]), greyscale_gaps(PALETTE[:6])
    ok3 = (g3["min_gap"] or 0) >= MIN_GREY_GAP
    print(f"  {'✅ 통과 ' if ok3 else '❌ 실패 '} 팔레트: 앞 3색 명도차 {g3['min_gap']} "
          f"≥ {MIN_GREY_GAP} (WiFi·LTE·5G 기본형) · 6색이면 {g6['min_gap']} "
          f"— 그래서 마커·선종을 함께 바꾼다")
    bad += 0 if ok3 else 1

    # ── §4 부품이 노트북을 왕복하는가(round-trip) ─────────────────────────
    print("── 자기검사: 추출 왕복 ──")
    try:
        from report_style import build_notebook, header, next_steps
        probe = os.path.join(SP, "pk_probe.ipynb")
        hdr = header(num=9, title="probe", did="세 조명원을 통제 비교했다.",
                     results=["편차 0.201 dB 다.", "두 번째 줄", "세 번째 줄"],
                     method=[("a", "b"), ("c", "d")],
                     repro=dict(cmd="x", out="outputs/sbr_kr_sweep.json"))
        hdr = attach(hdr, paper_map(**OKMAP, report="pk_probe"))
        # 그림 한 장을 규격대로 저장해 두고(논문 캡션은 PDF 메타데이터로 들어간다) 끼운다
        fig, _ = _probe_fig()
        save_figure(fig, os.path.join(SP, "rt_fig"), close=True,
                    caption="Output SNR against baseline range for the three illuminators.")
        build_notebook(probe, [
            hdr,
            figure_md(os.path.join(SP, "rt_fig.png"), 1,
                      "세 조명원의 출력 SNR 은 거리에 따라 어떻게 갈리는가?",
                      report="pk_probe"),
            md("![f](outputs/figures/report05_f2_budget.png)", "",
               "**그림 2.** 출력 SNR 은 어떤 항으로 만들어지는가?"),
            md("검출거리는 3.69 km ⟨outputs/report05_derived.json : "
               "r90.span_comparable_min_km⟩ 다."),
            paper_appendix(defence_block=defence([OKROW], report="pk_probe"),
                           methods_block=methods(OKMETHOD, tools=["Sionna 2.0.1"],
                                                 report="pk_probe"),
                           citations=[cite_ref("das"), cite_ref("ziganshin_journal")]),
            next_steps([("2편파를 잰다", "편파 항이 수치로 확정된다", "06편 §2")]),
        ], quiet=True)
        doc = extract_paper_kit([probe], out_path=os.path.join(SP, "pk_probe.json"))
        r = doc["reports"][probe]
        got = (len(r["paper_map"]), len(r["defence"]), len(r["methods"]),
               len(r["citations"]), len(r["figures"]), len(r["facts"]))
        want = (1, 1, 1, 2, 2, 1)
        okrt = got == want and r["did"] and r["figures"][0]["caption"]
        print(f"  {'✅ 통과 ' if okrt else '❌ 실패 '} 왕복: 대응·방어선·방법·인용·그림·수치 = "
              f"{got} (기대 {want})")
        bad += 0 if okrt else 1
        # ⭐ 논문 캡션(완결 문장)이 PDF 메타데이터를 거쳐 돌아오는가
        pc = r["figures"][0].get("paper_caption")
        okpc = bool(pc) and pc.startswith("Output SNR")
        print(f"  {'✅ 통과 ' if okpc else '❌ 실패 '} 논문 캡션 왕복(PDF 메타데이터): {pc!r}")
        bad += 0 if okpc else 1

        rep = __import__("report_style").check_budget(probe)
        print(f"  {'✅ 통과 ' if rep['ok'] else '❌ 실패 '} 규약 동시 통과: "
              f"md {rep['md_cells']}셀 · 부정문 {rep['n_negatives']} · 완충어 {rep['n_hedges']}"
              + ("" if rep["ok"] else f" — {rep['violations'][:2]}"))
        bad += 0 if rep["ok"] else 1
    except Exception as e:                                       # noqa: BLE001
        bad += 1
        print(f"  ❌ 왕복 검사에서 터짐: {type(e).__name__}: {e}")

    print(f"── 자기검사 {'성공' if bad == 0 else f'실패 {bad}건'} ── (산출물: {SP})\n")
    return bad


def _probe_fig(dual: bool = True):
    """자기검사용 그림 — dual=False 면 **색만으로** 계열을 구분한다(막혀야 한다)."""
    with paper_style(width="single") as st:
        fig, ax = st.figure()
        x = [1, 2, 3, 4]
        for i, name in enumerate(("WiFi", "LTE", "5G NR")):
            y = [v * (i + 1) for v in x]
            if dual:
                ax.plot(x, y, label=name, **st.series(i))
            else:                        # 색만 — 마커·선종을 같게 두면 흑백에서 사라진다
                ax.plot(x, y, label=name, color=st.color(i), marker="o", linestyle="-")
        ax.set_xlabel("Baseline range [km]")
        ax.set_ylabel("Output SNR [dB]")
        ax.legend()
    return fig, ax


if __name__ == "__main__":
    argv = sys.argv[1:]
    if argv and argv[0] == "extract":
        doc = extract_paper_kit(argv[1:] or DEFAULT_NOTEBOOKS)
        print(coverage_report(doc))
        print(f"\n→ {doc['meta'].get('path')}  "
              f"(수치 {doc['meta']['totals']['facts']}건 · 그림 "
              f"{doc['meta']['totals']['figures']}개)")
        if doc["todo"]:
            print("\n── 아직 없는 것 ──")
            for t in doc["todo"]:
                print(f"  · {t}")
        raise SystemExit(0)
    raise SystemExit(1 if _selftest() else 0)
