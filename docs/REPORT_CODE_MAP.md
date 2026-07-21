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
| **02** | 드론 3D 모델·RCS 개관 | `make_notebook02.py` | `report1.json`, ⚠`mesh_verify.json` | `viz_report1.py`, `viz_report2.py` | `drones.py` `drone_cad.py` `geom.py` `materials.py` `rcs_sbr.py` `rcs_po.py` |
| **03** | 실물 CAD 대조 | `make_notebook03.py` | `community_compare.json`, `phantom4_scan_compare.json`, `real_cad_compare.json` | `compare_phantom_scan.py`, `viz_report3_cad.py`, `viz_report3_compare_all.py`, `viz_report3_overlay.py`, `viz_report3_phantom_scan.py` | `drones.py` `geom.py` `mesh_compare.py` `trimesh` |
| **04** | 조명원·파형(WiFi/LTE/5G) | `make_notebook04.py` | `report2_waveform_rcs.json` | `viz_report2.py` | `waveforms.py` `waveforms_sionna.py` `rcs_sbr.py` |
| **05** | 파형 검증(Sionna PHY 대조) | `make_notebook05.py` | `report2_waveform_rcs.json` | `viz_report2.py` | `waveforms.py` `waveforms_sionna.py` `sionna_chain.py` |
| **06** | RCS·Sionna 한계(5실증) | `make_notebook06.py` | `report3_rt.json`, `rt_no_rcs_verify.json`, `rt_ray_budget.json` | `viz_report3.py`, `viz_verify_rt.py`, `viz_verify_sbr.py` | `rcs_sbr.py` `rcs_po.py` `radar_scene.py` `materials.py` |
| **07** | SBR(우리 방식) | `make_notebook07.py` | ⚠`mesh_verify.json`, `report2_waveform_rcs.json`, `report6_sbr.json` | `viz_report2.py`, `viz_verify_sbr.py` | `rcs_sbr.py` `rcs_po.py` `drones.py` `materials.py` |
| **08** | RCS 결과 | `make_notebook08.py` | ⚠`mesh_verify.json`, `report1.json`, `report2_waveform_rcs.json` | `viz_report1.py`, `viz_report2.py` | `rcs_sbr.py` `materials.py` `drones.py` |
| **09** | 바닥유령(clutter) | `make_notebook09.py` | `floor_ghost_verify.json`, ⚠`verify_pyapril.json` | `experiment_ghost.py`, `viz_verify_clutter.py` | `passive_process.py` `detection_gpu.py` `sionna_chain.py` `rcs_po.py` |
| **10** | CFAR 교정 | `make_notebook10.py` | `verify_cfar.json`, ⚠`verify_pyapril.json` | `passive_process.py`, `viz_report4.py` | `passive_process.py`(ECA/CAF/CFAR) `waveforms.py` |
| **11** | 저속·분해능·관측성 | `make_notebook11.py` | `verify_ambiguity.json`, `verify_cfar.json`, `verify_eca.json`, `verify_linkbudget.json`, ⚠`verify_pyapril.json` | `viz_report4.py`, `passive_process.py` | `passive_process.py` `waveforms.py` |
| **12** | 검출 벤치마크 결과 | `make_notebook12.py` | `detection_rx_sweep.json` | `experiment_detection.py`, `anim_plots.py` | `detection_gpu.py` `experiment_x410.py` `passive_process.py` `sionna_chain.py` `rcs_po.py` |

---

## 핵심 계산모듈 레퍼런스 (src/)

### 기하·메쉬 (드론 CAD)
- **`drones.py`** — 5기종 `DroneSpec`(공식제원·envelope) + `build_drone/build_frame/rotor_layout/drone_gamma_map`. 재질매핑 `DRONE_GROUP_MAT`.
- **`drone_cad.py`** — 부품 CAD 빌더(`_gimbal_*`·`_fisheye`·`_lidar`·`_gear_*`·`_blade`(NACA-4 익형)·`_body_folding` 등, trimesh+manifold3d).
- **`geom.py`** — `Mesh` 클래스(정점/면/그룹, `merge`·`transformed`·`write_obj_per_group`).
- **`chamber.py`** — 무향실 30×20×11 m 지오메트리.
- **`mesh_check.py`** — 부품별 mesh 검진(watertight·winding·법선·퇴화면, `check_all`/`assert_ok`).
- **`mesh_compare.py`** — 실물 CAD/스캔 대조.

### 전자기·RCS
- **`materials.py`** — ⭐재질 **유일 진리원**. `MATERIALS`(ITU/PO 물성) + `gamma_po`(PO 반사계수 |Γ|). Sionna RT(전파)와 PO(RCS)가 **둘 다 여기서 읽음**.
- **`rcs_sbr.py`** — ⭐**SBR+PO** RCS(Mitsuba 광선으로 조명면·가림 → PO 표면적분). `sbr_field`(복소장 E)·`rcs_sbr`(σ)·`validate`. **현재 모노스태틱 전용**.
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
- **`experiment_detection.py`/`experiment_x.py`/`experiment_x410.py`** — 검출 벤치 실험(X410 실측 파라미터 포함).
- **`experiment_ghost.py`** — 바닥유령 실험.

### 공통·인프라
- **`provenance.py`** — ⭐모든 리포트 공통 provenance 박스·용어집(🟢Sionna내부/🟡우리PO/🔴별도 분류, SBR/PO 정의).
- **`gpu.py`** — 여유메모리 기준 GPU 선택(`pick`).
- **`vizstyle.py`** — 그림 스타일(영어 라벨 규약).

---

## ⚠ 감사 플래그 (2026-07-21 발견 — 추후 확인)

1. **`outputs/mesh_verify.json` 이 실제로 없다.** report02/07/08 이 읽지만 `outputs/` 에 파일이 부재하고 생산 스크립트도 추적 안 됨 → **stale 참조 의심**. 생성기가 없을 때 어떻게 처리하는지(graceful? 빈값?) 확인 필요.
2. **`outputs/verify_pyapril.json` 은 존재(1247 B, keys=meta/modes)하나 생산 스크립트가 src 에 없다.** report09/10/11 이 읽음. 생산 코드가 삭제됐거나 외부에서 생성 → **재현 경로 불명**, 생산자 복원 필요.

> 이 두 항목은 리포트 1~12 전체 코드 감사에서 우선 확인 대상이다.
