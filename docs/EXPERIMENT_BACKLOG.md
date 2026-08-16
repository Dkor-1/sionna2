# 실험 백로그 — ⭐큐가 마르면 이 문서를 연다

> **왜 있나.** 팀미팅 덱은 스냅샷이고 연구는 연속이다(2026-08-16 사용자 지시). 덱 분량은 정한 선에서
> 마감하되 **실험은 계속 이어간다.** 지금까지 큐가 빈 적이 두 번 있었고 그때마다 GPU 가 1~2 시간
> 놀았다. 이 문서가 그걸 막는다 — **다음에 넣을 줄이 항상 여기 준비돼 있다.**

**쓰는 법.** 큐 잔량이 워커 수의 두 배 밑으로 떨어지면 §0 「지금 바로 넣는 줄」 블록을 위에서부터
통째로 복사해 큐에 붙인다(Q1 → Q9 순서가 값어치 순이다). §0 이 바닥나면 §1 순위표에서 「언제 =
지금」 인 줄을 골라 발주줄을 만든다. 발주 전에 반드시 **§4 발주 금지 목록**과 **§5 함정**을 본다.
판독이 끝난 줄은 이 문서에서 지우지 말고 «✅판독 완료 + 원장 경로» 를 뒤에 붙여 남긴다 —
같은 것을 두 번 사지 않기 위해서다. 우선순위 잣대는 재미가 아니라 **미해결을 닫는 힘**이고,
같은 힘이면 **상류**(뒤에 영향 주는 것)와 **싼 것**이 먼저다.

**⭐법칙 교체를 견디는 기준.** 지금 층 1(메쉬 날 법칙·로터 프리셋)이 교체 대기 중이라, 교체 뒤
다시 사야 하는 실험을 지금 사면 두 번 일한다. 가르는 기준은 하나다 — **같은 메쉬를 쓰는 두 팔
사이의 상대 판정은 살아남고, 절대 레벨·정본 수치는 다시 재야 한다**(RESUME 「엔진 비교 결론은
안 흔들린다」 와 같은 논리). §0 의 줄은 전부 앞쪽(상대 판정)이라 지금 사도 안 버린다.
뒤쪽은 §2 「재계산 뒤」 칸에 모아 뒀다.

- 원장 정본: `outputs/*.json` · 진행 상태: `docs/RESUME.md` · 사전등록·설계: `docs/NEXT_EXPERIMENTS.md`
- 이 문서의 수치는 전부 **2026-08-16 저녁 기준 디스크 실측**이다(샤드 폴더·원장 직접 계산).

---

## 0. ⭐지금 바로 넣는 줄 (GPU 125 줄 ≈ 33 워커-시간 + CPU 2 줄)

### 0-A. 큐에 그대로 붙이는 줄 — 125 줄

전부 **오늘 그대로 돈다**(배관 필요 없음 · 이름 충돌 없음 · 디스크 실측으로 «그 칸이 아직 없다» 를
확인했다). 워커 8 개면 벽시계 4 시간쯤이다. `#` 로 시작하는 줄은 설명이니 **붙이기 전에 지운다**.

