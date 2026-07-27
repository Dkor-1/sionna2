# 드론 ISAC 선행연구 통합 정독 노트 — 13편

*2026-07-23 작성 · 대상 폴더 `/home/yunjung/workspace/paper_sionna_Ray/`*
*우리 수치는 전부 `outputs/*.json` 에서 직접 읽었다. 재실행한 값은 그렇다고 표시했다.*
*인용은 영어 원문 그대로 옮기고 절·쪽을 밝힌다. 확인 못 한 것은 "논문에 없음" 이라 적는다.*

관련: [`VERIFY_CLUTTER.md`](VERIFY_CLUTTER.md) · [`VERIFY_RT_VS_PO.md`](VERIFY_RT_VS_PO.md) · [`PRIOR_WORK_COMPARISON.md`](PRIOR_WORK_COMPARISON.md)

---

## §1. 무엇을 읽었나 — 13편

`실측` = 자체 측정 데이터가 있음 · `시뮬` = 계산만 · `Sionna` = 이 논문이 Sionna 를 실제로 돌렸나.

### A. 실측 RCS (드론 σ 의 외부 앵커 후보)

| # | 약칭 | 한 줄 | 실측/시뮬 | Sionna |
|---|---|---|---|---|
| 1 | **mono3d** — Yuan·Yu·Li·Fan, *On Experimental Analysis of Mono-Static 3D UAV RCS for ISAC Channel Modeling*, EuCAP 2025 | DJI Phantom 3 를 무향실 CATR 턴테이블에서 1.8–18.2 GHz·방위 −90°:2°:90°·고도 3면(θ=90/0/180°) 모노스태틱 측정, μ·ε 를 주파수 1차식으로 회귀하고 Rician 을 최적분포로 채택 | **실측** | 미사용 (전문 0회) |
| 2 | **multiband** — Das·Zhang·Hovinen·Leinonen·Pärssinen·Kyösti, *Multiband Monostatic and Bistatic RCS Characterization of AAVs for ISAC Channel Modeling*, IEEE WCL 15:3731–3735, 2026 | DJI 4기종(Phantom 2/3·Mini 2·M350 RTK)을 1.8–27 GHz·바이스태틱각 0°:15°:90° 로 정리해 μ(f)=af+b, ε(f)=cf+d 계수표(Table III)와 log-normal/Gamma/Rician 적합을 낸다. **Phantom 2 만 신규 측정**, 나머지 3기는 Wei Fan 그룹 데이터 재가공 | **실측** | 미사용 (전문 0회) |
| 3 | **unified-rcs** — Zhang(Y.)·Zhang(J.) 외, *A Unified RCS Modeling of Typical Targets for 3GPP ISAC Channel Standardization and Experimental Analysis*, IEEE JSAC 44:702–716, 2026 | DJI M350·사람·차량을 10–36 GHz 무향실 VNA 로 재고 σ=A(f)·B1(φ)·B2 3성분으로 분해. 이 틀이 3GPP TSG RAN1 #120 에서 채택돼 표준의 일부가 됐다고 명시 | **실측** | 미사용 (전문 0회, ray tracing 은 참고문헌 [20] Weinmann PO/PTD 한 곳) |

### B. 마이크로도플러

| # | 약칭 | 한 줄 | 실측/시뮬 | Sionna |
|---|---|---|---|---|
| 4 | **md-props** — Costa·Myint·Andrich·Giehl·Schneider·Thomä, *Modelling Micro-Doppler Signature of Drone Propellers in Distributed ISAC*, IEEE RadarConf24 | 프로펠러를 thin-wire 무한 점산란체로 두고 **바이스태틱 OFDM** 으로 재유도, TU Ilmenau BiRa 무향실에서 β=30~180° 실측 대조(ρ≈0.98). 실측 도플러 피크 수치(±557.9/+559.8 Hz, 50.8 Hz)는 **이 학회판에만** 있다 | **실측** | 미사용 (RT 는 "쓸 수도 있는 다른 방법" 목록에만) |
| 5 | **md-multiprop** — 같은 팀 저널 확장판, *Modeling Micro-Doppler Signature of Multi-Propeller Drones in Distributed ISAC*, IEEE J-STEAP 1:208–222, 2025 | 다중 프로펠러 벡터 정식화 + 동체 모델 2종(가우시안 / 측정 S21 라이브러리) + 진동 랜덤워크 추가. HRR 거리-도플러에서만 경쟁 모델이 무너진다는 것을 정량화. 거리분해능을 ΔR=c/[2B·cos(β/2)] 로 **정정** | **실측** | 미사용 |
| 6 | **md-testbed** — Wei·Ma·He·Zhang·Feng·Liu·Liang(BUPT), *UAV's Rotor Micro-Doppler Feature Extraction Using ISAC Signal*, IEEE TWC 24(12):10166–10182, 2025 | 5G NR TDD 프레임을 재설계해 전 PDSCH 심볼을 센싱에 쓰고(PRI 33.3 µs), rmD-NSP + SET 로 로터 성분을 분리. 3.5 GHz Sub-6 ISAC 실기 테스트베드(DJI M300 RTK, 닝보)로 검증 | **실측**(스펙트로그램만) | 미사용 (자유공간 가정, 점산란체) |
| 7 | **md-rt** — Li(Changjun)·Mu·Jiang·Feng·Gao·Xu(상하이대/XJTLU), *Micro-Doppler Signature Simulation of Multirotor UAVs Using Ray Tracing*, IEEE ICCT 2025, pp.359–364 | **스톡 Sionna RT + Blender 블레이드 메쉬**로 UAV 로터 마이크로도플러 시간-주파수 스펙트로그램을 만들고 해석해(1562 Hz, T=0.04 s)와 일치시킴. 원추형(cone) 광선 집속 전략을 제안 | 시뮬 | **사용** (17회, 핵심 도구) |

### C. 채널·클러터·RT 방법론

| # | 약칭 | 한 줄 | 실측/시뮬 | Sionna |
|---|---|---|---|---|
| 8 | **clutter** — Liu(Rang)·Li·Li(Ming)·Swindlehurst, *Clutter-Aware ISAC: Models, Methods, and Future Directions*, Proc. IEEE 114(1):52–91, 2026 | cold/hot 클러터 분류 → 통계·공분산 모델 → slow-time·공간·STAP·KA 억제 → 송수신 공동설계까지의 39쪽 튜토리얼. 공개코드 있음 | 시뮬 | **사용** (site-specific 장면 생성 + 표적 메쉬) |
| 9 | **zig-journal** — Ziganshin·Vitucci·Kotterman·Thomä·Schneider·Degli-Esposti, *Ray-Based Simulation of Scattering from Discretized Curved Bodies for Vehicular and ISAC Applications*, arXiv:2604.05991v2 | 곡면을 패싯으로 쪼갤 때의 이산화 품질 지표 **E²/(Rλ)** 를 제안하고, Sionna-RT 에 UTD + 정점회절 + 이중반사를 확장해 구·원기둥·차량을 MLFMM/PO/실측과 대조 | 시뮬(+바이스태틱 실측 대조) | **사용** (솔버를 직접 확장) |
| 10 | **zig-conf** — 같은 팀 학회판, *Ray-Based Simulation of Multistatic Scattering from Target Objects in ISAC*, EuCAP | 정점회절 구현과 다중정적 산란. RT vs PO vs MLFMM 런타임을 직접 비교 — *"the simulation time for the PO solver is around one day, whereas the RT simulation takes only about two seconds"* | 시뮬 | **사용** |
| 11 | **montaner** — Montaner·Fenollosa·Ortega·Beltrán·Cardona(UPV), *Deterministic Modeling of Dynamic ISAC Channels in RF Digital Twin Environments*, arXiv:2603.28736, EuCAP | 77–81 GHz(4 GHz 대역) 채널사운더 실측과 RT 를 위상 정합 대조해 RF 디지털트윈을 **교정**하는 프로토콜. 모노/바이스태틱·이동 표적 포함 | **실측**+시뮬 | **사용** (확산산란 R²+S²=1) |
| 12 | **hoydis** — Hoydis·Aït Aoudia·Cammerer·Euchner·Nimier-David·ten Brink·Keller, *Learning Radio Environments by Differentiable Ray Tracing*, IEEE TMLCN, DOI 10.1109/TMLCN.2024.3474639 | RT 전체를 계산그래프로 보고 재질·산란·안테나 패턴을 **경사하강으로 교정**. DICHASUS 실내 분산 MIMO 사운더(3.438 GHz, 50 MHz, 32.5k 위치)로 검증 | **실측**+시뮬 | **사용** (Sionna RT 저자들) |

### D. 참고용 (논문 아님)

| # | 약칭 | 한 줄 | 판정 |
|---|---|---|---|
| 13 | **korean-note** — `Sionna RT 드론 ISAC 연구.pdf` | 저자·소속·게재처·DOI 없음. Google Docs 렌더러 출력, 표 셀에 `[cite: 24]` 미치환 마커, 참고자료 35건이 전부 URL. 자체 실험 0건 | **인용 금지.** 위 12편의 **색인 노트**로만 쓴다. 개별 주장은 반드시 원문 PDF 로 재확인 |

---

## §2. ⭐우리 σ 의 외부 앵커

### 2-1. 살아 있는 대조

우리 값은 `outputs/report2_waveform_rcs.json` → `rcs.drones.<key>.bands.<band>.mean_dbsm` 이다.
정의는 `src/viz_report2.py:841` `mean_dbsm = 10log₁₀(mean(σ))` = **방위 선형평균** — 아래 두 논문의 정의와 같다.

> multiband §III-1: *"The mean RCS is defined as σ_m(θ_b, f_i) = (1/K) Σ_k σ(θ_b, f_i, φ_k)"*
> unified-rcs Eq.(15): 방위 전체에 대한 **linear average**

