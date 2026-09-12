#!/usr/bin/env python
"""0929 발주서 — **대역폭이 전자기 계산에 들어간 적이 없다.** 그것을 처음 잰다.

■ 어디서 나왔나 (⛔지어낸 물음이 아니다)
  랩카드의 서사는 ISAC 이다 — 망이 이미 쏘는 신호(WiFi 80 MHz · LTE 20 MHz · 5G 100 MHz)로
  드론을 본다. 그런데 지금 사슬에서 **파형은 산란이 끝난 뒤 곱해지는 스칼라**다:
    · benchmark/elevation_sweep_md.py 는 자세마다 **한 주파수의 복소수 하나**를 낸다
      (bandwidth·ofdm·subcarrier 낱말 0 건).
    · benchmark/passive_two_channel_md.py 가 그 시계열을 파형에 **재생(replay)** 한다
      — 표적 변조를 갈아끼우는 곱셈이고, 대역폭은 전자기에 안 들어간다
      (그 원장 outputs/passive_two_channel.json 의 가정 7 이 스스로 그렇게 적어 두었다).
  ⇒ 「대역 안에서 표적의 복소 반사율이 평평한가」를 **한 번도 안 봤다.**
    평평하면 그 곱셈이 정당하고, 안 평평하면 파형 벤치마크의 바탕이 흔들린다.

■ 재고 (2026-09-12)
  산 반송파: 3.5 GHz 2,290 칸 · 5.8 GHz 9 · 10 GHz 9 · 24 GHz 15.
  ⛔전부 **서로 다른 대역**이다. **한 대역 안의 여러 점**은 한 칸도 없다.

■ 무엇을 사나 — 5G NR 100 MHz 대역을 3.5 GHz 둘레로 훑는다
  fc = 3.450 · 3.475 · 3.525 · 3.550 GHz  (3.500 은 이미 있다 — 대역 중앙)
  · 빈 하늘 : 표적만 있는 가장 깨끗한 자리. 여기서 안 평평하면 그것은 **표적의 성질**이다.
  · 우리 실외: 장면이 끼면 어떻게 되나. 지면 반사가 주파수를 타면 여기서 갈린다.
  앙각 −30 · −60 · R0D0E0F1 · 깊이 2 · 15 m · spp 4e9 · 자세 8,192 · 2 조각

■ ⛔이 묶음이 답하지 않는 것
  · ⛔**OFDM 을 계산하는 것이 아니다.** 대역 안 네 점을 따로 계산해 «평평한가» 만 본다.
    부반송파·순환전치·프레임 구조는 여기 없다.
  · ⛔「그래서 파형 벤치마크가 맞다/틀리다」를 이 판이 결정하지 않는다. 평평함의 **크기**를
    재서, 곱셈 근사가 몇 dB 짜리 가정인지 말할 수 있게 될 뿐이다.
  · ⛔반송파가 바뀌면 날개끝 도플러도 fc 에 비례해 바뀐다 — 스펙트럼을 겹쳐 볼 때
    **주파수축을 fc 로 나눠** 본다. 안 그러면 대역 효과와 도플러 눈금 효과가 섞인다.
  · ⛔실기 계측 대조는 0 건이고 이 판으로도 안 생긴다.

■ 죽는조건
  · 네 점의 복소 반사율이 크기·위상 모두 좁은 폭 안에 모이면, 「이 대역에서 표적은
    평평하다」가 서고 재생 곱셈이 그만큼 정당해진다 — 그 폭을 수로 적는다.
  · 크게 흔들리면 파형 벤치마크의 수는 **대역 중앙 한 점의 것**이라고 못 박고,
    대역을 계산에 넣는 길(부반송파별 계산)을 다음 설계로 올린다.

쓰는 법:
    /workspace/.venvs/py312/bin/python runners/make_jobs_0929.py --summary
    /workspace/.venvs/py312/bin/python runners/make_jobs_0929.py > runners/jobs_0929.txt
  ⭐발주 전 반드시:
    grep -vE "^\\s*(#|$)" runners/jobs_0929.txt \\
      | xargs -d"\\n" -P 4 -I{} runners/filter_jobs.sh {} | cut -d"|" -f1 | sort | uniq -c
"""
from __future__ import annotations
import sys

ARM, NSH, SPP = "R0D0E0F1", 2, 4_000_000_000
ELS = (-30, -60)
#: 5G NR 100 MHz 대역의 네 점 — 중앙 3.500 은 이미 있다
FCS = (3.450, 3.475, 3.525, 3.550)
BASE = f"--engine sionna --spp {SPP} --n-poses 8192 --max-depth 2 --range-m 15"
#: 실측 중앙(분) — 빈 하늘 38 · 우리 실외 121 (2026-09-12 장면 × 팔 비용표)
SCENES = [("빈 하늘 — 표적만", None, 38), ("우리 실외 — 장면이 끼면", "outdoor01", 121)]

OUT: list[str] = []
OUT.append("# ══ 0929 큐 — 대역 안에서 표적이 평평한가 ══")
OUT.append("#  ⛔여기 적힌 것은 «물음» 이지 «답» 이 아니다.")
OUT.append("#  ⛔OFDM 을 계산하는 것이 아니다 — 대역 안 네 점을 따로 계산해 평평함만 본다.")
OUT.append("#  ⛔반송파가 바뀌면 날개끝 도플러도 fc 에 비례한다 — 겹쳐 볼 때 주파수축을 fc 로 나눈다.")
OUT.append("#  ⛔이 판이 «파형 벤치마크가 맞다/틀리다» 를 결정하지 않는다.")
OUT.append("#  ⛔실기 계측 대조는 0 건이고 이 판으로도 안 생긴다.")
OUT.append("#  ⚠대역 중앙 3.500 GHz 는 이미 있다 — 네 점만 사면 다섯 점이 선다.")
OUT.append("")
tot = 0.0
for title, env, mins in SCENES:
    n0 = len(OUT)
    OUT.append(f"# ── {title}")
    for fc in FCS:
        for el in ELS:
            for k in range(NSH):
                e = f" --env {env}" if env else ""
                OUT.append(f"{BASE} --sw {ARM} --fc-ghz {fc:g} --els={el}{e} "
                           f"--shard {k} --nshards {NSH}")
    n = sum(1 for x in OUT[n0:] if x and not x.startswith("#"))
    tot += n * mins
    OUT.append(f"#   위 {n} 줄 · 한 샤드 어림 {mins} 분 ⇒ {n*mins/60:.0f} 일꾼시간")
    OUT.append("")

if "--summary" in sys.argv:
    n = len(FCS) * len(ELS) * NSH * len(SCENES)
    print(f"발주 줄 {n} · 어림 {tot/60:.0f} 일꾼시간 (일꾼 9 이면 약 {tot/60/9:.1f} 시간)")
    for title, env, mins in SCENES:
        k = len(FCS) * len(ELS) * NSH
        print(f"   {title:24s} {k:3d} 줄 · {k*mins/60:5.0f} 일꾼시간")
    print(f"   반송파 {FCS} GHz · 앙각 {ELS} · 대역 중앙 3.5 는 이미 있다")
else:
    print("\n".join(OUT))
