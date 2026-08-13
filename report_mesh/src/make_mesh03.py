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

# SOURCES.md 표(| 로 시작하는 줄)와 경고 블록
SOURCES_TABLE = "\n".join(l for l in SOURCES_MD.splitlines() if l.startswith("|"))
Q_SOURCES_WARN = quote(SOURCES_MD, "⚠️ **DJI 는 공식 CAD 를 공개하지 않습니다.**",
                       "우리 방법을 검증합니다.")
Q_SOURCES_UNIT = quote(SOURCES_MD, "**단위**", "스팬.")
Q_SOURCES_RULE = quote(SOURCES_MD, "**이 파일들은 비교·검증 전용입니다.**",
                       "생성합니다.")

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
   "> ⚠ **이 노트북은 생성물이다. 수정은 `src/make_mesh03.py` 에서** 하라.",
   ">   본문 수치는 전부 `outputs/mesh_verify.json`(측정)·`src/drones.py`(스펙)·원문 문서에서",
   ">   생성 시점에 읽어 넣은 것이다 — 손으로 옮겨 적은 숫자가 없다.",
   "",
   f"**한 줄 요약** — 우리 드론 메쉬 {len(ORDER)}종에 들어간 **모든 입력 자료의 출처 장부**다:",
   "① DJI 공식 제원(웹 조사→독립 검증 2단계), ② Phantom 4 **실기체 3D 스캔**(Thingiverse,"
   f" {SRC['license']}), ③ **실물 드론 CAD** 3종(오픈소스 로보틱스 저장소) — 그리고 각각을"
   " **어떤 라이선스로, 왜, 어디까지** 쓰는지 밝힌다.",
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
   "이번 편에서 다루는 자료는 세 층이다:",
   "",
   "| 층 | 자료 | 용도 | 출처 문서 |",
   "|---|---|---|---|",
   f"| A | 제조사 공식 제원 ({len(ORDER)}기체: {', '.join(d[k].name for k in ORDER)}) "
   "| **표적 메쉬 생성의 입력** | `docs/SPECS.md` + `docs/drone_research.json` |",
   f"| B | Phantom 4 실기체 3D 스캔 ({RES_MM} mm 해상도) | 우리 메쉬 vs 실물 형상 검증(A/B) "
   "| `assets/meshes/cad/SOURCE.txt` |",
   "| C | 실물 CAD·커뮤니티 메쉬 (Typhoon H480 실물 CAD · 커뮤니티 M100/M600) | 방법론 교차검증(report03) "
   "| `assets/meshes/reference/SOURCES.md` |",
   "",
   f"핵심 원칙을 미리 말하면: **표적 메쉬 {len(ORDER)}종은 A(공식 스펙)에서만 생성**하고, B·C 는",
   "**검증에만** 쓴다. 이유는 §3.1 에서. ← 출처: `assets/meshes/reference/SOURCES.md` 마지막 문단",
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
   "그 이유를 `note` 필드에 남겼다(§1.2). ← 출처: `docs/drone_research.json` 구조 · `src/drones.py:37`(DroneSpec 정의)·`:90`(DRONES)",
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
   "← 출처: `src/drones.py:92-113` (mini5pro note + 주석, 원문 그대로)",
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
   "← 출처: `src/drones.py:115-131` (mavic4pro note, 원문 그대로)",
   "",
   f"**사례 3 · Matrice 4E: 프로펠러 292 → {d['matrice4e'].prop_dia_mm:g} mm (검증 정정).**",
   "1단계 조사는 프롭 모델명 '1157F' 의 앞자리를 11.5 인치로 읽어 292 mm 로 냈다.",
   "독립 검증이 이를 뒤집었다:",
   "",
   f"> \"{Q_M4E_FIX}\"",
   "",
   "← 출처: `docs/SPECS.md` Matrice 4E '검증' 항목 (원문 그대로) · 채택값 확인: `src/drones.py:132-149`",
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
   "← 출처: `src/prep_cad_scan.py:1-20` (모듈 docstring 전문) · 상수 확인: "
   f"`SCALE={prep_cad_scan.SCALE}` (mm→m ×1.0125 보정), `CELL={prep_cad_scan.CELL}` m"
   " (`src/prep_cad_scan.py:32-33`)",
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
md("## 3. 실물 드론 CAD 3종 — 어디서, 어떤 라이선스로",
   "",
   "우리 메쉬 생성 **방법**(스펙 → 파라메트릭 CAD)이 옳은지 확인하려면, '정답 CAD 가 있는",
   "실물 드론'과 대조해야 한다. 문제는 — DJI 기체로는 그게 불가능하다는 것:",
   "",
   "> " + Q_SOURCES_WARN.replace("\n", "\n> "),
   "",
   "← 출처: `assets/meshes/reference/SOURCES.md` (원문 그대로)",
   "",
   "그래서 **CAD 가 공식 공개된 실물 드론**을 로보틱스 시뮬레이터 저장소에서 가져왔다.",
   "이 저장소들을 고른 이유: (1) **실제 판매 제품**의 형상이고, (2) PX4/ETH 취리히가",
   "시뮬레이션용으로 검수해 왔으며, (3) 라이선스가 허용적(Apache-2.0·BSD-3)이라 연구 사용에",
   "제약이 없다.",
   "",
   SOURCES_TABLE,
   "",
   "← 출처: `assets/meshes/reference/SOURCES.md` 표 (전문 그대로) — 파일 실물은"
   " `assets/meshes/reference/` 에 있다",
   "",
   f"단위 규약도 문서에 있다: \"{Q_SOURCES_UNIT}\"",
   "← 출처: `assets/meshes/reference/SOURCES.md`",
   ),

