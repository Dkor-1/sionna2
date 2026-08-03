# Sionna RT 기술보고서 — 프로젝트 표준 레퍼런스

> 이 문서는 `2504.21719` 59쪽 전문 정독의 결과물이다. 앞으로 Sionna 에 대한 우리 주장은
> **전부 이 문서의 한 줄을 근거로 삼는다.** 여기에 대응하는 줄이 없는 주장은 근거가 없는 것으로 취급한다.
> PDF 를 다시 열 필요 없이 인용할 수 있도록 쪽번호·식번호·축자 인용을 모두 실었다.

| | |
|---|---|
| 작성 | 2026-08-03 |
| 근거 | `outputs/sionnart_scope.json` · `sionnart_solver.json` · `sionnart_em.json` · `sionnart_boundary.json` + 본 세션 재검증 |
| 서술 규약 | `docs/REBUILD_2026-07-30.md` §5 |
| 쪽번호 규약 | **인쇄 쪽번호 = PDF 쪽번호**(1-indexed). 푸터로 p5·9·19·30·35·38·46·51·59 확인 |
| 인용 규약 | 본문 한국어, 인용문은 원문 영어 그대로, 식은 문서 내 번호로만 지칭 |

---

## 0. 사용 규율 — 네 줄

| 규율 | 내용 |
|---|---|
| **인용 문자열** | `Sionna RT: Technical Report, Version 1.2, arXiv:2504.21719v2, 2025-11-24` 로 고정한다. 파일명의 `v1` 을 근거로 버전을 적지 않는다 |
| **TR / FP 구별** | 솔버가 무엇을 계산하는가 = **TR 만**. 역사·계보 = FP 허용. 매 문장에서 출처를 밝힌다 |
| **범위 한정** | 모든 주장은 **내장(built-in) 솔버**에 대한 것이다. p7 확장 초대 문장을 항상 병기한다 (§7.1 C6) |
| **문서 ≠ 구현** | "문서에 없다"와 "구현에 없다"는 다른 명제다. 후자는 소스 실측이 필요하다 (§8.3) |

---

## 1. 문서 신원

### 1.1 주 문서 (TR)

| 항목 | 값 | 확인 방법 |
|---|---|---|
| 제목 | Sionna RT: Technical Report | PDF 메타데이터 + 표지 |
| 저자 | F. Aït Aoudia, J. Hoydis, M. Nimier-David, B. Nicolet, S. Cammerer, A. Keller | PDF 메타데이터 |
| **표지 버전 문자열** | `2025-11-24 – Version 1.2` | p1 첫 줄 |
| **arXiv 스탬프** | `arXiv:2504.21719v2 [cs.IT] 21 Nov 2025` | p1 좌측 |
| 쪽수 | **59** | `page_count` |
| 번호 붙은 식 | **199** (독립 태그 195개) | 표시식 태그 전수 |
| 그림 | **36** (Figure 1–36) | 캡션 전수 |
| 알고리즘 | **2** (Algorithm 1 = p20, Algorithm 2 = p26) | 본문 |
| 본문 / 부록 / 참고문헌 | 5–38 / 39–55 / 57–59 | 절 표제 스캔 |
| 자기 선언 목적 | "This document details the algorithms employed by Sionna RT to simulate radio wave propagation efficiently, while also addressing their current limitations." (p1) | 초록 |

**⚠ 파일명 함정.** 아카이브 파일명은 `...technical-report-v1.pdf` 이지만 내용은 arXiv **v2** = 문서 **Version 1.2** 다.
이 프로젝트가 반복해 맞아온 오류 유형이므로 §0 의 인용 문자열을 그대로 쓴다.

### 1.2 Version History (p56 원문 표)

| Version | Date | Description |
|---|---|---|
| 1.2 | September 2025 | Support for first-order diffraction and path solver improvements |
| 1.1 | June 2025 | Support for mesh-based measurement surfaces |
| 1.0 | April 2025 | Major release: Complete re-architecture of Sionna RT |

이 표는 **소프트웨어 릴리스 이력**이다. p5 각주 1 이 뒷받침한다 — "As of version 1.2, Sionna RT does not support RISs. It remains available as part of Sionna version 0.19.2."
따라서 **재구축된 1.x 계열에서 1차 회절은 2025년 9월 v1.2 에서 (재)도입되었다.** 2025-04 의 1.0 재구축판에는 회절이 없었다.
표지 날짜(11-24)와 릴리스 날짜(09)가 다르므로 필요하면 둘 다 적는다.

### 1.3 창설논문 (FP) 과의 분리

| | TR | FP |
|---|---|---|
| 식별자 | arXiv:2504.21719v2, Version 1.2 | arXiv:2303.11103v2 (2023-07-19) |
| 쪽수 | 59 | 5 |
| 기술 대상 | Sionna RT **1.2** | Sionna RT **v0.14** |
| EM 수식 | 199개 | **0개** |
| 굴절(refraction) | 지원 (ℐ 에 𝒯 포함, p9) | **미지원** — "For future releases, it is planned to add refraction as well as support for RIS" (p2) |
| 1차 회절 | 지원 | **지원함** — "Sionna RT supports specular and diffuse reflections (i.e., scattering) as well as first-order diffraction." (p2) |
| SBR | 44회 | **0회** (heuristic method 라고만 부름) |
| 해싱 중복제거 | §3.1.3 신규 기여 | 서술 없음 ("Duplicate paths are removed" 한 줄) |
| radar / RCS / physical optics | 0 / 0 / 0 | 0 / 0 / 0 |
| sensing | **0회** | 5회 (응용 동기) |
| ITU 재질 **값** 통합 진술 | **없음** | **있음** (p2, 인용판 P.2040-**2**) |

**각 문서가 지지할 수 있는 것 / 없는 것**

| 진술 유형 | TR | FP |
|---|---|---|
| 현행 솔버가 무엇을 계산하는가 | ✅ 유일한 근거 | ❌ 절대 금지 |
| 상호작용 4종·Fresnel·UTD·확산 수식 | ✅ | ❌ (수식 0개) |
| 출력 집합의 닫힘 | ✅ (p6, p38) | ❌ |
| "2023년 최초의 미분가능 전파 레이트레이서" | △ (p5 서술) | ✅ 정본 |
| "ITU 재질의 주파수 의존 함수가 통합돼 있다" | ❌ 오인용 | ✅ 유일한 근거 (단 P.2040-2) |
| "센싱이 동기다" | ❌ (sensing 0회) | ✅ (응용 동기일 뿐 구현 근거 아님) |

**⚠ 시간 역전 주의.** FP 는 RIS 를 "지원 예정"이라 적었고 TR v1.2 는 "미지원(0.19.2 에만 존재)"이라 적는다. 기능이 후퇴한 사례다.

### 1.4 버전 타임라인

```
v0.14 (2023) FP  정반사 + 확산반사 + 1차 회절 · 굴절 없음
v0.15            diffraction / diffuse reflection 확충 (TR p5)
v0.17            mobility 도입 (TR p5)  ← 객체 속도벡터의 출발점
v0.18 / 0.19.2   RIS 도입 / RIS 마지막 지원 버전
v1.0  (2025-04)  완전 재구축 · 회절 없음
v1.1  (2025-06)  메시 기반 measurement surface
v1.2  (2025-09)  1차 회절 + path solver 개선 ← TR 이 기술하는 판
────────────────────────────────────────────────
v2.0.1           ⚠ 우리 스택. TR 범위 밖 (§8.4)
```

---

## 2. 섹션 맵

한 줄 요약과 쪽 범위. 필요한 곳으로 바로 뛰라고 만든 표다.

### 2.1 본문

| 절 | 쪽 | 한 줄 요약 | 우리 쓰임 |
|---|---|---|---|
| 표지·초록 | 1 | 미분가능성·1.0 재구축·SBR+이미지법+해싱을 선언 | 버전 확인. ⚠ "purely SBR" 문장은 인용 금지 (§7.5) |
| Contents | 2–3 | 목차 | |
| List of Acronyms | 4 | BSDF·CIR·EM·GCS·JIT·LoS·RIS·SBR 8개 | SBR 정의가 여기 있다 |
| **1 Introduction** | **5–7** | 목적·아키텍처·식 (1)–(5)·기여·문서 구조 | ⭐ p5 목적 선언, p6 solver 2종, p7 확장 초대 |
| **2 Essential Concepts** | **8–10** | 용어 정의 | |
| 2.1 Scene Objects and Meshes | 8 | 객체·프리미티브 (o,m)·엣지 (o,m,ι) 삼중항 | 회절 엣지 식별자의 근거 |
| 2.2 Rays and Paths | 8 | 광선·경로 p(L)·깊이 L·소스/타깃 점 정의 | ⭐ target = R³ 의 점 |
| 2.3 Interactions with Scene Objects | 9 | **ℐ = {ℛ, 𝒮, 𝒯, 𝒟} 4종 열거** | ⭐ B4 의 정본 |
| 2.4 Ray Tubes | 9–10 | 광선관. R/T 는 방향만, S/D 는 파면을 바꾼다 | ⭐ 에너지 회계의 뿌리 |
| **3 Path Solver** | **11–30** | CIR 용 솔버 전체 | |
| 3.1 Generating Candidates by SBR | 12–21 | SBR 루프·타입별 유효성 조건 (11)–(17) | ⭐ SBR = 후보 탐색기 |
| 3.1.1 Sampling Initial Ray Directions | 16–17 | 구면 Fibonacci 격자 (18)·기본 N_S = 10⁶ | 표본 예산 |
| 3.1.2 Sampling Interaction Types | 17–18 | 중요도 표집 (19)(20)·q(D)=0.2 | 재질이 표집에 들어가는 자리 |
| 3.1.3 Specular Chain Candidates Deduplication | 18–21 | 서명 (21)·해시 (22)–(24)·Algorithm 1 | ⭐ p19 무한평면 문장 |
| 3.2 Image Method-based Candidate Processing | 22–24 | 이미지 (26)·역추적 (27)·회절 이미지 (28)–(31) | 후보 대부분이 여기서 버려진다 |
| 3.3 Channel Coefficients, Delays, Doppler | 25–28 | **Algorithm 2 (p26)** = 경로당 계산 전부 | ⭐ 면적분 부재의 1차 근거 |
| 3.3.1 Handling Multiple Antennas | 27–28 | 합성 배열 (35)(36) | 다중 Rx 유효조건 |
| 3.3.2 Doppler Shifts | 28 | 두 접근 + 식 (37)(38) | ⭐ Q4 전부가 이 한 쪽 |
| **3.4 Current Limitations** | **28–30** | **저자 자신의 한계 4항목** | ⭐ §5 전문 |
| **4 Radio Map Solver** | **31–38** | 라디오맵 솔버 전체 | Doppler/velocity 0회 |
| 4.1 Definition of Radio Map | 31–32 | 경로적분 형식 정의 (41)(46)(47) | ⭐ p33 "탐색기지 적분기 아님" |
| 4.2 Computation without Diffraction | 33–34 | 단일 SBR 루프·추정기 (52)·가중치 (53) | ⭐ p35 광선관 문장 |
| 4.3 Computation due to Diffraction | 35–36 | 쐐기 위 직접 몬테카를로 (54)(58)(59) | 회절은 SBR 이 아니다 |
| 4.4 Non-Coherent vs. Coherent | 36 | 비간섭 합이라 페이딩을 못 담는다 | |
| 4.5 Handling Multiple Transmit Antennas | 36–37 | 프리코딩 스칼라 α (60)–(62) | |
| 4.6 Practical Notes | 37–38 | 합성배열 한정·메시 측정면·조기종료 (63)·**출력 확장 진술** | ⭐⭐ p38 출력 닫힘 |

