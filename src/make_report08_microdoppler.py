# -*- coding: utf-8 -*-
"""
make_report08_microdoppler.py — ⭐**리포트 07 한 편을 네 편으로 쪼갠다** (사용자 지시 2026-08-10)

사용자:
> *"report07_microdoppler 의 전체적인 내용을 **쪼개서 새로운 레포트에** 넣도록 해.
>  이 파일 하나의 크기가 너무 커서 여러 개로 쪼개주면 좋겠어. 예: **08_1, 08_2, 08_3** 이런 식으로"*

왜 쪼개는가 — 크기와 메시지 둘 다
----------------------------------
옛 `report07_microdoppler.ipynb` 는 그림 14 장을 base64 로 박아 **23.4 MB** 였다. 열기도 무겁고,
한 편이 «시나리오 · 엔진 비교 · 무늬의 원인 · 표본화 한계» 네 이야기를 한꺼번에 했다.
⭐크기는 증상이고 원인은 **한 편에 메시지가 넷** 이었다는 것이다. 그래서 메시지 단위로 자른다.

    08_1  무엇을 보고 있나        시나리오·표적·측정모형        애니메이션 · f0 · f0c
    08_2  어떻게 계산하나        세 엔진과 거리                f12 · f8 · f5
    08_3  무엇이 무늬를 정하나    회전수·가림·산포              f1 · f2 · f3 · f4 · f7 · f11 · f13
    08_4  무엇을 잴 수 있나      광선 비용과 반복률            f9 · f10

⚠ 이 스크립트는 `src/make_report07_overview.py` 를 **대체**한다. 옛 빌더는 그대로 두되
  (되돌릴 수 있게) 산출물 `report07_microdoppler.ipynb` 는 더 쓰지 않는다.
⚠ 실행 순서: ① 조각 빌더 12 개 → ② **이 스크립트** → ③ `src/build_volumes.py`
  (build_volumes 가 08_3 뒤에 옛 조각 34~39 를 절로 덧붙인다)

    python src/make_report08_microdoppler.py
"""
from __future__ import annotations

import base64
import json
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, _HERE)

FIG = os.path.join(_ROOT, "outputs", "figures")
OUT = os.path.join(_ROOT, "reports")

# ── 원장 ────────────────────────────────────────────────────────────────────
MDB = json.load(open(f"{_ROOT}/outputs/report15b_microdoppler.json"))
TRI = json.load(open(f"{_ROOT}/outputs/report07_three_engines.json"))
MDP = json.load(open(f"{_ROOT}/outputs/report00_microdoppler.json"))
HOV = json.load(open(f"{_ROOT}/outputs/report07_hover_long.json"))["_meta"]
VERD = json.load(open(f"{_ROOT}/outputs/report15_verdict.json"))
RNGS = json.load(open(f"{_ROOT}/outputs/report07_sionna_ranges.json"))
W5G = json.load(open(f"{_ROOT}/outputs/report07_5g_waveform.json"))


def _opt(path):
    return json.load(open(path)) if os.path.exists(path) else None


HOD_J = _opt(f"{_ROOT}/outputs/report07_hover_long_outdoor.json")
HOD = HOD_J["_meta"] if HOD_J else None
ANIM = _opt(f"{_ROOT}/outputs/report07_anim.json")
_HAS_ANIM = bool(ANIM) and os.path.exists(f"{FIG}/report07_anim.gif")
_HAS_F13 = os.path.exists(f"{FIG}/report07_f13.png")
RBT = _opt(f"{_ROOT}/outputs/report07_ray_budget_test.json")
# ⭐야외 산포 프리셋의 근거 — 공개 비행로그 세 종을 직접 열어 잰 값(그림 f13 과 같은 원장).
RLT = _opt(f"{_ROOT}/outputs/rotor_log_traces.json")
_RLS = (RLT or {}).get("sources", {})
#: 로그 세 종의 «설명» 칸 — 숫자는 전부 원장에서 읽고, 여기엔 무엇인지만 적는다.
_RL_DESC = [("neurobem", "NeuroBEM (UZH RPG)", "레이싱 쿼드 · **실내** 무풍",
             "모터별 실측 회전수"),
            ("px4", "PX4 · CODEV AQUILA V3", "상용 대형 쿼드 · **야외**", "ESC 실측 rpm"),
            ("dji", "DJI Phantom 3 DAT", "⭐**진짜 DJI** · 야외", "모터 PWM **명령**")]


def _rl_rows() -> str:
    rows = []
    for k, nm, venue, sig in _RL_DESC:
        s = _RLS.get(k)
        if s is None:
            continue
        rows.append(f"| {nm} | {venue} | {sig} {s['fs_hz']:.0f} Hz | "
                    f"{s['static_std_pct']['median']:.2f} % | "
                    f"{s['wobble_amp_pct']['median']:.2f} % @ "
                    f"{s['wobble_peak_hz']['median']:.2f} Hz |")
    return "\n".join(rows)
TRR_J = _opt(f"{_ROOT}/outputs/report07_three_engine_ranges.json")
TRR = TRR_J["ranges"] if TRR_J else None
# ⭐변조 깊이를 p-p 와 p5~p95 두 자로 잰 원장(benchmark/ledger_ptp_robust.py).
#   본문에 손으로 적혀 있던 수치를 이것으로 갈음한다.
DEP = _opt(f"{_ROOT}/outputs/report07_depth_robust.json")
# ⭐대역밖 전력의 잣대 — 평활 없는 절대 대역 전력, 정규화는 전체 전력(분모를 이름에 박았다).
OOB = json.load(open(f"{_ROOT}/outputs/outofband_power.json"))
OOBE = {r["label"]: r for r in OOB["three_engines"]}
SGC = json.load(open(f"{_ROOT}/outputs/sbr_grid_convergence.json"))
#: λ/12 = 생산 기본 간격. 사다리에 칸이 늘어도 어긋나지 않게 **div 로** 찾는다.
SGF = next(r for r in SGC["in_band_fidelity"]["rows"] if r["div"] == 12)
SGL = SGC["in_band_fidelity"]["rows"]                          # 격자 사다리 전체
SG12 = next(r for r in SGC["rows"] if r["div"] == 12)          # 광선 수·조명점 수
# ⭐ 얼린 광선 격자 배선의 계약 게이트 · 블레이드 플래시 사다리 · 8 m 시드 조사
FRZ = _opt(f"{_ROOT}/outputs/verify_frozen_grid.json")
BFL = _opt(f"{_ROOT}/outputs/report15_blade_flash_ladder.json")
PRB = _opt(f"{_ROOT}/outputs/probe_8m_anomaly.json")
# ⭐ 얼린 판으로 원장을 다시 낸 **전후 비교표** — 이 편의 «광선 격자를 어디에 매나» 절이 읽는다.
#   27 열을 같은 잣대(레벨 · 변조 깊이 · 대역밖 절대 전력 · 진폭 상관)로 잰 원장이다.
FBA = _opt(f"{_ROOT}/outputs/freeze_before_after.json")
# ⭐표시 규약(조각 길이·hop·패딩)의 정본은 코드다 — 본문에 손으로 적지 않고 거기서 읽는다.
from md_mapstyle import (ARM_PO, ARM_SBR, ARM_SIONNA, FLASH_HOP,   # noqa: E402
                         FLASH_PAD, auto_periods)

RGM, RGR = RNGS["_meta"], RNGS["ranges"]
WM, WA = W5G["_meta"], W5G["arms"]
#: 5G 절의 «도플러 → 속도» 환산에 쓰는 파장 — 손으로 적지 않는다.
LAM5G = 299792458.0 / WM["fc_hz"]
LEAD = MDB["cells"]["matrice4e/belly"]
PH, FND, ARM = LEAD["physics"], LEAD["findings"], LEAD["arms"]
TM = TRI["_meta"]
R = FND["rpm_spread_makes_it_time_varying"]
# ⭐코사인 판정 칸은 그림 빌더(benchmark/build_three_engine_fig.py)가 같은 원장에 덧쓴다.
#   원장이 다시 계산되는 동안에는 그 칸이 비어 있으므로, 빌드를 죽이지 말고
#   본문에 «재계산 대기» 로 적는다 — 원장이 채워지면 다시 돌리는 것만으로 숫자가 돌아온다.
PENDING = "⏳재계산 대기"
_VJ = (TRI.get("verdict") or {}).get("cosine_in_ftip") or {}
V = {k: _VJ.get(k) for k in ("sionna_vs_sbr", "sionna_vs_po", "sbr_vs_po")}


def cos3(key: str) -> str:
    v = V.get(key)
    return PENDING if v is None else f"{v:.3f}"


CEN = MDP["specular_census"]["total"]
SPREAD = float(MDB["_meta"]["rpm_spread_frac"])
FARFIELD_M = next(r for r in MDP["rows"] if r["drone"] == "matrice4e")["farfield_m"]
# ⭐원거리장 경계는 **D 를 무엇으로 잡느냐**에 따라 배로 달라진다. 이 편이 쓰는 값은
#   «수평 최대치수» 정의이고, 15 권은 가장 보수적인 정의(로터 디스크까지 감싸는 3D 대각)를
#   채택한다. 이름만 같고 값이 다르면 두 권이 서로를 반박하는 것처럼 읽히므로, 이 편의 표는
#   **정의를 이름에 박고** 보수적인 짝을 나란히 적는다 — 둘 다 같은 원장에서 읽는다.
_PRB = json.load(open(f"{_ROOT}/outputs/report15_probe.json"))
_PRBPH = _PRB["airframes"]["matrice4e"]["physics"]
FF_D_H_M = float(_PRBPH["D_horizontal_m"])           # 이 편이 쓴 D (수평 최대치수)
FF_D_3D_M = float(_PRBPH["D_diag3d_m"])              # 보수적 D (메쉬 3D 대각)
FARFIELD_3D_M = float(_PRBPH["farfield_diag3d_m"])   # 그 D 로 다시 잡은 경계


def _tail_gap(drone: str) -> float:
    c = VERD["tail_excess"]["by_cell"][f"{drone}/3/nose"]
    return c["sionna_tail"]["mean_db"] - c["po_tail"]["mean_db"]


GAP_MINI2, GAP_M4E = _tail_gap("mini2"), _tail_gap("matrice4e")

# ── 파생값 — 손으로 적지 않고 여기서 한 번만 계산한다 ───────────────────────
#: 표시 조각(정본 `src/md_mapstyle.py`) — 이 원장의 PRF·f_flash 에서 나오는 값.
SEG_PER = auto_periods(TM["prf_hz"], TM["f_flash_hz"])
SEG_N = round(SEG_PER * TM["prf_hz"] / TM["f_flash_hz"])
SEG_MS = SEG_PER / TM["f_flash_hz"] * 1e3
SEG_HZ = TM["f_flash_hz"] / SEG_PER
#: 두 팔의 «레벨 차» — 단위가 다르므로 환산항을 빼고 남는 몫까지 여기서 낸다.
_LVL = TRI.get("levels_db") or {}
RANGE_M = float(TM.get("range_m", 3.0))
CONV_DB = -20.0 * math.log10(4.0 * math.pi * RANGE_M ** 2)     # 수신 전력장 ↔ 산란 진폭
GAP_DB = (_LVL["sionna"] - _LVL["sbr"]) if {"sionna", "sbr"} <= set(_LVL) else None
RESID_DB = None if GAP_DB is None else GAP_DB - CONV_DB


def num(v, fmt="{:.1f}") -> str:
    """원장에 아직 그 칸이 없으면 «재계산 대기» 로 적는다 — 손으로 채우지 않는다."""
    return PENDING if v is None else fmt.format(v)


#: 코사인 칸이 통째로 비어 있으면 맵 원장이 다시 계산되는 중이다.
MAPS_PENDING = all(v is None for v in V.values())
#: 맵을 낸 SBR 팔이 **얼린 격자**로 풀렸나 — 맵 스크립트가 원장에 직접 적는 표식이다.
SBR_GRID_FROZEN = bool(((TRI.get("engines") or {}).get("sbr") or {}).get("grid_frozen"))
#: 대조군(가림 없는 순수 PO) 라벨 — 표·산문에서 한 이름만 쓴다.
#  ⭐이름의 정본은 `src/md_mapstyle.py` 다 — 8-5(바이스태틱)도 같은 자리에서 받아야
#    같은 표의 같은 행이 두 편에서 같은 이름으로 읽힌다.
CTRL = ARM_PO


def _pending_note() -> str:
    """맵 원장이 다시 계산되는 중일 때만 절 머리에 뜬다(끝나면 저절로 사라진다)."""
    if not MAPS_PENDING:
        return ""
    return ("> ⏳ **재계산 대기** — 세 엔진 맵을 다시 푸는 중이다. 이 편의 **그림**과 "
            "**Sionna 팔에서 파생된 수치**(스펙트럼 코사인 · 깊이 표와 대역밖 표의 Sionna 행 · "
            "두 팔의 레벨 차)는 그 계산이 끝나고 파생 원장을 다시 내야 맞는다. 우리 두 팔"
            "(SBR · 대조군)의 수치는 현재 원장 그대로다.\n")


#: 격자 사다리에서 «지금 우리가 쓰는 팔» 의 칸 — 얼렸으면 얼린 팔을 인용해야 한다.
_LADDER_KEY = "cos_froz_vs_po" if SBR_GRID_FROZEN else "cos_prod_vs_po"


def _plate(meta, grid_ref=None) -> str:
    """원장 하나가 어떤 광선 격자로 풀렸는지 — 표식이 없으면 «옛 판» 이다(추측하지 않는다)."""
    if not meta:
        return "—"
    if not meta.get("grid_frozen"):
        return "⚠자세마다 다시 정의"
    g = grid_ref or meta.get("grid_ref") or {}
    return f"얼림 (한 변 {g['n']} 칸)" if g.get("n") else "얼림"


def _stamp(meta) -> str:
    """원장이 언제 났나 — 열을 다시 푼 라운드가 있으면 그 시각을 쓴다."""
    return (meta.get("regenerated") or meta.get("generated") or "")[:16]


_PLATE_TRI = _plate(TM, ((TRI.get("engines") or {}).get("sbr") or {}).get("grid_ref"))
_PLATE_R15B = _plate(MDB["_meta"])
_PLATE_HOV = _plate(HOV)
_PLATE_HOD = _plate(HOD)


def _grid_state_08_3() -> str:
    """8-3 의 맵이 어떤 광선 격자 위에 서 있나 — 원장의 표식에서 읽는다."""
    frozen = [k for k, m in (("f1 · f4", MDB["_meta"]), ("f7", HOV), ("f11", HOD))
              if m and m.get("grid_frozen")]
    if not frozen:
        return ("⚠ **이 편의 맵이 어떤 광선 격자 위에 서 있나.** 우리 SBR 팔은 광선 격자의 "
                "중심·반경·칸수를 자세마다 표적 경계상자에서 다시 잡는다 — 프로펠러가 돌면 "
                "그 자가 프레임마다 움직이고, 그 움직임이 슬로타임에 **광대역 바닥**으로 실린다. "
                "**이 편의 맵과 수치는 아직 그 판이다 — ⏳재계산 대기.**")
    return ("⭐ **이 편의 맵은 얼린 광선 격자 위에 서 있다**(" + " · ".join(frozen) + "). "
            "자를 자세마다 다시 놓으면 자의 움직임이 표적의 운동으로 기록되는데, 이 편의 맵은 "
            "판 한 장을 모든 자세가 함께 쓰는 계산으로 다시 났다. 전후 비교(레벨 · 변조 깊이 · "
            "대역밖 전력 · 가산성)는 [08_2 «광선 격자를 어디에 매나»](08_2_engines.ipynb) 가, "
            "기전과 대가는 [리포트 5 «우리 커널 — 무엇이고, 무엇이 아닌가»](05_kernel.ipynb) 가 "
            "낸다. ⚠ **f3 만 예외다** — 그 그림의 밴드별 깊이는 옛 판에서 잰 값이라 절대 dB 를 "
            "인용하지 마라(8-4 의 «그림별 데이터 이력» 참조).")


def _oob_rank_line() -> str:
    """SBR ↔ Sionna 의 대역밖 대소 — «위/아래» 도 «뒤집히나» 도 원장에서 읽는다."""
    rk = OOB["three_engines_ranking"]
    head = rk["sbr_over_sionna_db"]["new_frac_of_total"]      # + 면 SBR 이 위
    band = rk["sbr_over_sionna_db"]["secondary_out_over_in"]
    sec = rk["secondary_out_over_in"]["values_pct"]
    flipped = (head > 0) != (band > 0)
    s = ("⭐ **분모를 밝히지 않고는 대소를 쓰지 않는다.** 전체 전력 대비로는 SBR 이 Sionna 보다 "
         f"{abs(head):.1f} dB {'위' if head > 0 else '아래'}이고, 대역비"
         f"(f_tip 밖 / 블레이드 대역)로 재면 Sionna {sec['sionna']:.1f} % 대 SBR "
         f"{sec['sbr']:.1f} % 로 ")
    if flipped:
        return s + ("**순서가 뒤집힌다**. 그 대역비를 헤드라인으로 쓰지 않는 이유는 분모 자체가 "
                    "격자 잡음으로 부풀어 있기 때문이다.")
    return s + (f"**같은 순서**다({abs(band):.1f} dB 차). 두 잣대가 갈리지 않으므로 이 표의 "
                "대소는 정규화 선택에 안 걸린다 — 그래도 헤드라인은 분모를 이름에 박은 "
                "`frac_of_total` 로만 쓴다.")


