# 드론 마이크로도플러 분류 — 딥러닝 선행연구 조사 (2026-08-15)

> 조사 범위: ① 레이다 마이크로도플러 스펙트로그램 기반 드론 분류의 **원조·대표 CNN 계열**
> (네트워크 이름을 정확히) ② 그 직전 세대인 **고전 ML 뿌리**(수작업 특징 + SVM/베이즈/부스팅)
> ③ **입력 표현**(스펙트로그램/CVD/스펙트럼/캡스트럼)이 분류 성능에 미치는 영향.
> 지정 후보 6건(Kim GoogLeNet · Mendis DBN · Molchanov · Rahman & Robertson ·
> Ritchie NetRAD · Björklund)의 **존재·내용을 전부 1차 자료로 검증**했다.
> 1차 자료 = DOI 초록(OpenAlex API 원문), 공개 PDF(TNO·Glasgow eprints·로컬 보관본), Nature 전문.
> 확인 못 한 것은 §6 «못 찾았다» 에 정직하게 남겼다.

---

## TL;DR — 다섯 줄

1. **원조 CNN = Kim, Kang, Park (KAIST)** — *Drone Classification Using CNN With Merged
   Doppler Images*, IEEE GRSL 14(1):38–42 (온라인 2016-11, 인쇄 2017-01). **GoogLeNet** 에
   마이크로도플러 시그니처(MDS, 시간영역)와 CVD(주파수영역)를 **한 장으로 합친 «merged
   Doppler image»** 를 먹인다. Ku-band FMCW 실측(무향실+야외), 89.3 % → 94.7 %
   (MDS 단독 → 병합), 2기종 구분은 100 %.
2. **같은 해의 다른 갈래 = Mendis et al.** — MILCOM 2016, pp.924–929. CNN 이 아니라
   **deep belief network(DBN)** 이고 입력도 스펙트로그램이 아니라 **스펙트럼 상관함수(SCF)**
   다. 2.4 GHz CW 실측, 마이크로 UAS 3종, 정확도 «90 % 이상». 드론 마이크로도플러에
   딥러닝을 얹은 최초 그룹의 하나이지만 «CNN+스펙트로그램» 계보는 아니다.
3. **뿌리는 고전 ML 3부작** — ① Molchanov et al. 2014(IJMWT): X-band 9.5 GHz CW,
   마이크로도플러 시그니처 **상관행렬의 고유쌍(eigenpair)** 특징 + SVM/나이브베이즈,
   11클래스 약 92 %(회의판 EuRAD 2013 은 비선형 SVM 95.4 %). ② Ritchie/Fioranelli 의
   **멀티스태틱 NetRAD**(2.4 GHz, 3노드): SVD·센트로이드 특징 + 판별분석/나이브베이즈,
   페이로드 5클래스 96.8~98.2 %(멀티스태틱 투표). ③ Björklund EuRAD 2018: TVD 물리특징 +
   **부스팅**. — 셋 다 딥러닝이 **아니다**. 이름을 정확히 불러야 한다.
4. **대규모 실측 + CNN 완성형 = Rahman & Robertson**, IET RSN 14(5):653–661 (2020).
   비행 중 드론·새 스펙트로그램 대형 DB를 만들고 **GoogLeNet(RGB 입력)** 과 **자작 소형
   series CNN(그레이스케일)** 을 나란히: series 검증/테스트 99.6/94.4 %(4클래스),
   99.3/98.3 %(2클래스), GoogLeNet 은 전부 약 99 %. 데이터 뿌리는 같은 그룹의 Sci Rep
   8:17396 (2018) K-band 24 GHz + W-band 94 GHz 캠페인(그 논문 자체는 ML 없는 시그니처
   분석이고, 새는 진짜 맹금류 4종).
5. **«스펙트로그램이 항상 최선»은 아니다** — Gérard et al., EUSIPCO 2020, pp.1561–1565
   (로컬 PDF 보관, 원문 직독). GoogLeNet 고정 + 입력 표현만 5종 교체, S-band 3 GHz 펄스
   (PRF 10 kHz, 표적거리 1.5 km, 실기 5기종): 장시간 **스펙트럼(WSP) 98.1 % > 캡스트럼
   97.4 % > CVD 94.5 % > STFT 스펙트로그램 92.6 % > 원시 x(t) 75.8 %**. 잡음 주입 시 격차가
   더 벌어진다(WSP 92.7 % vs SG 73.4 %).