```text
# ── Q1. 격자 위상 널 — 「촘촘해서 변했나, 찍는 자리가 달라져서 변했나」 ── 13 줄 · ≈1.7 워커-시간
#   ⭐모든 실험의 판정 문턱인 ⓪ 격자 밴드의 정체를 가른다. 배선 게이트 17/17 PASS
#   (outputs/verify_grid_shift.json). 설계·판독법은 docs/GRID_PHASE_NULL.md.
#   ⭐법칙이 바뀌어도 이 판이 답하는 「귀속」은 같은 메쉬 A/B 라 다시 안 돌린다.
--engine ours --range-m 15 --n-poses 8192 --grid-shift 0.5 --els=0,-15,-30,-45 --shard 0 --nshards 4
--engine ours --range-m 15 --n-poses 8192 --grid-shift 0.5 --els=0,-15,-30,-45 --shard 1 --nshards 4
--engine ours --range-m 15 --n-poses 8192 --grid-shift 0.5 --els=0,-15,-30,-45 --shard 2 --nshards 4
--engine ours --range-m 15 --n-poses 8192 --grid-shift 0.5 --els=0,-15,-30,-45 --shard 3 --nshards 4
--engine ours --range-m 15 --n-poses 8192 --grid-shift 0.37,-0.19 --els=-15 --shard 0 --nshards 4
--engine ours --range-m 15 --n-poses 8192 --grid-shift 0.37,-0.19 --els=-15 --shard 1 --nshards 4
--engine ours --range-m 15 --n-poses 8192 --grid-shift 0.37,-0.19 --els=-15 --shard 2 --nshards 4
--engine ours --range-m 15 --n-poses 8192 --grid-shift 0.37,-0.19 --els=-15 --shard 3 --nshards 4
--engine ours --range-m 15 --n-poses 8192 --div 24 --grid-shift 0.5 --els=-15 --shard 0 --nshards 4
--engine ours --range-m 15 --n-poses 8192 --div 24 --grid-shift 0.5 --els=-15 --shard 1 --nshards 4
--engine ours --range-m 15 --n-poses 8192 --div 24 --grid-shift 0.5 --els=-15 --shard 2 --nshards 4
--engine ours --range-m 15 --n-poses 8192 --div 24 --grid-shift 0.5 --els=-15 --shard 3 --nshards 4
--engine ours --range-m 15 --n-poses 8192 --grid-shift 1.0 --els=-15 --shard 0 --nshards 16

# ── Q2. 셸 단독 두께 팔 — mini5pro · s1000plus ── 16 줄 · ≈2.8 워커-시간
#   ⭐「껍데기는 표적 축에 배선이 없다」가 matrice4e **한 기체**에서만 서 있다. 정본 서사의 기둥인데
#     기체 하나로는 못 세운다. 다른 둘은 셸·프롭을 함께 얇게 한 결합판뿐이라 분리가 원리적으로 불가능.
#   ⚠--prop-mm 은 **일부러 안 준다**(프롭을 100 mm 그대로 둬야 레벨 변화를 셸에 귀속할 수 있다).
#   대조군 이미 있음: sionna_p4000000000_{mini5pro,s1000plus}_r15_n8192_d1 (el −30)
--engine sionna --drone mini5pro --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --els=-30 --shell-mm 0.75 --shard 0 --nshards 8
--engine sionna --drone mini5pro --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --els=-30 --shell-mm 0.75 --shard 1 --nshards 8
--engine sionna --drone mini5pro --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --els=-30 --shell-mm 0.75 --shard 2 --nshards 8
--engine sionna --drone mini5pro --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --els=-30 --shell-mm 0.75 --shard 3 --nshards 8
--engine sionna --drone mini5pro --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --els=-30 --shell-mm 0.75 --shard 4 --nshards 8
--engine sionna --drone mini5pro --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --els=-30 --shell-mm 0.75 --shard 5 --nshards 8
--engine sionna --drone mini5pro --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --els=-30 --shell-mm 0.75 --shard 6 --nshards 8
--engine sionna --drone mini5pro --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --els=-30 --shell-mm 0.75 --shard 7 --nshards 8
--engine sionna --drone s1000plus --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --els=-30 --shell-mm 0.75 --shard 0 --nshards 8
--engine sionna --drone s1000plus --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --els=-30 --shell-mm 0.75 --shard 1 --nshards 8
--engine sionna --drone s1000plus --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --els=-30 --shell-mm 0.75 --shard 2 --nshards 8
--engine sionna --drone s1000plus --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --els=-30 --shell-mm 0.75 --shard 3 --nshards 8
--engine sionna --drone s1000plus --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --els=-30 --shell-mm 0.75 --shard 4 --nshards 8
--engine sionna --drone s1000plus --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --els=-30 --shell-mm 0.75 --shard 5 --nshards 8
--engine sionna --drone s1000plus --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --els=-30 --shell-mm 0.75 --shard 6 --nshards 8
--engine sionna --drone s1000plus --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --els=-30 --shell-mm 0.75 --shard 7 --nshards 8

# ── Q3. 굴절 켠 팔의 「셸만」 두께 칸 ── 8 줄 · ≈2.0 워커-시간
#   ⭐지금 굴절 팔의 두께 칸은 셸과 프롭을 **함께** 얇게 한 것뿐이라, H5 판이 사실은 셸 실험이 아니라
#     프롭 실험이었다. 다 끔 팔에는 셸만 칸이 셋(0.5·0.75·1.5) 있는데 굴절 팔에는 0 개다.
#   ⛔--max-depth 를 주지 마라 — 주면 이름에 _d1 이 붙어 기존 onlyrefr 팔과 갈린다(§5 함정 3).
--engine sionna --only refr --spp 4000000000 --range-m 15 --n-poses 8192 --els=-30 --shell-mm 0.75 --shard 0 --nshards 8
--engine sionna --only refr --spp 4000000000 --range-m 15 --n-poses 8192 --els=-30 --shell-mm 0.75 --shard 1 --nshards 8
--engine sionna --only refr --spp 4000000000 --range-m 15 --n-poses 8192 --els=-30 --shell-mm 0.75 --shard 2 --nshards 8
--engine sionna --only refr --spp 4000000000 --range-m 15 --n-poses 8192 --els=-30 --shell-mm 0.75 --shard 3 --nshards 8
--engine sionna --only refr --spp 4000000000 --range-m 15 --n-poses 8192 --els=-30 --shell-mm 0.75 --shard 4 --nshards 8
--engine sionna --only refr --spp 4000000000 --range-m 15 --n-poses 8192 --els=-30 --shell-mm 0.75 --shard 5 --nshards 8
--engine sionna --only refr --spp 4000000000 --range-m 15 --n-poses 8192 --els=-30 --shell-mm 0.75 --shard 6 --nshards 8
--engine sionna --only refr --spp 4000000000 --range-m 15 --n-poses 8192 --els=-30 --shell-mm 0.75 --shard 7 --nshards 8

# ── Q4. 얇은 셸 × 굴절 × 반사 깊이 3 — H5(투과 반대항)의 진짜 칸 ── 8 줄 · ≈1.5 워커-시간
#   ⭐예측이 부른 기제(껍데기를 뚫고 들어가 속 금속에 맞고 나옴)는 **깊이 1 에 배선 자체가 없다** —
#     두께 칸 11 개가 전부 깊이 1 이다. Q3 과 짝지으면 두께(100↔0.75 mm) × 깊이(1↔3) 2×2 가 완성된다
#     (나머지 두 칸은 이미 있다: onlyrefr el−30 · swR1D0E0F1_d3 el−30).
#   ⛔--only refr --max-depth 3 은 **조용히 깊이 1 로 돈다**(소스 실측, §5 함정 1). --sw 로 줘야 한다.
#   ⚠STANDARD_FRAME 밖 — 「별도 트랙」 꼬리표 필수.
--engine sionna --sw R1D0E0F1 --max-depth 3 --spp 4000000000 --range-m 15 --n-poses 8192 --els=-30 --shell-mm 0.75 --shard 0 --nshards 8
--engine sionna --sw R1D0E0F1 --max-depth 3 --spp 4000000000 --range-m 15 --n-poses 8192 --els=-30 --shell-mm 0.75 --shard 1 --nshards 8
--engine sionna --sw R1D0E0F1 --max-depth 3 --spp 4000000000 --range-m 15 --n-poses 8192 --els=-30 --shell-mm 0.75 --shard 2 --nshards 8
--engine sionna --sw R1D0E0F1 --max-depth 3 --spp 4000000000 --range-m 15 --n-poses 8192 --els=-30 --shell-mm 0.75 --shard 3 --nshards 8
--engine sionna --sw R1D0E0F1 --max-depth 3 --spp 4000000000 --range-m 15 --n-poses 8192 --els=-30 --shell-mm 0.75 --shard 4 --nshards 8
--engine sionna --sw R1D0E0F1 --max-depth 3 --spp 4000000000 --range-m 15 --n-poses 8192 --els=-30 --shell-mm 0.75 --shard 5 --nshards 8
--engine sionna --sw R1D0E0F1 --max-depth 3 --spp 4000000000 --range-m 15 --n-poses 8192 --els=-30 --shell-mm 0.75 --shard 6 --nshards 8
--engine sionna --sw R1D0E0F1 --max-depth 3 --spp 4000000000 --range-m 15 --n-poses 8192 --els=-30 --shell-mm 0.75 --shard 7 --nshards 8

# ── Q5. 두께 축 × 회절 켠 팔 ── 8 줄 · ≈5.9 워커-시간 (⚠회절 켠 칸은 다 끔의 3 배 비싸다)
#   ⭐두께 칸 17 개가 전부 「깊이 1 · 물리 끔」이라 회절을 켠 자리에서 두께가 무엇을 하는지 한 칸도 없다.
#     Sionna 소스가 UTD 쐐기 계수에도 두께를 물린다는 것은 확정인데(radio_material.py:1080-1090)
#     크기를 못 재서 「회절이 확산 바닥을 덮는다」의 매몰 간격이 +5.9 ~ +23.9 dB 로 넓게 열려 있다.
#   대조군 이미 있음: sionna_p4000000000_phys_r15_n8192_d1 (el −30). ⚠별도 트랙 꼬리표.
--engine sionna --physics --max-depth 1 --spp 4000000000 --range-m 15 --n-poses 8192 --els=-30 --shell-mm 0.75 --shard 0 --nshards 8
--engine sionna --physics --max-depth 1 --spp 4000000000 --range-m 15 --n-poses 8192 --els=-30 --shell-mm 0.75 --shard 1 --nshards 8
--engine sionna --physics --max-depth 1 --spp 4000000000 --range-m 15 --n-poses 8192 --els=-30 --shell-mm 0.75 --shard 2 --nshards 8
--engine sionna --physics --max-depth 1 --spp 4000000000 --range-m 15 --n-poses 8192 --els=-30 --shell-mm 0.75 --shard 3 --nshards 8
--engine sionna --physics --max-depth 1 --spp 4000000000 --range-m 15 --n-poses 8192 --els=-30 --shell-mm 0.75 --shard 4 --nshards 8
--engine sionna --physics --max-depth 1 --spp 4000000000 --range-m 15 --n-poses 8192 --els=-30 --shell-mm 0.75 --shard 5 --nshards 8
--engine sionna --physics --max-depth 1 --spp 4000000000 --range-m 15 --n-poses 8192 --els=-30 --shell-mm 0.75 --shard 6 --nshards 8
--engine sionna --physics --max-depth 1 --spp 4000000000 --range-m 15 --n-poses 8192 --els=-30 --shell-mm 0.75 --shard 7 --nshards 8

# ── Q6. PathSolver 정면 방위 곡선 — el 0 · az 22.5 · 67.5 · 90 ── 24 줄 · ≈6.3 워커-시간
#   ⭐「정면에서 동체 정반사가 지배할 때만 익사한다」의 PathSolver 쪽 근거가 방위 45° **한 점**이라
#     단조인지 널인지 주기인지 모른다(우리 커널은 el −30 에서 9 점 곡선을 가졌다). 이 24 줄이
#     0·22.5·45·67.5·90 다섯 점 곡선을 만든다(0 과 45 는 이미 있다).
#   ⛔나딧(el −90) × 방위는 죽은 축이라 발주 금지(§4).
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 22.5 --els=0 --shard 0 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 22.5 --els=0 --shard 1 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 22.5 --els=0 --shard 2 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 22.5 --els=0 --shard 3 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 22.5 --els=0 --shard 4 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 22.5 --els=0 --shard 5 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 22.5 --els=0 --shard 6 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 22.5 --els=0 --shard 7 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 67.5 --els=0 --shard 0 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 67.5 --els=0 --shard 1 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 67.5 --els=0 --shard 2 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 67.5 --els=0 --shard 3 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 67.5 --els=0 --shard 4 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 67.5 --els=0 --shard 5 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 67.5 --els=0 --shard 6 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 67.5 --els=0 --shard 7 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 90 --els=0 --shard 0 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 90 --els=0 --shard 1 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 90 --els=0 --shard 2 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 90 --els=0 --shard 3 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 90 --els=0 --shard 4 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 90 --els=0 --shard 5 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 90 --els=0 --shard 6 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 90 --els=0 --shard 7 --nshards 8

# ── Q7. PathSolver 빗각 방위 곡선 — el −30 · az 67.5 · 90 ── 16 줄 · ≈4.2 워커-시간
#   ⭐우리 커널이 el −30 에서 방위 9 점을 가진 자리를 PathSolver 는 2 점(0·22.5·45 중 일부)만 갖고 있다.
#     엔진 대 엔진을 같은 축에서 겨루려면 이 둘이 필요하다.
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 67.5 --els=-30 --shard 0 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 67.5 --els=-30 --shard 1 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 67.5 --els=-30 --shard 2 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 67.5 --els=-30 --shard 3 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 67.5 --els=-30 --shard 4 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 67.5 --els=-30 --shard 5 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 67.5 --els=-30 --shard 6 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 67.5 --els=-30 --shard 7 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 90 --els=-30 --shard 0 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 90 --els=-30 --shard 1 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 90 --els=-30 --shard 2 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 90 --els=-30 --shard 3 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 90 --els=-30 --shard 4 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 90 --els=-30 --shard 5 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 90 --els=-30 --shard 6 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 90 --els=-30 --shard 7 --nshards 8

# ── Q8. 굴절만 팔의 방위 곡선 마지막 점 — az 90 · el −30 ── 8 줄 · ≈2.0 워커-시간
#   ⭐굴절만 팔(= Sionna 공장 기본값 + 확산)에 az 0·22.5·45·67.5 는 있고 90 만 없다. 이 8 줄이
#     발표 서사로 쓰는 그 팔의 방위 곡선을 다섯 점으로 닫는다.
--engine sionna --only refr --spp 4000000000 --range-m 15 --n-poses 8192 --az-deg 90 --els=-30 --shard 0 --nshards 8
--engine sionna --only refr --spp 4000000000 --range-m 15 --n-poses 8192 --az-deg 90 --els=-30 --shard 1 --nshards 8
--engine sionna --only refr --spp 4000000000 --range-m 15 --n-poses 8192 --az-deg 90 --els=-30 --shard 2 --nshards 8
--engine sionna --only refr --spp 4000000000 --range-m 15 --n-poses 8192 --az-deg 90 --els=-30 --shard 3 --nshards 8
--engine sionna --only refr --spp 4000000000 --range-m 15 --n-poses 8192 --az-deg 90 --els=-30 --shard 4 --nshards 8
--engine sionna --only refr --spp 4000000000 --range-m 15 --n-poses 8192 --az-deg 90 --els=-30 --shard 5 --nshards 8
--engine sionna --only refr --spp 4000000000 --range-m 15 --n-poses 8192 --az-deg 90 --els=-30 --shard 6 --nshards 8
--engine sionna --only refr --spp 4000000000 --range-m 15 --n-poses 8192 --az-deg 90 --els=-30 --shard 7 --nshards 8

# ── Q9. PathSolver 방위 곡선 세 번째 앙각 — el −60 · az 22.5 · 67.5 · 90 ── 24 줄 · ≈6.3 워커-시간
#   ⭐Q6·Q7 과 합치면 PathSolver 방위 축이 「한 점」에서 **3 앙각 × 5 방위 면**이 된다 — 방위 의존이
#     단조인지 주기인지 앙각을 타는지가 그때 갈린다(RESUME 미해결 4).
#   ⭐덤 — 미해결 4 의 미귀속 칸(물리 켬 el −60 · az45 에서 리듬 15→28 %)의 **이웃**을 다 끔 팔에서
#     먼저 본다. 다 끔에서도 −60 의 방위 의존이 튀면 그것은 회절의 성질이 아니다.
#   대조군 이미 있음: sionna_p4000000000_r15_n8192_az45_d1 (el −60, 16 샤드 완결)
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 22.5 --els=-60 --shard 0 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 22.5 --els=-60 --shard 1 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 22.5 --els=-60 --shard 2 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 22.5 --els=-60 --shard 3 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 22.5 --els=-60 --shard 4 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 22.5 --els=-60 --shard 5 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 22.5 --els=-60 --shard 6 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 22.5 --els=-60 --shard 7 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 67.5 --els=-60 --shard 0 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 67.5 --els=-60 --shard 1 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 67.5 --els=-60 --shard 2 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 67.5 --els=-60 --shard 3 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 67.5 --els=-60 --shard 4 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 67.5 --els=-60 --shard 5 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 67.5 --els=-60 --shard 6 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 67.5 --els=-60 --shard 7 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 90 --els=-60 --shard 0 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 90 --els=-60 --shard 1 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 90 --els=-60 --shard 2 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 90 --els=-60 --shard 3 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 90 --els=-60 --shard 4 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 90 --els=-60 --shard 5 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 90 --els=-60 --shard 6 --nshards 8
--engine sionna --spp 4000000000 --range-m 15 --n-poses 8192 --max-depth 1 --az-deg 90 --els=-60 --shard 7 --nshards 8
```

