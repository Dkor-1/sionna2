# 재개 지점 — 2026-08-03 09:50

> **새 세션은 이 문서부터 읽는다.** 날짜별 재개 문서는 과거 기록이다.
> ⛔ **GPU 작업은 유지한다** — 세션이 끊겨도 `benchmark/rcs_anchor.py`(PID 1364837)는 죽이지 않는다.

---

## ⭐⭐⭐ 09:50 헤드라인 — 오늘의 두 결과

### A. Phantom 3 눈감기 검증 — **좋다** (`outputs/p3_ours.json`)

정답(Das 0.21 / −19.19)을 봉인한 채 사진·스펙만으로 메쉬를 만들고 σ 를 냈다.
**el=0(θ=90 수평면) · 방위 전주기 360점 · 1.8~18.2 GHz 21주파수 · 런타임 14,542 s:**

```
                기울기 a [dB/GHz]     레벨 b [dBsm]
우리              +0.4198              −21.79      (R²=0.68, rmse 1.43)
Das 실측          +0.21                −19.19
                   2.00 배               −2.60 dB
```

⭐ 기울기 **2.00배**는 다른 기체의 같은구간 재적합 **2.07배**와 일치한다. 우연이 아니다.

⭐⭐⭐ **격차의 원인이 규명됐다 — μ(f) 가 직선이 아니다:**
```
1.8 ~ 6   GHz   a = +1.563   R² = 0.96     ← 가파르다
6   ~ 18.2 GHz   a = +0.199   R² = 0.33     ← ⭐ Das 0.21 과 사실상 일치(비 0.95)
전대역           a = +0.420   R² = 0.68     ← 둘의 절충
```
**고주파 절반은 실측과 맞고, 격차가 전부 저주파에 있다.** 저주파 = ka 작음 = PO 가 지는 곳
(구에서 이미 정량화: 정확 Mie 대비 kr=1 에서 6.729 dB).
⚠ 단 Das 는 전대역 직선 하나를 적합한다. **정본 비교는 전대역 대 전대역 = 2.00배**이고,
부분대역 이야기는 **설명**이지 더 나은 비교가 아니다.
⚠ 고도 의존이 크다 — a 가 el 에 따라 **−0.157 ~ +0.484**(부호까지 바뀜), μ 의 고도간 산포 최대 **11.97 dB**.
⏳ **큐브·박스 대조군과 눈감기 감사는 아직** — 워크플로 3/7. **그게 진짜 판정이다.**

### B. 급소 실험 — **참인데 이름표가 틀렸다** (`outputs/tm_result.json`, `tm_attack.json`)

`shape_matters: true` · `verdict: REAL` · 재실행 편차 **0.00 dB** · 1,080 자세 · 5 환경.

> *"무너지는 것은 숫자가 아니라 **이름표**다 — 재는 것이 '형상' 이 아니라 **'σ 분포의 폭'** 이고,
> 헤드라인 낙차의 소유자는 우리 모형이 아니라 **우리가 치수를 정한 정육면체**다."*

```
순서   M1(통계 RCS) < M3(우리 σ) < M2(정육면체)      21/21 셀 전부 불변
소유   105개 환경×셀 전부에서 max = M2, min = M1.  ⚠ M3 는 낙차의 20~33% 만
크기   기하평균 14.65 · 중앙값 16.01 · 선형평균 29.30(헤드라인) · p95 33.71 · 최대 43.97 dB
       ⚠⚠ 검출기가 실제로 읽는 p10 에서 맞추면 **2.30 dB 로 붕괴하고 순서가 뒤집힌다**
       (헤드라인은 선형평균 일치 + 앙상블평균 Pd=0.9 로 **젠슨 격차를 두 번 센다**)
```

⚠⚠ **내 가설이 반증됐다.** 나는 *"다중경로가 풍부할수록 표적모형 오차가 커진다"* 고 했다. **반대다:**
```
환경의 각다양성이 차이를 지운다:  N_eff 1.0 → 3.8 에서  29.3 → 10.1 dB
가장 민감한 환경 = E0 자유공간
```