### 2.2 부록

| 절 | 쪽 | 한 줄 요약 | 식 |
|---|---|---|---|
| **A Primer on Electromagnetism** | **39–52** | 경로 위 전계 계산의 EM 기반 전체 | (64)–(174) |
| A.1 Coordinate System, Rotations, Vector Fields | 39–40 | GCS·구면 단위벡터·yaw-pitch-roll·Rodrigues | (64)–(75) |
| A.2 Planar Time-Harmonic Waves | 40–41 | 평면파·**복소 비유전율 η = ε_r − jσ/(ε₀ω)** | (76)–(83) |
| A.3 Far Field of a Transmitting Antenna | 41–42 | 구면파 원거리장·패턴 F·이득 G·정규화 | (84)–(97) |
| A.4 Modeling of a Receiving Antenna | 42–43 | 유효개구 A_R = G_R λ²/4π·수신전압 V_R·Friis | (98)–(107) |
| A.5 General Propagation Path | 43–44 | 산란과정 사슬을 단일 행렬 T̃ 로 | (108)–(111) |
| A.6 Frequency and Impulse Response | 44 | H(f) 와 h(τ)·경로계수 a_i 의 정의 | (112)–(116) |
| **A.7 Specular Reflection and Refraction** | **44–46** | TE/TM 분해·기저변환 W·Snell·**Fresnel** | (117)–(130) |
| A.7.1 Single-Layer Slab | 46–47 | 두께 d 를 위상두께 q 로 넣는 슬래브 계수 | (131)–(133) |
| **A.8 Diffraction** | **47–50** | GTD→UTD→Luebbers 계보·Keller 원뿔·회절행렬 | (134)–(163) |
| **A.9 Diffuse Reflection** | **50–52** | 산란계수 S·확산장·**정규화 조건**·예시 패턴 3종 | (164)–(174) |
| B A Brief Overview of Importance Sampling | 52–53 | 무편향 추정·분산·영분산 최적분포 q* | (175)–(182) |
| C Closed-Form Solution for First-Order Diffraction | 53–55 | 모서리 위 회절점의 폐형해 (Fermat) | (183)–(194) |
| D Weighting Factor for Diffraction Radio Maps | 55 | ‖δt/δx × δt/δφ‖₂ 야코비안 유도 | (195)–(199) |
| Version History | 56 | 소프트웨어 릴리스 3판 | |
| References | 57–59 | 42+ 항목. 각 항목 끝의 숫자가 본문 역참조 쪽 | |

---

## 3. 물리 — 상호작용마다 무엇이 계산되는가

### 3.1 뼈대: 경로계수 (4)

경로 하나의 복소계수는 **송신 패턴 · 상호작용 2×2 행렬들의 곱 · 수신 패턴**이다.

```
a_n = (λ/4π) · C_R(θ_R, φ_R)^H · ( Π_{ℓ'=1..ℓ} T_n^(ℓ') ) · C_T(θ_T, φ_T)      … (4), p6
g   = Σ_n |a_n|²                                                              … (5), p6
```

> p6: "T(ℓ′)_n is the 2 × 2 complex-valued matrix modeling the interaction with the ℓ′-th scatterer."

**⭐ 이 구조가 전부다.** 산란체는 경로 위의 2×2 행렬 하나로만 개입한다.
행렬 곱 사슬에 물체의 면적·크기·곡률이 들어갈 자리가 구조적으로 없다.

### 3.2 표면에서 일어나는 일 — 8단계 사슬

Algorithm 2 (p26) 가 경로당 계산의 전부이고, 그 루프는 **상호작용 인덱스 ℓ 에 대해서만** 돈다.

| # | 단계 | 쪽 | 산출/식 | 핵심 |
|---|---|---|---|---|
| 1 | 교차 판정 | 13 | v, n̂, o, m | ⭐ 점 1개 + 법선 1개 + 객체 ID + 삼각형 ID **뿐**. 형상 정보가 전달되지 않는다 |
| 2 | 상호작용 타입 표집 | 17–18 | (19)(20) | 교차마다 **1개만** 샘플. q(D)=0.2 고정, 나머지는 Fresnel 진폭 제곱 비례 |
| 3 | 유효성 기하 검사 | 14–16 | (12)(13) R/T · (16)(17) D | R/T/D 는 확률 0. **𝒮 만 next-event 로 즉시 유효** |
| 4 | 이미지법 정련 | 22–24 | (26)(27) | 공면 + 비차폐 두 조건. 후보 대부분이 여기서 탈락 |
| 5 | 계수 적용 | 26–27 | Alg.2 line 7–8 | `T ← Evaluate_Material(o, χ, …)` → `E ← T·E` |
| 6 | 편파 운반 | 44–46 | (117)–(120) | 2성분 복소벡터 + 기저회전 W |
| 7 | 에너지 회계 | 26 | 1/√γ · 확산인자 | 확산인자는 **경로 끝에서 한 번만** |
| 8 | — | — | — | ⭐ **면적분 단계 없음** |

**1단계 원문** (p13): "the surface normal at the intersection point oriented towards the half-space containing the incident field"
**5단계 원문** (p27): "the electric field is updated by the transfer matrix T(ℓ′)_n, which depends on the intersected object o(ℓ′)_n, the interaction type χ(ℓ′)_n, and other parameters (omitted for brevity)."
→ ⭐ **인자에 형상이 없다.** 이것이 "면적분 없음"의 양성 근거 (b) 다.

**3단계의 비대칭이 이 솔버 구조 전체의 이유다.**
> p14: "Since targets are modeled as points, condition (12) effectively occurs with zero probability"
> p11: "Since specular chains typically carry a significant amount of the transported energy, SBR alone is insufficient for computing CIRs."

### 3.3 상호작용 4종 — 한 표

> p9: "Sionna RT currently supports four types of interactions with scene objects" · "The set of possible interaction types is denoted by ℐ = {ℛ, 𝒮, 𝒯, 𝒟}."

| | ℛ 정반사 | 𝒮 확산반사 | 𝒯 굴절/투과 | 𝒟 회절 |
|---|---|---|---|---|
| 기하 | 반사각 = 입사각 (13) | 법선 반구 균일 표집 | **각편향 0** (직진) | Keller 원뿔 (17) |
| 계수 식 | (127)(128)(129) | (168)–(174) | (127)(128)(130) | (145)(146)(153)–(156) |
| 행렬 구조 | **대각** | 비대각 (Kx) | **대각** | 비대각 (R_n, R_0) |
| 탈편파 | **0** | 있음 (파라미터) | **0** | 있음 |
| 파면 | 방향만 바뀜 | **파면 변형** | 방향만 바뀜 | **파면 변형** |
| 광선관 | 신규 생성 안 함 | **점광원으로 신규 생성** | 신규 생성 안 함 | (회절 확산인자 별도) |
| 표집 확률 | \|r\|² 비례 | S² 비례 | \|t\|² 비례 | **고정 0.2** |
| 유효화 경로 | 이미지법 | next-event 즉시 | 이미지법 | 이미지법 |
| 선형성 | 선형 | **비선형** (p43) | 선형 | 선형 |

> p9 §2.4: "Importantly, specular reflection and refraction through planar surfaces only alter the ray direction. Diffuse reflection and diffraction alter the shape of the wavefront."

### 3.4 정반사·굴절 — Fresnel 과 슬래브 (§A.7, p44–47)

**전제** (p44): "When a plane wave hits a plane interface which separates two materials... We assume in the following description that both materials are uniform non-magnetic dielectrics, i.e. μ_r = 1, and follow the definitions as in [33]." ([33] = ITU-R P.2040-3)

| 단계 | 식 | 쪽 | 내용 |
|---|---|---|---|
| 입사장 → TE/TM 분해 | (117)(118) | 44–45 | ⊥ = TE, ∥ = TM |
| 기저변환 | (119)(120) | 45 | W(â,b̂,q̂,r̂) = [[âᵀq̂, âᵀr̂],[b̂ᵀq̂, b̂ᵀr̂]] |
| Snell | (121)(122) | 45 | 복소 비유전율로 굴절각 |
| 반사·투과 방향 | (125)(126) | 46 | |
| **Fresnel 4계수** | **(127)** | **46** | r⊥, r∥, t⊥, t∥ (일반) |
| 진공입사 축약형 | **(128)** | **46** | ⭐ 회절 (146) 이 재사용하는 식 |
| 2×2 대각 적용 | (129) 반사 / (130) 투과 | 46 | diag(r⊥,r∥)·W·[E_i,s; E_i,p] |
| **슬래브 반사** | (131) | **47** | r = r′(1−e^{−j2q}) / (1−r′²e^{−j2q}) |
| 슬래브 투과 | (132) | 47 | t = (1−r′²)e^{−jq} / (1−r′²e^{−j2q}) |
| **위상두께** | (133) | 47 | q = (2πd/λ)·√(η − sin²θ₀) |

**⭐ 무한 크기 가정이 두 층에 박혀 있다.**

| 층 | 쪽 | 원문 |
|---|---|---|
| 경로 기하 | 19 | "the image method assumes all reflection surfaces extend infinitely, making the exact in-plane position of a primitive irrelevant to the path geometry" |
| 계수 | 46 | "The reflection and refraction coefficients described above assume that the object reflecting the wave or allowing it to penetrate is of infinite size (or thickness)." |
| 에너지 회계 | 35 | "only the source s and diffuse reflection points act as point sources that spawn new ray tubes, whereas specular reflection and refraction points merely deviate existing ray tubes rather than spawning new ones." |

