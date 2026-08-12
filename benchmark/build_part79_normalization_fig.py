# -*- coding: utf-8 -*-
"""
build_part79_normalization_fig.py — 권 16 절 2 의 **정규화 그림 한 장**.

읽는 것 (계산 없음 — 원장만 읽는다, GPU 안 씀)
    outputs/ch1_elevation_figdata.json   앙각별 대역 몫 · 반송파 몫
쓰는 것
    outputs/figures/part79_normalization.png

⭐ 왜 이 그림이 필요한가
  대역 몫의 분모는 **전체 전력**이다. 동체선(반송파)이 널이 되는 앙각에서는 분자가 그대로여도
  몫이 혼자 뛴다. 그래서 같은 양을 **반송파 기준**으로도 그려 나란히 놓는다 — 두 선이 갈라지는
  자리가 곧 분모가 움직인 자리다.

  그림 글자는 전부 영어(하우스 규약). 본문·주석은 한국어.

    PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/build_part79_normalization_fig.py
"""
from __future__ import annotations

import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                        # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
from report_style import assert_fig_text                               # noqa: E402

FIG = os.path.join(ROOT, "outputs", "figures")
os.makedirs(FIG, exist_ok=True)

D = json.load(open(f"{ROOT}/outputs/ch1_elevation_figdata.json", encoding="utf-8"))
C = D["cells"]

ELS = [0, -15, -30, -45, -60, -75]          # f_tip > 0 인 6 점 — 추적 대역이 정의되는 자리
KEYS = [f"ours/el{e:+.0f}" for e in ELS]

RED, BLUE, GREY = "#c62828", "#1565c0", "#8e9aab"

TXT = dict(
    title="Same tracking-band energy, two denominators  (ours, SBR + PO)",
    a="(a)  tracking-band energy",
    b="(b)  carrier (body line) energy",
    x="elevation [deg]",
    ya="tracking-band energy [dB]",
    yb="carrier energy, share of total power [dB]",
    l1="share of total power",
    l2="relative to carrier",
    lband="carrier null",
    note="the gap between the two curves is the carrier share",
    note2="carrier nulls, so the share of total power inflates",
)
assert_fig_text(*TXT.values())


def main() -> None:
    tot = [C[k]["share_track_db"] for k in KEYS]
    rel = [C[k]["share_track_rel_carrier_db"] for k in KEYS]
    car = [C[k]["carrier_share_db"] for k in KEYS]

    fig, ax = plt.subplots(1, 2, figsize=(13.4, 5.4))

    ax[0].fill_between(ELS, tot, rel, color=BLUE, alpha=0.10, zorder=0)
    ax[0].plot(ELS, tot, "-o", color=RED, lw=2.2, ms=7, label=TXT["l1"], zorder=3)
    ax[0].plot(ELS, rel, "--s", color=BLUE, lw=1.8, ms=6, label=TXT["l2"], zorder=3)
    ax[0].set_title(TXT["a"], fontsize=12)
    ax[0].set_ylabel(TXT["ya"])
    ax[0].set_ylim(-31, 20)
    ax[0].legend(loc="upper left", fontsize=10, framealpha=0.95)
    ax[0].annotate(TXT["note"], xy=(-45, 0.5 * (tot[3] + rel[3])), xytext=(-38, -28),
                   fontsize=10, color=BLUE, ha="center",
                   arrowprops=dict(arrowstyle="->", color=BLUE, lw=1.2))
    ax[0].annotate(TXT["note2"], xy=(-60, rel[4]), xytext=(-62, 16),
                   fontsize=10, color="#333333", ha="center",
                   arrowprops=dict(arrowstyle="->", color="#333333", lw=1.2))

    ax[1].plot(ELS, car, "-o", color=GREY, lw=2.2, ms=7, zorder=3)
    ax[1].set_title(TXT["b"], fontsize=12)
    ax[1].set_ylabel(TXT["yb"])
    ax[1].set_ylim(-16.5, 0.5)

    for a in ax:
        a.axvspan(-64, -56, color="#9e9e9e", alpha=0.16, lw=0, zorder=0,
                  label=TXT["lband"])
        a.set_xlabel(TXT["x"])
        a.set_xticks(ELS)
        a.invert_xaxis()
        a.grid(alpha=0.3)
    ax[1].legend(loc="lower left", fontsize=10, framealpha=0.95)

    fig.suptitle(TXT["title"], fontsize=13.5)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    out = os.path.join(FIG, "part79_normalization.png")
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"✅ {os.path.relpath(out, ROOT)}")


if __name__ == "__main__":
    main()
