# SCENE_BUILD_OPTIONS — 씬(무대)을 우리가 직접 만든다면

> **조사일** 2026-08-12 · **원장** [`../outputs/survey_scene_build_paths.json`](../outputs/survey_scene_build_paths.json)
> **범위** 무대(환경) 전용. 표적(드론) 메쉬는 이 문서 밖이다.
> **조건** GPU 미사용(읽기·CPU 계측만) · git 미사용 · 설치 없음 · 기존 원장 미수정.

이 문서는 **공개 씬이 없거나 못 쓸 때의 대비**다. "무대를 우리가 지으려면 무엇을 어떻게 하는가"만 다룬다.

---

## 0. 한 줄

무대를 짓는 길은 **막혀 있지 않다**. Sionna 의 씬 형식은 2 KB 짜리 XML 한 장이고, 우리는 이미
그것과 같은 일을 하는 코드(`scene_build.py` + `chamber.py`)로 31 × 21 × 11.85 m 무대를 세워 봤다.
그리고 **가장 걱정했던 격자 문제는 이미 풀려 있다** — 무대와 표적은 애초에 서로 다른 엔진에
살아서, 격자를 «나눌 수 있나» 가 아니라 «나뉜 것을 어떻게 이어 붙이나» 가 진짜 질문이다.

---

## 1. Sionna 는 씬을 어떻게 읽나 (소스 실측)

읽은 파일 — `sionna/rt/scene.py` · `sionna/rt/scene_utils.py` · `sionna/rt/utils/meshes.py` · `sionna/rt/scene_object.py` (Sionna 2.0.1, Apache-2.0).

### 1.1 흐름

```
load_scene("site.xml")
  └─ 파일을 문자열로 읽고, 그 디렉터리를 mitsuba FileResolver 검색경로에 추가
       (그래서 XML 안의 "meshes/building_1.ply" 같은 상대경로가 풀린다)
  └─ process_xml(xml)
       (a) id 가 itu_ / mat-itu_ 로 시작하는 <bsdf> → itu-radio-material 로 바꿔 끼움
       (b) merge_shapes=True(기본) 면 모든 <shape> 를 <shape type="merge"> 로 감쌈 (속도)
  └─ mi.load_string(...)            ← Mitsuba 가 실제 로드
  └─ Scene._load_scene_objects()    ← shape 마다 검사 후 SceneObject 로 감쌈
```

### 1.2 어떤 파일 형식을 받나

| 경로 | 받는 형식 | 근거 |
|---|---|---|
| 파이썬 API (`SceneObject(fname=...)`, `load_mesh`) | **`.ply` · `.obj` 만** | `meshes.py:74-76`, `scene_object.py:77-81` — 그 외는 `ValueError` |
| 씬 컨테이너 | **Mitsuba 3 XML** | `load_scene` docstring 원문 |
| XML 안의 `<shape type=...>` | Mitsuba 가 해석 | 스톡 씬 15개는 **전부 `type="ply"`** |

> ⚠ `type="serialized"` / `type="obj"` 도 원리상 통과할 것으로 보이지만 **실행으로 확인하지 않았다**(GPU 금지).
> 스톡 표본에는 ply 밖에 없다. 확실한 길만 쓰려면 **ply 또는 obj** 를 쓰라.

### 1.3 XML 에 무엇이 있어야 하나

가장 작은 실제 예가 `simple_street_canyon.xml` **2101 바이트** 다 — 손으로 쓸 수 있는 분량이다.

```xml
<scene version="2.1.0">
  <bsdf type="itu-radio-material" id="concrete">
    <string name="type" value="concrete"/>
    <float name="thickness" value="0.1"/>
  </bsdf>

  <shape type="ply" id="mesh-building_1">
    <string name="filename" value="meshes/building_1.ply"/>
    <boolean name="face_normals" value="true"/>
    <ref id="concrete" name="bsdf"/>
  </shape>
</scene>
```

