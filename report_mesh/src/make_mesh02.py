# -*- coding: utf-8 -*-
"""make_mesh02.py — mesh02 ipynb 생성기. ⚠ 이 파일이 소스다.

mesh02 — "도구 상자: 어떤 파이썬 라이브러리를 왜 골랐나, 그리고 검사기는 무엇을 보나"
모든 수치는 원장에서 읽어 f-string 으로 주입한다(손 숫자 금지).
라이브러리 버전은 생성 시점에 실제 설치 환경(importlib.metadata)에서 읽는다.
⭐ 소스 **행 번호는 `inspect` 로 자동 주입**한다 — 손으로 적으면 다음 편집에서 곧바로 낡는다.
⏳ 프로펠러 축(날 법칙·기종별 두께·λ 대비 삼각형 크기)은 기체별 프로펠러 정본화 라운드가 정본.
"""
import inspect
import json, os, sys
import importlib.metadata as _im

HERE = os.path.dirname(os.path.abspath(__file__))
RM = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(RM, ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, HERE)
V = json.load(open(os.path.join(RM, "outputs", "mesh_verify.json"), encoding="utf-8"))

# ---- 실제 설치 환경에서 버전 읽기 (← 출처: /workspace/.venvs/py312, importlib.metadata) ----
VER = {p: _im.version(p) for p in ["numpy", "trimesh", "manifold3d", "shapely", "scipy"]}

# ---- JSON 수치 꺼내기 -------------------------------------------------------------
from mesh_ledger import ledger_order   # noqa: E402  (원장↔레지스트리 일치 강제)
import mesh_facts_0816 as F            # noqa: E402  (2026-08-16 원장 공용 로더)
DR = ledger_order(V)                       # = DRONES 레지스트리 전수
A = V["A_geometry"]
mav = A["mavic4pro"]
n_faces_total = sum(A[k]["n_faces"] for k in DR)
n_verts_total = sum(A[k]["n_verts"] for k in DR)
all_ok = all(A[k]["ok"] for k in DR)
dup_total = sum(A[k]["dup_vertices"] for k in DR)
unused_total = sum(A[k]["unused_vertices"] for k in DR)
engine = V["meta"]["mesh_engine"]
fc = V["meta"]["fc_ghz"]
lam_mm = V["meta"]["lam_hi_mm"]
_sbr = V.get("I_sbr_subdiv", {})
sub = _sbr.get("subdivision_invariance")
SBR_STALE = bool(_sbr.get("stale"))
mav_groups = ", ".join(A["mavic4pro"]["groups"].keys())

# ---- ⭐ 소스 행 번호 자동 주입 — 손으로 적으면 다음 편집에서 낡는다 ----------------
import cadkit as _ck      # noqa: E402
import drone_cad as _dc   # noqa: E402
import geom as _gm        # noqa: E402


def L(obj, attr=None) -> int:
    """함수/클래스의 **정의 시작 행 번호**를 소스에서 직접 읽는다."""
    t = getattr(obj, attr) if attr else obj
    return inspect.getsourcelines(t)[1]


CK = {n: L(_ck, n) for n in ["superellipse", "rounded_rect", "spline_sections", "loft",
                             "sweep", "revolve", "smooth", "Assembly", "box", "cyl",
                             "sphere", "capsule"]}
CK["Assembly.add"] = L(_ck.Assembly, "add")
CK["Assembly.union_group"] = L(_ck.Assembly, "union_group")
CK["Assembly.check"] = L(_ck.Assembly, "check")
DC = {n: L(_dc, n) for n in ["_motor_bell", "_airfoil", "_blade", "_body_folding",
                             "_canopy", "_arm_folding", "_gimbal_infinity"]}
GM_ = {n: L(_gm, n) for n in ["Mesh", "box", "cylinder", "pyramid", "pyramid_field",
                              "uv_sphere"]}
GM_["write_obj_per_group"] = L(_gm.Mesh, "write_obj_per_group")   # Mesh 의 메서드다

# ---- 겹침 — 부피 % 가 아니라 재질 가중(A·|Γ|²) + 담는 쪽의 불투명 여부 -------------
OVL = {k: F.MAT["fleet"][k] for k in DR}
ovl_worst = max(DR, key=lambda k: OVL[k]["po_overcount_opaque_dB"])
ovl_best = min(DR, key=lambda k: OVL[k]["po_overcount_opaque_dB"])


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
"# mesh02 — 도구 상자: 어떤 라이브러리를 왜 골랐고, 검사기는 무엇을 보나",
"",
*F.head_md(
    "mesh02",
    "이 드론들을 만드는 도구는 무엇이고, 그 도구로 만든 것을 무엇이 검사하며, "
    "그 검사가 아직 못 보는 것은 무엇인가.",
    ["verify", "materials", "body_arms", "audit"]),
