# OUTPUT_NAMING — 산출물 이름 지도 (옛 13편 번호 → 내용 이름)

리포트가 `⟨outputs/report13_freespace.json : ranges…⟩` 같은 출처태그를 단다. **13편은 이제 없다.**
저장소는 2026-07-30 에 13편 → 6편으로 재편됐고, 산출물 8종은 **은퇴한 번호를 이름에 달고 남았다.**
그 번호는 지금 1~6편 번호와 **충돌한다** — `report5_results.json` 을 읽는 편은 05편이 아니라 03편이다.

이 문서가 그 해독표다. 태그에서 옛 이름을 보면 여기 §1 에서 한 번 찾으면 끝난다.
파일을 실제로 옮기는 절차는 §5, 옮기는 스크립트는 `benchmark/rename_outputs.py`(예행이 기본).

> 이 문서 자체는 **옛 이름과 새 이름을 둘 다** 담는다. 이름 이전 스크립트도 이 파일은 건드리지 않는다.

---

## 1. ⭐ 한 번에 찾는 표 — 옛 이름이 가리키는 것

| 옛 이름 | 이름이 말하는 편 | **실제로 읽는 편** | 무엇이 들었나 | 새 이름 |
|---|---|---|---|---|
| `outputs/report1.json` | 1편 | **02편** (§1.2 · 12태그) | 메쉬 삼각형수·외형봉투 + 재질 γ(bulk·PO) 표 | `mesh_materials.json` |
| `outputs/report2_waveform_rcs.json` | 2편 | **02편**(25) + **03편**(43) | 3파형 제원 · Sionna PHY 교차대조 · 가림 · RCS · 재질 | `waveform_rcs.json` |
| `outputs/report3_rt.json` | 3편 | **02편** (§2 · 2태그) | Sionna RT 스톡 solver 실험(광선·산란·금속판·구) | `rt_stock_solver.json` |
| `outputs/report4_fixups.json` | 4편 | **03편** (§2 · 13태그) | 규약 상수 F1~F6(듀티·CPI·straddle·CFAR 손실·CRLB) | `convention_constants.json` |
| `outputs/report5_results.json` | 5편 | **03편** (§2.1 · 2태그) | 챔버 벤치 A~E. `A_occupancy` 만 살아 있다 | `bench_matrix.json` |
| `outputs/report6_sbr.json` | 6편 | **02편** (§2 · 3태그) | SBR 커널 검증(구·판 기준해 오차, 기종별 가림) | `sbr_kernel_verify.json` |
| `outputs/report13_freespace.json` | 13편(없음) | **05편** (§1~§3 · 52태그) | 자유공간 검지거리 4단계 + ranges·curves·coverage | `freespace_range.json` |
| `outputs/report13_sigma_grid.json` | 13편(없음) | **05편** (§1.1 · 3태그) | σ 격자(자세×밴드) + 신뢰구간 + 멀티스태틱 Δσ(β) | `sigma_grid.json` |

여덟 중 **일곱은 이름이 가리키는 편이 아예 읽지 않는다.** 나머지 하나 `report2_waveform_rcs.json` 은
02편이 읽지만 태그의 63%(43/68)를 03편이 읽는다. 읽는 편은 노트북 마크다운 셀의 출처태그를 세어
확인했다(2026-07-31, 합 155태그).

**그림도 같은 충돌이 있다** — `report2_*.png` 7장 중 **4장은 03편이 싣는다**(§3).

---

## 2. 새 이름의 규칙

| 산출물 | 이름 규칙 | 왜 |
|---|---|---|
| 계산 JSON | **내용**으로 짓는다 — `sigma_grid.json` | JSON 하나를 여러 편이 읽는다. 편 번호는 태생적으로 거짓말이 된다 |
| 그림 PNG | **싣는 편**으로 짓는다 — `report03_occupancy.png` | 그림 한 장은 정확히 한 편에 실린다 |
| 빌더 파생 JSON | `report0N_derived.json` | 그 편의 빌더가 만들고 그 편만 읽는다 — 1:1 이 구조적으로 보장된다 |

이미 잘 지어진 이름들이 규칙의 증거다. 전부 내용 이름이고 전부 여러 편이 읽는다 —
`sigma_anchor.json`(02·05·06) · `verify_cfar.json`(01·04) · `prior_census.json`(01·04) ·
`sbr_kr_sweep.json`(01·02) · `sbr_defect_fixes.json`(02·05).

편 번호를 **JSON 이름에 넣어도 되는 경우는 하나뿐이다** — 그 편의 빌더가 만들고 그 편만 읽을 때다
(`report02_derived.json` · `report03_illuminators.json` · `report06_derived.json`).

