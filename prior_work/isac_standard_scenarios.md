# 3GPP ISAC 표준 시나리오 — 원문 확정본

**작성 2026-08-10 · 보충 2026-08-11 · 전량 1차 자료(3GPP 원문 docx) 기반**
기계판: `outputs/isac_standard_scenarios.json` · **`outputs/isac_standard_gaps.json`**(보충분)

> **2026-08-11 보충** — §⑨ 가 결손으로 남긴 **G3(XPR)**·**G4(UMa-AV)** 와 **TR 38.765 §9** 를
> **§⑩·§⑪·§⑫** 에서 닫았다. TR 36.777 V15.0.0 을 새로 확보했다.
> 세 줄 요약:
> · **XPR 은 하나가 아니라 셋**이고(표적 13.75/7.07 + 전파 8/4·7/3), 전력영역 유효값은 **7.99 dB** 다.
>   ±45 이중편파 기지국에서는 **유효 XPR 이 0 dB** 이며 단일편파 수신은 **3.010 dB** 를 잃는다.
> · **UMa-AV 의 실체는 TR 36.777 B.1.3 «스톡 UMa + 라이시안 K = 15 dB»** 다. 표적 앙각 중앙
>   **−38.1°**, 3D 거리 중앙 **242 m**, 그리고 **76.8 %** 가 우리 옛 σ 격자(el ≥ −20°) 밖이었다.
> · **TR 38.765 의 병목은 정확도가 아니라 탐지다** — 정확도는 어디서나 1~4 m(목표 10 m)인데
>   떨어진 건 전부 P_md·P_fa Type 2 다. 그리고 130 건 평가에 **바이스태틱은 0 건**이다.

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
| **G3** | XPR μ=13.75 dB, σ=7.07 dB (Table 7.9.2.2-1) | 편파 처리를 규격과 비교할 축 → **✅ 2026-08-11 §⑩ 에서 닫음**(그리고 XPR 이 셋이라는 것이 드러남) |
| **G4** | **TR 38.765 / TR 22.837 / TS 22.137 / UMa-AV** 가 저장소 전체에 **0회 언급** | 우리는 «3GPP 표적모형» 은 알고 **«3GPP 시나리오»는 모르는** 상태였다. 배치·전력·격리·간섭 가정이 전부 여기 있다 → **✅ 2026-08-11 §⑪·§⑫ 에서 닫음** |
| **G5** | Rel-20 §9 결론(단일 TRP 3/11 · 다중 TRP 9/10) 및 자기간섭 격리 65/80 dB 유도 | §⑥ 의 부수 발견 2건 — **우리 논문에 바로 쓸 수 있는 규격 측 논거** |

**정확 확인(변경 불필요) — 3건**: §④-2 표 상단 3행(σ_M 값·σ_S·주파수 무관·σ_RCS 3성분 구조·
Step 10/15 주입점) 모두 원문과 일치.

---
---

# 결손 3건 보충 (2026-08-11)

**추가 작성 2026-08-11 · 접근일 2026-08-11 · 1차자료 3건을 새로 열어 읽었다**
기계판: `outputs/isac_standard_gaps.json` (생성기 `benchmark/isac_standard_gaps.py`, GPU 미사용)

§⑨ 가 «결손» 으로 남긴 것 중 **G3(XPR)·G4(UMa-AV 시나리오)** 와, `docs/PLAN_0818.md` 4층이
지목한 **TR 38.765 §9** 를 여기서 닫는다. 위 §①~⑨ 에 이미 있는 것은 되풀이하지 않는다.

이번에 새로 연 원문(전부 직접 내려받아 본문 추출):

| 문서 | 판·날짜 | 이번에 읽은 절 | 비고 |
|---|---|---|---|
| **TR 38.901** | V19.4.0 (2026-06) | §7.9.2.1 · **§7.9.2.2** · **§7.9.3** · **§7.9.4.1 Step 10~15** · Table 7.5-6 | 수식은 OMML 을 직접 렌더해 위첨자·근호를 살렸다 |
| **TR 38.765** | V20.0.0 (2026-06) | **§4 · §5 · §6 · §9 · Annex A** 전문 | §9 를 축자로 옮겼다 |
| **TR 36.777** | V15.0.0 (2018-01) | **Annex B · B.1.1 · B.1.3** | Word-97 이진 .doc → 조각표 파서로 본문 추출 |

---

## ⑩ XPR — 규격의 편파 처리와 우리 스칼라 커널

### ⑩-1 ⭐먼저 틀을 바로잡는다 — 규격의 σ 도 스칼라다

우리는 «우리 커널이 무편파 스칼라라서 규격과 다르다» 고 적어 왔다. **틀린 대비다.**

> **TR 38.901 §7.9.2.1 첫 문장 (축자):**
> *"The RCS of a SPST is **a scalar value** defined in LCS of the ST and is dependent on
> both the incident angle and the scattered angle."*

규격도 σ 를 스칼라로 둔다. 편파는 σ 안에 있지 않고 **곱해지는 별도의 2×2 행렬**
(cross-polarization matrix, CPM)에 있다. 즉 규격의 구조는

```
채널 = [수신 안테나 편파벡터]ᵀ · (CPM_rx · CPM_표적 · CPM_tx) · [송신 안테나 편파벡터] · √(전력)
                                  └──────── 편파(무차원) ────────┘   └─ σ 가 여기 ─┘
```

**우리 결손은 «σ 가 무편파라서» 가 아니라 «CPM 이 아예 없어서» 다.** 이 구분이 중요한 이유는,
전자는 σ 격자를 통째로 다시 계산해야 하는 문제로 들리고 후자는 **σ 는 그대로 두고 곱할 항을
붙이는** 문제이기 때문이다. 규격이 이미 그렇게 인수분해해 두었다.

### ⑩-2 CPM 의 정확한 모양 (원문 수식)

