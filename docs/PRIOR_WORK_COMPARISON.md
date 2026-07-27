# 선행연구 대조 — 방법론 차용 · 결과 정량비교

> 작성 2026-07-23. 리포트 01~13 전편에 대해 (A) 선행이 확립한 규약을 우리가 따르게 하고,
> (B) 우리 숫자와 선행 숫자를 나란히 놓은 결과를 기록한다.
> **이 문서에 실린 비교는 전부 적대적 검증을 통과한 것만이다.** 검증에서 죽은 비교는
> §14 "폐기된 비교" 에 사유와 함께 남긴다 — 죽였다는 사실 자체가 결과다.
> 우리 숫자는 전부 `outputs/*.json` 을 이 문서 작성 시점에 직접 읽어 재확인했다.

---

## 0. 왜 이 문서가 있나

사용자 지시는 두 가지였다.

> "선행연구에서 이미 비슷한 일을 한 것이 있고 참고할 수 있다면 그 방법론을 최대한 가져와서
> 활용해주고, 추가로 선행 연구에서의 결과와 우리가 만들어 낸 결과를 비교도 해보고"

이 프로젝트의 기여는 **새로운 물리가 아니다**. 우리는 새 산란 이론을 만들지 않았고, 새 검출기를
발명하지도 않았다. 우리가 가진 것은 **통제된·재현가능한 벤치마크**다 — 같은 챔버, 같은 표적,
같은 검출 체인 위에서 조명원만 바꿔 공정하게 재는 것.

그렇다면 기여의 가치는 전적으로 **비교가능성**에 달려 있다. 우리가 쓰는 축(ΔR_b 의 좌표계,
점유율의 정의, Pfa 의 정의, σ 의 통계량)이 문헌 관행과 어긋나면, 우리 숫자는 아무와도 견줄 수
없는 고아가 된다. **선행 규약을 따를수록 우리 벤치마크의 가치가 올라간다.** 이것이 (A) 의 이유다.

(B) 는 더 위험한 작업이다. 밴드·기종·기하·지표정의가 어긋난 두 숫자를 나란히 놓으면 그것은
비교가 아니라 착시다. 그래서 이 문서의 모든 비교표에는 **사과-대-사과** 열이 있고, `false` 인
항목은 방향성 진술까지만 허용한다. 그리고 **비교를 만들려다 실패한 것을 숨기지 않는다** —
§14 가 이 문서에서 가장 정직한 절이다.

### 이 문서의 판정 기준

| 기호 | 뜻 |
|---|---|
| **adopt** | 규약을 그대로 채택. 우리 파이프라인에서 성립함이 확인됨 |
| **partial** | 일부만 채택. 단서를 반드시 병기 |
| **reject** | 채택하지 않음. 이식하면 우리 파이프라인에서 깨짐 |
| 사과-대-사과 `true` | 밴드·기하·지표정의가 모두 정합. 숫자를 나란히 놓아도 됨 |
| 사과-대-사과 `false` | 어긋난 축이 있음. **방향성 진술만** 허용 |
| **미확인** | 원문 PDF 를 열지 못했거나 저장소에 없음. 인용 시 그렇게 표기 |

### 선행연구 자산의 등급

| 등급 | 뜻 | 이 문서에서의 취급 |
|---|---|---|
| **[P]** | 로컬 PDF 원문을 직접 열어 축자 확인 | 수치 인용 가능 |
| **[N]** | 워크스페이스 노트(.md)만 존재, PDF 없음 | 수치 인용 시 "노트 근거" 명시 |
| **[W]** | `prior_work.json` 의 웹 메타데이터만 | 방향성 근거로만, "원문 미확인" 병기 |

저장소 실사 결과(이 문서 작성 시 확인):
- `/data/public/jeong/papers/{5G,LTE,Wifi}/` — 패시브 드론 검출 PDF **21편** [P]
- `/data/public/sionna_jeong/papers_isac_sionna/` — ISAC/Sionna PDF **27편** [P]
- `refs/drone_papers/*.md` — Li&Ling·Ezuma·Semkin·Quevedo·DTMB **5편 전부 [N]**
  (전 디스크 검색 결과 이 5편의 PDF 는 존재하지 않는다)
- `prior_work/outputs/prior_work.json` — 14편, 대부분 grade `WEB`/`SOURCE` [W]

---

## 1. 리포트 01 — 통제 환경(반무향 챔버, 바닥 반사)

### 선행은 이렇게 했다

| 선행 | 등급 | 무엇을 했나 | 경로 |
|---|---|---|---|
| Sionna RT 기술보고서 arXiv:2504.21719 (Sionna 1.x/2.x) | [W] | PathSolver 경로계산 = **SBR(경로 열거) + image method**, 프레넬 계수 식 (127)(128) 명시 | `prior_work/sionna_sensing_survey.md` (2.0.1 문서 기반 2차 노트) |
| Hoydis 외, Sionna RT 창설논문 arXiv:2303.11103 | [W] | 스톡 솔버 아키텍처: image method + 확산계수 + 1차 회절, 반환값은 **경로별 복소이득** | `prior_work/outputs/prior_work.json` (key `sionna_rt`, grade SOURCE, 로컬 PDF 없음) |
| Pegurri 외, VaN3Twin arXiv:2505.14184 (IEEE TWC) | [P] | 차량/건물 재질을 **ITU-R P.2040** 키로 부여 | `/data/public/sionna_jeong/sionna_papers_by_task/digital_twin/2505.14184__*.pdf` |
| Manukyan 외 arXiv:2507.19653 | [N] | 도시 RSSI 충실도가 PathSolver 노브(max_depth·토글)에 **무감** = "죽은 파라미터" | `deep_read_notes_topvenue.md` L210-217 |

### 우리가 가져올 규약

- **adopt** — 환경 전파를 스톡 `PathSolver` 에 맡기고 엔진을 재사용한다. report01 이 이미 그렇게 한다.
- **adopt** — §4 의 "세기 일치는 항등식" 캐비엇의 1차 인용처를 **2504.21719 (프레넬 식 127-128 + image method)** 로 한다.
  창설논문(2303.11103)의 "위상 말고 전력으로 캘리브레이션하라" 는 인용하지 **않는다** — 그 문장은
  *실측으로 재질을 학습시킬 때*의 경고이고 권고 방향이 "전력을 신뢰하라" 라서, 전력 일치를 항등식으로
  낮추고 지연을 승격하는 report01 서술과 **정반대**다. 게다가 같은 논문에 image method 문장이 있어
  심사자가 인용을 따라가면 "지연=독립증거" 주장까지 무너진다.
- **partial** — ITU-R P.2040 을 재질 진리원으로. 단 **면적 기준 8% 에만 참**이다(아래 표).
- **reject** — VaN3Twin 의 "결정론 RT > 확률적 LoS/NLoS". 그 논문의 대립축은 *결정론 RT vs 통계 채널모델*
  (둘 다 실외)이고 report01 의 대립축은 *통제된 방 vs 실환경*(둘 다 RT). 축 바꿔치기라 챔버 선택을 정당화하지 못한다.
- **reject** — Neural ISAC(2509.21118)의 "방이 커지면 클러터↓". 메커니즘이 다르다(그들=경로손실,
  우리 SCR 불변=ECA 도플러-0 사영). 게다가 **우리 자체 RT 가 반증한다**(아래).

### 수치 비교표

| 항목 | 우리값(정의) | 선행값(정의) | 사과-대-사과 | 정직한 해석 |
|---|---|---|---|---|
| 챔버 바닥 콘크리트 σ | 0.123087 S/m, εr 5.24 @3.5 GHz (`report1.json chamber.materials.concrete_light`) | ITU-R P.2040 콘크리트식 σ = 0.0462·f_GHz^0.7822 | **true**(규약 출처 확인) | 역산 결과 3.5 GHz 에서 정확히 일치. 1.8 GHz→0.0732, 5.2 GHz→0.1678 이므로 **밴드 스냅샷**임을 병기해야 한다 |
| ITU 재질이 덮는 챔버 면적 | 삼각형 19,988 중 **1,548개(7.7%)** 만 ITU (concrete 1,200 + metal 348) | VaN3Twin: 차량·건물 전면 P.2040 | **false**(적용 대상 다름) | 챔버의 **92.0%(18,392 삼각형)는 흡수체**이고 그 재질은 `source: "custom"`, `note: "⚠ 실측치 아님 — 모델값"`, 단일면 \|Γ\|=0.549 다. "우리 재질층은 문헌 표준에 정합" 은 **면적 기준 8% 에만 참** |

### 대응 선행 없음

- **단일 정반사 경로의 image-source + 프레넬 닫힌형 자기일치 대조** — 우리 아카이브(115편 + PDF 48편)
  안에 같은 검증을 한 선행이 없다. 선행의 RT 검증은 전부 실측(AIRMap·GEO2SIGMAP·RIS 캘리브레이션)
  또는 풀웨이브 EM(Ziganshin/FEKO)이다. 다만 report01 자신이 세기 일치를 항등식이라 밝혔으므로
  이 검증은 **"고유하지만 약한(구현 일관성) 증거"** 로 남는다. 그리고 "문헌에 없다" 가 아니라
  **"우리 아카이브 안에 없다"** 로 써야 한다(웹 예산 소진으로 전수 아님).
- **조명원(WiFi vs LTE vs 5G) 공정 비교용 통제 시뮬 챔버** — 선례 미발견. 문헌의 무향실은
  RCS/하드웨어 특성화용이다.

### ⚠ 이 절이 드러낸 우리 쪽 문제

`report3_rt.json` 을 직접 읽은 결과, **챔버에서 가장 센 표적무관 반사는 바닥이 아니다**:

| 경로 | 지연 | 직접파 대비 |
|---|---|---|
| 천장 흡수체 1회 (`S1_depth` max_depth=1) | 12.97 ns | **−9.82 dB** |
| 정면 흡수체 2회 (`S2_floor.twins`) | 19.33 ns | **−11.63 dB** |
| **바닥 1회** (`S2_floor.rt_floor`) | 19.31 ns | −14.68 dB |

즉 "반무향이라 바닥만 반사한다" 는 서술은 물리적으로 부정확하다 — 흡수체(모델값 \|Γ\|=0.549)가
바닥보다 세게 돌아온다. 진짜 통제는 물리적 단일반사가 아니라 **ECA 의 도플러-0 제거**(report09)다.
report01 은 caveat 에서 이미 이 선을 긋고 있으므로 §2 본문에도 −9.8 dB 를 명시해야 한다.

또한 `A_static_floor.pred` 는 `rel_db_tm = −14.683` 과 `rel_db_te = −8.536` 을 **분리 계산**한다.
"−14.7 dB" 는 TM 전용 값이고 TE 는 6.1 dB 더 세다 — 패시브 조명원의 편파가 정해지지 않았으므로
"TM 기준" 을 선언해야 한다.

---

## 2. 리포트 02 — 드론 3D 파라메트릭 CAD

### 선행은 이렇게 했다

| 선행 | 등급 | 무엇을 했나 | 경로 |
|---|---|---|---|
| Ziganshin 외 arXiv:2604.05991 | [P] | 곡면 표적을 facet 이산화. 위상오차 Δφ~2πs/λ, 무차원 지표 **E²/(Rλ)**. i-MiEV 3 GHz 에서 0.4–0.6. 구 케이스 앵커: **0.61 @346 facets, 1.34 @156 facets**. 메쉬 위생을 **정성 요구사항**으로 언급("removal of small details, correction of **non-manifold edges**, and **intersecting facets**") | `/data/public/sionna_jeong/papers_isac_sionna/2604.05991__ziganshin_curved-body-scattering.pdf` |
| Geo2SigMap arXiv:2312.14303 (DySPAN) | [P] | OSM → Blender → .ply/Mitsuba XML(**객체별** 재질 ref) → Sionna 자동 파이프라인 | `.../channel_modeling_raytracing/2312.14303__*.pdf` |
| VaN3Twin arXiv:2505.14184 (IEEE TWC) | [P] | 차량 메쉬를 body/windows/lights/rims 로 세분해 부위별 radio material 부여 | `.../digital_twin/2505.14184__*.pdf` |
| LAMBDA 2607.03826 / Great-X 2507.08716 / TGNN 2604.08306 / Wu 2606.07328 / Beuster 2402.16591 | [P] | 표적 기하를 (a) 외부 에셋 (b) 점산란체·통계 σ (c) 실측 중 하나로 마련 | `papers_isac_sionna/*.pdf` |

### 우리가 가져올 규약

- **adopt(보고 규약만)** — Ziganshin 의 "facet 변길이를 λ 로 정규화해 공개한다". 우리 `edge_vs_lam52` 가 그것이다.
- **reject(수렴 근거로서)** — Ziganshin 의 이산화 우려를 **subdivision invariance 로 반박하면 안 된다**.
  `verify_mesh_suite.py` 의 `trimesh.subdivide()` 는 **중점 분할**이라 정점을 옮기지 않는다 → 표면이
  비트 단위로 동일 → Δσ = 2.9e-7 dB 는 **항등식**이지 증거가 아니다. 같은 파일 docstring 도
  "표면이 같으니 자명하지만" 이라 적는다. 진짜 수치 놉은 `ray_spacing_convergence` 다.
- **adopt** — Geo2SigMap 의 "소스데이터 → 프로그래매틱 메쉬 → Sionna" 워크플로 패턴.
  단 그들의 재질 태그는 **객체별**(건물 1채 = 재질 1개)이지 부위별이 아니다.
- **partial** — VaN3Twin 의 부위 세분 + 부위별 재질. 단 (i) 그 논문의 P.2040 은 건물/나무/지면이고
  차량은 "metallic bodies" 로만 진술된다, (ii) 그들의 차량 메쉬는 **외부 에셋**(우리가 거부하는 경로)이므로
  "에셋 출처는 거부, 부위세분 규약만 차용" 을 한 문장으로 분리해야 논리가 새지 않는다.
- **reject(방법 차용으로서)** — LAMBDA/Great-X/TGNN/Wu/Beuster. 이들은 **공백 분류의 실증**이지
  차용 대상이 아니다.

### 수치 비교표

| 항목 | 우리값(정의) | 선행값(정의) | 사과-대-사과 | 정직한 해석 |
|---|---|---|---|---|
| facet 변길이 / λ | p95/λ **0.133–0.487**, max/λ **1.81–4.98** (λ=57.54 mm @5.2 GHz, `mesh_verify.json A_geometry.*.edge_vs_lam52`) | Ziganshin: E²/(Rλ) 0.4–0.6 @3 GHz (i-MiEV), 구 앵커 0.61@346 / 1.34@156 facets | **false** (지표 정의: 우리 E/λ vs 그들 E²/(Rλ) — 곡률 R 포함) | 규약은 공유(둘 다 facet 을 λ 에 연동). 최악은 s1000plus p95/λ=0.487 ≈ **λ/2** — "λ/4 보다 촘촘" 은 거짓. E²/(Rλ) 로 직접 견주려면 곡률 R 산출이 필요하고 현재 없다 |
| SBR 광선격자 수렴 | λ/12→λ/24: 방위평균 **−0.143 dB**, per-angle mean 0.498 / p95 **1.399** / max **2.00** dB (`mesh_verify.json I_sbr_subdiv.ray_spacing_convergence`, 3.5 GHz·모노스태틱 후방산란) | (대응 없음) | — | 이것이 우리의 **진짜** 수치 놉이다. 자명한 2.9e-7 dB 만 인용하고 이 2 dB 를 숨기면 선택적 보고다 |
| 대각거리 재현 오차 | matrice4e **−2.30%**, s1000plus **−0.14%**, phantom4 **+1.98%** (`mesh_verify.json C_dims.*.checks.diagonal`) | (대응 없음) | — | 이 3종만 유효하다. **mavic4pro(−0.57%)·mini5pro(0.00%) 는 자기참조**다 — `drones.py:126-129` 가 "diagonal was ESTIMATED (400 mm) … Fitting the frame to the official envelope implies **440.9 mm**" 라 적으므로 441 은 우리 모델 역산값이고, mini5pro 는 면내 배율 1.0 이라 0.00% 가 대수 항등식이다 |
| 외곽 L/W/H 오차 | 0% (전 기종) | (대응 없음) | — | **결과가 아니라 구속조건**이다. `drones.py:274 frame_fit_scale()` 이 bbox 를 envelope 에 강제로 맞춘다(matrice H 잔차 1.9e-14 = 부동소수 지문). 검증으로 인용 금지 |
| 메쉬 위생 게이트 | 5종 불량면(안쪽법선+역와인딩+퇴화) **0**, 그룹별 watertight, Γ맵 all_covered | Ziganshin: 비다양체 모서리·**교차면 제거**를 정성 요구사항으로만 언급 | **false** (선행은 수치 미보고) | "비교 대상이 없다" 는 거짓이다 — 정성 규약은 존재한다. 정직한 형태: "선행은 정성 규약만 말하고 우리는 게이트로 수치화했다. **단 교차면 항목은 의도적으로 위반**한다"(`F_overlap`: mavic4pro battery∩body 786.09 cm³ — 유전체 셸 투과 코히런트 합산을 위해) |

### 대응 선행 없음

- **공개 제원표 → 오픈소스 파라메트릭 드론 CAD + 수밀 검증**. 확인한 8편이 전부 (a) 외부 에셋
  (b) 점산란체/통계 σ (c) 실측 중 하나다. 이 공백은 적대적 검증에서도 무너지지 않았다 — report02 의 진짜 기여.

---

## 3. 리포트 03 — 표적 검증(실물 CAD·스캔·커뮤니티 모델 대조)

### 선행은 이렇게 했다

| 선행 | 등급 | 무엇을 했나 | 경로 |
|---|---|---|---|
| Beuster 외 arXiv:2402.16591 (JC&S 2024, TU Ilmenau) | [P] | BiRa 바이스태틱 테스트베드로 **DJI Phantom 2 쿼드** 반사도 측정(2–18 GHz, 바이스태틱각 10–180°). **정지 프로펠러**("propellers at standstill")와 **회전 블레이드 1장** 마이크로도플러를 **분리 보고**. 데이터셋 공개 | `papers_isac_sionna/2402.16591__*.pdf` |
| LAMBDA 2607.03826 / TGNN 2604.08306 | [P] | 표적 산란을 파이프라인 밖 독립기준(CADFEKO / 점산란체)으로 구해 `h = h_bg + h_target` 로 주입 | `papers_isac_sionna/*.pdf` |

### 우리가 가져올 규약

