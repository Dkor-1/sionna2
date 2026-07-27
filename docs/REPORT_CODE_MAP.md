# 리포트 코드-경로 인덱스 (REPORT_CODE_MAP)

리포트 01~12의 **각 생성 내용이 어느 파이썬 파일에서 나오는지**를 추적하는 지도.
2026-07-21 작성(임포트·출력 json 생산자 자동 추적 + 수기 검증).

## 파이프라인 구조 (중요)

```
report0N.ipynb  ◀── src/make_notebook0N.py   [표현층: provenance import + outputs/*.json 읽어 마크다운/표 조립]
                         └── outputs/<name>.json  ◀── src/<producer>.py  [계산층: 실제 물리·시뮬·검증이 여기]
                                                          └── 핵심 계산모듈(rcs_sbr, materials, drones, ...)
```

- **`make_notebook0N.py` 자체엔 물리 계산이 (거의) 없다** — provenance 박스 + 미리 계산된 `outputs/*.json` 을 읽어 그림·표·서술로 조립할 뿐.
- **진짜 코드**는 그 json 을 **쓰는 생산 스크립트**(`viz_*.py`, `experiment_*.py`, `passive_process.py`)와 그들이 부르는 **핵심 계산모듈**에 있다.
- 모든 리포트 공통 provenance/용어집: **`src/provenance.py`**.

---

## 리포트별 지도

| 리포트 | 주제 | 생성기 | 읽는 데이터(outputs/) | 데이터 생산 스크립트 | 핵심 계산모듈 |
|---|---|---|---|---|---|
| **01** | 챔버 30×20×11 · 바닥반사 | `make_notebook01.py` | `report1.json`, `report3_rt.json` | `viz_report1.py`, `viz_report3.py` | `chamber.py` `scene_build.py` `bistatic_scene.py` `render_rt.py` |
| **02** | 드론 3D 모델·RCS 개관 | `make_notebook02.py` | `report1.json`, `mesh_verify.json`(부록 report_mesh 인용) | `viz_report1.py`, `viz_report2.py` | `drones.py` `drone_cad.py` `geom.py` `materials.py` `rcs_sbr.py` `rcs_po.py` |
| **03** | 실물 CAD 대조 | `make_notebook03.py` | `community_compare.json`, `phantom4_scan_compare.json`, `real_cad_compare.json` | `compare_phantom_scan.py`, `viz_report3_cad.py`, `viz_report3_compare_all.py`, `viz_report3_overlay.py`, `viz_report3_phantom_scan.py` | `drones.py` `geom.py` `mesh_compare.py` `trimesh` |
| **04** | 조명원·파형(WiFi/LTE/5G) | `make_notebook04.py` | `report2_waveform_rcs.json`, `waveform_research.json` | `viz_report2.py` | `waveforms.py` `waveforms_sionna.py` `rcs_sbr.py` |
| **05** | 파형 검증(Sionna PHY 대조) | `make_notebook05.py` | `report2_waveform_rcs.json` | `viz_report2.py` | `waveforms.py` `waveforms_sionna.py` `sionna_chain.py` |
| **06** | RCS·Sionna 한계(5실증) | `make_notebook06.py` | `report3_rt.json`, `rt_no_rcs_verify.json`, `rt_ray_budget.json`, **`report2_waveform_rcs.json`**(재질별 σ 분해) | `viz_report3.py`, `viz_verify_rt.py`, `viz_verify_sbr.py` | `rcs_sbr.py` `rcs_po.py` `radar_scene.py` `materials.py` |
| **07** | SBR(우리 방식) | `make_notebook07.py` | `mesh_verify.json`(인용), `report2_waveform_rcs.json`, `report6_sbr.json` | `viz_report2.py`, `viz_verify_sbr.py` | `rcs_sbr.py` `rcs_po.py` `drones.py` `materials.py` |
| **08** | RCS 결과 | `make_notebook08.py` | `mesh_verify.json`(인용), `report1.json`, `report2_waveform_rcs.json` | `viz_report1.py`, `viz_report2.py` | `rcs_sbr.py` `materials.py` `drones.py` |
| **09** | 바닥유령(clutter) | `make_notebook09.py` | `floor_ghost_verify.json`, `verify_pyapril.json` | `experiment_ghost.py`, `viz_verify_clutter.py` | `passive_process.py` `detection_gpu.py` `sionna_chain.py` `rcs_po.py` |
| **10** | CFAR 교정 | `make_notebook10.py` | `verify_cfar.json`, `verify_pyapril.json` | `passive_process.py`, `viz_report4.py` | `passive_process.py`(ECA/CAF/CFAR) `waveforms.py` |
| **11** | 저속·분해능·관측성 | `make_notebook11.py` | `verify_ambiguity.json`, `verify_cfar.json`, `verify_eca.json`, `verify_linkbudget.json`, `verify_observability.json`, `verify_pyapril.json` | `viz_report4.py`, `passive_process.py` | `passive_process.py` `waveforms.py` |
| **12** | 검출 벤치마크 결과 | `make_notebook12.py` | `detection_rx_sweep.json`, `report2_waveform_rcs.json`(방위평균 σ 인용) | `experiment_detection.py`, `anim_plots.py` | `detection_gpu.py` `experiment_x410.py` `passive_process.py` `sionna_chain.py` `rcs_po.py` |

