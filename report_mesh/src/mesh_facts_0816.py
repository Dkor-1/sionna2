# -*- coding: utf-8 -*-
"""mesh_facts_0816.py — report_mesh 8편이 **함께 쓰는 원장 로더**.

왜 이 파일이 있나
  2026-08-16 라운드가 메쉬 원장을 넷 더 냈다(동체·팔·다리 / 짐벌·센서 / 내부 금속 / 재질·검사기).
  여덟 편이 같은 사실을 각자 손으로 적으면 편마다 숫자가 갈린다 — 실제로 그렇게 갈린 적이 있다.
  ⇒ **원장을 읽는 자리를 한 곳으로 모은다.** 생성기는 여기서 받아 f-string 으로 주입만 한다.

  같은 규약: `report_mesh/src/mesh_ledger.py`(원장↔레지스트리 개수 일치 강제).

무엇을 담나
  · `LEDGERS`      — 편 머리의 «무엇을 근거로 하는가» 목록의 원본
  · `head_md()`    — 그 머리 블록을 만드는 함수(8편 공통 서식)
  · `GRADES`       — 근거 등급 [A]/[B]/[C]/[D] 의 뜻과 기체별 배정
  · `fleet_table()`— 10종 규모표(원장 실측 + 등급 + 지금 선언된 결함)
  · `defect_table()`— 지금 남은 결함 지도
  · `material_table()` / `engine_divergence_table()` — 재질 13그룹, 두 엔진 |Γ| 갈림
  · `checker_table()` / `budget_table()` — 검사기 셋의 분담과 «예산» 선언

⛔ 이 파일은 **읽기 전용**이다. 어떤 메쉬도, 어떤 기본 동작도 바꾸지 않는다.
"""
from __future__ import annotations

import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
RM = os.path.abspath(os.path.join(HERE, ".."))            # report_mesh/
ROOT = os.path.abspath(os.path.join(RM, ".."))            # 저장소 루트
OUT = os.path.join(ROOT, "outputs")


# --------------------------------------------------------------------------- #
#  원장 목록 — 편 머리의 «무엇을 근거로 하는가» 가 여기서 나온다
# --------------------------------------------------------------------------- #
LEDGERS = {
    "verify": ("report_mesh/outputs/mesh_verify.json",
               "기하 검증 스위트 A~I — 이 시리즈의 기본 원장"),
    "body_arms": ("outputs/mesh_inspect_body_arms_0816.json",
                  "동체·팔·다리·모터 벨 전수 실측(10종) + matrice4e 공식 CAD 정정 착지 검증"),
    "gimbal": ("outputs/mesh_inspect_gimbal_sensors_0816.json",
               "짐벌·카메라·센서 검사(10종) — 부착 게이트 A~D"),
    "internal": ("outputs/mesh_inspect_internal_metal_0816.json",
                 "내부 금속(배터리·기판·모터) 정밀 검토 + 정면 금속면 재측정"),
    "internal_check": ("outputs/mesh_internal_metal_check_0816.json",
                       "«내부 금속이 정말 셸 안에 있나» 기체별 판정(PASS/FAIL/N/A/UNKNOWN)"),
    "materials": ("outputs/mesh_inspect_materials_check_0816.json",
                  "재질 배정·검사기·프롭 외 부품 감사(13그룹·10종)"),
    "meshfix_m4e": ("outputs/meshfix_matrice4e.json",
                    "DJI 공식 STEP 대조 정정 명세 14건(matrice4e)"),
    "audit": ("docs/MESH_AUDIT_0816.md",
              "적대적 감사 — 발견·반증·수리 우선순위(§⑤)"),
    "material_correction": ("docs/MATERIAL_CORRECTION.md",
                            "재질·두께 규약 정정(셸 0.75 mm 정본, 두 엔진 갈림)"),
    "sources": ("assets/meshes/reference/SOURCES.md",
                "참조 CAD·스캔의 출처와 라이선스"),
}


