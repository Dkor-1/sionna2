# PTD 모서리항 정식화 — 채택: **untruncated Michaeli PTD-EEC (first order)**

> ## ⚠⚠ 정정 (2026-08-03) — 파일명과 §2 의 "ILDC" 는 **문헌 개관**이지 우리 이름이 아니다
>
> 파일명 `PTD_ILDC_FORMULATION.md` 는 이력 때문에 그대로 두지만, **우리가 구현한 것의 이름은**
>
> ### `untruncated Michaeli PTD-EEC (first order)`
> 1차 PTD 프린지파 보정 — Michaeli 1986 의 **비절단(untruncated)** 등가모서리전류(PTD-EEC)를
> 직선 모서리 조각을 따라 해석 적분한 것.
>
> ⛔ **NOT "TW-ILDC" · NOT "ILDC" · NOT "Gao's method".**
> Gao 2012 의 TW(truncated wedge) = Johansen 1996 의 절단 보정 EEC (3)(9)(10)(11)(21)(22) 이고
> 우리는 그것을 **하나도** 구현하지 않았다. 우리 것은 Johansen (4)(5) = Michaeli 1986 (4)–(7),
> 즉 **비절단 절반**이다. 이 문서에서 ILDC·TW-ILDC·Gao 가 나오는 자리는 전부 (i) 문헌이 무엇을
> 말하는지 설명하거나 (ii) **우리가 안 넣은 것**을 밝히는 부정 문맥이다. 근거·판정은
> `outputs/ptd_attack_lit.json` q3, 철회 기록은 `docs/RETRACTION_LOG.md` R13.
>
> **정규화 상수도 정정됐다(2026-08-03, 결함 D-1).** §9.1 의 `½` 는 **크기만** 맞고 부호가 틀렸다.
> 옳은 값은 **−½** 이며 유도는 §9.1 에 새로 적었다. 부호가 뒤집힌 커널로 만든
> `outputs/ptd_regression.json` · `ptd_drone_effect.json` · `ptd_plate_validation.json` 은
> **SUPERSEDED** 로 표시돼 있다 — 재생성 전에는 인용하지 마라.

**목적** — 우리 RCS 커널(`src/rcs_po.py` + `src/rcs_sbr.py`)에 더할 모서리 프린지 항을 **수식 수준으로 못박는다**. 어떤 정식화를 쓰는지, 그 닫힌형이 무엇인지, 모노스태틱에서 어느 모서리가 기여하는지, 적분을 해석적으로 할 수 있는지, 그리고 구현이 맞는지 무엇으로 확인하는지를 확정한다.

**현재 상태** — 우리 커널은 PO 면적분만 한다. Ufimtsev 의 비균일(프린지) 전류 기여가 통째로 빠져 있다.

본문은 한국어, 수식·그림 문구는 영어. 축자 인용은 `>` 인용블록에 원문 그대로 두고 출처를 붙였다. **확정 못 한 것은 §10 에 따로 모았다.**

작성 2026-08-03.

---

## 0. TL;DR — 확정 사항

| 질문 | 확정 |
|---|---|
| 프린지 전류 정의 | `J^(1) = J − J^(0)` (정확전류 − PO전류). Ufimtsev 는 이것을 "nonuniform part of the current" 라 부른다 |
| ILDC 가 주는 것 | 모서리 **단위길이당 원거리 산란장 증분** `dE^(s,NU)/dl`. 등가 선전류 `(I^f, M^f)` 한 쌍으로 표현된다 |
| Michaeli EEC ↔ Mitzner ILDC | **같은 물리**. Knott 1985 가 둘의 관계를 확정했다. Michaeli 1986 의 fringe 성분이 Mitzner ILDC 에 대응한다 |
| 무한 쐐기 닫힌형 | Ufimtsev (4.07)(4.08) + (3.33)(3.34) → `f^(1)=f−f^(0)`, `g^(1)=g−g^(0)`. 소프트=`f`(E편파), 하드=`g`(H편파) |
| Gao 의 TW 변형 | 무한 스트립을 **실제 면 경계에서 절단**. `EEC_T = EEC_UT − EEC_cor` (Johansen 1996). 복소 Fresnel 적분 필요 |
| ⭐ 채택 (이름) | **untruncated Michaeli PTD-EEC (first order)** — Michaeli 1986 프린지 EEC 를 Öztürk 2002 표기로. 열린 모서리는 반평면 (3.33)(3.34). **TW 는 미구현이므로 "TW-ILDC"·"ILDC"·"Gao's method" 라 부르지 않는다** |
| Keller 원뿔 · 모노스태틱 | 후방산란이 원뿔 위에 오는 것은 **모서리가 시선에 수직일 때뿐** (`t̂·û = 0`). 그 모서리가 코히어런트하게 지배한다 |
| 모서리 적분 | **해석적**. 직선 조각 + 상수 EEC → `L·sinc(k L t̂·û)`. 수치 적분 불필요 |
| 검증 표준 케이스 | 사각 평판 모노스태틱 σ(θ) — PO 는 편파 무감이라 비정반사에서 틀리고 PO+PTD 가 편파를 가른다 |

**⚠ 전제 정정 하나.** "Gao 가 비용 +4.6~17.2% 로 정확도를 얻었다" 는 **월클럭 수치이지 연산량 수치가 아니다**. Gao Table 1 을 보면 TW-ILDC 자체 연산은 항공기 A 에서 913.9 s, SBR 단독 전체가 1311 s 다 — **모서리항이 PO/SBR 전체와 맞먹는 양의 산술을 요구한다**. 4.6% 는 그 연산을 놀고 있던 CPU 로 밀어 GPU SBR 과 겹쳐 숨겼기 때문에 나온 값이다. 항공기 B 는 TW-ILDC 2428.2 s > SBR 단독 2302.7 s 로 아예 CPU 가 지배하고, 그래서 17.2% 로 커졌다. 우리 계획에 이 숫자를 그대로 옮기면 안 된다.

---

## 1. Ufimtsev 프린지(비균일) 전류 — 수식 정의

### 1.1 정의

물체 표면의 전류를 두 조각으로 나눈다.

```
J_total(r)  =  J^(0)(r)  +  J^(1)(r)
              └ uniform  └ nonuniform (= fringe)
```

`J^(0)` 는 기하광학/물리광학이 주는 균일 부분이다. PEC 조명면에서

```
J^(0) = 2 n̂ × H^inc      (lit face)
J^(0) = 0                 (shadowed face)
```

`J^(1)` 는 정확전류에서 그것을 뺀 나머지, 즉 **모서리 근방에서만 살아 있고 모서리에서 멀어지면 급격히 감쇠하는 여분 전류**다.

```
J^(1)  :=  J_total − J^(0)
```

Ufimtsev 원전(1962, 미공군 FTD 영역본)의 서술:

> "P. Ya. Ufimtsev studied the scattering characteristics by such bodies by taking into account, besides the currents being excited on the surface of the body according to the laws of geometric optics (the *"uniform part of the current"* according to his terminology), the additional currents arising in the vicinity of the edges or borders which have the character of edge waves and rapidly attenuate with increasing distance from the edge or border (the *"nonuniform part of the current"*)."
> — Ufimtsev, *Method of Edge Waves in the Physical Theory of Diffraction*, FTD-HC-23-259-71, Foreword, p. v

장(field) 차원에서의 정의는 §4 첫 문장이 그대로 준다.

> "In § 1 and 3 we represented the rigorous and approximate expressions for the diffraction field by integrals along the same contour in the complex variable plane. **By subtracting the approximate expression from the rigorous expression, we find the field created by the nonuniform part of the current.**"
> — 같은 문헌, p. 26 (§4 도입부)

즉 **PTD 의 프린지 항은 "정확해 − PO해" 로 *정의*된 것**이지 따로 유도된 물리가 아니다. 그래서 PO 적분 옆에 **더하는** 구조가 된다.

### 1.2 현대 표기 (교차 확인)

```
J_PTD(r) = J_PO(r) + J_NU(r)                            ... (Wu & Chew 2016, eq. 29)
E^(s)(r) ≈ (i k e^{ikr} / 4πr) √(μ/ε) (I − r̂r̂) · ∫_∂Ω dr' e^{-ik r̂·r'} J_PTD(r')   ... (eq. 30)
```
— B. B. Wu, W. C. Chew, "The Modern High Frequency Methods for Solving Electromagnetic Scattering Problems," *PIER* **156**, 63–82, 2016 (open access).

Johansen 의 표현도 같다.

> "The EEC's are determined from an analytical integration of the FW current (**the exact current minus the PO current**) along incremental strips on the canonical wedge or half-plane."
> — P. M. Johansen, IEEE TAP **44**(7):989–995, 1996, §I

