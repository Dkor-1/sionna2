# -*- coding: utf-8 -*-
"""
make_jobs_0903b.py — 2026-09-03 에 파헤친 것에서 곧장 나오는 물음들을 잡 줄로 만든다.

무엇을 사는가
    오늘 갈린 것 —
      · 정면(el 0°)에서 **같은 줄이 여러 번 적힌다**. 그 횟수가 기체마다 다르다(2·3·4)
      · 횟수는 광선 예산(40 배)·거리(8 배)·자세·삼각형 넓이·메쉬 중복 어느 것도 안 따라간다
      · 빗각의 낙차는 **날개가 지나가며 가리는 것**(블록 간격이 날개 주기와 1.00 배)
      · 실외의 낙차는 **지면 정반사가 목록에서 빠지는 것**
    아직 못 답한 것 —
      ⓐ 그 횟수가 **방위**를 타나 (GATES_0902 는 az 0° 에서 3 → 9 라 적었다)
      ⓑ 정면 창이 얼마나 **좁은가** — el 0° 에는 있고 −4° 에는 없다. 그 사이가 비어 있다
      ⓒ 실외 낙차가 **판마다 같은가** — 실외에는 재실행 판이 한 장도 없다
      ⓓ 기체를 넓히면 횟수가 어떻게 되나 (s1000plus 는 한 값에 안 뭉쳤다)
      ⓔ 깊이를 바꾸면 횟수가 바뀌나

⭐새 샤드에는 `E_dedup`(같은 줄을 한 번만 센 합)과 `n_dup` 이 함께 적힌다 —
  그래서 **어떤 잡이든** 이 물음에 기여한다.

⛔지키는 것
  · 확산(F)은 **항상 켠다** — F0 계열을 발주하지 않는다
  · 프로펠러 단독(`--parts`)은 만들지 않는다
  · `--inmem` 은 기본값이라 줄에 안 적어도 된다(2026-08-29) — 그래도 명시해 둔다

쓰는 법
    CUDA_VISIBLE_DEVICES="" ~/.venvs/py312/bin/python runners/make_jobs_0903b.py > runners/jobs_0903b_new.txt
"""
from __future__ import annotations

import sys

SPP = 4_000_000_000
BASE = f"--engine sionna --spp {SPP} --n-poses 8192 --range-m 15 --inmem"
#: 다섯 팔 중 PathSolver 넷 — 확산은 넷 다 켜져 있다(F1)
SW4 = ["R0D0E0F1", "R1D0E0F1", "R0D1E1F1", "R1D1E1F1"]
#: 값싼 두 팔 — 축을 넓게 훑을 때 쓴다
SW2 = ["R0D0E0F1", "R0D1E1F1"]

out: list[tuple[str, str]] = []          # (묶음, 줄)


def add(tag: str, s: str) -> None:
    out.append((tag, s.strip()))


# ── ⓐ 방위 — 같은 줄이 적히는 횟수가 방위를 타나 ─────────────────────────
#    ⭐GATES_0902 가 az 0° 에서 3 → 9 라 적었다. 그 둘레를 촘촘히 본다.
for az in ("0", "1", "2", "5", "10", "22.5", "45", "67.5", "90"):
    for sw in SW2:
        add("ⓐ방위", f"{BASE} --sw {sw} --max-depth 2 --az-deg {az} --els=0")

# ── ⓑ 정면 창의 폭 — el 0° 에는 있고 −4° 에는 없다 ────────────────────────
for el in ("0.5", "1", "1.5", "2", "3", "4", "6"):
    for sw in SW2:
        add("ⓑ정면창", f"{BASE} --sw {sw} --max-depth 2 --els=-{el}")

# ── ⓒ 실외 재실행 — 실외에는 판이 한 장도 없다 ────────────────────────────
for rep in (1, 2, 3):
    for el in ("0", "-30", "-60"):
        add("ⓒ실외재실행",
            f"{BASE} --sw R0D0E0F1 --env outdoor01 --rep {rep} --max-depth 2 --els={el}")

# ── ⓓ 기체 — 횟수가 기체마다 다르다. 네 기체를 같은 자리에서 ──────────────
for dr in ("mavic4pro", "mini5pro", "s1000plus"):
    for sw in SW4:
        for el in ("0", "-15", "-30"):
            add("ⓓ기체", f"{BASE} --drone {dr} --sw {sw} --max-depth 2 --els={el}")

# ── ⓔ 깊이 — 횟수가 깊이를 타나 ───────────────────────────────────────────
for dep in (1, 3):
    for sw in SW4:
        add("ⓔ깊이", f"{BASE} --sw {sw} --max-depth {dep} --els=0")