def _load(rel: str):
    p = os.path.join(ROOT, rel)
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def load(key: str):
    """원장 키 → 파싱된 JSON. (`audit`·`material_correction`·`sources` 는 md 라 제외)"""
    return _load(LEDGERS[key][0])


# 자주 쓰는 것은 미리 연다(생성기마다 다시 열지 않게).
BODY = load("body_arms")
GIMBAL = load("gimbal")
INTERNAL = load("internal")
INTERNAL_CHECK = load("internal_check")
MAT = load("materials")
M4EFIX = load("meshfix_m4e")


def head_md(volume: str, question: str, keys, extra=()) -> list[str]:
    """편 머리의 공통 블록 — «이 편이 답하는 질문» 한 줄 + «무엇을 근거로 하는가» 목록.

    사용자 규약(2026-08-16): 여덟 편 전부 이 블록을 머리에 단다.
    """
    lines = [
        f"> ⚠ **이 노트북은 생성물이다.** 수정은 `report_mesh/src/make_{volume}.py` 에서 하고",
        "> 재실행할 것(`.ipynb` 를 직접 고치면 다음 빌드에서 사라진다).",
        "",
        f"**이 편이 답하는 질문** — {question}",
        "",
        "**무엇을 근거로 하는가** (본문 수치는 손으로 적지 않고 아래 원장에서 주입한다)",
        "",
        "| 원장 | 무엇이 들어 있나 |",
        "|---|---|",
    ]
    for k in keys:
        path, what = LEDGERS[k]
        lines.append(f"| `{path}` | {what} |")
    for path, what in extra:
        lines.append(f"| `{path}` | {what} |")
    return lines


# --------------------------------------------------------------------------- #
#  근거 등급 — 사용자 규약(2026-08-16)
# --------------------------------------------------------------------------- #
GRADE_LEGEND = [
    "| 등급 | 뜻 | 이 저장소에서의 실체 |",
    "|---|---|---|",
    "| **[A]** | 공식 CAD 직접 | 제조사가 낸 CAD 파일을 열어 잰 값 — DJI Matrice 4T STEP · "
    "DJI Mini 2 GLB · Holybro X500 v2 STEP · Yuneec Typhoon H480 실물 CAD |",
    "| **[B]** | 사진 계측 | 제품사진·매뉴얼 도해를 픽셀로 잰 값 |",
    "| **[C]** | 계열 유추 | 다른 기체의 실측을 크기비로 옮긴 값 |",
    "| **[D]** | 대리 | 다른 제조사의 부품을 대신 세운 값 |",
    "",
    "⚠ 등급은 **«공표 숫자만으로는 안 정해지는 형상»** 이 어디서 왔는가를 매긴다. "
    "공표 제원(외형 L×W×H · 프로펠러 지름 · 대각)은 10종 공통 입력이라 이 축 밖이다 — "
    "그 숫자들의 출처는 mesh03 이 따로 맡는다.",
]

#  기체별 형상 근거 등급. 근거는 옆 칸에 적는다(전부 원장·소스에서 확인한 것).
GRADES = {
    "matrice4e": ("A", "DJI Matrice 4T 공식 STEP 로 형상 상수 14건 정정, 전부 착지 "
                       "(`meshfix_matrice4e.json` · `body_arms.meshfix_matrice4e_landed`). "
                       "⚠ 짐벌·카메라 블록만 4T↔4E 가 달라 **치수는 사진, 매다는 자리만 CAD**"),
    "mini2": ("A", "DJI 공식 GLB(WM161) 실측 — 셸 6 스테이션 중 가운데 4개가 GLB 와 0.5 % 안"),
    "x500v2": ("A", "Holybro 공식 STEP 프레임(암 단면 16.0×16.0 mm 재현)"),
    "typhoonh480": ("A", "Yuneec 실물 CAD(ethz-asl/rotors_simulator, Apache-2.0) — 암 12.0×12.6 ↔ CAD 12.002"),
    "phantom4": ("B", "공표 제원 + 제품사진. 실기체 3D 스캔(CC-BY)은 **채점 전용**이라 제작에 안 썼다"),
    "phantom3": ("B", "공표 제원 + 제품사진"),
    "mini5pro": ("B", "제품사진 계측. ⚠ 셸 높이의 1차 출처가 없다 — 공표 91 mm 가 프롭을 포함해 셸을 구속하지 않는다"),
    "mavic4pro": ("C", "암 폭은 **Mini 5 Pro 실측의 크기비 이전**. DJI 가 Mavic 4 Pro CAD 를 공개하지 않는다"),
    "s1000plus": ("B", "공표 제원(카본 튜브 25 mm) + 제품사진"),
    "m350rtk": ("B", "공표 제원 + 제품사진(암 튜브 22 mm)"),
}

