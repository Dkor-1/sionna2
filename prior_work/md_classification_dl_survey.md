# 드론 마이크로도플러 분류 — 딥러닝 선행연구 종합 (2026-08-15)

> **조사 범위**: ① 레이다 마이크로도플러(로터가 만드는 미세 도플러)로 드론을 **분류**한 논문의
> **기법 계보** — 고전 특징+분류기부터 CNN 전이학습·경량 CNN·시퀀스 모델·트랜스포머까지 ②
> **입력 표현**의 표준(무엇을 망에 먹이나) ③ **합성 데이터로 학습해 실측에 쓰는(sim-to-real)**
> 축의 성숙도 ④ **패시브(방송·통신 조명원) 에코로 분류**한 사례의 존재 여부 ⑤ 우리 첫 분류
> 실험(`benchmark/classify_airframe.py`)이 이 계보의 어디에 놓이는가.
> 수치 원장: `outputs/md_classification_dl_survey.json`.
>
> **회수된 조사다.** 수집·원문검증은 앞 라운드가 했고 **종합 단계에서 세션 한도로 끊겼다.**
> 회수 파일 `survey_recovered.json` 에 **논문 45편**(수집·중복제거 완료)과 **판정 41건**(원문
> 대조)이 남아 있었고, 이 문서는 그 위에 종합만 얹었다. ⭐**본표(§3)에는 판정에서 통과한
> 39편만 넣는다.** 판정이 «불통과»인 2편과 **판정 자체가 없는 4편**은 §5 에 이유와 함께 남긴다.
> 나 자신이 이번에 직접 다시 연 링크는 §6 의 7건뿐이다 — 나머지 39편의 «원문과 맞다»는 판정은
> **앞 라운드 검증자를 신뢰한 것**이고, 그 사실을 숨기지 않는다.
>
> ⛔ 이 조사는 «그런 논문이 없다»를 결론으로 쓰지 않는다. 쓸 수 있는 문장은
> **«이번 검증 집합에서 못 찾았다»** 뿐이다.

---

## TL;DR — 다섯 줄

1. **주류는 여전히 «스펙트로그램 이미지 + CNN»이고, 상위 정확도는 큰 망이 아니라 «경량 전용
   CNN + 좋은 전처리»가 가져간다.** 2017년 Kim 의 GoogLeNet(⚠전이학습 여부는 원문에 명시 없음)으로 시작한 계보가
   2020~2022 년에 **0.15~0.45 M 파라미터급 스크래치 CNN**(Park 의 light CNN 97.14 % ·
   DIAT-RadSATNet 97.3 % · AirGuard 0.15 M 99.37 %)으로 옮겨 갔고, 2025~2026 에 트랜스포머
   (ViT 97.76 % · DC-Former 96~98 % · Swin)와 **Mamba 상태공간 모델**(97.5 %)이 얹혔다.
   ⚠**정확도는 이미 포화**(97~99 %)라 «누가 더 정확한가»는 더 이상 변별력이 없다 —
   변별력은 **어떤 데이터·어떤 분할 규약이었나**에 있다.
2. **입력 표현의 표준은 STFT 스펙트로그램이다**(검증된 분류 논문 29편 중 **20편이 그대로 망에
   넣고**, 4편은 거기서 특징만 뽑는다 — 시간-주파수 면을 아예 안 거치는 것은 **5편뿐**). 개선은 두
   갈래로만 갈린다 — **병합**(Kim: MDS+CVD 로 89.3→94.7 % · Chen: mD+CVD+켑스트럼 융합
   >97 % · AirGuard: cmD+HRRP 로 97.75→99.37 % · Zhang: L/K 듀얼밴드 late fusion)과
   **복소 보존**(Park 의 실수·허수 2채널 · Gérard 의 1-D 2채널 · Larrat 의 시계열 직행).
   ⭐**망을 고정하고 전처리만 바꿔 +10 pp** 를 얻은 사례가 있다(Park 의 A-SPC: 87.14→97.14 %) —
   **표현 교체가 백본 교체보다 이득이 크다**는 것이 이 분야의 반복된 교훈이다.
3. **sim-to-real 은 «아직 못 넘었다»가 정직한 요약이다.** 합성만으로 학습해 실측에서 실측학습을
   이긴 사례는 **검증 집합에 0편**이다. 최선은 **반합성**(White: 합성 표적을 실측 배경 시계열에
   주입 → 86.6 % vs 실측학습 89.7 %, **−3.1 pp**)이고, 정면 경고도 있다 — Kearney & Gurbuz 는
   **저충실도 시뮬 단독 학습이 random guessing 을 못 넘었다**고 §V-A 에 적고, 시뮬을 학습
   데이터가 아니라 **분류기 앞단의 물리 사전(prior)** 으로 쓰라고 처방한다(50.0→71.2 % 개선은
   합성 훈련데이터 쪽 공로). 시뮬 전용으로 99 %를 보고한 편들(AirGuard 99.37 % · Networked ISAC
   97.82 %)은 **시뮬 안에서 시험한 수**(sim-to-sim)라 성격이 다르다.
4. **패시브 조명원 에코 + 딥러닝 분류는 검증 집합에 0편이다.** 그런데 이 «0»은 조심해서 읽어야
   한다 — 패시브 후보 3편(Vorobev DVB-T2 2019 · Kulpa IRS 2025 · Cao DTMB 2025)이 **하필 전부
   판정 못 받은 4편 칸에 몰려 있고**, 앞 조사(`passive_ofdm_dl_survey.md`)에 따르면 그 셋은
   **애초에 딥러닝이 아니다**(정성 구분 또는 RCS 유사도 인식기). 통신 파형으로 간 학습 분류는
   전부 **모노스태틱 ISAC** 쪽이다 — 실측은 DC-Former(5G NR 3.5 GHz·100 MHz) 하나, 나머지는
   시뮬(AirGuard·Networked ISAC). ⭐**바이스태틱 OFDM 마이크로도플러 + 학습 분류**의 칸은
   Costa 의 저널판(모델만 있고 학습은 후속과제로 비움)까지 확인한 뒤에도 **비어 있다.**
5. **우리 첫 분류 실험은 계보의 «0세대» 자리에 있고, 재는 것도 다르다.**
   `classify_airframe.py` 는 스펙에서 계산한 빗살 템플릿을 맞춰 보는 **학습 파라미터 0개**의
   물리 정합기다(우리 커널 100 % · Sionna 94.64 % · 셔플 널 33.9/35.1 %). 문헌의 97 % 와
   **나란히 놓으면 안 된다** — 문헌은 실측 스펙트로그램 수천~수만 장에 잡음까지 얹은 «분류
   성능»이고, 우리는 무잡음 시뮬 자세 시계열 8192점에서 «**엔진이 무늬를 그리는가**»를 물어
   **분류 가능성의 상한**을 잰 것이다. ⭐**두 시뮬 엔진을 같은 잣대로 겨룬 편은 39편 중 0편** —
   이 축은 문헌에 대응물이 없고, 그래서 겨루는 것이 아니라 **눈금으로 쓴다.**

---

## 0. 회수 경위와 우리 기록과의 겹침

### 0-1. 이 문서가 어떻게 만들어졌나 (숨기지 않는다)

| 단계 | 누가 | 산출 | 상태 |
|---|---|---|---|
| 수집·중복제거 | 앞 라운드 수집기(3축 병렬) | `papers` **45편** | 완료 |
| 원문 대조 판정 | 앞 라운드 검증기 | `verdicts` **41건**(통과 39 · 불통과 2) | 완료 |
| 종합·집필 | — | — | ⛔**세션 한도로 중단** |
| 회수 + 종합(이 문서) | 이번 세션 | 본 문서 + `outputs/md_classification_dl_survey.json` | 완료 |

회수 파일은 저장소 안으로 옮겨 두었다 —
`prior_work/outputs/md_classification_dl_survey_recovered.json` (117,918 바이트, `papers` 45 ·
`verdicts` 41). 원본 위치는 스크래치패드의 `survey_recovered.json` 이다.

⭐**§3 의 표와 원장 JSON 은 손으로 두 번 적지 않았다** — 문서를 쓴 뒤
`prior_work/src/build_md_classification_dl_survey.py` 가 **이 문서의 §3 표를 되읽어**
`outputs/md_classification_dl_survey.json` 을 만든다. 표와 원장이 어긋날 수 없고, 표를 고치면
생성기를 다시 돌리면 된다. 생성기는 «표 39행 = 판정 통과 39편»을 **assert 로 검사**한다.

같은 날 남은 **축별 1차 초안 3편**이 `prior_work/` 에 있다 — `drone_md_dl_classification_survey.md`
(고전 뿌리·원조 CNN 축) · `sim2real_md_classification_survey.md`(합성학습 축) ·
`drone_md_classification_dl_survey.md`(패시브·서베이 체계 축). 이 문서가 **그 셋의 종합본**이고,
셋은 재료로 남긴다(폐기하지 않는다 — 축별 상세는 그쪽이 더 길다).

### 0-2. 이미 우리 기록에 있어 다시 조사하지 않은 것

| 우리 기록 | 겹치는 내용 | 이 문서의 처리 |
|---|---|---|
| `prior_work/passive_ofdm_dl_survey.md` (2026-08-11) | 패시브 조명원별 분류 사례 6편의 읽음 등급, Cao §4 반증(방송대역 RCS 로는 드론끼리 구분난), Kulpa IRS 2025 미확보, Czerkawski 는 **사람 행동**이라 수치 이전 금지 | 패시브 축은 **재조사하지 않고 인용**. §5-2 에 판정 공백으로 연결 |
| `prior_work/noise_modeling_survey.md` (2026-08-10) | 문헌의 SNR 정의는 거의 **표본당(pre-integration)**, Raval `10log10(A_r²/σ₀²)` · Malarvanan «single pulse» | §4-2 (6) 잡음 축 처방의 근거로 재사용 |
| `prior_work/rotor_randomness_survey.md` | 로터 rpm 산포·호버 rpm 근거 | 우리 템플릿 `f_flash = 날개수 × rpm/60` 의 스펙 출처 |
| `prior_work/sionna_sensing_survey.md` | Sionna 계열 센싱 논문 총람 | Li(ICCT 2025, Sionna RT 마이크로도플러)를 **새로 추가**한다 |
| `outputs/classify_airframe.json` · `outputs/refute_classify_airframe.json` | 우리 첫 분류 실험 원장과 반증 팔 | §4 의 우리 수치 전부 |

