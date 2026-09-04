<!-- 생성물 — `src/build_volumes.py` 가 낸다. 손으로 고치지 말고 그 파일을 고쳐라. -->

# 리포트 — 본편 13 권 · 별편 7 편

패시브 바이스태틱 드론 탐지 시뮬레이터의 본문이다. **한 권이 물음 하나를 들고, 권 제목이 그 물음이다.** 권 안의 절은 각각 «한 일 · 결과 · 방법 · 재현» 을 앞에 달고 있어 필요한 절만 따로 읽어도 된다.

처음이면 [리포트 1 «이 연구가 묻는 것과 답한 방식»](01_map.ipynb) 부터다 — 열세 권의 지도와 읽는 경로 셋이 거기 있다.

## 본편 열세 권

| 권 | 이 권이 답하는 물음 | 절 | 한 절만 읽는다면 |
|---|---|---|---|
| [1 «이 연구가 묻는 것과 답한 방식»](01_map.ipynb) | 패시브 바이스태틱으로 드론을 탐지하고 마이크로도플러로 분류하는 것이 태스크이고, RCS 는 그 인프라다. 이… | 3 | [절 3 «주장마다 판정 범위를 결판·사슬확인·캠페인 밖으로 적었다»](01_map.ipynb) |
| [2 «우리 커널 — 무엇이고, 무엇이 아닌가»](02_kernel.ipynb) | SBR + 물리광학이 무엇을 계산하고 무엇을 계산하지 않는지를 정의하고, 해석해가 있는 과녁(구·평판·이면각)… | 6 | [절 4 «해석 PO 구 대비 구현오차는 kr 전 구간에서 λ/16 격자 0.201 dB · 생산 λ/12 격자 0.254 dB 안이다»](02_kernel.ipynb) |
| [3 «σ 를 무엇에 붙들어 매나»](03_anchor.ipynb) | 우리 σ 의 절대 레벨을 붙드는 것은 공개 문헌 한 기체·한 실험실뿐이다. 그 끈의 장력을 재고, 끊어질 자리… | 6 | [절 1 «σ = A(f)·B₁·B₂ 에서 A(f) 의 기울기만 측정에서 받고, 레벨과 각패턴은 우리 SBR+PO 커널(B) 출력이다»](03_anchor.ipynb) |
| [4 «앙각 커버리지 — 어느 각도까지 유효한가»](04_elevation-coverage.ipynb) | 관측 앙각을 0° 에서 −90° 까지 내리며 같은 표적을 재면, 커버리지를 정하는 것은 표적이 아니라 우리가… | 5 | [절 2 «−75° 에서 추적 대역 몫은 고정 대역보다 38.55 dB 크고, 그 차이를 만든 것은 대역을 어디에 놓았는가 하나다»](04_elevation-coverage.ipynb) |
| [5 «엔진의 물리 스위치 — 켜면 무엇이 달라지나»](05_engine-physics.ipynb) | 스톡 PathSolver 의 굴절·회절·모서리회절·다중반사를 하나씩 켜서 무엇이 결과를 만들었는지 귀속한다… | 5 | [절 1 «나딧에서 레벨을 −130.78 dB 에서 −64.23 dB 로 올리는 스위치는 회절 하나다»](05_engine-physics.ipynb) |
| [6 «마이크로도플러 — 도는 로터가 남기는 무늬»](06_1_scene.ipynb) | 호버링하는 드론은 제자리에 있지만 프로펠러는 돈다. 그 회전이 남기는 시간-주파수 무늬가 이 연구의 분류 축이… | 6 | [절 3 «두 엔진이 날개끝 주파수 아래에서 겹치고 그 위에서 갈린다»](06_3_pattern.ipynb) |
| [7 «무엇을 조명원으로 쓸 수 있나»](07_illuminators.ipynb) | LTE·5G·WiFi 가 각각 얼마나 자주, 얼마나 넓게 신호를 내주는가. 5G 는 대역이 넓은 대신 상시 신… | 7 | [절 3 «여섯 항목은 닫힌형이고, 점유 대가만 몬테카를로 격자에서 읽는다»](07_illuminators.ipynb) |
| [8 «처리 사슬 — 직접파를 죽이고 표적을 세운다»](08_detector.ipynb) | ECA 로 직접파를 지우고 CFAR 로 문턱을 세운다. 문턱을 어디에 두느냐가 결과를 정하므로 그 교정을 먼저… | 4 | [절 3 «운용 형상에서 경험 Pfa 를 재니 명목값의 1.52~2.66 배였다»](08_detector.ipynb) |
| [9 «관측가능성과 기하 — 어디에 서야 보이나»](09_observability.ipynb) | 송신기·수신기·표적의 배치가 검출을 정한다. 볼 수 없는 자리를 먼저 지도로 그리고, 그 다음에 거리를 말한다. | 4 | [절 1 «한 순간의 (R_b, f_d) 는 랭크 2 이고, 수신기를 하나 더하면 위치가 풀린다»](09_observability.ipynb) |
| [10 «결과 — 얼마나 멀리서 보이나»](10_results.ipynb) | R90 과 순위가 이 연구의 정량 결론이다. 적분시간·잔류·σ 가정을 흔들어 순위가 견디는지까지 함께 적는다. | 5 | [절 2 «앵커 σ 위의 R90 은 비교가능 12칸에서 3.69~7.44 km 이고, 밴드 순서는 기체마다 바뀐다»](10_results.ipynb) |
| [11 «실측 계획 — 무엇을 재야 이 문서가 닫히나»](11_measurement.ipynb) | 시뮬레이션이 선언으로 남겨 둔 것들의 목록과, 그것을 닫는 야외 실측 규약이다. | 7 | [절 6 «캠페인이 결판내는 양은 절대값이 아니라 순위다»](11_measurement.ipynb) |
| [12 «실외 장면 — 지면과 벽이 서면 무엇이 달라지나»](12_outdoor-scene.ipynb) | 자유공간에서 세운 판정이 지면과 건물이 있는 자리에서도 서는지 묻는다. 실외 기록의 날개 박자는 솔버 인공물에… | 0 | — |
| [A «도감 — 원장의 모든 팔을 그림으로»](A_atlas.ipynb) | 앙각 스윕 원장이 담은 팔 전부를 STFT 맵과 대역 에너지로 펴 둔 재고 목록이다. 판정하지 않는다 — 어느… | 14 | — |

