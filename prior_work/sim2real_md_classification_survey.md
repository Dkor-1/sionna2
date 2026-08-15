# 드론 마이크로도플러 분류 딥러닝 — sim-to-real 축 조사 (2026-08-15)

> 조사 범위: ① **시뮬레이션(운동학/EM) 스펙트로그램으로 학습해 실측에 적용**한 드론 분류와
> 그 **도메인 갭 처리법** ② 시뮬 전용 학습(실측 검증 없음) 사례 ③ 레이트레이싱(Sionna 포함)·
> ISAC 계열의 마이크로도플러 합성 축 ④ 실측 딥러닝 기준선의 **정확한 아키텍처 이름**.
> 경로: WebSearch + Semantic Scholar/OpenAlex API 서지 확정 + 로컬 PDF 1편 직독
> (`pdfs/eusipco2020_1561__gerard_*.pdf`). 인용은 전부 1차 자료(DOI/arXiv/공개 PDF).
> 기존 서베이(`passive_ofdm_dl_survey.md` · `rotor_randomness_survey.md` ·
> `noise_modeling_survey.md`)가 이미 원문 정독한 편은 §0 에서 잇고 **재조사하지 않았다**.
> 확인 못 한 것은 §6 에 «못 찾았다» 로 남겼다.

---

## TL;DR — 다섯 줄

1. **sim-to-real 정면 대결의 최상 선례는 White 외 (IEEE TRS vol.2, 2024, 버밍엄)** —
   합성으로 학습한 AlexNet(ImageNet 사전학습·conv 동결)이 실측 L밴드 응시레이더 시험에서
   **86.6±0.5%**, 실측 학습 기준선은 **89.7±0.5%** (**−3.1 pp**). 단 ⛔«합성만»이 아니라
   **반합성**(큰 드론 2종만 합성 + 실측 배경 시계열에 주입)이다 —
   이 편은 `passive_ofdm_dl_survey.md` 가 이미 원문 정독했다.
2. **도메인 갭 처리법은 문헌에서 4갈래다** — (a) **시뮬 충실도를 올린다**: 실기 모터속도
   로그(White RadarConf22), 레이저스캔 CAD(Moore IET RSN 2024) (b) **합성 표적을 실측 배경에
   주입**(White) (c) ⭐**시뮬을 학습데이터가 아니라 분류기 앞단 물리 사전(prior)으로**(Kearney
   & Gurbuz TAES 62 — «저충실도 시뮬 단독 학습은 random guessing 을 못 넘었다», §V-A)
   (d) **모델기반 증강**(Rojhani TMTT 71 — 관행 증강 66.18% ↔ 모델기반 78.68%).
3. **시뮬 전용 학습(실측 검증 없음)은 많고, 그 정확도는 상한으로만 읽는다** —
   Raval 외 Drones 2021(Martin–Mulgrew 운동학 모델, 맞춤 CNN, **F1 0.816±0.011 @학습 SNR
   10 dB**), Malarvanan arXiv:2403.02080(CNN vs 하이브리드 양자 NN), Zhang & Song Drones
   2026(L/K 이중대역 + **Mamba 상태공간 백본**, 97.5%). 전부 실측 시험이 없다.
4. ⭐**우리 스택과 직결되는 신규 발굴 2편**: Li 외 (IEEE ICCT 2025)가 **Sionna RT** 로
   멀티로터 마이크로도플러를 CSI 에서 뽑았고(분류 없음), Costa 외 (IEEE JSTEAP 1(1):208–222,
   2025)는 바이스태틱 OFDM thin-wire 모델을 실측으로 검증하며 **«ML 학습 데이터셋 생성»을
   목적이라 자인하고 학습 자체는 비워 뒀다**. 즉 이번 범위에서
   **레이트레이싱/ISAC 축으로 분류까지 간 논문은 없다** — 그 칸이 우리 자리다.
