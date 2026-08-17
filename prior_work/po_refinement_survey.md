# PO 를 정밀화하는 방법들 — 선행연구 조사 (2026-08-11)

> **왜 이 조사인가.** 앙각 스윕(matrice4e · 3.5 GHz · 반경 10 m · 0/−15/…/−90°)에서 위상 변동폭이
> 단조롭지 않았고, 사용자가 *"우리 PO 에 대해서 좀 제대로 검증 좀 해봐"* 라고 했다. 커널 판정은
> 별도 라운드(`outputs/verify_po_elev_*.json`)가 하고, **이 문서는 그 옆 질문 하나만 답한다** —
> *"PO 를 다듬기 위한 선행 연구 논문 같은 것도 있을까?"*
>
> 수치 원장: `outputs/po_refinement_survey.json`.
>
> ⚠ **표기 규약.** 항목마다 다음 셋 중 하나를 붙인다.
> · **[원문]** — PDF 를 열어 본문을 읽었다 (해당 절·표·축자 인용을 이 문서에 옮겼다).
> · **[서지]** — 저자·제목·게재처·연도까지는 1차 자료(그 논문의 참고문헌 목록 또는 출판사 페이지)로
>   확인했으나 **본문은 못 읽었다**. 그 논문이 무엇을 주장하는지는 2차 인용으로만 안다.
> · **[미확보]** — 존재는 알지만 서지가 특정되지 않았다. §9 에 모은다.
>
> ⛔ 이 문서는 «최초» 나 «없다» 를 결론으로 쓰지 않는다. 못 찾은 것은 §9 에 «못 찾았다» 로 적는다.

---

## 0. 여섯 줄 요약

1. **③ 곡면 문제는 우리 문제가 아니다 — 재 봤다.** Ziganshin(arXiv:2604.05991 v2, OJAP 투고)의
   이산화 지표 `E²/(Rλ)` 를 **우리 matrice4e 메쉬에서 직접 계산**했더니 부품별 중앙값
   **0.0001 ~ 0.0053**, p90 ≤ 0.028 이다. 그들이 «충분히 곱다» 고 한 선이 **0.5**, 실용 절충대가
   **0.6–0.9** 다. 우리는 그들의 가장 고운 설정보다 **약 100 배 더 곱다**. 기하 이산화가 만드는
   위상오차는 `Δφ ≈ 2π·E²/(Rλ)` ⇒ 중앙값 **약 1°**, p90 **약 10°** 다.
   ⇒ **위상 변동폭 4217° 를 메쉬 탓으로 돌릴 수 없다.** 후보 하나가 수치로 지워졌다.
2. **그리고 같은 논문이 우리에게 정반대 방향의 경고를 한다.** 그들의 UTD 노선은 facet 이
   `E > 1.5λ` 여야 성립한다. 우리 facet 은 **0.018 ~ 0.098 λ** 다. ⇒ **Ziganshin 의 처방(vertex
   diffraction)은 우리 메쉬에 그대로 못 쓴다.** 그들의 두 조건을 동시에 만족하려면
   `R > 4.5λ`(= 3.5 GHz 에서 곡률반경 39 cm 이상)여야 하는데, 메쉬에서 읽은 우리 곡률반경은
   **0.16 ~ 3.58 λ 로 굽은 여섯 그룹 전부가 그 아래**다. **우리 표적은 그 방법의 적용범위 밖에
   있다.** (⭐OUR ARITHMETIC, §4.3)
3. **① 모서리 회절이 문헌상 가장 확실한 «남은 물리» 이고, 하필 우리 문제 구간에서 커진다.**
   Gao(PIER 122, 2012) 축자: 다중반사가 지배하는 **큰 σ** 각도에서는 SBR 단독도 MLFMM 과 잘 맞고,
   *"the edge-diffraction effect, as the secondary dominant scattering mechanism, can not be
   ignored in the case of **weak scattering**"*. 사용자가 물은 −60° 는 변조깊이 0.390 의 **깊은 널**,
   −90° 는 도플러가 물리적으로 0 인 자리 — 둘 다 **약한 산란 구간**이다.
4. **④ 우리 저-kr 6.73 dB 는 «결함» 이 아니라 문헌이 선언한 유효범위 밖이다.** Sagitta(KTH,
   arXiv:2604.09243)가 독립적으로 **kr ≳ 30** 을 광학영역의 시작으로 못 박았다(그 위에서 ±2%).
   우리 `outputs/sbr_kr_sweep.json` 도 **kr ≥ 30 에서 Mie 대비 표준편차 1.55~1.83 %** 이고,
   6.73 dB 는 전부 kr < 30 에서 나온다. **두 잣대가 같은 자리에 선을 긋는다.**
5. **⑤ 편파가 지금 가장 싼 이득이다.** 우리 PO 면적분은 **스칼라(|Γ| 가중)** 다 — 이건 PO 의 한계가
   아니라 **우리가 PO 위에 더 얹은 근사**다. 진짜 PO 는 `J = 2n̂ × H^i` 로 벡터다. 넣으면
   grazing 각 의존이 정확해지고 HH/VV 가 갈라지며, Lee(JEES 2021)가 보인 **cross-pol 로 CW/CCW
   로터를 가르는** 새 관측량이 생긴다.
