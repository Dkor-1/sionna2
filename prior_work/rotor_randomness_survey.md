# 드론 로터 회전의 «랜덤성» 을 남들은 어떻게 모델링하나 — 조사 (2026-08-10)

> 목적: 우리 마이크로도플러 시뮬의 로터 모델(로터 4개에 **서로 다른 상수 rpm ±0.22 %** + **정현파 흔들림
> ±0.15 % @ 2.7 Hz** + **t=0 위상 정렬**)이 문헌·물리·오픈소스 관행 대비 어디에 서 있는지 확인한다.
> 수치 원장: `outputs/rotor_randomness_survey.json`.
>
> ⚠ 이 문서에서 **«원문 확인»** 은 PDF 를 내려받아 본문을 직접 읽었다는 뜻이고,
> **«초록만»** 은 초록/포털 메타데이터까지만 봤다는 뜻이다. 둘을 항목마다 표시했다.
> 못 본 것은 §7 에 «못 찾았다» 로 모아 두었다.

---

## 0. 네 줄 요약

1. **문헌 주류는 «모든 로터가 같은 rpm»** 이다. 초기 각도만 무작위로 흩뿌린다.
   원문 확인된 대표 문장: Cai(TU Delft, RADAR 2019) *"The propellers were assumed rotating with random
   angle shift at the **same velocity of 3000 rpm**"*.
2. **그 관행을 정면으로 잰 논문이 하나 있다** — White(버밍엄, IEEE TRS 2024). 실기 로그 rpm 을 쓴 판과
   «전 로터 고정 동일 rpm» 판으로 CNN 을 각각 학습시켜 실데이터로 시험했다.
   드론 재현율 **80.1 % → 74.5 %**, 정확도 **86.6 % → 84.4 %** 로 떨어진다.
   결론 문장: *"multi-rotor modelling and motor speed variation are **both required**"*.
   ⇒ **우리 «시간변동 없음» 은 문헌이 이미 대가를 측정해 둔 결함이다.**
3. **자세제어가 만드는 rpm 변동은 백색이 아니다. 저주파 지배가 물리적으로 강제된다.**
   바깥(자세각) 루프의 교차주파수가 PX4 `MC_ROLL_P=4.0 1/s` → **0.64 Hz**,
   ArduPilot `ATC_ANG_*_P=4.5 1/s` → **0.72 Hz** 다. 그 위로는 자이로 저역통과(PX4 40 Hz,
   ArduPilot 20 Hz)와 **로터 1차 시상수**(τ = 5~72 ms, 코너 2.2~32 Hz)가 이중으로 깎는다.
   ⇒ **가우시안 백색으로 두면 안 되고, 저역통과(1차 저역통과 잡음 = OU 과정)를 씌워야 한다.**
4. **우리 원장의 «지배 성분 0.3~2.2 Hz» 는 이 물리와 정확히 맞는다.**
   자세 루프 교차 0.64~0.72 Hz 가 그 구간 한복판이다. 우리 코드의 2.7 Hz 는 상단 바깥이고,
   무엇보다 **정현파 한 톤**이라 «선이 넓어짐» 이 아니라 «선이 빗살로 갈라짐» 을 만든다 —
   물리(랜덤 과정)와 **모양이 다르다**.

---

## 1. 우리 기록과 겹치는 부분 (먼저 선언)

`prior_work/` 를 먼저 훑었고, 아래는 **이미 우리 안에 있는 것**이다. 새 사실이 아니다.

| 이미 있는 것 | 어디에 | 이 조사와의 관계 |
|---|---|---|
| 실기 로그 3원천 앵커(NeuroBEM 0.54 % · CODEV 야외 2.35 % · DJI P3 DAT 2~6 %), 지배 0.3~2.2 Hz | `outputs/rotor_rpm_web_anchor.json` | §4 에서 **문헌·제어이론과 대조**했다. 값은 그대로 인용만 |
| PX4 SITL x500 의 τ = 12.5 / 25 ms, 정적 바이어스 0.08 %, 순시 산포 p50 0.26 % / p90 6.41 % | `docs/PRIOR_WORK_JIHYUCK.md:340-374` | §3-2·§5 에서 **원 소스코드로 재확인**(RotorS 기본값과 동일한 값임을 확정) |
| «로터별 초기위상을 난수로 뿌리면 창마다 상대위상이 균등분포로 흩어진다» | `docs/PRIOR_WORK_JIHYUCK.md:378-382` | §2-1 에서 **문헌이 정확히 그것을 한다**는 근거를 붙였다(Cai, Costa) |
| md-rt(ICCT 2025) 로터 모델은 정량 앵커로 쓰지 말 것 | `prior_work/sionna_sensing_survey.md:244-250` | 이 조사에서도 **로터 랜덤성 근거로 쓰지 않았다** |
| 현재 프리셋 2종(sitl / outdoor) | `benchmark/report07_hover_long.py:70-75` | §6 권고의 출발점 |

**새로 얻은 것**은 다음 넷이다 — (a) «전 로터 동일 rpm» 이 주류라는 **원문 문장**, (b) 그 단순화의
**분류 성능 대가를 잰 논문**, (c) rpm 변동 스펙트럼을 정하는 **제어 루프 대역폭의 1차 출처(파라미터 기본값)**,
(d) 오픈소스 시뮬레이터 5종에 **rpm 잡음 주입항이 하나도 없다**는 소스코드 확인.

---

## 2. 질문 1 — 마이크로도플러 문헌의 로터 모델

### 2-1. 주류: «전 로터 동일 rpm + 초기 각도만 무작위»

**Cai, Krasnov, Yarovoy (TU Delft), *Simulation of Radar Micro-Doppler Patterns for Multi-Propeller
Drones*, Int. Radar Conf. (RADAR) 2019, DOI 10.1109/RADAR41533.2019.171372** `[원문 확인]`

> "the backscattered signal series of DJI R2170 propellers were generated with sampling frequency
> fs = 1 kHz. **The propellers were assumed rotating with random angle shift at the same velocity of
> 3000 rpm** which is reasonable for drones." (§IV, 본문 p.4)