**합계** — Q1 1.7 · Q2 2.8 · Q3 2.0 · Q4 1.5 · Q5 5.9 · Q6 6.3 · Q7 4.2 · Q8 2.0 · Q9 6.3
= **≈33 워커-시간**(125 줄). 비용은 원장 `seconds` 실측에서 뽑았다
(⚠GPU 경합 아래의 벽시계라 3 배까지 흔들린다 — 어느 설정이 더 비싼가를 이 수로 따지지 않는다).

⭐**우리 커널 방위 팔은 일부러 안 넣었다.** 지금 도는 큐가 바로 그 칸들(mini5pro·s1000plus ×
az 22.5·45·67.5 × 빗각)을 채우고 있다 — 이 문서를 쓰는 사이에도 12 칸이 새로 떨어졌다.
남는 구멍은 `ours_r15_n8192_az90` 의 빗각 세 점뿐이고, 그것도 같은 큐가 이어서 채울 자리다.
⇒ **§5-7 의 충돌 검사를 발주 직전에 반드시 한 번 돌린다.**

### 0-B. 쉘에서 바로 도는 CPU 명령 — ⛔큐에 넣지 말고 손으로 돌린다

```bash
# ⭐①  병합 — GPU 0. 지금 디스크에 **원장 밖 완결 칸이 34 개** 쌓여 있다(전부 8192 자세 완결).
#     방위 21 칸 · 거리 4 칸 · 회절 사다리 2 칸(1e9 d1/d3) · 기체 교차 칸이 여기 들어 있다.
#     이 한 줄이 순위 1·2·3 의 재료를 한꺼번에 원장에 올린다. 큐가 도는 중에 돌려도 안전하다
#     (덜 찬 칸은 n_missing 행으로 남고 다음 병합에서 덮인다).
cd /workspace/sionna && PYTHONPATH=src:benchmark \
  /workspace/.venvs/py312/bin/python benchmark/elevation_sweep_md.py --merge

# ⭐②  셸 두께 원장 만들기 — GPU 0. 셸 정본 0.75 mm 가 사람이 쓴 글 안에만 있고 원장이 없다
#     (직접 확인: outputs/m4t_wall_thickness.json 없음 · gmsh 미설치). 저장소 규율(원장+출처)에
#     어긋난 유일한 정본값이고, 지금 재질 라인의 GPU 발주 여러 건이 이 수를 인용한다.
/workspace/.venvs/py312/bin/python -m pip install gmsh
cd /workspace/sionna && PYTHONPATH=src:benchmark /workspace/.venvs/py312/bin/python \
  benchmark/measure_m4t_wall_thickness.py --step /workspace/M4T_v2.stp \
  --json outputs/m4t_wall_thickness.json
# (gmsh 없이 추정자만 검사하려면 --selftest. ⚠스크립트 기본 경로
#  assets/meshes/reference/matrice4-M4T_v2.step 에는 파일이 없다 — --step 을 반드시 준다)
```