**결론: 새로 배울 것은 «누가 더 정확한가»가 아니라 «어떤 입력 표현을 쓰고, 어떻게 분할하고,
합성 데이터를 어디에 놓는가»다.**

---

## 1. 기법 계보 — 연도 흐름

### 1-1. 2013~2016 · 고전 특징 + 분류기 (딥러닝 이전)

**Molchanov 외 2014**(IJMWT 6(3-4):435–444, 회의판 EuRAD 2013)가 문제 설정의 원조다. X-band
9.5 GHz CW 실측에서 마이크로도플러 시그니처의 **상관행렬 고유쌍(eigenpair)** 을 특징으로 뽑아
SVM·나이브베이즈에 넣었고(저널판 92.3 %, 회의판 10-fold 비선형 SVM 95.39 %), ⭐**새(bird)를
처음부터 같은 문제에 넣었다** — 이 «드론 vs 새» 프레임이 이후 10년을 지배한다.

**Ritchie 외 2016**(IET RSN 11(1):116–124)은 **멀티스태틱**의 이득을 정량화했다. NetRAD
2.4 GHz 3노드(모노 1 + 바이 2, 기선 50 m)에서 스펙트로그램 SVD 특징과 도플러 센트로이드
특징을 뽑아 **노드별로 분류하고 투표**했더니 96.8~98 %, 모노 단독은 91~94 %. ⚠**전 노드
데이터를 한 분류기에 합치면 54~61 %로 추락한다** — 다중 수신의 이득은 «데이터를 합치기»가
아니라 «판정을 합치기»에서 온다는 경고다.

**Björklund 2018**(EuRAD)은 TVD(Time-Velocity Diagram)에서 물리 특징을 뽑아 **부스팅**으로
드론/새를 나눴다. 이 편이 바로 다음 해 딥러닝판의 기준선이 된다.

### 1-2. 2016 · 첫 딥러닝은 CNN 이 아니었다

**Mendis 외 2016**(MILCOM)이 드론 마이크로도플러에 심층망을 얹은 최초기 논문인데,
망은 **deep belief network(DBN)** 이고 입력도 스펙트로그램이 아니라 **스펙트럼 상관함수(SCF)**
다(2.4 GHz CW, 3종, >90 %). ⭐계보를 그릴 때 흔히 «2016 부터 CNN» 이라고 쓰지만 **틀렸다** —
2016 의 딥러닝은 DBN+SCF 였고, CNN+스펙트로그램 계보는 2017 부터다.

### 1-3. 2017~2020 · CNN 전이학습 (GoogLeNet·AlexNet·VGG)

**Kim 외 2017**(IEEE GRSL 14(1):38–42)이 계보의 문을 연다. **GoogLeNet** 에 마이크로도플러
스펙트로그램(MDS)과 CVD(케이던스-속도 다이어그램)를 **한 장으로 병합한 merged Doppler image**
를 먹여 Ku-band FMCW 실측에서 **89.3 → 94.7 %(+5.4 pp)**. 표현을 병합하면 이득이 난다는
이 분야의 첫 증거다.

**Rahman & Robertson 2020**(IET RSN 14(5))은 같은 GoogLeNet 전이학습으로 드론/새/클러터/잡음
4클래스 **~99 %**, 자체 설계 CNN 으로 검증 99.6 %/시험 94.4 %. 데이터는 같은 그룹의 K-band
24 GHz + W-band 94 GHz 캠페인이고, 그 물리 근거는 **Rahman & Robertson 2018**(Sci. Rep. 8:17396)
가 깔아 놓았다 — 드론 마이크로도플러는 몸체 대비 −20~−40 dB, 새는 0~−10 dB 에 4~6 Hz 날갯짓.

**Gérard 외 2020**(EUSIPCO)은 백본을 GoogLeNet 으로 **고정하고 입력 표현 5종**(원시 x(t)·장시간
가중 스펙트럼 WSP·켑스트럼 CP·STFT 스펙트로그램 SG·CVD)을 겨뤘다. 결론은 **긴 관측의 WSP 가
최적**(98.1 %), 그리고 ⭐**시험/학습을 촬영 날짜로 분리하지 않으면 정확도가 98~100 %로 부풀어
오른다**는 경고 — 이 분야에서 «분할 규약»을 명시적으로 문제 삼은 드문 편이다.

전이학습 갈래는 **DIAT-μSAT**(Kumawat 외, GRSL vol.19, 온라인 2021)에서 **VGG16 95 % /
VGG19 97 %** 기준선과 **공개 데이터셋 4,849장**으로 굳어지고, White 외 2023/24(TRS vol.2)의
**AlexNet**(conv 5층 동결·FC 만 학습)까지 이어진다.

### 1-4. 2020~2022 · 경량 스크래치 CNN — «작은 망으로 충분하다»

**Park(Junhyeong) 외 2020**(arXiv:2009.14422)이 방향을 튼다. conv 3층 + FC 1층,
**0.217 M 파라미터**(원문 217,125)짜리 light CNN 인데 Ku-band FMCW 5클래스에서 **97.14 %**.
⭐핵심은 망이 아니라 전처리다 — **망을 고정한 채 MDS 추출법만 A-SPC 로 바꿔 87.14 → 97.14 %
(+10 pp)**. 비교표의 GoogLeNet 행(6.8 M·89.3 %)은 Kim 2017 인용값이다.

**Park(Dongsuk) 외 2021**(Sensors 21(1):210)은 **ResNet-SP**(ResNet-18 을 채널 축소·팽창
컨볼루션으로 경량화)로 훈련 640 s→242 s, 정확도 79.88 → **83.39 %**. 입력을 **실수부·허수부
2채널 이미지**로 둔 규약이 이 편에서 나온다(정확도 수준이 낮은 것은 드론 3종에 **사람 활동
2종**(walking·sit-walking)을 섞은 5클래스이기 때문).

**DIAT-RadSATNet**(Kumawat 외 2022, IEEE TIM vol.71)은 **0.45 M** 전용 DCNN 으로 검출/분류
**97.1~97.3 %** — 전이학습 없이도 대형 백본과 대등하다는 것을 X-band CW 6클래스에서 보였다.

### 1-5. 2021~2023 · 합성 학습과 증강 (sim-to-real 의 태동)

**Raval 외 2021**(Drones 5(4):149)은 **전량 합성**(Martin–Mulgrew 블레이드 모델)으로 CNN 을
학습해 F1 0.816 ± 0.011 @ SNR 10 dB 를 냈고, **F1 vs SNR 곡선**이라는 보고 규약을 세웠다.
**Rojhani 외 2023**(IEEE TMTT 71(5))은 물리모델 파라미터를 흔들어 만든 **모델기반 증강**이
관행 증강을 이긴다고 보고했다(78.68 % vs 66.18 %) — ⚠단 섭동 크기 σ_P 를 **시험셋으로
튜닝**한 흔적이 있어 방법론은 따라 하면 안 된다. 입력이 스펙트로그램이 아니라
**77 GHz FMCW 레인지 프로파일 400점 벡터**인 것도 이 편의 특이점이다.

**White 외 2023/24**(IEEE TRS vol.2:167–179)가 sim-to-real 의 최상 선례다. 도심 L밴드 응시
레이더에서 **실측 학습 89.7 ± 0.5 %**, **반합성 학습 86.6 ± 0.5 %**(**−3.1 pp**). ⛔«합성만»이
아니라 **합성 표적 에코를 실측 배경 시계열에 더한** 반합성이고, 한 비행이 train/test 에
걸치지 않게 나눴다. 그 전신인 **White 외 2022**(RadarConf22)는 **실기 모터속도 로그**를
운동학 모델에 주입해 시뮬 충실도를 올린 편이다.

### 1-6. 2023~2024 · 어텐션과 표현 융합

**Dai 외 2023**(Measurement vol.222)의 **RCA-ResNeSt** — ResNeSt(residual split-attention)
백본에 CrossNorm/SelfNorm 과 coordinate attention 을 얹어 L밴드 응시 레이다 실측에서
UAV/새 **97.99 %**. **Chen 외 2024**(GRSL vol.21)는 **ResNet34** 로 마이크로도플러
스펙트로그램·CVD·켑스트럼 **3종 표현을 융합**해 >97 %(데이터 레벨 융합과 특징 레벨 융합을 비교).

### 1-7. 2025~2026 · 시퀀스 모델·트랜스포머·상태공간

- **Larrat & Sales 2025**(Sensors 25(3):721) — ⭐**이미지화를 버렸다.** 60 GHz mmWave 복소
  시계열(1000프레임 × 128윈도우 × 168특징, 진폭·위상 보존)을 **LSTM·GRU·Conv1D·Transformer**
  에 직접 넣어 겨루고, 진폭·위상·왜도·첨도를 결합한 **Multimodal Transformer** 를 제안했다.
  백색·임펄스·멀티패스 잡음에서 AUC ≈ 1.0, ⚠중꼬리(파레토) 잡음에서만 저하.
- **Czuba 2025**(arXiv:2512.00374) — **ViT-S-M**(ViT-Small 을 인코더 12→5층으로 줄임, 패치
  32×32). CNN 의 고정 해상도 제약을 피해 **적분시간이 다른 가변 크기 스펙트로그램**
  (384×384/768/1152, 세로 고정·가로 가변)을 그대로 분류해 **97.76 %**.
- **Xue 외 2025**(ICCCS) **DC-Former** — depth convolution(국소) + 트랜스포머 자기어텐션(전역).
  ⭐**5G NR 3.5 GHz·100 MHz 실측 + 시뮬** 에코로 UAV/새 96~98 %. 통신 파형 실측 에코를 딥러닝으로
  분류한 **유일 확인 사례**.
