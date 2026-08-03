# 선행연구 상시 정독 — 대조 기록 (라운드 1, 2026-08-03)

> 산출물: `outputs/deepread_reconcile.json` (이 문서의 기계 판본)
> 입력: `outputs/deepread_w1.json` … `deepread_w5.json`, `outputs/deepread_backlog.json`
> ⛔ **이 라운드는 기존 기록을 하나도 수정하지 않았다.** 병행 워크플로가 같은 파일에 있을 수 있어서다.
> §2 의 정정 목록은 *적용 지시서*이지 적용 결과가 아니다.
>
> **규칙** — 논문에 대한 주장에는 축자 인용문 + PDF 경로 + 쪽수가 붙는다. 없으면 UNVERIFIED 이고,
> UNVERIFIED 는 보고해도 되는 결과다.

---

## 0. 이 라운드가 한 일

다섯 웨이브가 **고유 문서 51편**(파일 경로 55개, 판본 중복쌍 4개 접음)을 쪽 단위로 읽었다.
그중 40편은 이전까지 정독된 적이 없었고(용어 카운트 또는 산문 언급만 있었다), 14편은 특정 칸을
채우려고 다시 열었으며, 2편은 트리아지 목록에 아예 없던 파일이다.

| 판정 | 수 |
|---|---|
| 깨진 주장 | **0** |
| 좁혀야 하는 주장 | **3** (C1 · C3 · C4) |
| 그대로 유효한 주장 | 2 (H8 · C2) |
| 우리 기록 정정 항목 | **21** |
| **우리가 앞서 내린 정정이 다시 틀린 건** | **1** ⭐ |
| 기계 센서스 오탐 유형 | 5 |
| 능력매트릭스 제안 행 | 33 |

### 0.1 인용 재대조를 먼저 했다

웨이브 기록을 그대로 승계하면 '읽지 않고 인용' 이 한 단계 늘어난다. 그래서 이번 라운드에서 가장
무게가 실린 인용문 11건을 **내가 직접 PDF 를 열어 재대조**했다. 결과는 **11/11 축자 일치**다.
다만 쪽번호 하나가 어긋났으므로(Taylor 의 10log10(7) 문장은 p.11-12 가 아니라 p.11), 쪽을 인용할
때는 웨이브 기록이 아니라 `deepread_reconcile.json : verification_today` 를 쓴다.

---

## 1. ⭐⭐ 먼저 — 우리 자신이 두 번째로 틀렸다

깨진 것은 선행연구가 아니라 **우리 오류기록의 1번 항목 자체**다.

우리는 "v_max = λ·PRF/4 를 우리 발견이라 주장했다 → Chen et al. 2024 가 먼저 냈고 기호까지 같다"
라고 스스로를 정정했었다. 그 정정이 **두 군데에서 틀렸다.**

**(a) Chen 은 최초가 아니다.** 1년 앞선 게재본이 같은 축에서 같은 규약을 식 번호까지 붙여 인쇄한다.

> "The Doppler range is limited by T SSB dist so that Vb ∈ [ −λ/(4 T SSB dist) , λ/(4 T SSB dist) ]  (16)"
> — K. Abratkiewicz, A. Ksiezyk, M. Plotka, P. Samczynski, J. Wszolek, T. P. Zielinski,
> "SSB-Based Signal Processing for Passive Radar Using a 5G Network",
> **IEEE JSTARS 16:3469-3484, 2023, 게재** (DOI 10.1109/JSTARS.2023.3262291), p.8
> `/data/public/sionna_jeong/reference_library/g1g2/abratkiewicz2023_jstars.pdf`
> *(내가 오늘 직접 재대조)*

**(b) "같은 기호" 는 거짓이다.** Chen 2024 전문 20쪽에 `PRF` 라는 기호는 **0회**이고 v_max 의 닫힌
기호식도 없다 — 수치로만 조립한다. *(내가 오늘 정규식으로 재계수)*

**정답은 우선권 다툼이 아니다.** 이 식은 표본화 정리의 직접 귀결이고 두 논문 모두 그렇게 쓴다.
우리가 "우리 발견" 이라 부른 것도, "Chen 이 최초" 라고 정정한 것도 둘 다 과잉 주장이었다.

> **남는 우리 몫**은 식이 아니라, 서로 다른 축·규약으로 인쇄된 게재 수치 11편 이상을 하나의 규약
> (±λ/4T)으로 환산해 나란히 놓은 **대조표**다. 그 표가 없으면 같은 "SSB 패시브 레이더" 라는 이름
> 아래 ±1.09 m/s(Abratkiewicz, T_SSB 축)와 수백 m/s(Jopanya, 심볼 축)가 동시에 인쇄되는 이유를
> 아무도 설명하지 않는다.

⚠ 같은 오류가 이번까지 세 번째다(R20 novelty, Ziganshin 판본, 이번 우선권). **원인은 매번 같다 —
2차 인용으로 우선권을 판정했다.** 그리고 이번에도 우리 기록 안에서 파일마다 말이 달랐다:
`outputs/capability_matrix.json` 의 headline 은 이미 Abratkiewicz eq.(16) 을 바르게 적고 있었고,
`reflib_sweep_geometry.json` 만 "our equation, our symbols, two years earlier" 라고 적고 있었다.

---

## 2. 정정 목록 — 무엇을 어떻게 고쳐야 하는가

전체 21건은 `deepread_reconcile.json : corrections_patchlist.items` 에 있다.
아래는 CRITICAL·HIGH 다섯 건이다.

