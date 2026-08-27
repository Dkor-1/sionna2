# CageDroneRF (CDRF) 정독 — arXiv 2601.03302v2 · IEEE T-AES

> **원문** `/data/public/sionna_jeong/papers_isac_sionna/new_0731/2601.03302__cagedronerf-benchmark.pdf` (17 p.)
> **읽은 날** 2026-08-27 · **읽은 범위** 전문(1~15 p. 본문 + 참고문헌)
> ⭐이 문서 이전에는 `REFERENCE_LIBRARY.md:1980` 에서 **미독본**으로 잡혀 있었고,
> `SIM2REAL_PLAN.md` 부록 A-8/A-8b/A-8c 의 축자 인용은 **형제 라운드에서 인계받은 것**이었다.
> 이번에 원문을 직접 열어 그 인용들을 **전부 확인했고**(아래 §6), 새 사실을 덧붙였다.

---

## 1. 서지

| | |
|---|---|
| 제목 | CageDroneRF: A Large-Scale RF Benchmark and Toolkit for Drone Perception |
| 저자 | Mohammad Rostami\*, Atik Faysal\* (공동 1저자), Hongtao Xia, Hadi Kasasbeh, Ziang Gao, Huaxia Wang |
| 소속 | Rowan University ECE (Glassboro, NJ) + **AeroDefense** (Oceanport, NJ) — 산학 공동 |
| 게재 | IEEE Transactions on Aerospace and Electronic Systems (T-AES) |
| arXiv | 2601.03302**v2**, cs.CV, **2026-03-19** |
| 코드 | `https://github.com/DroneGoHome/U-RAPTOR-PUB` |
| 데이터 | `https://aerodefense.tech/u-raptor-data-request` — ⚠**요청 기반 배포**(즉시 다운로드 아님) |

⭐**투고처가 우리와 겹친다.** `S2R_JEPA_POSITION.md:250` 이 P3 의 2순위로 IEEE TAES 를 적어 둔
근거가 이 논문이다. 같은 저널에 실린 데이터셋 논문이므로 **심사자 풀이 겹칠 가능성**이 있다.

---

## 2. 이 논문이 주장하는 것

한 줄로: **«데이터셋 + 도구»를 한 몸으로 설계해, 원시 I/Q 에서 라벨까지 끊기지 않는 사슬을 처음 제공한다.**

기존 벤치마크를 다섯 축으로 비판한다(p.4~5):

1. **클래스·환경 다양성** — DroneRF 3 기종, VTI 3 기종, DroneDetect V2 7 기종, RFUAV 37 기종.
2. **원시 I/Q 접근성** — DroneRF 는 크기(magnitude) 스펙트럼만, VTI·Noisy Drone 은 전처리된 텐서만.
3. **하드웨어 현실성** — RFUAV 의 **100 MS/s** 는 엣지에서 실시간 불가.
4. ⭐**원시→주석 추적성** — 이 논문이 «가장 결정적» 이라고 부르는 축(§3).
5. **도구·평가 기반** — 데이터셋 비의존 도구·교차 벤치마크 평가가 아무 데도 없다.

### 기여 목록 (p.2 축자 요약)

- CDRF 벤치마크 데이터셋(케이지 + 실외, 풍부한 샘플별 메타데이터)
- **I/Q 수준** 증강 파이프라인 — SNR 주입 · 간섭원 혼합 · 주파수 이동 + **YOLO 라벨 정확 재계산**(wrap-around 포함)
- SNR 계층화 분할(잡음만 배경 포함)
- 데이터셋 비의존 도구(생성 · 메타데이터 · Roboflow 정리 · 렌더링)
- YOLO 에서 **검출별 클래스 확률 벡터를 노출하는 패치** — 교정(calibration)·개집합 분석용
- PyTorch 기준선(이진·다중 클래스) · 개집합 인식(OSR) 구현

---

## 3. ⭐핵심 기여 — 「원시→주석 추적성」이 왜 결정적인가