---

## 3. 전체 지도 — 옛 이름 → 생산자 → 읽는 곳 → 새 이름

### 3.1 계산 JSON 8종

| 옛 이름 | 생산자(검증됨) | 파이프라인 단계 | 리포트가 읽는 키 | 코드가 읽는 곳 | 새 이름 |
|---|---|---|---|---|---|
| `report1.json` | `src/viz_report1.py --only mesh,cad` **+** `benchmark/refresh_material_table.py` | 1 | 02: `chamber.materials.<재질>.gamma_bulk/gamma_po` | `benchmark/plan_measurement.py:59` · `src/viz_mesh_gallery.py:69` · `src/viz_verify_sbr.py:44` | `mesh_materials.json` |
| `report2_waveform_rcs.json` | `src/viz_report2.py:91` | 2 | 02: `materials.rows[*]` `occlusion.*` / 03: `reference.G1.*` `crosscheck.*` | `src/make_report02_target.py:533` · `src/make_report03_illuminators.py:49` | `waveform_rcs.json` |
| `report3_rt.json` | `benchmark/rt_experiments.py:72` | 2 | 02: `C_metal.itu_metal_S` `C_metal.metal_share_pct` | `src/make_report02_target.py:282` · `src/viz_report3.py:43` | `rt_stock_solver.json` |
| `report4_fixups.json` | `benchmark/report4_fixups.py:33` | 4 | 03: `F4_linkbudget.*` `F3_ambiguity.*` `_meta.runtime_s` | `src/viz_report4.py`(F1~F6 전부) | `convention_constants.json` |
| `report5_results.json` | `benchmark/run_matrix.py:831 --only a` | 4 | 03: `A_occupancy` 만 | `benchmark/verify_floor_ghost.py:52`(RT 캐시) | `bench_matrix.json` |
| `report6_sbr.json` | `src/viz_verify_sbr.py:42 --force` | 2 | 02: `n_az` · `compare.<기종>.occl_el15` | `src/make_report02_target.py:588` | `sbr_kernel_verify.json` |
| `report13_freespace.json` | `src/experiment_freespace_range.py:54` | 5 | 05: `solve.W1.*` `ranges.*` `threshold.pfa.*` `waveforms.G1.*` | `src/viz_report05.py`(8곳) · `benchmark/verify_freespace.py:62` · `src/viz_report06.py:226` · `src/make_r6_frames.py:29` | `freespace_range.json` |
| `report13_sigma_grid.json` | `src/experiment_freespace_sigma.py:55` | 3 | 05: `meta.el_deg` | `src/sigma_anchor.py:635`(자세패턴 배열) · `src/experiment_freespace_range.py:55` · `src/render_report13.py:76` | `sigma_grid.json` |

`bench_matrix.json` 은 같은 생산자가 이미 쓰는 `outputs/bench_matrix.csv` 와 짝이 된다.

### 3.2 σ 격자 조각 5개 — 읽는 코드가 없다

`report13_sigma_grid.<기종>.json` 5개(matrice4e · mavic4pro · mini5pro · phantom4 · s1000plus,
각 0.20 MB, 2026-07-24)는 GPU 분할 실행의 중간산출물이다. 병합본만 읽히므로 조각은
`outputs/parts/sigma_grid.<기종>.json` 으로 내린다.

### 3.3 그림 7장 — 편 번호가 곧 이름이다

| 옛 이름 | 생산자 | 싣는 편 | 새 이름 |
|---|---|---|---|
| `figures/report2_gallery.png` | `src/viz_report2.py:1231` | 02 §1 | `report02_gallery.png` |
| `figures/report2_occlusion.png` | `src/viz_report2.py:950` | 02 §2 | `report02_occlusion.png` |
| `figures/report2_rcs_polar.png` | `src/viz_report2.py:1015` | 02 §5 | `report02_rcs_polar.png` |
| `figures/report2_resource_grid.png` | `src/viz_report2.py:318` | **03** §1 | `report03_resource_grid.png` |
| `figures/report2_ref_signal.png` | `src/viz_report2.py:265` | **03** §1.1 | `report03_ref_signal.png` |
| `figures/report2_occupancy.png` | `src/viz_report2.py:358` | **03** §2.1 | `report03_occupancy.png` |
| `figures/report2_crosscheck.png` | `src/viz_report2.py:461` | **03** §3 | `report03_crosscheck.png` |

