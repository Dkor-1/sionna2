#!/usr/bin/env python
"""jobs_0914 — **우리 실외 씬이 왜 깨지는지** 가르는 발주서.

■ 무엇을 쫓나
  우리가 만든 실외 씬 `outdoor01` 에서, 레이다가 제 지면을 보고 돌려보내는 몫이
  **로터 각도를 모르는 상수**인데(자세에 대한 변동 −74 dB) 8,192 자세 중 약 1 % 에서
  그 상수가 **70 dB 사라진다**. 상쇄가 아니라 없어진다 — 그 자세에서 실외 기록이
  빈 하늘 기록과 같아진다(복소 상대차 0.14). 되풀이해도 **똑같은 자세**다(자카드 1.0000).
  자세한 수는 `outputs/outdoor_dip_origin_0908.json`.

■ ⛔이미 죽인 가설 (다시 사지 않는다)
  · 재질이 거울이라서 — 기본 씬(뮌헨·거리 협곡)도 전부 S=0.0 이다
  · 면이 적어서 — 거리 협곡도 삼각형 74 개로 우리와 같다
  · 지면이 삼각형 둘짜리 큰 평판이라서 — 세 씬 모두 그렇고 우리 것이 가장 작다
  · 대각선 이음매 — 방위 45°(정반사점이 이음매 위)에서 오히려 낙차 1 개
  · 드론 고도 — 10·40 m 로도 안 꺼진다
  · 경로 상한 — n_trunc=0 이고 경로가 2,825 개뿐이다(상한 2,000,000)
  · 날개가 가려서 — 자세 번호를 박자 주기로 접은 집중도가 0.185 뿐이다
  ⭐한 가지는 **끈다** — 지면 거칠기 0.3 이상이면 사라진다. 다만 그것이 «우리 씬 대
    남의 씬» 을 설명하지는 못한다(양쪽 다 거울이니까).

■ 이 발주가 가르려는 것 (묶음마다 물음 하나)
  A **드론 메쉬가 방아쇠인가** — 기체를 바꾼다. phantom4 는 «되풀이된 도달» 이 0 % 인
    기체라 대조로 특히 좋다. 기체를 바꿔도 나면 드론 메쉬 탓이 아니다.
  B **탐색 문제인가** — 광선 예산을 40 분의 1 로 줄이고 10 분의 1 로 줄여 본다.
    낙차 수가 예산을 따라가면 «경로를 못 찾는 것» 이고, 안 따라가면 다른 것이다.
  C **어느 차수의 경로인가** — 반사 깊이 1 과 3. 깊이 1 은 한 번 튀는 경로만이다.
    깊이 1 에서도 나면 «지면 한 번 튀는 경로» 하나가 사라지는 것이다.
  D **드론 크기가 방아쇠인가** — 동체를 반으로/두 배로. 크기를 따라가면 가림·그림자다.
  E **거칠기가 다른 앙각에서도 끄나** — el −30 에서만 확인했다. el −60 에서 다시 본다.

■ 규약
  · ⭐전부 **지면만**(`--env outdoor01_ground`)이다 — 건물은 이 현상을 안 만든다(쪼갠 칸 6/6).
  · ⭐앙각은 **−60°** 로 고정한다. 그 칸이 빈 하늘 낙차 0 개라 대조가 가장 깨끗하다.
  · 확산(F)은 늘 켠다. 팔은 R0D0E0F1(확산만) 하나로 고정 — 축을 하나만 흔든다.
  · ⛔자유공간 짝은 **새로 안 산다** — el −60 빈 하늘 판이 이미 있다.
    ⚠다만 기체·크기를 바꾼 묶음은 빈 하늘 짝이 없으므로 함께 산다.

쓰는 법
    cd /workspace/sionna
    CUDA_VISIBLE_DEVICES="" /workspace/.venvs/py312/bin/python runners/make_jobs_0914.py > runners/jobs_0914.txt
    CUDA_VISIBLE_DEVICES="" /workspace/.venvs/py312/bin/python runners/make_jobs_0914.py --summary
    발주 전 runners/filter_jobs.sh 로 NEW·DONE·STALE 을 가른다.
"""
from __future__ import annotations

