# -*- coding: utf-8 -*-
"""
make_jobs_0909.py — 실외 클러터 환경을 «다각도로» — 손잡이 하나씩.

■ 왜 (사용자 2026-09-06: «클러터 환경 모델링했을 때의 결과물을 다각도로 실험해 보면»)
    0903 판 마지막 쪽이 약속한 것이 «이 실외 메쉬 안에서 같은 다섯 팔을 돌린다»였다.
    지금까지 산 실외 칸(57 계열)은 **전부 15 m · 깊이 2 · 지면 S=0(거울)** 이고, 거칠기는
    한 팔에서 두 점(0.3·0.7)뿐이다. 손잡이를 하나씩 흔든 적이 없다.

■ 확인된 사실 (benchmark/elevation_sweep_md.py)
    · 환경은 outdoor01 하나 — 120×120 m 콘크리트 지면 · 건물 4 · 기둥 2 · 드론 고도 20 m
    · 지면 재질 기본 산란계수 **S=0 = 완벽한 거울** (src/materials.py). --env-scat 로 바꾼다.
    · 남의 씬은 --env sionna:<이름> (simple_street_canyon · munich · etoile · florence …)
    · ⛔우리 커널(--engine ours)은 --env 를 **거부한다**(:484, 2026-09-01) — 다섯 팔 중 넷만 된다.
    · 레이다는 거리·sin(앙각) 깊이에 온다 — outdoor01 은 고도 20 m 라 **거리·sin|앙각| < 20 m** 여야
      땅속에 안 들어간다. 이 파일이 줄마다 검사한다.

■ 설계 원칙
    · 한 묶음은 손잡이 **하나만** 흔든다. 나머지는 정본(15 m · 깊이 2 · 정본 메쉬 · 4e9 · 8,192 자세).
    · 대조군(같은 인자 · 환경만 없음)이 **같은 묶음 안에** 있다. 이미 있으면 거르기가 뺀다.
    · 정면 0.2° 창을 피한다 — 앙각 −30° 가 기본. 방위 0° 이면 앙각이 0 이 아니어야 한다.
    · 팔 둘(확산만 R0D0E0F1 · 회절 R0D1E1F1)이 기본. 다섯 팔이 필요한 묶음만 넷(우리 커널 제외).
    · ⛔챔버·F0·프롭 단독 없음. 리듬 몫 크기는 읽지 않는다 — STFT·에너지·변조 스펙트럼으로 읽는다.

쓰는 법
    cd /workspace/sionna
    CUDA_VISIBLE_DEVICES="" /workspace/.venvs/py312/bin/python runners/make_jobs_0909.py > runners/jobs_0909.txt
    CUDA_VISIBLE_DEVICES="" /workspace/.venvs/py312/bin/python runners/make_jobs_0909.py --summary
    발주 전 NEW·DONE·STALE 거르기(make_jobs_0907 머리말)를 반드시 거친다.
"""
from __future__ import annotations

import math
import sys

BASE = "--engine sionna --spp 4000000000 --n-poses 8192"
ALT_OUTDOOR01 = 20.0
ARMS2 = ("R0D0E0F1", "R0D1E1F1")
ARMS4 = ("R0D0E0F1", "R1D0E0F1", "R0D1E1F1", "R1D1E1F1")

OUT: list[str] = []
GROUPS: list[tuple[str, int]] = []


def sec(t: str) -> None:
    OUT.append(""); OUT.append(f"# ── {t}"); GROUPS.append((t, len(OUT)))


def job(*, arm: str, el: float, env: str = "", scat=None, az=None, rng: int = 15,
        depth: int = 2, nsh: int = 2, extra: str = "") -> None:
    if env.startswith("outdoor01") and rng * math.sin(math.radians(abs(el))) >= ALT_OUTDOOR01:
        raise SystemExit(f"⛔ 레이다가 땅속: {rng} m · {el}° → 깊이 {rng*math.sin(math.radians(abs(el))):.1f} m ≥ {ALT_OUTDOOR01}")
    e = f" --env {env}" if env else ""
    s = "" if scat is None else f" --env-scat {scat:g}"
    a = "" if az is None else f" --az-deg {az:g}"
    OUT.extend(f"{BASE} --range-m {rng} --sw {arm} --max-depth {depth} --els={el:g}{a}{e}{s}{extra}"
               f" --shard {k} --nshards {nsh}" for k in range(nsh))


