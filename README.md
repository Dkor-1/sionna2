# sionna2 — 통신신호를 조명원 삼는 패시브 바이스태틱 드론 탐지 시뮬레이터

셀이 이미 켜 두는 상시 신호(WiFi · LTE · 5G NR)를 조명 삼아 드론을 탐지하는 패시브 바이스태틱
레이더를, Sionna RT 2.0.1 위에서 자유공간 기하로 끝까지 시뮬레이션한다. 표적 산란은 Sionna 의
Mitsuba/OptiX 광선엔진으로 면별 가림을 풀고 그 조명면 위에서 부품별 재질 PO 를 적분해 만든다.
σ 의 **주파수 의존성**은 공개 측정(Das)에 맞추고, **자세 패턴과 절대 레벨은 우리 PO 출력**이다.
표적 7종의 정본은 `src/drones.py` 의 `DRONES` 레지스트리이고, 리포트 본문의 숫자는 전부
`outputs/*.json` 에서 주입된다.

> 처음 왔다면 **`report01_prior.ipynb` → `report02_target.ipynb`** 순서로 읽는다.
> 어느 절이 어느 코드·JSON 에서 나왔는지는 **[`docs/REPORT_CODE_MAP.md`](docs/REPORT_CODE_MAP.md)** 한 파일에 다 있다.

---

## 이 저장소가 한 일

| 한 일 | 수치 |
|---|---|
| **광선엔진 안에서 산란을 적분한다** — Sionna 자체 Mitsuba/OptiX 로 first-hit 가림을 판정하고 조명면 위에서 부품별 재질 PO 를 적분한다 | `src/rcs_sbr.py:184` · `src/materials.py` |
| **커널을 기준해로 검증했다** — 해석 PO 구 대비 kr 1~100 전 구간, 입사 48방향 | 최대 **0.201 dB** ⟨`outputs/sbr_kr_sweep.json : summary_div16.max_abs_db_vs_po`⟩ |
| **다중반사 위상을 PEC 이면각 닫힌형 8πa²b²/λ² 와 맞췄다** — 변 길이 4점 | 최대 **0.556 dB** ⟨`outputs/sbr_defect_fixes.json : d3_multibounce_phase.max_abs_err_db`⟩ |
| **바이스태틱 출사 가시성을 넣었다** — 히트마다 수신기 방향으로 그림자 광선을 쏜다 | 상반성 위반 최악 21.15 → **13.69 dB** ⟨`…: d2_exit_vis_effect_on_reciprocity.worst_with_exit_vis_db`⟩ |
| **σ 의 주파수 기울기를 측정에 정렬했다** — σ = A(f)·B₁(φ,θ)·B₂ 에서 A(f) 의 **기울기만** Das 측정, **절대 레벨과 B₁ 은 우리 PO 출력** | **0.210 dB/GHz** ⟨`outputs/rcs_anchor.json : literature.mu_eps.multiband_phantom3.mu_a`⟩ · 평균 레벨이동 **0.00 dB** ⟨`outputs/report02_derived.json : anchor_modes.level_shift_abs_max_db`⟩ · 정규화 각패턴 이동 **1.9e-15 dB** ⟨`outputs/report02_derived.json : anchor.shape_invariance_max_abs_db`⟩ |
| **모드 선택의 대가를 수치로 적었다** — 레벨까지 앵커에 맞추려면 크기전이 법칙을 하나 골라야 하고, 그 선택 하나가 기체당 최대 이만큼을 정한다 | L² ↔ L⁴ 예측 차 최대 **9.50 dB** (DJI S1000+) ⟨`outputs/report02_derived.json : anchor_modes.size_law_spread_max_db`⟩ |
| **CFAR 를 경험 Pfa 로 교정했다** — GPU 몬테카를로로 오경보 셀을 직접 세었다 | **2717 s** ⟨`outputs/verify_cfar.json : meta.runtime_s`⟩, 명목 1e-4 에서 배율 1.52~2.66 |
| **세 파형을 한 표적·한 검출기로 비교했다** — 점유·대역·PRF·λ² 를 dB 원장으로 닫았다 | 점유 **18.0 dB** ⟨`outputs/report03_illuminators.json : occupancy_cost.value_db`⟩ |
| **기체 7종을 사진·제원에서 세우고 실물 CAD 와 맞댔다** | `outputs/real_cad_compare.json` · `community_compare.json` |
| **선행연구를 전문으로 판정했다** — 아카이브 PDF 41편 중 16편, 게재상태는 PDF 로 확정 | 드론 메쉬에서 산란을 계산한 게재본 **0편** ⟨`outputs/prior_census.json : funnel.all.g3_mesh_scattering`⟩ |

