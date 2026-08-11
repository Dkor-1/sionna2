# 패시브 센싱 · OFDM 마이크로도플러 · 딥러닝 — 선행연구 조사 (2026-08-11)

> **답할 질문 셋**
> - **Q1** 드론 탐지·분류를 **패시브 센싱**으로 한 논문이 무엇이 있나
> - **Q2** **마이크로도플러를 OFDM 파형으로** 센싱·측정한 논문이 있나
> - **Q3(앞선 요청)** 딥러닝으로 방향을 정했으니, 비슷한 태스크의 **딥러닝 프레임워크** 선행연구
>
> 수치 원장: `outputs/survey_passive_ofdm_dl.json` (키 `synthesis`, 그리고 각 조사 각도별 원본 키).
>
> ---
>
> ⚠ **읽음 등급 표기 — 이 문서 전체에서 지킨다.**
>
> | 표기 | 뜻 |
> |---|---|
> | **`[원문]`** | PDF 를 내려받아 본문을 직접 읽었다. 표·절 위치를 적을 수 있다. |
> | **`[초록]`** | 초록을 **축자로** 확인했다(Crossref·OpenAlex·S2 가 IEEE 초록을 미러). 본문은 못 봤다. |
> | **`[2차]`** | 원문도 초록도 못 봤다. **다른 논문이 인용하며 적어 준 서술**만 봤다. 수치를 우리 표에 그대로 옮기면 안 된다. |
>
> ⛔ 이 조사는 **«그런 논문이 없다»를 결론으로 쓰지 않는다.** 쓸 수 있는 문장은
> **«이번 조사 범위에서 못 찾았다»** 뿐이다.

---

## 0. 여섯 줄 요약

1. **Q1 — 있다. 그것도 «분류까지» 간 것이 최소 6편이다.** 다만 **전부 방송·위성 조명원**(DVB-T2 · DVB-T ·
   DTMB · DVB-S · GNSS)이다. **셀룰러(LTE · 5G)·WiFi 조명원에서 분류까지 간 게재 논문은 이번 범위에서
   못 찾았다** — 그쪽은 검출·측위·추적에서 멈춘다.
2. ⛔ **그래서 우리가 여러 문서·덱에 써 온 «패시브 선행은 대부분 검출에서 멈춘다» 는 조명원 한정어 없이는
   거짓이다.** 「셀룰러·WiFi 조명원에 한해」를 반드시 붙여야 한다.
3. **Q2 — 있다. 그런데 답이 두 갈래로 갈린다.**
   ⭐**«패시브 OFDM 으로 로터 마이크로도플러를 봤다» 는 방송 OFDM(DVB-T2 · DVB-T · DTMB)에서 보고된다.**
   **«셀룰러 OFDM(5G NR)으로 봤다» 는 전부 모노스태틱 자체 테스트베드**(Wei, BUPT)이거나
   **자체 채널사운더**(Costa, TU Ilmenau)이고, **상시 기준신호(SSB · CRS · CSI-RS)만으로 본 사례는 못 찾았다.**
   그 반대 방향의 실측 근거는 있다 — Chen 외(Appl. Sci. 2024)가 상용 5G 로 회전표적을 겨눴다가
   **«도플러가 측정범위를 넘어 접혔다»** 고 보고한다.
4. **Q2 의 물리적 이유가 숫자로 있다.** Wei 외(IEEE TWC 2025)는 **심볼률이 곧 PRF** 라는 것을 프레임 설계
   문제로 바꿨다. 3.5 GHz · 로터 80 r/s · 블레이드 0.5 m 면 **왕복 팁 도플러 ±5864 Hz**, 즉 **PRF ≥ 11.7 kHz**
   가 필요하다(⭐논문 자신은 계수 2 를 빠뜨려 5868 Hz 라 적었다 — §2-3). **5G SSB 주기 20 ms = 50 Hz** 는
   여기서 **234 배 모자란다.** 우리 «5G 이중고» 서사는 이 자리에서 정량적으로 선다.
5. **Q3 — 딥러닝은 «어떤 망이냐» 가 아니라 «무엇을 먹이느냐» 가 지배한다.** 같은 망을 고정한 채
   **입력 전처리 하나로 +10.0 포인트**(A-SPC, KAIST)가 나오는데, **백본 용량을 2.2 배 키우면 +0.7 포인트**
   (Glüge, VGG11→VGG19)에 그친다. **파라미터 0.15~0.22 M 급 소형 CNN 이면 충분하다**는 것이
   서로 다른 네 그룹에서 일치한다.
6. ⭐ **우리를 정면으로 겨누는 반증 셋을 확보했다** — Cao 외(Appl. Sci. 2025 §4, 방송대역에서 드론끼리
   구분은 어렵다) · AirGuard(JSAC, 미학습 기체에서 정확도 4.49% 로 붕괴) · Kearney & Gurbuz(TAES 2026 §V-A,
   **저충실도 시뮬 단독 학습은 random guessing 을 못 넘었다**). 셋 다 우리 계획의 전제를 때린다.

---

## 1. Q1 — 패시브 센싱으로 드론 탐지·분류

### 1-1. 먼저 낱말부터 — «패시브» 가 코퍼스에서 네 뜻으로 쓰인다

⭐ 이걸 정리하지 않으면 인용 하나로 즉시 반박당한다.

| 뜻 | 무엇 | 대표 |
|---|---|---|
| **(1) 기회조명 바이스태틱 레이다** | 남의 송신기를 조명원으로 빌려 **표적 에코**를 받는다 | 이 절의 거의 전부 |
| (2) 드론 자체 방사 수신 | 드론의 **제어링크·영상링크를 듣는다**(RF 지문·TDOA). 표적 운동은 무관 | arXiv:2512.14608(AERPAW) · Glüge J-RFID 2024 |
| (3) 전방산란(p-FSR) | 표적이 Tx–Rx 직선을 가로지를 때의 회절 | Abdullah, Remote Sens. 2020 · Abdul Aziz, IJIE 2023 |
| (4) 무송신 기만 | 아예 다른 주제 | Kozlov, Sci. Rep. 2025 |

**우리 문서는 (1)만 쓴다.** IEEE COMST 2025 는 §V-D(=(1))와 §VI(=(2))를 명시적으로 분리한다 —
**우리도 같은 분리를 문서에 박아야 한다.**

### 1-2. ⭐표 — 패시브 드론 논문, 조명원별

**«분류» 열의 뜻**: `검출` = 있다/없다까지 · `측위·추적` = 위치·궤적까지 ·
**`분류` = 표적 종류를 갈랐다**(⭐로 표시).

| # | 논문 | 조명원 | OFDM? | 실측/시뮬 | 어디까지 | 게재처 | 연도 | 읽음 |
|---|---|---|---|---|---|---|---|---|
| 1 | Vorobev·Veremyev·Tulenkov, *Experimental DVB-T2 Passive Radar Signatures of Small UAVs* | DVB-T2 | **예** | **실측** | ⭐**분류** | SPSympo(학회), pp.67–70 | 2019 | **`[초록]`** |
| 2 | Jarabo-Amores 외, *Drone detection feasibility with passive radars* | DVB-T | **예** | **실측** | ⭐**분류** | EuRAD(학회), pp.313–316 | 2018 | **`[2차]`** |
| 3 | Kulpa·Malanowski·Bączyk, *Passive Radar for Drone Detection and Classification* | 미상 | 미상 | **실측** | ⭐**분류** | IRS(학회), Hamburg | 2025 | **`[초록]`** |
| 4 | Cao 외, *A Novel Recognition-Before-Tracking Method…* | DTMB | (TDS-OFDM) | 실측+합성 | ⭐**분류** | Applied Sciences 15(18):9957 | 2025 | **`[원문]`** |
| 5 | Ummenhofer 외, *UAV Micro-Doppler Signature Analysis Using DVB-S Based Passive Radar* | DVB-S | **아니오** | **실측** | 마이크로도플러 추출(분류는 «might») | IEEE RADAR(학회), pp.1007–1012 | 2020 | **`[초록]`** |
| 6 | Clemente 외, *GNSS Based PBR for Micro-Doppler based Classification of Helicopters* | GPS L1 C/A | **아니오** | **실측** | ⭐**분류**(단 표적=헬기) | IEEE Int. Radar Conf.(학회) | 2015 | **`[원문]`** |
| 7 | Wang 외, *Complex Clutter Suppression and UAV Detection in the Lightweight DTMB-Based Passive Radar* | DTMB | (TDS-OFDM) | **실측** | 검출 + **마이크로도플러 관측** | ICVISP(학회) | 2025 | **`[초록]`** |
| 8 | Demissie & Steffes, *Drone Detection With a LTE450-Based Passive Radar* | **LTE450** | **예** | **실측** | 검출·측위 | IET Radar, Sonar & Nav. 19:e70092 (OA) | 2025 | **`[원문]`** |
| 9 | Sun 외 (LIPASE), *An Experimental Study of Passive UAV Tracking with Digital Arrays and Cellular Downlink* | **LTE** | **예** | **실측** | 검출·측위·추적 | arXiv:2412.20788v1 ⚠게재판 별도 | 2024 | **`[원문]`** |
| 10 | Ji 외, *Doppler-Based Multistatic Drone Tracking via Cellular Downlink Signals* | **LTE** | **예** | **실측** | 추적 | arXiv:2509.25732 | 2025 | **`[초록]`**(1쪽) |
| 11 | Wypich & Zielinski, *Experimental Evaluation of 5G NR OFDM-Based Passive Radar…* | **5G NR** | **예** | 실측(⚠SDR 에뮬 기지국) | 검출 | Sensors 26(4):1317 (OA) | 2026 | **`[원문]`** |
| 12 | Chen 외, *Rotating Target Detection Using Commercial 5G Signal* | **5G NR** | **예** | **실측** | 검출 + ⛔**도플러 접힘** | Applied Sciences 14(10):4282 | 2024 | **`[원문]`** |
| 13 | Jopanya & Osorio, *Utilizing 5G NR SSB Blocks for Passive Detection and Localization…* | **5G SSB** | **예** | 시뮬 | 검출·측위(CRB) | IEEE SPAWC(학회) | 2025 | **`[원문]`** |
| 14 | Abratkiewicz 외, *SSB-Based Signal Processing for Passive Radar Using a 5G Network* | **5G SSB** | **예** | 실측+시뮬 | 검출 | IEEE JSTARS 16:3469– | 2023 | **`[원문]`** |
| 15 | Huang 외, *Fuse-then-Detect for Passive UAV Localization Using Multi-UE 5G Uplink* | **5G 상향 SRS** | **예** | 시뮬 | 측위 | arXiv:2607.11955 | 2026 | **`[원문]`** |
| 16 | Schüpbach 외, *Micro-UAV detection using DAB-based passive radar* | DAB+ | **예** | **실측** | 검출(최고 36%) | IEEE RadarConf(학회) | 2017 | **`[2차]`** |
| 17 | Abdullah 외, *Passive Forward-Scattering Radar Using DVB-S…* | DVB-S(전방산란) | **아니오** | **실측** | 검출 ⛔**본문에 classification 0회** | Remote Sensing 12(18):3075 | 2020 | **`[원문]`** |
| 18 | Abdul Aziz 외, *…Drone Detection and Classification in LTE-Based Passive FSR* | LTE(전방산란) | **예** | **실측** | ⚠«분류»=**고도 2 m vs 3 m** | Int. J. Integrated Eng. 15(3) | 2023 | **`[원문]`** |
| 19 | Wu 외, *Posterior-Aware Differential Channel Tracking for … DAB+ Passive Radar* | DAB+ | **예** | **실측**(민항기) | 검출·기준채널 복원 | arXiv:2605.24385 | 2026 | **`[원문]`** |
| 20 | Viberg 외 3편 계열 (ECA 불완전 기준신호 통계) | 일반 | — | 시뮬 | 이론(추정 효율) | arXiv:2601.20817 / 2510.07948(CAMSAP25) / 2601.15821(ICASSP26) | 2025–26 | **`[초록]`** |
| 21 | Khawaja 외, *A Survey on Detection, Classification, and Tracking of UAVs…* | (서베이) | — | — | 조명원별 총람 | **IEEE COMST**(⚠아래 주) | 2025 | **`[원문]`**(프리프린트) |
| 22 | Tang 외, *UAV Detection with Passive Radar: Algorithms, Applications, and Challenges* | (리뷰) | — | — | 총람 | Drones 9(1):76 | 2025 | **`[원문]`** |

