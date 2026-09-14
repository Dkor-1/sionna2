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
    #: ── 2026-09-14(3) 적대 검증이 찾은 «꼬리 붙은» 모양 ──────────────────────
    #  ⛔틀이 토막 뒤에 아무것도 못 오게 해서 **발간물의 55 자리**가 그대로 샜다.
    #  ⭐⭐그중 가장 뼈아픈 것: 시험에는 「nan~nan %」만 있었는데, 생산 빌더가 실제로
    #    내는 것은 f"{min(rs):.1f}~{max(rs):.1f} %" 이고 min() 은 NaN 을 **왼쪽에** 놓는다
    #    — 곧 실제로 날 모양은 「nan~80.9 %」다. 되는 쪽만 시험에 담고 있었다.
    ("⭐생산 범위(왼쪽 nan)",     "| a | nan~80.9 % |",                            True),
    ("⭐생산 범위(오른쪽 nan)",   "| a | 12.3~nan % |",                            True),
    ("⭐꼬리 표시 기호",          "| a | nan dB ⛔ |",                              True),
    ("⭐화살표 뒤",              "| a | 13.06 → nan |",                           True),
    ("⭐화살표 앞",              "| a | nan → 12.2 |",                            True),
    ("⭐괄호 안 판 수",           "| a | 2.76e-05 dB (nan 판 @ 3500 MHz) |",        True),
    ("정상 범위",               "| a | 12.5~80.9 % |",                           False),
    ("정상 화살표",             "| a | 13.06 → 12.26 |",                          False),
]

#: ⚠**아직 막지 못하는 모양** — 숨기지 않고 적어 둔다.
#  「1272.9 · 759.9 · nan Hz ⚠갈린다」 는 꼬리 「갈린다」 3 자가 _TAIL_MAX 를 넘어 샌다.
#  꼬리를 4 자로 늘리면 「NaN 감지」·「비유한 값이 있다(NaN·무한)」 같은 **사유 문장**이
#  값으로 읽혀 발간이 막힌다 — 한글 두세 자 꼬리는 단위와 문장을 못 가른다.
#  ⇒ 그 자리는 글 검사로 못 닫는다. `benchmark/read_bandflat_0913.py` 의 그 칸을
#    `reader_gate.cell()` 로 옮겨 **수가 글이 되는 자리**에서 막았다(2026-09-14(3)).
#    여기 한 줄로 남겨, 다음에 틀을 만질 때 이 갈림을 다시 만나게 한다.
KNOWN_UNBLOCKED = [("꼬리가 긴 표시", "| a | 1272.9 · 759.9 · nan Hz ⚠갈린다 |")]

#: 세 판독기가 실제로 찍는 칸 서식을 비유한 수로 찍어 본 것 — 하나도 새면 안 된다.
PROD_FORMATS = ["nan dB", "nan dB (0 점)", "nan dB (3 판 @ 3500 MHz)", "nan~nan %",
                "nan %", "+nan %p", "+nan~+nan dB", "nan", "nan Hz",
                "nan · 501 Hz ⚠갈린다", "+nan dB", "+nan", "±nan Hz", "nan ms",
                "nan (+nan)", "— (+nan)", "inf dB", "-inf dB", "nan %p"]

#: 09-13(9) 에 실제로 «nan» 20 자리를 실어 발간했던 판. 그 20 자리를 지금도 잡아야 한다.
LEAK_COMMIT, LEAK_PATH, LEAK_N = "5db40e9b", "docs/WFSURVIVE_0912.md", 20

#: 지금 발간물 — 오탐이 하나도 없어야 한다.
LIVE = ["docs/WFSURVIVE_0912.md", "docs/SCENEPHYSICS_0913.md", "docs/BANDFLAT_0913.md",
        "docs/ALTITUDE_0914.md"]      # ⭐2026-09-14: 새 판독기의 문서가 빠져 있었다

#: ⭐**발간물의 표 칸에 든 수를 하나씩 nan 으로 바꿔** 관문이 잡나 본다 — 시험 줄이
#  «되는 쪽만» 담는 것을 막는 유일한 방법이다(2026-09-14(3) 신설).
def leak_sweep() -> tuple[int, int, list[str]]:
    import re as _re
    tot = miss = 0
    ex: list[str] = []
    num = _re.compile(r"(?<![\w.])[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?(?![\w.])")
    sep = _re.compile(r"^\|[\s:\-|]+\|$")
    for rel in LIVE:
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            continue
        lines = open(p, encoding="utf-8").read().splitlines()
        for i, ln in enumerate(lines):
            t = ln.strip()
            if not (t.startswith("|") and t.endswith("|")):
                continue
            #: ⛔표 **머리글**과 구분줄은 뺀다 — 거기 든 수는 계산값이 아니라 제목이다
            #  (「3.500 GHz 와의 모양 상관」·「1/h² 예측」). 자료 칸만 훑는다.
            if sep.match(t):
                continue
            nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
            if sep.match(nxt):
                continue
            for m in num.finditer(t):
                tot += 1
                spoiled = t[:m.start()] + "nan" + t[m.end():]
                if not _nonfinite_paths({"md": spoiled}):
                    miss += 1
                    if len(ex) < 5:
                        ex.append(f"{rel}: {spoiled[:76]}")
    return tot, miss, ex


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

    #: ⭐발간물 훑기 — 표 칸의 수를 하나씩 nan 으로 바꿔 잡나 본다.
    tot, miss, ex = leak_sweep()
    print(f"\n── 발간물 표 칸 훑기: 수 {tot} 자리 중 ⛔새는 자리 {miss}")
    for e in ex:
        print(f"     {e}")
    #: ⭐새는 자리가 **KNOWN_UNBLOCKED 에 적힌 모양뿐**이면 통과시킨다 — 그 자리는
    #  글 검사로 못 닫고, 수가 글이 되는 자리(`reader_gate.cell()`)에서 막았다.
    #  ⛔그 밖의 모양이 하나라도 새면 실패다. 이 갈림을 여기 남겨 둔다.
    unexplained = [e for e in ex if "⚠갈린다" not in e]
    if miss and (unexplained or miss > len(KNOWN_UNBLOCKED)):
        bad.append(("발간물 훑기(설명 안 되는 새는 자리)", len(unexplained) or miss, 0))
    elif miss:
        print(f"     ⚠새는 {miss} 자리는 전부 KNOWN_UNBLOCKED 의 모양이다 — 그 자리는 "
              "`reader_gate.cell()` 이 수가 글이 되는 자리에서 막는다.")

    print("── 아직 막지 못하는 모양(숨기지 않는다)")
    for name, md in KNOWN_UNBLOCKED:
        blocked = bool(_nonfinite_paths({"md": md}))
        print(f"     {'⚠여전히 샌다' if not blocked else '✅이제 막힌다'} {name}")

    if bad:
        print(f"\n⛔ 어긋난 줄 {len(bad)} — {bad}")
        return 1
    print(f"\n✅ 양방향 {len(CASES)} 줄 · 생산 서식 {len(PROD_FORMATS)} 가지 · "
          f"옛 유출 판 {LEAK_N} 자리 · 발간물 오탐 0 · 표 칸의 문 통과")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
