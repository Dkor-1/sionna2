# -*- coding: utf-8 -*-
"""make_mesh03.py — mesh03 ipynb 생성기. ⚠ 이 파일이 소스다.

mesh03 — "자료 수집: 모든 숫자와 모델은 어디서 왔나"
배정 그림: originals_gallery.png (다른 리포트와 중복 금지)

원칙: 본문 수치는 손으로 적지 않는다.
  - 측정치  : report_mesh/outputs/mesh_verify.json
  - 스펙치  : src/drones.py 의 DroneSpec (import)
  - 문서 인용: docs/SPECS.md · assets/meshes/reference/SOURCES.md ·
              assets/meshes/cad/SOURCE.txt · src/prep_cad_scan.py docstring 을
              **파일에서 직접 읽어** 발췌/전문 인용한다.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RM = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(RM, ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

V = json.load(open(os.path.join(RM, "outputs", "mesh_verify.json"), encoding="utf-8"))

# ---- 스펙: 코드가 실제로 쓰는 값 (src/drones.py) --------------------------------
from drones import DRONES                       # noqa: E402
from mesh_ledger import ledger_order            # noqa: E402  (원장↔레지스트리 일치 강제)
ORDER = ledger_order(V)                         # = DRONES 레지스트리 전수
import prep_cad_scan                            # noqa: E402  (docstring·상수 인용용)
sys.path.insert(0, HERE)
import mesh_facts_0816 as MF                    # noqa: E402  (2026-08-16 원장 공용 로더)

# ---- ⭐정본 스위치 — 여덟 편이 같은 문장을 쓰도록 공용 로더에서 받는다 -------------
#  2026-08-17 부터 `src/geom.py` 의 두 상수가 기본값이다. 이 편은 «무엇을 쓰고 있나» 를
#  선언만 하고, 값의 뜻은 mesh01(지도)·mesh05(프로펠러)·mesh07(검사)이 맡는다.
import mesh_canon_0817 as CAN                   # noqa: E402  (정본 판 원장 로더 — 8편 공용)
BLADE_LAW = CAN.LAW                             # 'per_airframe'
MESH_FIX_ON = ",".join(CAN.FIXES)               # 'battery,i5'
FILE_TAG = CAN.TAG                              # '_mfixbatteryi5_blperairframe'

# ---- ⭐기체별 프로펠러 법칙 원장 (정본의 1차 자료 장부) --------------------------
PROP_LAW = json.load(open(os.path.join(ROOT, "outputs",
                                       "prop_law_by_airframe_0816.json"), encoding="utf-8"))
CLAW = PROP_LAW["C_law_by_airframe"]            # 기체 → {prop, grade, source, ledger, …}
PROP_GAPS = PROP_LAW["F_gaps"]                  # 원장이 스스로 적은 구멍 목록

# ---- ⭐바깥 참값 대조(인증서 치수 축) — 이 편의 «진리원» 표에 들어간다 -------------
DIMREF = json.load(open(os.path.join(ROOT, "outputs",
                                     "mesh_cert_dimension_external_0816.json"), encoding="utf-8"))
_DR_ROWS = DIMREF["residual_table"]
DR_N = len(_DR_ROWS)
DR_IND = sum(1 for r in _DR_ROWS if r.get("circularity") == "independent")
DR_IND_A = sum(1 for r in _DR_ROWS
               if r.get("circularity") == "independent" and r.get("grade") == "A")
DR_MISMATCH = DIMREF["findings"]["n_mismatch"]
DR_NO_INDEP = sorted(k for k in ORDER
                     if not any(r["key"] == k and r.get("circularity") == "independent"
                                for r in _DR_ROWS))

# ---- 원문 문서 로드 -------------------------------------------------------------
SPECS_MD = open(os.path.join(ROOT, "docs", "SPECS.md"), encoding="utf-8").read()
SOURCES_MD = open(os.path.join(ROOT, "assets", "meshes", "reference", "SOURCES.md"),
                  encoding="utf-8").read()
SOURCE_TXT = open(os.path.join(ROOT, "assets", "meshes", "cad", "SOURCE.txt"),
                  encoding="utf-8").read()
PREP_DOC = (prep_cad_scan.__doc__ or "").strip()

NPZ = os.path.join(ROOT, "assets", "meshes", "cad", "phantom4_scan_points.npz")
npz_mb = os.path.getsize(NPZ) / 1e6

G = V["G_scan"]
SRC = G["source"]          # {"thing","license","author","note"}

# ---- SPECS.md 파싱: 드론별 섹션 → 조사 대각값·URL ------------------------------
def specs_sections():
    """SPECS.md 를 '## ' 헤더로 잘라 {헤더: 본문} 사전으로."""
    out = {}
    parts = re.split(r"\n## ", SPECS_MD)
    for p in parts[1:]:
        head, body = p.split("\n", 1)
        out[head.strip()] = body
    return out

SEC = specs_sections()
#  ⚠ 2026-07-30 (Phase 3): `docs/SPECS.md` 는 **DJI 5종 전용 문서**다(그 문서 머리말이 명시).
#     비-DJI 표적(Yuneec·Holybro)은 여기 절이 **없고, 만들지도 않는다** — 그 제원의 단일
#     출처는 `src/drones.py` 의 note + `docs/RESUME_0729.md` §5 다(제원 3갈래 분산 방지).
#     그래서 아래 조회는 전부 **없을 수 있다는 전제**로 쓴다. 예전엔 KeyError 로 죽었다.
SEC_KEY = {  # DroneSpec key → SPECS.md 헤더 (DJI 5종만 존재)
    "mini5pro": "DJI Mini 5 Pro",
    "mavic4pro": "DJI Mavic 4 Pro",
    "matrice4e": "DJI Matrice 4E (M4E)",
    "s1000plus": "DJI Spreading Wings S1000+",
    "phantom4": "DJI Phantom 4 (original, 2016)",
}

def _sec_of(key):
    """SPECS.md 의 해당 절 본문 — 없으면 None(비-DJI 표적)."""
    return SEC.get(SEC_KEY.get(key, "\x00"))

def research_diag(key):
    """SPECS.md 의 '- **대각거리(휠베이스)**: NNN mm' 값(1차 조사값). 절이 없으면 None."""
    sec = _sec_of(key)
    if sec is None:
        return None
    m = re.search(r"\*\*대각거리\(휠베이스\)\*\*: ([\d.]+) mm", sec)
    assert m, key
    return float(m.group(1))

def urls_of(key, n=3):
    sec = _sec_of(key)
    return [] if sec is None else re.findall(r"^  - (https?://\S+)", sec, flags=re.M)[:n]

def quote(text, start, end):
    """원문에서 start~end 마커 사이(마커 포함)를 발췌. 실패하면 즉시 에러."""
    i = text.find(start)
    assert i >= 0, f"quote start not found: {start[:40]}"
    j = text.find(end, i)
    assert j >= 0, f"quote end not found: {end[:40]}"
    return text[i:j + len(end)]

# 발췌 인용(원문 그대로) — 전부 docs/SPECS.md 에서
Q_MINI_RESEARCH = quote(SEC[SEC_KEY["mini5pro"]],
                        "DIAGONAL WHEELBASE (motor-to-motor) IS ESTIMATED",
                        "before finalizing the CAD.")
Q_MINI_VERIFY = quote(SEC[SEC_KEY["mini5pro"]],
                      "CAVEAT on diagonal_mm:",
                      "before finalizing CAD.")
Q_MAVIC = quote(SEC[SEC_KEY["mavic4pro"]],
                "DJI does not publish a diagonal/wheelbase figure",
                "somewhat bigger).")
Q_M4E_FIX = quote(SEC[SEC_KEY["matrice4e"]],
                  "propeller_diameter_mm: change from 292 to 274",
                  "not 11.5 inches).")
Q_SPECS_HEAD = quote(SPECS_MD, "> 조사일", "`docs/drone_research.json`.")

# drones.py 의 note(왜 이 값을 채택했나)
NOTE_MINI = DRONES["mini5pro"].note
NOTE_MAVIC = DRONES["mavic4pro"].note
NOTE_M4E = DRONES["matrice4e"].note
NOTE_S1000 = DRONES["s1000plus"].note

# 원본 스캔 통계 — 문서에서 정규식으로 추출(손으로 안 적음)
TRIS = re.search(r"([\d,]+)\s*tris", SOURCE_TXT).group(1)          # "3,086,688"
STL_MB = re.search(r"(\d+)\s*MB", PREP_DOC).group(1)               # "154"
RES_MM = re.search(r"([\d.]+)\s*mm 해상도", SOURCE_TXT).group(1)   # "0.4"
CURL = re.search(r"(curl -LO \S+)", PREP_DOC).group(1)
compress_x = float(STL_MB) / npz_mb

# SOURCES.md 의 표 — ⚠ «| 로 시작하는 줄» 을 통째로 모으면 서로 다른 표 다섯 개가 한 덩어리로
#   붙어 분류 자체가 거짓이 된다. 그래서 **표 블록별로** 뽑는다.
_SRC_HDR = "| 파일 | 실물 | 출처 | 라이선스 |"


def sources_table(nth: int) -> str:
    """`SOURCES.md` 의 nth(0-base) «파일|실물|출처|라이선스» 표를 그대로 발췌.

    표 중간에 `>` 경고 블록이 끼어 있으므로 «다음 표 머리글까지» 를 경계로 삼는다.
    """
    lines = SOURCES_MD.splitlines()
    starts = [i for i, l in enumerate(lines) if l.strip() == _SRC_HDR]
    assert len(starts) > nth, f"SOURCES.md 에 표가 {len(starts)}개뿐이다 (nth={nth})"
    out = []
    for l in lines[starts[nth]:]:
        if l.startswith("|"):
            out.append(l)
        elif l.strip() == "" or l.startswith(">"):
            continue          # 표 사이의 빈 줄·경고 블록은 건너뛴다(같은 표의 일부다)
        else:
            break             # 산문·헤딩이 나오면 이 표는 끝났다 — 다음 표를 삼키지 않는다
    return "\n".join(out)


SOURCES_TABLE = sources_table(0)      # 로보틱스 저장소(Apache-2.0·BSD-3)
SOURCES_TABLE_MFR = sources_table(1)  # 제조사 배포물(공개 라이선스 없음)

# ---- 사진층(등급 [B] 의 실체) — 폴더를 세어서 적는다(손으로 안 적음) ----------------
_PHOTO_ROOT = os.path.join(ROOT, "assets", "photos")
PHOTO_DIRS = sorted(k for k in ORDER
                    if os.path.isdir(os.path.join(_PHOTO_ROOT, k)))
_PHOTO_CNT = {k: len([f for f in os.listdir(os.path.join(_PHOTO_ROOT, k))
                      if not f.startswith(".")]) for k in PHOTO_DIRS}
PHOTO_N = sum(_PHOTO_CNT.values())
PHOTO_ROWS = [f"| {DRONES[k].name} | `assets/photos/{k}/` | {_PHOTO_CNT[k]} |"
              for k in sorted(PHOTO_DIRS, key=lambda k: -_PHOTO_CNT[k])]
#  ⭐사진 폴더의 출처 문서 유무 — 폴더를 봐서 적는다(손으로 안 적음).
#    출처 문서가 없으면 «그 사진이 어느 기체의 무슨 컷인지» 를 되짚을 근거가 없다.
PHOTO_NO_SRC = [k for k in PHOTO_DIRS
                if not os.path.exists(os.path.join(_PHOTO_ROOT, k, "SOURCES.md"))]


# ---- 기체별 프로펠러 1차 자료 장부 (원장 그대로) ---------------------------------
def _cell(s: str) -> str:
    """표 칸에 안전하게 넣는다 — 파이프는 표를 깨고, 줄바꿈은 행을 쪼갠다."""
    return " ".join(str(s).replace("|", "/").split())


def prop_source_rows():
    """`prop_law_by_airframe_0816.json` C_law_by_airframe → 출처 장부 표.

    ⭐이 편이 적는 것은 **자료의 출처와 등급**까지다. 평면형 수치(c_max/R·시위 절점)는
      mesh05(프로펠러 편)가 정본이라 여기 두 번 적지 않는다.
    """
    rows = []
    for k in ORDER:
        c = CLAW[k]
        proxy = ("" if not c.get("proxy_of")
                 else f" · ⛔**대리**({DRONES[c['proxy_of']].name} 의 프롭을 대신 세운다)")
        rows.append(f"| {DRONES[k].name} | {_cell(c['prop'])} "
                    f"| **[{c['grade'].replace('-', '−')}]**{proxy} "
                    f"| ±{c['uncertainty_pct']:g} % | {_cell(c['source'])} |")
    return "\n".join(rows)


PROP_SOURCE_TABLE = prop_source_rows()


def prop_grade_groups() -> str:
    """등급 → 그 등급인 기체들. 한 줄에 10기체를 늘어놓지 않으려고 묶는다."""
    by = {}
    for k in ORDER:
        by.setdefault(CLAW[k]["grade"], []).append(k)
    order = ["A", "A-", "B", "B-", "C", "D"]
    return " · ".join(f"**[{g.replace('-', '−')}]** " + "·".join(by[g])
                      for g in order if g in by)


PROP_GRADE_GROUPS = prop_grade_groups()
PROP_GAP_LINES = [f"- {g}" for g in PROP_GAPS]
_UNC = [CLAW[k]["uncertainty_pct"] for k in ORDER]
PROP_UNC_MIN, PROP_UNC_MAX = min(_UNC), max(_UNC)
PROP_PROXY = [k for k in ORDER if CLAW[k].get("proxy_of")]
Q_SOURCES_WARN = quote(SOURCES_MD, "⚠️ **제조사 공식 CAD 는",
                       "**채점 전용**입니다.")
Q_SOURCES_UNIT = quote(SOURCES_MD, "**단위**: STL 은 mm 단위",
                       "457 이 전후임을 확정).")
Q_SOURCES_RULE = quote(SOURCES_MD, "표적 메쉬 자체는 여전히",
                       "X500 DAE 만 예외적으로 재질 분할이 있다).")

# 대각값의 성격(공식/추정) — 근거는 §1.2·§1.3 의 SPECS.md 원문 인용
#  ⚠ 폴백은 등급을 **주장하지 않는다** — 어디를 보라고만 말한다(비-DJI 2종).
_DIAG_KIND_FALLBACK = "← `src/drones.py` note (`docs/RESUME_0729.md` §5)"
DIAG_KIND = {
    "mini5pro": "추정(비공개) → envelope 재유도",
    "mavic4pro": "추정(비공개) → envelope 재유도",
    "matrice4e": "공식(438.8)",
    "s1000plus": "공식(1045)",
    "phantom4": "공식(350)",
}

# ---- 노트북 셀 ------------------------------------------------------------------
def md(*lines):
    src = "\n".join(lines).splitlines(keepends=True)
    return {"cell_type": "markdown", "metadata": {}, "source": src or [""]}

d = DRONES  # 짧은 별칭

# 스펙 표 행
spec_rows = []
for k in ORDER:
    s = d[k]
    rd = research_diag(k)
    arrow = (f"**{s.diagonal_mm:g}**" if rd is None or rd == s.diagonal_mm
             else f"{rd:g} → **{s.diagonal_mm:g}**")
    w = f"{s.weight_g:g}"
    if k == "s1000plus":
        w = f"{s.weight_g:g}†"
    spec_rows.append(f"| {s.name} | {arrow} | {w} | {s.prop_dia_mm:g} | "
                     f"{s.num_rotors} | {s.release} | {DIAG_KIND.get(k, _DIAG_KIND_FALLBACK)} |")
SPEC_TABLE = "\n".join(spec_rows)

url_lines = []
for k in ORDER:
    us = urls_of(k, 2)
    url_lines.append(f"- **{d[k].name}**: " + (" · ".join(f"<{u}>" for u in us) if us else
                     "`docs/SPECS.md` 에 절이 없다(그 문서는 DJI 5종 전용) — 출처는 "
                     "`src/drones.py` 의 `note` 와 `docs/RESUME_0729.md` §5"))
URL_LIST = "\n".join(url_lines)

cells = [

# 1 ── 제목 + 경고 + 요약 + 용어풀이 ------------------------------------------------
md("# mesh03 — 자료 수집: 모든 숫자와 모델은 어디서 왔나",
   "",
   *MF.head_md(
       "mesh03",
       f"표적 {len(ORDER)}종의 모든 숫자와 형상이 어느 자료에서 왔고, "
       "그중 무엇이 **제작에 들어갔고** 무엇이 **채점만 하는가**.",
       ["verify", "sources", "body_arms", "meshfix_m4e", "audit"],
       extra=[
           ("outputs/prop_law_by_airframe_0816.json",
            "⭐기체별 프로펠러 법칙의 1차 자료 — 프롭 모델명·근거 등급·불확실도·남은 구멍"),
           ("outputs/mesh_cert_dimension_external_0816.json",
            f"바깥 참값 대조 {DR_N}행(우리 수가 아니라 **저장소 밖** 참값과 견준 표)"),
           ("docs/MESH_CERTIFICATE.md",
            "메쉬 인증서 — 무엇을 장담하고 무엇은 장담 못 하는가(판정 «조건부 장담»)"),
       ]),
   "",
   f"**한 줄 요약** — 우리 드론 메쉬 {len(ORDER)}종에 들어간 **모든 입력 자료의 출처 장부**다:",
   "① 제조사 공표 제원(웹 조사→독립 검증 2단계), ② **제조사 공식 CAD 3종**(Matrice 4T STEP ·",
   f"Mini 2 GLB · X500 V2 STEP), ③ Phantom 4 **실기체 3D 스캔**({SRC['license']}),",
   "④ 오픈소스 실물 CAD — 그리고 각각을 **어떤 라이선스로, 왜, 어디까지** 쓰는지 밝힌다.",
   "",
   "⭐ 이 편의 핵심 구별은 **«제작에 들어간 자료» ↔ «채점만 하는 자료»** 다(§3.2).",
   "그 구별이 무너지면 «독립 검증» 이라는 말이 과장이 된다.",
   "",
   "**형상 근거 등급** — 이 시리즈 공통 규약:",
   "",
   *MF.grade_legend(self_is_mesh03=True),
   "",
   "| 드론 | 등급 | 근거 |",
   "|---|---|---|",
   *[f"| {d[k].name} | **[{MF.GRADES[k][0]}]** | {MF.GRADES[k][1]} |" for k in ORDER],
   "",
   "## 용어풀이 (이 리포트에 나오는 말)",
   "",
   "| 용어 | 뜻 |",
   "|---|---|",
   "| 스펙시트(spec sheet) | 제조사가 공개하는 제원표(치수·무게·속도 등). 우리 메쉬의 1차 진리원 |",
   "| 대각거리(휠베이스) | 마주보는 모터 축 사이 거리[mm]. 드론 크기의 표준 척도 (자동차 축거에 해당) |",
   "| CAD | 컴퓨터로 만든 3D 설계 모델. 여기선 '실물 제품의 3D 형상 파일' 의미로 쓴다 |",
   "| STL | 3D 형상을 삼각형 조각들로 저장하는 파일 형식. 3D 프린팅의 표준 |",
   "| 점구름(point cloud) | 물체 표면을 점들의 집합으로 표현한 것. 스캐너 출력이 보통 이 형태 |",
   "| npz | 여러 numpy 배열을 압축해 담는 파이썬 파일 형식 |",
   "| PO(물리광학) | 표면 전류 근사로 레이더 반사(RCS)를 계산하는 방법 — 표면 점+법선+면적이면 충분 |",
   "| CC-BY | 크리에이티브 커먼즈 '저작자표시' 라이선스 — 출처를 밝히면 수정·재배포 자유 |",
   "| Apache-2.0 / BSD-3 | 소프트웨어의 허용적(permissive) 라이선스 — 표시 유지 조건으로 자유 사용 |",
   "| 프로버넌스(provenance) | 데이터의 혈통: 어떤 원천에서 어떤 가공을 거쳐 왔는지의 기록 |",
   ),

# 2 ── 왜 '출처 장부'가 리포트 한 편인가 -------------------------------------------
md("## 0. 왜 출처만 다루는 리포트가 따로 있나",
   "",
   "시뮬레이션의 신뢰도는 **입력의 신뢰도를 넘을 수 없다.** 드론 RCS(레이더 반사 면적)를 아무리",
   "정밀하게 계산해도, 기체 치수가 틀렸으면 결과도 틀린다. 그래서 이 시리즈는 검증(mesh07~08)에 앞서",
   "**모든 숫자와 모델의 혈통(프로버넌스)** 을 한 편으로 정리한다. 원칙은 세 가지다:",
   "",
   "1. **숫자마다 출처를 단다** — 공식인지, 추정인지, 추정이면 오차범위는 얼마인지.",
   "2. **모르면 모른다고 쓴다** — 아래 §1.2 의 Mini 5 Pro 대각처럼, DJI 가 공개 안 한 값은",
   "   '추정 ±20 mm' 로 명시한다 (덮어두지 않는다).",
   "3. **다운로드물은 라이선스와 함께 산다** — 저작자표시 의무를 파일 옆에 기록한다(§5).",
   "",
   "이번 편에서 다루는 자료는 **네 층**이고, 층마다 «제작에 들어가나» 가 다르다:",
   "",
   "| 층 | 자료 | 제작에 들어가나 | 출처 문서 |",
   "|---|---|---|---|",
   f"| A | 제조사 공표 제원 ({len(ORDER)}기체) — 대각·외형 L×W×H·프롭 지름·무게 "
   "| ✅ **전 기체의 출발점** | `docs/SPECS.md`(DJI 5종) + `docs/drone_research.json` + "
   "`src/drones.py` 의 `note`(비-DJI 5종) |",
   "| B | 제품사진·매뉴얼 도해 | ✅ **공표 숫자가 안 정하는 형상**(셸 비율·암 폭·다리·짐벌) "
   "| `assets/photos/*` + `src/drones.py` note 의 픽셀 근거 |",
   "| C | 제조사 공식 CAD 3종 (Matrice 4T STEP · Mini 2 GLB · X500 V2 STEP) "
   "| ✅ **그 기체에 한해 형상 상수를 읽는다**(§3.2) | `assets/meshes/reference/SOURCES.md` |",
   f"| D | Phantom 4 실기체 3D 스캔({RES_MM} mm) · 로보틱스 저장소의 실물 CAD "
   "| ⛔ 스캔은 채점 전용 · 참조 프로펠러 셋 중 **Yuneec 것만 그 기체(Typhoon H480)의 제작 입력**, "
   "나머지 둘은 교차검증 "
   "| `assets/meshes/cad/SOURCE.txt` · `SOURCES.md` · `outputs/reference_props.json` |",
   "",
   "⭐ **핵심 원칙을 정확히 적으면 이렇다.** 표적 메쉬는 **공표 제원(A)에서 파라메트릭으로 생성**하고,",
   "공표 숫자가 안 정하는 형상은 **사진(B)** 이 정하며, **공식 CAD 가 있는 기체에 한해 그 CAD(C)에서",
   "형상 상수를 읽는다.** 나머지(D)는 채점 쪽이다.",
   "← 출처: `assets/meshes/reference/SOURCES.md` 머리말 · 본 편 §3.2.",
   "",
   f"⭐ **프로펠러 자료의 지위가 여기서 갈린다.** 지금 프로펠러는 **기체마다 그 기체의 순정 프롭**이다",
   f"(정본 날 법칙 `BLADE_LAW_CANON=\"{BLADE_LAW}\"`, `src/geom.py`). 그래서 참조 프로펠러 3종",
   "(3DR Solo · PX4 1345 · Yuneec H480)은 **«10기종 공용 평면형»이 아니다**:",
   "",
   "- **Yuneec H480 프롭**은 Typhoon H480 **자신의** 프롭이라 그 기체의 1차 자료다(등급 [A−]).",
   "- **3DR Solo · PX4 1345** 는 지금 **어느 기체의 형상도 정하지 않는다** — 실물 프롭끼리 얼마나",
   "  다른지 견주는 **교차검증 자료**다.",
   "- 사진이 못 주는 구간(뿌리 안쪽·팁 바깥)을 이어 붙이는 **기준곡선은 Mini 2 공식 GLB** 다 —",
   "  저장소에서 **스팬 전체가 [A] 인 유일한 프롭**이기 때문이고, 이어 붙인 구간의 등급은 그래서",
   "  [D](뿌리)·[C](팁)로 따로 적힌다 ← 출처: `outputs/prop_law_by_airframe_0816.json`",
   "  `B_reference_curve_mini2_A` · 각 기체의 `segment_grade`.",
   "",
   "기체별 1차 자료는 §3.1.2 의 장부가 전부 적는다.",
   "",
   "«전부 검증 전용» 이라고 쓰면 짧고 깔끔하지만 지금 상태와 다르다. 그 차이가 «독립 채점» 이라는",
   "말의 무게를 정하므로, 이 편은 층마다 위 열을 붙여 둔다.",
   ),

# 3 ── §1 공식 제원: 2단계 구조 ----------------------------------------------------
md("## 1. DJI 공식 제원 — 조사 → 독립검증의 2단계",
   "",
   "드론 제원은 웹에 떠도는 값이 서로 다른 경우가 많다(리뷰 사이트가 피치를 지름으로 잘못 옮기는",
   "식). 그래서 우리는 한 번 조사하고 끝내지 않고 **두 단계**를 거쳤다:",
   "",
   "> " + Q_SPECS_HEAD.replace("\n> ", " ").lstrip("> "),
   "",
   "← 출처: `docs/SPECS.md` 머리말 (조사 원자료는 `docs/drone_research.json`)",
   "",
   "- **1단계 research**: 기체당 공식 스펙페이지·데이터시트·리뷰를 뒤져 제원을 수집하고,",
   "  값마다 '공식/추정' 딱지와 근거 URL 을 남긴다.",
   "- **2단계 verify**: **다른 조사자가 원 조사를 보지 않고** 핵심 5개 필드(대각·무게·로터 수·",
   "  프로펠러 지름·출시상태)를 독립적으로 재조사해 대조한다. 불일치가 나오면 정정 기록을 남긴다.",
   "",
   "왜 이렇게까지 하나? 실제로 2단계에서 **오류가 잡혔기 때문**이다 — Matrice 4E 의 프로펠러",
   "지름이 292 mm(1단계) → **274 mm**(2단계 정정) 로 바뀌었다(§1.3). 한 번 조사로 끝냈으면",
   "6.6 % 큰 프로펠러로 마이크로도플러를 계산할 뻔했다.",
   "",
   "`docs/drone_research.json` 은 이 두 단계의 **원자료**다: 기체당 `{research: {...}, verify:",
   "{...}}` 두 블록이 있고, `SPECS.md` 는 그걸 사람이 읽게 요약한 문서다. 코드가 실제로 쓰는 값은",
   "`src/drones.py` 의 `DroneSpec`(기체당 하나)에 옮겨져 있으며, 조사값과 다르게 채택한 경우",
   "그 이유를 `note` 필드에 남겼다(§1.2). ← 출처: `docs/drone_research.json` 구조 · `src/drones.py`(DroneSpec 정의)·`:90`(DRONES)",
   ),

# 4 ── §1.1 스펙 표 ---------------------------------------------------------------
md(f"## 1.1 표적 {len(ORDER)}기체 핵심 제원 (코드가 실제로 쓰는 값)",
   "",
   "아래 표는 이 노트북 생성 시점에 `src/drones.py` 의 `DroneSpec` 에서 **import 해 읽은** 값이다.",
   "'조사 → 채택' 표기는 1차 조사값(`docs/SPECS.md`)과 최종 채택값이 다른 경우다.",
   "",
   "| 기체 | 대각 [mm] (조사→채택) | 이륙중량 [g] | 프롭 Ø [mm] | 로터 | 상태 | 대각값의 성격 |",
   "|---|---|---|---|---|---|---|",
   SPEC_TABLE,
   "",
   f"† S1000+ 의 {d['s1000plus'].weight_g:g} g 은 대표 **이륙**중량이다 — 기체(airframe) 자중은"
   " 4.4 kg, 권장 이륙중량 6.0~11.0 kg. ← 출처: `docs/SPECS.md` S1000+ 절"
   f" (\"{NOTE_S1000.split('. ')[-1].rstrip('.')}\" — `src/drones.py` note)",
   "",
   "- 무게·프로펠러·로터 수·출시상태는 전 기체 **공식값**(검증 통과). ← 출처: `docs/SPECS.md` 각 절 '검증' 항목",
   "- **대각거리는 두 기체(Mini 5 Pro·Mavic 4 Pro)가 추정**이다 — DJI 가 Mini/Mavic 시리즈의",
   "  대각을 공개하지 않기 때문. 어떻게 추정했고 왜 조사값과 다른 값을 채택했는지가 다음 절이다.",
   ),

# 5 ── §1.2 사례 1: Mini 5 Pro ----------------------------------------------------
md("## 1.2 사례 1 — Mini 5 Pro 대각: '추정 ±20 mm' 를 그대로 드러내기",
   "",
   f"1차 조사는 대각을 {research_diag('mini5pro'):g} mm 로 냈지만, 조사자 스스로 이렇게 적었다:",
   "",
   f"> \"{Q_MINI_RESEARCH}\"",
   "",
   "← 출처: `docs/SPECS.md` Mini 5 Pro '주의' 항목 (원문 그대로)",
   "",
   "독립 검증자도 같은 결론이다 — **확인 불가, 추정으로 취급하라**:",
   "",
   f"> \"{Q_MINI_VERIFY}\"",
   "",
   "← 출처: `docs/SPECS.md` Mini 5 Pro '검증' 항목 (원문 그대로)",
   "",
   "요약하면: DJI 공식 스펙페이지 어디에도 Mini 5 Pro 의 모터-모터 대각이 없다. 250 mm 는",
   "언폴드 외형(304×380 mm, 프롭팁 포함)에서 프롭 반지름을 빼 역산한 **추정치 ±약 20 mm** 다.",
   "",
   f"그런데 코드의 채택값은 **{d['mini5pro'].diagonal_mm:g} mm** 다. 왜 조사값과 다른가 —",
   "`src/drones.py` 의 note 가 그 이유를 기록하고 있다:",
   "",
   f"> \"{NOTE_MINI}\"",
   "",
   "← 출처: `src/drones.py` (mini5pro note + 주석, 원문 그대로)",
   "",
   "⚠ **인용문 안의 `255×181×91 mm` 를 그대로 쓰지 말 것.** 저장소의 제원 조사가 이 수를"
   " **2차 매체의 오류로 기각**해 두었다 — DJI 가 공개한 것은 «접었을 때(프롭 제외) 157×95×68»"
   " 과 «펼쳤을 때(프롭 포함) 304×380×91» 두 줄뿐이고, 폭 181 mm 는 152.4 mm 프롭 4장이"
   " 물리적으로 들어가지 못한다 ← 출처: `docs/drone_specs_2026.json`(mini5pro, `unfolded_*` = null"
   " · «이 숫자를 쓰지 말 것»). 코드도 그 기각을 따른다 — `DroneSpec.envelope_mm` 은"
   " **높이 91 mm 만** 강제하고 L/W 는 비워 둔다.",
   "",
   "즉 **공식 외형(envelope)에 프레임을 맞추자 대각 274.6 mm 가 유도**됐고, 옛 추정 250 mm 는",
   "약 9 % 작았던 것이다. 우리는 '더 공식적인 값(외형)이 이긴다'는 규칙으로 envelope 을 우선했다.",
   "추정값 하나를 조용히 쓰는 대신, **추정임을 명시하고 → 더 강한 근거가 나오면 갈아탄 과정**을",
   "전부 기록해 둔 것 — 이것이 이 프로젝트의 자료 취급 방식이다.",
   ),

# 6 ── §1.3 사례 2·3 --------------------------------------------------------------
md("## 1.3 사례 2·3 — Mavic 4 Pro 대각, Matrice 4E 프로펠러",
   "",
   f"**사례 2 · Mavic 4 Pro: 대각 {research_diag('mavic4pro'):g} → {d['mavic4pro'].diagonal_mm:g} mm.**",
   "1차 조사부터 추정임이 명시돼 있었다:",
   "",
   f"> \"{Q_MAVIC}\"",
   "",
   "← 출처: `docs/SPECS.md` Mavic 4 Pro '주의' 항목 (원문 그대로)",
   "",
   "그런데 이 400 mm 는 **공식 외형과 기하학적으로 모순**이었다 — 328.7×390.5 mm 몸체를",
   "400 mm 대각으로는 펼 수 없다(대각선이 몸체 대각보다 짧아진다). `src/drones.py` note:",
   "",
   f"> \"{NOTE_MAVIC}\"",
   "",
   "← 출처: `src/drones.py` (mavic4pro note, 원문 그대로)",
   "",
   f"**사례 3 · Matrice 4E: 프로펠러 292 → {d['matrice4e'].prop_dia_mm:g} mm (검증 정정).**",
   "1단계 조사는 프롭 모델명 '1157F' 의 앞자리를 11.5 인치로 읽어 292 mm 로 냈다.",
   "독립 검증이 이를 뒤집었다:",
   "",
   f"> \"{Q_M4E_FIX}\"",
   "",
   "← 출처: `docs/SPECS.md` Matrice 4E '검증' 항목 (원문 그대로) · 채택값 확인: `src/drones.py`",
   "",
   "**세 사례가 보여주는 원칙**: 웹에서 한 번 긁은 값은 믿지 않는다. (1) 독립 재조사로 대조하고,",
   "(2) 공식 외형과의 **기하 일관성**으로 다시 검산하고, (3) 정정 이력을 지우지 않고 남긴다.",
   "이렇게 채택된 최종 치수가 실제 메쉬와 일치하는지는 mesh04 §3(치수 대조)과 mesh08 에서 자로 잰다.",
   ),

# 7 ── §1.4 출처 URL 발췌 ---------------------------------------------------------
md("## 1.4 근거 URL (발췌)",
   "",
   "기체마다 4~6개 출처를 대조했다. 대표 URL 만 발췌하면 (전체 목록: `docs/SPECS.md` 각 절 '출처'):",
   "",
   URL_LIST,
   "",
   "← 출처: `docs/SPECS.md` 각 드론 절의 '출처' 목록에서 생성 시점에 파싱",
   "",
   "공식 페이지(dji.com·enterprise.dji.com)를 1순위로, 제3자 데이터시트(dronespec 등)와",
   "리뷰를 교차확인용으로 썼다. 단종품(S1000+, 2014)은 공식 페이지가 아카이브 상태라",
   "소매점 사양표까지 대조했다.",
   ),

# 7b ── §1.5 사진층 ---------------------------------------------------------------
md("## 1.5 ⭐ 사진층 — 공표 숫자가 **안 정하는** 형상은 어디서 왔나",
   "",
   "공표 제원은 상자 하나(L×W×H)와 몇 개의 길이를 줄 뿐이다. 셸이 어디서 넓고 어디서 잘록한지,",
   "암이 얼마나 굵은지, 다리가 얼마나 긴지, 짐벌이 어디에 매달리는지는 **그 숫자로 안 정해진다.**",
   "공식 CAD 가 없는 기체에서 그 형상의 1차 근거는 **제품사진·매뉴얼 도해**이고, 그래서 이 층이",
   "형상 근거 등급 **[B]** 의 실체다.",
   "",
   f"저장소에 있는 사진: `assets/photos/` 아래 {len(PHOTO_DIRS)}개 기체 폴더, 파일 {PHOTO_N}장",
   "(공식 제품컷·FCC 정투영·매뉴얼 도해·저면 렌더).",
   "",
   "| 기체 | 폴더 | 장수 |",
   "|---|---|---|",
   *PHOTO_ROWS,
   "",
   "**사진을 어떻게 숫자로 바꾸나 — 축척 앵커.** 사진 한 장에는 «몇 픽셀» 밖에 없으므로, 그 사진",
   "안에서 **길이를 아는 것 하나**를 골라 mm/px 를 정하고 나머지를 잰다. 그 앵커와 결과를",
   "`src/drones.py` 의 `note` 에 그대로 적어 둔다. 예(Mini 5 Pro 다리 길이):",
   "",
   "> 앞 로터쌍 **641.55 px = 227.6 mm**(공표 프롭 포함 폭 380 mm 에서) 로 축척을 잡으면 다리의",
   "> 투영 길이가 85 px = 30.2 mm 이고, 앙각 성분을 빼면 **31.1 mm**. 밴드 **±15 %** —",
   "> DJI 는 다리 치수를 공표하지 않는다.",
   "",
   "← 출처: `src/drones.py` mini5pro `note`(§1.2 전문 인용에 같은 문장이 있다).",
   "픽셀 근거는 `src/drone_cad.py` 의 `_SHELL_SHAPE` · `_ARM_WIDTH` · `_ARM_SECTION` 에도 함께 산다.",
   "",
   "⚠ **이 층의 한계를 그대로 적는다.**",
   "",
   "- **원근**이 남는다. 마케팅 렌더는 정투영이 아니어서 앞뒤 트랙이 다르게 보일 수 있다 —",
   "  Mini 5 Pro 의 «사다리꼴 배치» 가설이 그렇게 나왔고, 공표 두 치수와 안 맞아 **채택하지 않은",
   "  채로 note 에 남겨 두었다**(반증 기록).",
   "- **밴드가 붙는다.** 사진 계측값은 대개 ±15 % 대의 폭을 함께 선언한다.",
   "- 기체별로 사진의 질이 다르다 — FCC 정투영(자 포함)이 있는 기체와 제품컷 3장뿐인 기체가 같은",
   "  [B] 등급 안에 있다.",
   "",
   "⭐ **사진층에 지금 뚫려 있는 구멍 셋** — 프로펠러 1차 자료를 정리하면서 드러난 것이고,",
   "그대로 적어 둔다(← 출처: `outputs/prop_law_by_airframe_0816.json` 각 기체 `caveat_ko`):",
   "",
   f"- **출처 문서가 없는 폴더가 {len(PHOTO_NO_SRC)}개다** — "
   + ", ".join(f"`assets/photos/{k}/`" for k in PHOTO_NO_SRC)
   + " 에 `SOURCES.md` 가 없다. 나머지 폴더는 전부 있다. 출처 문서가 없으면 «이 컷이 어디서 왔고"
     " 정말 그 기체인가» 를 되짚을 근거가 사진 자체밖에 없다.",
   "- **Mini 5 Pro 사진은 기체 동일성이 미확정이다.** 같은 묶음으로 들어온 «mavic 4 pro_1/_4.png»"
   " 는 대조 결과 **다른 기종**(Mavic 3 계열)으로 확인됐다. 그래서 이 기체의 프롭 평면형 등급이"
   f" **[{CLAW['mini5pro']['grade']}]**(±{CLAW['mini5pro']['uncertainty_pct']:g} %)에 머문다.",
   "- **Phantom 4 폴더는 다른 기체다** — Phantom 4 **Pro+ V2.0**(프롭 9455S)이다. 거기서 재면"
   " «고침» 이 아니라 새 오류가 되므로, 이 기체의 프롭은 재지 않고 Phantom 3 의 9450 을"
   " **대리**로 세운다(§3.1.2).",
   ),

# 8 ── §2 실기체 스캔 --------------------------------------------------------------
md("## 2. 실기체 3D 스캔 — DJI Phantom 4 (Thingiverse thing:1456295)",
   "",
   "스펙시트는 대각·외형 몇 개 숫자만 준다. **곡면 실루엣까지 실물과 닮았는지**는 숫자 몇 개로",
   "확인할 수 없다. 그래서 실기체를 통째로 3D 스캔한 공개 데이터를 구했다:",
   "",
   f"- **무엇**: DJI Phantom 4 실기체를 {RES_MM} mm 해상도로 스캔한 STL",
   f"  (\"DJI PHANTOM 4 HI RES SCAN\") — 원본 {STL_MB} MB, 삼각형 {TRIS}개.",
   f"- **저작자**: {SRC['author']}, 2016.",
   f"- **출처**: <https://www.thingiverse.com/{SRC['thing'].split()[-1].replace(':', ':')}> "
   "(미러: archive.org)",
   f"- **라이선스**: **{SRC['license']}** — 저작자를 표시하면 수정·재배포 자유.",
   "",
   f"← 출처: `assets/meshes/cad/SOURCE.txt` · `mesh_verify.json[\"G_scan\"][\"source\"]`",
   "",
   "저장소에 있는 기록 파일 전문(이 파일이 스캔 파생물의 '출생신고서'다):",
   "",
   "```text",
   SOURCE_TXT.rstrip(),
   "```",
   "",
   "← 출처: `assets/meshes/cad/SOURCE.txt` (전문 그대로)",
   "",
   "⚠ 위 인용문의 «report03» 은 **옛 리포트 번호**다. 지금 그 자리는 별편 2-3 "
   "«표적을 짓는다 — 메쉬와 재질»(`reports/02_3_target-mesh.ipynb`)과 이 시리즈 mesh08 이다.",
   "",
   "표적 기체 중 왜 Phantom 4 만 스캔이 있나 — **공개된 실기체 고해상도 스캔이 사실상 이것뿐**",
   "이기 때문이다. 2016년 인기 기종이라 3D 프린팅 커뮤니티(Thingiverse)에 실물 스캔이 올라온",
   "드문 경우다. 최신 기종(Mini 5 Pro·Mavic 4 Pro·Matrice 4E)은 공개 스캔이 없어, 형상 검증은",
   "Phantom 4 한 기체로 방법을 확립하고(→ mesh08 스캔 대조) 나머지는 공식 외형 치수로 검증한다.",
   ),

# 9 ── §2.1 npz 전처리 ------------------------------------------------------------
md("## 2.1 왜 원본 STL 을 저장소에 안 넣고 npz 로 전처리했나",
   "",
   f"원본 STL 은 {STL_MB} MB·삼각형 {TRIS}개다. 이걸 그대로 쓰지 않은 이유는 세 가지다:",
   "",
   f"1. **용량** — git 저장소에 {STL_MB} MB 바이너리는 부적절하다. 전처리 결과",
   f"   `phantom4_scan_points.npz` 는 **{npz_mb:.2f} MB** (약 {compress_x:.0f}배 압축)로,",
   f"   점 {G['n_scan']:,}개(P=위치[m], N=법선, dA=면적[m²])만 담는다.",
   "2. **물리적으로 충분** — 우리 용도는 PO(물리광학) RCS 비교다. PO 적분에 필요한 것은",
   "   '표면 어디에(P), 어느 방향으로(N), 얼마만큼의 면적(dA)이 있나'뿐이라 삼각형 연결정보가",
   "   필요 없다. 3 mm 격자로 뭉쳐도(클러스터) 파장 대비 충분히 조밀하다(아래 docstring).",
   "3. **라이선스 관리** — 파생물임과 저작자를 `SOURCE.txt` 한 파일로 명시하고, 원본은",
   "   공식 미러(archive.org)에서 받게 한다. 원본 재배포를 우리가 떠안지 않는다.",
   "",
   "전처리 스크립트의 docstring 이 처리 단계와 그 이유를 전부 기록하고 있다:",
   "",
   "```text",
   PREP_DOC,
   "```",
   "",
   "← 출처: `src/prep_cad_scan.py` (모듈 docstring 전문) · 상수 확인: "
   f"`SCALE={prep_cad_scan.SCALE}` (mm→m ×1.0125 보정), `CELL={prep_cad_scan.CELL}` m"
   " (`src/prep_cad_scan.py`)",
   "",
   "**스케일 보정 ×1.0125 의 근거**: 스캔의 모터 허브 대각을 재면 345.7 mm 인데 공식 대각은",
   f"{d['phantom4'].diagonal_mm:g} mm 다(← 출처: 위 docstring ③ · `docs/SPECS.md` Phantom 4)."
   " 스캐너 보정 오차로 보고 전역 ×1.0125 를 곱했다 — 형상은 그대로 두고 자만 맞추는 보정이다.",
   "",
   "**재현 방법** (원본이 필요하면 미러에서 직접):",
   "",
   "```bash",
   CURL,
   "# 압축 해제 후 src/prep_cad_scan.py 상단의 STL 경로를 맞추고:",
   "python src/prep_cad_scan.py   # → assets/meshes/cad/phantom4_scan_points.npz",
   "```",
   "",
   "← 출처: `src/prep_cad_scan.py` docstring 의 재현 명령",
   ),

# 10 ── §2.2 스캔의 한계 ----------------------------------------------------------
md("## 2.2 스캔 데이터의 한계 — 알고 쓰는 것",
   "",
   f"- **프로펠러·짐벌 카메라가 없다.** 스캔 대상 실기체가 프롭·짐벌을 뗀 상태였다. 그래서",
   "  우리 메쉬와 A/B 비교할 때는 **우리 쪽도 같은 그룹(prop·camera)을 제외**하고 비교한다 —",
   f"  \"{SRC['note']}\" ← 출처: `mesh_verify.json[\"G_scan\"][\"source\"][\"note\"]` · `SOURCE.txt` 비고",
   "- **스캔 아티팩트 ~0.8 %** — 비다양체(non-manifold: 면이 제대로 안 이어진 곳)·부유 링",
   "  조각이 있으나, 면적이 미미해 면적가중 클러스터 합산에서 무시 가능하다.",
   "  ← 출처: `src/prep_cad_scan.py` docstring '주의'",
   "- **한 기체뿐** — §2 말미에 쓴 대로, 공개 실기체 스캔이 있는 기종이 Phantom 4 뿐이다.",
   "",
   f"실제 대조 결과(스캔 {G['n_scan']:,}점 ↔ 우리 메쉬 {G['n_cad']:,}점, 중앙값 거리"
   f" {G['scan_to_cad_mm']['p50']:.1f} mm)는 **mesh08(실물·물리 검증 편)** 에서 그림과 함께 다룬다 —",
   "여기서는 '이 데이터가 어디서 왔고 무엇이 빠졌나'까지만.",
   ),

# 11 ── §3 실물 CAD ---------------------------------------------------------------
md("## 3. 실물·공식 CAD — 어디서, 어떤 라이선스로, 그리고 어디까지 쓰나",
   "",
   "우리 메쉬 생성 **방법**(스펙 → 파라메트릭 CAD)이 옳은지 확인하려면 '정답 CAD 가 있는",
   "실물 드론'과 대조해야 한다. 그 정답이 **기체마다 있고 없다**:",
   "",
   "> " + Q_SOURCES_WARN.replace("\n", "\n> "),
   "",
   "← 출처: `assets/meshes/reference/SOURCES.md` (원문 그대로)",
   "",
   "### 3.0 제조사 공식 CAD 세 개 — 그리고 축척 검산",
   "",
   "| 파일 | 무엇 | 축척 검산 | 이 저장소에서의 지위 |",
   "|---|---|---|---|",
   "| `matrice4-M4T_v2.step` | DJI **Matrice 4T** 공식 STEP (Creo, mm) | 폭 **387.51** ↔ 공표 387.5 mm "
   "(+0.003 %) | matrice4e 형상 상수의 1차 근거 ⚠ **짐벌 제외** |",
   "| `WM161_zhankai_1k.glb` | DJI **Mini 2** 공식 3D(펼침) | 프롭 제외 bbox **159.11 × 203.43 × 55.98** "
   "↔ 공표 159×203×56 · 모터 대각 **213.05** ↔ 공표 213 | mini2 **전 형상 상수**의 근거 |",
   "| `x500v2-frame.step` | Holybro **X500 V2** 프레임 어셈블리 (STEP AP214) | 판 143.72 · 모터원 502.8 · "
   "판 간격 28.00 mm | x500v2 치수의 1차 근거 |",
   "",
   "← 출처: `assets/meshes/reference/SOURCES.md` 각 절(원본 URL·md5 포함).",
   "",
   "⭐ **M4T 는 우리 표적이 아니다.** 표적은 Matrice 4**E** 이고 DJI 는 4E 판 CAD 를 공개하지 않는다",
   "(403). 그래서 이 CAD 는 **부품군별로 갈라 쓴다** — 이것이 상시 규칙이다:",
   "",
   "| 부품군 | 4T ↔ 4E | CAD 를 써도 되나 |",
   "|---|---|---|",
   "| 셸(동체)·팔·다리·모터 | 공용 | ✅ 그대로 |",
   "| 어안·비전 센서·비콘 위치 | 공용 | ✅ 그대로 |",
   "| RTK 안테나 | 공용 | ✅ 그대로 |",
   "| ⚠ **짐벌·카메라 블록** | **다르다** — 탑재체가 갈리는 지점 | ⛔ **치수는 쓰지 마라.** "
   "매다는 자리(크래들·댐핑플레이트)만 공용이라 **위치는** 써도 된다 |",
   "| 내부 기판·배터리 | CAD 는 외장 모델이라 애초에 없다 | — |",
   "",
   "← 출처: `docs/MESH_AUDIT_0816.md` §⑧ (사용자 지시로 세운 상시 규칙) · "
   "`outputs/meshfix_matrice4e.json` `_meta.variant_warning`.",
   "",
   "⚠ 남은 불확실: «4T 와 4E 의 기체가 공용» 이라는 것은 제원·매뉴얼 대조에서 나온 판단이고,",
   "부품 단위로 전수 대조한 것은 아니다.",
   "",
   "### 3.0.1 두 파일은 저장소에 없다 — 재현하는 법",
   "",
   "`matrice4-M4T_v2.step`(158 MB)은 이력에 영구히 박히는 것을 피하려고 **의도적으로 제외**했다.",
   "재현 경로가 셋이고, 어느 경로로 받든 **md5 `51ff9a47fac2c4c7a9d3817d5444f74d`** 여야 한다",
   "← 출처: `assets/meshes/reference/SOURCES.md`.",
   "",
   "⭐ **그 CAD 에서 뽑아낸 것은 저장소에 있다** — `outputs/meshfix_matrice4e.json` 이 정정",
   "14건의 측정값·근거·출처를 전부 들고 있어서, 원본 없이도 «무엇을 어떤 값으로 고쳤는지» 는",
   "저장소만으로 읽힌다. 원본이 필요한 것은 그 측정을 **다시 재고 싶을 때**뿐이다.",
   "",
   "### 3.0.2 ⭐ Mini 2 GLB 안에는 **DJI 실물 프로펠러 날**도 들어 있다",
   "",
   "출처 장부로서 이 편이 반드시 적어야 하는 사실이다. `WM161_zhankai_1k.glb` 는 셸만 담은 파일이",
   "아니라 **날 8장 + 허브 4개**를 함께 담고 있다 — 즉 **이 저장소에는 DJI 프로펠러의 실물 기하가",
   "있다.**",
   "",
   "| 무엇 | 측정값 | 어떻게 알았나 |",
   "|---|---|---|",
   "| 날·허브 개수 | 날 **8장**(1635×4 + 1691×4 삼각형) · 허브 **4개**(1704×4) | 면수 히스토그램 |",
   "| 프롭 디스크 지름 | **118.13~119.07 mm**(평균 118.60) ↔ 공칭 4726F 119.4 mm(**−0.67 %**) "
   "| 로터별 최적중심 최대반경 |",
   "| 회전축 | 월드 **+y**(4로터 편차 0.001) | 허브 관성주축 실측 |",
   "",
   "← 출처: `docs/MESH_AUDIT_0816.md` C3 · 부록 D-1 #4·#5(별도 검증자가 GLB 를 새로 열어 재현).",
   "이 사실은 원장 `outputs/reference_props.json` 에도 `meta.retraction_20260816` 으로 실려 있다 —",
   "그 파일의 옛 문면(«저장소에 DJI 프로펠러 실물 기하는 존재하지 않는다»)이 **지금은 거짓**임을",
   "원장 스스로 선언한다.",
   "",
   "⚠ **GLB 를 얼마나 믿을 것인가** — 이 파일은 **제품 뷰어용 1k 간략화판**이지 계측 스캔이 아니다.",
   "실루엣·평면형은 믿을 만하고(Mini 2 실물 사진과 +4 % 안에서 일치), **두께는 날 1장이",
   "1635~1691 삼각형뿐이라 ±10 % 로 읽어야 한다** ← 출처: `docs/MESH_AUDIT_0816.md` 부록 C.",
   "mini2 를 «형상 근거 등급이 가장 높은 기체» 로 세우는 것도 이 한계와 함께 읽을 것.",
   "",
   "⭐ **이 날이 지금 하는 일 두 가지.** 출처 장부로서 여기까지 적는다 —",
   "무엇을 어떤 값으로 썼는지의 정본은 mesh05(프로펠러 편)다.",
   "",
   f"1. **Mini 2 자신의 날의 1차 근거**다 — 등급 **[{CLAW['mini2']['grade']}]**"
   f"(불확실도 ±{CLAW['mini2']['uncertainty_pct']:g} %), 두께는 이 함대에서 **절대값[mm]으로"
   f" 잰 유일한 프롭**이다({_cell(CLAW['mini2']['t_note_ko'])}).",
   "2. **다른 기체의 사진이 못 주는 구간을 채우는 기준곡선**이다(뿌리 안쪽·팁 바깥). 이유는 하나 —",
   "   저장소에서 **스팬 전체가 [A] 인 프롭이 이것뿐**이라서다. 그 구간은 [D]/[C] 로 따로 적힌다.",
   "",
   "← 출처: `outputs/prop_law_by_airframe_0816.json` `C_law_by_airframe.mini2` ·"
   " `B_reference_curve_mini2_A`.",
   "",
   "### 3.1 로보틱스 저장소의 실물 CAD — 채점자 · 그리고 프로펠러 자료",
   "",
   "**CAD 가 공개된 실물 드론**을 로보틱스 시뮬레이터 저장소에서 가져왔다.",
   "이 저장소들을 고른 이유: (1) **실제 판매 제품**의 형상이고, (2) PX4/ETH 취리히가",
   "시뮬레이션용으로 검수해 왔으며, (3) 라이선스가 허용적(Apache-2.0·BSD-3)이라 연구 사용에",
   "제약이 없다.",
   "",
   SOURCES_TABLE,
   "",
   "← 출처: `assets/meshes/reference/SOURCES.md` 첫 표(원문 그대로) — 파일 실물은"
   " `assets/meshes/reference/` 에 있다",
   "",
   "⭐ **이 표의 프로펠러 셋은 지위가 서로 다르다.** 셋 다 실측 원장이 있다 —",
   "`outputs/reference_props.json`(디스크 지름 1345 **346.66** · Solo **253.82** ·",
   "Yuneec **230.10** mm, 반경 36 스테이션에서 시위·두께·비틀림을 잰 표). 지금 쓰이는 자리는:",
   "",
   "- **Typhoon H480 프롭 어셈블리** — 그 기체 **자신의** 프롭이다. Typhoon H480 평면형의 1차 자료"
   f"(등급 **[{CLAW['typhoonh480']['grade'].replace('-', '−')}]**, §3.1.2).",
   "- **3DR Solo · PX4 1345** — **어느 표적 기체의 형상도 정하지 않는다.** 실물 프롭이 서로 얼마나",
   "  다른지 견주는 교차검증 자료다. 실제로 이 셋은 한 덩어리가 아니다 — **1345·Solo 는 뿌리 편중형,",
   "  DJI 계열은 정점이 바깥쪽**이라 «참조 프롭 하나를 대표로 쓴다» 가 성립하지 않는다",
   "  ← 출처: `outputs/mesh_adversarial_verdict_0816.json`.",
   "",
   "⚠ 그 원장이 스스로 붙여 둔 단서 둘도 함께 읽어야 한다 ← 출처: 같은 파일 `meta`:",
   "",
   "- 세 CAD 는 **시뮬/시각화용이지 계측 스캔이 아니다.** 1345 는 워시아웃이 0 이라 비틀림 기준으로 쓸 수 없다.",
   "- 측정 방법은 «스팬축 수직 평면 절단» 이 아니라 **원통 단면**이다"
   "(`meta.method_correction_20260816` — 측정값은 그대로고 방법 설명 문면만 정정됐다).",
   "",
   "### 3.1.1 제조사 배포물이지만 공개 라이선스가 없는 것 — 두 건",
   "",
   SOURCES_TABLE_MFR,
   "",
   "← 출처: `assets/meshes/reference/SOURCES.md` 둘째 표. 위 표(Apache-2.0·BSD-3)와 달리",
   "**재배포 조건이 표기돼 있지 않아** 저장소는 이 둘을 «내부 참조용» 으로 다룬다(§5).",
   "",
   f"단위 규약도 문서에 있다: \"{Q_SOURCES_UNIT}\"",
   "← 출처: `assets/meshes/reference/SOURCES.md`",
   ),

# 11b ── §3.1.2 기체별 프로펠러 1차 자료 장부 -------------------------------------
md(f"## 3.1.2 ⭐ 기체별 프로펠러의 1차 자료 — {len(ORDER)}기체 출처 장부",
   "",
   "프로펠러는 **기체마다 그 기체의 순정 프롭**이다. 그래서 «프롭 자료» 라는 한 칸이 아니라",
   f"기체 {len(ORDER)}줄이 필요하다. 아래가 그 장부다 — 어느 파일에서 왔고, 등급이 얼마이며,",
   "얼마나 흔들리는지까지.",
   "",
   "| 기체 | 프롭 모델 | 등급 | 불확실도 | 1차 자료(파일·무엇을 봤나) |",
   "|---|---|---|---|---|",
   PROP_SOURCE_TABLE,
   "",
   "← 출처: `outputs/prop_law_by_airframe_0816.json` `C_law_by_airframe`"
   "(`prop`·`grade`·`uncertainty_pct`·`source`). 평면형 수치(최대시위 c_max/R·시위 정점 위치)와"
   " 그 값이 무엇을 바꾸는지는 **mesh05(프로펠러 편)** 가 정본이다 — 여기서 두 번 적지 않는다.",
   "",
   f"⚠ **불확실도가 ±{PROP_UNC_MIN:g} % 에서 ±{PROP_UNC_MAX:g} % 까지 벌어진다.** 같은 표에 있다고",
   "같은 무게가 아니다. 특히 **대리로 세운 자리가 둘**이다 — "
   + " · ".join(f"**{DRONES[k].name}**(← {DRONES[CLAW[k]['proxy_of']].name} 의 프롭)"
               for k in PROP_PROXY)
   + ". 자체 측정이 하나도 없다는 뜻이므로, 이 두 기체의 프롭 형상은 «잰 값» 이 아니라",
   "**«같은 급이라고 본 값»** 으로 읽어야 한다.",
   "",
   "원장이 스스로 적어 둔 구멍을 그대로 옮긴다 (← 같은 파일 `F_gaps`):",
   "",
   *PROP_GAP_LINES,
   "",
   "⭐ **빈칸을 채우지 않는 것이 규율이다.** 위 목록의 «두께 8기종 빈칸» 은 게을러서가 아니라",
   "사진으로는 **원리적으로** 못 재기 때문이다(겉보기 높이는 시위와 두께가 섞인 값이고 앞항이",
   "훨씬 크다). 값을 지어내는 대신 비워 두고, 그 사실을 여기 적는다.",
   ),

# 12 ── §3.1 검증 전용 원칙 -------------------------------------------------------
md("## 3.2 ⭐ 참조 자료가 실제로 제작에 들어간 자리 — 세 군데",
   "",
   "«다운로드한 모델은 채점에만 쓰고 제작에는 안 쓴다» 는 깔끔한 문장이지만, 지금 상태를 정확히",
   "말하면 **제조사 공식 CAD 는 제작에도 들어간다.** 감추면 «독립 채점» 이 과장이 되므로 적어 둔다.",
   "",
   "| # | 어디에 | 무엇이 들어갔나 | 등급 |",
   "|---|---|---|---|",
   "| ① | **matrice4e 형상 상수 14건** | DJI Matrice 4T 공식 STEP 의 모서리 실측 "
   "(접지 −59.82 · 갑판 crown 69.18 · RTK 꼭대기 89.70 · 셸 중심 x 41.71 mm 를 0.1 mm 안에서 재현) "
   "| **[A] 공식 CAD 직접** |",
   "| ② | **mini2 전 형상 상수** | DJI 공식 GLB(WM161 펼침) 실측 — 셸 6 스테이션 중 가운데 4개가 "
   "GLB 와 0.5 % 안. `shape_source=\"manufacturer_cad\"` 로 선언돼 있다 | **[A] 공식 CAD 직접** |",
   "| ③ | **프로펠러 날 평면형 — 기체마다 따로** | 그 기체 순정 프롭의 실측(공식 3D · 제품사진 · "
   "시뮬레이터 자산). 뿌리·팁의 못 잰 구간만 Mini 2 [A] 곡선으로 잇는다 "
   f"| **기체마다 다르다** — {PROP_GRADE_GROUPS} (§3.1.2) |",
   "",
   "← 출처: ①은 `outputs/meshfix_matrice4e.json` + `outputs/mesh_inspect_body_arms_0816.json` "
   "`meshfix_matrice4e_landed`(착지 검증) · ②는 같은 파일 `per_drone.mini2` · "
   "③은 `outputs/prop_law_by_airframe_0816.json` `C_law_by_airframe` + `src/geom.py` "
   f"`BLADE_LAW_CANON=\"{BLADE_LAW}\"`.",
   "",
   "⭐ **③ 이 이 표에서 가장 조심할 칸이다.** ①② 는 한 기체에 한 근거지만, ③ 은 **기체마다 근거가",
   "다르다** — 공식 3D([A]) 부터 근거 0([D] 대리)까지 한 표 안에 있다. 그래서 «프로펠러는 실물"
   f" 측정에서 왔다» 라고 뭉뚱그리면 {len(PROP_PROXY)}기체가 과장된다.",
   "",
   "**그래서 «독립 채점» 이라는 말은 이렇게 써야 한다:**",
   "",
   "> 채점자 중 **실기체 3D 스캔(Phantom 4, CC-BY)** 은 제작에 한 번도 안 들어갔다 —",
   "> 그 기체에 대해서는 채점이 진짜로 독립이다.",
   "> 반대로 matrice4e·mini2 의 공식 CAD 는 **제작에 들어갔으므로**, 같은 CAD 로 다시 채점한",
   "> 결과는 «맞췄다» 가 아니라 **«정정이 착지했다»** 로 읽어야 한다.",
   ),

# 12b ── §3.3 그 밖의 다운로드물 -------------------------------------------------
md("## 3.3 그 밖의 다운로드물은 채점 전용",
   "",
   "`SOURCES.md` 가 그 용도를 적는다:",
   "",
   f"> {Q_SOURCES_RULE}",
   "",
   "← 출처: `assets/meshes/reference/SOURCES.md` (원문 그대로)",
   "",
   "공식 CAD 가 **없는** 기체에 대해 인터넷 3D 모델을 표적으로 쓰지 않는 이유는 셋이다:",
   "",
   "1. **시각용 껍데기** — 렌더링용 모델은 껍데기(shell)뿐이라 내부의 배터리·모터·기판 같은",
   "   **금속 산란체가 없다**. RCS 는 금속이 지배하므로 치명적 결손이다.",
   "2. **치수 미검증** — 누가 어떤 자로 만들었는지 모른다. 우리는 §1 의 검증된 제원으로",
   "   치수를 강제할 수 있어야 한다.",
   "3. **라이선스 제약** — 다수가 개인용/비상업 조건이거나 라이선스 불명이다.",
   "",
   f"그래서 표적 {len(ORDER)}종은 전부 `src/drone_cad.py` 가 **공표 제원 수치에서 생성**한다",
   f"(엔진: {V['meta']['mesh_engine']}). 공식 CAD 가 있는 기체(matrice4e·mini2·x500v2)만 그 위에 "
   "CAD 실측이 얹힌다(§3.2).",
   "",
   "⚠ **두 기체는 표적이면서 동시에 자기 채점 기준이다** — Typhoon H480 과 X500 V2 는 표적",
   "목록에 올라 있고, 그 실물 CAD 도 저장소에 있다. 그 경우에도 표적 메쉬 자체는 파라메트릭",
   "생성이고(다운로드 메쉬는 부위별 재질이 없어 RCS 엔진에 못 쓴다), CAD 는 치수 근거로만 쓴다.",
   "**라이선스 의무가 내부 점검이 아니라 배포되는 표적 모델에 붙는다**는 점도 그 문서가 적는다",
   "← 출처: `assets/meshes/reference/SOURCES.md`.",
   ),

# 13 ── §4 갤러리 그림 ------------------------------------------------------------
md("## 4. 원본 갤러리 — 다운로드한 그대로",
   "",
   "아래 그림이 이번 편에서 소개한 '남의 자료' 전부다. 가공 전 원본 상태로 보여준다:",
   "",
   "![originals gallery](outputs/figures/originals_gallery.png)",
   "",
   "- **(왼쪽) Phantom 4 실기체 스캔** — npz 점구름에서 9,000점을 추려 높이(z)로 색칠했다."
   f" 총 {G['n_scan']:,}점. 몸통·고정암·랜딩 다리가 보이고, **프로펠러·짐벌이 없는 것**(§2.2)도"
   " 그림에서 확인된다. 제목에 저작자·라이선스를 박아 두었다"
   f" ({SRC['thing']}, {SRC['license']}, {SRC['author'].split('/')[0]}).",
   "- **Yuneec Typhoon H480** — 실물 헥사콥터(로터 6개)의 CAD 조립:"
   " 동체+다리+프롭+CGO3 짐벌. ethz-asl/rotors_simulator, Apache-2.0.",
   "- **DJI Matrice 100·600 Pro** — 커뮤니티 시각용 메쉬. 프로펠러를 **회전 원판**으로 그린"
   " 껍데기(정밀 CAD 아님)라 형상이 거칠다. 이 둘은 우리 표적이 아니고, **형상 거칠기가 σ 에"
   " 주는 영향**을 보는 대조군으로만 등장한다.",
   "",
   "그림 제목이 다시 한 번 원칙을 말한다 — *\"Downloaded ORIGINALS, shown as received — scoring",
   "references, not build inputs\"*. ⚠ 예외는 **Typhoon H480 프롭** 하나다 — 그 기체는 자기",
   "프롭이 여기 있어 평면형의 1차 자료가 된다(§3.1·§3.1.2).",
   "",
   "← 그림 생성: `report_mesh/src/viz_mesh_reports.py` `fig_originals()` —",
   "스캔은 npz 에서 직접, CAD 2종은 `mesh_compare.load_reference()`/`typhoon_h480_real()` 로"
   " 원본 STL 을 읽어 그렸다.",
   ),

# 14 ── §5 라이선스 존중 ----------------------------------------------------------
md("## 5. 라이선스를 어떻게 지켰나",
   "",
   "| 라이선스 | 한 줄 뜻 | 우리 의무 | 어디에 기록했나 |",
   "|---|---|---|---|",
   f"| {SRC['license']} (스캔) | 저작자표시 조건 자유 이용 | 저작자({SRC['author']})·출처·"
   "파생물임을 명시 | `assets/meshes/cad/SOURCE.txt` + 그림 제목 + 본 리포트 §2 |",
   "| Apache-2.0 (Typhoon·Solo) | 허용적 SW 라이선스 | 출처 저장소·라이선스 표기 유지 "
   "| `assets/meshes/reference/SOURCES.md` 첫 표 + 그림 제목 |",
   "| BSD-3-Clause (PX4 부품) | 허용적 SW 라이선스 | 출처·라이선스 표기 유지 "
   "| `assets/meshes/reference/SOURCES.md` 첫 표 |",
   "| ⚠ **공개 라이선스 없음** — DJI Matrice 4T STEP · DJI Mini 2 GLB 2종 "
   "| DJI 저작물이다 | **파일 자체를 재배포하지 않는다.** 형상 대조·치수 근거로만 쓴다 "
   "| `SOURCES.md` 각 절의 라이선스 문단(«재배포하지 말 것») |",
   "| ⚠ **재배포 조건 미표기** — Holybro X500 V2 프레임 STEP · AIR2216II 모터 STEP "
   "| 제조사 배포물 | **내부 참조용**으로만 둔다 | `SOURCES.md` 둘째 표 |",
   "",
   "⭐ **위 두 줄이 이 편에서 가장 조심해야 할 칸이다.** 그 넷은 «채점만 하는 자료» 가 아니라",
   "**형상 상수의 근거로 제작에 들어간 자료**인데(§3.0·§3.2), 공개 라이선스가 없다. 그래서 규약이",
   "이렇다 — **파일은 배포하지 않고, 그 파일에서 잰 «숫자와 근거» 만 원장으로 배포한다**",
   "(`outputs/meshfix_matrice4e.json` 이 그 예다, §3.0.1).",
   "",
   "구체적으로 한 일:",
   "",
   "1. **파일 옆 기록** — 다운로드물이 놓인 두 폴더에 각각 출처 문서를 두었다:",
   "   `assets/meshes/cad/SOURCE.txt`(스캔), `assets/meshes/reference/SOURCES.md`(CAD 표).",
   "2. **파생물 명시** — npz 는 원본 STL 의 가공물이므로, `SOURCE.txt` 에 \"전처리한",
   "   파생물이며 동일 라이선스·저작자표시를 따른다\"고 적었다(§2 전문 인용 참고).",
   "3. **그림에도 표시** — 원본이 등장하는 그림(§4)의 패널 제목에 출처·라이선스를 직접 넣어,",
   "   그림만 따로 떠돌아도 저작자표시가 유지되게 했다.",
   "4. **원본 재배포 회피** — 154 MB 원본은 저장소에 넣지 않고 공식 미러 링크로 대체(§2.1).",
   "",
   "← 출처: `assets/meshes/cad/SOURCE.txt` · `assets/meshes/reference/SOURCES.md` ·"
   " `report_mesh/src/viz_mesh_reports.py` (그림 제목 문자열)",
   ),

# 15 ── §6 출처 지도 --------------------------------------------------------------
md("## 6. 정리 — 무엇의 진리원(source of truth)이 어디인가",
   "",
   "| 알고 싶은 것 | 이 파일을 보라 | 성격 |",
   "|---|---|---|",
   "| 기체 제원의 근거·공식/추정 구분·URL | `docs/SPECS.md` | 사람용 요약(조사+검증) · **DJI 5종 전용** |",
   f"| 조사·검증의 원자료(JSON) | `docs/drone_research.json` | research/verify 두 블록 × {len(ORDER)}기체 |",
   "| **코드가 실제 쓰는 스펙값**과 채택 이유, 비-DJI 5종의 제원 출처 | `src/drones.py` "
   "(`DroneSpec.note`) + `docs/RESUME_0729.md` §5 | 최종 채택 |",
   "| 사진에서 잰 형상 상수와 그 픽셀 근거 | `src/drone_cad.py` "
   "(`_SHELL_SHAPE`·`_ARM_WIDTH`·`_ARM_SECTION`) + `assets/photos/` | 등급 [B] 의 실체 |",
   "| 실기체 스캔의 출처·라이선스·전처리 | `assets/meshes/cad/SOURCE.txt` + `src/prep_cad_scan.py` | 파생물 기록 |",
   "| 실물·공식 CAD 의 출처·라이선스 | `assets/meshes/reference/SOURCES.md` | 제작 근거 + 채점자 |",
   "| matrice4e 정정 14건의 측정값·근거 | `outputs/meshfix_matrice4e.json` | 원본 CAD 없이도 읽힌다 |",
   "| 참조 프로펠러 3종의 측정 | `outputs/reference_props.json` | Typhoon H480 의 1차 자료 + 교차검증 |",
   "| **기체별 프롭의 모델명·등급·불확실도·구멍** | `outputs/prop_law_by_airframe_0816.json` "
   "| §3.1.2 장부의 원본 |",
   "| **저장소 «밖»의 참값과 견준 결과** | `outputs/mesh_cert_dimension_external_0816.json` "
   f"(검사 본체 `src/mesh_dimref.py::REFS`) | {DR_N}행 — 우리가 적은 수가 아니라 남의 수와 견준다 |",
   "| **무엇을 장담하고 무엇은 못 하는가** | `docs/MESH_CERTIFICATE.md` | 판정 «조건부 장담» |",
   "| 메쉬 측정치(이 시리즈의 수치) | `report_mesh/outputs/mesh_verify.json` | 검증 스위트 출력 |",
   "",
   "⭐ **출처 장부가 반드시 함께 읽어야 하는 축이 하나 더 있다 — «바깥 참값».** 위 표의 대부분은",
   "«우리가 무엇을 보고 적었나» 를 말하지만, 그 값이 실물과 맞는지는 다른 문제다. 인증서의 치수 축이",
   f"그 자리를 맡는다: 참값 **{DR_N}행** 중 **{DR_IND}행**만이 «순환이 아닌»(우리 상수를 우리가 다시",
   f"읽은 것이 아닌) 독립 행이고, 그중 {DR_IND_A}행이 공식 CAD·공표 직접이다. 그리고 지금",
   f"**{DR_MISMATCH}행이 어긋나 있다**(자세한 것은 mesh08).",
   "",
   "⛔ **독립 참값이 한 줄도 없는 기체가 둘이다** — "
   + " · ".join(DRONES[k].name for k in DR_NO_INDEP)
   + ". 이 둘의 «치수가 맞다» 는 말은 **우리 수를 우리가 다시 읽은 것**이라는 뜻이다"
     " ← 출처: `docs/MESH_CERTIFICATE.md` §3.3.",
   "",
   "이번 편의 요점 세 가지:",
   "",
   f"1. 표적 {len(ORDER)}종의 치수는 **조사→독립검증 2단계**를 거친 스펙에서 왔고, 추정값(Mini"
   f" {research_diag('mini5pro'):g}→{d['mini5pro'].diagonal_mm:g}, Mavic"
   f" {research_diag('mavic4pro'):g}→{d['mavic4pro'].diagonal_mm:g} mm)은 추정임을 명시한 채",
   "   공식 외형과의 일관성으로 재유도했다.",
   "2. 자료는 **층마다 지위가 다르다** — 공표 제원과 사진은 전 기체의 제작 입력이고, 공식 CAD 는"
   "   가진 기체(matrice4e·mini2·x500v2)에서 제작에 들어가며, **실기체 스캔만이 제작에 한 번도"
   "   안 들어간 진짜 독립 채점자**다. 프로펠러는 **기체마다 자기 자료**를 갖고(§3.1.2), 참조"
   "   프로펠러 셋 중 Typhoon H480 것만 그 기체의 1차 자료이며 나머지 둘은 교차검증 자료다.",
   "3. 라이선스도 층마다 다르다 — 스캔은 CC-BY, 로보틱스 저장소는 Apache-2.0·BSD-3,"
   "   **DJI·Holybro 배포물은 공개 라이선스가 없어 파일을 재배포하지 않는다**(§5).",
   "   모든 다운로드물 옆에 출처 문서를 두어, 누구든 같은 자료를 같은 조건으로 다시 구할 수 있다.",
   ),

# 16 ── 재현 + 다음 편 ------------------------------------------------------------
md("---",
   "",
   "## 재현 방법",
   "",
   "```bash",
   "# 이 노트북 재생성",
   "/workspace/.venvs/py312/bin/python report_mesh/src/make_mesh03.py",
   "",
   "# 정본 판 원장 재생성(이 시리즈 수치의 기본 — 스위치를 안 주면 정본이다)",
   "/workspace/.venvs/py312/bin/python report_mesh/src/verify_mesh_canon_0817.py",
   "/workspace/.venvs/py312/bin/python report_mesh/src/mesh_canon_0817.py",
   "",
   "# 그림 재생성",
   "/workspace/.venvs/py312/bin/python report_mesh/src/viz_mesh_reports.py",
   "",
   "# 스캔 원본이 필요하면 (154 MB, 저장소 밖):",
   CURL,
   "```",
   "",
   "⭐ **어느 판을 말하는 원장인가.** 이 편이 인용하는 프롭 등급·자료는 **정본 판**의 것이다.",
   "지금 기본으로 켜져 있는 스위치는 이렇다:",
   "",
   CAN.switch_table(),
   "",
   *CAN.switch_note(),
   "",
   "**다음 편** → `mesh04_*.ipynb`: 여기서 수집한 스펙이 실제로 어떻게 3D 메쉬가 되는지 —",
   "파라메트릭 CAD 생성 파이프라인으로 넘어간다.",
   ),
]

nb = {"cells": cells,
      "metadata": {"kernelspec": {"display_name": "py312", "language": "python",
                                  "name": "py312"},
                   "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 5}
out = os.path.join(RM, "mesh03_data_sources.ipynb")
for _i, _c in enumerate(nb["cells"]):
    _c["id"] = f"m03-{_i:02d}"

json.dump(nb, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("wrote", out, len(cells), "cells")