---

## 핵심 계산모듈 레퍼런스 (src/)

### 기하·메쉬 (드론 CAD)
- **`drones.py`** — 5기종 `DroneSpec`(공식제원·envelope) + `build_drone/build_frame/rotor_layout/drone_gamma_map`. 재질매핑 `DRONE_GROUP_MAT`.
  - ⚠ `envelope_mm` 의 **의미가 기종마다 다르다** — `env_props_included=True`(Mini 5 Pro)면 공식 높이가
    **프롭 포함**이라 `frame_fit_scale` 이 프레임이 아니라 **전체 드론**을 그 값에 맞춘다. 나머지 4종은 프롭 제외.
  - `frame_envelope_mm()` 은 `lwh_mm`(프레임)·`lwh_full_mm`(전체)·`lwh_compare_mm`(공식과 견줄 값)·
    `prop_disc_lw_mm`(회전 디스크 외곽 — 프롭포함 공식 L/W 와 견줄 유일하게 옳은 값)을 함께 낸다.
- **`drone_cad.py`** — 부품 CAD 빌더(`_gimbal_*`·`_fisheye`·`_lidar`·`_gear_*`·`_blade`(NACA-4 익형)·`_body_folding` 등, trimesh+manifold3d).
- **`geom.py`** — `Mesh` 클래스(정점/면/그룹, `merge`·`transformed`·`write_obj_per_group`).
- **`chamber.py`** — 무향실 30×20×11 m 지오메트리.
- **`mesh_check.py`** — 부품별 mesh 검진(watertight·winding·법선·퇴화면, `check_all`/`assert_ok`).
- **`mesh_compare.py`** — 실물 CAD/스캔 대조.

### 전자기·RCS
- **`materials.py`** — ⭐재질 **유일 진리원**. `MATERIALS`(ITU/PO 물성) + `gamma_po`(PO 반사계수 |Γ|). Sionna RT(전파)와 PO(RCS)가 **둘 다 여기서 읽음**.
- **`rcs_sbr.py`** — ⭐**SBR+PO** RCS(Mitsuba 광선으로 조명면·가림 → PO 표면적분).
  `rcs_sbr_batch`/`rcs_sbr`(모노스태틱 σ) · `sbr_field`(복소장 E) · **`rcs_sbr_multistatic`(바이/멀티스태틱 σ —
  입사·산란 방향을 따로 받고 조명패스를 재사용)** · `validate`. 전부 `penetrate=True`(유전체 셸 투과) 기본.
  - ⚠ **엔진은 바이스태틱을 하지만 파이프라인은 아직 모노스태틱 등가로 조회한다** — `benchmark/channel.py`
    의 `look_angles` 가 이등분선 û=(û₁+û₂)/|·| 로 **등가 모노스태틱** 시선을 만들어 σ 를 뽑는다.
    엔진의 바이스태틱 경로를 파이프라인에 태우는 것은 열린 과제다.
- **`rcs_po.py`** — 레거시 PO(numpy 점구름). 비교·검증용.

### Sionna RT 장면(전파)
- **`scene_build.py`** — `Part`→Sionna 장면 조립(`build_scene`), `drone_parts`/`chamber_parts`(`_scene/*.obj` export).
- **`radar_scene.py`** — 모노스태틱 레이더 장면·채널(report2).
- **`bistatic_scene.py`** — 바이스태틱 장면(TX/RX/TGT 배치).
- **`render_rt.py`/`render_anim.py`/`render_drones.py`** — Mitsuba 렌더·GIF.