⭐ **Sionna 의 자리**: *"표적 산란이 아니라 **환경 축만** 진다 — 경로쌍 사다리에서 N_eff·각퍼짐·β 를
만들고 환경 의존 판정 전체가 그 위에 선다."* ⚠ 위험: 설치본 기본값 `diffraction=False` 가 N_eff 과소평가.

⚠⚠ **선행 충돌 1순위 — RadarTwin** (arXiv 2606.28396v1, 프리프린트):
방 전체 4바운스 광선추적 + 실물과 동일 OBJ. ***"물체단독 시뮬은 실측과 반상관(−0.24),
환경포함은 +0.42"* 를 이미 인쇄해 우리 "환경 필요" 논지를 선점했다.**
남은 것: 77 GHz FMCW 모노스태틱이고 **PO 면적분·절대 dBsm·Pd 곡선이 없다.** → 정독 중.

⚠ **M3(우리 팔)는 아직 인쇄 못 한다** — *"σ 전격자 재생성 뒤 확인 대기
(stale↔current 패턴 상관 0.05~0.56)"*. → §9 · 재생성 진행 중.

---

## ⭐ 저주파 격차의 원인 가르기 (진행 중, `w5wlytle2`)

**용의자 A — 격자가 λ 상대라 저주파에서 형상을 못 본다. 고칠 수 있다.**
```
             격자 d=λ/12    암(26.5mm) 가로지르는 광선     블레이드 코드(25mm)
1.8  GHz     13.88 mm            1.9 개  ⚠⚠                  1.8 개
3.5  GHz      7.14 mm            3.7                          3.5
18.2 GHz      1.37 mm           19.3  ✅                      18.2
```
**용의자 B — PO 타당조건 위반. 못 고친다.** 1.8 GHz 에서 암/λ = **0.16**, 블레이드/λ = 0.15
(PO 는 국소 곡률반경 >> λ 를 요구). 크리핑파·표면파도 PO 엔 없다.

⭐ **결정 실험**: 1.8 GHz 를 격자 **절대값 고정**(1.37 mm)으로 다시 돌린다.
σ 가 크게 변하면 A(고칠 수 있음), 안 변하면 B(근본).
+ 해석해 앵커(PEC 구 저 ka · 폭 0.15λ 얇은 판)로 같은 진단.
⚠⚠ **A 로 판정되면 지금까지 낸 모든 저주파 σ(LTE 1.843 GHz 포함)가 영향받는다.**

---

## ⚠ GPU 방침 — 내가 어겼다 (2026-08-03 09:47)

`nvidia-smi` util% 100% 를 보고 "여유 없음" 이라 판단했는데, **우리 자체 방침이 반대다:**
> `src/gpu.py:6` — *"**메모리 여유가 판단 기준**이다. 사용률(util%)은 참고만 한다"*

그때 실제 여유: **GPU3 24,563 MiB(완전 유휴)** · GPU2 14,856 · GPU0 4,957 · GPU1 1,478.
CPU load **6.03 / 64 코어**.
⭐ **규칙: 2 GB↑ 여유면 들어간다. 유휴카드 메모리 90% 목표. 찔끔 쓰지 않는다.
nvidia-smi 를 계속 보며 배치를 실시간 조절한다.**

---

## 0. ⭐⭐ 오늘의 프레임 (변경 없음, 재확인)

```
❌ 틀렸던 프레임 :  "Sionna 로 드론 σ 를 낸다"
✅ 옳은 프레임   :  σ 는 우리 커널(Mitsuba + PO)이 낸다.  Sionna 는 환경을 낸다.
                    레이다 방정식에서 원래 분리되는 양이다
```

| 담당 | 무엇 | 왜 |
|---|---|---|
| **우리 메쉬 + PO 커널** | σ 의 **각도 구조 · 가림** | 다중경로가 각도 구조를 요구. 가림이 11~40 dB |
| ⚠ **실측** | σ 의 **절대 레벨** | 메쉬로는 검증 불가 |
| **Sionna** | 환경 · 다중경로 · 유령 | 클러터 서베이가 16 dB 로 값어치 증명(⚠ 유도값) |

⛔ 메쉬 미세 정밀화(나사·배선·mm급) **중단**. ⛔ 상용 솔버(FEKO/CST) **구매 불필요**
(솔버 오차 0.85 dB 를 사려고 메쉬 오차 ≥2.7 dB 를 남긴다).

