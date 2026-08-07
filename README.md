<!-- 생성물 — `src/make_readme.py` 가 편성에서 읽어 쓴다. 손으로 고치지 말고 그 파일을 고쳐라. -->

# sionna2 — 통신신호를 조명원 삼는 패시브 바이스태틱 드론 탐지 시뮬레이터

셀이 이미 켜 두는 상시 신호(WiFi · LTE · 5G NR)를 조명 삼아 드론을 탐지하는 패시브
바이스태틱 레이더를, Sionna RT 2.0.1 위에서 자유공간 기하로 끝까지 시뮬레이션한다.
표적 산란은 Sionna 의 Mitsuba/OptiX 광선엔진으로 면별 가림을 풀고 그 조명면 위에서
부품별 재질 PO 를 적분해 만든다. σ 의 **주파수 의존성**은 공개 측정(Das)에 맞추고,
**자세 패턴과 절대 레벨은 우리 PO 출력**이다.

보고서는 **편 78개 · 부 12개** 다. 한 편이 중심 메시지 하나를 들고,
**편 제목이 곧 그 편의 결론 문장**이다 — 목차를 읽는 것이 결론을 읽는 것이다.

## 어디부터 읽어라

편 78개를 처음부터 읽지 않는다. **읽는 목적이 셋이면 읽는 순서도 셋**이고,
그 갈림길이 [편 00 «읽는 목적이 셋이면 읽는 순서도 셋이다»](reports/00_map.ipynb) 다.

| 무엇을 하려는가 | 어디로 | 얼마나 |
|---|---|---|
| 이 저장소가 무엇을 해냈는지만 알고 싶다 | ↓ **① 빨리 훑기** | 30분 |
| 판정을 검사하려 한다(심사·적대검증) | ↓ **② 왜 믿을 수 있나** | 2시간 |
| 숫자를 재생산하려 한다 | [`docs/REPRODUCE.md`](docs/REPRODUCE.md) — 편 → 명령 → 출력 → 소요 | 리포트를 안 읽는다 |
| 원고에 옮기려 한다 | [`docs/paper/`](docs/paper/README.md) — 조각마다 «어느 편에서 왔나» 가 붙어 있다 | — |

### ① 빨리 훑기 — 30분

부마다 결론 편 하나씩이다. **오른쪽 칸이 그 편의 결론 문장 전체**이므로, 제목만 읽어도
한 바퀴가 돈다. 막히는 데서만 그 편을 연다.

| 부 | 편 | 이 편의 결론 |
|---|---|---|
| 1 | [06](reports/06_decision-table.ipynb) `decision-table` | 표적 항이 비에서 소거되는가와 절대값이 필요한가, 두 물음이 실험을 네 칸으로 가른다 |
| 2 | [13](reports/13_where-we-stand.ipynb) `where-we-stand` | 네 관문을 동시에 통과한 게재본은 0편이고, 최근접 3편은 각각 다른 관문에서 걸린다 |
| 3 | [16](reports/16_mesh-vs-real.ipynb) `mesh-vs-real` | 메쉬 외형이 실제 기체와 얼마나 맞는지를 사진 IoU·CAD 치수·실물 스캔 세 자로 쟀다 |
| 4 | [21](reports/21_kernel-vs-reference.ipynb) `kernel-vs-reference` | 해석 PO 구 대비 구현오차는 kr 전 구간에서 0.201 dB 안이다 |
| 5 | [24](reports/24_anchor-mode.ipynb) `anchor-mode` | σ = A(f)·B₁·B₂ 에서 A(f) 의 기울기만 측정에서 받고, 레벨과 각패턴은 우리 PO 출력이다 |
| 6 | [32](reports/32_ladder-answer.ipynb) `ladder-answer` | 모양의 유무는 수십 dB 를 가르고, 모양의 정밀도는 한 자릿수 dB 안에서 논다 |
| 7 | [43](reports/43_md-prf.ipynb) `md-prf` | 상시 기준신호가 주는 것은 날개끝 확산이 아니라 블레이드 통과율까지다 |
| 8 | [46](reports/46_cost-ledger.ipynb) `cost-ledger` | 여섯 항목은 닫힌형이고, 점유 대가만 몬테카를로 격자에서 읽는다 |
| 9 | [53](reports/53_cfar-calib.ipynb) `cfar-calib` | 운용 형상에서 경험 Pfa 를 재니 명목값의 1.52~2.66 배였다 |
| 10 | [60](reports/60_r90.ipynb) `r90` | 앵커 σ 위의 R90 은 3.69~11.10 km 이고, 밴드 순서는 기체마다 바뀐다 |
| 11 | [74](reports/74_sim-vs-meas.ipynb) `sim-vs-meas` | 캠페인이 결판내는 양은 절대값이 아니라 순위다 |