---

## 1. 순위표 — 「언제 = 지금」

순위는 **닫는 힘**(이 실험이 어떤 미해결을 닫는가)으로 매기고, 같으면 상류성·비용 순이다.
「발주줄」이 §0 을 가리키면 그 블록을 그대로 복사하면 된다. ⛔선행 필요는 배관/코드가 먼저다.

| # | 제목 | 닫는 주장 | 언제 | 비용 | 발주줄 |
|---|---|---|---|---|---|
| 1 | 원장 밖 완결 칸 병합 | 방위·거리·회절 34 칸이 원장에 없어 아무 판정도 못 쓴다 | 지금 | GPU 0 · CPU 수 분 | §0-B ① |
| 2 | 회절 켠 팔의 광선 사다리 판독 | 회절이 얹는 −126 dB 바닥이 광선 표집 잡음이 아니라 결정론적 항인가 | 지금 | GPU 0(병합에 포함) | §0-B ① 뒤 CPU 판독 |
| 3 | 자세 수 사다리 판독 (R24) | 날개끝 상한 위 빗살이 자세 격자의 산물인가 — 「구조」라 부르던 자리의 이름 | 지금 | GPU 0 · CPU 수 분 | 원장 재독(칸 이미 있음) |
| 4 | 물리 켬 el −60 · 방위 45° 리듬 상승 재독 | 방위 수확의 유일한 미귀속 칸 — 「구조가 생김」↔「바닥이 걷힘」 | 지금 | GPU 0 · CPU 30 분 | 원장 재독(§0-A Q9 가 이웃 칸을 덤으로 준다) |
| 5 | `src/drones.py` 회전수 정정 4 건 | ⭐**재계산이 쓰는 입력**이다 — 안 고치면 전면 재계산을 두 번 한다 | 지금 | CPU 1~2 h | 코드 수정 + 특징 재생성 |
| 6 | 비틀림 법칙 바꾸기 전 플래시 폭을 커널로 직접 재기 | 감사가 스스로 조건으로 단 것 — 안 재고 바꾸면 근거 없는 수가 정본이 된다 | 지금 | 우리 커널 4 작업 ≈13 분 | 층 2 파일럿(별도 설계) |
| 7 | 팁 밴드 형상 오차의 스펙트럼 대가 | 표적 축에 직결되는데 한 번도 안 잰 유일한 자리 · 층 4 전면 재계산의 관문 | 지금 | ⛔`--blade-law` 배관 선행 + 8~16 작업 | ⛔선행 필요(§5 함정 4) |
| 8 | 실증 두 기체의 실물 프롭 1 차 출처 | 날 법칙 앵커를 「기종별 최선」으로 — 안 정하면 엉뚱한 프롭을 입힌다 | 지금 | GPU 0(실물·사진·문헌) | GPU 큐와 **동시 진행** |
| 9 | PO 커널 매몰면 이중계상의 σ 대가 | 절대 σ 와 기종 간 비교가 통째로 여기 걸린다 | 지금 | 우리 커널 PO 6 작업 ≈20 분 | ⛔판독 스크립트 신설 선행 |
| 10 | 로터마다 흔들림 크기를 다르게 | 실측이 반증한 모델 가정 · 5 와 같은 이유로 **재계산 입력** | 지금 | CPU 1 h | 프리셋 새 필드 |
| 11 | PathSolver 자신의 산포 밴드(씨앗만 바꾼 두 판) | ⭐PathSolver 판정이 **전부 남의 자 위에 서 있다** | 지금 | ⛔`--seed` 배관 + 16 작업 ≈2.8 h | ⛔선행 필요(§5 함정 2) |
| 12 | (11 과 **같은 발주**) 두께 팔과 같은 칸의 시드 복제 | 원장 두 곳에서 따로 제기됐을 뿐 설계가 같다 | 지금 | 11 에 통합 시 **추가 0** | 11 의 헤드라인 칸을 두께 팔 칸으로 |
| 13 | `outputs/m4t_wall_thickness.json` 원장 만들기 | 원장 없이 사람 글에만 있는 유일한 정본값 | 지금 | GPU 0 · CPU 수 분 | §0-B ② |
| 14 | `material_gamma_sweep` 에 matrice4e + 0.75 mm 등가 두 점 | 현행 유지(길 c)의 방어가 2 mm 판·matrice4e 부재로 비어 있다 | 지금 | 우리 커널 SBR 1 작업 ≈15 분 | ⛔스크립트 `DRONES_USED` 수정 선행 |
| 15 | 슬리버 법선 부호 흔들림(m2) · x500v2 동일평면 겹침(m4) | 감사가 「안 쟀다(추측)」로 남긴 두 자리 | 지금 | 우리 커널 PO 2~4 작업 ≈7~13 분 | 9 와 한 판에 묶어서 |
| 16 | 박자 축퇴의 정체 — 회전수 밴드 사다리 | 기종별 분류 성적이 물리인가 rpm 추정 오차인가 | 지금(5 직후) | CPU 1~2 h | `md_classify_dataset.py` 재빌드 |
| 17 | 격자 위상 널 | ⓪ 격자 밴드가 「수렴 안 됨」인가 「원래 이만큼 흔들리는 양」인가 | 지금 | 37 작업 ≈2.0 h | **§0-A Q1** |
| 18 | 셸 단독 두께 팔 — mini5pro · s1000plus | 「껍데기는 표적 축에 배선이 없다」를 한 기체에서 세 기체로 | 지금 | 16 작업 ≈2.8 h | **§0-A Q2** |
| 19 | 깊이 3 의 「+2 dB」를 물리와 표집으로 가른다 | 깊이 축의 마지막 갈래 · 못 가르면 「깊이 1 한정」 꼬리표가 영구 강제 | 지금 | ≈2.8 h | ⚠2 판독 뒤 범위 축소 · 별도 트랙 |
| 20 | 얇은 셸 × 굴절 × 깊이 ≥2 (H5 의 진짜 칸) | 철회를 확정 판정으로 바꾸는 유일한 칸 | 지금 | 8 작업 ≈1.5 h | **§0-A Q4** |
| 21 | 굴절 켠 팔의 「셸만」 두께 칸 | H5 판이 사실은 셸이 아니라 프롭 실험이었다 | 지금 | 8 작업 ≈2.0 h | **§0-A Q3** |
| 22 | 큰 프롭이 작은 프롭과 닮았는가 — 두께 축 확인 | 닮음이 깨지면 정본표 세 값이 통째로 흔들린다 | 지금 | GPU 0(기존 계측 파이프라인 재사용) | 8 과 동시 진행 |
| 23 | 스위치 완전요인의 앙각 축 | ⭐**정정 — 먼저 GPU 0 으로 읽어라**(§3 ①) | 지금 | 우선 CPU 0 · 남으면 32 작업 | ⚠아래 「순위 정정」 |
| 24 | `camera_assembly 0.85` 의 출처 | 총 σ 를 최대 1.81 dB 움직이는 최대 미검증 항인데 출처가 없다 | 지금 | 문헌 GPU 0 + 1 작업 ≈10 분 | 14 와 같은 스크립트 |
| 25 | PathSolver 방위 축이 사실상 한 점이다 | 「정면 익사」의 PathSolver 근거가 45° 한 점 — 단조인지 널인지 주기인지 모른다 | 지금 | 72 작업 ≈18.8 h | **§0-A Q6·Q7·Q8·Q9** |
| 26 | 두께 축 × 회절 켠 팔 | 「회절이 확산 바닥을 덮는다」의 매몰 간격이 넓게 열려 있다 | 지금 | 8 작업 ≈**5.9 h**(⚠아래) | **§0-A Q5** · 별도 트랙 |
| 27 | 다중 수신의 천장 — 각도 사이 요동 상관 길이 표 | 상한을 계산 없이 낸다 — **미래 지출을 막는** 항목 | 지금 | GPU 0 · CPU 수 분 | 원장 재독 |
| 28 | 셸 두께 실측이 Matrice 4T 한 기체뿐 | 「셸 0.75 mm」를 전 함대에 쓰는 근거의 범위 | 지금 | GPU 0(조사) → 확보 시 8 작업/기체 | 13 뒤 |
| 29 | 표적 없는 잡음 전용 팔 (R28) | −145 dB 가 계산 바닥인가 진짜 약한 에코인가 | 지금 | GPU 소액 | ⛔「표적 빼기」 배선 선행 |
| 30 | 「호버 전용」 딱지 + 기동용 2 성분 모델 | 모델에 원리적으로 배선이 없는 축을 선언한다 | 지금 | 딱지 GPU 0 · 모형 CPU 반나절 | 딱지부터 즉시 |
| 31 | DREGON · NeuroBEM 을 새 규약으로 다시 재기 | 옛 규약 수치와 새 규약 수치를 나란히 놓으면 안 되는 상태 | 지금 | GPU 0 · CPU 수 시간 | 원시 사본 이미 있음 |
| 32 | 표적 대역 × 표집률 ≥20 Hz 비행로그 확충 | 되돌아오는 시간(τ) 사다리의 절대 눈금이 ±30 % 열려 있다 | 지금 | GPU 0 · 반나절 | 선별기 개선 선행 |
| 33 | 흡수체 100 mm 가 챔버 절대 세기 주장에 남긴 것 | 두께 결함이 걸린 재질이 넷이 아니라 다섯이었다 | 지금 | **꼬리표만** GPU 0 | ⚠챔버는 통제군 — 재계산은 안 산다 |