- **adopt** — Beuster 의 **정지 프로펠러 / 회전 블레이드 분리 보고**. report03 은 정지 메쉬로 σ 를 재고
  회전은 report08 로 미루므로 이 분리를 명시 인용하면 된다. ⚠ 단 부속 서술 3개는 원문 근거가 없으므로
  삭제해야 한다: "헥사콥터"(원문 0회, BiRa 대상은 Phantom 2 단독), "HFSS/FEKO/CST 로 시뮬"
  (그 문장은 상용툴 일반 서베이 문장이지 그들이 쓴 솔버가 아니다), "같은 그림에 겹침"
  (캡션은 measured=상단 / simulated=하단 **별개 서브플롯**).
- **adopt** — LAMBDA/TGNN 의 `h = h_bg + h_target` 아키텍처를 §4 서사 근거로. 단 이들은 **메쉬 기하
  충실도 교차검증을 하지 않는다** — report03 핵심 방법론의 선례로 팔면 안 된다.
- **reject** — Ziganshin 의 HH/VV 편파 분리. **물리적으로 불가능**하다: `grep -ci polari src/rcs_sbr.py
  src/rcs_po.py` = 0, 0. 우리 SBR+PO 는 스칼라다. 채택하려면 편파 PO 엔진을 새로 짜야 한다.
- **reject** — Zhang M350 의 "평균만 인용, 각도별 인용 금지" 를 report03 결과② 의 표준으로 삼는 것.
  **원문 해석이 정반대다** — Zhang 은 σ = A(f) × B1(f,φ) × B2 로 **각도 의존을 결정론적으로 모형화**하고
  (Table V: 로브 중심 0/90/180/270°, 3 dB 폭 20.84/10.47/15.41/14.51°), log-normal 은 **잔차 B2**
  (UAV 기준 N(−0.52, 2.31²) dB)다. 이 잣대로 보면 우리 각도별 6.7–10.8 dB 는 표준 준수가 아니라
  **표준보다 3~5배 나쁜 상태**다.
- **reject** — Sagitta 의 kr 검증을 "우리 SBR+PO 가 옳다" 의 근거로. **인용 방향이 뒤집힌다**(§7 참조).

### 수치 비교표

**이 절에는 살아남은 정량 비교가 없다.** 두 후보 모두 §14 에서 사망했다.

### 대응 선행 없음

- **외부 기체를 제원표만으로 독립 재현 → 기준 기하의 RCS·투영면적 재현 확인**. 문헌 유비 미발견.
  단 이 주장은 아래 결함 때문에 현재 상태로는 쓸 수 없다.

### ⚠ 이 절이 드러낸 우리 쪽 문제 (비교 이전 문제)

1. **Typhoon 은 "독립 재현" 이 아니다.** `benchmark/compare_real_cad.py:105-118` 의 `ours_body_only()`
   가 실물 STL 의 bbox 를 읽어 `envelope_mm` 으로 주입하고 다시 축별 재스케일한다. 그 결과
   `real_cad_compare.json` 의 `bbox_ours_mm` = `bbox_real_mm` 이 **1e-14 까지 동일**하다
   (`[455.4132385253906, 520.3530883789062, 158.2498…]`). 제원만으로 짓는 `ours_typhoon()` 은
   `main()` 에서 **호출되지 않는 죽은 코드**다.
2. **방위 정합이 안 됐다.** `real_cad_compare.json` 의 prop 항목:
   `bbox_real_mm = [52.03, 346.00, 30.00]`(긴 축 Y) vs `bbox_ours_mm = [346.00, 80.37, 21.49]`(긴 축 X)
   → **90° 회전**. Phantom4 스캔도 `compare_phantom_scan.py:33-36` 의 뒤집기 판정이 `if …: pass`
   (죽은 코드)라 정합되지 않았다. 따라서 `d_sigma_rms_db` 6.7–10.8 dB 는 형상 충실도가 아니라
   **상당 부분 방위 미정합**을 재고 있다.
3. **이산화가 통제되지 않았다.** 면수가 9.5×~206× 차이 나는 메쉬를 재질만 PEC 로 통일하고 비교한다 —
   "순수 형상 차이" 라는 전제가 성립하지 않는다. 하필 이 교란을 정확히 다룬 논문이 Ziganshin 이다.
4. **"±1 dB" 헤드라인이 자기 숫자로 거짓이다.** `phantom4_scan_compare.json d_sigma_db = −1.7931`.
   `make_notebook03.py` 는 "−1.25 dB" 를 하드코딩하고 "±1 dB" 를 8회 반복한다.

---

## 4. 리포트 04 — 조명원 파형(WiFi/LTE/5G), 상시 기준신호

### 선행은 이렇게 했다

| 선행 | 등급 | 무엇을 했나 | 경로 |
|---|---|---|---|
| Maksymiuk 외, Rényi Entropy…, *Remote Sensing* 2022, 14, 6146 (DOI 10.3390/rs14236146) | [P] | **SSB 를 "always-on" 이라 직접 표기**. Figure 7 = "Resource grid with **no data payload, only the SSB signal is present**". 그러면서도 "저자들은 **상대적으로 큰 대역을 쓸 수 있어서** 다운링크 데이터 전송 기반 패시브 레이더에 집중한다" — 즉 **SSB 를 알면서도 대역이 좁아 버렸다**. §4.3 RMS 유효대역: 실측 5G 에서 "effective bandwidth can even **decrease** with an increase in link occupancy" | `/data/public/jeong/papers/5G/22_Rényi…pdf` |
| Maksymiuk 외, "UAV Intrusion Detection with Passive Radar Based on the 5G Network", Asilomar 2025, pp.1639-1642 (DOI 10.1109/IEEECONF67917.2025.11443758) | [P] | eq.(5) **ΔR_b = c/B** 명시. FR2 400 MHz → 75 cm 교차검산(계수 2 없음 확정). 점유율 **F = "the percentage of the resource grid occupancy"** 를 Cassini 검지거리식의 정식 항으로 | `/data/public/jeong/papers/5G/25_UAV Intrusion…pdf` |
| "LTE-based multistatic passive radar system for UAV detection", IET RSN 2020 | [P] | **BW_eff = 18.05 MHz → c/(2·BW_eff) = 8.33 m**. CRS 를 쓰면 **최대 무모호거리 1.67 km**, CRS 가 sparse 하게 스케줄돼 **CRS AF 첨두가 전체 다운링크 대비 12.56 dB 낮음** | `/data/public/jeong/papers/LTE/20_LTE-based multistatic…pdf` |
| Demissie 외 (Fraunhofer FKIE), LTE450 Range Measurements, IEEE RadarConf 2024 | [P] | LTE450(461.0–467.5 MHz). "The reference elements are **always** present in the downlink signal". 기준요소는 **전체 전력의 약 1/4**. 기준요소만 쓰는 처리 vs 완전 다운링크 처리를 실측으로 나란히 | `/data/public/jeong/papers/LTE/24_Protection…pdf` |
| "Experimental UAV detection using 4G-LTE-based passive Radar" | [P] | **CRS 포함 심볼만 쓰면 검출능이 "significantly improved"** — 대부분 심볼이 비어 있고 CRS 심볼은 항상 파일럿을 담기 때문 | `/data/public/jeong/papers/LTE/23_Experimental UAV…pdf` |
| Jopanya & Osorio, SPAWC 2025 (DOI 10.1109/SPAWC66079.2025.11143316) | [P] | SSB = "the only periodic block of symbols that is **well-defined as a fixed-size block** in the time-frequency grid". N=240 subcarrier(20 RB), L=4 sym, f_Δ=**60 kHz**, f_c=**15 GHz** | `/data/public/jeong/papers/5G/25_Utilizing 5G NR SSB…pdf` |

### 우리가 가져올 규약

- **adopt** — SSB **always-on** 의 1차 근거를 **Rényi(Remote Sens. 2022)** 로 한다. Jopanya 보다 3년 빠르고
  저널급이며, Figure 7 이 우리 G1 유휴 자원격자 그림 그 자체다. Jopanya 는 **"240-부반송파 × 4-심볼
  고정 블록" 구조**와 "유일한 주기 블록" 프레이밍만 인용하고 **뉴머롤로지는 가져오지 않는다**
  (f_Δ=60 kHz 는 3GPP SSB 패턴 Case A–E 에 없다 — *미확인: 이번에 TS 38.211 원문을 열지 않았다*.
  f_c=15 GHz 도 우리 3.5 GHz 와 4배 이상 벌어진다).
- **adopt** — 점유율 **F 를 1급 변수**로. 5G_25 eq.(9)에서 F 는 B 를 그대로 둔 채 곱해지는 SNR 인자다 —
  즉 **그들의 모델도 "점유율은 분해능이 아니라 SNR 을 바꾼다"** 는 우리 §2.5 와 같은 물리다.
- **adopt** — Rényi §4.3 의 **RMS 유효대역** 정의와 "점유↑ 시 유효대역이 오히려 ↓할 수 있다" 는 실측 관찰.
  이것이 우리 §2.5 의 **실측 선행**이다. ⚠ 동시에 우리에 대한 위협이다 — 우리
  `_ref_bw = (cols.max()−cols.min()+1)*scs`(`waveforms.py:233-239`)는 콤 파일럿을 "점유 스팬" 으로 세는데
  문헌의 유효대역 정의는 다른 값을 준다.
- **partial** — ΔR_b = c/B. **"문헌 규약" 이 아니라 "좌표계 선택"** 으로 써야 한다(아래 표).
- **reject** — Wypich & Zielinski(Sensors 2026)를 드론 조명원 선례표에 넣는 것. [W] 등급(PDF 없음)이고
  우리 자체 노트(`pilot_findings.md` L174-177)에 따르면 **표적이 차량**(5.8 GHz, 33.33 MHz)이다.
  게다가 읽을 수 있는 PDF 안에 **반대 부호의 실측**(LTE_23: CRS-only 가 더 낫다)이 있다.

### 수치 비교표

| 항목 | 우리값(정의) | 선행값(정의) | 사과-대-사과 | 정직한 해석 |
|---|---|---|---|---|
| LTE CRS 거리분해능 (규약 ×2 검증) | **16.669 m** @ ref_bw **17.985 MHz** (= c/B, 거리합 좌표) (`report2_waveform_rcs.json reference.G1.lte`) | LTE_20: **8.33 m** @ BW_eff **18.05 MHz** (= c/2B, 공간 좌표) | **true**(같은 표준·거의 같은 유효대역·패시브·UAV 표적) | 차이가 정확히 **×2 = 좌표계뿐**이다. 우리 `docs/waveform_research.json` L192 도 "occupied 18MHz = 8.33 m" 를 이미 기록한다 → 내부 정합성까지 확인. **이것이 report04 의 유일한 진짜 사과-대-사과다** |
| 거리분해능 좌표계 | ΔR_b = c/B (거리합 R_b=R1+R2−L) | c/B: 5G_23·5G_25·WiFi_21 / **c/2B: LTE_19·LTE_20** / **c/(2B·cos(β/2)): LTE_25 eq.(76)** | **false**(문헌이 갈림) | "우리 규약이 문헌과 일치 → 반박 원천 차단" 은 거짓이다. c/B 진영은 **전원 바르샤바 공대 한 학파**(Maksymiuk·Abratkiewicz·Samczyński·Płotka / Rzewuski·Kulpa·Malanowski·Salski)이고 그중 둘은 같은 실험이다. 정직한 서술: **"두 좌표계가 공존한다. 우리는 RD 맵 거리축이 R_b 이므로 c/B 를 쓴다"** |
| 자원격자 점유율 | G1 1.447% / G2 17.749% / G3 79.754% (5G, `reference.*.nr.occ_pct`) | 5G_25: F = 60% (단일 가정치, Table I) | **false**(그들 60%는 예측용 가정치, 우리는 합성 프레임 RE 충전율) | 축의 개념은 정확히 같다 — **점유율이 이미 문헌 규약**이라는 것이 우리 9모드 서사의 강한 지지다. 값의 해상도만 다르다(단일값 vs 60배 스팬) |

### 대응 선행 없음

- **통제된 head-to-head WiFi vs LTE vs 5G 조명원 비교**(같은 표적·같은 챔버). 코퍼스 21편이 전부
  조명원 하나씩만 고른다(WiFi_21 은 WiFi vs DVB-T, 5G_22 는 SSB vs 데이터). **이 주장은 살아남는다.**
- ⚠ 그러나 **"'구세대 LTE CRS > 5G SSB' 헤드라인에 직접 대응 선례 없음" 은 과장이다.**
  Rényi(5G_22)가 SSB 를 알면서 "대역이 좁아서" 데이터로 갔다고 적는다 — 같은 방향의 인용 가능한 선례다.
- **v_max = PRF·λ/4 규약**에 대응하는 선행 정의 미발견. Jopanya 의 v_u = λ·f_Δ/2 는 정의 축이 다르다.
  ⚠ 이것은 우리 **내부 좌표계 불일치**를 드러낸다: `waveforms.py` 의
  `range_resolution_m = C0/ref_bw_hz`(거리합 좌표)와 `v_unambiguous_ms = pilot_rate_hz*lam/4`
  (모노스태틱 등가)가 같은 표에서 서로 다른 좌표계에 산다. 거리합 좌표에서 f_d = Ṙ_b/λ 이므로
  v_max = PRF·λ/2 여야 하고, 5G_25 식 (1)의 CAF 커널 exp(−j2πV_b t/λ)·식 (6) ΔV_b = λ/T_int 가
  λ(λ/2 아님) 스케일링을 확인해 준다.

---

## 5. 리포트 05 — 파형 검증(Sionna PHY 대조)

### 선행은 이렇게 했다

| 선행 | 등급 | 무엇을 했나 | 경로 |
|---|---|---|---|
| Wu, Lee, Lee (NYCU) arXiv:2606.07328 | [P] | TR 38.901 ISAC 채널모델을 독립 구현하고 3GPP 각사 레퍼런스 CDF 와 대조. 동기: "different implementations may easily lead to highly inconsistent simulation outcomes, **despite all claiming compliance with the same 3GPP specification**" | `papers_isac_sionna/2606.07328__*.pdf` |
| Di Seglio, Filippini, Bongioanni, Colone, IET RSN 18(1):108-124 (2024), DOI 10.1049/rsn2.12506 | [P] | 패시브 WiFi 레이더에서 **"a synthetic PHY Preamble, built as specified by the employed IEEE 802.11 standard"** 를 레퍼런스로 재구성 | `/data/public/jeong/papers/Wifi/24_Comparing…pdf` |
| He, Kearney, Fardad (Syracuse + Hidden Level) arXiv:2512.24889 | [P] | 레퍼런스 파형을 **3GPP TS 36.101 R.13 RMC** 프로파일로 MATLAB 합성(10 MHz OFDM) | `papers_isac_sionna/2512.24889__*.pdf` |
| Ai 외, PIERS 2021 (NUDT) | [P] | **MATLAB 5G Toolbox** 로 한 프레임 다운링크 생성 | `/data/public/jeong/papers/5G/21_Passive Detection…pdf` |

### 우리가 가져올 규약

- **adopt** — Wu 의 절차 규약: 구현한 규격표를 명시하고, 독립 레퍼런스와의 일치를 정량 보고하고,
  구현선택(CP 배열·중앙기준 격자·전력정규화)을 문서화한다. ⚠ **"우리가 Wu 보다 훨씬 엄격" 은 삭제.**
  레퍼런스 독립성에서는 Wu 가 위다 — 그들은 외부 기관이 독립 생산한 곡선과 맞추고, 우리는
  우리 격자·우리 CP 배열을 채점자에게 손수 건넨 뒤 일치한다고 한다.
- **adopt(관행 인용만)** — Di Seglio 의 "합성 레퍼런스는 규격에서 재구성한다". ⚠ **5 dB 수치는 인용 금지** —
  원문 §3.1 은 그 손실이 "due to the corresponding reduction in the **coherent integration gain**"
  (프리앰블-한정 처리의 적분길이 손실, Fig.4 는 10–11 dB)이라 하고, Fig.7 의 ≈5 dB 는
  Strategy #1 풀패킷 vs Strategy #1 프리앰블-한정 비교라 **합성 레퍼런스가 개입조차 안 한다**.
- **adopt(관행 인용만)** — Ai / He 의 "신뢰 도구로 표준 프로파일 합성".
- **reject** — Sionna 창설논문(2203.11854)을 **검증 범위의 근거**로 쓰는 것. 인용문 자체는 결백하지만
  (`"many carefully tested standard processing blocks…"` 축자 확인) 그것이 우리 스코프를 정당화하지 못한다.
- **reject** — Ai 의 "CP → T_u 위치 부차봉우리" 를 §5 물리 선례로. `make_notebook05.py` 408줄 전체에
  자기상관/모호함수/부차봉우리가 **0 hit** 이다. §5 는 CP 배열 대신 스칼라를 넘긴 **재합성 오류 민감도**다.
- **reject** — OpenISAC EVM 병치. EVM 은 수신단 등화 후 성상도 지표이고 우리 값은 송신단 시간영역 NMSE 다.

### 수치 비교표

| 항목 | 우리값(정의) | 선행값(정의) | 사과-대-사과 | 정직한 해석 |
|---|---|---|---|---|
| 첫-심볼 긴 CP 길이 (독립 확인) | LTE `cp_head = [160,144,144,144]`, NR `[352,288,288,288]` (`report2_waveform_rcs.json crosscheck`) | Sionna `CarrierConfig.cyclic_prefix_length`: 15 kHz → **5.208333 µs**, 30 kHz → **2.864583 µs** | **true** | 5.208333 µs × 30.72 MHz = **160**, 2.864583 µs × 122.88 MHz = **352** — Sionna 가 우리 첫-심볼 긴 CP 를 **실제로 독립 확인해 준다**. ⚠ 현재 JSON 은 이 근거를 싣지 못한다: `waveforms_sionna.py:61-62` 의 `int(np.asarray(cc.cyclic_prefix_length)…[0])` 가 **초 단위 스칼라를 int() 로 절단**해 `cp_length_samples: 0` 을 기록한다(필드명도 단위 오표기) |

### 대응 선행 없음

- **같은 기회신호 파형의 두 독립 구현을 전샘플 복소 NMSE 로 대조**. 코퍼스 48편 + top-venue 42편
  어디에도 없다. 선행은 전부 (a) 벤더 툴박스 출력을 교차검증 없이 신뢰하거나 (b) 통계 CDF 로
  채널모델을 캘리브레이션한다. report05 방법은 **관행의 더 엄격한 변형**이며 직접 대응 선행이 없다.

### ⚠ 이 절이 드러낸 우리 쪽 문제 — 검증 범위가 리포트 서술보다 훨씬 좁다

`viz_report2.py:358` 은 `ofdm_from_grid(wf.grid, wf.fft, cps)` 로 **우리 격자와 우리 CP 배열을
채점자에게 그대로 건넨다.** Sionna `OFDMModulator` 의 입력 규약은
`[..., num_ofdm_symbols, fft_size] Resource grid in the frequency domain` 이고 동작은
ifftshift + IFFT + CP 복사뿐이다 — **가드도 DC널도 구성하지 않는다.**

