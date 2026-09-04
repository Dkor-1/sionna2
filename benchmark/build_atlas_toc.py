# -*- coding: utf-8 -*-
"""
build_atlas_toc.py — 마이크로도플러 아틀라스의 **목차 노트북**을 굽는다.

무엇을 만드나
------------
`benchmark/build_md_atlas.py` 가 원장 `outputs/elevation_sweep_md.{json,npz}` 의 팔과 칸을
그림으로 구웠고, 산출 목록을 `outputs/md_atlas_index.json` 에 남겼다.
⛔**개수를 여기 적지 않는다**(2026-09-04) — 전 판의 «팔 54 · 칸 220 · 그림 122» 는 색인이
다시 구워지면서 낡아 갔다(지금 `_meta` 는 팔 445 · 칸 1433 · 그림 961 이다). 세는 것은
`_meta` 다.
이 파일은 그 색인을 읽어 **사람이 찾아보는 문서** `reports/A_atlas.ipynb` 를 만든다.

  ① 머리        — 이 문서가 무엇이고, 그림 두 종류(맵 · 대역 에너지)를 어떻게 읽나
  ② 주제별 절   — 주제마다 그림 · 그 주제가 답하는 질문 한 줄 · 요약 수치 표
  ③ 이름 읽는 법 — 팔 이름의 토큰(`_phys` · `_swR#D#E#F#` · `_parts…` …)이 각각 무슨 뜻인가
  ④ 읽을 때 주의 — 잣대가 퇴화하는 자리 · 절대 세기 비교 금지 · 격자 흔들림 밴드
  ⑤ 누락 검사    — 원장 220 칸 중 그림이 없는 칸

⭐**이름은 `A_` 로 시작한다** — `src/build_volumes.py` 는 `reports/_parts/` 를 `^\\d{2}_.*\\.ipynb$`
  로만 훑기 때문이다. ⛔전 판은 여기에 «어느 색인에도 안 걸린다» 고 적었는데 **지금은 틀리다** —
  2026-09-03 에 `VOLUMES` 에 **A 권**으로 등록돼 README·지도·목차가 모두 싣는다(2026-09-04 정정).

⛔GPU 를 안 쓴다 — `sionna.rt` · `mitsuba` 를 부르지 않고 저장된 원장·색인만 읽는다.
  `src/drones.py` 는 순수 파이썬(geom → numpy)이라 안전하고, 기체별 박자를 **다시 계산해
  색인 값과 대조**하는 자기검사에만 쓴다.

돌리는 법
--------
    PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/build_atlas_toc.py
"""
from __future__ import annotations

import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

IDX_P = os.path.join(ROOT, "outputs", "md_atlas_index.json")
LED_J = os.path.join(ROOT, "outputs", "elevation_sweep_md.json")
LED_N = os.path.join(ROOT, "outputs", "elevation_sweep_md.npz")
GRID_P = os.path.join(ROOT, "outputs", "grid_convergence_check.json")
OUT = os.path.join(ROOT, "reports", "A_atlas.ipynb")

MINUS = "−"          # U+2212 — 각도의 음수 부호(하이픈 아님)
DEG = "°"
C_LIGHT = 2.998e8

IDX = json.load(open(IDX_P, encoding="utf-8"))
LED = json.load(open(LED_J, encoding="utf-8"))
GRID = json.load(open(GRID_P, encoding="utf-8"))
META = IDX["_meta"]
ROWS = {(r["engine"], float(r["el_deg"])): r for r in LED["rows"]}

#: ⭐**설계 격자** — 「그 팔에 없는 앙각」을 셀 때의 기준. 원장 _meta 가 정본이다.
#  ⛔전에는 이 목록을 손으로 박아 뒀다. 원장이 앙각을 더 받아도 안 따라오므로,
#    조각 78 에서 잡은 병(설계 점과 나중에 붙은 탐침 각이 표에서 섞임)이 여기서도 난다.
DESIGN_ELS = [float(e) for e in LED["_meta"]["elevations_deg"]]
#: ⚠원장이 **실제로** 담은 앙각의 합집합 — 설계 격자보다 넓다(뒤에 붙은 탐침 각).
#  «몇 점을 쟀나» 를 말할 때는 이쪽을, «무엇이 빠졌나» 를 말할 때는 설계 격자를 쓴다.
PRESENT_ELS = sorted({float(r["el_deg"]) for r in LED["rows"]}, reverse=True)
#: 결측 계산의 기준은 설계 격자다 — 탐침 각을 «빠졌다» 고 세면 안 된다.
FULL_ELS = DESIGN_ELS


# ═══════════════════════════════════════════════════════════════════════════ #
#  글쓰기 도구
# ═══════════════════════════════════════════════════════════════════════════ #
def deg_txt(el: float) -> str:
    """«0°» · «−30°» — 음수는 U+2212."""
    if abs(el) < 1e-9:
        return "0" + DEG
    return ("+" if el > 0 else MINUS) + f"{abs(el):.0f}" + DEG


def num(x, fmt="{:.1f}", dash="—"):
    """⭐음수 부호는 U+2212 로 — 각도와 같은 활자를 쓴다(하이픈과 섞이면 눈에 튄다)."""
    return dash if x is None else fmt.format(x).replace("-", MINUS)


def thousands(n) -> str:
    return f"{int(n):,}"


def si_rays(spp) -> str:
    """광선 수를 읽기 쉬운 말로 — 4,000,000,000 → «40 억» · 11,111,111 → «1,111 만»."""
    if spp is None:
        return "—"
    n = int(spp)
    if n >= 100_000_000:
        v = n / 100_000_000
        return (f"{v:,.0f} 억" if v >= 10 else f"{v:g} 억")
    if n >= 10_000:
        v = n / 10_000
        return (f"{v:,.0f} 만" if v >= 10 else f"{v:g} 만")
    return thousands(n)


# ═══════════════════════════════════════════════════════════════════════════ #
#  팔 이름 토막 풀이 — ⭐이름만 보고 무엇인지 알게 하는 것이 이 문서의 절반이다
# ═══════════════════════════════════════════════════════════════════════════ #
SW_BIT = {"R": "굴절", "D": "회절", "E": "모서리 회절", "F": "확산 반사"}
ONLY_KO = {"refr": "굴절만", "diffr": "회절만", "edge": "모서리 회절만",
           "depth3": "깊이 3 만"}


def sw_ko(bits: str) -> str:
    """swR1D0E0F1 → «굴절 + 확산 반사» (꺼진 것은 안 적는다).

    ⚠2026-08-15 정정 — 넷을 다 끈 조합을 «전부 끔» 이라고 적으면 **틀린다.**
      생성기(`benchmark/elevation_sweep_md.py`)가 `los=True, specular_reflection=True` 를
      하드코딩하므로 **정반사와 직선경로는 언제나 켜져 있다.** 이 네 비트는 그 위에 얹는
      굴절·회절·모서리·확산일 뿐이다."""
    on = [SW_BIT[bits[i]] for i in range(0, len(bits), 2) if bits[i + 1] == "1"]
    return " + ".join(on) if on else "넷 다 끔(정반사·LOS 는 켬)"


def arm_facts(arm: str) -> list[str]:
    """⭐한 팔이 «무엇을 바꾼 판인가» 를 원장 열 + 이름 토막에서 만든다.

    거리·자세·광선·깊이·물리·격자는 **원장 행**에서 읽는다(이름에 없는 팔이 많다 — 토큰이
    없으면 기본값이라, 이름만 믿으면 10 m 팔을 15 m 로 잘못 읽는다).
    스위치·부품·PTD·평면파처럼 원장 열이 없는 축만 이름에서 읽는다.
    """
    els = IDX_ARM[arm]["elevations_deg"]
    row = ROWS[(arm, els[0])]
    t = arm.split("_")
    f = []

    if arm.startswith("ours_free"):
        f.append("엔진 **우리 커널(SBR+PO), 동체 «면» 을 빼서 가림을 없앤 대조군**")
    elif arm.startswith("ours"):
        f.append("엔진 **우리 커널(SBR+PO)**, 동체 포함(가림 있음)")
    else:
        f.append("엔진 **Sionna RT PathSolver**")

    f.append(f"거리 {row['range_m']:g} m")
    f.append(f"자세 {thousands(row['n_poses'])} 개")
    if row.get("spp"):
        f.append(f"광선 {si_rays(row['spp'])} 발")
    if row.get("grid_div"):
        f.append(f"격자 λ/{int(row['grid_div'])}")
    if row.get("max_depth"):
        f.append(f"반사 깊이 {int(row['max_depth'])}")

    if "stockdef" in t:
        f.append("스위치: **PathSolver 순정 기본값**(굴절 켬 · 회절 끔 · 모서리 끔 · 확산 끔)")
    else:
        swt = [x for x in t if x.startswith("sw") and len(x) == 10]
        onl = [x for x in t if x.startswith("only")]
        if swt:
            f.append(f"스위치: `{swt[0][2:]}` = {sw_ko(swt[0][2:])}")
        elif onl:
            f.append(f"스위치: {ONLY_KO.get(onl[0][4:], onl[0][4:])} 켬")
        # ⚠2026-08-15 정정 — `physics` 는 **PathSolver 전용 축**이다. 우리 커널 팔의 행에도
        #   False 가 적혀 있어 그대로 옮기면 없는 축에서 갈리는 것처럼 보인다.
        elif not arm.startswith("ours"):
            if row.get("physics") is True:
                f.append("스위치: 물리 **전부 켬**(굴절 · 회절 · 모서리 회절)")
            elif row.get("physics") is False:
                f.append("스위치: 물리 끔")

    for x in t:
        if x.startswith("parts"):
            f.append("장면: **프로펠러만**" if x == "partsprop"
                     else ("장면: **프로펠러를 뺀 나머지**" if x == "partsnoprop"
                           else f"장면: `{x[5:]}`"))
    if "ptd" in t:
        f.append("모서리 회절(PTD 프린지) **켬**")
    if "pw" in t:
        f.append("조명: **평면파**(구면파 아님)")
    az = row.get("az_deg")
    if az is not None and abs(float(az)) > 1e-9:
        f.append(f"방위 {float(az):g}{DEG}")

    a = IDX_ARM[arm]
    f.append(f"표적 {a['airframe_label']}"
             + ("(**기체 태그**)" if a["airframe_tagged"] else "")
             + f", 박자 {a['f_flash_hz']:g} Hz")
    return f


