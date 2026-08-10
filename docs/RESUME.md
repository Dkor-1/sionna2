# ⚠오늘(2026-08-10) 한정 지시: **GPU 는 2번에 집중**한다 (사용자)
> 다른 카드로 분산하지 않는다. 여유 판정은 여전히 **메모리 기준**(util% 아님).
> 장기 방침([[sionna2-gpu-policy]] 의 «0~3 중 여유 있으면 다 침투»)은 내일부터 복귀.

# ⭐⭐세션 종료 대비 — 2026-08-10 08:4x KST (커밋 7cafee4 까지 푸시됨)

## 지금 도는 것: **없다**
GPU 작업·백그라운드 체인이 전부 끝났거나 멈췄다. 세션을 꺼도 잃을 계산이 없다.
⚠ 단, **덱 v4·v5 워크플로는 세션과 함께 죽는다**(진행 0, 산출물 없음 — 다시 띄우면 된다).
⚠ 10분 스냅샷 루프(docs/RESUME_LIVE.md)는 살아 있을 수 있다 — 무해하다.

## ⭐다음 세션에서 이어갈 것 (사용자 지시 순서)

### 1. 팀미팅 덱을 **한 주제로 다시 짓는다** — 사용자 최신 지시
> *"덱에 내용을 넣을 때는 **확실하게 교차검증**해서 넣고, 검증이 안 된 거면 **차라리 포기**하라.
>  **마이크로도플러 맵 · 거리별 분석 · SBR+PO 와 path solver 비교 이 하나만으로** 구성해도 된다.
>  단 청중은 **path solver 가 뭘 어떻게 해서 맵을 그렸는지 · SBR+PO 가 뭔지 · w/o occlusion 이
>  뭔 소리인지** figure 만 보고는 모른다."*
- 즉 RCS·조명원·5G·비행로그는 **뺀다**(부록 한 장 정도).
- ⭐**개념 설명 그림**을 새로 그려야 한다 — 세 엔진이 각각 «무엇을 쏘나 → 무엇을 세나 →
  무엇이 빠지나». 이게 이 덱의 성패다.
- ⭐덱에 넣을 **모든 수치를 원장에서 교차검증**하고, 검증 안 되면 버린다.
  ⚠특히 Sionna 의 p-p 는 거리마다 32.6/2.5/50.1 dB 로 요동한다(광선 표본화) → **수치 인용 불가,
  정성 서술만**. p5~p95 를 써라.
- 워크플로 스크립트가 이미 있다(재사용):
  `~/.claude/projects/-home-yunjung-workspace/…/workflows/scripts/deck-0811-v5-single-topic-wf_2569878d-108.js`
- 현재 최신 덱은 v3(본론 14장, 3부 구성) — `team_meeting/teammeeting_0811_v3.pptx` 로 **푸시됨**.
  v5 가 완성되면 같은 방식으로 `team_meeting/teammeeting_0811_v5.pptx` 로 올린다.

### 2. 리포트 78편 → **15권 통합** (진행 중, 절반 됨)
- ✅ 78편을 `reports/_parts/` 로 이동 · 빌더 12개 OUT 변경 · **셀 수 상한 규약 폐지**
  (사용자: «규약 상한 이런 거 만들지 마» — 그 규칙이 과잉 분할의 원인이었다)
- ✅ `src/build_volumes.py` 작성 — 15권 매핑·각주 재번호·권 머리말. **아직 실행 안 했다.**
- ⏳ 남은 일: 실행 → 검수 → `reports/README.md`·지도편 갱신 → 링크검사 → 커밋
- ⭐마이크로도플러는 «7번» 을 고집하지 않고 흐름상 제자리인 **8권**이다(사용자 지시).