6. **⑥ 자세 표본은 우리 문제가 아니다.** 문헌 관행은 360°/**512 자세**(Schröder 2016, Speirs 2018)
   이고 우리는 **4096** 이다 — 8 배 조밀하다. 그리고 «자세를 얼려 스냅샷마다 PO» 라는 우리 방식은
   Pouliguen(TAP 2002)이 **quasi-stationary approach** 로 이름 붙인 표준 관행이다.

---

## 1. 먼저 — 우리가 지금 실제로 쓰는 것 (조사의 기준선)

문제의 앙각 스윕이 부른 것은 `benchmark/elevation_sweep_md.py:132` → `rcs_sbr.sbr_field()` 다.
소스에서 확인한 그 함수의 실제 성질:

| 축 | 지금 상태 | 근거 |
|---|---|---|
| 반사 횟수 | **1 bounce** (first-hit 만) | `sbr_field` 는 `ray_intersect` 1 회. 다중반사는 `rcs_sbr(max_bounce≥2)` 별도 경로이고 **배치가 안 된다** (`rcs_sbr.py:218` 주석) |
| 편파 | **스칼라** — `E = Σ |Γ_i| e^{j2k p_i·û} d²` | `rcs_sbr.py:1013` docstring. `ptd_edges.APPROXIMATIONS` 첫 줄: *"PO surface term stays SCALAR (|Gamma| weighted, no pol)"* |
| 모서리 회절 | **꺼짐** (`ptd=False` 기본) | `sbr_field` 시그니처. 스윕 호출부는 `ptd` 를 안 넘긴다 |
| 광선 격자 | `λ/DEFAULT_DIV = λ/12` | `rcs_sbr.py:96` |
| 광선 발산 | **없음** — 평행 격자, 1/r 확산 없음 | `sbr_field` docstring: *"광선은 여전히 평행 격자이고 1/r 확산도 안 넣는다"* |
| 조명 | 구면파 위상 (`range_m`), 광선은 평행 | 같은 곳 |

그리고 PTD 쪽 미구현 목록(`src/ptd_edges.py::NOT_IMPLEMENTED`, 커널이 스스로 적어 둔 것)은
이 조사의 ①·②·⑤ 항목과 **정확히 겹친다**:

> TW (truncated wedge) correction EECs — **ABSENT** … second-order (edge-to-edge) diffraction —
> **ABSENT (0)** … corner / vertex diffraction — **ABSENT (0)** … creeping waves — **ABSENT (0)** …
> cross-polarized (HV/VH) scattering — **not computed**

⇒ **조사의 목적은 이 목록의 각 줄에 «문헌이 매긴 값어치와 값» 을 붙이는 것**이다.

---

## 2. ① 모서리 회절 — PTD / ILDC / MEC / UTD

우리가 이미 가진 정식화 문서는 `docs/PTD_ILDC_FORMULATION.md` (55 KB) 이고, 채택명은
**untruncated Michaeli PTD-EEC (first order)** 다. 그 문서가 이미 Ufimtsev·Michaeli·Mitzner·Knott·
Öztürk·Gao 의 서지와 수식을 담고 있으므로, **여기서는 그 문서에 없는 «수치» 만** 옮긴다.

### 2.1 1차 PTD 로 충분한가 — 아니다, 그리고 «작을수록 부족하다»

**Öztürk, *Implementation of Physical Theory of Diffraction for Radar Cross Section
Computations*, MS thesis, Bilkent Univ., 2002** — **[원문]** (`bilkent_thesis__ptd-implementation-rcs.pdf`)

축자 (p. 44):

> "only the **first order** diffractions are calculated in this work. Since the FW current is assumed
> to be travelling to infinity in accordance with the half plane geometry, **diffraction caused by the
> same current at another edge is neglected (second-order diffraction)**. This effect can also be
> **reduced by using a larger plate**."

그리고 원판 `ka = 5, 10, 15` 삼중 시험 (p. 45, Breinbjerg 1991 의 정확해 대비):

> "the agreement … **improves with increasing disc radius**. The edge interaction effects decrease as
> the disc size becomes larger. **When the disc size is small, the FW surface current possess
> sufficient strength to cause diffraction at the edge point of interest after traversing the disc.**"

실린더 `ka = 2.16, kl = 12.45` 를 Shaeffer 실측과 대조한 뒤 (p. 48):

> "Results of the computer program would be **more accurate if the dimensions of the cylinder were
> electrically larger**."

⇒ **읽는 법.** 2차 회절(모서리→면→다른 모서리)의 크기는 **표적이 작을수록 커진다**. 우리 로터
블레이드(3.5 GHz 에서 코드 방향 ~0.3λ, 스팬 ~4λ)와 짐벌·모터가 정확히 그 체급이다.
⚠ 그리고 이건 «PTD 를 켜면 좋아진다» 가 아니라 «**PTD 를 켜도 1차만으로는 few-λ 에서 부족하다**»
는 뜻이다 — 우리 doc 의 R2-b 근거(Öztürk Fig. 3.10 이 few-λ 에서 PO 단독보다 실측에 가깝다)를
**약화시키지는 않지만 상한을 긋는다**.

### 2.2 회절이 얼마나 값어치가 있는가 — 게재된 수치

**Gao, Wang, Guo, Yang, *A Hybrid Heterogeneous CPU-GPU Architecture for Fast Computation of
Complex Targets' RCS with SBR and TW-ILDCs*, PIER 122: 137–154, 2012** — **[원문]**

- 배(0.9 × 0.2 × 0.2 m, 10 GHz, VV/HH) SBR vs SBR+TW-ILDC vs MLFMM. 축자:
  > "there is a good agreement between the GPU-based SBR result and the MLFMM result **when the values
  > of RCS are relatively large, as multiple bounces dominate at those angles**. However, the
  > edge-diffraction effect, as the secondary dominant scattering mechanism, **can not be ignored in
  > the case of weak scattering**. Thus, the result of the SBR + TW-ILDCs is more accurate than the SBR
  > result, **especially in the incident angles after 180°**."
- 비용 (Table 1, Table 2 — 우리 doc §4.4 와 일치 확인):

  | | 항공기 A | 항공기 B |
  |---|---|---|
  | GPU SBR 단독 | 1311 s | 2302.7 s |
  | TW-ILDC CPU 연산 (step 4+5) | **913.9 s** (SBR 의 70 %) | **2428.2 s** (SBR 의 105 %) |
  | SBR + TW-ILDC 총합 (동적 부하분배) | 1371.4 s (**+4.6 %**) | 2699.9 s (**+17.2 %**) |
  | 직렬판 | 2230.8 s | 4712.2 s |

  ⚠ **+4.6 % 는 연산량이 아니라 월클럭이다.** 모서리항 자체는 PO/SBR 전체와 맞먹는 산술을 요구하고,
  그것을 놀던 CPU 로 밀어 GPU 와 겹쳐 숨겼기 때문에 나온 값이다. 우리는 GPU 한 종류만 쓰므로
  **이 숫자를 그대로 옮기면 안 된다** (이미 우리 doc 이 정정해 둔 항목).
- 정밀도 배분 축자 (§2, 우리 doc 에도 인용됨):
  > "The edge-diffraction effect is **more sensitive to round off** than multiple bounces. … the
  > TW-ILDCs are suitable to be implemented on the **CPU with double precision**, while single
  > precision should be used … in the GPU-based SBR."
- 광선 밀도 기준: *"be greater than **ten rays per wavelength** to ensure the accuracy"* (p. 264).
  ⇒ 우리 `λ/12` 는 이 기준을 만족한다(12 > 10).

**Kırık & Özdemir, *An Accurate and Effective Implementation of Physical Theory of Diffraction to
the Shooting and Bouncing Ray Method via Predics Tool*, Sigma J. Eng. Nat. Sci. 37(4), 2019**
— **[원문]** (`sigma2019_kirik-ozdemir__ptd-into-sbr-predics.pdf`)

- cone-sphere(구 반경 74 mm, 원뿔 높이 605 mm, 9 GHz) 를 Griesser 실측 + FEKO + CST 와 4중 대조.
- **회절만 남는 각도 구간의 수치** (축자, p. 12):
  > "For angles from −100° to −180°, the sphere part of the geometry is not illuminated … **only the
  > diffraction fields are generated** … Therefore, **RCS levels that are almost 45 dB less than the
  > peak RCS value** for this region of look-angle are observed. Similar to Altair FEKO, Predics's RCS
  > simulation produces RCS values that **fluctuate between −35 dBsm and −45 dBsm**. … **CST seems to
  > estimate RCS values somewhat lower** when compared to FEKO and Predics for this region."

⇒ **읽는 법.** «회절만 남는 구간» 은 정점 대비 **−45 dB** 짜리 자리다. 거기서 PO+PTD 는 실측과
±5 dB 안에서 맞고, PTD 가 없는 도구는 **더 낮게** 낸다. 우리 −90°(직하방)·깊은 널이 이 성격의
자리이고, 우리는 **PTD 가 꺼져 있다** ⇒ 문헌대로면 우리는 그 구간에서 σ 를 **낮게** 내고 있을 것이다.

### 2.3 UTD 노선 — PO 를 고치는 게 아니라 대체하는 길

**Ziganshin et al. (2026)** — §4 에서 상술. 요지: 그들은 **PO 를 안 쓴다**. UTD 에지 회절 +
**vertex diffraction**(Albani et al., TAP 57(12):3911–3925, 2009 — **[서지]**) + 2차 회절(EE/EV/VE)로
간다. UTD 는 «무한히 긴 모서리» 를 가정하므로 유한 모서리 끝점에서 불연속이 생기고, vertex
diffraction 이 그 불연속을 메운다. **PO 면적분에는 그 병이 애초에 없다** — 면적분은 연속이다.
⇒ 우리와 그들은 **다른 병을 고치고 있다**. 그들의 처방을 우리 커널에 옮기는 것은 범주 오류다.

**Mukherjee et al. (Remcom), *Blockage Prediction Using KED, UTD, and PO Against 60 GHz
Measurements*** — **[원문]** (`remcom_mukherjee__blockage-ked-utd-po-60ghz.pdf`)

- 인체 차폐를 60 GHz 정밀 실측 스위트와 대조. 축자 (초록):
  > "We found that the **PO method is the most accurate**, but it requires the most computational
  > resources … While the UTD method with the hexagon shape (approximately 42 faces) is slightly less
  > accurate than the PO method, it **provides the best compromise**."

⇒ **PO 가 UTD 보다 정확하다는 것을 실측으로 못 박은 게재물**이다. 우리가 PO 노선에 있는 것은
문헌상 «덜 정확한 길» 이 아니다 — 비싼 길이다.

**Weinmann, *Ray tracing with PO/PTD for RCS modeling of large complex objects*, IEEE TAP
54(6):1797–1806, 2006** — **[서지]** (Ziganshin [9], Kırık, Gao 가 공통 인용. 본문 미확보)
핵심은 **RDN (ray-density normalization)** — 다중반사 뒤 광선관이 발산·수렴하면서 생기는 밀도
왜곡을 정규화해 PO 적분을 유효하게 유지하는 기법. **우리 커널에 없는 것**이고 ② 와 직결된다.

---

## 3. ② 다중반사 — SBR 다중바운스 + PO 를 섞는 표준 방법

### 3.1 표준 구조

**Ling, Chou & Lee, *Shooting and bouncing rays: calculating the RCS of an arbitrarily shaped
cavity*, IEEE TAP 37(2):194–205, 1989** — **[서지]** (모두가 인용하는 원전. 본문 미확보)

표준 구조는 어디서나 같다: **GO 로 입사장을 다중반사로 나른 뒤, 마지막 히트 지점의 유도전류를
PO 로 적분한다.** Ziganshin 이 이걸 한 문장으로 요약한다 — **[원문]**:

> "In this hybrid approach, **SBR tracks ray trajectories and multiple reflections** on the aircraft
> surface, **while PO integration of the induced surface currents yields** an accurate computation of
> the backscattered field and thus the RCS."

⭐ **그리고 바로 다음 문장이 우리 노선에 대한 게재된 비판이다** — 반드시 인용해 둘 것:

> "This SBR+PO approach, however, is **limited to the illuminated region and is not suitable to
> predict the scattered field in the shadow region** of the obstacle. Furthermore, **the need to
> cascade PO after RT negates the computational advantages of RT**."

우리에게 해당하는가: **절반만.** 우리는 그림자 영역 필드를 주장하지 않는다(모노/바이스태틱 후방산란
σ 만 낸다). 두 번째 비판(비용)은 그대로 우리 것이다.

### 3.2 몇 바운스면 되나 — 게재된 값

**Audia, Manocha & Zwicker (Univ. of Maryland), *Accelerated, Memory-Efficient Far-Field Scattering
Computation with Monte Carlo SBR*, arXiv:2511.07586 (IEEE 투고)** — **[원문]**

- SBR 적분방정식을 **몬테카를로**로 다시 쓰고 렌더링의 분산감소 기법을 이식.
- 성능: *"up to a **10–15× reduction in memory usage** and a **4× speed up** in runtime, particularly
  for multilayer dielectric structures."*
- 정확도: *"**1−2 dB of average error** compared to deterministic SBR"* (평판·구·정육면체·이면체·항공기).
- **바운스 수 (우리에게 필요한 숫자)**: PEC 기하는 **3 bounce**, 유전체 평면은 **max 5** 로 설정.
  구·평판·정육면체·이면체 협대역 대조에서 *"once at least [N] bounces … the two algorithms are within
  **0.01 dBsm²**"*.
- 한계 자백: 모서리 회절 등 추가 현상은 **future work** (*"inclusion of additional phenomenology
  like edge diffraction"*).

⇒ **읽는 법.** PEC 표적에서 3 bounce 면 문헌이 수렴으로 본다. 우리는 **1 bounce** 다.
드론은 로터가 동체 **위에** 있어 «로터 → 동체 상면 → 레이더» 경로가 기하학적으로 실재한다.
**그 차이를 아직 아무도(우리도) 안 쟀다.**

### 3.3 광선 밀도 — 두 개의 기준이 있고 우리는 둘 다 만족한다

| 출처 | 기준 | 우리 (`λ/12`) |
|---|---|---|
| Gao PIER 2012 — **[원문]** | *"greater than **ten rays per wavelength**"* | 12 ✅ |
| Sagitta (KTH) — **[원문]** | *"we enforce a conservative sampling rule **Δs ≤ λ/5**"* (≥5 samples/λ) | 12 ✅ (2.4 배 여유) |

**Pasquale, Hu, Pennati, Peng & Markidis (KTH), *BVH-Accelerated Ray Tracing for High-Frequency
Electromagnetic Backscattering* (SagittaSBR), arXiv:2604.09243, ICCS 2026 확장판** — **[원문]**
- A380, 10 GHz: 30,000 × 30,000 광선 격자, **각도당 616.12 ms (FP32)**, 전체 스윕 27 분
  (8 LUMI 노드), 총 1.125 × 10¹⁴ 광선.
- 코드 공개: `github.com/marco-pas/SagittaSBR`.

**Kasdorf, Troksa, Key, Harmon & Notaroš, *Advancing Accuracy of Shooting and Bouncing Rays Method…*,
IEEE TAP, 2021 (DOI 10.1109/TAP.2021.3060051)** — **[원문]**
- per-ray cone angle · 이중계수 제거 · 최적 상수 각도의 해석식.
- ⚠ **우리에게 직접 적용 안 된다.** 이 논문의 «ray cone / reception sphere» 기계는 **수신구를 가진
  전파 예측(터널)** 용이다. RCS 용 SBR+PO 는 수신구가 없고 **개구면 적분**으로 받는다 —
  이중계수 문제가 애초에 다른 형태다. §9 에 «전용 불가» 로 기록.
- 다만 한 문장은 우리에게 유효: 곡률을 평면 조각으로 근사하면 *"many segments can lead to many
  **non-physical images** produced in the model"* (그들은 그래서 곡면 단면을 등가 사각형으로 바꿨다).

---

## 4. ③ 곡면 처리 — ⭐ 사용자가 지목한 논문

### 4.1 서지와 판본 — 먼저 확정한다

**Ziganshin, Vitucci, Kotterman, Thomä, Schneider & Degli-Esposti, *Ray-Based Simulation of
Scattering from Discretized Curved Bodies for Vehicular and ISAC Applications*,
arXiv:2604.05991** — **[원문 정독]**

| | |
|---|---|
| 소속 | TU Ilmenau (EMS/ThIMo) + Univ. of Bologna (DEI) |
| 판본 | **v1 2026-04-07**, **v2 2026-07-02** (arXiv 목록에서 확인) |
| 상태 | ⭐**2026-08-17 갱신 — 게재 확정.** Crossref 원장이 DOI `10.1109/OJAP.2026.3717211` 을 **`type: journal-article`**, container `IEEE Open Journal of Antennas and Propagation`, 저자 6인(Ziganshin·Vitucci·Kotterman·Thoma·Schneider·Degli-Esposti), 연도 2026 으로 등록. ⇒ **심사 통과한 저널 논문**이다.<br>⚠단 **쪽이 `1-1` 이고 권 배정이 없다** — IEEE 의 **Early Access** 표시다. 그러므로 «Vol. 7, pp. 1–13» 으로 인용하면 안 된다(팀 주간보고 2026-08-17 이 그렇게 적었으나 Crossref 와 불일치). 호가 붙을 때까지 **DOI 로만** 인용한다.<br>구 기록(2026-08-11): arXiv 각주 *"preprint version of a manuscript submitted to…"* · journal-ref 없음 ⇒ 그 시점엔 투고 상태였다. |
| 보관함 사본 | `papers_isac_sionna/2604.05991__…pdf` 와 `paper_sionna_Ray_0723/Ray-Based Simulation…pdf` 는 **md5 동일** (`cb5c0f0c…`) — 같은 파일이 두 이름으로 있는 것이지 회의판/저널판이 아니다 |
| 코드 | `github.com/AinurZiga/sionna-RT-reflectivity` (Sionna-RT **v0.19** 기반) |
| 선행판 | Ziganshin et al., *Ray-based simulation of multistatic scattering from target objects in ISAC*, **EuCAP 2025** — **[원문]** (보관함에 있음) |

> ⚠ 메모리의 «Ziganshin 저널판↔회의판 반드시 구별» 규칙을 여기에 적용하면: **이제 저널판이
> 있다**(OJAP, Early Access, DOI 위 참조). 회의판은 여전히 별건(EuCAP 2025)이고 내용이 다르다
> (구 12.8λ, facet 7.5λ/1.0λ 두 종만). 두 판을 섞어 인용하지 않는다.
>
> ⭐**이 변화가 우리 novelty 서술에 미치는 영향** — 이제 «표적을 메쉬로 놓고 산란을 확장한
> 심사 통과 연구는 없다» 고 쓰면 **거짓**이다. 참인 진술은: **심사 통과한 확장은 존재하나
> 표적이 자동차·PEC 단일재질·정지체이고, 회전 로터·부품별 이종재질·마이크로도플러로는
> 확장되지 않았다.** 우리 자리는 «최초의 메쉬 확장» 이 아니라 «그 확장이 안 간 축» 이다.

### 4.2 무엇을 고치나 · 얼마나 좋아지나 · 비용

**고치는 것:** 매끈한 곡면을 평면 facet 으로 자를 때 (a) 기하가 틀어지는 위상오차, (b) 잘게 자를수록
생기는 «전기적으로 짧은 모서리» 에서 UTD 가 깨지는 것.

**지표:** 국소 곡률반경 `R`, 대표 facet 변길이 `E`, 파장 `λ` 로

```
기하 편차   s ~ E²/R            (호와 현의 거리, E ≪ R 가정)
위상 오차   Δφ ~ 2π s/λ
⇒ 실용 지표  E²/(Rλ)
```

**얼마나 좋아지나 (전부 [원문], PEC, 2 GHz, 반경 7λ 구/원기둥, FEKO MLFMM 기준):**

| 케이스 | 구성 | MAE |
|---|---|---|
| 원기둥, 그림자 영역, `E²/(Rλ)=1.39` | Standard RT → **+EE** | 2.3 → **0.8 dB** |
| 구, 그림자 영역, `E²/(Rλ)=1.34` | V+EE → **+EV+VE** | 3.5 → **2.2 dB** |
| 구, 그림자 영역 평균, `E²/(Rλ)>0.6`, **HH** | V → V+EE → V+EE+EV+VE | 7.3 → 4.0 → **3.0 dB** |
| 구, 그림자 영역 평균, `E²/(Rλ)>0.6`, **VV** | V → V+EE → V+EE+EV+VE | 8.3 → 3.2 → **2.7 dB** |
| 차량(i-MiEV 저폴리 220 facet), 그림자, 2 GHz VV | V → V+EE → V+EE+EV+VE | (2.6) → **1.6 dB** |

**비용 (Table II, 초당, AMD EPYC 7343 ×2, 32 코어):**

| 시나리오 | RT | +V | +EE | +EV/VE | 배수 |
|---|---|---|---|---|---|
| 구 156 facet | 0.3 | 1.1 | 1.8 | 4.6 | **15×** |
| 구 346 facet | 0.4 | 1.8 | 3.1 | 6.8 | **17×** |
| 차량 220 facet | 0.4 | 0.9 | 2.4 | 5.0 | **13×** |
| 차량 1496 facet | 0.7 | 3.6 | 10.2 | 19.0 | **27×** |

그리고 복잡도: 단일 모서리 회절 `O(N_e)`, 2차 회절 `O(N_e²)`.

**권고 (축자):**
> "in the backscattering region, accuracy generally improves as the discretization becomes finer.
> However, **the improvement becomes progressively smaller once E²/(Rλ) approaches approximately 0.5**."
> "in the shadow region, **excessively fine discretization may become counterproductive**."
> "the interval **E²/(Rλ) ≈ 0.6−0.9** provides a practical compromise"
> "the facet size should be of several wavelengths in order to satisfy the UTD assumptions,
> **typically E > 1.5λ**"

실측 대조: BIRA 구면 바이스태틱 시스템, i-MiEV, 2–18 GHz 중 3 GHz, 1° 분해능, 거리 3.0 m.
상세 메쉬 1496 facet, `E²/(Rλ) ≈ 0.4–0.6`. 저자들 스스로 *"qualitative validation rather than an
attempt to exactly reproduce the measurements"* 라고 못 박았다.

### 4.3 ⭐ 우리 메쉬에 실제로 계산해 봤다 — 그리고 두 결론이 나온다

메쉬의 **인접면 꺾임각**에서 곡률을 직접 읽었다. 매끈한 테셀레이션에서는 꺾임각 `θ = E/R` 이므로
`E²/(Rλ) = E·θ/λ` 로 **가정 없이** 계산된다. (실제 특징 모서리를 빼려고 `θ < 30°` 인 이음매만 셌다.)

matrice4e, 3.5 GHz (λ = 85.7 mm), 30,662 삼각형. **굽은 그룹만** 실었다 — `accent`·`battery`·`pcb` 는
꺾임각 0° 의 평면 상자라 곡률 기준이 애초에 적용되지 않는다(원장에 `excluded_flat_groups` 로 기록).

| 부품 | facet 변 `E` (중앙, λ) | 꺾임각 (중앙, °) | 곡률반경 `R = E/θ` (중앙, λ) | **`E²/(Rλ)` 중앙** | p90 |
|---|---|---|---|---|---|
| body | 0.098 | 1.03 | 2.31 | **0.0013** | 0.0223 |
| prop | 0.078 | 0.68 | 3.58 | **0.0007** | 0.0042 |
| canopy | 0.084 | 2.27 | 1.48 | **0.0023** | 0.0146 |
| camera | 0.030 | 10.36 | 0.16 | **0.0053** | 0.0062 |
| motor | 0.042 | 1.57 | 2.21 | **0.0007** | 0.0090 |
| gear | 0.018 | 6.85 | 0.30 | **0.0001** | 0.0277 |

**결론 A — 곡면 이산화는 우리 위상 이상의 원인이 아니다.**
`E²/(Rλ)` 최대(p90) 가 **0.028** 이다. Ziganshin 이 «더 곱게 해도 이득이 미미해지는 선» 이라 한
**0.5** 의 **1/18**, 실용 절충대 0.6–0.9 의 **1/25 ~ 1/32** 다. 위상오차로 환산하면
`Δφ ≈ 2π × 0.028 = 0.18 rad ≈ 10°` (중앙값은 약 1°).
⇒ **위상 변동폭 40.6°/166.9°/4217.1° 의 비단조성을 메쉬 조밀도로 설명할 수 없다.**
후보 하나가 지워졌다. (⛔ 단, 이 지표는 **기하 편차**만 잰다 — PO 적분 오차·광선 표본·널 근방의
unwrap 붕괴는 별개의 축이고 이 계산이 무죄를 증명하지 않는다.)

**결론 B — 우리 표적은 Ziganshin 처방의 적용범위 밖이다. (⭐OUR ARITHMETIC)**
그들의 두 조건을 동시에 요구하면

```
E > 1.5λ          (UTD 가정)
E²/(Rλ) < 0.5     (기하 정확도)
⇒ (1.5λ)²/(Rλ) < 0.5  ⇒  R > 4.5λ
```

3.5 GHz 에서 **R > 39 cm** = 4.5λ. 위 표의 `R` 열을 보면 우리 굽은 부품의 곡률반경 중앙값은
prop **3.58λ**, body **2.31λ**, motor **2.21λ**, canopy **1.48λ**, gear **0.30λ**, camera **0.16λ** —
⇒ **여섯 그룹 전부 `R < 4.5λ` 다. 하나도 그들의 두 조건을 동시에 만족시킬 수 없다.**
그리고 우리 facet 은 실제로 **0.018 ~ 0.098 λ** 로 `E > 1.5λ` 를 **15 ~ 85 배 위반**한다.
⇒ **«vertex diffraction 을 넣자» 는 우리 다음 행동이 될 수 없다.** 그 물리는 λ 급 facet 에서
UTD 가 깨지는 것을 메우는 물건인데, 우리는 UTD 를 안 쓰고 facet 이 λ/10 이라 애초에 PO 면적분이
연속이다. **이것이 이 조사에서 가장 값진 «하지 말 것» 이다.**

### 4.4 NURBS 노선 (참고)

Ziganshin 이 정리한 대안: 곡면을 파라메트릭(NURBS)으로 직접 다루는 길.
- Domingo, Rivas, Perez, Torres & Cátedra, *Computation of the RCS of complex bodies modeled using
  NURBS surfaces*, IEEE APM 37(6):36–47, 1995 — **[서지]**
- Della Giovampaola, Carluccio, Puggelli, Toccafondi & Albani, *Efficient algorithm for the evaluation
  of the **physical optics** scattering by NURBS surfaces with relatively general boundary condition*,
  IEEE TAP 61(8):4194–4203, 2013 — **[서지]** ⭐ **PO 를 NURBS 위에서 직접 적분하는 논문**이다.
  우리 노선(PO)의 «곡면 정공법» 에 해당한다.
- Ziganshin 의 기각 사유 (축자): *"these approaches are **computationally demanding and are not
  commonly supported by practical RT frameworks**."*

⇒ 우리 판정: **지금 열지 않는다.** 우리 메쉬가 이미 λ/10 이라 NURBS 가 벌어 줄 기하 정확도는
§4.3 이 보인 대로 이미 0.03 수준이고, 얻을 것이 없다.

---

## 5. ④ 저-kr 한계 — 우리 6.73 dB 를 문헌 어디에 놓을 것인가

### 5.1 두 잣대가 같은 자리에 선을 긋는다

**Sagitta (KTH), arXiv:2604.09243** — **[원문]** — PEC 구를 정확 Mie 와 대조한 주파수 스캔:

> "At **kr = 1**, Mie resonances dominate and **ray tracing methods fail**, as wave effects cannot be
> neglected in this regime. Ray-based approximations become valid as frequency increases, with **good
> agreement typically expected for kr ≳ 30**."
> "Our simulation results demonstrate **excellent agreement with Mie theory beginning at an electrical
> size around kr ≈ 30**." — 그 위 광학영역에서 표준편차 **~2.5 %**, 해석해 대비 **±2 %**.
> 상단은 **kr ≈ 8 × 10³** 에서 광선 표본 부족(aliasing)으로 무너진다.

**우리 `outputs/sbr_kr_sweep.json`** (2026-07-31, 3.5 GHz, kr 1→100, 48 입사방향 평균):

| | div=12 | div=16 |
|---|---|---|
| Mie 대비 최대 \|Δ\| (kr 1–100 전구간) | 6.599 dB | **6.729 dB** |
| Mie 대비 표준편차, **kr ≥ 30** | **1.547 %** | **1.834 %** |
| 해석 PO 대비 최대 \|Δ\| | 0.254 dB | 0.201 dB |

⇒ **정렬된다.** 우리 6.73 dB 는 **전부 kr < 30 에서** 나오고, kr ≥ 30 에서는 1.5~1.8 % 로
Sagitta 의 2.5 % 보다 **좋다**. 그리고 해석 PO 대비 0.2 dB 는 **우리 수치구현이 PO 를 제대로 푼다**는
뜻이다 — 남은 6.5 dB 는 «PO 라는 근사를 쓴 대가» 이지 «우리 코드의 버그» 가 아니다.
(이 두 잣대 분리는 원장 `meta.reference_note` 가 이미 명시하고 있다.)

⚠ **완전한 사과-대-사과는 아니다** — 메쉬(우리 `uv_sphere`)와 구현이 다르다. 원장 `axis_note` 에
기록된 그대로다.

### 5.2 그런데 «kr ≥ 30» 은 우리 드론의 어디에 해당하나

3.5 GHz, λ = 85.7 mm 에서 `kr = 2πr/λ = 30` ⇒ **r = 41 cm**.
matrice4e 전장이 ~0.6 m 급이므로 **기체 전체는 겨우 그 언저리**이고, **부품은 전부 그 아래**다
(로터 반경 ~0.15 m ⇒ kr ≈ 11, 모터 ~0.02 m ⇒ kr ≈ 1.5).
⇒ ⭐ **이것이 우리 σ 축의 가장 정직한 한계 문장**이다: *"우리 커널의 광학영역 판정은 표적 전체
스케일에서만 성립하고, 부품 스케일에서는 문헌이 선언한 유효범위 밖이다."*

### 5.3 문헌은 저-kr 을 어떻게 다루나

**Gorji, Zakeri & Janalizadeh, *Physical Optics Analysis for RCS Computation of a Relatively Small
Complex Structure*, ACES Journal (River Publishers)** — **[원문]** (웹에서 PDF 확보·추출)
- 축소 선박 모델 58.75 × 8.25 × 6.27 cm 를 **100 MHz – 10 GHz** 에서 CST **IE 솔버(MoM)** vs
  **asymptotic 솔버(PO)** 로 대조 + 8.5 GHz 실측 검증.
- **기준: 최소 치수 기준 `D/λ ≥ 1`.** (그들 인용) 렌즈 안테나 PO 는 *"typically larger than **5λ**"*,
  표면임피던스 `Z_s = Z_0(0.2 + j0.02)` 를 준 경우는 *"dimensions **less than 8λ and more than
  1.5λ** has been precisely computed"*.
- ⭐ **PO 가 무엇을 놓치는지 명시**: 파장보다 작은 **부착 산란체**.
  > "While MoM accounts for the effect of the scatterers set on the infrastructure of the vessel, **PO
  > requirements are not met because these scatterers are generally small compared to the wavelength**;
  > … which results in **higher RCS values [for MoM] compared to PO backscattering**."
- 오차 성격: 평균은 작지만 **표준편차가 크다** — *"while RCS error is high for specific observations,
  it is **negligible in other view angles** in each single frequency."*

⇒ **우리에게 옮길 것 두 가지.** (a) `D/λ ≥ 1` 은 **가장 관대한** 기준이고 Sagitta 의 `kr ≥ 30`
(= `D/λ ≈ 9.5`)은 **가장 엄격한** 기준이다 — 문헌 안에서도 한 자릿수 배가 벌어진다.
(b) **PO 는 파장 이하 부착물에서 σ 를 낮게 낸다.** 드론의 안테나·다리·센서 돌기가 정확히 그것이다.

**Chalmers/DiVA 석사논문 1595877, *Evaluation of CST Studio for RCS simulation*** — **[원문]**
- 상용 두 도구 대조: **OPTISCAT** (PO + 모서리 회절 보정) vs **CST A-solver** (SBR).
- 결과 축자 요지: 두 도구의 σ 비(dB) 산포가 *"somewhere around [15 −15] dB which corresponds to the
  CST data being **32 times bigger/smaller** than the OPTISCAT data"* 인 구간이 있고,
  전기적으로 작은 구조에서 A-solver 가 *"took so [long]"* + 부정확.
⇒ **상용 asymptotic 솔버끼리도 ±15 dB 로 벌어진다.** 우리 6.73 dB(그것도 유효범위 밖에서)는
이 판에서 이상치가 아니다. ⚠ 이것은 «우리가 옳다» 가 아니라 «**이 계열 전체의 산포가 이만큼**» 이라는
문맥이다.

**MoM/MLFMM 혼성** — 검색으로 존재는 확인했으나 **서지를 특정하지 못했다** ⇒ §9.

---

## 6. ⑤ 재질·편파 — 편파를 넣으면 무엇이 달라지나

### 6.1 우리 상태를 정확히 적는다

우리 PO 면적분은 **스칼라**다. 이건 **PO 의 한계가 아니라 우리가 PO 위에 얹은 추가 근사**다 —
진짜 PO 는 `J_PO = 2 n̂ × H^i` 로 벡터이고 편파에 종속된다. `ptd_edges.APPROXIMATIONS` 축자:

> "polarization: **PO surface term stays SCALAR** (|Gamma| weighted, no pol); only the fringe term
> carries polarization. **The same scalar PO field is added to BOTH V and H.**"
> "receive polarization = transmit polarization in a fixed GLOBAL (h,v) basis (co-pol). … **cross-pol
> is not computed.**"

### 6.2 문헌이 말하는 편파의 값어치

**(a) 정반사 지배 구간에서는 작다.**
Öztürk 2002 — **[원문]** (우리 doc 에도 인용된 문장):
> "**Although PO is polarization independent, PTDEEC is not**, therefore, results for the fuel tank for
> horizontal and vertical polarizations differ."

Ziganshin — **[원문]**: 원기둥 후방산란은 *"HH polarization (**VV polarization behaves similarly**)"*.

**(b) 약한 산란·그림자 구간에서는 dB 단위로 갈린다.**
Ziganshin Table I (구 그림자, `E²/(Rλ)>0.6` 평균 MAE):

| 구성 | HH | VV |
|---|---|---|
| V | 7.3 dB | 8.3 dB |
| V+EE | 4.0 dB | 3.2 dB |
| V+EE+EV+VE | 3.0 dB | 2.7 dB |

⇒ 같은 기하·같은 방법인데 편파에 따라 **1.0 dB(V), 0.8 dB(V+EE), 0.3 dB(전부)** 씩 다르다.

**(c) ⭐ 편파는 «정확도» 가 아니라 «새 관측량» 을 준다 — 이게 우리에게 진짜 값어치다.**
**Lee, Yoo, Park, Kim et al., *Dynamic RCS Estimation according to Drone Movement Using the MoM and
Far-Field Approximation*, JEES (J. Electromagn. Eng. Sci.) 21(4):321–327, Sep. 2021** — **[원문]**

- DJI Mavic 2 프로펠러(20.32 cm = 9.65 GHz 에서 **6.5λ**), 탄소섬유 ≈ PEC 가정. FEKO MoM 대조.
- ⭐ **CW/CCW 프로펠러의 편파 관계** (축자 요지 + 식 (3)):
  > "Because of their mirror-image symmetric characteristics, **the co-polarized components of the
  > electric fields scattered from CW and CCW propellers are the same, and the cross-polarized
  > components have a phase difference of 180°.**"

  ```
  [S_θθ, S_θφ; S_φθ, S_φφ]_CW = [S_θθ, −S_θφ; −S_φθ, S_φφ]_CCW
  ```
- ⇒ **co-pol 만 보면 CW 와 CCW 가 구별되지 않는다. cross-pol 이 그 둘을 가른다.**
  우리는 cross-pol 을 계산하지 않으므로 **이 판별 정보를 통째로 버리고 있다.**
  우리 메인 태스크가 «탐지·분류» 인 것을 감안하면 이건 정확도 이야기가 아니라 **feature 이야기**다.

**(d) 편파 RCS 문헌 (참고, PO 정밀화 자체는 아님)**: `1910.13706` (자동차용 보행자 polarimetric RCS,
딥러닝), `2605.31267` (polarimetric effective roughness diffuse scattering) — 둘 다 보관함에 있고
**[원문 추출만 함, 정독 안 함]**.

---

## 7. ⑥ 마이크로도플러 특화 — 회전 표적에 PO 를 쓸 때의 알려진 함정

### 7.1 «자세를 얼려 스냅샷마다 PO» 에는 이름이 있다

**Pouliguen, Lucas, Muller, Quete & Terret, *Calculation and analysis of electromagnetic scattering
by helicopter rotating blades*, IEEE TAP 50(10):1396–1408, Oct. 2002** — **[서지]**
(서지는 Costa 2025 참고문헌 [12] 와 출판사 메타데이터로 확인. **본문 미확보.**)
- **PO + MEC(Method of Equivalent Currents)** 로 헬기 로터의 시변 RCS 를 계산.
- 2차 자료가 일관되게 전하는 핵심어: **quasi-stationary approach**, I-DEAS 삼각 메쉬.
⇒ **우리가 하는 것에 2002 년에 붙은 이름이 있고, 24 년 된 표준 관행이다.**
그리고 그들은 PO 에 **MEC(=모서리 등가전류)를 같이 썼다** — 회전 블레이드에 PO 를 쓴 원조가
모서리항을 함께 넣었다는 사실은 우리 §2 의 우선순위를 지지한다.

### 7.2 자세를 몇 개나 표본해야 하나 — 문헌 관행은 512, 우리는 4096

Costa et al. (아래) 의 관련연구 정리에서, 전부 **[서지]**:

| 논문 | 방법 | 자세 표본 |
|---|---|---|
| Schröder, Aulenbacher, Renker, Böniger, Oechslin, Murk & Wellig, *Numerical RCS and micro-Doppler investigations of a consumer UAV*, SPIE **9997**, 2016 | MoM + **PO** | **512 이산 프로펠러 자세** |
| Speirs, Schröder, Renker, Wellig & Murk, *Comparisons Between Simulated and Measured X-band Signatures of Quad-, Hexa- and Octocopters*, **EuRAD 2018** | FEM + MoM | **512 자세 균등 360°** |
| Petrovic, Savic & Ilic, *Electromagnetic Modelling of Micro-Doppler Signatures of Commercial Airborne Drones*, **TELFOR 2021** | 풀웨이브 다회 | 반 회전분 |

512 자세 = **0.703°/스텝**. 우리 앙각 스윕은 **4096 자세** = 0.088°/스텝 ⇒ **8 배 조밀**.
⇒ ⭐ **자세 표본은 우리 문제가 아니다.** (그리고 이건 사용자의 «위상 변동폭이 왜 커지나» 에 대한
또 하나의 후보 제거다 — 4217° 는 4096 표본에서 나온 것이므로 스텝당 평균 1.03° 이고, unwrap 이
π 를 넘기려면 스텝당 180° 가 필요하다. 다만 **국소적으로** 널을 지날 때는 그 평균이 무의미하다.)

### 7.3 ⭐ 비용을 157 배 줄이는 이식 가능한 트릭 — 그리고 그 대가

**Lee et al., JEES 21(4), 2021** — **[원문]** — MoM 기반이지만 **구조는 PO 에도 그대로 성립한다**:

1. **메쉬를 고정하고 입사각을 반대로 돌린다.** 임피던스 행렬(우리 경우 씬/BVH)을 한 번만 만든다.
2. **CW 하나만 계산하고 CCW 는 거울대칭으로 얻는다** (식 (3), §6.2c).
3. **로터 4 개 = 로터 1 개의 장 × 병진 위상**:
   `E^s_P(t) ≅ Σ_n E^s_{T_n}(t; θ,φ) · exp(−j2k⃗·r⃗_n)` (원거리 근사)
4. 방위각이 바뀌면 재계산 없이 **회전 시작각만 바꾼다** (CW 는 `+φ_obs`, CCW 는 `−φ_obs`).

**측정된 비용 (Table 1):** 기존 방식 **20:01:12** → 제안 방식 **00:07:40** ⇒ **약 157 배**.
검증: 1차 피크 313.2 Hz = 회전주파수 156.6 Hz × 2 (블레이드 양 끝 2 산란점).

⚠ **대가가 명확하다.** 이 트릭은 **로터끼리의 상호 그림자와 동체 가림을 통째로 버린다**
(각 로터를 독립 산란체로 보고 병진 위상만 더한다). 우리는 이미 가림을 넣고 있으므로 채택하면
**후퇴**다. ⇒ **채택 안 함. 대신 «대조군» 으로 쓴다** — 가림을 켠 우리 결과와 이 근사의 차이가
곧 **«상호 가림의 값»** 이고, 그건 아직 아무도(우리도) 안 잰 숫자다.

### 7.4 함정 목록 — 문헌이 명시한 것

| 함정 | 출처 | 내용 |
|---|---|---|
| **협대역 가정이 광대역에서 깨진다** | Costa et al., IEEE **JSTEAP** 2025 (arXiv:2504.05168) — **[원문]** | 광대역에서는 *"the same target point scatterer can produce **different Doppler**"* — 부반송파마다 도플러가 달라져 단일 `f_d` 가정이 무너진다. 우리 OFDM 패시브에 직결 |
| **풀웨이브 계열은 ML 데이터 생성에 불가능** | 같은 논문 — **[원문]** | *"extremely time-consuming and hard to implement. As a consequence, using these methods to generate a large amount of data to train machine learning algorithms becomes **unfeasible**."* |
| **RT 진영도 시변 부구조는 미해결** | Ziganshin 2026 «Open research challenges» 4번 — **[원문]** | *"**Modeling of time-varying substructures (micro-Doppler)**"* 를 열린 과제로 남기고 Costa 를 인용 |
| **Sionna RT 스톡은 회전 로터를 못 한다** | Li, Mu, Jiang, Feng, Gao & Xu, *Micro-Doppler Signature Simulation of Multirotor UAVs Using Ray Tracing* — **[원문]** | 시간 스텝마다 기하를 옮겨 **재시뮬**하고, 경로 밀도를 올리려 구면 샘플링을 **원뿔 샘플링**으로 교체. ⚠ **PO 를 안 쓴다** — 산란점/CSI 수준. 우리 메모리의 «md-rt 헤드라인 반증» 항목이 이 논문이다 |
| **가림 판정의 시간 일관성** | — | ⛔ **명시적으로 다룬 문헌을 못 찾았다.** §9 |

---

## 8. ⭐ 비용 대비 이득 순서 — 다음에 할 것

> 정렬 기준: (기대 이득) ÷ (구현 + 재계산 비용), 그리고 **상류부터**(뒤에 영향 주는 것 먼저).

### 1등 — PO 면적분을 벡터(편파)로 올린다  · 비용 **낮음** · 이득 **높고 확실**

**무엇을 고치나.** `J = 2 n̂ × H^i` 를 실제로 써서 스칼라 `|Γ|` 를 벗는다. 지금은 입사각 의존이
`|Γ|` 하나로 뭉개져 있어 **grazing 근방의 각도 의존이 구조적으로 틀린다** — 그리고 사용자가 물은
것이 바로 **앙각 의존**이다. el = −90°(직하방)에서는 도플러가 물리적으로 0 이라 **남는 변동이
진폭뿐인데, 그 진폭의 앙각 의존을 스칼라가 못 낸다.**

**얼마나 좋아지나.** 정반사 지배 구간에서는 작다(Öztürk: PO 는 편파 무감 / Ziganshin: VV≈HH).
**약한 산란 구간에서 0.3–1.0 dB** (Ziganshin Table I). 그리고 **cross-pol 이라는 새 채널**이 열려
CW/CCW 판별이 가능해진다(Lee 2021 식 (3)).

**비용.** 면적분 루프에 벡터 한 줄 + `Γ_∥/Γ_⊥` 분리. 재계산은 스윕 1 회.
**게이트.** 정반사 로브 안에서 `|σ_vec − σ_scalar| < 0.5 dB` 일 것(아니면 배선 오류).

### 2등 — «kr < 30 은 유효범위 밖» 을 원장·리포트에 못 박고 부품별 kr 표를 만든다 · 비용 **거의 0**

**무엇을 고치나.** 서술의 정직성. 지금 우리는 6.73 dB 를 «우리 커널의 오차» 로 들고 있는데,
Sagitta 가 독립적으로 kr ≳ 30 을 선언했고 우리 원장이 그 선 위에서 1.5–1.8 % 라는 것을 이미
증명한다. **결함이 아니라 선언된 경계**로 재분류해야 한다.

**얼마나.** 숫자는 안 바뀌고 **주장의 범위**가 바뀐다 — 그게 이 프로젝트의 통화다.
**추가 산출.** 부품별 `kr = 2πr/λ` 표(로터 반경 ≈ 11, 모터 ≈ 1.5, 기체 전체 ≈ 22…)를 만들어
**어느 부품이 선 아래인지** 밝힌다. §5.2 에 초안이 있다.

**비용.** 계산은 이미 `outputs/sbr_kr_sweep.json` 에 있다. 문서 작업뿐.

### 3등 — 1 bounce vs 2 bounce 를 자세 몇 개에서만 잰다 (채택 여부는 그 다음) · 비용 **중간**

**무엇을 고치나.** 우리는 **1 bounce** 다. Gao 축자로 «큰 σ 구간은 다중반사가 지배» 하고,
드론은 로터가 동체 **위**라 «로터 → 동체 상면 → 레이더» 가 기하학적으로 실재한다.
문헌 기준선은 PEC **3 bounce**(Monte Carlo SBR).

**얼마나.** **모른다 — 그게 이 실험의 목적이다.** Monte Carlo SBR 은 «충분한 바운스 뒤 두 알고리즘이
0.01 dBsm² 안» 이라고만 하지 1→2 의 값을 안 준다.

**비용.** `rcs_sbr(max_bounce≥2)` 는 이미 있으나 **배치가 안 된다**. 그래서 **전 스윕이 아니라
앙각 7 개 × 자세 8 개 = 56 회**만 돌린다. 차이가 < 0.5 dB 면 4등 이하로 강등하고 닫는다.
**GPU 방침 준수**: 카드 2 는 광선 사다리 중 ⇒ 3 → 0,1 순, 각 95 % (23,335 MiB) 상한.

### 4등 — 1차 PTD 를 **약한 산란 구간에서만** 켜 본다 · 비용 **중간~높음** · 이득 **불확실하지만 문헌 지지 강함**

**무엇을 고치나.** Gao·Kırık 두 원문이 «회절만 남는 −45 dB 구간» 에서 PTD 의 값어치를 못 박았고,
사용자가 물은 −60°(변조깊이 0.390 의 깊은 널)·−90° 가 **정확히 그 성격의 자리**다.
문헌대로면 **PTD 없는 우리는 그 구간에서 σ 를 낮게 내고 있다**.

**얼마나.** Kırık cone-sphere: PO+PTD 가 −35~−45 dBsm 로 실측·FEKO 와 정렬, PTD 없는 도구는 더 낮음.
⚠ Öztürk 의 상한: **few-λ 에서는 1차만으로 부족**하다(2차 회절이 작은 표적일수록 크다).

**비용 (실측된 것).**
- `ptd_edges` 는 `ptd=True` 일 때 PO 점구름 간격 **λ/20** 을 강제한다. 우리는 지금 **λ/12** ⇒
  면적분 표본이 `(20/12)² ≈ 2.8 배`.
- SBR 부착 경로가 **end-to-end 미검증**(`NOT_IMPLEMENTED` 마지막 항: *"the path is still NOT
  exercised end to end"*). 즉 **먼저 배선 검증부터**다.
- 우리 자체 기록의 경고: 재진입(오목) 모서리를 열면 **6.5 % 길이가 99.99 % 의 에지장**을 만들어
  `+13.9 dB` 짜리 거짓 «효과» 를 냈다.

**게이트 (문헌 R2 기준, 우리 doc §8).** 정반사 로브 ±(첫 널) 안에서 PO 단독과 PO+PTD 가
**0.5 dB 이내**로 같을 것. 이걸 통과 못 하면 물리가 아니라 우리 메싱이다.

### 5등 — «로터 독립 + 병진위상» 근사를 **대조군으로** 구현해 상호 가림의 값을 잰다 · 비용 **낮음**

**무엇을 고치나.** 아무것도 안 고친다. **모르는 것 하나를 숫자로 만든다** —
«로터끼리·로터와 동체의 상호 가림이 마이크로도플러에 얼마짜리인가».

**어떻게.** Lee 2021 식 (4) 를 우리 커널로: 로터 하나만 PO 로 돌리고 나머지 3 개는
`exp(−j2k⃗·r⃗_n)` 병진 위상으로 합성 + CW/CCW 거울대칭. **가림 없는 판**이 나온다.
현재의 가림 있는 판과 스펙트로그램·f_tip·변조깊이에서 차이를 잰다.

**왜 값어치가 있나.** (a) 상호 가림은 우리가 «넣었다» 고 주장하는 것 중 값이 안 매겨진 항목이다.
(b) 문헌 다수(Lee, Costa 계열 thin-wire)가 이 근사 위에 서 있으므로, 차이가 크면 **우리 결과가
그 문헌과 왜 다른지**를 설명하는 근거가 되고, 작으면 **157 배 가속을 정당하게 쓸 수 있다**.

---

### ⛔ 하지 말 것 (이 조사가 세운 «안 함» 목록)

1. **vertex diffraction 이식** — Ziganshin 의 처방은 `E > 1.5λ` facet 을 전제한다. 우리는 `0.018–0.098λ`
   로 15–80 배 위반이고, 애초에 UTD 를 안 쓴다(PO 면적분은 연속이라 그 불연속 병이 없다). §4.3.
2. **메쉬를 더 곱게 하기** — `E²/(Rλ)` 가 이미 그들 기준의 1/18–1/32 다. 얻을 게 없다. §4.3.
3. **NURBS 곡면 PO** — 위와 같은 이유. §4.4.
4. **Notaros 의 ray-cone / 이중계수 제거 이식** — 수신구 기반 전파 예측용 기계이고, 개구면 적분 방식의
   RCS SBR 과는 문제가 다르다. §3.3.
5. **광선 밀도 올리기** — 두 문헌 기준(≥10/λ, ≤λ/5) 을 이미 만족한다. §3.3.

---

## 9. 못 찾은 것 · 원문 미확보 (정직하게)

**본문을 못 읽었고 2차 인용으로만 아는 것 (서지는 확인):**
- Pouliguen et al., TAP 50(10):1396–1408, 2002 — PO+MEC 회전 블레이드. ⭐**⑥ 의 원전인데 못 읽었다.**
  quasi-stationary 라는 핵심어와 «시간 표본을 어떻게 정했나» 를 2차로만 안다. **다음 라운드 1순위 확보 대상.**
- Weinmann, TAP 54(6):1797–1806, 2006 — PO/PTD + **RDN**. ② 의 핵심 기법인데 본문 미확보.
- Ling, Chou & Lee, TAP 37(2):194–205, 1989 — SBR 원전.
- Albani, Capolino, Carluccio & Maci, TAP 57(12):3911–3925, 2009 — vertex diffraction 계수.
- Albani, TAP 53(2):702–710, 2005 — 2중 회절 균일 계수. Carluccio et al., TAP 60(12):5809–5817, 2012 — 3중.
- Della Giovampaola et al., TAP 61(8):4194–4203, 2013 — **NURBS 위의 PO**.
- Schröder(SPIE 9997, 2016) · Speirs(EuRAD 2018) · Petrovic(TELFOR 2021) — «512 자세» 의 원전 3편.
  ⚠ **512 라는 숫자를 Costa 의 요약으로만 안다.** 그들이 512 를 어떻게 정당화했는지는 모른다.
- Michaeli TAP 1984/1986, Mitzner AFAL-TR-73-296 (1974), Knott TAP 33(1):112–114 (1985) —
  우리 doc §10 이 이미 미확보로 기록한 것들. 상태 변동 없음.

**존재는 아는데 서지를 특정 못 한 것:**
- **저-kr 용 MoM–PO 혼성 / 임피던스 경계 보정.** 웹 검색으로 «hybrid MoM-PO 가 공진영역으로
  유효범위를 넓힌다» 는 취지의 2차 서술은 봤으나, **인용 가능한 1차 서지를 확정하지 못했다.**
  ⛔ 따라서 이 문서는 «④ 의 표준 해법» 을 제시하지 못한다. 이것이 이 조사의 가장 큰 구멍이다.
- **PO 의 저-kr 오차를 «보정계수» 로 다루는 문헌.** 못 찾았다. 찾은 것은 전부 «유효범위를 선언하고
  그 밖에서는 다른 솔버를 쓴다» 는 처방이다(Sagitta, Gorji, DiVA).

**아무도 안 다룬 것으로 보이는 것 (⚠ «없다» 가 아니라 «내가 못 찾았다»):**
- **가림 판정의 시간 일관성.** 회전하는 블레이드가 프레임마다 가림 판정을 뒤집을 때 생기는
  **위상·진폭 점프**를 명시적으로 다룬 문헌을 못 찾았다. 우리 −60° 의 «위상 변동폭 4217°» 가
  이 계열의 인공물일 가능성이 남아 있고, **커널 판정 라운드가 봐야 할 후보**다.
- **자세 보간.** 512 든 4096 이든 «표본 사이를 어떻게 잇는가» 를 논한 문헌을 못 찾았다.

**보관함에서 추출만 하고 정독하지 않은 것** (관련은 있으나 이 여섯 질문의 중심이 아님):
`2607.13417`(parametric diffraction sensing), `pier2008`(GPU EM), `plosone2021`(OptiX SBR),
`schuler2008`(virtual scattering centers), `gbppr`(PO 코드 노트), `1910.13706`, `2605.31267`,
`kit_vru_rcs_TMTT2022`, `2507.12235`, `Multiband…AAVs`, `iet-rsn-2019-0471`, `2505.20673`(M350),
`Modeling_Micro-Doppler…Distributed ISAC`, `white2023`.

---

## 10. 이 조사가 세우지 못하는 것

1. **우리 커널이 맞다는 것을 세우지 않는다.** 이 문서는 «남들이 PO 를 어떻게 다듬나» 만 모았다.
   커널 판정은 `outputs/verify_po_elev_*.json` 라운드가 한다.
2. **사용자의 비단조 위상 변동폭을 설명하지 않는다.** 후보 **두 개를 제거**했을 뿐이다 —
   곡면 이산화(§4.3, `E²/(Rλ)` ≤ 0.028)와 자세 표본 부족(§7.2, 4096 vs 문헌 512).
   남은 후보는 (a) 잣대 자체(널 근방 `np.unwrap` 붕괴), (b) 가림 판정의 시간 불연속, (c) 1 bounce,
   (d) 스칼라 편파, (e) 모서리항 부재다. **(a) 는 잣대 문제라 커널 판정 라운드가 먼저 봐야 한다.**
3. **④ 의 해법을 제시하지 못한다.** §9 참조 — 저-kr 보정의 1차 서지를 확보하지 못했다.
4. **비용 수치는 전부 남의 하드웨어다.** Ziganshin 은 CPU 32 코어, Gao 는 GTX 470, Sagitta 는
   LUMI 8 노드다. **우리 4×4090 에 그대로 옮기면 안 된다.** 우리 것은 우리가 재야 한다.
