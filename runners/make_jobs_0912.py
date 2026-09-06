# -*- coding: utf-8 -*-
"""
make_jobs_0912.py — 클러터를 모델링하고 **STFT 로 관찰**한다.

■ 목표 (사용자 2026-09-07)
    「클러터 모델링을 하고 실험을 돌려보고 **STFT 결과물을 관찰**하는 것」.
    ⇒ 수를 견주는 것이 아니라 **그림을 나란히 놓고 눈으로 보는 것**이 목적이다.
      그래서 자세는 **8,192 고정**이다 — STFT 는 자세열이 다 있어야 선다.
      (레벨만 볼 칸은 jobs_0911 이 자세 512 로 따로 산다.)

■ 이번 판의 머리기사 — ⭐**지면이냐 벽이냐**
    사용자가 물었는데(2026-09-06) 아직 못 답했다. 지금까지 실외는 지면·건물·기둥이
    **한 덩어리**라 가를 수가 없었다. 2026-09-07 에 같은 메쉬에서 부품만 가른 환경 둘을
    만들었다 — `outdoor01_ground`(지면만) · `outdoor01_bldg`(건물 넷 + 기둥 둘, 지면 없음).
    고도·재질·색은 `outdoor01` 과 글자 그대로 같다.
    ⇒ 한 줄에 네 판을 놓을 수 있게 된다: **자유공간 · 지면만 · 건물만 · 지면+건물**.

■ ⛔사지 않는 것 — 이미 디스크에 있다
    · 자유공간과 «지면+건물»(outdoor01) 은 팔 넷 × 앙각 여섯이 **전부 있다.**
      네 판 그림의 두 열은 계산 없이 채워진다.
    · 광선 예산 축 — 끝났다(1e8~4e9 에서 안 움직이고 4,294,967,295 가 라이브러리 천장이다).
    · 거칠기 축 — jobs_0911 이 사는 중이다. 겹치지 않는다.

■ 지금까지 갈린 것 (이 설계의 근거)
    · 실외에서 레벨이 오르는 몫은 표적이 아니라 **라디오가 제 발밑 지면을 본 것**이다 —
      드론이 안 들어가는 닫힌식이 다섯 앙각을 0.01~0.09 dB 로 맞춘다.
    · 실외에서 **날개 박자가 죽는다**(빗살 59.6 → 4.3 dB, el −30°). 자세 8,192 중 **74 개**를
      메우고 **그다음** 정지 성분을 빼면 59.7 로 돌아온다 — 순서를 바꾸면 4.3 이다.
    · ⚠**el −60° 는 절반만 돌아온다**(16.5 대 51.8). 왜인지 모른다 — ⓓ 가 그 자리를 좁힌다.

⛔지키는 것 — 확산(F)은 항상 켠다 · 프로펠러 단독 안 만든다 · 정면 0.2° 창을 피해 앙각은
  −15° 아래로만 · 레이다가 지면 아래로 가면 발생기가 막는다.

쓰는 법
    cd /workspace/sionna
    CUDA_VISIBLE_DEVICES="" /workspace/.venvs/py312/bin/python runners/make_jobs_0912.py > runners/jobs_0912.txt
    CUDA_VISIBLE_DEVICES="" /workspace/.venvs/py312/bin/python runners/make_jobs_0912.py --summary
    발주 전 runners/filter_jobs.sh 로 NEW·DONE·STALE 을 가른다.
"""
from __future__ import annotations

import math
import sys

BASE = "--engine sionna --spp 4000000000 --n-poses 8192 --range-m 15 --max-depth 2"
ALT_DEFAULT = 20.0
OUT: list[str] = []
GROUPS: list[tuple[str, int]] = []


def sec(t: str) -> None:
    OUT.append(""); OUT.append(f"# ── {t}"); GROUPS.append((t, len(OUT)))


def job(*, arm: str, el: float, env: str = "", alt: float = 0.0, nsh: int = 2) -> None:
    #: ⛔레이다는 거리·sin|앙각| 깊이에 온다 — 지면보다 아래로 가면 안 된다.
    h = alt or ALT_DEFAULT
    if env and 15.0 * math.sin(math.radians(abs(el))) >= h:
        raise SystemExit(f"⛔ 레이다가 땅속: el{el} · 고도 {h} m")
    e = f" --env {env}" if env else ""
    a = "" if not alt else f" --env-alt {alt:g}"
    OUT.extend(f"{BASE} --sw {arm} --els={el:g}{e}{a} --shard {k} --nshards {nsh}"
               for k in range(nsh))


# ── ⓐ 머리기사
sec("ⓐ ⭐지면이냐 벽이냐 — 같은 장면에서 부품만 가른다 (STFT 네 판 그림의 빠진 두 열)")
for env in ("outdoor01_ground", "outdoor01_bldg"):
    for el in (-15, -30, -45, -60):
        job(arm="R0D0E0F1", el=el, env=env)

# ── ⓑ 팔을 바꿔도 같은가
sec("ⓑ 회절 켠 팔에서도 같은가 — 기준선이 팔을 34 dB 타므로 한 팔로는 못 말한다")
for env in ("outdoor01_ground", "outdoor01_bldg"):
    for el in (-30, -60):
        job(arm="R0D1E1F1", el=el, env=env)

# ── ⓒ 고도
sec("ⓒ 드론 고도 10·40 m — 정지 클러터가 높이의 제곱에 반비례하나 (지면만)")
for alt in (10.0, 40.0):
    job(arm="R0D0E0F1", el=-30, env="outdoor01_ground", alt=alt)

#: ⛔⛔**ⓓ 를 뺐다(2026-09-07) — 사기 전에 답이 나왔다.**
#  「el −60° 가 절반만 돌아온다」는 틀린 읽기였다. 봉우리는 다 돌아오고, 남은 잔차의
#  99.5 % 가 자세 **열 개**에 몰려 있는데 그 자세들은 꺼진 것이 아니라 **밝다**
#  (|E|/중앙값 ≈ 1.117). 꺼진 자세 규칙이 못 보는 자리였을 뿐이다. 밝은 쪽도 함께 메우면
#  51.9 dB 로 자유공간 51.8 과 같아진다(outputs/outdoor_recover_0907.json).
#  ⇒ 앙각 −52·−68° 를 살 이유가 없다. 8 GPU시간 아꼈다.

GROUPS.append(("끝", len(OUT)))
if "--summary" in sys.argv:
    n = sum(1 for x in OUT if x and not x.startswith("#"))
    print(f"■ 0912 발주 — 잡 {n} 줄 · 자세 8,192 (STFT 관찰용)")
    for (t, a), (_, b) in zip(GROUPS, GROUPS[1:]):
        print(f"    {t[:76]}  … {sum(1 for x in OUT[a:b] if x and not x.startswith('#'))} 줄")
    print(f"\n    예상 GPU 시간 ≈ {n * 4096 * 1.85 / 3600:.0f} 시간 "
          f"(워커 9 병렬이면 벽시계 ≈ {n * 4096 * 1.85 / 3600 / 9:.1f} 시간)")
else:
    print("\n".join(OUT).strip())
