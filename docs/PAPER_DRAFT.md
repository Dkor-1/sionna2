> ⚠ **2026-08-16 재편 전 번호 체계의 기록이다** — 옛 `report0N` 층 번호로 적혀 있다. 옛→새 환산은 [`RESTRUCT_PLAN.md`](RESTRUCT_PLAN.md) §1 표, 현행 편성은 [`REPORTS_VOLUMES.md`](REPORTS_VOLUMES.md).

# 논문 골격 — 한 자리에서 초고를 쓰기 위한 발판

> 이 문서는 **원고가 아니라 발판**이다. 절을 하나 고르면 그 절의 주장·근거·그림·수치·예상반론이
> 여기 다 있어서 노트북을 다시 열지 않고 쓴다.
> 기계 판독본은 [`outputs/paper_kit.json`](../outputs/paper_kit.json) 이고 이 문서와 같은 소스에서 나온다.
> 계약 둘: [`PAPER_SPEC.md`](PAPER_SPEC.md) (무엇을 주장하는가) · [`REBUILD_2026-07-30.md`](REBUILD_2026-07-30.md) §5 (어떻게 쓰는가).

```
┌─ 한 일 ─────────────────────────────────────────────────────────────────────┐
│ 리포트 6편에서 논문 부품을 전부 뽑아 절별 골격 · 방어선 통합표 · 그림 목록 ·   │
│ 인용 목록 · 비용순 공백 목록 · 좁히기 기록으로 재조립했다.                     │
├─ 결과 ──────────────────────────────────────────────────────────────────────┤
│ 주장 7 · 방어선 50행 · 방법 문단 6 · 인용 31건 · 그림 38장 · 출처 붙은 수치     │
│   571개를 절 단위로 배치했다 ⟨outputs/paper_kit.json : meta.totals⟩.          │
│ 절 7개 중 6개는 공급 노트북이 있고, III-C(법칙)만 아직 없다 — 그 절의 수치는    │
│   `refrate_law.json` · `vmax_hardening.json` 에 있고 노트북 밖에 있다.        │
│ 그림 35장이 벡터본을 갖고, 2단 폭 7.16 in 배치에서 29장이 8 pt 문턱을 넘는다.   │
│ 공백 12건을 비용순으로 값매겼다 — 상위 5건 합계가 GPU 0 · 벤치 4시간이다.      │
├─ 방법 ──────────────────────────────────────────────────────────────────────┤
│ `paper_kit.extract_paper_kit()` 로 노트북 6편을 긁고, 그림은 저장된 PDF 를     │
│ `check_figure(placed_width_in=…)` 로 두 조판폭에서 다시 재고, 수치는 전부      │
│ JSON 키로 되짚었다. 이 문서의 숫자 중 손으로 친 것은 없다.                     │
├─ 재현 ──────────────────────────────────────────────────────────────────────┤
│ cd /workspace/sionna                                          │
│ PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python -c \                     │
│   "import paper_kit as pk; d=pk.extract_paper_kit(); print(pk.coverage_report(d))"
│ → outputs/paper_kit.json (0.9 MB · 3 s)                                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 0. ⭐ 논문 좌표 — 제목이 07-31 에 바뀌었다

**판정: [`PAPER_SPEC.md`](PAPER_SPEC.md) §1 을 정본으로 삼는다.** 두 계약 중 그것이 최신이고,
`PAPER_POSITION.md` §1 1행이 옛 헤드라인(3자 순위)을 이미 `drop` 으로 판정했다.

| | 옛 좌표 (07-30) | **정본 (07-31)** |
|---|---|---|
| 제목 | Controlled Comparison of WiFi / LTE / 5G NR Illuminators… | **The Ambient Reference Repetition Rate Sets Drone Velocity Observability in Passive Bistatic Sensing** |
| 한 문장 기여 | 세 파형을 교정된 Pfa 위에서 통제 비교한다 | **`v_max = λ·PRF_ref/4`** — 규격이 상시를 보장하는 하향 기준신호 중 드론 속도대를 덮는 것은 LTE CRS 하나다 |
| σ 의존 | 순위가 밴드별 차분 σ 를 탄다 | **σ 가 유도 사슬에 없다** ⟨`outputs/refrate_law.json : law.what_does_not_enter.sigma`⟩ |
| 세 파형 비교의 지위 | 헤드라인 | **정량화 계층** — 법칙이 검출로 얼마가 되는지를 재는 자리 |

**아직 반영되지 않은 곳 셋** (→ §5 공백 G1·G2·G3):

| 어디 | 상태 |
|---|---|
| `src/paper_kit.py:100` `PAPER_TITLE` | 옛 제목. `outputs/paper_kit.json : meta.paper_title` 이 그것을 그대로 싣는다 |
| `report03_illuminators.ipynb` | 법칙을 안 싣는다 — `refrate_law.json` 참조 0건 |
| `report05_results.ipynb` | 철회 대상 두 키가 살아 있다 — `r90.coverage_ceiling_by_mode.5G = 0.0` · `r90.blind_heading_frac_by_mode.5G = 1.0` ⟨`outputs/report05_derived.json`⟩ |

### 0.1 절 번호 — 세 체계를 하나로 묶는다

| 논문 절 (이 문서) | `paper_kit.json` 키 | 공급 노트북 | PAPER_SPEC §4 표기 |
|---|---|---|---|
| I. Introduction | `I. Introduction` | `report01_prior` | I |
| II. Related Work | `II. Related Work` | `report01_prior` | II |
| III-A. Target Model | `III-A. Target Model` | `report02_target` | III-A |
| III-B. Illuminators | `III-B. Illuminators` | `report03_illuminators` | III-B |
| **III-C. The Repetition-Rate Law** | **없음** | **없음** | IV. The Law |
| IV. Detection Chain | `IV. Detection Chain` | `report04_detector` | V |
| V. Results | `V. Results` | `report05_results` | VI |
| VI. Validation | `VI. Validation` | `report06_measurement` | VII |
| VII. Conclusion | — | — | — |

법칙을 독립 절(PAPER_SPEC 의 `IV. The Law`)로 올릴지 III-C 로 둘지는 지면이 정한다 — ICASSP 4쪽이면
III-C 가 맞고, 저널 8쪽이면 독립 절이 맞다. 두 경우 모두 공급물은 같다.

---

## 1. 절별 골격

각 절 블록의 읽는 법: **주장 → 공급처 → 그림/표 → 수치(키 포함) → 인용**.
수치는 `값 ⟨JSON : 키⟩` 형태이고, 원고에 옮길 때 그 키로 다시 확인한다.

### I. Introduction

**주장** — 드론 표면메쉬의 산란 진폭을 Sionna 급 광선엔진 안에서 계산해 검증한 게재 논문은
0편이고, 우리 기여는 그 엔진과 파이프라인 통합, 그리고 그 위에 세운 교정된 파형 비교다
⟨`paper_kit.json : sections["I. Introduction"].claims[0]`⟩.
⚠ 이 문장은 **Q1·Q2 를 반드시 데리고 다닌다** (§2 방어선 D02·D03, `paper_kit._H8_TRIGGER` 가 강제).

**공급처** `report01_prior` §2 · §3 · §4.1 · §4.1.1(영문 신규성 문단, 붙여넣기용)

**그림** F1 `report01_p1_funnel.pdf` · F4 `report01_p4_prongs.pdf`

**수치**

| 값 | 출처 키 |
|---|---|
| 전문 판정 문서 21건 (저작 19편) | `report01_paper.json : corpus.documents` · `corpus.distinct_works` |
| 게재 11편 · 프리프린트 10편 | `prior_work_survey.json : counts.published` · `counts.preprint` |
| 축자 인용 46건 (빌드가 PDF 쪽에서 재확인) | `prior_work_survey.json : counts.quotes_verified` |
| H8 후보 12편 · 4관문 동시통과 0편 | `report01_paper.json : h8.n_adjudicated` · `h8.n_passing_all_prongs` |
| 절대 σ 를 dBsm 으로 찍는 편 6편, 그중 광선엔진 구동 1편(표적=차량) | `prior_work_survey.json : counts.prints_dbsm` · `counts.prints_dbsm_and_runs_engine` |
| `CFAR` 와 `false alarm` 이 둘 다 0회인 논문 14편 | `prior_work_survey.json : counts.zero_cfar_and_false_alarm` |
| Sionna RT 기술보고서의 `SBR` 출현 44회 (v1.2 전문) | `prior_work_survey.json : engine.technical_report.term_counts.sbr` |

### II. Related Work

**주장** — 표적 서명의 조달처는 일곱 갈래이고, 고른 갈래가 그 편이 낼 수 있는 주장의 크기를 정한다.

**공급처** `report01_prior` §3(갈래별 원장, 한 행 = 한 편) · §4.1(4관문 판정표)

**그림** F2 `report01_p2_routes.pdf` · F3 `report01_p3_dbsm.pdf`

**표** §3 route ledger — `논문 | 상태 | 조달처 | 그 편이 산 주장` + `게재` 열
⟨`report01_paper.json : route_status`⟩. 논문 II 절 표의 원형이다.

**법칙 쪽 선행 3편** (아래 §4 인용목록 [32]~[34], **아직 `cite()` 블록이 없다** → §5 공백 G4)

| 하지 않는 주장 | 선행 | 우리 위치 |
|---|---|---|
| "SSB 반복률이 속도 모호를 만든다는 것을 처음 지적했다" | Abratkiewicz 외, *IEEE JSTARS* 16:3469–3484, 2023 | 법칙 자체에 선행이 있다 ⟨`refrate_law.json : novelty_guard[0]`⟩ |
| "무모호 속도 공식이 새롭다" | Jopanya & Osorio, arXiv:2504.02641 — 한계가 `\|v_u\| ≤ λ·SCS/2`, **버스트 내부** 축 | 같은 신호의 **다른 축**. 교환관계를 함께 적는 것이 기여의 일부 ⟨`refrate_law.json : novelty_guard[1]`⟩ |
| "도플러 모호가 패시브에서 새 문제다" | *FITEE*, DOI 10.1631/FITEE.2000143 (LTE 내부) | 표준 **사이**의 선택 기준으로 올린다 ⟨`refrate_law.json : novelty_guard[2]`⟩ |

### III-A. Target Model

**주장** — 표적 σ 는 부품별 재질 메쉬 위에서 광선으로 조명면을 가려낸 뒤 PO 면적분으로 계산하고,
절대 레벨은 그 계산 출력으로 두되 **주파수 기울기만** 측정 앵커에 맞춘다.
⭐ 편 머리에 한 줄: **이 절의 산출물은 검출 계층(V)에만 들어간다.**

**공급처** `report02_target` §1(메쉬) · §2(재질·가림) · §3.1(커널 검증) · §4(앵커) · §5(σ 민감도)

**그림** F5 `report02_f5_reference_gap.pdf` · F6 `report02_f6_band_slope.pdf` ·
F7 `report02_f7_sigma_sensitivity.pdf` · (부) `report02_f2_mesh_photo.pdf`

**수치**

| 값 | 출처 키 |
|---|---|
| 기체 7종 · 부품 219개 · 삼각형 207,010개 | `report02_derived.json : mesh.n` · `mesh.n_parts_total` · `mesh.n_tris_total` |
| 전기적 크기 kr 8.4 ~ 79.7 | `report02_derived.json : electrical.kr_min` · `electrical.kr_max` |
| 도전성 재질이 면적 45.3 % · Σ\|Γ\|A 의 73.5 % | `report02_derived.json : material.conducting_area_pct` · `material.conducting_gamma_pct` |
| 가림이 방위평균 σ 를 0.11 ~ 6.63 dB 옮긴다 | `report02_derived.json : occlusion.min_db` · `occlusion.max_db` |
| 이산화 잡음 바닥 최대 0.071 dB · 7기체 전부 그 위 | `report02_derived.json : occlusion.floor_max_db` · `occlusion.n_above_floor` |
| **커널 대 해석 PO: 최대 0.201 dB** (kr 1~100 · 21점 · 입사 48방향) | `sbr_kr_sweep.json : summary_div16.max_abs_db_vs_po` · `meta.n_incidence` |
| 다중반사 위상 대 PEC 이면각 해석해: 최대 0.556 dB | `sbr_defect_fixes.json : d3_multibounce_phase.max_abs_err_db` |
| 앵커 기울기 0.210 dB/GHz · 평균 레벨이동 0.00 dB · 각도패턴 이동 1.9e-15 dB | `rcs_anchor.json : literature.mu_eps.multiband_phantom3.mu_a` · `report02_derived.json : anchor_modes.level_shift_abs_max_db` · `anchor.shape_invariance_max_abs_db` |
| 사진 실루엣 IoU 0.478 ~ 0.875 (자기복제 상한의 50 ~ 91 %) | `report02_derived.json : photo.worst_iou` · `photo.best_iou` · `photo.worst_pct` · `photo.best_pct` |

⚠ Mie 와 해석 PO 는 **기준해**다. 매번 그렇게 이름 붙인다.

### III-B. Illuminators

**주장** — 세 조명원을 가르는 양(점유 대가 · 반송파 λ² · 기준신호 대역이 정하는 `ΔR_b = c/B_ref`)은
같은 표적·같은 기하에서 잰 두 양의 비이거나 규격이 고정한 상수이고, **표적 σ 는 분자와 분모에
함께 들어가 상쇄된다.**

**공급처** `report03_illuminators` §1(파형표) · §2(대가 원장) · §2.1(전제) · §3.1(Sionna 대조) · §4.3

**그림** F8 `report03_f4_ledger.pdf` · F9 `report03_f2_reference.pdf` ·
(부) `report03_f1_grid.pdf` · `report03_f3_occupancy.pdf` · `report03_f5_crosscheck.pdf`

**수치**

| 값 | 출처 키 |
|---|---|
| 기준신호 대역 — LTE CRS 17.98 MHz · WiFi VHT-LTF 76.56 MHz · 5G SSB 7.20 MHz | `report2_waveform_rcs.json : reference.G1.{lte,wifi,nr}.ref_bw_mhz` |
| ΔR_b — 5G 41.6 m 대 LTE 16.7 m (2.5배) | `report2_waveform_rcs.json : reference.G1.{nr,lte}.dR_m` · `report03_illuminators.json : ratios.drb_nr_over_lte` |
| 5G 채널대역이 줄 값 3.05 m (풀캡처 체제) | `report2_waveform_rcs.json : reference.G1.nr.chan_dR_m` |
| **점유 대가 18 dB**, 구간 [12, 24] dB, Pd 보간 16.4 dB, 격자 눈금 6 dB, 시행 60회 | `report03_illuminators.json : occupancy_cost.{value_db,bracket_lo_db,bracket_hi_db,interp_db,eirp_grid_step_db,n_trials}` |
| λ² — LTE→5G −5.57 dB · LTE→WiFi −9.03 dB (밴드 양끝 스팬 −9.03 dB) | `report03_illuminators.json : lambda2.{lte_to_nr_db,lte_to_wifi_db,span_db}` |
| WiFi 패킷 듀티 −12.84 dB · CPI 규약 3.01 dB | `report4_fixups.json : F4_linkbudget.wifi_pilot_fraction.packet_duty_db` · `cpi_asymmetry.span_db` |
| Sionna PHY 대조: 상관 1.0000 · NMSE −135.2 dB (CP 규칙 제거 대조군에서 0.05 로 붕괴) | `report2_waveform_rcs.json : crosscheck.nr.{corr,nmse_db,corr_bug}` |
| 모호함수 대 검출기 거리도플러: 최대 0.144 dB (6경우 · −45 dB 이상 셀) | `report03_illuminators.json : detector_af_max_err_db.{value,n_cases}` |

⚠ λ² 항은 **EIRP 고정 · 수신 안테나 이득 고정** 전제에서 선다 (`src/freespace_link.py:371`).
그 전제 한 줄을 §III-B 본문에 적는다.

### III-C. The Repetition-Rate Law ⭐

**주장** — 패시브 수신기 한 대가 모호 없이 잴 수 있는 표적 반경속도는 상시 기준신호의 반복률과
반송파가 정한다: `v_max = λ·PRF_ref/4`. 규격이 상시를 보장하는 하향 기준신호 중 드론 속도대
(5~20 m/s)를 덮는 것은 **LTE CRS 하나뿐**이다.

**공급처 — 노트북 없음.** 수치는 `outputs/refrate_law.json`(`benchmark/refrate_law.py`, 4.5 s)과
`outputs/vmax_hardening.json`(`benchmark/vmax_hardening.py`, 11.4 s)에 있다 → §5 공백 G2.

**그림** F10 `refrate_law_f1_ranking.pdf` · F11 `refrate_law_f2_law.pdf` ·
F12 `refrate_law_f3_matrix.pdf` · F13 `refrate_law_f4_design_rule.pdf` (네 장 모두 조판 규격 미달 → §3)

**헤드라인 표** ⟨`refrate_law.json : illuminators.rows.*`⟩

| 상시 기준신호 | PRF_ref [Hz] | v_max [m/s] | 드론 5~20 m/s |
|---|---:|---:|---|
| LTE CRS (서브프레임당) | 1000.0 | **40.67** | 덮는다 |
| WiFi VHT-LTF (트래픽 1 kHz 가정) | 1000.0 | 14.39 | 부분 |
| 5G NR SSB (기본 20 ms) | 50.0 | **1.07** | 못 덮는다 |
| WiFi 비콘 (유휴 AP · 100 TU) | 9.766 | **0.14** | 못 덮는다 |

**나머지 수치**

| 값 | 출처 키 |
|---|---|
| 상시·고정반복 조명원 **12종**, v_max 스팬 0.14 ~ 202.6 m/s (1442배) | `refrate_law.json : illuminators.ranking_ambient_fixed_prf` (길이 12) · `illuminators.headline.span` |
| 최악은 5G 가 아니라 **유휴 WiFi 비콘** | `refrate_law.json : illuminators.headline.worst_ambient_fixed` |
| LTE→5G 마이그레이션: v_max 38.0배 감소 = 반복률 20.0배 × 파장 1.90배 | `refrate_law.json : design_rule.lte_to_5g_migration.{v_max_ratio,prf_ratio,lambda_ratio}` |
| 닫힌형 검증: 저장소 기하 함수 대비 상대오차 5.87e-07 | `refrate_law.json : law.verification.V1_geometry_factor.max_rel_err` |
| 버스트 내부 축과의 교환관계: 무모호 1284.8 m/s ↔ 분해능 300.1 m/s (버스트 간 1.07 ↔ 0.43 m/s) | `refrate_law.json : scope.intra_burst_alternative.{intra_burst,inter_burst}` |
| 설정 의존: SSB 주기 {5,10,20,40,80,160} ms → v_max 4.283 ~ 0.134 m/s (5 ms 에서도 5 m/s 미달) | `vmax_hardening.json : verdict.configuration_dependence.v_max_by_ssb_period` |
| 완화계수 G (β ≤ 90°): 중앙값 1.011 · 최대 1.451 → `λ·PRF/4` 는 **하한** | `vmax_hardening.json : A_formula.relief_factor_G.beta_le_90_only` |

**탈출구 여섯의 판정** ⟨`vmax_hardening.json : verdict.escapes`⟩ — 본문의 절반이다.

| 탈출구 | 구제하나 | 한 줄 |
|---|---|---|
| (a) 언폴딩·스태거 | 아니다 | 패시브는 스태거를 못 만든다. 송신기가 준 비균일에서 알리아스 억압 0.10 dB (판정 문턱 10 dB) |
| (b) 프레임의 나머지 | 아니다 | 상시인 것은 SIB1/CORESET#0 뿐이고 같은 20 ms 창에 묶인다. Rel-17 유휴 TRS 최선의 셀도 100 Hz = 2.14 m/s |
| (c) 빔 스위핑 | 아니다 | 등이득·동위상 상한을 줘도 버스트 개구가 50 Hz 알리아스를 0.14 dB 만 누른다 |
| (d) 긴 CPI·모션보상 | **부분** | 검출 블라인드는 되살린다(0.733→0.064). alias_frac 은 0.858 고정 |
| (e) 멀티스태틱 | **부분** | 모호 부피 1.01e-01(N=1) → 1.55e-04(N=4). 도플러 1빈 오차에서 2.68e-02 로 되돌아가고 유령 192개 |
| (f) 밴드·반송파집성 | **부분** | λ 는 6.25배(n28)에서 멈춘다. CA-CRT 는 두 프론트엔드를 요구한다 |

### IV. Detection Chain

**주장** — 세 파형의 CFAR 문턱을 GPU 몬테카를로로 측정한 **경험 오경보율**에 맞춰 교정해,
세 조명원이 같은 실제 오경보율 위에서 비교되게 했다.
⭐ Pfa 통제는 통제 시뮬만 할 수 있는 일이다.

**공급처** `report04_detector` §1(사슬) · §2(ECA) · §3(교정표) · §4(관측성)

**그림** F14 `report04_f4_pfa.pdf` · F15 `report04_f5_cause.pdf` ·
(부) `report04_f1_chain.pdf` · `report04_f2_eca_depth.pdf` · `report04_f3_eca_notch.pdf`

**수치**

| 값 | 출처 키 |
|---|---|
| **GPU 몬테카를로 2717 s** · 파형·모드당 거리도플러 맵 10,000장 | `verify_cfar.json : meta.runtime_s` · `meta.n_maps_chain` |
| CFAR 눈금 확정: 백색 맵 500,000장(셀 5.64e8)에서 경험/명목 = 0.997 | `verify_cfar.json : meta.n_maps_white` · `white.48x24.rows[89].ratio` |
| 문턱 상수 대 이론식 상대오차 7.6e-16 | `verify_cfar.json : alpha_audit.g2x2_t6x6.rel_err` |
| **밴드별 배율 — WiFi 1.53 · LTE 2.66 · 5G 1.52** (명목 1e−04) | `verify_cfar.json : chain.{WiFi80,LTE20,NR100}.dpi_eca.op.rows[89].ratio` |
| 교정된 명목값 — WiFi 6.27e−05 · LTE 2.90e−05 · 5G 6.46e−05 | `verify_cfar.json : chain.*.dpi_eca.calib_op_mask1.points[2].pfa_nominal_needed` |
| 원인 규명 대조군 — rect 창 0.96 · 백색화 정합필터 1.02 | `verify_cfar.json : control_rect_window_NR100.op.rows[89].ratio` · `control_whitened_mf_rect_NR100.op.rows[89].ratio` |
| 형상 의존 — 운용 창 1.52배 대 넓은 창(256빈) 47.70배 | `verify_cfar.json : chain.NR100.dpi_eca.wide.rows[89].ratio` |
| ECA 소거 깊이 바닥 — 직접파만 232.3 dB ↔ 측정 다중경로 56.1 dB | `verify_eca.json : S1_depth_vs_taps[0].rows[12].{depth_dpi_db,depth_full_db}` |
| ECA 노치 3 dB 지점 f_d/Δf_d = 0.596, 속도 문턱 WiFi 0.39 · LTE 1.10 · 5G 1.16 m/s | `verify_eca.json : S4_target_loss[*].{fd_3db_over_dfd,v_3db_ms}` |
| 관측성 — 1쌍 FIM 랭크 2 → 2Rx 랭크 6 · 위치 RMS 0.19 m | `verify_observability.json : summary.{snapshot_fim_rank,fix_2rx_rank,fix_2rx_pos_rms_m}` |
| 문헌 대조 — census 16편 중 CFAR·false alarm 둘 다 0회 13편 | `prior_census.json : counts.zero_cfar_and_falsealarm` |

**측정 구간**: 명목 1e−06 ~ 1e−02 ⟨`verify_cfar.json : meta.pfa_nominal`⟩. 그 밖은 외삽으로 표시한다.

### V. Results

⭐ **이 절은 이 표만으로 쓸 수 있다.** 아래 값은 전부 키가 붙어 있고 노트북을 열 필요가 없다.

**주장 3개**

| # | 주장 | 근거 키 |
|---|---|---|
| V1 | 밴드 간 출력 SNR 차이를 만드는 항은 λ² 와 σ 둘뿐이다 | `report05_derived.json : gap_1km.by_pair` |
| V2 | 자세평균 σ + 측정 기울기에서 다섯 기체가 **하나의 순위**에 합의하고, 그 순위는 공통모드 σ 오차 ±10 dB 에서 불변이다 | `sigma_sensitivity.json : aspect_averaged.all_drones_agree` · `common_mode.order_invariant_everywhere` |
| V3 | 5G 상시 기준의 대가는 **CPI 스윕**이고 접힘과 블라인드는 다른 양이다 | `cpi_guard_sweep.json : equal_cpi_penalty` · `vmax_hardening.json : E_long_cpi` |

**그림** F16 `report05_pf2_ranking.pdf` · F17 `report05_pf3_robust.pdf` · F18 `report05_pf4_cpi.pdf` ·
(부) `report05_pf1_gap.pdf` · `report05_pf6_detector.pdf` · `report05_pf5_multirx.pdf`

**표 V-1 · 밴드 격차 분해 (1 km · Mavic 4 Pro)**

| 양 | 값 | 출처 키 |
|---|---:|---|
| WiFi−LTE 총격차 | +3.54 dB | `report05_derived.json : gap_1km.by_pair.W1-L1.d_total` |
| 그중 λ² | −9.03 dB | `report05_derived.json : gap_1km.by_pair.W1-L1.d_lambda2` |
| 그중 σ | +12.57 dB | `report05_derived.json : gap_1km.by_pair.W1-L1.d_sigma` |
| σ 항이 더 큰 밴드쌍 | 15쌍 중 9쌍 | `sigma_sensitivity.json : gap_decomposition.n_pairs_sigma_dominates` |

**표 V-2 · 순위와 그 강건성**

| 양 | 값 | 출처 키 |
|---|---:|---|
| 자세평균 합의 순위 | **LTE > 5G > WiFi** | `report05_derived.json : ranking.consensus_order_aspect_avg` |
| 단일자세에서 나오는 서로 다른 순위 수 | 3 | `sigma_sensitivity.json : ranking_consensus.single_aspect_n_distinct` |
| 자세평균에서 나오는 순위 수 | 1 | `sigma_sensitivity.json : ranking_consensus.aspect_avg_n_distinct` |
| 공통모드 ±10 dB 순위 불변 | 15/15 셀 (true) | `sigma_sensitivity.json : common_mode.order_invariant_everywhere` |
| 공통모드 기울기 dB(거리)/dB(σ) | 0.2227 ~ 0.2561 | `sigma_sensitivity.json : common_mode.slope_min` · `slope_max` |
| 공통모드 ±10 dB 의 절대거리 이동 | −43.31 % / +76.39 % | `sigma_sensitivity.json : common_mode.abs_range_shift_at_10db_pct` |
| 밴드별 차분 뒤집힘 문턱 (자세평균+앵커) | 3.72 dB | `sigma_sensitivity.json : configurations.by_config.aspect_avg_anchored.worst_flip_span_db` |
| 현실 차분오차 봉투 | 5.01 dB | `sigma_sensitivity.json : _meta.realistic_differential_span_db` |

**표 V-3 · 접힘과 블라인드는 다른 양이다 (5G G1)**

| 양 | 정의 | @0.1 s | @1.0 s | CPI 의존 | 출처 키 |
|---|---|---:|---:|---|---|
| `blind_hard` | `\|f_d,folded\| < 1.5·Δf_d` (검출 불가) | 0.733 | 0.064 | **있다** | `vmax_hardening.json : E_long_cpi.E1_blindness_falls_with_cpi.G1` |
| `alias_frac` | `\|f_d\| ≥ PRF/2` (속도 못 믿음) | 0.858 | 0.858 | **없다** | 같음 |

⚠ 같은 규약이 d=6301 m 에서 0.636, d=1000 m 에서 0.733 을 낸다. 점근식 `2g/M` 과 산포를 함께 쓴다.

**표 V-4 · 같은 CPI 에서의 블라인드 비율 (CPI 0.1 s)**

| 모드 | blind_hard | 출처 키 |
|---|---:|---|
| WiFi (W1) | 0.0528 | `cpi_guard_sweep.json : equal_cpi_penalty[0].blind_hard_W1` |
| LTE (L1) | 0.1583 | `…blind_hard_L1` |
| 5G (G1) | 0.6361 | `…blind_hard_G1` |
| 배수 G1/W1 | 12.05 | `…ratio_G1_over_W1` |

⚠ 12.05배는 **WiFi 패킷률 1000 Hz 가정 위에서만** 성립한다 ⟨`vmax_hardening.json : H_symmetry`⟩.
조건절과 함께만 쓴다 (§2 방어선 D01).

**표 V-5 · ⭐ 새 헤드라인 통계 — 검출가능 ∧ 무모호 헤딩 비율 (CPI 1.0 s · v = 15 m/s)**

| 모드 | 검출가능 | 무모호 | **둘 다** | 출처 키 |
|---|---:|---:|---:|---|
| WiFi | 0.9972 | 0.9083 | **0.9056** | `vmax_hardening.json : E_long_cpi.E5_usable_heading_fraction.W1_T1.by_speed[v=15]` |
| LTE | 0.9972 | 1.0000 | **0.9972** | `…L1_T1…` |
| 5G | 0.9528 | 0.0472 | **0.0444** | `…G1_T1…` |

이 표가 철회되는 "커버리지 0" 자리를 대신한다 — **긴 CPI 로도 안 회복되는 것**을 같은 표가 보여준다.

**표 V-6 · 전 헤딩 블라인드는 LTE 에서도 일어난다**

| 값 | 출처 키 |
|---|---|
| LTE 도 blind_hard = 1.000 이 CPI ≤ 0.0244 s 에서 성립 | `cpi_guard_sweep.json : structural.two_mechanisms.observed.L1.hard.T_max_total_blind_s` |
| 선언 규약이면 CPI ≤ 0.0393 s | `…observed.L1.declared.T_max_total_blind_s` |
| 기구 둘 — A 표본화(guard ≥ PRF/2) · B 진폭(guard ≥ max\|f_d\|) | `cpi_guard_sweep.json : structural.two_mechanisms` |

**표 V-7 · 다중 수신소자**

| 값 | 출처 키 |
|---|---|
| 측정 이득이 이상적 상한 10log₁₀N 대비 −0.11 ~ +0.47 dB | `report05_derived.json : rx_gain.excess_min_db` · `rx_gain.excess_max_db` |
| 기하·규약 게이트 12건 전부 통과 (실패 0) | `verify_freespace.json : summary.n_ran` · `summary.n_fail` |

### VI. Validation

**주장** — X410 야외 캠페인은 검출 사슬과 세 파형의 상대순위를 결판내며, 그 판정에 필요한 진폭
재현성을 세션 드리프트 예산 1.00 dB 로 확보한다(뒤집힘 폭 1.30 dB 아래).

**공급처** `report06_measurement` §2(세션 설계) · §3(판정 문턱) · §4(결정표)

**그림** F19 `report06_calibration.pdf` · F20 `report06_slope.pdf` · F21 `report06_size_law.pdf` ·
(부) `report06_farfield.pdf` · `report06_ground_bounce.pdf` · `report06_adc_headroom.pdf`

**수치**

| 값 | 출처 키 |
|---|---|
| 순위 뒤집힘 폭 최소 1.30 dB · 드리프트 예산 1.00 dB · 여유 +0.30 dB | `report06_derived.json : ranking_validation.{flip_span_min_db,drift_budget_db,drift_margin_db}` |
| 넓은 쪽 기체(Mini 5 Pro) 뒤집힘 폭 2.95 dB | `report06_derived.json : ranking_validation.flip_span_db.mini5pro` |
| 원거리장 최대 24.44 m · 점표적 서브밴드 200 MHz · 방위 표본 1.38° | `report06_derived.json : farfield_adopted.R_ff_max_m` · `point_target_max_bw_MHz` · `aspect_finest_deg` |
| D 정의 교체 시 요구거리 3.65배 스팬 | `report06_derived.json : farfield_adopted.spread_ratio_max` |
| 교정구 r = 17.8 cm · 예상 σ 대비 최소 +3.73 dB | `report06_derived.json : calibration_pick.radius_cm` · `calibration_margin_min_db` |
| 기울기 판정 문턱 = 세션간 재현성 2.44 dB | `report06_derived.json : slope.gap_db_min` |
| 크기법칙 판정 = 두 기체 차등신호 4.06 dB 의 부호 | `report06_derived.json : size_law.differential_db` |
| 12-bit ADC 동적범위 74.01 dB · 최소 여유 19.2 dB | `report06_measurement.json : hw.dynamic_range_db` · `adc.headroom_db_min` |

⚠ **1순위 실험을 E-ALIAS 로 교체한다** (PAPER_SPEC §2.3) — 상용 셀의 SSB 주기 분포를 우리가 재지
않았고, 그것이 §III-C 의 가장 날카로운 공격이다 → §5 공백 G8.

### VII. Conclusion

**쓸 것 넷** — 전부 앞 절의 수치를 되받는다.

| # | 문장의 뼈대 | 되받는 곳 |
|---|---|---|
| 1 | 상시 기준신호의 반복률이 패시브 드론 속도 관측성을 정하고, 규격이 상시를 보장하는 하향 기준 중 드론 속도대를 덮는 것은 LTE CRS 하나다 | III-C |
| 2 | 탈출구 여섯 중 셋은 닫히고 셋은 부분 완화이며, 완화의 크기를 각각 수치로 닫았다 | III-C 탈출구표 |
| 3 | 설계 규칙 — `PRF_req = 4v/λ` · `T_ref,max = λ/4v` · `f_c,max = c·PRF/4v` | `refrate_law.json : design_rule` |
| 4 | 다음 단계는 상용 셀 SSB 주기 분포의 실측(E-ALIAS)이다 | VI · §5 G8 |

⭐ 결론은 σ 없이 닫힌다. 헤드라인이 σ 와 무관하다는 것이 이 논문의 설계 논증이다.

---

## 2. 방어선 통합표 — 반박당하기 전에 쓴 반박문

50행 전부가 `paper_kit.json : sections[*].defence` 에 원문으로 있다. 아래는 **위험순**이고,
위험은 두 가지로 잰다 — ⑴ 헤드라인에 닿는가 ⑵ **우리 자신의 JSON 이 그 공격을 지지하는가**.

### R1 — 우리 JSON 이 공격 쪽에 서 있다 (여기서 지면 논문이 진다)

| # | 절 | 공격 | 답 |
|---|---|---|---|
| D01 | III-C | "WiFi 1000 Hz 는 트래픽 가정이다. 규격 보장 상시로 통일하면 WiFi 가 5G 보다 나쁘다" | 그렇다 — 비콘 9.77 Hz 에서 WiFi v_max = 0.140 m/s 로 5G(1.07)보다 나쁘다. 교차 패킷률 74.4 Hz. **법칙은 파형 이름이 아니라 λ·PRF 곱에 대한 진술**이고, 12종 표의 최악이 유휴 WiFi 비콘이라는 행이 그것을 증명한다 ⟨`vmax_hardening.json : H_symmetry`⟩ |
| D02 | I·II | "Rzewuski 외(NATO STO 2021)가 Parrot AR.Drone 의 모노·바이스태틱 RCS 를 FDTD 로 내고 50 m OTA 검출로 닫았다 — 같은 산출물이다" | 같은 산출물을 다른 엔진으로 낸다고 그대로 적는다. 그 편은 P3(엔진)에서만 걸린다. 우리가 더하는 것은 광선엔진 안의 부품별 재질 PO · 교정된 Pfa 위의 통제 비교 · σ 오차 아래 순위 강건성의 수치화다 ⟨`report01_paper.json : h8.scorecard`⟩ |
| D03 | I·II | "프리프린트를 넣으면 사실상 선행이 있는 것 아닌가" | LAMBDA 는 σ 를 CADFEKO 에서 받아 광선경로에 주입하고, Ziganshin 저널판은 차량을 푼다. 두 칸을 한 편에서 채우는 자리가 우리 자리다 ⟨`prior_settled_h8.json : H8.mandatory_qualification_2.text`⟩ |
| D04 | V | "현실 차분오차 봉투 5.01 dB 가 뒤집힘 문턱 3.72 dB 보다 크다" | 순위를 **기체별 문턱과 함께** 싣는다. 다섯 중 둘이 봉투 안에 들어가고, 몬테카를로 순위보존 확률이 같은 순서를 준다 ⟨`sigma_sensitivity.json : monte_carlo_per_band_error`⟩ |
| D05 | V | "단일 자세에서는 기체마다 순위가 달랐다 — 어느 쪽이 결론인가" | 결론은 자세평균 설정의 순위다. 단일자세는 3가지를 내고, 그 차이를 만드는 것이 자세별 로브 구조임을 같은 표가 보여준다 ⟨`sigma_sensitivity.json : ranking_consensus.single_aspect_n_distinct`⟩ |
| D06 | V | "CPI 0.1 s 한 점에서 커버리지 0 이라 적은 결과는 규약이 만든 인공물이다" | 그 점은 2.5빈 **선언**가드에서만 성립한다. 검출기 정본 1.5빈에서 같은 CPI 가 0.636, CPI 0.2 s 가 0.303 이다. 배수 12.05 는 CPI 전 구간에 남으므로 **스윕으로** 싣는다 ⟨`cpi_guard_sweep.json : verdict.artifact`⟩ |
| D07 | III-B | "점유 18 dB 는 EIRP 격자에서 읽은 값이라 유효숫자가 없다" | 격자 눈금 6 dB · 참값 구간 [12, 24] dB · Pd 보간 16.4 dB 를 그림 4 의 구간막대와 표에 함께 싣는다 ⟨`report03_illuminators.json : occupancy_cost`⟩ |
| D08 | III-A | "절대 σ 가 측정으로 검증되지 않았다면 검출 결과 전체가 흔들린다" | 공통모드 σ 오차는 15셀 전부에서 순위를 그대로 두고 절대거리만 σ 1 dB 당 0.246 dB 움직인다. 논문은 순위를 주장하고 절대 레벨은 VI 편 교정구로 앵커한다 ⟨`sigma_sensitivity.json : common_mode`⟩ |
| D09 | VI | "여유 0.30 dB 는 얇다" | 좁은 쪽은 Matrice 4E 하나이고 Mini 5 Pro 는 2.95 dB 다. 두 기체를 함께 재어 넓은 쪽이 좁은 쪽의 판정을 받친다 ⟨`report06_derived.json : ranking_validation`⟩ |
| D10 | VI | "그 여유는 앵커 절대레벨 위의 설계값이고, 앵커 절편에 통계규약 변환상수가 들어 있다" | 그 상수는 2.51 dB 이고 빼면 예상 σ 가 내려가 여유가 넓어진다. **생산 σ 는 slope_only 라 절편을 안 쓴다** ⟨`sigma_anchor.json : statistic_resolution.reconcile.by_kind.exponential.offset_db`⟩ |
| D11 | III-C | "1.07 m/s 는 규격 상수가 아니라 기본값 20 ms 의 귀결이다" | 그렇다. 합법 범위 {5…160} ms 가 v_max 를 4.283 ~ 0.134 m/s 로 벌린다. **가장 짧은 5 ms 에서도 4.28 m/s 라 5 m/s 를 못 덮는다 — 방향 불변, 크기만 4배 완화** ⟨`vmax_hardening.json : verdict.configuration_dependence`⟩ |
| D12 | III-C | "멀티스태틱으로 풀리지 않나" | 참인 문장은 **"수신기 한 대로는 못 푼다"** 다. 4대면 모호 부피가 1.01e-01 → 1.55e-04 로 줄지만, 도플러 1빈 오차에서 2.68e-02 로 되돌아가고 유령 덩어리 192개가 남는다 ⟨`vmax_hardening.json : F_multistatic`⟩ |

### R2 — 방법 계층 (주장 크기를 맞추면 사실이 된다)

| # | 절 | 공격 | 답 |
|---|---|---|---|
| D13 | III-A | "PO 는 few-λ 표적에서 부정확하다 — 드론이 바로 그 크기다" | PO **모델 자체의** 간극을 정확 Mie 기준해로 따로 쟀다 — kr ≥ 9.06 에서 1 dB, kr ≥ 15.16 에서 0.5 dB 안이다. 21조합 중 1개가 그 문턱 아래이고 그 자리를 §4 앵커가 잡는다 ⟨`report02_derived.json : po_floor`⟩ |
| D14 | III-A | "Sionna 에도 SBR 이 있으니 엔진 기여는 이미 그 안에 있다" | 기술보고서(v1.2 · 59쪽)에 SBR 은 48회 나오고 우리도 그 엔진을 그대로 쓴다. 같은 문서에서 `physical optics` 0회 · `radar cross section` 0회다 — **더한 것은 표면적분과 σ 출력**이다 ⟨`prior_settled_sionna.json : word_counts_rerun_this_session`⟩ |
| D15 | III-A | "가림 차이가 이산화 잡음일 수 있다" | λ/7↔λ/12 이산화 바닥이 최대 0.071 dB 이고 7기체 전부에서 가림이 그 위에 있다 ⟨`report02_derived.json : occlusion.floor_max_db`⟩ |
| D16 | III-A·V | "β > 45° 에서 상반성이 크게 깨진다면 엔진 자체를 믿기 어렵다" | 출사 가림을 켜면 위반 최대 9.69 → 8.24 dB 로 내려간다. 논문은 β ≤ 45° 만 쓰고(그 범위 rms 2.57 dB), 창을 넓히는 일을 다음 단계로 둔다 ⟨`sbr_defect_fixes.json : d2_exit_vis_effect_on_reciprocity`⟩ |
| D17 | IV | "배율은 CFAR 구현이 틀린 흔적이다" | 문턱 상수가 이론식과 7.6e-16 안에서 같고, 백색 맵 500,000장에서 경험/명목 = 0.997 로 눈금이 1 에 선다 ⟨`verify_cfar.json : alpha_audit` · `white.48x24`⟩ |
| D18 | IV | "셀 상관은 어느 검출기에나 있다 — 원인 지목의 근거가 약하다" | 대조군이 확정한다 — Hann→rect 로 0.96, 백색화 정합필터까지 끄면 1.02 로 눈금이 1 로 돌아온다 ⟨`verify_cfar.json : control_*`⟩ |
| D19 | IV | "그럼 이 교정표는 이 형상 하나에서만 쓰는 값이다" | 그렇다 — 같은 파형이 운용 창 1.52배, 넓은 창(256빈) 47.70배다. `check_detector_config()`(`src/passive_process.py:383`)가 형상 조건을 강제한다 |
| D20 | IV | "노치가 드론 속도대를 통째로 먹으면 비교가 무의미하다" | 3 dB 지점 f_d/Δf_d = 0.596, 프레임 48개에서 속도 문턱 WiFi 0.39 · LTE 1.10 · 5G 1.16 m/s — 그 위 속도는 온전히 남는다 ⟨`verify_eca.json : S4_target_loss`⟩ |
| D21 | IV | "ECA 깊이는 탭이 부족해서 얕게 나온 것이다" | 탭 1~96 스윕에서 포화한다. 직접파만 든 신호는 232.3 dB(float64 한계)까지, 측정 다중경로를 넣으면 56.1 dB 에서 멈춘다 ⟨`verify_eca.json : S1_depth_vs_taps`⟩ |
| D22 | III-B | "PRS 를 켜면 5G 도 전대역을 쓴다 — 왜 SSB 로 묶나" | PRS 는 측위 세션이 설정될 때 켜지는 옵션이고, 남의 셀을 빌리는 수신기의 기본선은 상시 SSB 다. PRS 체제(G2·G3)를 같은 그림에 낙관적 상한으로 싣는다 — B_ref 7.2 → 98.28 MHz ⟨`report03_illuminators.json : occupancy_cost`⟩ |
| D23 | III-B | "5G 채널이 98.3 MHz 인데 41.6 m 라는 것은 과장이다" | 채널대역이 주는 3.05 m 를 같은 그림에 병기했다 — 그 값은 **풀캡처 기준신호를 가진 체제**의 값이고 상시 SSB 체제의 값이 41.6 m 다 ⟨`report2_waveform_rcs.json : reference.G1.nr`⟩ |
| D24 | III-B | "수신 개구면적을 고정하면 λ² 의 부호가 뒤집힌다" | EIRP 고정 · 수신 안테나 **이득** 고정 전제를 §2.1 에 명시했고 그 전제는 코드 한 줄(`src/freespace_link.py:371`)이다. VI 편 측정 설계가 실제 안테나로 확정한다 |
| D25 | III-B | "두 구현이 같은 오해를 공유하면 대조가 통과해도 의미가 없다" | 심볼별 CP 규칙을 뺀 대조군에서 LTE·5G 상관이 0.06·0.05 로 무너진다 — **대조의 분해력**을 같은 표에 싣는다 ⟨`report2_waveform_rcs.json : crosscheck`⟩ |
| D26 | V | "점유·듀티 대가를 뺀 비교라 SSB 의 낮은 점유가 5G 에 유리했다" | 이 사슬은 기준신호가 CPI 전체를 채우는 규약이라 듀티가 세 밴드 모두 0 dB 다. 켜면 5G 가 LTE 대비 16.02 dB 를 더 치르고, 그 설정의 순위까지 §3.3 표가 든다 ⟨`sigma_sensitivity.json : unapplied_duty_axis`⟩ |
| D27 | V | "상한 10log₁₀N 을 넘는 이득은 계산 오류다" | 그 상한은 열잡음만 상대할 때의 값이고 ECA 잔차가 N 에 무관하게 고정이라 √N 이 잔차 대비로도 표적을 올린다(`src/experiment_detection.py:284`). 최대 초과분은 SNR50 몬테카를로 표준편차의 11.0배다 |
| D28 | VI | "야외 환경이 시뮬 자유공간과 달라 비교 대상이 흐려진다" | 순위를 정하는 λ²·점유·대역폭 항은 **밴드 간 차**이고 환경 항은 세 밴드 **공통**이다 ⟨`sigma_sensitivity.json : aspect_averaged.all_drones_agree`⟩ |
| D29 | VI | "밴드별 독립 σ 오차 1 dB 에서 단일자세 순위 보존확률이 0.58 로 떨어진다" | 그 값은 단일자세 인용의 것이다. 캠페인은 방위 1.38° 표본으로 자세평균 σ 를 내고, 자세평균에서 다섯 기체가 일치한다 ⟨`report06_derived.json : ranking_validation.mc_basis`⟩ |
| D30 | VI | "야외에서 Pfa 를 통제하면 교정 주장이 더 강해진다" | CFAR 임계는 2717 s GPU 몬테카를로 경험 Pfa 로 교정했다. 야외 세션은 **같은 임계를 부지 잡음 위에서 재현**해 사슬을 확인한다 ⟨`verify_cfar.json : chain_verify`⟩ |
| D31 | VI | "시뮬 자유공간 기하의 DNR 은 야외보다 낙관적이다" | 가장 좁은 여유는 19.2 dB 이고, 세션은 직접파를 실제로 받아 그 여유를 측정값으로 대체한다 ⟨`report06_measurement.json : adc.headroom_db_min`⟩ |

### R3 — 집계·형식 (판정 규칙을 적으면 닫힌다)

| # | 절 | 공격 | 답 |
|---|---|---|---|
| D32 | I | "일곱 갈래는 저자가 사후에 만든 범주다" | 갈래마다 축자 인용을 PDF 쪽 번호와 함께 붙였고, 46건은 빌드가 그 쪽에서 다시 찾는다 |
| D33 | I | "NATO STO 프로시딩을 동료심사 지면으로 세는 근거는" | 지면 기록이 있는 프로시딩을 P1 통과로 정의했다 — **이 정의는 우리 신규성을 좁히는 쪽이다** ⟨`report01_paper.json : h8.p1_rule_ko`⟩ |
| D34 | I | "본문에 채택을 적은 arXiv 원고는 게재로 세야 한다" | 그 규칙으로 올려도 H8 판정은 그대로다 — Sagitta 는 P2·P3 에서, FWA 협동센싱은 P2 에서 걸린다 |
| D35 | I | "Costa 와 Ziganshin 을 두 번 세어 표본을 부풀렸다" | 판마다 게재상태와 보고량이 달라 **판 단위**로 센다. 저작 수(19)를 §2 에 함께 적는다 |
| D36 | I | "Das 는 Phantom 3 를 직접 재지 않았다 — 원자료는 참고문헌 [7] 이다" | 그 귀속을 §4.3 에 적는다. 우리가 쓰는 것은 **기울기 하나**이고 절대 레벨은 세 밴드 공통이라 순위에서 상쇄된다 |
| D37 | I | "낱말 빈도가 방법을 재는 척도인가" | 낱말 0회는 **필요조건 검사**다. 교정 자체는 IV 편이 GPU 2717 s 로 수행한다 |
| D38 | I | "'Sionna 에 SBR 이 없다'고 적은 자료를 봤다" | 기술보고서 v1.2 전문에서 `SBR` 은 44회다. 스톡에 없는 것은 **면적분과 RCS 출력**이고 그 두 층이 우리가 얹은 것이다 |
| D39 | III-A | "IoU 0.875 는 눈금 없는 숫자다" | 같은 메쉬로 만든 가짜 사진을 같은 파이프라인에 넣은 **자기복제 상한** 0.864~0.957 을 함께 싣고 상한 대비로 읽는다. 자세 1° 오차에서 0.906 으로 내려간다 |
| D40 | III-B | "그러면 18 dB 를 '점유 대가'라고 부르는 것이 잘못 아닌가" | 18 dB 는 **상시 체제와 풀로드 체제의 차**이고 그 정의를 JSON `defn` 에 박아 두었다. 대역만 분리한 값은 V 편 대역고정 스윕이 낸다 |
| D41 | III-B | "모호함수를 따로 계산했다면 검출기와 다른 커널일 수 있다" | 같은 커널로 계산했고 6경우에서 −45 dB 이상 셀의 최대 편차 0.144 dB 를 실었다 |
| D42 | III-B | "SSB PRF 는 단일 CPI 에서 읽은 한 점이다" | 접힘은 PRF 하나가 정한다 — TS 38.213 기본 주기가 물리 반복률을 50 Hz 로 고정하고, 참 도플러 64.0 Hz 가 14.0 Hz 로 접힌다. CPI 가 정하는 것은 가드 폭이고 그 스윕은 V 편이 싣는다 |
| D43 | IV | "실측 플랫폼이 더 현실적인 근거다" | census 16편·198쪽에서 CFAR·false alarm 이 둘 다 0회인 논문이 13편이고 검출을 주장한 논문은 1편이다. 실외는 배경을 주어진 대로 받고, 이 편은 맵 10,000장을 **다시 만든다** |
| D44 | IV | "FIM 랭크는 기하 문제이고 검출기 성능과 별개다" | 검출 판정은 (R_b, f_d) 셀에서 난다 — 두 양이 위치로 풀리는 조건을 랭크 2 → 6 으로 적어두면 검출 결과가 말하는 범위가 정해진다 |
| D45 | V | "σ 절대레벨이 검증 안 됐는데 km 거리를 인용할 수 있나" | 절대 오차는 세 밴드 공통이라 순위에서 상쇄되고 거리만 옮긴다 — ±10 dB 에서 −43.3 %/+76.4 %. km 표는 이 봉투와 함께 읽는다 |
| D46 | V | "CPI 를 늘리면 되는 문제라면 구조적 대가가 아니다" | 대가는 재방문 시간이다 — LTE 패리티에 3.75배, WiFi 패리티에 10배. 25 m/s 이상에서 WiFi 패리티는 코히어런스 한계를 넘는다 ⟨`cpi_guard_sweep.json : cost_of_long_cpi`⟩ |
| D47 | V | "always-on 벤치는 단일 반송파·단일 σ 라 자유공간 결과와 축이 다르다" | 그래서 그 절은 **파형 축 하나의 상대 비교**로 읽는다. 배치를 §3.6 이 밝힌다 |
| D48 | V | "β 창 밖의 자세는 어떻게 되나" | β 60~90° 에서 상반성 rms 잔차가 창 안보다 크므로 그 창을 **방법 조건**으로 명시하고, 넓히는 일을 다음 단계 표에 둔다 |
| D49 | VI | "D 정의를 모터대각으로 바꾸면 요구거리가 3.65배 달라진다" | 그 비를 표에 실었고 채택은 가장 보수적인 env 다 |
| D50 | VI | "기체 2종은 표본이 작다" | 두 기체가 앵커보다 각각 크고 작아 L² 와 L⁴ 가 **반대 부호**를 예측하고, 차등은 4.06 dB 다 |

⚠ **D01·D11·D12 는 아직 어느 노트북의 `defence()` 블록에도 없다** — `vmax_hardening.json :
verdict.corrections_required` 의 X1~X6 에서 왔다. → §5 공백 G2.

---

## 3. 그림 목록

**규격 판정 방법**: 저장된 PDF 를 `paper_kit.check_figure(path, placed_width_in=…)` 로 다시 열어
글자 크기와 계열 이중부호화를 잰다. 두 조판폭에서 각각 쟀다 — **2단 폭 7.16 in** (그림이 그려진 폭)과
**1단 폭 3.5 in**. 문턱은 8 pt.

**총평**: 벡터본 35장 중 **2단 폭에서 29장 통과**. 1단 폭에서 통과하는 것은 2장뿐이다
(`report04_f2` · `report04_f7`, 각 8.20 pt). 법칙 그림 4장은 두 폭 모두 미달이다.

| 논문 # | 절 | 파일 (`outputs/figures/`) | 소스 스크립트 | 2단 7.16 in | 1단 3.5 in | 판정 |
|---|---|---|---|---|---|---|
| F1 | I | `report01_p1_funnel.pdf` | `src/figs_report01.py` | 통과 | 4.33 pt | 2단 전용 |
| F2 | II | `report01_p2_routes.pdf` | `src/figs_report01.py` | 통과 | 4.33 pt | 2단 전용 |
| F3 | II | `report01_p3_dbsm.pdf` | `src/figs_report01.py` | 통과 | 4.33 pt | 2단 전용 |
| F4 | I | `report01_p4_prongs.pdf` | `src/figs_report01.py` | 통과 | 4.33 pt | 2단 전용 |
| F5 | III-A | `report02_f5_reference_gap.pdf` | `src/make_report02_target.py` | 통과 | 4.31 pt | 2단 전용 |
| F6 | III-A | `report02_f6_band_slope.pdf` | `src/make_report02_target.py` | 통과 | 4.27 pt | 2단 전용 |
| F7 | III-A | `report02_f7_sigma_sensitivity.pdf` | `src/make_report02_target.py` | 통과 | 4.16 pt | 2단 전용 |
| (부) | III-A | `report02_f2_mesh_photo.pdf` | `src/make_report02_target.py` | 통과 | 4.35 pt | 2단 전용 |
| **⛔** | III-A | `mesh_gallery_all.png` | `src/viz_mesh_gallery.py` | — | — | **벡터본 없음** |
| **⛔** | III-A | `mesh_compare_material_area.png` | `src/viz_mesh_material.py` | — | — | **벡터본 없음** |
| **⛔** | III-A | `mesh_compare_material_shadow.png` | `src/viz_mesh_material.py` | — | — | **벡터본 없음** |
| F8 | III-B | `report03_f4_ledger.pdf` | `src/make_report03_illuminators.py` | 통과 | 4.09 pt | 2단 전용 |
| F9 | III-B | `report03_f2_reference.pdf` | `src/make_report03_illuminators.py` | 통과 | 4.08 pt | 2단 전용 |
| (부) | III-B | `report03_f1_grid.pdf` · `f3_occupancy` · `f5_crosscheck` · `f6_af_mainlobe` · `f7_af_sidelobe` | `src/make_report03_illuminators.py` | 통과 | 3.99~4.09 pt | 2단 전용 |
| **F10** | III-C | `refrate_law_f1_ranking.pdf` | `benchmark/refrate_law.py` | **4.81 pt · 색만으로 구분** | 2.35 pt | **미달 2건** |
| **F11** | III-C | `refrate_law_f2_law.pdf` | `benchmark/refrate_law.py` | **6.71 pt** | 3.28 pt | **미달** |
| **F12** | III-C | `refrate_law_f3_matrix.pdf` | `benchmark/refrate_law.py` | **6.98 pt** | 3.41 pt | **미달** |
| **F13** | III-C | `refrate_law_f4_design_rule.pdf` | `benchmark/refrate_law.py` | **6.11 pt · 색만으로 구분** | 2.99 pt | **미달 2건** |
| F14 | IV | `report04_f4_pfa.pdf` | `src/viz_report04_detector.py` | 통과 | 4.01 pt | 2단 전용 |
| F15 | IV | `report04_f5_cause.pdf` | `src/viz_report04_detector.py` | 통과 | 3.97 pt | 2단 전용 |
| (부) | IV | `report04_f1_chain` · `f3_eca_notch` · `f6_resolution` | `src/viz_report04_detector.py` | 통과 | 4.01 pt | 2단 전용 |
| (부) | IV | `report04_f2_eca_depth.pdf` · `report04_f7_observability.pdf` | `src/viz_report04_detector.py` | 통과 | **8.20 pt** | **1단 가능** |
| F16 | V | `report05_pf2_ranking.pdf` | `src/viz_report05_paper.py` | 통과 | 4.33 pt | 2단 전용 |
| F17 | V | `report05_pf3_robust.pdf` | `src/viz_report05_paper.py` | 통과 | 4.26 pt | 2단 전용 |
| F18 | V | `report05_pf4_cpi.pdf` | `src/viz_report05_paper.py` | 통과 | 4.33 pt | 2단 전용 |
| (부) | V | `report05_pf1_gap` · `pf5_multirx` · `pf6_detector` · `pf7_anchor` | `src/viz_report05_paper.py` | 통과 | 4.33 pt | 2단 전용 |
| **F19** | VI | `report06_calibration.pdf` | `src/viz_report06.py` | **7.87 pt** | 3.85 pt | **미달(문턱 −0.13 pt)** |
| **F20** | VI | `report06_slope.pdf` | `src/viz_report06.py` | **7.87 pt** | 3.85 pt | **미달** |
| **F21** | VI | `report06_size_law.pdf` | `src/viz_report06.py` | **7.87 pt** | 3.85 pt | **미달** |
| (부) | VI | `report06_adc_headroom` · `farfield` · `ground_bounce` | `src/viz_report06.py` | **7.87 pt** | 3.85 pt | **미달** |

**PAPER_SPEC §4.2 가 요구한 F5·F6·F7 (긴 CPI · 빔 스위핑 · 검출∧무모호 헤딩)은 아직 없다** —
사양은 `vmax_hardening.json : figure_specs[0..2]` 에 있고 파일은 없다 → §5 공백 G5.
`cpi_guard_f1..f5.png` 5장은 PNG 만 있고 노트북에 실려 있지 않다.

**캡션**: 38장 중 벡터본을 가진 것은 전부 **논문에 그대로 붙일 완결 영문 문장**을 PDF 메타데이터에
싣고 있다 ⟨`paper_kit.json : sections[*].figures[*].paper_caption`⟩. 캡션을 다시 쓸 필요가 없다.

---

## 4. 인용 목록

31건이 `cite()` 블록에서 나왔고 게재상태가 전부 붙어 있다 ⟨`paper_kit.json : sections[*].citations`⟩.
법칙 쪽 3건([32]~[34])은 `refrate_law.json : novelty_guard` 에만 있다.

| # | 저자 | 제목(줄임) | 지면 | 상태 |
|---|---|---|---|---|
| 1 | S. Das 외 | Multiband Monostatic and Bistatic RCS Characterization of AAVs | *IEEE WCL* 15:3731–3735, 2026 | **게재** |
| 2 | Z. Yuan 외 | Experimental Analysis of Mono-Static 3D UAV RCS | EuCAP 2025 | **게재** |
| 3 | Y. Zhang 외 | A Unified RCS Modeling of Typical Targets for 3GPP ISAC | *IEEE JSAC* 44:702–716, 2026 | **게재** |
| 4 | S. Rzewuski 외 | Drone Detectability Feasibility Study using Passive Radars (WIFI/DVB-T) | NATO STO-MP-MSG-SET-183 p.13, 2021 | **게재** |
| 5 | H. C. A. Costa 외 | Modeling Micro-Doppler Signature of Multi-Propeller Drones | *IEEE JSTEAP* 1:208–222, 2025 | **게재** |
| 6 | H. C. A. Costa 외 | Modelling Micro-Doppler Signature of Drone Propellers | IEEE RadarConf 2024 | **게재** |
| 7 | J. Wei 외 | UAV's Rotor Micro-Doppler Feature Extraction Using ISAC Signal | *IEEE TWC* 24:10166–10182, 2025 | **게재** |
| 8 | C. Li 외 | Micro-Doppler Signature Simulation of Multirotor UAVs Using Ray Tracing | IEEE ICCT 2025, 359–364 | **게재** |
| 9 | F. Liu 외 | Clutter-Aware Integrated Sensing and Communication | *Proc. IEEE* 114, 2026 | **게재** |
| 10 | A. Ziganshin 외 | Ray-Based Simulation of Multistatic Scattering from Target Objects | EuCAP 2025 | **게재** ⚠ 회의판 |
| 11 | J. Hoydis 외 | Learning Radio Environments by Differentiable Ray Tracing | *IEEE TMLCN*, 2024 | **게재** |
| 12 | F. Colone 외 | Sliding Extensive Cancellation Algorithm (ECA-S) | *IEEE TAES* 52(3):1309–1326, 2016 | **게재** |
| 13 | A. Ziganshin 외 | Ray-Based Simulation of Scattering from Discretized Curved Bodies | arXiv:2604.05991v2 | 프리프린트 ⚠ 저널판 |
| 14 | L. Zhou 외 | LAMBDA: Low-Altitude Multimodal Base Dataset | arXiv:2607.03826v1 | 프리프린트 |
| 15 | J. Montaner 외 | Deterministic Modeling of Dynamic ISAC Channels | arXiv:2603.28736v1 | 프리프린트 |
| 16 | H. Liu 외 | DMSNet: Cross-Band Learning for Multi-Target Sensing | arXiv:2607.17655v1 | 프리프린트 |
| 17 | Z. Zhou 외 | OpenISAC: Real-Time Experimentation Platform for OFDM-ISAC | arXiv:2601.03535v2 | 프리프린트 |
| 18 | M. Pasquale 외 | BVH-Accelerated Ray Tracing for HF EM Backscattering (Sagitta) | arXiv:2604.09243v1 | 프리프린트 (본문에 ICCS 2026 채택) |
| 19 | J. Zhang 외 | AI-Empowered Low-Altitude Economy: Cooperative Sensing with FWA | arXiv:2605.07623 | 프리프린트 (본문에 ICC-W 2026 부분채택) |
| 20 | K. Huang 외 | Unreal is all you need: Multimodal ISAC Data Simulation | arXiv:2507.08716 | 프리프린트 |
| 21 | B. Kumar 외 | CellSense: Sub-6 GHz Cellular ISAC for Clutter-Robust Passive Sensing | arXiv:2606.07900 | 프리프린트 |
| 22 | S. M. Sanaie 외 | Temporal GNN for ISAC Target Detection and Tracking | arXiv:2604.08306 | 프리프린트 |
| 23 | J. Hoydis 외 | Sionna RT Technical Report (v1.2) | NVIDIA tech. report · arXiv:2504.21719 | 프리프린트 |
| 24 | J. Hoydis 외 | Sionna: Open-Source Library for Next-Generation PHY Research | arXiv:2203.11854 | 프리프린트 |
| 25 | 3GPP | E-UTRA Physical channels and modulation | TS 36.211 V17.1.0, 2022 | 표준문서 |
| 26 | 3GPP | NR Physical channels and modulation | TS 38.211 V17.1.0, 2022 | 표준문서 |
| 27 | 3GPP | NR Physical layer procedures for control | TS 38.213 V17.1.0, 2022 | 표준문서 |
| 28 | IEEE | 802.11ac-2013 (VHT-LTF) | IEEE Std 802.11ac-2013 | 표준문서 |
| 29 | IEEE | 802.11-2016 (VHT-LTF §21.3.7) | IEEE Std 802.11-2016 | 표준문서 |
| 30 | NI / Ettus | USRP X410 Specifications | NI tech. spec., 2024 | 기술보고서 |
| **32** | K. Abratkiewicz 외 | SSB-Based Signal Processing for Passive Radar Using a 5G Network | *IEEE JSTARS* 16:3469–3484, 2023 | **게재** ⛔ `cite()` 없음 |
| **33** | P. Jopanya, D. P. M. Osorio | Utilizing 5G NR SSB Blocks for Passive Detection and Localization of Low-Altitude Drones | arXiv:2504.02641 | 프리프린트 ⛔ `cite()` 없음 |
| **34** | — | Doppler ambiguity analysis and suppression for LTE-based passive bistatic radars | *FITEE*, DOI 10.1631/FITEE.2000143 | **게재** ⛔ `cite()` 없음 · 본문 미확보 |

⚠ [10] 과 [13] 은 **같은 저자의 다른 판**이다 — 회의판이 게재본, 저널판이 프리프린트다.
반드시 구별해 인용한다 ⟨`prior_settled_h8.json : h8_candidates[2]/[3]`⟩.
⚠ [34] 는 검색 메타데이터만 확보한 상태다. 배경 인용으로만 쓴다.
⚠ Wypich & Zielinski 는 `/data/public` 268편 어디에도 PDF 가 없어 **인용에서 뺐다**
⟨`prior_settled_h8.json : X-C17`⟩.

---

## 5. ⭐ 공백 목록 — 제출 전에 메울 것, 비용순

값은 실측 런타임에서 왔다 ⟨`outputs/regen_timings.json`, 각 JSON 의 `meta.runtime_s`⟩.
**비싼 것은 비싸다고 적었다.**

| # | 할 일 | 비용 | 그러면 결정되는 것 |
|---|---|---|---|
| **G1** | `src/paper_kit.py:100` `PAPER_TITLE`·`CONTRIBUTION` 을 PAPER_SPEC §1 로 갱신하고 `extract_paper_kit()` 재실행 | **GPU 0 · 5분** | `paper_kit.json : meta` 가 정본 제목을 싣는다. 지금은 옛 제목이 박혀 있다 |
| **G2** | 법칙을 03편 노트북에 싣는다 — `refrate_law.json` 표 4개 + `vmax_hardening.json` 탈출구 6판정 + 조건절 X1~X6 을 `defence()` 로 | **GPU 0 · 반나절** (스크립트는 이미 돎: 4.5 s + 11.4 s) | III-C 가 공급 노트북을 갖는다. **지금 논문의 헤드라인 절에 소스 노트북이 없다** |
| **G3** | 05편 철회 실행 — `coverage_ceiling_by_mode.5G` · `blind_heading_frac_by_mode.5G` 를 내리고 표 V-3·V-5·V-6 으로 대체 (`src/make_report05_results.py:181-182`) | **GPU 0 · 2시간** (노트북 재빌드 ~2분) | 가장 공격받기 쉬운 한 줄이 사라지고 σ-무관 표 셋이 들어온다 |
| **G4** | 인용 [32]~[34] 를 01편 `cite()` 로 올리고 §1.4 "하지 않는 주장" 3행을 신규성 문단에 넣는다 | **GPU 0 · 1시간** | 법칙의 선행을 우리가 먼저 적는다. 안 적으면 심사에서 즉사한다 |
| **G5** | 그림 F5·F6·F7 을 그린다 (긴 CPI · 빔 스위핑 · 검출∧무모호) — 사양 `vmax_hardening.json : figure_specs` | **GPU 0 · 반나절** | 논문 그림 7장 규격이 채워진다 |
| **G6** | 법칙 그림 4장을 `paper_kit.save_figure` 로 다시 그린다 (2단 6.11~6.98 pt → 8 pt 이상, F1·F4 의 색-전용 계열에 마커/선종 추가) | **GPU 0 · 2시간** | 헤드라인 그림 4장이 조판을 통과한다 |
| **G7** | 02편 PNG 3장(`mesh_gallery_all` · `mesh_compare_material_{area,shadow}`)에 벡터본을 만든다 | **CPU 렌더 · 1시간** (`SIONNA2_CPU=1`) | 그림 전부가 벡터본을 갖는다 |
| **G8** | ⭐ **E-ALIAS** — 상용 셀의 SSB 주기 분포를 X410 으로 관측하고 06편 1순위 실험으로 올린다 | **벤치 1~2일** (장비 보유) | D11 의 설정 의존 공격이 닫힌다. **지금 우리가 안 잰 유일한 헤드라인 입력이다** |
| **G9** | 06편 그림 6장을 8 pt 이상으로 다시 그린다 (지금 7.87 pt, 문턱에서 0.13 pt 모자란다) | **GPU 0 · 1시간** | VI 절 그림이 통과한다 |
| **G10** | 듀티 축을 R90 경로에 배선 (`freespace_link.duty_db_from_cpi` 호출처 0회) 후 stage 5 재실행 | 설계 반나절 + **GPU ~1시간** | λ²(9.03 dB)보다 큰 σ-무관 축이 결과에 들어온다. WiFi–5G 격차가 0.27 dB 로 붙는지 확정 |
| **G11** | 자세평균 σ 를 정본 solve 경로에 넣고 측정 기울기를 배선 (`experiment_freespace_sigma.py` 의 `sigma_anchor` 참조 0회) | **GPU ~1시간** ×2 | V2 주장이 문장에서 사슬 속성으로 바뀐다. 5기체 중 2기체 순위가 바뀐다 |
| **G12** | 파형·RCS 스윕 복구 — stage2 가 `IndexError` 로 죽는다(52분 소모) | **GPU 52분+ · 디버깅 미상** | 02·03편의 자세 패턴이 현재 기하 위에 선다 ⟨`docs/RESUME_0731.md` §3⟩ |

**비싼 것 셋 (이번 논문 범위 밖이라고 적는다)**

| 할 일 | 비용 | 왜 이번엔 아닌가 |
|---|---|---|
| 편파 확장 (커널 VV/HH) | 커널 개조 + σ 격자 전면 재계산 **≈ 23 h GPU × 2편파** ⟨`docs/RESUME_0731.md` §3⟩ | 앵커(VV)와 모형(무편파)의 정합은 다음 논문의 크기다 |
| 바이스태틱 β > 45° 유효화 | 외부 솔버 교차검증, **규모 미정** | 유효창 선언으로 이번 논문은 닫힌다 |
| 절대 σ 레벨 앵커 (교정구 세션) | 조달 + 세션 **1일**, 그리고 기체 입고 대기 | 헤드라인이 σ 와 무관하므로 논문은 그것 없이 닫힌다 |

**G1~G4 는 GPU 0 이고 합쳐 하루 안이다. 그 넷이 정본 좌표와 헤드라인 절을 세운다.**
G8 은 캠페인 항목이고 나머지는 그림·배선이다.

---

## 6. ⭐ 좁히기 기록 — 이 논문이 덮는 것과 덮지 않는 것

사용자가 좁히기를 명시적으로 허가했다: *"하다가 정 안되는 것이 있으면 태스크 자체를 현실성 있게
좁혀서 진행시키자."* 그래서 이 목록은 **결과물**이다. 다음 라운드의 범위 팽창을 막는 것이 이 목록의 일이다.

### 6.1 주장 층위에서 좁힌 것

| # | 원래 | 좁힌 것 | 이유 · 출처 |
|---|---|---|---|
| N01 | 세 파형 **3자 순위** | **승자 주장 + 2위 동률** (그리고 헤드라인에서 내림) | 단일자세에서 5기체가 3개 순위를 낸다 ⟨`sigma_sensitivity.json : ranking_consensus`⟩. WiFi–5G 쌍은 어느 설정에서도 안 선다 ⟨`PAPER_POSITION.md` §1 1·2행⟩ |
| N02 | **절대 검출거리** R90 3.69~11.10 km | **drop** — 상대 비교만 | σ 공통모드 ±10 dB 가 거리를 −43 %/+76 % 옮긴다 ⟨`sigma_sensitivity.json : common_mode`⟩ |
| N03 | **드론 RCS 정확도** | **drop** — 앵커는 재보정이지 검증이 아니라고 앵커 자신이 적는다 | `sigma_anchor.json : meta.disclaimer`. 앵커 1기체·1실험실, Das 의 Phantom 3 행은 Yuan 원자료의 재분석 |
| N04 | **자세분해 바이스태틱** 전 각도 | **β ≤ 45° 유효창 선언** | 상반성 위반 최대 8.24 dB(출사 가림 후) ⟨`sbr_defect_fixes.json : d2_*`⟩ |
| N05 | "5G 커버리지 = 0, 전 헤딩 블라인드" | **CPI 스윕 + 검출∧무모호 표** | 한 점(CPI 100 ms + 2.5빈 선언가드)의 산물 ⟨`cpi_guard_sweep.json : verdict.artifact`⟩ |
| N06 | "CPI 로 못 고친다" | **"무모호 속도는 CPI 로 안 고쳐진다"** — 검출 블라인드는 고쳐진다 | X2 ⟨`vmax_hardening.json : verdict.corrections_required`⟩ |
| N07 | "5G 가 나쁘다" | **"상시 기준신호의 반복률이 정한다"** | 같은 M 에서 순위가 뒤집힌다 ⟨`cpi_guard_sweep.json : structural.s6`⟩. 12종 표의 최악은 유휴 WiFi 비콘 |
| N08 | `v_max = λ·PRF/4` | **그 식은 하한이다** — 일반형은 `λ·PRF/(4cos(β/2)cos δ_el)` | X1, 완화계수 중앙값 1.011·최대 1.451 ⟨`vmax_hardening.json : A_formula`⟩ |
| N09 | "멀티스태틱으로 못 푼다" | **"수신기 한 대로는 못 푼다"** | X5 ⟨`vmax_hardening.json : F_multistatic`⟩ |
| N10 | "최초로 …" 류 전부 | **엔진과 파이프라인 통합 + 교정된 비교** | Rzewuski 2021 이 같은 산출물을 FDTD 로 냈다. `paper_kit._BANNED_CLAIM` 이 기계로 막는다 |
| N11 | H8 을 넓게 읽기 | **문자 그대로의 4관문 + Q1·Q2 동반 의무** | `paper_kit._H8_TRIGGER` 가 두 단서 없는 문장을 예외로 막는다 |
| N12 | 마이크로도플러 · 챔버 · 바닥유령 | **리포트에서 제외** (코드 보존) | `REBUILD_2026-07-30.md` §3. 미도플러는 자체 검증 수단이 없고 Costa(JSTEAP, 게재)가 해석 경로를 이미 갖는다 |
| N13 | 순수 PO 엔진 결과 | **삭제** — 단 해석 PO 구는 **기준해**로 유지·명시 | `REBUILD_2026-07-30.md` §3 |

### 6.2 작업 층위에서 좁힌 것

| # | 좁힌 것 | 이유 |
|---|---|---|
| N14 | 리포트 **21편 → 6편**, 파이프라인 26단계 11.9시간 → 필요분만 | `REBUILD_2026-07-30.md` §2·§4 |
| N15 | 01편 셀 예산 — 논문 블록 3셀 → `attach()`(+0) + `paper_appendix()`(+1) 조립 | 24/25 셀. 3셀이면 27로 상한 초과 |
| N16 | 01편 그림 — 기존 `build_prior_survey.py` 를 안 건드리고 새 stem `report01_p1..p4` 발행 | 병렬 워크플로가 그 JSON 을 다시 쓸 수 있다. 옛 `report01_survey_*.png` 는 고아로 남았다 |
| N17 | 01편 폰트 사다리 상향 (base 10 pt / min 9 pt) | `bbox_inches='tight'` 로 7.28 in 이 되어 7.16 in 배치 시 8 pt 가 7.87 pt 로 떨어졌다. 검사를 끄는 대신 활자를 키웠다 |
| N18 | 01편 P1 관문 규칙 — 본문 채택 문장을 `일부` 로 세고 프리프린트 유지 | 인쇄된 규칙을 **적용된 규칙**으로 좁혔다. 우리 신규성을 줄이는 방향이라 안전하다 |
| N19 | 01편 인용 저자 — `First-author et al.` (전체 저자 나열 안 함), 제목은 PDF 1쪽에서 기계 추출 | 재현 가능한 형태. 감사에서 어긋난 first_author 4건을 정정했다 |
| N20 | 신규성 문단만 영문 + 한국어 provenance 리드인 | 원고에 그대로 붙일 두 블록(방법 문단·신규성 문단)만 예외 |
| N21 | σ 격자 5기체 → 필요 시 1기체 | 헤드라인이 σ 를 안 타므로 값싸게 좁힌다 ⟨`PAPER_SPEC.md` §5-5⟩ |
| N22 | 기체 7종 → 실측 2종(matrice4e·mini5pro) + 대조군 2종 | `PAPER_SPEC.md` §5-1 |
| N23 | 다중 Rx → 단일 Rx (멀티스태틱 완화는 조건절 X5 한 절로) | `PAPER_SPEC.md` §5-4 |
| **N24** | **이 문서**: 방어선 50행 중 R1·R2 는 전문, R3 은 공격·답 요지만 | 원문은 `paper_kit.json : sections[*].defence` 에 있고, 이 문서는 그 **위험순 진입점**이다 |
| **N25** | **이 문서**: 제목 충돌을 양쪽 다 쓰지 않고 **PAPER_SPEC 정본으로 판정**하고 옛 좌표를 §0 표 한 줄로 남겼다 | 두 좌표를 병기하면 다음 사람이 다시 고른다. 판정과 근거를 적는 편이 싸다 |

⛔ **절대 버리지 않는 것**: v_max 법칙과 12종 교차표준 표 · 탈출구 6판정 · Pfa 교정
⟨`PAPER_SPEC.md` §5⟩. 앞의 둘이 기여이고 셋째가 그것을 정량으로 만든다.

---

## 다음 단계

| 다음에 할 일 | 그러면 결정되는 것 | 어디서 |
|---|---|---|
| §5 G1~G4 를 친다 (GPU 0 · 하루 안) | 정본 제목이 산출물에 박히고, 헤드라인 절 III-C 가 공급 노트북을 얻고, 철회가 실행되고, 법칙의 선행을 우리가 먼저 적는다 | `src/paper_kit.py` · `src/make_report03_illuminators.py` · `src/make_report05_results.py` · `src/make_report01_prior.py` |
| §5 G5~G7·G9 로 그림을 채운다 | 논문 그림 7장 규격이 서고, 헤드라인 그림 4장이 조판을 통과한다 | `src/viz_report05*.py` · `benchmark/refrate_law.py` · `src/viz_report06.py` |
| §5 G8(E-ALIAS)을 06편 1순위로 올린다 | 설정 의존 공격(D11)이 닫힌다 | `docs/MEASUREMENT_PLAN.md` · `src/make_report06_measurement.py` |
| §5 G10~G11 로 듀티·자세평균·앵커를 사슬에 배선한다 | V 절 주장이 문장에서 산출물 속성으로 바뀐다 | `src/freespace_link.py` · `src/experiment_freespace_sigma.py` |
| `extract_paper_kit()` 을 노트북 갱신마다 다시 돌린다 | 이 문서와 `paper_kit.json` 이 노트북과 같은 상태를 유지한다 | `PYTHONPATH=src:benchmark … -c "import paper_kit as pk; pk.extract_paper_kit()"` |