"",
f"**한 줄 요약** — 드론 {len(DR)}기의 CAD 메쉬(총 삼각형 {n_faces_total:,}개)는 딱 5개 라이브러리",
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
"### 0.1 이 노트북이 쓰는 실제 버전 — 그리고 왜 버전이 이 편의 주제인가",
"",
"아래 셀은 지금 커널(py312)에 실제로 설치된 버전을 출력한다. 리포트 생성 시점에 확인된 버전은",
f"numpy {VER['numpy']} · **trimesh {VER['trimesh']}** · manifold3d {VER['manifold3d']} ·",
f"shapely {VER['shapely']} · scipy {VER['scipy']} 였다",
"← 출처: 실제 설치 환경(`/workspace/.venvs/py312`, importlib.metadata 로 조회).",
"",
"⭐ **버전을 굵게 적는 이유** — 라이브러리 판이 바뀌면 **검사의 뜻이 바뀔 수 있다.**",
f"trimesh {VER['trimesh']} 에서 `split()` 의 `repair` 기본값이 **켜짐**이다. 그냥 부르면",
"구멍 뚫린 부품을 **조용히 메운 사본**을 돌려주고, 그 사본은 당연히 «수밀» 로 나온다.",
"",
"확인은 세 줄이면 된다 — 삼각형 1장을 뺀 상자를 두 방식으로 쪼개 보는 것이다(§8 셀).",
"그래서 이 저장소의 검사 경로는 **모든 `split` 에 `repair=False` 를 명시**한다",
"← 출처: `src/mesh_check.py` 머리말·`_split()`, `report_mesh/src/verify_mesh_suite.py` 머리말.",
"",
"이것이 이 편의 교훈이다: **도구 편에서 버전은 각주가 아니라 본문이다.**",
),
code(
"# trimesh 5.x 의 split 기본값 확인 — 검사기가 «수리한 사본» 을 보지 않게 하는 이유",
"import trimesh",
"b = trimesh.creation.box()",
"holed = trimesh.Trimesh(vertices=b.vertices, faces=b.faces[:-1], process=True)  # 삼각형 1장 뺌",
"for kw in [{}, {\"repair\": False}]:",
"    c = holed.split(only_watertight=False, **kw)[0]",
"    tag = \"기본값\" if not kw else \"repair=False\"",
"    print(f\"{tag:12s} 면 {len(c.faces):3d}  수밀 {str(c.is_watertight):5s}  부피 {abs(c.volume):.3f}\")",
"print(\"→ 기본값은 없는 삼각형을 지어 구멍을 메운다. 검사기가 하면 안 되는 일이다.\")",
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
f"| `Mesh` (클래스) | 컨테이너 — .v/.f/.g + 변환·바운즈·그룹 조회 | src/geom.py:{GM_['Mesh']} |",
f"| `box` | 직육면체(정점 8개, 삼각형 12개) | src/geom.py:{GM_['box']} |",
f"| `cylinder` | 원기둥·원뿔대(`r_top`) | src/geom.py:{GM_['cylinder']} |",
f"| `pyramid` / `pyramid_field` | 전파흡수체 피라미드 1개 / 피라미드 밭 "
f"| src/geom.py:{GM_['pyramid']}, {GM_['pyramid_field']} |",
f"| `uv_sphere` | 구 — 극점을 삼각형 팬으로 접어 **넓이 0 삼각형을 안 만든다** "
f"| src/geom.py:{GM_['uv_sphere']} |",
"| `translate` / `rotate` / `scale` | 4×4 변환 행렬 | src/geom.py |",
f"| `write_obj_per_group` | 그룹별 .obj 저장 — \"OBJ 1개 = Sionna 재질 1개\" 규약 "
f"| src/geom.py:{GM_['write_obj_per_group']} |",
"",
"(행 번호는 이 노트북을 만들 때 `inspect` 로 소스에서 직접 읽는다 — 손으로 적지 않는다.)",
"",
"⚠ **`uv_sphere` 의 극점에 대해 정확히 적는다.** 넓이 0 삼각형은 **0개**가 맞다.",
"다만 극점 자리에 정점이 세그먼트 수만큼 **겹쳐** 있어, 출하 인덱스 그대로는 그 구가",
"수밀이 아니다(합쳐 보면 수밀이다). 선택 인자 `uv_sphere(..., weld_poles=True)` 를 주면",
"삼각형 좌표·개수·부피가 **완전히 같은 채로** 정점만 2·(seg−1)개 줄어든다. 기본값은 꺼져",
"있어 예전과 비트동일하다 ← 출처: `outputs/mesh_inspect_materials_check_0816.json`",
"`uv_sphere`·`selftest_weld_poles`.",
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
"MIT 라이선스, github.com/mikedh/trimesh). 이 프로젝트에서 맡는 핵심 역할은 네 가지다",
"← 출처: src/cadkit.py:15 (\"메쉬 컨테이너 · 프리미티브 · 스무딩 · 서브디비전 · 검증\"; 여기서",
"스무딩·서브디비전은 아래 \"어떻게\" 문단에서 함께 다룬다):",
"",
"1. **컨테이너/IO** — 정점·면을 담고 OBJ 등으로 읽고 쓴다.",
"2. **프리미티브** — `creation.box/cylinder/icosphere/capsule` 을 cadkit 이 얇게 감싼다",
f"   ← 출처: src/cadkit.py:{CK['box']}~{CK['capsule']} (`box`, `cyl`, `sphere`, `capsule`).",
"3. **검증 API** — `is_watertight`(구멍 없음), `is_winding_consistent`(감김 일관), `volume` 부호",
"   (법선이 안쪽이면 부피가 음수), `nondegenerate_faces`(넓이 0 삼각형 탐지). 눈으로는",
f"   놓치기 쉬운 기하 결함을 수치로 드러낸다 ← 출처: src/cadkit.py:{CK['Assembly.check']}",
"   (`Assembly.check`).",
"   ",
"   ⭐ **다만 API 를 주는 것과 올바르게 부르는 것은 다르다.** §0.1 에서 봤듯 `split()` 의",
"   `repair` 기본값이 켜져 있어서, 그냥 부르면 «검사하려던 그 결함» 이 사라진 사본을 본다.",
"   그래서 우리 검사 경로는 `repair=False` 를 명시한다.",
"4. **불리언 인터페이스** — `trimesh.boolean.union(..., engine=\"manifold\")` 처럼 계산 엔진을",
"   갈아끼울 수 있는 표준 창구 ← 출처: src/cadkit.py `Assembly.union_group`.",
"",
"**왜 trimesh 가 표준인가** — numpy 배열을 그대로 쓰는 가벼운 API, 순수 파이썬 + 선택적",
"가속, 그리고 위 검증 속성들이 property 하나로 제공된다. 검토했던 대안: **open3d**(포인트클라우드",
"·시각화 중심으로 무겁고 CSG 없음), **pymeshlab**(필터 파이프라인 API 라 파라메트릭 조립에",
"부적합), **Blender bpy**(§9 에서 따로 설명). 메쉬를 \"numpy 로 조립해서 검증하고 내보내는\"",
"용도라면 trimesh 가 사실상 유일한 표준이다.",
"",
"**어떻게** — 모든 파트는 `Assembly.add` 를 지나며 4단계 정리를 받는다: 퇴화면 제거 → 정점",
"병합 → 미사용 정점 제거 → 법선 바깥 정렬(`fix_normals` + 부피 음수면 `invert`)",
f"← 출처: src/cadkit.py:{CK['Assembly.add']} (\"여기서 걸러야 PO/SBR 의 조명판정(n̂·û>0)이 오염되지 않는다\").",
"각진 로프트는 `smooth`(Taubin 스무딩 + 선택적 서브디비전)로 실물처럼 다듬는다",
f"← 출처: src/cadkit.py:{CK['smooth']}. 그 매끈함에는 **대가가 있다** — §6.1 에서 잰다.",
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
f"**어떻게** — 두 군데서 쓴다 ← 출처: src/cadkit.py:{CK['Assembly.union_group']} 이하:",
"",
"* `Assembly.union_group` — 한 그룹 안의 파트들을 합집합으로 녹여 **겹친 부분의 내부 면을",
"  제거**한다 (\"PO/SBR 이 헛세지 않는다\").",
"* `Assembly.subtract` — 그룹에서 공구(tool) 메쉬를 **깎아낸다**(리세스·홈·구멍).",
"",
"⚠ **지금 상태로 정확히 적을 것 두 가지.**",
"",
"1. **합집합이 실패해도 예외도 로그도 안 남는다.** `union_group` 이 예외를 통째로 삼킨다",
"   — «안전한 후퇴» 가 아니라 **조용한 실패**다. 합집합이 안 된 그룹은 내부 면이 그대로",
"   남고, PO 는 가림을 안 보므로 그 면적을 이중으로 센다.",
"2. **manifold 로 끝나지 않는다.** 합집합 **결과 자체는 수밀**인데, 그 뒤 우리 코드가",
"   퇴화면을 지우는 단계에서 구멍이 날 수 있다. 지금 mini2 셸이 그 상태다 —",
f"   합집합 결과 {F.MAT['mini2_body_hole']['per_drone']['mini2'][0]['union_faces']}면·수밀에서",
f"   넓이 {F.MAT['mini2_body_hole']['per_drone']['mini2'][0]['dropped_area_mm2']:.2e} mm² 슬리버",
f"   {F.MAT['mini2_body_hole']['per_drone']['mini2'][0]['dropped']}장을 지우며 경계 모서리",
f"   {F.MAT['mini2_body_hole']['per_drone']['mini2'][0]['boundary_after']}개가 열린다.",
f"   같은 자리에서 typhoonh480 은 {F.MAT['mini2_body_hole']['per_drone']['typhoonh480'][0]['dropped']}장을",
"   지우고도 수밀이 유지된다 ← 출처: `outputs/mesh_inspect_materials_check_0816.json` `mini2_body_hole`.",
),