- 로터별 rpm 차이: **없다**(모두 3000 rpm).
- 초기 위상: **무작위**("random angle shift"). 분포는 명시하지 않는다.
- 시간 변동: **없다**.
- 블레이드: 얇은 선(thin-wire) 2개로 근사, 블레이드당 wire 길이 0.267 m / 0.053 m. 플렉싱·피치 변화 **없음**.
- 원문 PDF: <https://okrasnov.github.io/pdf/YCai-etal-2019-RADAR.pdf>

**Costa 외 (TU Ilmenau), *Modeling Micro-Doppler Signature of Multi-Propeller Drones in Distributed
ISAC*, arXiv:2504.05168 (저널판)** `[원문 확인 — 로컬 사본 및 arXiv HTML]`

> "Furthermore, propellers usually have **random initial azimuth angles (φ₀ₚ = 𝒰(0, 2π))** and
> **different rotation speeds ωₚ**, which can also be easily implemented with the proposed
> formulation." (§III-A1, 저널판 p.7)

- 초기 위상: **명시적으로 균등분포 𝒰(0, 2π)**. ← 우리가 채택해야 할 정확히 그 규약.
- 로터별 rpm: **다를 수 있다**(그림 예시는 1500 rpm 과 2000 rpm 두 개). 다만 **시간에 대해 상수**다.
- 시간 변동(흔들림): **없다**. ωₚ 는 파라미터일 뿐 확률과정이 아니다.
- 블레이드: rigid, homogeneous linear antenna — **플렉싱·피치 변화 없음**.
- ⭐ 다만 **몸체 진동은 확률과정으로 넣는다**(블레이드가 아니라 동체다):
  > "a displacement between two consecutive time steps t−1, and t was modeled as an **uniformly
  > distributed random variable**, with maximum displacement due to vibration given by D₀ …
  > Dᵥ(t) = Dᵥ(t−1) + D₀·𝒰(−1, 1)" (저널판 p.8, 식 (46)(47))
  즉 **랜덤워크**다. 우리에게 시사점: 이 분야가 «미세 변동은 랜덤과정으로 넣는다» 는 감각 자체는 갖고 있고,
  다만 **그 대상이 로터 속도가 아니라 동체 진동**이었을 뿐이다.

**Xu, Hong, Zhao, Yang (베이항대), *Detection and identification technology of rotor unmanned aerial
vehicles in 5G scene*, Int. J. Distributed Sensor Networks 15(6), 2019, DOI 10.1177/1550147719853990**
`[WebFetch 로 본문 렌더 — 인용문 2개 확인]`

> "the rotation speeds of four rotors are at **38.3, 41.8, 45.8, and 48.3 r/s**, respectively"
> "Due to the starting phase of different rotors is random, so the initial phase of each rotor is set to
> **0, π/4, π/2, and 3π/4**, respectively"

- 로터별 rpm 차이: **넣는다**. 평균 43.55 r/s 기준 산포가 **±11.5 %** — 실기체 로그(0.5~5 %)보다도 크다.
  근거는 없고 «시연용으로 크게 벌린 값» 으로 읽어야 한다. ⚠ **정량 앵커로 쓰지 말 것.**
- 초기 위상: «무작위» 라고 말하고 실제로는 **결정론적 등간격**(0, π/4, π/2, 3π/4)을 쓴다.
  우리의 현재 `phi0 = 2πk/n` 과 **똑같은 관행**이다.

**White 외 (버밍엄)가 정리한 문헌 지형** `[원문 확인]` — 아래 §2-3 논문의 §II:

> "**The most common choice found in literature is to apply the same estimated rotation speed to each
> motor** [19], [23], [24], [32], but increasingly more convincing results were found using dynamic
> and different motor speeds across each motor reverse engineered from a real trajectory [42], and
> more recently [34] which used real recorded motor speeds from a drone flight."

여기서 [19] Ahmad 외 IET ICRS 2022, [23] Choi & Oh ISAP 2018, [24] Raval 외 *Drones* 5(4):149 2021,
[32] = 위 Cai 2019. ⇒ **«전 로터 동일 rpm» 이 주류라는 것은 우리 추측이 아니라 이 분야가 스스로 쓴 문장이다.**

### 2-2. 로터별로 «다른 상수 rpm» 을 주는 사례

White 외 TRS 2024 §II 의 Fig. 2 실험(블레이드 길이 L = 0.19 m 쿼드) `[원문 확인]`:

| 판 | 로터 속도 | 스펙트로그램에서 보이는 것 |
|---|---|---|
| (a) | 전 로터 **100 Hz 고정** | *"uniform single sidebands are observed"* |
| (b) | **85 / 90 / 95 / 100 Hz** (로터별 다른 상수) | *"four distinct sidebands within each harmonic grouping that result from the differing speeds of each rotor blade"* |
| (c) | **실기 비행 로그의 실제 rpm 시계열** | 아래 §2-3 |

또 같은 절: *"Drone motor speeds would be expected to fall between **40 and 250 Hz**, depending
principally on the propellor length."* (= 2,400 ~ 15,000 rpm)

⇒ 우리의 «로터별 다른 상수 rpm» 은 **(b) 수준**이다. 문헌에서 이미 한 단계 위(c)가 있다.

### 2-3. ⭐ 시간에 따라 변하는 rpm — 실기 로그를 그대로 먹인 계열

**White, Jahangir, Baker, Antoniou, *Urban Bird-Drone Classification With Synthetic Micro-Doppler
Spectrograms*, IEEE Trans. Radar Systems, 2024 (온라인 2023-10-20), DOI 10.1109/TRS.2023.3326317**
`[원문 확인 — 저자판 PDF]` · 열람 URL <https://pure-oai.bham.ac.uk/ws/files/208677443/RevisedManuscript.pdf>

이 논문이 우리 질문에 가장 직접적이다. 요지:

- 로터 속도는 **DJI Inspire 실비행 로그에서 뽑는다**. 로그 기록률은 *"recorded at an approximate
  constant rate, of **30 Hz** for the Inspire"* — 즉 실기 모터 속도가 30 Hz 로 로깅된다.
