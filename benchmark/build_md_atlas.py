# -*- coding: utf-8 -*-
"""
build_md_atlas.py — 앙각 스윕 원장의 **모든 팔**을 그림으로 굽는 아틀라스 생성기.

왜 만드나
--------
`outputs/elevation_sweep_md.{json,npz}` 에는 지금 **팔 54 개 · 칸 220 개**가 들어 있는데,
그림으로 나온 것은 덱이 고른 세 팔뿐이다(`build_deck_maps.py`). 나머지는 «있는 줄도 모르는»
상태라, 원장에 있는데도 아무도 안 본 판이 대부분이다. 이 파일은 그 전부를 굽는다.

무엇을 굽나
----------
한 팔 = 그림 두 장이 기본이다.

  (a) `…__map.png`   그 팔이 가진 앙각을 **가로로** 늘어놓은 맵 격자.
                     위 줄 = 받은 그대로(0 도플러의 동체 선이 읽기의 기준),
                     아래 줄 = **정지 성분(시계열 평균)을 뺀** 판 = 움직이는 것만.
                     패널 구석에 리듬 몫[%] 을 작게 적는다.
  (b) `…__band.png`  블레이드 대역 전력 g(t) 의 **변조 스펙트럼** — 앙각마다 곡선 하나,
                     예측 박자(f_flash)의 정수배에 점선. 왼쪽 넓은 범위(100~1,000 Hz),
                     오른쪽 확대(0~420 Hz).

주제마다 **비교판**을 따로 굽는다 — 같은 주제의 팔들을 한 장에 모아 한 눈에 보게 한다
(스위치 조합 한 장, 기체 3 종 한 장, 거리 사다리 한 장 …). 너무 크면 쪽으로 쪼개되
파일 이름이 이어지므로 목차 순서는 그대로다.

규약(집 규칙)
-----------
· 마이크로도플러 표현은 **STFT 만** — `src/md_mapstyle.py` 의 `flash_spec`(0.45~0.6 블레이드
  주기 조각 · hop 2 · 8× 제로패딩)을 그대로 쓴다. 재할당·WVD 같은 다른 표현은 안 쓴다.
· 맵은 **패널마다 자기 최댓값**으로 정규화한다 — 모양을 읽는 그림이지 세기를 읽는 그림이
  아니다. 세기(dB)를 비교하는 수치는 전부 **정지 성분 제거 후**에 잰다.
· 그림 안 글자는 **영어**, 목차·주석·print 는 한국어.
· 각도는 «−30°»(U+2212)로 적는다.

⚠ 기체 태그(_mini5pro_ · _s1000plus_ …)가 붙은 팔은 **그 기체의 박자**로 잣대를 세운다.
  원장 `_meta.f_flash_hz` 는 기본 기체(matrice4e)의 126.67 Hz 라, 그대로 쓰면 mini5pro
  (183.33 Hz)·s1000plus(148.90 Hz) 팔의 점선이 전부 엉뚱한 자리에 선다.
⚠ 앙각 −90°(직하방)는 날개끝 상한 f_tip 이 **0 Hz** 라 «상한 위» 라는 잣대가 퇴화한다.
  그 칸은 그림에 그 사실을 적고(별표), 대역은 0° 의 대역을 빌려 쓴다.

⭐2026-08-15 수리 — «없는 물리를 있다고 읽게 만드는» 자리 넷을 막았다
--------------------------------------------------------------------
① **덜 찬 칸**(원장 `n_missing` 이 0 도 전부도 아닌 칸)에서는 **수를 아예 안 낸다.**
   그전에는 «전력이 0인가» 하나만 봐서, 자세 절반이 비어 0 으로 채워진 칸이 멀쩡한 칸으로
   실렸다. 0 을 끼우면 스펙트럼이 PRF/2·PRF/4 에 복제되어 «상한 위» 를 그 복제본이 삼키고
   리듬 몫이 0 % 로 주저앉는다 — 물리가 아니라 **결측 자국**이다.
   ⚠ 그 칸을 «고쳐서» 수를 내는 길은 없다: 비는 자리가 균일한 칸(2 칸 걸러 하나)은 하나뿐이고
     나머지는 자세가 뭉텅이로 빠져 균일 표본이 아니다. 그러므로 **원장을 다시 병합**해야 한다.
② **움직이는 것이 없는 칸**(AC/DC < 1e-12 = 배정밀도 반올림 바닥)도 같은 취급이다.
   프로펠러를 뺀 판이 그렇다 — 그전에는 반올림 오차의 봉우리를 «박자 204 Hz» 로 적었다.
③ 리듬 몫의 **널(백색잡음 값)을 칸마다 정확히 세어** 함께 낸다. 13 % 는 기본 기체 값이라
   mini5pro 팔(≈8.7)에 대면 «리듬 없음» 을 «있음» 으로 뒤집어 읽게 된다.
④ 리듬 몫은 **상한 위만** 재는 잣대라 낮은 값이 «날개가 없다» 는 뜻이 아니다. 그래서
   상한 **아래** 를 보는 대안 잣대 **빗살 대비[dB]** 를 함께 내고 그림에도 적는다
   (정수배 자리 ↔ 그 사이 자리의 전력비. 백색잡음 ≈ 0 dB).

돌리는 법
--------
    PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/build_md_atlas.py
    …                       benchmark/build_md_atlas.py --topics switch airframe
    …                       benchmark/build_md_atlas.py --force        # 다시 굽기

이미 있는 그림은 **원장·이 코드보다 새로울 때만** 건너뛴다 — 코드를 고치면 원장이 그대로여도
다시 굽는다(2026-08-15 수리: 그전에는 원장 시각만 봐서 코드를 고쳐도 옛 그림이 남았다).
산출 목록과 요약 수치는 `outputs/md_atlas_index.json` 에 남는다 — 목차 문서가 그것을 읽는다.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import textwrap
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                        # noqa: E402
import numpy as np                                                     # noqa: E402
from matplotlib.lines import Line2D                                    # noqa: E402
from matplotlib.ticker import MaxNLocator                              # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
from md_mapstyle import auto_periods, flash_spec, draw, YLIM_FTIP      # noqa: E402

OUTDIR = os.path.join(ROOT, "outputs", "figures", "atlas")
INDEX = os.path.join(ROOT, "outputs", "md_atlas_index.json")
LED_J = os.path.join(ROOT, "outputs", "elevation_sweep_md.json")
LED_N = os.path.join(ROOT, "outputs", "elevation_sweep_md.npz")

C_LIGHT = 2.998e8
MINUS = "−"          # U+2212 — 각도의 음수 부호(하이픈 아님)
DEG = "°"

#: 맵이 보여 주는 창 — 앞 20 ms 를 건너뛰고 60 ms. 플래시가 여러 번 지나가는 길이다.
T0, TSPAN = 0.020, 0.060
#: 블레이드 대역 변조 스펙트럼의 두 창(넓은 것 · 확대한 것)
BAND_WIDE, BAND_ZOOM = (100.0, 1000.0), (0.0, 420.0)
#: 리듬 몫을 잴 때 정수배 선 하나에 허용하는 반폭[Hz] (build_deck_maps.structure_bars 와 같다)
RHY_HW = 8.0
#: ⭐«움직이는 것이 없다» 문턱 — AC/DC 전력비가 이보다 작으면 시계열이 사실상 상수다.
#  배정밀도 1 ULP(≈2.2e-16)의 제곱이 ~5e-32 이므로 1e-12 는 그보다 20 자리 위의 넉넉한 문턱이다.
NO_MOTION_ACDC = 1e-12
#: ⭐«몇 자세가 통째로 튀었다» 문턱 — |AC| 의 최대÷중앙. 이보다 크면 박자를 «잰 값» 으로 안 쓴다.
SPIKE_MAX = 100.0


# ═══════════════════════════════════════════════════════════════════════════ #
#  원장 읽기
# ═══════════════════════════════════════════════════════════════════════════ #
J = json.load(open(LED_J))
Z = np.load(LED_N, allow_pickle=True)
M = J["_meta"]
assert int(np.asarray(Z["phase_sign_v2"]).ravel()[0]) == 1, "⛔ 부호 정정본이 아니다"

PRF = float(M["prf_hz"])
FC = float(M["fc_hz"])
DRONE_DEFAULT = str(M.get("drone", "matrice4e"))
RANGE_PRIMARY = float(M.get("range_m_primary", 15.0))
ROW = {(r["engine"], float(r["el_deg"])): r for r in J["rows"]}
#: 건너뛰기 기준 — **원장이나 이 코드가 그림보다 새로우면** 다시 굽는다.
#  ⭐2026-08-15 수리: 그전에는 원장 시각만 봐서, 그림 모양을 바꾸는 코드 수정 뒤 --force 를
#    빼먹으면 옛 그림이 그대로 남았다(코드는 새 규칙, 그림은 옛 규칙 → 목차와 그림이 갈린다).
LEDGER_MTIME = max(os.path.getmtime(LED_J), os.path.getmtime(LED_N))
CODE_MTIME = max(os.path.getmtime(os.path.abspath(__file__)),
                 os.path.getmtime(os.path.join(ROOT, "src", "md_mapstyle.py")))
FRESH_AFTER = max(LEDGER_MTIME, CODE_MTIME)

from drones import DRONES                                              # noqa: E402


# ═══════════════════════════════════════════════════════════════════════════ #
#  팔 자동 발견 · 주제 분류 — ⭐하드코딩 목록 없이 **이름 규칙**에서만 유도한다
# ═══════════════════════════════════════════════════════════════════════════ #
# ⚠생성기(benchmark/elevation_sweep_md.py)는 방위·거리를 `:g` 로 찍는다 — 22.5° 는 «az22.5»,
#   음수 방위는 «az-45» 다. 정수만 받는 정규식을 쓰면 그런 팔이 조용히 «기본 엔진» 으로 샌다.
RE_SW = re.compile(r"^sw(?:[A-Z]\d)+$")             # swR1D0E0F1 — 물리 스위치 조합
RE_AZ = re.compile(r"^az[-+]?\d+(?:\.\d+)?$")       # az45 · az22.5 — 방위
RE_R = re.compile(r"^r(\d+(?:\.\d+)?)$")            # r15 · r30 — 거리
RE_DIV = re.compile(r"^div\d+$")                    # div24 — 격자 세분

#: 목차 순서. 여기 없는 주제(새 이름 규칙)는 뒤에 알파벳 순으로 붙는다.
TOPIC_ORDER = ["base", "switch", "airframe", "azimuth", "parts",
               "range", "ptd", "grid", "planewave"]
TOPIC_LABEL = {
    #: ⚠«…만 갈린다» 라고 적었던 것을 고쳤다 — 01base 13 팔은 **거리도 갈린다**
    #   (10 m 8 팔 · 15 m 5 팔, 원거리장 경계 14.08 m 를 가로지른다). 이름에 `_r` 토막이
    #   없는 옛 팔이 기본 거리 10 m 라서 그렇다.
    "base":      ("base engines", "기본 엔진 — 엔진·광선예산·자세수, "
                                  "⚠거리도 10 m·15 m 로 섞여 있다"),
    "switch":    ("physics switches", "스위치 — 굴절·회절·모서리·확산을 켜고 끈 조합"),
    "airframe":  ("airframes", "기체 3 종 — 박자가 기체마다 다르다"),
    "azimuth":   ("azimuth", "방위 — 정면 말고 45° 에서 본 판"),
    "parts":     ("scene parts", "부품 분해 — 프로펠러만 / 동체만"),
    "range":     ("range", "거리 — 15 m 아닌 판(30 m)"),
    "ptd":       ("PTD edges", "PTD — 모서리 보정을 켠 판"),
    "grid":      ("grid", "격자 — λ/12 대신 더 촘촘한 격자"),
    "planewave": ("plane wave", "평면파 — 구면파 대신 평면파로 조명한 판"),
}


def discover_cells():
    """원장 npz 의 키에서 «팔 → 앙각 목록» 을 만든다. 새 팔이 생기면 자동으로 따라온다."""
    arms: dict[str, list[float]] = {}
    for k in Z.files:
        if "/" not in k:
            continue
        arm, tag = k.rsplit("/", 1)
        if not tag.startswith("el"):
            continue
        arms.setdefault(arm, []).append(float(tag[2:]))
    for a in arms:
        arms[a] = sorted(set(arms[a]), reverse=True)   # 0, −15, … −90
    return dict(sorted(arms.items()))


def airframe_tag(arm: str) -> str | None:
    """팔 이름에 박힌 기체 태그. 없으면 None(= 원장 기본 기체)."""
    for k in DRONES:
        if f"_{k}_" in arm or arm.endswith(f"_{k}"):
            return k
    return None


def topic_of(arm: str) -> str:
    """⭐이름 규칙만으로 주제를 정한다 — 우선순위는 «무엇을 물어보는 팔인가» 순서다.

    스위치 조합이 기체 태그보다 앞선다: `…_swR1D0E0F1_mini5pro_…` 는 기체를 보려고 만든
    팔이 아니라 **그 스위치 조합을 다른 기체에서도 확인**하려고 만든 팔이다.
    """
    t = arm.split("_")
    if any(RE_SW.match(x) or x.startswith("only") or x == "stockdef" for x in t):
        return "switch"
    if any(RE_AZ.match(x) for x in t):
        return "azimuth"
    if any(x.startswith("parts") for x in t):
        return "parts"
    for x in t:
        m = RE_R.match(x)
        if m and abs(float(m.group(1)) - RANGE_PRIMARY) > 1e-9:
            return "range"
    if "ptd" in t:
        return "ptd"
    if any(RE_DIV.match(x) for x in t):
        return "grid"
    if "pw" in t:
        return "planewave"
    if airframe_tag(arm) is not None:
        return "airframe"
    return "base"


def topic_rank(slug: str) -> int:
    return TOPIC_ORDER.index(slug) if slug in TOPIC_ORDER else len(TOPIC_ORDER)


def topic_prefix(slug: str, unknown: list[str]) -> str:
    """파일 이름 앞머리 — **정렬하면 목차 순서**가 되게.

    ⚠ 아는 주제는 TOPIC_ORDER 자리를 그대로 쓴다(새 주제가 생겨도 기존 파일 이름이 안 밀린다).
      모르는 주제(새 이름 규칙)는 뒤에 알파벳 순으로 번호를 받는다."""
    if slug in TOPIC_ORDER:
        return f"{TOPIC_ORDER.index(slug) + 1:02d}{slug}"
    return f"{len(TOPIC_ORDER) + 1 + unknown.index(slug):02d}{slug}"


def short_labels(arms: list[str]) -> dict[str, str]:
    """비교판에서 쓸 **짧은 이름** — 그 묶음의 팔들이 공유하는 토막을 지운다.

    묶음 안에서 갈리는 축만 남으므로 «무엇이 다른 판인가» 가 라벨에서 바로 읽힌다.
    (예: 스위치 20 조합 → `swR1D0E0F1_d3` 처럼 스위치·깊이만 남는다.)
    """
    if len(arms) == 1:
        return {arms[0]: arms[0]}
    toks = {a: a.split("_") for a in arms}
    common = set(toks[arms[0]])
    for a in arms[1:]:
        common &= set(toks[a])
    out = {}
    for a in arms:
        rest = [x for x in toks[a] if x not in common]
        out[a] = "_".join(rest) if rest else a
    return out


# ═══════════════════════════════════════════════════════════════════════════ #
#  팔마다의 «박자»와 «날개끝 상한» — ⚠기체 태그를 반드시 반영한다
# ═══════════════════════════════════════════════════════════════════════════ #
def arm_rates(arm: str) -> dict:
    """f_flash(날개 통과율) 와 f_tip 의 0° 값. 기체 태그가 있으면 **그 기체**의 제원.

    f_flash = 날개 수 × 호버rpm / 60      [Hz]  — 앙각과 무관
    f_tip   = 2·(2π f_rev R)/λ · cos(el)  [Hz]  — cos(el) 로 줄어든다
    """
    key = airframe_tag(arm) or DRONE_DEFAULT
    s = DRONES[key]
    f_rev = float(s.hover_rpm) / 60.0
    lam = C_LIGHT / FC
    ftip0 = 2.0 * (2 * math.pi * f_rev * (s.prop_dia_mm / 2000.0)) / lam
    return dict(drone=key, drone_label=s.name,
                f_flash_hz=int(s.prop_blades) * f_rev,
                f_tip0_hz=ftip0,
                tagged=airframe_tag(arm) is not None)


def f_tip_at(rates: dict, el: float) -> float:
    return rates["f_tip0_hz"] * math.cos(math.radians(el))


def deg_txt(el: float) -> str:
    """«0°» · «−30°» · «+15°» — 음수는 U+2212."""
    if abs(el) < 1e-9:
        return "0" + DEG
    return ("+" if el > 0 else MINUS) + f"{abs(el):.0f}" + DEG


# ═══════════════════════════════════════════════════════════════════════════ #
#  잣대 — ⭐레벨(dB)은 전부 **정지 성분 제거 후**
# ═══════════════════════════════════════════════════════════════════════════ #
def series(arm: str, el: float) -> np.ndarray:
    return np.asarray(Z[f"{arm}/el{el:+.0f}"], complex)


def rhythm_share(E: np.ndarray, f_flash: float, f_tip: float, hw: float = RHY_HW):
    """날개끝 상한 **위** 에너지 중 «박자의 정수배» 에 붙은 몫 [%].

    세기가 아니라 **구조**를 잰다 — 눈금·정규화에 무관하다.
    `build_deck_maps.structure_bars` 와 **같은 정의**를 유지한다(정의를 바꾸면 이미 인용된
    수와 갈린다). 대신 아래 두 가지를 함께 낸다.

      null   ⭐백색잡음이면 몇 %가 나오나 — «상한 위 빈 가운데 정수배 창 안에 든 빈의 비율»
             이라 칸마다 **정확히 셀 수 있다**(몬테카를로가 필요 없다). 이 값은 박자·상한·
             자세 수에 따라 달라진다: matrice4e ≈ 12.6, s1000plus ≈ 10.8, mini5pro ≈ 8.7.
             ⛔그래서 «13» 하나를 모든 팔에 대면 안 된다.
      above  상한 **위** 가 움직이는 에너지의 몇 %인가. 리듬 몫이 낮은 칸이 «조용해서» 낮은
             것인지 «위가 잡동사니로 가득 차서» 낮은 것인지는 이 수로만 갈린다.

    ⚠ f_tip 이 0(직하방)이면 «상한 위» 가 전 대역이 되어 잣대가 퇴화한다 — 그 사실을 함께 낸다.
    ⚠ 천장 100 은 **도달 불가**다. 실제 로터는 rpm 이 조금씩 흩어져 선이 번지고, 창 반폭이
      8 Hz 로 고정이라 높은 배음일수록 창 밖으로 샌다. 100 을 «완벽한 로터» 로 적지 않는다.
    """
    n = E.size
    P = np.abs(np.fft.fft((E - E.mean()) * np.hanning(n))) ** 2
    fr = np.fft.fftfreq(n, 1.0 / PRF)
    degenerate = f_tip <= 1e-6
    above = np.abs(fr) >= f_tip
    k = np.round(np.abs(fr) / f_flash)
    on = above & (np.abs(np.abs(fr) - k * f_flash) <= hw)
    n_above = int(above.sum())
    null = float(100.0 * int(on.sum()) / n_above) if n_above else None
    den = P[above].sum()
    tot = P.sum()
    frac_above = float(100.0 * den / tot) if tot > 0 else None
    if den <= 0:
        return None, null, frac_above, degenerate
    return float(100.0 * P[on].sum() / den), null, frac_above, degenerate


def comb_contrast_db(E: np.ndarray, f_flash: float, f_tip: float,
                     hw: float = RHY_HW):
    """⭐대안 잣대 — 상한 **아래** 빗살 대비 [dB]. «리듬 몫 0 %» 의 반증 도구.

    리듬 몫은 «날개가 만들 수 없는 자리(상한 위)» 만 본다. 날개 무늬가 상한 **아래** 에
    얌전히 들어앉으면 그 잣대는 0 % 를 낸다 — 무늬가 멀쩡한데도. 이 수는 그 반대편을 본다.

        on  = 박자의 정수배 자리(±hw)          ← 날개가 선을 세우는 자리
        off = 정수배와 정수배의 **한가운데**(±hw)  ← 같은 대역·같은 빈 수의 대조군
        R   = 10 log10( mean P_on / mean P_off )   [dB]

    널은 백색잡음 ≈ 0 dB(실측 +0.4 dB)다. 우리 커널 15 m 정면 ≈ +48 dB,
    PathSolver 같은 자리 ≈ −0.8 dB — 두 엔진을 가르는 자리에서 리듬 몫과 **같은 방향**을
    가리키되, 상한 위가 비어 있어도 살아 있다.
    ⚠ 대역(2·f_flash ~ f_tip)에 배음이 세 개도 안 들어가면 정의되지 않는다(낮은 앙각·직하방).
    """
    lo, hi = 2.0 * f_flash, float(f_tip)
    if not (hi >= 3.0 * f_flash):
        return None
    n = E.size
    P = np.abs(np.fft.fft((E - E.mean()) * np.hanning(n))) ** 2
    fr = np.abs(np.fft.fftfreq(n, 1.0 / PRF))
    band = (fr >= lo) & (fr <= hi)
    k = fr / f_flash
    on = band & (np.abs(k - np.round(k)) * f_flash <= hw)
    off = band & (np.abs(np.abs(k - np.floor(k)) - 0.5) * f_flash <= hw)
    if int(on.sum()) < 4 or int(off.sum()) < 4:
        return None
    num, den = float(P[on].mean()), float(P[off].mean())
    if not (num > 0 and den > 0):
        return None
    return float(10.0 * math.log10(num / den))


def spike_ratio(E: np.ndarray):
    """|AC| 의 **최대 ÷ 중앙**. 몇 자세가 통째로 튀면 100~1000 이 나온다.

    ⭐왜 재나 — 패널은 자기 최댓값으로 정규화하므로 튐 하나가 색역을 다 먹어 맵이 새까매지고,
    그런 칸의 «박자» 는 회전이 아니라 그 튐의 간격을 잰 수다(0.2x 같은 값이 그렇게 나온다).
    """
    ac = np.abs(E - E.mean())
    med = float(np.median(ac))
    if not (med > 0):
        return float("inf") if float(ac.max()) > 0 else None
    return float(ac.max() / med)


def modspec_curve(E: np.ndarray, f_flash: float, f_tip_band: float, periods: float):
    """블레이드 대역 전력 g(t) 의 **변조 스펙트럼**.

    `md_mapstyle.flash_spec` 로 STFT 를 뜨고 0.35~1.0 × f_tip 띠의 전력을 시간축으로 모은 뒤,
    **평균을 빼고**(정지 성분 제거) 스펙트럼을 낸다 — «맵에 줄무늬가 시간축으로 뛰나» 의
    직접 검사다(benchmark/comb_snr.py 의 band_g·mod_snr 와 같은 정의).
    ⚠ f_tip = 0(직하방)이면 대역이 정의되지 않아 호출자가 **0° 의 대역을 빌려** 넘긴다 —
      참값이 «선 없음» 인 자리라, 거기서 빗살이 서면 그것이 곧 인공물이다.
    """
    f, t, S, _ = flash_spec(E, PRF, f_flash, periods)
    m = (np.abs(f) >= 0.35 * f_tip_band) & (np.abs(f) <= f_tip_band)
    if m.sum() < 2:
        return None, None
    g = (S[m, :] ** 2).sum(axis=0)
    fs_g = 1.0 / float(t[1] - t[0])
    n = g.size
    Y = np.abs(np.fft.rfft((g - g.mean()) * np.hanning(n))) ** 2
    fr = np.fft.rfftfreq(n, 1.0 / fs_g)
    return fr, Y


def cell_summary(arm: str, el: float, rates: dict, periods: float) -> dict:
    """한 칸(팔·앙각)의 요약 수치 — 목차 JSON·갤러리가 읽는다.

    ⭐**수를 낼 자격이 있는 칸인가**를 먼저 정한다. 아래 셋 중 하나면 잣대를 내지 않는다
    (None 을 낸다 — 0 을 내면 «쟀는데 0 이었다» 로 읽힌다).

      no_return   에코가 통째로 0. 원장 level_db 가 −6000 이라는 표식을 함께 단다.
      incomplete  ⭐**자세가 덜 찼다** — 원장 `n_missing` 이 0 도 전부도 아니거나, 시계열에
                  «정확히 0» 인 표본이 섞여 있다. 병합이 끝나기 전의 칸이다. 빠진 자리가
                  0 으로 채워져 있어 스펙트럼이 PRF/2·PRF/4 에 복제되고, 그 복제본이 «상한
                  위» 를 삼켜 리듬 몫을 0 % 로 만든다. 물리가 아니라 결측 자국이다.
                  ⚠원장 n_missing 만 믿지 않고 **표본을 직접 세어** 확인한다 — 원장 병합이
                    낡았을 때(샤드가 원장보다 새로울 때) n_missing 은 0 으로 남아 있다.
      no_motion   AC/DC 가 배정밀도 반올림 바닥(1e-12) 아래. 움직이는 부분이 아예 없는 판이다
                  (프로펠러를 뺀 대조군). 그런 칸의 «박자» 는 1 ULP 를 흔든 자리라 재현되지 않는다.
    """
    E = series(arm, el)
    ft = f_tip_at(rates, el)
    ffl = rates["f_flash_hz"]
    Eac = E - E.mean()
    p_ac = float(np.mean(np.abs(Eac) ** 2))
    p_tot = float(np.mean(np.abs(E) ** 2))
    row = ROW.get((arm, el), {})

    n_zero = int(np.count_nonzero(E == 0))
    empty = (not (p_tot > 0.0)) or n_zero == E.size
    n_miss = int(row.get("n_missing") or 0)
    n_pose = int(row.get("n_poses") or E.size)
    incomplete = (not empty) and ((0 < n_miss < n_pose) or 0 < n_zero < E.size)
    acdc = (p_ac / p_tot) if p_tot > 0 else 0.0
    no_motion = (not empty) and (not incomplete) and acdc < NO_MOTION_ACDC
    mute = empty or incomplete or no_motion          # ⭐수를 낼 자격이 없는 칸

    share, null, frac_above, degen = rhythm_share(E, ffl, ft)
    comb = None if mute else comb_contrast_db(E, ffl, ft)
    spike = None if empty else spike_ratio(E)
    spiky = bool(spike is not None and spike > SPIKE_MAX)

    ft_band = ft if ft > 1e-6 else rates["f_tip0_hz"]
    beat = beat_rel = None
    if not mute:
        fr, Y = modspec_curve(E, ffl, ft_band, periods)
        if fr is not None:
            sel = (fr > 20.0) & (fr < 1000.0)
            if sel.any() and float(Y[sel].max()) > 0.0:
                beat = float(fr[sel][int(np.argmax(Y[sel]))])
                beat_rel = round(beat / ffl, 3)
    return dict(
        el_deg=el,
        f_tip_hz=round(ft, 1),
        # ── 깃발: 이 칸을 읽어도 되나 ──────────────────────────────────────
        no_return=bool(empty),
        incomplete=bool(incomplete),
        no_motion=bool(no_motion),
        beat_spiky=bool(spiky and not mute),
        tip_ceiling_degenerate=bool(degen),
        band_borrowed_from_0deg=bool(ft <= 1e-6),
        n_missing=n_miss,
        n_zero_samples=n_zero,
        ac_over_dc=None if empty else float(f"{acdc:.4g}"),
        spike_ratio=None if (spike is None or not np.isfinite(spike))
        else round(spike, 1),
        # ── 잣대 ─────────────────────────────────────────────────────────
        rhythm_share_pct=None if (share is None or mute) else round(share, 1),
        rhythm_null_pct=None if null is None else round(null, 1),
        above_ceiling_energy_pct=None if (frac_above is None or mute)
        else round(frac_above, 1),
        comb_contrast_db=None if comb is None else round(comb, 1),
        beat_hz=None if beat is None else round(beat, 1),
        beat_over_flash=beat_rel,
        moving_power_db=None if mute else round(10.0 * math.log10(p_ac), 2),
        moving_share_pct=None if mute else round(100.0 * p_ac / p_tot, 4),
        # ── 원장 열 — ⭐«비교해도 되는 칸인가» 는 여기서 갈린다 ────────────
        n_poses=n_pose,
        range_m=row.get("range_m"),
        spp=row.get("spp"),
        max_depth=row.get("max_depth"),
        physics=row.get("physics"),
        az_deg=row.get("az_deg"),
        grid_div=row.get("grid_div"),
        npaths_median=row.get("npaths_median"),
        ledger_level_db=row.get("level_db"),
        ledger_beat_hz=(row.get("track") or {}).get("beat_hz"),
    )


# ═══════════════════════════════════════════════════════════════════════════ #
#  그리기
# ═══════════════════════════════════════════════════════════════════════════ #
def nadir_window(rates: dict) -> float:
    """직하방(f_tip = 0)에서 쓸 도플러 창 — 상한이 없으니 **0° 상한의 1/4** 을 빌린다.

    ⚠ 임의의 고정 Hz 를 박으면 기체가 바뀔 때 창이 안 따라온다. 0° 상한에 비례시켜 둔다."""
    return YLIM_FTIP * 0.25 * rates["f_tip0_hz"]


def map_panel(ax, E, f_flash, f_tip, periods, *, dc_removed: bool, ylim=None):
    """맵 한 패널.

    ⭐**보이는 도플러 범위 밖의 빈은 자르고** 넘긴다. gouraud 음영은 격자 칸마다 폴리곤을
    찍는데, 안 보이는 빈까지 넘기면 한 패널에 20 초가 걸린다(2026-08-15 실측: 20.7 초 →
    0.29 초, 70 배). 자르는 것은 **표시 범위 밖**뿐이라 STFT 규약(조각·hop·제로패딩)은
    그대로다 — 220 칸을 굽는 판에서는 이것이 없으면 몇 시간이 걸린다.
    """
    n0, nz = int(round(T0 * PRF)), int(round(TSPAN * PRF))
    x = E[n0:n0 + nz] if E.size >= n0 + nz else E[-nz:] if E.size > nz else E
    if dc_removed:
        x = x - x.mean()                       # ⭐정지 성분 제거 — 움직이는 것만 남는다
    f, t, S, _ = flash_spec(x, PRF, f_flash, periods)
    yl = YLIM_FTIP * f_tip if ylim is None else float(ylim)
    keep = np.abs(f) <= yl * 1.03
    m = draw(ax, t, f[keep], S[keep], f_tip)
    ax.set_ylim(-yl, yl)
    ax.yaxis.set_major_locator(MaxNLocator(nbins=5, symmetric=True))
    ax.tick_params(labelsize=9)
    return m


def corner(ax, txt, *, size=8.6, panel_in=3.05):
    """패널 구석의 글 상자. ⚠**폭 안에 접어** 넣는다 — 안 접으면 상자가 패널 밖으로 새어
    옆 패널을 덮는다(2026-08-15 실측: «still filling up» 세 줄이 오른쪽으로 넘쳤다)."""
    cap = max(18, int((panel_in - 0.22) / (size / 72.0 * 0.60)))
    lines = []
    for ln in str(txt).split("\n"):
        lines += textwrap.wrap(ln, width=cap, break_long_words=False) or [""]
    ax.text(0.035, 0.96, "\n".join(lines), transform=ax.transAxes, color="w",
            fontsize=size, va="top", ha="left", linespacing=1.25,
            bbox=dict(fc="k", alpha=0.58, ec="none", pad=2.0))


def cell_corner(s) -> str:
    """맵 패널 구석의 글 — ⭐**그림 안에서** 잣대의 한계를 말한다.

    왜 이렇게까지 적나 — 그림 한 장만 열어 보는 사람이 대부분이라, 각주가 목차에만 있으면
    «rhythm 0 %» 는 «날개가 없다» 로 읽힌다. 그래서 한 상자 안에 넷을 함께 둔다.

      ① 리듬 몫 + **그 칸의 백색잡음 값**(칸마다 다르다)
      ② 상한 «위» 가 움직이는 에너지의 몇 %인가 — 몫이 낮은 까닭이 여기서 갈린다
      ③ 상한 «아래» 를 보는 대안 잣대(빗살 대비 dB) — 몫이 0 이어도 이것이 크면 날개는 있다
      ④ 박자. 몇 자세가 튀어서 생긴 박자는 그렇다고 적는다.

    ⚠ 수를 낼 자격이 없는 칸(에코 없음 · 덜 참 · 안 움직임)은 **까닭만** 적는다."""
    if s.get("no_return"):
        return "nothing came back\n(the ledger has an empty echo here)"
    if s.get("incomplete"):
        have = int(s.get("n_poses", 0)) - max(int(s.get("n_missing") or 0),
                                              int(s.get("n_zero_samples") or 0))
        return ("still filling up — no numbers\n"
                f"{have:,} of {int(s.get('n_poses', 0)):,} poses are in\n"
                "gaps are zeros — a fake comb")
    if s.get("no_motion"):
        return ("nothing here moves — no numbers\n"
                f"AC/DC {s.get('ac_over_dc'):.0e} = rounding floor\n"
                "(a beat read here is not real)")
    sh, null = s["rhythm_share_pct"], s.get("rhythm_null_pct")
    star = "*" if s["tip_ceiling_degenerate"] else ""
    if sh is None:
        lines = ["rhythm n/a" + star]
    else:
        lines = [f"rhythm {sh:.0f} % above ceiling" + star
                 + (f"  (noise {null:.0f})" if null is not None else "")]
        fa = s.get("above_ceiling_energy_pct")
        if fa is not None:
            lines.append(f"above it: {fa:.0f} % of the moving energy")
    cb = s.get("comb_contrast_db")
    lines.append(f"in-band comb {cb:+.0f} dB (noise 0)" if cb is not None
                 else "in-band comb: band too narrow here")
    if s["beat_hz"] is not None:
        lines.append(f"beat {s['beat_hz']:.0f} Hz = {s['beat_over_flash']:.2f}x"
                     + ("  (spiky)" if s.get("beat_spiky") else ""))
    return "\n".join(lines)


def setup_en(cells: dict, els) -> str:
    """⭐그림 안에 «어디서 잰 판인가» 를 적는다 — 원장 열에서 읽는다.

    ⚠2026-08-15 결함: 비교판이 10 m 팔과 15 m 팔을 아무 표시 없이 나란히 쌓았다.
      원장 _meta 스스로 «거리가 다른 팔을 나란히 놓을 때는 그 사실을 반드시 적는다» 고
      못 박아 둔 규칙을 그림이 깼다. 그래서 거리·자세 수를 제목 옆에 상시로 적는다.
    """
    c = cells[els[0]] if isinstance(els, (list, tuple)) else cells[els]
    bits = []
    if c.get("range_m") is not None:
        bits.append(f"range {float(c['range_m']):g} m")
    if c.get("n_poses"):
        bits.append(f"{int(c['n_poses']):,} poses")
    if c.get("spp"):
        bits.append(f"{int(c['spp']):,} rays")
    if c.get("max_depth"):
        bits.append(f"depth {int(c['max_depth'])}")
    if c.get("grid_div"):
        bits.append(chr(0x03BB) + f"/{int(c['grid_div'])} grid")
    return " · ".join(bits)


def range_of(cells: dict):
    for c in cells.values():
        if c.get("range_m") is not None:
            return float(c["range_m"])
    return None


def fit_title(name: str, width_in: float, base=14.0, floor=8.5):
    """팔 이름을 **폭 안에** 넣는다 — (글자 크기, 줄 목록).

    ⚠2026-08-15 실측 결함: 제목은 `fig.text(...)` 로 14 pt 고정이라 폭 맞춤이 없었다.
      앙각이 한 칸인 팔은 폭이 6.05 in 뿐이라 38 자에서 잘리는데, 하필 잘리는 꼬리가
      `_d1`/`_d3`(반사 깊이)라 **판을 구별해 주는 토막**이 사라졌다. 19 장이 그랬다.
      먼저 글자를 줄여 보고, 그래도 안 들어가면 낱말(밑줄) 단위로 접는다.
    """
    def cap_at(fs):                      # DejaVu Sans Mono 한 글자 = 0.6023 em
        return max(8, int(width_in / (fs / 72.0 * 0.6023)))
    fs = base
    while fs > floor and len(name) > cap_at(fs):
        fs -= 0.5
    if len(name) <= cap_at(fs):
        return fs, [name]
    cap = cap_at(fs)
    lines, cur = [], ""
    for tok in name.split("_"):
        cand = tok if not cur else cur + "_" + tok
        if len(cand) <= cap or not cur:
            cur = cand
        else:
            lines.append(cur + "_")
            cur = tok
    lines.append(cur)
    return fs, lines


def fit_lines(parts, width_in, fontsize=10.5, sep="   |   "):
    """부제를 그림 **폭 안에** 접어 넣는다 — 안 접으면 글자가 그림 밖으로 잘려 나간다.

    ⚠ 토막 하나가 통째로 폭보다 길 수도 있으므로 **낱말 단위로** 다시 접는다
      (2026-08-15 첫 판에서 «…and the rate the» 하고 잘렸다)."""
    cw = 0.0077 * fontsize                      # DejaVu Sans 한 글자 ≈ 0.55 em (여유 있게)
    cap = max(24, int((width_in - 0.25) / cw))
    return textwrap.wrap(sep.join(parts), width=cap, break_long_words=False) or [""]


def legend_cols(labels, width_in, fontsize=10.5) -> int:
    """범례를 몇 칸으로 눕힐까 — **폭 안에 들어가는 가장 넓은 배치**.

    ⚠ 7 개를 무조건 한 줄에 두면 «(nothing came back)» 같은 긴 라벨에서 마지막 항목이
      그림 밖으로 잘린다(2026-08-15 실측). 반대로 가장 긴 라벨 하나로 전 칸을 재면
      멀쩡한 판까지 두 줄로 밀린다. matplotlib 처럼 **칸마다 그 칸의 최대 폭**으로 잰다.
    """
    cw = 0.0077 * fontsize
    w = [len(x) * cw + 0.85 for x in labels]        # 글자 + 선 표본 + 칸 사이
    n = len(w)
    for nc in range(n, 1, -1):
        # matplotlib 의 칸 채우기와 **같은 방식**: 앞쪽 몇 칸이 한 줄 더 길다.
        nr, nlarge = divmod(n, nc)
        sizes = [nr + 1] * nlarge + [nr] * (nc - nlarge)
        total, i = 0.0, 0
        for s in sizes:
            if s:
                total += max(w[i:i + s])
                i += s
        if total <= width_in:
            return nc
    return 1


def _fig_frame(fig, ncol, nrow, pw, ph, *, top_in, bot_in, left_in, right_in,
               wspace=0.38, hspace=0.22):
    """제목·부제·컬러바 자리를 **인치로** 잡는다 — 기본 배치에 맡기면 격자 모양이 바뀔 때마다
    제목이 열 제목 위로 내려앉는다.

    ⚠ wspace 가 좁으면 앙각마다 눈금이 다른 y 축 라벨이 **왼쪽 패널을 침범**한다
      (2026-08-15 첫 판에서 실제로 겹쳤다). 기본값을 넉넉히 둔다."""
    W = left_in + ncol * pw + wspace * pw * (ncol - 1) + right_in
    H = top_in + nrow * ph + hspace * ph * (nrow - 1) + bot_in
    fig.set_size_inches(W, H)
    fig.subplots_adjust(left=left_in / W, right=1.0 - right_in / W,
                        top=1.0 - top_in / H, bottom=bot_in / H,
                        wspace=wspace, hspace=hspace)
    return W, H


def save(fig, path, dpi):
    fig.savefig(path, dpi=dpi)
    plt.close(fig)


# ─────────────────────────────────────────────────────────────────────────── #
#  (a) 한 팔의 맵 격자
# ─────────────────────────────────────────────────────────────────────────── #
def fig_map(arm, els, rates, periods, cells, path, dpi):
    ncol, nrow = len(els), 2
    pw, ph, wsp = 3.05, 2.45, 0.38
    left_in, right_in = 1.60, 1.40
    degen = any(f_tip_at(rates, e) <= 1e-6 for e in els)
    txt_w = ncol * pw + wsp * pw * (ncol - 1) + right_in - 0.15
    sub = fit_lines(
        [f"blade rate {rates['f_flash_hz']:.2f} Hz  ({rates['drone_label']})",
         setup_en(cells, els),
         "white dashes = the blade-tip ceiling",
         "each panel scaled to its own peak"], txt_w)
    #: ⭐각주는 **언제나** 붙인다 — 잣대가 무엇을 못 재는지는 −90° 가 있는 그림만의 이야기가
    #  아니다. 그림 한 장만 여는 사람에게 «rhythm 0 %» 를 물리로 읽히지 않게 하는 자리다.
    foot = fit_lines(
        ["reading the corner: “rhythm” only looks ABOVE the ceiling, where blades "
         "cannot reach — a low number means that strip is quiet, NOT that the blades "
         "are gone. The in-band comb next to it looks BELOW the ceiling, where the "
         "blades actually live (white noise " + chr(0x2248) + " 0 dB)."]
        + (["*  straight down: the blade-tip ceiling is 0 Hz, so the “above the "
            "ceiling” rhythm test degenerates and the Doppler window is borrowed "
            "from the 0" + DEG + " ceiling"] if degen else []), txt_w, fontsize=9.5)
    # ⚠제목은 left_in 자리에서 시작하므로 쓸 수 있는 폭은 **txt_w 그대로**다
    #   (2026-08-15: left_in 을 더해 넘겨 19 장이 그대로 잘렸다 — 눈으로 확인).
    tfs, tlines = fit_title(arm, txt_w)
    top_in = 0.78 + 0.24 * len(sub) + 0.20 * (len(tlines) - 1)
    #: ⚠각주는 **맨 아래에 붙인다** — 위로 올리면 «time [ms]» 축 라벨과 겹친다.
    bot_in = 0.78 + 0.22 * len(foot)
    fig, ax = plt.subplots(nrow, ncol, sharex=True, sharey=(ncol == 1), squeeze=False)
    W, H = _fig_frame(fig, ncol, nrow, pw, ph, top_in=top_in, bot_in=bot_in,
                      left_in=left_in, right_in=right_in, wspace=wsp)
    for c, el in enumerate(els):
        E = series(arm, el)
        ft = f_tip_at(rates, el)
        yl = YLIM_FTIP * ft if ft > 1e-6 else nadir_window(rates)
        for r, dcr in enumerate((False, True)):
            a = ax[r][c]
            map_panel(a, E, rates["f_flash_hz"], ft, periods, dc_removed=dcr, ylim=yl)
            if r == 0:
                a.set_title(deg_txt(el) + ("  *" if ft <= 1e-6 else ""),
                            pad=6, fontsize=13)
                corner(a, r"$f_{\rm tip}$ " + f"{ft:.0f} Hz"
                       + ("*" if ft <= 1e-6 else ""))
            else:
                corner(a, cell_corner(cells[el]))
                a.set_xlabel("time [ms]", fontsize=10)
            if c == 0:
                a.set_ylabel(("as received" if r == 0 else "stationary removed")
                             + "\nDoppler [Hz]", fontsize=11)
    cax = fig.add_axes([1.0 - (right_in - 0.46) / W, bot_in / H,
                        0.11 / W, 1.0 - (top_in + bot_in) / H])
    cb = fig.colorbar(ax[0][0].collections[0], cax=cax)
    cb.set_label("dB below the brightest point in that panel", fontsize=10)
    cb.ax.tick_params(labelsize=9)

    for i, ln in enumerate(tlines):
        fig.text(left_in / W, 1.0 - (0.34 + 0.20 * i) / H, ln, ha="left",
                 va="center", fontsize=tfs, family="monospace")
    y0 = 0.66 + 0.20 * (len(tlines) - 1)
    for i, ln in enumerate(sub):
        fig.text(left_in / W, 1.0 - (y0 + 0.24 * i) / H, ln, ha="left",
                 va="center", fontsize=10.5, color="0.35")
    for i, ln in enumerate(foot):
        fig.text(left_in / W, (0.22 * (len(foot) - i) - 0.10) / H, ln, ha="left",
                 va="center", fontsize=9.5, color="0.35")
    save(fig, path, dpi)


# ─────────────────────────────────────────────────────────────────────────── #
#  (b) 한 팔의 블레이드 대역 에너지
# ─────────────────────────────────────────────────────────────────────────── #
def _el_colors(els):
    cm = plt.get_cmap("turbo")
    if len(els) == 1:
        return {els[0]: "#c62828"}
    return {el: cm(0.06 + 0.88 * i / (len(els) - 1)) for i, el in enumerate(els)}


def fig_band(arm, els, rates, periods, cells, path, dpi):
    ffl = rates["f_flash_hz"]
    cols = _el_colors(els)
    pw, ph, wsp = 6.4, 4.6, 0.10
    left_in, right_in = 1.15, 0.40
    txt_w = 2 * pw + wsp * pw + right_in - 0.15

    # ── 곡선을 **먼저** 다 만든다 ────────────────────────────────────────────
    #    (a) 두 창에 같은 STFT 를 두 번 뜨지 않게, (b) 범례 글자 길이를 알아야 그림
    #    크기를 정할 수 있어서. ⚠아무것도 안 돌아온 칸은 **선을 안 그린다** — 0 을 dB 로
    #    바꾸면 −inf 라 보이지 않는 선이 범례에만 남아 «범례 1:1» 이 깨진다.
    curves, labels = {}, {}
    for el in els:
        ft = f_tip_at(rates, el)
        borrowed = ft <= 1e-6
        ftb = ft if not borrowed else rates["f_tip0_hz"]
        c = cells[el]
        # ⭐수를 낼 자격이 없는 칸은 **선을 안 그린다** — 덜 찬 칸의 0 채움은 PRF/2 에
        #   가짜 선을 세우고, 안 움직이는 칸은 반올림 오차를 봉우리로 세운다.
        why = ("nothing came back" if c.get("no_return") else
               "still filling up" if c.get("incomplete") else
               "nothing moves" if c.get("no_motion") else None)
        fr, Y = (None, None) if why else \
            modspec_curve(series(arm, el), ffl, ftb, periods)
        ok = why is None and fr is not None and np.isfinite(Y).all() \
            and float(Y.max()) > 0.0
        curves[el] = (fr, Y) if ok else None
        labels[el] = deg_txt(el) + (
            f" ({why or 'nothing came back'})" if not ok else
            (" (band borrowed from 0" + DEG + ")" if borrowed else ""))

    sub = fit_lines(
        ["power in the blade band, then how that power beats in time",
         setup_en(cells, els),
         f"dashed lines mark {ffl:.2f} Hz and its multiples — the rate the blades "
         f"of the {rates['drone_label']} should make"]
        + (["straight down has no blade ceiling, so its band is borrowed from 0" + DEG]
           if any(f_tip_at(rates, e) <= 1e-6 for e in els) else []), txt_w)
    # ⚠제목은 left_in 자리에서 시작하므로 쓸 수 있는 폭은 **txt_w 그대로**다
    #   (2026-08-15: left_in 을 더해 넘겨 19 장이 그대로 잘렸다 — 눈으로 확인).
    tfs, tlines = fit_title(arm, txt_w)
    top_in = 0.72 + 0.24 * len(sub) + 0.20 * (len(tlines) - 1)
    ncol_leg = legend_cols([labels[e] for e in els], left_in + txt_w)
    bot_in = 1.00 + 0.26 * math.ceil(len(els) / ncol_leg)
    fig, ax = plt.subplots(1, 2, sharey=True, squeeze=False)
    W, H = _fig_frame(fig, 2, 1, pw, ph, top_in=top_in, bot_in=bot_in,
                      left_in=left_in, right_in=right_in, wspace=wsp)
    ax = ax[0]
    hs, ls_ = [], []
    for j, (lo, hi) in enumerate((BAND_WIDE, BAND_ZOOM)):
        a = ax[j]
        for el in els:
            if curves[el] is None:
                if j == 0:
                    hs.append(Line2D([], [], color=cols[el], ls=":", lw=1.8))
                    ls_.append(labels[el])
                continue
            fr, Y = curves[el]
            m = (fr >= lo) & (fr <= hi)
            drawable = m.sum() >= 2 and float(Y[m].max()) > 0.0
            if drawable:
                ln, = a.plot(fr[m], 10 * np.log10(Y[m] / Y[m].max()),
                             lw=1.8, color=cols[el])
            if j == 0:
                hs.append(ln if drawable else
                          Line2D([], [], color=cols[el], lw=1.8))
                ls_.append(labels[el])
        for k in range(max(1, int(np.ceil(lo / ffl))), int(hi / ffl) + 1):
            a.axvline(k * ffl, color="0.35", ls="--", lw=1.1, zorder=1)
        a.set_xlim(lo, hi)
        a.set_ylim(-52, 4)
        a.set_title("wide, 100 to 1,000 Hz" if j == 0 else "zoom, the first lines",
                    pad=6, fontsize=13)
        a.set_xlabel("modulation rate [Hz]", fontsize=11)
        a.grid(alpha=0.25)
        a.set_axisbelow(True)
        a.tick_params(labelsize=10)
    ax[0].set_ylabel("line level [dB, each curve to its own peak]", fontsize=11)
    if hs:
        # ⚠범례를 축 **안**에 두면 곡선 7 개 중 하나는 반드시 가린다 — 축 밖 아래에 눕힌다.
        fig.legend(hs, ls_, loc="lower center", bbox_to_anchor=(0.5, 0.14 / H),
                   ncol=ncol_leg, frameon=False, fontsize=10.5,
                   handlelength=1.8, columnspacing=2.0)
    for i, ln in enumerate(tlines):
        fig.text(left_in / W, 1.0 - (0.32 + 0.20 * i) / H, ln, ha="left",
                 va="center", fontsize=tfs, family="monospace")
    y0 = 0.62 + 0.20 * (len(tlines) - 1)
    for i, ln in enumerate(sub):
        fig.text(left_in / W, 1.0 - (y0 + 0.24 * i) / H, ln, ha="left",
                 va="center", fontsize=10.5, color="0.35")
    save(fig, path, dpi)


# ─────────────────────────────────────────────────────────────────────────── #
#  주제별 비교판
# ─────────────────────────────────────────────────────────────────────────── #
def _chunks(seq, n):
    return [seq[i:i + n] for i in range(0, len(seq), n)]


def mix_note_en(arms, cells_of) -> str:
    """비교판 부제에 붙는 «이 판에 무엇이 섞였나» 한 줄.

    ⭐거리가 섞이면 반드시 말한다. 10 m 는 matrice4e 의 원거리장 경계(2D²/λ ≈ 14.1 m)
      **안쪽**이라 파면이 표적 위에서 휘고, 그 차이를 엔진 차이로 읽으면 안 된다."""
    rs = sorted({r for a in arms if (r := range_of(cells_of[a])) is not None})
    ps = sorted({int(c["n_poses"]) for a in arms for c in cells_of[a].values()
                 if c.get("n_poses")})
    bits = []
    if len(rs) > 1:
        bits.append("⚠ rows differ in RANGE (" + ", ".join(f"{r:g} m" for r in rs)
                    + ") — each row is labelled with its own")
    if len(ps) > 1:
        bits.append("pose counts differ (" + ", ".join(f"{p:,}" for p in ps) + ")")
    return "   ".join(bits) if bits else "all rows share the same range and pose count"


def _page_txt(i, n) -> str:
    """여러 쪽으로 쪼갠 비교판은 그림 안에 «몇 쪽 중 몇 쪽» 을 적는다 — 한 장만 열어도
    이어지는 판이 더 있다는 것이 보여야 한다(파일 이름 순서만으로는 안 보인다)."""
    return "" if n <= 1 else f"   ({i} of {n})"


def fig_compare_tiles(arms, el, rates_of, periods_of, cells_of, short, path, dpi,
                      topic_en, page=""):
    """앙각이 **하나뿐인** 팔들을 한 장에 타일로 — 스위치 조합판이 이 모양이다."""
    n = len(arms)
    ncol = min(5, n)
    nrow = math.ceil(n / ncol)
    pw, ph, wsp = 3.05, 2.55, 0.16          # 앙각이 같으니 y 축을 공유한다 → 좁아도 안 겹친다
    left_in, right_in = 1.05, 1.40
    degen = any(f_tip_at(rates_of[x], el) <= 1e-6 for x in arms)
    sub = fit_lines(
        ["corner: “rhythm” only looks ABOVE the blade-tip ceiling (a low number means "
         "that strip is quiet, not that the blades are gone); the in-band comb looks "
         "BELOW it, where the blades live",
         "each panel scaled to its own peak — brightness is not comparable between panels",
         mix_note_en(arms, cells_of)]
        + (["*  straight down has no ceiling, so that test degenerates"]
           if degen else []),
        ncol * pw + wsp * pw * (ncol - 1) + right_in - 0.15)
    #: 패널 제목은 «짧은 이름 + 거리» 라 두 줄 이상이 된다 — 그만큼 위를 비운다
    #  (2026-08-15 실측: 안 비우면 부제 마지막 줄이 열 제목을 덮는다).
    titles = {x: fit_title(short[x], pw, base=11.0, floor=7.5) for x in arms}
    tmax = max(len(v[1]) + (0 if range_of(cells_of[x]) is None else 1)
               for x, v in titles.items())
    top_in, bot_in = 0.72 + 0.24 * len(sub) + 0.20 * tmax, 0.70
    fig, ax = plt.subplots(nrow, ncol, sharex=True, sharey=True, squeeze=False)
    W, H = _fig_frame(fig, ncol, nrow, pw, ph, top_in=top_in, bot_in=bot_in,
                      left_in=left_in, right_in=right_in, wspace=wsp)
    for i in range(nrow * ncol):
        a = ax[i // ncol][i % ncol]
        if i >= n:
            a.axis("off")
            continue
        arm = arms[i]
        rt = rates_of[arm]
        ft = f_tip_at(rt, el)
        map_panel(a, series(arm, el), rt["f_flash_hz"], ft, periods_of[arm],
                  dc_removed=True, ylim=YLIM_FTIP * ft if ft > 1e-6
                  else nadir_window(rt))
        rng = range_of(cells_of[arm])
        tfs, tl = titles[arm]
        a.set_title("\n".join(tl) + ("" if rng is None else f"\n{rng:g} m"),
                    pad=5, fontsize=tfs, family="monospace")
        corner(a, cell_corner(cells_of[arm][el]), size=8.2)
        if i % ncol == 0:
            a.set_ylabel("Doppler [Hz]", fontsize=10)
        if i // ncol == nrow - 1:
            a.set_xlabel("time [ms]", fontsize=10)
    cax = fig.add_axes([1.0 - (right_in - 0.46) / W, bot_in / H,
                        0.11 / W, 1.0 - (top_in + bot_in) / H])
    cb = fig.colorbar(ax[0][0].collections[0], cax=cax)
    cb.set_label("dB below the brightest point in that panel", fontsize=10)
    cb.ax.tick_params(labelsize=9)
    fig.text(left_in / W, 1.0 - 0.32 / H,
             f"{topic_en}  —  all at {deg_txt(el)}, stationary echo removed{page}",
             ha="left", va="center", fontsize=14)
    for i, ln in enumerate(sub):
        fig.text(left_in / W, 1.0 - (0.62 + 0.24 * i) / H, ln, ha="left",
                 va="center", fontsize=10.5, color="0.35")
    save(fig, path, dpi)


def fig_compare_rows(arms, els, rates_of, periods_of, cells_of, short, path, dpi,
                     topic_en, page=""):
    """팔을 **세로로 쌓고** 앙각을 가로로 — 기체 3 종·거리 사다리가 이 모양이다."""
    ncol, nrow = len(els), len(arms)
    pw, ph, wsp = 3.05, 2.35, 0.38
    left_in = max(1.45, 0.075 * max(len(short[a]) for a in arms) + 0.85)
    right_in = 1.40
    degen = any(f_tip_at(rates_of[a], e) <= 1e-6 for a in arms for e in els)
    sub = fit_lines(
        ["corner: “rhythm” only looks ABOVE the blade-tip ceiling (a low number means "
         "that strip is quiet, not that the blades are gone); the in-band comb looks "
         "BELOW it, where the blades live",
         "each panel scaled to its own peak — brightness is not comparable between panels",
         mix_note_en(arms, cells_of)]
        + (["*  straight down has no ceiling, so that test degenerates"]
           if degen else []),
        ncol * pw + wsp * pw * (ncol - 1) + right_in - 0.15)
    top_in, bot_in = 0.72 + 0.24 * len(sub), 0.70
    fig, ax = plt.subplots(nrow, ncol, sharex=True, squeeze=False)
    W, H = _fig_frame(fig, ncol, nrow, pw, ph, top_in=top_in, bot_in=bot_in,
                      left_in=left_in, right_in=right_in, wspace=wsp)
    for r, arm in enumerate(arms):
        rt = rates_of[arm]
        for c, el in enumerate(els):
            a = ax[r][c]
            # ⚠열 제목·x 라벨은 **칸이 비어 있어도** 붙인다 — 첫 줄이 빈 팔이면 그 열의
            #   제목이 통째로 사라진다(2026-08-15 실측).
            if r == 0:
                a.set_title(deg_txt(el) + ("  *" if abs(el + 90.0) < 1e-9 else ""),
                            pad=5, fontsize=12)
            if r == nrow - 1:
                a.set_xlabel("time [ms]", fontsize=10)
            if el not in cells_of[arm]:
                # ⚠sharex 격자에서 set_xticks([]) 를 쓰면 **모든 패널**의 눈금이 사라진다.
                #   눈금 자리는 두고 표시만 끈다.
                a.tick_params(which="both", length=0, labelleft=False,
                              labelbottom=False)
                a.set_yticks([])
                for sp in a.spines.values():
                    sp.set_color("0.85")
                a.text(0.5, 0.5, "not in the ledger", transform=a.transAxes,
                       ha="center", va="center", fontsize=10, color="0.55")
                continue
            ft = f_tip_at(rt, el)
            map_panel(a, series(arm, el), rt["f_flash_hz"], ft, periods_of[arm],
                      dc_removed=True,
                      ylim=YLIM_FTIP * ft if ft > 1e-6 else nadir_window(rt))
            corner(a, cell_corner(cells_of[arm][el]), size=8.2)
        # ⭐줄 라벨에 **거리**를 함께 적는다 — 10 m 팔과 15 m 팔이 위아래로 붙어 있어도
        #   어느 줄이 어느 거리인지 그림 한 장 안에서 읽힌다.
        rng = range_of(cells_of[arm])
        ax[r][0].set_ylabel(short[arm] + ("" if rng is None else f"\n{rng:g} m")
                            + "\nDoppler [Hz]", fontsize=9.5, family="monospace")
    first = next((ax[r][c] for r in range(nrow) for c in range(ncol)
                  if ax[r][c].collections), None)
    if first is not None:
        cax = fig.add_axes([1.0 - (right_in - 0.46) / W, bot_in / H,
                            0.11 / W, 1.0 - (top_in + bot_in) / H])
        cb = fig.colorbar(first.collections[0], cax=cax)
        cb.set_label("dB below the brightest point in that panel", fontsize=10)
        cb.ax.tick_params(labelsize=9)
    fig.text(left_in / W, 1.0 - 0.32 / H,
             f"{topic_en}  —  stationary echo removed{page}",
             ha="left", va="center", fontsize=14)
    for i, ln in enumerate(sub):
        fig.text(left_in / W, 1.0 - (0.62 + 0.24 * i) / H, ln, ha="left",
                 va="center", fontsize=10.5, color="0.35")
    save(fig, path, dpi)


def fig_topic_overview(arms, cells_of, short, path, dpi, topic_en):
    """주제 한 장 요약 — 팔 × 앙각의 **리듬 몫[%]** 격자. 비교판을 읽기 전에 보는 지도.

    ⭐2026-08-15 수리 두 가지
      ① **−90° 열은 색을 안 칠한다.** 그 열은 잣대가 퇴화해 «전 대역의 빗살 정도» 를 재는
         다른 수인데, 같은 0~100 색눈금에 올려 두면 한눈에 «직하방이 제일 깨끗하다» 로
         읽힌다(실제로 −90° 평균이 가장 높다). 수는 그대로 적되 회색 빗금으로 덮는다.
      ② **수를 낼 자격이 없는 칸**(덜 참 · 안 움직임 · 에코 없음)은 색도 수도 안 낸다 —
         표식 글자(◐ ○ ∅)만 적는다. 그전에는 절반이 빈 칸이 «0 %» 라는 멀쩡한 수로 찍혔다.
    """
    els = sorted({e for a in arms for e in cells_of[a]}, reverse=True)
    Mx = np.full((len(arms), len(els)), np.nan)
    for i, a in enumerate(arms):
        for j, e in enumerate(els):
            s = cells_of[a].get(e)
            if s and s["rhythm_share_pct"] is not None \
                    and not s.get("tip_ceiling_degenerate"):
                Mx[i, j] = s["rhythm_share_pct"]
    nulls = [s["rhythm_null_pct"] for a in arms for s in cells_of[a].values()
             if s.get("rhythm_null_pct") is not None]
    ttl = f"{topic_en}  —  share of the energy above the blade-tip ceiling that " \
          f"sits on the blade rhythm [%]"
    lab_in = 0.075 * max(len(short[x]) for x in arms) + 0.35
    grid_w = max(0.62 * len(els), 3.0)
    #: ⚠각주 넉 줄과 x 축 라벨이 겹치지 않게 아래를 인치로 잡는다(2026-08-15 실측: 겹쳤다).
    foot_n, bot_in = 4, 0.75 + 0.28 * 4
    W = max(lab_in + grid_w + 1.5, 0.098 * len(ttl) + 0.4)
    H = 0.34 * len(arms) + 0.62 + bot_in + 0.43
    fig, a = plt.subplots(figsize=(W, H))
    fig.subplots_adjust(left=lab_in / W, right=1.0 - 1.20 / W,
                        top=1.0 - 0.62 / H, bottom=bot_in / H)
    im = a.imshow(Mx, cmap="viridis", vmin=0, vmax=100, aspect="auto")
    a.set_xticks(range(len(els)))
    a.set_xticklabels([deg_txt(e) + ("\n*" if abs(e + 90) < 1e-9 else "")
                       for e in els], fontsize=11)
    a.set_yticks(range(len(arms)))
    a.set_yticklabels([short[x] for x in arms], fontsize=9, family="monospace")
    for i, arm in enumerate(arms):
        for j, e in enumerate(els):
            s = cells_of[arm].get(e)
            v = Mx[i, j]
            if s is not None and (np.isnan(v) or s.get("tip_ceiling_degenerate")):
                # 색을 못 믿는 칸 — 빗금으로 덮고 까닭을 글자로
                a.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, fill=True,
                                          facecolor="0.86", edgecolor="0.6",
                                          hatch="///", lw=0.6, zorder=2))
            txt = "—"
            if s is not None:
                if s.get("no_return"):
                    txt = "∅"
                elif s.get("incomplete"):
                    txt = "◐"
                elif s.get("no_motion"):
                    txt = "○"
                elif s["rhythm_share_pct"] is not None:
                    txt = f"{s['rhythm_share_pct']:.0f}" \
                          + ("*" if s.get("tip_ceiling_degenerate") else "")
            a.text(j, i, txt, ha="center", va="center", fontsize=8.5, zorder=3,
                   color="w" if (not np.isnan(v) and v < 55) else "k")
    # ⚠제목을 축 제목으로 두면 가운데 정렬이라 오른쪽 끝이 **컬러바 눈금과 겹친다**.
    fig.text(0.02, 1.0 - 0.30 / H, ttl, ha="left", va="center", fontsize=12.5)
    a.set_xlabel("angle the radar looks down from level", fontsize=11, labelpad=6)
    cax = fig.add_axes([1.0 - 1.02 / W, bot_in / H, 0.16 / W,
                        1.0 - (0.62 + bot_in) / H])
    cb = fig.colorbar(im, cax=cax)
    cb.set_label("[%]", fontsize=10)
    cb.ax.tick_params(labelsize=9)
    nul = (f"white noise reads {min(nulls):.0f}" if nulls and
           max(nulls) - min(nulls) < 0.6 else
           (f"white noise reads {min(nulls):.0f} to {max(nulls):.0f} here — it "
            f"depends on the airframe's blade rate" if nulls else "white noise " +
           chr(0x2248) + " 13"))
    for i, ln in enumerate([
            nul + ".  100 is NOT reachable: real rpm spread smears the lines.",
            "this only scores what sits ABOVE the ceiling — a low number does not "
            "mean the blades are gone (see the in-band comb in each panel).",
            "*  straight down has no ceiling, so that column measures something "
            "else — it is hatched, not coloured, to keep it off this scale.",
            "hatched: ◐ still filling up (poses missing) · ○ nothing moves · "
            "∅ nothing came back · — not in the ledger"][:foot_n]):
        fig.text(0.02, (0.28 * (foot_n - i) - 0.12) / H, ln, ha="left",
                 va="center", fontsize=9.0, color="0.35")
    save(fig, path, dpi)


# ═══════════════════════════════════════════════════════════════════════════ #
#  구움
# ═══════════════════════════════════════════════════════════════════════════ #
def fresh(path: str, force: bool) -> bool:
    """이미 있고 **원장·이 코드보다** 새 그림이면 True(= 건너뛴다)."""
    return (not force) and os.path.exists(path) and \
        os.path.getmtime(path) >= FRESH_AFTER


def main():
    ap = argparse.ArgumentParser(description="앙각 스윕 원장의 모든 팔을 그림으로 굽는다")
    ap.add_argument("--force", action="store_true", help="이미 있는 그림도 다시 굽는다")
    ap.add_argument("--topics", nargs="*", default=None,
                    help="이 주제만 (base switch airframe azimuth parts range ptd grid planewave)")
    ap.add_argument("--arms", nargs="*", default=None, help="이 팔만")
    ap.add_argument("--no-compare", action="store_true", help="주제별 비교판을 건너뛴다")
    ap.add_argument("--dpi", type=int, default=130)
    ap.add_argument("--compare-dpi", type=int, default=110,
                    help="비교판은 판이 커서 해상도를 조금 낮춘다(파일 크기)")
    ap.add_argument("--rows-per-page", type=int, default=7,
                    help="비교판 한 쪽에 쌓는 팔 수")
    a = ap.parse_args()

    os.makedirs(OUTDIR, exist_ok=True)
    plt.rcParams.update({"figure.facecolor": "white", "savefig.facecolor": "white",
                         "figure.max_open_warning": 0})

    all_arms = discover_cells()
    topics: dict[str, list[str]] = {}
    for arm in all_arms:
        topics.setdefault(topic_of(arm), []).append(arm)
    order = sorted(topics, key=lambda s: (topic_rank(s), s))
    unknown = [s for s in order if s not in TOPIC_ORDER]

    if a.topics:
        order = [s for s in order if s in a.topics]
    keep_arms = set(a.arms) if a.arms else None

    n_cells = sum(len(all_arms[x]) for s in order for x in topics[s]
                  if keep_arms is None or x in keep_arms)
    print(f"═══ 마이크로도플러 아틀라스 ═══")
    print(f"  원장   {os.path.relpath(LED_J, ROOT)}  ·  팔 {len(all_arms)} · "
          f"칸 {sum(len(v) for v in all_arms.values())}")
    print(f"  이번   주제 {len(order)} · 칸 {n_cells}   →  "
          f"{os.path.relpath(OUTDIR, ROOT)}/")
    print(f"  주제   " + " · ".join(f"{s}({len(topics[s])})" for s in order))
    print()

    index = {
        "_meta": {
            "generator": "benchmark/build_md_atlas.py",
            "ledger": os.path.relpath(LED_J, ROOT),
            "ledger_mtime": LEDGER_MTIME,
            "code_mtime": CODE_MTIME,
            "built_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "figdir": os.path.relpath(OUTDIR, ROOT),
            "prf_hz": PRF, "fc_hz": FC,
            "drone_default": DRONE_DEFAULT,
            "range_m_primary": RANGE_PRIMARY,
            "stft_ko": "md_mapstyle.flash_spec — 블레이드 주기의 auto_periods 배 조각 · "
                       "hop 2 · 8× 제로패딩. 마이크로도플러 표현은 STFT 만 쓴다.",
            "map_window_ko": f"맵은 {T0*1e3:.0f} ms 부터 {TSPAN*1e3:.0f} ms 창.",
            "level_rule_ko": "⭐레벨(dB)·리듬 몫·박자는 전부 정지 성분(시계열 평균) 제거 후에 잰다.",
            "airframe_rule_ko": "⚠기체 태그(_mini5pro_ 등)가 붙은 팔은 그 기체의 박자"
                                "(날개수 × 호버rpm/60)로 잣대를 세운다. 원장 _meta.f_flash_hz "
                                "는 기본 기체 값이라 그대로 쓰면 틀린다.",
            "nadir_rule_ko": "⚠앙각 −90° 는 f_tip = 0 이라 «날개끝 상한 위» 잣대가 퇴화한다"
                             "(tip_ceiling_degenerate). 대역은 0° 것을 빌린다"
                             "(band_borrowed_from_0deg).",
            "rhythm_ko": "리듬 몫[%] — 상한 위 AC 에너지 중 박자의 정수배(±8 Hz)에 붙은 몫. "
                         "⛔이 잣대는 «상한 위» 만 본다 — 날개 무늬가 상한 아래에 그대로 "
                         "있어도 0 % 가 나온다. 0 % 는 «리듬이 없다» 가 아니라 «이 자리에선 "
                         "못 읽는다» 이다. 널(백색잡음 값)은 칸마다 다르므로 "
                         "cells[*].rhythm_null_pct 를 쓴다(matrice4e ≈ 12.6 · s1000plus ≈ 10.8 "
                         "· mini5pro ≈ 8.7). 천장 100 은 도달 불가다 — 실제 rpm 산포가 선을 "
                         "번지게 한다.",
            "comb_ko": "빗살 대비[dB] — ⭐리듬 몫의 짝. 상한 **아래**(2·f_flash ~ f_tip)에서 "
                       "«정수배 자리» ÷ «정수배 사이 자리» 전력비. 백색잡음 ≈ 0 dB, 우리 커널 "
                       "15 m 정면 ≈ +48 dB, 같은 자리 PathSolver ≈ −0.8 dB. 상한 위가 비어 "
                       "리듬 몫이 0 이어도 이 수는 살아 있다 — «못 읽음» 과 «없음» 을 가른다. "
                       "대역에 배음이 3 개도 안 들어가면(낮은 앙각·직하방) 정의되지 않는다.",
            "mute_ko": "⭐수를 낼 자격이 없는 칸은 값을 None 으로 낸다 — no_return(에코 0) · "
                       "incomplete(자세가 덜 찼다: 원장 n_missing 또는 시계열 안의 0 표본) · "
                       "no_motion(AC/DC < 1e-12 = 반올림 바닥). 덜 찬 칸은 빈 자리가 0 으로 "
                       "채워져 스펙트럼이 PRF/2·PRF/4 에 복제되고 그 복제본이 «상한 위» 를 "
                       "삼켜 리듬 몫을 0 % 로 만든다 — 물리가 아니라 결측 자국이다.",
            "spike_ko": "spike_ratio = |AC| 의 최대÷중앙. 100 을 넘으면 beat_spiky 를 세운다 — "
                        "몇 자세가 통째로 튄 것이라 그 «박자» 는 회전이 아니라 튐의 간격이다.",
            "beat_window_ko": "⚠박자는 **전 구간**(자세 전부)으로 재고, 맵 그림은 20~80 ms "
                              "창만 그린다 — 같은 상자의 두 수가 다른 구간에서 나온 수다.",
            "topics_ko": {s: TOPIC_LABEL.get(s, (s, s))[1] for s in topics},
        },
        "topics": {},
    }

    t_start = time.time()
    done = 0
    for ti, slug in enumerate(order, start=1):
        arms = sorted(topics[slug])
        if keep_arms is not None:
            arms = [x for x in arms if x in keep_arms]
        if not arms:
            continue
        en, ko = TOPIC_LABEL.get(slug, (slug, slug))
        pre = topic_prefix(slug, unknown)
        short = short_labels(sorted(topics[slug]))
        print(f"── [{ti}/{len(order)}] {slug}  ({len(arms)} 팔)  {ko}")

        rates_of, periods_of, cells_of = {}, {}, {}
        tinfo = {"label_en": en, "label_ko": ko, "order": topic_rank(slug),
                 "n_arms": len(topics[slug]), "arms": {}, "compare": []}

        for ai, arm in enumerate(arms, start=1):
            els = all_arms[arm]
            rt = arm_rates(arm)
            per = auto_periods(PRF, rt["f_flash_hz"])
            rates_of[arm], periods_of[arm] = rt, per
            cells = {el: cell_summary(arm, el, rt, per) for el in els}
            cells_of[arm] = cells

            p_map = os.path.join(OUTDIR, f"{pre}__{arm}__map.png")
            p_bnd = os.path.join(OUTDIR, f"{pre}__{arm}__band.png")
            t0 = time.time()
            tags = []
            if fresh(p_map, a.force):
                tags.append("map=skip")
            else:
                fig_map(arm, els, rt, per, cells, p_map, a.dpi)
                tags.append("map")
            if fresh(p_bnd, a.force):
                tags.append("band=skip")
            else:
                fig_band(arm, els, rt, per, cells, p_bnd, a.dpi)
                tags.append("band")
            done += len(els)
            print(f"   [{ai:2d}/{len(arms)}] {arm:52s} el {len(els)}  "
                  f"{'·'.join(tags):18s} {time.time()-t0:5.1f}s   "
                  f"({done}/{n_cells} 칸)", flush=True)

            tinfo["arms"][arm] = {
                "topic": slug,
                "figures": {"map": os.path.relpath(p_map, ROOT),
                            "band": os.path.relpath(p_bnd, ROOT)},
                "airframe": rt["drone"],
                "airframe_tagged": rt["tagged"],
                "airframe_label": rt["drone_label"],
                "f_flash_hz": round(rt["f_flash_hz"], 3),
                "f_tip0_hz": round(rt["f_tip0_hz"], 1),
                "stft_periods": per,
                "elevations_deg": els,
                "cells": {f"{el:+.0f}": cells[el] for el in els},
            }

        # ⭐주제가 «무엇을 섞고 있나» 를 색인에 싣는다 — 갤러리·목차가 이것으로
        #   «같은 자리인데 엔진만 갈렸다» 같은 거짓 전제를 못 쓰게 한다.
        tinfo["ranges_m"] = sorted({float(c["range_m"])
                                    for x in cells_of.values() for c in x.values()
                                    if c.get("range_m") is not None})
        tinfo["n_incomplete"] = sum(1 for x in cells_of.values() for c in x.values()
                                    if c.get("incomplete"))
        tinfo["n_no_return"] = sum(1 for x in cells_of.values() for c in x.values()
                                   if c.get("no_return"))
        tinfo["n_no_motion"] = sum(1 for x in cells_of.values() for c in x.values()
                                   if c.get("no_motion"))

        # ── 주제별 비교판 ────────────────────────────────────────────────
        if not a.no_compare and len(arms) > 1:
            p_ov = os.path.join(OUTDIR, f"{pre}__000-overview-rhythm.png")
            if not fresh(p_ov, a.force):
                fig_topic_overview(arms, cells_of, short, p_ov, a.dpi, en)
            tinfo["compare"].append(os.path.relpath(p_ov, ROOT))
            print(f"   overview  →  {os.path.basename(p_ov)}")

            # ── 앙각이 **하나뿐인** 팔들은 그 앙각별로 타일 한 장 ─────────────
            #    (스위치 조합 20 개가 전부 −30° 한 점이라 이 길로 한 장에 들어간다)
            singles: dict[float, list[str]] = {}
            rest = []
            for arm in arms:
                (singles.setdefault(all_arms[arm][0], []) if len(all_arms[arm]) == 1
                 else rest).append(arm)
            for el, grp in sorted(singles.items(), reverse=True):
                if len(grp) < 2:            # 혼자면 아래 «쌓기» 판에 합류시킨다
                    rest.extend(grp)
                    continue
                pages = _chunks(sorted(grp), 20)
                for pi, page in enumerate(pages, start=1):
                    p = os.path.join(OUTDIR, f"{pre}__01-compare-tile"
                                             f"{el:+.0f}-p{pi}.png")
                    if not fresh(p, a.force):
                        fig_compare_tiles(page, el, rates_of, periods_of,
                                          cells_of, short, p, a.compare_dpi, en,
                                          page=_page_txt(pi, len(pages)))
                    tinfo["compare"].append(os.path.relpath(p, ROOT))
                    print(f"   compare   →  {os.path.basename(p)}  "
                          f"({len(page)} 팔 @ {deg_txt(el)})", flush=True)
            # ── 나머지는 **세로로 쌓아** 앙각을 가로로 편다 ────────────────
            #    앙각 구성이 갈리면 합집합을 쓰고, 원장에 없는 칸은 그렇다고 적는다.
            rest = sorted(set(rest))
            if len(rest) >= 2:
                uni = sorted({e for x in rest for e in all_arms[x]}, reverse=True)
                pages = _chunks(rest, a.rows_per_page)
                for pi, page in enumerate(pages, start=1):
                    p = os.path.join(OUTDIR, f"{pre}__02-compare-stack-p{pi}.png")
                    if not fresh(p, a.force):
                        fig_compare_rows(page, uni, rates_of, periods_of,
                                         cells_of, short, p, a.compare_dpi, en,
                                         page=_page_txt(pi, len(pages)))
                    tinfo["compare"].append(os.path.relpath(p, ROOT))
                    print(f"   compare   →  {os.path.basename(p)}  "
                          f"({len(page)} 팔 × 앙각 {len(uni)})", flush=True)

        index["topics"][pre] = tinfo
        print()

    # 목차 JSON — 부분 실행이면 기존 것과 합친다(주제별로 나눠 돌릴 수 있게)
    if (a.topics or a.arms) and os.path.exists(INDEX):
        old = json.load(open(INDEX))
        merged = old.get("topics", {})
        for k, v in index["topics"].items():
            if k in merged and a.arms:
                merged[k]["arms"].update(v["arms"])
                merged[k]["compare"] = v["compare"] or merged[k].get("compare", [])
            else:
                merged[k] = v
        index["topics"] = dict(sorted(merged.items()))
    index["_meta"]["n_topics"] = len(index["topics"])
    index["_meta"]["n_arms"] = sum(len(t["arms"]) for t in index["topics"].values())
    index["_meta"]["n_cells"] = sum(len(x["cells"]) for t in index["topics"].values()
                                    for x in t["arms"].values())
    index["_meta"]["n_figures"] = sum(len(x["figures"]) for t in index["topics"].values()
                                      for x in t["arms"].values()) \
        + sum(len(t["compare"]) for t in index["topics"].values())
    json.dump(index, open(INDEX, "w"), ensure_ascii=False, indent=1)

    n_png = len([f for f in os.listdir(OUTDIR) if f.endswith(".png")])
    print(f"═══ 끝  {(time.time()-t_start)/60:.1f} 분 ═══")
    print(f"  그림   {n_png} 장  →  {os.path.relpath(OUTDIR, ROOT)}/")
    print(f"  목차   {os.path.relpath(INDEX, ROOT)}  "
          f"(주제 {index['_meta']['n_topics']} · 팔 {index['_meta']['n_arms']} · "
          f"칸 {index['_meta']['n_cells']})")


if __name__ == "__main__":
    main()