---

## 0. 우리 기록과의 접점

- **입력 표현 정책**: 우리는 마이크로도플러를 **STFT 스펙트로그램만** 쓰기로 했다
  (메모 «마이크로도플러는 STFT만»). Gérard §5 의 결과(장시간 스펙트럼·캡스트럼이 분류에는
  더 유리)는 이 정책과 **긴장 관계**다 — 다만 Gérard 의 우위는 «준정지 표적 + 300 ms 관측»
  조건이고, 우리 용도(플래시 시인성, 시간분해능 우선)와 목적함수가 다르다. 분류기를 실제로
  붙이는 단계가 오면 이 표를 근거로 표현을 다시 논의해야 한다(그 전엔 정책 유지).
- **선행 방법론 차용·결과비교 상시규칙**: 아래 §5 종합표가 사과-대-사과 비교의 출발점.
  우리 시뮬 스펙트로그램에 분류기를 얹을 때 1차 재현 대상은 Kim(merged Doppler image)과
  Rahman & Robertson(스펙트로그램 + GoogLeNet/소형 CNN) 두 편이다.
- 기존 `prior_work/` 서베이들과 표적 겹침 없음(본 서베이가 분류 계보 첫 편).

---

## 1. 딥러닝 이전 뿌리 — 고전 ML 3부작

### 1.1 Molchanov et al. 2014 — 고유쌍 특징 + SVM (X-band CW)

