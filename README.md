<!-- 생성물 — `src/make_readme.py` 가 편성에서 읽어 쓴다. 손으로 고치지 말고 그 파일을 고쳐라. -->

# sionna2 — 통신신호를 조명원 삼는 패시브 바이스태틱 드론 탐지 시뮬레이터

셀이 이미 켜 두는 상시 신호(WiFi · LTE · 5G NR)를 조명 삼아 드론을 탐지하는 패시브
바이스태틱 레이더를, Sionna RT 2.0.1 위에서 자유공간 기하로 끝까지 시뮬레이션한다.
표적 산란은 Sionna 의 Mitsuba/OptiX 광선엔진으로 면별 가림을 풀고 그 조명면 위에서
부품별 재질 PO 를 적분해 만든다. σ 의 **주파수 의존성**은 공개 측정(Das)에 맞추고,
**자세 패턴과 절대 레벨은 우리 PO 출력**이다.

보고서는 **본편 13권 · 별편 7편 · 절 102개** 다. **한 권이 물음 하나를 들고, 절 제목이 그 절의
결론 문장**이다 — 목차를 읽는 것이 결론을 읽는 것이다. 사람이 읽는 문서는
`reports/NN_slug.ipynb` 이고, 6권만 그림이 무거워 5편으로 나뉜다 · A권만 그림이 무거워 10편으로 나뉜다. **별편**은 부모 권의 물음에 딸린 답(심화·지원·변주)이고 번호가 부모-K 다. 그림 무게로 나뉜 **분권**은 한 권의 장일 뿐이라 별편과 지위가 다르다. 별편은 부모 권의 목차에 적어 두었다.

## 어디부터 읽어라

본편 13권을 처음부터 읽지 않는다. **읽는 목적이 셋이면 읽는 순서도 셋**이고,
그 갈림길이 [리포트 1 절 1 «열세 권의 지도 — 무엇이 어디에 있나»](reports/01_map.ipynb) 다.

| 무엇을 하려는가 | 어디로 | 얼마나 |
|---|---|---|
| 이 저장소가 무엇을 해냈는지만 알고 싶다 | ↓ **① 빨리 훑기** | 30분 |
| 판정을 검사하려 한다(심사·적대검증) | ↓ **② 왜 믿을 수 있나** | 2시간 |
| 숫자를 재생산하려 한다 | [`docs/REPRODUCE.md`](docs/REPRODUCE.md) — 명령 → 출력 → 소요 | 리포트를 안 읽는다 |
| 원고에 옮기려 한다 | [`docs/paper/`](docs/paper/README.md) — 조각마다 «어디서 왔나» 가 붙어 있다 | — |
| 본편·별편·조각, 층이 왜 이런지 알고 싶다 | [`docs/REPORTS_VOLUMES.md`](docs/REPORTS_VOLUMES.md) | — |

### ① 빨리 훑기 — 30분

본편 권마다 결론 절 하나씩이다. **오른쪽 칸이 그 절의 결론 문장 전체**이므로, 제목만
읽어도 한 바퀴가 돈다. 막히는 데서만 그 절을 연다. 별편의 결론은 아래 목차의 별편 표에 있다.

| 권 | 절 | 이 절이 낸 결론 |
|---|---|---|
| [1 «이 연구가 묻는 것과 답한 방식»](reports/01_map.ipynb) | [절 3](reports/01_map.ipynb) | 주장마다 판정 범위를 결판·사슬확인·캠페인 밖으로 적었다 |
| [2 «우리 커널 — 무엇이고, 무엇이 아닌가»](reports/02_kernel.ipynb) | [절 4](reports/02_kernel.ipynb) | 해석 PO 구 대비 구현오차는 kr 전 구간에서 λ/16 격자 0.201 dB · 생산 λ/12 격자 0.254 dB 안이다 |
| [3 «σ 를 무엇에 붙들어 매나»](reports/03_anchor.ipynb) | [절 1](reports/03_anchor.ipynb) | σ = A(f)·B₁·B₂ 에서 A(f) 의 기울기만 측정에서 받고, 레벨과 각패턴은 우리 SBR+PO 커널(B) 출력이다 |
| [4 «앙각 커버리지 — 어느 각도까지 유효한가»](reports/04_elevation-coverage.ipynb) | [절 2](reports/04_elevation-coverage.ipynb) | −75° 에서 추적 대역 몫은 고정 대역보다 38.55 dB 크고, 그 차이를 만든 것은 대역을 어디에 놓았는가 하나다 |
| [5 «엔진의 물리 스위치 — 켜면 무엇이 달라지나»](reports/05_engine-physics.ipynb) | [절 1](reports/05_engine-physics.ipynb) | 나딧에서 레벨을 −130.78 dB 에서 −64.23 dB 로 올리는 스위치는 회절 하나다 |
| [6 «마이크로도플러 — 도는 로터가 남기는 무늬»](reports/06_1_scene.ipynb) | [절 3](reports/06_3_pattern.ipynb) | 두 엔진이 날개끝 주파수 아래에서 겹치고 그 위에서 갈린다 |
| [7 «무엇을 조명원으로 쓸 수 있나»](reports/07_illuminators.ipynb) | [절 3](reports/07_illuminators.ipynb) | 여섯 항목은 닫힌형이고, 점유 대가만 몬테카를로 격자에서 읽는다 |
| [8 «처리 사슬 — 직접파를 죽이고 표적을 세운다»](reports/08_detector.ipynb) | [절 3](reports/08_detector.ipynb) | 운용 형상에서 경험 Pfa 를 재니 명목값의 1.52~2.66 배였다 |
| [9 «관측가능성과 기하 — 어디에 서야 보이나»](reports/09_observability.ipynb) | [절 1](reports/09_observability.ipynb) | 한 순간의 (R_b, f_d) 는 랭크 2 이고, 수신기를 하나 더하면 위치가 풀린다 |
| [10 «결과 — 얼마나 멀리서 보이나»](reports/10_results.ipynb) | [절 2](reports/10_results.ipynb) | 앵커 σ 위의 R90 은 비교가능 12칸에서 3.69~7.44 km 이고, 밴드 순서는 기체마다 바뀐다 |
| [11 «실측 계획 — 무엇을 재야 이 문서가 닫히나»](reports/11_measurement.ipynb) | [절 6](reports/11_measurement.ipynb) | 캠페인이 결판내는 양은 절대값이 아니라 순위다 |

### ② 왜 믿을 수 있나 — 2시간

검증·대조·반증 절만 모았다. 뼈대는 **눈감기 대조 · 사전등록 채점 · PREMATURE 판정 ·
널 교정** 넷이다 — 우리가 틀렸을 수 있는 자리를 우리가 먼저 때린 절들이다.