TOKEN_TABLE = [
    # (토큰, 뜻, 없으면(기본값), 나온 팔 수 계산용 판정자)
    ("`ours`", "우리 커널(SBR+PO) — 동체를 넣어 **가림이 있는** 판",
     "—", lambda t, a: a.startswith("ours") and not a.startswith("ours_free")),
    ("`ours_free`", "우리 커널이되 **동체 «면» 만 빼서** 가림을 없앤 대조군 "
     "(꼭짓점 · bbox · 광선 격자는 그대로라 «동체가 막느냐» 하나만 갈린다)",
     "—", lambda t, a: a.startswith("ours_free")),
    ("`sionna`", "Sionna RT 의 `PathSolver` 팔", "—",
     lambda t, a: a.startswith("sionna")),
    ("`p<N>`", "광선 수(`--spp`). `p4000000000` = 40 억 발",
     "규칙값 (R/3)²×1M", lambda t, a: any(x.startswith("p") and x[1:].isdigit()
                                        for x in t)),
    ("`phys`", "PathSolver 물리를 **전부 켠다** — 굴절 · 회절 · 모서리 회절",
     "셋 다 끔", lambda t, a: "phys" in t),
    ("`swR#D#E#F#`", "스위치를 **비트로 직접** 준 판. `R` 굴절 · `D` 회절 · "
     "`E` 모서리 회절 · `F` 확산 반사, `1` 이 켬. 예 `swR1D0E0F1` = 굴절 + 확산 반사. "
     "⚠소스 실측으로 `E` 는 `D=1` 일 때만 뜻이 있다. "
     "⭐**이 네 비트에 정반사·직선경로(LOS)는 없다** — 생성기가 `los=True, "
     "specular_reflection=True` 를 하드코딩하므로 둘은 **모든 팔에서 항상 켜져 있다**. "
     "그러니 `swR0D0E0F0` 도 «전부 끔» 이 아니다",
     "—", lambda t, a: any(x.startswith("sw") and len(x) == 10 for x in t)),
    ("`stockdef`", "PathSolver 를 **순정 기본값 그대로** — 굴절 켬 · 회절 끔 · "
     "모서리 끔 · 깊이 3 · 확산 끔. 우리 «끔» 판과도 «켬» 판과도 다른 제3 의 조합",
     "—", lambda t, a: "stockdef" in t),
    ("`only<x>`", "스위치를 **하나만** 켠 판 — `onlyrefr` 굴절 · `onlydiffr` 회절 · "
     "`onlyedge` 모서리 회절 · `onlydepth3` 깊이 3. `phys` 는 넷을 한꺼번에 켜서 "
     "무엇이 무엇을 했는지 귀속이 안 된다",
     "—", lambda t, a: any(x.startswith("only") for x in t)),
    ("`d<N>`", "PathSolver 반사 깊이(`--max-depth`). 물리 스위치와 깊이를 **가르는** 축",
     "옛 규칙(물리 켜면 3, 아니면 1)",
     lambda t, a: any(x.startswith("d") and x[1:].isdigit() for x in t)),
    ("`parts<…>`", "장면에 넣을 부품 그룹. `partsprop` = 프로펠러만 · "
     "`partsnoprop` = 프로펠러를 뺀 나머지(0° 붕괴가 «기근이냐 익사냐»)",
     "기체 전체", lambda t, a: any(x.startswith("parts") for x in t)),
    ("기체 태그", "표적 기체를 바꾼 판 — `mini5pro` · `s1000plus`. "
     "⚠**박자와 날개끝 상한이 함께 바뀐다**",
     "원장 기본 `matrice4e`", lambda t, a: IDX_ARM[a]["airframe_tagged"]),
    ("`az<N>`", "방위각[°]. `az45` = 45° 옆에서 본 판", "원장 기본 0" + DEG,
     lambda t, a: any(x.startswith("az") for x in t)),
    ("`r<N>`", "구면 반경[m]. `r15` = 15 m · `r30` = 30 m",
     "옛 기본 10 m(원거리장 경계 안쪽)",
     lambda t, a: any(x.startswith("r") and x[1:].replace(".", "").isdigit()
                      for x in t)),
    ("`n<N>`", "슬로타임 자세 수. `n8192` = 8,192 자세(박자 FFT 분해능 = PRF/N)",
     "원장 기본 4,096",
     lambda t, a: any(x.startswith("n") and x[1:].isdigit() for x in t)),
    ("`div<N>`", "우리 커널 표면 격자 간격 λ/N. `div24` = λ/24 (PathSolver 에 없는 축)",
     "규약값 λ/12", lambda t, a: any(x.startswith("div") for x in t)),
    ("`ptd`", "우리 팔의 **모서리 회절(PTD 프린지)** 켬", "끔",
     lambda t, a: "ptd" in t),
    ("`pw`", "**평면파** 조명(구면파 대신 · 무한 거리 등가)", "구면파",
     lambda t, a: "pw" in t),
]


# ═══════════════════════════════════════════════════════════════════════════ #
#  주제마다 «무엇을 묻는 판인가»
# ═══════════════════════════════════════════════════════════════════════════ #
TOPIC_Q = {
    "01base": "엔진과 광선 예산만 바꾸면 날개 무늬가 달라지나 — 그리고 얼마나 부어야 "
              "달라지기를 멈추나.",
    "02switch": "굴절 · 회절 · 모서리 회절 · 확산 반사 중 **무엇을 켜면** 날개 리듬이 "
                "백색 수준으로 주저앉나.",
    "03airframe": "표적 기체를 바꾸면 그림의 박자가 **그 기체의 박자**로 따라가나 — "
                  "분류 축이 성립하나.",
    "04azimuth": "지금까지의 결론이 방위 한 자리(정면)에서만 서는 것인가 — "
                 "45" + DEG + " 옆에서도 같은 말을 하나.",
    "05parts": "무늬를 만드는 것은 프로펠러인가 동체인가 — 프로펠러만 남기면 무엇이 남나.",
    "06range": "15 m 에서 30 m 로 물러나면 날개 무늬가 남나.",
    "07ptd": "우리 팔의 모서리 회절(PTD 프린지)을 켜면 무늬가 달라지나.",
    "08grid": "표면 격자를 λ/12 에서 λ/24 로 조이면 잣대가 얼마나 움직이나 — "
              "**판정 문턱을 정하는 판**이다.",
    "09planewave": "직하방의 잔여가 근접장 **곡률** 탓인가 — 평면파로 바꾸면 사라지나.",
}

#: 비교판 파일 이름 → 그 판이 무엇인지
def compare_caption(path: str, topic_en: str) -> str:
    b = os.path.basename(path)
    if "000-overview-rhythm" in b:
        return ("이 주제의 팔 × 앙각 **리듬 몫[%]** 지도 — 개별 그림을 열기 전에 "
                "어디를 볼지 정하는 판이다. `—` 는 원장에 그 칸이 없다는 뜻이고, "
                "**빗금 친 칸은 색눈금에 올리면 안 되는 칸**이다: "
                f"{MINUS}90{DEG} 열(잣대 퇴화) · ◐ 자세가 덜 참 · ○ 안 움직임 · "
                "∅ 에코 없음. ⚠이 지도는 **상한 위**만 보는 잣대라 낮은 값이 "
                "«날개가 없다» 는 뜻이 아니다.")
    if "01-compare-tile" in b:
        el = b.split("01-compare-tile")[1].split("-p")[0]
        return (f"앙각이 **{deg_txt(float(el))} 하나뿐인** 팔들을 한 장에 타일로 — "
                f"전부 정지 성분을 뺀 판이라 «움직이는 것» 만 남았다.")
    if "02-compare-stack" in b:
        return ("팔을 세로로 쌓고 앙각을 가로로 편 판 — 같은 앙각 열을 위아래로 "
                "훑으면 팔 사이 차이가 보인다.")
    return "비교판."


# ═══════════════════════════════════════════════════════════════════════════ #
#  색인 펼치기
# ═══════════════════════════════════════════════════════════════════════════ #
IDX_ARM: dict[str, dict] = {}
ARM_TOPIC: dict[str, str] = {}
for _tk, _t in IDX["topics"].items():
    for _arm, _a in _t["arms"].items():
        IDX_ARM[_arm] = _a
        ARM_TOPIC[_arm] = _tk
TOPICS = sorted(IDX["topics"].items(), key=lambda kv: kv[1]["order"])

ALL_CELLS = [(arm, ek, c) for arm, a in IDX_ARM.items()
             for ek, c in a["cells"].items()]


def _null_range() -> str:
    """⭐«백색잡음이면 몇 %» 는 칸마다 다르다 — 기체(박자)마다 갈리므로 표로 적는다."""
    by: dict[str, list[float]] = {}
    for arm, _ek, c in ALL_CELLS:
        v = c.get("rhythm_null_pct")
        if v is not None:
            by.setdefault(IDX_ARM[arm]["airframe_label"], []).append(v)
    return " · ".join(f"{k} ≈ {sum(v)/len(v):.1f}" for k, v in sorted(by.items()))


def _low_high() -> dict:
    """리듬 몫이 낮은 칸 ↔ 높은 칸에서 «상한 위» 가 움직이는 에너지의 몇 %인가.

    ⭐이 문서가 «무늬가 상한 아래로 들어앉아 몫이 낮다» 고 적었던 것을 반증한 자리다 —
    실제로는 몫이 낮은 칸이 상한 **위**에 에너지가 더 많다(잡동사니가 차 있다)."""
    lo, hi = [], []
    for _arm, ek, c in ALL_CELLS:
        v, f = c.get("rhythm_share_pct"), c.get("above_ceiling_energy_pct")
        if v is None or f is None or abs(float(ek) + 90.0) < 1e-9:
            continue
        (lo if v < 20.0 else hi).append(f)
    med = lambda x: float(np.median(x)) if x else float("nan")     # noqa: E731
    return dict(low_n=len(lo), high_n=len(hi), low_med=med(lo), high_med=med(hi))


def _farfield() -> tuple[list[str], str]:
    """⭐기체마다의 원거리장 경계 2D²/λ — 표 줄과 «안쪽에 선 팔» 문장.

    ⚠규약을 원장과 맞춘다: D 는 **메쉬 3D 대각**이다(원장의 14.08 m 가 그 값이다).
      D 를 «최대 수평 크기» 로 잡으면 다른 수가 나오므로 섞어 쓰면 안 된다.
    ⛔GPU 를 안 쓴다 — `drones.build_drone` 은 순수 파이썬(geom → numpy)이다."""
    from drones import DRONES, build_drone
    lam = C_LIGHT / float(META["fc_hz"])
    rows, inside = [], []
    for key in sorted({a["airframe"] for a in IDX_ARM.values()}):
        b0, b1 = build_drone(DRONES[key]).bounds()
        D = float(np.linalg.norm(np.asarray(b1) - np.asarray(b0)))
        r_ff = 2.0 * D * D / lam
        arms = [x for x in IDX_ARM if IDX_ARM[x]["airframe"] == key]
        rs = sorted({float(ROWS[(x, IDX_ARM[x]["elevations_deg"][0])]["range_m"])
                     for x in arms
                     if ROWS[(x, IDX_ARM[x]["elevations_deg"][0])].get("range_m")
                     is not None})
        bad = [r for r in rs if r < r_ff]
        for r in bad:
            inside += [x for x in arms
                       if float(ROWS[(x, IDX_ARM[x]["elevations_deg"][0])]["range_m"]) == r]
        rows.append(
            f"| {DRONES[key].name} | {D:.2f} m | **{r_ff:.2f} m** | "
            + " · ".join(f"{r:g} m" for r in rs) + " | "
            + ("전부 밖(원거리장)" if not bad else
               "⚠" + " · ".join(f"{r:g} m 는 **안쪽**(근접장, 경계의 {r/r_ff:.2f} 배)"
                                for r in bad)) + " |")
    if inside:
        ko = (f"근접장에 선 팔이 **{len(inside)} 개**다 — "
              + " · ".join(f"`{x}`" for x in sorted(inside)[:8])
              + (" …" if len(inside) > 8 else "") + ".")
    else:
        ko = "이 원장에는 근접장에 선 팔이 없다."
    return rows, ko


