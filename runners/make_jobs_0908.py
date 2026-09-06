# -*- coding: utf-8 -*-
"""
make_jobs_0908.py — 09-10 팀미팅 그림이 **말할 수 있는 범위**를 넓히는 발주.

■ 왜 이 판이 필요한가
    그림 조사(work/sweep_0904/figsurvey_0906.json)가 「지금 자료로는 못 하는 것」을
    짚었다. 그림은 다 구울 수 있는데, **말할 수 있는 범위가 좁다.**

    ⛔**팔 다섯 중 둘까지만 말할 수 있다.** 굴절을 켠 두 팔(R1D0E0F1·R1D1E1F1)에는
      축 근처 칸이 **아예 없다** — 고도 15·30·60° 뿐이고 방위 사다리는 빈 사전이다.
      「0.2° 벌어지면 없다」를 다섯 팔로 말하려면 이 둘을 사야 한다.
    ⛔확산만 켠 팔의 방위 0.5°·1°·2° 는 샤드가 **있는데** 되풀이 칸이 없는 옛 세대다.
      사다리 선이 그 세 칸에서 끊긴다.
    ⚠방위 0.7° 만 다른 칸과 다르다 — 두 팔 모두 자세마다 줄이 하나씩 지워지는데
      필드는 0.7%(확산)·0.0%(회절) 밖에 안 커진다. 창 밖 다른 칸은 비트 단위로 같다.
      샤드 4 장뿐이고 씨앗 바꾼 판이 없어 **진짜인지 확인이 안 됐다.**
    ⚠회절 켠 팔의 방위 0.05° 봉우리(중앙 7.99·최대 107.2)와 0.07° 구멍(1.03%) 도
      아무도 재현을 확인하지 않았다. 그림에 그대로 보이므로 확인이 필요하다.
    ⛔창의 **폭**이 광선 예산을 타는지 모른다 — 1e8·1e9 에는 고도 0 과 −30 두 칸뿐이라
      가장자리를 못 본다. 지금까지 흔든 것은 **정면 한 점의 배수**뿐이다.

■ ⛔지키는 것
    확산(F)은 항상 켠다 · 프로펠러 단독 안 만든다 · `--inmem` 은 기본값
    발주 전에 줄마다 `--dry-run` 으로 NEW·DONE·STALE 을 가른다(make_jobs_0907 머리말)

쓰는 법
    cd /workspace/sionna
    CUDA_VISIBLE_DEVICES="" /workspace/.venvs/py312/bin/python runners/make_jobs_0908.py > runners/jobs_0908.txt
    CUDA_VISIBLE_DEVICES="" /workspace/.venvs/py312/bin/python runners/make_jobs_0908.py --summary
"""
from __future__ import annotations

import sys

BASE = "--engine sionna --n-poses 8192 --range-m 15"
SPP = 4_000_000_000

OUT: list[str] = []
GROUPS: list[tuple[str, int]] = []


def sec(t: str) -> None:
    OUT.append("")
    OUT.append(f"# ── {t}")
    GROUPS.append((t, len(OUT)))


def job(*, arm: str, el=0, az=None, spp: int = SPP, nsh: int = 2, extra: str = "") -> None:
    a = "" if az is None else f" --az-deg {az:g}"
    OUT.extend(
        f"{BASE} --spp {spp} --sw {arm} --max-depth 2 --els={el:g}{a}{extra}"
        f" --shard {s} --nshards {nsh}"
        for s in range(nsh)
    )


# ── ⓐ 다섯 팔로 말하려면 이 둘이 있어야 한다
sec("ⓐ ⭐굴절 켠 두 팔의 근축 사다리 — 지금은 팔 둘까지만 말할 수 있다")
for arm in ("R1D0E0F1", "R1D1E1F1"):
    job(arm=arm, el=0)                                   # 축 위 기준점
    for az in (0.05, 0.1, 0.15, 0.2, 0.3):
        job(arm=arm, el=0, az=az)
    for el in (-0.05, -0.1, -0.15, -0.2, -0.3):
        job(arm=arm, el=el)

# ── ⓑ 끊긴 선을 잇는다
sec("ⓑ 확산만 켠 팔의 방위 0.5·1·2° — 옛 세대라 되풀이 칸이 없다")
for az in (0.5, 1, 2):
    job(arm="R0D0E0F1", el=0, az=az)

# ── ⓒ 창 밖에서 혼자 다른 칸
sec("ⓒ ⚠방위 0.7° 만 다르다 — 씨앗을 바꿔 진짜인지 본다")
for arm in ("R0D0E0F1", "R0D1E1F1"):
    for seed in (1, 2):
        job(arm=arm, el=0, az=0.7, extra=f" --rotor-seed {seed}")

# ── ⓓ 회절 팔의 들쭉날쭉
sec("ⓓ ⚠회절 팔 방위 0.05° 봉우리와 0.07° 구멍 — 재현 확인이 없다")
for az in (0.05, 0.07):
    for rep in (1, 2):
        job(arm="R0D1E1F1", el=0, az=az, extra=f" --rep {rep}")

# ── ⓔ 창의 폭이 광선 예산을 타나
sec("ⓔ 창의 **폭**이 광선 예산을 타나 — 지금까지 흔든 것은 정면 한 점뿐이다")
for spp in (100_000_000, 1_000_000_000):
    for az in (0.1, 0.15, 0.2):
        job(arm="R0D0E0F1", el=0, az=az, spp=spp)

GROUPS.append(("끝", len(OUT)))

if "--summary" in sys.argv:
    print(f"■ 0908 발주 — 잡 {sum(1 for x in OUT if x and not x.startswith('#'))} 줄")
    for (t, a), (_, b) in zip(GROUPS, GROUPS[1:]):
        n = sum(1 for x in OUT[a:b] if x and not x.startswith("#"))
        print(f"    {t}  … {n} 줄")
else:
    print("\n".join(OUT).strip())