이 논문의 진짜 novelty 는 데이터 «양» 이 아니라 **사슬** 이다. p.5 축자:

> *"If a researcher modifies the I/Q recording, for instance by injecting noise, applying a frequency
> shift, or mixing an interferer, the pre-existing annotations become invalid with no means to recover
> them: the spectrogram must be regenerated from the modified signal, and every bounding box must be
> re-annotated manually."*

그리고 스펙트로그램 «생성 파라미터» 를 바꿔도 같은 일이 생긴다 — 표본화율·FFT 크기·창 길이·hop 을
바꾸면 시간·주파수 해상도가 바뀌므로 **모든 픽셀 좌표가, 따라서 모든 경계상자가 바뀐다.** p.5:

> *"This effectively renders the raw I/Q data read-only for any task that requires detection-level labels."*

⭐**이 진단은 우리에게도 그대로 적용된다.** 우리 파이프라인도 STFT 파라미터를 바꾸면
(`md_mapstyle.flash_spec` 의 `PERIODS`·창 길이) 하류 그림과 지표가 전부 바뀐다. 우리는 검출 상자를
안 쓰므로 «재주석» 비용은 없지만, **「파라미터를 바꾸면 무엇이 자동으로 따라 바뀌는가」를 명시해 두는
설계** 는 배울 점이다.

---

## 4. 데이터셋 실체

### 4-1. 수집 장비 (p.5)

| | |
|---|---|
| SDR | **USRP B200-mini** + 듀얼밴드 무지향성 안테나(고정 마운트) |
| 소프트웨어 | **GNU Radio v3.10** |
| 데이터 싱크 | Lenovo IdeaPad Flex 5 · i7-1165G7 8코어 · 16 GB · Ubuntu 24.04.2 |
| 표본화율 | **20 MHz** (실내·실외 공통) |
| SDR 이득 | 실내 **50 dB** · 실외 **76 dB** |
| 대역 | 900 MHz · 2.4 GHz · 5.8 GHz 중 기종 지원 채널. **sweep scanning** 으로 주사 |

⭐**케이지 배치가 특이하다**(p.6): 안테나를 패러데이 케이지 «안» 에 두고 **UAV 는 케이지 밖 아주
가까이** 놓는다. 그래야 UAV 신호는 세게 들어오고 주변 간섭원은 케이지가 막는다.
그리고 **RC 는 옆방에 둔다** — UAV 신호와 RC 신호를 따로 분석할 수 있게 하려는 것이다.

### 4-2. 규모 — ⚠논문이 자기 총량을 안 밝힌다

제목이 «Large-Scale» 인데 **총 용량(TB)·총 시간·총 샘플 수를 어디에도 적지 않는다.**
비교 대상 RFUAV 의 «∼1.3 TB» 는 인용하면서(p.4) 자기 수치는 없다. 클래스 분포 그림에서 역산하면:

| 하위집합 | 역산 총계 | 근거 |
|---|---|---|
| 케이지(실내) Fig.3 | **≈ 7,874** 샘플 | background 1,504 = 19.1 % |
| 실외(Rowan) Fig.5 | **= 2,500** 샘플 | background 2,100 = 84.0 % |
| 최종 균형본 Fig.6 | **≈ 4,643** 샘플 | background 260 = 5.6 % |

⛔**인용할 때 주의** — 「39 클래스 / 23 기종」은 논문 축자이지만(p.2, p.4), **«large-scale» 을
용량으로 뒷받침하는 문장은 없다.** 우리가 이 논문을 «대규모» 로 인용하면 반박당할 수 있다.
안전한 표현: «**39 클래스 23 기종을 다루는 이중 환경 벤치마크**».

### 4-3. 클래스 구성의 실제 모습 — ⚠불균형이 심하다