필수·선택을 갈라 적으면,

- **필수** — 루트 `<scene version="...">`, `<bsdf>` 에 **`id` 속성**(없으면 `process_xml` 이 `ValueError`), `<shape>` 의 `filename` 과 `<ref ... name="bsdf">`.
- **선택** — `face_normals`(스톡은 대부분 true), `thickness`(기본 0.1 m, `rt/constants.py:80`), 표시색 `<rgb name="color|reflectance|base_color">`.
- **없어도 되는 것** — 카메라(`sensor`)·`integrator` 블록. 스톡 씬에 없다. Sionna 가 `Camera` 를 따로 만든다.
- **좌표변환** — 스톡 씬 15개 중 `<transform>` 을 쓰는 것은 **하나도 없다**. 좌표를 메쉬에 구워 넣는다. Mitsuba 문법상 가능하긴 하다.

### 1.4 ⭐ 재질을 어떻게 붙이나 — 그리고 여기가 최대 함정

붙이는 길은 **두 갈래뿐**이다.

1. **이름 규약** — `<bsdf ... id="mat-itu_concrete">` 처럼 `itu_` 또는 `mat-itu_` 로 시작하면
   `process_xml` 이 알아서 `itu-radio-material` 로 바꿔 끼운다.
2. **플러그인 직접 지정** — `<bsdf type="radio-material" ...>`.

그 외 **일반 BSDF(diffuse 등)는 로드 시점에 예외**로 죽는다:

> `Found shape "..." with associated material "...", which is not a radio material.`
> — `scene.py:937-945`

⭐ 이 한 줄이 **Blender 경로의 성패를 가른다.** Blender 에서 그냥 내보내면 머티리얼 이름이
`Material.001` 같은 것이라 무조건 실패한다. **Blender 안에서 머티리얼 이름을 `mat-itu_concrete` 로 지어야 한다.**
반대로 ITU 이름을 접두어 없이 `id="concrete"` 로 쓰는 것도 막혀 있다(`process_xml:115-121`).

Sionna 에 있는 ITU 재질(`radio_materials/itu.py`)은 다음 14종이다:

`concrete · brick · plasterboard · wood · glass · ceiling_board · chipboard · plywood · marble · floorboard · metal · very_dry_ground · medium_dry_ground · wet_ground`

> ⚠ **지면 세 종류는 유효대역이 1–10 GHz** 다. 우리 3.5 GHz 는 안이고, 5.8 GHz 도 안이다.
> ⚠ **아스팔트와 초목은 표에 없다.** 야외 무대에 필요하면 커스텀 `RadioMaterial` 과 근거 문헌이 있어야 한다.

### 1.5 ⛔ 내보내기(export)가 없다

`Scene` 에 씬을 XML 로 저장하는 메서드가 **없다**. 저장되는 것은 `render_to_file` 의 PNG 뿐이다
(`scene.py` public 메서드 전수 확인).

→ **우리가 만든 무대를 파일로 남기려면 XML 을 우리가 써야 한다.** 위 2 KB 예를 보면 알겠지만
어려운 일이 아니고, 오히려 «우리 Part 목록이 곧 씬» 인 지금 구조에 라이터 한 개를 더하는 일이다.

### 1.6 우리 `scene_build.py` 와의 대조

우리는 **XML 을 전혀 쓰지 않는다.** `rt.load_scene()` 으로 **빈 씬**을 만들고
`SceneObject(fname=OBJ, radio_material=make_material(...))` 를 `scene.edit(add=[...])` 로 밀어 넣는다.

