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
# — 대신 벌크 프레넬은 materials.gamma_bulk 와 **같은 공식**(materials.py:127-132)을 그대로 재현해 계산.
from drones import DRONES, DRONE_GROUP_MAT, MATERIAL_COLOR

EM = V["E_materials"]
ORDER = V["meta"]["drones"]                       # mini5pro, mavic4pro, matrice4e, s1000plus, phantom4
FC_GHZ = V["meta"]["fc_ghz"]
LAM_MM = V["meta"]["lam_hi_mm"]

# --- gamma_map 은 5종 모두 동일해야 한다(재질 규칙이 드론 공통이므로) — 생성 시점에 검증 ---
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
SHORT = {"mini5pro": "Mini5", "mavic4pro": "Mavic4", "matrice4e": "M4E",
         "s1000plus": "S1000+", "phantom4": "P4"}

MAT_KO = {"prop_plastic": "프로펠러 플라스틱(얇은 날개)", "plastic": "플라스틱(ABS/PC)", "carbon": "탄소섬유(CFRP)", "metal": "금속(ITU)",
          "camera_assembly": "카메라 조립품", "pcb": "PCB(FR-4+구리)"}

A_M4E = V["A_geometry"]["matrice4e"]

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
    "> ⚠ **이 노트북은 생성물이다.** 수정은 `src/make_mesh06.py` 에서 할 것.",
    "",
    f"**한 줄 요약** — 드론 3D 메쉬의 부위 그룹 {len(DRONE_GROUP_MAT)}개마다 전파 재질과",
    f"진폭 반사계수 |Γ|@{FC_GHZ:g} GHz 를 배정하고, **렌더 색을 재질과 1:1 로 묶어**",
    "\"그림만 봐도 전파 물성이 보이게\" 만들었다. 5개 기종 전부에서 재질이 빠진 그룹은",
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
    "| 박막 간섭 | 얇은 층(드론 셸 1~3 mm)의 앞·뒷면 반사가 겹쳐 \\|Γ\\| 가 두께·파장에 따라 출렁이는 현상 |",
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
    "> ← 출처: `src/drone_cad.py:321-323` (배터리팩·PCB 박스를 동체 안에 넣는 코드의 주석)",
    "",
    "즉 부위별 재질은 장식이 아니라, **문헌이 보고하는 7 dB 급 차이를 재현하기 위한 최소",
    "조건**이다. 대안이었던 '전체 PEC' 는 플라스틱 기종의 RCS 를 크게 과대평가해 폐기했다.",
))