| 출처 | 표적 | 주파수 | 기하 | 편파 | 자세정의 | 논문 값 [dBsm] | **우리 값** [dBsm] | 사과-대-사과 |
|---|---|---|---|---|---|---|---|---|
| **multiband** Table III (p.3734) — Phantom 3, θb=0° | DJI Phantom 3 (350×200 mm) | μ=0.21f−19.19 → **−18.80 / −18.46 / −18.10** @1.843/3.5/5.21 GHz | 모노스태틱, 무향실 **far-field** | 논문에 없음 (V 는 Phantom 2 셋업에만 명시) | 수평면(el=0), 방위 −90°:2°:+90°, 로터 정지 | 위 세 값 | **phantom4 (350 mm)** el=15°(JSON): **−21.69 / −18.85 / −18.90** → Δ **−2.89 / −0.40 / −0.81** · el=0°(재실행): **−21.10 / −17.72 / −15.42** → Δ **−2.30 / +0.73 / +2.68** | ★**최상**. 대각·기하·지표·주파수 4축 정합. 남은 미정렬은 편파(우리 스칼라 Γ)와 **자세축**(아래 2-3) |
| **mono3d** IV절 (p.4) — θ=90° | DJI Phantom 3 (350×200 mm) | μ=0.315f−16.15 → **−15.57 / −15.05 / −14.51** | 모노스태틱 CATR | VV | 수평면(el=0), −90°:2°:+90°, 로터 정지 | 위 세 값 | 같은 phantom4 → el=15° Δ **−6.12 / −3.81 / −4.39** · el=0° Δ **−5.54 / −2.68 / −0.91** | 조건은 동일한데 **같은 캠페인의 값이 multiband 와 3.2~3.6 dB 다르다**(2-2) |
| 3GPP 등방 상수 (multiband §I, mono3d I절 이 함께 인용) | UAV 일반 | **−20 dBsm @ 4.9 GHz**, 입사각 무관 | 무향실 | 미상 | 미상 | −20 | 5.21 GHz 방위평균: mini5pro **−21.57**, matrice4e **−20.22**, phantom4 **−18.90**, mavic4pro **−15.98**, s1000plus **−12.92** | 거친 정합. 소·중형 3기가 ±1.6 dB 안, 대형 2기는 크기 순서대로 위로 벗어남 |
| **unified-rcs** §III-B (p.709) — 교정 기준 | 지름 0.5 m 금속구 | 28 GHz | 모노스태틱 | V | — | 이론 πa² = **−7.07**, 측정 **−8.96**, **편차 1.89 dB** | 우리 `rcs_sbr.validate()` 는 해석 PO 와만 대조 (구 교정 미실시) | **절차만 차용.** 편차 **< 2 dB** 를 우리 구 교정 합격선으로 삼는다 |

**앵커 요약 (정직한 형태)**
- 우리 대각 350 mm 기체의 방위평균 σ 는 **3.5 GHz 에서 실측 앵커의 −0.4 ~ −3.8 dB, 5.2 GHz 에서 −0.8 ~ −4.4 dB** 안에 있다(el=15° JSON 기준).
- 자세를 문헌과 맞추면(el=0°) **3.5 GHz +0.7/−2.7 dB, 5.2 GHz +2.7/−0.9 dB** 로 **문헌 두 값 사이에 들어간다**.
- 1.843 GHz 는 어느 자세에서도 **2.3~6.1 dB 어둡다** — 우리 저역이 눌려 있거나 광대역 단일회귀가 저역에서 낙관적이거나 둘 다다. multiband Fig.3(b) 원자료는 1.8–2 GHz 에서 적합선보다 아래로 내려가므로 후자도 실재한다.
- **단일 앵커로 "우리가 밝다/어둡다" 를 단정할 수 없다.** 앵커 자체의 산포가 우리 오차보다 크다.

### 2-2. ⚠ 앵커 자체의 산포 — 같은 측정, 다른 요약, 3.2~3.6 dB

multiband 와 mono3d 의 Phantom 3 는 **같은 측정 캠페인**이다. 직접 확인했다:

| | multiband Table I | mono3d II-A절 |
|---|---|---|
| 치수 | 35 cm × 20 cm | 35 cm × 20 cm |
| 대역 | 1.8 GHz–18.2 GHz | 1.8–18.2 GHz |
| 주파수점 | 2801 | 2801 |
| 방위 | −90° ≤ φ(=2°) ≤ 90° | φ = [−90°:2°:90°] |
| 환경 | Far-field, Anechoic | 무향실 CATR |

> multiband 사사(p.3735): *"The authors would like to thank Prof. Wei Fan from Southeast University for providing the measured RCS data for the DJI Mini 2, DJI Phantom 3, and DJI M350 RTK."*
> mono3d 저자 = Southeast University, Wei Fan 그룹.

그런데 요약값이 다르다:

| f [GHz] | multiband μ | mono3d μ(θ=90°) | 차이 |
|---|---|---|---|
| 1.843 | −18.80 | −15.57 | **3.23 dB** |
| 3.500 | −18.46 | −15.05 | **3.41 dB** |
| 5.210 | −18.10 | −14.51 | **3.59 dB** |

**가장 그럴듯한 원인**: multiband 자신의 ε(f)=0.03f+5.16 → 5.22/5.27/5.32 dB 이고, 로그정규에서 (선형평균 − dB영역평균) = (ln10/20)·ε² = **3.13/3.19/3.25 dB** 로 관측 차이와 거의 같다. 즉 **한쪽은 선형평균, 한쪽은 dB영역 평균**이며 최소 한 편이 라벨을 잘못 달았다. multiband 는 본문에 선형평균이라 명시하므로, **우리 `mean_dbsm` 과 사과-대-사과인 것은 multiband 쪽**이다.

> **결론**: 절대 σ 대조표에는 **평균 규약 열(선형/dB)** 을 반드시 넣고 두 논문을 **두 행으로 병기**한다. 3.4 dB 스프레드는 우리 앵커링 허용오차(±2~3 dB)보다 크므로, 이것이 절대값 판정의 하한 불확도다.

### 2-3. ⚠ 자세축 미정렬 — 우리 el=15°, 문헌 el=0° (수치 확정)

> mono3d §III-A: *"Three UAV elevation sides including the azimuth plane, top, and bottom, were considered"* → θ = {90°, 0°, 180°}
> unified-rcs §III-A: *"this study focuses on two-dimensional RCS measurements in the horizontal plane, with the elevation angle fixed at 90°"*

우리 `report2_waveform_rcs.json` 은 `meta.el_deg = 15.0` 이다. 문헌은 전부 **수평면**이다.
**직접 재실행해 편향을 쟀다** (az 5° 스텝 72점, `n_f=5`, spacing λ/16, GPU 0):

| 기체·밴드 | el=0° mean | el=15° mean (재실행) | **el0 − el15** | JSON(el=15, az 1°) |
|---|---|---|---|---|
| phantom4 LTE 1.843 | −21.10 | −21.65 | **+0.55** | −21.69 |
| phantom4 5G 3.5 | −17.72 | −18.90 | **+1.18** | −18.85 |
| phantom4 WiFi 5.21 | −15.42 | −18.65 | **+3.24** | −18.90 |
| mavic4pro LTE 1.843 | −17.75 | −16.85 | **−0.90** | −16.84 |
| mavic4pro 5G 3.5 | −16.64 | −18.24 | **+1.61** | −18.36 |
| mavic4pro WiFi 5.21 | −12.83 | −15.80 | **+2.97** | −15.98 |

- 편향은 **−0.9 ~ +3.2 dB**, 부호가 항상 같지도 않다.
- 부수 확인: **방위 1° → 5° 재샘플의 대가는 ≤ 0.25 dB** (el=15 재실행 vs JSON). unified-rcs 의 5° 스텝 규약을 따라도 결론이 안 바뀐다.
- `make_notebook08.py:687` 의 각주 *"문헌 측정 앙각은 미상"* 은 **사실이 아니다.** 미상이 아니라 명시돼 있고, 위 표가 편향이다.

### 2-4. 표에서 제외한 대조와 이유

| 제외 대상 | 이유 |
|---|---|
| **unified-rcs** A_AAV = 0.31f − 9.26 | 적합 구간이 **10/15/20/28/36 GHz** 뿐. 우리 밴드는 적합 하한의 1/6~1/2 이라 외삽 무효. 외삽값(−8.70/−8.18/−7.65)은 같은 표적에 평판 σ∝f² 를 적용한 값과 4~12 dB 어긋나 **논문 식 자체가 sub-6 에서 물리와 충돌**한다 |
| **multiband** Mini 2 / M350 RTK 행 | 21–27 GHz 전용. 우리 밴드 밖 |
| **unified-rcs** M350 치수 앵커 | 본문은 *"four symmetrically deployed rotor arms and approximate dimensions of 430 × 420 × 430 mm"* 라 쓰는데 이는 DJI 스펙의 **접힌** 치수다. multiband Table I 은 같은 기체를 **81 cm × 67 cm**(펼침)로 적는다. 광학영역 면적으로 5.5 dB 차 — 크기 앵커로 못 쓴다 |
| **multiband** 바이스태틱 열 3/4 | Phantom 3·Mini 2·M350 은 7개 θb 칸에서 **기울기가 전부 동일**(0.21 / 0.07 / 0.17)이고 **ε 식이 θb 에 완전 불변**이다(내가 Table III 를 직접 렌더해 확인). 논문 자신이 *"The DJI Phantom 2 dataset is newly measured in this work"* 라 밝히므로 **실측 바이스태틱은 Phantom 2 열 하나뿐** |
| **Li & Ling 2017** (우리 report08 §6 의 현 판정 근거) | §5-A 참조. 등급 [N](PDF 부재)이고, 이 폴더의 두 실측과 **물리적으로 불가능한 방향으로** 어긋난다 |
| **md-props / md-multiprop** | 절대 RCS 를 **한 번도** 내지 않는다. 반사도는 무차원 \|E_scat\|²/\|E_inc\|² 이고 dBsm 표기가 전문에 없다 |
| **md-testbed** σ_body = 0.01 m²(−20 dBsm) | Table I 값이지만 **출처가 없다** — [43]=3GPP TS 38.104 를 인용하는 문장 아래 놓였으나 그 규격에 RCS 값이 없다. 주파수·자세·편파 조건도 없다. **가정값이지 측정값이 아니다** |
| **clutter** 서베이 | 표적 RCS 를 dBsm 으로 한 번도 보고하지 않는다. UAV 는 '강한 표적' 이라는 상대적 역할만 한다 |
| **zig-journal / zig-conf** | 표적이 PEC 차량·구·원기둥(2–10 GHz). 드론 아님, 유전체 아님 |