### ⭐순위 정정 (이 백로그를 짜며 디스크·소스에서 새로 확인한 것)

1. **23 위(스위치 완전요인 앙각 축)는 GPU 5.6 시간을 살 필요가 없을 수 있다.** 수집본은 「회절 켠
   조합이 el −30 한 자리뿐」이라 했는데, 디스크 실측으로 **굴절 켠 D-뒤집기 짝이 이미 7 앙각에 있다** —
   `sionna_p4000000000_onlyrefr_r15_n8192`(=R1D0E0F1) ↔ `sionna_p4000000000_phys_r15_n8192_d1`
   (=R1D1E1F1, 소스 실측: `--physics` 는 확산을 안 끈다). 원장이 다른 앙각에 실어 둔
   `diffraction_scope_other_elevations` 는 굴절 **끈** 짝(R0)만 썼다. ⇒ **먼저 R1 짝으로 담김계수·
   매몰 깊이를 7 앙각에서 CPU 로 읽고**, 그래도 빈 자리가 있을 때만 발주한다.
2. **26 위 비용이 과소 계상이었다.** 회절 켠 칸은 다 끔의 약 3 배다(원장 실측: `phys_..._d1` 한 칸
   3.5~6.2 워커-시간 ↔ 다 끔 2.1). 1.4~2.8 h 가 아니라 **≈5.9 h** 로 잡아야 한다.