---

## 리포트 7편 — 한 편이 한 일 하나를 보고한다

전부 **생성물**이다. 서술을 고치려면 `src/make_report0N_*.py` 를 고치고 다시 돌린다.

| # | 노트북 | 이 편이 한 일 | 헤드라인 |
|---|---|---|---|
| 00 | [`report00_foundations.ipynb`](report00_foundations.ipynb) | Sionna RT 설치본을 인자 목록까지 해부해 광선이 면을 맞았을 때 무엇이 계산되는지를 적고, 표적 산란이 어디서부터 별도 항이 되는지를 결정표로 갈랐다 | 평판 면적 1600배에 PO σ 는 64.08 dB · path solver 진폭은 7.4e-07 dB ⟨`outputs/report00_evidence.json : A_plate_size_sweep.numbers`⟩ · 판별 기준 2문 결정표 |
| 01 | [`report01_prior.ipynb`](report01_prior.ipynb) | 선행 16편이 표적 서명을 어디서 조달했고 그 조달처가 무슨 주장을 사 주었는지 카탈로그로 만들었다 | 게재본 중 메쉬 산란 계산 0편, CFAR·false alarm 이 0회인 논문 13편 |
| 02 | [`report02_target.ipynb`](report02_target.ipynb) | 메쉬 7종의 σ 를 광선 가림 + 재질 PO 로 계산하고 그 **주파수 의존성**을 Das 측정에 정렬했다 | 해석 PO 대비 0.201 dB · 앵커 기울기 0.210 dB/GHz · 평균 레벨이동 0.00 dB |
| 03 | [`report03_illuminators.ipynb`](report03_illuminators.ipynb) | 상시 기준신호를 세 표준의 자원격자에서 세우고 조명원 선택의 대가를 dB 원장으로 닫았다 | 점유 18.0 dB · 5G SSB 무모호 속도 1.07 m/s · Sionna PHY 대조 NMSE −135.2 dB |
| 04 | [`report04_detector.ipynb`](report04_detector.ipynb) | 검출 사슬의 경험 Pfa 를 측정하고 세 파형의 CFAR 문턱을 그 값에 맞췄다 | 명목 1e-4 → 경험 배율 WiFi 1.53 · LTE 2.66 · 5G 1.52, 교정표 확정 |
| 05 | [`report05_results.ipynb`](report05_results.ipynb) | 같은 표적·기하·교정문턱에서 세 조명원의 검출거리를 앵커 σ 위에서 쟀다 | R90 3.69~11.10 km (5기종×3밴드) · 다중수신기 이득이 10log₁₀N 에 −0.11~+0.47 dB |
| 06 | [`report06_measurement.ipynb`](report06_measurement.ipynb) | X410 로 교정된 σ 를 얻는 세션 설계와 판정 기준을 수치로 고정했다 | 원거리장 최대 24.44 m · 교정구 반경 17.8 cm(**절대 레벨의 첫 측정 앵커**) · 기울기 판정 문턱 2.44 dB |

| 07 | [`report07_microdoppler.ipynb`](report07_microdoppler.ipynb) | 로터를 돌려가며 매 시간표본마다 다시 추적해, 무늬를 정하는 것이 **회전수·가림·자세** 임을 단일축으로 갈랐다 | 회전수가 같으면 반창 스펙트럼 상관 0.9966(시간에 안 변한다) → 흩뜨리면 0.7757 · 가림이 변조 깊이를 -8.69 dB · ⚠상시 신호로는 통과율까지만 보인다 |
헤드라인 칸의 수치는 각 편 **여는 블록**의 출처태그 붙은 값을 그대로 옮긴 것이다 — 원본과 그 JSON 키는 노트북에 있다.
06편이 다음 라운드의 계약서다 — 어느 측정이 어느 주장을 결판내는지 결정표로 적어 둔 편이다.

