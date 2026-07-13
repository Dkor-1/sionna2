# sionna2 — 대형 차폐시설 & DJI 드론 5종

처음부터 **단순하고 투명하게** 다시 만든 작업 공간입니다.
딱 두 가지만 다룹니다: **① 대형 차폐시설(전파무반사실)** 과 **② DJI 드론 5종**.
그리고 **그림으로 최대한 많이** 보여줍니다.

> 먼저 볼 것 (커널 없이도 그림이 보임):
> - **[`report1.ipynb`](report1.ipynb)** — 1단계: 환경 세팅 (차폐시설 + 드론 5종)
> - **[`report2.ipynb`](report2.ipynb)** — 2단계: 레이더 구성 & RCS 특성화 (WiFi·LTE·5G 비교)
> - **[`report3.ipynb`](report3.ipynb)** — 3단계: 분절 드론 + 마이크로-도플러 (+ PX4 연동 가능성)
> - **[`report4.ipynb`](report4.ipynb)** — 4단계: **무반사 챔버 내부** 바이스태틱 패시브 레이더 **탐지**(ECA·CAF·CFAR·Pd/Pfa)
> - **[`report5.ipynb`](report5.ipynb)** — 5단계: **공정 벤치마크** — 링크버짓(EIRP·kTB·PO-RCS)으로 SNR 을 유도하고 SCR·Pd 는 측정(점유·신호×드론·시나리오·RT 교차검증)
>
> ※ **모든 실험은 30×20×11 m 무반사 차폐시설(챔버) 안에서** 진행합니다. report4 도 챔버 양쪽 벽에 신호원 TX·
> 패시브 RX 를 놓고 quiet zone 의 드론을 탐지합니다(베이스라인 L≈15 m, Rb 수~수십 m). 무반사라 클러터가 약해
> ECA 는 주로 직접파(DPI)를 제거하고, 좁은 챔버라 거리분해능(대역폭)이 탐지 성패를 좌우합니다.

---

## 한 번에 전부 만들기

```bash
PY=/home/yunjung/.venvs/py312/bin/python
cd sionna2/src
CUDA_VISIBLE_DEVICES=2 $PY build_all.py             # 메쉬+도면+GIF+렌더 전부 (GPU 2번 사용)
CUDA_VISIBLE_DEVICES=2 $PY build_all.py --no-render # 렌더 빼고 빠르게
```

생성물은 `outputs/figures/`(도면·그래프·GIF) 와 `outputs/renders/`(Sionna 렌더 PNG) 에 쌓입니다.

---

## 만든 것

### 1) 대형 차폐시설 — 30 m × 20 m × 11 m
사진 그대로: 🔺피라미드 전파흡수체(4면 벽+천장) · 🧱금속 차폐벽 · ▦체커보드 바닥 ·
🟦파란 트림 · 🏗️강철 골조 · 🚪출입문 2개. 흡수체가 전파를 가둬 **메아리 없는(무반사)** 공간을 만듭니다.

### 2) DJI 드론 5종 — 실측 제원 기반
| 드론 | 출시상태 | 로터 | 대각거리 | 무게 | 프로펠러 |
|---|---|---|---|---|---|
| **Mini 5 Pro** | 출시(2025) | 4 | ~250 mm* | 249.9 g | Ø152 mm ×2 |
| **Mavic 4 Pro** | 출시(2025) | 4 | ~400 mm* | 1063 g | Ø267 mm ×2 |
| **Matrice 4E** | 출시(2025) | 4 | 438.8 mm | 1219 g | Ø274 mm ×2 |
| **S1000+** | 단종(2014) | **8** | 1045 mm | 4400 g† | Ø381 mm ×2 |
| **Phantom 4** | 출시(2016) | 4 | 350 mm | 1380 g | Ø239 mm ×2 |

\* 대각거리는 DJI 비공개라 외형에서 추정한 값입니다(Mini 5 Pro 는 외형에서 ±20 mm, Mavic 4 Pro 는 Mavic 3 의 380.1 mm 와 언폴드 치수에서 추정).
무게·언폴드 치수·프로펠러 지름 등은 공식 제원입니다.
† S1000+ 의 4400 g 은 **기체(airframe) 자중**입니다 — 권장 이륙중량은 6.0~11.0 kg(대표 ~9.5, 최대 11). 나머지 4종은 이륙중량(TOW) 기준.
(원자료·근거: `docs/drone_research.json`, `docs/SPECS.md`).

---

## 시각화 결과물 (outputs/)

