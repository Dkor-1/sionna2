# -*- coding: utf-8 -*-
"""
make_jobs_0906.py — 0905 판 188 줄이 답한 것에서 곧장 나오는 물음들.

■ 0905 큐(188 줄 · 실패 0)가 답한 것
    ⭐**정면 창의 폭이 나왔다** — 두 축 모두 **0.2° 에서 절벽**이다.
        방위  0° 3.00 · 0.05° **4.97** · 0.10° 2.59 · ≥0.20° 1.000
        앙각  0° 3.00 · −0.05° 2.71 · −0.10° 1.76 · ≤−0.20° 1.000
      ⇒ 창은 **1° 보다 훨씬 좁다.**
    · 양의 앙각(+15·+30·+60°)은 전부 N=1.000 — el 0 만 특별하다.
    · 깊이 1 N=2.68 · 깊이 2 N=3.00 — 깊이가 조금 움직인다.
    · 기체: matrice4e 2.675 · phantom4 1.000 · x500v2 1.002 · m350rtk 1.000.

■ ⛔0905 가 못 답한 것 — 그리고 왜 못 답했나
    **mini5pro · mavic4pro · s1000plus 는 답이 없다.** 샤드는 100·52·110 장인데
    `n_dup` 이 든 것이 **0 장**이다 — 스크립트가 `os.path.exists(f) and not overwrite` 로
    **옛 세대 샤드를 보고 건너뛴다.** 이름이 같으니 새로 안 돈 것이다.
    ⇒ 이번에는 그 셋에 **`--overwrite`** 를 준다.
    ⚠«중복은 공짜» 는 절반만 맞다 — 옛 세대가 있으면 새 물음이 **조용히** 안 풀린다.

■ 이번에 사는 것
    ⓐ ⭐**방위 0.05° 의 튐** — N 이 축 위(3.00)보다 높은 4.97 이 나왔는데 샤드 4 장이다.
      0.02~0.15° 를 촘촘히 깔고 샤드를 늘려 그 봉우리가 진짜인지 본다.
      (앙각 쪽은 단조로 내려가는데 방위만 튄다 — 두 축이 다르게 죽는다.)
    ⓑ ⭐**기체 셋을 --overwrite 로 다시** — 「기체마다 2·3·4」가 재현되는지.
    ⓒ **창이 거리를 타나** — 지금 전부 15 m 다. 기하/대칭이면 거리에 안 움직여야 하고,
      광선 밀도의 성질이면 움직인다. 30·60 m 에서 같은 사다리를 짧게 깐다.
    ⓓ **창이 광선 예산을 타나** — spp 를 1/4 로, 4 배로.
    ⓔ **깊이 3 에서 N** — 지금 깊이 3 은 `n_dup` 이 든 샤드가 0 장이다.
    ⓕ **창 안에서 실제로 낙차가 나나** — N=3 인 자세에서 |E| 가 떨어지는지가 덱의
      «0° 서든 드랍» 과 이 현상을 잇는 고리다. 자세를 4 배로 늘려 통계를 두껍게 한다.

⛔지키는 것 — 확산(F)은 항상 켠다 · 프로펠러 단독 안 만든다 · `--inmem` 은 기본값

쓰는 법
    cd /workspace/sionna
    CUDA_VISIBLE_DEVICES="" python3 runners/make_jobs_0906.py > runners/jobs_0906.txt
    CUDA_VISIBLE_DEVICES="" python3 runners/make_jobs_0906.py --summary
"""
from __future__ import annotations

import sys

SPP = 4_000_000_000
BASE = f"--engine sionna --spp {SPP} --n-poses 8192 --range-m 15"
SW2 = ["R0D0E0F1", "R0D1E1F1"]          # 값싼 두 팔 — 확산 켬
out: list[tuple[str, str]] = []


def add(group: str, line: str, shards: int = 2) -> None:
    for sh in range(shards):
        out.append((group, f"{line} --shard {sh} --nshards {shards}"))


