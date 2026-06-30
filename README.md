# sionna2 — 대형 차폐시설 & DJI 드론 5종

처음부터 **단순하고 투명하게** 다시 만든 작업 공간입니다.
딱 두 가지만 다룹니다: **① 대형 차폐시설(전파무반사실)** 과 **② DJI 드론 5종**.
그리고 **그림으로 최대한 많이** 보여줍니다.

> 가장 먼저 볼 것 → **[`report1.ipynb`](report1.ipynb)** (한글 단계별 설명서. 커널 없이도 그림이 보임)

---

## 한 번에 전부 만들기

```bash
PY=/home/yunjung/workspace/jeong/miniforge3/envs/sionna/bin/python
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
build_all.py    한 번에 전부 생성
make_notebook.py report1.ipynb 생성기
```

설계 원칙: **OBJ 1개 = 부위 1개 = Sionna 재질 1개.** 그래서 부위별로 색/전파재질을
따로 줄 수 있고, 나중에 광선추적(RT) 시뮬레이션에 바로 쓸 수 있습니다.

## 환경
- Python: `/home/yunjung/workspace/jeong/miniforge3/envs/sionna/bin/python`
  (sionna-rt 2.0.1, mitsuba 3.8.0, GPU RTX 4090). `conda activate` 대신 **이 경로로 직접** 실행.
- 추가 설치 불필요 — 메쉬는 numpy 로 직접 OBJ 작성, GIF 는 Pillow 사용.

## 아직 안 한 것 (다음 단계 후보)
외형/시각화까지만 했습니다. 이어서 원하시면: 송수신 안테나 배치 + 광선추적,
드론 RCS/패시브 레이더 시뮬레이션, 흡수체 무반사 성능(-dB) 검증 등.
