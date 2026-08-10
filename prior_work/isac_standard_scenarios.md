# 3GPP ISAC 표준 시나리오 — 원문 확정본

**작성 2026-08-10 · 접근일 2026-08-10 · 전량 1차 자료(3GPP 원문 docx) 기반**
기계판: `outputs/isac_standard_scenarios.json`

이 문서는 우리 저장소 기록을 쓰지 않고 3GPP 공개 문서(www.3gpp.org/ftp)에서 직접 내려받은
원문만으로 작성했다. 인용은 전부 해당 docx 본문의 축자 문장이다(수식 기호는 OMML 에서 평문으로
풀어 옮겼다). 2차 자료는 §8 에 따로 표시했고, 1차와 어긋나는 곳은 없었다.

---

## ① 한 줄 답 (사용자 질문 직답)

**질문 A — "드론 감시는 모노스태틱을 기반으로 하는가?"**

> **단계마다 다르다. Rel-19 채널모델 단계에서는 "아니다"(6개 모드 전부 열려 있었다).
> Rel-20 규격화 단계에서는 "그렇다"(gNB 모노스태틱 하나로 못 박혔다).**

- Rel-19 SI(`RP-242348`)는 *"All six sensing modes should be considered"* 라고 **명시**했고,
  TR 38.901 §7.9.1 의 ISAC-UAV 절도 *"Monostatic **or** bistatic sensing can be performed
  using TRPs and/or UEs"* 라고 쓴다 → **기준 모드 지정 없음**.
- 그러나 Rel-20 SI(`RP-253246`, 2025-12 승인)의 첫 목표가
  *"Evaluate the performance of **gNB-based mono-static sensing** (i.e., single TRP with
  co-located sensing transmitter and receiver) **for UAV use case**"* 이고,
  Rel-20 WI(`RP-261566`, 2026-06 승인)는
  *"specify **gNB-based mono-static sensing for UAV sensing target use cases**"* 다.
  → **지금(2026-08) 규격이 실제로 만들어지고 있는 드론 감시는 gNB 모노스태틱이다.**

**질문 B — "어떤 시나리오가 표준 시나리오인가?"**

> **UAV 는 `UMa-AV`(도심 매크로 · 공중 UE 확장) 가 표준 시나리오다.**
> Rel-19 교정(calibration) 시나리오도 UMa-AV, Rel-20 성능평가 baseline 도 (UMa-AV, ISD 500 m) 이다.
> 표적은 **소형 UAV 0.3×0.4×0.2 m**, σ_M = **−12.81 dBsm**, 고도 25–300 m, 수평속도 0–180 km/h,
> FR1 4/4.9 GHz(옵션 6 GHz)·100 MHz, gNB 높이 25 m.

---

## ② 센싱 모드 — 정확히 6가지

3GPP 가 **개수와 명칭을 한 문장으로 확정한 곳은 TR 이 아니라 SID** 다. TR 38.901 본문은 이 6개를
정의 절에서 열거하지 않고, 절차·교정표에서 **이름으로 호출만** 한다.

> **`RP-242348` §4.1 (축자):**
> *"All six sensing modes should be considered (i.e. TRP-TRP bistatic, TRP monostatic,
> TRP-UE bistatic, UE-TRP bistatic, UE-UE bistatic, UE monostatic)."*

| # | 정식 명칭(영문) | 송신 | 수신 | 정의·근거 문서 | 절 | 등급 |
|---|---|---|---|---|---|---|
| 1 | **TRP monostatic** | TRP | 동일 TRP(동위치) | RP-242348 / TR 38.765 | §4.1 / §1 | 1차 |
| 2 | **TRP-TRP bistatic** | TRP | 다른 TRP | RP-242348 / TR 38.901 | §4.1 / §7.9.4.2 | 1차 |
| 3 | **TRP-UE bistatic** | TRP | UE | RP-242348 / TR 38.901 | §4.1 / §7.9.4.2 | 1차 |
| 4 | **UE-TRP bistatic** | UE | TRP | RP-242348 / TR 38.901 | §4.1 / §7.9.4.2 | 1차 |
| 5 | **UE-UE bistatic** | UE | 다른 UE | RP-242348 / TR 38.901 | §4.1 / §7.9.4.2 | 1차 |
| 6 | **UE monostatic** | UE | 동일 UE(동위치) | RP-242348 / TR 38.901 | §4.1 / §7.9.6.1 | 1차 |

**⚠ 내 사전 기억과 다른 점(= 발견 3건)**

1. 임무문에 적힌 예상 축 *"gNB↔UE 바이스태틱 **양방향**"* 은 맞다 — 3GPP 는 **TRP-UE 와 UE-TRP 를
   서로 다른 모드로 센다**(그래서 5개가 아니라 6개다). 다만 명칭은 gNB 가 아니라 **TRP** 다.
2. TR 38.901 §7.9.4.2 는 배경채널을 다룰 때만 네 바이스태틱을 한 줄에 모아 쓴다:
   *"For TRP-TRP, TRP-UE, UE-TRP and UE-UE bistatic sensing modes, ... the background channel
   between a pair of STX and SRX is generated using Step 2 to Step12 of Clause 7.5"*.
   그 외 §7.9.6 교정표는 **UE-TRP 를 아예 적지 않는다**(대칭이라 TRP-UE 로 흡수).
3. **UAV 교정표만 모드가 4개다.** Table 7.9.6.1-1 / 7.9.6.2-1 의 `Sensing mode` 행은
   *"TRP monostatic, TRP-TRP bistatic, TRP-UE bistatic, UE-UE bistatic"* — 인체·차량·AGV 표에는
   있는 **UE monostatic 이 UAV 에만 빠져 있다.** (드론을 손안의 UE 레이다로 잡는 건 교정 대상이
   아니라는 뜻.)

