# 딥러닝 파이프라인의 탑티어 뒷받침 — 축별 앵커 31편 (2026-08-16)

> **사용자 지시(2026-08-16)**: *«딥러닝 프레임워크는 웬만하면 **탑티어 논문**을 토대로 했으면 좋겠다»*
>
> **정직한 진단.** `docs/DL_PIPELINE.md` 의 근거는 두 층이다. 방법론 층(누수·검정)은
> 이미 탑급이 받치고 있었지만, 응용 층(드론 마이크로도플러)은 분야가 작아서
> EUSIPCO·IET RSN·RadarConf·MDPI·arXiv 가 섞여 있다. 응용 결과 자체는 그 분야 학술지에만
> 있으므로 **그 인용은 그대로 유지**하고, 대신 **설계 선택마다 «같은 원리를 상위
> 학술지·학회가 확립한 논문»을 옆에 단다** — 그 목록이 이 문서다.
>
> **탑티어 기준**: IEEE TAES·TGRS·TSP·JSTSP·Proc. IEEE / NeurIPS·ICML·ICLR·CVPR /
> JMLR·Patterns·Science·Nature 계열.
>
> **전부 원문 확인을 거쳤다(2026-08-16 검증 라운드).** JMLR·arXiv·NeurIPS
> proceedings·CVF·OpenReview 는 원문 페이지를 직접 열어 초록을 대조했고, IEEE·Nature·
> Science·Patterns 는 DOI 조회(Semantic Scholar)로 서지+초록을 확인했다. 수치를 옮겨 오는
> 4건(DivNet 정확도 · Erol 체질 수치 · Adam 기본 lr · Seyfioglu 2018 비교군)은 **PDF 전문을
> 내려받아 축자 대조**했다. 검증에서 살아남지 못한 후보는 0편이지만, **문구를 고쳐야만 쓸 수
> 있는 것 1건과 표기 주의 3건**이 있다 — §7·§8 에 적었다.
>
> 설계 문서 쪽 대응표는 `docs/DL_PIPELINE.md` **부록 A-2**. 어긋나면 이 문서가 아니라
> 설계 문서(원장)가 이긴다.

---

## 0. 한눈에 — 축별 표

관계 표기: **지지** = 우리 선택과 같은 원리를 확립 · **⚠어긋남** = 우리 선택과 긴장 관계
(맞춰 고치지 않고 원장에 남긴다) · **⚠표기** = 인용 문구를 조심해야 함.

### ④ 표현 (1편)

| 논문 | 어디 | 우리 설계의 어느 자리 | 관계 |
|---|---|---|---|
| Chen 외 2006 | IEEE TAES 42(1) | R1(시간-주파수 dB 맵) = 문헌 표준 + 수식 합성 커널 접근 자체(§4-1) | 지지 · ⚠표기(§8-③) |

### ⑤ 모델 사다리 (6편)

| 논문 | 어디 | 우리 설계의 어느 자리 | 관계 |
|---|---|---|---|
| Kim & Ling 2009 | IEEE TGRS 47(5) | L0″(손 특징+고전 분류기) 관행 선 · M3 중단 규칙의 비교 계보(§5·§10) | 지지 |
| Chen 외(A-ConvNets) 2016 | IEEE TGRS 54(8) | L1 경량 스크래치 CNN · «작은 망부터» 순서(§5-0) | 지지 |
| Seyfioglu 외 2018 | IEEE TAES 54(4) | L1 대조군(4층 CNN) · 소데이터에서 초기화의 힘(§5) | 지지 · **⚠표기(§8-①)** |
| Seyfioglu 외(DivNet) 2019 | IEEE TAES 55(5) | L3′(합성 사전학습→실측 미세조정) · §9-3 분량 행 · 데이터량 곡선(§8-2) | 지지 |
| Brooks 외 2019 | NeurIPS 2019 | L6 공분산(SPD) 얇은 데이터 대조군(§5) — 실험 자체가 레이다 드론 데이터 | 지지 · ⭐인용 승급 권고 |
| LeCun 외(LeNet) 1998 | Proc. IEEE 86(11) | CNN 이라는 선택 자체 · L2 전역평균풀링=이동 불변 · «CNN 은 텍스처 기계» 진단(§4-1·§5) | 지지 |

### ⑥ 학습 절차·증강 (10편)