## 권에 딸린 별편 7 편

별편은 **부모 권 물음의 심화·지원·변주**다 — 번호가 «부모번호-K» 이고, 부모를 읽은 뒤에 여는 글이다. 6 권의 다섯 편 · A 권의 열 편은 이것과 달리 그림 무게로 나눈 **분권**(한 권의 장)이다. 6-6 만 파일 이름이 분권 꼬리를 잇고 지위는 별편이다.

| 별편 | 어느 권에 붙나 | 무엇을 하나 | 빌더 |
|---|---|---|---|
| [1-2 «선행연구는 어디까지 왔고 우리는 어디 서는가»](01_2_prior-work.ipynb) | 1 권 | 공개 문헌과 오픈소스를 전수로 세어, 우리가 새로 하는 것과 빌려 쓰는 것을 갈라 적는다 | `src/build_volumes.py (조각 조립)` |
| [2-2 «스톡 Sionna 로는 왜 부족한가»](02_2_stock-engine.ipynb) | 2 권 | 스톡 레이 트레이서는 경로를 풀지 산란적분을 하지 않는다. 그 한 가지가 드론처럼 작은 표적에서 무엇을 무너뜨리는지 여덟 갈래로 잰다 | `src/build_volumes.py (조각 조립)` |
| [2-3 «표적을 짓는다 — 메쉬와 재질»](02_3_target-mesh.ipynb) | 2 권 | 기체 10 대를 CAD 로 짓고, 그중 σ 를 내는 7 대를 실물 사진·도면과 대조한다. 재질은 측정이 아니라 선언이고, 그 선언이 어디까지 미치는지 함께 적는다 | `src/build_volumes.py (조각 조립)` |
| [3-2 «표적을 얼마나 거칠게 그려도 되나 — 사다리와 크기 법칙»](03_2_size-law.ipynb) | 3 권 | 표적 모형을 구·정육면체·상자·평판으로 갈아 끼우는 사다리로 단순화의 값을 재고, 앵커보다 크고 작은 두 기체로 크기전이 법칙을 가르는 계획을 적는다. 사다리의 답이 이르게 나오면 그것부터 의심한다 | `src/build_volumes.py (조각 조립)` |
| [5-2 «물리 스위치 격자 — 회절은 리듬을 지우지 않고 리듬 없는 에코로 덮는다»](05_2_switch-grid.ipynb) | 5 권 | 5 권이 단일축으로 귀속한 회절을 굴절·회절·모서리회절 7 조합 전수 격자로 다시 재고, 절대 세기로 읽어 기전을 가른다 — 회절을 켠 판은 끈 판을 계수 ≈1 로 품고 있고, 날개끝 위 바닥이 올라와 원래 빗살을 덮는다(빗각 −15°~−75°) | `src/build_report18_switch_grid.py` |
| [6-6 «마이크로도플러 — 무엇이 그 무늬를 흐리나»](06_6_microdoppler-limits.ipynb) | 6 권 | 자세·보정·광선 예산·표본율 네 가지가 무늬를 지운다. 각각을 단일축으로 갈라 얼마나 지우는지 잰다 | `src/build_volumes.py (조각 조립)` |
| [10-2 «결론이 무엇에 기대고 있나 — 강건성과 하드웨어»](10_2_robustness.ipynb) | 10 권 | 표적 모형·수신 소자·장비를 바꿔 넣어 결론이 어디서 흔들리는지 본다 | `src/build_volumes.py (조각 조립)` |