# ── §5.1 겹침을 어떤 자로 재나 ──────────────────────────────────────────────
md(
"### 5.1 그룹 **사이**의 겹침 — 자를 세 번 갈았다",
"",
"동체 속에 박힌 배터리·기판처럼 그룹 사이 겹침은 **의도된 설계**다. 문제는 «얼마나 겹치나» 를",
"어떤 자로 재느냐다. 자에 따라 우선순위가 뒤집힌다:",
"",
"| 자 | 무엇을 세나 | 왜 부족한가 |",
"|---|---|---|",
"| ① 부피 % | 교차 부피 ÷ 전체 부피 | 산란은 부피가 아니라 **표면**에서 난다 |",
"| ② 표면적 % | 다른 부품 속에 묻힌 면적 비율 | 금속 1 cm² 와 플라스틱 1 cm² 를 같게 센다 |",
"| ③ **재질 가중 + 담는 쪽의 불투명 여부** | A·\\|Γ\\|² 로 세고, **유전체 셸 안**은 빼고 "
"**불투명 부품 안**만 센다 | 지금 쓰는 자 |",
"",
"③ 이 맞는 이유: 금속 상자가 **플라스틱 셸 안**에 있는 것은 결함이 아니라 설계다 —",
"전파는 셸을 투과해 그 금속을 본다. 진짜 이중계상은 **불투명한 부품 안**에 묻힌 면이다.",
"",
F.po_overcount_table(DR),
"",
"← 출처: `outputs/mesh_inspect_materials_check_0816.json` `fleet.*`.",
f"함대에서 가장 큰 것이 {ovl_worst}({OVL[ovl_worst]['po_overcount_opaque_dB']:+.2f} dB), 가장 작은 것이",
f"{ovl_best}({OVL[ovl_best]['po_overcount_opaque_dB']:+.2f} dB)다.",
"",
"⭐ **이 표가 주는 교훈**: «묻힌 면적이 40 %» 라는 문장과 «PO 가 0.5 dB 과대» 라는 문장은",
"같은 사실의 두 얼굴이고, **결정을 내릴 때 쓸 것은 뒤쪽**이다. 앞쪽만 보면 우선순위를 잘못 잡는다.",
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
f"← 출처: src/cadkit.py:{CK['spline_sections']}. `z_off` 덕에 \"코가 살짝 처지는\" 실물 특징(nose drop)도 낸다",
f"← 출처: src/drone_cad.py:{DC['_body_folding']} (`_body_folding` 의 `zo` 배열).",
),