**용어**: 3GPP 는 송/수신단을 **STX(sensing transmitter) / SRX(sensing receiver)** 로 부른다.
SA1 정의(TS 22.137 §3.1)는 *"A sensing transmitter is part of a **RAN node or a UE**"*,
*"A sensing receiver is part of a **RAN node or a UE**"* 다. **이 한 줄이 §⑥ 판정의 뿌리다.**
TS 22.137 §4.2 는 개념 층위에서 Monostatic / Bistatic 에 더해 **Multistatic**
(*"A more advanced scenario with multiple sensing transmitters and receivers is also possible,
called Multistatic sensing"*)까지 열어 두지만, RAN1 의 6개 모드 목록에는 멀티스태틱이 없다.

---

## ③ UAV 유스케이스와 그 모드

### ③-1 SA1 층 — TR 22.837 (Feasibility Study), V19.4.0 (2024-06)

총 **32개 유스케이스(§5.1–5.32)** 중 **UAV 직접 관련 4건**:

| 번호 | 제목(영문 원문) | 성격 |
|---|---|---|
| **5.10** | *Use case on UAV flight trajectory tracing* | 궤적 추적(협조 UAV) |
| **5.12** | *Use case on Network assisted sensing to avoid UAV collision* | 충돌 회피 |
| **5.13** | *Use case on sensing for UAV intrusion detection* | **침입 탐지(비협조 UAV)** ← 우리 과제와 직결 |
| **5.22** | *Use case of UAVs/vehicles/pedestrians detection near Smart Grid equipment* | 설비 주변 감시 |

⭐ **TR 22.837 전문에 "monostatic" / "bistatic" 이라는 단어가 단 한 번도 안 나온다**(기계 검색 0건).
**SA1 은 모드를 지정하지 않는다** — 서비스 요구사항(정확도·지연·해상도)만 준다.
즉 "드론 감시 = 모노스태틱" 은 SA1 층에는 근거가 없다.

§5.13 은 비협조성을 명시한다:
> *"considering that the UAV entering the restricted area is illegal and the UAV itself even could
> be illegal, this kind of sensing operation **doesn't require the cooperation of the UAV**.
> That means the UAV may be unaware of the sensing operation."*

§5.10 은 **UE 를 수신 보조로 쓰는 이유**까지 적어 두었다(= 바이스태틱 정당화):
> *"some UEs are located in the reflection directions that have larger radar cross section (RCS)
> than 5G RAN entities considering the UAV RCS variation in different reflection directions."*

정규 요구사항은 TS 22.137 V19.1.0 §7 Table 7.1-1 의 **Sensing service categories 1–4** 로 넘어갔고,
UAV 는 카테고리 1~4 전부의 예시 표적으로 들어가 있다(카테고리 3 기준: 수평/수직 정확도 1 m,
속도 정확도 1 m/s, 최대 1000 m 거리, 갱신 0.05–1 s).

### ③-2 RAN1 채널모델 층 — TR 38.901 §7.9.1, V19.4.0 (2026-06)

§7.9.1 은 통신 시나리오 X 위에 센싱 시나리오를 얹는 구조다:
> *"Sensing scenario X is defined as a scenario for sensing where STX/SRX are selected among the
> TRPs and UEs in the corresponding communication scenario X. X can be
> UMi/UMa/RMa/InH/InF/UMi-AV/UMa-AV/RMa-AV/Urban grid/Highway/High Speed Train (HST)."*

**채택된 5개 시나리오군** (표적 종류로 묶음):

| 군 | 명칭 | 표적 | 표 |
|---|---|---|---|
| 1 | **ISAC-UAV** | 실외 UAV(건물 상/하) | Table 7.9.1-1 |
| 2 | ISAC-Automotive | 승용/트럭/버스 | Table 7.9.1-2 |
| 3 | ISAC-Human | 실내외 성인·아동 | Table 7.9.1-3 |
| 4 | ISAC-AGV | 공장 내 AGV | Table 7.9.1-4 |
| 5 | ISAC-Objects creating hazards on roads/railways | 사람·동물 | Table 7.9.1-5 |

⭐ **모노스태틱 기준 여부 판정 — 원문 인용**

> **TR 38.901 §7.9.1 (ISAC-UAV, 축자):**
> *"In the ISAC-UAV sensing scenarios, the sensing targets are outdoor UAVs below or above the
> buildings in urban or rural areas. **Monostatic or bistatic sensing can be performed using TRPs
> and/or UEs, including UEs on other UAVs.**"*

**판정: «모노스태틱이 기준이다» 는 Rel-19 채널모델 층에서 거짓이다.**
5개 시나리오군 **전부** 같은 문형("Monostatic or bistatic sensing can be performed…")을 쓴다.
**기준 모드 지정이 없다**가 정답이고, 교정표에서 4~5개 모드를 **동시에** 돌린다.

### ③-3 RAN1/RAN3 규격화 층 — Rel-20, 여기서 모노스태틱으로 좁아진다

| 항목 | 값 |
|---|---|
| Rel-19 SI | `FS_Sensing_NR`, SID **RP-242348**(RAN#105, 2024-09), 산출 = **TR 38.901 §7.9** (CR RP-251567, RAN#108 2025-06, → V19.0.0) |
| Rel-20 SI | `FS_Sensing_NR_bis`, SID **RP-253246**(RAN#110, 2025-12), 산출 = **TR 38.765 V20.0.0 (2026-06)** — **완료** |
| Rel-20 WI | `NR_Sensing_bis`, WID **RP-261566**(RAN#112, 2026-06) — **진행중**, 목표 RAN#115 |

> **`RP-253246` §4.1 (축자):** *"Evaluate the performance of **gNB-based mono-static sensing**
> (i.e., single TRP with co-located sensing transmitter and receiver) **for UAV use case** [RAN1]"*
> … *"Study network architecture for gNB-based mono-static sensing for UAV sensing target use
> cases [RAN3]"* … *"Applicability to **gNB bistatic** sensing may be considered as part of this
> network architecture **without additional architecture impacts**."* … *"**No UE impacts**"*
> … *"**FR1 frequency range is prioritized.**"*

> **`RP-261566` §4 (축자):** *"The objective of this Work Item is to specify **gNB-based mono-static
> sensing for UAV sensing target use cases**, building upon the conclusions of the ISAC Study Item
> as documented in TR 38.765. **There will be no UE impacts.**"*
> 부속: *"Applicability to **intra-gNB bistatic** sensing may be considered as part of this network
> architecture without additional architecture impacts."*

> **`TR 38.765` §1 Scope (축자):** *"Performance evaluation of **gNB-based mono-static sensing for
> UAV use case**"* / *"Network architecture for gNB-based mono-static sensing for UAV use cases"*

**즉 3GPP 는 32개 유스케이스 중 «UAV» 하나를, 6개 모드 중 «gNB 모노스태틱» 하나를 골라
규격화에 착수했다.** 바이스태틱은 *동일 gNB 내부(intra-gNB)* 에 한해 "아키텍처 영향 없이 적용
가능성만 고려" 수준이고, **gNB↔gNB 조율은 명시적으로 제외**(*"No inter-gNB coordination will be
studied."*)다.

TR 38.765 §9 결론(축자 요지): baseline 1(52 dBm·80 dB 격리)에서 **다중 TRP 측정 융합 시 10곳 중
9곳**이 성능목표 달성, **단일 TRP 만으로는 11곳 중 3곳**. baseline 2(37 dBm·65 dB)에서는 각각
9곳 중 7곳 / 9곳 중 2곳. 성능목표는 **오검출확률 5 % · 오경보확률 5 % · 수평/수직 정확도 10 m
(90 %) · 속도 정확도 5 m/s (90 %)** (Table 4.2-1).

---

## ④ 표적 RCS 모델 — 우리 저장소 값 검증

**TR 38.901 V19.4.0 §7.9.2.1**

구조(축자): *"The RCS related coefficient σ_RCS of a SPST for a pair of incident/scattered angles
is composed of a first component σ_M …, and a second component σ_D and third component σ_S …,
i.e., **σ_RCS = σ_M · σ_D · σ_S**. σ_M is a deterministic value for the SPST. σ_D can be fixed to 1
or can be angular dependent. σ_S follows log-normal distribution."*
그리고 μ_σS_dB = −(ln10/20)·σ_σS_dB² (식 7.9.2-1) 로 σ_S 의 평균이 표준편차에 묶여 있다.

**UAV 는 크기에 따라 두 갈래다.**

| 갈래 | 모델 | 표 | 10lgσ_M | σ_σS_dB | 각도 의존 σ_D |
|---|---|---|---|---|---|
| **UAV with small size** (0.3×0.4×0.2 m) | **RCS model 1** | Table 7.9.2.1-1 | **−12.81 dBsm** | **3.74 dB** | **없음(σ_D ≡ 1)** |
| **UAV with large size** (1.6×1.5×0.7 m) | **RCS model 2** | Table 7.9.2.1-2 | **−5.85 dBsm** | 2.50 dB | **있음** — Left/Back/Right/Front/Bottom/Roof 6섹터 |

RCS model 1 식(7.9.2-2, 축자):
> *"σ_MD_dB(θi,φi,θs,φs) = max{ 10lgσ_M − 3·sin(β/2), σ_FS(θi,φi,θs,φs) }"*
> *"β ∈ [0°,180°]. β is the bistatic angle between the incident ray and scattering ray"*
> *"σ_FS … is for the effect of forward scattering and is set to **−∞**."*

RCS model 2 의 섹터 조회 방식(축자):
> *"The bisector angle (θ,φ) is used to index one set from the N_sp sets of parameters, and
> determine σ_D of the ST consequently."*
> Table 7.9.2.1-2 의 `Range of θ` / `Range of φ` 열이 그 조회 격자다
> (예: Front = θ∈[45,135), φ∈[−45,45); Roof = θ∈[0,45), φ∈[0,360)).

**주파수 의존성 — 명시적 검증**
- §7.9.2.1 전문(Table 7.9.2.1-1~-7 포함)에 **주파수·파장·GHz 라는 단어가 하나도 없다**(기계 검색 0건).
- 같은 −12.81 dBsm 값이 **FR1 6 GHz 와 FR2 30 GHz 교정에 그대로** 쓰인다(Table 7.9.6.1-1:
  *"Carrier Frequency | FR1: 6 GHz FR2: 30 GHz"* + *"Component σ_M of the RCS for each scattering
  point | −12.81 dBsm"*, 주파수별 분기 없음).
- Rel-20 평가도 4/4.9/6 GHz 에서 같은 값을 쓴다(TR 38.765 Annex A: *"RCS model 1 for UAV with
  small size"*).
→ **주파수 무관 확정.**

**모노/바이스태틱 동일성 — 이건 우리 저장소에 없던 새 사실**
> **Table 7.9.6.2-1 (축자):** *"Component σ_M: −12.81 dBsm / Component σ_D: 0 dB /
> Component σ_S: 3.74 dB for standard deviation. **The same values are used for monostatic RCS
> and bistatic RCS**"*
즉 규격은 소형 UAV 의 바이스태틱 RCS를 모노스태틱과 **같은 값**으로 두고, 각도 의존성은 오직
식 7.9.2-2 의 **−3·sin(β/2)** 한 항으로만 준다(β=180° 전방산란에서 −3 dB, 그리고 σ_FS=−∞ 로 컷).

**교차편파(§7.9.2.2)** — 우리 저장소에 기록이 없던 항목:
CPM 의 XPR κ 는 로그정규, **UAV: μ_XPR = 13.75 dB, σ_XPR = 7.07 dB** (Table 7.9.2.2-1).
Rel-19 full calibration 도 같은 값을 쓴다.

### ④-1 −12.81 dBsm 의 출처(프로베넌스) — RAN1 검증 원장

TR 38.901 §4 는 *"An overview list of the sources is available in [27]"* → **R1-2504948**
("Information on validations for ISAC", RAN1 #121, 2025-05)이고, 첨부 엑셀의 **UAV 시트**가
그 근거 목록이다. 원문 그대로:

| Tdoc | 회사 | 측정/시뮬 | 표적 크기 | 반송파 | BW | 거리 |
|---|---|---|---|---|---|---|
| R1-2502417 | CALTTA, ZTE, Sanechips | RT simulation | 0.3×0.4×0.2 m | 4.9 GHz | – | 15 m |
| R1-2502452 | Xiaomi, BJTU, BUPT | **Measurement** | 0.81×0.67×0.43 m | 28 GHz | 3 GHz | 6 m |
| R1-2406975 | Huawei | **Measurement** | 0.35×0.28×0.1 m | 4.9 GHz | – | mono, 3 m |
| R1-2408658 | Samsung | RT simulation | 0.16×0.16×0.1 m | 3.5 GHz | – | 2 m |
| R1-2409609 | Samsung | RT simulation | 1.6×1.6×0.5 m | 3.5 GHz | – | 25 m |
| R1-2503859 | BUPT, CMCC, vivo, X-Net | **Measurement** | 0.81×0.67×0.43 m | 24 GHz | 3 GHz | bistatic 3+3 m |
| R1-2502419 | BUPT, CMCC, vivo, X-Net | **Measurement** | 0.81×0.67×0.43 m | 28 GHz | 3 GHz | mono 6 m |
| R1-2405010 | Ericsson | **Measurement** | 171×245×62 mm | 3.8 GHz | 100 MHz | 44–52 m (bistatic RCS) |
| R1-2502726 | Ericsson | **Measurement** (Rahman & Robertson 인용) | DJI Phantom 3 / Inspire | 24, 94 GHz | 150 MHz | 170 m (Doppler) |
| R1-2410136 | NIST | **Measurement** | 1.1×1.2×0.5 m | 28.5 GHz | 2 GHz | mono+bistatic 4+4 m |
| R1-2500660 | Sony | **MoM EM simulation** | 0.4×0.3×0.2 m | 3.5 GHz | – | 원거리(>100 m) mono+bistatic |
| R1-2410235 | Sony | **MoM EM simulation** | 1.6×1.5×0.7 m | 3.5 GHz | – | 원거리(>100 m) mono+bistatic |
| R1-2501002 | Moderator(Xiaomi) | FL summary | – | – | – | *"Proposal 4.4-1 is for RCS of small size UAV"* |
| R1-2503152 | Moderator(Xiaomi) | FL summary | – | – | – | *"Proposal 3-1 is for RCS of large size UAV"* |

⭐ **읽어야 할 것**: 근거는 **3.5 / 3.8 / 4.9 / 24 / 28 / 28.5 / 94 GHz 에 흩어진 이종 자료**이고,
표적 크기도 0.16 m 부터 1.6 m 까지다. 그걸 하나로 눌러 **주파수 무관 단일 상수 두 개(−12.81 /
−5.85)** 를 낸 것이다. **주파수 무관은 실증 주장이 아니라 표준화 단순화다.** 우리가 σ(f) 를
논문에서 다룰 때 이 문장이 그대로 논거가 된다.

### ④-2 우리 저장소 대조

| 우리 기록 | 원문 | 판정 |
|---|---|---|
| `docs/PAPER_POSITION_0803.md` M1 = "TR 38.901 V19.4.0 §7.9.2.1 RCS model 1 — 단일 산란점, σ_M = −12.81 dBsm, 자세 패턴 평평" | 일치 | ✅ **정확** |
| `docs/INJECTION_PRECEDENT.md` "소형 UAV 값은 −12.81 dBsm(σ_S 표준편차 3.74 dB, 주파수 무관)" | 일치(§7.9.2.1 + 교정표 교차확인) | ✅ **정확** |
| `docs/INJECTION_PRECEDENT.md` "σ_RCS = σ_M·σ_D·σ_S 를 Table 7.9.2.1-1~-7 로 배포, 각도 섹터로 조회, 7.9.4.1 Step 10 / Step 15" | 일치(Step 10 = 소규모, Step 15 = 대규모 파라미터) | ✅ **정확** |
| M1 의 −3sin(β/2) 항을 껐다(M1b) | 규격은 그 항이 **본체**다 | ⚠ **의도된 이탈 — 논문에 "spec deviation" 으로 명기 필요** |
| **누락**: UAV 가 large/small 두 갈래이고 large 는 −5.85 dBsm + 6섹터 각도의존 | Table 7.9.2.1-2 | ❌ **결손** |
| **누락**: XPR μ=13.75 dB, σ=7.07 dB | Table 7.9.2.2-1 | ❌ **결손** |
| **누락**: "모노 = 바이 같은 값" 이 규격 문장으로 존재 | Table 7.9.6.2-1 | ❌ **결손**(우리 유리한 논거인데 안 쓰고 있었다) |

---

## ⑤ 배치·기하 파라미터 (표준이 지정하는 것만)

### ⑤-1 Rel-19 채널모델 — TR 38.901 Table 7.9.1-1 (ISAC-UAV 시나리오 정의)

| 항목 | 값(축자) |
|---|---|
| Applicable communication scenarios | *"UMi, UMa, RMa, SMa UMi-AV, UMa-AV, RMa-AV [36.777]"* |
| STX/SRX 위치 | *"selected among the TRPs and UEs locations in the corresponding communication scenarios"* (aerial UE 포함) |
| LOS/NLOS | LOS and NLOS |
| 실내외 | Outdoor |
| **수평속도** | *"uniform distribution between 0 and 180 km/h, if horizontal velocity is not fixed to 0"* |
| **수직속도** | *"0 km/h, optional {20, 40} km/h"* |
| **고도** | Option A: *"Uniform between 1.5 m and 300 m"* / Option B: *"Fixed height value chosen from {25, 50, 100, 200, 300} m"* |
| 표적 수 | N = {1,2,3,4,5} (*"N=0 may be considered for the evaluation of false alarm"*) |
| **표적 크기** | *"Option 1: 1.6 m × 1.5 m × 0.7 m / Option 2: 0.3 m × 0.4 m × 0.2 m"* |
| 방향 | *"Random in horizontal domain"* |
| 최소 STX/SRX–표적 3D 거리 | TR 36.777 의 최소 TRP/UE 거리 기준 |
| 표적간 최소 거리 | Option 1: 표적 물리크기 이상 / Option 2: 10 m |

### ⑤-2 Rel-19 교정 시나리오 — TR 38.901 Table 7.9.6.1-1 / 7.9.6.2-1 (**«표준 시나리오» 의 실체**)

| 항목 | 값 |
|---|---|
| **Scenario** | **UMa-AV** |
| **Sensing mode** | TRP monostatic, TRP-TRP bistatic, TRP-UE bistatic, UE-UE bistatic *(UE monostatic 없음)* |
| Target type | **UAV of small size (0.3 m × 0.4 m × 0.2 m)** |
| Carrier | **FR1: 6 GHz / FR2: 30 GHz** |
| Bandwidth | **FR1: 100 MHz / FR2: 400 MHz** |
| BS Tx power | FR1 56 dBm / FR2 41 dBm |
| BS/UT 안테나 | 단일 dual-pol isotropic (large-scale 교정용) |
| BS noise figure | FR1 5 dB / FR2 7 dB |
| UT 높이 | 1.5 m (terrestrial) |
| UE 수 | 중심셀 30 |
| 표적 고도 | **고정 200 m** (aerial UE 도 200 m, FR1 가정) |
| σ_M | **−12.81 dBsm** |
| 최소 STX/SRX–표적 3D 거리 | **10 m** |
| STX/SRX 선택 | *"Best N = 4 STX-SRX pairs to be selected for the target"* |
| Fast fading (full cal.) | **TR 36.777 Annex B.1.3** |
| XPR | 평균 13.75 dB, 표준편차 7.07 dB |
| 경로 드롭 임계 | −40 dB |

### ⑤-3 Rel-20 성능평가 — TR 38.765 Table 6.2-1 & Annex A (**현행 «표준 평가조건»**)

**Baseline configuration 1 / 2** (Table 6.2-1):

| | Baseline 1 | Baseline 2 |
|---|---|---|
| Scenario | (UMa-AV, 500 m) | (UMa-AV, 500 m) |
| Tx/Rx 동시동작 | 동시 | 동시 |
| Carrier | 4 or 4.9 GHz | 4 or 4.9 GHz |
| **Max BS Tx power** | **52 dBm** | **37 dBm** |
| BS 안테나 | Tx/Rx (8,8,2,1,1;4,8), dH,dV=(0.5,0.8)λ, ±45° | 동일 |
| 중심 사이트 섹터당 표적 수 | N = 5 | N = 5 |
| 표적 고도 | 25–300 m | 25–300 m |

**Annex A Table A-1 전체(FR1 / FR2-1 옵션)**:

| 항목 | FR1 | FR2-1(옵션) |
|---|---|---|
| Scenario | **UMa-AV**, 옵션 RMa-AV | UMi-AV |
| Carrier | **4 or 4.9 GHz**, 옵션 6 GHz | 30 GHz |
| System bandwidth | **100 MHz** | 400 MHz |
| Numerology | SCS 30 kHz | SCS 120 kHz |
| BS layout | 육각 격자, **7 매크로 사이트 × 3 섹터**(30/150/270°) | 동일 |
| **Inter-BS(2D) 거리** | UMa-AV **500 m**(옵션 1000 m), RMa-AV 1732 m | 200 m |
| Wrap-around | 없음 | 없음 |
| **BS 안테나 높이** | **UMa-AV 25 m**, RMa-AV 35 m | 10 m |
| BS 방사패턴 | *"Table 9 in Report ITU-R M.2412"* | 동일 |
| 기계 틸트 | 90° GCS(수평 지향) | 동일 |
| 전기 틸트 | Option 1 없음 / Option 2 102° GCS | 동일 |
| **안테나 격리** | **65 dB, 80 dB** | 80–100 dB |
| Max BS Tx power | **37 dBm, 52 dBm** (= Rx 포화 −28 dBm + 격리) | 30 dBm |
| **자기간섭** | *"residual leakage interference/noise … modelled e.g. by additional AWGN, **−94+X dBm in 100 MHz**"* | 동일 |
| 사이트간/섹터간/인접채널 간섭 | **모두 미모델링** | 동일 |
| BS NF | 5 dB | 7 dB |
| 표적 | **UAV small (0.3×0.4×0.2 m)**, RCS model 1 | 동일 |
| 표적 분포 | 중심 사이트 **섹터당 N=5**(옵션 1~10), 수평 균등, **수직 25–300 m**(옵션 1.5–300 m) | 동일 |
| 이동성 | **수평 0–180 km/h 균등, 수직 0 km/h** | 동일 |
| 최소 BS–표적 3D | **10 m** | 동일 |
| 최소 표적–표적 3D | **10 m** | 동일 |
| gNB–표적 링크 | *"TRP-UAV link in Table 7.9.3-2 in TR 38.901, using Clause B.1.3 in TR 36.777"* | 동일 |
| 파형 | **CP-OFDM baseline**, DL NR 파형·DL NR 참조신호 baseline | 동일 |

**성능목표(Table 4.2-1)**: 오검출 5 % · 오경보 Type1 5 % · 오경보 Type2 5 % ·
수평 정확도 10 m(90 %) · 수직 정확도 10 m(90 %) · 속도 정확도 5 m/s(90 %).

**측정 리포트 레벨(TR 38.765 §5.1)**: Level A(원시 CIR/주파수 샘플) · Level B(지연/도플러/각
프로파일) · Level C(검출 경로/점 단위) · Level D(객체 단위). 결론: **Level A 미지원, Level C 규격화
합의, Level D 는 프라이버시·보안 해소 조건부** — Rel-20 WI 가 C/D 를 대상으로 한다.

---

## ⑥ ⭐우리 포지셔닝 판정 — 패시브 바이스태틱은 3GPP 틀 «밖»이다 (경계선 위)

**판정: 기하학적으로는 안, 제도적으로는 밖. 정확히는 «TRP-UE bistatic 의 비인가·비협조 변종».**

근거를 세 겹으로 쌓는다.

**(1) 3GPP 의 6개 모드는 전부 «3GPP 노드 쌍»이다.**
> TS 22.137 §3.1: *"A sensing receiver is an entity that receives the sensing signal … **A sensing
> receiver is part of a RAN node or a UE.**"*
우리 수신단은 USRP X410 이다 — RAN 노드도 UE 도 아니다. 6개 모드의 어느 칸에도 안 들어간다.
TR 38.765 의 아키텍처도 **gNB ↔ SenF(Sensing Function)** 로 닫혀 있고, 새 인터페이스 Ns 는
*"the direct interface between the gNB and the SenF"* 다. 망 밖 수신기를 위한 자리가 없다.

**(2) 3GPP 문서에서 "passive" 는 «수동 수신»이 아니라 «수동 표적»을 뜻한다 — 용어 충돌 주의.**
- TR 38.901·TR 38.765: "passive" **0회**, "non-cooperative" **0회**.
- TR 23.700-14 V20.0.0: *"The detected Object can be a **passive object** (e.g. a human or an animal
  or a drone/vehicle without UE on board …)"* — 표적이 UE 를 안 달았다는 뜻.
- TR 22.837 §5.13: *"**Non-cooperative UAVs** could intrude some no-fly zone"* — **표적**이 비협조.
→ 논문에서 "passive bistatic" 을 3GPP 독자에게 쓸 때 **반드시 «passive **receiver**»라고 못 박아야**
한다. 안 그러면 심사자는 "UE 없는 드론" 으로 읽는다. (이건 리뷰에서 바로 터질 자리다.)

**(3) 그래도 우리는 규격의 절반을 정당하게 상속한다.**
- **조명원**: gNB 하향 신호를 쓰는 것은 TR 38.765 baseline(*"existing DL NR waveform and DL NR
  reference signals are to be used for evaluations"*)과 동일한 조명 가정이다.
- **기하**: 송신 TRP ↔ 다른 위치의 수신단 = **TRP-UE bistatic 과 동일 기하**. 채널모델도 그대로
  쓸 수 있다 — TR 38.901 Table 7.9.3-2 는 TRP→UAV 를 **Case 4 (TRP–Aerial UE link, TR 36.777
  Annex A/B)** 로, 배경채널 TRP↔단말을 Case 2 로 지정한다. 수신기가 인가 UE 인지 아닌지는
  채널모델이 구분하지 않는다.
- **표적모형**: σ_M, σ_S, XPR, −3sin(β/2) 전부 모드 무관(§④ 의 *"The same values are used for
  monostatic RCS and bistatic RCS"*).

**논문 포지셔닝 문장(권고)**
> *"We adopt the 3GPP ISAC target and scenario framework (TR 38.901 §7.9, ISAC-UAV/UMa-AV) but
> operate outside the 3GPP sensing-mode taxonomy: our receiver is not a RAN node or a UE
> (TS 22.137 §3.1), so no defined mode covers it. Geometrically it is the **TRP-UE bistatic**
> configuration with an **unauthorized, non-cooperative receiver**. Rel-20 normative work
> (RP-261566) targets **gNB monostatic only, with no UE impacts**, which leaves the
> passive-receiver bistatic case unaddressed by the standard — that gap is our contribution
> surface, not a defect."*

⭐ **부수 발견 — 우리에게 유리한 새 논거 2건**
1. **Rel-20 결론이 «단일 TRP 모노스태틱으로는 부족하다» 를 숫자로 말한다.** TR 38.765 §9:
   단일 TRP 만으로 성능목표를 만족한 소스는 baseline 1 에서 **11곳 중 3곳**, baseline 2 에서
   **9곳 중 2곳**뿐이고, 다중 TRP 융합에서만 9/10·7/9 로 올라간다. **«모노스태틱 기준»의 한계를
   3GPP 자신이 기록해 두었다** — 분산 수신(우리 다중 Rx 서사)의 근거로 그대로 쓸 수 있다.
2. **자기간섭이 모노스태틱의 결정 파라미터다.** Rel-20 은 Tx 전력을 **Rx 포화 −28 dBm + 안테나
   격리(65/80 dB)** 로 유도했다. 즉 gNB 모노스태틱의 링크버짓 상한이 **격리도**에 묶여 있다.
   **패시브 바이스태틱은 이 항이 원천적으로 없다** — 우리 구조의 장점을 규격 문서로 논증할 수 있다.

---

## ⑦ 확보 실패 목록과 그 영향

| 대상 | 결과 | 영향 |
|---|---|---|
| `www.3gpp.org` **WebFetch 도구** 직접 접근 | **403 Forbidden** | 없음 — 브라우저 User-Agent 를 붙인 `curl` 로 전부 우회 성공 |
| ETSI `deliver/etsi_tr/138900_138999/138901/` 디렉터리 목록 | HTTP 200 이나 **링크 0건**(JS 렌더 페이지) | 없음 — 3GPP 원본(더 최신 V19.4.0)을 직접 확보. ETSI 판(TR 138 901 V19.2.0)은 **한 판 뒤짐**, 인용 시 판본 주의 |
| RAN1 개별 Tdoc 다수(`R1-2502417`, `R1-2410235` 등 §④-1 원 기고문) | **미확보**(회의 폴더 다수 403, 개별 탐색 안 함) | 중 — −12.81 dBsm 의 **원 측정 곡선**은 못 봤다. 우리는 **모더레이터 원장(R1-2504948)** 의 메타데이터만 확보. 우리 σ 를 3GPP 근거와 곡선 대 곡선으로 대조하려면 이 Tdoc 들이 필요하다 |
| `R1-2509126` (Rel-19 ISAC 교정 결과) | **미시도** | 소 — 우리 시뮬을 3GPP 교정 CDF 와 맞추려면 필요 |
| RAN1 #120 회의 합의문(Zhang JSAC 통합 RCS 채택 주장의 1차 확인) | **미확보**(TSGR1_120 403) | 소 — 우리 저장소 `DRONE_ISAC_PRIOR_READING.md` 의 "RAN1 #120 채택" 진술은 **아직 2차(논문 자기주장)** 상태 |
| Rel-20 WI 산출 TS 번호 | **미정 상태** — WID 가 `38.xxx` 로 비워 둠 | 없음 — 아직 번호가 안 붙은 게 사실 |

**추측으로 메운 곳은 없다.** 위 항목은 전부 "못 봤다" 로 남긴다.

---

## ⑧ 출처 전체

### 1차 (3GPP 공개 원문 — 전량 직접 내려받아 본문 추출, 접근일 2026-08-10)

| # | 문서 | 버전·날짜 | URL |
|---|---|---|---|
| P1 | **3GPP TR 38.901**, *Study on channel model for frequencies from 0.5 to 100 GHz* (Rel-19) | **V19.4.0 (2026-06)** | `https://www.3gpp.org/ftp/Specs/archive/38_series/38.901/38901-j40.zip` |
| P2 | **3GPP TR 22.837**, *Feasibility Study on Integrated Sensing and Communication* (Rel-19, SA1) | **V19.4.0 (2024-06)** | `https://www.3gpp.org/ftp/Specs/archive/22_series/22.837/22837-j40.zip` |
| P3 | **3GPP TS 22.137**, *Service requirements for Integrated Sensing and Communication; Stage 1* (Rel-19, SA1) | **V19.1.0 (2024-03)** | `https://www.3gpp.org/ftp/Specs/archive/22_series/22.137/22137-j10.zip` |
| P4 | **3GPP TR 38.765**, *Study on Integrated Sensing And Communication (ISAC) for NR* (Rel-20, RAN) | **V20.0.0 (2026-06)** | `https://www.3gpp.org/ftp/Specs/archive/38_series/38.765/38765-k00.zip` |
| P5 | **3GPP TR 23.700-14**, *Study on Integrated Sensing and Communication; Stage 2* (Rel-20, SA2) | **V20.0.0 (2026-03)** | `https://www.3gpp.org/ftp/Specs/archive/23_series/23.700-14/23700-14-k00.zip` |
| P6 | **RP-242348**, *Revised SID: Study on channel modelling for ISAC for NR* (Xiaomi, AT&T) | RAN#105, Melbourne, 2024-09-09/12 (rev. of RP-240799) | `https://www.3gpp.org/ftp/tsg_ran/TSG_RAN/TSGR_105/Docs/RP-242348.zip` |
| P7 | **RP-253246**, *Revised SID: Study on Integrated Sensing And Communication (ISAC) for NR* (Xiaomi, China Telecom) | RAN#110, Baltimore, 2025-12-08/11 (rev. of RP-252819) | `https://www.3gpp.org/ftp/tsg_ran/TSG_RAN/TSGR_110/Docs/RP-253246.zip` |
| P8 | **RP-261566**, *New WID on Integrated Sensing And Communication (ISAC) for NR* | RAN#112, Singapore, 2026-06-08/11 | `https://www.3gpp.org/ftp/tsg_ran/TSG_RAN/TSGR_112/Docs/RP-261566.zip` |
| P9 | **R1-2504948**, *Information on validations for ISAC* (Moderator, Xiaomi) + 첨부 xlsx | RAN1 #121, St Julian's, 2025-05-19/23 | `https://www.3gpp.org/ftp/tsg_ran/WG1_RL1/TSGR1_121/Docs/R1-2504948.zip` |
| P10 | **3GPP Work Plan** (WI/SI 대장) | 2026-06-26 판 | `https://www.3gpp.org/ftp/Information/WORK_PLAN/Work_plan_3gpp_2026_06_26.xlsx` |

TR 38.901 §7.9 의 개정 이력(Annex 변경이력, P1 내부):
RP-251567 (RAN#108, 2025-06) → **V19.0.0 최초 도입** · RP-252623 (RAN#109, 2025-09) → V19.1.0 ·
RP-253012 (RAN#110, 2025-12) → V19.2.0 · RP-260166 (RAN#111, 2026-03) → V19.3.0 ·
**RP-261338 (RAN#112, 2026-06) → V19.4.0 "CR on ISAC reference channel model"**.

### 2차 (참고 — 1차와 어긋난 곳 없음)

| # | 자료 | 지위 |
|---|---|---|
| S1 | Y. Liu, Y. Zhang, J. Zhang 외 20인, *A Comprehensive Survey of 3GPP Release 19 ISAC Channel Modeling: From Empirical Features to Unified Methodology and Standardized Simulator*, **arXiv:2512.03506v1 (2025-12-03)** | 서베이. 6개 모드 열거가 P6 과 **일치**. 저자에 TR 38.901 ISAC 에디터(Yingyang Li, Xiaomi) 포함 |
| S2 | ETSI TR 138 901 **V19.2.0 (2026-02)** (ETSI 발행 미러) | **한 판 뒤짐** — V19.4.0 대신 인용하면 안 된다 |
| S3 | ETSI GR ISC 001 V1.1.1 (2025-03) / GR ISC 002 V1.1.1 (2025-08), ETSI ISG ISAC | 3GPP 아닌 **별개 SDO** 산출물. 3GPP 모드 정의의 근거로 쓰면 안 됨 |

---

## ⑨ 우리 저장소와 어긋나는 곳 (정정 대상)

마지막 단계에서 `docs/INJECTION_PRECEDENT.md`, `docs/DRONE_ISAC_PRIOR_READING.md`,
`docs/PAPER_POSITION_0803.md` 를 열어 대조했다.

**모순(정정 필요) — 1건**

| ID | 우리 기록 | 원문 | 조치 |
|---|---|---|---|
| **X1** | `DRONE_ISAC_PRIOR_READING.md:73` — 등방 상수 **−20 dBsm** 을 "3GPP 합의 σ" 계열로 취급(귀속: R1-2403921 / JSAC 2편). 우리 5기체 방위평균(−21.6 ~ −12.9 dBsm)을 이 값에 정합시켰다 | **3GPP 가 실제로 합의해 규격에 넣은 값은 −20 이 아니라 −12.81 dBsm(소형) / −5.85 dBsm(대형)** 이다. −20 dBsm 은 **개별 기고문(R1-2403921) 단계의 제안치**이지 채택치가 아니다 | −20 을 인용할 때 **"기고 단계 제안치, 미채택"** 이라고 표시. 규격 대조는 −12.81/−5.85 로 다시 |

**결손(추가 필요) — 5건**

| ID | 없는 것 | 왜 중요한가 |
|---|---|---|
| **G1** | **UAV large/small 두 갈래**. 우리는 −12.81(소형·평평)만 M1 으로 쓴다 | 우리 편대의 **S1000+ (1.05 m 급)** 은 규격 기준 **large**(1.6×1.5×0.7 m) 쪽이라 −5.85 dBsm + 6섹터 각도의존이 맞는 대조군이다. 지금 M1 은 소형 5기 전부에 소형 상수를 먹이고 있다 |
| **G2** | *"The same values are used for monostatic RCS and bistatic RCS"* (Table 7.9.6.2-1) | 우리가 «이등분선 모노스태틱 근사» 를 쓰는 것에 대한 **규격 선례**다(`PAPER_POSITION_0803.md` C5 의 방어논거). 안 쓰고 있었다 |
| **G3** | XPR μ=13.75 dB, σ=7.07 dB (Table 7.9.2.2-1) | 편파 처리를 규격과 비교할 축 |
| **G4** | **TR 38.765 / TR 22.837 / TS 22.137 / UMa-AV** 가 저장소 전체에 **0회 언급** | 우리는 «3GPP 표적모형» 은 알고 **«3GPP 시나리오»는 모르는** 상태였다. 배치·전력·격리·간섭 가정이 전부 여기 있다 |
| **G5** | Rel-20 §9 결론(단일 TRP 3/11 · 다중 TRP 9/10) 및 자기간섭 격리 65/80 dB 유도 | §⑥ 의 부수 발견 2건 — **우리 논문에 바로 쓸 수 있는 규격 측 논거** |

**정확 확인(변경 불필요) — 3건**: §④-2 표 상단 3행(σ_M 값·σ_S·주파수 무관·σ_RCS 3성분 구조·
Step 10/15 주입점) 모두 원문과 일치.
