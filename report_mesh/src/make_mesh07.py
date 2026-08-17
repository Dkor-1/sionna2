# -*- coding: utf-8 -*-
"""make_mesh07.py — mesh07 ipynb 생성기. ⚠ 이 파일이 소스다.

mesh07 — "검증 ① 기하 품질 — 삼각형이 건강한가"
  ⭐**정본 판** 원장 `outputs/mesh_verify_canon_0817.json` 의 A(geometry)/B(symmetry)/
  F(overlap)·매몰면·예산 사용을 초보자 눈높이로 해설한다.
  모든 수치는 그 원장과 `src/mesh_check.py` 예산표에서 읽어 f-string 주입(손으로 적은 숫자 금지).
  배정 그림: triangle_quality.png, symmetry_chamfer.png, overlap_matrix.png,
             wireframe_s1000plus.png
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
RM = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(RM, ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
#  ⭐ 2026-08-17 — 이 편의 표는 **정본 판** 원장에서 나온다. 정본 판이란 메쉬 수리
#     `MESH_FIX_CANON=("battery","i5")` 와 날 법칙 `BLADE_LAW_CANON="per_airframe"` 가
#     켜진 기본 상태다(`src/geom.py`). 옛 원장(`mesh_verify.json`, 2026-08-16 13:15)은
#     다른 세대의 메쉬를 잰 수라 섞어 쓰면 세대가 갈린다.
V = json.load(open(os.path.join(RM, "outputs", "mesh_verify_canon_0817.json"), encoding="utf-8"))
CANON_LEDGER = "report_mesh/outputs/mesh_verify_canon_0817.json"

# ---------------------------------------------------------------- 수치 준비
#  ⭐ 2026-07-30 (Phase 3): 5종 하드코딩 → **원장 meta.drones**(= DRONES 레지스트리 전수)에서
#     유도. 표시명은 drones.drone_label. 예전엔 목록에 없는 기종이 표에서 조용히 빠졌다.
sys.path.insert(0, HERE)
from drones import drone_label            # noqa: E402
from mesh_ledger import ledger_order   # noqa: E402  (원장↔레지스트리 일치 강제)
import mesh_facts_0816 as MF          # noqa: E402  (2026-08-16 원장 공용 로더)
import mesh_check as MC                # noqa: E402  (예산표는 코드에서 직접 읽는다 — 손숫자 금지)
import geom as GEOM                    # noqa: E402  (정본 스위치의 단일 진리원)
ORDER = ledger_order({"meta": V["_meta"]}, CANON_LEDGER)   # 원장↔레지스트리 일치 강제
NAME = {k: drone_label(k) for k in ORDER}
A = V["A_geometry"]; B = V["B_symmetry"]; Fo = V["F_overlap"]
D = V["D_volume"]; META = V["_meta"]
LAM = META["lam_hi_mm"]                                   # 57.5 mm @5.21 GHz
BUD = V["budget_usage"]; BURIED = V["buried_faces"]; PROPTRI = V["prop_triangles"]
FIXES = ", ".join(f"`{x}`" for x in GEOM.MESH_FIX_CANON)
PEER_LEDGER = "report_mesh/outputs/mesh_canon_0817.json"
PEER = json.load(open(os.path.join(RM, "outputs", "mesh_canon_0817.json"), encoding="utf-8"))
BATT = json.load(open(os.path.join(ROOT, "outputs",
                                   "mesh_layer2_battery_overlap_0816.json"), encoding="utf-8"))
#  battery 수리로 사라지는 PO 이중계상의 크기 — 실제로 고쳐서 잰 값(예측이 아니다).
_bt = {k: v["sigma"] for k, v in BATT["σ"].items() if v.get("touched")}
_bt = {k: v for k, v in _bt.items() if abs(v["mono_el0"]["azimuth_mean_db"]) > 0.01}
_mono = ("mono_el0", "mono_el-30")
BT_MONO = (min(v[g]["azimuth_mean_db"] for v in _bt.values() for g in _mono),
           max(v[g]["azimuth_mean_db"] for v in _bt.values() for g in _mono))
#  ⚠ 방위 하나씩 보면 부호가 양쪽으로 갈린다 — 밝은 쪽/어두운 쪽을 **따로** 낸다.
#     (signed max 만 쓰면 mini2 el−30 의 −18.5 dB 를 통째로 놓친다.)
BT_WORST_HI = max(v[g]["worst_az_db"] for v in _bt.values() for g in _mono)
BT_WORST_LO = min(v[g]["worst_az_db"] for v in _bt.values() for g in _mono)
BT_BI_WORST_HI = max(v["bi_b120_el-30"]["worst_az_db"] for v in _bt.values())
BT_BI_WORST_LO = min(v["bi_b120_el-30"]["worst_az_db"] for v in _bt.values())


def _sgn(x: float) -> str:
    """부호 붙인 dB — 음수는 하우스 규약대로 유니코드 빼기표(−)를 쓴다."""
    return f"{x:+.1f}".replace("-", "\u2212")

BT_BI = max(v["bi_b120_el-30"]["azimuth_mean_db"] for v in _bt.values())
BT_N = len(_bt)
import math as _math                                        # noqa: E402
_mx = BATT["질량축_감사I9"]
BT_DM = [v["battery_mass_g"][1] - v["battery_mass_g"][0] for v in _mx.values()]
BT_DI = [(y / x - 1) * 100 for v in _mx.values()
         for x, y in zip(v["Idiag_kgm2"][0], v["Idiag_kgm2"][1])]
BT_DC = [_math.dist(v["com_mm"][0], v["com_mm"][1]) for v in _mx.values()]
BT_DV = max(v["double_counted_volume_pct"] for v in BATT["인구조사"].values()
            if v.get("double_counted_volume_pct"))
BT_OV = [v["checker_overlap_pct"][0] for v in BATT["인구조사"].values()
         if v.get("checker_overlap_pct", [0])[0] > 1.0]

TAG = META["file_tag"]                                    # 파일명 꼬리표

tot_verts = sum(A[k]["n_verts"] for k in ORDER)
tot_sliver = sum(BUD[k]["slivers"] for k in ORDER)
sl_lo = min(BUD[k]["slivers"] for k in ORDER)
sl_hi = max(BUD[k]["slivers"] for k in ORDER)

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


# ---------------------------------------------------------------- 정본 판 표들
#  ⭐ 예산은 «지금 이만큼이다» 라는 선언이다. 값은 전부 `src/mesh_check.py` 에서 **직접 읽어**
#     주입한다 — 리포트와 코드가 갈리는 자리를 없애려는 것이다.
def checker_table_canon() -> str:
    """공용 검사기 표 + 이 저장소의 여섯 번째 검사기(골든 봉인기)."""
    rows = MF.checker_table().splitlines()
    rows = [r.replace("이 시리즈의 숫자를 만든다. I 절(SBR)만 GPU",
                      "이 시리즈의 숫자를 만든다. I 절(SBR)만 GPU. ⭐정본 판 재측정은 "
                      "`report_mesh/src/verify_mesh_canon_0817.py` 가 **같은 함수를 그대로 불러** "
                      "낸다(CPU, 잣대를 다시 짜지 않는다)") for r in rows]
    rows.append("| `benchmark/mesh_certify.py` | 형상을 고친 뒤·의심될 때 | 10기체 형상 지문 · "
                "예산표 · 바깥 참값 · 메쉬가 파일로 나가는 «문» 배선이 골든과 같은가 | "
                "**«옳음» 이 아니라 «안 바뀜» 만 본다.** 대조 한 번은 짧고, `--full` 은 지도·"
                "적대 대조·매트릭스까지 다시 찍는다(약 295 초) |")
    return "\n".join(rows)


def po_overcount_table_canon() -> str:
    """PO 경로가 이중계상하는 몫 — 정본 판, 재질 가중."""
    rows = ["| 드론 | 묻힌 면의 반사 몫 [%] | 그중 **불투명 부품 안** [%] | PO 과대계상 [dB] |",
            "|---|---|---|---|"]
    for k in ORDER:
        f = PEER["material_weighted"][k]
        rows.append(f"| {NAME[k]} | {f['buried_power_weight_pct']:.1f} "
                    f"| {f['buried_in_opaque_weight_pct']:.2f} "
                    f"| **+{f['po_overcount_opaque_dB']:.2f}** |")
    return "\n".join(rows)


def canon_budget_table() -> str:
    sl_bl = ", ".join(f"{k[1]} {v}" for k, v in MC.SLIVER_BUDGET_BLADE_LAW.items()
                      if k[0] == GEOM.BLADE_LAW_CANON)
    pb_bl = ", ".join(f"{k[1]} {v} %" for k, v in MC.PROP_BELL_SOLID_AREA_PCT_BLADE_LAW.items()
                      if k[0] == GEOM.BLADE_LAW_CANON)
    bf = MC.BURIED_FACE_BUDGET_PCT
    bf_rng = (f"{min(v for k, v in bf.items() if k != '_default'):.1f}~"
              f"{max(v for k, v in bf.items() if k != '_default'):.1f} %")
    return "\n".join([
        "| 예산 | 정본 판에서 지금 값 | 무엇을 뜻하나 |",
        "|---|---|---|",
        f"| `BOUNDARY_EDGE_BUDGET_FIXED` | 전 기체·전 그룹 **{MC.BOUNDARY_EDGE_BUDGET_FIXED['_default']}** "
        "| 구멍(경계 모서리)은 없어야 한다. 정본에는 예외가 없다 |",
        f"| `SLIVER_BUDGET` | 기종별 {min(v for k, v in MC.SLIVER_BUDGET.items() if k != '_default')}~"
        f"{max(v for k, v in MC.SLIVER_BUDGET.items() if k != '_default')} "
        f"(정본에서 {len([1 for k in MC.SLIVER_BUDGET_BLADE_LAW if k[0] == GEOM.BLADE_LAW_CANON])}기체는 "
        "아래 날 법칙별 예산이 대신 걸린다) "
        "| 아주 뾰족한 삼각형 개수. 면적 비중이 0.0001~0.03 % 라 σ 에는 무해하고, 감시하는 이유는 "
        "법선이 수치적으로 불안정한데 PO 조명 판정이 `n̂·û>0` 이기 때문이다 |",
        f"| ⭐`SLIVER_BUDGET_BLADE_LAW` | ({GEOM.BLADE_LAW_CANON}) {sl_bl} "
        "| **날 법칙별 예산.** 기체마다 다른 평면형으로 로프트를 다시 뜨면 씨접합 슬리버 수가 "
        "달라진다 — 결함이 는 것이 아니라 다른 형상이다. 값은 실측 + 약 10 % 이고 실측치를 "
        "코드 주석 괄호에 남긴다 |",
        f"| `GROUP_OVERLAP_BUDGET_FIXED` | 기본 {MC.GROUP_OVERLAP_BUDGET_FIXED['_default']} % "
        "| **그룹 안** 에서 부품이 서로 파묻힌 비율. battery 그룹이 합집합으로 한 몸이 되어 "
        "정본 실측은 전 기체 0.00 % 다 |",
        f"| ⭐`PROP_BELL_SOLID_AREA_PCT_BLADE_LAW` | ({GEOM.BLADE_LAW_CANON}) {pb_bl} "
        "| 프로펠러가 모터 벨 솔리드 **안**에 든 면적. 정본 날은 뿌리 시위가 달라 두 기체에서 "
        "겹침이 0.4 pp 커졌다 — 허브 실측 근거가 없어 크기를 적고 넘긴다 |",
        f"| `BURIED_FACE_BUDGET_PCT` | 기종별 {bf_rng} "
        "| **전 부품쌍 매몰면** 중 «진짜 결함» 몫(설계 의도인 셸 안 금속은 뺀다) |",
        f"| `DIM_TOL_PCT` | 프롭 지름 {MC.DIM_TOL_PCT['prop_dia']:.0f} % · 외형 "
        f"{MC.DIM_TOL_PCT['envelope']:.0f} % · 대각 {MC.DIM_TOL_PCT['diagonal']:.0f} % "
        f"(mini5pro 예외 {MC.DIM_DIAGONAL_TOL_PCT['mini5pro']:.0f} %) | 공표 숫자와의 허용 오차 |",
        f"| `HANDEDNESS_MIN_ABS` | {MC.HANDEDNESS_MIN_ABS} | 날 비틀림 지표의 최소 크기. "
        "이보다 작으면 «비틀리지 않았다» 는 뜻이라 부호를 믿을 수 없다 |",
    ])


def budget_usage_table() -> str:
    """지금 예산을 얼마나 쓰고 있나 — 정본 판 실측."""
    rows = ["| 드론 | 경계 모서리 | 슬리버 (예산) | 그룹 안 겹침 최대 | 매몰 «진짜 결함» (예산) |",
            "|---|---|---|---|---|"]
    for k in ORDER:
        b, f = BUD[k], BURIED[k]
        rows.append(f"| {NAME[k]} | {b['boundary_edges']} / {b['boundary_edge_budget']} "
                    f"| {b['slivers']} ({b['sliver_budget']}) "
                    f"| {b['group_overlap_max_pct']:.2f} % "
                    f"| {f['defect_pct']:.2f} % ({f['budget_pct']:.1f} %) |")
    return "\n".join(rows)


def buried_table() -> str:
    """매몰면 전수 — 총 · 설계 의도 · 진짜 결함. PO 경로의 이중계상이 여기서 나온다."""
    rows = ["| 드론 | 총 매몰 [%] | 그중 설계 의도 [%] | ⭐진짜 결함 [%] | 예산 [%] | 못 본 컨테이너 |",
            "|---|---|---|---|---|---|"]
    for k in ORDER:
        f = BURIED[k]
        rows.append(f"| {NAME[k]} | {f['buried_pct']:.2f} | {f['design_intent_pct']:.2f} "
                    f"| **{f['defect_pct']:.2f}** | {f['budget_pct']:.1f} | {f['blind_containers']} |")
    return "\n".join(rows)


def prop_tri_table() -> str:
    """프로펠러 **만** 의 삼각형 크기 — 기체마다 날이 다르므로 기체마다 다르다."""
    rows = ["| 드론 | 프롭 삼각형 | 기체 전체 대비 | 엣지 p50 | 엣지 p95 | p95/λ | 최대/λ |",
            "|---|---|---|---|---|---|---|"]
    for k in ORDER:
        p = PROPTRI[k]
        if not p.get("has_prop"):
            continue
        rows.append(f"| {NAME[k]} | {p['n_faces']:,}장 | {p['share_pct']:.1f} % "
                    f"| {p['edge_mm']['p50']:.1f} mm | {p['edge_mm']['p95']:.1f} mm "
                    f"| {p['edge_vs_lam']['p95_over_lam']:.2f} "
                    f"| {p['edge_vs_lam']['max_over_lam']:.2f} |")
    return "\n".join(rows)


#  ⭐ 공용 표(mesh_facts_0816)는 여러 편이 함께 쓴다. 정본에서 **해소된 줄**만 이 편에서 걸러
#     낸다 — 공용 파일을 이 편이 고치면 다른 편의 서술과 갈릴 수 있기 때문이다.
_SETTLED = ("셸에 삼각형 1장 구멍", "L/W 강제가 남아 축간거리가 부푼다")


def defect_table_canon() -> str:
    keep = [ln for ln in MF.defect_table().splitlines()
            if not any(s in ln for s in _SETTLED)]
    #  ⏳ 표시는 «다른 라운드가 정한다» 는 뜻이었다. 프로펠러 라운드가 닫혔으므로 이유를 적는다.
    keep = [ln.replace("프롭 장착 높이가 함께 움직인다 ⏳",
                       "프롭 장착 높이가 함께 움직인다 — 엔진을 고쳐야 하는 자리라 미뤄 두었다")
            for ln in keep]
    return "\n".join(keep)


def unresolved_canon() -> list[str]:
    """«모른다» 목록 — 프로펠러 축에서 닫힌 것과 남은 것을 갈라 적는다."""
    out = []
    for ln in MF.unresolved_list():
        if "프로펠러 축 전부" in ln:
            out.append(
                "- **프로펠러 날의 두께** — 날의 평면형(시위 분포·정점 위치·팁)은 기체마다 정본이 "
                "정해졌지만(mesh05), **두께는 여전히 모른다.** 사진으로는 원리적으로 못 잰다 — "
                "겉보기 높이가 «시위 × sin(피치) + 두께 × cos(피치)» 라 앞항이 두께의 다섯 배쯤 "
                "되기 때문이다. 실측 근거가 있는 기체는 mini2(공식 CAD) 하나뿐이다.")
            continue
        out.append(ln)
    return out


def blind_spots_canon() -> list[str]:
    """검사기가 못 보는 것 — 정본에서 닫힌 줄은 빼고, 인증서가 새로 찾은 줄을 더한다."""
    out = [b for b in MF.BLIND_SPOTS
           if "삼각형 크기를 파장에 묶는 규약" not in b and "PO 경로의 가림" not in b]
    out += [
        "**PO 경로의 가림** — `rcs_po.py` 가 자기 docstring 에서 자기차폐·다중반사를 무시한다고 "
        "선언한다. 부품 속에 묻힌 면이 그 경로에서는 이중계상된다 — 크기는 §8.3 의 매몰면 표다.",
        "**출하된 파일 자체** — 검사는 메모리 배열에서 돌고 OBJ 는 그 뒤에 쓰인다. 좌표를 "
        "1 µm 격자로 반올림해 쓰므로 되읽은 파일은 검사한 물건과 다른 객체다"
        "(인증서 §3.1: matrice4e·mini2 파일이 저장소 자기 검사에 **실패**한다).",
        "**부품이 통째로 사라지는 것** — 그룹 하나를 지워도 검사 10계열이 전부 조용하다"
        "(인증서 §3.2: canopy 표면적 8.4 % · gear 2.1 %). 좌우 짝 중 **한쪽만** 지우면 "
        "대칭 검사가 울지만, 그룹 전체를 지우면 대칭이 유지되므로 안 운다.",
        "**매몰면 예산의 방향** — 지금 잣대는 전체 표면적 대비 비율이라 부품 하나를 통째로 "
        "묻어도 예산을 못 넘고, 값이 거꾸로 가기도 한다(인증서 §1③). 이 검사가 지키는 것은 "
        "«오늘보다 나빠지지 않음» 이다.",
        "**아주 작은 좌우 비대칭** — 한쪽 단차 0.16 mm 는 통과하고 0.30 mm 에서 실패한다"
        "(인증서 §3.4, mini5pro 실측). 예산 숫자 0.15 mm 보다 실효 문턱이 높다.",
    ]
    return out


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
        ["materials", "body_arms", "audit"],
        extra=[(CANON_LEDGER,
                "⭐**정본 판** 기하 원장(A 기하·B 대칭·F 겹침·매몰면·예산 사용) — 이 편의 표는 "
                "전부 여기서 나온다"),
               ("docs/MESH_CERTIFICATE.md",
                "메쉬 인증서 — 무엇을 장담하고 무엇은 장담 못 하는가(판정 «조건부 장담»)"),
               ("benchmark/mesh_certify.py · outputs/mesh_golden_0816.json",
                "골든 봉인 — 형상이 어제와 같은가(정점이 1 nm 이상 움직이면 문다)")]),
    "",
    f"**한 줄 요약** — 드론 {len(ORDER)}종·삼각형 {tot_faces:,}장·꼭짓점 {tot_verts:,}개·"
    f"부위(그룹) {tot_groups}개·닫힌 부품 {tot_parts}개를 전수 검사했다. "
    f"수밀 {n_wt}/{tot_parts}, 경계 모서리(구멍) {sum(BUD[k]['boundary_edges'] for k in ORDER)}개, "
    f"안쪽 법선 {tot_inward}건, winding 불일치 {tot_badwind}건. "
    "⭐ **«통과» 는 «0» 이 아니라 «선언된 예산 안» 이라는 뜻**이고, 이 편은 그 예산이 무엇인지와 "
    "지금 예산을 쓰고 있는 항목이 무엇인지를 함께 적는다. "
    "좌우비대칭·부위겹침처럼 '결함처럼 보이는 것'은 왜 결함이 아닌지도 수치로 공개한다.",
    "",
    "## ⭐ 어느 판을 잰 수인가 — 정본 판",
    "",
    "메쉬는 «지금 기본으로 지어지는 판» 이 하나로 정해져 있다. 이 편의 모든 표는 그 **정본 판**을",
    "잰 것이다. 판이 다르면 삼각형 수부터 달라지므로, 표를 인용하기 전에 어느 판인지 먼저 본다.",
    "",
    "| 무엇 | 지금 값 | 뜻 |",
    "|---|---|---|",
    f"| 메쉬 수리 기본값 `MESH_FIX_CANON` | {FIXES} | `battery` = 배터리 팩 상자와 구조판이 서로 "
    "파고들던 자리를 불리언 합집합으로 한 몸으로 만든다(**치수는 안 바꾼다**). `i5` = mini2 셸을 "
    "닫는다 |",
    f"| 날 법칙 기본값 `BLADE_LAW_CANON` | `{GEOM.BLADE_LAW_CANON}` | 기체마다 **그 기체의 순정 "
    "프로펠러** 평면형으로 날을 뜬다(정본은 mesh05) |",
    f"| 파일명 꼬리표 | `{TAG}` | 계산 결과 파일 이름에 판이 박힌다 — 옛 판에서 만든 조각을 새 판 "
    "계산이 조용히 재사용하는 사고를 막는다 |",
    "| 옛 판 재현 | `MESH_FIX=none BLADE_LAW=legacy` | 전환 직전 판을 **비트동일**로 다시 만든다 |",
    "| 전환 직전 산출물 보관 | `/data/public/sionna/archive_pre_meshfix_20260817/` | 조각 파일 "
    "3,813개 + README |",
    "",
    f"← 출처: `src/geom.py` `MESH_FIX_CANON`·`BLADE_LAW_CANON`(스위치의 단일 진리원, 환경변수를 "
    f"**호출할 때마다** 읽는다) · 원장 `{CANON_LEDGER}` `_meta`.",
    "",
    "⚠ 이 편은 **옛 원장(`report_mesh/outputs/mesh_verify.json`, 2026-08-16 13:15)을 인용하지 "
    "않는다.** 그 원장은 다른 세대의 메쉬를 잰 수라, 한 표 안에 섞이면 어느 판의 숫자인지 알 수 "
    "없게 된다.",
    "",
    "⚠ **그림 4장은 전환 직전 판에서 구운 것이다** — 이 라운드는 그림을 새로 굽지 않았다. "
    "분포의 모양과 이 편의 결론은 그대로지만, 그림 안의 절대 수치(삼각형 수 등)는 본문 표가 정본이다.",
    "",
    f"⭐ **같은 판을 두 측정기가 따로 쟀고 수가 같다.** 이 편의 원장(`{CANON_LEDGER}`)과 재질 축 원장"
    f"(`{PEER_LEDGER}`)은 서로 다른 스크립트인데, 겹치는 항목이 전부 일치한다 — 삼각형 "
    f"{tot_faces:,}장 · 꼭짓점 {tot_verts:,}개 · 닫힌 부품 {tot_parts}개 · 수밀 {n_wt}개 · 슬리버 "
    f"{tot_sliver:,}장 · 중복 꼭짓점 {tot_dup}개. 한쪽이 실수했다면 여기서 갈렸을 것이다.",
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
    f"| λ(파장) | 전파 한 주기의 길이. 본 검증 최고 대역 5.21 GHz에서 **{LAM:.1f} mm** ← 출처: mesh_verify_canon_0817.json `_meta.lam_hi_mm` |",
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
    "| **A** geometry | 삼각형이 기하학적으로 건강한가? (watertight·법선·winding·퇴화면·중복점·엣지길이) | §2~§6 |",
    "| **B** symmetry | 좌우대칭 기체가 정말 대칭인가? (미러 chamfer 거리) | §7 |",
    "| **F** overlap | 부위끼리 얼마나 겹치는가? (조립식 의도 겹침의 정량 공개) | §8 |",
    "",
    "← 출처: verify_mesh_suite.py 모듈 docstring(9개 섹션 정의). 치수 대조(C)·부피(D)·재질(E)·",
    "실기체 스캔(G)·물리 수렴(H/I)은 다음 리포트들에서 다룬다.",
))

# ---------------------------------------------------------------- 3. 검사 대상
cells.append(md(
    f"## 1. 검사 대상 — 삼각형으로 지은 드론 {len(ORDER)}종",
    "",
    f"검사 대상은 파라메트릭 CAD 로 지은 드론 {len(ORDER)}종({', '.join(NAME[k] for k in ORDER)}),",
    f"합계 **삼각형 {tot_faces:,}장, 꼭짓점 {tot_verts:,}개, 부위(그룹) {tot_groups}개, "
    f"닫힌 부품 {tot_parts}개**다",
    f"← 출처: `{CANON_LEDGER}` §A_geometry (n_faces·n_verts·n_groups·groups.n_parts 합산).",
    "",
    f"아래는 {len(ORDER)}종 중 가장 큰 **S1000+** (8로터 옥토콥터)다. 가운데 wireframe 패널이 바로 이 리포트의",
    "주인공인 '삼각형'들이다 — 매끈해 보이는 몸체가 실은 작은 삼각형의 모자이크임을 볼 수 있다.",
    "",
    "![wireframe s1000plus](outputs/figures/wireframe_s1000plus.png)",
    "",
    f"*그림 1 — S1000+: 셰이딩(색=재질) / 와이어프레임(삼각형) / 상면도. 삼각형 {s1k['n_faces']:,}장,"
    f" 부위 {s1k['n_groups']}개(팔 8·모터 8·프로펠러 부품 {s1k['groups']['prop']['n_parts']}개 등).",
    "← 출처: 그림 생성 report_mesh/src/viz_mesh_reports.py `fig_wireframes()`,",
    "수치 mesh_verify_canon_0817.json §A_geometry.s1000plus*",
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
    "**검사기는 하나가 아니다** — 여섯이고 역할이 다르다:",
    "",
    checker_table_canon(),
    "",
    "도구별 채택 이유와 대안:",
    "",
    "| 도구 | 무엇에 쓰나 | 왜 이것인가 (대안은 왜 아닌가) |",
    "|---|---|---|",
    "| **trimesh** | watertight·winding·부호부피 판정 | 파이썬 메쉬 검증의 사실상 표준. `is_watertight`·`is_winding_consistent`·부호있는 `volume` 이 내장 — 직접 짜면 검증기 자체를 또 검증해야 한다 ← 출처: src/mesh_check.py check_mesh()(세 판정 모두 trimesh 내장 속성 호출) |",
    "| **scipy cKDTree** | 대칭 검사(B)의 최근접점 탐색 | 점이 최대 백만 개(S1000+ full "
    f"{B['s1000plus']['full']['n_points']:,}점 ← mesh_verify_canon_0817.json §B). 모든 쌍을 재는 브루트포스는 조 단위 연산이라 불가능, KD-트리는 점당 log 시간 |",
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
    "import json, os, sys",
    'sys.path.insert(0, os.path.abspath("../src"))   # 저장소 src/ — 아래 셀들이 drones 를 쓴다',
    'V = json.load(open("outputs/mesh_verify_canon_0817.json", encoding="utf-8"))',
    'meta = V["_meta"]',
    'print("검증 대상 드론 :", ", ".join(meta["drones"]))',
    'print("메쉬 엔진      :", meta["mesh_engine"])',
    'print(f"최고대역 파장 λ : {meta[\'lam_hi_mm\']:.1f} mm  (WiFi 5.21 GHz — 엣지 길이의 잣대)")',
    'print("섹션           :", ", ".join(k for k in V if not k.startswith("_")))',
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
    f"**결과: {n_wt}/{tot_parts} 부품 수밀 · 경계 모서리(구멍) "
    f"{sum(BUD[k]['boundary_edges'] for k in ORDER)}개**",
    f"← 출처: `{CANON_LEDGER}` §A_geometry 각 드론 groups.watertight ·",
    "`budget_usage`(아래 코드 셀이 그대로 집계한다).",
    "",
    "### 3.1 «구멍 없음» 은 예산으로 선언한다",
    "",
    "출하 게이트가 쓰는 잣대는 «수밀 참/거짓» 이 아니라 **경계 모서리 수**다 — 삼각형 하나만 쓰는",
    "모서리를 세는 것이라, 구멍이 몇 개인지·얼마나 큰지가 숫자로 남는다. **정본 판에서는 예외가",
    "없다**: `BOUNDARY_EDGE_BUDGET_FIXED` 가 전 기체·전 그룹에 0 을 건다.",
    "",
    "예산은 «이만큼이 옳다» 가 아니라 **«지금 이만큼이다» 라는 선언**이다. 그리고 정본에서는",
    "예산이 **판마다 따로 선언**된다 — 날 법칙이 바뀌면 로프트가 다시 떠지므로 같은 잣대라도",
    "수가 달라지기 때문이다:",
    "",
    canon_budget_table(),
    "",
    "← 출처: `src/mesh_check.py` 예산 표를 이 노트북 생성기가 **직접 읽어** 주입한다"
    "(코드와 리포트가 갈리는 자리를 없애려는 것이다).",
    "",
    "⚠ **«예산을 올려 통과시킨다» 는 안티패턴이다** — 인증서가 그렇게 경고한다. 그래서 날 법칙별",
    "예산은 실측 + 약 10 % 로만 두고, 실측치를 코드 주석 괄호에 남긴다. 지금 쓰고 있는 몫은 이렇다:",
    "",
    budget_usage_table(),
    "",
    f"← 출처: `{CANON_LEDGER}` `budget_usage`·`buried_faces`.",
    "",
    "### 3.2 ⭐ mini2 셸을 닫은 이유는 산란이 아니라 **검사 정확도**다",
    "",
    "정본 수리 `i5` 는 mini2 의 셸을 닫는다. 이 수리로 σ(레이더 반사)는 **안 움직인다** —",
    "구멍 넓이가 5e-06 mm² 급이라 재보면 차이가 1e-10 dB 다. 그런데도 켜는 이유가 있다.",
    "",
    "**껍질이 열려 있으면 «안/밖» 이라는 말 자체가 성립하지 않는다.** `contains()`(이 점이 이 부품",
    "안인가)가 정의되지 않으므로, 내부 판정을 쓰는 검사가 그 부품을 **컨테이너 목록에서 조용히",
    "빼 버린다**. 그 결과가 이것이다:",
    "",
    "| 셸 상태 | 검사가 읽는 mini2 총 매몰면 | 뜻 |",
    "|---|---|---|",
    "| 열린 셸(구멍 있음) | 29.71 % | body 를 컨테이너에서 빼고 세어 **14.74 pp 를 못 본다** |",
    "| 닫힌 셸 | 44.45 % | 참값 |",
    "",
    "← 출처: `outputs/mesh_layer2_holes_poles_0816.json` `I5_mini2_body_구멍.⭐진짜_피해는_간접이다`.",
    "",
    f"즉 이 수리의 값어치는 **검사기가 자기가 수리한 사본을 안 봐도 되게 만드는 것**이다"
    "(§2.1 규약과 같은 줄기다).",
    "",
    f"⚠ 위 표의 44.45 % 는 **셸을 닫는 수리만** 켠 판에서 잰 참값이다. 정본은 아래 `battery` 수리도 "
    f"함께 켜져 있어 그만큼 덜 묻힌다 — 지금 mini2 총 매몰면은 {BURIED['mini2']['buried_pct']:.2f} %, "
    f"그중 «진짜 결함» 은 {BURIED['mini2']['defect_pct']:.2f} % 다(§8.3).",
    "",
    f"**같은 층의 다른 수리 `battery`.** 배터리 팩 상자와 구조판 상자가 "
    f"{min(BT_OV):.1f}~{max(BT_OV):.1f} % 씩 서로 파고들어 PO 가 그 면적을 두 번 세던 자리를, "
    "불리언 합집합으로 한 몸으로 만든다. **치수는 한 mm 도 안 바꾼다** — 상자 크기·위치는 그대로 "
    "두고 겹친 부분만 없앤다(기종별 실측 치수가 없어서 상자를 옮기는 쪽은 «지어내기» 가 된다).",
    "정본에서 `battery` 그룹의 그룹 안 겹침은 전 기체 0.00 % 이고, 예산도 기본값",
    f"{MC.GROUP_OVERLAP_BUDGET_FIXED['_default']} % 로 **같이 조여져 있다** — 안 그러면 «고쳤는데 "
    "다시 겹쳐도» 통과한다.",
    "",
    f"**얼마나 큰 자리였나 — 고쳐서 직접 쟀다.** 겹침이 있던 {BT_N}기체에서 PO 방위평균 σ 가 "
    f"{BT_MONO[0]:.2f}~{BT_MONO[1]:.2f} dB 만큼 밝은 쪽으로 치우쳐 있었고(모노스태틱, 고각 0°·−30°), "
    f"바이스태틱(β=120°, 고각 −30°)에서는 방위평균으로도 최대 {BT_BI:.1f} dB 였다. "
    f"⚠ **방위 하나씩 보면 훨씬 크고 부호가 양쪽으로 갈린다** — 모노에서 밝은 쪽 최대 "
    f"**{_sgn(BT_WORST_HI)} dB**, 어두운 쪽 최대 **{_sgn(BT_WORST_LO)} dB**(둘 다 mini2), "
    f"바이스태틱에서는 {_sgn(BT_BI_WORST_HI)} / {_sgn(BT_BI_WORST_LO)} dB 다. 즉 방위평균은 "
    "상쇄된 값이므로 «최대 오차» 로 읽으면 안 된다. "
    "겹침이 0 인 기체(matrice4e·phantom3·m350rtk)는 0.00 dB 로 안 움직인다 "
    "← 출처: `outputs/mesh_layer2_battery_overlap_0816.json` `σ`(`azimuth_mean_db`·`worst_az_db`; "
    "예측이 아니라 **고친 메쉬로 다시 잰 값**이다). ⚠ SBR 은 first-hit 이라 이 오차가 구조적으로 "
    "0 이므로, 이 dB 는 **PO 경로 전용**이다.",
    "",
    f"⚠ **이 수리는 σ 만 건드리는 것이 아니다.** 겹쳐 있던 몫이 사라지면서 배터리 부피가 "
    f"−{BT_DV:.2f} % 줄고, 그 결과 질량 −{abs(max(BT_DM)):.1f}~−{abs(min(BT_DM)):.1f} g · 관성 대각 "
    f"{min(BT_DI):+.1f}~{max(BT_DI):+.1f} % · 무게중심 {min(BT_DC):.2f}~{max(BT_DC):.2f} mm 가 "
    "따라 움직인다. 자세 응답(로터가 흔들리는 정도)을 다루는 모델은 이 값을 써야 한다 "
    "← 출처: `outputs/mesh_layer2_battery_overlap_0816.json` `질량축_감사I9`·`인구조사`.",
))

cells.append(cc(
    "# watertight/법선/winding/퇴화면 — 부위(그룹)별 전수 집계",
    'from drones import drone_label            # 표적 목록·표시명의 단일 출처',
    'ORDER = list(V["_meta"]["drones"])         # = DRONES 레지스트리 전수(개수 하드코딩 없음)',
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
    "← 출처: src/geom.py 주석 \"PO(rcs_po)는 조명면을 n̂·û>0 로 고르므로 법선 방향이 맞아야 한다\".",
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
    "← 출처: mesh_verify_canon_0817.json §A_geometry groups.inward_normals·bad_winding (위 코드 셀 합계 행).",
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
    "mesh_verify_canon_0817.json §A_geometry (degenerate·dup_vertices·unused_vertices, 아래 셀에서 확인).",
    "",
    "### 5.1 ⭐ «퇴화면 0» 은 어느 자로 잰 0 인가",
    "",
    "**자가 둘이고, 답이 다르다.** 이 구별을 안 적으면 위의 0 이 과장된다.",
    "",
    "| 자 | 무엇을 세나 | 함대 결과 |",
    "|---|---|---|",
    f"| **절대** — 면적 < {MC.DEGENERATE_AREA_M2:g} m² | 진짜 넓이 0 | **{tot_degen}장** |",
    f"| **상대** — 최소 내각 < {MC.SLIVER_MIN_ANGLE_DEG}° | 아주 가늘고 긴 삼각형(슬리버) "
    f"| 기종당 {sl_lo}~{sl_hi}장(합계 {tot_sliver:,}장) |",
    "",
    "절대 잣대는 **기체 크기에 따라 뜻이 달라진다** — 같은 1e-14 m² 가 Mini 2 에서는 큰 삼각형이고",
    "S1000+ 에서는 먼지다. 그래서 지금 게이트는 상대 잣대를 **겸용**하고, 슬리버 개수를 기종별",
    "예산으로 선언한다(§3.1). 정본 판에서는 그 예산이 **날 법칙별**로 갈려 있다 —",
    "날 평면형이 기체마다 다르면 불리언 씨접합에서 나오는 얇은 삼각형 수도 기체마다 달라지기",
    "때문이다. 늘어난 것이 결함이 아니라는 근거는 옆 축에 있다: 정본에서 안쪽 법선·winding 깨짐·",
    "퇴화면·경계 모서리가 **전 기체 0** 이다(= 불리언이 정상이라는 뜻).",
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
    "1퍼센타일/중앙값. ← 출처: 그림 report_mesh/src/viz_mesh_reports.py `fig_tri_quality()`,",
    "수치 mesh_verify_canon_0817.json §A_geometry edge_mm·tri_min_angle_deg*",
    "",
    "**왜 엣지가 파장보다 충분히 짧아야 하나.** 메쉬의 곡면은 사실 평평한 삼각형의 모자이크다.",
    "전파 입장에서 표면의 '매끈함'은 파장 λ 를 자로 재서 판단한다: 삼각형 한 장이 λ 에 비해 충분히",
    "작으면 모자이크의 각진 단차가 파장 아래에 묻혀 **연속 곡면처럼** 산란하고, λ 보다 크면 각 삼각형이",
    "**개별 평면 거울**처럼 행동해 실물에 없는 반짝임(글린트)을 만든다. 디지털 사진과 같은 이치다 —",
    "픽셀이 충분히 작으면 눈에는 곡선으로 보인다. 여기서 픽셀 크기의 잣대가 파장이다.",
    "",
    f"기준 파장은 시뮬레이션 최고 대역인 WiFi 5.21 GHz 의 **λ = {LAM:.1f} mm** 로 잡았다 — 파장이",
    "가장 짧은 대역이 가장 엄격한 잣대이기 때문이다 ← 출처: verify_mesh_suite.py",
    "`LAM_HI = C0/5.21e9` 주석 \"최고 대역 파장 — 엣지 길이 기준\".",
    "",
    "| 드론 | 엣지 p50 | 엣지 p95 | p95/λ | 최소각 p1 | 최소각 중앙값 |",
    "|---|---|---|---|---|---|",
    *[f"| {NAME[k]} | {A[k]['edge_mm']['p50']:.1f} mm | {A[k]['edge_mm']['p95']:.1f} mm | "
      f"{A[k]['edge_vs_lam52']['p95_over_lam']:.2f} | {A[k]['tri_min_angle_deg']['p1']:.1f}° | "
      f"{A[k]['tri_min_angle_deg']['median']:.1f}° |" for k in ORDER],
    "",
    "← 출처: mesh_verify_canon_0817.json §A_geometry (edge_mm, edge_vs_lam52, tri_min_angle_deg).",
    "",
    f"엣지의 95 % 가 λ 의 {min(A[k]['edge_vs_lam52']['p95_over_lam'] for k in ORDER):.2f}~"
    f"{max(A[k]['edge_vs_lam52']['p95_over_lam'] for k in ORDER):.2f}배 구간에 있다.",
    "곡면(몸체·캐노피)은 파장 대비 충분히 잘게 쪼개져 있다.",
    "",
    "### 6.1 ⭐ 프로펠러의 삼각형은 따로 잰다",
    "",
    "프롭은 위 표에 섞어 읽으면 안 된다. 로터 1개당 삼각형 수가 정해져 있는데 프롭 지름은 기체마다",
    "4배 넘게 벌어지므로, 큰 기체일수록 프롭 삼각형이 성기다. 정본 판에서는 **기체마다 날 평면형이",
    "다르므로** 이 축도 기체마다 다른 수다 — 그래서 따로 잰다:",
    "",
    prop_tri_table(),
    "",
    f"← 출처: `{CANON_LEDGER}` `prop_triangles`(프롭 그룹 삼각형만, 엣지 잣대는 §6 표와 같다).",
    "",
    f"**프롭은 함대에서 가장 잘게 쪼개진 부위다** — p95 가 λ 의 "
    f"{min(PROPTRI[k]['edge_vs_lam']['p95_over_lam'] for k in ORDER):.2f}~"
    f"{max(PROPTRI[k]['edge_vs_lam']['p95_over_lam'] for k in ORDER):.2f}배,",
    f"최장 엣지도 {max(PROPTRI[k]['edge_vs_lam']['max_over_lam'] for k in ORDER):.2f}λ 를 안 넘는다"
    f"(가장 성긴 쪽이 {NAME[max(ORDER, key=lambda k: PROPTRI[k]['edge_vs_lam']['max_over_lam'])]},"
    f" 가장 촘촘한 쪽이 {NAME[min(ORDER, key=lambda k: PROPTRI[k]['edge_vs_lam']['max_over_lam'])]}).",
    f"삼각형 수로 보면 프롭이 기체 전체의 "
    f"{min(PROPTRI[k]['share_pct'] for k in ORDER):.0f}~{max(PROPTRI[k]['share_pct'] for k in ORDER):.0f} %"
    " 를 차지한다 — 날이 곡면이라 잘게 쪼개야 하기 때문이다.",
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
    'lam = V["_meta"]["lam_hi_mm"]',
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
    "← 출처: 그림 viz_mesh_reports.py `fig_symmetry()`, 수치 mesh_verify_canon_0817.json §B_symmetry*",
    "",
    "| 드론 | 기체만 p95 | 전체 p95 | 배율 |",
    "|---|---|---|---|",
    *[f"| {NAME[k]} | {fr95[k]:.2f} mm | {fu95[k]:.1f} mm | ×{fu95[k]/fr95[k]:.0f} |" for k in ORDER],
    "",
    "← 출처: mesh_verify_canon_0817.json §B_symmetry chamfer_mm.p95 (full/frame_only).",
    "",
    f"**기체만 보면 {len(ORDER)}종 전부 p95 ≤ {max(fr95.values()):.1f} mm ≤ 2 mm** — 즉 샘플링 해상도 안이다.",
    "기하학적으로는 사실상 완전 대칭이라는 뜻이다.",
    "",
    f"**그런데 프로펠러를 포함하면 {min(fu95.values()):.0f}~{max(fu95.values()):.0f} mm 로 뛴다.",
    "이것은 결함이 아니라 물리다.** 프로펠러 날개는 피치와 트위스트가 들어간 비틀린 곡면이라",
    "**카이럴**하다 — 거울에 비추면 반대손(반대 회전방향용) 날개가 되어 원본 어디에도 겹칠 짝이 없다.",
    "실제 드론도 인접 로터가 서로 반대로 돌도록 CW/CCW 프로펠러를 섞어 달며(반토크 상쇄), 우리 메쉬도",
    "로터마다 dir=+1/−1 을 교대로 준다 ← 출처: src/drones.py rotor_layout() docstring",
    "\"dir 은 인접 로터가 반대로 도는 멀티로터 관례(대각쌍 동일)\"·323행. 날개 장착 위상도 로터마다",
    "달라(base_ang 오프셋) 거울상과 어긋난다. verify_mesh_suite.py 의 sec_B docstring 도 같은 경고를",
    "박아 놨다: \"full 의 큰 p95 는 결함이 아니라 프로펠러 물리다. 기체 대칭성은 frame_only 로",
    "판정한다\" ← 출처: verify_mesh_suite.py.",
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
    "### 8.1 왜 부위를 따로 만들어 겹쳐 넣나",
    "",
    "우리 드론은 부위(몸체·캐노피·배터리·모터·프로펠러…)를 **따로 닫힌 입체로 만들어 서로 밀어 넣는**",
    "조립식이다. 그래서 부위끼리 부피가 겹친다 — 배터리는 몸체 속에 통째로 들어가 있고, 모터 밑동은",
    "팔에 박혀 있다. 숨길 일이 아니라 **정량 공개**할 일이다: watertight 부품끼리 불리언 교집합을 돌려",
    "겹침 부피를 전부 쟀다 ← 출처: verify_mesh_suite.py sec_F_overlap()(manifold 엔진,",
    "bbox 가 겹칠 때만 시도).",
    "",
    "![overlap matrix](outputs/figures/overlap_matrix.png)",
    "",
    "*그림 4 — 드론별 부위×부위 겹침 부피 행렬 [cm³]과 총부피 대비 %. ← 출처: 그림",
    "viz_mesh_reports.py `fig_overlap()`, 수치 mesh_verify_canon_0817.json §F_overlap*",
    "",
    "| 드론 | 겹침 합계 | 총부피 대비 | 최대 겹침 쌍 |",
    "|---|---|---|---|",
    *[f"| {NAME[k]} | {Fo[k]['total_overlap_cm3']:.0f} cm³ | {ovp[k]:.2f}% | "
      f"{Fo[k]['pairs'][0]['a']}–{Fo[k]['pairs'][0]['b']} ({Fo[k]['pairs'][0]['overlap_cm3']:.0f} cm³) |"
      for k in ORDER],
    "",
    "← 출처: mesh_verify_canon_0817.json §F_overlap (total_overlap_cm3·overlap_pct_of_volume·pairs).",
    "",
    f"s1000plus 를 뺀 {len(ORDER) - 1}종이 {min(v for k, v in ovp.items() if k != 's1000plus'):.0f}~"
    f"{max(ovp.values()):.0f} % 씩 겹친다. 셸형 기체의 1위는 예외 없이 battery–body — 예컨대 Mavic 4 Pro 의",
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
    "   경계가 사라진다 ← 출처: viz_mesh_reports.py `fig_build_stages()` 캡션 \"each part =",
    "   one OBJ = one Sionna material\".",
    "2. **프로펠러는 돌아야 한다.** 마이크로도플러 시뮬레이션은 프로펠러 메쉬를 매 프레임 회전시킨다.",
    "   몸체와 한 덩어리면 관절이 죽는다 ← 출처: src/drones.py build_propeller() docstring",
    "   (\"pose_articulated 가 이 메쉬를 z회전(스핀)시켜 각 로터에 배치한다\")·pose_articulated().",
    "3. **묻힌 표면을 SBR 은 자동으로 거른다.** 광선이 처음 맞는 면만 반사에 넣으므로 몸체 속에",
    "   묻힌 배터리 표면은 가려진다(occlusion). ⚠ **PO 는 그렇지 않다** — §8.3 에서 따로 다룬다.",
    "",
    "**⭐ 그런데 «부위 사이» 와 «부위 안» 은 다른 이야기다.** 위 표는 전부 **부위 사이**(battery ↔ body "
    "처럼 다른 그룹끼리)의 겹침이고, 그것은 설계다. 반대로 **같은 그룹 안**에서 부품 둘이 서로 "
    "파고드는 것은 설계가 아니다 — 그 자리는 재질도 같고 부위도 같아서 겹친 면이 그냥 **두 번 세어질** "
    "뿐이다. 정본 판은 그 자리를 하나 없애 놓았다(`battery` 팩 상자 ↔ 구조판, 불리언 합집합, 치수 "
    f"무변경). 지금 그룹 안 겹침은 전 기체 최대 "
    f"{max(BUD[k]['group_overlap_max_pct'] for k in ORDER):.2f} % 이고, 예산은 "
    f"{MC.GROUP_OVERLAP_BUDGET_FIXED['_default']} % 다(§3.1·§3.2).",
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
    "선언한다. 즉 §8.1 의 «묻힌 면은 전파가 못 본다»(SBR 이 가림으로 거른다) 는 **SBR 경로의 성질**이고, PO 경로에서는",
    "묻힌 면이 그대로 면적에 더해진다.",
    "",
    "**먼저 면적으로.** 정본 판에서 매몰면을 전 부품쌍에 대해 전수로 센 결과다. 두 종류를 갈라",
    "적는다 — 셸 안의 금속(battery·pcb 같은 **설계 의도**)은 결함이 아니고, 그 밖의 매몰이",
    "«진짜 결함» 이다:",
    "",
    buried_table(),
    "",
    f"← 출처: `{CANON_LEDGER}` `buried_faces`(엔진은 `src/mesh_buried.py` `buried_census`, "
    "예산은 `mesh_check.BURIED_FACE_BUDGET_PCT`).",
    "",
    "예산 값은 «선언 시점 실측 + 약 10 %» 라, 지금 값이 그 아래에 있다는 것은 매몰면이 늘지 않았다는",
    "뜻이다. battery 그룹이 한 몸이 되면서 «진짜 결함» 몫이 셸형 기체에서 특히 내려가 있다.",
    "",
    "«못 본 컨테이너» 열이 전 기체 0 인 것이 중요하다 — 수밀이 아니어서 안/밖을 못 따지는 부품이",
    "하나도 없다는 뜻이고, 이것이 §3.2 에서 mini2 셸을 닫은 값어치다. **«못 봄» 을 0 으로 보고하지",
    "않는 것**이 이 검사의 규약이다.",
    "",
    "**그 다음 재질 가중으로.** 면적만 세면 금속 1 cm² 와 플라스틱 1 cm² 를 같게 센다. ③ 의 자로",
    "재면 이렇다:",
    "",
    po_overcount_table_canon(),
    "",
    f"← 출처: `{PEER_LEDGER}` `material_weighted`(정본 판 재측정, 이 시리즈의 재질 축 원장).",
    "",
    "⚠ **이 dB 는 «불투명 부품 안에 묻힌 면» 만 센 값이다.** 셸 안의 금속처럼 설계 의도인 매몰까지",
    "전부 세면 훨씬 크다(같은 원장 `po_overcount_allburied_dB`) — 그러나 그쪽은 결함이 아니라",
    "**전파가 실제로 보는 것**이라 빼면 안 된다. 두 수를 섞지 말 것.",
    "",
    "**캐노피는 특히 죽은 무게다.** 상단 캐노피는 여러 기체에서 셸 안에 69~100 % 묻혀 있어,",
    "SBR 기여가 **정확히 0** 이다(first-hit 이 될 수 없고, 투과 패스에서는 셸이 제외된다).",
    "재질이 플라스틱이라 PO 쪽 과대도 작다 — 빼도 방위평균 σ 가 0.03~0.09 dB 밖에 안 움직인다",
    "← 출처: `outputs/mesh_inspect_materials_check_0816.json` `rf_estimates.buried_canopy`.",
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
    defect_table_canon(),
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
    *unresolved_canon(),
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
    "   실물 충실도는 별도 검사다 — 공식 제원 대조와 실기체 3D 스캔 대조가 다음 편(mesh08)의",
    f"   주제이고, 거기서 «맞춰 놓은 축» 과 «독립 검증» 을 가른다(치수 최악 "
    f"{max(V['C_dims'][k]['worst_err_pct'] for k in ORDER):.2f} % 는 사다리꼴 로터 배치인 "
    f"{NAME['mini5pro']} 의 «대각» 한 항목이다).",
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
    *[f"- {b}" for b in blind_spots_canon()],
    "",
    "### 9.1 ⭐ 인증서가 «장담한다» 고 적은 것과 «못 한다» 고 적은 것",
    "",
    "이 편의 검사들은 따로 노는 항목이 아니라 하나의 문서로 묶여 있다 —",
    "`docs/MESH_CERTIFICATE.md`. 판정은 **«조건부 장담»** 이고, 조건이 무엇인지가 이 절의 요점이다.",
    "인증서는 범주 18개(M0~M17)로 결함이 있을 수 있는 자리를 나누고, 각 검사마다 **일부러 결함을",
    "심어 정말 우는지**(양성 대조)를 확인한 뒤, 형상을 지문으로 봉인한다.",
    "",
    "**장담하는 쪽** — 자기 무결성(메쉬가 스스로 앞뒤가 맞는가)과 회귀(어제와 같은가):",
    "",
    "| 무엇 | 눈금 | 대조 |",
    "|---|---|---|",
    "| 부품마다 껍질이 닫혀 있고 면 방향이 일관되며 안팎이 안 뒤집혔다 | 경계 모서리 0 · 비다양체 0 · "
    "부호부피 > 0 | 양성 대조 있음(16/16 · 41/41) |",
    "| 나비넥타이 정점·중복 삼각형·자기교차가 없다 | 전부 0쌍 | 양성 대조 있음 |",
    "| 곡면이 파장 대비 잘게 쪼개져 있다 | 사지타 ≤ λ/16 위반 면적 ≤ 0.01 %(3.5·5.8 GHz) | "
    "원통·구 해석해로 자 검정(오차 ≤ 0.6 %) |",
    "| 프로펠러 손잡이(좌/우)와 회전방향 배치가 규약대로다 | 지표 \\|h\\| 0.16~0.29 · Σdir = 0 | "
    "양성 대조 32/32 |",
    "| 프롭 지름이 스펙과 1 % 안, 로터 대각이 3 % 안 | 실측 잔차 프롭 −0.000 % | "
    "경계 대조(+0.9 % 통과 / +1.1 % 실패) |",
    "| 프로펠러가 모터 벨 속에 박혀 있지 않다 | 솔리드 내부판정 면적 % | 양성 대조 새로 심음 |",
    "| matrice4e 는 공식 CAD 라는 독립 참값을 갖는다(16행) | 그 잣대는 **0.07 mm** 를 가른다 | "
    "경계 대조 6/6 |",
    "| 그룹 라벨이 세 재질표에 다 있고 조용한 폴백이 없다 | 미등록 0 | 양성 대조 39/39 |",
    "| 오늘의 형상이 어제와 같다 | 골든 지문 — **1 nm** 이상 움직이면 문다 | 봉인기 적대 21/21 |",
    "",
    "**장담 못 하는 쪽** — 실물 충실도(진짜 기체와 같은가)와 완전성(있어야 할 것이 다 있는가):",
    "",
    "| 무엇 | 크기 |",
    "|---|---|",
    "| 출하된 OBJ 파일 자체는 검사된 적이 없다 | 좌표를 1 µm 격자로 반올림해 쓰므로 되읽으면 "
    "**2/10 기체가 저장소 자기 검사에 실패**한다(면적 0 삼각형 6장·비다양체 모서리 6개) |",
    "| 부품이 통째로 사라져도 못 본다 | canopy(표면적 8.4 %)·gear(2.1 %) 를 지워도 검사 10계열이 "
    "전부 조용하다 |",
    "| 매몰면 예산은 그 결함으로는 실패할 수 없다 | 부품 하나를 통째로 묻어도 예산을 못 넘고, "
    "값이 거꾸로 가기도 한다 |",
    "| 바깥 참값과 지금 어긋난 자리 | **77행 중 24행**(최대 −6.5 %) — 상세는 mesh08 |",
    "| 독립 참값이 아예 없는 기체 | s1000plus · m350rtk **0행** |",
    "| 기체 × 부품 120칸 중 근거가 있는 칸 | 등급이 붙은 칸 37, 그중 **독립 근거가 있는 칸 15** |",
    "| 짐벌을 구속하는 바깥 검사 | **없다**(사진 대비 +26 %, 판정 면제) |",
    "| 예산의 성격 | 예산 근처 57행이 전부 80 % 이상 소진돼 있고 그중 **56행이 «선언 스냅샷»** — "
    "지키는 것은 «오늘보다 나빠지지 않음» 이지 «옳음» 이 아니다 |",
    "",
    "← 출처: `docs/MESH_CERTIFICATE.md` §2·§3(근거 시험은 "
    "`benchmark/adv_mesh_certificate_probes_0816.py`).",
    "",
    "### 9.2 ⭐ 지금 봉인은 «다른 메쉬» 를 가리킨다 — 재발급 대기",
    "",
    "인증서는 **자기가 어느 형상에 대한 것인지**를 지문으로 못 박고, 지문이 달라지면 그 순간",
    "장담이 끝난다고 스스로 선언한다(인증서 §5 무효 조건 1·6). 정본 전환이 정확히 그 조건이다 —",
    "지금 봉인 대조를 돌리면 이렇게 나온다:",
    "",
    "```text",
    "골든 봉인 대조 — outputs/mesh_golden_0816.json  (봉인 2026-08-17 03:26 KST)",
    "  지금 2026-08-17 14:15 KST · 기체 10대 · 형상 동일 0/10",
    "",
    "🔴 [인증서유효] 인증서 dimension 는 **다른 메쉬**에 대한 것이다 (10/10 기체 불일치 → 재발급 필요)",
    "🔴 [형상] x500v2 — 형상이 바뀌었다   삼각형 19030 → 20198 (+1168) · 정점 9615 → 10199 (+584)",
    "       그룹 prop: 면 12736→13904 (+1168) · 부피 +6.09 % · 면적 +4.80 %",
    "       치수 prop_dia: 254.000 → 254.000 mm (-0.000 mm, -0.00 %)",
    "🟠 [예산] mesh_check — 검사 잣대·예산이 바뀌었다 (2건)",
    "       SLIVER_BUDGET_BLADE_LAW · PROP_BELL_SOLID_AREA_PCT_BLADE_LAW 신설",
    "```",
    "",
    "**읽는 법.** 빨강은 «메쉬가 나빠졌다» 가 아니라 «봉인이 가리키던 물건이 아니다» 라는 뜻이다.",
    "바뀐 자리는 정본 전환이 의도한 자리 그대로다 — 프로펠러 면이 기체마다 늘었고(x500v2 +1,168장),",
    "**프롭 지름 같은 공표 치수는 소수점까지 그대로**다. 그리고 정본 판 자체는 전수 검사를",
    "10/10 통과한다(이 편의 §3~§8 이 그 결과다).",
    "",
    "⇒ 지금 상태를 한 줄로: **검사는 통과, 봉인은 재발급 대기.** 인증서의 «장담» 목록(§9.1 위쪽)은",
    "형상이 아니라 **검사 구조**에 대한 진술이라 그대로 유효하고, 지문표·«어긋난 24행» 같은 수치는",
    "정본 판에서 다시 찍어야 한다. 절차는 `benchmark/mesh_certify.py --update --reason \"…\"` 이고,",
    "형상을 고치는 라운드가 다 착지한 뒤에 하는 것이 맞다(중간 상태를 골든으로 굳히지 않으려는 것이다).",
    "",
    "요약 판정:",
    "",
    "| 검사 | 결과 | 판정 |",
    "|---|---|---|",
    f"| 수밀 (부품 {tot_parts}개) | {n_wt}/{tot_parts} · 경계 모서리 "
    f"{sum(BUD[k]['boundary_edges'] for k in ORDER)}개 | 통과 (정본에는 선언된 예외가 없다) |",
    f"| 안쪽 법선 | {tot_inward}건. 부호부피를 두 번 잰다 — trimesh 로 한 번, "
    "**trimesh 를 전혀 안 거치고 출하 인덱스에서** 손으로 한 번 | 통과 |",
    f"| winding 불일치 / 퇴화면(절대) / 중복점 / 미사용점 | {tot_badwind} / {tot_degen} / {tot_dup} / {tot_unused} | 통과 |",
    f"| 퇴화면(상대 — 최소 내각 <{MC.SLIVER_MIN_ANGLE_DEG}°) | 기종당 {sl_lo}~{sl_hi}장 "
    "| **예산 안** (기종별·날 법칙별 선언) |",
    f"| 엣지 p95 vs λ({LAM:.1f} mm) | 기체 {min(A[k]['edge_vs_lam52']['p95_over_lam'] for k in ORDER):.2f}~"
    f"{max(A[k]['edge_vs_lam52']['p95_over_lam'] for k in ORDER):.2f}λ · 프롭만 "
    f"{min(PROPTRI[k]['edge_vs_lam']['p95_over_lam'] for k in ORDER):.2f}~"
    f"{max(PROPTRI[k]['edge_vs_lam']['p95_over_lam'] for k in ORDER):.2f}λ | 통과 |",
    f"| 좌우대칭(기체만 p95) | ≤ {max(fr95.values()):.1f} mm (샘플링 한계 안) | 통과 |",
    f"| 매몰면 «진짜 결함» | {min(BURIED[k]['defect_pct'] for k in ORDER):.1f}~"
    f"{max(BURIED[k]['defect_pct'] for k in ORDER):.1f} % · 못 본 컨테이너 "
    f"{sum(BURIED[k]['blind_containers'] for k in ORDER)}개 | **예산 안** (기종별 선언) |",
    "| 부위 겹침 | 설계된 겹침. SBR 은 옳게 처리, PO 는 §8.3 만큼 밝게 | 공개됨 |",
    "| 부착·치수·재질 배정 | §8.4 의 결함 지도 | **일부 미해결 — 선언됨** |",
    "| 골든 봉인(형상이 어제와 같은가) | 정본 전환으로 10/10 형상이 바뀌었다 | **재발급 대기**(§9.2) |",
    "",
    f"← 출처: `{CANON_LEDGER}` §A_geometry·§B_symmetry·§F_overlap·`buried_faces` 집계"
    f"(전체 판정 all_ok={all_ok}) · `docs/MESH_CERTIFICATE.md` · 2026-08-16 원장 4종.",
))

# ---------------------------------------------------------------- 13. 재현
cells.append(md(
    "## 10. 재현 방법 · 다음 리포트",
    "",
    "```bash",
    "PY=/workspace/.venvs/py312/bin/python",
    "cd /workspace/sionna",
    "",
    "# 1) 이 편의 원장 재생성 → report_mesh/outputs/mesh_verify_canon_0817.json",
    "#    (정본 판 A·B·C·D·F·G + 매몰면 + 예산 사용. CPU 만 쓰고 약 85 초)",
    "PYTHONPATH=src:benchmark $PY report_mesh/src/verify_mesh_canon_0817.py",
    "",
    "# 2) 그림 재생성 (triangle_quality / symmetry_chamfer / overlap_matrix / wireframe_* 등)",
    "PYTHONPATH=src:benchmark $PY report_mesh/src/viz_mesh_reports.py",
    "",
    "# 3) 이 노트북 재생성",
    "PYTHONPATH=src:benchmark $PY report_mesh/src/make_mesh07.py",
    "",
    "# (참고) 출하 게이트와 같은 코드로 빠른 전수 검사만 — 정본 판",
    "PYTHONPATH=src:benchmark $PY src/mesh_check.py",
    "",
    "# (참고) 옛 판을 비트동일하게 재현해서 같은 검사를 걸어 본다",
    "MESH_FIX=none BLADE_LAW=legacy PYTHONPATH=src:benchmark $PY src/mesh_check.py",
    "",
    "# (참고) 골든 봉인 대조 — 형상이 어제와 같은가 · --full 은 지도·매트릭스까지(약 295 초)",
    "PYTHONPATH=src:benchmark $PY benchmark/mesh_certify.py",
    "```",
    "",
    "⚠ **판을 섞지 말 것.** 계산 결과 파일 이름에는 판 꼬리표"
    f"(`{TAG}`)가 붙는다 — 꼬리표가 없으면",
    "옛 판에서 만든 조각을 새 판 계산이 조용히 재사용한다. 실제로 그 사고가 나면 작업이 몇 초 만에",
    "«건너뜀» 으로 끝나고 재계산이 통째로 무효가 된다.",
    "",
    "⭐ **순서를 지켜야 한다.** 생성기는 원장이 레지스트리와 다르면 **일부러 멈춘다** —",
    "리포트가 틀린 기체 수를 조용히 쓰는 것보다 낫다는 규약이다",
    "← 출처: `report_mesh/src/mesh_ledger.py` `ledger_order()`.",
    "",
    "삼각형이 건강함을 확인했으니, 다음 질문은 \"그래서 **실물과 맞는가**\"다.",
    "",
    "**다음 리포트 → mesh08 — 검증 ② (공식 제원 치수 대조·부피/암시밀도·실기체 스캔·PO/SBR 수치 수렴).**",
    "그 편은 정본 판 원장의 §C·§D·§G 와, 아직 옛 판에만 있는 §H·§I 를 **세대를 밝혀 가며** 싣는다.",
))

nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "py312",
      "language": "python", "name": "py312"}, "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 5}
out = os.path.join(RM, "mesh07_verify_geometry.ipynb")
for _i, _c in enumerate(nb["cells"]):
    _c["id"] = f"m07-{_i:02d}"

json.dump(nb, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("wrote", out, len(cells), "cells")