### 3. 바이스태틱 마이크로도플러 새 리포트 (1단계만 됨)
- ✅ `src/rcs_sbr.py` 에 `sbr_field_bistatic` — **모노 회귀 게이트 144케이스 최대오차 0.0**
- ⚠ 발견: `rcs_sbr_multistatic` 은 Γ(θ) 를 **안 곱한다**(matk 를 받고도 미사용) → 신규 함수는 배선함
- ⏳ 남은 일: β 스윕 계산 → 기하 그림 → `report07b_microdoppler_bistatic.ipynb` 조립 → 검증
  (워크플로가 2단계에서 스키마 재시도 초과로 죽었다 — 스키마를 느슨하게 해서 다시 띄울 것)

### 4. ⭐3GPP ISAC 조사 결과를 반영한다 (조사 완료)
`prior_work/isac_standard_scenarios.md` · `outputs/isac_standard_scenarios.json` (1차자료 10건)
- ⚠**모순 정정**: `docs/DRONE_ISAC_PRIOR_READING.md:73` 이 −20 dBsm 을 «3GPP 합의 σ» 로 쓴다.
  실제는 **−12.81(소형)/−5.85(대형)**, −20 은 기고 단계 제안치다 → 정정 + 규격 대조 재계산
- 결손 5건: UAV large 갈래 · 모노=바이 동일값 규격 선례(우리 이등분선 근사의 방어논거) ·
  XPR · UMa-AV 시나리오 자체 · Rel-20 §9 결론
- ⭐논문에 쓸 새 논거 둘: 3GPP 스스로 **모노스태틱이 성능목표 3/11 만 만족**한다고 적었고,
  모노는 **자기간섭이 Tx 전력 상한**인데 패시브 바이스태틱엔 그 항이 없다

### 5. 남은 재계산·검증
- σ 격자: matrice4e 완료(07:13), **mini5pro 는 실패**(watcher cwd 오류) → 다시 돌릴 것
  `SIONNA2_GPU=2 PYTHONPATH=src python src/experiment_freespace_sigma.py --drone mini5pro --backend direct --force`
  ⚠prefill 백엔드는 GPU2 동시작업과 BrokenProcessPool — **반드시 direct**
- ⭐**광선 예산 결판 시험** 미완 — `benchmark/report07_ray_budget_test.py` (40 m 에서 규칙값 178M
  까지 사다리). 이게 «40 m 붕괴가 구조인가 예산 부족인가» 를 가른다. **덱에 40 m 슬라이드를
  넣으려면 이것부터**.
- σ 완료 후 편 59·60·61 재빌드(기체별 Γ(θ) 게이트가 새로 들어갔다 — 동작 확인)

## ⚠미해결 선언
- 40 m 붕괴의 «구조 vs 예산» 미분리 — 위 결판 시험 대기
- Γ(θ) 가 `rcs_sbr_multistatic`·다중반사 경로에 **미배선** → 바이스태틱 σ 는 서술과 다른 물리
- 우리 σ ↔ Das: 같은 기종·같은 구간에서 **2.39배**, z=9.6σ, 레벨 1.5~3.3 dB 낮음 (열린 문제)
- 패시브 2채널(기준·감시) 처리는 `src/passive_process.py` 에 있으나 헤드라인은 **이상적 기준신호**
  정합필터 SNR 을 쓴다 — 현실적 승격이 열린 과제

