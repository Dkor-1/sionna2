# 드론 마이크로도플러 분류 — 딥러닝 기법 이름 정밀 조사 (2026-08-15)

> **조사 범위 — 답할 질문 둘**
> - **Q1** 패시브/통신 조명원(DVB-T·LTE·5G·WiFi) 레이다로 드론을 **분류**한 논문 — 쓰인 분류
>   기법(딥러닝이면 **아키텍처의 정확한 이름**).
> - **Q2** 레이다 드론 분류 **서베이/리뷰 논문(2021~2026)** — 그 서베이가 정리한 **기법 분류 체계**.
>
> 방법: 웹검색 → 1차 자료(arXiv PDF 직접 다운로드 + `fitz` 본문 직독, Crossref DOI 검증)로 확인 →
> 기존 조사 `prior_work/passive_ofdm_dl_survey.md`(2026-08-11)와 대조. GPU 사용 없음.
> 이번에 새로 받아 둔 PDF (전부 `prior_work/pdfs/`):
> `comst2025_khawaja_uav_dct_survey.pdf`(arXiv:2402.05909v2) ·
> `ijcip2024_semenyuk_uav_detection_survey.pdf`(arXiv:2409.05985) ·
> `arxiv2604.02680_bai_isac_uav_survey.pdf` · `jsac2026_airguard_luo.pdf`(arXiv:2603.13112) ·
> `arxiv2307.10326_drone_radar_atr_intro.pdf`.
>
> ⚠ **읽음 등급 표기** — `[원문]` PDF 본문 직독 / `[초록]` 초록·Crossref 메타데이터 축자 확인 /
> `[2차]` 다른 논문(주로 서베이)의 서술만 봄. `[2차]` 수치는 우리 표에 그대로 옮기면 안 된다.
> ⛔ 이 조사는 «그런 논문이 없다»를 결론으로 쓰지 않는다 — 쓸 수 있는 문장은
> **«이번 조사 범위에서 못 찾았다»** 뿐이다.

---

## TL;DR — 다섯 줄

1. **Q1 패시브 갈래의 답은 0811 조사와 같다** — 패시브 조명원 실측에서 «학습형 분류기+혼동행렬»까지
   간 게재 논문은 **Cao 외(DTMB, Appl. Sci. 2025) 하나**이고 그것도 **딥러닝이 아니다**(biased-RCS
   특징벡터 + NBV 유사도 인식기, ACRR 85.16%). **패시브 에코 + 딥러닝** 게재 사례는 이번
   재조사(0815)에서도 **못 찾았다.** 나머지 패시브 분류(Vorobev DVB-T2 2019 등)는 로터 회전수
   도플러 시그니처의 **정성 구분**이다.
2. **통신 파형 실측 에코 + 딥러닝은 모노스태틱 ISAC 갈래에 있다** — ⭐**DC-Former**(Xue 외, ICCCS
   2025: depth convolution + **Transformer** 멀티헤드 자기어텐션, 5G NR 3.5 GHz·100 MHz 실측+시뮬,
   STFT 스펙트로그램 클래스당 10,000장, 96~98%)가 실측 5G 에코 딥러닝 분류의 유일 확인 사례.
   그 옆에 **AirGuard**(이중분기 특징융합 CNN 0.15M, cmD+HRRP, 시뮬만, >98%)와
   **PinpuNet**(ICC 2025: 비균질 2D conv + residual, FMCW 공개 데이터셋 6기종, 97.17/99.50%).
3. **능동 레이다 마이크로도플러 딥러닝의 이름 목록**(전부 1차 확인): GoogLeNet 전이학습(Gérard
   EUSIPCO 2020 · Rahman & Robertson IET RSN 2020), ResNet-SP=ResNet-18 경량화(Park Sensors 2021),
   CNN(Raval Drones 2021, Martin-Mulgrew 합성), AlexNet conv 동결 전이(White TRS 2024), VGG16/19
   전이(IEEE 2025), 경량 CNN+coordinate attention(Electronics 2025), **Mamba**(Drones 2026) —
   백본이 CNN → Transformer → Mamba 로 번지고 있으나 입력은 한결같이 **STFT 스펙트로그램(+CVD)**.