### P01 · CRITICAL — 무모호속도식 우선권
- **대상**: 우리 세션 오류기록 1번 · `reflib_sweep_geometry.json:entries[chen2024appliedsci].ambiguity.reports`
  · `reference_library.json:novelty_guards[G4]` · `reference_library.json:gap_statement.what_we_must_not_claim_ko[2]`
- **우리가 쓴 말**: "our equation, our symbols, two years earlier"
- **고친 말**: 위 §1 참조. Chen 은 기호식을 쓰지 않으며 `PRF` 를 한 번도 쓰지 않는다. SSB 축의 1차
  출처는 Abratkiewicz(IEEE JSTARS 2023, 게재), CSI-RS 축은 Chen(Appl. Sci. 2024, 게재).

### P02 · HIGH — Abratkiewicz PDF 는 이제 우리 손에 있다
- **대상**: `reference_library.json:master_table[abratkiewicz_ssb_jstars23].status` ("2차 출처 서지; PDF 미확보"),
  `reflib_sweep_geometry.json:actions_ranked[1]` ("확보 전까지 우리 novelty 문장 확정 불가")
- **현황**: 16쪽 진본 확보·정독 완료. 이 논문으로 게재 근거 네 개가 열린다 —
  ① 무모호속도 우선권(p.8), ② "The SSB is the only always-ON signal in the 5G network."(p.1),
  ③ 콘텐츠 유무에 따른 SNR 차 4.23 dB(p.10), ④ SSB 기본 주기 20 ms(p.3).
- ⚠ 같은 폴더의 `abrat2023.pdf` 는 **여전히 IEEE Xplore 오류 페이지 2쪽**이다. 경로를 정확히 구분할 것.

### P03 · HIGH — Chen PDF 도 확보, 경로 갱신
- 옛 경로 `.../g1g2/chen2024_s2.pdf` 는 오늘 존재하지 않는다. 현재는 `chen2024_applsci_14_4282.pdf`(20쪽).
- `band_note: "3.55 GHz"` 는 "실험 3.55 GHz / §4.1.3 시뮬레이션 3.45 GHz" 로 분리해 적을 것.

### P04 · HIGH — C1 문구가 지금 그대로면 반증당한다
- **대상**: C1 이 인쇄되는 모든 곳 + `reflib_sweep_sionna.json` 의 `target_representation='none stated'` 항목들.
- **반례 넷**(전부 산란적분은 없지만 메시는 있다):
  - **CAVIAR** (Borges 외, Ericsson Research/UFPA, **arXiv:2401.03310, 프리프린트**) — 드론 객체가 Sionna
    장면 안에 **ITU metal** 재질로 존재한다(표 V, p.9). 단 감지 대상이 아니라 수신기다.
  - **Cazzella 외** (Politecnico di Milano/Huawei Italia, **arXiv:2507.19173, 프리프린트**, 31쪽) —
    CARLA 차량 메시 3종을 Sionna RT v0.18.0 장면에 넣고 창문 부품을 손으로 분리해 부품별 재질을 준다.
  - **VaN3Twin** (Pegurri 외, **arXiv:2505.14184, 프리프린트**) — Sionna RT v1.2.0, 차량 메시를
    차체·전조등·창·휠림으로 분할해 재질 배정.
  - **AirGuard** (Luo 외, **IEEE JSAC accepted**, arXiv:2603.13112) — DJI Mavic 3/Mini 2/Avata/Inspire 2/
    Ehang eVTOL 의 실제 `.obj` 메시를 불러온다.
- **고친 말**: *"우리가 보유·정독한 문헌 중, 드론 기체의 3-D 표면 메시를 **산란적분에 통과시켜 그
  진폭을 보고한** 논문은 0편이다. 장면에 드론·차량 메시를 넣고 재질까지 배정한 선행은 여럿 있으나,
  그 메시가 하는 일은 전파 상호작용이지 표적 산란단면적 산출이 아니다."*

### P05 · HIGH — "스톡 Sionna 에는 회절이 없다" 는 우리 쪽 문장이 틀렸다
> "While [36] deals with diffraction at edges of perfectly conducting surfaces, it was heuristically
> extended to finitely conducting wedges in [37]. This solution, which is also recomended by the ITU
> [38], is implemented in Sionna."
> — Sionna RT: Technical Report v1.2, **arXiv:2504.21719v2, 2025, 프리프린트/벤더 기술문서**, p.47

그리고 우리 설치본에서 직접 확인했다 — `sionna 2.0.1`, `PathSolver.__call__`:
`diffraction: bool = False`, `edge_diffraction: bool = False`, `diffraction_lit_region: bool = True`.

- **정확한 문장**: 스톡 Sionna RT 에 없는 것은 **표적 산란적분(PO 표면적분·RCS 출력)**이지 회절이 아니다.
  "1차 UTD wedge 회절만 있고 정점·2차·slope·creeping·PTD 는 없으며, 표적 RCS 출력이 없다."
- ⭐⭐ **이건 문헌 정정이 아니라 우리 실험 정정 후보다.** 우리 RT 실행이 PathSolver 를 기본값으로
  돌렸다면 회절이 전부 꺼진 상태였다. report07/09 의 RT 결과 해석 전에 플래그 이력을 감사할 것.