5. **실측 딥러닝 기준선의 이름은 GoogLeNet 이 지배적** — Kim 외 GRSL 2017(MDS+CVD 병합
   이미지, 89.3→94.7%), Rahman & Robertson IET RSN 2020(4클래스 시험 94.4%), Gérard 외
   EUSIPCO 2020(입력표현 5종 비교 — **WSP 98.1% 최상**, ⭐날짜 분리 없으면 98~100%로
   부풀어 오름). 드론 전용 GAN 증강·명시적 DANN 류 도메인 적응은 **못 찾았다**(§6).

---

## 0. 우리 기록과 겹치는 부분 (먼저 확인함)

| 우리 기록 | 겹치는 내용 | 본 조사의 추가 |
|---|---|---|
| `passive_ofdm_dl_survey.md:323` (§3-1 표) | **White TRS 2024 원문 정독** — AlexNet conv 동결·FC만 학습, 20 timestep=5.6 s RGB, 실측 89.7 ↔ 합성 86.6, 비행 단위 분할 | 재조사 안 함. 본 조사는 계보(RadarConf22 전신)와 갭 처리법 분류에만 씀 |
| `passive_ofdm_dl_survey.md` §5-1 C3 | ⛔«합성만» 과장 정정 — 큰 드론 2종만 합성(학습셋 34.5%), 실측 배경에 주입 = **반합성** | 그대로 승계. 아래 §1 서술에 반영 |
| `passive_ofdm_dl_survey.md` §4-2 | «C 의 sim2real 축 = White·Rojhani·Kearney & Gurbuz·Gurbuz 계열» 점유 지도 | ⭐**Kearney & Gurbuz·Rojhani 의 DOI 를 이번에 1차로 확보** (§1-3, §1-4) |
| `passive_ofdm_dl_survey.md` §5-1 C4 | Gérard = **GoogLeNet**(«AlexNet» 은 옛 기록 오류) | 로컬 PDF 재직독으로 재확인 + 결과 수치 표 (§4-3) |
| `rotor_randomness_survey.md:128·166·187` | White TRS·RadarConf22·Moore 서지, **모터속도 샘플링 충실도** 심층(Fixed-Speeds→Sub-CPI **+2.2 pp 정확도·+5.8 pp 드론 재현율**, Table V) | 재조사 안 함. Moore 전문은 그때도 지금도 못 열었다(§6) |
| `noise_modeling_survey.md:286-287` | Raval·Malarvanan 의 **SNR 주입 관행**(표본당 A_r² 기준) | 본 조사는 같은 두 편을 «시뮬 전용 학습» 축으로 재분류 (§2) |
| `sionna_sensing_survey.md` | Sionna 계열 센싱 논문 누적 | ⭐**Li ICCT 2025(Sionna RT 마이크로도플러)는 그 파일에 없던 신규 발굴** (§3-1) |

**본 조사 라운드의 순증**: ① Li ICCT 2025(신규) ② Costa **저널판** JSTEAP 확정 서지
③ Kearney & Gurbuz·Rojhani DOI ④ Kim GRSL·Rahman IET·Huizing·Zhang Mamba 서지 확정
⑤ Gérard 결과표 원문 수치.

---

## 1. sim-to-real 직결 축 — 합성으로 학습해 실측에 적용

### 1-1. 버밍엄 계보 (⭐우리 프로젝트와 가장 가까운 축)