> **eq 7.9.2-5 (UAV·사람·차량·AGV 공통, 축자 렌더):**
> `CPM_sp,i = [[ exp(jΦ^θθ), √(κ⁻¹)·exp(jΦ^θφ) ], [ √(κ⁻¹)·exp(jΦ^φθ), exp(jΦ^φφ) ]]`
>
> **§7.9.4.1 Step 13 (축자):** *"The distribution for initial phases is uniform within
> (−π, π)"* — 네 위상 **전부 독립**이다.
>
> **Table 7.9.2.2-1:** UAV **μ_XPR = 13.75 dB · σ_XPR = 7.07 dB** (로그정규)

읽어야 할 세 가지.

1. **동일편파 진폭이 1 로 고정**되어 있다(α=1). κ 는 오직 **교차편파 누설**의 크기다.
2. **네 위상이 독립**이다 — 대각의 Φ^θθ 와 Φ^φφ 사이에 어떤 관계도 없다. 이게 §⑩-4 의
   놀라운 결과를 낳는다.
3. eq 7.9.4-4 는 이 3중곱을 **자기 대각의 RMS 로 나눈다**:
   `÷ √((|d^θθ|² + |d^φφ|²)/2)`, 여기서 d 는 `CPM_rx·CPM_표적·CPM_tx` 의 대각 두 원소다.
   → 편파 사슬은 **레벨을 안 나른다**. 레벨은 전부 σ 가 나른다.
   ⭐ 이 «전력평균으로 정규화» 는 우리 `src/materials.py:276` 의
   `g = √((|Γ_TE|²+|Γ_TM|²)/2)` 와 **구조가 같은 선택**이다. 층이 다를 뿐이다(경로 대 면).

### ⑩-3 ⭐XPR 은 **하나가 아니라 셋**이다 — 우리 기록의 진짜 구멍

§④ 는 Table 7.9.2.2-1 의 13.75/7.07 만 적었다. 그런데 eq 7.9.4-4 의 곱에는 CPM 이 **셋** 들어가고
셋이 서로 다른 XPR 표를 쓴다.

| 자리 | 식 | XPR 출처 | UAV·UMa 값 |
|---|---|---|---|
| `CPM_tx` (STX→산란점 링크의 레이) | eq **7.9.4-7** | **Table 7.5-6 Part-1, UMa 열** | LOS μ 8 · σ 4 dB / NLOS μ 7 · σ 3 dB |
| `CPM_표적` (산란점 자체) | eq **7.9.4-6** | Table 7.9.2.2-1 | **μ 13.75 · σ 7.07 dB** |
| `CPM_rx` (산란점→SRX 링크의 레이) | eq **7.9.4-8** | Table 7.5-6 Part-1, UMa 열 | LOS μ 8 · σ 4 dB / NLOS μ 7 · σ 3 dB |

LOS 레이일 때만 링크 CPM 이 `[[1,0],[0,−1]]` 로 고정된다(§7.9.4.1 Step 14 축자).
**즉 «3GPP 의 UAV XPR = 13.75 dB» 라고 쓰면 틀린다.** 그건 표적 항 하나이고, 전파 항 둘이 앞뒤로
더 곱해진다. 우리 문서가 13.75 만 적어 온 것은 **결손이 아니라 부분인용**이었다.

### ⑩-4 얼마나 큰가 — 정량 ⟨`outputs/isac_standard_gaps.json` : `xpr`⟩

4×10⁶ 몬테카를로. 기준 0 dB = 정렬된 동일편파(V→V)에서 우리 스칼라 커널의 수신전력.
해석식과 소수 셋째 자리까지 일치한다.

**(가) μ 를 그대로 링크버짓에 쓰면 안 된다**

| | 값 |
|---|---|
| Table 7.9.2.2-1 의 μ_XPR | 13.75 dB |
| **전력영역 유효 XPR** = −10log₁₀ E[1/κ] | **7.99 dB** |
| 차이 | **5.76 dB** |
| P(XPR < 0 dB) — 완전 탈편파보다 나쁜 경로 | **2.59 %** |
| P(XPR < 3 dB) | 6.40 % |
| P(XPR > 20 dB) | 18.83 % |

σ_XPR = 7.07 dB 의 로그정규 꼬리가 E[1/κ] 를 지배한다. **13.75 dB 는 «평균 XPR» 이지
«전력이 실제로 나뉘는 비» 가 아니다.** 후자가 7.99 dB 다.

**(나) ⭐⭐±45° 이중편파 기지국에서는 유효 XPR 이 0 dB 다**

TR 38.765 Table 6.2-1 의 기지국 안테나는 축자로 *"dH,dV = (0.5, 0.8)λ, **+45°/−45° polarization**"*
이다. 그 기저에서 위 CPM 을 통과시키면

| 포트 | 3GPP CPM (κ~로그정규) | 3GPP CPM (κ=μ 고정) | 우리 스칼라 커널 |
|---|---|---|---|
| V → V (정렬 동일편파) | 0.000 dB | 0.000 dB | 0.000 dB |
| V → H (교차편파) | **−7.99 dB** | −13.75 dB | **−∞** |
| +45 → +45 (동일 슬랜트) | −2.37 dB | −2.83 dB | **0.00 dB** |
| +45 → −45 (교차 슬랜트) | **−2.37 dB** | −2.83 dB | **−∞** |

**두 슬랜트 포트가 같은 전력을 받는다 — κ 가 얼마든 상관없이.** 유효 XPR 0.0005 dB.
이유는 κ 가 아니라 **대각의 두 위상이 독립**이라는 데 있다. Φ^θθ 와 Φ^φφ 가 무관하면
±45 기저에서 합·차가 통계적으로 같아진다. 규격의 표적은 슬랜트 기저를 **완전히 흐트러뜨린다.**

**(다) 그래서 단일편파 수신은 3.010 dB 를 잃는다**

| | 두 포트 합 | 한 포트만 | 손실 |
|---|---|---|---|
| 3GPP CPM | +0.64 dB | −2.37 dB | **−3.010 dB** |
| 우리 스칼라 커널 | 0.00 dB | 0.00 dB | **0.000 dB** |

우리 커널은 «동일편파 포트 하나로 전부 받는다» 고 말하고, 규격은 «절반은 직교 포트에 있다» 고
말한다. **총 전력은 0.64 dB 밖에 안 다른데 그 전력이 어느 포트에 있느냐가 완전히 다르다.**