셀 2896 개 · 각주 2420 개 · 그림 1045 개.

## 각 권에 어느 조각이 들어갔나

`조각` 칸은 `_parts/` 안의 파일이다. **조각은 사람이 직접 읽는 문서가 아니다** — 조각 빌더(`src/build_partNN_*.py`)의 중간 산출물이고, 권을 조립하는 재료다. 본문을 고칠 일이 생기면 조각이나 권이 아니라 **그 조각을 만든 빌더**를 고치고 다시 조립한다.

### 권 [1 «이 연구가 묻는 것과 답한 방식»](01_map.ipynb)

별편이 한 편 딸려 있다.

- [1-2 «선행연구는 어디까지 왔고 우리는 어디 서는가»](01_2_prior-work.ipynb) (빌더 `src/build_volumes.py (조각 조립)`) — 공개 문헌과 오픈소스를 전수로 세어, 우리가 새로 하는 것과 빌려 쓰는 것을 갈라 적는다.

| 절 | 제목 | 조각 |
|---|---|---|
| 1 | 열세 권의 지도 — 무엇이 어디에 있나 | (이 스크립트가 생성) |
| 2 | 네 관문을 동시에 통과한 게재본은 0편이고, 최근접 3편은 각각 다른 관문에서 걸린다 | `_parts/13_where-we-stand.ipynb` |
| 3 | 주장마다 판정 범위를 결판·사슬확인·캠페인 밖으로 적었다 | `_parts/75_decision-matrix.ipynb` |

### 별편 [1-2 «선행연구는 어디까지 왔고 우리는 어디 서는가»](01_2_prior-work.ipynb)

[리포트 1 «이 연구가 묻는 것과 답한 방식»](01_map.ipynb) 의 **별편**이다.

| 절 | 제목 | 조각 |
|---|---|---|
| 1 | 전문 판정한 게재본 중 드론 메쉬 산란을 엔진 안에서 «검증» 한 것은 0편이다 | `_parts/08_census-published.ipynb` |
| 2 | 프리프린트는 따로 세고, Ziganshin 은 두 판을 구별해 인용한다 | `_parts/09_census-preprint.ipynb` |
| 3 | 표적 서명을 어디서 조달했는지가 그 논문이 낼 수 있는 주장의 크기를 정한다 | `_parts/10_procurement.ipynb` |
| 4 | 조달처 일곱 갈래 R1~R7 을 전수로 적었다 | `_parts/11_procurement-catalog.ipynb` |
| 5 | 외부 σ 주입은 게재돼 있고, 그 값의 대가는 검증이 치른다 | `_parts/12_injection.ipynb` |
| 6 | 선행에서 빌린 절차와 아직 안 빌린 절차를 비용과 함께 센다 | `_parts/14_borrowed.ipynb` |

### 권 [2 «우리 커널 — 무엇이고, 무엇이 아닌가»](02_kernel.ipynb)

별편이 두 편 딸려 있다.

- [2-2 «스톡 Sionna 로는 왜 부족한가»](02_2_stock-engine.ipynb) (빌더 `src/build_volumes.py (조각 조립)`) — 스톡 레이 트레이서는 경로를 풀지 산란적분을 하지 않는다. 그 한 가지가 드론처럼 작은 표적에서 무엇을 무너뜨리는지 여덟 갈래로 잰다.
- [2-3 «표적을 짓는다 — 메쉬와 재질»](02_3_target-mesh.ipynb) (빌더 `src/build_volumes.py (조각 조립)`) — 기체 10 대를 CAD 로 짓고, 그중 σ 를 내는 7 대를 실물 사진·도면과 대조한다. 재질은 측정이 아니라 선언이고, 그 선언이 어디까지 미치는지 함께 적는다.

| 절 | 제목 | 조각 |
|---|---|---|
| 1 | 가림 판정은 Sionna 광선엔진이 하고, 면적분은 우리 커널이 한다 | `_parts/18_kernel-what.ipynb` |
| 2 | 스톡 솔버와 맞대면 «면이 많아서 에코가 커진다» 가설은 반증되고, 런타임의 96.9% 는 호스트가 쓴다 | `_parts/19_kernel-vs-stock.ipynb` |
| 3 | 수신 방향 그림자 광선을 켜면 상반성 위반이 9.69 → 8.24 dB 로 내려간다 | `_parts/20_bistatic-exit.ipynb` |
| 4 | 해석 PO 구 대비 구현오차는 kr 전 구간에서 λ/16 격자 0.201 dB · 생산 λ/12 격자 0.254 dB 안이다 | `_parts/21_kernel-vs-reference.ipynb` |
| 5 | PO 유효 무릎을 부품 폭으로 옮기면 어느 부품이 어느 밴드에서 떨어지는지가 보인다 | `_parts/22_po-knee.ipynb` |
| 6 | 커널이 아직 못 하는 것은 편파 분리·PTD·재테셀레이션·다중반사 Γ(θ) 넷이고, 각각의 크기를 적었다 | `_parts/23_kernel-open-items.ipynb` |