def _cosine_order_line() -> str:
    """세 코사인의 대소를 원장에서 읽어 문장으로 — 손으로 순서를 적지 않는다."""
    if MAPS_PENDING:
        return f"⏳ 세 자리의 대소는 원장이 다시 나야 적을 수 있다 — {PENDING}."
    nm = {"sbr_vs_po": "우리 두 팔끼리", "sionna_vs_sbr": "Sionna↔우리 기본팔",
          "sionna_vs_po": "Sionna↔대조군"}
    order = sorted(V, key=lambda k: -V[k])
    return ("⭐ **이 실행의 대소** — " + " > ".join(f"{nm[k]} {V[k]:.3f}" for k in order)
            + ". " + ("우리 두 팔이 서로 가장 닮았고, Sionna 는 그 둘에서 비슷한 거리만큼 "
                      "떨어져 있다 — 광선을 쓰는 두 구현(Sionna·우리 SBR)이 서로 닮은 것이 "
                      "아니라, **가림을 빼면 우리 두 팔이 같은 물리를 낸다**는 쪽이다."
                      if order[0] == "sbr_vs_po" else
                      "⚠ 우리 두 팔끼리가 가장 닮은 짝이 아니다 — 그 자체가 살펴야 할 신호다."))


def _ray_count_phrase() -> str:
    """자세당 광선 수 — 얼린 판을 쓰면 그 판이 정하고, 아니면 사다리의 λ/12 칸이 정한다."""
    gref = ((TRI.get("engines") or {}).get("sbr") or {}).get("grid_ref") or {}
    if SBR_GRID_FROZEN and gref.get("n"):
        return (f"자세당 광선 {gref['n']**2:,} 발(얼린 판 한 변 {gref['n']} 칸 — 아래 "
                "**절 «광선 격자를 어디에 매나»**)")
    return f"자세당 광선 {SG12['rays_per_pose']:,} 발"


def _freeze_para() -> list:
    """맵이 어떤 광선 격자로 풀렸는지 한 줄 — 자세한 것은 아래 «광선 격자를 어디에 매나» 절."""
    if SBR_GRID_FROZEN:
        return ["⭐ **이 편의 맵은 얼린 광선 격자로 풀었다** — 판 한 장을 모든 자세가 함께 쓴다. "
                "그것이 무엇이고 이 편의 숫자를 얼마나 옮겼는지는 아래 "
                "**절 «광선 격자를 어디에 매나»** 가 낸다.", ""]
    return ["⏳ **이 편의 맵은 아직 기본값(자세마다 다시 정의하는 격자)으로 푼 판이다** — "
            "얼린 판으로 다시 푸는 계산이 돌고 있고, 끝나면 이 편의 그림과 수치가 함께 갱신된다.",
            ""]


# --------------------------------------------------------------------------- #
#  ⭐ 08_2 의 «광선 격자를 어디에 매나» 절
#     기전은 리포트 5(커널 편)가 이미 다룬다 — 여기서는 **이 편의 숫자가 그것으로 바뀌었다**
#     만 짧게 적고, 전후 비교표(outputs/freeze_before_after.json)를 읽는다.
# --------------------------------------------------------------------------- #
_KERNEL_LINK = ("[리포트 5 «우리 커널 — 무엇이고, 무엇이 아닌가»](05_kernel.ipynb)")


def _grid_anchor_cell():
    """이 편의 맵이 딛고 선 광선 격자와, 그것을 바꿨을 때 이 편의 숫자가 움직인 폭."""
    g1 = (FRZ or {}).get("gate1_bit_identity") or {}
    g2 = (FRZ or {}).get("gate2_frozen_grid_invariant") or {}
    pr, fz = g2.get("prod") or {}, g2.get("frozen") or {}
    #: 계약 게이트가 쓴 **검증판**의 격자와 이 편이 쓴 **생산판**의 격자 — 봉투가 다르다.
    vref = g2.get("grid_ref") or {}
    gref = ((TRI.get("engines") or {}).get("sbr") or {}).get("grid_ref") or {}
    ad = ((FBA or {}).get("additivity") or {}).get("cells", {}).get("matrice4e/az0_el-15")
    row = ((FBA or {}).get("ledgers") or {}).get("report07_three_engines/sbr")
    smy = (FBA or {}).get("summary") or {}
    ogate = (FBA or {}).get("off_switch_gate") or {}

    out = ["## 광선 격자를 어디에 매나", "",
           "> **자를 프레임마다 다시 놓으면, 자가 움직인 것이 표적이 움직인 것으로 기록된다.**", ""]

    # ① 쉬운 말 — 무엇이 문제인가
    out += ["우리 커널은 표적 앞에 **평면 자**를 세우고 그 격자점마다 광선을 쏜다. 자를 정하는 "
            "것은 중심 ctr · 반경 Rout · 한 변의 칸수 n 셋이다. 그 셋을 **자세마다 표적 "
            "경계상자에서 다시 뽑으면** 프로펠러가 돌 때마다 상자가 숨을 쉬므로 자도 같이 "
            "움직인다. 마이크로도플러는 **프레임 사이 위상차**로 재는 양이라, 그 움직임이 "
            "표적의 운동으로 기록된다.", ""]
    if pr and fz:
        out += [f"실측은 **검증판**에서 났다(계약 게이트 `outputs/verify_frozen_grid.json` · 로터 "
                f"한 바퀴를 {vref.get('n_mesh', 0)} 등분한 봉투 · 같은 기체·자세 · 자세 "
                f"{g2.get('n_pose', 0)} 개 · λ/12): 자세마다 다시 뽑는 "
                f"자는 한 변이 {pr['n_min']}~{pr['n_max']} 칸을 오가며 {pr['n_changes']} 번 튀고, "
                f"위상 원점이 시선 방향으로 {pr['ctr_dot_u_ptp_mm']:.1f} mm · 반경이 "
                f"{pr['Rout_ptp_mm']:.0f} mm 돌아다닌다. 얼린 판은 한 변 {fz['n']} 칸으로 "
                f"**{fz['n_changes']} 번** 바뀐다.", ""]
    if gref:
        out += [f"⭐ **이 편이 쓴 판은 생산판이다** — 로터 한 바퀴를 {gref.get('n_mesh', 0)} 등분해 그 "
                f"메쉬들의 합집합 경계상자로 한 번 만든 판이다: 한 변 {gref['n']} 칸 · 간격 "
                f"{gref['spacing']*1e3:.3f} mm · 반경 {gref['Rout']*1e2:.1f} cm. "
                f"{TM['n']:,} 자세가 전부 이 한 장을 쓴다"
                f"(`outputs/report07_three_engines.json:engines.sbr.grid_ref`).", ""]
    if gref and vref:
        _same = (vref["n"] == gref["n"]
                 and abs(vref["spacing"] - gref["spacing"]) < 1e-9)
        out += [f"⚠ **두 판은 봉투가 다르다** — 검증판은 한 바퀴 {vref.get('n_mesh', 0)} 등분, "
                f"생산판은 {gref.get('n_mesh', 0)} 등분이다. "
                + (f"한 변 칸수 {gref['n']} 과 간격 {gref['spacing']*1e3:.3f} mm 는 두 판이 "
                   f"같고 반경만 {abs(vref['Rout'] - gref['Rout'])*1e3:.2f} mm 차이라, 위 실측의 "
                   "결론이 이 판에도 그대로 선다."
                   if _same else
                   f"검증판은 한 변 {vref['n']} 칸 · 간격 {vref['spacing']*1e3:.3f} mm, "
                   f"생산판은 한 변 {gref['n']} 칸 · 간격 {gref['spacing']*1e3:.3f} mm 다 — "
                   "판이 갈렸으므로 위 실측을 이 판의 값으로 인용하지 마라."), ""]

    # ② 결정적 검사 — 가산성
    out += ["**결정적 검사는 가산성이다.** 서로 가리지 않는 로터의 PO 면적분은 "
            "E(φ₁..φ₄) = E₀ + Σ ΔE_j(φ_j) 로 정확히 쪼개진다 — 로터를 하나씩 돌린 변화량의 합이 "
            "넷을 함께 돌린 장과 같아야 한다. 이 잣대에는 창도 평활도 분모도 안 들어간다.", ""]
    if ad:
        out += ["| 격자 | 가산성 잔차 (중앙값) | 읽는 법 |", "|---|---|---|",
                f"| 얼린 판 한 장 | {ad['frozen']['additivity_residual_median']:.1e} | "
                "기계정밀도 — 정리가 그대로 성립한다 |",
                f"| 자세마다 다시 정의 | {ad['moving']['additivity_residual_median']:.3f} | "
                "O(1) — 물리적으로 결합할 수 없는 로터 사이에 결합이 생긴다 |", "",
                f"그 가짜 결합이 그대로 변조로 실린다 — 이 자세에서 "
                f"{ad['spurious_modulation_db']:+.1f} dB 다"
                f"(변조 RMS {ad['moving']['modulation_rms']:.2e} ↔ 얼린 판 "
                f"{ad['frozen']['modulation_rms']:.2e}). "
                f"기전과 다른 기체·자세의 같은 검사는 {_KERNEL_LINK} 가 낸다 — 여기서는 "
                "**이 편의 자세**에서 그것이 성립한다는 것만 확인한다.", ""]

    # ③ 이 편의 숫자가 얼마나 옮겼나
    out += ["### 이 편의 숫자가 얼마나 옮겼나", "",
            "옛 판(자세마다 다시 정의)과 새 판(얼림)을 **같은 잣대**로 나란히 잰 원장이 "
            "`outputs/freeze_before_after.json` 이다. 옛 열은 `outputs/prefreeze/` 에 사본으로 "
            "남아 있다 — 지우지 않았다.", ""]
    if row:
        out += ["| 잣대 | 옛 판 | 얼린 판 | 차 |", "|---|---|---|---|",
                f"| 평균 레벨 20·log₁₀(mean&#124;E&#124;) | {row['level_db_before']:.2f} dB | "
                f"{row['level_db_after']:.2f} dB | {row['level_db_delta']:+.2f} dB |",
                f"| 변조 깊이 std&#124;E&#124;/mean&#124;E&#124; | {row['mod_depth_before']:.3f} | "
                f"{row['mod_depth_after']:.3f} | ×{row['mod_depth_ratio']:.2f} |",
                f"| 변조 깊이 p-p | {row['ptp_db_before']:.1f} dB | {row['ptp_db_after']:.1f} dB | "
                f"{row['ptp_db_after'] - row['ptp_db_before']:+.1f} dB |",
                f"| 대역밖 절대 전력 P_out (&#124;f&#124; > f_tip) | {row['P_out_db_before']:.1f} dB | "
                f"{row['P_out_db_after']:.1f} dB | **{row['P_out_db_delta']:+.1f} dB** |", "",
                f"⭐ **레벨은 {abs(row['level_db_delta']):.1f} dB 움직이는 데 그쳤는데 날개끝 밖 "
                f"바닥은 {abs(row['P_out_db_delta']):.1f} dB 내려간다.** 얼리기는 신호를 키우거나 "
                "줄이는 조작이 아니라 **슬로타임 변조를 바로잡는** 조작이다. 내려간 만큼이 "
                "표적의 운동이 아니라 자의 흔들림이었다.", "",
                f"⚠ **같은 신호의 미세 수정이 아니다.** 옛 열과 새 열의 진폭 상관이 "
                f"{row['amp_corr']:.3f}(복소 코히런스 {row['complex_coherence']:.3f})다 — "
                "**다른 시계열**이다. 그래서 옛 판으로 그린 그림과 새 판의 숫자를 섞어 실으면 "
                "안 된다.", ""]
    if smy:
        lv, ac, md_, po = (smy.get("level_db_delta") or {}), (smy.get("amp_corr") or {}), \
            (smy.get("mod_depth_ratio") or {}), (smy.get("outofband_P_out_db_delta") or {})
        _lk = list(((FBA or {}).get("ledgers") or {}).keys())
        _n_tri = sum(1 for k in _lk if k.startswith("report07_three_engines/"))
        _n_15b = sum(1 for k in _lk if k.startswith("report15b/"))
        _n_hov = sum(1 for k in _lk if k.startswith("report07_hover_long/"))
        out += [f"같은 잣대를 이 라운드에서 다시 낸 **{smy.get('n_series', 0)} 열 전부**에 "
                f"먹이면({_n_tri} + {_n_15b} + {_n_hov} = 세 엔진 원장의 **sbr 열 하나** · "
                f"report15b 여섯 자세 × 네 SBR 팔 · 호버 두 프리셋 — 얼리기가 닿는 것은 "
                "광선 격자를 쓰는 SBR 계열뿐이다): 레벨 차 중앙값 "
                f"{lv.get('median', 0):+.2f} dB({lv.get('min', 0):+.2f} ~ {lv.get('max', 0):+.2f}) · "
                f"진폭 상관 중앙값 {ac.get('median', 0):.3f} · 변조 깊이 후/전 비 중앙값 "
                f"×{md_.get('median', 0):.2f} · 대역밖 절대 전력 "
                f"**{po.get('n_decreased', 0)}/{smy.get('n_series', 0)} 열에서 감소**"
                f"(중앙값 {po.get('median', 0):+.1f} dB · 최대 {po.get('min', 0):+.1f} dB).", "",
                "⚠ 변조 깊이는 **항상 얕아지지 않는다** — 후/전 비의 범위가 "
                f"×{md_.get('min', 0):.2f} ~ ×{md_.get('max', 0):.2f} 다. 격자 흔들림이 실제 "
                "변조를 **가리고 있던** 열도 있다는 뜻이라, «얼리면 변조가 준다» 고 쓰면 틀린다. "
                "한 방향으로 움직인 것은 대역밖 전력뿐이다.", ""]

    # ④ 교차 확인 — 판을 어디에 잡든 같은가 / 스위치를 끄면 옛 원장인가
    out += ["### 이 판을 믿을 근거 두 가지", ""]
    if row and (pc := row.get("plate_choice_check")):
        out += [f"**① 판의 위치에 둔하다.** 같은 «얼림» 을 다른 봉투로 잡은 판"
                f"(`{pc['vs'].split('::')[-1]}` — 자세 {TM['n']:,} 개 전부의 합집합)과 견주면 진폭 "
                f"상관 {pc['amp_corr']:.3f} · 레벨 차 {pc['level_db_delta']:+.3f} dB 다. "
                f"얼림↔안얼림이 {row['amp_corr']:.3f} 인 것과 나란히 놓으면, 차이를 만든 것은 "
                "판의 **위치**가 아니라 판이 **움직였다는 사실**이다.", ""]
    if ogate.get("rows"):
        n_ok = sum(1 for v in ogate["rows"].values() if v.get("bit_identical"))
        out += [f"**② 스위치를 끄면 옛 원장이 그대로 선다.** 재계산기에서 얼리기를 끄고"
                f"(`SIONNA2_FREEZE_GRID=0`) 자세 {ogate.get('n_poses_checked', 0)} 개를 다시 풀면 "
                f"{n_ok}/{len(ogate['rows'])} 열이 옛 원장과 **비트 동일**하다. 자세 격자·PRF·"
                "로터 회전수를 하나도 안 건드렸다는 증거이고, 그래서 위 표의 «전 ↔ 후» 가 "
                "격자 하나만의 차이가 된다. 커널 자체의 기본값(`grid_ref=None`)도 배선 전과 "
                f"{g1.get('n_bit_identical', 0)}/{g1.get('n_cases', 0)} 비트 동일이다.", ""]
    _sio_pr = [r["cos_prod_vs_sionna"] for r in SGL if r.get("cos_prod_vs_sionna") is not None]
    _sio_fz = [r["cos_froz_vs_sionna"] for r in SGL if r.get("cos_froz_vs_sionna") is not None]
    out += [f"⭐ **격자 사다리의 예측과도 맞는다 — 잣대는 우리 두 팔끼리다"
            f"({ARM_SBR} ↔ {CTRL}).** 사다리는 얼리면 그 코사인이 "
            f"{SGF['cos_prod_vs_po']:.3f} → {SGF['cos_froz_vs_po']:.3f} 로 오른다고 예측했고"
            f"(`outputs/sbr_grid_convergence.json:in_band_fidelity` · λ/{SGF['div']} 칸), 이 편의 "
            f"생산 원장을 얼린 판으로 다시 풀어 재면 **{cos3('sbr_vs_po')}** 다 — 독립 구현의 "
            "예측을 생산 경로가 재현했다.", ""]
    if _sio_pr and _sio_fz:
        out += [f"⚠ **PathSolver 를 잣대로 두면 방향이 반대다.** 같은 사다리에서 SBR↔"
                f"{ARM_SIONNA} 코사인은 λ/{SGF['div']} 칸에서 "
                f"{SGF['cos_prod_vs_sionna']:.3f} → {SGF['cos_froz_vs_sionna']:.3f} 로, 사다리 "
                f"{len(_sio_fz)} 칸 전부에서 {min(_sio_pr):.3f}~{max(_sio_pr):.3f} → "
                f"{min(_sio_fz):.3f}~{max(_sio_fz):.3f} 로 **내려간다**. 얼리기는 우리 두 팔을 "
                "서로 닮게 하고 스톡 팔과는 덜 닮게 한다. 판정을 우리 두 팔끼리로 세우는 이유는 "
                "둘이 같은 물리(가림만 다른 면적분)를 풀기 때문이고, 스톡 팔은 재료가 다르다 — "
                f"순수 PO 는 점구름 적분이라 광선 격자 밖에 있고, PathSolver 는 경로가 성기다"
                + (f"(자세당 중앙값 {TRR['R3']['paths_median']:.0f} 가닥)." if TRR else ".")
                + " 그러므로 이 절의 심판은 **우리 두 팔끼리**다.", ""]

    # ⑤ 대가
    out += ["### 대가", "",
            "| 대가 | 크기 | 무엇을 뜻하나 |", "|---|---|---|"]
    if g2:
        out += [f"| 광선 수 | ×{g2.get('extra_ray_cost', 1):.3f} "
                f"(+{100*(g2.get('extra_ray_cost', 1)-1):.1f} %) | 전 자세를 덮는 판이라 자세별 "
                "최소 판의 평균보다 크다 — 계산이 그만큼 비싸진다 |"]
    if FRZ and (fl := FRZ.get("field_level")):
        out += [f"| 디더 평균 | 얼린 장과 생산 장의 레벨 차 "
                f"{fl['froz_vs_prod_level_db_ptp']:.2f} dB p-p | 자세마다 굴리던 무작위 오프셋은 "
                "사실상 몬테카를로 평균이었다. 얼리면 그 평균이 사라지고 **오프셋 한 판**에 절대 "
                "레벨이 걸린다 — 그래서 얼린 복소장은 **모양**에만 쓰고, 절대 σ 는 정적 경로에서 "
                "가져온다 |"]
    if FRZ and (g3 := FRZ.get("gate3_coverage")):
        out += [f"| 판을 미리 잡는 일 | 덮개 여유 최소 {g3['margin_min_mm']:.0f} mm | 자세열을 "
                "먼저 훑어야 판이 나온다 — 스트리밍으로는 못 잡는다. 판이 자세를 못 덮으면 커널이 "
                "예외를 던진다 |"]
    out += ["", f"기전·수렴·적대 검증의 정본은 {_KERNEL_LINK} 다. 이 절은 그것을 되풀이하지 않고 "
            "**이 편의 숫자가 그 판으로 바뀌었다**는 것만 적는다.", ""]

    # ⑥ 선언
    out += ["### 이 편의 모든 맵은 얼린 격자로 계산됐다", ""] if SBR_GRID_FROZEN else []
    if SBR_GRID_FROZEN:
        out += [f"⭐ 이 편(8-2)의 **SBR 팔 맵과 그 파생 수치는 전부 위의 얼린 판으로 계산됐다** — "
                f"세 엔진 원장 `report07_three_engines.npz` 의 sbr 열 {TM['n']:,} 자세를 다시 "
                "풀었고, 그 열을 읽는 그림(f12 · f8)과 표(깊이 · 대역밖 · 코사인)가 모두 그 "
                "열에서 나온다. 8-3 의 맵(f1 · f4 · f7 · f11)도 같은 라운드에서 같은 방식으로 "
                "다시 났다.", "",
                "⚠ **같이 안 바뀐 것을 밝힌다.** ① 세 엔진 원장의 **Sionna 열과 대조군(순수 PO) "
                "열은 다시 안 돌렸다** — 순수 PO 는 점구름 적분이라 광선 격자를 아예 안 쓰고, "
                "Sionna 열은 몬테카를로라 다시 돌리는 것이 곧 다른 추첨이다. 두 열은 비트 그대로 "
                "옮겼다. ② **8-5(바이스태틱)의 원장**과 PO 대조 원장은 아직 옛 판이다 — 그 편의 "
                "해당 절에 그렇게 적혀 있다.", ""]
    return md(*out)