⚠ **21번 주의(정정 항목):** 우리가 인용해 온 «§V-D7 p.25 · 참고문헌 [247]» 위치표기는
**arXiv:2402.05909v2 프리프린트**의 것이다. **게재판은 제목이 UAV→AAV 로 바뀌었고**
(DOI 10.1109/COMST.2025.3554613, vol.28, pp.3272–3310) **25쪽이라는 쪽번호가 존재하지 않는다.**

### 1-3. ⭐«분류까지» 간 6편이 공통으로 말하는 것 — **재질이 분류를 가른다**

이것이 이번 조사에서 가장 재사용 가치가 큰 발견이다. 서로 독립인 네 편이 같은 결론에 닿는다.

| 논문 | 무슨 말을 하나 | 읽음 |
|---|---|---|
| Vorobev, SPSympo 2019 | 로터 회전수 도플러 서명 차이로 분류 가능 — **단 플라스틱 블레이드를 쓴 최소형 기체는 제외** | `[2차]` (Demissie §1) |
| Jarabo-Amores, EuRAD 2018 | **흑연 재질 중형 UAV 는 분류까지**, 플라스틱은 신호가 약해도 **검출만** | `[2차]` (Drones §5) |
| Demissie, IET RSN 2025 | **수평편파를 택한 이유가 탄소섬유 로터** — 수직편파면 반사가 약해진다 | **`[원문]`** |
| Abdullah, Remote Sens. 2020 | CST 로 **PEC vs 플라스틱** 블레이드 전방산란 RCS 를 나눠 시뮬 | **`[원문]`** |

⇒ **우리에게 뜻하는 것.** 우리 재질가중 PO(`GROUP_GAMMA`)는 지금 **σ 절대값 축**으로만 기록에 들어가 있다.
문헌은 그것을 **«분류 가능성» 축**으로 쓴다. **우리 5기종 중 플라스틱 프로펠러 기체는 같은 실패를 겪을
것이라는 예측을 세우고 시험할 수 있다** — 새 실험 설계가 하나 열린다.

### 1-4. 셀룰러 갈래에는 «분류» 열이 아예 없다

LIPASE(arXiv:2412.20788) **Table I** 이 패시브 UAV 실험 17편을 조명원·주파수·대역폭·기하·**D/L/T**
(Detection/Localization/Tracking)·안테나·표적·베이스라인·거리·측위오차로 정리하는데,
⭐**C(Classification) 열이 아예 없다.** 이것이 «셀룰러 패시브는 검출·측위·추적에서 멈춘다» 는
우리 문장의 가장 직접적인 근거다 — **단 조명원 한정어를 붙였을 때만 참이다.**

그리고 그 표는 **우리 report12 비교표의 열 구성을 그대로 베낄 표준**이기도 하다. 사과-대-사과를 하려면
우리 표를 여기에 맞춰야 한다.

### 1-5. 실측 Pd 를 «교정된 Pfa 와 함께» 인쇄한 드문 사례

우리 report10(CFAR 경험교정)의 사과-대-사과 대조군으로 쓸 수 있는 것은 사실상 하나다.

**Demissie & Steffes, IET RSN 19:e70092, 2025 `[원문]`**
- 표적 DJI Matrice M210(약 88×88×39 cm, <5 kg), GPS 로거 지상진리, USRP X310+TwinRX, CIT T=0.8 s
- 단채널: **Pfa=1e-4 에서 바이스태틱 약 1600 m**(§4, Fig.11)
- 다채널(4소자 Yagi ULA·수평편파) **Table 1**: 거리오차 0.93±15.7 ~ 10.4±9.1 m,
  도플러 0.32~0.61±(0.8~1.7) Hz, 방위 2.2~2.8±(2.4~3.8)°,
  ⭐**Pd(Pfa=0.008) = 79.7 / 81.1 / 96.4 / 75.0 %**
- eNodeB 거리 9.6·10.8 km, LTE450 = 467.37 MHz, BW ≤ 약 5 MHz
- ⭐**LTE 하향의 기준요소(RE)만 써서 모호함수를 안정화** — 우리 CRS 모드와 같은 선택이다

⛔ **분류는 전혀 없다.** 표적 1기종, 궤적 2개. LTE450 은 유럽 한정 대역이라 우리 1.8/3.5/5.2 GHz 축과
주파수가 안 겹친다.

---

## 2. Q2 — OFDM 파형으로 마이크로도플러

### 2-1. ⭐먼저 스코핑을 바로잡는다 — **방송 조명원 대부분이 이미 OFDM 이다**

이번 조사에서 두 각도가 서로 다르게 스코핑했고, 합치면 답이 달라진다. 정리한다.

| 조명원 | 파형 | Q2 대상인가 |
|---|---|---|
| DVB-T / DVB-T2 | **COFDM** | **예** |
| DAB / DAB+ | **COFDM** | **예** |
| DTMB | **TDS-OFDM**(다중반송파 모드) ⚠단일반송파 모드도 존재 | **예**(모드 확인 필요) |
| LTE · 5G NR 하향 | **CP-OFDM** | **예** |
| WiFi 802.11a/g/n/ac/ax | **OFDM** | **예** |
| **DVB-S / DVB-S2** | **단일반송파 QPSK/APSK** | ⛔**아니오** |
| **GNSS(GPS L1 C/A)** | **DSSS BPSK** | ⛔**아니오** |
| FM · GSM · UMTS | 아날로그 / GMSK / WCDMA | ⛔아니오 |

⇒ **Ummenhofer(DVB-S)와 Clemente(GNSS)는 Q2 의 답이 아니다.** 반대로 **Vorobev(DVB-T2) ·
Jarabo-Amores(DVB-T) · Wang(DTMB) 은 Q1 이자 Q2 다.**

### 2-2. 표 — OFDM 마이크로도플러