따라서 NMSE −135 dB 가 독립적으로 보증하는 것은 **IFFT 규약(fftshift 방향·정규화) + CP 복사·
심볼별 이어붙이기 순서**뿐이다. "IFFT·가드·DC널·심볼별 CP 삽입" 은 과대주장이다.
"뉴머롤로지를 CarrierConfig 에서 읽음" 도 절반만 참이다 — `waveforms_sionna.py:51` 의
`mu = {15:0, 30:1, 60:2, 120:3}[…]` 는 로컬 하드코딩이고, CarrierConfig 에서 실제로 오는 것은
`num_symbols_per_slot`·`num_slots_per_frame`·`frame_duration`·`cyclic_prefix` 넷뿐이다.

또한 `crosscheck` 은 `all_waveforms("G3")` 하나에서만 돈다 — "세 신호 모두" 라 쓸 때 격자 조건을 명시해야 한다.

**리포트에 넣을 정직한 문장(권장):**
> 우리 교차검증이 독립적으로 보증하는 것은 IFFT 규약과 CP 복사·이어붙이기 기계뿐이다. 격자
> (가드·DC널·파일럿 좌표)와 CP 길이 배열은 우리가 채점자에게 함께 건넨 것이므로 이 대조로
> 검증되지 않는다. 다만 `CarrierConfig.cyclic_prefix_length`(15 kHz→5.208 µs, 30 kHz→2.865 µs)를
> 샘플로 환산하면 160/352 로 우리 첫-심볼 긴 CP 와 일치하며, 이것이 CP 길이에 대한 별도의 독립 근거다.

---

## 6. 리포트 06 — RCS 와 Sionna 한계(산란적분 부재)

### 선행은 이렇게 했다

| 선행 | 등급 | 무엇을 했나 | 경로 |
|---|---|---|---|
| **NVIDIA 메인테이너 직답 — GitHub Discussion #844** | [P](우리 조사 기록) | 사용자가 "Sionna RT 로 금속체를 대량 광선 샘플링해 RCS 를 낼 수 있나" 묻자 **Jakob Hoydis 가 "This is currently not supported"** 라고 답 | `prior_work/sionna_sensing_survey.md:37` |
| Sionna RT 기술보고서 arXiv:2504.21719 (2.0.1 세대) | [W] | PathSolver = image method + SBR(**경로 열거용** 광선발사) + 정반사/확산/1차회절/굴절 계수. **표적 표면전류 PO 적분 없음** | `prior_work/sionna_sensing_survey.md:28-33` (2차 노트) |
| 자체 문헌 센서스 | [P] | genuine Sionna 27편 정독 → 16편 집계: A1=1·A2=2·C=3·D=5·NA=5, **스톡 솔버 안에서 코히어런트 PO/산란적분을 낸 논문 0편** | `/data/public/sionna_jeong/papers_isac_sionna/deep_read_notes.md:26-28` |
| Ziganshin arXiv:2604.05991 | [P] | Sionna-RT **v0.19 를 in-place 확장**(UTD + vertex + double-bounce 회절) | `papers_isac_sionna/2604.05991__*.pdf` |
| Sagitta SBR arXiv:2604.09243 | [P] | 독립 GPU BVH SBR + Stratton–Chu PO. **Sionna 미사용** | `papers_isac_sionna/2604.09243__*.pdf` |

### 우리가 가져올 규약

- **adopt** — 증거 위계를 이렇게 세운다:
  **① Discussion #844(메인테이너 직답) → ② 2504.21719 / 2.0.1 문서 → ③ 2303.11103(설계 계보) → ④ 우리 [A]~[E]**
  기존 서술은 ②③ 만 쓰고 ① 을 통째로 놓쳤다. 그리고 2303.11103 은 **2023년 v0.14 시절 RT** 문서인데
  우리는 Sionna 2.0.1 을 돌린다(PathSolver 는 1.0 에서 재구현) — 버전 정합 근거는 ② 뿐이다.
- **adopt** — 문헌 센서스(16편 중 0편)를 §3 헤드라인 숫자로. 단 **"스톡 Sionna 로" 를 반드시 붙인다** —
  FEKO·openEMS·무향실 측정으로는 다들 낸다.
- **reject** — 2603.28736(EuCAP 2026)을 "우리 핵심주장의 peer-reviewed 지지" 로 쓰는 것. 원문:
  *"Purely specular RT on low-polygon meshes underestimates power **at mmWave/sub-THz** due to
  **electromagnetic roughness**; direct meshing at O(λ/10) is infeasible **at E-band** [12]."*
  밴드 한정 2개가 제거된 채 인용되고 있었다. **3.5 GHz 에서 λ/10 = 8.6 mm 는 전혀 불가능하지 않다**
  (우리 드론 메쉬 28,548 faces) — 우리 밴드에서 논증이 **뒤집힌다**. 게다가 원인도 다르다
  (그들=표면 거칠기, 우리=PO 적분 부재). route (b) 확산-S 대표 선행으로서의 인용만 유효.
- **reject** — pw04 등급 문자와 `deep_read_notes` 센서스 등급 문자를 **겹쳐 쓰는 것**. 두 루브릭의
  정의가 다르다(pw04: B=외생 analytical/point-scatterer, D=RCS 언급만 / deep_read: B=측정, D=점산란,
  NA 존재). 실제 충돌: TGNN 2604.08306 이 pw04 에선 B, deep_read 에선 D. Great-X 2507.08716 이
  pw04 에선 C, deep_read 에선 A2. 센서스 산출 루브릭(deep_read)으로 §3 표를 단일 재라벨할 것.
- **partial** — Sagitta 를 route (d) 선행으로. **"완전동일" 은 거짓**이다(§7 참조).

### 수치 비교표

| 항목 | 우리값(정의) | 선행값(정의) | 사과-대-사과 | 정직한 해석 |
|---|---|---|---|---|
| 스톡 Sionna 로 소형표적 코히어런트 RCS 를 낸 편수 | **0편** — 우리도 못 내서 자작 SBR+PO(route d)로 계산해 (c)로 주입 | genuine Sionna **16편 중 0편** (A1=1·A2=2·C=3·D=5·NA=5) | **true**(문헌 count 로서) | σ 숫자 대조가 아니라 **주장 census** 로서 사과-대-사과. 우리 route (d)→(c) 선택이 억지가 아니라 문헌 전체가 우회한다는 사실의 귀결. ⚠ 27편 표본은 웹 예산 소진으로 전수 아님 |
| PEC 구 반환 경로수 | r=0.3·1.0 m 에 광선 **4억 발**까지 쏴도 경로 **0개**(8행 전부). 대조 평판(변 0.6 m)은 100만 발에 1경로 −7.913 dB (`report3_rt.json E_sphere`) | (대응 없음 — 선행은 곡면표적을 스톡으로 시도하지 않고 UTD/PO 로 우회) | **false**(우리 고유 진단) | 스톡 산란적분 부재의 가장 날카로운 시연. 창설논문의 image-method 문서화(곡면엔 image point 없음)와 정성 부합. **"선행 없음(우리 고유)"** 로 정직히 표기 |

### 대응 선행 없음

- 우리 [A] 코히어런트합 비수렴(+14.9 dB @report3_rt / +16.5 dB @rt_ray_budget), [D] 평판 −7.913 dB 불변,
  [E] PEC 구 0경로 — 세 진단수치에 대응하는 "선행이 보고한 같은 수치" 가 없다. 선행은 도구한계를
  정성/문서로만 진술한다.

### ⚠ 이 절이 드러낸 우리 쪽 문제

1. **두 원장이 같은 조건에서 다른 값을 준다.** [A] 25M spp 코히어런트: `report3_rt.json` −68.287(3 seeds)
   vs `rt_ray_budget.json` −70.128(5 seeds) → 헤드라인 비수렴 폭이 +14.9 ↔ +16.5 dB 로 갈린다.
   [B] S=0.1 코히어런트: −74.844 vs −68.601 → **6.2 dB 불일치**. 확산-S 민감도를 인용할 때
   **한 원장(rt_ray_budget, 5 seeds)만 써야** 한다.
2. **코히어런트 span 과 인코히런트 slope 를 한 문장에 붙이면 안 된다.** `B_S_sweep` 직접 검산:
   인코히런트 −74.318→−55.904 over log10(8) = **20.4 dB/dec**(= `B_fit` 값), 코히어런트
   −68.601→−30.873 = **약 41.8 dB/dec**. `make_notebook06.py:438` 자신이 "인코히런트 합 로그기울기 …
   (코히런트 합은 더 가파르다)" 라 적는다. `S_to_match_truth = 0.704` 도 인코히런트 곡선 보간값이다.
3. **metal_share 퍼센트가 두 값으로 공존한다.** `report2_waveform_rcs.json materials` 에서
   full −18.4122 / metal core −18.0193 → 선형비 **109.5%**(물리적으로 불가). 코드셀은
   `report3_rt.json C_metal.metal_share_pct = 88.74%`(n_az=36)를 출력한다. 별도로
   "금속코어가 통드론보다 **0.39 dB 밝다**"(`delta_db = +0.3929`)는 그 자체로 가림/투과 모델의 부호
   문제이며 퍼센트 통일만으로는 해소되지 않는다.
4. **우리가 A1 인가 A2 인가가 우리 기록끼리 충돌한다.** `deep_read_notes.md:86` 은 A1(외부 SBR+PO),
   같은 파일 `:270` 은 "우리도 A2다 — Sionna RT 의 Mitsuba 엔진을 재사용",
   `sionna_sensing_survey.md:35` 는 "`PathSolver` 는 subclass 확장점이 아니다(MRO 실측) → Mitsuba
   광선엔진 위에 직접 짠다". **글자를 확정하거나 버리고 메커니즘으로 서술할 것**
   ("그들 = UTD 회절 in-place, 우리 = PO 표면적분 on Mitsuba").

---

## 7. 리포트 07 — SBR+PO 엔진(해석해 대조 검증)

### 선행은 이렇게 했다

| 선행 | 등급 | 무엇을 했나 | 경로 |
|---|---|---|---|
| Pasquale, Hu, Pennati, Peng, Markidis (KTH), SagittaSBR arXiv:2604.09243 | [P] | GO 다중반사 + **Stratton–Chu PO over ray tubes** + BVH. PEC 구를 **Mie 해석해**와 kr = 2πr/λ **10⁰–10⁴ 스윕**, σ/(πr²) 정규화. 광학영역 std **~2.5%**, 유효구간 **kr=30(Mie→광학 경계) ~ kr=8000(aliasing 개시)**. 광선샘플링 **Δs ≤ λ/5**. **모노스태틱 전용**을 명시하고 각주 1 에서 바이스태틱은 "a visibility function to account for shadow regions between the reflection points and the final receiver" 가 추가로 필요하다고 경고 | `papers_isac_sionna/2604.09243__*.pdf` |
| Ziganshin 외 arXiv:2604.05991 | [P] | 정준 구+원통을 해석해 + FEKO-MLFMM 과 먼저 대조 후 i-MiEV 를 BiRa 실측(설비 2–18 GHz, **실제 대조 3 GHz**)과. **Fig.5 는 후방산란 MAE 를 E²/(Rλ) 함수로 직접 그린다** — 후방산란 정확도는 **E²/(Rλ) ≈ 0.5** 를 지나면 개선 미미, 실용 절충대 0.6–0.9 | `papers_isac_sionna/2604.05991__*.pdf` |

### 우리가 가져올 규약

- **adopt** — Sagitta 의 **kr 스윕 검증**(σ/(πr²) 정규화 + Mie 대조 + 유효경계 명시). 우리 검증절의
  가장 큰 구조적 결손(단일 kr)을 정확히 메운다. 부수 효과가 크다 — 우리 검증 구는 r=0.5 m, 3.5 GHz 에서
  **kr = 36.7 로 Sagitta 유효 하한 kr=30 의 1.22배**, 즉 방법이 valid 하다고 공표된 구간의 **가장 시끄러운
  가장자리**에서만 검증했다는 사실이 드러난다.
- **adopt(단서 필수)** — Δs ≤ λ/5 를 공표된 하한으로 인용. 우리 `rcs_sbr.py:68 DEFAULT_DIV = 12`(λ/12),
  드론 측정은 λ/16. ⚠ **"3.2× 여유" 는 과장이다** — Sagitta 자신의 스윕 설정(22,000×22,000 광선 /
  2.05 m 개구 → Δs = 93.2 µm)으로 계산하면 그들이 **관측한** aliasing 개시는 kr=8000(r=1 m, λ=785 µm)
  ↔ 8.4 samples/λ, ±2% 유지 상한 300 GHz ↔ 10.7 samples/λ 다. λ/5 는 검증된 임계가 아니라 경험칙이고
  실측 붕괴점 대비 우리 여유는 **약 1.9배**다. *(이 산술은 논문 명시값이 아니라 본문 설정값에서 유도한 것)*
- **adopt** — Ziganshin 의 **정준먼저-검증 프로토콜**(실제 표적 전에 구·원통을 해석해/풀웨이브로 먼저).
- **partial** — Sagitta 식 (5)(6) Stratton–Chu PO(J_s = 2n̂×H 조사영역 / 0 그림자영역)를 §5 가림의 근거로.
  ⚠ **반드시 "모노스태틱 한정" 스코프를 붙일 것.** 우리 프로젝트는 패시브 **바이스태틱**이고,
  우리 `rcs_sbr.py:252-259` 독스트링이 같은 고장을 이미 자백한다 — 전방산란 무효(β→180° 에서 σ≡0),
  비볼록 표적 상반성 rms 5–9 dB(최대 18 dB) 붕괴. 무스코프 인용은 빌려온 권위가 report12 가 의존하는
  바이스태틱 케이스까지 조용히 덮는다.
- **reject** — Ziganshin 의 **각도응답 dB MAE(40λ, 0.5°, 720점)**. 우리 정준 검증은 각도응답이 아니라
  **단일 입사방향 한 점**(`viz_report2.py:588` `az_deg=0.0, el_deg=0.0`)이라 계산할 대상이 없다.
- **reject** — 곡률적응 facet 규칙을 **드론에** 적용. 우리 PO 합의 구적점은 facet 이 아니라 광선 히트라
  facet 밀도가 정의상 값에 못 들어간다(`mesh_verify` 실측: 4배 세분 → Δσ 2.9e-7 dB).
  **검증 구에 한해서만** 살아난다(아래 표).

### 수치 비교표

| 항목 | 우리값(정의) | 선행값(정의) | 사과-대-사과 | 정직한 해석 |
|---|---|---|---|---|
| 광선격자 밀도 규칙 | 드론 측정 **λ/16**, 커널 기본 λ/12, 검증 스윕 λ/4–λ/30 (`rcs_sbr.py:147 d = lam/DEFAULT_DIV`, `:496 rays_per_lambda = lam/d`) | Sagitta: **Δs ≤ λ/5** ("at least five samples per wavelength are required to accurately capture the rapidly oscillating phase") | **true**(둘 다 직교 개구면 incident-ray-grid 간격) | 정의 축이 동일한 진짜 규약 대조. 우리가 공표 하한보다 3.2×, **관측된 붕괴점(8~11 samples/λ) 대비 약 1.9× 촘촘**. 결과가 아니라 방법 신뢰성 근거로만 |
| 정준 구 facet 이산화 적정성 | `uv_sphere(r=0.5, seg=180, rings=90)`, λ=85.65 mm → E = 2πr/180 = 17.45 mm(=λ/4.91) → **E²/(Rλ) = 0.0071** | Ziganshin: 후방산란 수렴 무릎 **0.5**, 실용대 0.6–0.9, i-MiEV 0.4–0.6 | **true**(무차원 지표 그대로 계산됨) | 무릎 대비 **약 70배 촘촘**. 결론: **우리 구의 잔차를 facet 이산화 탓으로 돌릴 수 없다 — 남은 용의자는 광선격자뿐이다.** ⚠ Ziganshin 의 E²/(Rλ) 는 UTD-facet 기반이라 PO-over-ray-tubes 로의 이전이 검증된 등가는 아님 |

### 대응 선행 없음

- **가림 대가(occlusion dB)**. 우리 `report2_waveform_rcs.json occlusion.occlusion_db = −4.3475`.
  Sagitta·Ziganshin 모두 그림자 facet 을 zeroing 하는 물리는 공유하지만 "가림이 σ 를 몇 dB 낮추나" 를
  보고하지 않는다. *(2026-07-23 확인: `report6_sbr.json` 의 `compare` 블록이 비어 있어, 과거 지적된
  −4.35 vs −2.71 dB 내부 불일치는 현재 파일에서 재현되지 않는다 — 단일 값 −4.3475 만 남아 있다)*

### ⚠ 이 절이 드러낸 우리 쪽 문제 — 평판 검증은 전자기 정보가 0 이다

`rcs_sbr(plate, …, el_deg=90.0)` = z=const 평면에 **수직입사**. 그러면 모든 히트에서
e^{j2k(p−ctr)·û} 가 **상수**다. 따라서 E = g·N·d², σ = (4π/λ²)(N d²)², 기준 = 4πA²/λ² →
비 = (N d²/A)² 이고 **λ 가 항등적으로 소거된다.** 즉 `plate_err` 은 "광선격자가 0.4×0.4 m
정사각형을 얼마나 잘 타일링하나" 만 잰다 — 위상 없음, 파장 의존 없음, **어떤 주파수에서도 실패 불가**.

증거(우연 아님) — `sbr_validation.plate_err` 를 직접 읽으면 값이 **비트 단위로 반복**된다:

| div | 4 | 6 | 8 | 10 | 12 | 16 | 20 | 24 | 30 |
|---|---|---|---|---|---|---|---|---|---|
| plate_err [dB] | +0.29374 | **−0.0137361380132141** | **−0.1695378933541799** | −0.26369 | **−0.0137361380132126** | **−0.1695378933541799** | +0.10991 | +0.14068 | **−0.0137361380132141** |

div ∈ {6, 12, 30} 이 동일, div ∈ {8, 16} 이 동일 — 순수 정수 정합성(commensurability) 지문이다.
우리 소스도 자백한다(`rcs_sbr.py:66-67`: "평판 정면(el=90°)은 위상항이 상수라 이 진동을 진단 못 한다").

→ **§4 헤드라인에서 평판을 "엔진 검증" 이 아니라 "면적 구적(quadrature) 확인" 으로 강등해야 한다.**
비스듬한 입사(el≠90°)로 다시 재면 sinc 로브가 살아나 4πA²/λ² 가 비자명한 검증이 된다.

