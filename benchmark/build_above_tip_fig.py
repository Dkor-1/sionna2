# -*- coding: utf-8 -*-
"""build_above_tip_fig.py — ⭐«물리 상한 위로 새는 에너지» 잣대 한 장 (조각 80 전용)

■ 왜 새로 그리나
    `outputs/figures/wideband_energy.png` 은 세 단이고 그중 (c) 만 이 잣대를 그린다.
    조각 80 은 잣대 **하나**를 설명하는 절이라 그림도 한 질문만 답해야 한다 —
      (a) 상한이 앙각에 따라 어디에 그어지나 (관찰 대역의 어디까지가 물리적으로 가능한가)
      (b) 팔마다 그 위에 얼마가 놓이나 (참값이 0 인 자리다)

■ 원장
    outputs/wideband_energy.json  — 값을 여기서만 읽는다. 새로 계산하지 않는다.
    ⛔GPU 를 쓰지 않는다. JSON 을 읽어 matplotlib 로 그릴 뿐이다.

■ 하우스 규약
    그림 안의 글자는 **전부 영어**. 하이퍼파라미터는 그림 안에 적지 않는다
    (관찰 상한·PRF 는 리포트 본문의 세팅 블록이 말한다).

실행
    cd /home/yunjung/workspace/sionna2
    PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/build_above_tip_fig.py
"""
from __future__ import annotations

import json
import os

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                      # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = f"{ROOT}/outputs/wideband_energy.json"
OUT = f"{ROOT}/outputs/figures/ch1_f6_above_tip.png"

ELS = [0.0, -15.0, -30.0, -45.0, -60.0, -75.0]
ARMS = [("ours", "Ours (SBR+PO)", "tab:blue"),
        ("sionna", "PathSolver 11.1M", "tab:orange"),
        ("sionna_p250000000", "PathSolver 250M", "tab:green")]


def main() -> None:
    J = json.load(open(SRC, encoding="utf-8"))
    cells, meta = J["cells"], J["_meta"]
    nyq = float(meta["nyquist_hz"])
    ftip0 = float(meta["f_tip_el0_hz"])

    fig, ax = plt.subplots(2, 1, figsize=(11, 9))

    # ── (a) 상한이 어디에 그어지나 ─────────────────────────────────────────
    el = np.linspace(0, -90, 361)
    ft = ftip0 * np.cos(np.radians(el))
    ax[0].fill_between(el, ft, nyq, color="tab:red", alpha=0.10)
    ax[0].fill_between(el, 0, ft, color="tab:blue", alpha=0.18)
    ax[0].plot(el, ft, color="k", lw=2.0)
    ax[0].set_xlim(2, -92)
    ax[0].set_ylim(0, nyq)
    ax[0].set_xlabel("elevation [deg]")
    ax[0].set_ylabel("Doppler frequency [Hz]")
    ax[0].set_title("(a) Blade Doppler can only live under the tip-speed limit "
                    "f_tip(el) = f_tip(0) x cos(el)")
    ax[0].text(-45, nyq * 0.55, "energy here cannot be blade Doppler = artefact",
               fontsize=12, color="darkred", ha="center")
    ax[0].text(-11, ftip0 * 0.42, "blade band", fontsize=10, color="navy")
    ax[0].annotate("f_tip(el)", xy=(-30, ftip0 * np.cos(np.radians(30))),
                   xytext=(-24, ftip0 * 2.8), fontsize=10,
                   arrowprops=dict(arrowstyle="->", lw=1.1))
    ax[0].grid(alpha=0.3)

    # ── (b) 그 위에 얼마가 놓이나 ─────────────────────────────────────────
    x, w = np.arange(len(ELS)), 0.26
    for i, (arm, label, col) in enumerate(ARMS):
        v = [100.0 * cells[f"{arm}/el{e:+.0f}"]["above_f_tip_frac"] for e in ELS]
        b = ax[1].bar(x + (i - 1) * w, v, w, color=col, label=label)
        ax[1].bar_label(b, fmt="%.1f", fontsize=8, padding=1)
    ax[1].set_xticks(x)
    ax[1].set_xticklabels([f"{e:+.0f}" for e in ELS])
    ax[1].set_xlabel("elevation [deg]")
    ax[1].set_ylabel("energy above f_tip [% of total power]")
    ax[1].set_ylim(0, 100)
    ax[1].set_title("(b) Leakage above the limit, where the true value is 0 for every bar "
                    "- lower is better")
    ax[1].annotate("ours leaks most here", xy=(2 - w, 11.2), xytext=(2.05, 34),
                   fontsize=10, color="tab:blue",
                   arrowprops=dict(arrowstyle="->", color="tab:blue", lw=1.1))
    ax[1].grid(alpha=0.3, axis="y")
    ax[1].legend(fontsize=9)

    fig.tight_layout()
    fig.savefig(OUT, dpi=150)
    print(f"  wrote {OUT}")
    for arm, label, _ in ARMS:
        v = [100.0 * cells[f"{arm}/el{e:+.0f}"]["above_f_tip_frac"] for e in ELS]
        print(f"  {label:<20} min {min(v):6.2f} %  max {max(v):6.2f} %")


if __name__ == "__main__":
    main()