# --- 3. §2 재질 지도 그림 --------------------------------------------------------------
cells.append(md(
    "## 2. 재질 지도 한 장 — 색 = 재질 = 전파 물성",
    "",
    "아래 범례가 이 편의 핵심 요약이다. 왼쪽부터 **색 → 재질 → \\|Γ\\| → 이 재질을 쓰는",
    "메쉬 그룹 → 물성의 출처** 순서로 읽는다. 이 규칙은 **5개 기종 전부에 동일**하게 적용된다.",
    "",
    "![material legend](outputs/figures/material_legend.png)",
    "",
    f"*그림 1 — 재질 범례. \\|Γ\\| 수치는 {FC_GHZ:g} GHz 기준이고 `drone_gamma_map()` 이",
    "`materials.MATERIALS` 에서 유도한 값(그림 생성 코드: `report_mesh/src/viz_mesh_reports.py:84-113`,",
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
    "부위→재질 배정은 `src/drones.py:179-190` 의 `DRONE_GROUP_MAT` **한 곳**에서만 한다.",
    "표의 한글 설명은 그 딕셔너리의 문자열을 그대로 가져온 것이고, \\|Γ\\| 는",
    "`outputs/mesh_verify.json` §E_materials 의 gamma_map(5개 기종 모두 동일함을 생성 시",
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
    f"- **`arm`(탄소섬유, \\|Γ\\|={GM['arm']:.2f})은 S1000+ 에만 있다.** 나머지 기종의 접이식/일체형",
    "  암은 플라스틱 셸의 연장이라 `body` 그룹으로 들어간다. 코드의 규칙 그대로 —",
    "  \"셸형 암(arm_style≠carbon)은 build_frame 이 'body' 그룹으로 넣으므로 자동으로",
    "  플라스틱이 적용된다\" ← 출처: `src/drones.py:197-202` (`drone_gamma_map` docstring).",
    "  §1 의 Semkin 실측(카본 기체가 밝다)과 정확히 같은 구도다 — 카본 프레임 S1000+ ↔ 카본 M100.",
    f"- **`battery`(\\|Γ\\|={GM['battery']:.2f})가 금속인 이유**는 표의 설명 그대로 \"GHz 에서 파우치",
    "  포일은 사실상 금속\"이기 때문이다 ← 출처: `src/drones.py:188`. LiPo 배터리의 알루미늄",
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
    "← 출처: `mesh_verify.json` §meta lam_hi_mm(최고 대역 기준). 드론 셸 두께(1~3 mm)는 파장의 수십분의 1이라",
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
    "print(f\"gamma_map 이 5개 기종에서 동일한가: \"\n"
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
    "> ← 출처: `src/drones.py:386-388`",
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
    "← 출처: `mesh_verify.json` §A_geometry). 왼쪽: 색=재질 셰이딩, 가운데: 와이어프레임,",
    "오른쪽: 상면도. 그림 생성: `report_mesh/src/viz_mesh_reports.py:119-138`.*",
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
    "mesh01(mavic4pro)·mesh04(mini/phantom)·mesh07(s1000plus) 에 실려 있다 — 색 규칙은 어디서나 동일하다.",
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
    "← 출처: `src/materials.py:2-5`.",
    "",
    "그 안에서 값의 출처는 두 부류로 나뉜다. 원칙은 docstring 그대로:",
    "",
    "> \"■ 원칙 — **ITU 가 있으면 ITU 를 쓴다**",
    "> Sionna 는 ITU-R P.2040 재질(주파수 의존 εr·σ)을 내장한다. 우리가 숫자를 지어내는 대신",
    "> Sionna 에게 물어본다(= scene.frequency 를 주고 값을 읽는다).\"",
    "> ← 출처: `src/materials.py:15-18`",
    "",
    "| 부류 | 재질 | 근거 |",
    "|---|---|---|",
    "| **Sionna 내장 (ITU-R P.2040)** | `metal`(모터·배터리·camera/pcb 의 반사면) | 국제 표준 권고안. 주파수를 바꾸면 εr·σ 가 자동 보정된다 ← `src/materials.py:49-51,106-124` |",
    "| **커스텀 (문헌 기반)** | `plastic`(ABS/PC, εr=2.7 — 프로펠러 포함), `carbon`(CFRP, σ=3×10³ S/m), `pcb`(FR-4+구리) | ITU 표에 이 재질들이 **없다**. 문헌값으로 정의하고 근거를 각 `note` 에 기록 ← `src/materials.py:69-90` |",
    "",
    "커스텀이라고 감으로 지은 값이 아니라는 '건전성 검사(sanity check)'도 코드에 있다.",
    "플라스틱 항목의 note:",
    "",
    "> \"드론 셸(ABS/PC). ITU 에 plastic 없음 — 문헌값 εr≈2.6~3.0.",
    "> 가장 가까운 ITU plasterboard(2.73)와 벌크 \\|Γ\\| 가 0.247 vs 0.244 로 사실상 동일.\"",
    "> ← 출처: `src/materials.py:71-74` ('plastic' note)",
    "",
    "즉 철학은 \"**최대한 Sionna(표준) 값을 쓰고, 표준에 없는 것만 문헌으로 채우되 근거를",
    "적는다**\"이다. 반대 대안 — 전부 직접 수치를 지정 — 은 주파수 보정을 스스로 다시 짜야 하고",
    "표준과 어긋날 위험이 있어 쓰지 않았다(\"우리가 공식을 다시 짜지 않는다\" ← `src/materials.py:93`).",
))

# --- 10. §4.2 gamma_po 실효값 층 -------------------------------------------------------
cells.append(md(
    "### 4.2 2층: 벌크 프레넬 vs 실효 \\|Γ\\| — 얇은 것들의 사정",
    "",
    "PO 가 쓰는 \\|Γ\\| 의 **기본값은 (εr, σ) 에서 프레넬 공식으로 유도**한다",
    "(`gamma_bulk`, 공식 Γ=(1−√εc)/(1+√εc), εc=εr−j·σ/(ω·ε0) ← `src/materials.py:127-132`).",
    "손으로 적는 표가 아니므로 Sionna 와 어긋날 수 없다.",
    "",
    "그런데 **벌크(반무한 두께) 프레넬로는 못 담는 물리**가 있다. 그 경우에만 재질 정의에",
    "`gamma_po`(실효값)를 명시하고 이유를 note 에 적는다 ← `src/materials.py:44-46,135-144`:",
    "",
    f"| 재질 | 벌크 프레넬 | 실효 \\|Γ\\| (채택) | 왜 다른가 (note 요약) |",
    "|---|---|---|---|",
    f"| `plastic` | {G_PLASTIC_BULK:.3f} | {GM['body']:.2f} | 셸이 1~3 mm **박막**이라 앞뒷면 간섭으로 \\|Γ\\| 가 0.1~0.45 를 오간다 — 벌크 값은 그 하한 근처라 대표값 0.28 채택 ← `materials.py:73-74` |",
    f"| `carbon` | {G_CARBON_BULK:.3f} | {GM['arm']:.2f} | \"직조 섬유 사이 유전체 개구·이방성을 반영\" — 벌크는 금속 근접이지만 실물 CFRP 는 약간 샌다 ← `materials.py:81-84` |",
    f"| `pcb` | (ITU metal≈1.0) | {GM['pcb']:.2f} | \"부분 개구(커넥터·비도체 영역)를 반영한 실효 0.80\" — 반사면은 구리 그라운드플레인 ← `materials.py:59-62` |",
    f"| `camera_assembly` | (ITU metal≈1.0) | {GM['camera']:.2f} | 금속 하우징+**유리 렌즈+틈새** 복합 조립품의 실효값 ← `materials.py:52-58` |",
    "",
    "(벌크 열은 `materials.py` 의 εr·σ 로 같은 프레넬 공식을 계산한 값; 실효 열은",
    "`mesh_verify.json` §E_materials gamma_map — 두 층 어느 쪽이든 **같은 표에서** 나온다는",
    "것이 gamma_po docstring 의 핵심: \"어느 쪽이든 Sionna 와 같은 표에서 나온다. 두 엔진이",
    "조용히 어긋날 수 없다\" ← `src/materials.py:135-144`)",
))

