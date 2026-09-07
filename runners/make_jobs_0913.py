# -*- coding: utf-8 -*-
"""
make_jobs_0913.py — 클러터 다음 판 **여섯 안 전부**, 사용자가 고른 순서로.

■ 사용자 지시(2026-09-07): 「B, A, C, D E F 순으로 전부 실어줘. 단 실제로 큐에 넣을 때는
  확실히 다듬어서.」 그래서 **한 발주서에 그 순서대로** 담는다 — 감독자는 파일 순서대로
  띄우므로 파일을 나누면 순서가 안 지켜진다.

■ 잣대는 **모양**이다 (사용자: 「모양 위주로 소개할거야」)
    빗살 하모닉 SNR 과 STFT 로 읽는다. ⛔레벨(dB)은 인용하지 않는다 — 회절 스위치 하나로
    34 dB, 지면 거칠기로 30 dB 넘게 움직인다. 그래서 자세는 **8,192 고정**이다.

■ ⛔다듬은 곳 — 그냥 두면 죽거나 뜻이 갈리는 자리
    ① **레이다가 땅속에 들어가면 안 된다.** 레이다는 거리·sin|앙각| 깊이에 오고 지면은
       고도 20 m 다. ⇒ r30 은 앙각 −30° 까지, r60 은 **−15° 까지**만 된다.
       (r30·sin45 = 21.2 m · r60·sin30 = 30.0 m 는 지면 아래다.) 발생기가 줄마다 막는다.
    ② **남의 씬은 고도가 다르다** — `ENV_BUILTIN_ALT = 25.0` 이고 우리 씬은 20.0 이다.
       ⇒ C 안의 결과를 A·B 와 «같은 조건» 으로 나란히 놓지 않는다. 그림 조건 줄에 적는다.
    ③ **확산(F)은 모든 팔에서 켠다** — A 안이 회절 D 와 모서리회절 E 를 가르는 것이지
       확산을 끄는 것이 아니다(R0D1E0F1 · R0D0E1F1 둘 다 F1).
    ④ **자유공간 짝을 같은 묶음 안에 둔다.** 없으면 «실외 때문» 이라 말할 수 없다.
       C 안만 예외다 — 남의 씬의 자유공간 짝은 우리 씬의 것과 같다(둘 다 빈 씬).

■ 여섯 안
    B 방위를 돌려도 이야기가 서나  ⭐가장 싸고, 결론의 **유효 범위**를 정한다
      ⚠지금 「꺼진 자세가 박자를 죽였다」는 방위 0° 한 자리에 붙어 있다. 방위 45°·90° 에서는
        꺼진 자세가 1 개·0 개뿐인데 빗살이 55 → 5.4·7.4 dB 로 무너진다.
    A 회절 켠 팔은 왜 안 돌아오나  ⭐지금 가장 큰 구멍
      회절 끈 두 팔은 무너진 열 칸이 **전부** 돌아오는데 켠 두 팔은 **하나도** 안 돌아온다.
      D(회절)와 E(모서리회절)를 따로 켜서 어느 쪽이 범인인지 가른다.
    C 남의 씬 — 우리 120×120 m 콘크리트 판이 인공적인가
    D 기체를 바꿔도 같은가 — 실외는 지금 matrice4e 하나뿐이다
    E 거리·깊이 — 실외는 전부 15 m · 깊이 2 뿐이다
    F 재현성 — ⚠`--rep` 판은 서로 1e−7 이라 자연 산포를 못 잰다. `--rotor-seed` 로 본다.

쓰는 법
    cd /workspace/sionna
    CUDA_VISIBLE_DEVICES="" /workspace/.venvs/py312/bin/python runners/make_jobs_0913.py > runners/jobs_0913.txt
    CUDA_VISIBLE_DEVICES="" /workspace/.venvs/py312/bin/python runners/make_jobs_0913.py --summary
    발주 전 runners/filter_jobs.sh 로 NEW·DONE·STALE 을 가른다.
"""
from __future__ import annotations

import math
import sys

BASE = "--engine sionna --spp 4000000000 --n-poses 8192 --max-depth 2"
ALT_OURS, ALT_BUILTIN = 20.0, 25.0
OUT: list[str] = []
GROUPS: list[tuple[str, int]] = []