### ② 왜 믿을 수 있나 — 2시간

검증·대조·반증 편만 모았다. 뼈대는 **눈감기 대조 · 사전등록 채점 · PREMATURE 판정 ·
널 교정** 넷이다 — 우리가 틀렸을 수 있는 자리를 우리가 먼저 때린 편들이다.

| 부 | 편 | 무엇을 때렸나 |
|---|---|---|
| 1 | [01](reports/01_stock-says.ipynb) `stock-says` | Sionna 기술보고서 59쪽에 physical optics 는 0회, SBR 은 44회 나온다 |
| 1 | [04](reports/04_eight-factors.ipynb) `eight-factors` | 필드 갱신 인자 여덟 개에 면적·곡률·치수·λ 가 없다 |
| 1 | [05](reports/05_size-sweep.ipynb) `size-sweep` | 면적을 1600배로 키워도 경로 진폭은 7.4e-07 dB 움직인다 |
| 4 | [21](reports/21_kernel-vs-reference.ipynb) `kernel-vs-reference` | 해석 PO 구 대비 구현오차는 kr 전 구간에서 0.201 dB 안이다 |
| 4 | [22](reports/22_po-knee.ipynb) `po-knee` | PO 유효 무릎을 부품 폭으로 옮기면 어느 부품이 어느 밴드에서 떨어지는지가 보인다 |
| 5 | [26](reports/26_blind-p3.ipynb) `blind-p3` | Phantom 3 를 문헌값을 보지 않고 내고 봉인을 풀었다 |
| 5 | [27](reports/27_box-sphere-control.ipynb) `box-sphere-control` | 메쉬가 사는 축은 절대 크기가 아니라 각도 구조다 |
| 5 | [28](reports/28_fleet-prereg.ipynb) `fleet-prereg` | 같은 잣대를 네 기체로 넓히면 판정이 NOT_VALIDATED 로 갈린다 |
| 5 | [29](reports/29_sigma-robustness.ipynb) `sigma-robustness` | 공통모드 σ 오차는 파형 순위를 안 건드리고, 차분 오차가 뒤집는다 |
| 6 | [33](reports/33_ladder-premature.ipynb) `ladder-premature` | 이 답을 아직 결론이라고 부를 수 없는 이유가 일곱 가지이고, 그중 둘이 치명적이다 |
| 7 | [41](reports/41_md-calibration.ipynb) `md-calibration` | 판정 잣대를 널 팔 15 칸과 이상 점산란자로 먼저 교정했다 |
| 9 | [53](reports/53_cfar-calib.ipynb) `cfar-calib` | 운용 형상에서 경험 Pfa 를 재니 명목값의 1.52~2.66 배였다 |
| 9 | [54](reports/54_cfar-why.ipynb) `cfar-why` | 그 배율의 원인은 셀 상관이고, 교정표는 형상마다 다시 재야 한다 |
| 10 | [61](reports/61_rank-durability.ipynb) `rank-durability` | 그 순위는 자세평균이면 σ 오차 아래에서 하나로 모인다 |
| 11 | [76](reports/76_session-drift.ipynb) `session-drift` | 기울기 판정의 문턱은 세션간 진폭 재현성이고, σ 사슬 세대를 바꾸면 그 문턱이 손닿는 범위 밖으로 좁아진다 |

---

## 이 저장소가 한 일