### 별편 [2-2 «스톡 Sionna 로는 왜 부족한가»](02_2_stock-engine.ipynb)

[리포트 2 «우리 커널 — 무엇이고, 무엇이 아닌가»](02_kernel.ipynb) 의 **별편**이다.

| 절 | 제목 | 조각 |
|---|---|---|
| 1 | Sionna 기술보고서 59쪽에 physical optics 는 0회, SBR 은 44회 나온다 | `_parts/01_stock-says.ipynb` |
| 2 | 경로는 SBR 과 이미지법이 정한다 | `_parts/02_engine-paths.ipynb` |
| 3 | 진폭은 국소 평면파–평면경계 해 하나로 만들어진다 | `_parts/03_engine-amplitude.ipynb` |
| 4 | 필드 갱신 인자 여덟 개에 면적·곡률·치수·λ 가 없다 | `_parts/04_eight-factors.ipynb` |
| 5 | 면적을 1600배로 키워도 경로 진폭은 7.4e-07 dB 움직인다 | `_parts/05_size-sweep.ipynb` |
| 6 | 표적 항이 비에서 소거되는가와 절대값이 필요한가, 두 물음이 실험을 네 칸으로 가른다 | `_parts/06_decision-table.ipynb` |
| 7 | 완전파는 정확도의 과녁이고, SBR+PO 는 표를 만들 수 있는 비용대에서 가장 정확하다 | `_parts/07_why-po.ipynb` |

### 별편 [2-3 «표적을 짓는다 — 메쉬와 재질»](02_3_target-mesh.ipynb)

[리포트 2 «우리 커널 — 무엇이고, 무엇이 아닌가»](02_kernel.ipynb) 의 **별편**이다.

| 절 | 제목 | 조각 |
|---|---|---|
| 1 | 기체 7종을 제원과 제조사 CAD 치수에서 세우고 부품을 재질 그룹으로 유지했다 | `_parts/15_mesh-build.ipynb` |
| 2 | 메쉬 외형이 실제 기체와 얼마나 맞는지를 사진 IoU·CAD 치수·실물 스캔 세 자로 쟀다 | `_parts/16_mesh-vs-real.ipynb` |
| 3 | 도전성 재질이 면적의 45.3% 로 Σ|Γ|A 의 73.5% 를 낸다 | `_parts/17_materials.ipynb` |

### 권 [3 «σ 를 무엇에 붙들어 매나»](03_anchor.ipynb)

별편이 한 편 딸려 있다.

- [3-2 «표적을 얼마나 거칠게 그려도 되나 — 사다리와 크기 법칙»](03_2_size-law.ipynb) (빌더 `src/build_volumes.py (조각 조립)`) — 표적 모형을 구·정육면체·상자·평판으로 갈아 끼우는 사다리로 단순화의 값을 재고, 앵커보다 크고 작은 두 기체로 크기전이 법칙을 가르는 계획을 적는다. 사다리의 답이 이르게 나오면 그것부터 의심한다.

| 절 | 제목 | 조각 |
|---|---|---|
| 1 | σ = A(f)·B₁·B₂ 에서 A(f) 의 기울기만 측정에서 받고, 레벨과 각패턴은 우리 SBR+PO 커널(B) 출력이다 | `_parts/24_anchor-mode.ipynb` |
| 2 | 앵커가 통제한 항목과 남은 항목의 크기를 기체별 원장으로 적었다 | `_parts/25_anchor-ledger.ipynb` |
| 3 | Phantom 3 를 문헌값을 보지 않고 내고 봉인을 풀었다 | `_parts/26_blind-p3.ipynb` |
| 4 | 메쉬가 사는 축은 절대 크기가 아니라 각도 구조다 | `_parts/27_box-sphere-control.ipynb` |
| 5 | 같은 잣대를 네 기체로 넓히면 판정이 NOT_VALIDATED 로 갈린다 | `_parts/28_fleet-prereg.ipynb` |
| 6 | 공통모드 σ 오차는 파형 순위를 안 건드리고, 차분 오차가 뒤집는다 | `_parts/29_sigma-robustness.ipynb` |

### 별편 [3-2 «표적을 얼마나 거칠게 그려도 되나 — 사다리와 크기 법칙»](03_2_size-law.ipynb)

[리포트 3 «σ 를 무엇에 붙들어 매나»](03_anchor.ipynb) 의 **별편**이다.

