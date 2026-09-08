#!/usr/bin/env python
"""0918 발주서 — 큐가 마른 뒤 채우는 판. 전부 **이미 있는 것의 빈칸**을 메운다.

⭐이 판이 답하려는 물음 셋 (전부 2026-09-08 훑기·판독에서 나왔다)

  A 덱의 실외 절이 **앙각 두 자리에만** 서 있다.
    `ls outputs/elev_sweep_shards | grep envsionna-simple_street_canyon` = 8 장.
    설정 둘 × 앙각 −30·−60 뿐이고 0°·−15°·−45°·−75° 가 없다.
    우리 씬(envoutdoor01 계열)은 같은 자리에 199 장이라 대조가 한쪽으로 기울어 있다.
    ⭐빈 하늘 짝은 그 앙각 넷에 **이미 다 있다**(el+0·el-15·el-45·el-75) — 대조군이 공짜다.

  B 「걸리는 자세를 정하는 것이 동체인가 로터인가」
    0914 판독(outputs/read_0914_0908.json ⑬)이 가른 것:
      · 동체만 바꾸면(--body-scale 0.5 ↔ 2, 같은 기체·같은 회전수) 자카드 0.681 — 대부분 그대로
      · 되돌림 깊이·지면 거칠기를 바꿔도 0.86~0.95 — 거의 안 움직인다
      · 그런데 **기체를 통째로 바꾸면**(phantom4 ↔ mini5pro, 둘 다 5500 rpm) 자카드 0.024
    동체는 안 움직이는데 기체는 움직인다 ⇒ 남은 차이는 **프롭·허브**다.
    --prop-scale 은 프롭 크기만 바꾸고 허브·동체·회전수를 고정한다(elevation_sweep_md.py:1340).
    ⛔프롭만 키우면 이웃 프롭이 관통한다 — matrice4e 는 틈이 5.9 mm 뿐이다(:1336 경고).
      그래서 **키울 때는 --frame-scale 과 짝지어** 기체를 통째로 키운다.
    ⚠--prop-scale 은 f_tip 을 배율만큼 옮긴다 — 판독기가 이미 _ps 를 읽어 대역을 옮긴다
      (comb_snr.py, 2026-09-08 고침).

  C 「되풀이가 끊기는 자리가 **각도**인가 **가로 거리**인가」 — 덱 13 쪽 열린 물음 ③.
    15 m 에서 창이 방위 0.11°와 0.12° 사이에서 닫힌다(outputs/front_window_0906.json).
    · 각도라면 120 m 에서도 0.11~0.12° 에서 닫힌다
    · 가로 거리라면 15 m 의 0.115° = 30 mm 이므로 120 m 에서는 0.0144° 에서 닫힌다
    지금 120 m 판은 방위 0.01·0.02·0.05 **셋뿐**이라 두 가설을 못 가른다.
    0.10·0.11·0.12·0.15 를 더하면 «각도» 쪽이 갈리고, 0.014 언저리를 더하면 «거리» 쪽이 갈린다.

⛔이 판에 없는 것과 그 까닭
  · 뮌헨 — 원장이 「드론이 건물에 가려 있다」고 적었다
    (builtin_scene_diagnosis_0908.json geometry.scenes.munich.cells 의 −30·−60 둘 다
     blocked_before_drone=true, 12.4 m 앞에서 «no-name-6» 에 막힘).
    트인 자리는 드론을 (−20, 0, 25) 로 옮기는 것인데 **그럴 손잡이가 없다** —
    --env-alt 는 고도만 바꾸고 그나마 남의 씬에는 안 걸린다(elevation_sweep_md.py 문지기).
    ⇒ GPU 발주가 아니라 코드 일이다. 여기 안 넣는다.
  · 거칠기 축 — 경로 상한에 붙어 접은 채로 둔다.
  · F0 계열(확산 끈 팔) — 발주하지 않는다(상시 규약).
  · 프로펠러 단독(--parts prop) — 더 이상 만들지 않는다(상시 규약).

쓰는 법:
    /workspace/.venvs/py312/bin/python runners/make_jobs_0918.py --summary
    /workspace/.venvs/py312/bin/python runners/make_jobs_0918.py > runners/jobs_0918.txt
"""
import sys

OUT: list = []
GROUPS: list = []
_SEEN: set = set()

#: 현세대 공통 — 0913/0914/0917 과 같은 축이라야 견줄 수 있다
BASE = "--engine sionna --spp 4000000000 --n-poses 8192 --max-depth 2"
ARM = "R0D0E0F1"          # 덱이 보여 주는 설정 하나로 좁힌다
NSH = 2


def sec(title: str) -> None:
    GROUPS.append((title, len(OUT)))
    OUT.append("")
    OUT.append(f"# ══ {title} ══")


def note(*lines: str) -> None:
    for s in lines:
        OUT.append(f"#   {s}")


