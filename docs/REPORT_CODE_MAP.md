> ⚠ **2026-08-16 재편 전 번호 체계의 기록이다** — 리포트 6편 시대의 지도라 지금의 편성이 아니다. 옛→새 환산은 [`RESTRUCT_PLAN.md`](RESTRUCT_PLAN.md) §1 표, 현행 편성은 [`REPORTS_VOLUMES.md`](REPORTS_VOLUMES.md).

# REPORT_CODE_MAP — 리포트의 각 절이 어느 코드·JSON 에서 나오는가

리포트 6편의 **절 하나하나**를 그것을 만든 코드와 JSON 에 잇는 지도다. 새로 온 사람이
"이 숫자 어디서 났나" 를 30초 안에 끝내라고 만들었다. 2026-07-31 재편판.

```
report0N_*.ipynb  <-- src/make_report0N_*.py        [표현층: 계산 없음. 서술·표·출처태그]
                          +-- outputs/<name>.json   <-- benchmark/*.py · src/viz_*.py · src/experiment_*.py
                                                          [계산층: 물리·시뮬·검증이 여기 있다]
                                                          +-- 핵심 모듈 (rcs_sbr · materials · waveforms · passive_process …)
```

- 본문 숫자는 `값 ⟨outputs/xxx.json : key⟩` 로 출처가 붙는다. `src/report_style.py` 의 `num()` 이
  그 JSON 을 열어 대조하고 어긋나면 빌드를 세운다.
- 파생 JSON 3개(`report02_derived` · `report03_illuminators` · `report06_derived`)는 **빌더가 만든다** —
  리포트 안의 유도량을 한 파일로 굳혀 같은 값을 두 번 계산하지 않게 한 것이다.
- 생산 순서와 소요는 `benchmark/regen_mesh_dependents.py --list` 가 진리원이다(29단계 · 직렬 9.1 h).
- 리포트가 읽는 JSON 을 파이프라인이 전부 만드는지는 `--check` 가 검사한다.

---

## 0. 숫자 하나를 역추적하는 절차

1. 노트북에서 그 숫자의 출처태그를 본다 → `outputs/xxx.json : key`.
2. **§7 JSON → 생산자** 표에서 `xxx.json` 의 생산 스크립트를 찾는다.
3. 그 스크립트를 열면 계산이 있다. 스크립트가 부르는 핵심 모듈은 §8 에 있다.
4. 다시 만들려면 `regen_mesh_dependents.py --list` 로 단계 번호를 보고 `--stage N` 으로 그 단계만 돌린다.

---

## 1. 리포트 01 — 선행연구

빌더 `src/make_report01_prior.py` · 근거 1종(`prior_census.json`) · 그림 4장

| 절 | 읽는 JSON | 그림 |
|---|---|---|
| 여는 블록 · 방법 | `prior_census.json : meta.*` | |
| §1 Sionna RT 가 푸는 것 | `prior_census.json : sionna_api.*` (설치본 API 를 직접 셈) | |
| §2 센서스 — 관문 4개 | `prior_census.json : funnel.*` | `report01_gate_funnel.png` |
| §2.1~2.3 게재본 · 프리프린트 | `prior_census.json : papers[]` | |
| §3 조달 카탈로그 | `prior_census.json : strategies.*` | `report01_strategy_matrix.png` |
| §3.2 낱말 빈도 | `prior_census.json : counts.*` | `report01_dbsm_counts.png` · `report01_detection_vocab.png` |
| §4 우리가 선 자리 | `prior_census.json` · `sbr_kr_sweep.json` · `verify_cfar.json` | |

- 계산: `benchmark/prior_census.py` — PDF 전문 추출(PyMuPDF) · 축자 인용 기계대조(`:450`) · 그림 4장.
- 원자료: `/data/public/sionna_jeong/papers_isac_sionna`, 정리 노트는 `prior_work/`.

## 2. 리포트 02 — 표적 모델