| 절 | 제목 | 조각 |
|---|---|---|
| 1 | 사다리가 하나가 아니라 셋이었다 — 여섯 단이 서로 다른 운동학을 쓰고 있었다 | `_parts/30_ladder-three.ipynb` |
| 2 | 몸통은 진짜 CAD, 프로펠러만 갈아 끼운 교정 사다리가 답할 자격이 있는 유일한 축이다 | `_parts/31_ladder-calibrated.ipynb` |
| 3 | 모양의 유무는 수십 dB 를 가르고, 모양의 정밀도는 한 자릿수 dB 안에서 논다 | `_parts/32_ladder-answer.ipynb` |
| 4 | 이 답을 아직 결론이라고 부를 수 없는 이유가 일곱 가지이고, 그중 둘이 치명적이다 | `_parts/33_ladder-premature.ipynb` |
| 5 | 두 기체를 함께 재면 크기전이 법칙이 차등신호의 부호 하나로 갈린다 | `_parts/77_size-law-differential.ipynb` |

### 권 [4 «앙각 커버리지 — 어느 각도까지 유효한가»](04_elevation-coverage.ipynb)

| 절 | 제목 | 조각 |
|---|---|---|
| 1 | 앙각 7 점을 15 m 한 자리에서 광선 40 억 발로 재고, 77 행이 모두 완결이다 | `_parts/78_el-sweep-design.ipynb` |
| 2 | −75° 에서 추적 대역 몫은 고정 대역보다 38.55 dB 크고, 그 차이를 만든 것은 대역을 어디에 놓았는가 하나다 | `_parts/79_el-band-tracking.ipynb` |
| 3 | 물리 상한 위 누설은 우리 팔(λ/12 격자) 0.22~17.18 %, 스톡 PathSolver 0.81~96.17 % 이고, 물리를 켜면 여섯 앙각이 전부 78 % 위다 | `_parts/80_el-above-tip-limit.ipynb` |
| 4 | 나딧 잔여의 64 % 는 광선 격자 표본화 잡음이고, 널은 나딧 −49.18 dB 에서 10° −23.73 dB 로 완만히 차는 얕은 웅덩이다 | `_parts/82_el-nadir-floor.ipynb` |
| 5 | el 0 에서 광선을 360 배 늘리면 정지 성분은 0.03 dB 안에 모이고, 같은 한 계단이 el −75 의 레벨을 12.55 dB 옮긴다 | `_parts/87_budget-not-physics.ipynb` |

### 권 [5 «엔진의 물리 스위치 — 켜면 무엇이 달라지나»](05_engine-physics.ipynb)

별편이 한 편 딸려 있다.

- [5-2 «물리 스위치 격자 — 회절은 리듬을 지우지 않고 리듬 없는 에코로 덮는다»](05_2_switch-grid.ipynb) (빌더 `src/build_report18_switch_grid.py`) — 5 권이 단일축으로 귀속한 회절을 굴절·회절·모서리회절 7 조합 전수 격자로 다시 재고, 절대 세기로 읽어 기전을 가른다 — 회절을 켠 판은 끈 판을 계수 ≈1 로 품고 있고, 날개끝 위 바닥이 올라와 원래 빗살을 덮는다(빗각 −15°~−75°).

| 절 | 제목 | 조각 |
|---|---|---|
| 1 | 나딧에서 레벨을 −130.78 dB 에서 −64.23 dB 로 올리는 스위치는 회절 하나다 | `_parts/83_physics-single-axis.ipynb` |
| 2 | AC/DC 가 +0.89 dB 에서 −68.13 dB 로 내려간 것은 분모가 66.55 dB 이상 커진 결과다 | `_parts/84_physics-denominator.ipynb` |
| 3 | 광선을 250M 으로 맞추면 물리 스위치가 상한 위 몫에 남기는 것은 앙각 0° 에서 0.00084 이고, 기울인 세 앙각에서 0.55~0.77 다 | `_parts/85_physics-above-limit.ipynb` |
| 4 | 우리 커널은 덱 3~40 m 판과 0.9141~0.9877 로 겹치고, 엔진이 바뀐 3 칸은 0.6291~0.6961 다 | `_parts/86_physics-deck-match.ipynb` |
| 5 | 이 비교가 세우는 것은 el −90 한 자리의 스위치 귀속이고, 절대 σ 는 산포 16.27 dB 로 미검증이다 | `_parts/88_engine-claim-scope.ipynb` |

### 권 [6 «마이크로도플러 — 도는 로터가 남기는 무늬»](06_1_scene.ipynb)

그림이 무거워 **5 편**으로 나뉜다 — 별편이 아니라 **분권**, 곧 한 권의 장이다(빌더 `src/make_report08_microdoppler.py (06_5 만 src/make_report07b_bistatic.py)`).