---

## §3. ⭐마이크로도플러 대조

우리 값: `outputs/report1.json` → `microdoppler.drones.<key>`, cfg = `{fc: 3.5 GHz, az: 0, el: 15, prf: 20000, n_t: 6144, n_phase: 144}`.

### 3-1. flash rate — 규약이 실측으로 확인된다 ✅

우리 `flash_hz = N_blades × rpm/60`.

> md-props §III-C (p.5): *"These impulses are separated by ∆f = N f_rot ... the rotation frequency was f_rot = 1500 rpm = 25 Hz and N = 2, so ∆f = 50 Hz, which is consistent with what can be seen in the image."* (그림 주석 실측 **50.8 Hz**)
> 같은 절: *"distance among impulses does not change with respect to bistatic angles, since they depend only on the rotation frequency and the number of blades"*

| 기체 | rpm | 블레이드 | **우리 flash_hz** | 기하 의존성 |
|---|---|---|---|---|
| mini5pro | 5500 | 2 | **183.3** | **없음**(β 불변, 실측 확인) |
| mavic4pro | 3600 | 2 | **120.0** | 없음 |
| matrice4e | 3800 | 2 | **126.7** | 없음 |
| s1000plus | 3600 | 2 | **120.0** | 없음 |
| phantom4 | 5500 | 2 | **183.3** | 없음 |

→ **지문 두 눈금 중 flash 는 안전하다.** 조건 표기 없이 인용해도 된다.

### 3-2. f_tip — 우리 값은 모노스태틱이다 ⚠

> md-props §III-C 식(20): *"f_D = 2v cos(β/2) cos(δ)/λ ... where β is the bistatic angle and δ the angle between the bistatic bisector, and v the direction of target motion"*

우리 `f_tip_hz = 2·v_tip·cos(el)/λ` (el=15°) 는 β=0 인 **모노스태틱 형태**다. 우리 챔버 기하(`verify_linkbudget.json` config: TX[4,2.5,8], RX[4,17.5,6.5], TGT[21,10,5.5])를 내가 직접 계산했다:

```
R1 = 18.748 m   R2 = 18.608 m   L = 15.075 m
β  = 47.598°    cos(β/2) = 0.91497
이등분선 앙각 δ = 5.868°   (수평 로터면 접선속도 기준)
보정계수 = cos(β/2)·cos(δ) / cos(15°) = 0.9423
```

⚠ **naive 하게 ×cos(β/2)(=0.915)만 곱하면 앙각을 이중계산한다.** 우리 모노 f_tip 에 이미 cos(15°) 가 들어가 있으므로, 챔버 기하로 옮기는 올바른 계수는 **×0.9423** 이다.

| 기체 | v_tip [m/s] | **발표 f_tip (모노, el=15)** | **챔버 바이스태틱 (β=47.6°, δ=5.87°)** |
|---|---|---|---|
| mini5pro | 43.89 | 989.8 Hz | **932.7 Hz** |
| mavic4pro | 50.33 | 1135.1 Hz | **1069.6 Hz** |
| matrice4e | 54.52 | 1229.6 Hz | **1158.6 Hz** |
| s1000plus | 71.82 | 1619.7 Hz | **1526.3 Hz** |
| phantom4 | 69.12 | 1558.8 Hz | **1468.8 Hz** |

> md-props §III-C: *"the maximum Doppler spread is observed in the monostatic case, while in forward configuration almost no Doppler spread is present"* — 실측 Fig.6 로 확인됨(β→180° 에서 소멸).

### 3-3. 스펙트로그램 규약 — DC/블레이드선 비, 정의부터 다르다 ⚠

우리 `ratio_db = 20log₁₀(|DC| / std(AC))` (`src/viz_report1.py:783-790`) — **시간영역 총 AC 전력** 기준.
md-props Fig.3 은 **주파수영역 선 피크 대 선 피크** 기준.

**두 지표를 우리 `outputs/report1_microdoppler.npz` 로 직접 계산했다** (Hann 창, |f|>50 Hz 배제):

| 기체 | JSON `sbr.ratio_db` | 내 재계산 \|DC\|/std(AC) | **스펙트럼 DCpk − ACpk** | 정의 오프셋 | JSON `po.ratio_db` |
|---|---|---|---|---|---|
| mini5pro | +9.06 | +9.06 ✅ | **+20.30** | +11.24 | +26.46 |
| mavic4pro | −2.17 | −2.17 ✅ | **+7.56** | +9.73 | +37.15 |
| matrice4e | +6.90 | +6.90 ✅ | **+12.41** | +5.52 | +17.25 |
| s1000plus | +8.45 | +8.45 ✅ | **+16.48** | +8.03 | +18.84 |
| phantom4 | +16.43 | +16.43 ✅ | **+24.56** | +8.13 | +32.48 |

문헌 값 (md-props Fig.3 축 판독, 본문에 수치 없음): DC 피크 ≈83 dB, 블레이드 선 ≈32–36 dB → **약 47 dB**.

| 축 | 우리(SBR, 정의 맞춤) | 문헌 실측 | 격차 |
|---|---|---|---|
| DC 대 블레이드선 | **+7.6 ~ +24.6 dB** | **≈47 dB** | **22 ~ 39 dB** (우리가 낙관적) |

**조건 차이 (전부 우리에게 불리한 방향은 아님, 정직하게)**: ⓐ 논문은 **4개 중 1개 프로펠러만 회전** → 정지 프로펠러 3개 + 프레임이 전부 DC 에 실려 DC 가 과대. ⓑ 표적이 자작 Tarot IRON MAN 650 **골격**(탄소섬유 프로펠러)이지 밀폐 DJI 기체가 아니다. ⓒ β=60°, 3.7 GHz. ⓓ 편파 미기재. ⓔ 무보정 상대 dB.
→ **방향은 명확하나 확정은 아니다.** 우리 PO 계열(|DC|/std(AC) 17.3~37.2 dB)은 SBR 보다 문헌 쪽에 가깝다 — §5-C 참조.
⚠ PO 시계열은 npz 에 없어 PO 의 **스펙트럼** 지표는 직접 못 냈다. 추정하지 않는다.

### 3-4. PRF 게이트 — 관측 가능성의 하드 조건 ⚠

> md-testbed §IV-A (p.10174): *"the pulse repetition frequency (PRF) must be at least twice the maximum micro-Doppler frequency, i.e., PRF >= 2 f_mD^max ... we obtain fmD = 2934 Hz, which requires a PRF of at least 5868 Hz"*

우리 f_tip(모노) 기준 요구 PRF = 2·f_tip:

| 기체 | 요구 PRF [Hz] | L(1000) | G(2000) | W(2136.8) | report1 마이크로도플러(20000) |
|---|---|---|---|---|---|
| mini5pro | **1979.7** | ✗ | **✓** | **✓** | ✓ |
| mavic4pro | 2270.2 | ✗ | ✗ | ✗ | ✓ |
| matrice4e | 2459.1 | ✗ | ✗ | ✗ | ✓ |
| s1000plus | 3239.5 | ✗ | ✗ | ✗ | ✓ |
| phantom4 | 3117.6 | ✗ | ✗ | ✗ | ✓ |

(PRF 는 `detection_rx_sweep.json` 의 `modes.*.prf` = **시뮬 slow-time 반복률**. 이 값과 저장소가 선언한 물리 파일럿률의 불일치는 §5-G.)

- **45개 조합 중 2개만 통과** (mini5pro × {5G, WiFi}).
- ⚠ **`report1.json` 의 마이크로도플러는 PRF 20 kHz 에서 계산됐다.** 논문 분류상 이는 '전 PDSCH 풀캡처' 급 조건이지 상시 기준신호 모드가 아니다. **report03/report08 §5 에 이 조건을 명시해야 한다** — 현재 어디에도 없다.
- 다행히 `make_notebook11.py`·`make_notebook12.py` 는 마이크로도플러를 한 번도 언급하지 않으므로(grep 0건) **검출 서사는 마이크로도플러에 기대고 있지 않다.**

### 3-5. 관측 CPI vs 검출 CPI

| | 값 | 출처 |
|---|---|---|
| md-testbed 헤드라인 | 0.1 s CPI 안에 **로터 회전 8회** 식별 | §V, Fig.16 |
| md-props (유도) | ≈1.05 s CPI (8 µs × subsampling 8 × 16384) | Table I + §III-B |
| 우리 검출 CPI | `verify_eca.json` S4: 5G 8~24 ms · `detection_rx_sweep` M=112/56 | JSON |

→ **분류용 지문은 검출 CPI 의 20~40배 길이를 요구한다.** report11 에 "검출 CPI ≠ 분류 CPI" 절이 필요하다.

---

## §4. 차용할 방법론 (우선순위)

### P0 — 지금 당장, 재실행 없이 표기만으로 되는 것

1. **평균 규약 열을 모든 σ 표에 신설한다** (선형평균 / dB영역 평균). multiband 와 mono3d 가 같은 데이터에서 3.4 dB 벌어진 원인이 이것이다. 우리 `mean_dbsm` 은 선형평균임을 명기.
2. **σ 표에 (재질, ε_r, σ, **평가 주파수 f**) 4열을 강제한다.** korean-note 의 표가 f 를 안 밝혀 자기 식으로도 재현 불가가 된 실패를 반복하지 않는다.
3. **f_tip 표에 기하 라벨을 단다** — `flash_hz`는 β 불변(md-props 실측 확인), `f_tip_hz` 는 **모노스태틱 등가**이며 챔버 기하로는 ×0.9423. §3-2 표를 그대로 싣는다.
4. **마이크로도플러 그림·표에 PRF 20 kHz 조건을 명시한다** (§3-4).
5. **Δ(ka) = 2π·D·B/c 게이트를 상시 규약으로 도입** (§6-1 표). clutter §IV-A2a: *"As a practical illustration for ISAC, a scatterer dimension Ddom = 1 m and bandwidth B = 400 MHz lead to ∆(ka) ≈ 8.4, indicating that frequency selectivity is a relevant issue."*
6. **입력 SCNR / 출력 SCR 을 둘 다 찍는다.** clutter 서베이는 **억제 전** 입력 SCNR 을 헤드라인으로 쓰고(−45.9 / −47.4 / −63.5 dB), 우리는 **억제 후** 표적셀 SCR(45.6 dB)을 쓴다. 지금은 비교 불가.
7. **σ 를 네 각도 인수 함수로 표기한다** — `σ_RCS(θ_in, φ_in, θ_out, φ_out)` — 그리고 우리 구현이 θ_out = θ_in(모노스태틱 후방산란) 단면만 채운다는 사실을 같은 식 아래 한 줄로 명기.
8. **전계 항목 원장(ledger)** — zig-journal 의 `E_total = E_direct + Σ E_specular + Σ E_edge + Σ E_vertex` 를 report07 서두에 인용하고, 우리 SBR+PO 가 채우는 항과 **비우는 항(에지·정점 회절)** 을 표로 대조한다.