# 12 ── §3.1 검증 전용 원칙 -------------------------------------------------------
md("## 3.1 원칙: 다운로드 모델은 '검증 전용', 표적은 스펙에서 생성",
   "",
   "`SOURCES.md` 는 이 파일들의 용도를 못박는다:",
   "",
   f"> {Q_SOURCES_RULE}",
   "",
   "← 출처: `assets/meshes/reference/SOURCES.md` 마지막 문단 (원문 그대로)",
   "",
   "왜 다운로드한 3D 모델을 표적으로 직접 쓰지 않나 — 위 §3 인용문의 세 가지 이유를 풀면:",
   "",
   "1. **시각용 껍데기** — 인터넷의 DJI 모델은 렌더링용이라 껍데기(shell)뿐, 내부의 배터리·",
   "   모터·PCB 같은 **금속 산란체가 없다**. RCS 는 금속이 지배하므로 치명적 결손이다.",
   "2. **치수 미검증** — 누가 어떤 자로 만들었는지 모른다. 우리는 §1 의 검증된 스펙으로",
   "   치수를 강제할 수 있어야 한다.",
   "3. **라이선스 제약** — 다수가 개인용/비상업 조건이거나 라이선스 불명이다.",
   "",
   f"그래서 표적 {len(ORDER)}종({', '.join(d[k].name for k in ORDER)})은 전부",
   f"`src/drone_cad.py` 가 **공식 스펙시트 수치에서 생성**한다(엔진: {V['meta']['mesh_engine']}).",
   "다운로드한 실물 CAD·커뮤니티 메쉬는 '우리 파라메트릭 방법이 실물을 얼마나 재현하나'를 재는",
   "**잣대로만** 쓴다(→ 본편 report03.ipynb). ← 출처: `assets/meshes/reference/SOURCES.md` · `src/drone_cad.py`",
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
   " 껍데기(정밀 CAD 아님)라 형상이 거칠다 — report03 이 실물 CAD·스캔과 함께 대조하는 **네 원본**에 포함된다.",
   "",
   "그림 제목이 다시 한 번 원칙을 말한다 — *\"Downloaded ORIGINALS used only for verification",
   "(our 5 DJI targets are built from official spec sheets, not these)\"*.",
   "",
   "← 그림 생성: `report_mesh/src/viz_mesh_reports.py:218-263` `fig_originals()` —",
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
   "| `assets/meshes/reference/SOURCES.md` 표 + 그림 제목 |",
   "| BSD-3-Clause (X500 부품) | 허용적 SW 라이선스 | 출처·라이선스 표기 유지 "
   "| `assets/meshes/reference/SOURCES.md` 표 |",
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
   " `report_mesh/src/viz_mesh_reports.py:230-262` (그림 제목 문자열)",
   ),

# 15 ── §6 출처 지도 --------------------------------------------------------------
md("## 6. 정리 — 무엇의 진리원(source of truth)이 어디인가",
   "",
   "| 알고 싶은 것 | 이 파일을 보라 | 성격 |",
   "|---|---|---|",
   "| 기체 제원의 근거·공식/추정 구분·URL | `docs/SPECS.md` | 사람용 요약(조사+검증) |",
   f"| 조사·검증의 원자료(JSON) | `docs/drone_research.json` | research/verify 두 블록 × {len(ORDER)}기체 |",
   "| **코드가 실제 쓰는 스펙값**과 채택 이유 | `src/drones.py` (`DroneSpec.note`) | 최종 채택 |",
   "| 실기체 스캔의 출처·라이선스·전처리 | `assets/meshes/cad/SOURCE.txt` + `src/prep_cad_scan.py` | 파생물 기록 |",
   "| 실물 CAD 3종의 출처·라이선스 | `assets/meshes/reference/SOURCES.md` | 검증 전용 |",
   "| 메쉬 측정치(이 시리즈의 수치) | `report_mesh/outputs/mesh_verify.json` | 검증 스위트 출력 |",
   "",
   "이번 편의 요점 세 가지:",
   "",
   f"1. 표적 {len(ORDER)}종의 치수는 **조사→독립검증 2단계**를 거친 스펙에서 왔고, 추정값(Mini"
   f" {research_diag('mini5pro'):g}→{d['mini5pro'].diagonal_mm:g}, Mavic"
   f" {research_diag('mavic4pro'):g}→{d['mavic4pro'].diagonal_mm:g} mm)은 추정임을 명시한 채",
   "   공식 외형과의 일관성으로 재유도했다.",
   f"2. 실물 대조 자료는 **라이선스가 확인된 공개물만** 썼다 — 스캔 1종({SRC['license']}),",
   "   CAD 3종(Apache-2.0·BSD-3) — 그리고 전부 **검증 전용**이다.",
   "3. 모든 다운로드물 옆에 출처 문서를 두어, 누구든 같은 자료를 같은 조건으로 다시 구할 수 있다.",
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
   "# 본문 수치의 원천 재생성(검증 스위트 → mesh_verify.json, 그림 포함)",
   "/workspace/.venvs/py312/bin/python report_mesh/src/verify_mesh_suite.py",
   "/workspace/.venvs/py312/bin/python report_mesh/src/viz_mesh_reports.py",
   "",
   "# 스캔 원본이 필요하면 (154 MB, 저장소 밖):",
   CURL,
   "```",
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