# 작업 현황 — 2026-08-10 06:0x KST  ⭐세션 종료 대비 최종판
> ✅사건 갱신5 (24b9539): **그림 12 완성** — 그림 3 거리판 3/8/15 m(Sionna 열만 재해,
> 기선 0, 경로중앙 5/13/6·빈자세 0%·레벨 −117→−148 dB; 8 m 초과보상 13경로 정직 기록).
> report07 = **셀 16 · 그림 13장**. 오늘 커밋 사슬: 676e448 → 7a6984f → bfd510e → f23f771 → 24b9539.
>
> 🔄세션이 꺼져도 계속 도는 것(전부 자동, 로그는 scratchpad/):
>   ① σ격자 m4e `--backend direct --force` (PID 101312, 04:26~ 출력버퍼링으로 sigma_m4e2.log
>      가 조용해 보여도 정상) → 끝나면 **watcher 가 σ mini5 direct 자동 시작**(sigma_force_mini5_direct.log)
>   ② 같은구간 RCS 스윕 (PID 84448) → outputs/rcs_same_span.json (matrice4e→mini5pro→phantom4)
>   ③ RESUME_LIVE.md 10분 스냅샷 루프(24h 자동종료)
> ⚠σ prefill 백엔드는 GPU2 동시작업과 BrokenProcessPool — **재시도는 반드시 direct 로**.
>
> ⏭다음 세션이 이어서 할 일(순서대로):
>   1. σ 완료 확인 → 편 59·60·61 재빌드(조건형 Γ(θ) 경고 자동소멸 확인) · SLOPE assert 걸리면 정합 라운드
>   2. rcs_same_span.json 생기면 → Das 사과-대-사과 기울기 보고 + 덱 1부 그림
>   3. 덱 v2 최종 확정 → sionna2/decks/ 복사+커밋(상시규칙) + team_meeting 경로지정 커밋
>   4. 후순위: freespace_range:496 라벨굳음 커널 수정+재계산 · 구 report03/04/05 복원 판단 ·
>      restruct_exec_plan 구제목 5건 · Lane D 무효화 목록의 mini5pro 파생물(report16 등) 재계산
> ✅사건 갱신4 (f23f771): 사용자 문답 3건 처리 — ①그림별 엔진 매핑(예외: 그림0 렌더·
> 그림2 Sionna↔PO 비교·그림4 08-07 PO 하드코딩) ②그림10 **4패널 축 통일**(0~0.3s·±2334Hz,
> 나이퀴스트=회색선, 빈 하양=측정불가 정직표시) ③그림11 야외/실내 프리셋 상세 설명.
> 그림3 "SBR+PO 가 왜 지저분하나" 답변: 가림 변조 7.5dB 가 진짜 신호, Sionna 의 깨끗함은
> 프롭 정반사 0 + 절대레벨 −60dB 의 착시. 🔄그림3 거리판(3/8/15m, 기선0) GPU2 계산 중
> (3m ✅ 경로5 · 8m 진행) → 완료 시 f12(3행×3열) + report07 절. 스크래치 gitignore 추가.
> ✅사건 갱신3: hover outdoor 완료(4.9분) → **f11 프리셋 비교 그림**(sitl vs 야외 2%/2.5%@1Hz —
> 야외는 능선이 얽힌 뱀, 플래시 아치는 양쪽 다 생존 = 시간분해능-우선의 물리 근거) →
> report07 **셀 15·그림 12장** 재빌드. σ m4e 는 옛 `--backend direct` 런(PID 101312, 04:26~)이
> 진짜로 돌고 있고(출력버퍼링으로 sigma_m4e2.log 0바이트), 내 prefill 체인 σ 는 둘 다
> BrokenProcessPool — **mini5 σ 를 direct 로 101312 종료 후 재체인 등록**. 라운드3 커밋 예정.
> ✅사건 갱신2 (05:1x): 에이전트② 완료 — 처방 41적용/6자동해소/2보류, HIGH 6 전건,
> **78편 재빌드·링크 441·출처 1,332·위반 0**. freespace_link:207 원버그 사망 확인,
> ⚠상류 라벨굳음 발견: src/experiment_freespace_range.py:496 하드코딩 eca_depth_db=60.0 →
> DNR>60 전 셀 limit="dpi_residual" 굳음(리포트 축은 인용 제거로 차단, 커널 수정은 팀미팅 뒤).
> ⚠기존 파손 발견: 구 report03/04/05 노트북 1셀 공동화 — paper doc 가드로 보존 처리.
> **라운드2 커밋 7a6984f 푸시됨.**
> ✅사건 갱신1 (05:0x): report15b 재계산(m4e Δ=0.000 재현·mini5pro SBR팔만 이동 F/G ±13dB) ·
> 에이전트①(f9·f10, report07 셀14/그림11) · f1~f4 재생성 · 덱 v2 슬라이드14 정정 재빌드.
> 🔄남은 것: σ체인(m4e 진행→mini5→hover outdoor)·같은구간 스윕(matrice4e ~10GHz).

