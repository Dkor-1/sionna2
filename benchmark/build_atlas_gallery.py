# -*- coding: utf-8 -*-
"""
build_atlas_gallery.py — 마이크로도플러 아틀라스의 **보기 쉬운 갤러리**(HTML)를 굽는다.

무엇을 만드나
------------
`benchmark/build_md_atlas.py` 가 원장 `outputs/elevation_sweep_md.{json,npz}` 의 팔 54 개 ·
칸 220 개를 그림 122 장으로 굽고 목록을 `outputs/md_atlas_index.json` 에 남겼다.
이 파일은 그 색인을 읽어 **브라우저로 넘겨 보는 갤러리**를 `atlas/` 에 만든다.

  atlas/index.html        — 대문(읽는 법 · 주제 카드 9 장 · 이름 읽는 법 · 주의)
  atlas/NN_<주제>.html    — 주제별 페이지 9 장(팔마다 맵 · 대역 그림 + 요약 표)
  atlas/README.md         — 같은 내용의 마크다운 판(VSCode 미리보기 · 깃허브용)

설계 규칙
--------
⭐**그림을 복사하지 않는다** — `../outputs/figures/atlas/…` 상대경로로만 건다.
  (`atlas/` 는 `outputs/` 와 형제 폴더라 `../` 하나면 닿는다. 굽고 나서 실제로 파일이
  있는지 전부 확인하고, 없으면 개수를 찍는다.)
⭐**팔 이름은 HTML 로 찍는다** — 앙각이 하나뿐인 팔의 맵 그림은 캔버스가 좁아 제목(팔 이름)이
  오른쪽에서 잘린다. 갤러리는 이름을 그림 밖 캡션으로 내보내 그 결함을 우회한다.
⭐**수치는 손으로 안 적는다** — 색인 · 원장 · `grid_convergence_check.json` 에서 읽어 넣는다.
⭐**자체 포함** — CSS 를 파일 안에 넣는다(CDN · 외부 폰트 없음). 인터넷 없이 열린다.
  밝은 배경 · 어두운 배경 둘 다 색을 명시한다(`prefers-color-scheme`).

⛔GPU 를 안 쓴다 — `sionna.rt` · `mitsuba` 를 부르지 않는다. 저장된 json 만 읽는다.

돌리는 법
--------
    /workspace/.venvs/py312/bin/python benchmark/build_atlas_gallery.py

그림이 늘거나 원장이 바뀌면 `build_md_atlas.py` 를 먼저 돌리고 이 파일을 다시 돌린다.
(원장이 색인보다 새로우면 페이지 맨 위에 «낡음» 띠가 뜬다.)
"""
from __future__ import annotations

import argparse
import html
import json
import math
import os
import re
import struct
import time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

IDX_P = os.path.join(ROOT, "outputs", "md_atlas_index.json")
LED_J = os.path.join(ROOT, "outputs", "elevation_sweep_md.json")
LED_N = os.path.join(ROOT, "outputs", "elevation_sweep_md.npz")
GRID_P = os.path.join(ROOT, "outputs", "grid_convergence_check.json")
OUTDIR = os.path.join(ROOT, "atlas")

MINUS = "−"        # U+2212 — 각도의 음수 부호(하이픈 아님)
DEG = "°"

RE_SW = re.compile(r"^sw(?:[A-Z]\d)+$")
RE_AZ = re.compile(r"^az[-+]?\d+(?:\.\d+)?$")
RE_R = re.compile(r"^r(\d+(?:\.\d+)?)$")
RE_DIV = re.compile(r"^div\d+$")
RE_P = re.compile(r"^p\d+$")
RE_N = re.compile(r"^n\d+$")
RE_D = re.compile(r"^d\d+$")

DRONE_KEYS = ("matrice4e", "mini5pro", "s1000plus", "mini2", "phantom3", "m350rtk", "x500v2")


# ═══════════════════════════════════════════════════════════════════════════ #
#  0. 읽기
# ═══════════════════════════════════════════════════════════════════════════ #
IDX = json.load(open(IDX_P, encoding="utf-8"))
LED = json.load(open(LED_J, encoding="utf-8"))
META = IDX["_meta"]
ROWS = {(r["engine"], float(r["el_deg"])): r for r in LED["rows"]}

try:
    GRID = json.load(open(GRID_P, encoding="utf-8"))
    _L3 = GRID["grid_dispersion_bands"]["bands"]["layer3_metric"]
    _L2 = GRID["grid_dispersion_bands"]["bands"]["layer2_statistics"]
    RHY_BAND = float([b for b in _L3 if b["metric"] == "rhythm_share_pp"][0]["band"])
    AC_BAND = float([b for b in _L2 if b["metric"] == "ac_power_db"][0]["band"])
    BAND_SRC = "outputs/grid_convergence_check.json"
except Exception:                                            # pragma: no cover
    RHY_BAND, AC_BAND, BAND_SRC = float("nan"), float("nan"), "(없음)"

RANGE_PRIMARY = float(META.get("range_m_primary", 15.0))
#: ⛔2026-08-15 수리 — «백색잡음 = 13 %» 는 **기본 기체에서만** 맞는 수다. 널은 창 폭을
#  박자로 나눈 값이라 기체마다 다르다(matrice4e ≈ 12.6 · s1000plus ≈ 10.8 · mini5pro ≈ 8.7).
#  13 하나를 모든 팔에 대면 자기 널 위인 칸이 «리듬 없음» 으로 읽힌다 — 그래서 **칸마다**
#  색인의 rhythm_null_pct 를 쓴다. 이 상수는 그 값이 없을 때의 마지막 보루일 뿐이다.
NOISE_FLOOR_FALLBACK = 12.5
#: 색인이 적어 둔 잣대 설명 — «상한 위만 본다» 는 경고가 여기에 들어 있다
RHY_SCALE = META.get("rhythm_ko", "")
COMB_SCALE = META.get("comb_ko", "")


def null_of(c: dict) -> float:
    """그 칸의 백색잡음 값[%] — 없으면 마지막 보루."""
    v = (c or {}).get("rhythm_null_pct")
    return float(v) if v is not None else NOISE_FLOOR_FALLBACK


def readable(c: dict) -> bool:
    """⭐이 칸의 수를 인용해도 되나 — 덜 참 · 안 움직임 · 에코 없음이면 안 된다."""
    return bool(c) and c.get("rhythm_share_pct") is not None \
        and not (c.get("incomplete") or c.get("no_motion") or c.get("no_return"))


def _farfield_table():
    """⭐기체마다의 원거리장 경계 2D²/λ — «15 m 면 원거리장» 이 참이 아님을 표로 못 박는다.

    ⛔GPU 를 안 쓴다 — `src/drones.py` 는 순수 파이썬(geom → numpy)이라 `sionna.rt`·`mitsuba`
      를 부르지 않는다. 규약은 원장과 같다(D = 메쉬 **3D 대각**, 그 값이 원장의 14.08 m 다).
    """
    import sys
    sys.path.insert(0, os.path.join(ROOT, "src"))
    try:
        from drones import DRONES, build_drone
    except Exception:                                        # pragma: no cover
        return []
    lam = 2.998e8 / float(META["fc_hz"])
    out = []
    for key in sorted({a["airframe"] for a in ARM_IDX.values()}):
        b0, b1 = build_drone(DRONES[key]).bounds()
        D = float(sum((float(y) - float(x)) ** 2 for x, y in zip(b0, b1)) ** 0.5)
        r_ff = 2.0 * D * D / lam
        rs = sorted({float(arm_row(x)["range_m"]) for x in ARM_IDX
                     if ARM_IDX[x]["airframe"] == key
                     and arm_row(x).get("range_m") is not None})
        bad = [r for r in rs if r < r_ff]
        out.append(dict(
            key=key, label=DRONES[key].name, D=D, r_ff=r_ff, ranges=rs,
            verdict=("전부 밖(원거리장)" if not bad else
                     "⚠" + " · ".join(f"<b>{r:g} m 는 근접장</b>(경계의 {r / r_ff:.2f} 배)"
                                      for r in bad))))
    return out

#: 팔 → 주제키 · 팔 → 색인 객체
ARM_IDX: dict[str, dict] = {}
ARM_TOPIC: dict[str, str] = {}
for _tk, _t in IDX["topics"].items():
    for _a, _v in _t["arms"].items():
        ARM_IDX[_a] = _v
        ARM_TOPIC[_a] = _tk
ALL_ARMS = set(ARM_IDX)
TOPICS = sorted(IDX["topics"].items(), key=lambda kv: kv[1]["order"])


# ═══════════════════════════════════════════════════════════════════════════ #
#  1. 주제마다 «무엇을 묻는 판인가» — 사용자가 정한 질문
# ═══════════════════════════════════════════════════════════════════════════ #
TOPIC_Q = {
    "base": "세 엔진이 같은 드론을 어떻게 그리나",
    "switch": "어느 물리 스위치가 무늬를 바꾸나",
    "airframe": "기체를 무늬로 가릴 수 있나",
    "azimuth": "드론이 돌면 어떻게 되나",
    "parts": "날개 신호는 어디서 오나",
    "range": "멀어지면 어떻게 되나",
    "ptd": "모서리 보정이 무늬를 바꾸나",
    "grid": "계산을 촘촘히 하면 답이 변하나",
    "planewave": "파면 곡률이 결과를 바꾸나",
}

#: 질문을 조금 더 풀어 쓴 한 줄(수치는 안 들어간다 — 수치는 아래에서 계산해 넣는다)
TOPIC_WHY = {
    #: ⛔2026-08-15 정정 — «같은 드론 · 같은 자리» 는 **거짓**이었다. 이 주제의 13 팔은
    #  10 m 8 팔 · 15 m 5 팔로 갈리고, 그 경계(matrice4e 원거리장 2D²/λ ≈ 14.08 m)를
    #  가로지른다. 반사 깊이·물리 스위치도 함께 갈린다. 헤드라인은 거리를 맞춰 묶는다.
    "base": "엔진(우리 커널 · Sionna PathSolver)과 광선 예산 · 자세 수를 갈아 끼운 판이다. "
            "⚠<b>같은 자리가 아니다</b> — 이 주제 안에서 거리가 10 m 와 15 m 로 갈리고 "
            "(원거리장 경계 2D²/λ ≈ 14.08 m 를 가로지른다) 반사 깊이 · 물리 스위치도 함께 "
            "갈린다. 그래서 아래 헤드라인은 <b>거리를 맞춰서</b> 묶었다.",
    "switch": "굴절 · 회절 · 모서리 회절 · 확산 반사를 하나씩 켜고 끈 판이다. "
              "무엇을 켜면 날개 리듬이 살아나고 무엇을 끄면 주저앉는지를 한 축씩 본다.",
    "airframe": "표적 기체를 바꾼 판이다. 날개 수와 회전수가 다르면 «박자»가 달라지므로, "
                "그림의 박자가 그 기체 값으로 따라가면 무늬로 기체를 가릴 수 있다는 뜻이다.",
    "azimuth": "정면(방위 0°)이 아니라 옆에서 본 판이다. 지금까지의 결론이 방위 한 자리에서만 "
               "서는 것인지 확인한다.",
    "parts": "장면에서 부품을 빼 본 판이다. 프로펠러만 남기거나, 프로펠러만 뺀다. "
             "날개 무늬를 만드는 것이 정말 프로펠러인지 귀속시킨다.",
    "range": "표적까지의 거리를 15 m 에서 30 m 로 물린 판이다. 멀어지면 되돌아오는 힘이 약해지는데, "
             "무늬 자체가 남는지를 본다. ⚠<b>이 주제의 잣대는 거리를 못 읽는다</b> — 리듬 몫도 "
             "빗살 대비도 «모양»을 재는 수라 에코 전체가 공통 인수로 작아지는 것에 둔감하다. "
             "거리를 말하려면 절대 눈금(dB)이 함께 있어야 하는데, 엔진끼리는 그 dB 를 비교할 수 "
             "없다. 그러니 여기서 읽을 수 있는 것은 «같은 엔진 안에서 무늬가 남았나»뿐이다.",
    "ptd": "우리 커널의 모서리 회절 보정(PTD — 날카로운 모서리에서 새어 나오는 파를 더해 주는 보정)을 "
           "켠 판이다.",
    "grid": "우리 커널이 표면을 잘라 쓰는 격자를 λ/12 에서 λ/24 로 더 촘촘히 한 판이다. "
            "답이 격자에 따라 흔들리면 그 폭이 곧 «이만큼 차이는 판정 불가» 라는 문턱이 된다.",
    "planewave": "조명을 구면파(가까운 곳에서 퍼져 나가는 파) 대신 평면파(무한히 먼 곳에서 오는 평평한 파)로 "
                 "바꾼 판이다. 남은 신호가 파면의 휘어짐 탓인지 가린다.",
}


# ═══════════════════════════════════════════════════════════════════════════ #
#  2. 이름 토막 사전 — «팔 이름 읽는 법»
# ═══════════════════════════════════════════════════════════════════════════ #
def _has(pred):
    return lambda arm: pred(arm.split("_"), arm)


TOKENS = [
    ("ours", "우리 커널(SBR+PO). 광선을 쏘아 맞은 면에서 되쏘는 셈을 직접 한다. 동체가 있어 "
             "날개가 <b>가려지는</b> 판이다.",
     "—", _has(lambda t, a: a.startswith("ours") and not a.startswith("ours_free"))),
    ("ours_free", "같은 우리 커널인데 동체의 «면»만 빼서 <b>가림을 없앤</b> 대조군. 꼭짓점·상자·광선 격자는 "
                  "그대로라 «동체가 막느냐» 하나만 갈린다.",
     "—", _has(lambda t, a: a.startswith("ours_free"))),
    ("sionna", "Sionna RT 의 경로 추적기(PathSolver) 팔.",
     "—", _has(lambda t, a: a.startswith("sionna"))),
    ("p&lt;N&gt;", "쏘는 광선 수. <code>p4000000000</code> = 40 억 발.",
     "거리로 정하는 규칙값", _has(lambda t, a: any(RE_P.match(x) for x in t))),
    ("phys", "PathSolver 물리를 <b>전부 켠다</b> — 굴절 · 회절 · 모서리 회절.",
     "셋 다 끔", _has(lambda t, a: "phys" in t)),
    ("swR#D#E#F#", "스위치를 비트로 직접 준 판. <code>R</code> 굴절 · <code>D</code> 회절 · "
                   "<code>E</code> 모서리 회절 · <code>F</code> 확산 반사이고 <code>1</code> 이 «켬». "
                   "예 <code>swR1D0E0F1</code> = 굴절 + 확산 반사.",
     "—", _has(lambda t, a: any(RE_SW.match(x) for x in t))),
    ("stockdef", "PathSolver 를 <b>순정 기본값 그대로</b> — 굴절 켬 · 회절 끔 · 모서리 끔 · 확산 끔 · 깊이 3. "
                 "우리 «끔» 판과도 «켬» 판과도 다른 제3 의 조합이다.",
     "—", _has(lambda t, a: "stockdef" in t)),
    ("only&lt;x&gt;", "스위치를 <b>하나만</b> 켠 판 — <code>onlyrefr</code> 굴절 · <code>onlydiffr</code> 회절 · "
                      "<code>onlyedge</code> 모서리 회절 · <code>onlydepth3</code> 깊이 3.",
     "—", _has(lambda t, a: any(x.startswith("only") for x in t))),
    ("d&lt;N&gt;", "PathSolver 가 몇 번까지 튕긴 경로를 세는가(반사 깊이).",
     "물리를 켜면 3, 아니면 1", _has(lambda t, a: any(RE_D.match(x) for x in t))),
    ("parts&lt;…&gt;", "장면에 넣을 부품. <code>partsprop</code> = 프로펠러만 · "
                       "<code>partsnoprop</code> = 프로펠러를 뺀 나머지.",
     "기체 전체", _has(lambda t, a: any(x.startswith("parts") for x in t))),
    ("기체 태그", "표적 기체를 바꾼 판 — <code>mini5pro</code> · <code>s1000plus</code>. "
                  "⚠박자와 날개끝 상한이 <b>함께</b> 바뀐다.",
     "원장 기본 " + str(META.get("drone_default", "matrice4e")),
     _has(lambda t, a: ARM_IDX[a]["airframe_tagged"])),
    ("az&lt;N&gt;", "방위각[°] — 드론을 옆에서 보는 각. <code>az45</code> = 45° 옆.",
     "0" + DEG + "(정면)", _has(lambda t, a: any(RE_AZ.match(x) for x in t))),
    ("r&lt;N&gt;", "표적까지 거리[m]. <code>r15</code> = 15 m · <code>r30</code> = 30 m.",
     "옛 기본 10 m", _has(lambda t, a: any(RE_R.match(x) for x in t))),
    ("n&lt;N&gt;", "찍은 자세 수(시간 방향 표본 수). <code>n8192</code> = 8,192 자세.",
     "원장 기본 4,096", _has(lambda t, a: any(RE_N.match(x) for x in t))),
    ("div&lt;N&gt;", "우리 커널이 표면을 자르는 격자 간격 λ/N. <code>div24</code> = λ/24.",
     "규약값 λ/12", _has(lambda t, a: any(RE_DIV.match(x) for x in t))),
    ("ptd", "우리 팔의 <b>모서리 회절 보정</b>(PTD) 켬.",
     "끔", _has(lambda t, a: "ptd" in t)),
    ("pw", "<b>평면파</b> 조명 — 무한히 먼 곳에서 오는 평평한 파(구면파 대신).",
     "구면파", _has(lambda t, a: "pw" in t)),
]

