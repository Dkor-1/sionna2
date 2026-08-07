# -*- coding: utf-8 -*-
"""
build_part11_measurement.py — 부 11 「실측 설계」 → reports/67~77_*.ipynb
==========================================================================================
한 편 = 중심 메시지 하나. 옛 `report06_measurement.ipynb` 한 편(26 셀)을 열한 편으로 쪼갠다.

    67 hardware            X410 의 12-bit ADC 가 직접파 제거의 천장이다
    68 sigma-checklist     교정된 절대 σ 를 만드는 조건 여섯 항목
    69 site-geometry       세션 거리 하나가 두 기체 세 밴드를 덮는다
    70 calibration-sphere  구가 σ 를 절대량으로 만든다
    71 subband             표적을 한 거리빈에 넣는 최대 대역
    72 attitude            각도표본을 λ/4D 로 잡는다
    73 three-layers        σ(f) 레인지 · 파형축 · 비행검출
    74 sim-vs-meas         캠페인이 결판내는 양은 순위다
    75 decision-matrix     어느 측정이 어느 주장을 결판내나
    76 session-drift       기울기 판정의 문턱은 세션간 진폭 재현성이다
    77 size-law-differential  두 기체를 함께 재면 크기전이 법칙이 부호로 갈린다   ⭐신설

⭐ 이 빌더는 **읽기만** 한다 — `outputs/report06_derived.json` 과 그림 6장은 옛 빌더가 만든
   것을 그대로 인용한다. 근거 JSON 도 그림도 다시 만들지 않는다.

옛 편의 논문 부록(셀 23)과 재현 코드(셀 24)는 리포트 밖으로 나간다 —
    docs/paper/06_measurement.md · docs/repro/part11_measurement.md
그 두 파일은 `src/extract_part11_docs.py` 가 만든다.

실행
    cd /home/yunjung/workspace/sionna2
    PYTHONPATH=src ~/.venvs/py312/bin/python src/build_part11_measurement.py

⚠ GPU 도 Sionna 도 필요 없다 — JSON 을 읽어 노트북을 조립할 뿐이다.
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

from report_style import (ContractError, build_notebook, caption,   # noqa: E402
                          from_json, header, md, next_steps, table, table_from)

# --------------------------------------------------------------------------- #
#  앵커 해결기 — 번호는 실행 계획이 정본이다
# --------------------------------------------------------------------------- #
_PLAN = os.path.join(_ROOT, "outputs", "restruct_exec_plan.json")

#: 계획 밖에서 이 묶음이 새로 만든 편. 옛 셀 22 가 두 메시지를 담고 있어 쪼갰다.
#: ⚠ 앵커 이름은 다른 갈래가 먼저 쓴 `size-law-differential` 을 따른다 —
#:   그쪽 색인 샤드가 이미 그 이름으로 서 있어서 이름을 갈면 링크가 끊긴다.
EXTRA = {
    "size-law-differential": ("77", "두 기체를 함께 재면 크기전이 법칙이 "
                                    "차등신호의 부호 하나로 갈린다"),
}


def _registry() -> dict:
    with open(_PLAN, encoding="utf-8") as f:
        plan = json.load(f)
    reg = {r["anchor"]: (str(r["no"]), r["title_ko"]) for r in plan["reports"]}
    reg.update(EXTRA)
    return reg


REG = _registry()


def ref(anchor: str, short: str | None = None) -> str:
    if anchor not in REG:
        raise ContractError(f"모르는 앵커: {anchor!r} — 실행 계획에 없다")
    no, title = REG[anchor]
    return f"[편 {no} «{short or title}»]({no}_{anchor}.ipynb)"


# --------------------------------------------------------------------------- #
#  근거 JSON — 전부 읽기 전용
# --------------------------------------------------------------------------- #
D = from_json("outputs/report06_derived.json")     # 설계 파생값 (옛 빌더가 만든 것)
M = from_json("outputs/report06_measurement.json")  # 하드웨어·밴드·원거리장 원본
A = from_json("outputs/sigma_anchor.json")          # 앵커 원장
V = from_json("outputs/verify_cfar.json")           # CFAR 교정 몬테카를로
P3 = from_json("outputs/p3_validation.json")        # 눈감기 대조 사전값
PV2 = from_json("outputs/p3_validation_v2.json")    # 밴드정합 앵커 · v2 메쉬
PW = from_json("outputs/ptd_wiring.json")           # PTD 배선 상태
MFX = from_json("outputs/meshfix_applied.json")     # 형상 정정 — 설계값 신선도
S2A = from_json("outputs/s2r_attack.json")          # sim-to-real 설계 적대검증
from_json("outputs/lowfreq_attack.json")            # 결정표가 경로로 가리킨다 — 존재 검사
from_json("outputs/measurement_layers.json")        # 3층 설계 원본
from_json("outputs/meshfix_attack.json")            # 형상 정정 파급

OUT = os.path.join(_ROOT, "reports")
FIG = "../outputs/figures"

REPRO = dict(
    cmd=["PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/plan_measurement.py",
         "PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python -c "
         "\"import sigma_anchor as S; S.write_measurement_plan()\"",
         "PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python src/make_report06_measurement.py"],
    out=["outputs/report06_measurement.json", "outputs/measurement_plan.json",
         "outputs/report06_derived.json"],
    runtime="약 10 초 (CPU)",
    note="산문판 설계서는 `docs/MEASUREMENT_PLAN.md` 이고, 그 안의 수치표는 "
         "`src/sigma_anchor.py:939` 가 자동 주입한다")


def _fig(no: int, stem: str, question: str) -> list[str]:
    return [f"![{stem}]({FIG}/{stem}.png)", "", caption(no, question)]


# =========================================================================== #
#  편 67 — 하드웨어
# =========================================================================== #
def blocks_67() -> list:
    return [
        header(
            num=67,
            title="X410 의 12-bit ADC 동적범위가 직접파 제거의 천장이다",
            did="보유 장비 USRP X410 의 공식 사양을 한 곳에서 읽어 세션이 무엇에 묶이는지를 "
                "항목마다 수치로 고정했다.",
            results=[
                f"12-bit ADC(아날로그 신호를 숫자로 바꾸는 변환기)의 동적범위는 "
                f"{M.num('hw.dynamic_range_db', fmt='{:.2f}', unit='dB')} 이고, 이 값이 "
                f"직접파 제거의 천장이다.",

                f"세 파형 중 여유가 가장 좁은 것은 `{M.get('adc.worst_waveform')}` 이고 "
                f"{M.num('adc.headroom_db_min', fmt='{:.1f}', unit='dB')} 다 — 점유대역이 좁아 "
                f"기준채널 이득이 높다.",

                f"세션은 기준 1 + 감시 1 = "
                f"{D.num('layers.n_channels', fmt='{:.0f}', unit='채널')} 을 같은 클럭에서 "
                f"쓴다. 사양의 4 RX 는 각도축을 여는 예비다.",

                f"채널당 순시대역은 "
                f"{M.num('hw.max_bw_mhz', fmt='{:.0f}', unit='MHz')} 이고 주파수 범위는 "
                f"{D.num('hw_span.f_lo_mhz', fmt='{:.0f}', unit='MHz')} ~ "
                f"{D.num('hw_span.f_hi_ghz', fmt='{:.1f}', unit='GHz')} 로 세 밴드를 전부 덮는다.",

                f"이 DNR 은 자유공간 시뮬 기하에서 나온 값이다 — 야외에서 송수신을 가깝게 놓으면 "
                f"DNR 이 올라가 여유가 그만큼 줄어든다.",
            ],
            method=[
                ("사양 출처",
                 "ni.com / ettus.com 공식 스펙 한 곳에서 인용 — `src/experiment_x410.py:61`"),
                ("기하 배치",
                 "`src/experiment_x410.py:100` 한 곳에 있다"),
                ("양자화 잔차",
                 "직접파를 양자화한 뒤 남는 잔차를 `src/experiment_x410.py:83` 의 "
                 "`adc_quantize()` 가 모델에 넣는다"),
                ("DNR 의 출처",
                 "자유공간 시뮬 기하에서 계산한 값이다 — 야외 실측이 이 값을 대체한다"),
            ],
            repro=REPRO,
        ),

        md("## X410 한 대가 기준과 감시를 동시에 든다", "",
           "세션은 **RX0 = 기준(직접파)** 과 **RX1 = 감시** 두 채널을 **같은 클럭**에서 쓴다"
           "⟨outputs/measurement_layers.json : validation_three_points.channels⟩ — 사양의 4 RX 는 "
           "각도축을 여는 예비다.", "",
           "사양은 `src/experiment_x410.py:61`, 기하 배치는 `src/experiment_x410.py:100` "
           "한 곳에 있다."),

        md("## 사양이 무엇을 제약하나", "",
           table(["항목", "값", "무엇을 제약하나"], [
               ["TX / RX 채널",
                M.num("hw.n_tx", fmt="{:.0f}") + " / " + M.num("hw.n_rx", fmt="{:.0f}"),
                "세션은 기준 1 + 감시 1 을 공통 클럭에서 쓴다"],
               ["채널당 순시대역", M.num("hw.max_bw_mhz", fmt="{:.0f}", unit="MHz"),
                "거리분해능과 점표적 서브밴드"],
               ["주파수 범위",
                D.num("hw_span.f_lo_mhz", fmt="{:.0f}", unit="MHz") + " ~ "
                + D.num("hw_span.f_hi_ghz", fmt="{:.1f}", unit="GHz"), "세 밴드 전부 커버"],
               ["ADC 동적범위", M.num("hw.dynamic_range_db", fmt="{:.2f}", unit="dB"),
                "직접파 제거의 천장"],
               ["감시배열 AoA 빔폭", M.num("hw.aoa_beamwidth_deg", fmt="{:.1f}", unit="°"),
                "네 RX 를 전부 감시로 쓸 때 열리는 각도축"],
               ["최대대역 바이스태틱 ΔR",
                M.num("hw.range_res_bistatic_m_at_max_bw", fmt="{:.3f}", unit="m"),
                "표적이 퍼지는 폭"],
           ]), "",
           f"원사양 출처는 `{M.get('hw.source')}` 한 곳이다."),

        md("## 여유가 가장 좁은 파형", "",
           *_fig(1, "report06_adc_headroom",
                 "12-bit ADC 는 직접파 대 잡음비 위에 얼마의 여유를 남기는가?"),
           f"여유가 가장 좁은 파형은 `{M.get('adc.worst_waveform')}` 이고 "
           f"{M.num('adc.headroom_db_min', fmt='{:.1f}', unit='dB')} 다 — 점유대역이 좁아 "
           f"기준채널 이득이 높다.", "",
           "이 DNR 은 자유공간 시뮬 기하에서 나온 값이다⟨outputs/report06_measurement.json : "
           "adc.dnr_source⟩. 야외에서 송수신을 가깝게 놓으면 DNR 이 올라가 여유가 그만큼 줄어든다."),

        next_steps([
            ("직접파를 실제로 받아 ECA 잔차를 잰다",
             f"여유 {M.num('adc.headroom_db_min', fmt='{:.1f}', unit='dB')} 가 야외에 얼마나 "
             f"남는지가 측정값으로 확정된다",
             ref("decision-matrix", "결정표") + " 의 사슬 확인 행"),
            ("네 RX 를 전부 감시로 두는 배치를 따로 설계한다",
             "각도축이 열리고 그 각도축이 검출 이후의 확장축이 된다",
             "`src/experiment_x410.py:100` 확장"),
        ]),
    ]


# =========================================================================== #
#  편 68 — 체크리스트 여섯 항목
# =========================================================================== #
def blocks_68() -> list:
    return [
        header(
            num=68,
            title="교정된 절대 σ 를 만드는 조건은 여섯 항목이 전부다",
            did="교정된 절대 σ 를 만드는 조건을 실행 항목 여섯 개로 적고 항목마다 만족해야 할 "
                "수치 임계를 붙였다.",
            results=[
                f"여섯 항목은 기준체 · 배경차감 · 자세통제 · 안테나 패턴교정 · 원거리장 · "
                f"점표적 대역이다.",

                f"기준체 여유는 "
                f"{D.num('calibration_margin_min_db', fmt='{:+.2f}', unit='dB')} 이상, "
                f"세션 거리는 "
                f"{D.num('farfield_adopted.R_ff_max_m', fmt='{:.2f}', unit='m')} 이상이다.",

                f"자세 표본 간격은 "
                f"{D.num('aspect_finest_deg', fmt='{:.2f}', unit='°')} 이하, 점표적 서브밴드는 "
                f"{D.num('point_target_max_bw_MHz', fmt='{:.0f}', unit='MHz')} 이하다.",

                f"배경 차감은 지면반사 경로차가 거리분해능보다 커야 성립하고, 기하 "
                f"{D.num('ground_bounce_sep_frac_200MHz', fmt='{:.0%}')} 가 그 조건을 만족한다.",

                f"순위 판정은 이 중 앞의 셋만 요구한다 — 여섯을 다 채운 세션이 다음 라운드의 "
                f"더 센 주장(절대 σ)을 만든다.",
            ],
            method=[
                ("여섯 항목의 출처",
                 "산문판 조건은 `docs/MEASUREMENT_PLAN.md` 에 있고, 수치 임계는 "
                 "`outputs/report06_derived.json` 한 곳에서 계산된다"),
                ("임계의 성격",
                 "왼쪽은 세션에서 **하는 일**, 오른쪽은 그 일이 만족해야 하는 **수치 임계**다"),
                ("무엇이 순위 판정에 필요한가",
                 "앞의 셋(기준체 · 배경차감 · 자세통제)만 있으면 파형 순위는 결판난다"),
            ],
            repro=REPRO,
        ),

        md("## 교정된 절대 σ 로 가는 세션 — 실행 체크리스트", "",
           "이 여섯 항목이 **교정된 절대 σ** 를 만드는 조건 전부다. 순위 판정은 이 중 앞의 셋만 "
           "요구하고, 여섯을 다 채운 세션이 다음 라운드의 더 센 주장을 만든다.", "",
           "왼쪽은 세션에서 **하는 일**, 오른쪽은 그 일이 만족해야 하는 **수치 임계**다."),

        md("## 여섯 항목", "",
           table(["실행 항목", "세션에서 하는 일", "수치 임계"], [
               ["교정 기준체",
                "정밀 PEC 구를 세션 **시작과 끝**에 표적과 같은 지지대·같은 위치에서 잰다",
                "예상 σ 대비 여유 ≥ "
                + D.num("calibration_margin_min_db", fmt="{:+.2f}", unit="dB")],
               ["배경 차감",
                "지지대를 세운 채 표적만 치우고 배경 응답을 **복소수로** 뺀다",
                "지면반사 경로차 > ΔR — 기하 "
                + D.num("ground_bounce_sep_frac_200MHz", fmt="{:.0%}") + " 가 분리"],
               ["자세 통제",
                "엔코더 턴테이블로 방위를 돌리고 로터를 정지시켜 블레이드 방위를 기록한다",
                "Δφ ≤ " + D.num("aspect_finest_deg", fmt="{:.2f}", unit="°")],
               ["안테나 패턴 교정",
                "교정구를 표적과 같은 자리·같은 높이에 놓아 패턴과 체인 이득을 비율로 소거한다",
                "표적/교정구 위치 동일"],
               ["원거리장 거리",
                "2D²/λ 이상에서 잰다 — 교정구는 같은 자리에 놓으면 자동 만족한다",
                "R ≥ " + D.num("farfield_adopted.R_ff_max_m", fmt="{:.2f}", unit="m")],
               ["점표적 서브밴드",
                M.num("hw.max_bw_mhz", fmt="{:.0f}", unit="MHz")
                + " 순시대역을 쪼개 서브밴드마다 σ 를 내고, 그 다발을 σ(f) 로 삼는다",
                "B ≤ " + D.num("point_target_max_bw_MHz", fmt="{:.0f}", unit="MHz")],
           ])),

        md("## 항목마다 자기 편이 있다", "",
           table(["실행 항목", "그 항목을 세우는 편"], [
               ["교정 기준체 · 안테나 패턴 교정", ref("calibration-sphere", "교정 기준체")],
               ["배경 차감 · 원거리장 거리", ref("site-geometry", "부지 기하")],
               ["자세 통제", ref("attitude", "자세 통제")],
               ["점표적 서브밴드", ref("subband", "점표적 서브밴드")],
               ["세션을 층으로 쌓는 법", ref("three-layers", "실측 3층")],
           ])),

        next_steps([
            ("기체 2종을 입고하고 이 여섯 항목대로 세션을 돌린다",
             "우리 기체의 절대 σ(f, φ) 가 외부 앵커 없이 자체 측정으로 선다",
             "`outputs/measured_sigma.json` → `src/sigma_anchor.py:255` 앵커 등록"),
            ("앞의 셋만 채운 짧은 세션을 먼저 돌린다",
             "파형 상대순위 판정이 절대 σ 보다 먼저 닫힌다",
             ref("sim-vs-meas", "캠페인이 결판내는 양")),
        ]),
    ]


# =========================================================================== #
#  편 69 — 부지 기하 (원거리장 + 지면반사)
# =========================================================================== #
def blocks_69() -> list:
    return [
        header(
            num=69,
            title="가장 보수적인 D 정의로도 세션 거리 하나가 두 기체 세 밴드를 덮는다",
            did="원거리장 2D²/λ 를 D 정의 세 가지로 계산하고, 야외 부지의 지면반사 유령이 "
                "거리게이팅으로 떨어지는 기하를 함께 셌다.",
            results=[
                f"채택한 D 는 가장 보수적인 정의다 — 회전 로터 디스크까지 포함한 외접상자의 "
                f"3D 대각이고, 요구거리 최대는 "
                f"{D.num('farfield_adopted.R_ff_max_m', fmt='{:.2f}', unit='m')} 다 "
                f"({D.get('farfield_adopted.airframe')} · {D.get('farfield_adopted.band')}).",

                f"같은 기체를 모터-모터 대각으로 재정의하면 요구거리가 "
                f"{D.num('farfield_adopted.spread_ratio_max', fmt='{:.2f}', unit='배')} "
                f"짧아진다 — 정의를 섞으면 거리가 그만큼 틀린다.",

                f"세션 거리는 그 최대값 하나로 잡는다. 한 거리가 기체 2종 × 3밴드를 전부 덮는다.",

                f"지면반사 유령은 경로차 2hH/R 이 서브밴드 거리분해능보다 클 때 떨어진다 — "
                f"{D.num('ground_bounce_n_geom', fmt='{:.0f}', unit='개')} 기하 중 "
                f"{D.num('ground_bounce_ref_bw_MHz', fmt='{:.0f}', unit='MHz')} 서브밴드에서 "
                f"분리되는 비율이 "
                f"{D.num('ground_bounce_sep_frac_200MHz', fmt='{:.0%}')} 다.",

                f"⚠ 이 D 는 Matrice 4E 메쉬의 외접상자에서 나오고, 그 형상은 "
                f"{MFX.num('_meta.date')} 에 공식 CAD 실측으로 정정됐다 — 표의 값은 "
                f"**정정 전** 메쉬 기준이다.",
            ],
            method=[
                ("원거리장 요구거리",
                 "메쉬 외접상자(회전 로터 디스크 포함)의 3D 대각 D 를 세 밴드 λ 에 넣어 "
                 "2D²/λ 로 계산 — `benchmark/plan_measurement.py`"),
                ("D 정의 세 가지",
                 "env(로터 디스크 포함 외접상자 3D 대각) · bbox(프로펠러 포함 수평 최대치수) · "
                 "diag(모터-모터, 앵커 문헌 관례). 채택은 가장 보수적인 env"),
                ("배경 차감",
                 "배경은 **지지대를 세운 채로** 재고 **복소수로** 뺀다"),
                ("지면반사",
                 "표적을 경유한 지면반사의 경로차 2hH/R 을 안테나 높이 h · 표적 높이 H · "
                 "지상거리 R 의 격자에서 계산해 서브밴드 거리분해능과 견줬다"),
            ],
            repro=REPRO,
        ),

        md("## 원거리장 — 2D²/λ 를 두 기체 × 세 밴드로", "",
           "채택한 D 는 가장 보수적인 정의다 — 회전 로터 디스크까지 포함한 외접상자의 3D 대각. "
           f"같은 기체를 모터-모터 대각으로 재정의하면 요구거리가 "
           f"{D.num('farfield_adopted.spread_ratio_max', fmt='{:.2f}')}배 짧아진다. "
           f"세 정의를 한 표에 나란히 실어 어느 값을 쓰는지 고정한다."),

        md("## 세 정의를 한 표에", "",
           D.table("farfield",
                   [("기체", "airframe"), ("밴드", "band"), ("λ", "lam_mm"),
                    ("D_env", "D_env_m"), ("**R_ff(env)**", "R_ff_env_m"),
                    ("R_ff(bbox)", "R_ff_bbox_m"), ("R_ff(모터대각)", "R_ff_diag_m")],
                   fmt={"lam_mm": "{:.0f} mm", "D_env_m": "{:.3f} m",
                        "R_ff_env_m": "{:.2f} m", "R_ff_bbox_m": "{:.2f} m",
                        "R_ff_diag_m": "{:.2f} m"})),

        md("## 세션 거리 하나로 전부 덮는다", "",
           *_fig(1, "report06_farfield",
                 "각 기체와 밴드에서 원거리장에 들어가려면 얼마나 멀어야 하는가?"),
           f"세션 거리는 최대값 "
           f"{D.num('farfield_adopted.R_ff_max_m', fmt='{:.2f}', unit='m')} 로 잡는다 — "
           f"그 한 거리가 두 기체 세 밴드를 전부 덮는다.", "",
           f"⚠ 이 표와 그림의 D 는 Matrice 4E 메쉬의 외접상자에서 나오고, 그 형상은 "
           f"{MFX.num('_meta.date')} 에 공식 CAD 실측으로 정정됐다"
           f"(⟨outputs/meshfix_applied.json : per_drone.matrice4e⟩). 로터 디스크를 포함한 "
           f"대각이라 변화 폭은 작게 잡히지만, 그 크기는 재계산이 정한다. 형상 정정 자체는 "
           + ref("mesh-build", "메쉬 세우기") + " 가 적는다."),

        md("## 배경 차감과 지면반사 — 야외 부지를 기하로 다룬다", "",
           "배경 S_BG 는 **지지대를 세운 채로** 재고 **복소수로** 뺀다.", "",
           "표적을 경유한 지면반사는 경로차 `2hH/R` 이 서브밴드 거리분해능보다 **클 때** "
           "레인지게이팅으로 떨어진다."),

        md("## 어떤 부지가 유령을 밀어내나", "",
           *_fig(2, "report06_ground_bounce",
                 "어떤 야외 기하가 지면반사 유령을 표적 거리빈 밖으로 밀어내는가?"),
           f"{D.num('ground_bounce_n_geom', fmt='{:.0f}')}개 기하 중 "
           f"{D.num('ground_bounce_ref_bw_MHz', fmt='{:.0f}', unit='MHz')} 서브밴드에서 "
           f"분리되는 비율은 {D.num('ground_bounce_sep_frac_200MHz', fmt='{:.0%}')} 다. "
           f"경로차 범위는 {D.num('ground_bounce_min_m', fmt='{:.2f}')} ~ "
           f"{D.num('ground_bounce_max_m', fmt='{:.2f}', unit='m')} 다.", "",
           "부지 선정은 그림 2 에서 분해능 선 위에 오는 (h, H, R) 조합으로 한다."),

        next_steps([
            ("β ≤ 45° 안에서 송수신 분리각별 기하를 같은 방식으로 계산한다",
             "바이스태틱 세션의 원거리장 거리와 게이팅 임계가 정해진다",
             "`benchmark/plan_measurement.py` 확장"),
            ("σ 사슬을 정정된 메쉬로 다시 돌린 뒤 D 를 다시 읽는다",
             "세션 거리가 현재 형상 위에서 확정된다",
             ref("mesh-build", "메쉬 세우기")),
            ("후보 부지에서 (h, H, R) 을 실측하고 경로차를 확인한다",
             "레인지게이팅으로 유령을 뗄 수 있는 부지가 확정된다",
             "이 편의 그림 2"),
        ]),
    ]


# =========================================================================== #
#  편 70 — 교정 기준체
# =========================================================================== #
def blocks_70() -> list:
    return [
        header(
            num=70,
            title="구가 σ 를 절대량으로 만들고, 반경 17.8 cm 를 고른다",
            did="정밀 PEC 구를 기준체로 두고 정확 Mie 급수로 기준값을 계산해 두 기체·세 밴드에서 "
                "여유가 남는 반경을 골랐다.",
            results=[
                f"채택 반경은 "
                f"{D.num('calibration_pick.radius_cm', fmt='{:.1f}', unit='cm')} 다 — "
                f"{D.get('calibration_pick.why')}",

                f"교정구는 두 기체·세 밴드에서 예상 σ 보다 최소 "
                f"{D.num('calibration_margin_min_db', fmt='{:+.2f}', unit='dB')} 밝다 — "
                f"같은 이득 설정으로 둘 다 잡히고, 그래야 두 응답의 비율이 그대로 σ 비율이 된다.",

                f"세션 **시작과 끝에 한 번씩** 잰다. 두 값의 차가 그 세션의 드리프트이고, "
                f"예산 {D.num('ranking_validation.drift_budget_db', fmt='{:.2f}', unit='dB')} "
                f"안에 든 세션만 자료로 쓴다.",

                f"⭐ 이 구가 캠페인에서 값어치가 가장 크다 — 지금 우리 PO 출력인 **절대 레벨을 "
                f"측정에 앵커한다**(생산 모드의 평균 레벨이동 "
                f"{D.num('modes.level_shift_production_abs_max_db', fmt='{:.2f}', unit='dB')}).",

                f"앵커 사슬이 선언한 σ_cal "
                f"{D.num('layers.cal_anchor_declared_dbsm', fmt='{:.2f}', unit='dBsm')} 대비 "
                f"우리 정확 Mie 교정은 밴드에 따라 "
                f"{D.num('layers.mie_shift_min_db', fmt='{:+.2f}')} ~ "
                f"{D.num('layers.mie_shift_max_db', fmt='{:+.2f}', unit='dB')} 위로 뜬다.",
            ],
            method=[
                ("기준체",
                 "정밀 PEC 구. 구는 방위무관이라 정렬 오차가 σ 에 안 들어간다"),
                ("기준값",
                 "정확 Mie 급수로 계산 — `benchmark/mie_pec_sphere.py:207`, `selfcheck()` 보유. "
                 "πr² 광학 점근과의 차이는 표의 `Mie−πr²` 열에 dB 로 있다"),
                ("여유 정의",
                 "교정구 정확 Mie σ 에서 기체 예상 σ(앵커 레벨 + L² 크기보정)를 뺀 값 [dB]"),
                ("드리프트",
                 "세션 시작과 끝에 같은 구를 재고 두 값의 차를 그 세션의 드리프트로 기록한다"),
                ("패턴 교정",
                 "교정구를 표적과 같은 자리·같은 높이에 놓아 안테나 패턴과 체인 이득을 "
                 "비율로 소거한다"),
            ],
            repro=REPRO,
        ),

        md("## σ 를 절대량으로 만드는 장치", "",
           "**정밀 PEC 구**를 쓴다. 구는 방위무관이라 정렬 오차가 σ 에 안 들어간다.", "",
           "기준값은 **정확 Mie** 로 쓴다 — πr² 광학 점근과의 차이는 아래 표의 `Mie−πr²` 열에 "
           "dB 로 있다. 단일 출처는 `benchmark/mie_pec_sphere.py:207` 이고 자체검증 "
           "`selfcheck()` 을 갖고 있다.", "",
           f"세션 **시작과 끝에 한 번씩** 잰다. 두 값의 차가 그 세션의 드리프트 예산이고, "
           f"그 차가 목표 정확도 "
           f"{D.num('ranking_validation.drift_budget_db', fmt='{:.2f}', unit='dB')} 안에 "
           f"들어온 세션만 자료로 쓴다."),

        md("## 두 후보 구의 정확 Mie σ 와 여유", "",
           D.table("calibration",
                   [("구", "sphere"), ("밴드", "band"), ("ka", "ka"),
                    ("σ_Mie", "mie_dbsm"), ("Mie−πr²", "mie_minus_go_db"),
                    ("Matrice 4E 대비 여유", "margin_matrice4e_db"),
                    ("Mini 5 Pro 대비 여유", "margin_mini5pro_db")],
                   fmt={"ka": "{:.1f}", "mie_dbsm": "{:+.2f} dBsm",
                        "mie_minus_go_db": "{:+.2f} dB",
                        "margin_matrice4e_db": "{:+.2f} dB",
                        "margin_mini5pro_db": "{:+.2f} dB"})),

        md("## 어느 반경을 고르나", "",
           *_fig(1, "report06_calibration",
                 "어느 반경의 교정구가 세 밴드 모두에서 기체 예상 σ 위에 있는가?"),
           f"채택 반경은 {D.num('calibration_pick.radius_cm', fmt='{:.1f}', unit='cm')} 다 — "
           f"{D.get('calibration_pick.why')}", "",
           f"⚠ 이 여유가 견주는 «기체 예상 σ» 는 `rcs_anchor → sigma_anchor` 사슬에서 오고, "
           f"그 사슬은 {MFX.num('_meta.date')} 형상 정정 전 메쉬 위에 있다 — 반경 선택은 여유가 "
           f"{D.num('calibration_margin_min_db', fmt='{:+.2f}', unit='dB')} 라 그 정도 이동에는 "
           f"버틴다."),

        md("## 앵커와 사과-대-사과로 견주려면 규약차를 먼저 되돌린다", "",
           f"앵커 사슬은 같은 반경의 금속구를 σ_cal "
           f"{D.num('layers.cal_anchor_declared_dbsm', fmt='{:.2f}', unit='dBsm')} 로 "
           f"선언했다 — πr² 광학값 "
           f"{D.num('layers.cal_pir2_dbsm', fmt='{:.2f}', unit='dBsm')} 이다"
           f"⟨outputs/measurement_layers.json : calibration_convention_gap.anchor_quote⟩.", "",
           f"우리가 정확 Mie 로 교정하면 우리 σ 는 그 규약 대비 밴드에 따라 "
           f"{D.num('layers.mie_shift_min_db', fmt='{:+.2f}')} ~ "
           f"{D.num('layers.mie_shift_max_db', fmt='{:+.2f}', unit='dB')} 위로 뜬다 — "
           f"앵커와 견줄 때 이 항을 먼저 되돌린다."),

        md("## 이 구가 값어치가 가장 큰 이유 두 가지", "",
           "절대 레벨만 보면 모양을 안 닮은 구도 부피를 맞게 골라 넣으면 우리 메쉬와 같은 자리에 "
           "온다 — 그 부피는 결과를 보고 고를 수 있는 값이라, 메쉬 부피로 잡은 구는 도로 우리보다 "
           "나쁘다(" + ref("box-sphere-control", "구·상자 대조") + ").", "",
           "그리고 우리 세 밴드는 전부 PO 근사의 유효 문턱 아래에 부품을 남긴다"
           "(" + ref("po-knee", "PO 무릎") + "). **계산으로 닫히지 않는 축을 이 구가 닫는다.**"),

        next_steps([
            ("교정구를 표적과 같은 자리·같은 높이에서 세션 시작과 끝에 잰다",
             f"지금 우리 PO 출력인 절대 레벨이 처음으로 측정에 앵커된다 — 생산 모드의 평균 "
             f"레벨이동 "
             f"{D.num('modes.level_shift_production_abs_max_db', fmt='{:.2f}', unit='dB')} 가 "
             f"측정값으로 대체된다",
             "`src/sigma_anchor.py` 레벨 앵커 등록"),
            ("규약차 항을 되돌린 뒤 앵커 문헌과 σ 를 나란히 놓는다",
             "우리 σ 와 앵커 σ 의 비교가 사과-대-사과가 된다",
             ref("anchor-mode", "앵커 모드")),
        ]),
    ]


# =========================================================================== #
#  편 71 — 점표적 서브밴드
# =========================================================================== #
def blocks_71() -> list:
    return [
        header(
            num=71,
            title="표적을 한 거리빈에 넣는 최대 대역은 200 MHz 다",
            did="순시대역을 서브밴드로 쪼개 거리분해능이 기체 최대치수보다 커지는 최대 대역을 "
                "두 기체에서 함께 찾았다.",
            results=[
                f"두 기체를 함께 만족시키는 최대 서브밴드는 "
                f"{D.num('point_target_max_bw_MHz', fmt='{:.0f}', unit='MHz')} 다.",

                f"peak |s|² 를 σ 로 쓰려면 표적이 **한 거리빈 안**에 들어와야 한다 — "
                f"조건은 ΔR = c/2B > D_bbox 다.",

                f"서브밴드마다 σ 를 내면 그 다발이 곧 σ(f) 이고, 앵커 문헌(Das)의 절차와 같다.",

                f"게이팅은 넓게, 평가는 좁게 한다 — 게이팅 "
                f"{D.num('layers.gate_bw_mhz', fmt='{:.0f}', unit='MHz')} 전대역, 평가 "
                f"{D.num('layers.eval_bw_mhz', fmt='{:.0f}', unit='MHz')} 서브밴드 "
                f"{D.num('layers.n_subbands', fmt='{:.0f}', unit='개')}.",

                f"이 대역 상한이 "
                + ref("site-geometry", "부지 기하") + " 의 지면반사 분리 조건과 같은 눈금을 쓴다.",
            ],
            method=[
                ("점표적 조건",
                 "ΔR = c/2B 가 기체 최대치수 D_bbox 보다 커야 한다 — 그래야 표적이 한 거리빈에 든다"),
                ("D_bbox",
                 "프로펠러를 포함한 수평 최대치수. 원거리장에서 채택한 env 정의와 구별한다"),
                ("게이팅과 평가",
                 "앵커는 6차 Kaiser 창으로 CIR 을 게이팅한 뒤 주파수축으로 되돌린다"
                 "⟨outputs/measurement_layers.json : gate_wide_evaluate_narrow.anchor_quote⟩. "
                 "우리는 전대역에서 게이팅하고 σ 는 서브밴드로 평가한다"),
            ],
            repro=REPRO,
        ),

        md("## 순시대역을 쪼개 σ(f) 로 만든다", "",
           "peak |s|² 를 σ 로 쓰려면 표적이 **한 거리빈 안**에 들어와야 한다 "
           "(ΔR = c/2B > D_bbox).", "",
           f"두 기체를 함께 만족시키는 최대 서브밴드는 "
           f"{D.num('point_target_max_bw_MHz', fmt='{:.0f}', unit='MHz')} 다. 서브밴드마다 "
           f"σ 를 내면 그 다발이 곧 σ(f) 이고, 앵커 문헌의 절차와 같다."),

        md("## 대역별 점표적 조건", "",
           D.table("point_target",
                   [("대역 B", "B_MHz"), ("ΔR = c/2B", "dR_m"),
                    ("Matrice 4E", "matrice4e_ok"), ("여유", "matrice4e_margin_m"),
                    ("Mini 5 Pro", "mini5pro_ok"), ("여유", "mini5pro_margin_m")],
                   fmt={"B_MHz": "{:.0f} MHz", "dR_m": "{:.3f} m",
                        "matrice4e_margin_m": "{:+.3f} m",
                        "mini5pro_margin_m": "{:+.3f} m"})),

        md("## 게이팅은 넓게, 평가는 좁게", "",
           f"게이팅(되돌아온 신호에서 필요한 시간 구간만 창으로 잘라내기)은 넓게, 평가는 좁게 "
           f"한다. 우리는 {D.num('layers.gate_bw_mhz', fmt='{:.0f}', unit='MHz')} 전대역에서 "
           f"게이팅한 뒤 σ 는 {D.num('layers.eval_bw_mhz', fmt='{:.0f}', unit='MHz')} 서브밴드 "
           f"{D.num('layers.n_subbands', fmt='{:.0f}')} 개로 평가한다.", "",
           "앵커는 6차 Kaiser 창(가장자리를 부드럽게 깎는 시간창)으로 CIR(채널 임펄스 응답 — "
           "한 번 때린 신호가 되돌아오는 모양)을 게이팅한 뒤 주파수축으로 되돌린다"
           "⟨outputs/measurement_layers.json : gate_wide_evaluate_narrow.anchor_quote⟩."),

        next_steps([
            ("서브밴드마다 σ 를 내고 그 다발을 σ(f) 로 묶는다",
             "우리 σ(f) 가 앵커 문헌과 같은 절차 위에 서고 기울기 판정에 쓸 수 있게 된다",
             ref("session-drift", "기울기 판정 문턱")),
            ("서브밴드 폭을 바꿔 σ(f) 가 폭에 의존하는지 잰다",
             "점표적 가정이 실제로 성립하는 폭이 측정값으로 확정된다",
             "`benchmark/plan_measurement.py` 확장"),
        ]),
    ]


# =========================================================================== #
#  편 72 — 자세 통제
# =========================================================================== #
def blocks_72() -> list:
    return [
        header(
            num=72,
            title="각도표본을 λ/4D 로 잡아 앵커 문헌의 고정 2° 보다 촘촘하게 간다",
            did="방위 각도표본 간격을 밴드마다 λ/4D 로 정하고 앵커 문헌의 고정 간격과 밴드별로 "
                "견줬다.",
            results=[
                f"가장 촘촘한 요구는 "
                f"{D.num('aspect_finest_deg', fmt='{:.2f}', unit='°')} 다 "
                f"(`{D.get('aspect_finest_airframe')}` · `{D.get('aspect_finest_band')}`) — "
                f"한 바퀴에 {D.num('aspect_n_az_max', fmt='{:.0f}', unit='표본')} 이다.",

                f"앵커 문헌은 밴드와 무관하게 "
                f"{D.num('layers.anchor_step_deg', fmt='{:.2f}', unit='°')} 고정(반원 "
                f"{D.num('layers.anchor_N', fmt='{:.0f}', unit='점')})을 썼고, 우리는 밴드마다 "
                f"λ/4D 를 따라간다.",

                f"우리 요구 표본수는 반원당 "
                f"{D.num('layers.N_required_min', fmt='{:.0f}')} ~ "
                f"{D.num('layers.N_required_max', fmt='{:.0f}', unit='점')} 이다.",

                f"앵커가 스스로 «높은 주파수에서 성기다» 고 적은 자리는 우리 기체에서 "
                f"`{D.get('layers.anchor_too_coarse_1')}` 와 "
                f"`{D.get('layers.anchor_too_coarse_2')}` 두 칸이다.",

                f"로터는 **정지**시키고 블레이드 방위를 기록한다 — 앵커가 회전 성분을 뺐으므로 "
                f"그 규약에 맞춘다.",
            ],
            method=[
                ("표본 간격",
                 "`λ/(4·D_bbox)` [deg] 이하로 잡는다 — 방위 각도표본 권장 간격"),
                ("턴테이블",
                 "엔코더 턴테이블로 방위를 돌리고 각 표본의 각도를 기록한다"),
                ("로터 규약",
                 "로터는 정지시키고 블레이드 방위를 기록한다 — 앵커 문헌이 회전 성분을 뺐다"),
                ("앵커 대비",
                 "밴드별로 우리 요구 간격이 앵커의 고정 간격보다 촘촘한지 표의 마지막 열에 "
                 "그대로 싣는다"),
            ],
            repro=REPRO,
        ),

        md("## 각도표본을 λ/4D 로 잡는다", "",
           "방위는 엔코더 턴테이블로 돌리고, 표본 간격은 `λ/4D` 이하로 잡는다.", "",
           f"가장 촘촘한 요구는 {D.num('aspect_finest_deg', fmt='{:.2f}', unit='°')} "
           f"(`{D.get('aspect_finest_airframe')}` · `{D.get('aspect_finest_band')}`)이고, "
           f"한 바퀴에 {D.num('aspect_n_az_max', fmt='{:.0f}')} 표본이다.", "",
           "로터는 **정지**시키고 블레이드 방위를 기록한다 — 앵커가 회전 성분을 뺐으므로 "
           "그 규약에 맞춘다."),

        md("## 밴드별 요구 간격", "",
           D.table("aspect",
                   [("기체", "airframe"), ("밴드", "band"),
                    ("Δφ 나이퀴스트", "az_nyquist_deg"), ("Δφ 권장", "az_recommended_deg"),
                    ("한 바퀴 표본수", "n_az_per_turn"),
                    ("앵커 고정 2° 보다 촘촘한가", "finer_than_anchor_2deg")],
                   fmt={"az_nyquist_deg": "{:.2f}°", "az_recommended_deg": "{:.2f}°",
                        "n_az_per_turn": "{:.0f}"})),

        md("## 앵커가 성기다고 적은 자리", "",
           f"앵커는 높은 주파수에서 그 고정 간격이 성기다고 스스로 적었고"
           f"⟨outputs/measurement_layers.json : angular_sampling._rule⟩, 우리 기체에서 그 자리는 "
           f"`{D.get('layers.anchor_too_coarse_1')}` 와 "
           f"`{D.get('layers.anchor_too_coarse_2')}` 두 칸이다.", "",
           f"나머지 칸에서는 앵커의 고정 간격이 우리 요구보다 촘촘하다. 요구 표본수는 반원당 "
           f"{D.num('layers.N_required_min', fmt='{:.0f}')} ~ "
           f"{D.num('layers.N_required_max', fmt='{:.0f}')} 점이다."),

        next_steps([
            ("정지 로터 세션과 별도로 회전 세션을 잡는다",
             "마이크로도플러가 앵커와의 사과-대-사과를 깨지 않고 들어온다",
             ref("md-attitude", "자세와 가림")),
            ("방위 스윕으로 자세평균 σ 를 내고 로브 위치를 설계값과 대조한다",
             "자세 패턴을 기하에서 계산했다는 주장이 결판난다",
             ref("decision-matrix", "결정표") + " 의 첫 행"),
        ]),
    ]


# =========================================================================== #
#  편 73 — 실측 3층
# =========================================================================== #
def blocks_73() -> list:
    return [
        header(
            num=73,
            title="σ(f) 레인지·파형축·비행검출로 층을 나눈다",
            did="캠페인을 세 층으로 나누고 층마다 여는 축과 그 대가를 적었다.",
            results=[
                f"1층은 σ(f) 레인지다 — 정지 표적·턴테이블 방위컷·교정구·배경 코히런트 차감으로 "
                f"σ(f, φ) 의 분포 P(σ) 를 낸다.",

                f"2층은 파형축이다 — 세 파형 구조를 ISM "
                f"{D.num('layers.carrier_ism_ghz', fmt='{:.1f}', unit='GHz')} 한 반송파의 "
                f"같은 서브밴드 중심에 겹쳐 송신하고 SNR_out / E_tx 를 낸다.",

                f"3층은 비행 검출이다 — 로터가 도는 유일한 층이고, 고정 Pfa 에서 "
                f"`{D.get('layers.layer3_headline')}` 를 낸다.",

                f"2층을 한 반송파에 고정하는 이유는 면허다. 잃는 반송파축은 수신전용 검증 3점"
                f"({D.num('layers.validation_points')})의 실제 배치신호와 v_max 의 λ 비 "
                f"이전으로 갚는다.",

                f"2·3층의 ISM 원거리장은 외접상자 정의로 최대 "
                f"{D.num('layers.farfield_ism_bbox_max_m', fmt='{:.2f}', unit='m')} 이고, "
                f"세션 거리 "
                f"{D.num('farfield_adopted.R_ff_max_m', fmt='{:.2f}', unit='m')} 안에 든다.",
            ],
            method=[
                ("층 나누기",
                 "1층 = σ(f) 레인지, 2층 = ISM 한 반송파의 파형축, 3층 = 비행 검출. "
                 "값은 `outputs/measurement_layers.json` 에서 옮기거나 단위만 바꿨다"),
                ("한 반송파로 묶는 이유",
                 "2.1 GHz 야외 송신은 허가가 필요하고 '2.1 GHz 의 WiFi' 라는 배치신호는 세상에 "
                 "존재하지 않는 인공물이다"
                 "⟨outputs/measurement_layers.json : layer2_waveform_axis.why_one_carrier⟩"),
                ("1층이 내는 것",
                 "점별 패턴이 아니라 **분포 P(σ)** 다 — 검출확률이 σ 분포의 함수이므로 그 분포를 "
                 "Swerling 틀에 넣어 3층을 예측하고 3층이 그 예측을 검사한다"),
                ("수신 채널",
                 "검증 3점은 수신전용이고 기준 1 + 감시 1 = "
                 + D.num("layers.n_channels", fmt="{:.0f}", unit="채널")
                 + " 을 같은 클럭에서 쓴다"),
            ],
            repro=REPRO,
        ),

        # ⚠ `layers.rows[*].carrier` 는 근거 JSON 안에 옛 절 번호가 박혀 있다. 그 파일은
        #    고치지 않는 것이 이 라운드의 규칙이라, 반송파 열만 깨끗한 키로 다시 짠다.
        md("## 세 층", "",
           table(["층", "무엇을 재나", "반송파", "산출"], [
               [D.num("layers.rows[0].layer"), D.num("layers.rows[0].measures"),
                D.num("layers.validation_points"), D.num("layers.rows[0].product")],
               [D.num("layers.rows[1].layer"), D.num("layers.rows[1].measures"),
                "ISM " + D.num("layers.carrier_ism_ghz", fmt="{:.1f}", unit="GHz") + " 단일 · "
                + D.num("layers.span_ism_mhz", fmt="{:.0f}", unit="MHz") + " 폭",
                D.num("layers.rows[1].product")],
               [D.num("layers.rows[2].layer"), D.num("layers.rows[2].measures"),
                "ISM " + D.num("layers.carrier_ism_ghz", fmt="{:.1f}", unit="GHz"),
                D.num("layers.rows[2].product")],
           ])),

        md("## 2층을 한 반송파에 고정하는 이유", "",
           f"면허다 — 2.1 GHz 야외 송신은 허가가 필요하고 '2.1 GHz 의 WiFi' 라는 배치신호는 "
           f"세상에 존재하지 않는 인공물이다"
           f"⟨outputs/measurement_layers.json : layer2_waveform_axis.why_one_carrier⟩.", "",
           f"잃는 반송파축은 수신전용 검증 3점({D.num('layers.validation_points')})의 실제 "
           f"배치신호와 v_max 의 λ 비 이전으로 갚는다 — 그 3점은 교차설계의 대각선이 아니라 "
           f"독립 검사점이다."),

        md("## 1층이 내는 것은 분포다", "",
           f"1층이 내는 것은 점별 패턴이 아니라 **분포 P(σ)** 다. 검출확률이 σ 분포의 "
           f"함수이므로, 그 분포를 Swerling 틀(표적 밝기가 얼마나 요동하는지를 몇 가지 표준 "
           f"분포로 나눈 레이다 관례 분류)에 넣어 3층의 `{D.get('layers.layer3_headline')}` 를 "
           f"예측하고 3층이 그 예측을 검사한다"
           f"⟨outputs/measurement_layers.json : layer3_flight.ties_back_to⟩.", "",
           f"2층·3층의 ISM 원거리장은 외접상자(bbox — 프로펠러까지 감싸는 수평 최대치수) "
           f"정의로 최대 "
           f"{D.num('layers.farfield_ism_bbox_max_m', fmt='{:.2f}', unit='m')} 이고, "
           + ref("site-geometry", "부지 기하") + " 가 채택한 세션 거리 "
           f"{D.num('farfield_adopted.R_ff_max_m', fmt='{:.2f}', unit='m')}(env 정의) 안에 든다."),

        next_steps([
            ("자세축과 로터위상축을 σ 생산자에 배선한 뒤 sim-to-sim ablation 을 돌린다",
             "우리 σ 가 (σ̄, τ_decorr, 분포형) 3개 수로 환원되는지가 실측 없이 판정된다 — "
             "태스크는 분류가 아니라 **검출**로 고정한다",
             "`docs/SIM2REAL_PLAN.md` → `outputs/s2r_protocol.json`"),
            ("3팔 실측 ablation 설계를 검출 태스크와 supervision 사다리로 다시 짠다",
             f"현 설계 판정 {S2A.num('verdict')} 의 근거가 닫힌다 — 자세축·로터위상축을 배선하기 "
             f"전에는 세 팔이 분포형·상관시간 두 수로 환원되어 판정이 설계로 보장된다",
             "`outputs/s2r_attack.json` → `docs/SIM2REAL_PLAN.md`"),
            ("1층의 P(σ) 를 Swerling 틀에 넣어 3층의 Pd(range) 를 예측한다",
             "1층과 3층이 하나의 예측-검사 고리로 묶인다",
             "`outputs/measurement_layers.json : layer3_flight.ties_back_to`"),
        ]),
    ]


# =========================================================================== #
#  편 74 — 캠페인이 결판내는 양은 순위다
# =========================================================================== #
def blocks_74() -> list:
    return [
        header(
            num=74,
            title="캠페인이 결판내는 양은 절대값이 아니라 순위다",
            did="자세평균 σ 위에서 파형 순위를 뒤집는 데 필요한 밴드별 σ 이동폭을 캠페인의 "
                "진폭 재현성 요구치로 삼고 세션 드리프트 예산과 견줬다.",
            results=[
                f"기체 {D.num('ranking_validation.n_drones', fmt='{:.0f}', unit='종')}이 "
                f"순위 `{' > '.join(D.get('ranking_validation.consensus_order'))}` 에 "
                f"합의한다.",

                f"그 순위를 뒤집는 밴드별 σ 이동폭은 Matrice 4E "
                f"{D.num('ranking_validation.flip_span_db.matrice4e', fmt='{:.2f}', unit='dB')} · "
                f"Mini 5 Pro "
                f"{D.num('ranking_validation.flip_span_db.mini5pro', fmt='{:.2f}', unit='dB')} 다.",

                f"세션 드리프트 예산 "
                f"{D.num('ranking_validation.drift_budget_db', fmt='{:.2f}', unit='dB')} 가 "
                f"그 폭 아래에 있다 — 여유 "
                f"{D.num('ranking_validation.drift_margin_db', fmt='{:+.2f}', unit='dB')}. "
                f"설계가 판정 대상과 맞는다.",

                f"σ 를 세 밴드 공통으로 1 dB 옮기면 절대거리가 "
                f"{D.num('ranking_validation.common_mode_slope_db_per_db', fmt='{:.2f}', unit='dB')} "
                f"움직인다 — 순위는 그 공통이동에서 불변이다.",

                f"⚠ 그 폭을 정하는 것은 Matrice 4E 행이고, 그 행은 {MFX.num('_meta.date')} "
                f"형상 정정 전 메쉬 값이다 — σ 사슬을 다시 돌려 그 행이 여유만큼만 움직여도 "
                f"이 «맞는다» 판정이 뒤집힌다.",
            ],
            method=[
                ("판정 대상",
                 "자세평균 σ 위의 파형 순위 뒤집힘 폭을 캠페인 요구치로 삼음 — "
                 "`benchmark/sigma_sensitivity.py:470`"),
                ("왜 순위인가",
                 "순위를 정하는 λ²·점유·대역폭 항은 밴드 간 차이고 환경 항은 세 밴드 공통이다 — "
                 "야외 환경이 시뮬 자유공간과 달라도 밴드 간 차는 남는다"),
                ("몬테카를로 기저",
                 "단일자세 lead 위의 몬테카를로 — `benchmark/sigma_sensitivity.py:430`. "
                 "캠페인은 방위 "
                 + D.num("ranking_validation.az_step_deg", fmt="{:.2f}", unit="°")
                 + " 표본으로 자세평균 σ 를 낸다"),
                ("절대 σ 는 다음 라운드",
                 ref("sigma-checklist", "체크리스트") + " 여섯 항목을 다 채운 세션이 만든다"),
            ],
            repro=REPRO,
        ),

        md("## 캠페인이 결판내는 양", "",
           f"자세평균 σ 에서 기체 "
           f"{D.num('ranking_validation.n_drones', fmt='{:.0f}', unit='종')}이 순위 "
           f"`{' > '.join(D.get('ranking_validation.consensus_order'))}` 에 합의하고, 그 순위를 "
           f"뒤집는 밴드별 σ 이동폭은 Matrice 4E "
           f"{D.num('ranking_validation.flip_span_db.matrice4e', fmt='{:.2f}', unit='dB')} · "
           f"Mini 5 Pro "
           f"{D.num('ranking_validation.flip_span_db.mini5pro', fmt='{:.2f}', unit='dB')} 다.", "",
           f"세션 드리프트 예산 "
           f"{D.num('ranking_validation.drift_budget_db', fmt='{:.2f}', unit='dB')} 가 그 폭 "
           f"아래에 있으므로(여유 "
           f"{D.num('ranking_validation.drift_margin_db', fmt='{:+.2f}', unit='dB')}) 이 "
           f"캠페인은 **검출 사슬과 파형 순위**를 결판낸다."),

        md("## 설계상 같게 맞춘 축과 다르게 둔 축", "",
           table(["설계상 같게 맞춘 축", "설계상 다르게 둔 축"], [
               ["바이스태틱 구조 — 기준 1 + 감시 1, 공통 클럭",
                "환경 — 시뮬은 자유공간, 실측은 지면반사·다중경로"],
               ["같은 기체 2종 (Matrice 4E · Mini 5 Pro)", "클러터 — 실측 부지의 정적 산란체"],
               ["같은 세 파형 (LTE · 5G · WiFi)", "동적범위 — 시뮬 ECA 는 float64, 실측은 12-bit"],
               ["같은 검출기 사슬 (ECA → 거리도플러 → CA-CFAR)",
                "자세 — 시뮬은 각도격자, 비행 중에는 자유"],
               ["σ 통계 규약 (방위 선형평균)", "링크예산 전제 — 절대 탐지거리"],
           ])),

        md("## 앵커 원장 — 이 캠페인이 닫으러 가는 항목", "",
           A.table("uncontrolled",
                   [("항목", "term"), ("상태", "status"), ("크기", "size_db")],
                   fmt={"size_db": "{:+.2f} dB"}, null="미상")),

        md("## 재보정 모드 — 어느 숫자가 어느 모드에서 오나", "",
           f"생산 σ 원장은 `{D.num('modes.production_mode')}` 다 — 주파수 기울기만 측정에서 "
           f"받고 **절대 레벨은 우리 PO 출력 그대로**다(평균 레벨이동 "
           f"{D.num('modes.level_shift_production_abs_max_db', fmt='{:.2f}', unit='dB')}). "
           f"레벨을 앵커에 맞추는 두 모드는 설계 계산에만 쓴다.", "",
           D.table("modes.rows",
                   [("모드", "mode"), ("무엇을 옮기나", "moves"),
                    ("Matrice 4E", "matrice4e_db"), ("Mini 5 Pro", "mini5pro_db")],
                   fmt={"matrice4e_db": "{:+.2f} dB", "mini5pro_db": "{:+.2f} dB"})),

        md("## 두 기체가 앵커에 대해 어디 서 있나", "",
           table(["기체", "앵커 대비 등급", "크기비", "L² 보정", "L⁴ 보정"], [
               ["Matrice 4E", A.get("drones.matrice4e.comparability.verdict"),
                A.num("drones.matrice4e.comparability.size_ratio", fmt="{:.3f}"),
                A.num("drones.matrice4e.comparability.size_corr_L2_db", fmt="{:+.2f}", unit="dB"),
                A.num("drones.matrice4e.comparability.size_corr_L4_db", fmt="{:+.2f}", unit="dB")],
               ["Mini 5 Pro", A.get("drones.mini5pro.comparability.verdict"),
                A.num("drones.mini5pro.comparability.size_ratio", fmt="{:.3f}"),
                A.num("drones.mini5pro.comparability.size_corr_L2_db", fmt="{:+.2f}", unit="dB"),
                A.num("drones.mini5pro.comparability.size_corr_L4_db", fmt="{:+.2f}", unit="dB")],
           ]), "",
           f"두 기체 다 등급이 `scaled` 다 — 앵커 기체와 같은 4로터 위상이고 대각만 다르다.", "",
           f"⚠ 위 표들은 `rcs_anchor → sigma_anchor` 사슬 위에 서 있고, 그 사슬은 "
           f"{MFX.num('_meta.date')} 형상 정정 **전** 메쉬로 돌린 것이다 — 다섯 앵커 기체 중 "
           f"Matrice 4E 가 그 정정을 받았다"
           f"(⟨outputs/meshfix_attack.json : Q6_invalidated_outputs.critical[1]⟩)."),

        next_steps([
            ("야외 고정기하에서 세 파형을 같은 세션에 송신하고 방위 스윕으로 자세평균 순서를 잰다",
             f"파형 상대순위 "
             f"`{' > '.join(D.get('ranking_validation.consensus_order'))}` 가 실측에서 "
             f"확인된다 — 판정 문턱은 뒤집힘 폭 "
             f"{D.num('ranking_validation.flip_span_min_db', fmt='{:.2f}', unit='dB')} 다",
             ref("decision-matrix", "결정표") + " → 검출 결과 편과 대조"),
            ("σ 사슬을 정정된 메쉬로 다시 돌린 뒤 뒤집힘 폭을 다시 읽는다",
             "설계와 판정 대상의 «맞는다» 가 현재 형상 위에서 확정된다",
             "`benchmark/rcs_anchor.py` → `src/sigma_anchor.py`"),
        ]),
    ]


# =========================================================================== #
#  편 75 — 결정표
# =========================================================================== #
def blocks_75() -> list:
    return [
        header(
            num=75,
            title="주장마다 판정 범위를 결판·사슬확인·캠페인 밖으로 적었다",
            did="시뮬의 주장마다 그것을 뒤집는 관측량을 짝지어 임계를 수치로 고정하고 판정 범위를 "
                "세 갈래로 표시했다.",
            results=[
                f"판정 범위는 세 갈래다 — `결판`(이 캠페인이 정한다) · `사슬 확인`(설계값과 "
                f"대조한다) · `이 캠페인 밖`(다음 라운드나 통제 시뮬이 정한다).",

                f"«이 캠페인 밖» 으로 적은 것이 둘이다 — 자유공간 절대 탐지거리와 Pfa 교정. "
                f"앞은 환경 공통항이, 뒤는 통제 몬테카를로 "
                f"{V.num('meta.runtime_s', fmt='{:.0f}', unit='s')} 가 정한다.",

                f"편파는 `결판` 이다 — 앵커 측정은 VV 하나이고 우리 커널은 무편파 스칼라라, "
                f"VV / VH / HV / HH 4조합이 그 차를 dB 로 확정한다.",

                f"PTD(모서리 회절) 행도 `결판` 이다 — 켠 비용은 "
                f"{PW.num('verdict.cost_increase_pct', fmt='{:+.1f}', unit='%')} 이고, "
                f"정면입사만 재면 판별력이 0 이라 비스듬한 입사를 함께 잰다.",

                f"레벨 행의 눈감기 사전값은 고도정합 실측곡선 대비 밴드평균 "
                f"{P3.num('residual.vs_yuan_theta90_measured_curve.mean_db', fmt='{:+.2f}', unit='dB')} "
                f"이고, 사진 실측 v2 메쉬에서는 "
                f"{PV2.num('v1_vs_v2.level_db.v2', fmt='{:+.2f}', unit='dB')} 다.",
            ],
            method=[
                ("표의 네 번째 열",
                 "판정 범위 — `결판` · `사슬 확인` · `이 캠페인 밖`. 세 번째 값을 그대로 적는 "
                 "것이 이 표의 핵심이다"),
                ("주장과 측정의 짝",
                 "시뮬의 주장마다 그것을 뒤집는 관측량을 짝지어 임계를 수치로 고정했다"),
                ("편파 용어",
                 "전파의 전기장이 흔들리는 방향. 세워서 보내고 세워서 받는 조합을 VV, 눕혀 "
                 "보내고 눕혀 받는 조합을 HH 라 적는다. 우리 커널은 세기 값 하나만 내므로 "
                 "**무편파 스칼라**다"),
            ],
            repro=REPRO,
        ),

        md("## 판정 범위를 세 갈래로 적는다", "",
           "네 번째 열이 **판정 범위**다 — `결판`(이 캠페인이 정한다) · `사슬 확인`(설계값과 "
           "대조한다) · `이 캠페인 밖`(다음 라운드나 통제 시뮬이 정한다). 세 번째 값을 그대로 "
           "적는 것이 이 표의 핵심이다.", "",
           "표에 나오는 **편파**는 전파의 전기장이 흔들리는 방향을 말한다 — 세워서 보내고 "
           "세워서 받는 조합을 VV, 눕혀 보내고 눕혀 받는 조합을 HH, 한쪽만 눕힌 조합을 "
           "VH·HV 라 적는다. 우리 커널은 그 방향을 가르지 않고 세기 값 하나만 내므로 "
           "**무편파 스칼라**라고 부른다."),

        md("## 표적 모델 쪽 주장", "",
           table(["주장", "이를 결정하는 측정", "판정 기준", "판정 범위"], [
               ["자세 패턴 B1(φ) 을 SBR+PO 기하에서 계산했다",
                "턴테이블 방위컷, 로터 정지",
                "Δφ ≤ " + D.num("aspect_finest_deg", fmt="{:.2f}", unit="°")
                + " 로 재고 로브 위치 대조", "결판"],
               ["절대 레벨은 우리 PO 출력이다 (앵커는 기울기만 옮긴다)",
                "표적과 같은 자리에서 교정구 + 배경 코히런트 차감",
                "교정구 여유 ≥ "
                + D.num("calibration_margin_min_db", fmt="{:+.2f}", unit="dB")
                + ", 세션 드리프트 ≤ "
                + D.num("ranking_validation.drift_budget_db", fmt="{:.2f}", unit="dB"), "결판"],
               ["밴드 기울기는 측정 앵커에 맞췄다",
                "세 밴드를 같은 세션에서 측정",
                "세션 재현성 < "
                + D.num("slope.threshold_db", fmt="{:.2f}", unit="dB"),
                "결판 — σ 사슬 재실행이 선행 조건"],
               ["크기전이는 L² 와 L⁴ 를 괄호로 함께 싣는다 ("
                + D.num("size_law.uncontrolled_size_db", fmt="{:.2f}", unit="dB") + ")",
                "두 기체를 한 캠페인에서 측정",
                "차등 " + D.num("size_law.differential_db", fmt="{:.2f}", unit="dB") + " 의 부호",
                "결판"],
               ["편파: 앵커 측정은 VV 하나, 커널은 무편파 스칼라",
                "VV / VH / HV / HH 4조합",
                "무편파 모형과 VV 측정의 차를 dB 로 확정", "결판"],
           ])),

        md("## 모서리 회절 행 — 어느 각도에서 재는가", "",
           table(["주장", "이를 결정하는 측정", "판정 기준", "판정 범위"], [
               ["모서리 회절 — 1차 PTD 항이 커널에 있고 생산 기본값은 끔이다",
                "모서리가 많은 표준체(평판·이면각)를 같은 세션에서 함께 측정하되 **정면입사만 "
                "재지 않는다** — 1차 모서리 항은 정면입사에서 두 편파에 같은 값을 주므로 그 "
                "각도에서는 판별력이 0 이다 ⟨outputs/lowfreq_attack.json : "
                "what_survives_the_attack[3]⟩. 비스듬한 입사와 모서리 방향 입사를 함께 잰다",
                "위상까지 정합해 부호를 심판한다 — 평판 RMS 시험은 위상맹목이다. 켠 비용은 "
                + PW.num("verdict.cost_increase_pct", fmt="{:+.1f}", unit="%"),
                "결판"],
           ]), "",
           f"레벨 행의 눈감기 사전값도 여기 붙는다 — 고도정합 실측곡선 대비 밴드평균 "
           f"{P3.num('residual.vs_yuan_theta90_measured_curve.mean_db', fmt='{:+.2f}', unit='dB')} "
           f"(v1 메쉬)이고, 사진 실측 v2 메쉬에서는 "
           f"{PV2.num('v1_vs_v2.level_db.v2', fmt='{:+.2f}', unit='dB')} 다."),

        md("## 조명원·검출기·결과 쪽 주장", "",
           table(["주장", "이를 결정하는 측정", "판정 기준", "판정 범위"], [
               ["파형별 점유·대역폭 대가는 σ 와 무관하게 정확하다",
                "X410 이 같은 기하에서 세 파형을 송신",
                "측정 ΔR·모호함수가 설계값과 일치", "사슬 확인"],
               ["파형 상대순위 `"
                + " > ".join(D.get("ranking_validation.consensus_order")) + "`",
                "야외 고정기하 탐지시험 · 방위 스윕으로 자세평균",
                "순서 일치 · 뒤집힘 폭 "
                + D.num("ranking_validation.flip_span_min_db", fmt="{:.2f}", unit="dB"),
                "결판"],
               ["자유공간 절대 탐지거리",
                "환경 공통항(지면·클러터)이 정한다",
                "σ 공통이동 1 dB 당 거리 "
                + D.num("ranking_validation.common_mode_slope_db_per_db",
                        fmt="{:.2f}", unit="dB") + " 이동",
                "**이 캠페인 밖**"],
               ["명목 Pfa 를 교정해야 파형 비교가 성립한다",
                "부지 배경 CPI 를 녹화해 그 부지의 경험 Pfa 를 별도로 기록",
                "교정 자체는 통제 몬테카를로 "
                + V.num("meta.runtime_s", fmt="{:.0f}", unit="s") + " 가 세운다",
                "**이 캠페인 밖**"],
               ["12-bit ADC 가 직접파 제거의 천장이다",
                "직접파를 실제로 받아 ECA 잔차를 잰다",
                "여유 " + M.num("adc.headroom_db_min", fmt="{:.1f}", unit="dB")
                + " 가 야외에 얼마나 남나", "사슬 확인"],
           ])),

        md("## 각 행이 어느 편으로 이어지나", "",
           table(["행", "이어지는 편"], [
               ["자세 패턴 · 각도표본", ref("attitude", "자세 통제")],
               ["절대 레벨 · 교정구", ref("calibration-sphere", "교정 기준체")],
               ["밴드 기울기", ref("session-drift", "기울기 판정 문턱")],
               ["크기전이 법칙", ref("size-law-differential", "크기법칙")],
               ["파형 상대순위", ref("sim-vs-meas", "캠페인이 결판내는 양")],
               ["Pfa 교정", ref("cfar-calib", "CFAR 교정")],
               ["ADC 천장", ref("hardware", "하드웨어")],
           ])),

        next_steps([
            ("VV / VH / HV / HH 4조합을 잰다",
             "무편파 스칼라 모형과 VV 측정의 차가 dB 로 확정된다",
             "`src/materials.py:171` `gamma_po()` 의 편파 확장 결정"),
            ("같은 세션에서 모서리가 많은 표준체를 **정면입사 밖의 각도까지** 함께 잰다",
             f"1차 PTD 항의 부호와 크기를 실측이 심판한다 — 켠 비용은 "
             f"{PW.num('verdict.cost_increase_pct', fmt='{:+.1f}', unit='%')} 다",
             "`benchmark/ptd_plate_validation.py`"),
            ("부지 배경 CPI 를 녹화해 그 부지의 경험 Pfa 를 별도로 기록한다",
             "야외 세션이 같은 임계를 부지 잡음 위에서 재현해 사슬을 확인한다",
             ref("cfar-calib", "CFAR 교정")),
        ]),
    ]


# =========================================================================== #
#  편 76 — 기울기 판정의 문턱
# =========================================================================== #
def blocks_76() -> list:
    return [
        header(
            num=76,
            title="기울기 판정의 문턱은 세션간 진폭 재현성이고, σ 사슬 세대를 바꾸면 그 문턱이 "
                  "손닿는 범위 밖으로 좁아진다",
            did="우리 커널의 밴드 기울기와 앵커 두 개의 기울기가 대역 끝에서 벌리는 간격을 계산해 "
                "세션 재현성 요구치로 못 박고, 세대를 바꿔 같은 계산을 다시 했다.",
            results=[
                f"판정 문턱은 "
                f"{D.num('slope.threshold_db', fmt='{:.2f}', unit='dB')} 다 — 앵커 두 개(전대역 "
                f"Das · 창을 맞춘 저대역 Yuan) 중 **좁은 쪽**이다.",

                f"우리 커널은 {D.num('slope.rows[0].ours_db_per_ghz', fmt='{:.3f}')} ~ "
                f"{D.num('slope.rows[1].ours_db_per_ghz', fmt='{:.3f}')} dB/GHz 이고, 앵커는 "
                f"전대역 {D.num('slope.anchor_db_per_ghz', fmt='{:.3f}')} · 창을 맞춘 쪽 "
                f"{D.num('slope.anchor_band_matched_db_per_ghz', fmt='{:.3f}')} dB/GHz 다.",

                f"대역 {D.num('slope.span_ghz', fmt='{:.3f}', unit='GHz')} 를 지나며 두 가설이 "
                f"벌리는 폭은 전대역 앵커에서 "
                f"{D.num('slope.gap_db_min', fmt='{:.2f}')} ~ "
                f"{D.num('slope.rows[1].gap_db', fmt='{:.2f}')} dB, 창을 맞춘 앵커에서 "
                f"{D.num('slope.gap_db_min_band_matched', fmt='{:.2f}')} ~ "
                f"{D.num('slope.rows[1].gap_db_band_matched', fmt='{:.2f}')} dB 다.",

                f"⚠⚠ 이 문턱은 생산 원장 세대({D.num('slope.ledger_generation')})의 수다. "
                f"디스크의 현재 세대({D.num('slope.current_generation')})로 같은 정의를 다시 "
                f"적합하면 Matrice 4E 가 "
                f"{D.num('slope.rows[0].ours_db_per_ghz', fmt='{:.3f}')} → "
                f"{D.num('slope.rows[0].ours_current_generation_db_per_ghz', fmt='{:.3f}', unit='dB/GHz')} "
                f"로 내려간다.",

                f"그 세대에서 가장 좁은 판별폭은 "
                f"{D.num('slope.discrimination_min_abs_db_current_generation', fmt='{:.2f}', unit='dB')} "
                f"로, 세션 진폭 재현성이 닿는 범위 밖이다 — 이 행을 «결판» 으로 유지하려면 "
                f"σ 사슬 재실행이 선행 조건이다.",
            ],
            method=[
                ("기울기 정의",
                 "세 밴드 방위평균 μ 를 f[GHz] 에 1차 적합(el=0). 정의는 하나로 고정한다 — "
                 + D.num("slope.fit_note_short")),
                ("판별폭",
                 "gap = (ours − anchor) × span — 대역 끝에서 두 가설이 벌리는 간격 [dB]. "
                 "세션간 진폭 재현성이 이보다 좋아야 기울기 판정이 성립한다"),
                ("앵커 두 개",
                 "전대역 적합값(Das)과 이 캠페인에 창을 맞춘 저대역 적합값(Yuan θ=90 복원 "
                 "실측곡선)을 나란히 쓴다. 문턱은 " + D.num("slope.threshold_rule")),
                ("두 세대",
                 "생산 원장은 한 세대 앞선 `rcs_anchor.json` 위에 서 있다. 디스크의 현재 "
                 "판으로 같은 정의를 다시 적합한 값을 나란히 싣는다 — 문턱은 생산 원장 값으로 "
                 "그대로 둔다"),
            ],
            repro=REPRO,
        ),

        md("## 세션 재현성이 판정의 문턱이다", "",
           *_fig(1, "report06_slope",
                 "우리 기울기와 앵커 기울기를 가르려면 세션 재현성이 얼마나 좋아야 하는가?"),
           f"우리 커널은 {D.num('slope.rows[0].ours_db_per_ghz', fmt='{:.3f}')} ~ "
           f"{D.num('slope.rows[1].ours_db_per_ghz', fmt='{:.3f}')} dB/GHz 다. 앵커는 "
           f"**두 개를 나란히** 쓴다."),

        md("## 두 앵커와 두 창", "",
           table(["앵커", "기울기 [dB/GHz]", "적합 창 [GHz]"], [
               ["전대역 (Das)",
                D.num("slope.anchor_db_per_ghz", fmt="{:.3f}"),
                D.num("slope.anchor_window_ghz[0]", fmt="{:.1f}") + " ~ "
                + D.num("slope.anchor_window_ghz[1]", fmt="{:.1f}")],
               ["창을 맞춘 저대역 (" + D.num("slope.anchor_band_matched_source") + ")",
                D.num("slope.anchor_band_matched_db_per_ghz", fmt="{:.3f}"),
                D.num("slope.anchor_band_matched_window_ghz[0]", fmt="{:.1f}") + " ~ "
                + D.num("slope.anchor_band_matched_window_ghz[1]", fmt="{:.1f}")],
               ["이 캠페인의 창", "—",
                D.num("slope.campaign_window_ghz[0]", fmt="{:.3f}") + " ~ "
                + D.num("slope.campaign_window_ghz[1]", fmt="{:.2f}")],
           ]), "",
           "⚠ 두 창은 **같지 않고 겹친다** — 앵커 창이 이 캠페인의 창을 덮되 위쪽이 더 넓다. "
           "전대역 앵커와 견주면 훨씬 가깝다는 뜻이지 같은 창이라는 뜻이 아니다."),

        md("## 판별폭과 문턱", "",
           f"대역 {D.num('slope.span_ghz', fmt='{:.3f}', unit='GHz')} 를 지나며 두 가설이 "
           f"벌리는 폭은 전대역 앵커에서 "
           f"{D.num('slope.gap_db_min', fmt='{:.2f}')} ~ "
           f"{D.num('slope.rows[1].gap_db', fmt='{:.2f}')} dB, 창을 맞춘 앵커에서 "
           f"{D.num('slope.gap_db_min_band_matched', fmt='{:.2f}')} ~ "
           f"{D.num('slope.rows[1].gap_db_band_matched', fmt='{:.2f}')} dB 다.", "",
           f"**판정 문턱은 둘 중 좁은 쪽 "
           f"{D.num('slope.threshold_db', fmt='{:.2f}', unit='dB')} 로 잡는다** — 창을 맞춘 "
           f"앵커가 우리 값에 더 가까워서 요구 재현성이 그만큼 빡빡하다"
           f"(⟨outputs/p3_validation_v2.json : our_operating_band⟩)."),

        md("## 세대를 바꾸면 문턱이 손닿는 범위 밖으로 간다", "",
           f"위의 «우리 커널» 값은 생산 원장(`sigma_anchor.json`, "
           f"{D.num('slope.ledger_generation')} 판 `rcs_anchor.json` 위)에서 왔다. 디스크의 "
           f"현재 `rcs_anchor.json`({D.num('slope.current_generation')} 판)으로 같은 정의를 "
           f"다시 적합하면 Matrice 4E 가 "
           f"{D.num('slope.rows[0].ours_db_per_ghz', fmt='{:.3f}')} → "
           f"{D.num('slope.rows[0].ours_current_generation_db_per_ghz', fmt='{:.3f}', unit='dB/GHz')} "
           f"로 내려가고, 전대역 앵커와의 판별폭이 "
           f"{D.num('slope.rows[0].gap_db', fmt='{:.2f}')} → "
           f"{D.num('slope.rows[0].gap_db_current_generation', fmt='{:.2f}', unit='dB')} 가 "
           f"된다.", "",
           f"그 세대에서 가장 좁은 판별폭은 "
           f"{D.num('slope.discrimination_min_abs_db_current_generation', fmt='{:.2f}', unit='dB')} "
           f"로, 세션 진폭 재현성이 닿는 범위 밖이다. 두 세대 모두 {MFX.num('_meta.date')} "
           f"형상 정정 전 메쉬 위에 서 있고, 앵커 5기체 중 Matrice 4E 가 그 정정을 받았다."),

        next_steps([
            ("σ 사슬(rcs_anchor → sigma_anchor)을 한 세대로 다시 돌린 뒤 이 문턱을 다시 낸다",
             f"기울기 판별폭이 현재 기하 위에서 확정된다 — 지금은 세대를 바꾸는 것만으로 "
             f"{D.num('slope.rows[0].gap_db', fmt='{:.2f}')} → "
             f"{D.num('slope.rows[0].gap_db_current_generation', fmt='{:.2f}', unit='dB')} "
             f"움직인다",
             "`benchmark/rcs_anchor.py` → `src/sigma_anchor.py`"),
            ("세 밴드를 같은 세션에서 재고 세션간 진폭 재현성을 기록한다",
             f"밴드 기울기가 우리 커널 값과 앵커 "
             f"{D.num('slope.anchor_db_per_ghz', fmt='{:.3f}')} dB/GHz 중 어디에 앉는지 "
             f"결정된다 — 위 사슬 재실행이 이 판정의 선행 조건이다",
             ref("anchor-mode", "앵커 모드") + " 재기술"),
        ]),
    ]


# =========================================================================== #
#  편 77 — 크기전이 법칙  ⭐신설 (옛 셀 22 의 뒤 절반)
# =========================================================================== #
def blocks_77() -> list:
    return [
        header(
            num=77,
            title="두 기체를 함께 재면 크기전이 법칙이 차등신호의 부호 하나로 갈린다",
            did="앵커보다 큰 기체와 작은 기체를 한 캠페인에 넣고 두 크기전이 법칙이 예측하는 μ 를 "
                "밴드마다 계산해 차등신호를 냈다.",
            results=[
                f"Matrice 4E 는 앵커보다 크고(크기비 "
                f"{D.num('size_law.by_airframe.matrice4e.size_ratio', fmt='{:.3f}')}), "
                f"Mini 5 Pro 는 작다"
                f"({D.num('size_law.by_airframe.mini5pro.size_ratio', fmt='{:.3f}')}).",

                f"두 법칙의 예측이 **반대 방향**으로 갈리므로 두 기체의 μ 차이가 법칙을 직접 "
                f"고른다 — 차등신호는 "
                f"{D.num('size_law.differential_db', fmt='{:.2f}', unit='dB')} 다.",

                f"기체별 두 법칙의 벌어짐은 Matrice 4E "
                f"{D.num('size_law.by_airframe.matrice4e.spread_db', fmt='{:+.2f}', unit='dB')} · "
                f"Mini 5 Pro "
                f"{D.num('size_law.by_airframe.mini5pro.spread_db', fmt='{:+.2f}', unit='dB')} 다.",

                f"앵커 원장은 크기전이 법칙을 미해소 항목으로 두고 그 크기를 "
                f"{D.num('size_law.uncontrolled_size_db', fmt='{:.2f}', unit='dB')} 로 적어 "
                f"뒀다 — 이 캠페인이 그 항목을 닫으러 간다.",

                f"판정은 값이 아니라 **부호**다 — 두 기체 μ 차이의 부호 하나가 법칙을 고른다.",
            ],
            method=[
                ("크기전이 법칙",
                 "앵커 기체의 σ 를 우리 기체로 옮길 때 길이의 몇 제곱으로 잡느냐 — "
                 "L²(면적 비례)와 L⁴(공진 영역) 두 가설"),
                ("예상 σ",
                 "Das 앵커 레벨에 두 법칙을 각각 적용 — `src/sigma_anchor.py:255`. "
                 "설계 계산에만 쓰고 생산 σ 원장은 기울기만 앵커한다"),
                ("차등신호",
                 "(L⁴−L²)_matrice4e − (L⁴−L²)_mini5pro [dB]. 두 기체가 앵커보다 각각 크고 "
                 "작으므로 두 법칙의 예측이 반대 방향으로 갈린다"),
            ],
            prereq=[("앞 편", ref("sim-vs-meas", "캠페인이 결판내는 양")
                     + " — 두 기체가 앵커에 대해 어디 서 있나")],
            repro=REPRO,
        ),

        md("## 두 기체를 함께 사는 이유", "",
           f"Matrice 4E 는 앵커보다 크고(크기비 "
           f"{D.num('size_law.by_airframe.matrice4e.size_ratio', fmt='{:.3f}')}), Mini 5 Pro 는 "
           f"작다({D.num('size_law.by_airframe.mini5pro.size_ratio', fmt='{:.3f}')}). "
           f"두 법칙의 예측이 **반대 방향**으로 갈리므로 두 기체의 μ 차이가 법칙을 직접 고른다."),

        md("## 두 법칙이 반대로 갈린다", "",
           *_fig(1, "report06_size_law",
                 "두 기체를 함께 재면 L² 와 L⁴ 를 가를 수 있는가?"),
           f"차등신호 {D.num('size_law.differential_db', fmt='{:.2f}', unit='dB')} 가 두 기체를 "
           f"함께 사는 이유다. 기체별 벌어짐은 Matrice 4E "
           f"{D.num('size_law.by_airframe.matrice4e.spread_db', fmt='{:+.2f}', unit='dB')} · "
           f"Mini 5 Pro "
           f"{D.num('size_law.by_airframe.mini5pro.spread_db', fmt='{:+.2f}', unit='dB')} 다."),

        md("## 앵커 원장이 이 항목을 열어 뒀다", "",
           f"앵커 원장은 크기전이 법칙을 미해소 항목으로 두고 그 크기를 "
           f"{D.num('size_law.uncontrolled_size_db', fmt='{:.2f}', unit='dB')} 로 적어 뒀다. "
           f"이 캠페인이 그 항목을 닫으러 간다.", "",
           f"정의는 하나로 고정한다 — `{D.get('size_law.definition')}`", "",
           "판정은 값이 아니라 **부호**다. 두 기체 μ 차이의 부호 하나가 법칙을 고르고, 그 뒤에 "
           "σ 원장이 괄호를 지운다."),

        next_steps([
            ("두 기체를 한 캠페인에서 재고 μ 차이의 부호를 본다",
             f"크기전이 법칙 L² vs L⁴ (원장 "
             f"{D.num('size_law.uncontrolled_size_db', fmt='{:.2f}', unit='dB')})가 확정된다",
             "`src/sigma_anchor.py` 크기법칙 고정"),
            ("고른 법칙을 σ 원장에 반영하고 앵커 원장의 괄호를 지운다",
             "미해소 항목 하나가 원장에서 닫힌다",
             ref("anchor-ledger", "앵커 원장")),
        ]),
    ]


# --------------------------------------------------------------------------- #
#  색인 샤드 — 편마다 하나. W0 이 `outputs/reports_index.json` 으로 병합한다.
#  ⚠ 편마다 따로 쓰므로 부 에이전트가 동시에 돌아도 안 부딪친다.
# --------------------------------------------------------------------------- #
_SHARD_DIR = os.path.join(_ROOT, "outputs", "reports_index")


def _plan_meta(anchor: str) -> dict:
    with open(_PLAN, encoding="utf-8") as f:
        plan = json.load(f)
    for r in plan["reports"]:
        if r["anchor"] == anchor:
            return r
    return {}


def _part_name(part: int) -> str:
    with open(_PLAN, encoding="utf-8") as f:
        plan = json.load(f)
    for p in plan["parts"]:
        if int(p["part"]) == part:
            return p["name"]
    return ""


def write_shard(no: str, anchor: str, rep: dict, part: int) -> None:
    meta = _plan_meta(anchor)
    title = REG[anchor][1]
    short = title.split("—")[0].split(",")[0].strip()
    if len(short) > 26:
        short = short[:25].rstrip() + "…"
    shard = dict(
        no=no, anchor=anchor, part=part, part_name=_part_name(part),
        title=title, short=short,
        file=f"reports/{no}_{anchor}.ipynb",
        builder=f"src/{os.path.basename(__file__)}",
        in_plan=bool(meta),
        evidence=list(meta.get("evidence_json") or []),
        from_cells=list(meta.get("from_cells") or []),
        md_cells=rep["md_cells"], figures=rep["figures"],
        provenance_tags=rep["provenance_tags"],
        negatives=rep["n_negatives"], hedges=rep["n_hedges"], ok=rep["ok"])
    os.makedirs(_SHARD_DIR, exist_ok=True)
    with open(os.path.join(_SHARD_DIR, f"{anchor}.json"), "w", encoding="utf-8") as f:
        json.dump(shard, f, ensure_ascii=False, indent=1)


# =========================================================================== #
REPORTS = [
    ("67", "hardware", blocks_67),
    ("68", "sigma-checklist", blocks_68),
    ("69", "site-geometry", blocks_69),
    ("70", "calibration-sphere", blocks_70),
    ("71", "subband", blocks_71),
    ("72", "attitude", blocks_72),
    ("73", "three-layers", blocks_73),
    ("74", "sim-vs-meas", blocks_74),
    ("75", "decision-matrix", blocks_75),
    ("76", "session-drift", blocks_76),
    ("77", "size-law-differential", blocks_77),
]


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    print("── 부 11 「실측 설계」 빌드 ──")
    for no, anchor, fn in REPORTS:
        path = os.path.join(OUT, f"{no}_{anchor}.ipynb")
        rep = build_notebook(path, fn(), strict=True)
        write_shard(no, anchor, rep, 11)
    print(f"✅ {len(REPORTS)} 편 → {os.path.relpath(OUT, _ROOT)}/")


if __name__ == "__main__":
    main()