### 나머지 16건 (요약)
| ID | 내용 |
|---|---|
| P06 | Ziganshin "저널판" 은 게재본이 아니라 **IEEE OJAP 투고 프리프린트**(arXiv:2604.05991v2). ⭐ 두 판본이 패싯 크기 조건에서 **반대로** 말하고, 실측 검증(BIRA)은 미게재판에만 있다 |
| P07 | `gap_statement.what_is_genuinely_ours_ko` ② — "축의 구별" 도 우리 것이 아니다(Abratkiewicz 2023 이 이미 기준반복축·반폭). 남는 것은 **대조표** |
| P08 | hover blind 는 우리 발견이 아니다 — Milani(Remote Sens. 13(18):3556, **2021 게재**), Sun(IEEE OJ-COMS **2025 게재**), Taylor(IEEE TAES 61(4) **2025 게재**) |
| P09 | 10log10(N) 이상 상한도 게재 선례가 있다 — Taylor p.11 |
| P10 | 기계 센서스 3건 정정 — 2503.12177 자리표시자 DOI(프리프린트), 2504.09849 Sionna 미사용(Wireless InSite), 2507.08716 Sionna 재구현 |
| P11 | UTD 카운트 오염 — 단어경계 없이 세면 `o-UTD-oor` 가 잡힌다 |
| P12 | ⛔ **규약 2배 주장(Wei TVT / I-SCOUT)은 지금 쓰면 안 된다** — 두 PDF 다 아카이브에 없다. 우리 오류기록 "+8~16 dB" 와 같은 형태 |
| P13 | ΔR_b = c/B 에 "바이스태틱 이등분선 방향" 한정어가 필요하다(Costa p.3, Sun 식 76 은 c/(2B cos(β/2))) |
| P14 | wave_01 rank 3/4 는 같은 논문(Sun 프리프린트 ↔ OJ-COMS 게재판). ⭐ 게재판에만 있는 "반경 25 cm 강철 구" 가 결과를 좌우한다 |
| P15 | ⛔ Kirik 2019 의 "헬리콥터 PTD 결과" 는 논문에 없다(초록만 약속) |
| P16 | zhang_unified_rcs 는 모순이 아니라 객체 구별(arXiv 파일 vs 게재판) |
| P17 | ⚠ Yuan **EuCAP 2025 는 보유**, Yuan **AWPL 2024 는 미보유** — 별개 논문 |
| P18 | "20 ms 축에서 33.6 RPM" 은 반경 r=0.3 m 에 묶인 값이다. r=0.12 m 면 84 RPM (우리 산술) |
| P19 | five_gaps ② 에 범위 한정어 필요 |
| P20 | `who_is_silent` 6항목 등급을 term-count → 정독으로 상향 |
| P21 | POFACETS 는 논문이 아니라 도구 문서로 인용 |

---

## 3. 주장 판정

### H8 — **SURVIVES** (네 프롱 문자 그대로일 때만)
51편 어디에도 네 프롱을 동시에 만족하는 논문이 없다. 그러나 **최근접이 갱신됐다.**

| 논문 | 통과한 프롱 | 걸린 프롱 |
|---|---|---|
| **AirGuard** (IEEE JSAC **accepted**, arXiv:2603.13112) | 게재 · **실제 드론 표면 메시** | 엔진 내부 계산 ✘ (MeshLab 로 점구름 환원 후 등방 점산란 위상합) · 진폭검증 ✘ (CNN 분류정확도) |
| **Costa 외** (IEEE JSTEAP 1, **2025 게재**) | 게재 · 드론 · 시그니처 검증 | 표면 메시 ✘ (thin-wire) · 광선엔진 ✘ |
| **Ziganshin 외** (EuCAP **2025 게재** / arXiv:2604.05991v2 **프리프린트**) | 엔진 내부 · 진폭검증 · 게재(회의판) | 표적이 승용차 ✘ · 실측 검증판은 미게재 ✘ |
| **Clutter-Aware ISAC** (Proc. IEEE 114(1), **게재**) | 게재 · 드론 메시 · 엔진 내부 | 진폭검증 ✘ (41쪽에 `validat` 0회) |
| **Deep 외** (arXiv:1910.13706v1, **2019 프리프린트**) | 표면 폴리메시(3052 삼각형) · 자체 SBR 내부 · 실측 SSIM 0.81~0.99 | 게재 미확인 ✘ · **표적이 보행자** ✘ · Sionna 급 GPU 엔진 ✘ |

⭐ 맨 아래 줄이 중요하다. **"드론" 과 "Sionna 급 GPU 엔진" 두 한정어가 실제로 일을 하고 있다.**
그 둘을 빼면 H8 은 즉시 무너진다.

**H8 을 지지하는 새 인용 자산 셋**
- 표준화 진영이 왜 아무도 안 하는지를 직접 인쇄한다:
  > "However, as for the typical STs such as Unmanned Aerial Vehicles (UAVs), humans, and vehicles,
  > the high computational complexity of electromagnetic simulations limits their applicability in
  > standardized models…"
  > — Liu 외, 3GPP Rel-19 ISAC 채널모델링 서베이, **arXiv:2512.03506v1, 2025, 프리프린트**, p.2
- 선행 저자 본인이 드론 적용을 향후과제로 적는다(게재본):
  > "The proposed solution can also be applied to compute scattering from other objects, such as
  > drones, humans, and micro-Doppler effects, making it an important area for further investigation."
  > — Ziganshin 외, **EuCAP 2025, 게재**, p.5 *(내가 오늘 재대조)*
- 2026년 저고도 UAV 감시 ISAC 서베이(**arXiv:2604.02680, 프리프린트**, 24쪽)가
  Sionna 0회 · 레이트레이싱 0회 · 회절 0회 · PO 0회 · SBR 0회.

### C1 — **NARROWED** (§2 P04 참조)