4. **서베이 기법 분류 체계 회수(2021~2026)** — ① Khawaja COMST 2025: 분류 특징 = **RCS vs
   마이크로도플러** 2축 + Table X 알고리즘 총람(SVM·Naive Bayes·최근접이웃·신경망·CNN·스펙트로그램
   패턴 분석·총오류율 최소화), 패시브(§V-D)와 드론 자체 RF(§VI)를 명시 분리. ② Semenyuk IJCIP
   2024: 레이다 인식 = **6기술 결합**(RCS 분석/ML·DL/mD 분석/통계 인식/스펙트로그램/다중주파수).
   ③ Tang Drones 2025: 패시브 한정, **조명원별** 정리. ④ Bai arXiv 2026(미게재): ISAC 식별 =
   **신호처리 vs 학습기반 vs 합성데이터 생성** 3분. ⑤ Hanif IEEE Sensors J 2022는 초록만
   확인(본문 유료·프리프린트 차단) — 체계 미회수.
5. **서베이 체계에서도 우리 빈 자리가 확인된다** — 어느 서베이도 «패시브 조명원 열»과 «딥러닝 분류
   열»이 만나는 칸에 게재 논문을 채우지 못한다(COMST Table X 전부 능동, Tang 은 분류 정확도 인용
   0건, Bai 학습기반 3편 전부 모노스태틱 ISAC/FMCW). 0811 조사의 «A+B+C 동시 점유 없음» 결론이
   서베이 횡단으로 재확인된다.

---

## 0. 기존 기록과의 관계 (먼저 확인함)

`prior_work/passive_ofdm_dl_survey.md`(2026-08-11)가 Q1 의 «패시브+분류» 6편과 딥러닝 프레임워크
표(§3-1)를 이미 가진다. **이번 조사가 새로 보태는 것만** 적는다.

| 새로 확정한 것 | 내용 |
|---|---|
| DC-Former 의 1차 정보원 특정 | 0811 기록은 `[2차]` 출처 불명이었다. 이번에 **Bai 서베이(arXiv:2604.02680) §IV-C·ref [92]** 가 원출처임을 PDF 직독으로 특정: J. Xue, Q. Zhang, D. Ma, J. Wei, ICCCS 2025, pp.927–932. 아키텍처·데이터·정확도 서술 축자 회수(아래 §2). 여전히 `[2차]` — IEEE 원문은 못 열었다 |
| **PinpuNet** (신규) | Y. Luo, Q. Zhu, R. Guan, IEEE ICC 2025, pp.6007–6012 — 0811 조사에 없던 ISAC 학습 분류 편 |
| 서베이 3편 신규 | Semenyuk IJCIP 2024(arXiv:2409.05985) `[원문]` · Hanif IEEE Sensors J 22(4) 2022 `[초록]` · Gong arXiv:2307.10326(드론 레이다 ATR 개관) `[원문]` |
| 능동 DL 이름 4건 신규 | Rahman & Robertson(IET RSN 2020, GoogLeNet — Crossref 초록 확인) · Zhang & Song **Mamba**(Drones 10(4):265, 2026) · Zhang 외 경량 CNN+coordinate attention(Electronics 14(24):4831, 2025) · VGG16/19 전이(IEEE doc 11101447, 2025) |
| Teo ICCCS 2021 (신규, 인접) | 5G+WiFi 조명원 + **KNN** — 단 태스크가 검출·측위라 Q1 본표에서 제외(§1-3) |

