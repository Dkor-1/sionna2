# -*- coding: utf-8 -*-
"""fig_fairbudget_leak.py — 「예산을 맞추면 물리 스위치가 누설을 얼마나 움직이나」 한 장.

x 축 = 광선 예산 두 계단(11.1M · 250M), 막대 = 물리 스위치 끔/켬,
y 축 = 날개끝 상한 위로 새는 에너지 몫 [%]. 막대 위에 자세당 경로 중앙값을 적는다.
가로 파선은 우리 커널의 같은 값이다.

⛔GPU 를 쓰지 않는다. ⛔기존 그림·원장을 덮어쓰지 않는다(새 파일 하나만 만든다).
그림 안의 글자는 전부 영어(하우스 규약).

실행
    PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/fig_fairbudget_leak.py
"""
from __future__ import annotations

import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                       # noqa: E402
import numpy as np                                                    # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from report_style import assert_fig_text                              # noqa: E402

SRC = f"{ROOT}/outputs/wideband_energy_fairbudget.json"
OUT = f"{ROOT}/outputs/figures/fairbudget_leak.png"

#: (예산 이름, 물리 끔 팔, 물리 켬 팔)
LADDER = [("11.1M rays\n(rule value)", "sionna", "sionna_phys"),
          ("250M rays\n(matched budget)", "sionna_p250000000",
           "sionna_p250000000_phys")]
EL = "el+0"


def main() -> None:
    D = json.load(open(SRC, encoding="utf-8"))
    cells, rows = D["cells"], D["rows"]

    def leak(arm: str) -> float:
        return 100.0 * float(cells[f"{arm}/{EL}"]["above_f_tip_frac"])

    def paths(arm: str) -> int:
        return int(rows[f"{arm}/{EL}"]["npaths_median"])

    labels = [b for b, _, _ in LADDER]
    off = [leak(a) for _, a, _ in LADDER]
    on = [leak(a) for _, _, a in LADDER]
    noff = [paths(a) for _, a, _ in LADDER]
    non = [paths(a) for _, _, a in LADDER]
    ours = 100.0 * float(cells[f"ours/{EL}"]["above_f_tip_frac"])

    ttl = ("Energy above the blade-tip limit at el 0 deg — "
           "physics switch versus ray budget")
    ylab = "energy above f_tip  [% of total power]"
    lg_off = "physics OFF"
    lg_on = "physics ON (refraction + diffraction + edge + depth 3)"
    lg_ours = f"Ours (SBR+PO) = {ours:.1f} %"
    assert_fig_text(ttl, ylab, lg_off, lg_on, lg_ours, *labels)

    x = np.arange(len(LADDER))
    w = 0.30
    fig, ax = plt.subplots(figsize=(8.6, 5.6))
    b1 = ax.bar(x - 0.19, off, w, color="tab:orange", label=lg_off)
    b2 = ax.bar(x + 0.19, on, w, color="tab:red", label=lg_on)
    ax.axhline(ours, color="tab:blue", ls="--", lw=1.6, label=lg_ours)

    for bars, ns in ((b1, noff), (b2, non)):
        for r, n in zip(bars, ns):
            ax.text(r.get_x() + r.get_width() / 2, r.get_height() + 1.5,
                    f"{r.get_height():.1f} %\n{n} paths/pose", ha="center",
                    va="bottom", fontsize=9)

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel(ylab)
    ax.set_ylim(0, 104)
    ax.set_title(ttl, fontsize=11)
    ax.grid(alpha=0.3, axis="y")
    ax.legend(fontsize=9, loc="upper center", bbox_to_anchor=(0.5, -0.13),
              ncol=2, frameon=False)

    fig.tight_layout()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=150)
    print(f"  11.1M  off {off[0]:6.2f} %({noff[0]:3d} paths)  "
          f"on {on[0]:6.2f} %({non[0]:3d} paths)")
    print(f"  250M   off {off[1]:6.2f} %({noff[1]:3d} paths)  "
          f"on {on[1]:6.2f} %({non[1]:3d} paths)")
    print(f"  → {OUT}")


if __name__ == "__main__":
    main()