### 1.3 우리에게 중요한 귀결

- PO 적분을 고쳐 쓰는 게 아니라 **항을 하나 더한다**: `E_tot = E_PO + E_PTDEEC` (Öztürk 2002, eq. 3.42).
- 프린지 항은 **부호가 있는 복소장**이다. 전력 가산이 아니라 **장에서 코히어런트 합**이다. `docs/HOW_OTHERS_SOLVED_IT.md` 의 전력가산 산술은 자릿수 점검이지 예측이 아니다.
- 프린지 계수는 **PEC 유도**다. 우리 `|Γ|` 가중 PO 와 섞이는 문제는 §9.3 에서 다룬다.

---

## 2. ILDC — 단위길이당 무엇을 주는가, Michaeli EEC 와의 관계

### 2.1 ILDC 가 주는 양

Mitzner 의 ILDC(1974)는 **모서리 미소길이 `dl` 하나가 원거리에 만드는 산란장의 증분**이다. 균일전류(PO) 성분을 빼고 남긴 비균일 성분만 취한다.

```
δE^(s,NU)(r) ≈ dl · (i k e^{ikr} / 4πr) √(μ/ε) (θ̂θ̂ + φ̂φ̂) · ∫_C(s) dr' e^{-ik r̂·r'} K^(NU)(r̂_i, r')

K = K^(PO) + K^(NU)                                       ... (Wu & Chew 2016, eqs. 34, 37, 38)
```

여기서 `C(s)` 는 모서리에서 면 안쪽으로 뻗는 **증분 스트립(incremental strip)** 이고, `K^(NU)` 는 그 스트립 위의 프린지 전류다. 스트립 방향은 **Keller 원뿔과 면의 교선**이다 (§2.2·§4).

즉 ILDC 는 "이 모서리 조각 1 m 가 그 방향으로 얼마를 산란시키는가" 를 주는 계수다. 이것을 모서리 전 길이에 대해 선적분하면 프린지 장이 나온다.

### 2.2 EEC 로 재포장하기 (구현에 쓰는 형태)

같은 증분을 **가상의 등가 선전류 한 쌍** `(I^f, M^f)` 으로 표현하면 코드에 넣기 쉽다. 이것이 EEC(equivalent edge currents)다.

```
E^FW = j k ∫_C  (e^{-jks} / 4πs) [ ζ ŝ×(ŝ×t̂) I^f  +  ŝ×t̂ M^f ] dl        ... (Öztürk 2002, eq. 3.7)
```

Gao 도 같은 식을 쓴다(부호 규약만 다름).

> "The truncated equivalent edge currents (EECs) are expressed by the magnetic current M_T and the electric current I_T, and the formula of the electric fringe wave field is given:
> `E = jk ∫_l ( Z I_T ŝ × (ŝ × t̂) + M_T ŝ × t̂ ) exp(−jkr)/(4πr) dl`"
> — Gao et al., *PIER* **122**, 137–154, 2012, eq. (3)

그리고 `I^f, M^f` 자체가 **스트립을 따라간 ILDC 적분**으로 정의된다.

```
I^FW = (|û×t̂| / |ŝ×t̂|²) ŝ·(t̂×ŝ) × ∫_0^∞ J^FW e^{jk ŝ·û u} du       ... (Öztürk 2002, eq. 3.10)
M^FW = ζ (|û×t̂| / |ŝ×t̂|²) t̂·ŝ    × ∫_0^∞ J^FW e^{jk ŝ·û u} du       ... (eq. 3.11)
```

> "This expression states that the incremental diffracted field associated with the end point at the position r̄_e is the endpoint contribution to the field generated by the surface current density J̄^FW on an incremental strip starting at that edge point and extending away from the edge in the direction specified by û."
> — Öztürk 2002, p. 35

**결론: ILDC 와 EEC 는 같은 물건의 두 표기다.** ILDC = 단위길이당 계수, EEC = 그 계수를 낳는 등가 선전류. 구현은 EEC 형태로 한다.

### 2.3 Michaeli EEC ↔ Mitzner ILDC 관계 (Knott 1985)

> "Michaeli derived a set of equivalent edge currents for scattering directions not on the Keller cone, and some years ago, Mitzner developed his incremental length diffraction coefficient (ILDC) for the same purpose. It is shown that **Michaeli's results relate to Mitzner's for arbitrary directions in identically the way Keller's relate to Ufimtsev's for directions on the Keller cone**."
> — E. F. Knott, "The relationship between Mitzner's ILDC and Michaeli's equivalent currents," IEEE TAP **33**(1):112–114, 1985 (색인 초록. ⚠ 원문 전문 미확보 — §10)

읽는 법: Keller:Ufimtsev = 전체전류:프린지전류 다. 그러므로 Michaeli 1984 EEC(전체전류 기반, GTD 계열) 에서 PO 성분을 빼면 Mitzner ILDC(프린지 전용) 가 된다. Michaeli 자신이 1986 년에 **fringe 성분만의 EEC** 를 따로 냈고, 그것이 우리가 쓸 물건이다.

- A. Michaeli, "Equivalent edge currents for arbitrary aspects of observation," IEEE TAP **32**(3):252–258, 1984 — 전체전류 EEC
- A. Michaeli, "Elimination of infinities in equivalent edge currents, Part I: Fringe current components," IEEE TAP **34**(7):912–918, 1986 — **프린지 EEC. 우리가 쓰는 식의 원전**
- K. M. Mitzner, *Incremental Length Diffraction Coefficients*, Aircraft Div., Northrop Corp., Tech. Rep. AFAL-TR-73-296, Apr. 1974 — ILDC 원전 (⚠ 원문 미확보)

**따라서 후보 (a) 와 (b) 는 대립하는 선택지가 아니다.** 어느 쪽을 "고르느냐" 가 아니라 어느 대수 표기가 손에 있느냐의 문제다.

---

## 3. 무한 쐐기 프린지 회절계수 — 닫힌형

### 3.1 좌표와 각도 규약

- 쐐기 모서리는 `ẑ`. 외부(open) 쐐기각 `α`, 그리고 `n := α/π` (반평면은 `α = 2π`, `n = 2`).
- `φ₀` = 입사 방위각, `φ` = 관측 방위각. 둘 다 조명면(face 1)에서 잰다.
- 시간 규약: Ufimtsev 원전은 `e^{−iωt}` (발산파가 `e^{+ikr}`). 현대 EEC 문헌(Michaeli/Johansen/Öztürk/Gao)은 `e^{+jωt}` (`e^{−jkr}`). **부호를 섞지 말 것.**

### 3.2 전체(정확) 쐐기 회절계수 — Ufimtsev (4.08)

```
{ f }        sin(π/n)  (        1                          1                 )
{   } (φ,φ₀,n) = ────── ( ───────────────────────  ∓  ─────────────────────── ),   n = α/π
{ g }             n     ( cos(π/n) − cos((φ−φ₀)/n)     cos(π/n) − cos((φ+φ₀)/n) )
```
— Ufimtsev 1962, eq. (4.08), p. 27. 위 부호(−)가 `f`, 아래 부호(+)가 `g`.

- `f` = **soft / Dirichlet / E-편파** (`E_z` 성분, TM-to-edge)
- `g` = **hard / Neumann / H-편파** (`H_z` 성분, TE-to-edge)

이 두 계수가 나타나는 장 표현은

```
E_z = −H_φ = E_0z · f · e^{i(kr+π/4)} / √(2πkr),   E_φ = H_z = 0     ... (Ufimtsev 4.05 의 f→f 형)
H_z =  E_φ = H_0z · g · e^{i(kr+π/4)} / √(2πkr),   H_φ = E_z = 0     ... (4.06)
```

### 3.3 PO(균일전류) 부분 — Ufimtsev (3.33)/(3.34)

**한 면만 조명될 때** (`0 < φ₀ < α − π`):

```
f^(0) =   sin φ₀ / (cos φ + cos φ₀)
g^(0) = − sin φ  / (cos φ + cos φ₀)                                   ... (3.33) = (4.09)
```

**두 면 다 조명될 때** (`α − π < φ₀ < π`):

```
f^(0) =   sin φ₀ /(cos φ + cos φ₀)  +  sin(α−φ₀) /(cos(α−φ) + cos(α−φ₀))
g^(0) = − sin φ  /(cos φ + cos φ₀)  −  sin(α−φ) /(cos(α−φ) + cos(α−φ₀))   ... (3.34) = (4.10)
```

> "The index "0" for the functions f⁰ and g⁰ means that the cylindrical waves (3.31) and (3.32) are radiated by **the uniform part of the surface current (j⁰)**."
> — Ufimtsev 1962, p. 25

### 3.4 프린지 계수 — Ufimtsev (4.07)