def _flash_census_para() -> list:
    """«프롭 정반사 0 칸» — 무엇을 센 격자이고, 예산·앙각 두 축의 시험이 무엇을 냈나."""
    out = ["⭐ **Sionna 가 왜 얼룩인가** — 프로펠러를 맞은 **정반사 경로가 이 격자에서 0 칸**이다. "
           f"자세×위상 격자 {CEN['n_cells']} 칸(기체 두 대 몫)에서 정반사가 잡힌 칸이 "
           f"{CEN['n_with_specular']} 칸인데, 그중 **프롭 정반사는 "
           f"{CEN['n_with_prop_specular']} 칸**이다. 남은 것은 확산 산란뿐이라 아치가 뭉개진다.", ""]
    if not BFL:
        return out + [f"⚠ 이 «0» 의 예산·앙각 시험 원장이 아직 없다 — {PENDING}.", ""]
    m = BFL["_meta"]
    lo, hi = str(m["spp_ladder"][0]), str(m["spp_ladder"][-1])
    b0 = BFL["budget_axis"]["matrice4e"][lo]
    tm_, tn = BFL["budget_axis"]["matrice4e"][hi], BFL["budget_axis"]["mini2"][hi]
    dm, dn = BFL["elevation_axis"]["matrice4e"]["deep"], BFL["elevation_axis"]["mini2"]["deep"]
    vm, vn = BFL["verdict"]["matrice4e"], BFL["verdict"]["mini2"]
    out += [f"⚠ **그 격자가 무엇인지 밝힌다** — 방위 {m['n_az']} × 앙각 {len(m['el_base'])}"
            f"({min(m['el_base']):.0f}~{max(m['el_base']):.0f}°) × 로터 위상 {m['n_phase']} = "
            f"기체당 {b0['n_cells']} 칸, 광선 {m['spp_ladder'][0]/1e8:.2f} 억 발이다. "
            f"⚠ **이 편의 자세(앙각 {TM['el_deg']:.0f}°)는 그 격자에 들어 있지 않다** — "
            "프롭 원판의 법선은 위를 향하고, 인구조사는 그 위쪽만 훑었다.", "",
            "⭐ **그 «0» 을 축 두 개로 시험했다**(원장 `outputs/report15_blade_flash_ladder.json`) "
            "— 한 번에 둘을 바꾸면 원인을 못 가르므로 한 축씩 열었다.", "",
            "| 축 | 무엇을 바꿨나 | matrice4e | mini2 |", "|---|---|---|---|",
            f"| 예산 | 광선 {m['spp_ladder'][0]/1e8:.2f} 억 → {m['spp_ladder'][-1]/1e8:.2f} 억"
            f"({m['spp_ladder'][-1]/m['spp_ladder'][0]:.0f} 배) | 프롭 정반사 "
            f"{tm_['n_cells_with_prop_specular']} / {tm_['n_cells']} 칸 | "
            f"{tn['n_cells_with_prop_specular']} / {tn['n_cells']} 칸 |",
            f"| 앙각 | 격자를 {max(m['el_base']):.0f}° → {max(m['el_deep']):.0f}° 까지 열기"
            f"(같은 예산) | {dm['n_cells_with_prop_specular']} / {dm['n_cells']} 칸 | "
            f"{dn['n_cells_with_prop_specular']} / {dn['n_cells']} 칸 |", "",
            "⇒ **기체마다 답이 갈린다.** "
            f"**matrice4e** — {vm['verdict_ko'].lstrip('⭐ ')} "
            f"**mini2** — {vn['verdict_ko'].lstrip('⭐ ')}", "",
            f"⇒ 이 편의 자세는 프롭 원판의 법선에서 {90 - abs(TM['el_deg']):.0f}° 떨어져 있다. "
            "그러므로 여기서 아치가 얼룩인 것은 «이 기하에서 프롭 정반사가 없다» 와 앞뒤가 "
            "맞는다 — **모든 기하에서 없다** 는 뜻이 아니다.", ""]
    return out


def _census_scope_para() -> list:
    """맺음말이 «0 칸» 을 쓸 때 함께 서야 하는 두 단서 — 격자의 앙각 범위와 기체별 갈림."""
    if not BFL:
        return [f"⚠ 그 «0 칸» 의 앙각 시험 원장이 아직 없다 — {PENDING}.", ""]
    m = BFL["_meta"]
    hi = str(m["spp_ladder"][-1])
    dm, dn = BFL["elevation_axis"]["matrice4e"]["deep"], BFL["elevation_axis"]["mini2"]["deep"]
    bn = BFL["budget_axis"]["mini2"][hi]
    return [f"⚠ **그 «0 칸» 이 어디까지의 0 인지 밝힌다.** 인구조사 격자는 앙각 "
            f"{min(m['el_base']):.0f}~{max(m['el_base']):.0f}° 이고 **이 편의 자세"
            f"(앙각 {TM['el_deg']:.0f}°)는 그 밖이다**. 축을 하나씩 열면 답이 기체마다 갈린다 — "
            f"앙각을 {max(m['el_deep']):.0f}° 까지 연 판에서 matrice4e 는 프롭 정반사가 "
            f"{dm['n_cells_with_prop_specular']}/{dm['n_cells']} 칸으로 나오고, mini2 는 같은 판에서 "
            f"{dn['n_cells_with_prop_specular']}/{dn['n_cells']} 칸 · 예산 사다리 꼭대기"
            f"({m['spp_ladder'][-1]/1e8:.0f} 억 발)에서도 {bn['n_cells_with_prop_specular']}/"
            f"{bn['n_cells']} 칸이다(`outputs/report15_blade_flash_ladder.json` · 두 축은 따로 "
            "열었다). 그러므로 이 맺음말은 **이 기하에서의 0** 이고, 기체별 판정은 절 «블레이드 "
            "플래시를 세 엔진으로 나란히» 가 낸다.", ""]


def _seed_para() -> list:
    """«거리의 성질» 로 읽히던 것이 실은 몬테카를로 추첨 한 번이라는 실측(8 m 이상 조사)."""
    if not PRB:
        return [f"⚠ 시드 의존성 원장(`outputs/probe_8m_anomaly.json`)이 없다 — {PENDING}.", ""]
    runs = PRB["runs_512pose"]
    keys = [k for k in runs if k.startswith(("A_", "B_", "C_"))][:3]
    lvl = [runs[k]["db_of_mean_abs"] for k in keys]
    beat = [runs[k]["beat_over_f_flash"] for k in keys]
    ana = PRB["prior_probe_reanalysis"]
    ck = next(k for k in ana if k.startswith("ctrl_same_spp"))
    ctrl = [ana[ck][r]["beat_over_fflash"] for r in ("R3", "R8", "R15")]
    sl = ana["spp_scaling"]
    s3 = [r["slope_absE"] for r in sl if r["rng"] == 3.0]
    s8 = [r["slope_absE"] for r in sl if r["rng"] == 8.0]
    i3 = [r["slope_incoh"] for r in sl if r["rng"] == 3.0]
    return [
        "⭐ 기하·자세·광선 수를 **하나도 안 바꾸고 시드만** 바꾼 실측"
        f"(8 m · 자세 {PRB['_meta']['n_slowtime']} 개): 레벨이 "
        + " / ".join(f"{v:.1f}" for v in lvl)
        + f" dB 로 **{max(lvl) - min(lvl):.0f} dB** 흔들리고, 최강선이 "
        + " / ".join(f"{v:.3f}" for v in beat)
        + " ·f_flash 로 바뀐다. 즉 «8 m 만 3 배 조화» 도 «레벨이 안 떨어진다» 도 **거리의 성질이 "
          "아니라 이 시드의 성질**이다. 세 거리를 모두 같은 광선 수"
        + f"({ck.rsplit('_', 1)[-1]})로 다시 풀면 최강선이 "
        + " / ".join(f"{v:.3f}" for v in ctrl)
        + " ·f_flash 로 셋 다 기본파에 꽂힌다.", "",
        "⚠ 그리고 이 팔의 절대 레벨은 **광선 수에 수렴하지 않는다**. 우리가 재는 것은 "
        "h = Σ a_p e^(−j2πf_c τ_p) 인데, Sionna 는 확산 경로 진폭을 **전력 합**이 광선 수와 "
        "무관하도록 정규화한다. 그것을 코히어런트로 더하면 광선을 늘릴수록 값이 커진다 — "
        f"√spp 에 대한 실측 기울기가 3 m 에서 {min(s3):+.2f}~{max(s3):+.2f} 다"
        + (f"(같은 잣대로 8 m 는 {min(s8):+.2f}~{max(s8):+.2f} 라, 부풀림의 크기 자체가 "
           "자세·거리에 딸린다). " if s8 else ". ")
        + f"반면 Σ&#124;a_p&#124;² 의 기울기는 {min(i3):+.2f}~{max(i3):+.2f} 로 평평하다. "
          "거리마다 다른 광선 수를 준 이 표는 거리마다 다른 부풀림을 섞고 있다.", ""]

# ── 셀 도구 ─────────────────────────────────────────────────────────────────
_SEEN: dict[str, list[str]] = {}
_CUR = [""]


def embed(stem: str, ext: str = "png") -> str:
    _SEEN.setdefault(_CUR[0], []).append(stem)
    with open(os.path.join(FIG, f"{stem}.{ext}"), "rb") as f:
        b = base64.b64encode(f.read()).decode()
    return f"![{stem}](data:image/{ext};base64,{b})"


def md(*lines):
    return {"cell_type": "markdown", "metadata": {},
            "source": [l + "\n" for l in "\n".join(lines).split("\n")]}


def write(no: str, slug: str, cells: list) -> None:
    nb = {"cells": cells,
          "metadata": {"kernelspec": {"display_name": "py312", "language": "python",
                                      "name": "py312"},
                       "language_info": {"name": "python"}},
          "nbformat": 4, "nbformat_minor": 5}
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, f"{no}_{slug}.ipynb")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)
    mb = os.path.getsize(p) / 1e6
    figs = _SEEN.get(no, [])
    print(f"  ✅ reports/{no}_{slug}.ipynb — 셀 {len(cells):2d} · 그림 {len(figs):2d}장 · "
          f"{mb:5.1f} MB   ({', '.join(figs)})")


NAV = ("> **8 권은 다섯 편이다** — "
       "[08_1 시나리오](08_1_scene.ipynb) · [08_2 세 엔진과 거리](08_2_engines.ipynb) · "
       "[08_3 무늬를 정하는 것](08_3_pattern.ipynb) · [08_4 무엇을 잴 수 있나](08_4_sampling.ipynb) · "
       "[08_5 바이스태틱](08_5_bistatic.ipynb)")

LEDGER_NOTE = ("⭐ 본문 숫자는 계산 결과 JSON(원장)에서 주입된다 — 원장이 다시 계산되면 "
               "`python src/make_report08_microdoppler.py` 한 번으로 본문 숫자가 따라 바뀐다. "
               "원장이 없는 자리는 «원장 없음» 이라고 적고 그 숫자를 비율·헤드라인에서 뺀다.")