또한 §4 산문이 아티팩트보다 낡았다: `make_notebook07.py:371-376` 은 "개별각 최대 ~6 dB, p95 ~3.9 dB,
25,676→102,704면" 이라 적지만 `mesh_verify.json` 실제값은 **max 2.00 / p95 1.399 dB, 28,548→114,192면** 이다.

그리고 `report6_sbr.json kernel` 과 `report2_waveform_rcs.json sbr_validation` 은 **독립 재현이 아니다** —
`viz_report2.py:588` 과 `viz_verify_sbr.py:107-108` 이 같은 함수를 같은 인자로 부른다.
비트 일치는 "결정론적 동일 코드경로를 두 번 호출" 의 증거이지 독립 검증이 아니다.

---

## 8. 리포트 08 — 드론 RCS 결과 + 마이크로도플러

### 선행은 이렇게 했다

| 선행 | 등급 | 무엇을 했나 | 경로 |
|---|---|---|---|
| Li & Ling, IEEE AWPL 2017 | **[N]** | VNA 턴테이블 + 구 교정 S11, **3–6 GHz**. **aspect-peak**: Phantom 2(35 cm) −27.5 / 3DR Solo(46 cm) −24.2 / Inspire 1(56 cm) −13.7 dBsm. 자세 스프레드 ~14 dB. 3–6 GHz 는 12–15 GHz 보다 ~12 dB 낮음 | `refs/drone_papers/Li_Ling_2017_*.md` (**PDF 전 디스크 부재**) |
| Zhang 외 arXiv:2505.20673 | [P] | DJI **M350**(원문 "approximate dimensions of **430 × 420 × 430 mm**") 무향실 모노스태틱 10/15/20/28/36 GHz, **el = 90°(수평면)**. σ = A(f)·B1(f,φ)·B2 3층 분해. Table V: 로브 중심 0/90/180/270°, 3dB 폭 20.84/10.47/15.41/14.51°. 잔차 B2 ~ log-normal **N(−0.52, 2.31²) dB**, KL 로 Weibull/Gamma 대비. 교정구 이론 −7.07 vs 측정 −8.96 dBsm | `papers_isac_sionna/2505.20673__*.pdf` |
| Semkin 외, IEEE Access 8:48958 (2020) | [N] | 무향실 quasi-monostatic 26–40 GHz, 로터 정지, **mean HH**. Mavic Pro(335 mm 플라스틱) −16.8~−15.0 / P4Pro −16.4~−12.3 / **M100(650 mm 카본) −10.5~−6.6** dBsm, std ~6 dB | `refs/drone_papers/Semkin_2020_*.md` |
| Beuster 외 arXiv:2402.16591 | [P] | 정지/회전 프로펠러 분리 보고, 바이스태틱각 스윕, **공개 데이터셋** github.com/EMS-TU-Ilmenau/bira-dataset. **논문 자체에는 dBsm 절대값 없음** | `papers_isac_sionna/2402.16591__*.pdf` |
| OpenISAC arXiv:2601.03535 | [P] | 마이크로도플러 판독 규약: "The **zero-Doppler** return represents quasi-static scattering from the UAV body. **Symmetric, equidistant ridges** correspond to the rotating rotor blades. The **spacing between these ridges reflects the rotor angular velocity**, while the overall **Doppler spread** indicates the maximum radial velocity of the blade tips." | `papers_isac_sionna/2601.03535__*.pdf` |

### 우리가 가져올 규약

- **adopt** — OpenISAC 의 마이크로도플러 판독 3규약 + `|STFT|²` 축. ⚠ **두 곳에서 깨진다**:
  (i) OpenISAC 의 ridge 간격은 **로터 각속도(rpm/60)** 인데 우리 `flash_hz = blades × rpm/60` 은
  **정확히 2배**다 — 그 문장 옆에 우리 flash 를 두면 블레이드 수만큼 어긋난 두 양을 병치하게 된다.
  (ii) OpenISAC 은 STFT **앞에 MTI(0-Doppler 노치)** 를 걸므로 그들의 "zero-Doppler = 동체" 는
  MTI 잔차다. 우리 pedestal·`gain_db` 는 MTI 없는 신호에서 잰다.
- **adopt** — Beuster 의 정지/회전 분리 + 바이스태틱각 축. ⚠ 실제 정량 대조를 하려면
  `rcs_sbr_multistatic()` 출력 JSON + BiRa 데이터셋 확보 **둘 다** 필요하다(논문에 dBsm 이 없다).
- **adopt** — Zhang 의 **σ = A·B1·B2 3층 분해**를 그대로. 우리 방위 σ 를 A(dB평균)·B1(로브)·B2
  (log-normal 잔차)로 분해하고 **우리 잔차 표준편차를 Zhang 의 2.31 dB 와 나란히** 두면
  "잔차 산포" 라는 공유 축이 실제로 존재하는 정량 비교가 된다.
- **partial** — Semkin 은 **규약만**(재질·로터상태·편파 명기). **+7 dB 수치는 인용 금지** —
  M100 650 mm 카본 vs Mavic Pro 335 mm 플라스틱이라 광학영역 면적 스케일링만으로
  10log10((650/335)²) = **+5.7 dB**, "카본 이득" 의 거의 전부가 크기 효과다.
- **reject** — Zhang 의 **교정구 <2 dBsm 을 우리 시뮬 목표치로** 삼는 것. 남의 **계측 눈금오차**를
  우리 정확도 목표로 삼는 역방향 논증이고 Sagitta 의 Mie ±2%(≈0.09 dB)보다 20배 느슨하다.
- **reject** — 밴드 기울기 인용(§14 참조).

### 수치 비교표

| 항목 | 우리값(정의) | 선행값(정의) | 사과-대-사과 | 정직한 해석 |
|---|---|---|---|---|
| **크기 짝 aspect-peak** @3–6 GHz | peak_dbsm, el=15°, 방위 361점 최대, 모노스태틱, 3.5 GHz: mini5pro(275 mm) **−15.96** / phantom4(350 mm) **−11.71** / matrice4e(438.8) **−16.13** / mavic4pro(441) **−13.06** / s1000plus(1045) **−5.69** | Li & Ling aspect-peak: Phantom 2(350 mm) −27.5 / 3DR Solo(460) −24.2 / Inspire 1(560) −13.7 | **true** (밴드·기하·지표 3축 정합, 크기로 짝) | 크기로 짝을 맞추면 **우리가 +8.0 ~ +15.8 dB 밝다**. 최정합 짝은 **phantom4(350 mm DJI 쿼드) ↔ Phantom 2(350 mm DJI 쿼드) = +15.79 dB**. ⚠ 편파 미분리(Li&Ling S11 = co-pol)·앙각 미상·peak 은 샘플밀도에 상향 편향(우리 1° vs 문헌 5°)·[N] 등급. **결론: 우리 σ 는 "범위 안" 이 아니라 "크기 짝 실측 대비 과밝음"** |
| **four-leaf 포락선** (n=4 조화) | 3.5 GHz dB 방위패턴의 4차 조화가 AC 에너지에서 차지하는 비중: **phantom4 58.9%**(최강 조화 n=4) / s1000plus 17.1%(최강 n=16) / matrice4e 5.5% / mavic4pro 4.6% / mini5pro 0.9%. phantom4 4섹터 평균 편차 **+6.44 / +6.33 / +6.38 / +6.33 dB**(스프레드 **0.11 dB**) | Zhang: 사각 동체 UAV 의 four-leaf 포락선(0/90/180/270°), Table V 로브 파라미터 | **false** (밴드 3.5 vs 10–36 GHz, 지표 정의 상이) | **양성 결과다.** 우리 Phantom 4 는 교과서적 four-leaf 를 재현한다. mini5pro·s1000plus 는 2-fold(90/270), mavic4pro·matrice4e 는 섹터 수준 거의 등방 — **물리적으로 기대되는 바**(Mavic 계열은 접이식 비대칭 동체, s1000plus 는 8암). ⚠ 로브 **개수**(prom>2 dB 로 20~29개)는 Zhang 의 포락선 모델이 아니라 잔차 리플을 세는 것이므로 **인용 금지** |

### 대응 선행 없음

- **마이크로도플러 flash / f_tip 정량 대조**. 우리 `report1.json microdoppler.drones`:
  flash 120.0 / 126.67 / 183.33 Hz, f_tip 989.8–1619.7 Hz, gain_db 10.36–39.33 dB.
  대응 선행 수치가 없다 — OpenISAC·Costa 는 판독 규약만 주고 flash 식을 안 준다.
  DTMB Mavic 3 노트는 서지가 `drone_lit.jsonl` 에 있으나(DSP Elsevier 2026-03, PII S1051200426002265)
  그 기록 자신이 **"no blade-flash frequency in Hz in the accessible (paywalled) abstract;
  no dBsm RCS reported"** 라고 적는다. **정량 비교 불가**.
- **바이스태틱 σ**. 우리 `rcs.drones` 는 전부 모노스태틱(등가)이다. 따라서 **report08 의 절대값 앵커는
  report12(패시브 바이스태틱 검출)로 상속되지 않는다** — 이 문장을 §6 에 명시해야 한다.