```
f^(1) = f − f^(0)
g^(1) = g − g^(0)                                                     ... (4.07)
```

프린지 장:

```
E_z = −H_φ = E_0z · f^(1) · e^{i(kr+π/4)} / √(2πkr),   E_φ = H_z = 0   ... (4.05)
H_z =  E_φ = H_0z · g^(1) · e^{i(kr+π/4)} / √(2πkr),   H_φ = E_z = 0   ... (4.06)
```

**핵심 성질 두 가지 (원문 인용):**

> "On the boundary of the plane waves (that is, when φ = π ± φ₀ and φ = 2α − π − φ₀) **the functions f, f⁰ and g, g⁰ become infinite, whereas the functions f¹ and g¹ remain finite**."
> — Ufimtsev 1962, p. 28

> "**In the case of radar, when the direction to the observation point coincides with the direction to the source (φ = φ₀), both functions f¹ and g¹ are continuous.**"
> — 같은 곳

두 번째가 우리에게 특히 좋다 — 모노스태틱은 `φ = φ₀` 이고, 거기서 프린지 계수는 연속이다.

### 3.5 경사입사(3-D) — Ufimtsev §5

모서리에 비스듬히 입사해도 **새 함수가 필요 없다.** 규칙은 두 줄이다.

1. `k → k₁ = k sin γ` 로 바꾼다. `γ` 는 회절선이 모서리와 이루는 각(= Keller 원뿔 반각).
2. 방위각을 **모서리 수직면으로 투영한 값**으로 바꾼다: `tan φ₀ = cos β / cos α` (Ufimtsev 5.12, 여기서 α·β 는 입사방향의 방향여현).

```
E_z = −H_γ = E_0z f^(1)(φ,φ₀) · e^{i(k₁r+π/4)}/√(2πk₁r) · e^{ikz cos γ}
H_z =  E_γ = H_0z g^(1)(φ,φ₀) · e^{i(k₁r+π/4)}/√(2πk₁r) · e^{ikz cos γ}    ... (5.10)

E_r = −cot γ · E_z ,  H_r = −cot γ · H_z ,  E_φ = (1/sin γ) H_z ,  H_φ = −(1/sin γ) E_z   ... (5.13)
```

이 `1/sin γ` 가 현대 EEC 식의 `1/sin β'`, `1/sin²β'` 인자의 출처다.

**⚠ 유효 범위:** §5 의 이 구성은 **Keller 원뿔 위에서만** 성립한다(관측각이 입사각과 같은 원뿔각을 이룰 때). 원뿔을 벗어난 방향은 §5 로 못 간다 — 그래서 Michaeli/Mitzner 가 필요하다(§5 의 채택 근거).

### 3.6 수치 검증 — 우리가 직접 돌린 것

`f`, `g`, `f^(0)`, `g^(0)` 를 그대로 코딩해 네 가지를 확인했다.

| 검사 | 결과 |
|---|---|
| (4.08) 이 표준 Keller cot 형과 동일한가 — `cot((π+ψ)/2n) + cot((π−ψ)/2n) = −2 sin(π/n)/(cos(π/n) − cos(ψ/n))` | 무작위 2000 각도쌍, **최대 상대오차 6.1e−12** ✅ |
| `n=2` 에서 반평면 sec 형 `−½[sec((φ−φ₀)/2) ∓ sec((φ+φ₀)/2)]` 로 환원되는가 | 자릿수 전부 일치 ✅ |
| 반사경계 `φ → π−φ₀` 에서 `f,g` 는 발산하고 `f^(1),g^(1)` 는 유한한가 | `f = −1.0e+6` 인데 `f^(1) = −0.2730` 로 유한 ✅ |
| 모노스태틱(`φ=φ₀`) 반평면 닫힌형 | 아래 참조 ✅ |

**반평면(n=2) 모노스태틱 닫힌형 — 우리가 유도해 수치로 확인한 것:**

```
f^(1)(φ₀) = ½ [ (1 − sin φ₀)/cos φ₀ − 1 ]
g^(1)(φ₀) = −½ [ 1 + (1 − sin φ₀)/cos φ₀ ]
```

이로부터 **단위검사로 딱 좋은 두 불변량**이 나온다.

```
f^(1) + g^(1) = −1        (모든 φ₀ 에서 정확히. 수치로 −1.000000000000 확인)
f^(1) = g^(1) = −1/2      (φ₀ = 90°, 즉 시선이 면에 수직일 때)
```

`φ₀=90°` 에서 두 편파가 같아진다는 것은 물리적으로도 맞다 — 수직입사에서는 편파 차이가 사라지고, 비스듬해질수록 갈라진다.

**⚠ 구현 경고 (수치실험에서 나온 것).** 반사경계에 `1e−8` rad 까지 접근시키면 `f ≈ −1e+8`, `f^(0) ≈ −1e+8` 이 되어 배정도에서도 **`f − f^(0)` 이 무너진다**(참값 −0.273 자리에 +1.796 이 나왔다). 이것은 Gao 가 TW-ILDC 를 GPU 단정도가 아니라 CPU 배정도로 돌린 이유와 같은 현상이다.

> "The edge-diffraction effect is more sensitive to round off than multiple bounces. ... Thus, the TW-ILDCs are suitable to be implemented on the CPU with double precision, while single precision should be used to achieve optimal performance without much loss of accuracy in the GPU-based SBR."
> — Gao et al. 2012, p. 142

**대응: 프린지 항은 배정도로, 그리고 `f − f^(0)` 형태를 직접 빼지 말고 §5 에서 채택하는 Michaeli 닫힌형(빼기가 이미 해석적으로 수행된 형태)을 쓴다.**

### 3.7 쐐기가 평평해질 때 — 테셀레이션 안전성

우리 메쉬는 매끈한 셸을 삼각형으로 쪼갠 것이라 **가짜 쐐기**가 잔뜩 있다. `α → π` 에서 프린지가 0 으로 가는지 확인했다(`φ=φ₀=60°`).

| 외부각 α | 359.9° | 300° | 270° | 225° | 200° | 190° | 185° | 181° | 180.1° |
|---|---|---|---|---|---|---|---|---|---|
| `f^(1)` | −0.366 | −0.379 | −0.394 | −0.325 | −0.156 | −0.082 | −0.042 | −0.0087 | −0.00087 |
| `g^(1)` | −0.634 | −0.493 | −0.376 | −0.195 | −0.129 | −0.075 | −0.040 | −0.0086 | −0.00087 |

**읽는 법: 프린지 항은 쐐기가 평평해지면 스스로 사라진다.** 이면각 편차 1° 면 진짜 모서리 대비 −32 dB, 5° 면 −19 dB, 10° 면 −13 dB(진폭). 임계각 문턱은 물리적 필수가 아니라 속도 최적화다.

**⚠ 그래도 방심 금지.** 테셀레이션 모서리는 서로 λ 이하로 촘촘히 붙어 있어 **코히어런트하게 누적될 수 있다**. 개당 −19 dB 라도 100 개가 위상 맞춰 더해지면 +20 dB 가 돌아온다. 그래서 §8 Rung 0(테셀레이션 구) 게이트가 필수다.

---

## 4. Gao 의 TW(truncated wedge) 변형은 무한 쐐기와 무엇이 다른가

### 4.1 무엇을 자르는가

`I^f, M^f` 를 만들 때 프린지 전류를 적분하는 **증분 스트립**의 길이가 다르다.

- **무한(untruncated)**: 스트립이 모서리에서 **무한대까지** 뻗는다 (Öztürk eq. 3.10/3.11 의 `∫_0^∞`). 쐐기 면이 무한하다고 가정.
- **절단(truncated, TW)**: 스트립이 **실제 면이 끝나는 곳(trailing edge)에서 잘린다.**

> "As illustrated in Figure 1, the previous infinite incremental strip is truncated and it extends from the edge to the boundary of the wedge face A. **The truncated equivalent edge currents are represented as the differences between the untruncated EECs and the correction EECs**, and their detailed expressions can be found in [12]."
> — Gao et al. 2012, p. 140. ([12] = Johansen 1996)

```
M_T = M_UT − M_cor ,     I_T = I_UT − I_cor                            ... (Johansen 1996, eq. 3)
```

스트립 방향은 두 경우 모두 같다.

> "From the midpoint of each segment, the truncated incremental strip is traced along **the intersection of the Keller cone and the wedge face**."
> — Gao et al. 2012, p. 140

### 4.2 왜 자르는가

무한 스트립 EEC 의 결함 두 가지를 없애려는 것이다.

