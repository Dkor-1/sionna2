#!/usr/bin/env python
"""jobs_0915 — 설계 심사가 고른 첫 묶음.

2026-09-08 에 관점 넷이 독립으로 19 개를 설계하고 심사했다
(`work/sweep_0904/design_next_0908.json`). 그중 **GPU 를 쓰면서 값어치가 가장 큰 셋**을 산다.
나머지(사후 재조합·판독법·코드가 필요한 축)는 GPU 를 안 쓰거나 코드 선행이라 따로 간다.

■ A ⭐**우리 커널의 첫 실외** — 거울상 지면
  우리 SBR+PO 커널은 실외를 **한 번도 안 돌았다**(`_gnd` 샤드 0 개).
  까닭은 「지면 120 m 를 메쉬에 넣으면 격자점이 79,483 배」였는데, `sbr_field_ground`
  (거울상 3 항)는 **지면을 메쉬에 안 넣는다** — 격자는 그대로고 커널 호출만 셋이다.
  배선·이름표·가드가 다 끝나 있고(:458 · :615 · :671) 게이트 7 개도 통과했다.
  ⭐현세대 자유공간 짝이 **13 앙각 × 2 샤드로 이미 있다** — 대조군이 공짜다.
  ⭐실측: 우리 팔 한 샤드가 **3.1~3.4 분**이다(sionna 실외 팔은 2.1 시간 — 40 배 싸다).

  ⛔⛔**이 커널이 내는 것은 «표적이 겪는 지면 다중경로» 이지 «지면 자신의 되돌림» 이
    아니다.** 그래서 이 묶음은 「솔버가 정적 경로를 못 찾는다」(열린 물음 ①)에 답하지
    않는다. 결과 첫 줄에 이 구분을 적는다.

■ B **지면은 아래에서 보는 두 번째 눈인가**
  거울상 반사는 드론을 **아래에서** 비춘다 — 직접 시선이 동체에 가린 날개를 그 두 번째
  시선이 드러내나. 지금까지 가림은 **조명 하나**에서만 시험했다(`--body-scale`·`ours_free`).
  시선 갈림: el 0 에서 69.4° · −15 에서 53.1° · −30 에서 38.2°(r15 · 지면 20 m).
  ⚠`--body-scale` 은 가림뿐 아니라 위상·bbox 도 바꾼다 — 「가림이다」로 확정하지 않는다.

■ C **레이다-지면 높이를 붙들고 거리만 민다**
  지금까지 거리를 바꾸면 레이다 높이가 **늘 같이** 움직였다. h 를 고정하고 R 만 밀면
  「클러터 상수는 h 만의 함수라 서 있고 표적 몫만 1/R⁴ 로 준다」가 시험된다.
  ⭐`--ground-alt` 를 거리마다 맞춰 h 를 일정하게 만든다.

■ 규약
  · 전부 `--engine ours` 다 — 지금 도는 sionna 큐(0913·0914)와 축이 안 겹친다.
  · 자유공간 짝은 **새로 안 산다**(현세대 `ours_r15_n8192_mfix…_el*` 를 쓴다).
    ⚠B 의 `ours_free` 만 현세대 짝이 없어 함께 산다.
  · 자세 8,192(샤드 2) — 1,024 미만이면 빗살 잣대가 값을 안 낸다.
  · ⛔el 0° 는 사되 「레벨·폭」은 인용하지 않는다(GATES_0902).

쓰는 법
    cd /workspace/sionna
    CUDA_VISIBLE_DEVICES="" /workspace/.venvs/py312/bin/python runners/make_jobs_0915.py > runners/jobs_0915.txt
    CUDA_VISIBLE_DEVICES="" /workspace/.venvs/py312/bin/python runners/make_jobs_0915.py --summary
    발주 전 runners/filter_jobs.sh 로 NEW·DONE·STALE 을 가른다.
"""
from __future__ import annotations

import math
import sys

OUT, GROUPS = [], []
BASE = "--engine ours --n-poses 8192"


def sec(title: str) -> None:
    GROUPS.append((title, len(OUT)))
    OUT.append("")
    OUT.append(f"# ══ {title} ══")


def job(*, el, engine="ours", rng=15, ground="concrete", galt=20.0,
        body=0.0, nsh=2) -> None:
    """한 줄(샤드 나눔 포함). 문지기는 elevation_sweep_md.py 에도 있다."""
    #: ⛔레이다가 지면 아래로 가면 그 줄은 뜻이 없다 — 커널도 막지만 여기서 먼저 막는다
    if ground:
        depth = rng * math.sin(math.radians(abs(el)))
        if depth >= galt:
            raise SystemExit(f"⛔ 레이다가 땅속: r{rng} · el{el:g} → 깊이 {depth:.1f} m "
                             f"≥ 지면 높이 {galt:g} m")
    g = f" --ground {ground} --ground-alt {galt:g}" if ground else ""
    b = f" --body-scale {body:g}" if body else ""
    OUT.extend(f"--engine {engine} --n-poses 8192 --range-m {rng}{g}{b}"
               f" --els={el:g} --shard {k} --nshards {nsh}" for k in range(nsh))


# ══ A ══ 가장 큰 빈칸 — 앞에 둔다
sec("A ⭐우리 커널의 첫 실외 — 거울상 지면 (자유공간 짝은 이미 있다)")
for el in (0, -15, -30, -45, -60, -75, -90):
    job(el=el)

# ══ B ══
sec("B 지면은 아래에서 보는 두 번째 눈인가 — 가림을 세 갈래로 (⚠원인 확정 안 함)")
for el in (0, -15, -30):
    job(el=el, engine="ours_free")            # 동체 면만 뗀 대조군 · 실외
    job(el=el, engine="ours_free", ground="")  # 그 현세대 자유공간 짝(없다)
    job(el=el, body=0.4)                       # 동체를 줄인 판 · 실외

# ══ C ══
sec("C 레이다-지면 높이를 붙들고 거리만 민다 (h ≈ 12.5 m 고정 · el −30)")
#: h = galt − R·sin|el| 을 12.5 m 로 붙든다 ⇒ galt = 12.5 + R·sin30° = 12.5 + R/2
for rng in (15, 30, 60, 90):
    job(el=-30, rng=rng, galt=12.5 + rng / 2.0)

GROUPS.append(("끝", len(OUT)))
if "--summary" in sys.argv:
    n = sum(1 for x in OUT if x and not x.startswith("#"))
    print(f"발주 줄 {n} (샤드 나눔 포함)")
    for (t1, i1), (_t2, i2) in zip(GROUPS, GROUPS[1:]):
        c = sum(1 for x in OUT[i1:i2] if x and not x.startswith("#"))
        print(f"  {c:>3} 줄  {t1}")
    print(f"\n어림 GPU시간: {n * 0.06:.1f} (우리 팔 실측 3.1~3.4 분/샤드)")
else:
    print("\n".join(x for x in OUT if x is not None))