### P1 — 계산은 하되 새 실험은 아닌 것

9. **금속구 절대교정을 우리 파이프라인에 이식.** unified-rcs 지름 0.5 m (πa² = −7.07 dBsm) 또는 mono3d 반지름 17.8 cm (−10.02 dBsm) PEC 구를 우리 SBR+PO 로 돌려 편차를 낸다. **합격선은 unified-rcs 의 실측 편차 1.89 dB 를 따라 < 2 dB.**
10. **문헌 대조 전용 el=0° 컷을 산출해 병기한다.** §2-3 이 phantom4·mavic4pro 만 냈다 — 5기종 × 3밴드로 확장.
11. **원시 σ(az) 배열을 JSON 에 함께 저장한다** (`sigma_raw`). 현재 저장된 `sigma_smooth` 는 밴드 5주파수 평균 + 3° 각도창을 거친 값이고, 우리 코드 자신이 그 후처리가 널을 **18 dB** 메운다고 적어 뒀다(`src/rcs_po.py:191-193`: 단일주파수 −59.2 → 대역평균 −45.0 → +3° 창 −41.0 dBsm). 분포 적합은 **원시로만** 해야 한다.
12. **μ(f) = a·f + b, ε(f) = c·f + d 회귀를 우리 5기종에 대해 낸다.** 3점 회귀는 빈약하므로 1.8–6 GHz 를 0.2 GHz 간격으로 스윕해 ≥20점을 만든다. 기준선: multiband Phantom 3 a=0.21, mono3d θ=90° a=0.315 dB/GHz.
13. **분포 적합 + 적합도 거리.** Rician / Gamma / log-normal 을 우리 원시 방위 표본에 MLE 적합하고 두 거리를 모두 낸다 —
    - Anderson–Darling (multiband 식 5): `d_AD = −K − (1/K)Σ_k(2k−1)[ln F(σ_(k)) + ln F(σ_(K+1−k))]` (오름차순 정렬 필수)
    - Cramér–von Mises (mono3d): `d_C = √(1/(12N) + Σ_i|F(σ(φ_i)) − (2i−1)/(2N)|²)`
    기준: multiband Phantom 3 Rician 0.436(최선) / mono3d 평균 Rician 0.28 < Gamma 0.31 < LogNormal 0.48.
14. **보고 지표를 '평균전력 정규화 σ 의 1%/10% 분위점' 으로 추가한다** (mono3d IV절). 우리 `sigma_smooth` 기준 값을 이미 냈다 —

    | 기체 | LTE P10/P1 | 5G P10/P1 | WiFi P10/P1 |
    |---|---|---|---|
    | mini5pro | −9.08 / −13.39 | −8.55 / −12.18 | −8.23 / −13.42 |
    | mavic4pro | −7.64 / −10.58 | −6.41 / −11.54 | −6.42 / −11.76 |
    | matrice4e | −9.85 / −13.67 | −7.04 / −11.50 | −10.50 / −16.22 |
    | s1000plus | −8.17 / −11.21 | −5.89 / −9.36 | −7.00 / −9.86 |
    | phantom4 | −9.21 / −15.95 | −12.59 / −16.73 | −9.57 / −14.40 |

    문헌: −8.5 / −18.5 dB(우세성분 有), −10 / −20 dB(無).
    ⚠ **평활 전 원시로 다시 내기 전까지 이 대조는 판정 보류.**
15. **B1(φ) 3GPP 조각 2차식 적합** (unified-rcs Eq.16): `10log₁₀B1 = −min{12((φ−φ_k)/φ_3dB,k)² + c_k, Y_max}`, k=0/90/180/270°. 논문 UAV 값(φ_3dB = 20.84/10.47/15.41/14.51°, c_k = 0.68/−6.52/−5.61/−12.30, Y_max = 4.47)과 병기. **⚠ 각주 필수** — Table V 의 c_k 로 계산한 봉우리와 Fig.10(a) 의 적합 봉우리가 최대 6.7 dB 어긋난다.
16. **RMSE[dB] 한 숫자로 적합오차를 보고** (unified-rcs Eq.18). 기준: AAV 2.414 / vehicle 1.831 / human 2.245.
17. **바이스태틱 근사 오차 상한을 한 줄로 증명해 둔다** (md-multiprop Appendix D): `Err ≤ (l²/2)(1/R_T + 1/R_R)`. 우리 R1=18.75, R2=18.61 m, 최대 블레이드 반길이 l≈0.19 m → **Err ≤ 1.9 mm**, 바이스태틱 거리의 0.005%.
18. **거리분해능을 이중 표기한다.** 우리 규약 = 바이스태틱 거리합 `c/B`; md-multiprop(Willis) 규약 = 이등분선 방향 `c/[2B·cos(β/2)]`. 같은 물리인데 변수가 다르다 (WiFi 예: 3.916 m ÷ (2×0.915) = 2.14 m). ⚠ md-props 학회판은 `c/(2B)` 라 적었고 저널판이 정정했다 — 학회판만 읽고 우리 규약을 '2배 틀렸다' 고 판정하면 안 된다.

### P2 — 새 실험이 필요한 것

19. **클러터 도플러퍼짐 주입 + 재판정** (§6-2). VERIFY_CLUTTER.md §7-4 의 미해결 숙제를 clutter 서베이가 정확히 처방한다.
20. **hot clutter 추가** (§6-3).
21. **σ 요동을 Pd 에 넣는다** — 현재 고정 σ(Swerling 0/V). mono3d 의 'poor' 케이스(P10 −10 / P1 −20 dB)는 지수분포 이론값(−9.77 / −19.98 dB)과 정확히 일치하므로 사실상 Swerling I/II 다. 기종별로 분포를 골라야 한다 — multiband §III-2: *"the best-fit RCS distribution is platform-dependent and no single distribution is suitable for all AAVs."*
22. **동체 진동 항 신설** (md-testbed 식 9): `R_q(t) = R0 + vt + D_v·sin(2πf_v t)·cosθ·cosα_q`, 파라미터 f_v=100 Hz, D_v=0.05 m, α_q=10°. md-multiprop 은 HRR 에서 동체 기여를 살리려면 진동이 **필수(vital)** 라고 결론짓는다. 우리 ECA(0-도플러 널링)를 이 진동이 뚫는지가 직접 시험이다.
23. **광선 유실(Ray-tracing Path Missing) 수렴 증거를 report07 에 싣는다** — 기체별 (발사 광선 수, 표적 적중 비율, 포화 지점). md-rt §III 이 같은 문제를 보고하고 원추 집속으로 푼다.
24. **디랜덤화 3분기(RF / MF / LMMSE)를 `passive_process.py` 에 스위치로** (clutter 식 31). 우리 '이상적 레퍼런스 정합필터' 는 분류상 **MF 분기**다.
25. **경쟁 상쇄기 베이스라인** — RMA(망각계수 ρ≈0.99–0.995), SDC, 심볼평균을 우리 ECA 와 같은 축(상쇄깊이 dB)에 놓는다.
26. **X410 외부 실측 프로토콜 고정**: ① 배경 S21 코히어런트 차감 → ② **6차 Kaiser 창** 레인지 게이팅(mono3d II-C · multiband §II-3b, 둘 다 *"a sixth-order Kaiser window"*; 게이트 폭은 기체 치수 + 거리 불확실성) → ③ 기준체 대비 전력비. ⚠ 기준체 σ_Cal 을 multiband 처럼 전 주파수·전 θb 단일 상수(2.8 dBsm)로 두지 말고 주파수·바이스태틱각별로 산출해 기록한다. ④ **back-to-back(Tx→Rx 직결) 교정**을 필수 단계로 — md-props §III-B: *"an OFDM radar processing was performed ... with a back to back measurement as reference for proper measurement calibration."* ⑤ rpm 은 가정하지 말고 계측한다 — md-props §III-A 는 *"it is desirable to have full control over the rotors' rotation, which is not feasible with most standard commercial drones"* 이라며 Arduino + 회전수 센서 자작 리그로 rpm 을 ground truth 로 삼았다. 우리는 PX4/DJI SDK 텔레메트리로 로깅해 report08 의 '호버 rpm 가정' 을 대체한다.
27. **RT 교정 루프 도입 검토** — hoydis 의 미분가능 RT 경사교정(재질·산란·안테나 패턴을 계산그래프의 학습 파라미터로) + montaner 의 위상정합 지연-도플러 대조 프로토콜. zig-journal 이 자기 future work 5번으로 *"Gradient-based optimization for calibrating digital environments and object representations directly from channel measurements [35]"* 라며 hoydis 를 지목한다.

---

## §5. 우리 주장과의 충돌 (검증 통과한 것만)

각 항목: **(충돌) / (근거) / (우리가 어떻게 답해야 하나)**

### A. ⭐절대 σ 헤드라인이 단일 [N] 등급 앵커에 매달려 있다