| 논문 | 어디 | 우리 설계의 어느 자리 | 관계 |
|---|---|---|---|
| Kingma & Ba(Adam) 2015 | ICLR 2015 | §6-1 «Adam 을 쓴다»는 선택의 원 논문 | 지지 · ⚠원문 기본 lr 은 1e-3 |
| Caruana 외 2000 | NeurIPS 2000 | §6-1 조기종료를 1차 정칙화로 — 사다리 전체의 공통 안전장치 | 지지 |
| Chen·Dobriban·Lee 2020 | JMLR 21(245) | §6-2 허용/금지 목록의 이론 틀(분포 보존 변환만 이득) | 지지 |
| Balestriero 외 2022 | NeurIPS 2022 | §6-2 SpecAugment(주파수 마스킹) 금지의 실증 근거 | 지지 |
| Yosinski 외 2014 | NeurIPS 2014 | L3·L3′ 전이+미세조정 기본값(§5·§9-3) | 지지 |
| Raghu 외(Transfusion) 2019 | NeurIPS 2019 | L3 ImageNet 전이의 기대 이득(+8~16 %p) | **⚠부분 어긋남(§7-③)** |
| Srivastava 외(Dropout) 2014 | JMLR 15(56) | §6-1 에 **빈칸** — dropout·weight decay 언급 0회 | **⚠빈칸(§7-④)** |
| Loshchilov & Hutter(AdamW) 2019 | ICLR 2019 | §6-1 의 AdamW 배제 결정 | **⚠어긋남(§7-①)** |
| Wilson 외 2017 | NeurIPS 2017 | §6-1 의 Adam 채택 | **⚠어긋남(§7-②)** |
| Erol 외 2020 | IEEE TAES 56(4) | §6-2 금지 목록 + 물리 체질(sifting) 게이트 | 지지 · **⚠표기(§8-②)** |

### ⑦ 평가·통계 (6편)

| 논문 | 어디 | 우리 설계의 어느 자리 | 관계 |
|---|---|---|---|
| Ojala & Garriga 2010 | JMLR 11(62) | §7-3 C1 라벨 치환 널 + «특징 안 섞기» 검정 + p 규약 | 지지 · ⚠표기(§8-④) |
| Cawley & Talbot 2010 | JMLR 11(70) | §7-0 S-1(안쪽에서 고르기)·S-3(n_test_peeks) | 지지 |
| Demšar 2006 | JMLR 7 | §7-0 S-2(다중비교 문턱) · §7-2 B-2(짝지은 차이) | 지지 |
| Dwork 외 2015 | Science 349 | §7-0 S-3 시험 폴드 재사용 경고 | 지지 |
| Bengio & Grandvalet 2004 | JMLR 5 | §7-2 B-3·B-4 폴드 sd 를 과신하지 않는 이유 | 지지 |
| Nadeau & Bengio 1999/2003 | NeurIPS 1999 · Machine Learning 52 | §7-2 B-1(밴드는 그 자리에서 다시)·B-2·B-3 | 지지 |

### ⑧ 누수·분할 (2편)

| 논문 | 어디 | 우리 설계의 어느 자리 | 관계 |
|---|---|---|---|
| Kapoor & Narayanan 2023 | Patterns 4(9) | §8-1 누수 검사표 L-1~L-4(원문 번호 그대로) · §7-4 사전등록 | 지지 |
| Chaibub Neto 외 2019 | npj Digital Medicine 2 | §3-4 칸 단위 배타 분할 · §8-1 L-5 부풀림 측정 | 지지 |

### ⑨ 시뮬→실측 (6편 + 재등장 2편)

| 논문 | 어디 | 우리 설계의 어느 자리 | 관계 |
|---|---|---|---|
| Chen 외(DR 이론) 2022 | ICLR 2022 spotlight | §9-2 «모델 파라미터를 흔든다»는 DR 프레임 | 지지 |
| Ben-David 외 2006 | NeurIPS 2006 | ⑨축 골격(시험은 언제나 M · 4팔) · Q4 대리 측정의 정식 이름 | 지지 |
| Ganin 외(DANN) 2016 | JMLR 17(59) · 회의판 ICML 2015 | §9-3 라벨 없는 실측 활용 예비 팔 · §9-5 배경 캡처 | 지지 · ⚠표기(§8-⑤) |
| Zhuang 외 2021 | Proc. IEEE 109(1) | L3/L3′ 와 §9-3 분량별 미세조정의 상위 좌표 | 지지 |
| Shrivastava 외(SimGAN) 2017 | CVPR 2017 Best Paper | SM 반합성 팔 · 실측↔시뮬 번역 백업(§9-1·§9-3) | 지지 |
| Geirhos 외 2020 | Nature Machine Intelligence 2 | §4-1 세기 치트 · §7-3 널 설계 · §8 시뮬 내부 성적 불신 전체 | 지지 |
| (재등장) Seyfioglu 2019 · Erol 2020 | IEEE TAES | 합성 사전학습·물리 체질이 ⑨축에서도 근거 | 지지 |

