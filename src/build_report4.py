# -*- coding: utf-8 -*-
"""build_report4.py — report4 (탐지·추적 벤치마크를 위한 신호처리 체인 검증) 산출물 생성.

**이 리포트는 벤치마크를 돌리지 않는다.** 벤치마크를 *믿을 수 있게* 만든다:
6개 검증실험(E1..E6)의 JSON 을 읽어 그림 7장 + 노트북을 만든다.

⚠ 측정 자체는 여기서 하지 않는다. 측정 스크립트가 JSON 을 남기고, 이 스크립트는 **읽기만** 한다.
   (그래야 그림과 글이 어긋날 수 없다.)

필요한 JSON (없으면 어떤 스크립트를 돌려야 하는지 알려준다):
    outputs/verify_cfar.json          benchmark/verify_cfar.py          [E1]
    outputs/verify_eca.json           benchmark/verify_eca.py           [E2]
    outputs/verify_ambiguity.json     benchmark/verify_ambiguity.py     [E3]
    outputs/verify_linkbudget.json    benchmark/verify_linkbudget.py    [E4]
    outputs/verify_observability.json benchmark/verify_observability.py [E5]
    outputs/verify_ghost_impact.json  benchmark/verify_ghost_impact.py  [E6]
    outputs/report4_fixups.json       benchmark/report4_fixups.py       ← 적대적 검증의 **정정값**

실행:  python src/build_report4.py            (그림 7장 + 노트북)
       python src/build_report4.py --figs     (그림만)
       python src/build_report4.py --nb       (노트북만)
"""
import argparse
import os
import subprocess
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (_HERE, os.path.join(_ROOT, "benchmark")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

NEEDED = [
    ("verify_cfar.json", "benchmark/verify_cfar.py", "[E1] CFAR 오경보율 교정"),
    ("verify_eca.json", "benchmark/verify_eca.py", "[E2] ECA 상쇄깊이·저속표적 손실"),
    ("verify_ambiguity.json", "benchmark/verify_ambiguity.py", "[E3] 모호함수"),
    ("verify_linkbudget.json", "benchmark/verify_linkbudget.py", "[E4] 링크버짓 → RD SNR"),
    ("verify_observability.json", "benchmark/verify_observability.py", "[E5] 관측가능성"),
    ("verify_ghost_impact.json", "benchmark/verify_ghost_impact.py", "[E6] 바닥 유령"),
    ("report4_fixups.json", "benchmark/report4_fixups.py", "⭐ 적대적 검증의 정정값"),
]


def check_inputs():
    missing = [(f, s, w) for f, s, w in NEEDED
               if not os.path.exists(os.path.join(_ROOT, "outputs", f))]
    if missing:
        print("❌ 측정 JSON 이 없다. 먼저 아래를 돌려라:\n")
        for f, s, w in missing:
            print(f"   ~/.venvs/py312/bin/python {s:40s}  # {w}  → outputs/{f}")
        sys.exit(1)
    print("✔ 측정 JSON 7종 확인 — 본문 숫자는 전부 여기서 읽는다 (하드코딩 없음)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--figs", action="store_true", help="그림만")
    ap.add_argument("--nb", action="store_true", help="노트북만")
    a = ap.parse_args()
    t0 = time.time()
    both = not (a.figs or a.nb)

    print("=" * 72)
    print("▶ report4 — 탐지·추적 벤치마크를 위한 신호처리 체인 검증")
    print("   질문: 벤치마크를 돌리기 전에, 우리 검출기가 교정돼 있는가?")
    print("=" * 72)
    check_inputs()

    if both or a.figs:
        print("\n" + "=" * 72, "\n▶ 그림 7장 (전부 JSON 에서 읽어 그린다)\n", "=" * 72)
        import viz_report4 as V
        V.build_all()

    if both or a.nb:
        print("\n" + "=" * 72, "\n▶ report4.ipynb\n", "=" * 72)
        subprocess.run([sys.executable, os.path.join(_HERE, "make_notebook4.py")], check=True)

    # 판정 요약 — 그림/노트북과 **같은 소스**(viz_report4.VERDICT)에서 센다
    from viz_report4 import VERDICT
    npass = sum(1 for v in VERDICT if v[2] == "PASS")
    nfail = sum(1 for v in VERDICT if v[2] == "FAIL")
    ncond = sum(1 for v in VERDICT if v[2] == "COND")
    print("\n" + "=" * 72)
    print(f"  판정: {npass} PASS / {ncond} 조건부 / {nfail} FAIL")
    print("  → 벤치마크가 불가능하다는 뜻이 아니라, 지금 명세 그대로 돌리면")
    print("    방어할 수 없는 숫자가 나온다는 뜻이다. 처방은 노트북 §8.")
    print("=" * 72)
    print(f"\n✅ report4 완료 ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