겹침 주의: Gérard EUSIPCO 2020 로컬 PDF(`pdfs/eusipco2020_1561__gerard_*.pdf`)를 재확인했다 —
망은 **GoogLeNet**(§IV-B "obtained with GoogLeNet [20]")이 맞다. 0811 정정 유지.

---

## 1. Q1 — 패시브/통신 조명원으로 드론 «분류»

### 1-1. 표 — 분류까지 간 것(기법 이름 붙여서)

| # | 논문 | 조명원 | 분류 기법(정확한 이름) | 데이터 | 성적 | 읽음 |
|---|---|---|---|---|---|---|
| P1 | Vorobev·Veremyev·Tulenkov, *Experimental DVB-T2 Passive Radar Signatures of Small UAVs*, SPSympo 2019, pp.67–70, doi:10.1109/SPS.2019.8881955 | DVB-T2 (660 MHz) | ⛔딥러닝 아님 — **로터 회전수 도플러 시그니처의 정성 구분**(분류기 없음) | 실측 4기체(Phantom 3·F450·Geoscan 401·고정익), 750~900 m | 정확도 수치 없음. «기종 간 구별 특징 존재, 단 플라스틱 블레이드 최소형 제외» | `[초록]`+`[2차]`(Demissie §1) |
| P2 | Jarabo-Amores 외, *Drone detection feasibility with passive radars*, EuRAD 2018 | DVB-T | ⛔딥러닝 아님 — 회전 블레이드 도플러 특성 관찰 | 실측 (흑연 중형 UAV vs 플라스틱) | 흑연 기체는 «detected and classified», 플라스틱은 검출만 | `[2차]`(Tang §5) |
| P3 | **Cao 외**, *A Novel Recognition-Before-Tracking Method Based on a Beam Constraint in Passive Radars for Low-Altitude Target Surveillance*, Appl. Sci. 15(18):9957, 2025, doi:10.3390/app15189957 | **DTMB** (7.56 MHz) | ⛔딥러닝 아님 — **biased-RCS 특징벡터(길이 20) + 정규화 바이스태틱 속도(NBV) 유사도 매칭** 인식기 | 실측(우한대 멀티스태틱, A320·SR20)+합성(Phantom 4) 3클래스 | **ACRR 85.16%**(Phantom 4 행 100% 는 합성), 시뮬 >89% | **`[원문—0811]`** |
| P4 | Kulpa·Malanowski·Bączyk, *Passive Radar for Drone Detection and Classification*, IRS 2025, doi:10.23919/IRS64527.2025.11046011 | 미상 | **미상**(초록: 프로펠러 마이크로도플러를 분류 특징으로) | 실측 예제 | 수치 없음 | `[초록]` |
| P5 | Clemente 외, *GNSS Based PBR for Micro-Doppler Based Classification of Helicopters*, IEEE Int. Radar Conf. 2015 | GPS L1 C/A | ⛔딥러닝 아님 — 로터 RPS 추정 대조(표적이 **헬기**, 드론 아님) | 실측 헬기 2기종 | RPS 일치로 식별 | `[원문—0811]` |

⭐ **결론(0815 재확인).** 패시브 조명원 실측 위에 «학습된 분류기 + 혼동행렬»을 올린 게재 논문은
**Cao 하나**, 그마저 특징이 마이크로도플러가 아니라 RCS 크기이고 **딥러닝은 0편**이다. 이번
재조사에서도 반례를 못 찾았다(§5).

### 1-2. Cao 가 인쇄한 반대 근거 (다시 새김)

Cao §4: 라디오/TV 대역에서는 드론 RCS 가 입사·산란각에 거의 안 변해 **드론끼리(intra-class) 구분이
어렵고, 이 방법은 기종 구분을 노린 것이 아니다.** — 우리 5기종 분류가 넘어야 할 문장. 우리 답
(대역 1.8~5.2 GHz + 특징이 RCS 아닌 마이크로도플러)은 0811 조사 §4-4 R1 그대로.

### 1-3. 인접 — 통신 조명원 + 고전 ML(분류 아님)