- **Luo(Y.) 외 2025**(ICC) **PinpuNet** — 비균질 2D 컨볼루션(시간축·주파수축 상관을 분리해 학습)
  + residual. 공개 데이터셋 LSS-FMCWR-1.0 6기종에서 4클래스 97.17 % / 5클래스 99.50 %.
- **Zhang & Song 2026**(Drones 10(4):265) — **Mamba 상태공간 백본**. L/K 듀얼밴드 스펙트로그램을
  패치 시퀀스로 만들고 상호학습·**대조학습 손실** + late fusion 으로 97.5 %.
- **Luo(H.) 외 2026 AirGuard**(arXiv:2603.13112, JSAC) — 0.15 M 이중분기 CNN 에 **cmD(중심화
  마이크로도플러) + HRRP** 를 각각 넣어 융합. 95.34/97.75 → **99.37 %**. 26 GHz OFDM ISAC
  **시뮬 전용** 237,600장. ⚠분할 규약 미기재 → 근접중복 누수 위험.
- **Luo(H.) 외 2026 Networked ISAC**(arXiv:2607.10319) — **Swin Transformer** 로 다중 기지국의
  시간-주파수 표현 3종을 융합, 4클래스 144만 샘플 시뮬 벤치마크에서 평균 97.82 %.
- **Kearney & Gurbuz 2026**(IEEE TAES 62:9875–9891) — **물리유도(physics-guided)**. CAD 시뮬만으로
  학습한 U-Net 시맨틱 분할(HERM 라인 마스크)을 GAN·분류기와 통합. Real→Low SINR 전이에서
  50.0 → 71.2 %(CAE + SS-GAN 합성훈련), 분할단을 붙이면 52.6 → 73.1 %.
- **Mustafa 외 2026**(arXiv:2604.12567) — ⭐**반동**. 딥러닝이 아니라 물리·통계 수제 특징
  10개 중 5개(사이드로브 에너지비·사이드로브 엔트로피·스펙트럼 엔트로피·시간 에너지 분산·
  시간 엔트로피) + SVM/랜덤포레스트. 소데이터(130건)에서 청정 0.916, −10 dB급 열화에서 RF F1
  0.831 — «작은 데이터면 고전이 강인하다»는 기준선.
- **Yerushalimov 외 2026 μDopplerTag**(arXiv:2601.08042) — 계보 밖의 갈래. 블레이드에 **공진
  전자기 스티커**를 붙여 인위적 마이크로도플러 코드를 새기고 경량 CNN 으로 43개 구성을 식별
  (SNR>9 dB 에서 ~99 %, 0 dB 에서 ~10 %로 붕괴). **협조적 식별**이라 비협조 표적엔 이전 불가.

### 1-8. 한 줄 요약 그림

```
2014 고전(고유쌍+SVM)  →  2016 DBN+SCF  →  2017 GoogLeNet 전이(+CVD 병합)
   →  2020 표현 비교(WSP)·전이학습 성숙(~99%)  →  2020~22 경량 스크래치 CNN(0.2~0.45M, 97%)
   →  2021~23 합성/증강(F1 0.816 · 반합성 −3.1pp · 모델기반 증강)
   →  2023~24 어텐션·표현 융합(ResNeSt 97.99 · ResNet34 융합 >97)
   →  2025~26 시퀀스/트랜스포머/Mamba(ViT 97.76 · DC-Former · Swin · Mamba 97.5)
        ‖ 그 옆으로 물리유도(Kearney)·고전 반동(Mustafa)·협조 태깅(μDopplerTag)
```

⚠**계보에서 빠진 칸이 있다** — «CNN-LSTM» 같은 **CNN+순환망 하이브리드는 검증 39편에 0편**이고,
**자기지도 사전학습(SimCLR·MAE 류)도 0편**이다(대조학습은 Zhang 의 **보조 손실**로만 등장).
§5-3 에 «못 찾았다»로 적는다.

---

## 2. 입력 표현 — 표준과 변주

세는 규칙을 먼저 밝힌다. 검증된 **분류 29편**을 «시간-주파수 면(스펙트로그램)을 어떻게
쓰는가»로 셋으로 나누면 — **그대로 망에 넣는다 20편** · **거기서 특징만 뽑는다 4편**
(Molchanov 의 상관행렬 고유쌍 · Ritchie 의 SVD·센트로이드 · Björklund 2018 의 TVD 물리특징 ·
Mustafa 의 수제 디스크립터) · **면을 아예 안 거친다 5편**(Mendis 의 SCF · Rojhani 의 레인지
프로파일 · Zhang(L.) 의 레인지-도플러 맵 · Larrat·Malarvanan 의 복소 시계열)이다.
⇒ **24/29 가 스펙트로그램 위에 서 있다.**

| 표현 | 쓴 편 | 메모 |
|---|---|---|
| **STFT 스펙트로그램(이미지)** | Kim · Rahman&Robertson · Gérard(SG) · Björklund 2019(TVD) · DIAT-μSAT · DIAT-RadSATNet · Dai · White · Czuba · Xue · PinpuNet · Zhang(Mamba) · Kearney · Raval · Park(A-SPC MDS) · Park(ResNet-SP) · Chen · AirGuard(cmD) · Networked ISAC(TF 스펙트럼 3종) · μDopplerTag | **사실상 표준** — 그대로 넣는 20편 |
| **복소 2채널(실수·허수)** | Park(ResNet-SP) · Gérard(1-D 입력) | 위상 정보를 버리지 않는 규약 |
| **표현 병합·융합** | Kim(MDS+CVD) · Chen(mD+CVD+켑스트럼) · AirGuard(cmD+HRRP) · Zhang(L/K 듀얼밴드) | ⭐이득이 확인된 유일한 «공짜 점수» |
| **스펙트로그램이 아닌 것** | Mendis(SCF) · Rojhani(레인지 프로파일 400점) · Zhang(L.)(레인지-도플러 맵) · Molchanov(상관행렬 고유쌍) · Ritchie(SVD·센트로이드 특징) | 소수파지만 계속 나온다 |
| **시계열 직행(이미지화 없음)** | Larrat(복소 시계열) · Malarvanan(복소 시계열) · μDopplerTag(스펙트로그램을 1D 로 언랩) | ⭐2024~26 에 생긴 갈래 — **우리 데이터와 형태가 같다** |
| **관측시간(적분시간)** | Gérard(길수록 유리, WSP) · Czuba(102.4/204.8/307.2 ms 가변) · White(20 timestep = 5.6 s) · Raval(0.3 s) | 창 길이는 성능의 1차 변수다 |

---

## 3. 큰 표 — 검증 통과 39편

읽는 법: **판정 통과분만** 싣는다. 정확도 칸의 ⭐/⚠ 는 §3-4 의 정정·단서로 연결된다.
표는 세 덩이로 나눴다 — 분류 실험이 있는 편(29) · 분류기 없는 물리/시뮬 앵커(5) · 서베이(5).

### 3-1. 분류 실험이 있는 논문 (29편)