# =========================================================================== #
#  08_1 — 무엇을 보고 있나
# =========================================================================== #
def build_08_1():
    _CUR[0] = "08_1"
    # ── 이 편이 쓰는 파생값 — 전부 원장에서 읽는다(손으로 적지 않는다) ─────────
    #  ⭐ 팔 셋: S = Sionna PathSolver · B = 우리 SBR+PO · P = 순수 PO(대조군).
    #    광선 수·조명점 수는 **B 팔** 것이다 — P 는 광선 격자를 안 쓴다.
    m4e = next(r for r in MDP["rows"] if r["drone"] == "matrice4e")
    gref = ((TRI.get("engines") or {}).get("sbr") or {}).get("grid_ref") or {}
    n_side = gref.get("n")
    n_rays = n_side ** 2 if n_side else None
    spacing_mm = gref["spacing"] * 1e3 if gref.get("spacing") else None
    #: 얼린 판의 광선 수 교차 확인(계약 게이트가 같은 수를 따로 적는다).
    n_rays_gate = (((FRZ or {}).get("gate2_frozen_grid_invariant") or {})
                   .get("frozen") or {}).get("n_rays")
    #: ⭐얼린 판의 조명점 수 — 생산 판(n_mesh=24)을 재는 원장이 없어, **같은 칸수·같은
    #    간격**의 얼린 판을 잰 적대적 감사 원장에서 읽고 출처를 본문에 밝힌다.
    adv = _opt(f"{_ROOT}/outputs/adv_grid_freeze_audit.json")
    _arow = next((r for r in ((adv or {}).get("audit_2_signal_loss") or {}).get("rows", [])
                  if r.get("div") == 12 and r.get("n0_frozen") == n_side), None)
    n_lit = _arow["n_lit_froz_mean"] if _arow else None
    n_lit_rsd = _arow["n_lit_froz_relstd"] * 100.0 if _arow else None
    n_lit_x = ((((adv or {}).get("audit_5_recompute") or {}).get("arms") or {})
               .get("froz") or {}).get("n_lit_mean")
    #: S 팔의 표적 경유 경로 중앙값 — 비율의 분모는 이것 하나만 쓴다(직행 경로를 뺀다).
    p_med = TRR["R3"]["paths_median"] if TRR else None
    ratio = (n_lit / p_med) if (n_lit and p_med) else None
    #: 같은 3 m · 같은 광선 예산에서 시드만 바꾼 판 — 경로 수의 흔들림 폭.
    _runs = (PRB or {}).get("runs_512pose") or {}
    seed_meds = [_runs.get(k, {}).get("paths_median")
                 for k in ("E_R3_spp1.0M_seed2", "F_R3_spp1.0M_seedper")]
    seed_line = (
        f" — 원장 판(3 m · 광선 {TRR['R3']['spp']/1e6:.1f}M · 시드 1 · "
        f"자세 {TRR_J['_meta']['n']:,})의 "
        f"자세당 중앙값은 {p_med:.0f} 가닥이고, 같은 거리·같은 광선 예산에서 시드를 바꾼 "
        f"두 판(자세 {PRB['_meta']['n_slowtime']})은 고정 시드 2 에서 "
        f"{seed_meds[0]:.0f} 가닥 · 자세마다 다른 시드에서 {seed_meds[1]:.0f} 가닥이다"
        "([08_2](08_2_engines.ipynb))"
        if (TRR and PRB and p_med and all(v is not None for v in seed_meds)) else
        " — 시드 사다리는 **원장 없음**")

    c = [
        md("# 리포트 8-1 — 마이크로도플러: 무엇을 보고 있나", "", NAV, "",
           "> **호버링하는 드론은 제자리에 있지만 프로펠러는 돈다.** "
           "그 회전만이 되돌아오는 신호를 흔든다 — 이 편은 그 장면을 먼저 세운다.", "",
           "이 편은 **시나리오와 측정 모형**만 다룬다. 계산 엔진의 비교는 8-2, 무늬를 정하는 "
           "요인들은 8-3, 표본화 한계는 8-4 다.", "", LEDGER_NOTE),

        md("## 표적이 실제로 무엇을 하고 있나", "",
           "" if not _HAS_ANIM else embed("report07_anim", "gif"), "",
           "" if not _HAS_ANIM else
           f"호버링하는 {ANIM['_meta'].get('name', 'DJI Matrice 4E')}. **아래칸이 배치**다 — "
           f"붉은 공 하나가 레이더이고, 거기서 {ANIM['_meta']['range_m']:.0f} m 떨어진 곳에 "
           "드론이 떠 있다"
           f"(방위 {ANIM['_meta']['az_deg']:.0f}° · 앙각 {ANIM['_meta']['el_deg']:.0f}°, "
           "즉 레이더가 드론을 올려다본다). 공이 하나인 이유는 기선이 0 인 **진짜 모노스태틱**이라 "
           "송신기와 수신기가 같은 점에 있기 때문이다. **위칸**은 그 레이더 시선에서 표적을 "
           "당겨 본 모습이다.", "",
           "" if not _HAS_ANIM else
           "⭐볼 것은 하나다 — **동체는 한 픽셀도 안 움직이는데 프로펠러 넷의 날 방향만 "
           f"프레임마다 바뀐다**(호버 {ANIM['rotors']['rpm_mean']:.0f} rpm, 로터마다 조금씩 "
           "다르고 CW/CCW 가 섞여 있다). 그 바뀌는 부분이 되돌아오는 신호의 위상을 흔들고, "
           "그것이 이 편들이 다루는 마이크로도플러다.", "",
           "" if not _HAS_ANIM else
           f"⚠ 실제 날은 초당 {ANIM['rotors']['rpm_mean']/60:.0f} 바퀴를 돌아 눈으로는 볼 수 없다 — "
           f"이 애니메이션은 프레임 사이 실시간 "
           f"{ANIM['loop']['loop_real_ms']/int(ANIM['loop']['n_frames']):.2f} ms 를 "
           f"{int(ANIM['loop']['frame_delay_ms'])} ms 로 늘여 튼 "
           f"**약 {ANIM['loop']['slowmotion_factor']:.0f} 배 슬로모션**이다"
           f"(프레임당 {ANIM['loop']['blade_deg_per_frame']:.0f}° 회전, "
           f"{ANIM['loop']['n_frames']} 프레임 = 블레이드 {ANIM['loop']['n_periods']} 주기). "
           f"⚠ 로터 간 누적 어긋남이 {ANIM['loop']['seam_mismatch_deg']:.1f}° 뿐이라 "
           "**산포는 여기 안 보인다** — 그 성질은 8-3 이 담당한다."),

        md("## 배치 — 무엇이 어디에 있나", "",
           embed("report07_f0"), "",
           "**공통**: DJI Matrice 4E 한 대가 **제자리 호버링**한다(이동 0, 벌크 도플러 0). "
           "환경은 자유공간이다 — 지면도 벽도 클러터도 잡음도 두지 않았다. "
           "레이더는 기체의 **배 쪽 아래**에서 본다(방위 0°, 앙각 −15°). "
           "지상 레이더가 나는 드론을 보는 각도다.", "",
           "| | |", "|---|---|",
           f"| 기체 | {LEAD['name']} |",
           f"| 자세 | 방위 {LEAD['az_deg']:.0f}° · 앙각 {LEAD['el_deg']:.0f}° (배 쪽) |",
           f"| 반송파 | {TM['fc_hz']/1e9:.2f} GHz (5G n78 대역의 반송파만 빌렸다) |",
           f"| 호버 회전수 | {PH['rpm']:.0f} rpm |",
           f"| 날개끝 도플러 | {PH['f_tip']:.0f} Hz "
           f"(앙각 {LEAD['el_deg']:.0f}° 사영 · 브로드사이드는 {m4e['f_tip_hz']:.0f} Hz) |",
           f"| 블레이드 통과율 | {PH['f_flash']:.1f} Hz (= 플래시 {1000/PH['f_flash']:.1f} ms 마다) |",
           f"| 원거리장 경계 | 2D²/λ = {FARFIELD_M:.1f} m "
           f"(D = 수평 최대치수 {FF_D_H_M:.2f} m) |",
           "",
           "⚠ **이 경계는 D 를 무엇으로 잡느냐에 매인다.** 여기 D 는 메쉬의 **수평 최대치수**"
           f"({FF_D_H_M:.2f} m)다. 같은 기체를 **3D 대각**({FF_D_3D_M:.2f} m)으로 다시 잡으면 "
           f"경계가 {FARFIELD_3D_M:.1f} m 로 밀린다. 실측 계획은 그보다 더 보수적인 정의"
           "(회전 로터 디스크까지 감싸는 외접상자)를 채택하고 세 정의를 나란히 적는다 — "
           "[리포트 15 절 1 «가장 보수적인 D 정의로도 세션 거리 하나가…»](15_measurement.ipynb). "
           "**정의를 밝히지 않은 «원거리장 경계» 는 이 문서 어디서도 비교하지 않는다.**",
           "",
           "⭐ **측정 모형 — 파형이 아니다.** 이 편들의 신호 h(t) 는 슬로타임 격자 위의 "
           f"**복소 코히어런트 합**이고, 반송파는 **{TM['fc_hz']/1e9:.2f} GHz 단일 톤(CW)** "
           "하나다. 5G 파형을 변조해 쏜 것이 아니라 반송파 주파수만 n78 에서 빌렸다. "
           "PRF 는 «채널을 얼마나 자주 재느냐»(슬로타임 표본율)이지 펄스 반복률이 아니다. "
           "실제 5G 파형을 태우면 어떻게 되는지는 **8-4** 가 잰다.", "",

           "⭐ **그 합을 이루는 항은 팔마다 다르다.** 8 권은 계산 팔 셋을 쓰고, 이 편의 "
           "숫자에도 팔 이름을 붙인다.", "",
           "| 팔 | h(t) 의 한 항 | 가림 | 광선 격자 |", "|---|---|---|---|",
           f"| **S — Sionna PathSolver** | 경로 p 마다 a_p·exp(−j2πf_c·τ_p) | 경로해가 푼다 | "
           "씬 광선(경로해) |",
           "| **B — 우리 SBR + PO** | 광선이 맞힌 표면 점마다 물리광학 항 | 광선 격자가 푼다 | "
           + (f"λ/12 = {spacing_mm:.1f} mm · 얼린 판 |" if spacing_mm else "λ/12 · 얼린 판 |"),
           "| **P — 순수 PO (대조군)** | 점구름 전면의 물리광학 항 | 열어 둔다 | "
           "쓰지 않는다(점구름 면적분) |",
           "",
           "세 팔의 자기서술은 `report07_three_engines.json:engines.*.engine` 이 낸다. "
           "**세 팔이 공유하는 것은 슬로타임 격자와 반송파 하나**이고, 팔을 가르는 것은 "
           "위 표의 오른쪽 두 칸이다. 세 팔이 같은 장면에서 얼마나 갈리는지는 **8-2** 가 잰다.",
           "",
           "⚠ **없는 것을 적어 둔다** — 잡음 0 · 클러터 0 · 지면 0 · 다중경로 0. "
           "즉 이 편들의 수치는 **상한**이고, 현실 성능이 아니다."),

        md("## 경로 렌더 — Sionna 가 실제로 찾은 것", "",
           embed("report07_f0c"), "",
           "**S 팔(PathSolver)이 이 자세에서 찾은 경로 전부**가 씬 위에 겹쳐 그려져 있다 — "
           "TX→RX 직행 한 가닥과 표적 경유 몇 가닥이다. 8-2 의 맵에서 Sionna 무늬가 성긴 이유가 "
           "이 그림에 있다 — 경로 몇 가닥이 그 엔진의 재료 전부다.", "",
           "⚠ **그림 속 경로 수는 «원장 없음» 이다.** 렌더 실행"
           "(`benchmark/render_md_scene.py` · 자세 1 · 시드 1 · 광선 100 만 발)이 표적 경유 "
           "9 가닥을 stdout 으로 적었고, 그 수를 담은 원장 파일이 없다. 아래 비율은 이 수를 "
           "빼고 **원장의 자세당 중앙값**으로 잰다.", "",
           "⚠ **경로 수는 «추첨 한 장» 이다.** PathSolver 는 확산 경로를 몬테카를로로 "
           "찾으므로 경로 수가 시드와 광선 예산에 딸려 흔들린다" + seed_line + ".", "",
           "⭐ 여기서 «경로» 는 광선이 표적을 맞고 돌아온 **한 가닥**이다. **B 팔**(우리 SBR + PO)"
           + (f"은 같은 표적에 λ/12(= {spacing_mm:.1f} mm) 격자로 자세마다 광선 "
              f"**{n_rays:,} 발**(얼린 판 한 변 {n_side} 칸)을 쏘고, 그중 표면을 맞은 점을 "
              "면적분한다" if n_rays else "은 λ/12 격자로 표면을 면적분한다")
           + (f" — 조명점은 **자세 평균 {n_lit:.0f} 점**(자세마다 ±{n_lit_rsd:.1f} %)이다. "
              f"표적 경유 경로 중앙값 {p_med:.0f} 가닥과 같은 잣대로 견주면 적분점이 "
              f"**{ratio:.0f} 배**다." if ratio else " — 조명점 수는 **원장 없음**이다.")
           + " **P 팔**(순수 PO 대조군)은 이 광선 격자를 쓰지 않는다 — 점구름을 통째로 "
           "면적분한다. 세 팔의 차이가 무엇을 만드는지가 8-2 의 주제다.", "",
           "⚠ **조명점 수의 출처를 밝힌다.** 생산 판(`n_mesh=24`)의 조명점 수를 담은 원장이 "
           "없다. 위 수는 격자 사다리의 얼린 판을 잰 값이고"
           "(`adv_grid_freeze_audit.json:audit_2_signal_loss.rows[div=12].n_lit_froz_mean`), "
           f"그 판은 생산 판과 **한 변 {n_side} 칸 · 간격 λ/12** 가 같고 판을 앉힌 중심·반경만 "
           "다르다. 같은 파일의 다른 자리가"
           + (f" {n_lit_x:.0f} 점" if n_lit_x else "")
           + "으로 교차 확인한다(`audit_5_recompute.arms.froz.n_lit_mean`). "
           + (f"광선 수 {n_rays_gate:,} 발은 계약 게이트가 따로 적은 값과 같다"
              "(`verify_frozen_grid.json:gate2_frozen_grid_invariant.frozen.n_rays`)."
              if n_rays_gate else "")),

        md("## 이 편이 서 있는 자리", "",
           "| 다음 | 무엇을 답하나 |", "|---|---|",
           "| [08_2 세 엔진과 거리](08_2_engines.ipynb) | 같은 장면을 세 가지로 계산하면 무엇이 갈리나 |",
           "| [08_3 무늬를 정하는 것](08_3_pattern.ipynb) | 회전수·가림·산포가 무늬를 어떻게 바꾸나 |",
           "| [08_4 무엇을 잴 수 있나](08_4_sampling.ipynb) | 광선 비용과 조명원 반복률의 한계 |",
           "",
           "⚠ 이 편은 **모노스태틱**이다. 바이스태틱 기하로 가면 무엇이 달라지는지는 "
           "[08_5 바이스태틱](08_5_bistatic.ipynb) 이 다룬다 — 단 그 편도 **기하만** 다룬다.", "",
           "⚠ **8 권은 채널 하나만 본다.** 여기의 h(t) 는 표적 에코 한 갈래이고, 패시브가 실제로 "
           "쓰는 **기준·감시 두 채널**(ECA·CAF)은 이 권에 없다. 기준채널이 이상적이지 않을 때 "
           "무엇을 잃는지는 [리포트 11-2 «기준채널이 현실이면 얼마를 잃는가»](11_2_two_channel.ipynb) "
           "가 단일축으로 잰다."),

        md("## 출처", "",
           "이 편의 숫자가 온 자리다 — 파일은 전부 `outputs/` 아래에 있고, «팔» 칸은 그 값을 "
           "낸 계산 팔이다(**S** = Sionna PathSolver · **B** = 우리 SBR + PO · "
           "**P** = 순수 PO 대조군 · **해** = 닫힌 식·규약).", "",
           "| 어디 | 원장 : 키 | 팔 |", "|---|---|---|",
           "| 애니메이션(셀 1) | `report07_anim.json` : `_meta.{name,range_m,az_deg,el_deg}` · "
           "`rotors.rpm_mean` · `loop.*` | 렌더 |",
           "| 배치표 기체·자세·운동학 | `report15b_microdoppler.json` : "
           "`cells['matrice4e/belly'].{name,az_deg,el_deg,physics.*}` | 해 |",
           "| 반송파 · 세 팔의 자기서술 · 얼린 판 | `report07_three_engines.json` : "
           "`_meta.fc_hz` · `engines.*.engine` · `engines.sbr.grid_ref.{n,spacing}` | S·B·P |",
           "| 원거리장 경계 · 브로드사이드 날개끝 도플러 | `report00_microdoppler.json` : "
           "`rows[matrice4e].{farfield_m,f_tip_hz}` | 해 |",
           "| D 정의 셋 | `report15_probe.json` : `airframes.matrice4e.physics."
           "{D_horizontal_m,D_diag3d_m,farfield_diag3d_m}` | 해 |",
           "| 표적 경유 경로 중앙값 | `report07_three_engine_ranges.json` : "
           "`ranges.R3.{spp,paths_median}` | S |",
           "| 얼린 판 조명점 수 | `adv_grid_freeze_audit.json` : "
           "`audit_2_signal_loss.rows[div=12].{n0_frozen,n_lit_froz_mean,n_lit_froz_relstd}` · "
           "`audit_5_recompute.arms.froz.n_lit_mean` | B |",
           "| 자세당 광선 수 교차 확인 | `verify_frozen_grid.json` : "
           "`gate2_frozen_grid_invariant.frozen.n_rays` | B |",
           "| 3 m 시드 사다리 | `probe_8m_anomaly.json` : "
           "`runs_512pose.{E_R3_spp1.0M_seed2,F_R3_spp1.0M_seedper}.paths_median` | S |",
           "",
           "**원장 없음 두 자리** — 렌더가 찾은 경로 수(`benchmark/render_md_scene.py` 가 "
           "stdout 으로만 적는다) · 생산 판(`n_mesh=24`)의 조명점 수. 둘 다 본문에서 «원장 "
           "없음» 으로 표시했고 비율에서 뺐다.", "",
           "그림 셋(애니메이션 · f0 · f0c)의 데이터 이력은 "
           "[08_4 부록 «그림별 데이터 이력»](08_4_sampling.ipynb) 이 한 표로 낸다."),
    ]
    write("08_1", "scene", c)


# =========================================================================== #
#  08_2 — 어떻게 계산하나
# =========================================================================== #
#: 이 편이 숫자를 끌어오는 원장 — 파일 · 키 · 어디에 쓰이나. 표는 이 목록에서 난다.
_SRC_08_2 = [
    ("report07_three_engines.json",
     "`_meta` · `engines.sbr.grid_ref` · `levels_db` · `verdict.cosine_in_ftip`",
     "슬로타임 격자 · 얼린 판 · 두 팔의 레벨 차 · 세 팔 코사인"),
    ("report07_depth_robust.json", "`engines.*` · `sionna_by_range`",
     "깊이 표(p-p · p5~p95)와 거리별 요동"),
    ("outofband_power.json", "`three_engines` · `three_engines_ranking`",
     "대역밖 표와 그 대소 판정"),
    ("report07_three_engine_ranges.json", "`_meta.grid_note_ko` · `ranges.R{3,8,15}`",
     "거리 표 — Sionna 열만"),
    ("probe_8m_anomaly.json", "`runs_512pose` · `prior_probe_reanalysis`",
     "시드 사다리 · √spp 기울기"),
    ("sbr_grid_convergence.json", "`rows` · `in_band_fidelity.rows`",
     "격자 사다리 — 간격 · 광선 수 · 코사인"),
    ("verify_frozen_grid.json",
     "`gate1_bit_identity` · `gate2_frozen_grid_invariant` · `gate3_coverage` · `field_level`",
     "자 흔들림 실측(검증판)과 «대가» 표"),
    ("freeze_before_after.json", "`ledgers` · `summary` · `additivity` · `off_switch_gate`",
     "얼리기 전후 27 열과 가산성 검사"),
    ("report15_verdict.json", "`sionna` · `po` · `tail_excess`",
     "절 «…겹치고 위에서 갈린다» 의 두 팔과 꼬리 초과"),
    ("report15_verdict_po_grid.json", "`meta.baseline_m` · `meta.engine`",
     "그 절의 기하(기선)와 대조군 커널"),
    ("report15b_microdoppler.json", "`cells[matrice4e/belly].findings`",
     "가림만 떼어낸 축(F ↔ G)의 실측"),
    ("report15_blade_flash_ladder.json", "`_meta` · `budget_axis` · `elevation_axis` · `verdict`",
     "정반사 «0 칸» 의 예산·앙각 시험"),
    ("report00_microdoppler.json", "`specular_census` · `rows[matrice4e].farfield_m`",
     "정반사 인구조사 총계 · 원거리장 경계"),
]