Teo·Seow·Wen, *5G Radar and Wi-Fi Based Machine Learning on Drone Detection and Localization*,
IEEE ICCCS 2021, pp.875–880, doi:10.1109/ICCCS52626.2021.9449224 `[2차]`(Semenyuk ref [13]) —
5G 주파수 바이스태틱 반사 NLOS + RSSI 를 **KNN** 에 넣어 드론 **존재 검출과 2×2 m 격자 측위**.
기종 분류가 아니라 Q1 본표에서 뺐다. «통신 조명원 + ML» 조합의 가장 이른 사례라 기록만 한다.

---

## 2. 통신 파형(5G/ISAC) 실측·시뮬 에코 + 딥러닝 — 이름 셋

패시브 바이스태틱은 아니고 **모노스태틱/자체 테스트베드 ISAC** 갈래다. 그러나 «OFDM 통신 파형
에코 위의 딥러닝 분류»라는 점에서 우리와 가장 가까운 이웃이고, 기법 이름이 정확히 남아 있다.
셋 다 1차 정보원은 **Bai 서베이(arXiv:2604.02680) §IV-C** 직독 `[원문]`(개별 논문은 `[2차]`).

| # | 논문 | 아키텍처(축자) | 입력 | 데이터 | 성적 |
|---|---|---|---|---|---|
| C1 | **Xue·Zhang·Ma·Wei**, *DC-Former Network Empowered UAV and Bird Recognition Based on Integrated Sensing and Communication System*, ICCCS 2025, pp.927–932 | **DC-Former** — "integrates **depth convolution** for local spatial feature extraction and **Transformer with multi-head self-attention** for global dependency modeling" | STFT 시간-주파수 스펙트로그램(3D 이미지) | ⭐**5G NR 3.5 GHz·100 MHz 실측+시뮬**, UAV/새 2클래스 × 10,000장 | **96~98%**, "outperforms conventional CNN-based models" |
| C2 | **Luo·Chu·Zhang·Zhao·Lin·Gao**, *AirGuard: UAV and Bird Recognition Scheme for ISAC System*, IEEE JSAC(Bai ref [91] 표기)·arXiv:2603.13112. 학회판: Chu 외, IEEE/CIC ICCC 2025, pp.1–6 | **이중분기(dual-branch) 특징융합 CNN** — 분기당 conv3×3 3층+maxpool → concat → FC, **0.15 M 파라미터** (0811 원문 직독) | **cmD 스펙트럼 + HRRP** 이미지 각 3@256×256 | ⛔시뮬만 — 3D 메시 기반 합성 237,600장 | cmD+HRRP **>98%**(0811 직독: 99.37%) |
| C3 | **Luo·Zhu·Guan**, *PinpuNet: Towards ISAC-based Drone Monitoring by Learning Micro-Doppler Spectrum*, IEEE ICC 2025, pp.6007–6012 | **PinpuNet** — "**inhomogeneous 2D convolutions**"(시간축·주파수축 상관을 따로 잡음) + **residual layers** | STFT 마이크로도플러 스펙트로그램 | 공개 데이터셋 **LSS-FMCWR-1.0**(Journal of Radars 13(3), 2023 — ⚠FMCW 능동 실측) 6기종: Mavic 2·Phantom·Inspire 2·M350·M600·고정익 | K밴드 4클래스 **97.17%** · L밴드 5클래스 **99.50%**, 스미어링 하에서도 >91% |

참고(분류기 없음, 같은 갈래의 인프라): Ma 외 MICCIS 2024, pp.173–179(5G TDD 프레임별 로터 파라미터
추정 MSE) · Wei 외 IEEE TWC 24(12) 2025(rmD-NSP + SET 로 로터 마이크로도플러 «추출», 실측 —
분류기는 없음) · Costa 외 IEEE J-STEAP/RadarConf(바이스태틱 OFDM 마이크로도플러 **합성 생성기**,
"enabling large-scale synthetic data generation for UAV classification" — sim2real 고리는 아직
안 닫음).