| 편 | 무엇에 답하나 |
|---|---|
| [06_1_scene.ipynb](06_1_scene.ipynb) | 무엇을 보고 있나 — 시나리오와 신호의 정체 |
| [06_2_engines.ipynb](06_2_engines.ipynb) | 어떻게 계산하나 — 세 엔진과 거리 |
| [06_3_pattern.ipynb](06_3_pattern.ipynb) | 무엇이 무늬를 정하나 — 회전수·가림·산포 |
| [06_4_sampling.ipynb](06_4_sampling.ipynb) | 무엇을 잴 수 있나 — 광선 비용과 반복률 |
| [06_5_bistatic.ipynb](06_5_bistatic.ipynb) | 송수신이 갈라지면 — 바이스태틱 도플러·플래시·에코 |

아래 절은 이 스크립트가 `06_3_pattern.ipynb` 뒤에 이어 붙인 것이다.

별편이 한 편 딸려 있다.

- [6-6 «마이크로도플러 — 무엇이 그 무늬를 흐리나»](06_6_microdoppler-limits.ipynb) (빌더 `src/build_volumes.py (조각 조립)`) — 자세·보정·광선 예산·표본율 네 가지가 무늬를 지운다. 각각을 단일축으로 갈라 얼마나 지우는지 잰다.

| 절 | 제목 | 조각 |
|---|---|---|
| 1 | 스톡 Paths.doppler 로는 블레이드 변조가 안 나온다 — SceneObject.velocity 가 객체당 강체 1벡터다 | `_parts/34_md-paths-doppler.ipynb` |
| 2 | 시간표본마다 자세를 새로 놓고 다시 쏘아 슬로타임 복소열을 만든다 | `_parts/35_md-slowtime.ipynb` |
| 3 | 두 엔진이 날개끝 주파수 아래에서 겹치고 그 위에서 갈린다 | `_parts/36_md-two-engines.ipynb` |
| 4 | 네 로터가 같은 회전수로 돌면 무늬는 시간에 못 변한다 | `_parts/37_md-rpm.ipynb` |
| 5 | 동체가 날개를 가리면 변조 깊이와 레벨이 함께 바뀐다 | `_parts/38_md-occlusion.ipynb` |
| 6 | 블레이드 신호는 약하지 않다 — 동체 정적 반사가 덮고 있을 뿐이다 | `_parts/39_md-blade-vs-body.ipynb` |

### 별편 [6-6 «마이크로도플러 — 무엇이 그 무늬를 흐리나»](06_6_microdoppler-limits.ipynb)

[리포트 6 «마이크로도플러 — 도는 로터가 남기는 무늬»](06_1_scene.ipynb) 의 **별편**이다.

| 절 | 제목 | 조각 |
|---|---|---|
| 1 | 지상 레이더는 기체를 아래에서 보므로 가림이 무는 자세가 우리 자세다 | `_parts/40_md-attitude.ipynb` |
| 2 | 문턱은 널 팔이 교정했고, 가장자리 시험은 아직 교정되지 않았다 | `_parts/41_md-calibration.ipynb` |
| 3 | 두 기체가 갈리는 축은 메쉬 품질이 아니라 표적 크기 대비 광선예산이다 — 예산을 맞춰 확인하는 시험은 이 하네스에서 아직 못 한다 | `_parts/42_md-ray-budget.ipynb` |
| 4 | 상시 기준신호가 주는 것은 날개끝 확산이 아니라 블레이드 통과율까지다 | `_parts/43_md-prf.ipynb` |

### 권 [7 «무엇을 조명원으로 쓸 수 있나»](07_illuminators.ipynb)

| 절 | 제목 | 조각 |
|---|---|---|
| 1 | 상시이면서 내용을 미리 아는 신호는 표준마다 하나씩 있다 | `_parts/44_illuminators.ipynb` |
| 2 | 5G 는 좁고 드물다 — 두 배의 대가를 치른다 | `_parts/45_5g-double-cost.ipynb` |
| 3 | 여섯 항목은 닫힌형이고, 점유 대가만 몬테카를로 격자에서 읽는다 | `_parts/46_cost-ledger.ipynb` |
| 4 | 바이스태틱 거리 분해능은 c/B, 잡음대역은 √(B/fs) 로 고정한다 | `_parts/47_range-convention.ipynb` |
| 5 | 같은 자원격자를 독립 변조기에 넣으면 같은 시간파형이 나온다 | `_parts/48_waveform-check.ipynb` |
| 6 | 검출기가 실제로 쓰는 커널 그대로 모호함수를 그렸다 | `_parts/49_ambiguity.ipynb` |
| 7 | 5G SSB 는 걷는 드론에서 접힌다 | `_parts/50_doppler-fold.ipynb` |

### 권 [8 «처리 사슬 — 직접파를 죽이고 표적을 세운다»](08_detector.ipynb)

