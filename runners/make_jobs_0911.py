# -*- coding: utf-8 -*-
"""
make_jobs_0911.py — 실외 축 **재설계**. 2026-09-07 에 갈린 것에 맞춘다.

■ 무엇이 갈렸나 (그래서 앞 설계 0909·0910 을 접는다)
    ⓐ ⛔**실외의 «+53 dB» 는 표적이 아니다.** 자세가 바뀌어도 안 변하는 성분이고, 드론이
      안 들어가는 닫힌식 σ=|Γ|²/(4π(2h)²) 이 다섯 앙각을 0.01~0.09 dB 로 맞춘다.
      라디오가 제 발밑 지면을 때리고 돌아온 정지 클러터다.
    ⓑ ⛔**그 «+53 dB» 는 손잡이 둘을 심하게 탄다.** 회절 스위치 하나로 34 dB,
      지면 거칠기로 30 dB 넘게 움직인다. 폭을 안 적으면 못 쓰는 수다.
    ⓒ ⛔⛔**거칠기 판 세 계열이 8,192 자세 전부 경로 상한에 잘려 있었다**(2026-09-07 확인).
      곧 «거칠면 환경 몫이 준다» 를 **아직 아무도 안 쟀다** — 준 것이 물리인지 잘림인지 모른다.
    ⓓ ⭐**믿을 만한 쪽은 모양이다.** 저장소가 «모양은 되고 절대 레벨은 안 된다» 로 선을
      그어 뒀다. 그리고 모양 잣대(빗살 SNR)로는 이미 결과가 있다 —
      실외에서 59.62 → 4.30 으로 죽고, **8,192 자세 중 74 자세만 메우면 59.66 으로 돌아온다**
      (아무 자세나 74 개 메우면 4.30 그대로). el −60 은 84 자세를 메워도 16.53 까지만이다.

■ 그래서 이번에 사는 것 — **레벨 사다리를 사지 않는다. 잘림과 모양을 산다.**
    ⓐ ⭐**잘림 수렴** — 상한을 올려도 값이 안 움직이나. 이게 먼저다. 안 닫히면 아래가 다 헛것이다.
    ⓑ 거칠기 사다리를 **잘림 없는 상한**으로, 자세를 줄여서(레벨만 보면 되니까)
    ⓒ 거친 지면에서 모양이 어떻게 되나 — 거울 대조와 짝으로

■ ⛔사지 않고 **분석만** 하는 것 (이미 디스크에 있다)
    · 네 팔 × 여섯 앙각의 실외 샤드 — 전부 있다. 겹침 셈(n_dup)이 없을 뿐이고 이번
      물음은 그것을 안 쓴다. 기준선이 팔을 34 dB 타는 것도, 빠진 앙각도 이것으로 읽는다.
    · «74 자세만 메우면 빗살이 돌아온다» 가 팔·앙각 전반에서 성립하나 — 같은 샤드로 답한다.

⛔안 사는 것과 까닭
    · 우리 커널 지면(--ground) — 게이트 일곱을 통과했지만(⚠그 게이트는 저장소의 2선 모델과
      **자기일치** 한다는 것만 잰다 — 실측 대조는 0 건이다) 지금 물음이 «분모와 잘림» 이라
      여기 넣으면 축이 하나 더 늘 뿐이다. 기능은 남겨 두고 이번 판에서는 안 산다.
    · 거리·방위 축 — 앞 설계에 있었으나 지금 물음이 아니다.
    · ⛔확산(F)은 항상 켠다 · 프로펠러 단독 안 만든다.

⚠자세 수를 줄인 칸은 **레벨만** 읽는다 — 빗살 SNR 은 자세가 많아야 선다(정본 8,192).

쓰는 법
    cd /workspace/sionna
    CUDA_VISIBLE_DEVICES="" /workspace/.venvs/py312/bin/python runners/make_jobs_0911.py > runners/jobs_0911.txt
    CUDA_VISIBLE_DEVICES="" /workspace/.venvs/py312/bin/python runners/make_jobs_0911.py --summary
    발주 전 runners/filter_jobs.sh 로 NEW·DONE·STALE 을 가른다.
"""
from __future__ import annotations