**⭐ 슬래브가 완화하는 것은 두께뿐이다.** p46–47 원문이 "…of infinite size (or thickness). However… the object has a finite thickness." 라고 적는다. **측방 크기는 끝까지 무한이다** (Figure 32).

**⚠ 'locally' 는 우리 낱말이다.** 문서에 2회뿐이고 둘 다 다른 뜻이다 — p8 은 엣지 인덱스가 "identified locally", p50 은 입사파가 "an incoming locally planar linearly polarized wave" 다. **평면인 것은 파(wave)이지 표면이 아니다.** 문서는 표면에 대해 조건 없이 `extend infinitely` / `of infinite size` 라고 쓴다.

**투과의 성질** (p9): "The transmitted rays are traced without angular deflection. Surfaces like walls should be modeled as single flat surfaces" · "However, when computing the transmitted and reflected fields, the thickness of the traversed object is considered."
→ 두께는 **필드에만** 들어가고 기하에는 전혀 반영되지 않는다. 해싱조차 굴절을 건너뛴다 (p19).

### 3.5 회절 — 정확히 어떤 정식화인가 (§A.8, p47–50)

**계보** (p47, 축자):
> "While [36] deals with diffraction at edges of perfectly conducting surfaces, it was **heuristically extended to finitely conducting wedges** in [37]. This solution, which is also recomended by the ITU [38], is implemented in Sionna."
> "However, both [37] and [38] only deal with two-dimensional scenes... We will provide below the three-dimensional version of [37], following the defintitions of [12, Ch. 6]."

| 부호 | 실체 |
|---|---|
| [10] | Keller, GTD, J. Opt. Soc. Am. 52(2), 1962 |
| [12] | McNamara·Pistorius·Malherbe, *Introduction to the UTD*, Artech House 1990 — 3D 형태의 출처 |
| [36] | Kouyoumjian & Pathak, Proc. IEEE 62(11) 1448–1461, 1974 — UTD 원본 |
| **[37]** | **Luebbers, IEEE TAP 32(1) 70–76, 1984 — 실제 구현된 계수의 출처** |
| [38] | ITU-R P.526-15, 2019 |

**⭐ 정확한 한 줄**: "Kouyoumjian–Pathak UTD 를 Luebbers 가 유한도전율 쐐기로 휴리스틱 확장한 판, McNamara 교재의 3D 형태." — `UTD 를 쓴다` 로만 적으면 부정확하다.

**계산 구조**

| 요소 | 식 | 쪽 | 내용 |
|---|---|---|---|
| Keller 조건 | (134) | 48 | cos β′₀ = \|s′ᵀê\| = \|sᵀê\| = cos β₀ |
| edge-fixed 기저 | (135)–(138) | 48 | φ̂′, β̂′₀, φ̂, β̂₀ |
| 각도·sgn | (139)–(144) | 48 | 0-face 기준 φ′, φ |
| **회절 행렬** | **(145)** | **49** | −((D₁+D₂)I − D₃R_n − D₄R₀) · √(1/(s′s(s′+s))) · e^{−jk(s′+s)} |
| **쐐기면 Fresnel** | **(146)** | **49** | R_ν = W·diag(r⊥(θ_r,ν, η_ν), r∥(θ_r,ν, η_ν))·W |
| 반사각 | (147)(148) | 49 | cos θ_r,0 = \|sin φ′\| |
| D₁…D₄ | (153)–(156) | 50 | −e^{−jπ/4}/(2n√(2πk) sin β₀) · cot(·) · F(kL a^±) |
| 보조 | (157)–(159) | 50 | L = ss′sin²β₀/(s+s′), a^±, N^± |
| 전이함수 | (160)(163) | 50 | F(x) = 2j√x e^{jx}∫_{√x}^∞ e^{−jt²}dt |

**⭐ 회절의 재질 의존성은 전적으로 두 쐐기면의 평면 Fresnel 반사계수 (128) 로만 들어온다.** 회절 고유의 재질 모델은 없다.
**주파수 스케일링**은 D_k ∝ 1/√k ∝ √λ 와 전이함수 인자 kL 뿐 — UTD 고유의 것만 있다.

**엣지를 어떻게 얻는가** (p15): "the probability that a ray exactly intersects the edge of a wedge is zero. Therefore, when a ray intersects a primitive and diffraction is sampled…, the intersection point… **is projected onto one of the primitive's edges**"
→ path solver 는 **삼각형의 세 엣지로 교점을 투영**한다. 반면 radio map solver 는 "wedges near the source are detected and stored" (p33) 로 **사전 검출**한다. 두 경로의 쐐기 집합이 일치하는지는 문서가 답하지 않는다 (§8.2).

**기하 전제** (p47): "We consider an infinitely long wedge with unit norm edge vector ê" — 쐐기도 무한히 길다.

**명시적으로 제외된 것**

| 항목 | 근거 |
|---|---|
| 2차 이상 회절 | p30: "calculating the electric field along these high-order diffraction paths **remains an open problem**, and as a result, high-order diffraction is not currently supported." |
| 회절 + 확산반사 혼합 경로 | p16: "the path solver prohibits sampling paths that contain both diffraction and diffuse reflection." |
| PTD 프린지파·등가 엣지 전류·코너 회절·slope diffraction·크리핑파 | ⭐ 낱말 카운트가 아니라 **A.8 전문 정독**으로 확인. A.8 은 (134)–(163) 으로 끝나고 (145) 의 D₁–D₄ 외에 어떤 보정항도 도입하지 않는다 |

### 3.6 확산반사 — 무엇을 위한 모델인가 (§A.9, p50–52)

| 요소 | 식 | 쪽 | 내용 |
|---|---|---|---|
| 에너지 분배 | (164) | 50 | R = √(1−S²). S>0 이면 (127) 에 곱한다 |
| 확산장 | (168) | 51 | (SΓ/‖r−q‖)·√(f_s·cosθ_i·dA)·[Kx 행렬]·E_i |
| Γ | (169) | 51 | 반사되는 전력 비율 — **입사장에 의존** |
| Kx / XPD | (170) | 51 | XPD_s = 10log₁₀((1−Kx)/Kx) |
| **정규화 조건** | **(171)** | **51** | ∫∫ f_s sinθ_s dφ_s dθ_s = **1** |
| Lambertian | (172) | 52 | cos θ_s / π |
| Directive | (173) | 52 | F_{α_R}(θ_i)^{−1}·((1+k̂_rᵀk̂_s)/2)^{α_R} |
| Backscattering | (174) | 52 | −k̂_i 로브 추가, Λ 로 배분 |

**⭐ Q7 의 답 — 문서 자신의 문장 두 개로 못 박는다.**

> p51: "The scattering pattern must be normalized to satisfy the condition [(171)] which **ensures the power balance between the incoming, reflected, and refracted fields**."
> p43: "In some cases, e.g., for diffuse reflection (see (168) in Section A.9), the matrix T̃ **depends on the incoming field and is not a linear transformation**."
> p44: "Note that the matrices T̃_i also ensure appropriate scaling so that the **total received power can never be larger than the transmit power**."

**따라서**: 이 모델은 **전력 정규화 재분배 커널**이다. 반구적분이 1 로 강제되므로 f_s 는 "반사된 에너지를 어느 방향으로 나눌지"만 정한다.
자유 파라미터 S · Kx · α_R · α_I · Λ · χ₁ · χ₂ 는 표면 기하나 미세구조에서 유도되지 않고 사용자가 준다.
위상마저 물리가 아니다 — p51: "χ₁, χ₂ ∈ [0, 2π] are **(optional) independent random phase shifts**".

**절대 정확도 주장의 부재**: TR 59쪽에 실측 대조 검증 절이 없다. 유일한 측정 언급조차 [41] 원논문 결과이고 조건부다 —
p52: "The authors of [41] derived several simple scattering patterns that were shown to achieve good agreement with measurements **when correctly parametrized**."
문서 내 유일한 일치 확인은 p36 의 **자체 두 솔버 간 내부 일관성 검사**다.

**⚠ 'empirical' 은 TR 에 0회다** — 우리 낱말이므로 위 세 문장으로 대체한다 (§7.6 CLAIM-4).

### 3.7 재질 — 표면 응답이 어떻게 결정되는가 (Q3)

**개념적 위상** (p6): "Radio materials are akin to **bidirectional scattering distribution function (BSDF)** in the field of computer graphics, see e.g. [7, Ch. 4.3.1]."
BSDF 는 정규화된 반사율 분포이지 물체의 절대 단면적이 아니다. 이것이 (171) 의 철학과 정확히 같다.

**재질 → 필드 연결고리 전수**

```
재질 ─→ 복소 비유전율 η = ε_r − jσ/(ε₀ω)            … (80), p40   ← 유일한 물리 파라미터
      ├→ Fresnel (127)(128) ─→ 반사/굴절 2×2 (129)(130)
      ├→ + 두께 d ─→ 슬래브 (131)(132)(133)
      ├→ η₀, η_n (쐐기 두 면) ─→ 회절행렬 R_ν (146) ─→ (145)
      └→ S ─→ 확산 (168) 및 정반사 감쇠 R = √(1−S²) (164)
재질 ─→ 상호작용 타입 표집 확률 (20)                              ← 결과값에 영향 없음
```

> p17: "Importantly, the choice of distribution 𝒬 does not affect the calculation of the paths' electric fields, which are solely dependent on the propagation environment."

**⭐ ITU-R P.2040 이 들어오는 지점 — 정확히 두 곳뿐**

| 쪽 | 맥락 | 역할 |
|---|---|---|
| 44 | A.7 도입 "…and follow the definitions as in [33]." | 반사/굴절 **정의·표기**의 출처 |
| 47 | A.7.1 "…computed as described in [33, Section 2.2.2.2]" | 단일층 슬래브 **식**의 출처 |

참고문헌 [33] 항목 끝의 역참조가 정확히 `44, 47` 이다.
**⚠ TR 에는 어떤 재질의 ε_r·σ 수치표도, 주파수 의존 피팅식도 없다.** `concrete` 는 p44 예시 문장 한 번뿐이다.
"ITU 재질 함수가 통합되어 있다"는 진술은 **FP p2** 의 것이고 거기 인용판은 P.2040-**2** 다 (§1.3).

**주파수가 들어오는 경로 3개**

| 경로 | 식 | 성격 |
|---|---|---|
| 전도손실 | (80) | η = ε_r − jσ/(ε₀ω). ε_r·σ 는 상수, ω 가 분모 — **재질 데이터의 주파수 의존이 아니라 정의적 손실항** |
| 슬래브 위상두께 | (133) | q ∝ d/λ. 에탈론 리플. **실질적으로 가장 강한 주파수 의존** |
| 회절계수 | (153)–(160) | D_k ∝ 1/√k |

