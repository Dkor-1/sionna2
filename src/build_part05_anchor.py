# -*- coding: utf-8 -*-
"""
build_part05_anchor.py — 부 5 「앵커와 검증」 → 편 24~29
==========================================================================================
부 5 가 답하는 질문 하나
    **σ 의 어느 축을 측정에서 받고, 그 판정이 함대에서 버티나.**

편 하나 = 중심 메시지 하나 (제목이 곧 그 편의 결론 문장이다)

    24 anchor-mode         σ = A(f)·B₁·B₂ 에서 A(f) 의 기울기만 측정에서 받고,
                           레벨과 각패턴은 우리 PO 출력이다
    25 anchor-ledger       앵커가 통제한 항목과 남은 항목의 크기를 기체별 원장으로 적었다
    26 blind-p3            Phantom 3 를 문헌값을 보지 않고 내고 봉인을 풀었다
    27 box-sphere-control  메쉬가 사는 축은 절대 크기가 아니라 각도 구조다
    28 fleet-prereg        같은 잣대를 네 기체로 넓히면 판정이 NOT_VALIDATED 로 갈린다
    29 sigma-robustness    공통모드 σ 오차는 파형 순위를 안 건드리고, 차분 오차가 뒤집는다

어디서 왔나 (재구성 전 → 후)
    `report02_target.ipynb` c14~c22
    계획: `outputs/restruct_exec_plan.json : reports[no in 24..29]`

실행
    cd /home/yunjung/workspace/sionna2
    PYTHONPATH=src ~/.venvs/py312/bin/python src/build_part05_anchor.py

⚠ GPU 도 Sionna 실행도 필요 없다 — 서술 재배치다.
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (_HERE, os.path.join(_ROOT, "benchmark")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from report_registry import index_shard, nb_path, ref, ref_part           # noqa: E402
from report_style import (build_notebook, caption, header, md,            # noqa: E402
                          next_steps, num, table, table_from)

# --------------------------------------------------------------------------- #
#  근거 파일
# --------------------------------------------------------------------------- #
DER = "outputs/report02_derived.json"        # 02 파생 원장(밴드 기울기·앵커·σ 민감도)
ANC = "outputs/rcs_anchor.json"              # 문헌 적합 — 측정 기울기
SIG = "outputs/sigma_anchor.json"            # 재보정 모드 · 비교가능성 · 미통제 항목
P3V1 = "outputs/p3_validation.json"          # 눈감기 대조 (v1 메쉬)
P3V2 = "outputs/p3_validation_v2.json"       # 상자·구 대조군 (v2 메쉬)
P3O = "outputs/p3_ours.json"                 # 눈감기 산출 원본
DFV = "outputs/das_fleet_validation.json"    # 함대 사전등록 채점
DFP = "outputs/das_fleet_prereg.json"        # 봉인한 합격규칙
DFA = "outputs/das_fleet_attack.json"        # 함대 적대검증
LFA = "outputs/lowfreq_anchor.json"          # 얇은 판 참값 — 편파 낙차
LFK = "outputs/lowfreq_attack.json"          # 저대역 적대검증
SS = "outputs/sigma_sensitivity.json"        # σ 오차 → 순위
MFX = "outputs/meshfix_applied.json"         # 형상 정정이 옮긴 것
MFX_ATK = "outputs/meshfix_attack.json"      # 형상 정정 적대검증
AGI = "outputs/angle_gamma_impact.json"      # Γ(θ) 각도 모양 — 커널 세대의 셋째 축
VBF = "outputs/verify_bistatic_field.json"   # 다중정적 σ 경로에 Γ(θ) 가 들어온 시점·일치도
S2R = "outputs/s2r_assets_verify.json"       # 재생성 대조

FIG = "../outputs/figures"


def _n(key: str, src: str, fmt: str | None = None, unit: str = "") -> str:
    return num(None, (src, key), fmt, unit)


def _fig(no: int, stem: str, question: str) -> list[str]:
    return [f"![{stem}]({FIG}/{stem}.png)", "", caption(no, question)]


def _repro(cmd: list[str], out: list[str], runtime: str, note: str = "") -> dict:
    d = dict(cmd=cmd + ["PYTHONPATH=src python src/build_part05_anchor.py"],
             out=out, runtime=runtime)
    if note:
        d["note"] = note
    return d


_DERIVE = "PYTHONPATH=src python src/make_report02_target.py --derive-only"
_MESHFIX = f"{_n('_meta.date', MFX)} 형상 정정"
_GAMMA_AXIS = (f"{_n('_meta.generated', AGI)} Γ(θ) 각도 모양(기본 켬) 이전 커널의 산출"
               f"이기도 하다 — 전체 드론 σ 이동 "
               f"{_n('whole_drone_sigma_az24_el_-15.mini5pro.delta_db', AGI, '{:+.2f}')} ~ "
               f"{_n('whole_drone_sigma_az24_el_-15.matrice4e.delta_db', AGI, '{:+.2f}', 'dB')}")


# =========================================================================== #
#  편 24 — anchor-mode
# =========================================================================== #
def report_24_anchor_mode():
    return [
        header(
            num=24,
            title="σ = A(f)·B₁·B₂ 에서 A(f) 의 기울기만 측정에서 받고, 레벨과 각패턴은 우리 PO "
                  "출력이다",
            did="게재된 표준트랙 논문의 분해를 그대로 쓰고, 세 인자 중 주파수 기울기 하나만 공개 "
                "측정에 정렬했다.",
            results=[
                f"기하에서 나온 우리 밴드 기울기는 "
                f"{_n('band_slope.ours_min', DER, '{:.3f}')}"
                f"({_n('band_slope.ours_min_drone', DER)})~"
                f"{_n('band_slope.ours_max', DER, '{:.3f}', 'dB/GHz')}"
                f"({_n('band_slope.ours_max_drone', DER)}) 이고, 측정은 "
                f"{_n('literature.mu_eps.das_phantom3_mono.mu_a', ANC, '{:.3f}')}(Das) 와 "
                f"{_n('literature.mu_eps.yuan_phantom3_azplane.mu_a', ANC, '{:.3f}', 'dB/GHz')}(Yuan) 다.",

                f"생산 기준은 "
                f"`{_n('anchor_modes.production_mode', DER)}` 이고, 밴드별로 옮기는 양은 "
                f"{_n('anchor.correction_max_db', DER, '{:+.2f}')}"
                f"({_n('anchor.correction_max_drone', DER)} @ "
                f"{_n('anchor.correction_max_band', DER)}) ~ "
                f"{_n('anchor.correction_min_db', DER, '{:+.2f}', 'dB')}"
                f"({_n('anchor.correction_min_drone', DER)} @ "
                f"{_n('anchor.correction_min_band', DER)}) 다.",

                f"정렬 후 "
                f"{_n('anchor_modes.n_airframes', DER, '{:.0f}', '기종')} 기울기가 모두 "
                f"{_n('anchor.slope_after_db_per_ghz', DER, '{:.3f}', 'dB/GHz')} 위에 서고, 기종 간 "
                f"산포는 "
                f"{_n('anchor.slope_after_spread_db_per_ghz', DER, '{:.1e}', 'dB/GHz')} 다.",

                f"레벨이동 절대 최대는 "
                f"{_n('anchor_modes.level_shift_abs_max_db', DER, '{:.2f}', 'dB')}, 재보정 후 정규화 "
                f"각패턴 변화는 "
                f"{_n('anchor.shape_invariance_max_abs_db', DER, '{:.1e}', 'dB')} 다 — 주파수 눈금만 "
                f"측정에서 오고 레벨과 모양은 그대로다.",

                f"레벨까지 맞추려면 크기전이 법칙을 하나 골라야 하고, 그 선택 하나가 기체당 최대 "
                f"{_n('anchor_modes.size_law_spread_max_db', DER, '{:.2f}', 'dB')} 를 정한다.",
            ],
            method=[
                ("분해", "σ = A(f)·B₁(φ,θ)·B₂ — 게재된 표준트랙 논문의 분해를 그대로 쓴다"
                      "(Zhang, IEEE JSAC 44:702, 2026 — 측정 적합 모델)"),
                ("무엇을 받나", "A(f) 의 **기울기만** 측정에서 받는다. A(f) 의 레벨과 B₁ 은 우리 "
                          "PO 출력이다"),
                ("왜 기울기만", "레벨까지 맞추려면 크기전이 법칙을 하나 골라야 하고, 측정이 그 "
                           "대가 없이 제약하는 양은 기울기뿐이다"),
                ("모드 구현", "`src/sigma_anchor.py` 가 재보정 모드 셋을 제공한다 — 생산은 "
                          "`slope_only` 다"),
            ],
            repro=_repro([_DERIVE, "PYTHONPATH=src python benchmark/rcs_anchor.py"],
                         [DER, ANC, SIG],
                         "약 3분 (GPU 0장 — 이미 낸 σ 격자에 적합을 다시 건다)",
                         "PO 면적분은 f² 로 커지는 정반사항을 담는다 — 그 기울기를 측정과 맞춘다"),
        ),

        md("## 세 인자로 갈라 놓고 하나만 건드린다", "",
           "게재된 표준트랙 논문의 분해를 그대로 쓴다(Zhang, IEEE JSAC 44:702, 2026 — 측정 적합 "
           "모델): **σ = A(f)·B₁(φ,θ)·B₂**. A(f) 는 주파수 의존성, B₁ 은 자세에 따른 모양, "
           "B₂ 는 자세 요동의 분포족이다.", "",
           "**A(f) 의 기울기는 측정에서, A(f) 의 레벨과 B₁ 은 우리 계산에서 온다.** PO 면적분은 "
           "f² 로 커지는 정반사항을 담으므로 기울기가 기하에서 나오고, 그 하나를 측정에 맞춘다."),

        md("## 우리 기울기와 측정 기울기", "",
           f"기하에서 나온 우리 밴드 기울기는 "
           f"{_n('band_slope.ours_min', DER, '{:.3f}')}"
           f"({_n('band_slope.ours_min_drone', DER)})~"
           f"{_n('band_slope.ours_max', DER, '{:.3f}', 'dB/GHz')}"
           f"({_n('band_slope.ours_max_drone', DER)}) 이고, 측정은 "
           f"{_n('literature.mu_eps.das_phantom3_mono.mu_a', ANC, '{:.3f}')}(Das, IEEE WCL 2026) 와 "
           f"{_n('literature.mu_eps.yuan_phantom3_azplane.mu_a', ANC, '{:.3f}', 'dB/GHz')}"
           f"(Yuan, EuCAP 2025) 다.", "",
           f"⚠ **두 수는 창이 다르다** — 우리 값은 생산 세 밴드"
           f"({_n('bands_ghz.LTE', DER, '{:.3f}')}~"
           f"{_n('bands_ghz.WiFi', DER, '{:.2f}', 'GHz')})에서 잰 기울기이고 측정 두 값은 "
           f"{_n('slope.das_published.band[0]', P3V2, '{:.1f}')}~"
           f"{_n('slope.das_published.band[1]', P3V2, '{:.1f}', 'GHz')} 전대역 적합이다. 같은 "
           f"기체를 같은 커널로 돌려도 창을 바꾸면 기울기가 달라진다 — 우리 Phantom 3 v2 메쉬에서 "
           f"저대역 창 {_n('slope.subband.ours.1.8-6.0 GHz.a', P3V2, '{:.3f}')} 대 전대역 "
           f"{_n('slope.ours_el0_full_band.a', P3V2, '{:.3f}', 'dB/GHz')} 다."),

        md("## 앵커는 각 기체의 기울기를 어디로 옮기나", "",
           *_fig(1, "report02_f6_band_slope",
                 "측정 앵커는 각 기체의 밴드 기울기를 어디로 옮기는가?")),

        md("## 모드 선택 — 무엇을 옮기고 무엇을 대가로 내는가", "",
           table_from(f"{DER}:anchor_modes.rows",
                      [("모드", "mode"), ("무엇을 옮기나", "moves"),
                       ("평균 레벨이동 [dB]", "mean_shift_range_db"), ("대가", "cost")]), "",
           f"생산 기준은 `{_n('anchor_modes.production_mode', DER)}` 이고, 밴드별로 옮기는 양은 "
           f"{_n('anchor.correction_max_db', DER, '{:+.2f}')}"
           f"({_n('anchor.correction_max_drone', DER)} @ "
           f"{_n('anchor.correction_max_band', DER)}) ~ "
           f"{_n('anchor.correction_min_db', DER, '{:+.2f}', 'dB')}"
           f"({_n('anchor.correction_min_drone', DER)} @ "
           f"{_n('anchor.correction_min_band', DER)}) 다. 레벨이동 열은 기체 "
           f"{_n('anchor_modes.n_airframes', DER, '{:.0f}', '종')} 의 세 밴드 평균 Δ 다."),

        md("## 왜 기울기만 받나", "",
           f"레벨까지 앵커에 맞추려면 크기전이 법칙을 하나 골라야 하고, 그 선택이 기체에 따라 최대 "
           f"{_n('anchor_modes.size_law_spread_max_db', DER, '{:.2f}', 'dB')} 를 정한다. 측정이 그 "
           f"대가 없이 제약하는 양은 기울기뿐이므로 기울기만 받는다 "
           f"⟨{DER} : anchor_modes.why_production⟩.", "",
           f"그 선택을 측정으로 닫는 자리가 {ref('sim-vs-meas', short=True)} 이고, 절대 레벨을 "
           f"처음으로 앵커하는 것은 {ref('calibration-sphere', short=True)} 의 교정구다."),

        md("## 세 인자, 각각의 출처", "",
           table(["인자", "무엇", "어디서", "이 편의 근거"],
                 [["A(f) 기울기", "주파수 의존성", "**측정**(Das)",
                   "μ 기울기 " + _n('literature.mu_eps.das_phantom3_mono.mu_a', ANC, '{:.2f}', 'dB/GHz')],
                  ["A(f) 레벨", "절대 레벨", "**우리 PO 출력**",
                   "`" + _n('anchor_modes.production_mode', DER) + "` 의 레벨이동 절대 최대 "
                   + _n('anchor_modes.level_shift_abs_max_db', DER, '{:.2f}', 'dB')],
                  ["B₁(φ,θ)", "자세에 따른 모양", "**기하**(광선 가림 + PO)",
                   "재보정 후 정규화 패턴 변화 "
                   + _n('anchor.shape_invariance_max_abs_db', DER, '{:.1e}', 'dB')],
                  ["B₂", "자세 요동의 분포족", "기하",
                   "문헌 적합 RMSE " + _n('literature.fit_rmse_db.AAV', ANC, '{:.2f}', 'dB')
                   + " 가 기준선"]])),

        md("## 이 표가 서 있는 사슬 세대", "",
           f"⚠ **생산 앵커 원장과 위 문단의 우리 기울기는 σ 사슬의 서로 다른 세대다.** 생산 원장은 "
           f"{_n('anchor.slope_ledger_source_generation', DER)} 판 `rcs_anchor.json` 위에 서 있고, "
           f"위 문단은 디스크의 현재 판({_n('meta.generated', ANC)})에서 다시 적합한 값이다. 겹치는 "
           f"{_n('anchor.n_slope_crosschecked', DER, '{:.0f}', '기체')} 에서 밴드 기울기가 최대 "
           f"{_n('anchor.slope_ledger_gap_max_db_per_ghz', DER, '{:.3f}', 'dB/GHz')} 갈린다"
           f"({_n('anchor.slope_ledger_gap_max_drone', DER)}).", "",
           f"⚠ **그리고 두 세대 모두 {_MESHFIX} 전 메쉬 위에 서 있다** — 이 축은 위 문단의 세대 "
           f"축과 별개다. 기울기를 대조한 "
           f"{_n('anchor.n_slope_crosschecked', DER, '{:.0f}', '기체')} 중 Matrice 4E 가 그 정정을 "
           f"받았다 "
           f"⟨{MFX_ATK} : Q6_invalidated_outputs.critical[1]⟩.", "",
           f"⚠ 셋째 축 — 두 세대 모두 {_GAMMA_AXIS} 다. 앵커를 갈아끼우려면 σ 사슬 전체를 "
           f"형상 정정 + Γ(θ) 한 세대로 맞춰야 하고, 그것은 {ref_part(10)} 전체가 먹는 값이다."),

        next_steps([
            ("앵커 사슬(rcs_anchor → sigma_anchor)을 현재 메쉬·Γ(θ) 켠 커널로 다시 돌린다",
             "밴드 기울기와 재보정 원장이 현재 기하 위에 선다 — 재생성 평균이 기체마다 "
             + _n('overstated[0].결과_표[0].mean_delta_db', S2R, '{:+.2f}') + " ~ "
             + _n('overstated[0].결과_표[2].mean_delta_db', S2R, '{:+.2f}', 'dB') + " 로 갈린다",
             "`benchmark/rcs_anchor.py` → `src/sigma_anchor.py`"),
            ("R90 사슬에 `modes.slope_only.delta_db` 를 적용한다",
             "앵커 후 파형 순위가 확정된다 — 지금 적용하면 "
             + _n('sigma_sens.anchor_not_applied_n_order_changed', DER, '{:.0f}', '기체')
             + " 의 순위가 바뀐다",
             "`src/experiment_freespace_sigma.py` → " + ref("slope-anchor", short=True)),
            ("Matrice 4E · Mini 5 Pro 의 상대 레벨을 실측한다",
             "크기전이 지수가 직접 고정되어 앵커 원장의 최대 항이 닫힌다",
             ref("sim-vs-meas", short=True)),
            ("모서리 회절항(PTD)을 켜고 밴드 기울기를 다시 적합한다",
             "면적분 밖의 항이 주파수 축을 얼마나 옮기는지가 확정된다",
             "`benchmark/rcs_anchor.py --ptd`"),
        ]),
    ]


# =========================================================================== #
#  편 25 — anchor-ledger
# =========================================================================== #
def report_25_anchor_ledger():
    return [
        header(
            num=25,
            title="앵커가 통제한 항목과 남은 항목의 크기를 기체별 원장으로 적었다",
            did="앵커 기체와의 거리를 기체마다 판정하고, 앵커가 통제하지 못한 항목을 상태와 dB "
                "크기로 함께 원장에 적었다.",
            results=[
                f"앵커 기체는 {_n('anchor.anchor_platform', DER)} 한 대다 — 같은 급이면 `direct`"
                f"({_n('anchor.n_direct', DER, '{:.0f}', '대')}), 크기법칙으로 옮기면 `scaled`"
                f"({_n('anchor.n_scaled', DER, '{:.0f}', '대')}), 위상 자체가 다르면 "
                f"`not_comparable`({_n('anchor.n_not_comparable', DER, '{:.0f}', '대')}) 다.",

                f"가장 큰 미통제 항은 **{_n('anchor.largest_uncontrolled_term', DER)}** "
                f"{_n('anchor.largest_uncontrolled_db', DER, '{:.2f}', 'dB')} 이고, 실제 적용한 "
                f"보정 최대치 "
                f"{_n('anchor.correction_abs_max_db', DER, '{:.2f}', 'dB')} 보다 크다.",

                f"그래서 커널은 그대로 두고 **원장으로만** 적용한다 — 검출 결과 편이 이 표를 "
                f"함께 읽는다.",

                f"⭐ `polarisation` 칸은 이제 크기를 갖는다 — 얇은 판 참값에서 폭 "
                f"{_n('thin_plate.per_width.0.15.a_lam', LFA, '{:.2f}', 'λ')} 일 때 두 편파가 "
                f"{_n('thin_plate.truth_2d_mom.0.15.tm_minus_te_db', LFA, '{:.2f}', 'dB')} "
                f"갈린다.",
            ],
            method=[
                ("비교가능성 판정", "앵커 기체와 같은 급이면 `direct`, 크기법칙으로 옮기면 "
                              "`scaled`, 위상 자체가 다르면 `not_comparable` 로 적는다"),
                ("미통제 항목", "앵커가 닫지 못한 항목을 상태(RESOLVED/PARTIAL/UNRESOLVED)와 dB "
                          "크기로 함께 싣는다 — 크기를 못 붙인 항은 그렇게 적는다"),
                ("왜 원장인가", "가장 큰 미통제 항이 실제 보정보다 크다. 그래서 커널을 고치는 "
                           "대신 원장으로 적고 결과 편이 나란히 읽게 한다"),
            ],
            repro=_repro([_DERIVE], [SIG, DER, LFA],
                         "약 2분 (GPU 0장)",
                         "두 표 모두 생산 원장 세대이고 " + _MESHFIX + " 전 메쉬 위에 있다"),
        ),

        md("## 기체마다 앵커와의 거리가 다르다", "",
           f"앵커 기체는 {_n('anchor.anchor_platform', DER)} 한 대다. 같은 급이면 `direct`"
           f"({_n('anchor.n_direct', DER, '{:.0f}', '대')}), 크기법칙으로 옮기면 `scaled`"
           f"({_n('anchor.n_scaled', DER, '{:.0f}', '대')}), 위상 자체가 다르면 `not_comparable`"
           f"({_n('anchor.n_not_comparable', DER, '{:.0f}', '대')})로 적는다."),

        md(table_from(f"{SIG}:drones",
                      [("기체", "comparability.name"), ("대각 D [m]", "comparability.D_m"),
                       ("D/D_ref", "comparability.size_ratio"),
                       ("로터", "comparability.num_rotors"),
                       ("판정", "comparability.verdict"),
                       ("L²↔L⁴ 산포 [dB]", "comparability.size_law_spread_db")],
                      fmt={"comparability.D_m": "{:.3f}", "comparability.size_ratio": "{:.2f}",
                           "comparability.num_rotors": "{:.0f}",
                           "comparability.size_law_spread_db": "{:.2f}"})),

        md("## 앵커가 통제한 항목과 남은 항목의 크기", "",
           table_from(f"{SIG}:uncontrolled",
                      [("항목", "term"), ("상태", "status"), ("크기 [dB]", "size_db")],
                      fmt={"size_db": "{:+.2f}"}, null="미상"), "",
           f"표의 `polarisation` 행 크기 칸은 원장이 null(미상)로 두고 있다 — 본문이 드는 "
           f"{_n('thin_plate.truth_2d_mom.0.15.tm_minus_te_db', LFA, '{:.2f}', 'dB')} 는 얇은 판 "
           f"참값에서 온 값이고, 원장 반영은 다음 단계 표에 있다."),

        md("## 가장 큰 항이 실제 보정보다 크다", "",
           f"가장 큰 항은 **{_n('anchor.largest_uncontrolled_term', DER)}** "
           f"{_n('anchor.largest_uncontrolled_db', DER, '{:.2f}', 'dB')} 이고, 실제 적용한 보정 "
           f"최대치 {_n('anchor.correction_abs_max_db', DER, '{:.2f}', 'dB')} 보다 크다. 그래서 "
           f"커널은 그대로 두고 **원장으로만** 적용한다 — {ref_part(10)} 이 이 표를 함께 읽는다.", "",
           f"⭐ `polarisation` 칸은 이제 크기를 갖는다 — 얇은 판 참값에서 폭 "
           f"{_n('thin_plate.per_width.0.15.a_lam', LFA, '{:.2f}', 'λ')} 일 때 두 편파가 "
           f"{_n('thin_plate.truth_2d_mom.0.15.tm_minus_te_db', LFA, '{:.2f}', 'dB')} 갈리는데 우리 "
           f"면적분은 편파를 가르는 대신 세기 하나만 내는 스칼라다"
           f"({ref('po-knee', short=True)}). 그 낙차가 이 항의 크기이고, 부호는 "
           f"{ref('sigma-checklist', short=True)} 의 VV/HH 측정이 정한다.", "",
           f"⚠ 두 표 모두 생산 원장 세대이고 {_MESHFIX} 전 메쉬 위에 있으며, {_GAMMA_AXIS} 다 "
           f"— Matrice 4E 행이 그 정정을 받은 기체다."),

        next_steps([
            ("VV/HH 2편파를 잰다",
             "원장의 편파 항이 크기에서 값으로 바뀐다",
             ref("sigma-checklist", short=True)),
            ("Matrice 4E · Mini 5 Pro 의 상대 레벨을 실측한다",
             "크기전이 지수가 직접 고정되어 원장의 최대 항이 닫힌다",
             ref("sim-vs-meas", short=True)),
            ("정정된 메쉬로 앵커 원장 두 표를 다시 낸다",
             "원장이 현재 형상 위에 선다",
             f"⟨{MFX_ATK} : recommended_gate_before_any_sigma_claim⟩"),
            ("고도 정합을 문헌 측정과 같은 격자로 좁힌다",
             "PARTIAL 로 남은 elevation 항이 닫힌다",
             "`benchmark/rcs_anchor.py` → 고도 격자"),
        ]),
    ]


# =========================================================================== #
#  편 26 — blind-p3
# =========================================================================== #
def report_26_blind_p3():
    return [
        header(
            num=26,
            title="Phantom 3 를 문헌값을 보지 않고 내고 봉인을 풀었다",
            did="앵커 기체와 같은 기체를 문헌 상수를 한 번도 읽지 않은 경로로 돌리고 별도 "
                "스크립트가 봉인을 풀어 문헌과 맞댔다.",
            results=[
                f"같은 창 "
                f"{_n('slope.das_published.band[0]', P3V1, '{:.1f}')}~"
                f"{_n('slope.das_published.band[1]', P3V1, '{:.1f}', 'GHz')} 에서 우리 커널로 "
                f"돌렸다(`benchmark/p3_ours.py`, "
                f"{_n('meta.runtime_s_total_process', P3O, '{:,.0f}', 's')}).",

                f"우리 el=0 전대역 기울기는 "
                f"{_n('slope.ours_el0_full_band.a', P3V1, '{:.3f}')} ± "
                f"{_n('slope.ours_el0_full_band.se_a', P3V1, '{:.3f}', 'dB/GHz')} 이고, Das 공표 "
                f"{_n('slope.das_published.a', P3V1, '{:.2f}', 'dB/GHz')} 대비 "
                f"{_n('slope.ratios.ours_over_das', P3V1, '{:.2f}', '배')} · "
                f"{_n('slope.significance.z_vs_das_0p21', P3V1, '{:.1f}', 'σ')} 다.",

                f"Yuan θ=90° 실측곡선 대비는 "
                f"{_n('slope.ratios.ours_over_yuan_theta90', P3V1, '{:.2f}', '배')} · "
                f"{_n('slope.significance.z_vs_yuan_theta90_0p315', P3V1, '{:.1f}', 'σ')} 이고 레벨은 "
                f"{_n('residual.vs_yuan_theta90_measured_curve.mean_db', P3V1, '{:+.2f}', 'dB')} 다.",

                f"우리 세 밴드가 전부 저주파 구간 안에 있고, 거기서 우리 μ(f) 는 "
                f"{_n('subband_fits.by_aspect.el0.1.8-6.0 GHz.a', P3O, '{:.2f}')}(1.8–6.0 GHz)에서 "
                f"{_n('subband_fits.by_aspect.el0.6.0-18.2 GHz.a', P3O, '{:.2f}', 'dB/GHz')}"
                f"(6.0–18.2 GHz)로 꺾인다.",

                f"낙차의 방향은 얇은 판 참값이 정한다 — 전력을 만드는 쪽 기준이면 우리 PO 가 "
                f"{_n('thin_plate.truth_2d_mom.0.15.po_minus_tm_db', LFA, '{:.2f}')}, 약한 쪽 "
                f"기준이면 "
                f"{_n('thin_plate.truth_2d_mom.0.15.po_minus_te_db', LFA, '{:+.2f}', 'dB')} 다.",
            ],
            method=[
                ("눈감기", "산출 과정은 문헌 상수를 한 번도 읽지 않았고 봉인은 별도 스크립트가 "
                       "풀었다(`benchmark/p3_validation.py`)"),
                ("창 맞추기", "적합 창은 Das Table III · Yuan §IV 와 같다 — 창을 바꾸면 같은 "
                          "커널에서도 기울기가 달라지기 때문이다"),
                ("무엇을 재나", "절대 레벨과 주파수 의존 **두 스칼라**다. 각도패턴은 우리 기하에서 "
                           "나온 그대로다"),
                ("독립성", "Das 의 Phantom 3 행은 Yuan 원자료의 재분석이라 독립 2건이 아니다"),
            ],
            repro=_repro(["PYTHONPATH=src python benchmark/p3_ours.py",
                          "PYTHONPATH=src python benchmark/p3_validation.py"],
                         [P3O, P3V1, LFA, LFK],
                         "약 4시간 (GPU 1장 — 전대역 σ 를 다시 낸다)",
                         "이 절의 표 네 행은 전부 v1 메쉬 산출이다 — v2 는 다음 편이 잇는다"),
        ),

        md("## 무엇을 눈감고 냈나", "",
           f"앵커 기체와 같은 기체(DJI Phantom 3)를 같은 창 "
           f"{_n('slope.das_published.band[0]', P3V1, '{:.1f}')}~"
           f"{_n('slope.das_published.band[1]', P3V1, '{:.1f}', 'GHz')} 에서 우리 커널로 돌렸다"
           f"(`benchmark/p3_ours.py`, "
           f"{_n('meta.runtime_s_total_process', P3O, '{:,.0f}', 's')}). 산출 과정은 문헌 상수를 "
           f"한 번도 읽지 않았고 봉인은 별도 스크립트가 풀었다. 적합 창은 Das Table III · Yuan §IV "
           f"와 같다(일치 {_n('window.same_window', P3V1)}).", "",
           f"이 대조가 재는 것은 절대 레벨과 주파수 의존 두 스칼라이고, 각도패턴은 우리 기하에서 "
           f"나온 그대로다. ⚠ 아래 표 네 행은 전부 **v1 메쉬** 산출이다 — 사진 실측으로 다시 지은 "
           f"v2 메쉬의 같은 두 스칼라는 {ref('box-sphere-control', short=True)} 이 잇는다."),

        md("## 봉인을 풀고 맞댄 결과", "",
           table(["대조 상대", "고도 · 창", "기울기 [dB/GHz]", "우리와의 거리"],
                 [["우리 el=0 전대역 (눈감기 산출)",
                   "el=0 · " + _n('slope.das_published.band[0]', P3V1, '{:.1f}') + "–"
                   + _n('slope.das_published.band[1]', P3V1, '{:.1f}', 'GHz'),
                   _n('slope.ours_el0_full_band.a', P3V1, '{:.3f}') + " ± "
                   + _n('slope.ours_el0_full_band.se_a', P3V1, '{:.3f}')
                   + " (양 끝점 제외 "
                   + _n('slope.ours_slope_robustness.drop_both_endpoints', P3V1, '{:.3f}') + ")",
                   "—"],
                  ["Das 공표 (IEEE WCL 2026)", "고도풀링 · 같은 창",
                   _n('slope.das_published.a', P3V1, '{:.2f}'),
                   _n('slope.ratios.ours_over_das', P3V1, '{:.2f}', '배') + " · "
                   + _n('slope.significance.z_vs_das_0p21', P3V1, '{:.1f}', 'σ')],
                  ["Yuan θ=90° 실측곡선 (EuCAP 2025)", "고도정합 · 같은 창",
                   _n('slope.yuan_theta90_published.a', P3V1, '{:.3f}'),
                   _n('slope.ratios.ours_over_yuan_theta90', P3V1, '{:.2f}', '배') + " · "
                   + _n('slope.significance.z_vs_yuan_theta90_0p315', P3V1, '{:.1f}', 'σ')
                   + " · 레벨 "
                   + _n('residual.vs_yuan_theta90_measured_curve.mean_db', P3V1, '{:+.2f}', 'dB')],
                  ["부분대역 1.8–6.0 GHz (설명)", "el=0 · 실측곡선 대조",
                   "우리 " + _n('subband_fits.by_aspect.el0.1.8-6.0 GHz.a', P3O, '{:.2f}')
                   + " vs 측정 "
                   + _n('our_operating_band.measured_theta90_curve_dense.a', P3V1, '{:.2f}'),
                   _n('our_operating_band.slope_ratio', P3V1, '{:.2f}', '배') + " · 1.8 GHz 레벨 "
                   + _n('our_operating_band.level_error_db.at_1p8', P3V1, '{:+.2f}', 'dB')]])),

        md("## 정본은 전대역 대 전대역이다", "",
           f"부분대역 행은 우리 μ(f) 가 "
           f"{_n('subband_fits.by_aspect.el0.1.8-6.0 GHz.a', P3O, '{:.2f}')}(1.8–6.0 GHz)에서 "
           f"{_n('subband_fits.by_aspect.el0.6.0-18.2 GHz.a', P3O, '{:.2f}', 'dB/GHz')}"
           f"(6.0–18.2 GHz)로 꺾인다는 것을 보이는 설명이다.", "",
           f"⚠ **우리 세 밴드(LTE {_n('bands_ghz.LTE', DER, '{:.3f}')} · 5G "
           f"{_n('bands_ghz.5G', DER, '{:.1f}')} · WiFi "
           f"{_n('bands_ghz.WiFi', DER, '{:.2f}', 'GHz')})가 전부 그 저주파 구간 안에 있고, 거기서 "
           f"우리 σ 는 실측곡선보다 낮다.**"),

        md("## 낙차의 방향은 어디까지 말할 수 있나", "",
           f"이 낙차의 방향은 결과 밖에 둔다 — 우리 PO 적분은 편파를 가르는 대신 세기 하나만 내는 "
           f"스칼라라서, 참값이 편파에 따라 갈리는 구간에서는 한쪽 편파 기준으로 낮게 다른 쪽 "
           f"기준으로 높게 나온다 ⟨{LFK} : what_survives_the_attack[4]⟩.", "",
           f"⭐ 다만 두 쪽의 크기가 서로 다르다 — 얇은 판 참값에서 **전력을 만드는 쪽**(두 편파 중 "
           f"σ 가 {_n('thin_plate.truth_2d_mom.0.15.tm_minus_te_db', LFA, '{:.2f}', 'dB')} 큰 쪽) "
           f"기준이면 우리 PO 는 "
           f"{_n('thin_plate.truth_2d_mom.0.15.po_minus_tm_db', LFA, '{:.2f}', 'dB')}(음수 = 우리가 "
           f"낮다), 약한 쪽 기준이면 "
           f"{_n('thin_plate.truth_2d_mom.0.15.po_minus_te_db', LFA, '{:+.2f}', 'dB')} 다.", "",
           f"그래서 **우리 σ 가 낮게 나와 있을 개연성 쪽이 크고**, 그 방향이라면 검출 산출물은 "
           f"보수적인(비관적인) 쪽으로 틀린 것이다. 레벨을 만드는 굵은 부품일수록 이 어긋남이 "
           f"작아서 이 항이 설명하는 몫은 관측된 낙차보다 작다 "
           f"⟨{LFK} : q4_A_and_B_are_not_exclusive.the_dB_decomposition_the_files_refuse_to_do."
           f"my_crude_budget.reading⟩ — 그래서 방향은 여기까지, 개연성으로만 적는다. 금칙 세 "
           f"가지는 {ref('po-knee', short=True)} 에 있다."),

        next_steps([
            ("v2 메쉬로 같은 눈감기 대조를 다시 봉인해 돌린다",
             "형상 개선이 두 스칼라를 어느 방향으로 옮기는지가 사전등록 아래에서 확정된다",
             "`benchmark/p3_ours.py` → " + ref("box-sphere-control", short=True)),
            ("편파를 가르는 커널로 같은 창을 다시 낸다",
             "낙차의 부호가 개연성에서 값으로 바뀐다",
             ref("kernel-open-items", short=True)),
            ("같은 잣대를 네 기체로 넓힌다",
             "일치도가 한 기체의 우연인지 함대에서 서는 성질인지가 갈린다",
             ref("fleet-prereg", short=True)),
        ]),
    ]


# =========================================================================== #
#  편 27 — box-sphere-control
# =========================================================================== #
def report_27_box_sphere_control():
    return [
        header(
            num=27,
            title="메쉬가 사는 축은 절대 크기가 아니라 각도 구조다",
            did="Phantom 3 를 상자·정육면체·구로 바꿔 넣고 같은 눈금에서 다시 채점해 메쉬가 "
                "값어치를 내는 축을 갈랐다.",
            results=[
                f"레벨 축에서 우리 메쉬는 상자 계열을 전부 이긴다 — 가장 가까운 정육면체가 "
                f"{_n('controls.table.cube_vol_v2.level_err_db', P3V2, '{:+.2f}')} 인데 우리는 "
                f"{_n('controls.table.ours_phantom3_mesh_v2.level_err_db', P3V2, '{:+.2f}', 'dB')} "
                f"다.",

                f"⚠ 레벨 하나만 보면 부피를 맞게 고른 구가 우리보다 낫다 — 논문표기 상자와 부피가 "
                f"같은 구가 "
                f"{_n('controls.table.sphere_eqvol_paperbox.level_err_db', P3V2, '{:+.2f}', 'dB')} · "
                f"rms {_n('controls.table.sphere_eqvol_paperbox.rms_db', P3V2, '{:.2f}', 'dB')} 다.",

                f"⭐ 그 구의 부피를 무엇으로 잡는가가 자유 매개변수다 — 메쉬 부피와 같은 구는 "
                f"{_n('controls.table.sphere_vol_v2.level_err_db', P3V2, '{:+.2f}', 'dB')} 로 "
                f"우리보다 나쁘다.",

                f"각도 축에서는 갈린다 — Das 잣대에서 우리는 "
                f"{_n('controls.table.ours_phantom3_mesh_v2.eps_err_vs_das_db', P3V2, '{:+.2f}')}, "
                f"상자 계열은 "
                f"{_n('controls.table.cube_vol_v2.eps_err_vs_das_db', P3V2, '{:+.2f}')}~"
                f"{_n('controls.table.box_paper.eps_err_vs_das_db', P3V2, '{:+.2f}', 'dB')} 다.",

                f"v1→v2 메쉬는 레벨오차 "
                f"{_n('v1_vs_v2.level_db.v1', P3V2, '{:+.2f}')} → "
                f"{_n('v1_vs_v2.level_db.v2', P3V2, '{:+.2f}', 'dB')}, 기울기 "
                f"{_n('v1_vs_v2.slope_db_per_ghz.v1', P3V2, '{:.3f}')} → "
                f"{_n('v1_vs_v2.slope_db_per_ghz.v2', P3V2, '{:.3f}', 'dB/GHz')} 로 움직인다.",
            ],
            method=[
                ("무엇을 갈아끼우나", "같은 자리·같은 창에서 Phantom 3 를 논문표기 상자·정육면체·"
                               "구로 바꿔 넣고 다시 채점한다"),
                ("레벨의 잣대", "Yuan θ90 복원 실측곡선 기준 밴드평균 잔차 "
                           f"⟨{P3V2} : controls.scoring⟩"),
                ("각도의 잣대", "⚠ ε(방위 산포)만은 잣대가 다르다 — 비교 상대가 Das Table III 가 "
                           "준 값이다. 레벨은 Yuan 잣대, ε 는 Das 잣대다"),
                ("메쉬 세대", "이 편의 «우리» 는 v2 메쉬(사진 실측으로 다시 지은 판)이고, 눈감기 "
                          "대조의 «우리» 는 v1 이다"),
            ],
            repro=_repro(["PYTHONPATH=src python benchmark/p3_validation_v2.py"],
                         [P3V2, DFV],
                         "약 2시간 (GPU 1장 — 대조군 형상마다 σ 를 다시 낸다)",
                         "구는 방위에 따라 σ 가 그대로라 ε 를 0 으로 낸다"),
        ),

        md("## 무엇을 갈아끼웠나", "",
           f"**레벨을** 같은 눈금(Yuan θ90 복원 실측곡선 기준 밴드평균 잔차 "
           f"⟨{P3V2} : controls.scoring⟩)으로 놓고 Phantom 3 를 상자·정육면체·구로 바꿔 넣어 다시 "
           f"채점했다. 우리 메쉬는 **상자 계열을 전부 이긴다** — 가장 가까운 정육면체가 "
           f"{_n('controls.table.cube_vol_v2.level_err_db', P3V2, '{:+.2f}')} 인데 우리는 "
           f"{_n('controls.table.ours_phantom3_mesh_v2.level_err_db', P3V2, '{:+.2f}', 'dB')} 다.", "",
           f"⚠ 그런데 **레벨 하나만 보면 부피를 맞게 고른 구가 우리보다 낫다** — 논문표기 상자와 "
           f"부피가 같은 구가 "
           f"{_n('controls.table.sphere_eqvol_paperbox.level_err_db', P3V2, '{:+.2f}', 'dB')} · "
           f"주파수 전체에 걸친 평균 오차 크기(rms) "
           f"{_n('controls.table.sphere_eqvol_paperbox.rms_db', P3V2, '{:.2f}', 'dB')} 다. "
           f"⭐ 다만 **그 구의 부피를 무엇으로 잡는가가 자유 매개변수**(결과를 보고 골라 넣을 수 "
           f"있는 값)다 — 메쉬 부피와 같은 구는 "
           f"{_n('controls.table.sphere_vol_v2.level_err_db', P3V2, '{:+.2f}', 'dB')} 로 우리보다 "
           f"나쁘다."),

        md("## v1 과 v2 는 다른 메쉬다", "",
           f"⭐ **이 편의 «우리» 는 v2 메쉬**(사진 실측으로 다시 지은 판)이고, "
           f"{ref('blind-p3', short=True)} 표의 «우리» 는 v1 메쉬다. 같은 Yuan θ90 곡선 잣대에서 "
           f"v1→v2 는 레벨오차 "
           f"{_n('v1_vs_v2.level_db.v1', P3V2, '{:+.2f}')} → "
           f"{_n('v1_vs_v2.level_db.v2', P3V2, '{:+.2f}', 'dB')}, 기울기 "
           f"{_n('v1_vs_v2.slope_db_per_ghz.v1', P3V2, '{:.3f}')} → "
           f"{_n('v1_vs_v2.slope_db_per_ghz.v2', P3V2, '{:.3f}', 'dB/GHz')}"
           f"(촘촘하게 되살린 실측곡선 "
           f"{_n('v1_vs_v2.slope_db_per_ghz.measured_comparand_dense', P3V2, '{:.3f}', 'dB/GHz')})로 "
           f"움직인다 — 레벨은 가까워지고 기울기는 멀어졌다.", "",
           f"형상은 삼각형 {_n('v1_vs_v2.mesh.v1_n_tri', P3V2, '{:,.0f}')}→"
           f"{_n('v1_vs_v2.mesh.v2_n_tri', P3V2, '{:,.0f}')} · 실루엣 IoU 가 자기복제 상한 대비 "
           f"{_n('v1_vs_v2.mesh.silhouette_iou_pct_of_ceiling.old', P3V2, '{:.1f}')}→"
           f"{_n('v1_vs_v2.mesh.silhouette_iou_pct_of_ceiling.new', P3V2, '{:.1f}', '%')} 다."),

        md("## 각도 축에서는 갈린다", "",
           f"구는 방위에 따라 σ 가 그대로라 방위 산포 ε(같은 기체를 여러 방위에서 볼 때 σ 가 얼마나 "
           f"흩어지는지, dB)를 "
           f"{_n('controls.table.sphere_eqvol_paperbox.eps_mean_db', P3V2, '{:.2f}', 'dB')} 로 낸다.", "",
           f"⚠ **ε 만은 잣대가 다르다** — 비교 상대가 위 레벨이 쓴 Yuan 곡선이 아니라 Das Table III "
           f"가 준 {_n('v1_vs_v2.eps_db.das_mean', P3V2, '{:.2f}', 'dB')} 다. 그 Das 잣대에서 "
           f"우리는 "
           f"{_n('controls.table.ours_phantom3_mesh_v2.eps_err_vs_das_db', P3V2, '{:+.2f}')}, 상자 "
           f"계열은 {_n('controls.table.cube_vol_v2.eps_err_vs_das_db', P3V2, '{:+.2f}')}~"
           f"{_n('controls.table.box_paper.eps_err_vs_das_db', P3V2, '{:+.2f}', 'dB')} 다.", "",
           f"**그래서 메쉬가 값어치를 내는 축은 σ 의 절대 크기가 아니라 각도에 따른 구조다** — 절대 "
           f"레벨은 {ref('calibration-sphere', short=True)} 의 교정구가 측정으로 앵커한다."),

        md("## 레벨에서 구가 이긴 것은 잣대가 아니라 어느 구를 넣었나가 갈랐다", "",
           f"⭐ 메쉬 부피로 잡은 같은 반지름의 구를 레벨까지 Das Table III 잣대로 다시 채점해도 "
           f"같은 Phantom 3 에서 우리"
           f"({_n('box_control.phantom3.ours_DL_db', DFV, '{:+.2f}')})가 구"
           f"({_n('box_control.phantom3.controls.sphere_eqvol.DL_db', DFV, '{:+.2f}', 'dB')})를 "
           f"이긴다. 그쪽 표는 구의 σ 를 단면적 πa² 로 굳힌 근사로, 이 표는 정확해(Mie)로 낸다 — "
           f"반지름은 같다.", "",
           f"즉 **두 잣대 모두에서 지는 것은 메쉬 부피로 잡은 구**이고, 레벨에서 우리를 앞선 것은 "
           f"반지름을 그보다 키운 논문표기 상자부피 구 하나다. 두 결과는 «어느 부피를 골랐나» 와 "
           f"함께 읽는다.", "",
           f"⚠ 이 마지막 두 수는 함대 원장(`{DFV}`)에서 왔고, 그 σ 는 다중정적 경로"
           f"(`rcs_sbr_multistatic`)로 낸 값이다. 그 경로에 Γ(θ) 각도 모양이 들어온 것은 "
           f"{_n('generated', VBF)} 이고 이 표는 그 이전 판이다 — **재계산 대기**이고, 두 수의 "
           f"순위는 재계산 뒤 다시 읽는다."),

        next_steps([
            ("Phantom 3 구 대조군을 방위 산포 ε 축까지 포함해 다섯 기체로 넓힌다",
             "형상 모형이 각도 구조를 사는 폭이 기체마다 확정된다",
             "`benchmark/p3_validation_v2.py` 확장"),
            ("교정구를 표적과 같은 자리에서 함께 잰다",
             "레벨 축이 측정으로 닫힌다 — 지금은 어느 부피를 골랐나가 결과를 정한다",
             ref("calibration-sphere", short=True)),
            ("같은 대조군을 함대 사전등록 채점으로 넓힌다",
             "형상 증거의 유무가 일치도를 가르는지가 네 기체에서 확정된다",
             ref("fleet-prereg", short=True)),
        ]),
    ]


# =========================================================================== #
#  편 28 — fleet-prereg
# =========================================================================== #
def report_28_fleet_prereg():
    return [
        header(
            num=28,
            title="같은 잣대를 네 기체로 넓히면 판정이 NOT_VALIDATED 로 갈린다",
            did="계산 전에 봉인한 합격규칙을 그대로 걸어 Das Table III 의 네 기체 · 바이스태틱각 "
                "일곱 개를 전수 채점했다.",
            results=[
                f"판정은 **{_n('prereg_judgement.verdict', DFV)}** 다 — 결정권을 준 항목은 레벨오차 "
                f"산포가 6.0 dB 이하일 것이고, 실제 산포는 "
                f"{_n('prereg_judgement.P3_spread_db', DFV, '{:.2f}', 'dB')} 다.",

                f"봉인이 예측한 산포는 "
                f"{_n('prereg_judgement.spread_predicted_db', DFV, '{:.1f}', 'dB')} 였다 — 예측이 "
                f"반증됐다.",

                f"⭐ 갈린 축은 대역도 전기적 크기도 기체 크기도 아니고 **그 기체 자체의 형상 증거가 "
                f"있는가** 다 — 증거가 있는 Mini 2 "
                f"{_n('prereg_judgement.DL0_db.mini2', DFV, '{:+.2f}')} · Phantom 3 "
                f"{_n('prereg_judgement.DL0_db.phantom3', DFV, '{:+.2f}')} 와 얇은 Phantom 2 "
                f"{_n('prereg_judgement.DL0_db.phantom2', DFV, '{:+.2f}')} · M350 RTK "
                f"{_n('prereg_judgement.DL0_db.m350rtk', DFV, '{:+.2f}', 'dB')} 사이에 "
                f"{_n('degrees_of_freedom.evidence_split.gap_db', DFV, '{:.2f}', 'dB')} 의 빈 구간이 "
                f"있다.",

                f"예측이 반증됐고 일치도가 메쉬 구속도를 따라간다는 두 사실이 함께 서 있다 — "
                f"그것은 결과에 맞춰 맞춘 흔적의 정반대 서명이다 ⟨{DFA} : Q5_tuned_evidence⟩.",
            ],
            method=[
                ("사전등록", "합격규칙은 **계산 전에** 봉인했고(`outputs/das_fleet_prereg.json`) "
                         "그대로 썼다"),
                ("결정 항목", "⭐ max(DL(0)) − min(DL(0)) ≤ 6.0 dB — 오차가 기체마다 흩어진 게 "
                          "아니라 **공통 오프셋**일 것"),
                ("DL(0) 이란", "바이스태틱각 0°(송신기와 수신기가 같은 자리)에서 측정 대비 우리 σ "
                           "가 몇 dB 높거나 낮은가다 — 양수면 우리가 더 밝게 냈다"),
                ("P3 이란", "판정 문자열의 P3 은 봉인한 합격조건 네 개 중 **세 번째**(레벨오차의 "
                        "산포)를 가리키는 이름이고 기체 Phantom 3 를 뜻하지 않는다"),
            ],
            repro=_repro(["PYTHONPATH=src python benchmark/das_fleet_validation.py"],
                         [DFV, DFP, DFA],
                         "약 3시간 (GPU 1장 — 네 기체를 문헌 격자에서 다시 낸다)",
                         "봉인 파일은 채점 전 커밋에 그대로 있다"),
        ),

        md("## 봉인하고 채점했다", "",
           f"Das Table III 는 네 기체를 바이스태틱각 일곱 개로 준다 — 그 칸을 전부 채점했다"
           f"(⟨{DFV} : table_28⟩). 합격규칙은 **계산 전에** 봉인했고"
           f"(`outputs/das_fleet_prereg.json`) 그대로 썼다.", "",
           f"결정권을 준 항목은 「⭐ max(DL(0)) − min(DL(0)) ≤ 6.0 dB — 오차가 기체마다 흩어진 게 "
           f"아니라 **공통 오프셋**일 것 "
           f"⟨{DFP} : pass_rule.primary_gate_level_at_theta_b_0.P3_spread⟩」 이다."),

        md("## 판정", "",
           f"판정은 **{_n('prereg_judgement.verdict', DFV)}** 다 — 실제 산포가 "
           f"{_n('prereg_judgement.P3_spread_db', DFV, '{:.2f}', 'dB')} 이고 봉인이 예측한 산포는 "
           f"{_n('prereg_judgement.spread_predicted_db', DFV, '{:.1f}', 'dB')} 였다.", "",
           table(["봉인 항목", "무엇을 요구했나", "통과"], [
               ["P1", _n('pass_rule.primary_gate_level_at_theta_b_0.P1_all', DFP),
                _n('prereg_judgement.P1_all_within_6db', DFV)],
               ["P2", _n('pass_rule.primary_gate_level_at_theta_b_0.P2_most', DFP),
                _n('prereg_judgement.P2_three_within_4db', DFV)
                + " (실제 " + _n('prereg_judgement.P2_count_within_4db', DFV, '{:.0f}', '기체')
                + ")"],
               ["P3 ⭐", _n('pass_rule.primary_gate_level_at_theta_b_0.P3_spread', DFP),
                _n('prereg_judgement.P3_spread_within_6db', DFV)],
               ["P4", _n('pass_rule.primary_gate_level_at_theta_b_0.P4_sign', DFP),
                _n('prereg_judgement.P4_sign_agreement', DFV)],
               ["기울기", f"phantom3 · phantom2 둘 다 기울기차가 봉인 문턱 안 ⟨{DFP} : "
                        f"pass_rule.slope_gate.S1⟩", _n('prereg_judgement.slope_gate_pass', DFV)],
               ["바이스태틱", f"phantom2 의 바이스태틱 추세가 봉인 범위 안 ⟨{DFP} : "
                          f"pass_rule.bistatic_gate⟩", _n('prereg_judgement.bistatic_gate_pass', DFV)],
           ]), "",
           f"네 항목 전부 통과가 요구조건이고"
           f"(⟨{DFP} : pass_rule.primary_gate_level_at_theta_b_0.all_four_required⟩), 판정 "
           f"문자열이 이름으로 든 것은 산포(P3) 다 — 봉인이 «판정을 정하는 항목» 으로 미리 지목한 "
           f"것이 그것이기 때문이다 ⟨{DFP} : "
           f"pass_rule.primary_gate_level_at_theta_b_0.why_spread_is_the_decisive_one⟩.", "",
           f"⚠ 용어 두 개를 푼다. 판정 문자열의 **P3 은 봉인한 합격조건 네 개 중 세 번째**(레벨오차 "
           f"산포)를 가리키는 이름이고 기체 Phantom 3 를 뜻하지 않는다. 그리고 **레벨오차 DL(0)** "
           f"는 바이스태틱각 0°(송신기와 수신기가 같은 자리에 있는 배치)에서 측정 대비 우리 σ 가 "
           f"몇 dB 높거나 낮은가다 — 양수면 우리가 더 밝게 냈다는 뜻이다."),

        md("## 갈린 축은 형상 증거의 유무다", "",
           f"⭐ 갈린 축은 대역도 전기적 크기도 기체 크기도 아니고 **그 기체 자체의 형상 증거가 "
           f"있는가** 다 — 형상 증거가 있는 Mini 2 "
           f"{_n('prereg_judgement.DL0_db.mini2', DFV, '{:+.2f}')} · Phantom 3 "
           f"{_n('prereg_judgement.DL0_db.phantom3', DFV, '{:+.2f}')} 와 증거가 얇은 Phantom 2 "
           f"{_n('prereg_judgement.DL0_db.phantom2', DFV, '{:+.2f}')} · M350 RTK "
           f"{_n('prereg_judgement.DL0_db.m350rtk', DFV, '{:+.2f}', 'dB')} 사이에 "
           f"{_n('degrees_of_freedom.evidence_split.gap_db', DFV, '{:.2f}', 'dB')} 의 빈 구간이 "
           f"있다.", "",
           f"예측이 반증됐고 일치도가 메쉬 구속도를 따라간다는 두 사실이 함께 서 있고, 그것은 "
           f"결과에 맞춰 맞춘 흔적의 정반대 서명이다 ⟨{DFA} : Q5_tuned_evidence⟩.", "",
           f"⚠ 이 2:2 분할은 봉인이 계산 전에 지목한 것이고, 지목된 두 기체가 |DL(0)| 하위 두 "
           f"자리를 다 차지할 확률은 무작위 배정에서 "
           f"{_n('degrees_of_freedom.evidence_split.exact_partition_p', DFV, '{:.3f}')} 다 — "
           f"기체가 넷뿐이라 유의수준이 아니라 **가설 생성**으로 읽는다 "
           f"⟨{DFV} : degrees_of_freedom.evidence_split.exact_partition_note⟩. 구속도와 |DL(0)| 의 "
           f"상관도 같은 이유로 서술용이다 ⟨{DFV} : degrees_of_freedom._correlation.what⟩.", "",
           f"⚠ M350 RTK 값은 계산이 다 끝나기 전의 스냅샷에서 집계됐고, Mini 2 행은 {_MESHFIX} 전 "
           f"메쉬에서 나온 값이다 — 둘 다 재집계를 기다린다 "
           f"⟨{DFA} : overall.required_before_citing[0]⟩ · "
           f"⟨{MFX_ATK} : Q6_invalidated_outputs.critical[0]⟩.", "",
           f"⚠ **이 표의 σ 는 다중정적 경로(`rcs_sbr_multistatic`)로 냈고, 그 경로에 Γ(θ) 각도 "
           f"모양이 들어온 것은 {_n('generated', VBF)} 다** — 그 뒤로 복소장 경로와 σ 경로가 "
           f"{_n('verdict.sigma_angle_gamma_gap_db', VBF, '{:.1e}', 'dB')} 안에서 같은 값을 낸다"
           f"(⟨{VBF} : sigma_cross_check.angle_gamma_on⟩). 이 표는 그 배선 이전 판이라 **재계산 "
           f"대기**이고, 이동의 크기는 이 격자에서 아직 안 쟀다. 판정이 기댄 것은 산포 "
           f"{_n('prereg_judgement.P3_spread_db', DFV, '{:.2f}', 'dB')} 와 위 표 P3 문턱 사이의 "
           f"거리이고, 형상 증거 구간 "
           f"{_n('degrees_of_freedom.evidence_split.gap_db', DFV, '{:.2f}', 'dB')} 는 그 거리보다 "
           f"좁다."),

        next_steps([
            ("함대 σ 를 Γ(θ) 가 배선된 다중정적 경로로 다시 낸다",
             "이 표의 모든 칸이 현재 커널 위에 서고, 형상 증거 구간이 그 이동 뒤에도 남는지가 갈린다",
             "`benchmark/das_fleet_sigma.py` → `benchmark/das_fleet_validation.py`"),
            ("M350 RTK 를 계산이 끝난 격자에서 다시 집계한다",
             "네 기체 중 한 행의 값이 확정되어 산포가 다시 계산된다",
             f"⟨{DFA} : overall.required_before_citing[0]⟩"),
            ("Mini 2 를 정정된 메쉬로 다시 낸다",
             "형상 증거 축이 정정 후에도 서는지가 확정된다",
             f"⟨{MFX_ATK} : Q6_invalidated_outputs.critical[0]⟩"),
            ("형상 증거가 있는 기체를 실측으로 늘린다",
             "형상 증거 ↔ 일치도의 관계가 우리 1차 표적 두 대에서 확정된다",
             ref("sim-vs-meas", short=True)),
            ("다음 라운드의 합격규칙을 같은 방식으로 미리 봉인한다",
             "판정이 결과를 보고 조정되지 않았다는 것이 다음 라운드에서도 유지된다",
             ref("decision-matrix", short=True)),
        ]),
    ]


# =========================================================================== #
#  편 29 — sigma-robustness
# =========================================================================== #
def report_29_sigma_robustness():
    return [
        header(
            num=29,
            title="공통모드 σ 오차는 파형 순위를 안 건드리고, 차분 오차가 뒤집는다",
            did="σ 오차를 공통모드와 차분 두 갈래로 나눠 검출거리 R90 순위에 넣고 각각이 순위를 "
                "언제 뒤집는지 쟀다.",
            results=[
                f"기체 {_n('sigma_sens.n_airframes', DER, '{:.0f}')} × 밴드 "
                f"{_n('sigma_sens.n_bands', DER, '{:.0f}')} = "
                f"{_n('sigma_sens.n_cells', DER, '{:.0f}', '셀')} 에서 쟀다.",

                f"공통모드에서 순위는 "
                f"{_n('sigma_sens.offset_min_db', DER, '{:.0f}')}~"
                f"{_n('sigma_sens.offset_max_db', DER, '{:+.0f}', 'dB')} 전 구간 "
                f"{_n('sigma_sens.n_cells', DER, '{:.0f}', '셀')} 에서 그대로다 — 움직이는 것은 "
                f"절대거리뿐이다.",

                f"그 기울기가 σ 1 dB 당 "
                f"{_n('sigma_sens.slope_mean_db_per_db', DER, '{:.3f}', 'dB')}"
                f"({_n('sigma_sens.slope_min_db_per_db', DER, '{:.3f}')}~"
                f"{_n('sigma_sens.slope_max_db_per_db', DER, '{:.3f}')}), 즉 σ ±10 dB 에서 거리 "
                f"{_n('sigma_sens.range_at_minus10_pct', DER, '{:.0f}')} %~"
                f"{_n('sigma_sens.range_at_plus10_pct', DER, '{:+.0f}', '%')} 다.",

                f"자세평균 σ 로 인용하면 다섯 기체가 한 순위"
                f"({_n('sigma_sens.aspect_avg_order', DER)})에 합의하고, 단일자세에서는 순위 "
                f"{_n('sigma_sens.single_aspect_n_orders', DER, '{:.0f}', '종')} 이 나온다.",

                f"거기에 측정 기울기를 얹으면 최악 뒤집힘 문턱이 "
                f"{_n('sigma_sens.worst_flip_aspect_avg_db', DER, '{:.2f}')} → "
                f"{_n('sigma_sens.worst_flip_anchored_db', DER, '{:.2f}', 'dB')} 로 올라간다"
                f"({_n('sigma_sens.anchor_gain_db', DER, '{:+.2f}', 'dB')}).",
            ],
            method=[
                ("두 갈래", "**공통모드**는 한 기체의 세 밴드를 같은 dB 로 옮기고(절대 레벨 오차의 "
                        "모양), **차분**은 밴드마다 다르게 옮긴다(기울기 오차의 모양)"),
                ("무엇에 넣나", "검출거리 R90 — 검출확률 90 % 문턱을 마지막으로 넘는 거리다 "
                           "(`benchmark/sigma_sensitivity.py`)"),
                ("무엇을 보나", "절대거리가 아니라 **세 파형의 순위**가 언제 뒤집히는지를 본다"),
                ("왜 이 축인가", "차분오차가 순위를 정하는 축이고, 그래서 앵커가 잡는 축이 정확히 "
                            "이것이다"),
            ],
            repro=_repro(["PYTHONPATH=src python benchmark/sigma_sensitivity.py"],
                         [SS, DER],
                         "약 20분 (GPU 1장 — 검출 사슬을 오차마다 다시 푼다)",
                         "논문이 절대 σ 에 기대는 곳은 공통모드 문단에서 끝난다"),
        ),

        md("## 오차를 두 갈래로 나눈다", "",
           f"σ 오차를 두 갈래로 나눠 검출거리 R90(검출확률 90 % 문턱을 마지막으로 넘는 거리) 순위에 "
           f"넣었다(`benchmark/sigma_sensitivity.py`, 기체 "
           f"{_n('sigma_sens.n_airframes', DER, '{:.0f}')} × 밴드 "
           f"{_n('sigma_sens.n_bands', DER, '{:.0f}')} = "
           f"{_n('sigma_sens.n_cells', DER, '{:.0f}', '셀')}).", "",
           "**공통모드**는 한 기체의 세 밴드를 같은 dB 로 옮긴다 — 절대 레벨 오차의 모양이다. "
           "**차분**은 밴드마다 다르게 옮긴다 — 기울기 오차의 모양이다."),

        md("## 공통모드 — 절대거리만 움직인다", "",
           f"공통모드에서 순위는 "
           f"{_n('sigma_sens.offset_min_db', DER, '{:.0f}')}~"
           f"{_n('sigma_sens.offset_max_db', DER, '{:+.0f}', 'dB')} 전 구간 "
           f"{_n('sigma_sens.n_cells', DER, '{:.0f}', '셀')} 에서 그대로다 — 움직이는 것은 "
           f"절대거리뿐이고 그 기울기가 σ 1 dB 당 "
           f"{_n('sigma_sens.slope_mean_db_per_db', DER, '{:.3f}', 'dB')}"
           f"({_n('sigma_sens.slope_min_db_per_db', DER, '{:.3f}')}~"
           f"{_n('sigma_sens.slope_max_db_per_db', DER, '{:.3f}')}), 즉 σ ±10 dB 에서 거리 "
           f"{_n('sigma_sens.range_at_minus10_pct', DER, '{:.0f}')} %~"
           f"{_n('sigma_sens.range_at_plus10_pct', DER, '{:+.0f}', '%')} 다.", "",
           "**논문이 절대 σ 에 기대는 곳은 여기서 끝난다.**"),

        md("## 차분 — 순위를 정하는 축", "",
           f"차분오차가 순위를 정하는 축이고, 그래서 {ref('anchor-mode', short=True)} 의 앵커가 잡는 "
           f"축이 정확히 이것이다.", "",
           f"자세평균 σ 로 인용하면 다섯 기체가 한 순위"
           f"({_n('sigma_sens.aspect_avg_order', DER)})에 합의하고(단일자세에서는 순위 "
           f"{_n('sigma_sens.single_aspect_n_orders', DER, '{:.0f}', '종')}), 거기에 측정 기울기를 "
           f"얹으면 최악 뒤집힘 문턱이 "
           f"{_n('sigma_sens.worst_flip_aspect_avg_db', DER, '{:.2f}')} → "
           f"{_n('sigma_sens.worst_flip_anchored_db', DER, '{:.2f}', 'dB')} 로 올라간다"
           f"({_n('sigma_sens.anchor_gain_db', DER, '{:+.2f}', 'dB')})."),

        md("## σ 오차가 어느 축으로 커질 때 순위가 뒤집히는가", "",
           *_fig(1, "report02_f7_sigma_sensitivity",
                 "σ 오차가 어느 축으로 얼마나 커질 때 세 파형의 순위가 뒤집히는가?")),

        md(table_from(f"{DER}:sigma_sens.rows",
                      [("기체", "airframe"), ("최대 치수 [m]", "extent_m"),
                       ("D/λ @LTE", "d_over_lambda_lte"),
                       ("뒤집힘 문턱 · 단일자세 [dB]", "flip_single_db"),
                       ("뒤집힘 문턱 · 자세평균 [dB]", "flip_aspect_avg_db"),
                       ("밴드간 σ 산포 [dB]", "band_sigma_spread_db"),
                       ("P(순위 보존) @1 dB", "p_order_1db")],
                      fmt={"extent_m": "{:.3f}", "d_over_lambda_lte": "{:.2f}",
                           "flip_single_db": "{:.2f}", "flip_aspect_avg_db": "{:.2f}",
                           "band_sigma_spread_db": "{:.1f}", "p_order_1db": "{:.3f}"})),

        md("## 이 표가 사는 주장", "",
           f"뒤집힘 문턱은 기체 크기가 아니라 **로브 산포**가 정한다 — 표에서 최대 치수 열과 "
           f"뒤집힘 문턱 열이 같은 방향으로 가지 않는다. 밴드간 σ 산포 열이 그 순서를 만든다.", "",
           f"⚠ Matrice 4E 행은 {_MESHFIX} 전 값이고, 표 전체가 {_GAMMA_AXIS} 다 — 이 표를 낸 "
           f"`outputs/sigma_sensitivity.json` 가 그 기체의 형상을 먹는다 "
           f"⟨{MFX_ATK} : Q6_invalidated_outputs.critical[3]⟩. 재생성 시 0.1 dB 급 문턱 값은 그 "
           f"이동만으로도 움직인다 — 한 기체 값이 움직여도 이 표가 사는 주장은 그대로 선다."),

        next_steps([
            ("Matrice 4E 를 정정된 메쉬로 다시 넣어 표를 갱신한다",
             "한 행의 값이 현재 형상 위에 선다",
             f"⟨{MFX_ATK} : Q6_invalidated_outputs.critical[3]⟩"),
            ("공통모드 기울기를 검출 결과 편의 σ-free 축과 나란히 읽는다",
             "σ 를 곱하기 전에 이미 순위를 정하는 축이 무엇인지가 확정된다",
             ref("sigma-free-axis", short=True)),
            ("자세평균 인용 규약을 σ 인용 단위로 굳힌다",
             "어느 통계로 인용해야 순위가 서는지가 규약으로 확정된다",
             ref("rank-durability", short=True)),
            ("차분오차의 실제 크기를 실측으로 잰다",
             "뒤집힘 문턱과 실제 오차의 거리가 확정된다",
             ref("session-drift", short=True)),
        ]),
    ]


# =========================================================================== #
REPORTS = [
    ("anchor-mode", report_24_anchor_mode),
    ("anchor-ledger", report_25_anchor_ledger),
    ("blind-p3", report_26_blind_p3),
    ("box-sphere-control", report_27_box_sphere_control),
    ("fleet-prereg", report_28_fleet_prereg),
    ("sigma-robustness", report_29_sigma_robustness),
]


def main() -> int:
    print(f"── 부 5 「앵커와 검증」 — 편 {len(REPORTS)}개 ──")
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