| 권·절 | 무엇을 때렸나 |
|---|---|
| [리포트 2-2 절 1](reports/02_2_stock-engine.ipynb) | Sionna 기술보고서 59쪽에 physical optics 는 0회, SBR 은 44회 나온다 |
| [리포트 2-2 절 4](reports/02_2_stock-engine.ipynb) | 필드 갱신 인자 여덟 개에 면적·곡률·치수·λ 가 없다 |
| [리포트 2-2 절 5](reports/02_2_stock-engine.ipynb) | 면적을 1600배로 키워도 경로 진폭은 7.4e-07 dB 움직인다 |
| [리포트 2 절 4](reports/02_kernel.ipynb) | 해석 PO 구 대비 구현오차는 kr 전 구간에서 λ/16 격자 0.201 dB · 생산 λ/12 격자 0.254 dB 안이다 |
| [리포트 2 절 5](reports/02_kernel.ipynb) | PO 유효 무릎을 부품 폭으로 옮기면 어느 부품이 어느 밴드에서 떨어지는지가 보인다 |
| [리포트 3 절 3](reports/03_anchor.ipynb) | Phantom 3 를 문헌값을 보지 않고 내고 봉인을 풀었다 |
| [리포트 3 절 4](reports/03_anchor.ipynb) | 메쉬가 사는 축은 절대 크기가 아니라 각도 구조다 |
| [리포트 3 절 5](reports/03_anchor.ipynb) | 같은 잣대를 네 기체로 넓히면 판정이 NOT_VALIDATED 로 갈린다 |
| [리포트 3 절 6](reports/03_anchor.ipynb) | 공통모드 σ 오차는 파형 순위를 안 건드리고, 차분 오차가 뒤집는다 |
| [리포트 3-2 절 4](reports/03_2_size-law.ipynb) | 이 답을 아직 결론이라고 부를 수 없는 이유가 일곱 가지이고, 그중 둘이 치명적이다 |
| [리포트 6-6 절 2](reports/06_6_microdoppler-limits.ipynb) | 문턱은 널 팔이 교정했고, 가장자리 시험은 아직 교정되지 않았다 |
| [리포트 8 절 3](reports/08_detector.ipynb) | 운용 형상에서 경험 Pfa 를 재니 명목값의 1.52~2.66 배였다 |
| [리포트 8 절 4](reports/08_detector.ipynb) | 그 배율의 원인은 셀 상관이고, 교정표는 형상마다 다시 재야 한다 |
| [리포트 10 절 3](reports/10_results.ipynb) | 그 순위는 자세평균이면 하나로 모이고, 자세평균 뒤집힘 문턱은 현실 봉투 안이다 |
| [리포트 10 절 5](reports/10_results.ipynb) | 모호속도는 표본화율의 성질이라 CPI 와 무관한 상한이다 |
| [리포트 11 절 7](reports/11_measurement.ipynb) | 기울기 판정의 문턱은 세션간 진폭 재현성이고, σ 사슬 세대를 바꾸면 그 문턱이 손닿는 범위 밖으로 좁아진다 |

---

## 이 저장소가 한 일

| 한 일 | 수치 | 어느 절 |
|---|---|---|
| **광선엔진 안에서 산란을 적분한다** — Sionna 자체 Mitsuba/OptiX 로 first-hit 가림을 판정하고 조명면 위에서 부품별 재질 PO 를 적분한다 | `src/rcs_sbr.py:184` · `src/materials.py` | [리포트 2 절 1 «가림 판정은 Sionna 광선엔진이 하고, 면적분은…»](reports/02_kernel.ipynb) |
| **커널을 기준해로 검증했다** — 해석 PO 구 대비 kr 1~100 전 구간 | 최대 0.201 dB [^1] | [리포트 2 절 4 «해석 PO 구 대비 구현오차는 kr 전 구간에서 λ/…»](reports/02_kernel.ipynb) |
| **다중반사 위상을 PEC 이면각 닫힌형 8πa²b²/λ² 와 맞췄다** — 변 길이 4점 | 최대 0.556 dB [^2] | [리포트 2 절 4 «해석 PO 구 대비 구현오차는 kr 전 구간에서 λ/…»](reports/02_kernel.ipynb) |
| **바이스태틱 출사 가시성을 넣었다** — 히트마다 수신기 방향으로 그림자 광선을 쏜다 | 상반성 위반 최악 9.69 [^3] → 8.24 dB [^4] | [리포트 2 절 3 «수신 방향 그림자 광선을 켜면 상반성 위반이 9.69…»](reports/02_kernel.ipynb) |
| **σ 의 주파수 기울기를 측정에 정렬했다** — σ = A(f)·B₁·B₂ 에서 A(f) 의 **기울기만** 측정, **절대 레벨과 B₁ 은 우리 PO 출력** | 0.210 dB/GHz [^5] · 평균 레벨이동 0.00 dB [^6] · 정규화 각패턴 이동 1.9e-15 dB [^7] | [리포트 3 절 1 «σ = A(f)·B₁·B₂ 에서 A(f) 의 기울기만…»](reports/03_anchor.ipynb) |
| **모드 선택의 대가를 수치로 적었다** — 레벨까지 앵커에 맞추려면 크기전이 법칙을 하나 골라야 하고, 그 선택 하나가 기체당 최대 이만큼을 정한다 | L² ↔ L⁴ 예측 차 최대 9.50 dB [^8] | [리포트 3 절 2 «앵커가 통제한 항목과 남은 항목의 크기를 기체별 원장…»](reports/03_anchor.ipynb) |
| **우리 σ 를 눈감고 내고 봉인을 풀었다** — 문헌 상수를 한 번도 안 읽은 경로로 Phantom 3 를 내고 별도 스크립트가 열었다 | 사전등록 판정 NOT_VALIDATED (P3 산포) [^9] | [리포트 3 절 5 «같은 잣대를 네 기체로 넓히면 판정이 NOT_VALI…»](reports/03_anchor.ipynb) |
| **CFAR 를 경험 Pfa 로 교정했다** — GPU 몬테카를로로 오경보 셀을 직접 세었다 | 2,717 s [^10], 명목 1e-4 에서 배율을 형상마다 다시 잰다 | [리포트 8 절 3 «운용 형상에서 경험 Pfa 를 재니 명목값의 1.52…»](reports/08_detector.ipynb) |
| **세 파형을 한 표적·한 검출기로 비교했다** — 점유·대역·PRF·λ² 를 dB 원장으로 닫았다 | 점유 18.0 dB [^11] | [리포트 7 절 3 «여섯 항목은 닫힌형이고, 점유 대가만 몬테카를로 격자…»](reports/07_illuminators.ipynb) |
| **기체 7종을 사진·제원에서 세우고 실물 CAD 와 맞댔다** | 메쉬 7 종 [^12] · 삼각형 207,268 개 [^13] | [리포트 2-3 절 2 «메쉬 외형이 실제 기체와 얼마나 맞는지를 사진 IoU…»](reports/02_3_target-mesh.ipynb) |
| **선행연구를 전문으로 판정했다** — 아카이브 PDF 41편 중 16편, 게재상태는 PDF 로 확정 | 드론 메쉬에서 산란을 계산한 게재본 0 편 [^14] | [리포트 1-2 절 1 «전문 판정한 게재본 중 드론 메쉬 산란을 엔진 안에서…»](reports/01_2_prior-work.ipynb) |

---

## 목차 — 본편 13권 + 별편 7편

권마다 답하는 물음이 하나다. 절 제목은 그 절의 **결론 문장** 그대로다.