3. **1 위는 지금 그대로 도는 부분이 훨씬 크다.** 병합기가 상수 7 앙각만 도는 것은 맞지만, 미병합
   34 칸 중 **−52·−68·−82 의 7 칸만** 그 상수에 걸린다. 나머지 27 칸은 표준 앙각이라 **패치 없이
   지금 `--merge` 만 돌려도 들어온다.** ⇒ §0-B ① 을 먼저 돌리고, 앙각 3 점은 아래 한 줄 패치 뒤에.
4. **11·12 위와 7 위는 오늘 발주가 **불가능**하다** — 배관이 없다(§5 함정 2·4). 순위는 유지하되
   큐에는 못 넣는다. 배관은 각 10 분짜리 CPU 작업이고, **「인자를 안 주면 비트동일」 게이트**가
   필수다(이 저장소에서 가장 비싼 사고가 이름 겹침으로 인한 원장 오염이다).

**앙각 3 점을 살리는 한 줄 패치**(⛔이 문서는 제안까지 — 적용은 본체가 한다):
`benchmark/elevation_sweep_md.py:489` 의 `for el in ELS:` 를, 그 팔의 샤드 **파일 이름에서 읽은
앙각 집합**으로 바꾼다. 예 — `for el in sorted({float(re.search(r"_el([+-]\d+)_", os.path.basename(f)).group(1))
for f in glob.glob(f"{SHD}/{eng}_el*.npz")}, reverse=True):`. 상수 `ELS`(78 행)는 계산 쪽 기본값으로
그대로 두고 **병합 쪽만** 바꾼다.