SW_BIT = {"R": "굴절", "D": "회절", "E": "모서리 회절", "F": "확산 반사"}
ONLY_KO = {"refr": "굴절만", "diffr": "회절만", "edge": "모서리 회절만", "depth3": "깊이 3 만"}


# ═══════════════════════════════════════════════════════════════════════════ #
#  3. 잔손질
# ═══════════════════════════════════════════════════════════════════════════ #
def now_kst() -> str:
    """⚠컨테이너는 UTC 로 돈다 — 보고는 한국시간(KST = UTC+9)으로 적는다."""
    return time.strftime("%Y-%m-%d %H:%M", time.gmtime(time.time() + 9 * 3600)) + " KST"


def stamp_kst(t: float) -> str:
    return time.strftime("%Y-%m-%d %H:%M", time.gmtime(t + 9 * 3600)) + " KST"


def built_at_kst() -> str:
    """색인의 `built_at`(컨테이너 시계 = UTC)을 KST 로 옮긴다 — 한 페이지 안에서 시계를 섞지 않는다."""
    raw = str(META.get("built_at", ""))
    try:
        t = time.mktime(time.strptime(raw, "%Y-%m-%d %H:%M:%S")) - time.timezone
        return stamp_kst(t)
    except Exception:
        return raw


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def deg_txt(el: float) -> str:
    if abs(el) < 1e-9:
        return "0" + DEG
    return ("+" if el > 0 else MINUS) + f"{abs(el):.0f}" + DEG


def cell_key(el: float) -> str:
    return f"{el:+.0f}"