| 절 | 제목 | 조각 |
|---|---|---|
| 1 | 수신 → ECA → 거리도플러 → CFAR, 사슬의 형상은 파형이 정한다 | `_parts/51_chain.ipynb` |
| 2 | 탭을 늘리면 환경이 정한 바닥에서 멈추고, 그 대가가 0-도플러 노치다 | `_parts/52_eca.ipynb` |
| 3 | 운용 형상에서 경험 Pfa 를 재니 명목값의 1.52~2.66 배였다 | `_parts/53_cfar-calib.ipynb` |
| 4 | 그 배율의 원인은 셀 상관이고, 교정표는 형상마다 다시 재야 한다 | `_parts/54_cfar-why.ipynb` |

### 권 [9 «관측가능성과 기하 — 어디에 서야 보이나»](09_observability.ipynb)

| 절 | 제목 | 조각 |
|---|---|---|
| 1 | 한 순간의 (R_b, f_d) 는 랭크 2 이고, 수신기를 하나 더하면 위치가 풀린다 | `_parts/55_observability.ipynb` |
| 2 | TX·RX·표적 배치와 β·앙각·원거리장이 유효창을 연다 | `_parts/56_geometry.ipynb` |
| 3 | 세 밴드에서 값이 다른 항은 λ² 와 σ 둘뿐이다 | `_parts/57_sensitivity-chain.ipynb` |
| 4 | 자유공간 형상에서 문턱을 다시 재니 세 밴드가 SNR90 하나를 공유한다 | `_parts/58_shared-threshold.ipynb` |

### 권 [10 «결과 — 얼마나 멀리서 보이나»](10_results.ipynb)

별편이 한 편 딸려 있다.

- [10-2 «결론이 무엇에 기대고 있나 — 강건성과 하드웨어»](10_2_robustness.ipynb) (빌더 `src/build_volumes.py (조각 조립)`) — 표적 모형·수신 소자·장비를 바꿔 넣어 결론이 어디서 흔들리는지 본다.

| 절 | 제목 | 조각 |
|---|---|---|
| 1 | 레벨을 맞추려면 크기전이 법칙을 골라야 하므로 기울기만 받는다 | `_parts/59_slope-anchor.ipynb` |
| 2 | 앵커 σ 위의 R90 은 비교가능 12칸에서 3.69~7.44 km 이고, 밴드 순서는 기체마다 바뀐다 | `_parts/60_r90.ipynb` |
| 3 | 그 순위는 자세평균이면 하나로 모이고, 자세평균 뒤집힘 문턱은 현실 봉투 안이다 | `_parts/61_rank-durability.ipynb` |
| 4 | CPI 를 늘리면 세 파형 모두 블라인드율이 내려간다 | `_parts/62_cpi-sweep.ipynb` |
| 5 | 모호속도는 표본화율의 성질이라 CPI 와 무관한 상한이다 | `_parts/63_cpi-residual.ipynb` |

### 별편 [10-2 «결론이 무엇에 기대고 있나 — 강건성과 하드웨어»](10_2_robustness.ipynb)

[리포트 10 «결과 — 얼마나 멀리서 보이나»](10_results.ipynb) 의 **별편**이다.

| 절 | 제목 | 조각 |
|---|---|---|
| 1 | σ 를 곱하기 전에 이미 세 파형의 순서를 정하는 축이 있다 | `_parts/64_sigma-free-axis.ipynb` |
| 2 | 평판·큐브·우리 격자를 같은 동작점에서 갈아끼우면 요구 이득이 이만큼 달라진다 | `_parts/65_target-model-swap.ipynb` |
| 3 | 코히어런트 배열이득은 10log₁₀N 상한에 -0.11~+0.47 dB 로 붙는다 | `_parts/66_rx-elements.ipynb` |
| 4 | X410 의 12-bit ADC 동적범위가 직접파 제거의 천장이다 | `_parts/67_hardware.ipynb` |
| 5 | 교정된 절대 σ 를 만드는 조건은 여섯 항목이 전부다 | `_parts/68_sigma-checklist.ipynb` |

### 권 [11 «실측 계획 — 무엇을 재야 이 문서가 닫히나»](11_measurement.ipynb)

| 절 | 제목 | 조각 |
|---|---|---|
| 1 | 가장 보수적인 D 정의로도 세션 거리 하나가 두 기체 세 밴드를 덮는다 | `_parts/69_site-geometry.ipynb` |
| 2 | 구가 σ 를 절대량으로 만들고, 반경 17.8 cm 를 고른다 | `_parts/70_calibration-sphere.ipynb` |
| 3 | 표적을 한 거리빈에 넣는 최대 대역은 200 MHz 다 | `_parts/71_subband.ipynb` |
| 4 | 가장 촘촘한 요구 1.38° 를 세션 간격으로 채택해 앵커 문헌의 고정 2° 보다 촘촘하게 간다 | `_parts/72_attitude.ipynb` |
| 5 | σ(f) 레인지·파형축·비행검출로 층을 나눈다 | `_parts/73_three-layers.ipynb` |
| 6 | 캠페인이 결판내는 양은 절대값이 아니라 순위다 | `_parts/74_sim-vs-meas.ipynb` |
| 7 | 기울기 판정의 문턱은 세션간 진폭 재현성이고, σ 사슬 세대를 바꾸면 그 문턱이 손닿는 범위 밖으로 좁아진다 | `_parts/76_session-drift.ipynb` |

