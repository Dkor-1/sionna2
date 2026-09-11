#!/usr/bin/env python
"""0927 발주서 — 협곡에 **기체를 세 대 더** 세운다. 지금은 한 대뿐이다.

■ 어디서 나왔나 (⛔지어낸 물음이 아니다 — 재고를 세었다)
  2026-09-11 재고: 거리 협곡 샤드 **73 장이 전부 기본 기체(matrice4e)** 다.
  빈 하늘 쪽에는 같은 팔·같은 앙각(−30·−60)으로 **네 기체**가 짝으로 서 있다
  (mavic4pro · mini5pro · phantom4 · s1000plus, 각 4 장).
  0923 C 묶음이 그중 **mini5pro 만** 산다(el −30·−60).
  ⇒ **mavic4pro · phantom4 · s1000plus 는 협곡에 한 장도 없다.** 그 칸을 산다.

■ 왜 사나 — 지금 우리가 못 하는 말
  「장면이 얹은 몫(D = E_장면 − E_빈하늘)」을 우리는 **한 기체에서만** 봤다. 그래서
  «협곡에서 사건이 96·339 개 난다» 가 **그 기체의 성질인지 장면의 성질인지 못 가른다.**
  네 기체가 서면 그것을 처음으로 가를 수 있다.

■ 무엇을 사나 — 거리 협곡 · 15 m · R0D0E0F1 · 깊이 2 · 4e9 · 자세 8,192
  기체 **mavic4pro · phantom4 · s1000plus** × 앙각 **−30 · −60** × 샤드 2 = **12 줄**
  (빈 하늘 짝은 이미 있다 — 그래서 이 12 줄만 사면 대조가 선다)

■ ⛔이 묶음이 답하지 않는 것
  · ⛔**자세 집합을 기체끼리 직접 못 견준다.** 자세 번호는 시각(t = i/PRF)이지 로터 각이
    아니고 기체마다 호버 회전수가 다르다(matrice4e 3800 · mavic4pro 3600 · phantom4 5500 ·
    s1000plus 4467 rpm, src/drones.py). ⇒ **레벨과 빈도만 읽는다.**
    0923 C 묶음이 이미 같은 한정을 달아 두었다.
  · ⛔사건 수가 기체마다 다르다고 그것을 곧장 «기체 크기 탓» 으로 읽지 마라 — 날개끝 주파수·
    프롭 지름·동체가 함께 바뀐다. 이 축으로는 하나만 흔든 것이 아니다.
  · ⛔σ 절대 레벨을 기체끼리 견주지 않는다(집 규약).
  · ⛔실기 계측 대조는 0 건이고 이 판으로도 안 생긴다.

■ 죽는조건
  · 네 기체에서 사건 수·레벨이 **같은 자리**에 서면 「협곡이 얹는 몫은 기체를 안 탄다」가 서고,
    그때 비로소 96·339 를 «장면의 성질» 로 말할 수 있다.
  · 기체마다 크게 다르면 그 수는 **그 기체의 것**이다 ⇒ 덱·문서에서 96·339 를 말할 때
    「matrice4e 에서」를 반드시 붙인다.

쓰는 법:
    /workspace/.venvs/py312/bin/python runners/make_jobs_0927.py --summary
    /workspace/.venvs/py312/bin/python runners/make_jobs_0927.py > runners/jobs_0927.txt
  ⭐발주 전 반드시:
    grep -vE "^\\s*(#|$)" runners/jobs_0927.txt \\
      | xargs -d"\\n" -P 4 -I{} runners/filter_jobs.sh {} | cut -d"|" -f1 | sort | uniq -c
"""
from __future__ import annotations
import sys

ARM, ENV, NSH, SPP = "R0D0E0F1", "sionna:simple_street_canyon", 2, 4_000_000_000
ELS = (-30, -60)
#: ⛔mini5pro 는 0923 C 가 산다 — 여기서 또 사면 두 번 뜬다
DRONES = [("mavic4pro", "267 mm · 3600 rpm"),
          ("phantom4", "240 mm · 5500 rpm"),
          ("s1000plus", "381 mm · 4467 rpm — 가장 큰 기체")]
BASE = f"--engine sionna --spp {SPP} --n-poses 8192 --max-depth 2 --range-m 15"

OUT: list = []
OUT.append("# ══ 0927 큐 — 협곡에 기체를 세 대 더 세운다 ══")
OUT.append("#  ⛔여기 적힌 것은 «물음» 이지 «답» 이 아니다.")
OUT.append("#  ⛔자세 집합을 기체끼리 직접 못 견준다(회전수가 다르다) — 레벨과 빈도만 읽는다.")
OUT.append("#  ⛔사건 수 차이를 곧장 «기체 크기 탓» 으로 읽지 마라 — 날개끝·프롭·동체가 함께 바뀐다.")
OUT.append("#  ⛔mini5pro 는 0923 C 가 산다 — 여기서 또 사지 않는다.")
OUT.append("#  ⛔실기 계측 대조는 0 건이고 이 판으로도 안 생긴다.")
OUT.append("#  ⚠빈 하늘 짝은 이미 있다 — 이 12 줄만 사면 대조가 선다.")
OUT.append("#  ⚠협곡 한 샤드가 실측 중앙 238 분이다 — 12 줄이면 어림 48 일꾼시간.")
OUT.append("")
for d, note in DRONES:
    OUT.append(f"# ── {d} ({note})")
    for el in ELS:
        for k in range(NSH):
            OUT.append(f"{BASE} --sw {ARM} --els={el} --env {ENV} --drone {d} "
                       f"--shard {k} --nshards {NSH}")
    OUT.append("")

if "--summary" in sys.argv:
    n = sum(1 for x in OUT if x and not x.startswith("#"))
    print(f"발주 줄 {n} · 기체 {len(DRONES)} × 앙각 {len(ELS)} × 샤드 {NSH}")
    print("어림 — 협곡 한 샤드 238 분 ⇒ 12 × 4.0 h ≈ 48 일꾼시간")
else:
    print("\n".join(OUT))