- 레이더 PRF 7 kHz, 4096 펄스 STFT(Blackman-Harris, 50 % 겹침) → **CPI 0.56 s**.
- **«모터 속도 표집(motor speed sampling)» 을 네 가지로 바꿔가며 같은 CNN 을 학습**시켰다:
  1. **sub-CPI** — 로그를 신호 길이(~7.3 kHz)까지 0-패딩+저역보간으로 올린 뒤 평활. 가장 고충실.
  2. **per-CPI** — CPI 당 한 값으로 3차 스플라인 재표집. *"the sidebands in the simulation are overly
     clean and are of uniform spectral width"* — **너무 깨끗하다**는 자기 진단이 붙는다.
  3. **Single-Motor** — sub-CPI 인데 로터를 1개로 축소.
  4. **Fixed-Speeds** — *"a single speed for all four rotors … The fixed rotational frequency was
     constant across the flight"*. 논문이 **«문헌에 보고된 방식» 이라고 명시**하고 [19][24][32] 를 단다.
- 결과(실데이터 시험):

  | 판 | 정확도 | 드론 재현율(중앙값) |
  |---|---|---|
  | 실데이터 기준선 | **89.7 %** | 88.4 % |
  | sub-CPI | **86.6 %** | 80.1 % |
  | per-CPI | — | 78.8 % |
  | Single-Motor | — | (두 값 사이) |
  | **Fixed-Speeds** | **84.4 %** | **74.5 %** |

  > "the fixed-speeds fell significantly further demonstrating that **motor speed variation is an
  > essential component of training**" (§V-C)
  > "it has been found that **multi-rotor modelling and motor speed variation are both required to
  > prevent sub-optimal training producing a classifier with a high rate of false positives**" (§VII)
- ⭐ 바람과의 연결도 명시: *"**Wind will have a significant impact on a drone's motor speeds** which
  will be preserved in the recordings … Rapid changes in motor speeds over a CPI induced by wind
  changes or to enable a maneuver, manifested as artifacts in the per-CPI spectrogram as
  discontinuities in the spectral lines"* (§V-A1)
- ⚠ 이 논문도 **못 하는 것을 자백**한다: 실데이터에서 *"sidebands fluctuated in their appearance and
  power. **The simulation model presented in this paper does not attempt to model such fluctuations**"*
  (§V-B). 즉 rpm 시계열은 실측으로 채웠지만 **산란 진폭의 요동은 여전히 미모델**이다.

**앞선 회의판**: White 외, *Multi-rotor Drone Micro-Doppler Simulation Incorporating Genuine Motor
Speeds and Validation with L-band Staring Radar*, IEEE RadarConf 2022, DOI
10.1109/RadarConf2248738.2022.9764352 `[초록만 — 공개 전문 없음]`. 초록: *"by populating the equation
parameters with **genuine drone motor speed recordings**, a synthetic spectrogram was generated that
accurately captures the characteristic uDoppler sidebands"*. 위 TRS 논문이 이 회의판을 [34] 로 인용하며
상세를 재서술하므로, 우리는 **TRS 판을 1차 인용처로 쓴다**.

**Bennett, Harman, Petrunin, *Realistic Simulation of Drone Micro-Doppler Signatures*, EuRAD 2022,
DOI 10.23919/EuRAD50154.2022.9784488** `[초록만 — 전문 접근 실패]`. 초록 취지: 드론 비행의 **기구학·동역학을
모델링해 변하는 로터 회전율을 만든다**. 즉 «비행역학 시뮬 → rpm 시계열» 경로. 전문을 못 봐서
어떤 자동조종 모델인지, 잡음 주입이 있는지는 **확인 못 했다**.

**Gérard, *Drone recognition with Deep Learning*, PhD thesis, Univ. Paris-Saclay, 2022 (HAL
tel-03640378)** `[미열람]`. White TRS 가 [42] 로 인용하며 *"dynamic and different motor speeds across
each motor **reverse engineered from a real trajectory**"* 라고 요약한다. HAL 이 봇 차단(Anubis)이라
전문을 못 받았다.

### 2-4. 블레이드 플렉싱·피치 변화

- **Costa(arXiv:2504.05168)**: 블레이드는 rigid — 플렉싱 **없음** `[원문 확인]`.
- **Cai(RADAR 2019)**: 얇은 선 2개 — 플렉싱·피치 **없음** `[원문 확인]`.
- **Moore, Robertson, Rahman, IET RSN 18(3):477-492, 2024, DOI 10.1049/rsn2.12494 (CC-BY)**
  `[초록만 — 전문 접근 실패]`: CAD 기반 고충실 시뮬. 검색엔진 요약에 *"blade flexing can occur as
  malleable plastic blades rotate"* 라는 문장이 뜨지만 **원문에서 확인하지 못했다**.
  ⚠ **이 문장을 인용하지 말 것.** 전문 확보 후 다시 판정할 항목이다(§7).
- ⇒ **원문 확인 범위에서 블레이드 플렉싱·피치 변화를 넣은 마이크로도플러 시뮬 사례는 못 찾았다.**

### 2-5. 한 장 요약표

| 논문 | 로터별 rpm | 초기 위상 | 시간 변동(흔들림) | 블레이드 변형 | 확인 |
|---|---|---|---|---|---|
| Cai 2019 (RADAR) | **동일**(3000 rpm) | 무작위(분포 미명시) | 없음 | 없음 | 원문 |
| Costa 2025 (arXiv 2504.05168) | 다를 수 있음(상수) | **𝒰(0, 2π)** | 없음 | 없음(동체 진동은 랜덤워크) | 원문 |
| Xu 2019 (IJDSN) | 다름(±11.5 %, 근거 없음) | «무작위» 라 쓰고 등간격 사용 | 없음 | 없음 | 본문 렌더 |
| White 2024 (IEEE TRS) | **실기 로그 4채널** | (모델 (1)에 blade 항 2πb/B) | **있음 — 로그 시계열** | 없음 | 원문 |
| White 2024 의 Fixed-Speeds 대조군 | 동일·상수 | — | 없음 | 없음 | 원문 |
| Bennett 2022 (EuRAD) | 비행역학이 생성 | ? | **있음(주장)** | ? | 초록만 |
| Moore 2024 (IET RSN) | ? | ? | ? | ? (플렉싱 언급 소문) | 초록만 |
| **우리 현재** | 다름(**±0.22 %** 상수) | **정렬(0)** | 정현파 1톤 ±0.15 % @2.7 Hz | 없음 | — |