**케이지(Fig.3)** — 배경이 19.1 % 로 최대, 상위 몇 개가 몰려 있다:
background 1504 · DJI_Mini3 656(8.3 %) · DJI_MavicMini4-armed 478(6.1 %) · DJI_FPV 449(5.7 %) ·
Autel_EXOII 293 · DJI_Mavic3 282 · Parrot_Anafi 260 · DJI_Mavic2Pro 253 …
그리고 꼬리가 **극단적으로 얇다**: DJI_Mavic3_RC-m **1개(0.0 %)** · DJI_Mini3_RC-s 4 ·
Yuneec_Q500-HD_RC-m 5 · DJI_MavicPro_RC-s 6.

**실외(Fig.5)** — ⛔**배경이 84.0 %(2,100/2,500)** 이고 드론 클래스는 **9 개뿐**이다.
그중 4 개는 샘플이 **1·2·6·8 개**다. 실질적인 실외 드론 데이터는 **약 400 샘플**이다.

**균형본(Fig.6)** — 대부분 클래스를 **156 개**로 잘라 맞추고, 4 개만 256, 배경 260.

⭐**이것이 아래 §5 결과를 읽는 열쇠다.** 「실외 일반화가 나쁘다」는 결론은 **실외 학습 데이터가
사실상 400 샘플뿐** 이라는 사실과 분리해서 읽을 수 없다.

### 4-4. 파일·메타데이터 규약 (p.6~7)

- 케이지: `{제조사}_{모델}_{대역폭}_{중심주파수}_{운용모드}.dat`
- 실외: `{device}_{status}_{env}_{sdr_gain}_{splitter}_{duration}_{distance}_{altitude}_{center_freq}_{drone_c_freq}_{bw}_{snr}_{sampling_rate}_{record_dir}.dat`
- 저장 형식: **인터리브 이진, 32-bit float 두 개**(I/Q 복소)
- 샘플별 메타데이터: 원본 경로 · 라벨 · 표본화율 · FFT 크기 · STFT 프레임 수 · **샘플별 시간 경계** · 중심주파수 · 출력 경로

⭐실외 디렉터리 이름에 **거리·고도·SNR** 이 들어간다. 우리 캠페인 설계(P3)에서 그대로 베낄 만한 규약이다.

---

## 5. 처리·증강 파이프라인

### 5-1. STFT 기본값 (p.8) — ⭐우리와 비교할 수 있는 숫자

```
scipy.signal.stft · Hann 창 · FFT_SIZE = 1024 · overlap = 128
two-sided + fftshift(DC 중앙) · SAMPLING_RATE = 20 MHz · NUM_FFT_SPEC = 1500 시간빈
S_dB = 10 log10(|X|² + ε) → [0,1] 정규화 → 지각적 컬러맵 → RGB PNG
```
컬러맵을 7 종(viridis/plasma/inferno/magma/cividis/gray/hot) 제공해 **색 민감도 시험**을 지원한다.

### 5-2. 증강 — 전부 **I/Q 단계**에서 (p.9)

| 연산 | 식 | 목적 |
|---|---|---|
| SNR 조건화 | `n ~ CN(0,σ²)`, `σ² = Ps/10^(SNR_dB/10)` | 목표 SNR 정확 주입. 잡음만 스펙트로그램도 내보냄 |
| 주파수 이동 | `x_Δf[n] = x[n]·e^{j2πΔf n/Fs}` | 반송파 옵셋·프런트엔드 오차. 스펙트로그램에서 **수직 평행이동** |
| 간섭원 혼합 | `x_mix = norm(x1 + α·x2)`, `α ∈ [0,1]` | 스펙트럼 혼잡. 각 소스에 독립 주파수 이동 가능 |
| 렌더링 변주 | 컬러맵·정규화 무작위(재현 가능) | 시각 다양성. 주파수 내용은 불변 |

⭐**핵심은 «STFT 이전» 이라는 것**(p.2 축자):
> *"Crucially, augmentations operate on complex baseband I/Q, before time-frequency conversion, so
> synthesized conditions faithfully reflect RF phenomena rather than image-level artifacts."*

