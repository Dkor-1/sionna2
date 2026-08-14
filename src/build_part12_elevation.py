# -*- coding: utf-8 -*-
"""
build_part12_elevation.py — 권 16 「앙각 커버리지」의 조각들 → reports/_parts/8N_*.ipynb
==========================================================================================
권 16 은 관측 앙각을 0° 에서 −90° 까지 내리며 같은 표적을 재고, 커버리지를 정하는 것이
표적이 아니라 **분석 대역과 잣대**임을 보인다. 절 편성은
`outputs/volumes_16_17_plan.json` 이 정본이다.

    78 el-sweep-design      스윕 규약과 인용해도 되는 행
    79 el-band-tracking     대역을 f_tip 따라 옮기면 −75° 까지 산다
    80 el-above-tip-limit   ⭐이 파일이 짓는 절 — 물리 상한 위로 새는 에너지(새 잣대)
    81 el-beat-vs-tip       박자·굴러떨어짐
    82 el-nadir-floor       나딧 잔여의 정체

⚠ 조각 80 의 **앵커가 계획과 다르다.** 계획의 (권 16 · 절 3) 칸은 `el-prediction-gap`
  이었는데, 이 자리에 배정된 내용이 «물리 상한 위 누설» 로 바뀌었다. 번호 80 은 계획의
  권·절 지도를 그대로 두고, 앵커와 제목만 내용에 맞춰 `el-above-tip-limit` 으로 적는다
  (아래 `EXTRA` 가 그 한 행이다). 형제 조각이 `el-prediction-gap` 으로 거는 링크는
  이 앵커로 바꿔야 한다.

⭐ 조각(`reports/_parts/`)은 **사람이 직접 읽는 문서가 아니다.** 숫자를 원장에서 주입하는
   층이고, `src/build_volumes.py` 가 이 조각들을 이어 권 `reports/16_elevation-coverage.ipynb`
   를 짓는다(각주 재번호·상호참조 재배선·머리말은 그쪽이 한다).

⚠ 같은 권의 다른 절을 짓는 사람은 **자기 함수만** 이 파일에 덧붙인다 —
  `REPORTS` 목록에 자기 행 하나를 더하고 `blocks_8N()` 을 새로 쓴다.

실행
    cd /workspace/sionna
    PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python src/build_part12_elevation.py

⚠ GPU 도 Sionna 도 필요 없다 — 원장 JSON 을 읽어 노트북을 조립할 뿐이다.
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (_HERE, os.path.join(_ROOT, "benchmark")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from report_style import (ContractError, assert_fig_text, build_notebook,  # noqa: E402
                          caption, from_json, header, md, next_steps, table,
                          table_from)

OUT = os.path.join(_ROOT, "reports", "_parts")   # ⭐조각이 사는 곳
FIG = "../outputs/figures"                        # ⭐권(reports/) 기준 상대경로
_SHARD_DIR = os.path.join(_ROOT, "outputs", "reports_index")
_PLAN = os.path.join(_ROOT, "outputs", "volumes_16_17_plan.json")
_EXEC = os.path.join(_ROOT, "outputs", "restruct_exec_plan.json")

#: 색인 샤드의 부 번호 — `outputs/volumes_16_17_plan.json : part_shard_schema.part_value`.
SHARD_PART = 12
SHARD_PART_NAME = "앙각·물리 스위치"

#: 이 라운드가 계획 밖에서 이름을 새로 붙인 조각(위 ⚠ 참조).
#  제목은 노트북 H1 과 **글자 하나까지 같아야** 한다(색인의 title-mismatch 검사).
TITLE_80 = ("물리 상한 위 누설은 우리 팔 0.22~17.18 %, 스톡 PathSolver 0.81~96.17 % "
            "이고, 물리를 켜면 여섯 앙각이 전부 78 % 위다")
EXTRA = {"el-above-tip-limit": ("80", TITLE_80)}


# --------------------------------------------------------------------------- #
#  앵커 해결기 — 새 조각은 편성 계획, 옛 조각은 실행 계획이 정본이다
# --------------------------------------------------------------------------- #
def _registry() -> dict:
    reg: dict[str, tuple[str, str]] = {}
    with open(_EXEC, encoding="utf-8") as f:                 # 00~76 옛 조각
        reg.update({r["anchor"]: (str(r["no"]), r["title_ko"])
                    for r in json.load(f)["reports"]})
    with open(_PLAN, encoding="utf-8") as f:                 # 78~87 새 조각
        reg.update({p["anchor"]: (str(p["no"]), p["title"])
                    for p in json.load(f)["parts"]})
    reg.update(EXTRA)
    return reg


REG = _registry()


def ref(anchor: str, short: str | None = None) -> str:
    """형제 조각으로 가는 링크. 권으로 묶일 때 `build_volumes.py` 가 절 번호로 다시 배선한다."""
    if anchor not in REG:
        raise ContractError(f"모르는 앵커: {anchor!r} — 편성 계획에 없다")
    no, title = REG[anchor]
    # ⭐«편 NN» 꼴로 낸다 — `build_volumes._XREF` 가 그 꼴만 권·절 주소로 다시 배선한다.
    return f"[편 {no} «{short or title}»]({no}_{anchor}.ipynb)"


# --------------------------------------------------------------------------- #
#  원장 — 전부 읽기 전용
# --------------------------------------------------------------------------- #
#: ⭐2026-08-13 재설계 — 이 권이 서술하는 판은 **15 m**(원거리장 밖)다. 파생 원장도
#  같은 판으로 다시 구웠다. 10 m 옛 판은 꼬리 없는 파일로 그대로 남아 있다.
WJ = "outputs/wideband_energy_r15.json"
W = from_json(WJ)                                    # ⭐물리 상한 위 누설(이 절의 본체)
S = from_json("outputs/elevation_sweep_md.json")     # 앙각 스윕 원장(규약·완결성)


def row(engine: str, el_deg: float, *, complete: bool = True) -> str:
    """`rows[i]` 의 i 를 (엔진, 앙각)으로 찾아 준다 — 병합마다 인덱스가 밀리기 때문이다."""
    for i, r in enumerate(S.get("rows")):
        if r.get("engine") != engine or abs(float(r.get("el_deg")) - el_deg) > 1e-9:
            continue
        if complete and r.get("n_missing"):
            continue
        return f"rows[{i}]"
    raise ContractError(f"찾는 행이 없다 — engine={engine!r}, el={el_deg}")


# =========================================================================== #
#  조각 80 — 권 16 절 3 「물리 상한 위 누설이 엔진을 가른다」
# =========================================================================== #
ELS = (0.0, -15.0, -30.0, -45.0, -60.0, -75.0)
#: ⭐세 팔은 **같은 광선 예산(40 억 발)** 을 쓴다. 갈리는 축은 «엔진» 과 «물리 스위치» 뿐이다.
K_OURS = "ours_r15_n8192"                              # 우리 커널 (SBR + PO)
K_OFF = "sionna_p4000000000_r15_n8192_d1"              # PathSolver, 물리 스위치 끔
K_ON = "sionna_p4000000000_phys_r15_n8192_d1"          # PathSolver, 물리 스위치 켬, 깊이 1
K_ON2 = "sionna_p4000000000_phys_r15_n8192_d2"         # 같은 팔, 깊이 2
ARMS = ((K_OURS, "우리 커널"), (K_OFF, "PathSolver 물리 끔"), (K_ON, "PathSolver 물리 켬"))


def leak(arm: str, el: float) -> str:
    """상한 위 에너지 몫 한 칸 — 몫(0~1)을 백분율 표기로 낸다."""
    return W.num(f"cells.{arm}/el{el:+.0f}.above_f_tip_frac", fmt="{:.2%}")


def inband(arm: str, el: float) -> str:
    """대역 안(500 Hz ~ f_tip) 몫 한 칸 [dB]."""
    return W.num(f"cells.{arm}/el{el:+.0f}.500-f_tip", fmt="{:.2f}", unit="dB")


#: 격자 축 — 같은 표적·같은 앙각에서 격자 간격만 바꾼 사다리.
WG = from_json("outputs/sbr_grid_convergence.json")


def sat(el: float) -> str:
    """평평한 스펙트럼이 받는 점수 — 상한 위 대역이 관찰 대역에서 차지하는 폭의 몫."""
    nyq = float(W.get("_meta.nyquist_hz"))
    ftip = float(W.get(f"cells.{K_OURS}/el{el:+.0f}.f_tip_hz"))
    return (f"{(nyq - ftip) / nyq:.2%} ⟨{WJ} : "
            f"_meta.nyquist_hz → cells.{K_OURS}/el{el:+.0f}.f_tip_hz 를 빼고 나눈 값⟩")


def leak_phys(arm: str, el: float) -> str:
    """물리 스위치를 켠 팔의 상한 위 누설 한 칸.

    ⭐새 판에서는 물리를 켠 팔도 **같은 원장·같은 예산**에 있어 `leak` 과 한 곳에서 읽는다.
    """
    return leak(arm, el)


def _assert_title_numbers() -> None:
    """제목의 네 숫자는 손으로 친 자리다 — 원장에서 다시 계산해 **대조**한다.

    (제목은 `num()` 을 못 쓴다. 그래서 여기서 막는다: 원장이 바뀌면 빌드가 멈춘다.)
    """
    def f(arm: str, el: float) -> float:
        return float(W.get(f"cells.{arm}/el{el:+.0f}.above_f_tip_frac"))

    ours = [f(K_OURS, e) for e in ELS]
    path = [f(a, e) for a in (K_OFF, K_ON) for e in ELS]
    want = [format(min(ours), ".2%"), format(max(ours), ".2%"),
            format(min(path), ".2%"), format(max(path), ".2%")]
    missing = [w for w in want if w.rstrip("%") not in TITLE_80]
    if missing:
        raise ContractError(
            f"제목의 숫자가 원장과 어긋난다 — 원장이 말하는 값: {want}\n"
            f"  제목: {TITLE_80!r}\n  → 제목을 원장 값으로 고쳐라.")


_assert_title_numbers()


REPRO_80 = dict(
    cmd=['WB_TAG=_r15 WB_ARMS="ours_r15_n8192|Ours (SBR+PO)|tab:blue;'
         'sionna_p4000000000_r15_n8192_d1|PathSolver physics off|tab:orange;'
         'sionna_p4000000000_phys_r15_n8192_d1|PathSolver physics on|tab:red" '
         "PYTHONPATH=src:benchmark python benchmark/build_wideband_energy_fig.py",
         "(같은 환경변수) PYTHONPATH=src:benchmark python "
         "benchmark/build_above_tip_fig.py"],
    out=["outputs/wideband_energy_r15.json",
         "outputs/figures/ch1_f6_above_tip_r15.png"],
    runtime="그림 0.95 초 (CPU 전용) · 원장 재생성은 미측정",
    note="시계열은 `outputs/elevation_sweep_md.npz` 에서 읽는다. 팔의 완결성은 "
         "`outputs/elevation_sweep_md.json` 의 `n_missing` 이 정한다")

_R_OURS0 = row(K_OURS, 0.0)


def blocks_80() -> list:
    return [
        header(
            num=80,
            title=TITLE_80,
            did="광선 예산이 같은 세 팔 여섯 앙각에서 날개끝 속도가 정하는 상한 위 대역의 "
                "에너지 몫을 재고, 엔진과 물리 스위치를 가르는 잣대로 삼았다.",
            results=[
                f"상한은 f_tip = {W.num('_meta.f_tip_el0_hz', fmt='{:.1f}', unit='Hz')} × "
                f"cos(el) 이고 관찰 상한은 나이퀴스트 "
                f"{W.num('_meta.nyquist_hz', fmt='{:.0f}', unit='Hz')} 다 — el 0° 에서 "
                f"순시 도플러가 닿는 폭은 관찰 대역의 {sat(0.0)} 를 남긴다.",

                f"우리 팔의 누설은 el −75° 의 {leak(K_OURS, -75.0)} 에서 el −15° 의 "
                f"{leak(K_OURS, -15.0)} 사이다 — f_tip 이 0 보다 큰 여섯 앙각의 값이다.",

                f"물리를 끈 PathSolver 는 el −45° 의 {leak(K_OFF, -45.0)} 에서 el 0° 의 "
                f"{leak(K_OFF, 0.0)} 사이로, 큰 값이 el 0° 한 자리에 몰린다.",

                f"⭐물리를 켠 PathSolver 는 여섯 앙각이 **전부** el −45° 의 "
                f"{leak(K_ON, -45.0)} 위이고, el −75° 에서 {leak(K_ON, -75.0)} 다 — "
                f"움직이는 에너지의 대부분이 날개가 낼 수 없는 자리에 있다.",

                f"이 잣대의 위 끝은 포화점이다 — el 0° 에서 평평한 스펙트럼이 받는 점수가 "
                f"{sat(0.0)} 이고 물리를 켠 팔의 {leak(K_ON, 0.0)} 가 그 근처다.",
            ],
            method=[
                ("상한의 정의",
                 "f_tip = 2·(2π f_rev R)/λ · cos(el) — `benchmark/elevation_sweep_md.py:205` "
                 "의 `f_tip_at()` 한 곳에 있다"),
                ("표적의 운동",
                 "기체는 15 m 한 자리에 고정하고 회전자 위상만 시간에 따라 돌린다 — "
                 "`benchmark/elevation_sweep_md.py:105` 의 `rotor_phases()`"),
                ("팔 사이 공정성",
                 "세 팔이 **광선 40 억 발**로 같다. 갈리는 축은 엔진과 물리 스위치뿐이다"),
                ("누설 몫",
                 "자세 시계열의 슬로타임 FFT(한나 창)에서 |f| ≥ f_tip 전력 ÷ 전체 전력 — "
                 "`benchmark/build_wideband_energy_fig.py:133`"),
                ("정규화",
                 "팔마다 자기 전체 전력으로 나눈 몫이라 팔 사이 절대 레벨은 이 표 밖이다"),
                ("행 선택",
                 "`n_missing = 0` 인 행만 쓴다 — 원장이 부분 병합 행을 미리 뺐다"),
            ],
            prereq=[
                (ref("el-sweep-design", "스윕 규약"),
                 "이 스윕이 무엇을 어떤 규약으로 쟀고 어느 행을 인용해도 되나"),
                (ref("el-band-tracking", "대역 추적"),
                 "대역을 앙각마다 f_tip 으로 옮겨 잡는 규약"),
            ],
            repro=REPRO_80,
        ),

        md("## 상한은 날개끝 속도가 긋는다", "",
           "회전자 날개끝이 시선 방향으로 내는 속도가 **순시 도플러**의 상한을 정한다. 그 "
           "상한이 f_tip 이고, 앙각이 내려가면 날개 속도가 시선에 수직해지면서 cos(el) 로 "
           "줄어든다 — el 0° 에서 "
           f"{W.num(f'cells.{K_OURS}/el+0.f_tip_hz', fmt='{:.1f}', unit='Hz')}, 직하방에서 "
           f"{W.num(f'cells.{K_OURS}/el-90.f_tip_hz', fmt='{:.1f}', unit='Hz')} 다.", "",
           "관찰 상한은 그와 무관하게 표본율이 정한다 — PRF "
           f"{W.num('_meta.prf_hz', fmt='{:.0f}', unit='Hz')} 의 절반인 나이퀴스트 "
           f"{W.num('_meta.nyquist_hz', fmt='{:.0f}', unit='Hz')} 다.", "",
           f"⇒ el 0° 에서 순시 도플러가 닿는 폭 밖에 남는 자리는 관찰 대역의 {sat(0.0)} 이고, "
           f"직하방에서는 {sat(-90.0)} 다. 원장은 그 자리를 인공물로 적는다"
           f"⟨{WJ} : _meta.physical_limit_ko⟩."),

        md("그 «인공물» 을 0 이 참값인 자리로 읽는 것은 이 잣대가 서는 범위 **밖**이다. "
           "f_tip 은 순시 주파수의 상한이지 스펙트럼이 끊기는 자리가 아니다 — 회전 날개의 "
           "위상변조 측대역은 그 위로 이어진다. 그래서 이상적인 날개도 상한 위에 작은 양수를 "
           "남긴다.", "",
           f"상한선의 정밀도도 여기까지다. f_tip 은 호버 회전수 한 값으로 긋는데 이 스윕의 "
           f"네 로터는 «{S.num('_meta.rotor_ko')}» 로 돌아, 가장 빠른 로터의 순시 상한은 "
           f"el 0° 에서 f_tip 보다 몇 Hz 위에 있다.", "",
           "⇒ 이 절은 상한 위 몫을 **같은 앙각에서 팔끼리 견주는 상대 잣대**로 쓴다. 바닥이 "
           "0 인 절대 눈금으로 올리려면 진폭변조를 포함한 참조 신호로 물리 꼬리를 먼저 빼야 "
           "하고, 그 빼기는 다음 단계 표의 첫 줄이다."),

        md("### 이 절의 세팅", "",
           table(["설정", "값"], [
               ["표적", S.num("_meta.drone")],
               ["거리", S.num("_meta.range_m_primary", fmt="{:.1f}", unit="m")],
               ["PRF", W.num("_meta.prf_hz", fmt="{:.0f}", unit="Hz")],
               ["자세 표본", S.num(f"{_R_OURS0}.n_poses", fmt="{:.0f}", unit="개")],
               ["격자", S.num("_meta.grid_ko")],
               ["빠진 행", W.num("_meta.incomplete_excluded_ko")],
           ])),

        md(f"![above tip limit]({FIG}/ch1_f6_above_tip_r15.png)", "",
           caption(1, "물리적으로 블레이드가 닿을 수 없는 대역에 어느 팔이 얼마를 "
                      "남기는가?"), "",
           "(a) 는 상한이 앙각을 따라 어디에 그어지는지, (b) 는 그 위에 팔마다 얼마가 "
           "놓이는지다. (b) 의 모든 막대는 참값이 0 이다."),

        md("## 세 팔이 상한 위에 남기는 몫", "",
           table(["앙각", "f_tip", "우리 커널", "PathSolver 물리 끔", "PathSolver 물리 켬"],
                 [[f"{el:+.0f}°",
                   W.num(f"cells.{K_OURS}/el{el:+.0f}.f_tip_hz", fmt="{:.1f}", unit="Hz"),
                   leak(K_OURS, el), leak(K_OFF, el), leak(K_ON, el)] for el in ELS])),

        md("## 이 잣대가 대역 안 에너지와 다른 점", "",
           f"대역 안(`500 Hz` 부터 f_tip 까지) 몫은 el 0° 에서 우리 {inband(K_OURS, 0.0)}, "
           f"물리 끔 {inband(K_OFF, 0.0)}, 물리 켬 "
           f"{inband(K_ON, 0.0)} 로 갈린다. 셋 중 무엇이 참인지는 표적의 "
           "산란과 조명 기하가 정하고, 그 참값은 이 원장 밖에 있다.", "",
           "상한 위의 참값도 같은 것이 정한다 — 날개 위 진폭 분포가 위상변조 꼬리의 크기를 "
           "정하기 때문이다. 두 잣대의 참값은 같은 이유로 원장 밖에 있다.", "",
           "상한 위가 더 강한 것은 **그 참값이 작다고 알려져 있다**는 데 있다. 대역 안 몫은 "
           "0.2~0.9 사이 어디든 될 수 있지만, 상한 위 몫은 이상적 날개에서 한 자릿수 퍼센트 "
           "아래로 묶인다. 그래서 이 잣대는 큰 값을 인공물로 읽는 데 쓰고, 작은 값들 사이의 "
           "순위는 이 절의 범위 밖이다."),

        md("### 이 잣대가 서는 범위", "",
           table(["조건", "이 절이 재는 자리"], [
               ["관찰 상한",
                W.num("_meta.nyquist_hz", fmt="{:.0f}", unit="Hz")
                + " 아래만 읽는다 — 그 위 성분은 접혀 들어와 대역 안에 더해진다"],
               ["표적의 운동",
                "기체 고정 · 회전자만 회전. 기체가 움직이면 상한이 동체 도플러만큼 옮겨간다"],
               ["앙각",
                "f_tip > 0 인 여섯 앙각. 직하방은 f_tip = 0 이라 몫이 정의되지 않는다"],
               ["포화점",
                f"평평한 스펙트럼이 받는 점수 — el 0° 에서 {sat(0.0)}, el −75° 에서 "
                f"{sat(-75.0)}. 그 값에 닿은 팔들 사이의 순위는 읽지 않는다"],
               ["비교 축",
                "같은 앙각에서 팔끼리 몫을 견준다. 앙각을 가로지르는 비교는 분모가 달라 이 표 "
                "밖이다"],
               ["격자",
                "우리 팔은 λ/12 한 판이다. 같은 앙각에서 격자만 바꾸면 이 잣대가 "
                + WG.num("rows[0].froz_frac_power_beyond_ftip", fmt="{:.2%}") + " 에서 "
                + WG.num("rows[4].froz_frac_power_beyond_ftip", fmt="{:.3%}")
                + " 로 움직인다(다른 추정기·같은 방향)"],
               ["합격선", "미정 — 임계는 다음 단계 표가 정한다"],
           ])),

        md("## 우리 팔도 −15°·−30° 두 자리에서 샌다", "",
           f"우리 팔의 누설은 네 앙각에서 {leak(K_OURS, -75.0)} ~ {leak(K_OURS, 0.0)} 이고, "
           f"el −15° 에서 {leak(K_OURS, -15.0)}, el −30° 에서 {leak(K_OURS, -30.0)} 로 "
           "올라간다.", "",
           f"el −15°·−30° 는 이 표에서 우리 팔이 물리를 끈 PathSolver 보다 높은 두 자리다 — "
           f"각각 {leak(K_OFF, -15.0)} · {leak(K_OFF, -30.0)} 위다. 같은 잣대가 우리 팔에도 "
           "인공물을 드러낸다.", "",
           f"그 순위는 엔진의 순위라기보다 **표본화 밀도의 순위**다. 우리 팔의 판은 앙각마다 "
           f"λ/12 하나뿐인데, 같은 표적·같은 el −15° 에서 격자만 λ/8 → λ/32 로 바꾸면 같은 "
           f"종류의 대역밖 몫이 "
           f"{WG.num('rows[0].froz_frac_power_beyond_ftip', fmt='{:.2%}')} 에서 "
           f"{WG.num('rows[4].froz_frac_power_beyond_ftip', fmt='{:.3%}')} 로 16 배 내려간다"
           f"(얼린 격자 팔, 블레이드 대역을 분모로 쓰는 다른 추정기).", "",
           "이 판에서 남는 원인 후보는 둘이다 — λ/12 격자의 표본화와 자세 시계열 창의 누설. "
           "거리 곡률은 후보에서 빠진다: 이 스윕은 원거리장 경계 밖에서 쟀다"
           + f"(" + ref("el-sweep-design", "스윕 규약") + "). "
           "이 절이 확정한 것은 두 자리의 크기까지다."),

        md("## ⭐물리 스위치를 켜면 여섯 앙각이 전부 상한 위로 간다", "",
           "굴절·회절·모서리회절을 켠 팔은 같은 광선 예산·같은 자리에서 잰다. 갈리는 축은 "
           "스위치 하나뿐이다.", "",
           table(["앙각", "물리 끔", "물리 켬 (깊이 1)", "물리 켬 (깊이 2)"],
                 [[f"{el:+.0f}°", leak(K_OFF, el), leak(K_ON, el), leak(K_ON2, el)]
                  for el in ELS]), "",
           f"물리를 끈 팔은 el 0° 한 자리에서만 {leak(K_OFF, 0.0)} 로 뛰고 나머지 다섯 "
           f"자리는 {leak(K_OFF, -45.0)} ~ {leak(K_OFF, -60.0)} 사이다. 물리를 켠 팔은 "
           f"여섯 자리가 전부 {leak(K_ON, -45.0)} 위이고 el −75° 에서 "
           f"{leak(K_ON, -75.0)} 다.", "",
           "⇒ 물리를 켜면 **움직이는 에너지의 대부분이 날개가 낼 수 없는 대역**에 놓인다. "
           "그 자리의 참값은 0 에 가깝다고 알려져 있으므로, 그 몫은 표적의 운동이 아니라 "
           "엔진이 만든 것으로 읽는다."),

        md(f"반사 깊이는 이 잣대를 움직이지 않는다 — 여섯 자리 모두 깊이 1 과 깊이 2 의 차이가 "
           f"소수점 아래다(el 0° 에서 {leak(K_ON, 0.0)} 대 {leak(K_ON2, 0.0)}). 깊이를 "
           "1 에서 2 로 올리는 것은 이 표적·이 자리에서 사실상 같은 계산이다."),

        md("이 몫이 무엇에서 오는지는 이 절이 갈라 두지 않는다. 스위치를 하나씩만 켜서 축을 "
           "가른 실험은 " + ref("engine-paths", "경로가 무엇을 세나") + " 에 있고, 이 절이 "
           "확정한 것은 «켜면 여섯 자리가 전부 상한 위로 간다» 까지다."),

        md("### 검증된 것과 열어 둔 것", "",
           table(["무엇", "상태"], [
               ["상한 f_tip(el) 의 위치", "운동학 정의 — 원장이 앙각마다 값을 싣는다"],
               ["세 팔 18 칸의 누설 몫", "계산값 — 합격선은 다음 단계가 정한다"],
               ["우리 팔 두 자리의 원인", "열린 과제 — 후보 셋을 다음 단계가 가른다"],
           ])),

        next_steps([
            ("이상적 회전 블레이드의 상한 위 꼬리 τ 를 같은 규약으로 계산해 원장에 싣는다",
             "이 잣대의 바닥이 0 에서 τ 로 바뀌고, 우리 팔의 작은 값들이 τ 안인지 밖인지 "
             "갈린다",
             "`outputs/tip_tail_reference.json` 신규 (CPU 수 초) · **새 계산이 필요하다**"),

            ("상한 위 누설의 합격선을 τ 위에서 정해 게이트로 올린다",
             "팔을 통과·불통과로 가르는 잣대가 하나 늘고 이 절의 표가 판정표가 된다",
             "`benchmark/build_wideband_energy_fig.py` 에 임계와 판정 칸 추가"),

            ("우리 팔 el −15°·−30° 를 λ/48 격자로 다시 돌린다",
             "그 두 자리의 누설이 격자 표본화에서 오는지가 수치로 갈린다",
             "`benchmark/elevation_sweep_md.py:76` 의 `DIV = 12` → 48 · **새 계산이 필요하다**"),

            ("우리 팔 −15°·−30° 두 자리의 남은 후보(격자 표본화 대 창 누설)를 가른다",
             "우리 팔이 이 잣대에서 유일하게 지는 두 자리의 원인이 특정된다",
             "같은 시계열에 창 길이 축을 하나 더 태운다 (CPU)"),

            ("PRF 를 올려 나이퀴스트 위에서 접혀 들어오는 몫을 잰다",
             "관찰 상한이 이 잣대에 넣는 몫이 갈린다",
             "`benchmark/elevation_sweep_md.py` PRF 축 · **새 계산이 필요하다**"),
        ]),
    ]


# =========================================================================== #
#  조각 78 — 권 16 절 1 「무엇을 어떻게 쟀나 · 설정과 그 대가」
#  ⚠ 이 절만 이 구역을 고친다(같은 권의 다른 절은 자기 구역을 쓴다).
# =========================================================================== #
from report_style import table_from                                   # noqa: E402

J78 = "outputs/elevation_sweep_md.json"
G78 = from_json("outputs/ch1_elevation_figdata_r15.json")  # 15 m 판의 파생량·게이트
T78 = from_json("outputs/report07_three_engines.json")  # 방위·자세 수의 원본(덱과 같은 판)
P78 = from_json("outputs/report15_probe.json")          # 두 가지 D 정의의 원거리장 경계
NF78 = from_json("outputs/nearfield_sphere_vs_plane.json")  # 구면파↔평면파 환산 몫

_ROWS78 = S.get("rows")          # ⚠각주 색인이 이 순서를 쓰므로 **거르지 않는다**
#: ⭐2026-08-13 재설계 — 이 권이 서술하는 판은 **15 m** 다. 같은 원장에 10 m 옛 팔이
#  함께 살지만, 표와 세는 수는 15 m 행만 본다(행 색인은 위 전체 배열 기준을 유지).
R78_PRIMARY = float(S.get("_meta.range_m_primary"))
#: 다른 기체(mini 5 Pro · S1000+)는 **이 권의 대상이 아니다** — 기체 축 실험으로 따로 산다.
OTHER_AIRFRAMES = ("ours_mini5pro_r15_n8192", "ours_s1000plus_r15_n8192")
_R15 = [r for r in _ROWS78
        if r.get("range_m") == R78_PRIMARY and r.get("engine") not in OTHER_AIRFRAMES]
N78_ALL = len(_R15)                                      # 이 권이 서술하는 행
N78_OK = sum(1 for r in _R15 if not r.get("n_missing"))  # 인용 가능한 행
N78_EL = len(S.get("_meta.elevations_deg"))
#: 앙각 7 점을 다 덮은 세 팔 — 재설계판의 주력이다.
#  A_OURS  우리 커널(SBR+PO)   A_OFF  PathSolver 물리 끔   A_ON  PathSolver 물리 켬
A_OURS = "ours_r15_n8192"
A_OFF = "sionna_p4000000000_r15_n8192_d1"
A_ON = "sionna_p4000000000_phys_r15_n8192_d1"
A_ON2 = "sionna_p4000000000_phys_r15_n8192_d2"      # 같은 팔의 깊이 2
ARMS78 = (A_OURS, A_OFF, A_ON)

#: ⭐제목의 숫자는 손으로 치지 않고 **원장에서 세어** 만든다 — 병합으로 행이 늘면 제목도 같이
#  바뀌고, 색인 샤드(title-mismatch 검사)도 같은 문자열을 받는다.
TITLE_78 = (f"앙각 {N78_EL} 점을 {R78_PRIMARY:.0f} m 한 자리에서 광선 40 억 발로 재고, "
            f"{N78_ALL} 행이 모두 완결이다"
            if N78_ALL == N78_OK else
            f"앙각 {N78_EL} 점을 {R78_PRIMARY:.0f} m 한 자리에서 광선 40 억 발로 재고, "
            f"{N78_ALL} 행 중 {N78_OK} 행만 판정에 쓴다")
REG["el-sweep-design"] = ("78", TITLE_78)

REPRO_78 = dict(
    cmd=["SIONNA2_GPU=3 PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python "
         "benchmark/elevation_sweep_md.py --engine ours --shard 0 --nshards 8",
         "SIONNA2_GPU=3 PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python "
         "benchmark/elevation_sweep_md.py --engine sionna --shard 0 --nshards 8",
         "PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python "
         "benchmark/elevation_sweep_md.py --merge",
         "PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python "
         "src/make_fig_el_geometry.py",
         # ⭐시나리오 렌더 — 씬을 Sionna RT 로 그리고(GPU) 도식과 합친다(CPU)
         "PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python "
         "benchmark/render_el15_scene.py",
         "PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python "
         "benchmark/build_el15_scenario_fig.py"],
    out=["outputs/elevation_sweep_md.json", "outputs/elevation_sweep_md.npz",
         "outputs/figures/ch1_f0_geometry.png",
         "outputs/figures/el15_scenario.png"],
    runtime="한 행마다 GPU 누적 14 분 ~ 2 시간 21 분 · 샤드 8 개 병렬. "
            "병합과 그림은 CPU 로 수 초",
    note="`--merge` 는 샤드 폴더 `outputs/elev_sweep_shards/` 를 읽어 원장 두 개를 다시 쓴다")


def _idx78(engine: str) -> list[int]:
    """한 팔의 행 번호를 원장 순서대로. ⚠병합마다 밀리므로 **찾아서** 만든다."""
    return [i for i, r in enumerate(_ROWS78) if r.get("engine") == engine]


def _idx78_rest() -> list[int]:
    """주력 세 팔 밖의 15 m 팔을 **팔당 한 줄**로 — 깊이 2 · 가림 · 평면파 · 단일축 스위치.

    ⚠행마다 한 줄로 뽑으면 표가 40 줄이 넘는다(규약 위반). 설정은 팔 안에서 같으니
      팔의 **첫 행**을 대표로 세운다. 완결성은 표가 아니라 본문이 적는다.
    ⚠10 m 옛 팔과 다른 기체 팔은 이 권의 대상이 아니라 뺀다(원장에는 그대로 남는다).
    """
    seen, out = set(), []
    for i, r in enumerate(_ROWS78):
        e = r.get("engine")
        if (e in ARMS78 or e in OTHER_AIRFRAMES or e in seen
                or r.get("range_m") != R78_PRIMARY):
            continue
        seen.add(e)
        out.append(i)
    return out


def _ref78(anchor: str, short: str) -> str:
    """형제 조각 링크. 형제가 앵커 이름을 바꿔 지었으면 색인 샤드에서 실제 이름을 줍는다."""
    import glob as _glob
    no = REG[anchor][0] if anchor in REG else None
    if no and not os.path.exists(os.path.join(_SHARD_DIR, f"{anchor}.json")):
        for fn in sorted(_glob.glob(os.path.join(_SHARD_DIR, "*.json"))):
            try:
                with open(fn, encoding="utf-8") as f:
                    sh = json.load(f)
            except (OSError, ValueError):
                continue
            if str(sh.get("no")) == no and sh.get("anchor"):
                return f"[편 {no} «{short}»]({no}_{sh['anchor']}.ipynb)"
    return ref(anchor, short)


def _tab78(order: list[int], columns: list, fmt: dict, null: str = "미상") -> str:
    return table_from(f"{J78}:rows", columns, fmt=fmt, null=null, order=order)


def blocks_78() -> list:
    r_ours0, r_ours90 = row(A_OURS, 0.0), row(A_OURS, -90.0)
    r_off0, r_on0 = row(A_OFF, 0.0), row(A_ON, 0.0)
    el_lo = S.num("_meta.elevations_deg[0]", fmt="{:+.0f}", unit="°")
    el_hi = S.num(f"_meta.elevations_deg[{N78_EL - 1}]", fmt="{:+.0f}", unit="°")

    return [
        header(
            num=78,
            title=TITLE_78,
            did=f"관측 앙각 {N78_EL} 점을 15 m 구면 한 자리에 고정해 광선 예산이 같은 세 "
                f"팔로 같은 표적을 재고, 규약과 완결성을 이 조각에 못 박았다.",
            results=[
                f"잰 자리는 하나다 — 반경 {S.num('_meta.range_m_primary', fmt='{:.0f}', unit='m')} "
                f"구면, 방위 {T78.num('_meta.az_deg', fmt='{:.0f}', unit='°')}, "
                f"앙각 {el_lo} 에서 {el_hi} 까지 {N78_EL} 점.",

                f"한 앙각마다 자세 {S.num(f'{r_ours0}.n_poses', fmt='{:,.0f}', unit='개')} 를 "
                f"PRF {S.num('_meta.prf_hz', fmt='{:,.0f}', unit='Hz')} 로 태웠고, 표적은 "
                f"{S.num('_meta.drone')} 하나다.",

                f"그 자리는 **원거리장 경계 밖**이다 — 두 가지 D 정의 모두에서 밖이라 이 "
                f"판은 원거리장 판으로 읽는다. 우리 커널의 조명 규약은 "
                f"«{S.num('_meta.ours_illumination')}» 다.",

                f"광선은 세 팔이 다 같다 — PathSolver 두 팔 모두 "
                f"{S.num('_meta.sionna_spp_primary', fmt='{:,.0f}', unit='발')} 이고, 이 판의 "
                f"{N78_ALL} 행은 빠진 자세 없이 전부 완결이다.",

                f"경로 수는 물리 스위치가 가른다 — 같은 예산에서 물리를 끄면 "
                f"{G78.num(f'gates.G5_{A_OFF}_npaths_min_max[0]', fmt='{:.0f}')}~"
                f"{G78.num(f'gates.G5_{A_OFF}_npaths_min_max[1]', fmt='{:.0f}')} 개, 켜면 "
                f"{G78.num(f'gates.G5_{A_ON}_npaths_min_max[0]', fmt='{:.0f}')}~"
                f"{G78.num(f'gates.G5_{A_ON}_npaths_min_max[1]', fmt='{:.0f}')} 개를 센다.",
            ],
            method=[
                ("기하", "반경 15 m 구면 위에서 방위 하나·앙각 일곱. 송신과 수신은 같은 "
                         "자리다(baseline 0) — `benchmark/elevation_sweep_md.py:83,175`"),
                ("표적·회전", "matrice4e 메쉬 전체(동체·팔·로터·짐벌)에 첫 충돌 가림. 로터 "
                              "넷은 덱과 같은 결정론 RPM 이라 바뀌는 축은 앙각 하나다"),
                ("조명", "우리 커널은 구면파로 조명하고, PathSolver 는 송수신 위치를 실제 "
                         "기하로 놓는다. 광선 수는 두 PathSolver 팔이 40 억 발로 같다 — "
                         "거리만 보는 기본 규칙 `(R/3)²×1M` 을 `--spp` 로 덮어썼다"),
                ("분석 대역", "추적 대역은 앙각마다 그 앙각의 날개끝 주파수로 다시 잡고, "
                              "고정 대역은 덱의 −15° 대역을 그대로 쓴다 — 두 정의는 "
                              "«대역은 두 가지로 잰다» 절에 원장 문장 그대로 싣는다"),
                ("완결성", "`rows[i].n_missing` 은 시계열에 0 으로 남은 자세 수다. 이 조각의 "
                           "표는 `(engine, el_deg, n_missing == 0)` 으로 행을 찾아 만들었다"),
            ],
            prereq=[
                (_ref78("md-attitude", "자세와 가림"),
                 "지상 레이더가 기체를 아래에서 본다는 **기체 자세** 축 — 이 권이 바꾸는 "
                 "앙각은 **수신 기하**이고 그 자세와 다른 축이다"),
                (_ref78("md-two-engines", "두 엔진"),
                 "두 엔진이 날개끝 주파수 아래에서 겹치고 그 위에서 갈린다는 −15° 한 점의 결과"),
            ],
            repro=REPRO_78,
        ),

        md("## 잰 자리는 한 자리다", "",
           "앙각 하나만 바꾼다. 거리·방위·로터 RPM·자세 격자는 같은 값으로 얼려 뒀으므로, "
           "팔 사이와 앙각 사이에서 달라진 것은 시선 방향 하나다.", "",
           f"로터 설정을 원장은 이렇게 적는다 — «{S.num('_meta.rotor_ko')}»."),

        md(table(["설정", "값"], [
            ["표적", S.num("_meta.drone")],
            ["반송파", S.num("_meta.fc_hz", fmt="{:.2e}", unit="Hz")],
            ["거리 — 구면 반경", S.num("_meta.range_m_primary", fmt="{:.0f}", unit="m")],
            ["방위", T78.num("_meta.az_deg", fmt="{:.0f}", unit="°")],
            ["앙각", f"{el_lo} 에서 {el_hi} 까지 {N78_EL} 점"],
            ["자세", S.num(f"{r_ours0}.n_poses", fmt="{:,.0f}", unit="개")],
            ["PRF", S.num("_meta.prf_hz", fmt="{:,.0f}", unit="Hz")],
            ["플래시 박자 — 예측 입력", S.num("_meta.f_flash_hz", fmt="{:.2f}", unit="Hz")],
            ["날개끝 주파수 — 앙각 0°", S.num(f"{r_ours0}.f_tip_hz", fmt="{:.1f}", unit="Hz")],
        ])),

        md("## 그 자리는 어느 원거리장 정의를 쓰느냐로 갈린다", "",
           f"이 스윕이 잰 자리는 반경 "
           f"{S.num('_meta.range_m_primary', fmt='{:.0f}', unit='m')} 구면 위다. 그 거리를 "
           f"고른 이유는 하나다 — **원거리장 경계 밖**에 두면 이 권의 어느 문장에도 "
           f"«근거리장» 단서를 달 필요가 없기 때문이다.", "",
           f"matrice4e·3.5 GHz 에서 2D²/λ 는 **D 를 무엇으로 잡느냐에 따라 두 값**이다 — "
           f"수평 최대치수 {P78.num('airframes.matrice4e.physics.D_horizontal_m', fmt='{:.2f}', unit='m')} "
           f"로 잡으면 "
           f"{P78.num('airframes.matrice4e.physics.farfield_m', fmt='{:.2f}', unit='m')}, "
           f"메쉬 3D 대각 "
           f"{P78.num('airframes.matrice4e.physics.D_diag3d_m', fmt='{:.2f}', unit='m')} 로 "
           f"잡으면 "
           f"{P78.num('airframes.matrice4e.physics.farfield_diag3d_m', fmt='{:.2f}', unit='m')} "
           f"다. 이 판의 15 m 는 **두 값 모두의 밖**이다 — 보수적 정의(3D 대각)로 재도 경계를 "
           f"넘는다. 옛 판이 10 m 여서 두 값 사이에 놓였던 것과 갈리는 지점이 여기다. 이 권은 "
           f"«경계» 를 쓸 때 **정의를 값과 함께** 적는다."),

        md("우리 커널은 이 자리에서도 표적을 **구면파**로 조명한다 — 원장의 조명 규약은 "
           f"«{S.num('_meta.ours_illumination')}» 다. 평면파로 바꾸면 얼마나 달라지는지는 "
           f"재어 뒀다: 같은 기체·같은 반송파·같은 얼린 격자·앙각 −15° 한 점에서 두 조명의 "
           f"차이는 이 판의 15 m 에서 레벨 "
           f"{NF78.num('ranges.15.level_diff_db', fmt='{:.2f}', unit='dB')} · 맵 코사인 "
           f"{NF78.num('ranges.15.map_cosine', fmt='{:.3f}')} 이고, 경계 안쪽 8 m 에서도 "
           f"{NF78.num('ranges.8.level_diff_db', fmt='{:.2f}', unit='dB')} · "
           f"{NF78.num('ranges.8.map_cosine', fmt='{:.3f}')} 다. 차이는 거리와 함께 매끄럽게 "
           f"줄고 **경계를 그대로 지나간다.**"),

        md("다음 셋은 경계와 무관한 **판 조건**이다 — 어느 거리에서도 같다.", "",
           "- PathSolver 는 송수신 위치를 실제 기하로 놓는다. 그 계산이 받는 것은 두 자리의 "
           "좌표뿐이다.",
           f"- 광선 수 {S.num('_meta.sionna_spp_primary', fmt='{:,.0f}', unit='발')} 는 두 "
           f"PathSolver 팔에 **같은 값으로 손수 지정**했다 — 거리만 보는 기본 규칙을 덮어썼다.",
           f"- 표면 격자는 «{S.num('_meta.grid_ko')}» 다 — 자세마다 다시 잡지 않으므로 앙각 "
           f"사이의 차이는 격자가 아니라 자세와 시선에서 온다."),

        # ⭐사용자 지시(2026-08-13) — 시나리오를 **Sionna 렌더**로 보인다.
        #   위 칸이 기하 도식, 아래 칸이 앙각 7 점에서 «레이더가 실제로 보는 드론» 이다.
        #   ⚠아래 «메쉬를 통째로 넣은 대가» 절의 두 몫(cos(el) 감소 · 동체 가림)이
        #     이 그림의 왼쪽 끝과 오른쪽 끝에 그대로 보인다.
        md(f"![experiment scenario rendered with Sionna RT]({FIG}/el15_scenario.png)", "",
           caption(1, "이 판은 표적을 어느 자리에서 보고, 그 자리에서 무엇이 보이나?"), "",
           "위 칸은 기하다 — 15 m 구면 위 앙각 일곱 점과, 그 안쪽을 지나는 원거리장 "
           "경계선. 아래 칸은 그 일곱 자리에서 **레이더가 실제로 보는 표적**이고 "
           "`benchmark/render_el15_scene.py` 가 Sionna RT 로 낸 렌더다. 왼쪽 끝(앙각 0°)은 "
           "로터를 옆에서 봐 블레이드가 선으로 보이고, 오른쪽 끝(−90°)은 로터 원반이 "
           "열리는 대신 **동체가 가운데를 덮는다** — 아래 절이 가르는 두 몫이 이것이다."),

        md("## 메쉬를 통째로 넣은 대가는 두 몫이 겹쳐 있다", "",
           "메쉬는 통째로 넣었다 — 동체·팔·로터·짐벌이 다 들어 있고 첫 충돌 가림이 켜져 "
           "있다. 그래서 앙각을 내리면 두 가지가 함께 움직인다.", "",
           "1. 날개끝 속도의 시선 방향 성분이 cos(el) 로 준다.",
           "2. 동체가 로터와 센서 사이로 들어온다 — 나딧에서는 동체 원반이 로터를 덮는다."),

        md(f"아래 표의 «날개끝 주파수» 는 1 번만 담는 **입력값**이다. `f_tip_at()`"
           f"(`benchmark/elevation_sweep_md.py:205`) 이 로터 지름·회전수에서 "
           f"f_tip = 2·(2π f_rev R)/λ · cos(el) 로 내며, 앙각 0° 의 "
           f"{S.num(f'{r_ours0}.f_tip_hz', fmt='{:.1f}', unit='Hz')} 에서 −90° 의 "
           f"{S.num(f'{r_ours90}.f_tip_hz', fmt='{:.1f}', unit='Hz')} 로 간다. 그것은 cos(el) "
           f"열에 앙각 0° 값을 곱한 수와 같고, 원장에서 앙각 0° 를 가진 여섯 팔이 전부 같은 "
           f"값을 싣는다 — 이 열은 앙각 하나의 함수다. 이 표에서 이 판이 잰 열은 "
           f"`빠진 자세` 하나이고, 일곱 행 모두 0 이라 우리 커널의 일곱 점을 그대로 인용한다."),

        md(_tab78(_idx78(A_OURS),
                  [("앙각 [°]", "el_deg"), ("cos(el)", "cos_el"),
                   ("날개끝 주파수 [Hz]", "f_tip_hz"), ("빠진 자세", "n_missing")],
                  fmt={"el_deg": "{:+.0f}", "cos_el": "{:.4f}",
                       "f_tip_hz": "{:.1f}", "n_missing": "{:.0f}"})),

        md("2 번 몫은 대조군이 가른다. 동체의 «면만» 빼고 정점을 남겨 bbox 와 광선 격자를 "
           "보존하는 `ours_free`(`benchmark/elevation_sweep_md.py:117-122, 132-133`) 가 "
           "그것이고, 축은 «동체가 막느냐» 하나다. 이 판에서는 그 대조군을 같은 일곱 점에서 "
           "다 돌려 원장에 실었다.", "",
           "지금 배선은 `keep = np.asarray(fp.g) == \"prop\"` 이라 prop 아닌 면을 **전부** "
           "뺀다 — `DRONE_GROUP_MAT` 기준으로 body·canopy·arm·motor·gear·camera·accent·"
           "battery·pcb 가 함께 빠지므로 가림과 정적 산란체(DC 분모)가 한 축에 묶인다. "
           "가림만 가르려면 `keep` 을 «body·canopy 만 뺀다» 로 좁혀 돌린다."),

        md("## 세 팔이 같은 자리에서 낸 것", "",
           f"![micro-Doppler maps versus elevation]({FIG}/ch1_f1_maps_r15.png)", "",
           caption(2, "세 팔은 같은 자리에서 앙각을 내릴 때 무엇을 냈나?"), "",
           "위 줄이 우리 커널(SBR + PO), 가운데가 물리 스위치를 끈 PathSolver, 아래가 켠 "
           "PathSolver 다. 세 판의 광선 예산은 같다. 판마다 자기 최댓값으로 정규화했으므로 "
           f"판 사이 레벨 비교는 이 그림 밖이다. 그림은 {N78_EL} 점 중 네 점을 싣고, 일곱 "
           "점 전부의 완결성은 아래 표에 있다.", "",
           "맨 오른쪽 칸(−90°, 직하방)에서는 세 판 모두 가로줄만 남는다 — 그 자리는 날개 "
           "속도의 시선 성분이 0 이라, 남는 것은 정지 성분뿐이다."),

        md("## 대역은 두 가지로 잰다", "",
           f"- 추적 대역 — {S.num('_meta.band_track_ko')}",
           f"- 고정 대역 — {S.num('_meta.band_fixed_ko')}", "",
           "둘을 함께 내는 이유는 «고정 대역을 쓰면 어디서 무너지나» 가 그 자체로 결과이기 "
           f"때문이다. 그 판정은 {_ref78('el-band-tracking', '대역 추적')} 에 있다."),

        md(f"## 어느 행을 인용해도 되나 — {N78_ALL} 행이 모두 완결이다", "",
           f"이 판의 {N78_ALL} 행은 전부 `n_missing = 0` 이다. `n_missing` 은 시계열에 0 이 "
           "박힌 자세의 수이고, 0 이 박히면 스펙트럼과 레벨이 그만큼 눌린다. 이 권은 그런 "
           "행을 인용하지 않는데, 이 판에는 그런 행이 없다.", "",
           "아래 표는 주력 세 팔 **밖의** 팔들이다 — 반사 깊이를 2 로 올린 판, 동체를 뺀 "
           "대조군, 평면파 조명 판, 그리고 물리 스위치를 하나씩만 켠 넉 장이다. 설정은 팔 "
           "안에서 같으므로 팔당 한 줄로 싣는다."),

        md(_tab78(_idx78_rest(),
                  [("팔", "engine"), ("반사 깊이", "max_depth"), ("광선 [발]", "spp"),
                   ("물리 스위치", "physics")],
                  fmt={"max_depth": "{:.0f}", "spp": "{:,.0f}"}, null="해당 없음")),

        md("이 권이 이 원장을 읽는 규칙은 셋이다.", "",
           f"1. 판정은 대역 몫으로 하고 `level_db` 는 "
           f"{_ref78('budget-not-physics', '광선 예산')} 이 같은 엔진 안에서 다룬다 — 팔마다 "
           f"정규화가 다르다.",
           f"2. −90° 에서 추적 대역의 폭이 0 이라 그 칸이 `null` 이다. `null` 은 0 이 아니라 "
           f"«잴 수 없다» 는 표시이고, {_ref78('el-band-tracking', '대역 추적')} 이 "
           f"«측정 불가» 로 적는다.",
           "3. 행 번호는 병합할 때마다 밀린다. 이 조각의 표는 `(engine, el_deg, "
           "n_missing == 0)` 으로 행을 찾아 만들었다."),

        md("## 경로 수를 가르는 것은 예산이 아니라 물리 스위치다", "",
           f"이 판은 두 PathSolver 팔에 광선을 "
           f"{S.num('_meta.sionna_spp_primary', fmt='{:,.0f}', unit='발')} 로 **똑같이** 줬다. "
           f"그런데도 한 자세가 찾아 오는 경로 수가 갈린다 — 물리를 끈 팔이 "
           f"{G78.num(f'gates.G5_{A_OFF}_npaths_min_max[0]', fmt='{:.0f}')}~"
           f"{G78.num(f'gates.G5_{A_OFF}_npaths_min_max[1]', fmt='{:.0f}')} 개, 켠 팔이 "
           f"{G78.num(f'gates.G5_{A_ON}_npaths_min_max[0]', fmt='{:.0f}')}~"
           f"{G78.num(f'gates.G5_{A_ON}_npaths_min_max[1]', fmt='{:.0f}')} 개다.", "",
           "예산이 같은데 갈렸으므로 이 차이를 만든 것은 물리 스위치다. 스위치를 하나씩만 켜서 "
           f"어느 스위치가 그 일을 하는지 가른 실험은 "
           f"{_ref78('physics-single-axis', '물리 스위치')} 에 있다.", "",
           f"한 팔 **안에서** 경로 수가 앙각을 따라 움직이는 몫은 시선 기하가 정한다 — 두 팔 "
           f"다 앙각 0° 에서 −90° 로 가며 늘어난다. 아래 두 표가 같은 열을 앙각별로 싣는다.", "",
           f"⇒ 인용한 네 수는 자세 "
           f"{S.num(f'{r_ours0}.n_poses', fmt='{:,.0f}', unit='개')} 중앙값의 최소·최대이고, "
           f"자세 하나하나의 경로 수는 그보다 넓게 흩어진다. 경로 수를 산란 세기로 읽는 "
           f"해석은 {_ref78('engine-paths', '경로가 무엇을 세나')} 가 다룬다."),

        md("**PathSolver — 물리 스위치 끔**", "",
           _tab78(_idx78(A_OFF),
                  [("앙각 [°]", "el_deg"), ("빠진 자세", "n_missing"),
                   ("경로 수 중앙값", "npaths_median")],
                  fmt={"el_deg": "{:+.0f}", "n_missing": "{:.0f}",
                       "npaths_median": "{:.0f}"})),

        md("**PathSolver — 물리 스위치 켬(같은 광선 예산)**", "",
           _tab78(_idx78(A_ON),
                  [("앙각 [°]", "el_deg"), ("빠진 자세", "n_missing"),
                   ("경로 수 중앙값", "npaths_median")],
                  fmt={"el_deg": "{:+.0f}", "n_missing": "{:.0f}",
                       "npaths_median": "{:.0f}"})),

        next_steps([
            ("가림만 끄고 산란체는 남기는 팔을 배선해 같은 일곱 점에서 돌린다 — 지금의 "
             "`ours_free` 는 프로펠러만 남기는 팔이라 분모까지 바뀐다",
             "가림이 대역 몫을 얼마나 지우는지가 정적 성분 변화와 분리돼 나온다",
             "`benchmark/elevation_sweep_md.py:117-122` 의 `keep` 을 body·canopy 로 좁힌다 · "
             "**새 계산이 필요하다**"),

            ("−60° 와 −75° 사이를 다섯 점 더 잰다",
             "고정 대역이 대역외 바닥에 닿는 앙각이 15° 격자 안에서 특정된다",
             "`benchmark/elevation_sweep_md.py --els` · "
             + _ref78("el-band-tracking", "대역 추적")),

            ("나딧 삼분할과 CPU 재현기를 이 판의 15 m 에서 다시 만든다",
             "옛 10 m 판에서 낸 나딧 진단이 이 권의 주력 거리에서 그대로 서는지 갈린다",
             "`benchmark/verify_nadir_flash.py` · `refute_nadir_mechanism_final.py` 를 거리 "
             "축으로 열어야 한다 · **새 계산이 필요하다**"),

            ("다른 기체(mini 5 Pro · S1000+)의 일곱 점을 같은 규약으로 마저 채운다",
             "이 권이 본 것이 matrice4e 한 기체의 성질인지 기체 공통인지 갈린다",
             "`benchmark/elevation_sweep_md.py --drone` (진행 중)"),
        ]),
    ]


# --------------------------------------------------------------------------- #
#  색인 샤드 — README·지도가 읽는다

# <<<PART82_BEGIN>>>
# =========================================================================== #
#  조각 82 — 권 16 「직하방 — 도플러가 원리적으로 0 인 자리에서 무엇이 남나」
#  ⚠ 이 구역은 조각 82 전용이다. 다른 절을 맡은 사람은 여기를 건드리지 않는다.
# =========================================================================== #
#: 계획의 제목을 이 라운드에서 늘려 잡았다 — 노트북 H1 과 샤드가 **글자 하나까지** 같아야 한다.
TITLE_82 = ("나딧 잔여 −38.31 dB 의 64 % 는 광선 격자 표본화 잡음이고, "
            "5° 만 기울면 −11.88 dB 로 열린다")
REG["el-nadir-floor"] = ("82", TITLE_82)

#: 조각 82 의 원장 — 전부 읽기 전용. (W · S 는 위에서 이미 열렸다)
NF = from_json("outputs/verify_nadir_flash.json")             # 잣대 감사 · 분해 · 각도/거리
RN = from_json("outputs/refute_nadir_mechanism_final.json")   # CPU 재현기 · 삼분할 · 링크버짓
FD = from_json("outputs/ch1_elevation_figdata.json")          # 앙각축 파생량

#: 팔 색 — 기존 앙각 그림(ch1_f*)과 같은 배정.
COL_OURS, COL_S11, COL_S250 = "#c62828", "#8e9aab", "#1565c0"
FIGDIR = os.path.join(_ROOT, "outputs", "figures")
_R_OURS90 = row("ours", -90.0)          # el −90 행(결측 0)의 인덱스 — 병합마다 밀린다

REPRO_82 = dict(
    cmd=["PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python "
         "benchmark/verify_nadir_flash.py",
         "PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python "
         "benchmark/refute_nadir_mechanism_final.py",
         "PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python "
         "src/build_part12_elevation.py"],
    out=["outputs/verify_nadir_flash.json",
         "outputs/refute_nadir_mechanism_final.json"],
    runtime="약 2분 (CPU)",
    note="두 스크립트 모두 GPU 를 쓰지 않는다 — 광선은 CPU z-버퍼이고 "
         "mitsuba·sionna 를 import 하지 않는다")


def _assert_title_numbers_82() -> None:
    """제목의 세 숫자는 손으로 친 자리다 — 원장에서 다시 읽어 **대조**한다.

    (제목은 `num()` 을 못 쓴다. 원장이 바뀌면 여기서 빌드가 멈춘다.)
    """
    want = [
        format(abs(float(NF.get("B_decomposition.ours/el-90.ac_over_dc_db"))), ".2f"),
        format(100.0 * float(
            RN.get("R5_detection.nadir_ac_split.grid_sampling_noise_fraction")), ".0f"),
        format(abs(float(
            NF.get("C_D_geometry.offnadir_farfield.-85.0.ac_over_dc_db"))), ".2f"),
        format(float(NF.get("C_D_geometry.offnadir_farfield.-85.0.off_nadir_deg")),
               ".0f"),
    ]
    missing = [w for w in want if w not in TITLE_82]
    if missing:
        raise ContractError(
            f"제목의 숫자가 원장과 어긋난다 — 원장이 말하는 값: {want}\n"
            f"  제목: {TITLE_82!r}\n  → 제목을 원장 값으로 고쳐라.")


_assert_title_numbers_82()


def xref(anchor: str, short: str) -> str:
    """`build_volumes.py` 의 `_XREF` 가 알아보는 꼴 — `[편 NN «…»](NN_anchor.ipynb)`."""
    if anchor not in REG:
        raise ContractError(f"모르는 앵커: {anchor!r} — 편성 계획에 없다")
    return f"[편 {REG[anchor][0]} «{short}»]({REG[anchor][0]}_{anchor}.ipynb)"


def _save82(fig, name: str) -> str:
    os.makedirs(FIGDIR, exist_ok=True)
    p = os.path.join(FIGDIR, name)
    fig.savefig(p, dpi=170, bbox_inches="tight")
    print(f"  ✅ {os.path.relpath(p, _ROOT)}")
    return p


def fig_nadir_cone() -> str:
    """나딧에서 벗어난 각도별 변조 예산 — 사각지대 원뿔의 폭."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    T = dict(title="Blind cone at nadir: modulation returns within a few degrees",
             xlabel="Tilt away from nadir [deg]",
             ylabel="Modulation AC/DC [dB]",
             l_far="Far-field geometry proxy",
             l_rep="Kernel replica at 10 m",
             l_meas="Measured sweep, same metric",
             note="0.0 deg: -305 dB\n(exact far-field invariance)")
    assert_fig_text(*T.values())

    ff = NF.get("C_D_geometry.offnadir_farfield")
    rp = RN.get("R4d_null_width.cpu_replica")
    ms = RN.get("R4d_null_width.measured_sweep_same_metric")
    xf = [r["off_nadir_deg"] for r in ff.values() if r["off_nadir_deg"] > 0]
    yf = [r["ac_over_dc_db"] for r in ff.values() if r["off_nadir_deg"] > 0]
    xr = [r["off_nadir_deg"] for r in rp.values()]
    yr = [r["sph10_ac_over_dc_db"] for r in rp.values()]

    plt.rcParams.update({
        "font.size": 11, "axes.titlesize": 12.5, "axes.labelsize": 11,
        "legend.fontsize": 10, "figure.facecolor": "white",
        "savefig.facecolor": "white", "axes.grid": True, "grid.alpha": 0.25,
        "axes.axisbelow": True})
    fig, a = plt.subplots(figsize=(8.4, 5.2))
    a.plot(xf, yf, "o-", color=COL_S250, lw=2.0, ms=8, label=T["l_far"], zorder=3)
    a.plot(xr, yr, "s--", color=COL_S11, lw=2.0, ms=7, label=T["l_rep"], zorder=2)
    a.plot([0.0, 15.0], [ms["el-90"], ms["el-75"]], "D", color=COL_OURS, ms=9,
           label=T["l_meas"], zorder=4)
    for x, y in zip(xf, yf):
        if x in (0.5, 2.0, 5.0):
            a.annotate(f"{y:.1f} dB", xy=(x, y), xytext=(9, -13),
                       textcoords="offset points", fontsize=10, color=COL_S250,
                       bbox=dict(fc="white", ec="none", alpha=0.9, pad=1.4))
    a.annotate(T["note"], xy=(0.0, -57.0), xytext=(1.1, -66.0), fontsize=10,
               color="0.25", ha="left",
               arrowprops=dict(arrowstyle="->", color="0.45", lw=1.2))
    a.set_xlim(-0.6, 15.8)
    a.set_ylim(-70, 6)
    a.set_xlabel(T["xlabel"])
    a.set_ylabel(T["ylabel"])
    a.set_title(T["title"])
    a.legend(loc="lower right", framealpha=0.95)
    return _save82(fig, "ch1_nadir_cone.png")