> "For the analysis of bistatic radar scattering there are two problems associated with the untruncated EEC's, namely **the presence of the Ufimtsev singularity** and **the discontinuities of the calculated FW field across the current layers associated with the untruncated strips**. The Ufimtsev singularity occurs when the direction of observation is the continuation of an incident field grazing a face of the structure."
> — Johansen 1996, §I

Johansen 판의 성질:

> "New uniform closed-form expressions for physical theory of diffraction equivalent edge currents are derived for truncated incremental wedge strips. In contrast to previously reported expressions, **the new expressions are well behaved for all directions of incidence and observation and take a finite value for zero strip length.**"
> — Johansen 1996, Abstract

Gao 가 TW 를 고른 이유도 같은 문장이다.

> "In contrast to other common diffraction methods, the truncated wedge incremental length diffraction coefficients (TW-ILDCs) are well behaved for all directions of incidence and observation and take a finite value for zero strip length."
> — Gao et al. 2012, p. 138

### 4.3 값비싼 이유

> "In addition, **complex Fresnel integrals are required for the TW-ILDCs**, but the relatively simple Gordon's contour integration can be used to calculate the PO integral in the SBR."
> — Gao et al. 2012, p. 142

Gao Table 1 (초 단위):

| 표적 | SBR step1 | SBR step2(EM) | SBR step3 | TW step4 | TW step5 | 합계(이종) | SBR 단독 |
|---|---|---|---|---|---|---|---|
| Aircraft A | 18.2 | 1046.8 | 219.3 | 7.9 | 906 | 1371.4 | 1311 |
| Aircraft B | 21.5 | 2153.5 | 118.4 | 17.8 | 2410.4 | 2699.9 | 2302.7 |

- TW-ILDC 연산량 = A: 913.9 s (SBR 단독의 **70%**), B: 2428.2 s (SBR 단독의 **105%**).
- 월클럭 증가 = A: +4.6%, B: +17.2% — **CPU 로 밀어 GPU 와 겹쳤기 때문**.

### 4.4 우리 판정

**1 단계에서 TW 는 채택하지 않는다.**

- Ufimtsev 특이점과 스트립 층 불연속은 **바이스태틱 전방향** 계산에서 문제가 된다. 우리 1 단계는 모노스태틱 후방산란이고, 거기서는 무한 스트립 EEC 가 이미 특이점이 없다(§5.2).
- 무한 스트립은 초등함수 + `arccos` 하나면 되고, TW 는 복소 Fresnel 적분이 필요하다.

**⚠ 그러나 이것이 우리 최대 약점이다.** 무한 스트립 가정은 "쐐기 면이 스트립 방향으로 충분히 길다" 를 요구하는데, **우리 표적은 few-λ 다.** 드론 팔 폭, 짐벌 면, 배터리 면은 λ 남짓이다. 즉 **TW 가 물리적으로 옳은 쪽인데 우리가 그것을 미루고 있다** — 이 사실을 리포트에 그대로 적는다. 업그레이드 경로는 Johansen 1996 이고, 그때는 배정도 + Fresnel 적분이 들어온다.

---

## 5. ⭐ 채택 — 가장 단순하면서 옳은 후보

### 5.1 결론

> **채택: (a) Michaeli fringe EEC — 정식 명칭 `untruncated Michaeli PTD-EEC (first order)`.**
> 구체적으로 — Michaeli 1986 의 프린지 EEC 를 **Öztürk 2002 의 모노스태틱 후방산란 특수화 (3.35)–(3.38)** 형태로 구현한다. 얇은 판/열린 모서리(`N=2`)는 반평면 형 (3.33)–(3.34) 로 더 줄어든다.
> **(c) Ufimtsev `f^(1)/g^(1)` 는 버리지 않는다 — 온-콘 단위검사로 쓴다.**
> ⛔ 이 채택안을 **"TW-ILDC"·"ILDC"·"Gao's method"** 라 부르지 않는다 — 절단항이 없다(문서 첫머리 정정).
>
> ⚠ 구현은 일반 바이스태틱 형 (3.23)–(3.32) 으로 돼 있고, 모노스태틱 특수화 (3.35)–(3.38) 은
> 교차검사로만 쓴다(둘은 수치로 8.7e−13 까지 같다).

### 5.2 채택 식 (그대로 구현할 것)

쐐기 외부각 `Nπ`, 국소축 `ẑ` = 모서리 접선, face 1 은 `φ=0` 면. `β'` = 입사가 모서리와 이루는 각, `β` = 관측각, `φ'` = 입사 방위, `φ` = 관측 방위. `Z` = 매질 임피던스, `Y=1/Z`, `U(·)` = 단위계단.

**보조량**

```
cos γ = û·ŝ = sin β' sin β cos φ + cos β' cos β                        ... (3.30)
μ     = (cos γ − cos²β') / sin²β'  =  1 − 2 sin²(γ/2)/sin²β'           ... (3.29)
a     = arccos μ = −j ln( μ + j√(1−μ²) )                               ... (3.28)
```

**face 1 의 PO 성분과 전체 성분 (Michaeli)**

```
I^PO_1 = 2j U(π−φ') / [k sin β' (cos φ' + μ)] · [ sin φ' /(Z sin β') · ẑ·Ē^i_0
                                                  − (cot β' cos φ' + cot β cos φ) ẑ·H̄^i_0 ]     ... (3.24)

M^PO_1 = −2j Z sin φ U(π−φ') / [k sin β sin β' (cos φ' + μ)] · ẑ·H̄^i_0                          ... (3.25)

I_1 = (2j / (k sin β')) · (1/N) / [cos(φ'/N) − cos((π−a)/N)] · [ sin(φ'/N)/(Z sin β') ẑ·Ē^i_0
        + (sin((π−a)/N)/ sin a) (μ cot β' − cot β cos φ) ẑ·H̄^i_0 ]
      − (2j cot β' / (k N sin β')) ẑ·H̄^i_0                                                       ... (3.26)

M_1 = 2j Z sin φ / (k sin β' sin β) · (1/N) sin((π−a)/N) csc a / [cos((π−a)/N) − cos(φ'/N)] · ẑ·H̄^i_0   ... (3.27)
```

**프린지 성분** (= 이 문서의 목표량)

```
I^f_1 = I_1 − I^PO_1 ,   M^f_1 = M_1 − M^PO_1                          ... (3.23)
I^f   = I^f_1 − I^f_2 ,  M^f   = M^f_1 − M^f_2                         ... (3.31)(3.32)
```

face 2 는 변수치환으로 얻는다: `z→−z, β→π−β, β'→π−β', φ→Nπ−φ, φ'→Nπ−φ'`.

**모노스태틱 후방산란 특수화** (`β = π−β'`, `φ = φ'`):

```
μ₁ = cos φ − 2 cot²β                                                    ... (3.35)
μ₂ = cos(Nπ − φ) − 2 cot²β                                              ... (3.36)
a₁ = arccos μ₁ ,  a₂ = arccos μ₂
```

`I^f`, `M^f` 의 완전 전개는 Öztürk 2002 eqs. (3.37)–(3.38). 저자 서술:

> "(3.37) and (3.38) with (3.35) and (3.36) derived for backscattering **do not involve any singularities except the degenerate cases just mentioned** and are used in the computer program for the backscattering calculations."
> — Öztürk 2002, p. 43

퇴화 케이스는 `φ' = π`(면을 스치는 입사)와 `β → 0, π`(모서리 정면 입사)뿐이고, 후자는 반경 적분에 들어가면 사라진다.

**얇은 판 / 열린 모서리 (`N=2`, 반평면) — 가장 단순한 형**

```
I^f = E^i_t · (2jY / (k sin²β')) · √2 sin(φ'/2) / (cos φ' + μ) · [ √(1−μ) − √2 cos(φ'/2) ]
    + H^i_t · (2j / (k sin β')) · 1/(cos φ' + μ) · [ cot β' cos φ' + cot β cos φ
        + √2 cos(φ'/2) (μ cot β' − cot β cos φ)/√(1−μ) ]                                      ... (3.33)

M^f = H^i_t · (2jZ sin φ / (k sin β sin β')) · 1/(cos φ' + μ) · [ 1 − √2 cos(φ'/2)/√(1−μ) ]   ... (3.34)
```

**평판 수직입사 특수화** (`β' = φ' = π/2`, `N=2`) — 검증용:

```
I^f = t̂·Ē^i · (2√2 jY sin(π/4) / (k μ)) [ √(1−μ) − √2 cos(π/4) ]
    + t̂·H̄^i · (2j /(k μ)) [ cot β cos φ − √2 cos(π/4) cot β cos φ / √(1−μ) ]                ... (3.39)
M^f = t̂·H̄^i · (2jZ sin φ / (k sin β μ)) [ 1 − √2 cos(π/4)/√(1−μ) ]                           ... (3.40)
μ   = sin β cos φ                                                                              ... (3.41)
```