빌더 `src/make_report02_target.py` (게재 규격 그림 4장 자체 생성 + 파생 `report02_derived.json`)

⭐ 이 편은 논문 **III-A. Target Model** 을 먹인다(`docs/PAPER_SPEC.md` §3). 편 머리에 `논문 대응`
블록, 끝에 `§7 방법 문단 · 방어선 · 인용` 이 붙고, 빌더가 내는 그림 넷은 `paper_kit.save_figure()`
로 **벡터 PDF + 400 dpi PNG** 를 함께 만들어 배치 폭 7.16 in 에서 8 pt 를 지킨다.

| 절 | 읽는 JSON (생산자) | 그림 (생산자) |
|---|---|---|
| §1 일곱 대의 기체 | `mesh_gallery.json` (`src/viz_mesh_gallery.py`) → `report02_derived.json : mesh` | 그림 1 `mesh_gallery_all.png` (viz_mesh_gallery) |
| §1.1 사진 대조 | `mesh_compare_photo.json` (`src/viz_mesh_photo.py`) → `report02_derived.json : photo` | 그림 2 `report02_f2_mesh_photo.{pdf,png}` (빌더, 실측 2종 + 대조군 2종) |
| §1.2 형상 검사 세 가지(사진·CAD·실물) | `mesh_compare_cad.json` (`src/viz_cad_compare.py`) · `community_compare.json` · `real_cad_compare.json` · `phantom4_scan_compare.json` | |
| §1.3 부품별 재질 | `mesh_compare_material.json` (`src/viz_mesh_material.py`) → `report02_derived.json : material` | 그림 3 `mesh_compare_material_area.png` (viz_mesh_material) |
| §2 엔진(가림 + PO 적분) | `mesh_compare_material.json : airframes.*.shadow/sigma` → `report02_derived.json : occlusion` · `report3_rt.json` · `prior_settled_sionna.json : word_counts_*`(엔진 문장) | 그림 4 `mesh_compare_material_shadow.png` (viz_mesh_material) |
| §2.1 바이스태틱 출사 가시성 | `sbr_defect_fixes.json : d2_*` `d4_*` (`benchmark/verify_sbr_defect_fixes.py`) | |
| §3 기준해 셋 + 기체가 놓인 kr | 기준해는 빌더가 `benchmark/mie_pec_sphere.py` 를 직접 호출해 그린다 | 그림 5 `report02_f5_reference_gap.{pdf,png}` (빌더, (c) 판이 옛 `report02_electrical_size.png` 을 흡수) |
| §3.1 두 눈금(해석 PO · 정확 Mie) | `sbr_kr_sweep.json` (`benchmark/verify_sbr_kr_sweep.py`) · `report02_derived.json` | |
| §3.2 다중반사 위상 | `sbr_defect_fixes.json : d3_multibounce_phase` | |
| §4 앵커 sigma = A(f)·B1·B2 (기울기만 측정) | `rcs_anchor.json` (`benchmark/rcs_anchor.py`) · `sigma_anchor.json` (`src/sigma_anchor.py`) | 그림 6 `report02_f6_band_slope.{pdf,png}` (빌더) |
| §4.1 모드 선택(레벨이동 · 대가) | `report02_derived.json : anchor_modes` (빌더) | |
| §4.2 세 인자, 각각의 출처 | `rcs_anchor.json : literature` · `report02_derived.json : anchor` | |
| §4.3 비교가능성 원장 | `sigma_anchor.json : drones` | |
| §4.4 미통제 항의 크기 | `sigma_anchor.json : uncontrolled` | |
| ⭐ §5 σ 오차 → 순위 강건성 | `sigma_sensitivity.json` (`benchmark/sigma_sensitivity.py`) → `report02_derived.json : sigma_sens` | 그림 7 `report02_f7_sigma_sensitivity.{pdf,png}` (빌더 — 공통모드 · 인용규약별 문턱 · MC) |