### C2 — **SURVIVES, 강화됨**
오늘 두 파일을 직접 계수했다 — EuCAP 게재본 `dBsm = 1`(p.5 "RCS (dBsm)" 축 + "RCS of the simplified car"),
같은 저자 저널 프리프린트 `dBsm = 0`(|E_sc| dB 만 씀).
⚠ 다만 **Sagitta SBR**(arXiv:2604.09243, ICCS 2026 accepted 확장판)은 dBsm 을 찍는다 — 자작 GPU SBR 이다.
"GPU 광선엔진이 dBsm 을 찍은 최초" 라고 쓰면 반증당한다. **"Sionna" 한정을 유지할 것.**

### C3 — **NARROWED**
아카이브 227편 전문에서 `ssb-PeriodicityServingCell` 는 **0회**다. 반증할 문서도 지지할 문서도 없다.
그러나 "배치 주기 + 센싱 귀결" 이라는 **논증 형태**에는 이미 게재 선례가 있다:

- **Chen 외**(Appl. Sci. 14(10):4282, **2024 게재**) — 상용 5G 기지국의 CSI-RS 주기(Period **40 slots**
  = 20 ms)를 표 5 에 인쇄하고(p.16), 같은 논문에서 그 귀결을 보고한다:
  > "the reason for the error of 100% is that the Doppler frequency exceeds the measurement range,
  > resulting in Doppler blur." (p.16)
- **Abratkiewicz 외**(IEEE JSTARS 16, **2023 게재**) — SSB 주기 후보 {5,10,20,40,80,160} ms 와
  "기본이자 가장 흔한 값은 20 ms" (p.3). ⚠ **저자 단언이지 배치 분포 측정치가 아니고 근거 인용도 없다.**
- **LaSen**(ACM/IEEE SenSys **2026 게재**) — 실측 N41 gNB 의 CSI-RS 실효 200 Hz(p.11), sub-6 상한 500 Hz(p.1).

→ **세 한정어(ssb-PeriodicityServingCell · deployed DISTRIBUTION · sensing consequence)를 전부 유지**하고,
"이 아카이브만으로는 지지도 반증도 못 한다" 를 문장에 남긴다.

### C4 — **NARROWED** (가장 위험)
전체 무게가 **"multi-illuminator(조명원 종류가 여럿)"** 한정어 하나에 실려 있다.

**최근접 선례 — Taylor & Poullin, IEEE TAES 61(4), August 2025, pp.8804-, 게재**
표적 1(DJI Phantom 3) · 검출기 1(네 방향 중 최소를 취하는 lowest-of CA-CFAR) · **교정된 오경보율**
(13 dB 문턱 ↔ Pfa = 10⁻⁶) 아래에서 경쟁하는 신호자원을 통제 비교했다.

> "The highest SNR is obtained by using all the symbols (24.2 dB), followed by a configuration using
> symbols containing the CRS (17.5 and 17.9 dB). However, the configuration using all the symbols also
> shows the highest number of plots, and thus of false alarms (only one plot corresponds to the
> target). This number is roughly three times higher than when using symbols containing the CRS." (p.11)
> *(내가 오늘 재대조)*

결과 방향까지 우리 "점유 대가" 서사와 같고 더 강하다. **C4 가 사는 이유는 하나뿐** — 비교 대상이
서로 다른 조명원이 아니라 한 LTE 하향 신호 *안*의 심볼 부분집합이고 기하도 하나다.

**고친 말**: *"한 표적·한 검출기·경험적으로 교정된 오경보율 아래에서 **서로 다른 조명원 종류**
(WiFi / LTE / 5G)를 통제 비교한 연구는 없다. 같은 방법론을 한 조명원 안의 자원 선택에 적용한 게재
선행은 있다(Taylor & Poullin, IEEE TAES 61(4), 2025) — 우리 벤치마크 설계의 선행 방법론으로 반드시
인용해야 한다."*

**공백을 확인해 주는 게재 논문 넷** — Lin 외(IEEE/CIC ICCC 2023, 게재, CFAR 0회·평가는 분류정확도),
Filippini 외(IEEE Xplore 게재, CFAR 0회·육안 궤적 식별), Maksymiuk 외(IRS 2023, 게재, 조명원 하나),
Geng 외(IET RSN 14(7), 2020, 게재, `CFAR`/`false alarm` 전문 0회).

---

## 4. ⭐ 회절 — 문헌이 실제로 하는 일, 그리고 우리가 쓸 수 있는 것

### 4.1 결론부터
> **우리가 지금 확실히 가진 것은 "인용할 수 있는 알려진 한계" 이지 "구현하면 대역기울기 문제가
> 낫는다" 가 아니다.** 두 번째를 주장할 근거는 이번 라운드에서 만들어지지 않았고, 오히려 **반대
> 방향 증거가 하나 나왔다.**

### 4.2 문헌의 여섯 갈래

| 갈래 | 편수 | 대표 |
|---|---|---|
| **PTD 를 실제로 구현** | 2 | Öztürk (MSc thesis, Bilkent Univ., **2002, 학위논문·미게재**) · Kırık & Özdemir (Sigma J. Eng. Nat. Sci. 37(4):1153-1166, **2019 게재**) |
| **UTD 를 실제로 구현** | 3 | Ziganshin (EuCAP **2025 게재**) · Ziganshin (arXiv:2604.05991v2, **2026 프리프린트**) · Sionna RT 본체 |
| **값싼 폐형식(KED)으로 우회** | 1 | Liu 외 (arXiv:2506.00480v1, **2025 프리프린트**) |
| **명시적으로 포기하고 그 사실을 적음** | 4 | Costa (IEEE JSTEAP **2025 게재**) · Sagitta SBR (arXiv:2604.09243, ICCS 2026 accepted) · Audia (arXiv:2511.07586, IEEE 투고중) · POFACETS 매뉴얼(비논문) |
| **"계산" 이 아니라 "해석 어휘" 로만 사용** | 3 | Ezuma ×2 (**프리프린트**) · Zhang 통합 RCS |
| **국제표준: 회절 칸 자체가 없음** | 1 | 3GPP TR 38.901 V19.0.0 (**2025-06 공식 발간**) |