### 5.3 왜 이것인가 — 후보별 판정

| 후보 | 오프-콘 유효 | 닫힌형 | 가산 구조 | 원문 확보 | 판정 |
|---|---|---|---|---|---|
| **(a) Michaeli fringe EEC** | ✅ 임의 관측방향 | ✅ 초등함수+arccos | ✅ `E_PO + E_PTDEEC` | ⚠ 2 차출처(Öztürk 2002)로 확보 | **채택** |
| (b) Mitzner ILDC | ✅ | ✅ | ✅ | ❌ AFAL-TR-73-296 미확보 | (a) 와 동일 물리 (Knott 1985). 대수만 (a) 로 |
| (c) Ufimtsev 원형 `f^(1),g^(1)` | ❌ **Keller 원뿔 위에서만** | ✅ 가장 단순 | ✅ | ✅ 원문 확보 | **단위검사 전용** |
| (d) Knott 실용 근사 | ? | ? | ? | ❌ 축자 정의 미확보 | **미확정 — 채택 불가** (§10) |

**(c) 를 본선에서 배제한 결정적 근거 — 우리 표적이 few-λ 라서.**

직선 모서리 길이 `L` 의 모노스태틱 기여는 `L·sinc(kL cos β)` 로 감쇠한다(§7). 온-콘(수직) 대비 오프-콘 억압량을 계산했다.

| `kL` (`L/λ`) | β=90°(온-콘) | 80° | 70° | 60° | 45° |
|---|---|---|---|---|---|
| 6.0 (0.95 λ) | 0.0 dB | −1.6 | −7.3 | −26.6 | −13.5 |
| 12.0 (1.91 λ) | 0.0 dB | −7.6 | −14.0 | −26.6 | −20.4 |
| 20.0 (3.18 λ) | 0.0 dB | −20.6 | −22.2 | −25.3 | −23.0 |
| 60.0 (9.55 λ) | 0.0 dB | −21.9 | −26.3 | −29.6 | −32.6 |

**`L≈1λ` 인 모서리(=우리 드론의 대부분)에서는 시선과 80° 를 이루는 모서리도 −1.6 dB 밖에 안 죽는다.** 오프-콘 방향이 실질적으로 전부 살아 있다. 큰 항공기(`L≈10λ`)라면 (c) 로도 되겠지만 우리는 아니다. → **(a) 필수.**

### 5.4 채택하지 않은 것과 그 이유 (기록)

- **TW 절단(Johansen/Gao)** — 1 단계 미채택. 근거·약점 §4.4.
- **2 차 회절 (Breinbjerg 1992 higher-order EEC)** — 미채택. 우리 표적이 작아 2 차가 상대적으로 크다는 것은 Öztürk 자신이 지적한다.
  > "Since the FW current is assumed to be travelling to infinity in accordance with the half plane geometry, diffraction caused by the same current at another edge is neglected (second-order diffraction). This effect can also be reduced by using a larger plate." — Öztürk 2002, p. 44
- **코너 회절 (Hansen 1991 quarter-plate)** — 미채택. 삼각메쉬는 코너 천지라 열면 끝이 없다.
- **크리핑파** — 범위 밖.

---

## 6. Keller 회절 원뿔 — 모노스태틱에서 어느 모서리가 기여하는가

### 6.1 원뿔 조건

Keller 법칙: 회절선은 모서리와 **입사선과 같은 각**을 이룬다.

```
ŝ · t̂  =  d̂ · t̂                     (d̂ = 입사 진행방향, ŝ = 관측방향, t̂ = 모서리 접선)
```

즉 `β = β'`. 회절선 전체가 반각 `β'` 의 원뿔(Keller cone)을 이룬다.

### 6.2 ⭐ 모노스태틱 특수화

후방산란은 `ŝ = −d̂` 이므로

```
ŝ·t̂ = d̂·t̂   ⟹   −d̂·t̂ = d̂·t̂   ⟹   d̂·t̂ = 0
```

> **모노스태틱 후방산란이 Keller 원뿔 위에 놓이는 것은 모서리가 시선(LOS)에 정확히 수직일 때뿐이다.**
> 등가 표현: `β' = π/2`, 또는 `t̂ ⊥ û`.

이 조건을 만족하면 모서리 전 길이의 위상이 **같아져서** 기여가 코히어런트하게 `L` 에 비례해 쌓인다(진폭 ∝ L, 전력 ∝ L²). 이것이 평판의 leading/trailing edge flash 다.

만족하지 못하면 위상이 모서리를 따라 굴러가고 기여는 `sinc(kL t̂·û)` 로 억압된다(§5.3 표, §7).

### 6.3 사각 평판 예 (주평면 입사)

평판이 `z=0` 에, 시선 `û = (sinθ, 0, cosθ)` 일 때:

- `t̂ = ŷ` 인 두 변 → `û·t̂ = 0` → **온-콘. 지배한다.** 두 변이 `x=±a/2` 에 있으므로 상대위상 `e^{±jka sinθ}` 로 **간섭**한다 → RCS 패턴의 로빙 주기 `Δ(2a sinθ) = λ`.
- `t̂ = x̂` 인 두 변 → `û·t̂ = sinθ ≠ 0` → 오프-콘. `sinc(ka sinθ)` 로 억압.

즉 **입사면에 수직인 두 변이 프린지 기여를 낳고 서로 간섭한다.** Öztürk 도 같은 말을 한다.

> "The deep nulls throughout the pattern are caused by **the destructive interference of the fields caused by two orthogonal edges**."
> — Öztürk 2002, p. 44

### 6.4 조명 판정

원뿔 조건과 별개로 **그 모서리 조각이 실제로 조명되어야** 한다.

> "Equivalent currents are assumed to exist at an edge segment **if only it is illuminated**. Otherwise no FW currents are induced at the edge point."
> — Öztürk 2002, p. 48

Gao 도 각 입사각마다 다시 계산한다고 명시한다.

> "As the edge may be visible partially, the edge is split into small segments to ensure the accuracy of the result. ... The visibility and the truncated segments of the edges described above are **recalculated for each incident angle** because they vary with the angle of incidence."
> — Gao et al. 2012, p. 140

우리 구현은 이미 SBR 가시성 판정(`_exit_visible`)을 갖고 있으니 재사용한다.

---

## 7. 모서리 조각 적분 — 해석적으로 되는가

### 7.1 답: 된다. `sinc` 다.

직선 모서리 조각에서 `I^f, M^f` 는 **상수**다 — `β', β, φ', φ, N` 이 조각 내내 안 바뀌기 때문이다(평면파 + 원거리 + 삼각메쉬의 한 edge 는 두 삼각형만 공유). 그러면 (3.7) 의 선적분은 위상항만 남는다.

조각을 `r'(u) = r_c + u t̂`, `u ∈ [−L/2, L/2]` 로 두면, 모노스태틱 위상은 `exp(j 2k û·r')` 이므로

```
∫_{−L/2}^{L/2} e^{j 2k û·(r_c + u t̂)} du
   = L · e^{j 2k û·r_c} · sinc( k L (t̂·û) ),        sinc(x) := sin(x)/x
```

**정확한 닫힌형이다. 수치 구적 불필요.**

- `t̂·û = 0` (온-콘·시선수직) → `sinc = 1` → 전 길이가 위상 맞춰 더해진다.
- 벗어날수록 `sinc` 로 죽는다 — §5.3 의 표가 그 값이다.
- 파수 인자가 `k` 가 아니라 `2k` 인 것에 주의(모노스태틱 왕복).

### 7.2 그러면 무엇이 수치인가

| 항목 | 해석/수치 |
|---|---|
| 모서리 방향 선적분 | **해석 (sinc)** |
| `I^f, M^f` 계수 | **해석** (초등함수 + `arccos`). 스트립 방향 적분은 Michaeli 가 이미 해 놓았다 |
| 모서리 가시성·부분조명 | **수치** — 가려진 부분에서 조각을 잘라야 한다. 자른 조각마다 위 `sinc` 를 다시 쓴다 |
| `N`(국소 쐐기각) 추출 | **수치** — 인접 삼각형 두 법선에서 |
| 곡선 모서리 | 조각별 직선 근사 후 조각마다 `sinc` |

### 7.3 무엇이 이 해석성을 깨뜨리는가

- **TW 절단**을 도입하면 `I_cor, M_cor` 에 복소 Fresnel 적분이 들어온다(§4.3). 모서리 방향 `sinc` 자체는 그대로 살아 있다.
- 근접장(near-field) 관측이면 `sinc` 가 깨진다. 우리 모노스태틱 RCS 는 원거리라 무관하다.

---