# ── §6.1 매끈함의 대가 ─────────────────────────────────────────────────────
md(
"### 6.1 매끈함에는 대가가 있다 — 두 가지, 둘 다 «밝게» 쪽으로 틀린다",
"",
"«매끈해서 좋다» 만 적으면 절반이다. 지금 상태에서 실제로 재 본 두 가지를 적는다.",
"",
"**① 스플라인이 제어점 사이에서 넘친다(overshoot).** 3차 스플라인은 C² 연속을 지키느라",
"제어점 사이에서 값을 살짝 벗어난다. 형상표가 «잘록한 허리 → 넓은 어깨» 로 꺾이면 특히 그렇다.",
"실측:",
"",
"| 기체 | 무엇 | 형상표 의도 | 메쉬 실측 | 어긋남 |",
"|---|---|---|---|---|",
"| matrice4e | 셸 배(아래쪽) | −30.38 mm | −34.74 mm | **3.93 mm 더 아래** |",
"| mini5pro | 셸 최대 반폭 | 35.21 mm | 37.87 mm | **+7.6 %** |",
"| mini2 | 셸 높이 | 44.80 mm | 48.36 mm | **+8.0 %** |",
"",
"⭐ **부호가 늘 같은 쪽이다** — 항상 «더 크게(= 전파에 더 밝게)». 우연이 아니라 스플라인",
"넘침의 성질이다. 고치는 길은 둘이다: 제어점을 6 → 8~10 으로 늘리거나, 넘치지 않는 보간",
"(PCHIP, 단조 스플라인)으로 바꾸는 것. 둘 다 전 기종 메쉬가 바뀌므로 별도 라운드의 일이다.",
"",
"**② Taubin 스무딩이 끝단 캡을 안쪽으로 당긴다.** 로프트의 앞뒤 마감면은 삼각형 팬으로",
"닫혀 있는데, 스무딩이 그 테두리 링을 안으로 끌어당긴다. 실측(스무딩 0회 ↔ 4회 대조):",
"",
"| 기체 | 어디 | 스무딩 전 | 스무딩 후 | 남은 비율 |",
"|---|---|---|---|---|",
"| matrice4e | 기수 단면(반폭×반높이) | 41.02×36.88 mm | 23.42×21.31 mm | 약 57 % |",
"| mavic4pro | 꼬리 단면 | 42.63×28.57 mm | 24.58×16.43 mm | 약 57 % |",
"| phantom3 | 기수 단면 | 26.04×22.01 mm | 16.30×12.96 mm | 약 61 % |",
"",
"**가운데 4개 스테이션은 형상표를 0.5 % 안에서 재현한다** — 손실은 끝단 전용이다.",
"방위평균 투영면적으로는 −0.00~−0.06 dB 밖에 안 움직이므로 **레벨 결함이 아니다.**",
"흔들리는 것은 «기수를 정면으로 봤을 때의 정반사 형상» 이고, 그 크기는 아직 커널로 안 쟀다",
"(평판극한 상한 10 dB 는 상한일 뿐이다 — §4.4 의 «모른다» 목록).",
"",
"← 출처: `outputs/mesh_inspect_body_arms_0816.json` `findings`(로프트 끝단 캡·스플라인 넘침).",
"고칠 자리는 이미 선택 인자로 뚫려 있다: `_body_folding(..., smooth_iters=)` 와",
"`_SHELL_SHAPE[key]['smooth_iters']`. **기본값이 옛 값이라 지금 메쉬는 비트동일하다.**",
),