### 신호·파형·검출
- **`waveforms.py`/`waveforms_sionna.py`** — WiFi/LTE/5G 파형(자작 + Sionna PHY 대조).
- **`sionna_chain.py`** — Sionna PHY 에코 채널(`cir_to_time_channel` 지연커널).
- **`microdoppler.py`** — 프롭 회전 마이크로도플러.
- **`passive_process.py`** — ⭐패시브 DSP: ECA(직접경로 제거)·CAF(교차상관)·CFAR.
- **`detection_gpu.py`** — GPU 배치 검출 몬테카를로.
- **`experiment_detection.py`/`experiment_x410.py`** — 검출 벤치 실험(X410 실측 파라미터 포함).
- **`experiment_ghost.py`** — 바닥유령 실험.

### 벤치마크 계산층 (benchmark/)
- **`channel.py`** — ⭐σ 조회의 단일 진리원. `look_angles`(바이스태틱 등가 시선) + `sigma_sbr_cache.json`
  디스크 캐시 + `sbr_sigma_prefill`(여러 GPU 분배). 워커는 조회만 하고, 미스면 **큰 소리로 실패**한다.
  - ⚠ 캐시 키에 **메쉬 지문**(`_mesh_fp`, md5 8자)이 들어간다 — 없으면 CAD 를 고쳐도 옛 σ 를 조용히
    재사용해 링크버짓·SCR·Pd 가 전부 옛 형상 위에 얹힌다. 메쉬를 고치면 캐시는 저절로 무효화된다.
- **`verify_linkbudget.py`** → `verify_linkbudget.json` (report11) · **`report4_fixups.py`** → `report4_fixups.json`
- **`run_matrix.py`** → `report5_results.json` · **`verify_floor_ghost.py`** → `floor_ghost_verify.json`

### 공통·인프라
- **`provenance.py`** — ⭐모든 리포트 공통 provenance 박스·용어집(🟢Sionna내부/🟡우리PO/🔴별도 분류, SBR/PO 정의).
- **`gpu.py`** — 여유메모리 기준 GPU 선택(`pick`).
- **`vizstyle.py`** — 그림 스타일(영어 라벨 규약).

---

## 감사 플래그 (2026-07-21 제기 → 2026-07-22 **둘 다 해소**)

1. ~~`mesh_verify.json` 부재~~ → **실재한다**: `report_mesh/outputs/mesh_verify.json` (27 kB).
   report02/07/08 의 참조는 `json.load` 가 아니라 **본문 각주 인용**이다(부록 report_mesh 소관 데이터를
   본문에서 근거로 가리키는 것). 애초에 `outputs/` 만 훑어서 생긴 오탐.
2. ~~`verify_pyapril.json` 생산자 불명~~ → **`benchmark/verify_pyapril.py`** 가 생산자다.
   `src/` 만 검색해서 생긴 오탐 — 벤치마크 계산층은 `benchmark/` 에 산다(위 절 참고).

> 교훈: 생산자 추적은 `src/` 뿐 아니라 **`benchmark/` 와 부록 `report_mesh/`** 까지 훑어야 한다.

### 3. 진짜 고아 1건 — `outputs/report3_microdoppler.json` (2026-07-22 정리)
리포트 재편 때 옛 report3 가 사라지면서 **생산자가 없어진 산출물**인데, `viz_verify_sbr.fig_sbr` 이
report06 그림의 마이크로도플러 headline 을 계속 거기서 읽고 있었다 → **메쉬·엔진을 고쳐도 그림 속
숫자만 옛날 값에 고정**되는 조용한 stale 경로. 살아있는 생산자
(`viz_report1.measure_microdoppler` → `report1.json["microdoppler"]["drones"]["mavic4pro"]`)로 갈아끼우고,
옛 파일은 `_orphan_report3_microdoppler.json.bak` 으로 퇴역시켰다.

> 고아 판별법: **읽기만 하고 아무도 안 쓰는 json** 을 찾을 것 —
> `grep -rn "<name>.json" --include=*.py .` 결과에 `json.dump`/`open(...,"w")` 가 하나도 없으면 고아다.
