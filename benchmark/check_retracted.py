# -*- coding: utf-8 -*-
"""
check_retracted.py — **철회한 수가 다시 인용되고 있지 않은가**
==========================================================================================
왜 이 관문이 필요한가
    이 저장소는 정정을 아주 잘 적는다 — `docs/RETRACTION_LOG.md` 는 파일 이름과 줄 번호까지
    지목한다. 그런데 실제로 고쳐지는 것은 «본문 아래쪽 한 자리» 뿐이고, 머리·제목·표·원장
    json·HTML 은 그대로 남는다. 2026-09-04 전수조사에서 나온 30 건 중 **17 건이 이 모양**
    이었고, 그중 셋은 **같은 문단 안에서 자기 자신과 어긋났다**.

    ⇒ 정정의 «작용 범위» 를 사람의 기억이 정하고 있었다. 그것을 기계가 정하게 한다.

무엇을 하나
    아래 `RETRACTED` 표(철회된 문자열 · 예외 허용 경로 · 사유)를 저장소 전체에 대고 훑는다.
    `docs/RETRACTION_LOG.md` 자신과 `archive/` 는 기록이라 봐준다. 그 밖에서 나오면 실패다.
    ⭐**철회 문장을 «인용» 이 아니라 «철회한다» 고 적는 자리는 통과시킨다** — 같은 줄에
    ⛔·철회·무효화·인용 금지 중 하나가 있으면 그 줄은 표시가 붙은 것으로 본다.

⛔이 관문은 판정하지 않는다 — 표에 적힌 것만 본다. 새 철회를 적을 때 이 표에도 한 줄 넣는다.

실행
    cd /workspace/sionna
    CUDA_VISIBLE_DEVICES="" PYTHONPATH=src:benchmark python benchmark/check_retracted.py
        --all   맞은 줄을 전부 인쇄한다(기본은 파일마다 3 줄까지)
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

#: 표시가 붙은 줄로 보는 표식 — 이 중 하나가 같은 줄에 있으면 «철회를 적는 자리» 다.
MARKS = ("⛔", "철회", "무효화", "인용 금지", "인용하지 않는다", "옛 기록", "옛 판", "RETRACTED")

#: ⭐**발행면만 훑는다.** 분석 스크립트와 원시 원장(공격·감사 산출물)은 그 수를 «주제»
#  로 다루는 것이 정상이라 여기 넣지 않는다 — 문제는 정정이 **읽는 사람이 보는 면**에
#  안 닿는 것이었다. 발행면은 사람이 읽으라고 내놓은 것 전부다.
SCAN_ROOTS = ("reports", "docs", "atlas", "README.md", "CLAUDE.md")
#: 훑지 않는 곳 — 기록 자체이거나 사람 손이 닿지 않는 곳.
SKIP_DIRS = {".git", "__pycache__", ".ipynb_checkpoints", "archive", "node_modules",
             "elev_sweep_shards", ".venvs", "refs", "papers_isac_sionna", "paper"}
#: 감사·적대검증 문서는 철회할 수를 **주제로** 다룬다 — 그 안에서는 인용이 정상이다.
SKIP_FILES = {"docs/RETRACTION_LOG.md", "benchmark/check_retracted.py",
              "docs/AUDIT_REPORTS_0901.md", "docs/REPORTS_ADVERSARIAL_0810.md"}
EXTS = (".md", ".py", ".json", ".html", ".ipynb", ".txt")

#: (정규식, 사유, 예외 허용 경로들)
RETRACTED: list[tuple[str, str, tuple[str, ...]]] = [
    (r"23\.17\s*dB|23\.2\s*dB",
     "R14 — φ 스윕. 그 수는 φ 가 아니라 스윕하지 않은 고도차 Δz=35 m 의 성질이고 "
     "R90 동작점에서는 ≤1.20 dB 다. φ=90° 가 세 팔 모두 최소",
     ("outputs/fix_phi.json", "outputs/geometry_grid_axis_review.json",
      "outputs/geometry_grid_fairness_audit.json", "docs/GEOMETRY_BENCHMARK.md")),

    (r"49\.02\b",
     "리포트 02-2 · 조각 06 — 정반사 채널과 확산 채널의 계단을 한 사슬로 더한 값. "
     "형상 판정을 통과하는 구간에서 사는 것은 2→1 의 −6.05 dB 하나다",
     ("outputs/facet_count.json",)),

    (r"0\.6903",
     "2026-08-16 — sionna_phys el −15° 행. 자세 4,096 개 중 #3195 하나가 요동 전력의 "
     "91.6 % 를 쥔 튐 칸이다. ⇒ 그 행 인용 금지",
     ("outputs/physics_vs_deck.json", "outputs/outlier_recheck_0816.json")),

    (r"86\.6\s*(?:→|->)\s*32\.4",
     "2026-08-16 ③ — 8,192 자세 중 #3399 한 개 탓. 그 자세를 빼면 85.52 대 85.24 % 로 일치",
     ("outputs/switch_factorial.json", "outputs/depth_axis_verdict_0816.json")),

    (r"판독\s*(?:거리가\s*)?47\s*m|47\s*m\s*밖에\s*못\s*읽",
     "2026-08-16 (2) — 정당한 선택 네 가지로 다시 재면 47/280/40/56 m 로 40~280 m(7 배)이고 "
     "30·60 m 칸에서 판정이 뒤집힌다",
     ()),

    (r"p99\s*15\.2",
     "RHO_IS_SMOOTHNESS — 남의 구현으로 낸 영분포를 이 구현에 갖다 썼다. "
     "정본 바닥은 p99 ≈ 8.4 · 2,000 판 최대 9.6",
     ()),

    (r"0\.175\s*[~-]\s*0\.315",
     "MATERIAL_CORRECTION §6 — 0.175 는 인용에서 뺀다. 그리고 그 구간은 1.8~18.2 GHz "
     "전대역 적합이라 6 GHz 위 우리 적합과 나란히 놓을 수 없다",
     ()),

    (r"프레넬[^\n]{0,40}23\s*배|23\s*배로\s*감당",
     "리포트 12 절 3 — 조각을 자기 원점에 홀로 놓았을 때의 값이다. 드론에 합치면 "
     "1,388 배(el −30°) · 1,279 배(el −60°)",
     ()),

    (r"아무도\s*(?:이\s*)?[^\n]{0,20}한\s*적이\s*없|우리가\s*처음\s*낸다|아무도\s*안\s*한",
     "R12 — 코퍼스 안의 미발견을 문헌의 부재로 말했다. 「보유 아카이브 218편 안에서 "
     "찾지 못했다」로만 쓴다",
     ()),

    (r"실측\s*논문은\s*Pfa\s*통제가\s*불가능",
     "2026-09-04 — 한 코퍼스의 낱말 세기에서 원리 주장으로 도약했다. 살아남는 말은 "
     "「통제된 Pfa 위의 조명원 비교는 시뮬 쪽이 값싸다」",
     ()),

    (r"리듬\s*90\s*%|리듬이\s*90\s*%",
     "R29 — 창 반폭 hw 2/8/32 Hz 로 같은 데이터가 9.9/63.4/90.0 % 로 움직인다. "
     "리듬 몫의 크기는 인용하지 않고 순서만 읽는다",
     ()),

    (r"벌\s*수\s*N|몇\s*벌인지",
     "2026-09-03 사용자 지시 — 지어낸 말이다. 「같은 줄이 적히는 횟수」로 푼다",
     ()),
]

_COMPILED = [(re.compile(p), why, ex) for p, why, ex in RETRACTED]


#: 표식은 **같은 문단** 안에서만 인정한다 — 문단은 «빈 줄로 끊긴 덩어리» 다.
#  ⛔고정 줄수 창(±10)은 쓰지 않는다. 시험해 보니 ⛔가 잦은 문서에서는 아무 데나 새 인용을
#  붙여도 통과했다(되돌림을 심었더니 exit 0 이 나왔다) — 창을 쓰면 관문이 조용히 잠든다.
#  ⛔같은 줄만 보는 것도 아니다. 정정문은 두세 줄에 걸치는 것이 보통이라 그러면 정정문
#  자신이 전부 걸린다. 문단이 딱 맞는 크기다.
def blocks(lines: list) -> list:
    """줄 번호(1-based) → 그 줄이 속한 문단의 글자. 빈 줄이 문단을 끊는다."""
    out, cur, mem = {}, [], []
    for i, ln in enumerate(lines, 1):
        if ln.strip() in ("", '"\n",', '""'):
            for j in mem:
                out[j] = "\n".join(cur)
            cur, mem = [], []
        else:
            cur.append(ln)
            mem.append(i)
    for j in mem:
        out[j] = "\n".join(cur)
    return out


def marked(block: str) -> bool:
    return any(m in block for m in MARKS)


#: `| [^12] | outputs/x.json | key | 값 |` 꼴은 **각주 출처 표**다 — 그 수가 어디서 왔는지
#  기계가 찍는 자리라, 철회를 적는 문장도 자기 각주를 이 표에 갖는다. 주장이 아니다.
_CITE_ROW = re.compile(r'^\s*"?\|\s*\[\^\d+\]\s*\|')


def scan() -> list[tuple[str, int, str, str]]:
    hits: list[tuple[str, int, str, str]] = []
    walk_roots = []
    for r in SCAN_ROOTS:
        p_ = os.path.join(ROOT, r)
        if os.path.isfile(p_):
            walk_roots.append((os.path.dirname(p_), [], [os.path.basename(p_)]))
        elif os.path.isdir(p_):
            walk_roots.extend(os.walk(p_))
    for dp, dns, fns in walk_roots:
        dns[:] = [d for d in dns if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in fns:
            if not fn.endswith(EXTS):
                continue
            rel = os.path.relpath(os.path.join(dp, fn), ROOT)
            if rel in SKIP_FILES:
                continue
            try:
                with open(os.path.join(dp, fn), encoding="utf-8") as f:
                    lines = f.read().split("\n")
            except (UnicodeDecodeError, OSError):
                continue
            blk = blocks(lines)
            for rx, why, ex in _COMPILED:
                if rel in ex:
                    continue
                for i, ln in enumerate(lines, 1):
                    if rx.search(ln) and not marked(blk.get(i, ln)) \
                            and not _CITE_ROW.match(ln):
                        hits.append((rel, i, why, ln.strip()[:150]))
    return hits


def main() -> int:
    show_all = "--all" in sys.argv
    hits = scan()
    print("── 철회한 수가 다시 인용되고 있는가 ──")
    print(f"  철회 항목 {len(RETRACTED)}개 · 표시 없이 인용된 자리 {len(hits)}건\n")
    if not hits:
        print("✅ 철회한 수가 표시 없이 인용된 자리가 없다")
        return 0
    by: dict[str, list] = {}
    for rel, i, why, ln in hits:
        by.setdefault(rel, []).append((i, why, ln))
    for rel in sorted(by):
        rows = by[rel]
        print(f"⛔ {rel}  ({len(rows)}건)")
        for i, why, ln in (rows if show_all else rows[:3]):
            print(f"   :{i}  {ln}")
            print(f"        ↳ {why}")
        if not show_all and len(rows) > 3:
            print(f"   … 외 {len(rows) - 3}건 (`--all`)")
    print(f"\n⛔ {len(hits)}건 — 그 자리에 ⛔철회 표시를 달거나 값을 정본으로 갈아라.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