정규화도 신호 수준(단위 평균전력 / I·Q 각각 z-정규화)과 스펙트로그램 수준(주파수별 z / 시간별 z /
전역 min-max) 둘 다 제공한다.

### 5-3. 주석 정책 — «whole-signal» (p.9~10)

- 한 기기의 **연속 방출 버스트 전체**를 **상자 하나**로 잡는다(스펙트럼 형태 + 시간 점유를 함께).
- 경계상자는 **ON 상태로 시작하고 ON 상태로 끝난다.** 앞뒤 OFF 는 제외.
- ⛔**배경으로 돌리는 규칙**: 버스트가 시간축의 **10 % 미만**이거나 ON 상태가 **하나뿐** 이면 상자를 안 매기고 배경으로 라벨한다.
- RC 신호(주파수 도약)는 **두 가지 주석**을 함께 제공: ①모든 버스트를 덮는 상자 하나 ②**채널별** 상자.

---

## 6. 결과 — ⭐부록 A-8 인용 전부 원문 확인 완료

### 6-1. YOLO 검출 (Table II, p.11) — YOLOv11n(nano), Ultralytics v8.3.156, COCO 사전학습

| Run | Epochs | Precision | Recall | mAP@0.5 | mAP@[.5:.95] |
|---|---|---|---|---|---|
| Clean | 100 | 0.932 | **0.982** | 0.986 | **0.948** |
| Augmented | 50 | **0.940** | **0.855** | 0.935 | 0.838 |

⭐**증강하면 정밀도는 유지·소폭 상승하는데 재현율이 0.982 → 0.855 로 떨어진다.** 논문 해석(p.11):
> *"the detector becomes more conservative (fewer false positives) at the expense of increased misses
> (more false negatives)."*

그리고 혼동행렬은 두 조건 모두 **강한 대각**을 유지한다 — 즉 **열화의 정체는 «놓침» 이지 «혼동» 이 아니다.**

⚠**에폭이 다르다**(100 vs 50). 논문은 «증강본은 원본 하나가 여러 변형으로 여러 번 보이므로 유효
노출을 맞추려는 의도» 라고 명시한다. 그래도 **동일 조건 비교는 아니다** — 인용할 때 각주가 필요하다.

### 6-2. ⭐계층 분류 — 우리가 챔버 방침 근거로 쓰는 그 수치 (p.11~12)

계층: **Modulation(3 클래스) → Protocol(5) → Model(27)**.
공유 ResNet-18 백본 + 헤드 3 개, `HierarchicalLoss`(각 헤드 교차엔트로피 가중합).
**실내로만 학습 → 실외로 평가**, 그리고 **실내+실외 혼합 학습 → 실외 평가**를 비교(실내 분량은 고정).

| 학습 구성 | Modulation | Protocol | **Model** |
|---|---|---|---|
| 실내만 | 69.95 % | 66.11 % | **42.07 %** |
| 실내+실외 | 89.42 % | 87.34 % | **69.63 %** |
| 이득 | +19.47 pp | +21.23 pp | ⭐**+27.56 pp** |

p.11 축자 (= 부록 A-8, **확인됨**):
> *"When the model is trained on indoor data only, it achieves moderate accuracy at the coarser levels
> (Modulation: 69.95%, Protocol: 66.11%) but struggles significantly with model-level identification
> (42.07%). This indicates poor domain generalization from indoor to outdoor environments."*

p.12 축자 (= 부록 A-8c, **확인됨**):
> *"accuracy increases to 89.42% for Modulation, 87.34% for Protocol, and 69.63% for Model. The most
> significant gain (+27.56 pp) is observed at the model level, the task most sensitive to environmental shifts."*

p.4 축자 (= 부록 A-8b, **확인됨**):
> *"DroneRF [77] includes only three drone models in a clean controlled environment, producing
> near-ceiling benchmark accuracy that transfers poorly to operational settings."*

⭐**핵심 규칙성: 태스크 입도가 고와질수록 도메인 격차가 커진다.**
Modulation(3) → Protocol(5) → Model(27) 로 갈수록 실내-only 성능이 무너진다(69.95 → 66.11 → 42.07).