def job(*, el, rng=15, env="", az=None, prop=0.0, frame=0.0, arm=ARM) -> None:
    """한 줄(샤드 나눔 포함). ⛔같은 줄을 두 번 내지 않는다."""
    e = f" --env {env}" if env else ""
    a = f" --az-deg {az:g}" if az is not None else ""
    p = f" --prop-scale {prop:g}" if prop else ""
    f = f" --frame-scale {frame:g}" if frame else ""
    for k in range(NSH):
        line = (f"{BASE} --range-m {rng} --sw {arm} --els={el:g}"
                f"{e}{a}{p}{f} --shard {k} --nshards {NSH}")
        if line in _SEEN:
            OUT.append(f"#   ⤷ 건너뜀(이미 위에 있다): {line}")
            continue
        _SEEN.add(line)
        OUT.append(line)


# ══ A ══ 덱의 실외 절을 앙각 두 자리에서 여섯 자리로
sec("A ⭐솔버가 주는 거리 협곡 — 앙각을 채운다 (빈 하늘 짝은 이미 다 있다)")
note("지금 협곡은 앙각 −30·−60 둘뿐이라 덱의 실외 절이 두 점에 서 있다.",
     "0°·−15°·−45°·−75° 를 더하면 우리 씬(여섯 자리)과 나란히 놓을 수 있다.",
     "⚠0° 는 그 자리의 빈 하늘 기록이 철회된 판이라 «되풀이» 물음에는 못 쓴다 —",
     "  여기서는 «지면·건물이 무늬를 묻는가» 만 본다.")
for el in (0, -15, -45, -75):
    job(el=el, env="sionna:simple_street_canyon")

# ══ B ══ 동체는 안 움직이는데 기체는 움직인다 — 남은 것은 프롭·허브
sec("B ⭐걸리는 자세를 정하는 것이 동체인가 프롭인가")
note("0914 ⑬: 동체만 0.5↔2 로 바꿔도 자카드 0.681, 깊이·거칠기는 0.86~0.95 로 거의 안 움직인다.",
     "그런데 기체를 통째로 바꾸면(같은 회전수) 0.024 로 흩어진다. 남은 차이가 프롭·허브다.",
     "⛔프롭만 키우면 이웃 프롭이 관통한다(틈 5.9 mm) — 키울 때는 프레임과 함께 키운다.",
     "⚠--prop-scale 은 f_tip 을 배율만큼 옮긴다. comb_snr 이 _ps 를 읽어 대역을 옮긴다.",
     "앙각 −60 으로 고정한다 — 0914 가 전부 그 자리라 바로 견줄 수 있다.")
for env in ("outdoor01_ground", ""):        # 실외와 그 빈 하늘 짝
    job(el=-60, env=env, prop=0.6)                    # 프롭만 줄인다 (관통 없음)
    job(el=-60, env=env, prop=1.5, frame=1.5)         # 기체를 통째로 키운다 (관통 없음)
    job(el=-60, env=env, frame=1.5)                   # 프레임만 벌린다 (프롭 고정)

# ══ C ══ 창이 각도인가 가로 거리인가
sec("C ⭐되풀이가 끊기는 자리 — 각도인가 가로 거리인가")
note("15 m 에서 창은 방위 0.11°와 0.12° 사이에서 닫힌다(front_window_0906.json).",
     "  각도라면 120 m 에서도 0.11~0.12° 에서 닫힌다.",
     "  가로 거리라면 15 m 의 0.115° = 30 mm 이므로 120 m 에서는 0.0144° 에서 닫힌다.",
     "지금 120 m 판은 방위 0.01·0.02·0.05 셋뿐이라 두 가설을 못 가른다.",
     "0.012·0.017 은 «거리» 가설의 벼랑을 끼고, 0.10·0.12 는 «각도» 가설의 벼랑을 낀다.",
     "⛔둘 다 아니면 그렇게 적는다 — 셋째 설명을 지어내지 않는다.")
for az in (0.012, 0.017, 0.10, 0.12):
    job(el=0, rng=120, az=az)

GROUPS.append(("끝", len(OUT)))
if "--summary" in sys.argv:
    n = sum(1 for x in OUT if x and not x.startswith("#"))
    print(f"발주 줄 {n} (샤드 나눔 포함)")
    for (t1, i1), (_t2, i2) in zip(GROUPS, GROUPS[1:]):
        c = sum(1 for x in OUT[i1:i2] if x and not x.startswith("#"))
        print(f"  {c:>3} 줄  {t1}")
    print("\n어림 — 0917 에서 잰 중앙값으로:")
    print("    거리 협곡 430 분/샤드 · 빈 하늘 37 분 · 우리 씬 땅만 56 분")
    print("  ⚠A 묶음(협곡 8 줄)이 이 판의 시간을 거의 다 쓴다.")
else:
    print("\n".join(x for x in OUT if x is not None))