---

## 1. ⭐ 오늘 확정 (전부 원문·코드 확인)

### 1-1. 주입 아키텍처는 **탑베뉴 게재** — 입장료는 **검증**

| 논문 | 게재처 | 무엇으로 검증했나 |
|---|---|---|
| Zhang 외 | **IEEE JSAC 44 (2026) p.702**, DOI 10.1109/JSAC.2025.3608732 | held-out 대역 + 금속구 |
| ⭐ **Deep 외** | **IET Radar Sonar Nav. 2020**, doi 10.1049/iet-rsn.2019.0471 | 77 GHz 실장비, NMSE<10%, SSIM>81% |
| Costa 외 | **IEEE J-STEAP 2025** | BiRa 대조 |
| Das 외 | **IEEE WCL 15 (2026) p.3731**, DOI 10.1109/LWC.2026.3705634 | 교정 실린더 + Anderson-Darling |

⭐⭐ **Deep 은 자체 in-house SBR 솔버**로 RCS 를 내 신호모형에 주입한다 — 우리와 같은 동작, 동료심사 통과.
⭐⭐⭐ **갈림**: 게재된 것은 전부 자기 σ 를 검증했고, 상용 솔버를 사서 검증 없이 넣은 **LAMBDA 만 미게재**.
⚠ 조사 범위 = 우리 아카이브 8디렉터리 **327편 전수**. 웹 검색 아님.

### 1-2. 런타임 반론 답변됨 (`outputs/runtime_benchmark.json`, 97 설정)

```
우리 per-pose   9.2~356 ms, 중앙값 38.1 ms  (공유 RTX 4090 1장, 120방위 배치)
스톡 PathSolver 72.8~128.0 ms               (같은 카드, 12설정)   → ⭐ 우리가 아래다
단계 분해       GPU ray_intersect 3.1% · PO 적분(host numpy) 48.5% → 호스트 96.9%
SagittaSBR      PO 가 광선발사의 1.9~6.5% (디바이스 커널일 때)
```
⚠ 인용 단위: Ziganshin 0.7/19.0 s 는 **360 각도점 전체 스윕**(각도점당 1.94→52.8 ms).
⚠ 오차막대: 반복 드리프트 0.80~1.10 (중앙 0.92).

### 1-3. 클러터 서베이 (Proc. IEEE 114(1):52-89, 2026) — 원문 확인

```
σ²c        β_c,n ~ CN(0, σ²c(f)), 경험적 지면클러터 모델    ← ⚠ PO 아님, 통계
표적 RCS   식(108) α_t,n ~ CN(0, σ²_t,n)                   ← ⚠ 통계 추출
표적 메쉬  "simplified 3-D mesh … publicly available 3-D models in Blender …
            keeps the ray-tracing scene lightweight"        ← 가볍게 하려고
Sionna     "background cold-clutter returns from surrounding buildings … by ray tracing"
SCNR       Fig.5 통계 −47.4 / Fig.7 Sionna RT −63.5 dB     ← ⚠ 16 dB 는 우리 유도값
```
41쪽 카운트: `physical optics` 0 · `dBsm` 0 · `drone` 0 · `DJI` 0 · `mesh` **2** · `Blender` **1** ·
`num_samples`/`max_depth`/`launch` **전부 0**. ⭐ 기종·광선예산 미보고 = **재현성 구멍**.

### 1-4. 앵커 = 측정 **1건** (원문 확정)

| | |
|---|---|
| **Das** | *Multiband Monostatic and Bistatic RCS Characterization of AAVs for ISAC Channel Modeling* — Shrayan Das, Peize Zhang, Veikko Hovinen, Marko E. Leinonen, Aarno Pärssinen, Pekka Kyösti |
| **Yuan** | *On Experimental Analysis of Mono-Static 3D UAV RCS for ISAC Channel Modeling* — Zhiqiang Yuan, Le Yu, Chunhui Li, **Wei Fan** (東南大) |