| 논문 | 연도 | 기법(정확한 이름) | 입력 표현 | 데이터(실측/합성·레이다) | 정확도 | 링크 |
|---|---|---|---|---|---|---|
| Molchanov 외, *Classification of small UAVs and birds by micro-Doppler signatures* | 2014 | 딥러닝 아님 — 상관행렬 **고유쌍(eigenpair)** 특징 + 선형/비선형 SVM·나이브베이즈 | 몸체 도플러 보상·정렬한 mD 시그니처의 상관행렬 고유쌍(EVD/SVD) | 실측, X-band 9.5 GHz CW(Thales NL + TNO D-RACE), 11클래스(모형기·쿼드로터·헬기·정지 로터·새) | 저널판 **92.3 %**, 회의판 10-fold 비선형 SVM 95.39 % | https://doi.org/10.1017/S1759078714000282 |
| Mendis 외, *Deep learning based doppler radar for micro UAS detection and classification* | 2016 | **deep belief network(DBN)** — CNN 아님 | **스펙트럼 상관함수(SCF)** — 스펙트로그램 아님 | 실측, 2.4 GHz CW 도플러 레이다, 실험실 조건, 마이크로 UAS 3종 | **>90 %** ⚠(2017 확장판 ~97 % 는 원문 미확인) | https://doi.org/10.1109/MILCOM.2016.7795448 |
| Ritchie 외, *Multistatic micro-Doppler radar feature extraction … unloaded/loaded micro-drones* | 2016 | 딥러닝 아님 — diagonal-linear 판별분석·나이브베이즈·랜덤포레스트 + **노드별 분류 후 투표** | 스펙트로그램 SVD(U행렬 대각 통계) + 도플러/대역폭 센트로이드 특징 | 실측, NetRAD 2.4 GHz 3노드(모노1+바이2, 기선 50 m, PRF 5 kHz), 야외, DJI Phantom 2 Vision+ 페이로드 5클래스 | 센트로이드 96.8~98 % · SVD 92.8~96.6 % · 모노 단독 91~94 % ⚠**전 노드 합치면 54~61 %** | https://doi.org/10.1049/iet-rsn.2016.0063 |
| Kim 외, *Drone Classification Using CNN With Merged Doppler Images* | 2017 | **GoogLeNet** | **merged Doppler image** = MDS 스펙트로그램 + CVD 병합 | 실측 Ku-band FMCW, 드론 2종, 무향실 + 야외(50/100 m) | **94.7 %**(병합) vs 89.3 %(MDS 단독), 2기종 50/100 m 100 % | https://doi.org/10.1109/LGRS.2016.2624820 |
| Björklund, *Target Detection and Classification of Small Drones by Boosting on Radar Micro-Doppler* | 2018 | 딥러닝 아님 — **부스팅**(SVM 과 비교) | **TVD**(Time-Velocity Diagram)에서 뽑은 물리 특징 | 실측 드론·새 ⚠(레이다 대역·기종은 페이월로 미확인) | ⚠**초록에 수치 없음** | https://doi.org/10.23919/EuRAD.2018.8546569 |
| Björklund & Wadströmer, *Target Detection and Classification of Small Drones by Deep Learning on Radar Micro-Doppler* | 2019 | 딥러닝 분류기 ⚠**아키텍처명 초록에 없음**(페이월) | TVD | 2018 부스팅판과 **동일 실측 데이터** | ⚠수치 미공개 — «자신들의 부스팅·SVM 대비 향상»만 명시 | https://doi.org/10.1109/RADAR41533.2019.171294 |
| Gérard 외, *Micro-Doppler Signal Representation for Drone Classification by Deep Learning* | 2020 | **GoogLeNet**(백본 고정·표현 비교용, 1-D 입력엔 5×5→5×1 필터·실수+허수 2채널) | **표현 5종 비교** — x(t)·WSP(장시간 가중 스펙트럼)·켑스트럼·STFT·CVD | 실측(ONERA Medycis, S밴드 펄스), 드론 5클래스, 학습 36,730 / 시험 4,670 청크, **날짜 분리** | 청정 **WSP 98.1 %** / 잡음 92.7 % / 짧은 관측 93.7 % ⭐분리 안 하면 98~100 %로 부풀음 | https://doi.org/10.23919/Eusipco47968.2020.9287525 |
| Park(J.) 외, *Small Drone Classification with Light CNN and … A-SPC Technique* | 2020 | **경량 스크래치 CNN** — conv 3층 + FC 1층, **0.217 M**(217,125) | A-SPC 로 추출한 MDS 이미지 128×128×3 | 실측 Ku-band FMCW, 드론 3종 + 잡음 2 = 5클래스, 3,500장(+독립 시험셋 1,750장) | **97.14 %** ⭐전처리만 바꿔 87.14→97.14 % | https://arxiv.org/abs/2009.14422 |
| Rahman & Robertson, *Classification of drones and birds using CNN applied to radar micro-Doppler spectrogram images* | 2020 | **GoogLeNet 전이학습**(RGB) + 자체 설계 CNN(그레이스케일) | mD 스펙트로그램 이미지(RGB·그레이스케일) | 실측 **K-band 24 GHz + W-band 94 GHz**(94 GHz NIRAD 는 unseen 시험 전용), 4클래스(드론·새·클러터·잡음) 및 2클래스 | GoogLeNet **~99 %**, 자체 CNN 검증 99.6 % / 시험 94.4 % | https://doi.org/10.1049/iet-rsn.2019.0493 |
| Park(D.) 외, *Radar-Spectrogram-Based UAV Classification Using CNN* | 2021 | **ResNet-SP**(ResNet-18 경량화: 채널 축소·팽창 컨볼루션·그래디언트 클리핑) | STFT 스펙트로그램을 **실수부·허수부 2채널** 이미지로 | 실측 FMCW X-band(Ancortek SDR-KIT 980AD2), 5클래스 = 드론 3종(Metafly·Mavic Air 2·Parrot Disco) + 사람활동 2종(walking·sit-walking) | **83.39 %**(ResNet-18 79.88 %), 훈련 242 s vs 640 s | https://doi.org/10.3390/s21010210 |
| Raval 외, *Convolutional Neural Networks for Classification of Drones Using Radars* | 2021 | 자체 설계 CNN | STFT 스펙트로그램 | ⭐**전량 합성**(Martin–Mulgrew 블레이드 모델), X/W-band 시나리오, SNR 주입, 드론 5클래스 + 잡음 1클래스 | **F1 0.816 ± 0.011 @ SNR 10 dB**(X-band) ⚠X>W 우위는 저자 스스로 일반화 경계 | https://doi.org/10.3390/drones5040149 |
| Kumawat 외, *DIAT-μSAT: Small Aerial Targets' Micro-Doppler Signatures and Their Classification Using CNN* | 2022 | **VGG16 / VGG19 전이학습**(특징추출기) | CW 레이다 mD 시그니처 이미지 | 실측 X-band 10 GHz CW, ⭐**공개 데이터셋 DIAT-μSAT 4,849장**, 초록 열거 6항(2엽·3엽 단/장 로터·쿼드콥터·바이오닉버드·복합) | **VGG16 95 % / VGG19 97 %** | https://doi.org/10.1109/LGRS.2021.3102039 |
| Kumawat 외, *DIAT-RadSATNet — Lightweight DCNN … SUAV Detection and Classification* | 2022 | **DIAT-RadSATNet** — 자체 설계 경량 DCNN **0.45 M** | mD 스펙트로그램 | 실측 X-band 10 GHz CW, DIAT-μSAT 확장 6클래스 | ⚠초록은 «검출/분류 정확도가 **97.1~97.3 %** 범위» | https://doi.org/10.1109/TIM.2022.3188050 |
| Rojhani 외, *Model-Based Data Augmentation … Classification of Micro-Doppler Signatures Using FMCW Radar* | 2023 | 커스텀 CNN(Adam lr 1e-3) | ⭐**77 GHz FMCW 레인지 프로파일 400점 벡터**(스펙트로그램 아님) | 합성 학습 32,000×400(결정론적 후방산란 모델) + **실측 시험 136장**, 로터수 2클래스 | **78.68 %**(모델기반 증강) vs 66.18 %(관행 증강) ⚠σ_P 를 시험셋으로 튜닝 | https://ieeexplore.ieee.org/document/10004894 |
| Dai 외, *UAVs and birds classification using robust coordinate attention synergy residual split-attention network …* | 2023 | **RCA-ResNeSt** — ResNeSt(split-attention) + CrossNorm/SelfNorm + coordinate attention | SVD 클러터 제거 후 그레이스케일 mD 스펙트로그램 | 실측 **L-band 홀로그래픽 응시(staring) 레이다**, UAV 3종 + 새 2종 | **97.99 %** | https://doi.org/10.1016/j.measurement.2023.113692 |
| White 외, *Urban Bird-Drone Classification with Synthetic Micro-Doppler Spectrograms* | 2023 | **AlexNet 전이학습**(ImageNet, conv 5층 유지·FC 3층만 재학습, Bayesian optimization) | RGB 위색 STFT 스펙트로그램(20 timestep ≈ 5.6 s, 15 Hz 고역통과) | 실측 L밴드 응시레이다(도심) 학습 7,256장 + ⭐**반합성**(합성 표적 에코를 실측 배경 시계열에 합산, 큰 드론 2종만) | 실측 **89.7 ± 0.5 %** / 반합성 **86.6 ± 0.5 %**(−3.1 pp) | https://doi.org/10.1109/TRS.2023.3326317 |
| Chen 외, *UAV Classification Based on Deep Learning Fusion of Multidimensional UAV Micro-Doppler Image Features* | 2024 | **ResNet34** 기반 데이터-레벨/특징-레벨 융합 비교 | ⭐**mD 스펙트로그램 + CVD + 켑스트럼** 3종 융합 | FMCW 레이다 ⚠데이터 상세는 초록 수준만 검증 | **>97 %** | https://doi.org/10.1109/LGRS.2024.3371171 |
| Malarvanan, *Hybrid Quantum Neural Network Advantage for Radar-Based Drone Detection and Classification in Low SNR* | 2024 | CNN vs **하이브리드 양자 신경망(HQNN)** 비교 | Martin–Mulgrew **복소 시계열**(펄스당 SNR = 10log10 A_r²/σ_n²) | ⭐**합성 전용**, 실측 없음 | SNR 구간별 F1 절대수치 제시 — 고 SNR CNN 우세 / **저 SNR(−5 dB 이하) HQNN 우세** | https://arxiv.org/abs/2403.02080 |
| Zhang(L.) 외, *A Lightweight CNN-Based Method for Micro-Doppler Feature-Based UAV Detection and Classification* | 2025 | **RangeDopplerNet** — 경량 CNN + coordinate attention(임베디드 지향) | **레인지-도플러 맵** | FMCW 레이다 실측(드론·차량·보행자) | ⭐Type-1 **96.71 %** / Type-2 **98.08 %**, 모델 403 KB(MobileNetV2 대비 −97.04 %) | https://doi.org/10.3390/electronics14244831 |
| Larrat & Sales, *Classification of Flying Drones Using Millimeter-Wave Radar: … Algorithms Under Noisy Conditions* | 2025 | **LSTM·GRU·Conv1D·Transformer** 4종 비교 + **Multimodal Transformer**(진폭·위상·왜도·첨도 결합) | ⭐**복소 레이다 시계열 직접 입력**(1000프레임×128윈도우×168특징, 이미지화 없음) | 실측 60 GHz mmWave(Kang 외 2024 데이터셋 재사용), 3클래스(Mavic·Phantom 3 Pro·바이오닉버드), 백색·임펄스·파레토·멀티패스 잡음 주입 | Multimodal Transformer **AUC 1.0**(백색·임펄스·멀티패스) ⚠표준 Transformer 는 백색에서 0.92~0.98 | https://doi.org/10.3390/s25030721 |
| Xue 외, *DC-Former Network Empowered UAV and Bird Recognition Based on ISAC System* | 2025 | **DC-Former** — depth convolution + 트랜스포머 멀티헤드 자기어텐션 | STFT 시간-주파수 스펙트로그램 | ⭐**5G NR 3.5 GHz·100 MHz 실측 + 시뮬**, UAV vs 새 각 10,000장 | **96~98 %** | https://arxiv.org/abs/2604.02680 (§III-C 재인용) |
| Luo(Y.) 외, *PinpuNet: Towards ISAC-based Drone Monitoring by Learning Micro-Doppler Spectrum* | 2025 | **PinpuNet** — 비균질(inhomogeneous) 2D 컨볼루션 + residual | STFT mD 스펙트로그램 | 공개 데이터셋 **LSS-FMCWR-1.0**(FMCW 능동 실측, Journal of Radars 13(3):539–553, 2024), 6기종 | K밴드 4클래스 **97.17 %** / L밴드 5클래스 **99.50 %**, 스미어링 하 >91 % | https://arxiv.org/abs/2604.02680 (§III-C 재인용) |
| Czuba, *Vision Transformer for Classification of UAV and Helicopters Using Micro-Doppler Spectrograms in Surveillance Radar* | 2025 | **ViT-S-M** — ViT-Small 개조(인코더 12→5층, 패치 32×32) | ⭐**가변 크기** mD 스펙트로그램(적분 102.4/204.8/307.2 ms → 384×384/768/1152) + 개조 DT-CWT 잡음제거 | 실측 **C-band 감시 레이다**(Sola, 기계식 회전), 3클래스(Matrice 600 Pro·PZL SW-4·PZL W-3), 13,614장 | 시험 **97.76 %**(검증 97.61 %, 훈련 98.73 %) | https://arxiv.org/abs/2512.00374 |
| Zhang & Song, *A Classification Algorithm of UAV and Bird Target Based on L/K Dual-Band Micro-Doppler and Mamba* | 2026 | **Mamba 상태공간 백본** + 듀얼브랜치 패치 인코딩 + 상호학습·**대조학습 손실** + late fusion | **L/K 듀얼밴드** mD 스펙트로그램의 패치 시퀀스 | L/K 듀얼밴드 레이다 탐지 모델, UAV vs 새 ⚠규모 상세 없음 | **97.5 %** | https://doi.org/10.3390/drones10040265 |
| Luo(H.) 외, *AirGuard: UAV and Bird Recognition Scheme for ISAC System* | 2026 | 이중분기 융합 CNN(자체 설계 **0.15 M**) — 분기당 conv3×3 3층 + maxpool → concat → FC 2층 | ⭐**cmD(중심화 마이크로도플러) + HRRP** 이중 입력(각 3@256×256) | ⭐**시뮬 전용** — 26 GHz OFDM ISAC 에코 237,600장(운동모델 3600 × SNR 11단 × 6), UAV vs 새 | **99.37 %**(융합) / 97.75 %(cmD) / 95.34 %(HRRP) ⚠분할 규약 미기재 | https://arxiv.org/abs/2603.13112 |
| Luo(H.) 외, *Networked ISAC Enabled Target Recognition Towards Low-Altitude Economy* | 2026 | **Swin Transformer**(다중 스케일 특징 융합) | 다중 기지국 에코의 시간-주파수 스펙트럼 3종(속도분해능 우선·시간분해능 우선·속도전이) | ⭐**시뮬 전용** — 네트워크형 ISAC 1,440,000 샘플 공개 벤치마크, UAV·새·차량·보행자 4클래스 | ⭐본문 **평균 97.82 %**(3-BS·미지 서브타입, SNR 평균) — 초록엔 수치 없음 | https://arxiv.org/abs/2607.10319 |
| Mustafa 외, *Feature-Level Robustness of Physics-Guided Micro-Doppler Descriptors for classification of Drones and Birds* | 2026 | ⭐**딥러닝 아님** — 물리·통계 수제 특징(10개 분석 → 5개 선정) + SVM·랜덤포레스트 | 77 GHz FMCW 스펙트로그램에서 뽑은 특징 벡터(엔트로피·사이드로브 등) | 공개 77 GHz FMCW 실측 **130건·3클래스**(드론 44 / 새 56 / 반사체 19) + AWGN·위상잡음 열화 | 청정 평균 **0.916**, −10 dB급 열화에서 RF **F1 0.831** | https://arxiv.org/abs/2604.12567 |
| Kearney & Gurbuz, *Physics-Guided Deep Neural Networks for Radar-Based UAV Recognition in Different Environments With No Prior In Situ Data* | 2026 | **U-Net 시맨틱 분할(CAD 시뮬만으로 학습)** 을 GAN 판별기·분류기와 통합(SS-GAN 합성 + 분할단 부착 CAE) | 스펙트로그램 + **HERM 라인 시맨틱 분할 마스크** | 실측 **77–81 GHz FMCW**(TI AWR2243) 79녹화 → 6 s 395샘플 → 프루닝 333, UAV 5기체(Low-SINR 시험은 4기체) + CAD 시뮬 | Real→Low SINR **50.0 → 71.2 %**(CAE+SS-GAN) ⭐분할단 부착 시 52.6 → **73.1 %** ⚠저충실도 시뮬 단독 학습은 random guessing 수준 | https://doi.org/10.1109/TAES.2026.3685229 |
| Yerushalimov 외, *μDopplerTag: CNN-Based Drone Recognition via Cooperative Micro-Doppler Tagging* | 2026 | 경량 커스텀 CNN — conv 3층(32/64/128) + FC128 | 스펙트로그램 행렬을 **단일채널**로(원문은 «1D 언랩»이라 쓰지만 실제 연산은 2D conv) | 실측 S밴드 3.35 GHz CW — 무향실 **43 태그코드 × 3기록 × 10 s** + 야외 **7코드 × 10기록 × 15 s** | SNR>9 dB **~99 %**, 0 dB **~10 %(붕괴)** ⚠협조적(태그 부착) 식별 | https://arxiv.org/abs/2601.08042 |

