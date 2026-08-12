# -*- coding: utf-8 -*-
"""figs_vol17_scope.py — 권 17 절 5(조각 88)의 **범위 그림** 한 장.

무엇을 그리나
    엔진 물리 스위치 비교가 **앙각 축에서 어디에 실제로 있는지**를 4 원장 × 7 앙각
    격자로 그린다. 칸의 상태는 셋이다.

        complete  그 앙각의 칸이 완결로 존재한다(n_missing = 0 · 칸이 원장에 있다)
        partial   칸은 있는데 부분 병합이거나 팔 하나가 비었다
        absent    그 앙각의 칸이 원장에 없다

    ⭐이 그림은 «무엇이 옳은가» 가 아니라 «어디까지 쟀는가» 를 그린다. 절 5 의 범위표가
      말로 하는 것을 한 눈에 보이게 하는 것이 전부다.

규약
    · 그림 안의 글자는 전부 영어(`assert_fig_text` 로 검사한다).
    · 색 + 무늬(해칭) **두 겹**으로 상태를 표시한다 — 색맹·흑백 인쇄에서도 갈린다.
    · 하이퍼파라미터(spp·PRF·자세 수)는 그림에 안 적는다. 본문 표가 적는다.

실행
    cd /home/yunjung/workspace/sionna2
    PYTHONPATH=src ~/.venvs/py312/bin/python src/figs_vol17_scope.py

⚠ GPU 안 쓴다. 원장 JSON 을 읽어 격자를 칠할 뿐이다.
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import matplotlib                                                    # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                      # noqa: E402
from matplotlib.patches import Rectangle                             # noqa: E402

from report_style import assert_fig_text                             # noqa: E402

OUT = os.path.join(_ROOT, "outputs", "figures", "ch17_scope_coverage.png")

ELS = [0.0, -15.0, -30.0, -45.0, -60.0, -75.0, -90.0]

#: 상태 → (면색, 테두리색, 해칭). 파랑/황갈/회색 — 색맹 대비 + 해칭으로 두 겹.
STATE = {
    "complete": ("#2f6fb0", "#1d4e7c", None),
    "partial":  ("#f0c060", "#9a7010", "///"),
    "absent":   ("#eef1f4", "#c2c9d0", None),
}


def _load(name: str) -> dict:
    with open(os.path.join(_ROOT, "outputs", name), encoding="utf-8") as f:
        return json.load(f)


def rows_from_ledgers() -> list[tuple[str, dict[float, str]]]:
    """원장 넷을 열어 «앙각 → 상태» 를 만든다. 손으로 적는 칸은 하나도 없다."""
    sweep = _load("elevation_sweep_md.json")["rows"]
    wide = _load("wideband_energy.json")["cells"]
    deck = _load("physics_vs_deck.json")
    diag_el = float(_load("diag_physics_paths_el-90.json")["_meta"]["el_deg"])

    # ① 스위치 단일축 분해 — 그 원장이 적은 앙각 한 자리만
    r1 = {e: ("complete" if e == diag_el else "absent") for e in ELS}

    # ② 물리 팔 마이크로도플러 스윕 — n_missing 이 상태를 정한다
    r2 = {e: "absent" for e in ELS}
    for r in sweep:
        if r["engine"] == "sionna_phys" and float(r["el_deg"]) in r2:
            r2[float(r["el_deg"])] = ("complete" if int(r["n_missing"]) == 0
                                      else "partial")

    # ③ 광대역 에너지 — 물리 팔 칸이 있는 앙각
    def _key(e: float) -> str:
        return f"sionna_phys/el{'+' if e >= 0 else '-'}{abs(int(e))}"
    r3 = {e: ("complete" if _key(e) in wide else "absent") for e in ELS}

    # ④ 덱 STFT 대조 — 칸이 있는 앙각이되, 물리 팔이 missing_arms 면 partial
    miss = set(deck["_meta"]["missing_arms"])
    have = {float(k.split("el")[-1]) for k in deck["cells"] if "el" in k}
    r4 = {}
    for e in ELS:
        if e not in have:
            r4[e] = "absent"
        else:
            tag = f"sionna_phys/el{int(e)}" if e < 0 else f"sionna_phys/el+{int(e)}"
            r4[e] = "partial" if tag in miss else "complete"

    return [("Switch decomposition", r1),
            ("Physics-arm sweep", r2),
            ("Wideband energy, physics arm", r3),
            ("Deck STFT cross-check", r4)]


def main() -> None:
    rows = rows_from_ledgers()
    title = "Where the physics-switch evidence exists"
    xlabel = "Elevation (deg)"
    tally = "complete of 7"
    labels = [n for n, _ in rows]
    assert_fig_text(title, xlabel, tally, *labels, *STATE.keys())

    fig, ax = plt.subplots(figsize=(9.2, 3.6), dpi=170)
    n = len(rows)
    for j, (name, states) in enumerate(rows):
        y = n - 1 - j
        for i, e in enumerate(ELS):
            fc, ec, hatch = STATE[states[e]]
            ax.add_patch(Rectangle((i + 0.06, y + 0.12), 0.88, 0.76,
                                   facecolor=fc, edgecolor=ec, linewidth=1.0,
                                   hatch=hatch))
        k = sum(1 for e in ELS if states[e] == "complete")
        ax.text(len(ELS) + 0.18, y + 0.5, f"{k} {tally}", va="center",
                ha="left", fontsize=9, color="#3a4149")

    ax.set_xlim(0, len(ELS) + 1.9)
    ax.set_ylim(0, n)
    ax.set_xticks([i + 0.5 for i in range(len(ELS))])
    ax.set_xticklabels([f"{int(e)}" for e in ELS], fontsize=10)
    ax.set_yticks([n - 1 - j + 0.5 for j in range(n)])
    ax.set_yticklabels(labels, fontsize=10)
    ax.set_xlabel(xlabel, fontsize=10)
    ax.set_title(title, fontsize=12, pad=10)
    for s in ("top", "right", "left", "bottom"):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0)

    handles = [Rectangle((0, 0), 1, 1, facecolor=f, edgecolor=e, hatch=h)
               for f, e, h in (STATE[k] for k in ("complete", "partial", "absent"))]
    ax.legend(handles, list(("complete", "partial", "absent")),
              loc="lower center", bbox_to_anchor=(0.5, -0.42), ncol=3,
              frameon=False, fontsize=9)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.tight_layout()
    fig.savefig(OUT, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"✅ {os.path.relpath(OUT, _ROOT)}")
    for name, st in rows:
        print("  ", name, {int(k): v for k, v in st.items()})


if __name__ == "__main__":
    main()