합계 **31편**(축 표에는 33칸 — DivNet·Erol 이 두 축에 걸린다).

---

## 1. ④ 표현

**Chen, Li, Ho, Wechsler 2006 — "Micro-Doppler Effect in Radar: Phenomenon, Model, and
Simulation Study" (IEEE TAES 42(1):2–21).** 미세도플러라는 분야를 연 논문이다(인용 1,700+).
도는 날개·떨리는 부품이 레이다 반사 신호에 새기는 주파수 떨림을 **수식으로 모델을 세우고,
시뮬레이션으로 확인한 뒤, 시간-주파수 맵으로 읽는 절차**를 정립했다. 우리 두 선택을 동시에
받친다 — R1(시간-주파수 dB 맵)을 «문헌 표준 팔»로 두는 것, 그리고 수식 기반 합성(우리 로터
커널)으로 시그니처를 연구하는 접근 자체.
https://doi.org/10.1109/TAES.2006.1603402

## 2. ⑤ 모델 사다리

**Kim & Ling 2009 — "Human Activity Classification Based on Micro-Doppler Signatures Using a
Support Vector Machine" (IEEE TGRS 47(5):1328–1337).** 딥러닝 이전의 정본 파이프라인.
스펙트로그램에서 손으로 뽑은 특징 6개 + SVM + 4겹 교차검증으로 사람 활동 7가지(12명)를
90 %+ 로 갈랐다. 우리가 L0″(27특징+RF100)를 «관행 선»으로 반드시 그리는 이유의 출처이고,
딥러닝이 이 계보를 못 이기면 «손 특징으로 충분»으로 접는다는 M3 중단 규칙(§10)의 비교
상대가 바로 이 계보다.
https://ieeexplore.ieee.org/document/4801689

**Chen, Wang, Xu, Jin 2016 — "Target Classification Using the Deep Convolutional Networks for
SAR Images" (A-ConvNets, IEEE TGRS 54(8):4806–4817).** 레이다 표적인식 CNN 의 정본.
레이다 데이터는 적어서 보통 CNN 은 심하게 과적합하므로, **완전연결층을 아예 없애 파라미터를
줄인 소형 전(全)합성곱 망**으로 MSTAR 10클래스 99.13 % 를 냈다. 우리 L1(0.15~0.45 M 경량
CNN 출발점)과 «작은 망부터, 큰 망은 나중» 순서(§5-0)와 같은 원리를 상급지가 확립한 것이다.
https://doi.org/10.1109/TGRS.2016.2551720

**Seyfioglu, Özbayoglu, Gurbuz 2018 — "Deep Convolutional Autoencoder for Radar-Based
Classification of Similar Aided and Unaided Human Activities" (IEEE TAES 54(4):1709–1723).**
겉보기에 비슷한 12가지 활동의 미세도플러를 **작은 실측 데이터**로 가르는 과제에서 합성곱
오토인코더(CAE)가 94.2 %(SVM 대비 +17.3 %p)를 냈다. 핵심은 **가중치 초기화(비지도
사전학습)의 힘**이다 — 무작위 초기화 CNN 특징+SVM 은 8.3 %, 사전학습을 거치면 83.4 %
(PDF 전문 축자 확인). ⚠인용 문구 정정 두 건이 필수다 — §8-① 을 보라(전이학습 정면 비교는
이 논문이 아니고, patience 조기종료도 이 논문이 아니다).
https://doi.org/10.1109/TAES.2018.2799758

**Seyfioglu, Erol, Gurbuz, Amin 2019 — "DNN Transfer Learning From Diversified Micro-Doppler
for Motion Classification" (DivNet, IEEE TAES 55(5):2164–2180).** L3′ 의 정본. 물리 시뮬
(모캡 기반)로 다양화한 **합성** 미세도플러로 사전학습하고 소량 실측으로 미세조정한 DivNet 이
ImageNet 전이와 스크래치를 이겼다 — PDF 전문 축자 확인: 7클래스 **DivNet-15 97 % >
ResNet 95 % > VGG 94 % > 스크래치 4층 CNN 86 %**, 11클래스 95.7 % vs 91 %, 미세조정은
474표본/7클래스(클래스당 약 68장). §9-3 «클래스당 60~90 스니펫 → 전체 미세조정» 행과
§8-2 데이터량 곡선(Table IX 형식)의 직접 근거다.
https://arxiv.org/abs/1811.08361