## 8. 검증 표준 케이스 — PTD 구현이 맞는지 어떻게 아는가

**사다리로 오른다. 아래 칸을 통과하지 못하면 위 칸을 보지 않는다.**

### Rung 0 — 테셀레이션 구 (메쉬 인공물 게이트) ⭐ 우리가 추가한 칸

**표적:** 진짜 모서리가 하나도 없는 매끈한 구를 삼각형으로 쪼갠 것 (`rcs_po._sphere_mesh` 그대로).
**기대:** PTD 항을 켜도 σ 가 **거의 안 움직여야** 한다. 움직이면 그것은 물리가 아니라 우리 메싱이다.
**허용:** 전 방위에서 |Δσ| < 0.3 dB. (숫자는 우리가 정한 문턱이고 문헌값이 아니다.)
**근거:** §3.7 — 프린지는 `α→π` 에서 스스로 0 으로 가지만, 촘촘한 가짜 모서리가 코히어런트하게 쌓일 수 있다.
**참조값:** 구의 PO 해석해 `E = 2πr²[e^{jb}(1/(jb) + 1/b²) − 1/b²], b = 2kr` — `src/rcs_po.py` 가 이미 ±0.015 dB 로 재현한다.

### Rung 1 — 반평면 해석 불변량 (계수 단위검사)

계수 코드만 시험한다. 기하 없음.

| 검사 | 참조값 | 출처 |
|---|---|---|
| `f^(1) + g^(1)` at `φ=φ₀` (n=2) | **정확히 −1**, 모든 `φ₀` | 우리 유도, Ufimtsev (4.07)(4.08)(3.33) 에서. 수치로 −1.000000000000 확인 |
| `f^(1) = g^(1)` at `φ₀=90°` | **−1/2** | 같음 |
| `f, g` ↔ Keller cot 형 | 상대오차 < 1e−10 | 항등식 `cot((π+ψ)/2n)+cot((π−ψ)/2n) = −2sin(π/n)/(cos(π/n)−cos(ψ/n))` |
| 반사경계에서 `f^(1)` 유한 | `f→−1e6` 일 때 `f^(1)=−0.273` | Ufimtsev p. 28 축자 |
| Michaeli EEC → Ufimtsev `f^(1),g^(1)` (온-콘 `β=β'`) | 일치 | ⚠ **우리가 아직 확인 안 함.** 구현 후 첫 검사로 |

### Rung 2 — ⭐ 사각/직사각 평판 모노스태틱 σ(θ) (정석)

> ⚠ **합격 기준 정정 (2026-08-03, 결함 D-7).** 아래의 "dB-RMS 가 개선되는가" 류 지표는 **위상맹목**이라 180° 부호오류를 통과시킨다(실제로 통과시켰다 — 부호가 뒤집힌 커널이 oblique RMS 를 11.0 → 5.4 dB 로 '개선'했다. 모서리 전력을 **비코히런트로** 더하면 2.65 dB 로 더 좋아진다). **1차 게이트는 위상이다**: 평판 on-cone 모서리에서 `arg(A_code / A_analytic) < 1e−6°`. RMS 지표는 2차이고, 인용할 때는 비코히런트·무작위위상 기준선과 **항상 같이** 적는다.

**왜 이것이 정석인가.** PO 는 평판에서 편파를 구분하지 못한다. 그런데 실제 평판은 비정반사 방위에서 HH/VV 가 갈린다. **그 갈라짐 전부가 프린지 항이다.**

> "Although PO is polarization independent, PTDEEC is not, therefore, results for the fuel tank for horizontal and vertical polarizations differ."
> — Albayrak 2005 (Bilkent MSc), p. 50

Ross 1966 의 결론도 같은 말이다.

> Simple physical optics theory provides accurate predictions for near-specular values but **fails to account for polarization dependence in nonspecular regions**, while calculations using the geometrical theory of diffraction show excellent agreement with measured data except at edge-on aspects.
> — R. A. Ross, IEEE TAP **14**(3):329–335, 1966 (⚠ 색인 초록 요약. 원문 미확보 — §10)

**PO 참조 닫힌형 (직접 검산 가능).** 판 `a×b`, `z=0`, 주평면 입사, 법선에서 `θ`:

```
A_PO(θ) = a b cos θ · sinc(k a sin θ)
σ_PO(θ) = (4π a²b² / λ²) cos²θ · sinc²(k a sin θ)
σ_PO(0) = 4π A² / λ²                                  (A = ab)
첫 널:  k a sin θ = π  ⟹  sin θ = λ/(2a)
```

`6λ × 6λ` 판이면 `σ_PO(0) = 4π(36λ²)²/λ² = 16286 λ²` = **+42.1 dB(λ² 기준)**, 첫 널 `θ = 4.78°`.

**참조값 출처 (신뢰 순):**

| # | 출처 | 무엇을 주는가 | 확보 |
|---|---|---|---|
| R2-a | **Öztürk 2002, Fig. 3.7** — `σ_φφ` of a square plate of area `36λ²`, PTD-EEC vs **MoM** (Breinbjerg PhD 1991 에서 인용) | 우리 채택 식과 **같은 식**으로 계산된 곡선 + MoM 기준선 | ✅ PDF 확보 |
| R2-b | **Breinbjerg, IEEE TAP 40(12):1543–1552, 1992** — 정사각판 바이스태틱 RCS, 1 차 EEC vs 고차 EEC vs MoM | 2 차 회절 크기의 상한 | ✅ PDF 확보 (DTU orbit) |
| R2-c | **Ross, IEEE TAP 14(3):329–335, 1966** — 직사각 평판 실측 σ(방위), HH/VV | **실측** 기준. 편파 갈라짐의 원전 | ❌ 원문 미확보 |
| R2-d | **Knott, Shaeffer, Tuley, _Radar Cross Section_, Artech House, 1985 (Ch. 6)** — PO vs PTD 평판 비교 도판 | 교재 표준 곡선 | ❌ 도판 수치 미확보 |
| R2-e | **Stein, ACES Journal 7(1), 1992** — "Application of Equivalent Edge Currents to Correct the Backscattered Physical Optics Field of Flat Plates" | 우리 케이스와 **정확히 같은 문제** | ❌ 원문 미확보 |

**합격 기준(제안):** 정반사 로브 ±(첫 널) 안에서 PO 단독과 PO+PTD 가 0.5 dB 이내로 같을 것(PTD 가 정반사를 망가뜨리면 안 됨). 비정반사 방위에서 HH/VV 분리가 나타날 것. R2-a 곡선과 형상(널 위치)이 일치할 것.

### Rung 3 — ⭐ 짧은 원기둥 (few-λ, 우리 체급과 가장 가까움)

**표적:** `ka = 2.16`, `k l_c = 12.45` PEC 원기둥 (= 반지름 0.344λ, 길이 1.98λ), 2.6 GHz, H 편파.
**참조:** **실측** — J. F. Shaeffer, IEEE TAP **AP-30**(3):426–431, 1982. `σ₀ = 0.0052` 로 정규화.
**출처:** Öztürk 2002 Fig. 3.10 (PO only vs PO+PTDEEC vs 실측), Albayrak 2005 Fig. 4.4 (PO vs PO+PTDEEC vs MoM).
**왜 중요한가:** `2λ` 급 표적이다. 우리 드론(1.8–5.2 GHz 에서 0.3–1.5 m ⇒ 2–26λ)과 체급이 겹친다. 그리고 두 논문이 "PO 단독보다 PO+PTDEEC 가 실측에 가까워진다" 고 명시적으로 기록한 유일한 few-λ 케이스다.

> "It is observed that addition of PTDEEC improves the PO only result, such that the total RCS data approaches to the experimental result."
> — Albayrak 2005, p. 49

### Rung 4 — 원판 (곡선 모서리 스트레스 테스트)

`ka = 5, 10, 15` PEC 원판의 바이스태틱 `σ_φφ`, 수직입사. 참조는 Breinbjerg 의 정확해(Öztürk Fig. 3.8).
**기대되는 실패 방향(기록):** 반지름이 작을수록 나빠진다. 우리 드론은 작다.

> "It is observed that the agreement ... improves with increasing disc radius. The edge interaction effects decrease as the disc size becomes larger. When the disc size is small, the FW surface current possess sufficient strength to cause diffraction at the edge point of interest after traversing the disc."
> — Öztürk 2002, p. 45

### Rung 5 — 우리 드론 with/without 진단

Rung 0–4 통과 후에만. `docs/HOW_OTHERS_SOLVED_IT.md` §3 의 실험 설계(같은 스윕을 edge 항 on/off 두 번, 기울기 부호 + IFFT 거리프로파일에서 추가 에너지 위치)를 그대로 쓴다.
**⚠ 예측을 먼저 기록한다:** 우리 산술은 주파수 무관 edge 항 하나로 3.5–8 배 기울기 초과가 닫히지 **않는다**고 예측한다. 닫힌다면 절대 레벨이 6–12 dB 튀어 P5 와 충돌한다.