| 축 | XML 경로 | 우리 경로 (`scene_build.py`) |
|---|---|---|
| 씬 컨테이너 | 디스크의 `.xml` | 메모리 — 파일이 없다 |
| 메쉬 | `meshes/*.ply` 상대경로 | `assets/meshes/**/*.obj` 절대경로 |
| 재질 정의처 | XML 의 `<bsdf>` 노드 | `src/materials.py` 의 `MATERIALS` dict (**단일 진리원**) |
| 재질 부착 단위 | shape 1개 = bsdf 1개 | **OBJ 1개 = SceneObject 1개 = RadioMaterial 1개** (부위별) |
| 재질 표현력 | `itu-radio-material` 이 편함 | ITU + 커스텀(`eps_r`/`sigma`/`S`) 둘 다 자유 |
| 배치 | 메쉬에 구워 넣음 | `Part.position/orientation/scaling` |
| `merge_shapes` 최적화 | 기본 켜짐 | **안 걸림** — 부위 수만큼 shape 가 산다 |
| 보존·공유 | 폴더째 복사 | 파이썬을 다시 돌려야 재현 |

**두 경로는 같은 곳에 도착한다.** 우리 것이 부위별 재질에 강하고(드론 8부위에 서로 다른 재질을
붙이는 일은 XML 로는 성가시다), XML 이 보존·공유·병합최적화에 강하다.

> ⚠ 우리 경로의 알려진 함정 하나 — `SceneObject.position` 세터는 **평행이동이 아니라 AABB 중심 재배치**다.
> 절대좌표가 구워진 메쉬에 `(0,0,0)` 을 넣으면 원점으로 끌려온다. `scene_build.py:65-74` 가 이미
> `Part.position` 을 «평행이동 벡터» 로 재해석해 감싸 두었다. 야외 무대를 지어도 이 규약을 그대로 승계하면 된다.

---

## 2. 우리가 이미 가진 것 (계측)

### 2.1 코드

| 파일 | 줄 | 역할 |
|---|---|---|
| `src/scene_build.py` | 175 | `Part` 목록 → Sionna 씬 조립 + 렌더. `chamber_parts` / `drone_parts` / `ground_part` |
| `src/chamber.py` | 225 | 반무향실 **절차적 생성** — 바닥타일·피라미드 흡수체·금속 백킹·트림·외골격·문 |
| `src/geom.py` | — | 순수 numpy `Mesh` + 프리미티브 `box · quad · cylinder · pyramid · uv_sphere · pyramid_field`, 그룹별 OBJ 저장 |
| `src/cadkit.py` | — | trimesh + manifold3d CAD — `loft · sweep · revolve · superellipse · rounded_rect` + 불리언 |
| `src/materials.py` | 289 | **재질 단일 진리원** — Sionna 와 PO 커널이 같은 표를 읽는다 |
| `src/report14_scene.py` | — | ⭐**스톡 실외 씬**(street_canyon/munich/etoile/florence) 로드 + 확산산란 + 클러터 경로 추출 |

**요점: 우리는 무대를 «코드로» 짓는다.** 225줄로 31 × 21 × 11.85 m 짜리 무대가 나왔다.
이건 야외 사이트에 그대로 쓸 수 있는 방식이다.

### 2.2 자산 (2026-08-12 계측, λ = 8.5655 cm @ 3.5 GHz)

| 자산 | 파일 | 삼각형 | 변길이 중앙값 | ÷λ |
|---|---|---|---|---|
| 챔버(무대) | 19 OBJ | 38,440 | 0.588 m | **6.86** |
| mavic4pro | 7 OBJ | 28,052 | 6.12 mm | **0.071** |
| mini5pro | 8 OBJ | 26,502 | 3.55 mm | **0.041** |
| matrice4e | 9 OBJ | 31,216 | 5.32 mm | **0.062** |
| phantom4 | 8 OBJ | 27,664 | 5.51 mm | **0.064** |
| s1000plus | 10 OBJ | 39,238 | 8.68 mm | **0.101** |

> 챔버 최대 변 36.06 m 는 30 × 20 m 금속 백킹 판 **한 장의 대각선**이다 — 평면이라 커도 무해하다.
> 교차검증: 위 p95/λ 를 5.2 GHz(λ=57.54 mm)로 환산하면 **0.137 ~ 0.487** 이고,
> 기존 원장 `PRIOR_WORK_COMPARISON.md` 의 «p95/λ 0.133–0.487» 과 **일치한다**.