---

## 3. 질문 2 — 자세제어가 만드는 rpm 변동의 «스펙트럼» 물리

결론부터: **저주파 지배다. 백색이 아니다.** 이유는 세 겹이고, 셋 다 1차 출처로 수치가 잡힌다.

### 3-1. 겹 1 — 제어 루프의 교차주파수가 «어디에 에너지가 실리나» 를 정한다

멀티로터 자동조종은 3중 캐스케이드다(위치 → 자세각 → 각속도). 바깥 두 루프는 **비례(P) 제어**이고,
P 게인의 단위가 그대로 **1/초**여서 **게인 = 교차 각주파수** 로 읽힌다.

| 항목 | 값 | 1차 출처(파일:줄) | Hz 환산 |
|---|---|---|---|
| PX4 자세각 P 게인 `MC_ROLL_P` | **4.0** ("desired angular speed in **rad/s** for error 1 rad") | `PX4-Autopilot/src/modules/mc_att_control/mc_att_control_params.yaml:5-11` | **0.64 Hz** |
| ArduPilot 자세각 P `ATC_ANG_*_P` | **4.5** | `ardupilot/libraries/AC_AttitudeControl/AC_AttitudeControl.h:15` (`AC_ATTITUDE_CONTROL_ANGLE_P 4.5f`), 사용처 `AC_AttitudeControl.cpp:1141-1144` | **0.72 Hz** |
| PX4 수평위치 P `MPC_XY_P` | **0.95** (m/s per m) | `.../mc_pos_control/multicopter_position_control_gain_params.yaml:15-20` | **0.15 Hz** |
| PX4 수직위치 P `MPC_Z_P` | **1.0** | 같은 파일 :5-10 | **0.16 Hz** |
| PX4 각속도 루프 게인 | `MC_ROLLRATE_P` 0.15 · `I` 0.2 · `D` 0.003 | `.../mc_rate_control/mc_rate_control_params.yaml:5-45` | (아래 필터가 상한을 정함) |

**해석**: 호버 중 rpm 을 흔드는 «명령» 은 대부분 **자세각 루프가 바람·비대칭을 되받아치는 동작**이다.
그 루프가 0.6~0.7 Hz 에서 교차한다는 것은, **그보다 느린 외란은 루프가 거의 그대로 되받아치고
(→ rpm 에 1:1 로 나타나고), 그보다 빠른 외란은 루프가 따라가지 못한다**(→ rpm 에 덜 나타난다)는 뜻이다.
게다가 외란(바람·난류) 자체의 스펙트럼도 저주파가 크다. **두 효과가 같은 방향으로 겹쳐 저주파 지배가 된다.**

### 3-2. 겹 2 — 각속도 루프의 상한은 자이로 저역통과가 정한다

| 항목 | 값 | 1차 출처 |
|---|---|---|
| PX4 자이로 저역통과 `IMU_GYRO_CUTOFF` | **40.0 Hz** (2차 버터워스, *"only affects the angular velocity sent to the controllers"*) | `.../sensors/vehicle_angular_velocity/imu_gyro_parameters.yaml:73-85` |
| PX4 D항 저역통과 `IMU_DGYRO_CUTOFF` | **20.0 Hz** | 같은 파일 :111-127 |
| PX4 각속도 루프 실행률 `IMU_GYRO_RATEMAX` | **400 Hz** (*"This is the loop rate for the rate controller and outputs"*) | 같은 파일 :90-110 |
| ArduPilot 자이로 필터 `INS_GYRO_FILTER` | **20 Hz** (Copter 기본) | `ardupilot/libraries/AP_InertialSensor/AP_InertialSensor.cpp:64-66, 344-350` |
| ArduPilot 각속도 루프 T/D 필터 | **20 Hz** | `.../AC_AttitudeControl/AC_AttitudeControl_Multi.h:22-23` (`AC_ATC_MULTI_RATE_RPY_FILT_HZ 20.0f`) |
| ArduPilot 메인 루프 | **400 Hz** (Copter) | `.../AP_Scheduler/AP_Scheduler.cpp:43-47` |
| ArduPilot 스루틀 슬루 제한 `MOT_SLEW_UP/DN_TIME` | **기본 0 = 끔** | `.../AP_Motors/AP_MotorsMulticopter.h:21`, `.cpp:207-221` |

**해석**: 루프는 400 Hz 로 돌지만 **명령이 실제로 흔들릴 수 있는 상한은 자이로 필터의 20~40 Hz** 다.
그 위는 «컨트롤러가 볼 수 없어서» 명령도 안 흔들린다.
⭐ 우리 원장이 DJI P3 **명령(PWM)** 영역에서 잰 **13~19 Hz 성분**은 정확히 이 각속도 루프 대역이다 —
20 Hz 필터 바로 밑. 즉 그 관측은 앨리어싱 잡음이 아니라 **제어 구조가 예측하는 자리에 있다.**

### 3-3. 겹 3 — 로터 관성이 고주파를 한 번 더 깎는다

모터+프로펠러는 **1차 지연**으로 모델링된다(§5 의 시뮬레이터 5종 전부, 그리고 실측 시스템동정도).
전달함수 1/(τs+1), 코너 f_c = 1/(2πτ).

| 출처 | τ | 코너 f_c |
|---|---|---|
| AirSim `RotorParams.hpp:43` `control_signal_filter_tc = 0.005f` | 5 ms | **31.8 Hz** |
| RotorS/PX4/gz-sim `kDefaultTimeConstantUp = 1/80` | 12.5 ms | **12.7 Hz** |
| 같은 곳 `kDefaultTimeConstantDown = 1/40` | 25 ms | **6.4 Hz** |
| Flightmare `quadrotor_dynamics.cpp:15` `motor_tau_inv_(1.0/0.05)` | 50 ms | **3.2 Hz** |
| UZH 실측 시스템동정(arXiv:2404.07837 §IV-A, Crazyflie) `Tm = 0.072 s` — 제조사 스텝응답 ≈0.073 s 와 일치 | 72 ms | **2.2 Hz** |