# ── ⓐ 지면 거칠기 — 거울(S=0)에서 완전 확산(S=1)까지
sec("ⓐ ⭐지면 거칠기 S 사다리 — 지금 지면은 거울(S=0)이다 · 앙각 −30° · 대조 = S 기본")
for arm in ARMS2:
    for S in (0.1, 0.3, 0.5, 0.7, 1.0):          # 이미 있는 칸(R0D0E0F1 0.3·0.7)은 거르기가 뺀다
        job(arm=arm, el=-30, env="outdoor01", scat=S)
    job(arm=arm, el=-30, env="outdoor01")         # 대조: S 기본(거울) — 있으면 빠진다
    job(arm=arm, el=-30)                          # 대조: 자유공간 — 있으면 빠진다

# ── ⓑ 남의 씬 — 우리 콘크리트 거울이 아닌 실제 도시 씬에서도 같은가
sec("ⓑ ⭐남의 씬 — 엔비디아 기본 씬(거리 협곡 · 뮌헨) · 앙각 −30/−15° · 대조 = 자유공간")
for scene in ("sionna:simple_street_canyon", "sionna:munich"):
    for arm in ARMS2:
        for el in (-30, -15):
            job(arm=arm, el=el, env=scene)
for arm in ARMS2:
    job(arm=arm, el=-15)                          # 자유공간 대조 (−30 은 위에서)

# ── ⓒ 거리 — 스치는 각이 바뀐다 (레이다 깊이 < 20 m 를 지킨다)
sec("ⓒ 거리 — 15 → 30 m (앙각 −30°) · 15 → 60 m (앙각 −15°) · 대조 = 같은 거리 자유공간")
for arm in ARMS2:
    job(arm=arm, el=-30, env="outdoor01", rng=30); job(arm=arm, el=-30, rng=30)
    job(arm=arm, el=-15, env="outdoor01", rng=60); job(arm=arm, el=-15, rng=60)

# ── ⓓ 반사 깊이 — 지면을 거치는 경로가 몇 번 튀나
sec("ⓓ 반사 깊이 1·3 — 지면 경유 경로(깊이 ≥2)와 지면→드론→지면(깊이 3) · 앙각 −30°")
for arm in ARMS2:
    for d in (1, 3):
        job(arm=arm, el=-30, env="outdoor01", depth=d)
        job(arm=arm, el=-30, depth=d)             # 자유공간 대조

# ── ⓔ 방위 — 건물·기둥이 방위를 가른다
sec("ⓔ 방위 22.5·67.5·135·180° — 건물 배치가 보이는 각 · 앙각 −30° · 대조 = 자유공간 같은 방위")
for az in (22.5, 67.5, 135, 180):
    job(arm="R0D0E0F1", el=-30, env="outdoor01", az=az)
    job(arm="R0D0E0F1", el=-30, az=az)

# ── ⓕ 다섯 팔 약속 — 넷까지 (우리 커널은 --env 거부)
sec("ⓕ 지난 판이 약속한 «같은 다섯 팔» — 실외에서 넷 · 앙각 −30° 되풀이 2 판 (자연 산포)")
for arm in ARMS4:
    for rep in (1, 2):
        job(arm=arm, el=-30, env="outdoor01", extra=f" --rep {rep}")

GROUPS.append(("끝", len(OUT)))
if "--summary" in sys.argv:
    print(f"■ 0909 발주 — 잡 {sum(1 for x in OUT if x and not x.startswith('#'))} 줄")
    for (t, a), (_, b) in zip(GROUPS, GROUPS[1:]):
        print(f"    {t[:70]}  … {sum(1 for x in OUT[a:b] if x and not x.startswith('#'))} 줄")
else:
    print("\n".join(OUT).strip())