| 파일 | 내용 |
|---|---|
| `figures/chamber_schematic.png` | 시설 평면도+입면도(치수) |
| `figures/size_compare.png` | 5종 같은 축척 크기 비교 + 막대그래프 |
| `figures/card_<드론>.png` | 드론별 상세 카드(3D+도면+제원) ×5 |
| `figures/turntable_<드론>.gif`, `turntable_all.gif` | 회전 애니메이션 |
| `figures/catalog.png`, `facility_views.png` | 렌더 카탈로그/시설뷰 모음 |
| `renders/studio_<드론>.png` | 드론 단독 스튜디오 렌더 ×5 |
| `renders/facility_hero.png`, `facility_corner.png` | 차폐시설 렌더 |
| `renders/lineup_floor.png`, `flight_scene.png` | 드론이 들어간 시설 장면 |

---

## 코드 구조 (`src/`, 전부 한글 주석)

> ⚠️ **`reportN.ipynb` 는 전부 생성물이다.** 서술(마크다운) 수정은 `src/make_notebook*.py`,
> 그림 수정은 `src/viz_*.py` / `src/build_report*.py` 에서 한다.
> `build_all.py`(report1) 와 `build_report2~5.py` 가 대응 `make_notebook*.py` 를 자동 호출해 노트북을
> 덮어쓰므로, `.ipynb` 를 직접 고치면 다음 빌드에서 사라진다.

```
geom.py         삼각형으로 3D 도형 만드는 미니 도구 (외부 의존성 없음)
chamber.py      차폐시설 모델
drones.py       드론 5종 실측 제원 + 파라메트릭 생성기
materials.py    Sionna 전파재질(금속/콘크리트/흡수체/플라스틱/카본)
scene_build.py  부위 OBJ → Sionna 장면 조립 + 렌더 엔진
vizstyle.py     matplotlib 공통 스타일(한글 폰트 등록·출시상태 배지 색)
viz_diagram.py  도면식 그림(matplotlib)
viz_anim.py     회전 GIF
render_drones.py Sionna 사진풍 렌더
viz_montage.py  렌더 모아 카탈로그
build_all.py    한 번에 전부 생성 (report1)
make_notebook.py report1.ipynb 생성기 — 서술(마크다운) 원본
--- report2 (레이더) ---
radar_scene.py  모노스태틱 장면 + Sionna RT 채널/클러터 + 원거리장 점검
rcs_po.py       물리광학(PO) RCS — 평판·구 이론 검증 + 부위별 |Γ| 재질 가중(drones.GROUP_GAMMA)
                ·내부 금속 산란체(배터리/PCB)
prep_cad_scan.py 실기체 3D 스캔 STL(Thingiverse 1456295, CC-BY) → PO 점군 전처리
                (1회 오프라인; 산출물 assets/meshes/cad/phantom4_scan_points.npz 는 저장소 포함)
waveforms.py    실제 OFDM 파형 합성 + 점유모드 G1/G2/G3 (WiFi/LTE/5G, PRS·SSB·CRS·DMRS 라벨)
radar_process.py 에코 생성 + 정합필터(FFT) + RCS 추정 + 패시브(파일럿만) 처리
viz_radar.py    RCS/파형/거리프로파일 시각화
viz_occupancy.py 리소스 그리드 '사진' + 점유 상태 실험(거리×속도 두 축)
viz_mesh.py     메쉬 기반 실험 시각화 — 셋업 3D·RCS '풍선'·조명면·도플러
build_report2.py report2 산출물 한 번에 생성
make_notebook2.py report2.ipynb 생성기 — 서술(마크다운) 원본
--- report3 (분절 + 마이크로도플러) ---
drones.py       (분절 추가) build_frame/build_propeller/rotor_layout/pose_articulated
                — 몸체 RPY ⟂ 로터별 스핀 (build_drone 출력 동일·호환)
microdoppler.py 회전 블레이드 마이크로도플러 — PO 복소장 E(t) + 스펙트로그램
viz_articulation.py 분절 검증 도면 + 마이크로도플러 + 회전 GIF
build_report3.py report3 산출물 한 번에 생성
make_notebook3.py report3.ipynb 생성기 — 서술(마크다운) 원본
--- report4 (바이스태틱 탐지) ---
bistatic_scene.py 바이스태틱 기하 (Rb·τ·f_d·β, 등Rb 타원)
passive_process.py 처리 체인 — make_cpi/ECA(클러터제거)/CAF 거리-도플러/CA-CFAR
viz_bistatic.py 기하·거리도플러맵(ECA 전후)·검출성능(Pd vs SNR)·추적 GIF 시각화
build_report4.py report4 산출물 한 번에 생성
make_notebook4.py report4.ipynb 생성기 — 서술(마크다운) 원본
--- report5 (공정 벤치마크; 하네스는 ../benchmark/) ---
build_report5.py  benchmark 하네스(최소셀→매트릭스 A~D)를 실행하고 report5.ipynb 생성
make_notebook5.py report5.ipynb 생성기 — outputs/report5_results.json 의 실측 수치를 읽어 삽입
--- 애니메이션(GIF) ---
viz_animations.py RCS 글린트(report2)·마이크로도플러 회전(report3)·점유 진행(report2)
build_animations.py 위 실험 애니메이션 한 번에 생성
```