### 3-2. 분류기 없는 물리·시뮬 앵커 (5편)

| 논문 | 연도 | 기법(정확한 이름) | 입력 표현 | 데이터(실측/합성·레이다) | 정확도 | 링크 |
|---|---|---|---|---|---|---|
| Rahman & Robertson, *Radar micro-Doppler signatures of drones and birds at K-band and W-band* | 2018 | 분류기 없음 — 시그니처 분석(2020 CNN 편의 물리 앵커) | STFT 스펙트로그램(블레이드 플래시·HERM 라인) | 실측 K-band 24 GHz FMCW + W-band 94 GHz 2기(T-220·NIRAD), Phantom 3·Inspire 1·S900 + 맹금류 4종(0.26~1.84 kg) | — (드론 mD 는 몸체 대비 **−20~−40 dB**, 새는 0~−10 dB·4~6 Hz 날갯짓, W-band 가 «일부 경우» 5~10 dB 유리) | https://doi.org/10.1038/s41598-018-35880-9 |
| White 외, *Multi-rotor Drone Micro-Doppler Simulation Incorporating Genuine Motor Speeds and Validation with L-band Staring Radar* | 2022 | 분류기 없음 — 시계열 반환 단순 모델 3종 | 합성 스펙트로그램(⭐**실기 모터속도 로그** 주입) | 합성 + 실측 L밴드 응시레이더 배경(합성 표적을 실측 배경에 주입) | — (시뮬·실측 스펙트로그램 정성 비교) | https://doi.org/10.1109/RadarConf2248738.2022.9764352 |
| Moore 외, *A new simulation methodology for generating accurate drone micro-Doppler with experimental validation* | 2024 | 분류기 없음(학습용 대량 합성 생성 «가능성»만 언급) | 3D CAD → 포인트클라우드 기반 합성 mD 스펙트로그램 | 합성 + 전용 검증 레이더 실측, 프로펠러 모양이 다른 3기종 | — ⭐**CAD 정밀도에 매우 민감, 레이저스캔 모델이 최상** | https://doi.org/10.1049/rsn2.12494 |
| Li 외, *Micro-Doppler Signature Simulation of Multirotor UAVs Using Ray Tracing* | 2025 | 분류 없음 — ⭐**Sionna RT 기반 시뮬레이션** | Sionna RT 시나리오의 CSI 에서 추출한 로터 유도 mD | ⚠합성 전용(초록 수준 확인), 6G ISAC 맥락, 전문 유료로 미열람 | — (반송파↑일수록 mD 확산) | https://doi.org/10.1109/ICCT67417.2025.11374154 |
| Costa 외, *Modeling Micro-Doppler Signature of Multi-Propeller Drones in Distributed ISAC* | 2025 | 분류 없음 — thin-wire 블레이드 모델의 **바이스태틱 + OFDM 확장**(ML 데이터셋 생성이 목적이라 자인, 학습은 후속과제) | 바이스태틱 OFDM 채널의 mD 시그니처 | 합성 + 실측 GT 검증(TU Ilmenau **BIRA** 측정 인프라), 멀티프로펠러 드론 | — (실측과의 유사성 검증) | https://doi.org/10.1109/JSTEAP.2025.3604407 |

### 3-3. 서베이·리뷰 (5편)

| 논문 | 연도 | 기법(정확한 이름) | 입력 표현 | 데이터(실측/합성·레이다) | 정확도 | 링크 |
|---|---|---|---|---|---|---|
| Hanif 외, *Micro-Doppler Based Target Recognition With Radars: A Review* | 2022 | 서베이 ⚠**본문 미확보**(유료·프리프린트 차단) | — | mD 표적 인식 전반(드론 포함) | — | https://ieeexplore.ieee.org/document/9673798 |
| Semenyuk 외, *Advance and Refinement: The Evolution of UAV Detection and Classification Technologies* | 2024 | 서베이 — 레이다 인식 **6기술 체계**: RCS 분석 · ML/딥러닝 · mD 분석 · 통계적 인식 · 스펙트로그램 · 다중주파수 | — | 레이다·RF·광학·음향 + 센서융합, 2020년 이후 | Table 1: RCS 통계인식 97.73 %(SNR 10 dB) · GA-BP 80 %(SNR 3 dB) · 하이브리드 DNN 의도분류 98.97 % | https://arxiv.org/abs/2409.05985 |
| Khawaja 외, *A Survey on Detection, Classification, and Tracking of UAVs using Radar and Communications Systems* | 2025 | 서베이 — **특징 축(RCS vs mD) × 알고리즘 축**(Table X: 15종 고전 분류기·CNN/딥러닝·SVM·나이브베이즈·스펙트로그램 패턴 분석) | — | 능동 / 패시브(§V-D 조명원별) / 드론 자체 RF(§VI) 를 절 단위 분리 | Table X 예: RCS 15분류기 SNR≥3 dB 100 % · 폴라리메트릭 NN 100 % · mD 딥러닝 98.8 % · SVM 95.39 % (⭐**전부 능동**) | https://arxiv.org/abs/2402.05909 |
| Tang 외, *UAV Detection with Passive Radar: Algorithms, Applications, and Challenges* | 2025 | 서베이 — **조명원별**(FM·DAB·DVB-T/T2·DTMB·GSM·LTE·5G·WiFi·위성) × **처리 단계별**(클러터 억제→RD맵→검출·추적) | — | 패시브 레이다 한정 | ⭐**분류 정확도 인용 0건** | https://doi.org/10.3390/drones9010076 |
| Bai 외, *MIMO OFDM-Enabled ISAC for Low-Altitude Non-Cooperative UAV Surveillance: A Survey* | 2026 | 서베이 — UAV 식별(§III-C) **3분 체계**: 신호처리(mD 파라미터 추정) · 학습 기반(PinpuNet·AirGuard·DC-Former) · 합성데이터 생성(Costa) | — | 통신 파형(MIMO OFDM ISAC) 한정 | Table VIII 이 논문×아키텍처×데이터×성적 총람 | https://arxiv.org/abs/2604.02680 |