⛔ **두 장은 생산자가 둘이다** — `report2_occupancy.png` 는 `src/viz_occupancy.py:174` 도,
`report2_rcs_polar.png` 는 `src/viz_radar.py:110` 도 같은 파일명으로 쓴다(둘 다 파이프라인 밖).
이름만 옮기면 옛 생산자가 옛 이름으로 다시 그려 유령 파일이 생긴다.
그래서 `rename_outputs.py` 는 이 둘의 `--apply` 를 **막는다**. 옛 생산자를 먼저 정리한다.

---

## 4. 옮기지 않는 것 — 그리고 그 이유

### 4.1 6편이 읽지 않는 옛 이름 산출물

| 이름 | 생산자 | 왜 그대로 두나 |
|---|---|---|
| `report1_microdoppler.npz` | `src/viz_report1.py:787` | 마이크로도플러는 future work 강등(`regen_mesh_dependents.DROPPED`) |
| `figures/report1_*.png` (8장) | `src/viz_report1.py` | 6편 중 싣는 편 없음 |
| `figures/report2_*.png` (나머지 21장) | `src/viz_report2.py` 외 | 6편 중 싣는 편 없음 |
| `figures/report3_*.png` (11장) | `src/viz_report3.py` (DROPPED) | 6편 중 싣는 편 없음 |
| `figures/report4_*.png` (11장) | `src/viz_report4.py` | 04편은 `report04_f*.png` 를 쓴다 |
| `figures/report5_*.png` (6장) | `benchmark/run_matrix.py` | 05편은 `report05_f*.png` 를 쓴다 |
| `figures/report13_*.png` (16장) | `src/viz_report13.py` | 6편 중 싣는 편 없음 |

읽는 편이 없으므로 충돌도 없다. 이름 이전의 위험만 남는 쪽이라 **손대지 않는다.**

### 4.2 혼동쌍 — 이름과 생산자가 엇갈려 보이는 둘

| 파일 | 생산자 | 읽는 편 | 메모 |
|---|---|---|---|
| `outputs/report06_measurement.json` | `benchmark/plan_measurement.py:192` | 06 (12태그) | 이름은 `report06_*`, 생산자는 `plan_measurement` |
| `outputs/measurement_plan.json` | `src/sigma_anchor.py:876 write_measurement_plan` | 06 (1태그) | 이름은 `measurement_plan`, 생산자는 `sigma_anchor` |

둘 다 **06편만** 읽으므로 §1 의 충돌은 아니다. 이름과 생산자가 교차해 보일 뿐이라 여기 적어 둔다.

### 4.3 옛 이름을 그대로 둘 문서

날짜가 박힌 기록은 **그 날 그 이름이었다는 사실 자체가 기록**이다. 바꾸면 기록이 거짓이 된다.
다른 작업줄이 소유한 문서도 건드리지 않는다. 이 문서(§1 표)가 그들의 해독표 역할을 한다.

| 그대로 두는 문서 | 부류 |
|---|---|
| `docs/RESUME_*.md` · `docs/AUDIT_FINDINGS_*.md` · `docs/READING_*.md` | 날짜 기록 |
| `docs/REPORT13_*.md` · `docs/REPORT14_*.md` · `docs/ARCHIVE.md` · `docs/REBUILD_2026-07-30.md` | 은퇴 체계·재편 설계 기록 |
| `docs/PRIOR_WORK_COMPARISON.md` · `docs/DRONE_ISAC_PRIOR_READING.md` · `prior_work/` | 선행연구 작업줄 소유 |
| `_legacy_reports/` · `src/_legacy_builders/` | 은퇴한 리포트·빌더 |
| `docs/OUTPUT_NAMING.md` (이 문서) | 옛·새 이름을 둘 다 담는 것이 목적 |

살아 있는 문서 안에도 **옛 이름을 일부러 적어 둔 구간**이 있다 — `docs/REPORT_CODE_MAP.md` §7.1 의
해독표와 `README.md` 의 안내 줄이다. 그 구간은 `<!-- keep-old-names:on -->` … `<!-- keep-old-names:off -->`
로 감싼다. 마크다운에서는 보이지 않고, 스크립트는 그 줄을 건너뛴다.

---

## 5. 이전 절차 — `benchmark/rename_outputs.py`

⚠ **아직 돌리지 않았다.** 재생성이 이 파일들 중 일부를 쓰고 있는 동안 이름을 옮기면 반쪽이 된다.
파이프라인이 멈춘 뒤 아래 순서로 한다.

```bash
# 1) 예행 — 옮길 파일과 바꿀 참조를 전부 찍는다 (기본값. 아무것도 바꾸지 않는다)
PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/rename_outputs.py

# 2) 한 항목만 자세히 보고 싶을 때
PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/rename_outputs.py \
    --only report13_freespace.json -v

# 3) 실제 적용 — 두 깃발을 다 줘야 한다. 실행 중 프로세스가 잡히면 스스로 멈춘다
PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/rename_outputs.py \
    --apply --pipeline-is-idle
```