**문서가 다루지 않는 재질 요소**: 표면 거칠기 (`roughness` 0회) · 자성재질 (μ_r = 1 고정) · 다층/이방성/분산 모델 · 재질 수치 카탈로그.

### 3.8 편파 운반

| 요소 | 식 | 쪽 |
|---|---|---|
| 임의 직교 편파 → TE/TM | (117)(118) | 44–45 |
| 기저변환 W | (119)(120) | 45 |
| 정반사·굴절 대각 | (129)(130) | 46 |
| 회절 비대각 | (145)(146) | 49 |
| 확산 Kx | (168)(170) | 51 |
| 미분가능 실수블록 표현 | (33)(34) | 27 |

> p27: "For dual polarization, two independent electric field vectors are tracked per path."

**탈편파 지도**: 회절 (145) 의 비대각 R_n/R₀ 항과 확산 (168) 의 Kx 항에서**만** 발생한다. 정반사·굴절은 대각행렬이라 탈편파 0.

### 3.9 에너지 회계 (Algorithm 2, p26)

| 변수 | 초기화 | 갱신 | 의미 |
|---|---|---|---|
| r_n | line 3 = 0 | line 10 누적 · line 14/17 리셋 · line 21 마지막 구간 | 현재 광선관이 태어난 뒤 진행 거리 |
| s_n | line 5 = 0 | line 16 회절 직전 r_n 저장 | 회절 확산인자용 입사 구간 |
| γ_n | line 4 = 1 | line 9 γ←γ·q(χ) · line 12 E←E/√γ · line 13 γ←1 | 표집 확률 되돌리기 |
| τ_n | — | line 19/22 | 지연 |
| a_n | — | line 24 (λ/4π)(E_nᵀE_n^rx) · line 26 회절 1/√(s r(s+r)) · line 28 그 외 1/r | 최종 계수 |

**⭐ 확산인자를 경로 끝에서 한 번만 적용한다.** 정반사·굴절은 파면 곡률을 전혀 바꾸지 않으므로 발산인자가 1 이고, 이는 **무한평면 반사와 동치**다. 유한 크기·곡률 산란체의 파면 확산이 들어올 자리가 없다.

**보존의 성격** (전부 채널 예산 수준):
- p26: "The remaining ray tubes must therefore compensate for the discarded ones to maintain energy conservation."
- p26: "the channel gain (5)… is accurate **if all specular chains are identified** by the path solver, which is assumed to be the case."
- p51: (171) 반구적분 = 1
- p44: 수신전력 ≤ 송신전력

어디에도 "한 물체가 되돌리는 절대 산란량이 물리적으로 맞다"는 주장이 없다.

### 3.10 도플러·이동성 (§3.3.2, p28 — 이 한 쪽이 전부)

| 접근 | 원문 | 성격 |
|---|---|---|
| ① 스텝-앤-리시뮬 | "moving objects in small incremental steps along their trajectories and recomputing the propagation paths at each step. While this method provides the highest accuracy, it is **computationally expensive**." | 알고리즘으로 정의되지 않음. 한 문장뿐 |
| ② 속도벡터 누적 | "we assign a **velocity vector v(o) ∈ R³ to each object o** and compute the time evolution by accumulating Doppler shifts along the propagation paths." | 식 (37)(38) |

```
ν_n^(ℓ') = ν_n^(ℓ'−1) + v(o_n^(ℓ'))ᵀ(k̂_n^(ℓ') − k̂_n^(ℓ'−1))/λ     … (37)
ν_n      = ν_n^(ℓ) + v(s)ᵀk̂_n^(0)/λ − v(t)ᵀk̂_n^(ℓ)/λ             … (38)
```

**유효조건** (저자 명시): "when trajectory lengths are small (**not exceeding a few wavelengths**)".

| 확인 항목 | 판정 | 근거 |
|---|---|---|
| 속도 = 객체당 R³ 벡터 1개 | ✅ | (37) 이 **교차된 객체 인덱스로만** v 를 조회 — 같은 객체의 어느 표면을 맞아도 동일 속도 |
| 각속도 표현 | ❌ | `angular velocity` 0회. `rotat*` 12회는 전부 좌표계 회전·Rodrigues·부록 C 기하 트릭 |
| 시변 기하 | ❌ | `time-varying` 0회 · `deform*` 0회. ②는 경로 확정 **후** 위상만 바꾼다 |
| 라디오맵 솔버의 이동성 | ❌ | §4 전체에 Doppler/velocity 0회 |

**⭐ 회전 프로펠러 마이크로도플러**: ②로는 원리적으로 불가능하다 (블레이드 팁과 허브가 같은 속도). ①은 원리적으로 가능하지만 TR 이 루프를 정의하지 않고 자세 갱신 규약도 없다.

### 3.11 경로 탐색 기계 — SBR → 이미지법 → 해싱 (B5)

**SBR 의 역할** (p11): "the path solver uses **SBR as a heuristic to find path candidates**." · 절 제목도 같다 — p12 "3.1. Generating Candidates by Shooting and Bouncing of Rays (SBR)".
**저자 자신의 구별** (p33): "the path solver… is **not concerned with evaluating an integral** but rather with **finding a set of paths**, which are not aggregated into a single scalar value."

| 요소 | 값/식 | 쪽 |
|---|---|---|
| 초기 방향 | 구면 Fibonacci 격자 (18) · θ_n = arccos(2n/N_S) | 16 |
| 기본 표본 수 | **N_S = 10⁶** | 17 |
| 광선관 개구각 | ≈ 4π/N_S | 16 |
| 후보 서명 | (21) c = (s, (o,m,ι,χ)…), χ ∈ {ℛ,𝒯,𝒟} | 19 |
| 해시 (평면) | 양자화 법선 + 평면 오프셋 d = n̂ᵀp, FNV-1a | 20 |
| 해시 (모서리) | 끝점 6성분, FNV-1a | 20 |
| 롤링 해시 | 1373·curr + inter | 20 |
| 타깃 결합 | (22) | 19 |
| 배열 인덱스 | (23) mod N_H · (24) N_H = max(N_B, 10⁶) | 21 |
| 양자화 | rounding·floor 두 해시 (LSH). "A path is only considered unique if all of its corresponding hash values are unique." | 22 |

**해싱에서 제외되는 것** (p19): 굴절 — "refraction can be omitted from the hashing procedure since it does not change the ray direction". 공면 프리미티브는 동일 취급 — ⭐ 무한평면 문장의 출처.
**확산반사는 해싱이 불필요** (p15): 무작위 표집 점이 일치할 확률이 0 이므로.
**버퍼 정책** (p21): 가득 차면 새 경로를 버린다. 낮은 깊이 경로가 먼저 들어가고 에너지가 크기 때문.
**수율** (p24): "Typically, most of the candidates are discarded by the image method." (Figure 20, p25)

### 3.12 라디오맵 솔버 (§4, p31–38)

| 항목 | 내용 | 쪽 |
|---|---|---|
| 이미지법 | **쓰이지 않는다** | 33 |
| 회절 | SBR 이 아니다 — 쐐기 위 x~U[0,L_E], φ~U[0,nπ] 직접 몬테카를로 (59) | 35–36 |
| 합 방식 | **비간섭** — "does not capture fast fading effects" | 36 |
| 수신기 가정 | 등방·편파정합 ("the receive antenna pattern is not applied") | 32 |
| 배열 | 합성 배열만 지원 | 36 |
| 조기 종료 | gain thresholding · Russian roulette (63) — 약한 경로를 의도적으로 버린다 | 38 |

**⚠ 초록의 "Radio maps are computed using a purely SBR-based approach" (p1) 는 본문과 어긋난다.**
> p33: "However, **SBR is not applicable to paths that include diffraction**… Sionna RT computes the radio map in two steps… First, the radio map is computed for all interaction types except diffraction using a single SBR loop… Second, only diffracted paths are computed."

인용은 초록 대신 이 본문을 쓴다.

---

## 4. 출력 집합 — 솔버가 낼 수 있는 것 전부

**분류가 닫혀 있다** (p6): "Given the distinct algorithmic requirements for CIRs and radio maps, Sionna RT provides **two types of solvers**".

### 4.1 경로 솔버

| # | 출력 | 식 | 쪽 | 근거 |
|---|---|---|---|---|
| 1 | 경로 기하 (상호작용 시퀀스·정점·객체·프리미티브) | (7)(11)(14) | 21 | ⚠ p21 "…and more" 포함 |
| 2 | 경로별 복소 채널계수 a_n | (4) | 6, 26 | Alg.2 line 30 `return a_n, τ_n` |
| 3 | 경로별 지연 τ_n | Alg.2 19/22 | 26 | 동일 |
| 4 | 경로별 도플러 ν_n | (37)(38) | 28 | |
| 5 | 출발/도착각 (θ_T,φ_T),(θ_R,φ_R) | (4) 안 | 5–6 | ⚠ **출력으로 열거되지 않음**. 계산 중간량 |
| 6 | 어레이 채널행렬 H_array,n | (35)(36) | 27 | |
| 7 | CIR h(τ) | (2)(115)(116) | 5, 44 | |
| 8 | 채널 주파수응답 H(f) | (1)(3)(112)(114) | 5, 44 | |
| 9 | 채널 이득 g = Σ\|a_n\|² | (5) | 6 | |
| 10 | 채널 탭 계수 h_i | (50) | 33 | 위 산출물의 sinc 리샘플 |

### 4.2 라디오맵 솔버

| # | 출력 | 식 | 쪽 |
|---|---|---|---|
| 11 | 셀별 채널이득 맵 C_i | (41)(46)(47)(52)(53) | 31–35 |
| 12 | 1차 회절 기여 맵 C_i^(D) 와 합산 | (54)(58)(59) | 35–36 |
| 13 | 프리코딩 반영 맵 | (60)(61)(62) | 36–37 |
| 14 | 메시 기반 측정면 위의 맵 | — | 37 |

### 4.3 메타

| # | 출력 | 쪽 |
|---|---|---|
| 15 | 위 전부에 대한 그래디언트 | 1 (초록) |

### 4.4 ⭐ 닫힘의 근거 — 이것이 추론을 진술로 바꾼다

> **p38 §4.6**: "The Sionna RT solver **currently supports the calculation of channel gain maps**, which are radio maps that provide an estimate of the channel gain for each cell. It is possible to **extend** the solver to calculate other types of radio maps, such as **root-mean-square delay spread maps and angular spread maps** [27]."

저자가 현재 지원 항목을 스스로 열거하고 확장 예시까지 들었는데, **확장 예시조차 산란 단면적류가 아니다.**
따라서 "내장 솔버는 물체의 산란 단면적을 출력하지 않는다"는 진술의 근거는 `RCS` 가 0회라는 사실이 아니라 **문서화된 목록에 그 항목이 없다는 사실**이다.