| 한 일 | 수치 | 어느 편 |
|---|---|---|
| **광선엔진 안에서 산란을 적분한다** — Sionna 자체 Mitsuba/OptiX 로 first-hit 가림을 판정하고 조명면 위에서 부품별 재질 PO 를 적분한다 | `src/rcs_sbr.py:184` · `src/materials.py` | [18 «가림 판정은 Sionna 광선엔진이 하고»](reports/18_kernel-what.ipynb) |
| **커널을 기준해로 검증했다** — 해석 PO 구 대비 kr 1~100 전 구간 | 최대 0.201 dB [^1] | [21 «해석 PO 구 대비 구현오차는 kr 전 구간에…»](reports/21_kernel-vs-reference.ipynb) |
| **다중반사 위상을 PEC 이면각 닫힌형 8πa²b²/λ² 와 맞췄다** — 변 길이 4점 | 최대 0.556 dB [^2] | [21 «해석 PO 구 대비 구현오차는 kr 전 구간에…»](reports/21_kernel-vs-reference.ipynb) |
| **바이스태틱 출사 가시성을 넣었다** — 히트마다 수신기 방향으로 그림자 광선을 쏜다 | 상반성 위반 최악 9.69 [^3] → 8.24 dB [^4] | [20 «수신 방향 그림자 광선을 켜면 상반성 위반이…»](reports/20_bistatic-exit.ipynb) |
| **σ 의 주파수 기울기를 측정에 정렬했다** — σ = A(f)·B₁·B₂ 에서 A(f) 의 **기울기만** 측정, **절대 레벨과 B₁ 은 우리 PO 출력** | 0.210 dB/GHz [^5] · 평균 레벨이동 0.00 dB [^6] · 정규화 각패턴 이동 1.9e-15 dB [^7] | [24 «σ = A(f)·B₁·B₂ 에서 A(f) 의…»](reports/24_anchor-mode.ipynb) |
| **모드 선택의 대가를 수치로 적었다** — 레벨까지 앵커에 맞추려면 크기전이 법칙을 하나 골라야 하고, 그 선택 하나가 기체당 최대 이만큼을 정한다 | L² ↔ L⁴ 예측 차 최대 9.50 dB [^8] | [25 «앵커가 통제한 항목과 남은 항목의 크기를 기체…»](reports/25_anchor-ledger.ipynb) |
| **우리 σ 를 눈감고 내고 봉인을 풀었다** — 문헌 상수를 한 번도 안 읽은 경로로 Phantom 3 를 내고 별도 스크립트가 열었다 | 사전등록 판정 NOT_VALIDATED (P3 산포) [^9] | [28 «같은 잣대를 네 기체로 넓히면 판정이 NOT_…»](reports/28_fleet-prereg.ipynb) |
| **CFAR 를 경험 Pfa 로 교정했다** — GPU 몬테카를로로 오경보 셀을 직접 세었다 | 2,717 s [^10], 명목 1e-4 에서 배율을 형상마다 다시 잰다 | [53 «운용 형상에서 경험 Pfa 를 재니 명목값의…»](reports/53_cfar-calib.ipynb) |
| **세 파형을 한 표적·한 검출기로 비교했다** — 점유·대역·PRF·λ² 를 dB 원장으로 닫았다 | 점유 18.0 dB [^11] | [46 «여섯 항목은 닫힌형이고»](reports/46_cost-ledger.ipynb) |
| **기체 7종을 사진·제원에서 세우고 실물 CAD 와 맞댔다** | 메쉬 7 종 [^12] · 삼각형 207,268 개 [^13] | [16 «메쉬 외형이 실제 기체와 얼마나 맞는지를 사진…»](reports/16_mesh-vs-real.ipynb) |
| **선행연구를 전문으로 판정했다** — 아카이브 PDF 41편 중 16편, 게재상태는 PDF 로 확정 | 드론 메쉬에서 산란을 계산한 게재본 0 편 [^14] | [08 «게재본 중 드론 메쉬에서 산란을 계산한 것은…»](reports/08_census-published.ipynb) |

---

## 목차 — 부 12개

부마다 답하는 물음이 하나다. 아래 표의 «편» 칸은 그 편의 **결론 문장** 그대로다.

