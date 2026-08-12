# -*- coding: utf-8 -*-
"""
viz_ch1_el0_budget_ladder.py — **el 0 광선 예산 사다리** 한 장.

읽는 것 (원장만 — 계산도 GPU 도 없다)
    outputs/elevation_sweep_md.json     팔별·앙각별 레벨·박자·경로 수
쓰는 것
    outputs/figures/ch1_f6_el0_budget_ladder.png

무엇을 보이나
    (a) 11.1 M 계단 대비 **레벨 변화** — el 0 은 0.03 dB 안에 모이고 el −30 은 계속 올라간다
    (b) **박자** 대 광선 — el −30 은 f_flash 에 붙고 el 0 은 창 안을 헤맨다
    (c) **자세당 경로 수 중앙값** — 광선과 함께 자란다

⚠ 그림 글자는 전부 영어(하우스 규약). 그림 안에 하이퍼파라미터는 넣지 않는다 —
  x 축의 광선 수는 이 그림이 흔드는 축 자신이고, f_flash 선은 **입력한 참값**이다.

    PYTHONPATH=src ~/.venvs/py312/bin/python src/viz_ch1_el0_budget_ladder.py
"""
from __future__ import annotations

import json
import os
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                     # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from report_style import assert_fig_text                            # noqa: E402

FIG = os.path.join(ROOT, "outputs", "figures")
OUT_NAME = "ch1_f6_el0_budget_ladder.png"

J = json.load(open(os.path.join(ROOT, "outputs", "elevation_sweep_md.json"),
                   encoding="utf-8"))
M = J["_meta"]
FFL = float(M["f_flash_hz"])
RULE_SPP = int(M["sionna_spp"])            # (R/3)² × 1M 규칙값 — 10 m 에서 11.1 M

#: 박자 탐색창 — `benchmark/elevation_sweep_md.py:237` 의 `sel = (fr >= 40) & (fr <= 400)`
SEARCH_LO, SEARCH_HI = 40.0, 400.0

C_EL0, C_EL30 = "#1565c0", "#c62828"


def spp_of(engine: str) -> int:
    """팔 이름이 곧 광선 예산이다 — `sionna` 는 규칙값, `sionna_pN` 은 N 발."""
    m = re.match(r"^sionna_p(\d+)$", engine)
    return int(m.group(1)) if m else RULE_SPP


def ladder(el_deg: float) -> list[dict]:
    """그 앙각의 **완결된**(n_missing == 0) PathSolver 행을 광선 순서로."""
    rows = [r for r in J["rows"]
            if r["engine"].startswith("sionna") and "phys" not in r["engine"]
            and float(r["el_deg"]) == el_deg and int(r["n_missing"]) == 0]
    return sorted(rows, key=lambda r: spp_of(r["engine"]))


