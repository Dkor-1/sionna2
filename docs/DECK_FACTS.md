# DECK_FACTS — 0804 팀미팅 덱이 인용해도 되는 사실 기반

생성 2026-08-03 02:32:42 · 생성기 `benchmark/deck_facts.py` · 런타임 2.8 s

> **증거 규칙**  한 주장은 (a) 내가 직접 연 PDF 의 축자 문장이거나, (b) 디스크의 JSON 에서 우리가 계산했고 재현 가능하거나, 둘 중 하나다. 나머지는 UNVERIFIED 로 라벨하거나 뺀다.
> 인용은 매 빌드 PDF 페이지 텍스트에 재대조된다. 개수 주장은 **코퍼스 이름을 달고 다닌다**.

**사실 32건**(축자 인용 9 · 우리 계산 22 · SECONDHAND 1 · UNVERIFIED 0) · **철회 10건** · **열린 구멍 7건** · 자체검사 42/42 통과 (인용 재대조 13건)

⚠ SECONDHAND ['F30'] — 다른 라운드가 연 PDF 의 인용에 기댄다. 슬라이드에 올리기 전 원문을 직접 열 것.

---

## 0. 한 문장 포지션 (적대적 질문을 견디도록 쓴 판)

> **우리는 새 물리를 주장하지 않는다 — 우리는 드론 기체 메시에서 재질 가중 산란을 계산하고, 그 σ 를 세 기하·세 조명원 격자에 넣어, 이미 알려진 무모호 속도 한계(Abratkiewicz, IEEE JSTARS 2023, eq.16)를 네 표준에 걸쳐 하나의 규약으로 평가하며 교정된 검출성능까지 잇는다. 우리가 연 26편 중 이 여섯 축을 동시에 채운 것은 없고, 우리도 회절과 로터 두 축은 비어 있다.**

*(EN)* We claim no new physics: we compute material-weighted scattering from whole drone airframe meshes, carry that sigma through a three-geometry x three-illuminator grid, and evaluate a known unambiguous-velocity limit (Abratkiewicz, IEEE JSTARS 2023, eq.16) across four standards under one stated convention, all the way to CFAR-calibrated detection - a combination no row in our 26-paper matrix fills, and one where two of our own columns (diffraction, rotor) are still empty.