### ⑩-5 우리 커널의 결손이 정확히 어디인가

`src/materials.py:259-279` 는 면마다 **프레넬 두 편파를 실제로 계산해 놓고** 276 행에서
전력평균해 버린다(`g = √((|Γ_TE|²+|Γ_TM|²)/2)`). 3.5 GHz 에서 버려지는 대비
⟨`isac_standard_gaps.json` : `our_kernel_polarisation`⟩:

| 재질 | 30° | 60° | 75° | 최대 \|대비\| | 그 각도 | 전력평균이 TE 대비 | TM 대비 |
|---|---|---|---|---|---|---|---|
| plastic / plastic_blue / prop_plastic | +3.24 | +28.45 | +6.72 | **+37.63 dB** | 58.8° | +3.01 dB | **−34.62 dB** |
| carbon | +0.03 | +0.15 | +0.36 | +7.62 dB | 89.5° | +2.32 dB | −5.30 dB |
| absorber | +1.54 | +6.84 | +7.29 | +8.19 dB | 69.2° | +2.40 dB | −5.79 dB |

(metal·pcb·camera_assembly 는 `itu="metal"` PEC 근사라 대비 0 dB.)

⚠ **이 수를 표적 σ 의 오차로 읽으면 안 된다.** 브루스터 널은 각도폭이 좁고, 표적은 수많은 면의
합이라 대부분 평균된다. **표적 전체에 얼마가 남는지는 편파 커널이 없어서 측정하지 못했다 —
모른다.** 위 표는 **면 단위 상한**이다.

⛔ 그리고 이 대비는 **3GPP κ 와 나란히 못 놓는다.** 위는 동일편파 두 성분의 비(S_θθ 대 S_φφ)이고
3GPP κ 는 교차편파 누설(|S_θφ|²/|S_θθ|²)이다. 우리 커널에는 **S_θφ 를 만드는 경로가 없다** —
면마다의 국소 TE/TM 이 전역 (θ,φ) 기저로 회전·합성되지 않기 때문이다.
**우리 XPR 은 «높다» 가 아니라 «정의되지 않는다».** 논문에 수를 적을 자리가 아니다.

### ⑩-6 판정 — 지금 말할 수 있는 것과 없는 것

**말할 수 있는 것**
- 우리 σ 는 **동일편파 σ** 다. 규격의 σ 도 스칼라이므로 이 자리에서는 어긋나지 않는다.
- 3GPP 와 정합하는 이중편파 기지국을 상대로 우리 링크버짓을 비교하면 **단일편파 수신은
  −3.010 dB** 를 물어야 한다. 우리 사다리(③′ `snr_slow_ac_db`)에는 **편파 항이 아예 없다.**
  → 이건 «시나리오 행» 으로 넣을 수 있다. 커널을 안 고쳐도 된다.
- 3GPP 표적 XPR 을 인용할 때는 **7.99 dB**(전력영역)를 쓰고 13.75 는 μ 라고 밝힌다.

**말할 수 없는 것 (모른다)**
- 우리 표적의 실제 XPR — 커널에 그 자유도가 없다. **추정치도 내지 않는다.**
- 편파가 우리 σ 절대레벨에 얼마를 더하는지 — `docs/ENGINE_VALIDATION.md:107` 이 이미
  *"우리 값이 VV 측정보다 낮게 나온 것을 편파로는 설명하지 못한다"* 고 방향만 못 박아 두었다.
  이번 라운드가 그 문장을 바꾸지 않는다.
- 편파 특징이 분류(드론 대 새)에 얼마나 기여하는지 — 우리 분류는 마이크로도플러 단독이다.

**닫으려면 무엇이 필요한가** (⛔이번 라운드에서 하지 않았다)
- 값싼 쪽: 커널은 그대로 두고 **«우리 σ = 동일편파 σ» 선언 + 단일편파 −3.01 dB 시나리오 행**.
- 진짜 쪽: `src/rcs_sbr.py` 의 누산기가 지금 **복소 스칼라 `E`** 다(`rcs_sbr.py:335, 515`).
  이걸 2×2 로 올리고, 면마다 국소 TE/TM 기저를 전역 (θ,φ) 로 회전시켜 코히어런트 누산해야 한다.
  프레넬 두 갈래는 **이미 있다**(`materials.py:259-268`) — 없는 것은 **기저 회전과 2×2 누산**이다.
  σ 격자 전면 재계산이 따라온다(`docs/PAPER_DRAFT.md:569` 가 ≈23 h GPU × 2편파로 견적).

---

## ⑪ UMa-AV — 시나리오의 실체와 우리 기하와의 차이

### ⑪-1 ⭐UMa-AV 는 TR 38.901 에 없다 — TR 36.777 로 나간다

§⑤ 는 UMa-AV 를 «시나리오 이름» 으로만 적었다. 실체는 **Rel-15 항공 UE 연구(TR 36.777)** 에 있고
ISAC 은 그것을 **참조로 끌어다 쓴다.**

> **TR 38.901 Table 7.9.3-1 Case 4 (TRP ↔ aerial UE, 축자):**
> *"TRP-aerial UE link of scenario UMa-AV, UMi-AV, and RMa-AV in Clause **Annex A and B of
> TR 36.777** for FR1 / Reuse the channel model of scenario UMa-AV, UMi-AV, and RMa-AV of FR1
> for FR2"*
>
> **TR 38.901 Table 7.9.3-2:** STX/SRX = TRP, Target = UAV → **Case 4**.
>
> **TR 38.765 Annex A Table A-1 (축자):** *"gNB-target link | TRP-UAV link in Table 7.9.3-2 in
> TR 38.901, using **Clause B.1.3 in TR 36.777**"*

즉 사슬은 **TR 38.765 → TR 38.901 §7.9.3 Case 4 → TR 36.777 Annex B.1.3** 이다.

### ⑪-2 ⭐⭐B.1.3 의 전문 — 한 줄이다

