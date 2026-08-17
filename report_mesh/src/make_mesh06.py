# -*- coding: utf-8 -*-
"""make_mesh06.py — mesh06 ipynb 생성기. ⚠ 이 파일이 소스다.

mesh06 — "색이 곧 재질 — 부위별 전파 재질 입히기"
  · 모든 수치는 outputs/mesh_verify.json (E_materials·A_geometry·meta) 에서 읽어 f-string 주입.
  · 재질/색 정의는 src/drones.py (DRONE_GROUP_MAT·MATERIAL_COLOR) 와 src/materials.py 에서 import.
  · 배정 그림: material_legend.png, wireframe_matrice4e.png (다른 리포트와 중복 금지).
"""
import json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
RM = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(RM, ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
V = json.load(open(os.path.join(RM, "outputs", "mesh_verify.json"), encoding="utf-8"))

# drones.py 는 numpy/geom 만 필요(가벼움). materials.py 는 sionna 를 import 하므로 여기선 안 부른다
# — 대신 벌크 프레넬은 materials.gamma_bulk 와 **같은 공식**(materials.py)을 그대로 재현해 계산.
from drones import DRONES, DRONE_GROUP_MAT, MATERIAL_COLOR, drone_label
sys.path.insert(0, HERE)
import mesh_facts_0816 as MF  # noqa: E402  (2026-08-16 원장 공용 로더)

EM = V["E_materials"]
from mesh_ledger import ledger_order   # noqa: E402  (원장↔레지스트리 일치 강제)
ORDER = ledger_order(V)                           # = DRONES 레지스트리 전수
FC_GHZ = V["meta"]["fc_ghz"]
LAM_MM = V["meta"]["lam_hi_mm"]

# --- gamma_map 은 전 기종 동일해야 한다(재질 규칙이 드론 공통이므로) — 생성 시점에 검증 ---
GM = EM[ORDER[0]]["gamma_map"]
for k in ORDER[1:]:
    assert EM[k]["gamma_map"] == GM, f"gamma_map differs for {k}"
ALL_COVERED = all(EM[k]["all_covered"] for k in ORDER)
UNCOVERED_TOTAL = sum(len(EM[k]["uncovered"]) for k in ORDER)
assert ALL_COVERED and UNCOVERED_TOTAL == 0

def db(g):                                        # 진폭 |Γ| → 반사 '전력'비 dB (20·log10)
    return 20.0 * math.log10(g)

# --- 벌크 프레넬 |Γ| (materials.py gamma_bulk 와 동일 공식·동일 입력) --------------------
EPS0 = 8.8541878128e-12
def gamma_bulk(eps_r, sigma, fc=FC_GHZ * 1e9):
    eps_c = complex(eps_r, -sigma / (2 * math.pi * fc * EPS0))
    s = eps_c ** 0.5
    return abs((1 - s) / (1 + s))

G_PLASTIC_BULK = gamma_bulk(2.7, 0.02)            # materials.py 'plastic' (εr=2.7, σ=0.02)
G_CARBON_BULK = gamma_bulk(5.0, 3.0e3)            # materials.py 'carbon'  (εr=5.0, σ=3e3)
CAM_MISMATCH_DB = db(GM["camera"]) - db(G_PLASTIC_BULK)   # camera 를 plastic 으로 뒀다면 생길 어긋남 크기

# --- 색 헥사코드 + HTML 색칩 ---------------------------------------------------------
def hexc(rgb):
    return "#%02X%02X%02X" % tuple(int(round(c * 255)) for c in rgb)

def chip(mat):
    return (f'<span style="display:inline-block;width:14px;height:14px;'
            f'background:{hexc(MATERIAL_COLOR[mat])};border:1px solid #666;'
            f'vertical-align:middle"></span>')

# --- 그룹이 어느 드론 메쉬에 실재하나 (E_materials.groups 에서) -------------------------
PRESENCE = {g: [k for k in ORDER if g in EM[k]["groups"]] for g in DRONE_GROUP_MAT}
#  ⭐ 2026-07-30 (Phase 3): 5종 하드코딩 사전이라 원장에 기종이 늘면 `SHORT[k]` 가 **KeyError**
#     로 죽었다. 짧은 약칭은 손으로 고른 것이라 이름에서 유도할 수 없으므로 **override + 폴백**
#     구조로 둔다(폴백 = `drones.drone_label`). 기존 5종의 표 문자열은 그대로다.
_SHORT_OVERRIDE = {"mini5pro": "Mini5", "mavic4pro": "Mavic4", "matrice4e": "M4E",
                   "s1000plus": "S1000+", "phantom4": "P4"}
SHORT = {k: _SHORT_OVERRIDE.get(k, drone_label(k)) for k in ORDER}

MAT_KO = {"prop_plastic": "프로펠러 플라스틱(얇은 날개)", "plastic": "플라스틱(ABS/PC)", "carbon": "탄소섬유(CFRP)", "metal": "금속(ITU)",
          "camera_assembly": "카메라 조립품", "pcb": "PCB(FR-4+구리)"}

# --------------------------------------------------------- 정본 스위치(코드에서 읽는다)
import geom as _GEOM                          # noqa: E402  (정본 수리·날 법칙의 유일한 자리)
CANON_FIX = tuple(sorted(_GEOM.mesh_fix_set()))
CANON_LAW = _GEOM.blade_law_canon()
CANON_FIX_S = ",".join(CANON_FIX) if CANON_FIX else "none"

# --------------------------------------------------------- 정본 판 원장 (2026-08-17)
#  ⭐ 재질 원장(2026-08-16 13:15 세대)은 정본 전환 **이전** 메쉬에서 나왔다. 면적처럼 형상이
#     정하는 값은 **정본 판 원장**에서 읽고, 재질 규칙(배정·|Γ|)만 옛 원장에서 읽는다.
#     ⚠ 원장의 스위치가 지금 스위치와 다르면 여기서 죽는다 — 다른 판의 수를 싣지 않으려고.
import numpy as np                             # noqa: E402
from drones import build_drone                 # noqa: E402
sys.path.insert(0, os.path.join(ROOT, "benchmark"))
from mesh_internal_metal_check import check_drone   # noqa: E402  (원장을 만든 그 함수)

CANON = json.load(open(os.path.join(RM, "outputs", "mesh_canon_0817.json"), encoding="utf-8"))
_CM = CANON["_meta"]
assert tuple(sorted(_CM["mesh_fix"])) == CANON_FIX and _CM["blade_law"] == CANON_LAW, (
    f"정본 원장({_CM['mesh_fix']}·{_CM['blade_law']})이 지금 스위치와 다르다 — "
    f"report_mesh/src/mesh_canon_0817.py 를 다시 돌릴 것")
CAN = {k: dict(faces=v["n_faces"], verts=v["n_verts"], groups=v["n_groups"])
       for k, v in CANON["per_drone"].items()}
AREA_CANON = {}                                 # 그룹 → 함대 합계 면적 [mm²] (정본 판)
for _k, _v in CANON["material_weighted"].items():
    for _g, _x in _v["groups"].items():
        AREA_CANON[_g] = AREA_CANON.get(_g, 0.0) + float(_x["area_mm2"])

#  ⭐ «정본 전환만의 몫» 을 정확히 가르려면 옛 판도 같은 자로 재야 한다(추측 금지).
#     스위치는 호출 시점에 환경변수를 읽으므로 잠깐 옛 판으로 돌려 짓고 되돌린다.
_env_bak = (os.environ.get("MESH_FIX"), os.environ.get("BLADE_LAW"))
os.environ["MESH_FIX"], os.environ["BLADE_LAW"] = "none", "legacy"
AREA_LEGACY = {}
for _k in ORDER:
    _m = build_drone(DRONES[_k])
    _V = np.asarray(_m.v, float)
    _F = np.asarray(_m.f, int)
    _G = np.asarray(_m.g)
    _a = np.linalg.norm(np.cross(_V[_F[:, 1]] - _V[_F[:, 0]],
                                 _V[_F[:, 2]] - _V[_F[:, 0]]), axis=1) / 2.0 * 1e6
    for _g in set(_G):
        AREA_LEGACY[_g] = AREA_LEGACY.get(_g, 0.0) + float(_a[_G == _g].sum())
for _name, _val in zip(("MESH_FIX", "BLADE_LAW"), _env_bak):
    if _val is None:
        os.environ.pop(_name, None)
    else:
        os.environ[_name] = _val
assert _GEOM.mesh_fix_set() == set(CANON_FIX) and _GEOM.blade_law_canon() == CANON_LAW
#  정본 전환으로 **실제로** 움직인 그룹만 고른다(0.05 % 이상).
MOVED = sorted((g for g in AREA_CANON
                if abs(AREA_CANON[g] - AREA_LEGACY[g]) / AREA_LEGACY[g] > 5e-4),
               key=lambda g: -abs(AREA_CANON[g] - AREA_LEGACY[g]))

#  커버리지 표는 «그룹 라벨» 축이라 형상이 바뀌어도 안 움직여야 한다 — 정본 판에서 확인한다.
#  (`drone_gamma_map` 은 Sionna 씬을 열어 GPU 를 요구하므로 부르지 않는다. 여기서 보는 것은
#   «메쉬에 실재하는 그룹 라벨이 배정표 키로 덮이는가» 뿐이고, 그것이 커버리지 검사의 정의다.)
GROUPS_CANON = {k: sorted(CANON["per_drone"][k]["groups"]) for k in ORDER}
GROUPS_CANON_SAME = all(GROUPS_CANON[k] == list(EM[k]["groups"]) for k in ORDER)
UNCOVERED_CANON = sorted({g for k in ORDER for g in GROUPS_CANON[k]
                          if not any(g == kk or g.startswith(kk + "_")
                                     for kk in DRONE_GROUP_MAT)})

#  «내부 금속이 정말 셸 안인가» — 판정은 정본 원장에서 읽고, «얼마나 나왔나» 는 원장을 만든
#  그 함수로 여기서 재서 덧붙인다(판정이 어긋나면 assert 로 멈춘다).
INTMETAL = {k: check_drone(k) for k in ORDER}
for _k in ORDER:
    assert INTMETAL[_k]["verdict"] == CANON["internal_metal"][_k]["verdict"], (
        f"{_k}: 내부금속 판정이 원장과 다르다 — 원장을 다시 만들 것")
_IM_MEAN = {"PASS": "금속 상자가 전부 셸 안에 있다",
            "FAIL": "금속 상자의 일부가 셸 **밖**으로 나와 있다",
            "N/A": "설계상 열린 프레임이라 «셸 안» 이라는 물음이 성립하지 않는다",
            "UNKNOWN": "셸이 닫혀 있지 않아 안/밖 판정 자체가 정의되지 않는다"}

A_M4E = dict(n_faces=CAN["matrice4e"]["faces"], n_groups=CAN["matrice4e"]["groups"])

def md(*lines):
    src = "\n".join(lines).splitlines(keepends=True)
    return {"cell_type": "markdown", "metadata": {}, "source": src or [""]}

def code(src_text):
    return {"cell_type": "code", "metadata": {}, "execution_count": None,
            "outputs": [], "source": src_text.splitlines(keepends=True)}

# ============================================================================ #
#  셀 구성
# ============================================================================ #
cells = []

# --- 1. 제목 + 경고 + 요약 + 용어풀이 ---------------------------------------------------
cells.append(md(
    "# mesh06 — 색이 곧 재질: 부위별 전파 재질 입히기",
    "",
    *MF.head_md(
        "mesh06",
        "부위마다 어떤 전파 재질을 배정했고, 그 배정 중 무엇이 근거를 갖고 "
        "무엇이 아직 **출처 없는 대표값**인가.",
        ["verify", "materials", "internal", "internal_check", "gimbal",
         "material_correction"],
        extra=[("docs/MESH_CERTIFICATE.md",
                "메쉬 인증서 — 재질 라벨 축(G10)은 장담, 재질 **물성값의 옳음**은 범위 밖(§3.6)")]),
    "",
    f"> ⚠ **원장 세대와 정본 설정** — 지금 메쉬는 `MESH_FIX_CANON = ({CANON_FIX_S})` · "
    f"`BLADE_LAW_CANON = \"{CANON_LAW}\"` 로 지어진다(← `src/geom.py`). 위 원장들은 그 전환 "
    f"**이전** 세대라, 이 편에서 **형상이 정하는 값(면 수·면적·«금속이 셸 안인가» 판정)은 이 "
    f"정본 판에서 다시 잰 원장** `report_mesh/outputs/mesh_canon_0817.json` 에서 읽고 그렇게 "
    f"표시한다. "
    f"재질 규칙 자체(배정표·\\|Γ\\|·두 엔진 갈림)는 정본 전환과 무관하므로 원장 그대로다.",
    "",
    f"**한 줄 요약** — 드론 3D 메쉬의 부위 그룹 {len(DRONE_GROUP_MAT)}개마다 전파 재질과",
    f"진폭 반사계수 |Γ|@{FC_GHZ:g} GHz 를 배정하고, **렌더 색을 재질과 1:1 로 묶어**",
    f"\"그림만 봐도 전파 물성이 보이게\" 만들었다. {len(ORDER)}종 전부에서 재질이 빠진 그룹은",
    f"**0개**(all_covered={ALL_COVERED}) ← 출처: `outputs/mesh_verify.json` §E_materials.",
    "",
    "이 편은 형상(mesh01~05)이 아니라 **표면 물성** 이야기다. 같은 모양이라도 표면이",
    "금속이냐 플라스틱이냐에 따라 레이더에는 전혀 다른 물체로 보인다 — 그 배정 규칙과",
    "근거, 그리고 재질 선택 하나가 왜 10 dB 급 무게를 갖는가(§5 카메라 사례)까지 다룬다.",
    "",
    "## 용어풀이",
    "",
    "| 용어 | 한 줄 뜻 |",
    "|---|---|",
    "| 전파 재질(radio material) | 시뮬레이터가 표면마다 갖는 전기적 성질(εr, σ). 렌더용 '색'과는 별개 개념 |",
    "| \\|Γ\\| (반사계수) | 전파가 표면에 부딪혀 **진폭이 몇 배로 반사**되는지. 1.0=완전 거울, 0=전부 통과/흡수 |",
    "| 반사 전력비 [dB] | 20·log10\\|Γ\\|. 예: \\|Γ\\|=0.28 → 약 −11 dB(반사 전력이 1/13) |",
    "| PO (Physical Optics) | 물리광학 — 표면 적분으로 RCS 를 계산하는 근사법. 우리 RCS 엔진(`src/rcs_po.py`) |",
    "| Sionna RT | NVIDIA 의 전파 레이트레이싱 시뮬레이터. 챔버 전파(멀티패스)를 계산 |",
    "| ITU-R P.2040 | 국제전기통신연합의 건축자재 전파물성 권고안 — Sionna 가 내장 |",
    "| εr (비유전율) / σ (전도도) | 재질의 전기적 성질. εr 는 전기장을 얼마나 저장하나, σ[S/m] 는 얼마나 전류가 흐르나 |",
    "| PEC | Perfect Electric Conductor(완전도체) — \\|Γ\\|=1.0 인 이상 금속 |",
    "| 프레넬(Fresnel) 반사 | (εr, σ) 에서 경계면 반사계수를 주는 고전 공식 |",
    "| 박막 간섭 | 얇은 층(드론 셸 **0.75 mm 급**)의 앞·뒷면 반사가 겹쳐 \\|Γ\\| 가 두께·파장에 따라 출렁이는 현상 |",
    "| CFRP / FR-4 | 탄소섬유강화플라스틱(암 소재) / PCB 기판 유리섬유 에폭시 |",
    "| 메쉬 그룹(group) | 메쉬 삼각형에 붙인 부위 라벨(body, prop, …). 재질 배정의 단위 |",
))

# --- 2. §1 왜 부위별 재질인가 ----------------------------------------------------------
cells.append(md(
    "## 1. 왜 '부위별' 재질인가 — 드론은 한 가지 재질이 아니다",
    "",
    "가장 쉬운 길은 드론 전체를 금속(PEC) 하나로 칠하는 것이다. 실제로 많은 RCS 예제가",
    "그렇게 한다. 우리는 그 길을 **버렸다**. 이유는 두 가지다.",
    "",
    "**(1) 실측 문헌이 재질 차이를 크게 본다.** Semkin 등(IEEE Access 2020)은 무반향",
    "챔버에서 드론 4종의 RCS 를 26–40 GHz 로 실측했는데, **탄소섬유 기체(Matrice M100)가",
    "플라스틱 기체(Mavic Pro·Phantom 4 Pro)보다 평균 RCS 가 약 7 dB 높았다**",
    "(plastic Mavic Pro −16.8~−15.0 dBsm vs carbon M100 −10.5~−6.6 dBsm).",
    "재질을 뭉개면 이 5배짜리 차이가 통째로 사라진다.",
    "← 출처: `refs/drone_papers/Semkin_2020_Drone_RCS_mmWave_IEEE_Access.md`",
    "(DOI 10.1109/ACCESS.2020.2979339).",
    "",
    "**(2) 플라스틱 드론의 반사는 셸이 아니라 '속'에서 나온다.** 우리 재질표 기준으로",
    f"플라스틱 셸의 반사계수는 \\|Γ\\|={GM['body']:.2f}(전력 {db(GM['body']):.1f} dB) 로 전파에 반투명하고,",
    f"모터·배터리 같은 금속 부품은 \\|Γ\\|={GM['motor']:.4f}(≈{db(GM['motor']):.2f} dB) 로 거의 완전 거울이다",
    "← 출처: `outputs/mesh_verify.json` §E_materials gamma_map. 그래서 우리 메쉬는 겉껍질만",
    "만들지 않고 **내부 배터리팩·PCB 를 금속 산란체로 함께 모델링**한다. 소스코드 주석 그대로:",
    "",
    "> \"내부 금속 산란체 (RCS 지배) — 셸 안이라 렌더엔 안 보이지만 PO/SBR 이 센다\"",
    "> ← 출처: `src/drone_cad.py` (배터리팩·PCB 박스를 동체 안에 넣는 코드의 주석)",
    "",
    "즉 부위별 재질은 장식이 아니라, **문헌이 보고하는 7 dB 급 차이를 재현하기 위한 최소",
    "조건**이다. 대안이었던 '전체 PEC' 는 플라스틱 기종의 RCS 를 크게 과대평가해 폐기했다.",
))

# --- 3. §2 재질 지도 그림 --------------------------------------------------------------
cells.append(md(
    "## 2. 재질 지도 한 장 — 색 = 재질 = 전파 물성",
    "",
    "아래 범례가 이 편의 핵심 요약이다. 왼쪽부터 **색 → 재질 → \\|Γ\\| → 이 재질을 쓰는",
    f"메쉬 그룹 → 물성의 출처** 순서로 읽는다. 이 규칙은 **{len(ORDER)}종 전부에 동일**하게 적용된다.",
    "",
    "![material legend](outputs/figures/material_legend.png)",
    "",
    f"*그림 1 — 재질 범례. \\|Γ\\| 수치는 {FC_GHZ:g} GHz 기준이고 `drone_gamma_map()` 이",
    "`materials.MATERIALS` 에서 유도한 값(그림 생성 코드: `report_mesh/src/viz_mesh_reports.py`,",
    "수치 검증: `outputs/mesh_verify.json` §E_materials).*",
))

# --- 4. §2.1 DRONE_GROUP_MAT 전체 표 ---------------------------------------------------
rows = []
for grp, (mat, desc) in DRONE_GROUP_MAT.items():
    who = "·".join(SHORT[k] for k in PRESENCE[grp]) if PRESENCE[grp] else "(셸형 암은 body 로 흡수)"
    rows.append(f"| `{grp}` | {desc} | `{mat}` ({MAT_KO[mat]}) | {chip(mat)} "
                f"| {GM[grp]:.2f} | {db(GM[grp]):+.1f} | {who} |")
cells.append(md(
    "### 2.1 부위 그룹 → 재질 배정표 (`DRONE_GROUP_MAT`) 전체",
    "",
    "부위→재질 배정은 `src/drones.py` 의 `DRONE_GROUP_MAT` **한 곳**에서만 한다.",
    "표의 한글 설명은 그 딕셔너리의 문자열을 그대로 가져온 것이고, \\|Γ\\| 는",
    f"`outputs/mesh_verify.json` §E_materials 의 gamma_map({len(ORDER)}종 모두 동일함을 생성 시",
    "검증했다)에서 읽었다.",
    "",
    f"| 그룹 | 부위(코드 원문) | 재질 | 색 | \\|Γ\\|@{FC_GHZ:g} GHz | 전력[dB] | 실재하는 기종* |",
    "|---|---|---|---|---|---|---|",
    *rows,
    "",
    "\\* '실재하는 기종' = 그 기종 메쉬에 실제로 그 그룹 삼각형이 있는가",
    "(← 출처: `mesh_verify.json` §E_materials groups). Mini5=Mini 5 Pro, Mavic4=Mavic 4 Pro,",
    "M4E=Matrice 4E, S1000+=S1000+, P4=Phantom 4.",
    "",
    "몇 가지 눈여겨볼 점:",
    "",
    f"- **`arm`(탄소섬유, \\|Γ\\|={GM['arm']:.2f})은 열린 프레임 {len(PRESENCE['arm'])}종에만 있다"
    f"({'·'.join(DRONES[k].name for k in PRESENCE['arm'])}).** 나머지 기종의 접이식/일체형",
    "  암은 플라스틱 셸의 연장이라 `body` 그룹으로 들어간다. 코드의 규칙 그대로 —",
    "  \"셸형 암(arm_style≠carbon)은 build_frame 이 'body' 그룹으로 넣으므로 자동으로",
    "  플라스틱이 적용된다\" ← 출처: `src/drones.py` (`drone_gamma_map` docstring).",
    "  §1 의 Semkin 실측(카본 기체가 밝다)과 정확히 같은 구도다 — 카본 프레임 S1000+ ↔ 카본 M100.",
    f"- **`battery`(\\|Γ\\|={GM['battery']:.2f})가 금속인 이유**는 표의 설명 그대로 \"GHz 에서 파우치",
    "  포일은 사실상 금속\"이기 때문이다 ← 출처: `src/drones.py`. LiPo 배터리의 알루미늄",
    "  파우치 포일은 파장(수 cm)보다 훨씬 넓고 연속된 도체면이다.",
    f"- **`camera` 는 단일 재질이 아니라 '조립품'**(`camera_assembly`, \\|Γ\\|={GM['camera']:.2f})이다.",
    "  금속 하우징+유리 렌즈+짐벌 모터의 복합체라서인데, 왜 전용 재질 한 항목으로 두는지는",
    "  §5 에서.",
))

# --- 5. §2.2 |Γ| 읽는 법 ---------------------------------------------------------------
cells.append(md(
    "### 2.2 \\|Γ\\| 숫자 읽는 법 — 거울, 반투명 유리, 그리고 그 사이",
    "",
    "\\|Γ\\| 는 '진폭' 반사계수라 감이 잘 안 올 수 있다. 전력으로 바꾸면(20·log10):",
    "",
    f"- 금속 \\|Γ\\|={GM['motor']:.4f} → {db(GM['motor']):.2f} dB ≈ **온전한 거울**. 들어온 전파를 거의 다 되돌린다.",
    f"- 탄소섬유 \\|Γ\\|={GM['arm']:.2f} → {db(GM['arm']):.1f} dB ≈ 거울의 8할. 사실상 금속처럼 행동한다.",
    f"- PCB \\|Γ\\|={GM['pcb']:.2f} → {db(GM['pcb']):.1f} dB, 카메라 조립품 \\|Γ\\|={GM['camera']:.2f} → {db(GM['camera']):.1f} dB.",
    f"- 플라스틱 \\|Γ\\|={GM['body']:.2f} → {db(GM['body']):.1f} dB ≈ **반투명 유리**. 전력 기준 8% 미만만 반사.",
    f"- 프로펠러 \\|Γ\\|={GM['prop']:.2f} → {db(GM['prop']):.1f} dB — 셸보다 더 얇아서 한 단계 더 어둡다.",
    "",
    f"(수치 ← 출처: `mesh_verify.json` §E_materials gamma_map, dB 는 여기서 환산)",
    "",
    f"직관 하나: 우리 **최고 대역**(WiFi 5.21 GHz)의 파장이 약 {LAM_MM:.1f} mm(주력 3.5 GHz 는 85.7 mm)",
    "← 출처: `mesh_verify.json` §meta lam_hi_mm(최고 대역 기준). 드론 셸 두께는 **정본 0.75 mm** 라"
"(DJI 공식 CAD 의 벽 두께 중앙값 0.704 mm 실측 ← `docs/MATERIAL_CORRECTION.md` D1) 파장의 백분의 1 급이라",
    "전파 입장에서 셸은 '벽'이 아니라 '비닐막'이다 — 그래서 얇은 부위일수록 \\|Γ\\| 를 더 낮게",
    "잡는다(§4.1 박막 간섭).",
))

# --- 6. code: JSON 직접 확인 -----------------------------------------------------------
cells.append(code(
    "# 본문 수치의 원본을 직접 확인한다 — outputs/mesh_verify.json §E_materials\n"
    "# (표준 라이브러리만 사용; 숫자를 손으로 옮겨적지 않기 위한 확인 셀)\n"
    "import json, math\n"
    "V = json.load(open('outputs/mesh_verify.json', encoding='utf-8'))\n"
    "EM = V['E_materials']\n"
    "gm0 = EM['" + ORDER[0] + "']['gamma_map']\n"
    "print(f\"gamma_map 이 전 기종({len(EM)}종)에서 동일한가: \"\n"
    "      f\"{all(EM[k]['gamma_map'] == gm0 for k in EM)}\")\n"
    "print(f\"{'group':10s} {'|Gamma|':>8s} {'power dB':>9s}\")\n"
    "for g, gam in gm0.items():\n"
    "    print(f'{g:10s} {gam:8.4f} {20*math.log10(gam):9.2f}')\n"
    "for k in EM:\n"
    "    e = EM[k]\n"
    "    print(f\"{k:10s} groups={len(e['groups'])}  uncovered={e['uncovered']}  \"\n"
    "          f\"all_covered={e['all_covered']}\")\n"
))

# --- 7. §3 색 규칙 ---------------------------------------------------------------------
color_rows = []
COLOR_STORY = {
    "metal":           "파랑 — 금속(모터·배터리 포일)",
    "plastic":         "밝은 회색 — 플라스틱(동체 셸·캐노피·착륙장치·식별색·**프로펠러**). 같은 재질 = 같은 색",
    # ⚠ 프롭은 얇아 실효 |Γ| 0.25(셸 0.28) — 색=재질(회색) 유지, |Γ|만 대표보정. 정밀 두께모델 아님(±2~3dB)
    "carbon":          "검정 — 탄소섬유(CFRP) 암",
    "camera_assembly": "주황 — 금속 하우징+유리 렌즈 **복합 조립품**(플라스틱도 금속도 아닌 별개 재질)",
    "pcb":             "초록 — FR-4+구리(별개 재질; 실물 솔더마스크 색이기도 하다)",
}
for mat, rgb in MATERIAL_COLOR.items():
    if mat not in COLOR_STORY:           # prop_plastic 등 = plastic 과 같은 색(별도 행 불필요)
        continue
    color_rows.append(f"| {chip(mat)} `{hexc(MATERIAL_COLOR[mat])}` | `{mat}` | "
                      f"RGB ({rgb[0]:.2f}, {rgb[1]:.2f}, {rgb[2]:.2f}) | {COLOR_STORY[mat]} |")
cells.append(md(
    "## 2.5 실제 재질 — 1차출처로 확인",
    "",
    "위 재질 배정은 상상이 아니라 **1차출처(제조사·teardown·FCC·RCS 측정논문)로 검증**했다:",
    "",
    "| 부위 | 실제 재질 | 확인 |",
    "|---|---|---|",
    "| 프로펠러 | **나일론 복합재**(Mavic 4 Pro 1158F · Matrice 4E 1157F) | ✅ DJI 공식 — 카본 아님 |",
    "| 배터리 | **Li-NMC 파우치 332 g**(단일 최대 밀집 금속) | ✅ DJI 공식 |",
    "| 동체 셸 | 폴리카보네이트(전파 투과) + **마그네슘합금 내부 프레임**(AZ91 계열) | ⚠️ 리뷰·DJI 계열 관례 |",
    "| 모터·PCB·짐벌 마운트 | 금속(구리·NdFeB·알루미늄 · FR-4+구리) | ⚠️ 브러시리스·전자 관례 |",
    "",
    "**RCS 지배(측정논문 확인)** — 배터리 ≈ 모터 > 짐벌/PCB > 셸·프롭(사실상 무시). 되쏘는 밝기는 "
    "**내부 금속**이 정하고, 플라스틱 셸·나일론 프롭은 거의 안 보인다(arXiv:1911.05926 — DJI 드론 실측에서 "
    "몸체·프롭이 저반사 재질로 기술됨). 그래서 우리 메쉬도 셸 안에 배터리·PCB 를 금속 산란체로 "
    "넣어 이 물리를 담는다. 근거: `docs/drone_material_deepverify.json`.",
))

cells.append(md(
    "## 3. 색 규칙 — 5색이면 재질이 다 보인다 (`MATERIAL_COLOR`)",
    "",
    "렌더 색은 `src/drones.py` 의 `MATERIAL_COLOR` 5색이 전부다 — 기종별 개성 색이",
    "아니라 **재질별 공통색**이다(모든 드론 공통; 색만 보면 재질을 안다).",
    "",
    "| 색 | 재질 키 | RGB (코드 값) | 왜 이 색인가 |",
    "|---|---|---|---|",
    *color_rows,
    "",
    "(RGB ← 출처: `src/drones.py` MATERIAL_COLOR 를 import 해 그대로 출력; 색 선정 이유는",
    "이 리포트의 해설)",
    "",
    "**왜 기종별 개성 색이 아닌가.** 기종마다 실물 색(Phantom=흰색, S1000=검정, Mavic=실버 …)을",
    "입히는 대안은 보기엔 실물 같지만, 그림에서 **어느 부위가 금속인지 알 수 없다**. 이 리포트의",
    "그림은 예쁜 렌더가 아니라 전파 물성 문서이므로 재질색을 쓴다. 규칙은 `drone_colors()`",
    "docstring 그대로:",
    "",
    "> \"부위 그룹 → **재질별** 표시색 RGB. **모든 드론이 같은 규칙**이라 색만 보면 재질을 안다:",
    "> plastic=회색(프로펠러 포함) · carbon=검정 · metal=파랑 · camera=주황 · pcb=초록.",
    "> (색과 전파재질은 **같은 그룹**(DRONE_GROUP_MAT)에서 나온다 — 이제 렌더 색이 곧 재질이다.)\"",
    "> ← 출처: `src/drones.py`",
    "",
    "핵심은 마지막 괄호다: 색과 전파재질이 **같은 딕셔너리 한 곳**(DRONE_GROUP_MAT)에서",
    "나오므로, 색과 물성이 어긋나는 일이 구조적으로 불가능하다. '예쁜 그림용 색표'와",
    "'시뮬레이션용 재질표'를 따로 두면 둘이 조용히 어긋날 수 있다 — §5 가 다루는 어긋남이",
    "정확히 '표가 두 개'일 때 생기는 종류다.",
))

# --- 8. §3.1 wireframe 그림 ------------------------------------------------------------
m4e_groups = ", ".join(f"`{g}`" for g in EM["matrice4e"]["groups"])
cells.append(md(
    "### 3.1 실제 메쉬에서 — Matrice 4E 예시",
    "",
    "![matrice4e wireframe](outputs/figures/wireframe_matrice4e.png)",
    "",
    f"*그림 2 — {DRONES['matrice4e'].name} 메쉬(삼각형 {A_M4E['n_faces']:,}개, 그룹 {A_M4E['n_groups']}개",
    f"← 출처: `report_mesh/outputs/mesh_canon_0817.json`, 정본 판). 왼쪽: 색=재질 셰이딩, 가운데: 와이어프레임,",
    "오른쪽: 상면도. 그림 생성: `report_mesh/src/viz_mesh_reports.py`.",
    "⚠ 그림 자체는 정본 전환 이전 판으로 구워졌다 — **색 규칙과 그룹 구성**을 보는 그림이라 "
    "그 축은 그대로지만, 프로펠러의 폭 분포는 지금 메쉬와 다르다(mesh05 §5c).*",
    "",
    f"이 기종에 실재하는 그룹은 {A_M4E['n_groups']}개 — {m4e_groups}",
    "← 출처: `mesh_verify.json` §E_materials matrice4e.groups. 색을 읽어보면:",
    "",
    "- 회색 동체·캐노피·프로펠러(전부 플라스틱), 그 앞 아래 **주황** 짐벌 카메라,",
    "  로터 허브의 **파랑** 모터. 동체 속에는 렌더로는 잘 안 보이는 **파랑 배터리·초록 PCB** 가",
    "  들어 있다(§1 의 내부 산란체).",
    f"- `arm` 그룹이 없다 — Matrice 4E 의 접이식 암은 셸형이라 `body`(플라스틱)로 흡수된다"
    "(§2.1 표의 '실재하는 기종' 열과 일치).",
    "",
    "같은 규칙의 나머지 4종 그림(`wireframe_mini5pro/mavic4pro/s1000plus/phantom4.png`)은",
    "mesh01(mini5pro)·mesh04(mini5pro/phantom4)·mesh07(s1000plus) 에 실려 있다 — 색 규칙은 어디서나 동일하다.",
))

# --- 9. §4 재질값의 출처 2층 (ITU vs custom) -------------------------------------------
cells.append(md(
    "## 4. 재질값은 어디서 왔나 — 2층 구조",
    "",
    "### 4.1 1층: \"ITU 가 있으면 ITU 를 쓴다\" (Sionna 내장 vs 커스텀)",
    "",
    "재질의 (εr, σ) 정의는 `src/materials.py` 의 `MATERIALS` **단 한 곳**이다. 파일 docstring 이",
    "선언하듯 이 파일이 \"**재질의 단일 진리원(single source of truth)**\" 이고, \"이 파일이",
    "정의한 재질을 **Sionna RT(전파 시뮬레이션)와 PO(RCS 계산)가 똑같이** 쓴다\"",
    "← 출처: `src/materials.py`.",
    "",
    "그 안에서 값의 출처는 두 부류로 나뉜다. 원칙은 docstring 그대로:",
    "",
    "> \"■ 원칙 — **ITU 가 있으면 ITU 를 쓴다**",
    "> Sionna 는 ITU-R P.2040 재질(주파수 의존 εr·σ)을 내장한다. 우리가 숫자를 지어내는 대신",
    "> Sionna 에게 물어본다(= scene.frequency 를 주고 값을 읽는다).\"",
    "> ← 출처: `src/materials.py`",
    "",
    "| 부류 | 재질 | 근거 |",
    "|---|---|---|",
    "| **Sionna 내장 (ITU-R P.2040)** | `metal`(모터·배터리·camera/pcb 의 반사면) | 국제 표준 권고안. 주파수를 바꾸면 εr·σ 가 자동 보정된다 ← `src/materials.py,106-124` |",
    "| **커스텀 (문헌 기반)** | `plastic`(ABS/PC, εr=2.7 — 프로펠러 포함), `carbon`(CFRP, σ=3×10³ S/m), `pcb`(FR-4+구리) | ITU 표에 이 재질들이 **없다**. 문헌값으로 정의하고 근거를 각 `note` 에 기록 ← `src/materials.py` |",
    "",
    "커스텀이라고 감으로 지은 값이 아니라는 '건전성 검사(sanity check)'도 코드에 있다.",
    "플라스틱 항목의 note:",
    "",
    "> \"드론 셸(ABS/PC). ITU 에 plastic 없음 — 문헌값 εr≈2.6~3.0.",
    "> 가장 가까운 ITU plasterboard(2.73)와 벌크 \\|Γ\\| 가 0.247 vs 0.244 로 사실상 동일.\"",
    "> ← 출처: `src/materials.py` ('plastic' note)",
    "",
    "즉 철학은 \"**최대한 Sionna(표준) 값을 쓰고, 표준에 없는 것만 문헌으로 채우되 근거를",
    "적는다**\"이다. 반대 대안 — 전부 직접 수치를 지정 — 은 주파수 보정을 스스로 다시 짜야 하고",
    "표준과 어긋날 위험이 있어 쓰지 않았다(\"우리가 공식을 다시 짜지 않는다\" ← `src/materials.py`).",
))

# --- 10. §4.2 gamma_po 실효값 층 -------------------------------------------------------
cells.append(md(
    "### 4.2 2층: 벌크 프레넬 vs 실효 \\|Γ\\| — 얇은 것들의 사정",
    "",
    "PO 가 쓰는 \\|Γ\\| 의 **기본값은 (εr, σ) 에서 프레넬 공식으로 유도**한다",
    "(`gamma_bulk`, 공식 Γ=(1−√εc)/(1+√εc), εc=εr−j·σ/(ω·ε0) ← `src/materials.py`).",
    "손으로 적는 표가 아니므로 Sionna 와 어긋날 수 없다.",
    "",
    "그런데 **벌크(반무한 두께) 프레넬로는 못 담는 물리**가 있다. 그 경우에만 재질 정의에",
    "`gamma_po`(실효값)를 명시하고 이유를 note 에 적는다 ← `src/materials.py`:",
    "",
    f"| 재질 | 벌크 프레넬 | 실효 \\|Γ\\| (채택) | 왜 다른가 (note 요약) |",
    "|---|---|---|---|",
    f"| `plastic` | {G_PLASTIC_BULK:.3f} | {GM['body']:.2f} | 셸이 **박막**이라 앞뒷면 간섭으로 \\|Γ\\| 가 0.1~0.45 를 오간다 — 벌크 값은 그 하한 근처라 대표값 0.28 채택 ← `materials.py` |",
    f"| `prop_plastic` | {G_PLASTIC_BULK:.3f} | {GM.get('prop', 0.25):.2f} | `plastic` 과 **동일 재질·동일 회색**이지만, 프롭은 셸보다 **더 얇은 날개**라 실효 \\|Γ\\| 만 0.28→0.25 로 더 낮춘 대표값(정밀 두께모델 아님) ← `materials.py` |",
    f"| `carbon` | {G_CARBON_BULK:.3f} | {GM['arm']:.2f} | \"직조 섬유 사이 유전체 개구·이방성을 반영\" — 벌크는 금속 근접이지만 실물 CFRP 는 약간 샌다 ← `materials.py` |",
    f"| `pcb` | (ITU metal≈1.0) | {GM['pcb']:.2f} | \"부분 개구(커넥터·비도체 영역)를 반영한 실효 0.80\" — 반사면은 구리 그라운드플레인 ← `materials.py` |",
    f"| `camera_assembly` | (ITU metal≈1.0) | {GM['camera']:.2f} | 금속 하우징+**유리 렌즈+틈새** 복합 조립품의 실효값 ← `materials.py` |",
    "",
    "(벌크 열은 `materials.py` 의 εr·σ 로 같은 프레넬 공식을 계산한 값; 실효 열은",
    "`mesh_verify.json` §E_materials gamma_map — 두 층 어느 쪽이든 **같은 표에서** 나온다는",
    "것이 gamma_po docstring 의 핵심: \"어느 쪽이든 Sionna 와 같은 표에서 나온다. 두 엔진이",
    "조용히 어긋날 수 없다\" ← `src/materials.py`)",
    "",
    "⚠ **두께 축의 현재 상태를 한 번 더 못 박아 둔다.** 셸 두께의 정본은 **0.75 mm** 이고 "
    "(DJI 공식 CAD 벽 두께 중앙값 0.704 mm 실측), 민감도 축은 0.75 / 1.5 / 3.0 mm 다 "
    "← `docs/MATERIAL_CORRECTION.md` D1. 위 표의 `plastic` note 문면은 그보다 두꺼운 대(1~3 mm)를 "
    "가정한 서술이 남아 있다 — **채택한 대표값 0.28 은 그대로 쓰고, 두께를 인용할 때는 "
    "정본 0.75 mm 를 쓸 것.** 프로펠러 두께는 §6.5 에 적는다(전 기종 공용 상수이고 실측 근거가 "
    "있는 기체가 둘뿐이다).",
))

# --- 11. code: 프레넬 직접 계산 --------------------------------------------------------
cells.append(code(
    "# 벌크 프레넬 |Gamma| 를 직접 계산해 본다 — materials.gamma_bulk 와 같은 공식\n"
    "# (src/materials.py:  Gamma=(1-sqrt(eps_c))/(1+sqrt(eps_c)),  eps_c=eps_r-j*sigma/(w*eps0))\n"
    "import math\n"
    "EPS0 = 8.8541878128e-12\n"
    f"FC = {FC_GHZ:g}e9\n"
    "def gamma_bulk(eps_r, sigma, fc=FC):\n"
    "    eps_c = complex(eps_r, -sigma / (2 * math.pi * fc * EPS0))\n"
    "    s = eps_c ** 0.5\n"
    "    return abs((1 - s) / (1 + s))\n"
    "\n"
    "# materials.py MATERIALS 의 (eps_r, sigma) — plastic:(2.7, 0.02), carbon:(5.0, 3e3)\n"
    "gp = gamma_bulk(2.7, 0.02); gc = gamma_bulk(5.0, 3.0e3)\n"
    "print(f'plastic  벌크 프레넬 |G| = {gp:.4f}  (채택한 실효값 0.28 은 박막 간섭 반영)')\n"
    "print(f'carbon   벌크 프레넬 |G| = {gc:.4f}  (채택한 실효값 0.90 은 직조 개구 반영)')\n"
    "print(f'camera 를 plastic 으로 뒀다면: 20*log10(0.85/{gp:.4f}) = '\n"
    "      f'{20*math.log10(0.85/gp):.1f} dB 어긋남  # §5 재질 선택의 무게')\n"
))

# --- 12. §5 camera_assembly 사례 -------------------------------------------------------
cells.append(md(
    "## 5. 사례 연구 — 카메라 조립품: 재질 선택 하나의 무게",
    "",
    "재질 배정이 왜 '한 곳 정의'를 고집하는지, 카메라가 가장 좋은 예다. 짐벌 카메라는",
    "**금속 하우징 + 유리 렌즈 + 짐벌 모터**의 복합체라, 단일 재질로 뭉개기 가장 애매한",
    "부품이다(← `src/materials.py` 'camera_assembly' note).",
    "",
    f"애매함의 대가는 크다. 겉면만 보고 `plastic`(벌크 \\|Γ\\|={G_PLASTIC_BULK:.3f})으로 두면,",
    f"금속 하우징이 지배하는 실효값 \\|Γ\\|={GM['camera']:.2f} 와의 차이는",
    f"20·log10({GM['camera']:.2f}/{G_PLASTIC_BULK:.3f}) = **{CAM_MISMATCH_DB:.1f} dB** 다",
    "(위 코드 셀에서 직접 계산). 만약 두 엔진이 이 판단을 **각자** 내린다면 — 한쪽은 반투명",
    "플라스틱, 다른 쪽은 금속 덩어리 — 같은 카메라를 10 dB 넘게 다르게 보게 되고, 그 상태의",
    "RT↔PO 교차검증은 비교 자체가 무의미해진다.",
    "",
    "**그래서 구조로 막는다.** `camera_assembly` 라는 전용 재질을 `materials.MATERIALS`",
    f"**한 곳**에 두고(Sionna 쪽=ITU metal, PO 쪽=실효 {GM['camera']:.2f}, 근거는 note 에",
    "← `src/materials.py`), 두 엔진이 그 한 항목을 읽는다. 같은 값을 사람이 두 군데",
    "적는 구조라면 언젠가 조용히 어긋난다 — 단일 정의는 그 가능성 자체를 없앤다",
    "(gamma_po docstring: \"어느 쪽이든 Sionna 와 같은 표에서 나온다. 두 엔진이 조용히",
    "어긋날 수 없다\" ← `src/materials.py`).",
))

# --- 13. §6 커버리지 검증 --------------------------------------------------------------
#  ⚠ 2026-08-16 (적대검증): 아래 문장이 «S1000+ 만 10개 · Mavic 4 Pro 는 7개» 로 손타이핑돼
#     있었다 — 원장은 X500 V2 도 10개, Mavic 4 Pro 는 8개다. 원장에서 읽는다.
_gcount = {k: len(EM[k]["groups"]) for k in ORDER}
_g_min, _g_max = min(_gcount.values()), max(_gcount.values())
_g_max_who = "·".join(DRONES[k].name for k in ORDER if _gcount[k] == _g_max)
_g_min_who = "·".join(DRONES[k].name for k in ORDER if _gcount[k] == _g_min)

cov_rows = []
for k in ORDER:
    e = EM[k]
    cov_rows.append(f"| {DRONES[k].name} | {len(e['groups'])} | "
                    f"{', '.join('`%s`' % g for g in e['groups'])} | "
                    f"{len(e['uncovered'])}개 | **{e['all_covered']}** |")
cells.append(md(
    "## 6. 검증 — 재질이 빠진 그룹은 없는가 (E_materials)",
    "",
    "배정 규칙이 아무리 좋아도 **어떤 그룹이 표에서 누락**되면 문제가 된다. 검증 스위트가",
    "이 항목을 두는 이유는 코드 주석 한 줄로 요약된다:",
    "",
    "> \"E. 재질 커버리지 — 그룹마다 \\|Γ\\| 가 배정돼 있나 (**빠지면 PEC=1.0 으로 과대반사**)\"",
    "> ← 출처: `report_mesh/src/verify_mesh_suite.py`",
    "",
    f"즉 누락된 그룹은 기본값(완전도체)으로 굴러떨어져 플라스틱 부위(\\|Γ\\|={GM['body']:.2f},",
    f"{db(GM['body']):.1f} dB)가 금속(0 dB)으로 계산되는 — §5 가 경고하는 종류의 — 조용한 과대평가를",
    f"만든다. 검사는 {len(ORDER)}종 메쉬의 **실제 그룹 라벨**을 모두 모아 gamma_map 키와 대조한다",
    "(`verify_mesh_suite.py`). 결과 전체:",
    "",
    "| 기종 | 그룹 수 | 실재 그룹 | 누락(uncovered) | all_covered |",
    "|---|---|---|---|---|",
    *cov_rows,
    "",
    f"**{len(ORDER)}종 모두 누락 0개, all_covered=True** ← 출처: `outputs/mesh_verify.json` §E_materials",
    f"(uncovered·all_covered 필드). 기종마다 그룹 수가 {_g_min}~{_g_max}개로 갈리는 것"
    f"(가장 많은 쪽 {_g_max_who} · 가장 적은 쪽 {_g_min_who})은 §2.1 에서 본 대로 기체 구조의 차이 —"
    " 검사는 '있는 그룹'만 따진다.",
    "",
    f"⭐ **정본 판에서 다시 확인했다** — 이 노트북을 생성할 때 정본 설정으로 {len(ORDER)}기체를 "
    f"다시 지어 그룹 라벨을 모아 보면, 위 표와 그룹 구성이 "
    f"{'완전히 같고' if GROUPS_CANON_SAME else '**달라졌고**'} 배정표가 못 덮는 라벨은 "
    f"{len(UNCOVERED_CANON)}개다. 즉 **정본 전환은 «어느 부위가 있는가» 를 바꾸지 않았다** — "
    f"바뀐 것은 그 부위의 크기(면적·삼각형 수)뿐이다(§6.6).",
    "",
    "⭐ **이 축은 인증서가 밖에서 한 번 더 조인다** — «그룹 라벨이 세 재질표에 모두 있고, 모르는",
    "재질이 조용히 기본값으로 흘러가는 자리가 없다» 를 10/10 으로 장담하고, 일부러 라벨을 망가뜨린",
    "**양성 대조 39/39** 로 «검사가 실제로 문다» 는 것까지 보였다",
    "← 출처: `docs/MESH_CERTIFICATE.md` §2 G10(`adv_material_provenance_faults`).",
    "",
    "⛔ 반대로 인증서가 **선을 긋는 자리**도 그대로 옮긴다: «재질 물성값(εr·tanδ)의 옳음은 이",
    "인증서의 범위 밖» 이다 ← 같은 문서 §3.6. 즉 **여기서 보증되는 것은 «빠진 라벨이 없다»** 이고,",
    "**«그 값이 실물과 같다» 는 보증이 아니다.** 그 축의 한계는 §7 에 모아 적는다.",
))

# --- 13b. §6.5 두 계산 경로의 |Γ| 는 설계상 다르다 -------------------------------------
cells.append(md(
    "## 6.5 ⭐ 같은 재질인데 숫자가 둘이다 — 두 계산 경로가 다른 값을 쓴다",
    "",
    "우리는 산란을 두 경로로 계산한다. **Sionna 재질**(광선엔진이 쓰는 (εr, σ) 슬래브)과",
    "**PO 커널의 \\|Γ\\|**(면적분이 쓰는 실효 반사계수)다. 둘은 **일부러 다른 값**이고,",
    "그 갈림을 적어 두는 것이 정직한 서술이다:",
    "",
    MF.engine_divergence_table(),
    "",
    "← 출처: `outputs/mesh_inspect_materials_check_0816.json` `engine_divergence`"
    f" (fc = {FC_GHZ:g} GHz, 수직입사).",
    "",
    "**왜 갈리나** — Sionna 쪽은 «반무한 벌크» 프레넬 값이고, PO 쪽은 «얇은 판의 앞뒷면 간섭까지",
    "넣은 실효값» 이다. 드론 셸은 두께 **0.75 mm** 급이라 그 차이가 실재한다",
    "← 출처: `docs/MATERIAL_CORRECTION.md`(셸 정본 두께 = 제조사 공식 CAD 벽 두께 실측의 중앙값).",
    "",
    "⚠ **현재의 한계** — 우리 PO 커널에는 **두께라는 개념이 없다.** \\|Γ\\| 하나를 상수로 받는다.",
    "즉 PO 경로는 «두꺼운 판» 극한으로 계산하고, 두께는 그 상수를 고를 때 한 번만 반영된다.",
    "이 한계는 지금 그대로 있고, 값은 발표까지 동결돼 있다.",
    "",
    "**프로펠러의 두께는 어디에 있나** — 프로펠러 재질은 셸과 **같은 플라스틱**이고, 다른 것은",
    "재질이 아니라 **두께**다(그래서 실효 \\|Γ\\| 만 0.28 → 0.25 로 낮춘 대표값을 쓴다). 그 두께의",
    "현재 상태를 못 박아 둔다:",
    "",
    f"- 정본 날 법칙(`BLADE_LAW_CANON = \"{CANON_LAW}\"`)은 프로펠러의 **평면형(위에서 본 폭 분포)만**",
    "  기체별로 바꿨다. **두께 상수는 안 건드렸다** — `TC_ROOT`=0.095 → `TC_TIP`=0.065 가",
    f"  {len(ORDER)}기종 **공용**이다 ← `src/drone_cad.py`.",
    "- 두께에 실측 근거가 있는 기체는 **둘뿐**이다(mini2 [A] 시위가중 평균 0.478 mm · typhoonh480",
    "  [A−] 두께비 t/c 0.086~0.128). 나머지 8기체는 빈칸이고, 사진으로는 원리적으로 못 잰다",
    "  ← `outputs/prop_law_by_airframe_0816.json` §F · 형상 쪽 설명은 mesh05 §6.5.",
    "- ⇒ 프롭 \\|Γ\\|=0.25 라는 **한 상수**가 두께 축을 통째로 대신하고 있다. 우리 PO 커널에",
    "  두께 개념이 없으므로(위 문단) 이 상수를 바꾸는 것 말고는 두께 감도를 볼 길이 없다.",
))

# --- 13c. §6.6 함대 전체 배정표 --------------------------------------------------------
cells.append(md(
    "## 6.6 함대 전체 배정표 — 그룹마다 무엇이 들어 있나",
    "",
    "기체 하나가 아래 그룹을 전부 쓰지는 않는다(열린 프레임 기체에는 셸이 없고, 접이식에는",
    "데크가 없다). 면적은 10종 합계 실측이다:",
    "",
    MF.assignment_table(),
    "",
    "← 출처: `outputs/mesh_inspect_materials_check_0816.json` `assignment_audit`.",
    "⚠ 표시는 «배정 자체를 다시 봐야 하는 칸» 이다 — §7 의 한계 목록 참조.",
    "",
    f"⭐ **면적 열의 세대** — 위 면적은 2026-08-16 13:15 원장 세대다. 정본 설정"
    f"(`MESH_FIX={CANON_FIX_S}` · `BLADE_LAW={CANON_LAW}`)으로 다시 지어 재면 "
    f"**{len(MOVED)}개 그룹**이 움직인다. 옛 판(`MESH_FIX=none BLADE_LAW=legacy`)도 같은 자로 "
    f"지어 재서 «정본 전환만의 몫» 을 갈라 적는다:",
    "",
    "| 그룹 | 옛 원장 [cm²] | 옛 판 실측 [cm²] | 정본 판 원장 [cm²] | 정본 전환만의 몫 | 무엇이 바꿨나 |",
    "|---|---|---|---|---|---|",
    *[f"| `{g}` | {MF.MAT['assignment_audit'][g]['total_area_mm2'] / 100:,.0f} "
      f"| {AREA_LEGACY[g] / 100:,.0f} | **{AREA_CANON[g] / 100:,.0f}** "
      f"| {100 * (AREA_CANON[g] - AREA_LEGACY[g]) / AREA_LEGACY[g]:+.1f} % | {why} |"
      for g, why in [  # noqa: E501
          ("prop", "정본 날 법칙 — 기체마다 그 기체의 평면형이라 대부분의 프롭이 옛 판보다 "
                   "홀쭉해졌다(mesh05 §5c). 삼각형 수는 오히려 늘었다(팁을 더 촘촘히 깐다)"),
          ("battery", "정본 메쉬 수리 `battery` — 팩 상자와 구조판이 서로 파고들던 것을 "
                      "합집합으로 없애, **두 번 세어지던 면적**이 사라졌다"),
      ]],
    "",
    f"나머지 {len(DRONE_GROUP_MAT) - len(MOVED)}개 그룹은 옛 판과 정본 판의 면적이 **같다** "
    f"(위와 같은 자로 확인). 그런데 표의 `camera` 처럼 **원장과 지금 빌드가 다른 칸**이 더 있는데, "
    f"그것은 정본 전환이 아니라 그 사이의 **치수 적용 라운드**에서 온 차이다 — 면적을 인용할 때는 "
    f"어느 세대인지 밝힐 것.",
    "",
    "### 내부 금속이 정말 셸 «안» 에 있나",
    "",
    "재질 배정이 옳아도, 그 금속이 **어디에 있는지**가 다르면 계산이 달라진다. 우리 SBR 은",
    "**셸을 맞은 광선만** 내부를 투과로 본다 — 금속 상자가 셸 밖으로 나와 있으면 그 상자는",
    "«내부 산란체» 가 아니라 그냥 겉면이 된다.",
    "",
    "| 기체 | 판정 | 셸 밖으로 나온 금속면 | 무엇을 뜻하나 |",
    "|---|---|---|---|",
    *[f"| {drone_label(k)} | **{INTMETAL[k]['verdict']}** | "
      + (" · ".join("`%s#%d` %.2f cm² (그 상자 겉면의 %.1f %%)"
                    % (b["group"], b["comp"], b["counted_outside_area_cm2"],
                       b["counted_outside_frac"] * 100)
                    for b in INTMETAL[k].get("boxes", []) if not b["pass"])
         if any(not b["pass"] for b in INTMETAL[k].get("boxes", [])) else "—")
      + f" | {_IM_MEAN[INTMETAL[k]['verdict']]} |" for k in ORDER],
    "",
    f"↑ 판정은 정본 판 원장 `report_mesh/outputs/mesh_canon_0817.json` §internal_metal "
    f"(`MESH_FIX={CANON_FIX_S}` · `BLADE_LAW={CANON_LAW}`), «얼마나 나왔나» 는 그 원장을 만든 "
    "그 함수 `benchmark/mesh_internal_metal_check.py` `check_drone`(0.5 mm 격자)로 이 노트북 "
    "생성 시점에 덧붙여 잰 값이다 — 판정이 원장과 어긋나면 생성기가 멈춘다.",
    "",
    "⭐ **Mini 2 가 «판정 불가» 에서 벗어났다.** 정본 수리 `i5` 가 셸을 닫아 안/밖 판정이 "
    "성립하고, 그 결과가 **FAIL** 이다 — 배터리 상자의 일부가 셸 밖으로 나와 있다. "
    "즉 셸이 열려 있던 동안 이 기체는 «통과» 도 «실패» 도 아닌 **모르는 상태**였다.",
))

# --- 14. §7 요약 + 한계 ----------------------------------------------------------------
cells.append(md(
    "## 7. 정리 — 그리고 현재 한계",
    "",
    "**이 편이 보장하는 것:**",
    "",
    f"1. 부위→재질 배정은 `DRONE_GROUP_MAT`({len(DRONE_GROUP_MAT)}개 그룹) 한 곳, 재질→물성은",
    "   `materials.MATERIALS` 한 곳 — Sionna RT 와 PO 가 **같은 표**를 읽는다.",
    "2. 렌더 **색 = 재질** (5색 규칙, 모든 기종 공통) — 그림이 곧 물성 문서다.",
    "3. 값의 출처가 계층적으로 기록돼 있다: ITU-R P.2040(표준) → 문헌 커스텀(εr·σ) →",
    "   실효 \\|Γ\\|(박막·조립품, note 에 근거).",
    f"4. {len(ORDER)}종 전부 재질 누락 0 (all_covered={ALL_COVERED}) — PEC 과대반사 경로 차단.",
    "",
    "**한계(반증 가능성을 위해 기록):**",
    "",
    "- 실효 \\|Γ\\| 는 **실측이 아니라 물리 논거를 단 대표값**이다.",
    "  특히 박막 간섭은 두께·입사각에 따라 0.1~0.45 를 오가므로(← `materials.py`)",
    "  단일 대표값은 근사다.",
    "- ⭐ **`camera_assembly` 의 0.85 는 출처가 없다** — 저장소가 스스로 그렇게 적는다",
    "  (← `docs/MATERIAL_SOURCES.md` §6-4). 그 값을 유전체로 바꿔 보면 방위평균 σ 가",
    "  el 0/−30/−60° 에서 −2.2…+0.1 dB 움직이는데 **바로 아래(나디르)에서는 −6.5…+2.7 dB**",
    "  로 훨씬 크게 움직인다 ← `outputs/mesh_inspect_gimbal_sensors_0816.json`",
    "  `_summary.gate_D_dielectric_swing_db`. 원인은 짐벌을 매다는 **방진판이 수평 평판**이라",
    "  바로 아래 방향에 정반사가 서기 때문이다.",
    "- ⭐ **배터리는 팩 외피 6면 전부를 금속으로 둔 상한값이다.** 실물 팩은 플라스틱 케이스 안에",
    "  셀 스택이 들어 있어 되쏘는 금속면이 더 작다. 크기는 1~3 dB 급이고 **미해결로 선언돼 있다**",
    "  ← `outputs/mesh_inspect_internal_metal_0816.json` `battery_material`.",
    "  ⭐ 다만 «상한» 의 뜻이 좁아졌다 — 정본 수리 `battery` 가 켜져 있어 **팩 상자와 구조판이",
    "  서로 파고들어 같은 면적을 두 번 세던 몫은 이제 없다**(4기체, 겹침 47.9~50.0 % → 0 %;",
    f"  함대 `battery` 면적이 옛 판 {AREA_LEGACY['battery'] / 100:,.0f} → 정본 "
    f"{AREA_CANON['battery'] / 100:,.0f} cm², "
    f"{100 * (AREA_CANON['battery'] - AREA_LEGACY['battery']) / AREA_LEGACY['battery']:+.1f} %)",
    "  ← `src/geom.py` `MESH_FIX_CANON`.",
    "  남은 상한성은 «6면 전부 금속» 이라는 재질 가정 하나다.",
    "- ⭐ **인증서가 이 편의 경계를 명시한다** — 라벨 축(빠진 재질 없음)은 장담하지만,",
    "  «재질 물성값(εr·tanδ)의 옳음 · 커널(PO·SBR)의 옳음» 은 **인증서의 범위 밖**이라고",
    "  적혀 있다 ← `docs/MESH_CERTIFICATE.md` §3.6. 즉 이 편의 표가 보증하는 것은 «배정이",
    "  일관되고 빠짐이 없다» 까지이고, 값 자체의 실물 충실도는 별도 축이다.",
    "- ⭐ **s1000plus 의 카본 센터플레이트가 `plastic` 그룹에 들어 있다** — 판 2장만 세도",
    "  body 합집합 전 면적의 상당 부분이고, 면 반사율로는 carbon 0.90 ↔ plastic 0.28 =",
    "  **10.14 dB** 차이다 ← `outputs/mesh_inspect_materials_check_0816.json` `findings` A1.",
    "- **`drone_gamma_map(spec, fc)` 이 `spec` 을 안 쓴다.** 지금은 재질이 기체와 무관해서",
    "  맞지만, 기종별 재질(위 카본 판 같은)이 생기는 순간 **조용히 틀린 답**을 준다.",
    "- 탄소섬유의 **이방성(방향에 따라 도전율이 다름)은 무시**했다 ← `src/materials.py`.",
    "- Semkin 실측은 26–40 GHz, 우리는 3.5 GHz — 재질 차이의 '방향'은 이전 가능하지만 절대값",
    "  비교엔 3~10 dB 보정이 필요하다 ← `refs/drone_papers/Semkin_2020_..._IEEE_Access.md`.",
    "- 재질 가중이 실제 RCS 수치에 주는 효과(기종 간 A/B, 실측 앵커링)는 RCS 결과 편의 주제다",
    "  — 여기서는 배정과 검증까지만 다뤘다.",
))

# --- 15. 재현 + 다음 -------------------------------------------------------------------
cells.append(md(
    "## 재현 방법",
    "",
    "```bash",
    "# 1) 정본 판 원장(mesh_canon_0817.json) 재생성 — 면 수·면적·내부금속 판정이 여기서 온다",
    "cd /workspace/sionna",
    "PYTHONPATH=src:benchmark /workspace/.venvs/py312/bin/python \\",
    "    report_mesh/src/mesh_canon_0817.py",
    "",
    "cd /workspace/sionna/report_mesh",
    "# 2) 재질 원장(mesh_verify.json §E_materials) 재생성",
    "/workspace/.venvs/py312/bin/python src/verify_mesh_suite.py",
    "# 3) 그림(material_legend.png, wireframe_matrice4e.png 등) 재생성",
    "/workspace/.venvs/py312/bin/python src/viz_mesh_reports.py",
    "# 4) 이 노트북 재생성 (⚠ 본문 수정은 반드시 이 파일에서)",
    "/workspace/.venvs/py312/bin/python src/make_mesh06.py",
    "```",
    "",
    "다음 리포트: **mesh07** (`report_mesh/mesh07_*.ipynb`) — 시리즈의 다음 편으로 이어진다.",
))

nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "py312",
      "language": "python", "name": "py312"}, "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 5}
out = os.path.join(RM, "mesh06_materials.ipynb")
for _i, _c in enumerate(nb["cells"]):
    _c["id"] = f"m06-{_i:02d}"

json.dump(nb, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("wrote", out, len(cells), "cells")