def num(v, spec="{:.1f}", dash="—"):
    """수 하나 — 없으면 «—», 음수는 U+2212(각도 표기와 같은 부호)."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return dash
    return spec.format(v).replace("-", MINUS)


def thousands(n) -> str:
    return f"{int(n):,}"


def si_rays(n) -> str:
    """광선 수를 한국어 단위로 — 40 억 · 2.5 억 처럼.

    ⚠2026-08-15 수리: `:g` 로 찍어서 11,111,111 발이 «1111.11 만» 이 되었다(목차 문서는
      같은 수를 «1,111 만» 으로 적어 두 문서가 갈렸다). 만 단위는 **반올림해 천단위 쉼표**로
      적고, 정확한 수가 필요한 자리에서는 옆에 원수를 함께 낸다."""
    v = float(n)
    if v >= 1e8:
        return (f"{v / 1e8:,.0f} 억" if v / 1e8 >= 10 else f"{v / 1e8:g} 억")
    if v >= 1e4:
        return (f"{v / 1e4:,.0f} 만" if v / 1e4 >= 10 else f"{v / 1e4:g} 만")
    return f"{int(v):,}"


def png_size(path: str):
    """PNG 폭·높이 — 외부 라이브러리 없이 헤더만 읽는다."""
    try:
        with open(path, "rb") as f:
            head = f.read(33)
        if head[:8] != b"\x89PNG\r\n\x1a\n":
            return None
        w, h = struct.unpack(">II", head[16:24])
        return int(w), int(h)
    except Exception:
        return None


MISSING: list[str] = []
LINKED: set[str] = set()


def rel(fig: str) -> str:
    """색인의 저장소 상대경로 → **atlas/ 기준** 상대경로. 없으면 기록해 둔다.

    ⚠`atlas/` 와 `outputs/` 는 형제 폴더라 `../` 하나면 닿는다 — 굽고 나서 실제로
      파일이 있는지 여기서 전부 확인한다(브라우저에서 깨진 그림이 뜨지 않게).
    """
    if os.path.exists(os.path.join(ROOT, fig)):
        LINKED.add(fig)
    else:
        MISSING.append(fig)
    return "../" + fig.replace(os.sep, "/")


def abspath_of(fig: str) -> str:
    return os.path.join(ROOT, fig)


# ═══════════════════════════════════════════════════════════════════════════ #
#  4. 팔이 «무엇을 바꾼 판인가» — 원장 열에서 읽는다
# ═══════════════════════════════════════════════════════════════════════════ #
def arm_row(arm: str) -> dict:
    els = ARM_IDX[arm]["elevations_deg"]
    return ROWS.get((arm, float(els[0])), {})


def arm_facts(arm: str) -> list[str]:
    """⚠이름만 믿으면 10 m 팔을 15 m 로 잘못 읽는다 — 거리 · 자세 · 광선 · 깊이 · 격자는 원장에서."""
    row = arm_row(arm)
    t = arm.split("_")
    a = ARM_IDX[arm]
    f: list[str] = []

    if arm.startswith("ours_free"):
        f.append("엔진 <b>우리 커널</b>(동체 면을 빼 가림 없앤 대조군)")
    elif arm.startswith("ours"):
        f.append("엔진 <b>우리 커널</b>(SBR+PO, 가림 있음)")
    else:
        f.append("엔진 <b>Sionna PathSolver</b>")

    if row.get("range_m") is not None:
        f.append(f"거리 {float(row['range_m']):g} m")
    if row.get("n_poses"):
        f.append(f"자세 {thousands(row['n_poses'])} 개")
    if row.get("spp"):
        # ⚠단위 표기는 반올림이다 — 원수를 툴팁에 남긴다(문서끼리 갈리지 않게)
        f.append(f'광선 <span title="정확히 {thousands(row["spp"])} 발">'
                 f"{si_rays(row['spp'])} 발</span>")
    if row.get("grid_div"):
        f.append(f"격자 λ/{int(row['grid_div'])}")
    if row.get("max_depth"):
        f.append(f"반사 깊이 {int(row['max_depth'])}")

    if "stockdef" in t:
        f.append("스위치 <b>순정 기본값</b>(굴절만 켬 · 확산 끔)")
    else:
        swt = [x for x in t if RE_SW.match(x)]
        onl = [x for x in t if x.startswith("only")]
        if swt:
            bits = swt[0][2:]
            on = [SW_BIT[bits[i]] for i in range(0, len(bits), 2) if bits[i + 1] == "1"]
            f.append("스위치 " + (" + ".join(on) if on else "<b>전부 끔</b>"))
        elif onl:
            f.append("스위치 " + ONLY_KO.get(onl[0][4:], onl[0][4:]) + " 켬")
        # ⚠2026-08-15 정정 — `physics` 는 **PathSolver 전용 축**이다(굴절·회절·모서리 회절).
        #   우리 커널 팔에도 원장이 False 를 적어 둔 행이 있어서, 그대로 옮기면 «존재하지 않는
        #   축에서 갈리는» 것처럼 보였다(ours 10 팔 중 6 팔에 «스위치 물리 끔» 이 붙었다).
        elif not arm.startswith("ours"):
            if row.get("physics") is True:
                f.append("스위치 물리 <b>전부 켬</b>")
            elif row.get("physics") is False:
                f.append("스위치 물리 끔")

    for x in t:
        if x.startswith("parts"):
            f.append("장면 <b>프로펠러만</b>" if x == "partsprop"
                     else ("장면 <b>프로펠러 뺀 나머지</b>" if x == "partsnoprop" else f"장면 {x[5:]}"))
    if "ptd" in t:
        f.append("모서리 보정(PTD) <b>켬</b>")
    if "pw" in t:
        f.append("조명 <b>평면파</b>")
    az = row.get("az_deg")
    if az is not None and abs(float(az)) > 1e-9:
        f.append(f"방위 {float(az):g}{DEG}")

    f.append(f"표적 {a['airframe_label']}"
             + ("(<b>기체 태그</b>)" if a["airframe_tagged"] else "")
             + f" · 박자 {a['f_flash_hz']:g} Hz")
    return f


#: 기체마다의 원거리장 경계 — `arm_row` 가 있어야 계산되므로 여기서 만든다
FARFIELD = _farfield_table()
NEARFIELD_ARMS = sorted(
    x for x in ARM_IDX
    for r in FARFIELD if r["key"] == ARM_IDX[x]["airframe"]
    if arm_row(x).get("range_m") is not None
    and float(arm_row(x)["range_m"]) < r["r_ff"])


def counterpart(arm: str) -> str | None:
    """⭐«한 축만 다른 짝 팔» — 그 주제를 만드는 토막만 빼고 같은 이름이 있으면 그것."""
    slug = ARM_IDX[arm]["topic"]
    t = arm.split("_")
    keep, changed = [], False
    for x in t:
        if slug == "switch" and (RE_SW.match(x) or x.startswith("only") or x == "stockdef"):
            changed = True
            continue
        if slug == "azimuth" and RE_AZ.match(x):
            changed = True
            continue
        if slug == "parts" and x.startswith("parts"):
            changed = True
            continue
        if slug == "grid" and RE_DIV.match(x):
            changed = True
            continue
        if slug == "ptd" and x == "ptd":
            changed = True
            continue
        if slug == "planewave" and x == "pw":
            changed = True
            continue
        if slug == "airframe" and x in DRONE_KEYS:
            changed = True
            continue
        if slug == "range":
            m = RE_R.match(x)
            if m and abs(float(m.group(1)) - RANGE_PRIMARY) > 1e-9:
                keep.append(f"r{RANGE_PRIMARY:g}")
                changed = True
                continue
        keep.append(x)
    cand = "_".join(keep)
    return cand if (changed and cand in ALL_ARMS and cand != arm) else None


def pair_delta(arm: str, other: str):
    """두 팔이 함께 가진 앙각에서 리듬 몫 차이 — (칸 수, 최대 |Δ|, 평균 Δ, 뺀 칸 수).

    ⭐2026-08-15 수리 두 가지
      ① **잣대가 퇴화한 −90° 칸을 뺀다** — 그 칸의 «리듬 몫» 은 다른 열과 같은 수가 아니다
         (상한이 0 이라 전 대역을 재는 다른 잣대다). 넣어 두면 짝 비교의 최댓값이 그 칸에서
         나와 «차이가 살아 있다» 가 엉뚱한 자리에서 선다.
      ② **수를 낼 자격이 없는 칸을 뺀다**(덜 참 · 안 움직임 · 에코 없음).
    """
    ca, cb = ARM_IDX[arm]["cells"], ARM_IDX[other]["cells"]
    d, skipped = [], 0
    for k, v in ca.items():
        w = cb.get(k)
        if not w:
            continue
        if not (readable(v) and readable(w)):
            skipped += 1
            continue
        if v.get("tip_ceiling_degenerate") or w.get("tip_ceiling_degenerate"):
            skipped += 1
            continue
        d.append(v["rhythm_share_pct"] - w["rhythm_share_pct"])
    if not d:
        return None
    return len(d), max(abs(x) for x in d), sum(d) / len(d), skipped


# ═══════════════════════════════════════════════════════════════════════════ #
#  5. 주제마다 ⭐핵심 발견 3 줄 — 전부 색인에서 계산한다
# ═══════════════════════════════════════════════════════════════════════════ #
def verdict(spread: float, *, slug: str | None = None) -> str:
    """폭 하나를 격자 흔들림 밴드에 대 본다 — 밴드 안이면 «차이가 있다»고 말하지 않는다.

    ⚠이 밴드는 **우리 커널의 격자 축**(λ/12 ↔ λ/24)에서 나온 수다. PathSolver 에는 그 축이
      아예 없다 — 그러니 «PathSolver 팔끼리의 차이» 를 이 밴드로 재는 것은 빌려 쓰는 것이고,
      그 사실을 문장에 적는다.
    ⚠08grid 주제는 **이 밴드를 만든 바로 그 짝**이다. 자기 자신과 비교하는 자리라 «판정 불가»
      가 아니라 «이 짝이 밴드의 정의» 라고 적는다(2026-08-15 수리)."""
    if math.isnan(RHY_BAND):
        return ""
    if slug == "grid":
        return (f"⚠이 짝이 바로 <b>밴드 {RHY_BAND:.1f} %p 를 정의한 짝</b>이다 — "
                "자기 자신과 대는 자리라 판정 대상이 아니다")
    return (f"격자 흔들림 밴드 {RHY_BAND:.1f} %p 밖이라 <b>차이가 살아 있다</b>" if spread > RHY_BAND
            else f"격자 흔들림 밴드 {RHY_BAND:.1f} %p 안이라 <b>판정 불가</b>")


def engine_of(arm: str) -> str:
    if arm.startswith("ours_free"):
        return "우리 커널(가림 없앤 대조군)"
    if arm.startswith("ours"):
        return "우리 커널(SBR+PO)"
    return "Sionna PathSolver"


def arm_beat_ok(a: dict) -> bool:
    """그 팔이 잡은 박자가 자기 기체의 예측 박자 ±2 % 안인가(칸 다수결)."""
    v = [c["beat_over_flash"] for c in a["cells"].values()
         if c.get("beat_over_flash") is not None]
    return bool(v) and sum(abs(x - 1.0) <= 0.02 for x in v) * 2 >= len(v)


def cells_of_topic(tinfo: dict):
    for nm, a in tinfo["arms"].items():
        for k, c in a["cells"].items():
            yield nm, k, c


def comb_says_blades(c: dict):
    """상한 **아래** 빗살 대비가 «날개가 있다» 고 말하나 — (판정, 수치).

    널이 0 dB 이므로 +3 dB 를 문턱으로 둔다(백색잡음 실측 +0.4 dB)."""
    v = (c or {}).get("comb_contrast_db")
    if v is None:
        return None, None
    return bool(v >= 3.0), float(v)


def no_rhythm_tail(hi_name: str, hi_cell: dict, tinfo: dict) -> str:
    """⭐«리듬이 아예 남지 않았다» 를 **함부로 쓰지 않는다.**

    2026-08-15 수리 — 옛 판은 «가장 높은 팔조차 13 % 아래 → 리듬이 아예 남지 않았다» 를
    자동으로 찍었다. 두 군데가 틀렸다.
      ① 13 은 기본 기체의 널이다. 자기 널이 8.7 인 팔이 9 % 를 내면 «없다» 가 아니다.
      ② 이 잣대는 **상한 위**만 본다. 상한 **아래** 에 빗살이 서 있으면 «리듬이 없다» 는
         거짓이다 — 그 자리를 보는 짝 잣대가 바로 빗살 대비[dB]다.
    그래서 두 잣대가 **함께** 널일 때만 «안 보인다» 고 쓰고, 아니면 «이 잣대로는 못 읽는다» 로 쓴다.
    """
    null = null_of(hi_cell)
    if hi_cell["rhythm_share_pct"] >= null:
        return ""
    ok, v = comb_says_blades(hi_cell)
    if ok:
        return (f" 다만 <b>«리듬이 없다»고 읽으면 안 된다</b> — 이 잣대는 상한 <b>위</b>만 "
                f"보는데, 같은 칸의 상한 <b>아래</b> 빗살 대비는 <b>{v:+.1f} dB</b>"
                "(백색잡음 0 dB)라 날개 무늬가 대역 안에 그대로 있다는 뜻이다. "
                "이 자리에서는 «못 읽는다»가 맞는 말이다.")
    if ok is False:
        return (f" 그 칸의 백색잡음 값은 {null:.1f} % 이고, 상한 <b>아래</b>를 보는 빗살 "
                f"대비도 <b>{v:+.1f} dB</b>(백색잡음 0 dB)라 <b>두 잣대가 함께</b> "
                "«날개 리듬이 안 보인다»고 말한다.")
    return (f" 그 칸의 백색잡음 값은 {null:.1f} % 다. ⚠짝 잣대(상한 아래 빗살 대비)는 이 "
            "앙각에서 대역이 좁아 정의되지 않으므로, 한 잣대만으로 «리듬이 없다»고 "
            "단정하지 않는다.")


def topic_findings(tkey: str, tinfo: dict) -> list[str]:
    slug = tkey[2:]
    arms = tinfo["arms"]
    out: list[str] = []

    # ── ⓪ ⭐먼저 «이 주제로 결론을 내도 되나» ────────────────────────────────
    inc = [(nm, k) for nm, k, c in cells_of_topic(tinfo) if c.get("incomplete")]
    nomo = [(nm, k) for nm, k, c in cells_of_topic(tinfo) if c.get("no_motion")]
    n_read = sum(1 for _, _, c in cells_of_topic(tinfo) if readable(c))
    if inc:
        out.append(
            f"⛔<b>이 주제는 아직 결론을 낼 수 없다</b> — 칸 {len(inc)} 개가 "
            "<b>자세가 덜 찬 상태</b>다(병합이 절반이다). 빈 자세 자리가 0 으로 채워져 "
            "있어서 그 0 채움이 스펙트럼을 PRF/2 · PRF/4 에 복제하고, 그 복제본이 "
            "«상한 위»를 삼켜 리듬 몫을 0 % 로 만든다 — 물리가 아니라 <b>결측 자국</b>이다. "
            "그래서 그 칸에는 수를 싣지 않았다("
            + " · ".join(f"<code>{esc(nm)}</code> {deg_txt(float(k))}" for nm, k in inc)
            + "). 원장을 다시 병합한 뒤에 읽어야 한다."
            + (f" 남은 읽을 수 있는 칸은 {n_read} 개다." if n_read else
               " <b>이 주제에는 읽을 수 있는 칸이 하나도 없다.</b>"))

    # ── ⓪-b ⭐이 주제 안에 «자세 하나가 끄는 칸» 이 있나 ─────────────────────
    #    있으면 그 칸의 수를 근거로 쓰기 전에 그 자세를 열어 봐야 한다(버리라는 뜻이 아니다).
    mov = [(nm, k, c) for nm, k, c in cells_of_topic(tinfo)
           if c.get("one_pose_moves_headline")]
    und = [(nm, k) for nm, k, c in cells_of_topic(tinfo)
           if c.get("flash_comb_undersampled")]
    if mov:
        out.append(
            f"⚑<b>자세 하나가 헤드라인을 끄는 칸이 {len(mov)} 개</b> 있다 — "
            + " · ".join(f"<code>{esc(nm)}</code> {deg_txt(float(k))}"
                         f"(자세 #{c.get('outlier_argmax_pose')})" for nm, k, c in mov)
            + ". 가장 큰 자세 하나를 이웃 평균으로 갈아 끼우면 헤드라인이 그 앙각의 격자 산포 "
              "밴드 밖으로 움직인다. ⛔<b>버리라는 뜻이 아니다</b> — 그 자세가 진짜 정반사 "
              "플래시일 수도 있으니, 이 칸의 수를 근거로 쓰기 전에 그 자세를 열어 본다.")
    if und:
        out.append(
            f"⌗<b>플래시가 한 표본 폭으로 찍힌 칸이 {len(und)} 개</b> 있다 — "
            "튐이 <b>아니라</b> 시간 분해능 문제다(참 신호가 표본 간격보다 좁다). "
            "그 칸의 «상한 위 몫 · 빗살 대비»를 인용할 때는 그 단서를 함께 적는다.")

    # ── ① 팔 사이(팔이 하나면 앙각 사이) 리듬 몫이 얼마나 벌어지나 ──────────
    el_count = Counter()
    for a in arms.values():
        for k, c in a["cells"].items():
            if readable(c):
                el_count[k] += 1
    el_star = None
    if el_count:
        el_star, n_at = el_count.most_common(1)[0]
        vals = sorted(
            ((nm, a["cells"][el_star]["rhythm_share_pct"]) for nm, a in arms.items()
             if el_star in a["cells"] and readable(a["cells"][el_star])),
            key=lambda x: x[1])
        if len(vals) >= 2:
            lo, hi = vals[0], vals[-1]
            sp = hi[1] - lo[1]
            tail = no_rhythm_tail(hi[0], arms[hi[0]]["cells"][el_star], tinfo)
            # ⭐양 끝 두 팔이 «한 축만» 다른 팔인지 확인한다 — 거리·광선 예산이 함께
            #   다르면 이 폭은 «엔진 차이» 가 아니다(2026-08-15 수리).
            cl, ch = arms[lo[0]]["cells"][el_star], arms[hi[0]]["cells"][el_star]
            diff = [n for n, k in (("거리", "range_m"), ("광선 예산", "spp"),
                                   ("자세 수", "n_poses"), ("반사 깊이", "max_depth"))
                    if cl.get(k) != ch.get(k)]
            warn = (f" ⚠양 끝 두 팔은 {' · '.join(diff)}도 다르다 — 이 폭을 «엔진 차이»로 "
                    "읽으면 안 된다." if diff else "")
            out.append(
                f"앙각 {deg_txt(float(el_star))} 에서 팔 {n_at} 개를 늘어놓으면 리듬 몫이 "
                f"<b>{lo[1]:.1f} %</b>(<code>{esc(lo[0])}</code>) 에서 "
                f"<b>{hi[1]:.1f} %</b>(<code>{esc(hi[0])}</code>) 까지 벌어진다 — "
                f"폭 {sp:.1f} %p 는 {verdict(sp, slug=slug)}.{warn}{tail}")
        else:
            nm, a = next(iter(arms.items()))
            xs = sorted((c["el_deg"], c["rhythm_share_pct"], c)
                        for c in a["cells"].values() if readable(c))
            if len(xs) >= 2:
                lo = min(xs, key=lambda x: x[1])
                hi = max(xs, key=lambda x: x[1])
                out.append(
                    f"팔이 하나뿐이라 앙각으로 읽는다 — 리듬 몫이 {deg_txt(lo[0])} 의 "
                    f"<b>{lo[1]:.1f} %</b> 에서 {deg_txt(hi[0])} 의 <b>{hi[1]:.1f} %</b> 까지 "
                    f"움직인다(그 칸의 백색잡음 값 {null_of(lo[2]):.1f}~{null_of(hi[2]):.1f} %)."
                    + no_rhythm_tail(nm, hi[2], tinfo))
            elif xs:
                el, v, c = xs[0]
                ok, cv = comb_says_blades(c)
                out.append(
                    f"이 주제는 읽을 수 있는 칸이 하나뿐이다 — {deg_txt(el)} 에서 리듬 몫 "
                    f"<b>{v:.1f} %</b>(그 칸의 백색잡음 값 {null_of(c):.1f} %"
                    + (f", 상한 아래 빗살 대비 {cv:+.1f} dB" if cv is not None else "")
                    + "). "
                    + (f"⚠{MINUS}90{DEG} 라 잣대가 퇴화한 자리이므로 «리듬이 있다»로 읽지 않는다."
                       if abs(el + 90) < 1e-9 else ""))

    # ── ② 박자가 예측과 맞나(팔 단위로 센다) ────────────────────────────────
    have = [a for a in arms.values()
            if any(c.get("beat_over_flash") is not None for c in a["cells"].values())]
    if have:
        ok = sum(arm_beat_ok(a) for a in have)
        out.append(
            f"박자(날개가 시선을 지나가는 빠르기)를 잰 팔 {len(have)} 개 중 <b>{ok} 개</b>가 "
            f"자기 기체의 예측 박자 ±2 % 안에 든다"
            + ("." if ok == len(have) else
               f" — 나머지 {len(have) - ok} 개는 봉우리가 다른 자리에 섰다는 뜻이니 "
               "대역 그림에서 점선과 봉우리가 어긋났는지 본다."))

    # ── ③ 주제마다 한 줄 더 ─────────────────────────────────────────────────
    if slug == "base" and el_star:
        # ⭐거리를 맞춰서 묶는다 — 이 주제는 10 m 팔과 15 m 팔이 섞여 있어서,
        #   섞어 평균하면 «엔진 차이» 안에 «거리 차이» 가 들어간다.
        by_eng: dict[tuple, list[float]] = {}
        for nm, a in arms.items():
            c = a["cells"].get(el_star)
            if readable(c):
                by_eng.setdefault((engine_of(nm), c.get("range_m")), []).append(
                    c["rhythm_share_pct"])
        rngs = sorted({k[1] for k in by_eng if k[1] is not None})
        if len(by_eng) >= 2:
            txt = " · ".join(
                f"{k[0]} @{k[1]:g} m {sum(v) / len(v):.0f} %(팔 {len(v)})"
                for k, v in sorted(by_eng.items(), key=lambda kv: (kv[0][1] or 0, kv[0][0])))
            out.append(
                f"엔진끼리 묶어 {deg_txt(float(el_star))} 의 리듬 몫을 평균하면 — {txt}. "
                + (f"⚠<b>거리를 맞춰서</b> 묶었다 — 이 주제의 팔은 {' · '.join(f'{r:g} m' for r in rngs)} "
                   "로 갈리므로, 섞어 평균하면 «엔진 차이» 안에 «거리 차이»가 들어간다. "
                   if len(rngs) > 1 else "")
                + "⚠dB(세기)는 엔진마다 눈금이 달라 비교하지 않는다.")
        # ⭐광선 예산 사다리 — **같은 거리**에서 spp 만 올린 PathSolver 팔
        #   (거리를 안 맞추면 사다리 안에 거리 차이가 섞인다)
        cand = [(c["spp"], nm, c["rhythm_share_pct"], c.get("comb_contrast_db"))
                for nm, a in arms.items()
                if (c := a["cells"].get(el_star)) and readable(c) and c.get("spp")
                and "phys" not in nm.split("_")]
        if cand:
            rmode = Counter(arms[nm]["cells"][el_star].get("range_m")
                            for _s, nm, _v, _cb in cand).most_common(1)[0][0]
            cand = [x for x in cand
                    if arms[x[1]]["cells"][el_star].get("range_m") == rmode]
        lad = sorted(cand, key=lambda x: x[0])
        if len(lad) >= 3 and len({x[0] for x in lad}) >= 3:
            same_r = True
            out.append(
                "⭐<b>광선을 부을수록 PathSolver 의 «리듬»이 무너진다</b> — "
                + " → ".join(f"{si_rays(s)} 발 {v:.1f} %" for s, _nm, v, _cb in lad)
                + f"(전부 {deg_txt(float(el_star))}"
                + (f" · 같은 거리 {arms[lad[0][1]]['cells'][el_star]['range_m']:g} m" if same_r else "")
                + "). 가장 적게 부은 <code>" + esc(lad[0][1]) + "</code> 의 높은 값은 "
                "<b>덜 수렴한 판</b>으로 보는 것이 맞다 — 최고값이라고 인용하면 안 된다.")
    elif slug == "airframe":
        by_af: dict[str, list] = {}
        for nm, a in arms.items():
            by_af.setdefault(a["airframe_label"], []).append((nm, a))
        seg = []
        #: 기본 기체는 이 주제에 없다(태그가 없는 팔은 «기본 엔진» 주제로 간다) — 잣대로 함께 적는다
        base_ref = next((a for a in ARM_IDX.values() if not a["airframe_tagged"]), None)
        if base_ref and base_ref["airframe_label"] not in by_af:
            seg.append(f"{base_ref['airframe_label']}(기본 기체 · 01base 쪽) 예측 "
                       f"{base_ref['f_flash_hz']:g} Hz")
        for lab, lst in sorted(by_af.items()):
            pred = lst[0][1]["f_flash_hz"]
            beats = [c["beat_hz"] for _, a in lst for c in a["cells"].values()
                     if c.get("beat_hz") is not None]
            got = (f"잰 값 {min(beats):.1f}~{max(beats):.1f} Hz" if beats else "잰 값 없음")
            seg.append(f"{lab} 예측 {pred:g} Hz({got})")
        out.append("기체마다 박자가 다르다 — " + " · ".join(seg)
                   + ". 그림이 그 기체 박자를 따라가면 <b>무늬로 기체를 가릴 수 있다</b>는 뜻이다.")
    else:
        pairs = []
        for nm in sorted(arms):
            cp = counterpart(nm)
            if cp:
                d = pair_delta(nm, cp)
                if d:
                    pairs.append((nm, cp, d))
        if pairs:
            pairs.sort(key=lambda x: -x[2][1])
            nm, cp, (n, mx, mean, skip) = pairs[0]
            n_out = sum(1 for _n, _c, d in pairs if d[1] > RHY_BAND)
            out.append(
                f"한 축만 다른 짝(<code>{esc(nm)}</code> ↔ <code>{esc(cp)}</code>)을 같은 앙각 "
                f"{n} 칸에서 빼면 리듬 몫 차이가 가장 큰 곳이 <b>{mx:.1f} %p</b>"
                f"(평균 {mean:+.1f} %p) — {verdict(mx, slug=slug)}."
                + (f" 뺀 칸 {skip} 개(잣대 퇴화 · 수를 낼 자격 없음)는 셈에서 제외했다."
                   if skip else "")
                + (f" ⭐짝이 있는 팔은 {len(pairs)} 개인데 그중 밴드 밖은 <b>{n_out} 개</b>다 — "
                   "여기 적은 것은 그중 <b>가장 큰 한 짝</b>일 뿐이니 주제 전체의 결론으로 "
                   "읽지 마라(팔마다 링크를 달아 두었다)." if len(pairs) > 1 else ""))
        else:
            nr = sum(1 for a in arms.values() for c in a["cells"].values() if c.get("no_return"))
            dg = sum(1 for a in arms.values() for c in a["cells"].values()
                     if c.get("tip_ceiling_degenerate"))
            out.append(
                f"이 주제에는 «한 축만 다른 짝 팔»이 없거나, 있어도 <b>비교할 수 있는 칸이 "
                f"없다</b>(짝의 칸이 «되돌아온 것 없음»·«덜 참»·«잣대 퇴화» 중 하나면 뺀다). "
                f"깃발은 되돌아온 게 없는 칸 <b>{nr} 개</b> · {MINUS}90{DEG} 잣대 퇴화 칸 "
                f"<b>{dg} 개</b> · 덜 찬 칸 <b>{len(inc)} 개</b>다.")
    return out[:5]


# ═══════════════════════════════════════════════════════════════════════════ #
#  6. CSS — 자체 포함 · 밝은 배경 / 어두운 배경 둘 다 명시
#     색: dataviz 기준 팔레트(순차 파랑 · 상태색 4). 막대는 한 가지 색(크기만 뜻이 있다).
# ═══════════════════════════════════════════════════════════════════════════ #
CSS = """
:root{
  color-scheme: light dark;
  --bg:#faf9f7; --surface:#ffffff; --surface-2:#f0efec; --line:#dedcd6;
  --ink:#131211; --ink-2:#4d4b46; --ink-3:#77746c;
  /* ⭐대비 — 배지·링크 글자는 배경 대비 4.5:1 이상이어야 읽힌다(2026-08-15 수리:
     밝은 배경에서 --serious 3.0:1 · --accent 3.9:1 이라 «▲ 잣대 퇴화» 배지가 흐렸다). */
  --accent:#1c62b8; --accent-soft:#cde2fb;
  --good:#0a7a0a; --warn:#8a6200; --serious:#b8501c; --critical:#c02626;
  --shadow: 0 1px 2px rgba(18,17,15,.06), 0 6px 18px rgba(18,17,15,.05);
}
@media (prefers-color-scheme: dark){
  :root{
    --bg:#141413; --surface:#1c1c1a; --surface-2:#262623; --line:#373733;
    --ink:#f6f5f1; --ink-2:#c3c2b7; --ink-3:#94928a;
    /* 어두운 배경에서는 반대로 **밝게** — #d03b3b 는 어두운 바탕에서 3.4:1 이었다 */
    --accent:#6fb0f5; --accent-soft:#184f95;
    --good:#4cc94c; --warn:#f0c04a; --serious:#f0a070; --critical:#f08b8b;
    --shadow: 0 1px 2px rgba(0,0,0,.4), 0 6px 18px rgba(0,0,0,.35);
  }
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{
  margin:0; background:var(--bg); color:var(--ink);
  font-family: "Pretendard","Apple SD Gothic Neo","Noto Sans KR","Malgun Gothic",
               system-ui,-apple-system,"Segoe UI",sans-serif;
  font-size:16px; line-height:1.72; letter-spacing:-.005em;
}
.wrap{max-width:1480px; margin:0 auto; padding:0 22px 96px}
a{color:var(--accent)}
code,kbd{font-family:"JetBrains Mono","SFMono-Regular",Menlo,Consolas,monospace;
  font-size:.88em; background:var(--surface-2); padding:.1em .38em; border-radius:5px;
  word-break:break-all}
h1{font-size:2.05rem; line-height:1.28; margin:.2em 0 .1em; letter-spacing:-.02em}
h2{font-size:1.42rem; margin:2.4em 0 .55em; letter-spacing:-.015em;
   padding-bottom:.3em; border-bottom:2px solid var(--line)}
h3{font-size:1.06rem; margin:0 0 .25em; letter-spacing:-.01em}
p{margin:.55em 0}
.lede{color:var(--ink-2); font-size:1.03rem; max-width:78ch}
.muted{color:var(--ink-3)}
.small{font-size:.86rem}

/* ── 위쪽 이동 띠 ─────────────────────────────────────────── */
.nav{position:sticky; top:0; z-index:20; background:var(--bg); border-bottom:1px solid var(--line); margin-bottom:26px}
.nav .inner{max-width:1480px; margin:0 auto; padding:9px 22px; display:flex; gap:10px;
  align-items:center; flex-wrap:wrap}
.nav a{display:inline-block; padding:5px 11px; border-radius:8px; text-decoration:none;
  color:var(--ink-2); font-size:.9rem; border:1px solid transparent}
.nav a:hover{background:var(--surface-2); color:var(--ink)}
.nav a.home{border-color:var(--line); color:var(--ink); font-weight:600}
.nav a.here{background:var(--accent-soft); color:var(--ink); font-weight:700}
.nav .sp{flex:1}

/* ── 머리 ─────────────────────────────────────────────────── */
header.top{padding:26px 0 6px}
.kicker{color:var(--accent); font-weight:700; font-size:.82rem; letter-spacing:.09em;
  text-transform:uppercase; margin-bottom:.35em}
.stats{display:flex; flex-wrap:wrap; gap:10px; margin:20px 0 6px}
.stat{background:var(--surface); border:1px solid var(--line); border-radius:12px;
  padding:11px 15px; min-width:104px; box-shadow:var(--shadow)}
.stat b{display:block; font-size:1.5rem; line-height:1.15; letter-spacing:-.02em}
.stat span{display:block; color:var(--ink-3); font-size:.79rem}

/* ── 상자 ─────────────────────────────────────────────────── */
.box{background:var(--surface); border:1px solid var(--line); border-radius:14px;
  padding:18px 20px; margin:16px 0; box-shadow:var(--shadow)}
.box h3{margin-top:0}
.note{border-left:4px solid var(--accent); background:var(--surface);
  border-radius:0 12px 12px 0; padding:14px 18px; margin:14px 0}
.note.warn{border-left-color:var(--warn)}
.note.crit{border-left-color:var(--critical)}
.stale{border-left-color:var(--serious)}
.grid2{display:grid; gap:16px; grid-template-columns:1fr}
@media (min-width:900px){ .grid2{grid-template-columns:1fr 1fr} }

/* ── 주제 카드 ────────────────────────────────────────────── */
.cards{display:grid; gap:18px; grid-template-columns:1fr}
@media (min-width:720px){ .cards{grid-template-columns:1fr 1fr} }
@media (min-width:1180px){ .cards{grid-template-columns:1fr 1fr 1fr} }
.card{background:var(--surface); border:1px solid var(--line); border-radius:14px;
  overflow:hidden; box-shadow:var(--shadow); display:flex; flex-direction:column;
  text-decoration:none; color:inherit}
.card:hover{border-color:var(--accent)}
.card .thumb{background:var(--surface-2); border-bottom:1px solid var(--line);
  aspect-ratio:16/9; overflow:hidden; display:flex; align-items:center; justify-content:center}
.card .thumb img{width:100%; height:100%; object-fit:contain; padding:6px}
.card .body{padding:14px 16px 16px}
.card .q{font-weight:700; font-size:1.04rem; margin:.1em 0 .3em; letter-spacing:-.01em}
.card .n{color:var(--ink-3); font-size:.83rem; margin-top:.5em}
.card .tag{display:inline-block; font-size:.74rem; letter-spacing:.06em; font-weight:700;
  color:var(--accent); text-transform:uppercase}

/* ── 그림 ─────────────────────────────────────────────────── */
.arm{background:var(--surface); border:1px solid var(--line); border-radius:14px;
  padding:18px 20px 20px; margin:22px 0; box-shadow:var(--shadow); scroll-margin-top:70px}
.arm .name{font-family:"JetBrains Mono","SFMono-Regular",Menlo,Consolas,monospace;
  font-size:1.0rem; font-weight:600; word-break:break-all; letter-spacing:-.01em}
.facts{color:var(--ink-2); font-size:.9rem; margin:.35em 0 .1em}
.facts b{color:var(--ink)}
.figrow{display:grid; gap:16px; grid-template-columns:1fr; margin-top:14px}
@media (min-width:1080px){ .figrow{grid-template-columns:var(--cols,1fr 1fr)} }
figure{margin:0; background:var(--surface-2); border:1px solid var(--line);
  border-radius:12px; overflow:hidden; display:flex; flex-direction:column}
figure img{display:block; width:100%; height:auto; background:#fff}
figure a{display:block; line-height:0}
figcaption{padding:11px 14px 13px; font-size:.86rem; color:var(--ink-2); line-height:1.6}
figcaption b{color:var(--ink)}
.figtitle{font-weight:700; color:var(--ink); font-size:.9rem}
.zoom{float:right; font-size:.76rem; color:var(--ink-3)}

/* ── 표 ───────────────────────────────────────────────────── */
.scroll{overflow-x:auto; margin:14px 0 2px; border:1px solid var(--line); border-radius:12px}
table{border-collapse:collapse; width:100%; font-size:.87rem; background:var(--surface)}
th,td{padding:7px 11px; text-align:right; white-space:nowrap;
  border-bottom:1px solid var(--line)}
th{background:var(--surface-2); color:var(--ink-2); font-weight:600; font-size:.8rem;
  position:sticky; top:0}
th:first-child,td:first-child{text-align:left}
tbody tr:last-child td{border-bottom:none}
tbody tr:hover td{background:var(--surface-2)}
td.el{font-variant-numeric:tabular-nums; font-weight:600}
td.n{font-variant-numeric:tabular-nums}
.bar{display:flex; align-items:center; gap:8px; justify-content:flex-end}
.bar .track{position:relative; width:78px; height:8px; border-radius:4px;
  background:var(--surface-2); border:1px solid var(--line); overflow:hidden; flex:none}
.bar .fill{position:absolute; left:0; top:0; bottom:0; background:var(--accent);
  border-radius:4px}
.bar .floor{position:absolute; top:-2px; bottom:-2px; width:1px; background:var(--ink-3)}
.bar .v{font-variant-numeric:tabular-nums; min-width:3.4em}
.badge{display:inline-block; font-size:.72rem; font-weight:700; padding:1px 7px;
  border-radius:999px; border:1px solid; margin-right:4px; white-space:nowrap}
.b-crit{color:var(--critical); border-color:var(--critical)}
.b-warn{color:var(--serious); border-color:var(--serious)}
.b-ok{color:var(--ink-3); border-color:var(--line)}

/* ── 이름 읽는 법 ─────────────────────────────────────────── */
.tok td:first-child{white-space:nowrap; font-family:"JetBrains Mono",monospace;
  font-size:.84rem; font-weight:600}
.tok td{white-space:normal; text-align:left}
.tok td.n{white-space:nowrap; text-align:right}
.tok th{text-align:left}
.tok th.n{text-align:right}

ul.find{margin:.4em 0 .2em; padding-left:1.15em}
ul.find li{margin:.3em 0}
ol.steps{padding-left:1.2em}
footer{margin-top:56px; padding-top:18px; border-top:1px solid var(--line);
  color:var(--ink-3); font-size:.83rem}
"""


# ═══════════════════════════════════════════════════════════════════════════ #
#  7. 조각 만들기
# ═══════════════════════════════════════════════════════════════════════════ #
def page(title: str, nav: str, body: str) -> str:
    return (
        "<!doctype html>\n<html lang=\"ko\">\n<head>\n"
        "<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        f"<title>{esc(title)}</title>\n<style>{CSS}</style>\n</head>\n<body>\n"
        f"{nav}\n<div class=\"wrap\">\n{body}\n"
        "<footer>"
        f"만든 것 <code>benchmark/build_atlas_gallery.py</code> · "
        f"재료 <code>outputs/md_atlas_index.json</code>(그림 구운 시각 {esc(built_at_kst())}) · "
        f"원장 <code>{esc(META['ledger'])}</code> · "
        f"갤러리 새로 구운 시각 {esc(now_kst())}<br>"
        "그림은 <b>복사하지 않았다</b> — <code>../outputs/figures/atlas/</code> 를 그대로 건다. "
        "그림이 늘면 <code>build_md_atlas.py</code> → <code>build_atlas_gallery.py</code> 순으로 다시 돌린다."
        "</footer>\n</div>\n</body>\n</html>\n")


def stale_banner() -> str:
    """원장이 색인보다 새로우면 «낡음» 띠."""
    try:
        cur = max(os.path.getmtime(LED_J), os.path.getmtime(LED_N))
    except OSError:
        return ""
    old = float(META.get("ledger_mtime", 0.0))
    if cur - old <= 1.0:
        return ""
    return ("<div class=\"note warn stale\"><b>⚠ 이 갤러리는 낡았다.</b> 원장이 그림보다 새롭다"
            f"(원장 {esc(stamp_kst(cur))} · 그림 {esc(built_at_kst())}). 실험이 새 행을 붙였다는 "
            "뜻이다 — "
            "<code>build_md_atlas.py</code> 를 먼저 돌리고 이 갤러리를 다시 구워야 최신이 된다.</div>")


#: 손으로 쓴 색인 페이지(생성기가 안 만든다) — 대문 nav 와 대문 첫 블록에서 건다.
SINCE_DECK = "00_since_deck.html"


def nav_bar(here: str, prev=None, nxt=None, *, since_deck: bool = False) -> str:
    parts = ['<div class="nav"><div class="inner">',
             '<a class="home" href="index.html">◇ 대문</a>']
    if since_deck:
        parts.append(f'<a href="{SINCE_DECK}">00 덱 이후</a>')
    for tkey, _t in TOPICS:
        cls = ' class="here"' if tkey == here else ""
        parts.append(f'<a href="{page_name(tkey)}"{cls}>{esc(tkey)}</a>')
    parts.append('<span class="sp"></span>')
    if prev:
        parts.append(f'<a href="{page_name(prev)}">← {esc(prev)}</a>')
    if nxt:
        parts.append(f'<a href="{page_name(nxt)}">{esc(nxt)} →</a>')
    parts.append("</div></div>")
    return "".join(parts)


def page_name(tkey: str) -> str:
    return f"{tkey[:2]}_{tkey[2:]}.html"


def img_block(fig: str, title: str, caption: str) -> tuple[str, float]:
    """<figure> 한 장 + 가로세로비(칸 나눌 때 쓴다)."""
    src = rel(fig)
    dim = png_size(abspath_of(fig))
    wh = ""
    ar = 2.0
    if dim:
        wh = f' width="{dim[0]}" height="{dim[1]}"'
        ar = dim[0] / max(1, dim[1])
    px = f"{dim[0]}×{dim[1]} px" if dim else "원본"
    return (f'<figure><a href="{esc(src)}" title="원본 크기로 열기">'
            f'<img src="{esc(src)}" alt="{esc(title)}" loading="lazy" decoding="async"{wh}></a>'
            f'<figcaption><span class="zoom">클릭 → 원본 {esc(px)}</span>'
            f'<span class="figtitle">{title}</span><br>{caption}</figcaption></figure>'), ar


def rhythm_bar(c: dict) -> str:
    """리듬 몫 막대 — ⭐세로선은 **그 칸의** 백색잡음 값이다(팔마다 다르다)."""
    v = (c or {}).get("rhythm_share_pct")
    if v is None:
        return '<span class="muted">—</span>'
    w = max(0.0, min(100.0, float(v)))
    nl = null_of(c)
    return ('<span class="bar"><span class="track">'
            f'<span class="fill" style="width:{w:.1f}%"></span>'
            f'<span class="floor" style="left:{nl:.1f}%" title="이 칸의 백색잡음 값 '
            f'{nl:.1f} %"></span></span>'
            f'<span class="v">{v:.1f}</span></span>')


def flags_cell(c: dict) -> str:
    out = []
    if c.get("no_return"):
        out.append('<span class="badge b-crit">✕ 되돌아온 것 없음</span>')
    if c.get("incomplete"):
        miss = max(c.get("n_missing") or 0, c.get("n_zero_samples") or 0)
        out.append(f'<span class="badge b-crit">◐ 덜 참 — {thousands(c["n_poses"] - miss)}'
                   f'/{thousands(c["n_poses"])} 자세</span>')
    if c.get("no_motion"):
        out.append('<span class="badge b-crit">○ 움직이는 것 없음</span>')
    if c.get("tip_ceiling_degenerate"):
        out.append('<span class="badge b-warn">▲ 잣대 퇴화</span>')
    if c.get("band_borrowed_from_0deg"):
        out.append('<span class="badge b-warn">↺ 대역 빌림</span>')
    if c.get("beat_spiky"):
        # ⚠«크다» 와 «혼자 크다» 는 다른 잣대다 — 이름을 갈라 둔다(아래 ⚑ 가 튐 진단이다).
        out.append(f'<span class="badge b-warn" title="|AC| 의 최대÷중앙 = '
                   f'{c.get("spike_ratio", 0):.0f}. 크기만 잰 수다 — 정반사 플래시는 원래 '
                   f'크다.">⚡ 큰 자세 {c.get("spike_ratio", 0):.0f}배</span>')
    # ── ⭐튐 진단(2026-08-16 부터 상시) ──────────────────────────────────────
    if c.get("one_pose_moves_headline"):
        out.append(f'<span class="badge b-crit" title="{esc(c.get("outlier_why_ko") or "")}">'
                   f'⚑ 튐 — 자세 #{c.get("outlier_argmax_pose")} 하나가 헤드라인을 민다</span>')
    elif c.get("one_pose_dominates_within_band"):
        out.append('<span class="badge b-warn" title="자세 하나가 잣대를 끌긴 하는데 움직인 '
                   '폭이 격자 산포 밴드 안이라 읽기는 안 바뀐다.">◱ 자세 하나 쏠림(밴드 안)</span>')
    if c.get("flash_comb_undersampled"):
        out.append('<span class="badge b-warn" title="진짜 날개 플래시인데 한 표본 폭으로 '
                   '찍혔다 — 튐이 아니라 시간 분해능 문제다.">⌗ 덜 찍힌 플래시</span>')
    if c.get("outlier_grade_shaky"):
        cg = c.get("outlier_census_grade")
        out.append('<span class="badge b-warn" title="죄 없는 자세 12 개를 어느 것으로 뽑느냐에 '
                   '등급이 걸린 칸이다 — 문턱에 걸터앉아 있다는 뜻이지 둘 중 하나가 틀렸다는 '
                   '뜻이 아니다.">◈ 경계 — 대조군 추첨에 흔들림'
                   + (f' (census: {esc(cg)})' if cg and cg != c.get("outlier_grade") else "")
                   + '</span>')
    if c.get("isolation_over_noise_null") and not c.get("one_pose_moves_headline"):
        out.append('<span class="badge b-warn" title="가장 큰 자세가 둘째보다 유난히 크다 — '
                   '같은 길이 무작위 잡음 판의 99.9 % 자리보다 고립돼 있다.">◇ 고립도 잡음판 밖</span>')
    return "".join(out) or '<span class="badge b-ok">정상</span>'


#: ⭐튐 진단 원장 — 아틀라스가 쓰는 문턱이 어디서 왔는지를 색인 _meta 가 적어 둔다.
OUT_META = META.get("outlier") or {}


def outlier_note(n_move: int, n_under: int, n_dom: int, li: str) -> str:
    """⭐«튐» 깃발 범례 — 대문에 붙는 절. ⚠손으로 안 적는다(생성기 안에서 원장을 읽는다).

    왜 이 절이 필요한가 — 2026-08-16 에 «−60° 에서 깊이 3 이면 리듬이 86.6 → 32.4 % 로
    무너진다» 는 헤드라인이 자세 8,192 개 중 **하나** 때문이었다. 그 뒤로 진단을 상시로
    돌리는데, 깃발의 **읽는 법**이 같이 붙어 있지 않으면 다음 사람이 «튐 = 버려라» 로
    읽는다. 그것이 두 번째 사고다.
    """
    if not OUT_META:
        return ""
    src = OUT_META.get("threshold_source") or "(없음)"
    band = OUT_META.get("band_source") or "(없음)"
    fen = OUT_META.get("dominance_fence")
    stale = OUT_META.get("thresholds_stale")
    ok = OUT_META.get("thresholds_ok")
    g = OUT_META.get("grades") or {}
    gtxt = " · ".join(f"{k} {v}" for k, v in sorted(g.items(), key=lambda x: -x[1]))
    warn = ""
    if not ok:
        warn = ('<br><b class="crit">⛔ 문턱 원장을 못 읽어 등급을 안 매겼다</b> — '
                + esc(" / ".join(OUT_META.get("notes") or [])))
    elif stale:
        warn = ('<br><b>⚠ 문턱이 낡았다</b> — 문턱은 원장 '
                f'{OUT_META.get("census_ledger_rows")} 행에서 뜬 값인데 지금 원장은 '
                f'{OUT_META.get("ledger_rows_now")} 행이다. '
                '<code>benchmark/outlier_census_0816.py</code> 를 다시 돌려야 선이 맞는다.')
    return f"""
<div class="note crit">
  <b>6. ⭐자세 <u>하나</u>가 헤드라인을 끄는 칸이 {n_move} 개 있다 — 그 칸은 수보다 자세를 먼저 봐라.</b>
  <p>2026-08-16 에 «{MINUS}60{DEG} 에서 반사 깊이 3 이면 리듬 몫이 86.6 → 32.4 % 로 무너진다»는
  판정이 <b>자세 8,192 개 중 하나</b> 때문이었다. 그 자세를 이웃 평균으로 갈아 끼우면 두 판이
  85.5 대 85.2 % 로 같다. 그래서 <b>튐 진단을 모든 칸에 상시로</b> 돌린다.</p>
  <p>재는 법은 이렇다 — 그 칸에서 가장 큰 자세 <b>하나</b>를 이웃 평균으로 갈아 끼우고
  헤드라인 넷(리듬 몫 · 빗살 대비 · 요동 전력 · 상한 위 몫)을 다시 잰다. 그 폭이
  ① 죄 없는 자세 12 개와 둘째로 큰 자세를 같은 방법으로 갈아 끼웠을 때보다
  <b>{f"{fen:.0f}배" if isinstance(fen, (int, float)) else "울타리"}</b> 넘게 크고
  ② 그 앙각의 <b>격자 산포 밴드</b>보다 크면 «튐»이다. 두 문턱 다 원장에서 읽어 온다
  (<code>{esc(src)}</code> · 밴드는 <code>{esc(band)}</code>).{warn}</p>
  <ul class="find">
    <li><span class="badge b-crit">⚑ 튐</span> <b>{n_move} 개</b> — 자세 하나가 헤드라인을
        격자 밴드 <b>밖으로</b> 민다.{f"<ul class='find'>{li}</ul>" if li else ""}</li>
    <li><span class="badge b-warn">◱ 자세 하나 쏠림(밴드 안)</span> <b>{n_dom} 개</b> —
        자세 하나가 잣대를 끌긴 하는데 움직인 폭이 밴드 안이라 <b>읽기는 안 바뀐다</b>.</li>
    <li><span class="badge b-warn">⌗ 덜 찍힌 플래시</span> <b>{n_under} 개</b> —
        ⭐<b>튐이 아니다.</b> 진짜 날개 플래시가 <b>한 표본 폭</b>으로 찍힌 것이다. 에코는
        날개끝 상한으로 대역제한돼 있어 플래시의 최소 폭이 0{DEG} 에서 7.7 표본이어야 하는데
        1 표본이면 참 신호가 표본 간격보다 좁다는 뜻이다 — 고칠 곳은 그 칸이 아니라
        <b>표집(시간 분해능)</b>이다. 그 칸의 «상한 위 몫 · 빗살 대비»를 인용할 때는
        그 단서를 함께 적는다.</li>
    <li><span class="badge b-warn">◇ 고립도 잡음판 밖</span> — 가장 큰 자세가 둘째보다
        유난히 크다(같은 길이 무작위 잡음 판의 99.9 % 자리보다 고립). 왜 그런지를
        설명하는 <b>보조</b> 증거지 판정이 아니다.</li>
    <li><span class="badge b-warn">◈ 경계 — 대조군 추첨에 흔들림</span>
        <b>{OUT_META.get('n_grade_shaky', 0)} 개</b> — 쏠림의 분모가 «죄 없는 자세 12 개를
        갈아 끼웠을 때의 <b>최댓값</b>»이라 <b>어느 12 개를 뽑느냐</b>에 등급이 걸린다.
        중앙값 대조군으로 다시 재서 판정이 갈리는 칸에 이 딱지를 붙였다.
        {(f"감식 원장(<code>outputs/outlier_census_0816.json</code>)과 등급이 갈린 칸이 "
          f"<b>{OUT_META.get('n_disagree_with_census')} 개</b> 있는데, 그 칸에는 감식 원장의 "
          "등급도 함께 적어 두었다 — «둘 중 하나가 틀렸다»가 아니라 «그 칸이 문턱에 "
          "걸터앉아 있다»는 뜻이다.") if OUT_META.get("n_disagree_with_census") else ""}</li>
  </ul>
  <p>⛔<b>깃발이 떴다고 그 칸을 자동으로 버리지 마라.</b> 깃발의 뜻은 «이 수는 자세 하나에
  걸려 있으니 그 자세를 열어 보라»이지 «틀렸다»가 아니다 — 로터가 시선과 딱 맞는 순간의
  <b>진짜 정반사 플래시</b>도 이렇게 보인다. 그래서 «얼마나 큰가»(최대÷중앙)는 등급에 <b>안
  쓰고</b>, «날개가 지나갈 때마다 다시 서나 · 이웃 자세와 이어지나 · 갈아 끼우면 헤드라인이
  움직이나»로만 판정한다. 등급 분포: {esc(gtxt) or "—"}.</p>
  <p class="small muted">잣대 정의는 <code>benchmark/build_md_atlas.py</code> 의
  <code>outlier_probe</code>, 문턱은 <code>benchmark/outlier_census_0816.py</code> 가 원장
  자기 분포의 꼬리에서 뜬 값이다(이 갤러리에 손으로 적은 숫자는 없다). 그 자세의
  <b>경로 수</b>가 이상한지(계산 사건인지)는 샤드를 읽어야 해서 census 원장에만 있다.</p>
</div>"""


def arm_table(arm: str) -> str:
    a = ARM_IDX[arm]
    rows = []
    for el in a["elevations_deg"]:
        c = a["cells"].get(cell_key(float(el)))
        if not c:
            continue
        lvl = c.get("ledger_level_db")
        rows.append(
            "<tr>"
            f'<td class="el">{esc(deg_txt(float(el)))}</td>'
            f'<td class="n">{num(c.get("f_tip_hz"), "{:.0f}")}</td>'
            f'<td>{rhythm_bar(c)}</td>'
            f'<td class="n">{num(c.get("rhythm_null_pct"), "{:.1f}")}</td>'
            f'<td class="n">{num(c.get("above_ceiling_energy_pct"), "{:.1f}")}</td>'
            f'<td class="n">{num(c.get("comb_contrast_db"), "{:+.1f}")}</td>'
            f'<td class="n">{num(c.get("beat_hz"), "{:.1f}")}</td>'
            f'<td class="n">{num(c.get("beat_over_flash"), "{:.3f}")}</td>'
            f'<td class="n">{num(c.get("moving_power_db"), "{:.2f}")}</td>'
            f'<td class="n">{num(c.get("moving_share_pct"), "{:.3g}")}</td>'
            f'<td class="n">{thousands(c["n_poses"]) if c.get("n_poses") else "—"}</td>'
            # ⚠원장은 «메아리 없음» 을 −6000 dB 라는 표시값으로 적는다 — 세기로 읽히지 않게 가린다
            f'<td class="n">'
            + ('<span class="muted" title="측정값이 아니라 «없음» 표식이다">'
               + MINUS + '6000 (표식)</span>'
               if (lvl is not None and float(lvl) <= -5999.0)
               else num(lvl, "{:.2f}")) + "</td>"
            f"<td>{flags_cell(c)}</td></tr>")
    head = ("<tr><th>앙각</th><th>날개끝 상한<br>f_tip [Hz]</th>"
            "<th>리듬 몫 [%]<br><span class=\"muted\">상한 <b>위</b>만 · 선=그 칸의 백색잡음</span></th>"
            "<th>그 칸<br>백색잡음 [%]</th>"
            "<th>상한 위 에너지<br>[%]</th>"
            "<th>빗살 대비 [dB]<br><span class=\"muted\">상한 <b>아래</b></span></th>"
            "<th>박자 [Hz]</th><th>박자÷예측</th>"
            "<th>움직이는 전력<br>[dB]</th><th>움직이는 몫<br>[%]</th>"
            "<th>자세 수</th><th>원장 레벨<br>[dB]</th><th>표시</th></tr>")
    foot = (
        '<p class="small muted">표 읽는 법 — ⭐<b>리듬 몫</b>은 <b>날개끝 상한 «위»만</b> 재는 '
        '수다. 막대 안 세로선은 <b>그 칸의</b> 백색잡음 값이고(팔마다 다르다 — 옆 열에 적었다), '
        '그보다 낮다고 «날개가 없다»는 뜻이 <b>아니다</b>. 그 판단은 <b>빗살 대비</b>와 함께 '
        '한다 — 그것은 상한 <b>아래</b>(날개가 실제로 사는 자리)에서 «정수배 자리 ÷ 그 사이 '
        '자리» 전력비이고 백색잡음이 0 dB 다. <b>상한 위 에너지</b>는 움직이는 힘 중 몇 %가 '
        '상한 위에 있나로, 리듬 몫이 낮은 까닭이 «위가 조용해서»인지 «위가 잡동사니로 '
        '가득 차서»인지를 가른다. <b>박자÷예측</b>이 1.00 이면 예측한 자리에 봉우리가 섰다는 '
        '뜻이고 2.00 이면 두 배 자리다 — ⚡튐 딱지가 붙은 칸의 박자는 회전이 아니라 튄 자세 '
        '몇 개의 간격이다. <b>움직이는 전력</b>과 <b>원장 레벨</b>은 dB 라 <b>같은 팔 안에서만</b> '
        '비교한다. 박자는 <b>전 구간</b>으로 재고 맵 그림은 20~80 ms 창만 그린다.</p>')
    return ('<div class="scroll"><table><thead>' + head + "</thead><tbody>"
            + "".join(rows) + "</tbody></table></div>" + foot)


MAP_CAP = ("가로가 <b>시간</b>, 세로가 <b>도플러 주파수</b>(움직이는 것 때문에 되돌아온 신호의 "
           "주파수가 밀린 양)다. 위줄은 받은 그대로, 아래줄은 <b>가만히 있는 부분(정지 성분)을 뺀</b> 판이다. "
           "흰 점선이 <b>날개끝 상한</b> — 날개가 만들 수 있는 가장 빠른 도플러이고, 그 위에 무엇이 있으면 "
           "날개 말고 다른 것이다. <b>규칙적으로 되풀이되는 밝은 세로 줄무늬</b>가 날개가 시선을 지나갈 때의 "
           "번쩍임이다. ⚠패널마다 <b>자기 최댓값</b>으로 밝기를 맞추므로 패널끼리 밝기는 비교하지 않는다 — "
           "모양만 읽는다.")

# ⚠2026-08-15 정정 — 옛 문구는 이 띠를 «상한 위» 라고 적었다. **틀렸다**: 날개 대역은
#   상한의 0.35~1.0 배, 즉 상한 **아래**의 띠다(`build_md_atlas.modspec_curve`).
#   같은 페이지의 «리듬 몫은 상한 위» 와 헷갈리면 두 그림이 같은 자리를 본다고 오해한다.
BAND_CAP = ("날개 대역 — 날개끝 상한의 <b>0.35~1.0 배</b> 띠(상한 <b>아래</b>다) — 의 힘이 "
            "시간에 따라 오르내리는 <b>리듬</b>을 주파수로 편 그림이다. "
            "가로가 리듬의 빠르기[Hz], 세로가 그 세기다. <b>점선이 예측 박자의 정수배</b> — "
            "점선 자리에 뾰족한 봉우리가 서면 날개가 그 박자로 규칙적으로 지나간다는 뜻이고, "
            "봉우리 없이 뭉개져 있으면 그냥 잡음이다. 왼쪽은 넓게, 오른쪽은 첫 봉우리 부근을 확대한 판이다. "
            "색은 앙각(위에서 내려다본 각)이다.")


def arm_section(arm: str) -> str:
    a = ARM_IDX[arm]
    figs = a["figures"]
    fmap, ar1 = img_block(figs["map"], "① 마이크로도플러 맵",
                          MAP_CAP + f" 이 팔의 날개끝 상한은 0{DEG} 에서 "
                                    f"<b>{a['f_tip0_hz']:.0f} Hz</b> 다.")
    fband, ar2 = img_block(figs["band"], "② 블레이드 대역 에너지",
                           BAND_CAP + f" 이 팔의 예측 박자는 <b>{a['f_flash_hz']:g} Hz</b> 다.")
    cols = f"{ar1:.2f}fr {ar2:.2f}fr"

    cp = counterpart(arm)
    cp_line = ""
    if cp:
        d = pair_delta(arm, cp)
        extra = ""
        if d:
            n, mx, mean, skip = d
            extra = (f" 같은 앙각 {n} 칸에서 리듬 몫 차이는 최대 {mx:.1f} %p(평균 {mean:+.1f} %p) — "
                     + verdict(mx, slug=ARM_IDX[arm]["topic"]) + "."
                     + (f" 뺀 칸 {skip} 개(잣대 퇴화·수를 낼 자격 없음)." if skip else ""))
        else:
            # ⚠2026-08-15 결함 — 여기서 아무 말도 안 붙여 문장이 «…짝 팔 <이름>» 에서 끊겼다.
            extra = (" 다만 <b>비교할 수 있는 칸이 없다</b> — 두 팔이 함께 가진 앙각의 칸이 "
                     "«되돌아온 것 없음»·«자세가 덜 참»·«잣대 퇴화» 중 하나라 셈에서 뺐다.")
        cp_line = (f'<p class="facts">↔ <b>한 축만 다른 짝 팔</b> '
                   f'<a href="{page_name(ARM_TOPIC[cp])}#arm-{esc(anchor(cp))}">'
                   f'<code>{esc(cp)}</code></a>{extra}</p>')

    return (f'<section class="arm" id="arm-{esc(anchor(arm))}">'
            f'<h3 class="name">{esc(arm)}</h3>'
            f'<p class="facts">{" · ".join(arm_facts(arm))}</p>'
            f'{cp_line}'
            f'<div class="figrow" style="--cols:{cols}">{fmap}{fband}</div>'
            f'{arm_table(arm)}'
            "</section>")


def anchor(arm: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "-", arm)


def compare_caption(path: str) -> tuple[str, str]:
    b = os.path.basename(path)
    if "000-overview-rhythm" in b:
        return ("한눈에 보는 리듬 몫 지도",
                "이 주제의 <b>팔 × 앙각</b> 리듬 몫[%] 표를 색으로 칠한 판이다. 개별 그림을 열기 전에 "
                "<b>어디를 볼지 정하는</b> 데 쓴다. <code>—</code> 는 원장에 그 칸이 없다는 뜻이고, "
                "<b>빗금 친 칸은 색눈금에 올리면 안 되는 칸</b>이다 — "
                f"{MINUS}90{DEG} 열(잣대 퇴화) · ◐ 자세가 덜 참 · ○ 안 움직임 · ∅ 에코 없음. "
                "⚠이 지도는 <b>상한 위</b>만 보는 잣대라 낮은 값이 «날개가 없다»는 뜻이 아니다.")
    if "01-compare-tile" in b:
        el = b.split("01-compare-tile")[1].split("-p")[0]
        try:
            eltxt = deg_txt(float(el))
        except ValueError:
            eltxt = el
        return (f"{eltxt} 한 각도 타일",
                f"앙각이 <b>{eltxt} 하나뿐인</b> 팔들을 한 장에 늘어놓은 판이다. 전부 정지 성분을 뺀 "
                "그림이라 «움직이는 것»만 남았다. 패널 제목은 그 묶음에서 <b>갈리는 토막만</b> 남긴 짧은 이름이다.")
    if "02-compare-stack" in b:
        return ("팔 세로 · 앙각 가로 스택",
                "팔을 세로로 쌓고 앙각을 가로로 편 판이다. <b>같은 앙각 열을 위아래로 훑으면</b> 팔 사이 "
                "차이가 보인다. 팔이 많으면 여러 쪽(<code>p1</code> · <code>p2</code>)으로 나뉜다.")
    return ("비교판", "이 주제의 팔을 한 장에 모은 판이다.")


# ═══════════════════════════════════════════════════════════════════════════ #
#  8. 대문
# ═══════════════════════════════════════════════════════════════════════════ #
def thumb_for(tinfo: dict) -> str:
    """카드 썸네일 — 요약판이 있으면 그것, 없으면 그 주제에서 가장 가벼운 그림."""
    for p in tinfo["compare"]:
        if "000-overview-rhythm" in os.path.basename(p):
            return p
    cands = list(tinfo["compare"])
    for a in tinfo["arms"].values():
        cands += [a["figures"]["band"], a["figures"]["map"]]
    cands = [c for c in cands if os.path.exists(abspath_of(c))]
    if not cands:
        return next(iter(tinfo["arms"].values()))["figures"]["map"]
    return min(cands, key=lambda c: os.path.getsize(abspath_of(c)))


def n_figs(tinfo: dict) -> int:
    return len(tinfo["compare"]) + 2 * len(tinfo["arms"])


def n_cells(tinfo: dict) -> int:
    return sum(len(a["cells"]) for a in tinfo["arms"].values())


def build_index() -> str:
    total_cells = sum(n_cells(t) for _, t in TOPICS)
    deg_cells = sum(1 for a in ARM_IDX.values() for c in a["cells"].values()
                    if c.get("tip_ceiling_degenerate"))
    nr_cells = sum(1 for a in ARM_IDX.values() for c in a["cells"].values()
                   if c.get("no_return"))
    inc_cells = sum(1 for a in ARM_IDX.values() for c in a["cells"].values()
                    if c.get("incomplete"))
    nm_cells = sum(1 for a in ARM_IDX.values() for c in a["cells"].values()
                   if c.get("no_motion"))
    sp_cells = sum(1 for a in ARM_IDX.values() for c in a["cells"].values()
                   if c.get("beat_spiky"))
    ou_cells = sum(1 for a in ARM_IDX.values() for c in a["cells"].values()
                   if c.get("one_pose_moves_headline"))
    us_cells = sum(1 for a in ARM_IDX.values() for c in a["cells"].values()
                   if c.get("flash_comb_undersampled"))
    dm_cells = sum(1 for a in ARM_IDX.values() for c in a["cells"].values()
                   if c.get("one_pose_dominates_within_band"))
    ou_list = "".join(
        f'<li><code>{esc(nm)}</code> {deg_txt(float(k))} — {esc(c.get("outlier_why_ko") or "")}</li>'
        for nm, a in sorted(ARM_IDX.items()) for k, c in sorted(a["cells"].items())
        if c.get("one_pose_moves_headline"))
    ff_rows = "".join(
        f'<tr><td class="el">{esc(r["label"])}</td><td class="n">{r["D"]:.2f} m</td>'
        f'<td class="n"><b>{r["r_ff"]:.2f} m</b></td>'
        f'<td>{" · ".join(f"{x:g} m" for x in r["ranges"])}</td>'
        f'<td>{r["verdict"]}</td></tr>' for r in FARFIELD)
    by_rng: dict[float, list[str]] = {}
    for arm in sorted(ARM_IDX):
        r = arm_row(arm).get("range_m")
        by_rng.setdefault(float(r) if r is not None else float("nan"), []).append(arm)

    # 읽는 법 예시 그림 — 첫 주제의 첫 팔
    ex_arm = sorted(TOPICS[0][1]["arms"])[0]
    ex = ARM_IDX[ex_arm]
    ex_map, ar1 = img_block(ex["figures"]["map"], "맵은 이렇게 생겼다",
                            "예시 · <code>" + esc(ex_arm) + "</code> — " + MAP_CAP)
    ex_band, ar2 = img_block(ex["figures"]["band"], "대역 에너지는 이렇게 생겼다",
                             "예시 · <code>" + esc(ex_arm) + "</code> — " + BAND_CAP)

    cards = []
    for tkey, tinfo in TOPICS:
        slug = tkey[2:]
        th = thumb_for(tinfo)
        cards.append(
            f'<a class="card" href="{page_name(tkey)}">'
            f'<div class="thumb"><img src="{esc(rel(th))}" alt="{esc(tkey)} 대표 그림" '
            f'loading="lazy" decoding="async"></div>'
            f'<div class="body"><span class="tag">{esc(tkey[:2])} · {esc(tinfo["label_en"])}</span>'
            f'<div class="q">{esc(TOPIC_Q.get(slug, slug))}</div>'
            f'<div class="small muted">{esc(tinfo["label_ko"])}</div>'
            f'<div class="n">그림 {n_figs(tinfo)} 장 · 팔 {len(tinfo["arms"])} 개 · '
            f'칸 {n_cells(tinfo)} 개</div></div></a>')

    tok_rows = []
    for tok, mean, dflt, pred in TOKENS:
        cnt = sum(1 for a in ALL_ARMS if pred(a))
        tok_rows.append(f"<tr><td>{tok}</td><td>{mean}</td><td>{esc(dflt)}</td>"
                        f'<td class="n">{cnt}</td></tr>')

    rng_rows = "".join(
        f'<tr><td class="el">{r:g} m</td><td class="n">{len(v)}</td>'
        f'<td>{"기준 거리 — 나머지 팔 전부" if abs(r - RANGE_PRIMARY) < 1e-9 else " · ".join(f"<code>{esc(x)}</code>" for x in v)}</td></tr>'
        for r, v in sorted(by_rng.items()))

    body = f"""
{stale_banner()}
<div class="note" style="margin-top:22px">
  <b>⭐먼저 볼 것 — <a href="{SINCE_DECK}">8/18 덱 이후에 한 실험 (한 장 색인)</a></b><br>
  <span class="small">덱에 실린 데까지가 기준선이고, 그 뒤 <b>실험 30 건</b>이 무엇을 물어 무엇으로 답했는지를
  «물음 / 판정 / 근거 원장 / 볼 곳» 네 칸으로 한 장에 모았다. 이 갤러리의 어느 그림이
  어느 실험의 답인지도 거기서 이어진다.</span>
</div>

<header class="top">
  <div class="kicker">micro-doppler atlas</div>
  <h1>드론 마이크로도플러 아틀라스 — 그림으로 넘겨 보기</h1>
  <p class="lede">실험 원장에 쌓인 <b>팔 {META['n_arms']} 개 · 칸 {total_cells} 개</b>를 두 종류의 그림
  — <b>마이크로도플러 맵</b>과 <b>블레이드 대역 에너지</b> — 으로 전부 구워 놓은 갤러리다.
  주제 카드를 눌러 들어가면 팔마다 그림 두 장과 앙각별 수치 표가 나란히 있다.
  그림을 클릭하면 원본 크기로 열린다.</p>
  <div class="stats">
    <div class="stat"><b>{len(TOPICS)}</b><span>주제</span></div>
    <div class="stat"><b>{META['n_arms']}</b><span>팔(조건 하나)</span></div>
    <div class="stat"><b>{total_cells}</b><span>칸(팔 × 앙각)</span></div>
    <div class="stat"><b>{META['n_figures']}</b><span>그림</span></div>
    <div class="stat"><b>{META['fc_hz'] / 1e9:g} GHz</b><span>주파수</span></div>
    <div class="stat"><b>{META['prf_hz'] / 1000:g} kHz</b><span>표본율(PRF)</span></div>
  </div>
</header>

<h2 id="howto">먼저 — 이 그림들을 어떻게 읽나</h2>
<p class="lede">두 종류뿐이다. 하나는 <b>시간에 따른 도플러 그림(맵)</b>, 다른 하나는
<b>그 도플러 대역의 힘이 뛰는 리듬(대역 에너지)</b>이다. 아래 예시 두 장이 나머지 전부와 같은 형식이다.</p>
<div class="figrow" style="--cols:{ar1:.2f}fr {ar2:.2f}fr">{ex_map}{ex_band}</div>

<div class="grid2">
  <div class="box">
    <h3>용어 — 처음 나오는 말</h3>
    <ul class="find">
      <li><b>도플러</b> — 움직이는 것에 맞고 되돌아온 신호는 주파수가 밀린다. 그 밀린 양[Hz]이 도플러다.
          빠를수록 크다.</li>
      <li><b>박자</b>(f_flash) — 날개가 시선을 지나가는 횟수[Hz] = 날개 수 × 회전수. 기체마다 다르다.</li>
      <li><b>날개끝 상한</b>(f_tip) — 날개 <b>끝</b>이 만들 수 있는 가장 큰 도플러. 위에서 내려다볼수록
          작아지고, 바로 아래({MINUS}90{DEG})에서는 0 이 된다.</li>
      <li><b>리듬 몫</b>[%] — <b>날개끝 상한 «위»에</b> 남은 힘 중 <b>박자의 정수배(±8 Hz)</b>에
          붙은 몫. ⛔<b>이 수는 상한 위만 본다.</b> 날개 무늬가 상한 «아래»에 멀쩡히 있어도 0 % 가
          나올 수 있다 — 0 % 는 «리듬이 없다»가 아니라 <b>«이 자리에선 못 읽는다»</b>이다.
          백색잡음 값은 팔마다 다르고(표에 칸마다 적었다), 100 은 실제 자료에서 도달 불가다.</li>
      <li><b>빗살 대비</b>[dB] — ⭐리듬 몫의 <b>짝</b>. 상한 <b>아래</b>(날개가 실제로 사는 자리)에서
          «박자의 정수배 자리 ÷ 그 사이 자리» 전력비다. 백색잡음이 0 dB. 리듬 몫이 0 인데 이 수가
          +40 dB 면 날개는 있고 잣대가 못 읽은 것이다. 두 수가 <b>함께</b> 널일 때만 «안 보인다»고
          말한다.</li>
      <li><b>정지 성분 제거</b> — 가만히 있는 부분(시간 평균)을 빼는 것. {esc(META['level_rule_ko'].lstrip('⭐'))}</li>
      <li><b>앙각</b> — 표적을 얼마나 위에서 내려다보는가. 0{DEG} 가 옆에서, {MINUS}90{DEG} 가 바로 위에서다.</li>
      <li><b>팔</b> — 조건 하나를 가리키는 말(예: 엔진 · 거리 · 스위치 조합 하나). 팔 이름이 곧 조건이다.</li>
    </ul>
  </div>
  <div class="box">
    <h3>그림을 만든 규약</h3>
    <ul class="find">
      <li>{esc(META['stft_ko'])}</li>
      <li>{esc(META['map_window_ko'])}</li>
      <li>{esc(META['airframe_rule_ko'].lstrip('⚠'))}</li>
      <li>{esc(META['nadir_rule_ko'].lstrip('⚠'))}</li>
      <li>기본값 — 주파수 {META['fc_hz'] / 1e9:g} GHz · 표본율 {META['prf_hz']:g} Hz ·
          기본 기체 {esc(META['drone_default'])} · 기준 거리 {META['range_m_primary']:g} m.</li>
    </ul>
  </div>
</div>

<h2>주제 {len(TOPICS)} 개</h2>
<div class="cards">
{"".join(cards)}
</div>

<h2>팔 이름 읽는 법</h2>
<p class="lede">팔 이름은 <b>조건을 그대로 적은 것</b>이라 길다.
예: <code>sionna_p4000000000_phys_r15_n8192_d1</code> = PathSolver · 광선 40 억 발 · 물리 전부 켬 ·
거리 15 m · 자세 8,192 개 · 반사 깊이 1. 토막마다 뜻은 이렇다.</p>
<div class="scroll"><table class="tok"><thead>
<tr><th>토막</th><th>뜻</th><th>없으면(기본값)</th><th class="n">쓰인 팔</th></tr>
</thead><tbody>
{"".join(tok_rows)}
</tbody></table></div>

<h2>⚠ 읽을 때 주의</h2>
<div class="note warn">
  <b>1. 바로 아래({MINUS}90{DEG})는 잣대가 망가진다.</b>
  날개가 도는 면이 시선과 수직이라 날개끝 상한이 0 Hz 다. 상한이 0 이면 «상한 <b>위</b>»가 전 대역이 되어
  리듬 몫이 «날개가 만들 수 없는 자리에 무엇이 남았나»를 재는 잣대이기를 그만둔다.
  이 아틀라스에서 그런 칸은 <b>{deg_cells} 개</b>이고 표에 <span class="badge b-warn">▲ 잣대 퇴화</span> 로 적었다.
  대역 그림도 {MINUS}90{DEG} 는 0{DEG} 의 대역을 빌려 그린다(<span class="badge b-warn">↺ 대역 빌림</span>).
  ⭐주제 요약 지도에서도 그 열은 <b>색을 안 칠하고 빗금</b>으로 덮는다 — 같은 0~100 색눈금에 올려 두면
  한눈에 «직하방이 제일 깨끗하다»로 읽히기 때문이다(실제로 {MINUS}90{DEG} 열의 값이 가장 높다).
</div>
<div class="note crit">
  <b>2. 엔진끼리 «절대 세기»를 비교하지 마라.</b>
  우리 커널과 PathSolver 는 <b>눈금이 다르다</b>. 같은 표적을 같은 자리에서 재도 «−70 dB»와 «−94 dB»는
  세기의 비교가 아니다 — 광선 예산 · 격자 · 정규화가 엔진마다 다르게 들어간 수라, 두 팔의 dB 를 빼는 순간
  그 차이는 물리가 아니라 구현의 차이가 된다.
  그래서 이 갤러리는 <b>모양</b>과 <b>눈금에 무관한 수</b>(리듬 몫[%] · 빗살 대비[dB] · 박자[Hz] ·
  박자÷예측)로만 말한다. ⚠그 대가로 <b>거리를 읽을 수 없다</b> — 모양 잣대는 에코 전체가 공통 인수로
  작아지는 것에 둔감하다(06range 참고).
  같은 팔 안에서 앙각끼리 dB 를 비교하는 것은 된다(같은 눈금이다).
</div>
<div class="note warn">
  <b>3. 격자 흔들림 밴드 안이면 판정 불가.</b>
  표면 격자를 λ/12 에서 λ/24 로 조이기만 해도 잣대가 움직인다. 그 폭이
  <b>리듬 몫 {RHY_BAND:.1f} %p · 움직이는 전력 {AC_BAND:.2f} dB</b> 다(<code>{esc(BAND_SRC)}</code>,
  앙각 네 점에서 잰 최댓값). 두 팔의 리듬 몫 차이가 {RHY_BAND:.1f} %p 안이면 «차이가 있다»고 말할 수 없다.
  ⚠<b>이 밴드는 우리 커널의 격자 축(λ/12 ↔ λ/24)에서 나온 수다 — PathSolver 에는 그 축이 아예 없다.</b>
  PathSolver 팔끼리의 차이에 이 밴드를 대는 것은 <b>빌려 쓰는</b> 것이고, 그 사실을 알고 써야 한다.
</div>
<div class="note warn">
  <b>4. 거리가 다른 팔이 섞여 있고, 근접장은 기체마다 다른 자리에서 시작한다.</b>
  이름에 <code>r</code> 토막이 없는 팔은 옛 기본 10 m 다. 나란히 놓을 때는 거리를 함께 적는다
  (비교판 그림의 줄 라벨에 거리를 박아 두었다).
  ⭐원거리장 경계는 2D²/λ 라 <b>표적이 커지면 멀어진다</b> — 기본 기체({esc(META.get('drone_default',''))})
  는 <b>14.08 m</b> 이지만 기체마다 다르다. 아래 표의 «근접장» 칸이 그 판정이다.
  근접장에서는 파면이 표적 위에서 휘므로 그 팔의 차이를 «엔진 차이»로 읽으면 안 된다.
  <div class="scroll" style="margin-top:10px"><table><thead>
  <tr><th>거리</th><th class="n">팔 수</th><th style="text-align:left">어느 팔인가</th></tr></thead>
  <tbody>{rng_rows}</tbody></table></div>
  <div class="scroll" style="margin-top:10px"><table><thead>
  <tr><th>기체</th><th class="n">표적 크기 D</th><th class="n">원거리장 경계 2D²/λ</th>
  <th style="text-align:left">이 원장의 거리</th><th style="text-align:left">판정</th></tr></thead>
  <tbody>{ff_rows}</tbody></table></div>
</div>
<div class="note crit">
  <b>5. 수를 낼 자격이 없는 칸이 {nr_cells + inc_cells + nm_cells} 개 있다 — 그 칸에는 값이 없다.</b>
  <ul class="find">
    <li><b>되돌아온 게 없는 칸 {nr_cells} 개</b> — 원장의 에코가 통째로 0 이다
        (<span class="badge b-crit">✕ 되돌아온 것 없음</span>). 원장 레벨의 {MINUS}6000 dB 는
        잰 세기가 아니라 «없음» 표식이다.</li>
    <li>⭐<b>아직 덜 찬 칸 {inc_cells} 개</b> — 자세가 절반만 들어왔다
        (<span class="badge b-crit">◐ 덜 참</span>). 빈 자세 자리의 0 채움이 스펙트럼을
        PRF/2 · PRF/4 에 복제해 «상한 위»를 삼키므로 리듬 몫이 0 % 로 주저앉는다.
        <b>물리가 아니라 결측 자국</b>이라 잣대를 내지 않는다 — 원장을 다시 병합해야 한다.</li>
    <li><b>움직이는 것이 없는 칸 {nm_cells} 개</b> — AC/DC 가 반올림 바닥 아래다
        (<span class="badge b-crit">○ 움직이는 것 없음</span>). 거기서 뽑은 «박자»는
        마지막 자리 한 칸을 흔든 자리라 재현되지 않는다.</li>
    <li><b>자세 몇 개가 유난히 큰 칸 {sp_cells} 개</b> — <span class="badge b-warn">⚡ 큰 자세</span>
        딱지가 붙은 칸의 박자는 회전이 아니라 <b>튄 자세들의 간격</b>일 수 있다. 맵도 그 자세
        하나가 색역을 다 먹어 나머지가 바닥색으로 깔린다. ⚠이 딱지는 <b>크기만</b> 잰 수다 —
        «혼자 큰가»는 아래 6 번의 <span class="badge b-crit">⚑ 튐</span> 이 잰다.</li>
  </ul>
</div>
{outlier_note(ou_cells, us_cells, dm_cells, ou_list)}
<div class="note warn">
  <b>7. 아직 못 고친 것 — 알고 쓰라고 적어 둔다.</b>
  <ul class="find">
    <li><b>덜 찬 칸 {inc_cells} 개의 참값</b> — 원장을 다시 병합해야 나온다. 이 갤러리는 원장을
        읽기만 하므로 여기서는 못 고친다. 세 칸 중 둘은 자세가 <b>뭉텅이로</b> 빠져 있어
        «0 을 걷어내고 다시 재는» 길도 없다(균일 표본이 아니다).</li>
    <li><b>주제 분류는 아직 이름 토막으로 거리를 본다</b> — 그래서 <code>_r</code> 토막이 없는
        10 m 옛 팔이 «기본 엔진» 주제에 남아 있다. 원장 <code>range_m</code> 으로 바꾸면 그 팔들이
        거리 주제로 옮겨가 그림 파일 이름이 전부 바뀌므로, 주제를 다시 짤 때 함께 고친다.
        그 사이의 안전장치가 위의 거리 표와 그림 속 거리 라벨이다.</li>
    <li><b>맵은 패널마다 자기 최댓값으로 밝기를 맞춘다</b> — 그래서 <b>거리와 세기를 그림에서
        읽을 수 없다</b>. 공통 눈금을 쓰면 눈금이 다른 두 엔진을 한 색역에 올리는 더 큰 거짓이
        되므로 그대로 두었다.</li>
    <li><b>리듬 몫의 창 반폭은 8 Hz 고정</b> — 이미 인용된 수와 갈리지 않게 정의를 유지했다.
        그 대가로 높은 배음일수록 창 밖으로 새어 <b>100 은 도달 불가</b>다.</li>
    <li><b>박자와 맵은 다른 구간에서 잰 수다</b> — 박자는 전 구간(0.42 s), 맵은 20~80 ms 창이다.</li>
  </ul>
</div>
"""
    return page("드론 마이크로도플러 아틀라스", nav_bar("index", since_deck=True), body)


# ═══════════════════════════════════════════════════════════════════════════ #
#  9. 주제 페이지
# ═══════════════════════════════════════════════════════════════════════════ #
#: 주제 페이지에 덧붙이는 절 — 팔 목록 위, 요약 그림 아래에 들어간다.
#  ⚠팔 하나로는 안 되는 이야기(축 하나를 통째로 읽은 판정)를 여기에 싣는다.
DEPTH_LEDGER = os.path.join(ROOT, "outputs", "depth_axis_verdict_0816.json")


def _depth_numbers() -> dict | None:
    """깊이 축 판정 원장에서 인용할 수를 **그때그때 계산한다**(손으로 안 적는다)."""
    if not os.path.exists(DEPTH_LEDGER):
        return None
    d = json.load(open(DEPTH_LEDGER, encoding="utf-8"))
    ps = d["pairs"]

    def hl(p, k):
        return p["trim"][f"k{p['trim_headline_k']}"][k]

    std = [p for p in ps if p["in_standard_frame"]]
    diff_on = [p for p in ps if p["switches"]["D"] and p["depths"] == [1, 3]]
    # 빗살 대비는 정면(0°)만 그 앙각 밴드 안에서 크게 움직인다 — 빗각·거리만 따로 센다.
    obl = [p for p in std if p["el_deg"] != 0.0
           and hl(p, "d_comb_contrast_db") is not None]
    lv = [hl(p, "d_moving_power_db") for p in diff_on]
    forensic = d["outlier_forensics"]["el60_case"]
    return {
        "n_pairs": len(ps),
        "n13": sum(1 for p in ps if p["depths"] == [1, 3]),
        "n12": sum(1 for p in ps if p["depths"] == [1, 2]),
        "n_std": len(std),
        "std_rhy": max(abs(hl(p, "d_rhythm_pp")) for p in std),
        "std_comb": max(abs(hl(p, "d_comb_contrast_db")) for p in obl),
        "n_obl": len(obl),
        "lv_lo": min(lv), "lv_hi": max(lv),
        "band30": d["null_bands"]["grid_dispersion_ac_db_by_el"]["-30.0"],
        "n_moves": sum(1 for p in ps if p["moves_the_reading"]),
        # ⚠«밴드 밖» 은 두 갈래다 — 실제로 큰 것과, 그 앙각 밴드가 극도로 좁아 밖으로 찍힌 것.
        "n_level_real": sum(1 for p in ps if p["level_outside_band"]
                            and abs(hl(p, "d_moving_power_db")) >= 0.5),
        "n_level_thin": sum(1 for p in ps if p["level_outside_band"]
                            and abs(hl(p, "d_moving_power_db")) < 0.5),
        "n_inside": sum(1 for p in ps if not p["level_outside_band"]),
        # ⚠«경로가 늘 수 있는 짝»만 센다 — 확산 끈 칸은 두 깊이 모두 경로 8 개라 늘 자리가 없다.
        "npaths_lo": d["answers"]["a"]["npaths_ratio_where_paths_grow"]["min"],
        "npaths_hi": d["answers"]["a"]["npaths_ratio_where_paths_grow"]["max"],
        "npaths_n": d["answers"]["a"]["npaths_ratio_where_paths_grow"]["n"],
        "pose": forensic.get("argmax_pose", 3399),
        "n_poses": max(p["n_poses"] for p in ps),
        "ladder": d["bounce_ladder"]["third_over_second"],
    }


def topic_extra(slug: str) -> str:
    """주제 페이지의 덧붙임 절. 지금은 «switch» 하나뿐이다."""
    if slug != "switch":
        return ""
    n = _depth_numbers()
    if n is None:
        return ""
    f1, _ = img_block(
        "outputs/figures/depth_axis_0816.png",
        "깊이 짝 22 개 전부 — 각자 자기 밴드에 대고",
        "왼쪽 세 열이 잣대 셋(요동 절대전력 · 리듬 몫 · 빗살 대비)이고 <b>회색 띠가 그 줄의 "
        "격자 산포 밴드</b>다. <b>띠 안이면 판정 불가</b>이고, 띠가 판보다 넓으면 그 줄은 "
        "판 전체가 회색이 된다. ⭐<b>띠의 폭은 앙각마다 다르다</b> — 왼쪽 아래 판이 그 폭이다"
        f"(0° 3.86 dB ↔ −60° 0.02 dB). 오른쪽 열은 깊이 3 이 실제로 더 찾은 경로 수다 — "
        f"경로가 늘 수 있는 짝 {n['npaths_n']} 개에서 "
        f"{n['npaths_lo']:.3f}~{n['npaths_hi']:.3f} 배이고 줄어든 짝은 없다"
        "(확산 끈 칸은 두 깊이 모두 경로 8 개라 늘 자리가 없어 <code>8→8</code> 로 적힌다).")
    f2, _ = img_block(
        "outputs/figures/depth_axis_maps_0816.png",
        "같은 칸 · 두 깊이 — 맵으로 보면",
        "표준 프레임 팔(PS 다 끔 · 확산만)의 깊이 1(위)과 깊이 3(아래)을 나란히 놓은 것이다. "
        "<b>무늬가 같다</b>는 것이 위 그림의 «판독이 안 바뀐다»를 눈으로 확인해 준다. "
        "⚠맵은 <b>패널마다 자기 최댓값</b>으로 밝기를 맞추므로 <b>패널 사이 절대 레벨은 "
        "이 그림 밖</b>이다 — 레벨 물음은 위 그림이 답한다. "
        "직하방(−90°)은 <b>뺐다</b> — 그 칸은 날개끝 상한이 0 Hz 라 맵의 세로 눈금이 "
        "무너진다(원장에서도 판정에 안 실은 칸이다).")

    return f"""
<h2 id="depth">반사 깊이 축 — 깊이 1 과 깊이 3 이 같은 것을 읽나</h2>
<p class="lede">이 주제의 팔 목록에는 <b>깊이 3</b> 팔이 여럿 있다
(<code>…_d3</code> · <code>onlydepth3</code>). 그 팔들은 <b>같은 조건 · 깊이 1</b> 팔과 짝을
이루는데, 저장된 칸을 전수 조사해 <b>짝 {n['n_pairs']} 개</b>(깊이 1↔3 {n['n13']} · 1↔2 {n['n12']})를
나란히 읽은 판정이 <b>08-16</b> 에 나왔다.
8/18 덱 30 장 «Future work» <b>1 번</b>이 바로 이 축이다.</p>

<div class="note crit">
  <b>⭐판정 — «우리 규약(깊이 1)에 대해서는 닫힌다. 축 전체로는 아직 안 닫힌다.»</b>
  <ul class="find">
    <li><b>닫힌 것</b> — 표준 프레임이 싣는 두 팔(PS 다 끔 · PS 굴절만)에서 깊이 1↔3 은
      <b>판독이 같다</b>. 짝 {n['n_std']} 개 전부 리듬 몫 차 <b>≤{n['std_rhy']:.2f} %p</b> 이고,
      빗살 대비 차는 빗각·거리 {n['n_obl']} 칸에서 <b>≤{n['std_comb']:.2f} dB</b> 다.
      앙각 넷(0 · −30 · −60 · −90°)과 거리 셋(15 · 30 · 120 m)을 덮는다.
      ⇒ <b>큐에서 깊이 3 을 표준 팔에 다시 태울 이유가 없다.</b></li>
    <li><b>안 닫힌 것</b> — <b>회절을 켠 조합</b>에서는 깊이 3 이 요동 절대전력을
      <b>+{n['lv_lo']:.2f}~+{n['lv_hi']:.2f} dB</b> 올린다(−30° 격자 밴드 {n['band30']:.2f} dB 의
      4~6 배이고 튄 자세를 빼도 그대로다). 그 팔의 <b>절대 레벨 인용에는 «깊이 1 한정»
      꼬리표</b>가 필요하다. «깊이는 죽은 축»이라고는 쓰면 안 된다.</li>
    <li><b>얹힌 항의 정체는 회절 스위치 하나가 가른다</b> — 회절을 끄면 깊이가 얹는 항이
      <b>날개 박자를 갖고</b>(리듬 몫 52~85 %) 원 신호보다 16~23 dB 아래다 = 진짜 다중 반사
      표적 에코. 회절을 켜면 1.4~4.3 dB 아래로 크지만 <b>백색</b>이다(11~12 % = 널).
      ⇒ «작은 표적엔 다중 경로가 안 생긴다»는 <b>틀렸다</b> — 생기고, 다만 우리가 쓰는
      팔에서 그것은 −16~−23 dB 짜리 곁가지라 판독을 못 바꾼다.</li>
    <li>⛔<b>철회</b> — 08-15 판의 «−60° 에서 깊이 3 이 리듬을 무너뜨린다»(86.6 → 32.4 %)는
      <b>자세 {thousands(n['n_poses'])} 개 중 하나</b>(#{n['pose']}) 때문이었다. 그 자세만 빼면
      두 판이 <b>85.5 ↔ 85.2 %</b> 로 일치한다.
      <code>outputs/switch_factorial.json</code> 의 <code>B_failures</code> 첫 줄
      (<code>R0D0E0F1</code> · el −60 · 12.74 dB · −54.25 %p)은 <b>인용하면 안 된다</b>.</li>
  </ul>
  <p class="small muted">밴드 안이면 «안 바뀐다»가 아니라 <b>«판정 불가»</b>로 적는다.
  짝 {n['n_pairs']} 개를 그렇게 채점하면 — <b>판독을 바꾼 짝 {n['n_moves']} 개</b> ·
  레벨이 실제로 움직인 짝 {n['n_level_real']} 개(전부 회절 켠 조합) ·
  밴드가 극도로 좁아 밖으로 찍혔을 뿐인 짝 {n['n_level_thin']} 개(차이가 0.5 dB 미만) ·
  밴드 안 {n['n_inside']} 개다.</p>
</div>

<div class="figrow" style="--cols:1fr">{f1}</div>
<div class="figrow" style="--cols:1fr">{f2}</div>

<div class="note warn">
  <b>⚠ 이 판정이 기대고 있는 것 — 정직하게</b>
  <ul class="find">
    <li>밴드는 <b>우리 커널(SBR+PO)의 격자 축</b>에서 잰 것을 <b>빌려 쓴 것</b>이다.
      여기 짝은 전부 PathSolver 팔이고 <b>PathSolver 자신의 깊이-3 산포는 안 잰 값</b>이다.
      그래서 밴드에 안 기대는 잣대(얹힌 항의 리듬 몫 대 <b>백색 널</b> — 널은 칸마다 정확히
      셀 수 있다)를 헤드라인으로 썼다.</li>
    <li>회절 켠 조합의 <b>+2 dB 가 물리인지 경로 표집의 부산물인지 못 가른다</b>.
      얹힌 항이 백색이라는 것과 <b>튕김 사다리가 안 줄어든다</b>는 것
      (세 번째 튕김이 두 번째의 <b>{n['ladder']:.1f} 배</b>를 더한다) 두 단서는 표집 쪽을
      가리키지만, 깊이 3 에서 <b>광선 사다리도 시드 복제도 안 돌려 봤다</b>.</li>
    <li>깊이 3 칸이 <b>없는 자리</b> — 앙각 −15 / −45 / −75° · 거리 60 / 240 / 480 m ·
      기체 <code>mini5pro</code> · <code>s1000plus</code> · 방위 15~90°.
      거리 축 깊이 짝은 «PS 다 끔 · −30°» 한 줄뿐이다.</li>
    <li>−60° 밴드 <b>0.02 dB</b> 는 극도로 좁아 0.06 dB 짜리 차이도 «밖»으로 찍힌다.
      그 폭에 <b>물리적 의미를 붙이면 안 된다</b>. 정면 0° 와 직하방 −90° 는 원장 깃발이
      달린 칸이라(익사 · 상한 퇴화) 판정에 안 실었다.</li>
  </ul>
  <p class="small muted">원장 <code>outputs/depth_axis_verdict_0816.json</code> ·
  그림 재생성 <code>benchmark/build_depth_axis_fig.py</code> ·
  같은 원장의 요약 판
  <a href="../outputs/figures/depth_axis_verdict_0816.png">depth_axis_verdict_0816.png</a> ·
  색인 <a href="{SINCE_DECK}#gaps">00 덱 이후 §4</a></p>
</div>
"""


def build_topic(i: int, tkey: str, tinfo: dict) -> str:
    slug = tkey[2:]
    prev = TOPICS[i - 1][0] if i > 0 else None
    nxt = TOPICS[i + 1][0] if i < len(TOPICS) - 1 else None
    finds = topic_findings(tkey, tinfo)

    cmp_html = ""
    if tinfo["compare"]:
        blocks, ars = [], []
        for p in tinfo["compare"]:
            ttl, cap = compare_caption(p)
            b, ar = img_block(p, ttl, cap)
            blocks.append(b)
            ars.append(ar)
        cols = " ".join(f"{a:.2f}fr" for a in ars[:2]) if len(ars) > 1 else "1fr"
        cmp_html = (f'<h2>이 주제를 한 장으로</h2>'
                    f'<div class="figrow" style="--cols:{cols}">{"".join(blocks)}</div>')

    arms_html = "".join(arm_section(a) for a in sorted(tinfo["arms"]))

    body = f"""
{stale_banner()}
<header class="top">
  <div class="kicker">{esc(tkey[:2])} · {esc(tinfo['label_en'])} · 주제 {i + 1} / {len(TOPICS)}</div>
  <h1>{esc(TOPIC_Q.get(slug, slug))}</h1>
  <p class="lede">{TOPIC_WHY.get(slug, esc(tinfo['label_ko']))}</p>
  <div class="stats">
    <div class="stat"><b>{len(tinfo['arms'])}</b><span>팔</span></div>
    <div class="stat"><b>{n_cells(tinfo)}</b><span>칸</span></div>
    <div class="stat"><b>{n_figs(tinfo)}</b><span>그림</span></div>
  </div>
  <div class="note"><b>⭐ 핵심 발견</b>
    <ul class="find">{"".join(f"<li>{x}</li>" for x in finds)}</ul>
    <p class="small muted">전부 <code>outputs/md_atlas_index.json</code> 과 원장에서 계산한 수다.
    «격자 흔들림 밴드»는 리듬 몫 {RHY_BAND:.1f} %p — 그 안의 차이는 판정하지 않는다.</p>
  </div>
</header>

{cmp_html}

{topic_extra(slug)}

<h2>팔마다 — 맵 · 대역 에너지 · 수치</h2>
<p class="lede">왼쪽이 <b>마이크로도플러 맵</b>(가로 시간 · 세로 도플러), 오른쪽이
<b>블레이드 대역 에너지</b>(점선이 예측 박자의 정수배)다. 그림을 클릭하면 원본 크기로 열린다.
읽는 법이 헷갈리면 <a href="index.html#howto">대문의 «어떻게 읽나»</a> 로 돌아가면 된다.</p>
{arms_html}
"""
    return page(f"{tkey} · {TOPIC_Q.get(slug, slug)}", nav_bar(tkey, prev, nxt), body)


# ═══════════════════════════════════════════════════════════════════════════ #
#  10. README.md — 같은 내용의 마크다운 판
# ═══════════════════════════════════════════════════════════════════════════ #
def md_uscore(s: str) -> str:
    """⚠마크다운은 `_x_` 를 기울임으로 읽는다 — 원장 문구의 밑줄이 그대로 보이게 막는다."""
    return s.replace("_", "\\_")


def readme_extra(slug: str) -> list[str]:
    """`topic_extra()` 의 마크다운 판 — 같은 수를 같은 원장에서 읽는다."""
    if slug != "switch":
        return []
    n = _depth_numbers()
    if n is None:
        return []
    return [
        "**⭐ 반사 깊이 축 — 깊이 1 과 깊이 3 이 같은 것을 읽나** "
        "(8/18 덱 «Future work» 1 번)",
        "",
        f"짝 {n['n_pairs']} 개(깊이 1↔3 {n['n13']} · 1↔2 {n['n12']})를 전수 조사한 판정: "
        "**우리 규약(깊이 1)에 대해서는 닫히고, 축 전체로는 아직 안 닫힌다.**",
        "",
        f"- **닫힌 것** — 표준 프레임 두 팔의 깊이 짝 {n['n_std']} 개 전부 리듬 몫 차 "
        f"**≤{n['std_rhy']:.2f} %p**, 빗각·거리 {n['n_obl']} 칸에서 빗살 대비 차 "
        f"**≤{n['std_comb']:.2f} dB**. 큐에서 깊이 3 을 표준 팔에 다시 태울 이유가 없다.",
        f"- **안 닫힌 것** — 회절 켠 조합에서 깊이 3 이 요동 절대전력을 "
        f"**+{n['lv_lo']:.2f}~+{n['lv_hi']:.2f} dB** 올린다"
        f"(−30° 밴드 {n['band30']:.2f} dB 의 4~6 배). 그 팔의 절대 레벨 인용에는 "
        "«깊이 1 한정» 꼬리표가 필요하다.",
        f"- ⛔**철회** — «−60° 에서 깊이 3 이 리듬을 무너뜨린다»(08-15)는 자세 "
        f"{thousands(n['n_poses'])} 개 중 하나(#{n['pose']}) 때문이었다. "
        "`outputs/switch_factorial.json` 의 `B_failures` 첫 줄은 인용 금지.",
        "",
        f"![깊이 축 판정]({rel('outputs/figures/depth_axis_0816.png')})",
        "",
        f"![깊이 1 대 3 맵]({rel('outputs/figures/depth_axis_maps_0816.png')})",
        "",
        "원장 `outputs/depth_axis_verdict_0816.json` · "
        "재생성 `benchmark/build_depth_axis_fig.py`",
        "",
    ]


def readme_outlier(n_move: int, n_under: int, n_dom: int, rows: list) -> list[str]:
    """`outlier_note()` 의 마크다운 판 — 같은 수를 같은 원장(색인 `_meta.outlier`)에서 읽는다."""
    if not OUT_META:
        return []
    fen = OUT_META.get("dominance_fence")
    g = OUT_META.get("grades") or {}
    out = [
        f"7. ⭐**자세 «하나»가 헤드라인을 끄는 칸이 {n_move} 개** — «⚑ 튐» 딱지. "
        "그 칸에서 가장 큰 자세 하나를 이웃 평균으로 갈아 끼우고 헤드라인 넷(리듬 몫 · "
        "빗살 대비 · 요동 전력 · 상한 위 몫)을 다시 잰 폭이 ① 죄 없는 자세 12 개·둘째 자세를 "
        f"같은 방법으로 갈아 끼웠을 때보다 **{fen:.0f}배** 넘게 크고 ② 그 앙각의 **격자 산포 "
        "밴드**보다 크면 «튐»이다.",
    ]
    for nm, k, c in rows:
        out.append(f"   - `{md_uscore(nm)}` {deg_txt(float(k))} — "
                   + md_escape(c.get("outlier_why_ko") or ""))
    out += [
        f"   - «◱ 자세 하나 쏠림(밴드 안)» {n_dom} 개 — 끌긴 하는데 폭이 밴드 안이라 "
        "**읽기는 안 바뀐다**.",
        f"   - «⌗ 덜 찍힌 플래시» {n_under} 개 — ⭐**튐이 아니다.** 진짜 날개 플래시가 "
        "**한 표본 폭**으로 찍힌 것이다(참 신호가 표본 간격보다 좁다). 고칠 곳은 그 칸이 "
        "아니라 **표집**이고, 그 칸의 «상한 위 몫·빗살 대비» 인용에는 그 단서가 필요하다.",
        f"   - «◈ 경계 — 대조군 추첨에 흔들림» {OUT_META.get('n_grade_shaky', 0)} 개 — 쏠림의 "
        "분모가 «죄 없는 자세 12 개의 **최댓값**»이라 어느 12 개를 뽑느냐에 등급이 걸린다. "
        "중앙값 대조군으로 다시 재서 판정이 갈리면 이 딱지를 붙였고, 감식 원장과 등급이 갈린 "
        f"칸 {OUT_META.get('n_disagree_with_census', 0)} 개에는 그쪽 등급도 함께 적었다 — "
        "«둘 중 하나가 틀렸다»가 아니라 «문턱에 걸터앉아 있다»는 뜻이다.",
        "   - ⛔**깃발이 떴다고 자동으로 버리지 마라** — 뜻은 «이 수는 자세 하나에 걸려 "
        "있으니 그 자세를 열어 보라»이지 «틀렸다»가 아니다. 로터가 시선과 맞는 순간의 "
        "**진짜 정반사 플래시**도 이렇게 보인다. 그래서 크기(최대÷중앙)는 등급에 안 쓰고 "
        "되풀이·이웃·영향으로만 판정한다.",
        "   - 등급 분포 " + (" · ".join(f"{k} {v}" for k, v in sorted(g.items(),
                                                                     key=lambda x: -x[1]))
                          or "—")
        + f". 문턱 출처 `{md_uscore(str(OUT_META.get('threshold_source')))}` "
          f"(원장 {OUT_META.get('census_ledger_rows')} 행) · 밴드 "
          f"`{md_uscore(str(OUT_META.get('band_source')))}`."
        + ("" if not OUT_META.get("thresholds_stale") else
           f" ⚠**문턱이 낡았다** — 지금 원장은 {OUT_META.get('ledger_rows_now')} 행이라 "
           "`benchmark/outlier_census_0816.py` 를 다시 돌려야 선이 맞는다."),
    ]
    return out


def md_escape(s: str) -> str:
    return s.replace("<b>", "**").replace("</b>", "**") \
            .replace("<code>", "`").replace("</code>", "`") \
            .replace("&lt;", "<").replace("&gt;", ">") \
            .replace("<br>", " ")


def build_readme() -> str:
    total_cells = sum(n_cells(t) for _, t in TOPICS)
    deg_cells = sum(1 for a in ARM_IDX.values() for c in a["cells"].values()
                    if c.get("tip_ceiling_degenerate"))
    nr_cells = sum(1 for a in ARM_IDX.values() for c in a["cells"].values()
                   if c.get("no_return"))
    inc_cells = sum(1 for a in ARM_IDX.values() for c in a["cells"].values()
                    if c.get("incomplete"))
    nm_cells = sum(1 for a in ARM_IDX.values() for c in a["cells"].values()
                   if c.get("no_motion"))
    sp_cells = sum(1 for a in ARM_IDX.values() for c in a["cells"].values()
                   if c.get("beat_spiky"))
    ou_cells = sum(1 for a in ARM_IDX.values() for c in a["cells"].values()
                   if c.get("one_pose_moves_headline"))
    us_cells = sum(1 for a in ARM_IDX.values() for c in a["cells"].values()
                   if c.get("flash_comb_undersampled"))
    dm_cells = sum(1 for a in ARM_IDX.values() for c in a["cells"].values()
                   if c.get("one_pose_dominates_within_band"))
    ou_rows = [(nm, k, c) for nm, a in sorted(ARM_IDX.items())
               for k, c in sorted(a["cells"].items())
               if c.get("one_pose_moves_headline")]
    L = []
    A = L.append
    A("# 드론 마이크로도플러 아틀라스 — 보기 쉬운 판")
    A("")
    A(f"> ⭐**먼저 볼 것 — [`{SINCE_DECK}`]({SINCE_DECK}) · 8/18 덱 이후에 한 실험 (한 장 색인)**")
    A("> 덱에 실린 데까지가 기준선이고, 그 뒤 **실험 30 건**이 무엇을 물어 무엇으로 답했는지를")
    A("> «물음 / 판정 / 근거 원장 / 볼 곳» 네 칸으로 한 장에 모았다.")
    A("> 이 갤러리의 어느 그림이 어느 실험의 답인지도 거기서 이어진다.")
    A("")
    A(f"실험 원장에 쌓인 **팔 {META['n_arms']} 개 · 칸 {total_cells} 개**를 두 종류의 그림 — "
      "**마이크로도플러 맵**과 **블레이드 대역 에너지** — 으로 전부 구워 놓은 갤러리다.")
    A("")
    A("| 어디로 | 무엇 |")
    A("|---|---|")
    A(f"| [`{SINCE_DECK}`]({SINCE_DECK}) | ⭐**덱 이후 색인** — 실험 30 건 · "
      "물음/판정/원장/볼 곳 · 아직 그림 없는 것 |")
    A("| [`index.html`](index.html) | **대문** — 읽는 법 · 주제 카드 9 장 · 이름 읽는 법 · 주의 |")
    for tkey, tinfo in TOPICS:
        slug = tkey[2:]
        A(f"| [`{page_name(tkey)}`]({page_name(tkey)}) | {TOPIC_Q.get(slug, slug)} "
          f"(팔 {len(tinfo['arms'])} · 그림 {n_figs(tinfo)}) |")
    A("")
    A("> 브라우저로 열려면 `atlas/index.html` 을 열면 된다(VSCode 에서 파일 우클릭 → "
      "«Open with Live Server» 또는 그냥 파일 두 번 클릭). 인터넷 없이 열린다 — "
      "CSS 가 파일 안에 들어 있고 그림은 저장소 안 상대경로다.")
    A("")
    A("---")
    A("")
    A("## 1. 이 그림들을 어떻게 읽나")
    A("")
    A("**① 마이크로도플러 맵** — " + md_escape(MAP_CAP))
    A("")
    A("**② 블레이드 대역 에너지** — " + md_escape(BAND_CAP))
    A("")
    ex_arm = sorted(TOPICS[0][1]["arms"])[0]
    ex = ARM_IDX[ex_arm]
    A(f"예시(`{ex_arm}`):")
    A("")
    A(f"![맵 예시]({rel(ex['figures']['map'])})")
    A("")
    A(f"![대역 에너지 예시]({rel(ex['figures']['band'])})")
    A("")
    A("### 용어")
    A("")
    A("| 말 | 뜻 |")
    A("|---|---|")
    A("| 도플러 | 움직이는 것에 맞고 되돌아온 신호의 주파수가 밀린 양[Hz]. 빠를수록 크다 |")
    A("| 박자(`f_flash`) | 날개가 시선을 지나가는 횟수[Hz] = 날개 수 × 회전수. 기체마다 다르다 |")
    A(f"| 날개끝 상한(`f_tip`) | 날개 **끝**이 만들 수 있는 가장 큰 도플러. 바로 아래({MINUS}90{DEG})에서 0 |")
    A("| 리듬 몫[%] | 날개끝 상한 **«위»에** 남은 힘 중 박자의 정수배(±8 Hz)에 붙은 몫. "
      "⛔**상한 위만 본다** — 날개 무늬가 상한 «아래»에 멀쩡히 있어도 0 % 가 나올 수 있다. "
      "0 % 는 «리듬 없음» 이 아니라 «이 자리에선 못 읽음» 이다. 백색잡음 값은 팔마다 다르다 |")
    A("| 빗살 대비[dB] | ⭐리듬 몫의 **짝**. 상한 **아래**(날개가 실제로 사는 자리)에서 "
      "«정수배 자리 ÷ 그 사이 자리» 전력비. 백색잡음 0 dB. 두 수가 **함께** 널일 때만 "
      "«안 보인다» 고 말한다 |")
    A(f"| 정지 성분 제거 | 가만히 있는 부분(시간 평균)을 빼는 것. {META['level_rule_ko'].lstrip('⭐')} |")
    A(f"| 앙각 | 얼마나 위에서 내려다보는가. 0{DEG} 옆에서 · {MINUS}90{DEG} 바로 위에서 |")
    A("| 팔 | 조건 하나(엔진 · 거리 · 스위치 조합 …). 팔 이름이 곧 조건이다 |")
    A("")
    A("### 그림을 만든 규약")
    A("")
    for k in ("stft_ko", "map_window_ko", "airframe_rule_ko", "nadir_rule_ko"):
        A(f"- {md_uscore(META[k])}")
    A(f"- 기본값 — 주파수 {META['fc_hz'] / 1e9:g} GHz · 표본율 {META['prf_hz']:g} Hz · "
      f"기본 기체 {META['drone_default']} · 기준 거리 {META['range_m_primary']:g} m · "
      f"그림 구운 시각 {built_at_kst()}.")
    A("")
    A("---")
    A("")
    A("## 2. 주제 9 개")
    for i, (tkey, tinfo) in enumerate(TOPICS):
        slug = tkey[2:]
        A("")
        A(f"### {tkey[:2]}. {TOPIC_Q.get(slug, slug)}")
        A("")
        A(f"> {TOPIC_WHY.get(slug, tinfo['label_ko'])}")
        A("")
        A(f"팔 {len(tinfo['arms'])} 개 · 칸 {n_cells(tinfo)} 개 · 그림 {n_figs(tinfo)} 장 · "
          f"페이지 [`{page_name(tkey)}`]({page_name(tkey)})")
        A("")
        A("**⭐ 핵심 발견**")
        A("")
        for f in topic_findings(tkey, tinfo):
            A(f"- {md_escape(f)}")
        A("")
        for line in readme_extra(slug):
            A(line)
        th = thumb_for(tinfo)
        A(f"![{tkey} 요약]({rel(th)})")
        A("")
        A("| 팔 | 무엇을 바꾼 판인가 | 앙각 | 리듬 몫[%] | 맵 · 대역 |")
        A("|---|---|---|---|---|")
        for arm in sorted(tinfo["arms"]):
            a = tinfo["arms"][arm]
            els = a["elevations_deg"]
            rs = []
            for el in els:
                c = a["cells"].get(cell_key(float(el)))
                rs.append("—" if not c or c.get("rhythm_share_pct") is None
                          else f"{c['rhythm_share_pct']:.0f}")
            eltxt = " ".join(deg_txt(float(e)).replace(DEG, "") for e in els)
            A(f"| `{arm}` | {md_escape(' · '.join(arm_facts(arm)))} | {eltxt} | {' '.join(rs)} | "
              f"[맵]({rel(a['figures']['map'])}) · [대역]({rel(a['figures']['band'])}) |")
    A("")
    A("---")
    A("")
    A("## 3. 팔 이름 읽는 법")
    A("")
    A("| 토막 | 뜻 | 없으면(기본값) | 쓰인 팔 |")
    A("|---|---|---|---|")
    for tok, mean, dflt, pred in TOKENS:
        cnt = sum(1 for a in ALL_ARMS if pred(a))
        A(f"| `{md_escape(tok)}` | {md_escape(mean)} | {dflt} | {cnt} |")
    A("")
    A("---")
    A("")
    A("## 4. ⚠ 읽을 때 주의")
    A("")
    A(f"1. **바로 아래({MINUS}90{DEG})는 잣대가 망가진다** — 날개끝 상한이 0 Hz 라 «상한 위»가 전 대역이 된다. "
      f"그런 칸이 **{deg_cells} 개**이고 표에 «▲ 잣대 퇴화»로 적었다. 대역 그림은 0{DEG} 것을 빌려 그린다.")
    A(f"2. **엔진끼리 절대 세기를 비교하지 마라** — 우리 커널과 PathSolver 는 눈금이 다르다. "
      "모양과 눈금에 무관한 수(리듬 몫 · 박자 · 박자÷예측)로만 말한다. 같은 팔 안 앙각끼리는 비교해도 된다.")
    A(f"3. **격자 흔들림 밴드 안이면 판정 불가** — 격자를 λ/12 → λ/24 로 조이기만 해도 "
      f"리듬 몫 **{RHY_BAND:.1f} %p** · 움직이는 전력 **{AC_BAND:.2f} dB** 가 움직인다(`{BAND_SRC}`). "
      f"두 팔의 차이가 그 안이면 «차이가 있다»고 말할 수 없다. "
      "⚠이 밴드는 **우리 커널의 격자 축**에서 나온 수다 — PathSolver 에는 그 축이 없으니 "
      "그쪽에 대는 것은 빌려 쓰는 것이다.")
    A("4. **거리가 다른 팔이 섞여 있고, 근접장은 기체마다 다른 자리에서 시작한다** — "
      "이름에 `r` 토막이 없는 팔은 옛 기본 10 m 다. 원거리장 경계 2D²/λ 는 표적이 커지면 "
      "멀어진다:")
    for r in FARFIELD:
        A(f"   - {r['label']} — D {r['D']:.2f} m · 경계 **{r['r_ff']:.2f} m** · "
          f"이 원장의 거리 {' · '.join(f'{x:g} m' for x in r['ranges'])} → "
          + md_escape(r["verdict"]))
    A(f"5. **수를 낼 자격이 없는 칸이 {nr_cells + inc_cells + nm_cells} 개** — "
      f"되돌아온 게 없는 칸 {nr_cells} 개 · ⭐**아직 자세가 덜 찬 칸 {inc_cells} 개** · "
      f"움직이는 것이 없는 칸 {nm_cells} 개. 그 칸에는 잣대를 싣지 않았다. "
      "덜 찬 칸은 빈 자세 자리의 0 채움이 스펙트럼을 PRF/2 · PRF/4 에 복제해 리듬 몫을 "
      "0 % 로 만든다 — **물리가 아니라 결측 자국**이라, 원장을 다시 병합해야 읽을 수 있다.")
    A(f"6. **자세 몇 개가 유난히 큰 칸이 {sp_cells} 개** — «⚡ 큰 자세» 딱지가 붙은 칸의 박자는 "
      "회전이 아니라 튄 자세들의 간격일 수 있다. 맵도 그 자세 하나가 색역을 다 먹는다. "
      "⚠이 딱지는 **크기만** 잰 수다 — «혼자 큰가»는 아래 7 번이 잰다.")
    for line in readme_outlier(ou_cells, us_cells, dm_cells, ou_rows):
        A(line)
    A("")
    A("### 아직 못 고친 것")
    A("")
    A(f"- **덜 찬 칸 {inc_cells} 개의 참값** — 원장 재병합이 필요하다. 세 칸 중 둘은 자세가 "
      "뭉텅이로 빠져 «0 을 걷어내고 다시 재는» 길도 없다(균일 표본이 아니다).")
    A("- **주제 분류가 아직 이름 토막으로 거리를 본다** — `_r` 토막이 없는 10 m 옛 팔이 "
      "«기본 엔진» 주제에 남아 있다. 안전장치는 위의 거리 표와 그림 속 거리 라벨이다.")
    A("- **맵은 패널마다 자기 최댓값으로 밝기를 맞춘다** — 거리·세기는 그림에서 못 읽는다.")
    A("- **리듬 몫의 창 반폭은 8 Hz 고정** — 정의를 유지한 대가로 100 은 도달 불가다.")
    A("- **박자는 전 구간, 맵은 20~80 ms** — 같은 상자의 두 수가 다른 구간에서 나왔다.")
    A("")
    A("---")
    A("")
    A("## 5. 다시 굽는 법")
    A("")
    A("```bash")
    A("# ① 그림(원장이 바뀌었을 때만)")
    A("PYTHONPATH=src /workspace/.venvs/py312/bin/python benchmark/build_md_atlas.py")
    A("# ② 이 갤러리")
    A("/workspace/.venvs/py312/bin/python benchmark/build_atlas_gallery.py")
    A("```")
    A("")
    A("그림은 **복사하지 않는다** — `../outputs/figures/atlas/` 를 상대경로로 걸 뿐이라 "
      "저장소가 두 배로 커지지 않는다. 원장이 그림보다 새로우면 페이지 맨 위에 «낡음» 띠가 뜬다.")
    A("")
    return "\n".join(L)


# ═══════════════════════════════════════════════════════════════════════════ #
#  11. main
# ═══════════════════════════════════════════════════════════════════════════ #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUTDIR, help="갤러리를 만들 폴더(기본 atlas/)")
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)

    written = []
    p = os.path.join(out, "index.html")
    open(p, "w", encoding="utf-8").write(build_index())
    written.append(p)

    for i, (tkey, tinfo) in enumerate(TOPICS):
        p = os.path.join(out, page_name(tkey))
        open(p, "w", encoding="utf-8").write(build_topic(i, tkey, tinfo))
        written.append(p)

    p = os.path.join(out, "README.md")
    open(p, "w", encoding="utf-8").write(build_readme())
    written.append(p)

    # ── 자기검사 ────────────────────────────────────────────────────────────
    print(f"✅ {len(written)} 개 파일 · {out}")
    for w in written:
        print(f"   {os.path.relpath(w, ROOT)}  {os.path.getsize(w) / 1024:.0f} KB")
    uniq = sorted(set(MISSING))
    if uniq:
        print(f"⛔ 그림 {len(uniq)} 장이 실제로 없다 — 링크가 깨진다:")
        for m in uniq[:12]:
            print(f"   {m}")
    else:
        print(f"✅ 건 그림 {len(LINKED)} 장 전부 실재 · 빠짐 0 "
              f"(색인이 아는 그림 {META['n_figures']} 장)")
    print(f"   주제 {len(TOPICS)} · 팔 {len(ALL_ARMS)} · "
          f"칸 {sum(len(v['cells']) for v in ARM_IDX.values())} "
          f"(색인 _meta: {META['n_topics']} · {META['n_arms']} · {META['n_cells']})")
    if stale_banner():
        print("⚠ 원장이 색인보다 새롭다 — build_md_atlas.py 를 다시 돌려야 최신이 된다")


if __name__ == "__main__":
    main()