> **TR 36.777 §B.1.3 Alternative 3 (축자, 전문):**
> *"In this alternative, for RMa-AV aerial UEs, UMa-AV aerial UEs, and UMi-AV aerial UEs, the
> fast fading model in Section 7.5 of [4] is used with **K=15 dB**. In this alternative, all the
> remaining parameters are reused from [4], including the delay and angular spreads, the
> cross-correlations among the LSPs, the delay scaling factor, **the XPR**, the number of
> clusters, the cluster delay and angular spreads, the per-cluster shadowing, and the LSP
> autocorrelation distances."*

**Rel-20 이 UAV 링크에 쓰는 채널모델의 전부가 «스톡 UMa 에 라이시안 K 를 15 dB 로 못 박은 것»
이다.** 그리고 *"the XPR"* 이 재사용 목록에 명시돼 있다 → §⑩-3 의 전파 XPR(UMa LOS 8/4 ·
NLOS 7/3 dB)이 여기서 확정된다.

참고로 다른 두 대안(Rel-20 은 안 쓴다)도 같은 방향을 가리킨다.

| 대안 | UMa-AV LOS | UMa-AV NLOS |
|---|---|---|
| **B.1.1 (Alt 1, CDL-D 기반)** | ASA/ASD **0.5°**, ZSA/ZSD **0.1°**, K **20 dB**, DS **10 ns** | ASA/ASD 1°, ZSA/ZSD 0.3°, K 10 dB, DS 30 ns |
| **B.1.2 (Alt 2)** | **못 읽었다** — 값이 OLE Equation 개체(그림)로 박혀 있다 | 〃 |
| **B.1.3 (Alt 3)** ← Rel-20 채택 | 스톡 UMa + **K = 15 dB** | 스톡 UMa + K = 15 dB |

⭐ **읽어야 할 것**: 어느 대안을 골라도 공중링크는 **거의 단일 광선**이다. K 15~20 dB,
각도확산 0.1~1°, 지연확산 10~30 ns. 규격은 «도심 매크로» 라는 이름을 달고 있지만 표적으로 가는
다리는 사실상 자유공간에 가깝다.

**우리에게 유리한 정량 하나.** K = 15 dB 면 정반사 성분이 K/(K+1) = **96.94 %** 다.
우리는 표적 링크를 자유공간(K = ∞)으로 놓는다. 그 차이는 코히어런트 성분을 **+0.135 dB**
과대평가하는 것뿐이다. ⚠ 단, 나머지 **3.06 %** 는 사라지는 게 아니라 **이웃 지연·도플러 칸으로
퍼지는 성분**이다 — 그건 신호 항이 아니라 클러터 항이고, 우리 자유공간 팔에는 그 항이 없다.
0.135 dB 는 «작다» 가 맞고, 빠진 3.06 % 는 «다른 종류» 다. 둘을 섞어 읽으면 안 된다.

### ⑪-3 표적 드롭 기하 — 계산해서 우리 축에 겹쳤다

TR 38.765 Annex A Table A-1 의 baseline 그대로 몬테카를로(N ≈ 6.7×10⁵)
⟨`outputs/isac_standard_gaps.json` : `umaav_geometry`⟩:
ISD 500 m 육각셀의 한 섹터에 균등, 고도 균등 25~300 m, gNB 25 m, 최소 3D 거리 10 m.

| 양 | p5 | 중앙 | p95 | 최대 |
|---|---|---|---|---|
| 2D 거리 | 59.0 m | **185.6 m** | 258.8 m | 288.6 m |
| 고도 | 38.8 m | 162.7 m | 286.3 m | 300 m |
| **3D 거리** | 112.7 m | **242.3 m** | 338.1 m | **397.0 m** |
| **앙각**(우리 규약, belly = 음수) | −69.7° | **−38.1°** | −4.5° | −89.9° |

⭐ **결과 1 — 규격의 UAV 는 «위» 에 있다.** gNB 안테나가 25 m 이고 표적 고도 하한이 **똑같이
25 m** 라, baseline 에서는 **표적이 안테나보다 낮은 경우가 없다** → 규격 시나리오는 **전부
배면(belly) 조망**이다. 우리 σ 격자의 음수 el 규약이 바로 그 기하다.
⚠ 단 Table A-1 은 *"optionally between **1.5 m** and 300 m"* 라는 옵션도 둔다. 그 옵션에서는
표적이 안테나 아래로 내려가 **정면·상면 조망**이 생기고, **우리 σ 격자에는 양수 el 행이 없다**
(`el_note` 축자: *"NEGATIVE el only (belly view)"*). 옵션 쪽은 **우리가 못 덮는다.**

⭐ **결과 2 — 우리 el 확장 라운드가 «있으면 좋은 것» 이 아니었다.**

| 구간 | UMa-AV 표적 비중 |
|---|---|
| el ∈ (0, −20]° — 2026-08-03 기본 행 | **23.2 %** |
| el < −20° — el 확장 라운드 행(−24 … −90°) | **76.8 %** |
| el < −57° — 전 기체·전 밴드가 클램프행보다 밝은 구간 | 15.5 % |

**규격 시나리오의 4분의 3 이 옛 9행 격자 밖이었다.** 옛 −20° 클램프의 오차를 UMa-AV 앙각 분포로
가중하면 ⟨`outputs/sigma_el_extend_verify.json` : `clamp_direction`⟩

| | 값 |
|---|---|
| UMa-AV 분포 가중 평균 편향 | **−0.03 dB** |
| 조회 하나하나의 rms | **6.23 dB** |
| 방위평균 레벨만(계통 성분) rms | 2.23 dB |
| 최대 \|오차\| | 32.79 dB |

⭐ 읽는 법: **옛 클램프는 «레벨 편향» 이 아니라 «산포» 였다.** 얕은 각의 음의 편향과 급한 각의
양의 편향(−71°에서 +4.07 dB, −90°에서 +7.97 dB)이 평균에서 상쇄된다. 그래서
«평균은 맞는데 표적 하나하나는 rms 6.2 dB 틀린» 상태였다. 검출은 평균이 아니라 개체로 하므로
이건 실질적인 결함이었고, el 확장이 그걸 닫았다.