### 2.3 그 코드로 야외 무대를 지으려면 무엇이 더 필요한가

| # | 빠진 것 | 무엇이 없나 | 비용 | 메모 |
|---|---|---|---|---|
| 1 | **야외 재질 키** | `MATERIALS` 10키가 전부 실내·기체용(metal · camera_assembly · pcb · concrete_light/dark · plastic · plastic_blue · prop_plastic · carbon · absorber). 지면·아스팔트·벽돌·유리·초목이 없다 | 낮음 | ITU 에 지면 3종·brick·glass·wood·marble 이 있어 키만 추가. ⚠**아스팔트·초목은 ITU 에 없다** |
| 2 | **지형** | 높이맵·불규칙 삼각망이 없다. `quad` 한 장이 전부 | 낮음(평지)/중간(경사) | 실증지가 평평하면 quad + 재질로 충분 |
| 3 | **건물 매스 압출기** | 발자국 폴리곤 → 벽 + 지붕 압출 함수가 없다 | 낮음 | shapely 는 이미 설치돼 있고 `cadkit.loft` 가 있다 — 수십 줄 |
| 4 | **씬 파일 라이터** | 우리는 메모리에서만 짓고, Sionna 에도 export 가 없다 | 낮음 | Part 목록 → Mitsuba XML 라이터. 스톡이 2 KB 규모 |
| 5 | **좌표 원점 규약** | 챔버는 `x∈[0,W]` 로컬좌표. 야외는 위경도 → 로컬 ENU 원점을 **선언**해야 한다 | 낮지만 **틀리면 전부 틀린다** | 실측 RTK GT·X410 배치와 같은 계를 써야 한다. `pyproj` 미설치 |
| 6 | **규모 검사** | 챔버는 삼각형 3.8만으로 족했다. 수백 m 사이트의 삼각형 예산·PathSolver 시간을 재본 적이 없다 | 중간 | 스톡 munich 는 메쉬 파일 **2367개** 다. 우리는 그런 규모를 안 돌려봤다 |

---

## 3. OSM → 씬 경로 (조사만 · ⛔설치·clone 안 함)

### 3.1 결론부터 — 이 경로는 **실재하고, 검증돼 있다**

Sionna 공식 문서가 자기 내장 씬을 어떻게 만들었는지 직접 밝히고 있다:

> "The scene was created with data downloaded from **OpenStreetMap** and the help of **Blender**
> and the **Blender-OSM** and **Mitsuba Blender** add-ons."
> — <https://nvlabs.github.io/sionna/rt/api/scene.html> (2026-08-12 확인)

즉 munich · etoile · florence · san_francisco 가 전부 이 파이프라인의 산물이다. 남의 실험이 아니라
**NVIDIA 가 자기 씬을 만든 경로**다.

### 3.2 도구 표

| 도구 | 하는 일 | 라이선스 | 설치 요건 | 확인 |
|---|---|---|---|---|
| **Blender** | 3D 편집·중간 허브 | GPL-2.0-or-later | 데스크톱 앱. `--background` 로 헤드리스 가능. 로컬 **미설치** | ⚠원문 미확인(널리 알려진 사실이나 이번에 fetch 안 함) |
| **blosm** (구 blender-osm)<br>`vvoovv/blosm` | OSM + 지형 + Google 3D 도시 임포트. 건물 높이는 `building:levels` 태그 | **GPL** (텍스처는 CC0) | Blender 애드온 zip. ⚠소스는 `release` 브랜치, 배포는 gumroad(base 무료/자율기부) | ✅ 저장소 페이지 확인 |
| **mitsuba-blender**<br>`mitsuba-renderer/mitsuba-blender` | Blender 씬 → Mitsuba 3 XML + 메쉬 | **BSD-3-Clause** | Blender ≥ 2.93 (LTS 3.6 · 4.2 권장) | ✅ 저장소 페이지 확인 |
| **sionna_osm_scene**<br>`manoj-kumar-joshi/sionna_osm_scene` | ⭐**Blender 없이** 순수 파이썬으로 OSM → Mitsuba XML + PLY | **MIT** | `osmnx · shapely · pyproj · pyvista · open3d · ipyleaflet · ipyvolume`. 로컬엔 shapely 만 있음 | ✅ 저장소 + 노트북 원문 확인 |
| **Geo2SigMap**<br>`functions-lab/geo2sigmap` | OSM → Blender → PLY/XML → Sionna 자동 파이프라인 + U-Net 커버리지 | ⛔ **CC BY-NC 4.0 (비상업)** | 문서가 하위 README 로 분산 | ✅ 저장소 페이지 확인 |