- ⭐ **§5 가 이 편의 두 번째 산출물**이다: 공통모드 σ 오차는 순위에서 상쇄되고(절대거리만 σ 1 dB 당
  0.246 dB), 차분(밴드별) σ 오차가 순위를 정한다 — 그래서 §4 의 기울기 앵커가 그 축을 잡는다.
  자세평균 인용 + 측정 기울기가 최악 뒤집힘 문턱을 0.09 → 3.72 dB 로 올린다.
- ⚠ 자세 패턴(폴라)·부품 스트립은 `report2_waveform_rcs.json` 이 옛 메쉬라 이 편에서 **뺐다** —
  현재 메쉬로 다시 재어 되싣는 일이 02편 §6 표 두 번째 줄이다.

- ⭐ **데이터 시각**: 빌더가 `report02_derived.json : provenance` 에 이 편이 읽는 JSON 15개의 생성
  시각을 메쉬 소스(`src/drone_cad.py` · `src/drones.py` · `src/cadkit.py` · `src/geom.py`)의 최신
  편집 시각과 맞대어 새것/옛것을 적는다. 옛것으로 나온 원장의 재실행은 02편 §6 표에 있다.

- 커널: `src/rcs_sbr.py:184 rcs_sbr_batch` — Mitsuba first-hit 가림 + 조명면 PO 적분, 재질은 `src/materials.py`.
- 메쉬: `src/drones.py:822 build_drone` · `src/drone_cad.py` · `src/cadkit.py` · `src/geom.py`.
- 기준해: `benchmark/mie_pec_sphere.py:207 sphere_reference_set`(정확 Mie · 해석 PO), `selfcheck()` 보유.
- 앵커: `src/sigma_anchor.py` — 생산 모드 `slope_only` 는 **A(f) 의 기울기만** Das 측정에서 받는다.
  절대 레벨 A(f)|mean 과 B1 은 우리 PO 계산 그대로다(평균 레벨이동 0.00 dB). 레벨까지 옮기는
  `level_and_slope_L2/L4` 는 크기전이 법칙을 가정하고, 두 법칙은 최대 9.50 dB 갈린다(02편 §4.1).

## 3. 리포트 03 — 조명원

빌더 `src/make_report03_illuminators.py` (그림 3장 + 파생 `report03_illuminators.json`)

| 절 | 읽는 JSON (생산자) | 그림 |
|---|---|---|
| §1 세 조명원 | `report2_waveform_rcs.json` (`src/viz_report2.py`) | `report2_resource_grid.png` |
| §1.1 5G 의 두 대가 | `report2_waveform_rcs.json : reference.G1.*` · `report03_illuminators.json` | `report2_ref_signal.png` |
| §2 대가 원장 | `report03_illuminators.json` · `report4_fixups.json` (`benchmark/report4_fixups.py`) | |
| §2.1 각 항목이 서는 조건 | 위와 같음 + `report5_results.json : A_occupancy` (`benchmark/run_matrix.py --only a`) | `report03_cost_ledger.png` · `report2_occupancy.png` |
| §2.2 거리 규약 c/B | `verify_ambiguity.json` (`benchmark/verify_ambiguity.py`) | |
| §3 파형 검증(Sionna PHY) | `report2_waveform_rcs.json : crosscheck.*` | `report2_crosscheck.png` |
| §4 모호함수 | `verify_ambiguity.json` · `report03_illuminators.json` | `report03_af_mainlobe.png` · `report03_af_sidelobe.png` |

- 파형 합성: `src/waveforms.py`(LTE CRS `:258` · 5G SSB `:313` · WiFi VHT-LTF `:370`).
- 대조: `src/waveforms_sionna.py` — `src/viz_report2.py:387` 이 Sionna PHY `OFDMModulator` 로 독립 변조해 채점한다.
- 모호함수는 검출기와 같은 커널을 쓴다 — `benchmark/verify_ambiguity.py:150`.

## 4. 리포트 04 — 검출기