⭐ **결과 3 — 거리축은 우리가 규격에 한참 못 미친다.**

| 기체 | R90 (EIRP 12 dBm, chamber) | UMa-AV 표적 중 그 안에 드는 비율 | R90 (EIRP 63 dBm 로 환산) | 비율 |
|---|---|---|---|---|
| mavic4pro | 72.5 m | **1.32 %** | 1366 m | 100 % |
| s1000plus | 51.2 m | 0.46 % | 964 m | 100 % |
| matrice4e | 22.1 m | 0.03 % | 416 m | 100 % |
| mini5pro | 15.7 m | 0.01 % | 297 m | 81.5 % |
| phantom4 | 15.4 m | 0.01 % | 290 m | 78.5 % |

⟨R90 = `outputs/md_snr_vs_range.json` : `observability_measured`⟩. 환산은 단일정적 1/R⁴ 에서
R ∝ EIRP^(1/4) → 배율 18.84×.
⚠ **63 dBm 과 규격의 52/37 dBm 은 직접 비교 금지.** 규격 값은 **도통 전력**이고 배열 이득은
ITU-R M.2412 Table 9 패턴에 맡겨져 있다. 우리 63 dBm 은 EIRP 선언값이다. 두 수의 차를 «이득» 이라
읽으면 안 된다. 여기서 말할 수 있는 것은 **«챔버급 12 dBm 으로는 규격 시나리오의 1 % 도 못 본다,
매크로급 조명이면 대부분 본다»** 는 자릿수 판정뿐이다.

### ⑪-4 ⭐우리 설정과 UMa-AV 의 차이표

| 항목 | 3GPP UMa-AV (TR 38.765 baseline) | 우리 | 판정 |
|---|---|---|---|
| **모드** | gNB 모노스태틱 | 패시브 바이스태틱 | **다르다** — §⑥ 판정 그대로 |
| 반송파 | **4 또는 4.9 GHz** (옵션 6) | 1.8 / **3.5** / 5.2 GHz | 다르다. 규격 σ 는 주파수 무관이라 규격 쪽은 영향 없고, **우리 σ 는 주파수 의존**이라 우리 쪽만 값이 달라진다 |
| 대역폭 | FR1 **100 MHz** | 5G NR **100 MHz** (LTE 20 · WiFi 80) | **5G 팔은 일치** |
| Numerology | **SCS 30 kHz** | 5G NR **30 kHz** ⟨`src/waveforms.py:46`⟩ | **일치** |
| 거리분해능 ΔR = c/2B | (목표는 정확도 10 m) | **1.50 m** (100 MHz) · 7.50 m (LTE) · 1.88 m (WiFi) | 우리가 목표보다 촘촘하다 |
| 배치 | 육각 7 사이트 × 3 섹터, **ISD 500 m** | 단일 Tx–Rx 쌍, 베이스라인 **L = 0 / 10 / 500 m** ⟨`outputs/mono_link.json` : `placements`⟩ | **다르다** — 우리는 셀룰러 배치를 안 쓴다. L=500 m 만 규격 ISD 와 우연히 같다 |
| Tx 높이 | **25 m** (UMa-AV) | 야외 사이트 미확정 · 챔버 천장 11 m | **모른다** — 야외 실증 기하가 아직 안 정해졌다 |
| 표적 고도 | 균등 **25~300 m** | φ 스윕에서 **60 m · 120 m** ⟨`outputs/sigma_el_extend_verify.json` : `pools`⟩ | 규격 범위 **안**에 든다(두 점만 쓴다) |
| 표적 앙각 | 중앙 **−38.1°**, 76.8 % 가 −20° 아래 | σ 격자 el 23행 **0 … −90°** | **덮는다**. 다만 4분의 3 이 확장 행에 의존한다 |
| 최소 Tx–표적 3D | **10 m** | 거리 격자가 **1 m** 부터 ⟨`md_snr_vs_range.json` : `R_m`⟩ | ⚠ 우리 R = 1 · 2 · 5 m 행은 **규격이 안 보는 구간**이다. 규격과 나란히 놓을 때 빼야 한다 |
| 표적 수 | 섹터당 **N = 5** (옵션 1~10, N=0 은 오경보용) | 단일 표적 | **다르다**. 오경보 Type 2(표적 있는데 다른 것을 잡음)를 우리는 잴 수 없다 |
| 표적 크기 | 소형 **0.3×0.4×0.2 m** 단일 | 5기체, mini5pro~s1000plus(1.05 m급) | s1000plus 는 규격 기준 **대형**(§⑨ G1) |
| σ 모형 | −12.81 dBsm **상수**, 자세·주파수 무관, 단일 산란점 | az 120 × el 23 × 3밴드 격자, 다면 PO/SBR | 우리가 훨씬 촘촘하다. ⚠ 단 우리 σ 는 `NOT_VALIDATED` ⟨`outputs/das_fleet_validation.json`⟩ |
| **편파** | 표적 CPM(XPR 13.75/7.07) × 전파 CPM(8/4·7/3) · BS **±45° 이중편파** | 무편파 스칼라, CPM 없음 | **결손** — §⑩. 단일편파 수신이면 3.01 dB |
| 링크(공중) | 스톡 UMa 소규모페이딩 + **K = 15 dB** | 자유공간 (K = ∞) | 코히어런트 성분 **+0.135 dB** 과대. 확산 3.06 % 는 **우리 모형에 없다** |
| 이동성 | 수평 **0~180 km/h** 균등, **수직 0** | 호버 + 로터 회전 | **직교한다** — §⑪-5 |
| CPI | 보고된 값 **≤ 160 ms** ⟨TR 38.765 §6.3⟩ | **250 ms** (L=5000 @ PRF 20 kHz) | 같은 자릿수. 우리가 조금 길다 |
| 자기간섭 | **−94+X dBm in 100 MHz**, X 는 회사 보고 | 항 없음(패시브) | 우리 구조의 이점 — §⑥ 부수발견 2 |
| 간섭(사이트간·섹터간·인접채널) | **전부 미모델링** | 미모델링 | **일치**(둘 다 안 한다) |

