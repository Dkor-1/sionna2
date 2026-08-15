> ⚠ **2026-08-16 재편 전 번호 체계의 기록이다** — 옛 권 번호(평면 01~18)로 적혀 있다. 옛→새 환산은 [`RESTRUCT_PLAN.md`](RESTRUCT_PLAN.md) §1 표, 현행 편성은 [`REPORTS_VOLUMES.md`](REPORTS_VOLUMES.md).

# 재개 지점 — 2026-07-31 06:20

사용자 지시로 **새 작업 착수 없이** 진행 중인 것만 마무리하는 상태. 이 문서만 읽으면 이어받을 수 있다.

---

## 1. ⭐⭐ 가장 중요 — 헤드라인이 좁아졌다 (반증 시도 결과)

`outputs/vmax_hardening.json` 이 8갈래 반증(A~H)을 돌린 결과: **`survives: true`**, 단
**"무모호 속도(unambiguous velocity)에 대한 진술이지 검출(detection)에 대한 진술이 아니다"**.

내가 사용자에게 **너무 세게 말한 것 4건**을 정정해야 한다:

| id | 내가 한 말 | 실제 |
|---|---|---|
| **X4** ⭐ | "WiFi 14.4 m/s (PRF 1000 Hz)" | **1000 Hz 는 트래픽 가정이다.** 규격 보장 상시신호는 **비콘 9.77 Hz** → WiFi v_max = **0.140 m/s 로 5G(1.07)보다 나쁘다.** 교차 패킷률 74.4 Hz |
| **X2** | "CPI 로 못 고친다" | **검출 블라인드는 CPI 로 고쳐진다**(0.636@0.1 s → 0.053@1 s). 못 고치는 건 **무모호 속도뿐**. 두 양을 분리해 써야 한다 |
| **X3** | "모든 드론이 접힌다" | **접힘 ≠ 미검출.** 접힌 표적도 *틀린 도플러 셀*에서 검출된다. 잃는 건 그 셀이 0-도플러 가드에 떨어질 때뿐이고 확률은 `2g/M` |
| **X5** | "CPI 로 절대 못 고친다" (멀티스태틱 함의) | **넓게 벌린 다중 수신기는 속도 모호를 실제로 푼다.** 참인 문장은 **"수신기 한 대로는 못 푼다"** |
| X1 | `v_max = λ·PRF/4` | 일반형은 `λ·PRF/(4·cos(β/2)·cos(δ_el))`, `λ·PRF/4` 는 **하한**. 완화계수 중앙값 1.001, 최대 1.036 |

⭐ **X4 가 제일 아프다.** 5G 의 *규격 보장 상시신호*(SSB)를 WiFi 의 *트래픽 의존 속도*와 비교했다 —
사과 대 사과가 아니다. **비교 축을 "규격이 보장하는 상시신호"로 통일**하면 순위가 바뀔 수 있다.
→ 다음 사람이 가장 먼저 할 일: **§H 를 읽고 비교 규약을 다시 정하라.**

---

## 2. 진행 중이던 것 (전부 백그라운드, 새로 시작하지 말 것)

| ID | 내용 | 상태 |
|---|---|---|
| `wgxmbz013` | 리포트 6편 → 논문 참고자료 | 산출 중 (`paper_kit.json` 06:14) |
| `wi5t8f30q` | 헤드라인 경화 + 재프레이밍 | Harden 완료 → Reframe |
| `w8bsm62ll` | SenSys·MobiSys 심사 + 실측 2기종 메쉬 보수 | 진행 |
| `brtdx858u` | `viz_report2.py` 재현 실행(52분) — stage2 IndexError 추적용 | 실행 중 |

---

## 3. GPU 재생성 상태

```
stage1  ✅ 전부 (x500v2 버그 수리 후)
stage2  4/5 ✅  —  report6_sbr · sbr_kr_sweep · report3_rt · sbr_defect_fixes
        1/5 ❌  —  파형·RCS 스윕: IndexError: index 5 is out of bounds for axis 0 with size 5 (52분 소모)
stage3~ 미착수  (rcs_anchor 3h10m · σ격자 최대 23h)
```

⚠ `viz_report2.py:1164` 의 `range(5)` 는 **표 열 개수**라 무관하다(오진했다). 진짜 원인은
`brtdx858u` 로그에서 확인할 것.

---

## 4. 미적용 정정 (발견만 됐고 파일은 안 고쳤다)

1. **리포트 05 철회** — "5G 커버리지 0" 은 단일점 아티팩트. `outputs/cpi_guard_sweep.json`
   `verdict.report05_action` 에 교체 지시가 있다