⇒ **읽는 법.** 실측 5G 에코 딥러닝 분류는 DC-Former 한 편뿐이고 그것도 **모노스태틱·2클래스
(UAV vs 새)** 다. 기종 분류(intra-drone)로 가면 통신 파형 갈래 전체에 게재 사례가 없다.

---

## 3. 능동 레이다 마이크로도플러 딥러닝 — 이름 대조표 (참조군)

우리 분류기 후보 선정용. 전부 1차 확인(로컬 PDF·Crossref·0811 원문 직독).

| 논문 | 아키텍처(정확한 이름) | 입력 | 데이터 | 성적 | 확인 경로 |
|---|---|---|---|---|---|
| Gérard·Tomasik·Morisseau·Rimmel·Vieillard, *Micro-Doppler Signal Representation for Drone Classification by Deep Learning*, EUSIPCO 2020, pp.1561–1565 (공개 PDF: eurasip.org/Proceedings/Eusipco/Eusipco2020/pdfs/0001561.pdf — 링크 생존 확인 0815) | **GoogLeNet**(전이) — 표현 5종 비교(x(t)·WSP·CP·SG·CVD) | STFT 계열 5표현 | S밴드 능동 펄스, 실측 5클래스, 학습 36,730 청크, ⭐날짜 분리 | 청정 WSP 98.1 / 잡음 92.7% | **`[원문]`** 로컬 PDF |
| Rahman & Robertson, *Classification of drones and birds using CNNs applied to radar micro-Doppler spectrogram images*, IET RSN 14(5), 2020, doi:10.1049/iet-rsn.2019.0493 | **GoogLeNet**(RGB 스펙트로그램 전이학습) | 마이크로도플러 스펙트로그램(+CVD) | K밴드 94 GHz/24 GHz CW 실측, 드론 vs 새 | (본문 미확인) | `[초록]` Crossref |
| Park·Lee·Park·Kwak, *Radar-Spectrogram-Based UAV Classification Using CNNs*, Sensors 21(1):210, 2021, doi:10.3390/s21010210 | **ResNet-SP**(ResNet-18 경량화 자체 설계) | STFT 스펙트로그램 | FMCW 실측, UAV 3종+사람활동 2 | **83.39%**(ResNet-18 은 79.88%) | `[초록]`+PMC |
| Raval·Hunter·Hudson·Damini·Balaji, *CNNs for Classification of Drones Using Radars*, Drones 5(4):149, 2021, doi:10.3390/drones5040149 | **CNN**(자체) | STFT 스펙트로그램 | ⛔합성만 — Martin & Mulgrew 블레이드 모델 | (0811 잡음조사에서 SNR 규약 원장으로 씀) | `[초록]`+0811 |
| White 외, IEEE TRS 2:167–179, 2024 | **AlexNet**(ImageNet 전이, ⭐conv 동결·FC만 학습) | RGB 스펙트로그램 20 timestep | L밴드 응시레이다 실측, 새 vs 드론 | 실측 89.7±0.5% | `[원문—0811]` |
| Kaushal(표기), *Radar-Based UAV Classification: A Micro-Doppler and Deep Learning Approach*, IEEE 학회 2025, ieeexplore 11101447 | **VGG16 / VGG19** 특징추출기 전이 DCNN | 마이크로도플러 시그니처 이미지 | CW X밴드 10 GHz, 4,849장·5표적 | **95% / 97%** | `[초록/검색요약]` ⚠저자명 미검증 |
| Zhang(Luyan)·Tu·Xu·Zhou, *A Lightweight CNN-Based Method for Micro-Doppler Feature-Based UAV Detection and Classification*, Electronics 14(24):4831, 2025, doi:10.3390/electronics14244831 | **경량 CNN + coordinate attention** | 레인지-도플러 맵 | FMCW 실측(드론·차량·보행자) | (본문 미확인) | `[초록]` Crossref |
| Zhang(T.)·Song(X.), *A Classification Algorithm of UAV and Bird Target Based on L/K Dual-Band Micro-Doppler and Mamba*, Drones 10(4):265, 2026, doi:10.3390/drones10040265 | ⭐**Mamba**(상태공간모델) 융합망 — L/K 이중대역 스펙트로그램 융합 | 이중대역 마이크로도플러 스펙트로그램 | 시뮬 모델 기반, UAV vs 새 | (본문 미확인) | `[초록]` Crossref |
| A-SPC(KAIST), arXiv:2009.14422 | **경량 CNN**(conv 3층+FC 1층, 0.217 M) | mD 이미지 128×128×3 | Ku FMCW 실측 5클래스 | 전처리 교체만으로 87.14→**97.14%** | `[원문—0811]` |