### 3.3 두 갈래

- **(A) Blender GUI 경로** — 공식이고 검증됐지만 애드온 2개 + 데스크톱 앱이 필요하고 손이 많이 간다.
  ⭐그리고 **머티리얼 이름을 `mat-itu_*` 로 짓는다는 계약**(§1.4)을 지켜야 한다.
- **(B) 순수 파이썬 경로 (`sionna_osm_scene`, MIT)** — 우리 철학(«코드로 메쉬를 만든다»)과 같다.
  건물 높이 = `building:levels` × 3.5 m(태그 없으면 3.5 m), 발자국 `delaunay_2d` 삼각화 후 압출,
  `building_{idx}.ply` + `ground.ply` 저장, XML 에 `mat-itu_concrete / marble / metal / wood / wet_ground` 생성.
  ⚠ **삼각형 밀도를 조절하는 파라미터가 노출돼 있지 않다**(노트북 원문 확인).

우리에게는 **(B)가 참조 구현으로 더 맞다**. MIT 라 안전하고, Blender 가 필요 없고,
우리가 이미 `geom.py`/`cadkit.py` 로 하는 일과 같은 종류다.

### 3.4 ⚠ 라이선스 — 두 층을 구분하라

- **도구 층** — 위 표대로. Geo2SigMap 만 **비상업(NC)** 이다. 아이디어는 참고하되 **코드를 우리
  저장소에 흡수하지 않는 편이 안전하다** — NC 가 전염될 소지가 있다.
  (우리 `PRIOR_WORK_COMPARISON.md:137` 은 이미 «워크플로 패턴만 adopt» 로 적어 두었다 — 일관된다.)
- **데이터 층** — OpenStreetMap 은 **ODbL v1.0** 이고 share-alike 다:
  > "If you alter or build upon our data, you may distribute the result only under the same license."
  > — <https://www.openstreetmap.org/copyright>

  OSM 발자국으로 만든 건물 메쉬를 **배포**하면 파생물로 볼 여지가 크다. 내부 계산용은 배포가
  아니므로 문제되지 않는다. **논문 부록에 씬을 공개할 계획이면 이 조항을 먼저 정리해야 한다.**
  ⚠ 법률 판단이 아니라 라이선스 원문을 읽은 우리 해석이다.

---

## 4. ⭐ 격자 해상도 — 무대와 표적을 따로 둘 수 있나

### 4.1 답: 이미 따로다. 두 엔진이라서.

| | 무대 | 표적 |
|---|---|---|
| 엔진 | **Sionna `PathSolver`** | **우리 SBR+PO 커널** (`src/rcs_sbr.py`) |
| 물리 | 기하광학(GO) — 면을 «국소 무한 거울» 로 본다. **표면적분이 없다** | 광선으로 조명면을 찾고 그 위에서 **PO 표면적분** |
| 격자 기준 | 삼각형 크기(메쉬가 정함) | 광선 간격 `d = λ/12` = **7.14 mm** @3.5 GHz |
| 잇는 곳 | ← **σ 주입** → | |