⭐ **PTD 를 구현한 최신 문서가 7년 전(2019)이다.** 2026년 KTH GPU SBR, 2026년 Monte-Carlo SBR,
3GPP Rel-19 표준 RCS 모델, Sionna RT 재구현(Great-X)이 **전부 회절 없이** 나온다.
**우리 커널에 PTD 가 없는 것은 뒤처진 것이 아니라 이 분야의 기본값이다.**

### 4.3 우리 메시 규모에서는 UTD 노선이 막힌다

두 논문의 축자 요구조건이 **정반대**다.

| 쪽 | 요구 | 3.5 GHz 환산 |
|---|---|---|
| UTD 하한 — "the facet size should be of several wavelengths in order to satisfy the UTD assumptions, typically **E > 1.5λ**" (Ziganshin arXiv:2604.05991v2, 프리프린트, p.4) | 패싯이 **커야** | 1.5λ ≈ **12.9 cm** — Mavic 4 Pro 급 전장의 절반 수준. 패싯 하나가 드론만 해져야 한다 |
| PO 상한 — "area of each triangle is restricted to be smaller than **0.005λ²**" (Öztürk 2002, 학위논문, p.3) | 삼각형이 **작아야** | 변 ≈ λ/9.3 ≈ **9 mm** |

→ **λ 이하 부재가 지배하는 드론에는 UTD 가 아니라 PTD-EEC 를 붙여야 한다.**
⚠ 이 결론은 두 논문의 문장을 나란히 놓아 **우리가 도출한 것**이고, 어느 논문도 직접 쓰지 않았다.
보강 수치: 패싯 ~1λ 급에서도 UTD+정점회절이 **5 dB 오프셋**을 남긴다(Ziganshin EuCAP 2025, 게재).

### 4.4 우리 표적이 어디에 있는가 — 두 문턱과 우리 값

| 출처 | 문턱 | 우리 |
|---|---|---|
| Sagitta SBR (arXiv:2604.09243, 2026) p.8 — "good agreement typically expected for kr ≳ 30" | **kr ≥ 30** (광선법 신뢰) | 3.5 GHz, 동체 r=0.10 m → **kr ≈ 7.3** |
| Lindgren (MSc thesis, Umeå Univ., 2021, 학위논문) | **kr > 10** (creeping wave 무시 가능) | 같은 값 → **못 넘는다** |

우리 표적은 광선법이 "잘 맞는다" 고 말하는 영역의 **1/4 지점**에 있고, creeping wave 를 무시할 수
있는 문턱조차 넘지 못한다. 기존 판단("few-λ marginal")이 문헌 수치로 뒷받침된다.

### 4.5 CITE 는 있고 IMPLEMENT 는 없다

**우리가 지금 인용할 수 있는 것 (CITE)**
- "회절 없음" 이 2025-2026 최신 SBR 계열의 공통 상태라는 근거 4건
- 국제표준의 소형 UAV 모델에도 회절·형상·각도가 없다는 근거
  (10lg σ_M = **−12.81 dBsm**, σ_D = 0 dB, 로그정규 σ_S = 3.74 dB, 바이스태틱은 −3·sin(β/2) 한 줄,
  전방산란 σ_FS = −∞)
- 스톡 Sionna 의 회절 범위(1차 UTD wedge)를 확정하는 공식 문장 + 우리 설치본 소스
- 회절을 끄면 반사깊이로 못 메우는 RMSE 바닥이 생긴다는 Sionna RT 안의 정량 예시
  (AIRMAP, arXiv:2511.05522, Sionna RT 1.2.1 — 회절 ON + 깊이 14 가 최적, 라디오맵당 0.265 s)

**우리가 쓸 수 없는 것 (IMPLEMENT)**
- ⛔ "PTD 를 넣으면 우리 대역기울기가 개선된다" — **부호 미정, 반대 증거 있음**
- ⛔ "PTD 가 소형 드론 RCS 를 몇 dB 올린다" — Kirik 2019 는 정량 지표가 하나도 없다
- ⛔ "UTD 확장이 우리 메시에서 작동한다" — E > 1.5λ 가 막는다

**반대 증거** — 웨이브 3 이 같은 라운드 안에서 자기 추론을 하향했다.
Kirik 그림 8(b)를 보고 "PTD 는 저주파를 더 올려 기울기를 완만하게 만든다" 고 적었으나:
> "This is because the very small wavelength (λ = 1.2 cm) of the 25 GHz radar **enhances** the effects
> of diffraction and scattering by sharp edges and corners on the drones."
> — Ezuma 외, **arXiv:1911.05926, 2019, 프리프린트**, p.4

드론에서는 **고주파일수록 엣지 효과가 커진다**는 정반대 해석이다. 부호는 실제로 붙여 보기 전까지
UNVERIFIED 다.

**부호를 확정할 최소 실험** — 드론 메시 한 기종에 대해 1.8 / 3.5 / 5.2 GHz 세 점에서
PO 단독 vs PO+PTD-EEC 를 돌려 **기울기 변화의 부호만** 본다.
⚠ 그 전에 우리 메시 밀도가 0.005λ²(3.5 GHz 에서 변 ≈ 9 mm) 조건을 만족하는지 감사해야 한다 —
만족하지 않으면 PTD 이전에 **PO 자체가 틀린다.**