# ────────────────────────────────────────────────────────────────── 11. §7 cadkit 도감
md(
"## 7. `src/cadkit.py` 함수 도감 — 무엇을 만드는 함수인가",
"",
"cadkit 은 위 라이브러리들을 조합해 **CAD 동사(verb)** 를 제공한다. 함수 하나 = 모델링 동작",
"하나다 ← 출처: 각 행의 소스 위치(모두 src/cadkit.py) 및 사용처(src/drone_cad.py):",
"",
"| 함수 | 무엇을 만드나 | 어떻게 | 대가(있으면) | 드론에서의 사용처 |",
"|---|---|---|---|---|",
f"| `superellipse` (:{CK['superellipse']}) | 초타원 단면 | 지수 n 으로 타원↔둥근 사각 사이 조절 "
f"| — | 동체·캐노피 단면 (`_body_folding` drone_cad.py:{DC['_body_folding']}) |",
f"| `rounded_rect` (:{CK['rounded_rect']}) | 둥근 모서리 사각 단면 | shapely `buffer` 오프셋 "
f"| — | 팔(arm) 단면 (`_arm_folding` drone_cad.py:{DC['_arm_folding']}) |",
f"| `spline_sections` (:{CK['spline_sections']}) | 매끈하게 보간된 단면열 | scipy CubicSpline ×3 "
f"| **제어점 사이 넘침** — 셸 배 3.93 mm·반폭 +7.6 %(§6.1) | 동체 제어점 6개→단면 24~30장 |",
f"| `loft` (:{CK['loft']}) | 단면열을 이은 곡면 껍질 | 단면 등간격 재샘플 후 옆면 결합+앞뒤 캡 "
f"| — | 동체·캐노피·⏳프로펠러 날 |",
f"| `sweep` (:{CK['sweep']}) | 경로를 따라 민 관 | 접선 + 최소회전 프레임 "
f"| — | 접이식 팔·착륙다리 |",
f"| `revolve` (:{CK['revolve']}) | 회전체 | (r,z) 프로파일을 z 축 둘레로 회전, r=0 은 꼭짓점으로 접음 "
f"| — | 모터 벨·프롭 허브·RTK 돔 (`_motor_bell` drone_cad.py:{DC['_motor_bell']}) |",
f"| `smooth` (:{CK['smooth']}) | 매끈해진 메쉬 | Taubin 스무딩(+서브디비전) "
f"| **끝단 캡 단면의 약 43 % 손실**(§6.1) | 로프트 직후 동체/캐노피 |",
f"| `box`/`cyl`/`sphere`/`capsule` (:{CK['box']}~) | 기본 입체 | trimesh.creation 래퍼 "
f"| — | 배터리·기판·짐벌 볼·다리 |",
f"| `Assembly` (:{CK['Assembly']}) | 그룹(재질)별 파트 바구니 "
f"| add(정리)→union_group/subtract(불리언)→check(검증)→to_geom(변환) "
f"| union 실패가 조용하다(§5) | 모든 기체의 최종 조립 |",
"",
"(행 번호는 `inspect` 로 소스에서 직접 읽어 넣는다.)",
"",
"핵심 규약 세 가지 ← 출처: src/cadkit.py 머리말:",
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
"← 출처: report_mesh/src/viz_mesh_reports.py:152-178 `fig_build_stages()` 가 생성. 각 단계가 곧 위 도감의",
"함수들이다:",
"",
"| 그림 속 단계 | 만든 함수 (도구) | 소스 |",
"|---|---|---|",
f"| 1. body (superellipse loft) | `spline_sections`+`superellipse` → `loft` → `smooth` "
f"| drone_cad.py:{DC['_body_folding']} `_body_folding` |",
f"| 2. + canopy/battery lid | 같은 로프트 조합(더 납작한 돔) | drone_cad.py:{DC['_canopy']} `_canopy` |",
f"| 3. + motors | `revolve` — 아웃러너 모터 벨 회전체 | drone_cad.py:{DC['_motor_bell']} `_motor_bell` |",
"| 4. + internal battery & PCB | `box` (trimesh.creation.box 래퍼) — 반투명으로 내장 표시 | drone_cad.py `INTERNALS` |",
f"| 5. + gimbal camera | `sphere` — 구형 짐벌 볼 | drone_cad.py:{DC['_gimbal_infinity']} `_gimbal_infinity` |",
f"| 6. + propellers | ⏳ 익형 단면을 비틀며 `loft` | drone_cad.py:{DC['_airfoil']} `_airfoil` · "
f"{DC['_blade']} `_blade` |",
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
"## 8. 검사기는 무엇을 보고, 무엇을 못 보나",
"",
"라이브러리 선택의 가치는 **검사가 결함을 실제로 잡을 때** 증명된다. 그래서 이 절은",
"«무엇을 잡는다» 만큼 «무엇을 아직 못 잡는다» 를 같은 무게로 적는다.",
"",
"### 8.1 웰딩과 수리는 다른 일이다 — 하나는 해야 하고 하나는 하면 안 된다",
"",
"둘 다 «메쉬를 손본다» 로 뭉뚱그려지지만, 검사기에게는 정반대 성격이다.",
"",
"| | 무엇을 하나 | 검사기가 해도 되나 |",
"|---|---|---|",
"| **웰딩** (`process=True`) | 같은 자리에 겹친 **정점**을 하나로 합친다. 새 형상을 만들지 않는다 "
"| ✅ **해야 한다.** 우리 `geom.Mesh` 는 프리미티브마다 정점을 따로 쌓으므로, 웰딩 없이는 "
"멀쩡한 부품도 전부 «비수밀» 로 나온다 |",
"| **수리** (`repair=True`) | 없는 **삼각형**을 지어 구멍을 메운다 "
"| ⛔ **하면 안 된다.** 찾으려던 결함이 측정 직전에 사라진다 |",
"",
"← 출처: `src/mesh_check.py` 머리말이 정확히 이 구별을 규약으로 적는다.",
"",
"### 8.2 지금의 10 검사",
"",
F.checks_table(),
"",
"1~7 은 **부품(연결요소) 단위**로 돈다. 드론은 프리미티브의 합집합이라 전체 메쉬는 원래",
"수밀이 아니고, 의미 있는 검사는 부품별 검사이기 때문이다.",
"",
"**«통과» 는 «0» 이 아니라 «선언된 예산 안» 이다:**",
"",
F.budget_table(),
"",
"예산 표는 «이만큼이 옳다» 가 아니라 **«지금 이만큼이다» 라는 선언**이다.",
"그래서 새로 생기는 결함은 예산을 넘겨 **실패한다** — 숨기지 않으면서 회귀를 막는 방식이다.",
"",
"### 8.3 게이트가 어디에 걸려 있나 — 범위를 정확히",
"",
F.checker_table(),
"",
"출하 게이트는 `python src/drones.py`(부위별 OBJ 내보내기) **한 문**에 걸려 있다. 단서 셋:",
"",
"1. 환경변수 `MESH_GATE=off` 로 끌 수 있다.",
"2. RCS·렌더·마이크로도플러가 쓰는 **인메모리 `build_drone()` 은 이 문을 안 지난다** —",
"   전 기종 검사가 수십 초 걸려 import 시점에 걸지 않는다고 코드가 스스로 적는다.",
"3. ⇒ «메쉬를 쓰는 모든 경로가 검사를 통과한다» 는 지금 상태보다 강한 말이다.",
"",
"### 8.4 아직 못 보는 것",
"",
*[f"- {b}" for b in F.BLIND_SPOTS],
"",
"### 8.5 ⭐ 검사기를 만들 때의 규율 — 양성 대조부터 통과시켜라",
"",
"음성 대조(«문제 없는 것에 0 이 나온다»)만으로는 **«0 을 내는 검사기»** 와",
"**«0 이 맞는 대상»** 을 구별할 수 없다. 이 저장소에서 실제로 갈린 사례 둘:",
"",
"| 한때 보고된 것 | 무엇이 문제였나 | 제대로 재니 |",
"|---|---|---|",
"| «전 기체에 자기교차가 수천 쌍» | 삼각형-모서리 관통 판정의 구간 겹침 처리가 "
"**양성 대조를 통과하지 못했다** | 양성 4종·음성 5종을 다 통과시킨 뒤 재니 전 기체 **0** |",
"| «발 블록이 11~12 mm 떠 있다» | **단방향** 정점→면 거리 잣대. 큰 상자가 가는 봉을 "
"관통해 감싸면 모서리→표면 거리가 그만큼 나온다 | 양방향 + 내부 판정으로 **0 mm**(실제로는 겹침) |",
"",
"← 출처: `docs/MESH_AUDIT_0816.md` 부록 A·",
"`outputs/mesh_inspect_body_arms_0816.json` `retracted_by_this_round`.",
"",
"**지금 상태의 사실들** — 위 규율을 지켜 다시 잰 값이다:",
"",
f"- 드론 {len(DR)}기 전부 검사 통과. 중복 정점 {dup_total}개 · 미사용 정점 {unused_total}개",
"  ← 출처: `mesh_verify.json` `A_geometry.*`.",
"- **자기교차 0 건** · **안쪽을 향하는 법선 0 개**(전 기체·전 그룹, trimesh 수리를 전혀 거치지",
"  않고 출하 인덱스에서 손계산한 부호부피가 모두 양수) · **프롭 스윕 지름 오차 −0.000 %**",
"  ← 출처: `docs/MESH_AUDIT_0816.md` §③.",
),
code(
"# 예산 표를 직접 읽어 본다 — «통과» 가 «0» 이 아니라 «선언된 예산 안» 이라는 뜻",
"import os, sys",
"sys.path.insert(0, os.path.abspath(os.path.join(os.getcwd(), \"..\", \"src\")))",
"import mesh_check as MC",
"print(\"경계 모서리 예산 :\", MC.BOUNDARY_EDGE_BUDGET)",
"print(\"슬리버 예산     :\", MC.SLIVER_BUDGET)",
"print(\"치수 허용오차   :\", MC.DIM_TOL_PCT, \"| 대각 예외\", MC.DIM_DIAGONAL_TOL_PCT)",
),