def fig_nadir_residual() -> str:
    """나딧 잔여의 구성과 거리 거동 — 실물 신호인지 가르는 두 잣대."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    T = dict(title="What the nadir residual is made of, and how it travels",
             t1="Attribution of the residual modulation power",
             t2="Residual vs range",
             x1="Share of AC power [%]", x2="Range [m]",
             y2="Modulation AC/DC [dB]",
             c1="Ray-grid sampling noise", c2="Near-field curvature",
             c3="Occlusion",
             l_rep="Kernel replica, production grid",
             l_prx="Geometry proxy, no grid, no occlusion",
             n_rep="flat within 2 dB from 10 m to 1 km",
             n_prx="fitted exponent 4.0")
    assert_fig_text(*T.values())

    sp = RN.get("R5_detection.nadir_ac_split")
    shares = [100.0 * sp["grid_sampling_noise_fraction"],
              100.0 * sp["nearfield_fraction"], 100.0 * sp["occlusion_fraction"]]
    names = [T["c1"], T["c2"], T["c3"]]
    cols = [COL_S11, COL_S250, COL_OURS]
    rep = RN.get("R4b_cpu_kernel_replica.range_sweep_ac_over_dc_db")
    prx = RN.get("R4a_facet_proxy_no_grid_no_occlusion.range_sweep_ac_over_dc_db")
    kr = sorted((k for k in rep if k != "plane"), key=float)
    kp = sorted(prx, key=lambda s: float(s[:-1]))

    plt.rcParams.update({
        "font.size": 11, "axes.titlesize": 12, "axes.labelsize": 11,
        "legend.fontsize": 9.5, "figure.facecolor": "white",
        "savefig.facecolor": "white", "axes.grid": True, "grid.alpha": 0.25,
        "axes.axisbelow": True})
    fig, ax = plt.subplots(1, 2, figsize=(13.6, 4.4),
                           gridspec_kw=dict(width_ratios=[1.0, 1.25]))

    a = ax[0]
    ypos = list(range(len(shares)))[::-1]          # 위에서 아래로 큰 몫부터
    a.barh(ypos, shares, height=0.52, color=cols)
    for y, s in zip(ypos, shares):
        a.text(s + 1.8, y, f"{s:.0f}%", va="center", fontsize=12, color="0.15")
    a.set_yticks(ypos)
    a.set_yticklabels(names, fontsize=11)
    a.set_xlim(0, 78)
    a.set_xlabel(T["x1"])
    a.set_title(T["t1"])
    a.grid(True, axis="x", alpha=0.25)
    a.grid(False, axis="y")
    for side in ("top", "right", "left"):
        a.spines[side].set_visible(False)
    a.tick_params(axis="y", length=0)

    a = ax[1]
    a.semilogx([float(k) for k in kr], [rep[k] for k in kr], "s-", color=COL_OURS,
               lw=2.0, ms=7, label=T["l_rep"])
    a.semilogx([float(k[:-1]) for k in kp], [prx[k] for k in kp], "o--",
               color=COL_S250, lw=2.0, ms=7, label=T["l_prx"])
    a.annotate(T["n_rep"], xy=(45, rep["50"]), xytext=(0, 12),
               textcoords="offset points", fontsize=10.5, color=COL_OURS)
    a.annotate(T["n_prx"], xy=(230, -68), fontsize=10.5, color=COL_S250,
               bbox=dict(fc="white", ec="none", alpha=0.9, pad=1.4))
    a.set_xlabel(T["x2"])
    a.set_ylabel(T["y2"])
    a.set_title(T["t2"])
    a.legend(loc="lower left", framealpha=0.95)
    fig.suptitle(T["title"], fontsize=13, y=1.03)
    return _save82(fig, "ch1_nadir_residual.png")


def _fig82(no: int, stem: str, question: str) -> list:
    return [f"![{stem}]({FIG}/{stem}.png)", "", caption(no, question), ""]


def blocks_82() -> list:
    fig_nadir_residual()          # 그림은 원장만 읽어 CPU 로 그린다(GPU 없음)
    fig_nadir_cone()
    return [
        header(
            num=82,
            title=TITLE_82,
            did="직하방에서 남은 변조를 세 갈래로 귀속하고, 나딧에서 벗어난 각도별 "
                "변조 예산과 거리 거동을 원장에서 뽑았다.",
            results=[
                f"원거리장 나딧의 변조는 "
                f"{NF.num('C_D_geometry.nadir_plane_wave_ac_over_dc_db', fmt='{:.2f}', unit='dB')}"
                f" — 회전이 산란적분을 그대로 두는 자리다.",

                f"10 m 판에 남는 변조는 "
                f"{NF.num('B_decomposition.ours/el-90.ac_over_dc_db', fmt='{:.2f}', unit='dB')} "
                f"이고, 그 전력의 "
                f"{RN.num('R5_detection.nadir_ac_split.grid_sampling_noise_fraction', fmt='{:.1%}')}"
                f" 가 광선 격자 표본화 잡음이다.",

                f"나딧에서 "
                f"{NF.num('C_D_geometry.offnadir_farfield.-89.5.off_nadir_deg', fmt='{:.1f}', unit='°')}"
                f" 벗어나면 "
                f"{NF.num('C_D_geometry.offnadir_farfield.-89.5.ac_over_dc_db', fmt='{:.2f}', unit='dB')}, "
                f"{NF.num('C_D_geometry.offnadir_farfield.-85.0.off_nadir_deg', fmt='{:.0f}', unit='°')}"
                f" 에서 "
                f"{NF.num('C_D_geometry.offnadir_farfield.-85.0.ac_over_dc_db', fmt='{:.2f}', unit='dB')}"
                f" 로 변조가 돌아온다 — 사각지대는 좁은 원뿔이다.",

                f"생산 격자에서 재면 이 잔여는 10 m "
                f"{RN.num('R4b_cpu_kernel_replica.range_sweep_ac_over_dc_db.10', fmt='{:.2f}', unit='dB')} "
                f"에서 1 km "
                f"{RN.num('R4b_cpu_kernel_replica.range_sweep_ac_over_dc_db.1000', fmt='{:.2f}', unit='dB')} "
                f"까지 평평하다.",

                f"나딧의 몸체 에코는 오히려 커진다 — 10 m SNR "
                f"{RN.num('R5_detection.rows.10m.nadir_snr_total_db', fmt='{:.2f}', unit='dB')} "
                f"대 −15° 의 "
                f"{RN.num('R5_detection.rows.10m.el15_snr_total_db', fmt='{:.2f}', unit='dB')} 다.",
            ],
            method=[
                ("변조 잣대",
                 "자세 시계열의 AC/DC [dB] — 반송파(DC) 대비 흔들리는 전력. "
                 "`benchmark/verify_nadir_flash.py` 의 분해 규약을 그대로 쓴다"),
                ("삼분할",
                 "커널을 CPU 로 재현해 격자·근접장·가림을 한 축씩 갈라 남는 전력의 몫으로 "
                 "나눈다. 세 갈래가 직교하지 않으므로 이 나눗셈은 어림이다"),
                ("각도 예산",
                 "재질·가림·격자 없는 평면 패싯 PO 대리모형의 원거리장 값이다. 각도 의존만 "
                 "읽고 절대 레벨은 SBR 원장 쪽을 쓴다"),
                ("판",
                 f"matrice4e 1기 · 3.5 GHz · 거리 "
                 f"{S.num(f'{_R_OURS90}.range_m', fmt='{:.0f}', unit='m')} · 방위 고정 · el −90 "
                 f"행의 자세 {S.num(f'{_R_OURS90}.n_poses', fmt='{:.0f}', unit='개')}"
                 f"(결측 {S.num(f'{_R_OURS90}.n_missing', fmt='{:.0f}', unit='개')}). "
                 f"⭐이 절의 삼분할·재현기는 **그 거리에 맞춰 만든 것**이라, 이 권의 주력 "
                 f"거리 {S.num('_meta.range_m_primary', fmt='{:.0f}', unit='m')} 판과 "
                 f"구분해 읽는다"),
            ],
            prereq=[
                (xref("el-sweep-design", "스윕 규약"),
                 "이 스윕이 무엇을 어떤 규약으로 쟀고 어느 행을 인용해도 되나"),
                (xref("el-above-tip-limit", "상한 위 누설"),
                 "날개끝 상한 위 에너지가 왜 인공물의 눈금인가"),
            ],
            repro=REPRO_82,
        ),

        md("## 원거리장 나딧에서 회전은 산란적분을 그대로 둔다", "",
           "시선이 로터 면에 수직이면 날개의 속도가 시선과 직각이라 도플러 항이 0 이 된다. "
           "평면파로 계산한 나딧 변조 "
           f"{NF.num('C_D_geometry.nadir_plane_wave_ac_over_dc_db', fmt='{:.2f}', unit='dB')} "
           "는 배정밀도 반올림의 크기다 — 회전이 시선 방향 좌표도 투영 면적도 바꾸지 않아 "
           "적분값이 자세에 불변이기 때문이다.", "",
           "근거는 원장의 한 줄이다 — "
           f"`{RN.get('R4a_facet_proxy_no_grid_no_occlusion.exact_invariance_ko')}`"),

        md("## 10 m 판에서는 굽은 파면이 두 날개를 다르게 본다", "",
           f"이 절이 쓰는 행의 거리는 "
           f"{S.num(f'{_R_OURS90}.range_m', fmt='{:.0f}', unit='m')} 이고, 보수적 정의(메쉬 3D "
           f"대각)로 잡은 원거리장 경계 "
           f"{P78.num('airframes.matrice4e.physics.farfield_diag3d_m', fmt='{:.2f}', unit='m')} "
           f"의 안쪽이다. 그래서 이 자리에서는 파면이 굽어 있다.", "",
           "굽은 파면에서는 허브가 회전축에서 "
           f"{RN.num('R2_analytic.geometry_from_mesh.hub_radius_m', fmt='{:.4f}', unit='m')} "
           "밀려 있는 만큼 날개끝 왕복거리가 흔들리고, 그 흔들림은 왕복 위상 "
           f"{RN.num('R2_analytic.per_element.two_way_phase_swing_pp_deg', fmt='{:.2f}', unit='°')} "
           "peak-peak 다. 2엽 로터는 그 1차 항을 상쇄하고 2ψ 성분만 남기므로 해석 예측은 "
           f"{RN.num('R2_analytic.two_blade_cancellation.predicted_ac_over_dc_db', fmt='{:.2f}', unit='dB')} "
           "이고, 관측 "
           f"{NF.num('B_decomposition.ours/el-90.ac_over_dc_db', fmt='{:.2f}', unit='dB')} "
           "가 그 옆에 선다.", "",
           "이 예측을 어디까지 읽어도 되는지는 원장이 적어 뒀다 — "
           f"`{RN.get('R2_analytic.two_blade_cancellation.comparison_ko')}`"),

        md("## 남은 변조의 3 분의 2 는 수치 인공물이다", "",
           *_fig82(1, "ch1_nadir_residual", "나딧에 남은 변조는 실물 표적의 신호인가?"),
           table(["갈래", "AC 전력 몫", "무엇인가"],
                 [["광선 격자 표본화 잡음",
                   RN.num("R5_detection.nadir_ac_split.grid_sampling_noise_fraction",
                          fmt="{:.1%}"),
                   "격자가 두 날개를 다르게 표본화해 생기는 수치 인공물 — 실물 표적에는 없다"],
                  ["근접장 파면 곡률",
                   RN.num("R5_detection.nadir_ac_split.nearfield_fraction", fmt="{:.1%}"),
                   "10 m 에서만 사는 기하 항 — 물리적으로는 거리에 1/r⁴ 로 준다"],
                  ["가림",
                   RN.num("R5_detection.nadir_ac_split.occlusion_fraction", fmt="{:.1%}"),
                   "날개가 몸체를 스치며 가리는 몫 — 조인 격자 판 값이라 상한이다"]])),

        md("### 이 나눗셈이 서는 범위", "",
           "가림 몫이 상한이므로 격자 잡음 몫은 하한이다. 근거는 원장에 한 줄로 있다 — "
           f"`{RN.get('R5_detection.nadir_ac_split.basis')}`", "",
           "재현기가 관측을 되살린다는 근거는 상관 "
           f"{RN.num('R4b_cpu_kernel_replica.corr_ac_sph10_vs_measured', fmt='{:.3f}')} "
           "이고, 같은 계열을 시간축으로 밀어 만든 널 분포의 99 백분위는 "
           f"{RN.num('R4b_cpu_kernel_replica.shift_null.null_p99', fmt='{:.4f}')} 다."),

        md("## 이 잔여는 거리를 늘려도 2 dB 안에서 평평하다", "",
           "생산 격자에서 근접장 고유항만 남기면 거리 지수는 "
           f"{RN.num('R4c_grid_ladder.rows.lambda/12.nearfield_only_fit_exponent', fmt='{:.3f}')} "
           "이고, 격자를 네 배 조이면 "
           f"{RN.num('R4c_grid_ladder.rows.lambda/48.nearfield_only_fit_exponent', fmt='{:.2f}')} "
           "로 4 에 다가간다. 총 AC/DC 는 10 m "
           f"{RN.num('R4b_cpu_kernel_replica.range_sweep_ac_over_dc_db.10', fmt='{:.2f}', unit='dB')} "
           "에서 1 km "
           f"{RN.num('R4b_cpu_kernel_replica.range_sweep_ac_over_dc_db.1000', fmt='{:.2f}', unit='dB')} "
           "까지 평평하다.", "",
           "거리 지수 "
           f"{RN.num('R4a_facet_proxy_no_grid_no_occlusion.fit_exponent', fmt='{:.3f}')} "
           "는 격자·재질·가림이 없는 패싯 대리모형의 성질이다. 그림 1 오른쪽 판이 두 거동을 "
           "나란히 놓는다 — 실전 거리에서 이 바닥이 얼마나 낮은지는 **거리가 아니라 격자**가 "
           "정한다."),

        md("## 나딧에서 고정 대역이 보고하는 박자는 창 누설이다", "",
           "70 표본 한나 창의 주엽 반폭 "
           f"{NF.num('A_instrument_audit.hann_mainlobe_halfwidth_hz', fmt='{:.1f}', unit='Hz')} "
           "가 대역 하단 "
           f"{NF.num('A_instrument_audit.band_lo_hz', fmt='{:.1f}', unit='Hz')} "
           "를 덮는다. 그래서 el −90 에서 그 대역이 보고하는 전력 "
           f"{NF.num('B_decomposition.ours/el-90.fixed_band_power_db', fmt='{:.2f}', unit='dB')} "
           "는 누설분만 넣었을 때의 값과 "
           f"{NF.num('B_decomposition.ours/el-90.fixed_band_true_over_leakage_db', fmt='{:.2f}', unit='dB')} "
           "차이다.", "",
           f"전 구간 FFT(`{FD.get('_meta.spectrum_ko')}`)로 같은 대역을 재면 "
           f"{RN.num('R3_window_robustness.ours/el-90.fullrecord_band_share_db', fmt='{:.2f}', unit='dB')} "
           "이고, 저역통과로 대역 안 내용물만 남기면 "
           f"{RN.num('R3_window_robustness.ours/el-90.fullrecord_band_share_lowpassed_db', fmt='{:.2f}', unit='dB')} "
           "다. 나딧에서 날개끝 상한은 "
           f"{S.num(f'{_R_OURS90}.f_tip_hz', fmt='{:.1f}', unit='Hz')} "
           "라 이 대역에 블레이드 도플러가 들어올 자리의 폭이 0 이다."),

        md("## 엔진마다 나딧 잔여의 크기가 다르다", "",
           "같은 자리에서 위상 흔들림 p95 는 우리 팔 "
           f"{NF.num('B_decomposition.ours/el-90.phase_dev_p95_deg', fmt='{:.2f}', unit='°')}, "
           "PathSolver 11.1M "
           f"{NF.num('B_decomposition.sionna/el-90.phase_dev_p95_deg', fmt='{:.2f}', unit='°')}, "
           "250M "
           f"{NF.num('B_decomposition.sionna_p250000000/el-90.phase_dev_p95_deg', fmt='{:.2f}', unit='°')} "
           "다. 광선을 늘린 팔에서 흔들림이 함께 줄어드는 축이 곧 표본화 축이다.", "",
           "위상 흔들림은 **각도**라 팔 사이에서 그대로 견줄 수 있다. 진폭 쪽에는 그런 잣대가 "
           "이 절에 없다 — 팔마다 정규화가 달라 «흔들리는 전력 ÷ 반송파 전력» 을 dB 로 빼면 "
           "분모가 다른 두 수를 빼는 것이 된다. 그래서 이 절은 **위상 축만으로** 판정하고, "
           "진폭 축의 팔 사이 비교는 열어 둔다.", "",
           "도플러가 원리적으로 0 인 자리에서 남는 이 크기는 산란 물리가 아니라 각 엔진의 "
           "표본화가 정한다."),

        md("## 사각지대는 반각 몇 도짜리 원뿔이다", "",
           *_fig82(2, "ch1_nadir_cone",
                   "호버 중인 기체가 나딧에서 몇 도 기울면 프로펠러 변조가 돌아오는가?"),
           "호버링하는 기체는 바람과 자세 제어로 늘 몇 도 기운다. 그 몇 도가 아래 표의 어느 "
           "줄에 앉느냐가 프로펠러 무늬를 볼지 말지를 정한다."),

        md("### 각도 예산 — 원거리장 기하가 주는 표", "",
           table_from("outputs/verify_nadir_flash.json:C_D_geometry.offnadir_farfield",
                      [("나딧에서 벗어난 각 [°]", "off_nadir_deg"),
                       ("변조 AC/DC [dB]", "ac_over_dc_db")],
                      fmt={"off_nadir_deg": "{:.1f}", "ac_over_dc_db": "{:.2f}"}), "",
           "10 m 재현기로 같은 각도를 훑으면 0° 에서 "
           f"{RN.num('R4d_null_width.cpu_replica.-90.0.sph10_ac_over_dc_db', fmt='{:.2f}', unit='dB')}, "
           "5° 에서 "
           f"{RN.num('R4d_null_width.cpu_replica.-85.0.sph10_ac_over_dc_db', fmt='{:.2f}', unit='dB')} "
           "다 — 격자 잡음 바닥 위로 각도 항이 올라오는 자리가 그 사이에 있다."),

        md("## 탐지로 옮기면 — 에코는 커지고 블레이드 선만 무너진다", "",
           "나딧에서 몸체 반사는 "
           f"{RN.num('R5_detection.sigma_dbsm.nadir_dc', fmt='{:.2f}', unit='dBsm')} "
           "로 −15° 의 "
           f"{RN.num('R5_detection.sigma_dbsm.el15_dc', fmt='{:.2f}', unit='dBsm')} "
           "보다 크고, 변조 성분은 "
           f"{RN.num('R5_detection.sigma_dbsm.nadir_ac_at_10m', fmt='{:.2f}', unit='dBsm')} "
           "로 −15° 의 "
           f"{RN.num('R5_detection.sigma_dbsm.el15_ac', fmt='{:.2f}', unit='dBsm')} "
           "보다 작다.", "",
           "10 m 링크버짓에서 전체 SNR 은 나딧 "
           f"{RN.num('R5_detection.rows.10m.nadir_snr_total_db', fmt='{:.2f}', unit='dB')} "
           "대 −15° "
           f"{RN.num('R5_detection.rows.10m.el15_snr_total_db', fmt='{:.2f}', unit='dB')} "
           "이고, 블레이드 선 SNR 은 나딧 "
           f"{RN.num('R5_detection.rows.10m.nadir_snr_blade_physical_db', fmt='{:.2f}', unit='dB')} "
           "대 −15° "
           f"{RN.num('R5_detection.rows.10m.el15_snr_blade_db', fmt='{:.2f}', unit='dB')} 다.", "",
           "머리 위 기체는 **에코로 잡고, 프로펠러 무늬는 기울어진 뒤에 잡는다.** 이 사다리의 "
           f"절대 σ 규약은 원장이 적어 뒀다 — `{RN.get('R5_detection.convention.caveat_ko')}`"),

        next_steps([
            ("호버 자세 분포를 넣어 나딧 0~5° 를 자세 표본으로 채운다",
             "사각지대 원뿔의 입체각이 확정된다",
             "`benchmark/elevation_sweep_md.py` 앙각 간격 세분 · **새 계산이 필요하다**"),

            ("나딧 한 점을 조인 격자로 다시 재고 삼분할을 갱신한다",
             "격자 잡음 몫 64 % 가 하한에서 실제값으로 좁혀진다",
             "`benchmark/refute_nadir_mechanism_final.py` R4c · **새 계산이 필요하다**"),

            ("실측에서 기체를 정면 상공에 띄우고 같은 잣대로 잰다",
             "잔여가 수치 인공물인지 실물 신호인지 갈린다",
             xref("el-sweep-design", "스윕 규약") + " → 실측 캠페인"),
        ]),
    ]
# <<<PART82_END>>>

# --------------------------------------------------------------------------- #
def write_shard(no: str, anchor: str, rep: dict, evidence: list | None = None) -> None:
    title = REG[anchor][1]
    short = title.split("—")[0].split(",")[0].strip()
    if len(short) > 26:
        short = short[:25].rstrip() + "…"
    shard = dict(
        no=no, anchor=anchor, part=SHARD_PART, part_name=SHARD_PART_NAME,
        title=title, short=short,
        file=f"reports/_parts/{no}_{anchor}.ipynb",
        builder=f"src/{os.path.basename(__file__)}",
        volume="16", evidence=list(evidence or []),
        md_cells=rep["md_cells"], figures=rep["figures"],
        provenance_tags=rep["provenance_tags"],
        negatives=rep["n_negatives"], hedges=rep["n_hedges"], ok=rep["ok"])
    os.makedirs(_SHARD_DIR, exist_ok=True)
    with open(os.path.join(_SHARD_DIR, f"{anchor}.json"), "w", encoding="utf-8") as f:
        json.dump(shard, f, ensure_ascii=False, indent=1)


# =========================================================================== #
#  조각 79 — 권 16 절 2 「커버리지를 정하는 것은 표적이 아니라 분석 대역이다」
#  ⭐권의 헤드라인. 원장 핸들·헬퍼를 전부 함수 안에 두어 형제 절과 안 부딪치게 했다.
#
#  ⭐제목의 숫자는 **기준띠가 필요 없는 두 대역의 차**다. 대역외 기준띠 위 여유는 띠를
#    2600 Hz 한 자리에 놓아 얻은 값이라 자리를 옮기면 함께 움직인다 — 그래서 헤드라인은
#    같은 시계열 안에서 분모가 약분되는 «추적 몫 − 고정 몫» 으로 잡는다.
# =========================================================================== #
_F79 = from_json("outputs/ch1_elevation_figdata_r15.json")
TITLE_79 = (
    f"−75° 에서 추적 대역 몫은 고정 대역보다 "
    f"{float(_F79.get('cells.ours/el-75.share_track_db')) - float(_F79.get('cells.ours/el-75.share_fixed_db')):.2f}"
    f" dB 크고, 그 차이를 만든 것은 대역을 어디에 놓았는가 하나다")
REG["el-band-tracking"] = ("79", TITLE_79)


def blocks_79() -> list:
    FJ79 = "outputs/ch1_elevation_figdata_r15.json"
    F79 = from_json(FJ79)                                    # 앙각별 대역 몫 · 반송파 몫
    R79 = from_json("outputs/report07_three_engines.json")   # 고정 대역 상단의 출처

    def _ref79(no: str, anchor: str, short: str) -> str:
        # ⚠ `build_volumes._XREF` 는 «편 NN» 형태만 절 주소로 다시 배선한다.
        return f"[편 {no} «{short}»]({no}_{anchor}.ipynb)"

    def gapdb(key_hi: str, key_lo: str, fmt: str = "{:+.2f}") -> str:
        """두 칸의 차이 [dB] — **손으로 치지 않고** 원장에서 뺀다.

        출처는 파생 표기(`키 → 무엇을 했나`)로 단다. `report_style._resolve_cite` 가
        기준 키를 다시 열어 검사하고 각주에 «(파생)» 으로 남긴다.
        """
        v = float(F79.get(key_hi)) - float(F79.get(key_lo))
        short = key_lo.rsplit(".", 1)[-1]
        return f"{fmt.format(v)} dB ⟨{FJ79} : {key_hi} → 같은 칸의 {short} 를 뺀 값⟩"

    def width(key: str, what: str, src=None) -> str:
        """f_tip 에 0.65 를 곱한 대역폭 [Hz]. 역시 원장에서 계산한다."""
        S = src or F79
        return f"{0.65 * float(S.get(key)):.0f} Hz ⟨{S.path} : {key} → {what}⟩"

    def fig79(no: int, stem: str, question: str) -> list:
        return [f"![{stem}](../outputs/figures/{stem}.png)", "", caption(no, question)]

    ours = [f"ours/el{e}" for e in ("+0", "-15", "-30", "-45", "-60", "-75", "-90")]

    repro79 = dict(
        cmd=['CH1_TAG=_r15 CH1_N=8192 CH1_ARMS="ours_r15_n8192|Ours|#c62828;'
             'sionna_p4000000000_r15_n8192_d1|PathSolver physics off|#8e9aab;'
             'sionna_p4000000000_phys_r15_n8192_d1|PathSolver physics on|#1565c0" '
             "PYTHONPATH=src:benchmark python benchmark/build_ch1_elevation_figs.py",
             "CH1_TAG=_r15 PYTHONPATH=src:benchmark python "
             "benchmark/build_part79_normalization_fig.py"],
        out=["outputs/ch1_elevation_figdata_r15.json",
             "outputs/figures/ch1_f4_bandenergy_r15.png",
             "outputs/figures/part79_normalization_r15.png"],
        runtime="정규화 그림 약 1 초 (CPU). 앙각 그림 다섯 장의 시간은 미측정",
        note=f"두 스크립트 모두 원장을 읽어 CPU 로 FFT 한다⟨{FJ79} : _meta.gpu_ko⟩")

    return [
        header(
            num=79,
            title=TITLE_79,
            did="앙각 7 점의 같은 시계열에서 프로펠러 대역을 두 가지로 잡아 서로 견주고, "
                "같은 양을 세 정규화(전체 전력·반송파·대역외 기준띠)로 함께 냈다.",
            results=[
                f"−75° 에서 추적 대역 몫은 "
                f"{F79.num('cells.ours/el-75.share_track_db', fmt='{:+.2f}', unit='dB')}, "
                f"고정 대역 몫은 "
                f"{F79.num('cells.ours/el-75.share_fixed_db', fmt='{:+.2f}', unit='dB')} "
                f"— 차이 "
                f"{gapdb('cells.ours/el-75.share_track_db', 'cells.ours/el-75.share_fixed_db')} "
                f"다. 두 몫의 분모가 같은 시계열이라 이 차는 대역 선택 하나만 담는다.",

                "고정 대역이 비는 것은 대역 산수가 정한다 — 그 하단이 그 앙각의 f_tip 보다 "
                "위라 겹치는 폭이 0 이다.",

                f"같은 폭 대역외 기준띠로 견주면 추적 대역은 그 띠 위 "
                f"{gapdb('cells.ours/el-75.share_track_db', 'cells.ours/el-75.share_track_oob_db')}, "
                f"고정 대역은 "
                f"{gapdb('cells.ours/el-75.share_fixed_db', 'cells.ours/el-75.share_fixed_oob_db')} "
                f"로 띠 높이에 앉는다 — 이 두 여유는 띠를 2.6 kHz 한 자리에 놓아 얻은 값이다.",

                f"−75° 추적 대역이 담은 것은 f_flash 의 1·2 차 빗살이고, 그 선의 SNR 은 "
                f"{F79.num('cells.ours/el-75.comb_snr_db[0]', fmt='{:.1f}', unit='dB')} 와 "
                f"{F79.num('cells.ours/el-75.comb_snr_db[1]', fmt='{:.1f}', unit='dB')} 다.",

                f"−60° 에서는 반송파 몫이 "
                f"{F79.num('cells.ours/el-60.carrier_share_db', fmt='{:+.2f}', unit='dB')} "
                f"로 내려앉아 «전체 대비» 몫이 혼자 뛴다 — 그래서 반송파 기준 "
                f"{F79.num('cells.ours/el-60.share_track_rel_carrier_db', fmt='{:+.2f}', unit='dB')} "
                f"를 나란히 싣는다.",
            ],
            method=[
                ("추적 대역", F79.num("_meta.band_track_ko")),
                ("고정 대역", F79.num("_meta.band_fixed_ko") + " — 그 상단은 "
                 + R79.num("_meta.f_tip_hz", fmt="{:.1f}", unit="Hz") + " 다"),
                ("바닥 잣대", F79.num("_meta.oob_ko")),
                ("몫의 정의", F79.num("_meta.share_ko")),
                ("스펙트럼", F79.num("_meta.spectrum_ko")),
                ("정규화 둘", "전체 전력 대비 몫과 반송파(동체선) 대비 몫을 칸마다 함께 낸다"),
            ],
            prereq=[(_ref79("78", "el-sweep-design", "스윕 설계"),
                     "앙각 7 점이 무엇을 어떤 잣대로 쟀고 어느 행을 인용해도 되나")],
            repro=repro79,
        ),

        md("## 프로펠러 대역은 앙각을 따라 내려간다", "",
           "블레이드 끝이 만드는 도플러는 **날개끝 주파수 f_tip** 에서 멈춘다 — 기체에서 가장 "
           "빠른 산란체가 날개끝이기 때문이다. 그 f_tip 은 관측 앙각을 내리면 함께 "
           "내려간다.", "",
           f"우리 팔의 표를 그대로 읽으면 f_tip 은 0° 의 "
           f"{F79.num('cells.ours/el+0.f_tip_hz', fmt='{:.1f}', unit='Hz')} 에서 −75° 의 "
           f"{F79.num('cells.ours/el-75.f_tip_hz', fmt='{:.1f}', unit='Hz')} 로 내려가고, "
           f"−90° 에서 {F79.num('cells.ours/el-90.f_tip_hz', fmt='{:.1f}', unit='Hz')} 가 된다 "
           f"— cos(el) 을 곱한 값 그대로다.", "",
           "그러니 **대역을 어디에 놓느냐**가 판정을 정한다. 여기서는 두 가지로 놓고 잰다."),

        md("## 두 대역, 그리고 바닥을 읽는 자", "",
           table(["대역", "어디에 놓나", "−75° 에서의 폭"], [
               ["추적 대역", F79.num("_meta.band_track_ko"),
                width("cells.ours/el-75.f_tip_hz", "0.65 를 곱한 추적 대역 폭")],
               ["고정 대역", "8/11 덱이 −15° 의 f_tip 으로 못 박은 자리에 그대로 둔다",
                width("_meta.f_tip_hz", "0.65 를 곱한 고정 대역 폭", src=R79)],
           ]), "",
           f"두 대역 모두 **자기와 같은 폭의 대역외 기준띠**와 견준다"
           f"⟨{FJ79} : _meta.oob_ko⟩. 그 띠는 2.6 kHz 위에 있어 블레이드가 원리적으로 못 오는 "
           f"자리다 — 대역 몫이 그 띠와 같으면 그것은 신호가 아니라 **바닥**이다."),

        md("## −75° 한 자리에서 두 대역이 갈린다", "",
           table(["무엇을", "대역 몫", "같은 폭 기준띠", "띠 위 여유"], [
               ["추적 대역, −75°",
                F79.num("cells.ours/el-75.share_track_db", fmt="{:+.2f}", unit="dB"),
                F79.num("cells.ours/el-75.share_track_oob_db", fmt="{:+.2f}", unit="dB"),
                gapdb("cells.ours/el-75.share_track_db",
                      "cells.ours/el-75.share_track_oob_db")],
               ["고정 대역, −75°",
                F79.num("cells.ours/el-75.share_fixed_db", fmt="{:+.2f}", unit="dB"),
                F79.num("cells.ours/el-75.share_fixed_oob_db", fmt="{:+.2f}", unit="dB"),
                gapdb("cells.ours/el-75.share_fixed_db",
                      "cells.ours/el-75.share_fixed_oob_db")],
               ["고정 대역, −90°",
                F79.num("cells.ours/el-90.share_fixed_db", fmt="{:+.2f}", unit="dB"),
                F79.num("cells.ours/el-90.share_fixed_oob_db", fmt="{:+.2f}", unit="dB"),
                gapdb("cells.ours/el-90.share_fixed_db",
                      "cells.ours/el-90.share_fixed_oob_db")],
           ])),

        md(f"추적 대역은 −75° 에서 고정 대역보다 좁다. 좁은 대역이 전체 전력의 "
           f"{gapdb('cells.ours/el-75.share_track_db', 'cells.ours/el-75.share_fixed_db')} "
           f"만큼 더 큰 몫을 가져갔다는 것은 그 에너지가 거기에 **몰려 있다**는 뜻이다. "
           f"두 몫의 분모가 같은 시계열이라 이 차는 대역 선택 하나만 담는다.", "",
           f"고정 대역이 비는 것은 대역 산수가 정한다 — 그 하단 430.1 Hz 가 −75° 의 f_tip "
           f"{F79.num('cells.ours/el-75.f_tip_hz', fmt='{:.1f}', unit='Hz')} 보다 위라 "
           f"겹치는 폭이 "
           f"{F79.num('prediction.fixed_band_overlap_frac.-75', fmt='{:.4f}')} 다."),

        md("## −75° 의 추적 대역을 채운 것은 저차 빗살이다", "",
           f"f_flash 의 정수배에 선 빗살 선 SNR 을 원장이 30 차까지 싣는다"
           f"⟨{FJ79} : _meta.comb_ko⟩. −75° 에서 추적 대역(115.3~329.5 Hz)에 드는 차수는 "
           f"1·2 차이고, 그 두 선은 "
           f"{F79.num('cells.ours/el-75.comb_snr_db[0]', fmt='{:.1f}', unit='dB')} 와 "
           f"{F79.num('cells.ours/el-75.comb_snr_db[1]', fmt='{:.1f}', unit='dB')} 로 서 있다. "
           f"덱 대역이 담는 4~9 차는 같은 칸에서 "
           f"{F79.num('cells.ours/el-75.comb_snr_db[7]', fmt='{:.1f}', unit='dB')} ~ "
           f"{F79.num('cells.ours/el-75.comb_snr_db[6]', fmt='{:.1f}', unit='dB')} 다.", "",
           "f_flash 는 앙각과 무관하고 f_tip 만 cos(el) 로 줄기 때문에, 창이 담는 차수는 "
           "앙각이 내려갈수록 낮아진다. −75° 에서 추적 대역이 얻는 이득은 날개끝 신호를 지킨 "
           "대가라기보다 창이 가장 센 저차 빗살 위로 내려앉은 결과다."),

        md(f"−90° 는 f_tip 이 0 이라 추적 대역의 폭도 0 이다 — 그 칸은 «측정 불가» 로 "
           f"비워 뒀다⟨{FJ79} : cells.ours/el-90.share_track_db⟩. 값이 비는 이유는 신호가 "
           f"약해서가 아니라 **잴 대역이 없어서**다.", "",
           f"같은 −90° 에서 고정 대역 "
           f"{F79.num('cells.ours/el-90.share_fixed_db', fmt='{:+.2f}', unit='dB')} 와 그 "
           f"기준띠 "
           f"{F79.num('cells.ours/el-90.share_fixed_oob_db', fmt='{:+.2f}', unit='dB')} 는 "
           f"{gapdb('cells.ours/el-90.share_fixed_db', 'cells.ours/el-90.share_fixed_oob_db')} "
           f"안에서 같다. 같다는 것은 두 띠에 **같은 f_flash 빗살이 지나간다**는 뜻이다 — "
           f"고정 대역 안 차수 4~9 는 국소 바닥 위 "
           f"{F79.num('cells.ours/el-90.comb_snr_db[3]', fmt='{:.1f}', unit='dB')} ~ "
           f"{F79.num('cells.ours/el-90.comb_snr_db[6]', fmt='{:.1f}', unit='dB')}, 기준띠 안 "
           f"차수 21~26 은 "
           f"{F79.num('cells.ours/el-90.comb_snr_db[23]', fmt='{:.1f}', unit='dB')} ~ "
           f"{F79.num('cells.ours/el-90.comb_snr_db[20]', fmt='{:.1f}', unit='dB')} 로 서 "
           f"있다. 이 잣대가 −90° 에서 재는 것은 «대역이 비었나» 라기보다 «블레이드만의 "
           f"초과분이 있나» 이고, 그 초과분은 0.17 dB 안에서 0 이다."),

        md(*fig79(1, "ch1_f4_bandenergy_r15",
                  "앙각을 내리면 프로펠러 대역 에너지가 정말 주는가?"), "",
           "점선이 각 팔의 대역외 기준띠다. **자기 점선 위에 앉은 표식은 바닥에 앉은 것**이고, "
           "오른쪽 패널의 −75°·−90° 에서 붉은 선이 정확히 그렇게 된다."),

        md("## 앙각 7 점 전부", "",
           table_from(
               (FJ79, "cells"),
               [("칸", None),
                ("f_tip [Hz]", "f_tip_hz"),
                ("추적 몫 [dB]", "share_track_db"),
                ("추적 기준띠 [dB]", "share_track_oob_db"),
                ("고정 몫 [dB]", "share_fixed_db"),
                ("고정 기준띠 [dB]", "share_fixed_oob_db")],
               fmt={"f_tip_hz": "{:.1f}", "share_track_db": "{:+.2f}",
                    "share_track_oob_db": "{:+.2f}", "share_fixed_db": "{:+.2f}",
                    "share_fixed_oob_db": "{:+.2f}"},
               null="측정 불가", order=ours)),

        md(f"추적 대역이 자기 대역외 기준띠 위로 서는 여유는 f_tip 이 살아 있는 여섯 앙각에서 "
           f"−15° 의 "
           f"{gapdb('cells.ours/el-15.share_track_db', 'cells.ours/el-15.share_track_oob_db')} "
           f"가 가장 좁고 −75° 의 "
           f"{gapdb('cells.ours/el-75.share_track_db', 'cells.ours/el-75.share_track_oob_db')} "
           f"가 가장 넓다. 이 여유는 한 칸 안에서 두 대역의 비라 팔마다 다른 절대 눈금과 "
           f"무관하다.", "",
           f"같은 여섯 점을 전체 전력 대비 «몫» 으로 보면 −15° 의 "
           f"{F79.num('cells.ours/el-15.share_track_db', fmt='{:+.2f}', unit='dB')} 와 −60° 의 "
           f"{F79.num('cells.ours/el-60.share_track_db', fmt='{:+.2f}', unit='dB')} 사이, 폭 "
           f"{F79.num('gates.G6_ours_track_share_span_db', fmt='{:.1f}', unit='dB')} 안에 "
           f"흩어진다. 그 폭은 잣대를 바꾸면 달라진다 — 기준띠 위 여유로는 29.64 dB, 반송파 "
           f"기준으로는 28.11 dB 다. 앙각이 내려가는 동안 몫은 단조롭지 않다: −15°, −30°, "
           f"−45°, −60° 가 각각 "
           f"{F79.num('cells.ours/el-30.share_track_db', fmt='{:+.2f}', unit='dB')} 와 "
           f"{F79.num('cells.ours/el-45.share_track_db', fmt='{:+.2f}', unit='dB')} 를 사이에 "
           f"두고 오르내린다.", "",
           f"고정 대역도 −60° 까지는 자기 기준띠 위로 "
           f"{gapdb('cells.ours/el-60.share_fixed_db', 'cells.ours/el-60.share_fixed_oob_db')} "
           f"남아 있다가 −75° 에서 그 띠에 닿는다. 그 지점부터 고정 대역은 f_tip 위에 "
           f"통째로 놓인다."),

        md("## 분모를 바꿔도 같은 결론이 서는가", "",
           *fig79(2, "part79_normalization_r15",
                  "전체 전력으로 나눈 몫과 반송파로 나눈 몫이 어디서 갈라지는가?")),

        md(table_from(
            (FJ79, "cells"),
            [("칸", None),
             ("반송파 몫 [dB]", "carrier_share_db"),
             ("전체 대비 추적 몫 [dB]", "share_track_db"),
             ("반송파 대비 추적 몫 [dB]", "share_track_rel_carrier_db")],
            fmt={"carrier_share_db": "{:+.2f}", "share_track_db": "{:+.2f}",
                 "share_track_rel_carrier_db": "{:+.2f}"},
            null="측정 불가", order=ours)),

        md(f"몫의 분모는 **전체 전력**이고, 그 전력의 대부분은 동체선(반송파)이다 — 우리 팔의 "
           f"반송파 몫은 −60° 를 뺀 여섯 점에서 "
           f"{F79.num('cells.ours/el-15.carrier_share_db', fmt='{:+.2f}', unit='dB')} ~ "
           f"{F79.num('cells.ours/el-30.carrier_share_db', fmt='{:+.2f}', unit='dB')} 안에 "
           f"있다. 그래서 반송파가 내려앉는 칸에서는 분자가 그대로여도 몫이 올라간다. −60° 가 "
           f"그 자리다 — 반송파 몫이 "
           f"{F79.num('cells.ours/el-60.carrier_share_db', fmt='{:+.2f}', unit='dB')} 로 "
           f"내려앉고, 전체 대비 추적 몫 "
           f"{F79.num('cells.ours/el-60.share_track_db', fmt='{:+.2f}', unit='dB')} 가 우리 팔 "
           f"여섯 점 중 가장 커진다."),

        md(f"이 내려앉음은 **우리 팔 한 칸의 성질이다.** 같은 "
           f"−60° 에서 물리를 끈 PathSolver 는 "
           f"{F79.num('cells.sionna_off/el-60.carrier_share_db', fmt='{:+.2f}', unit='dB')}, 켠 판은 "
           f"{F79.num('cells.sionna_on/el-60.carrier_share_db', fmt='{:+.2f}', unit='dB')} "
           f"로 다른 앙각과 같다.", "",
           f"정규화를 반송파로 바꾸는 것은 이 칸을 되돌려 놓지 못한다 — 전체 전력의 대부분이 "
           f"반송파라 두 분모가 함께 내려앉기 때문이다. 반송파 기준으로 재면 −60° 는 "
           f"{F79.num('cells.ours/el-60.share_track_rel_carrier_db', fmt='{:+.2f}', unit='dB')} "
           f"로 우리 팔 여섯 점 중 유일한 양수가 되어 오히려 더 튄다.", "",
           f"분모가 약분되는 잣대는 **같은 폭의 대역외 기준띠와의 여유**다. 그 잣대에서 −60° 는 "
           f"{gapdb('cells.ours/el-60.share_track_db', 'cells.ours/el-60.share_track_oob_db')} "
           f"로 0° 의 "
           f"{gapdb('cells.ours/el+0.share_track_db', 'cells.ours/el+0.share_track_oob_db')} · "
           f"−45° 의 "
           f"{gapdb('cells.ours/el-45.share_track_db', 'cells.ours/el-45.share_track_oob_db')} "
           f"와 나란하고, −75° 가 "
           f"{gapdb('cells.ours/el-75.share_track_db', 'cells.ours/el-75.share_track_oob_db')} "
           f"로 가장 높다. 헤드라인 자리인 −75° 는 반송파 몫이 "
           f"{F79.num('cells.ours/el-75.carrier_share_db', fmt='{:+.2f}', unit='dB')} 로 통상값 "
           f"안에 있어, 전체 대비와 반송파 대비가 여섯 점 중 같은 순위를 준다"
           f"⟨{FJ79} : cells.ours/el-75.share_track_rel_carrier_db⟩."),

        md("## 대역에 무언가 남는 것과 프로펠러가 보이는 것은 다른 일이다", "",
           table_from(
               (FJ79, "cells"),
               [("칸", None),
                ("고정 몫 [dB]", "share_fixed_db"),
                ("기준띠 [dB]", "share_fixed_oob_db"),
                ("f_tip [Hz]", "f_tip_hz")],
               fmt={"share_fixed_db": "{:+.2f}", "share_fixed_oob_db": "{:+.2f}",
                    "f_tip_hz": "{:.1f}"},
               order=["ours/el-75", "sionna_off/el-75", "sionna_on/el-75",
                      "ours/el-90", "sionna_off/el-90", "sionna_on/el-90"])),

        md(f"−75° 에서 고정 대역은 f_tip = "
           f"{F79.num('cells.ours/el-75.f_tip_hz', fmt='{:.1f}', unit='Hz')} 위에 통째로 "
           f"놓인다 — 겹치는 폭이 "
           f"{F79.num('prediction.fixed_band_overlap_frac.-75', fmt='{:.4f}')} 다. 우리 팔은 그 "
           f"자리를 기준띠 높이로 비워 둔다. PathSolver 두 팔은 갈린다 — 물리를 끈 팔은 "
           f"{gapdb('cells.sionna_off/el-75.share_fixed_db', 'cells.sionna_off/el-75.share_fixed_oob_db')} "
           f"를 채워 넣고, 켠 팔은 "
           f"{gapdb('cells.sionna_on/el-75.share_fixed_db', 'cells.sionna_on/el-75.share_fixed_oob_db')} "
           f"로 우리 팔과 마찬가지로 띠 높이에 앉는다."),

        md(f"⭐그 세 숫자가 재는 범위는 여기까지다. 기준띠에도 빗살 21~26 차가 들어 있어서, "
           f"이 여유는 «빗살 든 칸 대 빈 칸» 이 아니라 **빗살 대 빗살**의 대비다 — 같은 "
           f"−75° 에서 물리를 끈 팔의 고정 대역 차수 4~9 는 국소 바닥 위 "
           f"{F79.num('cells.sionna_off/el-75.comb_snr_db[7]', fmt='{:.1f}', unit='dB')} ~ "
           f"{F79.num('cells.sionna_off/el-75.comb_snr_db[3]', fmt='{:.1f}', unit='dB')} 이고, "
           f"기준띠 차수 21~26 은 "
           f"{F79.num('cells.sionna_off/el-75.comb_snr_db[24]', fmt='{:.1f}', unit='dB')} ~ "
           f"{F79.num('cells.sionna_off/el-75.comb_snr_db[21]', fmt='{:.1f}', unit='dB')} 다. "
           f"빗살의 간격은 회전 입력 f_flash 가 정하므로, 빗살이 섰다는 사실은 산란 커널의 "
           f"점수와 다른 물건이다.", "",
           f"가르는 것은 대역을 f_tip 따라 옮겼을 때다 — 같은 −75° 에서 우리 팔의 추적 대역은 "
           f"자기 기준띠보다 "
           f"{gapdb('cells.ours/el-75.share_track_db', 'cells.ours/el-75.share_track_oob_db')} "
           f"높다. 빗살이 f_tip 위에서도 살아남는다는 것은 관측 사실이고, 그 빗살이 블레이드 "
           f"도플러인지 자세별 경로 집합의 깜빡임인지는 "
           + _ref79("87", "budget-not-physics", "광선 예산")
           + " 이 예산 축에서 가른다."),

        next_steps([
            ("검출기의 도플러 대역을 앙각 추정값의 f_tip 에 묶는다",
             "−75° 이하에서 고정 대역이 잃는 여유를 추적 대역이 되찾는지가 검출 확률로 결정된다",
             "`src/passive_process.py` 의 대역 설정"),
            ("−75° 와 −90° 사이에 앙각 한 점을 더 잰다",
             "추적 대역의 폭이 언제 0 으로 닫히는지가 관측으로 정해진다",
             "`benchmark/elevation_sweep_md.py --els -82.5`"),
            ("기하 겹침 예측을 이 두 대역 위에서 다시 채점한다",
             "«대역이 겹치는 만큼 에너지가 준다» 는 예측의 성립 범위가 확정된다",
             "`outputs/ch1_elevation_figdata_r15.json` 의 "
             "`prediction.fixed_band_overlap_frac`"),
        ]),
    ]


# =========================================================================== #
#: 이 파일이 짓는 조각들. ⚠다른 절을 맡은 사람은 **자기 행만** 더한다.
REPORTS = [
    ("78", "el-sweep-design", blocks_78,
     ["outputs/elevation_sweep_md.json", "outputs/ch1_elevation_figdata_r15.json",
      "outputs/report07_three_engines.json"]),
    ("79", "el-band-tracking", blocks_79,
     ["outputs/ch1_elevation_figdata_r15.json",
      "outputs/report07_three_engines.json"]),
    ("80", "el-above-tip-limit", blocks_80,
     ["outputs/wideband_energy_r15.json", "outputs/elevation_sweep_md.json"]),
    #: ⚠조각 82 만 옛 10 m 판의 진단 원장을 쓴다 — 그 사실은 조각 안에 적혀 있다.
    ("82", "el-nadir-floor", blocks_82,
     ["outputs/verify_nadir_flash.json",
      "outputs/refute_nadir_mechanism_final.json",
      "outputs/ch1_elevation_figdata.json",
      "outputs/elevation_sweep_md.json"]),
]


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    print("── 권 16 「앙각 커버리지」 조각 빌드 ──")
    for entry in REPORTS:          # (번호, 앵커, blocks 함수[, 근거 원장]) — 넷째 칸은 선택
        no, anchor, fn = entry[0], entry[1], entry[2]
        path = os.path.join(OUT, f"{no}_{anchor}.ipynb")
        rep = build_notebook(path, fn(), strict=True)
        write_shard(no, anchor, rep, entry[3] if len(entry) > 3 else [])
    print(f"✅ {len(REPORTS)} 조각 → {os.path.relpath(OUT, _ROOT)}/")


if __name__ == "__main__":
    main()