**명령→실제 rpm 감쇠**(1차, dB):

| τ \ 주파수 | 0.7 Hz | 1 Hz | 2 Hz | 5 Hz | 10 Hz | 15 Hz | 20 Hz |
|---|---|---|---|---|---|---|---|
| 5 ms | −0.00 | −0.00 | −0.02 | −0.11 | −0.41 | −0.87 | −1.45 |
| 12.5 ms | −0.01 | −0.03 | −0.11 | −0.62 | −2.09 | −3.78 | −5.40 |
| 25 ms | −0.05 | −0.11 | −0.41 | −2.09 | −5.40 | −8.16 | −10.36 |
| 50 ms | −0.21 | −0.41 | −1.45 | −5.40 | −10.36 | −13.66 | −16.07 |
| 72 ms | −0.42 | −0.81 | −2.60 | −7.86 | −13.32 | −16.73 | −19.18 |

**해석**: 0.3~2 Hz 대는 로터 관성이 **거의 안 깎는다**(≤2.6 dB). 반대로 13~19 Hz 명령 성분은
τ = 25 ms 면 −8 dB, τ = 72 ms 면 −17 dB 로 줄어든다.
⇒ **명령 영역에서 큰 13~19 Hz 성분이 실제 rpm 영역에서는 작게 보이는 현상이 정량적으로 설명된다.**
(우리 원장의 DJI P3 «명령 10~33 % @13~19 Hz» ↔ NeuroBEM 실측 rpm «0.6~1.1 % @0.7~2.2 Hz» 의 간극.)

### 3-4. ⇒ «가우시안 백색인가, 저역통과를 씌워야 하나» 의 답

**저역통과를 씌워야 한다.** 최소 1극, 정직하게는 2극이다.

```
백색 가우시안  →  [1차 저역통과 f≈0.7 Hz]  →  [1차 저역통과 f≈6~13 Hz]  →  Δrpm/rpm
                    (자세 루프 대역)            (로터 관성 τ=12.5~25 ms)
```

- 첫 극(≈0.7 Hz)이 «지배 주파수» 를 만든다 — 우리 원장의 0.3~2.2 Hz 와 일치.
- 둘째 극(6~13 Hz)이 «13~19 Hz 명령 성분이 rpm 에서 작아지는» 것을 만든다.
- 실용적으로는 **첫 극만 써도 된다**(OU 과정 = 1차 저역통과 백색잡음, 시상수 0.2~0.25 s).
  둘째 극은 8~20 dB 짜리 세부다.
- ⚠ **정현파 한 톤은 물리적으로 틀린 모양이다.** 랜덤과정은 선을 **넓히고**, 정현파는 선을
  **±f_m 간격 빗살로 가른다**. 음향 쪽 1차 문헌도 같은 말을 한다 —
  Physics of Fluids 33, 127107 (2021), DOI 10.1063/5.0071850 초록 `[초록 확인]`:
  > "**a random process was applied to reflect the RPM fluctuation effects** … Frequency and amplitude
  > modulation characteristics due to RPM fluctuations were observed **despite the considered hovering
  > condition** … an azimuthal noise directivity pattern in a circular shape was observed, which
  > corresponds to the **collapse of the phase effect due to the RPM fluctuation of each rotor**"

  마지막 구절이 우리에게 특히 중요하다 — **rpm 이 흔들리면 로터 사이의 위상 관계가 무너진다.**
  즉 «로터 4개가 코히런트하게 더해지는 깨끗한 빗살» 은 rpm 이 완벽히 일정할 때만 생기는 인공물이다.

---

## 4. 질문 3 — 공개 로그 실측치 vs 문헌·제어이론 대조

우리 원장(`outputs/rotor_rpm_web_anchor.json`)의 값과 위 물리·문헌을 나란히 놓으면:

| 축 | 우리 원장의 실측 | 제어이론이 예측하는 것 | 판정 |
|---|---|---|---|
| **지배 주파수** | NeuroBEM 0.7~2.2 Hz · CODEV 중앙 0.74 Hz(사분 0.5~1.5) · P3 다수 0.3~0.9 Hz | 자세각 루프 교차 **0.64 Hz**(PX4) / **0.72 Hz**(ArduPilot) | ⭐ **정합.** 세 원천의 중앙값이 이론 교차주파수와 10 % 안에서 만난다 |
| **저주파 꼬리(<0.5 Hz)** | 있음 | 위치 루프 **0.15 Hz** + 바람의 붉은 스펙트럼 | 정합 |
| **명령 영역 13~19 Hz** | P3 PWM 10~33 % | 각속도 루프 대역(자이로 필터 20~40 Hz 밑) | 정합 |
| **실측 rpm 영역에서 그 성분이 작음** | NeuroBEM 10~15 Hz 부성분(일부 창) | 로터 τ 저역통과 −5~−17 dB | 정합 |
| **정적 산포** | 실내 0.54 % · 야외 2.35 % · P3 2~6 % | (제어이론이 정하지 않음 — CG 오프셋·개체차·바람 트림) | 이론 무관, 실측만이 답 |
| **우리 코드의 2.7 Hz** | 관측 범위 상단 밖 | 이론 교차의 **4배** | ❌ **높다** |
| **우리 코드의 ±0.15 % 정현파** | 실측 0.6~1.1 %(실내) / 2.0~3.8 %(야외) | — | ❌ **5~25배 과소 + 모양도 다름** |

**추가 정합 증거(문헌)**: White TRS 2024 가 *"Wind will have a significant impact on a drone's motor
speeds"* 라고 쓴 것은 우리 원장이 «야외 CODEV 2.35 % ≫ 실내 NeuroBEM 0.54 %» 로 관측한 **실내/야외
한 자릿수 격차**와 같은 이야기다. 즉 «두 레짐 프리셋» 이라는 우리 설계 판단은 문헌의 서술과 맞는다.