### 3-4. 표에 붙는 정정·단서 (판정에서 회수한 것)

1. **Molchanov 2014** — 저널판 «~92 %»의 정확값은 **92.3 %**(비선형 SVM, 이중 샘플링레이트).
2. **Ritchie 2016** — 센트로이드 특징의 본문 명시 범위는 96.8~98 %(Table 2 셀은 96.5~98.2 %);
   모노 단독 91~94 %는 **센트로이드 한정**(SVD 특징의 모노 단독은 80.3~83.5 %); 합칠 때의 추락은
   센트로이드 56.5~61.1 % · SVD 54.1~58.8 %. 실험 드론은 **DJI Phantom 2 Vision+ 1대**(기종 다양성 없음).
3. **Raval 2021** — 분류기는 «5개 드론 클래스 + 잡음 1클래스»; **X>W 우위에 저자 스스로 단서**를
   달았다(*"likely due to the configuration of our neural network and may not be true in general"*).
4. **DIAT-μSAT** — 초록의 실험 클래스 열거는 **6항**(5클래스 + 2엽로터·바이오닉버드 **동시 운용**
   복합 1클래스, >97 %). DOI 온라인은 **2021-08**, 인쇄 vol.19 가 2022.
5. **DIAT-RadSATNet** — 초록은 «검출/분류 정확도가 97.1~97.3 % 범위»라고만 쓴다. «검출 97.1 /
   분류 97.3»의 1:1 대응은 본문 표 해석이고, «전이학습 없이»라는 표현도 초록엔 없다.
6. **Rojhani 2023** — «σ_P 를 시험셋으로 튜닝»은 **우리 판정의 해석**이다(원문이 스스로 결함이라
   부르지 않는다). 다만 근거 문장은 원문에 실재한다. 합성 학습 50 epochs vs 관행증강 100 epochs.
7. **White 2023/24** — 최종 서지는 **TRS vol.2:167–179**, 볼륨 연도는 **2024**(온라인 2023-10-20).
   원문 내부 불일치 있음: §III-C 는 5.6 s, §V-C 는 5.8 s.
8. **Larrat 2025** — 백색잡음 AUC 0.97~0.98 은 **표준 Transformer** 값이고 Mavic 0.92 가 빠져 있었다;
   **Multimodal Transformer** 는 백색·임펄스·멀티패스에서 AUC 1.0. 데이터는 자체 수집이 아니라
   **Kang 외(2024) 60 GHz 데이터셋 재사용**.
9. **Zhang(L.) Electronics 2025** — 정확도 «본문 미확인»은 해소됐다: **RangeDopplerNet Type-1
   96.71 % · Type-2 98.08 %**, 403 KB(초록의 «RangDopplerNet» 표기는 오타로 보인다).
10. **Networked ISAC 2026** — 초록엔 수치가 없지만 본문에 **평균 97.82 %**(클래스당 서브타입 10종).
    공저자 Guangyi Liu 소속은 칭화대가 아니라 **China Mobile Research Institute**.
11. **Kearney & Gurbuz TAES 2026** — ⭐**귀속 정정**: 50.0→71.2 %(+21.2 pp)는 SS-CAE 가 아니라
    **일반 CAE 분류기**(Table VII)의 결과이고, 개선 요인은 앞단 분할이 아니라 **SS-GAN 이 만든
    합성 훈련데이터**다. 분할단을 붙인 SS-CAE(Table VIII)는 **52.6 → 73.1 %**. 레이다는 원문 표기
    **77–81 GHz**(TI AWR2243). Low-SINR 시험은 대형 헥사콥터를 뺀 4기체.
12. **Mustafa 2026** — 특징 «10 vs 5» 상충은 둘 다 사실(10개 분석 → 5개 선정). 데이터는 드론·새만이
    아니라 **반사체 포함 3클래스·130건**.
13. **PinpuNet** — 데이터셋 LSS-FMCWR-1.0 의 게재 연도는 2023이 아니라 **2024**(Journal of Radars
    13(3):539–553, DOI 10.12000/JR23142)이고, 원문 표기 밴드는 **Ku+L**(재인용은 K 로 적는다) —
    사과-대-사과 비교 시 주의.
14. **DC-Former / PinpuNet** — 두 편의 1차 정보원인 Bai 서베이의 재인용 위치는 §IV-C 가 아니라
    **§III-C**(Table VIII). DC-Former 의 «모노스태틱»은 원문·서베이 어디에도 명시가 없다.
15. **Costa 2025** — «자체 채널사운더»의 정확한 표현은 **BIRA 측정 시스템**(TU Ilmenau). 회의판
    (arXiv:2401.14287)은 **제목·저자가 다르다**(*Modelling … Drone Propellers …*, 6인).
16. **Li ICCT 2025** — «합성 전용·실측 없음»은 **초록 수준에서만** 확인됐다(전문 미열람).
    «Sionna RT 로 멀티로터 mD 를 뽑은 첫 사례»의 «첫»은 **우리 평가**이지 원문 명제가 아니다.
17. **Moore 2024** — 결론부에 *"can be used to train a neural network … effectively"* 서술은 있으나
    **논문 안에 분류 실험·수치는 없다**.
18. **Tang 2025** — «플라스틱 블레이드 ×»는 **탐지 불가가 아니다**. 원문은 *weaker but still
    detectable* 이고, 약한 것은 **분류용 블레이드 mD** 다.
19. **Khawaja COMST** — 최종 권호 **vol.28 은 2026년 발행분**(2025는 억셉트·조기공개·arXiv v2 연도).
    Table X 의 98.8 % 행 알고리즘 칸 표기는 «Deep learning».
20. **Semenyuk 2024** — Crossref 에 이 제목 그대로의 IJCIP 게재 기록은 **없다**. 동일 저자진의
    게재판은 **개제**된 *"Advances in UAV detection: integrating multi-sensor systems and AI…"*,
    IJCIP vol.49:100744(2025). 인용 시 투고판/게재판을 구별할 것. GA-BP 80 %는 **SNR 3 dB 조건**.
21. **Czuba 2025** — «스크래치 학습»은 원문에 명시가 없다(«사전학습 언급 없음»으로 완화할 것).
    이미지 크기는 **384×384 / 384×768 / 384×1152**(세로 384 고정·가로 가변)가 원문 표기.
22. **Bai 2026** — «유일 문서»는 원문으로 증명 불가한 주장이라 «내가 찾은 범위에서 유일»로 완화.
    «통신 파형 학습분류 3편» 묶음에서 **PinpuNet 의 평가 데이터는 FMCW 레이다 에코**라 엄밀히는
    통신 파형 실험이 아니다 — 통신 파형 **실측은 DC-Former**, **합성은 AirGuard**.
23. **Hanif 2022** — ⚠**`prior_work/pdfs/jsen2022_hanif_microdoppler_review.pdf` 는 논문이 아니라
    1쪽짜리 Cloudflare 차단 페이지다**(*Enable JavaScript and cookies to continue*). 실물로 오인하지
    말고 파일을 교체해야 한다.

---

## 4. ⭐우리 실험에의 차용

### 4-1. 우리 첫 분류 실험은 무엇인가 (원장에서 그대로)

`benchmark/classify_airframe.py` → `outputs/classify_airframe.json`.

| 항목 | 값 |
|---|---|
| 질문 | «마이크로도플러 무늬(박자 빗살)만 보고 기체를 맞히나» |
| 기법 | ⭐**학습 파라미터 0개** — 스펙에서 계산한 빗살 템플릿과의 정합 점수 argmax |
| 템플릿 | `f_flash = 날개수 × 호버 rpm / 60` → mini5pro 183.33 / matrice4e 126.67 / s1000plus 148.90 Hz (⭐**데이터에 맞추지 않고 `src/drones.py` 스펙에서 계산**) |
| 입력 | 자세 시계열 8192점 → 겹치지 않는 **16창 × 512자세**, 창별 DC 제거 → hanning → 제로패딩 FFT(nfft 8192, 격자 2.405 Hz) |
| 점수 | 빗살 몫 = Σ P(f\_flash 의 정수배 ±8 Hz 안) / Σ P(주파수 크기 ≥ 8 Hz, 전체 AC) |
| 조건 | 3.5 GHz · PRF 19,700 Hz · 거리 15 m · 앙각 7개(0…−90°) · 3기체 · 엔진 2종(우리 커널 / Sionna spp 4e9·depth1) |
| **정확도** | ⭐**우리 커널 100 %(336/336)** · **Sionna 94.64 %** · 셔플 널 **33.93 % / 35.12 %**(우연 1/3) |
| 반증 팔 | `outputs/refute_classify_airframe.json` — 널 씨앗 5개 스윕(0.321~0.345) · 창 규약 3종 · 덮개율 정규화 · 템플릿 이동 · 위상무작위/원형이동 · **유효 표본 수** |

### 4-2. 계보 어디에 놓이는가

⭐**계보의 «0세대» 앞자리다** — 고전 특징+분류기(§1-1)보다도 앞이다. 이유는 하나: **학습이 없다.**
Molchanov 는 고유쌍 특징을 뽑아 **SVM 을 학습**했고 Björklund 는 TVD 특징으로 **부스팅을 학습**했다.
우리는 **스펙에서 계산한 주파수를 맞춰 보고 argmax** 를 취한다. 문헌에서 가장 가까운 이웃은 셋이다:

- **Mustafa 외 2026** — 딥러닝이 아니라 물리·통계 수제 특징 + SVM/RF. **소데이터 체제의 강인한
  기준선**이라는 자리매김이 우리와 같다(다만 그들도 분류기는 학습한다).
- **Björklund 2018** — TVD 물리 특징 + 부스팅. 딥러닝판(2019)이 같은 데이터에서 이겼다는 사실이,
  우리가 다음에 무엇을 해야 하는지 그대로 말해 준다.