| 부 | 이름 | 이 부가 답하는 물음 | 편 |
|---|---|---|---|
| [0](#부-0-지도) | 지도 | 어느 편이 어느 질문에 답하나 | 00 (1편) |
| [1](#부-1-스톡-엔진이-하는-일과-안-하는-일) | 스톡 엔진이 하는 일과 안 하는 일 | Sionna RT 가 스스로 계산하는 양은 어디서 끝나나 | 01~07 (7편) |
| [2](#부-2-선행연구) | 선행연구 | 남들은 표적 신호를 어디서 얻었나 | 08~14 (7편) |
| [3](#부-3-표적-메쉬) | 표적 메쉬 | 기체 7종을 무엇에서 지었고 실물과 얼마나 맞나 | 15~17 (3편) |
| [4](#부-4-산란-커널) | 산란 커널 | 우리 커널이 무엇을 계산하고 기준해와 얼마나 맞나 | 18~23 (6편) |
| [5](#부-5-앵커와-검증) | 앵커와 검증 | σ 의 어느 축을 측정에서 받고, 그 판정이 함대에서 버티나 | 24~29 (6편) |
| [6](#부-6-표적-사다리) | 표적 사다리 | 드론을 얼마나 거칠게 그려도 되나 | 30~33 (4편) |
| [7](#부-7-마이크로도플러) | 마이크로도플러 | 도는 로터가 만드는 무늬를 무엇이 정하나 | 34~43 (10편) |
| [8](#부-8-조명원) | 조명원 | 세 파형이 무는 대가 | 44~50 (7편) |
| [9](#부-9-검출기) | 검출기 | 수신 신호가 판정이 되기까지 | 51~55 (5편) |
| [10](#부-10-검출-결과) | 검출 결과 | 어느 조명원으로 어디까지 보이나 | 56~66 (11편) |
| [11](#부-11-실측-설계) | 실측 설계 | 무엇을 재면 어느 주장이 결판나나 | 67~77 (11편) |

### 부 0 «지도»

**어느 편이 어느 질문에 답하나**

읽는 목적이 셋이라 진입 경로도 셋이다. 여기서 갈라진다.

| 편 | 이 편의 결론 | 그림 |
|---|---|---|
| [00](reports/00_map.ipynb) `map` | 읽는 목적이 셋이면 읽는 순서도 셋이다 |  |

### 부 1 «스톡 엔진이 하는 일과 안 하는 일»

**Sionna RT 가 스스로 계산하는 양은 어디서 끝나나**

Sionna RT 설치본을 인자 목록까지 해부해, 광선이 면을 맞았을 때 무엇이 계산되고 무엇이 계산되지 않는지를 확정했다. 표적 산란이 별도 항이 되는 자리가 여기서 정해진다.

| 편 | 이 편의 결론 | 그림 |
|---|---|---|
| [01](reports/01_stock-says.ipynb) `stock-says` | Sionna 기술보고서 59쪽에 physical optics 는 0회, SBR 은 44회 나온다 |  |
| [02](reports/02_engine-paths.ipynb) `engine-paths` | 경로는 SBR 과 이미지법이 정한다 |  |
| [03](reports/03_engine-amplitude.ipynb) `engine-amplitude` | 진폭은 국소 평면파–평면경계 해 하나로 만들어진다 | 1 |
| [04](reports/04_eight-factors.ipynb) `eight-factors` | 필드 갱신 인자 여덟 개에 면적·곡률·치수·λ 가 없다 | 1 |
| [05](reports/05_size-sweep.ipynb) `size-sweep` | 면적을 1600배로 키워도 경로 진폭은 7.4e-07 dB 움직인다 | 1 |
| [06](reports/06_decision-table.ipynb) `decision-table` | 표적 항이 비에서 소거되는가와 절대값이 필요한가, 두 물음이 실험을 네 칸으로 가른다 | 1 |
| [07](reports/07_why-po.ipynb) `why-po` | 완전파는 정확도의 과녁이고, SBR+PO 는 표를 만들 수 있는 유일한 비용대다 |  |

### 부 2 «선행연구»

**남들은 표적 신호를 어디서 얻었나**

게재본 16편이 표적 서명을 어디서 조달했는지 전문으로 판정하고, 그 조달처가 사 준 주장의 크기를 카탈로그로 만들었다.

| 편 | 이 편의 결론 | 그림 |
|---|---|---|
| [08](reports/08_census-published.ipynb) `census-published` | 게재본 중 드론 메쉬에서 산란을 계산한 것은 0편이다 | 1 |
| [09](reports/09_census-preprint.ipynb) `census-preprint` | 프리프린트는 따로 세고, Ziganshin 은 두 판을 구별해 인용한다 |  |
| [10](reports/10_procurement.ipynb) `procurement` | 표적 서명을 어디서 조달했는지가 그 논문이 낼 수 있는 주장의 크기를 정한다 | 1 |
| [11](reports/11_procurement-catalog.ipynb) `procurement-catalog` | 조달처 일곱 갈래 R1~R7 을 전수로 적었다 |  |
| [12](reports/12_injection.ipynb) `injection` | 외부 σ 주입은 게재돼 있고, 그 값의 대가는 검증이 치른다 |  |
| [13](reports/13_where-we-stand.ipynb) `where-we-stand` | 네 관문을 동시에 통과한 게재본은 0편이고, 최근접 3편은 각각 다른 관문에서 걸린다 | 1 |
| [14](reports/14_borrowed.ipynb) `borrowed` | 선행에서 빌린 절차와 아직 안 빌린 절차를 비용과 함께 센다 |  |

### 부 3 «표적 메쉬»

**기체 7종을 무엇에서 지었고 실물과 얼마나 맞나**

기체 7종을 제원과 제조사 CAD 치수에서 세우고, 외형이 실물과 얼마나 맞는지를 사진 IoU·CAD 치수·실물 스캔 세 자로 쟀다.

| 편 | 이 편의 결론 | 그림 |
|---|---|---|
| [15](reports/15_mesh-build.ipynb) `mesh-build` | 기체 7종을 제원과 제조사 CAD 치수에서 세우고 부품을 재질 그룹으로 유지했다 | 1 |
| [16](reports/16_mesh-vs-real.ipynb) `mesh-vs-real` | 메쉬 외형이 실제 기체와 얼마나 맞는지를 사진 IoU·CAD 치수·실물 스캔 세 자로 쟀다 | 1 |
| [17](reports/17_materials.ipynb) `materials` | 도전성 재질이 면적의 45.3% 로 Σ\|Γ\|A 의 73.5% 를 낸다 | 1 |

### 부 4 «산란 커널»

**우리 커널이 무엇을 계산하고 기준해와 얼마나 맞나**

광선으로 조명면을 찾고 그 위에서 부품별 재질 PO 를 적분하는 커널을, 닫힌형 기준해 셋과 맞대 구현오차와 모형 간극을 따로 쟀다.

| 편 | 이 편의 결론 | 그림 |
|---|---|---|
| [18](reports/18_kernel-what.ipynb) `kernel-what` | 가림 판정은 Sionna 광선엔진이 하고, 면적분은 우리 커널이 한다 | 1 |
| [19](reports/19_kernel-vs-stock.ipynb) `kernel-vs-stock` | 스톡 솔버와 맞대면 «면이 많아서 느리다» 가설은 반증되고, 런타임의 96.9% 는 호스트가 쓴다 |  |
| [20](reports/20_bistatic-exit.ipynb) `bistatic-exit` | 수신 방향 그림자 광선을 켜면 상반성 위반이 9.69 → 8.24 dB 로 내려간다 |  |
| [21](reports/21_kernel-vs-reference.ipynb) `kernel-vs-reference` | 해석 PO 구 대비 구현오차는 kr 전 구간에서 0.201 dB 안이다 | 1 |
| [22](reports/22_po-knee.ipynb) `po-knee` | PO 유효 무릎을 부품 폭으로 옮기면 어느 부품이 어느 밴드에서 떨어지는지가 보인다 |  |
| [23](reports/23_kernel-open-items.ipynb) `kernel-open-items` | 커널이 아직 못 하는 것은 편파·PTD·재테셀레이션 셋이고, 각각의 크기를 적었다 |  |

### 부 5 «앵커와 검증»

**σ 의 어느 축을 측정에서 받고, 그 판정이 함대에서 버티나**

σ 의 주파수 기울기만 공개 측정에서 받고 레벨과 각패턴은 우리 출력으로 두었다. 그 판정을 눈감기 대조·대조군·사전등록 채점으로 때렸다.

| 편 | 이 편의 결론 | 그림 |
|---|---|---|
| [24](reports/24_anchor-mode.ipynb) `anchor-mode` | σ = A(f)·B₁·B₂ 에서 A(f) 의 기울기만 측정에서 받고, 레벨과 각패턴은 우리 PO 출력이다 | 1 |
| [25](reports/25_anchor-ledger.ipynb) `anchor-ledger` | 앵커가 통제한 항목과 남은 항목의 크기를 기체별 원장으로 적었다 |  |
| [26](reports/26_blind-p3.ipynb) `blind-p3` | Phantom 3 를 문헌값을 보지 않고 내고 봉인을 풀었다 |  |
| [27](reports/27_box-sphere-control.ipynb) `box-sphere-control` | 메쉬가 사는 축은 절대 크기가 아니라 각도 구조다 |  |
| [28](reports/28_fleet-prereg.ipynb) `fleet-prereg` | 같은 잣대를 네 기체로 넓히면 판정이 NOT_VALIDATED 로 갈린다 |  |
| [29](reports/29_sigma-robustness.ipynb) `sigma-robustness` | 공통모드 σ 오차는 파형 순위를 안 건드리고, 차분 오차가 뒤집는다 | 1 |

### 부 6 «표적 사다리»

**드론을 얼마나 거칠게 그려도 되나**

드론을 얼마나 거칠게 그려도 되는지를 사다리로 물었다 — 몸통은 진짜 CAD 로 두고 프로펠러만 갈아 끼운 축이 답할 자격이 있는 유일한 축이다.

| 편 | 이 편의 결론 | 그림 |
|---|---|---|
| [30](reports/30_ladder-three.ipynb) `ladder-three` | 사다리가 하나가 아니라 셋이었다 — 여섯 단이 서로 다른 운동학을 쓰고 있었다 | 1 |
| [31](reports/31_ladder-calibrated.ipynb) `ladder-calibrated` | 몸통은 진짜 CAD, 프로펠러만 갈아 끼운 교정 사다리가 답할 자격이 있는 유일한 축이다 |  |
| [32](reports/32_ladder-answer.ipynb) `ladder-answer` | 모양의 유무는 수십 dB 를 가르고, 모양의 정밀도는 한 자릿수 dB 안에서 논다 | 1 |
| [33](reports/33_ladder-premature.ipynb) `ladder-premature` | 이 답을 아직 결론이라고 부를 수 없는 이유가 일곱 가지이고, 그중 둘이 치명적이다 |  |

### 부 7 «마이크로도플러»

**도는 로터가 만드는 무늬를 무엇이 정하나**

로터를 돌려가며 시간표본마다 다시 추적해, 마이크로도플러 무늬를 정하는 것이 회전수·가림·자세임을 단일축으로 갈랐다.

| 편 | 이 편의 결론 | 그림 |
|---|---|---|
| [34](reports/34_md-paths-doppler.ipynb) `md-paths-doppler` | 스톡 Paths.doppler 로는 블레이드 변조가 안 나온다 — SceneObject.velocity 가 객체당 강체 1벡터다 |  |
| [35](reports/35_md-slowtime.ipynb) `md-slowtime` | 시간표본마다 자세를 새로 놓고 다시 쏘아 슬로타임 복소열을 만든다 |  |
| [36](reports/36_md-two-engines.ipynb) `md-two-engines` | 두 엔진이 날개끝 주파수 아래에서 겹치고 그 위에서 갈린다 | 1 |
| [37](reports/37_md-rpm.ipynb) `md-rpm` | 네 로터가 같은 회전수로 돌면 무늬는 시간에 못 변한다 | 1 |
| [38](reports/38_md-occlusion.ipynb) `md-occlusion` | 동체가 날개를 가리면 변조 깊이와 레벨이 함께 바뀐다 | 1 |
| [39](reports/39_md-blade-vs-body.ipynb) `md-blade-vs-body` | 블레이드 신호는 약하지 않다 — 동체 정적 반사가 덮고 있을 뿐이다 | 1 |
| [40](reports/40_md-attitude.ipynb) `md-attitude` | 지상 레이더는 기체를 아래에서 보므로 가림이 무는 자세가 우리 자세다 | 1 |
| [41](reports/41_md-calibration.ipynb) `md-calibration` | 판정 잣대를 널 팔 15 칸과 이상 점산란자로 먼저 교정했다 | 1 |
| [42](reports/42_md-ray-budget.ipynb) `md-ray-budget` | 두 기체가 갈리는 이유는 메쉬 품질이 아니라 표적 크기 대비 광선예산이다 | 1 |
| [43](reports/43_md-prf.ipynb) `md-prf` | 상시 기준신호가 주는 것은 날개끝 확산이 아니라 블레이드 통과율까지다 |  |

### 부 8 «조명원»

**세 파형이 무는 대가**

상시 기준신호를 세 표준의 자원격자에서 세우고, 조명원을 고르는 대가를 dB 원장으로 닫았다.

| 편 | 이 편의 결론 | 그림 |
|---|---|---|
| [44](reports/44_illuminators.ipynb) `illuminators` | 상시이면서 내용을 미리 아는 신호는 표준마다 하나씩 있다 | 1 |
| [45](reports/45_5g-double-cost.ipynb) `5g-double-cost` | 5G 는 좁고 드물다 — 두 배의 대가를 치른다 | 1 |
| [46](reports/46_cost-ledger.ipynb) `cost-ledger` | 여섯 항목은 닫힌형이고, 점유 대가만 몬테카를로 격자에서 읽는다 | 1 |
| [47](reports/47_range-convention.ipynb) `range-convention` | 바이스태틱 거리 분해능은 c/B, 잡음대역은 √(B/fs) 로 고정한다 |  |
| [48](reports/48_waveform-check.ipynb) `waveform-check` | 같은 자원격자를 독립 변조기에 넣어 상관 1.0000 을 얻었다 | 1 |
| [49](reports/49_ambiguity.ipynb) `ambiguity` | 검출기가 실제로 쓰는 커널 그대로 모호함수를 그렸다 | 1 |
| [50](reports/50_doppler-fold.ipynb) `doppler-fold` | 5G SSB 는 걷는 드론에서 접힌다 | 1 |

### 부 9 «검출기»

**수신 신호가 판정이 되기까지**

수신 신호가 판정이 되기까지의 사슬을 세우고, CFAR 문턱을 경험 Pfa 로 교정했다.

| 편 | 이 편의 결론 | 그림 |
|---|---|---|
| [51](reports/51_chain.ipynb) `chain` | 수신 → ECA → 거리도플러 → CFAR, 사슬의 형상은 파형이 정한다 | 1 |
| [52](reports/52_eca.ipynb) `eca` | 탭을 늘리면 환경이 정한 바닥에서 멈추고, 그 대가가 0-도플러 노치다 | 1 |
| [53](reports/53_cfar-calib.ipynb) `cfar-calib` | 운용 형상에서 경험 Pfa 를 재니 명목값의 1.52~2.66 배였다 | 1 |
| [54](reports/54_cfar-why.ipynb) `cfar-why` | 그 배율의 원인은 셀 상관이고, 교정표는 형상마다 다시 재야 한다 | 1 |
| [55](reports/55_observability.ipynb) `observability` | 한 순간의 (R_b, f_d) 는 랭크 2 이고, 수신기를 하나 더하면 위치가 풀린다 | 1 |

### 부 10 «검출 결과»

**어느 조명원으로 어디까지 보이나**

같은 표적·같은 기하·같은 교정문턱에서 세 조명원의 검출거리를 앵커 σ 위에서 쟀다.

| 편 | 이 편의 결론 | 그림 |
|---|---|---|
| [56](reports/56_geometry.ipynb) `geometry` | TX·RX·표적 배치와 β·앙각·원거리장이 유효창을 연다 |  |
| [57](reports/57_sensitivity-chain.ipynb) `sensitivity-chain` | 세 밴드에서 값이 다른 항은 λ² 와 σ 둘뿐이다 | 1 |
| [58](reports/58_shared-threshold.ipynb) `shared-threshold` | 자유공간 형상에서 문턱을 다시 재니 세 밴드가 SNR90 하나를 공유한다 | 1 |
| [59](reports/59_slope-anchor.ipynb) `slope-anchor` | 레벨을 맞추려면 크기전이 법칙을 골라야 하므로 기울기만 받는다 | 1 |
| [60](reports/60_r90.ipynb) `r90` | 앵커 σ 위의 R90 은 3.69~11.10 km 이고, 밴드 순서는 기체마다 바뀐다 | 1 |
| [61](reports/61_rank-durability.ipynb) `rank-durability` | 그 순위는 자세평균이면 σ 오차 아래에서 하나로 모인다 | 1 |
| [62](reports/62_cpi-sweep.ipynb) `cpi-sweep` | CPI 를 늘리면 세 파형 모두 블라인드율이 내려간다 |  |
| [63](reports/63_cpi-residual.ipynb) `cpi-residual` | 모호속도는 표본화율의 성질이라 CPI 와 무관한 상한이다 | 1 |
| [64](reports/64_sigma-free-axis.ipynb) `sigma-free-axis` | σ 를 곱하기 전에 이미 세 파형의 순서를 정하는 축이 있다 |  |
| [65](reports/65_target-model-swap.ipynb) `target-model-swap` | 평판·큐브·우리 격자를 같은 동작점에서 갈아끼우면 요구 이득이 이만큼 달라진다 |  |
| [66](reports/66_rx-elements.ipynb) `rx-elements` | 코히어런트 배열이득은 10log₁₀N 상한에 −0.11~+0.47 dB 로 붙는다 | 1 |

### 부 11 «실측 설계»

**무엇을 재면 어느 주장이 결판나나**

X410 으로 교정된 σ 를 얻는 세션 설계와, 어느 측정이 어느 주장을 결판내는지를 수치로 고정했다.

| 편 | 이 편의 결론 | 그림 |
|---|---|---|
| [67](reports/67_hardware.ipynb) `hardware` | X410 의 12-bit ADC 동적범위가 직접파 제거의 천장이다 | 1 |
| [68](reports/68_sigma-checklist.ipynb) `sigma-checklist` | 교정된 절대 σ 를 만드는 조건은 여섯 항목이 전부다 |  |
| [69](reports/69_site-geometry.ipynb) `site-geometry` | 가장 보수적인 D 정의로도 세션 거리 하나가 두 기체 세 밴드를 덮는다 | 1 |
| [70](reports/70_calibration-sphere.ipynb) `calibration-sphere` | 구가 σ 를 절대량으로 만들고, 반경 17.8 cm 를 고른다 | 1 |
| [71](reports/71_subband.ipynb) `subband` | 표적을 한 거리빈에 넣는 최대 대역은 200 MHz 다 |  |
| [72](reports/72_attitude.ipynb) `attitude` | 각도표본을 λ/4D 로 잡아 앵커 문헌의 고정 2° 보다 촘촘하게 간다 |  |
| [73](reports/73_three-layers.ipynb) `three-layers` | σ(f) 레인지·파형축·비행검출로 층을 나눈다 |  |
| [74](reports/74_sim-vs-meas.ipynb) `sim-vs-meas` | 캠페인이 결판내는 양은 절대값이 아니라 순위다 |  |
| [75](reports/75_decision-matrix.ipynb) `decision-matrix` | 주장마다 판정 범위를 결판·사슬확인·캠페인 밖으로 적었다 |  |
| [76](reports/76_session-drift.ipynb) `session-drift` | 기울기 판정의 문턱은 세션간 진폭 재현성이고, σ 사슬 세대를 바꾸면 그 문턱이 손닿는 범위 밖으로 좁아진다 | 1 |
| [77](reports/77_size-law-differential.ipynb) `size-law-differential` | 두 기체를 함께 재면 크기전이 법칙이 차등신호의 부호 하나로 갈린다 | 1 |

---

## 부록 — 동결(유효하고, 새 작업은 넣지 않는다)

| 위치 | 내용 |
|---|---|
| [`report_mesh/`](report_mesh) 8편 | 드론 메쉬 제작·검증 심화 가이드 |
| [`prior_work/`](prior_work) | 선행연구·오픈소스 조사 원자료 — 부 2 의 census 가 여기서 나온다 |
| [`OPENSOURCE.md`](OPENSOURCE.md) | 오픈소스 대체 지도(RadarSimPy 교차검증 · OpenISAC X410 실측) |
| `report0N_*.ipynb` (루트) | **옛 8편** — 재구성 전 원본이고 대조가 끝날 때까지 제자리에 둔다 |

## 다시 만들기

```bash
cd /home/yunjung/workspace/sionna2
PY=~/.venvs/py312/bin/python

# ① 편 78개를 다시 조립한다 (계산 없음 · GPU 0장 · 수 초)
for f in src/build_part*.py; do PYTHONPATH=src $PY "$f"; done

# ② 색인 · 재현 문서 · 논문 목차 · 지도 편 · README
PYTHONPATH=src $PY src/make_reports_index.py
PYTHONPATH=src $PY src/build_part00_map.py
PYTHONPATH=src $PY src/make_legacy_map.py
PYTHONPATH=src $PY src/make_readme.py

# ③ 편 사이 참조 검사 — 끊긴 링크·없는 앵커·안 열리는 출처를 센다
PYTHONPATH=src $PY benchmark/check_report_links.py

# ④ 숫자 자체를 다시 낸다 (GPU) — 어느 편의 어느 명령인지는 docs/REPRODUCE.md 에
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

- **편 제목이 결론 문장이다.** «…다» 로 끝나는 평서문이고, 물음표로 끝나는 제목은
  `src/report_style.py` 가 막는다.
- **숫자는 손으로 치지 않는다.** 전부 `num()` 이 JSON 을 열어 값을 대조하고, 화면에는
  각주 `[^n]` 으로 찍힌다. 편 끝 «출처» 표의 값은 표를 만들 때 JSON 을 **다시 열어**
  채운 것이다(왕복 검사). 지금 편 78개에 그림 46장이 실려 있다.
- **논문 문장과 재현 절차는 리포트 밖에 산다** — 사용자 지시다. [`docs/paper/`](docs/paper/README.md) 와 [`docs/REPRODUCE.md`](docs/REPRODUCE.md).
- 각 편은 `한 일 / 결과 / 방법 / 재현` 으로 열고 `다음 단계` 표로 닫는다. «다음 단계» 는 한계 목록이 아니라 앞을 보는 행동이다.
- 그림 텍스트(제목·축·범례·주석)는 **영어**, 본문·주석·print 는 **한국어**.
- 분량 상한: 편당 마크다운 25셀 · 셀당 12줄 · 편당 그림 8장. **넘치면 내용을 줄이지 말고 편을 쪼갠다.**

## 저장소 구조

```
reports/NN_<anchor>.ipynb   ⭐본편 78편 (생성물) — 번호는 읽는 순서다
report_mesh/               부록 8편 (동결)
prior_work/                선행연구 조사 원자료

src/
  build_part0N_*.py        ⭐편 생성기 — 서술의 원본. 계산은 없다
  build_part00_map.py      지도 편 + 읽기 경로의 정본
  make_reports_index.py    색인 · docs/REPRODUCE.md · docs/paper/README.md
  make_readme.py           이 파일을 만든다
  report_style.py          규약 강제(num()·각주·분량 상한·부정문 계수)
  report_registry.py       앵커 사전 — 편 사이 링크의 유일한 출처
  drones.py                ⭐표적 레지스트리 DRONES — 기종·제원의 유일한 출처
  materials.py             ⭐전파재질 단일 진리원 — Sionna RT 와 PO 가 둘 다 읽는다
  rcs_sbr.py               ⭐SBR+PO 커널 (Mitsuba 광선조준 + PO 표면적분)
  sigma_anchor.py          ⭐측정 앵커 재보정 σ=A(f)·B₁·B₂ + 미통제 항 원장
  waveforms*.py            WiFi/LTE/5G OFDM 합성 + Sionna PHY 대조
  passive_process.py       패시브 DSP: ECA → CAF 거리도플러 → CA-CFAR
  experiment_*.py          검출·자유공간 실험(GPU 몬테카를로)
  viz_*.py                 그림 (텍스트는 전부 영어)

benchmark/
  check_report_links.py    ⭐편 사이 참조 전수 검사
  regen_mesh_dependents.py ⭐재생성 파이프라인 — 무엇을 어느 순서로 돌리나
  mie_pec_sphere.py        기준해 두 개(정확 Mie · 해석 PO) — 커널의 과녁
  verify_*.py              검증 하네스 (편이 읽는 verify_*.json 생산)

outputs/                   *.json(숫자의 원본) · figures/ · reports_index.json
docs/                      REPRODUCE.md · paper/ · repro/ · SPECS.md · MEASUREMENT_PLAN.md
```

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