**양성 근거 5종** (전부 부재 추론이 아님)

| # | 근거 | 쪽 |
|---|---|---|
| a | Algorithm 2 가 경로당 계산 전부인데 면적 루프가 없다 | 26 |
| b | `Evaluate_Material` 인자가 (객체 ID, 상호작용 타입, …) — 형상이 아니다 | 27 |
| c | 교차 판정 산출물이 점·법선·객체 ID·프리미티브 ID 뿐이다 | 13 |
| d | 상호작용 집합 ℐ = {ℛ,𝒮,𝒯,𝒟} 가 닫혀 있다 | 9 |
| e | 출력 목록이 채널량으로 닫혀 있다 | 6, 38 |

**σ 를 얻으려면 필요한 것** — (i) 표면 유도전류 J_s = 2n̂ × H_i 의 조명영역 면적분, (ii) 입사평면파 기준 정규화 원거리장, (iii) σ = 4πr²\|E_s\|²/\|E_i\|² 형태의 비율량. **TR 에 (i)(ii)(iii) 어느 것도 없다.**

---

## 5. 저자 자신의 한계 — §3.4 전문 (p28–30)

**범위 선언** (p28): "We discuss in this section some current limitations and potential improvements of **the path solver**."
→ 라디오맵 솔버에는 대응 절이 없고 §4.6 Practical Notes 에 흩어져 있다.

### 5.1 네 항목

| # | 제목 | 쪽 | 요지 | 우리 관련도 |
|---|---|---|---|---|
| 1 | **Sampling of Ray Directions** | 28–29 | 초기·산란 광선 방향을 안테나 패턴·산란 패턴에 따라 중요도 표집하면 표본 효율이 개선된다. 현재는 균일 표집 | ★★ 소형 표적 직결 |
| 2 | **Handling Large Numbers of Targets and Sources** | 29–30 | 매 SBR 반복마다 전체 타깃을 순회해 시간이 선형 증가. 소스는 총 표본이 N_S·N_O 로 증가 | ★ 다중 Rx 설계 |
| 3 | **Higher-Order Diffraction and Diffuse Reflection** | 29–30 | 1차 회절만·회절+확산 혼합 경로 미처리·고차 회절 전계는 미해결 문제 | ★★★ 최대 관심 |
| 4 | **Collisions of Specular Chain Candidates** | 30 | 해시 인덱스 충돌 시 하나를 그냥 버린다 | ★ 조용한 경로 손실 |

### 5.2 축자 인용 (인용용 원문)

**항목 1** (p28–29)
> "Improved sample efficiency could be achieved by sampling initial ray directions and scattered ray directions based on the transmit antenna pattern and the scattering pattern, respectively. This approach is motivated by the substantial sample efficiency gains shown in Section 3.1.2 through the use of importance sampling."

Figure 23 (p29) 캡션: "The majority of sample directions exhibit low gain, indicating that importance sampling of ray directions may be beneficial."

**항목 2** (p29)
> "The current method for handling multiple targets involves iterating over all targets during each SBR loop iteration… the compute time increases with the number of targets due to the iteration over all targets in each SBR loop iteration. However, the number of candidates per target remains stable, although with variations due to hash collisions. Note that, as discussed in Section 3.2, most candidates do not result in valid paths."
> "When N_S samples are generated per source, the total number of samples produced by the candidate generator becomes N_S·N_O… the number of candidates found per source decreases rapidly as the number of sources increases."

실험 조건: simple street canyon 씬 · 타깃 고도 1.5 m · L = 5 · 확산반사 off · N_S = 10⁶ · NVIDIA RTX 4090.

**항목 3** (p29–30)
> "The path solver supports only first-order diffraction and does not handle paths that contain both diffraction and diffuse reflection. Enabling support for such combined paths would require the refinement of non-suffix path segments, which is computationally expensive and thus not implemented at present. However, these mixed paths typically transport a negligible amount of energy and therefore have little impact on the accuracy of the computed CIRs."
> "Regarding high-order diffraction, there are algorithms for determining the diffraction vertices [22]. However, **calculating the electric field along these high-order diffraction paths remains an open problem**, and as a result, high-order diffraction is not currently supported."

⚠ 인용 가드 2개: (a) 이 문장은 **고차 회절 전계**에 한정된다 — PO 나 1차 회절로 확대 인용하지 않는다. (b) "negligible energy" 자평은 도시 매크로셀 맥락의 것이며 소형 표적에 그대로 이전되지 않는다.

**항목 4** (p30)
> "The path solver does not handle collisions of specular chain candidates. More precisely, when two different specular chains share the same index value in the hash array despite having a different hash due to the modulo operation (23), the path solver discards one of them. This could be avoided by using a collision resolution mechanism, and by dynamically adjusting the hash array size to reduce the probability of collisions. Currently, it is assumed that the hash array size is set to a sufficiently large value to make collisions negligible."

### 5.3 ⭐ 한계 목록에 **없는** 것 — 그리고 그것을 읽는 법

| 목록에 없는 항목 |
|---|
| 물리광학·표면전류 적분의 부재 |
| RCS / 산란단면 출력의 부재 |
| 소형·파장급(few-λ) 물체 처리 |
| 회전 물체·마이크로도플러 |
| 절대 정확도의 실측 검증 |

**올바른 해석**: §3.4 의 네 항목은 전부 **알고리즘 효율·커버리지**에 관한 것이다. 위 항목들이 없다는 것은 "저자들이 몰랐다"가 아니라 **"이 도구의 문제 정의 밖에 있다"**는 뜻이며, p5 의 목적 선언과 정확히 일치한다.

| | 문장 |
|---|---|
| ⛔ **금지** | "저자들이 §3.4 에서 RCS 부재를 한계로 인정했다" — **인용 위조** |
| ✅ **허용** | "저자들의 한계 목록에 표적 산란단면이 없다는 사실 자체가, 물체 귀속 산란량이 이 엔진의 문제 정의에 포함되지 않음을 보여준다" |

### 5.4 §3.4 밖의 저자 주의사항

| 쪽 | 원문 | 우리 쓰임 |
|---|---|---|
| 5 | "As of version 1.2, Sionna RT does not support RISs." | 기능 후퇴 사례 |
| 9 | "Surfaces like walls should be modeled as single flat surfaces" | ★★ 두께 있는 3D 메시 제약 |
| 9 | "modeling transmit antennas as point sources is a valid approximation when the distances to scatterers and targets are significantly greater than the wavelength" | ★★ 근거리·소형표적에서 확인 필요 |
| 16 | "Sionna RT currently supports only first-order diffraction" | p16·23·33·35 에서 반복 |
| 26 | "the channel gain (5)… is accurate if all specular chains are identified… This assumption will be reasonable if the number of samples N_S is sufficiently large." | ★ 표본 부족 시 조용히 틀린다 |
| 27 | "it is an approximation that is valid only when the transmitter and receiver array sizes are small relative to the distance…" | ★ 다중 Rx/대형 배열 |
| 32 | "the receive antenna pattern is not applied… assuming a receiver equipped with an isotropic antenna" | 라디오맵 ≠ 경로솔버 |
| 36 | "However, it only supports synthetic arrays." | 라디오맵 제약 |
| 38 | gain thresholding · Russian roulette (63) | ★ 약산란체 연구에서 주의 |

---

## 6. 경계표 — 엔진 / 우리 / 아무도

**읽는 법**: 행 = 물리 기전. (a) 엔진이 계산하는 것 · (b) 엔진이 하지 않는 것 · (c) 우리가 얹은 것 · (d) 양쪽 모두 덮지 못하는 것.
**⭐ (d)열이 비어 있는 행은 하나도 없다.** 이 열이 논문의 한계 절로 그대로 나간다.

| # | 기전 | (a) 엔진이 한다 | (b) 엔진이 안 한다 | (c) 우리가 얹었다 | (d) 아무도 안 덮는다 |
|---|---|---|---|---|---|
| 1 | **정반사 ℛ** | 이미지법 경로 + 2×2 대각 Fresnel (127)(129) | 유한 크기 보정 · 파면 확산 (발산인자 1) | `rcs_sbr.py` — first-hit 조명면 판정 후 PO 면적분 | 크리핑파/표면파 · 우리 ≥2-bounce 출사 가시성 · PO 격자 산포 |
| 2 | **굴절 𝒯** | 각편향 0 직진 + 슬래브 계수 (131)–(133) | 기하 편향 · 다층벽 · **측방 무한 가정은 유지** | 유전체 셸 왕복 투과 τ=1−\|Γ\|² 2-패스 | 셸 내부 흡수손실 · 다층 CFRP 층간 간섭 · 내부 캐비티 공진 |
| 3 | **확산 𝒮** | S²:R² 배분 + 정규화 패턴 재분배 (164)(168)(171) | S 를 미세구조에서 유도 · 절대 산란량 · 결정론적 위상 · 선형성 | ⭐ **의도적 비사용** — σ 는 PO 적분에서, 재질은 \|Γ\| 로만 | 거친 표면 산란 물리 (Kirchhoff·SPM) · 부분 결맞음 |
| 4 | **회절 𝒟** | 무한 쐐기 1차 UTD (Luebbers) (145)(146)(153)–(156) | PTD · 등가 엣지 전류 · 코너 회절 · 고차 회절 | **없음** — 우리 커널에 엣지 회절 항이 없다 | ⭐⭐ 표적 σ 의 PTD 프린지 보정 |
| 5 | **표면전류 적분** | ⭐ **아무것도 안 한다** (경계의 중심선) | J_s 면적분 · 정규화 원거리장 · σ 정의 | ⭐ **정확히 이 빠진 층** — GO 가림 + PO 적분 | 완전파(MoM/FDTD) 정확도 · PO 자체 오차 · 절대 σ 1차 실측 앵커 |
| 6 | **편파** | ⭐ **엔진이 우리보다 강하다** — 2성분 복소벡터 운반 | 정반사·굴절 탈편파 · 표적 편파산란행렬 | ⚠ **없음 — 후퇴다.** 우리 커널은 스칼라 \|Γ\| | ⭐ 표적 바이스태틱 편파산란행렬 S_b |
| 7 | **이동성·도플러** | 경로 확정 후 도플러 누적, 객체당 R³ 벡터 1개 (37)(38) | 각속도 · 객체 내부 속도장 · 기하 갱신 | `microdoppler.py` — 슬로타임마다 재자세 후 PO 재호출 | 블레이드 공탄성 변형 · CPI 내 표적↔환경 결합 · (시스템) PRF ≳ 2f_tip |
| 8 | **시변 기하** | ⭐ **엔진 안에 시간축이 없다** | 시변 기하의 알고리즘 정의 · 변형체/관절체 | 관절 드론 메시 재자세 — 단 **Sionna 솔버 바깥**에서 | ⭐ 표적·환경 결합 시변 다중경로 · 씬 전체 재시뮬 |

