# -*- coding: utf-8 -*-
"""
make_jobs_0905.py — 2026-09-05 관찰에서 곧장 나오는 물음을 잡 줄로 만든다.

■ 오늘 갈린 것 (앞 큐 672 줄이 답한 것)
    ⭐⭐**같은 줄이 여러 번 적히는 현상은 «정확히 축 위» 한 점에서만 난다.**
      새 샤드의 `E_dedup`·`n_dup` 으로 305 장을 재니 N = |E| / |E_dedup| 이
        az 0°·el 0°  → **2.996**
        az 1·2·5·10° → **1.000**
        el −1·−2·−3·−4·−6·−15…−75° → **1.000**   (el +15·+30·+60 도 1.000)
      즉 「기체마다 2·3·4」보다 훨씬 좁은 말이다 — **한 점**이다.

■ 그래서 아직 못 답한 것
    ⓐ ⭐그 점이 **얼마나 좁은가.** 0° 와 1° 사이가 통째로 비어 있다. 폭이 0.1° 보다
      좁으면 덱이 말한 «0° 서든 드랍» 은 **측도 0 의 축 위 특이점**이고, 0.5° 쯤 되면
      호버링 자세 흔들림(바람·자세제어) 안에 들어와 **실제로 만나는 자리**가 된다.
      ⇒ 이 한 축이 «그 현상을 발표에 올릴 것인가» 를 정한다.
    ⓑ N 이 **기체의 대칭성을 세는가.** 옛 판의 2·3·4 는 축 위 한 점에서 잰 값이고
      기체 수가 셋뿐이었다. 일곱 기체를 같은 자리에서 다시 잰다.
    ⓒ 그 점에서 **깊이**를 바꾸면 N 이 바뀌나 (경로 사슬이 길어지면 겹침이 늘 것인가).
    ⓓ el 0 의 «레벨·폭» 인용 금지(GATES B1)를 **풀 수 있나** — λ/12 에서 안 수렴했다.
    ⓔ 실외 결론이 **el −30 한 칸**에서만 섰다(리포트 12). 다른 앙각·다른 팔에서도 서나.
    ⓕ 회절 켠 조합의 **깊이 3** 은 아직 열려 있다(EXPERIMENT_BACKLOG 416).
    ⓖ **위에서 내려다보는 판**(양의 앙각)은 칸당 10 장뿐이다.

⛔지키는 것
  · 확산(F)은 **모든 팔에서 항상 켠다** — F0 계열을 발주하지 않는다
  · 프로펠러 단독(`--parts`)은 만들지 않는다
  · `--inmem` 은 기본값이다(2026-08-29) — 줄에 안 적어도 된다
  · 리듬 몫의 **크기**는 이 줄들로도 인용하지 않는다(R29) — 순서만 읽는다

쓰는 법
    cd /workspace/sionna
    CUDA_VISIBLE_DEVICES="" python3 runners/make_jobs_0905.py > runners/jobs_0905.txt
    # 미리보기:  … runners/make_jobs_0905.py --summary
"""
from __future__ import annotations

import sys

SPP = 4_000_000_000
BASE = f"--engine sionna --spp {SPP} --n-poses 8192 --range-m 15"
#: PathSolver 네 팔 — 확산은 넷 다 켜져 있다(F1)
SW4 = ["R0D0E0F1", "R1D0E0F1", "R0D1E1F1", "R1D1E1F1"]
#: 값싼 두 팔 — 축을 넓게 훑을 때
SW2 = ["R0D0E0F1", "R0D1E1F1"]
#: 회절 켠 두 팔 — 깊이 축이 아직 열려 있는 쪽
SWD = ["R0D1E1F1", "R1D1E1F1"]

out: list[tuple[str, str]] = []


def add(group: str, line: str) -> None:
    #: 샤드 둘로 갈라 두 GPU 가 나눠 물게 한다(앞 큐와 같은 규약).
    for sh in (0, 1):
        out.append((group, f"{line} --shard {sh} --nshards 2"))


# ── ⓐ ⭐정면 창의 폭 — 이번 라운드의 머리 물음 ────────────────────────────
#    0° 와 1° 사이를 0.05° 부터 로그에 가깝게 촘촘히 깐다. 두 팔로 재서
#    «엔진 스위치가 아니라 기하» 라는 것도 함께 본다.
AZ_FINE = [0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 1.5, 3.0]
for az in AZ_FINE:
    for sw in SW2:
        add("ⓐ정면창-방위", f"{BASE} --sw {sw} --max-depth 2 --els=0 --az-deg {az}")

