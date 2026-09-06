# -*- coding: utf-8 -*-
"""
make_jobs_0907.py — 0906 판이 답한 것에서 곧장 나오는 물음들.

■ 0906 큐(122 줄)가 답한 것
    ⭐**「사다리가 오르내린다」는 앞의 읽기를 거둔다.** 중앙값만 본 것이었다.
      「겹치는 자세가 몇 %인가」로 다시 재면 오르내리지 않는다. 0.15° 까지
      거의 모든 자세에서 켜져 있다가, 한 칸 만에 **한 자세도 없이** 꺼진다.
          방위  0.02~0.10°  99.9~100%   →  0.15°  **0.0%**
          앙각  0.02~0.15°  99.7~100%   →  0.20°  **0.0%**
      오르내린 것은 **겹치는 줄 수**(2 냐 3 이냐)이지 현상의 유무가 아니다.
    · 0.3 · 0.5 · 0.7° 와 −15° 도 전부 0.0% — 창 밖은 깨끗하다.
    · **팔마다 다르다.** 방위 0.05° 에서 R0D0E0F1 은 중앙 2.00(최대 2)인데
      R0D1E1F1 은 중앙 7.99, 한 자세는 **107** 까지 간다.
      앞서 「0.05° 에 봉우리」로 읽은 4.97 은 두 팔을 섞은 값이었다.
    · 축 위에서 N 은 거리(15→120 m)에도 광선 예산(0.1e9→4e9)에도 안 움직인다.

■ 「2° 벌어지면 안 일어나나」 — 답이 이미 있었다
    발주 직전에 있는 샤드를 전부 긁어 보니 굵은 각도는 이미 사 둔 것이 있었다.
        방위 0.2·0.3·0.5·0.7·1·1.5·2·3·5·10°  → 전부 **0.0%**
        앙각 −0.2 … −6 · −15 · −45° 와 +15·+30·+60°  → 전부 **0.0%**
    ⇒ **2° 는 확실히 꺼져 있다.** 창 밖에서 다시 켜지는 자리는 없다.
      경계는 방위 0.10°↔0.15° 사이, 앙각 −0.15°↔−0.20° 사이다.
    ⚠그래서 ⓐ 의 44 줄 가운데 **30 줄은 발주에서 뺐다** — 이미 답이 있다.
      남긴 것은 아직 빈 자리(앙각 −5·−10° 등)뿐이다.

■ ⛔발주 전에 반드시 거르는 절차
    줄마다 `--dry-run` 으로 목표 샤드 이름을 뽑아 셋으로 가른다.
        NEW   … 파일 없음            → 그대로 발주
        DONE  … 파일 있고 `n_dup` 도 있음 → **뺀다.** 다시 사면 낭비다
        STALE … 파일 있는데 `n_dup` 없음  → **`--overwrite` 를 붙인다.**
                안 붙이면 스크립트가 옛 세대를 보고 **조용히 건너뛴다.**
    이번 판: NEW 106 · DONE 30 · STALE 8 → 발주 114 줄.

■ 이번에 사는 것
    ⓐ **빈 구간을 메운다** — 0.5·1·2·3·5·10°. 창 밖이 계속 0% 인지, 아니면
      어딘가에서 다시 켜지는지. (사용자가 물은 「2°」가 여기 들어간다.)
    ⓑ **벼랑을 한 자리 더 좁힌다** — 방위 0.11~0.14 · 앙각 0.16~0.19.
      99.9% 에서 0.0% 로 한 칸 만에 가는지, 중간이 있는지.
    ⓒ ⭐**각도로 정해지나, 가로 거리로 정해지나** — 지금 벼랑은 15 m 에서 0.2°,
      곧 **가로 5.2 cm** 다. 거리를 30·60·120 m 로 늘려 벼랑을 다시 찾는다.
        · 각도가 기준이면 → 어느 거리에서나 0.15~0.2° 에서 꺼진다.
        · 가로 거리가 기준이면 → 120 m 에서는 **0.025°** 쯤으로 8 배 좁아진다.
      이 둘은 원인이 완전히 다르다. 한 판으로 갈린다.
    ⓓ ⭐**기체를 키우면 창도 커지나** — `--frame-scale`·`--body-scale` 로 크기만
      바꾼다. 창이 기체 크기에 붙어 있으면 ⓒ 의 「가로 거리」 쪽 손을 들어준다.
    ⓔ **107 이 재현되나** — R0D1E1F1 · 방위 0.05° 를 `--rep` 과 `--rotor-seed`
      로 다시 돌린다. 한 번 나온 꼬리는 아직 우연과 구별되지 않는다.
    ⓕ **깊이 3** — 깊이 1 → 2.68, 깊이 2 → 3.00 이었다. 한 칸 더 본다.

⛔지키는 것 — 확산(F)은 항상 켠다 · 프로펠러 단독 안 만든다 · `--inmem` 은 기본값

쓰는 법
    cd /workspace/sionna
    CUDA_VISIBLE_DEVICES="" python3 runners/make_jobs_0907.py > runners/jobs_0907.txt
    CUDA_VISIBLE_DEVICES="" python3 runners/make_jobs_0907.py --summary
"""
from __future__ import annotations