⭐⭐ Das 사사 축자: *"thank **Prof. Wei Fan** … for **providing the measured RCS data**"* → **Das = Yuan 자료 재분석**.
**측정 프로토콜**(Yuan §II): 무향실 + **CATR** + VNA 2포트 + **턴테이블**, 방위 **−90°~90° 2° 간격**,
고도면 **{90°,0°,180°}**, **VV 편파**. 처리 = 배경측정 → 교정구 → DUT → **코히런트 배경차감** →
**레인지 게이팅** → 교정구 대비 전력비.
⚠ **그들이 밝힌 한계 축자**: *"the chosen step size may be too large at higher frequencies, and RCS
measurements should be ideally taken across all polarization states … due to time constraints"*

---

## 2. ⚠ 오늘 철회한 것 — `docs/RETRACTION_LOG.md` R9~R13

| | 내가 말했던 것 | 실제 |
|---|---|---|
| R9 | "**해석해** 대비 검증" | 과녁 셋 중 **둘이 PO 로 PO 채점**. 진짜 외부 검증은 **정확 Mie 하나**(0.375~0.851 dB) |
| R10 | 이면각 **0.076 dB** | 4개 중 최량. **max 0.556 dB**. kr 0.2006 은 div=16, 생산 div=12 는 0.2544 |
| R11 | 순위불변 0.2462 | 15개 적합 평균, 국소 0.049~0.357(이론상한 0.25 초과). **항등식이지 발견 아님** |
| R12 | "공개문헌상 공백" | "보유 218편에서 미발견". ⭐ 대체: **17편 중 절대 dBsm 인쇄 3편, 드론 0편** |
| ⭐ **R13** | "**TW-ILDC** 를 구현했다" | **거짓.** 정직한 이름 = **`untruncated Michaeli PTD-EEC (first order)`** |
| — | 기울기 격차 **6.4~9.5배** | 같은구간(1.8~18.2) **2.07배** / 1.8~5.8 GHz 조밀격자 V편파 **4.54배** |
| — | 실측 "X410 **4채널**" | **기준+감시 2채널, 같은 클럭** |

⚠ **부재주장 규칙**: 반드시 모집단을 밝힌 계수 진술로.
`"Nobody prints a drone RCS"` ❌ → `"None of the 18 papers computes a drone RCS"` ✅

---

## 3. ⚠⚠ PTD 라운드 — R13 상세 (`outputs/ptd_attack_*.json`)

**C-P1 REFUTED AS STATED:**
```
(a) 생산 커널에 없다   src/rcs_sbr.py 'ptd' 0회 · attach_to_sbr_field 호출처 0건
(b) 전역 부호 뒤집힘   A_code/참조 = 1.0000000000 ∠180° (5각도, 양 편파)
                       ⭐ 참조 부호는 독립 고정 — PO 항이 폐형해를 9자리로 재현
(c) 평판 "개선" 이 증거 아님   위상맹목. 비코히런트로 더해도 비슷한 개선
```
⭐ **따라서 "PTD 가 기울기 격차를 못 메운다"(4.54→4.08배)도 잠정적이다.**
⚠ 문헌 격차: Gao 의 **truncated wedge**(Johansen 1996 식 3,9,10,11,21,22)는 **미구현**.
우리는 Johansen (4)(5) = Michaeli 1986 (4)-(7) = **비절단 절반**만.
⚠ 근사: PO 면적분 항은 **스칼라**(편파 없음), 프린지 항만 편파. 동일편파만.
⭐ 살아남음: `regression_identical = true`, 레거시 커널 4개에 'ptd' 0회, 카드 간 결정성 확인.
비용 PO 16.7 → PO+PTD 35.2 ms/pose (+111%).

---

## 4. ⚠ 면 개수 가설 — **반증**, 그러나 다른 발견 (`outputs/facet_count.json`)

```
드론 데시메이션 → 스톡 Sionna 에코    0.084 dB/decade   ← 가설 REFUTED
                  우리 PO             0.654 dB/decade
```

⭐⭐ **대신 규명된 기전:**
> *"a target echo is **one image-source path per triangle** that satisfies the specular condition,
> and its amplitude is **exactly λ/(4π(R1+R2)) — the INFINITE-MIRROR value** — independent of
> facet area and curvature. Facet size enters only as an **ANGULAR ACCEPTANCE WINDOW**."*