def _sources_cell_08_2() -> list:
    """편 끝의 «## 출처» — 파일이 디스크에 있는지까지 확인해 적는다."""
    rows = []
    for f, keys, use in _SRC_08_2:
        mark = "" if os.path.exists(f"{_ROOT}/outputs/{f}") else " ⚠**없음**"
        rows.append(f"| `outputs/{f}`{mark} | {keys} | {use} |")
    return ["## 출처", "",
            f"이 편의 숫자는 아래 {len(rows)} 개 원장에서 난다. 표시 규약(조각 길이 · hop · "
            "제로패딩)과 세 팔의 이름은 코드 `src/md_mapstyle.py` 가 정본이다.", "",
            "| 원장 | 키 | 이 편의 어디에 |", "|---|---|---|", *rows, "",
            "⚠ 그림 `report07_f2` 는 위 목록의 `report15_verdict.json` 계열에서 나고, 나머지 "
            "그림(`report07_f12` · `report07_f8`)은 세 엔진 원장에서 난다 — 두 계열은 자세도 "
            "기하도 달라 절대 레벨을 섞어 읽으면 어긋난다."]


def build_08_2():
    _CUR[0] = "08_2"
    # ── 절 «…겹치고 위에서 갈린다» 의 팔과 기하 — 낱말이 아니라 원장 키에서 센다 ──────
    #    ⭐ `po`·`pose` 처럼 낱말이 겹치므로, 팔은 **최상위 키**로만 판별한다.
    _f2_keys = [k for k in ("sionna", "sbr", "po") if k in VERD]
    _f2_arms = " ↔ ".join({"sionna": ARM_SIONNA, "sbr": ARM_SBR, "po": CTRL}[k]
                          for k in _f2_keys)
    _f2_note = (f"**{ARM_SBR} 은 이 원장 밖이다** — 그래서 여기서 벌어지는 폭은 «가림을 켠 우리 "
                "커널 ↔ 스톡» 이 아니라 «가림 없는 대조군 ↔ 스톡» 이다. 가림을 켠 팔로 같은 "
                "물음을 재는 자리는 위의 세 엔진 절과 그 아래 격자 절이다."
                if "sbr" not in _f2_keys else
                "세 팔이 다 들어 있으므로 폭을 팔별로 갈라 읽어라.")
    #: 이 그림의 기하·대조군 커널 — 원장이 스스로 적는다(기선 0.2 m · 가림 없음).
    _PG = (_opt(f"{_ROOT}/outputs/report15_verdict_po_grid.json") or {}).get("meta") or {}
    _f2_base = (f"{_PG['baseline_m']:.2f} m" if _PG.get("baseline_m") is not None
                else "«원장 없음»")
    _f2_engine = _PG.get("engine", "«원장 없음»")
    c = [
        md("# 리포트 8-2 — 마이크로도플러: 세 엔진과 거리", "", NAV, "",
           "> **같은 장면을 세 가지로 계산하면 무엇이 갈리나.** "
           "대조군이 없으면 우리 맵이 틀렸는지 알 방법이 없다.", "",
           "장면은 [08_1](08_1_scene.ipynb) 이 세웠다. 이 편은 **계산 엔진**만 다룬다.", "",
           LEDGER_NOTE, "",
           _pending_note()),

        md("## 세 엔진이 각각 무엇을 하나", "",
           "| 엔진 | 무엇을 쏘나 | 무엇을 세나 | 무엇이 빠지나 |",
           "|---|---|---|---|",
           "| **Sionna PathSolver** | TX 에서 광선을 뿌린다 | 표적을 맞고 돌아온 **경로**의 "
           "진폭·지연으로 h = Σ a_p·e^(−j2πf_cτ_p) | 경로가 열 가닥 남짓이라 재료가 성기다. "
           "프롭을 맞은 **정반사** 경로는 이 격자에서 **0 칸**(아래) |",
           f"| **Ours (SBR+PO, 기본)** | 표적에 **앵커한** λ/12(= {SG12['spacing_mm']:.1f} mm) "
           f"격자로 평면파 조명 — {_ray_count_phrase()} | 광선이 **처음 맞은 "
           "지점만** 면적분 — E = Σ&#124;Γ(θ)&#124;·e^(j2k p·û)·d² (입사 코사인은 가중이 아니라 "
           "**문지기**다: n̂·û>0 인 점만 든다. 광선을 û 로 쏘므로 셀의 투영면적이 d² 와 "
           "상쇄된다) | 가려진 면이 자동으로 빠진다 (가림이 공짜) |",
           "| **Ours, nothing blocked (control)** | 광선을 안 쓴다 | 점구름의 **모든 면**을 "
           "더한다 — E = Σ(n̂·û>0) &#124;Γ&#124;·(n̂·û)·ΔA·e^(j2k p·û) (여기서는 코사인이 "
           "**가중**이다) | ⚠**아무것도 안 빠진다** — 남의 뒤에 숨은 면도 셈에 든다 |",
           "",
           "⭐ 셋째 열은 **물리적으로 불가능한 상태**다. 오직 «가림이 얼마나 바꾸나» 를 재는 "
           "대조군으로만 쓴다. ⚠«드론 일부만 그린 것» 이 아니다 — 동체도 프로펠러도 다 들어간다.", "",
           "⚠ **둘째와 셋째는 가림 말고 이산화 방식도 다르다**(광선 격자 ↔ 점구름). "
           "그래서 둘의 차이가 «가림만» 의 값은 아니다. 가림만 떼어낸 깨끗한 축은 "
           "`report15b` 의 F(동체 Γ=0 — 막되 산란 안 함) ↔ G(동체 면만 제거, 정점은 남겨 "
           "광선 격자 동일) 이고, 이 편의 자세(배 쪽)에서 그 실측은 레벨 "
           f"{FND['occlusion_level_db']:+.2f} dB · 변조 깊이 {FND['occlusion_ptp_db']:+.2f} dB 다 "
           "— 같은 값을 [08_3](08_3_pattern.ipynb) 이 그림과 함께 낸다."),

        md("## 세 엔진을 같은 격자에, 거리 3 / 8 / 15 m (거리축은 Sionna 열만)", "",
           "**시나리오** — 같은 기체·자세·주파수·PRF·로터별 회전수로 세 엔진을 돌리고 거기에 "
           f"거리축을 얹었다. {TM['n']:,} 표본 @ PRF {TM['prf_hz']:.0f} Hz = "
           f"{TM['blade_periods']:.0f} 블레이드 주기(= {TM['n']/TM['prf_hz']*1e3:.0f} ms), 로터 산포 "
           f"±{TM['rpm_spread_frac']*100:.2f} %(PX4 **SITL**(소프트웨어 시뮬) 중간값 — "
           "⚠실기 계측이 아니다). 기하는 **진짜 모노스태틱**"
           "(TX=RX, 기선 0)이다.", "",
           "" if TRR is None else embed("report07_f12"), "",
           "⭐ **왼쪽 열만 거리마다 다시 풀었다.** 가운데·오른쪽 열은 표적 앵커 평면파 조명이라 "
           "**거리라는 변수 자체가 없고**, 그래서 세 줄에서 같은 맵이 반복된다 — 그 반복이 이 "
           f"그림의 절반이다.", "",
           "⚠ **그 배선을 원장이 스스로 적는다** — "
           + ("" if TRR_J is None else
              f"«{TRR_J['_meta'].get('grid_note_ko', '')}»"
              "(`outputs/report07_three_engine_ranges.json:_meta.grid_note_ko`). ")
           + "즉 세 거리를 다시 푼 팔은 **Sionna 하나**이고, 우리 두 팔의 «거리 무관» 은 이 "
             "그림이 잰 것이 아니라 이 파이프라인의 전제다. 그 전제를 따로 잰 원장은 "
             "`outputs/deck_ours_by_range.json`(구면파 위상으로 3 / 15 / 40 m 를 다시 계산) "
             "이고, [08_4](08_4_sampling.ipynb) §1 이 그것을 읽는다.", "",
           f"⚠ **8 m 가 원거리장 경계({FARFIELD_M:.1f} m · D = 수평 최대치수) 곁이라는 사실은 "
           "이 그림에서 아무 역할도 하지 않는다.** "
           "Sionna PathSolver 에는 근/원거리장 구분이 아예 없고(경로의 지연이 2R/c 를 표적 반지름만큼만 "
           "감싼다), 8 m 를 특별하게 만드는 것은 기하가 아니라 **난수 추첨**이다 — 아래 참조.", "",
           "**깊이는 두 자로 잰다** — p-p(max−min)는 자세 하나가 혼자 끌 수 있어서, 양 끝 "
           "5 %를 버린 **p5~p95**(95 백분위 − 5 백분위) 를 함께 낸다. 둘의 **비**가 그 팔의 "
           "안정성이다. 표는 `outputs/report07_depth_robust.json` 을 읽는다.", "",
           f"⏳ 이 원장이 아직 없다 — {PENDING}." if DEP is None else "\n".join([
               "| 엔진 | p-p | p5~p95 | 비 | 무늬 |", "|---|---|---|---|---|"] + [
               f"| {nm} | {DEP['engines'][k]['ptp_db']:.1f} dB | "
               f"{DEP['engines'][k]['p5p95_db']:.1f} dB | "
               f"{DEP['engines'][k]['ptp_over_p5p95']:.1f}× | {desc} |"
               for k, nm, desc in [
                   ("sionna", ARM_SIONNA,
                    "얼룩이 대역을 채우고 날개끝 밖에도 남는다 — 전체 전력의 "
                    f"{OOBE['sionna']['frac_of_total']*100:.2f} % 가 f_tip 밖"),
                   ("sbr", ARM_SBR,
                    f"빗살이 또렷하다 — {OOBE['sbr']['frac_of_total']*100:.2f} % 가 f_tip 밖"
                    "(⚠대조군보다는 여전히 "
                    f"{OOB['three_engines_ranking']['new_P_out_absolute']['sbr_over_po_db']:.0f} "
                    "dB 위다)"),
                   ("po", CTRL,
                    "빗살이 가장 좁고 날개끝에서 절벽처럼 잘린다 — "
                    f"{OOBE['po']['frac_of_total']*100:.5f} %")]]), "",
           ("" if not (DEP and "sionna_by_range" in DEP) else
            "⚠ **이 표의 깊이를 물리량으로 인용하지 마라.** 같은 Sionna 팔을 거리만 바꿔 재면 p-p 가 "
            + " / ".join(f"{DEP['sionna_by_range'][k]['ptp_db']:.1f}"
                         for k in ("R3", "R8", "R15"))
            + " dB 로 요동친다(3 / 8 / 15 m). 그 요동은 물리가 아니라 **광선 표본화**다 — "
              "강건한 p5~p95 로 보면 "
            + " / ".join(f"{DEP['sionna_by_range'][k]['p5p95_db']:.1f}"
                         for k in ("R3", "R8", "R15"))
            + " dB 다. ⚠ 그중 **8 m 의 작은 값은 «변조가 얕다» 가 아니라 «플래시가 없다» 는 "
              "뜻**이다 — 자세에 안 변하는 정적 받침대가 프롭 변조보다 "
            + (f"{abs(PRB['runs_512pose']['A_R8_spp7.1M_seed1']['prop_over_static_db']):.1f} dB "
               if PRB else f"{PENDING} ")
            + "높아 깊이가 눌린 것이다(아래 «추첨 한 장» 참조). ⚠ 그리고 폭을 정하는 것은 "
              "이상치 **하나가 아니다** — 최솟값 자세를 빼고 다시 재도 3 m 는 "
            + f"{DEP['sionna_by_range']['R3']['ptp_db_drop1']:.1f} dB, 15 m 는 "
            + f"{DEP['sionna_by_range']['R15']['ptp_db_drop1']:.1f} dB 가 남는다. "
              "**꼬리가 두꺼운 것**이다."), "",
           f"⭐ 셋 다 **(a) 0 도플러 동체 선 · (b) 통과율 간격 능선 · (c) 날개끝 근처 감쇠**를 "
           f"낸다 — 구조가 일치한다. 날개끝 안 스펙트럼 코사인은 "
           f"Sionna↔SBR+PO **{cos3('sionna_vs_sbr')}** · Sionna↔대조군 **{cos3('sionna_vs_po')}** · "
           f"기본↔대조 **{cos3('sbr_vs_po')}** 다.", "",
           "⭐ **이 코사인이 무엇인가** — 두 팔의 슬로타임 스펙트럼을 |f| ≤ f_tip 안에서 "
           "**크기만** 취해 정규화한 뒤 내적한 값이다(위상 원점 무관 · 1 이면 같은 모양).", "",
           _cosine_order_line(), "",
           "⚠ **세 자리를 절대 척도로 인용하지 마라 — 격자 간격에 딸려 움직인다.** 같은 두 팔을 "
           "간격만 바꿔 재면 기본↔대조가 "
           + " · ".join(f"λ/{r['div']} {r[_LADDER_KEY]:.3f}" for r in SGL)
           + " 로 옮겨 다닌다(`outputs/sbr_grid_convergence.json` · "
           + ("얼린 팔" if SBR_GRID_FROZEN else "자세마다 다시 정의하는 팔")
           + "). "
           + ("같은 사다리에서 자세마다 격자를 다시 정의하는 팔은 "
              + f"{min(r['cos_prod_vs_po'] for r in SGL):.3f}~"
              + f"{max(r['cos_prod_vs_po'] for r in SGL):.3f} 에 눌려 있고, 간격을 "
                "촘촘히 해도 거기서 안 올라온다 — 그 팔의 한계는 광선 밀도가 아니었다. "
                if SBR_GRID_FROZEN else "")
           + "즉 이 수가 말하는 것은 **이 실행에서의 순서**까지다.", "",
           *_freeze_para(),
           "| 세 팔의 대역밖 (모노 원장) | **전체 전력** 중 f_tip 밖 몫 | 날개끝 밖 바닥 |",
           "|---|---|---|",
           "\n".join(
               f"| {nm} | {v*100:.2f} % | {OOBE[k]['new_floor_rel_db_raw_mean']:.1f} dB |"
               if (v := OOBE[k]['frac_of_total']) >= 1e-4 else
               f"| {nm} | {v*100:.5f} % | {OOBE[k]['new_floor_rel_db_raw_mean']:.1f} dB |"
               for k, nm in (("po", CTRL), ("sionna", ARM_SIONNA),
                             ("sbr", ARM_SBR))),
           "",
           "⚠ **이 칸의 정의** — 평활 없는 주기도에서 |f| > f_tip 의 전력을 **전 대역 전력**으로 "
           "나눈 몫이다(분모를 열 제목에 박아 두었다). «날개끝 밖 바닥» 은 같은 주기도의 "
           "f_tip 밖 평균을 봉우리 대비로 적은 값이다.", "",
           ("" if OOBE["sionna"].get("units_comparable_to_po") is not False else
            f"⚠ **{ARM_SIONNA} 행과 견줄 수 있는 것은 이 표의 두 칸뿐이다.** 그 팔이 내는 양은 "
            "수신 전력장이고 우리 두 팔은 산란 진폭[m²]이라, 원장이 그 행에 "
            "`units_comparable_to_po = false` 를 달고 **절대 전력 순위에서 뺀다**"
            "(`outputs/outofband_power.json:three_engines_ranking.new_P_out_absolute.excluded`"
            f" — 절대 순위는 {ARM_SBR} 대 {CTRL} 둘로만 매긴다). 표의 두 칸은 각 팔이 "
            "**자기 전체 전력 · 자기 봉우리**로 정규화한 무차원 값이라 나란히 읽는다. 절대 dB 는 "
            "팔 안에서만 쓴다."), "",
           _oob_rank_line(), "",
           "" if TRR is None else "\n".join([
               "| 거리 | 광선 수 | 자세당 경로(중앙값) | 경로 0 자세 | 평균 레벨 |",
               "|---|---|---|---|---|"] + [
               f"| {TRR[k]['range_m']:.0f} m | {TRR[k]['spp']/1e6:.1f}M | "
               f"{TRR[k]['paths_median']:.0f} | {TRR[k]['paths_zero_frac']:.1%} | "
               f"{TRR[k]['level_db']:.1f} dB |" for k in ("R3", "R8", "R15")]),
           "",
           "⚠⚠ **이 표의 경로 수와 레벨은 물리량이 아니라 «추첨 한 장» 이다.** Sionna 는 확산 "
           f"경로를 몬테카를로로 **발견**하는데, 이 스윕은 자세 {TM['n']:,} 개를 전부 같은 시드로 "
           "풀었다. 드론에서 움직이는 것은 로터뿐이라 동체·랜딩기어의 경로 집합이 전 자세에서 "
           "**비트 단위로 동일**하고"
           + ("" if not PRB else
              f"(정적 성분의 유일값이 "
              f"{PRB['runs_512pose']['A_R8_spp7.1M_seed1']['static_unique_values']} 개)")
           + f", 그래서 {TM['n']/TM['prf_hz']*1e3:.0f} ms 기록 전체가 추첨 한 번을 받침대로 깔고 "
             f"있다. 자세를 {TM['n']:,} 개 평균해도 그 추첨은 평균되지 않는다.", "",
           *_seed_para(),
           "⇒ **이 표에서 인용해도 되는 것은 «빈 자세 0 %» 뿐이다**(그것은 시드에 둔감하다). "
           "원장: `outputs/probe_8m_anomaly.json`."),

        _grid_anchor_cell(),

        md("## 블레이드 플래시를 세 엔진으로 나란히 (60 ms 확대)", "",
           "**시나리오** — 위와 **같은 원장·같은 슬로타임 격자·같은 로터 회전수**에서 60 ms 만 "
           "잘라 확대했다. 세 패널의 차이는 **산란 엔진뿐**이다. 조각은 블레이드 한 주기의 "
           f"{SEG_PER:.2f} 배라 플래시가 시간평균으로 지워지지 않는다.", "",
           embed("report07_f8"), "",
           f"⭐ 세로 아치가 블레이드 플래시이고 **{1000/TM['f_flash_hz']:.1f} ms 마다** 반복한다"
           f"(= f_flash {TM['f_flash_hz']:.0f} Hz). 세 엔진이 그 주기를 같이 낸다는 것이 "
           "이 그림의 첫 확인이다. 모양은 갈린다 — **우리 두 팔은 같은 자리에 같은 아치를 "
           f"낸다**(대역 안 코사인 {cos3('sbr_vs_po')}). 가림을 켠 기본팔의 아치가 도플러축으로 "
           "조금 더 넓게 번지고 날개끝 선 위로 옅은 꼬리를 남기는 것이 둘의 남은 차이이며, "
           "Sionna 는 아치라기보다 얼룩에 가깝다.", "",
           *_flash_census_para(),
           "⭐ **시간 분해능을 주파수 분해능보다 앞세운다.** 조각을 한 주기보다 길게 잡으면 "
           "플래시는 그 안에서 평균돼 사라지고 가로 능선만 남는다. 그래서 조각을 "
           f"**한 주기보다 짧게**({SEG_PER:.2f} 주기) 잡는다 — 정본은 `src/md_mapstyle.py` 다.", "",
           f"⚠ **{SEG_PER:.2f} 가 최적이라는 측정 근거는 없다** — 그림이 실제로 또렷해서 쓰는 "
           "값이다. 인용해도 되는 것은 정의가 하나뿐인 양뿐이다 — 조각 "
           f"{SEG_N} 표본 · Δt {SEG_MS:.2f} ms · Δf {SEG_HZ:.0f} Hz "
           f"(hop {FLASH_HOP} 표본 · 제로패딩 {FLASH_PAD} 배).", "",
           "⚠ 세 패널은 각자 최대로 정규화했다 — 이 그림은 **구조를 비교하지 레벨을 비교하지 않는다**.", "",
           "⚠⚠ **패널 사이의 레벨 차를 그대로 읽으면 안 된다.** 두 팔이 내는 양의 **단위가 "
           "다르다** — Sionna 는 1/R² 를 두 번 먹은 **수신 전력장**을 주고, 우리 커널은 표적의 "
           f"**산란 진폭**[m²]을 준다. {RANGE_M:.0f} m 에서 그 환산항만 −20log₁₀(4πR²) = "
           f"**{CONV_DB:.1f} dB** 다. 원장의 실측 격차 {num(GAP_DB)} dB 에서 환산을 빼면 남는 것은 "
           f"**{num(RESID_DB)} dB** 이고, 그것이 «프롭 정반사 경로가 0 칸» 으로 설명해야 할 "
           "몫이다. 단위가 다른 두 수의 차를 물리량으로 인용하지 마라."),

        md("## 스톡 PathSolver 와 가림 없는 대조군이 날개끝 아래에서 겹치고 위에서 갈린다", "",
           embed("report07_f2"), "",
           f"⭐ **이 그림에 선 팔은 둘이다 — {_f2_arms}.** 원장 "
           f"`outputs/report15_verdict.json` 의 최상위 팔 키가 그 둘이고"
           f"({' · '.join('`' + k + '`' for k in _f2_keys)}), {_f2_note}", "",
           "1 차원 스펙트럼으로 보면 두 팔이 **날개끝 주파수 아래에서 겹치고 위에서 갈린다**. "
           f"{ARM_SIONNA} 꼬리가 {CTRL} 대비 **{GAP_M4E:.1f} dB**(matrice4e) · "
           f"**{GAP_MINI2:.1f} dB**(mini2) 높다.", "",
           "⚠ **꼬리 초과의 정의** — 날개끝 주파수 **밖**(f_tip 초과) 빈들의 평균 레벨을 두 팔에서 "
           "각각 재어 뺀 값이다(봉우리 정규화 뒤).", "",
           f"⚠ **이 그림만 자세도 기하도 다르다** — 자세는 08_1 의 배 쪽"
           f"(el {TM['el_deg']:.0f}°) 대신 nose(el +15°)이고, 기하는 절 2 의 진짜 모노스태틱"
           f"(기선 0) 대신 **준-모노스태틱 기선 {_f2_base}** 다. 대조군 커널도 이 원장 전용이다 — "
           f"«{_f2_engine}»"
           "(`outputs/report15_verdict_po_grid.json:meta`). 원장이 다르다"
           f"(`outputs/report15_verdict.json` · {VERD['meta']['stamp'][:10]}). "
           "무늬 세부와 절대 레벨을 위 맵들과 직접 견주면 안 된다."),

        md("## 이 편이 서 있는 자리", "",
           "세 엔진이 **같은 주기**를 낸다. 모양은 **우리 두 팔끼리 거의 같고**"
           f"(대역 안 코사인 {cos3('sbr_vs_po')}) 남은 갈림은 가림이 만든다. "
           f"{ARM_SIONNA} 는 둘 모두에서 떨어져 있고({cos3('sionna_vs_sbr')} · "
           f"{cos3('sionna_vs_po')}) 그 원인은 경로 수 — 프롭 정반사가 **인구조사 격자에서** "
           "0 칸이다.", "",
           *_census_scope_para(),
           "⭐ 그리고 그 «거의 같다» 는 **광선 격자를 얼린 뒤에** 나온 자리다. 자를 자세마다 "
           "다시 놓던 판에서는 같은 두 팔이 훨씬 덜 닮았다 — **절 «광선 격자를 어디에 매나»**.", "",
           "| 다음 | 무엇을 답하나 |", "|---|---|",
           "| [08_3 무늬를 정하는 것](08_3_pattern.ipynb) | 회전수·가림·산포가 무늬를 어떻게 바꾸나 |",
           "| [08_4 무엇을 잴 수 있나](08_4_sampling.ipynb) | 이 계산을 얼마나 멀리·얼마나 자주 할 수 있나 |",
           "| `reports/09_microdoppler-limits.ipynb` | 자세·보정·광선 예산의 단일축 분해 |"),

        md(*_sources_cell_08_2()),
    ]
    write("08_2", "engines", c)