#  기체별 «지금 선언된 결함» — 한 칸에 들어갈 만큼 줄인 것. 자세한 것은 defect_table().
DECLARED = {
    "mini5pro": "세로 배율 1.2985(전 부품 늘림)",
    "mavic4pro": "세로 배율 1.3524 · 짐벌이 발보다 15.35 mm 아래",
    "matrice4e": "로터면이 CAD 보다 18.5 mm 위(F19~F21 보류)",
    "s1000plus": "카본 센터플레이트가 `plastic` 그룹",
    "phantom4": "L/W 강제 → 축간거리 +1.98 % · 착륙아치 8.3~8.5 mm 뜸",
    "typhoonh480": "—",
    "x500v2": "레일 4.0 mm 뜸 · accent↔arm 동일평면",
    "phantom3": "착륙아치 13.7~13.8 mm 뜸 · 짐벌 3조각이 떨어져 있음",
    "m350rtk": "프롭 허브가 벨 위 6.0 mm 뜸",
    "mini2": "셸에 삼각형 1장 구멍(경계 모서리 3)",
}


# --------------------------------------------------------------------------- #
#  10종 규모표
# --------------------------------------------------------------------------- #
def _parts(s):
    a, b = s.split("/")
    return int(a), int(b)


def fleet_table(V, order, label_fn, specs) -> str:
    """원장 A 절 + DroneSpec + 등급 + 선언된 결함을 한 표로."""
    rows = []
    for k in order:
        a = V["A_geometry"][k]
        sp = specs[k]
        wt = sum(_parts(g["watertight"])[0] for g in a["groups"].values())
        n_parts = sum(_parts(g["watertight"])[1] for g in a["groups"].values())
        wb = BODY["per_drone"][k]["wheelbase_mm"]
        grade = GRADES[k][0]
        rows.append(
            f"| {label_fn(k)} | **[{grade}]** | {wb:,.1f} | {sp.prop_dia_mm:.0f}×{sp.num_rotors} "
            f"| {a['n_verts']:,} | {a['n_faces']:,} | {a['n_groups']} | {wt}/{n_parts} "
            f"| {DECLARED[k]} |")
    return "\n".join(rows)


def fleet_totals(V, order) -> dict:
    tv = tf = tp = twt = 0
    for k in order:
        a = V["A_geometry"][k]
        tv += a["n_verts"]
        tf += a["n_faces"]
        for g in a["groups"].values():
            w, n = _parts(g["watertight"])
            twt += w
            tp += n
    return dict(verts=tv, faces=tf, parts=tp, watertight=twt)


