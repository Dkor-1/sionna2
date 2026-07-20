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
"(numpy · shapely · trimesh · manifold3d · scipy) 위에서 만들어지고, 결과는 경량 컨테이너",
"(`src/geom.py` 의 `Mesh`)에 담겨 뒷단 파이프라인으로 흘러간다.",
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
"이 프로젝트의 3D 도구는 역할이 뚜렷한 **두 층**으로 되어 있다.",
"",
"1. **`src/geom.py` — Mesh 컨테이너 + 챔버·범용 프리미티브.** numpy 만 쓰는 경량 모듈로,",
"   메쉬를 담는 그릇(`.v`/`.f`/`.g`)과 챔버·데모용 기본 도형(box/cylinder/uv_sphere/",
"   pyramid_field 등)을 제공한다. **드론 제작 도구가 아니다.**",
"2. **`src/cadkit.py` — 라이브러리를 제대로 쓰는 CAD 툴킷.** trimesh + manifold3d + shapely +",
"   scipy 로 로프트·스윕·회전체·불리언·검증을 수행한다. 실제 드론 형상(눈물방울 동체, 익형",
"   프로펠러)은 이 층 위의 `src/drone_cad.py` 가 만든다.",
"",
f"메쉬 엔진은 `\"{engine}\"` 단일 경로다 ← 출처: mesh_verify.json `meta.mesh_engine`,",
"src/drones.py:244 (`_build_frame_raw` — \"CAD(trimesh+manifold3d 로프트/불리언) 단일 경로\").",
"즉 **모양을 계산하는 본체는 cadkit(라이브러리) 층**이고, geom.Mesh 는 결과를 담아",
"뒷단 파이프라인(장면 구성·RCS·마이크로도플러)으로 넘기는 **공용 컨테이너**다",
"← 출처: src/cadkit.py:24 (\"마지막에 geom.Mesh 로 변환한다 → 기존 파이프라인이 그대로 돈다\").",
"",
"왜 층을 나누나? — 드론 형상에는 불리언·로프트·스무딩·검증이라는 무거운 CAD 연산이 필요하고",
"(§2.5), 챔버 벽·흡수체 피라미드 같은 단순 형상과 파이프라인 인터페이스에는 그게 필요 없기",
"때문이다. 무거운 쪽은 라이브러리에 맡기고, 가벼운 쪽은 투명한 자작 코드로 유지한다.",
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
"## 2. `src/geom.py` — Mesh 컨테이너와 챔버·범용 프리미티브",
"",
"**무엇** — 이 프로젝트의 **공용 메쉬 컨테이너**. 메쉬를 딱 세 목록으로",
"표현한다: `.v`(정점 좌표), `.f`(삼각형 인덱스), `.g`(면별 **그룹 이름** = body/arm/motor/prop...)",
"← 출처: src/geom.py:41-48. 그룹 이름표는 나중에 부위별 색칠과 부위별 전파재질(Sionna",
"RadioMaterial) 부여에 쓰인다 ← 출처: src/geom.py:19-22. 컨테이너 외에 챔버·데모용",
"**범용 프리미티브**(직육면체·원기둥·구·흡수체 피라미드)도 제공한다 — 드론 형상 제작은",
"cadkit/drone_cad 층의 몫이고, geom.py 는 그 일을 하지 않는다(§0).",
"",
"**왜 numpy 만으로 자작인가** — 소스 주석에 이유가 적혀 있다 ← 출처: src/geom.py:12-13:",
"",
"> \"**'도형이 어떻게 만들어지는지' 코드로 눈에 보이게** 하기 위해서입니다.",
"> (사용자가 쉽게 이해하는 것이 이 프로젝트의 1순위 목표)\"",
"",
"컨테이너와 단순 도형에는 무거운 CAD 연산이 필요 없으므로, 이 층은 **단순함·투명함·교육**을",
"우선한다. box 하나가 코드 20줄이라, 삼각형이 어떤 순서로 감기는지(winding) 눈으로 따라갈 수 있다.",
"",
"**어떻게 — 제공하는 것들** ← 출처: src/geom.py 의 각 함수:",
"",
"| 함수 | 만드는 것 | 소스 위치 |",
"|---|---|---|",
"| `Mesh` (클래스) | 컨테이너 — .v/.f/.g + 변환·바운즈·그룹 조회 | src/geom.py:41 |",
"| `box` | 직육면체(정점 8개, 삼각형 12개) | src/geom.py:184 |",
"| `cylinder` | 원기둥·원뿔대(`r_top`) | src/geom.py:213 |",
"| `pyramid` / `pyramid_field` | 전파흡수체 피라미드 1개 / 피라미드 밭 | src/geom.py:247, 304 |",
"| `uv_sphere` | 구 — 극점은 삼각형 팬으로 퇴화면 방지 | src/geom.py:271 |",
"| `translate` / `rotate` / `scale` | 4×4 변환 행렬 | src/geom.py:157-178 |",
"| `write_obj_per_group` | 그룹별 .obj 저장 — \"OBJ 1개 = Sionna 재질 1개\" 규약 | src/geom.py:137-147 |",
),
code(
"# geom.py 맛보기 — 챔버·범용 프리미티브를 라이브러리 없이 삼각형만으로",
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
"### 2.5 왜 드론은 geom.py 로 만들지 않나 — CAD 요구사항 4가지",
"",
"실물 드론 외형에는 삼각형을 손으로 쌓는 방식이 감당 못 하는 연산 4가지가 필요하다.",
"`cadkit.py` 상단 주석이 그 목록이다 ← 출처: src/cadkit.py:5-12 (요지):",
"",
"* **불리언(CSG)** — 오목부·홈·리세스를 파고, 겹친 프리미티브의 **속에 파묻힌 면**을 없앤다.",
"* **로프트(loft)** — 단면이 변하는 매끈한 동체(눈물방울·허리 잘록)를 만든다.",
"* **스무딩/서브디비전** — 각진 다각기둥을 실물 같은 곡면으로 다듬는다.",
"* **검증** — watertight·법선 방향·winding 을 **기계가** 파트마다 확인한다. 눈으로는",
"  안쪽을 향한 법선 같은 결함을 놓치기 쉽다(렌더링에는 멀쩡해 보이는 경우가 많다).",
"",
"왜 RCS(레이더 반사 면적)에 중요한가: 형상이 각지거나 내부 면이 남거나 법선이 뒤집히면",
"전자기 계산(PO/SBR)이 실물과 다른 면을 \"보게\" 된다 ← 출처: src/drone_cad.py:23-26 (\"RCS 는",
"외형(투영면적)과 재질 분포가 결정한다. 실루엣이 틀리면 σ 가 틀린다\").",
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
"  docstring. 접이식 동체는 n≈2.9 를 쓴다 ← 출처: src/drone_cad.py:108 (`_body_folding` 의",
"  `n_pow=2.9`).",
"* `rounded_rect(w, h, r)` — 둥근 모서리 직사각형: 접이식 팔(arm)의 단면 ← 출처:",
"  src/drone_cad.py:130-143 (`_arm_folding` 이 이 단면을 스윕 경로에 태운다).",
"",
"프로펠러 단면(NACA 익형)도 shapely Polygon 으로 조립된 뒤, 회전(피치각)·평행이동(스윕)을",
"`shapely.affinity` 로 처리한다 ← 출처: src/drone_cad.py:59-102 (`_airfoil`, `_blade`).",
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
"   (법선이 안쪽이면 부피가 음수!), `nondegenerate_faces`(넓이 0 삼각형 탐지). 눈으로는",
"   놓치기 쉬운 기하 결함을 **수치로 자동 적발**한다 ← 출처: src/cadkit.py:124-135",
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
"직선(선형) 보간은 제어점마다 접선이 불연속이라 꺾인 자국이 남는다. CubicSpline",
"은 기울기까지 연속(C²)이라 꺾임이 없고, 자동차 보닛처럼 부드러운 실물 곡면이 나온다.",
"자작 스플라인은 수치 안정성 검증이 부담이라 검토조차 하지 않았다 — 이건 바퀴의 재발명이다.",
"",
"**어떻게** — `spline_sections(xs, half_w, half_h, z_off)` 가 제어점을 CubicSpline 세 개(폭·높이",
"·중심 z)로 보간해 **초타원 단면 24~30장**을 뽑고, 이것이 그대로 `loft()` 의 입력이 된다",
"← 출처: src/cadkit.py:197-212. `z_off` 덕에 \"코가 살짝 처지는\" 실물 특징(nose drop)도 낸다",
"← 출처: src/drone_cad.py:114 (`zo` 배열의 `-nose_drop`).",
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
"| `superellipse` | 초타원 단면 | 지수 n 으로 타원↔둥근 사각 사이 조절 | 동체·캐노피 단면 (drone_cad.py:108-127) |",
"| `rounded_rect` | 둥근 모서리 사각 단면 | shapely `buffer` 오프셋 | 팔(arm) 단면 (drone_cad.py:140-143) |",
"| `spline_sections` | 매끈하게 보간된 단면열 | scipy CubicSpline ×3 | 동체 제어점 6개→단면 30장 (drone_cad.py:111-115) |",
"| `loft` (cadkit.py:148) | 단면열을 이은 곡면 껍질 | 단면 등간격 재샘플 후 옆면 결합+앞뒤 캡 | 동체·캐노피·**프로펠러 날개** |",
"| `sweep` (cadkit.py:218) | 경로를 따라 민 관 | 접선 + 최소회전 프레임(parallel transport) | 접이식 팔, S1000+ 착륙다리 (drone_cad.py:130-143, 200-212) |",
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
"| 1. body (superellipse loft) | `spline_sections`+`superellipse` → `loft` → `smooth` | drone_cad.py:108-116 `_body_folding` |",
"| 2. + canopy/battery lid | 같은 로프트 조합(더 납작한 돔, n=3.2) | drone_cad.py:119-127 `_canopy` |",
"| 3. + motors | `revolve` — 아웃러너 모터 벨 회전체 | drone_cad.py:44-51 `_motor_bell` |",
"| 4. + internal battery & PCB | `box` (trimesh.creation.box 래퍼) — 반투명으로 내장 표시 | drone_cad.py:322-323 |",
"| 5. + gimbal camera | `sphere` — 구형 Infinity 짐벌 볼 | drone_cad.py:149-159 `_gimbal_infinity` |",
"| 6. + propellers | NACA `_airfoil` 단면을 트위스트하며 `loft` | drone_cad.py:59-102 `_airfoil`+`_blade` |",
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
"## 8. 검증이 빌드에 박혀 있다 — 무엇을 잡고, 지금 결과는 어떤가",
"",
"라이브러리 선택의 가치는 **검증이 결함을 기계적으로 걸러낼 때** 증명된다. 검증은 두 겹이다:",
"",
"1. **생성 단계에서 결함을 원천 차단** — 예: `revolve` 는 r=0(축 위) 프로파일 점을 링이 아니라",
"   **꼭짓점(apex) 하나로 접는다**. 링으로 두면 같은 자리에 정점이 세그먼트 수만큼 겹쳐",
"   **넓이 0 퇴화 삼각형**이 쏟아지고, 퇴화면은 법선이 정의되지 않아 PO/SBR 의 조명판정을",
"   오염시키기 때문이다 ← 출처: src/cadkit.py:262-264 docstring, 271-278 (접기 구현).",
"   `Assembly.add` 도 파트마다 퇴화면 제거→정점 병합→법선 바깥 정렬을 강제한다 (cadkit.py:44-58).",
"2. **조립 후 파트별 검사** — `Assembly.check()` 가 watertight(구멍)·부피 부호(안쪽 법선)·",
"   winding(감김 일관)을 파트마다 검사한다 ← 출처: src/cadkit.py:124-135. 안쪽 법선처럼",
"   렌더링으로는 멀쩡해 보이는 결함도 부피 부호 하나로 드러난다.",
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
"## 9. 왜 Blender 가 아니라 코드인가 — 그림 도구가 아니라 \"스펙 공장\"이 필요해서",
"",
"Blender 로도 이 드론들을 **만들 수는 있다**. 하지만 우리에게 필요한 건 그림 도구가 아니라",
"**숫자(공식 스펙)를 넣으면 모양이 나오는 공장**이다. 모델은 한 번 그리고 끝나는 그림이 아니라,",
"제원·재질·검증과 맞물려 계속 재생산되는 **파이프라인의 부품**이기 때문이다. 공장이어야 하는",
"이유는 셋이다:",
"",
"1. **스펙 → 모양이 자동이다.** 목표 치수는 DJI 공식 제원(`src/drones.py` 의 `DroneSpec` —",
"   대각선·프로펠러 지름·공식 외형 `envelope_mm` 등 ← 출처: docs/SPECS.md 의 제원+URL)에서",
"   **변수로** 들어간다. 제원이 바뀌면 숫자 하나 고치고 재실행하면 5기 전부가 다시 나온다.",
"   GUI 모델은 치수 변경이 곧 수작업 재모델링이다.",
"2. **부위 = 재질이 자동으로 붙는다.** 파트마다 그룹 이름이 코드로 붙어, Sionna RadioMaterial",
"   과 PO 반사계수가 **한 곳(materials.py)** 에서 일관되게 연결된다 ← 출처: src/cadkit.py:22-23.",
"   수십 개 파트에 GUI 로 이름을 손으로 달면 오타 하나가 곧 재질 누락 사고다.",
"3. **재현과 검증이 자동이다.** 생성기 한 줄로 누가 돌려도 같은 바이트의 메쉬가 나오고,",
"   \"동체 폭 계수 0.46→0.50\" 같은 변경이 git diff 한 줄로 보이며(바이너리 .blend 는 diff 불가),",
"   §8 의 검증 스위트가 **빌드 게이트**로 매번 돈다.",
"",
"같은 \"코드 CAD\" 축의 대안(OpenSCAD, CadQuery/build123d, Blender bpy 스크립팅)도 있지만,",
"numpy 배열로 삼각형을 직접 다루며 pip 만으로 깔리는 trimesh 생태계가 위 세 요구와 기존",
"파이프라인(geom.Mesh → RCS/렌더)에 가장 잘 맞물렸다.",
),

# ────────────────────────────────────────────────────────────────── 15. 마무리
md(
"## 10. 정리와 재현",
"",
"| 층 | 도구 | 역할 한 줄 |",
"|---|---|---|",
"| 수치 기반 | numpy " + VER['numpy'] + " | 모든 좌표·변환의 공용 언어 |",
"| 컨테이너 | src/geom.py | Mesh 컨테이너(v/f/g·그룹별 OBJ 저장) + 챔버·범용 프리미티브 |",
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
"**다음 편** → mesh03: 모든 숫자와 모델의 출처 — 공식 스펙·실기체 스캔·외부 CAD 와 라이선스",
"(생성기: `src/make_mesh03.py`). 이전 편 ← mesh01: 시리즈 개요와 파이프라인 지도.",
),
]

nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "py312",
      "language": "python", "name": "py312"}, "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 5}
out = os.path.join(RM, "mesh02_tools.ipynb")
for _i, _c in enumerate(nb["cells"]):
    _c["id"] = f"m02-{_i:02d}"

json.dump(nb, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("wrote", out, len(cells), "cells")
