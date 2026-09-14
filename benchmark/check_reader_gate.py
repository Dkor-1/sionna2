#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""발간 관문이 **무엇을 막고 무엇을 통과시키나** — 상시 시험 (2026-09-14).

    CUDA_VISIBLE_DEVICES="" taskset -c 8-11 \
      /workspace/.venvs/py312/bin/python benchmark/check_reader_gate.py

왜 있나
-------
`src/reader_gate.py` 의 글 검사는 **글자를 세는 일**이라, 표기가 하나 늘 때마다 구멍이
난다. 2026-09-13~14 에 같은 자리를 **네 번** 고쳤고, 그때마다 고친 판이 다른 쪽으로
샜다(전부 실측):

| 판 | 막아야 하는데 샌 것 | 통과해야 하는데 막힌 것 |
|---|---|---|
| 09-13(9) 없음 | 표 칸의 `nan` 20 자리가 그대로 발간됐다 | — |
| 09-13(10) 낱말 검사 | — | 건너뜀 사유 한 줄이 **발간 전체**를 막았다 |
| 09-13(10) 값 자리 | 섞인 칸 「띠 안 nan · -6.0 dB」 | — |
| 09-13(10) 토막 검사 | `h1 nan` · `**nan**` · `` `nan` `` · 전각 | 저자 이름 「P. V. Brennan」 |

⇒ 고칠 때마다 양쪽을 **같이** 재지 않으면 되풀이된다. 이 파일이 그 표다.
⛔여기 줄을 지우지 않는다 — 줄마다 실제로 난 사고가 있다.

⭐진짜 방벽은 글 검사가 아니라 `reader_gate.cell()` 이다. 수가 글로 바뀌는 **그 자리**에
  문을 두면 「JSON 은 null 인데 글에만 수가 찍히는」 갈래가 구조적으로 없어진다.
  글 검사는 그 뒤를 받는 보조다.