빌더 `src/make_report04_detector.py` · 그림 7장은 `src/viz_report04_detector.py`

| 절 | 읽는 JSON (생산자) | 그림 |
|---|---|---|
| §1 사슬 | `verify_cfar.json : chain.*` · `verify_eca.json` | `report04_f1_chain.png` |
| §2 ECA 소거 깊이 · 0-도플러 노치 | `verify_eca.json` (`benchmark/verify_eca.py`) | `report04_f2_eca_depth.png` · `report04_f3_eca_notch.png` |
| §3 CFAR 교정 | `verify_cfar.json` (`benchmark/verify_cfar.py`) · `prior_census.json`(문헌 대조) | `report04_f4_pfa.png` |
| §3 교정표 · 원인(셀 상관) | `verify_cfar.json : chain.*.calib_op_mask1` · `control_*` | `report04_f5_cause.png` |
| §4 분해능 · CRLB · 관측가능성 | `verify_observability.json` (`benchmark/verify_observability.py`) | `report04_f6_resolution.png` · `report04_f7_observability.png` |

- 검출 사슬: `src/passive_process.py` — ECA → CAF 거리도플러 → CA-CFAR. 교정표를 읽는 자리는 `:283 _load_pfa_calibration`.
- 기하·링크: `benchmark/geometry.py` · `benchmark/link_budget.py` · `benchmark/scenarios.py` · `src/bistatic_scene.py`.

## 5. 리포트 05 — 검출 결과

빌더 `src/make_report05_results.py` · 그림 8장은 `src/viz_report05.py`

| 절 | 읽는 JSON (생산자) | 그림 |
|---|---|---|
| §1 기하 | `report13_freespace.json` (`src/experiment_freespace_range.py`) | |
| §1.1 유효창(beta · 앙각) | 위 + `report13_sigma_grid.json` (`src/experiment_freespace_sigma.py`) · `sbr_defect_fixes.json` | `report05_f1_geometry.png` |
| §2 감도사슬 | `verify_linkbudget.json` (`benchmark/verify_linkbudget.py`) · `sigma_anchor.json` | `report05_f2_budget.png` |
| §2.1 어느 벽이 거리를 정하나 | `report13_freespace.json : solve.*` | `report05_f7_walls.png` |
| §3 세 파형 벤치마크 | `report13_freespace.json : ranges.*` | `report05_f3_detector.png` |
| §3.2~3.3 앵커 sigma 위의 R90 | `sigma_anchor.json : delta_db` x `report13_freespace.json : ranges` | `report05_f8_anchored_bands.png` · `report05_f4_range_bars.png` |
| §3.4 헤딩 균일평균 | `report13_freespace.json` · `verify_freespace.json` (`benchmark/verify_freespace.py`) | `report05_f5_heading.png` |
| §3.5 · §4 수신소자 N | `detection_rx_sweep.json` (`src/experiment_detection.py`) | `report05_f6_multirx.png` |

- 자유공간 기하·예산·검출: `src/freespace_scene.py` · `src/freespace_link.py` · `src/freespace_detect.py`
  — 셋 다 `src/passive_process.py` 의 같은 검출기를 부른다.
- sigma 조회는 `benchmark/channel.py` 한 곳을 지난다(메쉬지문 디스크캐시 `outputs/sigma_sbr_cache.json`).
- 순서 고정: `benchmark/verify_freespace.py` 는 `report13_freespace.json` 을 **읽는다** — 검지거리 실험 뒤에 돌린다
  (파이프라인 stage 5 가 그 순서다).

## 6. 리포트 06 — 실측 설계

빌더 `src/make_report06_measurement.py` (그림 6장 + 파생 `report06_derived.json`)