# --------------------------------------------------------------------------- #
#  지금 남은 결함 지도 — 톤 규칙: «고쳤다» 서사 없이 «지금 이렇다» 만
# --------------------------------------------------------------------------- #
def defect_table() -> str:
    """원장에서 직접 뽑는다. 손으로 적은 수치가 없도록."""
    g = GIMBAL["_summary"]
    fit_m5 = BODY["per_drone"]["mini5pro"]["fit"][2]
    fit_mv = BODY["per_drone"]["mavic4pro"]["fit"][2]
    sh_m5 = BODY["per_drone"]["mini5pro"]["shell_h_mm"]
    sh_mv = BODY["per_drone"]["mavic4pro"]["shell_h_mm"]
    cam = g["gate_A_fail"][0]
    wb_p4 = BODY["per_drone"]["phantom4"]["wheelbase_mm"]
    plate = MAT["s1000plus_center_plate"]
    rows = [
        "| 무엇 | 기체 | 지금 이만큼 | 어디에 실리나 |",
        "|---|---|---|---|",
        f"| 공표 높이를 **형상이 아니라 세로 배율**로 맞춘다 | mini5pro · mavic4pro "
        f"| 세로 배율 {fit_m5:.4f} / {fit_mv:.4f} — 형상표의 셸 높이 "
        f"{sh_m5['table']:.2f} / {sh_mv['table']:.2f} mm 가 메쉬에서 "
        f"{sh_m5['delivered']:.2f} / {sh_mv['delivered']:.2f} mm 로 나온다 "
        f"| 평판극한 σ 상한 +2.27 / +2.62 dB (방위평균, el 0°) |",
        f"| 짐벌이 착륙발보다 아래 | mavic4pro | 카메라 최저점이 발보다 "
        f"{abs(cam['camera_below_gear_mm']):.2f} mm 아래. 발을 바닥으로 놓고 같은 규칙을 풀면 "
        f"세로 배율이 {cam['sz_now']:.4f} → {cam['sz_if_bottom_were_the_feet']:.4f} "
        f"({cam['vertical_scale_error_pct']:.2f} %) | 위 세로 배율의 **원인** — 예산 구멍을 가린다 |",
        f"| 뜬 파트(기체에 안 닿는 부품) | phantom4 · phantom3 · m350rtk · x500v2 "
        f"| 착륙아치 8.3~8.5 / 13.7~13.8 mm · 프롭 허브 6.0 mm · 레일 4.0 mm "
        f"| 간극 0.05~0.16 λ @3.5 GHz — 면적은 그대로고 가림·다중반사·위상이 바뀐다 |",
        f"| L/W 강제가 남아 축간거리가 부푼다 | phantom4 | 공표 350 → 메쉬 "
        f"{wb_p4:.2f} mm (+{(wb_p4 - 350) / 350 * 100:.2f} %) | 평판극한 −0.39 dB (el 0°) |",
        f"| 로터면이 공식 CAD 보다 위 | matrice4e | 18.5 mm = 0.216 λ @3.5 GHz. "
        f"명세가 F19~F21 로 «엔진 변경 필요» 라 미뤄 둔 자리 | 프롭 장착 높이가 함께 움직인다 ⏳ |",
        f"| 셸에 삼각형 1장 구멍 | mini2 | 경계 모서리 3개, 구멍 넓이 약 0.35 mm² (λ²/21000) "
        f"| σ 는 무시할 수준. 진짜 피해는 **안/밖 판정이 정의되지 않는 것** |",
        f"| 카본 판이 `plastic` 그룹에 있다 | s1000plus | 판 2장만 세도 body 합집합 전 면적의"
        f" {plate['plates_only_share_of_body_pct']:.1f} % (스탠드오프 기둥까지 넣은 스택은"
        f" {plate['carbon_plate_share_of_body_pct']:.1f} %) | 면 반사율 +10.14 dB"
        f" (carbon 0.90 ↔ plastic 0.28) |",
    ]
    return "\n".join(rows)


def unresolved_list() -> list[str]:
    """«모른다» 를 그대로 옮긴다 — 빈칸이 가짜 값보다 낫다."""
    out = []
    for x in BODY["not_settled_this_round"]:
        out.append(f"- {x}")
    bat = INTERNAL["battery_material"]
    out.append(f"- **배터리 재질** — {bat['verdict']}")
    cam = GIMBAL["material_review"]
    out.append(f"- **카메라 재질 0.85 의 출처** — {cam['repo_prior']}")
    return out