**우리 조건에서의 파급(산술)** — `outputs/report07_hover_long.json` 기준
(Matrice 4E, 3.5 GHz, rpm₀ 3800, f_flash 126.67 Hz, f_tip 1228.7 Hz, CPI 2 s → 도플러 빈 0.5 Hz):

| 항목 | 현 SITL 프리셋(0.22 % / 0.15 % @2.7 Hz) | 야외 앵커(2 % / 2.5 % @1 Hz) |
|---|---|---|
| 로터별 선 갈라짐 @ 1차 조화(126.7 Hz) | 0.56 Hz ≈ **1 빈** | 5.1 Hz ≈ **10 빈** |
| 로터별 선 갈라짐 @ 10차 조화(1267 Hz) | 5.6 Hz | **51 Hz** |
| 흔들림에 의한 순시 편이 @ 10차 | ±1.9 Hz | **±31.7 Hz** |
| Carson 대역(≈2(Δf+f_m)) @ 10차 | **9 Hz** | **65 Hz** |

⇒ **야외 실측 수준을 넣으면 높은 차수 HERM 선은 2 초 CPI 에서 수십 빈으로 번진다.**
이것이 White 가 실데이터에서 본 *"non-uniform bandwidth"* · *"sidebands fluctuated in their appearance
and power"* 의 정체일 가능성이 높다. **우리 그림의 «가늘고 선명한 빗살» 은 값이 작아서 생긴 것이다.**

⚠ 반증 여지: 지배 주파수가 0.7~1 Hz 면 **2 초 CPI 안에 1~2 주기밖에 안 들어간다**. 그러면 대칭 FM
측대역이 아니라 **창 안에서 선이 통째로 표류**하는 모습이 된다 — 이것이 White 의 per-CPI(창마다 한 값,
불연속) vs sub-CPI(창 안에서도 변함) 구분이 잡아낸 바로 그 차이다. **우리도 창 안 변동을 넣어야 한다.**

---

## 5. 질문 4 — 오픈소스 시뮬레이터는 로터 속도를 어떻게 만드나

**전부 «1차 지연», 잡음 주입항은 하나도 없다.** 소스코드로 확인했다.

| 시뮬레이터 | 모델 | 시상수 | rpm 잡음 주입 | 1차 출처(파일:줄) |
|---|---|---|---|---|
| **PX4 SITL (gazebo-classic)** | `FirstOrderFilter`, ZoH 이산화 x(k+1)=e^(−dt/τ)x(k)+(1−e^(−dt/τ))u(k) | τ_up 1/80 s, τ_dn 1/40 s | **없음**(파일 전체에 noise/random 문자열 0건) | `PX4-SITL_gazebo-classic/src/gazebo_motor_model.cpp:136-137, 161, 254`; 기본값 `include/gazebo_motor_model.h:68-69`; 필터 구현 `include/common.h:122-165` |
| **PX4 (gz-sim, 최신 기본)** | 동일 구현 이식 | 동일 1/80, 1/40 | **없음** | `gz-sim/src/systems/multicopter_motor_model/MulticopterMotorModel.cc:67-100, 204-208, 371-372, 676` |
| **RotorS (ETH)** | 동일(원조) | 동일 1/80, 1/40 | **없음** | `rotors_simulator/rotors_gazebo_plugins/src/gazebo_motor_model.cpp:194-208`; `include/.../gazebo_motor_model.h:66-67` |
| **AirSim** | `FirstOrderFilter` on control signal | **0.005 s** | **없음** | `AirLib/include/vehicles/multirotor/RotorParams.hpp:43`; 적용 `RotorActuator.hpp:54, 62, 95` |
| **Flightmare (UZH)** | *"simulate motors as a first-order system"*, ω ← cω + (1−c)ω_des, c = e^(−dt/τ⁻¹) | **0.05 s** | **없음** | `flightlib/src/objects/quadrotor.cpp:120-128`; 기본값 `src/dynamics/quadrotor_dynamics.cpp:15` |

### 그러면 SITL 로그의 rpm 흔들림(우리 원장의 0.07~0.29 %)은 어디서 오나

모터 모델이 아니라 **루프를 한 바퀴 돌아 들어온다**:

1. **IMU 센서 잡음** — `gazebo_imu_plugin.cpp` 가 `gyroscope_noise_density` · `gyroscope_random_walk` ·
   `bias_correlation_time`(가속도계도 동일 3종)으로 가우시안 잡음을 주입한다
   (`PX4-SITL_gazebo-classic/src/gazebo_imu_plugin.cpp:71-92`).
   이 잡음 → 추정기 → 자세/각속도 제어기 → 모터 지령 → **rpm 흔들림**.
2. **바람 플러그인**(옵션) — `gazebo_wind_plugin.cpp:58-79` 가 풍속·풍향을 정규분포로 뽑고
   `windGust*` 로 돌풍을 준다. **기본 씬에는 대개 안 붙어 있다.**
3. **비대칭이 아예 없다** — 우리 내부 기록(`docs/PRIOR_WORK_JIHYUCK.md:367-374`)이 이미 잰 대로
   SITL 의 로터별 평균은 0.08 % 안에 든다. 완전 대칭 기체 + 이상적 제어할당기라
   **CG 오프셋·프로펠러 불균형·모터 개체차가 존재하지 않는다.**

⭐ **그래서 SITL 유래 ±0.22 % 가 실기체보다 한 자릿수 작은 것은 버그가 아니라 구조다.**
잡음이 «센서 잡음 한 종» 밖에 없고, 정적 비대칭이 0 이고, 바람이 꺼져 있기 때문이다.

### 참고 — 실기체 τ 를 잰 1차 자료