### 부록 — 동결(유효하고, 새 작업은 넣지 않는다)

| 위치 | 내용 |
|---|---|
| `report_mesh/` 8편 | 드론 메쉬 제작·검증 심화 가이드. 증거는 `report_mesh/outputs/mesh_verify.json` |
| `prior_work/` | 선행연구·오픈소스 조사 원자료. 01편 census 가 여기서 나온다 |
| `OPENSOURCE.md` | 오픈소스 대체 지도(RadarSimPy 교차검증 · OpenISAC X410 실측) |

---

## 재현

```bash
PY=~/.venvs/py312/bin/python
cd sionna2

# ① 계획 — 29단계 · 직렬 9.1 h · 단계마다 "어느 편 어느 절이 읽는가" 가 붙는다
PYTHONPATH=src:benchmark $PY benchmark/regen_mesh_dependents.py --list

# ② 고아 감사 — 리포트가 읽는 JSON 을 파이프라인이 전부 만드는지 검사한다
PYTHONPATH=src:benchmark $PY benchmark/regen_mesh_dependents.py --check

# ③ 전부 다시 만든다 (GPU)
PYTHONPATH=src:benchmark $PY benchmark/regen_mesh_dependents.py

# ③' 죽은 실행 재개 / 한 단계만
PYTHONPATH=src:benchmark $PY benchmark/regen_mesh_dependents.py --skip-done
PYTHONPATH=src:benchmark $PY benchmark/regen_mesh_dependents.py --stage 4

# ④ 노트북만 다시 조립 (계산 없음, 수 분)
for f in src/make_report0*.py; do PYTHONPATH=src:benchmark $PY "$f"; done
```

- 편당 재현 명령은 각 노트북의 **재현** 블록이 그대로 들고 있다 — 복붙하면 그 JSON 이 나온다.
- **GPU**: `src/gpu.py` 가 여유 큰 카드를 고른다(`SIONNA2_GPU=N` 으로 고정). 몬테카를로 규모는
  `SIONNA2_DET_K`, 배치는 `SIONNA2_DET_BATCH`.
- 가장 무거운 단계는 `benchmark/rcs_anchor.py` **11407 s** ⟨`outputs/rcs_anchor.json : meta.runtime_s`⟩ 이고,
  메쉬를 고쳐 σ 캐시가 무효화되면 `src/experiment_freespace_sigma.py` 가 시간 단위로 커진다(`--list` 가 경고한다).

---

## 숫자가 어디 사는가

```
outputs/*.json   ──읽음──▶  src/make_report0N_*.py  ──▶  report0N_*.ipynb
     ▲                          (표현층: 계산 없음)
     └── benchmark/*.py · src/viz_*.py · src/experiment_*.py   (계산층: 물리가 여기 있다)
```

- 본문의 모든 숫자에 **`값 ⟨outputs/xxx.json : key⟩`** 출처가 붙는다. `src/report_style.py` 의 `num()` 이
  JSON 을 열어 대조하고 어긋나면 빌드를 세운다 — 손으로 친 숫자는 통과하지 못한다.
- 절 단위 지도는 **[`docs/REPORT_CODE_MAP.md`](docs/REPORT_CODE_MAP.md)**.
- 재편 설계와 서술 규약은 **[`docs/REBUILD_2026-07-30.md`](docs/REBUILD_2026-07-30.md)** §5.
<!-- keep-old-names:on -->
- 태그에 `report13_*` · `report5_results.json` 처럼 **은퇴한 13편 번호**가 보이면
  **[`docs/OUTPUT_NAMING.md`](docs/OUTPUT_NAMING.md)** §1 에서 한 번에 푼다
  (`report5_results.json` 을 읽는 편은 05편이 아니라 03편이다).
<!-- keep-old-names:off -->

---

## 별도 주제 — 코드는 그대로 있다

| 주제 | 코드 | 되살리기 |
|---|---|---|
| 반무향 챔버 환경 | `src/chamber.py` · `benchmark/verify_clutter_doppler.py` · `benchmark/run_matrix.py --only b,c,d,e` | `regen_mesh_dependents.py --dropped` 가 명령을 찍는다 |
| 바닥 유령 표적 | `benchmark/verify_floor_ghost.py` · `verify_ghost_impact.py` · `src/experiment_ghost.py` | 〃 |
| 마이크로도플러 | `src/microdoppler.py` · `microdoppler_nearfield.py` · `experiment_md_range.py` · `viz_report1.py --only md` | 〃 (future work) |