- **충돌** — `make_notebook08.py` §6 은 Li & Ling 2017 aspect-peak 를 유일한 판정 근거로 삼아 *"우리 5종이 전부 +8.0 ~ +15.8 dB 밝다"* 라고 쓴다. 그런데 그 앵커는 이 폴더의 두 실측과 **물리적으로 불가능한 방향으로** 어긋난다.
- **근거** — 같은 350 mm 급 DJI 쿼드에 대해:
  | 출처 | 지표 | 값 |
  |---|---|---|
  | Li & Ling 2017 (등급 **[N]**, PDF 부재) | Phantom 2 **aspect-peak** @3–6 GHz | **−27.5 dBsm** |
  | multiband Table III (PDF 확인) | Phantom 3 방위 **선형평균** @3.5 GHz | **−18.46 dBsm** |
  | mono3d IV절 (PDF 확인) | Phantom 3 방위 평균 @3.5 GHz | **−15.05 dBsm** |

  **peak 가 다른 실험실의 mean 보다 9.0~12.5 dB 아래일 수는 없다.** 두 앵커의 절대교정 레벨이 최소 그만큼 다르다는 뜻이다. 실제로 우리 phantom4 의 **mean** 은 multiband mean 과 −0.4 dB 로 맞는데(§2-1), 같은 기체의 **peak** 는 Li & Ling peak 보다 +15.8 dB 위다 — 두 판정이 동시에 참일 수 없다.
- **어떻게 답하나** — ① 헤드라인을 "밝다" 단정에서 **"문헌 절대앵커의 산포가 15~20 dB 라 절대 σ 판정을 보류하고 상대 결론만 주장한다"** 로 바꾼다. ② 판정 행을 우리 세 밴드를 전부 커버하는 **multiband Phantom 3** 로 교체하고 mono3d 를 병기해 3.4 dB 스프레드를 노출한다. ③ Li & Ling 을 계속 쓰려면 PDF 를 확보해 등급 [N]→[P] 로 올리고 σ_Cal 절차를 확인해야 한다.
- **⚠ 반대로, 확인해 보니 결함이 아니었던 것**: 짝짓기 규약은 이미 건전하다. `make_notebook08.py:166-172` 에 `_PAIR_TOL = 0.10` 이 있어 헤드라인 범위는 **대각비 ±10% 안인 짝**(mavic4pro ×0.959, matrice4e ×0.954, phantom4 ×1.000)에서만 잡히고, 하한 +8.07 dB 는 **matrice4e** 에서 나온다(s1000plus 아님). 면적 스케일링 보정 최솟값 `_PAIR_ADJ_LO = +2.59 dB` 도 이미 계산·보고된다. 이 축은 손댈 필요 없다.

### B. ⭐자세축이 문헌과 다르고, 그 편향이 이제 수치로 확정됐다

- **충돌** — 우리 발표용 RCS 표는 el=15°, 문헌 실측은 **전부 수평면(el=0°)**.
- **근거** — mono3d §III-A(θ={90°,0°,180°}) · unified-rcs §III-A(*"elevation angle fixed at 90°"*) · multiband(수평면 원호 한 평면, `elevation` 0회). 내 재실행 결과 편향은 **−0.90 ~ +3.24 dB** (§2-3).
- **어떻게 답하나** — 문헌 대조 전용 **el=0° 컷**을 5기종 × 3밴드로 산출해 report08 표에 병기하고, `make_notebook08.py:687` 의 *"문헌 측정 앙각은 미상"* 각주를 §2-3 표로 대체한다.

### C. ⭐마이크로도플러 — 우리가 "고쳤다"는 SBR 이 유일한 실측에서 멀어지는 방향이다

- **충돌** — `viz_report1.py:851,861` 은 *"Occlusion lowers the static pedestal"*, *"over-stating the static pedestal by 10 to 39 dB"* 라며 PO 를 과대평가로, SBR 을 교정값으로 서술한다. 그런데 정의를 맞춰 보면 **PO 쪽이 실측에 가깝다**.
- **근거** — §3-3 표. 정의 오프셋(+5.5~+11.2 dB)을 내가 npz 로 직접 검증했다. 정의를 맞춘 우리 SBR 스펙트럼 비 = **7.6 ~ 24.6 dB**, 문헌 실측 ≈ **47 dB**. |DC|/std(AC) 기준 PO 는 **17.3 ~ 37.2 dB** 로 SBR 보다 문헌 쪽이다. 특히 **mavic4pro SBR = −2.17 dB** 는 동체+배터리+PCB+암 전체의 정적 반환보다 블레이드 변조가 더 크다는 뜻으로 물리적으로 지지되지 않는다.
- **어떻게 답하나** — ① "가림 이득 / PO 과대평가" 프레임을 **유보**하고 "선행 실측은 PO 쪽에 있다" 를 명기. ② `microdoppler.py` 의 SBR 가림 판정에서 동체 정적 반환이 과다 제거되는지 재검증(mavic4pro 39.3 dB 이상치부터). ③ 지표를 **선 피크 대 선 피크**로 바꿔 보고. ④ 조건차(1/4 로터·탄소 골격·β=60°·그림 판독)를 각주로 병기 — 방향은 명확하나 확정은 아니다.

### D. ⭐검출 Pd 가 비요동 σ 위에 서 있다

- **충돌** — `detection_rx_sweep.json` 은 단일 자세 σ 를 고정값(Swerling 0/V)으로 쓴다. 실측은 방위축 요동이 사실상 Swerling I/II 다.
- **근거** — mono3d IV절: *"the normalized RCS power shows probabilities of 10% and 1% below -8.5 dBsm and -18.5 dBsm under favorable conditions ... for poor-sensing conditions ... the corresponding power thresholds are −10 dBsm and −20 dBsm."* 'poor' 값은 지수분포 이론값 −9.77 / −19.98 dB 와 **정확히** 일치한다. multiband §III-2: *"no single distribution is suitable for all AAVs."* 우리 코드 주석도 이미 인지하고 있다(`freespace_detect.py:1113`).
- **어떻게 답하나** — 몬테카를로 시행마다 σ 를 기종별 최적분포에서 뽑아 Pd·SNR50 을 재산출하고, 고정 σ 대비 **요동 손실**을 별도 열로 낸다. (⚠ mono3d 는 'Rayleigh (Swerling III/IV)' 라고 쓰는데 통상 Rayleigh 진폭 ↔ 지수 전력 ↔ **Swerling I/II** 다. 라벨을 그대로 옮기지 말 것.)

### E. ⭐상시 기준신호로는 마이크로도플러를 원리적으로 못 뽑는다

- **충돌** — §3-4. 45개 (기체 × 모드) 조합 중 **2개만** PRF 게이트를 통과한다.
- **근거** — md-testbed §IV-A: *"If DMRS signals are used as sensing symbols, the downlink sensing symbol interval would be 1×10⁻⁴ s, which might appear to satisfy the PRI requirement. However, because the complete ISAC process includes uplink slots ... the overall sensing symbol density is insufficient for accurate micro-Doppler extraction."* + *"only the use of the entire PDSCH signal ensures that the UAV's micro-Doppler features remain clear and unblurred."*
- **어떻게 답하나** — ① `report1.json` 마이크로도플러의 **PRF 20 kHz = 풀캡처** 조건을 report03/report08 에 명시. ② report11 에 5×9 통과/탈락 표를 싣는다. ③ 검출 서사는 마이크로도플러에 의존하지 않으므로(grep 확인) 헤드라인은 안전하다 — 그 사실 자체를 적어 둔다.

### F. ⭐"스톡 Sionna 는 표적을 못 다룬다" 프레이밍을 좁혀야 한다

- **충돌** — 두 편이 스톡 Sionna RT 만으로 UAV 표적 반환을 만들어 냈다.
- **근거** —
  > clutter §V-A4 (p.74): *"The ToI and UAVs are modeled as simplified 3-D mesh objects imported into Sionna. These meshes are obtained by simplifying publicly available 3-D models in Blender and exporting them in Sionna's XML format"* + *"for monostatic sensing, the target echoes appear as reflected and scattered paths that interact with the target object"* — Proceedings of the IEEE 게재.
  > md-rt §IV-A: *"When the rotating target is a physical model of a propeller, considering that the minimum spatial resolution in Sionna is 0.01 m, the number of scattering centers can be regarded as approaching infinity ... The simulation results are shown in Fig. 4e, which conform to the theoretical expectation."*
- **정직한 반론(우리가 리포트에 써야 할 것)** — 두 편 모두 **표적 σ(dBsm)를 한 번도 보고하지 않는다.** clutter 는 '강한 UAV vs 약한 ToI' 라는 상대적 세기만 필요하고 Pd/Pfa 도 없다. md-rt 는 도플러 **주파수**(1562 Hz)와 회전주기(0.04 s)만 검증하고 **진폭은 검증하지 않으며** 재질도 Sionna 내장 기본값이다. 즉 참으로 주장할 수 있는 좁은 명제는 **"스톡 솔버는 형상·기종·자세별 절대 σ 를 못 낸다"** 뿐이다.
- **추가 귀속 의무** — report07 의 "표적 조준 광선 다발" 절은 md-rt §III 이 먼저 발표한 것과 같은 전략이다(*"a cone with this vector as its main axis is constructed, limiting the spatial range of ray emission in this direction"*). 선행권을 명기하고, 우리 기여를 **절대 진폭 σ + 부위별 재질 + 가림**으로 좁힌다.

### G. ⭐선행이 우리 방법을 명시적으로 비판한다 (report08 §6 인용 프레이밍 오류)

- **충돌** — report08 §6 은 zig-journal 을 *"우리와 가장 가까운 선행"* 으로 인용한다. 그 논문 서론은 SBR+PO 를 **자기 방법의 대척점**으로 놓는다.
- **근거** — zig-journal §I: *"In this hybrid approach, SBR tracks ray trajectories and multiple reflections on the aircraft surface, while PO integration of the induced surface currents yields an accurate computation of the backscattered field and thus the RCS. **This SBR+PO approach, however, is limited to the illuminated region and is not suitable to predict the scattered field in the shadow region of the obstacle. Furthermore, the need to cascade PO after RT negates the computational advantages of RT.**"* + zig-conf: *"the simulation time for the PO solver is around one day, whereas the RT simulation takes only about two seconds"*. 그리고 자기 future work 4번으로 *"Modeling of time-varying substructures (micro-Doppler)"*, 결론부로 *"can also be applied to compute scattering from other objects, such as drones, humans, and micro-Doppler effects"* — 우리 영역을 예고한다.
- **어떻게 답하나** — *"가장 가까운 선행"* → **"우리 방법을 명시적으로 비판한 선행"** 으로 바꾸고 원문을 그대로 인용한 뒤 우리 반론을 한 문장으로 단다: 그들은 **PEC** 차량(2–10 GHz, UTD 유효조건 facet **E > 1.5λ**, 차량 E²/(Rλ) ≈ 0.4–0.6)이고 우리는 **부위별 유전체 소형 드론**(few-λ)이라 UTD 유효조건이 성립하지 않는다. 그리고 **`make_notebook07.py:550-553` 이 이미 자발적으로 공개한 한계**와 **명시적으로 연결**한다 — 우리 리포트는 이미 *"전방산란(β→180°)에서는 조명 게이트와 수신 게이트가 상호배타가 되어 σ ≡ 0 이 되고 … 비볼록 표적의 깊은 널에서는 상반성 σ(û_i,û_s) = σ(û_s,û_i) 가 깨진다. 따라서 이 리포트의 σ 는 모노스태틱 등가값으로 읽어야 하며, 바이스태틱 결론(report12)으로 그대로 상속되지 않는다"* 라고 쓰고 있다. **물리적 인식은 이미 있고 빠진 것은 인용 프레이밍뿐이다.**