`sbr_field` 의 서명을 보면 명확하다:

```python
sbr_field(mesh, group_mat, fc, u, spacing=None, pad=1.15, ..., grid_ref=None, range_m=None)
```

**인자에 무대가 없다.** `Mesh` 하나만 받는다. 무대 삼각형은 이 커널에 **들어올 방법이 자체가 없다.**
격자는 `_grid_for(mesh, d, pad, grid_ref, u)` 가 표적 bbox 를 `pad=1.15` 로 부풀린 구를 덮게 만든다.

> ⚠ 혼동 주의 — **`grid_ref` 와 `spacing` 은 «무대 대 표적» 노브가 아니다.**
> `grid_ref` 는 자세(로터 위상)마다 격자가 다시 만들어져 **위상 원점이 흔들리는 것을 막는 «얼린 격자»** 다
> (`rcs_sbr.py:732-911`). `spacing` 은 그 격자의 간격(기본 λ/`DEFAULT_DIV`, `DEFAULT_DIV=12`)이다.
> 둘 다 **표적 격자 전용**이고 무대와는 무관하다.

### 4.2 실제 격자비 — 얼마나 다른가 (계측)

| 무대 | 메쉬 파일 | 변길이 중앙값 | **÷λ** | p95 ÷λ |
|---|---|---|---|---|
| simple_street_canyon | 7 | 31.12 m | **363** | 697 |
| ...with_cars | 23 | 1.95 m | 22.8 | 488 |
| etoile | 565 | 13.40 m | **156** | 350 |
| munich | 2367 | 0.354 m | **4.1** | 203 |
| florence | 2639 | 2.22 m | 25.9 | 246 |
| san_francisco | 4735 | 9.04 m | **106** | 256 |
| `low_poly_car.ply` | 1 (20 삼각형) | 1.80 m | 21.0 | — |
| **`sphere.ply`** | 1 (15,872 삼각형) | 0.0485 m | **0.567** | 0.79 |
| **우리 챔버** | 19 | 0.588 m | 6.86 | 7.13 |
| **우리 드론 5종** | 7~10 | 3.55 ~ 8.68 mm | **0.041 ~ 0.101** | 0.09 ~ 0.33 |

> 도시 씬은 메쉬 파일 200개 무작위 표본(seed 0). 계측 스크립트는 원장 `_meta.measure_script` 참조.

읽는 법 두 가지.

1. **격자비가 40배(munich)에서 8800배(street_canyon)** 다. 같은 격자에 둘 다 태울 수 있는 문제가 아니다.
2. ⭐ **스톡 씬 전체에서 λ 이하인 메쉬는 `sphere.ply` 하나뿐**이다 — 그것도 무대가 아니라 커널 **검증용 구**다.
   즉 스톡 씬의 어떤 건물도 산란체 노릇을 하도록 만들어지지 않았다. 이건 결함이 아니라 **설계 의도**다.
   GO 에는 λ 기준 격자 요건이 애초에 없기 때문이다.

### 4.3 우리 저장소에 이미 선례가 있다

`src/report14_scene.py` 머리말이 그대로 답이다:

> "⚠ 표적 밝기 σ 는 report13 SBR+PO 격자로 주입한다(few-λ 드론은 스톡 Sionna 부정확 — 우리 메모).
> 여기서는 **환경만** RT 로 짓는다."

하는 일 — 스톡 실외 씬 로드 → 재질별 확산산란 `S` 설정 → `PathSolver(max_depth=3)` 로 TX→RX
다중경로 추출 → AoA × 도플러 클러터 공분산. **표적 메쉬는 씬에 넣지 않는다.**

→ 야외 무대의 격자 규약은 **새로 설계할 것이 아니라, 이미 서 있는 규약을 사이트로 확장**하는 일이다.

### 4.4 ⚠ 이 분리가 **주지 않는 것**