**어떻게 나왔는가**
- 우리가 FULL 인 여섯 열: engine · mesh · material · aspect · geometry · vmax (26행 중 이 여섯을 동시에 채운 유일한 행).
- 빼야 하는 열: rotor(NONE, future work 로 강등) · diffraction(NONE, 우리 최대 물리 공백) · amplitude validation(PARTIAL, 해석 PO 구까지).
- 가장 가까운 경쟁: Ziganshin(EuCAP'25 게재 / arXiv'26 프리프린트) 6/9 동점 — 회절은 우리보다 앞서고 표적은 자동차·구·원기둥이며 PEC 이고 무모호 속도를 다루지 않는다.
- 다음 경쟁: RadarTwin(arXiv'26) 은 engine·mesh·material·aspect 를 채우지만 vmax·geometry 가 비어 있다.
- vmax 가 FULL 인 선행(Abratkiewicz JSTARS'23 · Geng IET RSN'20 · Jopanya SPAWC'25)은 전부 산란을 계산하지 않는다.
- ⭐ 반드시 붙는 한정어 둘 — ⑴ '조명원 **종류**를 통제 비교' (한 조명원 '안'의 자원 비교는 Taylor & Poullin, IEEE TAES 61(4), 2025 게재가 이미 했다, F28). ⑵ '메시를 **산란적분에 통과**' (씬에 메시를 넣은 선행은 여럿 있다, F30).

**적대적 질문 4개와 답**
- **Q. 새로운 게 뭔가. 식도 남의 것, 엔진도 남의 것(Mitsuba), 표적도 남의 CAD 아닌가.**
  - A. 새 물리는 없다고 먼저 말한다. 새로운 것은 **연결**이다 — 기체별 재질 가중 σ 가 격자를 통과해 교정된 Pd 까지 한 파이프라인으로 이어진다. 매트릭스가 보여주는 것은 그 연결을 26편 중 아무도 끝까지 하지 않았다는 것이다. 그리고 어느 조각이 남의 것인지 칸마다 인용으로 적어 뒀다.
- **Q. 회절이 없으면 σ 가 틀린 것 아닌가. 그러면 뒤의 모든 결과가 틀린다.**
  - A. 밴드 **기울기**가 실측보다 3.5~8배 가파르다는 것은 우리가 먼저 말한다(F24). 다만 절대 레벨은 앵커로부터 0.00 dB 이동하므로 앵커가 레벨을 고쳐준 적이 없고(F20), 우리는 절대 σ 판정을 보류한다. 검출 결과는 σ 의 **상대 순서**(기체 간·자세 간)에 주로 의존하고, 절대 레벨은 링크버짓 상수로 흡수된다 — 그 의존성을 슬라이드에 명시한다.
- **Q. 무향실 시뮬레이션이 실제 배치와 무슨 상관인가.**
  - A. 상관없다고 인정하는 것이 정답이다. 챔버는 **통제된 비교대**이지 배치 예측이 아니다. 배치 주장은 실측(외부 필드테스트, X410)으로만 한다. 그리고 우리가 인용하는 실측 앵커는 우리 것이 아니라 공개 문헌 RCS 다.
- **Q. 그 6/9 는 자기 채점 아닌가.**
  - A. 그렇다. 그래서 채점표가 아니라 **근거표**를 낸다 — 234칸 중 80칸이 축자 인용이고 빌드가 매 실행 PDF 와 재대조한다(80/80 통과). 판정에 동의하지 않으면 근거를 보고 다시 채점할 수 있다. 그리고 우리 행에도 NONE 이 두 개 있다.

**절대 말하지 않는다**
- ⛔ '무모호 속도 식을 우리가 제시한다/유도한다' — Abratkiewicz 2023 eq.(16) 이 문자 그대로 같다.
- ⛔ '반복주기가 무모호 속도를 정한다는 관찰이 새롭다' — 2023년 JSTARS 초록에 있다.
- ⛔ '5G SSB 가 1 m/s 대에서 접힌다는 것을 우리가 처음 보인다' — ±1.0901 m/s 로 이미 적혀 있다.
- ⛔ 'ΔR = c/B 규약이 우리 선택' — Abratkiewicz eq.(15)/Malanowski 교재가 근거다.
- ⛔ 'SSB 상시성 프레임이 우리 것' — Abratkiewicz 서론 문장이다.
- ⛔ '광선추적은 RCS 를 못 낸다' — SBR 은 계산한다. 참인 문장은 'Sionna 기본 solver 에 산란적분이 없다' 뿐이다.
- ⛔ 'Sionna 에는 회절이 없다' — 1차 UTD 쐐기 회절이 있다.
- ⛔ '드론 RCS 를 Sionna 로 낸 논문은 세상에 없다' — 코퍼스를 밝히지 않은 전칭 주장은 금지.
- ⛔ 다운링크 점유를 성능 축으로 삼는 관점이 우리 것 — Abratkiewicz §V 가 3단계로 이미 갖고 있다.
- ⛔ 접힘 해제(dealiasing) 대책을 우리가 제안한다 — 제안하지 않는다. eq.(17)-(20) 이 선행이다.
- ⛔ '다중 Rx 10log10(N) 이상 상한' 이 우리 규약 — Taylor & Poullin(IEEE TAES 61(4), 2025, 게재) p.8814 에 10log10(7)=8.4 dB 로 이미 있다.
- ⛔ 'hover blind 를 우리가 발견했다' — 게재 실측 선례가 둘 있다.
- ⛔ '한 표적·한 검출기·교정 오경보율의 통제 비교를 아무도 안 했다' — 조명원 '종류' 한정어 없이 쓰면 Taylor & Poullin 이 즉시 반례다.
- ⛔ '스톡 Sionna 에 회절이 없다' — 1차 UTD 쐐기 회절이 있고 PathSolver 기본값이 False 일 뿐이다.
- ⛔ '드론 메시를 Sionna 씬에 넣은 논문이 없다' — CAVIAR 등 반례가 있다. '산란적분에 통과시킨' 을 반드시 넣는다.

---

## 1. 슬라이드 순서 — 청중이 재미있어 하는 순

연구실 청중이 무엇을 재미있어 하는가로 정렬했다. 우리 엔진이 아니라 ⑴ 교차표준 속도표와 그 우선권 이야기, ⑵ 철회 목록이 가장 강하다.

| # | 무엇 | 왜 |
|---|---|---|
| 1 | 철회 목록 (R1~R10, 슬라이드에는 R1·R3·R5·R8 네 개만) | ⭐ 이 방의 누구도 자기 정정을 슬라이드에 올리지 않는다. 그래서 가장 기억에 남고 가장 신뢰를 산다. 특히 R1(우선권을 두 번 고쳤다)과 R5(고쳤더니 우리에게 유리해졌다)는 '이 팀은 자기 결론에 유리한 방향으로만 고치지 않는다' 를 한 장으로 증명한다. |
| 2 | 교차표준 무모호 속도표 + 실기체 최고속도 겹치기 (F02, F03, F05, F06) | 숫자 네 개가 289배 벌어지고, 그 위에 드론 다섯 대의 최고속도를 겹치면 '5G 상시신호로는 나는 드론을 못 잰다' 가 한 그림으로 끝난다. 그리고 그 식의 주인이 '드론은 아직' 이라고 자기 논문 결론에 적어 놓았다 — 이게 이 발표의 최고 문장이다. |
| 3 | 능력 매트릭스 그림 (F12~F15) | 사용자 추적표의 형식이고, 산문 열 줄이 하는 일을 한 장이 한다. '9/9 인 행은 없다' 와 '우리 행도 두 칸 비었다' 를 같이 보여주는 것이 핵심. |
| 4 | 열린 구멍 G1~G7 (특히 G1·G2 가 닫혔다는 것) | 지난 발표에서 '가장 가까운 선행이 2차 정보' 였던 것을 이번에 닫았다. 진척으로 읽히고, 남은 구멍을 스스로 열거하는 것이 다시 신뢰가 된다. |
| 5 | 회절 열 (F14, F22, F23, F24) | 우리 최대 공백이면서 동시에 이 분야 전체의 공백이다(26행 중 3편). 약점을 분야 지형으로 바꾸는 슬라이드. |
| 6 | 엔진 검증 (F19, F20, F26) | ⚠ 가장 공들인 부분이지만 청중에게는 가장 덜 재미있다. 0.2006 dB 같은 수는 신뢰의 배경음이지 헤드라인이 아니다. 뒤로 보낸다. |
| 백업 | 우리 문구를 좁히는 선행 (F28~F32) — 슬라이드 아님, 질문 대비 | ⭐ 발표에 넣지 않되 **손에 들고 있는다**. Taylor & Poullin 이나 CAVIAR 를 아는 청중이 손을 들면 그 자리에서 인용으로 답해야 한다. '몰랐다' 가 가장 나쁜 답이다. F28 만은 본편 인용으로 올린다 — 우리 벤치마크 설계의 선행 방법론이기 때문이다. |

⚠ 우리가 가장 오래 붙든 것(SBR 커널)을 앞에 두고 싶은 유혹이 있다. 두면 안 된다.

---

## 2. ⭐ 철회 목록 — 이 프로젝트가 스스로 내린 주장들

⚠ 이 절은 **슬라이드에 올린다**. 자기 정정을 보여주는 팀은 신뢰받고, 조용히 지우는 팀은 그렇지 않다. 여기 있는 것은 실패가 아니라 감사가 작동한 기록이다.

### R1. 무모호 속도 식의 우선권 — 두 번 틀렸고 두 번 고쳤다

- **우리가 말했던 것** — ⑴ 'v_max = λ·PRF/4 는 우리 발견이다' → ⑵ '우리 것이 아니다, Chen 외 Applied Sciences 2024 가 같은 기호로 먼저 냈다'
- **무엇이 그것을 깼는가** — G1·G2 를 실제로 확보해 두 PDF 를 열었다. ⑴ Chen 은 닫힌 식을 표시하지 않는다 — 수치 대입뿐이다. ⑵ λ/(4T) 의 진짜 선행은 1년 앞선 Abratkiewicz 외 JSTARS 2023 eq.(16) 이고 반쪽 구간 규약까지 같다. ⑶ Chen 자신이 그 논문을 [8] 로 인용한다.
- **지금 참인 것** — 우선권은 Abratkiewicz 외(IEEE JSTARS 16:3469-3484, 2023, 게재)에 있다. 우리는 재현자다. 우리 몫은 식이 아니라 하나의 규약 아래 놓인 교차표준 표와, 그 표를 실기체 최고속도·검출성능에 잇는 것이다.
- **근거** — `pdf`: /data/public/sionna_jeong/reference_library/g1g2/abratkiewicz2023_jstars.pdf · `quote`: The Doppler range is limited by T^SSB_dist so that Vb in [-lambda/(4 T^SSB_dist), lambda/(4 T^SSB_dist)] · `json`: outputs/verify_chen.json : priority_ledger.who_owns_what[0] · corrections_to_our_records[1]
- **왜 슬라이드에 올리는가** — ⭐ 우선권 오귀속은 리뷰에서 반드시 걸린다. 우리가 먼저 말하면 감사가 작동한 증거가 되고, 숨기면 나중에 논문 심사에서 드러난다. 게다가 LaSen(SenSys 2026)의 귀속조차 한 세대 늦다는 것을 우리가 잡아냈다 — 이건 우리 코퍼스 작업의 성과다.
- **⭐ 예상 공격** — 두 번 틀렸다는 것은 조사 과정이 부실했다는 뜻 아닌가.
- **우리 답** — 첫 라운드의 인용문 3건은 원문과 축자 일치했다 — 그 라운드는 정직했고, 틀린 것은 '우리가 확보하지 못한 논문에 대해 결론을 냈다' 는 것이다. 그래서 이번 워크플로의 규칙이 '내가 직접 연 PDF 아니면 UNVERIFIED' 가 되었다.

### R2. '모노스태틱은 반복률을 자유롭게 고른다' 는 프레이밍

- **우리가 말했던 것** — 모노스태틱 센서는 자기가 송신하므로 PRF 를 설계변수로 자유롭게 고를 수 있고, 그래서 무모호 속도 문제에서 자유롭다.
- **무엇이 그것을 깼는가** — 3GPP 가 sub-6 CSI-RS 에 500 Hz 천장을 걸고, 실측 상용 gNB 는 50~200 Hz 로 돈다 (Chen 의 상용 gNB 40 슬롯=20 ms=50 Hz, LaSen 의 China Mobile N41 은 자원세트 2개를 엮어 200 Hz).
- **지금 참인 것** — 모노스태틱의 기준신호 천장은 500 Hz → 3.5 GHz 에서 10.71 m/s 이고, 이는 우리가 모형화한 5기체 중 0기를 커버한다. 모노스태틱의 진짜 탈출구는 반복률이 아니라 **데이터 심볼**이며, 그것은 트래픽에 종속된다.
- **근거** — `json`: outputs/monostatic_prior.json : headline_of_this_file · prf_ladder_at_3p5GHz · `pdf`: /data/public/sionna_jeong/reference_library/g1g2/chen2024_applsci_14_4282.pdf · `quote`: Table 5. CSI-RS signal parameters of the 5G commercial base station. ... Period 40 slots
- **왜 슬라이드에 올리는가** — 이 정정이 우리 서사를 **강화**한다 — 접힘 한계가 패시브만의 약점이 아니라 구조적 한계임을 보여준다. 우리 격자(A/B/C 세 기하)가 존재하는 이유가 이것이다.
- **⭐ 예상 공격** — PRS 를 요청하면 되지 않는가.
- **우리 답** — 된다 — 그리고 그것이 측위 세션 옵션이라는 것이 요점이다. 우리 서사는 '상시 신호' 축이고, PRS 는 상시가 아니다. 격자에서 그 칸을 따로 표시한다.

### R3. '5G 는 모든 헤딩에서 커버리지 0' 이라는 헤드라인

- **우리가 말했던 것** — 5G 상시기준(SSB)에서는 모든 헤딩에서 검출 커버리지가 0 이다.
- **무엇이 그것을 깼는가** — 그 '0' 은 CPI=100 ms 와 2.5빈 선언가드가 **동시에** 성립하는 한 점에서만 참인 단일-CPI 아티팩트였다. 검출기가 실제로 지우는 1.5빈 규약에서는 같은 CPI 에서 blind=0.636 이고, CPI 를 200 ms 로만 늘려도 0.303 이다. 게다가 LTE 도 CPI≤0.0393 s 에서는 blind=1.000 이 된다 — '전 헤딩 블라인드' 는 5G 만의 성질이 아니다.
- **지금 참인 것** — '0' 을 버리고 **구조적 비율**로 바꿨다: 같은 CPI 에서 5G 블라인드율은 WiFi 의 12~19배로 일정하게 크고(CPI 로 안 없어짐), 접힘 비율은 CPI 와 무관한 상수 0.861 이다(WiFi·LTE 0).
- **근거** — `json`: outputs/cpi_guard_sweep.json : verdict.artifact · structural.s1_equal_cpi_penalty · structural.s2_alias_floor · `numbers`: {"blind_hard_G1_at_100ms": 0.6361111111111111, "blind_hard_G1_at_200ms": 0.30277777777777776, "alias_frac_G1": 0.8611111111111112}
- **왜 슬라이드에 올리는가** — ⭐ 극단적인 수(0, 100%)는 청중이 가장 잘 기억하고 가장 쉽게 반증된다. 우리가 스스로 그 수를 내리고 더 약하지만 더 튼튼한 수로 바꾼 사례다.
- **⭐ 예상 공격** — 그럼 5G 가 나쁘다는 결론 자체가 흔들리는 것 아닌가.
- **우리 답** — 결론의 **방향**은 흔들리지 않았고 **크기**가 바뀌었다. 접힘 비율 0.861 대 0 은 CPI 로 제거되지 않는 구조적 격차이고, 그것이 원래 하려던 말이다. 바뀐 것은 '0' 이라는 단정뿐이다.

### R4. '실측 앵커가 우리 σ 레벨을 정한다' 는 주장

- **우리가 말했던 것** — 우리 절대 σ 는 문헌 실측에 앵커되어 있다.
- **무엇이 그것을 깼는가** — slope_only 모드에서 앵커가 실제로 옮기는 레벨을 계산했더니 7기체 평균 -0.0000 dB — 정확히 0 이다. 앵커는 회전축(pivot)을 밴드 비가중 평균에 두고 **기울기만** 돌린다.
- **지금 참인 것** — 앵커는 주파수 기울기만 받고 절대 레벨은 우리 PO 출력 그대로다. 그래서 매트릭스에서 우리 진폭 검증 칸은 FULL 이 아니라 PARTIAL 이고, 절대 σ 판정은 보류한다.
- **근거** — `json`: outputs/sigma_anchor.json : drones[*].modes.slope_only · `reproduce`: benchmark/deck_facts.py 가 매 실행 7기체 평균을 다시 계산한다 · `numbers`: {"matrice4e": -4.736951571734001e-15, "mavic4pro": -1.7763568394002505e-15, "mini5pro": -1.1842378929335002e-15, "phantom4": -5.921189464667501e-16, "s1000plus": -2.960594732333751e-15, "typhoonh480": 0.0, "x500v2": 2.3684757858670005e-15}
- **왜 슬라이드에 올리는가** — 레벨과 기울기를 뭉뚱그리면 '검증되었다' 는 인상이 과장된다. 이 정정이 우리 한계 문장(절대 σ 보류)의 근거다.
- **⭐ 예상 공격** — 그럼 level_and_slope 모드를 쓰면 레벨도 앵커되지 않는가.
- **우리 답** — 된다 — 그 모드는 크기보정(L² 또는 L⁴)을 가정해야 하고, 우리 자체 크기지수가 1.24~1.32 에 r=0.64~0.70 이라(F25) 그 가정이 가장 약한 고리다. 그래서 헤드라인은 가정이 가장 적은 slope_only 로 낸다.

### R5. '상반성 위반 13.7 dB' 라는 수

- **우리가 말했던 것** — 바이스태틱을 β≤45° 로 제한하는 근거는 최대 13.7 dB 의 상반성 위반이다.
- **무엇이 그것을 깼는가** — 역검증 결과 13.719 dB 는 **상반성 위반이 아니라** matrice4e·5G 3.5 GHz·β=45° 단일 셀의 **이등분선 근사오차 p95** 였다. 두 양은 크기도 뜻도 다르다.
- **지금 참인 것** — 참값은 이렇다 — 이등분선 근사오차 p95 최대 20.04 dB · rms 중앙 7.47 dB, 상반성 rms 최대 5.80 dB(최악 드론 β=90° 에서 8.24 dB). β 창을 정당화하는 근거는 근사오차 쪽이고, 그 값은 13.7 보다 **크다** — 즉 모노 팔의 이점이 브리핑보다 오히려 더 크다.
- **근거** — `json`: outputs/geometry_grid.json : sigma_transfer.correction_to_the_brief · `cross_check`: outputs/geometry_grid_axis_review.json : OK7 · outputs/geometry_grid_fairness_audit.json : D6 (독립 감사 2건이 정정을 통과시켰다)
- **왜 슬라이드에 올리는가** — ⭐ 이 정정은 우리에게 **불리하지 않다** — 그래서 더 좋은 사례다. '우리는 우리 결론에 유리한 방향으로만 고치지 않는다' 를 보여준다. 라벨이 틀렸으면 결론이 유리해져도 고친다.
- **⭐ 예상 공격** — 결과적으로 유리해졌다면 왜 처음에 불리하게 적었는가.
- **우리 답** — 두 양을 구분하지 않았기 때문이다. 값 하나를 여러 라운드가 이어받으며 라벨이 미끄러졌고, 역검증이 잡았다. 그래서 지금은 모든 수치에 '무엇의 어떤 통계인지' 를 함께 적는다.

### R6. (보너스) 게재처·인용문 오류 4건 — 매트릭스 빌드의 자동 재대조가 잡았다

- **우리가 말했던 것** — Costa 의 게재처는 IEEE JSTSP · RadarTwin 인용문 끝은 '…that the real system cannot resolve' · Semkin IEEE Access 2020 의 PDF 는 pdf_paths[0]
- **무엇이 그것을 깼는가** — 빌드가 매 실행 인용문을 PDF 페이지 텍스트에 재대조하도록 만들었더니 걸렸다.
- **지금 참인 것** — Costa 는 **IEEE JSTEAP vol.1 (2025)** 이다(게재판 1쪽 DOI 10.1109/JSTEAP.2025.3604407 확인). RadarTwin 원문은 '…that the real radar does not measure'. Semkin 의 pdf_paths[0] 은 다른 논문(arXiv 2112.09774)이고 본편은 pdf_paths[1] 이다. Great-X 의 재질 칸은 '언급 없음' 에서 원문 확인 후 PARTIAL 로 고쳤다.
- **근거** — `json`: outputs/capability_matrix.json : record_corrections_ko
- **왜 슬라이드에 올리는가** — 정정 자체보다 **정정을 잡은 장치**가 요점이다 — 인용문을 매 빌드 재대조하는 습관이 없었으면 넷 다 발표까지 갔다. 사용자 추적표의 'IEEE JSTEAP 2025' 가 맞았고 우리 기록이 틀렸다.
- **⭐ 예상 공격** — 그렇게 사소한 오류를 슬라이드에 올릴 필요가 있는가.
- **우리 답** — 오류를 올리는 게 아니라 **장치**를 올린다. 한 장에 '자동 재대조 80/80 통과, 그 과정에서 잡힌 기록 오류 4건' 으로 요약한다.

### R7. (보너스) 회절 언급 횟수 — 코퍼스를 밝히지 않으면 셋 다 다른 수가 나온다

- **우리가 말했던 것** — 우리 코퍼스는 diffraction 11회 · UTD 13회 · PTD 1회 · wedge 0회를 언급한다.
- **무엇이 그것을 깼는가** — 코퍼스를 특정해 다시 세었다. 그 수는 **reference_library.json 텍스트**의 수이고, 그중 13 은 UTD 가 아니라 diffract* 였다(UTD 는 10, PTD 는 8).
- **지금 참인 것** — 코퍼스 B(reference_library.json 텍스트): diffraction 11 · diffract* 13 · UTD 10 · PTD 8 · wedge 0. 코퍼스 A(PDF 217편 본문): diffract* 72편/607회 · UTD 10편 · PTD 6편 · wedge 10편. 두 수를 한 문장에 섞으면 안 된다.
- **근거** — `json`: outputs/psolve_diffraction.json : machine_census · outputs/deck_facts.json : recomputed.diffraction_census
- **왜 슬라이드에 올리는가** — ⭐ 이 프로젝트가 반복해서 틀린 방식이 정확히 이것이다 — 서로 다른 코퍼스의 수를 한 호흡에 섞는 것(81개 엔트리 중 8개 인용 건도 같은 실수였다). 규칙으로 승격했다: 모든 개수 주장은 코퍼스 이름을 달고 다닌다.
- **⭐ 예상 공격** — 단순 오타 아닌가.
- **우리 답** — 오타가 아니라 **범주 오류**다. 그리고 실질적 결론은 그대로다 — 어느 코퍼스로 세든 회절을 실제로 구현한 저작은 3편뿐이다.

### R8. ⭐⭐ '다중 Rx 10log10(N) 이상 상한' 과 'hover blind' 는 우리 발견이 아니다

- **우리가 말했던 것** — report12 의 다중 Rx 이상적 결합 상한 10log10(N) 규약, 그리고 report05 의 hover blind(정지 표적이 패시브 바이스태틱에서 사라진다)를 우리 관찰처럼 서술했다.
- **무엇이 그것을 깼는가** — Taylor & Poullin(IEEE TAES 61(4), 2025, 게재)이 7심볼 결합에 'the ideal gain one could expect would be of 10 log10(7) = 8.4 dB' 를 이미 적었다 — 내가 이번에 원문에서 직접 확인했다. hover blind 도 게재 실측 선례가 둘 있다(Taylor & Poullin: 미검출이 0-도플러 근접에 몰림 / Sun 외, IEEE OJ-COMS 2025: 궤적이 바이스태틱 등고선을 따라가 미검출).
- **지금 참인 것** — 둘 다 '우리가 처음' 이라고 쓸 수 없다. 10log10(N) 은 교과서 결합이득이고, hover blind 는 이 분야의 확립된 사실이다. 우리 몫은 그것을 **네 조명원에 걸쳐 정량화**한 것이며, 선행과 나란히 놓아야 한다. ⭐ 오히려 좋은 소식이다 — 우리 시뮬 결과가 독립 게재 실측으로 확인된다.
- **근거** — `pdf`: /data/public/jeong/papers/LTE/25_Drone_Detection_Using_4G-LTE-Based_Passive_Radar.pdf · `quote`: When performing the detection on all seven symbols, the ideal gain one could expect would be of 10 log10(7) = 8.4 dB. · `verified_by_me`: 이번 라운드에 PDF 를 직접 열어 조각 대조했다(Q.TAY29) · `json`: outputs/deepread_reconcile.json : headline_ko · outputs/deepread_w1.json
- **왜 슬라이드에 올리는가** — novelty 를 과장했다가 좁힌 사례이고, 동시에 우리 시뮬이 게재 실측과 같은 방향임을 보여주는 슬라이드로 바꿀 수 있다. 잃는 것은 '최초' 주장, 얻는 것은 외부 검증이다.
- **⭐ 예상 공격** — 그럼 report05·report12 의 결론이 다 남의 것 아닌가.
- **우리 답** — 결론이 아니라 **관찰**이 선행이다. 우리 결론은 '조명원을 바꾸면 이 현상의 크기가 어떻게 달라지는가' 이고, 그 비교는 여전히 비어 있다(F28). 다만 그 문장에서 '조명원 종류' 라는 한정어를 절대 빼면 안 된다.

### R9. '아무도 드론 메시를 Sionna 씬에 넣지 않았다' 로 읽히는 문장

- **우리가 말했던 것** — Sionna 씬에 표적을 넣은 논문 중 드론 기체 메시를 넣은 것은 없다.
- **무엇이 그것을 깼는가** — CAVIAR(arXiv 2401.03310)가 드론을 ITU metal 재질로 Sionna 씬에 넣고, Cazzella(arXiv 2507.19173)·VaN3Twin(arXiv 2505.14184)이 차량 메시를 부품 단위로 갈라 재질을 준다. AirGuard(IEEE JSAC accepted)는 실제 DJI .obj 메시를 부른다.
- **지금 참인 것** — 문장에서 **산란적분을 주어 자리로** 옮겼다: '드론 기체의 3-D 표면 메시를 산란적분에 통과시켜 그 진폭을 보고한 논문이 0편' 이 살아남는 문장이다. 메시를 씬에 넣은 선행은 여럿 있고, 그 메시가 하는 일은 전파 상호작용이지 σ 산출이 아니다.
- **근거** — `json`: outputs/deepread_reconcile.json : claim_status.C1 (verdict=NARROWED, counterexamples_to_the_loose_reading 5건)
- **왜 슬라이드에 올리는가** — ⭐ 이것이 이 발표에서 가장 반증당하기 쉬운 문장이었다. 우리가 먼저 좁히지 않으면 청중이 CAVIAR 한 편으로 슬라이드를 무너뜨린다.
- **⭐ 예상 공격** — 그렇게 좁히면 남는 게 거의 없지 않은가.
- **우리 답** — 좁혀도 남는 것이 정확히 우리 기여다 — 산란적분·재질 가중·자세 분해. 그리고 좁힌 문장은 H8 4관문 판정(12편 중 0편 통과)이 그림으로 뒷받침한다.

### R10. (보너스) 'Chen 이 같은 기호로 냈다' — 기호 주장도 부정확했다

- **우리가 말했던 것** — Chen 2024 가 v_max 를 우리와 **같은 기호로** 먼저 냈다.
- **무엇이 그것을 깼는가** — Chen 20쪽 전문에 'PRF' 는 **0회**, 'pulse repetition' 0회, 'Nyquist' 0회다 — 내가 이번에 직접 세었다. 같은 것은 eq.(4)의 β·δ 기호뿐이고, 반복률 기호는 공유하지 않는다.
- **지금 참인 것** — 'β·δ 기호는 같지만 PRF 표기는 없다' 로 정확히 쓴다. 그리고 β·δ 조차 Chen 의 것이 아니라 [16] Samczynski 외 TGRS 인용이다.
- **근거** — `pdf`: /data/public/sionna_jeong/reference_library/g1g2/chen2024_applsci_14_4282.pdf · `command`: fitz 전문 추출 후 정규식 계수 — PRF 0 / pulse repetition 0 / Nyquist 0 · `verified_by_me`: 이번 라운드에 직접 계수
- **왜 슬라이드에 올리는가** — R1 과 묶어 한 줄로만 보인다. 요점은 '같다' 는 말도 근거를 대고 해야 한다는 것.
- **⭐ 예상 공격** — 기호가 다르면 같은 식이 아니라는 뜻인가.
- **우리 답** — 아니다 — 반대다. Chen 은 그 식을 아예 표시하지 않았고(F07), 진짜 선행은 Abratkiewicz 다. 기호 계수는 우리 이전 서술이 얼마나 성급했는지를 보여주는 지표로만 쓴다.

---

## 3. 사실 기반 — 슬라이드에 올려도 되는 것 전부

각 항목: 한 문장 주장 · 증거 등급 · 정확한 출처 · **예상 공격과 우리 답**. 공격을 예상하지 못한 사실은 아직 생각해보지 않은 사실이다.

### [속도·우선권]

#### F01 · 우리가 쓰는 무모호 속도 법칙 v_max = λ·PRF/4 는 우리 것이 아니다 — Abratkiewicz 외, IEEE JSTARS 16:3469-3484 (2023, 게재) eq.(16) 이 반쪽 구간 규약까지 문자 그대로 같다.

- **등급** `quoted-from-PDF`
- **EN** Our unambiguous-velocity law is Abratkiewicz et al., IEEE JSTARS 16:3469-3484 (2023, PUBLISHED) eq.(16), verbatim, half-window convention included.
- **pdf** `/data/public/sionna_jeong/reference_library/g1g2/abratkiewicz2023_jstars.pdf`
- **loc** `Sec. IV, eq. (16), p.3476`
- **quote** > The Doppler range is limited by T^SSB_dist so that Vb in [-lambda/(4 T^SSB_dist), lambda/(4 T^SSB_dist)] (16)
- **quote_fragment_checked** > The Doppler range is limited by T
- **citation** `K. Abratkiewicz, A. Ksiezyk, M. Plotka, P. Samczynski, J. Wszolek, T. P. Zielinski, IEEE J. Sel. Topics Appl. Earth Observ. Remote Sens., vol. 16, pp. 3469-3484, 2023 (PUBLISHED, CC BY 4.0), doi:10.1109/JSTARS.2023.3262291`
- **json** `outputs/verify_chen.json : quotes_abratkiewicz2023[A2]`
- **⭐ 예상 공격** — 그럼 이 발표의 이론적 기여는 무엇인가. 남의 식을 표로 만든 것뿐 아닌가.
- **우리 답** — 맞다, 식은 선행이다. 우리가 새로 놓는 것은 식이 아니라 **평가**다 — 하나의 명시된 규약 아래 네 표준을 같은 표에 올리고(F02), 그 표를 실기체 최고속도와 겹치고(F03), 그 한계를 검출성능까지 잇는다(F26). 두 선행은 각자 자기 표준 한 줄만 갖고 있고, 둘 다 드론을 쓰지 않았다(F05).

#### F02 · 하나의 규약(반쪽 구간, c=3e8) 아래 네 조명원의 무모호 속도는 LTE CRS 40.695 · WiFi VHT-LTF 14.395 · 5G SSB 1.071 · WiFi beacon 0.141 m/s 로 289배 벌어진다.

- **등급** `computed-by-us`
- **EN** Under one stated convention the four ambient illuminators span 289x in unambiguous velocity: LTE CRS 40.695, WiFi VHT-LTF 14.395, 5G SSB 1.071, WiFi beacon 0.141 m/s.
- **json** `outputs/deck_facts.json : recomputed.vmax_table (cross-checked against outputs/verify_chen.json : reproductions_by_us.our_v1_table_recheck)`
- **formula** `v_max_half = lambda * PRF_ref / 4`
- **convention** `반쪽 구간(±). c = 3e8 — Abratkiewicz 도 c=3e8 을 썼음이 재현으로 확인됨.`
- **수치** `{"LTE CRS": 40.6945, "WiFi VHT-LTF": 14.3954, "5G SSB": 1.0714, "WiFi beacon": 0.1406}`
- ⚠ c 규약을 반드시 밝힌다. c 정확값을 쓰면 넷째 자리에서 갈린다(LTE 40.666 vs 40.695).
- **⭐ 예상 공격** — 반복률 값(LTE CRS 1 kHz, WiFi VHT-LTF 1 kHz)의 출처는 무엇인가.
- **우리 답** — 정직하게: 이번 라운드에서 **5G SSB 행만** 외부 1차 문헌으로 앵커되었다(Abratkiewicz A7 이 SSB 주기 집합 {5,10,20,40,80,160} ms 와 기본 20 ms 를 명시). LTE·WiFi 반복률은 우리 waveform 모듈의 가정이고 1차 규격으로 재확인하지 않았다 — 열린 항목이다.

#### F03 · 3GPP sub-6 CSI-RS 최대 설정률 500 Hz 로 올려도 3.5 GHz 에서 무모호 속도는 10.71 m/s 이고, 이는 우리가 모형화한 공개 최고속도 5기체 중 0기를 커버한다 — 가장 느린 typhoonh480 조차 13.5 m/s 다.

- **등급** `computed-by-us`
- **EN** Even at the 3GPP sub-6 CSI-RS ceiling of 500 Hz the unambiguous velocity at 3.5 GHz is 10.71 m/s, which covers 0 of 5 published airframe maxima.
- **json** `outputs/vmax_grid.json : drone_overlay.speed_axis.items (단일 진리원 src/drones.py : DRONES[*].max_speed_ms)`
- **ceiling_source** `outputs/monostatic_prior.json : prf_ladder_at_3p5GHz['csirs_spec_max'] (LaSen p.732 §1 이 3GPP TS 38.331 Rel-19 를 인용; Chen 2024 §3 의 슬롯 목록과 산술 정합)`
- **수치** `{"typhoonh480_max": 13.5, "mini5pro_max": 19.0, "phantom4_max": 20.0, "matrice4e_max": 21.0, "mavic4pro_max": 25.0}`
- **⭐ 예상 공격** — 500 Hz 는 규격 상한이지 실제 값이 아니다. 그리고 3GPP 원문을 직접 봤는가.
- **우리 답** — 둘 다 인정한다. 우리가 인용하는 500 Hz 는 **2차 인용**이다 — LaSen 이 TS 38.331 을 인용한 문장과 Chen §3 의 슬롯 목록(4~640 슬롯)이 30 kHz SCS 에서 2 ms=500 Hz 로 산술 정합한다는 것까지가 우리가 확인한 전부다. TS 38.331 원문은 열지 않았다. ⭐ 다만 방향을 보라 — PRF 가 높을수록 무모호 속도가 커져 우리 주장이 약해지므로, 500 Hz 는 **우리 주장에 가장 불리한 쪽으로 잡은 값**이다. 실측 상용망은 훨씬 낮다(Chen 의 상용 gNB 40 슬롯=20 ms=50 Hz → 1.07 m/s, C7). 즉 규격 확인이 어긋나더라도 현실 쪽으로 어긋날 가능성이 크고, 그러면 결론은 더 세진다.

#### F04 · Abratkiewicz 가 논문에 적은 두 숫자(20 ms → ±1.0901 m/s, 5 ms → ±4.3605 m/s @ 3.44 GHz)를 우리 법칙으로 소수 4자리까지 재현했다 — 단, 그들이 c=3e8 을 썼다는 것을 알아채야 맞는다.

- **등급** `computed-by-us`
- **EN** We reproduce both of Abratkiewicz's stated numbers to 4 decimals, once you notice they used c = 3e8.
- **json** `outputs/deck_facts.json : recomputed.abratkiewicz_eq16`
- **pdf** `/data/public/sionna_jeong/reference_library/g1g2/abratkiewicz2023_jstars.pdf`
- **loc** `Sec. IV, p.3476`
- **quote** > assuming the default value of T^SSB_dist = 20 ms and for the given carrier frequency, one can obtain the maximum unambiguous bistatic velocity of +-1.0901 m/s
- **quote_fragment_checked** > one can obtain the maximum unambiguous bistatic velocity of
- **수치** `{"T=20.0ms": {"paper": 1.0901, "ours_c3e8": 1.0901, "ours_cexact": 1.0894}, "T=5.0ms": {"paper": 4.3605, "ours_c3e8": 4.3605, "ours_cexact": 4.3574}}`
- **⭐ 예상 공격** — 소수 4자리 일치는 자명하다. 같은 식이니 당연한 것 아닌가.
- **우리 답** — 그렇다 — 그리고 그게 요점이다. 이 재현은 novelty 주장이 아니라 **우리 구현이 선행과 같은 양을 계산한다는 감사**다. 규약 불일치(c, 반쪽/전체 구간)는 이 분야에서 실제로 자주 어긋나는 지점이고, 우리는 그 어긋남을 이번에 잡아냈다(F08).

#### F05 · ⭐ 이 식을 소유한 두 논문 모두 드론을 쓰지 않았다 — Abratkiewicz 의 표적은 Volvo XC90 승용차이고, Chen 의 표적은 스테퍼 모터로 돌리는 회전 모형이다.

- **등급** `quoted-from-PDF`
- **EN** Neither owner of the equation used a drone: Abratkiewicz's target was a Volvo XC90 car, Chen's was a stepper-motor rotating model.
- **pdf_a** `/data/public/sionna_jeong/reference_library/g1g2/abratkiewicz2023_jstars.pdf`
- **loc_a** `Sec. VI, p.3478`
- **quote_a** > The cooperative target was a car (Volvo XC90) moving in a parking lot illuminated by the BTS
- **pdf_c** `/data/public/sionna_jeong/reference_library/g1g2/chen2024_applsci_14_4282.pdf`
- **loc_c** `Sec. 1, p.1-2`
- **quote_c** > a rotating target experimental model employing a stepper motor is constructed to accurately simulate target movement scenarios
- **json** `outputs/verify_chen.json : quotes_abratkiewicz2023[A9] · quotes_chen2024[C11]`
- **⭐ 예상 공격** — 드론을 안 썼다는 것이 그들의 결론을 무효화하지는 않는다. 왜 이것이 우리 자리인가.
- **우리 답** — 무효화하지 않는다 — 우리는 그렇게 주장하지 않는다. 주장은 **적용 범위**다. 승용차는 드론보다 반사도가 훨씬 크고, 이 차이를 저자들 스스로 적었다(F06). 우리가 계산하는 것은 정확히 그 빠진 항, 즉 드론 기체의 산란이다. 그리고 두 논문 다 EM 산란 계산이 없다.

#### F06 · ⭐⭐ 식의 주인이 직접 결론에 적어 놓았다: '다음으로 고려할 만한 문제는 소형 표적 검출, 예컨대 실험에 쓴 자동차보다 반사도가 훨씬 낮은 드론이다.'

- **등급** `quoted-from-PDF`
- **EN** The owners of the equation left drones as explicit future work, naming the reflectivity gap themselves.
- **pdf** `/data/public/sionna_jeong/reference_library/g1g2/abratkiewicz2023_jstars.pdf`
- **loc** `Conclusion / future work, p.3482`
- **quote** > The subsequent problem worth considering is small target detection, for instance, drones whose reflectivity is significantly lower than the car used in the experiment.
- **quote_fragment_checked** > drones whose reflectivity is significantly lower than the car
- **json** `outputs/verify_chen.json : quotes_abratkiewicz2023[A10]`
- **⭐ 예상 공격** — 2023년 future work 는 2026년까지 누가 이미 했을 수 있다.
- **우리 답** — 그래서 세었다. 능력 매트릭스 26행 어디에도 '드론 기체 메시 + 산란적분 + 진폭 검증 + 게재' 를 동시에 만족한 행이 없다 — H8 판정 12편 중 4관문 통과 0편이다(F16). 다만 이것은 '우리가 본 코퍼스 안에서' 이고, dblp 가 IEEE TAP/AWPL/EuCAP/IET RSN/TMTT 를 색인하지 않는다는 구조적 사각지대가 있다(G4).

#### F07 · ⚠ 우리 이전 기록이 우선권을 돌렸던 Chen 2024 는 **닫힌 식을 표시하지 않는다** — 20 ms → 50 Hz → [-25,25] Hz → 0.56 rps 라는 수치 대입만 있고, λ·PRF/4 도 cos(β/2)cos(δ) 합성형도 표시 식으로 없다.

- **등급** `quoted-from-PDF (검증된 부재 — PDF 20쪽 전문을 열어 확인)`
- **EN** Chen 2024 displays no closed-form unambiguous-velocity equation — only a numeric instantiation. Our earlier attribution to Chen was itself wrong.
- **pdf** `/data/public/sionna_jeong/reference_library/g1g2/chen2024_applsci_14_4282.pdf`
- **loc** `Sec. 5, p.13 of 20`
- **quote** > In experiments, the CSI-RS signal period is 20 ms, and the maximum unambiguous Doppler frequency is 50 Hz. The measurable Doppler frequency shift range is [-25 Hz, 25 Hz].
- **quote_fragment_checked** > the maximum unambiguous Doppler frequency is 50 Hz
- **json** `outputs/verify_chen.json : what_they_did_and_did_not.chen2024_DID_NOT[0]`
- **⭐ 예상 공격** — '식이 없다'는 부재 증명이다. 못 찾은 것과 없는 것을 어떻게 구분하는가.
- **우리 답** — 구분하지 못한다 — 그래서 범위를 좁혀 말한다. 확인한 것은 '20쪽 전문에서 우리가 찾지 못했다' 이고, 확인한 것은 Chen 의 표시 식 eq.(4)가 바이스태틱 도플러이며 그것조차 [16] Samczynski 외 TGRS 를 인용한다는 것이다(C1,C2). 그러니 우리가 하는 주장은 '이 식의 계보는 바르샤바 학파로 수렴한다' 까지다.

#### F08 · ⚠ 같은 논문 안에서 규약이 갈린다 — eq.(16) 은 반쪽 구간 ±λ/4T 인데 eq.(18) 은 전체 폭 λ/2T 를 Vmax 라 부른다. 규약을 밝히지 않으면 2배가 조용히 어긋난다.

- **등급** `quoted-from-PDF`
- **EN** One paper, two conventions: eq.(16) is the half-window +-lambda/4T while eq.(18) calls the full span lambda/2T 'Vmax'. A factor of 2 hides here.
- **pdf** `/data/public/sionna_jeong/reference_library/g1g2/abratkiewicz2023_jstars.pdf`
- **loc** `Sec. IV, eq. (17)-(18), p.3476`
- **quote** > Vi = V~i + N Vmax (17) ... and Vmax = lambda/(4 T) - (-lambda/(4 T)) = lambda/(2 T) (18)
- **quote_fragment_checked** > describes how many times the velocity is aliased
- **json** `outputs/verify_chen.json : quotes_abratkiewicz2023[A6]`
- **⭐ 예상 공격** — 사소한 표기 문제 아닌가.
- **우리 답** — 사소하지 않다. 이 워크플로가 잡은 실제 오류 다섯 건 중 두 건이 규약 혼선이었다. 선행과 우리 숫자를 나란히 놓는 슬라이드는 규약 줄(반쪽 구간·c 값)을 반드시 캡션에 넣는다.

#### F09 · Chen 의 Table 6 이 접힘 문턱을 (0.625, 0.75] rps 로 실측으로 가두고, 이는 우리 β=0 예측 0.560 rps 와 정합한다 — 그들이 문장으로만 말한 '바이스태틱 각 때문에 조금 더 크다' 가 수치로 뒷받침된다.

- **등급** `computed-by-us`
- **EN** Chen's Table 6 brackets the aliasing threshold in (0.625, 0.75] rps by measurement, consistent with our beta=0 prediction of 0.560 rps plus their stated bistatic relief.
- **json** `outputs/verify_chen.json : reproductions_by_us.chen_table6_threshold_bracket`
- **pdf** `/data/public/sionna_jeong/reference_library/g1g2/chen2024_applsci_14_4282.pdf`
- **loc** `Sec. 5.2, Tables 6-7, p.16-17`
- **quote** > the reason for the error of 100% is that the Doppler frequency exceeds the measurement range, resulting in Doppler blur
- **quote_fragment_checked** > resulting in Doppler blur
- **수치** `{"our_beta0_prediction_rps": 0.5600170374691247, "table6_ok_up_to_rps": 0.625, "table6_first_failure_rps": 0.75, "implied_beta_deg_if_delta_0": [52.72, 83.39]}`
- **⭐ 예상 공격** — β 와 δ 를 논문이 안 줬으면 그 역산은 자유도가 남는다.
- **우리 답** — 맞다 — 그래서 **구간으로만** 냈다. 단일 β 값을 주장하지 않는다. 그리고 독립 교차검사가 있다: 같은 0.75 rps 를 반경 0.15 m 로 줄이면 선속도가 한계 아래로 내려가고 논문의 Table 7 은 오차 0.9% 로 정상 측정한다. 부호가 우리 법칙을 따른다.

#### F10 · 무모호 속도의 바닥은 기하와 무관하다 — 모노스태틱 값과 바이스태틱 β=0 값의 차이가 세 밴드 모두 정확히 0 m/s 다. 즉 우리가 발표하는 숫자는 두 기하의 최악값이다.

- **등급** `computed-by-us`
- **EN** The unambiguous-velocity floor is geometry-independent: monostatic equals bistatic at beta=0, |diff| = 0 m/s in all three bands.
- **json** `outputs/geometry_grid.json : axis_independence.P1_floor_is_geometry_independent`
- **수치** `{"wifi": {"v_max_mono_ms": 14.385434644913628, "v_max_bi_beta0_ms": 14.385434644913628, "abs_diff_ms": 0.0}, "lte": {"v_max_mono_ms": 40.66636706456864, "v_max_bi_beta0_ms": 40.66636706456864, "abs_diff_ms": 0.0}, "nr": {"v_max_mono_ms": 1.07068735, "v_max_bi_beta0_ms": 1.07068735, "abs_diff_ms": 0.0}}`
- **⭐ 예상 공격** — β=0 에서 같은 건 정의상 당연하다. 왜 결과로 내세우는가.
- **우리 답** — 결과로 내세우는 것이 아니라 **방어선**으로 쓴다. '그건 패시브 바이스태틱이라 불리한 것 아니냐' 는 질문에 대한 답이다 — 아니다, 능동 모노스태틱으로 바꿔도 이 바닥은 그대로다. 기하를 바꿔서 벗어날 수 없다.

#### F11 · 접힘 비율은 CPI 와 무관한 상수다 — 5G 상시기준(SSB)에서 0.861, WiFi 0, LTE 0. 적분시간을 늘려도 표본화율의 한계는 사라지지 않는다.

- **등급** `computed-by-us`
- **EN** The alias fraction is a CPI-independent constant: 0.861 for 5G SSB, 0 for WiFi, 0 for LTE. Longer integration cannot fix a sampling-rate limit.
- **json** `outputs/cpi_guard_sweep.json : structural.s2_alias_floor`
- **수치** `{"5G_G1": 0.8611111111111112, "WiFi_W1": 0.0, "LTE_L1": 0.0}`
- **⭐ 예상 공격** — 접힌다고 못 보는 것은 아니다. 접힌 속도도 검출은 된다.
- **우리 답** — 정확한 지적이고 우리도 그렇게 구분해 쓴다 — 접힘(alias)과 블라인드(blind)는 다른 양이다. 표에서 둘을 따로 낸다. 그리고 접힘 해제 대책은 우리가 제안하지 않는다 — Abratkiewicz eq.(17)-(20)이 두 RD 맵 방식을 이미 냈다. 우리 몫은 '한계를 정량화한다' 까지다.

### [포지셔닝]

#### F12 · 능력 매트릭스는 26행 × 9열 = 234칸이고, UNVERIFIED 칸이 0개다 — 80칸은 축자 인용이며 빌드가 매 실행 PDF 원문과 재대조해 80/80 통과했다.

- **등급** `computed-by-us`
- **EN** The capability matrix is 26x9 = 234 cells with zero UNVERIFIED, 80 of them verbatim quotes re-checked against the PDFs on every build (80/80 pass).
- **json** `outputs/capability_matrix.json : counts`
- **generator** `benchmark/capability_matrix.py`
- **figures** `{'full': {'png': 'outputs/figures/capability_matrix.png', 'pdf': 'outputs/figures/capability_matrix.pdf'}, 'slide': {'png': 'outputs/figures/capability_matrix_slide.png', 'pdf': 'outputs/figures/capability_matrix_slide.pdf'}}`
- **수치** `{"QUOTED": 80, "COMPUTED": 123, "DERIVED": 31, "UNVERIFIED": 0}`
- **⭐ 예상 공격** — 칸을 채운 판정 자체가 주관적이다. 'PARTIAL' 의 경계는 누가 정하는가.
- **우리 답** — 우리가 정했고, 그래서 각 칸에 **판정 근거를 같이 실었다** — 인용문이면 문장과 위치, 계산이면 JSON 키와 스크립트. 판정에 동의하지 않아도 근거를 보고 스스로 다시 판정할 수 있다. 그것이 산문 대신 매트릭스를 쓰는 이유다.

#### F13 · 아홉 열을 모두 채운 행은 0개다. 최다는 6/9 이고 거기 해당하는 행은 Ziganshin EuCAP'25, Ziganshin arXiv'26, 그리고 우리다.

- **등급** `computed-by-us`
- **EN** No row fills all nine columns. The maximum is 6/9, tied between Ziganshin (EuCAP'25), Ziganshin (arXiv'26) and us.
- **json** `outputs/capability_matrix.json : rows[*].cells[*].level`
- **수치** `{"Ziganshin, arXiv'26": 6, "Ziganshin, EuCAP'25": 6, "OURS (sionna2)": 6, "Kirik, Sigma'19": 5}`
- **⭐ 예상 공격** — 우리를 남의 논문과 같은 표에 올린 것 자체가 자기평가다. 우리 행만 후하게 준 것 아닌가.
- **우리 답** — 그 위험을 알기 때문에 우리 행에 **NONE 두 개(rotor, diffraction)와 PARTIAL 한 개(진폭 검증)를 그대로 뒀다**. 6/9 는 Ziganshin 과 동점이지 최고가 아니고, 우리가 비는 열은 슬라이드에 인쇄된다.

#### F14 · ⭐ Diffraction 이 가장 빈 열이다 — 26행 중 회절을 실제로 모형에 넣은 것은 3편(Ziganshin EuCAP'25·arXiv'26 은 UTD+정점회절, Kirik Sigma'19 은 SBR 에 PTD)뿐이고, **우리 행도 그 빈칸 중 하나다**.

- **등급** `quoted-from-PDF + computed-by-us`
- **EN** Diffraction is the emptiest column: only 3 of 26 rows model it, and our row is one of the blanks.
- **json** `outputs/capability_matrix.json : column_findings.diffraction`
- **quote** > We show that more comprehensive diffraction methods are required to achieve realistic results: one of them is vertex diffraction
- **quote_source** > Ziganshin et al., Proc. EuCAP 2025 (PUBLISHED), Abstract, doi:10.23919/EuCAP63536.2025.10999367
- **수치** `{"rows_full": ["Ziganshin, EuCAP'25", "Ziganshin, arXiv'26", "Kirik, Sigma'19"]}`
- **⭐ 예상 공격** — Sionna 에는 회절이 있다. 왜 그냥 켜지 않는가.
- **우리 답** — Sionna 2.0.1 에 회절이 있는 것은 맞다(F22) — 1차 UTD **쐐기** 회절이고, 전파 경로의 그림자 경계 불연속을 고치는 물건이다. 그런데 그것이 먹일 **산란적분이 Sionna 에 없다**(F21). 게다가 테셀레이션된 드론 셸에서 쐐기 각도는 드론의 성질이 아니라 우리 메싱의 성질이 된다. 구조적으로 우리 커널에 더할 수 있는 것은 PTD/PTD-EEC 쪽이고, 그것이 밴드 기울기를 고칠지는 **미검증**이다.

#### F15 · 26행 중 engine·mesh·material·aspect·geometry·vmax 여섯 열을 동시에 FULL 로 채운 행은 우리뿐이다. 앞 네 열을 채운 다른 행은 RadarTwin(arXiv'26) 하나이고 그 행은 vmax·geometry 가 비어 있다.

- **등급** `computed-by-us`
- **EN** Ours is the only row FULL on engine+mesh+material+aspect+geometry+vmax simultaneously; the only other row full on the first four (RadarTwin, arXiv'26) is empty on vmax and geometry.
- **json** `outputs/capability_matrix.json : rows[*].cells[*].level (교집합 계산)`
- **수치** `{"rows_full_on_six": ["OURS (sionna2)"], "rows_full_on_first_four": ["RadarTwin, arXiv'26", "OURS (sionna2)"], "rows_with_vmax_and_mesh": [["Clutter-Aware ISAC, ProcIEEE'26", 1, 2, 0], ["OURS (sionna2)", 2, 2, 1]]}`
- **⭐ 예상 공격** — 열을 우리가 골랐으니 우리가 이기는 조합이 나오는 것은 당연하다.
- **우리 답** — 열은 사용자 추적표에서 왔다(Sionna RT · mesh · material · aspect/RCS · rotor · diffraction), 우리가 발명한 것이 아니다. 우리가 더한 세 열(진폭 검증·기하·무모호 속도) 중 두 열에서 우리는 각각 PARTIAL 과 동점이다. 그리고 우리가 고른 열에서도 우리는 9/9 가 아니다.

#### F16 · H8('드론 메시의 산란 시그니처를 Sionna 급 엔진에서 계산하고 진폭까지 검증한 게재 논문은 없다') 를 4관문으로 판정한 결과, 후보 12편 중 네 관문을 모두 통과한 것은 0편이다. 막힌 곳: 게재 8 · 드론메시 2 · 엔진내부 1 · 진폭검증 1.

- **등급** `computed-by-us`
- **EN** Of 12 adjudicated candidates, 0 pass all four prongs.
- **json** `outputs/report01_paper.json : h8 (n_adjudicated, n_passing_all_prongs, blocked_at_counts)`
- **corpus** `판정 문서 21건 / 저작 19편, 스윕 PDF 178편`
- **수치** `{"P1": 8, "P4": 1, "P2": 2, "P3": 1}`
- ⚠ 슬라이드 문구는 'ZERO papers' 가 아니라 'ZERO in our corpus of N, and here is what the corpus cannot see' 로 쓴다.
- **⭐ 예상 공격** — '없다' 는 세상 전체에 대한 주장이다. 못 본 논문이 있을 것이다.
- **우리 답** — 있다. 그래서 문장을 **코퍼스에 한정해서** 쓴다. 그리고 사각지대를 스스로 명시한다 — dblp 가 IEEE TAP·AWPL·EuCAP·IET RSN·TMTT 를 색인하지 않아 그 지면들은 자동 스윕에 구조적으로 보이지 않았다. 거기서 '안 나왔다' 는 '안 봤다' 라는 뜻이고, 그렇게 말해야 한다.

#### F17 · 아카이브 고유 PDF 218편 중 Sionna 를 언급한 것 140편, 실제로 돌린 것 137편인데, 광선추적 씬 **안에 표적을 세운** 고유 저작은 6편뿐이고, Sionna 로 dBsm 을 인쇄한 논문은 1편(Ziganshin, EuCAP 2025, 게재)뿐이며 그 표적은 **자동차**다.

- **등급** `computed-by-us`
- **EN** Of 218 unique PDFs, 137 actually run Sionna, only 6 put a target inside the scene, and exactly 1 prints dBsm from Sionna - a car.
- **json** `outputs/reflib_sweep_sionna.json : counts`
- **수치** `{"pdfs_unique": 218, "mention_sionna": 140, "sionna_used": 137, "target_in_scene_unique_works": 6, "prints_dbsm_from_sionna": 1, "state_a_sionna_version": 18, "state_no_sionna_version": 122, "published_verified_in_pdf": 9, "preprint": 128}`
- **⭐ 예상 공격** — '6편' 과 '19편' 을 예전에 섞어 말한 적이 있다. 어느 쪽인가.
- **우리 답** — 섞어 말한 것이 맞고, 그래서 이번에 분리했다. 6편 = **Sionna 씬 안에 표적을 세운 고유 저작** (reflib_sweep_sionna.json). 19편 = **전문 판정 코퍼스의 고유 저작 수**(report01_paper.json, 문서 21건). 서로 다른 두 코퍼스이고, 한 문장에 같이 넣으면 안 된다.

#### F18 · Sionna 를 쓴 논문 140편 중 버전을 적은 것은 18편뿐이다 — 스택이 0.8.0 에서 2.0.1 까지 두 번 갈아엎였는데도 그렇다.

- **등급** `computed-by-us`
- **EN** Only 18 of 140 papers state a Sionna version, across a stack that was rewritten twice between 0.8.0 and 2.0.1.
- **json** `outputs/reflib_sweep_sionna.json : counts.state_a_sionna_version`
- **⭐ 예상 공격** — 버전 미기재가 결과를 틀리게 만들지는 않는다.
- **우리 답** — 틀리게 만들지는 않는다. 재현 불가능하게 만든다. 우리가 이것을 드는 이유는 남을 비판하려는 게 아니라 **우리 리포트가 왜 버전·커밋·런타임을 다 적는지**를 설명하기 위해서다.

### [엔진]

#### F19 · 우리 SBR 커널은 해석적 PO 구 대비 최대 편차 0.2006 dB 다(div=16, kr 1~100, 입사방향 48개).

- **등급** `computed-by-us`
- **EN** Our SBR kernel agrees with the analytic PO sphere to 0.2006 dB max deviation.
- **json** `outputs/sbr_kr_sweep.json : summary_div16.max_abs_db_vs_po`
- **수치** `{"max_abs_db_vs_po": 0.2005726178588444, "max_abs_db_vs_mie": 6.729111994408728, "std_pct_vs_po_kr_ge30": 0.8854682372035955, "std_pct_vs_mie_kr_ge30": 1.834374210222452, "n_incidence": 48, "kr_min": 1.0, "kr_max": 100.0, "div": 16}`
- **⭐ 예상 공격** — 정확한 Mie 해와는 최대 6.73 dB 어긋난다. 0.2 dB 만 말하는 것은 유리한 기준을 고른 것 아닌가.
- **우리 답** — 두 수를 둘 다 낸다. 커널이 PO 근사이므로 **수치 수렴의 과녁은 해석 PO** 이고, Mie 잔차는 'PO 근사를 쓴 대가' 라는 별도의 자다. kr≥30 에서 Mie 대비 산포는 1.83% 로 떨어진다 — 큰 잔차는 저-kr(공진영역)에 몰려 있고, 그게 바로 우리 few-λ 한계다. ⭐ Mie 도 해석 PO 도 **기준해이지 우리 출력이 아니다**.

#### F20 · 실측 앵커는 **주파수 기울기만** 옮기고 절대 레벨은 옮기지 않는다 — 7기체 평균 레벨 이동 -0.0000 dB(최대 |4.7e-15| dB), 기울기는 0.74~1.70 → 0.210 dB/GHz 로 정렬된다.

- **등급** `computed-by-us`
- **EN** The measurement anchor moves the frequency SLOPE only; the mean absolute level shift is 0.0000 dB over 7 airframes.
- **json** `outputs/sigma_anchor.json : drones[*].modes.slope_only (mu_before_dbsm vs mu_after_dbsm, 7기체 평균)`
- **reproduce** `benchmark/deck_facts.py : recompute()['anchor_slope_only']`
- **수치** `{"mean_level_shift_db": -1.2688263138573218e-15, "n_airframes": 7, "slope_before_range": [0.7419970017631432, 1.6994008126771427], "slope_after": [0.21]}`
- **⭐ 예상 공격** — 그럼 절대 σ 는 아무 검증도 안 받은 것 아닌가.
- **우리 답** — 그렇다. 그것이 정확히 우리 매트릭스에서 진폭 검증이 FULL 이 아니라 PARTIAL 인 이유다. 절대 레벨은 해석 PO 구까지만 검증되었고 측정에 앵커되지 않았다. 우리는 절대 σ 판정을 보류한다.

#### F21 · 설치된 Sionna 2.0.1 의 rt 파이썬 소스에는 'rcs' 라는 단어가 0회, 'radar_cross_section' 이 0회 나온다 — 즉 산란적분도 σ 출력도 없다. 우리 파이프라인이 존재하는 이유가 이 한 줄이다.

- **등급** `computed-by-us (한 줄로 재현)`
- **EN** The installed Sionna 2.0.1 rt package contains zero occurrences of 'rcs' or 'radar_cross_section' - there is no scattering integral and no sigma output.
- **command** `grep -rio '\brcs\b' /home/yunjung/.venvs/py312/lib/python3.12/site-packages/sionna/rt --include=*.py | wc -l`
- **json** `outputs/deck_facts.json : recomputed.sionna_installed`
- **corroborating** `benchmark/verify_rt_no_rcs.py · outputs/psolve_diffraction.json : sionna_stock_D`
- **수치** `{"version": "2.0.1", "rt_dir": "/home/yunjung/.venvs/py312/lib/python3.12/site-packages/sionna/rt", "rcs_word_hits": 0, "radar_cross_section_hits": 0, "diffract_hits": 550}`
- **⭐ 예상 공격** — 'Sionna 는 RCS 를 못 낸다' 는 말은 예전에 우리가 틀렸다고 정정한 주장 아닌가.
- **우리 답** — 맞다 — 그래서 문장을 좁혔다. 틀린 문장은 '광선추적은 RCS 를 못 낸다' 였다(SBR 은 낸다). 참인 문장은 '**Sionna 기본 solver 에 산란적분 단계가 없다**' 뿐이고, 그것이 위 grep 이 보여주는 것이다. Sionna 는 경로 계수를 내지 σ 를 내지 않는다.

#### F22 · ⚠ 반대로 'Sionna 에 회절이 없다' 고 말하면 틀린다 — Sionna 는 1차 UTD **쐐기** 회절을 구현하고 기술보고서가 ITU-R P.526 권고 해를 쓴다고 명시한다. 다만 그것은 전파용 그림자경계 보정이지 산란적분에 붙는 PTD/fringe 보정이 아니다.

- **등급** `quoted-from-PDF`
- **EN** Sionna DOES implement first-order UTD wedge diffraction (ITU-R P.526 heuristic for finitely conducting wedges) - but as a propagation shadow-boundary fix, not as a PTD correction to a scattering integral.
- **pdf** `/data/public/sionna_jeong/sionna_papers_by_task/channel_modeling_raytracing/2504.21719__sionna-rt-technical-report-v1.pdf`
- **loc** `p.47 (Sionna RT Technical Report v1.2, arXiv 2504.21719v2)`
- **quote** > While [36] deals with diffraction at edges of perfectly conducting surfaces, it was heuristically extended to finitely conducting wedges in [37]. This solution, which is also recomended by the ITU [38], is implemented in Sionna.
- **quote_fragment_checked** > is implemented in Sionna
- **json** `outputs/psolve_diffraction.json : sionna_stock_D.what_D_IS`
- **⭐ 예상 공격** — 그럼 PathSolver(diffraction=True) 를 드론에 켜면 되지 않는가.
- **우리 답** — 켜도 σ 는 안 나온다 — 여전히 경로 계수만 나오고, D 가 먹일 산란적분이 없다(F21). 그리고 테셀레이션된 드론 셸에서 Sionna 의 쐐기 각도는 인접 면 법선 두 개로 읽히므로, 메시를 조밀하게 하면 각도가 바뀐다 — 드론의 성질이 아니라 우리 메싱의 성질이 된다.

#### F23 · 우리 RCS 커널(src/rcs_sbr.py + src/rcs_po.py)에는 diffract·PTD·UTD·creeping·fringe 가 0회 나온다 — 회절항이 전혀 없다. 이것이 우리 행의 빈칸이다.

- **등급** `computed-by-us (한 줄로 재현)`
- **EN** Our RCS kernel contains 0 occurrences of diffract/PTD/UTD/creeping/fringe - there is no edge term of any kind.
- **command** `grep -cEi 'diffract|\bPTD\b|\bUTD\b|creeping|fringe' src/rcs_sbr.py src/rcs_po.py`
- **json** `outputs/psolve_diffraction.json : our_p4_state_verified`
- **수치** `{"hits_by_file": {"src/rcs_sbr.py": 0, "src/rcs_po.py": 0}, "total_hits": 0}`
- **⭐ 예상 공격** — 그러면 결과를 믿을 수 없는 것 아닌가.
- **우리 답** — 영향의 크기를 우리가 계산했다(F24). 회절항 부재가 밴드 기울기 초과의 가장 유력한 물리적 후보이지만, 우리 자체 산술은 그것만으로 전부를 설명하기 어렵다고 말한다 — 우리 유효 지수는 2 가 아니라 0.55~1.27 이라 PO 적분이 이미 단일 평판이 아니다. 그래서 PTD 는 **수정이 아니라 진단으로 먼저** 붙일 계획이다.

#### F24 · 우리 σ 의 주파수 기울기는 실측 앵커보다 가파르다 — 3밴드 적합 7기체에서 0.74~1.70 dB/GHz, 22점 el=0 적합에서 0.96~1.54 dB/GHz 이고, 실측 센서스는 0.07~0.315 dB/GHz 다 (Das 0.210 대비 3.5~8.1배). 단 순수 f² 평판 한계는 2.681 dB/GHz 이므로 우리는 그 사이에 있다.

- **등급** `computed-by-us`
- **EN** Our band slope is steeper than measurement but below the pure-f^2 plate limit: ours 0.74-1.70 dB/GHz (3-band) vs measured 0.07-0.315, with the plate limit at 2.681.
- **json_ours_A** `outputs/report02_derived.json : band_slope (3밴드 1.843/3.5/5.21 GHz, 7기체)`
- **json_ours_B** `outputs/rcs_anchor.json : drones[*].regression.el0.a (22점 조밀 적합, 7기체)`
- **json_measured** `outputs/psolve_diffraction.json : our_p4_state_verified.measured_slope_census`
- **anchors** `Das (IEEE WCL 15:3731-3735, 2026, 게재) 0.210 · Yuan/mono3d θ=90° 0.315 dB/GHz`
- **수치** `{"fit_A_3band_7airframes_db_per_ghz": {"matrice4e": 0.9358698306274642, "mavic4pro": 1.3110883410656062, "mini5pro": 1.5170442793984567, "phantom4": 1.6994008126771427, "s1000plus": 1.6037946605260234, "typhoonh480": 1.1932246730776375, "x500v2": 0.7419970017631432}, "fit_A_range": [0.7419970017631432, 1.6994008126771427], "fit_B_22point_el0_7airframes_db_per_ghz": {"matrice4e": 1.1640230434425125, "mavic4pro": 0.9586804798404873, "mini5pro": 1.0666157392172597, "phantom4": 1.4105233519468743, "s1000plus": 1.5421589150245456, "typhoonh480": 1.3178556981757104, "x500v2": 1.0407900979670541}, "fit_B_range": [0.9586804798404873, 1.5421589150245456], "fit_B_n_points": [22], "measured_anchor_db_per_ghz": {"das_phantom3_mono": 0.21, "yuan_azplane": 0.315}, "measured_slope_census_db_per_ghz": [0.21, 0.21, 0.07, 0.17, 0.315, 0.231, 0.175], "measured_census_range": [0.07, 0.315], "pure_f2_plate_limit_db_per_ghz": 2.681, "ratio_fitA_over_das": [3.533319056014968, 8.092384822272109]}`
- ⚠ 어떤 적합을 인용하든 캡션에 밴드 수·점 수·고도각을 밝힌다. ⚠ 능력 매트릭스 그림의 회절 칸은 같은 22점 적합을 **DJI 쿼드 4종으로만** 잘라 '+0.96~+1.40 dB/GHz' 로 적는다 — 7기체 전체로는 +0.96~+1.54 다. 두 그림을 나란히 놓으면 차이가 보이므로, 한 발표 안에서는 한쪽 범위만 쓴다.
- **⭐ 예상 공격** — 두 개의 서로 다른 범위(0.74~1.70 과 0.96~1.54)를 내놓았다. 어느 것이 맞는가.
- **우리 답** — 둘 다 맞고 **다른 적합**이다 — 하나는 세 밴드 3점 회귀(1.843/3.5/5.21 GHz), 하나는 1.8~6.0 GHz 22점 조밀 회귀(el=0). 슬라이드에는 하나만 올리고 캡션에 적합 방식을 적는다. 이런 종류의 혼선이 이 프로젝트에서 실제로 정정을 부른 적이 있어서, 규약을 적는 것을 규칙으로 만들었다.

#### F25 · 우리 커널의 크기지수는 밴드별 1.24~1.32 이고 상관 r 은 0.64~0.70 에 불과하다 — L²(=2)도 L⁴(=4)도 아니고 산포가 커서, 크기 전이는 앵커의 가장 약한 고리다.

- **등급** `computed-by-us`
- **EN** Our kernel's own size exponent is 1.24-1.32 with Pearson r only 0.64-0.70 over 7 airframes - neither L^2 nor L^4, and too scattered to use as a single value.
- **json** `outputs/sigma_anchor.json : our_kernel_size_exponent.by_band`
- **수치** `{"by_band": {"LTE 1.843 GHz": {"exponent": 1.3227669529790187, "pearson_r": 0.6488790311984485}, "5G 3.5 GHz": {"exponent": 1.2376975333268867, "pearson_r": 0.6975110899360171}, "WiFi 5.21 GHz": {"exponent": 1.3181702184636794, "pearson_r": 0.6357166896631686}}, "exponent_range": [1.2376975333268867, 1.3227669529790187], "pearson_r_range": [0.6357166896631686, 0.6975110899360171], "n_drones": 7, "note_ko": "우리 기하가 스스로 내는 크기지수. L²(=2)도 L⁴(=4)도 아니고 산포가 크다 → 크기전이는 앵커의 가장 약한 고리이며 단일값으로 못 쓴다."}`
- **⭐ 예상 공격** — 자기 약점을 왜 스스로 슬라이드에 올리는가.
- **우리 답** — 누군가 물으면 어차피 나올 수이고, 우리가 먼저 말하면 신뢰가 되고 남이 먼저 말하면 흠이 된다. 그리고 실용적 결론이 붙는다 — 350 mm 급 실측 앵커를 1045 mm 옥토콥터로 전이하는 데 단일 크기법칙을 쓰면 안 된다.

#### F26 · CFAR 문턱은 이론값이 아니라 GPU 몬테카를로 2717초(백색 맵 500,000장 + 체인 맵 10,000장, complex128)의 경험적 오경보율에 교정되었고, 네 가드/트레이닝 구성의 α 는 이론값과 상대오차 최대 3.3e-04 로 일치한다.

- **등급** `computed-by-us`
- **EN** Our CFAR threshold is calibrated to empirical Pfa over 2717 s of GPU Monte Carlo (500,000 white maps), with alpha matching theory to 3.3e-04 relative error.
- **json** `outputs/verify_cfar.json : meta · alpha_audit`
- **수치** `{"runtime_s": 2716.746778488159, "n_maps_white": 500000, "n_maps_chain": 10000, "M_cpi": 48, "dtype": "torch.complex128", "pfa_nominal": [0.01, 0.003, 0.001, 0.0003, 0.0001, 3e-05, 1e-05, 3e-06, 1e-06], "guard_train": ["g2x2_t6x6", "g1x1_t4x4", "g3x3_t8x8", "g2x2_t10x10"], "alpha_max_rel_err": 0.00033463628713065505, "alpha_configs": 4}`
- **⭐ 예상 공격** — 백색잡음에서의 Pfa 교정은 실제 클러터에서 의미가 없다.
- **우리 답** — 맞다 — 그래서 백색 교정과 체인(전 처리사슬) 교정을 따로 냈다. 백색은 α 구현 감사용이고, 실제 오경보 판정은 체인 맵에서 한다. 그리고 우리 챔버는 semi-anechoic 이라 정적 클러터가 ECA 로 삼중 차단되고, 진짜 위협은 표적경유 바닥유령이라는 별도 축이다.

#### F27 · ⚠ 지금까지의 검출 결과는 전부 장면방위 φ=90° 한 컷이다. φ=90° 는 베이스라인의 수직이등분선이라 R₁≈R₂ 가 구조적으로 성립하고, 거기서 두 기하의 확산항 차는 0.118 dB 뿐이지만 φ 를 쓸면 최대 23.17 dB 로 벌어진다.

- **등급** `computed-by-us`
- **EN** Every detection result to date sits at scene azimuth phi=90 deg, where R1~=R2 structurally: the geometry difference is 0.118 dB there and up to 23.17 dB across phi.
- **json** `outputs/geometry_grid.json : range_normalisation.*.absmax_over_phi_db · traps[T1b]`
- **code** `src/experiment_freespace_range.py:322,773 (phi_deg=90.0 기본 인자)`
- **수치** `{"absmax_over_phi_db": 23.168839470105702, "at_headline_phi90_db": 0.118, "headline_phi": "phi_90", "file": "src/experiment_freespace_range.py", "default_arg_lines": [322, 773]}`
- **⭐ 예상 공격** — φ 는 하드코딩이 아니라 기본 인자다. 언제든 바꿀 수 있지 않은가.
- **우리 답** — 정확한 지적이고 우리 표현을 고쳐야 한다 — 하드코딩이 아니라 **기본 인자**다. 결함은 코드가 아니라 **보고**에 있다: 발표된 모든 숫자가 그 기본값에서 나왔고 φ 스윕을 보고한 적이 없다. 이번 라운드가 찾아낸 가장 큰 재계산 항목이고, 열린 채로 둔다.

### [⚠ 우리 문구를 좁히는 선행]

#### F28 · ⭐⭐ 우리 벤치마크 설계('한 표적·한 검출기·교정된 오경보율에서 통제 비교')에 게재된 선례가 있다 — Taylor & Poullin, IEEE TAES 61(4), 2025 (게재). 표적 DJI Phantom 4, 문턱 13 dB ↔ Pfa 10⁻⁶ 에서 전 심볼 사용과 CRS 포함 심볼만 사용을 통제 비교했고, 결과 방향이 우리 '점유 대가' 서사와 같다.

- **등급** `quoted-from-PDF`
- **EN** Our benchmark design has a published precedent: Taylor & Poullin, IEEE TAES 61(4), 2025, compared signal-resource choices on one target at a calibrated Pfa of 1e-6.
- **pdf** `/data/public/jeong/papers/LTE/25_Drone_Detection_Using_4G-LTE-Based_Passive_Radar.pdf`
- **loc** `p.8814 부근 (IEEE TAES vol.61 no.4, August 2025, 게재)`
- **quote** > The highest SNR is obtained by using all the symbols (24.2 dB), followed by a configuration using symbols containing the CRS (17.5 and 17.9 dB). However, the configuration using all the symbols also shows the highest number of plots, and thus of false alarms
- **quote_fragment_checked** > The highest SNR is obtained by using all the symbols
- **calibration_quote** `The 13 dB threshold corresponds to a false-alarm rate of 10-6.`
- ⚠ 이 논문은 슬라이드에 인용으로 올린다. 숨기면 가장 위험한 항목이다. ⭐ 우리 기록 정정: 다른 라운드가 표적을 'DJI Phantom 3' 으로 적었으나 원문은 **Phantom 4** 다('a DJI Phantom 4 drone evolving above the surveillance antenna'). 내가 이번에 직접 확인했다.
- **⭐ 예상 공격** — 그럼 우리 벤치마크는 새롭지 않다.
- **우리 답** — ⭐ 한정어 하나에 무게가 전부 실린다. 그들의 비교축은 **한 LTE 하향 신호 '안'의 심볼 부분집합**이고, 우리 비교축은 **서로 다른 조명원 종류**(WiFi / LTE / 5G)다. 기하도 그들은 하나, 우리는 셋이다. 그래서 우리 문장은 '조명원 종류를 통제 비교한 연구는 없다' 로만 쓰고, Taylor & Poullin 을 **선행 방법론으로 반드시 인용**한다. 이 한정어를 빼면 즉시 반례가 된다.

#### F29 · ⭐⭐ 다중 Rx 결합의 '10log10(N) 이상적 상한' 규약도 우리 것이 아니다 — 같은 논문이 7심볼 결합에 10log10(7)=8.4 dB 를 이상이득으로 잡고 문턱을 21.4 dB 로 올려야 한다고 적는다.

- **등급** `quoted-from-PDF`
- **EN** The 10log10(N) ideal-combining ceiling we use is published prior art, not ours.
- **pdf** `/data/public/jeong/papers/LTE/25_Drone_Detection_Using_4G-LTE-Based_Passive_Radar.pdf`
- **loc** `p.8814 (IEEE TAES 61(4), 2025, 게재)`
- **quote** > When performing the detection on all seven symbols, the ideal gain one could expect would be of 10 log10(7) = 8.4 dB. Theoretically, we thus should have used a threshold of 21.4 dB when using all the symbols.
- **quote_fragment_checked** > the ideal gain one could expect would be of 10 log
- **⭐ 예상 공격** — 10log10(N) 은 교과서 결합이득이다. 누구의 것도 아니지 않은가.
- **우리 답** — 정확히 그렇다 — 그래서 '우리 규약' 이라고 쓰면 안 된다는 것이다. 게다가 이 논문은 **실측이 이상값에 못 미친다**는 것까지 보였다. report12 의 다중 Rx 서술에서 '우리가 처음' 이라고 쓸 수 없고, 이 선례와 나란히 놓아야 한다.

#### F30 · ⭐ '드론 메시를 Sionna 씬에 넣은 논문이 없다' 로 읽히는 문장은 즉시 거짓이다 — CAVIAR(arXiv 2401.03310)는 드론을 ITU metal 재질로 씬에 넣고, Cazzella(arXiv 2507.19173)와 VaN3Twin(arXiv 2505.14184)은 차량 메시를 부품 단위로 갈라 재질을 준다. 살아남는 문장은 '그 메시를 **산란적분**에 통과시켜 검증된 진폭을 낸 게재 논문이 0편' 뿐이다.

- **등급** `SECONDHAND — 다른 정독 라운드가 연 PDF 의 인용에 근거한다. 나는 원문을 열지 않았다.`
- **EN** The loose reading of our corpus claim is false - drones and part-segmented vehicle meshes HAVE been placed in Sionna scenes with materials. Only the scattering-integral reading survives.
- **json** `outputs/deepread_reconcile.json : claim_status.C1.counterexamples_to_the_loose_reading`
- **upstream** `outputs/deepread_w1.json · outputs/deepread_w2.json (쪽번호·인용 포함)`
- **new_wording_ko** `우리가 보유·정독한 문헌 중, 드론 기체의 3-D 표면 메시를 산란적분에 통과시켜 그 진폭을 보고한 논문은 0편이다. 장면에 드론·차량 메시를 넣고 재질까지 배정한 선행은 여럿 있으나, 그 메시가 하는 일은 전파 상호작용이지 표적 산란단면적 산출이 아니다.`
- ⚠ 이 항목만은 내가 원문을 직접 열지 않았다. 슬라이드에 올리기 전 CAVIAR 표 V 를 직접 확인한다.
- **⭐ 예상 공격** — CAVIAR 가 드론을 Sionna 에 넣었는데 왜 우리가 처음인 것처럼 말하는가.
- **우리 답** — 말하지 않는다 — 문장을 고쳤다. CAVIAR 의 드론은 **수신기**이지 표적이 아니고 RCS 를 출력하지 않는다. 핵심은 '씬에 메시가 있느냐' 가 아니라 '그 메시가 산란적분을 통과해 σ 를 내느냐' 다. 슬라이드 문구에서 '산란적분' 을 주어 자리에 놓는다.

#### F31 · Sionna 2.0.1 의 PathSolver 는 diffraction=False · edge_diffraction=False 가 **기본값**이다. 즉 '스톡 Sionna 에 회절이 없다' 가 아니라 '기본으로 꺼져 있다' 가 참이다.

- **등급** `computed-by-us (설치본 소스 직접 확인)`
- **EN** Sionna's PathSolver defaults are diffraction=False and edge_diffraction=False - the capability exists and ships off by default.
- **code** `/home/yunjung/.venvs/py312/lib/python3.12/site-packages/sionna/rt/path_solvers/path_solver.py:154-155`
- **verbatim** `diffraction: bool = False,  /  edge_diffraction: bool = False,`
- **command** `grep -n 'diffraction' <sionna.rt>/path_solvers/path_solver.py`
- **⭐ 예상 공격** — 그러면 켜고 다시 돌리면 되는 것 아닌가.
- **우리 답** — 켜도 σ 는 안 나온다(F21·F22). 그리고 우리 커널에 없는 것은 UTD 쐐기항이 아니라 **PO 적분에 더해지는 PTD/fringe 항**이라 종류가 다르다. 다만 우리 쪽 표현이 부정확했던 것은 맞고, '스톡 Sionna 에 회절이 없다' 는 문장은 금지 목록에 넣었다.

#### F32 · 회절항 부재는 우리만의 뒤처짐이 아니라 이 분야의 기본값이다 — 26행 중 회절을 넣은 것이 3편뿐이고, Sagitta SBR(arXiv'26)·3GPP Rel-19 표준 RCS 모델·Great-X 가 전부 회절 없이 나온다. ⚠ 동시에, 회절을 붙이면 밴드 기울기가 좋아진다는 기대는 **근거가 약하다**.

- **등급** `computed-by-us`
- **EN** Missing diffraction is the field default, not our lag - and the expectation that adding it fixes our band slope is weakly grounded.
- **json** `outputs/capability_matrix.json : column_findings.diffraction · outputs/psolve_diffraction.json : THE_ANSWER · outputs/deepread_reconcile.json : diffraction_finding`
- **⭐ 예상 공격** — 그럼 회절을 붙일 것인가 말 것인가.
- **우리 답** — 붙이더라도 **진단으로 먼저** 붙인다. 우리가 지금 가진 것은 '인용할 수 있는 알려진 한계' 이지 '구현하면 기울기가 나아진다' 가 아니다 — 후자를 슬라이드에 쓰면 근거 없는 약속이 된다.

---

## 4. 열린 구멍 — 이번 워크플로 뒤의 정직한 상태

### G1. Chen 외, Applied Sciences 14(10):4282 (2024, 게재) — 우리의 가장 가까운 선행

- **이전** — MDPI 가 403 을 돌려줘 원문 미확보. LaSen 의 요약을 통한 2차 정보뿐이었다.
- **지금** — ✅ CLOSED — 확보하고 20쪽 전문을 읽었다.
- **어떻게** — Semantic Scholar OA 미러(HTTP 200, application/pdf). MDPI 직접 경로는 여전히 403.
- **무엇이 바뀌었는가** — ⭐ 두 가지가 바뀌었다. ⑴ Chen 은 닫힌 식을 표시하지 않는다 — 우리가 Chen 에게 돌렸던 우선권이 틀렸다. ⑵ Chen 의 표적은 스테퍼 모터 회전 모형이고 드론 로터는 동기로만 나온다.
- **근거** — `{"pdf": "/data/public/sionna_jeong/reference_library/g1g2/chen2024_applsci_14_4282.pdf", "sha256": "59593346f4fc540cfbeb04c81c23483d565205bcc87a15911dbfcda5c5da8472", "license": "CC BY 4.0 (원문 명시)", "json": "outputs/verify_chen.json : acquisition.G1_chen2024"}`
- **정직한 문장** — '우리의 가장 가까운 선행이 2차 정보' 라는 구멍은 닫혔다. 이제 우리는 그 논문을 직접 인용할 수 있고, 실제로 인용하면 우리 이야기가 더 강해진다.

### G2. Abratkiewicz 외, IEEE JSTARS 16:3469-3484 (2023, 게재)

- **이전** — 미확보. 서지정보만 있었고 references.bib 에 '본문 문장 인용 금지' 가 걸려 있었다.
- **지금** — ✅ CLOSED — 확보하고 16쪽 전문을 읽었다. 축자 인용 15건.
- **어떻게** — Crossref 의 link 필드가 실제 파일 경로를 알려줬고, 그 URL 의 Internet Archive 스냅샷(2024-04-15)에서 CC-BY 원본을 받았다. IEEE 직접 경로는 502/202/418 로 전부 막혔다.
- **무엇이 바뀌었는가** — ⭐⭐ 이 라운드의 헤드라인. 우리 v_max 법칙의 진짜 주인이고, 우리가 기록해둔 Chen 귀속조차 한 세대 늦었음이 드러났다. 동시에 그들이 드론을 future work 로 남겼다는 문장을 얻었다.
- **근거** — `{"pdf": "/data/public/sionna_jeong/reference_library/g1g2/abratkiewicz2023_jstars.pdf", "sha256": "7a25893831ae16c1acaa0ae8cbb1d51a6e0f76ca95e5437667265ff527a2631e", "license": "gold OA, CC BY 4.0 (Crossref license 레코드)", "json": "outputs/verify_chen.json : acquisition.G2_abratkiewicz2023"}`
- **정직한 문장** — references.bib 의 인용 금지를 해제하고 DOI 를 채워야 한다.

### G3. 인용 커버리지 — 81개 지면 엔트리 중 축자 인용은 8건

- **이전** — 엔트리 81건 중 축자 인용 8건, 출력 전반에 UNVERIFIED 마커 다수.
- **지금** — ⚠ 부분적으로만 개선. 넓은 코퍼스의 인용 커버리지는 그대로다(PDF 가 디스크에 있는 엔트리 41건). outputs 전체의 UNVERIFIED 마커는 오히려 676개로 늘었다 — 검증이 후퇴해서가 아니라 스윕이 더 돌아 미검증 항목이 더 많이 **드러났기** 때문이다.
- **무엇이 바뀌었는가** — ⭐ 발표가 실제로 인용하는 좁은 코퍼스는 다르다 — 능력 매트릭스 26행 234칸에서 UNVERIFIED 는 0 이고 인용 80건이 매 빌드 재대조된다. 덱은 넓은 코퍼스가 아니라 이 좁은 코퍼스에서만 인용한다.
- **정직한 문장** — '우리 문헌 조사가 검증되었다' 고 말하면 안 된다. '덱이 인용하는 26행은 검증되었고, 배후의 81개 엔트리 대부분은 서지 수준이다' 가 참이다.
- **⭐ 예상 공격** — 그럼 배후 코퍼스의 결론(H8 등)은 어떻게 믿는가.
- **우리 답** — H8 판정은 배후 코퍼스가 아니라 전문 판정 12편에서 나왔고, 그 12편은 PDF 를 열었다. 배후 81 엔트리는 '무엇을 아직 안 읽었는지' 의 지도이지 결론의 근거가 아니다.

### G4. dblp 구조적 사각지대 — IEEE TAP·AWPL·EuCAP·IET RSN·TMTT

- **이전** — 자동 지면 스윕이 dblp 를 썼는데 dblp 는 이 지면들을 색인하지 않는다.
- **지금** — ⚠ 그대로 열려 있다. 이번 라운드가 바꾸지 않았다.
- **뜻** — 이 지면들에서 '못 찾았다' 는 '안 봤다' 라는 뜻이고, 그렇게 말해야 한다. 안테나·전파 지면은 정확히 RCS·회절 논문이 사는 곳이라 사각지대의 방향이 우리에게 가장 나쁘다.
- **정직한 문장** — H8 같은 '없다' 형 주장은 반드시 코퍼스를 명시하고, 이 사각지대를 같은 슬라이드에 적는다.
- **⭐ 예상 공격** — 그러면 novelty 주장을 할 수 없는 것 아닌가.
- **우리 답** — '세계 최초' 는 못 한다. 할 수 있는 것은 '우리가 연 N편의 PDF 안에서, 이 축들을 동시에 채운 것이 없다' 이고, 그 문장은 매트릭스가 그림으로 증명한다. 그리고 EuCAP 은 이미 수동으로 들어와 있다 — Ziganshin 이 우리 최강 경쟁 행이다.

### G5. φ=90° 단일 방위 — 발표된 모든 검출 결과가 한 컷이다

- **이전** — src/experiment_freespace_range.py:322,773 의 phi_deg=90.0 에서 모든 결과가 나왔다.
- **지금** — ⚠ 그대로 열려 있다. 크기는 이번에 계량되었다 — φ=90° 에서 기하 차 0.118 dB, φ 를 쓸면 최대 23.17 dB.
- **우리 표현 정정** — ⭐ '하드코딩' 이 아니라 **기본 인자**다. 결함은 코드가 아니라 보고에 있다 — φ 스윕을 보고한 적이 없다.
- **근거** — `{"json": "outputs/geometry_grid.json : traps[T1b] · range_normalisation.*.absmax_over_phi_db", "code": "src/experiment_freespace_range.py:322,773"}`
- **정직한 문장** — 기하 축의 결론은 φ 를 쓸기 전까지 잠정이다. 슬라이드에 '단일 방위' 를 명시한다.
- **⭐ 예상 공격** — 그러면 지금 발표하는 검출 결과는 다 무효인가.
- **우리 답** — 무효는 아니다 — 무모호 속도 축은 φ 와 무관하고(F10), 링크버짓 축만 φ 에 매달린다. 영향 범위를 그렇게 좁혀 말한다.

### G6. (새로 연) 3GPP 원 규격을 직접 확인하지 않았다

- **이전** — -
- **지금** — ⚠ 새로 명시한 구멍. CSI-RS 최소 주기 500 Hz 는 LaSen 의 TS 38.331 인용과 Chen §3 의 슬롯 목록으로 산술 정합만 확인했고, TS 38.331/38.214 원문은 열지 않았다.
- **정직한 문장** — 슬라이드에서 500 Hz 옆에 '3GPP TS 38.331 (2차 인용)' 을 붙인다.
- **⭐ 예상 공격** — 규격 하나 확인 못 했다는 것인가.
- **우리 답** — 확인할 수 있었지만 이번 라운드에 하지 않았고, 그래서 그렇게 적는다. 그리고 이 값은 우리 결론을 **약하게** 만드는 방향이 아니다 — 실측 상용망은 50~200 Hz 로 더 낮다.

### G7. (새로 연) 바이스태틱 도플러 식의 계보 한 단계 위

- **이전** — -
- **지금** — ⚠ Chen eq.(4) 의 출처인 Samczynski 외, '5G network-based passive radar', IEEE TGRS 2021/2022 원문 미확보. 계보가 한 단계 남았다.
- **정직한 문장** — '이 식의 계보는 바르샤바 학파로 수렴한다' 까지만 말하고, 'Samczynski 가 최초' 라고는 말하지 않는다.
- **⭐ 예상 공격** — 그 위에는 더 없는가.
- **우리 답** — 바이스태틱 도플러는 표준 교재 수준의 식이라 '최초' 를 추적하는 것이 의미가 적다. 우리가 추적하는 것은 **5G 맥락에서 이 한계를 명시한 최초** 이고, 그것이 Abratkiewicz 2023 이다.

---

## 5. 자체검사 — 이 문서가 스스로 확인한 것

| 검사 | 결과 | 내용 |
|---|---|---|
| `V1.LTE CRS` | ✅ | LTE CRS c3e8 우리=40.694520 상류=40.694520 |
| `V1.WiFi VHT-LTF` | ✅ | WiFi VHT-LTF c3e8 우리=14.395393 상류=14.395393 |
| `V1.5G SSB` | ✅ | 5G SSB c3e8 우리=1.071429 상류=1.071429 |
| `V1.WiFi beacon` | ✅ | WiFi beacon c3e8 우리=0.140580 상류=0.140580 |
| `A16.20.0ms` | ✅ | T=20.0 ms 논문=1.0901 우리(c=3e8)=1.0901 |
| `A16.5.0ms` | ✅ | T=5.0 ms 논문=4.3605 우리(c=3e8)=4.3605 |
| `V4.coverage` | ✅ | 천장 10.707 m/s 가 커버하는 기체 0/5 |
| `V4.slowest` | ✅ | 가장 느린 기체 ('typhoonh480_max', 13.5) |
| `V5.zero` | ✅ | 밴드별 |모노-바이β0| = {'wifi': 0.0, 'lte': 0.0, 'nr': 0.0} |
| `V2.po` | ✅ | max|dB| vs 해석 PO = 0.200573 |
| `V3.level` | ✅ | 7기체 레벨 이동 최대 |4.74e-15| dB |
| `F24.band3_keys` | ✅ | 3밴드 적합 기체 7종, 범위 0.7420~1.6994 (기록값 0.7420~1.6994) |
| `F24.two_fits` | ✅ | 3밴드 적합 [0.7419970017631432, 1.6994008126771427] vs 22점 el0 적합 [0.9586804798404873, 1.5421589150245456] |
| `V6.runtime` | ✅ | 몬테카를로 런타임 2716.7 s |
| `V7.dbsm` | ✅ | Sionna 로 dBsm 을 인쇄한 논문 1편 |
| `V7.target` | ✅ | 씬에 표적을 세운 고유 저작 6편 |
| `F16.zero` | ✅ | H8 판정 12편 중 4관문 통과 0편 |
| `F13.no9` | ✅ | 9/9 채운 행 0개, 최다 6/9 |
| `F15.unique` | ✅ | engine+mesh+material+aspect+geometry+vmax 6열 FULL 인 행: ['OURS (sionna2)'] |
| `F14.diffraction` | ✅ | diffraction FULL 3/26 |
| `F12.unverified` | ✅ | UNVERIFIED 0/234, 인용 재대조 80/80 |
| `F11.alias` | ✅ | 접힘비율 5G 0.861 / WiFi 0 / LTE 0 |
| `G5.phi` | ✅ | φ 최대 확산차 23.168839470105702 |
| `F21.no_rcs` | ✅ | sionna.rt 2.0.1: 'rcs' 0회 · 'radar_cross_section' 0회 |
| `F22.has_diffraction` | ✅ | sionna.rt 2.0.1: 'diffract*' 550회 (있다 — 회절이 없다고 말하면 안 된다) |
| `F23.kernel` | ✅ | 우리 RCS 커널의 회절/PTD/UTD/creeping/fringe 출현 0회 |
| `F14b.census` | ✅ | reference_library.json 텍스트의 'wedge' 0회는 유지된다 |
| `Q.A2` | ✅ | A2 조각 대조: The Doppler range is limited by T... |
| `Q.A4` | ✅ | A4 조각 대조: one can obtain the maximum unambiguous bistatic velocity of... |
| `Q.A6` | ✅ | A6 조각 대조: describes how many times the velocity is aliased... |
| `Q.A9` | ✅ | A9 조각 대조: The cooperative target was a car... |
| `Q.A10` | ✅ | A10 조각 대조: drones whose reflectivity is significantly lower than the ca... |
| `Q.A7` | ✅ | A7 조각 대조: The default, and most often used, SSB periodicity is 20 ms... |
| `Q.C4` | ✅ | C4 조각 대조: the maximum unambiguous Doppler frequency is 50 Hz... |
| `Q.C9` | ✅ | C9 조각 대조: resulting in Doppler blur... |
| `Q.C11` | ✅ | C11 조각 대조: a rotating target experimental model employing a stepper mot... |
| `Q.TR47` | ✅ | TR47 조각 대조: is implemented in Sionna... |
| `Q.TAY28` | ✅ | TAY28 조각 대조: The highest SNR is obtained by using all the symbols... |
| `Q.TAY29` | ✅ | TAY29 조각 대조: the ideal gain one could expect would be of 10 log... |
| `Q.TAY.p4` | ✅ | TAY.p4 조각 대조: a DJI Phantom 4 drone evolving above the surveillance antenn... |
| `REC.phantom` | ✅ | Taylor & Poullin 표적은 Phantom 4 다 — 전문에 'Phantom 3' 문자열이 없다(outputs/deepread_reconcile.json 의 'DJI Phantom 3' 기재는 정정 대상) |
| `R10.prf` | ✅ | Chen 2024 전문의 'PRF' 출현 0회 — '같은 기호로 냈다' 는 우리 서술의 반례 |

실패 0건.