### 6-3. 개집합 인식 (OSR, p.12) — MetaMax

- 부분집합: 드론 **14 종 · 2,180 장**. 알려진 **10 종 1,915 장** / 미지 **4 종 265 장**.
- 분할: 알려진 클래스에서만 학습 60 % · 검증 20 %, 나머지는 시험.

| 지표 | 값 |
|---|---|
| 전체 정확도 | **75.15 %** |
| 알려진 클래스 정확도 | 75.98 % |
| 미지 검출률 | **73.96 %** (265 중 196) |

논문 스스로 «성능이 클래스 크기와 강하게 상관» 한다고 적는다.

### 6-4. ⛔단일 라벨 분류 — 53.49 % (p.12~13)

ResNet-18, **20 기종**, 교차엔트로피 + Adam. **시험 정확도 53.49 %.**

⭐⭐**이 수치가 이 논문에서 제일 중요한데 가장 조용히 지나간다.** 계층 분류의 Model 수준
69.63 % 와 달리, 평평한 20-클래스 분류는 **절반 남짓**이다. 논문은 «비슷한 기종 구별이 어렵다»
정도로만 논평하고 넘어간다.

⇒ **기종 식별(model-level ID)은 이 데이터셋에서 아직 안 풀린 문제다.** 39 클래스 23 기종을
모아 놓고도 그렇다.

---

## 7. 비판적 평가 — 인용하기 전에 알아야 할 것

### ⭐강점

1. **원시→주석 추적성**이 진짜 novelty 다. 다른 벤치마크가 못 하는 일을 한다.
2. **증강이 I/Q 단계**에 있다 — 이미지 증강과 질적으로 다르다. 우리 주장과 결이 같다.
3. **패러데이 케이지 + 실외 이중 환경**을 «한 데이터셋 안에서» 대조한다 — 도메인 격차를 **자기
   데이터로 인쇄**한다. 정직하다.
4. **20 MHz 를 엣지 현실성 근거로 정당화**한다. 설계 선택에 이유가 붙어 있다.
5. 도구가 **데이터셋 비의존**이라 남의 데이터셋에도 쓸 수 있다.

### ⚠약점 — 우리가 반대로 서면 쓸 수 있는 것

1. ⛔**«Large-Scale» 을 뒷받침하는 총량 수치가 없다.** 용량·시간·총 샘플 어디에도 없다.
2. ⛔**실외 하위집합이 사실상 배경이다** — 84 %가 background, 드론은 9 클래스·약 400 샘플.
   그런데 논문의 대표 결론(「실내→실외 일반화 실패」)이 바로 이 집합에서 나온다.
   **결론의 방향은 믿을 만하지만 수치의 절대값은 이 빈약함과 분리할 수 없다.**
3. ⛔**클래스 불균형이 극단적**이다(케이지에서 1 샘플짜리 클래스 존재). 균형본은 156 개로 잘라
   맞추므로 **다수 클래스의 정보를 대량으로 버린다.**
4. ⚠**Clean 100 epoch vs Augmented 50 epoch** — 유효 노출을 맞추려는 의도는 밝혔으나 동일 조건이 아니다.
5. ⚠**데이터가 요청 기반**이다. 즉시 재현이 안 된다 — 재현성 주장에 비해 마찰이 있다.
6. ⚠**단일 라벨 53.49 %** 를 본문에서 거의 논의하지 않는다. 벤치마크 논문으로서 제일 약한 지점을
   가장 짧게 다룬다.
7. ⚠**«RF 지문(RF Drone Fingerprint)»** 을 도약 주파수·지속시간·듀티비·도약 패턴 주기로 정의하는데,
   그 특징들이 실제로 분리에 기여했는지 **절제 실험(ablation)이 없다.**

---

## 8. ⭐우리 작업과의 관계

### 8-1. 이미 쓰고 있는 곳

