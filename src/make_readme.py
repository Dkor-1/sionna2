# -*- coding: utf-8 -*-
"""
make_readme.py — README.md 를 편성에서 직접 짓는다
==========================================================================================
목차를 손으로 유지하면 편성이 바뀔 때마다 어긋난다. 그래서 권 수·권 제목·절 수·절 제목·
그림 수를 전부 **`outputs/volumes_index.json` 에서 읽어서** 만든다. 권이 늘거나 절이
옮겨가면 이 스크립트를 다시 돌리는 것으로 끝난다 — 이 파일 안에 편성 숫자는 없다.

읽는 층이 둘이다.
    `reports/NN_slug.ipynb`        권 — 사람이 읽는 문서. README 의 링크는 전부 여기로 간다
    `reports/_parts/NN_slug.ipynb` 조각 — 빌더 산출물. README 는 가리키지 않는다

산출
    README.md

⭐ 출처는 각주다. 리포트와 같은 규약이고, GitHub 이 `[^n]` 을 그대로 각주로 렌더한다.
   숫자는 `report_style.num()` 이 JSON 을 열어 대조한 값이다 — 손으로 친 숫자가 없다.

실행 (색인이 먼저다)
    PYTHONPATH=src ~/.venvs/py312/bin/python src/build_volumes.py
    PYTHONPATH=src ~/.venvs/py312/bin/python src/make_readme.py
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

import report_style as RS                                              # noqa: E402
from report_style import num                                           # noqa: E402

#: 읽는 경로 ② «왜 믿을 수 있나» 의 정본은 권을 조립하는 스크립트다 — 1 권 절 1 의 지도와
#: 같은 목록을 써야 README 와 리포트가 갈라지지 않는다.
from build_volumes import VERIFY_PARTS                                 # noqa: E402

OUT = os.path.join(ROOT, "README.md")
IDX = "outputs/volumes_index.json"

#: 다시 만들기 블록의 한 줄 설명. 명령 목록 자체는 색인(`_meta.order`)이 정한다.
STEP_LEAD = {
    "src/build_partNN_*.py": "조각 빌더 → reports/_parts/NN_slug.ipynb "
                             "(계산 없음 · GPU 0 장 · 수 초)",
    "src/make_report08_microdoppler.py": "그림이 무거워 여러 편으로 나뉘는 권을 따로 짓는다",
    "src/make_report07b_bistatic.py": "그 권의 마지막 편(바이스태틱)은 빌더가 따로다",
    "src/make_report11_2_two_channel.py": "권에 딸린 별편 — 자기 파일만 낸다",
    "src/build_report18_switch_grid.py": "권에 딸린 별편 — 자기 파일만 낸다",
    "src/build_volumes.py": "조각 → 권 + 후처리 + 색인 + reports/README.md",
    "benchmark/check_report_links.py": "끊긴 링크·그림·출처를 전수로 센다",
}

#: 색인의 명령 목록이 글로브일 때 실제로 치는 명령.
STEP_CMD = {"src/build_partNN_*.py": 'for f in src/build_part*.py; do PYTHONPATH=src $PY "$f"; done'}


# --------------------------------------------------------------------------- #
#  색인 읽기 — 편성 숫자는 전부 여기서 온다
# --------------------------------------------------------------------------- #
def _index() -> dict:
    with open(os.path.join(ROOT, IDX), encoding="utf-8") as f:
        return json.load(f)


def _anchor_of(part_file: str) -> str:
    """`reports/_parts/18_kernel-what.ipynb` → `kernel-what`."""
    base = os.path.basename(part_file)
    return re.sub(r"^\d+_", "", base[:-6] if base.endswith(".ipynb") else base)


def _by_anchor(idx: dict) -> dict[str, dict]:
    """앵커 → 그 조각이 앉은 권과 절. 앵커는 조각 파일 이름에서 읽는다."""
    out: dict[str, dict] = {}
    for pno, p in idx["parts"].items():
        out[_anchor_of(p["part_file"])] = dict(p, part=pno)
    return out


def _cut(t: str, width: int = 72) -> str:
    """표 칸에 넣을 한 줄 — 굵은 표시를 떼고 길이로만 자른다.

    ⚠ «—» 나 «,» 에서 자르지 않는다. 권 제목은 앞머리가 겹치는 것들이 있어
      (6 권과 별편 6-6 둘 다 «마이크로도플러 — …») 앞부분만 남기면 서로 구별이 안 된다.
    """
    t = re.sub(r"\*\*", "", str(t)).strip()
    return t if len(t) <= width else t[: width - 1].rstrip() + "…"


def _gh_slug(heading: str) -> str:
    """GitHub 이 제목에서 만드는 앵커. 글자·숫자·공백·하이픈만 남기고 공백을 하이픈으로."""
    s = re.sub(r"[^\w\s\-]", "", heading.strip().lower(), flags=re.UNICODE)
    return re.sub(r"\s", "-", s)


def _disp(no) -> str:
    """위계 번호의 산문 표기 예비 유도식 — "01"→"1", "01_2"→"1-2", "10_2"→"10-2".

    정본은 색인이 주는 `no_disp` 다(`build_volumes._disp` 와 같은 규칙). 색인에 아직
    그 키가 없을 때만 이 유도식이 대신한다 — 표시 숫자를 손으로 치지 않기 위한 예비다.
    """
    h, _, t = str(no).partition("_")
    return str(int(h)) + (f"-{t}" if t else "")


def _vd(v: dict) -> str:
    """권 항목의 표시 번호 — 색인의 `no_disp` 소비, 없으면 규칙 유도."""
    return v.get("no_disp") or _disp(v["no"])


def _is_comp(v: dict) -> bool:
    """별편 판별 — 색인의 `kind`("trunk"|"companion") 가 정본, 없으면 번호의 `_` 로."""
    return v.get("kind", "companion" if "_" in str(v["no"]) else "trunk") == "companion"


def _vol_head(v: dict) -> str:
    return f"{'별편' if _is_comp(v) else '권'} {_vd(v)} «{v['title']}»"


def _sec_link(p: dict, disp: dict[str, str], width: int = 30) -> str:
    """절 하나를 가리키는 링크 — `[리포트 2 절 1 «…»](reports/02_kernel.ipynb)`."""
    d = disp.get(str(p["volume"])) or _disp(p["volume"])
    return (f"[리포트 {d} 절 {p['section']} «{_cut(p['title'], width)}»"
            f"](reports/{p['file']})")


# --------------------------------------------------------------------------- #
#  각주
# --------------------------------------------------------------------------- #
def _footnotes(text: str) -> str:
    """본문의 `값 ⟨파일 : 키⟩` 를 `값[^n]` 으로 바꾸고 문서 끝에 각주 정의를 붙인다.

    GitHub 마크다운이 `[^n]` / `[^n]: …` 를 각주로 렌더한다 — 리포트와 같은 규약이다.
    """
    order: list[tuple[str, str]] = []
    seen: dict[tuple[str, str], int] = {}

    def mark(m: re.Match) -> str:
        key = (m.group(1).strip(), m.group(2).strip())
        n = seen.get(key)
        if n is None:
            order.append(key)
            n = seen[key] = len(order)
        return f"[^{n}]"

    text = RS._PROV_PARTS.sub(mark, text)
    text = re.sub(r"(\[\^\d+\])\(", r"\1 (", text)
    if not order:
        return text
    L = ["", "---", "", "## 출처", "",
         "위 숫자에 붙은 `[^n]` 은 그 값이 온 JSON 파일과 키다. 값은 이 문서를 만들 때 "
         "JSON 을 다시 열어 채웠다.", ""]
    for n, (p, k) in enumerate(order, 1):
        L.append(f"[^{n}]: `{p}` : `{k}` = {RS._resolve_cite(p, k)}")
    return text + "\n".join(L) + "\n"


# --------------------------------------------------------------------------- #
#  본문
# --------------------------------------------------------------------------- #
def build() -> str:
    idx = _index()
    vols = idx["volumes"]
    parts = idx["parts"]
    anchors = _by_anchor(idx)
    esc = RS._md_escape_cell

    #  본편/별편 분리 — 표시 번호(`no_disp`)와 지위(`kind`)는 색인이 정본이다.
    trunk = [v for v in vols if not _is_comp(v)]
    disp = {str(v["no"]): _vd(v) for v in vols}

    def _pd(p: dict) -> str:                     # 절 항목의 권 표시 번호
        return disp.get(str(p["volume"])) or _disp(p["volume"])

    n_vol = len(trunk)
    n_comp = sum(len(cs) for cs in idx.get("companions", {}).values())
    n_sec = sum(int(v["n_sections"]) for v in vols)
    n_fig = sum(int(v["figures"]) for v in vols)
    n_split = [v for v in vols if len(v["files"]) > 1]

    L: list[str] = []
    A = L.append

    A("<!-- 생성물 — `src/make_readme.py` 가 편성에서 읽어 쓴다. "
      "손으로 고치지 말고 그 파일을 고쳐라. -->")
    A("")
    A("# sionna2 — 통신신호를 조명원 삼는 패시브 바이스태틱 드론 탐지 시뮬레이터")
    A("")
    A("셀이 이미 켜 두는 상시 신호(WiFi · LTE · 5G NR)를 조명 삼아 드론을 탐지하는 패시브")
    A("바이스태틱 레이더를, Sionna RT 2.0.1 위에서 자유공간 기하로 끝까지 시뮬레이션한다.")
    A("표적 산란은 Sionna 의 Mitsuba/OptiX 광선엔진으로 면별 가림을 풀고 그 조명면 위에서")
    A("부품별 재질 PO 를 적분해 만든다. σ 의 **주파수 의존성**은 공개 측정(Das)에 맞추고,")
    A("**자세 패턴과 절대 레벨은 우리 PO 출력**이다.")
    A("")
    A(f"보고서는 **본편 {n_vol}권 · 별편 {n_comp}편 · 절 {n_sec}개** 다. **한 권이 물음 하나를"
      " 들고, 절 제목이 그 절의")
    A("결론 문장**이다 — 목차를 읽는 것이 결론을 읽는 것이다. 사람이 읽는 문서는")
    A("`reports/NN_slug.ipynb` 이고, " + " · ".join(
        f"{_vd(v)}권만 그림이 무거워 {len(v['files'])}편으로 나뉜다" for v in n_split)
      + ("." if n_split else "")
      + (" **별편**은 부모 권의 물음에 딸린 답(심화·지원·변주)이고 번호가 부모-K 다."
         " 그림 무게로 나뉜 **분권**은 한 권의 장일 뿐이라 별편과 지위가 다르다."
         " 별편은 부모 권의 목차에 적어 두었다." if n_comp else ""))
    A("")

    # ── 읽기 경로 ────────────────────────────────────────────────────────────
    map_vol = vols[0]
    A("## 어디부터 읽어라")
    A("")
    A(f"본편 {n_vol}권을 처음부터 읽지 않는다. **읽는 목적이 셋이면 읽는 순서도 셋**이고,")
    A(f"그 갈림길이 [리포트 {_vd(map_vol)} 절 1 «{map_vol['sections'][0]['title']}»"
      f"](reports/{map_vol['sections'][0]['file']}) 다.")
    A("")
    A("| 무엇을 하려는가 | 어디로 | 얼마나 |")
    A("|---|---|---|")
    A("| 이 저장소가 무엇을 해냈는지만 알고 싶다 | ↓ **① 빨리 훑기** | 30분 |")
    A("| 판정을 검사하려 한다(심사·적대검증) | ↓ **② 왜 믿을 수 있나** | 2시간 |")
    A("| 숫자를 재생산하려 한다 | [`docs/REPRODUCE.md`](docs/REPRODUCE.md) — "
      "명령 → 출력 → 소요 | 리포트를 안 읽는다 |")
    A("| 원고에 옮기려 한다 | [`docs/paper/`](docs/paper/README.md) — 조각마다 "
      "«어디서 왔나» 가 붙어 있다 | — |")
    A("| 본편·별편·조각, 층이 왜 이런지 알고 싶다 | "
      "[`docs/REPORTS_VOLUMES.md`](docs/REPORTS_VOLUMES.md) | — |")
    A("")
    A("### ① 빨리 훑기 — 30분")
    A("")
    A("본편 권마다 결론 절 하나씩이다. **오른쪽 칸이 그 절의 결론 문장 전체**이므로, 제목만")
    A("읽어도 한 바퀴가 돈다. 막히는 데서만 그 절을 연다. 별편의 결론은 아래 목차의 별편 표에 있다.")
    A("")
    A("| 권 | 절 | 이 절이 낸 결론 |")
    A("|---|---|---|")
    for v in trunk:
        p = parts.get(str(v["headline_part"]))
        if not p:
            continue
        A(f"| [{_vd(v)} «{esc(v['title'])}»](reports/{v['file']}) "
          f"| [절 {p['section']}](reports/{p['file']}) | {esc(p['title'])} |")
    A("")
    A("### ② 왜 믿을 수 있나 — 2시간")
    A("")
    A("검증·대조·반증 절만 모았다. 뼈대는 **눈감기 대조 · 사전등록 채점 · PREMATURE 판정 ·")
    A("널 교정** 넷이다 — 우리가 틀렸을 수 있는 자리를 우리가 먼저 때린 절들이다.")
    A("")
    A("| 권·절 | 무엇을 때렸나 |")
    A("|---|---|")
    for pno in VERIFY_PARTS:
        p = parts.get(str(pno))
        if not p:
            continue
        A(f"| [리포트 {_pd(p)} 절 {p['section']}](reports/{p['file']}) "
          f"| {esc(p['title'])} |")
    A("")
    A("---")
    A("")

    # ── 저장소가 한 일 ────────────────────────────────────────────────────────
    A("## 이 저장소가 한 일")
    A("")
    A("| 한 일 | 수치 | 어느 절 |")
    A("|---|---|---|")
    for what, value, anchor in _headline():
        p = anchors[anchor]
        A(f"| {what} | {value} | {_sec_link(p, disp)} |")
    A("")
    A("---")
    A("")

    # ── 권 목차 ──────────────────────────────────────────────────────────────
    A(f"## 목차 — 본편 {n_vol}권 + 별편 {n_comp}편")
    A("")
    A("권마다 답하는 물음이 하나다. 절 제목은 그 절의 **결론 문장** 그대로다.")
    A("")
    A("| 권 | 이 권이 답하는 물음 | 절 | 그림 |")
    A("|---|---|---|---|")
    for v in trunk:
        A(f"| [{_vd(v)} «{esc(v['title'])}»](#{_gh_slug(_vol_head(v))}) "
          f"| {esc(_cut(v['thesis']))} | {v['n_sections']} | {v['figures'] or ''} |")
    A("")
    if n_comp:
        A("**별편** — 부모 권의 물음에 딸린 답이다. 그림 무게로 나뉜 분권과 달리 번호가 부모-K 다.")
        A("")
        A("| 별편 | 부모 권 | 무엇을 다루나 |")
        A("|---|---|---|")
        for pno in sorted(idx.get("companions", {})):
            for c in idx["companions"][pno]:
                A(f"| [{c['label']} «{esc(c['title'])}»](reports/{c['file']}) "
                  f"| {disp.get(str(pno)) or _disp(pno)} | {esc(_cut(c['what']))} |")
        A("")
    A(f"셀 {idx['_meta']['n_cells']}개 · 각주 {idx['_meta']['n_footnotes']}개 · "
      f"그림 {n_fig}장. 절 단위 목차는 [`reports/README.md`](reports/README.md) 에도 있다.")
    A("")

    for v in vols:
        A(f"### {_vol_head(v)}")
        A("")
        if _is_comp(v):
            _pno = str(v.get("parent") or str(v["no"]).partition("_")[0])
            _pv = next((t for t in trunk if str(t["no"]) == _pno), None)
            if _pv is not None:
                A(f"[권 {_vd(_pv)} «{_pv['title']}»](#{_gh_slug(_vol_head(_pv))}) 의 "
                  "**별편**이다.")
                A("")
        A(v["thesis"])                     # 논지는 자기 강조를 이미 달고 있다
        A("")
        A(f"→ [`reports/{v['file']}`](reports/{v['file']})")
        A("")
        if len(v["files"]) > 1:
            A(f"이 {len(v['files'])}편은 `{v['builder']}` 가 짓는다."
              if v.get("builder") else f"이 권은 {len(v['files'])}편으로 나뉜다.")
            A("")
            A("| 편 | 무엇에 답하나 |")
            A("|---|---|")
            for nb in v.get("notebooks", []):
                A(f"| [`{nb['file']}`](reports/{nb['file']}) | {esc(nb['holds'])} |")
            A("")
            if v.get("append_to"):
                A(f"아래 절은 [`{v['append_to']}`](reports/{v['append_to']}) 에 이어 붙어 있다.")
                A("")
        A("| 절 | 이 절의 결론 |")
        A("|---|---|")
        for s in v["sections"]:
            A(f"| [{s['n']}](reports/{s['file']}) | {esc(s['title'])} |")
        A("")
        #  ⭐권에 딸린 별편 — 권 파일과 따로 살고 빌더도 다르다. 여기 안 적으면 디스크에
        #    있는 노트북이 루트 목차에서만 사라진다(reports/README.md 에는 있었다).
        _comps = idx.get("companions", {}).get(str(v["no"]), [])
        if _comps:
            _KOR = {1: "한", 2: "두", 3: "세", 4: "네"}
            A(f"별편이 {_KOR.get(len(_comps), str(len(_comps)))} 편 딸려 있다.")
            A("")
            for c in _comps:
                _bld = f"(빌더 `{c['builder']}`) " if c.get("builder") else ""
                A(f"- [{c['label']} «{esc(c['title'])}»](reports/{c['file']}) "
                  f"{_bld}— {esc(c['what'])}.")
            A("")

    A("---")
    A("")

    # ── 부록 · 규약 · 재현 ───────────────────────────────────────────────────
    A("## 부록 — 동결(유효하고, 새 작업은 넣지 않는다)")
    A("")
    A("| 위치 | 내용 |")
    A("|---|---|")
    A("| [`report_mesh/`](report_mesh) 8편 | 드론 메쉬 제작·검증 심화 가이드 |")
    A("| [`prior_work/`](prior_work) | 선행연구·오픈소스 조사 원자료 — 별편 1-2 의 census 가 "
      "여기서 나온다 |")
    A("| [`OPENSOURCE.md`](OPENSOURCE.md) | 오픈소스 대체 지도(RadarSimPy 교차검증 · "
      "OpenISAC X410 실측) |")
    A("| `report0N_*.ipynb` (루트) | **옛 8편** — 재구성 전 원본이고 대조가 끝날 때까지 "
      "제자리에 둔다 |")
    A("")
    A("## 다시 만들기")
    A("")
    A("순서가 중요하다 — 뒤 단계가 앞 단계의 산출물을 읽는다.")
    A("")
    A("```bash")
    A("cd /workspace/sionna")
    A("PY=~/.venvs/py312/bin/python")
    _CIRCLED = "①②③④⑤⑥⑦⑧⑨"
    for i, step in enumerate(idx["_meta"]["order"], 1):
        A("")
        mark = _CIRCLED[i - 1] if i <= len(_CIRCLED) else f"{i}."
        A(f"# {mark} {STEP_LEAD[step]}" if step in STEP_LEAD else f"# {mark}")
        A(STEP_CMD.get(step, f"PYTHONPATH=src $PY {step}"))
    A("")
    A("# 이 README (색인을 읽어 목차를 다시 낸다)")
    A("PYTHONPATH=src $PY src/make_readme.py")
    A("")
    A("# 숫자 자체를 다시 낸다 (GPU) — 어느 절의 어느 명령인지는 docs/REPRODUCE.md 에")
    A("PYTHONPATH=src:benchmark $PY benchmark/regen_mesh_dependents.py --list")
    A("PYTHONPATH=src:benchmark $PY benchmark/regen_mesh_dependents.py")
    A("```")
    A("")
    A("| | |")
    A("|---|---|")
    A("| Python | `~/.venvs/py312/bin/python` (3.12) — 이 한 env 로 전부 실행 |")
    A("| 핵심 | Sionna RT 2.0.1 · Mitsuba 3.8.0 · drjit 1.3.1 (OptiX GPU) · torch · "
      "numpy · trimesh + manifold3d |")
    A("| 노트북 커널 | `py312` |")
    A("| 실행 규약 | `PYTHONPATH=src:benchmark` 를 반드시 준다 |")
    A("")
    A("## 하우스 규약")
    A("")
    A("- **권 제목은 물음, 절 제목은 답이다.** 절 제목은 «…다» 로 끝나는 평서문이고, "
      "물음표로 끝나는 절 제목은 `src/report_style.py` 가 막는다.")
    A("- **숫자는 손으로 치지 않는다.** 전부 `num()` 이 JSON 을 열어 값을 대조하고, 화면에는")
    A("  각주 `[^n]` 으로 찍힌다. 절 끝 «출처» 표의 값은 표를 만들 때 JSON 을 **다시 열어**")
    A(f"  채운 것이다(왕복 검사). 지금 본편 {n_vol}권·별편 {n_comp}편에 각주 "
      f"{idx['_meta']['n_footnotes']}개와 그림 {n_fig}장이 실려 있다.")
    A("- **본문을 고칠 곳은 조각 빌더다.** 조각(`reports/_parts/`)과 권(`reports/`)은 둘 다 "
      "생성물이라, 손으로 고치면 다음 빌드에서 사라진다.")
    A("- **논문 문장과 재현 절차는 리포트 밖에 산다** — 사용자 지시다. "
      "[`docs/paper/`](docs/paper/README.md) 와 [`docs/REPRODUCE.md`](docs/REPRODUCE.md).")
    A("- 각 절은 `한 일 / 결과 / 방법 / 재현` 으로 열고 `다음 단계` 표로 닫는다. "
      "«다음 단계» 는 한계 목록이 아니라 앞을 보는 행동이다.")
    A("- 그림 텍스트(제목·축·범례·주석)는 **영어**, 본문·주석·print 는 **한국어**.")
    A("- **권의 길이는 그 권이 답하는 물음의 크기가 정한다** — 셀 수 상한을 두지 않는다.")
    A("")
    A("## 저장소 구조")
    A("")
    A("읽는 층과 만드는 층이 갈려 있다.")
    A("")
    A("```")
    A(f"reports/NN_slug.ipynb        ⭐본편 {n_vol}권 + 별편 {n_comp}편 — 사람이 읽는 문서."
      " 한 권이 물음 하나")
    A("  README.md                  권 목차 (생성물)")
    A(f"  _parts/NN_slug.ipynb       조각 {idx['_meta']['n_parts_on_disk']}편 — 빌더 산출물."
      " 직접 읽지 않는다")
    A("report_mesh/                 부록 8편 (동결)")
    A("prior_work/                  선행연구 조사 원자료")
    A("")
    A("src/")
    A("  build_partNN_*.py          ⭐조각 생성기 — 서술의 원본. 계산은 없다")
    A("  build_volumes.py           ⭐조각 → 권 + 색인 + reports/README.md")
    #  ⭐권 파일을 따로 내는 빌더는 손으로 적지 않는다 — 옛 «8권 네 편» 이 다섯 편이 된
    #    뒤에도(당시 편성) 그 줄만 옛말로 남아 있었다. 목록도 설명도 색인(`_meta.order`·
    #    `companions`)에서 읽는다.
    #  ⚠조립 별편(조각에서 조립되는 별편)의 빌더는 `build_volumes.py` 자신이다 — 색인이 그
    #    이름을 그대로 주면 위에 손으로 적은 줄과 **겹쳐 두 번** 찍힌다. 이미 적은 줄은 뺀다.
    _HAND = {"src/build_volumes.py", "src/make_readme.py"}
    _comp_by_builder = {c["builder"]: c
                        for cs in idx.get("companions", {}).values()
                        for c in cs if c.get("builder")}
    for step in idx["_meta"]["order"]:
        if step in _HAND or not (step.startswith("src/make_report")
                                 or step in _comp_by_builder):
            continue
        _b = os.path.basename(step)
        _own = next((v for v in n_split if step in (v.get("builder") or "")), None)
        if step in _comp_by_builder:
            #  «별편 5-2 을/를» 은 번호마다 조사가 갈린다 — 조사를 피해 적는다.
            _lead = f"별편 {_comp_by_builder[step]['label']} — 자기 파일만 낸다"
        elif _own is None:
            _lead = "권 파일을 짓는다"
        elif (_own.get("builder") or "").split()[0] == step:
            _lead = (f"{_vd(_own)}권 {len(_own['files'])}편 중 주 빌더"
                     " (그림이 무거워 따로 짓는다)")
        else:
            _lead = f"{_vd(_own)}권의 나머지 한 편"
        A(f"  {_b}{' ' * max(2, 31 - len(_b))}{_lead}")
    A("  make_readme.py             이 파일을 만든다")
    A("  report_style.py            규약 강제(num()·각주·부정문 계수)")
    A("  report_registry.py         앵커 사전 — 조각 사이 링크의 유일한 출처")
    A("  drones.py                  ⭐표적 레지스트리 DRONES — 기종·제원의 유일한 출처")
    A("  materials.py               ⭐전파재질 단일 진리원 — Sionna RT 와 PO 가 둘 다 읽는다")
    A("  rcs_sbr.py                 ⭐SBR+PO 커널 (Mitsuba 광선조준 + PO 표면적분)")
    A("  sigma_anchor.py            ⭐측정 앵커 재보정 σ=A(f)·B₁·B₂ + 미통제 항 원장")
    A("  waveforms*.py              WiFi/LTE/5G OFDM 합성 + Sionna PHY 대조")
    A("  passive_process.py         패시브 DSP: ECA → CAF 거리도플러 → CA-CFAR")
    A("  experiment_*.py            검출·자유공간 실험(GPU 몬테카를로)")
    A("  viz_*.py                   그림 (텍스트는 전부 영어)")
    A("")
    A("benchmark/")
    A("  check_report_links.py      ⭐링크·그림·출처 전수 검사")
    A("  regen_mesh_dependents.py   ⭐재생성 파이프라인 — 무엇을 어느 순서로 돌리나")
    A("  mie_pec_sphere.py          기준해 두 개(정확 Mie · 해석 PO) — 커널의 과녁")
    A("  verify_*.py                검증 하네스 (절이 읽는 verify_*.json 생산)")
    A("")
    A("outputs/                     *.json(숫자의 원본) · figures/ · volumes_index.json")
    A("docs/                        REPORTS_VOLUMES.md(편성) · REPRODUCE.md · paper/ · "
      "SPECS.md")
    A("```")
    A("")
    A(f"기계용 색인은 [`{IDX}`]({IDX}) 다 — 권·절·조각 배치와 셀·각주·그림 수가 전부 거기 "
      "있고, 이 README 의 목차는 그 파일을 읽어 만든 것이다.")
    A("")
    A("## 별도 주제 — 코드는 그대로 있다")
    A("")
    A("| 주제 | 코드 |")
    A("|---|---|")
    A("| 반무향 챔버 환경 | `src/chamber.py` · `benchmark/verify_clutter_doppler.py` |")
    A("| 바닥 유령 표적 | `benchmark/verify_floor_ghost.py` · `src/experiment_ghost.py` |")
    A("")
    return _footnotes("\n".join(L))


def _headline() -> list[tuple[str, str, str]]:
    """저장소 헤드라인 — (한 일, 수치, 어느 조각의 앵커)."""
    KRS, DFX, ANC = ("outputs/sbr_kr_sweep.json", "outputs/sbr_defect_fixes.json",
                     "outputs/rcs_anchor.json")
    DER, CEN = "outputs/report02_derived.json", "outputs/prior_census.json"
    LED, CFR = "outputs/report03_illuminators.json", "outputs/verify_cfar.json"
    return [
        ("**광선엔진 안에서 산란을 적분한다** — Sionna 자체 Mitsuba/OptiX 로 first-hit 가림을 "
         "판정하고 조명면 위에서 부품별 재질 PO 를 적분한다",
         "`src/rcs_sbr.py:184` · `src/materials.py`", "kernel-what"),

        ("**커널을 기준해로 검증했다** — 해석 PO 구 대비 kr 1~100 전 구간",
         "최대 " + num(None, (KRS, "summary_div16.max_abs_db_vs_po"), "{:.3f}", "dB"),
         "kernel-vs-reference"),

        ("**다중반사 위상을 PEC 이면각 닫힌형 8πa²b²/λ² 와 맞췄다** — 변 길이 4점",
         "최대 " + num(None, (DFX, "d3_multibounce_phase.max_abs_err_db"), "{:.3f}", "dB"),
         "kernel-vs-reference"),

        ("**바이스태틱 출사 가시성을 넣었다** — 히트마다 수신기 방향으로 그림자 광선을 쏜다",
         "상반성 위반 최악 "
         + num(None, (DFX, "d2_exit_vis_effect_on_reciprocity.worst_without_exit_vis_db"),
               "{:.2f}") + " → "
         + num(None, (DFX, "d2_exit_vis_effect_on_reciprocity.worst_with_exit_vis_db"),
               "{:.2f}", "dB"), "bistatic-exit"),

        ("**σ 의 주파수 기울기를 측정에 정렬했다** — σ = A(f)·B₁·B₂ 에서 A(f) 의 **기울기만** "
         "측정, **절대 레벨과 B₁ 은 우리 PO 출력**",
         num(None, (ANC, "literature.mu_eps.das_phantom3_mono.mu_a"), "{:.3f}", "dB/GHz")
         + " · 평균 레벨이동 "
         + num(None, (DER, "anchor_modes.level_shift_abs_max_db"), "{:.2f}", "dB")
         + " · 정규화 각패턴 이동 "
         + num(None, (DER, "anchor.shape_invariance_max_abs_db"), "{:.1e}", "dB"),
         "anchor-mode"),

        ("**모드 선택의 대가를 수치로 적었다** — 레벨까지 앵커에 맞추려면 크기전이 법칙을 하나 "
         "골라야 하고, 그 선택 하나가 기체당 최대 이만큼을 정한다",
         "L² ↔ L⁴ 예측 차 최대 "
         + num(None, (DER, "anchor_modes.size_law_spread_max_db"), "{:.2f}", "dB"),
         "anchor-ledger"),

        ("**우리 σ 를 눈감고 내고 봉인을 풀었다** — 문헌 상수를 한 번도 안 읽은 경로로 Phantom 3 "
         "를 내고 별도 스크립트가 열었다",
         "사전등록 판정 "
         + num(None, ("outputs/das_fleet_validation.json", "prereg_judgement.verdict")),
         "fleet-prereg"),

        ("**CFAR 를 경험 Pfa 로 교정했다** — GPU 몬테카를로로 오경보 셀을 직접 세었다",
         num(None, (CFR, "meta.runtime_s"), "{:,.0f}", "s") + ", 명목 1e-4 에서 배율을 "
         "형상마다 다시 잰다", "cfar-calib"),

        ("**세 파형을 한 표적·한 검출기로 비교했다** — 점유·대역·PRF·λ² 를 dB 원장으로 닫았다",
         "점유 " + num(None, (LED, "occupancy_cost.value_db"), "{:.1f}", "dB"), "cost-ledger"),

        ("**기체 7종을 사진·제원에서 세우고 실물 CAD 와 맞댔다**",
         "메쉬 " + num(None, (DER, "mesh.n"), "{:.0f}", "종") + " · 삼각형 "
         + num(None, (DER, "mesh.n_tris_total"), "{:,.0f}", "개"), "mesh-vs-real"),

        ("**선행연구를 전문으로 판정했다** — 아카이브 PDF 41편 중 16편, 게재상태는 PDF 로 확정",
         "드론 메쉬에서 산란을 계산한 게재본 "
         + num(None, (CEN, "funnel.all.g3_mesh_scattering"), "{:.0f}", "편"),
         "census-published"),
    ]


def main() -> int:
    idx = _index()
    text = build()
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(text)
    n_foot = len(re.findall(r"^\[\^\d+\]:", text, re.M))
    n_sec = sum(int(v["n_sections"]) for v in idx["volumes"])
    n_trunk = sum(1 for v in idx["volumes"] if not _is_comp(v))
    n_comp = sum(len(cs) for cs in idx.get("companions", {}).values())
    print(f"✅ README.md — {len(text):,}자 · 각주 {n_foot}개 · "
          f"본편 {n_trunk}권 · 별편 {n_comp}편 · 절 {n_sec}개")
    return 0


if __name__ == "__main__":
    sys.exit(main())