### 권 [12 «실외 장면 — 지면과 벽이 서면 무엇이 달라지나»](12_outdoor-scene.ipynb)

그림이 무거워 **1 편**으로 나뉜다 — 별편이 아니라 **분권**, 곧 한 권의 장이다(빌더 `src/build_report12_outdoor.py`).

| 편 | 무엇에 답하나 |
|---|---|
| [12_outdoor-scene.ipynb](12_outdoor-scene.ipynb) | 실외 장면 — 지면과 벽이 서면 무엇이 달라지나 |

아래 절은 이 스크립트가 `12_outdoor-scene.ipynb` 뒤에 이어 붙인 것이다.

| 절 | 제목 | 조각 |
|---|---|---|

### 권 [A «도감 — 원장의 모든 팔을 그림으로»](A_atlas.ipynb)

그림이 무거워 **10 편**으로 나뉜다 — 별편이 아니라 **분권**, 곧 한 권의 장이다(빌더 `benchmark/build_atlas_toc.py (그림은 benchmark/build_md_atlas.py)`).

| 편 | 무엇에 답하나 |
|---|---|
| [A_atlas.ipynb](A_atlas.ipynb) | 도감 지도 — 읽는 법 · 편 목록 · 이름 규약 · 주의 |
| [A_atlas_A.ipynb](A_atlas_A.ipynb) | 기본 엔진 — 엔진·광선예산·자세수, ⚠거리도 10 m·15 m 로 섞여 있다 |
| [A_atlas_B.ipynb](A_atlas_B.ipynb) | 스위치 — 굴절·회절·모서리·확산을 켜고 끈 조합 |
| [A_atlas_C.ipynb](A_atlas_C.ipynb) | 기체 3 종 — 박자가 기체마다 다르다 |
| [A_atlas_D.ipynb](A_atlas_D.ipynb) | 방위 — 정면 말고 45° 에서 본 판 |
| [A_atlas_E.ipynb](A_atlas_E.ipynb) | 부품 분해 — 프로펠러만 / 동체만 |
| [A_atlas_F.ipynb](A_atlas_F.ipynb) | 거리 — 15 m 아닌 판(30 m) |
| [A_atlas_G.ipynb](A_atlas_G.ipynb) | PTD — 모서리 보정을 켠 판 |
| [A_atlas_H.ipynb](A_atlas_H.ipynb) | 격자 — λ/12 대신 더 촘촘한 격자 |
| [A_atlas_I.ipynb](A_atlas_I.ipynb) | 평면파 — 구면파 대신 평면파로 조명한 판 |

아래 절은 이 스크립트가 `A_atlas.ipynb` 뒤에 이어 붙인 것이다.

| 절 | 제목 | 조각 |
|---|---|---|

## 권에 넣지 않은 조각

| 조각 | 이유 |
|---|---|
| `_parts/00_map.ipynb` | «편 78 개 · 부 12 개» 라는 폐지된 편성 자체를 설명하는 글이라, 번호만 고쳐서는 말이 서지 않는다. 그 자리는 이 스크립트가 짓는 1 권 절 1 «지도» 가 대신한다. |

## 다시 만들려면

순서가 중요하다 — ③ 이 ② 의 산출물 뒤에 절을 덧붙이기 때문이다.

```bash
PYTHONPATH=src python src/build_part00_map.py              # ① 조각 빌더 14 개
#  … build_part01_stock_engine.py … build_part13_engine_physics.py
PYTHONPATH=src python src/make_report08_microdoppler.py    # ② 6 권 1~4 편
PYTHONPATH=src python src/make_report07b_bistatic.py       # ②' 6 권 5 편
PYTHONPATH=src python src/make_report11_2_two_channel.py   # ②" 별편 8-2
PYTHONPATH=src python src/build_report18_switch_grid.py    # ②" 별편 5-2
PYTHONPATH=src python src/build_volumes.py                 # ③ 조각 → 권 + 색인 + 이 파일
PYTHONPATH=src python benchmark/check_report_links.py      # ④ 검사
```

기계용 색인은 [`outputs/volumes_index.json`](../outputs/volumes_index.json), 구조 설명서는 [`docs/REPORTS_VOLUMES.md`](../docs/REPORTS_VOLUMES.md) 다.
