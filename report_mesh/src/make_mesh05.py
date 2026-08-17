# -*- coding: utf-8 -*-
"""make_mesh05.py — mesh05 ipynb 생성기. ⚠ 이 파일이 소스다.

mesh05 — "프로펠러 — 판때기가 아니라 날개다"
배정 그림: airfoil_profile.png (이 리포트 전용)
수치는 전부 outputs/mesh_verify.json + src/drones.py DroneSpec 에서 읽어 f-string 주입.
"""
import json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
RM = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(RM, ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

V = json.load(open(os.path.join(RM, "outputs", "mesh_verify.json"), encoding="utf-8"))
from drones import DRONES, drone_label  # noqa: E402  (스펙 수치의 유일한 진리원)
import inspect  # noqa: E402
import drone_cad as _DC  # noqa: E402  (블레이드 상수는 **코드에서 읽는다** — 손으로 적지 않는다)
def _wrap_sig(fn, head, width=96):
    """시그니처를 실제 소스에서 읽어 읽기 좋은 폭으로 접는다(손으로 옮겨 적지 않는다)."""
    parts = [f"{n}={p.default!r}" if p.default is not inspect.Parameter.empty else n
             for n, p in inspect.signature(fn).parameters.items()]
    lines, cur = [], head + "("
    pad = " " * len(cur)
    for i, t in enumerate(parts):
        piece = t + ("," if i < len(parts) - 1 else "):")
        if len(cur) + len(piece) + 1 > width:
            lines.append(cur.rstrip())
            cur = pad
        cur += piece + " "
    lines.append(cur.rstrip())
    return lines


_BLADE_SIG_LINES = _wrap_sig(_DC._blade, "def _blade")   # 실제 시그니처(기본값 포함)
_BLADE_DEF = {k: v.default for k, v in
              inspect.signature(_DC._blade).parameters.items()}
sys.path.insert(0, HERE)
import mesh_facts_0816 as MF  # noqa: E402  (2026-08-16 원장 공용 로더)

from mesh_ledger import ledger_order   # noqa: E402  (원장↔레지스트리 일치 강제)
ORDER = ledger_order(V)                     # = DRONES 레지스트리 전수
FC = float(V["meta"]["fc_ghz"])             # 3.5 GHz (검증 기준 주파수)
LAM_MM = 299.792458 / FC                    # λ[mm] = c/f

# --------------------------------------------------------- 정본 스위치(코드에서 읽는다)
import geom as _GEOM                         # noqa: E402  (정본 수리·날 법칙의 유일한 자리)
CANON_FIX = tuple(sorted(_GEOM.mesh_fix_set()))          # 지금 켜져 있는 메쉬 수리
CANON_LAW = _GEOM.blade_law_canon()                      # 지금 쓰는 날 법칙
CANON_FIX_S = ",".join(CANON_FIX) if CANON_FIX else "none"
#  산출물 파일명 꼬리표 — 규약은 benchmark/elevation_sweep_md.py 와 같다(손으로 적지 않는다).
FILE_TAG = ("" if not CANON_FIX else "_mfix" + "".join(CANON_FIX)) \
    + ("" if CANON_LAW == "legacy" else "_bl" + CANON_LAW.replace("_", ""))

# --------------------------------------------------------- 날 법칙 원장(2026-08-16)
LAWJ = json.load(open(os.path.join(ROOT, "outputs", "prop_law_by_airframe_0816.json"),
                      encoding="utf-8"))
VERJ = json.load(open(os.path.join(ROOT, "outputs", "prop_law_verify_0816.json"),
                      encoding="utf-8"))
LAW = LAWJ["C_law_by_airframe"]                          # 기체별 법칙(모델·등급·곡선)
CHG = {r["aircraft"]: r for r in LAWJ["D_change_table"]["rows"]}   # 옛 판 대비 변화
SPREAD = LAWJ["D_change_table"]["spread_ko"]
GAPS = LAWJ["F_gaps"]
VER = VERJ["V2_V4_by_airframe"]                          # 지어진 메쉬로 되잰 검증
V3S = VERJ["V3_summary"]
V5 = VERJ["V5_realization_deficit"]

# --------------------------------------------------------- 정본 판 형상 원장 (2026-08-17)
#  ⭐ `mesh_verify.json` 은 2026-08-16 13:15 세대(수리 없음·legacy 날)라 형상 수치가 한 세대
#     낡았다. 정본 판에서 다시 잰 원장이 따로 있고, 이 편의 형상 수치는 **전부 거기서** 온다.
#     ⚠ 원장의 스위치가 지금 스위치와 다르면 **여기서 죽는다** — 다른 판의 수를 싣지 않으려고.
CANONV = json.load(open(os.path.join(RM, "outputs", "mesh_verify_canon_0817.json"),
                        encoding="utf-8"))
_CM = CANONV["_meta"]
assert tuple(sorted(_CM["mesh_fix"])) == CANON_FIX and _CM["blade_law"] == CANON_LAW, (
    f"정본 원장({_CM['mesh_fix']}·{_CM['blade_law']})이 지금 스위치"
    f"({CANON_FIX}·{CANON_LAW})와 다르다 — report_mesh/src/verify_mesh_canon_0817.py 를 "
    f"다시 돌릴 것")
LAM_HI_MM = float(_CM["lam_hi_mm"])          # 최고 대역 파장(삼각형 크기 판정의 보수적 기준)
CAN = {}
for k in ORDER:
    _a = CANONV["A_geometry"][k]
    _pt = CANONV["prop_triangles"][k]
    _sy = CANONV["B_symmetry"][k]
    CAN[k] = dict(
        verts=_a["n_verts"], faces=_a["n_faces"],
        prop_faces=_pt["n_faces"], prop_pct=_pt["share_pct"],
        prop_edge_p95=_pt["edge_mm"]["p95"], prop_edge_max=_pt["edge_mm"]["max"],
        prop_edge_p95_lam=_pt["edge_vs_lam"]["p95_over_lam"],
        prop_edge_max_lam=_pt["edge_vs_lam"]["max_over_lam"],
        prop_dia_err_pct=CANONV["C_dims"][k]["checks"]["prop_dia"]["err_pct"],
        sym_full_p50=_sy["full"]["chamfer_mm"]["p50"],
        sym_full_p95=_sy["full"]["chamfer_mm"]["p95"],
        sym_frame_p50=_sy["frame_only"]["chamfer_mm"]["p50"],
        sym_frame_p95=_sy["frame_only"]["chamfer_mm"]["p95"],
    )

# ---------------------------------------------------------------- 파생 수치
# (전부 스펙(DroneSpec)·JSON 에서 계산 — 손으로 적은 숫자 없음)
ROWS = {}
for k in ORDER:
    s = DRONES[k]
    R = s.prop_dia_mm / 2000.0                       # 반경[m]
    P = (s.prop_pitch_in or 0.0) * 0.0254            # 기하피치[m]
    th = lambda r: math.degrees(math.atan(P / (2 * math.pi * r)))
    n_rev = s.hover_rpm / 60.0                       # 회전수[rev/s]
    vtip = 2 * math.pi * n_rev * R                   # 팁속도[m/s]
    ROWS[k] = dict(
        name=s.name, dia=s.prop_dia_mm, blades=s.prop_blades, rotors=s.num_rotors,
        P_in=s.prop_pitch_in, P_mm=P * 1000.0,
        R_mm=R * 1000.0,
        th_hub=th(0.15 * R), th_tip=th(R),
        rpm=s.hover_rpm, flash=s.prop_blades * n_rev,
        vtip=vtip, ftip_khz=2 * vtip / (LAM_MM / 1000.0) / 1000.0,
        gamma_prop=V["E_materials"][k]["gamma_map"]["prop"],
        #  형상 수치(면 수·프롭 몫·대칭·프롭 지름)는 위 CAN — **정본 판 실측**이다.
        prop_faces=CAN[k]["prop_faces"],
        all_faces=CAN[k]["faces"],
        sym_full_p95=CAN[k]["sym_full_p95"],
        sym_full_p50=CAN[k]["sym_full_p50"],
        sym_frame_p95=CAN[k]["sym_frame_p95"],
        sym_frame_p50=CAN[k]["sym_frame_p50"],
    )

MAV = ROWS["mavic4pro"]
R_MAV = MAV["R_mm"] / 1000.0                         # 0.1335 m
PROP_ERR = CAN["mavic4pro"]["prop_dia_err_pct"]      # 프롭 지름 오차 [%] (정본 판 실측)
PROP_ERR_MAX = max(abs(CAN[k]["prop_dia_err_pct"]) for k in ORDER)
MAV_FACE_PCT = 100.0 * MAV["prop_faces"] / MAV["all_faces"]
PROP_PCT_MIN = min(CAN[k]["prop_pct"] for k in ORDER)
PROP_PCT_MAX = max(CAN[k]["prop_pct"] for k in ORDER)
PROP_PCT_MIN_WHO = min(ORDER, key=lambda k: CAN[k]["prop_pct"])
PROP_PCT_MAX_WHO = max(ORDER, key=lambda k: CAN[k]["prop_pct"])
G_MOTOR = V["E_materials"]["mavic4pro"]["gamma_map"]["motor"]
G_BODY = V["E_materials"]["mavic4pro"]["gamma_map"]["body"]

# 마이크로도플러 표 (모델별)
mdop_tbl = ["| 기종 | 프롭 Ø×날수 | 피치 P | 호버 rpm | 플래시 [Hz/로터] | 팁속도 [m/s] | ±f_tip @3.5 GHz |",
            "|---|---|---|---|---|---|---|"]
for k in ORDER:
    r = ROWS[k]
    mdop_tbl.append(
        f"| {r['name']} | {r['dia']:g} mm × {r['blades']}날 | {r['P_in']:g}″ = {r['P_mm']:.0f} mm "
        f"| {r['rpm']:g} | {r['flash']:.0f} | {r['vtip']:.1f} | ±{r['ftip_khz']:.2f} kHz |")
MDOP = "\n".join(mdop_tbl)

# 피치각 표 (모델별)
pitch_tbl = ["| 기종 | 피치 P (스펙) | 반경 R | θ(0.15R) 허브 쪽 | θ(R) 팁 |",
             "|---|---|---|---|---|"]
for k in ORDER:
    r = ROWS[k]
    pitch_tbl.append(
        f"| {r['name']} | {r['P_in']:g}″ = {r['P_mm']:.1f} mm | {r['R_mm']:.1f} mm "
        f"| {r['th_hub']:.1f}° | {r['th_tip']:.1f}° |")
PITCH = "\n".join(pitch_tbl)

# 대칭 검사 표 (full vs frame_only)
sym_tbl = ["| 기종 | full p50 / p95 [mm] | frame_only p50 / p95 [mm] | p95 배율 |",
           "|---|---|---|---|"]
for k in ORDER:
    r = ROWS[k]
    sym_tbl.append(
        f"| {r['name']} | {r['sym_full_p50']:.2f} / **{r['sym_full_p95']:.1f}** "
        f"| {r['sym_frame_p50']:.2f} / **{r['sym_frame_p95']:.2f}** "
        f"| ×{r['sym_full_p95'] / r['sym_frame_p95']:.0f} |")
SYM = "\n".join(sym_tbl)

# 프롭이 메쉬에서 차지하는 몫 + 프롭 삼각형이 파장 대비 얼마나 잔가 (정본 판 원장)
share_tbl = ["| 기종 | 로터×날 | 메쉬 전체 [삼각형] | 프롭 그룹 [삼각형] | 프롭 몫 [%] "
             "| 프롭 삼각형 모서리 p95 [mm] | p95/λ_hi | 최대/λ_hi |",
             "|---|---|---|---|---|---|---|---|"]
for k in ORDER:
    r, c = ROWS[k], CAN[k]
    share_tbl.append(
        f"| {r['name']} | {r['rotors']}×{r['blades']} | {c['faces']:,} | {c['prop_faces']:,} "
        f"| **{c['prop_pct']:.1f}** | {c['prop_edge_p95']:.1f} | {c['prop_edge_p95_lam']:.3f} "
        f"| {c['prop_edge_max_lam']:.3f} |")
SHARE = "\n".join(share_tbl)
EDGE_LAM_MAX = max(CAN[k]["prop_edge_max_lam"] for k in ORDER)
EDGE_LAM_MAX_WHO = max(ORDER, key=lambda k: CAN[k]["prop_edge_max_lam"])

# 기체별 날 법칙 (정본) — 모델명·등급·c_max/R·정점·불확실도·옛 판 대비 면적 변화
law_tbl = ["| 기체 | 순정 프로펠러 | 등급 | c_max/R | 시위 정점 r/R | 불확실도 "
           "| 날 1장 설계면적 Δ | (참고) 면적비 dB |",
           "|---|---|---|---|---|---|---|---|"]
for k in ORDER:
    L, C = LAW[k], CHG[k]
    proxy = f" ⛔대리({L['proxy_of']})" if L.get("proxy_of") else ""
    law_tbl.append(
        f"| {drone_label(k)} | {L['prop']} | **[{L['grade']}]**{proxy} "
        f"| {L['c_max_over_R']:.4f} | {L['peak_r_over_R']:.2f} | ±{L['uncertainty_pct']:g} % "
        f"| {C['blade_area_pct']:+.1f} % | {C['db_blade_area']:+.2f} |")
LAWTBL = "\n".join(law_tbl)

# 같은 표의 근거·단서 — «빈칸이 가짜 값보다 낫다» 규약상 단서를 통째로 옮긴다
src_rows = ["| 기체 | 등급 | 1차 근거 | 이 칸의 단서 |", "|---|---|---|---|"]
for k in ORDER:
    L = LAW[k]
    src_rows.append(f"| {drone_label(k)} | **[{L['grade']}]** | {L['source']} "
                    f"| {L.get('caveat_ko', '—')} |")
LAWSRC = "\n".join(src_rows)

# 지어진 메쉬로 되잰 검증(V2·V4)
ver_tbl = ["| 기체 | 지어진 c_max/R | 법칙 c_max/R | 실현비 | 시위 정점 r/R (지어진 ↔ 법칙) "
           "| 형상편차 주대역 [%] | 판정 |", "|---|---|---|---|---|---|---|"]
for k in ORDER:
    x = VER[k]
    ver_tbl.append(
        f"| {drone_label(k)} | {x['c_max_over_R_built_new']:.4f} "
        f"| {x['c_max_over_R_registry']:.4f} | {x['peak_realized_ratio']:.3f} "
        f"| {x['peak_r_over_R_built']:.2f} ↔ {x['peak_r_over_R_registry']:.2f} "
        f"| {x['shape_max_dev_pct_main_band']:.2f} | {x['v2']} |")
VERTBL = "\n".join(ver_tbl)

# V5 — 지어진 날이 법칙보다 약 2 % 작은 이유(둘 다 의도된 것)
v5_tbl = ["| 기체 | 스윕디스크 정규화(스팬 배율) | 로프트 둘레비 | 나머지 | 지어진/법칙 |",
          "|---|---|---|---|---|"]
for r in V5["rows"]:
    v5_tbl.append(f"| {drone_label(r['aircraft'])} | {r['span_scale']:.4f} "
                  f"| {r['loft_perimeter_ratio']:.4f} | {r['residual_ratio']:.4f} "
                  f"| **{r['total_built_over_law']:.4f}** |")
V5TBL = "\n".join(v5_tbl)

# 법칙별 검사 예산 — 값은 코드에서, «실측» 은 그 줄의 주석에서 뽑는다(손으로 안 적는다)
import mesh_check as _MC                                    # noqa: E402
_MC_SRC = inspect.getsource(_MC)


def _budget_rows(dict_name, budget, unit=""):
    """`SLIVER_BUDGET_BLADE_LAW` 류 표를 «기체 | 실측 | 예산 | 옛 판 예산» 로."""
    meas = {}
    blk = _MC_SRC.split(dict_name + " = {", 1)[1].split("}", 1)[0]
    for ln in blk.splitlines():
        m = re.search(r'\("([^"]+)",\s*"([^"]+)"\):\s*([0-9.]+),\s*#\s*실측\s*([0-9.]+)'
                      r'[^0-9]*([0-9.]+)?', ln)
        if m:
            meas[(m.group(1), m.group(2))] = (float(m.group(4)),
                                              float(m.group(5)) if m.group(5) else None)
    rows = [f"| 기체 | 실측 | 정본 예산 | 옛 판(legacy) 예산 |", "|---|---|---|---|"]
    for (law, key), lim in sorted(budget.items(), key=lambda kv: kv[0][1]):
        if law != CANON_LAW:
            continue
        mv, old = meas.get((law, key), (None, None))
        rows.append(f"| {drone_label(key)} | {mv:g}{unit} | {lim:g}{unit} "
                    f"| {old:g}{unit} |" if mv is not None else
                    f"| {drone_label(key)} | — | {lim:g}{unit} | — |")
    return "\n".join(rows)


import re                                                    # noqa: E402
SLIVER_TBL = _budget_rows("SLIVER_BUDGET_BLADE_LAW", _MC.SLIVER_BUDGET_BLADE_LAW, "장")
BELL_TBL = _budget_rows("PROP_BELL_SOLID_AREA_PCT_BLADE_LAW",
                        _MC.PROP_BELL_SOLID_AREA_PCT_BLADE_LAW, " %")

_pairs = VERJ["V3_pairwise_shape_dev_pct"]
PAIR_MAX = _pairs[0]
PAIR_IDENT = " · ".join("↔".join(p) for p in V3S["identical_pairs"])
GAPS_MD = "\n".join(f"- {g}" for g in GAPS)
#  두께 — 근거가 있는 기체만 (나머지는 빈칸으로 남긴다)
T_HAVE = [(k, LAW[k]) for k in ORDER
          if LAW[k].get("t_mm") is not None or LAW[k].get("tc_max") is not None]


def md(*lines):
    src = "\n".join(lines).splitlines(keepends=True)
    return {"cell_type": "markdown", "metadata": {}, "source": src or [""]}


def code(src):
    return {"cell_type": "code", "metadata": {}, "execution_count": None,
            "outputs": [], "source": src.splitlines(keepends=True)}


cells = [

# ------------------------------------------------------------------ 1. 표지
md(
"# mesh05 — 프로펠러: 판때기가 아니라 날개다",
"",
*MF.head_md(
    "mesh05",
    "프로펠러를 왜 판이 아니라 비틀린 날개로 만드는가 — 그리고 그 날의 **형상 법칙**이 "
    "지금 무엇으로 정해져 있는가.",
    ["verify", "audit"],
    extra=[("outputs/prop_law_by_airframe_0816.json",
            "기체별 날 법칙 정본 — 프롭 모델명·등급·c_max/R·평면형 곡선·근거·단서"),
           ("outputs/prop_law_verify_0816.json",
            "지어진 메쉬로 되잰 검증 — 기체끼리 정말 다른가·법칙이 얼마나 실현됐나"),
           ("outputs/mesh_adversarial_verdict_0816.json",
            "적대 검증 판결 — 어떤 근거가 살아남고 어떤 근거가 무너졌나"),
           ("docs/MESH_CERTIFICATE.md",
            "메쉬 인증서 — 무엇을 장담하고 무엇은 못 하는가(판정 «조건부 장담»)")]),
"",
"---",
"",
"## ⭐ 정본 — 기체마다 그 기체의 프로펠러",
"",
f"> **지금 기본값**: 날 법칙 `BLADE_LAW_CANON = \"{CANON_LAW}\"` · 메쉬 수리 "
f"`MESH_FIX_CANON = ({CANON_FIX_S})` ← 출처: `src/geom.py`. "
f"환경변수를 안 주면 이 값으로 지어진다.",
"",
f"- **`{CANON_LAW}` 가 무엇인가** — 기체마다 **그 기체의 순정 프로펠러** 평면형(날을 위에서 "
f"봤을 때의 폭 분포)과 최대시위 비율 `c_max/R` 을 쓴다. 모델명까지 확정돼 있다: "
+ " · ".join(f"{drone_label(k)} {LAW[k]['prop'].split('(')[0].strip()}"
             for k in ["matrice4e", "mavic4pro", "mini5pro", "mini2", "s1000plus"]) + " ….",
f"- **옛 `legacy` 판은 {len(ORDER)}기종 전부가 3DR Solo 하나의 날 모양**이었다. 기종 사이 "
f"`c_max/R` 산포가 {SPREAD['headline_ko'].split('산포:')[1].strip()}",
"- ⛔ **옛 판은 언제든 그대로 재현된다** — `MESH_FIX=none BLADE_LAW=legacy` 로 지으면 "
"**비트동일**이다(회귀 시험 `benchmark/regress_blade_law_bitidentical.py`).",
f"- **파일명 꼬리표** — 정본으로 낸 산출물에는 `{FILE_TAG}` 가 붙는다. 이름이 갈려야 "
"계산기가 옛 샤드를 재사용하지 않는다(규약: `benchmark/elevation_sweep_md.py`).",
"",
"이 편의 다른 축들이 지금 어디에 서 있는지부터 적는다:",
"",
"| 축 | 지금 상태 | 근거 |",
"|---|---|---|",
f"| 날 평면형(시위 분포) | **기체별 정본** — 서로 다른 곡선 8개가 {len(ORDER)}기종에 걸린다 "
f"(phantom4·x500v2 는 선언된 대리) | `outputs/prop_law_by_airframe_0816.json` §C |",
"| 최대시위 `c_max/R` | **기체별 정본** — "
f"{min(LAW[k]['c_max_over_R'] for k in ORDER):.4f}~{max(LAW[k]['c_max_over_R'] for k in ORDER):.4f} "
"| 같은 원장 |",
"| 팁 형상 | **정본** — 뭉툭한 팁(`tip_refine=3`)과 0.95/0.98R 마디까지 기체별 곡선에 들어 있다 "
"| 같은 원장 |",
"| 회전 원반 지름 | **맞춰 놓았다** — 지어서 재고 되돌린다(§6) | 이 편 §6 실측 |",
"| 기하 피치 곡선 | **legacy 그대로** — 정본 날 법칙은 평면형만 바꿨다(§4) | `src/drone_cad.py` "
"`BLADE_LAWS['per_airframe'].pitch_default` |",
"| 파장 대비 삼각형 크기 | 인증서 G4 가 **λ/16 사지타** 기준으로 10/10 통과(위반 면적 ≤ 0.01 %) "
"| `docs/MESH_CERTIFICATE.md` §2 |",
f"| 날 두께 | ⛔ **여전히 전 기종 공용 상수**(`TC_ROOT`={_DC.TC_ROOT:.3f}·`TC_TIP`={_DC.TC_TIP:.3f}) "
f"— 실측 근거가 있는 기체는 {len(T_HAVE)}/{len(ORDER)}뿐이다(§5·§6) | 같은 원장 §F |",
"",
"그리고 이 편 전체에 걸리는 두 문장은 그대로다:",
"",
"- **움직이는 성분(AC)은 정의상 프로펠러만 남는다.** 정지한 동체의 기여는 순수 DC 라",
"  DC 를 걷어내면 사라진다. 이것은 측정이 아니라 구조적 필연이다.",
"- **총 반사(σ)로는 동체가 훨씬 세다** — matrice4e 부품 분해에서 프로펠러 몫은",
"  el −30° 에서 2.4 %(16.2 dB 아래), el 0° 에서 0.2 %(28.1 dB 아래)다",
"  ← 출처: `docs/MESH_AUDIT_0816.md` §④-1(우리 PO 커널로 부품별 분해).",
"- ⇒ «프로펠러가 표적을 지배한다» 는 **AC 채널 한정 문장**이다. 총 σ 문장으로 옮겨 쓰면 틀린다.",
"",
f"> ⚠ **원장 세대 주의** — `report_mesh/outputs/mesh_verify.json` 은 정본 전환 **이전** "
f"세대(2026-08-16 13:15)다. 그래서 이 편의 **형상 수치(면 수·프롭 몫·삼각형 크기·좌우대칭·"
f"프롭 지름)는 정본 판에서 다시 잰 원장** `report_mesh/outputs/mesh_verify_canon_0817.json` "
f"에서 읽는다(생성기: `report_mesh/src/verify_mesh_canon_0817.py`, 같은 검사 함수를 정본 "
f"설정으로 다시 부른 것). 재질 가중치 γ 처럼 정본 전환과 무관한 값만 옛 원장에서 읽는다. "
f"⛔ 두 원장의 스위치가 어긋나면 이 편의 생성기가 **멈춘다**(다른 판의 수를 싣지 않는다).",
"",
"---",
"",
f"**한 줄 요약** — 우리 드론 {len(ORDER)}종의 프로펠러는 납작한 판이 아니라, **NACA 익형 단면을 "
f"반경 방향으로 비틀며(피치) 이어붙인(로프트) 진짜 날개**이고, 이제 **기체마다 그 기체의 순정 "
f"프로펠러 평면형**을 쓴다. 단면은 공개 표준식, 비틀림은 공표 피치 P, 평면형은 그 기체 프롭의 "
f"실측 — 셋 다 출처가 있고 등급이 붙어 있다. 지어진 메쉬로 되재 보면 "
f"{V3S['pairs']}쌍 중 **{V3S['distinct_over_1pct']}쌍이 1 % 넘게 구별**된다(§6).",
"",
"## 용어 풀이 (이 편에 나오는 말들)",
"",
"| 용어 | 뜻 |",
"|---|---|",
"| **익형(airfoil)** | 날개를 칼로 자르면 나오는 단면 모양. 앞이 둥글고 뒤가 뾰족한 물방울꼴 |",
"| **시위(chord)** | 익형의 앞전(둥근 앞)→뒷전(뾰족한 뒤)을 잇는 직선 길이. \"날개 폭\" |",
"| **NACA-4** | 미국 NACA(NASA 의 전신)가 1930년대에 정리한 4자리 익형 시리즈. 두께 분포가 다항식 하나로 나온다 |",
"| **기하 피치(P)** | 프로펠러를 나사라고 보고, 미끄러짐 없이 1바퀴 돌 때 전진하는 거리. 파트번호의 둘째 숫자(인치) |",
"| **피치각 θ(r)** | 반경 r 의 단면이 회전면과 이루는 각 |",
"| **워시아웃(washout)** | 허브→팁으로 갈수록 피치각이 줄어드는 비틀림 |",
"| **테이퍼(taper)** | 팁으로 갈수록 시위가 좁아지는 것 |",
"| **시미터 스큐(scimitar skew)** | 날 끝이 초승달 칼처럼 뒤로 휘는 것(저소음 프롭의 특징) |",
"| **로프트(loft)** | 단면 여러 장을 순서대로 이어붙여 3D 곡면을 만드는 CAD 기법. 배 만들 때 늑골에 판자를 붙이는 것과 같다 |",
"| **마이크로도플러** | 기체 전체의 속도와 별개로, 회전·진동하는 **부품**이 만드는 잔 도플러 성분 |",
"| **블레이드 플래시** | 날이 레이더 정면을 향하는 순간 반사가 \"번쩍\"하는 주기 신호 |",
"| **카이럴(chiral)** | 거울에 비추면 자기 자신과 절대 겹칠 수 없는 성질(오른손↔왼손, 나사) |",
"| **chamfer 거리** | 두 점구름에서 \"상대편 가장 가까운 점까지의 거리\" 분포 — 모양 차이를 mm 로 재는 자 |",
"| **RCS** | radar cross section. 표적이 레이더에 얼마나 큰 면적으로 보이는가 [m²] |",
"| **평면형(planform)** | 날개를 **위에서 내려다본** 윤곽. 반경마다 시위가 얼마인지의 분포 |",
"| **c_max/R** | 가장 넓은 지점의 시위를 반경으로 나눈 값. \"이 프롭이 얼마나 통통한가\" 한 수로 |",
"| **시위 정점 r/R** | 시위가 최대가 되는 반경 위치. 안쪽(0.25R)이면 뿌리 편중형, 바깥(0.55R)이면 늦은 정점형 |",
"| **대리(proxy)** | 그 기체의 근거가 없어 **다른 기체의 계측을 대신 세운** 칸. 표에 ⛔로 표시한다 |",
"| **근거 등급 [A]~[D]** | [A] 공식 CAD 직접 · [B] 사진 계측 · [C] 계열 유추 · [D] 대리. 등급은 "
"**출처의 질**이지 \"검증됐다\"가 아니다 |",
),

# ------------------------------------------------------- 2. §1 왜 중요한가
md(
"## 1. 왜 프로펠러가 레이더에 중요한가 — 가장 약하지만, 가장 특별한 부품",
"",
"프로펠러는 역설적인 산란체다. 재질로 보면 드론에서 **가장 약한** 반사체이고, 신호로 보면 "
"**가장 특별한** 반사체다.",
"",
f"- **약하다**: 프롭은 나일론/복합재 플라스틱이다(Mini 5 Pro 프롭 6028F: \"나일론+고무 팁\" "
f"← 출처: docs/SPECS.md §DJI Mini 5 Pro·dji.com/mini-5-pro/specs). 재질 가중 PO 의 전력 반사 "
f"가중치는 γ(prop)={MAV['gamma_prop']:g} — 모터(γ={G_MOTOR:.2f}, 사실상 금속)의 ¼, 동체 셸"
f"(γ={G_BODY:g})보다도 약하다 ← 출처: mesh_verify.json `E_materials.*.gamma_map`(원본 src/materials.py).",
"- **특별하다**: 드론에서 **항상 돌고 있는 유일한 부품**이다. 몸체 에코는 새·풍선·간판과 "
"헷갈릴 수 있지만, 날이 레이더 정면을 스칠 때마다 번쩍이는 **블레이드 플래시**와 날개끝 속도가 "
"만드는 **마이크로도플러 확산**은 회전 날개만 만들 수 있는 지문이다.",
"",
"그 지문의 리듬은 스펙만으로 계산된다. 2날 프롭이면 한 바퀴에 두 번 번쩍이므로 플래시 주파수 = "
"날수×회전수/60, 날개끝 도플러 폭은 ±2·v_tip/λ 이다(모노스태틱, 팁이 시선 방향일 때):",
"",
MDOP,
"",
f"↑ 프롭 지름·날수·피치 ← 출처: src/drones.py DroneSpec(`prop_dia_mm`·`prop_blades`·"
f"`prop_pitch_in` — 필드 정의, 기종별 값·docs/SPECS.md(각 기종 절+공식 URL). 호버 rpm ← 출처: "
f"docs/drone_specs_2026.json `micro_doppler.hover_rpm_basis`(기종별 유도 근거: 추력균형 "
f"T=C_T·ρ·n²·D⁴ + 교차검증). 플래시·팁속도·f_tip 은 λ={LAM_MM:.1f} mm(={FC:g} GHz, "
f"mesh_verify.json `meta.fc_ghz`)로 위 공식에서 계산한 값이다.",
"",
f"> ⚠ **주의**: Matrice 4E 의 호버 rpm({ROWS['matrice4e']['rpm']:g})은 **미해결**이다 — "
f"C_T 법은 3950~4410, 공식 최대 rpm(7500, C2 인증) 앵커링은 4740~5300 을 준다. 우리가 채택한 호버 rpm "
f"3800(C_T≈0.108, T/W_max≈3.9)은 **두 방법의 범위보다 낮다** — 어느 쪽이 맞는지 **결론을 못 낸** 미해결 값이다. "
f"플래시·f_tip 이 이 값에 선형으로 걸린다 ← 출처: src/drones.py note.",
"",
"그래서 프로펠러의 **모양**이 틀리면 이 지문 전체가 틀린다. 날의 폭(시위)·비틀림(피치)·휨(스큐)이 "
"각도별 반짝임의 세기와 타이밍을 정하기 때문이다. 마이크로도플러 **결과**는 본편 권 6 "
"«마이크로도플러 — 도는 로터가 남기는 무늬»(`reports/06_1_scene.ipynb` 이하)가 다루고, "
"이 편은 그 입력이 되는 **날개 기하**를 만든다.",
"",
f"참고로 비용도 만만치 않다: Mavic 4 Pro 메쉬 전체 {MAV['all_faces']:,}면 중 프롭 그룹이 "
f"{MAV['prop_faces']:,}면 — **{MAV_FACE_PCT:.0f}%** 다(4로터×2날의 얇은 곡면이라 삼각형이 많이 든다). "
f"함대 전체로는 프롭 몫이 {PROP_PCT_MIN:.0f}~{PROP_PCT_MAX:.0f} % 로 갈린다 — 가장 낮은 쪽 "
f"{drone_label(PROP_PCT_MIN_WHO)}, 가장 높은 쪽 {drone_label(PROP_PCT_MAX_WHO)}"
f"({DRONES[PROP_PCT_MAX_WHO].num_rotors}로터라 프롭이 기체의 대부분이다):",
"",
SHARE,
"",
f"↑ 출처: `report_mesh/outputs/mesh_verify_canon_0817.json`(정본 판 형상 원장, "
f"`MESH_FIX={CANON_FIX_S}` · `BLADE_LAW={CANON_LAW}`) §A_geometry·§prop_triangles. "
f"λ_hi = {LAM_HI_MM:.1f} mm 는 우리가 쓰는 **최고 대역**의 파장이라 삼각형 크기 판정에서 "
f"가장 빡빡한 기준이다.",
"",
f"**삼각형이 파장 대비 충분히 잔가** — 프롭 삼각형의 모서리는 최악에서도 "
f"λ_hi 의 {EDGE_LAM_MAX:.2f} 배({drone_label(EDGE_LAM_MAX_WHO)}, 큰 프롭일수록 성겨진다)이고, "
f"흔한 값(p95)은 λ_hi 의 {min(CAN[k]['prop_edge_p95_lam'] for k in ORDER):.2f}~"
f"{max(CAN[k]['prop_edge_p95_lam'] for k in ORDER):.2f} 배다. 곡면이 얼마나 매끄럽게 따라가는지는 "
"인증서가 따로 판정한다 — 곡면 이산화(사지타 ≤ λ/16, 3.5·5.8 GHz)를 10기체 전부 통과하고 위반 "
"면적이 0.01 % 이하다 ← 출처: `docs/MESH_CERTIFICATE.md` §2 G4.",
"",
"> ⭐ **이 숫자를 «PO 적분이 성긴가» 로 읽지 말 것.** 우리 PO 커널은 삼각형을 그대로 쓰지 않고 "
"**자기 간격으로 다시 점을 깔아** 면적분한다(`rcs_po.mesh_to_points(mesh, spacing)`). "
"즉 위 표는 **모양이 얼마나 곱게 표현됐나**의 잣대이지 적분 표본 간격이 아니다. 적분 쪽 "
f"민감도는 따로 재어져 있다 — 점 간격을 λ/10 ↔ λ/20 으로 바꾸면 방위평균 σ 가 "
f"{abs(V['H_po_convergence']['mavic4pro']['azavg_dbsm']['diff']):.2f}"
f"~{abs(V['H_po_convergence']['phantom4']['azavg_dbsm']['diff']):.2f} dB 움직이고 "
f"각도별로는 평균 {V['H_po_convergence']['mavic4pro']['per_angle_absdiff_db']['mean']:.1f}"
f"~{V['H_po_convergence']['phantom4']['per_angle_absdiff_db']['mean']:.1f} dB 다 "
f"← `outputs/mesh_verify.json` §H_po_convergence(2기체, el 15°, {FC:g} GHz).",
),

# ------------------------------------------------------- 3. 그림
md(
"## 2. 이 편의 그림 — 한 장에 익형→피치→3D",
"",
"![propeller airfoil](outputs/figures/airfoil_profile.png)",
"",
"그림 생성: `report_mesh/src/viz_mesh_reports.py` `fig_airfoil()` — 아래에서 패널별로 뜯어본다.",
"",
"- **(a)** 날개 단면(NACA 계열 익형), 시위=1 로 정규화. 두께비 10%와 16% 두 곡선 — §3.",
f"- **(b)** 기하 피치각 θ(r)=atan(P/2πr) 을 {len(ORDER)}기종 스펙 피치로 그린 곡선 — §4. "
"허브 쪽이 가파르고 팁이 완만한 이유가 이 편의 핵심이다.",
"- **(c1)(c2)** Mavic 4 Pro 와 S1000+ 의 완성 프로펠러 — 비틀린 익형 단면들을 로프트한 결과 — §5.",
"",
"> ⚠ **이 그림의 세대** — (a)(b) 는 법칙과 무관하다(NACA 공식과 공표 피치 P 만 쓴다). "
"(c1)(c2) 의 3D 날은 **정본 전환 이전 판으로 구워진 그림**이라, 지금 지어지는 날의 "
"«폭 분포»와는 다르다. 정본 평면형의 수치는 §5·§6 의 표에서 읽을 것 — 이 라운드는 "
"그림을 다시 굽지 않았다.",
),

# ------------------------------------------------------- 4. §2 NACA
md(
"## 3. NACA-4 익형 — 단면은 공식 하나로 나온다",
"",
"날개 단면을 어떻게 그릴까? 우리는 1933년 NACA 보고서 이래 항공계 표준인 **NACA 4자리 익형**의 "
"두께 분포식을 쓴다. 시위를 0~1 로 두면(x=앞전 0, 뒷전 1), 두께비 t 인 단면의 반두께는:",
"",
"$$y_t(x) = 5t\\,(0.2969\\sqrt{x} - 0.1260x - 0.3516x^2 + 0.2843x^3 - 0.1015x^4)$$",
"",
"코드는 이 식을 그대로 옮겼다 ← 출처: src/drone_cad.py `_airfoil()`:",
"",
"```python",
"def _airfoil(chord, thick_ratio=0.10, pts=40):",
"    \"\"\"NACA-4 익형 단면(y=시위, z=두께). **캠버 포함**(camber_m=0 이면 대칭).\"\"\"",
"    t = thick_ratio",
"    x = (1 - np.cos(np.linspace(0, np.pi, pts // 2))) / 2   # 코사인 클러스터링(앞전 촘촘)",
"    yt = 5 * t * (0.2969 * np.sqrt(x) - 0.1260 * x - 0.3516 * x**2",
"                  + 0.2843 * x**3 - 0.1015 * x**4)",
"    ...",
"    P[:, 0] -= chord * 0.30                                 # 시위 30% 를 원점(피치축)으로",
"```",
"",
"**왜 이렇게 했나 (선택의 이유):**",
"",
"1. **왜 NACA 인가** — DJI 는 자기 프롭의 실제 익형 좌표를 공개하지 않는다(SPECS.md 에도 지름·피치·"
"재질뿐이다). 실단면을 모르는 상태에서 최선은 **공개 표준식**이다: 파라미터가 두께비 하나뿐이라 "
"재현 가능하고, 소형 프롭 단면과 시각적으로 잘 맞는다. 대안으로 생각할 수 있는 (i) 실물 역설계는 "
"데이터가 없고, (ii) 타원 단면은 앞전이 너무 뭉툭해지고, (iii) 직사각 단면(판)은 앞전의 둥근 회절과 "
"두께 분포를 통째로 잃는다(§5b 의 비교 참조).",
"2. **왜 코사인 클러스터링인가** — x 를 균일하게 40등분하면 곡률이 큰 **앞전**(√x 항이 지배)이 "
"각져 버린다. x=(1−cos u)/2 치환은 같은 점 수로 앞전에 점을 몰아준다. CFD/격자 생성에서 쓰는 표준 "
"트릭을 그대로 가져왔다 ← 출처: src/drone_cad.py 주석.",
"3. **왜 원점을 시위 30% 에 두나** — 이 원점이 곧 **피치축**(날을 비트는 회전축)이다. 실물 프롭도 "
"앞전이 아니라 시위 1/4~1/3 지점 근방을 축으로 비틀려 있다 ← 출처: src/drone_cad.py 주석.",
"",
"단면은 shapely `Polygon` 으로 반환된다 — 다음 단계(로프트·불리언)가 shapely/trimesh 파이프라인"
"(`src/cadkit.py`)이기 때문이다. 아래 셀로 직접 확인해 보자.",
),

code(
"""# NACA 단면을 직접 만들어 확인 — 노트북은 report_mesh/ 에서 열리므로 ../src 를 경로에 추가
import sys, os, numpy as np
sys.path.insert(0, os.path.abspath("../src"))
from drone_cad import _airfoil                      # ← src/drone_cad.py

poly = _airfoil(chord=1.0, thick_ratio=0.10)        # 시위 1, 두께비 10% (그림 (a) 파란 곡선)
pts = np.asarray(poly.exterior.coords)
print(f"둘레 점 개수      : {len(pts)}")
print(f"x(시위) 범위      : [{pts[:,0].min():+.3f}, {pts[:,0].max():+.3f}]  ← 0 이 피치축(시위 30% 지점)")
print(f"최대두께(위-아래) : {pts[:,1].max()-pts[:,1].min():.4f}  ← 두께비 0.10 이면 이론값 0.100")""",
),

# ------------------------------------------------------- 6. §3 기하피치
md(
"## 4. 기하 피치 — 파트번호 두 번째 숫자가 날개 비틀림 전체를 정한다",
"",
"프로펠러 파트번호에는 관례가 있다: **지름×피치**(인치). 예컨대 Phantom 4 의 \"9450\" 프롭은 "
"9.4″ 지름 × 5.0″ 피치라는 뜻이다. 기하 피치 P 는 \"프로펠러를 나사못이라고 보고, 미끄러짐 없이 "
"한 바퀴에 나아가는 거리\"다.",
"",
"나사 비유를 밀고 가면 비틀림 각이 저절로 나온다. 반경 r 의 단면은 한 바퀴에 원둘레 2πr 을 "
"돌면서 전진 P 를 만들어야 한다. 나선의 경사각이 곧 피치각이다:",
"",
"$$\\theta(r) = \\mathrm{atan}\\!\\left(P / 2\\pi r\\right)$$",
"",
"**왜 이 방식인가** — DJI 는 날의 트위스트 분포(반경별 각도표)를 공개하지 않는다. 공개된 것은 "
"파트번호 속 피치 P 하나다. 그런데 θ(r)=atan(P/2πr) 은 **P 하나만으로 반경 전 구간의 비틀림을 "
"물리적으로 유일하게** 정해 준다 — 임의의 선형 트위스트(`pitch_deg`/`twist_deg` 폴백, "
"`pitch_m` 을 안 줄 때만 쓰임)보다 근거가 강하고, 모델별 개성(P 가 다르면 날이 다르게 비틀림)이 "
"자동으로 생긴다 ← 출처: src/drone_cad.py·89-92 (`pitch_m` 분기).",
"",
"> ⭐ **정본 날 법칙은 이 축을 건드리지 않았다.** 기체별 정본은 «날을 위에서 본 폭 분포»(평면형)만 "
"바꿨고, 비틀림 곡선은 `legacy` 그대로다 ← 출처: `src/drone_cad.py` "
"`BLADE_LAWS['per_airframe']['pitch_default']`. 실물 계측에서 나온 대안 피치 곡선"
"(`PITCH_LAWS['dji_mini2']`, 기준 반경 0.75R)은 **일부러 안 켰다** — 그 축의 이득이 "
"커널 실측으로 ≤ 0.10 dB 였고(앙각 16점·모노/바이스태틱·3.5·10 GHz), «실물은 0.75R 기준» 이라는 "
"논거도 실측 프로펠러 132종에서 P(0.5R)/P(0.75R) 중앙값 0.996 으로 흐려졌다 "
"← 출처: `outputs/mesh_adversarial_verdict_0816.json` 5a·5b. "
"남는 정직한 사실 하나는 **공칭 피치를 0.5R 기준 표에 그대로 먹여 날 전체가 약 +6 % 과피치**라는 "
"것이고, 커널로 잰 대가는 ≈ +0.13 dB 다.",
"",
f"{len(ORDER)}기종의 피치와, 그로부터 계산한 허브 쪽(0.15R)·팁의 피치각:",
"",
PITCH,
"",
"피치 P 의 출처를 기종별로 하나하나 밝히면(사용자 특별 지시):",
"",
"- **Mini 5 Pro** 2.8″ ← 프롭 6028F \"152.4×71.1 mm (diameter×thread pitch)\" — DJI 매뉴얼 "
"C0 인증표 **공식** (docs/SPECS.md §Mini 5 Pro, docs/drone_specs_2026.json, dji.com/mini-5-pro/specs).",
"- **Mavic 4 Pro** 5.8″ ← 프롭 1158F \"26.7 × 14.7 cm\" — DJI 가 지름과 **피치를 함께** 공표한다"
"(14.7 cm = 5.787″ → 5.8″). 즉 **제조사 공표값**이지 추정이 아니다 "
"(← src/drones.py mavic4pro note · docs/SPECS.md §Mavic 4 Pro).",
"- **Matrice 4E** 5.7″ ← 프롭 1157F. 단 DJI 공식은 \"10.8 inch, composite\"뿐이고 14.5 cm "
"피치는 모델명 규칙(11**57**F=5.7″)+리셀러 리스팅에서 온 **강한 추정**이다 "
"(docs/SPECS.md §Matrice 4E 검증 노트, enterprise.dji.com/matrice-4-series/specs).",
"- **S1000+** 5.2″ ← 프롭 1552, 15×5.2″ — DJI **공식** (docs/SPECS.md §S1000+, "
"dji.com/spreading-wings-s1000-plus/info).",
"- **Phantom 4** 5.0″ ← 프롭 9450, 9.4″×5.0″ — DJI **공식** (docs/SPECS.md §Phantom 4, "
"dji.com/phantom-4/info, store.dji.com/product/self-tightening-propellers).",
#  ⭐ 2026-07-30 (Phase 3): 비-DJI 2종이 표적에 들어왔다. 이 목록은 손으로 유지하는 출처
#     장부이므로(등급이 코드로 유도되지 않는다) 기종을 추가하면 여기도 같이 늘려야 한다.
"- **Typhoon H480** 6.0″ ← Yuneec 는 피치를 공표한 적이 없다. 실물 CAD 앙상블에서 잰 "
"5.84 ± 0.20″ 에서 온 **DERIVED** 값이다 (src/drones.py `typhoonh480` note, "
"docs/RESUME_0729.md §5).",
"- **X500 V2** 4.5″ ← 킷 프롭 **1045**(10 × 4.5″) — Holybro **공식** "
"(docs.holybro X500 V2 킷 구성, src/drones.py `x500v2` note). ⚠ 이 저장소의 참조 CAD 에 "
"들어 있는 1345 프롭은 **X500 의 프롭이 아니다** (같은 note 참조).",
),

# ------------------------------------------------------- 7. §3b 그림(b) 해설
md(
"### 4b. 그림 (b) 읽기 — 왜 허브 쪽은 가파르고 팁은 완만한가",
"",
f"그림 (b)의 {len(ORDER)}개 곡선이 전부 **왼쪽(허브)에서 높고 오른쪽(팁)에서 낮은** 이유는 공식이 말해 준다. "
f"한 바퀴에 전진해야 하는 거리 P 는 모든 단면에 **똑같은데**, 안쪽 단면은 작은 원(2πr 작음)을 돌므로 "
f"더 **가파르게** 기울어야 같은 전진을 만든다. 즉 워시아웃(허브→팁 비틀림 감소)은 멋이 아니라 "
f"\"나사가 되기 위한\" 기하학적 필연이다. 부수 효과로, 모든 단면이 공기에 대해 비슷한 받음각으로 "
f"일하게 되어 실물 프롭도 다 이렇게 만든다.",
"",
f"곡선의 개성도 스펙에서 나온다 (표 4 의 수치 그대로):",
"",
f"- **Mini 5 Pro** (파란 곡선)만 뚝 떨어져 있다: P={ROWS['mini5pro']['P_in']:g}″ 로 유일하게 3″ 미만이라 "
f"같은 반경에서 각이 작고, R={ROWS['mini5pro']['R_mm']:.1f} mm 로 짧아 곡선이 일찍 끝난다 "
f"(팁 {ROWS['mini5pro']['th_tip']:.1f}°).",
f"- **S1000+** (빨간 곡선)는 반대로 R={ROWS['s1000plus']['R_mm']:.1f} mm 로 가장 길어 오른쪽 멀리까지 "
f"이어지고, 팁 피치각 {ROWS['s1000plus']['th_tip']:.1f}° 로 {len(ORDER)}종 중 가장 완만하다 — 큰 프롭을 천천히 "
f"돌리는 리프터의 전형(P/D 비가 가장 작다).",
f"- **Mavic 4 Pro·Matrice 4E·Phantom 4** 는 P 가 5.0~5.8″ 로 비슷해 곡선이 거의 겹친다 — 팁 "
f"{ROWS['mavic4pro']['th_tip']:.1f}~{ROWS['matrice4e']['th_tip']:.1f}° 대.",
"",
"이 곡선이 바로 §5 로프트에서 각 단면에 주는 회전각이다. 아래 셀로 표를 재현할 수 있다.",
),

code(
f"""# 그림 (b) = θ(r)=atan(P/2πr) 를 스펙에서 재계산 (viz_mesh_reports.py fig_airfoil 과 동일 수식)
import sys, os, math
sys.path.insert(0, os.path.abspath("../src"))
from drones import DRONES                    # ← 스펙의 유일한 진리원 (src/drones.py)

for key in {ORDER!r}:
    s = DRONES[key]
    R = s.prop_dia_mm / 2000.0               # 반경[m]
    P = s.prop_pitch_in * 0.0254             # 기하피치[m]
    th = lambda r: math.degrees(math.atan(P / (2 * math.pi * r)))
    print(f"{{s.name:16s}}  P={{s.prop_pitch_in:>3.1f}}\\"  R={{R*1000:5.1f}}mm   "
          f"θ(0.15R)={{th(0.15*R):4.1f}}°  →  θ(팁)={{th(R):4.1f}}°")""",
),

# ------------------------------------------------------- 9. §4 _blade 파라미터
md(
"## 5. 날개 한 장의 해부 — `_blade()` 파라미터 하나하나",
"",
"단면(§3)과 비틀림(§4)이 준비됐으니 날개를 조립한다. `_blade()` 는 반경 방향으로 단면을 "
"22장 깔고, 각 단면에 **축소(테이퍼)·회전(피치)·이동(스큐)** 세 변환을 준 뒤 로프트한다 "
"← 출처: src/drone_cad.py.",
"",
"```python",
*_BLADE_SIG_LINES,
"    \"\"\"**진짜 익형 프로펠러 블레이드 1장** — 로프트(테이퍼 + 워시아웃 트위스트 + 시미터 스윕).",
"      chord_max : **R 에 대한 비율**. ⚠ 절대길이를 넣지 말 것.",
"      pitch_m   : 프로펠러 **기하 피치**[m] (1회전 전진량). ...\"\"\"",
"```",
"",
"(시그니처는 생성 시점에 `inspect` 로 소스에서 읽어 넣는다 — 손으로 옮겨 적지 않는다.)",
"",
"⭐ **읽는 법 주의** — 위 기본값은 `_blade()` 를 **혼자 부를 때**의 값이다. 실제 빌드 경로는 "
"`build_propeller_cad()` 이고, 그쪽이 `blade_law=None` → 정본(`geom.blade_law_canon()`)으로 "
"풀어 **그 기체의 평면형·`c_max/R` 을 인자로 넘긴다** ← 출처: `src/drone_cad.py` "
"`build_propeller_cad` · `resolve_chord_max_over_r` · `resolve_chord_profile`. "
"즉 «기본 호출은 전 기종 공용» 이 아니라 **기체마다 다른 값이 들어간다**.",
"",
"| 파라미터 | 값 | 무엇을 하나 · 왜 이 값인가 |",
"|---|---|---|",
"| `root_frac` | 날이 시작하는 반경 비율 | 루트가 허브 반경보다 **안쪽**이라 블레이드와 허브가 한 솔리드가 된다 — 의도된 설계다 |",
f"| `chord_max` | **기체별**({min(LAW[k]['c_max_over_R'] for k in ORDER):.4f}~"
f"{max(LAW[k]['c_max_over_R'] for k in ORDER):.4f}) | 최대시위를 반경 대비 비율로 준다. "
f"값과 등급은 §5c 표 — 그 기체 순정 프롭의 계측에서 온다 ← `drones.PROP_LAW_0816` |",
"| 시위 분포(평면형) | **기체별 곡선**(21점) | 루트 좁게 → 어딘가에서 최대 → 팁 둥글게. "
"**최대가 어디인가**가 기체마다 다르다(0.25R ~ 0.55R) — 배율로는 흉내 낼 수 없는 차이라 "
"곡선 자체를 기체별로 둔다 ← `resolve_chord_profile` docstring |",
"| `pitch_m` | 스펙 P (기종별) | **워시아웃**: θ(r)=atan(P/2πr) 로 단면마다 회전 ← src/drone_cad.py |",
"| `pitch_deg`·`twist_deg` | 20°·13° | `pitch_m=None` 일 때만 쓰는 선형 워시아웃 **폴백** — 실제 프로펠러 빌드는 항상 스펙 P 를 `pitch_m` 으로 넘긴다 ← src/drone_cad.py·350 |",
"| `sweep_frac` | 0.10 | **시미터 스큐**: y 이동량 = 0.10·R·sin(π/2·t) — 팁으로 갈수록 뒤로 휜다. DJI 저소음 프롭의 초승달 실루엣(투영 면적이 달라지므로 레이더에도 형상 인자) ← src/drone_cad.py |",
"| `tip_refine` | 3 (정본) | 팁 쪽 단면을 더 촘촘히 깔아 **뭉툭한 끝**을 살린다 ← `BLADE_LAWS` |",
f"| 두께비 | `TC_ROOT`={_DC.TC_ROOT:.3f} · `TC_TIP`={_DC.TC_TIP:.3f} — ⛔**전 기종 공용** "
f"| 앞의 NACA t 를 단면마다 다르게: **루트 {_DC.TC_ROOT * 100:.1f}% → 팁 "
f"{_DC.TC_TIP * 100:.1f}% 테이퍼**(뿌리는 굽힘 하중을 버텨야 두껍고, 팁은 공력 효율을 위해 얇다). "
f"기체별 두께는 **레지스트리에 칸만 있고 메쉬에 안 들어간다** — `_blade` 가 `prop_law_t_mm` 을 "
f"읽지 않는다. 실측 근거가 있는 기체도 {len(T_HAVE)}종뿐이다(§6) |",
f"| `n_sec`·`n_pts` | 22·36 | 스팬 단면 수·단면당 점 수 — 곡면 매끈함과 삼각형 수의 절충"
f"(§1: 프롭이 전체 면의 {PROP_PCT_MIN:.0f}~{PROP_PCT_MAX:.0f} %) |",
),

# ------------------------------------------------------- 10. §4b 로프트
md(
"### 5b. 로프트 — 단면 22장이 3D 날개가 되는 순간",
"",
"변환을 마친 단면(shapely Polygon) 22장을 `(반경 위치, 단면)` 목록으로 넘기면 `loft()` 가 "
"이웃 단면끼리 옆면 삼각형 띠로 잇고 양 끝을 막아 닫힌 곡면을 만든다 ← 출처: src/cadkit.py:",
"",
"```python",
"def loft(sections, n_pts=48, cap=True):",
"    \"\"\"단면들을 x 를 따라 이어 붙인다.  sections = [(x, shapely Polygon(y,z)), ...]",
"    ※ 이게 있어야 '눈물방울 동체', '허리가 잘록한 캐노피' 같은 **진짜 곡면**이 나온다.\"\"\"",
"```",
"",
"그리고 `build_propeller_cad()` 가 허브(회전체)와 날 `prop_blades` 장을 360°/날수 간격으로 "
"돌려 심고, **불리언 합집합**으로 허브에 파묻힌 날 뿌리의 내부 면을 녹여 없앤다(내부 면이 남으면 "
"PO/SBR 이 헛센다 — mesh 시리즈의 파이프라인 편 참조) ← 출처: src/drone_cad.py.",
"",
"**왜 로프트인가 — 대안과 비교**:",
"",
"- **직사각 판 근사(가상의 대안)**: 만약 단면을 익형 대신 **직사각형 판**(네 꼭짓점 링)으로 "
"근사하면 로프트는 훨씬 싸진다. 하지만 멀리서 보면 비슷해도, 단면이 판이 되는 순간 앞전의 둥근 "
"회절·두께 분포·받음각별 투영이 전부 사라진다 — \"판때기가 아니라 날개다\"라는 이 편의 제목이 "
"가리키는 대비가 바로 이것이다.",
"- **인터넷 CAD 다운로드**: 라이선스·기종 불일치·검증 불가 문제로 **대조용으로만** 쓴다"
"(assets/meshes/reference/SOURCES.md — 실물 대조는 mesh 시리즈의 검증 편에서).",
"- **복셀/스컬프팅**: 파라메트릭이 아니어서 \"피치를 스펙값으로 바꿔 재생성\" 같은 일이 불가능하다. "
"우리 파이프라인은 스펙 숫자 → 코드 → 메쉬가 한 줄로 이어져야 한다(재현성).",
"",
"그림 (c1)(c2)이 그 결과다: 같은 코드, 다른 스펙 — Mavic 4 Pro 와 S1000+ 의 날이 정말 다르게 "
"생겼는지 눈으로 확인하라. 다음 절이 **그 날의 폭 분포가 어느 프롭의 어떤 계측에서 왔는지**를 "
"기체마다 적고, §6 이 그것이 지어진 메쉬에서 지켜졌는지를 숫자로 확인한다.",
),

# ------------------------------------------------- 9b. §5c 기체별 법칙 표(정본)
md(
"### 5c. 기체별 법칙 — 어느 프롭을, 어떤 근거로",
"",
"정본이 실제로 무엇을 쓰는지 한 표에 모은다. **등급은 출처의 질**이고, ⛔대리 표시는 "
"«그 기체의 계측이 아니라 다른 기체의 계측을 대신 세웠다» 는 뜻이다.",
"",
LAWTBL,
"",
"↑ 출처: `outputs/prop_law_by_airframe_0816.json` §C(법칙) · §D(옛 판 대비 변화). "
"«날 1장 설계면적 Δ» 는 **설계 평면형의 ∫c dr**(0.07R~팁) 이 옛 판 대비 몇 % 인가다. "
"⚠ 옆의 dB 칸은 면적비를 20·log10 한 **참고값**이지 σ 변화가 아니다 — 커널로 재면 "
"면적→σ 지수가 앙각에 따라 0.12~1.69 로 변한다(정면 정반사 근처에서만 20log10 에 가깝고, "
"헤드라인 앙각 el −30° 에서는 그 절반쯤이다) ← 출처: "
"`outputs/mesh_adversarial_verdict_0816.json` R1.",
"",
"같은 표의 **근거와 단서**를 그대로 옮긴다 — 이 편에서 가장 정직해야 할 자리다:",
"",
LAWSRC,
"",
"**이 법칙이 아직 못 채운 칸**(원장이 스스로 적는 목록 그대로):",
"",
GAPS_MD,
"",
"그래서 이 법칙의 값어치를 정확히 적으면 이렇다 — **σ 정확도가 아니라 «기체 구분»** 이다. "
"총면적을 옛 판과 같게 맞춘 «면적중립» 평면형으로 바꿔 σ 를 재면 전 앙각에서 |Δσ| ≤ 0.14 dB 다. "
"즉 σ 축에서 실제로 움직이는 손잡이는 **총면적 하나**이고, 평면형의 나머지 차이는 "
"«기체마다 다른 프롭이다» 라는 **분류 축**에서 값어치를 갖는다 "
"← 출처: `outputs/mesh_adversarial_verdict_0816.json` R3.",
),

# ------------------------------------------------------- 11. §6 현재 검증
md(
"## 6. 지금 검증돼 있는 것, 그리고 아직 빈 칸",
"",
"§3~5 의 유도가 **지어진 메쉬에서 실제로 지켜지는지** 확인한다. 설계표를 믿지 않고 "
"`build_propeller` 가 뱉은 삼각형만 잘라서 되잰 원장이 있다 "
"← `outputs/prop_law_verify_0816.json`(판정 **" + VERJ["verdict"] + "**).",
"",
"### 6.1 기체마다 정말 다른 프롭인가 — 지어진 메쉬로 되재기",
"",
f"- **{V3S['pairs']}쌍 중 {V3S['distinct_over_1pct']}쌍이 1 % 넘게 구별**된다. 가장 크게 갈리는 쌍은 "
f"{drone_label(PAIR_MAX['a'])} ↔ {drone_label(PAIR_MAX['b'])} 로 **{PAIR_MAX['max_dev_pct']:.1f} %**.",
f"- 똑같이 나온 {len(V3S['identical_pairs'])}쌍({PAIR_IDENT})은 **선언된 대리**다 — "
"phantom4·x500v2 가 phantom3 의 평면형을 빌려 쓴다(§5c 표의 ⛔ 표시). "
"«우연히 같은» 것이 아니라 «같다고 적어 둔» 것이다.",
"- 잣대: x = r 평면 단면의 **최대 캘리퍼**(회전 불변이라 비틀림과 무관), 격자 0.10~0.99R.",
"",
VERTBL,
"",
f"↑ «형상편차 주대역» 은 법칙 곡선과 지어진 날의 폭이 주대역(뿌리 밴드 제외)에서 얼마나 어긋나는가 "
f"— 허용 {VERJ['_meta']['tolerance']['shape_pct']:.0f} % 안이다. "
f"{drone_label('m350rtk')} 만 `resolution_limited` 로 적혀 있다(단면 격자가 이 크기의 프롭에서 "
"곡선을 다 못 따라간다는 자기신고이지 실패가 아니다).",
"",
"### 6.2 확정 — 지금 믿어도 되는 것",
"",
f"1. **회전 원반 지름** — 완성 메쉬에서 잰 프롭 지름은 공표값 대비 오차가 "
f"{drone_label('mavic4pro')} {PROP_ERR:+.5f} %, {len(ORDER)}기체 최대 절대오차 "
f"{PROP_ERR_MAX:.5f} % 다(정본 판 원장 §C_dims). 빌드가 **날을 지은 뒤 실제 최대반경을 재서 되돌리기** "
f"때문이다 — ⚠ 이 값은 «맞다» 가 아니라 **«맞춰 놓았다»** 로 읽어야 한다. "
f"인증서도 같은 축을 밖에서 조인다(프롭 지름 1 % · 대각 3 %, 경계 대조에서 +0.9 % 통과 / "
f"+1.1 % 실패) ← `docs/MESH_CERTIFICATE.md` §2 G7. **그 «맞추기» 의 대가는 아래 6.2b 에 있다.**",
f"2. **피치 곡선** — 비틀림 θ(r) 이 공표 피치 P 하나에서 θ(r)=atan(P/2πr) 로 유도된다(§4). "
f"허브 쪽 피치각이 {drone_label('mini5pro')} {ROWS['mini5pro']['th_hub']:.0f}° ~ "
f"{drone_label('mavic4pro')} {ROWS['mavic4pro']['th_hub']:.0f}° 로 갈리는 **기종별 개성**이 "
f"메쉬에 그대로 실린다.",
"3. **카이럴성(손대칭)** — CW/CCW 가 서로 거울상으로 지어지고, 로터별 비틀림 방향이 회전방향과 "
"맞는지를 검사가 본다. 10/10 통과이고 지표 |h| 는 0.16~0.29(문턱 0.05), 양성 대조 32/32 "
"← `docs/MESH_CERTIFICATE.md` §2 G5.",
"4. **프롭이 모터 벨 속에 박혀 있지 않다** — 솔리드 내부판정으로 10/10(선언 예외 4기체), "
"양성 대조 새로 심음 ← 같은 인증서 G8.",
"5. **프롭 어셈블리의 기하 건강** — 전 기종 수밀, 중복면 0, 안쪽 법선 0 "
"← `docs/MESH_AUDIT_0816.md` §③.",
"",
"⛔ **여기서 장담이 끊기는 자리도 인증서가 적어 둔다.** 마이크로도플러가 쓰는 것은 «날이 조금씩 "
"돌아간 메쉬 여러 장»(분절)인데, 그 축은 «정본과 정점이 1 나노미터 안에서 같은가»(자세 재현)만 "
"보고 **일부러 결함을 심어 보는 양성 대조가 없다** — 즉 «검사가 실제로 무는가» 가 확인되지 "
"않은 축이다 ← `docs/MESH_CERTIFICATE.md` §3.6 · §1②(양성 대조가 없는 축 여섯 중 하나).",
"",
"### 6.2b 지름을 «맞춰 놓는» 대가 — 지어진 날이 법칙보다 약 2 % 작다",
"",
"지어진 날의 최대시위는 법칙값보다 조금 작다(위 §6.1 표의 «실현비» 열). 원인 둘 다 "
"**의도된 것**이고 크기가 재어져 있다:",
"",
V5TBL,
"",
"- **스윕디스크 정규화** — 팁이 뒤로 휘어 있어(시미터 스큐) 스팬을 R 로 잡으면 실제 최대반경이 "
"R 을 넘는다. 그래서 지어서 재고 0.991~0.992 배로 되돌린다. 이것이 «프롭 지름 오차 0» 의 정체다 "
"— 지름을 맞추는 대신 날이 그만큼 짧아진다.",
"- **로프트 재샘플** — 단면 외곽선을 36점으로 다시 깔면서 앞·뒷전 꼭짓점을 스쳐 둘레비가 "
"0.99 급이 된다(단면 점 수를 288 로 올리면 회복된다).",
"",
"둘 다 옛 판에도 똑같이 걸리므로 «옛 판 → 정본» 변화율(§5c 표)에는 안 들어간다 "
"← 출처: `outputs/prop_law_verify_0816.json` V5.",
"",
"### 6.3 방향이 정당한 근거 — 그리고 ⛔되살리면 안 되는 문장 다섯",
"",
"«기체별 순정 프롭으로 간다» 는 판단을 떠받치는 것은 다음 넷이다. 넷 다 **반증을 시도했고 "
"살아남았다** ← 출처: `outputs/mesh_adversarial_verdict_0816.json`.",
"",
"- 옛 날은 **외곽이 실물보다 좁다** — 0.60~0.96R 면적비 0.66(세 독립 잣대가 0.659/0.660/0.663 으로 0.6 % 안에서 일치). "
"⚠ 이 0.66 을 dB 로 옮긴 −3.66 은 **면적비의 dB 이지 σ 가 아니다**(§5c 의 R1 단서와 같은 이유).",
"- **시위 정점이 안쪽**이다 — 옛 판 0.31R ↔ 실물 0.45R.",
"- **`c_max/R` 이 실물마다 1.54 배**로 갈린다 — 저장소 참조 프롭 7종에서 0.177~0.273 이고, "
"실측 프로펠러 132종 모집단으로 넓히면 0.1529~0.3896(중앙값 0.1875)이다. 즉 «전 기종 한 값» 은 "
"근거가 없다.",
"- «이건 측정법 인공물이다» 라는 반증을 실제로 시도했고 **실패했다** — 스윕각 Λ 를 재서 "
"cosΛ 보정을 넣어도 0.70R 시위비가 0.6514 → 0.6499 로 거의 안 움직인다. 반경 정의를 바꿔도, "
"저폴리 간략화를 의심해 제품사진·FCC 실물사진으로 갈아 봐도 같은 방향이 나왔다.",
"",
"⛔ **다음 다섯 문장은 무너졌다. 근거로 다시 쓰면 안 된다**(같은 판결 원장):",
"",
"| 무너진 문장 | 실제 |",
"|---|---|",
"| 「날 면적이 −29 %(−2.97 dB)」 | 공통 창으로 재면 **−20~−24 %**. −29 % 는 우리 날만 0.175R 부터 "
"자르고 실물은 통째로 적분해서 나온 값이다 |",
"| 「DJI 날은 0.175R 부터 시작한다」 | 실측 **0.033R** 부터 있다(날 8장 전부) |",
"| 「3DR Solo 는 참조 중 유일한 이상치」 | 참조가 2:1 로 갈린다 — Holybro 1345 가 오히려 더 "
"뿌리 편중형이다. 앵커를 DJI 로 옮기는 진짜 이유는 «실증 표적이 DJI 기체» 라는 것 |",
"| 「c_max/R 은 프롭 크기와 반비례한다」 | 스피어만 **−0.05**. 우리 함대 크기급(8~13 in)에서는 "
"유의하지 않다 ⇒ ⛔ **크기 스케일링으로 빈칸을 채우면 안 된다** |",
"| 「메쉬 두께 실측 1.456 mm(정본보다 +1.8 %)」 | 부피 항등식으로 재면 1.396 mm(**−2.4 %**) — "
"부호가 반대다. 두께는 «정의» 를 못 박기 전에는 잴 수 없다 |",
"",
"### 6.4 검사 예산도 법칙별로 갈렸다",
"",
"프로펠러를 기체마다 다시 뜨면 **검사가 세는 숫자도 달라진다**. 그래서 두 예산은 이제 "
"«어느 날 법칙이냐» 까지 키로 갖는다 ← `src/mesh_check.py`.",
"",
"**⑴ 씨접합 슬리버**(`SLIVER_BUDGET_BLADE_LAW`) — 아주 가느다란 삼각형의 개수다. "
"평면형이 달라지면 로프트가 다시 떠지므로 이 수가 움직인다. 결함이 는 것이 아니라 **다른 형상**이고, "
"그 판단의 근거는 같은 판에서 «법선 안쪽·winding 깨짐·퇴화면·경계 모서리» 가 **전 기체 0** 이라는 "
"것이다(즉 불리언은 정상이다). 슬리버의 면적 비중은 0.0001~0.03 % 라 σ 로는 무해하다.",
"",
SLIVER_TBL,
"",
"**⑵ 프롭↔모터 벨 관통**(`PROP_BELL_SOLID_AREA_PCT_BLADE_LAW`) [%] — 이쪽은 슬리버와 달리 "
"**진짜 이중계상 면적**이라 늘어난 것을 그냥 넘기면 안 된다. 두 기체가 늘었고, 둘 다 원래부터 "
"«설계인지 결함인지 미판정» 으로 선언돼 있던 자리다(모터 상부 커버가 프롭 위를 덮는 구조 · "
"허브 보어 관통). 정본 날은 **뿌리 시위가 달라 그 겹침이 0.4 pp 커졌다**. 진짜로 닫으려면 "
"뿌리 형상 자체를 고쳐야 하는데 그 근거(허브 실측)가 없어서, 지금은 **크기를 적어 두고 넘긴다.**",
"",
BELL_TBL,
"",
"⭐ **예산을 정하는 규약** — 값은 «실측 + 약 10 %» 로만 두고 실측치를 괄호에 남긴다. "
"«예산을 올려 통과시킨다» 는 인증서가 경고한 안티패턴이기 때문이다 — 인증서는 예산 근처 57행이 "
"전부 80 % 이상 소진돼 있고 그중 56행이 «오늘 이만큼이다» 라는 **선언 스냅샷**이라고 적으며, "
"«예산이 완화되면 인증은 그 순간 무효» 라고 못 박는다 ← `docs/MESH_CERTIFICATE.md` §1③·§5. "
"위 표의 실측/예산 비가 그 규약을 지키는지 눈으로 확인할 수 있다.",
"",
"### 6.5 아직 빈 칸 — 두께",
"",
f"두께는 **여전히 전 기종 공용 상수**다(`TC_ROOT`={_DC.TC_ROOT:.3f} → `TC_TIP`="
f"{_DC.TC_TIP:.3f}). 기체별 두께 칸은 레지스트리에 있지만 `_blade` 가 읽지 않는다.",
"",
"**왜 못 채우나** — 사진으로는 원리적으로 못 잰다. 비틀린 날을 옆에서 보면 겉보기 높이가 "
"c·sinβ + t·cosβ 라 **앞항(시위 몫)이 두께의 다섯 배쯤** 되어, 두께는 그 안에 묻힌다. "
f"그래서 근거가 있는 기체가 {len(T_HAVE)}/{len(ORDER)}뿐이다:",
"",
"| 기체 | 등급 | 잰 것 | 단서 |",
"|---|---|---|---|",
*[f"| {drone_label(k)} | **[{L['grade']}]** | "
  + (f"평균 두께 {L['t_mm']:.3f} mm" if L.get("t_mm") else "절대 두께[mm] 없음")
  + (" · " if L.get("tc_max") else "")
  + (f"두께비 t/c {L['tc_max']:.3f}" if L.get("tc_max") else "")
  + " | " + " ⚠ ".join(x for x in (L.get("t_note_ko"), L.get("caveat_ko")) if x) + " |"
  for k, L in T_HAVE],
"",
"나머지 8기체는 **빈칸으로 둔다** — 빈칸이 가짜 값보다 낫다.",
"",
f"⚠ 그리고 그 두 표본조차 서로 갈린다 — mini2 중앙부 t/c 0.055~0.058 ↔ typhoonh480 "
f"0.086~0.128 이고, 코드의 공용 상수(루트 {_DC.TC_ROOT:.3f} → 팁 {_DC.TC_TIP:.3f})는 그 "
f"사이에 있다. 표본 둘로는 «공용 상수가 맞다» 도 «틀리다» 도 말할 수 없다. "
f"두께가 σ 로 얼마나 무거운 축인지는 재질 편(mesh06 §6.5)이 다룬다.",
"",
"아래 셀이 **기체별 법칙을 코드에서 직접 읽어** 최대시위를 재계산한다 — 표의 숫자가 "
"레지스트리에서 나온다는 것을 눈으로 확인할 수 있다.",
),

code(
f"""# 기체별 날 법칙을 **코드에서 직접** 읽는다 — 이 편의 표에 손으로 적은 숫자가 없다는 확인
import sys, os, numpy as np
sys.path.insert(0, os.path.abspath("../src"))
from drones import DRONES
from drone_cad import resolve_chord_max_over_r, resolve_chord_profile
from geom import blade_law_canon, mesh_fix_set

LAW = blade_law_canon()                       # 지금 쓰는 날 법칙 (환경변수 없으면 정본)
print(f"정본 날 법칙 = {{LAW}}   메쉬 수리 = {{sorted(mesh_fix_set()) or 'none'}}\\n")

for key in {ORDER!r}:
    s = DRONES[key]
    R = s.prop_dia_mm / 2000.0                                  # 반경[m] ← 스펙
    cmax, why = resolve_chord_max_over_r(s, LAW)                # 그 기체의 c_max/R + 출처
    rr, fr, prof = resolve_chord_profile(s, LAW)                # 그 기체의 평면형 곡선
    peak = rr[int(np.argmax(fr))] if rr else float('nan')       # 시위가 최대가 되는 r/R
    print(f"{{s.name:16s}} R={{R*1000:5.1f}} mm  c_max/R={{cmax:.4f}}  "
          f"최대시위 {{cmax*R*1000:5.1f}} mm  정점 {{peak:.2f}}R   [{{s.prop_law_grade}}] "
          f"{{s.prop_law_model}}")

# 옛 판과 견주려면(비트동일 재현): BLADE_LAW=legacy 로 돌리면 위가 전부 0.25 한 값으로 돌아간다
print("\\n옛 판:", resolve_chord_max_over_r(DRONES['mini2'], 'legacy'))""",
),

# ------------------------------------------------------- 14. §6 카이럴
md(
"## 7. CW/CCW 카이럴성 — \"거울대칭 깨짐\"이 곧 프로펠러 물리다",
"",
"> **지금 메쉬가 하는 일** — 실물 멀티로터는 반대로 도는 로터에 **거울상 프롭**을 단다"
"(스윕 방향과 피치 부호가 함께 뒤집힌다). 우리 빌드도 그렇게 짓는다: `build_drone()` 이 기준 형상"
"(CCW) 한 벌과 `build_propeller(spec, mirror=True)` 로 만든 거울상(CW) 한 벌을 짓고, "
"`rotor_layout()` 의 `dir` 부호에 따라 로터마다 골라 배치한다 ← 출처: `src/drones.py` `build_drone()`. "
"그래도 아래 표의 full p95 가 0 이 되지는 않는다 — 거울상을 달아도 **장착 위상(base_ang)** 이 "
"로터마다 달라 어느 순간의 스냅샷은 좌우 거울상이 아니기 때문이다. 남는 것이 진짜 카이럴성이다.",
"",
"검증 스위트에는 좌우대칭 검사(`B_symmetry`)가 있다: 드론 표면 점구름을 y→−y 로 거울 반전시켜 "
"원본과의 chamfer 거리를 잰다. 비행 안정을 위해 기체는 좌우대칭이어야 하니, 대칭이 맞다면 거리는 "
"샘플 간격 수준(~mm)이어야 한다. 결과가 흥미롭다:",
"",
SYM,
"",
f"↑ 출처: `report_mesh/outputs/mesh_verify_canon_0817.json` §B_symmetry(정본 판, "
f"`MESH_FIX={CANON_FIX_S}` · `BLADE_LAW={CANON_LAW}`). 측정 함수는 시리즈 원장과 같은 "
"`verify_mesh_suite.sec_B_symmetry`(점 간격 4 mm, y 미러 chamfer)다.",
"",
"프레임만 재면(frame_only) p95 가 2 mm 아래 — 기체는 확실히 좌우대칭이다. 그런데 프로펠러를 "
"포함하면(full) p95 가 수십 mm 로 뛴다. 결함일까? 아니다 — 검증 코드의 docstring 이 "
"먼저 답을 적어 두었다:",
"",
"> \"⚠ 프로펠러는 **카이럴**(CW/CCW 쌍 + 스큐 날) — y 미러가 날개 위상·회전방향을 뒤집으므로 "
"full 의 큰 p95 는 결함이 아니라 프로펠러 물리다. 기체 대칭성은 frame_only 로 판정한다.\" "
"← 출처: verify_mesh_suite.py.",
"",
"피치로 비틀린 날은 나사못처럼 **오른손/왼손이 구분되는(카이럴)** 물체다. 거울에 비추면 반대 "
"손의 날이 되는데, 그런 날은 그 자리에 없으니 가장 가까운 표면까지 수십 mm 가 뜬다. 실물도 "
"그렇다: 멀티로터는 반토크 상쇄를 위해 CW 프롭과 CCW 프롭을 **다른 부품**으로 만들어 대각쌍끼리 "
"같은 방향으로 돌린다(S1000+ 는 매뉴얼에 M1/3/5/7=CCW, M2/4/6/8=CW 로 명시 ← 출처: "
"docs/drone_specs_2026.json `rotor_directions`·DJI S1000 User Manual v1.10 p.10; Phantom 4 는 "
"검정/은색 캡 두 종, 9450 프롭 \"two CW + two CCW\" ← docs/SPECS.md §Phantom 4). 우리 "
"시뮬레이션에서 회전 방향은 `rotor_layout()` 의 `dir=+1/−1`(대각쌍 동일) 관례로 들어간다 "
"← 출처: src/drones.py.",
"",
"> **현재 한계** — 우리가 짓는 것은 «대각쌍끼리 같은 방향» 이라는 **상대** 관계뿐이다. "
"어느 로터가 실제로 CW 인지 — 즉 기체의 **절대 손방향** — 은 DJI 가 Mini/Mavic 에 대해 문서로 "
"공개하지 않는다(← docs/drone_specs_2026.json `rotor_directions` \"미확인\"). 그래서 우리 배치는 "
"실물과 **통째로 거울상**일 수 있고, 그 경우 방위각 패턴의 좌우가 뒤집힌다. 지금은 "
"\"대각쌍 동일 회전\" 제약만 지키는 것이 근거 가능한 최선이다.",
"",
"이 표는 이 편의 제목을 수치로 요약한다: **판때기였다면 크게 나지 않았을 거울대칭 깨짐이, "
"진짜 날개라서 수십 mm 로 찍힌다.** 형상이 물리를 담기 시작했다는 뜻이다.",
"",
"> ⚠ **회전축 규약에 열린 자리가 하나 있다.** 우리는 로터 축을 월드 좌표축에 세워 짓는다. "
"그런데 참조로 쓰는 DJI 공식 3D 자산에서 **실제 로터 축은 그 축과 나란하지 않다** — 앞 로터 "
"2.97° · 뒤 로터 5.00° 기울어져 있다(서로 다른 추정기 셋이 같은 값을 준다) "
"← 출처: `outputs/mesh_adversarial_verdict_0816.json` `judge_own_measurements.glb_rotor_axis`. "
"⇒ 레지스트리 `mini2` note 의 «뒷 로터는 코닝 틸트 때문에 두 날의 피치가 갈린다» 는 서술은 "
"**축을 세워 놓고 잰 인공물일 가능성이 크다**(축을 제대로 잡으면 한 로터의 두 날 기울기가 "
"17.487° ↔ 17.489° 로 같아진다). 그 note 를 근거로 무언가를 다시 쓰기 전에 재검사할 것.",
),

# ------------------------------------------------------- 15. 요약
md(
"## 8. 정리 — 이 편에서 확인한 것",
"",
f"1. 프로펠러는 γ={MAV['gamma_prop']:g} 의 약한 산란체지만, 블레이드 플래시 "
f"{min(r['flash'] for r in ROWS.values()):.0f}~{max(r['flash'] for r in ROWS.values()):.0f} Hz· "
f"팁 도플러 ±{min(r['ftip_khz'] for r in ROWS.values()):.1f}~"
f"±{max(r['ftip_khz'] for r in ROWS.values()):.1f} kHz(@{FC:g} GHz)의 유일무이한 지문을 만든다 — "
f"그래서 모양을 제대로 만들어야 한다 (§1 — 결과는 본편 권 6 으로 이어진다).",
"2. 단면은 NACA-4 공식 하나(+코사인 클러스터링), 비틀림은 스펙 피치 P 하나에서 "
"θ(r)=atan(P/2πr) 로 — 임의 조형이 아니라 **공개 스펙에서 유도**된다 (§3~4).",
f"3. 평면형은 **기체마다 그 기체의 순정 프롭**이다(`BLADE_LAW_CANON = \"{CANON_LAW}\"`). "
f"`c_max/R` 이 {min(LAW[k]['c_max_over_R'] for k in ORDER):.3f}~"
f"{max(LAW[k]['c_max_over_R'] for k in ORDER):.3f}, 시위 정점이 0.25R~0.55R 로 갈리고, "
f"칸마다 등급([A]~[D])과 단서가 붙어 있다 (§5c).",
f"4. 지어진 메쉬로 되재면 {V3S['pairs']}쌍 중 **{V3S['distinct_over_1pct']}쌍이 1 % 넘게 "
f"구별**되고(최대 {PAIR_MAX['max_dev_pct']:.1f} %), 똑같은 {len(V3S['identical_pairs'])}쌍은 "
f"선언된 대리다. 회전 원반 지름 오차는 {PROP_ERR:+.5f} %(맞춰 놓은 값), 그 «맞추기» 가 "
f"날을 약 2 % 줄인다는 것까지 재어져 있다 (§6).",
f"5. 프로펠러 포함 시 거울대칭 chamfer p95 가 최대 {max(r['sym_full_p95'] for r in ROWS.values()):.0f} mm "
f"까지 뛰는 것은 결함이 아니라 **카이럴 날개의 물리**다 — 대칭 판정은 frame_only 로 (§7).",
f"6. 빈 칸은 **두께 하나**다 — 전 기종 공용 상수이고, 실측 근거가 있는 기체가 "
f"{len(T_HAVE)}/{len(ORDER)}뿐이다. 사진으로는 원리적으로 못 잰다 (§6.5).",
),

# ------------------------------------------------------- 16. 재현 + 다음
md(
"## 재현 방법",
"",
"```bash",
"# 1) 정본 판 형상 원장(mesh_verify_canon_0817.json) 재생성 — 이 편의 형상 수치는 전부 여기서 온다",
"cd /workspace/sionna",
"PYTHONPATH=src:benchmark /workspace/.venvs/py312/bin/python \\",
"    report_mesh/src/verify_mesh_canon_0817.py",
"",
"cd /workspace/sionna/report_mesh",
"# 2) 옛 세대 원장(mesh_verify.json) 재생성 — 재질 γ 등 정본 전환과 무관한 값",
"/workspace/.venvs/py312/bin/python src/verify_mesh_suite.py",
"# 3) 그림(outputs/figures/airfoil_profile.png 포함) 재생성",
"/workspace/.venvs/py312/bin/python src/viz_mesh_reports.py",
"# 4) 이 노트북 재생성",
"/workspace/.venvs/py312/bin/python src/make_mesh05.py",
"```",
"",
"날 법칙 자체를 다시 만들거나 되재려면(둘 다 CPU·GPU 안 씀):",
"",
"```bash",
"cd /workspace/sionna",
"# 기체별 법칙 원장 재생성",
"PYTHONPATH=src:benchmark /workspace/.venvs/py312/bin/python \\",
"    benchmark/prop_law_by_airframe_0816.py",
"# 지어진 메쉬로 되잰 검증 재생성",
"PYTHONPATH=src:benchmark /workspace/.venvs/py312/bin/python \\",
"    benchmark/verify_prop_law_per_airframe_0816.py",
"# 메쉬 봉인 대조 — 형상이 어제와 같은가 (약 9 초)",
"PYTHONPATH=src:benchmark /workspace/.venvs/py312/bin/python benchmark/mesh_certify.py",
"```",
"",
f"⛔ **옛 판을 그대로 보고 싶으면** 앞에 `MESH_FIX=none BLADE_LAW=legacy` 를 붙인다 — "
f"비트동일로 재현된다. 정본으로 낸 산출물에는 파일명 꼬리표 `{FILE_TAG}` 가 붙으므로 "
f"두 판의 파일이 섞이지 않는다.",
"",
"**다음 편** → `mesh06_materials.ipynb` (같은 폴더): 색이 곧 재질 — 부위별 전파 재질 입히기. 검증은 "
"이어진다. 마이크로도플러 **결과**가 궁금하면 본편 권 6(`reports/06_3_pattern.ipynb`) 으로.",
),
]

nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "py312",
      "language": "python", "name": "py312"}, "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 5}
out = os.path.join(RM, "mesh05_propeller.ipynb")
for _i, _c in enumerate(nb["cells"]):
    _c["id"] = f"m05-{_i:02d}"

json.dump(nb, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("wrote", out, len(cells), "cells")
