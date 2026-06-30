# sionna2 — 대형 차폐시설 & DJI 드론 5종

처음부터 **단순하고 투명하게** 다시 만든 작업 공간입니다.
딱 두 가지만 다룹니다: **① 대형 차폐시설(전파무반사실)** 과 **② DJI 드론 5종**.
그리고 **그림으로 최대한 많이** 보여줍니다.

> 먼저 볼 것 (커널 없이도 그림이 보임):
> - **[`report1.ipynb`](report1.ipynb)** — 1단계: 환경 세팅 (차폐시설 + 드론 5종)
> - **[`report2.ipynb`](report2.ipynb)** — 2단계: 레이더 구성 & RCS 특성화 (WiFi·LTE·5G 비교)
> - **[`report3.ipynb`](report3.ipynb)** — 3단계: 분절 드론 + 마이크로-도플러 (+ PX4 연동 가능성)

---

## 한 번에 전부 만들기

```bash
PY=/home/yunjung/.venvs/py312/bin/python
cd sionna2/src
CUDA_VISIBLE_DEVICES=0 $PY build_all.py             # 메쉬+도면+GIF+렌더 전부
CUDA_VISIBLE_DEVICES=0 $PY build_all.py --no-render # 렌더 빼고 빠르게
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
| **S1000+** | 단종(2014) | **8** | 1045 mm | 4400 g | Ø381 mm ×2 |
| **Phantom 4** | 출시(2016) | 4 | 350 mm | 1380 g | Ø239 mm ×2 |

\* 대각거리는 DJI 비공개라 외형에서 추정한 값입니다. 무게·언폴드 치수 등은 공식 제원입니다
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

```
geom.py         삼각형으로 3D 도형 만드는 미니 도구 (외부 의존성 없음)
chamber.py      차폐시설 모델
drones.py       드론 5종 실측 제원 + 파라메트릭 생성기
materials.py    Sionna 전파재질(금속/콘크리트/흡수체/플라스틱/카본)
scene_build.py  부위 OBJ → Sionna 장면 조립 + 렌더 엔진
viz_diagram.py  도면식 그림(matplotlib)
viz_anim.py     회전 GIF
render_drones.py Sionna 사진풍 렌더
viz_montage.py  렌더 모아 카탈로그
build_all.py    한 번에 전부 생성 (report1)
make_notebook.py report1.ipynb 생성기
--- report2 (레이더) ---
radar_scene.py  모노스태틱 장면 + Sionna RT 채널/클러터 + 원거리장 점검
rcs_po.py       물리광학(PO) RCS 계산 — 평판·구 이론으로 검증됨
waveforms.py    실제 OFDM 파형 합성 + 점유모드 G1/G2/G3 (WiFi/LTE/5G, PRS·SSB·CRS·DMRS 라벨)
radar_process.py 에코 생성 + 정합필터(FFT) + RCS 추정 + 패시브(파일럿만) 처리
viz_radar.py    RCS/파형/거리프로파일 시각화
viz_occupancy.py 리소스 그리드 '사진' + 점유 상태 실험(거리×속도 두 축)
viz_mesh.py     메쉬 기반 실험 시각화 — 셋업 3D·RCS '풍선'·조명면·도플러
build_report2.py report2 산출물 한 번에 생성
--- report3 (분절 + 마이크로도플러) ---
drones.py       (분절 추가) build_frame/build_propeller/rotor_layout/pose_articulated
                — 몸체 RPY ⟂ 로터별 스핀 (build_drone 출력 동일·호환)
microdoppler.py 회전 블레이드 마이크로도플러 — PO 복소장 E(t) + 스펙트로그램
viz_articulation.py 분절 검증 도면 + 마이크로도플러 + 회전 GIF
build_report3.py report3 산출물 한 번에 생성
```

### report2 / report3 한 번에 만들기
```bash
cd sionna2/src && CUDA_VISIBLE_DEVICES=0 $PY build_report2.py   # GPU 불필요(PO+DSP)
cd sionna2/src && CUDA_VISIBLE_DEVICES=0 $PY build_report3.py   # GPU 불필요(메쉬+PO+DSP)
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
- ✅ **report3** 분절 드론(몸체 RPY ⟂ 로터별 스핀) + 회전 블레이드 마이크로-도플러 + PX4/Gazebo 연동 가능성 검증
- 다음 후보: 🛰️ 바이스태틱(패시브)+클러터제거(ECA)·CFAR·추적, 🔁 분절모델→Gazebo SDF/PX4 airframe 내보내기, 🎯 마이크로도플러 드론 vs 새 분류.