# ── §8-2 선택 인자 규약 ────────────────────────────────────────────────────
md(
"## 8-2. 형상을 안 바꾸면서 고칠 자리를 뚫는 법 — 선택 인자와 지문 검증",
"",
"메쉬를 고치는 일에는 함정이 있다. **형상을 한 줄만 바꿔도 하류의 모든 σ·마이크로도플러**",
"**결과가 낡는다.** 그래서 «지금 고칠 준비» 와 «지금 고치기» 를 분리하는 규약을 쓴다:",
"",
"1. 고칠 자리를 **선택 인자**로 뚫는다.",
"2. **기본값은 옛 동작**으로 둔다.",
"3. 편집 전후 소스를 각각 불러 메쉬를 짓고 **지문**을 비교한다 —",
"   sha256(float32 정점 + int32 삼각형). 전 기종 비트동일이면 통과.",
"",
"지금 뚫려 있는 자리들:",
"",
"| 자리 | 무엇을 고칠 수 있게 되나 | 기본값 |",
"|---|---|---|",
"| `_body_folding(..., smooth_iters=)` | 끝단 캡 손실(§6.1)을 기종별로 | 옛 값 |",
"| `_gear_arm_spikes(..., inboard=)` (로터별 시퀀스 허용) | 다리 안쪽 치우침을 로터별로 | 옛 스칼라 |",
"| `geom.uv_sphere(..., weld_poles=)` | 극점 중복 정점 | 꺼짐 |",
"| `materials.make_material(..., strict=)` | 모르는 재질 키에 예외를 낼지 | 꺼짐(값 무변경) |",
"",
"← 출처: `outputs/mesh_inspect_body_arms_0816.json` `code_changes`·",
"`outputs/mesh_inspect_materials_check_0816.json` `code_changes`.",
"",
"### 도구가 «모른다» 를 말하게 만들기",
"",
"재질을 얻는 경로가 둘인데, 한쪽만 모르는 키를 막고 있었다. 지금은 양쪽 다 말한다:",
"",
"- `gamma_po('nylon')` → **예외**(KeyError). 처음부터 막혀 있었다.",
"- `make_material('nylon', …)` → **경고**(RuntimeWarning) + `materials.UNKNOWN_KEY_FALLBACKS`",
"  에 기록. `strict=True` 를 주면 예외. **아는 키의 숫자는 하나도 안 바뀐다.**",
"",
"⭐ 조용한 폴백은 «없는 값» 을 «그럴듯한 값» 으로 바꿔 놓는다. 그것이 이 저장소가 가장",
"경계하는 실패 방식이다 — **빈칸이 가짜 값보다 낫다.**",
),
code(
"# mesh_verify.json 에서 전 기종의 기하 검증 요약 읽기 — 본문 수치의 원천",
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
"   **변수로** 들어간다. 제원이 바뀌면 숫자 하나 고치고 재실행하면 전 기종이 다시 나온다.",
"   GUI 모델은 치수 변경이 곧 수작업 재모델링이다.",
"2. **부위 = 재질이 자동으로 붙는다.** 파트마다 그룹 이름이 코드로 붙어, Sionna RadioMaterial",
"   과 PO 반사계수가 **한 곳(materials.py)** 에서 일관되게 연결된다 ← 출처: src/cadkit.py:22-23.",
"   수십 개 파트에 GUI 로 이름을 손으로 달면 오타 하나가 곧 재질 누락 사고다.",
"3. **재현과 검증이 자동이다.** 생성기 한 줄로 누가 돌려도 같은 바이트의 메쉬가 나온다 —",
f"   실제로 지문(sha256) A/B 로 {len(DR)}종 **비트동일**을 확인한다(§8-2). \"동체 폭 계수",
"   0.46→0.50\" 같은 변경은 텍스트 한 줄로 보인다(바이너리 .blend 는 그렇게 못 본다).",
"   검사기는 §8.3 에 적은 범위에서 돈다.",
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
"(버전 ← 출처: 실제 설치 환경 `/workspace/.venvs/py312` 을 importlib.metadata 로 조회)",
"",
f"이 도구 상자로 만든 결과물: 드론 {len(DR)}기, 정점 {n_verts_total:,}개 · 삼각형 {n_faces_total:,}개,",
f"검사 결과 {'전 기종 통과' if all_ok else '일부 실패'}(«선언된 예산 안» 이라는 뜻 — §8.2)",
"← 출처: mesh_verify.json `A_geometry`.",
"",
"**이 편의 한 줄** — 도구는 능력을 주지만 **기본값이 규약을 정하지는 않는다.**",
"검사기가 무엇을 보는지는 우리가 명시해야 하고, 못 보는 것은 적어 둬야 한다.",
"",
*([
"",
f"⚠ **원장의 I 절(SBR)은 이월된 값이다** — GPU 없이 돌린 갱신이 GPU 증거를 지우지 않게",
"직전 원장에서 옮겨 왔고 `stale: true` 로 표시돼 있다. 다른 절과 세대가 다르므로",
"면 수·σ 를 나란히 인용하지 말 것.",
] if SBR_STALE else ([
"",
f"덤으로: 면을 4배로 잘게 쪼개도 SBR 결과가 사실상 불변이다",
f"(면 {sub['faces_base']:,}→{sub['faces_fine']:,}개, 방위평균 차이 "
f"{abs(sub['azavg_dbsm']['diff']):.1e} dB) ← 출처: mesh_verify.json `I_sbr_subdiv`.",
] if sub else [])),
"",
"**재현 명령**",
"",
"```bash",
"PY=/workspace/.venvs/py312/bin/python",
"cd /workspace/sionna",
"",
"# 1) 원장 재생성 — 이것부터. 생성기는 원장이 레지스트리와 다르면 일부러 멈춘다.",
"PYTHONPATH=src:benchmark $PY report_mesh/src/verify_mesh_suite.py --skip-sbr   # GPU 없이 A~H",
"# 2) 그림 재생성",
"PYTHONPATH=src:benchmark $PY report_mesh/src/viz_mesh_reports.py",
"# 3) 이 노트북 재생성",
"PYTHONPATH=src:benchmark $PY report_mesh/src/make_mesh02.py",
"```",
"",
"**다음 편** → mesh03: 모든 숫자와 모델의 출처 — 공식 제원·공식 CAD·실기체 스캔·타사 CAD 와",
"라이선스. 이전 편 ← mesh01: 시리즈 개요와 전체 지도.",
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