NULL_RANGE = _null_range()
LOWHI = _low_high()
FF_ROWS, FF_INSIDE_KO = _farfield()
#: ⭐수를 낼 자격이 없는 칸 — 색인이 깃발로 적어 둔다(값은 전부 None 이다)
INCOMPLETE = [(a, e, c) for a, e, c in ALL_CELLS if c.get("incomplete")]
NO_MOTION = [(a, e, c) for a, e, c in ALL_CELLS if c.get("no_motion")]
SPIKY = [(a, e, c) for a, e, c in ALL_CELLS if c.get("beat_spiky")]
#: ⭐튐 진단(2026-08-16 부터 상시) — «자세 **하나**가 헤드라인을 끄나». 위 SPIKY 는 «크기» 만
#  잰 옛 깃발이고, 아래 둘은 «혼자인가 · 갈아 끼우면 헤드라인이 움직이나» 를 잰 깃발이다.
MOVES = [(a, e, c) for a, e, c in ALL_CELLS if c.get("one_pose_moves_headline")]
UNDERS = [(a, e, c) for a, e, c in ALL_CELLS if c.get("flash_comb_undersampled")]
SHAKY = [(a, e, c) for a, e, c in ALL_CELLS if c.get("outlier_grade_shaky")]
OUT_META = META.get("outlier") or {}


# ═══════════════════════════════════════════════════════════════════════════ #
#  ⑤ 누락 검사 — ⭐색인을 믿지 않고 **원장 npz 키에서 다시 센다**
# ═══════════════════════════════════════════════════════════════════════════ #
def audit() -> dict:
    Z = np.load(LED_N, allow_pickle=True)
    led: dict[str, set] = {}
    for k in Z.files:
        if "/" not in k:
            continue
        arm, tag = k.rsplit("/", 1)
        if tag.startswith("el"):
            led.setdefault(arm, set()).add(float(tag[2:]))

    no_fig, no_file = [], []
    for arm, els in sorted(led.items()):
        got = {float(x) for x in IDX_ARM.get(arm, {}).get("cells", {})}
        for e in sorted(els - got, reverse=True):
            no_fig.append((arm, e))
    for arm, a in IDX_ARM.items():
        for kind, p in a["figures"].items():
            if not os.path.exists(os.path.join(ROOT, p)):
                no_file.append(p)
    for tk, t in IDX["topics"].items():
        for p in t["compare"]:
            if not os.path.exists(os.path.join(ROOT, p)):
                no_file.append(p)

    empty = [(arm, e, c) for arm, a in IDX_ARM.items()
             for e, c in a["cells"].items() if c.get("no_return")]
    absent = {arm: [e for e in FULL_ELS if e not in led[arm]]
              for arm in led if len(led[arm]) < len(FULL_ELS)}

    # ⭐«파일이 있나» 만 세면 잡히지 않는 결측 — 원장 n_missing 이 그 용도로 있는 열이다.
    #   샤드가 원장보다 새로우면 n_missing 이 0 인 채로 남으므로 **디스크도** 본다.
    shard_dir = os.path.join(ROOT, "outputs", "elev_sweep_shards")
    led_mt = max(os.path.getmtime(LED_J), os.path.getmtime(LED_N))
    newer = []
    if os.path.isdir(shard_dir):
        newer = sorted(f for f in os.listdir(shard_dir)
                       if f.endswith(".npz")
                       and os.path.getmtime(os.path.join(shard_dir, f)) > led_mt + 1.0)

    return dict(
        incomplete=[(a, e, c) for a, e, c in INCOMPLETE],
        no_motion=[(a, e, c) for a, e, c in NO_MOTION],
        shards_newer_than_ledger=newer,
        n_ledger_cells=sum(len(v) for v in led.values()),
        n_ledger_arms=len(led),
        n_rows=len(LED["rows"]),
        no_fig=no_fig, no_file=sorted(set(no_file)),
        empty=sorted(empty), absent=absent,
        n_absent=sum(len(v) for v in absent.values()),
        arms_in_ledger_not_index=sorted(set(led) - set(IDX_ARM)),
        arms_in_index_not_ledger=sorted(set(IDX_ARM) - set(led)),
    )


def self_checks(A: dict) -> list[tuple[str, bool, str]]:
    """⭐자기검사 — ⚠**항진명제를 검사라고 부르지 않는다.**

    2026-08-15 정정: 옛 판의 첫 검사는 «기체별 박자를 `src/drones.py` 에서 다시 계산해
    색인과 대조» 라고 광고했지만, 색인을 만든 쪽(`build_md_atlas.arm_rates`)이 **같은 식·
    같은 입력**을 쓰므로 언제나 통과했다(airframe → f_flash 는 일대일 사상이다).
    그래서 «다시 계산» 은 그대로 두되, 진짜 **독립 증거**인 원장의 측정값
    (`track.beat_hz` — 스윕이 스스로 잰 박자)과의 대조를 함께 낸다.
    """
    from drones import DRONES
    fc = float(META["fc_hz"])
    out = []

    bad = []
    for arm, a in IDX_ARM.items():
        s = DRONES[a["airframe"]]
        f_rev = float(s.hover_rpm) / 60.0
        want = int(s.prop_blades) * f_rev
        tip0 = 2.0 * (2 * math.pi * f_rev * (s.prop_dia_mm / 2000.0)) / (C_LIGHT / fc)
        if abs(want - a["f_flash_hz"]) > 0.01 or abs(tip0 - a["f_tip0_hz"]) > 0.2:
            bad.append(arm)
    out.append(("기체별 박자·날개끝 상한을 `src/drones.py` 에서 다시 계산해 색인과 대조 "
                "⚠(같은 식·같은 입력이라 **항진명제**다 — 아래 원장 대조가 진짜 검사다)",
                not bad, f"팔 {len(IDX_ARM)} 개 전부 일치"
                if not bad else f"어긋난 팔 {len(bad)}: {bad[:3]}"))

    #: ⭐진짜 독립 검증 — 원장이 **스윕 도중에 직접 잰** 박자와 우리 예측을 댄다.
    hit = miss = 0
    worst = None
    for arm, a in IDX_ARM.items():
        for ek, c in a["cells"].items():
            m = c.get("ledger_beat_hz")
            if m is None or c.get("no_return") or c.get("incomplete") \
                    or c.get("no_motion") or abs(float(ek) + 90.0) < 1e-9:
                continue
            rel = float(m) / float(a["f_flash_hz"])
            if abs(rel - round(rel)) <= 0.03 and round(rel) >= 1:
                hit += 1
            else:
                miss += 1
                if worst is None or abs(rel - round(rel)) > worst[1]:
                    worst = (f"{arm}@{ek} {m:g} Hz = {rel:.2f}x", abs(rel - round(rel)))
    out.append(("⭐원장이 **스스로 잰** 박자(`track.beat_hz`)가 우리가 세운 예측 박자의 "
                "정수배 ±3 % 안에 든다 — 색인과 무관한 독립 증거",
                miss * 4 <= hit,
                f"맞음 {hit} 칸 · 어긋남 {miss} 칸"
                + (f" (가장 먼 칸 {worst[0]})" if worst else "")))

    tagged = sorted({a["airframe"] for a in IDX_ARM.values() if a["airframe_tagged"]})
    ff = {k: IDX_ARM[[x for x in IDX_ARM if IDX_ARM[x]["airframe"] == k][0]]["f_flash_hz"]
          for k in tagged}
    out.append(("기체 태그 팔의 박자가 원장 기본값과 **다르다**(그대로 썼으면 틀렸을 자리)",
                all(abs(v - LED["_meta"]["f_flash_hz"]) > 1.0 for v in ff.values()),
                " · ".join(f"{k} {v:g} Hz" for k, v in ff.items())
                + f" ↔ 원장 기본 {LED['_meta']['f_flash_hz']:.2f} Hz"))

    #: ⭐이번 수리의 핵심 — 자격 없는 칸에 수가 실리면 안 된다
    leak = [f"{a}@{e}" for a, e, c in ALL_CELLS
            if (c.get("incomplete") or c.get("no_motion") or c.get("no_return"))
            and any(c.get(k) is not None for k in
                    ("rhythm_share_pct", "beat_hz", "comb_contrast_db",
                     "moving_power_db"))]
    out.append(("⭐수를 낼 자격이 없는 칸(덜 참 · 안 움직임 · 에코 없음)에 **잣대가 하나도 "
                "안 실렸다**", not leak,
                f"덜 참 {len(A['incomplete'])} · 안 움직임 {len(A['no_motion'])} · "
                f"에코 없음 {len(A['empty'])} 칸, 새어 나온 수 {len(leak)} 개"))

    out.append(("원장 병합이 최신이다 — 샤드 파일 가운데 원장보다 새 것이 없다",
                not A["shards_newer_than_ledger"],
                "전부 원장보다 오래됨" if not A["shards_newer_than_ledger"]
                else f"⚠원장보다 새 샤드 {len(A['shards_newer_than_ledger'])} 개 — "
                     f"병합이 낡았다(예: `{A['shards_newer_than_ledger'][0]}`)"))

    out.append(("원장 칸 수와 색인 칸 수가 같다",
                A["n_ledger_cells"] == META["n_cells"] == A["n_rows"],
                f"원장 npz {A['n_ledger_cells']} · 원장 rows {A['n_rows']} · "
                f"색인 {META['n_cells']}"))
    out.append(("색인이 가리키는 그림 파일이 전부 디스크에 있다",
                not A["no_file"], f"그림 {META['n_figures']} 장 · 빠진 파일 "
                f"{len(A['no_file'])} 개"))
    out.append(("원장에 있는데 그림 열이 없는 칸이 없다",
                not A["no_fig"], f"빠진 칸 {len(A['no_fig'])} 개"))
    return out