2. **σ 앵커 +2.5068 dB 제거** — Das μ 는 선형평균(§III-1 + Table III 캡션), scale adjustment 는
   log-normal 기체용이고 Phantom 3 은 Rician. **생산 σ 는 무사**(slope_only 는 절편 미사용),
   실측계획 예상 σ(L2/L4)만 2.51 dB 낮아진다
3. **선행연구 정정 12건 + pw04 2건** — `outputs/prior_settled_*.json` 의 `corrections_to_apply`
4. **`sigma_anchor.json` 의 disclaimer 문자열**이 아직 "레벨과 주파수의존은 측정에서"라고 말한다(코드는 맞다)
5. **`viz_report2.py:1102-1103, 1181`** 의 "shell opaque / RF sees THROUGH the plastic" 라벨이
   `penetrate=True` 와 모순

---

## 5. 확정된 것 (되돌리지 말 것)

- **리포트 6편 체계** — 구 13편 삭제(보존커밋 `4bfb1e5`, 삭제 `d418dbf`)
- **서술 규약** `docs/REBUILD_2026-07-30.md` §5 (2026-07-31 재정립: 방어적 표현 금지, "한 일" 중심)
- **논문 규격** `docs/PAPER_SPEC.md` — 좁힌 기여 3개(세 파형·Pfa 교정·σ 민감도)
- **H8 4관문** 생존(178편 대조), 단 의역 2건은 거짓 — `outputs/prior_settled_h8.json`
- **커널 검증** 0.201 dB / 48입사 — kr 스윕 밀도 기본값 6→12 로 고정함
- **`confidence` ≠ 형상충실도** — `shape_source` 필드 신설. 사진 일치도는 confidence 와 **역순**

---

## 6. 학회 판단 (현재)

| 학회 | 합격률 | 판정 |
|---|---|---|
| ICASSP | ~45% | 가장 붙을 곳이지 **탑티어는 아니다** |
| **SenSys** | ~20% | ⭐ **1순위 권고** — 주제 적합도 최고, CORE A* |
| MobiSys · MobiCom | ~16-18% | 실측이 논문 몸통이어야 |
| INFOCOM | ~19% | 네트워킹 실체 필요 |

⚠ 전략 충돌: v_max 를 ICASSP 에 먼저 내면 SenSys 펀치가 빠진다. `w8bsm62ll` 이 이 쪼개기 안을
반대로 논증해보는 중.

**실측 최고가치 실험**(변경됨): 1.07 m/s 초과 비행으로 앰비언트 5G 앨리어싱 직접 시연.
⚠ 단 X4 때문에 **WiFi 쪽 비교 조건을 먼저 확정**해야 이 실험이 의미가 있다.

---

## 6.5 ⭐⭐ 07:15 — 사용자 지시로 워크플로 2개 중단. 재개 방법

```
Workflow({scriptPath: '<...>/workflows/scripts/venue-sensys-wf_12a2f5c7-93b.js',
          resumeFromRunId: 'wf_12a2f5c7-93b'})      # SenSys·MobiSys 심사 + 실측 2기종 메쉬 보수
Workflow({scriptPath: '<...>/workflows/scripts/monostatic-gap-wf_3318b7f6-a15.js',
          resumeFromRunId: 'wf_3318b7f6-a15'})      # 패시브↔모노 경계 + 모노 검출시나리오
```
경로 앞부분: `/root/.claude/projects/-workspace-sionna2/a78e7d06-306f-4e2d-b124-5fe972bc4462/`
완료된 에이전트는 캐시에서 즉시 반환되므로 **남은 단계만** 돈다.

### 중단 시점에 끝나 있던 것 / 안 끝난 것

| | 상태 |
|---|---|
| `outputs/monostatic_prior.json` (43 KB) | ✅ **LaSen 정독 완료** |
| `outputs/review_mobicom.json` (16 KB) | ✅ MobiCom 심사 |
| `outputs/mesh_compare_photo.json` (112 KB) | ✅ 사진↔메쉬 대조 |
| `mono_vs_passive` · `verify_monostatic` · `monostatic_scene.py` | ❌ 미착수 |
| `review_sensys` · `review_mobisys` | ❌ 미착수 |
| 실측 2기종(matrice4e·mini5pro) 메쉬 보수 | ❌ 미착수 |

### ⭐⭐ LaSen 확정 — 학회 전략을 바꾼다

> **LaSen: Low-Altitude Drone Sensing with 5G-NR Signals**
> Yang, Dai, Li, Huang, Chen, Zhang, Song, Zhang, Tao (SUSTech·Peng Cheng Lab·중산대·CAICT·HKUST·BUPT)
> **ACM/IEEE SenSys '26**, Saint Malo, 2026-05-11~14, pp. 732–745, DOI 10.1145/3774906.3800504
> **게재본**(camera-ready, ACM DL). 프리프린트 아님. CC BY 4.0.
> PDF: `/data/public/jeong/papers/5G/26_LaSen.pdf`