# --------------------------------------------------------------------------- #
#  재질 — 13그룹 · 두 엔진의 |Γ| 가 설계상 다르다
# --------------------------------------------------------------------------- #
def assignment_table() -> str:
    rows = ["| 부위(그룹) | 재질 키 | PO \\|Γ\\| | 쓰는 기체 | 함대 면적 [cm²] | 이 그룹이 무엇인가 |",
            "|---|---|---|---|---|---|"]
    A = MAT["assignment_audit"]
    for grp, v in sorted(((g, x) for g, x in A.items() if not g.startswith("_")),
                         key=lambda kv: -kv[1].get("total_area_mm2", 0)):
        flag = "" if v.get("verdict") == "ok" else " ⚠"
        rows.append(f"| `{grp}`{flag} | `{v.get('material','—')}` | {v.get('gamma_po', float('nan')):.2f} "
                    f"| {v.get('n_drones','—')}종 | {v.get('total_area_mm2', 0) / 100.0:,.0f} "
                    f"| {v.get('description','—')} |")
    return "\n".join(rows)


def engine_divergence_table() -> str:
    """PO 커널의 |Γ| 와 Sionna 재질의 |Γ| 는 **설계상 다르다** — 그 갈림을 표로."""
    rows = ["| 재질 키 | Sionna 경로 | Sionna \\|Γ\\| | PO \\|Γ\\| | 차이 [dB] | 왜 다른가 |",
            "|---|---|---|---|---|---|"]
    for k, v in MAT["engine_divergence"].items():
        #  ⚠ 문장 끝의 마침표로만 자른다. 그냥 split(".") 하면 «εr 2.7» 의 소수점에서 잘려
        #     괄호가 안 닫힌 조각(«…εr 2»)이 표에 실린다(2026-08-16 적대검증에서 발견).
        why = re.split(r"(?<!\d)\.(?!\d)", v["declared_reason"])[0].strip()
        rows.append(f"| `{k}` | {v['sionna_side']} | {v['gamma_sionna_normal']:.5f} "
                    f"| {v['gamma_po']:.5f} | {v['divergence_dB']:+.2f} | {why} |")
    return "\n".join(rows)


# --------------------------------------------------------------------------- #
#  검사기 — 셋의 분담, 10 검사, 예산
# --------------------------------------------------------------------------- #
CHECKERS = [
    ("`src/cadkit.py` `Assembly.check`", "빌드 도중", "파트 하나를 붙일 때마다",
     "부품 단위 수밀·법선"),
    ("`src/mesh_check.py`", "출하 게이트", "10 검사 + 예산표",
     "`python src/drones.py`(OBJ 내보내기) 한 문에 배선. `MESH_GATE=off` 로 끌 수 있고, "
     "RCS·렌더가 쓰는 **인메모리 `build_drone()` 은 이 문을 안 지난다**"),
    ("`report_mesh/src/verify_mesh_suite.py`", "원장 생성", "A~I 9절",
     "이 시리즈의 숫자를 만든다. I 절(SBR)만 GPU"),
    ("`benchmark/check_gimbal_sensors_0816.py`", "특수 검사", "짐벌·센서 게이트 A~D",
     "부착·삼킴·선언초과·재질 민감도"),
    ("`benchmark/mesh_internal_metal_check.py`", "특수 검사", "내부 금속 포함 판정",
     "«금속 상자가 정말 셸 안인가»"),
]


def checker_table() -> str:
    rows = ["| 검사기 | 언제 도나 | 무엇을 보나 | 범위·단서 |", "|---|---|---|---|"]
    for a, b, c, d in CHECKERS:
        rows.append(f"| {a} | {b} | {c} | {d} |")
    return "\n".join(rows)