- **편파 축**. 우리 SBR 은 스칼라 Γ(`grep -ci polari` = 0). 문헌 내 편파 스프레드는 10 dB 급이다
  (LTE450 실측: "a horizontally polarized antenna yields roughly **10 dB** higher target power than a
  vertically polarized one"). 즉 스칼라 σ 를 co-pol 실측과 견주는 순간 **모든 절대 dB 대조가
  ±5~10 dB 진술로 강등된다.** 캡션 각주가 아니라 §6 판정문의 **불확도 예산**에 들어가야 한다.

### ⚠ 이 절이 드러낸 우리 쪽 문제

- §2 가 `_span = 8.22 dB` 를 출력하면서 본문에 "약 5 배" 로 하드코딩. 8.22 dB = **6.6 배**.
- §5 의 "flash rate 만으로도 기체가 갈립니다 / 지문 주파수가 곧 기체 식별자" 가 자기 표로 반증된다:
  5종이 내는 flash 는 **3개 값뿐**이고 두 쌍이 충돌한다(mavic4pro = s1000plus = 120.0 Hz,
  mini5pro = phantom4 = 183.33 Hz, matrice4e 만 126.67 Hz 단독).
- §4 가 "코(0°)·꼬리(180°)·측면(90°/270°)에서 봉우리" 를 5종 공통으로 서술하지만
  위 조화 분석상 phantom4 만 성립한다.
- §6 이 Mavic Pro 2.4 GHz 행(**소형 쿼드·sub-6**)을 "대형·고정익·고주파" 로 실격시키는데,
  `prior_work.json measured_rcs_anchor` 는 같은 행을 "봉우리가 범위 내" 로 읽는다 — 판정 충돌.
  덤으로 그 verdict 의 우리 값(−19.7 / −12.4)은 낡았다(현재 −18.365 / −13.056).

---

## 9. 리포트 09 — 바닥 유령 표적(표적경유 다중경로)

### 선행은 이렇게 했다

| 선행 | 등급 | 무엇을 했나 | 경로 |
|---|---|---|---|
| Martelli, Murgia, Colone, Bongioanni, Lombardo (Sapienza) | [P] | WiFi 패시브 레이더 3D 측위. **"the sliding version of the ECA (ECA-S) … With respect to the standard ECA … preserves the low-Doppler moving target"**. 표준 체인 = ECA-S → 거리-속도 맵 → CA-CFAR → **3-of-3** → Kalman | `/data/public/jeong/papers/Wifi/17_Detection_and_3D…pdf` |
| "Fusing Measurements from Wi-Fi Emission-Based and Passive Radar Sensors" | [P] | ECA-S 가 "direct signal breakthrough and multipaths … together with the echoes from stationary targets" 를 제거 | `/data/public/jeong/papers/Wifi/21_Fusing…pdf` |
| Maksymiuk 외, "5G Network-Based Passive Radar for Drone Detection", IRS 2023 Berlin | [P] | 실측 5G(3.44 GHz, 38.16 MHz, TDD). **"38.16 MHz … maximum bistatic range resolution of approximately 7.8 m"**. R_b = R1+R2−L. GPS 로그 오버레이 | `/data/public/jeong/papers/5G/23_5G Network-Based…pdf` |
| Colone, Palmarini, Martelli, Tilli, "Sliding extensive cancellation algorithm…", IEEE TAES 52(3):1309-1326, 2016 | [W] | ECA-S 원논문 (서지는 위 W17 참고문헌 L510-514 에서 확인, **원문 미개봉**) | — |

### 우리가 가져올 규약

- **partial(조건부)** — ECA → CAF → CFAR 표준 체인. ⚠ **인용문을 그대로 캡션에 박으면 역효과다.**
  그 문장이 칭찬하는 low-Doppler 보존은 **ECA-S(sliding) 고유**이고 전제는 "standard ECA 는 그렇지
  못하다" 인데, 우리 `passive_process.py:82-110 ECACanceller` 는 CPI 전체에 대한 1회 최소제곱 사영
  (지연 부분공간만, 배치·슬라이딩 없음) = **standard ECA** 다. 챔버 드론이 3 m/s·f_d 64 Hz 로
  정확히 low-Doppler 영역이라 더 위험하다. 인용하려면 (a) 우리가 standard ECA 임을 명시,
  (b) low-Doppler 보존은 우리 `verify_eca.json` 으로 별도 입증, (c) 다중프레임 판정 규약을 도입할 것.
- **adopt** — ΔR_b = c/B 규약의 근거로 5G_23. 단 그 논문은 "range-sum 좌표" 라 말한 적이 없다 —
  7.8 ≈ c/B 는 **우리의 역산 추정**이므로 "역산으로 일치 확인" 이라 써야 한다.
- **reject** — Neural ISAC gSUB / CellSense baseline 차분을 우리 유령절에 붙이는 것.
  둘 다 **정지** 클러터만 지운다 — 표적경유 도플러 유령에는 적용 불가.

### 수치 비교표

| 항목 | 우리값(정의) | 선행값(정의) | 사과-대-사과 | 정직한 해석 |
|---|---|---|---|---|
| 바이스태틱 거리분해능 규약 | 5G NR 98.28 MHz → **3.0504 m**; WiFi 75.625 MHz → 3.9642 m; LTE 18 MHz → 16.655 m (`floor_ghost_verify.json CD_ghost[*].d_rb_m`, 거리합 좌표) | 5G_23: 38.16 MHz → ~7.8 m | **true**(규약 검증) | c/38.16e6 = 7.86 m 로 검산 일치(c/2B 라면 3.93 m). 결과 비교가 아니라 **좌표계 정합 확인**. 리포트에 "거리합 좌표 기준" 한 줄 + c/(2B·cos(β/2)) 병기 |

### 대응 선행 없음 — **단, 주장을 보류해야 한다**

기존 서술은 "표적경유(도플러 실린) 지면반사 유령을 별개 오검출 표적으로 정량화한 선행 0건 = 우리 고유
기여" 였다. **이 주장은 현재 상태로 쓸 수 없다.** 검색어가 `ghost` 하나뿐이었고, 같은 코퍼스 안에
정확히 이 현상을 다룬 참고문헌 2건이 있다:

1. **Mazhar, H., Hassan, S. A., "Analysis of target multipaths in WiFi-based passive radars,"
   IET Radar Sonar Navig., 2016, 10(1), pp. 140–145** — 제목이 문자 그대로 "표적 멀티패스".
   (출처: `LTE/20_LTE-based multistatic…` 참고문헌 [2])
2. **O. Rabaste, D. Poullin, "Rejection of Doppler shifted multipaths in airborne passive radar,"
   IEEE Radar Conf. 2015, pp. 1660–1665** — "도플러가 실려 정지클러터 제거를 통과하는 멀티패스"
   가 논문 한 편의 주제다. (출처: `LTE/25_Drone_Detection_Using_4G-LTE…` 참고문헌 [37])

두 원문 PDF 는 우리 코퍼스에 **없다(미확인)** 이므로 "이들이 별개 오검출 표적으로 정량화했는지" 는
알 수 없다. → **원문 확보 전까지 독창성 주장 보류.**

### ⚠ 이 절이 드러낸 우리 쪽 문제 — 헤드라인 "100% 오검출" 의 근거가 단일 스냅샷이다

`floor_ghost_verify.json CD_ghost` 의 `p_false = 1.0` 은 기하 플래그가 아니라 **몬테카를로 검출률**이다
(`benchmark/run_min_cell.py:212 ghost["p_false"] = ghost_hits / N`, N=60 시행마다 잡음 재추출 후
ECA → range_doppler → CA-CFAR). 기하 플래그는 별도 키 `resolved`(`:153`)다.

문제는 **N=60, 궤적 중앙 단일 스냅샷**이라는 것이다. 궤적 전체를 재는 `verify_ghost_impact.json`
(궤적 3종 × CFAR 셀 9개 = 27 지점, 각 N=60)을 직접 읽으면:

| 파형 | ghost_p_false 평균 (27셀) | ghost_margin 평균 | resolved |
|---|---|---|---|
| **5G NR 100 MHz** | **0.483** (최대 1.00) | **−1.78 dB** | 22/27 |
| WiFi 80 MHz | 0.037 | +8.54 dB | 6/27 |
| LTE 20 MHz | 0.000 | +16.68 dB | 0/27 |

분리량이 궤적 위에서 sep_m 2.48–4.69 m 로 변한다. 정직한 헤드라인:
**"궤적 중앙 스냅샷에서 100%, 궤적 평균 ~48%, 유령의 CFAR 임계 여유는 평균적으로 임계 아래(−1.78 dB)."**

부수로, `B_clutter_dead` 의 SCR span 1.06e-9 dB 는 물리 발견이 아니라 **모델의 귀결**이다 —
`benchmark/geometry.py:23-37` 이 스스로 문서화하듯 주입 클러터는 도플러 없는 지연복제 = ECA 기저
그 자체라 진폭과 무관하게 정확히 0 으로 지워진다. "구현 정합성 검사" 로 강등해야 한다.

---

## 10. 리포트 10 — 검출기 교정 ①: 오경보율(Pfa)

### 선행은 이렇게 했다

| 선행 | 등급 | 무엇을 했나 | 경로 |
|---|---|---|---|
| Yan, Gao, Colone, Costa, Hao, Manara, Orlando arXiv:2601.10846 | [P] | Pd(고정 Pfa=1e-4)를 SINR 함수로. **"we compute the detection thresholds and the Pd values over 100/Pfa and 10⁴ independent trials"**. §VI.B **CFAR Property**: 명목 문턱을 고정하고 CNR(−15~30 dB)·ρ 를 스윕해 **실제 Pfa** 가 평평한지(Fig.9) | `papers_isac_sionna/2601.10846__*.pdf` |
| He, Kearney, Fardad arXiv:2512.24889 | [P] | **명목 Pfa 대 관측 Pfa 를 Table 1 에 병기**. **exclusion neighborhood(4 test × 6 delay cells)** 의 양성 CFAR 셀은 파형 유발 delay smearing 이라 FAR 집계에서 제외. 10,000 MC, guard 1 / train 12(delay)·6(Doppler) | `papers_isac_sionna/2512.24889__*.pdf` |
| 드론 코퍼스 (Wifi_17 / LTE_19 / LTE_23 / Wifi_24 / LTE_25) | [P] | 표준 동작점: Pfa 1e-6 / 5e-6, 문턱 13 dB, guard cell + detection clustering, M-of-N(3-of-3), 현장 FA rate 18.2% | `/data/public/jeong/papers/*` |

### 우리가 가져올 규약

- **adopt** — He 의 **명목-vs-관측 Pfa 병기 표 형식**. report10 에는 Pd 열이 없으므로
  **(명목 | 경험 Pfa | 배율 | 95% CI)** 로 변형. He 열의 비단조성(γ=0.98: 5.42→69.6→5.46→0)을
  함께 적시해야 인용이 정직해진다.
- **partial** — He 의 exclusion neighborhood 를 우리 zero-Doppler 마스크의 **선례로 각주**.
  ⚠ 성격이 다르고(He 는 정답 표적 위치 앵커, 우리는 표적 없는 지도의 고정 행) 무게도 없다 —
  마스크 폭 0/1/3/5 에서 @1e-4 배율이 WiFi 1.417/1.447/1.504/1.490, LTE 2.608/2.663/2.756/2.767,
  NR 1.490/1.521/1.580/1.563 으로 헤드라인을 거의 안 움직인다.
- **adopt** — Colone 의 Pd-vs-SINR@고정 Pfa 프레임. ⚠ 우리 SNR 정의는 RD 피크²/잡음셀 **중앙값**이라
  Colone 의 화이트닝 정합필터 출력 대비 **+1.59 dB 낙관**(지수분포 중앙값 = 0.693×평균)임을 명시할 것.
- **reject** — Colone 의 **MC 시행수 규율(100/Pfa)** 을 우리 K 에 적용. **범주 오류다.** 우리는 문턱을
  MC 로 추정하지 않는다 — CA-CFAR 닫힌형 α 를 쓰고 `verify_cfar.json alpha_audit` 가
  `alpha_code = alpha_theory` 를 rel_err **7.58e-16** 로 확인해 준다. Pfa 추정 단위도 시행이 아니라
  셀(맵 10,000 × 셀)이다.
- **reject** — Colone 의 CFAR-property 축(CNR·ρ)을 그대로. 우리 반무향 챔버는 ECA 후 정적 클러터가
  죽은 파라미터라 **그 축이 존재하지 않는다.** 우리 실제 nuisance 는 아래 표의 `fs/B_ref` 다.

### 수치 비교표

| 항목 | 우리값(정의) | 선행값(정의) | 사과-대-사과 | 정직한 해석 |
|---|---|---|---|---|
| α(N, Pfa) 닫힌형 구현 정확성 | `g2x2_t6x6`(N=264): alpha_code **9.37288875313056** vs alpha_theory **9.372888753130553**, rel_err **7.58e-16**; 평탄맵 발화 0 (`verify_cfar.json alpha_audit`) | 교과서 α = N(Pfa^(−1/N) − 1) | **true** | 검출기 산수 자체는 무죄. 이 확인이 있어야 뒤의 배율이 "공식 오류" 가 아니라 "상관 효과" 로 귀속된다 |
| 이상 백색잡음에서 경험/명목 Pfa | 48×24 맵 500,000장 @1e-6: 배율 0.998 / 0.995 / 1.006 / 1.008 (`verify_cfar.json white`) | (대응 없음) | — | 이상 조건에서는 CA-CFAR 이 약속을 지킨다 |

### 대응 선행 없음

- **ECA 로 정리된 준-무클러터 RD 지도에서 순수 DSP 이웃칸 상관이 만드는 명목-vs-경험 Pfa 배율.**
  He 는 강한 정적클러터가 present(ECA 없음)라 배율이 208×까지 폭발하고, 원인이 다르다.
- ⚠ 그러나 **"21편 전부 명목 Pfa 를 설정만 하고 신뢰한다" 는 좁혀야 한다.** LTE_24(Demissie)는
  참조셀의 **99% 경험 분위수**로 문턱을 잡는다 — 부분 반례다. 정직한 형태:
  **"명목-vs-경험 Pfa 교정 곡선을 잰 선행이 없다."**

### ⚠ 이 절이 드러낸 우리 쪽 문제 — 배율이 보고 창(window) 선택에 20~40배 흔들린다

`verify_cfar.json chain` 을 `pfa_nom=1e-4, gt=g2x2_t6x6, zd_mask=1` 로 직접 뽑으면:

| 파형 | noise·op | noise·wide | **dpi_eca·op** | **dpi_eca·wide** |
|---|---|---|---|---|
| WiFi80 | 1.2380 | 1.1528 | **1.4468** | **41.146** |
| LTE20 | 2.3688 | 1.3589 | **2.6631** | **58.802** |
| NR100 | 1.2465 | 1.2178 | **1.5213** | **47.704** |

잡음 전용 지도에서는 넓은 창도 멀쩡하다(1.15–1.36). 즉 41–59× 는 **운영 창 바깥의 DPI+ECA 잔차 구조**다.
He 의 DD surface 는 지연 전 구간을 덮으므로 우리 `wide` 의 대응물이지 `op` 가 아니다. **창을 맞추면
우리 41–59× 와 He 70–208× 는 2~5배 안이고**, "우리는 2.66× 로 얌전, 그들은 208× 로 폭발" 이라는
서사가 사라진다.

그리고 배율의 진짜 지배 요인은 **거리 오버샘플링비 fs/B_ref** 다(직접 계산):

| 파형 | fs/B_ref | 경험 Pfa / 1e-4 (dpi_eca·op) | dpi_eca ρ_range | eff_indep_2d |
|---|---|---|---|---|
| WiFi | 1.045 | 1.447 | 0.491 | 0.101 |
| 5G G2/G3 | 1.250 | 1.521 | 0.534 | 0.099 |
| LTE | 1.705 | 2.663 | 0.679 | 0.092 |

⚠ 주의: 운영 지도(`dpi_eca`)의 유효 독립표본 몫은 세 파형이 **사실상 동일**하다(0.101/0.099/0.092).
그런데 배율은 갈린다. 즉 "actual Pfa vs ρ_range" 그림을 **같은 인구로** 정직하게 그리면 단조 관계가
나오지 않는다. 노이즈 전용 지도(ρ_range 8.6e-5 / 0.0705 / 0.2846, eff2d 0.486/0.399/0.306,
배율 1.238/1.247/2.369)에서만 자기일관적인데, 그건 리포트 헤드라인이 아니다.

또한 CFAR 창 `g2x2_t6x6` 은 17×17 = **289 셀**인데 LTE 운영 지도는 6×48 = **288 셀** —
**창이 지도보다 크다.** 세 파형 모두 거리축에서 온전한 훈련창을 가진 셀이 하나도 없으므로,
셀을 독립 시행처럼 세는 것은 통계력 과대계상이다.

---

## 11. 리포트 11 — 저속·분해능·관측가능성

### 선행은 이렇게 했다

| 선행 | 등급 | 무엇을 했나 | 경로 |
|---|---|---|---|
| Maksymiuk 외, Rényi, *Remote Sens.* 2022, 14, 6146 | [P] | "echoes from **stationary or slowly moving targets**. Adaptive filters or the CLEAN method are used to remove them". CAF χ(R_b,V_b) eq.(3), T_int 절충. eq.(9) **Re = √(R1R2) = "the equivalent of the monostatic detection range"** | `/data/public/jeong/papers/5G/22_Rényi…pdf` |
| Maksymiuk 외, Asilomar 2025 | [P] | eq.(5) ΔR_b = c/B, eq.(8)(9) **Cassini oval**, Table I(Pt 45 dBm·Gt 15·Gr 10·S0 0.1/0.05 m²·B 50 MHz·T_int 100 ms·**F 60%**·L 10 dB·Br 61.44 MHz·**D0 10/15/20 dB**), 적분이득 = B·T_int | `/data/public/jeong/papers/5G/25_UAV Intrusion…pdf` |
| Sun 외, LIPASE, IEEE OJ-COMS 2025 (DOI 10.1109/OJCOMS.2025.3558430) | [P] | eq.(76) **R = c/(2B·cos(β_bist/2))**, 5 MHz → 30 m @β=0°. **감시 ULA 10소자 중 중앙 8소자 활성 + 기준 4소자 = 12안테나**, 간격 7 cm, 디지털 빔포밍, 2D CA-CFAR + 클러스터링. 공개 데이터셋 | `/data/public/jeong/papers/LTE/25_An Experimental Study…pdf` |
| Martelli 외 (Sapienza) | [P] | "by employing **a set of three antennas** that have both horizontal and vertical displacement" → 3D 국소화 | `/data/public/jeong/papers/Wifi/17_…pdf` |
| Sun, Guo, Li, Gerdes, ACM WiSec '22 (DOI 10.1145/3507657.3529658) | [P] | "requires only **a single wireless receiver, and at least three transmitters** to successfully locate a drone" in 3-D | `/data/public/jeong/papers/LTE/22_Passive Drone Localization…pdf` |

### 우리가 가져올 규약

- **adopt** — Re = √(R1R2) 를 검지거리 스칼라로(report13 소관).
- **adopt** — LIPASE eq.(76)을 공간분해능 병기의 1차 인용처로. ⚠ **숫자를 우리 기하로 계산할 것**:
  β = **47.60°**, cos(β/2) = 0.9150 → c/(2B·cos(β/2)) = **1.667 m** (5G 98.28 MHz).
  `dR_mono_theory_m` 의 1.53 m 는 β=0° 특수해이므로 eq.(76) 라벨을 붙이면 틀린다.
- **adopt** — Rényi 의 "클러터 제거가 정지·저속 표적을 함께 먹는다" 를 §1 정성 근거로.
- **adopt** — Martelli(3안테나) / Sun(≥3 Tx)을 §5.3 처방의 실측 선례로. ⚠ **회계 방식이 다르다**:
  Sun 은 독립 거리 3개, Martelli 는 각도이고, 우리 "측정 2개(R_b, f_d)" 는 f_d 를 위치측정으로 세므로
  **속도 기지(旣知)를 전제**한다(모르면 미지수 6개).
- **reject** — Jopanya 를 "제로패딩은 분해능을 안 올린다" 의 근거로. 그 논문은 그런 진술을 하지 않는다.
  현행 `make_notebook11.py:492-495` 는 이미 그 문장을 **우리 목소리로** 쓰고 Jopanya 는 "CRB 유도" 로만
  인용한다 — **현행이 정답이다.**
- **reject** — Jopanya CRB 축 정렬. 그들 CRB 는 (N,L) 블록크기 곡선이고 고정 기하가 없어 절대 미터가
  안 나온다. 게다가 f_c=15 GHz, f_Δ=60 kHz, 10×10 평면배열, **동기·협조 조명원**(직접경로는 known 이라
  가정하고 제거)이라 기회조명 패시브가 아니다.

### 수치 비교표

| 항목 | 우리값(정의) | 선행값(정의) | 사과-대-사과 | 정직한 해석 |
|---|---|---|---|---|
| 거리분해능 좌표계 (두 규약 공존) | ΔR_b = c/B = 3.050 m (5G 98.28 MHz, 거리합); 우리 기하 β=47.60° 에서 공간분해능 c/(2B·cos(β/2)) = **1.667 m** | LIPASE eq.(76): 5 MHz → 30 m @β=0° (공간 좌표) | **false**(좌표계 정의 상이 — 둘 다 맞음) | 지연분해능 1/B 를 R_b 로 환산하면 c/B, 표적 공간변위로 투영하면 c/(2B·cos(β/2)). "거리합 좌표계 기준" 한 줄 + β 의존 병기로 방어 완결 |
| 표적 RCS (링크버짓 입력) | mavic4pro 5G100 **−11.7845 dBsm**, s1000plus **−7.8394 dBsm** (`verify_linkbudget.json A_radar_equation`, 이등분선 ±4° 5점 평균, 단일 fc) | Asilomar Table I: S0 = 0.1 m²(−10.0) / 0.05 m²(−13.01) | **false**(우리=SBR+PO 실산출, 그들=라운드넘버 가정치, 자세·편파·앙각 정의 없음) | **자릿수 정합(order-of-magnitude sanity)** 으로만. 그들 S0 는 750 MHz·3.5 GHz·25 GHz 에 **똑같이** 쓰이므로 밴드 정보가 0 이다 — "3.5 GHz 에서 맞았다" 는 착시 |
| 3D 위치 관측가능성 | 1 TX-RX 쌍: **NOT OBSERVABLE**, 스냅샷 FIM rank **2/3**, pos_rms **57.752 m**, cond **1.94e307**(수치적 특이); baseline 축 회전 정확대칭 ΔR_b < **1.42e-14 m**, Δf_d < **4.26e-14 Hz**. 처방: 2RX → rank 6, **0.1896 m** / 1RX+AoA(1°) **0.1207 m** / AoA(5°) **0.6034 m** (`verify_observability.json`) | Martelli: 3D 에 **3안테나** 필요 / Sun: **1 Rx + ≥3 Tx** | **false**(형식화 vs 안테나 개수, 회계 방식 상이) | 결론 구조는 일치 — 단일 바이스태틱 측정 2개로 3D 위치 3미지수를 못 푼다. 우리 기여는 이를 FIM 랭크 + 정확대칭으로 형식화하고 처방별 절대 pos_rms 를 낸 것. ⚠ **"우리 고유 형식화" 로 과장 금지** — 기저선 축 회전 불변성은 회전타원체 등거리면의 정의 그 자체(Willis 교과서)다. 정직한 표현: **"교과서 대칭성을 기계정밀도로 수치검증했다"** |

### 대응 선행 없음

- **ECA 저속 블라인드 속도의 정량값.** M=48 운용 적분:
  WiFi80 **0.3906 m/s**(T_cpi 48 ms) / LTE20 **1.1042 m/s**(48 ms) / 5G100 **1.1628 m/s**(24 ms);
  불변량 f_d,3dB/Δf_d = **0.5957**(세 파형 공통) (`verify_eca.json S4_target_loss[M=48]`).
  코퍼스 21편 어디에도 MDV/블라인드 속도 수치가 없다. Rényi 는 정성 서술만 준다.
  → **우리 고유 정량 기여. 외부 근거로 팔지 말 것.**
  ⚠ 1−sinc² 이론 일치 오차는 "max 0.0015 dB" 가 아니다 — M=48 에서 5G 0.0015 / LTE 0.0025 /
  **WiFi 0.021 dB** 이므로 최댓값은 **0.021 dB(WiFi)** 다.
- **3독립검산 자기일관성**(레이더방정식 3계산 편차 **2.842e-14 dB**, `verify_linkbudget.json max_dev_db`).
  이런 내부검증을 하는 선행이 없다 — 우리 고유 검증 관행.

### ⚠ 정정 — 기존 서술의 사실 오류 3건 (2026-07-23 파일 실사)

1. **"`verify_ambiguity.json` 의 physical 블록이 비어 있다" 는 거짓.** 6개 파형 전부 채워져 있고
   `nr_G1` 은 `prf_physical_hz = 50.0`, `v_unamb_phys_ms = 1.07068735`, `cpi_phys_ms = 960.0`,
   **`aliased = true`** 를 담는다. SSB 무모호속도는 지금 그대로 소싱 가능하다.
   단 Jopanya 의 |v_u| ≤ λ_c·f_Δ/2 = 600 m/s 와는 **560배 차이**이고 이는 물리가 아니라
   슬로우타임 샘플링 모델 차이이므로 **정량비교는 금지**.
2. **CRLB σ_rb 값이 낡았다.** 현재 `verify_observability.json cells`:
   WiFi80 G1 **0.016235 m**(셀 3.747 m, 231×) / LTE20 G1 **0.012381 m**(12.856 m, 1038×) /
   5G100 G1(SSB) **1.4901 m**(39.201 m, 26×) / 5G100 G3 **0.007303 m**(2.440 m, 334×).
   기존에 인용되던 0.036 / 0.0144 / 0.0084 는 파일에 없다.
3. **`verify_eca.json`·`verify_observability.json` 은 낡지 않았다** — mtime 07-22 08:52 / 09:49.

---

## 12. 리포트 12 — 다중 Rx 검출 + 9모드 벤치마크

### 선행은 이렇게 했다

| 선행 | 등급 | 무엇을 했나 | 경로 |
|---|---|---|---|
| LIPASE (LTE_25) | [P] | **감시 8소자 + 기준 4소자 = 12안테나** 디지털 빔포밍 실측(간격 7 cm ≈ 0.42λ @1.8 GHz), 2D CA-CFAR + guard + 클러스터링. 성능은 추적 RMSE 로 채점 | `/data/public/jeong/papers/LTE/25_…pdf` |
| Di Seglio 외, IET RSN 2023/24 | [P] | 같은 표적·같은 씬에서 **프리앰블(8µs+8µs)×20 MHz = 320 샘플** vs 전 파형을 공통 지표 SBR 로 head-to-head. 프리앰블-한정 SNR loss **10–11 dB**(Fig.4) / Fig.7 비교 **~5 dB** | `/data/public/jeong/papers/Wifi/24_…pdf` |
| Wang, Zumegen, Studer, Neural ISAC arXiv:2509.21118 (JSAC) | [P] | Lemma 1: L 심볼 평균 → 잔여 잡음 분산 **N0/L**. Prop.3 | `.../isac_sensing_radar/2509.21118__*.pdf` |
| FWA arXiv:2605.07623 | [P] | M=2 BS × N=16 CPE 협력검출 MDP **0.63% (95% CI [0.37, 1.01])**, FAP 0.00%. 표적은 **metallic cube** | `papers_isac_sionna/2605.07623__*.pdf` |
| Ceresoli, Bernazzoli, Pegurri, Filippini (PoliMi), "AoA Services in 5G Networks" arXiv:2510.17342 | [P] | **USRP N310** 의 per-port 위상이 런마다 랜덤 → 0° boresight 레퍼런스 UE 로 SRS 기반 위상오프셋 추정 후 e^{−jΔφ} 보정 | `.../positioning_localization/2510.17342__*.pdf` |

### 우리가 가져올 규약

- **adopt** — FWA 의 **95% CI 병기**. K=6000 이면 Pd 이항 CI 는 즉시, snr50 CI 는 부트스트랩으로.
  현재 헤드라인 SNR50 과 모드간 차(G1−G2 = 4.059 dB)에 오차막대가 없어 유의성 판정이 불가능하다.
- **adopt** — Di Seglio 의 "신호의 어느 부분을 쓰는가" 통제 비교 프레이밍. ⚠ **report12 의 SNR50 축에
  붙이면 자멸한다**(아래 표) — **report05 의 "점유 대가 18 dB" 로 이관할 것.**
- **partial** — Ceresoli 의 위상정렬. ⚠ 두 전제가 어긋난다: (i) 논문 장비는 **N310** 이고 인용된
  제조사 문구도 N310 한정이다 — X410 은 클로킹 구조가 다르므로 "필수" 라 단정하려면 스펙 확인이 먼저다.
  (ii) 그들의 보정은 **알려진 각도에 놓은 협조적 UE** 를 요구하는데 우리 X410 실측은 패시브
  바이스태틱 야외라 그런 UE 가 없다.
- **reject** — Neural ISAC Lemma 1 을 배열이득의 sanity anchor 로. 인용은 정확하나 iid 측정 L 개 평균의
  일반 법칙일 뿐이고, 우리 √N 은 **코드가 주입한 가정**이라 앵커링할 대상이 없다.
- **reject** — OpenISAC 을 X410 실측설계의 하드웨어 아날로그로. 실제 프로토타입은 **X310 + B210**
  ("X400 series" 는 지원 범위 언급)이고 노드당 감시 RX 는 단일 안테나라 다소자 코히어런트 배열이 아니다.

### 수치 비교표

| 항목 | 우리값(정의) | 선행값(정의) | 사과-대-사과 | 정직한 해석 |
|---|---|---|---|---|
| 바이스태틱 거리분해능 규약 | G1(SSB 7.2 MHz) **41.638 m** / G3·G2(NR-PRS 98.28 MHz) **3.050 m** / WiFi(76.5625 MHz) **3.916 m** / LTE(17.985~18.015 MHz) **16.669/16.641 m** (`detection_rx_sweep.json modes.*.range_res_m`) | 5G_23: 38.16 MHz → ~7.8 m; 5G_25 eq.(5) ΔR_b = c/B, FR2 400 MHz → 75 cm | **true**(규약 정합 확인) | 결과 비교가 아니라 **정의 정합 확인(factor-2 오류 방지)**. 근거로 5G_25 eq.(5)를 추가할 것 — 서술 문장 하나(5G_23)에만 걸 이유가 없다. ⚠ 우리 `range_res_m` 은 공식 출력이지 RD 맵 메인로브 폭 실측이 아니다 |

### 대응 선행 없음 — **단, 주장을 좁혀야 한다**

- **표준-간(WiFi vs LTE vs 5G) head-to-head 벤치마크**: 21편 범위 내에서 아직 유효.
- ⚠ **"다중 Rx 이득: 전부 최대 2채널, N-Rx 코히어런트 이득을 잰 논문 0" 은 앞 절이 거짓이다.**
  LIPASE 원문: *"Both the reference and surveillance antenna arrays are ULAs, each with **ten**
  4cm × 4cm patch antenna elements. The inter-element spacing is 7 cm. The central four antenna elements
  of the reference array are activated…, while the central **eight** antenna elements of the surveillance
  array are activated… The above **twelve antennas** are connected…"*
  좁은 판본("N 에 대한 이득 **곡선**을 준 논문은 없다")은 서 있으나, **우리 곡선도 √N 해석 주입이라
  '측정' 이 아니다.** 정직한 문장:
  > 감시 다소자 실측 배열은 LIPASE 에 있다. 우리 기여는 N 에 대한 이득 곡선이며,
  > 그마저 현재는 √N 해석 주입이라 **실측이 아니라 설계 상한**이다.

### ⚠ 이 절이 드러낸 우리 쪽 문제

**(1) 배열이득이 이론 상한을 넘는다.** `experiment_detection.py:270`
`surv = sqrtN * echo[None,:] + dpi[None,:] + _noise(b)` — 배열이득은 측정된 것이 아니라 코드가
신호 진폭에 √N 을 곱해 **주입**한 것이다(소자별 채널·패턴·상호결합·조향오차 없음). 그런데 K=6000
현재 파일에서 WiFi 3모드가 전부 이론 상한 10log10(4) = 6.02 dB 를 **초과**한다:

| 모드 | W1 | W2 | W3 | L1 | L2 | L3 | G1 | G2 | G3 |
|---|---|---|---|---|---|---|---|---|---|
| N=1→4 이득 [dB] | **6.798** | **6.547** | **6.537** | 6.048 | 5.993 | 6.020 | 6.388 | 6.073 | 6.047 |

MC 잡음 규모는 σ(snr50) ≈ 0.043 dB 이므로 0.78 dB 초과는 ~13σ 다 — **"K 를 늘리면 해결" 이 아니다.**
원인 후보: (i) x축이 σ 만 스케일하는데 DPI 잔차 `dpi` 는 고정이라 √N 이 신호를 DPI 대비로도 밀어올린다,
(ii) 표적이 0-도플러 능선에서 3빈밖에 안 떨어져 CFAR 훈련창이 DPI 스커트를 문다.
**확정 실험: `DPI_AMP = 0` 으로 재실행.** 6.02 dB 로 안 떨어지면 축·검출기 버그다.

**(2) 점유 축이 SNR50 위에서 사실상 죽어 있다.**

| | G1 | G2 | G3 | 스프레드 |
|---|---|---|---|---|
| WiFi snr50 | 12.208 | 11.888 | 11.868 | **0.340 dB** |
| LTE snr50 | 13.672 | 13.585 | 13.648 | **0.087 dB** |
| 5G snr50 | 15.202 | 11.143 | 11.278 | 4.059 dB |

WiFi·LTE 는 점유율을 9%→89%, 3%→59% 로 올려도 0.1~0.3 dB 밖에 안 움직인다. 5G 만 4 dB 움직이는데
**그건 점유가 아니라 대역이 7.2 → 98.28 MHz 로 바뀌고 기준신호가 SSB → NR-PRS 로 바뀌었기 때문**이다.
게다가 점유 레벨이 표준 간 공통이 아니다(G1 = WiFi 9.13% / LTE 3.22% / **NR 1.45%**).
→ "3표준 × 3점유 = 9모드 요인설계" 는 이 지표 위에서 요인이 아니다. Di Seglio 를 여기 인용하면
**선행 5~11 dB vs 우리 0.09~0.34 dB** 로 정면충돌한다.

**(3) 헤드라인 4 dB 중 ~0.8 dB 는 CFAR 아티팩트다.** Pd=0.9 동작점에서의 **경험** Pfa 를 직접 보간하면:

| 모드 | D0(Pd=0.9) [dB] | **경험 Pfa @D0** |
|---|---|---|
| W1/W2/W3 | 15.30 / 14.64 / 14.54 | 7.1e-5 |
| L1/L2/L3 | 16.14 / 16.09 / 16.12 | 4.5–5.2e-5 |
| **G1 (SSB)** | **17.86** | **1.305e-5** |
| G2/G3 | 13.76 / 13.90 | 7.6–8.1e-5 |

**G1 은 G2/G3 보다 6배 엄격한 오경보율에서 측정됐다.** 지수분포 문턱 T = μ·ln(1/Pfa) 로
10log10(11.30/9.485) = **0.76 dB** 의 문턱 상승이 그대로 SNR50 에 실린다.
원인은 G1 의 거리 오버샘플링(fs/B_ref = **17.07**)으로 CUT 와 훈련셀이 강하게 상관하기 때문이다.
더 나쁜 것: G1 분해능 41.6 m 인데 CFAR 훈련셀은 CUT 에서 (guard 2 + train 6) × 2.44 m = **19.5 m** 지점 —
**표적 자신의 메인로브 안**이다. **G1 만 자기가림(self-masking) 레짐**이다.

---

## 13. 리포트 13 — 자유공간 검지거리 (설계 단계)

### 현재 상태

- `src/make_notebook13.py` **없음**, `report13.ipynb` **없음**, `outputs/report13*.json` **없음**.
- 그러나 **설계 문서는 있다**: `docs/REPORT13_DESIGN.md`(64 KB) + `docs/REPORT13_SPEC.md`(63 KB),
  둘 다 2026-07-22 09:58. SPEC 은 적대적 반증 4라운드를 전량 판정한 최종 구현 스펙이다.
  (⚠ 선행 조사 과정에서 "report13 을 언급하는 파일은 `RESUME_0722.md` 하나뿐" 이라는 보고가 있었으나
  사실이 아니다 — §15 에 기록.)
- 아래는 전부 **"13 을 지을 때 이렇게 하라"는 처방**이고, 수치는 내가 기존 JSON 을 선행 식에 대입해
  계산한 **파생값**이다(아직 `outputs/` 에 없음).

### 선행은 이렇게 했다

| 선행 | 등급 | 무엇을 했나 | 경로 |
|---|---|---|---|
| Maksymiuk 외, Asilomar 2025 | [P] | 검지거리를 **Cassini oval** 로. eq.(9) R1R2 < sqrt(Pt·Gt·Gr·S0·λ²·B·T_int·**F** / ((4π)³·L·k·Tr·Br·D0)). Table I 전 10항목. D0 = 10/15/20 dB 스윕. "ca. 3 km at 3.5 GHz". 캐비엇: "these predictions assume the target is located at the center of the base station antenna beam, which represents an **idealized scenario**" | `/data/public/jeong/papers/5G/25_UAV Intrusion…pdf` |
| Rényi (Remote Sens. 2022) | [P] | **Re = √(R1R2) = 등가 모노스태틱 검지거리**. Pd 대 점유율 곡선을 Pfa 1e-4/1e-6/1e-8 에서. Table 2: D0 11 dB, T_int 20 ms, T0 493 K | `/data/public/jeong/papers/5G/22_Rényi…pdf` |
| Rzewuski 외, NATO STO-MP-MSG-SET-183 | [P] | 커버리지를 **RCS_min(x,y) [dBsm] 공간지도**(흰 영역 = 검출 성공)로. eq.(4)에 **duty factor F_u** 명시(WiFi 실측 듀티 18%). D0 = 8 dB @Pfa≈1e-4(단, "연속 조명 + 높은 갱신율" 근거의 **트랙 레벨** 문턱). Parrot AR.Drone 2.0 FDTD: WiFi 대역 σ **−40~0 dBsm(평균 ~−20)** | `/data/public/jeong/papers/Wifi/21_Drone Detectability…pdf` |
| Demissie 외, IEEE RadarConf 2024 | [P] | LTE450 실측 최대 검지거리: **Pfa=0.01 → 2700 m, Pfa=1e-4 → 약 1500 m** (DJI M210 88×88×39 cm). CUT 최대전력 vs 바이스태틱 거리 **이중로그 + 봉우리 선형피팅 + 문턱 교점**. 실측 CUT 전력이 **진동**(직접경로+반사 간섭) | `/data/public/jeong/papers/LTE/24_Protection…pdf` |
| Sun 외, WiSec '22 | [P] | 20 m 실측 → T-Mobile 타워 5기 링크버짓으로 **외삽**, geofencing zone 약 20,000 m². "at least 3 LTE cell towers" | `/data/public/jeong/papers/LTE/22_…pdf` |
| Ji 외 arXiv:2602.08203 | [P] | LTE 1.85/1.87 GHz, eNB-Rx 200/220 m, UAV-Rx <30 m(Re ≈ 77 m), 추적오차 <50 cm @90%. 표적 = **알루미늄박 25×20×40 cm 판지상자**를 매단 쿼드콥터 | `papers_isac_sionna/2602.08203__*.pdf` |

### 우리가 가져올 규약

- **adopt** — Re = √(R1R2) 스칼라 + Cassini oval(Tx ×, Rx ○, baseline L 명시) + D0 10/15/20 3곡선 +
  Table I 형식 파라미터 표 + "idealized scenario" 캐비엇.
- **adopt** — RCS_min(x,y) 공간지도. **5기종 비교에는 Cassini(기종당 1장)보다 이쪽이 낫다** —
  지도 1장 + 5개 σ 레벨선. ⚠ 캡션에 "방위평균·el=15°·편파 미분리·바이스태틱각 β 무시" 명시
  (지도 위 각 점은 서로 다른 β 를 갖는다).
- **adopt** — Demissie 의 **검지거리를 Pfa 함수로** 보고(단일 숫자 금지) + 이중로그 봉우리 피팅.
  ⚠ **기울기는 −20 dB/decade** 다(R1R2 축). P_r ∝ (R1R2)^−2 이므로. −40 dB/decade 는 Re 축(또는
  모노스태틱 R 축)에서만 성립하고, Demissie Fig.8 의 실제 x축은 **bistatic range** 다.
- **adopt** — Sun 의 **외삽 정직성 템플릿**: "검증된 것은 체인이지 거리가 아니다" + 면적 [m²] 병기.
- **partial** — F(점유율). ⚠ **B 도 모드별 `ref_bw_mhz` 로 함께 치환해야 한다** — B 를 선행의 50 MHz 로
  고정한 채 F 만 바꾸면 ref_bw 7.2 MHz 인 G1 이 98.28 MHz 와 같은 적분이득을 받는 **하이브리드**가 된다.
- **reject** — F(자원격자 점유)와 F_u(duty)를 **동시에** 넣는 것. Asilomar eq.(9)에는 F 만,
  Rzewuski eq.(4)에는 F_u 만 있다 — 같은 물리손실의 **대체 파라미터화**이지 곱할 대상이 아니다.
  우리 `occ_pct` 가 시간축 희소성을 이미 포함하는지(SSB 1.447% ≈ 주파수 7.2% × 시간 ~20%)
  정의를 확정하기 전에는 둘 중 하나만 쓴다.
- **reject** — Rzewuski D0 = 8 dB 를 우리 단일-CPI 문턱과 직접 비교. 그건 **트랙 레벨** 문턱이다.
- **reject** — 모드별 D0 를 우리 측정치로 갈아끼우는 것(현 상태). 모드마다 경험 Pfa 가 다르다(§12 참조).

### 수치 비교표

| 항목 | 우리값(정의) | 선행값(정의) | 사과-대-사과 | 정직한 해석 |
|---|---|---|---|---|
| 3.5 GHz 소형 드론 σ (S0 입력) | 방위평균 **−13.860 ~ −22.250 dBsm** (0.0411 ~ 0.00596 m²): s1000plus −13.860 / mavic4pro −18.365 / phantom4 −18.854 / matrice4e −22.226 / mini5pro −22.250 (`report2_waveform_rcs.json`, 361점 선형평균, el=15°, 대역 5주파수 평균, 모노스태틱, 정지 프롭, 편파 미분리) | Asilomar Table I: S0 = 0.1 m²(−10.0) / 0.05 m²(−13.01), **가정치·정의 없음** | **false**(선행은 σ 정의 자체를 안 밝힘; 우리는 모노스태틱인데 Cassini 는 바이스태틱 σ 요구) | 밴드는 3.5 GHz 로 정확히 일치하므로 **스케일 비교는 정당**. **우리 5기종은 전부 선행 가정보다 어둡다** — 가장 밝은 s1000plus 조차 0.1 m² 에 4.1 dB 못 미치고 mini5pro 는 12.3 dB 아래. 말할 수 있는 것: "선행의 검지거리 예측은 실제 기체보다 밝은 표적을 가정하고 있다." 말하면 안 되는 것: 우리 σ 가 더 정확하다 |
| **순수 점유율 효과** (G2↔G3) | 같은 식·같은 야외 링크버짓(Asilomar Table I 고정)에 우리 σ(mavic4pro −18.365)·우리 D0·우리 F 대입: **G2(F=17.75%, D0=13.76 dB) → 1692 m**, **G3(F=79.75%, D0=13.90 dB) → 2444 m**, 비 **1.444** | 선행 기준선(S0=0.1, D0=15, F=60%, Tr=290 K) → **3457 m** (내 재구현; 논문 본문 "ca. 3 km" 재현) | **true**(G2↔G3 한정) | **G2 와 G3 는 ref_bw(98.28 MHz)·CPI(56 ms)·M(112)·range_res(3.050 m)가 비트단위로 같고 occupancy 만 다르다** → 순수 점유율 효과 1.44배가 깨끗하게 분리된다. **이것이 report13 이 정직하게 주장할 수 있는 전부다.** G1 을 넣으면 ref_bw 가 1/13.6 이라 존재하지 않는 하이브리드 시스템이 된다 |
| 기종별 검지거리 (G3 모드) | mini5pro **1954 m** / matrice4e **1957 m** / phantom4 **2376 m** / mavic4pro **2444 m** / s1000plus **3167 m** — 스팬 **1.62배** | (대응 없음 — 문헌은 전부 1기종) | — | 파생값이며 `outputs/` 에 없다. Re ∝ σ^(1/4) 이므로 σ 8.4 dB 스팬 → 거리 1.62배 |
| WiFi 대역 σ | WiFi 5.21 GHz 방위평균 −12.922 ~ −21.565 dBsm (peak −4.186 ~ −15.811) | Rzewuski FDTD(Parrot AR.Drone 2.0, 폴리프로필렌+탄소섬유): WiFi 대역 **−40 ~ 0 dBsm, 평균 ~−20** | **false**(표적·엔진 FDTD vs SBR+PO·편파 Eφ vs 미분리·앙각) | 방향성만: 독립 FDTD 가 낸 소형 플라스틱 쿼드콥터 σ 범위와 우리 SBR+PO 5기종이 **같은 자릿수**에 있다. ⚠ −20 dBsm 에 가장 가까운 것은 mini5pro 가 아니라 **matrice4e(−20.215)** 이므로 "크기 순서와 일관" 이라는 논거는 성립하지 않는다 |
| 실측 검지거리 스펙트럼 | (우리 실측 없음. 챔버 기하는 R1=18.748·R2=18.608·L=15.075 m → Re=18.68 m 로 **검출 한계가 아니라 방 크기**) | LTE450 **2700 m @Pfa=0.01 / 1500 m @Pfa=1e-4**(M210) · LTE1800 200 m(Phantom 4, 인용) · WiFi 50 m(운용자 거리 제약) · DVB-T 200 m · LTE 테스트베드 20 m(반사체 부착) · Ji Re≈77 m(알루미늄박 상자) | **false**(우리에겐 대응 실측이 없다) | 두 용도만 정당: (1) **Pfa 를 밝히지 않은 검지거리는 무의미하다** — 같은 실험·같은 기체에서 Pfa 를 1e-2→1e-4 로 조이자 2700→1500 m 로 1.8배 줄었다. (2) 우리 파생 Re(1954~3167 m)가 실측 스펙트럼(50 m ~ 2700 m) 상단에 걸친다는 sanity check. ⚠ Ji·Sun 의 표적은 **반사체 부착 개조 상태**라 맨몸 실적으로 인용 금지 |

### 대응 선행 없음

- **"반사체가 전혀 없는 자유공간" 을 명시적 연구대상으로 삼은 패시브 드론 검출 선행.** 문헌은 전부
  야외 실측(다중경로 포함) 또는 도시 매크로셀 가정이다. 오히려 Demissie 는 실측 CUT 전력의 진동을
  "직접경로 + 1개 반사의 간섭" 으로 해석하므로 **야외 실측조차 자유공간이 아니다.**
  → report13 의 "반사체 없음" 은 비교 대상이 아니라 **이상화**이며 그렇게 명시해야 한다.
  (`REPORT13_SPEC.md` 의 FS-0/1/3 사다리와 "상한선 주장 철회 → 기준정규화 재정의" 판정이 이미 그렇게 한다.)
- **한 논문 안에서 상용 드론 5기종의 검지거리를 나란히 낸 선행.** 읽은 21+27편 전부 단일 기종이다.
  → report13 의 진짜 새로움. 단 "아무도 안 했다" 가 "우리가 옳다" 는 뜻은 아니다.
- **Sionna 로 드론 검지거리를 낸 선행 0편.** `sionna_papers_by_task/` 의 coverage 는 전부 통신
  coverage_map(스칼라 경로이득)이고 `cassini` 는 0건이다. → report13 은 Sionna 계열 선행 없이
  패시브 레이더 문헌 계열만으로 서야 한다.
- **회전 프로펠러 상태 σ 로 낸 검지거리** — 선행도 우리도 없다(양쪽 다 정지 프롭).
- **편파별 검지거리** — Demissie 는 쿼드콥터 에코가 탄소섬유 블레이드 때문에 수평편파 우세이고
  H 가 V 보다 ~15 dB(안테나 이득차 5 dB 보정 후 ~10 dB) 높다고 실측 보고하나, 우리는 스칼라 Γ 라 재현 불가.

### ⚠ 파생값 인용 시 필수 캐비엇

1. 위 Re 값은 **`outputs/` 에 없다.** report13 구현 시 `outputs/report13_freespace.json` 에 생산할 것.
2. **Tr = 290 K 는 Asilomar Table I 에 없다.** 나는 재구현에서 290 K 를 썼고 그 결과가
   본문 "ca. 3 km" 와 맞았지만, 같은 저자군의 Rényi 는 실효 잡음온도를 **493 K** 로 쓰며 그 경우
   기준선이 3457 → **3027 m** 다. 둘 다 "ca. 3 km" 라 논문 문장으로 판별이 안 된다 →
   **"식을 재현해 검증했다" 는 자유 파라미터 1개를 끼워 맞춘 것**이며, 두 경우를 병기해야 한다.
3. **σ 자세의존을 단일값으로 누르면 안 된다.** mavic4pro 3.5 GHz 가 방위평균 −18.365 / peak −13.056 이고
   Re ∝ σ^(1/4) 이라 **peak 로 자랑하면 2444 → 3252 m** 다. 문헌이 경계하는 "특정 자세로 최대거리
   자랑하기" 함정에 정확히 해당 → **백분위 밴드(p10/p50/p90)** 로 낼 것.
4. **Pt 45 dBm 은 선행에서 빌린 값**이지 우리 시스템 스펙(챔버 EIRP 12 dBm)이 아니다.
5. **모노스태틱 σ 를 바이스태틱 Cassini 식에 넣은 근사**다. `rcs_sbr_multistatic()` 출력이 필요하다.

---

## 14. 폐기된 비교 — 만들려다 실패한 것

정직성이 이 문서의 목적이므로, 검증에서 죽은 비교를 사유와 함께 남긴다.
**이 목록에 있는 짝은 리포트 본문에 넣지 않는다.**

| # | 폐기된 비교 | 사망 사유 |
|---|---|---|
| K1 | report01: 우리 닫힌형 자기일치(지연 5.85e-6 ns / 세기 0.00045 dB) ↔ AIRMap RT-대-실측 갭(상관 0.3967) | 서로 다른 양의 병치(sim-vs-닫힌형 vs sim-vs-실측). 게다가 "독립 증거" 라던 지연도 독립이 아니다 — Sionna 정반사 경로탐색 자체가 **image method** 이므로 우리 손계산과 같은 알고리즘의 자기일치다. 실제로 검증되는 것은 씬 좌표·단위·프리미티브 식별뿐 |
| K2 | report01: 챔버 30×20×11 m + SCR span 1.06e-9 dB ↔ Neural ISAC 방 크기 5→15 m 확대 시 정확도↑ | 메커니즘 축이 다르다(그들=경로손실, 우리 SCR span=ECA 도플러-0 사영 산물로 어떤 방에서도 같은 값). 우리 자체 RT 가 반증한다 — 천장 흡수체 −9.82 dB 가 바닥 −14.68 dB 보다 세다 |
| K3 | report01: ITU-R P.2040 재질 "일치"(apples=true) | 비교가 아니다(prior_value 에 숫자 없이 키 이름 목록뿐). 실질적으로도 틀리다 — 챔버 삼각형의 **92.0% 가 P.2040 밖 자체 모델값**(source=custom, "⚠실측치 아님") |
| K4 | report02: subdivision invariance 2.9e-7 dB 를 Ziganshin 이산화 우려의 반증으로 | **항등식**. `trimesh.subdivide()` 는 중점 분할이라 표면이 비트 단위로 동일 → facet-vs-진짜곡면 편차 s 를 1 나노미터도 줄이지 않는다 |
| K5 | report02: 외곽 L/W/H 0% · mavic4pro 대각 −0.57% · mini5pro 0.00% | 자기참조. 외곽 0% 는 `frame_fit_scale()` 구속조건이고, mavic 441 mm 는 우리 모델 역산값, mini5pro 는 면내 배율 1.0 이라 대수 항등식 |
| K6 | report03: 방위별 RMS 6.7–10.8 dB ↔ Ziganshin 그림자 MAE 2.7–8.3 dB | 우리 값이 오염됐다(prop 90° 회전, Phantom4 반위상, M600 실루엣 무상관). 선행 값도 다른 양이다(근접장 40λ 총 전계 MAE, 깊은 그림자, monostatic 0회 등장, RMS≠MAE). "회절보정 전→후" 라벨도 원문과 다르다(Table I 은 전부 vertex 회절 켜짐) |
| K7 | report03: max\|Δσ_mean\| 1.79 dB ↔ Zhang 교정구 1.89 dB | 우리 값이 지표 정의에 의존한다(선형 방위평균이라 글린트 지배 — M600 은 상위 6방위가 92%). 채택하겠다는 Zhang 규약(dB 영역 log-normal)을 적용하면 M600 이 +1.57 → **−5.45 dB** 로 뒤집혀 최악 오차가 3배가 된다. 그리고 선행 값은 **계측 눈금오차**, 우리는 **두 계산 메쉬의 자기정합** |
| K8 | report04: 우리 5G ΔR 3.05 m ↔ 선행 "~3 m @100 MHz / 7.8 m @38.16 MHz" | 동어반복(양쪽 다 c/B 를 거의 같은 B 에 대입). 선행 "~3 m" 도 측정이 아니라 스펙 인용. 게다가 우리 G3 는 `ref = "NR-PRS"` 인데 "풀채널(부하)" 로 라벨이 오기됐고, `make_notebook04.py` 는 PRS 와 captured full-waveform 을 **"섞어 인용하지 말라"** 고 금지한다. 두 출처(5G_23, 5G_25)도 같은 실험이다 |
| K9 | report05: NMSE −135 dB ↔ OpenISAC EVM 10.8% | 비교 가능한 양이 아니다. 우리 격자·CP 를 채점자에게 그대로 건네므로 −135 dB 는 물리 상한 없는 자기일치 바닥(float64 로 바꾸면 임의로 내려간다). 자릿수도 6이지 7이 아니다 |
| K10 | report05: corr 1.0000 ↔ Wu "good agreement" | prior_value 가 숫자가 아니다(CDF 육안 정성). "우리가 더 엄격" 은 방향이 반대다 |
| K11 | report06: 확산 S ×4 → +26.72 dB / 20.34 dB/decade ↔ 2603.28736 | 우리 쪽 정의 혼선(코히어런트 span + 인코히런트 slope 를 한 문장에), 두 원장 혼용(같은 조건 6.2 dB 불일치), 선행은 슬로프 미보고 + 밴드 스코핑 제거된 오인용 |
| K12 | report06: 평판 −7.913 dB ↔ image-source −7.882 dB (apples=true) | 비교가 아니다 — prior_value 가 "수치 미제시" 이고, −7.882 는 `make_notebook06.py:114` 가 우리 기하로 계산한 교과서 폐형식이다. 이론 자기일치 검사이지 선행비교가 아니다. 덤: "시드편차 5.4e-6 dB" 는 오라벨(그건 판 크기 6개 산포, 시드 sd 는 3.54e-7) |
| K13 | report07: 구 오차 +0.02~+0.21 dB ↔ Sagitta 광학영역 std ~2.5% | 우리는 단일 입사방향(az=0,el=0) 바이어스, Sagitta 는 "averaged across incident directions" 의 kr 스윕 산포. 기준해도 다르다(πr² 점근 vs 정확 Mie). **같은 산포 지표로 맞춰 재면 우리가 진다**: div≥8 구간 σ/exact 선형 std **15.5%**, div≥16 **8.6%** vs Sagitta 2.5% |
| K14 | report07: 평판 −0.0137 dB @λ/6 를 "엔진 검증" 으로 | 수직입사라 위상항이 상수 → λ 가 항등적으로 소거 → **전자기 정보 0**. plate_err 이 div{6,12,30}·{8,16} 에서 비트 단위 동일한 것이 지문 |
| K15 | report08: mavic4pro peak −13.06 ↔ Li&Ling Inspire 1 −13.7 ("어깨를 나란히") | 크기 짝을 안 맞췄다(441 mm ↔ 560 mm). 크기로 맞추면 **+8.0~+15.8 dB 과밝음**으로 결론이 뒤집힌다 |
| K16 | report08: 방위평균 −18.37 ↔ "포락선 −28~−16 dBsm" | 순환논증. 그 포락선은 Li&Ling 원문값이 아니라 report08 이 aspect-peak 에서 유도한 2차 산물이다 |
| K17 | report08: 밴드 기울기 +0.26~+1.48 dB/GHz ↔ Zhang 0.31 / Ezuma 0.263 | 3점 회귀 R² 가 mavic4pro **0.13**, matrice4e 0.47 — 분산의 13%만 설명하는 기울기다. 밴드도 완전 분리(1.8–5.2 vs 10–36 GHz). Zhang 의 0.31 은 3성분 분해의 **대규모 인자 A** 기울기이지 방위평균 기울기가 아니다 |
| K18 | report08: 유전체만 −6.86 dB ↔ Semkin 카본-플라스틱 +7 dB | 선행 값 자체가 재질을 분리하지 못한 교란 측정이다(M100 650 mm vs Mavic Pro 335 mm → 면적 스케일링만으로 +5.7 dB). 물리도 다르다(한 기체에서 금속 제거 vs 두 기체 재질 차) |
| K19 | report08: Phantom 4 −18~−19 ↔ Quevedo −20~−4.6 dBsm | 선행 값이 **15.4 dB 폭 범위**라 어떤 소형드론이든 삼킨다 — 반증 불가능한 진술. 로컬 소스끼리도 밴드가 불일치(refs 노트 "X-band 8.75 GHz" vs pilot_findings "broad") |
| K20 | report08: 방위평균 −18.37 ↔ Güvenç 서베이 −15.2 dBsm | 지표정의(peak/mean) 미상 + 세대차. 게다가 `make_notebook08.py` §6 이 이 행을 "대형·고정익·고주파" 로 이미 실격시켰는데 `prior_work.json` verdict 는 "범위 내" 로 읽는다 — **우리 내부 판정 충돌** |
| K21 | report08: four-leaf 를 **로브 개수**(20~29개)로 판정 | 범주 오류. Zhang 의 four-leaf 는 A(f) 정규화 후 4섹터 **포락선 모델**이고 잔차 B2 는 따로 log-normal 로 모델링된다. 개수는 잔차 리플을 센 것 → 거짓 음성. 포락선으로 재면 phantom4 는 재현한다(§8 표) |
| K22 | report09: SCR span 1.06e-9 dB 를 "정적 클러터 무해" 의 물리 증거로 | 모델의 항등식. 주입 클러터가 도플러 없는 지연복제 = ECA 기저 그 자체라 진폭 무관 소거된다(`geometry.py:23-37` 자체 문서화). "구현 정합성 검사" 로만 |
| K23 | report09: p_false=1.0 "100% 오검출" | 궤적 중앙 **단일 스냅샷 N=60** 값이다. 궤적 전체(`verify_ghost_impact.json`, 27셀)는 5G 평균 **0.483**, CFAR 여유 평균 **−1.78 dB** |
| K24 | report09: ghost_db −18.07 dB ↔ CellSense Pd 0.22→0.74 / Pfa 0.88→0.10 | 좌변이 없다(report09 는 Pd/Pfa 를 산출하지 않는다고 스스로 적음). 클러터 종류·표적·조명·지표 4축 전부 어긋남 |
| K25 | report10: 배율 1.45/2.66/1.52 @1e-4 ↔ He 208×/70× | 우리 숫자가 **보고 창 선택에 20~40배 흔들린다**(op 1.45 ↔ wide 41.1). He 의 DD surface 는 우리 `wide` 의 대응물이다. 창을 맞추면 2~5배 안이라 "원인이 달라 등치 불가" 서사가 사라진다 |
| K26 | report10: LTE 배율 5.67 @1e-6 ↔ He adapted 5.46 | 함께 붙인 "명목이 깊어질수록 배율↑" 교훈이 **인용한 그 열에서 반증된다**(He γ=0.98: 5.42→69.6→5.46→0/0/0, 1e-4→1e-6 에서 12.7배 하락). 양쪽 다 예산 고갈 직전의 불안정 점 |
| K27 | report10: 배율 vs ρ_range ↔ Colone Fig.9 CFAR property | 인구 뒤섞기(배율은 dpi_eca, ρ_range 는 noise). 같은 인구로 그리면 eff_indep_2d 가 0.101/0.099/0.092 로 사실상 동일한데 배율만 갈려 단조 관계가 없다. Colone 문턱은 CNR=25 dB·ρ=0.9 에서 MC 교정돼 정의상 그 점을 통과한다 |
| K28 | report10: MC 예산 vs Colone 100/Pfa (apples=true) | 범주 오류. 우리는 문턱을 MC 로 추정하지 않고 닫힌형 α 를 쓴다(rel_err 7.58e-16). 단위도 시행 vs 셀이고, CFAR 창(289셀)이 LTE 지도(288셀)보다 커서 셀들이 훈련 데이터를 거의 전부 공유한다 |
| K29 | report12: N=1→4 배열이득 6.0~6.8 dB ↔ 이론 10log10(4)=6.02 dB (apples=true) | **동어반복.** `experiment_detection.py:270` 이 `sqrtN * echo` 로 이득을 **주입**한다. 게다가 주입한 값이 이론 상한을 넘는다(WiFi 3모드 6.537~6.798 dB, ~13σ) — 물리적으로 불가능한 결과가 헤드라인에 찍힌다 |
| K30 | report12: SNR50 11~15 dB ↔ Asilomar D0 10/15/20 dB | 측정 동작점 vs **선언된 스윕값**. 우리 SNR 은 잡음셀 **중앙값** 기준이라 평균 기준 대비 +1.59 dB 낙관. 그리고 G1−G2 4.06 dB 중 ~0.8 dB 가 Pfa 불일치 아티팩트 |
| K31 | report12: 경험 Pfa 비 ↔ Colone CFAR property | 우리 반무향 챔버에는 CNR·ρ 축이 존재하지 않는다(정적 클러터가 죽은 파라미터). 진짜 nuisance 는 fs/B_ref 다 |
| K32 | report12: N=1→4 이득 ↔ FWA MDP 0.63% | 지표·메커니즘·노드수·표적(metallic cube)·기하 5축 어긋남. 방향성조차 성립 안 함 — 우리 이득이 관측이 아니라 주입이라 "노드↑ → 검출↑" 를 우리가 관측한 바가 없다 |
| K33 | report13: 모드별 D0 13.7~17.9 dB 를 "선행 가정을 사후 검증" | 모드마다 **경험 Pfa 가 6배 다르다**(G1 1.305e-5 vs G2/G3 7.6–8.1e-5). "같은 Pfa 에서 측정" 이라는 전제가 거짓. 그리고 Asilomar 10/15/20 은 가정이 아니라 선언된 스윕이다 |
| K34 | report13: "SSB 의 대가 = 검지거리 3.4배(2444→713 m)" | B 를 50 MHz 로 고정한 채 F·D0 만 바꿔서, G1 의 713 m 는 "50 MHz 적분이득 + 7.2 MHz 사슬 문턱" 이라는 **존재하지 않는 하이브리드**의 숫자다. G2↔G3(1.44배)만 깨끗하다 |

---

## 15. 총평

### 15-1. 우리 절대값이 선행 대비 어디에 서 있나

| 축 | 우리 위치 | 근거 |
|---|---|---|
| **RCS 절대값** | **크기 짝 실측 대비 +8~16 dB 과밝음** | 크기로 짝을 맞춘 Li&Ling 대조(§8). 특히 phantom4(350 mm) ↔ Phantom 2(350 mm) = **+15.79 dB**. 기존 "포락선 안, 밝은 상단" 서술보다 훨씬 나쁜 위치다. ⚠ 편파 미분리(문헌 스프레드 10 dB 급)·[N] 등급·peak 샘플밀도 편향이 불확도에 겹친다 |
| **RCS 방위 구조** | **재현한다(양성)** | phantom4 의 4차 조화가 AC 에너지의 **58.9%**, 4섹터 스프레드 0.11 dB — 교과서적 four-leaf. Mavic 계열·8암은 재현 안 하는데 그건 동체 대칭성상 **기대되는 바**다 |
| **파형 충실도** | 비교 대상 없음(자기일치 바닥) | NMSE −135 dB 는 물리 충실도가 아니라 두 소프트웨어 구현의 float32 반올림 바닥 |
| **SBR+PO 정확도** | **Sagitta 대비 산포 6배 나쁨**, 유효구간 **하단 가장자리** | div≥8 σ/exact 선형 std 15.5% vs Sagitta 2.5%. kr=36.7 은 Sagitta 유효 하한 kr=30 의 1.22배 |
| **검출기 교정** | 명목 Pfa 를 못 지킨다 — **창에 따라 1.45× ~ 58.8×** | `verify_cfar.json` 직접 실사(§10) |
| **검지거리(파생)** | 실측 스펙트럼(50 m ~ 2700 m)의 **상단**에 걸침 | G3 모드 1954~3167 m. 단 Pt 45 dBm 은 빌린 값이고 σ 는 선행 가정보다 어둡다 |
| **관측가능성** | 교과서 결론을 기계정밀도로 확인 | FIM rank 2/3, 회전 정확대칭 1.42e-14 m |

### 15-2. 이 프로젝트가 선행 대비 새로 말하는 것 (정직하게)

**살아남은 것 4개:**

1. **통제된 3표준 head-to-head 조명원 벤치마크.** 코퍼스 21편이 전부 조명원 하나씩만 고른다.
   같은 챔버·같은 표적·같은 검출 체인 위에서 WiFi/LTE/5G 를 나란히 놓은 선례가 없다.
   ⚠ 단 현재 **점유 축은 SNR50 위에서 사실상 죽어 있다**(WiFi 0.34 dB, LTE 0.09 dB) — "3×3 요인설계"
   라는 서술은 수정해야 한다.
2. **공개 제원표 → 오픈소스 파라메트릭 드론 CAD + 수밀 게이트.** 확인한 8편이 전부 외부 에셋/
   점산란체/실측 중 하나다. 적대적 검증에서도 무너지지 않았다.
3. **ECA 저속 블라인드 속도의 정량화.** 0.39–1.16 m/s(M=48), 노치 1−sinc² 형태, 불변량
   f_d,3dB/Δf_d = 0.5957. 코퍼스에 MDV 수치가 0건이다.
4. **명목-vs-경험 Pfa 교정 곡선.** 선행은 명목 Pfa 를 설정만 하고 신뢰한다(LTE_24 의 경험 분위수가
   부분 반례). ECA 후 준-무클러터 지도에서 **순수 DSP 상관**만 떼어 재고 절제실험으로 인과를
   못박은 선례가 없다.

**보류·철회해야 하는 것 3개:**

5. ~~"표적경유 바닥 유령을 별개 오검출로 정량화한 선행 0건"~~ → **보류.**
   Mazhar 2016(IET RSN, "target multipaths")·Rabaste 2015(IEEE Radar Conf, "Doppler shifted multipaths")
   가 존재한다. 원문 미확보라 "정량화했는지" 는 미확인이지만, 확보 전까지 독창성 주장 불가.
6. ~~"다중 Rx 이득: 전부 최대 2채널"~~ → **철회.** LIPASE 는 감시 8소자 λ/2 급 ULA 실측이다.
   좁은 판본("N 에 대한 이득 곡선 없음")은 서 있으나 **우리 곡선도 √N 주입이라 측정이 아니다.**
7. ~~"구세대 LTE CRS > 5G SSB 헤드라인에 직접 대응 선례 없음"~~ → **과장.**
   Rényi(Remote Sens. 2022)가 SSB 를 알면서 "대역이 좁아서" 데이터로 갔다고 적는다.

**없다고 말해야 하는 것:**

- **새 물리는 없다.** SBR+PO 는 확립된 아키텍처(Sagitta 와 같은 계열), ECA→CAF→CFAR 는 표준 체인,
  Cassini·Re·c/B 는 전부 문헌 규약이다.
- **Sionna 로 드론 RCS 를 낸 것 자체도 "최초" 라 말할 수 없다.** NVIDIA 메인테이너가 Discussion #844 에서
  "This is currently not supported" 라 답했고 우리가 그 위에 얹은 것은 맞지만, 같은 우회를
  Ziganshin(A2, UTD in-place)이 이미 출판했다. 차별점은 **소형·다중재질 드론 + PO 표면적분**이라는
  니치이지 "최초" 가 아니다.

### 15-3. 이 문서가 리포트 전체에 요구하는 것 (우선순위)

| 우선 | 조치 | 대상 |
|---|---|---|
| 1 | `DPI_AMP = 0` 대조 실행 — 이득이 6.02 dB 로 안 떨어지면 §4 표와 §6 novelty 표 전부 보류 | report12 |
| 2 | 모드별 CFAR α 재교정(경험 Pfa = 1e-4 정렬) 후 SNR50 재산출 | report12 |
| 3 | 크기 짝 Li&Ling 대조로 §0/§6 헤드라인 교체 + "±1 dB"·"약 5 배" 정정 | report03·08 |
| 4 | 평판 검증을 비스듬입사로 재측정하거나 "면적 구적 확인" 으로 강등 | report07 |
| 5 | ghost 헤드라인을 `verify_ghost_impact.json` 궤적 평균으로 재서술 | report09 |
| 6 | 보고 창(op/wide) 명시 + wide-vs-wide 로 He 대조 | report10 |
| 7 | 교차 원장 단일화(rt_ray_budget 5 seeds), metal_share 퍼센트 통일 | report06 |
| 8 | §4 stale 수치 갱신(6→2.00 dB, 3.9→1.399 dB, 25,676→28,548면) | report07 |
| 9 | 편파 미분리를 캡션 각주가 아니라 **불확도 예산**으로 승격 | report08·전편 |

---

## 16. 날조 검사 기록

적대적 검증에서 fabrication_suspects 로 걸린 인용을 **전부** 나열하고 처리 결과를 적는다.
**노골적 날조(존재하지 않는 논문·조작 수치)는 리포트 본문에서 발견되지 않았다.**
걸린 것은 (a) 오인용·범위 축소된 인용, (b) 우리 자신의 숫자 오독, (c) 미확인을 확인처럼 쓴 것이다.

### 16-1. 선행 인용 — 오인용·오귀속 (11건)

| # | 인용 | 문제 | 처리 |
|---|---|---|---|
| F1 | 2603.28736 "메쉬 위 순수 경면 RT 는 산란전력 과소평가, λ/10 메싱 불가능" | 원문의 밴드 스코핑 **2개가 삭제**됨: *"…at **mmWave/sub-THz** due to **electromagnetic roughness**; direct meshing at O(λ/10) is infeasible **at E-band** [12]."* 3.5 GHz 에서 λ/10 = 8.6 mm 는 불가능하지 않다. 원인도 다르다(거칠기 vs PO 적분 부재). 그 문장은 논문 자체 발견이 아니라 [12] 인용 | **report06 핵심 지지에서 제거.** route (b) 예시로만 |
| F2 | Beuster 2402.16591 "헥사콥터" / "HFSS/FEKO/CST 로 시뮬" / "같은 그림에 겹침" | 원문에 `hexacopter` **0회**(BiRa 대상은 Phantom 2 단독). HFSS/FEKO/CST 는 "상용 툴이 이런 걸 할 수 있다" 는 일반 서베이 문장. 캡션은 measured=상단/simulated=하단 **별개 서브플롯** | **세 서술 전부 삭제.** 정지/회전 분리 규약만 유지 |
| F3 | Zhang 2505.20673 을 "평균만 인용, 각도별 인용 금지" 의 표준으로 | **정반대다.** Zhang 은 σ=A·B1·B2 로 각도를 결정론 모형화하고 log-normal 은 잔차 B2(N(−0.52,2.31²) dB) | **3층 분해로 교체.** 우리 잔차 std 를 2.31 dB 와 병치 |
| F4 | Zhang M350 "대형 기체" → four-leaf 미재현 사유 | 원문: "approximate dimensions of **430 × 420 × 430 mm**" — 우리 mavic4pro(441)·matrice4e(438.8)와 같은 급 | **사유 철회.** 미재현의 진짜 원인은 지표 범주 오류(§K21) |
| F5 | Sagitta 2604.09243 "~2.5% = 입사방향들에 걸친 표준편차" | Fig.4 캡션은 곡선이 **이미** "averaged across incident directions" 라 명시. 2.5% 는 광학영역 **kr 스윕 전체**의 해석해 대비 산포 | 정의 정정 후 인용 |
| F6 | Ziganshin "i-MiEV 를 BiRa 2–18 GHz 실측과 대조" | 2–18 GHz 는 **설비 대역**, 실제 차량 대조는 **3 GHz 단일**, 정준 검증은 2 GHz | "설비 2–18 GHz / 대조 3 GHz" 분리 표기 |
| F7 | Di Seglio 5 dB "합성 레퍼런스가 실 신호와 어긋나 생기는 SNR 손실" | 원문 §3.1: "due to the corresponding reduction in the **coherent integration gain**"(적분길이 손실, Fig.4 는 **10–11 dB**). Fig.7 의 ≈5 dB 는 Strategy #1 대 Strategy #1 이라 **합성 레퍼런스가 개입조차 안 함** | **수치 인용 금지.** 관행 인용만 |
| F8 | Jopanya "PRS 를 별도 선례로 분리하는 것도 우리 캐비엇과 동일" | 원문 PRS 언급은 "the work in [2] investigates the positioning reference signal (PRS)" 한 줄뿐. **"PRS 는 상시가 아니다" 는 진술이 논문에 없다** | **삭제.** 우리 고유 주장으로 표기 |
| F9 | AoA 논문 2510.17342 "X410" / "(ICC Wkshp)" | 장비는 **USRP N310**(원문: "The N310 has no way of aligning the phase between channels"). 저자 Ceresoli 외(PoliMi), 제목 "AoA Services in 5G Networks" | 장비·서지 정정, "X410 이식은 스펙 확인 필요" 병기 |
| F10 | OpenISAC "USRP X400" / "다중 RX 채널" | Fig.9 프로토타입은 **Luowave USRP-LW X310 + Tiny B210**("X400 series" 는 지원 범위 언급). 노드당 감시 RX 는 단일 안테나 | 정정. 배열이득 선례로 사용 금지 |
| F11 | Wypich & Zielinski POD 24–32% → 77–78% | [W] 등급(PDF 전 디스크 부재). 우리 자체 노트(`pilot_findings.md` L174-177)에 **표적이 차량**, 5.8 GHz. 그들의 "풀 웨이브폼" 은 재구성 PDSCH 이지 NR-PRS 가 아님. 게다가 **반대 부호 실측**이 코퍼스에 있음(LTE_23: CRS-only 가 더 낫다) | **드론 선례표에서 제거.** 각주로 강등 + 표적 불일치 명시 |

### 16-2. 우리 자신의 숫자 오독 (9건)

| # | 주장 | 실제 | 처리 |
|---|---|---|---|
| G1 | "report3_rt.json 에 천장 −9.8 dB 가 없다(검증 미완)" | **두 군데 있다**: `S1_depth.sweeps[max_depth=1].paths[1]` = −9.822033 dB @12.971 ns (absorber_ceiling), `floor_ghost_verify.json A_static_floor.rt_taps[0] = [13.0, −9.8]` | gap 기각. §1 에 "최강 환경탭은 바닥이 아니다" 로 반영 |
| G2 | "sionna_sensing_survey.md 노트가 truncation 되어 미확인" | 완전한 문단이며 "표적을 향한 PO 표면산란적분(coherent RCS)·native RCS 계산 API 는 여전히 없다" 가 온전히 읽힌다 | 사유를 "2차 노트라서" 로 교체 |
| G3 | `verify_cfar.json` "07-16 낡음" | mtime **07-22 08:31** | 정정 |
| G4 | `detection_rx_sweep.json` "K=2000, mtime 07-20" | **K=6000, mtime 07-22 09:51** | 정정. 파생 D0·Re 전부 재계산 |
| G5 | `verify_ambiguity.json` "physical 블록이 빈 딕셔너리" | 6개 파형 전부 채워짐. `nr_G1`: prf_physical 50 Hz, v_unamb_phys 1.07069 m/s, **aliased=true** | gap 기각 |
| G6 | CRLB σ_rb "0.036 / 0.0144 / 0.0084 m" | **0.016235 / 0.012381 / 0.007303 m**(1RX pos_rms 도 66.75 → **57.752 m**, 2RX 0.219 → **0.18957 m**) | 전면 재파싱 |
| G7 | report12 배열이득 "5.78~6.65 dB" | **5.993(L2) ~ 6.798(W1) dB** — WiFi 3모드가 이론 상한 초과 | 정정 + 원인 규명 필요 |
| G8 | report10 Pfa 비 "G1 0.078 / L3 0.45" | (report12 §5 규약 재계산) **G1 0.1235 / L3 0.4782 / W1 0.7549 / G3 0.7729** | 정정 |
| G9 | report08 "flash 값이 단 2개" | **3개**(120.0: mavic4pro·s1000plus / 126.67: matrice4e / 183.33: mini5pro·phantom4). 다만 두 쌍이 충돌하므로 "식별자" 주장은 여전히 무효 | 정정하되 결론 유지 |

### 16-3. 미확인을 확인처럼 쓴 것 (6건)

| # | 항목 | 상태 | 처리 |
|---|---|---|---|
| H1 | 2603.28736 "EuCAP 2026 채택(peer-reviewed)" | 우리 `INDEX.md` 는 "claimed EuCAP 2026 (**unconfirmed by S2**)" 라 표기. arXiv abs 직접 조회로 사실 확인됨(comments: "Accepted for publication at the 2026 20th EuCAP") — **날조 아님, 그러나 확신의 출처가 없었다** | 확인 경로 명기 |
| H2 | "CORPUS 자산 지도가 report03 을 '직접 대응 선행 없음' 이라 명시" | 해당 문자열을 워크스페이스 + `/data/public/sionna_jeong` 전역 grep 한 결과 **0건**. 근거 파일이 실재하지 않음 | **삭제** 또는 실제 경로 제시 |
| H3 | `make_notebook03.py §4` "Ezuma/Semkin/Li&Ling 인용" | 그 파일에 `Semkin`·`Li`·`Ling` **0회**. 실제로는 "NCSU Ezuma·Güvenç" 와 "BUPT 3GPP unified RCS" 두 건 | 정정 |
| H4 | Li&Ling / Ezuma / Semkin / Quevedo / DTMB | **전 디스크에 PDF 없음.** `.md` 노트만 존재 → **[N] 등급 확정** | 인용마다 "노트 근거" 명시 |
| H5 | DTMB Mavic 3 | `refs/.../DTMB_*.md` 가 지목한 `drone_lit.jsonl` 은 **저장소가 아니라 세션 스크래치패드**(07-16)에 있다. 그 기록 자신이 "no blade-flash frequency in Hz…; **no dBsm RCS reported**" 라 적는다. 서지는 "DSP (Elsevier), March 2026, PII S1051200426002265" | **선행 목록에서 제거** 또는 "정량값 없음" 명시 |
| H6 | Jopanya arXiv:2504.02641 / Demissie IET RSN DOI 10.1049/rsn2.70092 / Doppler multistatic arXiv:2509.25732 / Malanowski IET RSN 8:153-159 (2014) | 전부 [W]. Jopanya PDF 에 찍힌 것은 **DOI 10.1109/SPAWC66079.2025.11143316** 이고 arXiv ID 는 `prior_work.json` 2차 출처. Demissie IET RSN 2025 판은 `pilot_findings.md` L263 이 "**paywalled, existence SOURCE only**" 라 명시 — 코퍼스에 있는 것은 2024 RadarConf 판이고 그쪽은 **Wiener 필터 + 참조셀 99% 경험분위수**를 쓴다(ECA→CAF→CFAR 아님) | **인용마다 "원문 미확인" 병기.** report10 §3 의 처리사슬 귀속은 읽은 2024 판으로 교체 |

### 16-4. 이번 조사 자체에서 발생한 오보 (1건)

| # | 주장 | 실제 |
|---|---|---|
| I1 | "report13 을 주제로 언급하는 파일은 `docs/RESUME_0722.md` 하나뿐이며 report13 은 미작성" | 노트북·JSON 이 없는 것은 맞으나 **`docs/REPORT13_DESIGN.md`(64 KB)·`docs/REPORT13_SPEC.md`(63 KB)** 가 2026-07-22 09:58 로 존재한다. SPEC 은 적대적 반증 4라운드를 전량 판정한 최종 구현 스펙이며, §13 의 여러 처방(자유공간 사다리 FS-0/1/3, SSB 50 Hz 물리 반복률, `equal_psd` 전력정규화)을 **이미 담고 있다** |

---

## 부록 — 이 문서가 읽은 우리 산출물 (전부 절대경로, 2026-07-23 실사)

| 파일 | mtime | 이 문서에서 쓴 키 |
|---|---|---|
| `/home/yunjung/workspace/sionna2/outputs/report1.json` | 07-22 06:12 | `chamber.dims/materials/groups`, `meshes.drones.*`, `microdoppler.drones.*` |
| `.../outputs/report2_waveform_rcs.json` | 07-22 06:39 | `rcs.drones.*.bands`, `reference.G{1,2,3}.*`, `crosscheck`, `numerology`, `sbr_validation`, `occlusion`, `materials` |
| `.../outputs/report3_rt.json` | 07-22 06:24 | `S1_depth`, `S2_floor`, `D_plate`, `E_sphere` |
| `.../outputs/report6_sbr.json` | 07-23 05:52 | `kernel`, `camera`, `prop_normals` (`compare` 는 빈 블록) |
| `.../outputs/floor_ghost_verify.json` | 07-22 06:02 | `A_static_floor`, `B_clutter_dead`, `CD_ghost` |
| `.../outputs/verify_ghost_impact.json` | 07-22 08:02 | `config`, `C_cfar`(81행), `D_tracker`, `E_mitigation` |
| `.../outputs/verify_cfar.json` | 07-22 08:31 | `meta`, `alpha_audit`, `white`, `chain.*.{noise,dpi_eca}.{op,wide}`, `whiteness` |
| `.../outputs/verify_eca.json` | 07-22 08:52 | `S4_target_loss` |
| `.../outputs/verify_ambiguity.json` | 07-22 07:15 | `waveforms.*.{dR_theory_m,dR_meas_m,dR_ratio,physical}` |
| `.../outputs/verify_linkbudget.json` | 07-22 05:49 | `config`, `A_radar_equation` |
| `.../outputs/verify_observability.json` | 07-22 09:49 | `summary`, `cells`, `fixes` |
| `.../outputs/detection_rx_sweep.json` | 07-22 09:51 | `meta`(K=6000), `modes.*.{snr_grid,curves,occupancy,ref_bw_mhz,range_res_m,pfa_nominal}` |
| `.../outputs/{real_cad,community,phantom4_scan}_compare.json` | 07-22 05:50~51 | `d_sigma_db`, `d_sigma_rms_db`, `d_area_db`, `bbox_*` |
| `.../report_mesh/outputs/mesh_verify.json` | 07-22 06:38 | `A_geometry.*.edge_vs_lam52`, `C_dims.*.checks.diagonal`, `I_sbr_subdiv` |
| `.../prior_work/outputs/prior_work.json` | — | `papers`(14편, grade), `measured_rcs_anchor` |

**이 문서는 `outputs/` 에 아무것도 쓰지 않았고 다른 파일을 수정하지 않았다.**