### H. 우리 벤치마크 내부의 두 축 불일치 (앵커 대조의 전제 조건)

문헌 대조 이전에 우리 값이 자기 메타데이터와 맞아야 한다. **직접 확인한 것만** 적는다.

1. **헤드라인 σ 의 자세.** `experiment_detection.py:330` 은
   ```python
   sigma_dbsm, _ = drone_rcs_pattern(drone, FC, np.array([abs(az)]))
   ```
   로 호출한다. 시그니처는 `drone_rcs_pattern(drone_key, fc, az_deg, el_deg=0.0, ...)` (`src/rcs_po.py:144`) — **`el_deg` 를 넘기지 않아 기본값 0.0 이 쓰이고, `abs(az)` 가 방위 부호를 뒤집는다.** 그런데 `detection_rx_sweep.json` `meta` 는 `az=−23.806, el=−3.081` 이라 적혀 있다. 즉 **메타가 선언한 자세와 코드가 조회한 자세가 다르다.**
2. **모드별 시간축.** `experiment_detection.py:132` 는 `ref_cpi = np.tile(block, b*M)` 로 송신 블록을 **연속 타일링**하고, `prf = fs/Lf` (라인 151) 로 slow-time PRF 를 블록 길이에서 뽑는다. 반면 같은 JSON 의 `v_unamb_ms` 는 `waveforms.PILOT_RATE_HZ` 의 **물리 반복률**과 각 파형의 **자기 반송파**로 계산된다 — 내가 재계산해 확인했다(G1: 50 Hz × λ(3.5 GHz)/4 = 1.071 m/s ✅ · W1: 1000 Hz × λ(5.21 GHz)/4 = 14.385 ✅ · L1: 1000 Hz × λ(1.843 GHz)/4 = 40.666 ✅). 그런데 시뮬은 전 모드 `FC = 3.5 GHz` 고정이고 `prf` 는 2136.8/1000/2000 이다.

   | 모드 | 시뮬 PRF | `PILOT_RATE_HZ` 물리값 | 10log₁₀(비) |
   |---|---|---|---|
   | W1–W3 | 2136.8 | 1000 (패킷률, 혼잡 AP 대표값) | +3.3 dB |
   | L1 (CRS) | 1000 | 1000 | **0 dB** ✅ |
   | L2/L3 (PRS) | 1000 | 6.25 | +22.0 dB |
   | G1 (SSB) | 2000 | 50 | +16.0 dB |
   | G2/G3 (NR-PRS) | 2000 | 200 | +10.0 dB |

- **어떻게 답하나** — ① `el_deg`·`az` 부호를 넘기도록 고쳐 재실행하거나, 최소한 meta 를 실제 사용값(el=0.0, az=+23.81)으로 정정하고 report12 본문 문구를 맞춘다. ② 모드별 `M_phys = T_CPI × PILOT_RATE_HZ` 를 표에 병기하고, 최소한 **"본 벤치마크는 기준신호가 매 블록 반복된다고 가정한다 = 풀캡처 상한"** 이라고 못박는다. ③ `v_unamb_ms` 를 시뮬 반송파(3.5 GHz)로 재계산하거나 각주로 규약을 분리한다.
  ⚠ SNR50 이 정확히 10log₁₀(M) 로 스케일하는지는 **재실행 없이 단정하지 않는다.** 위 표는 적분 횟수의 불일치만 말한다.
- **⚠ 이 항목은 논문과의 충돌이 아니라 우리 내부 문제다.** 그러나 §2 의 절대값 대조가 의미를 가지려면 먼저 정리돼야 한다.

### I. 원거리장 — 문헌 3편도, 우리도 위반한다

| 출처 | 표적 D | 측정거리 | 요구 2D²/λ | 판정 |
|---|---|---|---|---|
| unified-rcs UAV @10 GHz | 0.43 m(접힘 표기) / 0.81 m(실제) | 6 m | 12.3 / 43.7 m | 위반 |
| unified-rcs 교정구 @28 GHz | 0.5 m | 6 m | 46.7 m | 위반 |
| multiband Phantom 2 | 0.35 m | 2.6 m | 9.1 m @11 GHz | 위반 (논문도 인정) |
| multiband Phantom 3/Mini 2/M350 | — | Table I "**Far-field**" | — | ✅ |
| md-multiprop | 0.65 m | 3.43 m | ≈20 m @7 GHz | 위반 |
| **우리 s1000plus** | 1.348 m (`farfield_gate` 기준) | R1 = 18.75 m | 22.3 / 42.4 / **63.1** m | **전 밴드 위반** |

- **어떻게 답하나** — 링크버짓·검출 표에 **기체 × 밴드별 far-field 게이트 통과/탈락 열**을 넣고 s1000plus 를 회색 처리한다. 우리 SBR 은 무한거리 평면파로 σ 를 내므로(바운딩구에서 평행 발사) **원거리장 σ 를 근접장 기하에 꽂고 있다**는 사실을 명기. `src/freespace_scene.py:farfield_gate` 도크스트링이 이미 63.1 m 를 알고 있다 — 리포트로 끌어올린다.

### J. 편파 — 해소 불가, 명시만 가능

| 출처 | 편파 |
|---|---|
| 우리 SBR | **없음** (스칼라 실수 Γ, `src/rcs_sbr.py`) |
| unified-rcs | Vertical (Table III) |
| mono3d | VV — *"Both the transmitter and receiver (TX and RX) were equipped with vertically polarized directional antennas"* |
| multiband | V (Phantom 2 셋업에만 명시, 나머지 3기는 논문에 없음) |
| md-multiprop | **HH** (반사도 측정, Appendix B) |

- **어떻게 답하나** — 우리 σ 는 편파를 분리하지 않는다는 사실을 표 각주로 상설화한다. Costa 의 HH 와 나머지의 V 를 같은 표에 놓는 것도 그 자체로 미정렬임을 밝힌다.

---

## §6. 클러터 모델링 다음 단계

`VERIFY_CLUTTER.md` §4·§6 이 남긴 구멍은 셋이다 — **유한 ADC 동적범위 · 클러터 도플러퍼짐 · 양자화**.
현재 상태를 정확히 갱신하면 다음과 같다.

### 6-0. ADC 동적범위·양자화는 **이미 메워져 있다** — VERIFY_CLUTTER.md 가 낡았다

`outputs/verify_eca.json` 은 `meta.adc_bits = [12,14,16]`, `meta.dnrs = [30..90 dB]` 로 이미 스윕돼 있다:

| 설정 | 탭 | DNR 30 dB 에서 상쇄깊이 [dB] float / 16b / 14b / 12b |
|---|---|---|
| 5G NR 100 MHz | 32 | 55.77 / 55.77 / 55.69 / **54.60** |
| WiFi 80 MHz | 24 | 30.78 / 30.78 / 30.77 / **30.55** |
| LTE 20 MHz | 14 | 40.74 / 40.74 / 40.74 / **40.72** |

- 12-bit 대가는 **최대 1.17 dB**(5G, DNR 30 dB)다. X410 이 12-bit 이므로 이 값이 실측 상한이다.
- ⚠ clutter 서베이 39쪽 전체에 **ADC·양자화 모델이 없다** — `dynamic range` 0회, `quantization` 은 CSI 양자화 오차 인용 1회, 위상잡음은 각주에서 '보상 가정'. **이 축에서는 우리가 선행보다 앞서 있다.**
- **할 일**: (a) `VERIFY_CLUTTER.md` §6 "남은 리스크" 표의 ADC 행을 **닫힌 것으로 갱신**, (b) 이 스윕이 ECA 상쇄깊이 단계에만 걸려 있고 **Pd/SCR 까지 전파되지 않았다**는 잔여 한계를 대신 적는다.

### 6-1. 밴드 내 주파수 평탄 가정 — Δ(ka) 게이트 (신규)

> clutter §IV-A2a: *"when ∆(ka) ≳ O(1), the frequency-dependent scattering characteristics necessitate subband-based modeling and estimation strategies."*

`Δ(ka) = 2π·D·B/c₀` 를 우리 실제 `ref_bw_mhz` 와 JSON 대각(D)으로 직접 계산했다:

| D [m] (대각) | G1 SSB 7.2 MHz | G2/G3 NR-PRS 98.28 MHz | W1–3 VHT-LTF 76.56 MHz | L1–3 18.0 MHz |
|---|---|---|---|---|
| mini5pro 0.275 | 0.04 | 0.57 | 0.44 | 0.10 |
| mavic4pro 0.441 | 0.07 | 0.91 | 0.71 | 0.17 |
| matrice4e 0.439 | 0.07 | 0.90 | 0.70 | 0.17 |
| **s1000plus 1.045** | 0.16 | **2.15** | **1.68** | 0.39 |
| phantom4 0.350 | 0.05 | 0.72 | 0.56 | 0.13 |
| **챔버 바닥 30 m** | 4.5 | **61.8** | **48.1** | **11.3** |