프로젝트 메모 `[[sionna2-lasen-monostatic]]` 의 *"LaSen 은 모노스태틱, PDSCH 재활용은 패시브
바이스태틱에 이전 불가"* → **CONFIRMED** (정밀화 2건 필요, 상세는 JSON `lasen.geometry`).

**두 가지 함의가 정반대 방향이다 — 재개 시 가장 먼저 판단할 것.**

1. ✅ **SenSys 가 이 주제를 받는다는 증거다.** "저고도 드론 센싱 + 5G-NR" 이 그대로 실렸다.
   내가 SenSys 를 1순위로 민 근거가 실측으로 확인됐다.
2. ⚠ **그런데 내가 추천한 바로 그 학회에 아주 가까운 게재 경쟁자가 이미 있다.**
   우리 투고는 LaSen 과 대조 심사되고, 심사자로 그 저자들이 배정될 수 있다.

⭐ **다만 이것이 오히려 우리 기여를 날카롭게 만든다**:
LaSen 은 **모노스태틱 + PDSCH**(자기가 송신하니 기준신호를 통제한다).
우리는 **패시브 바이스태틱 + 앰비언트 전용**(통제 못 한다).
합치면 한 문장이 된다 — **"모노는 기준신호를 고를 수 있어서 되고, 패시브는 못 골라서 안 된다."**
즉 LaSen 은 위협이 아니라 **우리 경계 논증의 가장 강한 인용**이 될 수 있다.
→ 재개 시 `wf_3318b7f6-a15` 의 Boundary 단계가 정확히 이 논증을 수치로 닫는다.

## 6.9 ⭐⭐ 08:5x — 4개 워크플로 전부 완료. 프로젝트 상태가 크게 바뀌었다

### A. 헤드라인 법칙은 **우리 것이 아니다** (우선권 확정)

| 선행 | 내용 |
|---|---|
| **Chen 외, Applied Sciences 14(10):4282 (2024)** MDPI 게재·OA | `f_d=(2v/λ)cos(β/2)cosδ` 를 **같은 기호로**, **패시브 바이스태틱**에서, 실측까지 붙여 냈다. 우리 법칙으로 그들의 0.56 rps 를 재현하면 **상대오차 0.00 %** |
| Abratkiewicz 외, **JSTARS 16:3469–3484 (2023)** | SSB 주기가 패시브 속도 모호를 제한한다고 명시 |
| **LaSen, SenSys '26** | 3.5 GHz 나이퀴스트 산술을 **문제 서술**로 쓰고 그걸 이기는 시스템을 만들었다 |

⛔ **"우리가 처음"이라고 쓰면 즉사한다.** 살아남는 것: 근거 붙은 **교차표준 표** · 실기체 속도 겹치기 ·
설계규칙 역산 `PRF_req=4v/λ` · 인프라 이전 서사 · 검출성능(블라인드/접힘/CPI 독립성)까지의 연결 ·
**탈출구 6개 전수 판정**.
⚠ Chen 2024 원문 **미확보**(MDPI 403). 현재 LaSen 요약 경유 **2차 인용**이다 — 최대 구멍.

### B. 내 모노/패시브 경계 논증은 틀렸고, 고친 뒤 **더 강해졌다**

`"모노는 PRF 를 자유롭게 고른다"` → **거짓**. 3GPP sub-6 CSI-RS **500 Hz 천장**(13단 슬롯 사다리).
n78 에서 **10.71 m/s** = 패시브 기본값의 정확히 10.0배.
⭐ **그 천장조차 공개 기체 최고속도를 0/5 로 못 덮는다**(최저 typhoonh480 13.5 m/s). 직접 검산함.
→ 심사자의 *"왜 모노를 안 하나"* 에 대한 답: **모노도 10.71 m/s 에서 멈춘다.**

⭐ **진짜 경계는 기하가 아니다** — **기준신호만 쓰기 vs 전 파형 쓰기**.
그리고 그 경계는 **패시브 쪽에서도 넘는다**: 우리 `refrate_law.json` 의 `nr_recon` 행이
5G 전파형 1 ms → **21.4 m/s**. ⛔ 헤드라인을 **"기준신호 정합필터에 머무는 패시브는"** 으로
스코핑하지 않으면 **우리 표가 우리 문장을 반박한다.**

### C. ⭐ 진짜 우리 것 — 새 닫힌형 2개

1. **바닥의 기하 무관성**: 모노 v_max = 바이 β=0, 세 밴드 전부 `|차| = 0 m/s`(계산으로 확인).
   발표값 1.07/14.39/40.67 은 **두 기하의 최악값** — 부풀린 게 아니라 깎은 값이다.
