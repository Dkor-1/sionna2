# sim-to-real 방향 — 실행 설계

> 작성 2026-08-03. 입력: `outputs/s2r_prior.json` · `outputs/s2r_protocol.json` · `outputs/s2r_assets.json` ·
> `docs/MEASUREMENT_PLAN.md` · `docs/RESUME.md` · `docs/RETRACTION_LOG.md`.
> ⭐ 이 문서의 모든 축자인용은 **이번 라운드에 내가 직접 연 PDF**에서 뽑았다(§부록 A 에 파일경로·쪽수).
> 에이전트 JSON 에만 있고 내가 원문을 못 연 항목은 §부록 B 에 **미검증**으로 격리했다.
> ⛔ 이 라운드는 조사·설계다. GPU 작업 없음(`rcs_anchor` + Phantom 3 진행 중).
> ⛔ 진행중 워크플로 산출물(`p3_*`, `tm_*`, `ptd_*`, `facet_*`, `teammeeting_0804/*`) 미변경.

---

## 0. 한 문단 요약

**태스크는 (a) 유무 검출로 확정한다.** 논문의 뼈대는 *같은 사이트 트윈 · 같은 파형 · 같은 검출기에서
**표적모형만 3갈래**(통계 RCS / 큐브 / 우리 σ)* 로 바꾸는 ablation 이고, 공정성 규약은 **자세평균 σ 정합
(N1)과 무정합(N2)을 병행**한다. 실측 없이 오늘 볼 수 있는 것은 **sim-to-sim 3×3 교차행렬**이며 그것은
**필요조건 검사**다 — 비대각이 대각과 같으면 실측을 해도 ablation 은 0 이다. 전체 규모는 **6~12개월**이고
**임계경로는 GPU 가 아니라 실측 캠페인**이다.

---

## 1. 태스크 확정

### 1-1. 후보 4개의 비용

| | 실측 라벨 | 필요 기체·장비 | 실측 세션 배수 | 시뮬 측 추가 비용 | 3갈래 ablation 이 성립하는가 |
|---|---|---|---|---|---|
| **(a) 유무 검출** | 표적 유/무 (+대략 거리) | 구매 2종으로 충분. **표적 없는 배경 캡처가 곧 음성 클래스** | **×1 (기준)** | 궤적 생성기 + σ(t) 주입 (350~550 LOC) | ✅ 세 팔이 **같은 하류**(에코→RD→CFAR)를 통과한다 |
| (b) 드론 vs 비드론 | 위 + 비드론 무버 클래스 | 조류는 통제 불가 → 대리물(보행자·회전 코너리플렉터·투척물). 대리를 쓰면 *"조류 판별"* 주장 불가 | ×1.5~2 | + 대리표적 메쉬·운동학 | ⚠ **깨진다.** 통계팔·큐브팔에는 로터가 없어 팔 간 차이가 *"로터가 있느냐"* 로 퇴화한다 — 표적모형 ablation 이 아니라 로터 유무 ablation 이 된다 |
| (c) 기종 분류 | 기체별 라벨 | **클래스 수 = 기체 수.** 구매 2종 = 2-class 상한. 의미있는 5-class 는 기체 3종 추가 구매 | ×2.5 | 기종별 격자(있음) | ✅ 성립하나, ⚠ 실측 근거상 **가장 먼저 무너지는 태스크**(§1-3) |
| (d) 자세/상태 추정 | 자세 GT (PX4 로그 + ms급 시각동기) | 위 + 동기 배관 | ×2 | ⚠ **σ 격자에 기체 자세축이 아예 없다**(`s2r_assets.missing.attitude_axis`) → 자세상태 1개당 기존 격자 1벌 = 8기체×3밴드 **약 1.2 h/1카드** | ✅ 성립하나 **검출이 아니다** |

### 1-2. 선택 — **(a) 유무 검출**

이유 셋.

1. **세 팔이 서로 비교 가능한 유일한 태스크다.** 통계 RCS 와 금속 큐브에는 로터 마이크로도플러가
   없다. 분류 태스크로 가면 분류기는 로터선(rotor line)을 잡을 것이고, 그러면 ablation 이 측정하는 것은
   "표적모형의 질"이 아니라 "로터를 모형에 넣었느냐"가 된다. 검출은 세 팔 전부가 **σ(t) 하나로 환원**
   되어 같은 에코 합성 → RD → CFAR 를 통과하므로 공정하다.

2. **방향 확장이 아니다 → 대가가 0 이다.** 프로젝트 방향은 *디텍션 집중*(메모 `sionna2-project-direction`)
   으로 이미 확정돼 있다. (b)(c)(d) 중 무엇을 골라도 실측 세션이 1.5~2.5배가 되고, 특히 (c)는 **기체를
   3종 더 사야** 한다. 우리가 지금 사려는 것은 Mavic 4 Pro·Matrice 4E 2종뿐이다.

3. **지표가 이 분야의 정본과 일치한다.** 레이다·ISAC 문헌의 헤드라인은 *고정 Pfa 에서의 Pd* 이고
   Pfa 는 측정값이 아니라 CFAR 설계값이다. 우리는 그 배관(`passive_process.ca_cfar_2d`,
   `experiment_detection.gpu_montecarlo`)을 이미 갖고 있다.