### 4.6 그래도 지금 붙일 수 있는 것 하나 — KED
표적이 만드는 차폐/전방산란은 PTD 없이도 넣을 수 있다.

> "Ae1,n,m[dB] = −20 log₁₀ (1 − (Fh1 + Fh2)(Fw1 + Fw2))  (11)"
> — Liu 외, **arXiv:2506.00480v1, 2025, 프리프린트**, p.8 (105 GHz 실내공장 실측으로 검증)

프레넬 항 네 개만 계산하면 된다.
⚠ KED 는 표적을 **완전흡수 얇은 판**으로 가정하므로 재질이 사라진다 — 우리 재질 가중 PO 와 물리적으로
상충한다. **차폐 항으로만 쓰고 산란 항에 섞지 말 것.**

### 4.7 구현 레시피는 이미 손에 있다
- **식**: Öztürk 2002 (바이스태틱 3.23-3.28, 백스캐터 특이점 제거형 3.35-3.38, 합성 3.42)
- **절차**: Kırık & Özdemir 2019, **게재** (엣지 검출 = 공통 정점 2개 이상 인접 삼각형 · 광선-엣지
  게이팅 d_max = λ/10 · 등가 엣지길이 dl ∝ 광선밀도 · Griesser-Balanis IEEE TAP 1987 계수식 · PO 성분 차감)
- **우리가 새로 만들 것은 셋뿐** — (a) 엣지 인접 삼각형 테이블, (b) 히트점-엣지 수직거리 d_hit,
  (c) 회절계수. 파이프라인 구조(transport → accumulation)는 바뀌지 않는다.
- **남는 구멍**: 2차 엣지-엣지 회절 · 코너/정점 회절 · 스침입사 특이점 · creeping wave
- **참조 구현(⚠ 접속·라이선스 미확인)**: `github.com/AinurZiga/sionna-RT-reflectivity`,
  `github.com/marco-pas/SagittaSBR`

---

## 5. 능력매트릭스 — 이번에 읽은 논문의 행

`outputs/capability_matrix.json` 의 9열 규약(engine / mesh / material / aspect / rotor / diffraction /
validation / geometry / vmax), 4단 마크(FULL/PARTIAL/NONE/NOT_APPLICABLE), 4등급(QUOTED/COMPUTED/
DERIVED/UNVERIFIED)을 그대로 따라 **33행**을 만들었다 —
`deepread_reconcile.json : capability_matrix_rows_proposed.rows`.
신규 30행, 기존 행 갱신 3행(kirik / caviar / greatx).

**군별**: S(산란 계산) 7 · T(장면 안 표적, 산란적분 없음) 9 · M(실측 앵커) 5 · V(무모호 속도) 3 ·
**P(교정 오경보율 검출) 6** · **E(엔진·도구 참조) 3**

⭐ **새 군 두 개를 제안한다** — 기존 5군(S/T/M/V/O)에 C4 축(교정된 오경보율에서의 검출)과 엔진 명세를
담을 칸이 없었다. P·E 를 추가하면 Taylor·Milani·Maksymiuk·Lin·Filippini·Sun 여섯 행과 Sionna RT
기술보고서가 제자리를 찾는다. *(채택 여부는 `capability_matrix.py` 소유 워크플로가 정한다.)*

**⚠⚠ 이 행들을 그대로 병합하면 안 된다 — 근거 등급을 먼저 보라.**

| | 칸 수 |
|---|---|
| 전체 | 278 |
| **근거가 선 칸** | **94** (QUOTED 72 + COMPUTED 12 + DERIVED 10) |
| **UNVERIFIED** | **184 (66%)** |

기존 `capability_matrix.json` 은 `unverified_fraction = 0.0` 이다 — **근거를 세울 수 있는 칸만 썼기
때문이다.** 나는 반대로 "무엇을 아직 모르는가" 까지 칸에 남겼다. 소유 워크플로는 둘 중 하나를 골라야
한다: **(a)** UNVERIFIED 칸의 근거를 원문에서 세우거나, **(b)** 그 칸을 비우고 행만 받는다.
지금 상태로 병합하면 그 파일의 불변식이 깨진다.

각 칸에 `provenance` 를 붙였다 — `reverified_today`(내가 오늘 PDF 직접 재대조, 2칸) /
`this_agent_computed`(내가 오늘 전문 계수, 3칸) / `wave_record`(웨이브 인용문 승계, 79칸) /
`wave_record_label_only`(웨이브의 판정만 있고 인용문 없음, 184칸) / `derived_in_this_file`(10칸).
**`wave_record` 인 칸은 2차 승계다** — 표본 11건에서 11/11 일치를 확인했지만 개별 칸의 재대조는
아니다. 발표 전 해당 칸만 다시 열 것.

**이 열이 채워지면서 드러난 것**
- 기존 매트릭스 26행 중 회절 FULL 은 3행뿐이었다. 51편을 더해도 Öztürk · Liu(KED) · AIRMAP ·
  Ropitault · Sionna RT 본체 정도가 추가될 뿐이다.
- 실측 앵커 행이 크게 늘었다 — Ezuma 6기종 × 2대역 × 2편파 절대 RCS 표(25 GHz VV: M600 Pro −7.32,
  M100 −11.03, zx5 −9.64, **Mavic Pro 1 −16.20**, Inspire 1 −11.09, P4 Pro −12.40 dBsm)는
  `rcs_anchor.json` 확장 후보다. Mavic Pro 1 이 6대 중 최소이며 우리 주력 표적의 세대 선조다.