def main() -> str:
    os.makedirs(FIG, exist_ok=True)
    L0, L30 = ladder(0.0), ladder(-30.0)
    x0 = [spp_of(r["engine"]) / 1e6 for r in L0]
    x30 = [spp_of(r["engine"]) / 1e6 for r in L30]

    plt.rcParams.update({
        "font.size": 11, "axes.titlesize": 12, "axes.labelsize": 11,
        "legend.fontsize": 9.5, "figure.facecolor": "white",
        "savefig.facecolor": "white", "axes.grid": True, "grid.alpha": 0.25,
        "axes.axisbelow": True,
    })
    fig, ax = plt.subplots(1, 3, figsize=(16.2, 5.2))

    # ── (a) 가장 작은 예산 대비 레벨 변화 ────────────────────────────────────
    a = ax[0]
    for rows, x, col, lab in ((L0, x0, C_EL0, "el 0"), (L30, x30, C_EL30, "el -30")):
        base = float(rows[0]["level_db"])
        a.semilogx(x, [float(r["level_db"]) - base for r in rows], "o-",
                   color=col, lw=1.9, ms=7.5, label=f"{lab}, mean level")
        bb = float(rows[0]["track"]["band_power_db"])
        a.semilogx(x, [float(r["track"]["band_power_db"]) - bb for r in rows], "s--",
                   color=col, lw=1.5, ms=6, alpha=0.75,
                   label=f"{lab}, propeller-band power")
    span0 = max(abs(float(r["level_db"]) - float(L0[0]["level_db"])) for r in L0)
    a.annotate(f"el 0 stays inside {span0:.2f} dB\nover a 360x ray increase",
               xy=(x0[-1], float(L0[-1]["level_db"]) - float(L0[0]["level_db"])),
               xytext=(0.34, 0.04), textcoords="axes fraction", fontsize=9.5,
               color="0.2", ha="left",
               arrowprops=dict(arrowstyle="->", color="0.35", lw=1.2))
    a.axhline(0.0, color="0.6", lw=1.0)
    a.set_ylim(-1.6, None)
    a.set_xlabel("rays per pose [millions]")
    a.set_ylabel("change from the smallest budget [dB]")
    a.set_title("(a)  Level: converged at el 0, still climbing at el -30", pad=6,
                fontsize=11.5)
    a.legend(loc="upper left")

    # ── (b) 박자 ────────────────────────────────────────────────────────────
    a = ax[1]
    a.axhspan(0, SEARCH_LO, color="0.88", zorder=0)
    a.axhspan(SEARCH_HI, 430, color="0.88", zorder=0)
    a.text(x0[0] * 0.75, SEARCH_HI + 8, "outside the peak-search window",
           fontsize=9, color="0.35")
    a.axhline(FFL, color="#2e7d32", lw=1.6)
    a.text(x0[0] * 0.75, FFL + 12, f"f_flash (input) = {FFL:.2f} Hz",
           color="#1b5e20", fontsize=9.5)
    a.axhline(2 * FFL, color="#2e7d32", lw=1.1, ls=":")
    a.text(x0[0] * 0.75, 2 * FFL + 12, "2 x f_flash", color="#1b5e20", fontsize=9)
    for rows, x, col, lab in ((L0, x0, C_EL0, "el 0"), (L30, x30, C_EL30, "el -30")):
        a.semilogx(x, [float(r["track"]["beat_hz"]) for r in rows], "o-",
                   color=col, lw=1.9, ms=7.5, label=lab)
    a.set_ylim(0, 430)
    a.set_xlabel("rays per pose [millions]")
    a.set_ylabel("strongest modulation line [Hz]")
    a.set_title("(b)  Flash rate: el -30 locks on, el 0 wanders", pad=6,
                fontsize=11.5)
    a.legend(loc="center right")

    # ── (c) 경로 수 ─────────────────────────────────────────────────────────
    a = ax[2]
    for rows, x, col, lab in ((L0, x0, C_EL0, "el 0"), (L30, x30, C_EL30, "el -30")):
        a.loglog(x, [int(r["npaths_median"]) for r in rows], "s-", color=col,
                 lw=1.9, ms=7.5, label=lab)
    a.annotate("same budget, different elevation,\ndifferent path count",
               xy=(x30[1], int(L30[1]["npaths_median"])), xytext=(0.08, 0.78),
               textcoords="axes fraction", fontsize=9.5, color="0.2",
               arrowprops=dict(arrowstyle="->", color="0.35", lw=1.2))
    a.set_xlabel("rays per pose [millions]")
    a.set_ylabel("median paths per pose")
    a.set_title("(c)  Paths grow with the budget", pad=6, fontsize=11.5)
    a.legend(loc="lower right")

    fig.suptitle("CH1-F6   Ray-budget ladder at el 0, with el -30 as the control",
                 fontsize=14, y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.94))

    labels = [t.get_text() for a in ax
              for t in ([a.title, a.xaxis.label, a.yaxis.label]
                        + list(a.texts) + (a.get_legend().texts
                                           if a.get_legend() else []))]
    assert_fig_text(*[s for s in labels if s])

    p = os.path.join(FIG, OUT_NAME)
    fig.savefig(p, dpi=170, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✅ {p}")
    return p


if __name__ == "__main__":
    main()