⇒ 0811 §3-2 의 결론(«무엇을 먹이느냐 ≫ 어떤 망이냐», 소형 CNN 이면 충분)은 신규 4건을 넣어도
안 흔들린다 — 새 이름들(Mamba·coordinate attention)은 전부 «백본 축» 위의 변주이고, 통제비교로
입력 축을 이긴 사례는 이번에도 못 찾았다.

---

## 4. Q2 — 서베이/리뷰(2021~2026)와 기법 분류 체계

### 4-1. 표

| # | 서베이 | 게재처·연도 | 범위 | 읽음 |
|---|---|---|---|---|
| S1 | Khawaja·Ezuma·Semkin·Erden·Ozdemir·Guvenc, *A Survey on Detection, Classification, and Tracking of UAVs using Radar and Communications Systems* | **IEEE COMST** 28:3272–3310, 2025 (게재판 제목 UAV→**AAV**, doi:10.1109/COMST.2025.3554613) · arXiv:2402.05909 | 레이다+통신 전 갈래 | **`[원문]`**(프리프린트 v2) |
| S2 | Semenyuk·Kurmashev·Lupidi·Alyoshin·Kurmasheva·Cantelli-Forti, *Advance and Refinement: The Evolution of UAV Detection and Classification Technologies* | **Int. J. Critical Infrastructure Protection**(투고판 PDF), 2024 · arXiv:2409.05985 | 레이다·RF·광학·음향+융합, 2020~ | **`[원문]`** |
| S3 | Tang·Ma·Qu·Mao, *UAV Detection with Passive Radar: Algorithms, Applications, and Challenges* | Drones 9(1):76, 2025, doi:10.3390/drones9010076 | **패시브 한정** | `[원문—0811]` |
| S4 | Hanif·Muaz·Hasan·Adeel, *Micro-Doppler Based Target Recognition With Radars: A Review* | **IEEE Sensors Journal** 22(4):2948–2961, 2022 (ieeexplore 9673798) | 마이크로도플러 인식 전반(드론 포함) | `[초록]` ⚠본문 미확보 |
| S5 | Bai·Li·Yin·Qu·Hsu·Liu·Chen, *MIMO OFDM-Enabled ISAC for Low-Altitude Non-Cooperative UAV Surveillance: A Survey* | ⚠**미게재 프리프린트** arXiv:2604.02680, 2026 | ISAC(통신파형) 한정 | **`[원문]`** |
| 참고 | Gong·Yan·Kong·Li, *Introduction to Drone Detection Radar with Emphasis on ATR technology* | ⚠arXiv:2307.10326, 2023(게재 미확인) | 드론 레이다 ATR 설계 관점 | **`[원문]`** |

(2021 이전 고전: Coluccia·Parisi·Fascista, *Detection and Classification of Multirotor Drones in
Radar Sensor Networks: A Review*, Sensors 20(15):4172, **2020** — 창 밖이라 표에서 뺌.)