### 1-3. 대신 포기하는 것과, 공짜로 얻는 것

⚠ 포기: **기종 식별 주장.** 이건 실측 근거가 나쁘다. CageDroneRF(IEEE T-AES) p.11 축자 —

> *"When the model is trained on indoor data only, it achieves moderate accuracy at the coarser levels
> (Modulation: 69.95%, Protocol: 66.11%) but struggles significantly with model-level identification
> (42.07%). This indicates poor domain generalization from indoor to outdoor environments."*

**태스크 입도가 올라갈수록 도메인 격차가 커진다.** 우리는 챔버(=clean controlled) 프레임을 쓰므로
이 비판의 정면 표적이다. 같은 논문 p.4 축자: *"DroneRF [77] includes only three drone models in a clean
controlled environment, producing near-ceiling benchmark accuracy that transfers poorly to operational
settings."*

✅ 공짜로 얻는 것: 실측에서 기체 2종을 어차피 날리므로, **같은 녹화에 라벨 헤드만 하나 더 붙이면
2-class 기종식별이 측정 부담 0 으로 나온다.** 이것은 **주장이 아니라 "한계 패널"로만 인쇄**한다 —
탐지만 인쇄하고 세밀 태스크를 감추는 함정(P9)을 피하면서, 기종식별을 novelty 로 팔지도 않는 자리다.

---

## 2. ⭐⭐ 핵심 ablation — 표적모형 3갈래

### 2-1. 무엇을 고정하고 무엇을 바꾸는가

```
[고정]  사이트 트윈 S  →  조명 파형 w  →  궤적 T  →  ┃ 표적모형 M ┃ →  σ(t)
        → 에코 합성(R1·R2, 도플러 위상램프) → 클러터+잡음(시드 페어링)
        → ECA → CAF range-Doppler → CA-CFAR(설계 Pfa 고정) → 검출기
```

| 축 | 고정/변화 | 비고 |
|---|---|---|
| 사이트 기하·재질·RT 클러터 | **고정** | 세 팔이 같은 씬을 쓴다 |
| TX/RX 배치, 파형·점유모드, CPI 길이 | **고정** | |
| 궤적 집합 (waypoint·속도·시드) | **고정** | 같은 비행을 세 번 다르게 산란시킬 뿐 |
| ECA 탭수·거리창·CFAR guard/train·**설계 Pfa** | **고정** | 설계값을 표에 인쇄 |
| 잡음 시드 | **페어링 고정** | paired 통계의 전제 |
| 검출기/학습기 구조·하이퍼·5 seeds | **고정** | |
| **표적모형 M** | ⭐ **이것만 변화** | S / C / O |

### 2-2. 세 팔의 실제 구성

#### Arm S — 통계 RCS (`target_model="statistical"`)

σ 가 **각도에 무관**하고 전력이 지수분포다. 근거는 우리가 이미 정독한 클러터 서베이의 표적 항이다
(Proc. IEEE 게재판, 내가 이번에 다시 연 사본, pdf p.28, 식 (108) 직후) —

> *"where D(f_D) ≜ diag(d(f_D)), and α_t,n ∼ CN(0, σ²_t,n) represents the target RCS together with the
> associated path loss."*

- 구현: `sigma_t = rng.exponential(sigma_bar)` — 약 15 LOC.
- **하위변종 2개 필수** (시간상관이 표적모형 효과의 주된 통로이므로):
  - `S-I` : pass 당 1회 추출 후 고정 (Swerling I 급)
  - `S-II`: CPI 마다 독립 추출 (Swerling II 급)