# ── ⓐ ⭐방위 0.05° 의 튐 — 봉우리가 진짜인가 ──────────────────────────────
#    축 위(3.00)보다 높은 4.97 이 샤드 4 장에서 나왔다. 촘촘히 + 두껍게.
for az in (0.02, 0.03, 0.05, 0.07, 0.10, 0.15):
    for sw in SW2:
        add("ⓐ방위봉우리", f"{BASE} --sw {sw} --max-depth 2 --els=0 --az-deg {az}", shards=4)

#: 앙각 쪽도 같은 자리를 촘촘히 — 두 축이 정말 다르게 죽는지 확인한다.
for el in ("-0.02", "-0.03", "-0.07", "-0.15"):
    for sw in SW2:
        add("ⓐ앙각대조", f"{BASE} --sw {sw} --max-depth 2 --els={el}", shards=2)

# ── ⓑ ⭐기체 셋 — 옛 샤드를 덮어써야 답이 나온다 ─────────────────────────
for dr in ("mini5pro", "mavic4pro", "s1000plus"):
    for sw in SW2:
        add("ⓑ기체-덮어쓰기",
            f"{BASE} --sw {sw} --max-depth 2 --els=0 --drone {dr} --overwrite", shards=2)
#: 창의 폭도 기체를 타는지 — 답이 나온 기체 하나로 방위 사다리를 짧게.
for az in (0.05, 0.10, 0.20):
    add("ⓑ기체-창폭",
        f"{BASE} --sw R0D0E0F1 --max-depth 2 --els=0 --az-deg {az} --drone mini5pro --overwrite")

# ── ⓒ 창이 거리를 타나 ───────────────────────────────────────────────────
for rng in (30, 60):
    for az in (0.0, 0.05, 0.10, 0.20):
        line = (f"--engine sionna --spp {SPP} --n-poses 8192 --range-m {rng} "
                f"--sw R0D0E0F1 --max-depth 2 --els=0")
        add("ⓒ거리", line + (f" --az-deg {az}" if az else ""))

# ── ⓓ 창이 광선 예산을 타나 ──────────────────────────────────────────────
for spp in (1_000_000_000, 16_000_000_000):
    for az in (0.0, 0.05, 0.10):
        line = (f"--engine sionna --spp {spp} --n-poses 8192 --range-m 15 "
                f"--sw R0D0E0F1 --max-depth 2 --els=0")
        add("ⓓ광선예산", line + (f" --az-deg {az}" if az else ""))

# ── ⓔ 깊이 3 에서 N (지금 n_dup 든 샤드 0 장) ────────────────────────────
for sw in SW2:
    add("ⓔ깊이3", f"{BASE} --sw {sw} --max-depth 3 --els=0 --overwrite")

# ── ⓕ 창 안에서 실제로 낙차가 나나 — 자세를 4 배로 ───────────────────────
for az in (0.0, 0.05):
    line = (f"--engine sionna --spp {SPP} --n-poses 32768 --range-m 15 "
            f"--sw R0D0E0F1 --max-depth 2 --els=0")
    add("ⓕ두꺼운자세", line + (f" --az-deg {az}" if az else ""), shards=4)


def main() -> int:
    if "--summary" in sys.argv:
        from collections import Counter
        c = Counter(g for g, _ in out)
        print(f"총 {len(out)} 줄 · 묶음 {len(c)}\n")
        for g, n in c.most_common():
            print(f"  {n:4d}  {g}")
        return 0
    print("# 2026-09-06 발주 — 0905 가 낸 «창의 폭» 에서 이어지는 물음")
    print("#   ⭐방위 0.05° 의 봉우리(N=4.97)가 진짜인가 · 기체 셋은 --overwrite 로 다시 산다")
    print("#   만든 것: runners/make_jobs_0906.py")
    last = None
    for g, line in out:
        if g != last:
            print(f"\n# ── {g} ──")
            last = g
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