### 6.1 행별 결정 인용

| 행 | 쪽 | 원문 |
|---|---|---|
| 1 | 35 | "only the source s and diffuse reflection points act as point sources that spawn new ray tubes, whereas specular reflection and refraction points merely deviate existing ray tubes rather than spawning new ones." |
| 2 | 46 | "…is of infinite size (or thickness). However… it is often more practical to assume that the object has a finite thickness." → **완화되는 것은 두께뿐** |
| 3 | 51 | "The scattering pattern must be normalized to satisfy the condition [(171)] which ensures the power balance…" |
| 4 | 47 | "…it was heuristically extended to finitely conducting wedges in [37]. This solution… is implemented in Sionna." |
| 5 | 27 | "the electric field is updated by the transfer matrix T(ℓ′)_n, which depends on the intersected object o(ℓ′)_n, the interaction type χ(ℓ′)_n…" |
| 6 | 27 | "For dual polarization, two independent electric field vectors are tracked per path." |
| 7 | 28 | "we assign a velocity vector v(o) ∈ R3 to each object o…" |
| 8 | 28 | "The first approach involves moving objects in small incremental steps along their trajectories and recomputing the propagation paths at each step." |

### 6.2 우리 측 수치 (경계표의 (c)(d) 를 뒷받침하는 실측)

| 항목 | 값 | 출처 |
|---|---|---|
| PO 커널 대 해석 PO 최대 편차 | **0.201 dB** (kr 1–100, 21점, 입사 48방향) | ⟨`outputs/sbr_kr_sweep.json`⟩ |
| 서브셀 오프셋 산포 λ/8 · λ/12 · λ/16 | **5.284 · 1.373 · 1.782 dB** (단조 수렴 아님) | ⟨`outputs/report2_waveform_rcs.json` : sbr_validation.dither⟩ |
| 평판 변 0.2→4 m (σ 52 dB 변화) 시 RT 진폭비 | **−7.91 dB 불변** (산포 0.00 dB), 이론 image-source −7.88 dB | `docs/VERIFY_RT_VS_PO.md` §4[A], `benchmark/verify_rt_no_rcs.py` |
| 확산 S 0.2→1.0 시 진폭비 이동 | **+15.8 dB** (S² 법칙) — 이론값에 맞추려면 S ≈ 0.85 | `docs/VERIFY_RT_VS_PO.md` |
| PEC 구 (S=0) 경로 수 | **0개** (반지름 0.3/1/3 m, spp 1M–16M 전 조건) | `benchmark/verify_rt_no_rcs.py` |
| 해석 PO 대 GO (r=0.5 m) | +0.35 / −0.01 / −0.06 dB (1.84/3.5/5.21 GHz) | `docs/VERIFY_RT_VS_PO.md` |

### 6.3 ⭐ 갭은 결함이 아니라 범위 결정이다

문서 자신의 용어로:

| 사실 | 쪽 | 원문 |
|---|---|---|
| 링크는 **radio device 사이**에 정의된다 | 5 | "The primary objective of Sionna RT is to identify the propagation paths that link radio devices within a given propagation environment." |
| 물체는 **BSDF 유비의 재질**로만 개입한다 | 6 | "Radio materials are akin to bidirectional scattering distribution function (BSDF)…" |
| 경로 종단점 target 은 **점**이다 | 14 | "Since targets are modeled as points…" |
| 출력이 **채널량**으로 닫혀 있다 | 6, 38 | §4.4 |

**우리 층의 정확한 형태**: "엔진의 결함을 고쳤다"가 아니라 **"엔진이 초대한 확장 지점(p7)에 센싱용 층을 얹었다"**.

```
메시(drone_cad/drones) → 재질 단일 진리원(materials) → Mitsuba first-hit 조명면 판정
  → PO 표면적분(rcs_sbr) → 복소 (a, τ, ν) → Sionna PHY cir_to_time_channel 주입(sionna_chain)
  → ECA · 거리도플러 · CFAR(passive_process/radar_process)
```

---

## 7. 인용 치트시트

**규율**: 우리 리포트가 Sionna 에 대해 하는 모든 주장은 아래 표의 한 줄에 대응해야 한다. 대응 줄이 없으면 근거가 없는 것이다.

### 7.1 정체성 · 범위

| # | 주장 | 쪽 | 원문 | 가드 |
|---|---|---|---|---|
| C1 | 목적은 무선기기 사이 전파 경로 탐색이다 | 5 | "The primary objective of Sionna RT is to identify the propagation paths that link radio devices within a given propagation environment." | |
| C2 | 물체는 산란체이고 재질은 BSDF 유비다 | 6 | "Each object acting as a scatterer is associated with a radio material… Radio materials are akin to bidirectional scattering distribution function (BSDF) in the field of computer graphics" | |
| C3 | 경로 끝점을 source/target 이라 부른다 | 6 | "Throughout this document, the endpoints of a path will be referred to as sources and targets, which can be either radio devices or antennas." | ⭐ 86회 전수 확인 결과 레이더 의미 **0건** |
| C4 | target 은 점이다 | 14 | "Since targets are modeled as points, condition (12) effectively occurs with zero probability" | 회절판은 p16 에 동일 문장 |
| C5 | 솔버는 두 종류이고 분류가 닫혀 있다 | 6 | "Given the distinct algorithmic requirements for CIRs and radio maps, Sionna RT provides two types of solvers" | |
| C6 | ⭐ 저자가 커스텀 확장을 초대한다 | 7 | "While Sionna RT provides built-in solvers and radio material models, it is designed to facilitate the implementation of custom alternatives." | ⭐ C24 계열 주장에 **반드시 병기** |

### 7.2 기하 · 경로 탐색

| # | 주장 | 쪽 | 원문 | 가드 |
|---|---|---|---|---|
| C7 | 상호작용은 정확히 4종이다 | 9 | "Sionna RT currently supports four types of interactions with scene objects:" (ℐ = {ℛ,𝒮,𝒯,𝒟}) | |
| C8 | R/T 는 방향만, S/D 는 파면을 바꾼다 | 9 | "Importantly, specular reflection and refraction through planar surfaces only alter the ray direction. Diffuse reflection and diffraction alter the shape of the wavefront." | |
| C9 | 점광원 근사의 유효조건 | 9 | "modeling transmit antennas as point sources is a valid approximation when the distances to scatterers and targets are significantly greater than the wavelength of the propagating waves." | 근거리 실험에서 확인 필요 |
| C10 | ⭐ SBR 은 경로 후보 탐색기다 | 11 | "the path solver uses SBR as a heuristic to find path candidates." | 절 제목도 동일 (p12). 카운트 **44** |
| C11 | ⭐ 반사면은 무한히 뻗어 있다고 가정한다 (기하) | 19 | "This is because the image method assumes all reflection surfaces extend infinitely, making the exact in-plane position of a primitive irrelevant to the path geometry." | ⭐ 부록이 아니라 **솔버 본문**이다 |
| C12 | 경로 버퍼가 담는 것 | 21 | "This buffer holds, for each path, the sequence of interaction types, vertices, intersected objects, primitives, and more." | ⚠ "and more" 를 그대로 둘 것 |
| C13 | 해시 충돌로 유효 경로가 조용히 버려진다 | 21 | "When two different specular chains share the same index value despite being different, the path solver will discard one of them… can result in the discarding of valid paths." | |
| C14 | 에너지 정확도가 "모든 사슬을 다 찾았다"는 가정 위에 있다 | 26 | "the channel gain (5)… is accurate if all specular chains are identified by the path solver, which is assumed to be the case." | |
| C15 | ⭐ 경로 솔버는 적분기가 아니라 탐색기다 | 33 | "the path solver… is not concerned with evaluating an integral but rather with finding a set of paths, which are not aggregated into a single scalar value." | 저자 직접 진술 |
| C16 | ⭐ 정반사는 광선관을 새로 만들지 않는다 | 35 | "only the source s and diffuse reflection points act as point sources that spawn new ray tubes, whereas specular reflection and refraction points merely deviate existing ray tubes rather than spawning new ones." | 발산인자 1 = 무한평면 |

### 7.3 상호작용 · 재질

| # | 주장 | 쪽 | 식 | 원문 | 가드 |
|---|---|---|---|---|---|
| C17 | 투과는 각편향 0, 두께는 필드에만 | 9 | — | "The transmitted rays are traced without angular deflection. Surfaces like walls should be modeled as single flat surfaces… However, when computing the transmitted and reflected fields, the thickness of the traversed object is considered." | |
| C18 | ⭐ 재질 평가 인자에 형상이 없다 | 27 | Alg.2 L7 | "the electric field is updated by the transfer matrix T(ℓ′)_n, which depends on the intersected object o(ℓ′)_n, the interaction type χ(ℓ′)_n, and other parameters (omitted for brevity)." | ⭐ 면적분 부재의 양성 근거 (b) |
| C19 | 합성 배열 근사의 유효조건 | 27 | (35)(36) | "it is an approximation that is valid only when the transmitter and receiver array sizes are small relative to the distance from the radio devices to each other and to the scatterers." | |
| C20 | A.7 전제 — 평면파·평면계면·비자성 | 44 | — | "When a plane wave hits a plane interface which separates two materials… both materials are uniform non-magnetic dielectrics, i.e. μ_r = 1, and follow the definitions as in [33]." | [33] = P.2040-3, **정의의 출처로만** |
| C21 | Fresnel 식과 2×2 대각 적용 | 46 | (127)(128)(129)(130) | "The Fresnel equations provide relationships between the incident, reflected, and refracted field components" | |
| C22 | ⭐ 계수도 무한 크기를 가정 · 슬래브는 두께만 완화 | 46 | (131)(132)(133) | "The reflection and refraction coefficients described above assume that the object… is of infinite size (or thickness). However… it is often more practical to assume that the object has a finite thickness." | ⭐ "완화되는 것은 두께뿐"의 근거 |
| C23 | 전달행렬 설계 기준은 전력 예산이다 | 44 | (111) | "Note that the matrices T̃_i also ensure appropriate scaling so that the total received power can never be larger than the transmit power." | |

### 7.4 출력 · 한계