### 4-2. 각 서베이의 기법 분류 체계 (회수한 것)

**S1 Khawaja COMST 2025 `[원문]`** — 체계가 셋으로 갈린다.
- **모달리티 축**: 능동 레이다(§V-A~C) / **패시브 = 통신신호 기회조명 에코**(§V-D, 조명원별:
  GSM·LTE·5G·WiFi·DAB·DVB-T·DVB-S) / **드론 자체 RF 방사 청취**(§VI) — 둘 다 'passive' 로 불리는
  것을 절 단위로 분리. 우리도 같은 분리를 써야 한다(0811 §1-1 과 합치).
- **분류 특징 축**(§V-C 본문): "The popular methods ... are based on **RCS and micro-Doppler
  signatures**" — RCS(수치·이미지) vs 마이크로도플러(스펙트로그램) 2분.
- **알고리즘 축**(Table X, p.17 — 논문×알고리즘 총람): 15종 고전 분류기 일괄비교(RCS, Ezuma 계열) ·
  최근접이웃(편파 특징) · **딥러닝/CNN**(스펙트로그램) · SVM·Naive Bayes(로터 직경, mD 특징) ·
  신경망(환경 이미지) · 스펙트로그램 패턴 분석 · 총오류율 최소화 분류. ⛔**Table X 의 전 행이 능동
  레이다다** — 패시브 행이 하나도 없다.
- 분류 성립 조건 3개도 명시(주파수·각도·편파 불변 특징 / 저잡음 / 충분한 특징 수)와 과제
  (새 vs 드론, 군집, 실시간 데이터량, 특징 선택).

**S2 Semenyuk IJCIP 2024 `[원문]`** — 레이다 절(§2.1)의 체계:
- 시스템 축: **주파수 대역**(L/S/C/X/Ka/W)과 **변조**(FMCW·LFPM·FSK·LFM·SFM)로 2분.
- **기술 축 — 6기술의 결합**으로 정리(축자 번역): ① RCS 분석 ② **머신러닝·딥러닝** ③ 마이크로도플러
  시그니처 분석 ④ 통계적 인식 ⑤ 레이다 스펙트로그램 활용 ⑥ 다중주파수 레이다.
- Table 1 성능표: RCS 통계인식 97.73%(SNR 10 dB) · GA-BP 신경망 80%(SNR 3 dB) · NeXtRAD
  멀티스태틱 92.5% · 스펙트로그램 딥러닝(ResNet-SP, [15]=Park 2021) · 하이브리드 DNN 의도분류
  98.97%([18]=Fraser ICECCME 2023) 등 — **개별 논문의 이름 있는 기법을 표로 회수 가능**.
- ⛔패시브 조명원 갈래가 **아예 없다**(`passive radar` 0회, `DVB` 0회) — 5G 는 Teo(ICCCS 2021,
  KNN) 한 편으로만 등장.

**S3 Tang Drones 2025 `[원문—0811]`** — 패시브 한정. 체계 = **조명원별**(FM·DAB·DVB-T/T2·DTMB·
GSM·LTE·5G·WiFi·위성) × 처리 단계별(기준신호 정제·클러터 제거·CAF·검출·추적). §5 가 실험 논문을
조명원별로 요약하고 분류 성공/실패를 **블레이드 재질**로 가른다(탄소섬유·흑연 ○ / 플라스틱 ×).
⛔분류 **정확도**를 인용한 행이 0 — 원 논문들이 그 수치를 안 냈기 때문일 가능성이 크다(0811 판단
유지).

**S4 Hanif IEEE Sensors J 2022 `[초록]`** — "마이크로도플러 기반 표적 분류 기법과 응용의 리뷰"
라는 것까지만 확인. **체계는 회수 못 했다**(§5).