---

## 2. 「재계산 뒤」 칸 — ⛔지금 사면 두 번 일한다

법칙(메쉬 날 법칙·로터 프리셋) 교체가 **절대 수치를 바꾸는** 자리다. 층 3 정본 전환 결정이 난 뒤에 산다.

| # | 제목 | 닫는 주장 | 비용 |
|---|---|---|---|
| 37 | 정본 프롭 두께 점 — mini5pro 0.80 · s1000plus 1.99 mm 직접 측정 | 감사가 「가장 큰 단일 실행가능 dB」로 지목 · 정본 1.43 을 Mini 5 Pro 에 쓰면 프롭 에코 +3.8~+4.6 dB 과대 | 16 작업 ≈2.8 h |
| 38 | 프롭이 어두워질 때 「날개끝 상한 위 몫」이 왜 오르나 (40.2° ↔ 64.5°) | 두께 사다리가 남긴 유일한 물리 의문 | GPU 0 · CPU 30 분(안 닫히면 8 작업) |
| 39 | 프롭 삼각형 크기가 파장에 안 묶여 있다 — PO 오차 미측정 | 큰 프롭 기체의 σ 신뢰도 | PO 6 작업 ≈20 분 |
| 40 | s1000plus 배경의 정체 — 「프롭만」 대조군 | 정본의 유일한 반증 칸 · 「카본은 두께 손잡이 밖」이 지금은 **추론**이다 (`material_canon_0816.open_ko`) | PathSolver 8 작업 ≈1.4 h |
| — | 정본 프롭 1.43 mm 의 el −15 칸 | 상한 위 몫이 +15.5 %p 튀고 박자가 움직이는 유일한 앙각을 정본으로 못 봤다 | 8 작업 ≈1.3 h |

⭐두께 정본 세 값(0.80 · 1.43 · 1.99 mm)은 **서로 독립 측정이 아니라 한 법칙 × 프롭 지름**이다
(세 값 전부 지름 × 0.005220). 법칙이 바뀌면 세 값이 함께 움직인다 — 그래서 이 칸들이 여기 있다.

## 3. 「실측 뒤」 칸

| # | 제목 | 닫는 주장 | 비용 |
|---|---|---|---|
| 34 | 바람 축 — 프리셋에 배선이 없다 | 실측 「흔들림[%] = 0.84 + 0.306 × 기울기[°]」와 문헌 「바람 1 m/s당 +0.52~1.09 %p」를 쓸 자리가 없다 | **지금 할 일은 실측 프로토콜에 한 줄**(풍속·풍향 동시기록) |
| 35 | 표적 3 기체의 실측 회전수 — 휴대기기 `.DAT` + 레이저 타코미터 | 「표적 3 기체 실측 rpm 0 건」을 닫는 유일한 비용 0 경로 | GPU 0 · 실기 |
| 36 | PSDK `ESC_DATA` 가 Matrice 4E 에서 실제로 나오는지 | 로터별 회전수를 50 Hz · 8 채널로 받는 유일한 공식 경로 · 열리면 35 가 불필요해지고 10 의 직접 근거가 생긴다 | GPU 0 · E-Port 결선 |

---

## 4. ⛔발주 금지 목록 — 왜 금지인지와 함께

다음 사람이 실수로 사지 않게 여기 모아 둔다. **큐에 넣기 전에 이 절을 본다.**

| 금지 | 왜 |
|---|---|
| ⛔**회절 spp-내리는 사다리**(R1, `--only diffr --spp 250000000/1000000000`) | 사전등록의 전제가 R17 로 깨졌다 — 「바닥이 광선 수에 반비례해 내려간다」의 앞 절반이 이미 거짓이다(물리 끔 팔에서 −0.07 dB/옥타브, 신뢰구간이 −3.01 을 안 덮는다). 예산 축으로는 「잡음이냐」를 못 가른다. **사전등록문을 다시 쓰기 전에는 안 붙인다.** 남은 판별력은 §0-B ① 병합이 GPU 0 으로 회수한다 |
| ⛔**나딧(el −90) × 방위** | 죽은 축이다 — 세 엔진 모두 \|ΔAC\| ≤ 0.01 dB. 직하방에서는 방위를 돌려도 같은 그림이 나온다 |
| ⛔**우리 커널에 두께 인자**(`--engine ours --shell-mm/--prop-mm`) | 스크립트가 막는다(`elevation_sweep_md.py:246`). 우리 커널에는 두께 개념이 없다(\|Γ\| 와 τ 뿐) — 그대로 두면 **이름만 다르고 내용이 같은 샤드**가 생겨 원장이 거짓말을 한다. 우리 쪽 두께 감도가 필요하면 `materials.MATERIALS['plastic']['gamma_po']` 를 바꾸는 별도 축으로 설계할 것 |
| ⛔**모서리 E 만 다른 칸**(`R0D0E1F0` 등) | E 는 회절 D 가 꺼지면 무동작이다(소스 실측 `sb_candidate_generator:338`). 이름만 다른 같은 판이 생긴다 |
| ⛔**표준 팔에 `--max-depth 3` 다시 태우기** | 표준 프레임 두 팔에서 깊이 1↔3 차이가 판독을 못 바꿀 만큼 작다는 것이 확정됐다(짝 7 개 리듬 몫 차 ≤0.40 %p · 빗살 대비 차 ≤0.21 dB). ⚠단 **회절 켠 조합**에서는 아직 살아 있다(19 위) |
| ⛔**챔버 장면 재계산** | 챔버는 통제군이고 기본 시나리오는 야외다(사용자 확정). 33 위는 **꼬리표만** 붙이고 GPU 는 안 산다 |
| ⛔**λ/96 격자** | λ/48 판독 전에는 사지 않는다. 17 위(위상 널)가 「촘촘함 대 표본 자리」를 가르면 여기서 지출을 끊는다 |
| ⛔**`--fc 5.8e9`** | 인자 이름이 `--fc-ghz` 이고 단위는 **GHz** 다. 설계서(NEXT_EXPERIMENTS §H)의 옛 표기를 그대로 치면 죽는다 — `--fc-ghz 5.8` |