**Brooks, Schwander, Barbaresco, Schneider, Cord 2019 — "Riemannian Batch Normalization for
SPD Neural Networks" (NeurIPS 2019).** L6(공분산/SPD 모델)의 탑티어 판 — 설계 문서가
인용하는 Brooks CAp 2020 과 같은 저자들의 **상위 NeurIPS 판**이고, 실험 데이터가 바로
**레이다 드론 인식**이다(도메인까지 우리와 일치). 2차 통계(공분산) 위의 신경망이 **데이터
부족에 눈에 띄게 강인**함을 보여, 108칸뿐인 우리 데이터에서 SPD 대조군을 두는 선택을 받친다.
⇒ 설계 문서 §5 L6 행의 인용을 이 판으로 승급(부록 B12).
https://proceedings.neurips.cc/paper/2019/hash/6e69ebbfad976d4637bb4b39de261bf7-Abstract.html

**LeCun, Bottou, Bengio, Haffner 1998 — "Gradient-Based Learning Applied to Document
Recognition" (LeNet, Proc. IEEE 86(11):2278–2324).** CNN 정본. **가중치 공유+풀링이 이동
불변성을 «구조로» 준다**는 원리 — L2 의 «전역평균풀링 = 시간이동 불변» 채택과, «CNN 은
텍스처를 읽는 기계라 nper 얼룩 누수에 더 위험하다»(§4-1) 진단의 이론적 바닥이다.
⚠정직 노트: «레이다 딥러닝 리뷰 in Proc. IEEE» 같은 것은 검색으로 실재를 확인하지 못했다 —
가까운 리뷰(Gurbuz & Amin SPM 2019 · Geng IEEE Access 2021)는 탑티어 목록 밖이라 제외했고,
Proc. IEEE 몫은 이 정본으로 채운다.
https://ieeexplore.ieee.org/document/726791

## 3. ⑥ 학습 절차·증강