**White, Jahangir, Baker, Antoniou, "Urban Bird-Drone Classification With Synthetic
Micro-Doppler Spectrograms", IEEE Trans. Radar Systems, vol. 2, pp. 167–179, 2024**
(early access 2023-10-20), DOI [10.1109/TRS.2023.3326317](https://doi.org/10.1109/TRS.2023.3326317).

- **무엇**: 새 vs 드론 2클래스. 합성 마이크로도플러 스펙트로그램 데이터셋 4종을 만들어
  각각으로 CNN 을 학습시키고 **전부 실측 L밴드 응시레이더 데이터로 시험**.
- **딥러닝(정확한 이름)**: **AlexNet, ImageNet 사전학습, conv 층 동결, FC 층만 재학습**.
- **도메인 갭 처리 2개**: ① **모터속도 샘플링 충실도** — 4종 데이터셋은 모터속도를 어떻게
  뽑느냐만 다르다(상수 → 실기 로그 Sub-CPI 시계열). 충실도 최하→최상에서 +2.2 pp 정확도,
  드론 재현율 +5.8 pp. ② **합성 표적을 실측 레이더 배경 시계열에 더한다**(클러터·잡음은
  실측 그대로).
- **결과**: 최고 충실도 합성 학습 **86.6±0.5%** ↔ 실측 학습 **89.7±0.5%** — 갭 **−3.1 pp**.
- ⛔주의(기존 정정 승계): 드론 클래스 중 큰 2종(Inspire·Matrice)만 합성이고 새·Mini 는
  실측 유지 — «순수 합성 학습» 이라고 인용하면 과장이다.

**앞선 회의판 — White 외, "Multi-rotor Drone Micro-Doppler Simulation Incorporating Genuine
Motor Speeds and Validation with L-band Staring Radar", IEEE RadarConf22, 2022**,
DOI [10.1109/RadarConf2248738.2022.9764352](https://doi.org/10.1109/RadarConf2248738.2022.9764352).
멀티로터 시계열 반환의 단순 모델 3종을 세우고 **실기 드론 모터속도 기록**으로 파라미터를
채워 합성 스펙트로그램을 생성, 진폭변조의 결함은 현상학적으로 보정, 합성 표적을 실측 배경에
주입해 실측 스펙트로그램과 직접 비교(분류까지는 안 감 — 분류는 TRS 2024 판).

### 1-2. 세인트앤드루스 — 시뮬 충실도 쪽 기둥

**Moore, Robertson, Rahman, "A new simulation methodology for generating accurate drone
micro-Doppler with experimental validation", IET Radar, Sonar & Navigation 18(3):477–492,
2024** (CC-BY), DOI [10.1049/rsn2.12494](https://doi.org/10.1049/rsn2.12494).

- 드론 부품의 **정밀 3D 모델**(레이저스캔 포함)을 포인트클라우드로 바꿔 마이크로도플러를
  합성. **전용 제작한 검증 레이더**로 프로펠러 모양이 다른 3기종을 실측해 시뮬과 상세 비교,
  «very good agreement». CAD 정밀도에 매우 민감하고 **레이저스캔 모델이 최상**.
- 분류기는 학습하지 않았다 — «학습용 대량 합성 데이터 생성 가능성» 으로 남김.
- ⚠전문은 CC-BY 인데도 Wiley 402 로 이번에도 못 열었다(초록 + S2 API 까지;
  `rotor_randomness_survey.md:421` 과 같은 상태).

### 1-3. 앨라배마 CI4R — «시뮬은 데이터가 아니라 사전(prior)» 처방

**Kearney, Gurbuz, "Physics-Guided Deep Neural Networks for Radar-Based UAV Recognition in
Different Environments With No Prior In Situ Data", IEEE Trans. Aerospace and Electronic
Systems 62:9875–9891, 2026**, DOI [10.1109/TAES.2026.3685229](https://doi.org/10.1109/TAES.2026.3685229)
— `passive_ofdm_dl_survey.md` §3-1 이 원문 정독([원문] 표기), DOI 는 이번 라운드 확보.

- 79 GHz FMCW 실측 5기체. **CAD 시뮬만으로 학습한 U-Net 시맨틱 분할 마스크**(HERM 라인
  구조)를 GAN 판별기와 분류기 앞단에 넣는다. ⭐**«저충실도 시뮬 단독 학습은 random guessing
  을 못 넘었다»**(§V-A) — sim-to-real 의 하한 경고. SS-CAE 로 Real→Low SINR 전이
  **50.0→71.2%** (+21.2 pp).
- 학회판: "Semantic Segmentation Guided RF Micro-Doppler Synthesis and UAV Classification
  in Low SINR", IEEE RadarConf 2025
  ([IEEE 11031708](https://ieeexplore.ieee.org/document/11031708)).

### 1-4. 피렌체 — 모델기반 증강

**Rojhani, Passafiume, SadeghiBakhi, Collodi, Cidronali, "Model-Based Data Augmentation
Applied to Deep Learning Networks for Classification of Micro-Doppler Signatures Using FMCW
Radar", IEEE Trans. Microwave Theory and Techniques 71(5):2222–2236, 2023**,
DOI [10.1109/TMTT.2023.3231371](https://doi.org/10.1109/TMTT.2023.3231371)
— `passive_ofdm_dl_survey.md` §3-1 이 원문 정독, DOI 는 이번 라운드 확보.

- 77 GHz FMCW, ⛔입력은 스펙트로그램이 아니라 **레인지 프로파일 400점**. 합성 32,000 으로
  맞춤 CNN 학습, **실측 136장으로 시험**: 모델기반 합성 **78.68%** ↔ 관행 증강(회전·이동)
  **66.18%**. ⛔σ_P 를 시험셋으로 튜닝한 결함(따라하면 안 됨)도 기존 기록 그대로.

---

## 2. 시뮬 전용 학습 — 실측 검증이 없는 축 (정확도는 상한으로만)

| 논문 | 시뮬 방법 | 딥러닝(정확한 이름) | 입력 | 결과 | 실측? |
|---|---|---|---|---|---|
| **Raval, Hunter, Hudson, Damini, Balaji**, *Drones* 5(4):149, 2021, DOI [10.3390/drones5040149](https://doi.org/10.3390/drones5040149) | **Martin–Mulgrew** 회전블레이드 반환 모델, 블레이드 길이·회전수 변주, X/W밴드 | 맞춤 CNN(이름 없는 소형 CNN) | long-window **STFT 스펙트로그램** | **F1 0.816±0.011**(X밴드 PRF 2 kHz, 학습 SNR 10 dB) | ⛔없음(초록·본문 모두 시뮬) |
| **Malarvanan**, arXiv:[2403.02080](https://arxiv.org/abs/2403.02080), 2024 | Martin–Mulgrew 복소 시계열 | **CNN vs 하이브리드 양자 NN(HQNN)** | 시계열 | 고 SNR 에선 CNN 우세, 저 SNR 에선 HQNN 우세 | ⛔없음 |
| **Zhang, Song 외**, *Drones* 10(4):265, 2026, DOI [10.3390/drones10040265](https://doi.org/10.3390/drones10040265) | L/K **이중대역 레이더 탐지 모델** 수립(운동학) | ⭐**Mamba 상태공간 백본** + 패치블록 직렬화 + late fusion | 이중대역 마이크로도플러 스펙트로그램 | UAV vs 새 **97.5%** | ⚠«experimental testing» 이라 쓰나 실측/시뮬 구분이 초록에서 안 갈림(전문 403) |
| (참조) **AirGuard**, arXiv:2603.13112 | 운동학 모델 3600 × SNR 11단 | 이중분기 CNN 0.15 M | cmD + HRRP | 99.37% | ⛔없음 — `passive_ofdm_dl_survey.md:322` 원문 정독분, 재조사 안 함 |

공통 함정: **시뮬 안에서 낸 99% 급 정확도는 도메인 갭을 안 지난 수** — White 의 −3.1 pp,
Kearney 의 «random guessing» 하한, AirGuard 의 미학습 기체 4.49% 붕괴
(`passive_ofdm_dl_survey.md` §4-4 R2)와 같은 줄에 놓고 읽어야 한다.

---

## 3. 레이트레이싱 / ISAC 모델링 축 — 분류 직전에서 멈춘 논문들

### 3-1. ⭐Sionna RT 로 마이크로도플러를 뽑은 첫 사례 (이번 조사 신규 발굴)

**Li, Mu, Jiang, Feng, Gao, Xu (상하이대), "Micro-Doppler Signature Simulation of Multirotor
UAVs Using Ray Tracing", IEEE ICCT 2025**,
DOI [10.1109/ICCT67417.2025.11374154](https://doi.org/10.1109/ICCT67417.2025.11374154).

- **Sionna RT** 로 시나리오를 구성하고 **CSI 에서 로터 유도 마이크로도플러**를 뽑는다
  (6G ISAC 맥락). 반송파가 높아질수록 스펙트럼이 넓어지고 에너지가 분산됨을 보임.
- ⛔초록 기준 **CNN 분류도, 실측 검증도 없다**. 전문은 IEEE 유료라 못 열었다(§6).
- 우리 기록과의 관계: Sionna stock 은 회전 프로펠러를 객체당 강체 1벡터 한계로 못 돌린다
  ([[sionna-rt-doppler-velocity]]). **이들이 무엇으로 로터 회전을 흉내냈는지가 전문 확인
  1순위 질문**이다.

### 3-2. 바이스태틱 OFDM — 학습을 «후속 과제»로 비워 둔 자리

**Costa, Myint, Andrich, Giehl, Engelhardt, Schneider, Thomä (TU Ilmenau), "Modeling
Micro-Doppler Signature of Multi-Propeller Drones in Distributed ISAC", IEEE J. Selected
Topics in Electromagnetics, Antennas and Propagation 1(1):208–222, 2025**,
DOI [10.1109/JSTEAP.2025.3604407](https://doi.org/10.1109/JSTEAP.2025.3604407),
arXiv:[2504.05168](https://arxiv.org/abs/2504.05168).

- thin-wire 블레이드 모델을 **바이스태틱 + OFDM-like 신호**로 확장, 멀티프로펠러와 기체
  정적 반사(2가지 생성 방식)까지 포함. **실측 GT 로 검증** — «측정과 매우 유사한
  마이크로도플러». 동기를 **«ML 학습에 필요한 대량 데이터셋 생성»** 이라고 명시하되
  **학습·분류는 하지 않았다**. 회의판 전신: RadarConf 2024, arXiv:[2401.14287](https://arxiv.org/abs/2401.14287).
- `passive_ofdm_dl_survey.md` §4-5 의 «Costa 팀은 학습을 세 판에 걸쳐 후속과제로 비워
  뒀다» 가 저널판에서도 유지됨을 이번에 확인 — **바이스태틱 OFDM mD + 학습 분류의 칸은
  여전히 비어 있다.**

---

## 4. 실측 딥러닝 기준선 — 아키텍처 이름을 정확히

### 4-1. Kim, Kang, Park (KAIST), "Drone Classification Using Convolutional Neural Networks
With Merged Doppler Images", IEEE GRSL 14(1):38–42, 2017 (온라인 2016),
DOI [10.1109/LGRS.2016.2624820](https://doi.org/10.1109/LGRS.2016.2624820)

- Ku밴드 FMCW. ⭐**마이크로도플러 스펙트럼 + CVD 를 한 장으로 병합**한 입력을
  **GoogLeNet** 에 전이학습. 무향실 89.3% → 병합 이미지로 **94.7%**, 야외(고도 50–100 m,
  2기종)에선 100%. 무향실→야외 전이는 **통제환경→필드 도메인 갭**의 초기 사례
  (우리 챔버=통제군/야외=실증 구도와 같은 모양).
- ⚠전문 미열람([2차]) — 수치는 OpenAlex 초록 재구성 + `passive_ofdm_dl_survey.md:333` 교차.

### 4-2. Rahman, Robertson (세인트앤드루스), "Classification of drones and birds using
convolutional neural networks applied to radar micro-Doppler spectrogram images",
IET Radar, Sonar & Navigation 14(5):653–661, 2020,
DOI [10.1049/iet-rsn.2019.0493](https://doi.org/10.1049/iet-rsn.2019.0493)

- **GoogLeNet 기반**(전이학습), RGB·그레이스케일 스펙트로그램. 4클래스(드론·새·클러터·
  잡음) 검증 99.6%/시험 **94.4%**, 2클래스 99.3%/98.3%. 실측(자체 레이더; 같은 그룹의
  K/W밴드 Sci. Rep. 2018 데이터 계열).

### 4-3. Gérard, Tomasik, Morisseau, Rimmel, Vieillard (ONERA/CentraleSupélec),
"Micro-Doppler Signal Representation for Drone Classification by Deep Learning",
EUSIPCO 2020, pp.1561–1565, DOI [10.23919/Eusipco47968.2020.9287525](https://doi.org/10.23919/Eusipco47968.2020.9287525)
— ⭐로컬 PDF 직독 (`pdfs/eusipco2020_1561__gerard_microdoppler-representation-drone-dl.pdf`)

- S밴드 펄스(3 GHz, PRF 10 kHz), 실측 캠페인 5기종(1.5 km±250 m), 학습 36,730/시험 4,670
  청크. **GoogLeNet** 하나를 고정하고 **입력 표현 5종을 통제 비교**:

| 표현 | 기준 [%] | 잡음 추가 [%] | 짧은 관측 [%] |
|---|---|---|---|
| x(t) 시계열 | 75.8 | 72.6 | 67.1 |
| ⭐**WSP**(장구간 스펙트럼) | **98.1** | **92.7** | 93.7 |
| CP(켑스트럼) | 97.4 | 80.9 | **94.0** |
| SG(STFT 스펙트로그램) | 92.6 | 73.4 | 87.3 |
| CVD | 94.5 | 79.2 | — |

- 교훈 둘: ① **저 SNR 에서 WSP 가 차순위보다 10 pp 이상 우세** — 스펙트로그램이 늘 정답이
  아니다. ② ⭐⭐**train/test 를 날짜로 안 가르면 98~100% 로 부푼다**(«day separation» 강권,
  §IV) — 우리 leave-one-aspect-out 분할 논거의 1차 출처.

### 4-4. Huizing, Heiligers, Dekker, de Wit, Cifola, Harmanny (TNO), "Deep Learning for
Classification of Mini-UAVs Using Micro-Doppler Spectrograms in Cognitive Radar",
IEEE Aerospace and Electronic Systems Magazine 34(11):46–56, 2019,
DOI [10.1109/MAES.2019.2933972](https://doi.org/10.1109/MAES.2019.2933972)

- 미니 UAV 분류에 **CNN·RNN 계열**을 비교한 인지레이더 논문(피인용 103, 이 분야 표준
  인용처). ⚠**전문 미확보** — 훈련 데이터의 시뮬/실측 구성, 정확한 망 이름(예: LSTM 여부),
  «95% @0.2 s 창» 이라는 2차 요약 수치를 원문으로 확정하지 못했다(§6).

---

## 5. 도메인 갭 처리법 총정리 + 우리에게 주는 것

| 갈래 | 처방 | 근거(원문 확인 수치) | 우리 대응물 |
|---|---|---|---|
| (a) 시뮬 충실도 | 실기 모터속도 로그 주입 | White: Fixed-Speeds→Sub-CPI **+2.2 pp/재현율 +5.8 pp** | ⭐이미 있음 — 실측 로터 산포 0.07~0.29 반영([[measured-over-plausible]]) |
| (a′) 시뮬 충실도 | 레이저스캔급 CAD | Moore: «CAD 정밀도에 매우 민감» | ⚠주의 — 0803 프레임 전환으로 메쉬 미세정밀화는 중단, **필요 충실도의 하한**을 분류 성능으로 재야 함 |
| (b) 배경 합성 | 합성 표적 + **실측 배경** | White: 갭 −3.1 pp 달성의 절반 | 실측 라운드(X410) 배경 녹취를 합성에 재사용하는 경로 |
| (c) 물리 사전 | 시뮬→분할 마스크→분류기 앞단 | Kearney: Real→Low **+21.2 pp**; 시뮬 단독은 random guessing | σ 커널을 데이터 증배가 아니라 **특징 사전**으로 쓰는 보험 경로 |
| (d) 모델기반 증강 | 관행 증강 대신 물리 모델 변주 | Rojhani: **78.68 vs 66.18%** | 로터 rpm·앙각·자세 변주는 물리 모델로만 |

**기준선 문장**: 우리 시뮬 학습→실측 시험의 목표선은 **White 의 −3.1 pp**(반합성)이고,
경고선은 **Kearney 의 «저충실도 단독 = random guessing»** 이다. 반증 대비 표는
`passive_ofdm_dl_survey.md` §4-4(R1~R3)가 정본.

---

## 6. 못 찾았다 / 확인 못 했다 — 정직하게

1. **드론 마이크로도플러 전용 GAN 증강 논문** — 못 특정했다. GAN 증강은 전부
   **인간 활동** 계열만 확인됨(DCGAN: *Sensors* 19(21):4674, DOI
   [10.3390/s19214674](https://doi.org/10.3390/s19214674); ACGAN: Erol 외
   arXiv:[2001.08582](https://arxiv.org/abs/2001.08582); PFGAN: SPIE 13274, DOI
   [10.1117/12.3038540](https://doi.org/10.1117/12.3038540)). 검색 요약이 «MOCAP+도메인
   판별기 84.02%» 를 드론에 붙였으나 원문 특정에 실패해 **채택하지 않았다**.
2. **명시적 adversarial 도메인 적응(DANN/CORAL 류)을 드론 mD sim→real 에 쓴 게재 논문** —
   이번 범위에서 못 찾았다. 가장 가까운 것은 Kearney & Gurbuz 의 GAN 판별기+분할 사전(§1-3).
3. **Huizing 2019 의 훈련 데이터 구성**(시뮬/실측 비율, 정확한 망 이름) — IEEE 유료 +
   academia.edu 로그인벽으로 전문을 못 열었다. 2차 요약(실험 트라이얼 쿼드/헥사, 95%@0.2 s)
   은 **원문 미확정** 상태로만 §4-4 에 남겼다.
4. **MDPI 원문 403** — Raval 2021·Zhang 2026 은 초록+2차까지. 특히 첫 검색 요약에 나온
   «야외 데이터에 적용했다» 는 문장은 Raval 초록에 없어 **시뮬 전용으로 기재**했다.
5. **Moore IET RSN 2024 전문** — CC-BY 인데도 Wiley 402. `rotor_randomness_survey.md:421`
   때와 동일. 초록·S2 API 수준까지만.
6. **Li ICCT 2025 전문** — IEEE 유료. Sionna RT 에서 로터 회전을 어떻게 구현했는지
   (stock 한계 우회 여부)가 미해결 질문.

---

## 참고문헌 (1차 자료)

- D. White, M. Jahangir, C. J. Baker, M. Antoniou, "Urban Bird-Drone Classification With
  Synthetic Micro-Doppler Spectrograms," *IEEE Trans. Radar Systems*, vol. 2, pp. 167–179,
  2024. doi:10.1109/TRS.2023.3326317
- D. White, M. Jahangir, M. Antoniou, C. Baker, J. Thiyagalingam, S. Harman, C. Bennett,
  "Multi-rotor Drone Micro-Doppler Simulation Incorporating Genuine Motor Speeds and
  Validation with L-band Staring Radar," *IEEE RadarConf22*, 2022.
  doi:10.1109/RadarConf2248738.2022.9764352
- M. Moore, D. A. Robertson, S. Rahman, "A new simulation methodology for generating
  accurate drone micro-Doppler with experimental validation," *IET Radar Sonar Navig.*
  18(3):477–492, 2024. doi:10.1049/rsn2.12494
- S. Kearney, S. Z. Gurbuz, "Physics-Guided Deep Neural Networks for Radar-Based UAV
  Recognition in Different Environments With No Prior In Situ Data," *IEEE Trans. Aerosp.
  Electron. Syst.* 62:9875–9891, 2026. doi:10.1109/TAES.2026.3685229
- N. Rojhani, M. Passafiume, M. SadeghiBakhi, G. Collodi, A. Cidronali, "Model-Based Data
  Augmentation Applied to Deep Learning Networks for Classification of Micro-Doppler
  Signatures Using FMCW Radar," *IEEE Trans. Microw. Theory Techn.* 71(5):2222–2236, 2023.
  doi:10.1109/TMTT.2023.3231371
- D. Raval, E. Hunter, S. Hudson, A. Damini, B. Balaji, "Convolutional Neural Networks for
  Classification of Drones Using Radars," *Drones* 5(4):149, 2021. doi:10.3390/drones5040149
- A. S. Malarvanan, "Hybrid Quantum Neural Network Advantage for Radar-Based Drone Detection
  and Classification in Low SNR," arXiv:2403.02080, 2024.
- T. Zhang, X. Song 외, "A Classification Algorithm of UAV and Bird Target Based on L/K
  Dual-Band Micro-Doppler and Mamba," *Drones* 10(4):265, 2026. doi:10.3390/drones10040265
- C. Li, S. Mu, J. Jiang, L. Feng, Y. Gao, S. Xu, "Micro-Doppler Signature Simulation of
  Multirotor UAVs Using Ray Tracing," *IEEE ICCT*, 2025. doi:10.1109/ICCT67417.2025.11374154
- H. C. A. Costa, S. J. Myint, C. Andrich, S. W. Giehl, M. Engelhardt, C. Schneider,
  R. S. Thomä, "Modeling Micro-Doppler Signature of Multi-Propeller Drones in Distributed
  ISAC," *IEEE JSTEAP* 1(1):208–222, 2025. doi:10.1109/JSTEAP.2025.3604407 (arXiv:2504.05168;
  회의판 arXiv:2401.14287)
- B. K. Kim, H.-S. Kang, S.-O. Park, "Drone Classification Using Convolutional Neural
  Networks With Merged Doppler Images," *IEEE Geosci. Remote Sens. Lett.* 14(1):38–42, 2017.
  doi:10.1109/LGRS.2016.2624820
- S. Rahman, D. A. Robertson, "Classification of drones and birds using convolutional neural
  networks applied to radar micro-Doppler spectrogram images," *IET Radar Sonar Navig.*
  14(5):653–661, 2020. doi:10.1049/iet-rsn.2019.0493
- J. Gérard, J. Tomasik, C. Morisseau, A. Rimmel, G. Vieillard, "Micro-Doppler Signal
  Representation for Drone Classification by Deep Learning," *EUSIPCO 2020*, pp. 1561–1565.
  doi:10.23919/Eusipco47968.2020.9287525 (로컬: `pdfs/eusipco2020_1561__gerard_*.pdf`)
- A. Huizing, M. Heiligers, B. Dekker, J. J. M. de Wit, L. Cifola, R. Harmanny, "Deep
  Learning for Classification of Mini-UAVs Using Micro-Doppler Spectrograms in Cognitive
  Radar," *IEEE Aerosp. Electron. Syst. Mag.* 34(11):46–56, 2019. doi:10.1109/MAES.2019.2933972