# ═══════════════════════════════════════════════════════════════════════════ #
#  노트북 조립
# ═══════════════════════════════════════════════════════════════════════════ #
class NB:
    def __init__(self):
        self.cells = []
        self.fig = 0

    def md(self, *lines):
        txt = "\n".join(lines)
        self.cells.append({"cell_type": "markdown", "metadata": {},
                           "source": [l + "\n" for l in txt.split("\n")]})

    def figure(self, path: str, alt: str, caption: str):
        """⭐그림은 **하나에 캡션 하나**. 번호는 문서 전체에서 이어진다."""
        self.fig += 1
        self.md(f"![{alt}](../{path})", "",
                f"**그림 {self.fig}.** {caption}")


def rhythm_cell(c) -> str:
    """리듬 몫 한 칸의 표기 — ∅ 에코 없음 · ◐ 덜 참 · ○ 안 움직임 · * 잣대 퇴화.

    ⭐«덜 참»·«안 움직임» 칸에 수를 안 적는 것이 핵심이다 — 그 칸의 0 % 는 물리가 아니다."""
    if c is None:
        return "—"
    if c.get("no_return"):
        return "∅"
    if c.get("incomplete"):
        return "◐"
    if c.get("no_motion"):
        return "○"
    v = c.get("rhythm_share_pct")
    if v is None:
        return "n/a"
    return f"{v:.0f}" + ("\\*" if c.get("tip_ceiling_degenerate") else "")


def topic_table(t) -> list[str]:
    """주제 하나의 요약 수치 표 — 팔 × 앙각의 리듬 몫[%] 에 설정 열을 앞에 붙인다."""
    arms = sorted(t["arms"])
    els = sorted({float(k) for a in t["arms"].values() for k in a["cells"]},
                 reverse=True)
    head = "| 팔 | 표적 · 박자 | 거리 | " + " | ".join(deg_txt(e) for e in els) + " |"
    rule = "|---|---|---|" + "---|" * len(els)
    out = [head, rule]
    for arm in arms:
        a = t["arms"][arm]
        row = ROWS[(arm, a["elevations_deg"][0])]
        cells = " | ".join(rhythm_cell(a["cells"].get(f"{e:+.0f}")) for e in els)
        out.append(f"| `{arm}` | {a['airframe_label']} · {a['f_flash_hz']:g} Hz "
                   f"| {row['range_m']:g} m | {cells} |")
    return out


