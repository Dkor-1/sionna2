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
    cd /home/yunjung/workspace/sionna2
    PYTHONPATH=src ~/.venvs/py312/bin/python src/build_part07_microdoppler.py

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
                          header, md, next_steps, num, table, table_from)

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

OUT = os.path.join(_ROOT, "reports")
FIG = "../outputs/figures"

#: 헤드라인 칸 — 메쉬가 깨끗하고(프롭·벨 겹침 0.01 %) 1차 실측 표적이다.
LEAD = "cells.matrice4e/belly"

REPRO_15B = dict(
    cmd=["PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report15b_microdoppler_recompute.py",
         "PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report15b_stamp_provenance.py",
         "PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/build_report15b_figs.py"],
    out=[MDB, "outputs/report15b_series.npz"],
    runtime="약 25 분 (GPU 1장 — 광선 추적이 6칸 × 4팔)",
    note="산출물이 자기가 어떤 메쉬로 계산됐는지 지문을 함께 적는다(`mesh_provenance`) — "
         "계산 도중 메쉬가 바뀌면 스스로 경고한다")


def _n(key: str, src: str = MDB, fmt: str | None = None, unit: str = "") -> str:
    return num(None, (src, key), fmt, unit)


def _L(key: str, fmt: str | None = None, unit: str = "") -> str:
    return _n(f"{LEAD}.{key}", MDB, fmt, unit)


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

                f"정지 장면에서 도플러가 0 이 아닌 경로는 "
                f"{_n(B + '.doppler_nonzero_paths_static_scene', VRD, '{:.0f}', '개')} "
                f"(전체 {_n(B + '.n_paths', VRD, '{:.0f}', '개')}) — 배선 자체는 정상이다.",

                f"프롭 그룹에 강체속도를 주면 프롭 경유 경로 "
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
           table(["무엇을", "값"], [
               ["객체당 속도 자유도", _n(B + ".max_dof", VRD, "{:.0f}", "개")],
               ["정지 장면의 0 아닌 도플러", _n(B + ".doppler_nonzero_paths_static_scene", VRD, "{:.0f}", "개")],
               ["강체속도 주입 시 프롭 경로", _n(P + ".rigid_prop_velocity.n_target_paths", PRB, "{:.0f}", "개")],
               ["그 경로의 도플러 최대", _n(P + ".rigid_prop_velocity.doppler_max_hz", PRB, "{:.1f}", "Hz")],
               ["강체 운동학이 예측하는 값", _n(P + ".rigid_prop_velocity.predicted_rigid_hz", PRB, "{:.1f}", "Hz")],
           ]), "",
           f"프롭 전체에 강체속도 하나를 주면 프롭 경유 경로가 전부 같은 부호로 몰리고, 크기는 "
           f"각 경로의 강체 투영에 따라 0 부터 표의 최대값까지 퍼진다 — 그 최대값이 강체 예측과 "
           f"같은 자리에 선다. 블레이드 전진/후퇴가 갈라지려면 부호가 반대인 두 값이 나와야 "
           f"하는데, 이 표의 도플러는 한 부호로 몰린다."),

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
                f"{_L('physics.n_t', '{:.0f}', '개')} 를 이어 붙여 창 길이 "
                f"{_L('physics.duration_s', '{:.3f}', 's')} 를 얻었다.",

                f"그 창이 주는 도플러 분해능은 "
                f"{_L('physics.doppler_resolution_hz', '{:.2f}', 'Hz')} 이고, 날개끝까지 "
                f"{_L('physics.bins_to_ftip', '{:.0f}', '칸')} 이 든다.",

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
                 "창에 든 블레이드 주기 수가 정한다. 표본 수를 늘려도 안 좋아진다"),
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
           table(["무엇을", "값"], [
               ["표본율", _L("physics.prf", "{:.0f}", "Hz")],
               ["표본 수", _L("physics.n_t", "{:.0f}", "개")],
               ["창 길이", _L("physics.duration_s", "{:.3f}", "s")],
               ["도플러 분해능", _L("physics.doppler_resolution_hz", "{:.2f}", "Hz")],
               ["날개끝까지 든 칸 수", _L("physics.bins_to_ftip", "{:.0f}", "칸")],
           ]), "",
           "분해능은 «창에 든 블레이드 주기 수» 가 정한다. 같은 창 안에서 표본을 촘촘히 해도 "
           "칸이 좁아지지 않으므로, 능선을 가르려면 창을 늘린다."),

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

    return [
        header(
            num=36,
            title="두 엔진이 날개끝 주파수 아래에서 겹치고 그 위에서 갈린다",
            did="같은 로터 위상 스텝 절차를 스톡 Sionna 엔진과 우리 PO 커널 두 곳에 태워 "
                "같은 칸에서 나온 무늬를 맞댔다.",
            results=[
                f"운동학이 예측한 날개끝 주파수 **아래**에서 두 빗살이 겹친다 — 같은 자세·같은 "
                f"거리에서 변조 깊이가 Sionna "
                f"{_n('rows[1].ptp_sionna_db', MDP, '{:.2f}', 'dB')} · PO 커널 "
                f"{_n('rows[1].ptp_po_db', MDP, '{:.2f}', 'dB')} 다.",

                f"그 위에서 갈린다 — 기하 절벽 너머 꼬리의 최대값(중앙값)이 Mini 2 에서 Sionna "
                f"{_n(T + '.mini2.sionna_tail_max_db_median', VRD, '{:.2f}', 'dB')} 대 PO "
                f"{_n(T + '.mini2.po_tail_max_db_median', VRD, '{:.2f}', 'dB')} 다.",

                f"Sionna 의 빗이 **기하에서 온다** — 산란 물리를 전부 빼고 왕복 위상만 더한 "
                f"기준과 겹치면 근거리에서 Mini 2 "
                f"{_n(G + '.mini2.n_near_within_1_bin', VRD, '{:.0f}')}/"
                f"{_n(G + '.mini2.n_near_cells', VRD, '{:.0f}')} 칸이 ±1 조화 안에서 일치한다.",

                f"빗 모양 코사인 중앙값은 Mini 2 "
                f"{_n(G + '.mini2.comb_shape_cosine_median', VRD, '{:.4f}')} · Matrice 4E "
                f"{_n(G + '.matrice4e.comb_shape_cosine_median', VRD, '{:.4f}')} 다.",

                f"⭐ 아래쪽에서 겹친다는 것이 «위상은 광선 엔진이 맞게 낸다» 의 근거이고, "
                f"위쪽에서 갈린다는 것이 «세기는 PO 커널이 맡는다» 의 근거다.",
            ],
            method=[
                ("같은 격자",
                 "로터 위상 스텝·거리·자세·재질·주파수를 전부 같게 두고 엔진 하나만 바꿨다"),
                ("Sionna 팔",
                 "스톡 `sionna.rt.PathSolver` — h = Σ a_p·exp(−j2πf_c τ_p). "
                 "`Paths.cir()` 은 절대위상을 지우므로 쓰지 않는다"),
                ("PO 팔",
                 "`src/microdoppler_nearfield.py` — 평면파/구면파 PO 표면적분, 가림 없음"),
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
                 "Sionna 자체 엔진과 우리 PO 커널이 같은 로터에서 같은 무늬를 내는가?"),
           "로터 위상을 스텝하고 매번 다시 추적하는 같은 절차를 **서로 다른 두 엔진**에 태웠다 — "
           "하나는 Sionna 의 PathSolver 이고 하나는 우리 PO 커널이다.", "",
           "운동학이 예측한 날개끝 주파수 **아래**에서 두 빗살이 겹친다."),

        md("## 그 위에서 갈린다", "",
           table(["기체", "Sionna 꼬리 최대(중앙값)", "PO 꼬리", "기하 기준 꼬리"], [
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
           f"같은 기체·자세·주파수·PRF·로터별 회전수로 세 엔진을 돌렸다 — "
           f"{_n('_meta.n', TRI, '{:.0f}', '표본')} @ PRF "
           f"{_n('_meta.prf_hz', TRI, '{:.0f}', 'Hz')} = "
           f"{_n('_meta.blade_periods', TRI, '{:.0f}')} 블레이드 주기.", "",
           table(["엔진", "변조 p-p", "무늬"], [
               ["Sionna PathSolver", _n("ptp_db.sionna", TRI, "{:.1f}", "dB"),
                "능선이 성기고 날개끝 주파수 근처에서 잦아든다"],
               ["우리 SBR", _n("ptp_db.sbr", TRI, "{:.1f}", "dB"),
                "능선이 대역을 채우고 날개끝 주파수 밖에도 남는다"],
               ["우리 순수 PO", _n("ptp_db.po", TRI, "{:.1f}", "dB"),
                "능선이 몇 가닥에 그친다"],
           ]), "",
           f"⭐ 셋 다 (a) 0 도플러 동체 선, (b) 블레이드 통과율 간격 능선, "
           f"(c) 날개끝 주파수 근처 감쇠를 낸다 — **구조가 일치한다**. "
           f"날개끝 주파수 안에서 스펙트럼 코사인이 "
           f"{_n('verdict.cosine_in_ftip.sionna_vs_sbr', TRI, '{:.3f}')}(Sionna↔SBR) · "
           f"{_n('verdict.cosine_in_ftip.sionna_vs_po', TRI, '{:.3f}')}(Sionna↔PO) · "
           f"{_n('verdict.cosine_in_ftip.sbr_vs_po', TRI, '{:.3f}')}(SBR↔PO) 다."),

        md("## 그 코사인은 «닮았다» 까지를 말한다", "",
           "0.65~0.70 은 구조가 닮았다는 뜻이고, 세 엔진은 능선의 **세기와 밀도**에서 "
           "크게 갈린다. 갈리는 방향에 각각 이유가 있다.", "",
           table(["엔진", "무엇이 그렇게 만드나"], [
               ["우리 순수 PO", "가림을 빼고 계산하므로 모든 면이 항상 기여한다 → 변조가 씻긴다"],
               ["우리 SBR", "⚠ 날개끝 주파수 밖에도 능선을 낸다 — 운동학이 금지한 자리다"],
               ["Sionna", "경로가 열 개 남짓이라 표본이 성기다"],
           ]), "",
           "⚠ 남은 의심은 하나다 — **우리 SBR 의 날개끝 밖 능선이 광선 격자의 이산화 산물인가, "
           "물리인가.** " + ref("md-ray-budget", "광선예산") + " 이 그것을 잰다."),

        md("## Sionna 의 빗은 기하에서 온다", "",
           table(["기체", "±1 조화 안 일치(근거리)", "빗 모양 코사인 중앙값"], [
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

        md("## 정반사 경로는 프로펠러에서 사실상 0 이다", "",
           f"자세×로터위상 {_n('specular_census.total.n_cells', MDP, '{:,.0f}', '칸')} 전수에서 "
           f"프로펠러에 떨어진 정반사 경로는 "
           f"{_n('specular_census.total.n_with_prop_specular', MDP, '{:.0f}', '칸')} 이다.", "",
           f"지금 보이는 무늬는 전부 흩어져 되돌아오는 반사에서 나오고, 그 값은 광선을 다시 쏠 "
           f"때마다 흔들린다. **위상은 광선 엔진이, 세기는 PO 커널이 맡는** 분업의 근거가 여기 있다."),

        next_steps([
            ("가장자리 판정을 꼬리 초과분과 함께 다시 낸다",
             "«가장자리» 가 물리적 절벽인지 꼬리인지가 칸마다 갈린다",
             ref("md-ray-budget", "광선예산")),
            ("두 엔진 일치도를 가림 있는 SBR 팔로 한 번 더 잰다",
             "PO 팔의 «가림 없음» 이 일치도에 넣는 몫이 확정된다",
             "`src/rcs_sbr.py` 팔을 같은 격자에"),
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
            did="네 로터의 회전수를 잠근 팔과 흩뜨린 팔을 같은 격자에서 돌려 창 반쪽 스펙트럼의 "
                "상관을 쟀다.",
            results=[
                f"잠근 팔의 반창 스펙트럼 상관은 "
                f"{_n(R + '.locked_half_corr', MDB, '{:.4f}')} 다 — 신호가 완전한 주기함수라 "
                f"스펙트로그램이 창 내내 같은 모습으로 선다.",

                f"로터마다 회전수를 "
                f"{_n('_meta.rpm_spread_frac', MDB, '{:.2%}')} 흩뜨리면 상관이 "
                f"{_n(R + '.spread_half_corr', MDB, '{:.4f}')} 로 내려간다 — 낙차 "
                f"{_n(R + '.drop', MDB, '{:.4f}')}.",

                f"그때 변조 깊이도 함께 커진다 — 잠근 팔 "
                f"{_L('arms.A_sbr_locked.modulation_ptp_db', '{:.2f}', 'dB')} 에서 흩뜨린 팔 "
                f"{_L('arms.B_sbr_spread.modulation_ptp_db', '{:.2f}', 'dB')} 로.",

                f"동체:날개 비도 잠근 팔 "
                f"{_L('arms.A_sbr_locked.dc_over_ac', '{:.2f}')} 에서 흩뜨린 팔 "
                f"{_L('arms.B_sbr_spread.dc_over_ac', '{:.2f}')} 로 내려간다.",

                f"흩어짐 폭 ±{_n('_meta.rpm_spread_frac', MDB, '{:.2%}')} 는 PX4 텔레메트리 "
                f"실측 산포(모터간 0.07~0.29 %)의 중간값이다 — 우리 표적의 비행 로그가 오면 "
                f"그 값으로 바꾼다.",
            ],
            method=[
                ("단일축",
                 "잠근 팔과 흩뜨린 팔은 광선 엔진·재질·기하·창 길이가 전부 같고 로터별 회전수만 "
                 "다르다"),
                ("흩뜨림 규약",
                 "네 로터에 ±" + _n('_meta.rpm_spread_frac', MDB, '{:.2%}')
                 + " 를 패턴 [1, −1, −0.55, 0.55] 로 준다 — 무게중심 치우침과 요 "
                 "토크 균형이 만드는 실제 비대칭을 흉내 낸 것이다"),
                ("판정량",
                 "창을 반으로 갈라 두 스펙트럼의 상관을 잰다. 완전 주기함수면 1 에 붙는다"),
                ("흩어짐 폭의 출처",
                 "PX4 텔레메트리 실측(모터간 산포 0.07~0.29 %)의 중간값 ±0.22 % 다 — "
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
           table(["무엇을", "잠근 팔", "흩뜨린 팔"], [
               ["반창 스펙트럼 상관",
                _n(R + ".locked_half_corr", MDB, "{:.4f}"),
                _n(R + ".spread_half_corr", MDB, "{:.4f}")],
               ["변조 깊이",
                _L("arms.A_sbr_locked.modulation_ptp_db", "{:.2f}", "dB"),
                _L("arms.B_sbr_spread.modulation_ptp_db", "{:.2f}", "dB")],
               ["동체:날개 비",
                _L("arms.A_sbr_locked.dc_over_ac", "{:.2f}"),
                _L("arms.B_sbr_spread.dc_over_ac", "{:.2f}")],
               ["날개끝 안쪽 에너지 비",
                _L("arms.A_sbr_locked.energy_inside_ftip_frac", "{:.4f}"),
                _L("arms.B_sbr_spread.energy_inside_ftip_frac", "{:.4f}")],
           ]), "",
           "오른쪽 열이 «시간에 따라 변한다» 의 정량이다. 상관이 내려간 만큼 줄이 숨쉰다."),

        md("## 흩어짐 폭은 실측에서 온다", "",
           "실제 기체는 무게중심 치우침과 요 토크 균형 때문에 네 모터가 서로 다른 추력을 내고 "
           "그만큼 회전수가 갈린다. 그 폭을 PX4 텔레메트리 실측 산포(모터간 0.07~0.29 %)의 "
           f"중간값 ±{_n('_meta.rpm_spread_frac', MDB, '{:.2%}')} 로 놓았다 — 출처와 교체 "
           f"규약은 `{MDB} : _meta.spread_is_declared_ko` 다.", "",
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
    return [
        header(
            num=38,
            title="동체가 날개를 가리면 변조 깊이와 레벨이 함께 바뀐다",
            did="광선 엔진·재질·기하·운동학·광선 격자를 전부 같게 두고 «동체가 막느냐» 만 다르게 "
                "한 두 팔을 돌렸다.",
            results=[
                f"변조 깊이가 {_L('findings.occlusion_ptp_db', '{:+.2f}', 'dB')}, 레벨이 "
                f"{_L('findings.occlusion_level_db', '{:+.2f}', 'dB')} 바뀐다.",

                f"막는 팔의 변조 깊이는 "
                f"{_L('arms.F_blade_occ.modulation_ptp_db', '{:.2f}', 'dB')}, 안 막는 팔은 "
                f"{_L('arms.G_blade_free.modulation_ptp_db', '{:.2f}', 'dB')} 다.",

                f"레벨은 각각 {_L('arms.F_blade_occ.level_db', '{:.2f}', 'dB')} 와 "
                f"{_L('arms.G_blade_free.level_db', '{:.2f}', 'dB')} 다.",

                f"두 팔의 광선 격자를 같게 유지했다 — 막는 쪽은 동체를 완전흡수로 두고, "
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

        md("## 두 팔의 값", "",
           table(["무엇을", "막는 팔", "안 막는 팔", "차이"], [
               ["변조 깊이",
                _L("arms.F_blade_occ.modulation_ptp_db", "{:.2f}", "dB"),
                _L("arms.G_blade_free.modulation_ptp_db", "{:.2f}", "dB"),
                _L("findings.occlusion_ptp_db", "{:+.2f}", "dB")],
               ["레벨",
                _L("arms.F_blade_occ.level_db", "{:.2f}", "dB"),
                _L("arms.G_blade_free.level_db", "{:.2f}", "dB"),
                _L("findings.occlusion_level_db", "{:+.2f}", "dB")],
               ["동체:날개 비",
                _L("arms.F_blade_occ.dc_over_ac", "{:.3f}"),
                _L("arms.G_blade_free.dc_over_ac", "{:.3f}"), "—"],
               ["날개끝 안쪽 에너지 비",
                _L("arms.F_blade_occ.energy_inside_ftip_frac", "{:.4f}"),
                _L("arms.G_blade_free.energy_inside_ftip_frac", "{:.4f}"), "—"],
           ])),

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
    return [
        header(
            num=39,
            title="블레이드 신호는 약하지 않다 — 동체 정적 반사가 덮고 있을 뿐이다",
            did="같은 자세·같은 주파수에서 전체 드론 채널과 프로펠러 채널을 따로 재어 변조 깊이를 "
                "맞댔다.",
            results=[
                f"전체 드론 채널의 변조 깊이는 "
                f"{_L('arms.A_sbr_locked.modulation_ptp_db', '{:.2f}', 'dB')} 인데, 같은 칸의 "
                f"프로펠러 채널은 "
                f"{_L('arms.F_blade_occ.modulation_ptp_db', '{:.2f}', 'dB')} 다.",

                f"두 채널의 레벨은 "
                f"{_L('arms.A_sbr_locked.level_db', '{:.2f}', 'dB')} 와 "
                f"{_L('arms.F_blade_occ.level_db', '{:.2f}', 'dB')} 로, 동체가 훨씬 밝다.",

                f"동체:날개 비가 전체 채널에서 "
                f"{_L('arms.A_sbr_locked.dc_over_ac', '{:.2f}')}, 프로펠러 채널에서 "
                f"{_L('arms.F_blade_occ.dc_over_ac', '{:.3f}')} 다.",

                f"⭐ 블레이드 신호가 약한 것이 아니라 **동체 정적 반사가 덮고 있다** — "
                f"그것이 전처리에서 정적 성분을 지우는 이유다.",

                f"어려운 것은 «블레이드가 약하다» 가 아니라 **«동체와 블레이드를 가르는 일»** 이다.",
            ],
            method=[
                ("채널 분리",
                 "같은 추적에서 프로펠러 부품을 지난 경로만 따로 모아 프로펠러 채널을 만든다 — "
                 "기하·재질·광선 격자는 전체 채널과 같다"),
                ("변조 깊이",
                 "슬로타임 |h| 의 최대−최소 [dB]. 동체 정적 반사가 크면 이 값이 눌린다"),
                ("동체:날개 비",
                 "DC(정적 성분) 대 AC(변조 성분) 의 비. 이 값이 클수록 동체가 덮는다"),
                ("무엇을 안 주장하나",
                 "절대 레벨은 이 축의 산출이 아니다 — 두 채널의 **비**만 읽는다"),
            ],
            prereq=[("앞 편", ref("md-occlusion", "가림 축") + " — 두 팔의 정의")],
            repro=REPRO_15B,
        ),

        md("## 같은 칸을 두 채널로 읽는다", "",
           *_fig(1, "report07_f3", "블레이드 신호는 약한가, 아니면 동체가 덮고 있는가?"),
           "같은 자세·같은 주파수에서 전체 드론과 프로펠러 채널을 따로 쟀다. 두 채널은 같은 "
           "추적에서 나오므로 기하·재질·광선 격자가 같다."),

        md("## 두 채널의 값", "",
           table(["무엇을", "전체 드론 채널", "프로펠러 채널"], [
               ["변조 깊이",
                _L("arms.A_sbr_locked.modulation_ptp_db", "{:.2f}", "dB"),
                _L("arms.F_blade_occ.modulation_ptp_db", "{:.2f}", "dB")],
               ["레벨",
                _L("arms.A_sbr_locked.level_db", "{:.2f}", "dB"),
                _L("arms.F_blade_occ.level_db", "{:.2f}", "dB")],
               ["동체:날개 비",
                _L("arms.A_sbr_locked.dc_over_ac", "{:.2f}"),
                _L("arms.F_blade_occ.dc_over_ac", "{:.3f}")],
               ["반창 스펙트럼 상관",
                _L("arms.A_sbr_locked.half_window_spectrum_corr", "{:.4f}"),
                _L("arms.F_blade_occ.half_window_spectrum_corr", "{:.4f}")],
           ]), "",
           "⭐ 프로펠러 채널의 변조는 전체 채널보다 열 배 넘게 깊다. 레벨은 반대로 훨씬 낮다. "
           "두 줄을 같이 읽으면 **동체가 밝아서 변조를 눌렀다** 가 나온다."),

        md("## 그래서 무엇이 어려운가", "",
           "전기적으로 보면 블레이드 폭은 우리 대역에서 파장의 한 자릿수 분율이다. 그런데도 "
           "프로펠러 채널의 변조 자체는 "
           + _L("arms.F_blade_occ.modulation_ptp_db", "{:.1f}", "dB") + " 로 깊다.", "",
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
                f"깊이 {_n(NOSE + '.findings.occlusion_ptp_db', MDB, '{:+.2f}', 'dB')} · 레벨 "
                f"{_n(NOSE + '.findings.occlusion_level_db', MDB, '{:+.2f}', 'dB')} 다.",

                f"배 쪽(앙각 {_L('el_deg', '{:.0f}', '도')})에서는 "
                f"{_L('findings.occlusion_ptp_db', '{:+.2f}', 'dB')} · "
                f"{_L('findings.occlusion_level_db', '{:+.2f}', 'dB')} 로 바뀐다.",

                f"배 옆(방위 {_n(SIDE + '.az_deg', MDB, '{:.0f}', '도')})에서는 "
                f"{_n(SIDE + '.findings.occlusion_ptp_db', MDB, '{:+.2f}', 'dB')} · "
                f"{_n(SIDE + '.findings.occlusion_level_db', MDB, '{:+.2f}', 'dB')} 다.",

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
                ("Mini 5 Pro",
                 "프로펠러와 모터 벨이 겹친 삼각형이 남아 있어 헤드라인에서 뺐다. 같은 그림을 "
                 "그 기체로도 그려 따로 뒀다"),
            ],
            prereq=[("앞 편", ref("md-occlusion", "가림 축") + " — 칸마다 도는 단일축")],
            repro=REPRO_15B,
        ),

        md("## 자세가 답을 바꾼다", "",
           *_fig(1, "report07_f3", "자세에 따라 가림과 변조가 얼마나 달라지는가?"),
           "프로펠러는 동체 **위**에 있다. 그래서 위에서 내려다보면 날개가 통째로 드러나고, "
           "그 자세에서 가림은 0 에 가깝다.", "",
           "지상 레이더는 비행 중인 기체를 **아래에서** 보므로 기체 좌표계로 앙각이 음수이고, "
           "거기서 가림이 문다."),

        md("## 세 자세의 값", "",
           table(["자세", "방위", "앙각", "가림 · 변조 깊이", "가림 · 레벨"], [
               ["코 쪽",
                _n(NOSE + ".az_deg", MDB, "{:.0f}", "°"),
                _n(NOSE + ".el_deg", MDB, "{:.0f}", "°"),
                _n(NOSE + ".findings.occlusion_ptp_db", MDB, "{:+.2f}", "dB"),
                _n(NOSE + ".findings.occlusion_level_db", MDB, "{:+.2f}", "dB")],
               ["배 쪽 ⭐",
                _L("az_deg", "{:.0f}", "°"), _L("el_deg", "{:.0f}", "°"),
                _L("findings.occlusion_ptp_db", "{:+.2f}", "dB"),
                _L("findings.occlusion_level_db", "{:+.2f}", "dB")],
               ["배 옆",
                _n(SIDE + ".az_deg", MDB, "{:.0f}", "°"),
                _n(SIDE + ".el_deg", MDB, "{:.0f}", "°"),
                _n(SIDE + ".findings.occlusion_ptp_db", MDB, "{:+.2f}", "dB"),
                _n(SIDE + ".findings.occlusion_level_db", MDB, "{:+.2f}", "dB")],
           ]), "",
           "세 줄의 부호와 크기가 다르다는 것이 이 편의 내용이다 — 가림은 자세의 함수다."),

        md("## 이 결론은 우리 기하 명세와 같은 방향이다", "",
           "자유공간 바이스태틱의 이등분선 앙각은 전 구간 음수라 우리는 드론 배를 본다. "
           "자세 스윕이 그 문장에 **독립적인 근거**를 붙였다 — 기하 명세와 광선 추적이 서로 "
           "다른 길로 같은 자세를 가리킨다.", "",
           f"⚠ Mini 5 Pro 는 프로펠러와 모터 벨이 겹친 삼각형이 남아 있어 헤드라인에서 뺐다. "
           f"같은 그림을 그 기체로도 그려 `{FIG}/report15b_f1b.png` · "
           f"`{FIG}/report15b_f2b.png` 에 뒀다 — 겹침이 정리되기 전 값이라는 것을 알고 읽는다."),

        next_steps([
            ("가림을 자세 전면(방위×앙각 격자)으로 넓힌다",
             "어느 자세에서 얼마나 무는지의 지도가 서고, 그 지도가 분류기의 입력이 된다",
             "이 편의 세 칸을 격자로"),
            ("Mini 5 Pro 의 프롭·벨 겹침을 정리하고 같은 세 칸을 다시 돌린다",
             "두 기체의 자세 의존이 같은 잣대 위에 올라온다",
             "`src/drone_cad.py` 메쉬 정정 → 이 편 재실행"),
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
            title="판정 잣대를 널 팔 15 칸과 이상 점산란자로 먼저 교정했다",
            did="변조가 나오면 안 되는 물체와 이상 점산란자를 같은 측정법에 넣어 판정 문턱이 "
                "거짓양성과 거짓음성을 내는지 먼저 쟀다.",
            results=[
                f"널 팔 {_n(CA + '.n_null_cells', VRD, '{:.0f}', '칸')} 에서 변조 판정이 "
                f"{_n(CA + '.n_null_firing', VRD, '{:.0f}', '번')} 켜졌다 — 최댓값 "
                f"{_n(CA + '.max_null_ac_over_noise_db', VRD, '{:.2f}', 'dB')} 가 문턱 "
                f"{_n(CA + '.threshold_db', VRD, '{:.1f}', 'dB')} 아래에 든다.",

                f"신호 팔은 {_n(CA + '.n_signal_cells', VRD, '{:.0f}', '칸')} 중 "
                f"{_n(CA + '.n_signal_firing', VRD, '{:.0f}', '칸')} 이 켜진다 — 문턱이 "
                f"양쪽에서 작동한다.",

                f"이상 점산란자는 가장자리 시험을 "
                f"{_n(IR + '.n_pass', VRD, '{:.0f}')}/{_n(IR + '.n', VRD, '{:.0f}')} 칸에서 "
                f"통과한다 — 그 시험이 교정됐는지는 "
                f"{_n(IR + '.test_is_calibrated', VRD)} 로 적혀 있다.",

                f"널 팔 전용 재계산에서도 같은 결론이다 — 신호 대 인공물 여유 "
                f"{_n(NV + '.margin_rescaled_db', NUL, '{:.2f}', 'dB')}, 비 "
                f"{_n(NV + '.signal_over_floor_ratio', NUL, '{:.1f}', '배')}.",

                f"⚠ 적대검증이 널 셈을 정정했다 — 실제로 시험된 널은 "
                f"{_n(NS + '.n_null_cells_with_a_value', ATK, '{:.0f}', '칸')} 이고 나머지 "
                f"{_n(NS + '.n_null_cells_degenerate_no_value', ATK, '{:.0f}', '칸')} 은 "
                f"AC 가 정확히 0 이라 시험 자체가 성립하지 않는 칸이다.",
            ],
            method=[
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
                runtime="약 35 분 (GPU 1장 — 널 팔 20 개)"),
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
           "위 네 줄이 신호 팔(프로펠러가 도는 두 기체 × 두 엔진), 아래 네 줄이 널 팔이다. "
           "색눈금은 각 패널 자신의 정적 반사를 0 dB 로 잡은 값이라 널 줄과 신호 줄을 직접 "
           "견줄 수 있다. 널 줄은 세 거리 전부에서 검게 남는다."),

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
            title="두 기체가 갈리는 이유는 메쉬 품질이 아니라 표적 크기 대비 광선예산이다",
            did="기하를 고정하고 광선예산만 16배 흔들어 다시 추적해 판정 통계가 경로수를 "
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
                 "기하·자세·재질을 고정하고 표본 인자만 16 배 범위로 올려 새 시드로 다시 "
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
           "위 두 칸이 확산 채널의 경로수다 — 위상에 따라 매끄럽게 변하고, 껐다 켜지는 칸은 "
           "0 개다. 가운데가 정반사 채널이고, 아래가 거리별 두 엔진 일치도다.", "",
           "오른쪽 아래에서 Matrice 4E 의 «hot» 자세만 거리와 함께 무너진다 — 그 자세의 "
           "경로수가 가장 적기 때문이다."),

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
           "오염시킨다. Mini 2 는 Das 실측으로 검증된 기준자이므로, 이 차이를 «메쉬 탓» 으로 "
           "읽는 것은 근거를 벗어난다."),

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
           "거리에서도 인용하지 않는다** — 레벨이 √N 으로 자라기 때문이다."),

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
            did="상시 조명원 네 모드의 반복률과 날개끝 도플러가 요구하는 표본율을 같은 표에 놓고 "
                "어디까지 접히는지 셌다.",
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
                 "표준이 정한 상시 신호의 반복 주기에서 읽었다 — LTE CRS · WiFi VHT-LTF · "
                 "5G SSB · 5G NR-PRS"),
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
           f"네 모드 전부 요구 표본율 아래에 있으므로 날개끝 확산은 접힌다. 살아남는 것은 "
           f"**블레이드 통과율** 이다 — 헤드라인 기체(Matrice 4E)에서 "
           f"{_L('physics.f_flash', '{:.1f}', 'Hz')} · 이 표의 기체(Mini 5 Pro)에서 "
           f"{_n(C0 + '.flash_hz', RNG, '{:.1f}', 'Hz')} 이고, 둘 다 LTE·WiFi 의 나이퀴스트 "
           f"안에 든다.", "",
           f"5G 쪽 두 모드는 반복률이 낮아 그 통과율마저 접는다. 5G 가 치르는 두 배의 대가가 "
           f"마이크로도플러 축에서도 그대로 나타난다.", "",
           "⭐ 이 구분이 실험 설계를 바꾼다. 날개끝 확산을 보려면 기준 안테나가 **풀 파형을 "
           "받아야** 하고, 그건 «상시 신호만 쓴다» 와 다른 조건이다."),

        next_steps([
            ("통과율만 보이는 조건에서 탐지·분류를 돌린다",
             "상시 신호만으로 어디까지 가는지가 수치로 갈린다",
             "검출 결과 편의 파형축"),
            ("기준 안테나를 풀 파형 포착으로 두는 팔을 따로 설계한다",
             "날개끝 확산을 쓰는 조건과 상시 신호만 쓰는 조건의 대가가 나란히 선다",
             ref("hardware", "실측 하드웨어")),
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