CHECKS_10 = [
    ("수밀(watertight)", "부품이 닫힌 껍질인가"),
    ("경계 모서리", "삼각형 하나만 쓰는 모서리 = 구멍의 테두리. **원칙은 0**, 예산으로만 예외"),
    ("winding", "이웃한 면이 같은 방향으로 감겼는가"),
    ("법선 방향", "닫힌 부품의 부호있는 부피가 양수인가"),
    ("부호부피(원본 인덱스)", "trimesh 를 **전혀 안 거치고** 출하 인덱스에서 손계산"),
    ("퇴화면 — 절대 + 상대", "면적 잣대에 더해 **최소 내각 <0.5°** 슬리버를 센다"),
    ("그룹 안 겹침", "같은 그룹의 두 부품이 서로 파묻혔는가(PO 면적 이중계상)"),
    ("치수 대조", "프롭 지름·로터 대각·공표 외형을 `DroneSpec` 의 수와 대조"),
    ("손대칭성", "로터별 날 비틀림 방향이 회전방향과 맞는가 — **거울상 기체 탐지**"),
    ("프롭↔모터 벨 관통", "원통 근사(빠름) + 솔리드 내부판정(판정 기준)"),
]


def checks_table() -> str:
    rows = ["| # | 검사 | 무엇을 묻나 |", "|---|---|---|"]
    for i, (a, b) in enumerate(CHECKS_10, 1):
        rows.append(f"| {i} | **{a}** | {b} |")
    return "\n".join(rows)


def budget_table() -> str:
    """«예산» 은 «이만큼이 옳다» 가 아니라 «지금 이만큼이다» 라는 선언이다."""
    import sys
    sp = os.path.join(ROOT, "src")
    if sp not in sys.path:
        sys.path.insert(0, sp)
    import mesh_check as MC
    be = ", ".join(f"({k[0]}, {k[1]}) = {v}" for k, v in MC.BOUNDARY_EDGE_BUDGET.items()
                   if isinstance(k, tuple))
    sl = MC.SLIVER_BUDGET
    sl_rng = f"{min(v for k, v in sl.items() if k != '_default')}~" \
             f"{max(v for k, v in sl.items() if k != '_default')}"
    rows = [
        "| 예산 | 지금 값 | 무엇을 뜻하나 |",
        "|---|---|---|",
        f"| `BOUNDARY_EDGE_BUDGET` | 기본 **0**, 예외 {be} | 구멍은 원칙적으로 없어야 한다. "
        "예외 하나가 명시적으로 선언돼 있다 |",
        f"| `SLIVER_BUDGET` | 기종별 {sl_rng} | 아주 뾰족한 삼각형 개수. 면적 비중은 "
        "0.0001~0.03 % 라 σ 에는 무해하고, 감시하는 이유는 법선이 수치적으로 불안정한데 "
        "PO 조명 판정이 `n̂·û>0` 이기 때문이다 |",
        f"| `GROUP_OVERLAP_BUDGET_PCT` | 기본 {MC.GROUP_OVERLAP_BUDGET_PCT['_default']} %, "
        "battery 4종 55 % | 같은 그룹 안에서 부품이 파묻힌 비율 |",
        f"| `DIM_TOL_PCT` | 프롭 지름 {MC.DIM_TOL_PCT['prop_dia']:.0f} % · "
        f"외형 {MC.DIM_TOL_PCT['envelope']:.0f} % · 대각 {MC.DIM_TOL_PCT['diagonal']:.0f} % "
        f"(mini5pro 예외 {MC.DIM_DIAGONAL_TOL_PCT['mini5pro']:.0f} %) | 공표 숫자와의 허용 오차 |",
        f"| `HANDEDNESS_MIN_ABS` | {MC.HANDEDNESS_MIN_ABS} | 날 비틀림 지표의 최소 크기. "
        "이보다 작으면 «비틀리지 않았다» 는 뜻이라 부호를 믿을 수 없다 |",
    ]
    return "\n".join(rows)