**읽는 법** — ① 표적 σ 의 밴드 내 평탄 가정은 5G/WiFi 에서 이미 marginal(≈1)이고 **s1000plus 는 위반**(2.15). ② **"5G 는 98.28 MHz" 는 G2/G3 에만 맞다** — G1(SSB)은 7.2 MHz 라 Δ(ka)≈0.07 로 완전히 평탄하다. ③ **바닥/벽 클러터는 전 밴드에서 강하게 주파수 선택적**이다.
**할 일**: report02/report09 에 이 표를 싣고, `floor_ghost()` 가 밴드당 단일 프레넬 |Γ| 를 쓰는 것과 표적 σ 가 밴드 평균 1개인 것을 **명시적 한계**로 적는다. s1000plus·바닥은 서브밴드 처리로 넘길 근거로 삼는다.

### 6-2. 클러터 도플러퍼짐 — 서베이가 정확히 처방한다 (P2 최우선)

우리 `make_cpi` 의 클러터는 `camp * delayed(1.0, ctau)`, 즉 **도플러 항이 0** 인 지연 기준신호의 선형결합이다. ECA 의 기저가 정확히 그것이므로 사영이 **진폭과 무관하게 0** 으로 지운다. `verify_eca.json` `S5_clutter_dead.scr_span_db = 3.4e-09` 는 물리가 아니라 **항등식**이다.

서베이는 이 전제를 정면으로 부정한다:

> clutter §I: *"It can nevertheless exhibit Doppler spread when the receiver and scatterers are in relative motion."*
> §V-A4 (p.73): *"the cold clutter is modeled as a collection of C = 100 scatterers uniformly distributed over four iso-range rings whose radii bracket the target range, with two rings on the near-range side and two on the far-range side. The scatterer azimuth angles are independently drawn from a uniform distribution over [−90°, 90°], and their radial velocities are uniformly distributed over [−1, 1] m/s to represent slow-moving environmental clutter."*

**구체적 실행 절차**
1. `make_cpi` 클러터 생성을 다음으로 교체 — **C = 100 산란체**, 표적 바이스태틱 거리 앞뒤 **4개 iso-range 링**(가까운 쪽 2, 먼 쪽 2), 방위 i.i.d. `U[−90°, 90°]`(챔버 기하로 환산), **반경속도 `U[−1, +1] m/s`**, 반사계수 `β_c,n ~ CN(0, σ²_c(f_n))`, 서브캐리어 간 상관 `ρ_f(Δf) = exp(−|Δf|/B_c)` (B_c 는 평균 PDP 에서 추정).
2. 클러터 반사율 파라미터화는 서베이의 GIT 경험식 `σ₀(λ, φ_dep, σ_h)` (식 39) 를 쓰고, 챔버 바닥은 우리가 이미 실측한 RT 탭(19.3 ns, −14.7 dB / 최강 −9.8 dB)으로 스케일을 고정한다.
3. `CH_CLUTTER_RATIO` 진폭 40 dB 스윕을 **재실행**한다. 지금의 "SCR 변동 3.4e-9 dB = 죽은 파라미터" 결론이 살아남는지가 진짜 시험이다.
4. 서베이의 실증을 기준선으로 삼는다 — RMA 로 0-도플러 능선을 지워도 *"the strong-target components and their leakage remain evident"*, *"slow-time-only processing is insufficient when dominant moving objects occupy nonzero Doppler bins or overlap the Doppler of the ToI."*

### 6-3. hot clutter 추가 (모델에 절반이 통째로 빠져 있다)

> clutter §V-A4: *"pronounced residual interference and leakage persist because the hot-clutter contribution is not confined to a narrowband around fD = 0 and cannot be removed by slow-time background subtraction alone."*

우리 챔버에는 조명원 1기, 외부 비협조 이미터 **0기**다. 실측은 외부 필드테스트(다른 AP·gNB·UE 가 널려 있다)이므로 **시뮬↔실측 격차의 1순위 후보**다.
**할 일**: 외부 이미터 1기를 챔버 스케일로 환산해 넣고, `cold-only` ↔ `cold+hot` 두 조건의 **입력 SCNR** 을 나란히 보고한다. 서베이 기준값: **−45.9 dB(cold-only) → −47.4 dB(cold+hot) → −63.5 dB(Sionna RT site-specific)**. RT 장면이 확률적 장면보다 **16.1 dB 더 어렵다**는 것 자체가 우리 site-specific 노선의 근거다.

### 6-4. 0-도플러 행 삭제를 'MTI 노치' 로 재명명하고 대가를 계상

`run_min_cell.py` 의 `det[zd, :] = False` 는 무비용이 아니다.

> clutter §V-D1 (p.81): *"This map-assisted prenulling is particularly useful for low-velocity or quasi-stationary targets because Doppler-based suppression can be ineffective in that regime and **may suppress the desired echo together with low-Doppler clutter**."*
> §V-A1: SDC 블라인드 널 `f_D^blind = m/(G_d·T_sym)`, *"two-pulse SDC doubles it [the noise variance], and higher order differences further amplify it, necessitating careful threshold calibration."*

우리는 `verify_eca.json` `S4_target_loss` 에 `fd_3db`·`fd_1db`·`v_3db`·손실 곡선을 이미 갖고 있다. **report11(저속·분해능·관측)에 "호버·미세이동 드론이 노치에 먹히는 구간" 표로 낸다.**

### 6-5. 용어를 서베이 분류체계로 교체 (바닥유령 서사의 1급 근거)

| 우리 용어 | 서베이 용어 | 근거 |
|---|---|---|
| 정적 클러터 | **cold clutter** | §I 정의 |
| (아직 없음) 외부 간섭 | **hot clutter** | §I 정의 |
| 바닥 유령 | 클러터가 **아니라** *target-related NLoS multipath* / **virtual anchor** | §VI-C |

> clutter §VI-C (p.85): *"Rather than eliminating target echoes generated via NLoS paths, a complementary paradigm is to exploit strong specular NLoS target reflections since they can provide useful sensing information. ... virtual-anchor-based modeling provides a geometry-consistent interpretation of specular reflections, which helps maintain consistent hypotheses and mitigate ghost artifacts when dominant reflectors can be identified [99]."*
> §VII-B (p.88): *"Such scattering can produce 'ghost' target images that can be exploited for target detection and classification [124]."*

→ `VERIFY_CLUTTER.md` §6 의 *"표적과 함께 도플러가 실린 것은 정의상 클러터가 아니라 유령"* 주장에 **1급 인용 근거가 생겼다.** 그리고 report09 를 '위협' 에서 '미래 자산' 으로 확장하는 논거도 같은 절에 있다.

### 6-6. 실내 환경 모델 선택의 문헌 근거

> clutter Table 2 (p.70): Indoor — 지배적 클러터 특성 *"LoS-dominant; sparse multipath; micro-Doppler"* → 권장 모델 **"Geometric/Sparse parametric"**
> §IV-F2: *"The relatively slowly changing environment facilitates clutter characterization ... Deterministic geometric modeling can also characterize the dominant propagation paths in such environments."*

→ 우리의 (거울상 + 프레넬 닫힌형 + Sionna RT 탭) 방식이 **이 논문이 실내에 권장하는 바로 그 부류**다. 통계적 K/SIRV 모델을 안 쓰는 이유로 인용한다.

### 6-7. 표본 지원과 경쟁 베이스라인

- RMB 규칙 `N_tr ≥ 2D` (공간만 D=N_r, 공간–시간 D=N_r·L). 다중 Rx 로 적응 백색화를 도입할 때 OAS 축소(식 54–55)·FBA(식 56)·공간평활(식 57)을 이식.
- ⚠ **우리 다중 Rx 는 적응 백색화가 아니다** — 코히어런트 합성 + 10log₁₀(N) 이상적 상한이다. `detection_rx_sweep` 의 N=1→4 이득(예: G1 15.20 → 8.81 dB)은 **클러터 널링 이득이 아니라 순수 다이버시티·적분 이득**임을 report12 에 명시해야 한다.
- 공개 코드 `https://github.com/LS-Wireless/Clutter-Aware-ISAC-Tutorial` 로 RDM 생성(2D-DFT)·GLRT 통계·CFAR 를 교차검증하고 `OPENSOURCE.md` '검증후대체' 목록에 추가.

---

## §7. 우리 틈새 (정직하게)

⚠ **아래 "없다" 는 전부 이 13편 범위 안의 이야기다.** 이 폴더 밖의 문헌은 조사하지 않았으므로 "세계 최초" 같은 주장의 근거가 되지 않는다.

### 7-1. 이 13편이 하지 않은 것

| # | 빈칸 | 각 편이 왜 못 채우나 |
|---|---|---|
| 1 | **sub-6 GHz 소형 드론의 절대 σ(dBsm)를, 부위별 재질·유전체 셸 투과·가림을 가진 완전 CAD 메쉬에서 결정론적으로 계산** | mono3d/multiband/unified-rcs = 실측만(기하 모델 0). md-props/md-multiprop = thin-wire + 수동조정 c′_n, **dBsm 0회**. md-testbed = 점산란체 + 무출처 상수 σ_body. md-rt = 스톡 Sionna 로 **도플러 주파수만** 검증, 진폭·dBsm 없음, 재질 = 내장 기본값. clutter = Blender 단순화 메쉬를 넣고도 **σ 를 한 번도 보고 안 함**. zig-* = PEC 차량·구(드론 아님, 유전체 아님) |
| 2 | **상시 통신 기준신호(LTE CRS·5G SSB·WiFi 프리앰블) 기반 패시브 바이스태틱 드론 검출 벤치마크 — ECA→CAF→CFAR, Pd/Pfa/SNR50** | md-testbed = **모노스태틱** ISAC(CSI = D_RX/D_TX 규약, 자기송신 전제), Pd/Pfa/ROC/CFAR 0건. clutter = SCNR 과 정성적 RDM 뿐, **Pd/Pfa/ROC 0건**, ECA/CLEAN/CAF 언급 0회. md-* = 순수 서명 모델링, 검출 성능 없음 |
| 3 | **표적 경유 바닥 유령(표적 도플러를 실은 NLoS)이 CFAR 오검출로 바뀌는 정량 분석** | clutter 는 virtual-anchor/ghost 를 **방향으로만** 제시(수치 없음). md-* 는 무향실+배경차감이라 지면 반사가 없다. 실측 3편은 무향실 |
| 4 | **DPI 상쇄깊이의 ADC 비트 × DNR 스윕** | clutter 39쪽에 ADC·양자화 모델 없음(§6-0). 나머지 12편도 없음 |
| 5 | **5기종 × 3밴드 × 자세 스윕의 σ 원장 하나** | 실측 3편 합쳐 기종 6종이지만 밴드가 조각나 있고(우리 밴드를 전부 커버하는 기체는 **Phantom 3 하나**), 신형 Mavic 4 Pro·Matrice 4E 는 어느 편에도 없다(2024~25 출시) |