**S5 Bai arXiv:2604.02680 (2026, 미게재) `[원문]`** — ISAC 한정. UAV 감시를
검출·추적(§IV-B)/식별(§IV-C)로 나누고, **식별 절 안에서** ① 신호처리(마이크로도플러 파라미터
추정 — Ma·Wei) ② **학습 기반**(PinpuNet·AirGuard CNN·DC-Former) ③ **합성데이터 생성**(Costa
생성기) 3분. Table VIII 이 논문×아키텍처×데이터×성적을 표로 준다 — §2 의 축자가 여기서 나왔다.

### 4-3. 서베이 횡단에서 보이는 것

- **패시브 열 × 딥러닝 분류 열이 만나는 칸이 비어 있다.** S1 은 패시브 절(§V-D)에 분류 알고리즘
  표가 없고 알고리즘 표(Table X)에 패시브 행이 없다. S3 은 패시브 전용인데 분류 정확도 인용이 0.
  S5 의 학습 3편은 전부 모노스태틱 ISAC/FMCW. S2 는 패시브 갈래 자체가 없다.
- 이것은 0811 조사 §4-3(«A·B·C 동시 점유 없음»)의 **독립 재확인**이다 — 이번엔 개별 논문 수색이
  아니라 서베이 5편의 분류 체계 쪽에서 같은 구멍이 보였다.

---

## 5. 못 찾았다 — 정직하게

- **패시브 조명원(방송·셀룰러·WiFi 불문) 실측 에코에 딥러닝 분류기를 올린 게재 논문** — 이번
  재조사(0815, 웹검색 7회 + 서베이 5편 직독)에서도 못 찾았다. 가장 가까운 것은 Cao(비딥러닝)와
  DC-Former(딥러닝이나 모노스태틱 ISAC).
- **Kulpa IRS 2025 의 본문** — IEEE 유료. 분류가 학습형인지 특징 관찰인지 여전히 미확인.
- **Hanif 리뷰의 본문** — IEEE 유료, TechRxiv 프리프린트는 Cloudflare 차단. 기법 분류 체계 미회수.
- **Xue DC-Former·PinpuNet 의 IEEE 원문** — 유료. 수치·아키텍처 서술은 전부 Bai 서베이 `[2차]`.
- **IEEE doc 11101447(VGG16/19) 의 저자·학회명** — IEEE 페이지가 렌더링되지 않았다. 검색 요약의
  «Devesh Kaushal» 표기는 미검증 — 인용할 때 문서번호로만 가리킬 것.
- **Jarabo-Amores EuRAD 2018 원문** — 여전히 `[2차]`(Tang §5 경유).
- 중문 저널(Journal of Radars 의 LSS-FMCWR-1.0 원문 포함)은 이번에도 못 열었다.

---

## 6. 우리에게 뜻하는 것 (짧게)

1. **분류기 선택**: 게재 지형은 GoogLeNet/AlexNet/VGG 전이 ↔ 0.15~0.25 M 소형 CNN 양극이고,
   통제비교가 있는 쪽은 소형 CNN 이 이긴다(0811 §3-3). 신상 백본(Transformer·Mamba)은 아직 통제된
   우위 증거가 없다 — **소형 스크래치 CNN 1급 유지**, DC-Former 류는 대조군 팔로만.
2. **빈 칸 주장**: «패시브 셀룰러 에코 + 딥러닝 기종 분류» 는 서베이 5편의 체계에도 없는 칸이다.
   ⛔단 «최초» 라 쓰지 않는다 — §5 의 미확보 목록(Kulpa 본문 등)이 남아 있는 한 «이번 조사 범위에서
   못 찾았다» 까지만.
3. **벤치마크 상대**: 통신 파형 갈래의 수치 기준선은 DC-Former 96~98%(2클래스·실측)와 AirGuard
   >98%(2클래스·시뮬) — 우리 다기종 폐집합과는 클래스 수·분할 규약이 달라 **나란히 놓으려면 그
   차이를 표에 병기해야 한다**(0811 §3-4 규칙).