# =========================================================================== #
#  08_3 — 무엇이 무늬를 정하나
# =========================================================================== #
def build_08_3():
    _CUR[0] = "08_3"
    # ⭐ 2 초 호버 두 열(f7·f11)에 순수 PO 대조가 없다는 것을 원장이 스스로 적는다.
    #    그 선언을 본문으로 데려온다 — 이 편만 쓰는 원장이라 여기서 읽는다.
    _fsl = _opt(f"{_ROOT}/outputs/freeze_signal_loss.json") or {}
    _FSL_OPEN = ((_fsl.get("verdict") or {}).get("open_ko")
                 or "⛔ 원장 없음 — `outputs/freeze_signal_loss.json : verdict.open_ko`")
    # ⛔ 상설 규칙 — 얼린 팔의 **절대 레벨**과 가림 축의 **dB 크기**는 격자 판 한 장의
    #    서브셀 오프셋에 걸린다. 판 셋으로 잰 흩어짐이 그 값을 덮으므로 본문은 크기를 뺀다.
    _fps = (_opt(f"{_ROOT}/outputs/freeze_plate_sensitivity.json") or {}).get("verdict") or {}

    def _pl(key: str) -> str:
        v = _fps.get(key)
        return f"{v:.2f} dB" if isinstance(v, (int, float)) else "«원장 없음»"

    _PL_ABS, _PL_OCC, _PL_PTP = (_pl("abs_level_plate_ptp_db"),
                                 _pl("occlusion_level_plate_ptp_db"),
                                 _pl("occlusion_ptp_plate_ptp_db"))
    #: 두 채널의 레벨 **차** — 절대 두 수는 본문 밖이고, 차는 위 흩어짐을 한 자릿수 넘는다.
    _LVL_GAP = ARM["B_sbr_spread"]["level_db"] - ARM["F_blade_occ"]["level_db"]
    c = [
        md("# 리포트 8-3 — 마이크로도플러: 무엇이 무늬를 정하나", "", NAV, "",
           "> **회전수·가림·산포 세 가지가 무늬를 정한다.** 각각을 갈라서 얼마나 바꾸는지 잰다.", "",
           "엔진 비교의 **결론**은 [08_2](08_2_engines.ipynb) 가 요약하고, 그 **근거 절은 이 편 "
           "절 3**(«두 엔진이 갈린다») 에 있다. 앞머리 네 그림은 **표적 쪽 요인**을 다룬다.", "",
           "⭐ **이 편이 쓰는 팔 셋** — **S** = " + ARM_SIONNA + " · **B** = " + ARM_SBR
           + "(광선 격자로 가림을 푼다) · **P** = " + ARM_PO
           + "(점구름 면적분 · 광선 격자를 안 쓴다). 절마다 어느 팔이 재었는지를 이 세 이름으로 "
           "적는다.", "",
           _grid_state_08_3(), "",
           LEDGER_NOTE),

        md("## 회전수가 같으면 무늬가 시간에 안 변한다", "",
           embed("report07_f1"), "",
           f"왼쪽은 네 로터를 **같은 회전수**로 돌린 것이다. 줄무늬가 시간축 내내 같은 자리에 선다 — "
           f"창을 반으로 갈라 두 스펙트럼의 상관을 재면 **{R['locked_half_corr']:.4f}** 다. "
           "우연이 아니라 원리다: 네 로터가 같은 속도로 돌면 신호가 완전한 주기함수가 되고, "
           "주기함수의 스펙트로그램은 창 내내 자기 모습을 지킨다.", "",
           f"오른쪽은 로터마다 회전수를 **±{SPREAD*100:.2f} %** 흩뜨린 것이다 — 추측이 아니라 "
           "**PX4 SITL**(소프트웨어 인더루프 = 시뮬) 로그에서 모터 간 0.07~0.29 % 를 재서 "
           "고른 중간값이다. ⚠**실기 텔레메트리가 아니다** — 아래 «로터 산포 프리셋 비교» 가 "
           "실기 비행로그 세 종으로 이 값이 야외 호버를 한 자릿수 과소평가함을 보인다. "
           f"이 그림에서 ±{SPREAD*100:.2f} % 는 «산포가 무늬를 시간에 변하게 한다» 를 보이는 "
           "**하한 예시**다. "
           f"상관이 **{R['spread_half_corr']:.4f}** 로 내려가고(낙차 {R['drop']:.4f}) 줄이 "
           "숨쉬듯 흔들린다. ⭐그 내려감이 «시간에 따라 변한다» 의 정량이다.", "",
           f"⭐ **두 팔이 같은 낙차를 낸다.** 위 두 수는 **B 팔**(SBR)이고, 같은 칸의 **P 팔**"
           f"(순수 PO · 가림 없음 · 광선 격자 안 씀)은 "
           f"{ARM['C_po_locked']['half_window_spectrum_corr']:.4f} 에서 "
           f"{ARM['D_po_spread']['half_window_spectrum_corr']:.4f} 로 내려간다. 가림을 켠 팔과 "
           "아예 안 켠 팔이 같은 답을 내므로, 이 축의 원인은 **rpm 산포** 하나다"
           f"(`outputs/report15b_microdoppler.json : cells.{LEAD['drone']}/{LEAD['aspect']}"
           ".arms.{C_po_locked, D_po_spread}`)."),

        md("## 동체가 막으면 무엇이 달라지나", "",
           embed("report07_f4"), "",
           f"가림 단일축(F↔G)의 실측이다 — 둘 다 **B 팔**(SBR)이고, 광선 엔진·재질·기하·"
           "운동학·**광선 격자**까지 같고 오직 «동체가 막느냐» 만 다르다. 막으면 **레벨과 변조 "
           "깊이가 함께 움직인다**.", "",
           f"⛔ 그 움직임의 **dB 크기는 본문 밖**이다 — 격자 판을 반 칸 옮기면 레벨 차가 "
           f"{_PL_OCC}, 깊이 차가 {_PL_PTP} 흔들려 원장 값을 덮는다"
           "(`outputs/freeze_plate_sensitivity.json : verdict`). 크기가 필요한 자리에서는 판 "
           "앙상블 평균이 먼저이고, 그 실측 표는 절 5 가 낸다.", "",
           "⭐ **이 축은 B 팔에서만 선다** — P 팔(순수 PO)은 모든 면이 항상 기여하는 설계라 "
           "«막느냐» 라는 스위치가 그 팔의 밖에 있다. 그래서 이 그림에는 P 대조가 없고, "
           "그 사실이 이 축의 한계다.", "",
           "⚠ 합이 코히런트라 **가림이 레벨을 올릴 수도 있다** — 항이 줄어도 남은 항끼리 상쇄가 "
           "덜 되면 그렇다. 부호를 물리로 단정하지 말 것. 여섯 칸에서 부호가 실제로 갈린다 — "
           "칸별 부호표는 절 5 가 낸다."),

        md("## 블레이드는 강하고 동체가 덮는다", "",
           embed("report07_f3"), "",
           "⭐ 이 편들의 핵심 발견 하나 — **블레이드 신호가 약한 게 아니라 동체가 덮고 있다.** "
           f"같은 얼린 판·같은 자세·같은 로터 회전수의 두 **B 팔** 실행을 읽으면 전체 드론 "
           f"채널의 변조 깊이는 "
           f"{ARM['B_sbr_spread']['modulation_ptp_db']:.2f} dB p-p 인데, 프로펠러 채널만 떼면 "
           f"{ARM['F_blade_occ']['modulation_ptp_db']:.2f} dB p-p 다"
           f"({MDB['_meta']['fc_hz']/1e9:.1f} GHz · 방위 {LEAD['az_deg']:.0f}° · "
           f"앙각 {LEAD['el_deg']:.0f}°) — "
           f"{ARM['F_blade_occ']['modulation_ptp_db']/ARM['B_sbr_spread']['modulation_ptp_db']:.0f} "
           "배 차이다.", "",
           f"레벨은 반대다 — 프로펠러 채널이 전체 채널보다 **{_LVL_GAP:.2f} dB** 아래라 동체 "
           "쪽이 그만큼 밝다(위 두 원장 값의 차). 두 줄을 같이 읽으면 **동체가 밝아서 변조를 "
           "눌렀다** 가 나온다 — 검출 축에서 정적 성분을 지우는 이유가 여기 있다.", "",
           f"⛔ 절대 레벨 두 수는 본문 밖에 둔다 — 얼린 팔의 절대 레벨은 격자 판 한 장의 서브셀 "
           f"오프셋에 {_PL_ABS} p-p 로 걸리고, 절대 σ 는 디더를 켠 정적 경로가 낸다. 위 **차**는 "
           "그 흩어짐의 여섯 배라 그대로 선다.", "",
           "⛔ **이 그림의 밴드별 dB 는 원장 밖이다** — 값이 그림 빌더에 박혀 있고"
           "(`benchmark/build_report07_figs.py:221-222`, 2026-08-07 실행) 그 실행의 원장이 "
           "`outputs/` 에 없다. 위 문단이 선 원장은 **3.5 GHz 한 밴드**뿐이라 나머지 다섯 "
           "밴드는 «원장 없음» 이다. 그림에서 읽는 것은 두 채널의 **순서**다.", "",
           f"원장: `outputs/report15b_microdoppler.json : "
           f"cells.{LEAD['drone']}/{LEAD['aspect']}.arms"
           ".{B_sbr_spread, F_blade_occ}`."),

        md("## 2 초 호버링 — 능선과 로터 회전수", "",
           embed("report07_f7"), "",
           f"{HOV['seconds']:.0f} 초 · {HOV['n']:,} 표본 · {HOV['blade_periods']:.0f} 블레이드 주기. "
           "아래 패널이 네 로터의 회전수다 — 능선이 어떻게 움직이는지의 원인이 거기 있다.", "",
           f"⭐ 로터별 산포는 **{HOV['static_spread']:.2%}** 다. 로터들이 이만큼 가까운 속도로 "
           "돌기 때문에 네 빗살이 고조파마다 정렬되고 능선이 가늘게 선다.", "",
           "⚠ **이 그림과 다음 그림은 B 팔(SBR) 한 팔이다 — P 대조가 없다.** 원장이 그 사실을 "
           f"스스로 적는다: {_FSL_OPEN}", "",
           f"⚠ 제어루프 흔들림(±{HOV['wobble_amp']:.2%} @ {HOV['wobble_hz']:.1f} Hz)은 "
           "**선언된 가정**이다 — 우리 표적의 실측 비행 로그가 그 자리를 채운다."),
    ]
    if HOD is not None:
        c.append(md(
            "## 로터 산포 프리셋 비교: 실내-이상 하한 vs 야외 앵커", "",
            "**시나리오** — 위와 완전히 같은 계산(같은 기체·자세·2 초·SBR 팔)이고, 바꾼 것은 "
            f"**로터 산포 프리셋 하나**다. 왼쪽이 실내-이상(±{HOV['static_spread']:.2%}), "
            f"오른쪽이 **야외 프리셋**(±{HOD['static_spread']:.0%} · 흔들림 "
            f"±{HOD['wobble_amp']:.1%} @ {HOD['wobble_hz']:.1f} Hz)이다.", "",
            "⭐ 야외 프리셋의 출처는 **논문이 아니라 공개 비행로그 데이터셋 세 종**이다 — "
            "우리가 직접 내려받아 호버 구간을 잘라 재서 얻은 값이다.", "",
            "| 데이터셋 | 기체·환경 | 신호 | 정적 산포(중앙) | 흔들림(중앙) |",
            "|---|---|---|---|---|",
            _rl_rows(),
            "",
            "⚠ 세 줄의 한계는 각각 다르다. 앞의 둘은 **DJI 가 아니고**, CODEV 는 표본율 "
            f"{_RLS.get('px4', {}).get('fs_hz', float('nan')):.0f} Hz 라 나이퀴스트 "
            f"{_RLS.get('px4', {}).get('fs_hz', float('nan'))/2:.0f} Hz 위가 접혀 진폭이 "
            "과대측정될 수 있다. 셋째만 진짜 DJI 인데 **실측 rpm 이 아니라 PWM 명령**이라 "
            "백분율의 뜻이 앞의 둘과 다르다. 그래서 야외 프리셋 "
            f"±{HOD['static_spread']*100:.0f} % 는 **세 줄을 합쳐 반올림한 자릿수 앵커**이지 "
            "우리 표적의 실측이 아니다.", "",
            embed("report07_f11"), "",
            "⭐ 읽는 법 — 왼쪽은 로터들이 거의 같은 속도라 고조파 빗살이 정렬된다. 오른쪽은 "
            "로터별 f_tip 이 수십 Hz 씩 갈라져 능선이 **얽힌 뱀처럼** 교차한다. "
            "⭐⭐그런데 **세로 플래시 아치는 양쪽 다 남는다** — 산포는 능선(주파수축 구조)을 "
            "뭉개지만 플래시(시간축 사건)는 못 지운다. 시간 분해능을 우선하는 표시 규약이 "
            "야외에서 더 중요해지는 물리적 이유가 이것이다."))
    if _HAS_F13:
        c.append(md(
            "## 그 «야외 앵커» 를 눈으로: 공개 비행로그 세 종의 실측", "",
            "위 표의 근거를 그림으로 본다. 곡선과 상자는 인용이 아니라 **그 로그를 직접 열어 "
            "우리가 잰 값**이다. 세 로그에서 호버 구간(|v| < 0.3 m/s)을 전부 뽑아 같은 규약으로 쟀다.", "",
            embed("report07_f13"), "",
            "윗줄은 데이터셋마다 호버 창 하나를 골라 모터 넷을 겹쳐 그린 것이고, 아랫줄은 "
            "**찾아낸 모든 호버 창**의 산포·흔들림 분포에 우리 두 프리셋을 가로선으로 얹은 것이다. "
            "⭐야외선이 PX4 야외 상자를 관통하고 실내선은 NeuroBEM 상자 **아래**에 놓인다.", "",
            f"⭐ 세 독립 원천이 **같은 방향**을 가리킨다 — SITL 유래 ±{SPREAD*100:.2f} % 는 "
            "실기체 야외 호버를 "
            "한 자릿수 과소평가한다. 우리 표적(Mavic 4 Pro·Matrice 4E)의 실측 rpm 로그는 여전히 "
            "없고(Mavic Air 이후 DJI DAT 은 암호화), 그 구멍은 X410 필드테스트로만 닫힌다."))
    c.append(md(
        "## 이 편이 서 있는 자리", "",
        "무늬를 정하는 것은 **회전수의 균일함 · 동체의 가림 · 로터 산포** 셋이다.", "",
        "| 다음 | 무엇을 답하나 |", "|---|---|",
        "| [08_4 무엇을 잴 수 있나](08_4_sampling.ipynb) | 광선 비용과 조명원 반복률 |",
        "| `reports/09_microdoppler-limits.ipynb` | 자세·보정·광선 예산의 단일축 분해 |",
        "| `reports/10_illuminators.ipynb` | 조명원별로 무엇을 쓸 수 있나 |"))
    write("08_3", "pattern", c)


