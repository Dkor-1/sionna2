# -*- coding: utf-8 -*-
"""
build_part07_microdoppler.py — 부 7 「마이크로도플러」 → reports/34~43_*.ipynb
==========================================================================================
한 편 = 중심 메시지 하나. 옛 `report07_microdoppler.ipynb` 한 편에 일곱 메시지가 눌려 있었고,
그 §들이 여기서 자기 편을 갖는다. 그림·숫자·문장은 그대로 옮겼다.

    34 md-paths-doppler   스톡 Paths.doppler 로는 안 나온다        (신규)
    35 md-slowtime        슬로타임 복소열을 무엇으로 만드나         (report07 §1 · §1b)
    36 md-two-engines     두 엔진이 어디서 겹치고 어디서 갈리나     (report07 §1a)
    37 md-rpm             회전수가 같으면 무늬는 시간에 못 변한다   (report07 §2)
    38 md-occlusion       동체가 날개를 가리면                      (report07 §3)
    39 md-blade-vs-body   블레이드는 강하다 — 동체가 덮는다         (report07 §4a)
    40 md-attitude        지상 레이더는 배를 본다                   (report07 §4)
    41 md-calibration     판정 잣대를 먼저 교정했다                 (신규)
    42 md-ray-budget      두 기체가 갈리는 이유는 광선예산이다      (신규)
    43 md-prf             상시 신호는 블레이드 통과율까지다         (report07 §5)

⭐ 편 35 는 report07 §1 의 문체를 그대로 옮긴 본보기다 — 다른 부가 이 편을 보고 맞춘다.
옛 빌더 `src/make_report07_microdoppler.py` 는 Verify 가 대조할 때까지 그대로 둔다.

실행
    cd /workspace/sionna
    PYTHONPATH=src ~/.venvs/py312/bin/python src/build_part07_microdoppler.py

⚠ GPU 도 Sionna 도 필요 없다 — JSON 을 읽어 노트북을 조립할 뿐이다.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np      # ⛔깊이 p-p 는 표본 수 N 에 딸려 자란다 — 그 딸림을 재서 본문에 적는다

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (_HERE, os.path.join(_ROOT, "benchmark")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from md_mapstyle import ARM_PO, ARM_SBR, ARM_SIONNA          # noqa: E402
from report_style import (BREAK, ContractError, build_notebook,    # noqa: E402
                          caption, fetch, header, md, next_steps, num, table,
                          table_from)

# --------------------------------------------------------------------------- #
#  앵커 해결기 — 번호는 실행 계획이 정본이다
# --------------------------------------------------------------------------- #
_PLAN = os.path.join(_ROOT, "outputs", "restruct_exec_plan.json")


def _registry() -> dict:
    with open(_PLAN, encoding="utf-8") as f:
        plan = json.load(f)
    return {r["anchor"]: (str(r["no"]), r["title_ko"]) for r in plan["reports"]}


REG = _registry()


def ref(anchor: str, short: str | None = None) -> str:
    if anchor not in REG:
        raise ContractError(f"모르는 앵커: {anchor!r} — 실행 계획에 없다")
    no, title = REG[anchor]
    return f"[편 {no} «{short or title}»]({no}_{anchor}.ipynb)"


# --------------------------------------------------------------------------- #
#  근거 JSON
# --------------------------------------------------------------------------- #
TRI = "outputs/report07_three_engines.json"
MDP = "outputs/report00_microdoppler.json"      # 두 엔진 대조 + 정반사 인구조사
MDB = "outputs/report15b_microdoppler.json"     # ⭐재계산 (로터별 rpm · 가림 단일축 · 긴 창)
RNG = "outputs/md_range_sweep.json"             # 상시 기준신호 반복률 대 필요 PRF
PRB = "outputs/report15_probe.json"             # 스톡 Paths.doppler 실측
VRD = "outputs/report15_verdict.json"           # 판정 격자 + 교정
NUL = "outputs/report15_null_control.json"      # 널 팔
GEO = "outputs/report15_verdict_geomref.json"   # 이상 점산란자 기준
POC = "outputs/report15_po_control.json"        # PO 대조군 + 감사
ATK = "outputs/report15_attack_stats.json"      # 적대검증 렌즈 1
SPP = "outputs/report15_attack_spp_ladder.json"
SGC = "outputs/sbr_grid_convergence.json"       # 격자 사다리 — 생산·위상고정·얼림
FSL = "outputs/freeze_signal_loss.json"         # ⭐렌즈 B — 얼리기가 «신호» 도 깎았나
FPS = "outputs/freeze_plate_sensitivity.json"   # ⭐판 한 장에 절대 dB 가 얼마나 걸리나
SER = "outputs/report15b_series.npz"            # ⭐슬로타임 복소열 원본 — 잣대를 stride 로 흔든다
OOB = "outputs/outofband_power.json"            # ⭐대역밖 전력의 잣대(절대·평활 없음)
BFL = "outputs/report15_blade_flash_ladder.json"  # ⭐프롭 정반사 — 예산 축과 앙각 축
DEP = "outputs/report07_depth_robust.json"      # ⭐깊이를 두 자로(p-p·p5~p95) — 06_2 와 같은 규약
SER = "outputs/report15b_series.npz"            # 재계산의 슬로타임 복소열 — 깊이의 N 딸림을 잰다
TRZ = "outputs/report07_three_engines.npz"      # 세 엔진의 슬로타임 복소열 (같은 용도)

OUT = os.path.join(_ROOT, "reports", "_parts")   # ⭐조각 — 사람이 읽는 문서는 src/build_volumes.py 가 묶은 권이다
FIG = "../outputs/figures"

#: 헤드라인 칸 — 메쉬가 깨끗하고(프롭·벨 겹침 0.01 %) 1차 실측 표적이다.
LEAD = "cells.matrice4e/belly"

REPRO_15B = dict(
    cmd=["PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report15b_microdoppler_recompute.py",
         "PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report15b_stamp_provenance.py",
         "PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/build_report15b_figs.py"],
    out=[MDB, "outputs/report15b_series.npz"],
    runtime="약 25 분 (GPU 1장 — 광선 추적이 6칸 × 4팔)",
    note="메쉬 지문(`mesh_provenance`)은 도장 스크립트 "
         "`benchmark/report15b_stamp_provenance.py` 가 찍는다 — ⚠ 지금 원장의 최상위 키는 "
         "`_meta` 와 `cells` 둘이고, 지문은 그 스크립트를 돌린 다음 세대부터 실린다")


def _n(key: str, src: str = MDB, fmt: str | None = None, unit: str = "") -> str:
    return num(None, (src, key), fmt, unit)


#: 세 팔의 «전체 전력 중 f_tip 밖 몫» — 원장의 행 순서에 안 걸리게 라벨로 찾는다.
_OOB_ROW = {r["label"]: i for i, r in enumerate(fetch((OOB, "three_engines")))}


def _grid_state_line() -> str:
    """이 편의 맵이 어떤 광선 격자로 풀렸나 — 원장의 표식에서 읽는다."""
    if not bool(fetch((TRI, "_meta.grid_frozen")) or False):
        return ("⚠ 이 편의 맵은 아직 생산 격자로 계산돼 있다 — 커널의 `grid_ref` 배선을 하류가 "
                "안 넘긴다.")
    return ("⭐ **이 편의 맵은 그 얼린 판으로 다시 났다.** 옛 판과의 전후 비교"
            "(레벨 · 변조 깊이 · 대역밖 전력 · 가산성)는 6 권의 «광선 격자를 어디에 매나» 절이 "
            "낸다. ⚠ 아직 옛 판인 것은 바이스태틱 스윕 원장과 PO 대조 원장이다.")


def _oob_pct(label: str) -> str:
    """대역밖 몫을 %로 — 값이 아주 작으면 자릿수를 늘린다(0.00 % 로 뭉개지 않는다)."""
    v = float(fetch((OOB, f"three_engines[{_OOB_ROW[label]}].frac_of_total")))
    return _n(f"three_engines[{_OOB_ROW[label]}].frac_of_total", OOB,
              "{:.5%}" if v < 1e-4 else "{:.2%}")


def _L(key: str, fmt: str | None = None, unit: str = "") -> str:
    return _n(f"{LEAD}.{key}", MDB, fmt, unit)


#: 헤드라인 칸의 계열 키 앞머리 — 원장 키에서 `cells.` 접두만 뗀 것이다.
LEAD_SER = LEAD.removeprefix("cells.")


def _win() -> dict:
    """헤드라인 칸이 **실제로 돌린 창** — 원장에 적힌 이름값과 다르다.

    ⛔ `benchmark/report15b_microdoppler_recompute.py:119` 는
       `n_t = int(min(MAX_SAMPLES, round(prf * dur)))` 이고 `MAX_SAMPLES = 6000`(같은 파일 105)
       인데, 같은 함수가 `duration_s` · `doppler_resolution_hz` · `bins_to_ftip` 은 **자르기 전**
       이름값(`dur = N_FLASH_PERIODS/f_flash`, `f_flash/N_FLASH_PERIODS`)으로 적는다(121-123).
       matrice4e 세 칸은 요청이 9,954 표본이라 상한에 걸렸고, 그래서 그 세 키는 돌아간 적 없는
       창의 값이다. 여기서 원장의 `n_t` · `prf` · `f_tip` · `f_flash` 로 돌아간 창을 다시 낸다 —
       나온 칸 간격은 저장된 스펙트럼 축(`outputs/report15b_series.npz : */spec_f`)과 같다.
    """
    prf = float(fetch((MDB, f"{LEAD}.physics.prf")))
    n_t = float(fetch((MDB, f"{LEAD}.physics.n_t")))
    dur, res = n_t / prf, prf / n_t
    dur_nom = float(fetch((MDB, f"{LEAD}.physics.duration_s")))
    return dict(dur=dur, res=res,
                bins=float(fetch((MDB, f"{LEAD}.physics.f_tip"))) / res,
                periods=dur * float(fetch((MDB, f"{LEAD}.physics.f_flash"))),
                dur_nom=dur_nom, req_n=int(round(prf * dur_nom)),
                periods_nom=float(fetch((MDB, "_meta.n_flash_periods"))))


def _shrink(src: str, key: str, n_sub: int) -> dict:
    """같은 창을 **등간격으로 솎아** N 개만 쓴 깊이의 중앙값 — 씨앗이 없다(오프셋 전부의 중앙값).

    ⛔ 새 지표가 아니다. p-p(max−min)가 표본 수 N 에 딸려 자라는지를 **재서 본문에 적기 위한**
      것이고, 본문이 인용하는 자는 원장의 `p5p95_db` · `modulation_std_db` 다.
    """
    db = 20.0 * np.log10(np.abs(np.asarray(fetch((src, key)))) + 1e-30)
    k = len(db) // int(n_sub)
    sub = [db[o::k][:int(n_sub)] for o in range(k)]
    return dict(ptp=float(np.median([np.ptp(s) for s in sub])),
                p5p95=float(np.median([np.percentile(s, 95) - np.percentile(s, 5)
                                       for s in sub])),
                std=float(np.median([s.std() for s in sub])))


def _shrink_arm(arm: str, n_sub: int) -> dict:
    return _shrink(SER, f"{LEAD_SER}/{arm}/E", n_sub)


def _n_pending(key: str, src: str, fmt: str | None = None, unit: str = "") -> str:
    """⭐**그림 빌더가 나중에 덧쓰는 칸** — 원장이 재계산 중이면 그 자리가 잠시 비어 있다.

    빌드를 죽이는 대신 «재계산 대기» 로 적는다. 원장이 채워지면 이 빌더를 다시 도는 것만으로
    숫자가 돌아온다. ⚠ 이 완충은 **그런 칸에만** 쓴다 — 오타를 숨기는 데 쓰면 안 된다.
    """
    try:
        return _n(key, src, fmt, unit)
    except ContractError:
        return "⏳재계산 대기"


def _fig(no: int, stem: str, question: str) -> list[str]:
    return [f"![{stem}]({FIG}/{stem}.png)", "", caption(no, question)]


# =========================================================================== #
#  편 34 — 스톡 Paths.doppler 로는 안 나온다
# =========================================================================== #
def blocks_34() -> list:
    B = "branch1_paths_doppler.evidence"
    P = "airframes.matrice4e.A_doppler"

    return [
        header(
            num=34,
            title="스톡 Paths.doppler 로는 블레이드 변조가 안 나온다 — "
                  "SceneObject.velocity 가 객체당 강체 1벡터다",
            did="설치본 Sionna 의 장면 객체에 속도를 직접 넣고 경로 도플러를 읽어 자유도를 셌다.",
            results=[
                f"장면 객체 하나가 갖는 속도 자유도는 "
                f"{_n(B + '.max_dof', VRD, '{:.0f}', '개')} 다 — 평행이동 세 성분이고, "
                f"회전 자유도는 그 밖이다.",

                f"정지 장면(**Mini 2**)에서 도플러가 0 이 아닌 경로는 "
                f"{_n(B + '.doppler_nonzero_paths_static_scene', VRD, '{:.0f}', '개')} "
                f"(전체 {_n(B + '.n_paths', VRD, '{:.0f}', '개')}) — 배선 자체는 정상이다.",

                f"**Matrice 4E** 의 프롭 그룹에 강체속도를 주면 **표적 경유 경로** "
                f"{_n(P + '.rigid_prop_velocity.n_target_paths', PRB, '{:.0f}', '개')} 가 "
                f"모두 같은 부호로 몰린다 — 크기는 강체 투영에 따라 0 ~ "
                f"{_n(P + '.rigid_prop_velocity.doppler_max_hz', PRB, '{:.1f}', 'Hz')} 로 퍼지고, "
                f"그 최대가 강체 예측 "
                f"{_n(P + '.rigid_prop_velocity.predicted_rigid_hz', PRB, '{:.1f}', 'Hz')} 와 "
                f"같은 자리에 선다.",

                f"전진날과 후퇴날이 갈리려면 그 둘이 반대 부호를 받아야 하는데, 자유도 "
                f"{_n(B + '.max_dof', VRD, '{:.0f}')} 개짜리 벡터 하나가 그것을 표현한다.",

                f"그래서 남는 길은 하나다 — 시간표본마다 자세를 새로 놓고 다시 쏘는 것이고, "
                f"그 절차가 " + ref("md-slowtime", "슬로타임 복소열") + " 이다.",
            ],
            method=[
                ("자유도 세기",
                 "설치본 `sionna.rt.SceneObject.velocity` 의 성분 수를 부품 객체마다 직접 읽었다"),
                ("강체 주입 시험",
                 "프롭 그룹에만 속도 (0, 0, 30) m/s 를 주고 `Paths.doppler` 의 고유값을 셌다"),
                ("대조",
                 "같은 장면을 정지 상태로 한 번 더 추적해 도플러가 0 인지 확인했다"),
                ("무엇을 안 물었나",
                 "Sionna 가 «회전하는 기하의 왕복 위상» 을 따라가는지는 이 시험의 밖이다 — "
                 + ref("md-two-engines", "두 엔진") + " 이 그것을 잰다"),
            ],
            repro=dict(
                cmd="PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report15_probe.py",
                out=[PRB],
                runtime="약 7 분 (GPU 1장)"),
        ),

        md("## 무엇을 물었나", "",
           "Sionna 는 장면 객체에 속도를 주면 경로마다 도플러를 계산해 준다. 그 기능만으로 "
           "**블레이드 마이크로도플러**(도는 날개가 만드는 변조)가 나오는지가 첫 갈래다.", "",
           "나온다면 로터를 돌리는 비싼 길을 건너뛴다. 안 나온다면 시간표본마다 자세를 다시 "
           "놓고 광선을 다시 쏘는 길로 간다. 두 길의 비용 차이가 커서 먼저 확인했다."),

        md("## 자유도를 세면 답이 정해진다", "",
           table(["무엇을", "기체", "값"], [
               ["객체당 속도 자유도", "Mini 2", _n(B + ".max_dof", VRD, "{:.0f}", "개")],
               ["정지 장면의 0 아닌 도플러", "Mini 2",
                _n(B + ".doppler_nonzero_paths_static_scene", VRD, "{:.0f}", "개")],
               ["강체속도 주입 시 표적 경유 경로", "Matrice 4E",
                _n(P + ".rigid_prop_velocity.n_target_paths", PRB, "{:.0f}", "개")],
               ["그 경로의 도플러 최대", "Matrice 4E",
                _n(P + ".rigid_prop_velocity.doppler_max_hz", PRB, "{:.1f}", "Hz")],
               ["강체 운동학이 예측하는 값", "Matrice 4E",
                _n(P + ".rigid_prop_velocity.predicted_rigid_hz", PRB, "{:.1f}", "Hz")],
           ]), "",
           f"프롭 전체에 강체속도 하나를 주면 표적 경유 경로가 전부 같은 부호로 몰리고, 크기는 "
           f"각 경로의 강체 투영에 따라 0 부터 표의 최대값까지 퍼진다 — 그 최대값이 강체 예측과 "
           f"같은 자리에 선다. 블레이드 전진/후퇴가 갈라지려면 부호가 반대인 두 값이 나와야 "
           f"하는데, 이 표의 도플러는 한 부호로 몰린다."),

        md("## 표의 두 줄은 잣대가 다르다", "",
           f"«표적 경유 경로» 는 `{PRB} : {P}.rigid_prop_velocity.n_target_paths` 이고, 그 키는 "
           "표적의 어느 부품이든 스친 경로를 전부 센다 — 프롭만 센 수는 따로 세야 한다. "
           "판정은 그대로 선다: 경로 집합이 넓을수록 부호가 갈릴 기회가 많은데도 도플러가 "
           "한 부호로 몰린다.", "",
           "위 두 줄은 **Mini 2**, 아래 세 줄은 **Matrice 4E** 다. 자유도 세기는 두 기체에서 "
           f"같은 답을 낸다 — `{PRB} : airframes.*.A_doppler.velocity_dof_per_object` 의 모든 "
           "부품이 평행이동 세 성분뿐이라, 판정이 기체 선택에 안 걸린다."),

        md("## 이것은 구현 문제가 아니라 자료구조 문제다", "",
           "속도가 객체당 벡터 하나라는 것은 «그 객체가 강체로 평행이동한다» 는 뜻이다. "
           "회전하는 프로펠러는 같은 객체 안에서 점마다 속도가 다르고, 그 차이를 담을 자리가 "
           "벡터 하나 밖에 있다.", "",
           "부품을 날개 하나하나로 쪼개도 마찬가지다 — 날개 하나 안에서도 뿌리와 끝의 속도가 "
           "다르고, 그 차이가 바로 날개끝 확산을 만드는 양이다.", "",
           f"판정 문장은 산출물에 그대로 있다 — `{VRD} : branch1_paths_doppler.answer`."),

        next_steps([
            ("시간표본마다 자세를 새로 놓고 다시 쏜다",
             "블레이드 변조를 만드는 유일한 길이 실제로 작동하는지가 갈린다",
             ref("md-slowtime", "슬로타임 복소열")),
            ("Sionna 가 회전 기하의 왕복 위상을 따라가는지 우리 커널과 맞댄다",
             "위상을 광선 엔진에 맡길 수 있는지가 정해진다",
             ref("md-two-engines", "두 엔진")),
        ]),
    ]


# =========================================================================== #
#  편 35 — 슬로타임 복소열  ⭐문체 본보기
# =========================================================================== #
def blocks_35() -> list:
    _W = _win()      # ⛔돌아간 창. 원장의 duration_s·doppler_resolution_hz 는 요청값이다
    return [
        header(
            num=35,
            title="시간표본마다 자세를 새로 놓고 다시 쏘아 슬로타임 복소열을 만든다",
            did="로터 위상을 시간표본마다 다시 놓고 광선을 다시 쏘아 되돌아오는 복소 신호의 "
                "느린 시간축을 만들었다.",
            results=[
                f"헤드라인 칸은 {_L('name')} 를 배 쪽에서 본 것이다 — 방위 "
                f"{_L('az_deg', '{:.0f}', '도')} · 앙각 {_L('el_deg', '{:.0f}', '도')}.",

                f"호버 {_L('physics.rpm', '{:.0f}', 'rpm')} 에서 운동학이 예측하는 날개끝 "
                f"주파수는 {_L('physics.f_tip', '{:.0f}', 'Hz')}, 블레이드 통과율은 "
                f"{_L('physics.f_flash', '{:.1f}', 'Hz')} 다.",

                f"표본율 {_L('physics.prf', '{:.0f}', 'Hz')} 로 "
                f"{_L('physics.n_t', '{:,.0f}', '개')} 를 이어 붙여 창 길이 "
                f"{_W['dur']:.3f} s 를 얻었다 — 블레이드 {_W['periods']:.1f} 주기다"
                f"(원장의 `physics.n_t` ÷ `physics.prf`).",

                f"그 창이 주는 도플러 분해능은 {_W['res']:.2f} Hz 이고, 날개끝까지 "
                f"{_W['bins']:.0f} 칸이 든다. ⛔ 원장의 `duration_s`"
                f"({_L('physics.duration_s', '{:.3f}', 's')}) · `doppler_resolution_hz` · "
                f"`bins_to_ftip` 은 «{_W['periods_nom']:.0f} 블레이드 주기» 요청값"
                f"({_W['req_n']:,} 표본)으로 적혀 있으니 그대로 인용하지 마라 — matrice4e 세 칸이 "
                f"`MAX_SAMPLES = 6000` 상한에 잘렸다"
                f"(`benchmark/report15b_microdoppler_recompute.py:105,119`).",

                f"조립을 싸게 만든 것은 `src/articulated_fast.py` 다 — 드론을 한 번 짓고 "
                f"위상마다 행렬곱만 한다.",
            ],
            method=[
                ("슬로타임 복소열",
                 "시간표본마다 로터 위상을 다시 놓고 광선을 다시 쏜다 — 위상 하나짜리 표를 "
                 "쓰지 않으므로 로터마다 회전수를 다르게 줄 수 있다"),
                ("무엇이 그것을 가능하게 했나",
                 "`src/articulated_fast.py` — 드론을 한 번 짓고 위상마다 행렬곱만 한다. "
                 "정점 배열이 옛 함수와 비트 단위로 같다"),
                ("도플러 분해능",
                 "돌아간 창의 길이가 정한다 — `physics.n_t` ÷ `physics.prf` = "
                 f"{_W['dur']:.3f} s 이고 칸 간격은 그 역수 {_W['res']:.2f} Hz 다. ⛔ 원장의 "
                 "`doppler_resolution_hz` 는 자르기 전 요청 창의 값이라, 이 편은 그 자리에 "
                 "돌아간 창의 값을 적는다"),
                ("헤드라인 기체 선택",
                 "DJI Matrice 4E — 프롭·벨 겹침이 0.01 % 로 정리됐고 1차 실측 표적이다"),
            ],
            prereq=[("앞 편", ref("md-paths-doppler", "스톡 도플러") + " — 왜 이 길로 가나")],
            repro=REPRO_15B,
        ),

        md("## 무엇을 재는가", "",
           "표적이 제자리에 떠 있어도 날개는 돈다. 날개 표면의 점들이 시간에 따라 자리를 "
           "바꾸므로 왕복 위상이 변조되고, 그것이 되돌아오는 신호의 느린 시간축에 실린다. "
           "우리는 그 열을 **시간표본마다 자세를 새로 놓고 광선을 다시 쏘아** 만든다.", "",
           "왜 그렇게까지 하는가. 로터마다 회전수를 다르게 주려면 드론 전체 자세가 각도 하나의 "
           "함수가 아니게 되고, 그러면 «위상 하나짜리 표를 미리 만들어 두고 조회한다» 는 지름길이 "
           "막힌다. 조립을 싸게 만들어 그 지름길을 버렸다."),

        md("## 헤드라인 칸의 운동학", "",
           table(["무엇을", "값"], [
               ["기체 · 자세", _L("name") + " · 배 쪽"],
               ["방위 · 앙각", _L("az_deg", "{:.0f}", "°") + " · " + _L("el_deg", "{:.0f}", "°")],
               ["호버 회전수", _L("physics.rpm", "{:.0f}", "rpm")],
               ["날개끝 속도", _L("physics.v_tip", "{:.2f}", "m/s")],
               ["날개끝 주파수", _L("physics.f_tip", "{:.0f}", "Hz")],
               ["블레이드 통과율", _L("physics.f_flash", "{:.1f}", "Hz")],
           ])),

        md("## 창이 분해능을 정한다", "",
           table(["무엇을", "⭐돌아간 창", "⛔원장에 적힌 요청값"], [
               ["표본율", _L("physics.prf", "{:.0f}", "Hz"), "같음"],
               ["표본 수", _L("physics.n_t", "{:,.0f}", "개"),
                f"{_W['req_n']:,} 개 — `MAX_SAMPLES = 6000` 에서 잘렸다"],
               ["창 길이", f"{_W['dur']:.3f} s (블레이드 {_W['periods']:.1f} 주기)",
                _L("physics.duration_s", "{:.3f}", "s")
                + f" — `duration_s` ({_W['periods_nom']:.0f} 주기)"],
               ["도플러 분해능", f"{_W['res']:.2f} Hz",
                _L("physics.doppler_resolution_hz", "{:.2f}", "Hz")
                + " — `doppler_resolution_hz`"],
               ["날개끝까지 든 칸 수", f"{_W['bins']:.0f} 칸",
                _L("physics.bins_to_ftip", "{:.0f}", "칸") + " — `bins_to_ftip`"],
           ]), "",
           "분해능은 «창에 든 블레이드 주기 수» 가 정한다. 같은 창 안에서 표본을 촘촘히 해도 "
           "칸이 좁아지지 않으므로, 능선을 가르려면 창을 늘린다.", "",
           f"⛔ **본문이 쓰는 것은 가운데 열이다.** 오른쪽 열은 스크립트가 "
           f"«{_W['periods_nom']:.0f} 블레이드 주기» 를 요청해 계산한 이름값이고, 실제 실행은 "
           f"요청 {_W['req_n']:,} 표본이 `MAX_SAMPLES = 6000` 안전 상한에 걸려 "
           f"{_W['periods']:.1f} 주기에서 끊겼다 — `n_t` 만 상한을 타고 `duration_s` · "
           f"`doppler_resolution_hz` · `bins_to_ftip` 셋은 자르기 전 값으로 남는다"
           f"(`benchmark/report15b_microdoppler_recompute.py:105,119,121-123`). 가운데 열의 "
           f"{_W['res']:.2f} Hz 는 저장된 스펙트럼 축의 칸 간격과 같다"
           f"(`outputs/report15b_series.npz : {LEAD_SER}/B_sbr_spread/spec_f`).", "",
           "⚠ 이 어긋남은 **matrice4e 세 칸에만** 있다 — mini5pro 세 칸은 "
           + _n("cells.mini5pro/belly.physics.n_t", MDB, "{:,.0f}", "표본")
           + " 이라 상한 아래이고, 그 칸의 원장 값 셋은 돌아간 창과 0.01 % 안에서 같다."),

        md("## 전처리를 어떻게 했는가", "",
           "마이크로도플러 그림은 전처리가 답을 바꾼다. 그래서 규약을 적어 둔다.", "",
           "| 단계 | 우리가 한 것 | 왜 |",
           "|---|---|---|",
           "| 채널 | 전체 드론과 프로펠러만을 따로 | 동체가 블레이드를 덮는다 |",
           "| 0 도플러 | **살린다** | 동체 선이 읽기의 기준이다 |",
           "| 조각 길이 | 블레이드 13 주기 | 능선 사이에 13 빈이 들어 빗살이 안 뭉갠다 |",
           "| 창·제로패딩 | Hann · 4배 | 누설을 줄이고 주파수축을 매끈하게 |",
           "| 색역 | 60 dB | 동체 선을 0 dB 로 두고 능선을 그 아래에서 읽는다 |",
           "| 정규화 | 한 그림 안에서 공통 | 두 패널을 나란히 놓고 비교할 수 있게 |"),

        md("## 검출 축의 전처리는 따로 있다", "",
           "정적 성분을 지우는 슬로타임 고역통과(MTI)는 `src/microdoppler_proc.py` 에 따로 "
           "있다 — **검출 축**에서 쓴다. ⚠ 그 노치는 호버하는 표적의 동체도 함께 지우므로 "
           "탐지에서는 대가가 된다.", "",
           "⚠ 선행 구현의 **처리 파라미터**는 그 시스템의 자원격자에 맞춰진 값이라 그대로 "
           "옮기지 않았다. 우리가 가져온 것은 그림을 읽는 순서이고, 차단주파수 같은 것은 "
           "우리 물리에서 정했다."),

        next_steps([
            ("같은 절차를 두 엔진에 태워 무늬를 맞댄다",
             "위상을 광선 엔진에 맡기고 세기를 PO 커널에 맡기는 분업이 근거를 얻는다",
             ref("md-two-engines", "두 엔진")),
            ("로터마다 회전수를 다르게 준다",
             "무늬가 시간에 따라 변하는 데 무엇이 필요한지가 갈린다",
             ref("md-rpm", "회전수 축")),
        ]),
    ]


# =========================================================================== #
#  편 36 — 두 엔진
# =========================================================================== #
def blocks_36() -> list:
    T = "tail_excess.by_airframe"
    G = "geometric_phase_reference.by_airframe"
    #: ⛔ p-p 가 표본 수에 딸리는지를 재서 표 아래에 적는다 — 같은 계열, 등간격 솎기.
    #  전체 열 길이는 원장에서 든다 — 하드코딩하지 않는다.
    _NFULL = int(fetch((DEP, "engines_meta.n")))
    _S64, _S512, _SFULL = (_shrink(TRZ, "sionna", n) for n in (64, 512, _NFULL))

    return [
        header(
            num=36,
            title="두 엔진이 날개끝 주파수 아래에서 겹치고 그 위에서 갈린다",
            did="같은 로터 위상 스텝 절차를 스톡 Sionna 엔진과 우리 PO 커널 두 곳에 태워 "
                "같은 칸에서 나온 무늬를 맞댔다.",
            results=[
                f"운동학이 예측한 날개끝 주파수 **아래**에서 두 빗살이 겹친다 — 변조 깊이가 "
                f"Sionna {_n('rows[1].ptp_sionna_db', MDP, '{:.2f}', 'dB')} · 순수 PO "
                f"{_n('rows[1].ptp_po_db', MDP, '{:.2f}', 'dB')} 다"
                f"(**nose · {_n('_meta.range_m', MDP, '{:.0f}', 'm')} 한 칸**).",

                f"그 위에서 갈린다 — 기하 절벽 너머 꼬리의 최대값이 Mini 2 에서 Sionna "
                f"{_n(T + '.mini2.sionna_tail_max_db_median', VRD, '{:.2f}', 'dB')} 대 순수 PO "
                f"{_n(T + '.mini2.po_tail_max_db_median', VRD, '{:.2f}', 'dB')} 다"
                f"(**자세 5 × 거리 1·3·10 m = "
                f"{_n(T + '.mini2.n_cells', VRD, '{:.0f}', '칸')} 의 중앙값**).",

                f"Sionna 의 빗이 **기하에서 온다** — 산란 물리를 전부 빼고 왕복 위상만 더한 "
                f"기준과 겹치면 Mini 2 "
                f"{_n(G + '.mini2.n_near_within_1_bin', VRD, '{:.0f}')}/"
                f"{_n(G + '.mini2.n_near_cells', VRD, '{:.0f}')} 칸이 ±1 조화 안에서 일치한다"
                f"(**근거리 1·3 m 칸**).",

                f"빗 모양 코사인 중앙값은 Mini 2 "
                f"{_n(G + '.mini2.comb_shape_cosine_median', VRD, '{:.4f}')} · Matrice 4E "
                f"{_n(G + '.matrice4e.comb_shape_cosine_median', VRD, '{:.4f}')} 다"
                f"(**같은 15 칸의 중앙값**).",

                f"⭐ 아래쪽에서 겹친다는 것이 «위상은 광선 엔진이 맞게 낸다» 의 근거이고, "
                f"위쪽에서 갈린다는 것이 «세기는 PO 커널이 맡는다» 의 근거다.",
            ],
            method=[
                ("같은 격자",
                 "로터 위상 스텝·거리·자세·재질·주파수를 전부 같게 두고 엔진 하나만 바꿨다"),
                ("팔 셋 · 이 편의 낱말",
                 f"**S** = {ARM_SIONNA} · **B** = {ARM_SBR} · **P** = {ARM_PO}. "
                 "절마다 어느 팔이 재었는지를 이 세 이름으로 적는다"),
                ("Sionna 팔 (S)",
                 "스톡 `sionna.rt.PathSolver` — h = Σ a_p·exp(−j2πf_c τ_p). "
                 "`Paths.cir()` 은 절대위상을 지우므로 쓰지 않는다"),
                ("순수 PO 팔 (P)",
                 "`src/microdoppler_nearfield.py` — 평면파/구면파 PO 표면적분. 광선 격자를 "
                 "안 쓰고 가림도 안 푼다"),
                ("SBR 팔 (B)",
                 "`src/rcs_sbr.py::sbr_field` — 광선 격자로 보이는 면을 골라 PO. 그림 2 의 "
                 "가운데 칸이 이 팔이고, 결과 1~4 의 두 열은 S 와 P 다"),
                ("통계 단위",
                 "결과 1 은 nose · 3 m **한 칸**, 결과 2~4 는 자세 5 × 거리 1·3·10 m = "
                 "**15 칸의 중앙값**, 그림 2 는 belly · 앙각 −15° · 3 m **한 칸**이다"),
                ("비교 가능한 양만",
                 "절대 스케일과 기준위상이 다르므로 상수 복소배에 불변인 양(AC 상관 · dB ptp · "
                 "하모닉 스펙트럼)만 맞댔다"),
                ("기하 기준",
                 "같은 메쉬로 산란 물리를 빼고 왕복 위상만 더한 빗 — 움직이는 기하가 "
                 "원리적으로 낼 수 있는 도플러 빗이다"),
            ],
            prereq=[("앞 편", ref("md-slowtime", "슬로타임 복소열") + " — 두 엔진에 태운 절차")],
            repro=dict(
                cmd=["PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report15_po_control.py",
                     "PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report15_verdict_geomref.py",
                     "PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report15_verdict.py"],
                out=[POC, GEO, VRD],
                runtime="약 30 분 (GPU 1장)"),
        ),

        md("## 같은 로터를 두 엔진이 돌린다", "",
           *_fig(1, "report07_f2",
                 "Sionna 자체 엔진과 우리 순수 PO 대조팔이 같은 로터에서 같은 무늬를 내는가?"),
           "로터 위상을 스텝하고 매번 다시 추적하는 같은 절차를 **두 팔**에 태웠다 — "
           f"**S** = {ARM_SIONNA} 와 **P** = {ARM_PO} 다. 이 그림은 **nose · 3 m 한 칸**이고 "
           "기선은 0.2 m 다(준-모노스태틱).", "",
           "운동학이 예측한 날개끝 주파수 **아래**에서 두 빗살이 겹친다. 가림을 푸는 SBR 팔(B)은 "
           "이 그림 밖에 있고, 아래 «세 엔진을 같은 격자에» 절이 그 팔을 세운다."),

        md("## 그 위에서 갈린다", "",
           "잰 팔은 **S** 와 **P** 둘이고, 셋째 열은 산란 물리를 뺀 기하 기준이다 — "
           f"**자세 5 × 거리 1·3·10 m = {_n(T + '.mini2.n_cells', VRD, '{:.0f}', '칸')} 의 "
           "중앙값**이다.", "",
           table(["기체", "S 꼬리 최대", "P 꼬리", "기하 기준 꼬리"], [
               ["Mini 2",
                _n(T + ".mini2.sionna_tail_max_db_median", VRD, "{:.2f}", "dB"),
                _n(T + ".mini2.po_tail_max_db_median", VRD, "{:.2f}", "dB"),
                _n(T + ".mini2.geometry_tail_max_db_median", VRD, "{:.2f}", "dB")],
               ["Matrice 4E",
                _n(T + ".matrice4e.sionna_tail_max_db_median", VRD, "{:.2f}", "dB"),
                _n(T + ".matrice4e.po_tail_max_db_median", VRD, "{:.2f}", "dB"),
                _n(T + ".matrice4e.geometry_tail_max_db_median", VRD, "{:.2f}", "dB")],
           ]), "",
           "Sionna 의 꼬리가 PO·기하 기준보다 뚜렷하게 높게 남는다. 그 꼬리는 블레이드가 만든 "
           "것이 아니므로, 가장자리를 자동으로 찾는 검출기는 물리적이지 않은 자리를 가장자리라고 "
           "보고한다. 그 꼬리의 원인은 "
           + ref("md-ray-budget", "광선예산") + " 이 잰다."),

        md("## 세 엔진을 같은 격자에 태우면", "",
           *_fig(2, "report07_f5",
                 "Sionna·SBR·PO 를 같은 슬로타임 격자에 태우면 같은 무늬가 나오는가?"),
           f"같은 기체·자세·주파수·PRF·로터별 회전수로 세 팔을 돌렸다 — "
           f"{_n('_meta.n', TRI, '{:.0f}', '표본')} @ PRF "
           f"{_n('_meta.prf_hz', TRI, '{:.0f}', 'Hz')} = "
           f"{_n('_meta.blade_periods', TRI, '{:.0f}')} 블레이드 주기. 이 그림과 표는 "
           f"**belly · 앙각 {_n('_meta.el_deg', TRI, '{:.0f}', '°')} · "
           f"{_n('_meta.range_m', TRI, '{:.0f}', 'm')} 한 칸**이다.", "",
           table(["팔", "무엇으로 쟀나", "깊이 p-p ⛔", "깊이 p5~p95 ⭐", "비",
                  "전체 전력 중 날개끝 밖", "무늬"], [
               ["S", ARM_SIONNA, _n("engines.sionna.ptp_db", DEP, "{:.1f}", "dB"),
                _n("engines.sionna.p5p95_db", DEP, "{:.1f}", "dB"),
                _n("engines.sionna.ptp_over_p5p95", DEP, "{:.1f}", "배"),
                _oob_pct("sionna"),
                "얼룩이 대역을 채우고 날개끝 주파수 밖에도 남는다"],
               ["B", ARM_SBR, _n("engines.sbr.ptp_db", DEP, "{:.1f}", "dB"),
                _n("engines.sbr.p5p95_db", DEP, "{:.1f}", "dB"),
                _n("engines.sbr.ptp_over_p5p95", DEP, "{:.1f}", "배"),
                _oob_pct("sbr"),
                "빗살이 또렷하다 — ⚠순수 PO 보다는 여전히 "
                + _n("three_engines_ranking.new_P_out_absolute.sbr_over_po_db", OOB,
                     "{:.0f}", "dB") + " 위다"],
               ["P", ARM_PO, _n("engines.po.ptp_db", DEP, "{:.1f}", "dB"),
                _n("engines.po.p5p95_db", DEP, "{:.1f}", "dB"),
                _n("engines.po.ptp_over_p5p95", DEP, "{:.1f}", "배"),
                _oob_pct("po"),
                "빗살이 가장 좁고 날개끝에서 절벽처럼 잘린다"],
           ]), "",
           "⛔ **p-p 열을 물리량으로 인용하지 마라 — 특히 S 의 "
           + _n("engines.sionna.ptp_db", DEP, "{:.1f}", "dB")
           + " 는 표본 N 개의 max−min 이라 N 에 딸려 자란다:** 같은 "
           + _n("engines_meta.n", DEP, "{:,.0f}", "표본") + " 열을 등간격으로 솎아 재면 S 의 "
           + f"p-p 중앙값이 N=64 {_S64['ptp']:.1f} → 512 {_S512['ptp']:.1f} → {_NFULL:,} "
             f"{_SFULL['ptp']:.1f} dB 로 **전체 열까지 계속 자라고**, 같은 솎기의 p5~p95 는 "
             f"{_S64['p5p95']:.1f} → {_SFULL['p5p95']:.1f} dB 로 붙어 있다. 최솟값 자세 하나만 "
             "빼도 S 의 p-p 가 " + _n("engines.sionna.ptp_db_drop1", DEP, "{:.1f}", "dB")
           + " 로 내려간다. ⭐ 그래서 이 절이 깊이를 인용할 때 쓰는 자는 "
             "**p5~p95 열**이고, p-p 열과 «비» 열은 «이상치 몇 개가 폭을 정하는가» 를 보는 "
             "자로 읽는다.", "",
           f"⭐ 셋 다 (a) 0 도플러 동체 선, (b) 블레이드 통과율 간격 능선, "
           f"(c) 날개끝 주파수 근처 감쇠를 낸다 — **구조가 일치한다**. "
           f"날개끝 주파수 안에서 스펙트럼 코사인이 "
           f"{_n_pending('verdict.cosine_in_ftip.sionna_vs_sbr', TRI, '{:.3f}')}(Sionna↔SBR) · "
           f"{_n_pending('verdict.cosine_in_ftip.sionna_vs_po', TRI, '{:.3f}')}(Sionna↔PO) · "
           f"{_n_pending('verdict.cosine_in_ftip.sbr_vs_po', TRI, '{:.3f}')}(SBR↔PO) 다."),

        md("## 그 코사인은 «닮았다» 까지를 말한다", "",
           "위 코사인이 말하는 것은 «대역 안에서 무늬의 모양이 닮았다» 까지다. 세 엔진은 능선의 "
           "**세기와 밀도**에서 크게 갈리고, 갈리는 방향에 각각 이유가 있다.", "",
           table(["팔", "무엇이 그렇게 만드나"], [
               ["P " + ARM_PO,
                "가림을 빼고 계산하므로 모든 면이 항상 기여한다 → 변조가 씻긴다"],
               ["B " + ARM_SBR, "가림이 켜져 있어 능선이 굵다. 격자를 얼린 뒤 날개끝 밖에 남는 "
                                "몫은 " + _oob_pct("sbr") + " 이고, 그래도 순수 PO 보다 "
                + _n("three_engines_ranking.new_P_out_absolute.sbr_over_po_db",
                     OOB, "{:.0f}", "dB") + " 위다"],
               ["S " + ARM_SIONNA, "경로가 열 개 남짓이라 표본이 성기고, 날개끝 밖에 "
                                   + _oob_pct("sionna") + " 이 남는다"],
           ]), "",
           "⭐ **날개끝 밖에 남던 능선의 원인은 광선 격자의 이산화가 아니라 자세마다 격자를 다시 "
           "정의하는 것이었다.** 격자를 촘촘히 해도 λ/12 → λ/32 에서 대역밖 절대 전력이 "
           + _n("convergence.prod.drop_db_div12_to_div32", OOB, "{:.1f}", "dB")
           + " 만 내려간다 — 기울기 "
           + _n("convergence.prod.slope_ge12", OOB, "{:.2f}")
           + " 이고, d² 이산화 잡음이면 −2 여야 한다.", "",
           "격자를 얼리면 같은 광선 수로 "
           + _n("freeze_verdict.gains_db.12", OOB, "{:.1f}", "dB")
           + " 내려가면서 기울기가 "
           + _n("convergence.froz.slope_ge12", OOB, "{:.2f}")
           + " 로 예측에 붙는다. **순수 PO 팔(P)을 잣대로 놓으면** 얼린 팔의 대역 안 일치도가 "
           + _n("in_band_fidelity.rows[1].cos_prod_vs_po", SGC, "{:.3f}")
           + " 에서 "
           + _n("in_band_fidelity.rows[1].cos_froz_vs_po", SGC, "{:.3f}")
           + " 으로 오른다. 기전과 대가는 " + ref("kernel-what", "커널이 하는 일") + " 이 잰다.", "",
           BREAK,
           "## 얼리기의 판정은 잣대로 삼은 팔이 정한다", "",
           "⭐ **Sionna 팔(S)을 잣대로 놓으면 같은 원장이 반대로 움직인다** — 같은 격자(λ/12)에서 "
           + _n("in_band_fidelity.rows[1].cos_prod_vs_sionna", SGC, "{:.3f}")
           + " 에서 "
           + _n("in_band_fidelity.rows[1].cos_froz_vs_sionna", SGC, "{:.3f}")
           + " 로 내려가고, 사다리의 다섯 격자(λ/8 · λ/12 · λ/16 · λ/24 · λ/32) 전부에서 같은 "
           "방향이다.", "",

           table(["격자", "P 잣대 (prod → froz)", "S 잣대 (prod → froz)"],
                 [[f"λ/{r['div']}",
                   _n(f"in_band_fidelity.rows[{i}].cos_prod_vs_po", SGC, "{:.3f}") + " → "
                   + _n(f"in_band_fidelity.rows[{i}].cos_froz_vs_po", SGC, "{:.3f}"),
                   _n(f"in_band_fidelity.rows[{i}].cos_prod_vs_sionna", SGC, "{:.3f}") + " → "
                   + _n(f"in_band_fidelity.rows[{i}].cos_froz_vs_sionna", SGC, "{:.3f}")]
                  for i, r in enumerate(fetch((SGC, "in_band_fidelity.rows")))]), "",

           "두 잣대가 재는 것이 다르다 — P 는 광선을 아예 안 쓰는 팔이라 격자를 얼리면 가까워지고, "
           "S 는 경로가 성긴 팔이라 그 성김이 얼리기와 함께 움직인다. 그래서 이 절의 판정은 "
           "**순수 PO 를 잣대로 놓았을 때** 성립한다고 적는다.", "",
           BREAK,
           "## 얼리기가 블레이드 대역에 한 일", "",
           "⭐ 같은 재계산에서 **블레이드 대역 안**의 전력도 중앙값 "
           + _n("summary.P_in_delta_db_median", FSL, "{:+.1f}", "dB")
           + " 내려갔다. 그것이 표적의 운동이었다면 얼리기가 물리를 지운 것이므로, 판정을 "
           "광선을 안 쓰는 엔진에게 맡겼다 — 블레이드 대역이 순수 PO 보다 "
           + _n("summary.P_in_excess_over_po_db.before_median", FSL, "{:+.1f}", "dB")
           + " 위에 있던 것이 "
           + _n("summary.P_in_excess_over_po_db.after_median", FSL, "{:+.1f}", "dB")
           + " 로 줄었고 PO 밑으로 내려간 열은 "
           + _n("summary.P_in_excess_over_po_db.n_below_po_after", FSL, "{:.0f}")
           + " 개다. 같은 대역의 복소 일치는 "
           + _n("summary.blade_coh_vs_po.before_median", FSL, "{:.2f}") + " → "
           + _n("summary.blade_coh_vs_po.after_median", FSL, "{:.2f}")
           + " 로 오르고, 플래시 대조비는 "
           + _n("summary.flash_contrast_db.n_improved", FSL, "{:.0f}") + "/"
           + _n("summary.flash_contrast_db.n_series", FSL, "{:.0f}") + " 열에서 "
           + _n("summary.flash_contrast_db.delta_median", FSL, "{:+.1f}", "dB")
           + " 올라간다 — 자의 흔들림이 골짜기를 메우고 있었다는 뜻이다"
           + f" ⟨{FSL} : verdict.headline_ko⟩.", "",
           "⚠ 대가는 비율 쪽에 있다 — 동체가 든 열에서 «대역밖 ÷ 블레이드 대역» 이 "
           + _n("summary.by_group.with_body.oob_over_in_db_before_median", FSL, "{:.1f}", "dB")
           + " 에서 "
           + _n("summary.by_group.with_body.oob_over_in_db_after_median", FSL, "{:.1f}", "dB")
           + " 로 올라간다(순수 PO 는 "
           + _n("summary.oob_over_in_db.po_median", FSL, "{:.1f}", "dB")
           + "). 잉여가 사라진 만큼 남은 잔차가 상대적으로 커 보이는 것이고, 그 잔차가 지금 "
           "이 맵의 동적범위 상한이다"
           + f" ⟨{FSL} : verdict.cost_ko⟩.", "",
           _grid_state_line()),

        md("## Sionna 의 빗은 기하에서 온다", "",
           "잰 팔은 **S** 하나이고, 맞대는 상대는 산란 물리를 뺀 기하 기준이다.", "",
           table(["기체", "±1 조화 안 일치 (근거리 1·3 m 칸)",
                  "빗 모양 코사인 중앙값 (15 칸)"], [
               ["Mini 2",
                _n(G + ".mini2.n_near_within_1_bin", VRD, "{:.0f}") + " / "
                + _n(G + ".mini2.n_near_cells", VRD, "{:.0f}"),
                _n(G + ".mini2.comb_shape_cosine_median", VRD, "{:.4f}")],
               ["Matrice 4E",
                _n(G + ".matrice4e.n_near_within_1_bin", VRD, "{:.0f}") + " / "
                + _n(G + ".matrice4e.n_near_cells", VRD, "{:.0f}"),
                _n(G + ".matrice4e.comb_shape_cosine_median", VRD, "{:.4f}")],
           ]), "",
           "같은 메쉬로 산란 물리를 전부 빼고 왕복 위상만 더한 빗과 Sionna 의 빗을 겹치면 "
           "근거리에서 거의 모든 칸이 ±1 조화 안에서 맞는다. 즉 스톡 PathSolver 는 **회전하는 "
           "기하의 왕복 위상을 제대로 따라간다** — 그 빗은 몬테카를로 잡음의 산물이 아니다."),

        md("## 프롭 정반사가 잡히느냐는 예산이 아니라 앙각이 정한다", "",
           f"⭐ **이 소절의 숫자는 전부 스톡 팔(S) 하나에서 나온다** — 광선 예산 사다리와 "
           f"경로 인구조사, 그 둘뿐이다.", "",
           f"자세×로터위상 {_n('specular_census.total.n_cells', MDP, '{:,.0f}', '칸')} 전수에서 "
           f"프로펠러에 떨어진 정반사 경로는 "
           f"{_n('specular_census.total.n_with_prop_specular', MDP, '{:.0f}', '칸')} 이다"
           f"(**이 인구조사의** 자세 격자 = 앙각 0~"
           f"{_n('_meta.el_base[-1]', BFL, '{:.0f}', '°')}).", "",
           "그 «0» 이 표적의 물리인지 격자의 성질인지 가르려고 축을 **두 개** 따로 열었다 — "
           "광선을 사다리로 올리는 **예산 축**과, 프롭 법선이 향하는 가파른 쪽까지 여는 "
           "**앙각 축**이다.", "",
           table(["기체", "예산 꼭대기", "그 예산의 프롭 정반사",
                  f"앙각 {_n('_meta.el_deep[-1]', BFL, '{:.0f}', '°')} 까지 열면", "무엇이 갈랐나"], [
               ["Matrice 4E",
                _n("verdict.matrice4e.budget_top_spp", BFL, "{:,.0f}", "발"),
                _n("verdict.matrice4e.budget_top_prop_cells", BFL, "{:.0f}", "칸"),
                _n("verdict.matrice4e.deep_elevation_prop_cells", BFL, "{:.0f}", "칸")
                + " / " + _n("elevation_axis.matrice4e.deep.n_cells", BFL, "{:.0f}", "칸"),
                "앙각"],
               ["Mini 2",
                _n("verdict.mini2.budget_top_spp", BFL, "{:,.0f}", "발"),
                _n("verdict.mini2.budget_top_prop_cells", BFL, "{:.0f}", "칸"),
                _n("verdict.mini2.deep_elevation_prop_cells", BFL, "{:.0f}", "칸")
                + " / " + _n("elevation_axis.mini2.deep.n_cells", BFL, "{:.0f}", "칸"),
                "둘 다 아니다"],
           ]), "",
           "⭐ **두 기체가 갈린다.** Matrice 4E 는 광선을 사다리 꼭대기까지 올려도 0 칸인데 "
           "가파른 앙각을 열면 프롭 정반사가 나온다 — 그 «0» 은 격자가 프롭 법선 근처를 안 "
           "본 결과다. Mini 2 는 예산 꼭대기에서도 앙각 끝에서도 0 칸이라, 이 기체에 대해서만 "
           "«스톡 RT 가 프롭 정반사를 못 낸다» 에 가까워진다.", "",
           "⇒ 그래서 **이 인구조사의** 자세 격자(앙각 0~"
           + _n("_meta.el_base[-1]", BFL, "{:.0f}", "°")
           + ")에서 스톡 팔이 내는 무늬는 전부 흩어져 되돌아오는 반사에서 나오고, 그 값은 광선을 "
           "다시 쏠 때마다 흔들린다.", "",
           "⚠ **이 편의 맵은 다른 격자에 산다** — 앙각 "
           + _n("_meta.el_deg", TRI, "{:.0f}", "°")
           + " 한 칸이다. 두 격자는 따로 읽는다.", "",
           "**위상은 광선 엔진이, 세기는 PO 커널이 맡는** 분업의 근거는 이 절 그림 1·2 의 두 팔 "
           "대조이고, 이 인구조사는 거기에 **스톡 팔 쪽 한계**를 보탠다."),

        next_steps([
            ("가장자리 판정을 꼬리 초과분과 함께 다시 낸다",
             "«가장자리» 가 물리적 절벽인지 꼬리인지가 칸마다 갈린다",
             ref("md-ray-budget", "광선예산")),
            ("SBR 팔의 일치도를 15 칸 격자 전체로 넓힌다",
             "한 칸에서는 그림 2 가 이미 쟀다(SBR↔PO "
             + _n_pending("verdict.cosine_in_ftip.sbr_vs_po", TRI, "{:.3f}")
             + ") — 남은 것은 그 값이 자세·거리에 얼마나 걸리는지다",
             "`src/rcs_sbr.py` 팔을 15 칸 격자에"),
        ]),
    ]


# =========================================================================== #
#  편 37 — 회전수
# =========================================================================== #
def blocks_37() -> list:
    R = LEAD + ".findings.rpm_spread_makes_it_time_varying"

    return [
        header(
            num=37,
            title="네 로터가 같은 회전수로 돌면 무늬는 시간에 못 변한다",
            did="네 로터의 회전수를 잠근 판과 흩뜨린 판을 **두 엔진 팔**(SBR · 순수 PO)에서 "
                "각각 돌려 창 반쪽 스펙트럼의 상관을 쟀다.",
            results=[
                f"SBR 팔(B): 잠근 판의 반창 스펙트럼 상관은 "
                f"{_n(R + '.locked_half_corr', MDB, '{:.4f}')} 다 — 신호가 완전한 주기함수라 "
                f"스펙트로그램이 창 내내 같은 모습으로 선다.",

                f"로터마다 회전수를 "
                f"{_n('_meta.rpm_spread_frac', MDB, '{:.2%}')} 흩뜨리면 상관이 "
                f"{_n(R + '.spread_half_corr', MDB, '{:.4f}')} 로 내려간다 — 낙차 "
                f"{_n(R + '.drop', MDB, '{:.4f}')}.",

                f"⭐ 순수 PO 팔(P)이 같은 낙차를 **독립으로** 낸다 — "
                f"{_L('arms.C_po_locked.half_window_spectrum_corr', '{:.4f}')} 에서 "
                f"{_L('arms.D_po_spread.half_window_spectrum_corr', '{:.4f}')} 로 내려간다"
                f"(B 팔은 {_L('arms.B_sbr_spread.half_window_spectrum_corr', '{:.4f}')}). "
                f"P 는 광선 격자를 안 쓰고 가림도 안 푸는 팔이라, 이 축은 가림에 안 걸린다.",

                f"그때 B 팔의 변조 깊이가 "
                f"{_L('arms.A_sbr_locked.modulation_ptp_db', '{:.2f}', 'dB')} 에서 "
                f"{_L('arms.B_sbr_spread.modulation_ptp_db', '{:.2f}', 'dB')} 로 커지고, "
                f"동체:날개 비는 {_L('arms.A_sbr_locked.dc_over_ac', '{:.2f}')} 에서 "
                f"{_L('arms.B_sbr_spread.dc_over_ac', '{:.2f}')} 로 내려간다.",

                f"흩어짐 폭 ±{_n('_meta.rpm_spread_frac', MDB, '{:.2%}')} 는 PX4 **SITL**"
                f"(소프트웨어 인더루프 = 시뮬) 로그에서 잰 모터간 산포의 중간값이다 — "
                f"⚠실기 텔레메트리가 아니라 **하한 예시**이고, 우리 표적의 비행 로그가 오면 "
                f"그 값으로 바꾼다.",
            ],
            method=[
                ("단일축",
                 "잠근 판과 흩뜨린 판은 광선 엔진·재질·기하·창 길이가 전부 같고 로터별 회전수만 "
                 "다르다"),
                ("두 엔진 팔",
                 "**B** = " + ARM_SBR + " 의 A·B 열 과 **P** = " + ARM_PO
                 + " 의 C·D 열 이 같은 rpm 축을 각각 돈다. P 열은 광선 격자를 안 쓴다 — "
                 "`_meta.po_arms_not_recomputed_ko` 가 그렇게 적는다"),
                ("흩뜨림 규약",
                 "네 로터에 ±" + _n('_meta.rpm_spread_frac', MDB, '{:.2%}')
                 + " 를 패턴 [1, −1, −0.55, 0.55] 로 준다 — 무게중심 치우침과 요 "
                 "토크 균형이 만드는 실제 비대칭을 흉내 낸 것이다"),
                ("판정량",
                 "창을 반으로 갈라 두 스펙트럼의 상관을 잰다. 완전 주기함수면 1 에 붙는다"),
                ("흩어짐 폭의 출처",
                 "PX4 **SITL**(시뮬) 로그에서 잰 모터간 산포의 중간값이다 — "
                 "`_meta.spread_is_declared_ko` 에 출처와 교체 규약을 적었다"),
            ],
            prereq=[("앞 편", ref("md-slowtime", "슬로타임 복소열") + " — 이 축이 서는 절차")],
            repro=REPRO_15B,
        ),

        md("## 회전수가 같으면 무늬는 시간에 못 변한다", "",
           *_fig(1, "report07_f1",
                 "네 로터가 같은 회전수로 돌 때와 흩어질 때, 무늬가 시간에 따라 어떻게 다른가?"),
           f"왼쪽은 네 로터를 같은 회전수로 돌린 것이다. 줄무늬가 시간축 내내 **같은 자리에 "
           f"선다**. 창을 반으로 갈라 두 스펙트럼의 상관을 재면 "
           f"{_n(R + '.locked_half_corr', MDB, '{:.4f}')} 다.", "",
           "우연이 아니라 **원리**다 — 네 로터가 같은 속도로 위상까지 맞춰 돌면 신호가 완전한 "
           "주기함수가 되고, 주기함수의 스펙트로그램은 창 내내 자기 모습을 지킨다."),

        md("## 흩뜨리면 줄이 숨쉰다", "",
           table(["무엇을", "어느 팔", "잠근 판", "흩뜨린 판"], [
               ["반창 스펙트럼 상관", "B (SBR · 가림 O)",
                _n(R + ".locked_half_corr", MDB, "{:.4f}"),
                _n(R + ".spread_half_corr", MDB, "{:.4f}")],
               ["반창 스펙트럼 상관", "P (순수 PO · 가림 X)",
                _L("arms.C_po_locked.half_window_spectrum_corr", "{:.4f}"),
                _L("arms.D_po_spread.half_window_spectrum_corr", "{:.4f}")],
               ["변조 깊이", "B",
                _L("arms.A_sbr_locked.modulation_ptp_db", "{:.2f}", "dB"),
                _L("arms.B_sbr_spread.modulation_ptp_db", "{:.2f}", "dB")],
               ["변조 깊이", "P",
                _L("arms.C_po_locked.modulation_ptp_db", "{:.2f}", "dB"),
                _L("arms.D_po_spread.modulation_ptp_db", "{:.2f}", "dB")],
               ["동체:날개 비", "B",
                _L("arms.A_sbr_locked.dc_over_ac", "{:.2f}"),
                _L("arms.B_sbr_spread.dc_over_ac", "{:.2f}")],
               ["날개끝 안쪽 에너지 비", "B",
                _L("arms.A_sbr_locked.energy_inside_ftip_frac", "{:.4f}"),
                _L("arms.B_sbr_spread.energy_inside_ftip_frac", "{:.4f}")],
           ]), "",
           "오른쪽 열이 «시간에 따라 변한다» 의 정량이다. 상관이 내려간 만큼 줄이 숨쉰다."),

        md("## 두 팔이 같은 방향으로 내려간다", "",
           f"이 칸({_L('name')} · 배 쪽)에서 두 팔의 낙차가 소수 둘째 자리까지 붙는다 — "
           "가림을 켠 팔과 아예 안 켠 팔이 같은 답을 낸다. 이 축의 원인이 **rpm 산포** 하나임을 "
           "그 일치가 보인다.", "",
           "⚠ 절대 레벨은 두 팔이 서로 다른 잣대라 나란히 놓지 않는다 — 여기서 맞대는 것은 "
           "**같은 팔 안의 잠근 판 → 흩뜨린 판 낙차**뿐이다.", "",
           f"원장: `{MDB} : {LEAD}.arms.{{A_sbr_locked, B_sbr_spread, C_po_locked, "
           "D_po_spread}`."),

        md("## 흩어짐 폭은 실측에서 온다", "",
           "실제 기체는 무게중심 치우침과 요 토크 균형 때문에 네 모터가 서로 다른 추력을 내고 "
           "그만큼 회전수가 갈린다. 그 폭을 PX4 **SITL**(시뮬) 로그에서 잰 모터간 산포의 "
           f"중간값 ±{_n('_meta.rpm_spread_frac', MDB, '{:.2%}')} 로 놓았다 — 출처와 교체 "
           f"규약은 `{MDB} : _meta.spread_is_declared_ko` 다. ⚠실기 비행로그로 잰 야외 호버는 "
           "이보다 한 자릿수 크다(같은 권의 «로터 산포 프리셋 비교» 절).", "",
           "⭐ 이 편이 말하는 것은 특정 산포값이 아니라 "
           "**«무늬가 시간에 변하려면 흩어짐이 필요하다»** 는 구조다 — 실측 크기의 산포에서도 "
           f"상관이 {_n(R + '.spread_half_corr', MDB, '{:.4f}')} 로 내려간다."),

        next_steps([
            ("우리 표적(Matrice 4E)의 비행 로그 모터별 회전수를 넣는다",
             "PX4 중간값으로 둔 흩어짐 폭이 표적 자신의 측정값으로 바뀐다",
             "실측 1차 · Matrice 4E"),
            ("흩어짐 폭을 사다리로 흔들어 상관 낙차 곡선을 낸다",
             "«시간 변화» 를 검출기가 쓸 수 있는 최소 흩어짐이 정해진다",
             "이 편의 단일축을 격자로"),
        ]),
    ]


# =========================================================================== #
#  편 38 — 가림
# =========================================================================== #
def blocks_38() -> list:
    #: ⛔ 블레이드 채널의 p-p 가 표본 수에 딸리는지 — 같은 창, 등간격 솎기.
    #  창의 표본 수는 원장(`physics.n_t`)에서 든다 — 하드코딩하지 않는다.
    _NARM = int(fetch((MDB, f"{LEAD}.physics.n_t")))
    _F60, _FFULL = _shrink_arm("F_blade_occ", 60), _shrink_arm("F_blade_occ", _NARM)
    _G60, _GFULL = _shrink_arm("G_blade_free", 60), _shrink_arm("G_blade_free", _NARM)
    return [
        header(
            num=38,
            title="동체가 날개를 가리면 변조 깊이와 레벨이 함께 바뀐다",
            did="광선 엔진·재질·기하·운동학·광선 격자를 전부 같게 두고 «동체가 막느냐» 만 다르게 "
                "한 두 열을 **SBR 팔(B)** 에서 돌렸다.",
            results=[
                f"⭐ 이 축은 **SBR 팔(B)에서만 선다** — 순수 PO 팔(P)은 모든 면이 항상 "
                f"기여하는 설계라 «막느냐» 라는 스위치가 그 팔의 밖에 있다.",

                f"동체가 막으면 변조 깊이와 레벨이 **함께 움직인다** — 막는 열(F)의 깊이 "
                f"표준편차는 {_L('arms.F_blade_occ.modulation_std_db', '{:.2f}', 'dB')}, 안 막는 "
                f"열(G)은 {_L('arms.G_blade_free.modulation_std_db', '{:.2f}', 'dB')} 다"
                f"({_L('name')} · 배 쪽 한 칸 · {_L('physics.n_t', '{:,.0f}', '표본')}).",

                f"⛔ 그 움직임의 **dB 크기는 판 선택 위에 있다** — 격자 판을 반 칸 옮기면 레벨 "
                f"차가 {_n('verdict.occlusion_level_plate_ptp_db', FPS, '{:.2f}', 'dB')}, 깊이 "
                f"**p-p** 차가 {_n('verdict.occlusion_ptp_plate_ptp_db', FPS, '{:.2f}', 'dB')} "
                f"흔들려 같은 p-p 자로 잰 원장 값"
                f"(`findings.occlusion_ptp_db` = "
                f"{_L('findings.occlusion_ptp_db', '{:+.2f}', 'dB')}) 을 넘는다 — ⚠ 판 축은 "
                f"p-p 로만 재어 두었다. 두 열의 절대 레벨도 판 셋 사이 "
                f"{_n('verdict.abs_level_plate_ptp_db', FPS, '{:.2f}', 'dB')} p-p 라 같은 규칙 "
                f"아래 둔다 — 이 편은 크기 대신 **존재**를 세운다.",

                f"두 열의 광선 격자를 같게 유지했다 — 막는 쪽은 동체를 완전흡수로 두고, "
                f"안 막는 쪽은 동체 면만 빼되 정점은 남겼다.",

                f"⚠ 부호를 물리로 단정하지 않는다 — 합이 코히런트라 항이 줄어도 레벨이 "
                f"올라갈 수 있고, 실제로 그런 칸이 있다.",
            ],
            method=[
                ("가림 단일축",
                 "한쪽은 동체를 완전흡수(Γ=0)로 두어 막되 산란은 안 하게 하고, 다른 쪽은 동체 "
                 "면만 빼되 정점은 남겨 광선 격자를 같게 유지한다"),
                ("정점을 남기는 이유",
                 "경계상자가 같아야 두 팔의 광선 수와 간격이 같아진다. 정점을 빼면 «가림» 과 "
                 "«표본화» 가 섞인다"),
                ("채널",
                 "블레이드 채널만 본다 — 동체 정적 반사를 빼야 가림의 효과가 드러난다"),
                ("부호 규약",
                 "산출물이 부호 주의를 함께 적는다 — `findings.occlusion_sign_note_ko`"),
            ],
            prereq=[("앞 편", ref("md-slowtime", "슬로타임 복소열") + " — 이 축이 서는 절차")],
            repro=REPRO_15B,
        ),

        md("## 가림만 남기고 다른 것을 전부 묶었다", "",
           *_fig(1, "report07_f4",
                 "같은 광선·같은 메쉬·같은 운동에서 동체가 막으면 무엇이 달라지는가?"),
           "한쪽은 동체를 완전흡수로 두어 **광선은 막되 산란은 안 하게** 하고, 다른 쪽은 동체 "
           "면만 빼되 정점 배열은 남겨 두었다.", "",
           "정점을 남기면 경계상자가 같아서 두 팔의 광선 수와 간격이 같아진다. 정점을 빼면 "
           "«가림» 과 «표본화» 가 섞여 축이 둘이 된다."),

        md("## 두 열의 값 — 둘 다 SBR 팔이다", "",
           f"둘 다 **B** = {ARM_SBR} 이고, 여기서 «두 팔» 은 엔진이 아니라 **동체를 막는 열과 "
           "막지 않는 열**을 가리킨다. 오른쪽 두 열이 이 표를 읽는 법을 정한다 — 판 셋 "
           "흩어짐보다 작은 칸은 본문 밖에 둔다.", "",
           table(["무엇을", "막는 열 (F)", "안 막는 열 (G)", "차이 (F−G)", "판 셋 p-p"], [
               ["변조 깊이 std ⭐",
                _L("arms.F_blade_occ.modulation_std_db", "{:.2f}", "dB"),
                _L("arms.G_blade_free.modulation_std_db", "{:.2f}", "dB"),
                "⛔ 본문 밖", "⚠ 판 원장은 `ptp_db`·`level_db` 만 든다"],
               ["변조 깊이 p-p ⛔",
                _L("arms.F_blade_occ.modulation_ptp_db", "{:.2f}", "dB"),
                _L("arms.G_blade_free.modulation_ptp_db", "{:.2f}", "dB"),
                "⛔ 본문 밖",
                _n("verdict.occlusion_ptp_plate_ptp_db", FPS, "{:.2f}", "dB")],
               ["레벨",
                "⛔ 본문 밖", "⛔ 본문 밖", "⛔ 본문 밖",
                _n("verdict.occlusion_level_plate_ptp_db", FPS, "{:.2f}", "dB")
                + " (팔별 절대 "
                + _n("verdict.abs_level_plate_ptp_db", FPS, "{:.2f}", "dB") + ")"],
               ["동체:날개 비",
                _L("arms.F_blade_occ.dc_over_ac", "{:.3f}"),
                _L("arms.G_blade_free.dc_over_ac", "{:.3f}"), "—", "—"],
               ["날개끝 안쪽 에너지 비",
                _L("arms.F_blade_occ.energy_inside_ftip_frac", "{:.4f}"),
                _L("arms.G_blade_free.energy_inside_ftip_frac", "{:.4f}"), "—", "—"],
           ]), "",
           f"⛔ «본문 밖» 칸의 값은 원장 `{MDB}` 에 그대로 있다. 크기를 뺀 이유가 둘이다 — "
           "레벨 차(F−G)는 판 셋 흩어짐 "
           + _n("verdict.occlusion_level_plate_ptp_db", FPS, "{:.2f}", "dB")
           + " 안에 들고, 팔별 절대 레벨은 판 한 장의 서브셀 오프셋에 "
           + _n("verdict.abs_level_plate_ptp_db", FPS, "{:.2f}", "dB")
           + " p-p 로 걸린다. 얼린 복소장은 **무늬의 모양**을 내고, 절대 σ 는 디더를 켠 정적 "
           "경로가 낸다.", "",
           "⛔ **p-p 두 칸은 표본 수 위에도 있다** — 같은 창을 등간격으로 솎아 N 을 "
           + _L("physics.n_t", "{:,.0f}") + " 에서 60 으로 줄이면 F 의 p-p 가 "
           + f"{_FFULL['ptp']:.1f} → {_F60['ptp']:.1f} dB, G 가 {_GFULL['ptp']:.1f} → "
             f"{_G60['ptp']:.1f} dB 로 내려가는데, 같은 솎기의 std 는 {_FFULL['std']:.2f} → "
             f"{_F60['std']:.2f} dB · {_GFULL['std']:.2f} → {_G60['std']:.2f} dB 로 붙어 있다. "
             "⭐ 그래서 이 절이 깊이를 인용할 때 쓰는 자는 std 다. ⚠ 그 std 가 판 한 장에 얼마나 "
             f"걸리는지는 이 원장이 답하지 않는다 — 판 원장(`{FPS}`)은 팔마다 `ptp_db` 와 "
             "`level_db` 만 든다."),

        md("## 여섯 칸의 부호는 갈린다", "",
           "위 표는 한 칸이다. 같은 원장의 여섯 칸을 전부 늘어놓으면 레벨 차의 **부호가 칸마다 "
           "갈린다** — 크기를 물리로 읽는 대신 «두 양이 함께 움직인다» 까지만 읽는 이유가 여기 "
           "있다.", "",
           table(["칸", "레벨 차 (F−G)", "변조 깊이 차 (F−G)"],
                 [[k,
                   _n(f"cells.{k}.findings.occlusion_level_db", MDB, "{:+.3f}", "dB"),
                   _n(f"cells.{k}.findings.occlusion_ptp_db", MDB, "{:+.2f}", "dB")]
                  for k in fetch((MDB, "cells"))]), "",
           "⭐ `mini5pro/nose` 는 F 열과 G 열의 변조 깊이가 배정밀도 자릿수까지 같은 값이고 "
           "레벨 차도 그 자릿수 안에서 0 이다 — 그 자세에서 동체가 블레이드를 덮는 몫이 0 이다. "
           "이 축이 자세에 얼마나 걸리는지가 그 칸에 있다.", "",
           "⚠ 여섯 칸의 레벨 차는 전부 판 셋 흩어짐 "
           + _n("verdict.occlusion_level_plate_ptp_db", FPS, "{:.2f}", "dB")
           + " 안에 든다. 그래서 이 표가 세우는 것은 **«칸마다 다르다»** 까지이고, 칸 하나의 dB 는 "
           "판 선택 위에 있다."),

        md("## ⭐이 표의 dB 는 «판 한 장» 에도 걸린다", "",
           "두 팔은 같은 얼린 광선 격자를 쓴다. 그러면 격자를 어디에 놓았느냐는 두 팔에 똑같이 "
           "실리므로 차이에서 빠질 것 같다 — 그것이 «단일축» 이라는 말의 뒷받침이었다. "
           "그 가정을 재 봤다: 판의 중심만 **반 칸** 옮긴 같은 크기의 판으로 같은 자세열을 다시 "
           "태우면 (광선 수·간격이 같고 서브셀 오프셋만 다르다) 이렇게 움직인다.", "",
           table(["무엇이", "판 셋 사이 p-p", "원장에 있는 값", "이 편이 쓰는 자리"],
                 [["전체 팔의 절대 레벨",
                   _n("verdict.abs_level_plate_ptp_db", FPS, "{:.2f}", "dB"),
                   "`arms.*.level_db`",
                   "⛔ 본문 밖 — 절대 σ 는 디더를 켠 정적 경로가 낸다"],
                  ["가림 · 레벨 (F−G)",
                   _n("verdict.occlusion_level_plate_ptp_db", FPS, "{:.2f}", "dB"),
                   "`findings.occlusion_level_db`",
                   "⛔ 본문 밖 — 판 흩어짐이 그 값을 덮는다"],
                  ["가림 · 변조 깊이 (F−G)",
                   _n("verdict.occlusion_ptp_plate_ptp_db", FPS, "{:.2f}", "dB"),
                   "`findings.occlusion_ptp_db`",
                   "⛔ 본문 밖 — 깊이 차의 **부호도** 판에 따라 바뀐다"]]), "",
           "⭐ 셋째 열은 **키 이름**이다. 값은 원장에 그대로 있고, 이 편의 본문·표는 그 크기를 "
           "빼고 «두 양이 함께 움직인다» 만 세운다 — 규칙과 본문이 한 자리에서 맞는다.", "",
           "⭐ 그러니 이 편이 서는 자리를 좁힌다. **«동체가 막으면 두 양이 함께 움직인다» 는 "
           "그대로 서고, 그 움직임의 dB 크기는 판 선택 위에 있다.** 크기가 필요한 자리에서는 "
           "판 앙상블 평균(오프셋 여러 판의 평균)이 먼저다"
           f" ⟨{FPS} : verdict.how_to_read_ko⟩.", "",
           "두 팔의 기하가 서로 달라서(막는 팔은 동체가 있고 안 막는 팔은 동체 면이 없다) "
           "판 편향이 공통모드로 빠지지 않는다 — 그것이 이 표가 재서 확인한 내용이다"
           f" ⟨{FPS} : verdict.common_mode_ko⟩.", "",
           "이 비교가 같은 물리를 잰 것인지의 게이트도 함께 둔다 — 생산 판(P0)으로 낸 세 팔의 "
           "레벨이 생산 원장과 최대 "
           + _n("verdict.p0_vs_production_max_abs_db", FPS, "{:.2f}", "dB")
           + " 안에서 붙는다"
           + f" ⟨{FPS} : verdict.validity_ko⟩. 그러니 위 흩어짐은 배선 차이가 아니라 판 "
           "오프셋 그 자체다."),

        md("## 부호를 물리로 단정하지 않는 이유", "",
           "합이 코히런트라 항이 줄어도 남은 항끼리 상쇄가 덜 되면 레벨이 **올라갈 수 있다**. "
           "실제로 그런 칸이 있다.", "",
           f"근거는 `{MDB} : cells.*.findings.occlusion_sign_note_ko` 에 있다. 그래서 이 편이 "
           f"말하는 것은 «가림이 레벨을 내린다» 가 아니라 **«가림이 두 양을 함께 움직인다»** 다.", "",
           "가림이 무는 자세가 어디인지는 " + ref("md-attitude", "자세 축") + " 이 잰다."),

        next_steps([
            ("가림을 자세 전면으로 넓힌다",
             "어느 자세에서 얼마나 무는지의 지도가 서고, 그 지도가 분류기의 입력이 된다",
             "이 편의 단일축을 격자로"),
            ("가림 있는 커널을 사다리 채점에 정식 편입한다",
             "형상 사다리의 부호가 가림 아래에서 유지되는지가 갈린다",
             ref("ladder-premature", "사다리 판정 조건")),
        ]),
    ]


# =========================================================================== #
#  편 39 — 블레이드 대 동체
# =========================================================================== #
def blocks_39() -> list:
    #: 두 채널의 레벨 **차**. 절대 레벨 두 수는 판 한 장의 서브셀 오프셋에 걸려 본문 밖이고
    #  (상설 규칙 — `freeze_plate_sensitivity.json : verdict`), 차는 그 흩어짐을 크게 넘는다.
    _gap = (fetch((MDB, f"{LEAD}.arms.B_sbr_spread.level_db"))
            - fetch((MDB, f"{LEAD}.arms.F_blade_occ.level_db")))
    _GAP = f"{_gap:.2f} dB"
    _GAP_SRC = (f"`{MDB} : {LEAD}.arms." + "{B_sbr_spread, F_blade_occ}.level_db` 의 차")

    #: ⛔ «아홉 배» 는 p-p 로 잰 값이고, p-p 는 표본 수 N 에 딸린다. 두 자로 다시 잰다.
    _B60 = _shrink_arm("B_sbr_spread", 60)
    _F60 = _shrink_arm("F_blade_occ", 60)
    _R_STD = (fetch((MDB, f"{LEAD}.arms.F_blade_occ.modulation_std_db"))
              / fetch((MDB, f"{LEAD}.arms.B_sbr_spread.modulation_std_db")))
    _R_PTP = (fetch((MDB, f"{LEAD}.arms.F_blade_occ.modulation_ptp_db"))
              / fetch((MDB, f"{LEAD}.arms.B_sbr_spread.modulation_ptp_db")))

    return [
        header(
            num=39,
            #: ⛔2026-09-04 — 전 제목은 «블레이드 신호는 약하지 **않다** — 동체 정적 반사가
            #  **덮고 있을 뿐이다**» 로, 「A 가 아니라 B」와 「X 가 Y 를 덮는다」를 한 줄에
            #  쓰면서 범위가 하나도 없었다. 잰 것은 matrice4e 배 쪽 **한 칸** · 3.5 GHz
            #  **한 밴드**(이 편이 스스로 「나머지 다섯 밴드는 원장 없음」이라 적는다) ·
            #  얼린 판 한 장이다. 관측·범위형으로 바꾼다.
            title="matrice4e 배 쪽 3.5 GHz 한 칸에서 프로펠러 채널은 레벨이 20.70 dB 낮고 "
                  "변조 깊이는 0.73 → 5.93 dB 로 깊다",
            did="같은 얼린 판·같은 자세·같은 로터 회전수에서 전체 드론 채널과 프로펠러 채널을 "
                "따로 재어 변조 깊이를 맞댔다.",
            results=[
                f"전체 드론 채널의 변조 깊이 표준편차는 "
                f"{_L('arms.B_sbr_spread.modulation_std_db', '{:.2f}', 'dB')} 인데, 같은 칸의 "
                f"프로펠러 채널은 "
                f"{_L('arms.F_blade_occ.modulation_std_db', '{:.2f}', 'dB')} 다"
                f"({_L('physics.n_t', '{:,.0f}', '표본')} 한 창).",

                f"프로펠러 채널의 레벨은 전체 채널보다 **{_GAP}** 아래다({_GAP_SRC}) — 동체가 "
                f"그만큼 밝다. ⛔ 절대 레벨 두 수는 판 선택 위에 있어 본문 밖이고, 차는 판 셋 "
                f"흩어짐 {_n('verdict.abs_level_plate_ptp_db', FPS, '{:.2f}', 'dB')} 를 넘는다.",

                f"동체:날개 비가 전체 채널에서 "
                f"{_L('arms.B_sbr_spread.dc_over_ac', '{:.2f}')}, 프로펠러 채널에서 "
                f"{_L('arms.F_blade_occ.dc_over_ac', '{:.3f}')} 다.",

                f"⭐ 블레이드 신호가 약한 것이 아니라 **동체 정적 반사가 덮고 있다** — "
                f"그것이 전처리에서 정적 성분을 지우는 이유다.",

                f"어려운 것은 «블레이드가 약하다» 가 아니라 **«동체와 블레이드를 가르는 일»** 이다.",
            ],
            method=[
                ("채널 분리",
                 "같은 얼린 판·같은 자세·같은 로터 회전수의 **두 실행**이다 — 한쪽은 동체를 "
                 "완전흡수(Γ=0)로 두어 프로펠러 채널만 남긴다"),
                ("어느 팔인가",
                 "두 열 다 **B** = " + ARM_SBR + " 이다. «동체를 막느냐» 라는 스위치는 이 팔 "
                 "쪽에만 있고, 순수 PO 팔은 이 축의 밖에 선다"),
                ("변조 깊이 — 두 자",
                 "슬로타임 |h| [dB] 의 표준편차(std ⭐)와 최대−최소(p-p ⛔). 동체 정적 반사가 "
                 "크면 두 값이 다 눌린다. 이 편이 인용하는 자는 std 다 — p-p 는 표본 수 N 에 "
                 "딸려 자란다"),
                ("동체:날개 비",
                 "DC(정적 성분) 대 AC(변조 성분) 의 비. 이 값이 클수록 동체가 덮는다"),
                ("절대 레벨을 어디에 두나",
                 "얼린 팔의 절대 레벨은 격자 판 한 장의 서브셀 오프셋에 걸린다(판 셋 p-p "
                 + _n("verdict.abs_level_plate_ptp_db", FPS, "{:.2f}", "dB")
                 + ") — 이 편은 두 채널의 **차와 비**만 읽는다"),
            ],
            prereq=[("앞 편", ref("md-occlusion", "가림 축") + " — 두 팔의 정의")],
            repro=REPRO_15B,
        ),

        md("## 같은 칸을 두 채널로 읽는다", "",
           *_fig(1, "report07_f3", "블레이드 신호는 약한가, 아니면 동체가 덮고 있는가?"),
           "⛔ **이 그림의 밴드별 dB 는 원장 밖이다** — 값이 그림 빌더에 박혀 있고"
           "(`benchmark/build_report07_figs.py:221-222`, 2026-08-07 실행) 그 실행의 원장이 "
           f"`outputs/` 에 없다. 지금 서 있는 원장 `{MDB}` 은 **한 밴드**"
           f"(`_meta.fc_hz` = 3.5 GHz)뿐이라, 나머지 다섯 밴드는 «원장 없음» 이다.", "",
           "⇒ 그림에서 읽는 것은 **두 채널의 순서**이고, dB 는 아래 표(원장)에서만 읽는다.", "",
           "두 채널은 **같은 얼린 판·같은 자세·같은 로터 회전수**의 두 실행에서 나온다 — "
           "한쪽은 동체를 완전흡수로 두어 프로펠러 채널만 남긴다."),

        md("## 두 채널의 값", "",
           f"둘 다 **B** = {ARM_SBR} 이고, 로터 회전수는 두 열이 같다(흩뜨린 판).", "",
           table(["무엇을", "전체 드론 채널 (B_sbr_spread)", "프로펠러 채널 (F_blade_occ)"], [
               ["변조 깊이 — std ⭐ / p-p ⛔",
                _L("arms.B_sbr_spread.modulation_std_db", "{:.2f}") + " / "
                + _L("arms.B_sbr_spread.modulation_ptp_db", "{:.2f}", "dB"),
                _L("arms.F_blade_occ.modulation_std_db", "{:.2f}") + " / "
                + _L("arms.F_blade_occ.modulation_ptp_db", "{:.2f}", "dB")],
               ["레벨 (절대)", "⛔ 본문 밖 — 판 셋 p-p "
                + _n("verdict.abs_level_plate_ptp_db", FPS, "{:.2f}", "dB"),
                "⛔ 본문 밖 — 같은 이유"],
               ["레벨 차 (전체 − 프로펠러)", _GAP + " — 흩어짐을 넘는 양이라 이 편이 쓴다", "—"],
               ["동체:날개 비",
                _L("arms.B_sbr_spread.dc_over_ac", "{:.2f}"),
                _L("arms.F_blade_occ.dc_over_ac", "{:.3f}")],
               ["반창 스펙트럼 상관",
                _L("arms.B_sbr_spread.half_window_spectrum_corr", "{:.4f}"),
                _L("arms.F_blade_occ.half_window_spectrum_corr", "{:.4f}")],
           ]), "",
           f"⭐ 프로펠러 채널의 변조가 전체 채널보다 **깊고**, 레벨은 반대로 **{_GAP}** "
           f"아래다({_GAP_SRC}). 두 줄을 같이 읽으면 **동체가 밝아서 변조를 눌렀다** 가 나온다 "
           f"— 이 편이 세우는 것은 이 **방향**이다.", "",
           f"⛔ **몇 배인가는 이 원장으로 정하지 못한다 — 자와 표본 수에 딸린다.** "
           f"{_L('physics.n_t', '{:,.0f}', '표본')} 한 창에서 std 로 {_R_STD:.1f} 배 · p-p 로 "
           f"{_R_PTP:.1f} 배이고, 같은 창을 등간격으로 솎아 N 을 60 으로 줄이면 std 는 "
           f"{_F60['std'] / _B60['std']:.1f} 배로 붙지만 p-p 는 "
           f"{_F60['ptp'] / _B60['ptp']:.1f} 배로 내려간다. ⚠ 판 축은 `ptp_db` 로만 재어 두었다 "
           f"— 판 원장(`{FPS}`)은 팔마다 `ptp_db` 와 `level_db` 만 들고, 그 `ptp_db` 는 판 셋에서 "
           + _n(f"{LEAD}.arms.F_blade_occ.ptp_db.ptp", FPS, "{:.2f}", "dB")
           + " 흔들린다.", "",
           "⛔ 절대 레벨 두 수는 원장에 있고 본문 밖이다 — 얼린 팔의 절대 레벨은 격자 판 한 "
           "장의 서브셀 오프셋에 걸리고, 절대 σ 는 디더를 켠 정적 경로가 낸다. 이 편이 쓰는 "
           f"것은 **차**이고, 그 차 {_GAP} 는 판 흩어짐의 여섯 배다."),

        md("## 그래서 무엇이 어려운가", "",
           "전기적으로 보면 블레이드 폭은 우리 대역에서 파장의 한 자릿수 분율이다. 그런데도 "
           "SBR 팔이 낸 프로펠러 채널의 변조 자체는 "
           + _L("arms.F_blade_occ.modulation_std_db", "{:.2f}", "dB") + "(std) · "
           + _L("arms.F_blade_occ.modulation_ptp_db", "{:.1f}", "dB")
           + "(p-p) 로, 전체 드론 채널의 "
           + _L("arms.B_sbr_spread.modulation_std_db", "{:.2f}", "dB")
           + "(std) 보다 깊다.", "",
           "어려운 것은 «블레이드가 약하다» 가 아니라 **«동체와 블레이드를 가르는 일»** 이다. "
           "검출 축에서 정적 성분을 지우는 이유가 여기 있고, 그 노치가 호버 표적의 동체까지 "
           "지우는 대가도 여기서 나온다.", "",
           "⚠ PO 커널이 블레이드 폭에서 얼마나 약한지는 "
           + ref("ladder-premature", "사다리 판정 조건") + " 이 dB 로 적었다."),

        next_steps([
            ("정적 성분 제거 뒤의 블레이드 채널로 검출을 돌린다",
             "«동체를 지우는 대가» 와 «블레이드를 얻는 이득» 이 같은 저울에 올라간다",
             ref("md-prf", "상시 신호의 상한")),
            ("동체:날개 비를 자세 격자로 넓힌다",
             "어느 자세에서 블레이드가 드러나는지의 지도가 선다",
             ref("md-attitude", "자세 축")),
        ]),
    ]


# =========================================================================== #
#  편 40 — 자세
# =========================================================================== #
def blocks_40() -> list:
    NOSE = "cells.matrice4e/nose"
    SIDE = "cells.matrice4e/belly_side"

    # ── 이 편이 나눠 쓰는 두 잣대 ──────────────────────────────────────────
    #  변조 **폭**       = 두 팔 dB 열의 표준편차 차 (`modulation_std_db`)
    #  변조 **깊이 p-p** = 같은 열의 max−min 차     (`occlusion_ptp_db`)
    #  아래 도구는 원본 열(`SER`)을 stride 로만 솎아 두 잣대가 표본수에 어떻게 걸리는지를
    #  인쇄한다 — 판도 자세도 로터도 안 건드리고, 난수도 안 쓴다(흔드는 손잡이는 stride 하나).
    import numpy as _np

    _NT_ = int(fetch((MDB, LEAD + ".physics.n_t")))

    def _ser(cell: str, arm: str):
        """그 칸·그 팔의 슬로타임 dB 열 — 원장 숫자가 나온 바로 그 열이다."""
        E = _np.asarray(fetch((SER, f"{cell[len('cells.'):]}/{arm}/E")))
        return 20 * _np.log10(_np.maximum(_np.abs(E), 1e-30))

    def _ptp(x) -> float:
        return float(_np.max(x) - _np.min(x))

    def _sdv(x) -> float:
        return float(_np.std(x))

    def _thin(cell: str, stride: int, stat) -> list:
        """stride 로만 솎은 F−G — 위상 stride 개의 값."""
        F, G = _ser(cell, "F_blade_occ"), _ser(cell, "G_blade_free")
        return [stat(F[p::stride]) - stat(G[p::stride]) for p in range(stride)]

    def _lad(cell: str, stride: int, stat) -> str:
        """사다리 한 칸 — «뽑기 중앙값 (그 뽑기들의 p-p)»."""
        v = _thin(cell, stride, stat)
        return f"{_np.median(v):+.2f} (p-p {_ptp(v):.2f})"

    def _lad_ko(cell: str, stride: int, stat) -> str:
        """산문용 사다리 한 칸 — «중앙값 X dB · 뽑기 p-p Y dB»."""
        v = _thin(cell, stride, stat)
        return f"중앙값 {_np.median(v):+.2f} dB · 뽑기 p-p {_ptp(v):.2f} dB"

    def _val(cell: str, stat) -> float:
        """솎지 않은 전체 열의 F−G."""
        return stat(_ser(cell, "F_blade_occ")) - stat(_ser(cell, "G_blade_free"))

    def _full(cell: str, stat) -> str:
        return f"{_val(cell, stat):+.2f}"

    def _span(stat) -> str:
        """사다리 네 칸(솎기 셋 + 전체) **중앙값**이 옮겨 간 폭 — 칸마다 한 수."""
        out = []
        for _, k in _CELLS:
            m = [float(_np.median(_thin(k, s, stat))) for s in _STR] + [_val(k, stat)]
            out.append(f"{max(m) - min(m):.2f}")
        return " · ".join(out)

    def _sd_gap(cell: str) -> float:
        """변조 폭 차 — 원장 두 키의 차다(손으로 적은 값이 아니다)."""
        return (fetch((MDB, f"{cell}.arms.F_blade_occ.modulation_std_db"))
                - fetch((MDB, f"{cell}.arms.G_blade_free.modulation_std_db")))

    _CELLS = [("코 쪽", NOSE), ("배 쪽", LEAD), ("배 옆", SIDE)]
    _STR = (40, 8, 2)                       # 흔드는 손잡이 — 솎기 간격 하나뿐이다
    _NS = [_NT_ // s for s in _STR]         # 그 간격이 남기는 표본수(손으로 안 적는다)
    _SDG = {k: f"{_sd_gap(k):+.2f} dB" for _, k in _CELLS}
    _SDG_SRC = (f"`{MDB} : cells.*.arms."
                + "{F_blade_occ, G_blade_free}.modulation_std_db` 의 차")
    _NT = _n(LEAD + ".physics.n_t", MDB, "{:,.0f}", "표본")
    #: 배 옆 F 팔의 깊이에서 «가장 깊은 한 표본» 을 뺀 뒤와, 그 한 표본이 내는 몫.
    _F1 = _ptp(_np.sort(_ser(SIDE, "F_blade_occ"))[1:])
    _F1_CUT = _ptp(_ser(SIDE, "F_blade_occ")) - _F1

    return [
        header(
            num=40,
            title="지상 레이더는 기체를 아래에서 보므로 가림이 무는 자세가 우리 자세다",
            did="같은 기체를 코 쪽·배 쪽·배 옆 세 자세에서 돌려 가림과 변조가 자세에 따라 어떻게 "
                "움직이는지 쟀다.",
            results=[
                f"프로펠러는 동체 **위**에 있다 — 위에서 내려다보는 자세에서는 날개가 통째로 "
                f"드러나고, 아래에서 보는 자세에서 가림이 문다.",

                f"코 쪽(앙각 {_n(NOSE + '.el_deg', MDB, '{:.0f}', '도')})의 가림 효과는 변조 "
                f"폭 {_SDG[NOSE]} · 레벨 "
                f"{_n(NOSE + '.findings.occlusion_level_db', MDB, '{:+.2f}', 'dB')} 다 — 변조 "
                f"폭은 두 팔 dB 열의 표준편차 차(`modulation_std_db`)다.",

                f"배 쪽(앙각 {_L('el_deg', '{:.0f}', '도')})에서는 {_SDG[LEAD]} · "
                f"{_L('findings.occlusion_level_db', '{:+.2f}', 'dB')}, 배 옆(방위 "
                f"{_n(SIDE + '.az_deg', MDB, '{:.0f}', '도')})에서는 {_SDG[SIDE]} · "
                f"{_n(SIDE + '.findings.occlusion_level_db', MDB, '{:+.2f}', 'dB')} 다 — 세 칸이 "
                f"서로 다른 값을 낸다.",

                f"⚠ 세 자세의 dB 는 판 한 장과 표본수 위에 있다 — 판을 반 칸 옮기면 레벨 차가 "
                f"판 셋에서 {_n('verdict.occlusion_level_plate_ptp_db', FPS, '{:.2f}', 'dB')} "
                f"p-p 로 흩어지고, 원장은 «레벨 차가 판 선택을 견디는가» 에 "
                f"{_n('verdict.occlusion_level_survives_plate_choice', FPS)} 라고 적는다. "
                f"⛔ 변조 깊이 p-p 는 판을 그대로 두고 표본만 {_NS[0]:,} 개로 솎아도 배 옆에서 "
                f"{_lad_ko(SIDE, _STR[0], _ptp)} 로 흔들린다. 이 편이 세우는 것은 **가림이 "
                f"자세에 따라 다르게 문다**는 존재다.",

                f"자유공간 바이스태틱의 이등분선 앙각은 전 구간 음수라 우리는 드론 배를 본다 — "
                f"자세 스윕이 그 문장에 독립적인 근거를 붙였다.",
            ],
            method=[
                ("자세 세 칸",
                 "코 쪽(앙각 +15°) · 배 쪽(앙각 −15°) · 배 옆(방위 90° · 앙각 −15°). "
                 "기체 좌표계에서 앙각이 음수면 아래에서 보는 것이다"),
                ("가림 단일축",
                 "칸마다 «동체가 막느냐» 만 다른 두 팔을 돌려 그 자세의 가림 효과를 낸다"),
                ("왜 배 쪽이 헤드라인인가",
                 "지상 레이더는 비행 중인 기체를 아래에서 본다 — 자유공간 바이스태틱 기하가 "
                 "이미 그렇게 적혀 있다"),
                #: ⛔2026-09-04 — «겹친 삼각형이 **남아 있어**» 는 현재형이라 틀렸다.
                #  겹침은 2026-08-10 에 닫혔다 — `outputs/meshfix_mini5pro_overlap.json`
                #  「그 0.81 % 를 스탠드오프 1.0 mm(raw) 한 항목으로 **0.00 %** 로 닫았다」·
                #  `src/mesh_check.py` 도 0.00 % 로 적는다. 남은 것은 **그림의 원장 세대**다.
                ("Mini 5 Pro",
                 "이 그림들은 2026-08-10 겹침 수리 **이전** 원장으로 그린 것이라 헤드라인에서 "
                 "뺐다(현 메쉬의 프롭·벨 겹침은 0.00 % 다). 같은 그림을 그 기체로도 그려 "
                 "따로 뒀다"),
                ("⭐얼린 광선 격자",
                 "세 칸의 여섯 팔이 모두 로터 한 바퀴의 합집합 경계상자로 만든 판 한 장을 "
                 "쓴다. 그래야 프레임 사이 위상차가 표적의 운동만 담는다"),
                ("⭐두 잣대",
                 "변조 **폭** = 두 팔 dB 열의 표준편차 차(`modulation_std_db`), 변조 **깊이 "
                 "p-p** = 같은 열의 max−min 차(`occlusion_ptp_db`). 흔드는 손잡이는 솎기 간격 "
                 f"하나다 — {_NS[0]:,} 표본으로 솎을 때와 {_NT} 전부일 때 사이에서 사다리 "
                 f"중앙값이 깊이 p-p 는 코 쪽·배 쪽·배 옆 {_span(_ptp)} dB, 변조 폭은 "
                 f"{_span(_sdv)} dB 옮겨 간다(본문 표가 뽑기 산포까지 인쇄한다)"),
                ("⚠ 부호와 크기를 인용하는 범위",
                 "자세를 고정한 채 판만 반 칸 옮겨도 가림 dB 의 부호가 갈린다(레벨 차 판 셋 "
                 "p-p " + _n("verdict.occlusion_level_plate_ptp_db", FPS, "{:.2f}", "dB")
                 + " · 변조 깊이 판 셋 p-p "
                 + _n("verdict.occlusion_ptp_plate_ptp_db", FPS, "{:.2f}", "dB")
                 + " · 레벨 차가 판 선택을 견디는가 = "
                 + _n("verdict.occlusion_level_survives_plate_choice", FPS)
                 + "). 이 절은 **가림이 자세에 따라 다르게 문다**는 존재를 쓰고, 부호와 크기는 "
                 "판 앙상블 평균 뒤로 미룬다. ⚠ 판 재실행 원장은 변조 폭을 판마다 적어 두지 "
                 "않았으므로, 변조 폭이 판 선택을 견디는지는 이 원장으로 정할 수 없다"),
            ],
            prereq=[("앞 편", ref("md-occlusion", "가림 축") + " — 칸마다 도는 단일축")],
            repro=REPRO_15B,
        ),

        md("## 자세가 답을 바꾼다", "",
           "프로펠러는 동체 **위**에 있다. 그래서 위에서 내려다보면 날개가 통째로 드러나고, "
           "그 자세에서 가림은 0 에 가깝다.", "",
           "지상 레이더는 비행 중인 기체를 **아래에서** 보므로 기체 좌표계로 앙각이 음수이고, "
           "거기서 가림이 문다.", "",
           "⛔ 이 편의 자세 축은 **아래 표(원장)** 로 읽는다. 자세·기체별 요약 그림 "
           f"`{FIG}/report15b_f3.png` 의 dB 라벨은 지금 서 있는 원장 `{MDB}` 의 값과 다르다 — "
           "그림 빌더(`benchmark/build_report15b_figs.py::fig3_summary`)를 다시 돌리면 그 "
           "라벨이 아래 표와 같은 세대가 되고, 그때 이 자리에 들어온다."),

        md("## 세 자세의 값", "",
           table(["자세", "방위", "앙각", "가림 · 변조 폭",
                  "가림 · 변조 깊이 p-p ⚠", "가림 · 레벨"], [
               ["코 쪽",
                _n(NOSE + ".az_deg", MDB, "{:.0f}", "°"),
                _n(NOSE + ".el_deg", MDB, "{:.0f}", "°"),
                _SDG[NOSE],
                _n(NOSE + ".findings.occlusion_ptp_db", MDB, "{:+.2f}", "dB"),
                _n(NOSE + ".findings.occlusion_level_db", MDB, "{:+.2f}", "dB")],
               ["배 쪽 ⭐",
                _L("az_deg", "{:.0f}", "°"), _L("el_deg", "{:.0f}", "°"),
                _SDG[LEAD],
                _L("findings.occlusion_ptp_db", "{:+.2f}", "dB"),
                _L("findings.occlusion_level_db", "{:+.2f}", "dB")],
               ["배 옆",
                _n(SIDE + ".az_deg", MDB, "{:.0f}", "°"),
                _n(SIDE + ".el_deg", MDB, "{:.0f}", "°"),
                _SDG[SIDE],
                _n(SIDE + ".findings.occlusion_ptp_db", MDB, "{:+.2f}", "dB"),
                _n(SIDE + ".findings.occlusion_level_db", MDB, "{:+.2f}", "dB")],
           ]), "",
           f"변조 폭 열은 두 팔 dB 열의 표준편차 차이고({_SDG_SRC}), 세 열 모두 그 자세의 "
           f"슬로타임 {_NT} 전부로 잰 값이다. 세 줄이 서로 다른 값을 낸다 — **가림이 자세에 "
           f"따라 다르게 문다**는 것이 이 편의 내용이고, 그 dB 의 부호와 크기는 아래 절이 판 "
           f"앙상블 평균 뒤로 미룬다.", "",
           "⚠ **변조 깊이 p-p 열의 쓰임은 «그 자세에서 한 표본이 얼마나 깊이 떨어지나» 까지다** "
           "— 자세끼리의 비교는 변조 폭 열이 맡는다. 그 이유는 아래 «두 잣대를 표본수로 "
           "흔들었다» 절이 사다리로 인쇄한다.", "",
           "마이크로도플러는 프레임 사이 위상차로 재는 양이라, 광선 격자가 프레임마다 "
           "움직이면 그 움직임이 표적 운동과 같은 자리에 실린다. 그래서 커널은 자세 전체에 "
           "한 격자를 고정하고(`grid_ref`), **이 표는 그 얼린 판으로 다시 난 원장에서 나왔다** "
           f"⟨{MDB} : _meta.grid_frozen⟩. 옛 판의 값은 `outputs/prefreeze/` 에 사본으로 있다.", "",
           "⚠ 메쉬 지문(`mesh_provenance`)은 도장 스크립트를 돌린 다음 세대부터 이 원장에 "
           "실린다. 지문이 찍히면 표가 어떤 메쉬 세대에서 났는지까지 자기가 말한다."),

        md("## 두 잣대를 표본수로 흔들었다", "",
           table(["잣대 · 칸"] + [f"{n:,} 표본" for n in _NS] + [f"{_NT_:,} 표본(원장)"],
                 [[f"변조 깊이 p-p · {nm}"]
                  + [_lad(k, s, _ptp) for s in _STR] + [_full(k, _ptp)]
                  for nm, k in _CELLS]
                 + [[f"변조 폭 · {nm}"]
                    + [_lad(k, s, _sdv) for s in _STR] + [_full(k, _sdv)]
                    for nm, k in _CELLS]), "",
           f"같은 기록을 stride 로만 솎았다 — 판도 자세도 로터도 그대로이고, 흔든 손잡이는 "
           f"솎기 간격 하나다. 칸의 값은 «위상 stride 개 뽑기의 중앙값 (그 뽑기들의 p-p)» 이고 "
           f"마지막 열이 원장이 쓴 {_NT} 전부다. 판 사이 차이는 아래 절이 따로 잰다.", "",
           f"⭐ 사다리 네 칸의 **중앙값**이 옮겨 간 폭은 깊이 p-p 가 코 쪽·배 쪽·배 옆 "
           f"{_span(_ptp)} dB 이고(코 쪽과 배 옆은 부호까지 바뀐다), 같은 사다리에서 변조 폭은 "
           f"{_span(_sdv)} dB 다. ⛔ 깊이 p-p 가 무엇을 읽는지는 배 옆 칸이 보여 준다 — F 팔의 변조 깊이 "
           f"{_n(SIDE + '.arms.F_blade_occ.modulation_ptp_db', MDB, '{:.2f}', 'dB')} 가운데 "
           f"{_F1_CUT:.2f} dB 를 {_NT} 중 **가장 깊은 한 표본**이 낸다(그 한 표본을 빼면 "
           f"{_F1:.2f} dB 다)."),

        md("## 판 한 장이 그 dB 의 부호를 정한다", "",
           "판의 중심만 **반 칸** 옮긴 같은 크기의 판으로 같은 자세를 다시 태우면 가림 dB 가 "
           "판마다 이렇게 갈린다 — 세 판(P0 · 반 칸 둘)의 값이다. ⚠ 이 재실행은 생산 슬로타임 "
           f"열을 stride {_n('_meta.stride', FPS, '{:.0f}')} 로 솎은 "
           f"{_n('cells.matrice4e/belly.n_pose', FPS, '{:,.0f}', '표본')} 판이라, 위 표"
           f"({_NT})와는 표본수가 다른 추정치다.", "",
           table(["칸", "가림 · 변조 깊이 p-p (판 셋)", "가림 · 레벨 (판 셋)"],
                 [[f"`{k}`",
                   " / ".join(_n(f"cells.{k}.findings.occlusion_ptp_db.values[{i}]",
                                 FPS, "{:+.2f}") for i in range(3)),
                   " / ".join(_n(f"cells.{k}.findings.occlusion_level_db.values[{i}]",
                                 FPS, "{:+.2f}") for i in range(3))]
                  for k in fetch((FPS, "cells"))]), "",
           "⭐ 한 자세 안에서 부호가 갈린다. 레벨 차의 판 셋 흩어짐 "
           + _n("verdict.occlusion_level_plate_ptp_db", FPS, "{:.2f}", "dB")
           + " p-p 가 위 세 자세의 레벨 크기를 삼키고, 원장은 «레벨 차가 판 선택을 견디는가» 에 "
           + _n("verdict.occlusion_level_survives_plate_choice", FPS)
           + " 라고 적는다"
           + f" ⟨{FPS} : verdict.how_to_read_ko⟩.", "",
           "⛔ 깊이 p-p 열의 판 셋 흩어짐 "
           + _n("verdict.occlusion_ptp_plate_ptp_db", FPS, "{:.2f}", "dB")
           + " p-p 를 «반 칸 옮기면 가림 효과가 그만큼 바뀐다» 로 읽지 않는다. 세 판이 같은 "
           "슬로타임 표본을 쓰므로(`benchmark/adv_freeze_plate_sensitivity.py` 의 "
           "`idx = np.arange(0, n_t, stride)` 한 줄을 세 판이 공유한다) 그 흩어짐이 판에서 온 "
           "것은 맞다. 같은 통계량은 판을 하나도 안 옮기고 어느 표본을 뽑느냐만 바꿔도 배 쪽에서 "
           + f"{_lad_ko(LEAD, _STR[0], _ptp)} 로 흔들리는데, 뽑기 수(판 셋 · 위상 {_STR[0]}가지)가 "
           + f"달라 두 p-p 의 크기 비교는 이 원장 밖이다.", "",
           "⇒ 이 편이 세우는 것은 **가림이 자세에 따라 다르게 문다**는 존재이고, 그 dB 의 "
           "부호와 크기는 판 앙상블 평균(오프셋 여러 판의 평균)이 낸다. 기전은 "
           + ref("kernel-what", "커널이 하는 일") + " 이 잰다."),

        md("## 이 결론은 우리 기하 명세와 같은 방향이다", "",
           "자유공간 바이스태틱의 이등분선 앙각은 전 구간 음수라 우리는 드론 배를 본다. "
           "자세 스윕이 그 문장에 **독립적인 근거**를 붙였다 — 기하 명세와 광선 추적이 서로 "
           "다른 길로 같은 자세를 가리킨다.", "",
           f"⚠ Mini 5 Pro 의 그림은 2026-08-10 **겹침 수리 이전** 원장으로 그린 것이라 "
           f"헤드라인에서 뺐다. 같은 그림을 그 기체로도 그려 `{FIG}/report15b_f1b.png` · "
           f"`{FIG}/report15b_f2b.png` 에 뒀다 — 옛 세대 값이라는 것을 알고 읽는다. "
           f"⭐현 메쉬의 프롭·벨 겹침은 스탠드오프 1.0 mm 로 **0.00 %** 다"
           f"⟨outputs/meshfix_mini5pro_overlap.json : headline_ko⟩."),

        next_steps([
            ("가림을 자세 전면(방위×앙각 격자)으로 넓힌다",
             "어느 자세에서 얼마나 무는지의 지도가 서고, 그 지도가 분류기의 입력이 된다",
             "이 편의 세 칸을 격자로"),
            ("**수리된 메쉬(스탠드오프 1.0 mm)로** 같은 세 칸을 다시 돌린다",
             "두 기체의 자세 의존이 같은 잣대 위에 올라온다",
             "이 편 재실행 — 메쉬 정정은 2026-08-10 에 끝났다"),
            ("판 재실행을 솎기 없이 돌리고 판마다 `modulation_std_db` 를 적는다",
             "변조 폭이 판 선택을 견디는지가 같은 표본수 위에서 판정된다",
             "`benchmark/adv_freeze_plate_sensitivity.py` — stride 1 · 표준편차 기록 추가"),
        ]),
    ]


# =========================================================================== #
#  편 41 — 판정 잣대 교정
# =========================================================================== #
def blocks_41() -> list:
    CA = "criterion_a_calibration"
    IR = "ideal_reference"
    NV = "verdict"
    NS = "q1_noise_floor.null_sample_census"

    return [
        header(
            num=41,
            title="문턱은 널 팔이 교정했고, 가장자리 시험은 아직 교정되지 않았다",
            did="변조가 나오면 안 되는 물체와 이상 점산란자를 같은 측정법에 넣어 판정 문턱이 "
                "거짓양성과 거짓음성을 내는지 먼저 쟀다.",
            results=[
                f"널 팔 {_n(CA + '.n_null_cells', VRD, '{:.0f}', '칸')} 에서 변조 판정이 "
                f"{_n(CA + '.n_null_firing', VRD, '{:.0f}', '번')} 켜졌다 — 최댓값 "
                f"{_n(CA + '.max_null_ac_over_noise_db', VRD, '{:.2f}', 'dB')} 가 문턱 "
                f"{_n(CA + '.threshold_db', VRD, '{:.1f}', 'dB')} 아래에 든다.",

                f"신호 팔은 {_n(CA + '.n_signal_cells', VRD, '{:.0f}', '칸')} 중 "
                f"{_n(CA + '.n_signal_firing', VRD, '{:.0f}', '칸')} 이 켜진다 — 문턱이 "
                f"양쪽에서 작동한다. 그 신호 칸은 **S** 팔({ARM_SIONNA} · 스톡 그대로)로 낸 "
                f"**Mini 2** 한 기체이고, 거리 1·3·10 m × 채널 둘이다 — 칸 이름이 원장에 "
                f"그대로 있다(`{CA}.rows`).",

                f"⚠ 두 번째 잣대인 **가장자리 시험은 아직 안 섰다** — 반드시 통과해야 하는 "
                f"이상 점산란자가 {_n(IR + '.n', VRD, '{:.0f}')} 칸 중 "
                f"{_n(IR + '.n_pass', VRD, '{:.0f}')} 칸만 통과하고, 산출물도 그 시험이 "
                f"교정됐느냐에 {_n(IR + '.test_is_calibrated', VRD)} 라고 적는다. "
                f"이 편이 세운 것은 문턱(기준 a)이고, 가장자리(기준 b)는 아니다.",

                f"널 팔 전용 재계산에서도 같은 결론이다 — 신호 대 인공물 여유 "
                f"{_n(NV + '.margin_rescaled_db', NUL, '{:.2f}', 'dB')} 이고, 신호 변조 깊이를 "
                f"인공물 바닥으로 **dB 값끼리 나눈 비**(분자·분모가 둘 다 dB 값이다)가 "
                f"{_n(NV + '.signal_over_floor_ratio', NUL, '{:.1f}')} 다.",

                f"⚠ 적대검증이 널 셈을 정정했다 — 실제로 시험된 널은 "
                f"{_n(NS + '.n_null_cells_with_a_value', ATK, '{:.0f}', '칸')} 이고 나머지 "
                f"{_n(NS + '.n_null_cells_degenerate_no_value', ATK, '{:.0f}', '칸')} 은 "
                f"AC 가 정확히 0 이라 시험 자체가 성립하지 않는 칸이다.",
            ],
            method=[
                ("판정량 — 무엇을 무엇으로 나눈 값인가",
                 "**변조 전력 총합 ÷ 재추적 잡음 전력 총합** [dB] 이다(0 이 아닌 도플러 빈의 "
                 "신호 전력 합 대 같은 빈의 잡음 전력 합). 이 값이 문턱을 넘으면 «변조가 "
                 "있다» 로 찍는다 — `benchmark/report15_verdict.py` 의 판정 (a)"),
                ("널 설계 다섯 갈래",
                 "메쉬 완전 동결 · 프로펠러 제거 · 회전대칭 원판 · 등가부피 구 z 회전 · "
                 "같은 구 텀블 — 각 널이 서로 다른 고장모드를 막는다"),
                ("양성 대조",
                 "기체 전체를 돌린 팔을 함께 넣어 «켜져야 할 때 켜지는지» 를 확인했다"),
                ("바닥 정규화",
                 "널의 재추적 잡음이 신호팔보다 조용하다는 반론에 대해, 바닥을 "
                 "σ_signal/σ_null 로 환산해 보수적으로 다시 잡았다"),
                ("이상 점산란자",
                 "같은 메쉬로 산란 물리를 빼고 왕복 위상만 더한 기준 — 이 모형이 같은 시험을 "
                 "통과하지 못하면 시험이 틀린 것이다"),
                ("해상도 사다리",
                 "삼각형 100/50/25/12.5 % 로 재고 ptp 뿐 아니라 곡선 상관까지 봤다"),
            ],
            repro=dict(
                cmd=["PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report15_null_control_v2.py",
                     "PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report15_verdict_geomref.py",
                     "PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report15_verdict.py",
                     "PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report15_attack_stats.py"],
                out=[NUL, GEO, VRD, ATK],
                runtime="약 35 분 (GPU 1장 — 널 팔 "
                        + _n("verdict.n_null_arms", NUL, "{:.0f}", "개") + ")"),
        ),

        md("## 잣대를 먼저 교정하는 이유", "",
           "«나왔다» 를 말하려면 «안 나와야 하는 것이 안 나온다» 를 먼저 보여야 한다. "
           "회전대칭 물체는 돌려도 모양이 안 바뀌므로 변조를 만들 방법이 기하학적으로 막혀 있다 — "
           "그런 물체에서 변조가 보이면 그것은 측정법이 만든 인공물이다.", "",
           "반대 방향도 필요하다. 이상 점산란자처럼 «반드시 통과해야 하는» 모형이 같은 시험에서 "
           "떨어지면, 틀린 것은 대상이 아니라 시험이다."),

        md("## 널과 신호가 같은 문턱 아래에서 갈린다", "",
           *_fig(1, "report15_f1",
                 "변조가 나오면 안 되는 물체에서도 무늬가 보이는가?"),
           f"위 네 줄이 신호 팔이다 — 두 기체(Mini 2 · Matrice 4E) 각각을 **S** = {ARM_SIONNA}"
           "(그림의 `Sionna` 줄 · 스톡 그대로) 와 **P** = 가림 없는 순수 PO 커널(그림의 "
           "`PO kernel` 줄) 로 낸 프로펠러 채널 네 줄이다. 맨 아래 한 줄이 **널 팔 넷 중 가장 "
           "시끄러운 것**이다 — 대표는 자료가 고른다(세 거리 최대 측대역의 최댓값).", "",
           "⚠ 이 그림의 네 줄과 위 교정 격자는 범위가 다르다 — 교정 격자의 신호 칸 "
           + _n(CA + ".n_signal_cells", VRD, "{:.0f}", "개") + " 는 **S** 팔의 Mini 2 뿐이다.", "",
           "가장 시끄러운 널이 조용하면 나머지도 조용하므로, 나머지 세 줄은 그리지 않고 "
           "수치로 접었다. 접는 규칙과 접힌 값은 그림 빌더가 `null_rows_folded` 로 함께 "
           "낸다(`benchmark/report15_verdict_build.py::fig1_spectrograms`). "
           "⚠ 지금 원장(`" + VRD + " : figures.f1`)에는 그 키가 없다 — 그림을 다시 낼 때 "
           "채워진다.", "",
           "색눈금은 각 패널 자신의 정적 반사를 0 dB 로 잡은 값이다. ⭐**신호 줄은 블레이드 "
           "박자로 띠가 뛰고, 널 줄은 시간에 전혀 안 변한다** — 표시 규약이 0 도플러를 "
           "지우지 않으므로 널 줄에도 정지 반사 그 자체는 0 dB 로 남는다.", "",
           "즉 «검다» 가 아니라 «안 움직인다» 가 널의 표시다. 판마다 붙은 뱃지는 정적 성분을 "
           "지운 뒤의 최대 측대역을 그 패널 자신의 정적 반사 대비로 적은 값이고, 그 뱃지로 "
           "읽으면 신호 줄은 몇 dB 안쪽 · 널 줄은 수십 dB 아래다(뱃지 값 자체는 그림에만 "
           "있고 아직 원장 키로는 안 실린다)."),

        md("## 교정 결과", "",
           table(["무엇을", "값"], [
               ["널 칸 수", _n(CA + ".n_null_cells", VRD, "{:.0f}", "칸")],
               ["그중 판정이 켜진 칸", _n(CA + ".n_null_firing", VRD, "{:.0f}", "칸")],
               ["널 최댓값", _n(CA + ".max_null_ac_over_noise_db", VRD, "{:.2f}", "dB")],
               ["판정 문턱", _n(CA + ".threshold_db", VRD, "{:.1f}", "dB")],
               ["신호 칸 / 켜진 칸",
                _n(CA + ".n_signal_cells", VRD, "{:.0f}") + " / "
                + _n(CA + ".n_signal_firing", VRD, "{:.0f}")],
               ["이상 점산란자 통과",
                _n(IR + ".n_pass", VRD, "{:.0f}") + " / " + _n(IR + ".n", VRD, "{:.0f}")],
           ])),

        md("## 널 팔 전용 재계산이 같은 답을 낸다", "",
           table(["무엇을", "값"], [
               ["양성 대조가 켜졌나", _n(NV + ".positive_controls_fired", NUL)],
               ["널이 전부 조용한가", _n(NV + ".nulls_clean", NUL)],
               ["신호 변조 깊이", _n(NV + ".signal_ptp_db", NUL, "{:.2f}", "dB")],
               ["인공물 바닥(정규화)", _n(NV + ".artifact_floor_rescaled_db", NUL, "{:.3f}", "dB")],
               ["여유", _n(NV + ".margin_rescaled_db", NUL, "{:.2f}", "dB")],
               ["위 두 dB 값끼리의 비 (깊이 ÷ 바닥)",
                _n(NV + ".signal_over_floor_ratio", NUL, "{:.1f}")],
               ["해상도 사다리 최소 상관",
                _n(NV + ".resolution_min_pearson_r", NUL, "{:.4f}")],
           ])),

        md("## 적대검증이 정정한 두 가지", "",
           f"① 널 셈. 프로펠러를 제거한 팔 "
           f"{_n(NS + '.n_null_cells_degenerate_no_value', ATK, '{:.0f}', '칸')} 은 위상을 "
           f"돌려도 기하가 글자 그대로 같아서 AC 가 **정확히 0** 이다 — 시험을 통과한 칸이 "
           f"아니라 시험이 성립하지 않는 칸이다. 실제로 시험된 널은 "
           f"{_n(NS + '.n_null_cells_with_a_value', ATK, '{:.0f}', '칸')} 이다.", "",
           f"② 분포 겹침. 널 최댓값 "
           f"{_n(NS + '.null_max_db', ATK, '{:.2f}', 'dB')} 가 신호 격자 최솟값 "
           f"{_n(NS + '.null_max_vs_grid_min.grid_min_prop_db', ATK, '{:.2f}', 'dB')} 보다 "
           f"크다 — 문턱 {_n(NS + '.threshold_db', ATK, '{:.1f}', 'dB')} 는 두 분포의 «빈 "
           f"골짜기» 가 아니라 겹친 구간 위에 놓여 있다. 겹치는 칸들은 전부 무변조로 찍혔으므로 "
           f"이 겹침이 거짓양성을 만들지는 않았다.", "",
           "이 정정을 안고 읽어야 하는 판정이 " + ref("md-ray-budget", "광선예산 편") + " 이다."),

        next_steps([
            ("가장자리 시험을 이상 점산란자가 통과하는 창으로 다시 정의한다",
             "«가장자리가 예측과 맞는가» 판정이 교정된 시험 위에 선다",
             "`benchmark/report15_verdict.py` 의 (b) 규칙"),
            ("널 팔의 시드 수를 신호 격자와 같게 올린다",
             "널 최댓값의 신뢰구간이 좁아져 문턱을 겹침 밖으로 옮길 수 있다",
             "`benchmark/report15_null_control_v2.py` · GPU 반나절"),
        ]),
    ]


# =========================================================================== #
#  편 42 — 광선예산
# =========================================================================== #
def blocks_42() -> list:
    BL = "q1_noise_floor.budget_law"
    T = "tail_excess.by_airframe"
    SI = "q1_noise_floor.spp_dependence_existing.shape_invariance"

    return [
        header(
            num=42,
            title="두 기체가 갈리는 축은 메쉬 품질이 아니라 표적 크기 대비 광선예산이다 — "
                  "예산을 맞춰 확인하는 시험은 이 하네스에서 아직 못 한다",
            did="기하를 고정하고 광선예산만 사다리로 흔들어 다시 추적해 판정 통계가 경로수를 "
                "어떻게 따라가는지 쟀다.",
            results=[
                f"판정 통계는 경로수 1 dB 당 "
                f"{_n(BL + '.slope_db_per_db_of_paths_median', ATK, '{:.2f}', 'dB')} 로 "
                f"따라 올라간다 — 칸 {_n(BL + '.slope_n_cells', ATK, '{:.0f}', '개')} 의 "
                f"중앙값이다.",

                f"두 기체의 프롭 경로수 비는 "
                f"{_n(BL + '.median_path_count_ratio_m4e_over_mini2', ATK, '{:.2f}', '배')} "
                f"(Matrice 4E / Mini 2) 다. 예산 보정을 하면 자세 짝 "
                f"{_n(BL + '.n_pairs', ATK, '{:.0f}')} 중 "
                f"{_n(BL + '.n_pairs_where_mini2_wins_after_correction', ATK, '{:.0f}')} "
                f"에서 Mini 2 가 앞선다.",

                f"예산 보정 차이의 중앙값은 "
                f"{_n(BL + '.budget_corrected_delta_median_db', ATK, '{:+.2f}', 'dB')} 이고, "
                f"경로수를 맞추면 Mini 2 가 "
                f"{_n(BL + '.implied_mini2_boost_if_budget_matched_db', ATK, '{:+.2f}', 'dB')} "
                f"올라간다.",

                f"⚠ 예산을 맞추려면 "
                f"{_n(BL + '.spp_cap.factor_needed_for_match', ATK, '{:.2f}', '배')} 가 "
                f"필요한데 표본 인자가 uint32 라 올릴 수 있는 여유는 "
                f"{_n(BL + '.spp_cap.factor_available', ATK, '{:.1f}', '배')} 다 — 이 하네스로 "
                f"기체 비교를 닫으려면 표본 규칙을 먼저 바꿔야 한다.",

                f"그래서 Mini 2 의 무변조 칸 "
                f"{_n(BL + '.mini2_no_modulation_cells_now[0]', ATK)} 계열은 표적의 성질이 "
                f"아니라 예산의 성질이다.",
            ],
            method=[
                ("예산 사다리",
                 "기하·자세·재질을 고정하고 표본 인자만 "
                 + _n("meta.spp_ladder[0]", SPP, "{:,.0f}") + " → "
                 + _n("meta.spp_ladder[-1]", SPP, "{:,.0f}") + " 로 올려 새 시드로 다시 "
                 "추적했다"),
                ("기울기",
                 "판정 통계 [dB] 를 평균 경로수 [dB] 에 회귀한 기울기. 1 에 붙으면 통계가 "
                 "신호 세기가 아니라 **확신도**를 재고 있다는 뜻이다"),
                ("기체 짝 보정",
                 "두 기체의 같은 칸에서 판정 통계 차이를 경로수 차이로 나눠 보정했다"),
                ("독립 재현",
                 "같은 표본 인자·같은 칸을 새 시드 집합으로 다시 추적해 본 격자 값과 맞댔다"),
                ("모양 불변성",
                 "코히런트 조화의 **모양**이 예산에 불변한 거리를 따로 쟀다 — 그 거리 안에서만 "
                 "상대 스펙트럼을 인용한다"),
            ],
            prereq=[("앞 편", ref("md-calibration", "판정 잣대 교정") + " — 이 통계의 문턱")],
            repro=dict(
                cmd=["PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report15_attack_spp_ladder.py",
                     "PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report15_attack_stats.py"],
                out=[SPP, ATK],
                runtime="약 36 분 (GPU 1장 — 사다리 전량 재추적)"),
        ),

        md("## 판정량이 예산에 1 대 1 로 매달려 있다", "",
           *_fig(1, "report15_f3",
                 "경로수가 위상마다 껐다 켜지는가, 그리고 두 엔진은 거리에 따라 어떻게 갈리는가?"),
           "위 두 칸이 확산 채널의 경로수이고, 가운데가 정반사 채널, 아래가 거리별 두 엔진 "
           "일치도다.", "",
           "경로수 인구조사의 판정은 «" + _n("path_count_census.verdict_ko", VRD)
           + "» 이다 — 확산 채널은 위상에 따라 매끄럽게 변하고, 정반사 채널은 대부분의 칸이 "
           "통째로 비어 있다.", "",
           "오른쪽 아래에서 Matrice 4E 의 «hot» 자세만 거리와 함께 무너진다 — 그 자세의 "
           "경로수가 가장 적기 때문이다.", "",
           "⚠ **이 편의 «예산» 은 확산 채널의 이야기다 — 정반사 채널의 «0 칸» 까지 같은 축으로 "
           "읽지 마라.** 그 «0» 은 예산 축과 앙각 축을 따로 열어 별도로 시험했고 답이 기체마다 "
           "갈렸다. Matrice 4E: "
           + _n("verdict.matrice4e.verdict_ko", BFL)
           + " / Mini 2: " + _n("verdict.mini2.verdict_ko", BFL)
           + " 그 시험은 " + ref("md-two-engines", "두 엔진") + " 에 있다."),

        md("## 예산 법칙", "",
           table(["무엇을", "값"], [
               ["경로수 1 dB 당 판정 통계 상승",
                _n(BL + ".slope_db_per_db_of_paths_median", ATK, "{:.2f}", "dB")],
               ["잰 칸 수", _n(BL + ".slope_n_cells", ATK, "{:.0f}", "개")],
               ["두 기체 경로수 비",
                _n(BL + ".median_path_count_ratio_m4e_over_mini2", ATK, "{:.2f}", "배")],
               ["예산 보정 차이(중앙값)",
                _n(BL + ".budget_corrected_delta_median_db", ATK, "{:+.2f}", "dB")],
               ["보정 뒤 Mini 2 가 앞서는 짝",
                _n(BL + ".n_pairs_where_mini2_wins_after_correction", ATK, "{:.0f}")
                + " / " + _n(BL + ".n_pairs", ATK, "{:.0f}")],
               ["경로수를 맞췄을 때 Mini 2 상승분",
                _n(BL + ".implied_mini2_boost_if_budget_matched_db", ATK, "{:+.2f}", "dB")],
           ]), "",
           "기울기가 1 에 붙는다는 것은 이 통계가 **신호 세기가 아니라 확신도**를 잰다는 뜻이다. "
           "그러므로 경로수가 다른 두 대상끼리 이 값을 직접 견주는 길은 막혀 있다."),

        md("## 하네스의 표본 상한이 그 비교를 막는다", "",
           table(["무엇을", "값"], [
               ["예산을 맞추는 데 필요한 배수",
                _n(BL + ".spp_cap.factor_needed_for_match", ATK, "{:.2f}", "배")],
               ["하네스가 올릴 수 있는 배수",
                _n(BL + ".spp_cap.factor_available", ATK, "{:.1f}", "배")],
               ["본 격자 표본 인자", _n(BL + ".spp_cap.used_in_grid", ATK, "{:,.0f}")],
               ["안전 상한", _n(BL + ".spp_cap.max_safe_in_harness", ATK, "{:,.0f}")],
               ["맞출 수 있나", _n(BL + ".spp_cap.match_is_possible", ATK)],
           ]), "",
           f"표본 인자가 uint32 라 상한이 있다. 그래서 «Mini 2 가 Matrice 4E 보다 못하다» 는 "
           f"읽기는 이 하네스 안에서 근거를 잃는다 — 예산 법칙을 그대로 적용하면 Mini 2 의 "
           f"무변조 칸이 전부 사라진다는 것이 그 예측이고, 그 예측을 확인하려면 표본 상한을 "
           f"먼저 올려야 한다."),

        md("## 꼬리도 같은 이유에서 나온다", "",
           table(["기체", "Sionna 꼬리(중앙값)", "PO 꼬리", "−20 dB 위 칸 수"], [
               ["Mini 2",
                _n(T + ".mini2.sionna_tail_max_db_median", VRD, "{:.2f}", "dB"),
                _n(T + ".mini2.po_tail_max_db_median", VRD, "{:.2f}", "dB"),
                _n(T + ".mini2.n_cells_sionna_tail_above_minus20", VRD, "{:.0f}") + " / "
                + _n(T + ".mini2.n_cells", VRD, "{:.0f}")],
               ["Matrice 4E",
                _n(T + ".matrice4e.sionna_tail_max_db_median", VRD, "{:.2f}", "dB"),
                _n(T + ".matrice4e.po_tail_max_db_median", VRD, "{:.2f}", "dB"),
                _n(T + ".matrice4e.n_cells_sionna_tail_above_minus20", VRD, "{:.0f}") + " / "
                + _n(T + ".matrice4e.n_cells", VRD, "{:.0f}")],
           ]), "",
           "프롭 경로가 적은 기체에서 꼬리가 더 높이 남고, 그 꼬리가 −20 dB 가장자리 판정을 "
           "오염시킨다. Mini 2 의 메쉬는 제조사 공표 형상에서 왔고 함대 대조에서 문헌 계수와 "
           "가장 적게 어긋난 두 기체 중 하나다 — 이 차이를 «메쉬 탓» 으로 읽을 근거가 없다. "
           "⚠ 그 함대 대조 자체는 판정이 «검증 안 됨» 이므로, 여기서 쓰는 것은 «Mini 2 가 "
           "검증됐다» 가 아니라 «두 기체의 메쉬 증거가 같은 급이다» 까지다."),

        md("## 어느 거리에서 무엇을 인용해도 되나", "",
           table_from(f"{ATK}:{SI}.by_range",
                      [("거리 [m]", None), ("코히런트 모양 코사인", "coh_shape_cosine_min"),
                       ("최저 예산에서의 경로수", "n_paths_at_lowest_budget"),
                       ("모양이 예산에 불변인가", "coherent_shape_invariant")],
                      key_col="거리 [m]",
                      fmt={"coh_shape_cosine_min": "{:.4f}",
                           "n_paths_at_lowest_budget": "{:,.0f}"}), "",
           "가까운 거리에서는 상대 도플러 스펙트럼을 읽어도 된다. 거리가 늘면 모양 자체가 "
           "예산을 따라 흔들리므로 상대 스펙트럼도 인용 범위 밖이다. **절대 레벨은 어느 "
           "거리에서도 인용하지 않는다** — 레벨이 √N 으로 자라기 때문이다.", "",
           "⚠ 같은 이유로 **시드 하나로 뽑은 스톡 팔의 레벨과 최강선도 물리량이 아니다.** "
           "이 편의 사다리는 예산 칸마다 시드를 여러 장 쓰지만, 자세 격자를 시드 한 장으로 "
           "푼 다른 스윕의 레벨·경로수는 그 시드의 성질이 섞인다 — 그런 스윕에서 인용해도 "
           "되는 것은 **빈 자세 비율처럼 시드에 둔감한 양**뿐이고, 그 크기를 재는 거리 스윕은 "
           "재계산 대기다."),

        next_steps([
            ("경로수를 표적 크기에 맞춰 정규화하는 예산 규칙을 하네스에 넣는다",
             "기체 비교가 «표적의 성질» 로 닫힌다 — 지금은 예산의 성질이 섞여 있다",
             "`benchmark/report15_probe.py` 의 표본 인자 규칙"),
            ("가장자리 판정을 꼬리 초과분으로 보정한다",
             "«가장자리가 예측과 맞는가» 가 꼬리와 무관해진다",
             ref("md-two-engines", "두 엔진")),
            ("모양 불변 거리 밖의 칸을 인용 목록에서 뺀다",
             "상대 스펙트럼 인용의 성립 범위가 거리로 못 박힌다",
             "이 편의 거리 표"),
        ]),
    ]


# =========================================================================== #
#  편 43 — 상시 신호의 상한
# =========================================================================== #
def blocks_43() -> list:
    C0 = "cells[0]"

    return [
        header(
            num=43,
            title="상시 기준신호가 주는 것은 날개끝 확산이 아니라 블레이드 통과율까지다",
            did="조명원 네 모드(상시 셋 + 측위 세션 옵션인 PRS)의 반복률과 날개끝 도플러가 "
                "요구하는 표본율을 같은 표에 놓고 어디까지 접히는지 셌다.",
            results=[
                f"날개끝 도플러를 접힘 없이 보려면 표본율이 "
                f"{_n(C0 + '.prf_feasibility.LTE CRS.required_prf_hz', RNG, '{:.0f}', 'Hz')} "
                f"필요하다.",

                f"그 자리에 LTE CRS 는 "
                f"{_n(C0 + '.prf_feasibility.LTE CRS.mode_prf_hz', RNG, '{:.0f}', 'Hz')}, "
                f"5G SSB 는 "
                f"{_n(C0 + '.prf_feasibility.5G SSB.mode_prf_hz', RNG, '{:.0f}', 'Hz')}, "
                f"5G NR-PRS 는 "
                f"{_n(C0 + '.prf_feasibility.5G NR-PRS.mode_prf_hz', RNG, '{:.0f}', 'Hz')} 다.",

                f"네 모드 전부 요구치 아래에 있다 — 살아남는 것은 **블레이드 통과율(플래시선)** 이다.",

                f"블레이드 통과율은 헤드라인 기체(Matrice 4E) "
                f"{_L('physics.f_flash', '{:.1f}', 'Hz')} · 이 표의 기체(Mini 5 Pro) "
                f"{_n(C0 + '.flash_hz', RNG, '{:.1f}', 'Hz')} 로 둘 다 LTE·WiFi 의 나이퀴스트 "
                f"안에 든다. 5G 쪽 두 모드에서는 그 통과율마저 접힌다.",

                f"⭐ 날개끝 확산을 보려면 기준 안테나가 **풀 파형을 받아야** 하고, 그건 "
                f"«상시 신호만 쓴다» 와 다른 조건이다.",
            ],
            method=[
                ("요구 표본율",
                 "날개끝 도플러의 두 배 — 양쪽으로 퍼지므로 나이퀴스트가 f_tip 의 2배를 요구한다"),
                ("모드별 반복률",
                 "LTE CRS · 5G SSB 는 표준이 정한 상시 신호의 반복 주기에서 읽었다. "
                 "**WiFi VHT-LTF 는 선언값**이다 — 패킷이 언제 나가는지는 표준이 아니라 "
                 "트래픽이 정하므로 `src/waveforms.py` 의 `PILOT_RATE_HZ` 를 쓴다. "
                 "**5G NR-PRS 는 상시 신호가 아니라 측위 세션이 설정될 때 켜지는 옵션**이라 "
                 "낙관적 상한으로만 읽는다"),
                ("표적",
                 "Mini 5 Pro · 5G NR 3.5 GHz · 호버 회전수 — 같은 규약을 다른 기체로 옮기면 "
                 "f_tip 이 함께 움직인다"),
                ("무엇을 안 물었나",
                 "통과율만으로 검출·분류를 어디까지 할 수 있는지는 별도 질문이다"),
            ],
            prereq=[("앞 편", ref("md-slowtime", "슬로타임 복소열") + " — f_tip 과 f_flash 의 정의")],
            repro=dict(
                cmd="PYTHONPATH=src ~/.venvs/py312/bin/python src/experiment_md_range.py",
                out=[RNG],
                runtime="약 12 분 (GPU 1장)"),
        ),

        md("## 남이 쏘는 신호를 쓰면 표본율을 못 고른다", "",
           "패시브 레이더는 남이 쏘는 신호를 쓴다. 그 신호가 얼마나 자주 반복되는지가 우리가 "
           "볼 수 있는 도플러의 상한을 정한다.", "",
           "날개끝 도플러를 접힘 없이 보려면 표본율이 그 두 배는 돼야 한다. 그 요구치와 각 "
           "모드가 실제로 주는 반복률을 같은 표에 놓으면 어디까지 보이는지가 바로 읽힌다."),

        md("## 네 모드의 반복률과 요구 표본율", "",
           table_from(f"{RNG}:{C0}.prf_feasibility",
                      [("모드", None), ("반복률", "mode_prf_hz"),
                       ("요구 표본율", "required_prf_hz"), ("접힘 없이 보이나", "ok")],
                      key_col="모드",
                      fmt={"mode_prf_hz": "{:.0f} Hz",
                           "required_prf_hz": "{:.0f} Hz"}), "",
           f"표적은 {_n(C0 + '.drone', RNG)} · 반송파 "
           f"{_n(C0 + '.fc_hz', RNG, '{:.3g}', 'Hz')} · 호버 "
           f"{_n(C0 + '.rpm', RNG, '{:.0f}', 'rpm')} 이고, 이때 날개끝 주파수가 "
           f"{_n(C0 + '.f_tip_hz', RNG, '{:.1f}', 'Hz')} · 블레이드 통과율이 "
           f"{_n(C0 + '.flash_hz', RNG, '{:.1f}', 'Hz')} 다."),

        md("## 그래서 무엇이 남는가", "",
           f"⚠ 표의 네 줄 중 셋만 상시다 — 5G NR-PRS 는 측위 세션이 설정될 때 켜지는 "
           f"옵션이라, 그 줄은 «상시로 기대하는 값» 이 아니라 낙관적 상한이다. WiFi 줄의 "
           f"반복률도 표준이 정한 값이 아니라 트래픽 가정에서 온 선언값이다.", "",
           f"네 모드 전부 요구 표본율 아래에 있으므로 날개끝 확산은 접힌다. 살아남는 것은 "
           f"**블레이드 통과율** 이다 — 헤드라인 기체(Matrice 4E)에서 "
           f"{_L('physics.f_flash', '{:.1f}', 'Hz')} · 이 표의 기체(Mini 5 Pro)에서 "
           f"{_n(C0 + '.flash_hz', RNG, '{:.1f}', 'Hz')} 이고, 둘 다 LTE·WiFi 의 나이퀴스트 "
           f"안에 든다.", "",
           f"5G 쪽 두 모드는 반복률이 낮아 그 통과율마저 접는다. 5G 가 치르는 두 배의 대가가 "
           f"마이크로도플러 축에서도 그대로 나타난다.", "",
           "⭐ 이 구분이 실험 설계를 바꾼다. 날개끝 확산을 보려면 기준 안테나가 **풀 파형을 "
           "받아야** 하고, 그건 «상시 신호만 쓴다» 와 다른 조건이다.", "",
           "그 기준 안테나가 «완벽하다» 는 가정을 푸는 편이 따로 있다 — "
           "⛔«기준채널이 현실이면 얼마를 잃는가» 별편(2026-09-03 내림 — 동작점이 실내 통제 기하다, `archive/chamber_0903/`) 가 "
           "기준채널의 잡음·다중경로를 단일축으로 흔들어 검출이 무는 대가를 재고, 그 편의 "
           "마지막 절이 «검출이 죽은 칸에서 빗살은 어디까지 남는가» 를 같은 사슬에서 본다."),

        next_steps([
            ("통과율만 보이는 조건에서 탐지·분류를 돌린다",
             "상시 신호만으로 어디까지 가는지가 수치로 갈린다",
             "검출 결과 편의 파형축"),
            ("기준 안테나를 풀 파형 포착으로 두는 팔을 따로 설계한다",
             "날개끝 확산을 쓰는 조건과 상시 신호만 쓰는 조건의 대가가 나란히 선다",
             ref("hardware", "실측 하드웨어")
             + " · ⛔«기준채널이 현실이면 얼마를 잃는가» 별편(2026-09-03 내림 — 동작점이 실내 통제 기하다, `archive/chamber_0903/`) 의 기준채널 요구치"),
            ("지면 반사가 만드는 선을 블레이드 선과 대조한다",
             "환경이 이 무늬를 훼손하는지, 가짜 선이 구별되는지가 정해진다",
             ref("site-geometry", "야외 부지 기하")),
            ("정지 로터 세션과 별도로 회전 세션을 잡는다",
             "마이크로도플러가 앵커와의 사과-대-사과를 깨지 않고 들어온다",
             ref("attitude", "자세 통제")),
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
    ("34", "md-paths-doppler", blocks_34),
    ("35", "md-slowtime", blocks_35),
    ("36", "md-two-engines", blocks_36),
    ("37", "md-rpm", blocks_37),
    ("38", "md-occlusion", blocks_38),
    ("39", "md-blade-vs-body", blocks_39),
    ("40", "md-attitude", blocks_40),
    ("41", "md-calibration", blocks_41),
    ("42", "md-ray-budget", blocks_42),
    ("43", "md-prf", blocks_43),
]


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    print("── 부 7 「마이크로도플러」 빌드 ──")
    for no, anchor, fn in REPORTS:
        path = os.path.join(OUT, f"{no}_{anchor}.ipynb")
        rep = build_notebook(path, fn(), strict=True)
        write_shard(no, anchor, rep, 7)
    print(f"✅ {len(REPORTS)} 편 → {os.path.relpath(OUT, _ROOT)}/")


if __name__ == "__main__":
    main()