---

## 5. 함정 — 발주 전 확인

1. ⛔**`--only refr --max-depth 3` 은 조용히 깊이 1 로 돈다.** 소스에서 `elif only:` 가지가
   `mdep = 3 if only == "depth3" else 1` 로 **깊이를 덮어쓴다**(`elevation_sweep_md.py:346-350`).
   그런데 이름에는 `--max-depth` 를 준 사실만 반영돼 `_d1` 이 붙으므로, 「깊이 3 을 샀다」고 믿는
   원장 행이 생긴다. **굴절만 × 깊이 3 은 `--sw R1D0E0F1 --max-depth 3` 으로 준다**(`--sw` 가지는
   `--max-depth` 를 그대로 쓴다). `--stock` 도 깊이를 3 으로 덮어쓴다.
2. ⚠**`--seed` 인자가 없다.** PathSolver 호출에 `seed=1` 이 하드코딩돼 있다(`:400`). 11·12 위
   (PathSolver 자기 산포 밴드)는 이 배관 없이는 발주 불가다.
3. ⚠**`--max-depth` 를 주면 이름이 갈린다.** 안 주면 `_d` 꼬리표가 안 붙는다. 기존 `onlyrefr` 팔은
   꼬리표가 없으므로, 같은 팔을 이어 사려면 **주지 마라**(Q3 이 그 이유로 안 준다).
4. ⚠**`--blade-law` 는 아직 스윕에 배관되지 않았다.** `src/drones.py:build_propeller(blade_law=…)`
   과 `src/drone_cad.py:BLADE_LAWS` 는 있지만 `elevation_sweep_md.py` 에는 인자가 없다(7 위 선행).
5. ⚠**샤드 수를 바꾸지 마라 — 이미 샤드가 있는 칸이면.** 새 칸은 아무 `--nshards` 나 되지만, 반쯤 찬
   칸에 다른 `--nshards` 로 이어 붙이면 같은 파일 이름에 다른 자세 묶음이 들어가 헷갈린다.
   §0-A 는 전부 **새 칸**이라 자유롭게 잡았다.
6. ⚠**`--els` 는 등호로 붙인다** — `--els=-30`. 띄어 쓰면 argparse 가 `-30` 을 인자 이름으로 읽는다.
7. ⭐**발주 직전 이름 충돌 검사** — 큐가 도는 동안 칸이 계속 떨어지므로, §0-A 를 붙이기 전에 한 번 돌린다.
   같은 이름이 이미 있으면 스크립트가 건너뛰므로 사고는 안 나지만 **줄을 헛되이 채운다**.
   ```bash
   cd /workspace/sionna && ls outputs/elev_sweep_shards/ \
     | sed -E 's/_el[+-][0-9]+_[0-9]+\.npz$//' | sort -u \
     | grep -E 'shift|shell0\.75mm|_az(22\.5|67\.5|90)'
   ```
   나오는 팔 이름이 §0-A 가 만들려는 것과 겹치면 그 블록은 **빼고** 붙인다.
8. ⚠**메꿀 구멍 하나**(발주 전 확인 필요): `ours_r15_n8192_az90 / el −30` 이 2 샤드 중 **1 개만**
   있다. 큐가 지금 돌고 있는 칸일 수 있으니, 워커가 잡고 있지 않은 것을 확인한 뒤에만
   `--engine ours --range-m 15 --n-poses 8192 --az-deg 90 --els=-30 --shard 1 --nshards 2` 를 넣는다.
9. ⚠**병합 결과를 인용하기 전에 `n_missing` 을 본다.** 덜 찬 칸은 0 이 아닌 값으로 남고, 빗살 대비는
   샤드 완결에 민감하다(08-16 아침에 병합 전 부분집합으로 낸 수가 약 4 dB 낮게 나왔다).

---

## 6. 값어치를 매긴 잣대 (다음 사람이 순위를 다시 매길 때)

- **닫는 힘** — 이 실험이 없으면 못 쓰는 문장이 몇 개이고 그 문장이 어디까지 퍼져 있나.
  서술 층(리포트·덱)에 이미 실린 문장을 떠받치는 것이 가장 세다.
- **상류성** — 뒤의 실험이 이 결과를 기다리나. 층(커널 → 메쉬 → 재계산 → 서술 → 발표물)에서
  아래층일수록 먼저다. 5·10 위가 GPU 를 안 쓰는데도 앞에 있는 이유다.
- **비용** — 워커-시간. 같은 힘이면 싼 것이 먼저이고, **GPU 0 인 것은 GPU 작업과 동시에** 굴려
  큐를 안 막는다(8·13·22·27·28 위).
- **법칙 내성** — §머리의 기준. 다시 사야 하는 것은 §2 로 내린다.