- **Vorobev 2019(DVB-T2)** — 로터 회전수 도플러의 **정성 구분**. 사실상 «머릿속 템플릿 정합»이라
  기법상 우리와 가장 닮았다. ⚠단 이 편은 §5-2 의 미검증 칸에 있다.

그리고 우리 템플릿이 **데이터가 아니라 스펙에서 온다**는 점에서, 우리는 2021~2026 의
**물리 유도(physics-guided)** 갈래(Raval 의 합성 전용 · Kearney 의 물리 사전 · Mustafa 의 물리
디스크립터)와 같은 열에 선다. **«물리로 세우고, 데이터로 확인한다»가 우리 축이다.**

### 4-3. 다음 단계로 차용할 것 (상류부터)

| 순서 | 차용할 것 | 문헌 근거 | 우리에게 왜 |
|---|---|---|---|
| ① | **입력 표현을 먼저 승격** — 자세 시계열 → STFT 스펙트로그램(표준) + **CVD 병합** | Kim +5.4 pp · Park(A-SPC) **+10 pp**(망 고정) · Chen 3종 융합 >97 % | ⭐**표현 교체가 백본 교체보다 이득이 크다**는 것이 이 분야의 반복된 교훈이다. 우리는 `md_mapstyle.flash_spec` 규약이 이미 있으니 그 위에 얹으면 된다 |
| ② | **경량 스크래치 CNN 부터**(0.15~0.5 M) — ImageNet 전이 아님 | Park 0.217 M 97.14 % · DIAT-RadSATNet 0.45 M 97.3 % · AirGuard 0.15 M 99.37 % | 전이학습(GoogLeNet/AlexNet/VGG)은 **실측이 적을 때의 처방**이다. 우리는 합성이 대량이라 필요가 낮고, ImageNet RGB 통계와 우리 스펙트로그램은 애초에 다르다 |
| ③ | **시계열 분기도 같이** — 이미지화 없이 Conv1D/GRU/LSTM/Transformer 비교 | Larrat 2025(복소 시계열 직행, 4종 비교) · μDopplerTag(1D 언랩) | ⭐우리 원장이 **원래 복소 시계열**이다. 이미지로 굽지 않고 바로 넣는 경로가 **가장 싸고**, 문헌에 규약도 이미 있다 |
| ④ | **듀얼밴드 late fusion** | Zhang & Song 2026(L/K 듀얼밴드 Mamba 97.5 %) | 우리는 이미 여러 반송파를 돌린다 — 밴드를 **합쳐 한 장으로 만들지 말고**, 분기별로 판정한 뒤 융합하는 것이 Ritchie 의 «판정을 합쳐라» 교훈과도 맞는다 |
| ⑤ | **분할 규약을 먼저 못 박기** | Gérard(날짜 분리 안 하면 98~100 % 부풀음) · White(한 비행이 train/test 에 안 걸치게) · ⚠AirGuard(분할 미기재 → 누수 위험) | 우리 판은 **한 시계열의 16 창이 강하게 상관**되어 있다(§4-4). 창 단위로 나누면 **자동으로 새는 분할**이 된다 — 시계열/앙각/씨앗 단위로 나눠야 한다 |
| ⑥ | **잡음 축을 곡선으로** | Raval(F1 vs SNR 규약) · Larrat(백색·임펄스·파레토·멀티패스 4종) · Malarvanan(펄스당 SNR 정의) | 우리 `noise_modeling_survey.md` 가 이미 **표본당 SNR** 규약을 확정했다. 지금 원장은 **무잡음**이라 문헌과 같은 층위의 그림이 아직 없다 |
| ⑦ | **새(bird) 클래스** | Molchanov 2014 이후 거의 전편 | 우리 3클래스는 전부 회전익이다. 문헌이 10년째 푸는 «드론 vs 새»가 우리 판엔 없다 — 넣기 전엔 **난이도 비교 자체가 성립하지 않는다** |

### 4-4. ⚠사과-대-사과 — 우리 100 % 와 문헌 97 % 를 나란히 놓으면 안 되는 이유

| 축 | 문헌 표준 | 우리 첫 실험 |
|---|---|---|
| 데이터 출처 | **실측** 레이다 에코(X/Ku/K/W/L/C/60 GHz) | **시뮬** 자세 시계열(엔진 2종, 3.5 GHz) |
| 입력 | STFT 스펙트로그램 이미지 **수천~수만 장** | 8192 자세 → 16창×512 → 빗살 몫 **스칼라 3개** |
| 클래스 | 3~6(새·클러터·사람 포함) | **3 기체**(전부 회전익, 새 없음) |
| 우연 수준 | 1/5 ~ 1/6 | **1/3** — 같은 정확도라도 난이도가 다르다 |
| 표본 | 비행/날짜 단위 분리, 수천~수만 | 336 창이지만 ⭐**실질 독립 단위는 엔진당 21 시계열**(3기체×7앙각). 같은 시계열의 16 창은 강하게 상관 — 우리 커널은 21/21, Sionna 는 19/21 이 만장일치(`refute…json::G`) |
| 학습 | 있음(수백 epoch) | **없음**(학습 파라미터 0) → 일반화 주장 자체가 성립 안 함 |
| 잡음 | 주입 + SNR 스윕 | **무잡음 원장** |
| 견고성 | 잡음·저SINR·도메인 이동 | 창 256 으로 줄이면 88.2/85.1 %, 템플릿을 +10 Hz 밀면 65.2/78.9 % |

⇒ **우리 100 % 는 «분류를 잘한다»가 아니라 «이 조건에서 세 기체가 완전히 분리된다»는 뜻이다.**

### 4-5. ⭐우리 데이터의 특이점 — «엔진이 무늬를 그리는가»

우리 두 팔은 **같은 기체·같은 앙각·같은 창 규약·같은 템플릿**으로 돌렸다. 그러므로
**우리 커널 100 % 와 Sionna 94.64 % 의 차이는 분류기 성능 차가 아니라 엔진이 남긴 빗살 구조의
차이**다. 이 수는 분류 정확도가 아니라 ⭐**분류 가능성의 상한** — 무잡음·무학습·시뮬이라는
가장 유리한 조건에서 «무늬가 얼마나 뚜렷하게 남았나»의 눈금이다.

**상한이라서 오히려 쓸모가 있다.** 상한이 무너지는 지점이 곧 무늬의 두께이기 때문이다:

- 창을 512 → 256 으로 줄이면 100 → **88.2 %**(우리) · 94.6 → **85.1 %**(Sionna) — 짧은 관측에서
  먼저 무너진다(Gérard 의 «긴 관측이 유리»와 방향이 같다).
- 템플릿을 +5/+10 Hz 밀면 74.7/65.2 %(우리) · 89.3/78.9 %(Sionna) — 빗살이 **주파수에 얼마나
  날카롭게 걸려 있나**의 측정이다.
- Sionna 팔은 **0° 앙각에서만 72.9 %** 로 떨어진다(다른 앙각은 100 %) — 엔진 차이가 특정 기하에
  몰려 있다는 뜻이고, 이것이 «어디를 고쳐야 하나»의 좌표다.
- 위상만 무작위로 만들면(|FFT| 보존) 100 %/95.2 % 로 유지되고, 순서를 섞으면 33.9 % 로 붕괴한다 —
  ⭐**널이 우연으로 떨어지는 기전이 «백색화»라는 저자 주장이 실제로 선다.**

⭐**문헌에 이 축의 대응물이 없다.** 검증 39편 중 **두 시뮬레이션 엔진을 같은 분류기로 겨룬 편은
0편**이다. 가장 가까운 이웃도 성격이 다르다 — Moore 2024 는 **CAD 정밀도 → 시뮬/실측 일치**를
보았지 분류기를 태우지 않았고, White 2022 는 모터속도 로그로 충실도를 올렸지만 겨루기가 아니다.
그리고 **Kearney & Gurbuz 2026 이 정확히 반대편 경고**다 — «저충실도 시뮬 단독 학습은 random
guessing 을 못 넘는다». ⇒ ⛔**우리 100 % 를 «실측에서도 맞힌다»로 읽으면 문헌이 이미 반증해
놓은 주장을 하는 것이다.** 우리 수는 **엔진 비교의 눈금**으로만 쓴다.

---

## 5. 못 찾았다 · 검증 실패 (정직 섹션)

### 5-1. 판정 «불통과» 2건 — 본표에서 뺐다

**① IEEE Xplore 11101447, *Radar-Based UAV Classification: A Micro-Doppler and Deep Learning
Approach*(2025)** — ⛔**검색엔진 요약이 두 논문을 섞은 오염 사례.** 수집 당시 기록은 «VGG16 95 % /
VGG19 97 %, CW X밴드 10 GHz 자체 실측 4,849장·5클래스»였는데, Crossref·OpenAlex·Semantic Scholar
3중 대조 결과:

- 실체는 **Devesh Kaushal 단독, 2025 EAIC**(International Conference on Electronics, AI and
  Computing, Jalandhar, 2025-06-05~07, pp.1–6, DOI 10.1109/EAIC66483.2025.11101447).
- 기법은 VGG 전이학습이 **아니라** 커스텀 CNN vs **파인튜닝 EfficientNetB3**.
- 정확도는 커스텀 CNN **91.30 %**, EfficientNetB3 **97.10 %(테스트) / 97.74 %(검증)**.
- 데이터는 자체 실측이 아니라 **기존 DIAT(-μSAT) 데이터셋**, 클래스는 5종이 아니라 **6종**.
- ⭐«VGG16 95 % / VGG19 97 % · CW 10 GHz · 4,849장»의 **올바른 인용처는 Kumawat 외, DIAT-μSAT,
  IEEE GRSL(DOI 10.1109/LGRS.2021.3102039)** 이다(본표 3-1 에 그 편으로 실려 있다).

⇒ 본표에서 제외한다. EfficientNetB3 전이학습 사례로 인용하는 것은 가능하지만, 이번 라운드에서
확인한 것은 **OpenAlex 초록 색인까지**다(IEEE 원문 렌더는 차단됨).