**mavic4pro 29,932 삼각형 · 36자세:**
```
경로 수            213.8 개/자세      ← ⭐ 광선은 잘 맞는다
그중 정반사        36자세 통틀어 2개, 자세 1개(az=0,el=0)에만
정반사 세기        −33.87 dB   vs   전체(확산 지배) −78.29 dB   ← 44 dB 차이
데시메이션 효과    정반사 2→1개 −6.05 dB, 1→0개 −42.97 dB, 총 −49.02 dB (이산 붕괴)
```
⭐ 드론 에코는 **확산 지배**이고, 확산은 재질 노브 S 에 매달려 수렴도 안 한다(광선 100M→400M 에 +8~12 dB).
⭐ 평판 세분 대조: **같은 1 m² 판을 2→512 삼각형으로 나누면 +9.54 dB** (동일 경로 중복, 20log10(N)).
⚠ **비판 형태 주의**: 이건 벤더 결함이 아니라 image-source 설계다. **범위 진술로만** 쓴다.
⚠ 그리고 내가 클러터 서베이에 한 "메쉬 단순화" 비판은 **대상을 잘못 짚었다** — 그들 표적 진폭은 식(108) 통계 추출이다.

---

## 5. ⚠ 팀미팅 선행연구 감사 (`docs/TEAMMEETING_PRIORWORK_AUDIT.md`)

**덱 5개(0623/0630/0714/0721/0728) 주장 197건 중 오류 25건 · 대조불가 27건.**
```
0630 s10·s15  LaSen 을 "live 5G downlink 위 추적" 이라 적었으나 에코는 LaSen 자체 USRP 의
              MATLAB PDSCH+DM-RS 송신. "재활용 신호=CSI-RS/SSB" 도 거짓(실제 PDSCH+DM-RS).
              Fig.1 캡션 날조
0721 s13      CISSIR 행 세 칸 전부 거짓 + 저자 오귀속 — 실제는 40 m 단일표적·주입 RCS 1 m²·
              계열 Injected·저자 Hernangómez 외(Fraunhofer HHI/TUB)
0623 s7·0630 s2  LIPASE GT 를 "RTK/DGPS (cm)" 로 적었으나 원문은 sub-meter DGPS.
              "추적 논문 2편" 도 거짓(덱 자기 표에 세 줄)
0728 s20 노트  y = H_t x + H_c x + H_h **x** 로 적음 → 원문은 H_h **s^ext**(외부 방출체)
              ⚠ 그림 eq_decomp.png 자체는 옳다. 노트만 회귀
0623 s4       "all papers did experiment outdoor" → FALSIFIED (Lin 외 ICCC 2023 실내 씬 명시)
OpenISAC      "100~200 MHz 붕괴" → ⚠ **200 MHz 단독**. 50·100 MHz 는 안정 동작점
```
⚠ 감사 자체의 자기비판: 약한 CONFIRMED 16건, 과잉판정 10건, **그림 안 텍스트 미감사**(덱 5개에 그림 44장).

---

## 5-1. ⛔ 2026-08-03 10:10 — **워크플로 전면 정지 (사용자 지시)**

**살아 있는 것은 `benchmark/rcs_anchor.py` (PID 1364837, 4시간 17분) 하나뿐이다.** 죽이지 않는다.

### ⚠ 고아 프로세스 교훈 — `nohup ... &` 는 워크플로 종료에도 살아남는다

σ 재생성 에이전트가 `nohup python sg_driver.py ... &` 로 드라이버를 띄웠고,
`TaskStop` 으로 워크플로를 죽인 뒤에도 **드라이버 2개(PID 2548274 · 2557092)가 PPID=1 로 살아
계속 워커를 새로 띄우고 있었다.** PID 로 정확히 종료했다(⛔ `pkill -f` 금지).
⭐ **다음부터 워크플로 정지 시 `ps -eo pid,ppid,etime,cmd | grep -E "driver|worker"` 를 반드시 확인한다.**
관련 메모리: `zombie-session-hazard`.

### ⭐ 보존한 중간 산출물