| 권 | 이 권이 답하는 물음 | 절 | 그림 |
|---|---|---|---|
| [1 «이 연구가 묻는 것과 답한 방식»](#권-1-이-연구가-묻는-것과-답한-방식) | 패시브 바이스태틱으로 드론을 탐지하고 마이크로도플러로 분류하는 것이 태스크이고, RCS 는 그 인프라다. 이 권은 나머지 열두… | 3 | 1 |
| [2 «우리 커널 — 무엇이고, 무엇이 아닌가»](#권-2-우리-커널--무엇이고-무엇이-아닌가) | SBR + 물리광학이 무엇을 계산하고 무엇을 계산하지 않는지를 정의하고, 해석해가 있는 과녁(구·평판·이면각)으로 잰다. | 6 | 2 |
| [3 «σ 를 무엇에 붙들어 매나»](#권-3-σ-를-무엇에-붙들어-매나) | 우리 σ 의 절대 레벨을 붙드는 것은 공개 문헌 한 기체·한 실험실뿐이다. 그 끈의 장력을 재고, 끊어질 자리를 먼저 적는다. | 6 | 2 |
| [4 «앙각 커버리지 — 어느 각도까지 유효한가»](#권-4-앙각-커버리지--어느-각도까지-유효한가) | 관측 앙각을 0° 에서 −90° 까지 내리며 같은 표적을 재면, 커버리지를 정하는 것은 표적이 아니라 우리가 고른 분석 대역과… | 5 | 9 |
| [5 «엔진의 물리 스위치 — 켜면 무엇이 달라지나»](#권-5-엔진의-물리-스위치--켜면-무엇이-달라지나) | 스톡 PathSolver 의 굴절·회절·모서리회절·다중반사를 하나씩 켜서 무엇이 결과를 만들었는지 귀속한다. 나딧에서 레벨을 6… | 5 | 6 |
| [6 «마이크로도플러 — 도는 로터가 남기는 무늬»](#권-6-마이크로도플러--도는-로터가-남기는-무늬) | 호버링하는 드론은 제자리에 있지만 프로펠러는 돈다. 그 회전이 남기는 시간-주파수 무늬가 이 연구의 분류 축이다. 그림이 무거워… | 6 | 21 |
| [7 «무엇을 조명원으로 쓸 수 있나»](#권-7-무엇을-조명원으로-쓸-수-있나) | LTE·5G·WiFi 가 각각 얼마나 자주, 얼마나 넓게 신호를 내주는가. 5G 는 대역이 넓은 대신 상시 신호가 드물어 이중고… | 7 | 7 |
| [8 «처리 사슬 — 직접파를 죽이고 표적을 세운다»](#권-8-처리-사슬--직접파를-죽이고-표적을-세운다) | ECA 로 직접파를 지우고 CFAR 로 문턱을 세운다. 문턱을 어디에 두느냐가 결과를 정하므로 그 교정을 먼저 적는다. | 4 | 5 |
| [9 «관측가능성과 기하 — 어디에 서야 보이나»](#권-9-관측가능성과-기하--어디에-서야-보이나) | 송신기·수신기·표적의 배치가 검출을 정한다. 볼 수 없는 자리를 먼저 지도로 그리고, 그 다음에 거리를 말한다. | 4 | 4 |
| [10 «결과 — 얼마나 멀리서 보이나»](#권-10-결과--얼마나-멀리서-보이나) | R90 과 순위가 이 연구의 정량 결론이다. 적분시간·잔류·σ 가정을 흔들어 순위가 견디는지까지 함께 적는다. | 5 | 4 |
| [11 «실측 계획 — 무엇을 재야 이 문서가 닫히나»](#권-11-실측-계획--무엇을-재야-이-문서가-닫히나) | 시뮬레이션이 선언으로 남겨 둔 것들의 목록과, 그것을 닫는 야외 실측 규약이다. | 7 | 4 |
| [12 «실외 장면 — 지면과 벽이 서면 무엇이 달라지나»](#권-12-실외-장면--지면과-벽이-서면-무엇이-달라지나) | 자유공간에서 세운 판정이 지면과 건물이 있는 자리에서도 서는지 묻는다. 실외 기록의 날개 박자는 솔버 인공물에 가려 있었고, 그… | 0 | 2 |
| [A «도감 — 원장의 모든 팔을 그림으로»](#권-a-도감--원장의-모든-팔을-그림으로) | 앙각 스윕 원장이 담은 팔 전부를 STFT 맵과 대역 에너지로 펴 둔 재고 목록이다. 판정하지 않는다 — 어느 팔이 무엇을 담고… | 14 | 961 |

**별편** — 부모 권의 물음에 딸린 답이다. 그림 무게로 나뉜 분권과 달리 번호가 부모-K 다.

| 별편 | 부모 권 | 무엇을 다루나 |
|---|---|---|
| [1-2 «선행연구는 어디까지 왔고 우리는 어디 서는가»](reports/01_2_prior-work.ipynb) | 1 | 공개 문헌과 오픈소스를 전수로 세어, 우리가 새로 하는 것과 빌려 쓰는 것을 갈라 적는다 |
| [2-2 «스톡 Sionna 로는 왜 부족한가»](reports/02_2_stock-engine.ipynb) | 2 | 스톡 레이 트레이서는 경로를 풀지 산란적분을 하지 않는다. 그 한 가지가 드론처럼 작은 표적에서 무엇을 무너뜨리는지 여덟 갈래로… |
| [2-3 «표적을 짓는다 — 메쉬와 재질»](reports/02_3_target-mesh.ipynb) | 2 | 기체 10 대를 CAD 로 짓고, 그중 σ 를 내는 7 대를 실물 사진·도면과 대조한다. 재질은 측정이 아니라 선언이고, 그 선… |
| [3-2 «표적을 얼마나 거칠게 그려도 되나 — 사다리와 크기 법칙»](reports/03_2_size-law.ipynb) | 3 | 표적 모형을 구·정육면체·상자·평판으로 갈아 끼우는 사다리로 단순화의 값을 재고, 앵커보다 크고 작은 두 기체로 크기전이 법칙을… |
| [5-2 «물리 스위치 격자 — 회절은 리듬을 지우지 않고 리듬 없는 에코로 덮는다»](reports/05_2_switch-grid.ipynb) | 5 | 5 권이 단일축으로 귀속한 회절을 굴절·회절·모서리회절 7 조합 전수 격자로 다시 재고, 절대 세기로 읽어 기전을 가른다 — 회… |
| [6-6 «마이크로도플러 — 무엇이 그 무늬를 흐리나»](reports/06_6_microdoppler-limits.ipynb) | 6 | 자세·보정·광선 예산·표본율 네 가지가 무늬를 지운다. 각각을 단일축으로 갈라 얼마나 지우는지 잰다 |
| [10-2 «결론이 무엇에 기대고 있나 — 강건성과 하드웨어»](reports/10_2_robustness.ipynb) | 10 | 표적 모형·수신 소자·장비를 바꿔 넣어 결론이 어디서 흔들리는지 본다 |

셀 2896개 · 각주 2424개 · 그림 1045장. 절 단위 목차는 [`reports/README.md`](reports/README.md) 에도 있다.

### 권 1 «이 연구가 묻는 것과 답한 방식»

패시브 바이스태틱으로 드론을 **탐지하고 마이크로도플러로 분류**하는 것이 태스크이고, RCS 는 그 인프라다. 이 권은 나머지 열두 권과 거기 딸린 별편들의 지도다.

→ [`reports/01_map.ipynb`](reports/01_map.ipynb)

| 절 | 이 절의 결론 |
|---|---|
| [1](reports/01_map.ipynb) | 열세 권의 지도 — 무엇이 어디에 있나 |
| [2](reports/01_map.ipynb) | 네 관문을 동시에 통과한 게재본은 0편이고, 최근접 3편은 각각 다른 관문에서 걸린다 |
| [3](reports/01_map.ipynb) | 주장마다 판정 범위를 결판·사슬확인·캠페인 밖으로 적었다 |

별편이 한 편 딸려 있다.

- [1-2 «선행연구는 어디까지 왔고 우리는 어디 서는가»](reports/01_2_prior-work.ipynb) (빌더 `src/build_volumes.py (조각 조립)`) — 공개 문헌과 오픈소스를 전수로 세어, 우리가 새로 하는 것과 빌려 쓰는 것을 갈라 적는다.

### 별편 1-2 «선행연구는 어디까지 왔고 우리는 어디 서는가»

[권 1 «이 연구가 묻는 것과 답한 방식»](#권-1-이-연구가-묻는-것과-답한-방식) 의 **별편**이다.

공개 문헌과 오픈소스를 전수로 세어, 우리가 **새로 하는 것과 빌려 쓰는 것**을 갈라 적는다.

→ [`reports/01_2_prior-work.ipynb`](reports/01_2_prior-work.ipynb)

| 절 | 이 절의 결론 |
|---|---|
| [1](reports/01_2_prior-work.ipynb) | 전문 판정한 게재본 중 드론 메쉬 산란을 엔진 안에서 «검증» 한 것은 0편이다 |
| [2](reports/01_2_prior-work.ipynb) | 프리프린트는 따로 세고, Ziganshin 은 두 판을 구별해 인용한다 |
| [3](reports/01_2_prior-work.ipynb) | 표적 서명을 어디서 조달했는지가 그 논문이 낼 수 있는 주장의 크기를 정한다 |
| [4](reports/01_2_prior-work.ipynb) | 조달처 일곱 갈래 R1~R7 을 전수로 적었다 |
| [5](reports/01_2_prior-work.ipynb) | 외부 σ 주입은 게재돼 있고, 그 값의 대가는 검증이 치른다 |
| [6](reports/01_2_prior-work.ipynb) | 선행에서 빌린 절차와 아직 안 빌린 절차를 비용과 함께 센다 |

### 권 2 «우리 커널 — 무엇이고, 무엇이 아닌가»

SBR + 물리광학이 무엇을 계산하고 무엇을 **계산하지 않는지**를 정의하고, 해석해가 있는 과녁(구·평판·이면각)으로 잰다.

→ [`reports/02_kernel.ipynb`](reports/02_kernel.ipynb)

| 절 | 이 절의 결론 |
|---|---|
| [1](reports/02_kernel.ipynb) | 가림 판정은 Sionna 광선엔진이 하고, 면적분은 우리 커널이 한다 |
| [2](reports/02_kernel.ipynb) | 스톡 솔버와 맞대면 «면이 많아서 에코가 커진다» 가설은 반증되고, 런타임의 96.9% 는 호스트가 쓴다 |
| [3](reports/02_kernel.ipynb) | 수신 방향 그림자 광선을 켜면 상반성 위반이 9.69 → 8.24 dB 로 내려간다 |
| [4](reports/02_kernel.ipynb) | 해석 PO 구 대비 구현오차는 kr 전 구간에서 λ/16 격자 0.201 dB · 생산 λ/12 격자 0.254 dB 안이다 |
| [5](reports/02_kernel.ipynb) | PO 유효 무릎을 부품 폭으로 옮기면 어느 부품이 어느 밴드에서 떨어지는지가 보인다 |
| [6](reports/02_kernel.ipynb) | 커널이 아직 못 하는 것은 편파 분리·PTD·재테셀레이션·다중반사 Γ(θ) 넷이고, 각각의 크기를 적었다 |

별편이 두 편 딸려 있다.

- [2-2 «스톡 Sionna 로는 왜 부족한가»](reports/02_2_stock-engine.ipynb) (빌더 `src/build_volumes.py (조각 조립)`) — 스톡 레이 트레이서는 경로를 풀지 산란적분을 하지 않는다. 그 한 가지가 드론처럼 작은 표적에서 무엇을 무너뜨리는지 여덟 갈래로 잰다.
- [2-3 «표적을 짓는다 — 메쉬와 재질»](reports/02_3_target-mesh.ipynb) (빌더 `src/build_volumes.py (조각 조립)`) — 기체 10 대를 CAD 로 짓고, 그중 σ 를 내는 7 대를 실물 사진·도면과 대조한다. 재질은 측정이 아니라 선언이고, 그 선언이 어디까지 미치는지 함께 적는다.

### 별편 2-2 «스톡 Sionna 로는 왜 부족한가»

[권 2 «우리 커널 — 무엇이고, 무엇이 아닌가»](#권-2-우리-커널--무엇이고-무엇이-아닌가) 의 **별편**이다.

스톡 레이 트레이서는 경로를 풀지 **산란적분을 하지 않는다**. 그 한 가지가 드론처럼 작은 표적에서 무엇을 무너뜨리는지 여덟 갈래로 잰다.

→ [`reports/02_2_stock-engine.ipynb`](reports/02_2_stock-engine.ipynb)

| 절 | 이 절의 결론 |
|---|---|
| [1](reports/02_2_stock-engine.ipynb) | Sionna 기술보고서 59쪽에 physical optics 는 0회, SBR 은 44회 나온다 |
| [2](reports/02_2_stock-engine.ipynb) | 경로는 SBR 과 이미지법이 정한다 |
| [3](reports/02_2_stock-engine.ipynb) | 진폭은 국소 평면파–평면경계 해 하나로 만들어진다 |
| [4](reports/02_2_stock-engine.ipynb) | 필드 갱신 인자 여덟 개에 면적·곡률·치수·λ 가 없다 |
| [5](reports/02_2_stock-engine.ipynb) | 면적을 1600배로 키워도 경로 진폭은 7.4e-07 dB 움직인다 |
| [6](reports/02_2_stock-engine.ipynb) | 표적 항이 비에서 소거되는가와 절대값이 필요한가, 두 물음이 실험을 네 칸으로 가른다 |
| [7](reports/02_2_stock-engine.ipynb) | 완전파는 정확도의 과녁이고, SBR+PO 는 표를 만들 수 있는 비용대에서 가장 정확하다 |

### 별편 2-3 «표적을 짓는다 — 메쉬와 재질»

[권 2 «우리 커널 — 무엇이고, 무엇이 아닌가»](#권-2-우리-커널--무엇이고-무엇이-아닌가) 의 **별편**이다.

기체 10 대를 CAD 로 짓고, 그중 σ 를 내는 7 대를 실물 사진·도면과 대조한다. **재질은 측정이 아니라 선언**이고, 그 선언이 어디까지 미치는지 함께 적는다.

→ [`reports/02_3_target-mesh.ipynb`](reports/02_3_target-mesh.ipynb)

| 절 | 이 절의 결론 |
|---|---|
| [1](reports/02_3_target-mesh.ipynb) | 기체 7종을 제원과 제조사 CAD 치수에서 세우고 부품을 재질 그룹으로 유지했다 |
| [2](reports/02_3_target-mesh.ipynb) | 메쉬 외형이 실제 기체와 얼마나 맞는지를 사진 IoU·CAD 치수·실물 스캔 세 자로 쟀다 |
| [3](reports/02_3_target-mesh.ipynb) | 도전성 재질이 면적의 45.3% 로 Σ\|Γ\|A 의 73.5% 를 낸다 |

### 권 3 «σ 를 무엇에 붙들어 매나»

우리 σ 의 절대 레벨을 붙드는 것은 **공개 문헌 한 기체·한 실험실**뿐이다. 그 끈의 장력을 재고, 끊어질 자리를 먼저 적는다.

→ [`reports/03_anchor.ipynb`](reports/03_anchor.ipynb)

| 절 | 이 절의 결론 |
|---|---|
| [1](reports/03_anchor.ipynb) | σ = A(f)·B₁·B₂ 에서 A(f) 의 기울기만 측정에서 받고, 레벨과 각패턴은 우리 SBR+PO 커널(B) 출력이다 |
| [2](reports/03_anchor.ipynb) | 앵커가 통제한 항목과 남은 항목의 크기를 기체별 원장으로 적었다 |
| [3](reports/03_anchor.ipynb) | Phantom 3 를 문헌값을 보지 않고 내고 봉인을 풀었다 |
| [4](reports/03_anchor.ipynb) | 메쉬가 사는 축은 절대 크기가 아니라 각도 구조다 |
| [5](reports/03_anchor.ipynb) | 같은 잣대를 네 기체로 넓히면 판정이 NOT_VALIDATED 로 갈린다 |
| [6](reports/03_anchor.ipynb) | 공통모드 σ 오차는 파형 순위를 안 건드리고, 차분 오차가 뒤집는다 |

별편이 한 편 딸려 있다.

- [3-2 «표적을 얼마나 거칠게 그려도 되나 — 사다리와 크기 법칙»](reports/03_2_size-law.ipynb) (빌더 `src/build_volumes.py (조각 조립)`) — 표적 모형을 구·정육면체·상자·평판으로 갈아 끼우는 사다리로 단순화의 값을 재고, 앵커보다 크고 작은 두 기체로 크기전이 법칙을 가르는 계획을 적는다. 사다리의 답이 이르게 나오면 그것부터 의심한다.

### 별편 3-2 «표적을 얼마나 거칠게 그려도 되나 — 사다리와 크기 법칙»

[권 3 «σ 를 무엇에 붙들어 매나»](#권-3-σ-를-무엇에-붙들어-매나) 의 **별편**이다.

표적 모형을 구·정육면체·상자·평판으로 갈아 끼우는 사다리로 **단순화의 값**을 재고, 앵커보다 크고 작은 두 기체로 **크기전이 법칙**을 가르는 계획을 적는다. **사다리의 답이 이르게 나오면 그것부터 의심한다.**

→ [`reports/03_2_size-law.ipynb`](reports/03_2_size-law.ipynb)

| 절 | 이 절의 결론 |
|---|---|
| [1](reports/03_2_size-law.ipynb) | 사다리가 하나가 아니라 셋이었다 — 여섯 단이 서로 다른 운동학을 쓰고 있었다 |
| [2](reports/03_2_size-law.ipynb) | 몸통은 진짜 CAD, 프로펠러만 갈아 끼운 교정 사다리가 답할 자격이 있는 유일한 축이다 |
| [3](reports/03_2_size-law.ipynb) | 모양의 유무는 수십 dB 를 가르고, 모양의 정밀도는 한 자릿수 dB 안에서 논다 |
| [4](reports/03_2_size-law.ipynb) | 이 답을 아직 결론이라고 부를 수 없는 이유가 일곱 가지이고, 그중 둘이 치명적이다 |
| [5](reports/03_2_size-law.ipynb) | 두 기체를 함께 재면 크기전이 법칙이 차등신호의 부호 하나로 갈린다 |

### 권 4 «앙각 커버리지 — 어느 각도까지 유효한가»

관측 앙각을 0° 에서 −90° 까지 내리며 같은 표적을 재면, 커버리지를 정하는 것은 표적이 아니라 **우리가 고른 분석 대역과 잣대**다. 대역을 날개끝 주파수를 따라 옮기면 −75° 에서도 프로펠러 대역이 살아 있고, 8/11 덱의 대역을 고정한 채 내려가면 같은 자리가 바닥에 앉는다. 잣대를 고를 때마다 **광선 예산이 함께 움직인다**는 것이 이 권의 두 번째 결론이다. 여기서 재는 무늬 축의 정의는 **리포트 6** 에 있다.

→ [`reports/04_elevation-coverage.ipynb`](reports/04_elevation-coverage.ipynb)

| 절 | 이 절의 결론 |
|---|---|
| [1](reports/04_elevation-coverage.ipynb) | 앙각 7 점을 15 m 한 자리에서 광선 40 억 발로 재고, 77 행이 모두 완결이다 |
| [2](reports/04_elevation-coverage.ipynb) | −75° 에서 추적 대역 몫은 고정 대역보다 38.55 dB 크고, 그 차이를 만든 것은 대역을 어디에 놓았는가 하나다 |
| [3](reports/04_elevation-coverage.ipynb) | 물리 상한 위 누설은 우리 팔(λ/12 격자) 0.22~17.18 %, 스톡 PathSolver 0.81~96.17 % 이고, 물리를 켜면 여섯 앙각이 전부 78 % 위다 |
| [4](reports/04_elevation-coverage.ipynb) | 나딧 잔여의 64 % 는 광선 격자 표본화 잡음이고, 널은 나딧 −49.18 dB 에서 10° −23.73 dB 로 완만히 차는 얕은 웅덩이다 |
| [5](reports/04_elevation-coverage.ipynb) | el 0 에서 광선을 360 배 늘리면 정지 성분은 0.03 dB 안에 모이고, 같은 한 계단이 el −75 의 레벨을 12.55 dB 옮긴다 |

### 권 5 «엔진의 물리 스위치 — 켜면 무엇이 달라지나»

스톡 PathSolver 의 굴절·회절·모서리회절·다중반사를 하나씩 켜서 **무엇이 결과를 만들었는지 귀속**한다. 나딧에서 레벨을 66 dB 올리는 것은 회절 하나이고, 그 상승은 표적 변조(분자)가 아니라 정적 성분(분모)을 키운다. 스위치가 남기는 몫은 **광선 예산을 맞춘 뒤에야** 읽을 수 있고, 이 비교가 세우는 것은 상대량뿐이다 — 절대 σ 는 이 권 밖이다. 여기서 재는 무늬 축의 정의는 **리포트 6** 에 있다.

→ [`reports/05_engine-physics.ipynb`](reports/05_engine-physics.ipynb)

| 절 | 이 절의 결론 |
|---|---|
| [1](reports/05_engine-physics.ipynb) | 나딧에서 레벨을 −130.78 dB 에서 −64.23 dB 로 올리는 스위치는 회절 하나다 |
| [2](reports/05_engine-physics.ipynb) | AC/DC 가 +0.89 dB 에서 −68.13 dB 로 내려간 것은 분모가 66.55 dB 이상 커진 결과다 |
| [3](reports/05_engine-physics.ipynb) | 광선을 250M 으로 맞추면 물리 스위치가 상한 위 몫에 남기는 것은 앙각 0° 에서 0.00084 이고, 기울인 세 앙각에서 0.55~0.77 다 |
| [4](reports/05_engine-physics.ipynb) | 우리 커널은 덱 3~40 m 판과 0.9141~0.9877 로 겹치고, 엔진이 바뀐 3 칸은 0.6291~0.6961 다 |
| [5](reports/05_engine-physics.ipynb) | 이 비교가 세우는 것은 el −90 한 자리의 스위치 귀속이고, 절대 σ 는 산포 16.27 dB 로 미검증이다 |

별편이 한 편 딸려 있다.

- [5-2 «물리 스위치 격자 — 회절은 리듬을 지우지 않고 리듬 없는 에코로 덮는다»](reports/05_2_switch-grid.ipynb) (빌더 `src/build_report18_switch_grid.py`) — 5 권이 단일축으로 귀속한 회절을 굴절·회절·모서리회절 7 조합 전수 격자로 다시 재고, 절대 세기로 읽어 기전을 가른다 — 회절을 켠 판은 끈 판을 계수 ≈1 로 품고 있고, 날개끝 위 바닥이 올라와 원래 빗살을 덮는다(빗각 −15°~−75°).

### 권 6 «마이크로도플러 — 도는 로터가 남기는 무늬»

호버링하는 드론은 제자리에 있지만 **프로펠러는 돈다**. 그 회전이 남기는 시간-주파수 무늬가 이 연구의 분류 축이다. 그림이 무거워 **다섯 편**으로 나뉜다.

→ [`reports/06_1_scene.ipynb`](reports/06_1_scene.ipynb)

이 5편은 `src/make_report08_microdoppler.py (06_5 만 src/make_report07b_bistatic.py)` 가 짓는다.

| 편 | 무엇에 답하나 |
|---|---|
| [`06_1_scene.ipynb`](reports/06_1_scene.ipynb) | 무엇을 보고 있나 — 시나리오와 신호의 정체 |
| [`06_2_engines.ipynb`](reports/06_2_engines.ipynb) | 어떻게 계산하나 — 세 엔진과 거리 |
| [`06_3_pattern.ipynb`](reports/06_3_pattern.ipynb) | 무엇이 무늬를 정하나 — 회전수·가림·산포 |
| [`06_4_sampling.ipynb`](reports/06_4_sampling.ipynb) | 무엇을 잴 수 있나 — 광선 비용과 반복률 |
| [`06_5_bistatic.ipynb`](reports/06_5_bistatic.ipynb) | 송수신이 갈라지면 — 바이스태틱 도플러·플래시·에코 |

아래 절은 [`06_3_pattern.ipynb`](reports/06_3_pattern.ipynb) 에 이어 붙어 있다.

| 절 | 이 절의 결론 |
|---|---|
| [1](reports/06_3_pattern.ipynb) | 스톡 Paths.doppler 로는 블레이드 변조가 안 나온다 — SceneObject.velocity 가 객체당 강체 1벡터다 |
| [2](reports/06_3_pattern.ipynb) | 시간표본마다 자세를 새로 놓고 다시 쏘아 슬로타임 복소열을 만든다 |
| [3](reports/06_3_pattern.ipynb) | 두 엔진이 날개끝 주파수 아래에서 겹치고 그 위에서 갈린다 |
| [4](reports/06_3_pattern.ipynb) | 네 로터가 같은 회전수로 돌면 무늬는 시간에 못 변한다 |
| [5](reports/06_3_pattern.ipynb) | 동체가 날개를 가리면 변조 깊이와 레벨이 함께 바뀐다 |
| [6](reports/06_3_pattern.ipynb) | 블레이드 신호는 약하지 않다 — 동체 정적 반사가 덮고 있을 뿐이다 |

별편이 한 편 딸려 있다.

- [6-6 «마이크로도플러 — 무엇이 그 무늬를 흐리나»](reports/06_6_microdoppler-limits.ipynb) (빌더 `src/build_volumes.py (조각 조립)`) — 자세·보정·광선 예산·표본율 네 가지가 무늬를 지운다. 각각을 단일축으로 갈라 얼마나 지우는지 잰다.

### 별편 6-6 «마이크로도플러 — 무엇이 그 무늬를 흐리나»

[권 6 «마이크로도플러 — 도는 로터가 남기는 무늬»](#권-6-마이크로도플러--도는-로터가-남기는-무늬) 의 **별편**이다.

자세·보정·광선 예산·표본율 네 가지가 무늬를 지운다. 각각을 **단일축으로 갈라** 얼마나 지우는지 잰다.

→ [`reports/06_6_microdoppler-limits.ipynb`](reports/06_6_microdoppler-limits.ipynb)

| 절 | 이 절의 결론 |
|---|---|
| [1](reports/06_6_microdoppler-limits.ipynb) | 지상 레이더는 기체를 아래에서 보므로 가림이 무는 자세가 우리 자세다 |
| [2](reports/06_6_microdoppler-limits.ipynb) | 문턱은 널 팔이 교정했고, 가장자리 시험은 아직 교정되지 않았다 |
| [3](reports/06_6_microdoppler-limits.ipynb) | 두 기체가 갈리는 축은 메쉬 품질이 아니라 표적 크기 대비 광선예산이다 — 예산을 맞춰 확인하는 시험은 이 하네스에서 아직 못 한다 |
| [4](reports/06_6_microdoppler-limits.ipynb) | 상시 기준신호가 주는 것은 날개끝 확산이 아니라 블레이드 통과율까지다 |

### 권 7 «무엇을 조명원으로 쓸 수 있나»

LTE·5G·WiFi 가 각각 **얼마나 자주, 얼마나 넓게** 신호를 내주는가. 5G 는 대역이 넓은 대신 상시 신호가 드물어 **이중고**가 된다.

→ [`reports/07_illuminators.ipynb`](reports/07_illuminators.ipynb)

| 절 | 이 절의 결론 |
|---|---|
| [1](reports/07_illuminators.ipynb) | 상시이면서 내용을 미리 아는 신호는 표준마다 하나씩 있다 |
| [2](reports/07_illuminators.ipynb) | 5G 는 좁고 드물다 — 두 배의 대가를 치른다 |
| [3](reports/07_illuminators.ipynb) | 여섯 항목은 닫힌형이고, 점유 대가만 몬테카를로 격자에서 읽는다 |
| [4](reports/07_illuminators.ipynb) | 바이스태틱 거리 분해능은 c/B, 잡음대역은 √(B/fs) 로 고정한다 |
| [5](reports/07_illuminators.ipynb) | 같은 자원격자를 독립 변조기에 넣으면 같은 시간파형이 나온다 |
| [6](reports/07_illuminators.ipynb) | 검출기가 실제로 쓰는 커널 그대로 모호함수를 그렸다 |
| [7](reports/07_illuminators.ipynb) | 5G SSB 는 걷는 드론에서 접힌다 |

### 권 8 «처리 사슬 — 직접파를 죽이고 표적을 세운다»

ECA 로 직접파를 지우고 CFAR 로 문턱을 세운다. **문턱을 어디에 두느냐가 결과를 정하므로** 그 교정을 먼저 적는다.

→ [`reports/08_detector.ipynb`](reports/08_detector.ipynb)

| 절 | 이 절의 결론 |
|---|---|
| [1](reports/08_detector.ipynb) | 수신 → ECA → 거리도플러 → CFAR, 사슬의 형상은 파형이 정한다 |
| [2](reports/08_detector.ipynb) | 탭을 늘리면 환경이 정한 바닥에서 멈추고, 그 대가가 0-도플러 노치다 |
| [3](reports/08_detector.ipynb) | 운용 형상에서 경험 Pfa 를 재니 명목값의 1.52~2.66 배였다 |
| [4](reports/08_detector.ipynb) | 그 배율의 원인은 셀 상관이고, 교정표는 형상마다 다시 재야 한다 |

### 권 9 «관측가능성과 기하 — 어디에 서야 보이나»

송신기·수신기·표적의 배치가 검출을 정한다. **볼 수 없는 자리**를 먼저 지도로 그리고, 그 다음에 거리를 말한다.

→ [`reports/09_observability.ipynb`](reports/09_observability.ipynb)

| 절 | 이 절의 결론 |
|---|---|
| [1](reports/09_observability.ipynb) | 한 순간의 (R_b, f_d) 는 랭크 2 이고, 수신기를 하나 더하면 위치가 풀린다 |
| [2](reports/09_observability.ipynb) | TX·RX·표적 배치와 β·앙각·원거리장이 유효창을 연다 |
| [3](reports/09_observability.ipynb) | 세 밴드에서 값이 다른 항은 λ² 와 σ 둘뿐이다 |
| [4](reports/09_observability.ipynb) | 자유공간 형상에서 문턱을 다시 재니 세 밴드가 SNR90 하나를 공유한다 |

### 권 10 «결과 — 얼마나 멀리서 보이나»

R90 과 순위가 이 연구의 정량 결론이다. 적분시간·잔류·σ 가정을 흔들어 **순위가 견디는지**까지 함께 적는다.

→ [`reports/10_results.ipynb`](reports/10_results.ipynb)

| 절 | 이 절의 결론 |
|---|---|
| [1](reports/10_results.ipynb) | 레벨을 맞추려면 크기전이 법칙을 골라야 하므로 기울기만 받는다 |
| [2](reports/10_results.ipynb) | 앵커 σ 위의 R90 은 비교가능 12칸에서 3.69~7.44 km 이고, 밴드 순서는 기체마다 바뀐다 |
| [3](reports/10_results.ipynb) | 그 순위는 자세평균이면 하나로 모이고, 자세평균 뒤집힘 문턱은 현실 봉투 안이다 |
| [4](reports/10_results.ipynb) | CPI 를 늘리면 세 파형 모두 블라인드율이 내려간다 |
| [5](reports/10_results.ipynb) | 모호속도는 표본화율의 성질이라 CPI 와 무관한 상한이다 |

별편이 한 편 딸려 있다.

- [10-2 «결론이 무엇에 기대고 있나 — 강건성과 하드웨어»](reports/10_2_robustness.ipynb) (빌더 `src/build_volumes.py (조각 조립)`) — 표적 모형·수신 소자·장비를 바꿔 넣어 결론이 어디서 흔들리는지 본다.

### 별편 10-2 «결론이 무엇에 기대고 있나 — 강건성과 하드웨어»

[권 10 «결과 — 얼마나 멀리서 보이나»](#권-10-결과--얼마나-멀리서-보이나) 의 **별편**이다.

표적 모형·수신 소자·장비를 바꿔 넣어 **결론이 어디서 흔들리는지** 본다.

→ [`reports/10_2_robustness.ipynb`](reports/10_2_robustness.ipynb)

| 절 | 이 절의 결론 |
|---|---|
| [1](reports/10_2_robustness.ipynb) | σ 를 곱하기 전에 이미 세 파형의 순서를 정하는 축이 있다 |
| [2](reports/10_2_robustness.ipynb) | 평판·큐브·우리 격자를 같은 동작점에서 갈아끼우면 요구 이득이 이만큼 달라진다 |
| [3](reports/10_2_robustness.ipynb) | 코히어런트 배열이득은 10log₁₀N 상한에 -0.11~+0.47 dB 로 붙는다 |
| [4](reports/10_2_robustness.ipynb) | X410 의 12-bit ADC 동적범위가 직접파 제거의 천장이다 |
| [5](reports/10_2_robustness.ipynb) | 교정된 절대 σ 를 만드는 조건은 여섯 항목이 전부다 |

### 권 11 «실측 계획 — 무엇을 재야 이 문서가 닫히나»

시뮬레이션이 선언으로 남겨 둔 것들의 목록과, 그것을 닫는 **야외 실측 규약**이다.

→ [`reports/11_measurement.ipynb`](reports/11_measurement.ipynb)

| 절 | 이 절의 결론 |
|---|---|
| [1](reports/11_measurement.ipynb) | 가장 보수적인 D 정의로도 세션 거리 하나가 두 기체 세 밴드를 덮는다 |
| [2](reports/11_measurement.ipynb) | 구가 σ 를 절대량으로 만들고, 반경 17.8 cm 를 고른다 |
| [3](reports/11_measurement.ipynb) | 표적을 한 거리빈에 넣는 최대 대역은 200 MHz 다 |
| [4](reports/11_measurement.ipynb) | 가장 촘촘한 요구 1.38° 를 세션 간격으로 채택해 앵커 문헌의 고정 2° 보다 촘촘하게 간다 |
| [5](reports/11_measurement.ipynb) | σ(f) 레인지·파형축·비행검출로 층을 나눈다 |
| [6](reports/11_measurement.ipynb) | 캠페인이 결판내는 양은 절대값이 아니라 순위다 |
| [7](reports/11_measurement.ipynb) | 기울기 판정의 문턱은 세션간 진폭 재현성이고, σ 사슬 세대를 바꾸면 그 문턱이 손닿는 범위 밖으로 좁아진다 |

### 권 12 «실외 장면 — 지면과 벽이 서면 무엇이 달라지나»

자유공간에서 세운 판정이 **지면과 건물이 있는 자리**에서도 서는지 묻는다. 실외 기록의 날개 박자는 솔버 인공물에 가려 있었고, 그 인공물의 정체는 지면 거울 반사였다.

→ [`reports/12_outdoor-scene.ipynb`](reports/12_outdoor-scene.ipynb)

| 절 | 이 절의 결론 |
|---|---|

### 권 A «도감 — 원장의 모든 팔을 그림으로»

앙각 스윕 원장이 담은 팔 전부를 STFT 맵과 대역 에너지로 펴 둔 **재고 목록**이다. 판정하지 않는다 — 어느 팔이 무엇을 담고 있는지 찾아보는 자리다.

→ [`reports/A_atlas.ipynb`](reports/A_atlas.ipynb)

이 10편은 `benchmark/build_atlas_toc.py (그림은 benchmark/build_md_atlas.py)` 가 짓는다.

| 편 | 무엇에 답하나 |
|---|---|
| [`A_atlas.ipynb`](reports/A_atlas.ipynb) | 도감 지도 — 읽는 법 · 편 목록 · 이름 규약 · 주의 |
| [`A_atlas_A.ipynb`](reports/A_atlas_A.ipynb) | 기본 엔진 — 엔진·광선예산·자세수, ⚠거리도 10 m·15 m 로 섞여 있다 |
| [`A_atlas_B.ipynb`](reports/A_atlas_B.ipynb) | 스위치 — 굴절·회절·모서리·확산을 켜고 끈 조합 |
| [`A_atlas_C.ipynb`](reports/A_atlas_C.ipynb) | 기체 3 종 — 박자가 기체마다 다르다 |
| [`A_atlas_D.ipynb`](reports/A_atlas_D.ipynb) | 방위 — 정면 말고 45° 에서 본 판 |
| [`A_atlas_E.ipynb`](reports/A_atlas_E.ipynb) | 부품 분해 — 프로펠러만 / 동체만 |
| [`A_atlas_F.ipynb`](reports/A_atlas_F.ipynb) | 거리 — 15 m 아닌 판(30 m) |
| [`A_atlas_G.ipynb`](reports/A_atlas_G.ipynb) | PTD — 모서리 보정을 켠 판 |
| [`A_atlas_H.ipynb`](reports/A_atlas_H.ipynb) | 격자 — λ/12 대신 더 촘촘한 격자 |
| [`A_atlas_I.ipynb`](reports/A_atlas_I.ipynb) | 평면파 — 구면파 대신 평면파로 조명한 판 |

아래 절은 [`A_atlas.ipynb`](reports/A_atlas.ipynb) 에 이어 붙어 있다.

| 절 | 이 절의 결론 |
|---|---|

---

## 부록 — 동결(유효하고, 새 작업은 넣지 않는다)

| 위치 | 내용 |
|---|---|
| [`report_mesh/`](report_mesh) 8편 | 드론 메쉬 제작·검증 심화 가이드 |
| [`prior_work/`](prior_work) | 선행연구·오픈소스 조사 원자료 — 별편 1-2 의 census 가 여기서 나온다 |
| [`OPENSOURCE.md`](OPENSOURCE.md) | 오픈소스 대체 지도(RadarSimPy 교차검증 · OpenISAC X410 실측) |
| `report0N_*.ipynb` (루트) | **옛 8편** — 재구성 전 원본이고 대조가 끝날 때까지 제자리에 둔다 |

## 다시 만들기

순서가 중요하다 — 뒤 단계가 앞 단계의 산출물을 읽는다.

```bash
cd /workspace/sionna
PY=~/.venvs/py312/bin/python

# ① 조각 빌더 → reports/_parts/NN_slug.ipynb (계산 없음 · GPU 0 장 · 수 초)
for f in src/build_part*.py; do PYTHONPATH=src $PY "$f"; done

# ② 그림이 무거워 여러 편으로 나뉘는 권을 따로 짓는다
PYTHONPATH=src $PY src/make_report08_microdoppler.py

# ③ 그 권의 마지막 편(바이스태틱)은 빌더가 따로다
PYTHONPATH=src $PY src/make_report07b_bistatic.py

# ④ 권에 딸린 별편 — 자기 파일만 낸다
PYTHONPATH=src $PY src/make_report11_2_two_channel.py

# ⑤ 권에 딸린 별편 — 자기 파일만 낸다
PYTHONPATH=src $PY src/build_report18_switch_grid.py

# ⑥ 조각 → 권 + 후처리 + 색인 + reports/README.md
PYTHONPATH=src $PY src/build_volumes.py

# ⑦ 끊긴 링크·그림·출처를 전수로 센다
PYTHONPATH=src $PY benchmark/check_report_links.py

# 이 README (색인을 읽어 목차를 다시 낸다)
PYTHONPATH=src $PY src/make_readme.py

# 숫자 자체를 다시 낸다 (GPU) — 어느 절의 어느 명령인지는 docs/REPRODUCE.md 에
PYTHONPATH=src:benchmark $PY benchmark/regen_mesh_dependents.py --list
PYTHONPATH=src:benchmark $PY benchmark/regen_mesh_dependents.py
```

| | |
|---|---|
| Python | `~/.venvs/py312/bin/python` (3.12) — 이 한 env 로 전부 실행 |
| 핵심 | Sionna RT 2.0.1 · Mitsuba 3.8.0 · drjit 1.3.1 (OptiX GPU) · torch · numpy · trimesh + manifold3d |
| 노트북 커널 | `py312` |
| 실행 규약 | `PYTHONPATH=src:benchmark` 를 반드시 준다 |

## 하우스 규약

- **권 제목은 물음, 절 제목은 답이다.** 절 제목은 «…다» 로 끝나는 평서문이고, 물음표로 끝나는 절 제목은 `src/report_style.py` 가 막는다.
- **숫자는 손으로 치지 않는다.** 전부 `num()` 이 JSON 을 열어 값을 대조하고, 화면에는
  각주 `[^n]` 으로 찍힌다. 절 끝 «출처» 표의 값은 표를 만들 때 JSON 을 **다시 열어**
  채운 것이다(왕복 검사). 지금 본편 13권·별편 7편에 각주 2424개와 그림 1045장이 실려 있다.
- **본문을 고칠 곳은 조각 빌더다.** 조각(`reports/_parts/`)과 권(`reports/`)은 둘 다 생성물이라, 손으로 고치면 다음 빌드에서 사라진다.
- **논문 문장과 재현 절차는 리포트 밖에 산다** — 사용자 지시다. [`docs/paper/`](docs/paper/README.md) 와 [`docs/REPRODUCE.md`](docs/REPRODUCE.md).
- 각 절은 `한 일 / 결과 / 방법 / 재현` 으로 열고 `다음 단계` 표로 닫는다. «다음 단계» 는 한계 목록이 아니라 앞을 보는 행동이다.
- 그림 텍스트(제목·축·범례·주석)는 **영어**, 본문·주석·print 는 **한국어**.
- **권의 길이는 그 권이 답하는 물음의 크기가 정한다** — 셀 수 상한을 두지 않는다.

## 저장소 구조

읽는 층과 만드는 층이 갈려 있다.

```
reports/NN_slug.ipynb        ⭐본편 13권 + 별편 7편 — 사람이 읽는 문서. 한 권이 물음 하나
  README.md                  권 목차 (생성물)
  _parts/NN_slug.ipynb       조각 88편 — 빌더 산출물. 직접 읽지 않는다
report_mesh/                 부록 8편 (동결)
prior_work/                  선행연구 조사 원자료

src/
  build_partNN_*.py          ⭐조각 생성기 — 서술의 원본. 계산은 없다
  build_volumes.py           ⭐조각 → 권 + 색인 + reports/README.md
  make_report08_microdoppler.py  6권 5편 중 주 빌더 (그림이 무거워 따로 짓는다)
  make_report07b_bistatic.py     6권의 나머지 한 편
  make_report11_2_two_channel.py  권 파일을 짓는다
  build_report18_switch_grid.py  별편 5-2 — 자기 파일만 낸다
  make_readme.py             이 파일을 만든다
  report_style.py            규약 강제(num()·각주·부정문 계수)
  report_registry.py         앵커 사전 — 조각 사이 링크의 유일한 출처
  drones.py                  ⭐표적 레지스트리 DRONES — 기종·제원의 유일한 출처
  materials.py               ⭐전파재질 단일 진리원 — Sionna RT 와 PO 가 둘 다 읽는다
  rcs_sbr.py                 ⭐SBR+PO 커널 (Mitsuba 광선조준 + PO 표면적분)
  sigma_anchor.py            ⭐측정 앵커 재보정 σ=A(f)·B₁·B₂ + 미통제 항 원장
  waveforms*.py              WiFi/LTE/5G OFDM 합성 + Sionna PHY 대조
  passive_process.py         패시브 DSP: ECA → CAF 거리도플러 → CA-CFAR
  experiment_*.py            검출·자유공간 실험(GPU 몬테카를로)
  viz_*.py                   그림 (텍스트는 전부 영어)

benchmark/
  check_report_links.py      ⭐링크·그림·출처 전수 검사
  regen_mesh_dependents.py   ⭐재생성 파이프라인 — 무엇을 어느 순서로 돌리나
  mie_pec_sphere.py          기준해 두 개(정확 Mie · 해석 PO) — 커널의 과녁
  verify_*.py                검증 하네스 (절이 읽는 verify_*.json 생산)

outputs/                     *.json(숫자의 원본) · figures/ · volumes_index.json
docs/                        REPORTS_VOLUMES.md(편성) · REPRODUCE.md · paper/ · SPECS.md
```

기계용 색인은 [`outputs/volumes_index.json`](outputs/volumes_index.json) 다 — 권·절·조각 배치와 셀·각주·그림 수가 전부 거기 있고, 이 README 의 목차는 그 파일을 읽어 만든 것이다.

## 별도 주제 — 코드는 그대로 있다

| 주제 | 코드 |
|---|---|
| 반무향 챔버 환경 | `src/chamber.py` · `benchmark/verify_clutter_doppler.py` |
| 바닥 유령 표적 | `benchmark/verify_floor_ghost.py` · `src/experiment_ghost.py` |

---

## 출처

위 숫자에 붙은 `[^n]` 은 그 값이 온 JSON 파일과 키다. 값은 이 문서를 만들 때 JSON 을 다시 열어 채웠다.

[^1]: `outputs/sbr_kr_sweep.json` : `summary_div16.max_abs_db_vs_po` = 0.2006
[^2]: `outputs/sbr_defect_fixes.json` : `d3_multibounce_phase.max_abs_err_db` = 0.5563
[^3]: `outputs/sbr_defect_fixes.json` : `d2_exit_vis_effect_on_reciprocity.worst_without_exit_vis_db` = 9.687
[^4]: `outputs/sbr_defect_fixes.json` : `d2_exit_vis_effect_on_reciprocity.worst_with_exit_vis_db` = 8.237
[^5]: `outputs/rcs_anchor.json` : `literature.mu_eps.das_phantom3_mono.mu_a` = 0.21
[^6]: `outputs/report02_derived.json` : `anchor_modes.level_shift_abs_max_db` = 4.737e-15
[^7]: `outputs/report02_derived.json` : `anchor.shape_invariance_max_abs_db` = 1.929e-15
[^8]: `outputs/report02_derived.json` : `anchor_modes.size_law_spread_max_db` = 9.501
[^9]: `outputs/das_fleet_validation.json` : `prereg_judgement.verdict` = NOT_VALIDATED (P3 산포)
[^10]: `outputs/verify_cfar.json` : `meta.runtime_s` = 2717
[^11]: `outputs/report03_illuminators.json` : `occupancy_cost.value_db` = 18
[^12]: `outputs/report02_derived.json` : `mesh.n` = 7
[^13]: `outputs/report02_derived.json` : `mesh.n_tris_total` = 207268
[^14]: `outputs/prior_census.json` : `funnel.all.g3_mesh_scattering` = 0
