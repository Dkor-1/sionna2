# -*- coding: utf-8 -*-
"""make_mesh01.py — mesh01 ipynb 생성기. ⚠ 이 파일이 소스다.
================================================================
mesh01 — "우리 드론 3D 모델, 왜 이렇게 만들었나 (전체 지도)"

시리즈의 문을 여는 편. 단 하나의 주제: **왜 인터넷 3D 모델을 받지 않고
코드로 드론을 만들었는가, 그리고 그 전체 파이프라인의 지도**.

하우스 규약:
  · 본문 수치는 전부 report_mesh/outputs/mesh_verify.json 에서 f-string 주입 (손숫자 금지)
  · 스펙 숫자는 src/drones.py 의 DroneSpec 에서 import
  · 모든 사실 옆에 "← 출처:" 표기 (사용자 특별 지시)
  · 배정 그림: pipeline_map.png, wireframe_mavic4pro.png (이 두 장만 사용)
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RM = os.path.abspath(os.path.join(HERE, ".."))            # report_mesh/
ROOT = os.path.abspath(os.path.join(RM, ".."))            # sionna2/
sys.path.insert(0, os.path.join(ROOT, "src"))

V = json.load(open(os.path.join(RM, "outputs", "mesh_verify.json"), encoding="utf-8"))

from drones import DRONES  # noqa: E402  (스펙 원본: src/drones.py DroneSpec)

# --------------------------------------------------------------------------- #
#  수치 준비 — 본문의 모든 숫자는 여기서 계산해 주입한다
# --------------------------------------------------------------------------- #
META = V["meta"]
A = V["A_geometry"]
ORDER = META["drones"]                     # mini5pro, mavic4pro, matrice4e, s1000plus, phantom4

def _parts(s):                             # "12/12" → (12, 12)
    a, b = s.split("/")
    return int(a), int(b)

tot_verts = sum(A[k]["n_verts"] for k in ORDER)
tot_faces = sum(A[k]["n_faces"] for k in ORDER)
tot_parts = 0
tot_wt = 0
tot_inward = 0
tot_degen = 0
tot_dup = 0
for k in ORDER:
    tot_dup += A[k]["dup_vertices"]
    for g in A[k]["groups"].values():
        w_ok, w_all = _parts(g["watertight"])
        tot_wt += w_ok
        tot_parts += w_all
        tot_inward += g["inward_normals"]
        tot_degen += g["degenerate"]

MV = A["mavic4pro"]                        # 대표 기종(실측 대상)
mv_spec = DRONES["mavic4pro"]
mv_groups = MV["groups"]
mv_parts = sum(_parts(g["watertight"])[1] for g in mv_groups.values())
lam_hi = META["lam_hi_mm"]                 # 최고 대역(WiFi 5.21 GHz) 파장 [mm]
mv_p95 = MV["edge_mm"]["p95"]
mv_ratio = MV["edge_vs_lam52"]["p95_over_lam"]

# 재질 반사계수(|Γ| 진폭) — E_materials 는 5종 공통 gamma_map
GM = V["E_materials"]["mavic4pro"]["gamma_map"]
g_body, g_prop, g_batt, g_cam = GM["body"], GM["prop"], GM["battery"], GM["camera"]
db_batt_vs_body = 20.0 * math.log10(g_batt / g_body)     # 전력비 [dB]
db_batt_vs_prop = 20.0 * math.log10(g_batt / g_prop)

# 치수 검증(C) 최악 오차 — 5종 중 최댓값
worst_dim = max(V["C_dims"][k]["worst_err_pct"] for k in ORDER)

# 실기체 스캔 대조(G)
G = V["G_scan"]
g_p50 = G["scan_to_cad_mm"]["p50"]
g_p90 = G["scan_to_cad_mm"]["p90"]

# 드론 5종 표(스펙은 DroneSpec, 측정은 JSON)
_diag_est = {"mini5pro", "mavic4pro"}       # DJI 대각 비공개 → 추정 (src/drones.py note)
rows = []
for k in ORDER:
    sp = DRONES[k]
    a = A[k]
    parts = sum(_parts(g["watertight"])[1] for g in a["groups"].values())
    wt = sum(_parts(g["watertight"])[0] for g in a["groups"].values())
    star = "*" if k in _diag_est else ""
    rows.append(
        f"| {sp.name} | {sp.diagonal_mm:.0f}{star} | {sp.prop_dia_mm:.0f}×{sp.num_rotors} "
        f"| {a['n_verts']:,} | {a['n_faces']:,} | {a['n_groups']} | {wt}/{parts} |")
drone_table = "\n".join(rows)

# Mavic 4 Pro 부위(그룹)별 면 수 표 — §3 에서 사용
mat_of = {"body": "plastic_abs", "canopy": "plastic_abs", "camera": "glass+metal",
          "motor": "metal", "prop": "plastic_thin", "battery": "metal(Li-ion)",
          "pcb": "pcb(FR-4)"}
mv_rows = []
for gname in sorted(mv_groups, key=lambda x: -mv_groups[x]["n_faces"]):
    g = mv_groups[gname]
    mv_rows.append(f"| `{gname}` | {g['n_faces']:,} | {g['n_parts']} | {g['watertight']} "
                   f"| {mat_of.get(gname, '-')} | {GM.get(gname, float('nan')):.2f} |")
mv_group_table = "\n".join(mv_rows)


# --------------------------------------------------------------------------- #
#  노트북 셀
# --------------------------------------------------------------------------- #
def md(*lines):
    src = "\n".join(lines).splitlines(keepends=True)
    return {"cell_type": "markdown", "metadata": {}, "source": src or [""]}


cells = [

# ── 1. 제목 + 경고 + 요약 ──────────────────────────────────────────────────
md(
"# mesh01 — 우리 드론 3D 모델, 왜 이렇게 만들었나 (전체 지도)",
"",
"> ⚠ **이 노트북은 생성물이다.** 수정은 `src/make_mesh01.py` 에서 하고 재실행할 것",
"> (`.ipynb` 를 직접 고치면 다음 빌드에서 사라진다).",
"",
f"**한 줄 요약** — 인터넷의 DJI 3D 모델은 시각용 껍데기라 레이더 시뮬레이션에 못 쓴다.",
f"그래서 우리는 DJI **공식 제원표의 숫자**로부터 코드가 드론 {len(ORDER)}종을 직접 깎아 만들고",
f"(총 {tot_faces:,}개 삼각형), 9가지 독립 검사로 품질을 증명한다. 이 편은 그 **전체 지도**다.",
"",
"이 시리즈(mesh01~08)는 **파이썬 기초만 아는 독자**를 위한 3D 모델 제작 가이드다.",
"본문의 모든 숫자는 손으로 적지 않고 검증 스위트가 만든",
"`outputs/mesh_verify.json` 에서 자동 주입했으며, **모든 사실 옆에 `← 출처:` 를 단다** —",
"어느 파일·어느 웹페이지·어느 측정에서 온 정보인지 독자가 직접 추적할 수 있게."),

# ── 2. 용어풀이 ────────────────────────────────────────────────────────────
md(
"## 용어풀이 (이 리포트에 나오는 순서대로)",
"",
"| 용어 | 한 줄 풀이 |",
"|---|---|",
"| **메쉬(mesh)** | 작은 삼각형 수천 장을 이어붙여 만든 3D 표면. 컴퓨터가 형상을 저장하는 가장 보편적 방식 |",
"| **꼭짓점(vertex)** | 3D 공간의 점 (x, y, z). 삼각형의 모서리 끝점 |",
"| **면(face)** | 꼭짓점 3개를 이은 삼각형 1장. 메쉬의 최소 단위 |",
"| **법선(normal)** | 삼각형이 바라보는 방향(수직 화살표). 물체의 '겉'과 '속'을 구분한다 |",
"| **watertight(방수)** | 구멍이 하나도 없는 닫힌 표면 — 물을 부어도 새지 않는 그릇 |",
"| **그룹(group)** | 면마다 붙인 부위 이름표(body/prop/motor …). 부위별 재질 배정의 열쇠 |",
"| **OBJ** | 꼭짓점·삼각형 목록을 적는 텍스트 3D 파일 형식. Sionna/Mitsuba 가 바로 읽는다 |",
"| **파라메트릭 CAD** | 치수(파라미터)를 넣으면 코드가 형상을 만들어 주는 설계 방식 |",
"| **불리언(boolean union)** | 두 입체를 '합집합' 으로 녹여 붙여 내부의 숨은 면을 없애는 연산 |",
"| **trimesh / manifold3d** | 파이썬 3D 메쉬 라이브러리 / 불리언 연산 엔진 (둘을 함께 쓴다) |",
"| **Sionna RT** | NVIDIA 의 전파(RF) 광선추적 시뮬레이터. 우리 실험의 무대 |",
"| **RCS** | Radar Cross Section. 레이더에게 물체가 얼마나 '밝게' 보이는지의 면적값 [m²] |",
"| **PO / SBR** | 물리광학 / 광선발사·반사 — 메쉬 표면에서 RCS 를 계산하는 두 방법 (mesh08·report07) |",
"| **\\|Γ\\|(반사계수)** | 전파가 재질 표면에서 반사되는 진폭 비율. 금속≈1.0, 플라스틱≈0.3 |",
"| **파장 λ** | 전파의 한 주기 길이. 메쉬 삼각형은 λ 보다 충분히 작아야 형상을 '전파의 눈'으로 담는다 |"),

# ── 3. §0 이 편이 답하는 질문 ─────────────────────────────────────────────
md(
"## 0. 이 편이 답하는 질문",
"",
"우리 프로젝트는 30×20×11 m 반무향 챔버 안에서 WiFi/LTE/5G 신호로 드론을 탐지하는",
"패시브 레이더 시뮬레이션이다 ← 출처: `README.md` 1~10행. 그 시뮬레이션의 **표적**이 되는",
f"DJI 드론 {len(ORDER)}종({', '.join(DRONES[k].name.replace('DJI ', '') for k in ORDER)})의",
"3D 모델을 어떻게 만들었는지가 이 시리즈의 주제다.",
"",
"이 편(mesh01)은 네 가지 질문에 답한다:",
"",
"1. **삼각형 메쉬가 뭔가?** — 종이접기 비유로 (§1)",
"2. **왜 인터넷 3D 모델을 안 받고 코드로 만들었나?** (§2)",
"3. **핵심 원칙 'OBJ 1개 = 부위 1개 = 재질 1개' 는 무슨 뜻인가?** (§3)",
"4. **자료 → 제작 → 검증, 전체 파이프라인은 어떻게 생겼나?** (§4, 지도 그림)",
"",
"세부(몸체 깎는 법, 프로펠러 익형, 치수 검증, 재질, 삼각형 품질, 실물 대조, 수치 수렴)는",
"mesh02~08 각 편이 하나씩 맡는다 — 목차는 §5."),

# ── 4. §1 삼각형 메쉬란 ───────────────────────────────────────────────────
md(
"## 1. 삼각형 메쉬란 무엇인가 — 종이접기 다면체",
"",
"**비유**: 축구공 모양 종이 다면체를 접어 본 적이 있는가? 평평한 종이 조각(오각형·육각형)을",
"수십 장 이어붙이면 거의 둥근 공이 된다. 조각을 잘게 쓸수록 더 매끈해진다.",
"3D 메쉬가 정확히 그것이다 — 다만 조각이 전부 **삼각형**이고, 종이 대신 숫자로 접는다.",
"",
"왜 하필 삼각형인가? **점 3개는 반드시 한 평면 위에 있기 때문**이다. 사각형부터는 뒤틀릴 수",
"있어(네 점이 한 평면에 안 놓임) 계산이 모호해진다. 그래서 그래픽스·전파 시뮬레이션 모두",
"삼각형을 최소 단위로 쓴다.",
"",
"우리 코드의 메쉬 정의는 놀랄 만큼 단순하다:",
"",
"```",
"핵심 개념 — 메쉬(Mesh)는 딱 두 가지로 이루어집니다",
"  1) 꼭짓점(vertex) 목록 : 3D 점 (x, y, z) 들의 리스트",
"  2) 면(face) 목록       : \"몇 번 꼭짓점 3개를 이어 삼각형을 만들지\"",
"거기에 우리는 \"그룹(group)\" 하나를 더 붙입니다. 면마다 어떤 **재질 그룹**",
"(예: body / arm / motor / prop / absorber ...)에 속하는지 이름표를 답니다.",
"```",
"",
"← 출처: `src/geom.py` 15~21행 모듈 docstring (그대로 인용).",
"실제 클래스도 딱 세 줄이다 — `.v`(꼭짓점), `.f`(삼각형 인덱스), `.g`(면별 그룹 이름)",
"← 출처: `src/geom.py:41` `class Mesh` docstring.",
"",
f"예컨대 대표 기종 **{mv_spec.name}** 모델은 꼭짓점 {MV['n_verts']:,}개를",
f"삼각형 {MV['n_faces']:,}장으로 이어붙인 것이고, 면마다 {MV['n_groups']}가지 부위 이름표",
"(body/canopy/prop/motor/camera/battery/pcb)가 붙어 있다",
"← 출처: `outputs/mesh_verify.json` `A_geometry.mavic4pro` (측정: `report_mesh/src/verify_mesh_suite.py` §A)."),

# ── 5. §1.2 법선과 watertight ─────────────────────────────────────────────
md(
"### 1.2 법선과 watertight — '겉면 스티커'와 '물 안 새는 그릇'",
"",
"종이 다면체를 접을 때 겉과 속을 뒤집어 붙이면 이상해진다. 메쉬도 같다. 삼각형마다",
"**법선(normal)** — 어느 쪽이 '겉'인지 가리키는 수직 화살표 — 이 있고, 모든 법선이",
"바깥을 향해야 전파 시뮬레이터가 \"여기가 물체 표면\" 을 올바로 인식한다.",
"법선이 안쪽을 보면 그 면은 반사 계산에서 **거꾸로 세어져** RCS 가 틀어진다 —",
"그래서 검사 A 가 법선 방향·winding 을 전수 확인한다",
"← 출처: `report_mesh/src/verify_mesh_suite.py` §A 검사 항목(법선방향·winding).",
"",
"**watertight(방수)** 는 표면에 구멍이 하나도 없다는 뜻이다 — 그릇에 물을 부어도 안 샌다.",
"구멍이 있으면 (a) 부피를 정의할 수 없고 (b) 광선이 물체 '속'으로 새어들어 유령 반사를 만든다.",
"",
f"우리 {len(ORDER)}종의 성적표 (검사: trimesh 의 `is_watertight`·winding·법선 검사",
"← 출처: `report_mesh/src/verify_mesh_suite.py` §A):",
"",
f"- 부위 조각(파트) **{tot_parts}개 전부 watertight** ({tot_wt}/{tot_parts} 통과)",
f"- 안쪽을 보는 법선 **{tot_inward}개**, 퇴화 삼각형(넓이 0) **{tot_degen}개**, 중복 꼭짓점 **{tot_dup}개**",
"",
"← 출처: `outputs/mesh_verify.json` `A_geometry.*.groups` (watertight/inward_normals/degenerate/dup_vertices 합산).",
"",
"뒤 리포트들이 쓰는 물리 계산(PO 적분·SBR 광선추적, mesh08·report07)은 이",
"기하학적 건강함을 **전제**로 한다. 그래서 시리즈 첫 편에서 이 성적표부터 보여 준다."),

# ── 6. §1.3 5종 규모 표 ───────────────────────────────────────────────────
md(
"### 1.3 우리 드론 5종 — 한 표로",
"",
"| 드론 | 대각[mm] | 프롭Ø[mm]×수 | 꼭짓점 | 삼각형 | 부위 수 | watertight |",
"|---|---|---|---|---|---|---|",
drone_table,
f"| **합계** | | | **{tot_verts:,}** | **{tot_faces:,}** | | **{tot_wt}/{tot_parts}** |",
"",
"\\* 표시: DJI 가 대각거리(모터-모터 휠베이스)를 공개하지 않아 외형에서 **추정**한 값",
"← 출처: `src/drones.py:98·121` DroneSpec `note` 필드(mini5pro·mavic4pro)·`docs/SPECS.md` (각 기종 dji.com 스펙페이지 URL 포함).",
"대각·프롭 지름·로터 수는 `src/drones.py:37` `DroneSpec` dataclass 에서 import 했고(손숫자 아님),",
"꼭짓점·삼각형·watertight 는 `outputs/mesh_verify.json` `A_geometry` 측정값이다.",
"",
f"공식 외형치수와의 오차는 5종 최악이 **{worst_dim:.1f}%** (자세한 검증은 mesh04·mesh08)",
"← 출처: `mesh_verify.json` `C_dims.*.worst_err_pct`."),

# ── 7. 그림: wireframe ────────────────────────────────────────────────────
md(
"### 1.4 눈으로 보기 — 대표 기종 Mavic 4 Pro",
"",
"![wireframe mavic4pro](outputs/figures/wireframe_mavic4pro.png)",
"",
f"**그림 1** — {mv_spec.name} 메쉬 3면. 실측 캠페인 대상 기종이라 대표로 골랐다",
"← 출처: 프로젝트 방향(`README.md` 137~138행: 실측 = Mavic 4 Pro·Matrice 4E).",
"",
"- **왼쪽(shaded)**: 색이 곧 부위(=재질)다. 회색 몸체(body), 어두운 프로펠러(prop),",
"  금속색 모터(motor), 렌즈 3개가 박힌 구형 짐벌(camera) — Mavic 4 의 실제 특징인",
"  '인피니티 볼 짐벌'을 반영했다 ← 출처: `src/drone_cad.py` 머리말 실루엣 목록(16~17행).",
f"- **가운데(wireframe)**: 삼각형 {MV['n_faces']:,}장의 뼈대가 그대로 보인다. 곡면(동체·짐벌 볼)일수록",
"  삼각형이 촘촘하다.",
f"- **오른쪽(top view)**: 위에서 본 대각 배치. 프로펠러 지름 {mv_spec.prop_dia_mm:.0f} mm ×",
f"  로터 {mv_spec.num_rotors}개 ← 출처: DJI 공식 스펙(`docs/SPECS.md`, drdrone.ca/pages/dji-mavic-4-pro-technical-specifications).",
"",
f"삼각형 한 변 길이는 상위 95% 가 {mv_p95:.1f} mm — 우리가 쓰는 최고 대역(WiFi 5.21 GHz)의",
f"파장 λ={lam_hi:.1f} mm 의 **{mv_ratio:.2f}λ ≈ λ/{1/mv_ratio:.1f}** 수준이라, 전파의 눈으로 봐도",
"형상이 충분히 매끄럽다(엣지 길이 통계는 mesh07 에서 자세히)",
"← 출처: `mesh_verify.json` `A_geometry.mavic4pro.edge_mm/edge_vs_lam52`, 그림: `report_mesh/src/viz_mesh_reports.py` `fig_wireframes()`(119행)."),

# ── 8. §2 왜 인터넷 모델을 안 쓰나 ────────────────────────────────────────
md(
"## 2. 왜 인터넷 3D 모델을 그대로 안 쓰나",
"",
"가장 쉬운 길은 3D 모델 공유 사이트에서 \"DJI Mavic 4\" 를 검색해 받는 것이다.",
"우리는 그 길을 **버렸다**. 프로젝트 문서에 적어 둔 이유를 그대로 인용한다:",
"",
"> ⚠️ **DJI 는 공식 CAD 를 공개하지 않습니다.** 인터넷의 DJI 3D 모델들은",
"> · 시각용(껍데기만 — 내부 금속 산란체 없음)",
"> · 치수 검증 안 됨",
"> · 라이선스 제약",
"> 이라 RCS 에 쓸 수 없습니다.",
"",
"← 출처: `assets/meshes/reference/SOURCES.md` 6~10행 (그대로 인용).",
"",
"세 가지를 하나씩 풀면:",
"",
"1. **시각용 껍데기** — 게임·렌더용 모델은 겉모습만 그럴듯하면 된다. 하지만 전파(RF)의 눈에는",
f"   겉껍데기 플라스틱(반사 진폭 \\|Γ\\|={g_body:.2f})보다 속의 **배터리·모터 금속**",
f"   (\\|Γ\\|≈{g_batt:.2f})이 전력비로 **약 {db_batt_vs_body:.0f} dB**(≈{10**(db_batt_vs_body/10):.0f}배) 더 밝다.",
"   내부 금속이 없는 모델은 레이더 관점에서 '속 빈 유령'이다",
"   ← 출처: \\|Γ\\| 값은 `mesh_verify.json` `E_materials.*.gamma_map`(원본: `src/materials.py`, ITU-R P.2040), dB 는 20·log₁₀ 비율 계산.",
"2. **치수 미검증** — 취미 모델러가 사진을 보고 눈대중으로 만든 것이 많다. RCS 는 투영 면적과",
"   세부 형상에 민감해서(∝A²/λ² 까지 가능, report06) 치수가 몇 % 틀리면 답이 몇 dB 틀어진다.",
"3. **라이선스 제약** — 연구 산출물에 재배포 불가/상업 불가 모델을 섞으면 재현 패키지를 공개할 수 없다.",
"",
"**대안은 없었나?** 상용 스캔 서비스(수백만 원)나 직접 3D 스캔도 검토 대상이지만, 5종 전부를",
"검증 가능한 품질로 확보할 방법이 아니었다. 대신 **공짜이면서 가장 신뢰할 수 있는 원천** —",
"DJI 공식 제원표(외형 L×W×H·프로펠러 지름·무게) — 에서 출발하기로 했다",
"← 출처: `docs/SPECS.md` (기종별 dji.com/specs URL 목록·독립 교차검증 기록)."),

# ── 9. §2.2 코드 생성의 이점 ──────────────────────────────────────────────
md(
"### 2.2 그래서 코드로 만든다 — 파라메트릭 CAD 의 4가지 이점",
"",
"\"코드로 만든다\" = 치수를 넣으면 형상이 나오는 함수를 짠다는 뜻이다(파라메트릭 CAD).",
"각 드론은 `DroneSpec` 이라는 데이터클래스 하나로 요약된다 — 대각거리, 무게, 프로펠러",
"지름·날 수, 로터 수, 공식 외형(L×W×H) … ← 출처: `src/drones.py:37~81` `class DroneSpec`.",
"",
"| 이점 | 설명 |",
"|---|---|",
"| **재현성** | 누구든 `build_drone(spec)` 한 줄로 비트 단위 동일한 메쉬를 재생성 — 다운로드 링크가 죽어도 모델은 안 죽는다 |",
"| **파라메트릭** | 제원이 정정되면 숫자 하나만 고치면 형상 전체가 따라온다 (실제로 Mini 5 Pro 외형 정정이 있었다, 아래) |",
"| **부위별 재질** | 만들 때부터 면마다 body/prop/motor … 그룹 이름표 → 부위별 전파재질 배정이 공짜 (§3) |",
"| **버전관리** | 메쉬가 곧 코드니까 git diff 로 형상 변경 이력이 남는다 — 바이너리 3D 파일로는 불가능 |",
"",
"← 출처: 설계 의도는 `src/drones.py:2~24`·`src/geom.py:7~13` 모듈 docstring.",
"",
"**정직성 원칙** — 모르는 값은 모른다고 적는다. 예컨대 Mini 5 Pro 스펙의 `note` 필드:",
"",
"> \"Diagonal (250 mm) not published by DJI — was estimated from the unfolded shape.",
"> ⚠ 2026-07-14: after fitting the frame to the OFFICIAL envelope, the implied",
"> motor-to-motor diagonal is 274.6 mm, i.e. the old 250 mm estimate was ~9% low.\"",
"",
"← 출처: `src/drones.py:98~102` (그대로 인용). 추정값은 추정이라고 표시하고, 나중에 더 좋은",
"근거가 나오면 정정 이력까지 코드에 남긴다 — 이 습관 덕에 mesh04 의 치수 검증이 의미를 갖는다."),

# ── 10. §2.3 인터넷 모델·스캔의 올바른 자리 ───────────────────────────────
md(
"### 2.3 그럼 인터넷 모델은 어디에 쓰나 — '제작'이 아니라 '검증'에",
"",
"인터넷 3D 자료를 전부 버린 건 아니다. **라이선스가 확실하고 실물에서 온** 자료만 골라,",
"우리 모델을 만드는 데가 아니라 **우리 모델을 채점하는 데** 쓴다:",
"",
"| 자료 | 정체 | 라이선스 | 용도 |",
"|---|---|---|---|",
f"| Phantom 4 실기체 3D 스캔 | {G['source']['thing']} (저작자 {G['source']['author']}) | {G['source']['license']} | 표면 오차 채점 (mesh08) |",
"| Typhoon H480 / 3DR Solo CAD | ethz-asl/rotors_simulator 실물 모델 | Apache-2.0 | 실물 CAD 갤러리 대조 (mesh03·본편 report03) |",
"| Holybro X500 부품(프롭·모터) | PX4/PX4-gazebo-models | BSD-3-Clause | 부품 형상 대조 (mesh03·본편 report03) |",
"",
"← 출처: `assets/meshes/reference/SOURCES.md` 표(저장소 URL 포함)·`assets/meshes/cad/SOURCE.txt`",
"(Thingiverse thing:1456295, 0.4 mm 해상도 실기체 스캔, CC-BY, 미러 archive.org).",
"",
f"미리보기 하나: 우리 Phantom 4 메쉬는 실기체 스캔과 표면 거리 중앙값 **{g_p50:.1f} mm**,",
f"90분위 {g_p90:.1f} mm 안에서 겹친다 ← 출처: `mesh_verify.json` `G_scan.scan_to_cad_mm`.",
"자세한 방법(chamfer 거리 — 두 표면 사이 최근접점 거리 분포)과 그림은 mesh08 에서.",
"",
"**왜 이 역할 분담인가?** 스캔·타사 CAD 로 모델을 '만들면' 그 자료의 오류·라이선스가 우리",
"모델에 스며든다. '채점'에만 쓰면 독립된 두 원천(공식 제원 vs 실물 스캔)이 서로를 견제하는",
"교차검증이 된다 ← 출처: `assets/meshes/reference/SOURCES.md` 23~24행 (\"이 파일들은 비교·검증",
"전용입니다\")."),

# ── 11. §3 OBJ 1개 = 부위 1개 = 재질 1개 ─────────────────────────────────
md(
"## 3. 핵심 원칙 — \"OBJ 1개 = 부위 1개 = Sionna 재질 1개\"",
"",
"드론 한 대를 한 덩어리 파일로 저장하지 않고, **부위마다 별도 OBJ 파일**로 저장한다.",
"이유는 Sionna 의 규칙 때문이다:",
"",
"> Sionna 는 'OBJ 1개 = SceneObject 1개 = 재질 1개' 이므로, 부위별 재질을",
"> 주려면 이렇게 부위별로 나눠 저장한다.",
"",
"← 출처: `src/geom.py:137~140` `write_obj_per_group()` docstring (그대로 인용);",
"같은 원칙이 `README.md:79` 에 \"메쉬 원칙: OBJ 1개 = 부위 1개 = Sionna 재질 1개\" 로 선언돼 있다.",
"",
f"{mv_spec.name} 의 부위 {MV['n_groups']}개 ← 출처: 아래 표 전부 `mesh_verify.json`",
"`A_geometry.mavic4pro.groups`(면 수·파트·watertight)·`E_materials.mavic4pro.gamma_map`(\\|Γ\\|):",
"",
"| 부위(그룹) | 삼각형 | 파트 | watertight | 재질 계열 | \\|Γ\\|@3.5GHz |",
"|---|---|---|---|---|---|",
mv_group_table,
"",
f"플라스틱 프로펠러(\\|Γ\\|={g_prop:.2f})와 금속 배터리(\\|Γ\\|≈{g_batt:.2f})는 반사 전력이",
f"**{db_batt_vs_prop:.0f} dB** 차이 난다. 부위를 한 재질로 뭉뚱그리면 이 대비가 사라져",
"RCS 도, 회전 프로펠러의 마이크로도플러도 다 틀어진다 — 부위별 OBJ 는 겉치레가 아니라",
"물리의 요구다 ← 출처: 재질 배정 원본 `src/materials.py`(ITU-R P.2040 + 커스텀), 상세는 mesh06.",
"",
"덤으로 **분절(articulated) 자세**도 공짜로 얻는다: 몸체와 프로펠러가 별개 조각이라",
"몸체 기울기와 로터별 회전 위상을 따로 줄 수 있다 ← 출처: `src/drones.py` `pose_articulated()` docstring."),

# ── 12. §4 파이프라인 지도 ────────────────────────────────────────────────
md(
"## 4. 전체 파이프라인 지도",
"",
"![pipeline map](outputs/figures/pipeline_map.png)",
"",
"**그림 2** — 모든 정보가 어디서 와서 어떻게 검증되는지 한 장 지도",
"← 출처: 그림 생성 `report_mesh/src/viz_mesh_reports.py` `fig_pipeline_map()`(486행).",
"",
"**① 자료층 (주황)** — 세 가지 원천, 역할이 서로 다르다:",
"",
"- **DJI 공식 제원표** (기종별 dji.com/specs) → 웹 조사 + 독립 교차검증을 거쳐",
"  `docs/drone_research.json` → `docs/SPECS.md` 로 정리 ← 출처: `docs/SPECS.md` 머리말",
"  (\"1차 조사 후 독립 검증\", 조사일·URL 목록 포함). **모델 제작의 유일한 치수 원천.**",
"- **실기체 3D 스캔** (Phantom 4, CC-BY) — 검증 전용 ← 출처: `assets/meshes/cad/SOURCE.txt`",
"- **실물 제품 CAD** (Typhoon H480 등, Apache-2.0/BSD-3) — 검증 전용 ← 출처: `assets/meshes/reference/SOURCES.md`",
"",
"화살표 방향이 핵심이다: 스캔·실물 CAD 에서 제작층으로 가는 화살표는 **없다**.",
"둘은 오른쪽 아래 '물리 검증' 상자로만 흘러든다 (§2.3 의 역할 분담)."),

# ── 13. §4.2 제작층·검증층 ────────────────────────────────────────────────
md(
"### 4.2 제작층과 검증층",
"",
"**② 제작층 (파랑)** — 숫자가 형상이 되는 곳:",
"",
f"- `src/drones.py` 의 `DroneSpec` {len(ORDER)}개(공식 숫자) → `src/drone_cad.py` + `src/cadkit.py` 가",
f"  **{META['mesh_engine']}** 엔진으로 깎는다 ← 출처: `mesh_verify.json` `meta.mesh_engine`·",
"  `src/drones.py:243` `_build_frame_raw()` — 드론 제작은 **CAD 단일 경로**(trimesh+manifold3d)다.",
"- **왜 trimesh + manifold3d 인가?** 프리미티브를 그냥 겹쳐 놓으면 겹친 파트의 **내부에 숨은 면**이",
"  표면 데이터에 그대로 남고, PO/SBR 은 그런 면까지 반사면으로 세어 RCS 를 틀리게 만든다.",
"  manifold3d 의 **불리언 합집합**은 겹친 파트를 한 덩어리로 녹여 내부 면이 애초에 존재하지",
"  않게 한다 — 더 정확하고 더 빠르다 ← 출처: `src/drone_cad.py:23~27` \"왜 이게 RCS 에 중요한가\".",
"  (자작 `geom.Mesh` 의 역할은 **컨테이너와 무대**다: 완성 메쉬 담기(.v/.f/.g)·부위별 OBJ 저장,",
"  그리고 챔버·범용 프리미티브(box/cylinder/uv_sphere/pyramid_field) 제작",
"  ← 출처: `src/geom.py:41` `class Mesh`·`src/geom.py:137` `write_obj_per_group()`.)",
"- 완성 메쉬는 `write_obj_per_group()` 으로 **부위별 OBJ** 저장(§3) → `src/materials.py` 가",
"  부위→전파재질 배정 ← 출처: `src/geom.py:137`·`README.md:79~80`.",
"",
"**③ 검증층 (초록)** — 만들었으면 증명한다. 기하 검증(A~F)과 물리 검증(G~I)의 결과가",
"전부 **증거 JSON 한 파일**로 모인다:",
"",
"> evidence JSON → `report_mesh/outputs/mesh_verify.json` (all report numbers come from here)",
"",
"← 출처: 그림 2 보라 상자. 이 노트북의 모든 숫자도 그 파일에서 자동 주입됐다."),

# ── 14. §4.3 검증 9종 ─────────────────────────────────────────────────────
md(
"### 4.3 검증 9종 — 각각 한 질문",
"",
"검증 스위트의 자기소개(9개 검사, 각각 한 질문)를 표로 옮긴다",
"← 출처: `report_mesh/src/verify_mesh_suite.py:9~18` 모듈 docstring:",
"",
"| 검사 | 질문 |",
"|---|---|",
"| **A** geometry | 삼각형이 기하학적으로 건강한가? (watertight·법선방향·winding·퇴화면·중복점·엣지길이) |",
"| **B** symmetry | 좌우대칭 기체가 정말 대칭인가? (미러 chamfer 거리) |",
"| **C** dims | 공식 제원(외형·대각·프롭지름)과 몇 % 안에서 맞는가? |",
"| **D** volume | 닫힌 부피 → 암시 밀도가 물리적으로 말이 되는가? |",
"| **E** materials | 모든 부위(그룹)에 전파 재질이 배정돼 있는가? |",
"| **F** overlap | 부위끼리 얼마나 겹치는가? (의도된 겹침의 정량 공개) |",
"| **G** scan | 실기체 3D 스캔과 표면이 몇 mm 안에서 일치하는가? |",
"| **H** po_conv | PO 적분이 점 간격을 절반으로 줄여도 RCS 가 흔들리지 않는가? |",
"| **I** sbr_subdiv | SBR(GPU)이 메쉬를 세분화해도 RCS 가 흔들리지 않는가? |",
"",
"이 편에서는 A(§1.2 성적표)·C(§1.3 오차)·E(§3 재질표)·G(§2.3 스캔 미리보기)를 맛만 봤다.",
"나머지는 담당 편(mesh04·06·07·08)에서 그림과 함께 자세히 다룬다.",
"",
f"현재 상태 요약: {len(ORDER)}종 전부 A 검사 통과(`ok: true`), 치수 최악 오차 {worst_dim:.1f}%,",
"재질 미배정 부위 0개(`uncovered: []`) ← 출처: `mesh_verify.json` `A_geometry.*.ok`·`C_dims`·`E_materials.*.uncovered`."),

# ── 15. §5 시리즈 목차 ────────────────────────────────────────────────────
md(
"## 5. 시리즈 목차 — mesh02~08 예고",
"",
"| 편 | 주제 (한 줄) |",
"|---|---|",
"| **mesh02** | 도구 상자 — 어떤 파이썬 라이브러리를 왜 골랐나 (trimesh·manifold3d·cadkit) |",
"| **mesh03** | 자료 수집 — 모든 숫자·모델의 출처 (공식 스펙·실기체 스캔·외부 CAD, 라이선스) |",
"| **mesh04** | 몸체 CAD — 스펙 숫자가 드론 모양이 되기까지 (로프트·조립 순서·기종별 개성) |",
"| **mesh05** | 프로펠러 — NACA 익형 단면을 피치·테이퍼·스큐로 비틀어 진짜 블레이드를 만들기 |",
"| **mesh06** | 색이 곧 재질 — 부위별 전파 재질(ITU-R P.2040 + 커스텀)과 6색 규칙 |",
"| **mesh07** | 검증 ① 기하 품질 — watertight·법선·삼각형 품질·대칭·부위 겹침 |",
"| **mesh08** | 검증 ② 실물·물리 — 치수 대조·실기체 스캔 chamfer·PO/SBR 수치 수렴 |",
"",
"모든 편이 이 편과 같은 규약을 따른다: 생성물 노트북, 수치는 `mesh_verify.json` 주입,",
"사실마다 `← 출처:` 표기."),

# ── 16. 재현 + 다음 편 ────────────────────────────────────────────────────
md(
"## 재현 명령",
"",
"```bash",
"PY=~/.venvs/py312/bin/python",
"cd ~/workspace/sionna2",
"$PY report_mesh/src/verify_mesh_suite.py     # 증거 JSON 재생성 (검사 I 는 GPU 필요; --skip-sbr 로 생략 가능)",
"$PY report_mesh/src/viz_mesh_reports.py      # 그림 재생성 (outputs/figures/*.png)",
"$PY report_mesh/src/make_mesh01.py           # 이 노트북 재생성",
"```",
"",
"← 출처: 실행법은 `report_mesh/src/verify_mesh_suite.py:21~23` docstring.",
"",
"---",
"",
"**다음 편** → [mesh02 — 도구 상자](mesh02_tools.ipynb) : 어떤 파이썬 라이브러리를 왜 골랐고,",
"로프트·불리언이 실제로 무엇을 만드는지 빌드 단계 그림과 함께."),

]

nb = {"cells": cells,
      "metadata": {"kernelspec": {"display_name": "py312",
                                  "language": "python", "name": "py312"},
                   "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 5}
out = os.path.join(RM, "mesh01_overview.ipynb")
for _i, _c in enumerate(nb["cells"]):
    _c["id"] = f"m01-{_i:02d}"

json.dump(nb, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("wrote", out, len(cells), "cells")
