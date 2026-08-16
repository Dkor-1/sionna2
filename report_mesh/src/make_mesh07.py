# -*- coding: utf-8 -*-
"""make_mesh07.py — mesh07 ipynb 생성기. ⚠ 이 파일이 소스다.

mesh07 — "검증 ① 기하 품질 — 삼각형이 건강한가"
  mesh_verify.json 의 A(geometry)/B(symmetry)/F(overlap) 섹션을 초보자 눈높이로 해설.
  모든 수치는 outputs/mesh_verify.json 에서 읽어 f-string 주입(손으로 적은 숫자 금지).
  배정 그림: triangle_quality.png, symmetry_chamfer.png, overlap_matrix.png,
             wireframe_s1000plus.png
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
RM = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(RM, ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
V = json.load(open(os.path.join(RM, "outputs", "mesh_verify.json"), encoding="utf-8"))

# ---------------------------------------------------------------- 수치 준비
#  ⭐ 2026-07-30 (Phase 3): 5종 하드코딩 → **원장 meta.drones**(= DRONES 레지스트리 전수)에서
#     유도. 표시명은 drones.drone_label. 예전엔 목록에 없는 기종이 표에서 조용히 빠졌다.
sys.path.insert(0, HERE)
from drones import drone_label            # noqa: E402
from mesh_ledger import ledger_order   # noqa: E402  (원장↔레지스트리 일치 강제)
import mesh_facts_0816 as MF          # noqa: E402  (2026-08-16 원장 공용 로더)
ORDER = ledger_order(V)
NAME = {k: drone_label(k) for k in ORDER}
A = V["A_geometry"]; B = V["B_symmetry"]; Fo = V["F_overlap"]
D = V["D_volume"]; META = V["meta"]
LAM = META["lam_hi_mm"]                                   # 57.5 mm @5.21 GHz

tot_faces = sum(A[k]["n_faces"] for k in ORDER)
tot_parts = sum(g["n_parts"] for k in ORDER for g in A[k]["groups"].values())
tot_groups = sum(A[k]["n_groups"] for k in ORDER)
tot_inward = sum(g["inward_normals"] for k in ORDER for g in A[k]["groups"].values())
tot_badwind = sum(g["bad_winding"] for k in ORDER for g in A[k]["groups"].values())
tot_degen = sum(g["degenerate"] for k in ORDER for g in A[k]["groups"].values())
tot_dup = sum(A[k]["dup_vertices"] for k in ORDER)
tot_unused = sum(A[k]["unused_vertices"] for k in ORDER)
n_wt = sum(int(g["watertight"].split("/")[0]) for k in ORDER for g in A[k]["groups"].values())
all_ok = all(A[k]["ok"] for k in ORDER)

fr95 = {k: B[k]["frame_only"]["chamfer_mm"]["p95"] for k in ORDER}
fu95 = {k: B[k]["full"]["chamfer_mm"]["p95"] for k in ORDER}
ovp = {k: Fo[k]["overlap_pct_of_volume"] for k in ORDER}

#  ⚠ 2026-08-16 (적대검증): §7 끝 문장이 «가장 큰 S1000+» 로 손타이핑돼 있었다 — 실제 함대에서
#     프롭이 가장 큰 기체는 m350rtk(533.4 mm)이고, x500v2 는 프롭이 커도 full p95 가 최저다.
#     단조 관계가 아니므로 세 기체를 원장·스펙에서 뽑아 문장에 주입하고 반례를 함께 적는다.
from drones import DRONES                      # noqa: E402
_prop_big = max(ORDER, key=lambda k: DRONES[k].prop_dia_mm)
_prop_small = min(ORDER, key=lambda k: DRONES[k].prop_dia_mm)
_sym_low = min(ORDER, key=lambda k: fu95[k])

s1k = A["s1000plus"]
mav_batt_ov = Fo["mavic4pro"]["pairs"][0]           # battery–body 가 항상 1위
mav_batt_vol = D["mavic4pro"]["volume_cm3"]["battery"]
s1k_top = Fo["s1000plus"]["pairs"][0]               # accent–arm

# ---------------------------------------------------------------- 셀 헬퍼
def md(*lines):
    src = "\n".join(lines).splitlines(keepends=True)
    return {"cell_type": "markdown", "metadata": {}, "source": src or [""]}

def cc(*lines):
    src = "\n".join(lines).splitlines(keepends=True)
    return {"cell_type": "code", "metadata": {}, "execution_count": None,
            "outputs": [], "source": src or [""]}

cells = []

# ---------------------------------------------------------------- 1. 표지
cells.append(md(
    "# mesh07 — 검증 ① 기하 품질: 삼각형이 건강한가",
    "",
    *MF.head_md(
        "mesh07",
        f"드론 {len(ORDER)}종의 삼각형이 기하학적으로 건강한가 — 그리고 «통과» 라는 말이 "
        "지금 정확히 무엇을 뜻하는가.",
        ["verify", "materials", "body_arms", "audit"]),
    "",
    f"**한 줄 요약** — 드론 {len(ORDER)}종·삼각형 {tot_faces:,}장·부위(그룹) {tot_groups}개·"
    f"닫힌 부품 {tot_parts}개를 전수 검사했다. 수밀 {n_wt}/{tot_parts}, 안쪽 법선 {tot_inward}건, "
    f"winding 불일치 {tot_badwind}건. "
    "⭐ **«통과» 는 «0» 이 아니라 «선언된 예산 안» 이라는 뜻**이고, 이 편은 그 예산이 무엇인지와 "
    "지금 예산을 쓰고 있는 항목이 무엇인지를 함께 적는다. "
    "좌우비대칭·부위겹침처럼 '결함처럼 보이는 것'은 왜 결함이 아닌지도 수치로 공개한다.",
    "",
    "## 용어 풀이 (이 리포트에 나오는 말)",
    "",
    "| 용어 | 뜻 |",
    "|---|---|",
    "| 메쉬(mesh) | 3D 형상을 작은 **삼각형 수천 장**으로 이어 붙여 표현한 것 — 종이접기 모형과 같다 |",
    "| watertight | \"물 한 방울 안 새는\" **닫힌 표면** — 구멍·틈이 전혀 없는 상태 |",
    "| 법선(normal) | 각 삼각형에 수직으로 꽂힌 화살표 — \"이 면의 **바깥**은 이쪽\" 표시 |",
    "| winding | 삼각형 꼭짓점을 감는 순서(시계/반시계). 오른손 법칙으로 법선의 앞뒤가 정해진다 |",
    "| 퇴화면(degenerate face) | 넓이가 0인 불량 삼각형 — 세 점이 한 직선/한 점에 겹친 것 |",
    "| chamfer 거리 | 두 점구름에서 서로 **가장 가까운 점까지의 거리**들의 통계 — 두 표면이 얼마나 닮았나 |",
    "| p50 / p95 | 하위 50%(중앙값) / 95% 지점 값 — p95는 \"최악 5%를 빼고 본 상한\" |",
    "| 카이럴(chiral) | 거울에 비추면 자기 자신과 겹칠 수 없는 성질 — 왼손과 오른손의 관계 |",
    "| 불리언(boolean) 연산 | 입체끼리의 교집합·합집합·차집합 계산 |",
    "| PO(물리광학) | 표면을 점으로 덮고 반사 전류를 적분해 RCS(레이더 반사 면적)를 구하는 계산법 |",
    "| SBR | GPU로 광선을 쏘아 튕김을 추적하는 RCS 계산법 — 가려진 면을 자동으로 걸러낸다 |",
    f"| λ(파장) | 전파 한 주기의 길이. 본 검증 최고 대역 5.21 GHz에서 **{LAM:.1f} mm** ← 출처: mesh_verify.json meta.lam_hi_mm |",
))

# ---------------------------------------------------------------- 2. 들어가며
cells.append(md(
    "## 0. 왜 '물리'보다 '기하'를 먼저 검사하나",
    "",
    "우리 드론 메쉬는 결국 **레이더 시뮬레이션의 입력**이다. RCS 적분(PO)도, GPU 광선추적(SBR)도,",
    "Sionna RT 의 레이트레이싱도 전부 \"삼각형이 옳다\"는 가정 위에서 돈다. 삼각형이 병들어 있으면",
    "그 위의 물리는 **조용히 틀린다** — 에러도 안 나고, 그럴듯한 숫자가 나오는데 틀린 숫자다.",
    "사람 건강검진과 같은 순서다: 피검사(기하)를 먼저 하고, 그 다음 운동능력(물리 수렴)을 본다.",
    "",
    "검증 스위트 전체는 9개 섹션(A~I)인데, 이 리포트는 그중 **기하 3종**만 깊게 다룬다:",
    "",
    "| 섹션 | 질문 | 이 리포트의 장 |",
    "|---|---|---|",
    "| **A** geometry | 삼각형이 기하학적으로 건강한가? (watertight·법선·winding·퇴화면·중복점·엣지길이) | §2~§5 |",
    "| **B** symmetry | 좌우대칭 기체가 정말 대칭인가? (미러 chamfer 거리) | §6 |",
    "| **F** overlap | 부위끼리 얼마나 겹치는가? (조립식 의도 겹침의 정량 공개) | §7 |",
    "",
    "← 출처: verify_mesh_suite.py 모듈 docstring 9~18행(9개 섹션 정의). 치수 대조(C)·부피(D)·재질(E)·",
    "실기체 스캔(G)·물리 수렴(H/I)은 다음 리포트들에서 다룬다.",
))

# ---------------------------------------------------------------- 3. 검사 대상
cells.append(md(
    f"## 1. 검사 대상 — 삼각형으로 지은 드론 {len(ORDER)}종",
    "",
    f"검사 대상은 파라메트릭 CAD 로 지은 드론 {len(ORDER)}종({', '.join(NAME[k] for k in ORDER)}),",
    f"합계 **삼각형 {tot_faces:,}장, 부위(그룹) {tot_groups}개, 닫힌 부품 {tot_parts}개**다",
    "← 출처: mesh_verify.json §A_geometry (n_faces·n_groups·groups.n_parts 합산).",
    "",
    f"아래는 {len(ORDER)}종 중 가장 큰 **S1000+** (8로터 옥토콥터)다. 가운데 wireframe 패널이 바로 이 리포트의",
    "주인공인 '삼각형'들이다 — 매끈해 보이는 몸체가 실은 작은 삼각형의 모자이크임을 볼 수 있다.",
    "",
    "![wireframe s1000plus](outputs/figures/wireframe_s1000plus.png)",
    "",
    f"*그림 1 — S1000+: 셰이딩(색=재질) / 와이어프레임(삼각형) / 상면도. 삼각형 {s1k['n_faces']:,}장,"
    f" 부위 {s1k['n_groups']}개(팔 8·모터 8·프로펠러 부품 {s1k['groups']['prop']['n_parts']}개 등).",
    "← 출처: 그림 생성 report_mesh/src/viz_mesh_reports.py fig_wireframes() 119행,",
    "수치 mesh_verify.json §A_geometry.s1000plus*",
    "",
    "여기서 '부품'은 서로 붙어 있는 삼각형 덩어리(연결요소) 하나를 말한다. 프로펠러 하나는",
    "허브 1개+날개 2장 = 부품 3개다. 검사는 **부품 단위**로 한다 — 드론 전체는 부품을 조립해 만든",
    "것이라 전체가 하나의 닫힌 표면일 이유가 없고, \"닫혔는가\"라는 질문이 의미를 갖는 최소 단위가",
    "부품이기 때문이다 ← 출처: src/mesh_check.py 머리말(\"의미 있는 검사는 부품별 검사다\").",
))

# ---------------------------------------------------------------- 4. 검사 도구
cells.append(md(
    "## 2. 검사 도구 — 왜 trimesh · cKDTree · manifold3d 인가",
    "",
    "검사 코드는 두 파일이다: `src/mesh_check.py`(A 의 핵심: watertight/법선/winding/퇴화면)와",
    "`report_mesh/src/verify_mesh_suite.py`(A 확장 + B 대칭 sec_B_symmetry() + F 겹침 sec_F_overlap()).",
    "",
    "**왜 쌓는 코드가 아니라 독립 감사자에게 묻나.** 우리 드론 메쉬는 `src/drone_cad.py`",
    "(trimesh·manifold3d 기반 파라메트릭 CAD)로 짓고, 결과를 `src/geom.py` 의 Mesh 컨테이너",
    "(꼭짓점 v·삼각형 f·부위 g)에 담는다 — geom.py 자체는 챔버·범용 프리미티브(box·cylinder·",
    "uv_sphere 등)를 제공하는 컨테이너 계층이다 ← 출처: src/drone_cad.py 모듈 docstring,",
    "src/drones.py build_frame()/build_propeller()(CAD 단일 경로). 검사를 **쌓는 코드 자신**에게",
    "맡기면 같은 가정을 두 번 믿게 된다 — 생성기가 \"이쪽이 바깥\"이라고 믿는 방향을 검사기도 그대로",
    "물려받으면, 둘 다 틀려도 아무도 모른다. 그래서 검사의 뼈대는 완성된 삼각형만 보고 판정하는",
    "**생성 논리와 독립인 잣대**(trimesh 의 수밀·winding·부호부피)다.",
    "",
    "⚠ **다만 «삼각형만 본다» 가 전부는 아니다.** 지금 검사기는 스펙 대조도 한다 —",
    "프롭 지름·로터 대각·공표 외형을 `DroneSpec` 의 수와 맞춰 보고(치수 검사), 로터별 날 비틀림",
    "방향이 회전방향과 맞는지 본다(손대칭성 검사 — **좌우 뒤집힌 기체를 잡는 장치**).",
    "삼각형만 보는 검사는 «단위를 1000 배 틀린 메쉬» 나 «거울상 기체» 를 통과시키기 때문이다.",
    "",
    "**검사기는 하나가 아니다** — 다섯이고 역할이 다르다:",
    "",
    MF.checker_table(),
    "",
    "도구별 채택 이유와 대안:",
    "",
    "| 도구 | 무엇에 쓰나 | 왜 이것인가 (대안은 왜 아닌가) |",
    "|---|---|---|",
    "| **trimesh** | watertight·winding·부호부피 판정 | 파이썬 메쉬 검증의 사실상 표준. `is_watertight`·`is_winding_consistent`·부호있는 `volume` 이 내장 — 직접 짜면 검증기 자체를 또 검증해야 한다 ← 출처: src/mesh_check.py check_mesh()(세 판정 모두 trimesh 내장 속성 호출) |",
    "| **scipy cKDTree** | 대칭 검사(B)의 최근접점 탐색 | 점이 최대 백만 개(S1000+ full "
    f"{B['s1000plus']['full']['n_points']:,}점 ← mesh_verify.json §B). 모든 쌍을 재는 브루트포스는 조 단위 연산이라 불가능, KD-트리는 점당 log 시간 |",
    "| **manifold3d** | 겹침 검사(F)의 불리언 교집합 | trimesh 기본 불리언 백엔드(Blender/OpenSCAD)는 외부 프로그램 설치가 필요하고 느리다. manifold 는 pip 휠 하나로 붙는 수치적으로 견고한 전용 엔진 ← 출처: verify_mesh_suite.py sec_F_overlap() 257행 `engine=\"manifold\"` |",
    "",
    "판정 기준도 코드에 그대로 있다: 부품이 닫혔는가(`is_watertight`), 닫힌 부품의 **부호있는 부피가",
    "양수**인가(음수 = 법선이 안쪽 = 뒤집힌 부품), winding 일관성, 퇴화면 개수",
    "← 출처: src/mesh_check.py `check_mesh()`.",
    "",
    "### 2.1 ⭐ 검사기는 자기가 보는 것을 고치지 않는다",
    "",
    "이 편에서 가장 중요한 규약이다. `trimesh.split()` 은 지금 판에서 **수리(repair)가 기본으로**",
    "**켜져 있다** — 그냥 부르면 구멍 뚫린 부품을 조용히 메운 사본을 돌려주고, 그 사본은 당연히",
    "«수밀» 로 나온다. 확인은 세 줄이면 된다(아래 셀).",
    "",
    "⇒ 이 저장소의 검사 경로는 **모든 `split` 에 `repair=False` 를 명시**하고, 수밀 여부를 참/거짓",
    "하나로 뭉개는 대신 **경계 모서리 수**를 함께 싣는다",
    "← 출처: `src/mesh_check.py` `_split()`·`_edge_defects()` · `report_mesh/src/verify_mesh_suite.py` 머리말.",
    "",
    "**구별할 것 — 웰딩은 유지한다.** 웰딩(`process=True`)은 같은 자리의 중복 «정점» 을 합치는 것이라",
    "새 형상을 만들지 않는다. 우리 `geom.Mesh` 는 프리미티브마다 정점을 따로 쌓으므로, 웰딩 없이는",
    "멀쩡한 부품도 전부 «비수밀» 로 나온다. 반면 수리는 없는 «삼각형» 을 짓는 일이라 검사기가 하면 안 된다.",
))

cells.append(cc(
    "# 검사기가 «수리한 사본» 을 보면 어떻게 되나 — 삼각형 1장 뺀 상자로 확인",
    "import trimesh",
    "b = trimesh.creation.box()",
    "holed = trimesh.Trimesh(vertices=b.vertices, faces=b.faces[:-1], process=True)",
    "for kw in [{}, {\"repair\": False}]:",
    "    c = holed.split(only_watertight=False, **kw)[0]",
    "    tag = \"split 기본값\" if not kw else \"split(repair=False)\"",
    "    print(f\"{tag:20s} 면 {len(c.faces):3d}  수밀 {str(c.is_watertight):5s}  부피 {abs(c.volume):.3f}\")",
))

# ---------------------------------------------------------------- 5. 코드: 메타
cells.append(cc(
    "# 이 리포트의 데이터 원본을 연다 — 모든 표는 이 JSON 을 그대로 읽어 만든다",
    "import json",
    'V = json.load(open("outputs/mesh_verify.json", encoding="utf-8"))',
    'meta = V["meta"]',
    'print("검증 대상 드론 :", ", ".join(meta["drones"]))',
    'print("메쉬 엔진      :", meta["mesh_engine"])',
    'print(f"최고대역 파장 λ : {meta[\'lam_hi_mm\']:.1f} mm  (WiFi 5.21 GHz — 엣지 길이의 잣대)")',
    'print("섹션           :", ", ".join(k for k in V if k != "meta"))',
))

# ---------------------------------------------------------------- 6. watertight
cells.append(md(
    "## 3. watertight — 물 새는 곳 없는 닫힌 표면인가",
    "",
    "**watertight** 는 말 그대로 \"물이 안 새는\" 상태다. 풍선을 생각하면 된다: 바늘구멍 하나라도",
    "있으면 '안'과 '밖'의 구분이 무너진다. 메쉬에서 구멍이란 이웃 삼각형이 없는 노출 모서리다.",
    "",
    "왜 이게 모든 검사의 **전제 조건**인가:",
    "",
    "1. **부피가 정의되려면** 닫혀 있어야 한다 — 뚫린 그릇의 용량은 물을 수 없다.",
    "   (부피→암시밀도 검사인 §D, 그리고 아래 §7 겹침 부피가 전부 이 위에 선다)",
    "2. **불리언 연산의 전제** — 교집합·합집합은 \"안/밖\"이 정의된 입체끼리만 가능하다.",
    "   verify_mesh_suite.py 의 겹침 검사도 watertight 부품만 불리언 대상으로 삼는다",
    "   ← 출처: verify_mesh_suite.py sec_F_overlap() 238행 주석 \"watertight 단일컴포넌트만 불리언 대상(견고성)\".",
    "3. **법선 방향 판정의 전제** — \"바깥을 향한다\"는 말은 안/밖이 있어야 성립한다. 닫힌 부품이라야",
    "   부호있는 부피의 부호로 안팎 뒤집힘을 기계적으로 잡을 수 있다 ← 출처: mesh_check.py check_mesh()(부호부피 판정).",
    "",
    f"**결과: {n_wt}/{tot_parts} 부품 수밀** ← 출처: mesh_verify.json",
    "§A_geometry 각 드론 groups.watertight (아래 코드 셀이 그대로 집계한다).",
    "",
    "### 3.1 «구멍 없음» 은 예산으로 선언한다",
    "",
    "출하 게이트가 쓰는 잣대는 «수밀 참/거짓» 이 아니라 **경계 모서리 수**다 — 삼각형 하나만 쓰는",
    "모서리를 세는 것이라, 구멍이 몇 개인지·얼마나 큰지가 숫자로 남는다. **원칙은 0** 이고,",
    "예외는 예산 표에 이름을 적어 선언한다:",
    "",
    MF.budget_table(),
    "",
    "← 출처: `src/mesh_check.py` 예산 표.",
    "",
    f"지금 예산을 쓰고 있는 항목은 **하나**다 — mini2 셸에 경계 모서리 3개(= 삼각형 정확히 1장이",
    "빠진 구멍, 넓이 약 0.35 mm² = λ²/21000)가 있다. 발생 자리는 불리언 합집합 **뒤** 의 퇴화면",
    f"제거 단계다: 합집합 결과 "
    f"{MF.MAT['mini2_body_hole']['per_drone']['mini2'][0]['union_faces']}면·수밀에서 넓이",
    f"{MF.MAT['mini2_body_hole']['per_drone']['mini2'][0]['dropped_area_mm2']:.2e} mm² 슬리버 1장을",
    "지우면서 열린다 ← 출처: `outputs/mesh_inspect_materials_check_0816.json` `mini2_body_hole`.",
    "",
    "**산란 자체에는 영향이 없다**(표면적 비중이 1e-8 % 급). 진짜 피해는 간접이다 —",
    "이 부품은 **안/밖 판정(`contains`)이 정의되지 않아서**, 내부 판정을 쓰는 검사가 이 부품을",
    "조용히 건너뛴다. 실제로 «내부 금속이 셸 안에 있나» 검사가 이 기체에서만 **UNKNOWN** 이다(§8.2).",
))

cells.append(cc(
    "# watertight/법선/winding/퇴화면 — 부위(그룹)별 전수 집계",
    'from drones import drone_label            # 표적 목록·표시명의 단일 출처',
    'ORDER = list(V["meta"]["drones"])          # = DRONES 레지스트리 전수(개수 하드코딩 없음)',
    'NAME = {k: drone_label(k) for k in ORDER}',
    'A = V["A_geometry"]',
    'hdr = f"{\'드론\':12s} {\'삼각형\':>7} {\'부위\':>4} {\'부품\':>4} {\'watertight\':>10} {\'법선안쪽\':>6} {\'winding깨짐\':>8} {\'퇴화면\':>5}  판정"',
    "print(hdr); print('-' * len(hdr))",
    "tot = dict(f=0, g=0, p=0, wt=0, inw=0, bw=0, dg=0)",
    "for k in ORDER:",
    "    g = A[k]['groups']",
    "    p = sum(v['n_parts'] for v in g.values())",
    "    wt = sum(int(v['watertight'].split('/')[0]) for v in g.values())",
    "    inw = sum(v['inward_normals'] for v in g.values())",
    "    bw = sum(v['bad_winding'] for v in g.values())",
    "    dg = sum(v['degenerate'] for v in g.values())",
    "    print(f\"{NAME[k]:12s} {A[k]['n_faces']:7,} {A[k]['n_groups']:4d} {p:4d} \"",
    "          f\"{wt:5d}/{p:<4d} {inw:6d} {bw:8d} {dg:5d}  {'통과' if A[k]['ok'] else '결함!'}\")",
    "    tot['f'] += A[k]['n_faces']; tot['g'] += A[k]['n_groups']; tot['p'] += p",
    "    tot['wt'] += wt; tot['inw'] += inw; tot['bw'] += bw; tot['dg'] += dg",
    "print('-' * len(hdr))",
    "print(f\"{'합계':12s} {tot['f']:7,} {tot['g']:4d} {tot['p']:4d} \"",
    "      f\"{tot['wt']:5d}/{tot['p']:<4d} {tot['inw']:6d} {tot['bw']:8d} {tot['dg']:5d}\")",
))

# ---------------------------------------------------------------- 7. 법선
cells.append(md(
    "## 4. 법선 방향 — 안팎이 뒤집힌 면은 물리를 조용히 망친다",
    "",
    "법선은 삼각형마다 붙은 \"바깥은 이쪽\" 화살표다. PO(물리광학)는 **어느 면이 레이더에 비추어지는지**를",
    "법선으로 판정한다: 입사 방향 û 와 법선 n̂ 의 내적이 양수인 면(n̂·û>0)만 반사에 참여시킨다",
    "← 출처: src/geom.py 290행 주석 \"PO(rcs_po)는 조명면을 n̂·û>0 로 고르므로 법선 방향이 맞아야 한다\".",
    "법선이 안쪽으로 뒤집힌 면은 이 판정을 **정반대로** 통과한다 — 보이는 면이 빠지고 뒤통수가 들어온다.",
    "에러는 안 난다. RCS 숫자만 틀어진다.",
    "",
    "**법선 검사가 잡는 것.** 안쪽 법선은 특정 도구의 실수가 아니라 삼각형 메쉬 일반의 상습",
    "취약점이고, 뒤집히기 쉬운 자리도 정해져 있다: **캡(뚜껑) 면** — 원기둥이나 날개 단면을 막는",
    "뚜껑은 몸통 옆면과 감는 방향 규약이 달라 한쪽만 뒤집히기 쉽다 — 그리고 **회전체의 꼭짓점(극점)**",
    "— 삼각형이 한 점으로 모이는 곳이라 감는 순서가 헷갈리기 쉽고 0-넓이 퇴화면도 함께 생기기 쉽다.",
    "이런 실수는 겉보기 렌더링으로는 안 보인다(대부분의 뷰어는 양면을 그린다). 법선 검사만이 잡는다.",
    "",
    "그래서 사람의 믿음 대신 기계 검사를 **메쉬가 밖으로 나가는 문**에 걸어 두었다: 닫힌 부품의",
    "부호있는 부피가 음수면(=안팎 뒤집힘) `mesh_check.assert_ok()` 가 예외를 던져 **OBJ 내보내기가",
    "실패**한다. 부호부피는 두 번 잰다 — trimesh 로 한 번, **trimesh 를 전혀 안 거치고 출하 인덱스에서**",
    "손으로 한 번. 그리고 검사기는 자기가 보는 것을 **고치지 않는다**(모든 `split` 이 `repair=False` 라",
    "구멍은 메워지지 않고 경계 모서리 수로 세어진다).",
    "⚠ 이 게이트가 덮는 범위는 정확히 내보내기 경로다. 메쉬를 메모리에서 만들어 바로 쓰는 계산은",
    "이 문을 지나지 않는다.",
    "← 출처: src/mesh_check.py check_mesh()·assert_ok() · src/drones.py 내보내기 진입점의 게이트 호출.",
    "",
    f"**현재 결과: {len(ORDER)}종 {tot_parts}개 부품 중 안쪽 법선 {tot_inward}건, winding 불일치 {tot_badwind}건**",
    "← 출처: mesh_verify.json §A_geometry groups.inward_normals·bad_winding (위 코드 셀 합계 행).",
))

# ---------------------------------------------------------------- 8. 퇴화면 등
cells.append(md(
    "## 5. 퇴화면 · 중복 꼭짓점 · 미사용 꼭짓점",
    "",
    "나머지 잔병 세 가지도 훑는다:",
    "",
    "- **퇴화면**: 넓이가 사실상 0 인 삼각형. 법선을 계산할 수 없고(0 으로 나누기), 레이트레이서에",
    "  따라 NaN 을 퍼뜨린다.",
    "- **중복 꼭짓점**(같은 자리 점 2개, 1 nm 격자 기준): 파일 용량 낭비이자, 이웃 관계가 끊긴",
    "  '가짜 틈'의 씨앗 ← 출처: verify_mesh_suite.py `sec_A_geometry()`.",
    "- **미사용 꼭짓점**(어떤 삼각형도 참조 안 함): 무해하지만 지저분함의 지표 — 생성 코드가 헛손질을",
    "  했다는 뜻이다 ← 출처: 같은 함수.",
    "",
    f"**결과: {len(ORDER)}종 합계 퇴화면 {tot_degen}장, 중복 {tot_dup}개, 미사용 {tot_unused}개** ← 출처:",
    "mesh_verify.json §A_geometry (degenerate·dup_vertices·unused_vertices, 아래 셀에서 확인).",
    "",
    "### 5.1 ⭐ «퇴화면 0» 은 어느 자로 잰 0 인가",
    "",
    "**자가 둘이고, 답이 다르다.** 이 구별을 안 적으면 위의 0 이 과장된다.",
    "",
    "| 자 | 무엇을 세나 | 함대 결과 |",
    "|---|---|---|",
    "| **절대** — 면적 < 1e-14 m² | 진짜 넓이 0 | **0장** |",
    "| **상대** — 최소 내각 < 0.5° | 아주 가늘고 긴 삼각형(슬리버) | 기종당 수백 장 |",
    "",
    "절대 잣대는 **기체 크기에 따라 뜻이 달라진다** — 같은 1e-14 m² 가 Mini 2 에서는 큰 삼각형이고",
    "S1000+ 에서는 먼지다. 그래서 지금 게이트는 상대 잣대를 **겸용**하고, 슬리버 개수를 기종별",
    "예산으로 선언한다(§3.1 의 `SLIVER_BUDGET`).",
    "",
    "**σ 에는 무해하다** — 슬리버가 차지하는 면적 비중이 0.0001~0.03 % 다. 그런데도 세는 이유는,",
    "슬리버는 **법선이 수치적으로 불안정**한데 우리 PO 의 조명 판정이 `n̂·û > 0` 이기 때문이다.",
    "⚠ 그 부호가 실제로 흔들리는지는 **아직 안 쟀다** — 지금은 감시만 하고 있다.",
    "",
    "**중복 꼭짓점도 같은 성격의 단서가 하나 있다.** 범용 프리미티브 `geom.uv_sphere` 는 극점",
    "자리에 정점이 세그먼트 수만큼 겹친다(넓이 0 삼각형은 **0장** — 이 축은 깨끗하다).",
    "출하 인덱스 그대로는 그 구가 수밀이 아니고, 합쳐 보면 수밀이다. 선택 인자",
    "`uv_sphere(..., weld_poles=True)` 가 삼각형을 하나도 안 바꾸고 그 정점만 줄인다(기본은 꺼짐)",
    "← 출처: `outputs/mesh_inspect_materials_check_0816.json` `uv_sphere`·`selftest_weld_poles`.",
))

cells.append(cc(
    "# 잔병 3종 — 드론별 상세",
    'print(f"{\'드론\':12s} {\'퇴화면\':>6} {\'중복점\':>6} {\'미사용점\':>7}")',
    "for k in ORDER:",
    "    g = A[k]['groups']",
    "    dg = sum(v['degenerate'] for v in g.values())",
    "    print(f\"{NAME[k]:12s} {dg:6d} {A[k]['dup_vertices']:6d} {A[k]['unused_vertices']:7d}\")",
))

# ---------------------------------------------------------------- 9. 삼각형 품질
cells.append(md(
    "## 6. 삼각형 품질 — 엣지 길이 vs 파장, 최소각 분포",
    "",
    "![triangle quality](outputs/figures/triangle_quality.png)",
    "",
    f"*그림 2 — (좌) {len(ORDER)}종의 엣지(삼각형 변) 길이 분포와 최고대역 파장 λ, (우) 삼각형 최소각의",
    "1퍼센타일/중앙값. ← 출처: 그림 report_mesh/src/viz_mesh_reports.py fig_tri_quality() 446행,",
    "수치 mesh_verify.json §A_geometry edge_mm·tri_min_angle_deg*",
    "",
    "**왜 엣지가 파장보다 충분히 짧아야 하나.** 메쉬의 곡면은 사실 평평한 삼각형의 모자이크다.",
    "전파 입장에서 표면의 '매끈함'은 파장 λ 를 자로 재서 판단한다: 삼각형 한 장이 λ 에 비해 충분히",
    "작으면 모자이크의 각진 단차가 파장 아래에 묻혀 **연속 곡면처럼** 산란하고, λ 보다 크면 각 삼각형이",
    "**개별 평면 거울**처럼 행동해 실물에 없는 반짝임(글린트)을 만든다. 디지털 사진과 같은 이치다 —",
    "픽셀이 충분히 작으면 눈에는 곡선으로 보인다. 여기서 픽셀 크기의 잣대가 파장이다.",
    "",
    f"기준 파장은 시뮬레이션 최고 대역인 WiFi 5.21 GHz 의 **λ = {LAM:.1f} mm** 로 잡았다 — 파장이",
    "가장 짧은 대역이 가장 엄격한 잣대이기 때문이다 ← 출처: verify_mesh_suite.py 44행",
    "`LAM_HI = C0/5.21e9` 주석 \"최고 대역 파장 — 엣지 길이 기준\".",
    "",
    "| 드론 | 엣지 p50 | 엣지 p95 | p95/λ | 최소각 p1 | 최소각 중앙값 |",
    "|---|---|---|---|---|---|",
    *[f"| {NAME[k]} | {A[k]['edge_mm']['p50']:.1f} mm | {A[k]['edge_mm']['p95']:.1f} mm | "
      f"{A[k]['edge_vs_lam52']['p95_over_lam']:.2f} | {A[k]['tri_min_angle_deg']['p1']:.1f}° | "
      f"{A[k]['tri_min_angle_deg']['median']:.1f}° |" for k in ORDER],
    "",
    "← 출처: mesh_verify.json §A_geometry (edge_mm, edge_vs_lam52, tri_min_angle_deg).",
    "",
    f"엣지의 95 % 가 λ 의 {min(A[k]['edge_vs_lam52']['p95_over_lam'] for k in ORDER):.2f}~"
    f"{max(A[k]['edge_vs_lam52']['p95_over_lam'] for k in ORDER):.2f}배 구간에 있다.",
    "곡면(몸체·캐노피)은 파장 대비 충분히 잘게 쪼개져 있다.",
    "",
    "⏳ **프로펠러의 삼각형 크기는 이 표에 섞어 읽으면 안 된다.** 프롭은 로터 1개당 삼각형 수가",
    "고정인데 프롭 지름은 기체마다 4배 이상 벌어져서, 큰 기체일수록 프롭 삼각형이 성기다.",
    "**이 축의 정본은 기체별 프로펠러 정본화 라운드**이므로 여기서는 자리만 남기고 값은 적지 않는다.",
    "",
    f"**현재 한계 — 최장 엣지는 λ 를 넘는다** (예: S1000+ 최장 {A['s1000plus']['edge_mm']['max']:.0f} mm"
    f" = {A['s1000plus']['edge_vs_lam52']['max_over_lam']:.1f}λ ← 출처: 같은 JSON). 이 긴 엣지들은",
    "배터리·PCB 같은 **직육면체(삼각형 12장짜리 상자)의 평면**과 팔 원기둥의 축방향에 있다. 평면과",
    "직선은 삼각형이 아무리 커도 기하가 **정확**하다 — 잘게 쪼개야 하는 것은 곡률이지 평면이 아니다.",
    "또 하나: PO 의 적분 밀도는 삼각형 크기와 무관하게 표면을 λ/10 간격 점으로 다시 덮어 확보하고,",
    "SBR 은 λ/12 광선 격자를 쓴다. 즉 엣지-파장 검사는 **형상 충실도**의 잣대이고, **적분 정밀도**는",
    "별도 수렴 검사(§H·§I, 물리 검증 리포트)로 잡는다 ← 출처: verify_mesh_suite.py sec_H(321행 lam/10·lam/20)·sec_I(399행 lam/12→lam/24).",
    "",
    f"**주의 — 최소각**: 1퍼센타일이 {min(A[k]['tri_min_angle_deg']['p1'] for k in ORDER):.1f}°까지",
    "내려가는 가늘고 긴 삼각형(슬리버)이 소수 존재한다 — 에어포일 뒤전(얇게 수렴하는 날개 꽁무니)과",
    "원기둥 캡 부채꼴이 원인이다. FEM(유한요소해석)이라면 병이지만, 우리 파이프라인은 삼각형별",
    "수치적분이 아니라 표면 점샘플(PO)·광선(SBR)을 쓰므로 슬리버에 둔감하다. 넓이 0(퇴화)만 아니면",
    "된다 — 그리고 퇴화면은 §5 에서 본 대로 0 장이다.",
))

cells.append(cc(
    "# 엣지 길이 vs 파장 — JSON 원본 그대로",
    'lam = V["meta"]["lam_hi_mm"]',
    'print(f"기준 파장 λ = {lam:.1f} mm (WiFi 5.21 GHz)\\n")',
    'print(f"{\'드론\':12s} {\'p50[mm]\':>8} {\'p95[mm]\':>8} {\'max[mm]\':>8} {\'p95/λ\':>6} {\'max/λ\':>6}")',
    "for k in ORDER:",
    "    e, r = A[k]['edge_mm'], A[k]['edge_vs_lam52']",
    "    print(f\"{NAME[k]:12s} {e['p50']:8.1f} {e['p95']:8.1f} {e['max']:8.1f} \"",
    "          f\"{r['p95_over_lam']:6.2f} {r['max_over_lam']:6.2f}\")",
))

# ---------------------------------------------------------------- 10. 대칭
cells.append(md(
    "## 7. 좌우대칭 — 기체는 대칭, 프로펠러는 일부러 비대칭",
    "",
    "드론은 좌우대칭으로 설계된 기계다(비행 안정성의 기본). 그러니 \"우리 메쉬도 정말 대칭인가\"는",
    "좋은 무결성 검사다. 방법: 표면을 4 mm 간격 점으로 덮고, y→−y 로 **거울상**을 만든 뒤, 거울상의",
    "각 점에서 원본의 가장 가까운 점까지 거리(chamfer)를 잰다. 완벽 대칭이면 이 거리는 샘플링 간격의",
    "절반(≈2 mm) 안에 들어야 한다 — 점이 4 mm 마다 찍히므로 거울점이 원본 점과 정확히 겹칠 수는 없고,",
    "최악에도 이웃 점까지 ~2 mm 이기 때문이다 ← 출처: verify_mesh_suite.py sec_B_symmetry() 145행",
    "(spacing=4e-3)·cKDTree 최근접 탐색 147행.",
    "",
    "![symmetry chamfer](outputs/figures/symmetry_chamfer.png)",
    "",
    "*그림 3 — 미러 chamfer p95(로그 눈금): 파랑=기체만(프로펠러 제외), 빨강=프로펠러 포함 전체.",
    "← 출처: 그림 viz_mesh_reports.py fig_symmetry() 301행, 수치 mesh_verify.json §B_symmetry*",
    "",
    "| 드론 | 기체만 p95 | 전체 p95 | 배율 |",
    "|---|---|---|---|",
    *[f"| {NAME[k]} | {fr95[k]:.2f} mm | {fu95[k]:.1f} mm | ×{fu95[k]/fr95[k]:.0f} |" for k in ORDER],
    "",
    "← 출처: mesh_verify.json §B_symmetry chamfer_mm.p95 (full/frame_only).",
    "",
    f"**기체만 보면 {len(ORDER)}종 전부 p95 ≤ {max(fr95.values()):.1f} mm ≤ 2 mm** — 즉 샘플링 해상도 안이다.",
    "기하학적으로는 사실상 완전 대칭이라는 뜻이다.",
    "",
    f"**그런데 프로펠러를 포함하면 {min(fu95.values()):.0f}~{max(fu95.values()):.0f} mm 로 뛴다.",
    "이것은 결함이 아니라 물리다.** 프로펠러 날개는 피치와 트위스트가 들어간 비틀린 곡면이라",
    "**카이럴**하다 — 거울에 비추면 반대손(반대 회전방향용) 날개가 되어 원본 어디에도 겹칠 짝이 없다.",
    "실제 드론도 인접 로터가 서로 반대로 돌도록 CW/CCW 프로펠러를 섞어 달며(반토크 상쇄), 우리 메쉬도",
    "로터마다 dir=+1/−1 을 교대로 준다 ← 출처: src/drones.py rotor_layout() 310~311행 docstring",
    "\"dir 은 인접 로터가 반대로 도는 멀티로터 관례(대각쌍 동일)\"·323행. 날개 장착 위상도 로터마다",
    "달라(base_ang 오프셋) 거울상과 어긋난다. verify_mesh_suite.py 의 sec_B docstring 도 같은 경고를",
    "박아 놨다: \"full 의 큰 p95 는 결함이 아니라 프로펠러 물리다. 기체 대칭성은 frame_only 로",
    "판정한다\" ← 출처: verify_mesh_suite.py 137~139행.",
    "",
    "**크기의 방향도 대체로 앞뒤가 맞는다** — 프로펠러가 클수록(=날개가 휩쓰는 반경이 클수록) 전체 p95 가 커지는",
    f"경향이 있다: 프롭이 가장 큰 {NAME[_prop_big]}({DRONES[_prop_big].prop_dia_mm:g} mm)가 {fu95[_prop_big]:.0f} mm 로 최대,",
    f"가장 작은 {NAME[_prop_small]}({DRONES[_prop_small].prop_dia_mm:g} mm)가 {fu95[_prop_small]:.0f} mm 다.",
    "⚠ 다만 **단조 관계는 아니다** —",
    f"{NAME[_sym_low]} 는 프롭이 {DRONES[_sym_low].prop_dia_mm:g} mm 나 되는데 전체 p95 가 {fu95[_sym_low]:.1f} mm 로 함대 최저다.",
    "장착 위상(base_ang)이 로터마다 어떻게 놓이느냐가 프롭 크기만큼 세게 실리기 때문이다.",
    "그래서 이 열은 «프롭이 대칭을 깨는 정도» 의 참고값이지 «프롭 크기의 자» 가 아니다.",
))

cells.append(cc(
    "# 대칭 chamfer — frame_only vs full (JSON 원본)",
    'Bm = V["B_symmetry"]',
    'print(f"{\'드론\':12s} {\'기체만 p95[mm]\':>13} {\'전체 p95[mm]\':>12} {\'샘플점(전체)\':>10}")',
    "for k in ORDER:",
    "    fr = Bm[k]['frame_only']['chamfer_mm']['p95']",
    "    fu = Bm[k]['full']['chamfer_mm']['p95']",
    "    print(f\"{NAME[k]:12s} {fr:13.2f} {fu:12.1f} {Bm[k]['full']['n_points']:10,}\")",
    'print("\\n기체만: 전부 2 mm 이하 = 4 mm 점 샘플링의 분해능 한계 안 → 사실상 완전 대칭")',
))

# ---------------------------------------------------------------- 11. 겹침
cells.append(md(
    "## 8. 부위 겹침 공개 — 조립식이라 서로 파고든다, 그리고 그게 설계다",
    "",
    "우리 드론은 부위(몸체·캐노피·배터리·모터·프로펠러…)를 **따로 닫힌 입체로 만들어 서로 밀어 넣는**",
    "조립식이다. 그래서 부위끼리 부피가 겹친다 — 배터리는 몸체 속에 통째로 들어가 있고, 모터 밑동은",
    "팔에 박혀 있다. 숨길 일이 아니라 **정량 공개**할 일이다: watertight 부품끼리 불리언 교집합을 돌려",
    "겹침 부피를 전부 쟀다 ← 출처: verify_mesh_suite.py sec_F_overlap() 233~270행(manifold 엔진,",
    "bbox 가 겹칠 때만 시도).",
    "",
    "![overlap matrix](outputs/figures/overlap_matrix.png)",
    "",
    "*그림 4 — 드론별 부위×부위 겹침 부피 행렬 [cm³]과 총부피 대비 %. ← 출처: 그림",
    "viz_mesh_reports.py fig_overlap() 418행, 수치 mesh_verify.json §F_overlap*",
    "",
    "| 드론 | 겹침 합계 | 총부피 대비 | 최대 겹침 쌍 |",
    "|---|---|---|---|",
    *[f"| {NAME[k]} | {Fo[k]['total_overlap_cm3']:.0f} cm³ | {ovp[k]:.2f}% | "
      f"{Fo[k]['pairs'][0]['a']}–{Fo[k]['pairs'][0]['b']} ({Fo[k]['pairs'][0]['overlap_cm3']:.0f} cm³) |"
      for k in ORDER],
    "",
    "← 출처: mesh_verify.json §F_overlap (total_overlap_cm3·overlap_pct_of_volume·pairs).",
    "",
    f"소비자 드론 4종은 {min(v for k, v in ovp.items() if k != 's1000plus'):.0f}~"
    f"{max(ovp.values()):.0f}% 씩 겹친다. 1위는 예외 없이 battery–body — 예컨대 Mavic 4 Pro 의",
    f"배터리 겹침 {mav_batt_ov['overlap_cm3']:.0f} cm³ 는 배터리 부피 {mav_batt_vol:.0f} cm³ 와",
    "같다. 즉 **배터리가 몸체 안에 100% 묻혀 있다** — 실물이 그렇듯이 ← 출처: §F_overlap.mavic4pro",
    "pairs[0] vs §D_volume.mavic4pro.volume_cm3.battery.",
    "",
    f"**S1000+ 만 {ovp['s1000plus']:.2f}%로 거의 0** 인 이유도 실물 구조 그대로다: 이 기체는 중앙",
    "허브에 팔·랜딩기어를 **볼트로 덧다는**(bolt-on) 산업용 프레임이라, 부위들이 서로 파고들 일 없이",
    f"면에서 만난다. 최대 쌍도 {s1k_top['a']}–{s1k_top['b']} {s1k_top['overlap_cm3']:.0f} cm³ 가 전부다",
    "← 출처: §F_overlap.s1000plus.",
    "",
    "**왜 불리언 union 으로 하나로 안 합쳤나** — 세 가지 이유다:",
    "",
    "1. **부위 = 재질 단위다.** 부위 하나가 OBJ 파일 하나, Sionna 전파 재질 하나에 대응한다",
    "   (몸체=플라스틱, 모터=금속, 프로펠러=얇은 플라스틱…). union 으로 한 덩어리로 녹이면 이 재질",
    "   경계가 사라진다 ← 출처: viz_mesh_reports.py fig_build_stages() 163~164행 캡션 \"each part =",
    "   one OBJ = one Sionna material\".",
    "2. **프로펠러는 돌아야 한다.** 마이크로도플러 시뮬레이션은 프로펠러 메쉬를 매 프레임 회전시킨다.",
    "   몸체와 한 덩어리면 관절이 죽는다 ← 출처: src/drones.py build_propeller() 302~304행 docstring",
    "   (\"pose_articulated 가 이 메쉬를 z회전(스핀)시켜 각 로터에 배치한다\")·pose_articulated() 353~357행.",
    "3. **묻힌 표면을 SBR 은 자동으로 거른다.** 광선이 처음 맞는 면만 반사에 넣으므로 몸체 속에",
    "   묻힌 배터리 표면은 가려진다(occlusion). ⚠ **PO 는 그렇지 않다** — §8.3 에서 따로 다룬다.",
))

# ---------------------------------------------------------------- 11b. 겹침을 어떤 자로
cells.append(md(
    "### 8.2 부피 % 는 이 질문에 맞는 자가 아니다",
    "",
    "위 표의 «총부피 대비 %» 는 읽기 쉽지만, 답하려는 질문과 어긋난다. **산란은 부피가 아니라**",
    "**표면에서 난다.** 자를 세 번 갈아 보면 순위가 바뀐다:",
    "",
    "| 자 | 무엇을 세나 | 왜 부족한가 |",
    "|---|---|---|",
    "| ① 부피 % | 교차 부피 ÷ 전체 부피 | 산란은 표면에서 난다 |",
    "| ② 표면적 % | 다른 부품 속에 묻힌 면적 비율 | 금속 1 cm² 와 플라스틱 1 cm² 를 같게 센다 |",
    "| ③ **재질 가중 + 담는 쪽의 불투명 여부** | A·\\|Γ\\|² 로 세고, **유전체 셸 안**은 빼고 "
    "**불투명 부품 안**만 센다 | 지금 쓰는 자 |",
    "",
    "③ 이 맞는 이유는 물리에 있다. 금속 상자가 **플라스틱 셸 안**에 있는 것은 결함이 아니라 설계다 —",
    "전파는 셸을 투과해 그 금속을 본다(우리 SBR 이 정확히 그렇게 계산한다). 진짜 이중계상은",
    "**불투명한 부품 안**에 묻힌 면이다.",
    "",
    "### 8.3 ⭐ 그런데 우리 PO 경로에는 가림이 없다",
    "",
    "`src/rcs_po.py` 는 자기 docstring 에서 **자기차폐(self-shadowing)와 다중반사를 무시한다**고",
    "선언한다. 즉 §8.1 의 «묻힌 면은 전파가 못 본다» 는 **SBR 경로의 성질**이고, PO 경로에서는",
    "묻힌 면이 그대로 면적에 더해진다.",
    "",
    "그 크기를 ③ 의 자로 재면 이렇다:",
    "",
    MF.po_overcount_table(ORDER),
    "",
    "← 출처: `outputs/mesh_inspect_materials_check_0816.json` `fleet.*`.",
    "",
    "**캐노피는 특히 죽은 무게다.** 상단 캐노피는 여러 기체에서 셸 안에 69~100 % 묻혀 있어,",
    "SBR 기여가 **정확히 0** 이다(first-hit 이 될 수 없고, 투과 패스에서는 셸이 제외된다).",
    "재질이 플라스틱이라 PO 쪽 과대도 작다 — 빼도 방위평균 σ 가 0.03~0.09 dB 밖에 안 움직인다",
    "← 출처: 같은 파일 `rf_estimates.buried_canopy`.",
    "",
    "⇒ **결론 문장은 이렇게 써야 한다**: 겹침은 설계이고 SBR 은 그것을 옳게 처리한다.",
    "PO 로 절대 σ 를 낼 때는 위 표의 dB 만큼 밝은 쪽으로 치우친다.",
))

# ---------------------------------------------------------------- 11c. 지금 남은 결함
cells.append(md(
    "## 8.4 기하 축에서 지금 남은 결함",
    "",
    "이 편이 다루는 축(기하)에서 현재 메쉬가 안고 있는 어긋남을 있는 그대로 적는다.",
    "크기를 함께 적어, 어느 결론이 흔들리고 어느 결론이 안 흔들리는지 독자가 판단할 수 있게 한다.",
    "",
    MF.defect_table(),
    "",
    "← 출처: `outputs/mesh_inspect_body_arms_0816.json` `findings` · "
    "`outputs/mesh_inspect_gimbal_sensors_0816.json` `_summary` · "
    "`outputs/mesh_inspect_materials_check_0816.json` `findings`.",
    "",
    "**dB 를 읽는 법** — 위 표의 dB 는 대부분 **평판극한 상한**이다. «같은 크기 평판이라면 최대",
    "이만큼» 이라는 뜻이지 커널이 계산한 σ 가 아니다. 크기 감각을 주는 자로만 쓸 것.",
    "",
    "### 지금 «모른다» 고 선언한 것",
    "",
    *MF.unresolved_list(),
    "",
    "⭐ **빈칸이 가짜 값보다 낫다.** 위 항목들은 값을 채워 넣는 대신 비워 두었다.",
))

cells.append(cc(
    "# 부위 겹침 — 드론별 상위 3쌍",
    'Fo = V["F_overlap"]',
    "for k in ORDER:",
    "    r = Fo[k]",
    "    print(f\"[{NAME[k]}]  합계 {r['total_overlap_cm3']:7.1f} cm³ = 총부피의 {r['overlap_pct_of_volume']:5.2f}%\")",
    "    for p in r['pairs'][:3]:",
    "        print(f\"    {p['a']:>8s} ∩ {p['b']:<8s} {p['overlap_cm3']:8.1f} cm³\")",
))

# ---------------------------------------------------------------- 12. 한계
cells.append(md(
    "## 9. 이 검사가 보증하지 **않는** 것 (현재 한계)",
    "",
    "적대적으로 스스로 반박해 둔다 — 기하 검사 전 항목 통과는 다음을 **보증하지 않는다**:",
    "",
    "1. **실물을 닮았다는 보증이 아니다.** 완벽하게 watertight 한 정육면체도 드론은 아니다.",
    "   실물 충실도는 별도 검사다: 공식 제원 대조(§C_dims, 최악 오차 "
    f"{max(V['C_dims'][k]['worst_err_pct'] for k in ORDER):.1f}%)와 실기체 3D 스캔 대조(§G_scan)가",
    "   다른 리포트에서 다뤄진다.",
    "2. **물리 계산이 수렴한다는 보증이 아니다.** 건강한 메쉬 위에서도 적분 점간격·광선 간격이 성기면",
    "   RCS 는 흔들린다 — 그래서 §H(PO 수렴)·§I(SBR 세분화 불변)를 따로 돌린다.",
    "3. **«겹침이 무해하다» 는 SBR 경로에서만 참이다.** 우리 **PO 커널이 바로 그 «가림 없는 PO»**",
    "   다 — 자기차폐·다중반사를 무시한다고 스스로 선언한다. 이식 문제가 아니라 **우리 경로의",
    "   현재 성질**이고, 크기는 §8.3 의 표에 있다.",
    "4. **슬리버 삼각형은 우리 용도에 무해할 뿐**(면적 비중 0.0001~0.03 %), 유한요소 등 삼각형",
    "   품질에 민감한 도구에는 재메싱이 필요하다. 그리고 그 슬리버의 **법선 부호가 실제로",
    "   흔들리는지는 안 쟀다**(§5.1).",
    "5. **검사기가 아직 못 보는 것들이 있다** — 아래 목록.",
    "",
    "**이 검사가 아직 못 보는 것:**",
    "",
    *[f"- {b}" for b in MF.BLIND_SPOTS],
    "",
    "요약 판정:",
    "",
    "| 검사 | 결과 | 판정 |",
    "|---|---|---|",
    f"| 수밀 (부품 {tot_parts}개) | {n_wt}/{tot_parts} | **예산 안** (선언된 예외 1건 — mini2 셸) |",
    f"| 안쪽 법선 | {tot_inward}건. 부호부피를 두 번 잰다 — trimesh 로 한 번, "
    "**trimesh 를 전혀 안 거치고 출하 인덱스에서** 손으로 한 번 | 통과 |",
    f"| winding 불일치 / 퇴화면(절대) / 중복점 / 미사용점 | {tot_badwind} / {tot_degen} / {tot_dup} / {tot_unused} | 통과 |",
    "| 퇴화면(상대 — 최소 내각 <0.5°) | 기종당 수백 장 | **예산 안** (기종별 선언) |",
    f"| 엣지 p95 vs λ({LAM:.1f} mm) | {min(A[k]['edge_vs_lam52']['p95_over_lam'] for k in ORDER):.2f}~"
    f"{max(A[k]['edge_vs_lam52']['p95_over_lam'] for k in ORDER):.2f}λ | 통과 (⏳ 프롭 축은 별도) |",
    f"| 좌우대칭(기체만 p95) | ≤ {max(fr95.values()):.1f} mm (샘플링 한계 안) | 통과 |",
    "| 부위 겹침 | 설계된 겹침. SBR 은 옳게 처리, PO 는 §8.3 만큼 밝게 | 공개됨 |",
    "| 부착·치수·재질 배정 | §8.4 의 결함 지도 | **일부 미해결 — 선언됨** |",
    "",
    f"← 출처: mesh_verify.json §A_geometry·§B_symmetry·§F_overlap 집계(전체 판정 all_ok={all_ok}) · "
    "2026-08-16 원장 4종.",
))

# ---------------------------------------------------------------- 13. 재현
cells.append(md(
    "## 10. 재현 방법 · 다음 리포트",
    "",
    "```bash",
    "PY=/workspace/.venvs/py312/bin/python",
    "cd /workspace/sionna",
    "",
    "# 1) 원장 재생성 → outputs/mesh_verify.json (GPU 없으면 --skip-sbr)",
    "PYTHONPATH=src:benchmark $PY report_mesh/src/verify_mesh_suite.py --skip-sbr",
    "",
    "# 2) 그림 재생성 (triangle_quality / symmetry_chamfer / overlap_matrix / wireframe_* 등)",
    "PYTHONPATH=src:benchmark $PY report_mesh/src/viz_mesh_reports.py",
    "",
    "# 3) 이 노트북 재생성",
    "PYTHONPATH=src:benchmark $PY report_mesh/src/make_mesh07.py",
    "",
    "# (참고) 출하 게이트와 같은 코드로 빠른 전수 검사만",
    "PYTHONPATH=src:benchmark $PY src/mesh_check.py",
    "```",
    "",
    "⭐ **순서를 지켜야 한다.** 생성기는 원장이 레지스트리와 다르면 **일부러 멈춘다** —",
    "리포트가 틀린 기체 수를 조용히 쓰는 것보다 낫다는 규약이다",
    "← 출처: `report_mesh/src/mesh_ledger.py` `ledger_order()`.",
    "",
    "삼각형이 건강함을 확인했으니, 다음 질문은 \"그래서 **실물과 맞는가**\"다.",
    "",
    "**다음 리포트 → mesh08 — 검증 ② (공식 제원 치수 대조·부피/암시밀도·실기체 스캔·PO/SBR 수치 수렴,",
    "mesh_verify.json §C/§D/§G/§H/§I)**",
))

nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "py312",
      "language": "python", "name": "py312"}, "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 5}
out = os.path.join(RM, "mesh07_verify_geometry.ipynb")
for _i, _c in enumerate(nb["cells"]):
    _c["id"] = f"m07-{_i:02d}"

json.dump(nb, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("wrote", out, len(cells), "cells")