2. **간섭축의 같은 구조**: `모노 필요격리 − 패시브 직접파비 = 20log₁₀(4πL/λ) − G_rx = 87.3 dB`,
   **표적거리 무관**. L→0 이면 패시브가 모노로 **연속 수렴**한다.

### D. ⚠⚠ 기존 검출 결과 전체에 걸린 결함 — φ=90° 고정

`experiment_freespace_range.py:322, 773` 에 `phi_deg=90.0` 하드코딩. φ=90° 는 기저선의
**수직이등분선**이라 `R₁≈R₂` 가 **구조적으로** 성립 = 기하 차이가 원리적으로 못 나타나는 자리.

```
φ=90° 한 점   기하 간 spread 차   0.118 dB
φ 전체 스윕                      23.17 dB     ← 200배
```
report13·report05 의 R90·커버리지·블라인드가 전부 이 한 방위에서 풀렸다. **재계산 1순위.**

### E. Config B(패시브 준모노)는 막혀 있다

`P_dir ∝ 1/L²` → 조명원 옆에 붙을수록 직접파가 커진다. LTE L=10 m 에서 필요 제거량
**119.3 dB**(우리가 훑는 최대 90 dB 보다 29.3 dB 부족). ⚠ 단 달성가능량 40~90 dB 는
**출처 없는 선언값**이라 인용 전 근거 필요.
⭐ 그리고 **문헌에도 순수 config B 사례가 없다** — 우리 격자의 B 열이 공백일 가능성(그 자체가 기여).

### F. 참고문헌 라이브러리 완성

`docs/REFERENCE_LIBRARY.md`(293 KB) · `docs/references.bib`(62 KB) · `outputs/reference_library.json`(428 KB)

- 학회 스윕 **81항목**(A 능동모노 25 / B 준모노 4 / C 패시브바이 28), **41편 PDF 직독**, dblp 2,217 레코드
- Sionna 코퍼스 **고유 218편 중 140편이 Sionna 언급, 137편 실행**
- ⭐ **Sionna 로 dBsm 을 인쇄한 논문은 1편**(Ziganshin EuCAP 2025 게재) — 그것도 **차량**이고 UTD 를 얹은 뒤
- ⭐⭐ **씬에 표적을 세운 19편 중 드론 전기체 메시를 산란적분에 통과시킨 것 0편**(직접 검산)
  — 프로펠러 1개 · 금속 정육면체 · 큐보이드 사람 · 패싯 차량 · 외부솔버 주입(LAMBDA)뿐
- 신규 발견: **Needle in a Haystack (MobiSys 2026)** 실망 5G-A 기지국으로 UAV 추적 ·
  **HiSAC (SenSys '24)** 바이스태틱 분해능 규약 `Δr=c/[2B cos(β/2)]` · **Geng IET RSN 2020** 사과-대-사과 수치
- ⚠ **함정 하나 걸러냄**: 아카이브의 `Sionna RT 드론 ISAC 연구.pdf` 는 논문이 아니라 **한국어 AI 생성 메모**다.
  기계집계만 믿으면 선행연구로 들어간다 — 격리함
- ⚠ dblp 가 **TAP·AWPL·EuCAP·IET RSN·TMTT 를 색인 안 한다** → 그 5곳은 "없다"가 아니라 **"못 봤다"**

### G. 학회 판정

```
SenSys   시뮬만 REJECT ~2-3%  ·  실측 1회 추가해도 REJECT ~10-15%
MobiSys  후보에서 내려라 — 모바일 플랫폼이 없다
```
⭐ **비어 있는 자리 2개를 지목받았다**:
1. **셀 인벤토리** — 사업자·사이트·시간대별 실제 `ssb-PeriodicityServingCell` 분포.
   1.07 m/s 는 규격 상수가 아니라 **기본값의 귀결**(합법범위 4.28~0.134 m/s)인데 **배치 현실을 아무도 안 쟀다**
2. **패시브 전파형 수신기** — LaSen 의 패시브 대응물. **한계를 보고하는 게 아니라 이기는 것**

### H. LaSen 인용 시 필수 주석

⚠ **상용 gNB 로 드론을 잰 적이 없다.** 드론 반사는 자기 USRP 가 5.8 GHz 만재 송신으로 측정,
상용 gNB 2대(2,200 프레임)는 **RE 점유 마스크만** 제공, 둘을 원소별 곱해 12,079 샘플 생성.
LaSen 자체 모순 3건도 기록됨(CSI-RS 500 vs 200 Hz · "period of 100 Hz" 단위오류 · SDR 기종 불일치).

## 7. 미커밋

```
git status --short | wc -l    →  300+ 파일
미푸시 커밋                     →  3개 + 4bfb1e5 + d418dbf
```
사용자가 커밋·푸시를 승인했으나 **재편이 끝나지 않아 보류 중**.
