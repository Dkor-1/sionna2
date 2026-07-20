# -*- coding: utf-8 -*-
"""make_mesh02.py — mesh02 ipynb 생성기. ⚠ 이 파일이 소스다.

mesh02 — "도구 상자: 어떤 파이썬 라이브러리를 왜 골랐나"
모든 수치는 outputs/mesh_verify.json 에서 읽어 f-string 으로 주입한다(손 숫자 금지).
라이브러리 버전은 생성 시점에 실제 설치 환경(importlib.metadata)에서 읽는다.
"""
import json, os, sys
import importlib.metadata as _im

HERE = os.path.dirname(os.path.abspath(__file__))
RM = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(RM, ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
V = json.load(open(os.path.join(RM, "outputs", "mesh_verify.json"), encoding="utf-8"))

# ---- 실제 설치 환경에서 버전 읽기 (← 출처: ~/.venvs/py312, importlib.metadata) ----
VER = {p: _im.version(p) for p in ["numpy", "trimesh", "manifold3d", "shapely", "scipy"]}

# ---- JSON 수치 꺼내기 (전부 mesh_verify.json) -------------------------------------
DR = V["meta"]["drones"]
A = V["A_geometry"]
mav = A["mavic4pro"]
n_faces_total = sum(A[k]["n_faces"] for k in DR)
n_verts_total = sum(A[k]["n_verts"] for k in DR)
all_ok = all(A[k]["ok"] for k in DR)
dup_total = sum(A[k]["dup_vertices"] for k in DR)
unused_total = sum(A[k]["unused_vertices"] for k in DR)
ov_mav = V["F_overlap"]["mavic4pro"]["overlap_pct_of_volume"]
ov_s1000 = V["F_overlap"]["s1000plus"]["overlap_pct_of_volume"]
engine = V["meta"]["mesh_engine"]
fc = V["meta"]["fc_ghz"]
lam_mm = V["meta"]["lam_hi_mm"]
sub = V["I_sbr_subdiv"]["subdivision_invariance"]
mav_groups = ", ".join(A["mavic4pro"]["groups"].keys())


def md(*lines):
    src = "\n".join(lines).splitlines(keepends=True)
    return {"cell_type": "markdown", "metadata": {}, "source": src or [""]}


def code(*lines):
    src = "\n".join(lines).splitlines(keepends=True)
    return {"cell_type": "code", "metadata": {}, "source": src or [""],
            "outputs": [], "execution_count": None}


cells = [

# ────────────────────────────────────────────────────────────────── 1. 표지
md(
"# mesh02 — 도구 상자: 어떤 파이썬 라이브러리를 왜 골랐나",
"",
"> ⚠ **이 노트북은 생성물이다. 수정은 `src/make_mesh02.py` 에서 하라.**",
"",
f"**한 줄 요약** — 드론 5기의 CAD 메쉬(총 삼각형 {n_faces_total:,}개)는 딱 5개 라이브러리",
"(numpy · shapely · trimesh · manifold3d · scipy)와 자작 미니 도구(`src/geom.py`) 위에서 만들어졌다.",
"이 편에서는 **각 도구가 무엇을 하고, 왜 그것을 골랐고, 어떤 방식으로 쓰는지**를 하나씩 뜯어본다.",
"",
"| 용어 | 한 줄 풀이 |",
"|---|---|",
"| 메쉬(mesh) | 3D 모양을 **삼각형 조각들의 모음**으로 표현한 것 (꼭짓점 목록 + 삼각형 목록) |",
"| 정점(vertex) / 면(face) | 3D 점 (x,y,z) 하나 / 정점 3개를 이은 삼각형 하나 |",
"| watertight(방수) | 메쉬에 구멍·틈이 하나도 없어 물을 부어도 안 새는 상태 — 부피 계산·불리언의 전제 |",
"| 불리언(CSG) | 두 입체의 합집합/차집합/교집합 — 레고 붙이기·조각칼로 파내기에 해당 |",
"| 로프트(loft) | 여러 **단면**을 배 늑골처럼 세워 놓고 겉껍질을 씌워 곡면을 만드는 기법 |",
"| 스윕(sweep) | 단면 하나를 **곡선 경로를 따라 밀어** 관·팔 모양을 만드는 기법 |",
"| 회전체(revolve) | 옆모습 곡선을 축 둘레로 한 바퀴 돌려 만든 입체 (도자기 물레와 같음) |",
"| 초타원(superellipse) | 타원과 직사각형의 중간 곡선 — 실제 드론 동체 단면이 이 모양 |",
"| NACA 익형 | 미 항공자문위(NACA)의 표준 날개 단면 공식 — 프로펠러 단면에 사용 |",
"| 법선(normal) | 면이 바라보는 수직 방향 화살표 — 안/밖 구분과 전자기 계산의 기준 |",
"| 퇴화 삼각형(degenerate) | 세 점이 겹치거나 일직선이라 **넓이가 0**인 불량 삼각형 |",
"| PO / SBR | 물리광학 / 슈팅&바운싱 레이 — 이 메쉬를 소비하는 레이더 반사(RCS) 계산법 |",
),

# ────────────────────────────────────────────────────────────────── 2. §0 큰 그림
md(
"## 0. 큰 그림 — 도구는 두 층이다",
"",
"이 프로젝트의 3D 도구는 **두 층**으로 되어 있다.",
"",
"1. **`src/geom.py` — 의존성 0 자작 미니 도구.** numpy 만 쓰고, 삼각형을 한 장 한 장 손으로",
"   쌓는다. 단순하고 투명해서 \"메쉬가 뭔지\"를 배우기에 최적이고, 라이브러리가 없는 서버에서도 돈다.",
"2. **`src/cadkit.py` — 라이브러리를 제대로 쓰는 CAD 툴킷.** trimesh + manifold3d + shapely +",
"   scipy 로 로프트·스윕·회전체·불리언·검증을 수행한다. 실제 드론 형상(눈물방울 동체, 익형",
"   프로펠러)은 이 층에서 만들어진다.",
"",
f"최종 메쉬 엔진은 `\"{engine}\"` 이다 ← 출처: mesh_verify.json `meta.mesh_engine`.",
"즉 **모양을 계산하는 본체는 cadkit(라이브러리) 층**이고, geom.Mesh 는 마지막에 결과를 담아",
"기존 파이프라인(장면 구성·RCS·마이크로도플러)으로 넘기는 **공용 컨테이너**로 남았다",
"← 출처: src/cadkit.py:24 (\"마지막에 geom.Mesh 로 변환한다 → 기존 파이프라인이 그대로 돈다\").",
"",
"왜 이렇게 두 층인가? — 처음엔 geom.py 하나로 시작했는데, 실물 형상을 흉내 내려니 네 가지가",
"부족했기 때문이다(§2.5 에서 소스 주석을 그대로 인용한다). **이 진화 과정 자체가 \"왜 이",
"라이브러리들인가\"의 답**이므로, 이 편은 그 순서대로 서술한다.",
),

# ────────────────────────────────────────────────────────────────── 3. 버전 확인 코드
md(
"### 0.1 이 노트북이 쓰는 실제 버전",
"",
"아래 셀은 지금 커널(py312)에 실제로 설치된 버전을 출력한다. 리포트 생성 시점에 확인된 버전은",
f"numpy {VER['numpy']} · trimesh {VER['trimesh']} · manifold3d {VER['manifold3d']} ·",
f"shapely {VER['shapely']} · scipy {VER['scipy']} 였다",
"← 출처: 실제 설치 환경(~/.venvs/py312, importlib.metadata 로 조회).",
),
code(
"# 설치된 라이브러리 버전 확인 — 재현 시 아래 값이 본문 값과 같은지 보라",
"import importlib.metadata as im",
"for pkg in [\"numpy\", \"trimesh\", \"manifold3d\", \"shapely\", \"scipy\"]:",
"    print(f\"{pkg:12s} {im.version(pkg)}\")",
),

# ────────────────────────────────────────────────────────────────── 4. §1 numpy
md(
"## 1. numpy — 모든 좌표 계산의 기반",
"",
f"**무엇** — 수치 배열 라이브러리(버전 {VER['numpy']} ← 출처: 실제 설치 환경). 이 프로젝트에서",
"정점 좌표는 전부 `(N, 3)` 모양의 numpy 배열이고, 이동·회전·확대는 4×4 행렬 곱 한 번이다",
"← 출처: src/geom.py:76-96 (`Mesh.transformed` 가 동차좌표 `(N,4)` 를 만들어 `M @ P.T` 로 변환).",
"",
"**왜** — 파이썬 반복문으로 정점 수만 개를 하나씩 옮기면 수백 배 느리다. numpy 는 C 로 구현된",
"벡터 연산이라 좌표 수만 개를 한 번에 처리한다. 사실상 대안이 없는 과학계산 표준이며(BSD",
"라이선스, numpy.org), 아래의 trimesh·shapely·scipy 도 모두 numpy 배열을 주고받는다 —",
"**공용 언어**인 셈이다.",
"",
"**어떻게** — 이 프로젝트의 좌표 규약은 numpy 배열에 담긴 **z 축 위(up), 단위 미터(m)** 다.",
"드론 제원은 mm 로 들어오므로 /1000 해서 쓴다 ← 출처: src/geom.py:24-29 (좌표계·단위 주석).",
),

# ────────────────────────────────────────────────────────────────── 5. §2 geom.py
md(
"## 2. `src/geom.py` — 의존성 0 자작 미니 도구",
"",
"**무엇** — 외부 3D 라이브러리 없이 삼각형만으로 모델을 만드는 최소 도구. 메쉬를 딱 세 목록으로",
"표현한다: `.v`(정점 좌표), `.f`(삼각형 인덱스), `.g`(면별 **그룹 이름** = body/arm/motor/prop...)",
"← 출처: src/geom.py:41-48. 그룹 이름표는 나중에 부위별 색칠과 부위별 전파재질(Sionna",
"RadioMaterial) 부여에 쓰인다 ← 출처: src/geom.py:19-22.",
"",
"**왜 직접 만들었나** — 소스 주석에 이유가 그대로 적혀 있다 ← 출처: src/geom.py:8-13:",
"",
"> \"서버 sionna 환경에 trimesh 가 없고(설치 권한도 없음), 무엇보다 **'도형이 어떻게",
"> 만들어지는지' 코드로 눈에 보이게** 하기 위해서입니다. (사용자가 쉽게 이해하는 것이 이",
"> 프로젝트의 1순위 목표)\"",
"",
"즉 선택 이유는 **단순함·투명함·교육**, 그리고 설치 권한이 없는 환경에서의 이식성이다.",
"box 하나가 코드 20줄이라, 삼각형이 어떤 순서로 감기는지(winding) 눈으로 따라갈 수 있다.",
"",
"**어떻게 — 제공하는 프리미티브(기본 도형)** ← 출처: src/geom.py 의 각 함수:",
"",
"| 함수 | 만드는 것 | 소스 위치 |",
"|---|---|---|",
"| `box` | 직육면체(정점 8개, 삼각형 12개) | src/geom.py:184 |",
"| `cylinder` | 원기둥·원뿔대(`r_top`) | src/geom.py:213 |",
"| `pyramid` / `pyramid_field` | 전파흡수체 피라미드 1개 / 피라미드 밭 | src/geom.py:247, 403 |",
"| `uv_sphere` | 구(짐벌 카메라 공 등) — 극점은 삼각형 팬으로 퇴화면 방지 | src/geom.py:271 |",
"| `blade` / `prop_blade` | 평면 근사 / 트위스트·테이퍼 프로펠러 날개 | src/geom.py:302, 324 |",
"| `hull` | 타원 단면 다각기둥 동체 | src/geom.py:380 |",
"| `translate` / `rotate` / `scale` | 4×4 변환 행렬 | src/geom.py:157-178 |",
"| `write_obj_per_group` | 그룹별 .obj 저장 — \"OBJ 1개 = Sionna 재질 1개\" 규약 | src/geom.py:137-147 |",
),
code(
"# geom.py 맛보기 — 라이브러리 없이 삼각형만으로 도형 만들기",
"import os, sys, numpy as np",
"sys.path.insert(0, os.path.abspath(os.path.join(os.getcwd(), \"..\", \"src\")))",
"import geom",
"",
"shapes = {\"box\":       geom.box(0.30, 0.20, 0.10),          # 직육면체 30x20x10 cm",
"          \"cylinder\":  geom.cylinder(0.05, 0.20, seg=24),   # 반지름 5 cm 원기둥",
"          \"uv_sphere\": geom.uv_sphere(0.05)}                # 반지름 5 cm 구",
"for name, m in shapes.items():",
"    lo, hi = m.bounds()",
"    size_cm = np.round((hi - lo) * 100, 1)",
"    print(f\"{name:10s} 삼각형 {m.n_tris():4d}개  크기(cm) {size_cm}\")",
),

# ────────────────────────────────────────────────────────────────── 6. §2.5 한계
md(
"### 2.5 geom.py 의 네 가지 한계 — cadkit 이 태어난 이유",
"",
"실물 드론 외형을 흉내 내기 시작하자 자작 도구의 한계가 드러났다. `cadkit.py` 상단 주석이",
"그 목록이다 ← 출처: src/cadkit.py:5-12 (원문 인용):",
"",
"> \"`geom.py` 는 의존성 없이 삼각형을 쌓는 도구다. 그래서:",
"> · **불리언(CSG)이 없다** → 오목부·홈·리세스를 못 판다. 프리미티브를 겹쳐 놓을 뿐이라",
">   **속에 파묻힌 면**이 그대로 남는다.",
"> · **로프트(loft)가 없다** → 단면이 변하는 매끈한 동체(눈물방울·허리 잘록)를 못 만든다.",
"> · **스무딩/서브디비전이 없다** → 각진 다각기둥밖에 안 된다.",
"> · **검증이 없다** → 프로펠러 캡 법선이 뒤집힌 걸 몇 달간 못 잡았다.\"",
"",
"마지막 항목은 실제 사고였다: `geom.prop_blade` 의 뚜껑(캡) 두 장이 **둘 다 안쪽을 향한 채**",
"몇 달을 지나갔고, 2026-07-14 에야 수동으로 발견해 고쳤다 ← 출처: src/geom.py:369-374 수정",
"주석 (\"예전 코드는 두 캡의 감기가 반대여서 법선이 안쪽을 향했다 ... 프로펠러는",
"마이크로도플러의 신호 그 자체라 특히 민감하다\"). 자동 검증(`is_watertight`, 부피 부호)이",
"있었다면 즉시 잡혔을 버그다 — **이것이 trimesh 도입의 결정적 계기**다.",
"",
"왜 RCS(레이더 반사 면적)에 중요한가: 형상이 각지거나 내부 면이 남으면 전자기 계산(PO/SBR)이",
"실물과 다른 면을 \"보게\" 된다 ← 출처: src/drone_cad.py:23-26 (\"RCS 는 외형(투영면적)과 재질",
"분포가 결정한다. 실루엣이 틀리면 σ 가 틀린다\").",
),

# ────────────────────────────────────────────────────────────────── 7. §3 shapely
md(
"## 3. shapely — 2D 단면 폴리곤 공장",
"",
f"**무엇** — 2D 기하 라이브러리(버전 {VER['shapely']} ← 출처: 실제 설치 환경). 폴리곤(다각형)의",
"생성·버퍼(테두리 넓히기)·보간을 담당한다. 내부적으로 검증된 C++ 기하 엔진 GEOS 를 쓴다",
"(BSD 라이선스, shapely.readthedocs.io).",
"",
"**왜** — 3D 로프트/스윕의 입력은 결국 **2D 단면**이다. 단면을 다루는 연산 중 특히",
"\"정확한 오프셋(둥근 모서리)\"과 \"외곽선 등간격 재샘플\"은 직접 짜면 모서리·자기교차 처리에서",
"틀리기 쉽다. shapely 는 이를 `buffer` 와 `interpolate` 한 줄로 제공한다",
"← 출처: src/cadkit.py:188-194 (`rounded_rect` — \"shapely 의 buffer 로 만든다(정확한 오프셋)\"),",
"src/cadkit.py:141-145 (`_resample` — \"로프트하려면 단면들의 점 수가 같아야 한다\").",
"",
"**어떻게** — 이 프로젝트의 핵심 단면 두 가지가 shapely `Polygon` 으로 만들어진다:",
"",
"* `superellipse(a, b, n)` — **초타원**: n=2 면 타원, n>2 면 모서리가 둥근 직사각형.",
"  \"실제 드론 단면은 순수 타원도 박스도 아니고 이 중간이다\" ← 출처: src/cadkit.py:179-185",
"  docstring. 접이식 동체는 n≈2.9 를 쓴다 ← 출처: src/drone_cad.py:107 (`_body_folding` 의",
"  `n_pow=2.9`).",
"* `rounded_rect(w, h, r)` — 둥근 모서리 직사각형: 접이식 팔(arm)의 단면 ← 출처:",
"  src/drone_cad.py:139-142 (`_arm_folding` 이 이 단면을 스윕 경로에 태운다).",
"",
"프로펠러 단면(NACA 익형)도 shapely Polygon 으로 조립된 뒤, 회전(피치각)·평행이동(스윕)을",
"`shapely.affinity` 로 처리한다 ← 출처: src/drone_cad.py:59-101 (`_airfoil`, `_blade`).",
),

# ────────────────────────────────────────────────────────────────── 8. §4 trimesh
md(
"## 4. trimesh — 메쉬의 표준 컨테이너이자 품질 검사관",
"",
f"**무엇** — 파이썬 3D 삼각형 메쉬 라이브러리(버전 {VER['trimesh']} ← 출처: 실제 설치 환경;",
"MIT 라이선스, github.com/mikedh/trimesh). 이 프로젝트에서는 네 가지 역할을 한다",
"← 출처: src/cadkit.py:15 (\"메쉬 컨테이너 · 프리미티브 · 스무딩 · 서브디비전 · 검증\"):",
"",
"1. **컨테이너/IO** — 정점·면을 담고 OBJ 등으로 읽고 쓴다.",
"2. **프리미티브** — `creation.box/cylinder/icosphere/capsule` 을 cadkit 이 얇게 감싼다",
"   ← 출처: src/cadkit.py:329-358 (`box`, `cyl`, `sphere`, `capsule`).",
"3. **검증** — `is_watertight`(구멍 없음), `is_winding_consistent`(감김 일관), `volume` 부호",
"   (법선이 안쪽이면 부피가 음수!), `nondegenerate_faces`(넓이 0 삼각형 탐지). §2.5 의",
"   \"몇 달간 못 잡은 버그\"류를 **수치로 자동 적발**한다 ← 출처: src/cadkit.py:124-135",
"   (`Assembly.check`).",
"4. **불리언 인터페이스** — `trimesh.boolean.union(..., engine=\"manifold\")` 처럼 계산 엔진을",
"   갈아끼울 수 있는 표준 창구 ← 출처: src/cadkit.py:73, 93.",
"",
"**왜 trimesh 가 표준인가** — numpy 배열을 그대로 쓰는 가벼운 API, 순수 파이썬 + 선택적",
"가속, 그리고 위 검증 속성들이 property 하나로 제공된다. 검토했던 대안: **open3d**(포인트클라우드",
"·시각화 중심으로 무겁고 CSG 없음), **pymeshlab**(필터 파이프라인 API 라 파라메트릭 조립에",
"부적합), **Blender bpy**(§9 에서 따로 설명). 메쉬를 \"numpy 로 조립해서 검증하고 내보내는\"",
"용도라면 trimesh 가 사실상 유일한 표준이다.",
"",
"**어떻게** — 모든 파트는 `Assembly.add` 를 지나며 4단계 정리를 받는다: 퇴화면 제거 → 정점",
"병합 → 미사용 정점 제거 → 법선 바깥 정렬(`fix_normals` + 부피 음수면 `invert`)",
"← 출처: src/cadkit.py:44-58 (\"여기서 걸러야 PO/SBR 의 조명판정(n̂·û>0)이 오염되지 않는다\").",
"각진 로프트는 `smooth`(Taubin 스무딩 + 선택적 서브디비전)로 실물처럼 다듬는다",
"← 출처: src/cadkit.py:318-326.",
),

# ────────────────────────────────────────────────────────────────── 9. §5 manifold3d
md(
"## 5. manifold3d — 견고한 불리언 엔진",
"",
f"**무엇** — 3D 불리언(합집합·차집합·교집합) 전용 C++ 엔진의 파이썬 바인딩(버전",
f"{VER['manifold3d']} ← 출처: 실제 설치 환경; Apache-2.0, github.com/elalish/manifold).",
"trimesh 가 `engine=\"manifold\"` 로 백엔드로 호출한다 ← 출처: src/cadkit.py:16, 73.",
"",
"**왜 불리언이 어려운가** — 종이공작에 비유하면, 두 입체의 합집합은 \"서로 뚫고 들어간 종이",
"상자 두 개를 교선(交線)을 따라 정확히 오려 붙이는\" 작업이다. 교선 계산은 부동소수점 오차에",
"극도로 민감해서, 순진한 구현은 (a) 미세한 틈이 남아 watertight 가 깨지거나 (b) 면이 겹쳐",
"비다양체(non-manifold: 한 모서리에 면이 3개 이상 붙는 등 물리적으로 불가능한 상태)가 되기",
"일쑤다. 불리언은 **메쉬 연산 중 가장 잘 깨지는 연산**이다.",
"",
"**왜 manifold 인가** — 이 엔진은 이름 그대로 \"입력이 다양체(manifold)면 출력도 항상",
"다양체\"를 설계 목표로 하는 최신 엔진이고(견고성 보장), 병렬화로 빠르며, trimesh 가 공식",
"백엔드로 지원해 `pip install manifold3d` 한 줄로 붙는다. 검토했던 대안: **Blender 엔진**",
"(trimesh 의 다른 백엔드; 외부 프로그램 설치·프로세스 호출 필요), **OpenSCAD/CGAL**(정확하지만",
"매우 느리고 의존성이 무겁다). 서버에 GUI 없이 pip 만으로 재현 가능해야 하므로 manifold 가",
"유일한 실용해였다.",
"",
"**어떻게** — 두 군데서 쓴다 ← 출처: src/cadkit.py:66-98:",
"",
"* `Assembly.union_group` — 한 그룹 안의 파트들을 합집합으로 녹여 **겹친 부분의 내부 면을",
"  제거**한다 (\"PO/SBR 이 헛세지 않는다\"). 실패하면 그냥 둔다 — 합집합은 최적화일 뿐이라",
"  안전하게 후퇴한다 ← 출처: src/cadkit.py:82 주석.",
"* `Assembly.subtract` — 그룹에서 공구(tool) 메쉬를 **깎아낸다**(리세스·홈·구멍).",
"",
f"참고로 그룹 **사이**의 겹침(예: 동체 속에 박힌 배터리·PCB)은 의도된 설계라 남겨 두며, 그 양은",
f"Mavic 4 Pro 기준 전체 부피의 {ov_mav:.1f}%, 파트가 거의 안 겹치는 S1000+ 는 {ov_s1000:.2f}% 로",
"정량 추적한다 ← 출처: mesh_verify.json `F_overlap.*.overlap_pct_of_volume` (자세한 논의는",
"겹침 행렬을 다루는 편에서).",
),
code(
"# 불리언 합집합 데모 — 반쯤 겹친 상자 두 개를 하나의 껍질로 녹인다",
"import trimesh",
"a = trimesh.creation.box(extents=(1, 1, 1))          # 1x1x1 상자",
"b = trimesh.creation.box(extents=(1, 1, 1))",
"b.apply_translation([0.5, 0.5, 0.0])                 # 반쯤 겹치게 이동",
"u = trimesh.boolean.union([a, b], engine=\"manifold\")  # manifold3d 가 실제 계산",
"",
"print(\"합치기 전 면 수 :\", len(a.faces) + len(b.faces))",
"print(\"합친 후  면 수 :\", len(u.faces), \"(교선을 따라 새 삼각형이 생김)\")",
"print(\"watertight?    :\", u.is_watertight)",
"print(f\"부피           : {u.volume:.4f}  (겹침 0.5*0.5*1=0.25 가 한 번만 계산돼 1+1-0.25=1.75)\")",
),

# ────────────────────────────────────────────────────────────────── 10. §6 scipy
md(
"## 6. scipy — 단면을 매끈하게 잇는 스플라인",
"",
f"**무엇** — 과학계산 라이브러리(버전 {VER['scipy']} ← 출처: 실제 설치 환경; BSD, scipy.org).",
"이 프로젝트에서는 단 하나, `scipy.interpolate.CubicSpline`(3차 스플라인 보간)만 쓴다",
"← 출처: src/cadkit.py:30, 197-212 (`spline_sections`).",
"",
"**왜** — 동체의 폭·높이를 제어점 6개로만 지정하고 그 사이를 **매끈한 곡선**으로 채우고 싶다.",
"직선(선형) 보간은 제어점마다 꺾인 자국이 남는다 — 실제로 geom.py 의 구버전 프로펠러는",
"\"선형보간(numpy 없이)\" 으로 시위(chord)를 이었다 ← 출처: src/geom.py:341-346 주석. CubicSpline",
"은 기울기까지 연속(C²)이라 꺾임이 없고, 자동차 보닛처럼 부드러운 실물 곡면이 나온다.",
"자작 스플라인은 수치 안정성 검증이 부담이라 검토조차 하지 않았다 — 이건 바퀴의 재발명이다.",
"",
"**어떻게** — `spline_sections(xs, half_w, half_h, z_off)` 가 제어점을 CubicSpline 세 개(폭·높이",
"·중심 z)로 보간해 **초타원 단면 24~30장**을 뽑고, 이것이 그대로 `loft()` 의 입력이 된다",
"← 출처: src/cadkit.py:197-212. `z_off` 덕에 \"코가 살짝 처지는\" 실물 특징(nose drop)도 낸다",
"← 출처: src/drone_cad.py:113 (`zo` 배열의 `-nose_drop`).",
),

# ────────────────────────────────────────────────────────────────── 11. §7 cadkit 도감
md(
"## 7. `src/cadkit.py` 함수 도감 — 무엇을 만드는 함수인가",
"",
"cadkit 은 위 라이브러리들을 조합해 **CAD 동사(verb)** 를 제공한다. 함수 하나 = 모델링 동작",
"하나다 ← 출처: 각 행의 소스 위치(모두 src/cadkit.py) 및 사용처(src/drone_cad.py):",
"",
"| 함수 | 무엇을 만드나 | 어떻게 | 드론에서의 사용처 |",
"|---|---|---|---|",
"| `superellipse` | 초타원 단면 | 지수 n 으로 타원↔둥근 사각 사이 조절 | 동체·캐노피 단면 (drone_cad.py:107-124) |",
"| `rounded_rect` | 둥근 모서리 사각 단면 | shapely `buffer` 오프셋 | 팔(arm) 단면 (drone_cad.py:139-142) |",
"| `spline_sections` | 매끈하게 보간된 단면열 | scipy CubicSpline ×3 | 동체 제어점 6개→단면 30장 (drone_cad.py:110-115) |",
"| `loft` (cadkit.py:148) | 단면열을 이은 곡면 껍질 | 단면 등간격 재샘플 후 옆면 결합+앞뒤 캡 | 동체·캐노피·**프로펠러 날개** |",
"| `sweep` (cadkit.py:218) | 경로를 따라 민 관 | 접선 + 최소회전 프레임(parallel transport) | 접이식 팔, S1000+ 착륙다리 (drone_cad.py:129-142, 199-209) |",
"| `revolve` (cadkit.py:258) | 회전체 | (r,z) 프로파일을 z 축 둘레로 회전, r=0 은 꼭짓점으로 접음 | 모터 벨·프롭 허브·RTK 돔 (drone_cad.py:44-56) |",
"| `smooth` (cadkit.py:318) | 매끈해진 메쉬 | Taubin 스무딩(+서브디비전) | 로프트 직후 동체/캐노피 |",
"| `box`/`cyl`/`sphere`/`capsule` | 기본 입체 | trimesh.creation 래퍼 | 배터리·PCB·짐벌 볼·다리 등 |",
"| `Assembly` (cadkit.py:38) | 그룹(재질)별 파트 바구니 | add(정리)→union_group/subtract(불리언)→check(검증)→to_geom(변환) | 모든 기체의 최종 조립 |",
"",
"핵심 규약 세 가지 ← 출처: src/cadkit.py:20-24:",
"모든 파트는 **watertight** 로 만들고(검증 가능해짐), 파트마다 **그룹 이름**을 달아 재질의 단일",
"진리원(materials.py)과 연결하고, 마지막에 **geom.Mesh 로 변환**해 기존 파이프라인에 넘긴다.",
),

# ────────────────────────────────────────────────────────────────── 12. 그림
md(
"### 7.1 조립 순서로 보는 도구들 — build_stages",
"",
"![build_stages](outputs/figures/build_stages.png)",
"",
"**그림 1 — Mavic 4 Pro 파라메트릭 CAD 의 조립 순서** (파트 1개 = OBJ 1개 = Sionna 재질 1개)",
"← 출처: src/viz_mesh_reports.py:144-165 `fig_build_stages()` 가 생성. 각 단계가 곧 위 도감의",
"함수들이다:",
"",
"| 그림 속 단계 | 만든 함수 (도구) | 소스 |",
"|---|---|---|",
"| 1. body (superellipse loft) | `spline_sections`+`superellipse` → `loft` → `smooth` | drone_cad.py:107-115 `_body_folding` |",
"| 2. + canopy/battery lid | 같은 로프트 조합(더 납작한 돔, n=3.2) | drone_cad.py:118-124 `_canopy` |",
"| 3. + motors | `revolve` — 아웃러너 모터 벨 회전체 | drone_cad.py:44-51 `_motor_bell` |",
"| 4. + internal battery & PCB | `box` (trimesh.creation.box 래퍼) — 반투명으로 내장 표시 | drone_cad.py:321-322 |",
"| 5. + gimbal camera | `sphere` — 구형 Infinity 짐벌 볼 | drone_cad.py:148-158 `_gimbal_infinity` |",
"| 6. + propellers | NACA `_airfoil` 단면을 트위스트하며 `loft` | drone_cad.py:59-101 `_airfoil`+`_blade` |",
"",
"(접이식 기종의 팔은 `sweep` 으로 만들어 body 그룹에 합쳐지므로 단계 1 에 이미 포함돼 있다.",
f"Mavic 4 Pro 의 최종 그룹은 {mav['n_groups']}개: {mav_groups} ← 출처: mesh_verify.json",
"`A_geometry.mavic4pro.groups`.)",
"",
f"이렇게 조립된 Mavic 4 Pro 는 정점 {mav['n_verts']:,}개 · 삼각형 {mav['n_faces']:,}개다",
"← 출처: mesh_verify.json `A_geometry.mavic4pro`.",
),

# ────────────────────────────────────────────────────────────────── 13. §8 검증
md(
"## 8. 도구가 실제로 잡아낸 버그들 — \"검증 없는 자작\"과의 결별",
"",
"라이브러리 선택의 가치는 **검증이 실제로 버그를 잡을 때** 증명된다. 기록된 사례 두 건:",
"",
"1. **revolve 의 퇴화 삼각형** — 회전체 프로파일에서 r=0(축 위)인 링을 그대로 두면 같은 자리에",
"   정점이 세그먼트 수만큼 겹쳐 **넓이 0 삼각형이 쏟아진다**. trimesh 검증이 실제로 적발했다:",
"   \"모터 288개, 프로펠러 224개\" ← 출처: src/cadkit.py:262-264 docstring. 해결: r=0 링을",
"   꼭짓점(apex) 하나로 접는다 (cadkit.py:271-278).",
"2. **프로펠러 캡 법선 반전** — §2.5 에서 본, 자작 geom.py 시절 몇 달간 숨어 있던 버그",
"   ← 출처: src/geom.py:369-374. cadkit 체제에서는 `Assembly.check()` 가 watertight/부피",
"   부호/감김을 파트마다 검사하므로 같은 부류가 즉시 드러난다 ← 출처: src/cadkit.py:124-135.",
"",
"최종 산출물 전체가 이 검증을 통과한 상태다: 드론 5기 모두 검사 통과(ok=True), 중복 정점",
f"{dup_total}개, 미사용 정점 {unused_total}개",
"← 출처: mesh_verify.json `A_geometry.*.ok / dup_vertices / unused_vertices`.",
"또한 면을 4배로 잘게 쪼개도(서브디비전) RCS 계산 결과가 사실상 불변",
f"(면 {sub['faces_base']:,}→{sub['faces_fine']:,}개, 방위 평균 차이 {abs(sub['azavg_dbsm']['diff']):.1e} dB)",
"임이 확인돼, 메쉬 해상도가 결과를 왜곡하지 않음을 보였다 ← 출처: mesh_verify.json",
"`I_sbr_subdiv.subdivision_invariance` (수렴 이야기는 해당 편에서 자세히).",
),
code(
"# mesh_verify.json 에서 5기 전체의 기하 검증 요약 읽기 — 본문 수치의 원천",
"import json, os",
"V = json.load(open(os.path.join(\"outputs\", \"mesh_verify.json\"), encoding=\"utf-8\"))",
"print(f\"{'드론':12s} {'정점':>8s} {'삼각형':>8s} {'그룹':>4s}  검증\")",
"for k in V[\"meta\"][\"drones\"]:",
"    g = V[\"A_geometry\"][k]",
"    ok = \"PASS\" if g[\"ok\"] else \"FAIL\"",
"    print(f\"{k:12s} {g['n_verts']:8,d} {g['n_faces']:8,d} {g['n_groups']:4d}  {ok}\"",
"          f\"  (중복정점 {g['dup_vertices']}, 미사용 {g['unused_vertices']})\")",
"tot_v = sum(V['A_geometry'][k]['n_verts'] for k in V['meta']['drones'])",
"tot_f = sum(V['A_geometry'][k]['n_faces'] for k in V['meta']['drones'])",
"print(f\"{'합계':12s} {tot_v:8,d} {tot_f:8,d}\")",
),

# ────────────────────────────────────────────────────────────────── 14. §9 왜 코드인가
md(
"## 9. 왜 Blender·상용 CAD GUI 가 아니라 코드인가",
"",
"\"드론 모델링이면 Blender 나 Fusion 360 으로 그리면 되지 않나?\" — 진지하게 검토했고, 다섯",
"가지 이유로 코드를 골랐다:",
"",
"1. **파라메트릭 = 스펙 주입.** 모델의 목표 치수는 DJI 공식 제원(`src/drones.py` 의 `DroneSpec`",
"   — 대각선·프로펠러 지름·공식 외형 `envelope_mm` 등 ← 출처: docs/SPECS.md 의 제원+URL)에서",
"   **변수로** 들어간다. 제원이 바뀌면 숫자 하나 고치고 다시 실행하면 끝이다. GUI 모델은 치수",
"   변경이 수작업 재모델링이다.",
"2. **재현성.** `python make_drone.py` 한 줄로 누구나 같은 바이트의 메쉬를 얻는다. GUI 작업은",
"   손 기억에 의존해 재현이 안 된다 — 이 리포트 시리즈 전체가 \"생성기를 다시 돌리면 같은",
"   결과\" 원칙 위에 있다.",
"3. **버전 관리와 리뷰.** 코드는 git diff 로 \"동체 폭 계수 0.46→0.50\" 같은 변경이 한 줄로",
"   보인다. 바이너리 .blend 파일은 diff 불가.",
"4. **그룹→재질의 단일 진리원.** 파트마다 그룹 이름을 코드로 달아 두면 Sionna RadioMaterial",
"   과 PO 반사계수가 **한 곳(materials.py)** 에서 일관되게 붙는다 ← 출처: src/cadkit.py:22-23.",
"   GUI 에서 수십 개 파트에 이름을 손으로 달면 오타 하나가 재질 누락이 된다.",
"5. **환경 제약.** 작업 서버는 GUI 가 없고 설치 권한도 제한적이다(geom.py 탄생 배경과 동일",
"   ← 출처: src/geom.py:11). pip 로 깔리는 라이브러리만이 현실적 선택지였다.",
"",
"**검토한 대안들** — *Blender(bpy)*: 파이썬 API 는 있지만 수백 MB 설치 + GUI 지향 데이터 구조라",
"헤드리스 서버 파이프라인에 과하다. *OpenSCAD*: 코드 CAD 의 원조지만 별도 언어·외부 프로세스이고",
"메쉬 후처리(스무딩·검증)가 없다. *CadQuery/build123d*: 정밀 B-rep 커널(OCCT)이라 강력하지만",
"의존성이 무겁고, 우리 목적은 mm 정밀 기계도면이 아니라 **전파 계산용 외형**이라 삼각형 메쉬",
"직접 조립이 더 투명했다. 결국 \"numpy 배열 + pip 설치 + 삼각형 직접 관리\"라는 요구에 맞는",
"조합이 trimesh 생태계였다.",
),

# ────────────────────────────────────────────────────────────────── 15. 마무리
md(
"## 10. 정리와 재현",
"",
"| 층 | 도구 | 역할 한 줄 |",
"|---|---|---|",
"| 수치 기반 | numpy " + VER['numpy'] + " | 모든 좌표·변환의 공용 언어 |",
"| 자작 미니 | src/geom.py | 교육·이식성용 최소 삼각형 도구 + 최종 컨테이너(그룹별 OBJ 저장) |",
"| 2D 단면 | shapely " + VER['shapely'] + " | 초타원·둥근사각 단면과 재샘플 |",
"| 3D 조립 | trimesh " + VER['trimesh'] + " | 컨테이너·프리미티브·스무딩·**검증** |",
"| 불리언 | manifold3d " + VER['manifold3d'] + " | 견고한 union/difference 엔진 |",
"| 보간 | scipy " + VER['scipy'] + " | CubicSpline 로 매끈한 단면열 |",
"",
"(버전 ← 출처: 실제 설치 환경 ~/.venvs/py312 을 importlib.metadata 로 조회)",
"",
f"이 도구 상자로 만든 결과물: 드론 5기, 정점 {n_verts_total:,}개 · 삼각형 {n_faces_total:,}개,",
f"전 기체 기하 검증 통과({'모두 PASS' if all_ok else '일부 FAIL'})",
"← 출처: mesh_verify.json `A_geometry`.",
"",
"**재현 명령** (노트북 재생성 + 수치 원천 재검증 + 그림 재생성):",
"",
"```bash",
"# 1) 검증 수치(mesh_verify.json) 재계산",
"~/.venvs/py312/bin/python report_mesh/src/verify_mesh_suite.py",
"# 2) 그림(build_stages.png 등) 재생성",
"~/.venvs/py312/bin/python report_mesh/src/viz_mesh_reports.py",
"# 3) 이 노트북 재생성",
"~/.venvs/py312/bin/python report_mesh/src/make_mesh02.py",
"```",
"",
"**다음 편** → mesh03: 이 도구 상자로 다섯 기체를 실제로 조립하는 과정",
"(생성기: `src/make_mesh03.py`). 이전 편 ← mesh01: 시리즈 개요와 파이프라인 지도.",
),
]

nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "py312",
      "language": "python", "name": "py312"}, "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 5}
out = os.path.join(RM, "mesh02_tools.ipynb")
json.dump(nb, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("wrote", out, len(cells), "cells")