Bauersfeld 계열(UZH RPG), *Data-Driven System Identification of Quadrotors Subject to Motor Delays*,
arXiv:2404.07837 `[원문 확인]`:
- 모델 식 (10): `ω̇ₘ = Tₘ⁻¹(ω_sp − ωₘ)` — *"decoupled first-order systems subject to the time-constant Tₘ"*.
- Crazyflie 추정 **Tₘ = 0.072 s**, 제조사 스텝응답 판독 ≈0.073 s, 선행 문헌 추정 0.065 s (§IV-A).
- 프로프리오셉티브 로그 **1000 Hz**.
- ⚠ 큰 쿼드(§IV-B, Fig. 8)는 본문이 *"the delay is much smaller than … the Crazyflie"* 라고 쓰는데
  그림 주석은 **Tₘ = 0.065 s** 로 읽힌다 — 0.072 대비 «much smaller» 가 아니다. **내부 불일치로 표시**하고
  큰 기체의 τ 는 이 논문에서 확정값으로 쓰지 않는다.
- ⚠ Tₘ 은 «지령→추력» 지연이라 ESC + 모터 + 프로펠러 관성이 합쳐진 값이다. 프로펠러가 커지면
  관성이 커져 τ 도 커지는 방향이지만, **우리 표적(Mavic 4 Pro·Matrice 4E)의 τ 는 못 찾았다.**

---

## 6. 우리 모델에 대한 함의 (권고 — 즉시 반영 가능한 형태)

현재: `benchmark/report07_hover_long.py:70-116`
```
stat  = STATIC_SPREAD * PATTERN[k]                       # 로터별 상수 치우침
phi0  = 2π k / n                                          # ← 흔들림의 «위상», 결정론적
rpm_t = rpm0 * (1 + stat + WOBBLE_AMP*sin(2π·WOBBLE_HZ·t + phi0))
ang   = cumsum(360·rpm_t/60 · dt)                         # 회전각은 적분 ✅ (이건 옳다)
```

권고 4건. **상류(모양) → 하류(값)** 순서다.

1. ⭐⭐ **흔들림을 정현파 → 저역통과 잡음(OU 과정)으로 바꾼다.** 모양이 틀린 것이 값이 틀린 것보다 상류다.
   ```
   e_k(t+dt) = e_k(t)·exp(-dt/T) + σ·sqrt(1-exp(-2dt/T))·N(0,1)    # 로터마다 독립
   T = 1/(2π·0.7 Hz) ≈ 0.23 s        # 자세각 루프 교차(PX4 4.0 1/s / ArduPilot 4.5 1/s)
   ```
   근거: §3-1(루프 게인), §3-4(랜덤과정), Physics of Fluids 2021 초록.
   원한다면 두 번째 극(τ_motor = 12.5~25 ms)을 직렬로 하나 더 건다 — 8~20 dB 짜리 세부다.
2. ⭐ **로터별 초기 회전위상을 𝒰(0, 2π) 로 뽑는다.** 지금 t=0 정렬은 문헌 관행(Cai «random angle shift»,
   Costa «φ₀ₚ = 𝒰(0, 2π)»)과도 어긋나고, 우리 내부 기록도 이미 같은 것을 권고했다
   (`docs/PRIOR_WORK_JIHYUCK.md:378-382`). 시드는 원장에 남긴다.
3. **σ(흔들림 진폭)는 두 레짐 유지 — 실내 0.8 % / 야외 2.5 %.** 값 자체는 우리 원장이 이미 정했고
   이 조사가 바꿀 근거는 없다. 다만 라벨을 «정현파 진폭» 이 아니라 **«상대 rpm 의 표준편차 σ»** 로 바꿔야 한다
   (랜덤과정에서는 진폭이 아니라 σ 가 파라미터다).
4. **`WOBBLE_HZ = 2.7` 은 폐기한다.** OU 로 바꾸면 «주파수» 파라미터가 아예 없어지고 **시상수 T** 만 남는다.
   보고서 서술도 «2.7 Hz 로 흔든다» 가 아니라 «자세 루프 대역(≈0.7 Hz)까지 붉은 잡음» 으로 바꾼다.

⚠ **하지 말아야 할 것**: 가우시안 **백색**으로 바꾸는 것. §3 이 그것을 배제한다. 백색이면 PRF(19.7 kHz)까지
평평한 잡음이 되어 실제로는 존재하지 않는 고주파 흔들림을 넣게 된다.

⚠ **파급 점검 필요**: §4 의 산술대로면 야외 σ 에서 10차 HERM 선의 Carson 대역이 **65 Hz** 다.
`report11`(저속·분해능·관측) 의 분해능 논의와 충돌하는지 재확인해야 한다. 이 조사는 그 재계산을 하지 않았다.

---

## 7. 못 찾은 것 (지어내지 않는다)

1. **Moore, Robertson, Rahman, IET RSN 2024 (DOI 10.1049/rsn2.12494) 전문** — CC-BY 인데 Wiley·
   St Andrews 리포지터리·research-portal 파일 링크가 이 호스트에서 전부 403/타임아웃. 초록만 봤다.
   ⇒ **«블레이드 플렉싱을 모델링한다» 는 검색엔진 요약 문장을 확인하지 못했다. 인용 금지.**
2. **White 외 RadarConf 2022 (DOI 10.1109/RadarConf2248738.2022.9764352) 전문** — 공개판 없음(Unpaywall
   OA 위치 0건). 같은 저자의 TRS 2024 판 서술로 대체했다.
3. **Bennett 외 EuRAD 2022 전문** — Cranfield CERES 가 봇 차단. 어떤 비행역학 모델로 rpm 시계열을
   만드는지, 잡음이 있는지 **모른다**.
4. **Gérard PhD thesis (HAL tel-03640378) 전문** — HAL Anubis 봇 차단. «궤적에서 역산한 로터별 속도» 의
   구체 방법을 **못 봤다**.
5. **NATO STO MP-MSG-SET-183-01 / DTIC AD1151840** — 둘 다 403.
6. **rpm 변동의 «측정된 PSD 그림» 을 실은 논문** — 음향 쪽(Physics of Fluids 2021, JSV 2024,
   JMST 2020)이 rpm 변동을 확률과정으로 다루지만 **전부 유료이고 초록에 수치가 없다**.
   ⇒ 지금 우리가 가진 유일한 정량 스펙트럼은 **우리 원장(`rotor_rpm_web_anchor.json`)의 실측**이다.