# =========================================================================== #
#  08_4 — 무엇을 잴 수 있나
# =========================================================================== #
def build_08_4():
    _CUR[0] = "08_4"
    # ⭐ §1 의 «거리 비용» 을 **두 팔에서 실제로 잰** 원장 셋 — 그림 f9 (c) 가 같은 값을 그린다.
    #    자세 수가 셋 다 4096 이라 «자세당 벽시계 초» 로 바로 견준다. 없는 칸은 지어내지 않는다.
    _DK = _opt(f"{_ROOT}/outputs/deck_ours_by_range.json")
    _TER = _opt(f"{_ROOT}/outputs/report07_three_engine_ranges.json")
    _R40 = _opt(f"{_ROOT}/outputs/report07_range40_raybudget.json")
    _NOL = "«원장 없음»"

    _ps, _psr = [None, None, None], [None, None, None]   # S 팔 규칙 예산 판 · 3/15/40 m
    if _TER:
        _n_ter = _TER["_meta"]["n"]
        for _i, _k in enumerate(("R3", "R15")):
            _ps[_i] = _TER["ranges"][_k]["seconds"] / _n_ter
            _psr[_i] = _TER["ranges"][_k]["spp"]
    _big = _bigr = _bigh = _bignp = None
    _bign = 0
    if _R40:
        _rule = [r for r in _R40["rows"] if r["spp"] < 1e9]
        _huge = [r for r in _R40["rows"] if r["spp"] >= 1e9]
        if _rule:
            _ps[2] = _rule[0]["seconds"] / _rule[0]["n_poses"]
            _psr[2] = _rule[0]["spp"]
        if _huge:
            _big = sum(r["seconds"] / r["n_poses"] for r in _huge) / len(_huge)
            _bigh = sum(r["seconds"] for r in _huge) / len(_huge) / 3600.0
            _bigr, _bign, _bignp = _huge[0]["spp"], len(_huge), _huge[0]["n_poses"]
    _our = ([_DK["ranges"][k]["cpu_seconds"] / _DK["_meta"]["n"]
             for k in ("3", "15", "40")] if _DK else [None, None, None])

    def _sc(v, fmt="{:.3f} s"):
        return _NOL if v is None else fmt.format(v)

    _cost_rows = "\n".join([
        "| **S** · Sionna PathSolver | 규칙값 "
        + " / ".join(_NOL if r is None else f"{r/1e6:,.0f}M" for r in _psr) + " 발 | "
        + " | ".join(_sc(v) for v in _ps)
        + " | `report07_three_engine_ranges` · `report07_range40_raybudget` |",
        "| **S** · Sionna PathSolver | 40 m 에서 "
        + (_NOL if _bigr is None else f"{_bigr/1e6:,.0f}M") + " 발 | — | — | "
        + _sc(_big, "{:.2f} s") + (f" (시드 {_bign} 판 평균)" if _bign else "")
        + " | `report07_range40_raybudget` |",
        "| **B** · 우리 SBR+PO | 얼린 격자 한 벌 · 위상만 구면파 | "
        + " | ".join(_sc(v) for v in _our) + " | `deck_ours_by_range` |"])
    _r_budget = _NOL if (_big is None or not _ps[2]) else f"{_big/_ps[2]:.1f}"
    _r_rays = _NOL if (_bigr is None or not _psr[2]) else f"{_bigr/_psr[2]:.1f}"
    _r_ours40 = _NOL if (_big is None or not _our[2]) else f"{_big/_our[2]:.1f}"
    _big_hours = _NOL if _bigh is None else f"{_bigh:.1f} 시간"
    _big_poses = _NOL if _bignp is None else f"{_bignp:,} 개"
    _minus = (lambda v, f="{:.0f}": f.format(v).replace("-", "−"))

    # ⭐ 편 끝의 «## 출처» — 08_3·08_5 와 같은 규약. 파일이 디스크에 있는지까지 확인해 적고,
    #    «팔» 칸으로 어느 엔진이 그 값을 냈는지를 못 박는다.
    _src_08_4 = [
        ("report07_sionna_ranges.json",
         "`_meta.{spp_scaling_ko,n,prf_hz,farfield_boundary_m}` · "
         "`ranges.*.{range_m,spp,paths_zero_frac}`", "S", "§1 예산비 · 40 m 빈 자세"),
        ("report07_ray_budget_test.json",
         "`_meta.{range_m,n_poses,rule_value_spp,verdict_ko}` · `ladder.*`", "S",
         "§1 결판 시험 표 · 판정"),
        ("report07_three_engine_ranges.json",
         "`_meta.{n,grid_note_ko}` · `ranges.{R3,R15}.{spp,seconds}`", "S",
         "§1 비용표 3 · 15 m"),
        ("report07_range40_raybudget.json",
         "`_meta.range_m` · `rows[*].{spp,seconds,n_poses}`", "S",
         "§1 비용표 40 m 두 예산"),
        ("deck_ours_by_range.json",
         "`_meta.{drone,az_deg,el_deg,fc_hz,prf_hz,n}` · `ranges.{3,15,40}.cpu_seconds`",
         "B", "§1 비용표 우리 팔 · 그림 f9 (c)"),
        ("report00_microdoppler.json", "`rows[matrice4e].farfield_m`", "해",
         "§1 원거리장 경계"),
        ("report15_probe.json",
         "`airframes.matrice4e.physics.{D_horizontal_m,D_diag3d_m,farfield_diag3d_m}`",
         "해", "§1 D 정의 둘"),
        ("report07_5g_waveform.json",
         "`_meta.*` · `arms.*.{label,fs_hz,n,nyquist_hz,ftip_folds,fflash_folds}`", "B",
         "§2 전부(채널열은 얼기 전 판)"),
        ("report07_three_engines.json",
         "`_meta.{prf_hz,f_flash_hz}` · `engines.sbr.grid_ref`", "B",
         "부록 표시 규약 · f12 · f8 행"),
        ("report15_verdict.json", "`meta.stamp`", "S·P", "부록 f2 행"),
        ("report15b_microdoppler.json", "`_meta` · `cells[matrice4e/belly].physics`", "B",
         "부록 f1 · f4 행"),
        ("report07_hover_long.json", "`_meta.{generated,regenerated,prf_hz,grid_ref}`", "B",
         "부록 f7 행 · §2 채널의 현재 판"),
        ("report07_hover_long_outdoor.json", "`_meta.{generated,prf_hz}`", "B",
         "부록 f11 행"),
        ("rotor_log_traces.json", "`sources.*`(공개 비행로그)", "측정", "부록 f13 행"),
    ]

    def _src_rows_08_4() -> str:
        out = []
        for f, keys, arm, where in _src_08_4:
            mark = "" if os.path.exists(f"{_ROOT}/outputs/{f}") else " ⚠**없음**"
            out.append(f"| `outputs/{f}`{mark} | {keys} | **{arm}** | {where} |")
        return "\n".join(out)

    _our_span = (_NOL if None in _our else
                 f"{min(_our):.3f}~{max(_our):.3f} s")
    # ⭐ §2 표의 표본율은 «라벨» 이다 — 파형 스크립트가 보간 비를 5 kHz 로 못 박아 두어
    #    실제 시간축은 채널 PRF 만큼 늘어난다. 배율과 실제 축을 **같은 원장 두 키**로 다시
    #    잰다(표본 수 ÷ 기록 길이). 새 계산 없이 산술만 한다.
    _T5 = WA["cw_5k"]["n"] / WA["cw_5k"]["fs_hz"]
    _fs_true = {k: WA[k]["n"] / _T5 for k in WA}
    _mult5 = _fs_true["nr_full_28k"] / WA["nr_full_28k"]["fs_hz"]
    _nyq_crs, _nyq_ssb = _fs_true["nr_crs_1k"] / 2.0, _fs_true["nr_ssb_50"] / 2.0
    _cost_setup = ("" if not _DK else
                   f"{_DK['_meta']['drone']} · 방위 {_DK['_meta']['az_deg']:.0f} · 앙각 "
                   f"{_minus(_DK['_meta']['el_deg'])} · {_DK['_meta']['fc_hz']/1e9:.1f} GHz · "
                   f"슬로타임 {_DK['_meta']['prf_hz']/1e3:.1f} kHz · 자세 "
                   f"{_DK['_meta']['n']:,} 개")
    c = [
        md("# 리포트 8-4 — 마이크로도플러: 무엇을 잴 수 있나", "", NAV, "",
           "> **두 가지가 잴 수 있는 것을 제한한다 — 광선 비용과 조명원 반복률.** "
           "앞의 것은 우리가 감당하는 문제이고, 뒤의 것은 우리가 못 정하는 조건이다.", "",
           LEDGER_NOTE),

        md("## 거리 — 벽인가 예산인가", "",
           "**시나리오** — 진짜 모노스태틱(TX=RX, 기선 0), 배 쪽(방위 0·앙각 −15), "
           f"{RGM['fc_hz']/1e9:.1f} GHz CW. 표적을 3 → 10 → 20 → 40 m 로 물리며 자세당 "
           "발견 경로 수를 셌다.", "",
           embed("report07_f9"), "",
           "⭐ **판마다 선 팔이 다르다** — (a)(b) 는 **S 팔**(광선 예산 축) 하나로 서고, "
           "(c) 만 두 팔의 실측을 나란히 놓는다. 이 절의 거리 스윕 원장 둘"
           "(`report07_sionna_ranges` · `report07_ray_budget_test`)은 S 팔 키(`spp` · "
           "`paths_*`)만 담는다 — **B 팔의 거리 비용은 `deck_ours_by_range.json` 이 따로 "
           "잰 것**이고 아래 표 셋째 행이 그 값이다.", "",
           "⚠ **이 스윕이 쓴 광선 예산은 규칙값보다 적다 — 그것을 먼저 적는다.** 표적이 "
           "멀어지면 그만큼 작게 보이므로 광선을 (R/3)² 로 늘리는 것이 이 프로젝트의 규칙인데"
           "(원장 `_meta.spp_scaling_ko`), 이 스윕이 실제로 준 것은 규칙값의 "
           + " / ".join(
               f"**{RGR[k]['spp'] / (RGR['R3']['spp'] * (RGR[k]['range_m'] / RGR['R3']['range_m'])**2):.2f}**"
               for k in ("R3", "R10", "R20", "R40"))
           + " 배다"
           + " (" + " / ".join(f"{RGR[k]['range_m']:.0f} m" for k in ("R3", "R10", "R20", "R40"))
           + f"). 그래서 40 m 에서 자세의 {RGR['R40']['paths_zero_frac']:.1%} 가 경로 0 인 것은 "
           "**거리의 성질이 아니라 그 예산의 성질**이다.", "",
           "" if RBT is None else "⭐ 그 둘을 가르려고 **결판 시험**을 했다 — 40 m 를 고정하고 "
           "자세·기하·회전수를 그대로 둔 채 **광선만** 사다리로 올렸다.", "",
           "" if RBT is None else "\n".join([
               f"| 40 m 광선 | 경로 중앙 | 경로 평균 | 빈 자세 "
               f"(자세 {RBT['_meta']['n_poses']} 개 중) |", "|---|---|---|---|"] + [
               f"| {k} | {v['paths_median']:.0f} | {v['paths_mean']:.2f} | {v['zero_frac']:.1%} |"
               for k, v in RBT["ladder"].items()]), "",
           "" if RBT is None else
           f"⭐ **판정 — {RBT['_meta']['verdict_ko']}** 규칙값"
           f"({RBT['_meta']['rule_value_spp']/1e6:.0f}M)의 절반도 안 되는 지점에서 이미 "
           "빈 자세가 사라진다.", "",
           "" if RBT is None else
           "⭐ **두 판이 서로 맞는다.** 사다리는 자세 "
           + f"{RBT['_meta']['n_poses']} 개 판이고 위 스윕은 자세 {RGM['n']} 개 판이다. 같은 "
           + f"{next(iter(RBT['ladder'].values()))['spp']/1e6:.0f}M 발에서 빈 자세가 "
           + f"{next(iter(RBT['ladder'].values()))['zero_frac']:.1%} ↔ "
           + f"{RGR['R40']['paths_zero_frac']:.1%} 로 만난다.", "",
           "⭐ **그러면 무엇이 남는가 — 비용이다.** 거리가 두 배면 광선을 네 배 부어야 같은 경로 "
           "수를 얻는다. 40 m 규칙값이 "
           + ("178M" if RBT is None else f"{RBT['_meta']['rule_value_spp']/1e6:.0f}M")
           + " 이면 100 m 에서는 그 "
           + (f"{(100/40)**2:.1f}" if RBT is None else
              f"{(100/RBT['_meta']['range_m'])**2:.1f}")
           + " 배가 필요하다. 그 규칙은 **광선 수**의 규칙이므로, 비용은 따로 잰다.", "",
           "⭐ **비용을 두 팔에서 실제로 쟀다** — 아래는 자세당 벽시계 초다. 세 원장이 같은 판이라 "
           "바로 견줄 수 있다(" + _cost_setup + "). 그림 f9 (c) 가 이 표를 그린다.", "",
           "| 어느 팔 | 광선 예산 | 3 m | 15 m | 40 m | 원장 |",
           "|---|---|---|---|---|---|",
           _cost_rows, "",
           "⭐ **정본 서술** — 가까운 거리에서 최소 예산이면 PathSolver 가 싸고, 멀어지거나 예산을 "
           f"올리면 우리 커널이 싸다. 40 m 에서 광선을 {_r_rays} 배 올리면 자세당 초가 "
           f"{_r_budget} 배로 뛴다 — 자세 {_big_poses}를 쌓으면 한 판이 {_big_hours}이다. "
           f"우리 팔은 3 → 40 m 를 {_our_span} 폭 안에서 돈다.", "",
           "⚠ **거리축을 다시 푼 팔을 밝힌다.** 이 절의 스윕과 08_2 의 거리 표에서 세 거리를 다시 "
           "푼 광선 팔은 **PathSolver 하나**다 — `report07_three_engine_ranges.json` 의 "
           "`_meta.grid_note_ko` 가 sbr·po 열을 3 m 원장에서 그대로 옮긴다고 적는다. 우리 팔의 "
           "거리 비용은 `deck_ours_by_range.json` 이 따로 잰 값이고, 위 표 셋째 행이 그것이다.", "",
           "⭐ **무늬 쪽은 구조로 선다.** 우리 SBR+PO 는 광선 격자를 **표적에 앵커**(λ/12 간격)한 "
           "평면파 조명이라 격자의 크기와 칸수를 표적이 정한다. 원거리장 경계"
           f"({FARFIELD_M:.2f} m · D = 수평 최대치수 · 3D 대각으로 잡으면 {FARFIELD_3D_M:.1f} m · "
           "출처 `report15_probe.json`) 밖에서는 무늬가 거리에 **불변**이고 수신 레벨만 1/R² 로 "
           f"내려간다. ⚠ 같은 2D²/λ 를 이 스윕 원장은 D 를 조금 달리 잡아 "
           f"{RGM['farfield_boundary_m']:.2f} m 로 적는다 — 이 편은 앞의 한 값으로 쓴다.", "",
           "⭐ 그러므로 원거리 마이크로도플러에서 팔을 고르는 잣대는 **예산**이다 — 40 m 규칙 "
           f"예산에서 PathSolver 는 자세당 {_sc(_ps[2])} 로 우리 팔({_sc(_our[2])}) 아래에 "
           f"있고, 같은 거리에서 예산을 {_r_rays} 배로 올리면 {_sc(_big, '{:.2f} s')} 로 우리 "
           f"팔의 {_r_ours40} 배가 된다."),

        md("## 같은 채널에 5G 파형을 실제로 태우면", "",
           "**시나리오** — 채널은 **B 팔**(우리 SBR+PO · `rcs_sbr.sbr_field`)이 낸 08_3 의 "
           "2 초 호버링 h(t) 이고, 이 절이 쓰는 열은 그 원장의 "
           "**얼기 전 판**이다 — `outputs/prefreeze/report07_hover_long.npz::E` 와 바이트 "
           f"동일하다(5G 원장 {WM['generated'][:16]} · 채널 원장의 현재 판은 "
           f"{HOV.get('regenerated', HOV['generated'])[:16]} 의 얼린 격자다). "
           "**이 절이 쓰는 팔은 B 하나다.** 바꾼 것은 "
           f"파형뿐이다: 5G NR 형 OFDM — SCS {WM['scs_hz']/1e3:.0f} kHz(n78) · "
           f"유효 부반송파 {WM['n_sc']:,}개 · 심볼마다 무작위 QPSK · "
           f"심볼율 {WM['sym_rate_hz']/1e3:.0f}k sym/s. 수신은 기지 심볼 나눗셈으로 심볼마다 "
           "채널 ĥ 을 꺼낸다. **네 갈래**는 «채널을 얼마나 자주 읽나»(반복률)만 다르다 — "
           "여기서 «갈래» 는 표본율이고, 8 권의 다른 곳이 쓰는 «팔»(엔진)과 다른 축이다.", "",
           embed("report07_f10"), "",
           f"| 갈래 | 표본율 | 나이퀴스트 | 날개끝 ±{WM['f_tip_hz']:.0f} Hz | "
           f"플래시 {WM['f_flash_hz']:.0f} Hz |",
           "|---|---|---|---|---|",
           "\n".join(
               f"| {WA[k]['label']} | {WA[k]['fs_hz']:g} Hz | ±{WA[k]['nyquist_hz']:g} Hz | "
               f"{'⚠접힘' if WA[k]['ftip_folds'] else '보임'} | "
               f"{'⚠접힘' if WA[k]['fflash_folds'] else '보임'} |"
               for k in ("cw_5k", "nr_full_28k", "nr_crs_1k", "nr_ssb_50")),
           "",
           "⭐ 이것이 **5G 이중고**의 그림판이다 — 패시브가 기댈 상시 신호 기준으로, LTE CRS 급 "
           f"{WA['nr_crs_1k']['fs_hz']:.0f} Hz 는 날개끝이 나이퀴스트 "
           f"{WA['nr_crs_1k']['nyquist_hz']:.0f} Hz 안으로 **접혀** 들어오고, 5G SSB 급 "
           f"{WA['nr_ssb_50']['fs_hz']:.0f} Hz 는 **플래시선마저** 접힌다. 관측 창이 "
           f"±{WA['nr_ssb_50']['nyquist_hz']:.0f} Hz, 속도로는 "
           f"±{WA['nr_ssb_50']['nyquist_hz']*LAM5G/2:.2f} m/s 뿐인데 날개끝은 초당 "
           f"{WM['f_tip_hz']*LAM5G/2:.1f} m 로 움직인다(모노스태틱 환산 v = f·λ/2, "
           f"λ = {LAM5G*1e3:.1f} mm). ⚠ 이 두 칸 가운데 CRS 쪽은 **라벨 축**에서 선다 — "
           "아래 ⏳ 가 실제 축의 값을 적는다.", "",
           "⭐ **네 패널은 축이 완전히 같다.** 그래서 낮은 반복률의 대가가 **빈 자리**로 보인다 — "
           "회색으로 덮은 영역은 «조용함» 이 아니라 **그 표본율로는 측정 자체가 불가능한 영역**이다.", "",
           f"⚠ **이 수치가 무엇을 재는지 정확히 적는다.** «풀캡처 ≡ CW» 의 "
           f"{WM['full_capture_max_rel_err']:.1e} 는 **OFDM 수신 사슬이 채널을 정확히 되돌려주는가**"
           "를 잰 것이다. 평탄-채널 근사 아래에서 그 사슬은 항등식이므로 이 값이 작은 것은 "
           "**구현이 맞다는 확인**이지, 5G 와 CW 가 같은 물리를 본다는 **독립 검증이 아니다**. "
           "⭐이 그림의 진짜 내용은 오른쪽 두 갈래, 즉 **반복률**에 있다.", "",
           "⚠ 정직 한계 둘 — 채널열을 심볼율로 다상 보간했고(대역제한 가드 "
           f"{WM['bandlimit_guard_energy']:.1e}), 심볼 안에서 채널이 도는 ICI 를 1차 근사로 재면 "
           f"바닥이 {WM['ici_floor_db_first_order']:.1f} dB 인데 채널 모형에는 넣지 않았다.", "",
           "⏳ **이 절의 원장은 재계산 대기다 — 표의 수치를 지금 인용하지 마라.** 채널 원장"
           f"(`report07_hover_long`)의 PRF 는 {WA['cw_5k']['fs_hz']:.0f} Hz 인데 파형 스크립트의 "
           "보간 비는 «5 kHz → 심볼율» 에 고정돼 있어, 위 표의 **표본율 라벨과 실제 시간축이 "
           "어긋난다**(네 갈래의 나이퀴스트도 그 라벨에서 나온 값이다). 이 절의 논지 — "
           "«쓸 수 있는 것을 정하는 것은 파형이 아니라 반복률이다» — 는 그대로지만, 숫자는 "
           "`benchmark/report07_5g_waveform.py` 의 보간 비를 채널 PRF 에서 읽게 고쳐 다시 "
           "계산한 뒤에 인용한다.", "",
           "⏳ **그 어긋남의 크기를 같은 원장 안에서 잰다.** 갈래마다 표본 수를 기록 길이 "
           f"{_T5:.1f} 초로 나누면 실제 표본율이 나온다 — 라벨의 **{_mult5:.2f} 배**다"
           f"(풀캡처 {_fs_true['nr_full_28k']/1e3:.1f}k Hz · CRS 급 "
           f"{_fs_true['nr_crs_1k']:.0f} Hz · SSB 급 {_fs_true['nr_ssb_50']:.0f} Hz). "
           f"그 축에서 CRS 급의 나이퀴스트는 {_nyq_crs:.0f} Hz 라 날개끝 "
           f"{WM['f_tip_hz']:.0f} Hz 가 **보이고**, 위 표의 그 칸이 뒤집힌다. SSB 급은 실제 "
           f"축에서도 나이퀴스트가 {_nyq_ssb:.1f} Hz 뿐이라 날개끝과 플래시 "
           f"{WM['f_flash_hz']:.0f} Hz 가 둘 다 접힌다. ⇒ **지금 서는 것은 SSB 쪽 접힘이고, "
           "CRS 쪽 접힘은 라벨 축에서만 선다.**"),

        md("## 부록 — 그림별 데이터 이력", "",
           "그림마다 딛고 선 원장과 그 시점이 다르다. ⭐**원장의 PRF 가 다르면 시간 분해능도 "
           "다르다** — 그래서 그림마다 선명도가 갈릴 수 있다. 마지막 칸은 그 원장의 우리 팔이 "
           "어떤 **광선 격자**로 풀렸는가다(**절 [«광선 격자를 어디에 매나»](08_2_engines.ipynb)**).", "",
           "| 그림 | 편 | 원장 | 생성 | PRF | 광선 격자 |", "|---|---|---|---|---|---|",
           "| 애니메이션 · f0 | 08_1 | 렌더 — 애니메이션 계수는 `report07_anim.json` | "
           + ((ANIM["_meta"]["generated"][:10]) if ANIM else "2026-08-10")
           + " | — | 렌더(Mitsuba path tracer) · 팔 무관 |",
           "| f0c | 08_1 | 렌더 실행 — 그림 속 **경로 수는 원장 없음** | 2026-08-10 | — | "
           "**S** 팔(경로해 · 광선 격자 무관) |",
           f"| f12 · f8 | 08_2 | `report07_three_engines.json` | "
           f"{_stamp(TM)} | {TM['prf_hz']:.0f} Hz | {_PLATE_TRI} |",
           f"| f2 | 08_2 | `report15_verdict.json` | {VERD['meta']['stamp'][:10]} | — | "
           "광선 안 씀(순수 PO ↔ Sionna) |",
           f"| f1 · f4 | 08_3 | `report15b_microdoppler.json` | "
           f"{_stamp(MDB['_meta'])} | {PH['prf']:.0f} Hz | {_PLATE_R15B} |",
           "| f3 | 08_3 | 밴드별 변조 깊이(그림 빌더에 박힌 2026-08-07 실측) | 2026-08-07 | — | "
           "⚠자세마다 다시 정의 |",
           f"| f7 | 08_3 | `report07_hover_long.json` | {_stamp(HOV)} | "
           f"{HOV['prf_hz']:.0f} Hz | {_PLATE_HOV} |",
           ("" if HOD is None else
            f"| f11 | 08_3 | `report07_hover_long_outdoor.json` | {_stamp(HOD)} | "
            f"{HOD['prf_hz']:.0f} Hz | {_PLATE_HOD} |"),
           ("" if not _HAS_F13 else
            "| f13 | 08_3 | `rotor_log_traces.json` (공개 비행로그) | 2026-08-10 | 로그 원본 | "
            "— (측정 로그) |"),
           "| f9 (a)(b) | 08_4 | `report07_ray_budget_test.json` + "
           f"`report07_sionna_ranges.json` | {'' if RBT is None else RBT['_meta']['generated'][:16]}"
           f" · {RGM['generated'][:16]} | {RGM['prf_hz']:.0f} Hz | **S** 팔(광선 격자 무관) |",
           "| f9 (c) | 08_4 | `report07_three_engine_ranges.json` + "
           "`report07_range40_raybudget.json` + `deck_ours_by_range.json` | "
           + (_TER["_meta"]["generated"][:16] if _TER else "—")
           + " · 뒤의 둘은 시각 미기록 | "
           + (f"{_DK['_meta']['prf_hz']:.0f} Hz" if _DK else "—")
           + " | **S** 팔 실측 3 점 + **B** 팔 실측 3 점(얼린 격자) |",
           f"| f10 | 08_4 | `report07_5g_waveform.json` | {WM['generated'][:16]} | 갈래마다 다름 | "
           "⚠얼기 전 판 — 채널열이 `prefreeze/report07_hover_long` |",
           "",
           "⚠ **f3 과 f10 이 옛 판 위에 있다.** f3 의 밴드별 변조 깊이는 그림 빌더 안에 "
           "2026-08-07 실측값으로 박혀 있고, 그 실측은 자세마다 격자를 다시 정의하는 판에서 난 "
           "값이다 — 그 그림의 논지(«블레이드는 강한데 동체가 덮는다» · 프롭 채널 ↔ 전체 드론)는 "
           "두 채널을 **같은 판**에서 비교한 것이라 서지만, **깊이의 절대 dB 는 인용하지 마라**. "
           "f10 의 채널열은 얼기 전 판이라(위 표) **얼린 판을 쓰는 08_3 의 f7 과 다른 열**이다 — "
           "표본율·나이퀴스트의 논지는 서지만, 이 절의 dB 값은 08_3 과 나란히 두지 마라.", "",
           "**표시 규약**(8-1~8-4 의 맵 공통 · 8-5 도 같은 규약이다) — 조각 = 블레이드 **0.45 주기**"
           "(`md_mapstyle.auto_periods` 가 고르는 값 · 조각이 24 표본 아래로 내려가면 0.6 으로 "
           "물러난다) · hop 2 · 제로패딩 8 배 · Hann · gouraud · jet · 색역 0~−40 dB · "
           "0 도플러 안 지움 · 도플러축 ±1.9·f_tip. 정본은 `src/md_mapstyle.py` 다. "
           "⚠ 8-5(바이스태틱)만 도플러축을 ±2.1·f_tip 으로 넓혀 자른다 — 그 편의 축척이 "
           "β 마다 달라서다.", "",
           "⚠ 조각 길이 0.45 는 **정의가 하나뿐인 양**으로만 인용한다 — 조각 "
           f"{round(0.45*TM['prf_hz']/TM['f_flash_hz'])} 표본 · "
           f"Δt {0.45/TM['f_flash_hz']*1e3:.2f} ms · Δf {TM['f_flash_hz']/0.45:.0f} Hz. "
           "«플래시 대비가 최대» 라는 표는 독립 재구현에서 재현되지 않아 내렸다.", "",
           "**재현**", "", "```bash",
           "# 광선 격자 — 기본은 얼림. 0 이면 옛 판(자세마다 다시 정의)이 그대로 나온다.",
           "export SIONNA2_FREEZE_GRID=1",
           "# 원장 재계산(GPU)",
           "PYTHONPATH=src python benchmark/report07_three_engine_maps.py --n 4096   # SIONNA2_MD_PRF_MULT=16",
           "PYTHONPATH=src python benchmark/report07_hover_long.py --sec 2.0",
           "PYTHONPATH=src python benchmark/report15b_microdoppler_recompute.py",
           "PYTHONPATH=src python benchmark/report07_ray_budget_test.py",
           "# f9 (c) 의 자세당 초 — 두 팔을 같은 자세 수로 잰 원장 셋",
           "PYTHONPATH=src python benchmark/report07_three_engine_ranges.py   # S 팔 3 · 15 m",
           "PYTHONPATH=src python benchmark/report07_range40.py               # S 팔 40 m 샤드",
           "PYTHONPATH=src python benchmark/deck_ours_by_range.py --merge     # B 팔 3 · 15 · 40 m",
           "# 파생 원장(계산 없음 — 디스크에서 다시 잰다)",
           "PYTHONPATH=src python benchmark/build_raybudget_40m_fig.py        # 40 m 예산 원장",
           "PYTHONPATH=src python benchmark/ledger_ptp_robust.py",
           "PYTHONPATH=src python benchmark/ledger_outofband_power.py",
           "# 그림",
           "PYTHONPATH=src python benchmark/build_three_engine_fig.py        # f5 + 코사인 판정",
           "PYTHONPATH=src python benchmark/build_three_engine_ranges_fig.py  # f12",
           "PYTHONPATH=src python benchmark/build_flash_zoom.py               # f8",
           "PYTHONPATH=src python benchmark/build_report07_figs.py            # f1~f4",
           "PYTHONPATH=src python benchmark/build_hover_fig.py                # f7",
           "PYTHONPATH=src python benchmark/build_hover_compare_fig.py        # f11",
           "PYTHONPATH=src python benchmark/build_rotor_log_fig.py            # f13",
           "PYTHONPATH=src python benchmark/build_range_sweep_fig.py          # f9",
           "PYTHONPATH=src python benchmark/build_5g_fig.py                   # f10",
           "# 이 빌더가 내는 네 편(08_1~08_4) — 08_5 는 src/make_report07b_bistatic.py",
           "PYTHONPATH=src python src/make_report08_microdoppler.py",
           "```"),

        md("## 출처", "",
           "이 편의 숫자가 온 자리다. «팔» 칸은 그 값을 낸 계산 팔이다 — **S** = "
           + ARM_SIONNA + " · **B** = " + ARM_SBR + " · **P** = " + ARM_PO
           + " · **해** = 닫힌 식·규약. 팔 이름의 정본은 `src/md_mapstyle.py` 다.", "",
           "| 원장 | 키 | 팔 | 이 편의 어디에 |", "|---|---|---|---|",
           _src_rows_08_4(), "",
           "**원장 없음 두 자리** — 부록 표의 f0c 경로 수(렌더가 stdout 으로만 적는다) · "
           "얼린 판 위의 5G 채널(§2 의 열은 얼기 전 판이다). 둘 다 본문에 «원장 없음»·«얼기 전 "
           "판» 으로 적었고 그 자리의 수치는 인용에서 뺐다.", "",
           "⚠ **두 절은 다른 축을 잰다** — §1 은 광선 비용(**S**·**B** 두 팔의 자세당 벽시계 "
           "초 · 같은 자세 수), §2 는 조명원 반복률(**B** 팔 채널 하나)이다. 두 절의 절대 "
           "수치를 섞어 읽으면 어긋난다."),
    ]
    write("08_4", "sampling", c)


if __name__ == "__main__":
    print("── 8 권(마이크로도플러) 네 편 빌드 ──")
    build_08_1()
    build_08_2()
    build_08_3()
    build_08_4()
    print("✅ reports/08_1~08_4")
