# -*- coding: utf-8 -*-
"""
build_part04_kernel.py — 부 4 「산란 커널」 → 편 18~23
==========================================================================================
부 4 가 답하는 질문 하나
    **우리 커널이 무엇을 계산하고 기준해와 얼마나 맞나.**

편 하나 = 중심 메시지 하나 (제목이 곧 그 편의 결론 문장이다)

    18 kernel-what          가림 판정은 Sionna 광선엔진이 하고, 면적분은 우리 커널이 한다
    19 kernel-vs-stock      스톡 솔버와 맞대면 «면이 많아서 에코가 커진다» 가설은 반증되고,
                            런타임의 96.9% 는 호스트가 쓴다
    20 bistatic-exit        수신 방향 그림자 광선을 켜면 상반성 위반이 9.69 → 8.24 dB 로 내려간다
    21 kernel-vs-reference  해석 PO 구 대비 구현오차는 kr 전 구간에서 0.201 dB 안이다
    22 po-knee              PO 유효 무릎을 부품 폭으로 옮기면 어느 부품이 어느 밴드에서
                            떨어지는지가 보인다
    23 kernel-open-items    커널이 아직 못 하는 것은 편파 분리·PTD·재테셀레이션·Γ(θ) 배선
                            넷이고, 각각의 크기를 적었다

어디서 왔나 (재구성 전 → 후)
    `report02_target.ipynb` c7~c13  ·  `report00_foundations.ipynb` c18 · c19 · c22
    계획: `outputs/restruct_exec_plan.json : reports[no in 18..23]`

⚠ 계획의 `from_cells` 는 report00 의 셀 번호가 c16 부터 한 칸씩 밀려 있다(부 1 담당이 실측해
   보고했다). 실제 셀을 세어 맞췄다 — 편 21 ← c18 · 편 22 ← c19 · 편 23 ← c22 다.

실행
    cd /workspace/sionna
    PYTHONPATH=src ~/.venvs/py312/bin/python src/build_part04_kernel.py

⚠ GPU 도 Sionna 실행도 필요 없다 — 서술 재배치다.
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

from report_registry import index_shard, nb_path, ref, ref_part           # noqa: E402
from report_style import (build_notebook, caption, fetch, header, md,     # noqa: E402
                          next_steps, num, table, table_from)

# --------------------------------------------------------------------------- #
#  근거 파일
# --------------------------------------------------------------------------- #
DER = "outputs/report02_derived.json"        # 02 파생 원장(가림·kr·밴드)
MCM = "outputs/mesh_compare_material.json"   # 가림 축의 두 팔 정의와 그 바닥의 caveat
PSS = "outputs/prior_settled_sionna.json"    # Sionna 문서 단어 수
R3RT = "outputs/report3_rt.json"             # 스톡 산란 모델 대조
FCNT = "outputs/facet_count.json"            # 면 수 ↔ 에코 가설
FMEC = "outputs/facet_mechanism.json"        # 평판 대조군 — 이미지법 진폭
RUN = "outputs/runtime_benchmark.json"       # 같은 카드 런타임
DFX = "outputs/sbr_defect_fixes.json"        # 출사 가시성 · 이면각 · 상반성
KRS = "outputs/sbr_kr_sweep.json"            # kr 스윕 — 해석 PO / Mie
POC = "outputs/report00_po_case.json"        # 검증 3층 · PO 무릎 · 열린 항목
LFA = "outputs/lowfreq_anchor.json"          # 얇은 판 참값(2D MoM)
LFK = "outputs/lowfreq_attack.json"          # 저대역 적대검증
P3V2 = "outputs/p3_validation_v2.json"       # Phantom 3 v2 — 문헌 대역
MFX = "outputs/meshfix_applied.json"         # 형상 정정이 옮긴 것
MFX_ATK = "outputs/meshfix_attack.json"      # 형상 정정 적대검증
EVD = "outputs/report00_evidence.json"       # 테셀레이션 축
PTD = "outputs/ptd_wiring.json"              # PTD 배선 비용
AGI = "outputs/angle_gamma_impact.json"      # Γ(θ) 각도 모양 — 커널이 |Γ| 에 곱하는 축
APO = "outputs/angle_gamma_po_impact.json"   # 순수 PO 쪽 Γ(θ) — 호출 옵트인 · 비트동일 회귀
SGC = "outputs/sbr_grid_convergence.json"    # 격자 사다리 — 생산·위상고정·얼림 세 팔
SGZ = "outputs/sbr_grid_convergence.npz"     # 그 사다리의 슬로타임 계열·격자 진단
SGR = "outputs/sbr_grid_freeze_review.json"  # 얼리기 적대 반증 8 라운드
AGF = "outputs/adv_grid_freeze_audit.json"   # 얼리기 적대 감사 — 히트수·커버리지·비용
AGV = "outputs/adv_sbr_grid_verdict.json"    # 위 둘의 종합 판정
OOB = "outputs/outofband_power.json"         # ⭐대역밖 전력의 잣대(절대·평활 없음)
VFG = "outputs/verify_frozen_grid.json"      # grid_ref 배선 회귀 게이트
FSL = "outputs/freeze_signal_loss.json"      # ⭐렌즈 B — 얼리기가 «신호» 도 깎았나(PO 심판)
FPS = "outputs/freeze_plate_sensitivity.json"  # ⭐판 한 장에 절대 dB 가 얼마나 걸리나
MCV = "outputs/md_classify_verify.json"      # 가산성 정리 검사(격자 고정 ↔ 이동)
VBF = "outputs/verify_bistatic_field.json"   # 바이스태틱 복소장 게이트 — Γ(θ) 배선 포함
GEO = "outputs/geometry_grid.json"           # 검출 사슬이 σ 를 어느 기하에서 읽나
ARK = "outputs/audit_rcs_kernel.json"        # 커널 감사 — 배선 축의 열린 자리

FIG = "../outputs/figures"


def _n(key: str, src: str, fmt: str | None = None, unit: str = "") -> str:
    return num(None, (src, key), fmt, unit)


def _lit(key: str, src: str, fmt: str = "{:.2f}") -> str:
    """원장 값을 **출처 표시 없이** 글자로만 — 제목처럼 각주가 못 붙는 자리에 쓴다.

    본문 숫자는 언제나 `num()`(출처 태그 포함)으로 넣는다. 제목은 각주가 안 붙는 자리라
    손으로 적히기 쉬운데, 이 함수를 거치면 값이 **원장에서 읽혀** 원장이 움직이면 제목도
    같이 움직인다."""
    return fmt.format(fetch((src, key)))


def _pct(num_key: str, den: float, src: str, fmt: str = "{:.0f}") -> str:
    """원장 값을 분모로 나눈 비율 — 파생값을 본문에 손으로 적지 않기 위한 것이다."""
    return fmt.format(100.0 * float(fetch((src, num_key))) / float(den))


#: 격자 사다리가 돈 자세 수 — 「4095 스텝」 같은 파생 숫자를 여기서 만든다.
_N_POSE = int(fetch((SGC, "_meta.n")))
#: λ/12 격자에서 자세마다 갈리는 히트 수 — 계열의 최대−최소와 그 상대폭.
_NLIT = [float(x) for x in fetch((SGZ, "n_lit_div12"))]
_NLIT_PTP = max(_NLIT) - min(_NLIT)
_NLIT_PTP_PCT = 100.0 * _NLIT_PTP / (sum(_NLIT) / len(_NLIT))
#: 얼린 판이 자세 평균보다 더 쏘는 광선의 몫.
_RAY_COST_PCT = 100.0 * (float(fetch((VFG, "gate2_frozen_grid_invariant.extra_ray_cost"))) - 1.0)

#: ⭐리포트 8 계열의 원장이 얼린 판으로 다시 났나 — 상태를 **원장에서 읽는다**(손으로 안 적는다).
_R8J = os.path.join(_ROOT, "outputs", "report07_three_engines.json")
_FBAJ = os.path.join(_ROOT, "outputs", "freeze_before_after.json")


def _r8_freeze_status() -> str:
    """이 절의 숫자가 어디 것이고, 8 권이 그것으로 갈아탔는지."""
    tail = ("여기 숫자는 격자 사다리와 회귀 게이트 자신의 것이다 — 리포트 8 계열의 "
            "재계산 결과를 인용하지 않는다.")
    try:
        with open(_R8J, encoding="utf-8") as f:
            done = bool(json.load(f)["_meta"].get("grid_frozen"))
    except Exception:
        done = False
    if not done:
        return "⚠ 리포트 8 계열의 원장은 아직 옛 판(자세마다 다시 정의)이다 — " + tail
    n = ""
    try:
        with open(_FBAJ, encoding="utf-8") as f:
            n = f"{json.load(f)['summary']['n_series']} 열 · "
    except Exception:
        pass
    return ("⭐ 리포트 8 계열의 마이크로도플러 원장은 얼린 판으로 **다시 났다**"
            f"({n}옛 열은 `outputs/prefreeze/` 에 사본으로 남아 있다). 전후 비교와 그 판의 "
            "구체적인 수치는 [리포트 8-2 «광선 격자를 어디에 매나»](08_2_engines.ipynb) 가 낸다. "
            "⚠ 아직 옛 판인 것은 바이스태틱 스윕 원장(`report07b_bistatic_md`)과 PO 대조 원장"
            "(`report15_po_control`)이다. " + tail)

AGS = "outputs/angle_gamma_sigma_impact.json"   # Γ(θ) 가 σ 격자를 옮긴 양 — 기체 3 × 고각 2
#: 그 원장에서 **가장 작은 칸과 가장 큰 칸의 이름**을 고른다 — 범위의 두 끝까지 원장이 정한다.
_AGS_CELLS = ["matrice4e/el-15", "matrice4e/el+15", "mini5pro/el-15",
              "mini5pro/el+15", "phantom4/el-15", "phantom4/el+15"]


def _ends(src: str, cells: list[str], field: str) -> tuple[str, str]:
    vals = {c: float(fetch((src, f"{c}.{field}"))) for c in cells}
    return min(vals, key=vals.get), max(vals, key=vals.get)


_AGS_MEAN_LO, _AGS_MEAN_HI = _ends(AGS, _AGS_CELLS, "delta_db")
_AGS_CELL_LO, _AGS_CELL_HI = _ends(AGS, _AGS_CELLS, "cell_max_abs_db")


def _fig(no: int, stem: str, question: str) -> list[str]:
    return [f"![{stem}]({FIG}/{stem}.png)", "", caption(no, question)]


def _repro(cmd: list[str], out: list[str], runtime: str, note: str = "") -> dict:
    d = dict(cmd=cmd + ["PYTHONPATH=src python src/build_part04_kernel.py"],
             out=out, runtime=runtime)
    if note:
        d["note"] = note
    return d


_DERIVE = "PYTHONPATH=src python src/make_report02_target.py --derive-only"

#: 부품 폭 무릎을 주파수로 옮긴 값이 사는 자리 — 키가 길어서 한 번만 적는다.
_KNEE = ("q5_blast_radius.po_validity_blast_radius_the_real_one."
         "recomputed_by_me_frequency_at_which_each_feature_passes_that_knee.")


def _knee(part: str, fmt: str = "{:.2f}", unit: str = "GHz") -> str:
    return _n(_KNEE + part, LFK, fmt, unit)


def _knee_width(part: str) -> str:
    """무릎 표의 «폭» 칸 — 원장 키 이름에 박힌 치수를 그대로 읽는다.

    폭을 따로 손으로 적으면 표의 폭과 그 폭으로 찾은 주파수가 서로 다른 값을 가리킬 수
    있다. 같은 문자열에서 둘 다 나오게 두면 그 어긋남이 생기지 않는다."""
    return part.rsplit("_", 1)[-1].replace("mm", " mm")


#: 무릎 표의 행 — (부품 이름, 원장 키). 폭도 주파수도 이 키 하나에서 나온다.
_KNEE_ROWS = [("동체", "body_81.51mm"), ("암뿌리", "arm_root_45mm"),
              ("암끝", "arm_tip_30mm"), ("프로펠러", "prop_blade_13.78mm"),
              ("모터", "motor_13.68mm"), ("캐노피", "canopy_6.22mm"),
              ("PCB", "pcb_2.99mm")]


# =========================================================================== #
#  편 18 — kernel-what
# =========================================================================== #
def report_18_kernel_what():
    return [
        header(
            num=18,
            title="가림 판정은 Sionna 광선엔진이 하고, 면적분은 우리 커널이 한다",
            did="상용 고주파 솔버의 순서 그대로 광선으로 조명면을 찾고 그 면 위에서 부품별 "
                "재질 PO 를 적분해 σ 를 냈다.",
            results=[
                f"첫 충돌 탐색과 가림은 Sionna 가 이미 들고 있는 Mitsuba/OptiX 엔진이 하고, "
                f"표면전류 적분과 σ 출력은 우리가 얹는다 — 그 문서에 `physical optics` 는 "
                f"{_n('word_counts_rerun_this_session.sionna_rt_technical_report_v2_59p.physical optics', PSS, '{:.0f}', '회')} "
                f"나온다.",

                f"조명원을 방위 "
                f"{_n('occlusion.az_deg', DER, '{:.0f}', '°')} · 고각 "
                f"{_n('occlusion.el_deg', DER, '{:.0f}', '°')} 에 두면 조명원을 향한 외피의 "
                f"{_n('occlusion.shadow_min_pct', DER, '{:.0f}')}~"
                f"{_n('occlusion.shadow_max_pct', DER, '{:.0f}', '%')} 가 기체 자신에 가려 있다.",

                f"«가림 [dB]» 은 **두 팔의 차**다 — P(순수 PO · 점구름 λ/7 · 가림 없음)의 "
                f"방위평균 σ 에서 B(SBR+PO · 광선격자 λ/12)를 **불투명**으로 돌린 값을 뺀 것이 "
                f"최대 "
                f"{_n('occlusion.max_db', DER, '{:.2f}', 'dB')}"
                f"({_n('occlusion.max_drone', DER)}, 닫힌 동체)이고, 열린 프레임인 "
                f"{_n('occlusion.min_drone', DER)} 에서는 "
                f"{_n('occlusion.min_db', DER, '{:.2f}', 'dB')} 다. 기체 "
                f"{_n('occlusion.n_above_floor', DER, '{:.0f}', '종')} 전부에서 이 차가 "
                f"이산화 바닥(P 팔 한쪽을 λ/7↔λ/12 로 돌린 폭, 최대 "
                f"{_n('occlusion.floor_max_db', DER, '{:.3f}', 'dB')}) 위에 있다 — 원장이 "
                f"«가림 효과» 라고 부르기 위해 건 필요조건을 일곱 기체가 전부 통과한다 "
                f"⟨{MCM} : airframes.mini5pro.sigma.caveat⟩.",

                f"금속 4그룹만 남긴 메쉬의 방위평균 σ 가 전체의 "
                f"{_n('C_metal.metal_share_pct', R3RT, '{:.0f}', '%')} 다 — 코히런트 합이라 "
                f"100 % 를 넘는다.",

                f"그 광선 격자를 자세마다 다시 정의하면 로터 사이에 가짜 결합이 생긴다 — "
                f"가산성 잔차가 격자를 얼렸을 때 "
                f"{_n('grid_pinning.matrice4e.pinned.additivity_residual_median', MCV, '{:.1e}')} "
                f"(기계정밀도)이고 움직이는 격자에서 "
                f"{_n('grid_pinning.matrice4e.moving.additivity_residual_median', MCV, '{:.2f}')} "
                f"다. 얼리면 **대역밖**(블레이드 끝 도플러 "
                f"{_n('_meta.f_tip_hz', OOB, '{:.0f}', 'Hz')} 보다 높은 주파수 전부) 절대 전력이 "
                f"λ/12 에서 {_n('freeze_verdict.gains_db.12', OOB, '{:.1f}', 'dB')} 내려간다.",
            ],
            method=[
                ("① 조명면 찾기", "Sionna 의 Mitsuba/OptiX 광선엔진을 그대로 부른다 — 첫 충돌 "
                               "탐색과 자기가림 판정이 그쪽 몫이다"),
                ("② 면적분", "그 면 위에서 부품별 재질 PO 를 적분한다 "
                          "(`src/rcs_sbr.py` `rcs_sbr()`) — E = Σ |Γᵢ(θᵢ)| e^{j2k pᵢ·û} d², σ = 4π|E|²/λ²"),
                ("셸 투과", "얇은 유전체 셸 뒤의 금속(배터리·PCB)을 코히런트 합산한다 "
                        "(동 `penetrate=True`)"),
                ("가림의 크기", "같은 자세를 **다른 팔**로 다시 적분한다 — P(순수 PO 점구름 "
                            "λ/7, 가림 없음)와 B(SBR+PO 광선격자 λ/12)를 불투명으로 돌린 값의 "
                            "방위평균 σ 차이를 기체마다 잰다. 셸까지 통과시킨 생산 B 와 P 의 "
                            "차는 표의 «P − B(생산)» 열이다. 이산화 바닥은 P 팔 한쪽을 "
                            "λ/7↔λ/12 로 돌린 폭이고 그 옆에 나란히 싣는다"),
                ("격자를 무엇에 매나", "격자 중심·반경·칸수를 자세마다 다시 잡는 팔과 "
                                "한 판으로 얼린 팔을 같은 씬·같은 자세열에 나란히 태운다"),
            ],
            repro=_repro([_DERIVE], [DER, PSS, R3RT, SGC, OOB, VFG, MCV],
                         "약 2분 (GPU 0장 — 원장 조립이다)",
                         "σ 격자 자체의 재생성은 `benchmark/rcs_anchor.py` 가 맡는다"),
        ),

        md("## 두 낱말을 먼저 푼다", "",
           "**PO** 는 물리광학(physical optics)이다 — 빛이 닿는 면에 흐르는 전류를 근사식으로 "
           "바로 적어 넣고 그 면을 훑어 더해 산란을 내는 방법이다. **SBR** 은 광선을 쏴서 튀기며 "
           "그 면이 어디인지 찾는 방법(shooting-and-bouncing rays)이다.", "",
           "상용 고주파 RCS 솔버(FEKO/CST SBR+)의 순서 그대로다 — **① 광선으로 실제 조명면을 "
           "찾고 ② 그 위에서 PO 표면적분**(`src/rcs_sbr.py` `rcs_sbr()`). 레이다식이 표적 산란과 전파 "
           "경로를 두 양으로 쓰는 그대로, **σ 는 이 커널이 내고 경로와 환경은 그 엔진이 낸다**."),

        md("## 누가 무엇을 하나", "",
           table(["단계", "무엇을", "누가"],
                 [["첫 충돌 탐색 · 가림", "어느 면이 실제로 조명되는가",
                   "🟢 Sionna 의 Mitsuba/OptiX 광선엔진"],
                  ["재질 |Γ(θ)|", "수직입사 보정값 × 각도 모양(TE·TM 전력평균, "
                                "`ANGLE_GAMMA=1` 기본). 1회 반사 경로 넷이 같은 함수를 쓴다 "
                                "— 다중반사 경로가 서 있는 자리는 **절 6** 이다",
                   "🟢 Sionna 재질표(`src/materials.py` `MATERIALS`) + 🔵 각도 모양 "
                   "(`src/rcs_sbr.py` `ANGLE_GAMMA`)"],
                  ["PO 면적분 → σ", "E = Σ |Γᵢ(θᵢ)| e^{j2k pᵢ·û} d², σ = 4π|E|²/λ²",
                   "🔵 우리 (`src/rcs_sbr.py` `rcs_sbr()`)"],
                  ["셸 투과", "얇은 유전체 셸 뒤 금속(배터리·PCB)의 코히런트 합",
                   "🔵 우리 (동 `penetrate=True`)"]])),

        md("## 왜 우리가 얹어야 하나", "",
           f"Sionna 는 광선을 쏘고 튀긴다 — 기술보고서(v1.2, 59쪽)에 SBR 이 "
           f"{_n('word_counts_rerun_this_session.sionna_rt_technical_report_v2_59p.SBR or shooting-and-bouncing', PSS, '{:.0f}', '회')} "
           f"나오고 우리도 그 엔진을 그대로 부른다. 같은 문서에서 `physical optics` "
           f"{_n('word_counts_rerun_this_session.sionna_rt_technical_report_v2_59p.physical optics', PSS, '{:.0f}', '회')} · "
           f"`radar cross section` "
           f"{_n('word_counts_rerun_this_session.sionna_rt_technical_report_v2_59p.radar cross section', PSS, '{:.0f}', '회')} · "
           f"`surface current` "
           f"{_n('word_counts_rerun_this_session.sionna_rt_technical_report_v2_59p.surface current', PSS, '{:.0f}', '회')} 이고, "
           f"거친 면은 정규화 산란패턴을 쓰는 경험 모델이다 — 그 셈이 어디서 끝나는지는 "
           f"{ref_part(1)} 가 인자 목록까지 해부했다.", "",
           f"ITU `metal` 의 산란계수 S = "
           f"{_n('C_metal.itu_metal_S', R3RT, '{:.1f}')} 이라 스톡 산란 모델이 금속에서 내놓는 "
           f"항은 0 이고, 우리 σ 는 면적분에서 창발한다. 금속 4그룹(모터·배터리·PCB·카메라)만 "
           f"남긴 메쉬의 방위평균 σ 는 전체의 "
           f"{_n('C_metal.metal_share_pct', R3RT, '{:.0f}', '%')} 다."),

        md("## PO 적분이 실제로 올라타는 면은 어디까지인가", "",
           *_fig(1, "mesh_compare_material_shadow",
                 "PO 적분이 실제로 올라타는 면은 어디까지인가?"), "",
           f"조명원을 방위 {_n('occlusion.az_deg', DER, '{:.0f}', '°')} · 고각 "
           f"{_n('occlusion.el_deg', DER, '{:.0f}', '°')} 에 두었다 — 방위 "
           f"{_n('occlusion.n_az_sweep', DER, '{:.0f}', '점')} 스윕에서 7기체 평균 그늘비율의 "
           f"중앙값에 가장 가까운 방위이고, 규칙이 고른다. 가림 판정은 생산 SBR 이 쓰는 그림자광선 "
           f"그대로다(`rcs_sbr._exit_visible()`). 그림의 색은 재질이 아니라 조명 상태다."),

        md(f"**표.** 열 이름의 두 팔 — P = 순수 PO(점구름 λ/7), B = SBR+PO(광선격자 λ/12) 이고, "
           f"B 는 불투명(셸 투과 없음)과 생산(셸 투과) 두 설정으로 선다.", "",
           f"> 원장 정의 그대로다 — {_n('occlusion.definition', DER)}", "",
           table_from(f"{DER}:occlusion.rows",
                      [("기체", "airframe"), ("외피 그늘", "shadow_pct"),
                       ("가림 [dB]", "d_occlusion_db"), ("셸 투과 [dB]", "d_shell_db"),
                       ("P − B(생산) [dB]", "d_total_db"), ("이산화 바닥 [dB]", "floor_db"),
                       ("생산 σ [dBsm]", "sigma_dbsm")],
                      fmt={"shadow_pct": "{:.0f} %", "d_occlusion_db": "{:+.2f}",
                           "d_shell_db": "{:+.2f}", "d_total_db": "{:+.2f}",
                           "floor_db": "{:.3f}", "sigma_dbsm": "{:.1f}"})),

        md("## 두 팔의 차가 얼마인가", "",
           f"P(순수 PO · 점구름 λ/7 · 가림 없음)와 B(SBR+PO · 광선격자 λ/12)를 불투명으로 돌린 "
           f"값의 방위평균 σ 차이가 "
           f"{_n('occlusion.max_db', DER, '{:.2f}', 'dB')}"
           f"({_n('occlusion.max_drone', DER)}, 닫힌 동체)까지 가고, 열린 프레임인 "
           f"{_n('occlusion.min_drone', DER)} 에서는 "
           f"{_n('occlusion.min_db', DER, '{:.2f}', 'dB')} 다. 기체 "
           f"{_n('occlusion.n_above_floor', DER, '{:.0f}', '종')} 전부에서 이 차가 이산화 "
           f"바닥(최대 {_n('occlusion.floor_max_db', DER, '{:.3f}', 'dB')}) 위에 있다 — 그 바닥은 "
           f"**P 팔 한쪽**을 λ/7↔λ/12 로 돌린 폭이고, 원장은 이것을 «가림 효과» 라고 부르기 위한 "
           f"필요조건으로 쓴다 ⟨{MCM} : airframes.mini5pro.sigma.caveat⟩. B 팔 광선격자의 자기 "
           f"불확도는 같은 통계(방위 "
           f"{_n('occlusion.n_az_sweep', DER, '{:.0f}', '점')} 평균)로 재는 것이 다음 단계 표에 "
           f"있다.", "",
           f"⚠ 이 표와 그림은 {_n('_meta.date', MFX)} 형상 정정 **전** 메쉬 기준이고, "
           f"{_n('_meta.generated', AGI)} Γ(θ) 각도 모양(기본 켬) **이전** 커널의 산출이다 — "
           f"가림 최대치를 내는 Matrice 4E 와 X500 V2 가 그 정정을 받은 기체이고, 닫힌 동체의 "
           f"가림은 셸 형상에 직접 걸린다. 생산 σ 열도 두 축 같은 이유로 재계산 대상이다."),

        md("## 격자를 자세마다 다시 정의하면 무엇이 생기나", "",
           f"광선 격자는 표적 앞에 세우는 평면 자다 — 중심 ctr, 반경 Rout, 한 변의 칸수 n "
           f"셋이 그것을 정한다. 생산 경로는 그 셋을 **자세마다 bbox 에서 다시 잡는다**. "
           f"관절이 도는 로터에서는 bbox 가 자세마다 숨쉬므로 자도 같이 흔들린다.", "",
           table(["흔들리는 것",
                  f"무엇이 흔들리나 (λ/12 · {fetch((SGC, '_meta.drone'))} · {_N_POSE} 자세)",
                  "무엇이 실리나"],
                 [["위상 원점",
                   "ctr 이 시선방향으로 "
                   + _n("grid_wander.ctr_u_ptp_mm", SGC, "{:.1f}", "mm")
                   + " p-p 돌아다닌다 = "
                   + _n("R4_phase_only_arm.ctr_dot_u_ptp_rad", SGR, "{:.2f}", "rad") + " p-p",
                   "진폭은 "
                   + _n("R4_phase_only_arm.rows[1].max_abs_change", SGR, "{:.0e}")
                   + " 안에서 불변인 채 **위상만** 흔들린다 — 정지한 동체를 시선방향으로 "
                     "숨쉬게 만드는 것과 같다"],
                  ["표본 격자",
                   "n = ceil(2Rout/d) 가 정수라 "
                   + _n("grid_wander.per_div.12.n_min", SGC, "{:.0f}") + "~"
                   + _n("grid_wander.per_div.12.n_max", SGC, "{:.0f}")
                   + f" 사이를 오가고 {_N_POSE - 1} 스텝 중 "
                   + _n("grid_wander.per_div.12.n_changes", SGC, "{:.0f}", "번")
                   + f"({_pct('grid_wander.per_div.12.n_changes', _N_POSE - 1, SGC)} %) 튄다",
                   "서브셀 오프셋 표준편차 "
                   + _n("grid_wander.per_div.12.subcell_off_e1_std_frac", SGC, "{:.4f}")
                   + " 는 균등분포 1/√12 = 0.2887 과 넷째 자리까지 같다 — 자세마다 굴리는 "
                     "**백색 주사위**다"],
                  ["히트 집합",
                   "조명된 광선이 평균 "
                   + _n("audit_2_signal_loss.rows[1].n_lit_prod_mean", AGF, "{:.1f}", "개")
                   + ", 자세간 상대 표준편차 "
                   + _n("audit_2_signal_loss.rows[1].n_lit_prod_relstd", AGF, "{:.4f}"),
                   "자세별 히트 수 계열 ⟨" + SGZ + " : n_lit_div12⟩ 의 최대−최소가 "
                   f"{_NLIT_PTP:.0f} 개(평균의 {_NLIT_PTP_PCT:.0f} %) 다 — 어느 면이 "
                   "세어지는가가 자세마다 갈린다"]])),

        md("## 결정적 검사 — 가산성", "",
           "서로 가리지 않는 로터의 PO 면적분은 E(φ₁..φ₄) = E₀ + Σ ΔE_j(φ_j) 로 정확히 "
           "쪼개진다. 로터 넷을 따로 돌린 합과 넷을 함께 돌린 장의 차이를 잔차로 쓴다 — "
           "이 잣대에는 창도 평활도 분모도 안 들어간다.", "",
           table(["격자", "가산성 잔차 (중앙값)", "읽는 법"],
                 [["얼린 판 한 장",
                   _n("grid_pinning.matrice4e.pinned.additivity_residual_median", MCV, "{:.1e}")
                   + " ~ "
                   + _n("grid_pinning.mini5pro.pinned.additivity_residual_median", MCV, "{:.1e}"),
                   "기계정밀도 — 정리가 그대로 성립한다"],
                  ["자세마다 다시 정의",
                   _n("grid_pinning.s1000plus.moving.additivity_residual_median", MCV, "{:.3f}")
                   + " ~ "
                   + _n("grid_pinning.matrice4e.moving.additivity_residual_median", MCV, "{:.2f}"),
                   "O(1) — 물리적으로 결합할 수 없는 로터 사이에 결합이 생긴다"]]), "",
           f"그 가짜 결합이 변조로 실린다 — 기체별로 "
           f"{_n('grid_pinning.matrice4e.spurious_modulation_db', MCV, '{:+.1f}')} ~ "
           f"{_n('grid_pinning.phantom4.spurious_modulation_db', MCV, '{:+.1f}', 'dB')} 다. "
           f"교차 증거로, 광선을 안 쓰는 독립 엔진(순수 PO)과의 대역 안 스펙트럼 일치가 "
           f"{_n('in_band_fidelity.rows[1].cos_prod_vs_po', SGC, '{:.3f}')} 에서 "
           f"{_n('in_band_fidelity.rows[1].cos_froz_vs_po', SGC, '{:.3f}')} 으로 오른다."),

        md("## 얼리면 무엇이 오고 무엇을 잃나", "",
           f"잣대를 먼저 정의한다 — **대역밖 전력** P_out 은 슬로타임 스펙트럼에서 블레이드 끝 "
           f"도플러 f_tip = {_n('_meta.f_tip_hz', OOB, '{:.0f}', 'Hz')} 보다 높은 주파수의 "
           f"|X(f)|² 를 그대로 더한 값이다 ⟨{OOB} : new_definition.headline⟩ — 평활도 비율도 "
           f"안 들어가고, 정규화가 필요하면 분모를 이름에 박아 전체 전력으로 나눈다 "
           f"⟨{OOB} : new_definition.normalization⟩.", "",
           f"판 하나를 잡아 {_N_POSE} 자세에 그대로 쓰면 그 대역밖 절대 전력이 "
           f"λ/12 에서 {_n('freeze_verdict.gains_db.12', OOB, '{:.1f}')} · λ/32 에서 "
           f"{_n('freeze_verdict.gains_db.32', OOB, '{:.1f}', 'dB')} 내려간다. "
           f"⭐ 격자 사다리의 세 팔(생산 · 위상고정 · 얼림 ⟨{SGC} : _meta.arms⟩)을 예측 기울기 "
           f"≈ −2 ⟨{SGC} : _meta.prediction⟩ 에 맞대면, div ≥ 12 에서 잰 기울기가 생산 "
           f"{_n('convergence.prod.slope_ge12', OOB, '{:.2f}')}"
           f"(R² {_n('convergence.prod.r2_ge12', OOB, '{:.3f}')}) · 위상고정 "
           f"{_n('convergence.phase.slope_ge12', OOB, '{:.2f}')}"
           f"(R² {_n('convergence.phase.r2_ge12', OOB, '{:.3f}')}) · 얼림 "
           f"{_n('convergence.froz.slope_ge12', OOB, '{:.2f}')}"
           f"(R² {_n('convergence.froz.r2_ge12', OOB, '{:.3f}')}) 다 — 예측 위에 서는 것은 "
           f"위상고정과 얼림 둘이고, 얼린 팔이 적합도와 절대 바닥(λ/12 에서 P_out "
           f"{_n('convergence.froz.P_out_per_div.12', OOB, '{:.1e}')} 대 위상고정 "
           f"{_n('convergence.phase.P_out_per_div.12', OOB, '{:.1e}')})에서 앞선다. 생산 격자는 "
           f"λ/12 → λ/32 로 촘촘히 해도 "
           f"{_n('convergence.prod.drop_db_div12_to_div32', OOB, '{:.1f}', 'dB')} 만 내려간다 — "
           f"바닥의 지배 원인이 광선 밀도가 아니라는 뜻이다.", "",
           table(["대가", "크기", "무엇을 뜻하나"],
                 [["광선 수",
                   "얼린 판이 자세 평균 대비 "
                   + _n("gate2_frozen_grid_invariant.extra_ray_cost", VFG, "{:.3f}", "배"),
                   f"전 자세를 덮는 판이라 평균보다 크다 — 비용 +{_RAY_COST_PCT:.1f} %"],
                  ["디더 평균",
                   "얼린 장과 생산 장의 레벨 차가 "
                   + _n("field_level.froz_vs_prod_level_db_ptp", VFG, "{:.2f}", "dB") + " p-p",
                   "자세별 무작위 오프셋은 사실상 몬테카를로 평균이다. 얼리면 오프셋 한 판에 "
                   "절대 레벨이 걸린다 — 절대 σ 는 정적 경로에서 가져오고 얼린 복소장은 "
                   "**모양**에만 쓴다"],
                  ["⭐그 편향이 삼키는 것",
                   "판을 반 칸 옮기면 절대 레벨이 "
                   + _n("verdict.abs_level_plate_ptp_db", FPS, "{:.2f}", "dB")
                   + " p-p, **두 팔의 차**(가림 축)가 "
                   + _n("verdict.occlusion_level_plate_ptp_db", FPS, "{:.2f}", "dB") + " p-p",
                   "두 팔이 같은 판을 써도 기하가 달라 편향이 공통모드로 빠지지 않는다 — "
                   "차가 원본보다 더 흔들린다. 가림 dB 의 **크기**는 "
                   + ref("md-occlusion", "가림 축") + " 에서 판 앙상블 평균이 설 때까지 "
                   "보류다"],
                  ["대역 안도 같이 내려간다",
                   "블레이드 대역 전력 중앙값 "
                   + _n("summary.P_in_delta_db_median", FSL, "{:+.1f}", "dB"),
                   "대역밖만 내려가는 것이 아니다 — 아래 절이 그 몫이 잡음이었는지를 "
                   "광선을 안 쓰는 엔진으로 판정한다"],
                  ["판을 미리 잡는 일",
                   "덮개 여유 최소 "
                   + _n("gate3_coverage.margin_min_mm", VFG, "{:.1f}", "mm"),
                   "자세열을 먼저 훑어야 판이 나온다 — 스트리밍으로는 못 잡는다"]]), "",
           f"커널의 기본값은 `grid_ref=None` 이다 — 그 값이면 배선 전 커널과 "
           f"{_n('gate1_bit_identity.n_bit_identical', VFG, '{:.0f}')}/"
           f"{_n('gate1_bit_identity.n_cases', VFG, '{:.0f}')} 비트 동일이라 "
           f"(최대 상대오차 {_n('gate1_bit_identity.max_rel_err', VFG, '{:.1f}')}) 옛 원장이 "
           f"그대로 선다. 판을 잡는 쪽은 호출자다 — 슬로타임 경로(`src/microdoppler.py`)는 로터 "
           f"한 바퀴의 합집합 경계상자로 판 한 장을 만들어 넘기고, 스위치 "
           f"`SIONNA2_FREEZE_GRID` 가 그 켬·끔을 정한다(기본 켬). 판이 자세를 못 덮으면 커널이 "
           f"예외를 던진다 ⟨{VFG} : negative_controls.too_small_msg⟩.", "",
           _r8_freeze_status()),

        md("## 얼리기가 «신호» 도 깎았나 — 광선을 안 쓰는 엔진에게 묻는다", "",
           "대역밖 전력이 내려간 것은 좋은 소식이다. 그런데 같은 재계산에서 **블레이드 대역 "
           "안**의 전력도 함께 내려갔다 — 중앙값 "
           + _n("summary.P_in_delta_db_median", FSL, "{:+.1f}", "dB")
           + " 다. 그 몫이 표적의 진짜 운동이었다면 얼리기는 물리를 지운 것이다. 그래서 "
           "판정을 **광선 격자를 안 쓰는 엔진**에게 맡긴다 — 순수 PO 는 점구름 면적분이라 "
           "격자가 없고, 이번 재계산에서 비트 그대로였다"
           f" ⟨{FSL} : _meta.independent_judge_ko⟩.", "",
           table(["잣대", "얼리기 전", "얼린 뒤", "무엇을 뜻하나"],
                 [["블레이드 대역이 순수 PO 보다 몇 dB 위인가",
                   _n("summary.P_in_excess_over_po_db.before_median", FSL, "{:+.1f}", "dB"),
                   _n("summary.P_in_excess_over_po_db.after_median", FSL, "{:+.1f}", "dB"),
                   "PO **밑으로** 내려간 열이 "
                   + _n("summary.P_in_excess_over_po_db.n_below_po_after", FSL, "{:.0f}")
                   + " 개다 — 깎인 것은 잉여였다"],
                  ["같은 대역 복소 파형이 PO 와 닮은 정도",
                   _n("summary.blade_coh_vs_po.before_median", FSL, "{:.2f}"),
                   _n("summary.blade_coh_vs_po.after_median", FSL, "{:.2f}"),
                   _n("summary.blade_coh_vs_po.n_improved", FSL, "{:.0f}") + "/"
                   + _n("summary.blade_coh_vs_po.n_judged", FSL, "{:.0f}")
                   + " 열에서 올랐다 — 전력이 줄면서 닮음이 오르면 줄어든 것은 잡음이다"],
                  ["플래시 대조비 (봉우리 ÷ 바닥)",
                   "—",
                   _n("summary.flash_contrast_db.delta_median", FSL, "{:+.1f}", "dB") + " (중앙값)",
                   _n("summary.flash_contrast_db.n_improved", FSL, "{:.0f}") + "/"
                   + _n("summary.flash_contrast_db.n_series", FSL, "{:.0f}")
                   + " 열에서 올랐다 — 자의 흔들림이 골짜기를 메우고 있었다는 뜻이다"],
                  ["플래시 주파수 추정의 상대오차",
                   _n("summary.f_flash_relerr_abs_median.before", FSL, "{:.2%}"),
                   _n("summary.f_flash_relerr_abs_median.after", FSL, "{:.2%}"),
                   "포락 자기상관으로 읽은 f_flash — 두 판 다 예측 위에 선다"],
                  ["스펙트럼 가장자리 ÷ f_tip (운동학이 맞으면 1)",
                   _n("summary.width_ratio_20db.before_median", FSL, "{:.2f}"),
                   _n("summary.width_ratio_20db.after_median", FSL, "{:.2f}"),
                   "순수 PO 는 " + _n("summary.width_ratio_20db.po_median", FSL, "{:.2f}")
                   + " 다 — ⚠"
                   + _n("summary.width_ratio_20db.n_farther_from_one", FSL, "{:.0f}")
                   + " 열은 얼린 뒤 1 에서 더 멀어진다. 폭 지표는 PO 열에서 읽는다"]]), "",
           "⚠ **대가는 비율 쪽에 있다.** 절대 대역밖 전력은 내려가지만 블레이드 대역이 더 많이 "
           "내려가는 열이 있어서, «신호 대 비물리 잔차»(P_out/P_in)로 읽으면 동체가 든 "
           + _n("summary.by_group.with_body.n", FSL, "{:.0f}") + " 열 중 "
           + _n("summary.by_group.with_body.n_oob_worse", FSL, "{:.0f}") + " 열이 "
           + _n("summary.by_group.with_body.oob_over_in_db_before_median", FSL, "{:.1f}", "dB")
           + " → "
           + _n("summary.by_group.with_body.oob_over_in_db_after_median", FSL, "{:.1f}", "dB")
           + " 로 **나빠진다**(순수 PO 는 "
           + _n("summary.oob_over_in_db.po_median", FSL, "{:.1f}", "dB")
           + "). 잉여가 사라진 만큼 남은 잔차가 상대적으로 커 보이는 것이고, 그 잔차는 여전히 "
           "물리가 아니다 — 지금 판이 마이크로도플러에 줄 수 있는 동적범위의 상한이 여기 있다.", "",
           "반대로 블레이드만 남긴 "
           + _n("summary.by_group.blade_only.n", FSL, "{:.0f}") + " 열은 빗살 대조비가 "
           + _n("summary.by_group.blade_only.n_comb_improved", FSL, "{:.0f}") + "/"
           + _n("summary.by_group.blade_only.n", FSL, "{:.0f}") + " 열에서 "
           + _n("summary.by_group.blade_only.comb_line_delta_db_median", FSL, "{:+.1f}", "dB")
           + " 올라온다 — 신호가 약할수록 얼리기가 크게 남는다"
           + f" ⟨{FSL} : summary.by_group.why_ko⟩.", "",
           "⚠ 심판이 아직 붙지 않은 자리가 하나 남는다"
           + f" ⟨{FSL} : verdict.open_ko⟩ — 2 초 호버 두 열은 순수 PO 대조 팔을 기다린다."),

        next_steps([
            ("얼린 판으로 **바이스태틱** 스윕 원장과 PO 대조 원장을 다시 낸다",
             "모노 쪽은 갈아탔고(리포트 8-2), 남은 두 원장만 아직 옛 판이라 "
             "두 편의 절대값을 이어 붙여 읽을 수 없다",
             "`src/microdoppler.py`(판을 넘기는 쪽) → " + ref("md-slowtime", short=True)),
            ("B 팔 광선격자의 자기 불확도를 P 팔 바닥과 **같은 통계**(방위 72점 평균 σ)로 잰다",
             "가림 축의 판정 바닥이 두 팔 모두에서 서고, 어느 기체가 판정 안에 드는지가 확정된다",
             f"`src/viz_mesh_material.py` 가림 축 → {DER} `occlusion.floor_db`"),
            ("정정된 메쉬로 가림 표와 생산 σ 를 같은 설정에서 다시 낸다",
             "형상 정정이 가림과 σ 를 어느 방향으로 얼마나 옮기는지가 기체별로 확정된다",
             f"⟨{MFX_ATK} : recommended_gate_before_any_sigma_claim⟩"),
            ("같은 메쉬를 스톡 경로 솔버에 그대로 넣고 무엇이 나오는지 잰다",
             "우리 커널이 스톡 위에 얹은 항이 무엇인지가 나란히 확정된다",
             ref("kernel-vs-stock", short=True)),
            ("수신 방향 그림자 광선을 켜고 바이스태틱으로 넓힌다",
             "출사 쪽 가림이 상반성 위반을 얼마나 줄이는지가 확정된다",
             ref("bistatic-exit", short=True)),
            ("PO 면적분을 디바이스 커널로 옮긴다",
             "전격자 재생성 비용이 확정된다 — 지금은 호스트가 대부분을 쓴다",
             ref("kernel-vs-stock", short=True)),
        ]),
    ]


# =========================================================================== #
#  편 19 — kernel-vs-stock
# =========================================================================== #
def report_19_kernel_vs_stock():
    return [
        header(
            num=19,
            title="스톡 솔버와 맞대면 «면이 많아서 에코가 커진다» 가설은 반증되고, "
                  f"런타임의 {_lit('answer.cost_structure.host_side_pct', RUN, '{:.1f}')}% 는 "
                  "호스트가 쓴다",
            did="같은 메쉬를 스톡 경로 솔버에 그대로 넣고 경로 수·진폭·런타임을 우리 커널과 "
                "같은 카드에서 나란히 쟀다.",
            results=[
                f"삼각형 {_n('levels[0].n_tri', FCNT, '{:,.0f}', '개')}(mavic4pro)에서 광선 예산 "
                f"{_n('meta.spp_main', FCNT, '{:.1e}', 'spp')} 일 때 스톡 경로는 자세당 "
                f"{_n('levels[0].rt_n_paths_mean', FCNT, '{:.1f}', '개')} 다.",

                f"이미지법 정반사 경로는 "
                f"{_n('levels[0].spec_n_aspects', FCNT, '{:.0f}', '자세')} 를 통틀어 "
                f"{_n('levels[0].spec_n_paths_total', FCNT, '{:.0f}', '개')}(자세 "
                f"{_n('levels[0].spec_n_aspects_nonzero', FCNT, '{:.0f}', '개')})다 — 나머지 "
                f"진폭은 확산 항이 낸다.",

                f"«면이 많아서 에코가 커진다» 가설은 스톡 기울기 "
                f"{_n('slopes.stock_incoh', FCNT, '{:.3f}', 'dB/decade')} 로 "
                f"{_n('verdict.result', FCNT)} 다.",

                f"평판 대조군에서 정반사 진폭은 무한거울 값 "
                f"{_n('theory.amp_image_source_db', FMEC, '{:.2f}', 'dB')} 에 고정되어, 판 크기를 "
                f"{_n('VERDICT.plate_size_invariance.size_ratio_max', FMEC, '{:.0f}', '배')} 로 "
                f"키워도 {_n('VERDICT.plate_size_invariance.rt_spread_db', FMEC, '{:.1e}', 'dB')} "
                f"안에 머문다.",

                f"런타임은 같은 통계로 나란히 적는다 — S(스톡 PathSolver) "
                f"{_n('answer.same_card_control.stock_sionna_pathsolver_ms.min', RUN, '{:.1f}')}~"
                f"{_n('answer.same_card_control.stock_sionna_pathsolver_ms.max', RUN, '{:.1f}', 'ms')}"
                f"(중앙값 "
                f"{_n('answer.same_card_control.stock_sionna_pathsolver_ms.median', RUN, '{:.1f}', 'ms')}"
                f" · {_n('answer.same_card_control.stock_sionna_pathsolver_ms.n_configs', RUN, '{:.0f}', '설정')})"
                f" 대 B(우리 per-pose) "
                f"{_n('production_per_pose.summary_ms.min', RUN, '{:.1f}')}~"
                f"{_n('production_per_pose.summary_ms.max', RUN, '{:.1f}', 'ms')}(중앙값 "
                f"{_n('production_per_pose.summary_ms.median', RUN, '{:.1f}', 'ms')}) 다. 이 대조가 "
                f"통제하는 것은 하드웨어이고, 두 팔이 재는 양은 경로 해와 σ 로 갈린다 "
                f"⟨{RUN} : answer.same_card_control.caveat⟩.",
            ],
            method=[
                ("같은 메쉬", "우리 커널이 먹는 그 메쉬를 스톡 경로 솔버에 그대로 넣는다 — "
                          "면 수·광선예산·자세 격자를 맞춘다"),
                ("면 수 축", "같은 형상을 테셀레이션만 바꿔 쌓고 스톡 에코의 기울기를 "
                          "dB/decade 로 잰다"),
                ("평판 대조군", "닫힌형 무한거울 진폭이 있는 평판에서 판 크기만 키운다 — "
                            "경로 진폭이 면적을 보는지가 여기서 갈린다"),
                ("런타임", "같은 카드에서 스톡 PathSolver 와 우리 per-pose 를 나란히 재고, "
                        "비용을 호스트/GPU 단계로 쪼갠다"),
            ],
            repro=_repro(["PYTHONPATH=src python benchmark/facet_count.py",
                          "PYTHONPATH=src python benchmark/runtime_benchmark.py"],
                         [FCNT, FMEC, RUN],
                         "약 40분 (GPU 1장 — 스톡 솔버와 우리 커널을 같은 카드에서 돌린다)",
                         "런타임은 같은 카드·같은 세션에서 재야 비교가 선다"),
        ),

        md("## 같은 메쉬를 스톡에 그대로 넣으면", "",
           f"삼각형 {_n('levels[0].n_tri', FCNT, '{:,.0f}', '개')}(mavic4pro)에서 광선 예산 "
           f"{_n('meta.spp_main', FCNT, '{:.1e}', 'spp')} 일 때 경로는 자세당 "
           f"{_n('levels[0].rt_n_paths_mean', FCNT, '{:.1f}', '개')} 다. 그중 **이미지법 "
           f"정반사** 경로는 {_n('levels[0].spec_n_aspects', FCNT, '{:.0f}', '자세')} 를 통틀어 "
           f"{_n('levels[0].spec_n_paths_total', FCNT, '{:.0f}', '개')}(자세 "
           f"{_n('levels[0].spec_n_aspects_nonzero', FCNT, '{:.0f}', '개')})뿐이다.", "",
           "나머지 진폭은 확산 항이 낸다 — 그 항은 정규화 산란패턴을 쓰는 경험 모델이라 "
           "표면전류 적분이 아니다. 그래서 σ 를 얹을 자리가 생긴다."),

        md("## «면이 많아서 에코가 커진다» 를 반증했다", "",
           f"평판 대조군에서 정반사 진폭은 무한거울 값 "
           f"{_n('theory.amp_image_source_db', FMEC, '{:.2f}', 'dB')} 에 고정되어, 판 크기를 "
           f"{_n('VERDICT.plate_size_invariance.size_ratio_max', FMEC, '{:.0f}', '배')} 로 키워도 "
           f"{_n('VERDICT.plate_size_invariance.rt_spread_db', FMEC, '{:.1e}', 'dB')} 안에 "
           f"머문다. 같은 축을 드론 메쉬에서 재면 스톡 기울기가 "
           f"{_n('slopes.stock_incoh', FCNT, '{:.3f}', 'dB/decade')} 이고, 판정은 "
           f"**{_n('verdict.result', FCNT)}** 다.", "",
           f"⭐ S(스톡) 쪽에서 면 수가 값을 옮기는 자리는 **이미지법 중복 경로** 하나다 — 한 변 "
           f"{_n('H_tessellation_changes_the_answer.numbers.per_side[1].side_m', EVD, '{:.0f}', 'm')} "
           f"금속 평판을 "
           f"{_n('H_tessellation_changes_the_answer.numbers.per_side[1].n_tri[0]', EVD, '{:.0f}')} → "
           f"{_n('H_tessellation_changes_the_answer.numbers.per_side[1].n_tri[4]', EVD, '{:.0f}', '삼각형')} "
           f"으로 쪼개면 코히런트 전력이 "
           f"{_n('H_tessellation_changes_the_answer.numbers.max_inflation_db', EVD, '{:.2f}', 'dB')} "
           f"오르고, 늘어난 경로는 진폭·위상·지연이 같은 복사본이라 합이 20·log10(N) 을 "
           f"{_n('H_tessellation_changes_the_answer.numbers.coherent_N_law_max_resid_db', EVD, '{:.4f}', 'dB')} "
           f"안에서 따른다 ⟨{EVD} : H_tessellation_changes_the_answer.claim⟩.", "",
           f"⭐ 이 반증이 부 1 의 결론과 같은 물건이다 — 경로 진폭은 면적·곡률·치수를 인자로 "
           f"받지 않는다. 그 인자 목록은 {ref('eight-factors', short=True)} 에 있다."),

        md("## 비용은 어디에 있나", "",
           f"같은 카드에서 같은 통계로 나란히 쟀다 — S(스톡 PathSolver) "
           f"{_n('answer.same_card_control.stock_sionna_pathsolver_ms.min', RUN, '{:.1f}')}~"
           f"{_n('answer.same_card_control.stock_sionna_pathsolver_ms.max', RUN, '{:.1f}', 'ms')}"
           f"({_n('answer.same_card_control.stock_sionna_pathsolver_ms.n_configs', RUN, '{:.0f}', '설정')})"
           f" 대 B(우리 per-pose) "
           f"{_n('production_per_pose.summary_ms.min', RUN, '{:.1f}')}~"
           f"{_n('production_per_pose.summary_ms.max', RUN, '{:.1f}', 'ms')}, 중앙값끼리는 "
           f"{_n('answer.same_card_control.stock_sionna_pathsolver_ms.median', RUN, '{:.1f}')} 대 "
           f"{_n('production_per_pose.summary_ms.median', RUN, '{:.1f}', 'ms')} 다.", "",
           f"⚠ 두 팔은 다른 양을 잰다 — S 는 씬의 경로 해, B 는 표적 σ 이고 씬 내용도 갈린다. "
           f"이 대조가 통제하는 것은 하드웨어다 ⟨{RUN} : answer.same_card_control.caveat⟩. 사다리는 "
           f"자릿수를 놓는 것이고 같은 양을 잰 속도비는 그 뒤의 일이다 "
           f"⟨{RUN} : answer.what_the_measurement_does_NOT_support[2]⟩.", "",
           f"그 비용의 {_n('answer.cost_structure.host_side_pct', RUN, '{:.1f}', '%')} 가 "
           f"호스트에 있고 GPU 광선추적은 "
           f"{_n('production_per_pose.stage_pct_median_over_configs.rt_trace', RUN, '{:.1f}', '%')} "
           f"다. PO 단계가 "
           f"{_n('production_per_pose.stage_pct_median_over_configs.po', RUN, '{:.1f}', '%')} 이므로 "
           f"디바이스로 옮길 자리는 거기다 — 전격자 재생성 추정은 "
           f"{_n('production_per_pose.whole_published_grid.projected_hours', RUN, '{:.2f}', 'h')} 다."),

        next_steps([
            ("PO 면적분을 디바이스 커널로 옮긴다",
             "전격자 재생성 비용이 확정된다 — 지금 호스트 몫이 대부분이다",
             "`src/rcs_sbr.py` → `outputs/runtime_benchmark.json` 재측정"),
            ("면 수 축을 표적 사다리의 운동학 축과 분리해 다시 읽는다",
             "형상 정밀도가 σ 에 주는 몫이 광선예산 몫과 갈린다",
             ref("ladder-answer", short=True)),
            ("기준해와 맞대 커널의 구현오차를 확정한다",
             "이 커널이 PO 를 제대로 계산하는지가 kr 전 구간에서 확정된다",
             ref("kernel-vs-reference", short=True)),
        ]),
    ]


# =========================================================================== #
#  편 20 — bistatic-exit
# =========================================================================== #
def report_20_bistatic_exit():
    return [
        header(
            num=20,
            title="수신 방향 그림자 광선을 켜면 상반성 위반이 "
                  f"{_lit('d2_exit_vis_effect_on_reciprocity.worst_without_exit_vis_db', DFX)}"
                  f" → "
                  f"{_lit('d2_exit_vis_effect_on_reciprocity.worst_with_exit_vis_db', DFX)}"
                  " dB 로 내려간다",
            did="각 충돌점에서 수신기 방향으로 그림자 광선을 한 번 더 쏘아 출사 쪽 가림을 "
                "판정하고, 그 효과를 상반성으로 쟀다.",
            results=[
                f"상반성 위반 최대치(전 β 최악)가 "
                f"{_n('d2_exit_vis_effect_on_reciprocity.worst_without_exit_vis_db', DFX, '{:.2f}')} → "
                f"{_n('d2_exit_vis_effect_on_reciprocity.worst_with_exit_vis_db', DFX, '{:.2f}', 'dB')} "
                f"로 내려간다.",

                f"모노스태틱에서 이 검사는 무연산이라 생산 σ 는 "
                f"{_n('d4_epsilon_sensitivity.combos[0].by_drone.mavic4pro.monostatic_noop_max_abs_db', DFX, '{:.3e}', 'dB')} "
                f"그대로다 — 켜도 옛 결과가 안 움직인다.",

                f"바이스태틱 자세 패턴은 β ≤ "
                f"{_n('d2_exit_vis_effect_on_reciprocity.beta_deg[3]', DFX, '{:.0f}', '°')} 에서 "
                f"성립한다 — 그 범위의 상반성 RMS 가 "
                f"{_n('d2_exit_vis_effect_on_reciprocity.rms_with_exit_vis_db[3]', DFX, '{:.2f}', 'dB')} "
                f"다.",

                f"이 단계는 Sagitta(preprint, arXiv:2604.09243 각주 1)가 바이스태틱 SBR 에서 "
                f"빠져 있다고 지목한 바로 그 단계다 — 선행이 이름 붙인 구멍을 메운 자리다.",
            ],
            method=[
                ("출사 가시성", "각 충돌점에서 수신기 방향으로 그림자 광선을 한 번 더 쏜다 "
                            "(`src/rcs_sbr.py` `rcs_sbr_multistatic()`)"),
                ("무엇으로 재나", "**상반성** — 보내는 자리와 받는 자리를 맞바꿔도 σ 가 같아야 "
                             "한다는 성질이다. 위반량이 곧 모형오차의 크기다"),
                ("모노스태틱 대조", "송수신이 같은 자리면 이 검사가 무연산이 되는지 확인한다 — "
                               "옛 생산 σ 가 안 움직여야 한다"),
                ("유효창", "β 를 키우며 상반성 RMS 를 재서 자세 패턴을 주장할 범위를 못박는다"),
            ],
            repro=_repro(["PYTHONPATH=src python benchmark/verify_sbr_defect_fixes.py"],
                         [DFX], "약 25분 (GPU 1장)",
                         "상반성은 정리(theorem)라 위반량이 그대로 모형오차의 하한이다"),
        ),

        md("## 무엇을 한 번 더 쏘나", "",
           "각 충돌점에서 수신기 방향으로 그림자 광선을 한 번 더 쏘아 **출사 쪽 가림**을 "
           "판정한다(`src/rcs_sbr.py` `rcs_sbr_multistatic()`). 조명 쪽만 보면 «빛이 닿는 면» "
           "까지는 맞지만, 그 면이 수신기에서 보이는지는 따로 물어야 한다.", "",
           "Sagitta(preprint, arXiv:2604.09243 각주 1)가 바이스태틱 SBR 에서 빠져 있다고 지목한 "
           "바로 그 단계다."),

        md("## 켠 효과 — 상반성으로 잰다", "",
           f"**상반성**은 보내는 자리와 받는 자리를 맞바꿔도 σ 가 같아야 한다는 성질이다. "
           f"정리이므로 위반량이 그대로 모형오차의 크기다. 위반 최대치가 "
           f"{_n('d2_exit_vis_effect_on_reciprocity.worst_without_exit_vis_db', DFX, '{:.2f}')} → "
           f"{_n('d2_exit_vis_effect_on_reciprocity.worst_with_exit_vis_db', DFX, '{:.2f}', 'dB')} "
           f"로 내려간다.", "",
           f"모노스태틱에서 이 검사는 무연산이라 생산 σ 는 "
           f"{_n('d4_epsilon_sensitivity.combos[0].by_drone.mavic4pro.monostatic_noop_max_abs_db', DFX, '{:.3e}', 'dB')} "
           f"그대로다 — 새 단계를 켜도 옛 모노스태틱 결과가 한 눈금도 안 움직인다는 뜻이다."),

        md("## 두 계열을 나란히 — β 별 RMS", "",
           f"헤드라인 {_n('d2_exit_vis_effect_on_reciprocity.worst_without_exit_vis_db', DFX, '{:.2f}')} → "
           f"{_n('d2_exit_vis_effect_on_reciprocity.worst_with_exit_vis_db', DFX, '{:.2f}', 'dB')} 는 "
           f"**전 β 최악값** 하나의 개선이다. β 별 RMS 로 내려가면 두 방향이 함께 있다.", "",
           table(["β [°]", "출사 가시성 끔 [dB]", "출사 가시성 켬 [dB]"],
                 [[_n(f'd2_exit_vis_effect_on_reciprocity.beta_deg[{i}]', DFX, '{:.0f}'),
                   _n(f'd2_exit_vis_effect_on_reciprocity.rms_without_exit_vis_db[{i}]',
                      DFX, '{:.2f}'),
                   _n(f'd2_exit_vis_effect_on_reciprocity.rms_with_exit_vis_db[{i}]',
                      DFX, '{:.2f}')] for i in range(1, 7)]), "",
           f"β "
           f"{_n('d2_exit_vis_effect_on_reciprocity.beta_deg[3]', DFX, '{:.0f}', '°')}"
           f"(주장 창의 경계)와 "
           f"{_n('d2_exit_vis_effect_on_reciprocity.beta_deg[5]', DFX, '{:.0f}', '°')} 두 칸에서는 "
           f"켠 계열이 더 크다 — 창 규칙의 문턱 RMS 는 그 경계 칸의 값으로 세워져 있다. 나머지 네 "
           f"칸과 전 β 최악값에서는 켠 쪽이 더 작다."),

        md("## 자세 패턴을 주장할 범위", "",
           f"**바이스태틱 자세 패턴은 β ≤ "
           f"{_n('d2_exit_vis_effect_on_reciprocity.beta_deg[3]', DFX, '{:.0f}', '°')} 에서 "
           f"성립한다** — 창 규칙은 «경계 안 상반성 RMS ≤ "
           f"{_n('d2_exit_vis_effect_on_reciprocity.rms_with_exit_vis_db[3]', DFX, '{:.2f}', 'dB')}"
           f"» 이고, 경계는 선언값이다. RMS 는 β 에 단조가 아니라 β 60° 에서 "
           f"{_n('d2_exit_vis_effect_on_reciprocity.rms_with_exit_vis_db[4]', DFX, '{:.2f}')} 로 "
           f"내려왔다가 β 90° 에서 "
           f"{_n('d2_exit_vis_effect_on_reciprocity.rms_with_exit_vis_db[6]', DFX, '{:.2f}', 'dB')} "
           f"까지 오른다. 그 위의 β 는 창 밖이고, 검출 기하가 이 창 안에 드는지는 "
           f"{ref('geometry', short=True)} 가 확인한다.", "",
           f"전방산란 쪽 끝(β→180°)은 조명 게이트와 수신 게이트가 상호배타라 σ ≡ 0 이 된다 — "
           f"주장 창을 후방~중간 바이스태틱각으로 못박는 이유이고, 그 목록은 "
           f"{ref('kernel-open-items', short=True)} 에 있다."),

        md("## 이 절의 수치가 서 있는 자리", "",
           f"⚠ 위 상반성 표는 각도 모양 |Γ(θ)| 가 바이스태틱 경로에 들어오기 **전** 커널의 "
           f"산출이다. 지금 그 경로는 각도 모양을 곱하고, 같은 씬에서 복소장과 σ 두 경로가 "
           f"{_n('verdict.sigma_angle_gamma_gap_db', VBF, '{:.0e}', 'dB')} 안에서 맞는다 "
           f"⟨{VBF} : kernel.angle_gamma_wired⟩ — 상반성 표는 그 커널로 다시 낼 대상이다.", "",
           f"⚠ 그리고 **생산 검출 사슬은 이 커널을 부르지 않는다** — σ 를 모노스태틱 격자에서 "
           f"이등분선 방향으로 조회한다. 그 근사의 크기가 β 15° 에서 rms 중앙 "
           f"{_n('sigma_transfer.bisector_approximation_error_by_beta.15.dsigma_rms_median_db', GEO, '{:.2f}')}"
           f" · p95 최대 "
           f"{_n('sigma_transfer.bisector_approximation_error_by_beta.15.dsigma_p95_max_db', GEO, '{:.1f}', 'dB')}"
           f" 이므로, 검출 결과가 인용하는 β 가 몇 도인지가 그 근사의 유효성을 정한다 "
           f"({ref('geometry', short=True)})."),

        next_steps([
            ("2회 반사를 β 별로 다시 돌린다",
             "바이스태틱 유효범위가 45° 위로 얼마나 넓어지는지 확정된다",
             "`src/rcs_sbr.py` `rcs_sbr_multistatic()` 상반성 검사"),
            ("검출 기하가 이 창 안에 드는지 확인한다",
             "결과 편이 인용하는 β 가 자세 패턴 유효창 안인지가 확정된다",
             ref("geometry", short=True)),
            ("대칭 사입사 인자 √((n̂·û_i)(n̂·û_s)) 를 grazing 안정화와 함께 다시 시도한다",
             "상반성 위반이 격자 폭발 없이 줄어드는지가 확정된다 — 지금은 표준 (n̂·û_i) 를 두고 "
             "σ 레벨 기하평균(`symmetrize=True`)으로 우회한다",
             f"`src/rcs_sbr.py` `rcs_sbr_multistatic()` obliquity 주석 "
             f"⟨{ARK} : q2_mono_bi_multistatic.obliquity_question.code_says⟩"),
        ]),
    ]


# =========================================================================== #
#  편 21 — kernel-vs-reference
# =========================================================================== #
def report_21_kernel_vs_reference():
    return [
        header(
            num=21,
            title="해석 PO 구 대비 구현오차는 kr 전 구간에서 λ/16 격자 "
                  f"{_lit('summary_div16.max_abs_db_vs_po', KRS, '{:.3f}')} dB · 생산 λ/12 격자 "
                  f"{_lit('summary_div12.max_abs_db_vs_po', KRS, '{:.3f}')} dB 안이다",
            did="구 후방산란의 닫힌형 기준해 둘과 이면각 닫힌형에 커널을 맞대 구현오차와 모형 "
                "간극을 따로 쟀다.",
            results=[
                f"해석 PO 구 대비 최대 편차가 kr "
                f"{_n('summary_div16.kr_min', KRS, '{:.0f}')}~"
                f"{_n('s3_validation.layer1_analytic_po_convergence.kr_sweep_kr_max', POC, '{:.0f}')} "
                f"전 구간에서 λ/16 격자 "
                f"{_n('summary_div16.max_abs_db_vs_po', KRS, '{:.3f}')} · 생산 λ/12 격자 "
                f"{_n('summary_div12.max_abs_db_vs_po', KRS, '{:.3f}', 'dB')} 다(입사 "
                f"{_n('s3_validation.layer1_analytic_po_convergence.kr_sweep_n_incidence', POC, '{:.0f}', '방향')}).",

                f"정확 Mie 대비 최대 편차는 λ/16 격자 "
                f"{_n('summary_div16.max_abs_db_vs_mie', KRS, '{:.2f}')} · 생산 λ/12 격자 "
                f"{_n('summary_div12.max_abs_db_vs_mie', KRS, '{:.2f}', 'dB')}(kr=1) 이고, "
                f"이쪽이 PO 라는 모형 자체의 간극이다 — 격자를 "
                f"{_n('s3_validation.layer1_analytic_po_convergence.sphere_ka1_grid_refine_factor', POC, '{:.0f}', '배')} "
                f"조여도 "
                f"{_n('s3_validation.layer2_pec_sphere_mie.improvement_from_refining_grid_db', POC, '{:.3f}', 'dB')} "
                f"움직인다.",

                f"kr ≥ 30 산포는 λ/16 격자에서 해석 PO 대비 "
                f"{_n('summary_div16.std_sbr_over_po_pct_kr_ge30', KRS, '{:.3f}', '%')} · Mie 대비 "
                f"{_n('summary_div16.std_sbr_over_mie_pct_kr_ge30', KRS, '{:.3f}', '%')} 이고, "
                f"생산 λ/12 격자에서 "
                f"{_n('summary_div12.std_sbr_over_po_pct_kr_ge30', KRS, '{:.3f}', '%')} · "
                f"{_n('summary_div12.std_sbr_over_mie_pct_kr_ge30', KRS, '{:.3f}', '%')} 다.",

                f"PEC 이면각 닫힌형 8πa²b²/λ² 와는 2회 반사에서 최대 "
                f"{_n('d3_multibounce_phase.max_abs_err_db', DFX, '{:.3f}', 'dB')} 다 — "
                f"다중반사 위상이 맞는다는 뜻이다.",

                f"기체 7 × 밴드 3 = "
                f"{_n('electrical.n_airframe_band', DER, '{:.0f}', '조합')} 중 "
                f"{_n('electrical.n_below_po_1db', DER, '{:.0f}', '개')} 가 Mie 기준 1 dB 문턱 "
                f"아래에 놓이고, 그것이 실측 대상 "
                f"{_n('electrical.kr_min_name', DER)} 다.",
            ],
            method=[
                ("기준해 둘", "구에 대해서만 맥스웰 방정식이 그대로 풀리는 **정확 Mie** 와, 같은 "
                          "구에 PO 근사를 적용해 손으로 푼 **해석 PO** 다 "
                          "(`benchmark/mie_pec_sphere.py:98`, `:127`)"),
                ("왜 둘인가", "(커널 − Mie) = (커널 − 해석 PO) + (해석 PO − Mie) 다. 앞항은 "
                          "**구현오차**(격자를 조이면 준다), 뒷항은 **모형오차**(격자로는 안 준다)"),
                ("다중반사", "직각 이면각 이등분선 입사의 닫힌형 8πa²b²/λ² 와 변 길이 4점에서 "
                         "맞댄다(`benchmark/verify_sbr_defect_fixes.py`, λ/12 격자)"),
                ("자기검사", "상반성 σ(û_i,û_s)=σ(û_s,û_i) 위반을 기체에서 잰다 — 정리 위반이 "
                         "곧 모형오차다"),
            ],
            repro=_repro(["PYTHONPATH=src python benchmark/sbr_kr_sweep.py",
                          "PYTHONPATH=src python benchmark/verify_sbr_defect_fixes.py"],
                         [KRS, DFX, POC, DER],
                         "약 1시간 (GPU 1장 — kr 스윕이 대부분이다)",
                         "두 기준해는 우리 출력이 아니라 과녁이다"),
        ),

        md("## 과녁이 둘이고, 재는 것이 다르다", "",
           "구 후방산란은 두 개의 **닫힌형 기준해**(근사 없이 식으로 바로 값이 나오는 답)를 "
           "갖는다 — 구에 대해서만 맥스웰 방정식이 그대로 풀리는 **정확 Mie** 와, 같은 구에 PO "
           "근사를 적용해 손으로 푼 **해석 PO** 다. 둘 다 우리 출력이 아니라 과녁이다.", "",
           "```",
           "(커널 − Mie)  =  (커널 − 해석 PO)   +   (해석 PO − Mie)",
           "                  ↑ 우리 수치오차          ↑ PO 모델 자체의 간극",
           "```",
           "커널이 PO 이므로 **수치 수렴의 과녁은 해석 PO** 이고, Mie 잔차는 PO 모델 자체의 "
           "간극이라는 두 번째 눈금이다. 둘을 나눠 두면 각각이 얼마인지 그대로 읽힌다."),

        md("## 일곱 기체가 놓인 자리에서 각각 얼마인가", "",
           *_fig(1, "report02_f5_reference_gap",
                 "일곱 기체가 놓인 kr 자리에서 우리 수치오차와 PO 모델의 간극은 각각 얼마인가?")),

        md("## 두 눈금 — 격자 두 개에서", "",
           table(["", "우리 수치오차 · 기준해 = 해석 PO", "PO 모델의 간극 · 기준해 = 정확 Mie"],
                 [["최대 편차 (kr=1..100) · λ/16",
                   _n('summary_div16.max_abs_db_vs_po', KRS, '{:.3f}', 'dB'),
                   _n('summary_div16.max_abs_db_vs_mie', KRS, '{:.2f}', 'dB') + " (kr=1)"],
                  ["최대 편차 (kr=1..100) · 생산 λ/12",
                   _n('summary_div12.max_abs_db_vs_po', KRS, '{:.3f}', 'dB'),
                   _n('summary_div12.max_abs_db_vs_mie', KRS, '{:.2f}', 'dB') + " (kr=1)"],
                  ["kr≥30 산포 · λ/16",
                   _n('summary_div16.std_sbr_over_po_pct_kr_ge30', KRS, '{:.3f}', '%'),
                   _n('summary_div16.std_sbr_over_mie_pct_kr_ge30', KRS, '{:.3f}', '%')],
                  ["kr≥30 산포 · 생산 λ/12",
                   _n('summary_div12.std_sbr_over_po_pct_kr_ge30', KRS, '{:.3f}', '%'),
                   _n('summary_div12.std_sbr_over_mie_pct_kr_ge30', KRS, '{:.3f}', '%')],
                  ["1 dB 안으로 드는 kr",
                   "전 구간 (kr=" + _n('summary_div16.kr_min', KRS, '{:.0f}') + " 부터)",
                   "kr ≥ " + _n('po_floor.kr_below_1p0_db', DER, '{:.2f}')],
                  ["0.5 / 0.2 dB 안으로",
                   "전 구간",
                   _n('po_floor.kr_below_0p5_db', DER, '{:.2f}') + " / "
                   + _n('po_floor.kr_below_0p2_db', DER, '{:.2f}')]]), "",
           "격자를 두 줄로 적는 이유는 사슬이 둘이기 때문이다 — 커널 기본은 λ/12"
           "(`src/rcs_sbr.py` `DEFAULT_DIV`)이고, σ 앵커 사슬은 λ/16 으로 돈다"
           "(`benchmark/rcs_anchor.py` `raw_sigma_az(div=16)`)."),

        md("## 검증 3층 — 무엇을 각각 재는가", "",
           table(["층", "과녁", "무엇을 재나", "결과"],
                 [["①", "해석 PO 구", "커널 구현",
                   "최대 λ/16 " + _n('s3_validation.layer1_analytic_po_convergence.kr_sweep_max_abs_db_vs_po_div16', POC, '{:.3f}')
                   + " · 생산 λ/12 " + _n('summary_div12.max_abs_db_vs_po', KRS, '{:.3f}', 'dB')],
                  ["②", "PEC 구 Mie 정확해", "PO 라는 모형",
                   "ka=1 에서 " + _n('s3_validation.layer2_pec_sphere_mie.po_minus_mie_at_ka1_db', POC, '{:.2f}', 'dB')
                   + " · 광학영역 산포 λ/16 "
                   + _n('s3_validation.layer2_pec_sphere_mie.kr_sweep_std_pct_vs_mie_kr_ge30_div16', POC, '{:.2f}')
                   + " · 생산 λ/12 "
                   + _n('summary_div12.std_sbr_over_mie_pct_kr_ge30', KRS, '{:.2f}', '%')],
                  ["③", "얇은 띠 2D EFIE MoM", "가는 특징",
                   "가장 가는 폭에서 TM "
                   + _n('s3_validation.layer3_thin_plate_2d_mom.po_minus_tm_at_0p15lam_db', POC, '{:.2f}')
                   + " · TE "
                   + _n('s3_validation.layer3_thin_plate_2d_mom.po_minus_te_at_0p15lam_db', POC, '{:+.2f}', 'dB')],
                  ["+", "PEC 이면각 닫힌형", "다중반사 위상",
                   "2-bounce 최대 "
                   + _n('s3_validation.layer4_dihedral_multibounce.max_abs_err_2bounce_db', POC, '{:.3f}', 'dB')],
                  ["+", "상반성 정리", "정리 위반 = 모형오차",
                   "기체 최악 "
                   + _n('s3_validation.layer5_reciprocity_selfcheck.drone_worst_violation_db', POC, '{:.2f}', 'dB')
                   + " (같은 검사를 인쇄한 선행 0편)"]])),

        md("## 이면각 — 오목부에서 오는 항", "",
           f"**이면각**은 두 평판이 90° 로 맞붙은 표준 형상이고, **PEC** 는 전기를 완벽히 통하는 "
           f"이상적 금속이다. 직각 이면각의 이등분선 입사는 σ = 8πa²b²/λ² 로 닫혀 있다. 2회 반사를 "
           f"켜고 변 길이 4점에서 그 값과 맞댔다(3.5 GHz, λ/12 격자).", "",
           table_from(f"{DFX}:d3_multibounce_phase.rows",
                      [("변 a [m]", "a_m"), ("해석해 [dBsm]", "exact_dbsm"),
                       ("1회 반사 [dBsm]", "sbr_1bounce_dbsm"),
                       ("2회 반사 [dBsm]", "sbr_2bounce_dbsm"), ("오차 [dB]", "err_2bounce_db")],
                      fmt={"a_m": "{:.2f}", "exact_dbsm": "{:.2f}",
                           "sbr_1bounce_dbsm": "{:.2f}", "sbr_2bounce_dbsm": "{:.2f}",
                           "err_2bounce_db": "{:+.3f}"}), "",
           f"1회/2회 열이 오목부에서 오는 항이 어디에 있는지 그대로 보여준다. 셋째 줄(a = 0.30 m)"
           f"의 1회 반사는 "
           f"{_n('s3_validation.layer4_dihedral_multibounce.a03_sbr_1bounce_dbsm', POC, '{:.1f}', 'dBsm')}"
           f" 로 무너진 널이고, 그 줄의 작은 오차는 그 우연한 상쇄 위에 앉아 있다 — 이 표에서 "
           f"인용할 값은 4점의 **최대** "
           f"{_n('d3_multibounce_phase.max_abs_err_db', DFX, '{:.3f}', 'dB')} 다.", "",
           f"같은 스크립트가 "
           f"매끄러운 기준체도 함께 잰다 — 구는 λ/16 격자에서 해석 PO 대비 "
           f"{_n('d3_multibounce_phase.sphere_and_plate.sphere_vs_po_db.sphere_lam/16_vs_po', DFX, '{:+.3f}', 'dB')}, "
           f"평판은 λ/10 격자에서 "
           f"{_n('d3_multibounce_phase.sphere_and_plate.plate_db.plate_lam/10', DFX, '{:+.3f}', 'dB')} 다."),

        md("## 이 눈금이 드론에 그대로 걸리는가", "",
           f"기체 7 × 밴드 3 = "
           f"{_n('electrical.n_airframe_band', DER, '{:.0f}', '조합')} 중 "
           f"{_n('electrical.n_below_po_1db', DER, '{:.0f}', '개')} 가 Mie 기준 1 dB 문턱 아래에 "
           f"놓이고, 그것이 실측 대상 {_n('electrical.kr_min_name', DER)} 다.", "",
           f"⚠ **이 kr 눈금은 매끄러운 구에서만 맞는 눈금이다** — 구는 몸 전체가 하나의 넓은 "
           f"곡면이지만 드론은 얇은 판과 가는 막대의 모음이라, PO 가 어긋나는 자리를 정하는 것은 "
           f"기체 전체 크기가 아니라 **부품 하나의 폭이 파장에 비해 얼마나 넓은가** 다. 그 세 번째 "
           f"눈금이 {ref('po-knee')} 다."),

        next_steps([
            ("평판·이면각 표준체로 같은 kr 스윕을 돌린다",
             "얇고 모서리 많은 표적에서의 PO 간극 문턱이 선다",
             "`benchmark/verify_sbr_defect_fixes.py` 의 두 닫힌형 재사용"),
            ("부품 폭 눈금으로 옮겨 우리 세 밴드가 어디에 서는지 읽는다",
             "어느 부품이 어느 밴드에서 무릎 아래인지가 확정된다",
             ref("po-knee", short=True)),
            ("상용 솔버 한 대와 같은 형상에서 교차검증한다",
             "구·이면각 밖의 형상에서 구현오차가 확정된다",
             "`OPENSOURCE.md` — RadarSimPy 교차검증 항목"),
        ]),
    ]


# =========================================================================== #
#  편 22 — po-knee
# =========================================================================== #
def report_22_po_knee():
    return [
        header(
            num=22,
            title="PO 유효 무릎을 부품 폭으로 옮기면 어느 부품이 어느 밴드에서 떨어지는지가 보인다",
            did="얇은 금속 판을 2D 적률법 참값과 PO 로 각각 내어 유효 무릎을 폭으로 정하고, 그 "
                "무릎을 한 기체의 부품 치수로 옮겨 주파수 축에 세웠다.",
            results=[
                f"무릎의 정의는 «두 편파 중 나쁜 쪽의 |PO−MoM| 이 1 dB 를 넘는 구간의 상단» "
                f"이고, 그 아래로 내려가려면 특징 폭이 "
                f"{_n('thin_plate.truth_2d_mom_fine_width_grid.knee_a_over_lam', LFA, '{:.3f}', 'λ')} "
                f"이상이어야 한다.",

                f"그 무릎을 부품 치수로 옮기면 동체 {_knee('body_81.51mm')} · 암뿌리 "
                f"{_knee('arm_root_45mm')} · 암끝 {_knee('arm_tip_30mm')} · 프로펠러 "
                f"{_knee('prop_blade_13.78mm')} · 모터 {_knee('motor_13.68mm')} · 캐노피 "
                f"{_knee('canopy_6.22mm')} · PCB {_knee('pcb_2.99mm')} 에서 통과한다.",

                f"우리 생산 3 밴드는 전부 이 문턱 아래에 부품을 남긴다 — 무릎 위로 올라선 특징이 "
                f"LTE {_n('bands_ghz.LTE', DER, '{:.3f}', 'GHz')} 에서는 0 개(동체 무릎이 "
                f"{_knee('body_81.51mm')})이고, 5G {_n('bands_ghz.5G', DER, '{:.1f}', 'GHz')} "
                f"에서는 동체 하나, WiFi {_n('bands_ghz.WiFi', DER, '{:.2f}', 'GHz')} 에서는 "
                f"동체와 암뿌리({_knee('arm_root_45mm')}) 둘이다.",

                f"절대 σ 에는 격자 불확도도 붙는다 — λ/16 서브셀 디더 산포 "
                f"{_n('s2_our_kernel.grid_dither.dither_spread_div16_db', POC, '{:.2f}', 'dB')} 다.",

                f"저대역 판정 라벨 `{_n('s4_limits.adversarial_verdict_verbatim.attacked_verdict_label', POC)}` "
                f"에 대한 적대검증 판정은 "
                f"`{_n('s4_limits.adversarial_verdict_verbatim.adversarial_verdict', POC)}` 다 — "
                f"PO 한계는 **부호만** 확인됐고 크기 귀속은 열려 있다.",
            ],
            method=[
                ("참값", "얇은 금속 판을 2D 적률법(MoM — 맥스웰 방정식을 수치로 푸는 방법)으로 "
                      "낸다. 두 편파를 따로 낸다"),
                ("편파란", "전파의 전기장이 흔들리는 방향이다 — 판의 긴 축과 나란한 쪽을 TM, "
                       "그에 수직인 쪽을 TE 라 부른다"),
                ("무릎의 정의", "두 편파 중 **나쁜 쪽**의 |PO−MoM| 이 1 dB 를 넘는 구간의 상단. "
                            "나쁜 쪽을 쓰는 것이 보수적이다"),
                ("주파수로 옮기기", "Phantom 3 급 한 기체의 부품 치수를 넣어 부품마다 몇 GHz 에서 "
                              "무릎을 넘는지 계산한다"),
            ],
            repro=_repro(["PYTHONPATH=src python benchmark/lowfreq_anchor.py"],
                         [LFA, LFK, POC, DER],
                         "약 15분 (GPU 0장 — 2D MoM 은 CPU 다)",
                         "치수는 Phantom 3 를 사진 실측으로 다시 짓기 전 스윕에서 인용한 값이다"),
        ),

        md("## 무릎을 무엇으로 정했나", "",
           f"얇은 금속 판을 참값(2D 적률법 MoM)과 PO 로 각각 내고 맞대면, 두 편파 중 나쁜 쪽의 "
           f"차이가 1 dB 아래로 내려가는 문턱이 **폭 ≥ "
           f"{_n('thin_plate.truth_2d_mom_fine_width_grid.knee_a_over_lam', LFA, '{:.3f}', 'λ')}** "
           f"다. 정의는 «max(|PO−MoM TM|,|PO−MoM TE|) 가 1 dB 를 넘는 구간의 상단» "
           f"⟨{POC} : s4_limits.po_validity_knee_rule⟩ 이다.", "",
           f"⭐ 이 눈금은 {ref('kernel-vs-reference', short=True)} 의 두 눈금과 **다른 것을 "
           f"잰다.** (커널 − 해석 PO) 는 우리 구현이 PO 를 제대로 계산하는지의 눈금이고, 폭 "
           f"{_n('thin_plate.per_width.0.15.a_lam', LFA, '{:.2f}', 'λ')} 인 얇은 판에서도 격자를 "
           f"조이면 "
           f"{_n('thin_plate.per_width.0.15.max_abs_vs_po_two_finest_db', LFA, '{:.3f}', 'dB')} 까지 "
           f"수렴한다. (PO − 참값) 은 PO 라는 모델 자체가 참값과 떨어진 거리이고, 이 편이 크기를 "
           f"준 것이 그쪽이다."),

        md("## 부품마다 몇 GHz 에서 무릎을 넘나", "",
           table(["부품", "폭", "무릎 주파수"],
                 [[name, _knee_width(key), _knee(key)] for name, key in _KNEE_ROWS]), "",
           f"⚠ 이 목록은 **기체 하나**의 치수이고 7기체 공통이 아니다 — 크기 폭 "
           f"{_n('mesh.span_ratio', DER, '{:.2f}', '배')} 안에서 S1000+ 처럼 큰 기체는 이 문턱이 "
           f"그만큼 낮은 주파수로, Mini 급은 그만큼 높은 주파수로 옮겨간다."),

        md("## 우리 세 밴드는 어디에 서 있나", "",
           f"⚠⚠ **우리 생산 3 밴드(LTE {_n('bands_ghz.LTE', DER, '{:.3f}')} · 5G "
           f"{_n('bands_ghz.5G', DER, '{:.1f}')} · WiFi "
           f"{_n('bands_ghz.WiFi', DER, '{:.2f}', 'GHz')})는 전부 이 문턱 아래에 부품을 남긴다** "
           f"— LTE 에서는 동체까지 아래이고, 5G 에서는 동체 하나가 무릎 위, WiFi 에서는 동체와 "
           f"암뿌리({_knee('arm_root_45mm')}) 둘이 무릎 위다. 가장 높은 밴드에서도 암끝·프로펠러·"
           f"모터·캐노피·PCB 는 아래에 있다.", "",
           f"문헌 측정의 위쪽 끝("
           f"{_n('slope.das_published.band[1]', P3V2, '{:.1f}', 'GHz')})까지 **줄곧** 문턱 아래에 "
           f"남는 부품은 캐노피와 PCB 둘뿐이다. 프로펠러와 모터는 그 끝에 닿기 전인 "
           f"{_knee('prop_blade_13.78mm')} · {_knee('motor_13.68mm')} 에서 문턱을 넘는다 — 문헌 "
           f"대역의 맨 위 토막에서만 넘는 셈이다.", "",
           f"그래서 이 저장소는 σ 의 절대 크기 대신 **각도 구조와 밴드 간 상대 순위**를 주장한다. "
           f"절대 레벨은 {ref('calibration-sphere', short=True)} 의 교정구가 측정으로 앵커한다."),

        md("## 부호는 한 방향을 가리킨다", "",
           f"지배채널(TM) 기준 PO 는 얇은 특징을 **과소평가**한다 — 가장 가는 시험 폭에서 TM 기준 "
           f"{_n('s3_validation.layer3_thin_plate_2d_mom.po_minus_tm_at_0p15lam_db', POC, '{:.2f}', 'dB')}"
           f"(음수 = 우리가 낮다), TE 기준 "
           f"{_n('s3_validation.layer3_thin_plate_2d_mom.po_minus_te_at_0p15lam_db', POC, '{:+.2f}', 'dB')} "
           f"다. 참값 자체가 편파로 "
           f"{_n('s3_validation.layer3_thin_plate_2d_mom.tm_minus_te_at_0p15lam_db', POC, '{:.2f}', 'dB')} "
           f"갈린다.", "",
           f"따라서 우리 저주파 σ 는 낮게 나와 있을 개연성이 크고, 그 방향이라면 검출 성능 "
           f"산출물은 **보수적(비관적)** 쪽으로 틀렸다. 스칼라 PO 는 편파를 **못** 가르므로 TE "
           f"채널 기준으로는 부호가 반대다 — 방향을 못 박으려면 편파 있는 커널이 필요하다 "
           f"⟨{POC} : s4_limits.our_production_bands_vs_knee.sign_of_the_error⟩."),

        md("## 이 결과로 말할 수 없는 것 셋", "",
           f"· ✗ 「저주파 σ 가 틀렸다」 → 맞는 말은 **불확도가 지금 선언된 것보다 크고 그 크기를 "
           f"아직 정하는 중이다** ⟨{LFK} : q5_blast_radius.what_must_not_be_said[0]⟩.", "",
           f"· ✗ 「고대역은 검증됐다」 → 캐노피·PCB 는 문헌 측정 대역의 위쪽 끝까지 문턱 아래에 "
           f"머물고, 프로펠러·모터도 그 끝 바로 아래에서야 문턱을 넘는다 "
           f"⟨{LFK} : q5_blast_radius.what_must_not_be_said[1]⟩.", "",
           f"· ✗ 「격자를 더 촘촘히 하면 σ 가 고쳐진다」 → **정반대다.** 격자를 조이면 저대역 "
           f"기울기가 오히려 더 가팔라진다 — 이것이 이 라운드에서 가장 확실한 결과다 "
           f"⟨{LFK} : q5_blast_radius.sampling_blast_radius_actual.direction⟩.", "",
           f"절대 σ 에는 격자 불확도도 함께 붙는다 — λ/16 서브셀 디더 산포 "
           f"{_n('s2_our_kernel.grid_dither.dither_spread_div16_db', POC, '{:.2f}', 'dB')} 다. "
           f"저대역 판정 라벨 "
           f"`{_n('s4_limits.adversarial_verdict_verbatim.attacked_verdict_label', POC)}` 의 "
           f"적대검증 판정은 "
           f"`{_n('s4_limits.adversarial_verdict_verbatim.adversarial_verdict', POC)}` 이고, "
           f"살아남은 것은 표본화 배제뿐이다."),

        next_steps([
            ("편파를 가르는 커널로 넓히고 VV/HH 를 따로 낸다",
             "부호가 못 박히고 저대역 불확도의 크기가 확정된다",
             "`src/materials.py:171` 편파 분해 → " + ref("sigma-checklist", short=True)),
            ("생산 σ 를 `ptd=True` 로 다시 낸다",
             "모서리 항이 밴드 기울기를 얼마나 옮기는지가 수치로 남는다",
             f"`benchmark/rcs_anchor.py --ptd` · 비용 "
             f"{_n('verdict.cost_increase_pct', PTD, '{:.1f}', '%')}"),
            ("7기체 각각의 부품 치수로 무릎 표를 다시 낸다",
             "기체마다 어느 밴드에서 어느 부품이 떨어지는지가 전수로 확정된다",
             "`benchmark/lowfreq_anchor.py` → 기체 루프 추가"),
            ("교정구를 표적과 같은 자리에서 함께 잰다",
             "지금 우리 PO 출력인 절대 레벨이 처음으로 측정에 앵커된다",
             ref("calibration-sphere", short=True)),
        ]),
    ]


# =========================================================================== #
#  편 23 — kernel-open-items
# =========================================================================== #
def report_23_kernel_open_items():
    return [
        header(
            num=23,
            title="커널이 아직 못 하는 것은 편파 분리·PTD·재테셀레이션·다중반사 Γ(θ) 넷이고, "
                  "각각의 크기를 적었다",
            did="커널의 열린 항목을 하나씩 세고 각 항목이 σ 를 얼마나 움직이는지를 dB 로 함께 "
                "적었다.",
            results=[
                f"편파 — 면적분이 스칼라다. |Γ(θ)| 는 TE·TM 전력평균이라 채널 분리가 따로 "
                f"없고, 가장 가는 시험 폭에서 참값이 TM−TE "
                f"{_n('s3_validation.layer3_thin_plate_2d_mom.tm_minus_te_at_0p15lam_db', POC, '{:.2f}', 'dB')} "
                f"로 갈린다.",

                f"모서리 프린지(PTD) — 배선은 있고 생산 경로는 `ptd=False` 다. 켜면 TE 가 "
                f"{_n('s3_validation.layer3_thin_plate_2d_mom.po_minus_te_at_0p15lam_db', POC, '{:+.2f}')} → "
                f"{_n('s3_validation.layer3_thin_plate_2d_mom.po_ptd_minus_te_at_0p15lam_db', POC, '{:+.2f}', 'dB')} "
                f"로 벌어지고, 비용은 "
                f"{_n('verdict.cost_increase_pct', PTD, '{:+.1f}', '%')} 다.",

                f"테셀레이션 — 입력 메쉬를 어떻게 쪼갰는가에 σ 가 따라간다. 같은 드론 메쉬를 "
                f"삼각형 {_n('levels[0].n_tri', FCNT, '{:,.0f}')}→"
                f"{_n('levels[5].n_tri', FCNT, '{:,.0f}', '개')} 로 쌓아 재면 삼각형 수 10 배당 "
                f"B(SBR+PO) {_n('slopes.sbr', FCNT, '{:.2f}')} · P(순수 PO) "
                f"{_n('slopes.po', FCNT, '{:.2f}', 'dB/decade')} 다. 메쉬 사다리는 앵커 물체 두 "
                f"점에서 돌렸다.",

                f"2회 이상 다중반사 — 생산 σ 는 1-bounce 다. 변 "
                f"{_n('d3_multibounce_phase.rows[0].a_m', DFX, '{:.2f}', 'm')} 이면각에서 "
                f"1-bounce {_n('d3_multibounce_phase.rows[0].sbr_1bounce_dbsm', DFX, '{:.2f}')} "
                f"↔ 2-bounce "
                f"{_n('d3_multibounce_phase.rows[0].sbr_2bounce_dbsm', DFX, '{:.2f}', 'dBsm')} 다.",

                f"Γ(θ) 각도 모양 — 1회 반사 네 경로(σ 격자·복소장·바이스태틱 둘)가 같은 함수를 "
                f"기본으로 곱하고 순수 PO 는 호출 옵트인이며 ⟨{APO} : _meta.switch⟩, 다중반사 "
                f"경로는 아직 수직입사 값 그대로다. 켠 경로에서 프롭 채널이 "
                f"{_n('propeller_channel_el_-15_3p5GHz.matrice4e.level_delta_db', AGI, '{:+.2f}')} ~ "
                f"{_n('propeller_channel_el_-15_3p5GHz.mini5pro.level_delta_db', AGI, '{:+.2f}', 'dB')} "
                f"움직였다.",
            ],
            method=[
                ("무엇을 세나", "커널이 계산에 넣지 않는 항과, 넣되 생산 경로에서 꺼 둔 항을 "
                            "따로 센다 — 둘은 성질이 다르다"),
                ("크기를 어떻게 붙이나", "항마다 그 항이 σ 를 움직이는 양을 이미 잰 대조에서 "
                                 "끌어온다. 크기를 못 붙인 항은 그렇게 적는다"),
                ("왜 표인가", "열린 항목을 산문으로 쓰면 사과가 되고 표로 쓰면 예산이 된다 — "
                          "다음 라운드가 집어 갈 수 있는 형태다"),
            ],
            repro=_repro([], [POC, PTD, EVD],
                         "약 1분 (GPU 0장 — 이미 잰 값을 모은 표다)",
                         "각 행의 크기는 그 항을 실제로 켜거나 끄고 잰 대조에서 왔다"),
        ),

        md("## 열린 항목과 그 크기", "",
           "커널이 계산에 넣지 않는 항과, 넣되 생산 경로에서 꺼 둔 항을 한 표에 센다 — "
           "항마다 크기는 그 항을 실제로 켜거나 끄고 잰 대조에서 왔다."),

        md(table(["열린 항목", "현재 상태", "크기"],
                 [["편파", "면적분이 스칼라다 — |Γ(θ)| 는 TE·TM 전력평균이라 채널 분리가 "
                          "따로 없다",
                   "가장 가는 시험 폭에서 참값이 TM−TE "
                   + _n('s3_validation.layer3_thin_plate_2d_mom.tm_minus_te_at_0p15lam_db', POC, '{:.2f}', 'dB')
                   + " 로 갈린다"],
                  ["Γ(θ) 각도 모양의 근사", "벌크 각도 모양을 얇은 판 근사로 곱한다 — "
                                        "수직입사에서 보정값과 동일하다 "
                                        f"⟨{AGI} : _meta.design⟩",
                   "프롭 채널 레벨 "
                   + _n('propeller_channel_el_-15_3p5GHz.matrice4e.level_delta_db', AGI, '{:+.2f}')
                   + " ~ "
                   + _n('propeller_channel_el_-15_3p5GHz.mini5pro.level_delta_db', AGI, '{:+.2f}', 'dB')
                   + " · 기체 3대의 전체 드론 σ 는 방위평균 "
                   + _n(f'{_AGS_MEAN_LO}.delta_db', AGS, '{:+.3f}')
                   + " ~ " + _n(f'{_AGS_MEAN_HI}.delta_db', AGS, '{:+.3f}', 'dB')
                   + " · 칸별 최대 "
                   + _n(f'{_AGS_CELL_LO}.cell_max_abs_db', AGS, '{:.2f}')
                   + " ~ " + _n(f'{_AGS_CELL_HI}.cell_max_abs_db', AGS, '{:.2f}', 'dB')],
                  ["Γ(θ) 다중반사 경로", "1회 반사 네 경로는 기본 켬이고 순수 PO 는 호출 "
                                     "옵트인이다. 남은 자리는 `rcs_sbr(max_bounce≥2)` 로, "
                                     "재질 키를 받고도 각도 모양을 곱하지 않는다 "
                                     f"⟨{ARK} : q3_angle_gamma_wiring.UNWIRED_paths."
                                     f"rcs_sbr (max_bounce 경로)⟩",
                   "그 경로로 낸 2회 반사 σ 는 왼쪽 위 행의 크기만큼 1회 반사 경로와 갈린다"],
                  ["모서리 프린지(PTD)", "배선은 있고 생산 경로는 `ptd=False` 다",
                   "켜면 TE 가 "
                   + _n('s3_validation.layer3_thin_plate_2d_mom.po_minus_te_at_0p15lam_db', POC, '{:+.2f}')
                   + " → "
                   + _n('s3_validation.layer3_thin_plate_2d_mom.po_ptd_minus_te_at_0p15lam_db', POC, '{:+.2f}', 'dB')
                   + " 로 벌어진다"],
                  ["2회 이상 다중반사", "생산 σ 는 1-bounce 다 — 오목부의 항이 통째로 빠진다",
                   "변 " + _n('d3_multibounce_phase.rows[0].a_m', DFX, '{:.2f}', 'm')
                   + " 이면각에서 1-bounce "
                   + _n('d3_multibounce_phase.rows[0].sbr_1bounce_dbsm', DFX, '{:.2f}')
                   + " ↔ 2-bounce "
                   + _n('d3_multibounce_phase.rows[0].sbr_2bounce_dbsm', DFX, '{:.2f}', 'dBsm')
                   + " (**절 4** 표의 a = 0.30 m 줄은 1회 반사가 무너진 널이라 크기 인용에 "
                     "쓰지 않는다)"],
                  ["크리핑파·표면파", "우리 커널과 Sionna 가 같은 자리에 선다 — GO/UTD 계열 "
                                "고주파 근사의 바깥이다",
                   "매끄러운 볼록체 그림자 경계를 감아 도는 성분"],
                  ["전방산란 β→180°", "조명 게이트와 수신 게이트가 상호배타라 σ ≡ 0 이 된다",
                   "주장 창을 후방~중간 바이스태틱각으로 못박는다"],
                  ["생산 경로의 참값 대조", "참값 앵커는 penetrate=False · |Γ|=1 · 볼록이다",
                   "생산은 penetrate=True · 재질 Γ · 자기가림 · 1-bounce 다"],
                  ["테셀레이션 축", "커널의 스위치가 아니라 **입력 메쉬**의 축이다 — 메쉬 "
                                "사다리는 앵커 물체 두 점에서 돌렸다",
                   "삼각형 수 10 배당 B(SBR+PO) " + _n('slopes.sbr', FCNT, '{:.2f}')
                   + " · P(순수 PO) " + _n('slopes.po', FCNT, '{:.2f}', 'dB/decade')
                   + " · 형상이 보존된 수준만 쓰면 " + _n('slopes.sbr_shapeok', FCNT, '{:.2f}')
                   + " · " + _n('slopes.po_shapeok', FCNT, '{:.2f}', 'dB/decade')],
                  ["회전 프로펠러 도플러", "Sionna 의 Paths.doppler 는 객체당 강체 속도 1벡터다",
                   "부품별 위상은 우리 커널의 복소 E 에서 온다"]])),

        md("## 이 표를 읽는 법", "",
           f"편파 · Γ(θ) 두 항 · PTD · 2회 이상 다중반사 다섯 줄은 **커널 자신의 축**이다. **편파**는 "
           f"커널이 애초에 안 가르는 축이라 크기가 참값 쪽에서 오고, **Γ(θ)** 는 1회 반사 "
           f"경로와 다중반사 경로가 갈라져 있다 — 그 항의 근거는 교과서 프레넬과 θ=0 비트동일 "
           f"둘뿐이고, 각도 경로를 밟는 과녁은 아직 세우지 않았다(다음 단계 표). **PTD** 는 "
           f"배선이 끝나 있고 스위치만 꺼 둔 항이라 켜면 "
           f"바로 값이 나온다 — 비용 "
           f"{_n('verdict.cost_increase_pct', PTD, '{:+.1f}', '%')} 가 그 값이다. **테셀레이션**은 "
           f"커널 밖 **입력 메쉬**의 축이라 크기를 우리 두 팔(B·P)의 기울기로 적었고, 그 축을 "
           f"정면으로 다룬 것이 {ref_part(6)} 다.", "",
           f"전방산란 · 크리핑파 · 참값 대조 · 회전 프로펠러 도플러 넷은 **주장 창을 좁히는 "
           f"방식**으로 이미 처리돼 있다 — 전방산란은 창 밖으로 "
           f"내보냈고(그 창은 {ref('bistatic-exit', short=True)} 가 β ≤ 45° 로 못 박았다), "
           f"크리핑파는 고주파 근사 계열 전체가 못 내는 항이라 Sionna 도 같은 자리에 선다. "
           f"회전 프로펠러 도플러는 {ref_part(7)} 가 슬로타임 재추적으로 우회한다."),

        next_steps([
            ("편파 분해를 커널에 넣고 VV/HH 를 따로 낸다",
             "표의 첫 행이 크기에서 값으로 바뀐다",
             "`src/materials.py:171` → " + ref("sigma-checklist", short=True)),
            ("Γ(θ) 를 다중반사 경로에 배선하고 오목부 기체에서 다시 낸다",
             "2회 반사 σ 가 1회 반사 경로와 같은 각도 물리 위에 선다",
             "`src/rcs_sbr.py` `rcs_sbr(max_bounce≥2)`"),
            ("각도 경로를 실제로 밟는 과녁을 하나 세운다 — 유전체 평판 각도 스윕 대 MoM·프레넬",
             "Γ(θ) 의 외부 눈금이 처음 생긴다 — 지금 과녁은 전부 PEC 라 각도 경로를 안 밟는다",
             f"⟨{ARK} : open_items_ranked[2].item⟩"),
            ("생산 σ 를 `ptd=True` 로 다시 낸다",
             "모서리 항이 밴드 기울기를 얼마나 옮기는지가 수치로 남는다",
             "`benchmark/rcs_anchor.py --ptd` → `outputs/rcs_anchor_ptd.json`"),
            ("테셀레이션 축을 앵커 물체 밖 형상으로 넓힌다",
             "메쉬 쪼개기가 σ 를 얼마나 부풀리는지가 드론 형상에서 확정된다",
             ref("ladder-answer", short=True)),
            ("2회 반사를 생산 경로에서 켜고 비용과 이득을 함께 잰다",
             "오목부 있는 기체에서 1-bounce 가정의 대가가 확정된다",
             "`src/rcs_sbr.py` `rcs_sbr_multistatic()`"),
            ("회전 블레이드 마이크로도플러를 이 커널 위에서 검증한다",
             "미세도플러 서명을 이 커널의 산출물로 인용할 수 있게 된다",
             ref("md-slowtime", short=True)),
        ]),
    ]


# =========================================================================== #
REPORTS = [
    ("kernel-what", report_18_kernel_what),
    ("kernel-vs-stock", report_19_kernel_vs_stock),
    ("bistatic-exit", report_20_bistatic_exit),
    ("kernel-vs-reference", report_21_kernel_vs_reference),
    ("po-knee", report_22_po_knee),
    ("kernel-open-items", report_23_kernel_open_items),
]


def main() -> int:
    print(f"── 부 4 「산란 커널」 — 편 {len(REPORTS)}개 ──")
    bad = 0
    for anchor, fn in REPORTS:
        rep = build_notebook(nb_path(anchor), fn(), strict=True, quiet=True)
        index_shard(anchor, md_cells=rep["md_cells"], figures=rep["figures"],
                    provenance_tags=rep["provenance_tags"],
                    negatives=rep["n_negatives"], builder=os.path.basename(__file__))
        mark = "✅" if rep["ok"] else "⛔"
        print(f"  {mark} {rep['path']:46s} md {rep['md_cells']:2d}/25 · "
              f"그림 {rep['figures']}/8 · 출처 {rep['provenance_tags']:3d} · "
              f"부정문 {rep['n_negatives']}/3 · 완충어 {rep['n_hedges']}/0")
        bad += 0 if rep["ok"] else 1
    print(f"── {len(REPORTS) - bad}/{len(REPORTS)} 통과 ──")
    return bad


if __name__ == "__main__":
    sys.exit(main())