- ⭐ **무대 × 표적 결합항이 자동으로 안 나온다.** 「표적을 경유한 바닥 유령」
  (TX → 바닥 → 표적 → RX 같은 경로)은 **두 엔진 어디에도 없다** — 표적이 무대 씬에 없으니
  `PathSolver` 가 못 만들고, 무대가 SBR 커널에 없으니 PO 도 못 만든다.
  우리 메모가 「진짜 위협은 표적경유 바닥유령」이라 적어둔 바로 그 항이다. **명시적으로 배선해야 한다.**
  (저장소에 `src/experiment_ghost.py` 가 있다 — 이번 조사에서 내용은 안 읽었다.)
- 표적이 무대에 드리우는 그림자, 무대가 표적을 가리는 효과.
- 표적이 지면에 아주 가까울 때의 근거리 결합.

### 4.5 실무 규칙 넷

1. **무대 삼각형 크기를 λ 로 재지 마라.** GO 에는 λ 기준 격자 요건이 없다. 무대가 낳아야 할
   **경로의 각도 정밀도**로 재라.
2. **λ 보다 작은 무대 디테일(난간·창틀)은 넣지 마라.** GO 로 의미가 없다 — 물리가 아니라
   삼각형 예산 낭비다.
3. **표적 격자(λ/12)는 무대 기준으로 낮추지 마라.** σ 가 그 격자에서 나온다.
4. ⛔ **편의상 표적 메쉬를 무대 씬에 넣지 마라.** 스톡 Sionna 는 표면적분이 없어 σ 가 창발하지 않는다.
   `rcs_sbr.py` 머리말의 실측이 그대로다 — 평판 변을 0.2 → 4 m 로 키워 **σ 가 52 dB 변해도
   RT 진폭은 −7.91 dB 불변**(산포 0.00 dB).

---

## 5. 비용 추정 — 야외 사이트 트윈 하나

> 근거: 우리 저장소 실적(챔버 = `chamber.py` 225줄로 무대 완성) + §2.2 계측. **추정이지 실측 소요시간이 아니다.**
> 가정: 평지에 가깝고, 무대 반경 100~300 m, 건물 수십 채 이하.

| # | 단계 | 무엇을 하나 | 품 | 위험 |
|---|---|---|---|---|
| 1 | **사이트 확정·원점 선언** | 실증지 좌표 하나를 원점으로 못박고 로컬 ENU 축 선언. RTK GT · X410 배치와 같은 계 | 0.5일 | ⭐**틀리면 하류 전부 틀린다.** 그리고 지금 **막혀 있다** — `MEASUREMENT_PLAN.md` Q1 이 «1층 레인지가 어디인지 정해지지 않았다» 고 적고 있다 |
| 2 | **무대 기하 확보** | (A) OSM → 발자국 압출 (B) 실측/도면으로 박스 몇 개 (C) OSM 초안 + 현장 사진 교정 | OSM 1~2일 / 손 0.5~1일 | 낮음. 건물이 몇 채뿐이면 **(B)가 더 빠르고 더 정확하다** |
| 3 | **야외 재질 키 추가** | `materials.py` 에 ground(ITU 3종) · brick · glass · wood · marble. ⚠아스팔트·초목은 커스텀 + 문헌 | 0.5일 + 문헌 0.5일 | 낮음. 확장 지점이 이미 단일 진리원이라 명확 |
| 4 | **무대 조립 배선** | `chamber_parts()` 와 같은 모양의 `site_parts()` 를 만들어 `build_scene` 에 태움 | 0.5일 | 낮음. ⚠`Part.position` 함정만 승계 |
| 5 | **규모·비용 계측** | 삼각형 수 · `max_depth` 별 경로 수 · 소요시간 · 확산산란 폭발. 예산 초과면 무대 단순화 | 0.5~1일 (**GPU 필요**) | ⭐중간 — 이 규모를 돌려본 적이 없다 |
| 6 | **⭐σ 주입 인터페이스 고정** | 표적 σ 격자(자세 × 밴드 × 바이스태틱각)를 무대 계산에 넣는 규약. `report14_scene.py` 의 야외판 | 1일 | 중간 — 두 엔진의 경계라 **어긋나면 조용히 틀린다** |
| 7 | **⭐무대 × 표적 결합항** | 표적경유 바닥/건물 유령을 명시 배선(무대 → 표적 조명, 표적 → 무대 → RX) | 2~4일 | ⭐⭐**높음** — 우리 메모가 이 항을 «5G 100% 오검출의 원인» 이라 적고 있다 |
| 8 | **검증** | 무대만: 스톡 street_canyon 과 나란히 돌려 경로 수·지연분포 대조. 결합: 챔버 유령 결과와 정성 일치 | 1~2일 | 중간. ⭐우리 방침(2026-08-03)이 **«입장료는 검증»** 이다 |