| # | 주장 | 쪽 | 원문 | 가드 |
|---|---|---|---|---|
| C24 | ⭐⭐ 출력 집합의 닫힘 | 38 | "The Sionna RT solver currently supports the calculation of channel gain maps… It is possible to extend the solver to calculate other types of radio maps, such as root-mean-square delay spread maps and angular spread maps [27]." | ⭐ 낱말 카운트가 아니라 **저자의 목록** |
| C25 | ⭐ 고차 회절 전계는 미해결 문제다 | 30 | "calculating the electric field along these high-order diffraction paths remains an open problem, and as a result, high-order diffraction is not currently supported." | ⚠ **고차 회절 전계 한정**. PO·1차 회절로 확대 금지 |
| C26 | 해시 충돌을 해결하지 않는다 (한계 4) | 30 | "The path solver does not handle collisions of specular chain candidates… it is assumed that the hash array size is set to a sufficiently large value to make collisions negligible." | |
| C27 | 다중 Rx 비용은 타깃 수에 선형이다 | 29 | "The current method for handling multiple targets involves iterating over all targets during each SBR loop iteration." | 우리 벤치마크 설계 근거 |
| C28 | ⭐ 속도는 객체당 R³ 벡터 하나 | 28 | "we assign a velocity vector v(o) ∈ R3 to each object o and compute the time evolution by accumulating Doppler shifts along the propagation paths." | 유효범위 병기: "when trajectory lengths are small (not exceeding a few wavelengths)". `angular velocity` 0회 |
| C29 | 정확한 대안은 스텝-앤-리시뮬뿐이고 비싸다 | 28 | "The first approach involves moving objects in small incremental steps along their trajectories and recomputing the propagation paths at each step. While this method provides the highest accuracy, it is computationally expensive." | |
| C30 | 라디오맵 합은 비간섭이라 페이딩을 못 담는다 | 36 | "The proposed definition of radio maps involves a non-coherent summation of path gains (43). As a result, it does not capture fast fading effects" | |

### 7.5 회절

| # | 주장 | 쪽 | 식 | 원문 | 가드 |
|---|---|---|---|---|---|
| C31 | 회절점은 삼각형 엣지로 교점을 투영해 만든다 | 15 | — | "the intersection point between the ray… and the primitive… is projected onto one of the primitive's edges, yielding the vertex v(ℓ)_n" | |
| C32 | 1차 회절만 · 회절+확산 공존 금지 | 16 | — | "the path solver prohibits sampling paths that contain both diffraction and diffuse reflection… Sionna RT currently supports only first-order diffraction, meaning that paths may contain at most one diffraction event." | |
| C33 | 회절은 계수가 아니라 고정 확률로 표집된다 | 18 | (19)(20) | "In Sionna RT, q(D) is set to 0.2." | |
| C34 | 라디오맵은 'purely SBR' 이 아니다 | 33 | (59) | "However, SBR is not applicable to paths that include diffraction… Sionna RT computes the radio map in two steps… First… using a single SBR loop… Second, only diffracted paths are computed." | ⚠ 초록 p1 의 "purely SBR-based approach" 대신 **이 본문**을 인용 |
| C35 | ⭐ 회절 정식화 계보 | 47 | (145)(146)(153)–(156) | "While [36] deals with diffraction at edges of perfectly conducting surfaces, it was heuristically extended to finitely conducting wedges in [37]. This solution, which is also recomended by the ITU [38], is implemented in Sionna." | [36]=Kouyoumjian–Pathak 1974, [37]=Luebbers 1984, [38]=P.526-15 |
| C36 | 회절 기하는 무한히 긴 쐐기를 가정한다 | **47** | — | "We consider an infinitely long wedge with unit norm edge vector ê" | ⚠ **p47** 이다 (p48 은 Figure 33 캡션) |

### 7.6 확산산란

| # | 주장 | 쪽 | 식 | 원문 |
|---|---|---|---|---|
| C37 | S 는 자유 파라미터이며 반사 에너지를 쪼갤 뿐이다 | 50 | (164) | "we denote by S² the fraction of the reflected energy that is diffusely scattered, where S ∈ [0, 1] is the so-called scattering coefficient [41]" |
| C38 | 확산장 식은 문헌 모델을 가져온 것이다 | 51 | (168)(169)(170) | "According to [42, Eq. 9], the diffusely scattered field Es(r) at the observation point r can be modeled as" |
| C39 | ⭐⭐ 정규화의 목적은 전력수지다 | 51 | (171) | "The scattering pattern must be normalized to satisfy the condition [(171)] which ensures the power balance between the incoming, reflected, and refracted fields." |
| C40 | 확산 위상은 선택적 난수다 | 51 | — | "χ1, χ2 ∈ [0, 2π] are (optional) independent random phase shifts" |
| C41 | ⭐ 확산 전달행렬은 선형변환이 아니다 | 43 | — | "In some cases, e.g., for diffuse reflection (see (168) in Section A.9), the matrix T̃ depends on the incoming field and is not a linear transformation." |
| C42 | 예시 패턴의 출처와 조건부 정확도 | 52 | (172)(173)(174) | "The authors of [41] derived several simple scattering patterns that were shown to achieve good agreement with measurements when correctly parametrized." |

### 7.7 창설논문 (FP) 전용

| # | 주장 | 쪽 | 원문 | 가드 |
|---|---|---|---|---|
| F1 | v0.14 기능 목록 | 2 | "Sionna RT supports specular and diffuse reflections (i.e., scattering) as well as first-order diffraction. … For future releases, it is planned to add refraction as well as support for RIS" | ⚠ 솔버 거동 인용 금지. **역사·계보 전용** |
| F2 | ITU 재질 함수 통합 진술 | 2 | "Radio materials can be defined by frequency-dependent functions, similar to the materials defined by the ITU in [29], which are already integrated into Sionna." | ⚠ 거기 인용판은 P.2040-**2**. TR v1.2 에는 이 진술이 없다 |

### 7.8 Zero-hit 장부 (본 세션 재계수)

> **범위 표기 필수**: "Sionna RT 기술보고서 Version 1.2 **59쪽 전문 기준**".

| 용어 | 횟수 | 용어 | 횟수 |
|---|---|---|---|
| physical optics | 0 | radar | 0 |
| surface current | 0 | monostatic | 0 |
| induced current | 0 | bistatic | 0 |
| equivalent current | 0 | sensing | 0 |
| radar cross section | 0 | ISAC | 0 |
| RCS | 0 | PTD | 0 |
| dBsm | 0 | roughness | 0 |
| **empirical** | **0** | **validation** | **0** |
| angular velocity | 0 | time-varying | 0 |
| **SBR** | **44** | shooting and bouncing | 4 |
| target | 86 | scatterer | 23 |
| surface integral | 1 | Doppler | 9 |
| UTD / GTD | 2 / 3 | P.2040 | 3 |

**카운트 주의사항**

| 항목 | 주의 |
|---|---|
| SBR = 44 | 대소문자 구분. 무시하면 45 인데 1건은 참고문헌 [28] 독일어 `Ausbreitungsbedingungen` 오탐 |
| **48 은 오류** | `shooting and bouncing` 4건(p1 초록·p2 목차·p4 약어표·p12 절제목)은 **전부 같은 문장에 (SBR) 을 달고 있어 이미 44 에 포함**된다. 44+4=48 은 과대계상. **정본은 44** |
| target = 86 | 부분문자열 기준. 단어경계 정규식은 85 (p13 `𝑁𝑇targets` 가 수학 첨자와 붙음) |
| scatterer = 23 | 소문자 21 + 대문자 2 (Figure 8 캡션의 `Scatterer 1` / `Scatterer 2`) |
| surface integral = 1 | ⭐ 참고문헌 [26] Wikipedia 항목(문자열은 **p58 목록**)이고 **본문 역참조가 p35** 다. 라디오맵 회절 적분의 변수변환 야코비안 ‖δt/δx × δt/δφ‖₂ — **측정면 위 기하 면적분이지 유도전류 적분이 아니다** |
| ⚠ **far field** | **0회가 아니다** — 소문자 `far field` 3회 + `Far Field` 2회 = 5. §A.3 제목이 "Far Field of a Transmitting Antenna" 다. 하이픈형 `far-field` 만 0 이다. **`far-field 0회` 로 인용하지 말 것** |
| cross-section = 1 | Figure 28 캡션 "(b) 2D cross-section" — 기하학적 단면도 |

### 7.9 ⭐ 금지 문장 목록

| ⛔ 금지 | ✅ 대체 |
|---|---|
| "Sionna 에는 SBR 이 없다" | "Sionna RT 에는 SBR 이 있다. 다만 역할이 **경로 후보 탐색기**이지 산란장 계산기가 아니다" (p11) |
| "Sionna 에는 회절이 없다" | "1차 UTD 엣지 회절이 있다 (145)(146). 없는 것은 PTD·고차 회절이다" |
| "Sionna 의 UTD 를 가져오면 우리 PTD 결손이 메워진다" | 용도가 다르다 — 씬 쐐기 위 **경로 필드** vs 표적 σ 의 **엣지 보정항** |
| "저자들이 §3.4 에서 RCS 부재를 인정했다" | "한계 목록에 없다는 사실 자체가 문제 정의 밖임을 보여준다" |
| "레이트레이싱은 RCS 를 못 낸다" | "**내장** path/radio-map 솔버의 문서화된 출력에 물체 귀속 산란 단면적이 없다" |
| "Sionna 로는 원리적으로 불가능하다" | p7 이 커스텀 확장을 초대하고, Ziganshin 외(EuCAP 2025)가 실제로 UTD·정점 회절을 얹어 dBsm 을 냈다 |
| "확산 모델은 경험적이다" | "**전력 정규화 재분배 커널**이다" + (171) 목적 + p43 비선형 자인 |
| "국소 무한평면" (무근거 축약) | 우리 요약임을 밝히고 p19(기하) + p46(계수) 를 함께 단다 |
| "ITU-R P.2040 재질 값이 TR 근거로 들어온다" | TR 은 **수식 출처**로만 p44·p47. 값 통합 진술은 FP p2 (P.2040-2) |
| 파일명 근거 "v1" 표기 | `Version 1.2, arXiv:2504.21719v2, 2025-11-24` |
| 축자 인용 자리의 "SBR + image method" | 원문은 p1 "integrates shooting and bouncing of rays (SBR) with the image method and uses a hashing-based mechanism to efficiently eliminate duplicate paths" |

### 7.10 ⚠ 용어 충돌 — SBR 두 가지

| | Sionna 의 SBR | 우리 SBR |
|---|---|---|
| 역할 | **경로 후보 탐색기** (p11) | PO 면적분용 평행광선 격자 (`rcs_sbr.py`) |
| 산출 | 후보 (프리미티브 시퀀스) | 조명면 판정 → σ, 복소 E |
| 표기 | "Sionna 의 SBR(경로 후보 생성)" | "우리 SBR(PO 적분용 광선 추적)" |