---

## 9. 우리 커널에 붙이는 방법

### 9.1 정규화 — PO 적분과 같은 단위로

우리 PO 커널은

```
A_PO(û) = Σ_lit (n̂·û) |Γ| ΔA e^{j2k r·û}          [m²]
σ       = (4π/λ²) |A_PO|²
```

프린지 항을 같은 "등가면적" 단위로 옮기면 (`|E^i_0| = 1`, 원거리, 모노스태틱)

```
A_FW(û) = −½ Σ_segments [ ζ (ŝ×(ŝ×t̂))·ê_r I^f + (ŝ×t̂)·ê_r M^f ] · L · e^{j2k û·r_c} · sinc(k L t̂·û)

σ_total = (4π/λ²) | A_PO + A_FW |²
```

### ⚠⚠ 부호 정정 (2026-08-03, 결함 D-1)

**예전 이 자리에는 `+½` 이 적혀 있었고, 근거는 `λk/(4π) = ½` 라는 크기 계산뿐이었다. 크기는 맞고 부호가 틀렸다.** 옳은 상수는 `−½` 이며, 유도는 세 줄이다.

**(A) 우리 `A` 규약이 대응하는 원거리장 상수는 음수다.**
평면파 `E^i = ê e^{+jk û·r}`(진행방향 `d̂ = −û`, `e^{jωt}` 규약), PO 전류 `J = 2 n̂×H^i`, `H^i = (1/Z₀) d̂×ê`, 벡터 복사적분 `E = −jωμ/(4πr) e^{−jkr} ∫J_⊥ e^{jkŝ·r'}` 를 그대로 밀면

```
E^s·ê = −(jk/2π) (e^{−jkr}/r) · A_PO ,      A_PO = Σ_lit (n̂·û) ΔA e^{j2k û·r}
```

음부호는 `d̂ = −û` 에서 온다 — 복사적분은 **진행**방향으로 쓰이고 `A_PO` 는 **바깥쪽 시선** `û` 로 쓰여 있다. (수치 확인: 벡터 복사적분을 직접 계산한 값 / 위 식 = `1.0 ∠1e−14°`. 그리고 `σ = 4πr²|E^s|² = (4π/λ²)|A_PO|²` 로 규약이 닫힌다.)

**(B) EEC 복사적분의 문헌 상수는 `+jk/(4π)` 다** — §2.2 의 Öztürk (3.7) / Gao (3) 축자 인용 그대로.

**(C) 따라서** `A_FW / Σ[...] = (jk/4π) / (−jk/2π) = −½`. `j` 는 지워지고 남는 `−1` 은 (A) 의 음부호다.

**근원 판정** — 뒤집힌 것은 Michaeli 계수도, 면 법선도, 적분 방향도 아니다(계수는 Johansen 이 옮긴 Michaeli (4)–(7) 과 6e−12 일치, 면 순서 교환 불변, `t̂` 부호는 `g_I·I^f`·`g_M·M^f` 가 둘 다 홀수라 곱에서 상쇄). **뒤집힌 것은 이 절의 유도 하나** — 크기만 취하느라 (A) 와 (B) 의 **상대부호**를 버렸다.

**합격 기준 (Rung 2 게이트로 승격, D-7)** — 크기비가 아니라 **위상**이다.

```
arg( A_code / A_analytic_Ufimtsev ) = 0°       (|ratio| 는 180° 오류를 통과시킨다 — 실제로 통과시켰다)
```

수리 후 측정: `|ratio| − 1 = 1.4e−14`, `|arg| ≤ 5.8e−13°` (θ = 5…84°, 양 편파, 평판 on-cone 모서리 24 점).
이 게이트는 `benchmark/smoke_ptd.py` 의 `(f)` 칸에 상설로 들어갔고 실패하면 예외를 던진다.

### 9.2 편파 — 스칼라 커널의 한계

`I^f, M^f` 는 `ẑ·Ē^i_0`, `ẑ·H̄^i_0` 를 요구한다. **PTD 를 붙이는 순간 편파 상태를 정의해야 한다.** 우리 PO 는 스칼라(`|Γ|`)다.

**방침:** PTD 진단은 **VV / HH 두 편파를 따로** 돌리고 둘 다 보고한다. 스칼라 PO 는 PEC 극한의 co-pol 값으로 두 편파에 공통으로 쓴다. 이것은 근사이며 그렇게 표기한다.

### 9.3 재질 — PEC 프린지 vs `|Γ|` 가중 PO

프린지 계수는 PEC 유도다. 플라스틱 셸(`|Γ|≈0.3`) 모서리에 PEC 프린지를 붙이면 과대계상이다.

**방침 (보수적):** **양쪽 인접면이 모두 금속(`|Γ|=1`)인 모서리에만 PTD 를 적용**한다. 나머지 모서리는 보정하지 않고, 보정 안 한 모서리 길이 비율을 리포트에 적는다. `|Γ|` 로 프린지를 스케일하는 것은 유도가 없는 휴리스틱이므로 하지 않는다.

### 9.4 모서리 추출

1. 인접 삼각형 2 개를 공유하는 edge 를 모은다(메쉬는 거의 manifold).
2. 두 법선에서 이면각 → 외부각 `α` → `N = α/π`.
3. 인접 삼각형이 1 개뿐인 열린 edge → `N = 2` (반평면).
4. 문턱: `|α − π| < 5°` 는 건너뛴다 (진폭 −19 dB 이하, §3.7). ⚠ **순수한 속도 최적화가 아니다** — 매끈한 테셀레이션 구에서 이 이음매 무리는 메쉬를 조밀하게 해도 사라지지 않고(진폭 바닥 −32.5 dB @kr 13.1 → −40.6 dB @kr 36.7, log-log 기울기 −0.62), mini5pro 에서는 `|α−180°|<10°` 이음매만으로 금속 모서리 전체보다 **더 큰** 진폭이 나온다. 드론 숫자는 `sharp_deg` 5–30° 밴드로 보고하고 단일값을 인용하지 않는다.
5. ⭐ **오목(reentrant, `α < 180°` 즉 `N < 1`) 모서리는 버린다** — 전체전류 분모 `cos(φ'/N) − cos((π−a)/N)` 이 PO 분모와 짝이 맞지 않는 추가 영점(오목 구석의 다중반사 경계)을 갖고 `N = 1/(2m)` 은 정확한 극이다. 1차 PTD + 단일반사 PO 뺄셈으로 균일하게 다룰 수 없다. 버린 길이 비율을 리포트에 적는다(`reentrant_length_fraction`). 진단용은 `keep_reentrant=True`.
6. 조각 분할: 가시성이 바뀌는 지점에서 자른다. Gao 는 10 GHz 항공기에서 14000–40000 조각을 썼다.

### 9.5 비용 예상

Gao 의 비율(TW-ILDC ≈ SBR 연산량의 70–105%) 을 그대로 옮기면 안 된다 — 그건 TW(Fresnel 적분) 이고 우리는 무한 스트립(초등함수)이다. 그러나 **모서리 조각 수 × 방위각 수** 가 지배하므로 자릿수는 PO 면적분과 비슷하다고 보는 것이 안전하다. 배정도 필수(§3.6).

---

## 10. ⚠ 확정 못 한 것 · 미확보 원문

**원문을 못 본 것 (2 차출처로만 확보):**

| 문헌 | 상태 | 대체 경로 |
|---|---|---|
| Michaeli 1986, IEEE TAP 34(7):912–918 — **우리 채택 식의 원전** | ❌ 미확보 | Öztürk 2002 (3.23)–(3.41) 로 확보. ⭐ **원문 대조는 구현 전 필수** |
| Michaeli 1984, IEEE TAP 32(3):252–258 | ❌ 미확보 | — |
| Mitzner 1974, AFAL-TR-73-296 | ❌ 미확보 | Knott 1985 관계로 대체 |
| Knott 1985, IEEE TAP 33(1):112–114 | ❌ 전문 미확보 (초록만) | — |
| Ross 1966, IEEE TAP 14(3):329–335 | ❌ 미확보 (서지·초록 요약만) | — |
| Knott/Shaeffer/Tuley, *Radar Cross Section*, Artech 1985 | ❌ 미확보 | — |
| Stein 1992, ACES J. 7(1) | ❌ 미확보 | — |
| Shaeffer 1982, IEEE TAP AP-30(3):426–431 (Rung 3 실측 원전) | ❌ 미확보 | Öztürk Fig. 3.10 / Albayrak Fig. 4.4 로 재인용 |