- `SIM2REAL_PLAN.md:52-60` — **기종 식별 주장을 포기**하는 근거. 42.07 % 인용.
- `SIM2REAL_PLAN.md:388` — 챔버 결과를 운용 성능으로 주장하지 않는 근거. «격차의 실측 선례».
- `S2R_JEPA_POSITION.md:250` — P3 투고처 2순위(IEEE TAES)가 이 논문 게재지.

### 8-2. 이번 정독으로 **강화되는** 논지

⭐**「태스크 입도가 올라갈수록 도메인 격차가 커진다」가 세 수준에서 단조롭게 확인된다**
(69.95 → 66.11 → 42.07). 우리가 챔버(clean controlled) 프레임을 쓰므로 이 비판의 정면 표적이라는
`SIM2REAL_PLAN.md` §1-3 의 자기진단은 **더 강한 근거를 얻었다.**

⭐**단일 라벨 53.49 %** 는 §1-3 의 «기종 식별 포기» 결정을 **더 단단하게** 만든다. 계층 구조를
안 쓰면 20 기종에서 절반이다.

### 8-3. 이번 정독으로 **새로 생기는** 카드

1. ⭐**우리가 «파라미터→산출물» 사슬을 명시하면 같은 novelty 축에 설 수 있다.**
   CDRF 의 사슬은 «I/Q → 스펙트로그램 → YOLO 상자» 다. 우리 사슬은 «장면·자세 → 전자기 솔버 →
   E 시계열 → STFT → 지표» 이고 **더 길다.** 다만 우리는 그것을 «기여» 로 서술한 적이 없다.
2. ⭐**실외 하위집합의 빈약함(400 샘플)은 우리 P3 캠페인 설계의 논거가 된다.**
   「선행 벤치마크의 실외 파트가 이 정도였다」는 것이 R≈40~60 비행을 정당화한다.
3. ⚠**우리 P3 novelty 문장이 이 논문과 충돌하는지 재확인 필요.**
   `SIM2REAL_PLAN.md:395` 가 이미 경고하고 있다 — «사이트 트윈 + 계산된 자세분해 σ + 분류» 조합을
   novelty 로 쓰면 반증당한다. CDRF 는 **시뮬레이션이 아니라 실측 + I/Q 증강**이므로 직접 충돌은
   아니지만, «증강으로 도메인 격차를 메운다» 는 축에서는 겹친다.
4. **20 MHz · FFT 1024 · overlap 128 · 1500 시간빈** 은 우리가 실측 캠페인을 설계할 때
   **비교 가능성을 위해 맞춰 볼 만한 규약**이다.

### 8-4. ⛔인용 규칙 (이 저장소 관례)

- 42.07 / 69.63 / +27.56 pp · 89.42 / 87.34 — **p.11~12 축자, 확인됨. 그대로 인용 가능.**
- «three drone models in a clean controlled environment» — **p.4 축자, 확인됨.**
- **53.49 %** (단일 라벨, p.12) · **75.15 / 73.96 %** (OSR, p.12) · **Table II 검출 수치**(p.11) —
  이번에 새로 확인. 인용 가능.
- ⛔**«large-scale» 을 용량 근거로 인용하지 말 것.** 논문에 총량 수치가 없다.
- ⛔**실외 결과를 인용할 때는 «실외 드론 샘플 약 400» 을 함께 적을 것.** 안 적으면 과대인용이다.

---

## 9. 재현·확인 방법

```bash
P=/data/public/sionna_jeong/papers_isac_sionna/new_0731/2601.03302__cagedronerf-benchmark.pdf
pdftotext -f 11 -l 12 -layout "$P" - | grep -A3 '42.07'      # 계층 분류 축자
pdftotext -f 11 -l 11 -layout "$P" - | grep -B2 -A6 'TABLE II' # 검출 표
pdftotext -layout "$P" - | grep -n '53.49'                    # 단일 라벨
```
⚠`pdftotext` 는 `poppler-utils` 가 필요하다(2026-08-27 이 컨테이너에 설치함).