def sec(t: str) -> None:
    OUT.append(""); OUT.append(f"# ── {t}"); GROUPS.append((t, len(OUT)))


def job(*, arm: str, el: float, env: str = "", az=None, rng: int = 15,
        depth: int = 2, drone: str = "", seed: int = 0, nsh: int = 2) -> None:
    #: ⛔줄마다 막는다 — 레이다가 지면 아래로 가면 그 줄은 뜻이 없다.
    if env:
        alt = ALT_BUILTIN if env.startswith("sionna:") else ALT_OURS
        d = rng * math.sin(math.radians(abs(el)))
        if d >= alt:
            raise SystemExit(f"⛔ 레이다가 땅속: r{rng} · el{el:g} → 깊이 {d:.1f} m ≥ 고도 {alt} m")
    e = f" --env {env}" if env else ""
    a = "" if az is None else f" --az-deg {az:g}"
    dr = f" --drone {drone}" if drone else ""
    sd = f" --rotor-seed {seed}" if seed else ""
    md = "" if depth == 2 else f" --max-depth {depth}"
    b = BASE if depth == 2 else BASE.replace(" --max-depth 2", md)
    OUT.extend(f"{b} --range-m {rng} --sw {arm} --els={el:g}{a}{e}{dr}{sd}"
               f" --shard {k} --nshards {nsh}" for k in range(nsh))


# ══ B ══ 가장 싸고 결론의 유효 범위를 정한다
sec("B ⭐방위를 돌려도 이야기가 서나 — 지금 결론은 방위 0° 한 자리에 붙어 있다")
for az in (15, 30, 60, 75):
    job(arm="R0D0E0F1", el=-30, az=az, env="outdoor01")
    job(arm="R0D0E0F1", el=-30, az=az)

# ══ A ══ 가장 큰 구멍
sec("A ⭐회절 D 와 모서리회절 E 를 따로 켠다 — 회절 켠 팔이 왜 안 돌아오나")
for arm in ("R0D1E0F1", "R0D0E1F1"):
    for el in (-30, -60, -75):
        job(arm=arm, el=el, env="outdoor01")
        job(arm=arm, el=el)

# ══ C ══ 발표 그림
sec("C 남의 씬(거리 협곡·뮌헨) — 우리 콘크리트 판이 인공적인가 ⚠고도 25 m 로 다르다")
for env in ("sionna:simple_street_canyon", "sionna:munich"):
    for arm in ("R0D0E0F1", "R0D1E1F1"):
        for el in (-30, -60):
            job(arm=arm, el=el, env=env)

# ══ D ══
sec("D 기체를 바꿔도 같은가 — 실외는 지금 matrice4e 하나뿐이다")
for dr in ("mini5pro", "mavic4pro", "phantom4"):
    job(arm="R0D0E0F1", el=-30, env="outdoor01", drone=dr)
    job(arm="R0D0E0F1", el=-30, drone=dr)

# ══ E ══
sec("E 거리·깊이 — 실외는 전부 15 m · 깊이 2 뿐이다 (땅속을 피해 앙각을 맞췄다)")
job(arm="R0D0E0F1", el=-30, env="outdoor01", rng=30); job(arm="R0D0E0F1", el=-30, rng=30)
job(arm="R0D0E0F1", el=-15, env="outdoor01", rng=60); job(arm="R0D0E0F1", el=-15, rng=60)
job(arm="R0D0E0F1", el=-30, env="outdoor01", depth=3); job(arm="R0D0E0F1", el=-30, depth=3)

# ══ F ══
sec("F 재현성 — 꺼진 자세가 씨앗을 타나 (⚠--rep 판은 1e−7 이라 산포를 못 잰다)")
for seed in (1, 2):
    for el in (-30, -60):
        job(arm="R0D0E0F1", el=el, env="outdoor01", seed=seed)

GROUPS.append(("끝", len(OUT)))
if "--summary" in sys.argv:
    n = sum(1 for x in OUT if x and not x.startswith("#"))
    print(f"■ 0913 발주 — 잡 {n} 줄 · 자세 8,192 고정 (모양으로 읽는다)")
    for (t, a), (_, b) in zip(GROUPS, GROUPS[1:]):
        print(f"    {t[:78]}  … {sum(1 for x in OUT[a:b] if x and not x.startswith('#'))} 줄")
else:
    print("\n".join(OUT).strip())