- ⚠ 같은 서베이가 **씬 안에는 메시를 세운다**(pdf p.23: *"The ToI and UAVs are modeled as simplified 3-D
  mesh objects imported into Sionna… which keeps the ray-tracing scene lightweight"*). 즉 이 논문을
  "통계 팔의 대표"로 인용할 때는 **식 (108) 의 표적 진폭 항에 한정**해야 한다. 메시 단순화를 싸잡아
  비판하면 대상을 잘못 짚는다(RESUME §4 에서 이미 자기정정한 항목이다).

#### Arm C — 큐브 (`target_model="cube"`)

표적 메시를 정육면체로 갈아끼운다. `src/geom.py:184 box(a,a,a)` 한 줄이고 재질은 ITU metal 단일.

근거 — 이번에 연 원문, arXiv 2605.07623 pdf p.8 축자:

> *"The UAV is modeled as a metallic cube located at p = (x, y, 60), where x, y ∼ U[−75, 75]."*

⭐ **공정성의 핵심: 엔진은 고정한다.** 큐브 σ(az, el; f) 를 **우리와 똑같은 `rcs_sbr.rcs_sbr_batch`**
(1-bounce SBR + PO 면적분, 같은 spacing·jitter·대역평균)로 굽는다. 큐브 팔이 우리 엔진의 이득을
그대로 받아야, 팔 간 차이가 *"엔진"* 이 아니라 *"표적 표현"* 에서만 온다.

- 변 길이 `a` 두 규약:
  - `C-bbox` : 프로펠러 포함 bbox 최대 수평치수 (MEASUREMENT_PLAN §A: matrice4e 599.3 mm, mini5pro 376.0 mm)
  - `C-match`: 자세평균 σ 를 Arm O 에 맞춘 `a` (= 정규화 N1 의 큐브판)
- ⚠ **레벨 감각** (왜 정규화를 병행해야 하는지의 근거). 평판 PO 폐형해 σ = 4πa⁴/λ², 3.5 GHz(λ=85.66 mm):

  | a [m] | 정면 플래시 σ [dBsm] |
  |---|---|
  | 0.2 | **+4.38** |
  | 0.3 | **+11.42** |
  | 0.4 | **+16.42** |

  같은 대역에서 우리 격자의 **자세중앙값**은 −24.18(mini5pro) ~ −16.35(s1000plus) dBsm 이다
  (`outputs/report13_sigma_grid.json`, ⚠ **2026-07-29 생성 = 07-31 메시 개편 이전. 절대 레벨 인용 금지**,
  여기서는 자릿수 감각으로만 쓴다). 즉 **큐브 정면 플래시가 드론 자세중앙값보다 약 21~41 dB 위**다.
  ⚠ 이 비교는 *플래시 대 중앙값*이라 사과-대-사과가 아니다 — **큐브의 자세평균 σ 는 아직 계산 안 했다.
  §3 T6 에서 같은 커널로 굽는다.**

#### Arm O — 우리 σ (`target_model="ours"`)

우리 메시 + 재질가중 PO + 가림 + 유전체 셸 투과. σ(az, el; f) 격자 조회 → 궤적으로 시간축 부여.

- 선택적 **퇴화 사다리**(RadarTwin §7.4 형식, 확장):
  `O-full` → `O-uniform`(전면 금속 균일재질) → `O-rigid`(로터 정지) → `C` → `S` → `void`(표적 없음)
- ⚠ `O-full` 안의 PO vs PO+PTD 는 **주 ablation 축이 아니다** — 부호 수리(`wjogpc7w1`)가 끝나기
  전에는 사다리에 넣지 않는다(RETRACTION_LOG R13).

### 2-3. ⚠ 공정성 규약 — 두 정규화를 **병행**한다

이게 이 ablation 의 승부처다. 하나만 인쇄하면 반드시 진다.

#### N1 — 자세평균 σ 정합 (level-matched)

각 팔에 상수 이득 `g_M` 을 곱해 **궤적가중 선형(전력) 평균 σ 를 Arm O 에 맞춘다.**

```
σ̄_M = mean over {(az,el,f) : 궤적 T 가 실제로 스치는 시선각}  of  σ_M
g_M  = σ̄_O / σ̄_M
```

남는 차이는 오직 **각도 구조 + 요동 통계 + 시간 상관**이다. → *"구조가 검출을 바꾸는가"* 를 잰다.
**이게 주 규약이다.**

⚠ 두 갈래를 함께 들고 다닌다 (RETRACTION_LOG **A8** 규칙: 조용한 단일값 금지):
- **평균 규약**: 선형(전력) 평균 정합이 정본, dB영역 평균 정합은 부록. 두 정합의 차이가 곧 요동 크기이고,
  σ 가 지수분포일 때 그 상수는 `10/ln10 · γ = 2.5068 dB` 로 **정확**하다.
- **평균 집합**: *궤적가중*이 정본(교란변수 통제), *전 구면*은 부록.

#### N2 — 무정합 (as-published)

각 팔이 선행 관행대로 **자기 레벨을 그대로** 갖는다. S = 문헌 평균 σ(Das/Yuan 앵커), C = bbox 치수 큐브,
O = 우리 커널 출력 + 앵커 기울기 보정. → *"선행 관행을 그대로 따르면 검출 예측이 얼마나 틀리는가"* 를 잰다.
**실무적 헤드라인은 이쪽이다.**

#### 왜 둘 다인가

- N2 만 인쇄 → *"레벨만 맞추면 되는 것 아니냐"* 에 진다. 우리 기여가 스칼라 1개로 환원된다.
- N1 만 인쇄 → 선행 관행의 실제 대가(21~41 dB 급 레벨 오차)를 못 보인다.
- ⭐ **N1 에서 차이가 사라지고 N2 에서만 남으면, 그건 결과가 아니라 사망선고다** — §5 K2.

### 2-4. 인쇄물 — 팔 × 정규화마다

**utility (헤드라인).** 3열 규약: `Raw(무학습 CFAR) / Arm / Chance`.

| 지표 | 형식 | 왜 |
|---|---|---|
| **Pd @ 설계 Pfa** | 거리·헤딩·SNR 의 **함수**로 분해. 설계 Pfa 값을 표에 명시 | 이 분야는 pooled 단일숫자를 안 쓴다 |
| ⭐ **pass 단위 검출 연속성** | 검출된 CPI 비율, **최장 연속 드롭아웃 길이** | **스칼라 σ 는 드롭아웃을 만들 수 없다.** 세 팔이 가장 갈리는 자리 |
| **예측 r_max vs 달성 거리** | 단일 숫자 | 가장 값싼 sim-to-real 헤드라인 |
| 클래스별 recall | drone recall 을 총정확도와 **분리** 인쇄 | §부록 A-5 |

**fidelity (진단용. ⛔ 전이 주장의 근거로 쓰지 않는다).**

| 지표 | 비고 |
|---|---|
| 기종 간 σ **순위** Spearman ρ | ⛔ 절대 dBsm 아님 (§부록 A-4) |
| 측정 SINR-vs-range 산점도 위 시뮬 링크버짓 곡선 중첩 → **dB 오프셋** | 격차를 물리 원인에 귀속 |
| RD 진폭 분포 KS / Wasserstein | **real↔real2 바닥선을 반드시 옆에 병기** |

**통계.** 분석 단위 = **recording(=pass)**, 세그먼트 아님. 5 seeds, paired bootstrap 10,000 resample,
Δ의 95% CI 가 0 을 배제하면 유의. *'not above chance'* 를 명시적으로 판정.

**교란 통제.** RadarTwin p.11 축자:

> *"First, distance is a confound. Pooling distances inflates sim-real feature correlations (to ∼0.8)
> because both domains vary with range. Distance-matched, per-feature correlations peak near 0.5…"*

→ 모든 sim-real 비교는 **거리 매칭 상태**로. {기종, 거리, 대역} 중 **둘을 고정하고 하나만** 바꾼다.
chance 선도 층화 후 값으로 다시 계산한다.

### 2-5. 교차행렬

| | 테스트 = S | = C | = O | = 실측 |
|---|---|---|---|---|
| 학습 = S | 대각 | | | ⭐ sim-to-real |
| 학습 = C | | 대각 | | ⭐ |
| 학습 = O | | | 대각 | ⭐ |
| 학습 = 실측(같은 사이트) | | | | real→real 기준선 |
| 학습 = 실측(**다른** 사이트) | | | | ⭐ **공정 기준선** |

⚠ 마지막 행이 중요하다. sim-to-real 격차의 공정한 눈금은 *"같은 실측으로 학습"* 이 아니라
*"다른 조건의 실측으로 학습"* 이다(§부록 A-6).

### 2-6. 검출기는 학습형인가

**둘 다 돌린다.**

- **무학습 기준선**: ECA + CAF + CA-CFAR. 팔에 무관하게 동일하므로, 각 팔은 이 검출기의 **성능을 예측**
  할 뿐이다. 지표 = *예측 Pd(거리) 대 실측 Pd(거리)* 의 dB 오프셋. **ML 없이 성립하는 논문의 뼈대.**
- **학습형**: RD 맵 위의 **작은** 검출기(수천 파라미터급). 팔별로 학습 → 실측 평가 = 표준 sim2real 사다리.
  ⚠ 모델을 키우지 않는다 — 합성만으로 학습할 때 큰 모델은 시뮬 아티팩트에 수렴한다는 반례가 있다(§부록 B-3).

두 결과가 어긋나면 **그 어긋남 자체가 결과다**(§부록 A-3).

---

## 3. 최소 실행 계획 — 오늘 / 실측 필요

### 3-1. 오늘 할 수 있는 것 (실측 0, GPU 0~최소)

`s2r_assets.biggest_gap` 이 진단한 대로 **물리 커널은 다 있는데 데이터셋 층이 0줄**이다.
병목은 GPU 가 아니라 writer 다.

| ID | 무엇 | 규모 | GPU |
|---|---|---|---|
| **T1** | 데이터셋 층 — 샘플→텐서 writer, 라벨 스키마, manifest/split, 시드 재현 | 300~500 LOC | 0 |
| **T2** | 궤적 생성기 — 등속·선회·호버·PX4 로그 임포트 → (aspect, R1, R2, f_d) 시퀀스 | 200~300 LOC | 0 |
| **T3** | ⭐ **시간가변 σ(t)·자세(t) 주입** — CPI 안에서 σ 를 상수에서 시계열로 | 150~250 LOC | 0 |
| **T4** | 표적모형 어댑터 — 공통 인터페이스 `sigma(aspect, f, t)` 뒤에 S / C / O | ~150 LOC | 0 |
| **T5** | 정규화 N1/N2 + 궤적가중 평균 + dB/선형 두 분기 | ~80 LOC | 0 |
| **T6** | 큐브 σ 격자 굽기 (`box(a,a,a)`, 같은 커널) + **자세평균 σ 계산** | 코드 ~30 LOC | 소량 (큐브는 저면수 → 드론보다 쌈). ⛔ `rcs_anchor`·Phantom 3 종료 후 |
| **T7** | 검출 MC 처리율 계측 (`s2r_assets.missing.mc_throughput_unknown`) | 10분 | 소량 |
| **T8** | ⭐⭐ **sim-to-sim 3×3 교차행렬** (두 정규화 = 2장) | — | 중 |

⛔ 오늘 하지 말 것: σ 격자 전면 재생성(1.2 h/1카드) — `rcs_anchor` 가 끝나고 메시 개편이 반영된 뒤에.

### 3-2. ⭐ 실측 없이 ablation 을 미리 볼 수 있는가 — **볼 수 있다. 단 성격이 정해져 있다**

**sim-to-sim 3×3 은 필요조건 검사(necessary-condition gate)다.**

```
비대각 ≈ 대각  (Δ의 95% CI 가 0 포함, 5 seeds 전부)
   →  표적모형을 바꿔도 검출이 안 변한다
   →  실측을 해도 ablation 은 0 이다.        ⛔ K1 발동, 접는다.

비대각 ≠ 대각
   →  "실측에서도 다를 것" 이라는 뜻은 아니다.  ⚠ 역은 성립하지 않는다.
```

역이 성립하지 않는 근거 — 무보정 광선추적 합성이 실측에서 chance 로 붕괴한 실측 사례
(arXiv 2601.17871, 내가 이번에 받아 연 원문 pdf p.3):

> *"the baseline RT model trained solely on unmodified simulation struggles to generalize… resulting in a
> balanced accuracy close to 50% (chance-level for a binary task)."*
> *"the baseline RT model again fails to transfer, achieving balanced accuracy near 33% (random guessing)"*

즉 도메인 격차가 표적모형 효과를 **덮어버릴 수** 있다. 그래서 sim-to-sim 은 **GO/NO-GO 게이트**로만 쓰고,
sim-to-real 격차의 크기 주장에는 절대 쓰지 않는다.

### 3-3. 실측 없이 되는 **두 번째** 것 — Phantom 3 외부 앵커에 3팔을 다 대기

우리에겐 **외부 실측 앵커가 1건** 있다(Das IEEE WCL 2026 = Yuan EuCAP 2025 **재분석**, 같은 원자료 —
RETRACTION_LOG A2). Phantom 3 σ(f, φ) 에 대해 **O / C / S 세 팔의 오차를 각각** 낸다.

- 이건 실측 캠페인 **없이** 얻는 유일한 절대 대조다.
- ⭐ 그리고 진행 중인 Phantom 3 라운드(`wsju86tog`)가 **이미 큐브 대조군을 품고 있다** → **Arm C 는 거기서
  태어난다.** 별도 개발 비용이 사실상 0 이다.
- 판정: *큐브가 우리만큼 Phantom 3 실측을 맞추면, 메시 작업에 값어치가 없다*(RESUME §8-1). → K5.

### 3-4. 실측이 반드시 필요한 것

| 항목 | 왜 대체 불가 |
|---|---|
| utility 헤드라인 (실측 테스트셋 Pd) | 정의상 |
| **real↔real2 반복 수집 1세트** | 이게 없으면 어떤 격차 수치도 크다/작다를 말할 수 없다 |
| **표적 없는 배경 캡처** (각 기하마다) | 무향실 시뮬의 최대 위험은 *너무 깨끗한 노이즈 플로어*. 이 한 축 보정이 chance→97% 를 만든 사례가 있다(§3-2 인용의 같은 논문) |
| 교정표적 (금속구 / 코너리플렉터) 1회 | 절대 σ 스케일 + per-feature affine 앵커. **라벨 불필요 = 가장 싼 한 칸** |
| 사이트 **2곳** (개활 1 + 반사체 많은 곳 1) | 1곳이면 "전이가 환경 의존"이라는 발견 자체가 불가능 |
| 기체당 독립 비행 **10~15회**, 거리 3점 이상 | 분석 단위가 pass 이므로 |
| 예측 r_max vs 달성 거리 | 정의상 |

⚠ **정직성**: 위 수치는 선행 논문들의 사후 관행에서 역산한 것이지 검정력 계산이 아니다. 우리 효과크기를
아직 모른다. **파일럿(기체 2종 × 5비행)으로 분산을 재고 나서 본 캠페인 규모를 정한다.**

---

## 4. 일정과 규모

**총 6~12개월.** 임계경로는 GPU 가 아니라 **실측 캠페인**(날씨·사이트 확보·기체 조달·비행 허가)이다.

| 단계 | 내용 | 기간 | 실측 | GPU |
|---|---|---|---|---|
| **P0 배관** | T1~T5 (데이터셋 층 · 궤적 · σ(t) 주입 · 3팔 어댑터 · 정규화) | **2~3주** | 0 | 0 |
| **P1 게이트** | 급소 실험 결론 + T6~T8 sim-to-sim 3×3 → **GO/NO-GO** | **2~3주** | 0 | 중 |
| **P2 생산** | σ 격자 재생성(메시 개편 반영 + phantom3) · 자세축 배선 · 위상표 캐시 · 대량 생성 | **3~4주** | 0 | 높음 |
| **P3 사이트+파일럿** | 실측 사이트 트윈 씬(300~600 LOC + 메시) · 파일럿 2종×5비행 → 분산 추정 | **4~6주** | 파일럿 | 중 |
| **P4 본 캠페인** | 3층 실측(§6-3) · 사이트 2곳 · 기체당 10~15비행 · real↔real2 · 배경 · 교정표적 | **6~8주** | 본 | 0 |
| **P5 분석·집필** | 3팔 × 2정규화 × {sim, real} · paired bootstrap · 투고 | **6~8주** | 0 | 중 |

합계 **23~32주 ≈ 6~8개월**. 재실측·리비전·날씨 손실 버퍼를 얹으면 **6~12개월**이 정직한 폭이다.

**P1 이 게이트다.** P1 에서 NO-GO 가 나오면 P2 이후를 태우지 않는다 — 그게 이 일정의 요점이다.

투고처는 **IEEE 레이다 계열**(TAES / Trans. Radar Systems / JSAC ISAC). ⛔ SenSys·MobiSys·ICASSP 제외
— 우리 인용 그래프가 전부 IEEE 레이다·전파·통신이다.

---

## 5. ⚠ 이 방향이 실패하는 조건

| ID | 조건 | 무엇을 뜻하나 | 판정 시점 |
|---|---|---|---|
| **K1** ⭐ | **sim-to-sim 3×3 의 비대각−대각 차이가 잡음 이내** (Δ의 95% CI 가 0 포함, 5 seeds 전부) | 표적모형이 검출을 안 바꾼다 → **ablation 이 0 이면 논문의 뼈대가 없다** | **P1** (= 급소 실험이 지금 묻고 있는 질문) |
| **K2** ⭐ | **N1(정합)에서 차이가 사라지고 N2(무정합)에서만 남는다** | 우리 기여가 **스칼라 σ 1개**로 환원된다. 메시·SBR·PO·재질가중을 정당화할 수 없다 → 방향 축소(측정 앵커 논문으로 전환) | P1 |
| **K3** | 실측 테스트셋에서 **세 팔이 전부 chance 근처로 붕괴** | 도메인 격차가 표적모형 효과를 압도. ⚠ 이게 **기본값**이다(§3-2). 캘리브레이션(배경 주입·분포정렬) 후에도 붕괴면 접는다 | P4~P5 |
| **K4** | 실측이 σ 를 못 낸다 — 교정구 세션 드리프트 > 1 dB, 또는 지면유령을 레인지게이팅으로 못 뗀다 | utility 는 살아도 **fidelity 축이 죽는다** (MEASUREMENT_PLAN §1-1/§1-5 실패조건) | P3 파일럿 |
| **K5** | Phantom 3 앵커에서 **큐브가 우리 σ 만큼 맞는다** | 메시 파이프라인에 값어치가 없다 → Arm O 의 존재 이유가 사라진다 | Phantom 3 라운드(진행 중) |
| **K6** | PTD 부호 수리 후에도 대역기울기 격차가 2배 이상 남고, 그 격차가 **세 팔 차이보다 크다** | 밴드축 주장 포기 → 단일 밴드로 축소 | `wjogpc7w1` 종료 후 |
| **K7** | **무학습 CFAR 이 모든 팔의 학습형 검출기보다 실측에서 좋다** | ML 프레이밍 폐기 → 순수 *예측-대-달성* 링크버짓 논문으로 **피벗**(kill 이 아니라 전환) | P5 |

⚠ K1 과 K2 는 **실측 전에** 판정된다. 이 설계의 가장 값어치 있는 성질이 그것이다 —
**실측 예산을 태우기 전에 죽일 수 있다.**

---

## 6. 기존 계획과의 접속

### 6-1. Phantom 3 눈감기 검증 (`wsju86tog`)

- fidelity 축의 **외부 앵커**. Arm O 의 σ 오차막대를 준다.
- ⭐ 그 라운드의 **큐브 대조군이 곧 Arm C 의 씨앗**이다. 재사용 → Arm C 개발비 ≈ 0.
- K5 의 판정 자리.

### 6-2. 급소 실험 (`whlerhmfn`) — *표적모형이 검출을 바꾸는가*

- **K1 의 사전 판정이다.** 이 계획 전체의 GO/NO-GO 스위치가 거기 있다.
- 결과가 "바꾼다" → P0~P1 진행. "안 바꾼다" → K1 발동, 이 문서는 보류.
- ⚠ 급소 실험이 단일 CPI·단일 자세로 물었다면, 이 계획은 **pass 단위 시간축**을 추가한다 —
  스칼라 σ 는 드롭아웃을 만들 수 없으므로 시간축이 차이를 키우는 방향이다(§2-4).

### 6-3. 실측 3층 설계 (RESUME §8-7 · `docs/MEASUREMENT_PLAN.md`)

| 층 | 원래 목적 | **이 계획에서의 역할** |
|---|---|---|
| 1층 σ(f) 레인지 (능동 모노 · 교정구 · 서브밴드) | 우리 기체의 절대 σ·A(f) | **fidelity 앵커** + **N2 의 레벨 근거** |
| 2층 파형축 (ISM 한 곳) | 파형 규약 확인 | 조명 파형 검증 |
| 3층 비행 검출 | 탐지 성능 | ⭐ **utility 실측 테스트셋** = ablation 의 평가면 |

⭐ **3층 설계에 두 가지를 추가해야 한다** (지금 MEASUREMENT_PLAN 에 없다):
1. **real↔real2 반복 수집 1세트** — 같은 기종·같은 배치를 안테나 위치만 바꿔 재수집. 없으면 격차의 눈금이 없다.
2. **표적 없는 배경 캡처**를 각 기하마다 — 학습용 데이터보다 이게 더 값어치 있을 수 있다.

⛔ 3×3 교차설계는 취소된 채로 둔다("2.1 GHz 의 WiFi" 는 없고 면허 문제도 있다).

### 6-4. report12 검출 벤치마크 배관

- `experiment_detection.gpu_montecarlo` + `detection_gpu.rd_batch/cfar_batch/peak_batch` 를 **그대로** 쓴다.
  이미 9모드×4Rx×15SNR×9,000 = 4.86 M CPI 시행을 돌린 배관이다.
- **팔 교체 지점은 σ 조회 한 곳**(`build_echo_sionna` 의 `amp = √σ·L/(√4π R1R2)`).
  T3 이 그 자리를 스칼라에서 시계열로 바꾼다.

### 6-5. ⚠ 챔버 방침과의 관계 — **사용자 확인 필요**

상시 방침은 *모든 sionna2 실험을 30×20×11 m 무향실 안에서 프레이밍*한다. 그런데 이 계획은
**실측 사이트 트윈(실외)** 을 요구하고, 실측은 외부 필드테스트다.

제안하는 정리 — **대체가 아니라 추가**:
- **챔버 = 통제군이자 상한(upper bound).** 클러터가 없는 조건에서 표적모형 효과의 **최대치**를 잰다.
- **실외 사이트 트윈 = 전이 시험대.** 챔버 결과를 그대로 운용 성능으로 주장하지 않는다.
- 두 도메인의 격차 자체를 인쇄한다 — 그 격차의 실측 선례가 CageDroneRF 의 42.07% 다(§1-3).

⚠ `assets/scenes/` 는 비어 있다. 실외는 지금 스톡 Sionna 내장 4씬이 전부이고, 자체 사이트는 **300~600 LOC
+ 메시 자산**이 든다. 이건 P3 의 주 비용이다.

### 6-6. novelty 문장의 위치

⛔ *"사이트 트윈 + 계산된 자세분해 σ + 분류"* 조합 **자체**를 novelty 로 쓰면 반증당한다 —
그 조합을 이미 갖춘 데이터셋 논문이 있다(§부록 B-1).

✅ 살아남는 문장: **"조합 + 실측 폐루프"**, 그리고 **"표적모형을 통제변수로 놓고 검출 성능의 함수로 잰 것"**.
즉 우리가 파는 것은 σ 자체가 아니라 **σ 모형 선택이 검출 결론을 얼마나 움직이는가** 다.

---

## 부록 A — 이번 라운드에 내가 직접 연 원문 (축자 + 쪽수)

| # | 출처 | 파일 | 쪽 | 축자 |
|---|---|---|---|---|
| A-1 | 클러터-인지 ISAC (Proc. IEEE 게재판) | `/data/public/sionna_jeong/papers_isac_sionna/paper_sionna_Ray_0723/Clutter-Aware_Integrated_Sensing_and_Communication_Models_Methods_and_Future_Directions.pdf` (41 p.) | pdf 28 | *"α_t,n ∼ CN(0, σ²_t,n) represents the target RCS together with the associated path loss."* |
| A-1b | 같은 문헌 | 같은 파일 | pdf 23 | *"The ToI and UAVs are modeled as simplified 3-D mesh objects imported into Sionna. These meshes are obtained by simplifying publicly available 3-D models in Blender… which keeps the ray-tracing scene lightweight"* |
| A-2 | 저고도 협력센싱 FWA-CSI | `/data/public/sionna_jeong/papers_isac_sionna/2605.07623__lowalt-cooperative-cube-csi.pdf` (13 p.) | pdf 8 | *"The UAV is modeled as a metallic cube located at p = (x, y, 60), where x, y ∼ U[−75, 75]."* |
| A-3 | RadarTwin | `/data/public/sionna_jeong/reference_library/2606.28396__radartwin.pdf` (13 p.) | pdf 12 | *"we regenerate all lateral simulations under two degraded conditions and rerun the identical label-free protocol: uniform… and void… Recognition degrades monotonically: VLM materials 0.227 ± 0.015, uniform 0.192 ± 0.015, void 0.138 ± 0.008 (void not above chance)."* |
| A-3b | 같은 문헌 | 같은 파일 | pdf 11 | *"First, distance is a confound. Pooling distances inflates sim-real feature correlations (to ∼0.8) because both domains vary with range. Distance-matched, per-feature correlations peak near 0.5…"* |
| A-4 | 같은 문헌 | 같은 파일 | pdf 9 | *"absolute radiometry does not survive the sim-to-real gap: system gain and room-dependent multipath compression shift every level, and the simulator over-separates material contrast."* |
| A-5 | White 외, IEEE Trans. Radar Systems 2023 (DOI 10.1109/TRS.2023.3326317) | 이번에 내려받아 연 Birmingham AAM 사본 15 p. — `https://pure-oai.bham.ac.uk/ws/files/208677443/RevisedManuscript.pdf` ⚠ 아카이브에 없다. **아카이브로 옮길 것** | pdf 13 | *"The drone recalls of the two multi-rotor models incorporating all four motor speeds medians fell from the real baseline of 88.4% to 80.1% (sub-CPI) and 78.8% (per-CPI)."* / pdf 2: *"achieved a classification accuracy of 86.6% compared to the real benchmark accuracy of 89.7%"* |
| A-5b | 같은 문헌 | 같은 파일 | pdf 13 | *"As the synthetic fidelity decreases, the bird recall gets higher, thus showing that the model is biased towards predicting difficult targets as birds, which is an operationally ineffective outcome."* |
| A-6 | 같은 문헌 | 같은 파일 | pdf 11 | *"The simulated target's 1-D timeseries returns are summed elementwise with the background signal - extracted, injecting the simulated target into a real background."* |
| A-7 | Saribekyan 외, IEEE CITS 2026 | `…/published_by_venue/IEEE_CITS_2026/2607.04400__saribekyan_sim2real-positioning.pdf` (8 p.) | pdf 7 | *"These results support the main qualitative claim of the paper: physical plausibility alone is not a reliable predictor of sim-to-real transfer."* |
| A-8 | CageDroneRF, IEEE T-AES | `/data/public/sionna_jeong/papers_isac_sionna/new_0731/2601.03302__cagedronerf-benchmark.pdf` (17 p.) | pdf 11 | *"…struggles significantly with model-level identification (42.07%). This indicates poor domain generalization from indoor to outdoor environments."* |
| A-8b | 같은 문헌 | 같은 파일 | pdf 4 | *"DroneRF [77] includes only three drone models in a clean controlled environment, producing near-ceiling benchmark accuracy that transfers poorly to operational settings."* |
| A-8c | 같은 문헌 | 같은 파일 | pdf 12 | *"accuracy increases to 89.42% for Modulation, 87.34% for Protocol, and 69.63% for Model. The most significant gain (+27.56 pp) is observed at the model level, the task most sensitive to environmental shifts."* |
| A-9 | 물리기반 디지털트윈 FMCW 재실추정 | arXiv 2601.17871 (이번에 내려받아 연 원문 5 p.) ⚠ 아카이브에 없다. **아카이브로 옮길 것** | pdf 3 | *"…resulting in a balanced accuracy close to 50% (chance-level for a binary task)."* / *"the baseline RT model again fails to transfer, achieving balanced accuracy near 33% (random guessing)"* |

⚠ **A-5 내부 불일치 기록**: 같은 논문이 pdf p.12 에서는 실측 drone recall 을 **88.0%**, p.13 에서는
**88.4%** 로 적는다. 우리가 인용할 때는 **p.13 의 88.4 → 80.1** 쌍을 쓰고 이 불일치를 각주로 남긴다.

## 부록 B — 이번 라운드에 원문을 못 연 항목 (⚠ 미검증 — 인용 전 원문 확인)

| # | 주장 | 출처(에이전트 JSON 경유) | 조치 |
|---|---|---|---|
| B-1 | 사이트 트윈 + CADFEKO 자세분해 RCS + 레이더 큐브를 다 갖춘 UAV 데이터셋이 존재하고, 그 sim-to-real 근거는 RGB 경로뿐 | LAMBDA (arXiv 2607.03826), `s2r_prior.papers[lambda_uav]` | §6-6 의 novelty 문장이 여기 걸려 있다. **덱·논문에 쓰기 전 원문 확인 필수** |
| B-2 | 온라인 CAD 프로펠러 vs 레이저스캔 메시의 마이크로도플러 상관 0.7~0.8 대 지속적 저하 | Moore 외, IET RSN 2023, `s2r_prior.papers[moore2023_iet]` | 메시 충실도 정당화의 외부 근거. 원문 확인 후 사용 |
| B-3 | 합성 학습 시 4,560 파라미터 템플릿이 대형망을 실측에서 압도 | BatStation (arXiv 2509.06898), `s2r_prior.papers[batstation]` | §2-6 "모델을 키우지 않는다"의 근거. 원문 확인 후 사용 |
| B-4 | 무라벨 빈방 10초 보정으로 chance → 97% | 부록 A-9 와 같은 논문. 붕괴 수치(50/33%)는 **내가 확인함**, **97% 는 미확인** | 붕괴 쪽만 인용. 회복 수치는 보류 |

## 부록 C — 부재주장 원장 (모집단을 밝힌 계수 진술)

- *"사이트 트윈 + 물리적으로 계산된 자세분해 σ + 분류 + 실측 전이"* 4자를 다 갖춘 **드론** 논문:
  **정독 33편(아카이브 전문검색 313편 범위) 중 0편.** ⚠ 이 계수는 다른 에이전트의 정찰 결과이며,
  내가 재현하지 않았다. 논문에 쓰려면 검색어·모집단을 다시 고정해 재수행해야 한다.
- 아카이브 전문 스캔 316편 중 *expected calibration error / reliability diagram* 사용 **0편**
  → 우리도 ECE 를 쓰지 않는다. ⚠ 같은 단서(재현 안 함).
- ⛔ *"아무도 안 했다"* 형태의 문장은 이 문서 어디에도 쓰지 않았다.

---

## 부록 D — 다음 세션이 바로 집을 것

1. **P0 T1~T5 착수** (실측 0, GPU 0). 순서: T4 어댑터 인터페이스 → T3 σ(t) 주입 → T2 궤적 → T1 writer → T5 정규화.
2. `rcs_anchor` · Phantom 3 종료 확인 → **T6 큐브 격자 + 큐브 자세평균 σ** (§2-2 의 미계산 항목).
3. **급소 실험 결과 회수 → K1 판정.**
4. MEASUREMENT_PLAN 에 **real↔real2 1세트 + 기하별 배경 캡처** 추가 (§6-3).
5. §6-5 챔버 방침 관계를 사용자에게 확인받는다.