def arm_table(arm: str) -> list[str]:
    """팔 하나의 앙각별 수치. ⭐«리듬 몫» 옆에 그 칸의 **널**과 **짝 잣대**를 붙인다 —
    두 수를 나란히 두지 않으면 낮은 몫이 «날개 없음» 으로 읽힌다."""
    a = IDX_ARM[arm]
    out = ["| 앙각 | 날개끝 상한 f_tip | 리듬 몫 [%] | (그 칸 백색잡음) "
           "| 상한 위 에너지 [%] | 빗살 대비 [dB] | 박자 [Hz] | 박자 ÷ 예측 "
           "| 움직이는 전력 [dB] | 움직이는 몫 [%] |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for e in a["elevations_deg"]:
        c = a["cells"][f"{e:+.0f}"]
        why = ("∅ 에코 없음" if c.get("no_return") else
               f"◐ 덜 참({thousands(c['n_poses'] - max(c.get('n_missing') or 0, c.get('n_zero_samples') or 0))}"
               f"/{thousands(c['n_poses'])} 자세)" if c.get("incomplete") else
               "○ 안 움직임" if c.get("no_motion") else None)
        if why:
            out.append(f"| {deg_txt(e)} | {c['f_tip_hz']:.0f} Hz | {why} "
                       + "| — " * 7 + "|")
            continue
        star = "\\*" if c["tip_ceiling_degenerate"] else ""
        out.append(
            f"| {deg_txt(e)}{star} | {c['f_tip_hz']:.0f} Hz "
            f"| {num(c['rhythm_share_pct'], '{:.1f}')} "
            f"| {num(c.get('rhythm_null_pct'), '{:.1f}')} "
            f"| {num(c.get('above_ceiling_energy_pct'), '{:.1f}')} "
            f"| {num(c.get('comb_contrast_db'), '{:+.1f}')} "
            f"| {num(c['beat_hz'], '{:.1f}')}"
            + (" ⚠튐" if c.get("beat_spiky") else "")
            + f" | {num(c['beat_over_flash'], '{:.2f}')} "
            f"| {num(c['moving_power_db'], '{:.2f}')} "
            f"| {num(c['moving_share_pct'], '{:.3f}')} |")
    return out


def build() -> NB:
    A = audit()
    nb = NB()
    #: 절 번호 — 1 읽는 법 · 2 주제 목차 · 3…N 주제 · 그다음 이름 · 주의 · 누락.
    #  ⚠본문 여러 곳이 서로를 가리키므로 **여기서 한 번만** 정한다.
    S_TOPIC0 = 3
    n_last_topic = S_TOPIC0 + len(TOPICS) - 1
    n_tok, n_warn, n_aud = n_last_topic + 1, n_last_topic + 2, n_last_topic + 3
    band = GRID["grid_dispersion_bands"]["bands"]["layer3_metric"]
    rhy_band = [b for b in band if b["metric"] == "rhythm_share_pp"][0]["band"]
    ac_band = [b for b in GRID["grid_dispersion_bands"]["bands"]["layer2_statistics"]
               if b["metric"] == "ac_power_db"][0]["band"]
    white = [c for c in GRID["self_checks"] if "백색" in c["check"]][0]["detail"]

    # ── ① 머리 ────────────────────────────────────────────────────────────
    nb.md(
        "# 부록 A — 마이크로도플러 아틀라스 · 목차",
        "",
        f"> 앙각 스윕 원장에는 **팔 {META['n_arms']} 개 · 칸 {META['n_cells']} 개**가 "
        f"들어 있는데, 지금까지 그림으로 나온 것은 덱이 고른 몇 팔뿐이었다. "
        f"`benchmark/build_md_atlas.py` 가 그 전부를 **그림 {META['n_figures']} 장**으로 "
        f"구웠고, 이 문서는 그것을 주제별로 세워 놓은 **목차**다. "
        f"여기서 그림을 고르고, 팔 이름을 읽는 법을 익히고, 어디를 믿으면 안 되는지 확인한다.",
        "",
        "이 부록은 **A 권**으로 편성에 걸려 있다(2026-09-03 등록) — 결론을 주장하는 "
        "문서가 아니라 원장을 찾아보는 문서라 파일 이름이 `A_` 로 시작하지만, 지금은 "
        "`README.md` 목차 · `reports/README.md` · `reports/01_map.ipynb` 가 모두 싣는다. "
        "전체 목차는 [reports/README.md](README.md) 다.",
        "",
        "| 무엇 | 어디 |",
        "|---|---|",
        f"| 원장 | `{META['ledger']}` · `outputs/elevation_sweep_md.npz` |",
        f"| 그림 | `{META['figdir']}/` — {META['n_figures']} 장 |",
        f"| 색인(기계용) | `outputs/md_atlas_index.json` — 이 문서의 모든 수가 여기서 온다 |",
        f"| 구운 때 | {META['built_at']} |",
        f"| 잰 자리 | 반송파 {float(META['fc_hz'])/1e9:g} GHz · "
        f"PRF {thousands(META['prf_hz'])} Hz · 기본 표적 `{META['drone_default']}` |",
        "",
        "```bash",
        "PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/build_md_atlas.py",
        "PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/build_atlas_toc.py"
        "   # 이 문서",
        "```",
    )

    nb.md(
        "---",
        "",
        "## 절 1. 이 문서를 읽는 법",
        "",
        "### 그림은 두 종류다",
        "",
        "팔 하나에 그림이 **두 장** 붙는다. 한 장은 «무늬가 어떻게 생겼나», "
        "다른 한 장은 «그 무늬가 규칙적인가» 를 본다. 주제마다 그 위에 **비교판**이 "
        "한두 장 더 얹힌다 — 여러 팔을 한 장에 모아 어디를 열어 볼지 정하는 판이다.",
        "",
        "**(가) 맵** — 파일 이름이 `…__map.png` 로 끝난다.",
        "",
        "- 가로가 **시간**(20 ms 부터 60 ms 창), 세로가 **도플러**(움직이는 것이 주파수를 "
        "얼마나 밀었나)다.",
        "- 규칙적으로 지나가는 밝은 덩어리가 **날개**다. 날개가 시선을 스칠 때마다 한 번씩 "
        "번쩍하고, 그 번쩍이 일정한 간격으로 늘어서면 «회전하는 것이 달려 있다» 는 뜻이다.",
        "- 흰 점선은 **날개끝 상한**(f_tip) — 날개 끝이 낼 수 있는 가장 빠른 도플러다. "
        "물리적으로 그 선 위에는 날개가 만든 것이 있을 수 없다.",
        "- 위 줄은 **받은 그대로**, 아래 줄은 **정지 성분(시계열 평균)을 뺀** 판이다. "
        "위 줄 한가운데 가로로 진하게 눕는 띠가 동체 · 붙박이 반사이고, 아래 줄은 그것을 "
        "빼고 «움직이는 것만» 남긴 판이다. ⭐세기를 말하는 수는 전부 아래 줄에서 잰다.",
        "- 구석의 작은 수는 **«날개 박자에 붙은 에너지 몫[%]»** 이다 — 날개끝 상한 **위**에 "
        "남은 에너지 가운데 예측 박자의 정수배 자리(±8 Hz)에 앉은 몫. "
        f"백색잡음이면 얼마가 나오는지는 **칸마다 다르다**({NULL_RANGE}) — 그림·표가 그 칸의 "
        "널을 함께 적으니 «13» 하나를 모든 팔에 대지 마라.",
        "- ⚠**천장 100 은 실제 자료에서 도달 불가다.** 실제 로터는 rpm 이 조금씩 흩어져 선이 "
        "번지고 창 반폭이 8 Hz 로 고정이라 높은 배음일수록 창 밖으로 샌다. "
        f"눈금 실측(`grid_convergence_check.json`)의 «{white}» 에서 100 % 를 낸 «이상 로터» 는 "
        "**rpm 산포가 0 인 합성 신호**다 — 실물이 아니다. 그러니 100 을 «완벽한 로터» 로 "
        "읽지 말고, 눈금의 위쪽 끝이라고만 읽는다.",
        "- ⭐⚠**그 몫이 낮다고 «날개가 안 보인다» 는 뜻이 아니다.** 이 수는 상한 **위**에 "
        "남은 것만 본다. 그런데 몫이 낮은 칸은 대개 «위가 조용해서» 가 아니라 **«위가 "
        "잡동사니로 가득 차서»** 낮다 — 이 원장에서 직접 재 보면 그렇다: 리듬 몫이 20 % "
        f"미만인 칸 {LOWHI['low_n']} 개는 움직이는 에너지의 **중앙값 {LOWHI['low_med']:.0f} %**"
        f"가 상한 위에 있고, 20 % 이상인 칸 {LOWHI['high_n']} 개는 **{LOWHI['high_med']:.0f} %** "
        "뿐이다(−90° 제외). 즉 «무늬가 상한 아래로 얌전히 들어앉아서 몫이 낮다» 는 설명은 "
        "**거꾸로**다(2026-08-15 정정 — 그전 판에 그렇게 적혀 있었다).",
        "- 그래서 구석에는 **짝 잣대**를 함께 적는다 — «in-band comb [dB]» 는 상한 "
        "**아래**(2·박자 ~ 상한)에서 «정수배 자리 ÷ 그 사이 자리» 전력비다. 백색잡음 ≈ 0 dB. "
        "리듬 몫이 0 인데 이 수가 +40 dB 면 «날개가 없다» 가 아니라 **«이 잣대가 못 읽는 "
        "자리다»** 라는 뜻이다. 날개가 보이나는 결국 **맵 자체**와 이 수로 판단한다.",
        "- ⚠**패널마다 자기 최댓값을 기준으로 색을 칠한다.** 색이 진하다고 세기가 센 것이 "
        "아니다 — 이 그림은 **모양을 읽는 그림**이지 세기를 읽는 그림이 아니다.",
        "",
        "**(나) 대역 에너지** — 파일 이름이 `…__band.png` 로 끝난다.",
        "",
        "- 날개끝 상한의 0.35~1.0 배 띠(«날개 대역»)의 전력이 시간에 따라 어떻게 뛰는지, "
        "그 **리듬의 스펙트럼**이다. 맵의 줄무늬가 정말 규칙적으로 뛰는가를 직접 묻는 판이다.",
        "- 가로는 **초당 몇 번 뛰나**(변조율 [Hz]), 세로는 그 선의 세기다. "
        "왼쪽이 넓은 범위(100~1,000 Hz), 오른쪽이 첫 선들의 확대다.",
        "- 세로 점선이 **예측 박자의 정수배**다 — 날개 수 × 호버 rpm ÷ 60. 곡선의 봉우리가 "
        "그 점선에 올라앉으면 «예측한 그대로 돈다», 점선을 비껴 서면 «다른 것이 뛰고 있다», "
        "봉우리 없이 잔디밭이면 «리듬이 없다» 이다.",
        "- 곡선 하나가 앙각 하나다. ⚠여기서도 **곡선마다 자기 최댓값**으로 눕혔다 — "
        "곡선 사이 높이 비교는 뜻이 없다.",
        "",
        "### 표의 표기",
        "",
        "| 표기 | 뜻 |",
        "|---|---|",
        "| `—` | 원장에 그 칸이 없다(안 돌린 자리) |",
        "| `∅` | 돌리기는 했는데 **아무것도 안 돌아왔다**(에코가 통째로 0) |",
        f"| `◐` | ⭐**자세가 덜 찼다** — 병합이 아직 절반이라 잣대를 내지 않는다"
        f" (절 {n_aud}.1b) |",
        f"| `○` | **움직이는 것이 없다** — AC/DC 가 반올림 바닥 아래라 잣대를 내지 않는다"
        f" (절 {n_aud}.1c) |",
        f"| `*` | 앙각 {MINUS}90{DEG} — 날개끝 상한이 0 이라 «상한 위» 잣대가 **퇴화**한다"
        f" (절 {n_warn}.1 을 보라) |",
        "| `⚠튐` | 자세 몇 개가 통째로 튀어 그 «박자» 가 회전이 아니다"
        f" (절 {n_warn}.8) |",
        "",
        f"팔 이름이 낯설면 **절 {n_tok} «팔 이름 읽는 법»** 을 먼저 봐도 된다 — "
        "`_phys` · `_swR1D0E0F1` · `_partsprop` 같은 토막이 각각 무슨 뜻인지 표로 있다. "
        f"어디를 믿으면 안 되는지는 **절 {n_warn}** 에 모아 뒀다.",
        "",
        "### 집 규칙",
        "",
        "- 마이크로도플러 표현은 **STFT 만** 쓴다(재할당 · WVD 같은 다른 표현은 안 쓴다) — "
        f"`src/md_mapstyle.py` 의 `flash_spec`: 블레이드 주기의 "
        f"{sorted({a['stft_periods'] for a in IDX_ARM.values()})[0]:g} 배 조각 · hop 2 "
        f"· 8× 제로패딩.",
        f"- {META['level_rule_ko']}",
        f"- {META['map_window_ko']} 패널마다 자기 최댓값으로 정규화한다.",
        "- 그림 안 글자는 영어, 본문은 한국어다. 각도는 «"
        + MINUS + "30" + DEG + "» 로 적는다.",
    )

    # ── 목차 표 ──────────────────────────────────────────────────────────
    lines = ["---", "", "## 절 2. 주제 아홉 가지", "",
             "원장의 팔은 **이름 규칙**으로 아홉 주제에 갈린다 — 하드코딩한 목록이 아니라 "
             "이름에서 유도하므로, 새 팔이 생기면 자동으로 제자리에 붙는다.", "",
             "| 절 | 주제 | 무엇을 묻나 | 팔 | 칸 | 그림 |", "|---|---|---|---|---|---|"]
    for i, (tk, t) in enumerate(TOPICS, start=S_TOPIC0):
        ncell = sum(len(a["cells"]) for a in t["arms"].values())
        nfig = 2 * len(t["arms"]) + len(t["compare"])
        q = TOPIC_Q[tk].split(" — ")[0].rstrip(".")
        lines.append(f"| {i} | **{t['label_ko'].split(' — ')[0]}** "
                     f"(`{tk}`) | {q} | {len(t['arms'])} | {ncell} | {nfig} |")
    lines += ["", f"합계 — 팔 {META['n_arms']} · 칸 {META['n_cells']} · "
              f"그림 {META['n_figures']}."]
    nb.md(*lines)

    # ── ② 주제별 절 ───────────────────────────────────────────────────────
    #: ⭐주제마다 «어느 셀에서 시작하나» 를 적어 둔다 — main() 이 여기서 편을 가른다.
    #  ⛔셀 내용을 뒤져 «## 절» 을 찾는 방식은 안 쓴다. 제목 글자가 바뀌면 조용히 깨진다.
    nb.marks = []
    for i, (tk, t) in enumerate(TOPICS, start=S_TOPIC0):
        nb.marks.append((tk, t["label_ko"], i, len(nb.cells)))
        ncell = sum(len(a["cells"]) for a in t["arms"].values())
        nb.md(
            "---", "",
            f"## 절 {i}. {t['label_ko']}",
            "",
            f"> **묻는 것** — {TOPIC_Q[tk]}",
            "",
            f"팔 {len(t['arms'])} 개 · 칸 {ncell} 개 · 그림 "
            f"{2*len(t['arms']) + len(t['compare'])} 장. "
            f"그림 파일은 전부 `{META['figdir']}/{tk}__…` 로 시작한다.",
        )

        for p in t["compare"]:
            nb.figure(p, f"{t['label_en']} — {os.path.basename(p)}",
                      compare_caption(p, t["label_en"]))

        nb.md(
            f"### 절 {i}.1 요약 수치 — 팔 × 앙각의 리듬 몫 [%]", "",
            "날개끝 상한 **위**에 남은 에너지 가운데 예측 박자의 정수배에 앉은 몫이다. "
            f"⚠**상한 위만 재는 잣대**라 낮은 값이 «날개가 없다» 는 뜻이 아니다(절 {n_warn}.7 · "
            "팔마다의 표에 상한 **아래**를 보는 «빗살 대비[dB]» 를 함께 실었다). "
            f"백색잡음 값은 칸마다 다르다 — {NULL_RANGE}.", "",
            *topic_table(t), "",
            f"표기 — `—` 원장에 없는 칸 · `∅` 아무것도 안 돌아옴 · `◐` 자세가 덜 참 · "
            f"`○` 움직이는 것이 없음 · `*` {MINUS}90{DEG} 는 잣대 퇴화.",
        )

        for j, arm in enumerate(sorted(t["arms"]), start=2):
            a = t["arms"][arm]
            nb.md(f"### 절 {i}.{j} `{arm}`", "", " · ".join(arm_facts(arm)))
            nb.figure(a["figures"]["map"], f"{arm} micro-Doppler maps",
                      f"`{arm}` — 앙각별 맵. 위 줄이 받은 그대로, 아래 줄이 정지 성분을 "
                      "뺀 판이다. 흰 점선이 날개끝 상한이고, 구석 상자에는 네 가지가 "
                      "적힌다 — 리듬 몫[%]과 **그 칸의 백색잡음 값** · 상한 위가 움직이는 "
                      "에너지의 몇 %인가 · 상한 **아래**를 보는 빗살 대비[dB] · 박자. "
                      "수를 낼 자격이 없는 칸은 그 까닭만 적힌다.")
            nb.figure(a["figures"]["band"], f"{arm} blade-band rhythm spectrum",
                      f"`{arm}` — 날개 대역 전력이 뛰는 리듬의 스펙트럼. 세로 점선이 "
                      f"예측 박자 {a['f_flash_hz']:g} Hz 의 정수배다.")
            nb.md(*arm_table(arm))

    nb.marks.append((None, None, None, len(nb.cells)))   # 주제 절이 끝난 자리

    # ── ③ 이름 읽는 법 ────────────────────────────────────────────────────
    rows = []
    for tok, mean, dflt, pred in TOKEN_TABLE:
        cnt = sum(1 for arm in IDX_ARM if pred(arm.split("_"), arm))
        rows.append(f"| {tok} | {mean} | {dflt} | {cnt} |")
    nb.md(
        "---", "",
        f"## 절 {n_tok}. 팔 이름 읽는 법",
        "",
        "팔 이름은 «무엇을 바꾼 판인가» 를 밑줄로 이어 붙인 것이다. "
        "그림 파일 이름이 `<주제번호><주제>__<팔 이름>__map.png` 라서, "
        "**이 표만 있으면 파일 이름만 보고 그 판이 무엇인지 안다**.",
        "",
        "⭐읽는 요령은 **없는 토막이 곧 기본값**이라는 것이다 — `_r15` 가 없으면 "
        "15 m 가 아니라 옛 기본 10 m 이고, `_n8192` 가 없으면 자세가 4,096 이다. "
        "그래서 아래 표에는 «토막이 없으면 무엇인가» 칸을 함께 뒀다.",
        "",
        "| 토막 | 뜻 | 토막이 없으면 | 이 토막을 단 팔 |",
        "|---|---|---|---|",
        *rows,
        "",
        "**읽어 보기**",
        "",
        "| 팔 이름 | 읽으면 |",
        "|---|---|",
        "| `sionna_p4000000000_phys_r15_n8192_d1` | PathSolver · 광선 40 억 · 물리 전부 켬 "
        "· 15 m · 자세 8,192 · 반사 깊이 1 |",
        "| `sionna_p4000000000_swR1D0E0F1_mini5pro_r15_n8192_d1` | PathSolver · 광선 40 억 "
        "· 굴절 + 확산 반사만 · **표적이 Mini 5 Pro**(박자 183.33 Hz) · 15 m · 자세 8,192 "
        "· 깊이 1 |",
        "| `ours_free_r15_n8192` | 우리 커널이되 **동체 면을 뺀** 대조군 · 15 m · 자세 8,192 |",
        "| `ours` | 우리 커널 · 토막이 하나도 없으니 **전부 기본값** — 10 m · 자세 4,096 "
        "· 격자 λ/12 |",
        "",
        "**팔 → 주제 찾아보기**",
        "",
        "| 팔 | 주제 | 그림 파일 앞머리 |",
        "|---|---|---|",
        *[f"| `{arm}` | {IDX['topics'][ARM_TOPIC[arm]]['label_ko'].split(' — ')[0]} "
          f"| `{ARM_TOPIC[arm]}__{arm}__` |" for arm in sorted(IDX_ARM)],
    )

    # ── ④ 읽을 때 주의 ────────────────────────────────────────────────────
    deg_cells = sum(1 for a in IDX_ARM.values() for c in a["cells"].values()
                    if c.get("tip_ceiling_degenerate"))

    def _rng(arm):
        return float(ROWS[(arm, IDX_ARM[arm]["elevations_deg"][0])]["range_m"])
    by_rng: dict[float, list[str]] = {}
    for arm in sorted(IDX_ARM):
        by_rng.setdefault(_rng(arm), []).append(arm)
    off15 = sorted(r for r in by_rng if abs(r - 15.0) > 1e-9)
    nb.md(
        "---", "",
        f"## 절 {n_warn}. ⚠읽을 때 주의",
        "",
        f"### {n_warn}.1 앙각 {MINUS}90{DEG} 는 잣대가 퇴화한다",
        "",
        f"직하방에서는 날개가 도는 면이 시선과 **수직**이라 날개끝 상한 f_tip 이 0 Hz 다"
        f"(f_tip ∝ cos el). 상한이 0 이면 «상한 **위**» 가 전 대역이 되어, 리듬 몫이 "
        f"«날개가 만들 수 없는 자리에 무엇이 남았나» 를 재는 잣대이기를 그만둔다 — "
        f"그냥 전 대역의 빗살 정도를 재는 수가 된다. 그림에서는 그 칸 제목에 `*` 가 붙고 "
        f"각주가 달린다. 표에서도 `*` 다. 이 원장에서 그런 칸은 **{deg_cells} 개**다.",
        "",
        f"대역 에너지 그림도 마찬가지다 — {MINUS}90{DEG} 는 날개 대역 자체가 정의되지 않아 "
        f"**0{DEG} 의 대역을 빌려** 그린다. 참값이 «선 없음» 인 자리라서, 거기서 빗살이 서면 "
        f"그것이 곧 인공물이라는 뜻이다. 범례에 «band borrowed from 0{DEG}» 로 적혀 있다.",
        "",
        f"### {n_warn}.2 ⛔팔 사이의 **절대 세기**를 비교하지 마라",
        "",
        "우리 커널과 PathSolver 는 **눈금이 다르다** — 같은 표적을 같은 자리에서 재도 "
        "«전력 −70 dB» 와 «−94 dB» 는 세기의 비교가 아니다. 광선 예산 · 격자 · 정규화가 "
        "엔진마다 다르게 들어간 수라, 두 팔의 dB 를 빼는 순간 그 차이는 물리가 아니라 "
        "구현의 차이가 된다.",
        "",
        "**그래서 이 아틀라스는 «모양» 과 «구조» 로만 말한다** — 맵은 패널마다 자기 "
        "최댓값으로 정규화하고, 팔을 가로지르는 비교는 리듬 몫[%] · 박자[Hz] · 박자 ÷ 예측 "
        "처럼 **눈금에 무관한 수**로만 한다. 같은 팔 안에서 앙각끼리 dB 를 비교하는 것은 "
        "된다(같은 눈금이다).",
        "",
        f"### {n_warn}.3 격자 흔들림 밴드 안이면 판정 불가",
        "",
        f"표면 격자를 λ/12 에서 λ/24 로 조이기만 해도 잣대가 움직인다. 그 폭이 "
        f"**리듬 몫 {rhy_band:.1f} %p · 움직이는 전력 {ac_band:.2f} dB** 다"
        f"(`outputs/grid_convergence_check.json`, 앙각 네 점에서 잰 최대값).",
        "",
        f"⭐그러므로 **두 팔의 차이가 리듬 몫 {rhy_band:.1f} %p 안이면 «차이가 있다» 고 "
        f"말할 수 없다.** 예를 들어 58 과 63 의 차이는 판정 불가이고, 83 과 13 의 차이는 "
        f"밴드 밖이라 살아 있다. 이 표의 수를 어디에 인용하든 «λ/12 한정» 을 함께 적는다.",
        "",
        "⚠**두 수는 서로 다른 앙각의 값이고, 전역 최댓값이다.** 원장의 앙각별 밴드는 "
        "리듬 몫이 0° 11.8 · −15° **0.1** · −30° **21.8** · −45° 12.9 · −60° 16.0 · "
        "−75° 2.5 · −90° 16.4 %p, 움직이는 전력이 0° **3.86** · −15° 1.31 · −30° 0.37 dB "
        "다 — 즉 리듬 쪽은 −30° 값, 전력 쪽은 0° 값이다. 그 하나를 모든 칸에 대면 "
        "el −15° 에서는 그 앙각의 참 밴드(0.1 %p)보다 **218 배 넓은 자**가 된다. "
        "원장 자신이 경고해 뒀다 — `scorecard.band_rule_caveat_ko` 「⚠전역값이라 앙각별 "
        "밴드보다 넓다 — 넓은 밴드는 «판정 불가» 쪽으로 기울어 «안 바뀐다» 라는 결론에 "
        "**유리하다**」. 앙각별로 읽을 때는 `pairs[].moves_the_reading_by_el_band` 를 쓴다.",
        "",
        "⛔⛔**그리고 리듬 몫은 이 밴드로도 구제되지 않는다**(RETRACTION_LOG R29) — "
        "«λ/12 한정» 꼬리표로는 **부족하다**. 창 반폭 hw 를 2/8/32 Hz 로만 옮겨도 같은 "
        "데이터가 **9.9 / 63.4 / 90.0 %** 로 움직이고, `f_above` 를 함수 기본값"
        "(1.5·f_flash)으로 두면 63.4 % 가 **98.9 %** 가 된다"
        "(`outputs/rhythm_share_knob_audit_0825.json`). **격자보다 분석 손잡이가 더 크게 "
        "흔든다** — 리듬 몫의 **크기는 인용하지 않고 순서만** 읽는다. 크기를 말해야 하면 "
        "자유 파라미터 없는 양(요동 진폭비 · |상관| · 크기비)을 쓴다.",
        "",
        f"### {n_warn}.4 한 원장에 **거리가 다른 팔**이 섞여 있다",
        "",
        f"이 원장의 기준 거리는 15 m 인데, 팔 {len(by_rng.get(15.0, []))} 개만 거기에 있다. "
        f"`_r` 토막이 없는 팔 {len(by_rng.get(10.0, []))} 개는 옛 기본 **10 m** 에서 잰 것이고 "
        f"— 원거리장 경계 2D²/λ ≈ 14.08 m 의 **안쪽**(근접장)이다 — `_r30` 팔 "
        f"{len(by_rng.get(30.0, []))} 개는 30 m 다. **거리가 다른 팔을 나란히 놓을 때는 "
        f"그 사실을 반드시 적는다.** 주제별 요약 표에 거리 열을 둔 이유다.",
        "",
        "| 거리 | 팔 수 | 어느 팔인가 |",
        "|---|---|---|",
        *[f"| **{r:g} m** | {len(by_rng[r])} | "
          + ("기준 거리 — 나머지 팔 전부" if abs(r - 15.0) < 1e-9
             else " · ".join(f"`{x}`" for x in by_rng[r])) + " |"
          for r in sorted(by_rng)],
        "",
        f"### {n_warn}.5 ⭐**근접장은 기체마다 다른 자리에서 시작한다**",
        "",
        "원거리장 경계는 2D²/λ 다 — D 가 표적 크기라, **기체가 커지면 경계가 멀어진다.** "
        f"기본 기체({META['drone_default']}) 기준의 14.08 m 하나를 모든 팔에 대면 틀린다. "
        "기체별로 다시 계산하면 이렇다(원장과 같은 규약 — 메쉬 3D 대각).",
        "",
        "| 기체 | 표적 크기 D | 원거리장 경계 2D²/λ | 이 원장의 팔이 선 거리 | 판정 |",
        "|---|---|---|---|---|",
        *FF_ROWS,
        "",
        f"⚠**그래서 «15 m 면 원거리장» 이 아니다.** {FF_INSIDE_KO}",
        "",
        "근접장에서는 파면이 표적 위에서 휘어 날개끝과 동체가 서로 다른 위상 기울기를 받는다. "
        "그러니 그런 팔의 dB 는 물론 **리듬 몫도** 엔진 차이로 읽으면 안 된다 — "
        "«한 축만 다른 짝» 이라고 부르기 전에 이 표를 먼저 본다.",
        "",
        f"### {n_warn}.6 기체 태그가 붙은 팔은 박자가 다르다",
        "",
        "⚠이름에 `mini5pro` · `s1000plus` 가 박힌 팔은 표적이 바뀐 판이라 **예측 박자가 "
        "다르다** — 날개 수 × 호버 rpm ÷ 60 이라 기체마다 다른 수가 나온다. "
        f"원장 `_meta.f_flash_hz` 는 기본 기체({META['drone_default']}) 값이라 "
        "그대로 쓰면 그 팔의 점선이 전부 엉뚱한 자리에 선다.",
        "",
        "| 기체 | 박자 | 이 원장의 팔 |",
        "|---|---|---|",
        *[f"| {lab} | {ff:g} Hz | {n} |" for lab, ff, n in sorted(
            {(a["airframe_label"], a["f_flash_hz"],
              sum(1 for b in IDX_ARM.values()
                  if b["airframe"] == a["airframe"]))
             for a in IDX_ARM.values()}, key=lambda x: -x[2])],
        "",
        "이 아틀라스의 그림은 팔마다 `src/drones.py` 에서 박자를 다시 계산해 점선을 "
        f"세웠다 — 절 {n_aud}.3 의 자기검사가 그것을 확인한다.",
        "",
        f"### {n_warn}.7 ⭐리듬 몫의 **널도 기체마다 다르다**",
        "",
        f"백색잡음이면 리듬 몫이 얼마로 나오나 — {NULL_RANGE}. 창 폭(±8 Hz)을 박자로 나눈 "
        "값이 곧 널이라, 박자가 빠른 기체일수록 낮다. 그러므로 «13 아래면 리듬 없음» 은 "
        "기본 기체에서만 맞는 말이다. 표와 그림은 **그 칸의 널**을 함께 적는다.",
        "",
        f"### {n_warn}.8 **몇 자세가 튄 칸**의 박자는 박자가 아니다",
        "",
        f"|AC| 의 최대 ÷ 중앙(= 튐 지표)이 100 을 넘는 칸이 **{len(SPIKY)} 개**다. "
        "자세 몇 개가 통째로 다른 값이면 맵은 그 자리에 세로 줄 하나만 남기고 나머지가 "
        "바닥색으로 깔리고(패널마다 자기 최댓값으로 정규화하므로), 그때 잡히는 «박자» 는 "
        "회전이 아니라 **그 튐들의 간격**이다. 표·그림에 «⚡ 큰 자세»·«(spiky)» 로 적었다. "
        "예측의 0.5 배 미만처럼 이상한 배수가 나오면 먼저 이 깃발을 본다. "
        "⚠이 잣대는 «얼마나 큰가» 만 잰다 — «얼마나 혼자인가» 는 바로 아래 절이다.",
        "",
        f"### {n_warn}.9 ⭐자세 **하나**가 헤드라인을 끄는 칸 {len(MOVES)} 개",
        "",
        "⛔**철회됨** — 2026-08-16 에 «−60° 에서 반사 깊이 3 이면 리듬 몫이 86.6 → 32.4 % 로 "
        "무너진다» 는 "
        "판정이 **자세 8,192 개 중 하나** 때문이었다. 그 자세를 이웃 평균으로 갈아 끼우면 두 "
        "판이 85.5 대 85.2 % 로 같다. 그래서 튐 진단을 **모든 칸에 상시로** 돌린다 — 그 칸에서 "
        "가장 큰 자세 하나를 이웃 평균으로 갈아 끼우고 헤드라인 넷(리듬 몫 · 빗살 대비 · 요동 "
        "전력 · 상한 위 몫)을 다시 재서, 움직인 폭이 ① 죄 없는 자세 12 개·둘째 자세를 같은 "
        "방법으로 갈아 끼웠을 때보다 꼬리 울타리 밖으로 크고 ② 그 앙각의 **격자 산포 밴드**보다 "
        "크면 «튐» 이다. 문턱은 둘 다 원장에서 읽어 온다"
        f"(`{OUT_META.get('threshold_source', '(없음)')}` · 밴드 "
        f"`{OUT_META.get('band_source', '(없음)')}`).",
        "",
        *([f"- ⚑ **{a}** {e}° — {c.get('outlier_why_ko', '')}" for a, e, c in MOVES]
          or ["- (지금 원장에는 «튐» 등급 칸이 없다)"]),
        "",
        f"- ⌗ **덜 찍힌 플래시 {len(UNDERS)} 개** — ⭐**튐이 아니다.** 진짜 날개 플래시가 "
        "**한 표본 폭**으로 찍힌 것이다(에코는 날개끝 상한으로 대역제한이라 플래시의 최소 폭이 "
        "0° 에서 7.7 표본이어야 한다). 고칠 곳은 그 칸이 아니라 **표집**이고, 그 칸의 «상한 위 "
        "몫 · 빗살 대비» 를 인용할 때는 그 단서를 함께 적는다.",
        f"- ◈ **경계 칸 {len(SHAKY)} 개** — 쏠림의 분모가 «죄 없는 자세 12 개의 최댓값» 이라 "
        "어느 12 개를 뽑느냐에 등급이 걸린다. 중앙값 대조군으로 다시 재서 판정이 갈리면 이 "
        "깃발을 세우고, 감식 원장(`outputs/outlier_census_0816.json`)의 등급도 나란히 적는다.",
        "",
        "⛔**깃발이 떴다고 그 칸을 자동으로 버리지 마라.** 뜻은 «이 수는 자세 하나에 걸려 "
        "있으니 그 자세를 열어 보라» 이지 «틀렸다» 가 아니다 — 로터가 시선과 딱 맞는 순간의 "
        "**진짜 정반사 플래시**도 이렇게 보인다. 그래서 «얼마나 큰가»(최대÷중앙)는 등급에 안 "
        "쓰고, «날개가 지나갈 때마다 다시 서나 · 이웃 자세와 이어지나 · 갈아 끼우면 헤드라인이 "
        "움직이나» 로만 판정한다.",
        "",
        f"### {n_warn}.10 박자와 맵은 **다른 구간**에서 잰 수다",
        "",
        f"{META.get('beat_window_ko', '')} 같은 상자 안에 있어도 «맵에 보이는 것» 과 "
        "«박자 수치» 는 같은 창의 이야기가 아니다.",
        "",
        f"### {n_warn}.11 ⭐아직 **못 고친 것** — 알고 쓰라고 적어 둔다",
        "",
        f"- **덜 찬 칸 {len(INCOMPLETE)} 개의 참값** — 원장을 다시 병합해야 나온다. 이 문서는 "
        f"원장을 읽기만 한다. 그 가운데 {max(0, len(INCOMPLETE) - 1)} 칸은 자세가 뭉텅이로 "
        "빠져 «0 을 걷어내고 다시 재는» 길도 없다(균일 표본이 아니다).",
        "- **주제 분류(`topic_of`)가 아직 이름 토막으로 거리를 본다** — 그래서 `_r` 토막이 "
        f"없는 10 m 옛 팔이 «기본 엔진» 주제에 남아 있다. 원장 `range_m` 으로 바꾸면 그 팔들이 "
        "거리 주제로 옮겨가 그림 파일 이름이 전부 바뀌므로, 주제를 다시 짤 때 함께 고친다 — "
        f"그 사이의 안전장치가 절 {n_warn}.4 의 거리 표와 그림 속 거리 라벨이다.",
        "- **맵은 패널마다 자기 최댓값으로 밝기를 맞춘다** — 그래서 거리와 세기를 그림에서 "
        "읽을 수 없다. 공통 눈금을 쓰면 눈금이 다른 두 엔진을 한 색역에 올리는 더 큰 거짓이 "
        "되므로 그대로 두었다.",
        "- **리듬 몫의 창 반폭은 8 Hz 고정** — `build_deck_maps.structure_bars` 와 정의를 "
        "맞추려고 그대로 두었다. 그 대가로 높은 배음일수록 창 밖으로 새어 100 이 도달 불가다.",
        "",
        "수리의 «전 → 후» 수치는 `outputs/atlas_falsify.json` 에 있다 "
        "(`benchmark/audit_atlas_repair.py`).",
    )

    # ── ⑤ 누락 검사 ───────────────────────────────────────────────────────
    lines = ["---", "", f"## 절 {n_aud}. 누락 검사", "",
             f"> **원장 {A['n_ledger_cells']} 칸 가운데 그림이 없는 칸은 "
             f"{len(A['no_fig'])} 개다.**", ""]
    lines += [
        "세는 법 — 팔 하나의 맵 그림은 **그 팔이 가진 앙각을 가로로 늘어놓은 격자**라, "
        "칸 하나가 열 하나다. 그래서 «칸에 그림이 있나» 는 «그 칸이 어느 맵의 열로 "
        "그려졌나» 로 센다. 색인을 믿지 않고 원장 npz 의 키에서 팔과 앙각을 다시 뽑아 "
        "맞췄다.", "",
        "| 검사 | 결과 |", "|---|---|",
        f"| 원장 팔 · 칸 | {A['n_ledger_arms']} 팔 · {A['n_ledger_cells']} 칸 "
        f"(원장 `rows` {A['n_rows']} 행과 일치) |",
        f"| 그림 열이 없는 칸 | **{len(A['no_fig'])} 개** |",
        f"| 색인에만 있고 원장에 없는 팔 | {len(A['arms_in_index_not_ledger'])} 개 |",
        f"| 원장에만 있고 색인에 없는 팔 | {len(A['arms_in_ledger_not_index'])} 개 |",
        f"| 색인이 가리키는데 디스크에 없는 그림 파일 | {len(A['no_file'])} 개 |",
        "",
    ]
    if A["no_fig"]:
        lines += ["**그림이 없는 칸**", "", "| 팔 | 앙각 |", "|---|---|"]
        lines += [f"| `{a}` | {deg_txt(e)} |" for a, e in A["no_fig"]]
        lines += [""]
    else:
        lines += ["빠진 칸이 없으므로 아래에 목록이 없다. 대신 «그림은 있는데 "
                  "볼 것이 없는 칸» 과 «애초에 원장에 없는 자리» 를 남긴다 — "
                  "찾다가 허탕치는 자리는 그 둘이다.", ""]

    lines += [f"### {n_aud}.1 그림은 있는데 **아무것도 안 돌아온** 칸 "
              f"({len(A['empty'])} 개)", "",
              "원장의 시계열이 통째로 0 인 칸이다(원장 `level_db` 도 −6000 이라는 표식이 "
              "붙는다 — 잰 세기가 아니라 **«없음» 표식**이다). 맵은 그려지지만 패널에 "
              "«nothing came back» 이라고 적히고, 대역 에너지 그림에는 그 앙각의 곡선이 "
              "**아예 안 그려진다** — 0 을 dB 로 바꾸면 −∞ 라 보이지 않는 선이 범례에만 "
              "남기 때문이다.", "",
              "⚠**왜 비었나 를 스위치 탓으로만 적으면 틀린다.** 생성기 "
              "`benchmark/elevation_sweep_md.py` 는 `los=True, specular_reflection=True` 를 "
              "**하드코딩**하고 굴절·회절·모서리·확산만 `--sw` 로 켜고 끈다. 즉 "
              "`swR0D0E0F0` 도 «전부 끔» 이 아니라 «정반사와 직선경로는 켜 둔 채 나머지 "
              "넷을 끈» 판이다. 그런데도 표적 경유 경로가 0 개라는 것이 사실이다 "
              "(원장 실측 −30°: `swR0D0E0F0` 경로 0 · `swR1D0E0F0`(굴절만) 0 · "
              "`swR0D1E0F0`(회절만) 8).", "",
              "| 팔 | 앙각 | 왜 |", "|---|---|---|"]
    for arm, ek, c in A["empty"]:
        why = ("PathSolver 순정 기본값 조합(정반사·굴절 켬)이 이 앙각에서 표적 경유 경로를 "
               "하나도 못 찾았다"
               if "stockdef" in arm else
               "굴절 · 회절 · 모서리 · 확산을 끈 조합 — **정반사·LOS 는 켜져 있는데도** "
               "표적 경유 경로가 0 개다"
               if "swR0D0E0F0" in arm else
               "굴절만 켠 조합(정반사·LOS 는 켬)이 이 앙각에서 경로를 못 찾았다")
        lines.append(f"| `{arm}` | {deg_txt(float(ek))} | {why} |")

    # ── ⭐덜 찬 칸 · 안 움직이는 칸 ──────────────────────────────────────
    lines += ["", f"### {n_aud}.1b ⭐**아직 덜 찬** 칸 ({len(A['incomplete'])} 개) — "
              "수를 내지 않는다", ""]
    if A["incomplete"]:
        lines += [
            "원장 `n_missing` 열이 «이 칸은 자세가 덜 찼다» 고 적어 둔 칸이다(또는 시계열 "
            "안에 «정확히 0» 인 표본이 섞여 있는 칸). 실험이 도는 중이라 병합이 아직 절반인 "
            "것이다.", "",
            "⭐**왜 수를 내면 안 되나** — 빠진 자세 자리가 0 으로 채워져 있어서, 0 채움이 "
            "스펙트럼을 PRF/2 · PRF/4 자리에 **복제**한다. 그 복제본이 «날개끝 상한 위» 에 "
            "앉아 그 대역의 에너지를 거의 다 차지하고, 그래서 리듬 몫이 0 % 로 주저앉는다 — "
            "**물리가 아니라 결측 자국**이다. 맵에는 날개 무늬가 또렷한데 구석에 «0 %» 가 "
            "적히는 모순이 그렇게 생겼다(2026-08-15 정정 전 판이 그랬다).", "",
            f"⚠**«0 을 빼고 다시 재면 되지 않나»** — 안 된다. 덜 찬 {len(INCOMPLETE)} 칸 "
            "가운데 빠진 자리가 균일한 칸은 하나뿐이고(한 칸 걸러 하나), 나머지 "
            f"{max(0, len(INCOMPLETE) - 1)} 칸은 자세가 뭉텅이로 빠져 "
            "(4 개 중 2·3번째, 8 개 중 5~8번째) **균일 표본이 아니다** — 그런 자료의 "
            "스펙트럼은 정의되지 않는다. 고치는 길은 하나뿐이다: **원장을 다시 병합한다.**", "",
            "| 팔 | 앙각 | 들어온 자세 | 빠진 자세 | 거리 |", "|---|---|---|---|---|"]
        for arm, ek, c in A["incomplete"]:
            miss = max(c.get("n_missing") or 0, c.get("n_zero_samples") or 0)
            lines.append(f"| `{arm}` | {deg_txt(float(ek))} | "
                         f"{thousands(c['n_poses'] - miss)} | {thousands(miss)} | "
                         f"{c.get('range_m')} m |")
        lines += [""]
        if A["shards_newer_than_ledger"]:
            lines += [f"⚠**원장 병합이 낡았다** — `outputs/elev_sweep_shards/` 에 원장보다 "
                      f"새로운 샤드가 {len(A['shards_newer_than_ledger'])} 개 있다. "
                      "다시 병합하면 이 칸들이 채워질 수 있다(이 아틀라스는 원장만 읽으므로 "
                      "병합은 스윕 쪽 일이다).", ""]
    else:
        lines += ["지금은 없다.", ""]

    lines += [f"### {n_aud}.1c **움직이는 것이 없는** 칸 ({len(A['no_motion'])} 개)", ""]
    if A["no_motion"]:
        lines += ["시계열이 사실상 상수인 칸이다 — AC/DC 가 배정밀도 반올림 바닥(1e-12) "
                  "아래다. 프로펠러를 뺀 대조군이 그렇다: 돌아가는 것이 없으니 흔들릴 것도 "
                  "없다.", "",
                  "⭐그런 칸에서 뽑은 «박자» 는 **1 ULP(마지막 자리 한 칸)를 흔든 자리**라 "
                  "재현되지 않는다 — 계산 순서를 조금만 바꿔도 봉우리가 다른 자리로 "
                  "옮겨간다. 그래서 수를 내지 않는다(정정 전 판은 «beat 204 Hz = 1.61x · "
                  "움직이는 전력 −384 dB» 라고 적었다. −384 dB 는 물리량이 아니다).", "",
                  "| 팔 | 앙각 | AC/DC |", "|---|---|---|"]
        for arm, ek, c in A["no_motion"]:
            lines.append(f"| `{arm}` | {deg_txt(float(ek))} | {c.get('ac_over_dc')} |")
        lines += [""]
    else:
        lines += ["지금은 없다.", ""]

    lines += ["", f"### {n_aud}.2 애초에 **원장에 없는 자리** "
              f"({A['n_absent']} 칸)", "",
              f"7 점 격자(0{DEG} · {MINUS}15{DEG} … {MINUS}90{DEG})를 다 채웠다면 "
              f"{META['n_arms']} × 7 = {META['n_arms']*7} 칸일 텐데 원장에는 "
              f"{A['n_ledger_cells']} 칸이 있다. 나머지 {A['n_absent']} 칸은 **안 돌린 자리**다 — "
              f"그림이 빠진 것이 아니라 계산이 없다. 표와 지도에서 `—` 로 나온다.", "",
              "대부분은 설계가 그랬다 — 스위치 조합 판은 «어느 스위치가 리듬을 죽이나» "
              f"하나만 물으려고 {MINUS}30{DEG} 한 점에서만 돌렸고, 방위 · 부품 판은 네 점"
              f"(0{DEG} · {MINUS}30{DEG} · {MINUS}60{DEG} · {MINUS}90{DEG}), 격자 판은 "
              f"위쪽 네 점(0{DEG} ~ {MINUS}45{DEG})만 돌렸다. 거리 판은 정면 한 점이고, "
              f"평면파 판은 직하방 한 점이다.", ""]
    #: ⭐설계 격자 네 가지 — 7 점 · 성긴 4 점 · 촘촘한 4 점 · 1 점.
    #  어디에도 안 맞는 팔은 «왜 비었는지 원장이 말해 주지 않는» 자리다.
    PATTERNS = [set(FULL_ELS), {0.0, -30.0, -60.0, -90.0},
                {0.0, -15.0, -30.0, -45.0}]
    odd = sorted(arm for arm in A["absent"]
                 if len(IDX_ARM[arm]["elevations_deg"]) > 1
                 and set(IDX_ARM[arm]["elevations_deg"]) not in PATTERNS)
    if odd:
        lines += ["⚠**설계 격자 어디에도 안 맞는 팔이 있다.** 위 네 가지(7 점 · 성긴 "
                  "4 점 · 촘촘한 4 점 · 1 점) 중 어느 것도 아닌 앙각 구성이다 — "
                  "왜 그 칸만 비었는지는 원장에 적혀 있지 않다. 그 자리를 인용하려면 "
                  "다시 돌려야 한다.", "",
                  "| 팔 | 있는 앙각 | 없는 앙각 |", "|---|---|---|"]
        for arm in odd:
            have = IDX_ARM[arm]["elevations_deg"]
            lines.append(f"| `{arm}` | " + " · ".join(deg_txt(e) for e in have)
                         + " | **" + " · ".join(deg_txt(e) for e in A["absent"][arm])
                         + "** |")
        lines += [""]
    lines += ["**전체 목록** — 원장에 칸이 덜 찬 팔 "
              f"{len(A['absent'])} 개(나머지 {META['n_arms'] - len(A['absent'])} 개는 "
              f"7 점을 다 채웠다).", "",
              "| 팔 | 없는 앙각 |", "|---|---|"]
    for arm in sorted(A["absent"]):
        lines.append(f"| `{arm}` | "
                     + " · ".join(deg_txt(e) for e in A["absent"][arm]) + " |")

    lines += ["", f"### {n_aud}.3 자기검사", "", "| 검사 | 통과 | 실측 |", "|---|---|---|"]
    for name, ok, detail in self_checks(A):
        lines.append(f"| {name} | {'✅' if ok else '❌'} | {detail} |")
    lines += ["", "| | |", "|---|---|",
              f"| 출력 | `reports/A_atlas.ipynb` |",
              f"| 읽는 것 | `outputs/md_atlas_index.json` · "
              f"`outputs/elevation_sweep_md.{{json,npz}}` · "
              f"`outputs/grid_convergence_check.json` · `src/drones.py` |",
              "| 만든 곳 | `benchmark/build_atlas_toc.py` "
              "(그림은 `benchmark/build_md_atlas.py`) |",
              "| 소요 | CPU 로 수 초. GPU 를 안 쓴다 |"]
    nb.md(*lines)
    return nb


#: 편 꼬리 — 주제 순서대로 A · B · C …  (사용자 지시 2026-09-03: 「A,B,C 이런식으로 쪼개서」)
SUFFIX = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _cell(*lines) -> dict:
    """NB.md 와 같은 모양의 마크다운 셀 하나 — 편을 이을 때 쓴다."""
    txt = '\n'.join(lines)
    return {"cell_type": "markdown", "metadata": {},
            "source": [l + '\n' for l in txt.split('\n')]}


def _write(path: str, cells: list) -> int:
    doc = {"cells": cells,
           "metadata": {"kernelspec": {"display_name": "py312", "language": "python",
                                       "name": "py312"},
                        "language_info": {"name": "python"}},
           "nbformat": 4, "nbformat_minor": 5}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    return len(cells)


def main():
    """⭐한 권이 아니라 **지도 + 주제별 편**으로 낸다.

    ⛔전에는 전부 한 파일이었다 — 그림 수백 장이 한 노트북에 들어가 열기도 무거웠고,
      한 주제만 보려는 사람이 전체를 받아야 했다. 주제 경계는 build() 가 marks 에 적어 준다.
    """
    t0 = time.time()
    nb = build()
    marks = getattr(nb, "marks", [])
    if not marks:
        print("⛔주제 경계가 없다 — 나눌 수 없다")
        raise SystemExit(1)

    head_end, tail_start = marks[0][3], marks[-1][3]
    made = []
    for n, (tk, label, sec, start) in enumerate(marks[:-1]):
        end = marks[n + 1][3]
        suf = SUFFIX[n]
        fn = f"A_atlas_{suf}.ipynb"
        head = _cell(f"# 도감 {suf} — {label}", "",
                     "[← 도감 지도](A_atlas.ipynb) 로 돌아간다. "
                     f"이 편은 도감의 **절 {sec}** 하나다 — 주제마다 파일을 나눴다.")
        n_cells = _write(os.path.join(ROOT, "reports", fn),
                         [head] + nb.cells[start:end])
        made.append((suf, label, fn, n_cells))

    guide = _cell(
        "## 이 도감은 여러 편으로 나뉜다", "",
        "| 편 | 주제 | 파일 |", "|---|---|---|",
        *[f"| {suf} | {label} | [{fn}]({fn}) |" for suf, label, fn, _ in made], "",
        "⭐그림이 수백 장이라 한 파일에 담으면 열기가 무겁다. "
        "주제 하나만 볼 사람이 전체를 받지 않아도 되게 나눴다(2026-09-03).")
    n_head = _write(OUT, nb.cells[:head_end] + [guide] + nb.cells[tail_start:])

    print(f"✅ {os.path.relpath(OUT, ROOT)}  셀 {n_head} (지도)")
    for suf, label, fn, n in made:
        print(f"   ✅ reports/{fn}  셀 {n:3d} · {label}")
    print(f"   그림 {nb.fig} 장 · {time.time()-t0:.1f} 초")


if __name__ == "__main__":
    main()