`_legacy_reports/` 와 `src/_legacy_builders/` 에 구 리포트 13편과 그 빌더가 읽기전용으로 남아 있다.

---

## 저장소 구조

```
report0N_*.ipynb        본편 6편 (생성물)
report_mesh/            부록 8편 (동결)
prior_work/             선행연구 조사 원자료
_legacy_reports/        구 리포트 13편 (퇴역·읽기전용)

src/
  make_report0N_*.py    ⭐리포트 생성기 — 서술 원본. 계산은 없다
  report_style.py       리포트 규약 강제(num()·출처태그·분량 상한·부정문 계수)
  provenance.py         리포트 앞머리 provenance 블록
  drones.py             ⭐표적 레지스트리 DRONES — 기종 목록·제원의 유일한 출처
  drone_cad.py cadkit.py geom.py     파라메트릭 CAD(trimesh+manifold3d)
  materials.py          ⭐전파재질 단일 진리원 — Sionna RT 와 PO 가 둘 다 여기서 읽는다
  rcs_sbr.py            ⭐SBR+PO 커널 (Mitsuba 광선조준 + PO 표면적분, 가림·투과·출사 가시성)
  sigma_anchor.py       ⭐측정 앵커 재보정 σ=A(f)·B₁·B₂ + 미통제 항 원장
                        생산 모드 `slope_only` = 기울기만 측정에서, 레벨은 우리 PO 출력
  waveforms*.py         WiFi/LTE/5G OFDM 합성 + Sionna PHY 대조
  passive_process.py    패시브 DSP: ECA → CAF 거리도플러 → CA-CFAR(교정표 적용)
  experiment_*.py       검출·자유공간 실험(GPU 몬테카를로)
  viz_*.py              그림 (텍스트는 전부 영어)
  _legacy_builders/     구 빌더 13개 (퇴역·실행 금지)

benchmark/
  regen_mesh_dependents.py  ⭐재생성 파이프라인 — 무엇을 어느 순서로 돌리나
  channel.py            σ 조회 단일 진리원 + 메쉬지문 캐시
  mie_pec_sphere.py     기준해 두 개(정확 Mie · 해석 PO) — 커널의 과녁
  verify_*.py           검증 하네스 (리포트가 읽는 verify_*.json 생산)
  rcs_anchor.py         σ 절대앵커·분포적합
  prior_census.py       선행연구 census + 01편 그림 4장
  plan_measurement.py   실측 설계값 (06편)

  rename_outputs.py     옛 13편 번호 산출물 이름 이전 (예행이 기본)

outputs/                *.json(숫자의 원본) · figures/ · renders/
docs/                   REPORT_CODE_MAP.md · OUTPUT_NAMING.md · REBUILD_2026-07-30.md ·
                        MEASUREMENT_PLAN.md · SPECS.md
```

---

## 환경

| | |
|---|---|
| Python | `~/.venvs/py312/bin/python` (3.12) — 이 한 env 로 전부 실행 |
| 핵심 | Sionna RT 2.0.1 · Mitsuba 3.8.0 · drjit 1.3.1 (OptiX GPU) · torch · numpy · trimesh + manifold3d |
| 노트북 커널 | `py312` |
| 실행 규약 | `PYTHONPATH=src:benchmark` 를 반드시 준다 |

## 하우스 규약

- 그림 텍스트(제목·축·범례·주석)는 **영어**, 본문·주석·print 는 **한국어**.
- 리포트는 **한 일**을 쓴다 — 각 편은 `한 일 / 결과 / 방법 / 재현 / 앞 편에서` 5블록으로 열고
  `다음 단계` 표(`다음에 할 일 | 그러면 결정되는 것 | 어디서`)로 닫는다.
- 불확실한 양은 **표에 수치로** 넣는다. 범위는 조건절로 쓴다 — "β ≤ 45° 에서 성립한다".
- 분량 상한: 편당 마크다운 25셀 · 셀당 12줄 · 편당 그림 8장. `src/report_style.py` 가 검사한다.