**② IEEE Xplore 11031708, *Semantic Segmentation Guided RF Micro-Doppler Synthesis and UAV
Classification in Low SINR*(2025, 학회판)** — 확장 저널판이 실재하지만 **제목이 다르다**
(*Physics-Guided Deep Neural Networks…*, TAES 62:9875–9891, DOI 10.1109/TAES.2026.3685229 —
본표에 그 편으로 실려 있다). 또 **«SS-CAE»라는 명칭이 두 판 초록 어디에도 없고**(학회판 초록은
SS-GAN·SS-DNN), **+21.2 pp 는 학회판 수치가 아니다**(학회판 초록의 개선폭 서술은 «8 %»).
⇒ 학회판은 본표에서 빼고 저널판만 싣는다. 두 판을 같은 것으로 인용하면 안 된다.

### 5-2. ⚠판정 자체가 없는 4편 — 그리고 그 공백이 결론을 흔든다

수집은 됐는데 **원문 검증 라운드가 닿기 전에 세션이 끊겼다.** 본표에 넣지 않는다.

| 논문 | 왜 중요한가 | 지금 아는 것 |
|---|---|---|
| Huizing 외(TNO), *Deep Learning for Classification of Mini-UAVs Using Micro-Doppler Spectrograms in Cognitive Radar*, IEEE AESM 34(11):46–56, 2019 | 미니 UAV mD 딥러닝의 **표준 인용처**(피인용 100+) | 망 이름·훈련 구성 미확정, «95 % @ 0.2 s 창»은 **2차 요약** |
| Vorobev 외, *Experimental DVB-T2 Passive Radar Signatures of Small UAVs*, SPSympo 2019, pp.67–70 | ⭐**패시브 조명원 분류**의 최초급 사례 | 학습 분류기 아님(정성 구분). ⚠«660 MHz»는 666 MHz 오기 가능성, «4기체·750~900 m»는 Demissie 의 2차 서술(`passive_ofdm_dl_survey.md` T5·T6) |
| Cao 외, *A Novel Recognition-Before-Tracking Method … in Passive Radars*, Appl. Sci. 15(18):9957, 2025 | ⭐**패시브 실측 + 인식기 + 혼동행렬**까지 간 유일 확인 게재 사례 | **딥러닝 아님**(biased-RCS 20차원 특징 + NBV 유사도), ACRR 85.16 %, Phantom 4 행은 **합성**. §4 에 «방송대역 RCS 로는 드론끼리 구분난» 자인 → 우리를 겨눈 반증(R1). 이번 라운드에서 **서지 실재만** Crossref 로 확인(§6) — 내용은 `passive_ofdm_dl_survey.md` 의 `[원문]` 판정에 의존 |
| Kulpa·Malanowski·Bączyk, *Passive Radar for Drone Detection and Classification*, IRS 2025 | 제목이 그대로 «패시브 + 분류» | ⛔**조명원·기종수·정확도·실측 규모 전부 미상**, «분류»가 학습형인지 특징 관찰인지도 모름. **이 편으로 문장을 세우면 안 된다** |

⭐**이 공백이 TL;DR 4 를 흔든다.** 본표만 보면 «패시브 분류 0편»인데, 정확히 말하면
**패시브 후보가 전부 미검증 칸에 몰려 있다.** 다만 앞 조사의 판정에 따르면 셋 다 **딥러닝이
아니므로**, «패시브 + **딥러닝** 분류 0편»이라는 문장은 두 칸을 합쳐도 살아남는다.

### 5-3. 조사에서 아예 안 나온 계열 (검증 39편 기준)

- ⛔**CNN-LSTM / CRNN 하이브리드 0편.** 과제 지문이 계보 항목으로 지목했지만 **검증 집합에
  없다.** 시계열 결합은 Larrat 의 «LSTM·GRU·Conv1D·Transformer 4종 **병렬 비교**»로만 나타나고,
  CNN 앞단 + 순환망 뒷단을 이어 붙인 편은 못 찾았다. ⇒ 계보 그림에서 이 칸은 **비워 둔다.**
- ⛔**자기지도 사전학습(SimCLR·MAE·MoCo 류) 0편.** 대조학습은 Zhang & Song 2026 의 **보조 손실**
  로만 등장한다(사전학습이 아니다).
- ⛔**패시브(방송·셀룰러 조명원) 에코 + 딥러닝 0편**(§5-2 의 단서 포함).
- ⛔**바이스태틱 마이크로도플러 + 학습 분류 0편.** Costa 2025 는 모델만 세우고 학습은 후속과제로
  비웠다. ⭐**여기가 우리 자리다.**
- ⛔**레이트레이싱(Sionna 포함) 합성 데이터로 분류망을 학습한 편 0편.** Li 2025 는 Sionna RT 로
  mD 를 뽑았을 뿐 분류가 없다.
- ⛔**두 시뮬레이션 엔진을 같은 분류기로 겨룬 편 0편**(§4-5).
- **공개 벤치마크는 둘뿐** — DIAT-μSAT(X-band CW)와 LSS-FMCWR-1.0(FMCW, Ku+L). 둘 다 **능동**이고,
  **공개 코드 저장소는 이번 조사에서 확인하지 않았다.**
- **수치를 못 얻은 편** — Björklund 2018(초록에 수치 없음) · Björklund 2019(미공개) ·
  Hanif 2022(본문 미확보) · Li 2025(전문 유료).
- **본문을 못 본 편(초록·2차만)** — Björklund 2018/2019 · Chen 2024 · Xue(DC-Former) ·
  Luo(PinpuNet) · Li(ICCT) · Hanif. ⇒ 이 편들의 숫자를 우리 표에 **그대로 옮겨 쓰면 안 된다.**
- **언어권 공백** — 러시아어권·폴란드어권·중국어권 회의록(SPSympo · IRS · CIE Radar ·
  Journal of Radars 원문)을 목차 단위로 훑지 않았다.
- **방법론 공백** — 분류기의 **오검출/오분류 비용**(운용 관점 Pfa)이나 **개방집합(open-set) 인식**
  을 다룬 편을 못 찾았다. Networked ISAC 의 «미지 서브타입 일반화»가 가장 가깝다.

### 5-4. 이 문서 자체의 한계

- §3 의 «검증 통과»는 **앞 라운드 검증자의 판정**이다. 내가 다시 연 것은 §6 의 7건뿐이다.
- 회수 JSON 은 판정 결과만 담고 **검증에 쓴 원문 캐시는 담지 않았다** — 재검증하려면 다시 열어야
  한다(로컬 PDF 8편은 `prior_work/pdfs/` 에 있고, 그중 **1편은 차단 페이지**다. §3-4 주23).
- 정확도 칸의 단위가 편마다 다르다(정확도 · F1 · AUC · ACRR). **한 열에 있다고 같은 잣대가
  아니다.**

---

## 6. 이번 라운드에 내가 직접 연 링크 (표본 7건)

| # | URL | 확인한 것 | 결과 |
|---|---|---|---|
| 1 | `https://api.crossref.org/works/10.1109/LGRS.2016.2624820` | Kim 외 GRSL 서지 | ✅ 제목·저자 3인·GRSL·2017·vol.14·38–42 일치 |
| 2 | `https://arxiv.org/abs/2009.14422` | Park(J.) 초록 | ✅ 제목·저자 3인·2020-09-30, 초록에 «light CNN»·«A-SPC»·**97.14 %**·«10 % 향상» 실재 |
| 3 | `https://api.crossref.org/works/10.3390/app15189957` | Cao 외 서지(§5-2 미검증 4편 중 1편) | ✅ 제목·저자 5인·Applied Sciences·15(18)·article 9957·2025 **실재**(내용은 미검증) |
| 4 | `https://arxiv.org/abs/2603.13112` | AirGuard 초록 | ✅ 제목·저자 6인·2026-03-13, 초록에 «cmD spectrum»·«HRRP»·이중입력 CNN 실재. ⚠**99.37 % 는 초록에 없다**(본문 수치) |
| 5 | `https://api.crossref.org/works/10.1109/ICCT67417.2025.11374154` | Li 외(Sionna RT) 서지 | ✅ 제목·저자 6인·2025 IEEE 25th ICCT·IEEE 일치 |
| 6 | `https://api.crossref.org/works/10.1109/TAES.2026.3685229` | Kearney & Gurbuz 저널판 서지 | ✅ 제목·저자 2인·TAES·vol.62·9875–9891·2026 — **학회판과 제목이 다르다는 §5-1 ② 판정 확인** |
| 7 | `https://api.crossref.org/works/10.1109/JSTEAP.2025.3604407` | Costa 외 저널판 서지 | ✅ 제목·저자 7인(Engelhardt 포함)·JSTEAP·1(1)·208–222·2025 — **회의판 6인과 다르다는 §3-4 15 확인** |

---

## 7. 다음에 할 것 (이 조사가 남기는 숙제)

1. ⭐**입력 표현 승격 실험** — 같은 원장으로 (a) 현행 빗살 정합 (b) STFT 스펙트로그램 + 경량 CNN
   (c) 시계열 직행(Conv1D/GRU) 셋을 **같은 분할 규약**으로 겨룬다. 기대 산출은 정확도가 아니라
   **셋의 상한이 어디서 갈리는가**.
2. **분할 규약 확정** — 창 단위 분할 금지. 시계열/앙각/씨앗 단위. Gérard·White 를 근거로 문서에 박는다.
3. **잡음 축 연결** — `noise_modeling_survey.md` 의 표본당 SNR 규약으로 F1 vs SNR 곡선(Raval 규약)을
   그린다. 지금 원장은 무잡음이라 문헌과 같은 층위의 그림이 아직 없다.
4. **미검증 4편 정산** — 특히 Kulpa IRS 2025 원문(패시브+분류 반증의 정점)과 Huizing 2019.
5. **`prior_work/pdfs/jsen2022_hanif_microdoppler_review.pdf` 교체** — 지금 파일은 차단 페이지다.
6. **바이스태틱 칸 선점** — Costa 저널판이 «학습은 후속과제»로 비워 둔 자리가 우리 자리다.
   차용할 것은 그의 thin-wire + OFDM 바이스태틱 모델, 우리가 더할 것은 **학습 분류 + 두 엔진 눈금**.