### 7-2. 반대로 — 이 13편이 갖고 우리가 못 가진 것

정직성을 위해 같은 무게로 적는다.

| # | 우리에게 없는 것 | 누가 갖고 있나 |
|---|---|---|
| 1 | **실측 데이터가 0건이다.** 우리 σ 는 전부 계산값이다 | mono3d·multiband·unified-rcs·md-props·md-multiprop·md-testbed·montaner·hoydis — 8편이 자체 측정 |
| 2 | **편파 분리가 없다** (스칼라 Γ) | 전 실측편이 V 또는 VV 또는 HH 를 명시 |
| 3 | **바이스태틱 σ 가 없다.** 우리 SBR 은 D = −u 인 모노스태틱 후방산란만 낸다 | multiband(Phantom 2 실측 열)·zig-conf(다중정적)·md-props(β 스윕 실측) |
| 4 | **마이크로도플러 실측이 없고 rpm 이 가정값이다** | md-props 는 Arduino 자작 리그로 rpm 을 ground truth 로 확보 |
| 5 | **RT 교정 루프가 없다** — 우리 재질은 ITU 표에서 온 것이지 측정으로 맞춘 것이 아니다 | hoydis(경사기반 재질 교정)·montaner(77–81 GHz 사운더 위상정합 대조) |
| 6 | **회절이 없다** (에지·정점) | zig-journal/zig-conf 가 UTD + 정점회절 + 이중반사를 Sionna-RT 에 구현 |
| 7 | **계산 효율이 나쁘다** | md-multiprop (p.217): *"the proposed model can be easily implemented, not requiring paid software frameworks or powerful servers or high-performance computing (HPC) systems, for generating a large amount of data."* zig-conf: PO ~1일 vs RT ~2초. 우리 report1 마이크로도플러는 드론 1기 144자세에 207~258 s(GPU) |
| 8 | **곡면 이산화 품질 지표가 없다** | zig-journal 의 `E²/(Rλ)` — *"a physically motivated measure of discretization quality"*, UTD 유효조건 `E > 1.5λ` |

### 7-3. 한 줄 포지셔닝 (이 13편 기준)

> 실측 3편은 **σ 를 재지만 기하를 모른다**. 마이크로도플러 3편은 **기하를 모델링하지만 절대 σ 를 안 낸다**. RT 4편은 **엔진을 확장하지만 표적이 드론이 아니거나(zig-*, 차량 PEC) σ 를 보고하지 않는다(md-rt, clutter)**. 서베이 1편은 **억제 알고리즘을 다 갖췄지만 표적 σ 도 Pd 도 없다**.
> 우리 자리는 그 교차점 — **sub-6 GHz 소형 드론의 결정론적 절대 σ 를, 패시브 바이스태틱 검출 성능(Pd/Pfa)까지 끝까지 연결한 원장** 하나다.
> 그리고 그 원장의 가장 약한 고리는 **실측 앵커가 없다는 것**이다(§7-2-1). X410 외부 실측이 이 노트의 §4-P2-26 규약대로 나와야 §2 의 표가 완성된다.

---

## §8. 출처

### 8-1. PDF 경로

전부 `/home/yunjung/workspace/paper_sionna_Ray/` 아래.

| 약칭 | 파일명 |
|---|---|
| mono3d | `On_Experimental_Analysis_of_Mono-Static_3D_UAV_RCS_for_ISAC_Channel_Modeling.pdf` |
| multiband | `Multiband_Monostatic_and_Bistatic_RCS_Characterization_of_AAVs_for_ISAC_Channel_Modeling.pdf` |
| unified-rcs | `A_Unified_RCS_Modeling_of_Typical_Targets_for_3GPP_ISAC_Channel_Standardization_and_Experimental_Analysis.pdf` |
| md-props | `Modelling_Micro-Doppler_Signature_of_Drone_Propellers_in_Distributed_ISAC.pdf` |
| md-multiprop | `Modeling_Micro-Doppler_Signature_of_Multi-Propeller_Drones_in_Distributed_ISAC.pdf` |
| md-testbed | `UAVs_Rotor_Micro-Doppler_Feature_Extraction_Using_Integrated_Sensing_and_Communication_Signal_Algorithm_Design_and_Testbed_Evaluation.pdf` |
| md-rt | `Micro-Doppler_Signature_Simulation_of_Multirotor_UAVs_Using_Ray_Tracing.pdf` |
| clutter | `Clutter-Aware_Integrated_Sensing_and_Communication_Models_Methods_and_Future_Directions.pdf` |
| zig-journal | `Ray-Based Simulation of Scattering from Discretized Curved Bodies for Vehicular and ISAC Applications .pdf` |
| zig-conf | `Ray-Based_Simulation_of_Multistatic_Scattering_from_Target_Objects_in_ISAC.pdf` |
| montaner | `Deterministic Modeling of Dynamic ISAC Channels in RF Digital Twin Environments.pdf` |
| hoydis | `Learning_Radio_Environments_by_Differentiable_Ray_.pdf` |
| korean-note | `Sionna RT 드론 ISAC 연구.pdf` — **인용 금지** |

### 8-2. 게재처 (PDF 로 확인된 것만)

| 약칭 | 게재처 | 식별자 |
|---|---|---|
| mono3d | 2025 19th European Conference on Antennas and Propagation (EuCAP), 5쪽 | DOI 10.23919/EuCAP63536.2025.10999912 |
| multiband | IEEE Wireless Communications Letters, vol. 15, pp. 3731–3735, 2026 | DOI 10.1109/LWC.2026.3705634 |
| unified-rcs | IEEE Journal on Selected Areas in Communications, vol. 44, pp. 702–716, 2026 (CC-BY 4.0) | DOI 10.1109/JSAC.2025.3608732 |
| md-props | 2024 IEEE Radar Conference (RadarConf24), 6쪽 | DOI 10.1109/RADARCONF2458775.2024.10548468 |
| md-multiprop | IEEE J. Selected Topics in Electromagnetics, Antennas and Propagation, vol. 1, pp. 208–222, 2025 | DOI 10.1109/JSTEAP.2025.3604407 |
| md-testbed | IEEE Trans. Wireless Communications, vol. 24, no. 12, pp. 10166–10182, Dec 2025 | DOI 10.1109/TWC.2025.3578033 |
| md-rt | 2025 IEEE 25th International Conference on Communication Technology (ICCT), pp. 359–364 | DOI 10.1109/ICCT67417.2025.11374154 |
| clutter | Proceedings of the IEEE, vol. 114, no. 1, pp. 52–91, Jan 2026 | DOI 10.1109/JPROC.2026.3675476 · 코드 `github.com/LS-Wireless/Clutter-Aware-ISAC-Tutorial` |
| zig-journal | 프리프린트 (PDF 헤더에 게재처 없음) | arXiv:2604.05991v2 [eess.SP] |
| zig-conf | EuCAP (PDF 에 권·쪽 없음) | — |
| montaner | 프리프린트 / EuCAP | arXiv:2603.28736v1 [eess.SP] |
| hoydis | IEEE Trans. Machine Learning in Communications and Networking | DOI 10.1109/TMLCN.2024.3474639 |
| korean-note | **없음** — 저자·소속·게재처·연도·DOI 전부 부재 | — |

### 8-3. 우리 쪽 원장

| 파일 | 이 노트에서 쓴 것 |
|---|---|
| `outputs/report2_waveform_rcs.json` | `rcs.drones.*.bands.*.{mean,peak,median,min_smooth}_dbsm`, `sigma_smooth`, `meta.el_deg=15.0`, `diagonal_mm` |
| `outputs/report1.json` | `microdoppler.drones.*.{rpm, flash_hz, f_tip_hz, v_tip, gain_db, sbr, po}`, `microdoppler.cfg` |
| `outputs/report1_microdoppler.npz` | slow-time 복소 시계열(6144, PRF 20 kHz) — §3-3 스펙트럼 지표 재계산 |
| `outputs/detection_rx_sweep.json` | `meta.{K,az,el,sigma_dbsm,fc}`, `modes.*.{ref_name,ref_bw_mhz,occupancy,M,prf,v_unamb_ms,range_res_m}`, `curves.*.snr50` |
| `outputs/verify_eca.json` | `meta.{adc_bits,dnrs}`, `S2_dnr`, `S4_target_loss`, `S5_clutter_dead.scr_span_db` |
| `outputs/verify_linkbudget.json` | `config.{TX,RX,TGT}` → β·이등분선 재계산 |
| `src/viz_report2.py:841` · `src/viz_report1.py:783-790` · `src/rcs_po.py:144,179,191-193` · `src/experiment_detection.py:132,151,330` · `src/waveforms.py:112-119` · `src/make_notebook08.py:119-175,687` · `src/make_notebook07.py:534-541` | 정의·규약·결함 확인 |

### 8-4. 이 노트를 위해 새로 계산한 것 (JSON 미수록 — 재현 필요)

| 항목 | 방법 | 위치 |
|---|---|---|
| el=0° vs el=15° σ 편향 (phantom4·mavic4pro × 3밴드) | `drone_rcs_pattern_bw(..., el_deg∈{0,15}, n_f=5, spacing=λ/16)`, az 5° 스텝 72점, GPU 0 | §2-3 |
| 마이크로도플러 스펙트럼 DCpk−ACpk | `report1_microdoppler.npz` → Hann 창 FFT, \|f\|>50 Hz 배제 | §3-3 |
| β·이등분선 앙각·f_tip 보정계수 | `verify_linkbudget.json` config 좌표에서 직접 | §3-2 |
| Δ(ka) 표 | `2π·D·B/c`, D = JSON `diagonal_mm`, B = `ref_bw_mhz` | §6-1 |
| 정규화 σ 분위점 P10/P1 | `sigma_smooth` (⚠ 밴드평균 + 3° 평활 적용된 값) | §4-14 |
