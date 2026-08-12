# -*- coding: utf-8 -*-
"""
build_vol17_switch_fig.py — 권 17 절 「물리 스위치 단일축 분해」 그림 한 장.

읽는 것 (계산 없음 — 원장만 읽는다, GPU 안 씀)
    outputs/diag_physics_paths_el-90.json     6 케이스 × (경로 수 · 레벨 · AC/DC)
쓰는 것
    outputs/figures/vol17_f1_switches.png     ⭐스위치별 세 패널

⭐ 잣대를 왜 이렇게 골랐나
  · 세 양(경로 수 · 레벨 dB · AC/DC dB)은 눈금이 전혀 달라서 **한 축에 겹치지 않는다.**
    축 두 개를 한 그림에 넣는 대신 **패널 셋**으로 나눈다.
  · 색은 «순위» 가 아니라 **어느 스위치인지**를 따라간다. 세 패널에서 같은 스위치는 같은 색이다.
    결과를 바꾼 둘(굴절 = 파랑 · 회절 = 빨강)만 색을 갖고, 나머지는 회색이다.
    넷을 다 켠 판은 회절과 **같은 값**이라 회절 색에 빗금을 얹어 그 사실을 형태로도 적는다.
  · 막대마다 값을 직접 적는다 — 색맹 조건에서도 이름과 숫자만으로 읽힌다.
  · 그림 안에 설정값(광선 수 · 자세 수 · 앙각)은 적지 않는다. 그것은 리포트 본문이 말한다.

    PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/build_vol17_switch_fig.py
"""
from __future__ import annotations

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                  # noqa: E402
from matplotlib.patches import Patch                             # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIG = os.path.join(ROOT, "outputs", "figures")
os.makedirs(FIG, exist_ok=True)

SRC = os.path.join(ROOT, "outputs", "diag_physics_paths_el-90.json")
J = json.load(open(SRC, encoding="utf-8"))
C = J["cases"]

# ── 케이스 이름은 한국어 원장 키 → 그림 글자는 영어(하우스 규약) ──────────────
GRAY, BLUE, RED = "#9aa3ad", "#1565c0", "#c62828"
CASES = [
    ("기준(지금까지의 실행)", "baseline (depth 1)",       GRAY, ""),
    ("굴절만 켬",             "refraction only",          BLUE, ""),
    ("회절만 켬",             "diffraction only",         RED,  ""),
    ("모서리회절만 켬",        "edge diffraction only",    GRAY, ""),
    ("다중반사만 (depth 3)",   "multi-bounce (depth 3)",   GRAY, ""),
    ("전부 켬 (--physics)",    "all switches on",          RED,  "///"),
]
KO = [c[0] for c in CASES]
EN = [c[1] for c in CASES]
COL = [c[2] for c in CASES]
HAT = [c[3] for c in CASES]

plt.rcParams.update({
    "font.size": 11, "axes.titlesize": 12, "axes.labelsize": 11,
    "legend.fontsize": 9.5, "figure.facecolor": "white",
    "savefig.facecolor": "white", "axes.grid": True, "grid.alpha": 0.22,
    "axes.axisbelow": True,
})

#: (원장 키, 패널 제목, 축 이름, 값 표시, 그리는 꼴)
#  · 개수는 0 이 진짜 0 이라 **막대**로 그린다.
#  · 레벨(dB)은 0 이 없는 눈금이라 막대 대신 **점**으로 놓는다 — 바닥을 잘라 만든 막대는
#    길이 비를 없는 뜻으로 읽히게 한다.
#  · AC/DC 는 0 dB 를 사이에 두고 갈리므로 0 에서 시작하는 막대가 그 갈림을 그대로 보인다.
PANELS = [
    ("npaths_median", "Paths per pose (median)",     "paths", "{:.0f}",  "bar0"),
    ("level_db",      "Coherent level",              "dB",    "{:.2f}",  "dot"),
    ("ac_over_dc_db", "Modulation / static (AC/DC)", "dB",    "{:+.2f}", "bar0"),
]

fig, axs = plt.subplots(1, 3, figsize=(15.4, 4.4))
y = list(range(len(CASES)))[::-1]                 # 첫 케이스를 맨 위로

for a, (key, title, unit, fmt, kind) in zip(axs, PANELS):
    v = [float(C[k][key]) for k in KO]
    lo, hi = min(v), max(v)
    if kind == "bar0":
        lo, hi = min(0.0, lo), max(0.0, hi)
    span = (hi - lo) or 1.0
    pad = 0.14 * span

    if kind == "bar0":
        a.barh(y, v, height=0.62, color=COL, edgecolor="white", linewidth=1.2)
        for h, hh in zip(a.patches, HAT):
            if hh:
                h.set_hatch(hh)
                h.set_edgecolor("white")
        a.axvline(0.0, color="0.35", lw=1.0)
    else:
        for yy, x, c, hh in zip(y, v, COL, HAT):
            a.plot([x], [yy], marker="o", ms=13, color=c, mec="white", mew=1.6,
                   zorder=3)
            if hh:      # 넷을 다 켠 판 — 회절만 켠 판과 같은 값이라 표식을 얹는다
                a.plot([x], [yy], marker="x", ms=7, color="white", mew=2.2,
                       zorder=4)

    for yy, x in zip(y, v):
        right = x >= 0.0 if kind == "bar0" else True
        a.text(x + (0.035 if right else -0.035) * span, yy, fmt.format(x),
               va="center", ha="left" if right else "right",
               color="0.15", fontsize=10.5)

    a.set_xlim(lo - pad, hi + 2.2 * pad)
    a.set_ylim(-0.7, len(CASES) - 0.3)
    a.set_yticks(y)
    a.set_yticklabels(EN if a is axs[0] else [""] * len(EN))
    a.set_title(title, pad=9)
    a.set_xlabel(unit)
    a.grid(axis="y", visible=False)

axs[0].legend(handles=[
    Patch(facecolor=BLUE, edgecolor="white", label="switch that moves the path count"),
    Patch(facecolor=RED, edgecolor="white", label="switch that moves the level"),
    Patch(facecolor=RED, edgecolor="white", hatch="///",
          label="all four on — level equals diffraction alone"),
    Patch(facecolor=GRAY, edgecolor="white", label="outcome equals the baseline"),
], loc="upper left", bbox_to_anchor=(0.0, -0.24), ncol=2, frameon=False)

fig.suptitle("One switch at a time: what each PathSolver physics flag changes",
             y=1.02, fontsize=13.5)
out = os.path.join(FIG, "vol17_f1_switches.png")
fig.savefig(out, dpi=170, bbox_inches="tight")
plt.close(fig)
print(f"  ✅ {out}")