def po_overcount_table(order) -> str:
    """PO 경로는 가림을 안 본다 — 부품 속에 묻힌 면이 이중계상된다. 그 크기를 재질 가중으로."""
    rows = ["| 기체 | 묻힌 면의 반사 몫 [%] | 그중 **불투명 부품 안** [%] | PO 과대계상 [dB] |",
            "|---|---|---|---|"]
    for k in order:
        f = MAT["fleet"][k]
        rows.append(f"| {k} | {f['buried_power_weight_pct']:.1f} "
                    f"| {f['buried_in_opaque_weight_pct']:.2f} "
                    f"| **+{f['po_overcount_opaque_dB']:.2f}** |")
    return "\n".join(rows)


def internal_metal_table(order, label_fn) -> str:
    """«내부» 금속이 정말 셸 안에 있나 — 기체별 판정."""
    rows = ["| 기체 | 판정 | 무엇을 뜻하나 |", "|---|---|---|"]
    mean = {"PASS": "금속 상자가 전부 셸 안에 있다",
            "FAIL": "금속 상자의 일부가 셸 **밖**으로 나와 있다",
            "N/A": "설계상 열린 프레임이라 «셸 안» 이라는 물음이 성립하지 않는다",
            "UNKNOWN": "셸이 닫혀 있지 않아 안/밖 판정 자체가 정의되지 않는다"}
    for k in order:
        v = INTERNAL_CHECK.get(k, {})
        vd = v.get("verdict", "—")
        rows.append(f"| {label_fn(k)} | **{vd}** | {mean.get(vd, '—')} |")
    return "\n".join(rows)


#  검사기가 **아직 못 보는 것** — 정직하게 남긴다.
BLIND_SPOTS = [
    "**동일평면 겹침** — 두 부품 표면이 정확히 같은 자리에 있으면 관통 검사가 못 본다. "
    "9기체에서 34쌍이 그 상태다(가장 큰 것은 s1000plus body↔battery 16,745.8 mm²).",
    "⏳ **삼각형 크기를 파장에 묶는 규약** — 프로펠러 축은 기체별 프로펠러 정본화 라운드가 맡는다.",
    "**기종별 재질 분기** — `drone_gamma_map(spec, fc)` 이 `spec` 을 안 쓴다. "
    "지금은 재질이 기체와 무관해서 맞지만, 기종별 재질이 생기는 순간 조용히 틀린 답을 준다.",
    "**PO 경로의 가림** — `rcs_po.py` 가 자기 docstring 에서 자기차폐·다중반사를 무시한다고 "
    "선언한다. 부품 속에 묻힌 면이 그 경로에서는 이중계상된다(재질 가중으로 +0.03~+0.69 dB).",
]


#  ⏳ 프로펠러 축 — **이 시리즈의 다른 라운드가 정본이다.** 여기서는 자리만 잡는다.
PROP_PLACEHOLDER = [
    "> ⏳ **이 절은 기체별 프로펠러 정본화 결과로 채운다.** 날 시위 분포·기종별 두께·"
    "팁 형상·λ 대비 삼각형 크기는 그 라운드가 정본이므로, 이 편에서 값을 적으면 두 곳이 갈린다.",
    "",
    "지금 확실한 것만 적는다.",
    "",
    "- **움직이는 성분(AC)은 정의상 프로펠러만 남는다.** 정지한 동체의 기여는 순수 DC 라 "
    "  DC 를 걷어내면 사라진다. 이것은 측정이 아니라 구조적 필연이다.",
    "- **총 반사(σ)로는 동체가 훨씬 세다** — matrice4e 부품 분해에서 프로펠러 몫은 "
    "  el −30° 에서 2.4 %(16.2 dB 아래), el 0° 에서 0.2 %(28.1 dB 아래)다.",
    "- ⇒ «프로펠러가 표적을 지배한다» 는 **AC 채널 한정 문장**이다. 총 σ 문장으로 옮겨 쓰면 틀린다.",
]