- ⚠ Ezuma 요동분포 AIC 는 레일리를 6전6패로 기각하고 GEV/로그정규를 택했으나 **후보군에 지수분포
  (Swerling-1)가 없었다** — Swerling-1 반증으로 쓸 수 없다.

---

## 6. 남은 백로그 — 다음 라운드는 여기서 시작한다

### 6.1 정직한 숫자

| | |
|---|---|
| 아카이브 고유 문서 | **228** (파일 경로 282, dedup 227 + 신규 확보 1) |
| 이번 라운드 전 정독 | 68 |
| **이번 라운드 후 정독** | **109 (47.8%)** |
| ⚠ 그중 특정 절만 표적 정독 | 약 11편 (나머지 칸은 UNVERIFIED) |
| 여전히 **기계 센서스만** | **96** |
| — Sionna 센서스 한정 | 110 중 12 읽음, **98 남음** |
| 회절 용어 문서 중 미개봉 | **58** (76 중 18 개봉) |
| `reflib_sweep_venues.json` 인용문 없는 행 | **73 / 81** ⭐ |

### 6.2 티어

- **T1 · 점수 매겨진 큐 마무리 (19편)** — 트리아지가 점수 1 이상으로 올린 49편 중 30편만 읽었다.
  ⭐ **두 편을 상향한다**: `2507.12235__frequency-responsive-rcs-scaling_GLOBECOM-WS2024.pdf`
  (제목이 곧 우리 대역기울기 문제다 — 점수 1로 매겨진 것이 잘못이다) ·
  `2505.24763__detecting-airborne-objects-5gnr-radars.pdf`(5G NR PRS 모노스태틱 UAV 미검출률 곡선 =
  우리 검출 벤치마크의 직접 대조군). ⚠ 두 편은 중복 확인부터: `2112.09774`(제1저자는 Semkin 이 아니라
  Ezuma — 기존 `semkin_drone_rcs_access20` 행과 같은 논문인지) · `Modelling_...Propellers.pdf`
  (2401.14287 의 사본일 가능성).
- **T2 · Sionna 기계 센서스 98편** — 읽은 12편에서 **CORRECTED 가 6건**이었다. 오탐률이 절반이면
  나머지 98편의 센서스 값을 발표에 쓸 수 없다.
  ⭐ **정독보다 얕은 패스가 급하다** — "Sionna 를 실제로 돌린 문장이 있는가" 한 문장 확인(편당 2-3분)을
  98편 전체에 먼저 돌리고, `target_representation` 이 바뀌는 것만 정독한다.
- **T3 · 회절 용어 문서 58편** — 대부분 상투구일 것이나 확인하지 않았다. 편당 5분 표적 확인.
- **T4 · venue sweep 인용 공백 73행** ⭐ — **우리 최대 미검증 표면**. "PUBLISHED (per dblp record)"
  28행은 전부 2차 출처 판정이고 PDF 경로가 있는 것은 41행뿐이다. 우리 오류기록의 "아카이브에 없는
  PDF 에 수치 귀속" 이 재발할 가장 큰 표면. **정독보다 먼저 "리포트·덱에서 실제로 인용하는 항목" 을
  역추적**해(아마 10-15행) 그 문장만 원문 확인한다.
- **T5 · 강등된 꼬리 107편** — 이번에 그중 3편을 읽었고 **두 편은 회절 칸에서 TAIL 이 아니었다**
  (AIRMAP, Ropitault). ⭐ 점수 체계가 "우리 주장 축" 만 봤기 때문이다. 다음 트리아지에는
  **회절 · 검증방법 · 규약** 세 축을 점수에 넣을 것.

### 6.3 몇 라운드 남았나
- **우리 주장에 닿는 것을 전부 끝내는 데 약 1 라운드** (T1 19편 + T2 얕은 패스 + T4 역추적).
  5 에이전트 병렬이면 한 번에 끝난다.
- **224편 전편 정독까지 2-3 라운드 더** (미정독 119편, 라운드당 ~50편).
- ⭐⭐ **그러나 남은 위험의 대부분은 아카이브 "안" 이 아니라 "밖" 에 있다.** C3 는 아카이브 227편
  전문에서 `ssb-PeriodicityServingCell` 0회라 지지도 반증도 못 하고, 규약 2배 주장은 보유하지 않은
  두 PDF 에 걸려 있으며, 회절 × 회전블레이드 × 바이스태틱의 유일한 선행도 미보유다.
  **라운드를 더 도는 것보다 아래 확보가 값지다.**

---

## 7. 확보 목록 (순위)