```
outputs/partial/sigma_regen_0803/
  sigma_<drone>_<band>.json   19 / 21   (7기체 × 3밴드 중 s1000plus_nr · s1000plus_wifi 만 미완)
  sg_worker.py · sg_driver.py · sg_driver2.py · sg_merge.py · sg_compare.py · ms_worker.py
  cache_prune.json
```
⭐ **워커·드라이버·병합 스크립트가 그대로 있으므로 재개는 이어서 하면 된다.** 처음부터 다시 안 돌려도 된다.
⚠ 정지 시점에 s1000plus 두 셀 워커가 아직 돌고 있었다 — 끝났으면 scratchpad 에서 마저 거둘 것:
`/tmp/claude-1015/.../scratchpad/sg/` (⚠ /tmp 는 세션 밖에서 지워질 수 있다).

### 정지된 워크플로와 재개 방법

| 워크플로 | 상태 | 재개 |
|---|---|---|
| **σ 격자 재생성** + 축 배선 + RadarTwin | 19/21 셀 완료 | 스크립트 보존됨(위). `sg_driver2.py` 를 남은 2셀로 재실행 |
| **저주파 격차 진단** (격자 vs PO) | 착수 | `Workflow({scriptPath: '.../lowfreq-grid-vs-po-wf_26f2f411-33e.js'})` |
| **Phantom 3 대조군** (큐브·박스) | σ 계산 완료, 대조군 미착수 | `Workflow({scriptPath: '.../phantom3-blind-validation-wf_51692896-418.js', resumeFromRunId: 'wf_51692896-418'})` |
| **팀미팅 덱 수정** | ⚠ v3.pptx 15장 있으나 **날조 1·불일치 23 미수정** | `Workflow({scriptPath: '.../deck-0804-fix-wf_6cd225f7-71e.js'})` |
| **PTD SBR 배선** | ⭐ 부호는 이미 수리됨(파일 보존) | `Workflow({scriptPath: '.../ptd-signfix-wire-wf_0d067296-85c.js', resumeFromRunId: 'wf_0d067296-85c'})` |

⚠ **내일 팀미팅 덱**: `teammeeting_0804_v3.pptx` (15장, 기계검수 통과)는 있으나
**날조 1건("vertically polarised **horns**" — 원문은 "directional antennas")과 불일치 23건이 미수정**이다.
⛔ 그대로 발표하면 안 된다. 수정 라운드를 먼저 돌릴 것.

---

## 6. 🔄 (과거) 중단 시점에 돌고 있던 것

| ID | 무엇 | 상태 |
|---|---|---|
| — | ⛔ `benchmark/rcs_anchor.py` (GPU2, PID 1364837) | **2h52m 경과** / 약 3h. **유지** |
| `wsju86tog` | ⭐⭐ **Phantom 3 눈감기 검증** (최우선) | 메쉬 제작 단계. p3_specs.json 만 나옴 |
| `whlerhmfn` | ⭐⭐ **급소 실험** — 표적모형이 검출을 바꾸는가 = **Sionna 존폐** | 진행 |
| `wgor7658a` | sim-to-real 방향 정찰·설계·적대검증 | 진행 |
| `wjogpc7w1` | ⚠ **PTD 부호 수리 + SBR 배선** | 진행 |
| `wxxony7y6` | 팀미팅 덱 (담백한 13~16장) | 진행 |

**전부 `outputs/*.json` 으로 떨구므로 죽어도 이어갈 수 있다.**

---

## 7. 팀미팅 덱 (내일 08-04)

| 파일 | 상태 |
|---|---|
| `teammeeting_0804_v1.pptx` (22장) | 완성. `decks/` 에 커밋됨 |
| `teammeeting_0804_short.pptx` (5장) | 완성. ⚠ 낡은 σ 격자 그림 |
| `teammeeting_0804_v2.pptx` | ⛔ **31/60. 쓰지 말 것** |
| **`teammeeting_0804_v3.pptx`** | 🔄 제작 중 (`wxxony7y6`) |