| 절 | 읽는 JSON (생산자) | 그림 |
|---|---|---|
| §1 하드웨어 X410 | `report06_measurement.json` (`benchmark/plan_measurement.py`) | `report06_adc_headroom.png` |
| §2 세션 체크리스트 6항목 | 위 + `report06_derived.json` | |
| §2-1 원거리장 2D^2/lambda | `report06_derived.json : farfield_adopted` | `report06_farfield.png` |
| §2-2 교정 기준체(PEC 구) | `report06_derived.json : calibration_pick` (기준 sigma 는 `benchmark/mie_pec_sphere.py:207`) | `report06_calibration.png` |
| §2-3~2-5 서브밴드 · 자세 · 지면반사 | `report06_derived.json` | `report06_ground_bounce.png` |
| §3-1 앵커 원장 | `sigma_anchor.json : uncontrolled` | |
| §4 결정표 · 기울기 · 크기법칙 | `report06_derived.json` · `report06_measurement.json` | `report06_slope.png` · `report06_size_law.png` |
| §5 다음 단계 | `measured_sigma.json` — 실측 세션이 만들 파일 | |

- 장비 제원 단일 출처: `src/experiment_x410.py:61 class X410`(ni.com / ettus.com 공식 스펙).
- 설계값: `benchmark/plan_measurement.py` · 앵커 연동 `src/sigma_anchor.py:255`(크기법칙) `:939`(문서 주입).
- 산문판 설계서: `docs/MEASUREMENT_PLAN.md`.

---

## 7. JSON → 생산자 → 파이프라인 단계

| JSON | 생산자 | 단계 | 읽는 편 |
|---|---|---|---|
| `report1.json` (meshes) | `src/viz_report1.py --only mesh,cad` | 1 | 02 §1 · 06(plan_measurement 경유) |
| `report1.json` (chamber.materials) | `benchmark/refresh_material_table.py` | 1 | 02 §1.2 |
| `phantom4_scan_compare.json` | `src/compare_phantom_scan.py` | 1 | 02 §1.3 |
| `community_compare.json` | `benchmark/compare_community.py` | 1 | 02 §1.3 |
| `real_cad_compare.json` | `benchmark/compare_real_cad.py` | 1 | 02 §1.3 |
| `report2_waveform_rcs.json` | `src/viz_report2.py` | 2 | 02 §2·§5.1 · 03 §1·§3.1 |
| `report6_sbr.json` | `src/viz_verify_sbr.py --force` | 2 | 02 §2 |
| `sbr_kr_sweep.json` | `benchmark/verify_sbr_kr_sweep.py` | 2 | 01 §4 · 02 §3.1 |
| `report3_rt.json` | `benchmark/rt_experiments.py` | 2 | 02 §2 |
| `sbr_defect_fixes.json` | `benchmark/verify_sbr_defect_fixes.py` | 2 | 02 §2.1·§3.2 · 05 §1.1 |
| `rcs_anchor.json` | `benchmark/rcs_anchor.py` | 3 | 02 §4 · 06(경유) |
| `report13_sigma_grid.json` | `src/experiment_freespace_sigma.py` | 3 | 05 §1.1 |
| `sigma_anchor.json` | `src/sigma_anchor.py` | 3 | 02 §4~§5 · 05 §2·§3.2 · 06 §3-1·§3-2 |
| `measurement_plan.json` | `src/sigma_anchor.py :: write_measurement_plan` | 3 | 06 방법 |
| `verify_ambiguity.json` | `benchmark/verify_ambiguity.py` | 4 | 03 §2.2·§4 |
| `verify_eca.json` | `benchmark/verify_eca.py` | 4 | 04 §1·§2 |
| `verify_observability.json` | `benchmark/verify_observability.py` | 4 | 04 §4 |
| `report4_fixups.json` | `benchmark/report4_fixups.py` | 4 | 03 §2 |
| `verify_cfar.json` | `benchmark/verify_cfar.py` | 4 | 01 §4 · 04 §3 · 06(경유) |
| `verify_linkbudget.json` | `benchmark/verify_linkbudget.py` | 4 | 05 §2 |
| `report5_results.json` | `benchmark/run_matrix.py --only a` | 4 | 03 §2.1 (`A_occupancy` 만) |
| `report13_freespace.json` | `src/experiment_freespace_range.py` | 5 | 05 §1~§3 |
| `verify_freespace.json` | `benchmark/verify_freespace.py` | 5 | 05 §3.4 |
| `detection_rx_sweep.json` | `src/experiment_detection.py` | 5 | 05 §3.5·§4 |
| `report06_measurement.json` | `benchmark/plan_measurement.py` | 6 | 06 §1·§2·§4 |
| `prior_census.json` | `benchmark/prior_census.py` | 7 | 01 전편 · 04 §3 |
| `report02_derived.json` | `src/make_report02_target.py` | 9 | 02 |
| `report03_illuminators.json` | `src/make_report03_illuminators.py` | 9 | 03 |
| `report06_derived.json` | `src/make_report06_measurement.py` | 9 | 06 |
| `measured_sigma.json` | **미래 산출물** — 실측 세션이 만든다 | — | 06 §5 |