**Kingma & Ba 2015 — "Adam: A Method for Stochastic Optimization" (ICLR 2015).**
§6-1 «Adam 을 쓴다»는 선택의 원 논문. ⚠원문 기본 lr 은 **1e-3** 이다(*"Good default settings
… α = 0.001"* 축자 확인) — 우리 1e-4 는 분야 관행(Park·Ha·Czerkawski·Larrat)에서 온 값이라
**값의 근거로는 못 쓰고 알고리즘의 근거로만** 쓴다.
https://arxiv.org/abs/1412.6980

**Caruana, Lawrence, Giles 2000 — "Overfitting in Neural Nets: Backpropagation, Conjugate
Gradient, and Early Stopping" (NeurIPS 2000).** 조기종료의 정본. 핵심 발견: **여유 용량이 큰
망도 조기종료만 제대로 걸면 작은 망 수준으로 일반화한다** — 소데이터에서 조기종료를 1차
정칙화(과적합을 누르는 장치)로 쓰는 우리 결정과, L1→L4 사다리 전체에 조기종료를 공통
안전장치로 거는 설계를 받친다.
https://proceedings.neurips.cc/paper_files/paper/2000/hash/059fdcd96baeb75112f09fa1dcc740cc-Abstract.html

**Chen, Dobriban, Lee 2020 — "A Group-Theoretic Framework for Data Augmentation"
(JMLR 21(245):1–71).** 증강의 이론 틀. 증명된 정리: **증강은 데이터 분포를 (근사)보존하는
변환일 때만 분산 감소로 이득**이다. 시간 이동·SNR 주입·물리 파라미터 재추첨은 분포 보존이라
허용이고, 주파수 마스킹·회전·좌우반전은 라벨을 실은 구조(블레이드 빗살)를 깨거나 물리적으로
불가능한 표본을 만들므로 금지 — §6-2 목록 전체가 이 틀에서 정당화된다.
https://jmlr.csail.mit.edu/papers/volume21/20-163/20-163.pdf

**Balestriero, Bottou, LeCun 2022 — "The Effects of Regularization and Data Augmentation are
Class Dependent" (NeurIPS 2022).** SpecAugment 금지의 실증 상위 근거. **판별 정보가 실린
구조를 지우는 증강은 평균 정확도가 올라도 해당 클래스를 침몰시킨다** — random crop 만으로
ImageNet 한 클래스가 68 %→46 %(축자 확인). 우리 라벨 정보는 주파수축 빗살에 실려 있으므로
주파수 마스킹 금지가 정확히 같은 논리다. 참고: TAES/TGRS 급에서 드론 미세도플러에
SpecAugment 를 성공적으로 쓴 반례는 검색으로 못 찾았다(설계 문서의 «적용 사례 못 찾음»과
일치).
https://proceedings.neurips.cc/paper_files/paper/2022/hash/f73c04538a5e1cad40ba5586b4b517d3-Abstract-Conference.html

**Yosinski, Clune, Bengio, Lipson 2014 — "How transferable are features in deep neural
networks?" (NeurIPS 2014).** 특징 전이성의 정본. (1) 먼 과제에서 온 특징도 무작위 초기화보다
낫다, (2) 전이 후 **미세조정이 동결보다 낫다**, (3) 과제 거리가 멀수록 이득이 준다 —
L3·L3′ 에서 미세조정을 기본으로 두는 근거이자, ImageNet↔레이다 스펙트로그램 사이의 이득
축소 가능성을 미리 적어 둘 근거다.
https://arxiv.org/abs/1411.1792

**Erol, Gurbuz, Amin 2020 — "Motion Classification Using Kinematically Sifted
ACGAN-Synthesized Radar Micro-Doppler Signatures" (IEEE TAES 56(4):3197–3213).** 이미
탑티어인 응용 논문. 두 가지를 받친다 — (a) **영상용 증강은 운동학적으로 불가능한 RF 표본을
만든다**는 금지 원리(⚠축자 주의는 §8-②), (b) 생성 표본을 **물리 제약으로 체질(sifting)**
하면 성능이 오른다: 체질 하나로 **+9 %p → 93 %**, 보행 15 %·낙상 10 % 탈락(축자 확인) —
우리 «불가능 조합 배제 규칙 + 탈락률 원장 기록»(§6-2)이 같은 원리다.
https://arxiv.org/abs/2001.08582

**⚠어긋남·빈칸 4편(Raghu · Srivastava · Loshchilov & Hutter · Wilson)은 §7 에 모았다.**

## 4. ⑦ 평가·통계

**Ojala & Garriga 2010 — "Permutation Tests for Studying Classifier Performance"
(JMLR 11(62):1833–1863).** 치환검정의 정본 — **라벨 치환**과 **클래스 내 특징 치환** 두
검정을 모두 세웠다(원문 확인). §7-3 C1 «칸 단위 라벨 치환 널»과 표 마지막 행 «특징 안
섞기»의 원전이고, p = (1+#{널≥관측})/(1+n) 규약도 이 계열의 표준이다. ⚠단 원문의 치환은
**표본 단위**다 — «칸 단위로 치환해야 누수를 고발한다»는 우리 2판 정정은 이 원리를 그룹
구조에 맞게 **강화한 것**이지 원문 축자가 아니다. 리포트에 그렇게 적어야 정직하다.
https://jmlr.org/papers/v11/ojala10a.html

**Cawley & Talbot 2010 — "On Over-fitting in Model Selection and Subsequent Selection Bias in
Performance Evaluation" (JMLR 11(70):2079–2107).** **모델 고르기 자체가 과적합**이 된다는
정본. «여러 팔 중 최고 고르기»의 부풀림이 *"surprisingly large"* 라는 원문 축자를 확인했다 —
1판이 max(팔들)를 시험 폴드에서 채점한 결함(§7-0 진단)을 탑급이 이미 일반형으로 증명해
놓았던 것이다. §7-0 S-1(고르기는 안쪽 검증에서, 시험은 최종 1회)과 S-3(n_test_peeks 정수
기록)의 원전.
https://jmlr.org/papers/v11/cawley10a.html

**Demšar 2006 — "Statistical Comparisons of Classifiers over Multiple Data Sets" (JMLR 7:1–30).**
분류기 비교 통계의 표준 — Wilcoxon 부호순위·Friedman + 사후 다중비교 보정. §7-0 S-2(시험
폴드에 팔 k 개를 올리면 문턱을 k 에 맞춰 올린다)와 §7-2 B-2(같은 폴드·같은 씨앗의 «짝지은
차이»로 비교)가 **우리가 임의로 만든 규약이 아님**을 한 줄로 받쳐 준다.
https://jmlr.org/papers/v7/demsar06a.html

**Dwork, Feldman, Hardt, Pitassi, Reingold, Roth 2015 — "The reusable holdout: Preserving
validity in adaptive data analysis" (Science 349(6248):636–638).** **시험(홀드아웃) 집합을 보고
나서 다음 분석을 고르는 일을 반복하면 통계 보증이 무너진다**는 경고의 정본. §7-0 S-3
«시험 폴드를 본 횟수를 원장에 정수로 적는다»가 왜 필요한지, S-2 가 왜 σ 어림으로 안 되는지를
Science 급이 받친다. 이론 세부를 인용할 때는 NeurIPS 2015 판("Generalization in Adaptive Data
Analysis and Holdout Reuse", arXiv:1506.02629)을 쓴다 — 둘 다 실재 확인.
https://www.science.org/doi/10.1126/science.aaa9375

**Bengio & Grandvalet 2004 — "No Unbiased Estimator of the Variance of K-Fold
Cross-Validation" (JMLR 5).** 정리: **K겹 교차검증 분산에는 치우침 없는 보편 추정량이
존재하지 않는다**(폴드 사이가 서로 얽혀 있어서다). §7-2 B-3·B-4 의 근거 — 폴드 sd 를
«평균 ± 폴드 sd (겹 수, ddof)» 서술 통계로만 적고, 앙각 3겹(자유도 2)의 σ/√3 을
신뢰구간처럼 과신하지 않으며, 소수 넷째 자리를 금지하는 이유가 정확히 이 정리다.
https://jmlr.org/papers/v5/grandvalet04a.html

**Nadeau & Bengio 1999 — "Inference for the Generalization Error" (NeurIPS 1999 · 저널판
Machine Learning 52:239–281, 2003).** 성적 분산의 큰 몫이 **학습집합(=분할) 가변성**에서
온다는 것을 지적하고 보정 분산 추정을 세운 정본. §7-2 B-1 «밴드는 (분할축 × 학습기 × 표현)
마다 그 자리에서 다시 잰다 — 남의 실험 밴드를 옮겨 오지 않는다»의 원리적 근거이고, B-2·B-3
의 짝지은 비교·두 sd 병기도 이 논문의 보정 재표집 t(corrected resampled t) 계열이 정본이다.
https://papers.nips.cc/paper/1661-inference-for-the-generalization-error

## 5. ⑧ 누수·분할

**Kapoor & Narayanan 2023 — "Leakage and the reproducibility crisis in machine-learning-based
science" (Patterns 4(9):100804).** 누수 8종 분류의 정본. §8-1 누수 검사표가 이 논문의 항목
번호를 그대로(L1.2 전처리 격리 · L1.3 특징선택 격리 · L1.4 근접중복 · L3.2 그룹 배타성)
인용하고 있고, 원문 번호 체계와 일치함을 확인했다. **model info sheet**(모델 정보시트) 제안은
§7-4 사전등록 JSON 의 방법론적 근거이기도 하다.
https://doi.org/10.1016/j.patter.2023.100804

**Chaibub Neto 외 2019 — "Detecting the impact of subject characteristics on machine
learning-based diagnostic applications" (npj Digital Medicine 2:99).** **같은 개체의 반복 측정이
학습·시험 양쪽에 들어가면(record-wise 분할) 모델이 정체성을 외워 오차를 대폭 과소평가한다**
는 Nature 계열의 정량 실증. §3-4 «칸 단위 배타 분할» 그 자체와 §8-1 L-5 «일부러 행 무작위
분할로 부풀림을 잰다»(우리 측정 +16.7 %p)의 절차적 근거 — 그들이 사람(subject)으로 한 것을
우리는 칸(자세×기체)으로 한다. 정직 노트: «그룹 교차검증을 창설한 단일 논문»은 존재하지
않는다는 게 정직한 결론이고, 탑티어에서 이 원리를 확립한 최근접 정본이 이 논문이다
(교과서로는 Hastie 외 ESL §7.10.2 "the wrong way to do cross-validation" 병기 가능).
https://www.nature.com/articles/s41746-019-0178-x

## 6. ⑨ 시뮬→실측

**Chen, Hu, Jin, Li, Wang 2022 — "Understanding Domain Randomization for Sim-to-real
Transfer" (ICLR 2022, spotlight — 공식 페이지로 지위 확인).** 도메인 무작위화(DR)의 탑티어
이론 근거. **실측 표본 없이 DR 만으로 전이가 성립하는 조건**과 시뮬-실측 갭의 상계를
증명했다. 시뮬레이터를 «물리 파라미터가 달라지는 모델들의 집합»으로 놓고 그 파라미터를 뽑아
흔드는 프레임이라, §9-2 의 ⭐«출력 파형에 랜덤을 얹지 말고 모델 파라미터(rpm·산포·잡음)를
흔든다» 선택을 원리 수준에서 받친다. 원조(Tobin 2017 IROS, 로봇 학회) 인용은 유지한다 —
상위 대체물이 없다.
https://arxiv.org/abs/2110.03239

**Ben-David, Blitzer, Crammer, Pereira 2006 — "Analysis of Representations for Domain
Adaptation" (NeurIPS 2006).** 도메인 적응 이론의 출발점: **«실측 오차 ≤ 시뮬 오차 + 두
도메인의 거리»** 경계. 이게 ⑨축 전체(«시험은 언제나 M», S/S+DR/SM/M 4팔)의 논리 골격이다.
특히 **proxy A-distance**(두 도메인을 구별하는 분류기를 학습시켜 그 오차로 거리를 잰다)가
Q4 «엔진을 넘으면 몇 pp 잃나»의 대리 측정(R9 Stage 0, 27특징 42짝)의 정본 형태다 — 우리가
임시로 만든 대리 지표에 정식 이름과 이론이 있다.
https://proceedings.neurips.cc/paper/2006/file/b1b0432ceafb0ce714426e9114852ac7-Paper.pdf

**Ganin 외 2016 — "Domain-Adversarial Training of Neural Networks" (DANN, JMLR 17(59)).**
비지도 도메인 적응의 정본(그래디언트 반전). **라벨 없는 실측(배경 캡처·초기 비행)만 있어도
시뮬과 실측이 구별 안 되는 특징을 배우게 할 수 있다**는 표준 경로 — M8 실측 결합 단계에서
미세조정(§9-3) 외의 공인된 예비 팔이고, §9-5 «표적 없는 배경 캡처» 요구(라벨 없는 실측의
용도)에 방법론적 근거를 더한다. Ben-David 경계의 «도메인 거리 항을 줄이는 학습»을 실제로
구현한 논문이다. ⚠회의판 표기는 §8-⑤.
https://jmlr.org/papers/v17/15-239.html

**Zhuang 외 2021 — "A Comprehensive Survey on Transfer Learning" (Proc. IEEE 109(1):43–76).**
탑 저널의 전이학습 총정리. 정직한 결론: **sim-to-real «전용» 서베이는 탑 저널에 없다**(로봇
쪽 후보들은 그 아래 급) — 이 논문이 가장 가까운 정본이고 도메인 적응까지 포괄한다.
사전학습→미세조정 사다리(L3/L3′)와 §9-3 «실측 분량에 따라 동결+헤드 ↔ 전체 미세조정을
고른다»는 선택 축을 상위 문헌 체계 안에 위치시킨다.
https://doi.org/10.1109/JPROC.2020.3004555

**Shrivastava 외 2017 — "Learning from Simulated and Unsupervised Images through Adversarial
Training" (SimGAN, CVPR 2017 — Best Paper 수상 확인).** **«합성만으로는 부족하고, 합성의
라벨 + 실측의 통계를 섞어야 갭이 닫힌다»**를 정량으로 보인 탑티어(합성 단독 학습 < 실측
통계로 정제한 합성). 우리 SM 반합성 팔(합성 표적 에코 + 실측 배경, White −3.1 pp 목표선)과
백업 경로인 실측↔시뮬 번역(FMNet)의 상위 근거 — 응용지 수치에 탑티어 원리 층을 얹는다.
https://openaccess.thecvf.com/content_cvpr_2017/html/Shrivastava_Learning_From_Simulated_CVPR_2017_paper.html

**Geirhos 외 2020 — "Shortcut learning in deep neural networks" (Nature Machine Intelligence
2:665–673).** **«같은 분포 벤치마크에서 잘 나와도 지름길(허위 단서)을 배운 것일 수 있고,
분포가 바뀌면 무너진다»**의 정본. §4-1 세기 치트 상한 팔·N1/N2 세기 널, SAMPLE «시뮬만으로
95 %»를 합성이 정답을 베낀 결과로 의심하는 §8, 칸 단위 널 검정(G-G)까지 — 시뮬 내부 성적을
그대로 믿지 않고 치트·누수 검사를 겹겹이 두는 설계 전체의 탑티어 근거다. 개별 널(N1·N2·N4)
의 구체적 형태는 여전히 선례 없이 우리가 만든 것이라고 정직하게 적는다.
https://www.nature.com/articles/s42256-020-00257-z

---

## 7. ⚠어긋남·빈칸 — 맞춰 고치지 말고 원장에 남길 것들

설계 문서의 원칙대로, 우리 선택과 어긋나는 탑티어는 **숨기지도 따라가지도 않고** 어긋남
자체를 기록한다.

| # | 논문 | 어긋나는 자리 | 처분 |
|---|---|---|---|
| ① | **Loshchilov & Hutter(AdamW), ICLR 2019** | §6-1 은 AdamW 를 «분야 사례 0편»으로 배제했는데, 탑티어 쪽은 Adam 의 L2 정칙화가 사실상 망가져 있고 AdamW 가 일반화를 실질 개선함을 확립(현재 PyTorch 표준) | 라운드1 의 «분야 관행 고정»은 유지. 어긋남을 원장에 적고 **후속 라운드 감사 항목(AdamW 팔 1개)** 으로 |
| ② | **Wilson 외, NeurIPS 2017** | 적응형 방법(Adam 포함)이 잘 튜닝한 SGD 보다 일반화가 나쁜 사례를 이론+실증으로 제시 — «넷 다 Adam 1e-4» 관행 채택과 긴장 | Adam 채택의 목적이 성능 최적이 아니라 **선행 재현·비교가능성**임을 §6-1 에 한 줄 명시. SGD 대조 팔은 미래 작업 |
| ③ | **Raghu 외(Transfusion), NeurIPS 2019** | 작은 비자연영상(의료) 데이터에서 ImageNet 전이 이득이 작았고, 경량 모델이 큰 사전학습 모델과 비슷했으며, 이득 일부는 특징 재사용이 아니라 과매개변수화였다 — L3 칸의 «전이가 스크래치를 +8~16 %p» 기대와 상충 가능 | **부분 어긋남**으로 기록. 동시에 «작은 망 먼저»(§5-0)는 오히려 지지. L3 결과 해석 때 대조 인용 |
| ④ | **Srivastava 외(Dropout), JMLR 2014** | 어긋남이 아니라 **빈칸**: DL_PIPELINE.md 전체에 dropout·weight decay 언급이 0회(grep 확인) — §6-1 에 명시적 정칙화 행이 없다 | L1 에 dropout 을 쓸지 말지를 **어느 쪽이든 이 정본 인용과 함께 사전등록**(분야 선행 다수는 사용) |

링크: AdamW https://arxiv.org/abs/1711.05101 · Wilson
https://papers.nips.cc/paper/2017/hash/81b3833e2504647f9d794f7d7b9bf341-Abstract.html ·
Raghu https://arxiv.org/abs/1902.07208 · Srivastava https://jmlr.org/papers/v15/srivastava14a.html

## 8. ⚠표기 주의 — 인용할 때 틀리기 쉬운 곳 (원문 대조 결과)

| # | 논문 | 틀리기 쉬운 문구 | 원문이 실제로 말하는 것 |
|---|---|---|---|
| **①** | **Seyfioglu 2018 (TAES 54(4))** | «스크래치 CNN·전이학습·오토인코더 사전학습을 정면 비교» — **거짓**(전문에 "transfer" 0회) · «조기종료 인용의 원 논문» — **부정확** | 비교군은 **CNN·AE·CAE·SVM·RF·XGBoost** 다. 전이학습과의 정면 비교는 자매 논문 **Seyfioglu & Gurbuz, IEEE GRSL 2017**(DNN 초기화 방법 비교)에 있다. 학습은 **고정 280 epoch + 매 epoch 검증셋 평가**이고 patience 조기종료가 아니다(원문은 오히려 "no overfitting") — **«epoch 수·검증 모니터링 관행»의 출처로만** 쓴다. 대신 «초기화의 힘»은 원문이 더 세게 지지한다(8.3 % vs 83.4 %) |
| ② | Erol 2020 (TAES 56(4)) | 금지 증강을 «회전·반전·크롭»으로 축자 인용 | 원문 축자는 **"scaling and rotating"**(픽셀 기반 변환 일반)이다. 반전·크롭 금지는 **같은 원리의 우리식 확장**으로 적어야 정직하다. 체질 수치(+9 %p→93 %, 보행 15 %·낙상 10 % 탈락)는 축자 일치 |
| ③ | Chen 2006 (TAES 42(1)) | «STFT 를 정립» | 원문은 **"high-resolution time-frequency transforms"** 라 STFT 하나로 못박지 않는다. «시간-주파수 맵 정립»은 정확, "(STFT)" 는 넓은 의미로만 |
| ④ | Ojala & Garriga 2010 | «칸 단위 치환의 출처» | 원문 치환은 **표본 단위**다. 칸 단위는 그룹 구조에 맞춘 **우리 강화**(§7-3) — 원리의 출처로만 쓴다 |
| ⑤ | DANN 회의판 | "(ICML 2015)" 를 저널판 저자·제목 그대로 표기 | 회의판은 정확히는 **Ganin & Lempitsky, ICML 2015, "Unsupervised Domain Adaptation by Backpropagation"** (제목이 다르고 저자가 부분집합) |

---

*정본 관계: 설계는 `docs/DL_PIPELINE.md`(부록 A-2 가 이 문서의 대응표), 응용 층 서베이는
`prior_work/md_classification_dl_survey.md`(39편). 이 문서는 탑티어 층만 담당하며, 응용
인용을 대체하지 않는다 — 두 층을 나란히 쓰는 것이 규약이다.*