"""
from __future__ import annotations

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
from reader_gate import _nonfinite_paths, cell   # noqa: E402

#: (이름, 글, 막아야 하나). ⛔⭐가 붙은 줄은 **실제로 났던 사고**다.
CASES = [
    ("표 칸 단독 nan",          "| a | nan |",                                  True),
    ("⭐섞인 칸",                "| a | 띠 안 nan · -6.0 dB |",                  True),
    ("값과 섞임",               "| a | 1017.7 · nan |",                         True),
    ("괄호 안",                 "| a | 12.3 (nan) |",                           True),
    ("단위 붙은 둘",            "| a | nan Hz · nan dB |",                      True),
    ("실제 표 모양",            "| ours | f_tip 1272.9 · 띠 안 nan ( -6.0 dB) |", True),
    ("긴 이름표",               "| a | 띠 안 최강선 nan Hz |",                   True),
    ("⭐숫자 이름표 h1",         "| a | h1 nan |",                               True),
    ("⭐숫자 이름표 b3",         "| a | b3 nan |",                               True),
    ("⭐굵게",                   "| a | **nan** |",                              True),
    ("기울임",                  "| a | *nan* |",                                True),
    ("⭐코드 서식",              "| a | `nan` |",                                True),
    ("HTML 태그",               "| a | <b>nan</b> |",                           True),
    ("⭐전각",                   "| a | \uff4e\uff41\uff4e |",                      True),
    ("따옴표",                  '| a | "nan" |',                                True),
    ("-inf dB",                 "| a | 최강선 -inf dB |",                        True),
    ("범위 표기",               "| a | nan~nan % |",                            True),
    ("글 전체가 값",            "-inf",                                          True),
    ("표 밖 문장",              "NaN 을 null 로 바꿀 것(das_fig3b)",             False),
    ("영문 문장",               "converges to plane-wave sigma as R->inf.",      False),
    ("표 안 긴 문장",           "| 근거 | anchor_subband.json 의 NaN 을 null 로 바꿀 것 |", False),
    ("⭐표 안 건너뜀 사유",      "| 까닭 | 비유한 값이 4 자세에 있다(NaN·무한) |", False),
    ("⭐짧은 건너뜀 사유",       "| 까닭 | 비유한 값이 있다(NaN·무한) |",          False),
    ("⭐저자 이름",              "P. V. Brennan",                                 False),
    ("⭐저자 이름(표)",          "| 저자 | P. V. Brennan |",                       False),
    ("⭐필드 이름",              "second_prf_nan",                                False),
    ("⭐NaN 감지",               "NaN 감지",                                      False),
    ("⭐NaN 때문에 제외했다",    "NaN 때문에 제외했다",                            False),
    ("NaN detected",            "NaN detected",                                  False),
    ("정상 표",                 "| ours | f_tip 1272.9 · 띠 안 380.3 ( -6.0 dB) |", False),
    ("정상 «없음»",             "| ours | 띠 안 없음 · 접힘 True |",             False),
    ("정상 «—»",                "| a | — |",                                     False),
    ("정상 null·None",          "| a | null · None |",                           False),
]

#: 세 판독기가 실제로 찍는 칸 서식을 비유한 수로 찍어 본 것 — 하나도 새면 안 된다.
PROD_FORMATS = ["nan dB", "nan dB (0 점)", "nan dB (3 판 @ 3500 MHz)", "nan~nan %",
                "nan %", "+nan %p", "+nan~+nan dB", "nan", "nan Hz",
                "nan · 501 Hz ⚠갈린다", "+nan dB", "+nan", "±nan Hz", "nan ms",
                "nan (+nan)", "— (+nan)", "inf dB", "-inf dB", "nan %p"]

#: 09-13(9) 에 실제로 «nan» 20 자리를 실어 발간했던 판. 그 20 자리를 지금도 잡아야 한다.
LEAK_COMMIT, LEAK_PATH, LEAK_N = "5db40e9b", "docs/WFSURVIVE_0912.md", 20

#: 지금 발간물 — 오탐이 하나도 없어야 한다.
LIVE = ["docs/WFSURVIVE_0912.md", "docs/SCENEPHYSICS_0913.md", "docs/BANDFLAT_0913.md"]


def main() -> int:
    bad = []
    print("═══ 발간 관문 양방향 시험 ═══")
    for name, txt, want in CASES:
        got = bool(_nonfinite_paths({"md": txt}))
        if got != want:
            bad.append((name, got, want))
        print(f"  {'✅' if got == want else '⛔'} {name:<22s} 막나={got!s:<5s} (바람 {want})")
    n_real = len(_nonfinite_paths({"x": float("nan")}))
    if n_real != 1:
        bad.append(("진짜 비유한 수", n_real, 1))
    print(f"  {'✅' if n_real == 1 else '⛔'} 구조화된 진짜 비유한 수 {n_real} 자리")

    leak = [f for f in PROD_FORMATS if not _nonfinite_paths({"md": f"| a | {f} |"})]
    print(f"\n── 생산 서식 {len(PROD_FORMATS) - len(leak)}/{len(PROD_FORMATS)} 막힘"
          + (f" · ⛔새는 것 {leak}" if leak else ""))
    if leak:
        bad.append(("생산 서식", len(leak), 0))

    try:
        old = subprocess.run(["git", "show", f"{LEAK_COMMIT}:{LEAK_PATH}"],
                             capture_output=True, text=True, cwd=ROOT).stdout
    except Exception:
        old = ""
    if old:
        n = len(_nonfinite_paths({"md": old}))
        print(f"── 옛 유출 판({LEAK_COMMIT}) 에서 잡은 자리 {n} (기대 {LEAK_N})")
        if n != LEAK_N:
            bad.append(("옛 유출 판", n, LEAK_N))

    for f in LIVE:
        p = os.path.join(ROOT, f)
        if not os.path.exists(p):
            continue
        n = len(_nonfinite_paths({"md": open(p, encoding="utf-8").read()}))
        print(f"── 발간물 {f}: 오탐 {n}")
        if n:
            bad.append((f, n, 0))

    #: cell() — 진짜 방벽
    print("\n── 표 칸의 문 cell()")
    checks = [(cell(None), "없음"), (cell(1.5, ".2f", " dB"), "1.50 dB"),
              (cell(0.0, ".3f"), "0.000"), (cell(-2, "+.1f", " %p"), "-2.0 %p")]
    for got, want in checks:
        ok = got == want
        bad += [] if ok else [("cell()", got, want)]
        print(f"  {'✅' if ok else '⛔'} {got!r} == {want!r}")
    for v in (float("nan"), float("inf"), float("-inf")):
        try:
            cell(v, ".2f", " dB")
            bad.append(("cell() 비유한", v, "멈춰야 한다"))
            print(f"  ⛔ cell({v}) 가 안 멈췄다")
        except ValueError:
            print(f"  ✅ cell({v}) 가 멈춘다")

    if bad:
        print(f"\n⛔ 어긋난 줄 {len(bad)} — {bad}")
        return 1
    print(f"\n✅ 양방향 {len(CASES)} 줄 · 생산 서식 {len(PROD_FORMATS)} 가지 · "
          f"옛 유출 판 {LEAK_N} 자리 · 발간물 오탐 0 · 표 칸의 문 통과")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