적용 뒤 이 순서로 마감한다.

| 순서 | 명령 | 확인할 것 |
|---|---|---|
| 1 | 그림 라벨 4줄 수정 (§5.3) | 그림 안에 구워진 옛 이름 |
| 2 | `benchmark/regen_mesh_dependents.py --check` | 고아 감사 통과 |
| 3 | stage 9 — 리포트 6편 재빌드 | 노트북 출처태그가 새 이름으로 바뀐다 |
| 4 | `src/report_style.py :: check_budget` 6편 | 태그가 실제 JSON 을 여는지 재확인 |

### 5.1 예행이 세는 것 (2026-07-31 실측)

| 항목 | 수 | 스크립트의 처리 |
|---|---|---|
| 옮길 파일 | 20 | JSON 8 + σ조각 5 + 그림 7 |
| 고칠 코드·문서 참조 | 186곳 / 36파일 | `EDIT` — 문자열을 직접 바꾼다 |
| 노트북 안 참조 | 82곳 | `REBUILD` — 빌더가 다시 쓴다. 스크립트는 안 건드린다 |
| `outputs/*.json` 내부 경로 문자열 | 25곳 | `REGEN` — 생산자 재실행으로 따라온다 |
| 기록·타작업줄·해독표 | 110곳 / 12파일 | `FROZEN` — 옛 이름 그대로 둔다 (§4.3) |
| 확장자 없는 언급 | 25곳 | 문장 속 표현. 사람이 읽고 고친다 |

숫자는 저장소가 바뀌면 달라진다. 언제나 예행이 진리원이다.

### 5.2 스스로를 지키는 장치 두 개

| 장치 | 무엇을 막나 |
|---|---|
| `--apply` 실행 중 프로세스 검사 | 이 저장소의 `src/`·`benchmark/` 스크립트가 돌고 있으면 스스로 멈춘다. 2026-07-31 예행 때 `viz_mesh_photo.py` 를 잡아냈다 |
| `FIG_DUP_WRITERS` 차단 | 생산자가 둘인 PNG 2장(§3.3)의 적용을 막는다 |

`--apply` 는 프로세스를 **죽이지 않는다.** 찾아서 보고하고 멈춘다.

### 5.3 ⭐ 스크립트가 못 고치는 것 — 그림 안에 구워진 옛 이름 4곳

`report03_cost_ledger.png`(03편 §2 대가 원장)는 막대마다 출처 키를 **그림 텍스트로** 찍는다.
그 라벨 4개가 옛 이름을 담고 있다. 확장자가 없어 문자열 치환의 대상이 아니고, 이미 구워진
래스터라 파일을 옮겨도 그림은 옛 이름을 계속 보여 준다.

| 위치 | 지금 라벨 | 이전 뒤 라벨 |
|---|---|---|
| `src/make_report03_illuminators.py:237` | `report5_results : A_occupancy` | `bench_matrix : A_occupancy` |
| `src/make_report03_illuminators.py:242` | `report4_fixups : wifi_pilot_fraction` | `convention_constants : wifi_pilot_fraction` |
| `src/make_report03_illuminators.py:245` | `report4_fixups : wifi_pilot_fraction` | `convention_constants : wifi_pilot_fraction` |
| `src/make_report03_illuminators.py:252` | `report4_fixups : cpi_asymmetry` | `convention_constants : cpi_asymmetry` |

⚠ **이름을 옮기기 전에 라벨을 바꾸면 그림이 없는 파일을 가리킨다.** 순서는 하나뿐이다 —
파일 이전(§5) → 라벨 4줄 수정 → 03편 빌더 재실행(그림이 다시 구워진다).

---

## 6. 이 문서를 언제 갱신하나

- 새 산출물을 만들 때 — §2 규칙으로 이름을 지으면 이 표에 올릴 일이 없다.
- 이름을 실제로 옮긴 뒤 — §1 표는 **남긴다**. 옛 태그를 읽는 사람이 계속 나온다.
- 리포트 편성이 또 바뀌면 — §1 의 "실제로 읽는 편" 열만 다시 센다(노트북 출처태그 count).

관련 문서: `docs/REPORT_CODE_MAP.md`(절 ↔ 코드 ↔ JSON 지도, §7.1 에 같은 표의 축약판) ·
`benchmark/regen_mesh_dependents.py --list`(생산 순서·소요의 진리원).
