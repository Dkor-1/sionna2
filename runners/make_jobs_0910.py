# -*- coding: utf-8 -*-
"""
make_jobs_0910.py — ⭐**우리 커널의 실외 갈래** 첫 발주 (모노스태틱 · 평평한 지면).

■ 왜
    2026-09-07 에 `--ground` 를 넣어 우리 커널도 실외를 돌 수 있게 됐다
    (거울상 법 · 게이트 일곱: benchmark/verify_ground_kernel.py).
    0903 판 마지막 쪽이 «이 실외 장면에서 **같은 다섯 팔**을 돌린다» 고 약속했는데
    지금까지는 넷(Sionna 쪽)뿐이었다. 이 발주가 다섯째를 채운다.

■ 레이다는 **모노스태틱**이다
    송신국과 수신국이 같은 점(`ctr + R·û`)이다. 지면 반사 경로가 드론을 **다른 각도에서**
    비추므로 그 항만 바이스태틱 **산란**으로 계산할 뿐, 송·수신국이 떨어진 것이 아니다.
    (스윕에는 바이스태틱 레이다 인자가 아예 없다.)

■ ⛔이 모델이 하지 않는 것 — 읽는 사람이 반드시 알아야 한다
    지면은 **평평·무한·균질**이고 **정반사뿐**이다(거칠기 확산 없음).
    **건물·기둥이 없다** — Sionna 쪽 `--env outdoor01` 에는 건물 4·기둥 2 가 있다.
    ⇒ 두 엔진을 나란히 놓을 때는 «지면만» 대 «지면+건물» 임을 반드시 적는다.
    고도 기본 20 m 는 outdoor01 메쉬의 드론 고도와 **같은 값**이라 그나마 나란히 놓을 수 있다.

■ 묶음 (한 묶음은 손잡이 하나 · 대조군은 같은 묶음 안 · 정면 0.2° 창을 피해 앙각 −30° 기본)
    ⓐ 있나 없나        — 자유공간 대 지면, 앙각 넷. 이 발주의 기본선이다
    ⓑ 고도             — 10·20·40 m. 행로차 Δ 가 바뀌어 간섭 무늬가 움직여야 한다
    ⓒ 지면 재질        — 콘크리트 대 흙(ε_r 5.24 대 15.0). Γ 가 바뀐다
    ⓓ 확산 규약        — R/R_img 를 넣은 판과 뺀 판(고전 2선 규약). 손잡이를 흔들어 본다
    ⓔ 거리             — 30·60 m. 스침각이 바뀐다
    ⓕ 방위             — 45·90°. 지면은 방위에 대칭이라 **안 변해야** 한다(음성 대조)

⛔지키는 것 — 프로펠러 단독 안 만든다 · `--ptd`·`--plane-wave`·GPU 커널과는 못 쓴다(막혀 있다)

쓰는 법
    cd /workspace/sionna
    CUDA_VISIBLE_DEVICES="" /workspace/.venvs/py312/bin/python runners/make_jobs_0910.py > runners/jobs_0910.txt
    CUDA_VISIBLE_DEVICES="" /workspace/.venvs/py312/bin/python runners/make_jobs_0910.py --summary
    발주 전 runners/filter_jobs.sh 로 NEW·DONE·STALE 을 가른다.
"""
from __future__ import annotations

import math
import sys

BASE = "--engine ours --n-poses 8192"
OUT: list[str] = []
GROUPS: list[tuple[str, int]] = []


def sec(t: str) -> None:
    OUT.append(""); OUT.append(f"# ── {t}"); GROUPS.append((t, len(OUT)))


def job(*, el: float, gnd: str = "", alt: float = 20.0, spread: int = 1,
        az=None, rng: int = 15, nsh: int = 2) -> None:
    #: ⛔레이다가 지면 아래로 가면 커널이 막는다 — 발주서에서 미리 거른다.
    if gnd and rng * math.sin(math.radians(abs(el))) >= alt:
        raise SystemExit(f"⛔ 레이다가 땅속: r{rng} el{el} → {rng*math.sin(math.radians(abs(el))):.1f} m ≥ {alt}")
    g = ""
    if gnd:
        g = f" --ground {gnd}"
        if abs(alt - 20.0) > 1e-9:
            g += f" --ground-alt {alt:g}"
        if not spread:
            g += " --ground-spread 0"
    a = "" if az is None else f" --az-deg {az:g}"
    OUT.extend(f"{BASE} --range-m {rng} --els={el:g}{a}{g} --shard {k} --nshards {nsh}"
               for k in range(nsh))


# ── ⓐ 기본선
sec("ⓐ ⭐있나 없나 — 자유공간 대 지면 · 앙각 넷 (이 발주의 기본선)")
for el in (-15, -30, -45, -60):
    job(el=el)                       # 자유공간 대조 (이미 있으면 거르기가 뺀다)
    job(el=el, gnd="concrete")

# ── ⓑ 고도 — 행로차가 바뀐다
sec("ⓑ 고도 10·40 m — 행로차 Δ 가 바뀌어 간섭 무늬가 움직여야 한다 (20 m 는 ⓐ 에 있다)")
for alt in (10.0, 40.0):
    for el in (-15, -30):
        job(el=el, gnd="concrete", alt=alt)

# ── ⓒ 지면 재질
sec("ⓒ 지면 재질 — 흙(ε_r 15.0) 대 콘크리트(ε_r 5.24). Γ 가 바뀐다")
for el in (-15, -30, -45):
    job(el=el, gnd="soil")

# ── ⓓ 확산 규약 — 손잡이를 흔든다
sec("ⓓ 확산 규약 — R/R_img 를 뺀 고전 2선 판. 결론이 이 손잡이를 타는지 본다")
for el in (-15, -30, -45):
    job(el=el, gnd="concrete", spread=0)

# ── ⓔ 거리
sec("ⓔ 거리 30·60 m — 스침각이 바뀐다 (레이다 깊이 < 고도를 지킨다)")
job(el=-30, gnd="concrete", rng=30); job(el=-30, rng=30)
job(el=-15, gnd="concrete", rng=60); job(el=-15, rng=60)

# ── ⓕ 음성 대조
sec("ⓕ 방위 45·90° — 평평한 지면은 방위에 대칭이라 **안 변해야** 한다 (음성 대조)")
for az in (45, 90):
    job(el=-30, gnd="concrete", az=az)
    job(el=-30, az=az)

GROUPS.append(("끝", len(OUT)))
if "--summary" in sys.argv:
    print(f"■ 0910 발주 — 잡 {sum(1 for x in OUT if x and not x.startswith('#'))} 줄")
    for (t, a), (_, b) in zip(GROUPS, GROUPS[1:]):
        print(f"    {t[:72]}  … {sum(1 for x in OUT[a:b] if x and not x.startswith('#'))} 줄")
else:
    print("\n".join(OUT).strip())