> 이 문서는 **끝난 것 · 하는 것 · 할 것** 세 칸이다. 세션이 끊기면 여기부터 읽는다.
> ⭐ 라운드가 끝날 때마다 갱신한다. 10분 자동 스냅샷(프로세스·GPU·로그 후미)은
> `docs/RESUME_LIVE.md` (bash 루프, 24h 자동종료 — 수동 편집 금지). 팀미팅 **내일 8/11**.

---

## 0. ⭐⭐ 방향과 순서 — 두 가지 상시 규칙

### 메인 태스크
```
❌ 메인 아님   드론 RCS 를 정밀하게 계산한다
✅ 메인       드론 탐지  +  마이크로도플러 패턴으로 분류
```
σ 는 **기여가 아니라 인프라**다. «우리가 σ 를 정확히 냈다» 를 논문 주장으로 쓰지 않는다.
값어치를 내는 축은 σ 의 절대 레벨이 아니라 **구조** — 자세에 따른 변동(ε)·가림·블레이드 변조.

### ⭐ 작업 순서 — 상류부터
층을 그리고 **아래층부터** 끝낸다. 상류가 틀린 채로 하류를 돌리면 버릴 결과에 계산을 태운다.
```
1층  물리 커널   재질 Γ · PO/SBR 산란식 · 전처리 체인
2층  메쉬        기하 · 겹침 · 재질 배정
3층  재계산      σ 격자 · 마이크로도플러 (GPU)
4층  서술        리포트 · 그림      ← ⭐물리와 병행 가능(빌더가 JSON 을 읽는다)
5층  발표물      덱 · 논문
```
⛔ 결함을 **발견한 시점에** 층을 다시 세우고 순서를 갈아엎는다.

---

## 1. ✅ 최근 끝낸 것 (2026-08-10 — 상세는 docs/progress/2026-08-10.md, 커밋 676e448 푸시됨)

- **5갈래 스프린트 완주**:
  A 웹 실측 로터 앵커(`outputs/rotor_rpm_web_anchor.json` — 실내 0.54%/0.74%, 야외 2.4%/2.5%@0.74Hz,
    P3 DAT 2~6%; SITL ±0.22%는 대칭-이상 하한) ·
  B report07 재작성(§0 시나리오·그림별 이력표·설정 부록·조건형 서술) ·
  C 순수 PO Γ(θ) opt-in 배선(⭐정직한 음성: Sionna 일치 0.696→0.676, 확산 지배가 원인) ·
  D mini5pro 메쉬 참 무관통(블레이드루트 0.860mm 관통→벨 위 +0.165mm; 9기 비트동일;
    `mesh_check.check_prop_bell_solid` 솔리드 자 10/10) ·
  E 덱 v2(14슬라이드, JSON 수치주입, `teammeeting_0811/make_0811_v2.py`)
- **거리 스윕**(진짜 모노스태틱 기선0, spp∝(R/3)² 1M→32M): 경로 중앙 5/7/3/0 @ 3/10/20/40m,
  40m 빈자세 78.3% = PathSolver 구조 붕괴. SBR+PO 는 표적앵커 격자라 원거리장(8.3m) 밖 거리 불변.
- **5G 파형 4팔**: 풀캡처≡CW 2.4e-14 — 차이는 파형이 아니라 **반복률**(CRS 1kHz 팁 접힘·SSB 50Hz 플래시 접힘).
- **적대적 검증 78편**: 태그 1,277건 깨짐 0 · 발견 49건(HIGH 6) → `docs/REPORTS_ADVERSARIAL_0810.md`.
- report07_hover_long.py 에 산포 **프리셋 이원화**(sitl 기본/outdoor 웹앵커) — dict 만, CLI 배선 미완.