### ⑪-5 ⭐⭐규격에는 로터가 없다 — 기계 검색 결과

전문 검색(대소문자 무시):

| 낱말 | TR 38.901 | TR 38.765 |
|---|---|---|
| `rotor` | **0** | **0** |
| `blade` | **0** | **0** |
| `propeller` | **0** | **0** |
| `micro-Doppler` / `micro Doppler` | **0** | **0** |
| `micro motion` | **1** | **0** |

그 유일한 1회가 이것이다.

> **TR 38.901 eq 7.9.4-5 아래 정의 (축자):**
> *"v_k,p(t) is the velocity of SPST p of ST k, **v_k,p(t) = v_ma,k(t) + v_mi,k,p(t)**, where
> v_ma,k(t) is the velocity of the ST k, **v_mi,k,p(t) is velocity due to micro motion of SPST p
> of ST k**."*

**규격은 마이크로도플러의 «자리» 만 만들어 놓고 값을 한 번도 채우지 않는다.**
분포도, 표도, 기본값도 없다. 그리고 소형 UAV 는 RCS model 1 — **단일 산란점 · σ_D ≡ 1**
(Table 7.9.2.1-1 제목 축자: *"Parameters on RCS for the STs with **angular independent**
monostatic RCS values"*)이므로 v_mi 를 넣을 산란점 자체가 하나뿐이다.

⭐ **정리하면 3GPP 의 소형 UAV 표적은 «회전하지 않는 등방 점» 이다.** 이것이 우리 과제가
서 있는 빈칸이고, §⑥ 의 포지셔닝 문장에 **한 줄 더 붙일 수 있는 근거**다 —
지금까지 우리는 «모드가 규격 밖» 이라고만 논증했는데, **표적 모형에도 우리가 쓰는 축이 통째로
비어 있다**는 것이 이번에 확인됐다.
⚠ 정직하게: 이건 «3GPP 가 틀렸다» 가 아니다. Rel-19/20 의 목표는 **검출·측위**이지 분류가
아니고, 그 목표에는 등방 점이면 충분하다. 우리 주장은 «규격이 부족하다» 가 아니라
**«우리가 쓰는 축이 규격에 정의돼 있지 않아 규격 위에서 비교할 대상이 없다»** 여야 한다.

### ⑪-6 못 읽은 것 (⛔추측으로 안 메웠다)

| 대상 | 상태 | 영향 |
|---|---|---|
| TR 36.777 **Table B-1 (LOS 확률 식)** · **B-2 (경로손실 식)** · **B-3 (섀도잉 표준편차)** 의 수식·적용범위 | **못 읽었다** — Word-97 .doc 안에 **OLE Equation 3.0 개체(그림)** 로 박혀 있어 본문 추출로 안 나온다 | 중. UMa-AV 의 LOS 확률과 경로손실을 **우리가 직접 못 옮긴다**. 읽어 낸 것은 표의 **말** 부분뿐이다 |
| ETSI 발행 TR 136 777 PDF | **없다** — `etsi.org/deliver/.../136777/15.00.00_60/` 404 | 위 항목의 우회로가 막혔다 |
| B-2 Note 1 의 «breakpoint 없음» 적용범위 | 문장은 읽었다: *"For UMa-AV LOS, breakpoint distance is not observed for the aerial UE height range […] and 2D distance range […]"* — **대괄호 안이 그림**이다 | 소. «항공 UE 구간에서 UMa-AV LOS 는 단일기울기» 라는 **방향**은 확정, **범위는 모른다** |
| Rel-20 평가 원자료 **R1-2601668**(결과) · **R1-2601669**(가정) · **R1-2601610**(엑셀) | **미확보** | 중. §⑫-3 의 «어느 소스가 왜 실패했나» 를 항목별로 못 본다 |

---

## ⑫ TR 38.765 — §9 결론과, 그 앞이 우리에게 요구하는 것

§③-3 에 §9 요지가 이미 있다. 여기서는 **축자 전문**과, 우리가 안 읽고 있던 §4·§5·§6 을 더한다.

### ⑫-1 §9 전문 (축자)

> *"The performance for UAV sensing use case with gNB monostatic sensing is evaluated based on
> the evaluation assumptions in Annex A (including UMa-AV, Sensing Tx/Rx operating
> simultaneously, FR1) … Among all the reported evaluation results as captured in Annex B,*
> - *Baseline 1 (high BS TX power 52dBm with 80dB antenna isolation)*
>   - *By utilizing measurements from multiple or all TRPs, results from **9/10 sources** achieve
>     the performance objectives.*
>   - *By utilizing measurements from single TRP, results from **3/11 sources** achieve the
>     performance objectives.*
> - *Baseline 2 (low BS TX power 37dBm with 65dB antenna isolation)*
>   - *multiple or all TRPs: **7/9 sources**. single TRP: **2/9 sources**.*
>
> *Due to its higher transport capacity requirement, **Measurement level A is not supported**.
> … **Level C is agreed for specification** in a potential future normative phase. Whether it is
> possible to also support **Level D depends on the resolution of potential privacy and security
> issues** by the appropriate WG(s).*
> *Coordination with **SA3** is expected in order to resolve potential privacy and security
> issues, if any.*
> ***RAN3 aspects of sub-options for all measurement levels have not been discussed.***
> *Three different protocol stacks for sensing data transmission have been evaluated.
> **Option 1 (SCTP-based)** should be adopted in a potential future normative phase.*
> *For control plane signaling, a **dedicated application protocol between gNB and SenF (NsAP)**
> should be adopted …"*

§③-3 에 없던 것 넷: **SA3 조율(프라이버시·보안)** · **RAN3 미논의 자인** · **SCTP** · **NsAP**.
그리고 Annex B 가 원자료를 **R1-2601668 / R1-2601669** 로 넘긴다(§⑪-6 미확보).

### ⑫-2 §4 — 성능지표의 **정의**가 우리 지표와 다르다

우리 기록에는 목표값(5 % / 10 m / 5 m/s)만 있었다. 정의가 더 중요하다.

- **오검출 P_md** = `Σ_n (D_n / M_n) / N`, D_n = 검출객체와 **연결되지 않은** 참표적 수.
- **오경보 Type 1** = 표적이 **없는** 드롭에서 무언가를 잡을 확률. 드롭 단위 0/1.
- **오경보 Type 2** = 표적이 **있는** 드롭에서 참표적과 **연결되지 않은** 검출객체의 비율.
  *"NOTE: Both False alarm probability types are mandatory."*
- **연결(association) 규칙** (축자): *"One true target is associated with at most one detected
  object. One detected object is associated with at most one true target."* 그리고
  *"Companies should report the method used for association."*

⭐⭐ **그리고 이 한 줄이 우리에게 직격이다.**

> **§4.1 (축자):** *"**Sensing resolution, sensing service latency and refreshing rate are not
> considered as performance metrics** for the evaluation of NR ISAC."*

우리 리포트 11권은 **분해능**을 성능처럼 다룬다(제목이 «저속·분해능·관측»이다).
규격은 분해능을 **성능지표에서 뺐다** — 분해능은 수단이고 성능은 P_md·P_fa·정확도라는 뜻이다.
⚠ 이건 «우리가 틀렸다» 가 아니다. 우리 분해능 절이 **성능 주장이 아니라 관측가능성 진단**이라는
것을 문장으로 못 박으라는 요구다. 규격과 나란히 놓을 표에는 **P_md·P_fa1·P_fa2·정확도**만 올라간다.

⚠ 우리에게 **P_fa Type 2 가 아예 없다** — 표적이 하나뿐인 시뮬에서는 정의되지 않는다(§⑪-4).
규격은 두 Type 을 **둘 다 필수**로 못 박았다. 다표적 드롭 없이는 규격 형식으로 보고할 수 없다.

### ⑫-3 §6 결과 — ⭐병목은 정확도가 아니라 **탐지**다

§9 는 «몇 소스가 통과했나» 만 말한다. §6.3 은 **무엇 때문에 떨어졌나**를 말한다.
총 **130 건**(baseline 1 = 46 · baseline 2 = 29 · 기타 = 55)이 보고됐다.

**Case 1-4 (단일 TRP · 자원비 ≤10 % · 광폭빔), 20 건 / 6 소스** — 통과는 3 건 / 1 소스뿐이고
그것도 자기간섭을 **끈**(X = −Inf) 조건이다. 떨어진 17 건의 실패 항목:

| 실패 항목 | 보고된 범위 |
|---|---|
| 오검출 P_md (목표 5 %) | **9.21 ~ 23.05 %** (일부 5.17~12.40 %) |
| 오경보 Type 2 (목표 5 %) | **6.03 ~ 36.41 %** (일부 5.70~8.10 %) |
| 수평 정확도 (목표 10 m) | 통과 사례 **2.45 ~ 3.73 m** |
| 수직 정확도 (목표 10 m) | 통과 사례 **1.28 ~ 1.95 m** |

⭐ **정확도는 어디서도 문제가 아니다** — 통과·실패를 가리지 않고 1~4 m 로 목표 10 m 를 크게
밑돈다. 떨어뜨린 것은 **전부 P_md 와 P_fa Type 2** 다.
**«gNB 모노스태틱 UAV 센싱의 구속조건은 측위가 아니라 탐지»** 라고 규격 문서가 자기 숫자로
말하고 있다. 우리 프로젝트가 [[sionna2-main-task-detection]] 으로 탐지·분류에 집중한 판단이
**규격 측 근거를 얻었다.**

⭐ **클러터를 켜면 무너진다** (§6.3.1, 소스 [19] 1건, 축자):
*"The result is generated with **clutter mobility and low power clusters enabled**."*
→ 수평 정확도 11.1 m · **P_md 20.00 % · P_fa Type 1 91.00 % · P_fa Type 2 79.00 %**.
우리 report09(바닥 유령)의 서사 — **정적 클러터가 아니라 «움직이는 클러터 + 약한 클러스터»가
오경보를 만든다** — 와 같은 방향이고, 이쪽은 규격 문서의 수치다.

⭐ **속도축이 모노스태틱에서 갈린다.** 다중 TRP 팔은 **3D 속도** 정확도를 보고하고(0.35~0.58 m/s),
단일 TRP 팔은 **반경방향(radial) 속도**만 보고한다(3.08~4.63 m/s). 그리고 한 소스는 3D 속도
**52.19~56.28 m/s** 로 목표 5 m/s 를 크게 못 맞춰 그 항목만 떨어졌다(Case 1-1).
§4.1 축자가 그 이유를 적어 둔다: *"For single TRP monostatic sensing, both the radial velocity
accuracy and the 3D velocity accuracy can be estimated. The true radial velocity is the
projection of true 3D velocity on the direction from TRP to target."*
→ **단일 노드는 시선방향 성분밖에 못 잰다.** `outputs/mono_link.json` 의 «모노의 이점은
링크버짓이 아니라 속도축» 판정과 **맞물린다**(그쪽은 PRF 통제권, 이쪽은 3D 복원 불가).

⭐ **바이스태틱 평가는 0 건이다.** 130 건 전부 gNB 모노스태틱이고, 문서 전체에서 `bistatic` 은
**단 1회** 나온다 — 아키텍처 적용가능성 문장(*"Applicability to gNB bistatic sensing may be
considered … without additional architecture impacts"*)뿐이다.
**Rel-20 성능평가에 바이스태틱 수치는 존재하지 않는다.** 우리가 «규격 결과와 비교» 할 때
비교 상대가 모노스태틱밖에 없다는 뜻이고, 동시에 **그 자리가 비어 있다**는 뜻이다.

### ⑫-4 §6.2 · Annex A — 규격이 **회사 재량으로 남긴** 것

이게 우리에게 가장 실용적이다. 규격은 다음을 **고정하지 않고 «회사가 보고하라»** 고 한다
(Annex A 축자 목록에서):

- **CPI 길이** · **Tx 빔 구성**(개수·광폭/협폭) · **센싱 RS 의 RE 매핑**과 TDD 설정 ·
  **센싱 자원비** · **상위 신호처리 방법**(*"e.g., 2D FFT, MUSIC, and any other methods"*) ·
  자기간섭 모델의 **X** 값 · 표적을 단일/다중/전체 STX-SRX 채널 중 어디에 모델링하는지 ·
  다중 리포트를 어떻게 융합하는지 · 연결(association) 방법.

⭐ 두 방향으로 읽힌다.
1. **우리 선택이 규격 위반이 아니다.** ECA→CAF→CFAR, CPI 250 ms, 다중 Rx 융합 — 전부
   규격이 «회사 재량» 이라고 적어 둔 칸이다. 방법을 정당화할 필요는 없고 **보고**하면 된다.
2. **대신 반드시 보고해야 한다.** 지금 우리 리포트가 저 목록 중 **명시적으로 적지 않는 것**이
   있다면 규격 형식의 비교표에 못 올린다.

그리고 **센싱 자원비**는 정의까지 주어져 있다(§6.2 축자): Type_1(센싱 송신에 쓴 자원) ·
Type_2(그중 통신에도 쓰인 부분) · Type_3(센싱 때문에 통신에 못 쓰는 자원),
Option 1 = (T1+T3)/전체, Option 2 = (T1−T2+T3)/전체, **둘 다 보고**.
⭐ 우리 report05 의 «점유 대가 18 dB» 축과 **같은 것을 재는 다른 자» 다. 규격 정의로 환산해
두면 우리 점유 논의를 규격 독자에게 그대로 넘길 수 있다. ⛔ 지금은 환산 안 했다.

### ⑫-5 §5 — 측정 레벨이 곧 «무엇을 내보낼 수 있나»

Level A(원시 CIR/주파수 샘플) · B(지연·도플러·각 프로파일) · C(검출 경로/점) · D(객체).
결론은 **A 미지원 · C 규격화 · D 조건부**(§⑫-1).

⭐ 우리에게 무엇을 뜻하나: **패시브 수신기는 이 사다리 밖에 있다.** 우리는 자기 안테나에서
Level A 를 직접 잡는다 — 망이 A 를 «전송 부담이 커서 지원하지 않는다» 고 결론 낸 바로 그
데이터다. 즉 **«망이 못 내주기로 한 것을 우리는 갖고 있다»** 가 성립하고, 이건
§⑥ 의 포지셔닝에 붙일 수 있는 새 논거다.
⚠ 단 대가도 규격 문장으로 있다 — Level A 를 안 쓰기로 한 이유가 **전송 용량**이므로,
우리 구조의 대가는 «수신단에서 다 처리해야 한다» 는 것이다(중앙 융합이 공짜가 아니다).

---

## ⑬ 이번 라운드가 §⑨ 표에 미치는 변경

| ID | 이전 상태 | 지금 |
|---|---|---|
| **G3** (XPR) | 결손 | **닫힘 → §⑩.** 다만 «XPR 이 셋» 이라는 것이 새로 드러났고, 우리 쪽 값은 **정의되지 않는다**로 확정 |
| **G4** (TR 38.765 / UMa-AV 시나리오) | 결손 | **닫힘 → §⑪·§⑫.** UMa-AV 의 실체는 TR 36.777 B.1.3 «스톡 UMa + K=15 dB» 였다 |
| **G1** (UAV large/small 두 갈래) | 결손 | **그대로 열려 있다** — s1000plus 대조군 아직 안 만듦 |
| **G2** (모노=바이 동일값 선례) | 결손 | `docs/PAPER_POSITION_0803.md` C5 에 반영됨(2026-08-10) |
| **G5** (Rel-20 §9 결론·격리 유도) | 결손 | `docs/PAPER_POSITION_0803.md` P1·P2 에 반영됨. **§⑫-3 이 «왜 떨어졌나»를 추가** |

**새로 생긴 할 일** (⛔이번 라운드에서 안 했다)

1. 사다리에 **편파 시나리오 행** — 단일편파 수신 −3.010 dB. 커널 수정 아님, 선언 항목.
2. 3GPP 표적 XPR 인용 규약 — **7.99 dB(전력영역)**, 13.75 는 μ 라고 밝힌다.
3. 규격 비교표에서 **R < 10 m 행 제외**(규격 최소 3D 거리).
4. **P_fa Type 2** 를 낼 수 있는 다표적 드롭 — 없으면 규격 형식 보고가 불가능하다.
5. 센싱 **자원비**(Type_1/2/3, 두 옵션)로 우리 점유 축을 환산.
6. 리포트 11권 «분해능» 절에 **성능지표가 아니라 관측가능성 진단**이라고 명시.
7. TR 36.777 **Table B-1/B-2/B-3 수식** 확보 경로 찾기(OLE Equation 개체 렌더 또는 다른 판본).

---

## ⑭ 이번 보충의 출처

| # | 문서 | 판·날짜 | URL |
|---|---|---|---|
| P1 | **3GPP TR 38.901** (Rel-19) | V19.4.0 (2026-06) | `https://www.3gpp.org/ftp/Specs/archive/38_series/38.901/38901-j40.zip` |
| P4 | **3GPP TR 38.765** (Rel-20) | V20.0.0 (2026-06) | `https://www.3gpp.org/ftp/Specs/archive/38_series/38.765/38765-k00.zip` |
| **P11** | **3GPP TR 36.777**, *Study on Enhanced LTE Support for Aerial Vehicles* (Rel-15) | **V15.0.0 (2018-01)** | `https://www.3gpp.org/ftp/Specs/archive/36_series/36.777/36777-f00.zip` |

P1·P4 는 §⑧ 의 P1·P4 와 같은 파일이다. **P11 이 이번에 새로 확보한 1차자료**다.

우리 저장소 쪽 인용:
`outputs/isac_standard_gaps.json`(이번 생성) · `outputs/md_snr_vs_range.json` ·
`outputs/sigma_el_extend_verify.json` · `outputs/report13_sigma_grid.json` ·
`outputs/mono_link.json` · `src/materials.py` · `src/waveforms.py`