import sys

SPP = 4_000_000_000
BASE = f"--engine sionna --spp {SPP} --n-poses 8192"
ARMS = ("R0D0E0F1", "R0D1E1F1")

OUT: list[str] = []
GROUPS: list[tuple[str, int]] = []


def sec(title: str) -> None:
    OUT.append("")
    OUT.append(f"# ── {title}")
    GROUPS.append((title, len(OUT)))


def job(*, arm: str, el, az=None, rng: int = 15, depth: int = 2,
        nsh: int = 2, extra: str = "") -> None:
    #: 각도는 `%g` 로 적는다 — 0.15 를 `+0` 으로 뭉개면 다른 자리의 샤드를 덮는다.
    a = "" if az is None else f" --az-deg {az:g}"
    OUT.extend(
        f"{BASE} --range-m {rng} --sw {arm} --max-depth {depth}"
        f" --els={el:g}{a}{extra} --shard {s} --nshards {nsh}"
        for s in range(nsh)
    )


# ── ⓐ 0.2° 와 15° 사이 — 통째로 비어 있던 구간
sec("ⓐ 빈 구간 0.5~10° — 창 밖이 계속 꺼져 있는지")
for arm in ARMS:
    for az in (0.5, 1, 2, 3, 5, 10):
        job(arm=arm, el=0, az=az)
    for el in (-1, -2, -3, -5, -10):
        job(arm=arm, el=el)

# ── ⓑ 벼랑을 한 자리 더 좁힌다
sec("ⓑ 벼랑 좁히기 — 방위 0.11~0.14 · 앙각 0.16~0.19")
for arm in ARMS:
    for az in (0.11, 0.12, 0.13, 0.14):
        job(arm=arm, el=0, az=az)
    for el in (-0.16, -0.17, -0.18, -0.19):
        job(arm=arm, el=el)

# ── ⓒ ⭐각도냐 가로 거리냐
sec("ⓒ ⭐각도냐 가로 거리냐 — 거리마다 벼랑을 다시 찾는다")
#: 각도 기준이면 세 거리 모두 0.15~0.2 에서 꺼지고, 가로 거리 기준이면
#  거리에 반비례해 좁아진다. 그래서 거리마다 **다른 각도 띠**를 깐다.
for rng, azs in ((30, (0.05, 0.1, 0.15, 0.2)),
                 (60, (0.03, 0.05, 0.1, 0.15)),
                 (120, (0.01, 0.02, 0.05, 0.1))):
    for az in azs:
        job(arm="R0D0E0F1", el=0, az=az, rng=rng)

# ── ⓓ ⭐크기를 바꾼다
sec("ⓓ ⭐기체를 키우면 창도 커지나 — 크기만 바꾼다")
for flag, vals in (("--frame-scale", (0.5, 2.0)), ("--body-scale", (0.5, 2.0))):
    for v in vals:
        for az in (0.1, 0.15, 0.2):
            job(arm="R0D0E0F1", el=0, az=az, extra=f" {flag} {v:g}")

# ── ⓔ 한 번 나온 꼬리를 다시
sec("ⓔ 방위 0.05° 의 107 이 재현되나 — 되풀이와 씨앗")
for rep in (1, 2):
    job(arm="R0D1E1F1", el=0, az=0.05, nsh=3, extra=f" --rep {rep}")
for seed in (1, 2):
    job(arm="R0D1E1F1", el=0, az=0.05, extra=f" --rotor-seed {seed}")
    job(arm="R0D1E1F1", el=0, az=0.1, extra=f" --rotor-seed {seed}")

# ── ⓕ 깊이 한 칸 더
sec("ⓕ 깊이 3")
for az in (0, 0.1, 0.15):
    job(arm="R0D0E0F1", el=0, az=(None if az == 0 else az), depth=3)

GROUPS.append(("끝", len(OUT)))

if "--summary" in sys.argv:
    print(f"■ 0907 발주 — 잡 {sum(1 for x in OUT if not x.startswith('#') and x)} 줄")
    for (t, a), (_, b) in zip(GROUPS, GROUPS[1:]):
        n = sum(1 for x in OUT[a:b] if x and not x.startswith("#"))
        print(f"    {t}  … {n} 줄")
else:
    print("\n".join(OUT).strip())
