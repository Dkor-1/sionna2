# -*- coding: utf-8 -*-
"""
make_fig_captions_part10.py — 부 10 그림의 **영문 논문 캡션**을 문서로 남긴다
==========================================================================================
    PYTHONPATH=src /workspace/.venvs/py312/bin/python src/make_fig_captions_part10.py
    → docs/paper/figs_part10.md

왜 따로 있나
------------------------------------------------------------------------------------------
리포트 본문은 그림마다 **질문 캡션** 한 줄을 단다(하우스 규약). 논문에 그대로 붙일 **완결 문장
캡션**은 옛 `src/make_report05_results.py` 의 `figure_md(paper_caption=…)` 인자로만 있었고,
그 빌더가 편 11개로 쪼개지면서 본문에서 빠졌다. 사용자 지시가 «논문 작성 측면은 별도 메모» 이므로
본문으로 되돌리지 않고 **이 문서 하나에 모아 둔다** — 지우지 않기 위한 자리다.

⚠ `docs/paper/05_results.md` 의 「그림의 논문 캡션」 표가 채워지면 이 문서는 그쪽에 접고 지운다.
   그때까지 이 일곱 문장의 유일한 사본이 여기다.
"""
from __future__ import annotations

import os

from report_style import from_json

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

#: 캡션에 박히는 숫자는 손으로 치지 않는다 — 원장에서 읽어 f-string 으로 넣는다.
#: `outputs/report05_derived.json : rx_gain.excess_min_db` · `.excess_max_db`
_DV = from_json("outputs/report05_derived.json")
_EXC_MIN = float(_DV.get("rx_gain.excess_min_db"))
_EXC_MAX = float(_DV.get("rx_gain.excess_max_db"))

#: (편 번호, 앵커, 편 안의 그림 번호, PNG 이름, 영문 논문 캡션)
#: 출처 — `src/make_report05_results.py` 의 `figure_md(..., paper_caption=…)`
CAPTIONS = [
    ("57", "sensitivity-chain", 1, "report05_pf1_gap",
     "Per-band cost decomposition on one target and one geometry: only the wavelength "
     "term and the target cross section differ between the three illuminators, and the "
     "cross-section difference dominates 9 of 15 band pairs."),
    ("58", "shared-threshold", 1, "report05_pf6_detector",
     "Detection curves for the three always-on reference signals at an empirically "
     "calibrated false-alarm rate, and the sensitivity cost of restricting a receiver "
     "to always-on references."),
    ("59", "slope-anchor", 1, "report05_pf7_anchor",
     "The slope anchor applies one scalar per band and airframe, and the resulting band "
     "spread is compared with the size-transfer term the anchor leaves open."),
    ("60", "r90", 1, "report05_pf2_ranking",
     "Three-waveform comparison normalised per airframe: five airframes give three "
     "different orders at a single aspect and one common order on aspect-averaged, "
     "slope-anchored cross sections."),
    ("61", "rank-durability", 1, "report05_pf3_robust",
     "Ranking robustness: a common-mode cross-section error preserves the order at every "
     "offset within 10 dB and moves only the absolute range, while a per-band "
     "differential error reorders the waveforms above an airframe-specific threshold."),
    ("63", "cpi-residual", 1, "report05_pf4_cpi",
     "The 5G always-on-reference penalty as a CPI sweep: the blind-heading fraction falls "
     "with CPI under both guard conventions, and the CPI needed for parity with LTE or "
     "WiFi is bounded by the coherent-integration limit of the moving target."),
    # ⛔ 옛 캡션 「the measured excess comes from the N-independent cancellation
    #    residual」은 내렸다(2026-09-06) — 부호가 갈리는 값을 한 방향 사실로 눌러 적고
    #    원인까지 단정했다. 원장을 다시 세면 LTE 세 모드는 상한 위로 올라간 적이 없고,
    #    가장 낮은 값은 5G NR 모드다(`outputs/report05_derived.json : rx_gain.*` ·
    #    모드별 원본은 `outputs/detection_rx_sweep.json : modes.*.curves.*.snr50`).
    ("66", "rx-elements", 1, "report05_pf5_multirx",
     "Multi-receiver gain against the idealised coherent bound of 10 log10 N, which "
     "holds for thermal noise alone under perfect steering. Across the nine waveform "
     f"modes the measured gain departs from that bound by {_EXC_MIN:+.2f} to "
     f"{_EXC_MAX:+.2f} dB: the three LTE modes never rise above it, and the largest "
     "shortfall is a 5G NR mode. An N-independent cancellation residual would raise "
     "the gain above the bound in this way, but no controlled comparison here "
     "isolates that cause."),
]


def main() -> str:
    L = ["<!-- 생성물 — `src/make_fig_captions_part10.py` 가 쓴다. -->",
         "<!-- from: 옛 src/make_report05_results.py 의 figure_md(paper_caption=…) -->", "",
         "# 논문 조각 — 부 10 그림 캡션", "",
         "리포트 본문은 그림마다 **질문 캡션** 한 줄을 단다(하우스 규약). 논문에 그대로 붙일",
         "**완결 문장 캡션**은 본문에서 빠지므로 여기 모은다.", ""]
    for no, anchor, k, stem, cap in CAPTIONS:
        png = f"outputs/figures/{stem}.png"
        if not os.path.exists(os.path.join(_ROOT, png)):
            raise SystemExit(f"그림 파일이 없다: {png}")
        L += [f"<!-- from: 편 {no} {anchor} · 그림 {k} · {png} -->",
              f"**Fig. ({no}-{k})** {cap}", ""]
    p = os.path.join(_ROOT, "docs", "paper", "figs_part10.md")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print(f"✅ {os.path.relpath(p, _ROOT)} — 캡션 {len(CAPTIONS)}개")
    return p


if __name__ == "__main__":
    main()