그림 39장의 생산자는 넷 + 빌더다 — `benchmark/prior_census.py`(01) · `src/viz_report2.py`(02·03 공용) ·
`src/viz_report04_detector.py`(04) · `src/viz_report05.py`(05), 그리고 `report02_*` · `report03_*` ·
`report06_*` 는 그 편의 빌더가 직접 그린다.

## 7.1 ⭐ 옛 13편 번호가 박힌 이름 — 여기서 한 번에 푼다

<!-- keep-old-names:on --> <!-- 해독표다. 옛 이름이 그대로 남아 있어야 뜻이 산다.
     benchmark/rename_outputs.py 는 이 구간을 건너뛴다. -->

산출물 8종이 **은퇴한 13편 체계**의 번호를 이름에 달고 있다. 그 번호는 지금 1~6편 번호와
**충돌한다** — `report5_results.json` 을 읽는 편은 05편이 아니라 **03편**이다.
`⟨outputs/report13_freespace.json⟩` 태그를 만나면 이 표에서 찾으면 끝난다.

| 옛 이름 | 이름이 말하는 편 | **실제로 읽는 편**(태그수) | 무엇이 들었나 | 옮길 이름 |
|---|---|---|---|---|
| `report1.json` | 1편 | **02** (12) | 메쉬 삼각형수·외형봉투 + 재질 γ 표 | `mesh_materials.json` |
| `report2_waveform_rcs.json` | 2편 | **02**(25) + **03**(43) | 3파형 제원·Sionna PHY 대조·가림·RCS·재질 | `waveform_rcs.json` |
| `report3_rt.json` | 3편 | **02** (2) | Sionna RT 스톡 solver 실험 | `rt_stock_solver.json` |
| `report4_fixups.json` | 4편 | **03** (13) | 규약 상수 F1~F6(듀티·CPI·straddle·CFAR) | `convention_constants.json` |
| `report5_results.json` | 5편 | **03** (2) | 챔버 벤치 A~E — `A_occupancy` 만 살아 있다 | `bench_matrix.json` |
| `report6_sbr.json` | 6편 | **02** (3) | SBR 커널 검증(기준해 오차·기종별 가림) | `sbr_kernel_verify.json` |
| `report13_freespace.json` | 13편(없음) | **05** (52) | 자유공간 검지거리 4단계 + ranges·coverage | `freespace_range.json` |
| `report13_sigma_grid.json` | 13편(없음) | **05** (3) | σ 격자(자세×밴드)·신뢰구간·멀티스태틱 | `sigma_grid.json` |
| `figures/report2_{gallery,occlusion,rcs_polar}.png` | 2편 | **02** | 갤러리·가림·자세 극좌표 | `report02_*.png` |
| `figures/report2_{resource_grid,ref_signal,occupancy,crosscheck}.png` | 2편 | **03** | 리소스그리드·기준신호·점유·교차대조 | `report03_*.png` |