7. **우리 표적 기체(DJI Mavic 4 Pro · Matrice 4E)의 로터 시상수 τ 와 rpm 변동 통계** — 못 찾았다.
   DJI 는 최신 기종 DAT 를 암호화한다(우리 원장이 이미 기록). **자체 실측이 유일한 경로다.**
8. **블레이드 피치 변화(가변 피치)를 넣은 마이크로도플러 시뮬** — 소형 멀티로터는 고정 피치라
   애초에 대상이 아닐 가능성이 크지만, 확인된 사례는 **0건**이다.

---

## 8. 출처 목록

### 논문
- Y. Cai, O. Krasnov, A. Yarovoy, "Simulation of radar micro-Doppler patterns for multi-propeller
  drones," *Int. Radar Conf. (RADAR)*, Toulon, 2019, DOI 10.1109/RADAR41533.2019.171372.
  PDF <https://okrasnov.github.io/pdf/YCai-etal-2019-RADAR.pdf> `[원문 확인]`
- H. C. A. Costa, S. J. Myint, C. Andrich, S. W. Giehl, C. Schneider, R. S. Thomä, "Modeling
  micro-Doppler signature of multi-propeller drones in distributed ISAC," arXiv:2504.05168
  <https://arxiv.org/abs/2504.05168> `[원문 확인]`
- F. Xu, T. Hong, J. Zhao, T. Yang, "Detection and identification technology of rotor unmanned aerial
  vehicles in 5G scene," *Int. J. Distributed Sensor Networks* 15(6), 2019,
  DOI 10.1177/1550147719853990 `[본문 렌더 확인]`
- D. White, M. Jahangir, C. J. Baker, M. Antoniou, "Urban bird-drone classification with synthetic
  micro-Doppler spectrograms," *IEEE Trans. Radar Systems*, 2024, DOI 10.1109/TRS.2023.3326317.
  저자판 <https://pure-oai.bham.ac.uk/ws/files/208677443/RevisedManuscript.pdf> `[원문 확인]`
- D. White et al., "Multi-rotor drone micro-Doppler simulation incorporating genuine motor speeds and
  validation with L-band staring radar," *IEEE RadarConf*, 2022,
  DOI 10.1109/RadarConf2248738.2022.9764352 `[초록만]`
- C. Bennett, S. Harman, I. Petrunin, "Realistic simulation of drone micro-Doppler signatures,"
  *EuRAD*, 2022, DOI 10.23919/EuRAD50154.2022.9784488 `[초록만]`
- M. Moore, D. A. Robertson, S. Rahman, "A new simulation methodology for generating accurate drone
  micro-Doppler with experimental validation," *IET Radar Sonar Navig.* 18(3):477-492, 2024,
  DOI 10.1049/rsn2.12494 `[초록만]`
- J. Gérard, "Drone recognition with deep learning," PhD thesis, Univ. Paris-Saclay, 2022,
  HAL tel-03640378 `[미열람]`
- (음향) "Random process-based stochastic analysis of multirotor hovering noise under rotational speed
  fluctuations," *Physics of Fluids* 33(12):127107, 2021, DOI 10.1063/5.0071850 `[초록 확인]`
- (음향) "Effect of rotation speed fluctuation on rotor noise generation: A numerical and experimental
  study," *J. Sound Vib.*, 2024, DOI 10.1016/j.jsv.2024.118717 `[제목만]`
- (음향) "Noise prediction of multi-rotor UAV by RPM fluctuation correction method," *J. Mech. Sci.
  Technol.*, 2020, DOI 10.1007/s12206-020-0305-2 `[제목만]`
- (동정) "Data-driven system identification of quadrotors subject to motor delays," arXiv:2404.07837
  <https://arxiv.org/abs/2404.07837> `[원문 확인]`

### 코드 (전부 원 소스 확인, 기본 브랜치 2026-08-10 시점)
- PX4/PX4-SITL_gazebo-classic — `src/gazebo_motor_model.cpp`, `include/gazebo_motor_model.h`,
  `include/common.h`, `src/gazebo_imu_plugin.cpp`, `src/gazebo_wind_plugin.cpp`
- gazebosim/gz-sim (gz-sim9) — `src/systems/multicopter_motor_model/MulticopterMotorModel.cc`
- ethz-asl/rotors_simulator — `rotors_gazebo_plugins/src/gazebo_motor_model.cpp`, 동 헤더
- microsoft/AirSim — `AirLib/include/vehicles/multirotor/RotorParams.hpp`, `RotorActuator.hpp`
- uzh-rpg/flightmare — `flightlib/src/objects/quadrotor.cpp`, `flightlib/src/dynamics/quadrotor_dynamics.cpp`
- PX4/PX4-Autopilot — `src/modules/mc_att_control/mc_att_control_params.yaml`,
  `src/modules/mc_rate_control/mc_rate_control_params.yaml`,
  `src/modules/mc_pos_control/multicopter_position_control_gain_params.yaml`,
  `src/modules/sensors/vehicle_angular_velocity/imu_gyro_parameters.yaml`
- ArduPilot/ardupilot — `libraries/AC_AttitudeControl/AC_AttitudeControl.h`, `AC_AttitudeControl.cpp`,
  `AC_AttitudeControl_Multi.h`, `libraries/AP_InertialSensor/AP_InertialSensor.cpp`,
  `libraries/AP_Scheduler/AP_Scheduler.cpp`, `libraries/AP_Motors/AP_MotorsMulticopter.{h,cpp}`

### 우리 기록
- `outputs/rotor_rpm_web_anchor.json` — 실기 로그 3원천 앵커
- `docs/PRIOR_WORK_JIHYUCK.md:330-382` — PX4 SITL rpm 분포 실측·초기위상 권고
- `benchmark/report07_hover_long.py:60-130` — 현재 로터 모델
- `outputs/report07_hover_long.json` — 현재 실행 파라미터(f_flash 126.67 Hz, f_tip 1228.7 Hz)