# --- 11. code: 프레넬 직접 계산 --------------------------------------------------------
cells.append(code(
    "# 벌크 프레넬 |Gamma| 를 직접 계산해 본다 — materials.gamma_bulk 와 같은 공식\n"
    "# (src/materials.py:127-132:  Gamma=(1-sqrt(eps_c))/(1+sqrt(eps_c)),  eps_c=eps_r-j*sigma/(w*eps0))\n"
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
    "부품이다(← `src/materials.py:52-58` 'camera_assembly' note).",
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
    "← `src/materials.py:52-58`), 두 엔진이 그 한 항목을 읽는다. 같은 값을 사람이 두 군데",
    "적는 구조라면 언젠가 조용히 어긋난다 — 단일 정의는 그 가능성 자체를 없앤다",
    "(gamma_po docstring: \"어느 쪽이든 Sionna 와 같은 표에서 나온다. 두 엔진이 조용히",
    "어긋날 수 없다\" ← `src/materials.py:135-144`).",
))

# --- 13. §6 커버리지 검증 --------------------------------------------------------------
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
    "> ← 출처: `report_mesh/src/verify_mesh_suite.py:210`",
    "",
    f"즉 누락된 그룹은 기본값(완전도체)으로 굴러떨어져 플라스틱 부위(\\|Γ\\|={GM['body']:.2f},",
    f"{db(GM['body']):.1f} dB)가 금속(0 dB)으로 계산되는 — §5 가 경고하는 종류의 — 조용한 과대평가를",
    "만든다. 검사는 5개 기종 메쉬의 **실제 그룹 라벨**을 모두 모아 gamma_map 키와 대조한다",
    "(`verify_mesh_suite.py:212-227`). 결과 전체:",
    "",
    "| 기종 | 그룹 수 | 실재 그룹 | 누락(uncovered) | all_covered |",
    "|---|---|---|---|---|",
    *cov_rows,
    "",
    f"**5종 모두 누락 0개, all_covered=True** ← 출처: `outputs/mesh_verify.json` §E_materials",
    "(uncovered·all_covered 필드). 기종마다 그룹 구성이 다른 것(예: S1000+ 만 10개 전부,",
    "Mavic 4 Pro 는 7개)은 §2.1 에서 본 대로 기체 구조의 차이 — 검사는 '있는 그룹'만 따진다.",
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
    f"4. 5개 기종 전부 재질 누락 0 (all_covered={ALL_COVERED}) — PEC 과대반사 경로 차단.",
    "",
    "**한계(반증 가능성을 위해 기록):**",
    "",
    "- 실효 \\|Γ\\|(0.28/0.25/0.90/0.85/0.80)는 **실측이 아니라 물리 논거를 단 대표값**이다.",
    "  특히 박막 간섭은 두께·입사각에 따라 0.1~0.45 를 오가므로(← `materials.py:73-74`)",
    "  단일 대표값은 근사다.",
    "- 탄소섬유의 **이방성(방향에 따라 도전율이 다름)은 무시**했다 ← `src/materials.py:22`.",
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
    "cd /home/yunjung/workspace/sionna2/report_mesh",
    "# 1) 검증 수치(mesh_verify.json) 재생성",
    "/home/yunjung/.venvs/py312/bin/python src/verify_mesh_suite.py",
    "# 2) 그림(material_legend.png, wireframe_matrice4e.png 등) 재생성",
    "/home/yunjung/.venvs/py312/bin/python src/viz_mesh_reports.py",
    "# 3) 이 노트북 재생성 (⚠ 본문 수정은 반드시 이 파일에서)",
    "/home/yunjung/.venvs/py312/bin/python src/make_mesh06.py",
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