**후보 (d) "Knott 의 실용 근사" 는 확정하지 못했다.** 아카이브·웹에서 그 이름으로 특정되는 축자 정의를 찾지 못했다. Knott 의 이 분야 기여로 확인된 것은 (i) Knott & Senior 의 세 고주파 기법 비교, (ii) Knott 1985 의 ILDC↔EEC 관계 규명이고, 둘 다 "근사식" 이 아니다. **지어내지 않고 미확정으로 남긴다.**

**아직 확인하지 않은 검사:**

- Michaeli EEC 를 온-콘(`β=β'`)에서 평가하면 Ufimtsev `f^(1), g^(1)` 로 환원되는가 — 구현 후 첫 검사.
- §9.1 의 정규화 상수 `½`.
- Rung 0 문턱 0.3 dB 가 우리 메쉬 밀도에서 달성 가능한가.

**뒤집힐 수 있는 판단:**

- **TW 미채택.** few-λ 표적에서 무한 스트립 가정이 가장 약하다는 것을 알고도 미룬 것이다. Rung 3(원기둥) 이 실측과 안 맞으면 여기부터 의심한다.
- **`|Γ|=1` 모서리에만 적용.** 드론 모서리 대부분이 플라스틱이면 PTD 가 거의 아무 데도 안 붙어서 진단력이 0 이 될 수 있다. 적용 모서리 길이 비율을 먼저 재 본다.
- **1 차 회절만.** Öztürk·Breinbjerg 둘 다 작은 표적에서 2 차가 커진다고 적었다.

---

## 11. 참고문헌

**확보한 원문 (PDF 로 읽음):**

1. P. Ya. Ufimtsev, *Method of Edge Waves in the Physical Theory of Diffraction*, Izd-Vo Sov. Radio, 1962. English translation, U.S. Air Force Foreign Technology Division, **FTD-HC-23-259-71**, Sept. 1971. — §§3–6, eqs. (3.31)–(3.34), (4.05)–(4.10), (5.10)–(5.16). *(archive.org 사본)*
2. P. C. Gao, Y. B. Tao, Z. H. Bai, H. Lin, "Mapping the SBR and TW-ILDCs to Heterogeneous CPU-GPU Architecture for Fast Computation of Electromagnetic Scattering," *Progress In Electromagnetics Research* **122**, 137–154, 2012. DOI 10.2528/PIER11092303. *(로컬 아카이브: `/data/public/sionna_jeong/reference_library/new_0803/pier2011__sbr-twildcs-cpu-gpu-fast-rcs.pdf`)*
3. P. M. Johansen, "Uniform Physical Theory of Diffraction Equivalent Edge Currents for Truncated Wedge Strips," *IEEE Trans. Antennas Propag.* **44**(7):989–995, 1996. DOI 10.1109/8.504306. — Gao 의 ref [12]. *(DTU Orbit)*
4. A. K. Öztürk, "Implementation of Physical Theory of Diffraction for Radar Cross Section Calculations," MSc thesis, Bilkent Univ., July 2002. — Michaeli 프린지 EEC 의 완전 전개 + 모노스태틱 특수화 + 평판·원판·원기둥 검증.
5. N. A. Albayrak, "RCS Computations with PO/PTD for Conducting and Impedance Objects Modeled as Large Flat Plates," MSc thesis, Bilkent Univ., July 2005.
6. O. Breinbjerg, "Higher Order Equivalent Edge Currents for Fringe Wave Radar Scattering by Perfectly Conducting Polygonal Plates," *IEEE Trans. Antennas Propag.* **40**(12):1543–1552, 1992. *(DTU Orbit)*
7. B. B. Wu, W. C. Chew, "The Modern High Frequency Methods for Solving Electromagnetic Scattering Problems," *PIER* **156**, 63–82, 2016.

**서지만 확인 (원문 미확보):**

8. A. Michaeli, "Elimination of infinities in equivalent edge currents, Part I: Fringe current components," *IEEE TAP* **34**(7):912–918, 1986. ⭐ **우리 채택 식의 원전**
9. A. Michaeli, "Equivalent edge currents for arbitrary aspects of observation," *IEEE TAP* **32**(3):252–258, 1984.
10. K. M. Mitzner, *Incremental Length Diffraction Coefficients*, Northrop Corp. Aircraft Div., Tech. Rep. **AFAL-TR-73-296**, Apr. 1974.
11. E. F. Knott, "The relationship between Mitzner's ILDC and Michaeli's equivalent currents," *IEEE TAP* **33**(1):112–114, 1985.
12. R. A. Ross, "Radar cross section of rectangular flat plates as a function of aspect angle," *IEEE TAP* **14**(3):329–335, 1966.
13. E. F. Knott, J. F. Shaeffer, M. T. Tuley, *Radar Cross Section*, Artech House, 1985 (Ch. 6).
14. V. Stein, "Application of Equivalent Edge Currents to Correct the Backscattered Physical Optics Field of Flat Plates," *ACES Journal* **7**(1), 1992.
15. J. F. Shaeffer, "EM Scattering from Bodies of Revolution with Attached Wires," *IEEE TAP* **AP-30**(3):426–431, 1982.
16. J. J. Griesser, C. A. Balanis, "Backscatter analysis of dihedral corner reflectors using physical optics and the physical theory of diffraction," *IEEE TAP* **35**(10):1137–1147, 1987. DOI 10.1109/TAP.1987.1143987.
17. T. B. Hansen, "Corner diffraction coefficients for the quarter plane," *IEEE TAP* **39**(7):976–984, 1991.
18. F. Weinmann, *IEEE TAP* **54**(6):1797–1806, 2006 — PO/PTD 를 광선추적에 넣는 표준 참조.
19. E. Kırık, Ö. Özdemir, "An Accurate and Effective Implementation of Physical Theory of Diffraction to the Shooting and Bouncing Ray Method via Predics Tool," *Sigma J. Eng. Nat. Sci.* **37**(4):1153–1166, 2019.

---

## 부록 A — 재현 스크립트 (§3.6·§3.7·§5.3 의 숫자)

```python
import numpy as np

def fg(phi, phi0, n):
    """Ufimtsev (4.08). n = alpha/pi. returns (f=soft/E, g=hard/H)."""
    s = np.sin(np.pi/n)/n
    A = 1.0/(np.cos(np.pi/n) - np.cos((phi-phi0)/n))
    B = 1.0/(np.cos(np.pi/n) - np.cos((phi+phi0)/n))
    return s*(A-B), s*(A+B)

def fg0_one(phi, phi0):
    """Ufimtsev (3.33): PO part, ONE face lit  (0 < phi0 < alpha-pi)."""
    d = np.cos(phi) + np.cos(phi0)
    return np.sin(phi0)/d, -np.sin(phi)/d

def fg0_two(phi, phi0, alpha):
    """Ufimtsev (3.34): PO part, BOTH faces lit  (alpha-pi < phi0 < pi)."""
    d1 = np.cos(phi) + np.cos(phi0)
    d2 = np.cos(alpha-phi) + np.cos(alpha-phi0)
    return (np.sin(phi0)/d1 + np.sin(alpha-phi0)/d2,
            -np.sin(phi)/d1 - np.sin(alpha-phi)/d2)

def fringe(phi, phi0, alpha):
    """Ufimtsev (4.07): f1 = f - f0, g1 = g - g0."""
    n = alpha/np.pi
    f, g = fg(phi, phi0, n)
    f0, g0 = fg0_one(phi, phi0) if 0 < phi0 < alpha-np.pi else fg0_two(phi, phi0, alpha)
    return f-f0, g-g0

# Rung 1 unit tests
for p in np.radians([10, 45, 80, 100, 150]):
    f1, g1 = fringe(p, p, 2*np.pi)              # half-plane, monostatic
    assert abs(f1 + g1 + 1.0) < 1e-10           # f1 + g1 == -1  exactly
# both -> -1/2 at normal incidence. NOTE: do not push delta below ~1e-4 rad --
# f and f0 each blow up like 1/delta and the double-precision subtraction dies
# (section 3.6). This is why the production path uses Michaeli's closed form,
# where the subtraction f - f0 has already been done analytically.
delta = 1e-3
f1, g1 = fringe(np.radians(90)-delta, np.radians(90)-delta, 2*np.pi)
assert abs(f1 + 0.5) < 1e-3 and abs(g1 + 0.5) < 1e-3
print("Rung 1 OK   f1=%.6f g1=%.6f" % (f1, g1))

# monostatic straight-edge coherence factor (section 7)
def edge_sinc(kL, beta_deg):
    x = kL*np.cos(np.radians(beta_deg))
    return 1.0 if x == 0 else np.sin(x)/x
```