| # | 논문 | 파형·조명원 | 기하 | 실측/시뮬 | 마이크로도플러 | 게재처 | 연도 | 읽음 |
|---|---|---|---|---|---|---|---|---|
| 1 | **Wei 외**, *UAV's Rotor Micro-Doppler Feature Extraction Using ISAC Signal* | 5G NR PDSCH 전량(자체 프레임 DDDSU) | ⛔**모노스태틱** ISAC BS | **실측**(닝보 도심, DJI M300 RTK) | ⭐**추출 성공** | **IEEE TWC 24(12):10166–10182** | 2025 | **`[원문]`** |
| 2 | **Costa 외 (GeMiC 판)**, *Bistatic Micro-Doppler Analysis of a VTOL Drone in ICAS* | «OFDM-like»(Newman seq.) 7 GHz/2.4 GHz | ⭐**바이스태틱** | **실측**(BiRa 무향실) | ⭐**추출 + 비행모드 판별** | GeMiC 2025(학회) · arXiv:2502.08454 | 2025 | **`[원문]`** |
| 3 | Costa 외 (저널 확장판) | 같음 | 바이스태틱 | 실측 | 다중 프로펠러 모델링 | IEEE J-STEAP 1:208–222 | 2025 | **`[원문]`**(기존 기록) |
| 4 | Costa 외 (RadarConf24 판) | 같음 | 바이스태틱 | 실측 | 단일 프로펠러 | IEEE RadarConf24 | 2024 | **`[원문]`**(기존 기록) |
| 5 | **Luo 외 (AirGuard)** | OFDM ISAC 26 GHz | 준-모노스태틱 | ⛔**시뮬만** | ⭐cmD + HRRP → CNN | **IEEE JSAC**(채택) · arXiv:2603.13112 | 2026 | **`[원문]`** |
| 6 | Ma 외, *Performance Evaluation of Micro-Doppler Based UAV Identification Using Different 5G Frame Structures* | 5G NR TDD 프레임 | (미상) | 시뮬 | 로터 파라미터 MSE | MICCIS(학회), pp.173–179 | 2024 | **`[초록]`** |
| 7 | Xue 외, *DC-Former Network Empowered UAV and Bird Recognition…* | 5G NR | (미상) | «실제 에코 수집» 주장 | ⭐STFT → DC-Former | ICCCS(학회), pp.927–932 | 2025 | **`[2차]`** |
| 8 | Vorobev 외 (위 Q1 #1) | **DVB-T2** | 바이스태틱 | **실측** | ⭐**로터 회전수로 분류** | SPSympo(학회) | 2019 | **`[초록]`** |
| 9 | Wang 외 (위 Q1 #7) | **DTMB** | 바이스태틱 | **실측** | ⭐SCR 개선 후 **로터 mD 관측** | ICVISP(학회) | 2025 | **`[초록]`** |
| 10 | Chen 외, *Rotating Target Detection Using Commercial 5G Signal* | **5G CSI-RS(주기 20 ms)** | 바이스태틱 | **실측**(회전 시험대) | ⛔**접힘 — 오차 100%** | Applied Sciences 14(10):4282 | 2024 | **`[원문]`** |
| 11 | Mercier 외, *Comparison of Correlation-Based OFDM Radar Receivers* | OFDM 일반 | 패시브+모노 통합 | 시뮬 | ⛔없음(**pedestal 이론**) | **IEEE TAES 56(6):4796–4813** | 2020 | **`[원문]`** |
| 12 | Falcone 외, *Doppler Frequency Sidelobes Level Control for WiFi-Based PBR* | **WiFi** | 바이스태틱 | 실측 | ⛔없음(**CSMA 도플러 모호**) | IEEE RadarCon(학회) | 2011 | **`[원문]`** |
| 13 | Falcone 외, *Experimental Results for OFDM WiFi-Based Passive Bistatic Radar* | **WiFi** | 바이스태틱 | 실측 | ⛔없음(**AF PSLR 13 dB**) | IEEE Radar Conf.(학회) | 2010 | **`[원문]`** |
| 14 | Wypich & Zielinski (위 Q1 #11) | 5G NR 전 성분 | 바이스태틱 | 실측(⚠SDR 에뮬) | ⛔**전문에 micro-Doppler 0회** | Sensors 26(4):1317 | 2026 | **`[원문]`** |
| 15 | Reniers 외, *Joint Pilot and Unknown Data-based Localization for OFDM Opportunistic Radar* | OFDM 기회형 | 패시브 | 시뮬 | ⛔측위만 | VTC2026-Spring(학회) · arXiv:2601.15785 | 2026 | **`[원문]`** |
| 16 | Bai 외, *MIMO OFDM-Enabled ISAC for Low-Altitude Non-Cooperative UAV Surveillance: A Survey* | (서베이) | — | — | §III-C 가 mD+학습 총람 | ⚠**미게재 프리프린트** arXiv:2604.02680 | 2026 | **`[원문]`** |

**대조군(OFDM 아님, 비교용으로만)**
- Vovchuk 외, *Drone Carry-on Weight and Wind Flow Assessment via Micro-Doppler* — **CW**, 무향실+풍동.
  ⭐**바람이 기체를 기울이면 앞뒤 로터 회전수가 갈린다**는 것을 통제실험으로 못박았다(arXiv:2510.22846) `[원문]`
  ⇒ 우리 로터 산포 실측을 독립 지지한다.
- μDopplerTag(arXiv:2601.08042) — **CW**, ⛔**협력 표적**(블레이드에 공진 스티커) `[원문]`

### 2-3. ⭐«CW 에서 OFDM 으로 가면 무엇이 달라지나»

우리는 지금 CW(PRF 35 kHz) 기반 덱을 갖고 있다. OFDM 으로 옮기면 **다섯 가지가 새로 생긴다.**
논문들이 각각을 어떻게 다뤘는지 정리한다.

#### (가) ⭐**슬로타임 표본율이 파형이 아니라 «프레임 구조» 로 정해진다** — 가장 큰 변화

CW 는 PRF 를 우리가 정한다. OFDM 은 **심볼이 곧 표본**이라, 슬로타임 격자가 규격이 정한 심볼 배치에
묶인다. Wei 외(TWC 2025)가 이것을 **프레임 설계 문제로 바꾼 유일한 편**이다.

> **md-testbed §IV-A (p.10174) 축자:** *"the pulse repetition frequency (PRF) must be at least twice the
> maximum micro-Doppler frequency, i.e., PRF ≥ 2 f_mD^max … we obtain f_mD = 2934 Hz, which requires a
> PRF of at least 5868 Hz"*

⚠ **[우리 유도 — 논문이 그렇게 적은 것이 아니다]** 이 유도에 **계수 2 가 빠져 있다.**
`f_mD^max = 2π f_r L / λ` 는 **편도(one-way)** 식이다. 모노스태틱 왕복이면 2배다.

```
v_tip = 2π · f_r · L = 2π · 80 · 0.5          = 251.3 m/s
λ     = c / 3.5 GHz                            = 0.0857 m
편도  f = v_tip/λ                              = 2932 Hz   ← 논문의 2934
왕복  f = 2·v_tip/λ                            = 5864 Hz
∴ ±5864 Hz 를 접히지 않게 담으려면  PRF ≥ 11.7 kHz   (논문은 5868 Hz, 2배 느슨)
```

⭐**논문의 결론 자체는 살아남는다** — 그들이 제안한 DDDSU 프레임의 실효 PRF 는
`M/CPI = 1680 / 0.1 s = 16.8 kHz` 이고, `1680 = 200 슬롯 × (3/5) × 14 심볼` 로 정확히 맞는다.
11.7 kHz 를 넘는다.

**우리 조명원을 같은 자로 재면:**

| 신호 | 슬로타임 반복률 | 11.7 kHz 기준 |
|---|---|---|
| Wei DDDSU (PDSCH 전량) | **16.8 kHz** | 통과 |
| Wei DMRS만 | 10 kHz (PRI 1e-4 s), ⭐**단 UL 슬롯 때문에 실효 밀도 부족**(원문 자인) | 아슬 |
| **5G SSB(주기 20 ms)** | **50 Hz** | ⛔**234배 모자람** |
| **5G CSI-RS(40 슬롯 = 20 ms)** | **50 Hz** | ⛔접힘 — **Chen 2024 가 실측으로 확인**(오차 100%) |

> **Chen 외, Appl. Sci. 14(10):4282, p.16 축자:** *"the reason for the error of 100% is that the Doppler
> frequency exceeds the measurement range, resulting in Doppler blur."*

⇒ ⭐**우리 «5G 이중고» 서사(상시 신호의 반복률이 마이크로도플러를 원리적으로 막는다)가
여기서 처음으로 «이론 하한 + 실측 확인» 두 다리를 다 갖는다.**

#### (나) **데이터 심볼이 만드는 랜덤 사이드로브(pedestal)** — CW 에는 없던 열화항

**Mercier 외, IEEE TAES 56(6):4796–4813, 2020 `[원문]`** 이 이것을 정면으로 다룬다.
OFDM 은 심볼마다 실려 있는 **데이터가 매번 다르므로**, 레인지-도플러 맵 배경에 **랜덤한 대(pedestal)**
가 깔린다. 이 논문은 그 2차 모멘트를 **CP 를 넘는 지연까지 닫힌형으로 유도**하고, 상관 수신기 8종
(MF · PMF · PMF-CP · PMF-CC 와 각각의 reciprocal 판)을 하나의 표기로 통합해 비교한다.

**Fig.5(p.4805, RadCom 시나리오: fc 5 GHz, B 10 MHz, 표적 RCS 100 m², R0 2325 m, v 35.8 m/s):**

| 필터 | 배경 평균전력 | 표적 피크 |
|---|---|---|
| MF | −99.83 dBW | −84.98 dBW |
| PMF | −99.35 | −86.66 |
| PMF-CP | −99.14 | −86.43 |
| **PMF-CC(원형상관)** | **−106.01** | −86.23 |

⇒ 원형상관이 **pedestal 을 약 6.2 dB 낮추고 표적 피크는 1.25 dB 만 잃는다.**

⭐**우리에게 직접 닿는 곳**: 이 항은 **레인지-도플러 배경 통계를 바꾼다.** 우리 report10 CFAR 교정의
**«배경은 균질 잡음» 가정을 직접 건드린다.** 그리고 §I 이 **«패시브에서는 기준신호가 미지라 더 심하다»**
고 명시한다. **우리 prior_work/·docs/ 어디에도 이 논문이 없다.**

#### (다) **불규칙 PRT** — WiFi 에만 생기는 별도 벌점

**Falcone 외, IEEE RadarCon 2011 `[원문]`**: WiFi 는 CSMA 때문에 **펄스 길이와 간격이 둘 다 불규칙**하다.
그 결과 도플러 사이드로브가 예측 불가능해지고, **Hamming 같은 표준 테이퍼가 무력해진다.**

- 공칭 PRT 2 ms → 무모호 도플러 500 Hz → λ≈12 cm 에서 바이스태틱 약 60 m/s
- 실데이터 모호함수는 이론적 디지털 sinc 형태를 벗어나 **6 dB/옥타브로 감쇠하지 않는다**
- **±16 / ±20 / ±25 m/s 에 강한 도플러 모호 피크**가 선다
- Hamming 후 PSR 이 **이론치 43 dB 에 한참 못 미친다**; 제안 가중망으로 PSR 30 dB 이상(약 10 dB 개선)

⇒ 우리 3밴드 비교는 지금 **듀티비와 대역폭으로만** WiFi 를 벌점한다. **이 축이 빠져 있다.**
도플러 축을 정밀하게 봐야 하는 마이크로도플러일수록 이 벌점이 결정적이고,
**LTE·5G 는 주기적이라 이 문제가 훨씬 작다** — 우리 서사에 유리하게 붙는다.

#### (라) **모호함수 자체가 깨끗하지 않다**

**Falcone 외, IEEE Radar Conf. 2010 `[원문]`**: 802.11 OFDM AP 조명원의 **가공 전 AF PSLR 이 13 dB 뿐**이다.
(Δf = 20 MHz/64 = 0.3125 MHz, T_FFT = 3.2 µs, 실제 점유 B = 16.56 MHz → ΔR = c/2B = 9.05 m)
⇒ «OFDM 은 상관만 하면 되는 깨끗한 파형» 이라는 통념을 실측으로 깬다.

#### (마) **어떤 성분을 쓰느냐가 검출률을 3배 이상 바꾼다**

**Wypich & Zielinski, Sensors 26(4):1317, 2026 `[원문]`** 이 5G NR 하향 성분을 조합별로 켜고 끈다.

| 구성 | 무엇을 쓰나 | **POD** |
|---|---|---|
| P-Radar | CSI-RS만 | **24%** |
| SCP-Radar | SSB+PDCCH+CSI-RS | **32%** |
| SCD-Radar | 사용자데이터 포함(CSI-RS 제외) | **78%** |
| SCPD-Radar | 전부 + 사용자데이터 | **77%** |

- PNFR 편차(지니-에이디드 대비): 파일럿계 약 6.5 dB(4.5–7.5) → 데이터 포함 약 2.5 dB
- BER < 1e−2 면 0.5 dB, BER > 1e−1 면 4.5–5 dB (Fig.13, Spearman ρ=0.5412, p=5.05e−12)
- **PDSCH RE 위치를 저BER 20% / 고BER 40% 만 알아도 POD 96%**(Fig.14)
- 4-QAM vs 256-QAM 약 4.5 dB 차(Fig.16)
- 장비: NI USRP 2953R(X310)+UBX-160, fc **5.8 GHz**, 샘플레이트 33.33 MHz, SCS 30 kHz, FFT 2048,
  사용 부반송파 1596. Rx–표적 110 m, Tx–표적 180 m. ECA+ 후 CA-CFAR Pfa 1e−3.

⛔ **두 개의 큰 조건절이 있다.** ① **전문에 micro-Doppler 0회, drone/UAV 0회** — 표적은 고속도로 차량이다.
② ⭐**기지국이 상용 gNB 가 아니다**: *"§4.1 The base station was emulated using an SDR positioned
approximately 20 m above the ground"*, 게다가 **5.8 GHz 비면허 대역**이다.
LaSen 이 자기 USRP 로 풀밴드 NR 을 쏜 것과 구조가 같다.

⭐**Demissie(LTE450, 기준요소만 써서 모호함수를 안정화)와 Wypich(데이터까지 써야 POD 가 오른다)를
나란히 두면 우리 9모드 점유 비교의 양끝이 생긴다.**

### 2-4. ⛔이 각도에서 **못 찾은 것**을 정확히 적는다

**«5G NR 의 상시 기준신호(SSB · CRS · PRS · SRS)만으로 마이크로도플러를 본 논문» 은
이번 조사 범위에서 찾지 못했다.** 찾은 5G 마이크로도플러 실측은 전부

- **PDSCH 전량 사용 + 모노스태틱 자체 테스트베드**(Wei, BUPT), 또는
- **자체 채널사운더 OFDM-like**(Costa, TU Ilmenau, B=2.4 GHz — 어느 셀룰러 밴드보다도 넓다)

였다. 이는 우리 PRF 논지와 방향이 같지만, **근거는 «이 범위에서 못 찾았다» 까지다.**

---

## 3. Q3 — 딥러닝 프레임워크

### 3-1. ⭐표 — 우리가 따라 만들 수 있는 수준으로

| 논문 | 태스크(클래스) | 입력 | 백본 · 파라미터 | 데이터 | 분할·누수방지 | 정확도 | 읽음 |
|---|---|---|---|---|---|---|---|
| **AirGuard** (IEEE JSAC, arXiv:2603.13112) | UAV vs 새 **2클래스**, OFDM ISAC 26 GHz | ⭐**cmD 스펙트럼 + HRRP 두 장**, 각 3@256×256 | **이중분기 CNN**, 분기당 conv3×3×3 + maxpool×3 → 32@32×32 → adaptive avgpool → FC32; concat 64 → FC×2. **0.15 M** | 237,600 장 = 운동모델 3600 × SNR 11단 × 반복 6 | ⛔**규칙 없음** — 3600 모델이 66번씩 재등장하니 무작위 분할은 근접중복 누수 | **99.37%**(cmD+HRRP) / 97.75(cmD) / 95.34(HRRP) | **`[원문]`** |
| **White 외** (IEEE TRS **vol.2, pp.167–179, 2024**) | 새 vs 드론 2클래스, L밴드 응시레이다 | RGB 스펙트로그램, **20 timestep = 5.6 s**, 15 Hz 고역통과로 중앙 18 도플러빈 제거 | **AlexNet**(ImageNet 사전학습), ⭐**conv 동결·FC 만 학습** | 실측 14회 캠페인, 학습 7256장(새 3625 / Inspire 1444 / Matrice 1058 / Mini 1129) | ⭐**한 비행이 train/test/val 에 걸치지 않게 분할** | **실측 89.7±0.5 / 합성 86.6±0.5** | **`[원문]`** |
| **Gerard 외** (EUSIPCO 2020, pp.1561–1565) | 드론 **5클래스**(우연선 20%), S밴드 능동 펄스 | ⭐**표현 5종 비교**: x(t) · WSP · CP · SG · CVD | ⭐**GoogLeNet**(우리 기록의 «AlexNet» 은 오류) | 학습 36,730 / 시험 4,670 청크, 누적 3.5시간 | ⭐⭐**날짜 분리**(§IV-B) — 안 하면 98~100% 로 부풀어 오른다 | 청정 WSP **98.1** / 잡음 **92.7** / 짧은관측 93.7 | **`[원문]`** |
| **Kearney & Gurbuz** (IEEE TAES 62:9875–9891) | UAV **5기체**, 79 GHz FMCW | 스펙트로그램 + ⭐**시맨틱 분할 마스크** | U-Net(CAD 시뮬만 학습) → GAN 판별기 / 분류기 앞단 | 실측 79건 → 6 s 333샘플(High 107 / Low 226) | High/Low **SINR 계층**으로 분리 | SS-CAE Real→Low **50.0 → 71.2%**(+21.2pp) | **`[원문]`** |
| **Rojhani 외** (IEEE TMTT 71(5):2222–2236) | 로터수 2클래스, 77 GHz FMCW | ⛔**레인지 프로파일 400점**(스펙트로그램 아님) | CNN, Adam lr 1e-3 | 합성 32,000 × 400, 실측 시험 **136장** | ⛔σ_P 를 **시험셋으로 튜닝**(따라하면 안 됨) | **78.68%**(모델기반) vs **66.18%**(관행증강) | **`[원문]`** |
| **A-SPC** (KAIST, arXiv:2009.14422) | 드론 3종+잡음2 = 5클래스, Ku FMCW | mD 이미지 128×128×3 | ⭐**경량 CNN — conv 3층 + FC 1층, 0.217 M** | 3,500장(클래스당 700) | ⭐**독립 추출한 별도 시험셋 1,750장** | ⭐**87.14 → 97.14%**(망 고정, **전처리만 교체**) | **`[원문]`** |
| **Czerkawski 외** (IRS 2022) | ⚠**사람 행동 6클래스**(드론 아님) | 2채널 실수+허수 STFT 128×128 / CVD | 커스텀 conv(9×9) 2종 | 1,752 샘플 | 50/25/25 고정 | 표준 0.86 → **시간이동 0.76** → 시간증강 0.91/0.84; **CVD 로 바꾸면 적대 0.00→0.58** | **`[원문]`** |
| **Glüge 외** (IEEE J-RFID vol.8) | ⚠**제어링크 RF 7클래스**(mD 아님) | IQ → 2×1024×1024 | VGG11~19_BN, **9.36 → 20.17 M** | Kaggle, SNR −20~+30 dB | 층화 5-fold CV | **0.932 → 0.939**(파라미터 2.2배에 +0.7pp) | **`[원문]`** |
| **Czuba** (ICCI*CC 2023) | UAV 1 + 헬기 2 = 3클래스 | RGB 스펙트로그램 **3가지 길이** 102.4/204.8/307.2 ms | ⭐**ViT-S-M 10.6 M**, 인코더 **5층이 최적** | 13,614장 | ⚠무작위 80/10/10, 80% 중첩 STFT → 누수 의심 | 97.76%(상한으로 읽을 것) | **`[원문]`** |
| **ELCVIA 24(2)** | DIAT-µSAT 6 / RRN 4 / RAD-DAR 3 | 11×61×1, 224×224×3 | 커스텀 CNN + 채널어텐션(SE/ECA/GCT) | 공개 3종 | ⛔**분할 규약 미기재** | DIAT **97.14** vs 사전학습 VGG19 **97** (+0.14pp) | **`[원문]`** |
| **Mustafa 외** (arXiv:2604.12567) | 드론/새/반사체 3클래스 | 스펙트로그램에서 **수제 특징 5개** | ⛔**딥러닝 없음** — SVM · RF | ⚠**130건뿐** | 5-fold CV + 20% 홀드아웃 | 청정 0.916, **−10 dB 에서 RF F1 0.831** | **`[원문]`** |
| Kim 외 (IEEE GRSL 14(1):38–42) | 드론, Ku FMCW | ⭐**MDS + CVD 병합 이미지** | GoogLeNet | — | — | **89.3 → 94.7%**(CVD 병합) | **`[2차]`** |

### 3-2. ⭐⭐무엇이 실제로 정확도를 움직이나 — 통제비교 안에서만 센 순위

| 순위 | 무엇 | 효과 | 출처(통제조건) |
|---|---|---|---|
| **1** | **입력 전처리 품질** | ⭐**+10.0 pp** | A-SPC, **망을 고정**하고 추출만 교체 |
| **2** | **입력 표현 선택** | +5.4 pp(MDS→MDS+CVD, `[2차]`) · +4.0 pp(HRRP→cmD+HRRP) · 잡음하 WSP 가 차순위보다 **10 pp 이상** | Kim 2017 · AirGuard Fig.10b · Gerard Table II |
| **3** | **시뮬 로터 모델 충실도** | +2.2 pp 정확도, ⭐**+5.8 pp 드론 재현율** | White Table V (Fixed-Speeds → Sub-CPI) |
| 4 | 채널 어텐션 | **+0.14 pp** | ELCVIA Table 6 (사전학습 VGG19 대비) |
| 5 | 백본 용량 | **+0.7 pp**(파라미터 2.2배) | Glüge Table VI |

⇒ ⭐**네 그룹이 독립적으로 같은 순서에 닿는다: 무엇을 먹이느냐 ≫ 어떤 망이냐.**
이것은 우리 **[[upstream-first-ordering]]** 방침(로터 모델을 먼저 고치고 나서 학습한다)의 외부 근거다.

### 3-3. 파라미터 예산 — 작아도 된다

| 논문 | 파라미터 | 클래스 |
|---|---|---|
| AirGuard | **0.15 M** | 2 |
| ELCVIA UAVDetect1 | **0.162 M** | 3 |
| A-SPC 경량 CNN | **0.217 M** | 5 |
| μDopplerTag | conv 3층 | 43 |
| (대조) VGG11~19 · GoogLeNet · ViT-S-M · AlexNet | 9~61 M | — |

⭐**용량을 통제해서 잰 두 편(Glüge · Czuba)에서 큰 망은 «아무것도 안 하거나»(+0.7pp) «과적합했다»
(12층 ViT 가 13,614 샘플에서 무너짐).** 우리 데이터는 12,096 샘플이다 —
**소형 스크래치 CNN 을 대조군이 아니라 1급 후보로 올려야 한다.**

### 3-4. ⭐⭐분할 규약 — 이 분야의 최대 약점이자 **우리의 최대 카드**

> **Gerard EUSIPCO 2020 §IV-B 축자:** *"We stress that without day separation between the testing and
> training set, the classification accuracy reaches more than 98% in all configurations (even 100% for
> x(t)), much too optimistic. We thus strongly recommend that experiments should be conducted with the
> day separation."*

**누수 방어를 명시한 논문은 셋뿐이다** — White(한 비행이 분할에 안 걸침) · A-SPC(독립 추출 시험셋) ·
Gerard(날짜 분리). μDopplerTag 는 leave-one-recording-out 폴드를 보조로 돌린다.
**AirGuard · ViT 편 · ELCVIA 는 무작위 분할이거나 규약을 안 적는다.**

⇒ 우리 **leave-one-aspect-out 18폴드는 게재된 대부분보다 엄격하다.** 그렇게 말하는 것은 정당한 기여다.
⛔ **그러나 같은 이유로 우리 87.9% 를 그들의 97~99% 옆에 나란히 놓으면 안 된다.**

### 3-5. 사전학습은 정리된 문제가 아니다

| 논문 | 결론 |
|---|---|
| White TRS 2024 | ImageNet AlexNet 동결 + FC 만 학습 → 어려운 도심 2클래스에서 89.7% |
| **White RadarConf24** | ⭐**비지도 오토인코더 사전학습(레이다 데이터만)이 ImageNet 전이를 이긴다 — 단 «1% 미만»** (저자 자인: *"albeit by less than 1%"*). ADB 92.90 vs 92.23, LDB 98.69 vs 98.58 |
| 같은 편 | ⭐**합성으로 사전학습해도 거의 동일**(ADB 92.68 / LDB 98.69). ⛔**단 미세조정까지 합성으로 하면 LDB 98.69 → 93.31로 5 pp 하락** — *"real data is imperative when seeking maximum performance."* |
| Glüge · ELCVIA · μDopplerTag · A-SPC | 전부 스크래치 학습으로 93~99% |

⚠ **White RadarConf24 는 학회 원문을 못 구했다.** 위 수치는 **같은 1저자의 박사학위 논문
(Birmingham ETheses 15101) §8.2.1 Table 8.3/8.4** 에서 대조한 것이다 — 인용할 때 그렇게 적어야 한다.
그리고 **표는 전부 «best» 만 모은 값이다**: 원문이 *"not all CAEs learned adequate features"* 라고 적을
만큼 **CAE 사전학습은 자주 실패한다.**

### 3-6. ⭐«합성으로 훈련해 실측을 맞춘다» 의 실제 성적표

| 논문 | 무엇을 합성했나 | 결과 |
|---|---|---|
| **White TRS 2024** | ⛔**«합성만» 이 아니다** — **큰 드론 2종만** 합성(2502/7256 = **학습셋의 34.5%**, 드론 클래스의 69%). 새와 Mini 는 실측 유지. 게다가 합성 표적을 ⭐**실측 배경 시계열에 더한다**(식 2, Fig.7 3단계) | 89.7 → **86.6** (**−3.1 pp**) |
| **Rojhani TMTT 2023** | 결정론적 물리모델로 32,000장 | 78.68% vs 관행증강 66.18%. ⭐**진짜 결과는 정확도가 아니라 «편향»**: 최소 정밀도 **78.02% vs 15.55%** — 베이스라인은 사실상 붕괴한 분류기(HELI 재현율 15%) |
| **Kearney & Gurbuz TAES 2026** | 저충실도 CAD 포인트클라우드 | ⛔⭐**«저충실도 모델 단독 학습은 잡음 주입 여부와 무관하게 random guessing 을 못 넘었다»**(§V-A) ⇒ 시뮬을 **데이터가 아니라 사전(prior)** 으로 쓰라는 논거 |
| **Costa J-STEAP 2025** | 바이스태틱 OFDM mD 생성기 | 결론 §VI: *"Future work can comprise the use of simulated data using this proposed model to train target classification algorithms…"* ⇒ ⭐**가장 가까운 생성기가 sim2real 고리를 아직 안 닫았다** |
| **Gurbuz 계열**(TAES 2019/2020/2023 · SPIE 2020) | MOCAP·GAN | DivNet: 55 MOCAP → 32,000 합성 → 15층 초기화 → 미세조정 **95%**(실측만으로는 7층이 한계). 합성 2500→30000 이면 84→97% 인데 **15000→30000 은 +1% 뿐**. 교차주파수 미세조정 불일치는 **70% 붕괴** |

### 3-7. 우리가 바로 쓸 수 있는 레시피

**입력** — A1: peak-norm dB STFT 맵. A3(CVD 팔): 근거가 두 갈래로 독립이다 —
정확도(Kim +5.4pp `[2차]`)와 **강인성**(Czerkawski: 적대 0.00→0.58, 시간이동 0.76→0.85, 청정 손실 없음).
⚠ 단 **CVD 는 긴 관측에서만 값을 한다** — Gerard Table III 에서 36 ms 로 줄이면 94.5→79.3(Δ15.2)로
**다른 어떤 표현보다 3배 크게 무너진다.** 그리고 **[[md-stft-only]]** 규칙상 먼저 물어야 한다.

**백본** — 소형 스크래치 CNN(0.15~0.25 M)을 1급 팔로. ResNet18(11 M)은 우리 데이터 규모에서
Czuba 가 과적합한 크기대다.

**학습** — Adam 1e-4, batch 16, 50 epoch, ReduceLROnPlateau(factor 0.1, patience 3~4) [ELCVIA] 또는
Adam 1e-3, batch 32 [μDopplerTag]. ⛔**수평 뒤집기 증강 금지** — 스펙트로그램의 시간축을 뒤집는 것이고
블레이드 플래시 케이던스는 방향성이 있다(ELCVIA 가 이걸 한다 — 따라하면 안 된다).

**증강** — ⭐**출력 파형이 아니라 모델 파라미터 벡터에 섭동을 준다**(Rojhani 식 4 vs 식 2).
파형에 잡음·랜덤변환을 얹으면 클래스와 무관한 특징을 발명한다. 섭동 표준편차에 최적점이 있다(0.1~0.2).

**SNR 평가 규약** — ⭐**청정 데이터로 한 번 학습하고, 가중치를 얼린 채 시험셋에만 잡음을 주입한다**
(μDopplerTag Fig.4b/8). 이러면 «신호가 얼마나 남았나» 와 «망이 잡음에 얼마나 적응했나» 가 분리된다.
우리 현재 계획은 이 둘을 안 나눈다.

**분할** — leave-one-aspect-out 유지 + **날짜/세션 분리**(Gerard) + 근접중복 점검.

---

## 4. ⭐우리 위치 — 이 지형에서 우리는 어디 있나

### 4-1. 좌표

우리가 하려는 것은 세 조건의 **곱**이다.

- **A** = 패시브 **바이스태틱**, **비협력** 표적, **셀룰러 조명원**(LTE/5G, 1.8/3.5/5.2 GHz)
- **B** = **OFDM** 파형에서 **마이크로도플러**
- **C** = **우리가 계산한 σ**(SBR+PO 커널)로 만든 **합성 학습데이터 + 딥러닝 기종 분류**, 그리고 실측 검증

### 4-2. 각 쌍은 **이미 점유돼 있다**

| 조합 | 누가 이미 했나 |
|---|---|
| **A + B** (패시브 셀룰러 OFDM) | Demissie(LTE450, 실측) · LIPASE(LTE, 실측) · Wypich(5G, ⚠SDR 에뮬) · Chen(5G, 실측) · Jopanya(SSB, 시뮬) · Abratkiewicz(SSB, 실측) · Huang(상향 SRS, 시뮬) |
| **B + C** (OFDM mD + 딥러닝) | **AirGuard**(JSAC, 시뮬만) · Xue DC-Former(`[2차]`, 실측 주장) · Wei(TWC, 실측이나 학습 없음) |
| **A + 분류** (패시브 + 분류) | Vorobev(DVB-T2) · Jarabo-Amores(DVB-T) · Cao(DTMB) · Kulpa(IRS 2025) · Ummenhofer(DVB-S) · Clemente(GNSS) |
| **C 의 sim2real 축** | White(TRS) · Rojhani(TMTT) · Kearney & Gurbuz(TAES) · Gurbuz 계열 |

### 4-3. 그래서 쓸 수 있는 문장

> ⭐**«이번 조사 범위(보관함 372편 + arXiv/S2/Crossref/OpenAlex/웹)에서, A·B·C 를 함께 한 논문은
> 찾지 못했다.»**
>
> 더 좁혀 쓸 수 있는 것:
> - «**셀룰러 조명원 패시브 바이스태틱에서 드론 기종 분류까지 간 게재 논문**을 이번 범위에서
>   찾지 못했다. 분류까지 간 패시브 선행은 전부 방송·위성 조명원이었다.»
> - «**패시브 에코 + 딥러닝**의 게재 사례를 이번 범위에서 찾지 못했다.»
> - «**표적 산란을 스스로 계산하고 그 위에 학습 분류기를 세운** 패시브 드론 논문을 찾지 못했다.»

⛔ **«최초» 라고 쓰지 않는다.** 위 세 문장은 전부 **검색 범위에 대한 진술**이지 문헌 전체에 대한 진술이
아니다. 특히 §6 에 적은 대로 **중문 저널과 유료 IEEE 학회 6편을 못 열었다.**

### 4-4. ⭐우리를 정면으로 겨누는 반증 셋 — 먼저 답을 준비해야 한다

| # | 반증 | 어디 | 우리가 쓸 수 있는 대답 | 그 대답에 필요한 것 |
|---|---|---|---|---|
| **R1** | ⭐**«라디오/TV 대역에서 드론 RCS 는 입사·산란각에 따라 거의 안 변해 intra-class(드론끼리) 구분이 어렵다»** | Cao 외, Appl. Sci. 15(18):9957, **§4** `[원문]` | 우리 대역은 **1.8~5.2 GHz 로 훨씬 높고**, 우리 특징은 RCS 크기가 아니라 **마이크로도플러**다 | ⚠**대역별로 이 주장이 무너지는 지점을 수치로 보여야 한다.** 아직 없다 |
| **R2** | ⭐**미학습 기체에서 붕괴** — 4로터로만 학습하면 Ehang eVTOL 을 **4.49%** 만 맞고 95.51% 를 새로 오분류. Six-Rotor 66.78% | AirGuard **Fig.12** `[원문]` | 우리는 **폐집합 6클래스**를 주장하고, open-set 은 별도 게이트(G6)로 분리 | 우리 G6 를 **실제로 돌려서** 숫자를 내야 한다. 이건 외부 근거가 이미 있으니 미루면 안 된다 |
| **R3** | ⭐⭐**«저충실도 시뮬 단독 학습은 random guessing 을 못 넘었다»** | Kearney & Gurbuz, TAES 62 **§V-A** `[원문]` | 우리 시뮬은 저충실도가 아니다(SBR 가림 + 재질가중 PO + 실측 로터 산포). 그리고 그들의 처방(**시뮬을 데이터가 아니라 분류기 앞단 사전으로**)은 우리도 쓸 수 있다 | 우리 σ 충실도를 **분류 성능으로 환산한 증거**. White 의 «−3.1 pp» 가 우리가 넘어야 할 선이다 |

**R2 의 무게를 낮게 보면 안 된다** — AirGuard 는 **시뮬 안에서 SNR 만 바꾼 동일 파이프라인**인데도
붕괴했다. 도메인 시프트가 아니라 **클래스 시프트**만으로 그렇다.

### 4-5. 우리에게 유리한 지형도 정확히 적는다

1. **분할 규약** — 우리 leave-one-aspect-out 18폴드는 §3-4 대부분보다 엄격하다.
2. **σ 를 스스로 계산한다** — §4-2 의 어느 칸도 이걸 하지 않는다. AirGuard 는 메시를 등방 점산란으로
   환원하고(재질·편파·차폐 없음), Wei 는 σ_body 를 **출처 없는 상수 0.01 m²** 로 둔다.
3. **바이스태틱 기하** — B+C 칸(AirGuard · Wei)은 전부 모노스태틱/준-모노스태틱이다.
   바이스태틱 OFDM mD 실측은 Costa 팀뿐이고, **그들은 학습을 세 판에 걸쳐 «후속과제» 로 비워 뒀다.**
4. **상시 신호의 원리적 한계를 정량화한 자리** — §2-3(가)의 11.7 kHz vs 50 Hz 는
   우리 «5G 이중고» 서사를 이론+실측 두 다리로 세운다.

---

## 5. 기존 기록의 정정 — 어느 파일 어느 줄

### 5-1. ⛔즉시 고쳐야 하는 것 (사실 오류)

| # | 파일:줄 | 지금 뭐라고 적혀 있나 | 판정 | 고칠 내용 |
|---|---|---|---|---|
| **C1** | `docs/PLAN_DEEP_LEARNING.md:53` | DOI `10.1109/TRS.2023.3323484` | ⛔**존재하지 않는 DOI**(Crossref 404) | `10.1109/TRS.2023.3326317` |
| **C2** | `docs/PLAN_DEEP_LEARNING.md:52` | «IEEE Transactions on Radar Systems, **2023**» | ⛔틀림 | ⭐**vol. 2, pp. 167–179, 2024**(early access 2023-10-20). `prior_work/rotor_randomness_survey.md:129`·`:454` 가 이미 맞게 적어 놨다 — **우리 파일 셋이 서로 달랐다** |
| **C3** | `docs/PLAN_DEEP_LEARNING.md` §1-1 | «**합성 스펙트로그램으로만** CNN 을 훈련» | ⛔**과장** | **큰 드론 2종만 합성**(학습셋 34.5%, 드론 클래스 69%). 새와 Mini 2 는 실측 유지. 게다가 합성 표적을 **실측 배경 시계열에 더한다** → «반합성» |
| **C4** | `docs/PLAN_DEEP_LEARNING.md:~88` | Gerard 편을 «같은 **AlexNet** 에 넣어 비교» | ⛔틀림 | ⭐**GoogLeNet**. 전문 25,879자에 «AlexNet» 0회, «GoogLeNet» 1회(§IV-B) |
| **C5** | `docs/PLAN_DEEP_LEARNING.md:81` | 표 행 «켑스트로그램 · 가중 스펙트럼 \| **스펙트로그램의 변형**» | ⛔틀림 | **WSP 는 dwell 전체에 창 하나 씌운 FFT 로 시간분해능이 없다.** WSP·CP 는 **x(t)에서** 나오지 SG 에서 나오지 않는다. **SG 에서 파생되는 것은 CVD 뿐.** 그리고 논문은 «켑스트럼(CP)» 이라 쓰지 «켑스트로그램» 이라 쓰지 않는다 |
| **C6** | `docs/PLAN_DEEP_LEARNING.md:~86` | «hal-03602645» (게재처 없음) | 불완전 | **EUSIPCO 2020, Amsterdam, pp.1561–1565**, ISBN 978-9-0827-9705-3, DOI `10.23919/Eusipco47968.2020.9287525`. 원문 사본: `prior_work/pdfs/eusipco2020_1561__gerard_microdoppler-representation-drone-dl.pdf` |
| **C7** | `prior_work/sionna_sensing_survey.md:230` | CellSense «**MILCOM 2026**» | ⛔게재처 오류 | arXiv 코멘트 = *"Submitted to MILCOM 2026"* → **arXiv 프리프린트(MILCOM 2026 투고)** |
| **C8** | `prior_work/sionna_sensing_survey.md:340` | CellSense = «**Sionna PHY 링크레벨**+USRP» | ⛔**같은 파일 안에서 모순**(l.29·l.232 는 이미 RT 로 정정됨) | «**Sionna RT(CIR) + 자체 파이썬 OFDM 트랜시버 + USRP**». 원문 §V-A 가 그렇게 적는다 |
| **C9** | `prior_work/sionna_sensing_survey.md:146` | R1 «IEEE ICC Workshops 2026» | 낡음 | «**확장 프리프린트**(일부만 ICC-WS 2026 채택)». 원문 p.1 각주. 그리고 이 편은 **attention-MIL + Transformer 딥러닝 파이프라인인데 항목에 구조·수치가 한 줄도 없다** |
| **C10** | `prior_work/sionna_sensing_survey.md:306` | Zhang M350 «무향실 **10–36 GHz**» | 부정확 | **10/15/20/28/36 GHz 이산 5점**(각 3 GHz 대역), 연속 스윕 아님, **sub-6 는 한 점도 없다**. Table V 의 `A_UAV = −9.26 + 0.31 f [dBsm]` 를 우리 밴드로 외삽하면 **적합범위 밖**. ⚠`docs/INJECTION_PRECEDENT.md` P2 는 같은 논문을 **IEEE JSAC 44:702–716, 2026** 게재로 적어 두 파일이 갈린다 — 게재판을 병기 |
| **C11** | `docs/DRONE_ISAC_PRIOR_READING.md:38` | md-testbed «**PRI 33.3 µs**» | 부정확 | 원문 **Table I 은 OFDM 심볼 36.6 µs**. 33.33 µs 는 30 kHz SCS **유효심볼(CP 제외)**. ⭐**슬로타임 축을 33.3 µs 로 만들면 심볼마다 CP 만큼 어긋난다** |

### 5-2. ⚠조건절을 붙여야 하는 것 (참이지만 좁혀야 함)

| # | 파일:줄 | 지금 문장 | 붙일 조건절 |
|---|---|---|---|
| **N1** | 여러 리포트·덱 | «패시브 선행은 대부분 **검출에서 멈춘다**» | ⭐**«셀룰러·WiFi 조명원에 한해»**. 방송·위성까지 넣으면 거짓이다(§1-2 의 ⭐행 6개). LIPASE Table I 에 C 열이 없다는 근거는 **셀룰러 갈래 한정**으로는 여전히 유효 |
| **N2** | `docs/REFERENCE_LIBRARY.md:1911` | «⛔ *passive 는 곧 상시 기준신호만 쓴다* — **Wypich 가 반증한다**» | ⭐**«자기 송신 파형을 아는 SDR 에뮬레이션 환경에서»**. §4.1 축자: *"The base station was **emulated using an SDR** positioned approximately 20 m above the ground"*, 게다가 **5.8 GHz 비면허**. LaSen 구조와 같다 |
| **N3** | `docs/PRIOR_WORK_COMPARISON.md:669` | «**명목-vs-경험 Pfa 교정 곡선을 잰 선행이 없다**» | ⛔**반증됨** — Gurung arXiv:2608.05826 **Appendix A-1** 이 6.2e5 셀 시험으로 설계값별 실현 PFA 를 직접 읽는다(경험 0.98 @명목 1e-4 → α_OS 정정 4.9e-4 → 1.2 dB 오프셋 후 8.9e-5). ⇒ «**파형별·창별로 스윕한** 선행이 없다» 로 좁히고 Gurung 을 부분 선행으로 인용. 우리 우위는 **표본수(500,000 맵)·파형 3종·창 2종** |
| **N4** | `docs/TEAMMEETING_PRIORWORK_AUDIT.md:95` | «**SCR 을 보고 지표로 쓴 논문은 21편 중 0편**» | ⭐«**우리 21편 코퍼스 안에서** 0편». 코퍼스를 넓히면 Wang 외(ICVISP 2025, DTMB 패시브)가 SCR 개선을 헤드라인으로 쓴다. ⚠**단 이 편은 `[초록]` 이라 이 정정 자체가 잠정** |
| **N5** | `prior_work/sionna_sensing_survey.md:344` | «패시브 바이스태틱+Sionna+검출률도 미점유가 아니다 — CellSense» | 참이나 **과잉 양보**. «단 **표적은 사람 대용 직육면체(1.8×0.5×0.25 m)이고 UAV 가 아니다**» 를 붙인다(`REFERENCE_LIBRARY` 는 이미 정확히 적는다) |
| **N6** | `prior_work/rotor_randomness_survey.md` §2-3 | 드론 재현율 «중앙값» 열에 Fixed-Speeds **74.5%** | **평균과 중앙값이 섞였다.** 88.4·78.8 은 §V-C 본문의 **중앙값**, 74.5 는 논문이 **평균**이라 부른 값, **Table V 의 평균은 74.3±2.0**. Per-CPI·Single-Motor 정확도 칸이 비어 있다 → **85.9 / 86.1** |

### 5-3. ⛔인용할 때 함정 (파일 수정이 아니라 «다시는 이렇게 쓰지 말 것»)

| # | 함정 | 정확한 사실 |
|---|---|---|
| **T1** | **Ummenhofer 초록 인용문** «*extracted micro-Doppler signatures from UAVs to support potential classification capabilities*» | ⛔**초록에 없는 문장이다**(패러프레이즈). 실제 문장: *"In addition, micro-Doppler signatures for drones have been extracted, **which might give information for subsequent UAV classification**."* 따옴표 안에 넣지 말 것 |
| **T2** | COMST 위치표기 «§V-D7 · p.25 · [247]» | **arXiv:2402.05909v2 프리프린트**의 것. **게재판은 제목이 UAV→AAV**, DOI `10.1109/COMST.2025.3554613`, vol.28, pp.3272–3310 — **25쪽이 존재하지 않는다** |
| **T3** | 위성 패시브 수치 «최대도플러 88 Hz · SNR 14 dB @100 m» 를 Ummenhofer 것으로 | ⛔**Abdullah(Remote Sens. 2020, 서베이 [226])의 것**이다. 서베이는 [247]에 **수치를 0개** 준다 |
| **T4** | ⭐**서베이 요약을 믿고 쓰기** | **실증이 나왔다**: COMST 는 위성 갈래([226] Abdullah)를 분류와 묶어 서술하는데, **원문을 열어보니 본문에 «classification» 이 0회**이고 검출까지다. **우리 prior_work 의 2차 출처로 채운 칸을 다시 훑어야 한다** |
| **T5** | Vorobev **«660 MHz»** | ⭐**666 MHz(DVB-T2 UHF 45채널)의 오기일 가능성이 높다.** 660 MHz 는 유럽 8 MHz UHF 래스터에 없는 값(ch44=658, ch45=666). 같은 그룹의 OA 논문(J. Russian Univ. Radioelectronics, No.6 2018)이 *"the 45th channel of the DVB-T2 standard (666 MHz)"* 와 *"49.2 km"* 를 함께 적는다. **49.2 km 는 이 팀의 상설 Tx–Rx 베이스라인**이다 |
| **T6** | Vorobev 의 4표적·750–900 m 수치 | **원문이 아니라 Demissie & Steffes IET RSN 2025 §1 의 2차 서술**이다. 그렇게 귀속해서 적을 것 |
| **T7** | **PinpuNet(IEEE ICC 2025)** 을 «OFDM mD 딥러닝» 선례로 | ⛔**FMCW 데이터셋(LSS-FMCWR-1.0)이다.** 제목의 «ISAC-based» 만 보고 세면 틀린다 — R20 의 md-rt·Ziganshin 실패와 같은 형태 |
| **T8** | **Abdul Aziz(IJIE 2023)** 를 «패시브 LTE 분류» 사례로 | ⛔**클래스가 드론 기종이 아니라 «고도 2 m vs 3 m»** 다. 시험표본 4개, 정확도 75% |
| **T9** | **Rojhani(TMTT)** 를 «측정 없이» / «스펙트로그램 CNN» 으로 | ⛔둘 다 틀림. ① 모델 파라미터가 **이전 캠페인의 클래스당 1샘플에 피팅**돼 있다(§IV-A2·결론) → «**새 표적에 대한 새 측정 캠페인이 없다**» 가 정확. ② 입력은 **레인지 프로파일 400점**이지 스펙트로그램이 아니다. ③ 진짜 결과는 12.5 pp 정확도 격차가 아니라 **최소 정밀도 78.02 vs 15.55** |
| **T10** | **Kearney 회의 선행판 저자** 를 «Salehin & Gurbuz» 로 | ⛔**Kearney & Gurbuz** 다(Crossref·PDF 표지 일치). CI4R 웹페이지 배치 때문에 잘못 읽히기 쉽다 |
| **T11** | **AirGuard** 학회판↔저널판 | **제1저자가 다르다**(Chu, IEEE/CIC ICCC 2025 ↔ Luo, JSAC). Ziganshin·Costa 에 이어 **세 번째** 사례 — 판을 명시할 것 |
| **T12** | **Ma MICCIS 2024** 의 «3종 TDD / STFT / MATLAB+FEKO / 촘촘한 DL 슬롯이 이긴다» | ⛔**넷 다 원문 초록에 없다** — 서베이 Table VIII 의 서술이다. 초록이 실제로 말하는 것은 **«MSE 로 로터 파라미터 추정 성능을 평가했고, 고SNR 에서는 다 좋지만 저SNR 에서 갈린다»** 까지. ⭐**«촘촘한 하향 센싱 슬롯» 메커니즘은 후속 Wei TWC §IV-A 에 수치와 함께 있으니 그쪽을 인용할 것** |
| **T13** | Ma MICCIS 를 «Wei TWC 의 전신» 으로 | ⚠**우리 추론이다.** Wei TWC 는 **게재판·arXiv판 어느 쪽도 MICCIS 를 인용하지 않는다.** 저자 3인 공유·같은 BUPT 연구실·시간순만 근거 |
| **T14** | **Czerkawski(IRS 2022)** 수치를 드론 결과로 | ⛔**사람 행동 인식 6클래스**다(Walking, Drinking…). 저자도 버밍엄이 아니라 **Strathclyde**. 메커니즘은 이전되지만 수치는 안 된다 |
| **T15** | **Gerard 92.7%** | 맞다. ⚠**단 잡음 추가(SNR 10–30 dB) 조건의 값**이고 청정값은 **98.1%** 다. 짝을 지어 적지 않으면 헤드라인처럼 읽힌다 |

### 5-4. ⭐기록에 **새로 넣어야 할** 것

**(가) 우리 문서 어디에도 없는데 보관함에 PDF 가 있는 편**

| ID | 왜 |
|---|---|
| `arXiv:2608.05826` (Gurung) | ⭐우리 검출 사슬의 **최근접 baseline** — Sionna RT + 실제 OAI 5G 스택 + FlexRIC + OS-CFAR + Pd-vs-RCS 사다리 + **Pfa 교정**. 기록 전무 |
| `arXiv:2511.14529` (Two-Stage ISAC LAE) | 전수 grep 0. SSB+Type#0-PDCCH+SIB1 융합 → **초기접속 신호로 UAV 센싱** = 우리 G1(SSB) 서사의 직접 경쟁 |
| `arXiv:2604.12567` (Mustafa) | 딥러닝 전환의 **전제를 정면으로 때리는 편**(수제 특징 5개가 저SNR·소데이터에서 버틴다) |
| `arXiv:2601.20817` · `2510.07948`(CAMSAP25) · `2601.15821`(ICASSP26) (Viberg 계열) | ⭐우리가 미뤄 둔 **[[sionna2-passive-caf-open]]** — «이상적 레퍼런스 → 현실 2채널 CAF» 승격에 **정확히 필요한 이론**(기준채널이 불완전할 때의 추정 효율 충분조건) |
| `arXiv:2509.13287` (Sriranga, 2채널 분산 수신기) | 같은 축 |
| `arXiv:2605.24385` (Wu, DAB+ 단일스트림 차분 CSI) | ⭐**기준채널을 따로 안 받고 신호구조에서 복원**하는 세 번째 길. 5 dB SNR 에서 심볼오율 −63%, CSI NMSE +15.1 dB, RD 맵 최소 TBR 17.8→33.1 dB |

**(나) 새 논문 · 새 표 행**

- `docs/DRONE_ISAC_PRIOR_READING.md` B절에 ⭐**Costa 팀 제3판** 행 추가 —
  **GeMiC 2025(arXiv:2502.08454)**, VTOL 7프로펠러(리프트 6 + 전방추력 1), 바이스태틱 OFDM-like 실측,
  **비행모드 판별**(이륙/착륙/호버=6개 · 천이=7개 · 순항=1개). fc 7 GHz, B 2.4 GHz, HH, 캐리어 2500(유효 2048),
  블레이드 2매·반경 28.19 cm·탄소섬유.
  식(1) **B_D = 4ωL·cos(β/2)·sin(θ)/λ** ← ⭐**우리 바이스태틱 각도 게이트 논의에 그대로 붙는 닫힌형인데
  우리 기록에 없다.**
  ⚠[우리 유도] Table 1 의 «심볼 지속 ≈1 µs» 는 **유효심볼**이고, Fig.7 이 4096 심볼을 약 200 ms 에 걸치므로
  **심볼 반복주기 T ≈ 50 µs(PRF ≈ 20 kHz)** 를 함의한다 — «심볼률 = PRF» 로 읽으면 **20배 틀린다.**
- ⭐**GeMiC 판 결론에도** *"The feature extraction and development of classifiers based on the extracted
  features are further works"* 가 있다 ⇒ 우리 `docs/S2R_JEPA_POSITION.md` **AT2**(Costa 가 학습을 비워 뒀다)가
  J-STEAP p.10 한 문장이 아니라 **서로 다른 판 두 곳**에서 확인된다 — **논거가 한 다리 튼튼해졌다.**
- `docs/REFERENCE_LIBRARY.md:411`·`:702` — `huang_uplink_srs_arxiv26` «본문 미추출» 을 채운다:
  **FR1 5G NR 100 MHz, 보행자 UE 4대, 도심 클러터, TA 명령 + 인접 occasion 켤레곱으로 LOS 기준 동기
  (서브나노초), fuse-then-detect, 3D 위치오차 중앙값 4.84 m, UE 송신 약 23 dBm.
  ⛔Friis 바이스태틱 시뮬이고 실측 없음, 분류 없음, 점표적.**
- **Ma Dingyou 외, *Hovering UAV Detection via Rotor Spectral Symmetry: A Parity-Gated GLRT Approach*,
  IEEE TVT 2026** — 같은 BUPT 그룹. ⭐**우리 report05/report12 의 hover blind 문제를 정면으로 겨눈다.**
  ⚠미열람(S2 저자목록에서 발견).
- **Vorobev·Veremyev·Kholodnyak, J. Russian Univ. Radioelectronics No.6(2018), pp.75–90 (OA)** —
  SPSympo 편의 **방법론 원편**. CAF → mD 추출 → IFFT → 주기 성분 그룹화(1그룹=프로펠러기, 2그룹=헬기).
  **Mi-8 주로터 플래시 주기 실측 62.44 ms vs 이론 62.5 ms, 꼬리로터 17.48 vs 17.5 ms;
  Cessna 172 13.3 ms(3블레이드 1500 rpm).** ⭐**우리 flash_spec 규약과 같은 논리의 실측 검증.**

---

## 6. ⚠이 조사의 한계

### 6-1. ⛔원문을 못 연 편 — **하필 «패시브+분류» 반증의 핵심이 여기 몰려 있다**

| 논문 | 왜 못 열었나 | 무엇이 미상인가 |
|---|---|---|
| **Kulpa·Malanowski·Bączyk, IRS 2025** | IEEE 유료 | ⭐제목이 그대로 «Passive Radar for Drone Detection **and Classification**» 인데 **조명원·기종수·정확도·실측규모 전부 미상**. «분류» 가 학습 분류기인지 특징 관찰인지도 모른다. **이 편으로 우리 문장을 세우면 안 된다** |
| **Ummenhofer, RADAR 2020** | IEEE 유료(Fraunhofer publica 에 bitstream 0개) | 검출거리·SNR·기종·밴드·적분시간 전부 미상. **어떤 수치도 이 논문 것으로 인용 불가** |
| **Vorobev, SPSympo 2019** | IEEE 유료 | 분류 정확도·혼동행렬·분류기 종류 미상 |
| **Jarabo-Amores, EuRAD 2018** | 원문·초록 둘 다 못 봄 | 전부 리뷰의 2차 서술 |
| **Schüpbach, RadarConf 2017** | IEEE 유료 | 수치는 Demissie 2차 서술 |
| **Welschen, RadarConf 2020** | IEEE 유료 | 미확인 |
| **Ma, MICCIS 2024** | 완전 폐쇄(OA 0, arXiv 없음) | 초록만 확보. **TDD 몇 종인지, 어느 구조가 이겼는지 미상** |
| **Xue DC-Former, ICCCS 2025** | 원문·초록 다 못 구함 | ⭐⭐**«실제 5G NR 신호로 수집 · 클래스당 1만장 · 96–98%»** 가 전부 서베이 2차 서술이다. 사실이면 **OFDM+실측+딥러닝을 동시에 만족하는 유일한 편** — **다음 라운드 원문 확보 1순위** |
| **White, RadarConf24** | IEEE 유료(OA·arXiv 없음) | 학회판 표 번호로 인용 불가. **박사학위 논문 §8.2.1 로 대체 확인** |
| **Kim, GRSL 2017** | IEEE 유료 | ⭐**«CVD 병합으로 89.3→94.7%» 가 미검증**인데 우리 `PLAN_DEEP_LEARNING` §1-2 의 CVD 근거다 |
| **Kearney & Gurbuz, DDDAS 2024** | Springer 유료 | 초록도 미확보 |

### 6-2. 못 판 각도

- ⛔**중문 저널**(우한대·베이항대·전자과기대 계열, 雷达学报 등)은 검색에 거의 안 걸린다.
  «패시브 에코 + 딥러닝» 게재 사례가 여기 있을 가능성이 가장 크다.
- **러시아어권·폴란드어권 회의록**(SPSympo · IRS · CIE Radar) 목차 단위 훑기 안 함.
- **IET RSN · IEEE TAES 의 2021~2024 호** 목차 단위 훑기 안 함.
- **패시브 ISAR/이미징 기반 인식**(Manno-Kovacs, IEEE Sensors J.; Santi, DVB-S passive ISAR)은
  **이름만 확인하고 안 팠다** — 마이크로도플러가 아닌 **제3의 분류 특징축**이라 별도 조사가 필요하다.
- **OFDM 이외 ISAC 파형(OTFS 등)의 마이크로도플러** — 보관함의 `arXiv:2601.20827`(OTFS 파일럿 도플러 모호)를
  열지 않았다.
- **CVD 근거의 1차 출처**(Kim GRSL 2017) 미확보 — 우리 A3 팔의 근거가 아직 `[2차]` 다.

### 6-3. 표본이 얇아서 말할 수 없는 것

- **패시브 분류의 «성능 분포»** — 정확도 수치를 가진 것은 **Cao 85.16%** 와 **Abdul Aziz 75%** 둘뿐이고,
  후자는 클래스가 고도 2 m vs 3 m 다. **분포를 말할 표본이 없다.**
- **Cao 의 Phantom 4 행(CRR 100%)은 실측이 아니라 합성**이다 — 실측 데이터에 드론이 없다.
  전체 ACRR 85.16%, 클래스는 UAV/일반항공기/민항기 **3종**이고 드론은 1기종. **딥러닝도 아니다.**

### 6-4. 방법·자원

- ⭐**GPU 를 전혀 쓰지 않았다**(로터 계산 15프로세스 가동 중 — 지시 준수).
- 도구: 보관함 372편 전수 훑기 → arXiv API · Semantic Scholar Graph API · Crossref · OpenAlex ·
  Unpaywall · 웹 검색/페치 → PDF 내려받아 **PyMuPDF(fitz)** 텍스트 추출.
- **파일 수정 없음.** 새 산출물만: 이 문서 · `outputs/survey_passive_ofdm_dl.json`(키 추가) ·
  `prior_work/pdfs/eusipco2020_1561__*.pdf` · `outputs/survey_pdfs/kearney_gurbuz_{TAES2026,RADAR2025}_*.pdf`.
- ⭐**내가 손계산한 것은 전부 `[우리 유도]` 로 표시했다** — Wei 의 PRF 계수 2 누락,
  DDDSU 실효 PRF 16.8 kHz, Costa GeMiC 의 심볼 반복주기 ≈50 µs. **원문이 그렇게 적은 것이 아니다.**

---

## 7. 다음 라운드 할 일 (우선순위)

1. ⭐⭐**Xue DC-Former(ICCCS 2025) 원문 확보** — 사실이면 우리의 최근접 선행이다.
2. ⭐**Kulpa IRS 2025 원문 확보** — «패시브+분류» 반증의 정점.
3. ⭐**§5-1 의 C1~C11 을 실제로 고친다**(이 문서는 정정 목록이지 정정 자체가 아니다).
4. ⭐**Mercier TAES 2020 의 pedestal 을 report10 CFAR 교정에 반영** — 균질배경 가정이 걸려 있다.
5. **Viberg 3편으로 [[sionna2-passive-caf-open]] 을 다시 연다** — 미룬 이유가 «어떻게 할지 몰라서» 였다면
   이제 근거가 생겼다.
6. **AirGuard Fig.12 를 `docs/PLAN_DEEP_LEARNING.md` 에 G6 외부 근거로 박는다.**
7. **Kim GRSL 2017 원문 확보** — CVD 팔의 1차 근거.
8. **재질 → 분류 가능성 축 실험 설계**(§1-3) — 문헌 근거 4편이 이미 있다.
