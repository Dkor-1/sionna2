#!/usr/bin/env python
"""0923 발주서 — 0921 재고 세기가 찾은 «정말 안 산 축» 가운데 0922 가 안 산 것.

■ 왜 이 넷인가
  2026-09-09 재고 세기(work/wf/queue_design_0921_result.json census.truly_empty)가
  재고 7,000+ 장을 정규식으로 전수로 풀어 «정말 아직 안 산 축» 여섯을 세었다.
  0922 가 그중 둘(뒤쪽 반구 방위 · 협곡의 널)을 샀다. 남은 넷을 여기서 산다.
  ⭐한 축(우리 지면만 · 앙각 0)은 그 사이 0920 이 채웠다 — dry-run 이 「있음」을 냈다.

■ ⛔⛔이 발주서를 읽는 사람이 오해하지 않도록
  · 묶음 이름은 **무엇을 사는지**이지 무엇이 참인지가 아니다.
  · 묶음마다 «이 묶음이 답하지 않는 것» 을 적었다 — 결과를 읽을 때 먼저 본다.
  · ⛔「우리 커널이 맞고 솔버가 틀렸다」를 겨누는 줄은 없다. 둘 다 근사다.
  · ⛔실기 계측 대조는 이 저장소에 0 건이고 이 판으로도 안 생긴다.

■ ⚠2026-09-09 지적으로 확인된 한계 (결과를 읽을 때 함께 본다)
  ① 상한과 중복제거 해시 통 수가 묶여 있다(spec_counter_size = max(상한, 1e6),
     sb_candidate_generator.py:59·312). 우리 상한 2,000,000 은 바닥값 위다.
  ② 반환 경로 수는 후보 수가 아니다(path_solver.py:194 후보 → :246 무효 제거).
  ③ D = E_장면 − E_빈하늘 은 «환경 산란» 이 아니다 — 차폐·드론 경로 변화·탐색 차이 포함.
  ④ 진폭 증가를 «경로 유실의 반증» 으로 쓰지 않는다.
  ⑤ n_a·n_b/N 은 균일·독립 추출을 가정한 참고값이다.
  ⑥ 옵션을 다 켜도 모든 상호작용이 아니다 — 회절 경로당 1 회 · 확산+회절 동거 금지.

■ ⛔손잡이 문법에 함정이 하나 있다
  `--parts -camera` 는 argparse 가 `-camera` 를 **옵션으로 읽어** 죽는다.
  `--parts=-camera` 로 **붙여** 써야 한다(dry-run 으로 확인: _partsnocamera 로 이름이 난다).

쓰는 법:
    /workspace/.venvs/py312/bin/python runners/make_jobs_0923.py --summary
    /workspace/.venvs/py312/bin/python runners/make_jobs_0923.py > runners/jobs_0923.txt
"""
import sys

OUT: list = []
GROUPS: list = []
_SEEN: set = set()

BASE = "--engine sionna --spp 4000000000 --n-poses 8192"
ARM = "R0D0E0F1"
NSH = 2


def sec(title: str, *notes: str) -> None:
    GROUPS.append((title, len(OUT)))
    OUT.append("")
    OUT.append(f"# ══ {title} ══")
    for s in notes:
        OUT.append(f"#   {s}")


def job(*, el, depth=2, env="", parts="", drone="", rng=15, arm=ARM) -> None:
    e = f" --env {env}" if env else ""
    #: ⛔`--parts -camera` 는 argparse 가 죽인다 — `=` 로 붙인다
    p = f" --parts={parts}" if parts else ""
    d = f" --drone {drone}" if drone else ""
    for k in range(NSH):
        line = (f"{BASE} --max-depth {depth} --range-m {rng} --sw {arm}"
                f" --els={el:g}{e}{p}{d} --shard {k} --nshards {NSH}")
        if line in _SEEN:
            OUT.append(f"#   ⤷ 건너뜀(이미 위에 있다): {line}")
            continue
        _SEEN.add(line)
        OUT.append(line)


OUT.append("# ══ 0923 큐 — 재고 세기가 찾은 «안 산 축» 의 나머지 ══")
OUT.append("#  ⛔여기 적힌 것은 «물음» 이지 «답» 이 아니다.")
OUT.append("#  ⛔묶음마다 «안 답하는 것» 을 적었다 — 결과를 읽을 때 먼저 본다.")
OUT.append("#  ⛔실기 계측 대조는 0 건이고 이 판으로도 안 생긴다.")

# ══ A ══
sec("A 정지 부품 나눔 — 무엇이 프롭 낙차를 덮나 (재고에 11/13 그룹이 0 장)",
    "물음  정면(앙각 0)에서 프롭만 있는 팔은 8,192 자세 중 3,331 개가 중앙의 0.9 배 아래로",
    "      떨어지는데 통째는 58 개뿐이다. 정지 부품이 바닥을 올려 덮고 있다는 것인데,",
    "      **어느 정지 부품이 덮는지는 한 번도 안 샀다.**",
    "죽는조건  카메라를 뺀 판의 낙차 자세 수가 통째(58)에서 안 움직이면 «카메라가 덮는다» 는",
    "        죽는다. 3,331 쪽으로 크게 가면 그 부품이 바닥의 큰 몫이라는 관찰이 선다.",
    "⛔안답함  «어느 삼각형이» 까지는 안 간다 — outputs/hit_triangle_0903.json 이 카메라를",
    "        가리키지만 근거가 **기체당 자세 하나**다. 이 판은 자세 8,192 개로 넓힐 뿐이다.",
    "⛔안답함  이것은 빈 하늘 판이다 — 실외·두 씬 차이에는 한 글자도 답하지 않는다.",
    "⚠깊이 1 로 산다 — 그 자리의 옛 판(_d1)과 나란히 놓으려는 것이다.")