#: 앙각 쪽도 같은 사다리 — 두 축이 같은 폭인지 본다(대칭이면 같아야 한다).
EL_FINE = ["-0.05", "-0.1", "-0.2", "-0.3", "-0.5", "-0.7", "-1.5", "-3"]
for el in EL_FINE:
    for sw in SW2:
        add("ⓐ정면창-앙각", f"{BASE} --sw {sw} --max-depth 2 --els={el}")

#: 두 축을 **함께** 벗어나면 어떻게 되나 — 대각선 두 점.
for az, el in ((0.1, "-0.1"), (0.3, "-0.3")):
    for sw in SW2:
        add("ⓐ정면창-대각", f"{BASE} --sw {sw} --max-depth 2 --els={el} --az-deg {az}")

# ── ⓑ N 이 기체의 대칭성을 세는가 — 일곱 기체를 같은 자리에서 ─────────────
DRONES = ["matrice4e", "mini5pro", "mavic4pro", "phantom4",
          "s1000plus", "x500v2", "m350rtk"]
for dr in DRONES:
    for sw in SW2:
        add("ⓑ기체별-N", f"{BASE} --sw {sw} --max-depth 2 --els=0 --drone {dr}")

#: 창의 폭이 기체를 타나 — 둘째 기체로 방위 사다리를 짧게 한 번 더.
for az in (0.1, 0.3, 0.7):
    add("ⓑ기체별-창폭", f"{BASE} --sw R0D0E0F1 --max-depth 2 --els=0 "
                        f"--az-deg {az} --drone mini5pro")

# ── ⓒ 깊이가 N 을 바꾸나 ──────────────────────────────────────────────────
for d in (1, 2, 3):
    for sw in SW2:
        add("ⓒ깊이-N", f"{BASE} --sw {sw} --max-depth {d} --els=0")

# ── ⓓ el 0 격자 수렴 — «레벨·폭 인용 금지» 를 풀 수 있나 ──────────────────
#    ⛔`--div` 는 **우리 커널**의 표면 격자다. PathSolver 에는 그 축이 없다.
for div in (24, 48):
    for el in ("0", "-15"):
        add("ⓓ격자수렴", f"--engine ours --n-poses 8192 --range-m 15 "
                          f"--div {div} --els={el}")
#: 격자 위상 널 — 반 칸 이동이 el 0 만 −11.9 dB 였다(GATES B1). λ/24 에서도 그런가.
add("ⓓ격자수렴", "--engine ours --n-poses 8192 --range-m 15 "
                  "--div 24 --els=0 --grid-shift 0.5")

# ── ⓔ 실외 — 결론이 el −30 한 칸에서만 섰다 ──────────────────────────────
for rep in (1, 2, 3):
    for el in ("-60", "0"):
        add("ⓔ실외-재실행", f"{BASE} --sw R0D0E0F1 --env outdoor01 --max-depth 2 "
                             f"--els={el} --rep {rep}")
#: 둘째 팔로도 — 실외 판정이 엔진 스위치를 타는지 본다.
for rep in (1, 2):
    for el in ("-30", "-60"):
        add("ⓔ실외-둘째팔", f"{BASE} --sw R0D1E1F1 --env outdoor01 --max-depth 2 "
                             f"--els={el} --rep {rep}")

# ── ⓕ 회절 켠 조합의 깊이 3 (백로그 416 이 «아직 살아 있다» 고 적은 자리) ──
for sw in SWD:
    for el in ("0", "-15", "-30", "-60"):
        add("ⓕ회절-깊이3", f"{BASE} --sw {sw} --max-depth 3 --els={el}")

# ── ⓖ 위에서 내려다보는 판 — 칸당 10 장뿐이다 ────────────────────────────
for el in ("+15", "+30", "+60"):
    for sw in SW4:
        add("ⓖ양의앙각", f"{BASE} --sw {sw} --max-depth 2 --els={el}")


def main() -> int:
    if "--summary" in sys.argv:
        from collections import Counter
        c = Counter(g for g, _ in out)
        print(f"총 {len(out)} 줄 · 묶음 {len(c)}\n")
        for g, n in c.most_common():
            print(f"  {n:4d}  {g}")
        return 0
    print("# 2026-09-05 발주 — 정면 창의 폭이 머리 물음이다")
    print("#   앞 큐(672 줄)가 «N=3 은 az 0·el 0 한 점에서만» 을 냈다. 그 점의 폭을 잰다.")
    print("#   만든 것: runners/make_jobs_0905.py")
    last = None
    for g, line in out:
        if g != last:
            print(f"\n# ── {g} ──")
            last = g
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