### 벤치마크 하네스 (`benchmark/`, report5 의 실험 코드)

```
geometry.py     챔버 내 TX/RX/quiet-zone 배치 + RD 거리창 환산(chamber_window)
link_budget.py  바이스태틱 레이더 방정식 + Friis + kTB — 에코/직접파 SNR 을 물리로 유도
channel.py      채널 백엔드 스왑: AnalyticChannel(기하+PO) ↔ SionnaRTChannel(RT 멀티패스, GPU)
scenarios.py    통제 모션 4종(radial/tangential/hover/waypoint) — 전 신호·드론 공통
run_min_cell.py 최소 셀 1개 + 고속 Monte-Carlo(run_cell) — "SCR is measured, not swept"
run_matrix.py   본 실험: 점유(A)·신호×드론(B)·시나리오(C)·RT 교차검증(D) → 그림/CSV/JSON
verify_server.py RT 백엔드 진단·교차검증 단독 실행기
```

**애니메이션 GIF 모음** (커널 없이 노트북에서 재생):
turntable(드론 회전)·report3_articulation(분절 회전)·report4_tracking(비행 추적),
report2_anim_rcs(RCS 글린트)·report3_anim_microdoppler(프로펠러↔플래시)·report2_anim_occupancy(점유 진행).

### report2~5 한 번에 만들기
```bash
cd sionna2/src
$PY build_report2.py                          # GPU 불필요(PO+DSP)
$PY build_report3.py                          # GPU 불필요(메쉬+PO+DSP)
$PY build_report4.py                          # GPU 불필요(기하+DSP)
$PY build_animations.py                       # 실험 애니메이션 GIF(GPU 불필요, 느림)
CUDA_VISIBLE_DEVICES=2 $PY build_report5.py   # 벤치마크(D 섹션 Sionna RT 가 GPU 1장 사용)
```

설계 원칙: **OBJ 1개 = 부위 1개 = Sionna 재질 1개.** 그래서 부위별로 색/전파재질을
따로 줄 수 있고, 나중에 광선추적(RT) 시뮬레이션에 바로 쓸 수 있습니다.

## 환경 (단일 env: py312)
- Python: `/home/yunjung/.venvs/py312/bin/python` — **3.12.13**.
  DSP/PO/시각화(numpy·scipy·matplotlib) + **Sionna RT 2.0.1 / mitsuba 3.8.0 / drjit 1.3.1**
  (OptiX GPU 광선추적·렌더 동작 확인) 까지 **이 한 env 로 전부** 실행됩니다.
- VSCode 노트북은 커널 **py312** 선택. 추가 설치 불필요.

## 진행 상황 & 다음 단계
- ✅ **report1** 환경 세팅(차폐시설+드론)
- ✅ **report2** 모노스태틱 RCS + WiFi/LTE/5G 비교 + 점유모드(G1/G2/G3, 거리×속도 두 축) + 메쉬 실험 시각화
  + 재질 가중 PO(방위평균 약 2~6 dB↓)·공개 실측 문헌 앵커링·실기체 3D 스캔 형상 A/B(+0.7~2.8 dB)
  + **상시 기준신호(LTE CRS vs 5G SSB) 중심 비교** — PRS 는 측위 세션에서만 켜지는 옵션으로 분리
- ✅ **report3** 분절 드론(몸체 RPY ⟂ 로터별 스핀) + 회전 블레이드 마이크로-도플러 + PX4/Gazebo 연동 가능성 검증
- ✅ **report4** 바이스태틱 패시브 레이더 탐지: ECA 클러터제거 → CAF 거리-도플러 → CFAR → Pd/Pfa (파형·점유가 탐지 좌우)
- ✅ **report5** 공정 벤치마크(`benchmark/`): 링크버짓으로 SNR 유도 + SCR·Pd 측정 — 점유 공정성·신호×드론 매트릭스(CSV)·0-도플러 블라인드·Sionna RT 교차검증
- 다음 후보: 🌀 마이크로도플러 결합 탐지(블라인드 메우기), 📐 AoA+위치확정/다중정적+추적(Kalman/MTT), 🔁 분절모델→Gazebo SDF/PX4 airframe, 🔢 Rényi 적응적분.