**합계**

- 무대 기하만 세워 렌더까지 — **2~4일**
- σ 주입까지(= report14 규약의 야외판) — **4~7일**
- 결합항 + 검증까지 — **8~14일**

### ⭐ 지금 가장 값싼 한 수

1단계가 **막혀 있다**(사이트 미정). 그러니 지금은 **2·3·4단계를 사이트와 무관하게 미리 지어두는 것**이
가장 값싸다. 원점만 파라미터로 빼두면 사이트가 정해질 때 갈아끼우면 된다.

가장 작게 시작한다면 — `materials.py` 에 야외 재질 키를 추가하고, `geom.py` 에
「발자국 폴리곤 → 압출」 함수 하나를 더하는 것. **반나절이고, 사이트가 어디로 정해지든 버려지지 않는다.**

---

## 6. 모르는 것 (정직하게)

- XML 의 `type="serialized"` / `type="obj"` 가 Sionna 2.0.1 에서 **실제로** 로드되는지 — 실행 확인 안 함(GPU 금지). 스톡 15개는 전부 ply.
- 손으로 쓴 최소 XML 이 실제로 로드되는지 — 소스상 통과해야 하지만 **실행으로 확인 안 함**.
- `mitsuba-blender` 가 내보내는 메쉬 파일 형식(ply/obj/serialized) — 저장소 페이지에서 확인 못 함.
- Blender 라이선스 — 이번에 원문 fetch 안 함.
- `blosm` 저장소에 LICENSE 파일이 실제로 있는지 — 설명 문구만 확인.
- **스톡 씬 15개의 «데이터» 라이선스** — 코드는 Apache-2.0 이지만 OSM 유래 지오메트리에 ODbL 이 걸리는지 확인 못 함. **이 조사의 범위 밖**(공개 씬 조사 담당).
- `src/experiment_ghost.py` 가 무대 × 표적 결합을 이미 어디까지 다루는지 — 이번에 안 읽었다.
- 우리 규모(반경 100~300 m, 확산산란 ON)에서 `PathSolver` 의 실제 소요시간·메모리 — **잰 적 없다**.
- 야외 아스팔트·초목의 3.5 GHz `εr·σ` 근거 문헌 — 아직 없다.

---

## 참고 링크

- Sionna Scenes API (내장 씬 제작 경로 명시) — <https://nvlabs.github.io/sionna/rt/api/scene.html>
- Mitsuba 3 씬 형식 — <https://mitsuba.readthedocs.io/en/stable/src/key_topics/scene_format.html>
- blosm — <https://github.com/vvoovv/blosm>
- mitsuba-blender — <https://github.com/mitsuba-renderer/mitsuba-blender>
- sionna_osm_scene (MIT) — <https://github.com/manoj-kumar-joshi/sionna_osm_scene>
- Geo2SigMap (⛔CC BY-NC 4.0) — <https://github.com/functions-lab/geo2sigmap> · arXiv:2312.14303
- OpenStreetMap 저작권·ODbL — <https://www.openstreetmap.org/copyright>