import re
import sys

BASE = "--engine sionna --spp 4000000000 --n-poses 8192 --max-depth 2 --range-m 15"
EL = -60
OUT, GROUPS = [], []


def sec(title: str) -> None:
    GROUPS.append((title, len(OUT)))
    OUT.append("")
    OUT.append(f"# ══ {title} ══")


def job(*, arm="R0D0E0F1", el=EL, env="outdoor01_ground", spp=0, depth=2,
        drone="", body=0.0, scat=-1.0, nsh=2) -> None:
    """한 줄(샤드 나눔 포함). 문지기는 benchmark/elevation_sweep_md.py 에도 있다."""
    m = re.fullmatch(r"R([01])D([01])E([01])F([01])", arm)
    if not m:
        raise SystemExit(f"⛔ 팔 이름 형식: R#D#E#F# (받은 값 {arm!r})")
    if m.group(3) == "1" and m.group(2) == "0":
        raise SystemExit(f"⛔ {arm} 은 무동작 팔이다 — 회절 D 를 끄면 모서리회절 E 는 "
                         "아무 일도 안 한다(D0E1 ≡ D0E0).")
    #: ⛔레이다가 땅속으로 가면 그 줄은 뜻이 없다 — outdoor01 고도 20 m · 거리 15 m
    import math
    if env and 15 * math.sin(math.radians(abs(el))) >= 20.0:
        raise SystemExit(f"⛔ 레이다가 땅속: el{el:g} → 깊이 "
                         f"{15*math.sin(math.radians(abs(el))):.1f} m ≥ 20 m")
    b = BASE if depth == 2 else BASE.replace("--max-depth 2", f"--max-depth {depth}")
    if spp:
        b = b.replace("--spp 4000000000", f"--spp {spp}")
    e = f" --env {env}" if env else ""
    dr = f" --drone {drone}" if drone else ""
    bs = f" --body-scale {body:g}" if body else ""
    sc = f" --env-scat {scat:g}" if scat >= 0 else ""
    OUT.extend(f"{b}{e} --sw {arm} --els={el:g}{dr}{bs}{sc}"
               f" --shard {k} --nshards {nsh}" for k in range(nsh))


# ══ A ══ 가장 가르는 힘이 세다 — 앞에 둔다
sec("A ⭐드론 메쉬가 방아쇠인가 — 기체를 바꾼다 (빈 하늘 짝을 함께 산다)")
for dr in ("phantom4", "mini5pro"):
    job(drone=dr)                       # 지면만
    job(drone=dr, env="")               # 빈 하늘 짝

# ══ B ══
sec("B 탐색 문제인가 — 광선 예산을 1e8·1e9 로 (4e9 판은 이미 있다)")
for spp in (100_000_000, 1_000_000_000):
    job(spp=spp)

# ══ C ══
sec("C 어느 차수의 경로인가 — 반사 깊이 1 과 3 (깊이 2 는 이미 있다)")
for d in (1, 3):
    job(depth=d)
    job(depth=d, env="")                # 빈 하늘 짝 — 깊이를 바꾸면 드론 자신도 달라진다

# ══ D ══
sec("D 드론 크기가 방아쇠인가 — 동체를 반으로 / 두 배로 (빈 하늘 짝을 함께)")
for b in (0.5, 2.0):
    job(body=b)
    job(body=b, env="")

# ══ E ══
sec("E 거칠기가 다른 앙각에서도 끄나 — el −60 (el −30 은 이미 확인했다)")
job(scat=0.3)

GROUPS.append(("끝", len(OUT)))
if "--summary" in sys.argv:
    n = sum(1 for x in OUT if x and not x.startswith("#"))
    print(f"발주 줄 {n} (샤드 나눔 포함)")
    for (t1, i1), (_t2, i2) in zip(GROUPS, GROUPS[1:]):
        c = sum(1 for x in OUT[i1:i2] if x and not x.startswith("#"))
        print(f"  {c:>3} 줄  {t1}")
else:
    print("\n".join(x for x in OUT if x is not None))