구별 없이 쓰면 **"스톡 Sionna 도 SBR 이 있으니 RCS 를 낸다"** 는 잘못된 반론을 자초한다.

---

## 8. ⚠ 아직 읽지 않은 것 · 미해결

이 절을 숨기면 레퍼런스가 아니라 선전물이 된다.

### 8.1 텍스트 추출로 읽었고, 그림으로는 읽지 않은 것

| 항목 | 상태 |
|---|---|
| 본문·부록 59쪽 텍스트 | **전문 추출·정독 완료** |
| **그림 36개의 시각적 내용** | ⚠ **렌더링해서 보지 않았다.** 캡션 텍스트만 읽었다. Figure 5(상호작용 도해)·9/10(솔버 흐름)·13(엣지 투영)·16(공면 해싱)·26(라디오맵 2단계)·31–35(EM 기하)·33(쐐기 좌표계)는 도해가 본문 이해를 보강한다 |
| **정량 그림의 축·수치** | ⚠ Figure 15(중요도 표집 ~100배)·20(후보 대 유효 경로)·23(Fibonacci 이득 분포)·24(확장성)·29(간섭 대 비간섭)는 본문 서술과 캡션으로만 읽었다. 곡선에서 수치를 읽어 인용한 적은 없다 |
| Algorithm 1 (p20) · Algorithm 2 (p26) | 줄 단위로 읽었다. 다만 조판 특성상 일부 기호가 추출에서 깨질 수 있다 |
| 식 199개 중 4개 (25 · 29 · 185 · 186) | 독립 표시 태그가 없다 (인라인 또는 묶음 조판). 번호로 지칭한 적 없음 |
| 수식 내부 기호 | fitz 추출에서 유니코드가 깨지는 사례가 있다 (예: p9 `ℐ = {ℛ, 𝒮, 𝒯, 𝒟}` 가 `{R, S, TD}` 로 보임). **식은 항상 번호로만 지칭한다** |

### 8.2 문서가 답하지 않는 것 (읽었으나 서술이 없음)

| 질문 | 상태 |
|---|---|
| 메시의 어떤 엣지를 "진짜 쐐기"로 인정하는가 | ⚠ **서술 없음.** 외부각 nπ 를 삼각형 메시에서 어떻게 산출하는지도 없다 |
| path solver(엣지 투영)와 radio map solver(사전 검출)의 쐐기 집합이 일치하는가 | ⚠ **문서로 판정 불가** |
| 곡면을 잘게 테셀레이션한 메시에서 인공 엣지가 회절 후보가 되는가 | ⚠ 우리 관심사이나 **문서가 논하지 않는다.** 주장하려면 "보고서에 서술이 없다" 형태로만 |
| 사용자 API 가 실제로 노출하는 필드 목록 | ⚠ TR 범위 밖. p21 "and more" 가 출력 목록의 유일한 열린 표현 |

### 8.3 문서 내부의 표기 불일치 (인용 시 주의)

| # | 위치 | 문제 | 조치 |
|---|---|---|---|
| 1 | p17–18, 식 (20) 설명 | Fresnel 4계수를 "(131)"(슬래브 반사식)로 지시한다. 4계수는 (127)/(128) 이다 | 오탈자로 보이나 확정 불가. **인용은 (127)/(128) 을 쓴다** |
| 2 | p22 | "N_B corresponds to the samples_per_src… N_H corresponds to max_num_paths_per_src" — 정의(N_B=버퍼 크기, N_H=해시 배열)에 비추면 매핑이 뒤집혀 보인다 | ⛔ **소스 실측 전까지 인용 금지** |
| 3 | Algorithm 2 line 24 | 전치 `E_nᵀE_n^rx` 를 쓰는데 (4)/(114) 는 켤레전치 `C_R^H` 다 | 어느 쪽이 구현인지 TR 만으로 판정 불가. **인용은 (4) 를 쓴다** |
| 4 | p1 초록 | "Radio maps are computed using a purely SBR-based approach" 가 p33 본문과 어긋난다 | 본문(§4.1–4.3)을 인용한다 (C34) |

### 8.4 ⭐ 버전 간극 — 가장 큰 미해결

**TR 은 Sionna RT 1.2 를 기술하고 우리 스택은 2.0.1 이다.** 두 버전 사이 솔버 변경 가능성을 문서로 배제할 수 없다.

> **규율**: "우리가 쓰는 엔진이 이렇게 동작한다"는 진술에는 **TR v1.2 인용과 우리 2.0.1 실측을 함께** 댄다.
> 실측 근거: `benchmark/verify_rt_no_rcs.py` — 평판 σ 52 dB 변화에도 진폭비 −7.91 dB 불변, PEC 구(S=0)에서 경로 0개.

### 8.5 우리 쪽에서 이번에 드러난 결손

| 항목 | 상태 |
|---|---|
| ⭐ **편파** | 우리 PO/SBR 커널은 스칼라 \|Γ\| 합이다. 편파 기저도 2×2 도 없다 — 이 행에서 **엔진이 우리보다 강하다**. 편파 다이버시티·편파 판별 실험은 현 커널로 지지되지 않는다 |
| 표적 편파산란행렬 S_b | 양쪽 모두 비어 있는 칸. **향후 작업 후보 1순위** |
| ≥2-bounce 출사 가시성 | `src/rcs_sbr.py:555-557` 미검사. 생산 σ 는 전부 1-bounce 라 현재 무해하나 바이스태틱 확장 시 열린다 |
| TR 에 실측 검증이 없다 | 우리가 Sionna 를 절대 앵커로 쓸 수 없다는 근거인 **동시에**, 우리도 같은 잣대를 받는다는 뜻이다 |

### 8.6 저장소 정정 항목 (다른 워크플로 인계)

| 심각도 | 파일 | 내용 |
|---|---|---|
| 중간 | `docs/PAPER_DRAFT.md:397` (D14) | "SBR 은 48회" → **44**. 같은 파일 98행은 이미 44 로 **문서 내부 자기모순** |
| 중간 | `prior_work/sionna_sensing_survey.md:117` | "SBR 48회" → **44** |
| 낮음 | `outputs/prior_settled_sionna.json` | `"SBR or shooting-and-bouncing": 48` — **합성 카운트**. 44 와 4 로 분리 기록 권장 (48 오류의 뿌리) |
| 중간 | `docs/PRIOR_WORK_COMPARISON.md:352` | "유일한 surface integral 은 …참고문헌(p.35)" — 문자열은 **p58 목록**, 본문 역참조가 p35 |
| 중간 | `src/make_report01_prior.py:132` | 축자 인용 자리의 "SBR + image method" 는 원문 **0 hit**. ⚠ **편집 금지 파일** — 담당 워크플로 인계 |
| 낮음 | `outputs/sionnart_boundary.json` | "infinitely long wedge" 를 p48 로 기록 → 본문 문장은 **p47** (p48 은 Figure 33 캡션) |
| 낮음 | `outputs/sionnart_scope.json` | §3.4 항목 1 을 p29 로 기록 → 소제목·본문은 **p28** (Figure 23 이 p29) |
| 높음(습관) | 리포트·덱 전반 | 파일명 근거 "v1" 표기 → `Version 1.2, arXiv:2504.21719v2, 2025-11-24` |

---

## 부록 — 검증된 식 번호 → 쪽 색인

| 식 | 쪽 | 내용 | 식 | 쪽 | 내용 |
|---|---|---|---|---|---|
| (1)(3) | 5 | H(f) 정의·경로 합 | (127) | 46 | Fresnel 4계수 (일반) |
| (2) | 5 | CIR h(τ) | (128) | 46 | 진공입사 축약형 |
| **(4)** | **6** | **경로계수 a_n** | **(129)(130)** | **46** | **반사·투과 2×2 대각** |
| (5) | 6 | 채널이득 g | (131)(132) | 47 | 슬래브 r, t |
| (11)(12)(13) | 14 | 유효성·방향 (R/T) | **(133)** | **47** | **위상두께 q** |
| (16)(17) | 15 | 유효성·Keller 원뿔 (D) | (134) | 48 | Keller 조건 |
| (18) | 16 | Fibonacci 격자 | (135)–(144) | 48–49 | edge-fixed 기저·각도 |
| **(19)(20)** | **17–18** | **상호작용 표집 분포** | **(145)** | **49** | **회절 2×2 행렬** |
| (21)(22) | 19 | 후보 서명·타깃 결합 | **(146)** | **49** | **쐐기면 Fresnel R_ν** |
| (23)(24) | 21 | 해시 인덱스·배열 크기 | (147)(148) | 49 | 반사각 |
| (26)(27) | 23 | 이미지·역추적 | (153)–(156) | 50 | D₁…D₄ |
| (28)–(31) | 23–24 | 회절 이미지·Fermat | (157)–(159) | 50 | L, a^±, N^± |
| (33)(34) | 27 | 미분가능 실수블록 | (160)(163) | 50 | 전이함수 F |
| (35)(36) | 27–28 | 합성 배열 | **(164)** | **50** | **R = √(1−S²)** |
| **(37)(38)** | **28** | **도플러 누적·총합** | **(168)** | **51** | **확산장** |
| (41)(46)(47) | 32 | 라디오맵 정의 | (169)(170) | 51 | Γ · Kx |
| (50) | 33 | 채널 탭 계수 | **(171)** | **51** | **정규화 조건** |
| (52)(53) | 34 | 라디오맵 추정기 | (172)(173)(174) | 52 | Lambertian·Directive·Backscattering |
| (54)(58) | 35 | 회절 맵 | (175)–(182) | 52–53 | 중요도 표집 (부록 B) |
| (59) | 36 | 회절 추정기 | (183)–(194) | 53–55 | 회절점 폐형해 (부록 C) |
| (60)–(62) | 36–37 | 프리코딩 | (195)–(199) | 55 | 야코비안 가중치 (부록 D) |
| (63) | 38 | Russian roulette | | | |
| (64)–(75) | 39–40 | 좌표계·회전·Rodrigues | | | |
| **(80)** | **40** | **복소 비유전율 η** | | | |
| (84)–(97) | 41–42 | 원거리장·이득·정규화 | | | |
| (98)–(107) | 42–43 | 수신 안테나·Friis | | | |
| (108)–(111) | 43–44 | 사슬 행렬 T̃ | | | |
| (112)–(116) | 44 | H(f)·h(τ) | | | |
| (117)(118) | 44–45 | TE/TM 분해 | | | |
| **(119)(120)** | **45** | **기저변환 W** | | | |
| (121)(122) | 45 | Snell | | | |
| (125)(126) | 46 | 반사·투과 방향 | | | |
