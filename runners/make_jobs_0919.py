#!/usr/bin/env python
"""0919 발주서 — 2026-09-08 밤 설계판이 낸 것을 그대로 굽는다.

⛔발주서를 손으로 쓰지 않는다. 이 생성기가 원장(work/wf/queue_design_result.json)을 읽어
  줄을 내고, 샤드 나눔만 여기서 붙인다.

■ 어떻게 나왔나
  여섯 관점이 독립으로 27 묶음을 냈고, 묶음마다 「죽이려고」 반증했다 —
  ① 이미 답이 있나 ② 문지기에 걸리나 ③ 읽을 수 있나 ④ 상한에 붙나
  ⑤ 비용이 값어치를 넘나 ⑥ 손잡이가 실제로 있나.
  **27 중 21 이 죽고 6 이 살아남았다.** 죽은 것의 거의 전부가 ①「이미 샀다」였다.
  살아남은 것을 두 관점(값어치·시간)이 각각 하나의 발주서로 합쳤고, 여기서는
  **값어치 판(90 줄 · 어림 97 일꾼시간)** 을 굽는다.

■ ⛔모든 줄을 2 조각으로 나눈다
  이 줄들이 붙을 이웃 칸이 전부 --nshards 2 · 8,192 자세다. 다른 수로 나누면
  합칠 때 자세가 겹치거나 빈다. 생성기가 강제한다.

■ ⚠설계 원장이 함께 적어 둔 한계
  · 이 판은 「원인」을 정하지 않는다 — 손잡이와 원인은 일대일이 아니다.
  · 실기 계측 대조는 이 저장소에 0 건이다.
  · 확산은 모든 팔에서 켠 채다. 프로펠러 단독·뮌헨은 들어 있지 않다(확인함).

쓰는 법:
    /workspace/.venvs/py312/bin/python runners/make_jobs_0919.py --summary
    /workspace/.venvs/py312/bin/python runners/make_jobs_0919.py > runners/jobs_0919.txt
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = f"{ROOT}/work/wf/queue_design_result.json"
NSH = 2

with open(SRC, encoding="utf-8") as f:
    R = json.load(f)

#: 두 합침 안 가운데 **줄이 많은 쪽**(값어치 판)을 고른다
M = max(R["merged"], key=lambda x: len(x["queue_lines"]))
LINES = M["queue_lines"]
GROUPS = M["groups"]

#: ⛔규약 문지기 — 여기서 한 번 더 막는다(설계판이 지켰는지 믿지 않는다)
for ln in LINES:
    if "F0" in ln:
        raise SystemExit(f"⛔확산을 끈 팔이 들어 있다 — 발주 금지: {ln}")
    if "--parts prop" in ln:
        raise SystemExit(f"⛔프로펠러 단독은 더 이상 만들지 않는다: {ln}")
    if "munich" in ln:
        raise SystemExit(f"⛔뮌헨은 드론이 건물에 가려 결과가 아니다: {ln}")
    if "--shard" in ln or "--nshards" in ln:
        raise SystemExit(f"⛔줄에 샤드가 이미 붙어 있다 — 생성기가 붙인다: {ln}")

OUT = []
OUT.append("# ══ 0919 큐 — 2026-09-08 밤 설계판 (값어치 판) ══")
OUT.append(f"#  줄 {len(LINES)} × 샤드 {NSH} = {len(LINES) * NSH} 샤드 · 어림 {M['total_hours']} 일꾼시간")
OUT.append("#  ⭐여섯 관점이 27 묶음을 냈고 반증에서 21 이 죽었다(거의 전부 「이미 샀다」).")
OUT.append("#  ⛔이 판은 원인을 정하지 않는다 — 손잡이와 원인은 일대일이 아니다.")
OUT.append("#  ⛔실기 계측 대조는 0 건이다.")
OUT.append("#")
OUT.append("#  ── 묶음과 그 묶음이 답하지 **않는** 것 ──")
for g in GROUPS:
    OUT.append(f"#  ▸ {g['name']} ({g['n_lines']} 줄 · 어림 {g['cost_hours']} 시간)")
    OUT.append(f"#      물음  {g['question']}")
    OUT.append(f"#      죽는 조건  {g['kill_condition']}")
    if g.get("caveat"):
        OUT.append(f"#      ⛔안 답함  {g['caveat']}")
    OUT.append(f"#      읽는 법  {g.get('reads_how','')}")
OUT.append("#")
OUT.append("#  ── 차례를 왜 이렇게 짰나 ──")
for s in str(M["order_why"]).splitlines():
    OUT.append(f"#  {s}")
OUT.append("#")
OUT.append("#  ── 버린 것 ──")
for s in str(M["dropped"]).splitlines():
    OUT.append(f"#  {s}")
OUT.append("")

_SEEN = set()
for ln in LINES:
    for k in range(NSH):
        line = f"{ln} --shard {k} --nshards {NSH}"
        if line in _SEEN:
            OUT.append(f"#   ⤷ 건너뜀(이미 위에 있다): {line}")
            continue
        _SEEN.add(line)
        OUT.append(line)

if "--summary" in sys.argv:
    n = sum(1 for x in OUT if x and not x.startswith("#"))
    print(f"발주 줄 {n} (샤드 나눔 포함) · 조건 {len(LINES)} 개")
    print(f"어림 {M['total_hours']} 일꾼시간")
    for g in GROUPS:
        print(f"  {g['n_lines']:>3} 줄  {g['name']}")
else:
    print("\n".join(OUT))