# ── ⓕ 거리 — 횟수는 거리 무관으로 보였다. 정식으로 확인 ───────────────────
for rng in (30, 60, 120):
    for sw in SW2:
        for el in ("0", "-30"):
            add("ⓕ거리",
                f"--engine sionna --spp {SPP} --n-poses 8192 --range-m {rng} --inmem "
                f"--sw {sw} --max-depth 2 --els={el}")

# ── ⓖ 재실행 — 자유공간 낙차 칸도 판을 더 쌓는다 ──────────────────────────
for rep in (3, 4, 5):
    for sw in SW2:
        for el in ("0", "-15", "-45"):
            add("ⓖ재실행", f"{BASE} --sw {sw} --rep {rep} --max-depth 2 --els={el}")

# ── ⓗ 우리 커널 짝 — 같은 자리를 우리 엔진으로도 (비교축) ─────────────────
for dr in ("", "--drone mavic4pro", "--drone mini5pro", "--drone s1000plus"):
    for el in ("0", "-15", "-30", "-45", "-60", "-75"):
        add("ⓗ우리커널",
            f"--engine ours {dr} --max-depth 2 --range-m 15 --n-poses 8192 --inmem --els={el}")

# ── ⓘ 반송파 — 정반사 조건은 파장을 탄다. 횟수가 바뀌나 ──────────────────
#    ⭐24 GHz 는 λ 가 1/6.86 이라, 같은 면이 훨씬 «크게» 보인다.
for fc in ("24",):
    for sw in SW2:
        for el in ("0", "-15", "-30"):
            add("ⓘ반송파", f"{BASE} --sw {sw} --fc-ghz {fc} --max-depth 2 --els={el}")

# ── ⓙ 격자 — 우리 커널 el 0° 이 λ/12 에서 안 수렴한다(GATES_0902) ─────────
#    ⭐λ/24 를 사 두면 「el 0 레벨·폭 인용 금지」 단서를 풀 수 있다.
for div in (18, 24):
    for el in ("0", "-15", "-30", "-60"):
        add("ⓙ격자", f"--engine ours --div {div} --max-depth 2 --range-m 15 "
                     f"--n-poses 8192 --inmem --els={el}")

# ── ⓚ 표적 크기 — 정면 정반사가 크기를 어떻게 타나 ────────────────────────
for bs in ("0.6", "0.8", "1.2"):
    for sw in SW2:
        add("ⓚ크기", f"{BASE} --sw {sw} --body-scale {bs} --max-depth 2 --els=0")
        add("ⓚ크기", f"--engine ours --body-scale {bs} --max-depth 2 --range-m 15 "
                     f"--n-poses 8192 --inmem --els=0")

# ── ⓛ 표집률 — 날개 가림 블록의 길이가 표집을 타나 ────────────────────────
#    ⭐빗각 낙차가 «날개가 지나가는 것» 이면 PRF 를 올리면 블록이 길어져야 한다.
for prf in ("39400", "78800"):
    for sw in SW2:
        for el in ("-15", "-45"):
            add("ⓛ표집률", f"{BASE} --sw {sw} --prf {prf} --max-depth 2 --els={el}")

# ── ⓜ 방위 × 빗각 — 날개 가림이 방위를 타나 ──────────────────────────────
for az in ("0", "22.5", "45", "67.5"):
    for el in ("-15", "-45"):
        add("ⓜ방위빗각", f"{BASE} --sw R0D1E1F1 --az-deg {az} --max-depth 2 --els={el}")

# ── 샤드로 쪼갠다 — 한 줄이 너무 길면 워커가 오래 잡힌다 ──────────────────
SPLIT = 2
lines: list[str] = []
for tag, s in out:
    for k in range(SPLIT):
        lines.append(f"{s} --shard {k} --nshards {SPLIT}")

#: 값싼 것부터 — 큐가 앞에서 빨리 돌아 결과가 일찍 나온다
def cost(l: str) -> float:
    if "--engine ours" in l:
        return 13.1
    if "--env " in l:
        return 91.3
    return 55.9 if "D1E1" in l else 34.0


lines.sort(key=cost)

if sys.stdout.isatty():
    import collections
    c = collections.Counter(t for t, _ in out)
    tot = sum(cost(l) for l in lines) / SPLIT
    print(f"  묶음별 줄 수 (샤드 쪼개기 전): {dict(c)}", file=sys.stderr)
    print(f"  잡 줄 {len(lines)} · 예상 {tot/60:.0f} 워커·시", file=sys.stderr)
else:
    print("# 2026-09-03 추가 발주 — runners/make_jobs_0903b.py 가 지었다.")
    print("#  오늘 갈린 «같은 줄이 여러 번 적힌다» 를 방위·정면창·기체·깊이·거리로 넓힌다.")
    print("#  ⭐새 샤드에는 E_dedup·n_dup 이 함께 적히므로 어떤 줄이든 이 물음에 기여한다.")
    print("#  ⛔확산은 전부 켬(F1) · 프로펠러 단독 없음.")
    for l in lines:
        print(l)
