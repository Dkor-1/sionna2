# -*- coding: utf-8 -*-
"""
figs_report17_switch_axis.py — 권 17 절 1 의 그림 한 장.

읽는 것 (계산 없음 — 원장만 읽는다, GPU 안 씀)
    outputs/diag_physics_paths_el-90.json   스위치 하나씩만 바꾼 6 판
쓰는 것
    outputs/figures/report17_switch_axis.png

그림이 답하는 질문 하나 — **네 스위치 중 어느 것이 나딧 레벨을 올리나?**
왼쪽 막대는 판마다의 레벨[dB], 오른쪽 숫자는 그 판의 경로 중앙값이다.

    PYTHONPATH=src ~/.venvs/py312/bin/python src/figs_report17_switch_axis.py
"""
from __future__ import annotations

import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                      # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from report_style import assert_fig_text             # noqa: E402

SRC = os.path.join(ROOT, "outputs", "diag_physics_paths_el-90.json")
FIG = os.path.join(ROOT, "outputs", "figures")
OUT = os.path.join(FIG, "report17_switch_axis.png")

#: 원장의 판 이름 → 그림에 쓸 영어 이름 (그림 글자는 전부 영어 — 하우스 규약).
LABEL = {
    "기준(지금까지의 실행)": "baseline (as the sweep ran)",
    "굴절만 켬": "refraction only",
    "회절만 켬": "diffraction only",
    "모서리회절만 켬": "free-edge diffraction only",
    "다중반사만 (depth 3)": "multi-bounce only",
    "전부 켬 (--physics)": "all four on",
}

plt.rcParams.update({
    "font.size": 11, "axes.titlesize": 12.5, "axes.labelsize": 11,
    "figure.facecolor": "white", "savefig.facecolor": "white",
    "axes.grid": True, "grid.alpha": 0.25, "axes.axisbelow": True,
})


def main() -> None:
    with open(SRC, encoding="utf-8") as f:
        D = json.load(f)
    cases = D["cases"]
    names = list(LABEL)
    missing = [n for n in names if n not in cases]
    if missing:
        raise SystemExit(f"원장에 없는 판: {missing} — {SRC}")

    lab = [LABEL[n] for n in names]
    lvl = [float(cases[n]["level_db"]) for n in names]
    npm = [int(cases[n]["npaths_median"]) for n in names]
    base = float(cases["기준(지금까지의 실행)"]["level_db"])
    title = "Only one switch moves the nadir level"
    xlab = "Coherent level of the returned paths  [dB]"
    ylab_note = "median\npath count"

    assert_fig_text(title, xlab, ylab_note, *lab)

    # 회절이 든 판만 색을 준다 — 그림 하나가 답하는 질문이 그것이다.
    col = ["#c0392b" if v > base + 10.0 else "#5b7c99" for v in lvl]

    fig, ax = plt.subplots(figsize=(9.6, 4.4))
    y = list(range(len(names)))[::-1]
    ax.barh(y, lvl, color=col, height=0.62,
            left=0.0, edgecolor="white", linewidth=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels(lab)
    ax.set_xlabel(xlab)
    ax.set_title(title, pad=9)
    ax.set_xlim(-142.0, 16.0)
    ax.axvline(base, color="#444444", lw=1.1, ls="--")
    ax.text(base - 1.8, y[0] + 0.62, "baseline", ha="right", va="center",
            fontsize=10, color="#444444")
    for yy, v, n, c in zip(y, lvl, npm, col):
        ax.text(v + 2.0, yy, f"{v:.2f} dB", va="center", ha="left", fontsize=10,
                color="white" if c == "#c0392b" else "white")
        ax.text(6.0, yy, f"{n}", va="center", ha="center", fontsize=10,
                color="#555555")
    ax.annotate(ylab_note, xy=(6.0, 1.015), xycoords=("data", "axes fraction"),
                ha="center", va="bottom", fontsize=9.5, color="#555555")
    ax.axvline(0.0, color="#999999", lw=0.8)
    fig.tight_layout()
    os.makedirs(FIG, exist_ok=True)
    fig.savefig(OUT, dpi=170, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✅ {OUT}")


if __name__ == "__main__":
    main()