for parts in ("-camera", "-body", "-arm"):
    job(el=0, depth=1, parts=parts)

# ══ B ══
sec("B 부품 가른 실외의 «축 위» 칸 — 3.00 → 2.70 을 만드는 것이 지면인가 건물인가",
    "물음  축 위(앙각 0)에서 같은 에코가 몇 줄로 적히나 — 빈 하늘은 3.00 배,",
    "      우리 씬 통째는 2.70 배다(rep1·rep2·rep3 세 판이 전부 2.6988).",
    "      그 3.00 → 2.70 을 만드는 것이 지면인지 건물인지 지금은 못 가른다.",
    "죽는조건  건물만 판이 3.00 을 그대로 내면 지면이 그 몫을 만든 것이고, 2.70 쪽이면 건물이다.",
    "        둘 다 3.00 이면 «부품으로 안 갈린다» 로 적고 이 축을 접는다.",
    "⛔안답함  «왜 겹쳐 적히나» 에는 답하지 않는다 — 어느 면이 만드나까지다.",
    "⛔안답함  협곡은 부품으로 못 쪼갠다 — 이 물음을 그 씬에서는 물을 수 없다.",
    "⚠우리 지면만·앙각 0 은 0920 이 이미 샀다(dry-run «있음») — 건물만 두 줄만 산다.")
job(el=0, env="outdoor01_bldg")

# ══ C ══
sec("C 남의 씬 × 기본 아닌 기체 — 합성 배율 축과 실제 기체 축이 같은 답을 주나",
    "물음  「걸리는 자세를 정하는 것은 프롭·허브다」를 지금까지 흔든 것은 --prop-scale ·",
    "      --frame-scale 뿐이다 — 같은 메쉬를 늘렸다 줄인 **합성** 축이다.",
    "      실제 기체가 그 범위를 덮는다(mini5pro 152.4 mm = matrice4e 의 0.56 배).",
    "죽는조건  협곡에서 mini5pro 의 걸린 자세 목록이 matrice4e 와 «널 띠 안» 이면 기체 교체가",
    "        목록을 안 옮기는 것이고, 널 아래로 흩어지면 옮기는 것이다.",
    "⛔안답함  ⚠**널이 먼저 있어야 읽을 수 있다** — 0922 A 가 협곡의 널을 사고 있다.",
    "        그 값이 나오기 전에는 이 칸의 자카드를 «크다/작다» 로 말할 수 없다.",
    "⛔안답함  자세 번호는 시각(t=i/PRF)이지 로터 각이 아니다 — 회전수가 다른 기체끼리는",
    "        같은 번호가 다른 각이다. matrice4e 3800 대 mini5pro 5500 rpm 이라",
    "        **이 짝은 자세 집합을 직접 못 견준다.** 레벨과 빈도만 읽는다.")
for el in (-30, -60):
    job(el=el, env="sionna:simple_street_canyon", drone="mini5pro")

# ══ D ══
sec("D 앙각 −60 빈 하늘 기준선을 겹침 열쇠 있는 세대로 — 가장 많이 인용되는 분모의 감사",
    "물음  read_0914_0908.py · read_0918B_0909.py 의 기본 빈 하늘 짝(앙각 −60)이",
    "      2026-08-24 판이라 nret·n_dup·E_dedup·n_trunc 가 없다.",
    "      그 두 장이 D = E_실외 − E_빈하늘 의 **빼는 쪽**이고 「지면이 올린 몫」의 분모다.",
    "      빈 하늘은 축 위에서 에코를 3.00 배로 적는다 — 앙각 −60 에서도 그런가.",
    "죽는조건  n_dup 이 8,192 자세 전부 0 이면 분모는 깨끗하고 이 축은 닫힌다.",
    "        0 이 아니면 「지면이 올린 몫」이 최대 9.5 dB 틀릴 수 있다.",
    "⛔안답함  이것은 «새 답» 이 아니라 **감사**다 — 값이 그대로일 공산이 크다.",
    "⛔⛔--overwrite 는 백업을 안 만든다(elevation_sweep_md.py:768·932 이 같은 이름에 덮어쓴다).",
    "  ⇒ 굽기 전에 08-24 두 장을 따로 복사해 둔다. 안 그러면 «코드 세대가 값을 안 옮긴다» 를",
    "    보이는 유일한 옛 판이 사라진다. **그 복사를 안 했으면 이 줄을 띄우지 마라.**")
for k in range(NSH):
    line = (f"{BASE} --max-depth 2 --range-m 15 --sw {ARM} --els=-60"
            f" --shard {k} --nshards {NSH} --overwrite")
    _SEEN.add(line)
    OUT.append(line)

GROUPS.append(("끝", len(OUT)))
if "--summary" in sys.argv:
    n = sum(1 for x in OUT if x and not x.startswith("#"))
    print(f"발주 줄 {n} (샤드 나눔 포함)")
    for (t1, i1), (_t2, i2) in zip(GROUPS, GROUPS[1:]):
        c = sum(1 for x in OUT[i1:i2] if x and not x.startswith("#"))
        print(f"  {c:>3} 줄  {t1[:70]}")
    print("\n어림 — 빈 하늘 15 m 44 분 · 우리 씬 통째 136 분 · 거리 협곡 344 분")
    print(f"  A 6 × 44 = 4.4 h · B 2 × 136 = 4.5 h · C 4 × 344 = 22.9 h · D 2 × 44 = 1.5 h")
    print(f"  합계 어림 33 일꾼시간")
else:
    print("\n".join(OUT))