<!-- keep-old-names:off -->

이름 규칙(새 산출물은 이대로 짓는다) — **계산 JSON 은 내용으로**(여러 편이 읽으므로 편 번호는
거짓말이 된다) · **그림은 싣는 편으로**(한 장은 한 편에만 실린다) · **빌더 파생 JSON 만
`report0N_derived.json`**(그 편이 만들고 그 편만 읽어 1:1 이 보장된다).

⚠ 파일은 **아직 옮기지 않았다** — 재생성이 일부를 쓰고 있다. 전체 지도(생산자·읽는 코드 줄번호·
옮기지 않는 것·혼동쌍)는 `docs/OUTPUT_NAMING.md`, 이전 스크립트는 `benchmark/rename_outputs.py`
(예행이 기본, `--apply --pipeline-is-idle` 로만 실행).

## 8. 핵심 모듈 — 물리가 사는 곳

| 모듈 | 하는 일 | 쓰는 편 |
|---|---|---|
| `src/rcs_sbr.py` | SBR+PO 커널 — Mitsuba 광선조준 · first-hit 가림 · 출사 가시성 · PO 표면적분 | 02 · 05 |
| `src/materials.py` | 전파재질 단일 진리원 — Sionna RT 와 PO 가 같은 표를 읽는다 | 02 |
| `src/drones.py` `drone_cad.py` `cadkit.py` `geom.py` | 표적 레지스트리와 파라메트릭 CAD | 02 · 05 · 06 |
| `benchmark/mie_pec_sphere.py` | 기준해 둘(정확 Mie · 해석 PO) — 커널의 과녁 | 02 · 06 |
| `src/sigma_anchor.py` | sigma = A(f)·B1·B2 재보정 · 미통제 항 원장 · 실측계획 | 02 · 05 · 06 |
| `benchmark/channel.py` | sigma 조회 단일 진리원 + 메쉬지문 디스크캐시 | 04 · 05 |
| `src/waveforms.py` `waveforms_sionna.py` | WiFi/LTE/5G 자원격자 합성 · Sionna PHY 대조 | 03 |
| `src/passive_process.py` | 패시브 DSP — ECA → CAF 거리도플러 → CA-CFAR(교정표 적용) | 04 · 05 |
| `benchmark/geometry.py` `link_budget.py` `scenarios.py` · `src/bistatic_scene.py` | 바이스태틱 기하 · 링크버짓 · 시나리오 | 04 · 05 |
| `src/freespace_scene.py` `freespace_link.py` `freespace_detect.py` | 자유공간 기하 · 예산 · 검출 | 05 |
| `src/experiment_x410.py` | X410 하드웨어 제원 단일 출처 | 05 · 06 |
| `src/report_style.py` `provenance.py` | 출처태그 검증 · 분량 상한 · provenance 블록 | 전편 |

## 9. 파이프라인 밖에 있는 코드

리포트 6편이 읽지 않으므로 기본 실행에서 뺐고 스크립트는 디스크에 그대로 있다.
되살리는 명령은 `benchmark/regen_mesh_dependents.py --dropped` 가 찍는다.

| 주제 | 코드 |
|---|---|
| 반무향 챔버 | `src/chamber.py` · `benchmark/verify_clutter_doppler.py` · `run_matrix.py --only b,c,d,e` |
| 바닥 유령 | `benchmark/verify_floor_ghost.py` · `verify_ghost_impact.py` · `src/experiment_ghost.py` |
| 마이크로도플러 | `src/microdoppler.py` · `microdoppler_nearfield.py` · `experiment_md_range.py` · `viz_report1.py --only md` |
| RT 부가 실증 | `benchmark/verify_rt_rays.py` · `verify_target_rt.py` · `verify_rt_no_rcs.py` · `src/viz_report3.py` |
| 구 리포트 13편 | `_legacy_reports/` · `src/_legacy_builders/` (읽기전용) |
