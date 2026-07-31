# -*- coding: utf-8 -*-
"""
figs_report01.py — 리포트 01 의 그림 4장을 **게재 품질로** 다시 그린다
============================================================================================
계약: `docs/PAPER_SPEC.md` §4.3 — 벡터(PDF) + 300 dpi 이상 PNG 동시 저장 · 2단 축소 뒤에도
8 pt 이상 · **색 + 해치/마커 이중부호화**(흑백 인쇄에서 색은 사라진다) · 캡션은 논문에 그대로
붙일 완결 문장. 강제는 `src/paper_kit.py` 의 `save_figure()` 가 한다 — 규격을 어기면 저장 전에
예외가 나고, 통과한 감사 결과는 PDF 메타데이터에 심겨 `check_figure()` 로 다시 확인된다.

그리는 것 (전부 JSON 에서 읽는다. 여기서 새로 계산하는 값은 없다)
    F1 관문 깔때기      ⟨outputs/prior_work_survey.json : funnel⟩
    F2 조달 갈래        ⟨outputs/report01_paper.json : route_status⟩
    F3 dBsm 등장 횟수   ⟨outputs/prior_work_survey.json : papers[].terms.dbsm⟩
    F4 H8 관문 성적표   ⟨outputs/report01_paper.json : h8.scorecard⟩  ← Rzewuski 포함 12편

그림 안의 글자는 전부 영어다(하우스 규약). 본문·주석·print 는 한국어다.

실행
    cd /home/yunjung/workspace/sionna2
    PYTHONPATH=src ~/.venvs/py312/bin/python src/figs_report01.py
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import numpy as np                                            # noqa: E402

from paper_kit import PALETTE, check_figure, paper_style, save_figure   # noqa: E402

SURVEY = os.path.join(_ROOT, "outputs/prior_work_survey.json")
PAPER = os.path.join(_ROOT, "outputs/report01_paper.json")
FIGDIR = "outputs/figures"

#: 두 계열은 **색 + 해치**로 동시에 갈린다. 명도차 0.263(#0072B2 L=0.153 / #E69F00 L=0.416).
C_PUB, C_PRE = PALETTE[0], PALETTE[1]
H_PUB, H_PRE = "", "///"

#: 논문에 그대로 붙일 캡션(완결 문장). 노트북 캡션(질문)은 빌더가 따로 단다.
CAPTIONS = {
    "f1": ("Gate funnel over the 21 adjudicated documents: requiring a Sionna-class ray engine, "
           "drone geometry inside it, and a scattering amplitude computed on that mesh leaves no "
           "paper standing, published or preprint."),
    "f2": ("Seven routes by which the surveyed papers obtained a target signature; the route a "
           "paper chooses fixes the size of the claim it can make, and only three papers compute "
           "scattering on a mesh inside the ray engine."),
    "f3": ("Occurrences of the string dBsm in each full text: absolute radar cross section is "
           "printed by measurement and full-wave papers, and by a single ray-engine paper whose "
           "target is a vehicle."),
    "f4": ("Prong-by-prong adjudication of the twelve H8 candidates; every candidate fails at "
           "least one of published, drone mesh, in-engine ray solver, validated amplitude, and "
           "the closest published work fails only on the engine prong."),
}


def _load():
    with open(SURVEY, encoding="utf-8") as f:
        S = json.load(f)
    with open(PAPER, encoding="utf-8") as f:
        P = json.load(f)
    return S, P


# --------------------------------------------------------------------------- #
def fig_funnel(S, P):
    stages = ["Adjudicated documents", "G1  Sionna-class ray engine",
              "G2  + drone mesh inside it", "G3  + scattering on that mesh",
              "G4  + absolute RCS in dBsm"]
    keys = ["in_survey", "g1_engine", "g2_drone_mesh", "g3_mesh_scattering", "g4_dbsm"]
    pub = np.array([S["funnel"]["published"][k] for k in keys], float)
    pre = np.array([S["funnel"]["preprint"][k] for k in keys], float)
    y = np.arange(len(stages))[::-1]

    with paper_style(width="double", base_pt=10.0) as st:
        fig, ax = st.figure(height=2.9)
        ax.barh(y, pub, color=C_PUB, hatch=H_PUB, edgecolor="white",
                label="Published (venue of record)")
        ax.barh(y, pre, left=pub, color=C_PRE, hatch=H_PRE, edgecolor="white",
                label="Preprint only")
        for i in range(len(stages)):
            ax.text(pub[i] + pre[i] + 0.35, y[i],
                    f"{int(pub[i] + pre[i])}  ({int(pub[i])} published)",
                    va="center", fontsize=9.0)
        ax.set_yticks(y, stages, fontsize=9.0)
        ax.set_xlabel("Number of documents")
        ax.set_xlim(0, len(S["papers"]) + 7)
        ax.set_ylim(-0.7, len(stages) - 0.3)
        ax.legend(loc="lower right", fontsize=9.0)
        ax.grid(axis="y", visible=False)
    return save_figure(fig, f"{FIGDIR}/report01_p1_funnel", caption=CAPTIONS["f1"],
                       title="Gate funnel", placed_width_in=7.16, close=True)


def fig_routes(S, P):
    R = P["route_status"]
    order = sorted(R, reverse=True)
    lab = [f'{k}  {S["routes"][k]["label_en"]}' for k in order]
    pub = np.array([R[k]["published"] for k in order], float)
    pre = np.array([R[k]["papers"] - R[k]["published"] for k in order], float)
    y = np.arange(len(order))[::-1]

    with paper_style(width="double", base_pt=10.0) as st:
        fig, ax = st.figure(height=3.1)
        ax.barh(y, pub, color=C_PUB, hatch=H_PUB, edgecolor="white",
                label="Published (venue of record)")
        ax.barh(y, pre, left=pub, color=C_PRE, hatch=H_PRE, edgecolor="white",
                label="Preprint only")
        for i in range(len(order)):
            ax.text(pub[i] + pre[i] + 0.12, y[i], f"{int(pub[i] + pre[i])}",
                    va="center", fontsize=9.0)
        ax.set_yticks(y, lab, fontsize=9.0)
        ax.set_xlabel("Number of documents")
        ax.set_xlim(0, max(pub + pre) + 1.2)
        ax.set_ylim(-0.7, len(order) - 0.3)
        ax.legend(loc="lower right", fontsize=9.0)
        ax.grid(axis="y", visible=False)
    return save_figure(fig, f"{FIGDIR}/report01_p2_routes", caption=CAPTIONS["f2"],
                       title="Target-signature routes", placed_width_in=7.16, close=True)


def fig_dbsm(S, P):
    ps = sorted(S["papers"], key=lambda q: (q["terms"]["dbsm"], q["short"]))
    v = np.array([q["terms"]["dbsm"] for q in ps], float)
    eng = np.array([bool(q["gates"]["g1_engine"]) for q in ps])
    y = np.arange(len(ps))
    lab = [q["short"].split(" (")[0] for q in ps]

    with paper_style(width="double", base_pt=10.0) as st:
        fig, ax = st.figure(height=4.2)
        ax.barh(y[eng], v[eng], color=C_PUB, hatch=H_PUB, edgecolor="white",
                label="Runs a Sionna-class ray engine")
        ax.barh(y[~eng], v[~eng], color=C_PRE, hatch=H_PRE, edgecolor="white",
                label="Signature obtained outside the ray engine")
        for i in range(len(ps)):
            if v[i] > 0:
                ax.text(v[i] + 0.6, y[i], f"{int(v[i])}", va="center", fontsize=9.0)
        ax.set_yticks(y, lab, fontsize=9.0)
        ax.set_xlabel('Occurrences of "dBsm" in the full text')
        ax.set_xlim(0, max(v) + 6)
        ax.set_ylim(-0.7, len(ps) - 0.3)
        ax.legend(loc="lower right", fontsize=9.0)
        ax.grid(axis="y", visible=False)
    return save_figure(fig, f"{FIGDIR}/report01_p3_dbsm", caption=CAPTIONS["f3"],
                       title="Absolute RCS in the corpus", placed_width_in=7.16, close=True)


def fig_prongs(S, P):
    rows = P["h8"]["scorecard"]
    cols = ["P1\npublished", "P2\ndrone mesh", "P3\nin-engine solver", "P4\nvalidated amplitude"]
    score = {"yes": 1.0, "partial": 0.5, "no": 0.0}
    M = np.array([[score[r[k]] for k in ("P1", "P2", "P3", "P4")] for r in rows])
    T = [[r[k] for k in ("P1", "P2", "P3", "P4")] for r in rows]

    import matplotlib.colors as mcolors
    cmap = mcolors.ListedColormap(["#FFFFFF", "#E8E8E8", C_PUB])
    with paper_style(width="double", base_pt=10.0) as st:
        fig, ax = st.figure(height=3.9)
        ax.imshow(M, cmap=cmap, vmin=0, vmax=1, aspect="auto")
        for i in range(M.shape[0]):
            for j in range(M.shape[1]):
                ax.text(j, i, T[i][j], ha="center", va="center", fontsize=9.0,
                        color="white" if M[i, j] == 1.0 else "#222222")
        ax.set_xticks(range(len(cols)), cols, fontsize=9.0)
        ax.set_yticks(range(len(rows)), [r["label"] for r in rows], fontsize=9.0)
        ax.set_xticks(np.arange(-0.5, len(cols), 1), minor=True)
        ax.set_yticks(np.arange(-0.5, len(rows), 1), minor=True)
        ax.grid(which="minor", color="#666666", lw=0.6)
        ax.grid(which="major", visible=False)
        ax.tick_params(which="minor", length=0)
        ax.tick_params(axis="x", length=0)
        for s in ax.spines.values():
            s.set_visible(True)
            s.set_linewidth(0.6)
    return save_figure(fig, f"{FIGDIR}/report01_p4_prongs", caption=CAPTIONS["f4"],
                       title="H8 prong scorecard", placed_width_in=7.16, close=True)


# --------------------------------------------------------------------------- #
def main() -> int:
    S, P = _load()
    print("── 리포트 01 그림 (게재 품질) ──")
    made = []
    for fn in (fig_funnel, fig_routes, fig_dbsm, fig_prongs):
        out = fn(S, P)
        chk = out["check"]
        print(f"  {out['pdf']} · 최소 글자 {chk['min_font_pt']} pt "
              f"(배치 {chk['placed_width_in']} in → {chk['effective_min_font_pt']} pt) · "
              f"PNG {chk['png_dpi']} dpi · 색만 구분 {len(chk['colour_only_series'])}건 · "
              f"{'통과' if chk['ok'] else '위반 ' + str(chk['violations'])}")
        made.append(out)
    for m in made:
        rep = check_figure(m["pdf"], placed_width_in=7.16)
        if not rep["ok"]:
            raise SystemExit(f"저장본 재검사 실패: {rep}")
    print(f"✅ 그림 {len(made)}장 — 벡터 PDF + 400 dpi PNG, 저장본 재검사 통과")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