| # | 문헌 | 왜 |
|---|---|---|
| 1 | Pouliguen, Lucas, Muller, Quete, Terret, IEEE Trans. Antennas Propag. **50(10), 2002, 게재** (doi 10.1109/TAP.2002.800693) | ⭐⭐ 회절(등가전류 MEC) × 회전 블레이드 × 바이스태틱이 한 논문에서 만나는 **유일한** 선행. Costa(JSTEAP 2025, 게재)가 "회전 프로펠러 모델 중 바이스태틱을 다룬 것은 [12]와 [22]뿐" 이라고 단언한다 |
| 2 | T. Li, B. Wen, Y. Tian, S. Wang, Y. Yin, IEEE Access **7:101527-101538, 2019, 게재** | 회전 블레이드 RCS 를 적분모델+MoM 으로 유도하고 탄소섬유 계수를 실험 검증. 우리 로터 RCS 앵커 직결 |
| 3 | Wei 외, IEEE TVT **72(3):3250-3263, 2022, 게재** (arXiv:2211.11488) · Demir 외 "I-SCOUT", **IEEE MILCOM 2024, 게재** (arXiv:2410.08999) | ⭐ 우리 "규약 2배" 주장의 **유일한 근거인데 둘 다 아카이브에 없다**. 확보 전까지 그 주장 사용 금지 |
| 4 | Yuan, Yu, Wang, Li, Dallmann, Fan, **IEEE AWPL 2024, 게재** | 절대 σ 앵커. ⚠ 우리가 보유한 Yuan **EuCAP 2025**(게재, DOI 10.23919/EuCAP63536.2025.10999912)와 **별개 논문** — 게재처를 명시해 중복 확보를 막을 것 |
| 5 | F. Weinmann, IEEE TAP **54(6):1797-1806, 2006, 게재** | PO/PTD 를 광선추적에 넣는 표준 참조. Kirik 의 λ/10 게이팅 규칙 출처 |
| 6 | Ufimtsev IEEE TAP 54(10), 2006 · Hansen IEEE TAP 39(7), 1991 · Breinbjerg IEEE TAP · Albani IEEE TAP 57(12), 2009 (모두 **게재**) | PTD-EEC 구현 시 바로 부딪히는 네 구멍의 원전. **구현을 결정한 뒤** 확보해도 늦지 않다 |
| 7 | Wypich & Zielinski, Sensors **26(4):1317, 2026, 게재**(오픈액세스, DOI 10.3390/s26041317) | ⭐ 우리 "패시브는 상시 기준신호만 쓴다" 조건절이 이 논문 하나에 걸려 있는데 규약·슬로타임 정의를 원문 확인 못 했다 |
| 8 | 공개 데이터셋 `github.com/yfsun0327/LIPASE-dataset` (Sun 외 IEEE OJ-COMS 2025 **게재판에만** 링크) | 실측 패시브 LTE-드론 데이터. 우리 CAF 파이프라인을 남의 실측으로 검증할 기회. 논문이 아니라 확보 난이도가 낮다 |
| 9 | 3GPP TS 38.331 (`ssb-PeriodicityServingCell`, `CSI-ResourcePeriodicityAndOffset`), TS 38.211/213/214 | ⭐ **C3 의 유일한 진짜 해답 경로.** 그리고 "sub-6 CSI-RS 500 Hz 천장" 은 현재 LaSen(SenSys 2026, 게재) p.1 을 통한 **2차 인용** 상태다. 규격 원문은 무료 공개다 |

---

## 8. 방법 경고 (다음 웨이브가 반복하지 말 것)

1. ⭐ **grep 금지.** PDF 추출 텍스트에 NUL 바이트가 있으면 GNU grep 이 바이너리로 판정하고 침묵한다 —
   존재하는 용어가 0회로 보인다(arXiv:2412.20788 이 그랬다). 용어 집계는 **파이썬 `re` 로만**.
2. ⭐ `UTD`/`GTD`/`PTD` 는 **반드시 `\b` 단어경계**로. `o-UTD-oor` 가 잡힌다.
3. ⭐ `ambiguity` 로 도플러 모호 논문을 고르면 **최소 여섯 가지** 다른 현상이 섞인다
   (모호함수 / CFO 무모호구간 / 진폭전용 처리의 부호 모호 / 거리 모호 / AF 사이드로브 / 클러터-표적 구분불가).
4. ⭐ `ISAC`·`sensing` 빈도로 표적 유무를 추정하지 말 것 — arXiv:2604.19599 는 `sensing` 55회인데
   산란·에코·RCS 0회다.
5. ⭐ **아카이브 폴더 이름으로 엔진을 추정하지 말 것** — arXiv:2312.03950 은
   `sionna_papers_by_task/` 안에 있으면서 `Sionna` 0회다.
6. ⭐ **DOI 가 PDF 에 있다고 게재가 아니다** — IEEE Access 템플릿 자리표시자
   (`...ACCESS.2023.1120000` + "Date of publication xxxx 00, 0000")를 함께 본다.
7. ⭐ `Sionna` 가 나오는 문장이 **사용인지 언급/비교/대안소개인지** 판정 전에 `sionna_used` 를 세우지 말 것.
8. ⭐ **프리프린트판과 게재판을 두 편으로 세지 말 것.** 그리고 판본 차이가 결과를 바꾼다 —
   Sun 은 게재판에만 표적 치수(반경 25 cm 강철 구 = 우리 계산 −7.1 dBsm)가 있고, Ziganshin 은 두
   판본이 패싯 크기 조건에서 **반대로** 말한다.
9. ⭐ 스크래치패드를 병행 워크플로와 **공유한다** — 고유 파일명을 쓸 것(웨이브 1 의 `extract.py` 가
   실행 도중 덮어써졌다).
10. ⭐ 아카이브 경로가 세션 중에 바뀐다(`chen2024_s2.pdf` → `chen2024_applsci_14_4282.pdf`).
    인용에 **경로 + 쪽수 + 축자 인용문**을 함께 남겨야 경로가 죽어도 복구된다.
11. ⭐ **그림·표 값은 텍스트 추출로 못 읽는다** — Taylor 표 I~IV, Sun 표 2(CFAR α), AirGuard 그림 8,
    Geo2SigMap 의 Sionna 단독 RMSE 가 전부 그 상태다. UNVERIFIED 로 남긴다.
12. ⭐ **눈금 읽기를 저자 숫자로 옮기지 말 것** — Öztürk Fig.3.10 판독(+2~3 dB)과 AIRMAP Fig.6
    판독(RMSE 바닥 ~7.5)은 우리 판독이지 논문 값이 아니다.