import sys

BASE = "--engine sionna --spp 4000000000 --range-m 15 --max-depth 2"
OUT: list[str] = []
GROUPS: list[tuple[str, int]] = []


def sec(t: str) -> None:
    OUT.append(""); OUT.append(f"# ── {t}"); GROUPS.append((t, len(OUT)))


def job(*, arm: str, el, n: int = 8192, env: str = "", scat=None,
        mp: int = 0, nsh: int = 2) -> None:
    e = f" --env {env}" if env else ""
    s = "" if scat is None else f" --env-scat {scat:g}"
    m = "" if not mp else f" --max-paths {mp}"
    OUT.extend(f"{BASE} --n-poses {n} --sw {arm} --els={el:g}{e}{s}{m}"
               f" --shard {k} --nshards {nsh}" for k in range(nsh))


# ── ⓐ 먼저 닫아야 하는 것
sec("ⓐ ⭐⭐잘림 수렴 — 상한을 올려도 값이 안 움직이나 (자세 256, 싸고 결정적)")
for mp in (0, 6_000_000, 12_000_000):        # 0 = 규약값 2,000,000
    job(arm="R0D0E0F1", el=-30, n=256, env="outdoor01", scat=0.3, mp=mp)
    job(arm="R0D0E0F1", el=-30, n=256, env="outdoor01", scat=0.7, mp=mp)

# ── ⓑ 거칠기 — 레벨만 보므로 자세를 줄인다
sec("ⓑ 거칠기 사다리 — 잘림 없는 상한으로 다시. 자세 512(레벨만 읽는다)")
for S in (0.0, 0.1, 0.3, 0.5, 0.7, 1.0):
    job(arm="R0D0E0F1", el=-30, n=512, env="outdoor01", scat=S, mp=12_000_000)
job(arm="R0D0E0F1", el=-30, n=512)                      # 자유공간 대조(같은 자세 수)
job(arm="R0D0E0F1", el=-30, n=512, env="outdoor01")     # 재질 기본(S 안 줌) 대조

#: ⛔⛔**ⓒ 빠진 앙각 · ⓓ 팔 넷 은 사지 않는다 — 이미 디스크에 다 있다.**
#  발주 전 거르기가 24 줄을 STALE 로 잡았는데, 그 «STALE» 은 파일이 없는 것이 아니라
#  겹침 셈(n_dup)이 없는 옛 세대라는 뜻이다. 네 팔 × 여섯 앙각의 실외 샤드가 전부 있고,
#  이번 물음(모양 · 빗살 SNR)은 n_dup 을 안 쓴다. ⇒ **사지 말고 분석한다.**
#  (약 40 GPU시간 아꼈다. memory: filter-jobs-before-queueing 의 ⚠ 항목이 이 경우다.)

# ── ⓒ 거친 지면에서 모양이 어떻게 되나 — 자세를 늘리되 ⓐ 가 상한을 정한 뒤에
sec("ⓒ 거친 지면(S=0.5) 앙각 셋 — 자세 512. ⚠8,192 로 두면 샤드 하나에 24 시간이라 줄였다")
for el in (-15, -30, -60):
    job(arm="R0D0E0F1", el=el, n=512, env="outdoor01", scat=0.5, mp=12_000_000)
    job(arm="R0D0E0F1", el=el, n=512, env="outdoor01")        # 같은 자세 수의 거울 대조

GROUPS.append(("끝", len(OUT)))
if "--summary" in sys.argv:
    print(f"■ 0911 발주 — 잡 {sum(1 for x in OUT if x and not x.startswith('#'))} 줄")
    for (t, a), (_, b) in zip(GROUPS, GROUPS[1:]):
        print(f"    {t[:74]}  … {sum(1 for x in OUT[a:b] if x and not x.startswith('#'))} 줄")
else:
    print("\n".join(OUT).strip())