**v3 구성 — 사용자 확정:** ⛔ 부(PART) 나누기·구분자 없음. ⛔ 프레임 정정 부 제외. **담백한 13~16장.**
```
표지 → Das/Yuan 소개 → 그들의 측정 방법 → ⚠ 그들이 밝힌 한계 → 두 논문=측정 1건
→ 주입은 게재돼 있다 → 게재된 건 전부 검증했다 → 눈감고 시험한다 → 봉인/허용 + 자유도
→ ⭐⭐ 대조군(큐브·박스) → 결과 → 허락하는 것/안 하는 것 → 다음(사이트 트윈·분류·ablation·요청)
```

⭐ **상시 규칙(메모리 `sionna2-deck-git-standing`)**: 덱이 완성되면 **묻지 말고**
`sionna2/decks/` 복사 → 커밋 → 푸시. **완성본만.** ⛔ `git add -A` 금지, `team_meeting/` 금지.

---

## 8. ⭐ 다음 할 일 (오늘 재정렬)

1. ⭐⭐ **Phantom 3 결과** — 우리 메쉬 방식의 오차막대. **큐브 대조군이 핵심**
   (큐브가 우리만큼 맞으면 메쉬 작업에 값어치가 없다)
2. ⭐⭐ **급소 실험 결과** — **Sionna 존폐를 이게 정한다**
3. ⭐ **PTD 부호 수리 후 Phantom 3 재실행** — 사용자 지시:
   순수 SBR+PO 기준선 → 부호 수리·배선 → ptd=True 재실행 → **PO / PO+PTD / Das 실측 3자 비교**
   ⭐ **실측이 부호의 심판이 된다** (평판 시험은 위상맹목이라 못 한다)
4. `rcs_anchor.json` 재생성 완료 확인 → **σ 격자도 낡았다**(§9) → 재생성
5. ⚠ φ=90° 결함 — `experiment_freespace_range.py:322,773`
6. 감사 오류 25건을 덱·리포트·JSON 에 전파 (§5)
7. 실측 설계를 **3층 구조**로 갱신 (`MEASUREMENT_PLAN.md`)
   1층 σ(f) 레인지(능동 모노·교정구·서브밴드) · 2층 파형축(ISM 한 곳) · 3층 비행검출
   ⛔ **3×3 교차설계 취소** — "2.1 GHz 의 WiFi" 는 없고 면허 문제도 있다
8. ⭐ **sim-to-real 방향** — 실측 사이트 트윈 → 합성 데이터 → 드론 기종 + 새 분류.
   핵심 ablation = 같은 사이트·파형·분류기에서 **표적모형만 3갈래**.
   새는 (a) 공개 데이터 + (b) 우리 분절 파이프라인 **결합** — 검증이 운동학이라 이식된다.
   ⭐ 투고처는 **IEEE 레이다 계열**(TAES / Trans. Radar Systems / JSAC ISAC). ⛔ SenSys·MobiSys·ICASSP 제외
   (우리 인용 그래프가 전부 IEEE 레이다·전파·통신이다)

---

## 9. ⚠⚠⚠ 낡은 산출물 — **"낡음" 이 아니라 "다른 데이터" 다** (`outputs/s2r_assets_verify.json`)

```
outputs/rcs_anchor.json          07-30 09:46   ← 재생성 중 (3h39m 경과)
outputs/report13_sigma_grid.json 07-29 생성    ← ⚠⚠ 앵커보다도 낡았다
src/drones.py 07-31 06:49 · src/drone_cad.py 07-31 08:04  (커밋 cba8626 메쉬 개편)
```

⭐⭐ **동일 설정 재생성 대조(div=16·jitter=2·penetrate·n_f=3·선형평균, el=−3.5°, 3.5 GHz, az 12점):
84셀 중 일치(<0.01 dB) 0개.**

| 기체 | max | rms | mean |
|---|---|---|---|
| mavic4pro | **22.36** | 10.82 | −5.70 dB |
| typhoonh480 | 11.91 | 5.54 | −1.04 |
| mini5pro | 10.13 | 4.61 | **+3.18** |
| matrice4e | 9.00 | 4.87 | +1.34 |
| x500v2 | 8.65 | 5.23 | −2.62 |
| s1000plus | 7.83 | 4.64 | −2.09 |
| phantom4 | 5.10 | 3.34 | −1.07 |