- **서지(검증)**: P. Molchanov, R. I. A. Harmanny, J. J. M. de Wit, K. Egiazarian, J. Astola,
  *Classification of small UAVs and birds by micro-Doppler signatures*, Int. J. Microwave and
  Wireless Technologies **6**(3-4):435–444, 2014. DOI
  [10.1017/S1759078714000282](https://doi.org/10.1017/S1759078714000282).
  회의판: 10th European Radar Conference (EuRAD 2013), Nuremberg, pp.172–175 —
  [TNO 공개 PDF](https://publications.tno.nl/publication/105220/tJKET4/molchanov-2013-classification.pdf)
  전문 직독.
- **방법**: CW(또는 고PRF 펄스) 레이다 → 마이크로도플러 시그니처 추정 → 몸체 도플러 보상
  정렬 → **시그니처 상관행렬 Ψ(f₁,f₂)의 고유쌍 {vᵣ, λᵣ}** 을 특징으로 추출(식 (7)–(8),
  EVD/SVD) → 선형/비선형 SVM, 나이브베이즈.
- **데이터**: 실측, X-band **9.5 GHz CW** 레이다(D-RACE: Thales NL + TNO 공동). 고정익
  모형기·쿼드로터·헬기 모형(Align T-REX 450 등)·정지 로터·**새**를 포함한 **11클래스**.
- **정확도**: 저널판 초록 «약 92 %»; 회의판 Table II(10-fold CV): 선형 SVM 94.91 %,
  **비선형 SVM 95.39 %**, 나이브베이즈 93.6 %.
- **의의**: «UAV 마이크로도플러 분류» 문제 설정 자체의 원조격. UAV/새 구분을 처음부터
  같은 문제 안에 넣었다.

### 1.2 Ritchie, Fioranelli et al. — 멀티스태틱 NetRAD (S-band)

- **서지(검증)**: M. Ritchie, F. Fioranelli, H. Borrion, H. Griffiths, *Multistatic
  micro-Doppler radar feature extraction for classification of unloaded/loaded micro-drones*,
  IET Radar, Sonar & Navigation **11**(1):116–124 (온라인 2016). DOI
  [10.1049/iet-rsn.2016.0063](https://doi.org/10.1049/iet-rsn.2016.0063).
  [Glasgow eprints 공개 PDF](http://eprints.gla.ac.uk/119563/8/119563.pdf) 전문 직독.
  자매편: Fioranelli et al., *Classification of loaded/unloaded micro-drones using multistatic
  radar*, Electronics Letters 51(22):1813–1815, 2015, DOI
  [10.1049/el.2015.3038](https://doi.org/10.1049/el.2015.3038).
- **방법**: UCL **NetRAD** — 2.4 GHz S-band 코히어런트 펄스, **3노드**(모노스태틱 1 +
  바이스태틱 수신 2, 기선 50 m), 첩 0.6 µs/45 MHz, PRF 5 kHz. 특징은 ① RCS 계열
  ② 스펙트로그램 **SVD**(U 행렬 대각 성분의 평균·표준편차) ③ **도플러/대역폭 센트로이드**.
  분류기는 diagonal-linear 판별분석, 나이브베이즈, 랜덤포레스트 — **딥러닝 아님**.
- **데이터**: 실측, 2015-07 야외(UCL 스포츠그라운드). 마이크로드론 호버/비행 ×
  페이로드(무게) — 호버 시나리오 **5클래스**.
- **정확도**: 센트로이드 특징 96.8~98 %(나이브베이즈+투표), SVD 특징 92.8~96.6 %;
  멀티스태틱 threshold voting 최고 **98.2 %**, 모노 단독은 91~94 %. 1 s 관측으로 충분.
- **의의**: 멀티스태틱 정보의 이득을 정량화한 원조. 단 «all multi data 를 한 분류기에
  합치면 57~61 %로 추락, 노드별 분류 + 투표가 정답»이라는 관찰이 우리 다중 Rx 설계
  (report12 코히어런트 상한)와 직접 비교 대상.

### 1.3 Björklund 2018 — TVD 물리특징 + 부스팅

- **서지(검증)**: S. Björklund, *Target Detection and Classification of Small Drones by
  Boosting on Radar Micro-Doppler*, 15th European Radar Conference (EuRAD 2018), Madrid. DOI
  [10.23919/EuRAD.2018.8546569](https://doi.org/10.23919/EuRAD.2018.8546569) (초록 원문 확인).
- **방법**: 실측 드론·새 데이터 → **TVD(Time Velocity Diagram)** 에서 물리 특징 추출 →
  **부스팅** 분류기(SVM 과 비교). 드론 vs 새(검출) + 드론 기종(분류).
- **주의**: 과제 지문의 «Björklund (CVD)» 는 부정확 — 이 논문의 입력은 CVD(cadence-velocity
  diagram)가 아니라 **TVD** 다(초록 원문 기준). 정확도 수치·레이다 대역은 초록에 없음(§6).

---

## 2. 원조 딥러닝 계열 — 이름을 정확히

### 2.1 Kim, Kang, Park 2016/2017 — GoogLeNet + merged Doppler image ⭐원조 CNN

- **서지(검증)**: B. K. Kim, H. S. Kang, S.-O. Park, *Drone Classification Using
  Convolutional Neural Networks With Merged Doppler Images*, IEEE Geoscience and Remote
  Sensing Letters **14**(1):38–42 (온라인 2016-11, 인쇄 2017-01). DOI
  [10.1109/LGRS.2016.2624820](https://doi.org/10.1109/LGRS.2016.2624820)
  (OpenAlex 초록 원문 + KAIST Pure 메타데이터 교차확인).
- **네트워크**: **GoogLeNet** (Szegedy 2015 Inception v1). «고성능 + 계산자원 최적화» 가
  선택 이유.
- **입력 표현**: **merged Doppler image** — MDS(마이크로도플러 시그니처, 시간영역)와
  **CVD**(MDS 의 주파수영역 표현)를 **한 이미지로 병합**. CVD 를 드론 CNN 분류에 끌어들인
  것이 이 논문의 고유 기여.
- **데이터**: 실측, **Ku-band FMCW** 레이다. 무향실 + 야외 두 환경. 모터 개수·애스펙트각을
  바꾼 단일 기체 실험 + 50/100 m 고도의 2기종 실험.
- **정확도**: MDS 단독 89.3 % → 병합 이미지 **94.7 %**; 2기종 구분(50/100 m)은 **100 %**.
- **의의**: «CNN + 마이크로도플러 이미지» 로 드론을 분류한 대표 원조. 이후 논문들(아래
  Gérard 포함)이 GoogLeNet 을 비교 기준으로 삼는 계보의 출발점.
- 후속(참고): 같은 그룹 *Improved Drone Classification Using Polarimetric Merged-Doppler
  Images* (존재만 확인, 세부 미검증 — §6).

### 2.2 Mendis et al. 2016 — deep belief network + 스펙트럼 상관함수

- **서지(검증)**: G. J. Mendis, T. Randeny, J. Wei, A. Madanayake, *Deep learning based
  doppler radar for micro UAS detection and classification*, IEEE MILCOM 2016, pp.924–929.
  DOI [10.1109/MILCOM.2016.7795448](https://doi.org/10.1109/MILCOM.2016.7795448)
  (dblp 레코드 + Semantic Scholar 초록 교차확인).
- **네트워크**: **deep belief network(DBN)** — CNN 아님. (후속 확장판에서는 «저복잡도
  binarized DBN» 표기.)
- **입력 표현**: 스펙트로그램이 아니라 **스펙트럼 상관함수(SCF, spectral correlation
  function)** — 자기상관의 푸리에 변환으로 잡음에 강인한 순환정상성 패턴을 쓴다.
- **데이터**: 실측, **2.4 GHz CW** 도플러 레이다, 실험실 조건(기체 고정 + 프로펠러 구동),
  마이크로 UAS **3종**(후속판 기준 헬리콥터·인공 새·쿼드콥터).
- **정확도**: 초록 기준 **«90 % 이상»**. (후속 확장판의 ~97 % 수치는 원문 미확인 — §6.)
- **의의**: 드론 마이크로도플러에 심층 신경망을 얹은 최초기 논문의 하나. 다만 계보는
  «CNN+이미지» 가 아니라 «DBN+순환정상 특징».

### 2.3 Björklund & Wadströmer 2019 — 같은 데이터로 부스팅 → 딥러닝 승격

- **서지(검증)**: S. Björklund, N. Wadströmer, *Target Detection and Classification of Small
  Drones by Deep Learning on Radar Micro-Doppler*, 2019 International Radar Conference
  (RADAR), Toulon, pp.1–6. DOI
  [10.1109/RADAR41533.2019.171294](https://doi.org/10.1109/RADAR41533.2019.171294) (초록 원문 확인).
- **방법**: §1.3 과 **같은 실측 데이터·같은 TVD 입력**에 딥러닝 분류기를 적용, 자신들의
  부스팅·SVM 대비 **성능 향상**을 보고. 드론 vs 새 + 드론 기종 분류.
- **주의**: 정확한 아키텍처 이름·수치는 초록에 없음(페이월, §6). «딥러닝 분류기» 까지만
  1차 확인.

---

## 3. 대표 완성형 — Rahman & Robertson (St Andrews) 2018 → 2020

### 3.1 Sci Rep 2018 — 시그니처 물리 앵커 (ML 없음)

- **서지(검증)**: S. Rahman, D. A. Robertson, *Radar micro-Doppler signatures of drones and
  birds at K-band and W-band*, Scientific Reports **8**:17396, 2018. DOI
  [10.1038/s41598-018-35880-9](https://doi.org/10.1038/s41598-018-35880-9) (Nature 전문 직독).
- **내용**: **분류기 없음** — STFT 스펙트로그램 시그니처 분석 전용. K-band **24 GHz FMCW**
  (+25 dBm, 첩 234.8 µs) + W-band **94 GHz** 2기(T-220 코히어런트 FMCW, NIRAD 헤테로다인).
  드론 3기종(DJI Phantom 3 Standard, Inspire 1, S900) + **실제 맹금류 4종**(수리부엉이·해리스
  매 등, 0.26~1.84 kg).
- **핵심 관찰**: 드론은 블레이드 플래시 + **HERM 라인**, 마이크로도플러가 몸체 대비
  −20~−40 dB; 새는 4~6 Hz 날갯짓 주기 플래시, 몸체 대비 0~−10 dB. W-band 가 일부 조건에서
  5~10 dB 유리. → 드론/새 구분 가능성의 물리 근거이자 3.2 의 데이터 기반.

### 3.2 IET RSN 2020 — GoogLeNet + 자작 series CNN ⭐대표 CNN 완성형

- **서지(검증)**: S. Rahman, D. A. Robertson, *Classification of drones and birds using
  convolutional neural networks applied to radar micro-Doppler spectrogram images*, IET
  Radar, Sonar & Navigation **14**(5):653–661, 2020 (온라인 2019-12). DOI
  [10.1049/iet-rsn.2019.0493](https://doi.org/10.1049/iet-rsn.2019.0493) (OpenAlex 초록 원문).
- **네트워크**: 두 갈래 병행 — ① **GoogLeNet** (RGB 스펙트로그램 이미지) ② 본 연구에서
  개발한 **자작 series(직렬) CNN** (그레이스케일 이미지, 경량).
- **입력 표현**: 비행 중 드론·새의 **마이크로도플러 스펙트로그램 이미지** 대형 DB(RGB판 +
  그레이스케일판). 클래스 구성 2종: 4클래스(드론/새/클러터/잡음), 2클래스(드론/비드론).
- **데이터**: 실측. 레이다는 초록에 명시 없음 — 같은 그룹 3.1 캠페인 계열(24 GHz +
  94 GHz T-220)이라는 2차 확인만(§6).
- **정확도**: series CNN 검증/테스트 **99.6/94.4 %**(4클래스), **99.3/98.3 %**(2클래스);
  **GoogLeNet 은 전 구성에서 약 99 %**.
- **의의**: «대형 실측 DB + 검증/테스트 분리 + 기성 CNN vs 자작 경량 CNN» 이라는, 이후
  드론 분류 논문들의 표준 상차림을 완성.

---

## 4. 입력 표현이 성능을 가른다 — Gérard et al. EUSIPCO 2020 (로컬 PDF 직독)

- **서지(검증)**: J. Gérard, J. Tomasik, C. Morisseau, A. Rimmel, G. Vieillard
  (CentraleSupélec + ONERA), *Micro-Doppler Signal Representation for Drone Classification by
  Deep Learning*, 28th European Signal Processing Conference (EUSIPCO 2020), pp.1561–1565.
  로컬 보관본 `prior_work/pdfs/eusipco2020_1561__gerard_microdoppler-representation-drone-dl.pdf`
  전문 직독. 공개 링크: [EURASIP 프로시딩 PDF](https://eurasip.org/Proceedings/Eusipco/Eusipco2020/pdfs/0001561.pdf).
- **설계**: 네트워크를 **GoogLeNet 으로 고정**(선행 비교 가능성 때문에 선택)하고 **입력
  표현만 5종 교체** — 원시 시계열 x(t), 장시간 스펙트럼 WSP, 캡스트럼 CP, STFT
  스펙트로그램 SG(창 2.5 ms), CVD. 복소 데이터는 실부/허부를 2채널로 주입.
- **데이터**: 실측, ONERA **Medycis** 시스템, **S-band 3 GHz** 펄스, PRF 10 kHz, 수평
  편파, 표적거리 **1.5 km ± 250 m**, 2019-04 2주 캠페인. 실기 **5기종**(DJI S1000-A2,
  grand Spyder, Gryphon, DJI Phantom 4 Pro, DJI Mavic Pro), 관측 300 ms 조각, 학습/시험을
  **날짜로 분리**(분리 안 하면 98~100 %로 과대낙관 — 명시적 경고).
- **정확도**(5클래스, 날짜분리 시험):

  | 입력 표현 | 기준 [%] | 잡음 주입 [%] | 짧은 관측 [%] |
  |---|---|---|---|
  | x(t) 원시 시계열 | 75.8 | 72.6 | 67.1 |
  | **WSP 장시간 스펙트럼** | **98.1** | **92.7** | 93.7 |
  | CP 캡스트럼 | 97.4 | 80.9 | **94.0** |
  | SG 스펙트로그램 | 92.6 | 73.4 | 87.3 |
  | CVD | 94.5 | 79.2 | 79.3 |

- **결론**: 준정지 드론이면 **주파수 분해능(스펙트럼·캡스트럼)이 시간-주파수(스펙트로그램)
  보다 분류에 유리**하고, 잡음 강건성도 WSP 가 압도(격차 10 pt+). CVD 는 장관측 전제라
  짧은 관측에서 급락(−15.2 pt). — «스펙트로그램 = 기본값» 이라는 통념에 대한 1차 반례.

---

## 5. 종합표 — 검증된 9편

| # | 논문 (연도) | 기법(정확한 이름) | 입력 표현 | 데이터 | 표적 | 정확도 | 1차 링크 |
|---|---|---|---|---|---|---|---|
| 1 | Molchanov et al. (2014) | 고유쌍 특징 + 선형/비선형 SVM·나이브베이즈 (**DL 아님**) | 정렬된 MD 시그니처 상관행렬의 고유쌍 | 실측 X-band 9.5 GHz CW (Thales/TNO) | 11클래스 (모형기·쿼드·헬기·정지로터·새) | ~92 % (저널) / 95.4 % (회의판 비선형 SVM) | [DOI](https://doi.org/10.1017/S1759078714000282) |
| 2 | Fioranelli et al. (2015 EL) | 나이브베이즈·판별분석 (**DL 아님**) | MD 센트로이드 특징 | 실측 NetRAD 2.4 GHz 멀티스태틱 | 페이로드 유/무 | 96~97 % (호버) | [DOI](https://doi.org/10.1049/el.2015.3038) |
| 3 | Ritchie et al. (2016/17 IET) | diagonal-linear 판별분석·나이브베이즈·랜덤포레스트 + 멀티스태틱 투표 (**DL 아님**) | 스펙트로그램 SVD·도플러/대역폭 센트로이드 | 실측 NetRAD 2.4 GHz, 3노드, PRF 5 kHz | 페이로드 5클래스 | 센트로이드 96.8~98.2 % | [DOI](https://doi.org/10.1049/iet-rsn.2016.0063) · [PDF](http://eprints.gla.ac.uk/119563/8/119563.pdf) |
| 4 | Kim, Kang, Park (2016/17 GRSL) ⭐ | **GoogLeNet** | **merged Doppler image (MDS+CVD 병합)** | 실측 Ku-band FMCW, 무향실+야외 | 드론 2기종 (+모터수·각도) | 89.3→**94.7 %**, 2기종 100 % | [DOI](https://doi.org/10.1109/LGRS.2016.2624820) |
| 5 | Mendis et al. (2016 MILCOM) | **deep belief network (DBN)** | **스펙트럼 상관함수(SCF)** | 실측 2.4 GHz CW, 실험실 | 마이크로 UAS 3종 | >90 % | [DOI](https://doi.org/10.1109/MILCOM.2016.7795448) |
| 6 | Björklund (2018 EuRAD) | 부스팅, SVM 비교 (**DL 아님**) | TVD 물리특징 | 실측 (대역 미확인, §6) | 드론 기종 + 새 | 수치 미공개(초록) | [DOI](https://doi.org/10.23919/EuRAD.2018.8546569) |
| 7 | Björklund & Wadströmer (2019 RADAR) | 딥러닝 분류기(정확 아키텍처 §6) | TVD | §1.3 과 동일 실측 | 드론 기종 + 새 | 부스팅·SVM 대비 향상(수치 §6) | [DOI](https://doi.org/10.1109/RADAR41533.2019.171294) |
| 8 | Rahman & Robertson (2018 SciRep) | 없음 — 시그니처 분석 (**ML 아님**) | STFT 스펙트로그램 | 실측 K-band 24 GHz FMCW + W-band 94 GHz (T-220·NIRAD) | 드론 3기종 + 맹금류 4종 | — (HERM·플래시 물리) | [DOI](https://doi.org/10.1038/s41598-018-35880-9) |
| 9 | Rahman & Robertson (2020 IET) ⭐ | **GoogLeNet(RGB)** + **자작 series CNN(그레이)** | MD 스펙트로그램 이미지 대형 DB | 실측 (동 그룹 K/W-band 계열, §6) | 4클래스 / 2클래스 | series 테스트 94.4 %(4c)·98.3 %(2c), GoogLeNet ~99 % | [DOI](https://doi.org/10.1049/iet-rsn.2019.0493) |
| 10 | Gérard et al. (2020 EUSIPCO) ⭐ | **GoogLeNet** (표현 비교 실험대) | x(t)/WSP/CP/SG/CVD 5종 | 실측 S-band 3 GHz 펄스, 1.5 km, ONERA Medycis | 실기 5기종 | WSP 98.1 % … SG 92.6 % … x(t) 75.8 % | 로컬 PDF · [EURASIP](https://eurasip.org/Proceedings/Eusipco/Eusipco2020/pdfs/0001561.pdf) |

계보 요약: **고유쌍+SVM(2014) → 멀티스태틱 수작업 특징(2015-17) → DBN+SCF(2016) ↘
GoogLeNet+병합이미지(2016) → TVD 부스팅(2018)→DL(2019) → 대형DB+GoogLeNet/경량CNN(2020)
→ 입력표현 체계 비교(2020)**.

---

## 6. «못 찾았다» — 정직 선언

1. **Björklund 2018/2019 의 레이다 대역·기종**: 두 편 다 IEEE 페이월이고 공개 초록에
   대역이 없다. FOI(스웨덴 국방연구소) 소속이라는 것까지만 확실. 웹검색·DiVA 검색으로
   본문 확보 실패.
2. **Björklund & Wadströmer 2019 의 정확한 네트워크 이름**(층 구성·CNN 여부)과 정확도
   수치: 초록은 «deep learning classifier» 까지만. 2차 문헌(리뷰 PMC7435842)에 2018 부스팅판
   ~80 % 언급이 있으나 원문 미확인이라 본문 표에 싣지 않았다.
3. **Mendis 2017 확장판** (*Deep learning cognitive radar for micro UAS detection and
   classification*, IEEE CCAA 워크숍 2017): 존재는 확인(FIU/S2 레코드), 검색 스니펫의
   «~97 %, S-band CW» 는 원문 미확인이라 채택 보류.
4. **Rahman & Robertson 2020 본문의 레이다 목록**: 초록에 대역 명시가 없다. «24 GHz +
   94 GHz T-220» 은 검색 결과(2차) + 동일 그룹 2018 캠페인과의 연속성이라는 정황뿐이라
   본문 §3.2 에 «2차 확인» 으로만 적었다.
5. **Kim 2016 의 Ku-band 중심주파수**(14.x GHz 등 정확값)와 2기종의 기체명: 초록에 없음.
   원문 PDF 미확보.
6. **Kim 그룹 후속 폴라리메트릭판** (*Improved Drone Classification Using Polarimetric
   Merged-Doppler Images*): 존재만 확인(Semantic Scholar 레코드), 서지·수치 미검증.
7. 과제 지문의 «Björklund (CVD)» 대응물: Björklund 드론 논문 2편의 입력은 **TVD** 다.
   CVD 를 쓴 것은 Kim(2016, 병합 이미지 성분)과 Gérard(2020, 비교 대상 5종 중 하나) —
   Björklund+CVD 조합의 드론 논문은 **못 찾았다**.

---

## 부록 — 검증 방법 provenance

- OpenAlex API(`api.openalex.org/works/doi:…`)로 6개 DOI 의 서지+초록 원문을 받아 초록
  문장에서 기법·수치를 직접 인용(§1.1, §1.3, §2.1, §2.3, §3.2, 표의 정확도).
- 전문 직독 3편: Molchanov 회의판(TNO 공개 PDF), Ritchie(IET 수리판, Glasgow eprints),
  Gérard(로컬 보관 PDF, `fitz` 추출) + Rahman 2018(Nature 웹 전문).
- Mendis 는 dblp 레코드(MILCOM 2016, pp.924–929, DOI)와 Semantic Scholar 초록 교차확인.
- 웹검색은 후보 발견·교차확인용으로만 썼고, 수치는 전부 1차 자료(초록/전문)에서 재확인된
  것만 본문 표에 실었다. 미재확인 수치는 전부 §6 으로 보냈다.