## 2. 🔄 하는 중 (끊기면 이 순서로 확인)

1. **GPU2 report15b 재계산** (PID 174223 — mini5pro 메쉬수정 반영, 2기×3자세, ~25분)
   로그 `scratchpad/md15b3_meshfix.log` → `outputs/report15b_microdoppler.{json,npz}` 덮음
2. **σ격자 --force 체인** (1 종료 대기 → m4e → mini5; 로그 sigma_force_*.log, 마커 sigma_chain.log)
   ⚠ 1차 시도는 GPU2 3작업 동시로 BrokenProcessPool — 순차 체인으로 전환
   ⚠ SLOPE_LEDGER_GAP assert(1.40) 는 설계된 멈춤 — 멈추면 의식적 정합, 상수 올리지 마라
3. **같은구간 RCS 스윕** (PID 84448, 2~18GHz×0.5·az360: matrice4e ~9.5GHz → mini5pro → phantom4)
   로그 `scratchpad/samespan.log` → `outputs/rcs_same_span.json` (완료 시 생성)
4. **에이전트① 그림**: `benchmark/build_range_sweep_fig.py`(f9)·`build_5g_fig.py`(f10) 신설
   + `src/make_report07_overview.py` 두 절 추가 + report07 재빌드
5. **에이전트② 처방**: 적대적 2단계 빌더 문자열(§3-B1 14항+HIGH 6) 적용 + 해당 편 재빌드
   + `check_report_links.py` + freespace_link.py:207 판정 보고

## 3. ⏳ 할 것 (상류부터)

1. 재계산 완료 → 그림 재생성(`build_report07_figs.py`·`build_three_engine_fig.py`·
   `build_hover_fig.py`·`build_flash_zoom.py`) → report07 재빌드
   (`PYTHONPATH=src ~/.venvs/py312/bin/python src/make_report07_overview.py`)
   → 덱 v2 재빌드(`cd teammeeting_0811 && python make_0811_v2.py` — 그림 재복사됨)
2. 덱 v2 낡은 줄: 슬라이드14 "mini5pro 프롭겹침 9.12% 먼저" → **수정 완료(솔리드자 0%)** 로.
   f9·f10 슬라이드 추가 검토(본론 상한 12~14, deckcount.py 로 세기)
3. ~~hover --preset/--tag CLI 배선~~ ✅배선 완료 + **체인 등록됨**(σ완료 마커 →
   `--preset outdoor` 자동 실행, 로그 hover_outdoor.log, 출력 report07_hover_long_outdoor.*)
   → 끝나면 fig7 실내/야외 2패널(md_mapstyle 준수·시간분해능 우선)
4. 같은구간 스윕 완료 → Das 0.21 dB/GHz 사과-대-사과 기울기 보고 + 덱 1부 반영
5. 에이전트 산출 검수 → 라운드 커밋·푸시(sionna2 는 add -A 안전; 완성 덱은 decks/ 복사 규칙)
6. mini5pro σ 이후: Lane D 무효화 목록(`outputs/meshfix_mini5pro_overlap.json`)의
   나머지 mini5pro 파생물(report16·anchor 계열) 재계산 — 다음 라운드

## 4. ⚠ 미해결 선언
- σ assert 멈춤 가능성(설계상 정상) — 발생 시 원장 정합 라운드 필요
- v1 덱 표지가 2026.08.04 로 찍혀 있음(빌더 _cover_base 재사용) — v2 는 패치됨, v1 방치
- freespace_link.py:207 커널 버그 여부 — 에이전트② 판정 대기
- 적대적 확인불가 2건 미판정
- 로터 산포 **헤드라인**을 야외 프리셋(2%/2.5%)으로 바꿀지 — 사용자 확인 전.
  지금은 sitl(±0.22%) 기본 유지, outdoor 는 추가 팔로 준비 중