⚠⚠ **평균이 기체마다 반대 방향으로 움직인다 → 백분위·CDF·기체간 순위까지 전부 무효.**
⛔ 자산으로 셀 수 있는 것은 **축 설계·파이프라인·재생성 비용**뿐이다.
⚠ `outputs/sigma_sbr_cache.json` 2,000 엔트리 중 오늘 메쉬 기준 **유효 50개(2.5%)**
(650개는 `@meshfp` 없는 레거시 키 = 영구 미스, 1,300개는 stale).

---

## 9-1. ⭐ sim-to-real 방향 정찰 결과 (`outputs/s2r_*.json`, `docs/SIM2REAL_PLAN.md`)

**신규성 살아 있음**: 33편 정독(아카이브 313편 정규식 스크린 → 32편 히트 → 21편 정독 + 웹 12편)에서
*"사이트 트윈 + 물리계산 자세분해 σ + 분류 + 실측 전이"* 조합 보유 **0편**.
최근접 = **LAMBDA**(Sionna RT 사이트트윈 + CADFEKO 자세의존 RCS + FMCW 큐브)이나
**RF 분류 없음 · 실측 검증 없음**.

### ⭐⭐ 태스크는 **분류가 아니라 유무 검출**로 좁혔다 — 근거가 강하다

> *"통계 RCS 와 금속 큐브에는 **로터가 없어서**, 분류로 가면 ablation 이 '표적모형의 질' 이 아니라
> **'로터를 넣었느냐'** 를 재게 된다."*

검출은 세 팔이 전부 σ(t) 하나로 환원돼 **같은 에코합성 → ECA → CAF → CFAR** 를 통과하므로 공정하다.
⚠ 기종식별은 도메인 전이에서 **가장 먼저 무너진다** — CageDroneRF (IEEE T-AES) p.11 축자:
*"struggles significantly with **model-level identification (42.07%)** … **poor domain generalization**
from indoor to outdoor environments."*

### ⚠⚠ 적대검증 판정 **RISKY** — 가장 강한 반례가 40줄짜리다

> *"**S+** — 평균·상관시간·분포형 3자를 정합한 확률적 σ(t) (파라미터 3개, GPU 0, **~40 LOC**).
> 정규화 하에서 우리 σ 가 검출기에 주는 정보는 사실상 **(σ̄, τ_decorr, 분포형) 3개 수**뿐이다."*

⭐⭐⭐ **원인: 자세축과 로터위상축이 σ 생산자에 배선돼 있지 않다.** 세 팔 모두 **CPI 내 변조가 없다.**
격자 실측: az 상관길이 3~9° → v=10 m/s·R=100 m 에서 τ=0.5~1.6 s, 30 s pass 당 독립 draw 19~57.
p90−p10 중앙 13.3 dB (≈ log-normal σ_dB 5.2 dB).

⭐ **이 판정은 실측 없이 오늘 sim-to-sim 으로 가능하다(K8).** → **최우선 대응 = 자세·로터위상 축 배선.**
다른 강한 베이스라인: **M**(측정 σ 주입 오라클 — 경쟁자가 아니라 상한), **B**(실측 배경 주입 축 —
선행 4편이 최대 레버로 지목), **F**(in-domain 링크버짓 — 같은 조건 안에서는 우리를 반드시 이긴다).

### 평가 규약 — 레이다·ISAC 는 ML 일반과 다르다

```
· Pfa 는 측정값이 아니라 CFAR 설계값 → Pd 를 보고한다
· 모델-실측 격차를 정확도 차가 아니라 SINR-vs-range 산점도 위 dB 오프셋으로 인쇄
· "예측 r_max 540 m vs 실측 달성 500 m" 같은 단일 숫자
· 정확도는 평균±std 가 아니라 분위수(50%/95%)
· pooled 단일 숫자 금지 — SNR·거리·기하로 층화
```

---

## 10. git

**푸시됨: `5ad359b`** (프레임 정정 · R9~R12 · 주입 선례 · 런타임 · 인용검사기 · 앵커 서지, 22파일).
**미커밋 119 항목** — 진행 중 워크플로 산출물. 끝나면 이어서 커밋.
⛔ `team_meeting/` 제외, `groupmeeting_*` 제외, `git add -A` 금지.
