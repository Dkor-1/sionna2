# sionna2 레퍼런스 라이브러리 — ISAC 드론 디텍션 · Sionna 시뮬레이션 · 그 교집합

*생성 2026-07-31 · 빌더 `reflib_spine.py + build_reference_library.py` · 기계 원본 `outputs/reference_library.json` · BibTeX `docs/references.bib`*

**94편**을 기하(A/B/C/D/EMIT/E/SIM) 먼저, 그 다음 조명원 순으로 정렬했다. 그중 **64편은 PDF 원문을 열어 읽었고**(158개 인용문 보유), 25편은 서지만 확인했다. 게재 66 · 프리프린트 23 · 게재확정 1 · 게재처 미확인 2.

이 문서는 목록이 아니라 **논문을 쓰면서 여는 작업대**다. 각 카드는 PDF 를 다시 열지 않고도 인용 한 줄과 related-work 한 문장을 만들 수 있을 만큼을 담는다.

| 절 | 내용 |
|---|---|
| §1 | 분류 체계 — 기하 축, 조명원 축, 용어 함정 |
| §2 | ⭐ **마스터 표** — 기하 → 조명원 순 |
| §3 | Sionna 표 — 버전 · 용도 · 표적 산란을 계산했는가 |
| §4 | ⭐⭐ **교집합 표** — Sionna AND 드론, H8 4-프롱 채점 |
| §5 | 규약 원장 — 숫자를 나란히 놓기 전에 |
| §6 | ⭐ **관련연구 골격** — 문단별 논문과 초안 문장 |
| §7 | ⭐ **공백 진술** + novelty 가드 |
| §8 | 인용 금지 · 미해결 · 신뢰등급 |

## 0. 읽는 법

**등급.** 인용 가능 범위를 정한다.

| 등급 | 뜻 | 허용 |
|---|---|---|
| **P** | PDF 원문을 열어 읽었다(인용문 사용 가능). | 본문 문장 인용 가능 |
| **B** | 서지만 확인(dblp 또는 출판사 레코드). 본문 문장 인용 금지. | 서지 인용만 · 본문 문장 인용 금지 |
| **S** | 2차 출처 서지. 본문 미확보. | 서지 인용만 · 2차 출처임을 밝힐 것 |
| **U** | 확인 불가. 인용 금지. | 인용 금지 |

**적용한 오류 규칙.** 이 프로젝트가 실제로 저지른 오류에서 나온 규칙이다.

- **E1** — 논문에 없는 결과를 헤드라인으로 만들지 않는다 — 각 주장에 인용문 또는 소스 포인터를 붙였다.
- **E2** — 판본이 둘인 문헌은 별개 행으로 분리했다(Ziganshin 회의판/저널판, Taylor TAES/RADAR, Ji WCL/arXiv, Clutter-Aware 게재판/arXiv, Wei TWC/arXiv).
- **E3** — 규약(전폭/반폭, 심볼축/반복축, 거리합축/이등분선축)이 다르면 caution 에 적었다. 논문에 없는 식을 귀속하지 않는다.
- **E4** — 프리프린트는 status 와 BibTeX comment 양쪽에 PREPRINT 로 명시했다. 게재처가 확인 안 되면 UNVERIFIED 로 남겼다.
- **E6** — PDF 경로가 없는 수치는 기록하지 않았다. 경로는 전부 절대경로다.
- **invention** — 저자 full name 을 만들어내지 않았다. 이니셜만 검증된 곳은 이니셜을 그대로 두고, 절단된 곳은 'and others' 로 표시했다.

⚠ BibTeX 항목 94개 중 **32개가 INCOMPLETE** 로 표시돼 있다. 빠진 필드는 추측해 채우지 않았다. 투고 전에 그 항목들만 출판사 레코드로 채우면 된다.

## 1. 분류 체계

### 1.1 기하 축

| 코드 | 정의 | 편수 |
|---|---|---|
| **A** | A · 능동 모노스태틱 — 우리(또는 저자)가 송신하고 같은 자리에서 받는다. PRF 가 설계변수다 | 20 |
| **B** | B · 패시브 준-모노스태틱 — 남이 송신하고 RX 가 조명원 옆에 붙는다 (beta ~ 0) | 3 |
| **C** | C · 패시브 바이스태틱 — 남이 송신하고 RX 는 멀리 있다 (beta 큼) | 30 |
| **D** | D · 멀티스태틱 / 망-협조형 바이스태틱 — 조명원이나 수신기가 여럿, 또는 조명원이 자기 사업자망 | 6 |
| **EMIT** | EMIT · 방출 기반 — 표적 자신이 방사원이다 (우리 기하 축 밖) | 4 |
| **E** | E · RCS · 산란엔진 앵커 — 검출이 아니라 산란량 자체를 재거나 계산한다 | 16 |
| **SIM** | SIM · 시뮬레이션 플랫폼 · 데이터셋 · 도구 | 15 |

우리 3분류(A/B/C)에 문헌이 강제한 두 부류를 더했다 — D 멀티스태틱·망협조형, E RCS·산란엔진 앵커. 그리고 A/B/C 어디에도 안 들어가는 EMIT(방출 기반)를 별도로 뒀다.

### 1.2 조명원 축

정렬 순서: `WiFi` · `LTE` · `5G NR` · `5G NR (업링크 SRS)` · `5G-A` · `cellular (미분류)` · `DVB-T + WiFi` · `LoRa` · `802.11ad` · `다중 대역 통신 파일럿` · `기회 조명원 일반` · `OFDM/ISAC 파형 (자기송신)` · `mmWave FMCW (자기송신)` · `CW/FMCW 레이더 (자기송신)` · `없음 (RCS 실측)` · `없음 (수치 EM)` · `없음 (도구·데이터셋)`

### 1.3 ⭐ 두 축은 독립이다

> ⭐ '조명원 통제권' 과 '기하' 는 별개 축이다. 우리 C 는 비통제+바이스태틱이고, FWA cooperative sensing 은 통제+바이스태틱이다. 격자 각주에 이 분리를 명시하면 격자를 지킬 수 있다.

**격자에 없는 칸 (D).** D: 네트워크-네이티브 바이스태틱(cooperative bistatic) - 조명원이 '남'이 아니라 자기 사업자망이고, 송신기와 수신기가 물리적으로 떨어져 있으며, 파형은 통제 가능하지만 기하는 바이스태틱.

우리 2x3 격자(기하 2 x 조명원 3)에 이 칸이 없으면, 심사자가 'FWA/셀룰러 협조형 바이스태틱은 왜 뺐나' 라고 물었을 때 답이 없다. 격자 설명 각주 한 줄로 '조명원 통제권'과 '기하'를 분리된 축으로 명시할 것. 우리 C 는 '조명원 비통제 + 기하 바이스태틱'이고, X03 은 '조명원 통제 + 기하 바이스태틱'이다. 두 축을 분리해 적으면 격자는 그대로 두고 서술만 정밀해진다.

### 1.4 ⚠ 용어 함정

**`passive` 는 이 코퍼스에서 세 가지 뜻으로 쓰인다.**

- (1) 조명원이 남의 것 — Maksymiuk·Taylor·Colone·Martelli
- (2) 표적이 비협조 — mmHawkeye 등 ACM/IEEE 시스템 계열
- (3) 우리가 송신하지 않고 표적 방사를 듣는다 — DroneScale·Matthan

**`ambiguity` 는 여섯 가지 다른 현상을 가리킨다.** 문자열 검색으로 표를 채우면 E3 가 재발한다.

| 논문 | 그 논문에서 'ambiguity' 가 뜻하는 것 |
|---|---|
| `diseglio2024ietrsn` | 직접파 우세 가정이 깨져 위상 동기가 오염된 결과 |
| `openisac2026` | 반송파 주파수 오프셋(CFO) 추정의 무모호 구간 |
| `huang2026uplink` | 클러터와 표적을 구분할 수 없음 |
| `filippini2023 / colone2023taes` | 진폭만 쓰므로 속도 **부호**를 잃음 |
| `diseglio2022irs / yuan2025eucap` | 거리(지연) 모호 |
| `taylor2023radar / ai2021piers` | AF 사이드로브 구조 |

## 2. ⭐ 마스터 표

### 2.0 우리 2×3 격자의 채움 현황

| 칸 | 이 라이브러리가 가진 것 |
|---|---|
| **A x WiFi** | 없음 (Barneto 는 LTE/NR) |
| **A x LTE** | Barneto TMTT 2019(자기간섭 실측), Wang 5G-A GBS 가 1.99-5.04 GHz 를 걸침 |
| **A x 5G** | ⭐ 포화 - LaSen(SenSys'26), Saur(Nokia, FR2 실측), Wang(5G-A GBS 실측) |
| **B x WiFi** | Martelli 2017 (준-모노스태틱 명시), Di Seglio 2024(B 대 C 비교) |
| **B x LTE** | Demissie 2024 (LTE450) |
| **B x 5G** | ⭐ 공백 - 이 라이브러리에 사례 없음 |
| **C x WiFi** | Rzewuski 2021(+FDTD mono/bi RCS), Milani 2021, Colone/Filippini/Di Seglio 계열 |
| **C x LTE** | Dan 2019, Geng 2020, Taylor 2023/2025, Sun 2022/2025, Demissie 2024, Ji 2026 |
| **C x 5G** | Ai 2021, Maksymiuk 2022/2023/2025, Jopanya 2025, Lin 2023, Huang 2026(업링크) |

### 2.0.1 문헌 전체를 관통하는 다섯 공백

- 1) 표적 산란을 스스로 계산하고 그 위에 검출을 세운 드론 논문이 없다. Sionna 계열은 표적을 큐보이드·정육면체·단순화 메시로 놓고 산란은 스톡에 맡기거나(Clutter-Aware, CellSense, 2605.07623) 상용 솔버로 나간다(LAMBDA). RCS 를 실제로 찍은 유일한 Sionna 게재 논문은 표적이 차량이다(Ziganshin, EuCAP 2025).
- 2) 패시브 드론 코퍼스에서 무모호 속도를 자기 시스템에 대해 계산한 논문은 Geng(2020) 하나뿐이고, 그것도 시뮬레이션이며 규약이 전폭이다. Jopanya(2025)는 식을 쓰지만 축이 버스트 내부 심볼이다.
- 3) CFAR 오경보율은 거의 전부 설계값(nominal)으로만 보고된다. 실제 달성치를 잰 것은 He(2512.24889) 뿐이며 그마저 표적이 드론이 아니다.
- 4) 드론 RCS 실측은 대부분 15 GHz 이상이다(Semkin 26-40, Ezuma 15/25, Zhang 10-36, Azim 25-28). 우리 대역(1.8-5.2 GHz)을 직접 덮는 것은 Das(1.8-27 GHz) 와 Costa(5.78-8.22 GHz 반사도) 정도다.
- 5) config B(패시브 준-모노스태틱)의 순수 사례가 여전히 드물다. 명시적 근거가 있는 것은 Martelli(2017) 와 Demissie(2024) 둘뿐이고, 후자는 그 용어를 쓰지 않는다.

### 2.A — A · 능동 모노스태틱 — 우리(또는 저자)가 송신하고 같은 자리에서 받는다. PRF 가 설계변수다  *(20편)*

| 인용키 | 논문 | 게재처 · 상태 | 연 | 조명원 | 표적 표현 | 엔진/실측 | 무엇을 검증했나 | 우리와의 관계 | 등급 |
|---|---|---|---|---|---|---|---|---|---|
| `barneto_fullduplex_tmtt19` ⭐⭐ | Full-Duplex OFDM Radar with LTE and 5G NR Waveforms: Challenges, Solutions, a… | IEEE Trans. Microw. Theory Techn.<br>*PUBLISHED* | 2019 | LTE | 정지 상태 공중 드론 · 미확인 · 실물 | 실측 | 자기간섭 억제 예산 ↔ 실측 격리도 | A 열의 물리적 통행료(자기간섭)를 숫자로 주는 앵커. | B |
| `lasen_sensys26` ⭐⭐⭐ | LaSen: Low-Altitude Drone Sensing with 5G-NR Signals | Proc. 24th ACM Conf. Embedded Networked Senso…<br>*PUBLISHED* | 2026 | 5G NR | 실물 드론 · DJI Matrice 4E 외 1종 · 실물 비행, RTK 지상진리 | 실측(USRP 송수신) + 2D-OMP 희소복원 | 거리/속도 추정오차 ↔ RTK GNSS 지상진리 | A x 5G. 우리 격자의 A 열 5G 칸을 이미 채운 최근접 선행. | P |
| `saur_uav_isac_arxiv26` ⭐⭐ | Reliable UAV Detection with ISAC | arXiv 2605.23561<br>*PREPRINT* | 2026 | 5G NR | 실물 드론 · DJI Air 3 (프로펠러 펼친 대각 56 cm) · 실물 비행, GNSS 지상진리 | 실측 PoC (도심 계곡 지형, 강한 클러터). ECA-C 클러터 제거 + CA-CFAR. | 검출 위치 정확도와 최대 검출거리 ↔ GNSS 기준궤적 + 링크버짓 이론값 | A x 5G, 실측. 우리 시뮬 A 열의 현실 대조군. | P |
| `golzadeh_sib1_ssb_vtc23` ⭐⭐ | Downlink Sensing in 5G-Advanced and 6G: SIB1-Assisted SSB Approach | Proc. IEEE 97th Vehicular Technology Conf. (V…<br>*PUBLISHED* | 2023 | 5G NR | — | — | — | ⭐ 모노스태틱도 SSB 반복률 문제에서 자유롭지 않다는 직접 증거. 우리 G1(SSB 최악) 서사의 네트워크측 대응물. | B |
| `khosroshahi_prs_pdsch_globecom24` ⭐⭐ | Leveraging PRS and PDSCH for Integrated Sensing and Communication | Proc. IEEE Global Communications Conf. (GLOBE…<br>*PUBLISHED* | 2024 | 5G NR | — | — | — | 우리 G3(PRS 최고) 모드의 표준측 대응물. PRS comb 이 만드는 유령표적을 명시한다 — 우리 바닥유령과는 다른 종류이므로 구분해 인용. | P |
| `liu_nr_mono_positioning_isacom23` | 5G NR Monostatic Positioning with Array Impairments: Data-and-Model-Driven Ap… | Proc. 3rd ACM MobiCom Workshop on Integrated …<br>*PUBLISHED* | 2023 | 5G NR | — | — | — | LaSen 이 '모노스태틱 = gNB 에 수신 체인 하나 더' 라고 말할 때 다는 근거 [32]. 그 아키텍처 주장의 출처. | S |
| `gao_batstation_arxiv25` | BatStation: Toward In-Situ Radar Sensing on 5G Base Stations | arXiv<br>*PREPRINT* | 2025 | 5G NR | — | — | — | 주변부. '기지국을 센서로 쓴다' 는 아키텍처 근거로만. | P |
| `wang_gbs_lawn_arxiv26` ⭐⭐ | Clutter-Resilient ISAC for Low-Altitude Wireless Networks: A 5G Base Station-… | arXiv 2603.14351<br>*PREPRINT* | 2026 | 5G-A | 실물 드론 · DJI Mavic 3 · 실물 비행, 온보드 궤적 기준 | 야외 실측(outfield) + 링크버짓 계산 | 추적 궤적 ↔ UAV 온보드 시스템이 준 기준 궤적 | A x 5G, 실측. '통신 자원을 얼마나 뺏기는가'를 숫자로 준 유일 사례(1.2%). | P |
| `li_mdrt_icct25` ⭐⭐⭐ | Micro-Doppler Signature Simulation of Multirotor UAVs Using Ray Tracing | Proc. IEEE 25th Int. Conf. Communication Tech…<br>*PUBLISHED* | 2025 | OFDM/ISAC 파형 (자기송신) | 회전 프로펠러 1개 · Sionna 내장 reflector -> 1/2/3/6 점산란체 -> Blender 블레이드 … | Sionna RT 개조 - 광선 발사기를 구면 샘플링에서 원뿔 샘플링으로 교체 | 스펙트로그램 능선 위치 ↔ 해석적 마이크로도플러 예측(정성 비교) | 우리가 엔진에 손댄 일의 가장 가까운 기술적 선례. 다만 바꾼 것은 샘플러뿐이고 EM 은 스톡이다. | P |
| `wei_rotor_md_twc25` ⭐⭐⭐ | UAV's Rotor Micro-Doppler Feature Extraction Using Integrated Sensing and Com… | IEEE Trans. Wireless Commun.<br>*PUBLISHED* | 2025 | OFDM/ISAC 파형 (자기송신) | — | — | — | 우리 마이크로도플러 대조의 실측 앵커 계열(flash-rate 규약 확인에 이미 사용). | P |
| `xu_ckm_clam_arxiv25` | CKM-Enabled Joint Spatial-Doppler Domain Clutter Suppression for Low-Altitude… | arXiv 2512.09560<br>*PREPRINT* | 2025 | OFDM/ISAC 파형 (자기송신) | 저고도 소형 UAV · 시뮬레이션 표적(점 산란체 수준) | 시뮬레이션만. 사이트별 클러터각 지도(CLAM)를 사전 구축해 공간-도플러 2단 제거. | 파라미터 추정 정확도 ↔ 시뮬레이션 기준값 | A. 우리 '느린 표적은 도플러로 안 갈린다' 서사의 시뮬 선행. | P |
| `keskin_mono_isac_twc25` | Fundamental Trade-Offs in Monostatic ISAC: A Holistic Investigation Towards 6G | IEEE Trans. Wireless Commun.<br>*PUBLISHED* | 2025 | OFDM/ISAC 파형 (자기송신) | — | — | — | LaSen 식 데이터심볼 재활용의 이론적 대가. 우리 축과 직교하므로 보완으로 인용. | B |
| `mmhawkeye_secon23` | mmHawkeye: Passive UAV Detection with a COTS mmWave Radar | Proc. IEEE Int. Conf. Sensing, Communication,…<br>*PUBLISHED* | 2023 | mmWave FMCW (자기송신) | 실물 UAV · 본문 미확인(이번 라운드 미추출) · 실물 비행 | 실측 + LSTM 식별기, 주기적 미소운동(PMM) 특징 | 검출 정확도·거리 ↔ 실험 조건별 성능 평가 | A. 우리 격자에는 직접 안 들어가지만, 'passive' 라는 낱말의 뜻이 갈리는 대표 사례라 분류 근거로 인용한다. | P |
| `he_cots_mmwave_tosn24` | Detection and Identification of Non-Cooperative UAV Using a COTS mmWave Radar | ACM Trans. Sensor Netw.<br>*PUBLISHED* | 2024 | mmWave FMCW (자기송신) | — | — | — | A07 의 확장판. | S |
| `sun_doppler_resolution_taes19` ⭐⭐ | Improving the Doppler Resolution of Ground-Based Surveillance Radar for Drone… | IEEE Trans. Aerosp. Electron. Syst.<br>*PUBLISHED* | 2019 | CW/FMCW 레이더 (자기송신) | — | — | — | ⭐ 도플러 분해능이 드론 검출의 병목이라는 명제의 능동레이더측 선례. 우리 report11(저속·분해능)의 대조군. | B |
| `han_drone_dataset_scidata26` | A Time-Synchronized Multi-Sensor Drone Dataset Acquired from Multiple Radars … | Sci. Data<br>*PUBLISHED* | 2026 | CW/FMCW 레이더 (자기송신) | 상용 드론 4종 + 비-드론 표적 1종 · 본문 미추출 · 실물 | 실측 데이터셋. 2-30 m 를 2 m 간격으로, 통제 조건 반복 측정. | 데이터셋 일관성 ↔ 반복 시행 | A. 우리 실측 계획(측정 2종)의 참조 데이터셋 형식. | P |
| `vovchuk_carryon_arxiv25` | Drone Carry-on Weight and Wind Flow Assessment via Micro-Doppler Analysis | arXiv 2510.22846<br>*PREPRINT* | 2025 | CW/FMCW 레이더 (자기송신) | 호버링 쿼드콥터 · 본문 미추출 · 실물, 통제 풍동/야외 실험 | 실측 + 비행제어기 물리 설명 | 적재중량과 바람이 마이크로도플러에 남기는 서명 분리 ↔ 통제 실험 세트 | 우리 관절형 드론·로터별 개성 모델의 물리적 근거(로터별 회전수가 자세에 따라 갈린다). | P |
| `yazici_mimo_cw_taes24` | Detection and Localization of Drones in MIMO CW Radar | IEEE Trans. Aerosp. Electron. Syst.<br>*PUBLISHED* | 2024 | CW/FMCW 레이더 (자기송신) | — | — | — | 전용 MIMO CW 레이더 베이스라인 — 통신신호 재활용의 대가를 재는 기준선. | B |
| `zhang_fmcw_clutter_taes26` | Robust FMCW Radar Clutter Suppression for UAV Detection via Learning | IEEE Trans. Aerosp. Electron. Syst.<br>*PUBLISHED* | 2026 | CW/FMCW 레이더 (자기송신) | — | — | — | 클러터 억제 대조군(능동). 우리 ECA/MTI 노치 대가 계상과 나란히. | B |
| `kearney_physguided_taes26` | Physics-Guided Deep Neural Networks for Radar-Based UAV Recognition | IEEE Trans. Aerosp. Electron. Syst.<br>*PUBLISHED* | 2026 | CW/FMCW 레이더 (자기송신) | — | — | — | '물리 유도' 프레이밍의 최신 사례 — 우리 SBR+PO 물리모델 서사와 나란히 인용 가능. | B |

<details><summary><b>▸ 상세 카드 13편</b> — 서지 · 수치 · 인용문 · 초안 문장</summary>

#### `barneto_fullduplex_tmtt19` ⭐⭐ — Full-Duplex OFDM Radar with LTE and 5G NR Waveforms: Challenges, Solutions, and Measurements

- **서지** — C. Baquero Barneto and T. Riihonen and M. Turunen and L. Anttila and M. Fleischer and K. Stadius and J. Ryynänen and M. Valkama. *IEEE Trans. Microw. Theory Techn.*, 2019
- **상태** — PUBLISHED — IEEE TMTT 67(10); 프리프린트 arXiv:1908.03418  ·  **등급** — B  ·  ⚠ **BibTeX INCOMPLETE**
- **PDF** — 디스크에 없음
- **조명원 / 기준신호** — source=자기 자신(전이중) · reference_signal=LTE/5G NR 파형 · band=2.44 GHz · bandwidth_MHz=40
- **표적 표현** — 정지 상태 공중 드론 · 미확인 · 실물
- **엔진 / 실측** — 실측
- **무엇을 무엇에 대해 검증했나** — 자기간섭 억제 예산 ↔ 실측 격리도
- **핵심 수치** — `tx_above_thermal_noise_dB` = 140, `required_SI_suppression_dB` = 100, `measured_isolation_dB` = 100, `carrier_GHz` = 2.44, `bandwidth_MHz` = 40, `drone_range_m` = 40, `total_SI_suppression_required_dB` = 100, `circulator_plus_active_RF_dB` = 75
- **우리와의 관계** — A 열의 물리적 통행료(자기간섭)를 숫자로 주는 앵커.
- ⚠ ⚠ grade B - PDF 가 디스크에 없다. 위 두 인용문은 이전 라운드 기록(outputs/monostatic_prior.json)에서 온 것이며 이번에 원문 재확인을 하지 않았다. 논문 문장으로 인용하기 전에 원문을 열 것.
- ⚠ ⚠ 두 번째 인용은 우리에게 불리하다 — 이동표적은 SI 에 강하다고 저자들이 직접 말한다. 100 dB 를 드론 검출의 관문처럼 쓰면 과장. 출처 기록: outputs/monostatic_prior.json
  > “since the eNB/gNB transmit power can be even more than 140 dB larger than the receiver thermal noise floor, facilitating sufficient TX-RX isolation as a whole is technically very challenging, particularly in the monostatic shared-antenna OFDM radar case” — *본문(이전 라운드 인용, 원문 재확인 안 함)*
  > “from the OFDM radar processing perspective, limited TX-RX isolation is primarily a concern in detection of static targets while moving targets are inherently more robust to transmitter self-interference” — *본문(이전 라운드 인용)*
- **초안 문장** — 모노스태틱 ISAC 는 송신전력이 수신 잡음바닥보다 140 dB 이상 크다는 구조적 부담을 안고 100 dB 급 자기간섭 억제를 요구하지만(Baquero Barneto 외, IEEE TMTT 2019), 같은 논문은 이동 표적이 자기간섭에 본질적으로 강하다는 점도 함께 적는다.

#### `lasen_sensys26` ⭐⭐⭐ — LaSen: Low-Altitude Drone Sensing with 5G-NR Signals

- **서지** — Qian Yang and Yongtao Dai and Mingrui Li and Qianyi Huang and Xu Chen and Jin Zhang and Guochao Song and Qian Zhang and Xiaofeng Tao. *Proc. 24th ACM Conf. Embedded Networked Sensor Systems (SenSys '26)*, 2026. DOI `10.1145/3774906.3800504`
- **상태** — PUBLISHED — ACM/IEEE SenSys '26 camera-ready, CC BY 4.0  ·  **등급** — P
- **PDF** — `/data/public/jeong/papers/5G/26_LaSen.pdf`
- **조명원 / 기준신호** — source=자기 자신 (NI USRP-2954R 이 MATLAB 5G Toolbox 파형을 송신). 상용 gNB 가 아니다. · reference_signal=⭐ 전 파형 - CSI-RS/SSB/DM-RS 기준 RE 와 PDSCH 데이터 RE 를 하나의 비균일 슬로타임 행렬로 합친다 · band=5.8 GHz 비면허 (3.5 GHz N41 gNB 를 모사) · scs_kHz=30 · bandwidth_MHz=78.12
- **표적 표현** — 실물 드론 · DJI Matrice 4E 외 1종 · 실물 비행, RTK 지상진리
- **엔진 / 실측** — 실측(USRP 송수신) + 2D-OMP 희소복원
- **무엇을 무엇에 대해 검증했나** — 거리/속도 추정오차 ↔ RTK GNSS 지상진리
- **핵심 수치** — `csirs_measured_repetition_Hz` = 200, `csirs_max_configurable_Hz` = 500, `ssb_repetition_Hz` = 50, `lte_crs_Hz` = 1000, `baseline_unambiguous_velocity_m_s` = 2.6, `lasen_unambiguous_velocity_m_s` = 20.2, `range_rmse_m` = 2.2, `velocity_rmse_m_s` = 1.3, `detection_range_m` = 108, `carrier_GHz` = 5.8, `bandwidth_MHz` = 78.12, `scs_kHz` = 30, `csirs_measured_Hz` = 200, `ssb_Hz` = 50, `baseline_unambig_v_ms` = 2.6, `lasen_top_bin_ms` = 20.2, `range_rmse_m_top_bin` = 2.2, `velocity_rmse_ms_top_bin` = 1.3
- **우리와의 관계** — A x 5G. 우리 격자의 A 열 5G 칸을 이미 채운 최근접 선행.
- ⚠ LaSen 은 우리 법칙을 반증하지 않는다. 균일 표본화를 포기하는 방식으로 우회한다.
- ⚠ PDSCH 재활용은 패시브 바이스태틱에 이전 불가(메모: sionna2-lasen-monostatic).
- ⚠ LaSen 이 인용하는 Chen 외(Appl. Sci. 14(10):4282, 2024)는 원문 미확보 - 인용 시 'LaSen 이 그렇게 요약한다'로 표기(E4/E6).
- ⚠ 본문 내부 불일치: 구현부는 NI USRP-2954R, 8절은 USRP X310. 하드웨어 인용 시 둘 다 명시. 20.2 m/s 는 무모호 상한이 아니라 기체(DJI Matrice 4E, 최고 21 m/s)가 정한 실험 상한이다.
  > “A practical ISAC implementation involves configuring the gNB with an additional receive chain to capture reflections of its own transmitted signals [32], similar to a monostatic radar.” — *sec.2.2.1 p.733*
  > “The maximum configurable repetition frequency for Sub-6 GHz Channel State Information Reference Signals (CSI-RS) is 500 Hz [3], falling short of the Nyquist sampling requirements for resolving high-speed targets like drones.” — *본문*
  > “At the same 5.8 GHz frequency setting, the method based on CSI-RS estimation has an unambiguous velocity range of up to 2.6 m/s, while LaSen extends this range to 20.2 m/s.” — *본문*
- **초안 문장** — 능동 모노스태틱 배치에서는 gNB 가 자기 송신 파형 전체를 알고 있으므로 데이터 심볼까지 슬로타임 표본으로 끌어와 무모호 속도를 2.6 m/s 에서 20.2 m/s 로 넓힐 수 있으나(Yang 외, SenSys 2026), 이 우회는 송신기를 소유한 배치에서만 가능하며 조명원을 소유하지 않는 패시브 배치에는 이전되지 않는다.

#### `saur_uav_isac_arxiv26` ⭐⭐ — Reliable UAV Detection with ISAC

- **서지** — S. Saur and M. Doll and A. Grudnitsky and S. Mandelli and L. Giroto and M. Henninger and T. Wild. *arXiv 2605.23561*, 2026. arXiv:`2605.23561`
- **상태** — PREPRINT — PDF 안에 게재처 표기 없음  ·  **등급** — P
- **PDF** — `/data/public/sionna_jeong/papers_isac_sionna/new_0731/2605.23561__reliable-uav-detection-with-isac.pdf`
- **조명원 / 기준신호** — source=자기 자신 - 개조하지 않은 상용 5G 하드웨어(gNB RU, 옥상 설치, 지상 27 m) · reference_signal=전 다운링크 자원(TDD 프레임의 DL 심볼 전부를 센싱에 사용) · band=27.6 GHz (FR2) · scs_kHz=120 · bandwidth_MHz=200 · frame=10 ms 무선프레임당 DL 832 / UL 288 OFDM 심볼
- **표적 표현** — 실물 드론 · DJI Air 3 (프로펠러 펼친 대각 56 cm) · 실물 비행, GNSS 지상진리
- **엔진 / 실측** — 실측 PoC (도심 계곡 지형, 강한 클러터). ECA-C 클러터 제거 + CA-CFAR.
- **무엇을 무엇에 대해 검증했나** — 검출 위치 정확도와 최대 검출거리 ↔ GNSS 기준궤적 + 링크버짓 이론값
- **핵심 수치** — `carrier_GHz` = 27.6, `bandwidth_MHz` = 200, `assumed_target_rcs_dBsm` = -17, `range_error_p50_m_exp1` = 0.09, `range_error_p95_m_exp1` = 0.3, `range_error_p50_m_exp2` = 0.23, `range_error_p95_m_exp2` = 0.73, `max_demonstrated_range_m` = 500, `link_budget_limit_m` = 540, `cp_range_limit_m` = 89, `cfar_pfa_raised_from` = 1e-06, `cfar_pfa_raised_to` = 0.0001
- **우리와의 관계** — A x 5G, 실측. 우리 시뮬 A 열의 현실 대조군.
- ⚠ ⚠ PREPRINT. 게재된 것처럼 인용하지 말 것.
- ⚠ ⭐ ECA 가 느린 표적을 함께 죽인다는 문장은 우리 hover-blind 서사의 외부 근거지만, 우리 챔버 ECA 서사와 배치가 다르다(도심 옥상).
- ⚠ RCS -17 dBsm 은 26-40 GHz 측정에서 온 값이다. 우리 1.8-5.2 GHz 대역에 그대로 쓰면 안 된다.
  > “Based on the comparison of different UAV types [12], we have assessed its mean RCS as sigma = -17 dBsm.” — *p.3*
  > “In addition, in order to further improve detection rates for the long distance, the false alarm rate of the CA-CFAR detector was increased from 10^-6 to 10^-4.” — *p.4*
  > “The drawback of ECA-C is that the desired target is suppressed as well while moving slowly, causing missed detections around re[versal points]” — *p.4*
- **초안 문장** — 개조하지 않은 상용 5G FR2 하드웨어로 도심에서 UAV 를 검출한 PoC 가 보고되어 있다(Saur 외, Nokia Bell Labs, 2026).

#### `golzadeh_sib1_ssb_vtc23` ⭐⭐ — Downlink Sensing in 5G-Advanced and 6G: SIB1-Assisted SSB Approach

- **서지** — M. Golzadeh and E. Tiirola and L. Anttila and J. Talvitie and K. Hooli and O. Tervo and I. Peruga and S. Hakola and M. Valkama. *Proc. IEEE 97th Vehicular Technology Conf. (VTC2023-Spring)*, 2023. DOI `10.1109/VTC2023-Spring57618.2023.10200933`
- **상태** — PUBLISHED — IEEE VTC2023-Spring  ·  **등급** — B
- **PDF** — 디스크에 없음
- **핵심 수치** — `psl_suppression_dB` = 25, `resolution_improvement_pct_range` = [120, 190], `carriers_GHz` = [3.5, 28]
- **우리와의 관계** — ⭐ 모노스태틱도 SSB 반복률 문제에서 자유롭지 않다는 직접 증거. 우리 G1(SSB 최악) 서사의 네트워크측 대응물.
- ⚠ 본문 미독(리포지터리 PDF 는 anti-bot). 초록 외 문장 인용 금지.
  > “In general, the synchronization signal block (SSB) is a suitable candidate for always-on downlink sensing, due to its frequent periodical availability and because of its beam-sweeping nature. However, as this work demonstrates, using only the SSB has challenges related to radar ambiguity while being also limited in both distance and velocity resolution due to limited bandwidth and per-beam time duration, respectively.” — *abstract (verified verbatim via the Tampere University research portal record)*
- **초안 문장** — SSB 만으로 다운링크 센싱을 하려는 시도는 능동 배치에서도 반복률 제약에 부딪히며, 이를 완화하려고 SIB1 자원을 함께 쓰는 방식이 제안되었다(Golzadeh 외, IEEE VTC2023-Spring).

#### `khosroshahi_prs_pdsch_globecom24` ⭐⭐ — Leveraging PRS and PDSCH for Integrated Sensing and Communication

- **서지** — K. Khosroshahi and P. Sehier and S. Mekki. *Proc. IEEE Global Communications Conf. (GLOBECOM)*, 2024
- **상태** — PUBLISHED — IEEE GLOBECOM 2024  ·  **등급** — P  ·  ⚠ **BibTeX INCOMPLETE**
- **PDF** — `/data/public/sionna_jeong/reference_library/2408.00667v2.pdf`
- **우리와의 관계** — 우리 G3(PRS 최고) 모드의 표준측 대응물. PRS comb 이 만드는 유령표적을 명시한다 — 우리 바닥유령과는 다른 종류이므로 구분해 인용.
- ⚠ LaSen 은 이 계열([25,37,45,49])을 '트래픽 불확실성 미처리' 로 비판한다.
- **초안 문장** — 5G NR 에서 PRS 와 PDSCH 를 함께 센싱에 쓰는 구성은 표준 자원 관점에서 이미 검토되었고, PRS comb 구조가 만드는 유령 표적이 함께 보고된다(Khosroshahi 외, IEEE GLOBECOM 2024).

#### `wang_gbs_lawn_arxiv26` ⭐⭐ — Clutter-Resilient ISAC for Low-Altitude Wireless Networks: A 5G Base Station-Compatible Protocol, Waveform, and Prototype

- **서지** — J. Wang and Z. Du and Y. Wang and W. Yuan and F. Liu and X. Liang and Y. Zeng. *arXiv 2603.14351*, 2026. arXiv:`2603.14351`
- **상태** — PREPRINT — 저널 템플릿, 게재처 미표기  ·  **등급** — P
- **PDF** — `/data/public/sionna_jeong/papers_isac_sionna/new_0731/2603.14351__clutter-resilient-isac-lawn-5g-bs-protocol.pdf`
- **조명원 / 기준신호** — source=자기 자신 - 5G-A 지상기지국(GBS) 시제기 · reference_signal=NR 프레임 구조를 지키는 다운링크(통신 프로토콜 미변경) · band=1.99872-5.04 GHz · bandwidth_MHz=100 · scs_kHz=30 · frame=5 ms 단일 주기, 누적 심볼 256, 심볼길이 33.33 us, 주파수 듀티 50%
- **표적 표현** — 실물 드론 · DJI Mavic 3 · 실물 비행, 온보드 궤적 기준
- **엔진 / 실측** — 야외 실측(outfield) + 링크버짓 계산
- **무엇을 무엇에 대해 검증했나** — 추적 궤적 ↔ UAV 온보드 시스템이 준 기준 궤적
- **핵심 수치** — `carrier_band_GHz` = [1.99872, 5.04], `bandwidth_MHz` = 100, `accumulated_symbols` = 256, `symbol_duration_us` = 33.33, `duty_ratio` = 0.5, `max_detection_range_km` = 1.0, `computed_SNR_out_dB` = 21, `noise_figure_dB` = 8, `downlink_rate_loss_percent` = 1.2, `link_budget_carrier_GHz` = 3.747, `link_budget_wavelength_mm` = 80.064, `assumed_uav_rcs_m2` = 0.1, `assumed_uav_rcs_dBsm` = -10.0
- **우리와의 관계** — A x 5G, 실측. '통신 자원을 얼마나 뺏기는가'를 숫자로 준 유일 사례(1.2%).
- ⚠ ⚠ PREPRINT.
- ⚠ 센싱 듀티 50% 라는 값이 통신 손실 1.2% 와 어떻게 양립하는지는 본문에서 분리해 읽어야 한다 - 인용 시 두 수치를 한 문장에 나란히 놓지 말 것.
  > “Outfield experiments demonstrate that the developed 5G-A GBS can effectively track weak and slow targets at distances exceeding 1 kilometer, while incurring only a 1.2% downlink rate loss relative to commercial 5G-A GBS.” — *Abstract*
  > “the carrier frequency is 3.747 GHz (leading to the wavelength (lambda) as 80.064 mm), the UAV's RCS (sigma) is 0.1 m2, accumulated sensing symbol number (Nsym) is 256, the symbol duration (T) is 33.33 us, the radar frequency duty ratio (eta) is 50%, the maximum detection distance (Rmax) is 1 km” — *p.6*
- **초안 문장** — 5G-A 기지국 시제기로 저고도 UAV 를 추적한 야외 실측은 통신 자원 손실을 1.2 % 로 계상해 보고한다(Wang 외, 2026).

#### `li_mdrt_icct25` ⭐⭐⭐ — Micro-Doppler Signature Simulation of Multirotor UAVs Using Ray Tracing

- **서지** — Changjun Li and Shiyi Mu and Jun Jiang and Lei Feng and Yuan Gao and Shugong Xu. *Proc. IEEE 25th Int. Conf. Communication Technology (ICCT)*, 2025. DOI `10.1109/ICCT67417.2025.11374154`
- **상태** — PUBLISHED — PDF p.1 의 DOI 와 OpenAlex 조회로 이중 확인  ·  **등급** — P
- **PDF** — `/data/public/sionna_jeong/papers_isac_sionna/paper_sionna_Ray_0723/Micro-Doppler_Signature_Simulation_of_Multirotor_UAVs_Using_Ray_Tracing.pdf`
- **조명원 / 기준신호** — source=시뮬레이션(Sionna RT) · reference_signal=해당 없음 · band=본문 미확인
- **표적 표현** — 회전 프로펠러 1개 · Sionna 내장 reflector -> 1/2/3/6 점산란체 -> Blender 블레이드 1장 · ⭐ 기체 없음. 전기체 메시를 산란계산에 통과시키지 않는다.
- **엔진 / 실측** — Sionna RT 개조 - 광선 발사기를 구면 샘플링에서 원뿔 샘플링으로 교체
- **무엇을 무엇에 대해 검증했나** — 스펙트로그램 능선 위치 ↔ 해석적 마이크로도플러 예측(정성 비교)
- **핵심 수치** — `propeller_radius_cm` = 10.55, `blades` = 2, `rotating_propellers` = 1
- **우리와의 관계** — 우리가 엔진에 손댄 일의 가장 가까운 기술적 선례. 다만 바꾼 것은 샘플러뿐이고 EM 은 스톡이다.
- ⚠ ⚠ Table I 의 프로펠러 반경 10.55 cm 와 본문 IV-B 의 블레이드 길이 1.055 m 가 10배 어긋난다. 한쪽만 인용하지 말 것.
- ⚠ R20 대정정 기록 참조: 이 논문을 '드론 RCS 를 Sionna 로 냈다'로 요약하면 E1.
- ⚠ ⚠ 기체가 없다. '드론을 Sionna 에 넣었다'로 요약하면 과장이다. 정확히는 '로터 1개'다. ⚠ 저자군은 Great-X(X06)와 같은 연구실이다 - 두 편을 독립 증거처럼 나란히 세우지 말 것.
  > “We propose an improved directional ray-tracing strategy based on Sionna RT, which replaces spherical sampling with conical sampling to enhance path density and distribution accuracy in critical regions.” — *p.1*
  > “Rotating propellers 1 \| Blades per propeller 2 \| Propeller radius 10.55cm \| Propeller material Wood” — *p.3 Table I*
  > “To date, no research has systematically employed ray tracing to model and analyze signal spectrum variations caused by rotational motions of multirotor UAVs.” — *p.1*
- **초안 문장** — Sionna RT 의 광선 발사기를 원뿔 샘플링으로 바꿔 회전 프로펠러의 마이크로도플러를 모사한 선례가 있으나(Li 외, ICCT 2025), 대상은 프로펠러 한 개이고 절대 산란량(dBsm)이나 검출 지표는 한 번도 제시되지 않는다.

#### `wei_rotor_md_twc25` ⭐⭐⭐ — UAV's Rotor Micro-Doppler Feature Extraction Using Integrated Sensing and Communication Signal: Algorithm Design and Testbed Evaluation

- **서지** — Z. Wei and others. *IEEE Trans. Wireless Commun.*, 2025. DOI `10.1109/TWC.2025.3578033`
- **상태** — PUBLISHED — IEEE TWC 2025  ·  **등급** — P  ·  ⚠ **BibTeX INCOMPLETE**
- **PDF** — `/data/public/sionna_jeong/papers_isac_sionna/paper_sionna_Ray_0723/UAVs_Rotor_Micro-Doppler_Feature_Extraction_Using_Integrated_Sensing_and_Communication_Signal_Algorithm_Design_and_Testbed_Evaluation.pdf`
- **우리와의 관계** — 우리 마이크로도플러 대조의 실측 앵커 계열(flash-rate 규약 확인에 이미 사용).
- ⚠ ⚠ arXiv 판(2408.16415, 2024)과 TWC 판(2025, 17 p)은 다른 문서다 (E2).
- **초안 문장** — ISAC 파형으로 실제 멀티로터의 로터 마이크로도플러를 추출한 실측 연구는 PRF >= 2 f_mD,max 라는 표본화 조건을 드론 맥락에서 이미 명시한다(Wei 외, IEEE TWC 24:10166-10182, 2025).

#### `xu_ckm_clam_arxiv25`  — CKM-Enabled Joint Spatial-Doppler Domain Clutter Suppression for Low-Altitude UAV ISAC

- **서지** — Z. Xu and Z. Zhou and D. Wu and X. Xu and Y. Zeng. *arXiv 2512.09560*, 2025. arXiv:`2512.09560`
- **상태** — PREPRINT  ·  **등급** — P
- **PDF** — `/data/public/sionna_jeong/papers_isac_sionna/new_0731/2512.09560__ckm-clutter-suppression-lowalt-uav-isac.pdf`
- **조명원 / 기준신호** — source=ISAC 기지국 자기 송신 · reference_signal=OFDM · band=본문 미확인
- **표적 표현** — 저고도 소형 UAV · 시뮬레이션 표적(점 산란체 수준)
- **엔진 / 실측** — 시뮬레이션만. 사이트별 클러터각 지도(CLAM)를 사전 구축해 공간-도플러 2단 제거.
- **무엇을 무엇에 대해 검증했나** — 파라미터 추정 정확도 ↔ 시뮬레이션 기준값
- **우리와의 관계** — A. 우리 '느린 표적은 도플러로 안 갈린다' 서사의 시뮬 선행.
- ⚠ ⚠ PREPRINT, 시뮬레이션 전용.
  > “Traditional clutter suppression methods based on Doppler difference or signal strength are inadequate for scenarios with dynamic clutter and slow-moving targets like low-altitude UAVs.” — *Abstract*
- **초안 문장** — 저고도 UAV ISAC 에서 느린 표적이 클러터와 도플러로 갈리지 않는 문제는 사이트별 클러터 지도를 미리 만들어 공간-도플러 두 단계로 지우는 방식으로 다루어진다(Xu 외, 2025).

#### `mmhawkeye_secon23`  — mmHawkeye: Passive UAV Detection with a COTS mmWave Radar

- **서지** — Jia Zhang and Xin Na and Rui Xi and Yimiao Sun and Yuan He. *Proc. IEEE Int. Conf. Sensing, Communication, and Networking (SECON)*, 2023. DOI `10.1109/SECON58729.2023.10287526`
- **상태** — PUBLISHED — IEEE SECON 2023  ·  **등급** — P
- **PDF** — `/data/public/sionna_jeong/reference_library/2308.06479v1.pdf`
- **조명원 / 기준신호** — source=자기 자신 - COTS mmWave FMCW 레이더 · reference_signal=해당 없음(능동) · band=mmWave (COTS 레이더)
- **표적 표현** — 실물 UAV · 본문 미확인(이번 라운드 미추출) · 실물 비행
- **엔진 / 실측** — 실측 + LSTM 식별기, 주기적 미소운동(PMM) 특징
- **무엇을 무엇에 대해 검증했나** — 검출 정확도·거리 ↔ 실험 조건별 성능 평가
- **핵심 수치** — `detection_accuracy_percent` = 95.8, `detection_range_m` = 80
- **우리와의 관계** — A. 우리 격자에는 직접 안 들어가지만, 'passive' 라는 낱말의 뜻이 갈리는 대표 사례라 분류 근거로 인용한다.
- ⚠ ⚠ 이 논문을 패시브 레이더 선행으로 인용하면 분류 오류다.
- ⚠ 디스크 파일은 프리프린트 판이므로 쪽번호 인용 금지.
- ⚠ ⚠ 용어 함정: 제목의 Passive 는 조명원이 아니라 표적을 가리킨다. 기하는 능동 모노스태틱. 본문에 'monostatic'/'bistatic' 0회(기계 계수).
  > “This paper presents mmHawkeye, a passive approach for UAV detection with a COTS millimeter wave (mmWave) radar. mmHawkeye doesn't require prior knowledge of the type, motions, and flight trajectory of the UAV” — *Abstract*
- **초안 문장** — COTS mmWave 레이더로 비협조 UAV 를 검출하는 계열은 'passive' 를 '표적이 비협조' 라는 뜻으로 쓴다(Zhang 외, IEEE SECON 2023) — 조명원 소유권을 뜻하는 우리 용법과 구별해야 한다.

#### `sun_doppler_resolution_taes19` ⭐⭐ — Improving the Doppler Resolution of Ground-Based Surveillance Radar for Drone Detection

- **서지** — Hongbo Sun and Beom-Seok Oh and Xin Guo and Zhiping Lin. *IEEE Trans. Aerosp. Electron. Syst.*, 2019. DOI `10.1109/TAES.2019.2895585`
- **상태** — PUBLISHED — IEEE TAES 55(6)  ·  **등급** — B
- **PDF** — 디스크에 없음
- **우리와의 관계** — ⭐ 도플러 분해능이 드론 검출의 병목이라는 명제의 능동레이더측 선례. 우리 report11(저속·분해능)의 대조군.
- **초안 문장** — 드론 검출의 병목이 도플러 축에 있다는 인식은 지상 감시 레이더 문헌에서 먼저 확립되었으나(Sun 외, IEEE TAES 55(6), 2019), 그것은 분해능의 문제이지 반복률이 정하는 무모호 상한과는 다른 축이다.

#### `han_drone_dataset_scidata26`  — A Time-Synchronized Multi-Sensor Drone Dataset Acquired from Multiple Radars and RF Receiver

- **서지** — S.-K. Han and Y.-H. Jung. *Sci. Data*, 2026. DOI `10.1038/s41597-026-06802-6`
- **상태** — PUBLISHED — Scientific Data (Nature Portfolio)  ·  **등급** — P
- **PDF** — `/data/public/sionna_jeong/papers_isac_sionna/new_0731/natsciData2026__multisensor-drone-radar-dataset.pdf`
- **조명원 / 기준신호** — source=FMCW 레이더 + CW 레이더 + RF 수신기(방출 청취) · reference_signal=해당 없음 · band=본문 미추출
- **표적 표현** — 상용 드론 4종 + 비-드론 표적 1종 · 본문 미추출 · 실물
- **엔진 / 실측** — 실측 데이터셋. 2-30 m 를 2 m 간격으로, 통제 조건 반복 측정.
- **무엇을 무엇에 대해 검증했나** — 데이터셋 일관성 ↔ 반복 시행
- **핵심 수치** — `distance_min_m` = 2, `distance_max_m` = 30, `distance_step_m` = 2, `drone_models` = 4
- **우리와의 관계** — A. 우리 실측 계획(측정 2종)의 참조 데이터셋 형식.
- ⚠ 표적 모델명·주파수는 이번 라운드에서 추출하지 않았다 - UNVERIFIED.
  > “Measurements were taken across distances ranging from 2 to 30 meters in 2-meter intervals, with repeated trials under controlled conditions to ensure consistency.” — *Abstract*
- **초안 문장** — 여러 레이더와 RF 수신기를 시간 동기해 얻은 공개 드론 데이터셋이 존재하며(Han & Jung, Scientific Data 13:407, 2026), 실측 계획의 형식 참조가 된다.

#### `vovchuk_carryon_arxiv25`  — Drone Carry-on Weight and Wind Flow Assessment via Micro-Doppler Analysis

- **서지** — D. Vovchuk and O. Torgovitsky and M. Khobzei and V. Tkach and S. Geyman and A. Kharchevskii and A. Sheleg and T. Salgals and V. Bobrovs and S. Gizach and A. Glam and N. H. Mizrahi and A. Liberzon and P. Ginzburg. *arXiv 2510.22846*, 2025. arXiv:`2510.22846`
- **상태** — PREPRINT — 원고 템플릿, 게재처 미표기  ·  **등급** — P
- **PDF** — `/data/public/sionna_jeong/papers_isac_sionna/new_0731/2510.22846__drone-carryon-weight-microdoppler.pdf`
- **조명원 / 기준신호** — source=자체 레이더 · reference_signal=해당 없음 · band=본문 미추출
- **표적 표현** — 호버링 쿼드콥터 · 본문 미추출 · 실물, 통제 풍동/야외 실험
- **엔진 / 실측** — 실측 + 비행제어기 물리 설명
- **무엇을 무엇에 대해 검증했나** — 적재중량과 바람이 마이크로도플러에 남기는 서명 분리 ↔ 통제 실험 세트
- **우리와의 관계** — 우리 관절형 드론·로터별 개성 모델의 물리적 근거(로터별 회전수가 자세에 따라 갈린다).
- ⚠ ⚠ PREPRINT.
  > “the forward and rear rotors rotate at different velocities to maintain the tilt angle of the drone body relative to the airflow direction. This causes the splitting in the micro-Doppler spectra.” — *Abstract*
- **초안 문장** — 적재 중량과 바람이 쿼드콥터 마이크로도플러에 서로 다른 서명을 남긴다는 실험 보고가 있으며(Vovchuk 외, 2025), 이는 로터별 회전수가 자세에 따라 갈린다는 물리를 뒷받침한다.

</details>

### 2.B — B · 패시브 준-모노스태틱 — 남이 송신하고 RX 가 조명원 옆에 붙는다 (beta ~ 0)  *(3편)*

| 인용키 | 논문 | 게재처 · 상태 | 연 | 조명원 | 표적 표현 | 엔진/실측 | 무엇을 검증했나 | 우리와의 관계 | 등급 |
|---|---|---|---|---|---|---|---|---|---|
| `martelli_wifi_radar17` ⭐⭐⭐ | Detection and 3D Localization of Ultralight Aircrafts and Drones with a WiFi-… | Proc. IET Int. Conf. Radar Systems (Radar 201…<br>*PUBLISHED* | 2017 | WiFi | 초경량 항공기 + 소형 상용 드론 · 본문 미명시 · 실물 비행 | 실측. 사이드로브 억제 -> 거리-속도 맵 -> CA-CFAR -> 3 수신채널 3-of-3 결합 … | 3D 위치추정 ↔ 실비행 시나리오(기준 궤적은 본문 미확인) | ⭐ B x WiFi. 'quasi-monostatic' 이라는 낱말이 실제 배치에 붙은 교과서 사례이자 우리 B 정의의 인용 근거. | P |
| `diseglio_reffree_ietrsn24` ⭐⭐⭐ | Comparing Reference-Free WiFi Radar Sensing Approaches for Monitoring People … | IET Radar Sonar Navig.<br>*PUBLISHED* | 2024 | WiFi | 협력 인체 표적 + 상용 드론 · 본문 미명시 · 실물 | 실측 | 네 처리 전략의 검출 성능 ↔ 동일 실측 데이터의 상호 비교 | ⭐⭐ B 대 C 를 같은 시스템으로 비교한 유일 사례. 우리 격자의 기하 축 서술에 그대로 인용된다. | P |
| `demissie_lte450_radar24` ⭐⭐ | Protection of Critical Infrastructure Using LTE450-Based Passive Radar: Range… | Proc. IEEE Radar Conf. (RadarConf)<br>*PUBLISHED* | 2024 | LTE | 실물 드론 · DJI Matrice M210 (약 88 x 88 x 39 cm, 5 kg 미만) · 실물 비행, GP… | 실측 (농경지 주차장) | 거리 측정 ↔ GPS 로거 | ⭐ B x LTE. lambda 가 커서(약 0.65 m) v_max 가 가장 유리한 극단이기도 하다. | P |

<details><summary><b>▸ 상세 카드 3편</b> — 서지 · 수치 · 인용문 · 초안 문장</summary>

#### `martelli_wifi_radar17` ⭐⭐⭐ — Detection and 3D Localization of Ultralight Aircrafts and Drones with a WiFi-Based Passive Radar

- **서지** — T. Martelli and F. Murgia and F. Colone and C. Bongioanni and P. Lombardo. *Proc. IET Int. Conf. Radar Systems (Radar 2017)*, 2017. DOI `10.1049/cp.2017.0423`
- **상태** — PUBLISHED — IET Radar 2017  ·  **등급** — P
- **PDF** — `/data/public/jeong/papers/Wifi/17_Detection_and_3D_localization_of_ultralight_aircrafts_and_drones_with_a_WiFi-based_passive_radar.pdf`
- **조명원 / 기준신호** — source=상용 WiFi AP (비협력) · reference_signal=전용 기준 수신채널 · band=2.4 GHz WiFi · sampling_MHz=22
- **표적 표현** — 초경량 항공기 + 소형 상용 드론 · 본문 미명시 · 실물 비행
- **엔진 / 실측** — 실측. 사이드로브 억제 -> 거리-속도 맵 -> CA-CFAR -> 3 수신채널 3-of-3 결합 -> 3D 측위
- **무엇을 무엇에 대해 검증했나** — 3D 위치추정 ↔ 실비행 시나리오(기준 궤적은 본문 미확인)
- **핵심 수치** — `CPI_s` = 0.3, `map_step_s` = 0.1, `per_map_nominal_Pfa` = 0.01, `combined_nominal_Pfa` = 1e-06, `alt_per_channel_nominal_Pfa` = 0.05011872336272722, `alt_combined_nominal_Pfa` = 0.0001, `sampling_MHz` = 22
- **우리와의 관계** — ⭐ B x WiFi. 'quasi-monostatic' 이라는 낱말이 실제 배치에 붙은 교과서 사례이자 우리 B 정의의 인용 근거.
- ⚠ nominal Pfa 곱셈 결합(1e-2^3 = 1e-6)은 채널 간 독립 가정에 의존한다. 우리 경험적 Pfa 교정과 대비할 지점.
  > “the first surveillance antenna (RX1) was mounted above the second and third ones (RX2 and RX3) in a quasi-monostatic configuration with respect the TX.” — *본문*
  > “A CFAR threshold is applied to the individual range-velocity map set to provide Pfa=10-2, which allows a nominal Pfa=10-6 for the final range-velocity plane, since a three o[ut of three criterion is used]” — *p.4*
- **초안 문장** — 수신기를 조명원 바로 옆에 두는 준-모노스태틱 패시브 배치는 WiFi 패시브 레이더에서 명시적으로 채택된 바 있으며(Martelli 외, Radar 2017), 그 계열의 오경보율은 설계값(nominal Pfa)으로만 보고되고 실제 달성치는 측정되지 않는다.

#### `diseglio_reffree_ietrsn24` ⭐⭐⭐ — Comparing Reference-Free WiFi Radar Sensing Approaches for Monitoring People and Drones

- **서지** — M. Di Seglio and F. Filippini and C. Bongioanni and F. Colone. *IET Radar Sonar Navig.*, 2024. DOI `10.1049/rsn2.12506`
- **상태** — PUBLISHED — IET RSN 2024  ·  **등급** — P  ·  ⚠ **BibTeX INCOMPLETE**
- **PDF** — `/data/public/jeong/papers/Wifi/24_Comparing reference-free WiFi radar sensing approaches for monitoring people and drones.pdf`
- **조명원 / 기준신호** — source=상용 WiFi AP · reference_signal=네 전략 비교 - preamble-only PR / IDP(기준신호 없음) / 합성 기준 / 진폭만 · band=2.4 GHz 와 5 GHz
- **표적 표현** — 협력 인체 표적 + 상용 드론 · 본문 미명시 · 실물
- **엔진 / 실측** — 실측
- **무엇을 무엇에 대해 검증했나** — 네 처리 전략의 검출 성능 ↔ 동일 실측 데이터의 상호 비교
- **우리와의 관계** — ⭐⭐ B 대 C 를 같은 시스템으로 비교한 유일 사례. 우리 격자의 기하 축 서술에 그대로 인용된다.
- ⚠ ⚠⚠ 이 논문의 'Doppler ambiguity' 는 반복률 접힘이 아니라 직접파 우세 가정이 깨져 생긴 위상동기 실패다. 우리 v_max 서사에 끌어오면 E3.
  > “it relies on a reasonable stability of the amplitude of the target return that is typically guaranteed under extreme bistatic geometries while it might be weaker in quasi-monostatic configurations” — *본문*
  > “However, note that there is a Doppler ambiguity in the time interval between 0 and 5 s, when the target is in the first range cell.” — *본문*
- **초안 문장** — 같은 WiFi 시스템으로 준-모노스태틱과 극단 바이스태틱을 나란히 관측하면 처리 방식별 우열이 기하에 따라 뒤바뀐다(Di Seglio 외, IET RSN 2024).

#### `demissie_lte450_radar24` ⭐⭐ — Protection of Critical Infrastructure Using LTE450-Based Passive Radar: Range Measurements for Drone Detection

- **서지** — B. Demissie and M. Boswetter and M. Mandt and C. Steffes. *Proc. IEEE Radar Conf. (RadarConf)*, 2024. DOI `10.1109/RADAR58436.2024.10993905`
- **상태** — PUBLISHED — IEEE RADAR 2024  ·  **등급** — P
- **PDF** — `/data/public/jeong/papers/LTE/24_Protection_of_Critical_Infrastructure_using_LTE450-based_Passive_Radar_Range_Measurements_for_Drone_Detection.pdf`
- **조명원 / 기준신호** — source=LTE450 기지국(비협력) · reference_signal=기준 안테나 + 감시 안테나 · band=band 31/72, 461.0-467.5 MHz - 이 라이브러리에서 가장 낮은 반송파
- **표적 표현** — 실물 드론 · DJI Matrice M210 (약 88 x 88 x 39 cm, 5 kg 미만) · 실물 비행, GPS 로거 지상진리
- **엔진 / 실측** — 실측 (농경지 주차장)
- **무엇을 무엇에 대해 검증했나** — 거리 측정 ↔ GPS 로거
- **핵심 수치** — `carrier_MHz_range` = [461.0, 467.5]
- **우리와의 관계** — ⭐ B x LTE. lambda 가 커서(약 0.65 m) v_max 가 가장 유리한 극단이기도 하다.
- ⚠ config B 배정은 위 인용문에 근거한 우리 판정이다. 논문 자신은 기하 각도를 수치로 주지 않는다.
  > “For our first experiments, the goal was to get as close as possible to a monostatic setup.” — *본문*
- **초안 문장** — 패시브 배치를 모노스태틱에 최대한 가깝게 만들려는 시도는 LTE450 조명원 실험에서 명시적으로 보고되었다(Demissie 외, RADAR 2024).

</details>

### 2.C — C · 패시브 바이스태틱 — 남이 송신하고 RX 는 멀리 있다 (beta 큼)  *(30편)*

| 인용키 | 논문 | 게재처 · 상태 | 연 | 조명원 | 표적 표현 | 엔진/실측 | 무엇을 검증했나 | 우리와의 관계 | 등급 |
|---|---|---|---|---|---|---|---|---|---|
| `colone_reffree_taes23` | Reference-Free Amplitude-Based WiFi Passive Sensing | IEEE Trans. Aerosp. Electron. Syst.<br>*PUBLISHED, open access* | 2023 | WiFi | 인체 / 드론 · 본문 미명시 · 실물 | 실측 | 기준신호 없는 검출 ↔ 기준신호 있는 처리와의 비교 | 우리 '기준신호 접근도' 축(전 파형 / 기준신호만 / 기준신호 없음)의 최하단 계단. | P |
| `filippini_reffree_radarconf23` | OFDM Based WiFi Passive Sensing: A Reference-Free Non-Coherent Approach | Proc. IEEE Radar Conf. (RadarConf23)<br>*PUBLISHED* | 2023 | WiFi | 인체와 드론 · 본문 미명시 · 실물 | 실측 | 대안 압축(RpF)과 기준신호 없는 처리 ↔ 표준 정합필터 처리 | C x WiFi. 기준신호를 아예 안 쓰는 극단 — 우리 '이상적 레퍼런스 정합필터' 가정의 반대편 끝. | P |
| `diseglio_rpf_irs22` | Human and Drone Surveillance via RpF-Based WiFi Passive Radar: Experimental V… | Proc. Int. Radar Symp. (IRS)<br>*PUBLISHED* | 2022 | WiFi | 인체와 드론 · 본문 미명시 · 실물 | 실측 | 대안 압축(RpF)과 기준신호 없는 처리 ↔ 표준 정합필터 처리 | C x WiFi. reciprocal filter 로 압축하는 대안 — 우리 정합필터 규약과 나란히 놓을 처리 축. | P |
| `milani_fusion_rs21` | Fusing Measurements from Wi-Fi Emission-Based and Passive Radar Sensors for S… | Remote Sens.<br>*PUBLISHED, open access* | 2021 | WiFi | UAV / 드론 · 본문 미명시 · 실물 | 실측 | 추적/측위 ↔ 실비행 | C x WiFi. 방출 기반 측위와 반사 기반 패시브 레이더를 한 시스템에서 융합한 사례 — 'passive' 두 뜻이 한 논문에 공존한다. | P |
| `taylor_lte_pbr_taes25` ⭐⭐⭐ | Drone Detection Using 4G-LTE-Based Passive Radar | IEEE Trans. Aerosp. Electron. Syst.<br>*PUBLISHED* | 2025 | LTE | 실물 드론 · DJI Phantom 3 (TAES 실험) · 실물 비행, 약 10 m/s | 실측. 클러터 제거 -> 압축 -> lowest-of CA-CFAR. | 검출과 거리·속도 ↔ 실비행 기록 | ⭐ C x LTE. 실측 드론 바이스태틱 속도 분포를 주는 유일 앵커 - 우리 v_max 상한이 실제로 문제가 되는 구간인지 판정하는 기준. | P |
| `ji_bistatic_wcl26` ⭐⭐⭐ | An Experimental Study on Fine-Grained Bistatic Sensing of UAV Trajectory via … | IEEE Wireless Commun. Lett.<br>*PUBLISHED* | 2026 | LTE | 실물 UAV · 본문 미추출 · 실물 비행 | 실측. 두 방향의 바이스태틱 도플러로 속도를 얻고 궤적을 재구성. | 궤적 추적 오차 ↔ 복잡 궤적의 기준값(본문 미추출) | ⭐ C+D x LTE. 다중 수신기 결합의 최신 실측이며, '거리분해능보다 좋은 정확도' 주장이 우리 분해능 서사와 정면으로 부딪힌다. | P |
| `dan_lte_pbr_joe19` | LTE-Based Passive Radar for Drone Detection and Its Experimental Results | J. Eng.<br>*PUBLISHED* | 2019 | LTE | 소형 UAV · 실물 | 실측 | 검출 ↔ 실비행 | C x LTE 의 초기 실험 레퍼런스. | P |
| `sun_uav_tracking_ojcoms25` | An Experimental Study of Passive UAV Tracking with Digital Arrays and Cellula… | IEEE Open J. Commun. Soc.<br>*PUBLISHED* | 2025 | LTE | UAV / 드론 · 본문 미명시 · 실물 | 실측 | 추적/측위 ↔ 실비행 | C x LTE. 디지털 배열 2대로 바이스태틱 UAV 궤적을 추적한 실측 — 우리 다중 Rx 결합의 실측 상대. | P |
| `taylor_lte_pbr_radar23` | Experimental UAV Detection Using 4G-LTE-Based Passive Radar | Proc. IEEE Radar Conf. (RadarConf23)<br>*PUBLISHED* | 2023 | LTE | 실물 드론 · DJI Phantom 3 (TAES 실험) · 실물 비행, 약 10 m/s | 실측. 클러터 제거 -> 압축 -> lowest-of CA-CFAR. | 검출과 거리·속도 ↔ 실비행 기록 | C x LTE. TAES 2025 판의 회의 선행판 — 같은 실험의 초기 보고. | P |
| `sun_lte_poster_wisec22` | POSTER: Passive Drone Localization Using LTE Signals | Proc. 15th ACM Conf. Security and Privacy in …<br>*PUBLISHED* | 2022 | LTE | UAV / 드론 · 본문 미명시 · 실물 | 실측 | 추적/측위 ↔ 실비행 | C(+D) x LTE. ⚠ '패시브' 인데 조명원이 자기 USRP N210 이다 — 조명원 소유권 축의 경계 사례. | P |
| `maksymiuk_renyi_rs22` ⭐⭐⭐ | R\'enyi Entropy-Based Adaptive Integration Method for 5G-Based Passive Radar … | Remote Sens.<br>*PUBLISHED, open access CC BY* | 2022 | 5G NR | 실물 드론 · DJI M600 PRO (폭·길이 약 1 m, 높이 약 40 cm, 플라스틱) · 실물 비행, GPS … | 실측 + 시뮬레이션. Renyi 엔트로피로 다운링크 자원이 조밀하게 할당된 시간구간을 골라 적분한다. | 적응 적분 방식 ↔ 시뮬레이션 신호와 실측 신호 양쪽 | ⭐⭐ C x 5G. 우리 '점유(occupancy) 대가' 서사(G1/G2/G3)의 가장 강한 외부 앵커. 그리고 SSB 단독일 때의 반복주기 5-160 ms 를 명시한 게재 문헌. | P |
| `jopanya_ssb_spawc25` ⭐⭐⭐ | Utilizing 5G NR SSB Blocks for Passive Detection and Localization of Low-Alti… | Proc. IEEE 26th Int. Workshop Signal Processi…<br>*PUBLISHED* | 2025 | 5G NR | 저고도 드론 · ⭐ 시뮬레이션 점표적. 2D-FFT 추정기를 CRB 와 비교. | 시뮬레이션 | 추정기 성능 ↔ Cramer-Rao bound | ⭐⭐ C x 5G. 우리 헤드라인이 실제로 겨루는 상대이자 리뷰어가 가장 먼저 찌를 지점. | P |
| `abratkiewicz_ssb_jstars23` ⭐⭐⭐ | SSB-Based Signal Processing for Passive Radar Using a 5G Network | IEEE J. Sel. Topics Appl. Earth Observ. Remot…<br>*PUBLISHED* | 2023 | 5G NR | — | — | — | ⭐ SSB 를 '펄스' 로 보는 관점의 표준 참조 — 우리 v_max = lambda*PRF_ref/4 서사와 정확히 같은 물리. JSTARS 는 우리 타깃 저널 목록에도 있다. | S |
| `nataraja_bistatic_isac_tvt25` ⭐⭐ | Integrated Sensing and Communication (ISAC) for Vehicles: Bistatic Sensing wi… | IEEE Trans. Veh. Technol.<br>*PUBLISHED* | 2025 | 5G NR | — | — | — | LaSen 본문에서 'bistatic' 이라는 단어가 나오는 유일한 자리가 이 참고문헌 [37] 이다(LaSen 자신은 모노스태틱). 5G-NR 바이스태틱의 표준 참조. | B |
| `maksymiuk_5g_irs23` | 5G Network-Based Passive Radar for Drone Detection | Proc. Int. Radar Symp. (IRS)<br>*PUBLISHED* | 2023 | 5G NR | 드론 / UAV 침입 · 본문 미명시 · 실물 | 실측 | 검출 ↔ 실비행 | C x 5G. 우리 5G 대역·대역폭(3.44 GHz, 최대 38.16 MHz) 설정의 실측 대조군이자 바이스태틱 기호 규약(L, beta, R1, R2)의 표준. | P |
| `ai_5g_piers21` | Passive Detection Experiment of UAV Based on 5G New Radio Signal | Proc. PhotonIcs and Electromagnetics Research…<br>*PUBLISHED* | 2021 | 5G NR | UAV · (a) 실측 (b) 미상 | (a) 실측 (b) 학습 기반 | (a) 검출 실험 (b) 분류 성능 ↔ 본문 미확인 | C x 5G 의 연도 우선권. 5G 패시브 UAV 검출 실험의 최초 보고 계열. | P |
| `maksymiuk_5g_asilomar25` | UAV Intrusion Detection with Passive Radar Based on the 5G Network | Proc. 59th Asilomar Conf. Signals, Systems, a…<br>*PUBLISHED* | 2025 | 5G NR | 드론 / UAV 침입 · 본문 미명시 · 실물 | 실측 | 검출 ↔ 실비행 | C x 5G. 같은 그룹의 후속 실험 — UAV 침입 검출로 확장한 최신판. | P |
| `lin_5g_spectrum_iccc23` | 5G Spectrum Learning-Based Passive UAV Detection in Urban Scenario | Proc. IEEE/CIC Int. Conf. Communications in C…<br>*PUBLISHED* | 2023 | 5G NR | UAV · (a) 실측 (b) 미상 | (a) 실측 (b) 학습 기반 | (a) 검출 실험 (b) 분류 성능 ↔ 본문 미확인 | ⚠ '기하 미상' 칸의 정직한 표본 — 학습 기반 논문이 송수신 배치를 명시하지 않는 경향을 보여준다. | P |
| `huang_uplink_srs_arxiv26` ⭐⭐ | Fuse-then-Detect for Passive UAV Localization Using Multi-UE 5G Uplink Signals | arXiv 2607.11955<br>*PREPRINT* | 2026 | 5G NR (업링크 SRS) | 저고도 UAV · 본문 미추출 · 본문 미추출(시뮬레이션으로 보임 - 미확인) | 본문 미추출 - UNVERIFIED | 본문 미추출 ↔ 본문 미추출 | ⭐ 우리 조명원 축에 없는 칸 - 업링크. 우리가 다운링크 상시 신호만 다룬다는 스코핑 문장의 근거가 된다. | P |
| `needle_haystack_mobisys26` ⭐⭐⭐ | Needle in a Haystack: Tracking UAVs from Massive Noise in Real-World 5G-A Bas… | Proc. 24th Annu. Int. Conf. Mobile Systems, A…<br>*PUBLISHED* | 2026 | 5G-A | — | — | — | ⭐⭐ 2026 최상위 시스템 학회가 실망(live network) 5G-A 데이터로 UAV 를 추적한다 — 우리 챔버 시뮬레이션의 정반대 극. 우리 한계(무향실·시뮬)를 정직하게 대비시킬 최적의 문헌. | B |
| `bai_passive_uav_twc26` | Passive UAV Detection Based on Channel Estimation and Temporal Variation Netw… | IEEE Trans. Wireless Commun.<br>*PUBLISHED* | 2026 | cellular (미분류) | — | — | — | 채널추정 시계열 기반 패시브 검출(레이더맵 없이). 우리 검출 통계와 다른 계열의 베이스라인. | B |
| `gao_csi_uav_icassp25` | A Self-Supervised UAV Detection Method Based on Channel State Information | Proc. IEEE Int. Conf. Acoustics, Speech and S…<br>*PUBLISHED* | 2025 | cellular (미분류) | — | — | — | ⭐ CSI(통신 부산물)만으로 UAV 를 검출하는 ICASSP 2025 판. 우리 '이상적 정합필터' 대비 '실전 CSI' 축의 대조군. | B |
| `pang_mfs_taes25` | MFS: A Motion Feature Separation Model for UAV Detection Under Passive Radar | IEEE Trans. Aerosp. Electron. Syst.<br>*PUBLISHED* | 2025 | cellular (미분류) | — | — | — | 패시브 드론 검출의 최신 신호처리 베이스라인. | B |
| `zhang_cyclostationary_taes26` | Weak Cyclostationary Target Echo Detection for Multi-UAV Enabled Passive Radar | IEEE Trans. Aerosp. Electron. Syst.<br>*PUBLISHED* | 2026 | cellular (미분류) | — | — | — | 약신호 검출 통계의 대안(순환정상성) — 우리 CFAR 교정과 나란히. | B |
| `sun_passive_uav_imaging_tvt23` | Performance Analysis and System Implementation for Energy-Efficient Passive U… | IEEE Trans. Veh. Technol.<br>*PUBLISHED* | 2023 | cellular (미분류) | — | — | — | 패시브 UAV 레이더 이미징의 시스템 구현 — '패시브로 어디까지 가나' 의 상한 사례. | B |
| `rzewuski_nato21` ⭐⭐⭐ | Drone Detectability Feasibility Study Using Passive Radars Operating in WIFI … | NATO STO Meeting Proc. STO-MP-MSG-SET-183<br>*PUBLISHED* | 2021 | DVB-T + WiFi | 실물 드론 + 그 드론의 EM 모델 · Parrot AR.Drone 2.0 (폴리프로필렌 기체, 4 로터) · ⭐ 두… | FDTD (QuickWave-3D) 로 mono/bi RCS 계산 + 커버리지 예산 + WiFi/D… | 시뮬레이션 RCS 특성 ↔ 저자들의 이전 WiFi 대역 실측 [ref 2] 과의 비대칭성 일치 | ⭐⭐ C x WiFi + E. 우리 격자에서 기하 두 칸과 조명원 한 칸을 한 논문이 동시에 채운 유일 사례이자, 산란 계산을 바이스태틱으로 일반화해야 하는 이유의 문헌 근거. | P |
| `fang_lora_drone_infocomw22` ⭐⭐ | Exploring LoRa for Drone Detection | Proc. IEEE INFOCOM Workshops<br>*PUBLISHED* | 2022 | LoRa | — | — | — | 조명원 축을 WiFi/LTE/5G 밖으로 확장한 사례. LaSen 은 LoRa 의 '낮은 pulse repetition frequency' 때문에 속도 추정이 안 된다고 명시한다 — 우리 법칙의 또 다른 실사례. | B |
| `sneh_11ad_uav_icassp25` ⭐⭐ | IEEE 802.11ad-Aided 5-D Sensing with a UAV Swarm in Urban Environments | Proc. IEEE Int. Conf. Acoustics, Speech and S…<br>*PUBLISHED* | 2025 | 802.11ad | — | — | — | ⭐ WiFi 규격 신호로 UAV 를 센싱하는 ICASSP 사례 — 우리 WiFi 모드의 신호처리학회 대응물. 저자에 S. S. Ram / K. V. Mishra(마이크로도플러·레이더 시뮬 계보). | B |
| `hisac_sensys24` ⭐⭐⭐ | HiSAC: High-Resolution Sensing with Multiband Communication Signals | Proc. 22nd ACM Conf. Embedded Networked Senso…<br>*PUBLISHED* | 2024 | 다중 대역 통신 파일럿 | ⭐ 드론이 아니다 - 본문에 drone/UAV 가 0회 · 실측 표적 | 실측 (RFSoC 구현) | 초해상 거리 추정 ↔ 단일 대역 처리 | 우리 ΔR_b 규약 서술의 외부 대조. 그들은 이등분선 투영(cos 항 포함), 우리는 바이스태틱 거리합 축이다 - 모순이 아니라 축이 다르다. | P |
| `he_convex_clutter_arxiv25` ⭐⭐⭐ | Adaptive Clutter Suppression via Convex Optimization | arXiv 2512.24889<br>*PREPRINT* | 2025 | 기회 조명원 일반 | 이동 표적(드론 특정 아님) · ⭐ Monte Carlo 시뮬레이션의 무작위 표적/클러터 | 시뮬레이션. ECA 식 '먼저 지우고 나중에 검출' 대신 CAF 면 왜곡을 최소화하는 이차계획으로 … | 검출률과 실제 달성 오경보율 ↔ 동일 시뮬레이션의 비적응 CAF 기준선 | ⭐⭐ 우리 'CFAR 를 경험적 Pfa 로 교정한다' 는 절차의 유일한 외부 정량 근거. 표 1 은 설계 Pfa 1e-6 을 걸어도 클러터를 처리하지 않으면 실제 오경보율이 0.0141 로 4자리 어긋난다는 것을 보인다. | P |

<details><summary><b>▸ 상세 카드 25편</b> — 서지 · 수치 · 인용문 · 초안 문장</summary>

#### `colone_reffree_taes23`  — Reference-Free Amplitude-Based WiFi Passive Sensing

- **서지** — F. Colone and F. Filippini and M. Di Seglio and P. V. Brennan and R. Du and T. X. Han. *IEEE Trans. Aerosp. Electron. Syst.*, 2023. DOI `10.1109/TAES.2023.3276738`
- **상태** — PUBLISHED, open access — IEEE TAES 59(5)  ·  **등급** — P
- **PDF** — `/data/public/jeong/papers/Wifi/23_Reference-Free_Amplitude-Based_WiFi_Passive_Sensing.pdf`
- **조명원 / 기준신호** — source=상용 WiFi AP · reference_signal=⭐ 없음 - 진폭만 쓴다 · band=WiFi 20 MHz
- **표적 표현** — 인체 / 드론 · 본문 미명시 · 실물
- **엔진 / 실측** — 실측
- **무엇을 무엇에 대해 검증했나** — 기준신호 없는 검출 ↔ 기준신호 있는 처리와의 비교
- **우리와의 관계** — 우리 '기준신호 접근도' 축(전 파형 / 기준신호만 / 기준신호 없음)의 최하단 계단.
- ⚠ config 판정 confidence medium - 기하각을 명시하지 않는다.
- ⚠ RX 가 AP 근처(직접신호 지배)라 β 는 작지만 기하각 명시 없음. config B 배정은 우리 판단.
  > “Fig. 3 shows the result obtained with the IDP in the bistatic velocity-time plane.” — *Fig.3 설명*
- **초안 문장** — 패시브 센싱 문헌은 기준신호 접근도에 따라 전 파형·기준신호만·기준신호 없음의 세 계단으로 갈리며, 최하단에서는 속도 부호를 잃는다(Colone 외, IEEE TAES 2023).

#### `filippini_reffree_radarconf23`  — OFDM Based WiFi Passive Sensing: A Reference-Free Non-Coherent Approach

- **서지** — F. Filippini and M. Di Seglio and C. Bongioanni and P. V. Brennan and F. Colone. *Proc. IEEE Radar Conf. (RadarConf23)*, 2023. DOI `10.1109/RADARCONF2351548.2023.10149694`
- **상태** — PUBLISHED — IEEE RadarConf23  ·  **등급** — P
- **PDF** — `/data/public/jeong/papers/Wifi/22_Human_and_Drone_Surveillance_via_RpF-based_WiFi_Passive_Radar_Experimental_Validation.pdf` · `/data/public/jeong/papers/Wifi/23_OFDM_based_WiFi_Passive_Sensing_a_reference-free_non-coherent_approach.pdf`
- **조명원 / 기준신호** — source=상용 WiFi AP · reference_signal=(a) 없음 (b) reciprocal filter · band=WiFi 20 MHz
- **표적 표현** — 인체와 드론 · 본문 미명시 · 실물
- **엔진 / 실측** — 실측
- **무엇을 무엇에 대해 검증했나** — 대안 압축(RpF)과 기준신호 없는 처리 ↔ 표준 정합필터 처리
- **우리와의 관계** — C x WiFi. 기준신호를 아예 안 쓰는 극단 — 우리 '이상적 레퍼런스 정합필터' 가정의 반대편 끝.
- ⚠ 두 편을 한 레코드로 묶었다. 인용 시 각각 분리할 것.
  > “A moderate bistatic acquisition geometry was employed (see Fig. 2), featuring a commercial wireless AP (TP-Link Archer VR600 AC1600) used as illuminator of opportunity (IO)” — *IRS2022 본문*
- **초안 문장** — 기준신호를 전혀 쓰지 않는 비코히어런트 WiFi 패시브 센싱이 실험적으로 검증되어 있다(Filippini 외, IEEE RadarConf23).

#### `diseglio_rpf_irs22`  — Human and Drone Surveillance via RpF-Based WiFi Passive Radar: Experimental Validation

- **서지** — M. Di Seglio and F. Filippini and C. Bongioanni and F. Colone. *Proc. Int. Radar Symp. (IRS)*, 2022
- **상태** — PUBLISHED — IRS 2022  ·  **등급** — P  ·  ⚠ **BibTeX INCOMPLETE**
- **PDF** — `/data/public/jeong/papers/Wifi/22_Human_and_Drone_Surveillance_via_RpF-based_WiFi_Passive_Radar_Experimental_Validation.pdf` · `/data/public/jeong/papers/Wifi/23_OFDM_based_WiFi_Passive_Sensing_a_reference-free_non-coherent_approach.pdf`
- **조명원 / 기준신호** — source=상용 WiFi AP · reference_signal=(a) 없음 (b) reciprocal filter · band=WiFi 20 MHz
- **표적 표현** — 인체와 드론 · 본문 미명시 · 실물
- **엔진 / 실측** — 실측
- **무엇을 무엇에 대해 검증했나** — 대안 압축(RpF)과 기준신호 없는 처리 ↔ 표준 정합필터 처리
- **우리와의 관계** — C x WiFi. reciprocal filter 로 압축하는 대안 — 우리 정합필터 규약과 나란히 놓을 처리 축.
- ⚠ 두 편을 한 레코드로 묶었다. 인용 시 각각 분리할 것.
- ⚠ 게재처 미확인. β 도 명시되지 않아 config B 배정은 우리 판단이다.
  > “A moderate bistatic acquisition geometry was employed (see Fig. 2), featuring a commercial wireless AP (TP-Link Archer VR600 AC1600) used as illuminator of opportunity (IO)” — *IRS2022 본문*
- **초안 문장** — reciprocal filter 기반 WiFi 패시브 레이더로 사람과 드론을 함께 감시한 실험 검증이 있다(Di Seglio 외, IRS 2022).

#### `milani_fusion_rs21`  — Fusing Measurements from Wi-Fi Emission-Based and Passive Radar Sensors for Short-Range Surveillance

- **서지** — I. Milani and C. Bongioanni and F. Colone and P. Lombardo. *Remote Sens.*, 2021. DOI `10.3390/rs13183556`
- **상태** — PUBLISHED, open access — MDPI Remote Sensing 13(18)  ·  **등급** — P
- **PDF** — `/data/public/jeong/papers/LTE/22_Passive Drone Localization Using LTE Signals.pdf` · `/data/public/jeong/papers/LTE/25_An Experimental Study of Passive UAV Tracking With Digital Arrays and Cellular Downlink Signals.pdf` · `/data/public/jeong/papers/Wifi/21_Fusing Measurements from Wi-Fi Emission-Based and Passive Radar Sensors for Short-Range Surveillance.pdf`
- **조명원 / 기준신호** — source=(a) 상용 LTE eNB (b) ⚠ 자기 USRP N210 이 LTE eNB 를 모사 (c) 상용 WiFi AP · reference_signal=기준 채널 + CAF · band=(a) LTE (c) 2.4 GHz
- **표적 표현** — UAV / 드론 · 본문 미명시 · 실물
- **엔진 / 실측** — 실측
- **무엇을 무엇에 대해 검증했나** — 추적/측위 ↔ 실비행
- **우리와의 관계** — C x WiFi. 방출 기반 측위와 반사 기반 패시브 레이더를 한 시스템에서 융합한 사례 — 'passive' 두 뜻이 한 논문에 공존한다.
- ⚠ ⚠ (a) 의 'the reference and surveillance arrays of the system are co-located' 는 수신 배열 둘이 붙어 있다는 뜻이다. TX-RX 동일지점(Config B)이 아니다.
  > “Passive sensing with one illuminator and one receiver is referred to as bistatic sensing, and sensing with more than one illuminator or receiver is referred to as multi-static sensing.” — *(a) 본문*
  > “In general, we consider a multi-static passive localization setting in a 3-D Cartesian coordinate system.” — *(b) 본문*
- **초안 문장** — WiFi 대역에서는 표적 자신의 방사를 듣는 방출 기반 측위와 반사를 보는 패시브 레이더를 한 시스템에서 융합한 사례도 있다(Milani 외, Remote Sensing 13(18):3556, 2021).

#### `taylor_lte_pbr_taes25` ⭐⭐⭐ — Drone Detection Using 4G-LTE-Based Passive Radar

- **서지** — A. Taylor and D. Poullin. *IEEE Trans. Aerosp. Electron. Syst.*, 2025. DOI `10.1109/TAES.2025.3545000`
- **상태** — PUBLISHED — IEEE TAES 2025  ·  **등급** — P  ·  ⚠ **BibTeX INCOMPLETE**
- **PDF** — `/data/public/jeong/papers/LTE/23_Experimental UAV detection using 4G-LTE-based passive Radar.pdf` · `/data/public/jeong/papers/LTE/25_Drone_Detection_Using_4G-LTE-Based_Passive_Radar.pdf`
- **조명원 / 기준신호** — source=상용 LTE eNB(비협력, Tx1 우세) · reference_signal=기준 채널(H/V 편파 2채널로 기준신호 추정) + 파일럿 제한 거리-도플러 · band=fc = 1.87 GHz(비행 1-3) 또는 약 2.6 GHz(비행 4-6) · sampling_MHz=25 · resample_MHz=30.72
- **표적 표현** — 실물 드론 · DJI Phantom 3 (TAES 실험) · 실물 비행, 약 10 m/s
- **엔진 / 실측** — 실측. 클러터 제거 -> 압축 -> lowest-of CA-CFAR.
- **무엇을 무엇에 대해 검증했나** — 검출과 거리·속도 ↔ 실비행 기록
- **핵심 수치** — `carrier_GHz` = [1.87, 2.6], `sampling_MHz` = 25, `CPI_ms` = 125, `target_speed_m_s` = 10, `max_bistatic_speed_m_s` = 13, `flight2_max_m_s` = 8.2, `range_span_m` = [145, 241]
- **우리와의 관계** — ⭐ C x LTE. 실측 드론 바이스태틱 속도 분포를 주는 유일 앵커 - 우리 v_max 상한이 실제로 문제가 되는 구간인지 판정하는 기준.
- ⚠ ⚠ TAES 논문 안의 'active system is studied, with colocated transmitter and receiver' 문장은 인용문헌 소개이지 이 논문의 배치가 아니다.
- ⚠ ECA 를 버린 이유가 '레퍼런스 복호가 어렵다' 는 것 — 우리 이상적 레퍼런스 가정에 대한 반례이기도 하다.
  > “The target used was a DJI Phantom 3, evolving in a rather quiet area, without obstacles, at a velocity of about 10 m/s. For Doppler processing, a 125 ms coherent integration time was used.” — *TAES p.6*
  > “the maximum bistatic speed (also with respect to the receiver) is close to 13 m/s, except for flight 2 where the drone speed does not exceed 8.2 m/s.” — *TAES 본문*
  > “This procedure, known as lowest of cell-averaging CFAR [38], enables to avoid missed detection caused by residual sidelobes of the clutter.” — *TAES p.6*
- **초안 문장** — LTE 패시브 실측에서 관측된 드론의 바이스태틱 속도는 13 m/s 안팎에 머물며(Taylor & Poullin, IEEE TAES 2025), 이는 상시 기준신호만으로 얻는 무모호 속도와 직접 비교되는 값이다.

#### `ji_bistatic_wcl26` ⭐⭐⭐ — An Experimental Study on Fine-Grained Bistatic Sensing of UAV Trajectory via Cellular Downlink Signals

- **서지** — Chenqing Ji and Jiahong Liu and Qionghui Liu and Yifei Sun and Chao Yu and Rui Wang. *IEEE Wireless Commun. Lett.*, 2026. DOI `10.1109/LWC.2026.3663501`
- **상태** — PUBLISHED — IEEE WCL 2026, 15:1807-1811 (dblp journals/wcl/JiLLSYW26); 디스크 보유본은 arXiv:2602.08203 프리프린트  ·  **등급** — P
- **PDF** — `/data/public/sionna_jeong/papers_isac_sionna/2602.08203__ji_cellular-uav-bistatic.pdf`
- **조명원 / 기준신호** — source=상용 LTE 기지국 2대 · reference_signal=다운링크(수신기 2대가 각자 대응 BS 를 본다) · band=LTE
- **표적 표현** — 실물 UAV · 본문 미추출 · 실물 비행
- **엔진 / 실측** — 실측. 두 방향의 바이스태틱 도플러로 속도를 얻고 궤적을 재구성.
- **무엇을 무엇에 대해 검증했나** — 궤적 추적 오차 ↔ 복잡 궤적의 기준값(본문 미추출)
- **핵심 수치** — `bs_to_target_distance_m` = 200, `rx_to_uav_distance_m` = 30, `tracking_error_cm_at_90pct` = 50
- **우리와의 관계** — ⭐ C+D x LTE. 다중 수신기 결합의 최신 실측이며, '거리분해능보다 좋은 정확도' 주장이 우리 분해능 서사와 정면으로 부딪힌다.
- ⚠ ⚠ PREPRINT.
- ⚠ 이 정확도는 도플러 적분에서 오는 것이지 거리 측정에서 오는 것이 아니다. 우리 ΔR 논의와 혼동 금지.
- ⚠ PDF 미확보. 서지만 dblp 확인.
  > “it is demonstrated by experiments that the tracking errors are below 50 centimeters for 90% of the complicated trajectories, when the distances between the UAV and sensing receivers are less than 30 meters. Note this accuracy is significantly better than the ranging resolution of LTE signals” — *Abstract*
- **초안 문장** — 두 대의 LTE 기지국과 두 대의 패시브 수신기로 서로 다른 방향의 바이스태틱 도플러를 재면 LTE 의 거리분해능보다 정밀한 UAV 궤적 재구성이 가능하다(Ji 외, IEEE WCL 15:1807-1811, 2026).

#### `dan_lte_pbr_joe19`  — LTE-Based Passive Radar for Drone Detection and Its Experimental Results

- **서지** — Y. Dan and J. Yi and X. Wan and Y. Zhang. *J. Eng.*, 2019. DOI `10.1049/joe.2019.0583`
- **상태** — PUBLISHED — The Journal of Engineering (IET IRC 2018)  ·  **등급** — P
- **PDF** — `/data/public/jeong/papers/LTE/19_LTE-based passive radar for drone detection and its experimental results.pdf`
- **조명원 / 기준신호** — source=LTE FDD eNB(비협력) · reference_signal=기준채널 replica 정합필터 · band=약 1.8 GHz (본문 lambda 약 0.16 m)
- **표적 표현** — 소형 UAV · 실물
- **엔진 / 실측** — 실측
- **무엇을 무엇에 대해 검증했나** — 검출 ↔ 실비행
- **핵심 수치** — `lambda_m` = 0.16, `assumed_max_target_speed_m_s` = 20, `resulting_max_doppler_Hz` = 250
- **우리와의 관계** — C x LTE 의 초기 실험 레퍼런스.
- ⚠ ⭐ 이 인용문은 코퍼스 전형이다 - 표적 도플러는 계산하되 시스템 상한은 묻지 않는다. 우리 관측가능성 논지의 근거로 쓸 수 있다.
  > “Since UAV's maximum velocity is 20 m/s and wave length of adopted LTE is around 0.16 m, maximum Doppler caused by target manoeuvring is 250 Hz.” — *본문*
- **초안 문장** — LTE 다운링크를 조명원으로 쓴 패시브 드론 검출은 Dan 외(J. Eng., IET IRC 2018)에서 이미 실험적으로 보고되었다.

#### `sun_uav_tracking_ojcoms25`  — An Experimental Study of Passive UAV Tracking with Digital Arrays and Cellular Downlink Signals

- **서지** — Y. Sun and C. Yu and Y. Luo and T. X. Han and H. Tan and R. Wang and F. C. M. Lau. *IEEE Open J. Commun. Soc.*, 2025. DOI `10.1109/OJCOMS.2025.3558430`
- **상태** — PUBLISHED — IEEE OJ-COMS 2025  ·  **등급** — P  ·  ⚠ **BibTeX INCOMPLETE**
- **PDF** — `/data/public/jeong/papers/LTE/22_Passive Drone Localization Using LTE Signals.pdf` · `/data/public/jeong/papers/LTE/25_An Experimental Study of Passive UAV Tracking With Digital Arrays and Cellular Downlink Signals.pdf` · `/data/public/jeong/papers/Wifi/21_Fusing Measurements from Wi-Fi Emission-Based and Passive Radar Sensors for Short-Range Surveillance.pdf`
- **조명원 / 기준신호** — source=(a) 상용 LTE eNB (b) ⚠ 자기 USRP N210 이 LTE eNB 를 모사 (c) 상용 WiFi AP · reference_signal=기준 채널 + CAF · band=(a) LTE (c) 2.4 GHz
- **표적 표현** — UAV / 드론 · 본문 미명시 · 실물
- **엔진 / 실측** — 실측
- **무엇을 무엇에 대해 검증했나** — 추적/측위 ↔ 실비행
- **우리와의 관계** — C x LTE. 디지털 배열 2대로 바이스태틱 UAV 궤적을 추적한 실측 — 우리 다중 Rx 결합의 실측 상대.
- ⚠ ⚠ (a) 의 'the reference and surveillance arrays of the system are co-located' 는 수신 배열 둘이 붙어 있다는 뜻이다. TX-RX 동일지점(Config B)이 아니다.
- ⚠ LaSen 은 이 계열([45])을 '트래픽 불확실성 미처리' 로 비판한다.
  > “Passive sensing with one illuminator and one receiver is referred to as bistatic sensing, and sensing with more than one illuminator or receiver is referred to as multi-static sensing.” — *(a) 본문*
  > “In general, we consider a multi-static passive localization setting in a 3-D Cartesian coordinate system.” — *(b) 본문*
- **초안 문장** — 상용 LTE 다운링크와 디지털 배열 수신기로 UAV 궤적을 바이스태틱으로 추적한 실측이 보고되어 있다(Sun 외, IEEE OJ-COMS 2025).

#### `taylor_lte_pbr_radar23`  — Experimental UAV Detection Using 4G-LTE-Based Passive Radar

- **서지** — A. Taylor and D. Poullin. *Proc. IEEE Radar Conf. (RadarConf23)*, 2023. DOI `10.1109/RADAR54928.2023.10371153`
- **상태** — PUBLISHED — IEEE RADAR 2023  ·  **등급** — P
- **PDF** — `/data/public/jeong/papers/LTE/23_Experimental UAV detection using 4G-LTE-based passive Radar.pdf` · `/data/public/jeong/papers/LTE/25_Drone_Detection_Using_4G-LTE-Based_Passive_Radar.pdf`
- **조명원 / 기준신호** — source=상용 LTE eNB(비협력, Tx1 우세) · reference_signal=기준 채널(H/V 편파 2채널로 기준신호 추정) + 파일럿 제한 거리-도플러 · band=fc = 1.87 GHz(비행 1-3) 또는 약 2.6 GHz(비행 4-6) · sampling_MHz=25 · resample_MHz=30.72
- **표적 표현** — 실물 드론 · DJI Phantom 3 (TAES 실험) · 실물 비행, 약 10 m/s
- **엔진 / 실측** — 실측. 클러터 제거 -> 압축 -> lowest-of CA-CFAR.
- **무엇을 무엇에 대해 검증했나** — 검출과 거리·속도 ↔ 실비행 기록
- **핵심 수치** — `carrier_GHz` = [1.87, 2.6], `sampling_MHz` = 25, `CPI_ms` = 125, `target_speed_m_s` = 10, `max_bistatic_speed_m_s` = 13, `flight2_max_m_s` = 8.2, `range_span_m` = [145, 241]
- **우리와의 관계** — C x LTE. TAES 2025 판의 회의 선행판 — 같은 실험의 초기 보고.
- ⚠ ⚠ TAES 논문 안의 'active system is studied, with colocated transmitter and receiver' 문장은 인용문헌 소개이지 이 논문의 배치가 아니다.
- ⚠ ⚠ C11(TAES 2025)과 반드시 구별 (E2).
  > “The target used was a DJI Phantom 3, evolving in a rather quiet area, without obstacles, at a velocity of about 10 m/s. For Doppler processing, a 125 ms coherent integration time was used.” — *TAES p.6*
  > “the maximum bistatic speed (also with respect to the receiver) is close to 13 m/s, except for flight 2 where the drone speed does not exceed 8.2 m/s.” — *TAES 본문*
  > “This procedure, known as lowest of cell-averaging CFAR [38], enables to avoid missed detection caused by residual sidelobes of the clutter.” — *TAES p.6*
- **초안 문장** — 같은 ONERA 실험의 회의 선행판이 4G-LTE 패시브 레이더의 UAV 검출을 먼저 보고한다(Taylor & Poullin, IEEE RADAR 2023).

#### `sun_lte_poster_wisec22`  — POSTER: Passive Drone Localization Using LTE Signals

- **서지** — M. Sun and Z. Guo and M. Li and R. Gerdes. *Proc. 15th ACM Conf. Security and Privacy in Wireless and Mobile Networks (WiSec)*, 2022. DOI `10.1145/3507657.3529658`
- **상태** — PUBLISHED — ACM WiSec 2022 포스터  ·  **등급** — P
- **PDF** — `/data/public/jeong/papers/LTE/22_Passive Drone Localization Using LTE Signals.pdf` · `/data/public/jeong/papers/LTE/25_An Experimental Study of Passive UAV Tracking With Digital Arrays and Cellular Downlink Signals.pdf` · `/data/public/jeong/papers/Wifi/21_Fusing Measurements from Wi-Fi Emission-Based and Passive Radar Sensors for Short-Range Surveillance.pdf`
- **조명원 / 기준신호** — source=(a) 상용 LTE eNB (b) ⚠ 자기 USRP N210 이 LTE eNB 를 모사 (c) 상용 WiFi AP · reference_signal=기준 채널 + CAF · band=(a) LTE (c) 2.4 GHz
- **표적 표현** — UAV / 드론 · 본문 미명시 · 실물
- **엔진 / 실측** — 실측
- **무엇을 무엇에 대해 검증했나** — 추적/측위 ↔ 실비행
- **우리와의 관계** — C(+D) x LTE. ⚠ '패시브' 인데 조명원이 자기 USRP N210 이다 — 조명원 소유권 축의 경계 사례.
- ⚠ ⚠ (a) 의 'the reference and surveillance arrays of the system are co-located' 는 수신 배열 둘이 붙어 있다는 뜻이다. TX-RX 동일지점(Config B)이 아니다.
  > “Passive sensing with one illuminator and one receiver is referred to as bistatic sensing, and sensing with more than one illuminator or receiver is referred to as multi-static sensing.” — *(a) 본문*
  > “In general, we consider a multi-static passive localization setting in a 3-D Cartesian coordinate system.” — *(b) 본문*
- **초안 문장** — '패시브'로 소개되는 실험 가운데 상당수는 조명원을 자기 SDR 로 대체해 파형을 이미 알고 있으므로(Sun 외, WiSec 2022), 상용망 상시 신호만 쓰는 구성과 구분해서 인용해야 한다.

#### `maksymiuk_renyi_rs22` ⭐⭐⭐ — R\'enyi Entropy-Based Adaptive Integration Method for 5G-Based Passive Radar Drone Detection

- **서지** — R. Maksymiuk and K. Abratkiewicz and P. Samczyński and M. Plotka. *Remote Sens.*, 2022. DOI `10.3390/rs14236146`
- **상태** — PUBLISHED, open access CC BY — MDPI Remote Sensing 14(23)  ·  **등급** — P
- **PDF** — `/data/public/jeong/papers/5G/22_Rényi Entropy-Based Adaptive Integration Method for 5G-Based Passive Radar Drone Detection.pdf`
- **조명원 / 기준신호** — source=협력 5G 망(로츠 공대 캠퍼스)의 기지국 · reference_signal=기준 채널 + 감시 채널, 업링크 제거 -> 필터링 -> 클러터 제거 -> CAF -> CFAR · band=약 3.44 GHz · receiver=Ettus USRP X310, GPS 동기, 감시채널 증폭 20 dB 이상 / 기준채널 약 10 dB
- **표적 표현** — 실물 드론 · DJI M600 PRO (폭·길이 약 1 m, 높이 약 40 cm, 플라스틱) · 실물 비행, GPS 로거 지상진리
- **엔진 / 실측** — 실측 + 시뮬레이션. Renyi 엔트로피로 다운링크 자원이 조밀하게 할당된 시간구간을 골라 적분한다.
- **무엇을 무엇에 대해 검증했나** — 적응 적분 방식 ↔ 시뮬레이션 신호와 실측 신호 양쪽
- **핵심 수치** — `carrier_GHz` = 3.44, `poland_single_operator_bandwidth_MHz` = 80, `poland_five_operators_bandwidth_MHz` = 400, `best_case_range_resolution_m` = 0.75, `cfar_pfa_used` = [0.0001, 1e-06, 1e-08], `ssb_only_repetition_period_ms_range` = [5, 160], `first_reported_flight_duration_min` = 1
- **우리와의 관계** — ⭐⭐ C x 5G. 우리 '점유(occupancy) 대가' 서사(G1/G2/G3)의 가장 강한 외부 앵커. 그리고 SSB 단독일 때의 반복주기 5-160 ms 를 명시한 게재 문헌.
- ⚠ 이 논문은 반복주기를 '제약'으로 지목할 뿐 무모호 속도 식을 쓰지 않는다. 우리 v_max 법칙의 근거로 인용하면 E3 - '반복주기가 제약이라는 지적' 까지만 인용할 것.
- ⚠ 표적이 협력 드론이고 조명원도 협력 5G 망이다. 완전 비협력 시나리오가 아니다.
- ⚠ LaSen 은 이 계열을 '자원이 꽉 찬 드문 구간에만 센싱하면 잦고 긴 센싱 공백이 생긴다' 고 비판한다 — 우리도 같은 비판을 받는다.
  > “This paper presents the first successful drone detection results using a 5G network as a source of illumination in a passive radar system.” — *Abstract p.1*
  > “The resource allocation is strongly related to a network load and has a crucial influence on 5G-based passive radar range resolution and detection capabilities.” — *Abstract p.1*
  > “However, the proposed approach is functional as long as the content is present in the downlink transmission. Otherwise, the 5G network only generates synchronization pulses with a relatively low repetition rate (from 5 to 160 ms), which entails significant limitations [35].” — *Conclusions p.23*
- **초안 문장** — 5G 패시브 레이더의 거리분해능과 검출거리는 망 부하에 따른 자원 할당량에 종속되며, 다운링크에 데이터가 없으면 망은 반복주기 5-160 ms 의 동기 신호만 내보내 심각한 제약을 남긴다(Maksymiuk 외, Remote Sensing 14(23):6146, 2022).

#### `jopanya_ssb_spawc25` ⭐⭐⭐ — Utilizing 5G NR SSB Blocks for Passive Detection and Localization of Low-Altitude Drones

- **서지** — P. Jopanya and D. P. Moya Osorio. *Proc. IEEE 26th Int. Workshop Signal Processing Advances in Wireless Communications (SPAWC)*, 2025. DOI `10.1109/SPAWC66079.2025.11143316`
- **상태** — PUBLISHED — IEEE SPAWC 2025; 프리프린트 arXiv:2504.02641v3  ·  **등급** — P
- **PDF** — `/data/public/jeong/papers/5G/25_Utilizing 5G NR SSB Blocks for Passive Detection and Localization of Low-Altitude Drones.pdf`
- **조명원 / 기준신호** — source=같은 망의 피어 기지국(BsA 송신, BsB 수신) · reference_signal=SSB - 표준화된 기지 시퀀스 · band=5G NR
- **표적 표현** — 저고도 드론 · ⭐ 시뮬레이션 점표적. 2D-FFT 추정기를 CRB 와 비교.
- **엔진 / 실측** — 시뮬레이션
- **무엇을 무엇에 대해 검증했나** — 추정기 성능 ↔ Cramer-Rao bound
- **핵심 수치** — `unambiguous_range_rule` = d_u <= c*T_s, `unambiguous_velocity_rule` = |v_u| <= lambda_c*f_Delta/2
- **우리와의 관계** — ⭐⭐ C x 5G. 우리 헤드라인이 실제로 겨루는 상대이자 리뷰어가 가장 먼저 찌를 지점.
- ⚠ ⭐ intra-burst 심볼축 != inter-burst 반복축. 규약도 전폭이라 계수 2배. 환산 없이 나란히 적으면 E3.
- ⚠ 'passive' 는 기하만 뜻한다 - 파형은 알려져 있다.
- ⚠ ⚠ 규약 위험: \|v_u\| <= lambda*f_Delta/2 는 심볼축(f_Delta = subcarrier spacing) 전폭 규약. 우리 반쪽폭 규약 lambda*PRF_ref/4 와 (i) 계수 2배, (ii) 축(심볼축 vs 상시 기준신호 반복축)이 모두 다르다. 환산 없이 나란히 적으면 E3.
  > “The unambiguous range is a detectable distance given by the propagated distance of one symbol duration as d_u <= c*T_s. The unambiguous velocity is the range of maximum and minimum relative radial velocities, which can be defined as \|v_u\| <= lambda_c*f_Delta/2.” — *본문*
- **초안 문장** — SSB 기반 패시브 바이스태틱 센싱에서 무모호 속도를 명시한 선행이 있으나(Jopanya & Osorio, SPAWC 2025), 그 식은 SSB 버스트 내부의 OFDM 심볼 간격을 슬로타임으로 삼은 것이며 SSB 반복 주기가 정하는 상한과는 다른 축이다.

#### `abratkiewicz_ssb_jstars23` ⭐⭐⭐ — SSB-Based Signal Processing for Passive Radar Using a 5G Network

- **서지** — K. Abratkiewicz and A. Księżyk and M. Plotka and P. Samczyński and J. Wszołek and T. P. Zieliński. *IEEE J. Sel. Topics Appl. Earth Observ. Remote Sens.*, 2023
- **상태** — PUBLISHED — JSTARS 16 (2차 출처 서지; PDF 미확보)  ·  **등급** — S  ·  ⚠ **BibTeX INCOMPLETE**
- **PDF** — 디스크에 없음
- **조명원 / 기준신호** — 5G NR SSB
- **우리와의 관계** — ⭐ SSB 를 '펄스' 로 보는 관점의 표준 참조 — 우리 v_max = lambda*PRF_ref/4 서사와 정확히 같은 물리. JSTARS 는 우리 타깃 저널 목록에도 있다.
- ⚠ LaSen 참고문헌 [5] + 웹 서지로만 확인. 원문 미독 → 본문 문장 인용 금지 (E4/E6).
- **초안 문장** — 5G SSB 를 펄스처럼 다루는 패시브 레이더 신호처리는 이미 별도로 보고되어 있다(Abratkiewicz 외, IEEE JSTARS 16:3469-3484, 2023).

#### `nataraja_bistatic_isac_tvt25` ⭐⭐ — Integrated Sensing and Communication (ISAC) for Vehicles: Bistatic Sensing with 5G NR

- **서지** — N. K. Nataraja and S. Sharma and K. Ali and F. Bai and R. Wang and A. F. Molisch. *IEEE Trans. Veh. Technol.*, 2025. DOI `10.1109/TVT.2024.3514573`
- **상태** — PUBLISHED — IEEE TVT 74(4)  ·  **등급** — B
- **PDF** — 디스크에 없음
- **조명원 / 기준신호** — 5G NR
- **우리와의 관계** — LaSen 본문에서 'bistatic' 이라는 단어가 나오는 유일한 자리가 이 참고문헌 [37] 이다(LaSen 자신은 모노스태틱). 5G-NR 바이스태틱의 표준 참조.
- ⚠ ⚠ 표적이 차량이지 드론이 아니다. 드론 결과로 인용 금지.
- **초안 문장** — 5G NR 을 쓰는 바이스태틱 ISAC 는 차량 맥락에서 먼저 체계적으로 정리되었다(Nataraja 외, IEEE TVT 74(4), 2025).

#### `maksymiuk_5g_irs23`  — 5G Network-Based Passive Radar for Drone Detection

- **서지** — R. Maksymiuk and M. Plotka and K. Abratkiewicz and P. Samczyński. *Proc. Int. Radar Symp. (IRS)*, 2023
- **상태** — PUBLISHED — IRS 2023  ·  **등급** — P  ·  ⚠ **BibTeX INCOMPLETE**
- **PDF** — `/data/public/jeong/papers/5G/23_5G Network-Based Passive Radar for Drone Detection.pdf` · `/data/public/jeong/papers/5G/25_UAV Intrusion Detection with Passive Radar Based on the 5G Network.pdf`
- **조명원 / 기준신호** — source=상용 5G gNB · reference_signal=기준 채널 + 감시 채널, CAF · band=3.44 GHz 반송파, 최대 38.16 MHz 대역폭
- **표적 표현** — 드론 / UAV 침입 · 본문 미명시 · 실물
- **엔진 / 실측** — 실측
- **무엇을 무엇에 대해 검증했나** — 검출 ↔ 실비행
- **핵심 수치** — `carrier_GHz` = 3.44, `bandwidth_MHz` = 38.16, `bistatic_range_resolution_m` = 7.8, `integration_time_ms` = 100
- **우리와의 관계** — C x 5G. 우리 5G 대역·대역폭(3.44 GHz, 최대 38.16 MHz) 설정의 실측 대조군이자 바이스태틱 기호 규약(L, beta, R1, R2)의 표준.
- ⚠ 두 편을 한 레코드로 묶었다. 인용 시 분리할 것.
  > “The bistatic Doppler frequency, resulting from the target's motion, is given by fb = (1/lambda)(dR1/dt + dR2/dt).” — *Asilomar2025 본문*
  > “maximum bistatic range resolution of approximately 7.8 m” — *IRS2023 본문*
- **초안 문장** — 상용 5G gNB(3.44 GHz, 최대 38 MHz)를 조명원으로 한 패시브 드론 검출은 실측으로 확립되어 있으며 바이스태틱 거리분해능은 약 7.8 m 수준이다(Maksymiuk 외, IRS 2023).

#### `ai_5g_piers21`  — Passive Detection Experiment of UAV Based on 5G New Radio Signal

- **서지** — X. Ai and L. Zhang and Y. Zheng and F. Zhao. *Proc. PhotonIcs and Electromagnetics Research Symp. (PIERS)*, 2021. DOI `10.1109/PIERS53385.2021.9695141`
- **상태** — PUBLISHED — PIERS 2021  ·  **등급** — P
- **PDF** — `/data/public/jeong/papers/5G/21_Passive Detection Experiment of UAV Based on 5G New Radio Signal.pdf` · `/data/public/jeong/papers/5G/23_5G_Spectrum_Learning-Based_Passive_UAV_Detection_in_Urban_Scenario.pdf`
- **조명원 / 기준신호** — source=5G NR · reference_signal=(a) 기준 + 감시 채널 (b) 스펙트럼 학습 · band=5G NR
- **표적 표현** — UAV · (a) 실측 (b) 미상
- **엔진 / 실측** — (a) 실측 (b) 학습 기반
- **무엇을 무엇에 대해 검증했나** — (a) 검출 실험 (b) 분류 성능 ↔ 본문 미확인
- **핵심 수치** — `ai_delay_ambiguity_us` = 66.7
- **우리와의 관계** — C x 5G 의 연도 우선권. 5G 패시브 UAV 검출 실험의 최초 보고 계열.
- ⚠ (b) 의 config 는 UNCLEAR 이며 그 자체가 분류표의 유용한 결과다.
  > “By utilizing the existing communication signals as the illuminators, passive radar can be implemented for UAV detection, where the signals are separated as reference signals and surveillance signals for cross correlation calculation [21-23].” — *(b) 본문*
- **초안 문장** — 5G NR 을 조명원으로 한 패시브 UAV 검출 실험은 2021년부터 보고된다(Ai 외, PIERS 2021).

#### `maksymiuk_5g_asilomar25`  — UAV Intrusion Detection with Passive Radar Based on the 5G Network

- **서지** — R. Maksymiuk and K. Abratkiewicz and P. Samczyński. *Proc. 59th Asilomar Conf. Signals, Systems, and Computers*, 2025. DOI `10.1109/IEEECONF67917.2025.11443758`
- **상태** — PUBLISHED — Asilomar 2025  ·  **등급** — P  ·  ⚠ **BibTeX INCOMPLETE**
- **PDF** — `/data/public/jeong/papers/5G/23_5G Network-Based Passive Radar for Drone Detection.pdf` · `/data/public/jeong/papers/5G/25_UAV Intrusion Detection with Passive Radar Based on the 5G Network.pdf`
- **조명원 / 기준신호** — source=상용 5G gNB · reference_signal=기준 채널 + 감시 채널, CAF · band=3.44 GHz 반송파, 최대 38.16 MHz 대역폭
- **표적 표현** — 드론 / UAV 침입 · 본문 미명시 · 실물
- **엔진 / 실측** — 실측
- **무엇을 무엇에 대해 검증했나** — 검출 ↔ 실비행
- **핵심 수치** — `carrier_GHz` = 3.44, `bandwidth_MHz` = 38.16, `bistatic_range_resolution_m` = 7.8, `integration_time_ms` = 100
- **우리와의 관계** — C x 5G. 같은 그룹의 후속 실험 — UAV 침입 검출로 확장한 최신판.
- ⚠ 두 편을 한 레코드로 묶었다. 인용 시 분리할 것.
  > “The bistatic Doppler frequency, resulting from the target's motion, is given by fb = (1/lambda)(dR1/dt + dR2/dt).” — *Asilomar2025 본문*
  > “maximum bistatic range resolution of approximately 7.8 m” — *IRS2023 본문*
- **초안 문장** — 같은 그룹의 후속 실험은 5G 망 기반 패시브 레이더를 UAV 침입 검출로 확장한다(Maksymiuk 외, Asilomar 2025).

#### `lin_5g_spectrum_iccc23`  — 5G Spectrum Learning-Based Passive UAV Detection in Urban Scenario

- **서지** — L. Lin and N. Yu and Y. Wang and Z. Shi. *Proc. IEEE/CIC Int. Conf. Communications in China (ICCC)*, 2023. DOI `10.1109/ICCC57788.2023.10233342`
- **상태** — PUBLISHED — IEEE/CIC ICCC 2023  ·  **등급** — P
- **PDF** — `/data/public/jeong/papers/5G/21_Passive Detection Experiment of UAV Based on 5G New Radio Signal.pdf` · `/data/public/jeong/papers/5G/23_5G_Spectrum_Learning-Based_Passive_UAV_Detection_in_Urban_Scenario.pdf`
- **조명원 / 기준신호** — source=5G NR · reference_signal=(a) 기준 + 감시 채널 (b) 스펙트럼 학습 · band=5G NR
- **표적 표현** — UAV · (a) 실측 (b) 미상
- **엔진 / 실측** — (a) 실측 (b) 학습 기반
- **무엇을 무엇에 대해 검증했나** — (a) 검출 실험 (b) 분류 성능 ↔ 본문 미확인
- **핵심 수치** — `ai_delay_ambiguity_us` = 66.7
- **우리와의 관계** — ⚠ '기하 미상' 칸의 정직한 표본 — 학습 기반 논문이 송수신 배치를 명시하지 않는 경향을 보여준다.
- ⚠ (b) 의 config 는 UNCLEAR 이며 그 자체가 분류표의 유용한 결과다.
  > “By utilizing the existing communication signals as the illuminators, passive radar can be implemented for UAV detection, where the signals are separated as reference signals and surveillance signals for cross correlation calculation [21-23].” — *(b) 본문*
- **초안 문장** — 학습 기반 5G 패시브 UAV 검출 연구의 상당수는 송수신 기하를 본문에 명시하지 않는다(Lin 외, IEEE/CIC ICCC 2023).

#### `huang_uplink_srs_arxiv26` ⭐⭐ — Fuse-then-Detect for Passive UAV Localization Using Multi-UE 5G Uplink Signals

- **서지** — W. Huang and N. González-Prelcic and V. Ratnam and M. Bayraktar and C. J. Zhang. *arXiv 2607.11955*, 2026. arXiv:`2607.11955`
- **상태** — PREPRINT  ·  **등급** — P  ·  ⚠ **BibTeX INCOMPLETE**
- **PDF** — `/data/public/sionna_jeong/papers_isac_sionna/new_0731/2607.11955__fuse-then-detect-passive-uav-5g-uplink.pdf`
- **조명원 / 기준신호** — source=다수 UE 의 업링크 송신(망 인프라 재사용) · reference_signal=SRS 파일럿 - 기지 시퀀스 · band=5G NR
- **표적 표현** — 저고도 UAV · 본문 미추출 · 본문 미추출(시뮬레이션으로 보임 - 미확인)
- **엔진 / 실측** — 본문 미추출 - UNVERIFIED
- **무엇을 무엇에 대해 검증했나** — 본문 미추출 ↔ 본문 미추출
- **우리와의 관계** — ⭐ 우리 조명원 축에 없는 칸 - 업링크. 우리가 다운링크 상시 신호만 다룬다는 스코핑 문장의 근거가 된다.
- ⚠ ⚠ PREPRINT. 초록만 정독했고 실험 설정·표적 표현·검증은 이번 라운드에서 추출하지 않았다 - UNVERIFIED 로 표시된 항목을 채우지 말 것.
  > “Most prior work exploits monostatic sensing or bistatic/multistatic configurations based on downlink measurements. To the best of our knowledge, this paper presents the first uplink framework, where multiple user equipments (UEs) transmit sounding reference signal (SRS) pilots and the base station (BS) receives the UAV-scattered echoes.” — *Abstract*
- **초안 문장** — 패시브 UAV 센싱은 대부분 모노스태틱이거나 다운링크 기반 바이스태틱/멀티스태틱이며, 업링크 SRS 를 조명원으로 삼는 구성은 최근에야 제안되었다(Huang 외, arXiv:2607.11955).

#### `needle_haystack_mobisys26` ⭐⭐⭐ — Needle in a Haystack: Tracking UAVs from Massive Noise in Real-World 5G-A Base Station Data

- **서지** — Chengzhen Meng and Chenming He and Yidong Jiang and Xiaoran Fan and Dequan Wang and Lingyu Wang and Jianmin Ji and Yanyong Zhang. *Proc. 24th Annu. Int. Conf. Mobile Systems, Applications and Services (MobiSys)*, 2026. DOI `10.1145/3745756.3809186`
- **상태** — PUBLISHED — ACM MobiSys 2026; 프리프린트 arXiv:2603.29187  ·  **등급** — B
- **PDF** — 디스크에 없음
- **조명원 / 기준신호** — 5G-A base station (live network)
- **우리와의 관계** — ⭐⭐ 2026 최상위 시스템 학회가 실망(live network) 5G-A 데이터로 UAV 를 추적한다 — 우리 챔버 시뮬레이션의 정반대 극. 우리 한계(무향실·시뮬)를 정직하게 대비시킬 최적의 문헌.
- ⚠ ⚠ 회의판(MobiSys 2026)과 arXiv 판(2603.29187)이 둘 다 dblp 에 있다. 반드시 구별 (E2).
- **초안 문장** — 실제 운용 중인 5G-Advanced 기지국 데이터에서 UAV 를 골라내는 문제는 2026년 MobiSys 에서 다루어졌으며(Meng 외, pp.14-27), 통제된 시뮬레이션과 실망 데이터 사이의 간극을 그대로 보여준다.

#### `rzewuski_nato21` ⭐⭐⭐ — Drone Detectability Feasibility Study Using Passive Radars Operating in WIFI and DVB-T Band

- **서지** — S. Rzewuski and K. Kulpa and P. Pachwicewicz and M. Malanowski and B. Salski. *NATO STO Meeting Proc. STO-MP-MSG-SET-183*, 2021
- **상태** — PUBLISHED — NATO STO 프로시딩 (모든 쪽 헤더 STO-MP-MSG-SET-183)  ·  **등급** — P  ·  ⚠ **BibTeX INCOMPLETE**
- **PDF** — `/data/public/jeong/papers/Wifi/21_Drone Detectability Feasibility Study using Passive Radars Operating in WIFI and DVB-T Band.pdf`
- **조명원 / 기준신호** — source=WiFi AP 와 DVB-T(비협력) · reference_signal=기준 빔 + 감시 빔 · band=2.4 GHz WiFi 와 UHF DVB-T · dvbt_duty_note=실험 신호 duty factor 18%
- **표적 표현** — 실물 드론 + 그 드론의 EM 모델 · Parrot AR.Drone 2.0 (폴리프로필렌 기체, 4 로터) · ⭐ 두 가지 - FDTD 수치 모델(QuickWave-3D)과 실비행
- **엔진 / 실측** — FDTD (QuickWave-3D) 로 mono/bi RCS 계산 + 커버리지 예산 + WiFi/DVB-T OTA 검출 실험
- **무엇을 무엇에 대해 검증했나** — 시뮬레이션 RCS 특성 ↔ 저자들의 이전 WiFi 대역 실측 [ref 2] 과의 비대칭성 일치
- **핵심 수치** — `wifi_rcs_range_dBsm` = [-40, 0], `wifi_rcs_average_dBsm` = -20, `dvbt_rcs_range_dBsm` = [-60, -20], `detection_threshold_dB` = 8, `ota_bistatic_detection_range_m` = 50, `dvbt_duty_factor_percent` = 18
- **우리와의 관계** — ⭐⭐ C x WiFi + E. 우리 격자에서 기하 두 칸과 조명원 한 칸을 한 논문이 동시에 채운 유일 사례이자, 산란 계산을 바이스태틱으로 일반화해야 하는 이유의 문헌 근거.
- ⚠ 50 m 는 성능 한계가 아니다 - '조종자가 레이더 근처에 있어 드론이 더 멀리 날지 않았다'고 본문이 밝힌다.
- ⚠ RCS 값은 폴리프로필렌 기체의 것이다. 탄소섬유 기체에 그대로 옮기면 Semkin 이 보고한 7 dB 차이를 무시하게 된다.
- ⚠ FDTD 는 우리 SBR+PO 와 다른 solver 다. RCS 값을 직접 비교할 때 반드시 명시.
- ⚠ ⚠ 이번 세션에 재확인하지 않았다 - 이전 세션 확정 기록을 그대로 인용(grade S->P 재확인 권장).
  > “Mono- and bi-static radar cross-sections (RCS) of the Parrot AR.Drone 2.0 were computed with a finite-difference time-domain (FDTD) method implemented in the commercial software package, QuickWave-3D [2,3].” — *p.4*
  > “The most important is that the RCS range for WIFI band is between -40dBsm and 0dBsm (and average around -20dBsm). For DVB-T frequencies the RCS characteristics varies from -60dBsm to -20dBsm and rather increases with the frequency.” — *p.5*
  > “Experiment shows that it is possible to detect small size Parrot AR. Drone on bistatic distance equal to 50m.” — *p.9*
- **초안 문장** — 패시브 배치에서 표적 RCS 는 모노스태틱 값과 다르며, 소형 플라스틱 드론의 WiFi 대역 RCS 는 -40 ~ 0 dBsm(평균 약 -20 dBsm) 범위로 FDTD 계산과 OTA 검출(바이스태틱 50 m)이 함께 보고되어 있다(Rzewuski 외, NATO STO-MP-MSG-SET-183, 2021).

#### `fang_lora_drone_infocomw22` ⭐⭐ — Exploring LoRa for Drone Detection

- **서지** — Jian Fang and Zhiyi Zhou and Sunhaoran Jin and Lei Wang and Bingxian Lu and Zhenquan Qin. *Proc. IEEE INFOCOM Workshops*, 2022. DOI `10.1109/INFOCOMWKSHPS54753.2022.9798069`
- **상태** — PUBLISHED — IEEE INFOCOM Workshops 2022  ·  **등급** — B
- **PDF** — 디스크에 없음
- **조명원 / 기준신호** — LoRa
- **우리와의 관계** — 조명원 축을 WiFi/LTE/5G 밖으로 확장한 사례. LaSen 은 LoRa 의 '낮은 pulse repetition frequency' 때문에 속도 추정이 안 된다고 명시한다 — 우리 법칙의 또 다른 실사례.
- ⚠ INFOCOM 2022 Workshops, 2쪽 짜리다. 분량을 감안해 인용할 것.
- **초안 문장** — 조명원 축은 WiFi·LTE·5G 밖으로도 확장되어 LoRa 를 조명원으로 쓰는 시도까지 보고되었으나(Fang 외, IEEE INFOCOM Workshops 2022), 낮은 반복률 때문에 속도 추정이 성립하지 않는다는 지적이 뒤따른다(Yang 외, SenSys 2026).

#### `sneh_11ad_uav_icassp25` ⭐⭐ — IEEE 802.11ad-Aided 5-D Sensing with a UAV Swarm in Urban Environments

- **서지** — Akanksha Sneh and Shobha Sundar Ram and Kumar Vijay Mishra. *Proc. IEEE Int. Conf. Acoustics, Speech and Signal Processing (ICASSP)*, 2025. DOI `10.1109/ICASSP49660.2025.10889552`
- **상태** — PUBLISHED — ICASSP 2025  ·  **등급** — B
- **PDF** — 디스크에 없음
- **우리와의 관계** — ⭐ WiFi 규격 신호로 UAV 를 센싱하는 ICASSP 사례 — 우리 WiFi 모드의 신호처리학회 대응물. 저자에 S. S. Ram / K. V. Mishra(마이크로도플러·레이더 시뮬 계보).
- **초안 문장** — IEEE 802.11ad 규격 신호를 이용한 UAV 군집 센싱이 ICASSP 2025 에 보고되었다(Sneh 외).

#### `hisac_sensys24` ⭐⭐⭐ — HiSAC: High-Resolution Sensing with Multiband Communication Signals

- **서지** — Jacopo Pegoraro and Jesus O. Lacruz and Michele Rossi and Joerg Widmer. *Proc. 22nd ACM Conf. Embedded Networked Sensor Systems (SenSys '24)*, 2024. DOI `10.1145/3666025.3699357`
- **상태** — PUBLISHED — ACM SenSys 2024  ·  **등급** — P  ·  ⚠ **BibTeX INCOMPLETE**
- **PDF** — `/data/public/sionna_jeong/reference_library/2407.07023v2.pdf`
- **조명원 / 기준신호** — source=통신 시스템의 파일럿(5G-NR SSB 등)을 그대로 재사용 · reference_signal=여러 대역부분(BWP)의 SSB 를 점진적으로 결합해 위상 코히어런스를 맞춘다 · band=여러 GHz 에 걸친 비연속 서브밴드 · platform=RFSoC
- **표적 표현** — ⭐ 드론이 아니다 - 본문에 drone/UAV 가 0회 · 실측 표적
- **엔진 / 실측** — 실측 (RFSoC 구현)
- **무엇을 무엇에 대해 검증했나** — 초해상 거리 추정 ↔ 단일 대역 처리
- **핵심 수치** — `bistatic_resolution_formula_verbatim` = Delta_r = c/(2 B cos(pi/4))
- **우리와의 관계** — 우리 ΔR_b 규약 서술의 외부 대조. 그들은 이등분선 투영(cos 항 포함), 우리는 바이스태틱 거리합 축이다 - 모순이 아니라 축이 다르다.
- ⚠ ⭐ 이전 스윕이 이 논문의 식을 일반형 'Delta_r = c/[2B cos(beta/2)]' 로 적었으나, 내가 오늘 PDF 에서 확인한 것은 특정 기하의 'c/(2B cos(pi/4))' 뿐이다. 일반형으로 인용하려면 원문을 한 번 더 확인할 것(E3 위험).
- ⚠ ⚠ 드론 논문이 아니다. 드론 선행으로 인용 금지.
- ⚠ ⚠ 표적이 드론이 아니다(60 GHz 실내). 드론 결과로 인용 금지.
  > “Bi-static setting. We evaluate HiSAC's capability to estimate the targets' distances in a bi-static setting ... Note that the full band range resolution in this case is reduced to Delta_r = c/(2 B cos(pi/4))” — *p.11*
  > “Given that SSBs have a relatively narrow bandwidth, it is appealing to develop a system that can combine the SSBs transmitted by one or more radio cells to perform accurate mono-static ranging by exploiting the total frequency aperture over a wider bandwidth.” — *p.3*
  > “The corresponding ranging resolution for passive sensing also depends on the angle between the segments connecting the TX to the target and the target to the RX (bi-static angle), beta, as Delta_r = c/[2 B cos(beta/2)]. A mono-static system, with co-located TX and RX, gives Delta_r = c/(2B) which minimizes Delta_r with respect to beta.” — *sec.2*
- **초안 문장** — 바이스태틱 배치에서 거리분해능은 기하에 따라 c/(2B) 보다 나빠지며 이등분선 투영 계수가 붙는다(Pegoraro 외, ACM SenSys 2024).

#### `he_convex_clutter_arxiv25` ⭐⭐⭐ — Adaptive Clutter Suppression via Convex Optimization

- **서지** — Y. He and G. Kearney and M. Fardad. *arXiv 2512.24889*, 2025. arXiv:`2512.24889`
- **상태** — PREPRINT — 게재처 표기 없음  ·  **등급** — P
- **PDF** — `/data/public/sionna_jeong/papers_isac_sionna/2512.24889__he_caf-clutter-suppression.pdf`
- **조명원 / 기준신호** — source=기회 조명원 일반(방송·셀룰러·위성) · reference_signal=기준 채널 replica 를 시간·주파수 이동시킨 사전으로 CAF 를 구성 · band=3GPP TS 36.101 표준 기준측정채널(RMC) 10 MHz OFDM 파형을 MATLAB 으로 합성
- **표적 표현** — 이동 표적(드론 특정 아님) · ⭐ Monte Carlo 시뮬레이션의 무작위 표적/클러터
- **엔진 / 실측** — 시뮬레이션. ECA 식 '먼저 지우고 나중에 검출' 대신 CAF 면 왜곡을 최소화하는 이차계획으로 셀별 지연-도플러 필터를 합성.
- **무엇을 무엇에 대해 검증했나** — 검출률과 실제 달성 오경보율 ↔ 동일 시뮬레이션의 비적응 CAF 기준선
- **핵심 수치** — `gamma_optimal` = 0.98, `waveform` = 3GPP TS 36.101 RMC, 10 MHz OFDM, `table1_nominal_vs_achieved_Pfa` = {'1e-2': {'unadapted_Pd': 0.1627, 'unadapted_achieved_Pfa': 0.0413, 'adapted_Pd': 0.9999, 'adapted_achieved_Pfa': 0.0542}, '1e-4': {'unadapted_Pd': 0.0194, 'unadapted_achieved_Pfa': 0.0208, 'adapted_Pd': 0.9989, 'adapted_achieved_Pfa': 0.00696}, '1e-6': {'unadapted_Pd': 0.0033, 'unadapted_achieved_Pfa': 0.0141, 'adapted_Pd': 0.9908, 'adapted_achieved_Pfa': 5.46e-06}, '1e-8': {'unadapted_Pd': 0.0004, 'unadapted_achieved_Pfa': 0.01, 'adapted_Pd': 0.9721, 'adapted_achieved_Pfa': 0.0}, '1e-10': {'unadapted_Pd': 0.0, 'unadapted_achieved_Pfa': 0.0073, 'adapted_Pd': 0.9457, 'adapted_achieved_Pfa': 0.0}, '1e-12': {'unadapted_Pd': 0.0, 'unadapted_achieved_Pfa': 0.0053, 'adapted_Pd': 0.9192, 'adapted_achieved_Pfa': 0.0}}
- **우리와의 관계** — ⭐⭐ 우리 'CFAR 를 경험적 Pfa 로 교정한다' 는 절차의 유일한 외부 정량 근거. 표 1 은 설계 Pfa 1e-6 을 걸어도 클러터를 처리하지 않으면 실제 오경보율이 0.0141 로 4자리 어긋난다는 것을 보인다.
- ⚠ ⚠ PREPRINT, 시뮬레이션 전용, 표적은 드론이 아니다. '드론 검출에서 그렇다'로 옮기면 E1.
- ⚠ 표 1 의 두 Pfa 열(설계값 vs 달성값)을 절대 혼동하지 말 것.
  > “Monte Carlo simulations using common communication waveforms demonstrate strong clutter suppression, accurate CFAR calibration, and major detection-rate gains over the classical CAF.” — *Abstract*
  > “produces a DD map that remains metrically comparable to the canonical CAF, facilitating CFAR calibration and operator interpretation” — *p.2*
  > “[표 1 의 한 행을 재구성한 것이며 원문 문장이 아니다] Pfa(CFAR) = 10^-6 행: Unadapted Pd 0.0033 / Pfa 0.0141 ; gamma = 0.98 Pd 0.9908 / Pfa 5.46e-6” — *Table 1 (p.9)*
- **초안 문장** — 패시브 레이더에서 CFAR 의 설계 오경보율은 클러터를 제대로 다루지 않으면 실제 달성치와 몇 자릿수씩 어긋나며(설계 1e-6 에 대해 실제 0.0141), 지연-도플러 면을 왜곡하지 않는 억제를 거쳐야 비로소 교정이 성립한다(He 외, arXiv:2512.24889).

</details>

### 2.D — D · 멀티스태틱 / 망-협조형 바이스태틱 — 조명원이나 수신기가 여럿, 또는 조명원이 자기 사업자망  *(6편)*

| 인용키 | 논문 | 게재처 · 상태 | 연 | 조명원 | 표적 표현 | 엔진/실측 | 무엇을 검증했나 | 우리와의 관계 | 등급 |
|---|---|---|---|---|---|---|---|---|---|
| `geng_lte_multistatic_ietrsn20` ⭐⭐⭐ | LTE-Based Multistatic Passive Radar System for UAV Detection | IET Radar Sonar Navig.<br>*PUBLISHED* | 2020 | LTE | UAV · ⭐ 시뮬레이션만 - 모호함수 해석과 모의 검출 | 시뮬레이션 (실측 없음). Costas 주파수 부호 + P4 위상 부호로 미사용 자원격자에 파일럿을… | TLRS 파형의 모호함수 성질 ↔ 전 LTE 다운링크 신호와의 비교 | ⭐⭐ C+D x LTE. 우리 v_max 표와 나란히 놓을 수 있는 사실상 유일한 패시브 선행. | P |
| `fwa_cube_arxiv26` ⭐⭐⭐ | AI-Empowered Low-Altitude Economy: Cooperative Sensing with Fixed Wireless Ac… | arXiv 2605.07623<br>*PREPRINT* | 2026 | 5G NR | ⭐ UAV 를 금속 정육면체로 놓는다 · 'The UAV is modeled as a metallic cube loc… | Sionna RT PathSolver | UAV 영향 경로 라벨 ↔ ⭐ Sionna 자신이 준 경로 유형(확산 반사) | 드론을 금속 정육면체로 놓는 것이 표준 관행임을 보이는 표본. 우리 메시 기반 sigma(관측각) 결과와 대비할 최적 대조군. | P |
| `wu_miros_infocom26` | MIROS: Elusive Unauthorized AAV Positioning by Multi-View Radar-Vision Fusion | Proc. IEEE Conf. Computer Communications (INF…<br>*PUBLISHED* | 2026 | cellular (미분류) | — | — | — | 2026 INFOCOM 의 비인가 AAV 측위(레이더-비전 융합). 우리 RF-only 접근의 대비점. | B |
| `wang_passive_mimo_icassp21` ⭐⭐ | Parameter Estimation for Coherent Passive MIMO Radar with Unknown Transmit Si… | Proc. IEEE Int. Conf. Acoustics, Speech and S…<br>*PUBLISHED* | 2021 | 기회 조명원 일반 | — | — | — | ⭐ '레퍼런스를 모른다 + 직접경로가 지배한다' 는 config C 의 두 난제를 정식으로 다룬 ICASSP 논문. 우리 보류질문(2채널 CAF 승격)의 이론 근거 후보. | B |
| `viberg_separable_passive` | Separable Delay and Doppler Estimation in Passive Radar | arXiv 2601.15821<br>*⚠ UNVERIFIED VENUE* | 2026 | 기회 조명원 일반 | 느리게 움직이는 표적 일반 · 파라미터 추정 이론 | 이론 + 시뮬레이션(추정기 설계) | 지연·도플러 추정 정확도 ↔ 배치별 전 2D 탐색 방식 | C+D 처리 계열. 우리 CAF 계산 비용 논의의 인접 문헌. | P |
| `lam_6d_drone_infocom25` | 6D Self-Localization of Drones Using a Single Millimeter-Wave Backscatter Tag | Proc. IEEE Conf. Computer Communications (INF…<br>*PUBLISHED* | 2025 | mmWave FMCW (자기송신) | — | — | — | INFOCOM 계보에서 드론+mmWave 의 대표. 문제 방향이 반대(자기위치 vs 침입자 검출) — related-work 에서 '협조적 vs 비협조적' 축을 가를 때 쓴다. | B |

<details><summary><b>▸ 상세 카드 4편</b> — 서지 · 수치 · 인용문 · 초안 문장</summary>

#### `geng_lte_multistatic_ietrsn20` ⭐⭐⭐ — LTE-Based Multistatic Passive Radar System for UAV Detection

- **서지** — Z. Geng and R. Xu and H. Deng. *IET Radar Sonar Navig.*, 2020. DOI `10.1049/iet-rsn.2019.0452`
- **상태** — PUBLISHED — IET RSN 14(7)  ·  **등급** — P
- **PDF** — `/data/public/jeong/papers/LTE/20_LTE-based multistatic passive radar system for UAV detection.pdf`
- **조명원 / 기준신호** — source=상용 LTE FDD eNodeB 여러 대 · reference_signal=기준채널 + CRS + 자체 설계 파일럿(TLRS) · band=fc = 850 MHz 로 통일 가정
- **표적 표현** — UAV · ⭐ 시뮬레이션만 - 모호함수 해석과 모의 검출
- **엔진 / 실측** — 시뮬레이션 (실측 없음). Costas 주파수 부호 + P4 위상 부호로 미사용 자원격자에 파일럿을 심는다.
- **무엇을 무엇에 대해 검증했나** — TLRS 파형의 모호함수 성질 ↔ 전 LTE 다운링크 신호와의 비교
- **핵심 수치** — `fc_Hz` = 850000000.0, `MUV_full_waveform_m_s` = 2647, `velocity_resolution_m_s` = 18, `MUV_CRS_m_s` = 705, `blind_speed_spacing_m_s` = 1410, `MUV_TLRS_m_s` = 176.5, `TLRS_PRI_s` = 0.001, `MUR_TLRS_km` = 150, `range_resolution_TLRS_m` = 29.4, `velocity_resolution_TLRS_m_s` = 12.2
- **우리와의 관계** — ⭐⭐ C+D x LTE. 우리 v_max 표와 나란히 놓을 수 있는 사실상 유일한 패시브 선행.
- ⚠ ⚠ 규약이 전폭(v = lambda*PRF/2)이라 우리 반폭 값의 2배다. 환산 없이 나란히 적으면 E3.
- ⚠ ⚠ 논문이 MUV 를 CPI 탓으로 돌린 문장을 그대로 옮기면 물리적으로 틀린 진술을 옮기게 된다.
- ⚠ ⚠ CRS 기반 수치(1.67 km / 20.59 m/s)는 그들이 [13] 에서 재인용한 2차 수치다. 우리 문서에 옮기려면 [13] 원문을 열 것 (E6).
  > “Since the CPI is one radio frame (i.e. 10 ms), the maximum unambiguous velocity (MUV) is 2647 m/s and the velocity resolution is 18 m/s (i.e. 64.8 km/h) for fc = 850 MHz.” — *본문*
  > “an MUR of 150 km with a range resolution of 29.4 m and an MUV of 176.5 m/s (635.4 km/h) with a velocity resolution of 12.2 m/s are obtained” — *본문*
  > “when the CRS are used for the passive radar application, the maximum unambiguous range (MUR) and the velocity resolution are merely 1.67 km and 20.59 m/s, respectively [13]. Moreover, since the CRS are sparsely scheduled in the LTE downlink signal, the AF peaks associated with CRS are 12.56 dB lower than those associated with the LTE downlink signal [13].” — *intro*
- **초안 문장** — LTE 패시브 레이더의 무모호 속도는 조명 파형의 반복 구조에 따라 전 다운링크 2647 m/s, CRS 705 m/s, 자체 설계 파일럿 176.5 m/s 로 갈리며(Geng 외, IET RSN 2020), 이는 반복률이 상한을 정한다는 규칙을 전폭 규약으로 적은 것이다.

#### `fwa_cube_arxiv26` ⭐⭐⭐ — AI-Empowered Low-Altitude Economy: Cooperative Sensing with Fixed Wireless Access

- **서지** — *arXiv 2605.07623*, 2026. arXiv:`2605.07623`
- **상태** — PREPRINT — ⭐ 정정: 아카이브가 IEEE ICC Workshops 2026 폴더에 넣었으나 PDF 각주는 '제목이 다른 별개 논문' 이 부분 게재됐다고 말한다  ·  **등급** — P  ·  ⚠ **BibTeX INCOMPLETE**
- **PDF** — `/data/public/sionna_jeong/papers_isac_sionna/2605.07623__lowalt-cooperative-cube-csi.pdf`
- **조명원 / 기준신호** — source=고정무선접속(FWA) 망 · reference_signal=CSI · band=본문 참조
- **표적 표현** — ⭐ UAV 를 금속 정육면체로 놓는다 · 'The UAV is modeled as a metallic cube located at p = (x, y, 60)' · 정육면체 - 형상·재질·회전날개가 전부 사라진다
- **엔진 / 실측** — Sionna RT PathSolver
- **무엇을 무엇에 대해 검증했나** — UAV 영향 경로 라벨 ↔ ⭐ Sionna 자신이 준 경로 유형(확산 반사)
- **핵심 수치** — `uav_altitude_m` = 60, `xy_uniform_range_m` = [-75, 75]
- **우리와의 관계** — 드론을 금속 정육면체로 놓는 것이 표준 관행임을 보이는 표본. 우리 메시 기반 sigma(관측각) 결과와 대비할 최적 대조군.
- ⚠ ⚠ PREPRINT, 게재처는 2차 출처.
- ⚠ ⚠ 게재상태 오인용 위험 최고. 아카이브 폴더 위치를 믿지 말 것. ⚠ 'MDP 0.63%' 는 정육면체 표적·학습기반 수치라서 우리 Pd/Pfa 와 직접 비교 불가.
  > “The UAV is modeled as a metallic cube located at p = (x, y, 60), where x, y ~ U[-75, 75].” — *~p.9*
  > “the pair labels y(m,n) is derived from the path type provided by Sionna RT. As described in Sec. V-A1, UAV-affected paths are typically caused by diffuse reflections.” — *~p.9*
  > “The dataset is generated through ray-tracing, using OpenStreetMap (OSM), Blender, and Sionna RT [39].” — *p.8*
- **초안 문장** — 광선추적 기반 저고도 센싱 연구에서 UAV 는 흔히 금속 정육면체 한 개로 표현되며 표적 라벨조차 광선추적기가 반환한 경로 유형에서 유도된다(arXiv:2605.07623).

#### `wang_passive_mimo_icassp21` ⭐⭐ — Parameter Estimation for Coherent Passive MIMO Radar with Unknown Transmit Signals

- **서지** — Zhen Wang and Qian He. *Proc. IEEE Int. Conf. Acoustics, Speech and Signal Processing (ICASSP)*, 2021. DOI `10.1109/ICASSP39728.2021.9414746`
- **상태** — PUBLISHED — ICASSP 2021  ·  **등급** — B
- **PDF** — 디스크에 없음
- **우리와의 관계** — ⭐ '레퍼런스를 모른다 + 직접경로가 지배한다' 는 config C 의 두 난제를 정식으로 다룬 ICASSP 논문. 우리 보류질문(2채널 CAF 승격)의 이론 근거 후보.
- **초안 문장** — 송신 파형을 모르는 코히어런트 패시브 MIMO 레이더의 파라미터 추정은 정식으로 다루어져 있으며(Wang & He, ICASSP 2021), 이는 우리가 이상적 레퍼런스를 가정할 때 생략하는 문제를 정면으로 푼다.

#### `viberg_separable_passive`  — Separable Delay and Doppler Estimation in Passive Radar

- **서지** — M. Viberg and D. Gerosa and T. McKelvey and P. Dammert and T. Eriksson. *arXiv 2601.15821*, 2026. arXiv:`2601.15821`
- **상태** — ⚠ UNVERIFIED VENUE — 아카이브 파일명이 ICASSP 2026 을 주장하나 PDF 안에 게재처 문자열이 없다  ·  **등급** — P  ·  ⚠ **BibTeX INCOMPLETE**
- **PDF** — `/data/public/sionna_jeong/papers_isac_sionna/new_0731/2601.15821__separable-delay-doppler-passive-radar_ICASSP2026.pdf`
- **조명원 / 기준신호** — source=기회 조명원(분산 센서망) · reference_signal=노드마다 기준 채널 · band=미명시
- **표적 표현** — 느리게 움직이는 표적 일반 · 파라미터 추정 이론
- **엔진 / 실측** — 이론 + 시뮬레이션(추정기 설계)
- **무엇을 무엇에 대해 검증했나** — 지연·도플러 추정 정확도 ↔ 배치별 전 2D 탐색 방식
- **우리와의 관계** — C+D 처리 계열. 우리 CAF 계산 비용 논의의 인접 문헌.
- ⚠ ⚠⚠ 게재처 UNVERIFIED. 이전 라운드가 이 파일을 grade U 로 남긴 이유이며, 이번에 제목·저자만 승급했다. ICASSP 2026 게재로 인용하면 E4.
- ⚠ ⚠ 인용 전 반드시 PDF 를 열어 제목·저자·게재처를 확정할 것.
  > “Our approach is designed for slowly moving targets, and the accuracy of the time-delay estimate is similar to that of the full batch-wise 2-D method.” — *Abstract*
- **초안 문장** — 분산 패시브 레이더에서 지연과 도플러를 분리 추정해 2D 탐색 비용과 노드 간 통신 부담을 줄이는 방법이 제안되었다(Viberg 외, arXiv:2601.15821).

</details>

### 2.EMIT — EMIT · 방출 기반 — 표적 자신이 방사원이다 (우리 기하 축 밖)  *(4편)*

| 인용키 | 논문 | 게재처 · 상태 | 연 | 조명원 | 표적 표현 | 엔진/실측 | 무엇을 검증했나 | 우리와의 관계 | 등급 |
|---|---|---|---|---|---|---|---|---|---|
| `dronescale_sensys20` ⭐⭐ | DroneScale: Drone Load Estimation via Remote Passive RF Sensing | Proc. 18th ACM Conf. Embedded Networked Senso…<br>*PUBLISHED* | 2020 | 없음 (도구·데이터셋) | — | — | — | SenSys 계보에서 드론 RF 센싱의 출발점. | B |
| `matthan_mobisys17` ⭐⭐ | Matthan: Drone Presence Detection by Identifying Physical Signatures in the D… | Proc. 15th Annu. Int. Conf. Mobile Systems, A…<br>*PUBLISHED* | 2017 | 없음 (도구·데이터셋) | — | — | — | emission-based 부류의 대표. LaSen 도 [43] 을 들어 '통신이 없으면 무력' 이라 지적한다 — 우리 반사 기반 접근의 존재 이유를 한 문장으로 정당화해 준다. | B |
| `chen_event_rotation_sensys26` ⭐⭐ | Count Every Rotation and Every Rotation Counts: Exploring Drone Dynamics via … | Proc. 24th ACM Conf. Embedded Networked Senso…<br>*PUBLISHED* | 2026 | 없음 (도구·데이터셋) | — | — | — | ⭐ LaSen 과 같은 프로시딩(DOI prefix 10.1145/3774906)에 실린 프로펠러 중심 논문. '프로펠러가 드론 센싱의 정보원' 이라는 명제가 2026 SenSys 에서 RF/이벤트카메라 두 갈래로 동시에 등장했다고 쓸 수 있다. | B |
| `xu_rf_fingerprint_icassp21` | Adaptive RF Fingerprint Decomposition in Micro UAV Detection Based on Machine… | Proc. IEEE Int. Conf. Acoustics, Speech and S…<br>*PUBLISHED* | 2021 | 없음 (도구·데이터셋) | — | — | — | RF 지문 기반 마이크로 UAV 검출 — emission-based 부류의 ICASSP 사례. | B |

<details><summary><b>▸ 상세 카드 3편</b> — 서지 · 수치 · 인용문 · 초안 문장</summary>

#### `dronescale_sensys20` ⭐⭐ — DroneScale: Drone Load Estimation via Remote Passive RF Sensing

- **서지** — Phuc Nguyen and Vimal Kakaraparthi and Nam Bui and Nikshep Umamahesh and Nhat Pham and Hoang Truong and Yeswanth Guddeti and Dinesh Bharadia and Richard Han and Eric W. Frew and Daniel Massey and Tam Vu. *Proc. 18th ACM Conf. Embedded Networked Sensor Systems (SenSys)*, 2020. DOI `10.1145/3384419.3430778`
- **상태** — PUBLISHED — ACM SenSys 2020  ·  **등급** — B
- **PDF** — 디스크에 없음
- **우리와의 관계** — SenSys 계보에서 드론 RF 센싱의 출발점.
- ⚠ ⚠ 여기 'passive' 는 '우리가 송신하지 않는다' 이지 '남의 조명원의 반사' 가 아니다. 표적 자신이 방사원이므로 A/B/C 어디에도 안 들어간다.
- **초안 문장** — 방출 기반 계열은 드론이 내는 RF 만으로 적재 중량까지 추정할 만큼 발전했지만(Nguyen 외, ACM SenSys 2020), 표적이 송신해야만 동작한다는 점에서 반사 기반 접근과 상보적이다.

#### `matthan_mobisys17` ⭐⭐ — Matthan: Drone Presence Detection by Identifying Physical Signatures in the Drone's RF Communication

- **서지** — Phuc Nguyen and Hoang Truong and Mahesh Ravindranathan and Anh Nguyen and Richard Han and Tam Vu. *Proc. 15th Annu. Int. Conf. Mobile Systems, Applications and Services (MobiSys)*, 2017. DOI `10.1145/3081333.3081354`
- **상태** — PUBLISHED — ACM MobiSys 2017  ·  **등급** — B
- **PDF** — 디스크에 없음
- **우리와의 관계** — emission-based 부류의 대표. LaSen 도 [43] 을 들어 '통신이 없으면 무력' 이라 지적한다 — 우리 반사 기반 접근의 존재 이유를 한 문장으로 정당화해 준다.
- **초안 문장** — 드론의 RF 통신 신호에서 물리적 서명을 찾아 존재를 검출하는 방출 기반 접근은 MobiSys 2017 에서 확립되었으나(Nguyen 외), 표적이 통신하지 않으면 성립하지 않는다.

#### `chen_event_rotation_sensys26` ⭐⭐ — Count Every Rotation and Every Rotation Counts: Exploring Drone Dynamics via Propeller Sensing

- **서지** — Xuecheng Chen and Jingao Xu and Wenhua Ding and Haoyang Wang and Xinyu Luo and Ruiyang Duan and Jialong Chen and Xueqian Wang and Yunhao Liu and Xinlei Chen. *Proc. 24th ACM Conf. Embedded Networked Sensor Systems (SenSys '26)*, 2026. DOI `10.1145/3774906.3800477`
- **상태** — PUBLISHED — ACM SenSys 2026  ·  **등급** — B
- **PDF** — 디스크에 없음
- **우리와의 관계** — ⭐ LaSen 과 같은 프로시딩(DOI prefix 10.1145/3774906)에 실린 프로펠러 중심 논문. '프로펠러가 드론 센싱의 정보원' 이라는 명제가 2026 SenSys 에서 RF/이벤트카메라 두 갈래로 동시에 등장했다고 쓸 수 있다.
- ⚠ ⚠ RF 가 아니라 이벤트 카메라다. RF 결과로 인용 금지.
- **초안 문장** — 프로펠러 회전을 드론 센싱의 1차 정보원으로 삼는 관점은 2026년 SenSys 에서 RF 계열과 이벤트 카메라 계열 양쪽으로 동시에 제기되었다(Chen 외, pp.746-760).

</details>

### 2.E — E · RCS · 산란엔진 앵커 — 검출이 아니라 산란량 자체를 재거나 계산한다  *(16편)*

| 인용키 | 논문 | 게재처 · 상태 | 연 | 조명원 | 표적 표현 | 엔진/실측 | 무엇을 검증했나 | 우리와의 관계 | 등급 |
|---|---|---|---|---|---|---|---|---|---|
| `das_multiband_wcl26` ⭐⭐⭐ | Multiband Monostatic and Bistatic RCS Characterization of AAVs for ISAC Chann… | IEEE Wireless Commun. Lett.<br>*PUBLISHED* | 2026 | 없음 (RCS 실측) | 실물 드론 4종 · DJI Phantom 2, Phantom 3, Mini 2, M350 RTK · 실물. Phant… | 실측. 배경 -> 교정(반경 5.5 cm, 높이 30 cm 금속 원통, 기지 RCS 2.8 dBsm… | 주파수·바이스태틱각 결합 의존성 ↔ 교정 표적의 기지 RCS | ⭐⭐ E. 우리 sigma 앵커의 기울기(0.21 dB/GHz)가 여기서 온다. 그리고 mono/bi 를 함께 준 유일한 드론 RCS 실측. | P |
| `zhang_unified_rcs_jsac26` ⭐⭐⭐ | A Unified RCS Modeling of Typical Targets for 3GPP ISAC Channel Standardizati… | IEEE J. Sel. Areas Commun.<br>*PUBLISHED* | 2026 | 없음 (RCS 실측) | 실물 UAV + 인체 + 차량 · DJI M350 (네 개의 대칭 로터암, 약 430 x 420 x 430 mm), … | 실측. 직경 0.5 m 금속구로 교정. | 측정 정확도 ↔ 금속구 이론 RCS - 이론 -7.07 dBsm 대 측정평균 -8.96 dBsm, 차이 2 dBsm … | E. 3GPP 의 sigma = A x B1 x B2 분해가 어디서 왔는지를 보여주는 1차 문헌이자, 무향실 측정 정확도의 현실적 기준(구 교정 2 dB 이내). | P |
| `semkin_drone_rcs_access20` ⭐⭐⭐ | Analyzing Radar Cross Section Signatures of Diverse Drone Models at mmWave Fr… | IEEE Access<br>*PUBLISHED, open access CC BY* | 2020 | 없음 (RCS 실측) | 실물 멀티로터 8종 + RC 헬기 1종 + 6셀 Li-Po 배터리 1개 · DJI Matrice M100, Walke… | 실측 + CST Microwave Studio 광선추적으로 부품별 기여 추정. 교정은 알루미늄 사다… | 측정 셋업의 타당성 ↔ 동일 형상의 CST 광선추적 시뮬레이션 - 최대 10.2 dBsm 지점에서 일치, 정반사 밖에… | ⭐⭐ E. 우리 재질 가중 PO(GROUP_GAMMA)와 내부 배터리/PCB 모델의 외부 근거 가운데 우리가 가장 무겁게 쓰는 것. ⚠「재질이 7 dB 를 가른다」는 **이 논문이 잰 한 기체·한 자세·mmWave 대역**의 값이고 우리 세 대역(1.8~5.2 GHz)에서 다시 잰 적이 없다 — 크기를 우리 판에 그대로 옮기지 않는다. ⚠「가장 강한」은 우리가 읽은 아카이브 안에서의 순위다. | P |
| `azim_inf_rcs_arxiv25` ⭐⭐⭐ | 3GPP-Compliant Radar Cross Section Characterization of Indoor Factory Targets | arXiv 2505.08754<br>*PREPRINT* | 2025 | 없음 (RCS 실측) | 실물 드론 2종 + 로봇팔 + AGV · 소형 = DJI Mavic 2 Pro (접힘 214x91x84 mm, 907… | 실측 | 3GPP 로그정규 RCS 모델과 그 합의 파라미터 ↔ ⭐ 3GPP RAN1 합의값 A = -12.81 dBsm, B1… | ⭐ E. 3GPP 가 UAV 에 쓰는 절대 수준(A = -12.81 dBsm)의 1차 근거이며, 배터리가 RCS 를 올린다는 우리 재질 가중 PO(내부 배터리/PCB) 서사의 외부 근거. | P |
| `azim_bistatic_rcs_arxiv24` ⭐⭐⭐ | Indoor Statistical and Deterministic RCS Characterization for ISAC Channel Mo… | arXiv 2411.03206<br>*PREPRINT* | 2024 | 없음 (RCS 실측) | 실물 드론 2종 + 로봇팔 + 사족보행 로봇 · DJI Mavic 2 Pro, DJI Matrice 300 RTK ·… | 실측 + 근거리장 정반사 우세 바이스태틱 RCS 의 결정론적 모델(직사각 판) | 로그정규·감마 적합의 적합도, 그리고 결정론적 근거리장 모델 ↔ 적합도 검정(KS, MSE)과 측정 데이터 | ⭐ E. 바이스태틱각을 실제로 훑은 드론 RCS 실측이며, 우리 바이스태틱 PO 일반화의 필요성을 실측으로 뒷받침한다. | P |
| `costa_bistatic_md_jsteap25` ⭐⭐⭐ | Modeling Micro-Doppler Signature of Multi-Propeller Drones in Distributed ISAC | IEEE J. Sel. Topics Signal Process.<br>*PUBLISHED* | 2025 | 없음 (RCS 실측) | 실물 드론 + 해석 모델 · 'Ironman Drone' (다중 프로펠러) · ⭐ 두 겹 - 고전 thin-wire … | 해석 모델 + BiRa 실측 (바이스태틱각 10도:5도:180도, HH 편파, 표적 유무 배경차감) | 주파수영역 마이크로도플러 서명의 유사도 ↔ ⭐ 실측 - 바이스태틱각 30도에서 180도 구간에서 Pearson 교차상… | ⭐⭐ E + C. 우리 대역(5.21 GHz WiFi)에 가장 가까운 바이스태틱 드론 반사도 실측이며, '모델을 실측에 대고 검증한다'는 절차의 모범 사례. | P |
| `yuan_uav_rcs_eucap25` ⭐⭐ | On Experimental Analysis of Mono-Static 3D UAV RCS for ISAC Channel Modeling | Proc. 19th European Conf. Antennas and Propag…<br>*PUBLISHED* | 2025 | 없음 (RCS 실측) | 실물 드론 · DJI Phantom 3 (수평 대각 35 cm, 높이 20 cm) · 실물, VV 편파 | 실측 | 3D(방위 x 고도) RCS 분포 ↔ 무향실 교정 | E. Das 와 같은 기체(Phantom 3)다. ⚠「같은 연구실」은 저자·소속에서 **추정**한 것이고 논문이 그렇게 적지는 않는다. 두 논문의 mu 가 우리 세 대역에서 3.23-3.59 dB 어긋난다 — 그 격차는 **이 두 측정 사이의 불일치**이고, 우리 앵커의 불확실성과 같다고 말하려면 우리 값을 그 둘과 같은 조건에서 재야 한다(아직 안 했다). | P |
| `ezuma_rcs_stats_arxiv21` ⭐⭐ | Radar Cross Section Based Statistical Recognition of UAVs at Microwave Freque… | arXiv 2102.11954<br>*PREPRINT* | 2021 | 없음 (RCS 실측) | 실물 상용 UAV 6종 · DJI Matrice 600 Pro, DJI Matrice 100, Trimble zx5,… | 실측. 배경 차감 -> Hann 윈도 -> IFFT -> 시간영역 게이팅(Tukey) -> PEC … | 측정 체인 ↔ 세 개의 표준 PEC 구의 이론 RCS | E. 기종별 평균 RCS 표의 1차 출처이며, 원거리장 조건이 실측에서 얼마나 가혹한지(25 GHz 에서 M600 은 214 m 필요)를 보여준다. | P |
| `ye_gaf_rcs_taes23` | GAF Representation of Millimeter Wave Drone RCS and Drone Classification Meth… | IEEE Trans. Aerosp. Electron. Syst.<br>*PUBLISHED* | 2023 | 없음 (RCS 실측) | — | — | — | ⭐ mmWave 드론 RCS 를 분류 특징으로 쓰는 TAES 사례 — RCS 를 '값' 이 아니라 '시계열' 로 보는 관점. | B |
| `lee_dynamic_rcs_jees21` ⭐⭐⭐ | Dynamic RCS Estimation According to Drone Movement Using the MoM and Far-Fiel… | J. Electromagn. Eng. Sci.<br>*PUBLISHED, open access CC BY-NC* | 2021 | 없음 (수치 EM) | ⭐ 프로펠러 CAD 모델만 - 기체 없음 · DJI Mavic2 의 프로펠러. 길이 20.32 cm (9.65 GHz… | ⭐ MoM (full-wave). 핵심 트릭: 프로펠러가 돌아도 형상이 변하지 않으므로 메시와 임피… | 제안 방법의 산란장 ↔ ⭐ 상용 EM 툴 Altair FEKO 의 MoM 솔버 - '편차가 거의 없음' | ⭐ E. 우리 SBR+PO 의 정확도 상한 쪽 상대다. 같은 문제(회전 프로펠러 동적 RCS)를 full-wave 로 푼 선례이며, 6.5 lambda 라는 전기적 크기는 우리가 'few-lambda 에서 PO 는 marginal' 이라고 적는 지점과 정확히 겹친다. | P |
| `ziganshin_multistatic_eucap25` ⭐⭐⭐ | Ray-Based Simulation of Multistatic Scattering from Target Objects in ISAC | Proc. 19th European Conf. Antennas and Propag…<br>*PUBLISHED* | 2025 | 없음 (수치 EM) | ⭐ 차량 - 드론이 아니다 · 단순화 차량 메시 3.3 x 2.1 x 1.7 m, 평균 패싯 크기 약 2 lambda… | ⭐ Sionna RT + UTD + vertex diffraction + 고차 회절을 저자들이 얹었다 | 산란 결과 ↔ ⭐ MLFMM(구)과 PO 솔버(차량) - 상용 EM 대조 | ⭐⭐ E. Sionna 코퍼스 140편 중 Sionna 기반으로 dBsm 을 실제로 찍은 유일한 게재 논문이며 우리 SBR+PO 의 최근접 선례. | P |
| `ziganshin_curved_arxiv26` ⭐⭐ | Ray-Based Simulation of Scattering from Discretized Curved Bodies for Vehicul… | arXiv 2604.05991<br>*PREPRINT* | 2026 | 없음 (수치 EM) | 이산화된 곡면체(차량) · 패싯 차량 - 거울·바퀴·유리 생략 · 메시 | ⭐ Sionna-RT v0.19 를 기반으로 정점 회절과 고차 회절을 추가. 포크 공개: githu… | 제안 확장의 효과 ↔ 기본 Sionna-RT(정반사 + 1차 모서리 회절) | E. Sionna-RT 를 실제로 개조한 두 번째 선례이며 개조 코드가 공개된 유일한 사례. | P |
| `sagitta_sbr_po_arxiv26` ⭐⭐ | Sagitta: GPU SBR/PO Radar Cross Section Predictor | arXiv 2604.09243<br>*PREPRINT* | 2026 | 없음 (수치 EM) | PEC 구 + 복잡 항공기 형상 · 드론 아님 · 메시 | ⭐ GPU(NVIDIA/AMD) + MPI 위의 SBR + 이산 PO 적분. 입사광선 샘플링 규칙으… | RCS ↔ ⭐ PEC 구의 해석적 Mie 해 | ⭐ E. 우리 엔진과 같은 계열(GPU SBR+PO)의 독립 구현이며, 우리가 쓸 수 있는 검증 절차(PEC 구 대 Mie)를 그대로 보여준다. | P |
| `kirik_ptd_sbr_sigma19` ⭐⭐ | An Accurate and Effective Implementation of Physical Theory of Diffraction to… | Sigma J. Eng. Nat. Sci.<br>*PUBLISHED* | 2019 | 없음 (수치 EM) | 벤치마크 표적들 · 15 cm x 15 cm PEC 판, 이면 반사기(DCR), 직각 삼면 반사기, 미사일, 헬기 ·… | ⭐ PO + SBR + PTD (Predics 도구). 광선 밀도 10 rays/wavelength. | PO 구현과 PTD 보정 ↔ ⭐ 세 겹 - (1) 평판의 PO 해석해, (2) Griesser 의 실측 RCS(VV/… | ⭐ E. 우리 SBR+PO 에 PTD 보정을 얹으려는 계획의 방법 선례이자, 검증 사다리(해석해 -> 실측 -> 상용 솔버)의 모범. | P |
| `kataria_microdoppler_icasspw23` ⭐⭐ | Simulation of Micro-Doppler Signatures of Drones | Proc. IEEE Int. Conf. Acoustics, Speech and S…<br>*PUBLISHED* | 2023 | 없음 (수치 EM) | — | — | — | ⭐ ICASSP 계보에서 드론 마이크로도플러 **시뮬레이션**의 직접 선행. 우리 시뮬 파이프라인의 신호처리학회 쪽 대조군. | B |
| `kasdorf_sbr_coneangle` | Advancing Accuracy of Shooting and Bouncing Rays Method for Ray-Tracing Propa… | arXiv<br>*⚠ 게재 여부 UNVERIFIED* | 2021 | 없음 (수치 EM) | ⚠ 표적 없음 - 터널 환경 전파 · 해당 없음 | SBR 정확도 개선 - 광선별 원뿔각을 국소 이웃으로 계산, 정이십면체 광선 생성, 중복 계산 광선… | SBR 의 위상·크기 정확도 ↔ image theory RT (훨씬 느리지만 정확한 기준) | E. 우리 SBR 의 광선 밀도·원뿔각·중복 제거 설계의 방법 근거. 다만 산란이 아니라 전파 문제에서 온 것임을 반드시 밝혀야 한다. | P |

<details><summary><b>▸ 상세 카드 15편</b> — 서지 · 수치 · 인용문 · 초안 문장</summary>

#### `das_multiband_wcl26` ⭐⭐⭐ — Multiband Monostatic and Bistatic RCS Characterization of AAVs for ISAC Channel Modeling

- **서지** — S. Das and P. Zhang and V. Hovinen and M. E. Leinonen and P. Kyösti and others. *IEEE Wireless Commun. Lett.*, 2026. DOI `10.1109/LWC.2026.3705634`
- **상태** — PUBLISHED — IEEE WCL 15:3731-3735  ·  **등급** — P  ·  ⚠ **BibTeX INCOMPLETE**
- **PDF** — `/data/public/sionna_jeong/papers_isac_sionna/paper_sionna_Ray_0723/Multiband_Monostatic_and_Bistatic_RCS_Characterization_of_AAVs_for_ISAC_Channel_Modeling.pdf`
- **조명원 / 기준신호** — source=VNA 기반 RCS 측정(조명원 아님) · reference_signal=해당 없음 · band=1.8-27 GHz
- **표적 표현** — 실물 드론 4종 · DJI Phantom 2, Phantom 3, Mini 2, M350 RTK · 실물. Phantom 3/Mini 2/M350 은 무향 원거리장, Phantom 2 는 통제된 비무향 실내 근거리장.
- **엔진 / 실측** — 실측. 배경 -> 교정(반경 5.5 cm, 높이 30 cm 금속 원통, 기지 RCS 2.8 dBsm) -> 표적 순서.
- **무엇을 무엇에 대해 검증했나** — 주파수·바이스태틱각 결합 의존성 ↔ 교정 표적의 기지 RCS
- **핵심 수치** — `band_GHz` = [1.8, 27], `bistatic_angles_deg` = [0, 15, 30, 45, 60, 75, 90], `calibration_cylinder_rcs_dBsm` = 2.8, `phantom3_theta_b0_fit` = mu(f) = 0.21 f - 19.19 dBsm  (f in GHz), `phantom3_band_GHz` = [1.8, 18.2], `phantom3_dimension_cm` = [35, 20], `phantom3_bistatic_intercept_spread_dB` = 0.63
- **우리와의 관계** — ⭐⭐ E. 우리 sigma 앵커의 기울기(0.21 dB/GHz)가 여기서 온다. 그리고 mono/bi 를 함께 준 유일한 드론 RCS 실측.
- ⚠ ⭐ 우리 sigma_anchor 의 절대 수준은 논문값에 +2.5068 dB 변환을 얹은 것이고 그 변환은 논문의 정의 문장이 뒷받침하지 않는다(outputs/prior_settled_anchor.json anchor_health_today).
- ⚠ 일곱 개 바이스태틱 열이 Phantom 3 에서는 절편 0.63 dB 차이뿐이다 - '바이스태틱 의존성이 크다'의 근거로 쓰면 과장.
  > “The measured RCS spans 1.8 GHz-27 GHz and seven bistatic angles from 0 to 90 in 15 steps. The DJI Phantom 2 dataset is newly measured in this work, whereas the RCS data for the DJI Mini 2, Phantom 3, and M350 RTK were obtained from [prior work]” — *p.1*
  > “Calibration measurement: A metallic cylinder with radius 5.5 cm, height 30 cm, and known RCS sigma_Cal = 2.8 dBsm is placed at the center of the turntable” — *p.2*
- **초안 문장** — 소형 드론의 RCS 를 1.8-27 GHz 와 0-90도 바이스태틱각에 걸쳐 함께 특성화한 실측이 있으며(Das 외, IEEE WCL 15:3731, 2026), 여기서 얻은 주파수 기울기 약 0.21 dB/GHz 가 우리 절대 수준 앵커의 근거다.

#### `zhang_unified_rcs_jsac26` ⭐⭐⭐ — A Unified RCS Modeling of Typical Targets for 3GPP ISAC Channel Standardization and Experimental Analysis

- **서지** — Y. Zhang and J. Zhang and H. Gong and X. Hu and J. Zhang and H. Xing and S. Luo and Y. Xiong and L. Yu and Z. Yuan and G. Liu and T. Jiang. *IEEE J. Sel. Areas Commun.*, 2026. DOI `10.1109/JSAC.2025.3608732`
- **상태** — PUBLISHED — IEEE JSAC 44:702-  ·  **등급** — P  ·  ⚠ **BibTeX INCOMPLETE**
- **PDF** — `/data/public/sionna_jeong/papers_isac_sionna/paper_sionna_Ray_0723/A_Unified_RCS_Modeling_of_Typical_Targets_for_3GPP_ISAC_Channel_Standardization_and_Experimental_Analysis.pdf`
- **조명원 / 기준신호** — source=대형 무향실 RCS 측정 · reference_signal=해당 없음 · band=10, 15, 20, 28, 36 GHz
- **표적 표현** — 실물 UAV + 인체 + 차량 · DJI M350 (네 개의 대칭 로터암, 약 430 x 420 x 430 mm), 인체 180 cm / 70 kg · 실물
- **엔진 / 실측** — 실측. 직경 0.5 m 금속구로 교정.
- **무엇을 무엇에 대해 검증했나** — 측정 정확도 ↔ 금속구 이론 RCS - 이론 -7.07 dBsm 대 측정평균 -8.96 dBsm, 차이 2 dBsm 미만
- **핵심 수치** — `frequencies_GHz` = [10, 15, 20, 28, 36], `sphere_diameter_m` = 0.5, `sphere_theoretical_dBsm` = -7.07, `sphere_measured_avg_dBsm` = -8.96, `sphere_discrepancy_dBsm` = <2, `uav_dimensions_mm` = [430, 420, 430], `vehicle_target` = Volkswagen T-Cross, 4.218 x 1.76 x (미추출) m
- **우리와의 관계** — E. 3GPP 의 sigma = A x B1 x B2 분해가 어디서 왔는지를 보여주는 1차 문헌이자, 무향실 측정 정확도의 현실적 기준(구 교정 2 dB 이내).
- ⚠ ⭐ 무향실 실측조차 교정구에서 2 dB 가까이 벌어진다 - 우리 실측 앵커링 +-2~3 dB 허용치의 외부 근거로 쓸 수 있다.
- ⚠ arXiv 판(2505.20673)과 게재판은 별개 파일이다. 쪽번호는 게재판만 쓸 것.
- ⚠ ⭐ 게재판과 arXiv 판의 문면이 최소 한 곳에서 다르다(AAV vs UAV). 판본을 밝히지 않고 인용하면 E2 재발.
  > “RCS is -7.07 dBsm, while the measured average is -8.96 dBsm, with a discrepancy of less than 2 dBsm, confirming the high accuracy of the measurements.” — *p.7*
  > “The AAV used is the DJI M350, with four symmetrically deployed rotor arms and approximate dimensions of 430 x 420 x 430 mm.” — *게재판 p.6*
- **초안 문장** — 3GPP ISAC 채널 표준화를 겨냥한 통합 RCS 모델은 산란을 대규모 전력·각도 의존·무작위 성분으로 분해하며 무향실 모노스태틱 측정으로 검증되었고(Zhang 외, IEEE JSAC 44:702, 2026), 금속구 교정 기준 측정 오차는 2 dB 이내로 보고된다.

#### `semkin_drone_rcs_access20` ⭐⭐⭐ — Analyzing Radar Cross Section Signatures of Diverse Drone Models at mmWave Frequencies

- **서지** — V. Semkin and J. Haarla and T. Pairon and C. Slezak and S. Rangan and V. Viikari and C. Oestges. *IEEE Access*, 2020. DOI `10.1109/ACCESS.2020.2979339`
- **상태** — PUBLISHED, open access CC BY — IEEE Access 8  ·  **등급** — P
- **PDF** — `/data/public/sionna_jeong/papers_isac_sionna/new_0731/2112.09774__semkin_comparative-rcs-uav-classification.pdf` · `/data/public/sionna_jeong/papers_isac_sionna/new_0731/ieeeaccess2020_semkin__drone-rcs-mmwave-26-40ghz.pdf`
- **조명원 / 기준신호** — source=VNA + 표준 이득 혼(Tx) / 이중편파 Vivaldi 혼(Rx), Aalto 무향실 · reference_signal=해당 없음 · band=26-40 GHz, 1 GHz 간격 · range_m=5.8
- **표적 표현** — 실물 멀티로터 8종 + RC 헬기 1종 + 6셀 Li-Po 배터리 1개 · DJI Matrice M100, Walkera Voyager 4, HMF Y600, 자작 헥사콥터(그룹 II, 탄소섬유) / DJI Mavic Pro, DJI Phantom 4 Pro, Kyosho 헬기, DJI F450, Parrot AR.Drone(그룹 I, 플라스틱·스티로폼) · ⭐ 실물, 배터리를 장착한 채 측정(Y600 과 헥사콥터는 예외). 배터리 단독도 따로 측정.
- **엔진 / 실측** — 실측 + CST Microwave Studio 광선추적으로 부품별 기여 추정. 교정은 알루미늄 사다리꼴 육면체(최장 180 mm).
- **무엇을 무엇에 대해 검증했나** — 측정 셋업의 타당성 ↔ 동일 형상의 CST 광선추적 시뮬레이션 - 최대 10.2 dBsm 지점에서 일치, 정반사 밖에서는 점근 솔버 탓에 차이
- **핵심 수치** — `band_GHz` = [26, 40], `measurement_range_m` = 5.8, `group_II_minus_group_I_mean_dB` = 7, `group_II_minus_group_I_max_dB` = [10, 20], `rcs_vs_frequency_slope_dB_per_GHz` = 0.25, `rcs_std_dev_dB` = 6, `reference_cuboid_max_dBsm` = 10.2, `literature_drone_rcs_Xband_dBsm` = [-20, -15], `literature_drone_rcs_30_37GHz_dBsm` = < -20
- **우리와의 관계** — ⭐⭐ E. 우리 재질 가중 PO(GROUP_GAMMA)와 내부 배터리/PCB 모델의 외부 근거 가운데 우리가 가장 무겁게 쓰는 것. ⚠「재질이 7 dB 를 가른다」는 **이 논문이 잰 한 기체·한 자세·mmWave 대역**의 값이고 우리 세 대역(1.8~5.2 GHz)에서 다시 잰 적이 없다 — 크기를 우리 판에 그대로 옮기지 않는다. ⚠「가장 강한」은 우리가 읽은 아카이브 안에서의 순위다.
- ⚠ 26-40 GHz 측정이다. 0.25 dB/GHz 기울기를 우리 대역까지 외삽하면 근거 없이 14 GHz 를 넘겨 외삽하는 셈 - 인용은 하되 외삽은 하지 말 것.
- ⚠ Nokia 논문(A02)이 이 데이터를 근거로 DJI Air 3 의 RCS 를 -17 dBsm 으로 잡았다 - 같은 외삽 문제를 안고 있다.
  > “Mean RCS values of Group II are roughly 7 dB higher than those of Group I. This is predictable, since drones from Group II are mostly made of carbon fiber reinforced polymer material (CFRP).” — *p.11*
  > “The rate at which the RCS increases does not depend on the drone model and is approximately equal to 0.25 dB/GHz.” — *p.11*
  > “For all the considered scenarios, sigma is approximately 6 dB.” — *p.11*
- **초안 문장** — 드론 RCS 는 기체 재질이 지배하며 탄소섬유 기체가 플라스틱 기체보다 평균 약 7 dB, 최대 10-20 dB 높고, 리튬폴리머 배터리는 기체가 비반사성이어도 검출을 가능케 할 만큼 큰 반사체다(Semkin 외, IEEE Access 8:48958, 2020).

#### `azim_inf_rcs_arxiv25` ⭐⭐⭐ — 3GPP-Compliant Radar Cross Section Characterization of Indoor Factory Targets

- **서지** — A. W. Azim and A. Bazzi and R. Bomfin and M. Chafii. *arXiv 2505.08754*, 2025. arXiv:`2505.08754`
- **상태** — PREPRINT  ·  **등급** — P
- **PDF** — `/data/public/sionna_jeong/papers_isac_sionna/new_0731/2505.08754__3gpp-rcs-indoor-factory-targets.pdf`
- **조명원 / 기준신호** — source=실내 측정 시스템(Tx/Rx 수평 편파) · reference_signal=해당 없음 · band=25-28 GHz
- **표적 표현** — 실물 드론 2종 + 로봇팔 + AGV · 소형 = DJI Mavic 2 Pro (접힘 214x91x84 mm, 907 g), 중형 = DJI Matrice 300 RTK (3.6-6.3 kg, 듀얼 리튬이온 배터리) · 실물, 관측점 위에서 연속 회전 비행
- **엔진 / 실측** — 실측
- **무엇을 무엇에 대해 검증했나** — 3GPP 로그정규 RCS 모델과 그 합의 파라미터 ↔ ⭐ 3GPP RAN1 합의값 A = -12.81 dBsm, B1 = 0 dB, B2 = 3.74 dB
- **핵심 수치** — `band_GHz` = [25, 28], `tx_rx_baseline_cm` = 55, `angular_offset_deg` = 10, `3gpp_agreed_uav_A_dBsm` = -12.81, `3gpp_agreed_uav_B1_dB` = 0, `3gpp_agreed_uav_B2_dB` = 3.74, `3gpp_agreed_human_A_dBsm` = -1.37, `3gpp_agreed_human_B2_dB` = 3.94, `measured_small_uav_A_dBsm` = -13.57, `measured_small_uav_B2_dB` = 3.065
- **우리와의 관계** — ⭐ E. 3GPP 가 UAV 에 쓰는 절대 수준(A = -12.81 dBsm)의 1차 근거이며, 배터리가 RCS 를 올린다는 우리 재질 가중 PO(내부 배터리/PCB) 서사의 외부 근거.
- ⚠ ⚠ PREPRINT.
- ⚠ 25-28 GHz 값이다. 우리 대역으로 그대로 옮기면 Semkin 이 보고한 0.25 dB/GHz 기울기를 무시하게 된다.
  > “For UAV characterization, the agreed parameters comprise A = -12.81 dBsm, B1 = 0 dB, and B2 = 3.74 dB.” — *p.2*
  > “The derived log-normal parameters for small-sized UAVs yield A = -13.57 dBsm and B2 = 3.065 dB, demonstrating close agreement with 3GPP's standardized values” — *p.6*
  > “The mid-sized UAVs exhibit higher reflectivity compared to the small-sized UAV due to enhanced specular components attributed to material and lithium-ion battery packs.” — *Abstract*
- **초안 문장** — 3GPP RAN1 이 합의한 소형 UAV 의 평균 RCS 는 A = -12.81 dBsm 이며 독립 실측이 이를 1 dB 이내로 재현했고(Azim 외, arXiv:2505.08754), 같은 측정에서 중형 기체가 더 강하게 반사하는 이유로 재질과 리튬이온 배터리 팩이 지목된다.

#### `azim_bistatic_rcs_arxiv24` ⭐⭐⭐ — Indoor Statistical and Deterministic RCS Characterization for ISAC Channel Modeling

- **서지** — A. W. Azim and A. Bazzi and R. Bomfin and N. Giakoumidis and T. S. Rappaport and M. Chafii. *arXiv 2411.03206*, 2024. arXiv:`2411.03206`
- **상태** — PREPRINT  ·  **등급** — P
- **PDF** — `/data/public/sionna_jeong/papers_isac_sionna/new_0731/2411.03206__statistical-rcs-indoor-factory.pdf`
- **조명원 / 기준신호** — source=실내 측정 · reference_signal=해당 없음 · band=25-28 GHz
- **표적 표현** — 실물 드론 2종 + 로봇팔 + 사족보행 로봇 · DJI Mavic 2 Pro, DJI Matrice 300 RTK · 실물. 지면-기체 하부 간격 0.9 m(Mavic) / 0.6 m(Matrice), 배터리 위치가 다름(Mavic 상단, Matrice 측면)
- **엔진 / 실측** — 실측 + 근거리장 정반사 우세 바이스태틱 RCS 의 결정론적 모델(직사각 판)
- **무엇을 무엇에 대해 검증했나** — 로그정규·감마 적합의 적합도, 그리고 결정론적 근거리장 모델 ↔ 적합도 검정(KS, MSE)과 측정 데이터
- **핵심 수치** — `band_GHz` = [25, 28], `bistatic_angles_deg` = [20, 40, 60], `quasi_monostatic_offset_deg` = 10, `tx_target_separation_m` = [2, 10], `mavic_mu_range_by_theta_b` = [-3.95, -3.8], `quadruped_mu_range_by_theta_b` = [-3.55, -3.4]
- **우리와의 관계** — ⭐ E. 바이스태틱각을 실제로 훑은 드론 RCS 실측이며, 우리 바이스태틱 PO 일반화의 필요성을 실측으로 뒷받침한다.
- ⚠ ⚠ PREPRINT.
- ⚠ mu 값은 자연로그 스케일 로그정규 파라미터이지 dBsm 이 아니다. 혼동 금지.
  > “The analysis is conducted based on measurements in quasi-monostatic and bistatic configurations with bistatic angles of 20, 40, and 60.” — *Abstract*
  > “In case we know the geometry and NF regimes, RCS is no longer well represented by a distance-invariant random variable. Instead, RCS exhibits systematic dependence on range and bistatic angle.” — *p.1*
  > “the battery placement also differs between platforms (side-mounted for the Matrice 300 RTK versus top-mounted for the Mavic 2 Pro), which may alter dominant scattering centers.” — *p.4*
- **초안 문장** — 드론 RCS 는 거리 불변 확률변수가 아니라 거리와 바이스태틱각에 체계적으로 의존하며, 배터리 배치 같은 내부 구조가 지배 산란중심을 바꾼다는 점이 실측으로 보고되었다(Azim 외, arXiv:2411.03206).

#### `costa_bistatic_md_jsteap25` ⭐⭐⭐ — Modeling Micro-Doppler Signature of Multi-Propeller Drones in Distributed ISAC

- **서지** — H. C. A. Costa and others. *IEEE J. Sel. Topics Signal Process.*, 2025
- **상태** — PUBLISHED (저널판) — 회의판 arXiv:2401.14287 은 별개 문서  ·  **등급** — P  ·  ⚠ **BibTeX INCOMPLETE**
- **PDF** — `/data/public/sionna_jeong/papers_isac_sionna/new_0731/2504.05168__costa_microdoppler-multiprop-drones_JSTEAP-journal.pdf` · `/data/public/sionna_jeong/papers_isac_sionna/paper_sionna_Ray_0723/Modeling_Micro-Doppler_Signature_of_Multi-Propeller_Drones_in_Distributed_ISAC.pdf`
- **조명원 / 기준신호** — source=OFDM 형 신호(분산 ISAC 상정) + BiRa 측정설비 · reference_signal=해당 없음 · band=⭐ 반사도 측정 5.78-8.22 GHz, 10 MHz 간격; HRR 측정은 순시대역 2 GHz 초과
- **표적 표현** — 실물 드론 + 해석 모델 · 'Ironman Drone' (다중 프로펠러) · ⭐ 두 겹 - 고전 thin-wire 모델을 바이스태틱으로 확장 + 기체 정적 부분의 반사도를 통합
- **엔진 / 실측** — 해석 모델 + BiRa 실측 (바이스태틱각 10도:5도:180도, HH 편파, 표적 유무 배경차감)
- **무엇을 무엇에 대해 검증했나** — 주파수영역 마이크로도플러 서명의 유사도 ↔ ⭐ 실측 - 바이스태틱각 30도에서 180도 구간에서 Pearson 교차상관 0.98
- **핵심 수치** — `reflectivity_band_GHz` = [5.78, 8.22], `reflectivity_step_MHz` = 10, `bistatic_angles_deg` = {'start': 10, 'step': 5, 'stop': 180}, `pearson_correlation` = 0.98, `correlation_angle_range_deg` = [30, 180], `hrr_instantaneous_bandwidth_GHz` = >2
- **우리와의 관계** — ⭐⭐ E + C. 우리 대역(5.21 GHz WiFi)에 가장 가까운 바이스태틱 드론 반사도 실측이며, '모델을 실측에 대고 검증한다'는 절차의 모범 사례.
- ⚠ 회의판(2401.14287, RadarConf24)과 저널판은 별개 문서다. 쪽·수치를 섞지 말 것.
- ⚠ 0.98 은 '주파수영역 마이크로도플러 서명' 의 상관이지 RCS 절대값의 일치가 아니다.
  > “This produces a cross-correlation coefficient of 0.98 across the bistatic angles from 30 to 180.” — *p.6*
  > “The reflectivity of Ironman Drone is measured with wide bandwidth (5.78 GHz:10 MHz:8.22 GHz) for multiple bistatic angle constellations (10:5:180) in HH polarization.” — *p.11*
- **초안 문장** — 다중 프로펠러 드론의 바이스태틱 마이크로도플러는 thin-wire 해석 모델과 실측을 대조해 바이스태틱각 30-180도 구간에서 상관계수 0.98 로 재현된 바 있다(Costa 외, IEEE JSTEAP 2025).

#### `yuan_uav_rcs_eucap25` ⭐⭐ — On Experimental Analysis of Mono-Static 3D UAV RCS for ISAC Channel Modeling

- **서지** — *Proc. 19th European Conf. Antennas and Propagation (EuCAP)*, 2025. DOI `10.23919/EuCAP63536.2025.10999912`
- **상태** — PUBLISHED — EuCAP 2025  ·  **등급** — P  ·  ⚠ **BibTeX INCOMPLETE**
- **PDF** — `/data/public/sionna_jeong/papers_isac_sionna/paper_sionna_Ray_0723/On_Experimental_Analysis_of_Mono-Static_3D_UAV_RCS_for_ISAC_Channel_Modeling.pdf`
- **조명원 / 기준신호** — source=CATR(콤팩트 안테나 시험장) 무향실 · reference_signal=해당 없음 · band=본문(설정 JSON) 참조
- **표적 표현** — 실물 드론 · DJI Phantom 3 (수평 대각 35 cm, 높이 20 cm) · 실물, VV 편파
- **엔진 / 실측** — 실측
- **무엇을 무엇에 대해 검증했나** — 3D(방위 x 고도) RCS 분포 ↔ 무향실 교정
- **핵심 수치** — `fit_params_theta90` = [0.315, -16.15, 0.0045, 0.07], `fit_params_theta0` = [0.231, -17.92, 0.0024, 0.06], `fit_params_theta180` = [0.175, -17.12, 0.0019, 0.07]
- **우리와의 관계** — E. Das 와 같은 기체(Phantom 3)다. ⚠「같은 연구실」은 저자·소속에서 **추정**한 것이고 논문이 그렇게 적지는 않는다. 두 논문의 mu 가 우리 세 대역에서 3.23-3.59 dB 어긋난다 — 그 격차는 **이 두 측정 사이의 불일치**이고, 우리 앵커의 불확실성과 같다고 말하려면 우리 값을 그 둘과 같은 조건에서 재야 한다(아직 안 했다).
- ⚠ ⚠ Yuan 의 eps 는 선형 진폭 스케일의 라이시안 산포 파라미터이고 Das 의 eps 는 dB 영역 표준편차다. 같은 양이 아니다.
  > “{a,b,c,d} = {0.315,-16.15,0.0045,0.07} / {0.231,-17.92,0.0024,0.06} / {0.175,-17.12,0.0019,0.07} at theta = 90/0/180” — *IV 절 본문(settled 라운드가 텍스트 레이어에서 확인)*
- **초안 문장** — 같은 DJI Phantom 3 를 대상으로 한 두 편의 무향실 측정이 우리 관심 대역에서 3.2-3.6 dB 어긋난 평균 RCS 를 보고하며(Das, IEEE WCL 2026; Yuan, EuCAP 2025), 이 격차를 설명하는 문장은 양쪽 어디에도 없다.

#### `ezuma_rcs_stats_arxiv21` ⭐⭐ — Radar Cross Section Based Statistical Recognition of UAVs at Microwave Frequencies

- **서지** — M. Ezuma and C. K. Anjinappa and M. Funderburk and I. Guvenc. *arXiv 2102.11954*, 2021. arXiv:`2102.11954`
- **상태** — PREPRINT — PDF 에 게재처 표기 없음 (관련 저널판 존재 가능)  ·  **등급** — P
- **PDF** — `/data/public/sionna_jeong/papers_isac_sionna/new_0731/1911.05926__ezuma_compact-range-rcs-small-drones-15-25ghz.pdf` · `/data/public/sionna_jeong/papers_isac_sionna/new_0731/2102.11954__ezuma_uav-rcs-statistical-recognition.pdf`
- **조명원 / 기준신호** — source=콤팩트 레인지 무향실(대형 포물 반사경) · reference_signal=해당 없음 · band=15 GHz 와 25 GHz, VV/HH
- **표적 표현** — 실물 상용 UAV 6종 · DJI Matrice 600 Pro, DJI Matrice 100, Trimble zx5, DJI Mavic Pro 1, DJI Inspire 1 Pro, DJI Phantom 4 Pro · 실물
- **엔진 / 실측** — 실측. 배경 차감 -> Hann 윈도 -> IFFT -> 시간영역 게이팅(Tukey) -> PEC 구(12/6/3.75 인치) 교정.
- **무엇을 무엇에 대해 검증했나** — 측정 체인 ↔ 세 개의 표준 PEC 구의 이론 RCS
- **핵심 수치** — `frequencies_GHz` = [15, 25], `avg_rcs_15GHz_VV_dBsm` = {'DJI Matrice 600': -11.67, 'DJI Matrice 100': -14.69, 'Trimble zx5': -14.39, 'DJI Mavic Pro': -17.06, 'DJI Inspire 1': -14.24, 'DJI Phantom 4 Pro': -15.02}, `classification_accuracy_percent_at_10dB_SNR` = {'15GHz_HH': 97.43, '25GHz_HH': 100.0, '15GHz_VV': 99.17}, `farfield_distance_for_M600_at_25GHz_m` = 213.95
- **우리와의 관계** — E. 기종별 평균 RCS 표의 1차 출처이며, 원거리장 조건이 실측에서 얼마나 가혹한지(25 GHz 에서 M600 은 214 m 필요)를 보여준다.
- ⚠ ⚠ PREPRINT (게재판이 따로 있을 수 있음 - 확인 전 저널로 인용 금지).
- ⚠ ⭐ 이전 라운드(outputs/prior_settled_anchor.json X_C18)가 '이 PDF 가 디스크에 없다'고 판정했으나 2026-07-31 현재 new_0731/ 에 있다. 그 판정은 이 레코드로 정정된다.
- ⚠ 같은 저자군의 1911.05926(15-25 GHz 콤팩트 레인지)도 디스크에 있다.
  > “For the 15 GHz VV-polarization measurement, the average RCS of DJI Matrice 600, DJI Matrice 100, Trimble zx5, DJI Mavic Pro, DJI Inspire 1, and DJI Phantom 4 Pro are -11.67 dBsm, -14.69 dBsm, -14.39 dBsm, -17.06 dBsm, -14.24 dBsm, and -15.02 dBsm” — *p.24*
  > “For instance, a DJI Matrice 600 UAV, a popular commercial grade UAV, have diameter of about 1.133 m [39]. Therefore, using a 25 GHz radar, we need a separation distance R of at least 213.95 m to accurately measure the RCS of the UAV in the far-field.” — *p.9*
- **초안 문장** — 상용 소형 UAV 여섯 기종의 평균 RCS 는 15 GHz VV 편파에서 -11.7 ~ -17.1 dBsm 범위이며 로그정규·GEV·감마 분포가 가장 잘 맞는다(Ezuma 외, arXiv:2102.11954).

#### `lee_dynamic_rcs_jees21` ⭐⭐⭐ — Dynamic RCS Estimation According to Drone Movement Using the MoM and Far-Field Approximation

- **서지** — D.-Y. Lee and J.-I. Lee and D.-W. Seo. *J. Electromagn. Eng. Sci.*, 2021. DOI `10.26866/jees.2021.4.r.40`
- **상태** — PUBLISHED, open access CC BY-NC — JEES 21(4)  ·  **등급** — P
- **PDF** — `/data/public/sionna_jeong/papers_isac_sionna/new_0731/jees2021__dynamic-rcs-drone-mom.pdf`
- **조명원 / 기준신호** — source=수치 계산(입사 평면파) · reference_signal=해당 없음 · band=9.65 GHz, PRF 20 kHz
- **표적 표현** — ⭐ 프로펠러 CAD 모델만 - 기체 없음 · DJI Mavic2 의 프로펠러. 길이 20.32 cm (9.65 GHz 에서 약 6.5 lambda), 탄소섬유(PEC 와 RCS 수준이 유사해 PEC 로 가정) · 메시 기반 CAD
- **엔진 / 실측** — ⭐ MoM (full-wave). 핵심 트릭: 프로펠러가 돌아도 형상이 변하지 않으므로 메시와 임피던스 행렬을 한 번만 만들고, 프로펠러 대신 입사각을 역방향으로 회전시켜 여기 벡터에만 반영한다.
- **무엇을 무엇에 대해 검증했나** — 제안 방법의 산란장 ↔ ⭐ 상용 EM 툴 Altair FEKO 의 MoM 솔버 - '편차가 거의 없음'
- **핵심 수치** — `frequency_GHz` = 9.65, `prf_kHz` = 20, `propeller_length_cm` = 20.32, `electrical_size_lambda` = 6.5, `angular_step_deg` = 0.1, `spectral_peaks_Hz` = [250.6, 313.3], `hardware` = Intel Core i7-8700 3.20 GHz, 64 GB RAM
- **우리와의 관계** — ⭐ E. 우리 SBR+PO 의 정확도 상한 쪽 상대다. 같은 문제(회전 프로펠러 동적 RCS)를 full-wave 로 푼 선례이며, 6.5 lambda 라는 전기적 크기는 우리가 'few-lambda 에서 PO 는 marginal' 이라고 적는 지점과 정확히 겹친다.
- ⚠ 전기적 크기 6.5 lambda 는 우리 기준으로도 점근해법이 marginal 한 영역이다. 이 논문이 full-wave 를 쓴 이유가 그것이다.
  > “if the mesh is maintained while the scatterer is rotated, the impedance matrix does not change. That is, the mesh and the impedance matrix generated only once can be used continuously for a rotating propeller.” — *p.2*
  > “Each propeller was 20.32 cm long (which results in about 6.5λ at 9.65 GHz) and was made of carbon fiber.” — *p.4*
  > “the MoM solver of Altair's FEKO was used as the conventional method” — *p.4*
- **초안 문장** — 회전 프로펠러의 동적 RCS 를 회전 불변 임피던스 행렬로 가속한 full-wave(MoM) 계산이 보고되어 있으며 상용 솔버와 편차가 거의 없다(Lee 외, JEES 21(4):322, 2021), 다만 대상은 프로펠러 한 장이고 기체는 포함되지 않는다.

#### `ziganshin_multistatic_eucap25` ⭐⭐⭐ — Ray-Based Simulation of Multistatic Scattering from Target Objects in ISAC

- **서지** — A. Ziganshin and E. M. Vitucci and S. J. Myint and W. Kotterman and C. Schneider and V. Degli-Esposti and R. Thomä. *Proc. 19th European Conf. Antennas and Propagation (EuCAP)*, 2025
- **상태** — PUBLISHED — EuCAP 2025  ·  **등급** — P  ·  ⚠ **BibTeX INCOMPLETE**
- **PDF** — `/data/public/sionna_jeong/papers_isac_sionna/paper_sionna_Ray_0723/Ray-Based_Simulation_of_Multistatic_Scattering_from_Target_Objects_in_ISAC.pdf`
- **조명원 / 기준신호** — source=시뮬레이션(Sionna RT) · reference_signal=해당 없음 · band=10 GHz
- **표적 표현** — ⭐ 차량 - 드론이 아니다 · 단순화 차량 메시 3.3 x 2.1 x 1.7 m, 평균 패싯 크기 약 2 lambda @ 10 GHz; 이산화 구도 함께 · 광선추적 씬 안의 패싯 메시
- **엔진 / 실측** — ⭐ Sionna RT + UTD + vertex diffraction + 고차 회절을 저자들이 얹었다
- **무엇을 무엇에 대해 검증했나** — 산란 결과 ↔ ⭐ MLFMM(구)과 PO 솔버(차량) - 상용 EM 대조
- **핵심 수치** — `frequency_GHz` = 10, `car_dimensions_m` = [3.3, 2.1, 1.7], `avg_facet_lambda` = 2, `po_runtime` = 약 1일, `rt_runtime` = 약 2초
- **우리와의 관계** — ⭐⭐ E. Sionna 코퍼스 140편 중 Sionna 기반으로 dBsm 을 실제로 찍은 유일한 게재 논문이며 우리 SBR+PO 의 최근접 선례.
- ⚠ ⭐⭐ F8: arXiv:2604.05991 프리프린트와 별개 문서다. 그 프리프린트가 이 회의논문을 [24] 로 인용한다. 절대 혼동 금지.
- ⚠ 표적이 차량이라 우리 드론 결과의 직접 검증이 아니다.
- ⚠ ⚠ F8 - 회의판(게재)과 저널판(arXiv:2604.05991v2, 프리프린트)은 별개 문서다. 절대 섞지 말 것.
  > “The average facet size is around 2 lambda at a frequency of 10 GHz. The dimensions of this car model are around 3.3x2.1x1.7 (LxWxH) meters. An open-source parallelizable framework, Sionna RT [11], is utilized to conduct simulations.” — *p.3*
  > “The reflectivity with both TX and RX in the far-field transforms into RCS. In each case, the simulation time for the PO solver is around one day, whereas the RT simulation takes only about two seconds, highlighting a clear performance advantage for RT.” — *p.4*
  > “RCS of the simplified car [axis label 'RCS (dBsm)', curves 'EM (PO)' and 'RT+UTD+VD']” — *p.5 Fig.6*
- **초안 문장** — Sionna RT 에 UTD 와 정점 회절을 더해 차량의 다중정적 산란을 계산하고 이를 PO/MLFMM 상용 솔버와 대조한 선례가 있으며, PO 가 하루 걸리는 계산을 광선추적은 2초에 끝낸다(Ziganshin 외, EuCAP 2025).

#### `ziganshin_curved_arxiv26` ⭐⭐ — Ray-Based Simulation of Scattering from Discretized Curved Bodies for Vehicular and ISAC Applications

- **서지** — Ainur Ziganshin and Enrico M. Vitucci and Wim Kotterman and Reiner Thomä and Christian Schneider and Vittorio Degli-Esposti. *arXiv 2604.05991*, 2026. arXiv:`2604.05991`
- **상태** — PREPRINT — PDF 에 게재처 헤더도 DOI 도 없다  ·  **등급** — P
- **PDF** — `/data/public/sionna_jeong/papers_isac_sionna/2604.05991__ziganshin_curved-body-scattering.pdf`
- **조명원 / 기준신호** — source=시뮬레이션 · reference_signal=해당 없음 · band=본문 참조
- **표적 표현** — 이산화된 곡면체(차량) · 패싯 차량 - 거울·바퀴·유리 생략 · 메시
- **엔진 / 실측** — ⭐ Sionna-RT v0.19 를 기반으로 정점 회절과 고차 회절을 추가. 포크 공개: github.com/AinurZiga/sionna-RT-reflectivity
- **무엇을 무엇에 대해 검증했나** — 제안 확장의 효과 ↔ 기본 Sionna-RT(정반사 + 1차 모서리 회절)
- **핵심 수치** — `sionna_version` = 0.19
- **우리와의 관계** — E. Sionna-RT 를 실제로 개조한 두 번째 선례이며 개조 코드가 공개된 유일한 사례.
- ⚠ ⭐⭐ F8 반복: 회의판(E10)과 별개 문서. 단위·주장이 다르다.
- ⚠ ⚠ PREPRINT.
- ⚠ ⚠ 프리프린트를 게재물처럼 인용하면 E4. 회의판과 단위·주장이 다르다.
  > “Sionna-RT (v0.19) [19] was used as a basic RT framework, which is open-source, parallelizable, differentiable, and provides efficient path tracing and electromagnetic field...” — *~p.4*
  > “Standard RT corresponds to the default Sionna-RT implementation with specular reflections and single-bounce edge diffraction, without the proposed vertex and higher-order diffraction extensions.” — *~p.7*
  > “Sionna-RT (v0.19) [19] was used as a basic RT framework, which is open-source, parallelizable, differentiable, and provides efficient path tracing and electromagnetic field computation on triangulized geometries.” — *p.3*
- **초안 문장** — 기본 Sionna-RT 는 정반사와 1차 모서리 회절만 제공하며, 이산화된 곡면의 인공 산란을 없애려면 정점 회절과 고차 회절을 직접 추가해야 한다(Ziganshin 외, arXiv:2604.05991).

#### `sagitta_sbr_po_arxiv26` ⭐⭐ — Sagitta: GPU SBR/PO Radar Cross Section Predictor

- **서지** — *arXiv 2604.09243*, 2026. arXiv:`2604.09243`
- **상태** — PREPRINT  ·  **등급** — P  ·  ⚠ **BibTeX INCOMPLETE**
- **PDF** — `/data/public/sionna_jeong/papers_isac_sionna/2604.09243__sagitta-sbr.pdf`
- **조명원 / 기준신호** — source=시뮬레이션 · reference_signal=해당 없음 · band=본문 참조
- **표적 표현** — PEC 구 + 복잡 항공기 형상 · 드론 아님 · 메시
- **엔진 / 실측** — ⭐ GPU(NVIDIA/AMD) + MPI 위의 SBR + 이산 PO 적분. 입사광선 샘플링 규칙으로 위상 에일리어싱 억제.
- **무엇을 무엇에 대해 검증했나** — RCS ↔ ⭐ PEC 구의 해석적 Mie 해
- **핵심 수치** — `fp32_phase_error_after_100_reflections_percent` = [2, 3], `electrical_size_definition` = kr = 2 pi r / lambda
- **우리와의 관계** — ⭐ E. 우리 엔진과 같은 계열(GPU SBR+PO)의 독립 구현이며, 우리가 쓸 수 있는 검증 절차(PEC 구 대 Mie)를 그대로 보여준다.
- ⚠ ⚠ PREPRINT.
- ⚠ 저자·제목을 이번 라운드에서 추출하지 않았다 - 인용 전 확인 필요(UNVERIFIED).
- ⚠ ⭐ 이 엔진은 Sionna 를 쓰지 않는다. '경쟁 엔진' 으로 분류하되 Sionna 확장 선례로 인용하면 오류.
  > “We validate against analytical Mie solutions for a perfectly electrically conducting (PEC) sphere and demonstrate applicability to a complex aircraft geometry for monostatic radar cross-section prediction.” — *p.1*
  > “For a PEC surface and monostatic backscatter we compute the complex amplitude, detailed in Eq. 7, and the monostatic RCS is sigma = 4 pi \|A\|^2, which is evaluated in m2 and typically expressed in dBsm as 10 log10(sigma).” — *p.7*
  > “While FP32 introduces a slight phase accumulation error (~2-3% deviation) after 100 reflections due to catastrophic cancellation in the e^{-j2kR} term, it is generally acceptable on logarithmic RCS (dBsm) scales.” — *p.10*
- **초안 문장** — GPU 위에서 SBR 과 이산 물리광학 적분을 결합해 모노스태틱 RCS 를 예측하고 PEC 구의 Mie 해로 검증하는 것은 확립된 절차다(Sagitta, arXiv:2604.09243).

#### `kirik_ptd_sbr_sigma19` ⭐⭐ — An Accurate and Effective Implementation of Physical Theory of Diffraction to the Shooting and Bouncing Ray Method via Predics Tool

- **서지** — O. Kirik and C. Ozdemir. *Sigma J. Eng. Nat. Sci.*, 2019
- **상태** — PUBLISHED — 권·호·쪽이 p.1 에 인쇄됨  ·  **등급** — P
- **PDF** — `/data/public/sionna_jeong/papers_isac_sionna/new_0731/sigma2019_kirik-ozdemir__ptd-into-sbr-predics.pdf`
- **조명원 / 기준신호** — source=수치 계산 · reference_signal=해당 없음 · band=6 GHz / 9.4 GHz / 1-9 GHz
- **표적 표현** — 벤치마크 표적들 · 15 cm x 15 cm PEC 판, 이면 반사기(DCR), 직각 삼면 반사기, 미사일, 헬기 · CAD 메시
- **엔진 / 실측** — ⭐ PO + SBR + PTD (Predics 도구). 광선 밀도 10 rays/wavelength.
- **무엇을 무엇에 대해 검증했나** — PO 구현과 PTD 보정 ↔ ⭐ 세 겹 - (1) 평판의 PO 해석해, (2) Griesser 의 실측 RCS(VV/HH, 6 GHz 와 9.4 GHz), (3) FEKO(UTD) 및 CST(점근) 와의 1-9 GHz 스펙트럼 비교
- **핵심 수치** — `ray_density_rays_per_wavelength` = 10, `plate_cm` = [15, 15], `plate_frequency_GHz` = 6, `dcr_frequency_GHz` = 9.4, `trihedral_band_GHz` = [1, 9], `azimuth_points` = 361, `azimuth_range_deg` = [-90, 90]
- **우리와의 관계** — ⭐ E. 우리 SBR+PO 에 PTD 보정을 얹으려는 계획의 방법 선례이자, 검증 사다리(해석해 -> 실측 -> 상용 솔버)의 모범.
- ⚠ 게재처가 학내 저널이라 영향력은 낮다. 방법 선례로만 인용할 것.
  > “a PEC plate of 15 cm x 15 cm is considered and the monostatic RCS simulation of horizontal polarization at 6 GHz was carried out ... The ray density for the ray-launching process is chosen to be 10 rays/wavelength.” — *p.5*
  > “While Griesser's measurement for the VV polarization is plotted as blue dotted line, Predics's PO+SBR+PTD simulation result is given as red solid line. Very good agreement between the measured RCS results by [18] and the calculated RCS results is obvious” — *p.7*
  > “RCS simulations at VV polarization have been carried out by using FEKO (UTD solver), CST (Asymptotic solver) and Predics (PO+SBR+PTD solver) for the frequencies between 1 GHz and 9 GHz.” — *p.9*
- **초안 문장** — SBR 기반 RCS 예측기에 물리회절이론(PTD)을 결합하는 구현은 해석해·실측·상용 솔버의 세 단계로 검증된 선례가 있으며 광선 밀도는 파장당 10 개가 표준적으로 쓰인다(Kirik & Ozdemir, Sigma J. Eng. Nat. Sci. 37(4):1153, 2019).

#### `kataria_microdoppler_icasspw23` ⭐⭐ — Simulation of Micro-Doppler Signatures of Drones

- **서지** — Megha Kataria and Brejesh Lall. *Proc. IEEE Int. Conf. Acoustics, Speech and Signal Processing Workshops (ICASSPW)*, 2023. DOI `10.1109/ICASSPW59220.2023.10193632`
- **상태** — PUBLISHED — ICASSP Workshops 2023  ·  **등급** — B
- **PDF** — 디스크에 없음
- **우리와의 관계** — ⭐ ICASSP 계보에서 드론 마이크로도플러 **시뮬레이션**의 직접 선행. 우리 시뮬 파이프라인의 신호처리학회 쪽 대조군.
- ⚠ 워크숍 논문(5쪽). PDF 미확보 — 방법(해석적/RT/전자기)이 무엇인지 미확인이므로 방법 비교에 쓰기 전에 열 것.
- **초안 문장** — 드론 마이크로도플러 서명의 시뮬레이션은 신호처리 학계에서도 별도로 다루어져 왔다(Kataria & Lall, ICASSP Workshops 2023).

#### `kasdorf_sbr_coneangle`  — Advancing Accuracy of Shooting and Bouncing Rays Method for Ray-Tracing Propagation Modeling Based on Novel Approaches to Ray Cone Angle Calculation

- **서지** — S. Kasdorf and B. Troksa and C. Key and J. Harmon and B. M. Notaros. *arXiv*, 2021
- **상태** — ⚠ 게재 여부 UNVERIFIED — PDF 에 권·호·DOI 가 없다  ·  **등급** — P  ·  ⚠ **BibTeX INCOMPLETE**
- **PDF** — `/data/public/sionna_jeong/papers_isac_sionna/new_0731/notaros_TAP__advancing-accuracy-sbr.pdf`
- **조명원 / 기준신호** — source=수치 계산 · reference_signal=해당 없음 · band=터널 전파 모델링
- **표적 표현** — ⚠ 표적 없음 - 터널 환경 전파 · 해당 없음
- **엔진 / 실측** — SBR 정확도 개선 - 광선별 원뿔각을 국소 이웃으로 계산, 정이십면체 광선 생성, 중복 계산 광선 식별·제거
- **무엇을 무엇에 대해 검증했나** — SBR 의 위상·크기 정확도 ↔ image theory RT (훨씬 느리지만 정확한 기준)
- **우리와의 관계** — E. 우리 SBR 의 광선 밀도·원뿔각·중복 제거 설계의 방법 근거. 다만 산란이 아니라 전파 문제에서 온 것임을 반드시 밝혀야 한다.
- ⚠ ⚠⚠ 게재처·연도 UNVERIFIED. 파일명이 TAP 을 주장하나 PDF 에 근거가 없다 - 저널로 인용하기 전에 확인할 것(E4).
- ⚠ ⚠ 이 논문을 'SBR 로 RCS 를 검증했다'로 요약하면 E1. 전파 모델링 논문이다.
  > “We propose per-ray cone angle calculation, with the maximum separation angle between rays calculated for every individual ray, based on a set of local neighbors rather than a single global maximum. This allows the smallest theoretical error of the SBR method” — *Abstract*
  > “We thus demonstrate how the SBR methodology and implementation can be advanced to produce an SBR approach of similar accuracy as the image theory RT method, in simulations of large tunnels.” — *p.2*
- **초안 문장** — SBR 의 정확도는 광선 원뿔각 설정과 중복 광선 제거에 좌우되며, 이를 개선하면 훨씬 느린 image theory 광선추적과 같은 정확도에 도달할 수 있다(Kasdorf 외).

</details>

### 2.SIM — SIM · 시뮬레이션 플랫폼 · 데이터셋 · 도구  *(15편)*

| 인용키 | 논문 | 게재처 · 상태 | 연 | 조명원 | 표적 표현 | 엔진/실측 | 무엇을 검증했나 | 우리와의 관계 | 등급 |
|---|---|---|---|---|---|---|---|---|---|
| `lambda_dataset_arxiv26` ⭐⭐⭐ | LAMBDA: A Low-Altitude Multimodal Base Dataset for UAV Sensing and Communicat… | arXiv 2607.03826<br>*PREPRINT* | 2026 | 5G NR | UAV · AirSim UAV 모델 · ⭐ 표적 시그니처가 광선추적 밖에서 온다 - CADFEKO 로 RCS 를 미리… | Sionna RT(전파) + Altair CADFEKO(표적 RCS) 조합 | 데이터셋 품질관리 ↔ 본문 참조 - 정량 검증 미확인 | ⭐⭐ H8 의 가장 깨끗한 증거. 2026년 Sionna 논문이 UAV 시그니처가 필요해지자 상용 EM 솔버로 나갔다 - '전파는 Sionna, 표적 산란은 딴 데서' 가 이 분야의 기본값이고, 우리는 그 둘을 한 파이프라인에 넣는다. | P |
| `cellsense_arxiv26` ⭐⭐⭐ | CellSense: A Sub-6 GHz Cellular ISAC System for Clutter-Robust Passive Sensing | arXiv 2606.07900<br>*PREPRINT* | 2026 | 5G NR | ⭐ 사람 - 드론이 아니다 · 1.8 m x 0.5 m x 0.25 m 큐보이드 · 큐보이드 | Sionna 기반 OFDM 링크레벨 시뮬레이션(Blender 로 만든 실내 창고·야외 캠퍼스 씬) … | 검출확률과 오경보확률 ↔ 베이스라인 방식 | ⭐ 우리 벤치마크와 구조가 가장 닮은 Sionna 논문(사이트별 씬 + 표적 + Pd/Pfa + 실측 시제기). | P |
| `dmsnet_arxiv26` ⭐⭐⭐ | DMSNet: Cross-Band Learning for Multi-Target Sensing in Multi-Band ISAC | arXiv 2607.17655<br>*PREPRINT* | 2026 | 다중 대역 통신 파일럿 | ⭐ 미기재. 5쪽 전체에서 Sionna 를 언급하는 문장은 단 하나이고, UAV 를 씬 안에서 어떻게 표현했는지(메시… | Sionna RT | EM 검증 없음. 검증은 검출/추정 성능 벤치마크다. SNR 0 dB 표적개수추정: CA-CFAR 0.7119 / A… | ⭐⭐ 우리 다중대역 서사(WiFi/LTE/5G 를 나란히 놓는 2x3 격자)의 가장 가까운 이웃. 그들은 3.5 vs 28 GHz 를 상보적이라 주장하면서 정작 표적의 주파수 의존 산란을 '가정'만 하고 계산하지 않는다 - 우리가 대역별 sigma 를 실제로 계산해 … | P |
| `clutteraware_procieee26` ⭐⭐⭐ | Clutter-Aware Integrated Sensing and Communication: Models, Methods, and Futu… | Proc. IEEE<br>*PUBLISHED* | 2026 | OFDM/ISAC 파형 (자기송신) | ⭐ 단순화 3D 드론 메시 · 공개 3D 모델을 Blender 로 단순화해 Sionna XML 로 내보낸 것 · 메시… | NVIDIA Sionna RT, 최대 상호작용 깊이 3 | ⭐ 아무것도 - 'validat*' 가 41쪽 전체에서 0회 ↔ 없음 | ⭐⭐ 우리 자리를 정의하는 논문. 최상위 저널이 드론 메시를 Sionna 에 넣고도 표적 산란을 검증하지 않는다는 사실이, 우리 SBR+PO 가 채우는 빈칸이다. | P |
| `wang_neural_isac_jsac25` ⭐⭐ | Neural Integrated Sensing and Communication for the MIMO-OFDM Downlink | IEEE J. Sel. Areas Commun.<br>*ACCEPTED_TO_APPEAR* | 2025 | OFDM/ISAC 파형 (자기송신) | 표적에 재질과 형상 정보가 붙는다 · Blender 로 만든 씬 시드를 XML 로 내보낸 것 · 메시 | NVIDIA Sionna (CIR 생성) + 학습 기반 검출 | 센싱·통신 동시 성능 ↔ 본문 참조 | ⭐ 우리 다중 Rx 실험 설계 서술에 인용할 수 있는 운영 제약을 명시한 드문 논문 - 한 Sionna 씬 안에서는 모든 Rx 의 패턴이 같아야 한다. | P |
| `openisac_arxiv26` | OpenISAC: An Open-Source Real-Time Experimentation Platform for OFDM-ISAC | arXiv 2601.03535<br>*PREPRINT* | 2026 | OFDM/ISAC 파형 (자기송신) | 해당 없음(Sionna 씬 없음). | 인용만 - 'NVIDIA Sionna and the Sionna Research Kit are al… | 플랫폼 실증. CFAR/Pfa/Pd 는 0회(이전 세션 H9 확인, 이번 세션 term-count 재확인). | 우리 그룹미팅 덱의 주제이기도 함. 교집합 목록에는 '인용만' 사례로 남겨 둔다 - 자동 계수(sionna>=1)가 교집합으로 오분류하기 쉬운 대표 함정. | P |
| `rfgenesis_sensys23` ⭐⭐⭐ | RF Genesis: Zero-Shot Generalization of mmWave Sensing through Simulation-Bas… | Proc. 21st ACM Conf. Embedded Networked Senso…<br>*PUBLISHED* | 2023 | mmWave FMCW (자기송신) | — | — | — | RadarTwin(B04)이 자기 파이프라인의 기반으로 삼는 논문. 우리 방법을 SenSys/MobiSys 계열에 제출한다면 이 논문이 직접 비교 기준이 된다. | P |
| `radartwin_arxiv26` | RadarTwin: Scene-Specific mmWave Radar Simulation and Learning for Mobile Ind… | arXiv 2606.28396<br>*PREPRINT* | 2026 | mmWave FMCW (자기송신) | — | — | — | ⭐ 우리 SBR 설계의 외부 정당화 3종: (1) Fresnel 을 ITU-R P.2040-4 로 갈아끼우는 것이 표준 관행이라는 근거, (2) 반사 차수(4-bounce) 를 '경험적으로' 정하는 것이 허용된다는 근거, (3) 시뮬이 메시 전체를 보는 반면 실제 레… | P |
| `sionna_lib_arxiv22` ⭐⭐⭐ | Sionna: An Open-Source Library for Next-Generation Physical Layer Research | arXiv 2203.11854<br>*PREPRINT* | 2022 | 없음 (도구·데이터셋) | ⭐ 없다 - 이 문서들에서 'target' 은 경로의 끝점을 뜻한다 | 도구 자체 | 해당 없음 ↔ 해당 없음 | Sionna 계보의 출발점(0.8.0, RT 없음). 우리 report01 의 근거 문서. | P |
| `sionna_rt_globecom23` ⭐⭐⭐ | Sionna RT: Differentiable Ray Tracing for Radio Propagation Modeling | Proc. IEEE Globecom Workshops<br>*⚠ 디스크 파일은 arXiv:2303.11103v2 프리프린트; 게재 …* | 2023 | 없음 (도구·데이터셋) | ⭐ 없다 - 이 문서들에서 'target' 은 경로의 끝점을 뜻한다 | 도구 자체 | 해당 없음 ↔ 해당 없음 | Sionna RT 의 원전 회의 논문. 우리가 쓰는 광선추적기의 출처. | P |
| `sionna_rt_techreport25` ⭐⭐⭐ | Sionna RT: Technical Report | arXiv 2504.21719<br>*PREPRINT / 벤더 기술보고서* | 2025 | 없음 (도구·데이터셋) | ⭐ 없다 - 이 문서들에서 'target' 은 경로의 끝점을 뜻한다 | 도구 자체 | 해당 없음 ↔ 해당 없음 | ⭐ 우리 report01·06 의 근거 문서 — Sionna 가 무엇을 하고 무엇을 안 하는지(SBR 있음 / PO 표면적분·RCS 출력 없음)의 1차 출처. | P |
| `rt_limits_learning_2026` ⭐⭐ | On the Limitations of Ray-Tracing for Learning-Based RF Tasks | arXiv 2507.19653<br>*⚠ p.1 에 '* | 2026 | 없음 (도구·데이터셋) | none (1664 real UE positions, 6 BS sites, central Rome) | Sionna RT | — | ⭐ Sionna 결과를 실측과 대조한 몇 안 되는 논문이자 버전을 명시한 논문. 우리가 '시뮬 결과의 신뢰구간' 을 말할 때 인용할 외부 근거. 안테나 배치·방위가 solver 파라미터보다 오차를 지배한다는 결론도 우리 관측 설계에 직결. | U |
| `greatx_arxiv25` | Unreal Is All You Need: Multimodal ISAC Data Simulation with Only One Engine | arXiv 2507.08716<br>*PREPRINT* | 2025 | 없음 (도구·데이터셋) | 'Realistic 3D UAV models in Great-X' (Fig.1a). Unreal 자산 기반 3-D 모… | Sionna RT (수식 출처 + 비교대상) | 플랫폼 간 일반화 오차(측위 m 단위)로만. Sionna RT 학습/Sionna RT 시험 0.309 m, Great… | ⭐ '엔진을 바꾸면 결과가 얼마나 달라지나' 에 대한 유일한 정량 자료(8.1 m vs 11.1 m 교차 일반화 오차). 우리 SBR 구현이 Sionna 스톡과 다른 답을 낼 때, '엔진 차이는 이 정도 규모' 라는 외부 눈금으로 쓸 수 있다. 단 그 수치는 측위 오… | P |
| `caviar_arxiv24` | CAVIAR: Co-Simulation of 6G Communications, 3D Scenarios and AI for Digital T… | arXiv 2401.03310<br>*PREPRINT* | 2024 | 없음 (도구·데이터셋) | ⭐ Sionna 씬 안의 드론에 재질이 배정된다 - Table V: 'Radio material (drone) ITU… | Sionna (link/PHY + RT) | 빔 선택 정확도/검색-구조 임무 성능. 산란 진폭 검증 없음(RCS 0회). | 드론 메시 + 재질을 Sionna 씬에 넣는 관행이 2024년부터 있었다는 근거. 단 '표적으로서'가 아니라 '단말로서'다. 우리 report02(드론 3D)에서 '메시를 넣는 것 자체는 새롭지 않다' 를 정직하게 인정할 때 인용. | P |
| `sionna_kpi_deviation_arxiv26` | Quantifying System Level KPI Deviations of Sionna RT | arXiv 2605.10352<br>*PREPRINT* | 2026 | 없음 (도구·데이터셋) | none; 20 Rx positions, VNA-measured channels, OAI 5G NR testbed | Sionna RT | — | Sionna RT 대 실측 KPI 편차를 정면으로 잰 논문. 'ITU 사전정의 재질로 근사' 라는 관행(우리도 겪는 문제)을 그대로 적어 두었다 — 우리 재질 가중 PO 서술의 대비군. | U |

<details><summary><b>▸ 상세 카드 14편</b> — 서지 · 수치 · 인용문 · 초안 문장</summary>

#### `lambda_dataset_arxiv26` ⭐⭐⭐ — LAMBDA: A Low-Altitude Multimodal Base Dataset for UAV Sensing and Communication

- **서지** — L. Zhou and P. Rao and C. Zhang and J. Mo and S. Sun and Z. Chen and M. Tao. *arXiv 2607.03826*, 2026. arXiv:`2607.03826`
- **상태** — PREPRINT  ·  **등급** — P
- **PDF** — `/data/public/sionna_jeong/papers_isac_sionna/2607.03826__lambda-uav-dataset.pdf`
- **조명원 / 기준신호** — source=시뮬레이션 파이프라인(UE5 + Cosys-AirSim + Blender + Sionna RT + CADFEKO) · reference_signal=CSI · band=본문 참조
- **표적 표현** — UAV · AirSim UAV 모델 · ⭐ 표적 시그니처가 광선추적 밖에서 온다 - CADFEKO 로 RCS 를 미리 계산해 자세로 조회한 뒤 Sionna 다중경로 기하에 곱한다.
- **엔진 / 실측** — Sionna RT(전파) + Altair CADFEKO(표적 RCS) 조합
- **무엇을 무엇에 대해 검증했나** — 데이터셋 품질관리 ↔ 본문 참조 - 정량 검증 미확인
- **핵심 수치** — `dataset_size_TB` = 2.04, `aligned_frames` = 517939
- **우리와의 관계** — ⭐⭐ H8 의 가장 깨끗한 증거. 2026년 Sionna 논문이 UAV 시그니처가 필요해지자 상용 EM 솔버로 나갔다 - '전파는 Sionna, 표적 산란은 딴 데서' 가 이 분야의 기본값이고, 우리는 그 둘을 한 파이프라인에 넣는다.
- ⚠ ⚠ PREPRINT.
- ⚠ ⚠ 프리프린트. ⚠ '2.04 TB / 517,939 프레임' 같은 규모 수치는 데이터셋 규모지 정확도 근거가 아니다.
  > “Sionna RT [27] for material-aware ray tracing; and CADFEKO [28] for UAV radar cross-section (RCS) modeling. The resulting dataset contains 2.04 TB of data and 517,939 aligned multimodal data frames.” — *p.3*
  > “The complex-valued CSI coefficient captures the propagation effects computed by the ray-tracing channel generator, whereas the RCS term is obtained from CADFEKO simulations of the AirSim UAV model and queried according to the UAV attitude.” — *p.7*
  > “Blender [26] for scene-mesh conversion; Sionna RT [27] for material-aware ray tracing; and CADFEKO [28] for UAV radar cross-section (RCS) modeling.” — *p.3*
- **초안 문장** — 저고도 ISAC 데이터셋 생성에서 전파는 Sionna RT 로, UAV 의 RCS 는 상용 EM 솔버(CADFEKO)로 따로 계산해 곱하는 것이 현재의 표준 관행이다(Zhou 외, arXiv:2607.03826).

#### `cellsense_arxiv26` ⭐⭐⭐ — CellSense: A Sub-6 GHz Cellular ISAC System for Clutter-Robust Passive Sensing

- **서지** — B. Kumar and I. K. Jain and V. K. Shah. *arXiv 2606.07900*, 2026. arXiv:`2606.07900`
- **상태** — PREPRINT  ·  **등급** — P
- **PDF** — `/data/public/sionna_jeong/papers_isac_sionna/2606.07900__cellsense.pdf`
- **조명원 / 기준신호** — source=5G 셀룰러 프로토콜 스택에 통합된 송신(UE) / 수신(BS) · reference_signal=3GPP 규정 대역폭·자원 설정을 따르는 OFDM · band=sub-6 GHz
- **표적 표현** — ⭐ 사람 - 드론이 아니다 · 1.8 m x 0.5 m x 0.25 m 큐보이드 · 큐보이드
- **엔진 / 실측** — Sionna 기반 OFDM 링크레벨 시뮬레이션(Blender 로 만든 실내 창고·야외 캠퍼스 씬) + USRP/OpenAirInterface 실측 시제기
- **무엇을 무엇에 대해 검증했나** — 검출확률과 오경보확률 ↔ 베이스라인 방식
- **핵심 수치** — `Pd` = 0.74, `Pfa` = 0.1, `baseline_Pd` = 0.22, `baseline_Pfa` = 0.88, `target_cuboid_m` = [1.8, 0.5, 0.25]
- **우리와의 관계** — ⭐ 우리 벤치마크와 구조가 가장 닮은 Sionna 논문(사이트별 씬 + 표적 + Pd/Pfa + 실측 시제기).
- ⚠ ⚠ PREPRINT.
- ⚠ Pfa 정의가 우리와 다르다. 숫자를 나란히 놓으면 E3.
  > “To simulate a dynamic target, we model a mobile object as a 1.8 m x 0.5 m x 0.25 m cuboid to emulate the average physiological profile of a human.” — *p.4*
  > “CellSense achieves a detection probability (Pd) of 0.74 with a low false alarm rate (Pfa = 0.10), whereas the baseline struggles at Pd = 0.22 and a prohibitive Pfa = 0.88.” — *p.5*
- **초안 문장** — 셀룰러 ISAC 패시브 센싱을 Sionna 씬과 실측 시제기로 함께 평가한 사례가 있으나 표적은 사람을 대신한 큐보이드이며(Kumar 외, arXiv:2606.07900), 오경보율도 CFAR 임계 교정이 아니라 검출 비율로 정의된다.

#### `dmsnet_arxiv26` ⭐⭐⭐ — DMSNet: Cross-Band Learning for Multi-Target Sensing in Multi-Band ISAC

- **서지** — Haotian Liu and Zhiqing Wei and Quanjiang Zhao and Lin Wang and Yunxin Geng and Xingwang Li and Zhiyong Feng. *arXiv 2607.17655*, 2026. arXiv:`2607.17655`
- **상태** — PREPRINT  ·  **등급** — P
- **PDF** — `/data/public/sionna_jeong/papers_isac_sionna/2607.17655__dmsnet-crossband-multiband-isac.pdf`
- **표적 표현** — ⭐ 미기재. 5쪽 전체에서 Sionna 를 언급하는 문장은 단 하나이고, UAV 를 씬 안에서 어떻게 표현했는지(메시/입방체/점) 한 마디도 없다. 신호모형 쪽에서는 표적이 (r, v, theta) 3-파라미터 + 복소 산란계수 rho 로만 존재하며 RCS 는 xi = \|rho\|^2 로 정의된다.
- **엔진 / 실측** — Sionna RT
- **무엇을 무엇에 대해 검증했나** — EM 검증 없음. 검증은 검출/추정 성능 벤치마크다. SNR 0 dB 표적개수추정: CA-CFAR 0.7119 / ADVI-CFAR 0.6546 / CFARNet 0.7848 / Eigenvalue-1D-CNN 0.8597 / CSIYOLO 0.8901 / DMSNet 0.9174 (Count Acc.).
- **우리와의 관계** — ⭐⭐ 우리 다중대역 서사(WiFi/LTE/5G 를 나란히 놓는 2x3 격자)의 가장 가까운 이웃. 그들은 3.5 vs 28 GHz 를 상보적이라 주장하면서 정작 표적의 주파수 의존 산란을 '가정'만 하고 계산하지 않는다 - 우리가 대역별 sigma 를 실제로 계산해 넣는 이유를 이 한 문장으로 세울 수 있다. 또 CA-CFAR 을 baseline 으로 쓰되 Pfa 교정 얘기가 없다(우리 report10 의 대비축).
- ⚠ ⚠ 프리프린트. ⚠ '표적 표현 미기재' 를 '메시를 안 썼다'로 단정하지 말 것 - 우리가 아는 것은 '적혀 있지 않다'뿐이다. 인용할 때 그대로 그렇게 쓸 것.
  > “As shown in Fig. 2, a dual-band UAV sensing dataset is generated in a 1:1 3D digital twin of the Beijing University of Posts and Telecommunications (BUPT) campus using Sionna RT [13].” — *p.3*
  > “Each scene contains L in {0, ..., 5} UAVs with r in [50, 300] m, v in [-30, 30] m/s, and theta in [-pi/3, pi/3].” — *p.4*
  > “rho_{b,l} is the frequency-selective complex scattering coefficient, and the corresponding radar cross section (RCS) is denoted by xi_{b,l} = \|rho_{b,l}\|^2 [9]. This indicates that a target weakly visible in one band may still be detectable in another band, which provides a key motivation for multi-band target detection [9]” — *p.2*
- **초안 문장** — Sionna RT 로 만든 캠퍼스 디지털트윈에서 다중대역 UAV 센싱을 학습으로 푸는 Liu 외[arXiv'26]는 고·저 대역의 표적 산란응답이 상보적이라는 전제 위에 서 있지만, UAV 가 광선추적 씬에서 어떤 형상으로 표현되었는지는 논문에 기술되어 있지 않다.

#### `clutteraware_procieee26` ⭐⭐⭐ — Clutter-Aware Integrated Sensing and Communication: Models, Methods, and Future Directions

- **서지** — R. Liu and P. Li and M. Li and A. L. Swindlehurst. *Proc. IEEE*, 2026. DOI `10.1109/JPROC.2026.3675476`
- **상태** — PUBLISHED — Proc. IEEE 114(1), Jan 2026  ·  **등급** — P  ·  ⚠ **BibTeX INCOMPLETE**
- **PDF** — `/data/public/sionna_jeong/papers_isac_sionna/new_0731/2602.10537__clutter-aware-isac_ARXIV-v2_procIEEE-accepted.pdf` · `/data/public/sionna_jeong/papers_isac_sionna/paper_sionna_Ray_0723/Clutter-Aware_Integrated_Sensing_and_Communication_Models_Methods_and_Future_Directions.pdf`
- **조명원 / 기준신호** — source=시뮬레이션(모노스태틱 ISAC 기지국, 높이 13.5 m) · reference_signal=MIMO-OFDM · band=본문 Table 3
- **표적 표현** — ⭐ 단순화 3D 드론 메시 · 공개 3D 모델을 Blender 로 단순화해 Sionna XML 로 내보낸 것 · 메시. 재질은 유연히 배정하되 산란은 Sionna 스톡(프레넬)에 맡긴다.
- **엔진 / 실측** — NVIDIA Sionna RT, 최대 상호작용 깊이 3
- **무엇을 무엇에 대해 검증했나** — ⭐ 아무것도 - 'validat*' 가 41쪽 전체에서 0회 ↔ 없음
- **핵심 수치** — `bs_height_m` = 13.5, `target_heights_m` = [10, 15], `emitter_height_m` = 5, `max_interaction_depth` = 3, `reported_SCNR_dB` = -45.9, `pages` = 41, `validate_word_count` = 0
- **우리와의 관계** — ⭐⭐ 우리 자리를 정의하는 논문. 최상위 저널이 드론 메시를 Sionna 에 넣고도 표적 산란을 검증하지 않는다는 사실이, 우리 SBR+PO 가 채우는 빈칸이다.
- ⚠ ⭐ 'validat* 0회' 는 내가 오늘 41쪽 전문에서 센 값이다(F2 재확인). 이 사실을 비판으로 쓸 때는 '검증 절이 없다'까지만 말하고 '틀렸다'로 넘어가지 말 것.
- ⚠ ⚠ UAV 는 표적이 아니라 방해물이다. '드론 검출 논문'으로 인용하면 오인용. ⚠ 게재판 Table/그림 쪽수와 arXiv v2 쪽수가 다르다.
  > “The ToI and UAVs are modeled as simplified 3-D mesh objects imported into Sionna. These meshes are obtained by simplifying publicly available 3-D models in Blender and exporting them in Sionna's XML format, which keeps the ray-tracing scene lightweight while enabling flexible material assignment.” — *p.23*
  > “The maximum interaction depth for Sionna is set to three, so each ray undergoes at most three interactions with scene objects.” — *p.23*
  > “Sionna defines the LoS as a direct Tx-Rx path, so for monostatic sensing, the target echoes appear as reflected and scattered paths that interact with the target object, even when a geometric LoS exists.” — *p.23*
- **초안 문장** — 최근의 ISAC 종설은 단순화한 드론 메시를 Sionna 광선추적 씬에 넣어 클러터 환경을 site-specific 하게 생성하지만, 표적 산란 자체는 스톡 프레넬 반사에 맡기고 그 정확성을 검증하지 않는다(Liu 외, Proceedings of the IEEE 114(1), 2026).

#### `wang_neural_isac_jsac25` ⭐⭐ — Neural Integrated Sensing and Communication for the MIMO-OFDM Downlink

- **서지** — Z. Wang and F. Zumegen and C. Studer. *IEEE J. Sel. Areas Commun.*, 2025
- **상태** — ACCEPTED_TO_APPEAR — p.1 헤더 'TO APPEAR IN'; 프리프린트 arXiv:2509.21118  ·  **등급** — P  ·  ⚠ **BibTeX INCOMPLETE**
- **PDF** — `/data/public/sionna_jeong/sionna_papers_by_task/isac_sensing_radar/2509.21118__wang-neural-isac-mimo-ofdm.pdf`
- **조명원 / 기준신호** — source=MIMO-OFDM 다운링크 · reference_signal=다운링크 전 파형 · band=본문 참조
- **표적 표현** — 표적에 재질과 형상 정보가 붙는다 · Blender 로 만든 씬 시드를 XML 로 내보낸 것 · 메시
- **엔진 / 실측** — NVIDIA Sionna (CIR 생성) + 학습 기반 검출
- **무엇을 무엇에 대해 검증했나** — 센싱·통신 동시 성능 ↔ 본문 참조
- **우리와의 관계** — ⭐ 우리 다중 Rx 실험 설계 서술에 인용할 수 있는 운영 제약을 명시한 드문 논문 - 한 Sionna 씬 안에서는 모든 Rx 의 패턴이 같아야 한다.
- ⚠ 게재 확정이지만 권·호·쪽이 없다. 'to appear' 로 인용할 것.
  > “Since the Sionna platform limits that in one Sionna scene, the pattern of Rxs must be same, the CIRs for Rxs with different patterns cannot be generated in one Sionna scene.” — *p.6*
  > “a Sionna scene seed including the material properties and shape information of the targets and the non-target environment” — *p.6*
- **초안 문장** — Sionna 씬 하나에서는 모든 수신기의 안테나 패턴이 같아야 하므로 서로 다른 패턴의 다중 수신기를 다루려면 씬을 나눠야 한다는 제약이 문헌에 명시되어 있다(Wang 외, IEEE JSAC, to appear).

#### `openisac_arxiv26`  — OpenISAC: An Open-Source Real-Time Experimentation Platform for OFDM-ISAC

- **서지** — *arXiv 2601.03535*, 2026. arXiv:`2601.03535`
- **상태** — PREPRINT — 저자·게재처 미확정  ·  **등급** — P  ·  ⚠ **BibTeX INCOMPLETE**
- **PDF** — `/data/public/sionna_jeong/papers_isac_sionna/2601.03535__openisac.pdf`
- **표적 표현** — 해당 없음(Sionna 씬 없음).
- **엔진 / 실측** — 인용만 - 'NVIDIA Sionna and the Sionna Research Kit are also important open-source tools'; 참고문헌에 version 2.0.1 명시
- **무엇을 무엇에 대해 검증했나** — 플랫폼 실증. CFAR/Pfa/Pd 는 0회(이전 세션 H9 확인, 이번 세션 term-count 재확인).
- **우리와의 관계** — 우리 그룹미팅 덱의 주제이기도 함. 교집합 목록에는 '인용만' 사례로 남겨 둔다 - 자동 계수(sionna>=1)가 교집합으로 오분류하기 쉬운 대표 함정.
- ⚠ ⚠ Sionna 를 '쓰지' 않는다. 기계 계수만 보고 교집합에 넣으면 오분류.
  > “For a specific reflection p with radar cross section (RCS) sigma_{RCS,p}, range d_{s,p}, and radial velocity v_{s,p}, the complex scattering coefficient, round-trip delay, and two-way Doppler shift are modeled as” — *p.4*
- **초안 문장** — OFDM-ISAC 실시간 실험 플랫폼이 오픈소스로 공개되어 있다(OpenISAC, arXiv:2601.03535).

#### `rfgenesis_sensys23` ⭐⭐⭐ — RF Genesis: Zero-Shot Generalization of mmWave Sensing through Simulation-Based Data Synthesis and Generative Diffusion Models

- **서지** — *Proc. 21st ACM Conf. Embedded Networked Sensor Systems (SenSys)*, 2023. DOI `10.1145/3625687.3625798`
- **상태** — PUBLISHED — ACM SenSys 2023  ·  **등급** — P  ·  ⚠ **BibTeX INCOMPLETE**
- **PDF** — 디스크에 없음
- **우리와의 관계** — RadarTwin(B04)이 자기 파이프라인의 기반으로 삼는 논문. 우리 방법을 SenSys/MobiSys 계열에 제출한다면 이 논문이 직접 비교 기준이 된다.
- ⚠ ⚠ 원문 미확보. 수치·주장은 인용하지 말고 존재와 게재처만 인용할 것.
- **초안 문장** — 사람 메시를 광선추적기에 통과시켜 mmWave 레이더 원신호를 합성하는 파이프라인은 SenSys 2023 에서 확립되었으며, 메시에서 레이더 에코까지 잇는 접근의 최상위 학회 기준선이다(RF Genesis).

#### `radartwin_arxiv26`  — RadarTwin: Scene-Specific mmWave Radar Simulation and Learning for Mobile Indoor Perception

- **서지** — Emily Bejerano and Federico Tondolo and Devang Gupta and Aaron Mano Cherian and Taeyoo Kim and Ayaan Qayyum and Xiaofan Yu and others. *arXiv 2606.28396*, 2026. arXiv:`2606.28396`
- **상태** — PREPRINT  ·  **등급** — P
- **PDF** — `/data/public/sionna_jeong/reference_library/2606.28396__radartwin.pdf`
- **우리와의 관계** — ⭐ 우리 SBR 설계의 외부 정당화 3종: (1) Fresnel 을 ITU-R P.2040-4 로 갈아끼우는 것이 표준 관행이라는 근거, (2) 반사 차수(4-bounce) 를 '경험적으로' 정하는 것이 허용된다는 근거, (3) 시뮬이 메시 전체를 보는 반면 실제 레이더는 못 푸는 차원이 있어 sim-real 불일치가 생긴다는 정직한 경고 - 우리 mesh vs 실측 대조 서술에 그대로 쓸 수 있다.
- ⚠ ⚠ 드론 아님, Sionna 아님(인용만). 교집합이 아니라 방법 경계선.
  > “The simulator builds on Mitsuba 3 [16] (cuda_ad_rgb variant, CUDA backend) and the RF-Genesis ray-tracing pipeline [6], with material physics replaced to follow ITU-R P.2040-4 [15] on a per-surface basis.” — *p.5*
  > “Real radar cross section (RCS) does not increase consistently with can size. ... The simulator sees the full mesh and can introduce a size-brightness trend that the real system cannot resolve.” — *p.8*
  > “Rays are cast once from the sensor position and Fresnel reflection is evaluated at every ray-surface intersection, recursing up to four bounces. The four-bounce limit is validated empirically” — *p.5*
- **초안 문장** — 메시를 Mitsuba 기반 렌더러에 통과시켜 FMCW 원신호를 합성하고 실측과 짝지어 검증하는 파이프라인이 실내 인지 맥락에서 제시되었다(RadarTwin, arXiv:2606.28396).

#### `sionna_lib_arxiv22` ⭐⭐⭐ — Sionna: An Open-Source Library for Next-Generation Physical Layer Research

- **서지** — J. Hoydis and S. Cammerer and F. Ait Aoudia and A. Vem and N. Binder and G. Marcus and A. Keller. *arXiv 2203.11854*, 2022. arXiv:`2203.11854`
- **상태** — PREPRINT (arXiv)  ·  **등급** — P
- **PDF** — `/data/public/sionna_jeong/sionna_papers_by_task/channel_modeling_raytracing/2303.11103__sionna-rt-founding.pdf` · `/data/public/sionna_jeong/sionna_papers_by_task/channel_modeling_raytracing/2504.21719__sionna-rt-technical-report-v1.pdf` · `/data/public/sionna_jeong/sionna_papers_by_task/dataset_tooling/2203.11854__sionna-library-founding.pdf`
- **조명원 / 기준신호** — source=해당 없음 · reference_signal=해당 없음 · band=해당 없음
- **표적 표현** — ⭐ 없다 - 이 문서들에서 'target' 은 경로의 끝점을 뜻한다
- **엔진 / 실측** — 도구 자체
- **무엇을 무엇에 대해 검증했나** — 해당 없음 ↔ 해당 없음
- **핵심 수치** — `sbr_mentions_in_tech_report` = 48, `interaction_types` = 4
- **우리와의 관계** — Sionna 계보의 출발점(0.8.0, RT 없음). 우리 report01 의 근거 문서.
- ⚠ ⭐ (b) 는 v0.14(TensorFlow) 아키텍처 서술이라 우리가 돌리는 2.0.1 과 다르다. EM 세부는 (c) 기술보고서를 인용할 것.
- ⚠ (c) 는 벤더 기술보고서다. 동료심사 문헌이 아니다.
  > “3.1. Generating Candidates by Shooting and Bouncing of Rays (SBR) The candidate generator utilizes the SBR-based method as illustrated in Figure 10.” — *(c) p.12*
  > “Sionna RT currently supports four types of interactions with scene objects: Specular reflection (R) ... Diffuse reflection (S) ... Refraction (T)” — *(c) p.9*
  > “Sionna RT supports specular and diffuse reflections (i.e., scattering) as well as first-order diffraction.” — *(b) p.3*
- **초안 문장** — Sionna 는 GPU 위의 미분가능 링크레벨 시뮬레이션 라이브러리로 출발했으며, 그 초기 판(0.8.0)에는 광선추적이 없었다(Hoydis 외, arXiv:2203.11854).

#### `sionna_rt_globecom23` ⭐⭐⭐ — Sionna RT: Differentiable Ray Tracing for Radio Propagation Modeling

- **서지** — J. Hoydis and F. Ait Aoudia and S. Cammerer and M. Nimier-David and N. Binder and G. Marcus and A. Keller. *Proc. IEEE Globecom Workshops*, 2023
- **상태** — ⚠ 디스크 파일은 arXiv:2303.11103v2 프리프린트; 게재 정보(GLOBECOM Wkshps 2023, pp.317-321)는 아카이브 내부 2차 인용 2건에서 왔다  ·  **등급** — P  ·  ⚠ **BibTeX INCOMPLETE**
- **PDF** — `/data/public/sionna_jeong/sionna_papers_by_task/channel_modeling_raytracing/2303.11103__sionna-rt-founding.pdf` · `/data/public/sionna_jeong/sionna_papers_by_task/channel_modeling_raytracing/2504.21719__sionna-rt-technical-report-v1.pdf` · `/data/public/sionna_jeong/sionna_papers_by_task/dataset_tooling/2203.11854__sionna-library-founding.pdf`
- **조명원 / 기준신호** — source=해당 없음 · reference_signal=해당 없음 · band=해당 없음
- **표적 표현** — ⭐ 없다 - 이 문서들에서 'target' 은 경로의 끝점을 뜻한다
- **엔진 / 실측** — 도구 자체
- **무엇을 무엇에 대해 검증했나** — 해당 없음 ↔ 해당 없음
- **핵심 수치** — `sbr_mentions_in_tech_report` = 48, `interaction_types` = 4
- **우리와의 관계** — Sionna RT 의 원전 회의 논문. 우리가 쓰는 광선추적기의 출처.
- ⚠ ⭐ (b) 는 v0.14(TensorFlow) 아키텍처 서술이라 우리가 돌리는 2.0.1 과 다르다. EM 세부는 (c) 기술보고서를 인용할 것.
- ⚠ (c) 는 벤더 기술보고서다. 동료심사 문헌이 아니다.
  > “3.1. Generating Candidates by Shooting and Bouncing of Rays (SBR) The candidate generator utilizes the SBR-based method as illustrated in Figure 10.” — *(c) p.12*
  > “Sionna RT currently supports four types of interactions with scene objects: Specular reflection (R) ... Diffuse reflection (S) ... Refraction (T)” — *(c) p.9*
  > “Sionna RT supports specular and diffuse reflections (i.e., scattering) as well as first-order diffraction.” — *(b) p.3*
- **초안 문장** — Sionna RT 는 미분가능 광선추적을 무선 전파 모델링에 도입한 확장이다(Hoydis 외, IEEE GLOBECOM Workshops 2023).

#### `sionna_rt_techreport25` ⭐⭐⭐ — Sionna RT: Technical Report

- **서지** — F. Ait Aoudia and J. Hoydis and M. Nimier-David and B. Nicolet and S. Cammerer and A. Keller. *arXiv 2504.21719*, 2025. arXiv:`2504.21719`
- **상태** — PREPRINT / 벤더 기술보고서  ·  **등급** — P
- **PDF** — `/data/public/sionna_jeong/sionna_papers_by_task/channel_modeling_raytracing/2303.11103__sionna-rt-founding.pdf` · `/data/public/sionna_jeong/sionna_papers_by_task/channel_modeling_raytracing/2504.21719__sionna-rt-technical-report-v1.pdf` · `/data/public/sionna_jeong/sionna_papers_by_task/dataset_tooling/2203.11854__sionna-library-founding.pdf`
- **조명원 / 기준신호** — source=해당 없음 · reference_signal=해당 없음 · band=해당 없음
- **표적 표현** — ⭐ 없다 - 이 문서들에서 'target' 은 경로의 끝점을 뜻한다
- **엔진 / 실측** — 도구 자체
- **무엇을 무엇에 대해 검증했나** — 해당 없음 ↔ 해당 없음
- **핵심 수치** — `sbr_mentions_in_tech_report` = 48, `interaction_types` = 4
- **우리와의 관계** — ⭐ 우리 report01·06 의 근거 문서 — Sionna 가 무엇을 하고 무엇을 안 하는지(SBR 있음 / PO 표면적분·RCS 출력 없음)의 1차 출처.
- ⚠ ⭐ (b) 는 v0.14(TensorFlow) 아키텍처 서술이라 우리가 돌리는 2.0.1 과 다르다. EM 세부는 (c) 기술보고서를 인용할 것.
- ⚠ (c) 는 벤더 기술보고서다. 동료심사 문헌이 아니다.
  > “3.1. Generating Candidates by Shooting and Bouncing of Rays (SBR) The candidate generator utilizes the SBR-based method as illustrated in Figure 10.” — *(c) p.12*
  > “Sionna RT currently supports four types of interactions with scene objects: Specular reflection (R) ... Diffuse reflection (S) ... Refraction (T)” — *(c) p.9*
  > “Sionna RT supports specular and diffuse reflections (i.e., scattering) as well as first-order diffraction.” — *(b) p.3*
- **초안 문장** — Sionna RT 는 경로 후보를 shooting-and-bouncing rays 로 생성하고 정반사·확산반사·굴절·1차 회절을 지원하지만, 물리광학 표면전류 적분과 RCS 출력은 제공하지 않는다(Ait Aoudia 외, Sionna RT Technical Report; Hoydis 외, Sionna RT).

#### `rt_limits_learning_2026` ⭐⭐ — On the Limitations of Ray-Tracing for Learning-Based RF Tasks

- **서지** — *arXiv 2507.19653*, 2026. arXiv:`2507.19653`
- **상태** — ⚠ p.1 에 '(c)2026 IEEE' 저작권 줄이 있으나 게재처 이름이 인쇄되어 있지 않다  ·  **등급** — U  ·  ⚠ **BibTeX INCOMPLETE**
- **PDF** — `/data/public/sionna_jeong/sionna_papers_by_task/channel_modeling_raytracing/2507.19653__manukyan-rt-limitations-urban.pdf`
- **표적 표현** — none (1664 real UE positions, 6 BS sites, central Rome)
- **엔진 / 실측** — Sionna RT
- **우리와의 관계** — ⭐ Sionna 결과를 실측과 대조한 몇 안 되는 논문이자 버전을 명시한 논문. 우리가 '시뮬 결과의 신뢰구간' 을 말할 때 인용할 외부 근거. 안테나 배치·방위가 solver 파라미터보다 오차를 지배한다는 결론도 우리 관측 설계에 직결.
- **초안 문장** — 광선추적으로 만든 데이터가 학습 기반 RF 과제에서 갖는 한계는 별도로 정량화되어 있다(arXiv:2507.19653).

#### `greatx_arxiv25`  — Unreal Is All You Need: Multimodal ISAC Data Simulation with Only One Engine

- **서지** — Kongwu Huang and Shiyi Mu and Jun Jiang and Yuan Gao and Shugong Xu. *arXiv 2507.08716*, 2025. arXiv:`2507.08716`
- **상태** — PREPRINT  ·  **등급** — P
- **PDF** — `/data/public/sionna_jeong/papers_isac_sionna/2507.08716__great-x_unreal-isac.pdf`
- **표적 표현** — 'Realistic 3D UAV models in Great-X' (Fig.1a). Unreal 자산 기반 3-D 모델.
- **엔진 / 실측** — Sionna RT (수식 출처 + 비교대상)
- **무엇을 무엇에 대해 검증했나** — 플랫폼 간 일반화 오차(측위 m 단위)로만. Sionna RT 학습/Sionna RT 시험 0.309 m, Great-MSD/Great-MSD 0.647 m, Sionna->Great-MSD 11.082 m, Great-MSD->Sionna 8.107 m.
- **우리와의 관계** — ⭐ '엔진을 바꾸면 결과가 얼마나 달라지나' 에 대한 유일한 정량 자료(8.1 m vs 11.1 m 교차 일반화 오차). 우리 SBR 구현이 Sionna 스톡과 다른 답을 낼 때, '엔진 차이는 이 정도 규모' 라는 외부 눈금으로 쓸 수 있다. 단 그 수치는 측위 오차이지 산란 진폭 오차가 아니다.
- ⚠ ⚠ X01(md-rt)과 동일 연구실. ⚠ 프리프린트. ⚠ 'Sionna 보다 정밀' 주장은 렌더러 기하/텍스처에 대한 것이지 EM 정확도 비교가 아니다.
  > “This single-engine multimodal data twin platform reconstructs the ray-tracing computation of Sionna within Unreal Engine” — *p.1*
  > “The following formulas are referenced from SionnaRT [13].” — *p.2*
  > “To assess the effectiveness of the simulation platform, we conducted a bidirectional cross-platform evaluation between Great-X and SionnaRT. Both platforms used identical map configurations and consistent parameters.” — *p.4*
- **초안 문장** — 단일 게임 엔진 안에서 다중모달 ISAC 데이터를 합성하려는 시도도 있다(Great-X, arXiv:2507.08716).

#### `caviar_arxiv24`  — CAVIAR: Co-Simulation of 6G Communications, 3D Scenarios and AI for Digital Twins

- **서지** — João Borges and Felipe Bastos and Ilan Correa and Pedro Batista and Aldebaro Klautau. *arXiv 2401.03310*, 2024. arXiv:`2401.03310`
- **상태** — PREPRINT — p.1 'This work has been submitted to the IEEE...'  ·  **등급** — P
- **PDF** — `/data/public/sionna_jeong/papers_isac_sionna/2401.03310__caviar-digital-twin.pdf`
- **표적 표현** — ⭐ Sionna 씬 안의 드론에 재질이 배정된다 - Table V: 'Radio material (drone) ITU metal', 반송파 40 GHz. 메시는 Blender decimation 으로 단순화하고 텍스처는 제거.
- **엔진 / 실측** — Sionna (link/PHY + RT)
- **무엇을 무엇에 대해 검증했나** — 빔 선택 정확도/검색-구조 임무 성능. 산란 진폭 검증 없음(RCS 0회).
- **우리와의 관계** — 드론 메시 + 재질을 Sionna 씬에 넣는 관행이 2024년부터 있었다는 근거. 단 '표적으로서'가 아니라 '단말로서'다. 우리 report02(드론 3D)에서 '메시를 넣는 것 자체는 새롭지 않다' 를 정직하게 인정할 때 인용.
- ⚠ ⚠ 드론 검출 논문 아님. ⚠ 프리프린트.
  > “Sionna scene parameters ... Carrier frequency 40 GHz / Radio material (building and ground) ITU concrete / Radio material (drone) ITU metal / Synthetic array True” — *p.Table V*
  > “Each UAV is instantiated as a smart vehicle in AirSim, the 3D module, and as a receiver in Sionna, the Communications module.” — *p.Sec.V*
  > “The version used in Sionna does not use textures and underwent a slight simplification using the decimation modifier in Blender.” — *p.Sec.V*
- **초안 문장** — 6G 통신과 3D 시나리오, AI 를 공동 시뮬레이션하는 디지털 트윈 프레임워크에서 드론은 표적이 아니라 통신 종단으로 등장한다(CAVIAR, arXiv:2401.03310).

</details>

## 3. Sionna 표

아카이브 고유 PDF **218편** 중 **140편**이 본문에서 Sionna 를 언급하고 **137편**이 실제로 돌린다. 역할별로는 전파만 **118편**, 표적을 씬 안에 둔 것 **7편**, 엔진을 고친 것 **3편**이며, **Sionna 에서 dBsm 을 실제로 찍은 논문은 1편**뿐이다. Sionna 버전을 밝힌 논문은 18편, 안 밝힌 논문이 122편이다.

> **엔진 사실.** Sionna RT technical report 에서 SBR 48회, physical optics 0회, radar cross section 0회(outputs/prior_settled_sionna.json). 'Sionna 는 SBR 이 없다'는 거짓이고, 없는 것은 표면전류 PO 적분과 RCS 출력이다.

아래는 전파만 다루는 다수를 걷어내고 **역할이 구별되는 논문 + 정독한 논문**만 남긴 것이다.

| 논문 | 게재처 · 상태 | Sionna 버전 | 역할 | 표적 표현 | 표적 산란을 계산했나 | dBsm 출력 |
|---|---|---|---|---|---|---|
| Sionna RT: Differentiable Ray Tracing | arXiv:2303.11103v2 on disk; secondary sourc…<br>*PREPRINT_PDF_ON_DISK / venue PUBL…* | `v0.14` | 원전 문서 | none | **NO** | no |
| Sionna RT: Technical Report | arXiv preprint / vendor technical report<br>*PREPRINT* | `0.19.2, 1.0` | 원전 문서 | none - 'target' in this document means a path endpoint | **NO** | no |
| Sionna: An Open-Source Library for | arXiv:2203.11854 (per S2: arXiv.org, 503 ci…<br>*PREPRINT* | `0.8.0` | 원전 문서 | none (no RT in this version) | **NO** | no |
| AI-Empowered Low-Altitude Economy: Cooperative Sensing With Fixed… | page-1 venue string: IEEE ICC (per archive …<br>*PREPRINT_PDF (venue per archive f…* | `미기재` | 표적이 씬 안에 (산란은 스톡) | 'The UAV is modeled as a metallic cube' at (x,y,60) m | **YES** | no |
| CellSense: A Sub-6 GHz Cellular ISAC System for Clutter-Robust Pa… | arXiv:2606.07900<br>*PREPRINT* | `미기재` | 표적이 씬 안에 (산란은 스톡) | 'we model a mobile object as a 1.8 m x 0.5 m x 0.25 m cuboid … | **YES** | no |
| Clutter-Aware Integrated Sensing and Communication: Models, Metho… | arXiv:2602.10537v2 - the SAME work as Proc.…<br>*PREPRINT_OF_A_PUBLISHED_ARTICLE* | `미기재` | 표적이 씬 안에 (산란은 스톡) | simplified 3-D UAV/ToI meshes imported into Sionna (identical… | **YES** | no |
| Clutter-Aware Integrated Sensing and Communication: Models, Metho… | Proceedings of the IEEE, vol. 114, no. 1, J…<br>*PUBLISHED* | `미기재` | 표적이 씬 안에 (산란은 스톡) | 'The ToI and UAVs are modeled as simplified 3-D mesh objects … | **YES** | no |
| Micro-Doppler Signature Simulation of Multirotor UAVs Using Ray T… | 2025 IEEE 25th Int. Conf. Communication Tec…<br>*PUBLISHED* | `미기재` | 엔진 개조 + 표적이 씬 안에 | ONE rotating propeller: Sionna built-in reflector, then 1/2/3… | **YES** | no |
| Neural Integrated Sensing and Communication for the MIMO-OFDM Dow… | IEEE Journal on Selected Areas in Communica…<br>*ACCEPTED_TO_APPEAR* | `미기재` | 표적이 씬 안에 (산란은 스톡) | targets carry 'material properties and shape information' ins… | **YES** | no |
| Ray-Based Simulation of Multistatic Scattering from Target Object… | 2025 19th European Conference on Antennas a…<br>*PUBLISHED* | `미기재` | 엔진 개조 + 표적이 씬 안에 | faceted car mesh (avg facet ~2 lambda at 10 GHz, 3.3 x 2.1 x … | **YES** | YES |
| DeepRT Engine: A Unified GPU-Parallel Ray-Tracing Framework with … | arXiv:2607.11743v1, 13 Jul 2026 (LaTeX jour…<br>*PREPRINT* | `미기재` | 경쟁 엔진 | none (propagation benchmark vs Wireless InSite and Sionna) | **NO** | no |
| Learning Radio Environments by | arXiv:2311.18558v1; archive published_by_ve…<br>*PREPRINT_PDF (venue per secondary…* | `미기재` | 저자(NVIDIA)가 확장 | none - material/antenna/scattering-pattern parameters are the… | **NO** | no |
| Ray-Based Simulation of Scattering from Discretized Curved Bodies… | arXiv:2604.05991v2, 2 Jul 2026 - NO venue h…<br>*PREPRINT* | `0.19 (stated verbatim)` | 엔진 개조 | faceted (discretized) curved bodies - car model; PEC-ish, mir… | **YES** | no |
| LAMBDA: A Low-Altitude Multimodal Base Dataset for UAV Sensing an… | arXiv:2607.03826v1, 4 Jul 2026<br>*PREPRINT* | `미기재` | 표적 시그니처를 외부 솔버에서 주입 | UAV RCS comes from Altair CADFEKO simulations of the AirSim U… | **NO** | no |
| Analysis and Prediction of Coverage and Channel | arXiv:2502.10324<br>*PREPRINT* | `미기재` | 전파만 (표적 없음) | UAV is a RADIO ENDPOINT, not a target; custom-modeled trees a… | **NO** | no |
| CISSIR: Beam Codebooks with Self-Interference Reduction Guarantee… | page-1 header 'ACCEPTED DRAFT V3.1.3'; arch…<br>*ACCEPTED (venue per secondary sou…* | `미기재` | 전파만 (링크레벨) | analytic steering-vector target for sensing SNR; no scene tar… | **NO** | no |
| DMSNet: Cross-Band Learning for Multi-Target Sensing in Multi-Ban… | arXiv:2607.17655<br>*PREPRINT* | `미기재` | 전파만 (데이터셋) | UAV sensing dataset in a 1:1 digital twin; the paper does not… | **NO** | no |
| DT-RaDaR: Digital Twin Assisted Robot | arXiv:2411.12284<br>*PREPRINT* | `미기재` | 전파만 (표적 없음) | scene furniture/vehicles are ordinary scene objects with ITU … | **NO** | no |
| Deterministic Modeling of Dynamic ISAC Channels in RF Digital Twi… | not stated in the PDF (no venue header, no …<br>*UNKNOWN* | `미기재` | 전파만 (표적 없음) | scatterer abstraction; three-level scattering abstraction wit… | **NO** | no |
| End-to-End Human Pose Reconstruction from | arXiv:2503.04860<br>*PREPRINT* | `미기재` | 전파만 (표적 없음) | none - the human is sensed by wearable IMUs, not by RF scatte… | **NO** | no |
| Ns3 meets Sionna: Using Realistic Channels in | arXiv:2412.20524 (per S2 arXiv.org, 11 cita…<br>*PREPRINT* | `미기재` | 다른 시뮬레이터와 통합 | none | **NO** | no |
| On the Limitations of Ray-Tracing for Learning-Based RF Tasks in … | IEEE copyright line '(c)2026 IEEE' on page …<br>*PUBLISHED_IEEE_UNNAMED_VENUE* | `1.0.2 (stated verbatim)` | 전파만 (표적 없음) | none (1664 real UE positions, 6 BS sites, central Rome) | **NO** | no |
| OpenISAC: An Open-Source Real-Time Experimentation Platform for O… | arXiv:2601.03535v2, 6 Jul 2026<br>*PREPRINT* | `미기재` | 인용만 (미사용) | n/a (USRP testbed) | **NO** | no |
| Quantifying System Level KPI Deviations of Sionna RT: Material an… | arXiv:2605.10352<br>*PREPRINT* | `1.2.1 (stated verbatim)` | 전파만 (표적 없음) | none; 20 Rx positions, VNA-measured channels, OAI 5G NR testb… | **NO** | no |
| RayLoc: Wireless Indoor Localization via Fully Differentiable Ray… | arXiv:2501.17881v1<br>*PREPRINT* | `미기재` | 인용만, 그러나 논지 지탱 | device-free target as a scene object in their OWN differentia… | **NO** | no |
| SimART: A Unified and Open Real-world Multimodal Simulation Platf… | arXiv:2605.13309v1, 13 May 2026<br>*PREPRINT* | `미기재` | 전파만 (표적 없음) | none as a scatterer: the RT module loads a geometrically simp… | **NO** | no |
| Sionna Research Kit: A GPU-Accelerated Research Platform for AI-R… | arXiv:2505.15848v1, 19 May 2025<br>*PREPRINT* | `미기재` | 플랫폼 | none | **NO** | no |
| Super-Resolution Experimental Validation and Polarimetric Extensi… | arXiv:2605.31267<br>*PREPRINT* | `미기재` | 인용만, 그러나 논지 지탱 | rough surfaces, 266 angular configurations, all polarisation … | **NO** | no |
| TITAN: Twin-Informed Topology Adaptation for LAWN-enabled D2C Com… | arXiv:2603.00795<br>*PREPRINT* | `1.2` | 전파만 (표적 없음) | UAVs are relays (radio endpoints), not targets | **NO** | no |
| Temporal Graph Neural Network for ISAC Target Detection and Track… | arXiv:2604.08306v1, 9 Apr 2026<br>*PREPRINT* | `미기재` | 전파 + 해석적 표적 주입 (h = h_bg + h_targ… | POINT SCATTERER: target-related path gain carries an analytic… | **NO** | no |

**역할 분류 정의**

- `PRIMARY_DOC` — Sionna's own documentation papers.
- `PROPAGATION_ONLY` — Sionna computes propagation between radio endpoints. No radar target anywhere.
- `PROPAGATION_ONLY_PLUS_ANALYTIC_TARGET` — Sionna gives the background CIR; the target echo is added analytically (point scatterer with an assumed RCS). This is the mainstream h = h_bg + h_target.
- `TARGET_IN_SCENE` — A physical object stands in for the target inside the ray-traced scene (mesh, cube, cuboid) and its echo comes out of the stock interaction set.
- `TARGET_INJECTED_EXTERNAL` — The target signature is computed by a different EM tool and multiplied onto Sionna geometry.
- `ENGINE_MODIFIED` — The paper changed Sionna itself (sampler, diffraction, materials).
- `ENGINE_EXTENDED_BY_AUTHORS` — Extension written by Sionna's own authors.
- `TOOLING_INTEGRATION / TOOLING_PLATFORM` — Sionna wired into another simulator or platform.
- `COMPETING_ENGINE` — A different ray engine that benchmarks against Sionna.
- `CITE_ONLY` — Sionna named in prose or bibliography only; no simulation run.

## 4. ⭐⭐ 교집합 표 — Sionna AND 드론 센싱

Sionna(또는 동급 GPU 광선엔진) 시뮬레이션 AND 드론이 센싱 표적 — 사용자가 '가장 값지다' 고 지목한 교집합.

> **결론.** ⭐ H8 은 살아남았다. 교집합 8편(+경계 6편)을 이번 세션에 원문으로 다시 열어 프롱 채점한 결과, 네 프롱을 동시에 만족하는 논문은 0편이다. 우리 포지셔닝을 바꿀 필요는 없다. 다만 프롱별 최대치는 P1·P2·P3 를 동시에 만족하는 Clutter-Aware ISAC(Proc. IEEE 114(1))이며, 그 논문은 P4(진폭 검증)가 통째로 없다 - 본문 41쪽에 'validat' 0회, 'dBsm' 0회를 이번에 직접 세었다.

**H8 4-프롱**

| 프롱 | 정의 |
|---|---|
| **P1** | 동료심사 게재(저널/학회 프로시딩/표준화기구 프로시딩). arXiv 단독은 불가. 단, 원고 안에 '명시된 동료심사 게재처에 accepted' 라고 적혀 있으면 인정. |
| **P2** | UAV 가 기체의 3-D 표면 메시로 표현됨. 금속 정육면체·점산란체·단일 로터 블레이드·추상 복소계수는 불가. |
| **P3** | 산란장이 Sionna급 미분가능 GPU 광선엔진 '내부'에서 계산됨(Sionna RT, 그 in-place 확장, 또는 동급 GPU path-tracing EM 엔진). FEKO/CST/FDTD 에서 RCS 를 구해 광선경로에 곱하는 것은 주입이며 불가. |
| **P4** | 계산된 산란 '진폭'(RCS·반사도·에코전력)을 측정 또는 기준 full-wave/해석해와 대조. 도플러 주파수 위치·회전주기·스펙트로그램 리지 모양 일치는 운동학적 일치이므로 불가. |

| # | 논문 | 게재처 · 상태 | 드론 표현 | 스톡 너머 | 기하 | 무엇을 검증했나 | P1 | P2 | P3 | P4 |
|---|---|---|---|---|---|---|---|---|---|---|
| X01 | Micro-Doppler Signature Simulation of Multirotor UAVs Usi… | 2025 IEEE 25th International Confer…<br>*PUBLISHED - 근거 2겹: (a) PDF p1 에 '…* | 프로펠러 1개(블레이드 2장)만. 기체 없음. Blender 로 만든 프로펠러 물리모델 또는 Sio… | 산란물리는 스톡. 다만 '엔진 개조'가 있다 - 광선 방출 샘플링을 구면->원뿔로… | A (능동 모노스태틱) | 운동학만. p4(인쇄 362쪽): 'According to Eq. (7), the calculate… | YES | PARTIAL - 프로펠러 1개뿐, 기체 표면… | YES | NO - 자기 해석식과의 운동학 일치뿐 |
| X02 | Clutter-Aware Integrated Sensing and Communication: Model… | Proceedings of the IEEE<br>*PUBLISHED - PDF 러닝풋 'PROCEEDINGS …* | ⭐ UAV 가 '단순화된 3-D 메시'로 Sionna 씬 안에 실제로 들어간다. 공개 3D 모델을 … | 없음. 스톡 Sionna, max interaction depth = 3. 표적 … | A + 외부 방사원 혼합 | ⭐ 아무것도. 게재판 41쪽 전체에서 'validat' 0회, 'dBsm' 0회 (이번 세션 정규식… | YES | YES - 단순화 UAV 표면메시 | YES - Sionna RT 내부 | NO - 진폭 검증 전무(validat 0회) |
| X03 | AI-Empowered Low-Altitude Economy: Cooperative Sensing Wi… | arXiv preprint<br>*⚠ PREPRINT. ⭐ 종전 기록 정정: 아카이브가 이 파…* | ⭐ 금속 정육면체. 형상·재질·회전날개 전부 없음. 위치 (x,y,60) m, x,y ~ U[-75… | 없음. 표적 라벨조차 Sionna 가 붙여주는 path type(diffuse r… | 바이스태틱(단, 조명원이 자… | EM 검증 없음. 검증되는 것은 검출/측위 성능이다: MDP 0.63%, 95% 신뢰 측위오차 6.… | NO (이 원고는 preprint; 부… | NO - 금속 정육면체 | YES - Sionna RT | NO |
| X04 | DMSNet: Cross-Band Learning for Multi-Target Sensing in M… | arXiv preprint<br>*⚠ PREPRINT (arXiv 스탬프 'arXiv:2607…* | ⭐ 미기재. 5쪽 전체에서 Sionna 를 언급하는 문장은 단 하나이고, UAV 를 씬 안에서 어떻… | 없음(그리고 있었는지조차 서술되지 않음). | A (능동 모노스태틱, 다중… | EM 검증 없음. 검증은 검출/추정 성능 벤치마크다. SNR 0 dB 표적개수추정: CA-CFAR … | NO | NO - 표현 자체가 미기재 | YES - Sionna RT 로 데이터… | NO |
| X05 | LAMBDA: A Low-Altitude Multimodal Base Dataset for UAV Se… | arXiv preprint<br>*⚠ PREPRINT (arXiv 스탬프 직접 확인). 데이터…* | Cosys-AirSim 의 UAV 모델(3-D). 단, 그 형상의 산란은 Sionna 가 아니라 C… | ⭐ 엔진 밖에서. Sionna 는 재질인지 광선추적으로 다중경로 기하만 주고, U… | A (기지국/노변장치가 UA… | 진폭 검증 아님. 'quality control' 이 확인하는 것은 아카이브 무결성·모달리티 존재·… | NO | YES - AirSim UAV 3-D 모델 | NO - 산란은 CADFEKO(주입) | NO |
| X06 | Unreal is all you need: Multimodal ISAC Data Simulation w… | arXiv preprint<br>*⚠ PREPRINT (arXiv 스탬프 'arXiv:2507…* | 'Realistic 3D UAV models in Great-X' (Fig.1a). Unreal 자… | 없음 - 오히려 Sionna 의 반사/굴절/산란 공식을 그대로 옮긴다('The f… | 기지국-UAV 링크(측위).… | 플랫폼 간 일반화 오차(측위 m 단위)로만. Sionna RT 학습/Sionna RT 시험 0.30… | NO | YES - 현실적 3D UAV 모델 | PARTIAL - Sionna 가 아니… | NO |
| X07 | CAVIAR: Co-simulation of 6G Communications, 3D Scenarios … | arXiv preprint<br>*⚠ PREPRINT - PDF 첫 줄이 'This work …* | ⭐ Sionna 씬 안의 드론에 재질이 배정된다 - Table V: 'Radio material (… | 없음. 드론은 표적이 아니라 Sionna 의 수신기(Rx)로 인스턴스화된다. | 통신 링크(빔 선택). 센싱… | 빔 선택 정확도/검색-구조 임무 성능. 산란 진폭 검증 없음(RCS 0회). | NO | PARTIAL - 드론 메시에 ITU meta… | YES | NO |
| X08 | OpenISAC: An Open-Source Real-Time Experimentation Platfo… | arXiv preprint<br>*⚠ PREPRINT. 저자·게재처 미확정(UNVERIFIED…* | 해당 없음(Sionna 씬 없음). | 해당 없음. | 바이스태틱 중심 실증 플랫폼… | 플랫폼 실증. CFAR/Pfa/Pd 는 0회(이전 세션 H9 확인, 이번 세션 term-count … | NO | NO | NO - Sionna 미사용 | NO |

#### X01 — Micro-Doppler Signature Simulation of Multirotor UAVs Using Ray Tracing

- **서지** — Changjun Li / Shiyi Mu / Jun Jiang / Lei Feng / Yuan Gao / Shugong Xu. *2025 IEEE 25th International Conference on Communication Technology (ICCT)*, 2025.
- **상태** — PUBLISHED - 근거 2겹: (a) PDF p1 에 'DOI: 10.1109/ICCT67417.2025.11374154' 와 ISBN 979-8-3315-8578-5/25/$31.00 (c)2025 IEEE, (b) OpenAlex 독립조회에서 동일 DOI 반환
- **인용키** — `li_mdrt_icct25`
- **PDF** — `/data/public/sionna_jeong/papers_isac_sionna/paper_sionna_Ray_0723/Micro-Doppler_Signature_Simulation_of_Multirotor_UAVs_Using_Ray_Tracing.pdf`
- **Sionna** — {"used": true, "component": "Sionna RT", "version_stated": null, "version_note": "버전 미기재. 인용문 [16] 은 Sionna RT GLOBECOM Wkshps 2023 논문."}
- **판정** — H8 미반증. 다만 '게재된 Sionna + 드론형상' 조합으로는 가장 가까운 논문.
- 주장: 산란중심 1->2->3->6->블레이드모델로 늘리면 시간-주파수 도면이 최대 도플러 정현 포락선 안을 점점 채운다(Fig.4a-e).
- 주장: 거리분해능이 표적 물리크기보다 작아지는 HRR 영역에서는 표적이 단일 거리셀 점산란체가 아니라 거리축으로 퍼진 확장응답이 된다.
- 주장: 반송주파수를 올리면 마이크로도플러 스펙트럼이 넓어지고 에너지가 분산된다(초록·Fig.6, 2.4/5/6/24/60/77 GHz).
- 주장: ⚠ dBsm 0회, RCS 절대값 0회. 진폭에 대한 주장은 한 줄도 없다.
- ⚠ ⚠ 논문 안에서 숫자가 10배 어긋난다. Table I(p3) 'Propeller radius 10.55cm' vs 본문(p4, 인쇄 362쪽) 'Under the conditions of a blade length of 1.055 meters'. 이번 세션에 두 문장 모두 직접 확인했다. 우리가 어느 쪽이든 인용하면 다른 쪽도 같이 적을 것.
- ⚠ ⚠ 기체가 없다. '드론을 Sionna 에 넣었다'로 요약하면 과장이다. 정확히는 '로터 1개'다. ⚠ 저자군은 Great-X(X06)와 같은 연구실이다 - 두 편을 독립 증거처럼 나란히 세우지 말 것.
- **우리에게** — ⭐ 우리 report07/08 의 직접 선행. (1) 'ray tracing 으로 멀티로터 회전 스펙트럼을 체계적으로 다룬 연구가 아직 없다'는 저자들 자신의 gap 문장이 우리 서론의 외부 근거가 된다. (2) 그들이 검증한 것은 리지 '위치'뿐이고 진폭은 손도 안 댔다 - 우리가 σ(dBsm)를 앵커링한다는 주장의 대비축이 정확히 여기다. (3) 기하는 모노스태틱 1종뿐 - 우리 2x3 격자(모노/바이 x WiFi/LTE/5G)의 필요성을 그대로 뒷받침한다. (4) 재질 'Wood' 단일 - 우리 재질가중 PO(prop/body/battery/PCB)와 대비.
  > “To date, no research has systematically employed ray tracing to model and analyze signal spectrum variations caused by rotational motions of multirotor UAVs.” — *p.1*
  > “We propose an improved directional ray-tracing strategy based on Sionna RT, which replaces spherical sampling with conical sampling to enhance path density and distribution accuracy in critical regions.” — *p.1*
  > “The target consists of either Sionna's built-in reflector model or a physical model of a propeller modeled using Blender. The model's coordinates are located at its geometric center, and electromagnetic parameters such as conductivity are based on Sionna's built-in settings.” — *p.3*
- **초안 문장** — 레이트레이싱으로 멀티로터의 회전 마이크로도플러를 다룬 유일한 게재 논문은 Sionna RT 의 광선 샘플링을 구면에서 원뿔로 바꾼 Li 외[ICCT'25]이지만, 표적은 목재 프로펠러 1개이고 검증은 최대 도플러 1562 Hz 와 회전주기 0.04 s 라는 운동학적 일치에 그친다 - 산란 진폭은 논문 전체에 한 번도 등장하지 않는다.
- **인용 초안** — C. Li, S. Mu, J. Jiang, L. Feng, Y. Gao, and S. Xu, "Micro-Doppler signature simulation of multirotor UAVs using ray tracing," in Proc. IEEE 25th Int. Conf. Commun. Technol. (ICCT), 2025, pp. 359-364, doi: 10.1109/ICCT67417.2025.11374154.

#### X02 — Clutter-Aware Integrated Sensing and Communication: Models, Methods, and Future Directions

- **서지** — Rang Liu / Peishi Li / Ming Li / A. Lee Swindlehurst. *Proceedings of the IEEE*, 2026.
- **상태** — PUBLISHED - PDF 러닝풋 'PROCEEDINGS OF THE IEEE \| Vol. 114, No. 1, January 2026' 및 'Digital Object Identifier 10.1109/JPROC.2026.3675476' 직접 확인
- **인용키** — `clutteraware_procieee26`
- **PDF** — `/data/public/sionna_jeong/papers_isac_sionna/paper_sionna_Ray_0723/Clutter-Aware_Integrated_Sensing_and_Communication_Models_Methods_and_Future_Directions.pdf`
- **Sionna** — {"used": true, "component": "Sionna RT (스톡)", "version_stated": null, "version_note": "버전 미기재. 참고문헌 [72] 는 Sionna RT technical report arXiv:2504.21719."}
- **판정** — H8 미반증. ⭐ 그러나 P1+P2+P3 를 동시에 만족하는 유일한 논문이므로, H8 을 지탱하는 무게 전부가 P4 한 프롱에 실린다. 우리 문장은 반드시 '검증된(validated)' 을 명시해야 한다.
- 주장: UAV 는 '표적'이 아니라 약한 ToI 를 가리는 '강한 이동 클러터'로 배치된다. UAV-1 은 방위각이 ToI 에 가깝고 도플러가 분리, UAV-2 는 방위각 분리·도플러 중첩.
- 주장: 표적/클러터 진폭은 복소계수로 추상화된다: 'the frequency-dependent complex coefficients {alpha, beta} capture the combined effects of RCS, path loss, and multipath-induced phase variations'.
- 주장: Sionna RT 씬의 SCNR 은 확률모형 예제보다 훨씬 낮아 검출이 더 어렵다고 서술(정성).
- ⚠ ⚠ UAV 는 표적이 아니라 방해물이다. '드론 검출 논문'으로 인용하면 오인용. ⚠ 게재판 Table/그림 쪽수와 arXiv v2 쪽수가 다르다.
- **우리에게** — ⭐⭐ 우리 novelty 문장의 가장 위험한 이웃이자 최고의 지렛대. (1) '드론 메시를 Sionna 에 넣은 게 처음' 이라고 쓰면 즉시 반증된다 - Proc. IEEE 가 이미 했다. (2) 그러나 그들은 씬을 'lightweight' 하게 유지하려고 메시를 단순화했고 표적 RCS 를 한 번도 말하지 않는다. 우리 주장은 '메시를 넣었다'가 아니라 '넣은 표적의 산란 진폭을 계산하고 검증했다'여야 한다. (3) 그들의 hot clutter(외부 방사원) 취급은 우리 패시브 서사의 거울상 - 그들에게 간섭인 것이 우리에게는 조명원이다. 이 대비 한 문장이 우리 report09/12 의 좋은 프레임이 된다.
  > “The ToI and UAVs are modeled as simplified 3-D mesh objects imported into Sionna. These meshes are obtained by simplifying publicly available 3-D models in Blender and exporting them in Sionna's XML format, which keeps the ray-tracing scene lightweight while enabling flexible material assignment.” — *p.23*
  > “The scenario includes a monostatic ISAC BS, a weak ToI, two stronger mobile UAV targets, and an external emitter. The BS is deployed at a height of 13.5 m, the targets are placed at heights between 10 and 15 m, and the emitter is at 5 m.” — *p.23*
  > “The maximum interaction depth for Sionna is set to three, so each ray undergoes at most three interactions with scene objects.” — *p.23*
- **초안 문장** — 단순화한 UAV 표면메시를 Sionna RT 씬에 실제로 올린 게재 논문은 Liu 외[Proc. IEEE'26]가 있으나, 그 메시는 '씬을 가볍게 유지하기 위해' 단순화된 것이고 표적의 RCS 값은 제시되지도 검증되지도 않는다 - 논문 41쪽 전체에 dBsm 은 한 번도 나오지 않는다.
- **인용 초안** — R. Liu, P. Li, M. Li, and A. L. Swindlehurst, "Clutter-aware integrated sensing and communication: Models, methods, and future directions," Proc. IEEE, vol. 114, no. 1, pp. 52-92, Jan. 2026, doi: 10.1109/JPROC.2026.3675476.

#### X03 — AI-Empowered Low-Altitude Economy: Cooperative Sensing With Fixed Wireless Access

- **서지** — Jinya Zhang / Jiajia Guo / Xiangyi Li / Chao-Kai Wen / Shi Jin. *arXiv preprint*, 2026.
- **상태** — ⚠ PREPRINT. ⭐ 종전 기록 정정: 아카이브가 이 파일을 published_by_venue/IEEE_ICC_Workshops_2026/ 아래 복사해 두었고 outputs/prior_settled_h8.json 은 P1 을 'likely YES' 로 적었으나, PDF p1 각주는 'This work has been partly accepted by IEEE ICC Workshops 2026 [1]' 이고 [1] 은 제목이 다른 별개 논문(J. Zhang, J. Guo, X. Li, C.-K. Wen, S. Jin, 'Deep learning-based cooperative UAV detection with CPE-assisted sensing,' Proc. IEEE ICC Workshops, 2026)이다. 즉 이 13쪽 원고 자체는 미게재이고, 게재된 것은 부분·별제목 논문이다. 이 원고를 ICC Wkshps 게재물로 인용하면 E4.
- **인용키** — `fwa_cube_arxiv26`
- **PDF** — `/data/public/sionna_jeong/papers_isac_sionna/2605.07623__lowalt-cooperative-cube-csi.pdf`
- **Sionna** — {"used": true, "component": "Sionna RT (PathSolver)", "version_stated": null, "version_note": "버전 미기재"}
- **판정** — H8 미반증. 다만 '드론을 Sionna 안에 넣고 정량적 검출 성능을 낸' 가장 완성도 높은 사례.
- 주장: 표적 시그니처 자체를 주장하지 않는다. 검출은 '표적이 만드는 CSI 교란'을 신경망이 학습하는 방식이며, 에코 SNR 이나 RCS 는 등장하지 않는다.
- 주장: UAV 로 인한 경로는 대개 diffuse reflection 으로 나타난다고 가정하고 그것을 pair label 로 쓴다.
- ⚠ ⚠ 게재상태 오인용 위험 최고. 아카이브 폴더 위치를 믿지 말 것. ⚠ 'MDP 0.63%' 는 정육면체 표적·학습기반 수치라서 우리 Pd/Pfa 와 직접 비교 불가.
- **우리에게** — ⭐ 우리 검출편(report12)의 최적 대조군. 같은 질문(드론이 있나 없나)을 같은 도구(Sionna)로 풀되, 표적을 정육면체로 놓고 검출을 학습에 맡긴다. 우리는 표적을 메시로 놓고 검출을 CFAR+경험적 Pfa 로 교정한다. 두 축(표적 충실도 / 검출 규약의 통제가능성)에서 정확히 반대편이라 표 한 줄로 대비된다. 또 하나: 그들의 기하는 '자기 네트워크가 조명원인 바이스태틱'이라 우리 A/B/C 3분류에 네 번째 칸이 필요함을 드러낸다.
  > “The dataset is generated through ray-tracing, using OpenStreetMap (OSM), Blender, and Sionna RT [39].” — *p.8*
  > “The UAV is modeled as a metallic cube located at p = (x, y, 60), where x, y ~ U[-75, 75].” — *p.8*
  > “The UAV hovers at p = (x, y, z) and acts as a scatterer whose presence affects the wireless propagation.” — *p.2*
- **초안 문장** — Sionna RT 로 만든 데이터셋 위에서 UAV 검출률을 정량화한 사례로 Zhang 외[arXiv'26]가 있는데, 그 UAV 는 고도 60 m 에 놓인 금속 정육면체이고 검출 근거는 에코가 아니라 CSI 교란의 학습이다.
- **인용 초안** — J. Zhang, J. Guo, X. Li, C.-K. Wen, and S. Jin, "AI-empowered low-altitude economy: Cooperative sensing with fixed wireless access," arXiv:2605.07623v1, May 2026. (부분 게재판: Proc. IEEE ICC Workshops, 2026, 제목 상이)

#### X04 — DMSNet: Cross-Band Learning for Multi-Target Sensing in Multi-Band ISAC

- **서지** — Haotian Liu / Zhiqing Wei / Quanjiang Zhao / Lin Wang / Yunxin Geng / Xingwang Li / Zhiyong Feng. *arXiv preprint*, 2026.
- **상태** — ⚠ PREPRINT (arXiv 스탬프 'arXiv:2607.17655v1 [eess.SP] 20 Jul 2026' 직접 확인). 게재처 문자열 없음.
- **인용키** — `dmsnet_arxiv26`
- **PDF** — `/data/public/sionna_jeong/papers_isac_sionna/2607.17655__dmsnet-crossband-multiband-isac.pdf`
- **Sionna** — {"used": true, "component": "Sionna RT", "version_stated": null, "version_note": "버전 미기재"}
- **판정** — H8 미반증. ⭐ 그러나 우리 벤치마크와 '문항'이 가장 겹치는 논문: Sionna 트윈 + UAV + CFAR 대조군 + 다중대역.
- 주장: 'a target weakly visible in one band may still be detectable in another band, which provides a key motivation for multi-band target detection' - 주파수 선택적 RCS 를 검출 논거로 쓰지만 값을 제시하지 않는다.
- 주장: 고/저 대역이 분해능·전파·표적 산란응답에서 상보적이라는 정성 주장.
- ⚠ ⚠ 프리프린트. ⚠ '표적 표현 미기재' 를 '메시를 안 썼다'로 단정하지 말 것 - 우리가 아는 것은 '적혀 있지 않다'뿐이다. 인용할 때 그대로 그렇게 쓸 것.
- **우리에게** — ⭐⭐ 우리 다중대역 서사(WiFi/LTE/5G 를 나란히 놓는 2x3 격자)의 가장 가까운 이웃. 그들은 3.5 vs 28 GHz 를 상보적이라 주장하면서 정작 표적의 주파수 의존 산란을 '가정'만 하고 계산하지 않는다 - 우리가 대역별 sigma 를 실제로 계산해 넣는 이유를 이 한 문장으로 세울 수 있다. 또 CA-CFAR 을 baseline 으로 쓰되 Pfa 교정 얘기가 없다(우리 report10 의 대비축).
  > “As shown in Fig. 2, a dual-band UAV sensing dataset is generated in a 1:1 3D digital twin of the Beijing University of Posts and Telecommunications (BUPT) campus using Sionna RT [13].” — *p.3*
  > “Each scene contains L in {0, ..., 5} UAVs with r in [50, 300] m, v in [-30, 30] m/s, and theta in [-pi/3, pi/3].” — *p.4*
  > “rho_{b,l} is the frequency-selective complex scattering coefficient, and the corresponding radar cross section (RCS) is denoted by xi_{b,l} = \|rho_{b,l}\|^2 [9]. This indicates that a target weakly visible in one band may still be detectable in another band, which provides a key motivation for multi-band target detection [9]” — *p.2*
- **초안 문장** — Sionna RT 로 만든 캠퍼스 디지털트윈에서 다중대역 UAV 센싱을 학습으로 푸는 Liu 외[arXiv'26]는 고·저 대역의 표적 산란응답이 상보적이라는 전제 위에 서 있지만, UAV 가 광선추적 씬에서 어떤 형상으로 표현되었는지는 논문에 기술되어 있지 않다.
- **인용 초안** — H. Liu, Z. Wei, Q. Zhao, L. Wang, Y. Geng, X. Li, and Z. Feng, "DMSNet: Cross-band learning for multi-target sensing in multi-band ISAC," arXiv:2607.17655v1, Jul. 2026.

#### X05 — LAMBDA: A Low-Altitude Multimodal Base Dataset for UAV Sensing and Communication

- **서지** — Lin Zhou / Peichuan Rao / Chenshuo Zhang / Jianhua Mo / Shu Sun / Zhiyong Chen / Meixia Tao. *arXiv preprint*, 2026.
- **상태** — ⚠ PREPRINT (arXiv 스탬프 직접 확인). 데이터 논문 형식(Competing Interests / Author contributions 절 존재)이나 게재처 표기 없음.
- **인용키** — `lambda_dataset_arxiv26`
- **PDF** — `/data/public/sionna_jeong/papers_isac_sionna/2607.03826__lambda-uav-dataset.pdf`
- **Sionna** — {"used": true, "component": "Sionna RT (경로/CSI)", "version_stated": null, "version_note": "버전 미기재"}
- **판정** — H8 미반증. 커뮤니티가 실제로 쓰는 '주입 아키텍처'의 가장 깨끗한 표본.
- 주장: UAV 자세에 따라 RCS 가 달라진다는 것을 데이터 생성에 반영했다는 주장(값·검증은 없음).
- 주장: 'The complex-valued CSI coefficient captures the propagation effects computed by the ray-tracing channel generator, whereas the RCS term is obtained from CADFEKO simulations of the AirSim UAV model and queried according to the UAV attitude.'
- ⚠ ⚠ 프리프린트. ⚠ '2.04 TB / 517,939 프레임' 같은 규모 수치는 데이터셋 규모지 정확도 근거가 아니다.
- **우리에게** — ⭐ 우리 report06/07 의 '왜 엔진 안에서 계산해야 하나' 를 정당화하는 반례. 주입 방식은 (i) 표적-환경 결합(다중반사·바닥유령)을 원천적으로 못 만들고 (ii) 정적 RCS 테이블이라 관측각·바이스태틱각 조합이 씬 기하와 어긋날 수 있다. 우리 바닥유령 결과(report09)가 왜 주입식으로는 안 나오는지 설명할 때 이 논문을 지목하면 된다.
  > “Blender [26] for scene-mesh conversion; Sionna RT [27] for material-aware ray tracing; and CADFEKO [28] for UAV radar cross-section (RCS) modeling.” — *p.3*
  > “The radar synthesis module further combines the Sionna RT multipath geometry with CADFEKO-derived UAV RCS information to generate radar data.” — *p.4*
  > “The complex-valued CSI coefficient captures the propagation effects computed by the ray-tracing channel generator, whereas the RCS term is obtained from CADFEKO simulations of the AirSim UAV model and queried according to the UAV attitude.” — *p.7*
- **초안 문장** — 저고도 ISAC 데이터셋의 표준 아키텍처는 산란과 전파를 분리하는 것이다 - LAMBDA[arXiv'26]는 Sionna RT 로 다중경로 기하를 만들고 UAV RCS 는 CADFEKO 에서 따로 계산해 자세로 조회하여 곱한다.
- **인용 초안** — L. Zhou, P. Rao, C. Zhang, J. Mo, S. Sun, Z. Chen, and M. Tao, "LAMBDA: A low-altitude multimodal base dataset for UAV sensing and communication," arXiv:2607.03826v1, Jul. 2026.

#### X06 — Unreal is all you need: Multimodal ISAC Data Simulation with Only One Engine (Great-X / Great-MSD)

- **서지** — Kongwu Huang / Shiyi Mu / Jun Jiang / Yuan Gao / Shugong Xu. *arXiv preprint*, 2025.
- **상태** — ⚠ PREPRINT (arXiv 스탬프 'arXiv:2507.08716v3 [cs.CV] 26 Jul 2025').
- **인용키** — `greatx_arxiv25`
- **PDF** — `/data/public/sionna_jeong/papers_isac_sionna/2507.08716__great-x_unreal-isac.pdf`
- **Sionna** — {"used": "부분 - Sionna 의 RT 수식을 Unreal Engine 안에 재구현하고, Sionna RT 는 교차검증 baseline 으로 사용", "component": "Sionna RT (수식 출처 + 비교대상)", "version_stated": null, "version_note": "버전 미기재"}
- **판정** — H8 미반증.
- 주장: RCS 0회, dBsm 0회. 표적 산란 진폭에 대한 주장 없음.
- ⚠ ⚠ X01(md-rt)과 동일 연구실. ⚠ 프리프린트. ⚠ 'Sionna 보다 정밀' 주장은 렌더러 기하/텍스처에 대한 것이지 EM 정확도 비교가 아니다.
- **우리에게** — ⭐ '엔진을 바꾸면 결과가 얼마나 달라지나' 에 대한 유일한 정량 자료(8.1 m vs 11.1 m 교차 일반화 오차). 우리 SBR 구현이 Sionna 스톡과 다른 답을 낼 때, '엔진 차이는 이 정도 규모' 라는 외부 눈금으로 쓸 수 있다. 단 그 수치는 측위 오차이지 산란 진폭 오차가 아니다.
  > “This single-engine multimodal data twin platform reconstructs the ray-tracing computation of Sionna within Unreal Engine” — *p.1*
  > “The following formulas are referenced from SionnaRT [13].” — *p.2*
  > “To assess the effectiveness of the simulation platform, we conducted a bidirectional cross-platform evaluation between Great-X and SionnaRT. Both platforms used identical map configurations and consistent parameters.” — *p.4*
- **초안 문장** — Sionna RT 의 전파 수식을 Unreal Engine 으로 옮겨 UAV 다중모달 ISAC 데이터를 만드는 Great-X[arXiv'25]는 두 엔진 간 교차 일반화 측위오차를 8.1~11.1 m 로 보고하지만, 표적의 산란 진폭은 다루지 않는다.
- **인용 초안** — K. Huang, S. Mu, J. Jiang, Y. Gao, and S. Xu, "Unreal is all you need: Multimodal ISAC data simulation with only one engine," arXiv:2507.08716v3, Jul. 2025.

#### X07 — CAVIAR: Co-simulation of 6G Communications, 3D Scenarios and AI for Digital Twins

- **서지** — Joao Borges / Felipe Bastos / Ilan Correa / Pedro Batista / Aldebaro Klautau. *arXiv preprint*, 2024.
- **상태** — ⚠ PREPRINT - PDF 첫 줄이 'This work has been submitted to the IEEE for possible publication.'
- **인용키** — `caviar_arxiv24`
- **PDF** — `/data/public/sionna_jeong/papers_isac_sionna/2401.03310__caviar-digital-twin.pdf`
- **Sionna** — {"used": true, "component": "Sionna (link/PHY + RT)", "version_stated": null, "version_note": "버전 미기재"}
- **판정** — H8 미반증.
- 주장: 없음.
- ⚠ ⚠ 드론 검출 논문 아님. ⚠ 프리프린트.
- **우리에게** — 드론 메시 + 재질을 Sionna 씬에 넣는 관행이 2024년부터 있었다는 근거. 단 '표적으로서'가 아니라 '단말로서'다. 우리 report02(드론 3D)에서 '메시를 넣는 것 자체는 새롭지 않다' 를 정직하게 인정할 때 인용.
  > “Sionna scene parameters ... Carrier frequency 40 GHz / Radio material (building and ground) ITU concrete / Radio material (drone) ITU metal / Synthetic array True” — *p.Table V*
  > “Each UAV is instantiated as a smart vehicle in AirSim, the 3D module, and as a receiver in Sionna, the Communications module.” — *p.Sec.V*
  > “The version used in Sionna does not use textures and underwent a slight simplification using the decimation modifier in Blender.” — *p.Sec.V*
- **초안 문장** — 드론 메시에 전자기 재질을 배정해 Sionna 씬에 올리는 것 자체는 CAVIAR[arXiv'24]에서 이미 이루어졌으나(ITU metal, 40 GHz), 거기서 드론은 산란 표적이 아니라 수신 단말이다.
- **인용 초안** — J. Borges, F. Bastos, I. Correa, P. Batista, and A. Klautau, "CAVIAR: Co-simulation of 6G communications, 3D scenarios and AI for digital twins," arXiv:2401.03310v1, Jan. 2024.

#### X08 — OpenISAC: An Open-Source Real-Time Experimentation Platform for OFDM-ISAC

- **서지** — (OpenISAC authors - PDF 저자행 미확정). *arXiv preprint*, 2026.
- **상태** — ⚠ PREPRINT. 저자·게재처 미확정(UNVERIFIED) - 이 세션에서 저자행을 확정하지 않았다.
- **인용키** — `openisac_arxiv26`
- **PDF** — `/data/public/sionna_jeong/papers_isac_sionna/2601.03535__openisac.pdf`
- **Sionna** — {"used": false, "component": "인용만 - 'NVIDIA Sionna and the Sionna Research Kit are also important open-source tools'; 참고문헌에 version 2.0.1 명시", "version_stated": "2.0.1 (참고문헌 문자열)", "version_note": "⭐ 아카이브 전체에서 Sionna 2.0.1 을 명시적으로 적은 몇 안 되는 문서"}
- **판정** — H8 미반증. 교집합 아님(인용만).
- 주장: 레이더 방정식 안의 추상 sigma_RCS.
- ⚠ ⚠ Sionna 를 '쓰지' 않는다. 기계 계수만 보고 교집합에 넣으면 오분류.
- **우리에게** — 우리 그룹미팅 덱의 주제이기도 함. 교집합 목록에는 '인용만' 사례로 남겨 둔다 - 자동 계수(sionna>=1)가 교집합으로 오분류하기 쉬운 대표 함정.
  > “For a specific reflection p with radar cross section (RCS) sigma_{RCS,p}, range d_{s,p}, and radial velocity v_{s,p}, the complex scattering coefficient, round-trip delay, and two-way Doppler shift are modeled as” — *p.4*
- **인용 초안** — OpenISAC, arXiv:2601.03535v2, Jul. 2026. (저자·게재처 UNVERIFIED)

### 4.1 경계 · 방법 선례 (교집합은 아니나 방법이 가장 가깝다)

| # | 논문 | 게재처 | 왜 여기 있나 | 인용키 |
|---|---|---|---|---|
| B01 | Ray-Based Simulation of Multistatic Scattering from Target Ob… | EuCAP 2025 (⚠ 2차정보: outputs/reflib_swee… | 방법상 최근접 - 메시 산란을 Sionna 내부에서 계산하고 진폭까지 검증. 표적만 드론이 아님(차량). | `ziganshin_multistatic_eucap25` |
| B02 | Ray-Based Simulation of Scattering from Discretized Curved Bo… | arXiv preprint | 같은 저자군의 저널판. Sionna-RT v0.19 를 in-place 확장하고 BIRA 바이스태틱 측정과 대조. | `ziganshin_curved_arxiv26` |
| B03 | RF Genesis: Zero-Shot Generalization of mmWave Sensing throug… | ACM SenSys 2023 | ⭐ 사용자가 지목한 최상위 학회(SenSys)에서, 사람 메시를 광선추적기에 넣어 mmWave 레이더 원신호를 합성한 선례. 드론도 Sionna 도 아니지만 '메시->레이더 에코' 파이프라인의 최상위 게재 기준선. | `rfgenesis_sensys23` |
| B04 | RadarTwin: Scene-Specific mmWave Radar Simulation and Learnin… | arXiv preprint | 메시 -> Mitsuba 3 (Sionna RT 와 같은 렌더러) -> FMCW 원신호 -> 실측과 짝지어 검증. 표적이 실내 물체라 P2 실패. | `radartwin_arxiv26` |
| B05 | Drone Detectability Feasibility Study using Passive Radars Op… | NATO STO-MP-MSG-SET-183, paper 13 | H8-Q1 의 반례 - 드론 바이스태틱 RCS + 패시브 레이더 예산 + OTA 검출을 이미 다 한 논문. 엔진만 FDTD. | `rzewuski_nato21` |

### 4.2 사용자가 지목한 최상위 학회에서의 교집합

| 학회 | Sionna × 드론 센싱 편수 |
|---|---|
| **ICASSP** | 0 |
| **INFOCOM** | 0 |
| **MobiCom** | 0 |
| **SenSys** | 0 (드론+Sionna 교집합 기준). SenSys 에는 LaSen(드론, Sionna 없음)과 RF Genesis/HiSAC(Sionna 없음)가 있다. |
| **MobiSys** | 0 |

> ⭐ 사용자가 지목한 5개 최상위 학회 중 'Sionna 로 드론을 센싱한' 논문은 0편이다. 교집합은 전부 IEEE 계열(ICCT, Proc. IEEE)과 arXiv 에 있다. 이는 우리가 노릴 자리가 비어 있다는 뜻이기도 하고, 그 학회들이 시뮬레이션 단독 논문을 잘 안 받는다는 뜻이기도 하다 - 실측(X410) 없이 SenSys/MobiSys 를 노리는 것은 위험하다.

> **우리가 채우는 빈 칸.** Sionna 를 쓰면서 (i) 드론 메쉬에 산란적분을 돌리고 (ii) 지오메트리를 mono/bi 두 축으로 명시하고 (iii) 조명원 3종을 교차하고 (iv) CFAR 를 경험적 Pfa 로 교정한 논문은 이 스윕에서 하나도 나오지 않았다. 네 조건 중 최대 두 개까지만 겹친다.

## 5. 규약 원장 — 숫자를 나란히 놓기 전에

> ⭐ 숫자를 나란히 놓기 전에 이 표를 먼저 본다. 2배 오차가 그대로 결론을 바꾼다.

- 무모호 속도: LaSen 은 반폭(우리와 같음). Geng 과 Jopanya 는 전폭(계수 2배).
- 슬로타임 축: 우리와 LaSen 은 기준신호 반복 주기. Jopanya 는 OFDM 심볼 간격. Geng 은 파형별로 다르다.
- 거리분해능: 우리 ΔR_b = c/B 는 바이스태틱 거리합 축. HiSAC 은 이등분선 투영이라 cos 항이 붙는다.
- RCS 평균: Das 는 방위 선형평균(III-1 절), Yuan 은 정의 미상, Azim/3GPP 는 로그정규 기댓값의 dB 변환.
- Pfa: 대부분 설계값(nominal). CellSense 는 '검출 중 오검출 비율'. He 만 달성치를 별도 열로 준다.

### 5.1 무모호 속도 규약 — 누가 어느 규약을 쓰나

- **우리 규약** — half-window: v_max = lambda*PRF/4
- **전폭(full-width) 사용** — `geng2020 (MUV 176.5 m/s at PRI 1 ms, fc 850 MHz)`, `wei2022prs`, `jopanya2025spawc (as written)`
- **반폭(half-window) 사용** — `lasen2026 (2.6 m/s at 200 Hz, 5.8 GHz)`, `chen2024appliedsci ([-25,25] Hz from a 20 ms period)`
- **Nyquist 형태** — `wei2025twc (PRF >= 2*f_max)`
- **규약 미확인** — `wypich2026sensors (392 m/s - convention not read)`

> ⭐ 나란히 적을 때 규약을 반드시 열로 표시한다. 2배 오차가 그대로 결론을 바꾼다.

### 5.2 우리 법칙이 재현하는 세 편의 독립 논문

> ⭐ 우리 v_max = lambda*PRF_ref/4 를 세 편의 서로 다른 논문(다른 대역·다른 기준신호·다른 규약)이 적은 숫자에 대입한 결과. 전부 규약만 맞추면 재현된다.

| 논문이 적은 값 | fc | PRF | 규약 | 우리 식이 준 값 | 상대오차 |
|---|---|---|---|---|---|
| 2.6 | 5800000000.0 Hz | 200.0 Hz | half-window | 2.58441774137931 | 0.005993 |
| 176.5 | 850000000.0 Hz | 1000.0 Hz | full-width | 176.34850470588233 | 0.0008583 |
| chen2024appliedsci (Applied Sciences, passive bistatic, CSI-RS 20 ms, r=0.3 m) | 3550000000.0 Hz | 50.0 Hz | half-window, expressed in rps | 0.5600170374691247 | 3.042e-05 |

**정합성 보너스** — Wei(TWC 2025)는 반송파를 그 문단에 적지 않는다. f_mD = 2*pi*f_r*L/lambda 와 그들이 적은 f_mD=2934 Hz, f_r=80 r/s, L=0.5 m 로 lambda 를 역산하면 λ = 0.0856603 m → fc = 3.49978 GHz. 3.4998 GHz - 즉 정확히 3.5 GHz 대역이다. 그들의 숫자는 내부 정합적이고, 우리 5G 레인과 같은 반송파다.

### 5.3 ⚠ 우리 헤드라인을 위협하는 것들 (심각도 순)

| # | 논문 | 무엇 | 우리에게 미치는 영향 |
|---|---|---|---|
| 1 | `wei2025twc` | IEEE TWC 24(12), Dec 2025, PUBLISHED - 'PRF >= 2*f_mD_max' 를 드론 ISAC 맥락에 명시하고 숫자까지 넣는다(f_mD=2934 Hz -> PRF>=5868 Hz). | 우리 법칙의 마이크로도플러 판은 선행이 있고, LaSen(2026)보다 앞선다. '아무도 안 했다'는 문장은 불가능. |
| 2 | `chen2024appliedsci` | ⚠ **정정(R1)** — Applied Sciences 2024 는 **닫힌 식을 인쇄하지 않는다**(원문 20쪽 재계수: `PRF` **0회**). LaSen 이 우선권을 이 논문에 돌리지만 그건 LaSen 의 요약이다. **진짜 우선권은 Abratkiewicz 외 IEEE JSTARS 16:3469-3484 (2023) 식 (16) p.3476** — 반구간 규약까지 동일. | 식 자체의 우선권은 우리 것이 아니다(그러나 Chen 도 아니다). novelty 는 교차표·설계역산·검출률 귀결로 재정의해야 한다. |
| 3 | `wypich2026sensors` | Sensors 2026, PUBLISHED - **패시브** 수신기가 SSB+PDCCH+PDSCH+CSI-RS 를 전부 복원해 쓴다. 표에 최대 속도 392 m/s. | ⭐⭐ '패시브라서 기준신호만 쓴다'는 전제가 깨진다. 헤드라인의 조건절을 '상시 기준신호만 쓰는 운용에서'로 명시하지 않으면 반증당한다. 경계는 지오메트리가 아니라 파형 접근도다. |
| 4 | `jopanya2025spawc` | SPAWC 2025 - SSB 패시브 바이스태틱에서 \|v_u\| <= lambda*f_Delta/2 를 이미 적는다. | 다만 그 슬로타임은 버스트 **안쪽** 심볼 간격이지 SSB **반복 주기**가 아니다. 이 축 구별이 우리 novelty 의 전부이며 리뷰어가 가장 먼저 찌를 지점. |
| 5 | `viberg2026icassp` | ICASSP 2026 - 도플러 축을 소거하고 지연만 1D 탐색하는 패시브 추정기. | 우리 법칙은 '균일 슬로타임 푸리에 처리' 전제 위에서만 성능을 정한다. 그 전제를 본문에 명시해야 한다. |
| 6 | `diseglio2024ietrsn` | IET RSN 2024 - 'Doppler ambiguity' 라는 표현을 쓰지만 메커니즘이 반복률 접힘이 아니라 위상동기 실패다. | 동명이인 함정. 우리 표에 그대로 옮기면 E3(주장을 논문에 잘못 귀속). |
| 7 | `ji2026dualbistatic` | '도플러 정확도는 적분만 늘리면 쉽다'는 통념 문장이 그대로 적혀 있다. | 우리에게 **유리**한 반례. 정확도와 모호 상한의 혼동이 문헌에 실재함을 그대로 인용할 수 있다. |
| 8 | `abratkiewicz2023jstars` | 미확보 JSTARS 2023 논문이 SSB 도플러 모호를 이미 다뤘다는 **2건의 제3자 요약**이 있다. | ⭐ 확보 전까지 우리 novelty 문장을 확정할 수 없다. 최우선 조치. |

## 6. ⭐ 관련연구 골격

문단 7개 · 논문 슬롯 84개. 각 문단은 논지 한 줄 + 그 문단에 들어갈 논문들 + 논문마다 그대로 붙여넣을 수 있는 한 문장 + 가드로 이루어진다.

### RW1. 통신 조명원 기반 패시브 레이더 — 조명원 축이 먼저다

**논지** — 패시브 드론 레이더는 WiFi → LTE → 5G NR 순으로 조명원을 갈아타 왔고, 갈아탈 때마다 성능을 정한 것은 대역폭이 아니라 다운링크에 무엇이 얼마나 자주 실리는가였다. 우리 격자의 조명원 축은 이 계보를 그대로 잇는다.

| 인용키 | 게재처 · 연 | 등급 | 그대로 쓸 수 있는 한 문장 |
|---|---|---|---|
| `martelli_wifi_radar17` | Proc. IET Int. Conf. Radar Systems (R… 2017 | P | 수신기를 조명원 바로 옆에 두는 준-모노스태틱 패시브 배치는 WiFi 패시브 레이더에서 명시적으로 채택된 바 있으며(Martelli 외, Radar 2017), 그 계열의 오경보율은 설계값(nominal Pfa)으로만 보고되고 실제 달성치는 측정되지 않는다. |
| `rzewuski_nato21` | NATO STO Meeting Proc. STO-MP-MSG-SET… 2021 | P | 패시브 배치에서 표적 RCS 는 모노스태틱 값과 다르며, 소형 플라스틱 드론의 WiFi 대역 RCS 는 -40 ~ 0 dBsm(평균 약 -20 dBsm) 범위로 FDTD 계산과 OTA 검출(바이스태틱 50 m)이 함께 보고되어 있다(Rzewuski 외, NATO STO-MP-MSG-SET-183, 2021). |
| `colone_reffree_taes23` | IEEE Trans. Aerosp. Electron. Syst. 2023 | P | 패시브 센싱 문헌은 기준신호 접근도에 따라 전 파형·기준신호만·기준신호 없음의 세 계단으로 갈리며, 최하단에서는 속도 부호를 잃는다(Colone 외, IEEE TAES 2023). |
| `diseglio_reffree_ietrsn24` | IET Radar Sonar Navig. 2024 | P | 같은 WiFi 시스템으로 준-모노스태틱과 극단 바이스태틱을 나란히 관측하면 처리 방식별 우열이 기하에 따라 뒤바뀐다(Di Seglio 외, IET RSN 2024). |
| `dan_lte_pbr_joe19` | J. Eng. 2019 | P | LTE 다운링크를 조명원으로 쓴 패시브 드론 검출은 Dan 외(J. Eng., IET IRC 2018)에서 이미 실험적으로 보고되었다. |
| `taylor_lte_pbr_taes25` | IEEE Trans. Aerosp. Electron. Syst. 2025 | P | LTE 패시브 실측에서 관측된 드론의 바이스태틱 속도는 13 m/s 안팎에 머물며(Taylor & Poullin, IEEE TAES 2025), 이는 상시 기준신호만으로 얻는 무모호 속도와 직접 비교되는 값이다. |
| `ji_bistatic_wcl26` | IEEE Wireless Commun. Lett. 2026 | P | 두 대의 LTE 기지국과 두 대의 패시브 수신기로 서로 다른 방향의 바이스태틱 도플러를 재면 LTE 의 거리분해능보다 정밀한 UAV 궤적 재구성이 가능하다(Ji 외, IEEE WCL 15:1807-1811, 2026). |
| `sun_uav_tracking_ojcoms25` | IEEE Open J. Commun. Soc. 2025 | P | 상용 LTE 다운링크와 디지털 배열 수신기로 UAV 궤적을 바이스태틱으로 추적한 실측이 보고되어 있다(Sun 외, IEEE OJ-COMS 2025). |
| `demissie_lte450_radar24` | Proc. IEEE Radar Conf. (RadarConf) 2024 | P | 패시브 배치를 모노스태틱에 최대한 가깝게 만들려는 시도는 LTE450 조명원 실험에서 명시적으로 보고되었다(Demissie 외, RADAR 2024). |
| `ai_5g_piers21` | Proc. PhotonIcs and Electromagnetics … 2021 | P | 5G NR 을 조명원으로 한 패시브 UAV 검출 실험은 2021년부터 보고된다(Ai 외, PIERS 2021). |
| `maksymiuk_renyi_rs22` | Remote Sens. 2022 | P | 5G 패시브 레이더의 거리분해능과 검출거리는 망 부하에 따른 자원 할당량에 종속되며, 다운링크에 데이터가 없으면 망은 반복주기 5-160 ms 의 동기 신호만 내보내 심각한 제약을 남긴다(Maksymiuk 외, Remote Sensing 14(23):6146, 2022). |
| `maksymiuk_5g_irs23` | Proc. Int. Radar Symp. (IRS) 2023 | P | 상용 5G gNB(3.44 GHz, 최대 38 MHz)를 조명원으로 한 패시브 드론 검출은 실측으로 확립되어 있으며 바이스태틱 거리분해능은 약 7.8 m 수준이다(Maksymiuk 외, IRS 2023). |
| `abratkiewicz_ssb_jstars23` | IEEE J. Sel. Topics Appl. Earth Obser… 2023 | S | 5G SSB 를 펄스처럼 다루는 패시브 레이더 신호처리는 이미 별도로 보고되어 있다(Abratkiewicz 외, IEEE JSTARS 16:3469-3484, 2023). |
| `needle_haystack_mobisys26` | Proc. 24th Annu. Int. Conf. Mobile Sy… 2026 | B | 실제 운용 중인 5G-Advanced 기지국 데이터에서 UAV 를 골라내는 문제는 2026년 MobiSys 에서 다루어졌으며(Meng 외, pp.14-27), 통제된 시뮬레이션과 실망 데이터 사이의 간극을 그대로 보여준다. |
| `fang_lora_drone_infocomw22` | Proc. IEEE INFOCOM Workshops 2022 | B | 조명원 축은 WiFi·LTE·5G 밖으로도 확장되어 LoRa 를 조명원으로 쓰는 시도까지 보고되었으나(Fang 외, IEEE INFOCOM Workshops 2022), 낮은 반복률 때문에 속도 추정이 성립하지 않는다는 지적이 뒤따른다(Yang 외, SenSys 2026). |

- ⚠ 'passive' 는 이 코퍼스에서 세 뜻으로 쓰인다 — (1) 조명원이 남의 것, (2) 표적이 비협조, (3) 우리가 송신하지 않고 표적 방사를 듣는다. 문단 첫 문장에서 우리가 쓰는 뜻을 못 박을 것.
- ⚠ Sun(WiSec 2022)은 '패시브' 지만 조명원이 자기 USRP 다. Rzewuski 는 DVB-T 와 WiFi 를 함께 쓴다. 조명원 소유권과 기하는 별개 축이다.

### RW2. 드론 RCS 실측 — 절대 수준의 앵커와 그 한계

**논지** — σ 를 붙이려면 실측 앵커가 있어야 하는데, 공개된 드론 RCS 실측은 대부분 15 GHz 이상이고 기하는 거의 모노스태틱이다. 우리 대역(1.8-5.2 GHz)과 바이스태틱 기하를 함께 덮는 문헌은 손에 꼽는다.

| 인용키 | 게재처 · 연 | 등급 | 그대로 쓸 수 있는 한 문장 |
|---|---|---|---|
| `das_multiband_wcl26` | IEEE Wireless Commun. Lett. 2026 | P | 소형 드론의 RCS 를 1.8-27 GHz 와 0-90도 바이스태틱각에 걸쳐 함께 특성화한 실측이 있으며(Das 외, IEEE WCL 15:3731, 2026), 여기서 얻은 주파수 기울기 약 0.21 dB/GHz 가 우리 절대 수준 앵커의 근거다. |
| `zhang_unified_rcs_jsac26` | IEEE J. Sel. Areas Commun. 2026 | P | 3GPP ISAC 채널 표준화를 겨냥한 통합 RCS 모델은 산란을 대규모 전력·각도 의존·무작위 성분으로 분해하며 무향실 모노스태틱 측정으로 검증되었고(Zhang 외, IEEE JSAC 44:702, 2026), 금속구 교정 기준 측정 오차는 2 dB 이내로 보고된다. |
| `semkin_drone_rcs_access20` | IEEE Access 2020 | P | 드론 RCS 는 기체 재질이 지배하며 탄소섬유 기체가 플라스틱 기체보다 평균 약 7 dB, 최대 10-20 dB 높고, 리튬폴리머 배터리는 기체가 비반사성이어도 검출을 가능케 할 만큼 큰 반사체다(Semkin 외, IEEE Access 8:48958, 2020). |
| `azim_inf_rcs_arxiv25` | arXiv 2505.08754 2025 | P | 3GPP RAN1 이 합의한 소형 UAV 의 평균 RCS 는 A = -12.81 dBsm 이며 독립 실측이 이를 1 dB 이내로 재현했고(Azim 외, arXiv:2505.08754), 같은 측정에서 중형 기체가 더 강하게 반사하는 이유로 재질과 리튬이온 배터리 팩이 지목된다. |
| `azim_bistatic_rcs_arxiv24` | arXiv 2411.03206 2024 | P | 드론 RCS 는 거리 불변 확률변수가 아니라 거리와 바이스태틱각에 체계적으로 의존하며, 배터리 배치 같은 내부 구조가 지배 산란중심을 바꾼다는 점이 실측으로 보고되었다(Azim 외, arXiv:2411.03206). |
| `ezuma_rcs_stats_arxiv21` | arXiv 2102.11954 2021 | P | 상용 소형 UAV 여섯 기종의 평균 RCS 는 15 GHz VV 편파에서 -11.7 ~ -17.1 dBsm 범위이며 로그정규·GEV·감마 분포가 가장 잘 맞는다(Ezuma 외, arXiv:2102.11954). |
| `yuan_uav_rcs_eucap25` | Proc. 19th European Conf. Antennas an… 2025 | P | 같은 DJI Phantom 3 를 대상으로 한 두 편의 무향실 측정이 우리 관심 대역에서 3.2-3.6 dB 어긋난 평균 RCS 를 보고하며(Das, IEEE WCL 2026; Yuan, EuCAP 2025), 이 격차를 설명하는 문장은 양쪽 어디에도 없다. |
| `costa_bistatic_md_jsteap25` | IEEE J. Sel. Topics Signal Process. 2025 | P | 다중 프로펠러 드론의 바이스태틱 마이크로도플러는 thin-wire 해석 모델과 실측을 대조해 바이스태틱각 30-180도 구간에서 상관계수 0.98 로 재현된 바 있다(Costa 외, IEEE JSTEAP 2025). |
| `ye_gaf_rcs_taes23` | IEEE Trans. Aerosp. Electron. Syst. 2023 | B | 밀리미터파 드론 RCS 를 단일 값이 아니라 시계열 이미지로 보고 분류에 쓰는 접근도 있다(Ye 외, IEEE TAES 59(1), 2023). |

- ⚠ 대역 외삽을 하지 않으면 앵커가 얇고, 하면 근거 없는 외삽이 된다. 이 긴장은 해소되지 않았으므로 본문에서 정직하게 적을 것.
- ⚠ Das 와 Yuan 은 같은 기체(Phantom 3)를 재고도 세 대역에서 3.23-3.59 dB 어긋난다. Zhang 의 금속구 교정도 이론 대비 2 dB 가까이 벌어진다. 우리 ±2-3 dB 허용치의 근거이자 상한이다.
- ⚠ Wang(5G-A GBS)의 링크버짓은 UAV RCS 를 -10 dBsm 으로 가정하는데 출처가 없고 Semkin 계열보다 7-10 dB 낙관적이다.

### RW3. 광선추적·시뮬레이션 표적 시그니처 — 계산은 하되 검증은 하지 않는다

**논지** — Sionna 계열은 드론을 큐보이드·금속 정육면체·단순화 메시로 놓고 산란은 스톡에 맡기거나 상용 솔버로 나간다. 표적 산란 진폭을 계산하고 그것을 무엇엔가 대고 검증한 논문은 이 라이브러리에 없다.

| 인용키 | 게재처 · 연 | 등급 | 그대로 쓸 수 있는 한 문장 |
|---|---|---|---|
| `clutteraware_procieee26` | Proc. IEEE 2026 | P | 최근의 ISAC 종설은 단순화한 드론 메시를 Sionna 광선추적 씬에 넣어 클러터 환경을 site-specific 하게 생성하지만, 표적 산란 자체는 스톡 프레넬 반사에 맡기고 그 정확성을 검증하지 않는다(Liu 외, Proceedings of the IEEE 114(1), 2026). |
| `lambda_dataset_arxiv26` | arXiv 2607.03826 2026 | P | 저고도 ISAC 데이터셋 생성에서 전파는 Sionna RT 로, UAV 의 RCS 는 상용 EM 솔버(CADFEKO)로 따로 계산해 곱하는 것이 현재의 표준 관행이다(Zhou 외, arXiv:2607.03826). |
| `fwa_cube_arxiv26` | arXiv 2605.07623 2026 | P | 광선추적 기반 저고도 센싱 연구에서 UAV 는 흔히 금속 정육면체 한 개로 표현되며 표적 라벨조차 광선추적기가 반환한 경로 유형에서 유도된다(arXiv:2605.07623). |
| `li_mdrt_icct25` | Proc. IEEE 25th Int. Conf. Communicat… 2025 | P | Sionna RT 의 광선 발사기를 원뿔 샘플링으로 바꿔 회전 프로펠러의 마이크로도플러를 모사한 선례가 있으나(Li 외, ICCT 2025), 대상은 프로펠러 한 개이고 절대 산란량(dBsm)이나 검출 지표는 한 번도 제시되지 않는다. |
| `dmsnet_arxiv26` | arXiv 2607.17655 2026 | P | Sionna RT 로 만든 캠퍼스 디지털트윈에서 다중대역 UAV 센싱을 학습으로 푸는 Liu 외[arXiv'26]는 고·저 대역의 표적 산란응답이 상보적이라는 전제 위에 서 있지만, UAV 가 광선추적 씬에서 어떤 형상으로 표현되었는지는 논문에 기술되어 있지 않다. |
| `cellsense_arxiv26` | arXiv 2606.07900 2026 | P | 셀룰러 ISAC 패시브 센싱을 Sionna 씬과 실측 시제기로 함께 평가한 사례가 있으나 표적은 사람을 대신한 큐보이드이며(Kumar 외, arXiv:2606.07900), 오경보율도 CFAR 임계 교정이 아니라 검출 비율로 정의된다. |
| `greatx_arxiv25` | arXiv 2507.08716 2025 | P | 단일 게임 엔진 안에서 다중모달 ISAC 데이터를 합성하려는 시도도 있다(Great-X, arXiv:2507.08716). |
| `caviar_arxiv24` | arXiv 2401.03310 2024 | P | 6G 통신과 3D 시나리오, AI 를 공동 시뮬레이션하는 디지털 트윈 프레임워크에서 드론은 표적이 아니라 통신 종단으로 등장한다(CAVIAR, arXiv:2401.03310). |
| `ziganshin_multistatic_eucap25` | Proc. 19th European Conf. Antennas an… 2025 | P | Sionna RT 에 UTD 와 정점 회절을 더해 차량의 다중정적 산란을 계산하고 이를 PO/MLFMM 상용 솔버와 대조한 선례가 있으며, PO 가 하루 걸리는 계산을 광선추적은 2초에 끝낸다(Ziganshin 외, EuCAP 2025). |
| `ziganshin_curved_arxiv26` | arXiv 2604.05991 2026 | P | 기본 Sionna-RT 는 정반사와 1차 모서리 회절만 제공하며, 이산화된 곡면의 인공 산란을 없애려면 정점 회절과 고차 회절을 직접 추가해야 한다(Ziganshin 외, arXiv:2604.05991). |
| `rfgenesis_sensys23` | Proc. 21st ACM Conf. Embedded Network… 2023 | P | 사람 메시를 광선추적기에 통과시켜 mmWave 레이더 원신호를 합성하는 파이프라인은 SenSys 2023 에서 확립되었으며, 메시에서 레이더 에코까지 잇는 접근의 최상위 학회 기준선이다(RF Genesis). |
| `radartwin_arxiv26` | arXiv 2606.28396 2026 | P | 메시를 Mitsuba 기반 렌더러에 통과시켜 FMCW 원신호를 합성하고 실측과 짝지어 검증하는 파이프라인이 실내 인지 맥락에서 제시되었다(RadarTwin, arXiv:2606.28396). |
| `kataria_microdoppler_icasspw23` | Proc. IEEE Int. Conf. Acoustics, Spee… 2023 | B | 드론 마이크로도플러 서명의 시뮬레이션은 신호처리 학계에서도 별도로 다루어져 왔다(Kataria & Lall, ICASSP Workshops 2023). |
| `sionna_rt_techreport25` | arXiv 2504.21719 2025 | P | Sionna RT 는 경로 후보를 shooting-and-bouncing rays 로 생성하고 정반사·확산반사·굴절·1차 회절을 지원하지만, 물리광학 표면전류 적분과 RCS 출력은 제공하지 않는다(Ait Aoudia 외, Sionna RT Technical Report; Hoydis 외, Sionna RT). |
| `sionna_rt_globecom23` | Proc. IEEE Globecom Workshops 2023 | P | Sionna RT 는 미분가능 광선추적을 무선 전파 모델링에 도입한 확장이다(Hoydis 외, IEEE GLOBECOM Workshops 2023). |
| `sionna_lib_arxiv22` | arXiv 2203.11854 2022 | P | Sionna 는 GPU 위의 미분가능 링크레벨 시뮬레이션 라이브러리로 출발했으며, 그 초기 판(0.8.0)에는 광선추적이 없었다(Hoydis 외, arXiv:2203.11854). |
| `lee_dynamic_rcs_jees21` | J. Electromagn. Eng. Sci. 2021 | P | 회전 프로펠러의 동적 RCS 를 회전 불변 임피던스 행렬로 가속한 full-wave(MoM) 계산이 보고되어 있으며 상용 솔버와 편차가 거의 없다(Lee 외, JEES 21(4):322, 2021), 다만 대상은 프로펠러 한 장이고 기체는 포함되지 않는다. |
| `sagitta_sbr_po_arxiv26` | arXiv 2604.09243 2026 | P | GPU 위에서 SBR 과 이산 물리광학 적분을 결합해 모노스태틱 RCS 를 예측하고 PEC 구의 Mie 해로 검증하는 것은 확립된 절차다(Sagitta, arXiv:2604.09243). |
| `kirik_ptd_sbr_sigma19` | Sigma J. Eng. Nat. Sci. 2019 | P | SBR 기반 RCS 예측기에 물리회절이론(PTD)을 결합하는 구현은 해석해·실측·상용 솔버의 세 단계로 검증된 선례가 있으며 광선 밀도는 파장당 10 개가 표준적으로 쓰인다(Kirik & Ozdemir, Sigma J. Eng. Nat. Sci. 37(4):1153, 2019). |
| `kasdorf_sbr_coneangle` | arXiv 2021 | P | SBR 의 정확도는 광선 원뿔각 설정과 중복 광선 제거에 좌우되며, 이를 개선하면 훨씬 느린 image theory 광선추적과 같은 정확도에 도달할 수 있다(Kasdorf 외). |
| `rt_limits_learning_2026` | arXiv 2507.19653 2026 | U | 광선추적으로 만든 데이터가 학습 기반 RF 과제에서 갖는 한계는 별도로 정량화되어 있다(arXiv:2507.19653). |

- ⚠ 'Sionna 에는 SBR 이 없다' 는 거짓이다. 기술보고서 59쪽 전문에 'SBR' 44회(대소문자 구분)와 'shooting and bouncing' 3회가 나온다. 없는 것은 표면전류 PO 적분과 RCS 출력이다('physical optics' 0회 · 'radar cross section' 0회 — F10). ⚠ 종전 기록의 '48회' 는 두 표현을 합친 대소문자 무시 계수다.
- ⚠ md-rt(Li 외)가 바꾼 것은 광선 샘플러(구면→원뿔)이지 산란 모델이 아니다. '엔진을 고쳤다' 로 뭉뚱그리면 부정확하다.
- ⚠ Ziganshin 은 두 판이 있고 표적은 차량이다. 회의판(게재)과 저널 프리프린트를 절대 혼동하지 말 것(E2).

### RW4. 통신 하드웨어 위의 모노스태틱 ISAC — LaSen 이 이끈다

**논지** — 송신기를 소유하면 파형 전체를 알기 때문에 데이터 심볼까지 슬로타임 표본으로 끌어올 수 있다. 이 우회는 config A 에서만 성립하고, 조명원을 소유하지 않는 패시브 배치로는 이전되지 않는다.

| 인용키 | 게재처 · 연 | 등급 | 그대로 쓸 수 있는 한 문장 |
|---|---|---|---|
| `lasen_sensys26` | Proc. 24th ACM Conf. Embedded Network… 2026 | P | 능동 모노스태틱 배치에서는 gNB 가 자기 송신 파형 전체를 알고 있으므로 데이터 심볼까지 슬로타임 표본으로 끌어와 무모호 속도를 2.6 m/s 에서 20.2 m/s 로 넓힐 수 있으나(Yang 외, SenSys 2026), 이 우회는 송신기를 소유한 배치에서만 가능하며 조명원을 소유하지 않는 패시브 배치에는 이전되지 않는다. |
| `wei_rotor_md_twc25` | IEEE Trans. Wireless Commun. 2025 | P | ISAC 파형으로 실제 멀티로터의 로터 마이크로도플러를 추출한 실측 연구는 PRF >= 2 f_mD,max 라는 표본화 조건을 드론 맥락에서 이미 명시한다(Wei 외, IEEE TWC 24:10166-10182, 2025). |
| `saur_uav_isac_arxiv26` | arXiv 2605.23561 2026 | P | 개조하지 않은 상용 5G FR2 하드웨어로 도심에서 UAV 를 검출한 PoC 가 보고되어 있다(Saur 외, Nokia Bell Labs, 2026). |
| `wang_gbs_lawn_arxiv26` | arXiv 2603.14351 2026 | P | 5G-A 기지국 시제기로 저고도 UAV 를 추적한 야외 실측은 통신 자원 손실을 1.2 % 로 계상해 보고한다(Wang 외, 2026). |
| `golzadeh_sib1_ssb_vtc23` | Proc. IEEE 97th Vehicular Technology … 2023 | B | SSB 만으로 다운링크 센싱을 하려는 시도는 능동 배치에서도 반복률 제약에 부딪히며, 이를 완화하려고 SIB1 자원을 함께 쓰는 방식이 제안되었다(Golzadeh 외, IEEE VTC2023-Spring). |
| `khosroshahi_prs_pdsch_globecom24` | Proc. IEEE Global Communications Conf… 2024 | P | 5G NR 에서 PRS 와 PDSCH 를 함께 센싱에 쓰는 구성은 표준 자원 관점에서 이미 검토되었고, PRS comb 구조가 만드는 유령 표적이 함께 보고된다(Khosroshahi 외, IEEE GLOBECOM 2024). |
| `liu_nr_mono_positioning_isacom23` | Proc. 3rd ACM MobiCom Workshop on Int… 2023 | S | '모노스태틱 ISAC 는 기지국에 수신 체인을 하나 더 붙이는 것' 이라는 아키텍처 가정은 5G NR 모노스태틱 측위 연구에서 왔다(Liu 외, ACM MobiCom ISACom Workshop 2023). |
| `barneto_fullduplex_tmtt19` | IEEE Trans. Microw. Theory Techn. 2019 | B | 모노스태틱 ISAC 는 송신전력이 수신 잡음바닥보다 140 dB 이상 크다는 구조적 부담을 안고 100 dB 급 자기간섭 억제를 요구하지만(Baquero Barneto 외, IEEE TMTT 2019), 같은 논문은 이동 표적이 자기간섭에 본질적으로 강하다는 점도 함께 적는다. |
| `keskin_mono_isac_twc25` | IEEE Trans. Wireless Commun. 2025 | B | 데이터 심볼을 센싱에 재활용하면 모호 사이드로브가 올라간다는 결정론적-확률적 트레이드오프가 모노스태틱 ISAC 의 기본 제약으로 정식화되어 있다(Keskin 외, IEEE TWC 24(9), 2025). |
| `mmhawkeye_secon23` | Proc. IEEE Int. Conf. Sensing, Commun… 2023 | P | COTS mmWave 레이더로 비협조 UAV 를 검출하는 계열은 'passive' 를 '표적이 비협조' 라는 뜻으로 쓴다(Zhang 외, IEEE SECON 2023) — 조명원 소유권을 뜻하는 우리 용법과 구별해야 한다. |
| `hisac_sensys24` | Proc. 22nd ACM Conf. Embedded Network… 2024 | P | 바이스태틱 배치에서 거리분해능은 기하에 따라 c/(2B) 보다 나빠지며 이등분선 투영 계수가 붙는다(Pegoraro 외, ACM SenSys 2024). |
| `nataraja_bistatic_isac_tvt25` | IEEE Trans. Veh. Technol. 2025 | B | 5G NR 을 쓰는 바이스태틱 ISAC 는 차량 맥락에서 먼저 체계적으로 정리되었다(Nataraja 외, IEEE TVT 74(4), 2025). |

- ⚠ LaSen 은 우리 법칙을 반증하지 않는다. 균일 표본화를 포기(비균일 슬로타임 + 압축센싱)하는 방식으로 우회한다.
- ⚠ HiSAC 은 드론이 표적이 아니다(drone/UAV 0회). 분해능 규약 인용에만 쓸 것.

### RW5. 도플러 모호와 무모호 속도 — 우리 헤드라인이 놓이는 자리

**논지** — 패시브 드론 문헌은 CAF·CFAR·CPI 를 다 갖추고도 무모호 속도 칸을 대체로 비워 둔다. 비어 있지 않은 몇 편은 규약(전폭/반폭)과 슬로타임 축(심볼 간격/기준신호 반복 주기)이 서로 다르며, 그 차이가 우리 기여의 자리다.

| 인용키 | 게재처 · 연 | 등급 | 그대로 쓸 수 있는 한 문장 |
|---|---|---|---|
| `geng_lte_multistatic_ietrsn20` | IET Radar Sonar Navig. 2020 | P | LTE 패시브 레이더의 무모호 속도는 조명 파형의 반복 구조에 따라 전 다운링크 2647 m/s, CRS 705 m/s, 자체 설계 파일럿 176.5 m/s 로 갈리며(Geng 외, IET RSN 2020), 이는 반복률이 상한을 정한다는 규칙을 전폭 규약으로 적은 것이다. |
| `jopanya_ssb_spawc25` | Proc. IEEE 26th Int. Workshop Signal … 2025 | P | SSB 기반 패시브 바이스태틱 센싱에서 무모호 속도를 명시한 선행이 있으나(Jopanya & Osorio, SPAWC 2025), 그 식은 SSB 버스트 내부의 OFDM 심볼 간격을 슬로타임으로 삼은 것이며 SSB 반복 주기가 정하는 상한과는 다른 축이다. |
| `lasen_sensys26` | Proc. 24th ACM Conf. Embedded Network… 2026 | P | 능동 모노스태틱 배치에서는 gNB 가 자기 송신 파형 전체를 알고 있으므로 데이터 심볼까지 슬로타임 표본으로 끌어와 무모호 속도를 2.6 m/s 에서 20.2 m/s 로 넓힐 수 있으나(Yang 외, SenSys 2026), 이 우회는 송신기를 소유한 배치에서만 가능하며 조명원을 소유하지 않는 패시브 배치에는 이전되지 않는다. |
| `wei_rotor_md_twc25` | IEEE Trans. Wireless Commun. 2025 | P | ISAC 파형으로 실제 멀티로터의 로터 마이크로도플러를 추출한 실측 연구는 PRF >= 2 f_mD,max 라는 표본화 조건을 드론 맥락에서 이미 명시한다(Wei 외, IEEE TWC 24:10166-10182, 2025). |
| `abratkiewicz_ssb_jstars23` | IEEE J. Sel. Topics Appl. Earth Obser… 2023 | S | 5G SSB 를 펄스처럼 다루는 패시브 레이더 신호처리는 이미 별도로 보고되어 있다(Abratkiewicz 외, IEEE JSTARS 16:3469-3484, 2023). |
| `maksymiuk_renyi_rs22` | Remote Sens. 2022 | P | 5G 패시브 레이더의 거리분해능과 검출거리는 망 부하에 따른 자원 할당량에 종속되며, 다운링크에 데이터가 없으면 망은 반복주기 5-160 ms 의 동기 신호만 내보내 심각한 제약을 남긴다(Maksymiuk 외, Remote Sensing 14(23):6146, 2022). |
| `golzadeh_sib1_ssb_vtc23` | Proc. IEEE 97th Vehicular Technology … 2023 | B | SSB 만으로 다운링크 센싱을 하려는 시도는 능동 배치에서도 반복률 제약에 부딪히며, 이를 완화하려고 SIB1 자원을 함께 쓰는 방식이 제안되었다(Golzadeh 외, IEEE VTC2023-Spring). |
| `fang_lora_drone_infocomw22` | Proc. IEEE INFOCOM Workshops 2022 | B | 조명원 축은 WiFi·LTE·5G 밖으로도 확장되어 LoRa 를 조명원으로 쓰는 시도까지 보고되었으나(Fang 외, IEEE INFOCOM Workshops 2022), 낮은 반복률 때문에 속도 추정이 성립하지 않는다는 지적이 뒤따른다(Yang 외, SenSys 2026). |
| `taylor_lte_pbr_taes25` | IEEE Trans. Aerosp. Electron. Syst. 2025 | P | LTE 패시브 실측에서 관측된 드론의 바이스태틱 속도는 13 m/s 안팎에 머물며(Taylor & Poullin, IEEE TAES 2025), 이는 상시 기준신호만으로 얻는 무모호 속도와 직접 비교되는 값이다. |
| `sun_doppler_resolution_taes19` | IEEE Trans. Aerosp. Electron. Syst. 2019 | B | 드론 검출의 병목이 도플러 축에 있다는 인식은 지상 감시 레이더 문헌에서 먼저 확립되었으나(Sun 외, IEEE TAES 55(6), 2019), 그것은 분해능의 문제이지 반복률이 정하는 무모호 상한과는 다른 축이다. |
| `viberg_separable_passive` | arXiv 2601.15821 2026 | P | 분산 패시브 레이더에서 지연과 도플러를 분리 추정해 2D 탐색 비용과 노드 간 통신 부담을 줄이는 방법이 제안되었다(Viberg 외, arXiv:2601.15821). |
| `diseglio_reffree_ietrsn24` | IET Radar Sonar Navig. 2024 | P | 같은 WiFi 시스템으로 준-모노스태틱과 극단 바이스태틱을 나란히 관측하면 처리 방식별 우열이 기하에 따라 뒤바뀐다(Di Seglio 외, IET RSN 2024). |
| `hisac_sensys24` | Proc. 22nd ACM Conf. Embedded Network… 2024 | P | 바이스태틱 배치에서 거리분해능은 기하에 따라 c/(2B) 보다 나빠지며 이등분선 투영 계수가 붙는다(Pegoraro 외, ACM SenSys 2024). |
| `ji_bistatic_wcl26` | IEEE Wireless Commun. Lett. 2026 | P | 두 대의 LTE 기지국과 두 대의 패시브 수신기로 서로 다른 방향의 바이스태틱 도플러를 재면 LTE 의 거리분해능보다 정밀한 UAV 궤적 재구성이 가능하다(Ji 외, IEEE WCL 15:1807-1811, 2026). |

- ⚠⚠ 식 자체의 우선권은 우리 것이 아니다 — 다만 **Chen 도 아니다**(정정 R1, `docs/RETRACTION_LOG.md`). 우선권은 **Abratkiewicz 외, IEEE JSTARS 16:3469-3484 (2023), 식 (16) p.3476** 이고 반구간 규약까지 같다. LaSen 이 우선권을 Chen 에 돌리는 것은 **LaSen 의 요약**이지 Chen 의 인쇄물이 아니다. ⭐ 원문 확보됨(`/data/public/sionna_jeong/reference_library/g1g2/chen2024_applsci_14_4282.pdf`, 20쪽) — 'MDPI 403 미확보' 표기는 폐기. 재계수 결과 `PRF` **0회**, 닫힌 식 없음.
- ⚠⚠ 'ambiguity' 는 이 코퍼스에서 여섯 가지 다른 현상을 가리킨다(위상동기 실패·CFO·클러터 미분리·속도 부호 상실·거리 모호·AF 사이드로브). 문자열 검색으로 표를 채우면 E3 가 재발한다.
- ⚠ 우리 법칙은 '균일 슬로타임 푸리에 처리' 전제 위에서만 성능을 정한다. Viberg 식 비푸리에 추정기가 존재하므로 전제를 본문에 명시할 것.
- ⚠ Wypich 외(Sensors 2026)는 패시브 수신기가 SSB+PDCCH+PDSCH+CSI-RS 를 전부 복원한다고 보고한다(최대 속도 392 m/s, 규약 미확인). 헤드라인의 조건절은 '상시 기준신호만 쓰는 운용에서' 여야 한다.

### RW6. CFAR 와 오경보율 — 설계값과 달성값의 간극

**논지** — 이 코퍼스에서 오경보율은 거의 전부 설계값(nominal)으로만 보고된다. 실제 달성치를 별도로 잰 문헌은 하나뿐이고 그마저 표적이 드론이 아니다.

| 인용키 | 게재처 · 연 | 등급 | 그대로 쓸 수 있는 한 문장 |
|---|---|---|---|
| `he_convex_clutter_arxiv25` | arXiv 2512.24889 2025 | P | 패시브 레이더에서 CFAR 의 설계 오경보율은 클러터를 제대로 다루지 않으면 실제 달성치와 몇 자릿수씩 어긋나며(설계 1e-6 에 대해 실제 0.0141), 지연-도플러 면을 왜곡하지 않는 억제를 거쳐야 비로소 교정이 성립한다(He 외, arXiv:2512.24889). |
| `cellsense_arxiv26` | arXiv 2606.07900 2026 | P | 셀룰러 ISAC 패시브 센싱을 Sionna 씬과 실측 시제기로 함께 평가한 사례가 있으나 표적은 사람을 대신한 큐보이드이며(Kumar 외, arXiv:2606.07900), 오경보율도 CFAR 임계 교정이 아니라 검출 비율로 정의된다. |
| `taylor_lte_pbr_taes25` | IEEE Trans. Aerosp. Electron. Syst. 2025 | P | LTE 패시브 실측에서 관측된 드론의 바이스태틱 속도는 13 m/s 안팎에 머물며(Taylor & Poullin, IEEE TAES 2025), 이는 상시 기준신호만으로 얻는 무모호 속도와 직접 비교되는 값이다. |
| `zhang_cyclostationary_taes26` | IEEE Trans. Aerosp. Electron. Syst. 2026 | B | 패시브 레이더의 약한 표적 에코를 순환정상성 통계로 검출하는 대안도 제시되어 있다(Zhang 외, IEEE TAES 2026). |
| `pang_mfs_taes25` | IEEE Trans. Aerosp. Electron. Syst. 2025 | B | 패시브 레이더 기반 UAV 검출의 최신 신호처리 베이스라인은 운동 특징 분리 모델 계열이다(Pang 외, IEEE TAES 61(5), 2025). |
| `saur_uav_isac_arxiv26` | arXiv 2605.23561 2026 | P | 개조하지 않은 상용 5G FR2 하드웨어로 도심에서 UAV 를 검출한 PoC 가 보고되어 있다(Saur 외, Nokia Bell Labs, 2026). |

- ⚠ Pfa 의 정의가 문헌마다 다르다 — 설계값 / '검출 중 오검출 비율'(CellSense) / 달성치(He). 나란히 놓기 전에 정의를 열로 표시할 것.

### RW7. 분류에 들어가지 않는 것들 — 방출 기반과 융합

**논지** — 드론 RF 센싱 문헌의 큰 갈래 하나는 표적 자신의 송신을 듣는다. 우리 기하 축과는 무관하지만, 통신 링크가 없으면 무력하다는 한계가 반사 기반 접근의 존재 이유를 정당화한다.

| 인용키 | 게재처 · 연 | 등급 | 그대로 쓸 수 있는 한 문장 |
|---|---|---|---|
| `matthan_mobisys17` | Proc. 15th Annu. Int. Conf. Mobile Sy… 2017 | B | 드론의 RF 통신 신호에서 물리적 서명을 찾아 존재를 검출하는 방출 기반 접근은 MobiSys 2017 에서 확립되었으나(Nguyen 외), 표적이 통신하지 않으면 성립하지 않는다. |
| `dronescale_sensys20` | Proc. 18th ACM Conf. Embedded Network… 2020 | B | 방출 기반 계열은 드론이 내는 RF 만으로 적재 중량까지 추정할 만큼 발전했지만(Nguyen 외, ACM SenSys 2020), 표적이 송신해야만 동작한다는 점에서 반사 기반 접근과 상보적이다. |
| `xu_rf_fingerprint_icassp21` | Proc. IEEE Int. Conf. Acoustics, Spee… 2021 | B | RF 지문 분해로 소형 UAV 를 검출하는 방출 기반 접근은 신호처리 학계에도 독자적 계보를 갖는다(Xu 외, ICASSP 2021). |
| `milani_fusion_rs21` | Remote Sens. 2021 | P | WiFi 대역에서는 표적 자신의 방사를 듣는 방출 기반 측위와 반사를 보는 패시브 레이더를 한 시스템에서 융합한 사례도 있다(Milani 외, Remote Sensing 13(18):3556, 2021). |
| `chen_event_rotation_sensys26` | Proc. 24th ACM Conf. Embedded Network… 2026 | B | 프로펠러 회전을 드론 센싱의 1차 정보원으로 삼는 관점은 2026년 SenSys 에서 RF 계열과 이벤트 카메라 계열 양쪽으로 동시에 제기되었다(Chen 외, pp.746-760). |
| `wu_miros_infocom26` | Proc. IEEE Conf. Computer Communicati… 2026 | B | 비인가 AAV 측위를 레이더와 비전의 다중 시점 융합으로 푸는 접근이 2026년 INFOCOM 에 제시되었다(Wu 외). |
| `lam_6d_drone_infocom25` | Proc. IEEE Conf. Computer Communicati… 2025 | B | 드론을 다루는 mmWave 연구의 상당수는 드론이 협조적으로 자기 위치를 구하는 문제를 풀며(Lam 외, IEEE INFOCOM 2025), 비협조 침입자 검출과는 문제 설정이 반대다. |

- ⚠ 이 문단의 논문들은 우리 2x3 격자에 들어가지 않는다. 격자 밖이라는 사실 자체를 적어야 격자가 임의적으로 보이지 않는다.

## 7. ⭐ 공백 진술

> ⭐ 좁게 참인 공백: **드론 기체의 3-D 표면 메시에 대해 산란 진폭을 GPU 광선엔진 안에서 직접 계산하고, 그 진폭을 외부 앵커에 대고 검증한 뒤, 같은 파이프라인으로 모노스태틱과 바이스태틱 두 기하 x 세 상시 조명원에 대해 경험적 Pfa 로 교정된 CFAR 검출률까지 이어 붙인 연구는 이 라이브러리에 없다.** 네 요소 중 최대 두세 개까지만 겹친다.

**왜 좁게 적는가.** 이 프로젝트는 이미 넓은 주장을 한 번 철회했다(R20 novelty 대정정). 그래서 공백은 '아무도 안 했다' 가 아니라 '이 네 조건을 동시에 만족한 논문이 없다' 로 진술한다. 각 조건은 개별적으로는 선행이 있다.

### 7.1 각 조건에는 개별 선행이 있다

- 메시 + 광선엔진 내부 산란: Ziganshin(EuCAP 2025, 게재) — 다만 표적이 차량이고 기하는 멀티스태틱이며 드론이 아니다.
- 드론 메시를 Sionna 씬에 넣기: Clutter-Aware ISAC(Proc. IEEE 114(1)) — 다만 산란은 스톡 Fresnel 이고 41쪽에 validat* 0회.
- 드론 + 광선추적 + 마이크로도플러: Li 외(ICCT 2025) — 다만 표적이 목재 프로펠러 1개이고 검증은 운동학(리지 위치)뿐, 진폭 주장 0건.
- 드론 mono+bi RCS + 패시브 예산 + OTA 검출: ⚠⚠ Rzewuski 외(NATO STO 2021, F9) — 이미 다 했다. 엔진이 FDTD 이고 조명원이 WiFi/DVB-T 두 종이며 CFAR 경험 교정이 없다는 점만 다르다.
- 무모호 속도 상한 식: Chen 외(Appl. Sci. 2024, 원문 미확보) 와 Jopanya(SPAWC 2025) 가 이미 쓴다. Wei(TWC 2025)는 PRF >= 2 f_mD 형태로 쓴다.
- CFAR 달성 Pfa 정량화: He(arXiv:2512.24889) — 다만 표적이 드론이 아니고 프리프린트다.

### 7.2 ⭐ 그래서 진짜 우리 것은

- ① 같은 표적 표현(메시 + 재질 가중 PO)과 같은 검출 체인 아래에서 기하 2 x 조명원 3 을 **교차표로** 돌린 것. 개별 칸은 선행이 있지만 교차표는 없다.
- ② 무모호 속도를 **기준신호 반복 축**에서 반폭 규약으로 정의하고, 그 값을 세 편의 독립 논문 숫자에 대입해 재현한 것(규약만 맞추면 전부 재현된다). 식의 우선권이 아니라 **축의 구별과 교차 검증**이 기여다.
- ③ CFAR 를 설계 Pfa 가 아니라 경험적 Pfa 로 교정하고 그 위에서 검출률을 보고한 것 — 드론 표적에 대해서는 이 라이브러리에서 유일하다.
- ④ config B(패시브 준-모노스태틱)를 명시적 실험 조건으로 둔 것. B 열에 명시적 근거가 있는 문헌은 Martelli(2017)와 Demissie(2024) 둘뿐이고 B x 5G 는 아예 비어 있다.

### 7.3 ⛔ 절대 주장하면 안 되는 것

- ⛔ '드론 mono/bistatic RCS 와 패시브 검출을 함께 다룬 최초' — Rzewuski(2021)가 반증한다.
- ⛔ '무모호 속도 식을 처음 제시' — Chen(2024)·Jopanya(2025)·Wei(2025)가 반증한다.
- ⛔ 'Sionna 로 드론을 다룬 최초' — Clutter-Aware(2026)·Li(2025)·FWA cube(2026)가 반증한다.
- ⛔ 'Sionna 에는 광선추적 산란이 없다' — 기술보고서 59쪽에 'SBR' 44회(대소문자 구분)와 'shooting and bouncing' 3회가 있다. 없는 것은 PO 표면적분과 RCS 출력이다('physical optics' 0회, 'radar cross section' 0회).
- ⛔ 'passive 는 곧 상시 기준신호만 쓴다' — Wypich(Sensors 2026)가 반증한다. 조건절을 붙일 것.

### 7.4 아직 주장할 수 없는 것

⚠ 'B x 5G 는 문헌 공백이다' 는 주장은 아직 이르다. dblp 가 색인하지 않는 5개 게재처(IEEE TAP·AWPL·EuCAP·IET RSN·TMTT)를 손으로 더 뒤진 뒤에만 할 수 있다.

### 7.5 novelty 가드

**G1 — F9 Rzewuski (NATO STO 2021)**

Parrot AR.Drone 의 mono/bistatic RCS 를 FDTD(QuickWave-3D)로 계산하고, 패시브 레이더 커버리지 예산을 세우고, WiFi 와 DVB-T 로 50 m OTA 검출까지 했다. 우리 최종 산출물의 형태를 이미 만든 논문이다. 차별점은 (a) 엔진이 FDTD 대 GPU SBR+PO, (b) 조명원이 2종 대 3종 + 기하 교차표, (c) CFAR 경험적 Pfa 교정, (d) 표적이 1기종 대 5기종 이지, '처음' 이 아니다.

**G2 — H8 은 네 프롱 문자 그대로일 때만 산다**

⭐ H8 은 살아남았다. 교집합 8편(+경계 6편)을 이번 세션에 원문으로 다시 열어 프롱 채점한 결과, 네 프롱을 동시에 만족하는 논문은 0편이다. 우리 포지셔닝을 바꿀 필요는 없다. 다만 프롱별 최대치는 P1·P2·P3 를 동시에 만족하는 Clutter-Aware ISAC(Proc. IEEE 114(1))이며, 그 논문은 P4(진폭 검증)가 통째로 없다 - 본문 41쪽에 'validat' 0회, 'dBsm' 0회를 이번에 직접 세었다.

- ① '게재된(published)' 을 반드시 붙인다 — 프리프린트를 포함하면 프롱이 흔들린다.
- ② '검증된(validated)' 을 반드시 붙인다 — Clutter-Aware 가 P1+P2+P3 를 이미 만족하므로 H8 의 무게 전부가 P4(진폭 검증) 한 프롱에 실린다.

**G3 — ⭐ 축을 두 개로 분리해 적는다**

우리 C 는 '조명원 비통제 + 기하 바이스태틱' 이고, FWA cooperative sensing(2605.07623)은 '조명원 통제 + 기하 바이스태틱' 이다. 격자 각주 한 줄로 '조명원 통제권' 과 '기하' 를 분리된 축으로 명시하면, '셀룰러 협조형 바이스태틱은 왜 뺐나' 라는 질문에 답이 생긴다.

**G4 — 미확보 문헌 두 편이 novelty 문장을 붙잡고 있다**

(a) Chen 외 Appl. Sci. 14(10):4282 (2024) — MDPI 403, 우리 법칙의 최근접 외부 근거인데 LaSen 경유 2차 인용 상태. (b) Abratkiewicz 외 JSTARS 16:3469-3484 (2023) — SSB 도플러 모호를 이미 다뤘다는 제3자 요약이 2건. 둘 다 확보 전에는 '처음' 류 문장을 쓰지 않는다.

## 8. 인용 금지 · 미해결 · 신뢰등급

### 8.1 ⛔ 인용 금지

**HZ1** — `/data/public/sionna_jeong/papers_isac_sionna/paper_sionna_Ray_0723/Sionna RT 드론 ISAC 연구.pdf`

- ⭐⭐ 이것은 논문이 아니다. PDF 메타데이터 producer 가 'Skia/PDF m152 Google Docs Renderer' 이고 제목이 한국어('Sionna RT 드론 ISAC 연구'), 저자 없음, 게재처 없음, DOI 없음. 내용은 '독립 최신 Sionna RT 환경 기반 소형 UAV 의 3D 메쉬 및 전자기 재질 반영 고정밀 ISAC 채널 에뮬레이션 기술 분석 보고서' - 즉 우리 연구주제 그 자체를 요약한 AI 리서치 보고서다.
- **왜 위험한가** — 본문에 sionna 42회, RCS 11회, UAV 28회가 들어 있어 어떤 자동 term-count 교집합에도 상위로 올라온다. outputs/reflib_sweep_venues.json 의 교집합 17행에도 실제로 들어가 있다. 여기에 적힌 어떤 문장·수치도 문헌 근거가 아니며, 이것을 선행연구로 인용하면 E1(있지도 않은 결과를 서베이 헤드라인으로 주장)과 E6(아카이브에 없는 논문에 수치 귀속)을 한꺼번에 재발시킨다.
- **조치** — 교집합/센서스 스크립트에 파일명 화이트리스트가 아니라 '저자행+게재처 문자열 없으면 non_paper' 규칙을 넣을 것. 이 파일은 어떤 리포트에도 인용 금지.

### 8.2 ⭐ 이 라운드가 원문에 대고 다시 센 것

⭐ 이 라운드가 산출물을 만들면서 '가장 무게가 실린 세 수치' 를 PDF 원문에 대고 다시 세었다. 하나가 부정확해 정정했다.

**주장** — Clutter-Aware ISAC (Proc. IEEE 114(1)) 는 표적 산란 진폭을 검증하지 않는다

- **PDF** — `/data/public/sionna_jeong/papers_isac_sionna/paper_sionna_Ray_0723/Clutter-Aware_Integrated_Sensing_and_Communication_Models_Methods_and_Future_Directions.pdf` (41쪽)
- **계수** — `validat` = 0, `dBsm` = 0, `radar cross section` = 1, `Sionna` = 13, `simplified 3-D mesh` = 1
- **판정** — CONFIRMED. 단 'radar cross section' 이 1회 나오므로 'RCS 라는 말이 없다' 로 과장하지 말 것. 우리 주장은 '진폭을 검증하지 않았다' 까지다.

**주장** — Sionna RT 기술보고서에 SBR 이 48회 나온다 (F10)

- **PDF** — `/data/public/sionna_jeong/sionna_papers_by_task/channel_modeling_raytracing/2504.21719__sionna-rt-technical-report-v1.pdf` (59쪽)
- **계수** — `SBR (case-sensitive)` = 44, `sbr (case-insensitive)` = 45, `shooting and bouncing (ci)` = 3, `sum used by prior_settled_sionna.json` = 48, `physical optics` = 0, `radar cross section` = 0, `RCS` = 0
- **판정** — ⚠ CORRECTED. 48 은 'SBR 단독' 이 아니라 'SBR 또는 shooting-and-bouncing' 을 대소문자 무시로 합친 값이다(45+3). 결론('Sionna 는 SBR 을 한다, PO 표면적분과 RCS 출력이 없다')은 그대로 유지되지만, 숫자를 인용할 때는 계수 규칙을 함께 적어야 한다.

**주장** — md-rt(ICCT 2025) 내부에 10배 불일치가 있다

- **PDF** — `/data/public/sionna_jeong/papers_isac_sionna/paper_sionna_Ray_0723/Micro-Doppler_Signature_Simulation_of_Multirotor_UAVs_Using_Ray_Tracing.pdf` (6쪽)
- **근거** — Table I: 'Propeller radius 10.55cm'
- **근거** — Fig.6 문단: 'Under the conditions of a blade length of 1.055 meters'
- **판정** — CONFIRMED. 두 문장 모두 오늘 원문에서 다시 읽었다. 어느 쪽을 인용하든 다른 쪽도 함께 적을 것.

### 8.3 미해결

- Chen 외 Appl. Sci. 14(10):4282 (2024) 원문 미확보(MDPI 403). 우리 법칙의 최근접 외부 근거가 LaSen 경유 2차 인용 상태다.
- Abratkiewicz 외 JSTARS 16:3469-3484 (2023) 원문 미확보. SSB 도플러 모호 선행 가능성 — novelty 문장을 확정하기 전에 반드시 확보.
- Sagitta(2604.09243)의 저자·정식 제목 미추출. 엔진 방법 인용으로 쓰려면 서지 확정 필요.
- Costa JSTEAP 저널판의 권·호·쪽·DOI 와 저널명 문자열 미확정.
- Kasdorf/Notaros 와 2507.19653 은 게재처 UNVERIFIED.
- dblp 가 IEEE TAP·AWPL·EuCAP·IET RSN·TMTT 를 색인하지 않아 자동 스윕이 구조적으로 0건이다. B x 5G 공백 주장은 손 스윕 뒤로 미룬다.
- HiSAC 의 바이스태틱 분해능 일반형(c/[2B cos(beta/2)])은 원문에서 확인하지 못했다. 특정 기하 형태만 확인됨.
- 아카이브 미독본 **11편** 잔존(2601.10846, 2606.07328, 2502.11540, 2507.12235, 2512.03506, 2601.08042, 2407.19084, bilkent_thesis, diva_1595877, gbppr, 1910.13706).
  ⭐**2601.03302(CageDroneRF)는 2026-08-27 정독 완료** → [`PAPER_CAGEDRONERF_2601.03302.md`](PAPER_CAGEDRONERF_2601.03302.md). 부록 A-8/A-8b/A-8c 축자 인용 3건을 원문에서 확인했고, 검출 표(Table II)·단일 라벨 53.49 %·OSR 75.15 % 를 새로 기록했다.

### 8.4 신뢰등급 집계

| 항목 | 값 |
|---|---|
| `master_rows` | 94 |
| `grade_P_pdf_read` | 64 |
| `grade_B_bibliographic_only` | 25 |
| `grade_S_or_U` | 5 |
| `status_published` | 66 |
| `status_preprint` | 23 |
| `status_accepted` | 1 |
| `status_unverified_venue` | 2 |
| `entries_marked_incomplete` | 32 |
| `entries_with_pdf_on_disk` | 65 |
| `verbatim_quotes_carried` | 158 |
| `entries_with_cautions` | 77 |
| `bibtex_entries` | 94 |
| `bibtex_entries_incomplete` | 32 |
| `sionna_table_rows` | 30 |
| `intersection_entries` | 8 |
| `intersection_passing_all_four_prongs` | 0 |

---

*기계 원본은 `outputs/reference_library.json`. BibTeX 는 `docs/references.bib` (94항목, INCOMPLETE 32). 소스: `outputs/reflib_read.json`, `outputs/reflib_cross.json`, `outputs/reflib_sweep_venues.json`, `outputs/reflib_sweep_sionna.json`, `outputs/reflib_sweep_geometry.json`.*
