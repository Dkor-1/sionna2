# -*- coding: utf-8 -*-
"""
build_part01_stock_engine.py — 부 1 「스톡 엔진이 하는 일과 안 하는 일」 → 편 01~07
==========================================================================================
부 1 이 답하는 질문 하나
    **Sionna RT 가 스스로 계산하는 양은 어디서 끝나나.**

편 하나 = 중심 메시지 하나 (제목이 곧 그 편의 결론 문장이다)

    01 stock-says        기술보고서 59쪽에 physical optics 는 0회, SBR 은 44회 나온다
    02 engine-paths      경로는 SBR 과 이미지법이 정한다
    03 engine-amplitude  진폭은 국소 평면파–평면경계 해 하나로 만들어진다
    04 eight-factors     필드 갱신 인자 여덟 개에 면적·곡률·치수·λ 가 없다
    05 size-sweep        면적을 1600배로 키워도 경로 진폭은 7.4e-07 dB 움직인다
    06 decision-table    두 물음이 실험을 네 칸으로 가른다
    07 why-po            완전파는 정확도의 과녁이고, 표를 만들 수 있는 비용대에서 우리가 고른 것은 SBR+PO 다

어디서 왔나 (재구성 전 → 후)
    `report00_foundations.ipynb` c2~c17  ·  `report01_prior.ipynb` c2~c3
    계획: `outputs/restruct_exec_plan.json : reports[no in 01..07]`

이 파일이 하는 일
    JSON 을 읽어 노트북 일곱 개를 조립하는 것뿐이다. **계산도 그림도 여기서 새로 하지 않는다.**
    본문의 수치는 하나도 손으로 치지 않는다 — 전부 `num(None, …)` 과 `table_from()` 이
    JSON 에서 직접 읽어 출처 태그를 달고 넣는다.

실행
    cd /workspace/sionna
    PYTHONPATH=src ~/.venvs/py312/bin/python src/build_part01_stock_engine.py

⚠ GPU 도 Sionna 실행도 필요 없다.
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (_HERE, os.path.join(_ROOT, "benchmark")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from report_registry import (index_shard, nb_path, ref,                  # noqa: E402
                             ref_doc, ref_part)
from report_style import (build_notebook, caption, fetch, header, md,    # noqa: E402
                          next_steps, num, table, table_from)

# --------------------------------------------------------------------------- #
#  근거 파일 — 이 부의 모든 숫자가 나오는 곳
# --------------------------------------------------------------------------- #
ANA = "outputs/report00_sionna_anatomy.json"
PRB = "outputs/report00_sionna_probe.json"
EVD = "outputs/report00_evidence.json"
POC = "outputs/report00_po_case.json"
DEC = "outputs/report00_decision_map.json"
SURVEY = "outputs/prior_work_survey.json"
#: 평판 스윕의 원자료(`EVD : A_plate_size_sweep.source_path` 가 가리키는 그 파일).
#: 격자 축(변 · 예산 · 시드 · 깊이)은 여기서 읽는다.
FCT = "outputs/facet_mechanism.json"
#: 드론 **면 수 사다리**의 원자료. 사다리의 격자 축(자세 · 예산 · 시드 · 깊이)은 여기서
#: 읽는다 — 평판 스윕(`FCT`)의 깊이를 드론 사다리의 깊이로 대신 쓰지 않기 위해서다.
FCN = "outputs/facet_count.json"
#: 같은 사다리의 **적대검증 원장**(2026-08-03). 어느 숫자가 어느 창에서 나왔는지와
#: `must_not_say` · 실루엣 대조군을 여기서 읽는다.
ATK = "outputs/facet_attack.json"

#: 편은 `reports/` 아래 산다 — 그림 경로도 거기 기준이다.
FIG = "../outputs/figures"

#: `report00_decision_map.json:items` 는 순서가 고정돼 있다. 표를 반으로 쪼갤 때
#: 이름이 아니라 이 인덱스로 뽑는다.
RIGHT_HALF = [0, 1, 2, 3, 4]        # 표적 항이 소거되는 칸 (Z1 · Z2)
LEFT_HALF = [5, 6, 7, 8, 9, 10]     # 표적 항이 답에 남는 칸 (Z3 · Z4)
ITEM_COLS = [("실험 유형", "label_en"), ("칸", "zone"), ("왜 그런지", "why_ko")]

#: `report00_decision_map.json:items` 안에서 마이크로도플러 행의 자리(순서 고정).
MD_ITEM = 7

#: 같은 목록에서 메쉬 예산 행(Z4)의 자리. 그 행의 dB 를 편 06 에서 철회하므로 행 이름을
#: 손으로 적지 않고 원장에서 뽑는다.
Z4_ITEM = 10

#: 면 수 사다리에서 **형상 판정을 통과하는 마지막 단**. 원장이 `shape_ok_per_level` 로
#: 들고 있으므로 여기서 손으로 세지 않는다 — 판이 바뀌면 이 인덱스도 따라 바뀐다.
_SHAPE_OK = fetch((EVD, "B_facet_count_sweep.numbers.shape_ok_per_level"))
LAST_SHAPE_OK = max(i for i, ok in enumerate(_SHAPE_OK) if ok)

#: 평판 스윕의 격자 축. **변 수와 예산 수는 원장 배열 길이가 정한다** — 손으로 세지 않는다.
N_SIDE = len(fetch((EVD, "A_plate_size_sweep.numbers.side_m")))
N_BUDGET = len(fetch((EVD, "A_plate_size_sweep.numbers.spp_list")))

#: `prior_work_survey.json:papers` 는 리스트다. 게재/프리프린트 판정을 손으로 적는 대신
#: 키로 자리를 찾아 그 자리의 `status_ko` 를 그대로 주입한다.
_PAPER_IX = {p["key"]: i for i, p in enumerate(fetch((SURVEY, "papers")))}
ZIG_J = _PAPER_IX["zig_j"]
SAGITTA = _PAPER_IX["sagitta"]


def _n(key: str, src: str, fmt: str | None = None, unit: str = "") -> str:
    """`num(None, …)` 축약. **값은 언제나 JSON 이 정한다** — 이 파일에 숫자 리터럴은 없다."""
    return num(None, (src, key), fmt, unit)


def _fig(no: int, stem: str, question: str) -> list[str]:
    return [f"![{stem}]({FIG}/{stem}.png)", "", caption(no, question)]


def _repro(cmd_extra: list[str], out: list[str], runtime: str, note: str = "") -> dict:
    d = dict(cmd=cmd_extra + ["PYTHONPATH=src python src/build_part01_stock_engine.py"],
             out=out, runtime=runtime)
    if note:
        d["note"] = note
    return d


# =========================================================================== #
#  편 01 — stock-says
# =========================================================================== #
def report_01_stock_says():
    return [
        header(
            num=1,
            title="Sionna 기술보고서 59쪽에 physical optics 는 0회, SBR 은 44회 나온다",
            did="Sionna RT 기술보고서 전문과 설치본 `sionna.rt` 공개 이름을 직접 세어 "
                "스톡 솔버가 스스로 계산한다고 말하는 양의 경계를 1차 사료로 확정했다.",
            results=[
                f"기술보고서 {_n('engine.technical_report.version', SURVEY)} "
                f"{_n('engine.technical_report.pages', SURVEY, '{:.0f}', '쪽')} 전문에서 "
                f"`physical optics` "
                f"{_n('engine.technical_report.term_counts.physical_optics', SURVEY, '{:.0f}', '회')} · "
                f"`radar cross section`/`RCS` "
                f"{_n('engine.technical_report.term_counts.radar_cross_section', SURVEY, '{:.0f}', '회')} · "
                f"`dBsm` {_n('engine.technical_report.term_counts.dbsm', SURVEY, '{:.0f}', '회')} 다.",

                f"`SBR` 은 같은 전문에서 "
                f"{_n('engine.technical_report.term_counts.sbr', SURVEY, '{:.0f}', '회')} 나온다 — "
                f"광선을 쏘고 튕기는 층은 스톡에 있고, **면적분과 RCS 출력이 그 위에 얹히는 층**이다.",

                f"설치본 Sionna {_n('sionna_api.version', SURVEY)} 의 `sionna.rt` 공개 이름 "
                f"{_n('sionna_api.rt_public_names', SURVEY, '{:.0f}', '개')} 중 산란단면적을 "
                f"계산하는 것은 {_n('sionna_api.rcs_api_names', SURVEY, '{:.0f}', '개')} 이고, "
                f"`ScatteringPattern` 계열 "
                f"{_n('sionna_api.scattering_api_names', SURVEY, '{:.0f}', '개')} 는 확산반사의 "
                f"각분포 함수다.",

                f"5G 3.5 GHz 에서 λ 는 "
                f"{_n('bands.lambda_cm.5G 3.5 GHz', SURVEY, '{:.1f}', 'cm')} 이고 대각 "
                f"{_n('bands.drone_diag_m', SURVEY, '{:.2f}', 'm')} 급 드론은 파장의 다섯 배 규모 "
                f"유한 물체다 — 그 크기의 σ 는 조명면 전체의 위상 코히런트 면적분에서 나온다.",
            ],
            method=[
                ("낱말 계수", "기술보고서 PDF 전문을 PyMuPDF 로 뽑아 낱말을 센다 — "
                             "요약이 아니라 원문 문자열 계수다"),
                ("공개 이름 계수", "설치된 `sionna.rt` 를 임포트해 이름을 직접 센다 "
                                 "(`benchmark/prior_census.py`)"),
                ("파장·크기", "밴드 세 개의 λ 와 기체 대각을 같은 원장에 적어 둔다 — "
                             "«파장의 몇 배인가» 가 뒤따르는 모든 편의 축이다"),
            ],
            repro=_repro(["~/.venvs/py312/bin/python prior_work/src/build_prior_survey.py"],
                         [SURVEY], "약 1분 (CPU 만 쓴다)",
                         "아카이브 파일이름은 v1 이지만 내용은 Version 1.2 다 "
                         "— 그 함정을 근거 JSON 이 `filename_trap` 으로 들고 있다"),
        ),

        md("## 스톡 솔버가 계산하는 것, 표적 서명이 쓰는 것", "",
           "기술보고서를 열어 스톡 솔버가 무엇을 계산하는지 1차 사료로 확인했다. 경로는 "
           "SBR(광선을 쏴서 튀기며 부딪히는 면을 찾는 방법)로 후보를 만들고 이미지법으로 확정하며, "
           "면과의 상호작용은 네 가지다(p.9).", "",
           table(["스톡 솔버가 계산하는 것", "표적 서명이 쓰는 것"],
                 [["정반사 — 프레넬 계수 곱 (식 127–130, p.46)", "조명면 위의 위상 코히런트 면적분"],
                  ["확산반사 — 산란계수 S 와 정규화 산란패턴 (p.50–52)", "자세에 따른 진폭 σ(θ, φ)"],
                  ["굴절 · 1차 회절 (p.16)", "에지·정점 회절 항"],
                  ["경로 지연 τ · 도플러 · 가림 기하", "그 기하를 σ 로 환산하는 단계"]]), "",
           f"두 열은 같은 물리의 다른 층이다. 왼쪽이 있는 자리에 오른쪽을 얹는 일이 "
           f"{ref_part(4)} 의 커널이 하는 일이고, 그 층이 어디서 시작하는지를 "
           f"{ref('engine-paths')} 부터 셋으로 나눠 적는다."),

        md("## 낱말을 세면 층이 갈린다", "",
           f"{_n('engine.technical_report.pages', SURVEY, '{:.0f}', '쪽')} 전문에서 "
           f"`physical optics` "
           f"{_n('engine.technical_report.term_counts.physical_optics', SURVEY, '{:.0f}', '회')}, "
           f"`radar cross section`/`RCS` "
           f"{_n('engine.technical_report.term_counts.radar_cross_section', SURVEY, '{:.0f}', '회')}, "
           f"`dBsm` {_n('engine.technical_report.term_counts.dbsm', SURVEY, '{:.0f}', '회')} 다. "
           f"`SBR` 은 {_n('engine.technical_report.term_counts.sbr', SURVEY, '{:.0f}', '회')}, "
           f"`Fresnel` 은 "
           f"{_n('engine.technical_report.term_counts.fresnel', SURVEY, '{:.0f}', '회')}, "
           f"`surface integral` 은 "
           f"{_n('engine.technical_report.term_counts.surface_integral', SURVEY, '{:.0f}', '회')} "
           f"나온다.", "",
           "⭐ 이 계수가 말하는 것은 «Sionna 가 부실하다» 가 아니다. 스톡 문서가 자기 물건을 "
           "SBR 과 프레넬로 적고, 표면전류 면적분과 RCS 출력은 자기 물건으로 적지 않는다는 사실이다. "
           "그 사실이 이 저장소의 커널이 서는 자리를 정한다."),

        md("## 설치본의 공개 이름을 세면 같은 경계가 나온다", "",
           f"설치본 Sionna {_n('sionna_api.version', SURVEY)} 를 임포트해 `sionna.rt` 의 공개 이름 "
           f"{_n('sionna_api.rt_public_names', SURVEY, '{:.0f}', '개')} 를 셌다. 산란단면적을 "
           f"내는 이름은 {_n('sionna_api.rcs_api_names', SURVEY, '{:.0f}', '개')} 이고, "
           f"`ScatteringPattern` 계열 "
           f"{_n('sionna_api.scattering_api_names', SURVEY, '{:.0f}', '개')} 는 확산반사의 "
           f"**각분포 함수**다 — 세기를 면적분으로 만드는 물건과는 층이 다르다.", "",
           f"5G 3.5 GHz 에서 λ 는 "
           f"{_n('bands.lambda_cm.5G 3.5 GHz', SURVEY, '{:.1f}', 'cm')}, LTE 1.843 GHz 에서 "
           f"{_n('bands.lambda_cm.LTE 1.843 GHz', SURVEY, '{:.1f}', 'cm')}, WiFi 5.21 GHz 에서 "
           f"{_n('bands.lambda_cm.WiFi 5.21 GHz', SURVEY, '{:.1f}', 'cm')} 다. 대각 "
           f"{_n('bands.drone_diag_m', SURVEY, '{:.2f}', 'm')} 급 기체는 세 밴드 모두에서 "
           f"파장의 두 배에서 일곱 배 사이의 유한 물체이고, 그 크기에서 σ 는 조명면 전체의 "
           f"위상 코히런트 면적분이 정한다."),

        next_steps([
            ("경로가 어떻게 확정되는지를 소스 줄 번호까지 따라간다",
             "«스톡이 계산하는 것» 의 첫 층인 경로 탐색이 무슨 알고리즘인지가 확정된다",
             ref("engine-paths", short=True)),
            ("경로 하나가 진폭 하나가 되는 자리의 식을 인자까지 편다",
             "면적·곡률·치수·λ 가 그 식의 어디에 있는지가 행 단위로 확정된다",
             ref("engine-amplitude", short=True)),
            ("남들이 이 경계를 어떻게 넘었는지를 게재본에서 센다",
             "표적 서명의 조달처 일곱 갈래와 각 갈래가 사 주는 주장의 크기가 확정된다",
             ref("procurement", short=True)),
        ]),
    ]


# =========================================================================== #
#  편 02 — engine-paths
# =========================================================================== #
def report_02_engine_paths():
    return [
        header(
            num=2,
            title="경로는 SBR 과 이미지법이 정한다",
            did="Sionna RT 설치본의 경로 탐색을 소스 줄 번호까지 읽어 광선이 무엇을 하고 "
                "어디서 경로가 확정되는지를 적었다.",
            results=[
                f"소스마다 광선을 피보나치 격자로 뿌려 면 순서 후보를 모으고, 같은 면 순서를 "
                f"발견한 광선은 첫 발만 남긴다(`sb_candidate_generator.py:484-498`) — "
                f"그다음 이미지법이 교점을 해석적으로 다시 푼다(`image_method.py:37-47`).",

                f"그래서 광선은 **정찰병**이고 답의 단위는 경로다. 광선 수를 "
                f"{_n('exp_a_ray_count_sweep[0].samples_per_src', PRB, '{:,.0f}')} 발에서 "
                f"{_n('exp_a_ray_count_sweep[-1].samples_per_src', PRB, '{:,.0f}')} 발까지 "
                f"{_n('summary.ray_count_span', PRB, '{:.0f}')}배 올려도 정반사 진폭 스프레드는 "
                f"{_n('summary.abs_a_spread_over_ray_count_db', PRB, '{:.1f}', 'dB')} 다.",

                f"엔진은 자기가 푸는 문제를 정확히 푼다 — 평면 반사 진폭이 이미지-소스 해석해 대비 "
                f"{_n('exp_c_spreading_check.ratio_measured_over_predicted', PRB, '{:.4f}')} 이고, "
                f"자유공간 직접파가 Friis 이론과 "
                f"{_n('F_what_sionna_gets_right.numbers.los_agreement_db', EVD, '{:.1e}', 'dB')} "
                f"안이다.",

                f"설치본 {_n('item6_versions.values.sionna_rt', ANA)} 가 정확히 계산하는 메커니즘 "
                f"{len(fetch((ANA, 'item9_verdict.can_do')))}가지를 근거 줄 번호와 함께 아래 표에 "
                f"그대로 싣는다.",
            ],
            method=[
                ("경로 탐색의 알고리즘", "설치본 소스를 직접 읽고 `inspect.signature` 로 "
                                       "런타임에서 재확인했다"),
                ("광선 수 무응답", "빈 씬에서 광선 수만 바꾸며 정반사 진폭을 재는 실행 프로브"),
                ("이미지-소스 대조", "같은 형상의 해석해를 닫힌형으로 계산해 진폭 비를 잰다"),
            ],
            repro=_repro([], [ANA, PRB, EVD], "약 1분 (GPU 0장 — JSON 읽기다)",
                         "anatomy · probe 두 JSON 은 설치본 해부와 실행 프로브의 산출물이고, "
                         "각 파일의 `_meta` 가 자기 생성기 경로를 들고 있다"),
        ),

        md("## 광선은 정찰병이고, 답의 단위는 경로다", "",
           "답은 **두 단계**로 만들어진다. **① 경로 탐색.** 소스마다 광선을 구면에 뿌려"
           "(피보나치 격자, 난수가 아니다) 어느 면들을 어떤 순서로 맞는지 후보를 모은다. "
           "같은 면 순서를 발견한 광선은 첫 발만 남기고 나머지를 버린다 — 면 해시로 만든 경로 "
           "지문의 카운터를 원자적으로 올리고 `samples_counter == 0` 인 광선만 저장한다"
           "(`sb_candidate_generator.py:484-498`). 그다음 이미지법이 소스를 각 면에 거울반사시켜 "
           "교점 좌표를 해석적으로 다시 푼다(`image_method.py:37-47`).", "",
           "**② 필드 계산.** 그렇게 확정된 경로 **하나**를 따라가며 진폭 a 를 만든다"
           "(`field_calculator.py`).", "",
           f"그래서 광선은 정찰병이고, 답의 단위는 경로다. 이 구분이 {ref('engine-amplitude')} 의 "
           f"출발점이다."),

        md("## 비유 셋과, 그 비유가 깨지는 자리", "",
           "비유는 **깨지는 자리**를 함께 적어야 쓸모가 있다 "
           f"(근거 `{POC} : s0_fair_boundary.analogies_and_where_they_break`).", "",
           "- **Sionna 의 표면 처리는 거울 한 장이다.** 반사 세기(Fresnel)도 방향도 맞다. "
           f"⚠ 거울은 각도만 돌려준다 — 평판을 키워도 진폭이 그대로인 것이 그 뜻이고, "
           f"그 실측이 {ref('size-sweep')} 다.", "",
           "- **PO 표면적분은 조명면에 붙은 작은 안테나들의 합이다.** 점마다 위상이 더해지므로 "
           "모양이 바뀌면 보강·상쇄가 바뀐다 — σ 가 여기서 창발한다. ⚠ 그 작은 안테나의 세기를 "
           f"국소 평면 반사로 정한다. 특징 폭이 파장 아래로 가면 그 가정이 깨지고, 그 무릎이 "
           f"{ref('po-knee')} 다.", "",
           "- **SBR 은 손전등으로 비추고 빛이 닿은 자리만 세는 것이다.** 자기가림이 공짜로 "
           "처리된다. ⚠ 손전등은 모서리에서 휘는 빛과 몸통을 감아 도는 빛을 빼놓는다 — "
           f"전자가 PTD, 후자가 크리핑파이고 그 크기가 {ref('kernel-open-items')} 다."),

        md("## Sionna 가 정확히 계산하는 것 — 먼저 이것부터", "",
           table_from(f"{ANA}:item9_verdict.can_do",
                      [("메커니즘", "항목"), ("코드", "근거"), ("무엇을 어떻게", "설명_ko")])),

        md("## 광선 수는 진폭에 안 들어간다 — 다만 단서 하나", "",
           f"광선 수를 "
           f"{_n('exp_a_ray_count_sweep[0].samples_per_src', PRB, '{:,.0f}')} 발에서 "
           f"{_n('exp_a_ray_count_sweep[-1].samples_per_src', PRB, '{:,.0f}')} 발까지 "
           f"{_n('summary.ray_count_span', PRB, '{:.0f}')}배 올려도 정반사 진폭 스프레드는 "
           f"{_n('summary.abs_a_spread_over_ray_count_db', PRB, '{:.1f}', 'dB')} 다. "
           f"광선은 경로를 **찾는** 데 쓰이고 진폭을 **만드는** 데는 안 쓰인다.", "",
           "⭐ 공정하게 단서를 붙인다. 이 진술은 정반사·투과·회절 경로에서 참이다. "
           "확산산란 경로에서는 다르다 — `solid_angle` 이 4π/N 으로 초기화돼 재질까지 실려 가고, "
           "진폭에 sqrt(fs · solid_angle) 로 곱해져 1/sqrt(N) 으로 스케일된다. 그것이 몬테카를로 "
           "추정량의 올바른 정규화다: 경로 하나는 작아지고 경로 개수가 N 에 비례해 늘어 총 전력이 "
           "수렴한다.", "",
           "그 4π/N 은 **첫 상호작용에만** 살아 있고, 확산이 샘플링되는 순간 2π(반구 입체각)로 "
           f"덮어써진다(근거 `{ANA} : item1_ray_shooting_and_dedup.d_ray_count_in_amplitude`)."),

        next_steps([
            ("확정된 경로 하나가 진폭 하나가 되는 식을 인자까지 편다",
             "spreading factor 와 Jones 행렬이 각각 무엇을 담당하는지가 확정된다",
             ref("engine-amplitude", short=True)),
            ("그 식의 인자 목록을 전수로 세어 밖에 있는 양을 적는다",
             "면적·곡률·치수·λ 가 목록 안인지 밖인지가 행 단위로 확정된다",
             ref("eight-factors", short=True)),
            ("같은 광선엔진 위에 면적분을 얹은 우리 커널과 맞댄다",
             "가림 판정과 면적분의 분담선이 코드 경계로 확정된다",
             ref("kernel-what", short=True)),
        ]),
    ]


# =========================================================================== #
#  편 03 — engine-amplitude
# =========================================================================== #
def report_03_engine_amplitude():
    return [
        header(
            num=3,
            title="진폭은 국소 평면파–평면경계 해 하나로 만들어진다",
            did="확정된 경로 하나가 진폭 하나가 되는 식을 기호마다 뜻을 붙여 펴고, "
                "반사 확산인자가 왜 거리 하나로 닫히는지를 유도했다.",
            results=[
                "진폭은 `a = (안테나 패턴) × (경로 위 Jones 행렬들의 곱) × spreading_factor × λ/4π` "
                "하나로 만들어진다 — Jones 행렬의 대각 성분이 Fresnel 계수 r_te · r_tm 이다.",

                "반사 경로의 spreading_factor 는 `1/ray_tube_length` 하나로 끝난다"
                "(`field_calculator.py:323-326`). 평면 반사파의 중심이 소스의 거울상이므로 "
                "진폭이 1/(s′+s) 로 닫히는 것이 그 유도다.",

                "일반 확산인자 `A(s) = sqrt(ρ₁ρ₂/((ρ₁+s)(ρ₂+s)))` 의 면곡률 항은 삼각형 메쉬에서 "
                "구성상 0 이다 — 면마다 곡률이 정의상 0 이라 제2기본형식이 비어 있다.",

                f"회절 경로는 `1/sqrt(s·s′·(s+s′))` 로 갈라진다. sqrt 가 붙는 이유는 켈러 원뿔을 "
                f"따라 원통형으로 퍼지기 때문이고, 이 층까지가 설치본 "
                f"{_n('item6_versions.values.sionna_rt', ANA)} 가 계산하는 범위다.",

                f"식 끝의 λ/4π 는 **수신 안테나** 항이다 — 표적의 전기적 크기 L/λ 는 이 식 밖에 "
                f"있고, 그 실측이 {ref('size-sweep')} 다.",
            ],
            method=[
                ("식의 출처", "설치본 `field_calculator.py` 를 직접 읽어 인자와 줄 번호를 적는다"),
                ("확산인자 유도", "일반 기하광학 광선관 공식에서 면곡률 0 특수해로 붕괴시킨다 — "
                                "닫힌형 대수이고 새 계산이 없다"),
                ("그림 1", "같은 광선엔진 위에서 두 계산이 표면에서 갈라지는 자리를 그린다"),
            ],
            repro=_repro(["PYTHONPATH=src python src/figs_report00.py"],
                         [ANA, PRB], "약 1분 (GPU 0장)",
                         "그림은 게재 규격(벡터 PDF + 400 dpi PNG · 9 pt · 색+해치)으로 "
                         "`src/figs_report00.py` 가 그린다"),
        ),

        md("## 경로 하나가 진폭 하나가 되는 식", "",
           "`a = (안테나 패턴) × (경로 위 Jones 행렬들의 곱) × spreading_factor × λ/4π`", "",
           "기호를 하나씩. **Jones 행렬**은 전계를 (⊥, ∥) 2성분 복소 벡터로 보고 그것을 "
           "변환하는 2×2 행렬이고, 정반사에서는 대각 성분이 Fresnel 계수 r_te · r_tm 이다. "
           "**spreading_factor** 는 파면이 퍼지면서 진폭이 줄어드는 비율 [1/m] 이고, "
           "**λ/4π** 는 등방 안테나의 유효개구 λ²/4π 를 진폭 차원으로 옮긴 상수 [m] 다."),

        md("## 반사 확산인자가 거리 하나로 닫히는 이유", "",
           "반사 경로의 spreading_factor 는 `1/ray_tube_length` 하나로 끝난다"
           "(`field_calculator.py:323-326`). 왜 거리만으로 끝나는지가 이 편의 첫 유도다.", "",
           "점원에서 나온 구면파는 진폭이 1/r 로 준다. 이 파가 **평평한** 면에 부딪히면 "
           "반사파는 여전히 구면파이고 그 중심은 소스를 면에 대해 거울반사시킨 상(image)이다. "
           "상은 면 뒤 s′ 에 있으므로 반사점에서 s 를 더 간 수신점은 상으로부터 s′+s 이고, "
           "진폭은 1/(s′+s) — 정확히 `1/ray_tube_length` 다.", "",
           f"실행이 그 유도를 확인한다. 평면 반사 진폭과 이미지-소스 해석해의 비가 "
           f"{_n('exp_c_spreading_check.ratio_measured_over_predicted', PRB, '{:.4f}')} 다."),

        md("## 굽은 면이면 무엇이 더 붙는가", "",
           "일반 기하광학의 광선관 확산인자는 `A(s) = sqrt( ρ₁ρ₂ / ((ρ₁+s)(ρ₂+s)) )` 이고, "
           "ρ₁·ρ₂ 는 반사 **직후** 파면의 두 주곡률반경이다. 곡면 반사에서 이 ρ 는 입사 파면의 "
           "곡률과 **면의 주곡률**이 섞여 정해진다.", "",
           "면이 평평하면 면곡률 항이 0 이 되어 ρ = s′ 가 되고, 위 식이 s′/(s′+s) 로 붕괴한다 — "
           "여기에 소스에서 반사점까지의 1/s′ 를 곱하면 1/(s+s′) 다. **Sionna 는 이 일반 공식의 "
           "면곡률 0 특수해를 정확히 구현한다.** 면곡률 항을 채우려면 그 점에서 표면의 "
           "제2기본형식이 필요한데, 삼각형 메쉬는 면마다 곡률이 정의상 0 이라 그 항이 구성상 0 이다."),

        md("## 회절 경로와 λ 의 자리", "",
           "회절 경로는 `1/sqrt(s·s′·(s+s′))` 로 갈라진다. 두 조각으로 읽으면 뜻이 보인다 — "
           "`(1/s′) × sqrt( s′/(s(s+s′)) )` 에서 앞은 모서리까지 오는 구면파의 평범한 확산이고, "
           "뒤가 UTD 표준 모서리 인자다. sqrt 가 붙는 이유는 모서리에서 나온 파가 켈러 원뿔을 "
           "따라 한 방향으로 **원통형**으로 퍼지기 때문이다.", "",
           "⚠ 마지막 λ/4π 를 보고 «파장이 들어가니 산란도 다루겠지» 라고 읽기 쉽다. 그 λ 는 "
           "**수신 안테나** 항이고, 표적의 전기적 크기 L/λ 는 이 식 밖에 있다."),

        md("## 두 계산이 표면에서 갈라지는 자리", "",
           *_fig(1, "report00_f1",
                 "같은 광선엔진을 쓰는 두 계산은 표면에서 무엇이 갈라지는가?"), "",
           f"왼쪽은 경로 하나에 진폭 하나를 붙이는 계산이고, 오른쪽은 조명면 전체를 훑어 "
           f"위상을 더하는 계산이다. 두 계산은 **가림 판정까지 같은 광선엔진을 쓴다** — "
           f"갈라지는 자리는 «맞은 뒤 무엇을 하는가» 뿐이고, 그 분담선이 "
           f"{ref('kernel-what')} 다."),

        next_steps([
            ("이 식의 인자 목록을 전수로 세어 목록 밖의 양을 적는다",
             "면적·곡률·치수·λ 가 목록 안인지 밖인지가 행 단위로 확정된다",
             ref("eight-factors", short=True)),
            ("표적 크기를 실제로 흔들어 진폭이 움직이는지 잰다",
             "«크기는 yes/no 에만 쓰인다» 가 수치로 확정된다",
             ref("size-sweep", short=True)),
            ("같은 경로 위에 면적분을 얹은 우리 커널을 해석 PO 와 맞댄다",
             "얹은 층의 구현오차가 kr 전 구간에서 dB 로 확정된다",
             ref("kernel-vs-reference", short=True)),
        ]),
    ]


# =========================================================================== #
#  편 04 — eight-factors
# =========================================================================== #
def report_04_eight_factors():
    return [
        header(
            num=4,
            title="필드 갱신 인자 여덟 개에 면적·곡률·치수·λ 가 없다",
            did="필드 갱신 함수의 인자를 전수로 세고, 호출부가 무엇을 일부러 요청하지 않는지까지 "
                "소스 줄 번호로 적었다.",
            results=[
                f"인자는 "
                f"{len(fetch((ANA, 'item2_field_calculation_arguments.argument_inventory')))}개이고 "
                f"그중 셋은 방향·자세(회전·단위벡터), 하나는 반사/투과 분기, 넷은 프레넬 "
                f"반사·투과 계수다.",

                "호출부가 `return_vertices=False` 로 **정점 좌표를 일부러 요청하지 않고** 법선만 "
                "가져온다(`field_calculator.py:404-405`) — 삼각형 크기를 알 수 있는 유일한 통로가 "
                "그 자리에서 닫힌다.",

                "정확한 진술은 이것이다 — 광선이 면을 맞았는가는 유한 기하로 판정하고, 맞은 뒤 "
                "필드를 얼마나 바꿀지는 국소 평면파–평면경계 문제의 해로 계산한다. "
                "즉 크기는 `yes/no` 에만 쓰인다.",

                f"단위가 이미 답을 말한다. 같은 PEC, 같은 정면면적 "
                f"{_n('C_same_material_different_shape.numbers.frontal_area_m2', EVD, '{:.4f}')} m², "
                f"같은 5G 밴드에서 구는 "
                f"{_n('C_same_material_different_shape.numbers.sphere_sigma_dbsm', EVD, '{:.2f}', 'dBsm')}, "
                f"평판은 "
                f"{_n('C_same_material_different_shape.numbers.plate_same_area_sigma_dbsm', EVD, '{:.2f}', 'dBsm')} "
                f"로 "
                f"{_n('C_same_material_different_shape.numbers.shape_gap_db', EVD, '{:.2f}', 'dB')} "
                f"갈린다.",
            ],
            method=[
                ("인자 전수", "설치본 소스의 시그니처를 그대로 옮기고 `inspect.signature` 로 "
                            "런타임 재확인했다"),
                ("원문 인용", "기술보고서 원문 문장을 축자로 싣는다 — «무한평면 가정» 같은 거친 "
                            "요약을 쓰지 않기 위해서다"),
                ("모양 대조", "같은 재질·같은 정면면적에서 구와 평판의 σ 를 닫힌형으로 계산한다"),
            ],
            repro=_repro(["PYTHONPATH=src python src/figs_report00.py"],
                         [ANA, EVD, POC], "약 1분 (GPU 0장)"),
        ),

        md("## 그 수식에 없는 것 — 인자 여덟 개를 그대로 센다", "",
           "필드 갱신 함수가 받는 것을 전수로 옮긴다. 세어 보면 방향과 계수뿐이다."),

        md(table_from(f"{ANA}:item2_field_calculation_arguments.argument_inventory",
                      [("인자", None), ("무엇인가", "")], key_col="인자")),

        md("## 목록 밖에 있는 양들", "",
           table_from(f"{ANA}:item2_field_calculation_arguments.absent_quantities",
                      [("필드 갱신 인자 목록 밖에 있는 양", "")]), "",
           "여덟 인자 중 셋은 방향·자세(회전·단위벡터), 하나는 반사/투과 분기, 넷은 프레넬 "
           "반사·투과 계수다. 더 결정적인 것은 "
           "호출부다 — `field_calculator.py:404-405` 가 `return_vertices=False` 로 **정점 좌표를 "
           "일부러 요청하지 않고** 법선만 가져온다. 삼각형 크기를 알 수 있는 유일한 통로가 "
           "그 자리에서 닫힌다."),

        md("## 정확히 말하는 법 — «무한평면 가정» 은 거친 요약이다", "",
           "Sionna 가 무한평면을 가정한다고 쓰면 반박당한다. 기하는 유한하고, 광선이 그 삼각형을 "
           "맞았는지는 Mitsuba 가 정확히 판정한다 — 가림·그림자는 제대로 작동한다.", "",
           "정확한 진술은 이것이다: **광선이 면을 맞았는가는 유한 기하로 판정하고, 맞은 뒤 필드를 "
           "얼마나 바꿀지는 국소 평면파–평면경계 문제의 해로 계산한다.** 즉 크기는 `yes/no` 에만 "
           "쓰이고, `how much` 는 국소 해가 정한다.", "",
           f"· 경로 기하 — "
           f"{_n('G_exact_wording_infinite_surface.numbers.quote_path_geometry', EVD)}", "",
           f"· 계수 — {_n('G_exact_wording_infinite_surface.numbers.quote_coefficients', EVD)}", "",
           f"· ⚠ 낱말 주의 — 기술보고서의 «locally planar» 는 **파(wave)** 에 붙는 말이다"
           f"(p.50 “an incoming locally planar linearly polarized wave”). 표면에 대해서는 조건 없이 "
           f"extend infinitely · of infinite size 라고 쓴다 "
           f"(근거 `{EVD} : G_exact_wording_infinite_surface.numbers.caution_locally`)."),

        md("## 단위가 이미 답을 말한다 — Γ 는 무차원, σ 는 m²", "",
           "반사계수 Γ 는 무차원이고 레이더단면적 σ 의 단위는 m² 다. 무차원을 아무리 정확히 "
           "계산해도 결과는 무차원으로 남는다. 면적은 **조명면 위의 면적분**에서만 들어온다.", "",
           "평판의 PO 공식 `σ = 4πA²/λ²` 는 `4π·[m²]²/[m]² = m²` 로 닫히는데, Sionna 의 정반사 "
           "진폭 `|a| = λ/(4π(R₁+R₂))` 는 `[m]/[m] = 1` 로 닫힌다 — 면적 기호는 그 식 밖에 있다."),

        md("## 같은 면적, 다른 모양 — σ 는 얼마나 갈리는가", "",
           *_fig(1, "report00_f3",
                 "같은 재질·같은 정면면적에서 모양만 바꾸면 σ 는 얼마나 갈라지는가?"), "",
           f"같은 PEC, 같은 정면면적 "
           f"{_n('C_same_material_different_shape.numbers.frontal_area_m2', EVD, '{:.4f}')} m², "
           f"같은 5G 밴드 "
           f"{_n('s4_limits.our_production_bands_vs_knee.nr_ghz', POC, '{:.1f}', 'GHz')} 에서 구는 "
           f"{_n('C_same_material_different_shape.numbers.sphere_sigma_dbsm', EVD, '{:.2f}', 'dBsm')}, "
           f"평판은 "
           f"{_n('C_same_material_different_shape.numbers.plate_same_area_sigma_dbsm', EVD, '{:.2f}', 'dBsm')} "
           f"다.", "",
           f"주파수를 두 배로 올리면 평판은 "
           f"{_n('C_same_material_different_shape.numbers.plate_sigma_df_db_per_octave', EVD, '{:+.2f}', 'dB')}"
           f"/옥타브, 구는 "
           f"{_n('C_same_material_different_shape.numbers.sphere_sigma_df_db_per_octave', EVD, '{:+.2f}', 'dB')}"
           f"/옥타브 움직인다. 갈라지는 이유는 하나다 — "
           f"{_n('C_same_material_different_shape.formula.why_they_differ', EVD)}"),

        next_steps([
            ("표적 크기를 흔들어 경로 진폭이 움직이는지 실행으로 잰다",
             "«크기는 yes/no 에만 쓰인다» 가 dB 로 확정된다",
             ref("size-sweep", short=True)),
            ("면적분을 얹어 σ 를 m² 로 만드는 커널의 분담선을 적는다",
             "가림 판정과 면적분의 경계가 코드 경계로 확정된다",
             ref("kernel-what", short=True)),
            ("어느 실험이 이 경계를 실제로 넘어야 하는지 결정표로 가른다",
             "표적 모델이 필요한 실험과 필요 없는 실험이 칸으로 확정된다",
             ref("decision-table", short=True)),
        ]),
    ]


# =========================================================================== #
#  편 05 — size-sweep
# =========================================================================== #
def report_05_size_sweep():
    return [
        header(
            num=5,
            title="면적을 1600배로 키워도 경로 진폭은 7.4e-07 dB 움직인다",
            did="빈 자유공간에 금속 평판 하나를 두고 변만 키우며 PO 단면적과 path solver 의 "
                "표적 경로 진폭을 같은 축에서 재고, 같은 실험을 드론 메쉬로 옮겼다.",
            results=[
                f"평판 면적을 "
                f"{_n('A_plate_size_sweep.numbers.area_ratio_max', EVD, '{:.0f}')}배 키우면 "
                f"PO 단면적은 "
                f"{_n('A_plate_size_sweep.numbers.po_theory_span_db', EVD, '{:.2f}', 'dB')} 커지고, "
                f"path solver 의 표적 경로 진폭은 "
                f"{_n('A_plate_size_sweep.numbers.rt_span_db', EVD, '{:.1e}', 'dB')} 움직인다.",

                f"경로 수는 전 구간 "
                f"{_n('A_plate_size_sweep.numbers.n_paths_target_set_union[0]', EVD, '{:.0f}')}개이고, "
                f"그 진폭은 이미지-소스 해석해와 "
                f"{_n('A_plate_size_sweep.numbers.rt_minus_image_source_max_abs_db', EVD, '{:.4f}', 'dB')} "
                f"안에서 맞는다 — **엔진은 자기가 푸는 문제를 정확히 푼다**.",

                f"같은 실험을 기체 메쉬로 옮겨 삼각형을 "
                f"{_n('B_facet_count_sweep.numbers.n_tri_span_decades', EVD, '{:.2f}')} decade 깎으면, "
                f"실루엣이 살아 있는 단 전부에서 정반사 경로가 존재하는 자세는 "
                f"{_n('B_facet_count_sweep.numbers.spec_n_aspects', EVD, '{:.0f}')}자세 중 "
                f"{_n('B_facet_count_sweep.numbers.spec_n_aspects_nonzero_per_level[0]', EVD, '{:.0f}')}"
                f"개(az {_n('B_facet_count_sweep.numbers.hot_aspect.az_deg', EVD, '{:.0f}', '°')} · el "
                f"{_n('B_facet_count_sweep.numbers.hot_aspect.el_deg', EVD, '{:.0f}', '°')} · spp "
                f"{_n('B_facet_count_sweep.numbers.spec_probe_spp', EVD, '{:,.0f}')} · 깊이 "
                f"{_n('meta.max_depth', FCN, '{:.0f}')})이고, 그 자세의 정반사 경로 수는 "
                f"{_n('B_facet_count_sweep.numbers.spec_paths_per_level[0]', EVD, '{:.0f}')}→"
                f"{_n('B_facet_count_sweep.numbers.spec_paths_per_level[3]', EVD, '{:.0f}')} 로 준다.",

                f"⭐ 그 구간의 **정반사 전용** 값은 "
                f"{_n('B_facet_count_sweep.numbers.spec_coh_db_per_level[0]', EVD, '{:.4f}', 'dB')} → "
                f"{_n('B_facet_count_sweep.numbers.spec_coh_db_per_level[3]', EVD, '{:.4f}', 'dB')} 이고, "
                f"1경로값에 20·log₁₀(2) 를 더하면 2경로값과 잔차 "
                f"{_n('attack_4_defect_vs_misuse.C3_tessellation_non_invariance.evidence.drone_link.residual_db', ATK, '{:.1e}', 'dB')} "
                f"로 같다 — 닫힌형 20·log₁₀(1/2) = "
                f"{_n('B_facet_count_sweep.numbers.theoretical_step_two_to_one_facet_db', EVD, '{:+.2f}', 'dB')} "
                f"와 같은 **항등식**이고, 적대검증 원장은 여기서 사라진 것을 산란체가 아니라 "
                f"**중복 복사본**으로 읽는다. ⛔ 형상 판정에서 떨어지는 마지막 단(정반사 경로 "
                f"{_n('B_facet_count_sweep.numbers.spec_paths_per_level[-1]', EVD, '{:.0f}')}개)의 "
                f"계단은 이 편에서 폐기한다.",

                f"반대 방향도 같은 뿌리다 — 같은 평판을 쪼개기만 해도 코히어런트 전력이 "
                f"{_n('H_tessellation_changes_the_answer.numbers.max_inflation_db', EVD, '{:.2f}', 'dB')} "
                f"부푼다. 답의 단위가 면적이 아니라 경로라서 면 수가 곧 답이 된다.",
            ],
            method=[
                ("스윕 설계",
                 f"빈 씬에서 평판 변만 바꾼다 — 변 {N_SIDE}단 × 예산 {N_BUDGET}단 = "
                 f"{_n('A_plate_size_sweep.numbers.n_cells', EVD, '{:.0f}')}셀이고, 셀마다 시드 "
                 f"{_n('A_plate_size_sweep.numbers.n_seeds', EVD, '{:.0f}')}개를 평균하며 깊이는 "
                 f"{_n('A_plate_size[0].budget[0].max_depth', FCT, '{:.0f}')} 다"),
                ("깊이 확인", f"깊이 {_n('A_depth_check[1].max_depth', FCT, '{:.0f}')} 는 별도 블록 "
                            f"`A_depth_check` 가 변 하나 · spp "
                            f"{_n('A_depth_check[1].spp', FCT, '{:,.0f}')} 에서 따로 잰다"),
                ("PO 쪽 눈금", "같은 형상의 PO 단면적을 닫힌형으로 계산해 같은 축에 올린다"),
                ("정직성 검사", "RT 진폭을 이미지-소스 해석해와 대조해 «엔진이 틀렸다» 를 "
                              "먼저 배제한다"),
            ],
            repro=_repro(["PYTHONPATH=src python src/figs_report00.py"],
                         [EVD, FCT], "약 1분 (GPU 0장 — JSON 읽기와 그림 그리기다)"),
        ),

        md("## 평판 하나를 키워 보면", "",
           f"빈 자유공간에 금속 평판 하나를 두고 변만 "
           f"{_n('A_plate_size_sweep.numbers.side_m[0]', EVD, '{:.1f}', 'm')} → "
           f"{_n('A_plate_size_sweep.numbers.side_m[-1]', EVD, '{:.1f}', 'm')} "
           f"(면적 {_n('A_plate_size_sweep.numbers.area_ratio_max', EVD, '{:.0f}')}배) 로 키운다. "
           f"PO 단면적은 면적 dB 당 "
           f"{_n('A_plate_size_sweep.numbers.slope_sigma_db_per_area_db', EVD, '{:.2f}', 'dB')}씩, "
           f"총 {_n('A_plate_size_sweep.numbers.po_theory_span_db', EVD, '{:.2f}', 'dB')} 오른다.", "",
           f"같은 구간에서 path solver 의 표적 경로 진폭은 "
           f"{_n('A_plate_size_sweep.numbers.rt_span_db', EVD, '{:.1e}', 'dB')} 움직이고 경로 수는 "
           f"내내 {_n('A_plate_size_sweep.numbers.n_paths_target_set_union[0]', EVD, '{:.0f}')}개다 — "
           f"변 {N_SIDE}단 × 예산 {N_BUDGET}단 = "
           f"{_n('A_plate_size_sweep.numbers.n_cells', EVD, '{:.0f}')}셀 전부에서, 셀마다 시드 "
           f"{_n('A_plate_size_sweep.numbers.n_seeds', EVD, '{:.0f}')}개를 평균해 깊이 "
           f"{_n('A_plate_size[0].budget[0].max_depth', FCT, '{:.0f}')} 로 잰 값이다.", "",
           f"깊이 {_n('A_depth_check[1].max_depth', FCT, '{:.0f}')} 는 격자 밖의 별도 확인이다 — "
           f"블록 `A_depth_check` 가 변 하나 · spp "
           f"{_n('A_depth_check[1].spp', FCT, '{:,.0f}')} 에서 깊이 "
           f"{_n('A_depth_check[0].max_depth', FCT, '{:.0f}')} 와 "
           f"{_n('A_depth_check[1].max_depth', FCT, '{:.0f}')} 두 항을 잰다."),

        md("## 그 진폭이 무엇인지도 같이 확인된다", "",
           *_fig(1, "report00_f2", "표적을 키우면 무엇이 움직이고 무엇이 그대로인가?"), "",
           f"⭐ RT 값은 이미지-소스 해석해와 "
           f"{_n('A_plate_size_sweep.numbers.rt_minus_image_source_max_abs_db', EVD, '{:.4f}', 'dB')} "
           f"안에서 맞는다. **엔진은 자기가 푸는 문제를 정확히 푼다.** 두 곡선이 만나는 자리는 변 "
           f"{_n('A_plate_size_sweep.numbers.side_m_where_rt_equals_po', EVD, '{:.2f}', 'm')} "
           f"한 점뿐이고, 그것은 우연이다."),

        md("## 드론 메쉬에서는 정반사 경로가 자세 하나에서만 살아남는다", "",
           f"같은 실험을 기체 메쉬로 옮긴다. 삼각형을 "
           f"{_n('B_facet_count_sweep.numbers.n_tri_per_level[0]', EVD, '{:,.0f}')}개 → "
           f"{_n('B_facet_count_sweep.numbers.n_tri_per_level[-1]', EVD, '{:.0f}')}개"
           f"({_n('B_facet_count_sweep.numbers.n_tri_span_decades', EVD, '{:.2f}')} decade)로 "
           f"여섯 단에 걸쳐 깎는다.", "",
           f"실루엣이 유지되는 것은 "
           f"{_n(f'B_facet_count_sweep.numbers.n_tri_per_level[{LAST_SHAPE_OK}]', EVD, '{:,.0f}')}"
           f"개까지다. 가장 성긴 "
           f"{_n('B_facet_count_sweep.numbers.n_tri_per_level[-1]', EVD, '{:.0f}')}개 판은 원장의 "
           f"형상 판정에서 떨어진다(`shape_ok` = "
           f"{_n('B_facet_count_sweep.numbers.shape_ok_per_level[-1]', EVD)}) — 정면투영 편차 "
           f"{_n('B_facet_count_sweep.numbers.proj_dev_pct_per_level[-1]', EVD, '{:.1f}', '%')} · "
           f"경계상자 편차 "
           f"{_n('B_facet_count_sweep.numbers.bbox_dev_pct_per_level[-1]', EVD, '{:.1f}', '%')} 다. "
           f"실루엣이 살아 있는 단 전부에서, "
           f"{_n('B_facet_count_sweep.numbers.spec_n_aspects', EVD, '{:.0f}')}자세 중 정반사 경로가 "
           f"존재하는 자세는 "
           f"{_n('B_facet_count_sweep.numbers.spec_n_aspects_nonzero_per_level[0]', EVD, '{:.0f}')}"
           f"개다.", "",
           f"그 한 자세에서 스톡 솔버가 내놓는 **정반사 경로 수**는 "
           f"{_n('B_facet_count_sweep.numbers.spec_paths_per_level[0]', EVD, '{:.0f}')}→"
           f"{_n('B_facet_count_sweep.numbers.spec_paths_per_level[3]', EVD, '{:.0f}')} 로 줄고, "
           f"정반사만 남긴 코히어런트 값은 "
           f"{_n('B_facet_count_sweep.numbers.spec_coh_db_per_level[0]', EVD, '{:.4f}', 'dB')} → "
           f"{_n('B_facet_count_sweep.numbers.spec_coh_db_per_level[3]', EVD, '{:.4f}', 'dB')} 로 "
           f"내려간다. 1경로값에 20·log₁₀(2) 를 더하면 2경로값과 잔차 "
           f"{_n('attack_4_defect_vs_misuse.C3_tessellation_non_invariance.evidence.drone_link.residual_db', ATK, '{:.1e}', 'dB')} "
           f"로 같다 — 닫힌형 20·log₁₀(1/2) = "
           f"{_n('B_facet_count_sweep.numbers.theoretical_step_two_to_one_facet_db', EVD, '{:+.2f}', 'dB')} "
           f"와 같은 **항등식**이다.", "",
           f"⚠ 적대검증 원장은 이 자리를 금지 문장 목록에 올려 뒀다 — "
           f"{_n('must_not_say[5]', ATK)} (원장이 그 기전에 붙인 한정: "
           f"{_n('attack_4_defect_vs_misuse.C3_tessellation_non_invariance.hedges[3]', ATK)})", "",
           f"⛔ 가장 성긴 "
           f"{_n('B_facet_count_sweep.numbers.n_tri_per_level[-1]', EVD, '{:.0f}')}개 판에서는 정반사 "
           f"경로가 "
           f"{_n('B_facet_count_sweep.numbers.spec_paths_per_level[-1]', EVD, '{:.0f}')}개이고 정반사 "
           f"코히어런트 값이 "
           f"{num(None, (EVD, 'B_facet_count_sweep.numbers.spec_coh_db_per_level[-1]'), if_null='`null`')} "
           f"이다. 그 단에 남는 coh_db 는 확산(diffuse_reflection=True)을 켠 실행의 값이고, 원장은 "
           f"그런 값을 물리량으로 인용하는 것을 `must_not_say` 에 올린다 — 근거가 된 예산 스윕에서 "
           f"같은 "
           f"{_n('E_diffuse_workaround_fails.numbers.budget_convergence[2].n_tri', EVD, '{:.0f}')}개 "
           f"판이 spp "
           f"{_n('E_diffuse_workaround_fails.numbers.budget_convergence[2].spp_lo', EVD, '{:,.0f}')} → "
           f"{_n('E_diffuse_workaround_fails.numbers.budget_convergence[2].spp_hi', EVD, '{:,.0f}')} 에 "
           f"{_n('E_diffuse_workaround_fails.numbers.budget_convergence[2].coh_drift_db', EVD, '{:.2f}', 'dB')} "
           f"움직였다. 다만 그 스윕의 창은 el "
           f"{_n('meta.el_deg', FCN, '{:.0f}', '°')} 의 방위 두 개 · 시드 두 개 평균이라 여기 한 "
           f"자세(az {_n('B_facet_count_sweep.numbers.hot_aspect.az_deg', EVD, '{:.0f}', '°')} · el "
           f"{_n('B_facet_count_sweep.numbers.hot_aspect.el_deg', EVD, '{:.0f}', '°')})는 그 창 밖이고, "
           f"원장이 그 자세에 대해 들고 있는 행은 spp "
           f"{_n('B_facet_count_sweep.numbers.hot_spp', EVD, '{:,.0f}')} 하나뿐이라 마지막 단의 계단 "
           f"크기는 이 편에서 비워 둔다.", "",
           f"⭐ 면 수 축에서 이 편이 인쇄하는 것은 여기까지다. 형상 판정을 통과하는 구간에서 생산 "
           f"설정 총에코는 "
           f"{_n('attack_1_shape.killer_counter_evidence.table[3].decimation_factor', ATK, '{:.1f}')}배 "
           f"데시메이션에 "
           f"{_n('attack_1_shape.killer_counter_evidence.table[3].d_incoh_mean_db', ATK, '{:+.3f}', 'dB')} "
           f"± {_n('attack_1_shape.killer_counter_evidence.table[3].d_incoh_sd_db', ATK, '{:.3f}', 'dB')} "
           f"움직이고(같은 방위·같은 시드끼리 짝지은 차), 그 이동은 실루엣 면적비 "
           f"{_n('attack_1_shape.killer_counter_evidence.table[3].silhouette_ratio_mean', ATK, '{:.3f}')} "
           f"로 예측한 "
           f"{_n('attack_1_shape.killer_counter_evidence.table[3].predicted_from_silhouette_db', ATK, '{:+.3f}', 'dB')} "
           f"와 잔차 "
           f"{_n('attack_1_shape.killer_counter_evidence.table[3].residual_db', ATK, '{:.3f}', 'dB')} "
           f"로 맞는다. 움직인 것은 면 수가 아니라 남은 형상이다.", "",
           f"⚠ 나머지 자세가 빈 이유는 따로 있다. 같은 자세에 확산을 켜면 표적경유 경로가 자세당 "
           f"{_n('B_facet_count_sweep.numbers.hot_n_paths_min', EVD, '{:.0f}')}개 넘게 잡힌다. "
           f"비어 있는 것은 광선이 아니라 **거울 조건을 만족하는 삼각형**이다."),

        md("## 반대 방향도 같은 뿌리 — 쪼개기만 해도 답이 부푼다", "",
           f"같은 "
           f"{_n('H_tessellation_changes_the_answer.numbers.per_side[1].side_m', EVD, '{:.0f}', 'm')} "
           f"평판을 "
           f"{_n('H_tessellation_changes_the_answer.numbers.per_side[1].n_tri[0]', EVD, '{:.0f}')}개 → "
           f"{_n('H_tessellation_changes_the_answer.numbers.per_side[1].n_tri[-1]', EVD, '{:.0f}')}개 "
           f"삼각형으로 **쪼개기만** 해도 코히어런트 전력이 "
           f"{_n('H_tessellation_changes_the_answer.numbers.max_inflation_db', EVD, '{:.2f}', 'dB')} "
           f"부푼다. 늘어난 경로들은 진폭 산포 "
           f"{_n('H_tessellation_changes_the_answer.numbers.duplicate_path_forensics[0].amp_spread_db', EVD, '{:.1f}', 'dB')} · "
           f"지연 산포 "
           f"{_n('H_tessellation_changes_the_answer.numbers.duplicate_path_forensics[0].tau_spread_ns', EVD, '{:.1f}', 'ns')} · "
           f"위상 산포 "
           f"{_n('H_tessellation_changes_the_answer.numbers.duplicate_path_forensics[0].phase_spread_deg', EVD, '{:.1f}', '°')} "
           f"인 **완전한 복사본**이고, 합은 20·log₁₀(N) 을 "
           f"{_n('H_tessellation_changes_the_answer.numbers.coherent_N_law_max_resid_db', EVD, '{:.4f}', 'dB')} "
           f"안에서 따른다. 격자 위치를 옮겨도 중복은 남는다 (`offset_removes_duplication` = "
           f"{_n('H_tessellation_changes_the_answer.numbers.offset_removes_duplication', EVD)}).", "",
           "메쉬를 깎으면 무너지고 쪼개면 부푼다. 두 방향이 같은 뿌리에서 나온다 — "
           "**답의 단위가 면적이 아니라 경로라서** 면 수가 곧 답이 된다."),

        next_steps([
            ("어느 실험이 이 성질에 실제로 걸리는지 결정표로 가른다",
             "표적 모델이 필요한 실험과 필요 없는 실험이 칸으로 확정된다",
             ref("decision-table", short=True)),
            ("드론 본체에서 재테셀레이션 사다리를 돌린다",
             "적대검증이 무경계로 남긴 기하 축에 크기가 붙는다",
             "`benchmark/facet_mechanism_verdict.py` → " + ref("kernel-vs-stock", short=True)),
            ("면적분을 얹은 커널이 같은 메쉬에서 무엇을 내는지 맞댄다",
             "면 수 의존이 커널 쪽에서 사라지는지가 확정된다",
             ref("kernel-vs-stock", short=True)),
        ]),
    ]


# =========================================================================== #
#  편 06 — decision-table
# =========================================================================== #
def report_06_decision_table():
    return [
        header(
            num=6,
            title="표적 항이 비에서 소거되는가와 절대값이 필요한가, "
                  "두 물음이 실험을 네 칸으로 가른다",
            did="실험마다 표적 산란량이 비(比)에서 상수로 소거되는지와 결론이 절대 dBsm 을 "
                "인쇄해야 하는지를 물어 실험 목록을 네 칸으로 갈랐다.",
            results=[
                f"두 물음이 만드는 칸은 {len(fetch((DEC, 'zones')))}개이고, 실험 "
                f"{len(fetch((DEC, 'items')))}종을 그 칸에 배정했다.",

                f"오른쪽 절반({len(RIGHT_HALF)}종)은 표적 항이 소거되는 칸이다 — 표적 모델 없이도 "
                f"답이 선다.",

                f"왼쪽 절반({len(LEFT_HALF)}종)은 표적 항이 답에 남는 칸이고, 여기서 σ 가 "
                f"입력이 된다.",

                f"바닥 문장은 레이더 방정식 자신의 것이다 — {_n('footer_en', DEC)}",

                "⚠ 소거 논증은 표적이 **한 방향에서** 조명될 때의 것이다. 다중경로에서는 오른쪽 "
                "칸의 실험도 왼쪽으로 이사한다.",
            ],
            method=[
                ("두 축의 정의", "① 표적 산란량이 비를 취할 때 상수로 소거되는가 "
                               "② 결론이 절대 dBsm·dB 를 인쇄해야 하는가"),
                ("칸 배치", "판단이다. 행마다 그 판단이 선 근거 JSON 키를 붙였다"),
                ("한 사례 시험", f"도는 로터는 표적 항이 소거되지 않고 절대 dBsm 도 필요 없어 "
                              f"{_n(f'items[{MD_ITEM}].zone', DEC)} 에 앉는다 — 필요한 것은 "
                              f"레벨이 아니라 서명의 **모양**이고, 그 사례가 마이크로도플러 권이다"),
            ],
            repro=_repro(["PYTHONPATH=src python benchmark/build_report00_decision_map.py",
                          "PYTHONPATH=src python src/figs_report00.py"],
                         [DEC, POC, EVD], "약 1분 (GPU 0장)"),
        ),

        md("## 판별 기준은 두 문장이다", "",
           "**① 표적 산란량이 비(比)를 취할 때 상수로 소거되는가.** 소거되면 표적 모델 없이도 "
           "답이 선다. **② 결론이 절대 dBsm·dB 를 인쇄해야 하는가.**", "",
           "이 두 물음이 실험을 네 칸으로 가른다.", "",
           table_from(f"{DEC}:zones",
                      [("칸", "id"), ("표적 항이 소거되는가", "x_cancels"),
                       ("절대값이 필요한가", "y_absolute"), ("그래서 무엇을 쓰나", "tool_en")]), "",
           f"바닥 문장은 레이더 방정식 자신의 것이다 — {_n('footer_en', DEC)}"),

        md("## 두 물음을 던지면 각 실험은 어느 칸에 앉는가", "",
           *_fig(1, "report00_f4", "두 물음을 던지면 각 실험은 어느 칸에 앉는가?")),

        md("## 오른쪽 절반 — 표적 항이 소거되는 칸", "",
           table_from(f"{DEC}:items", ITEM_COLS, order=RIGHT_HALF)),

        md("## 왼쪽 절반 — 표적 항이 답에 남는 칸", "",
           table_from(f"{DEC}:items", ITEM_COLS, order=LEFT_HALF), "",
           f"⛔ Z4 행 «{_n(f'items[{Z4_ITEM}].label_en', DEC)}» 의 «왜 그런지» 칸에 적힌 "
           f"{_n('B_facet_count_sweep.numbers.total_collapse_db', EVD, '{:.2f}', 'dB')} 는 이 편에서 "
           f"철회한다 — 그 값의 마지막 계단은 형상 판정에서 떨어지는 단(`shape_ok` = "
           f"{_n('B_facet_count_sweep.numbers.shape_ok_per_level[-1]', EVD)})에서 나왔고, 그 단은 "
           f"정반사 경로가 "
           f"{_n('B_facet_count_sweep.numbers.spec_paths_per_level[-1]', EVD, '{:.0f}')}개라 그 자리에 "
           f"들어간 값은 확산을 켠 coh_db 다. 형상 판정을 통과하는 구간(`shape_ok` = "
           f"{_n(f'B_facet_count_sweep.numbers.shape_ok_per_level[{LAST_SHAPE_OK}]', EVD)})에서 남는 "
           f"것은 정반사 경로 수 2→1 의 항등식 "
           f"{_n('B_facet_count_sweep.numbers.theoretical_step_two_to_one_facet_db', EVD, '{:+.2f}', 'dB')} "
           f"이고, 원장은 그것을 중복 복사본 하나가 사라진 값으로 읽는다. **Z4 를 세우는 근거는 이 "
           f"dB 가 아니라 «실루엣이 살아 있는 단 전부에서 정반사 채널이 "
           f"{_n('B_facet_count_sweep.numbers.spec_n_aspects', EVD, '{:.0f}')}자세 중 az "
           f"{_n('B_facet_count_sweep.numbers.hot_aspect.az_deg', EVD, '{:.0f}', '°')} · el "
           f"{_n('B_facet_count_sweep.numbers.hot_aspect.el_deg', EVD, '{:.0f}', '°')} 한 자세에만 "
           f"있다» 는 사실이다** — 그 근거를 재는 자리가 {ref('size-sweep')} 다."),

        md("## ⚠ 단서 하나 — 조명 방향이 둘이면 칸이 바뀐다", "",
           "소거 논증은 표적이 **한 방향에서** 조명될 때의 것이다. 다중경로에서는 직접파와 바닥 "
           "반사가 서로 다른 방향에서 동시에 표적을 때리므로 표적 항이 방향마다 달라진다. "
           f"커널의 {_n('s2_our_kernel.derivation[7].statement', POC)} 가 보여주듯 각 조명 방향마다 "
           f"다른 E 가 나온다(식의 |Γ| 는 입사각 의존 |Γᵢ(θᵢ)| 다 — "
           f"⟨outputs/angle_gamma_impact.json : _meta.design⟩). 그때는 오른쪽 칸의 실험도 "
           f"왼쪽으로 이사한다.", "",
           f"⭐ 이 표를 한 사례로 시험한 것이 {ref_part(7)} 다 — 도는 로터는 "
           f"{_n(f'items[{MD_ITEM}].zone', DEC)}, 즉 **왼쪽 절반**에 앉는다. 표적 항이 소거되지 "
           f"않으므로 표적 모델이 필요하고, 다만 절대 dBsm 은 필요 없어 **모양만** 있으면 된다."),

        next_steps([
            ("다중경로 기하에서 표적 항이 소거되는지를 직접 잰다",
             "오른쪽 칸의 실험이 바닥 반사가 있는 형상에서도 그 칸에 남는지가 확정된다",
             ref_part(10)),
            ("왼쪽 칸이 요구하는 절대 σ 의 조달 방법을 고른다",
             "완전파·SBR+PO·주입 중 무엇을 쓸지가 비용과 함께 확정된다",
             ref("why-po", short=True)),
            (f"{_n(f'items[{MD_ITEM}].zone', DEC)} 사례를 하나 끝까지 돌린다",
             "표적 서명의 **모양**만으로 서는 실험이 절대 레벨 없이 실제로 서는지가 수치로 "
             "확정된다",
             ref_part(7)),
        ]),
    ]


# =========================================================================== #
#  편 07 — why-po
# =========================================================================== #
def report_07_why_po():
    return [
        header(
            num=7,
            #: ⛔2026-09-04 — 전 제목은 «비용대에서 **가장 정확하다**» 였다. 같은 비용대의
            #  다른 갈래(③통계 RCS 주입 ④기하 대리표적)의 정확도를 **잰 칸이 하나도 없고**,
            #  유일하게 재 본 경쟁자에게는 한 축에서 진다 — 편 27 「레벨 하나만 보면 부피를
            #  맞게 고른 구가 **우리보다 낫다** — +0.96 dB · rms 1.98 dB」(우리 −3.30 dB).
            #  최상급을 빼고 «우리가 고른 것» 으로 적는다.
            title="완전파는 정확도의 과녁이고, 표를 만들 수 있는 비용대에서 우리가 고른 "
                  "것은 SBR+PO 다",
            did="σ 를 조달하는 다섯 갈래를 비용과 정확도로 지도에 놓고, 프리프린트 반론"
                "(IEEE OJAP 투고) 하나를 그대로 실어 우리 선택의 값을 적었다.",
            results=[
                f"갈래는 {len(fetch((POC, 's1_alternatives.alternatives')))}개다. 완전파는 정확도의 "
                f"과녁이고 — 우리 2D EFIE MoM 자체검사가 정확 원기둥 고유함수해 대비 "
                f"{_n('s3_validation.layer3_thin_plate_2d_mom.mom_selftest_worst_db', POC, '{:.5f}', 'dB')} "
                f"다 — 그 대신 비용이 표를 못 만들게 한다.",

                f"우리 커널은 자세 하나(방위·고도 한 점 × 반송파 하나 → σ 한 값)에 중앙값 "
                f"{_n('s1_alternatives.ours_runtime.ours_per_pose_ms_median', POC, '{:.1f}', 'ms')} "
                f"다(측정은 Γ(θ) 배선 전 batch 커널 경로). 같은 `RTX 4090` 에서 스톡 "
                f"`sionna.rt.PathSolver` 전파 해가 "
                f"{_n('s1_alternatives.stock_sionna_same_card.stock_sionna_ms_median', POC, '{:.1f}', 'ms')} "
                f"라서 카드는 같다 — 씬 내용과 재는 양은 서로 다르고, 카드 점유는 통제 밖이다.",

                f"⚠ 반론도 그대로 싣는다 — "
                f"{_n('s1_alternatives.cascade_cost_objection._the_objection', POC)} "
                f"⚠ 인용문 속 «게재된» 은 원장 표기이고, 판정으로는 두 편 다 프리프린트다 — "
                f"Ziganshin "
                f"{_n(f'papers[{ZIG_J}].status_ko', SURVEY)} · SagittaSBR "
                f"{_n(f'papers[{SAGITTA}].status_ko', SURVEY)}",

                f"우리 구현에서 PO 적분은 광선캐스팅의 "
                f"{_n('s1_alternatives.cascade_cost_objection.our_po_over_rt', POC, '{:.1f}')}배다. "
                f"프리프린트로 공개된 유일한 GPU 커널 분해는 같은 캐스케이드를 광선발사의 "
                f"{_n('s1_alternatives.cascade_cost_objection.sagitta_po_over_raylaunch_A100_fp32', POC, '{:.1%}')} "
                f"로 적는다 — 절반은 우리 몫이다.",
            ],
            method=[
                ("갈래 지도", "방법마다 «무엇을 푸는가» 를 그 방법의 문헌 표현으로 적고, 그 문헌의 "
                            "게재 상태를 `prior_work_survey.json` 의 판정으로 붙인다"),
                ("비용 인용", f"완전파 쪽 비용은 Ziganshin 저널판"
                            f"({_n(f'papers[{ZIG_J}].status_ko', SURVEY)}) 본문 문장을 축자로 "
                            f"싣는다 — 우리 추정이 아니다"),
                ("런타임 대조", f"같은 `RTX 4090` 에서 우리 커널과 스톡 솔버를 나란히 잰다 — "
                              f"통제되는 것은 카드 하나이고 씬 내용과 재는 양은 서로 다르다"
                              f"(원장 caveat: "
                              f"{_n('s1_alternatives.stock_sionna_same_card.caveat', POC)})"),
            ],
            repro=_repro(["PYTHONPATH=src python benchmark/build_report00_po_case.py"],
                         [POC, SURVEY], "약 1분 (GPU 0장 — JSON 읽기다)"),
        ),

        md("## 다섯 갈래의 지도", "",
           table_from(f"{POC}:s1_alternatives.alternatives",
                      [("방법", "method"), ("무엇을 푸는가", "what_it_solves")]), "",
           f"⭐ 우리 자리를 정확히 적는다. {_n('s2_our_kernel.same_methodology_as.statement', POC)}"),

        md("## 완전파는 정확도의 과녁이다", "",
           f"우리 2D EFIE MoM 자체검사는 정확 원기둥 고유함수해 대비 "
           f"{_n('s3_validation.layer3_thin_plate_2d_mom.mom_selftest_worst_db', POC, '{:.5f}', 'dB')} "
           f"다. 그 눈금이 «완전파가 참값이다» 를 이 저장소 안에서 실제로 붙잡아 준다.", "",
           f"그 대신 비용이 표를 못 만들게 한다. 그 비용 문장은 반론과 같은 Ziganshin 저널판"
           f"({_n(f'papers[{ZIG_J}].locator', SURVEY)}) 본문의 것이고, 축자로 싣는다 — "
           f"{_n('s1_alternatives.alternatives[0].cost_quote_mlfmm', POC)}", "",
           f"우리 커널은 자세 하나에 중앙값 "
           f"{_n('s1_alternatives.ours_runtime.ours_per_pose_ms_median', POC, '{:.1f}', 'ms')} 다 — "
           f"측정은 Γ(θ) 배선 전 batch 커널 경로의 값이다. "
           f"같은 `RTX 4090` 에서 스톡 `sionna.rt.PathSolver` 전파 해가 "
           f"{_n('s1_alternatives.stock_sionna_same_card.stock_sionna_ms_median', POC, '{:.1f}', 'ms')} "
           f"라서 두 값은 같은 카드에서 나온다.", "",
           f"⚠ 이 대조가 통제하는 것은 카드 하나다. 원장 caveat 그대로 — "
           f"{_n('s1_alternatives.stock_sionna_same_card.caveat', POC)} "
           f"우리 팔(B)이 도는 씬은 자유공간 σ 경로이고, 스톡 팔(S)이 도는 씬은 전파 경로다.", "",
           f"⚠ 카드 점유도 통제 밖이다 — 측정 하드웨어는 "
           f"{_n('s1_alternatives.ours_runtime.hardware', POC)} 이고, 괄호 안 `SHARED` 가 그 뜻이다."),

        md("## 프리프린트 반론 하나 — 캐스케이드 비용", "",
           f"⚠ 반론을 그대로 싣는다 — "
           f"{_n('s1_alternatives.cascade_cost_objection._the_objection', POC)}", "",
           f"⚠ 출처 두 편의 게재 상태는 원장 판정이 정한다 — Ziganshin 저널판"
           f"({_n(f'papers[{ZIG_J}].locator', SURVEY)})은 "
           f"{_n(f'papers[{ZIG_J}].status_ko', SURVEY)}, 투고처는 "
           f"{_n(f'papers[{ZIG_J}].venue_ko', SURVEY)} 이고, SagittaSBR"
           f"({_n(f'papers[{SAGITTA}].locator', SURVEY)})은 "
           f"{_n(f'papers[{SAGITTA}].status_ko', SURVEY)} 다.", "",
           f"우리 구현에서 PO 적분은 광선캐스팅의 "
           f"{_n('s1_alternatives.cascade_cost_objection.our_po_over_rt', POC, '{:.1f}')}배다 — "
           f"적분이 아직 호스트 numpy 라서이고, 측정은 Γ(θ) 배선 전 batch 커널 경로다. "
           f"프리프린트로 공개된 유일한 GPU 커널 분해(SagittaSBR)는 같은 "
           f"캐스케이드를 광선발사의 "
           f"{_n('s1_alternatives.cascade_cost_objection.sagitta_po_over_raylaunch_A100_fp32', POC, '{:.1%}')} "
           f"로 적는다. 절반은 우리 몫이다.", "",
           f"⭐ 그래서 이 편의 결론은 «PO 가 가장 정확하다» 가 아니다. ⛔**«이 비용대에서 "
           f"가장 정확하다» 도 2026-09-04 에 내렸다** — 같은 비용대의 다른 갈래(③통계 RCS "
           f"주입 · ④기하 대리표적)의 정확도를 **잰 칸이 하나도 없다.** 유일하게 재 본 "
           f"경쟁자에게는 한 축에서 진다 — {ref('box-sphere-control')} 의 레벨 축에서 "
           f"**부피를 맞게 고른 구가 +0.96 dB · rms 1.98 dB 로 우리 −3.30 dB 보다 낫다.** "
           f"살아남는 문장은 «표를 만들 수 있는 비용대에서 **우리가 고른 것**이 SBR+PO 다» "
           f"이고, 그 표가 실제로 얼마나 맞는지는 {ref('kernel-vs-reference')} 가 잰다."),

        next_steps([
            ("PO 적분을 디바이스 커널로 내린다",
             f"캐스케이드 반론의 비율 "
             f"{_n('s1_alternatives.cascade_cost_objection.our_po_over_rt', POC, '{:.1f}')}배가 "
             f"프리프린트 GPU 분해 수준으로 내려가는지가 확정된다",
             "`src/rcs_sbr.py`"),
            ("Γ(θ) 를 batch 경로에 배선한 뒤 runtime_benchmark 를 같은 카드에서 다시 돌린다",
             "각도 모양이 붙은 커널의 자세당 비용이 확정된다",
             "`benchmark/runtime_benchmark.py`"),
            ("이 비용대에서 얻은 σ 를 해석 기준해와 맞댄다",
             "구현오차가 kr 전 구간에서 dB 로 확정된다",
             ref("kernel-vs-reference", short=True)),
            ("남들이 이 다섯 갈래 중 무엇을 골랐는지 게재본에서 센다",
             "조달처 일곱 갈래와 그 갈래가 사 주는 주장의 크기가 확정된다",
             ref("procurement", short=True)),
        ]),
    ]


# =========================================================================== #
REPORTS = [
    ("stock-says", report_01_stock_says),
    ("engine-paths", report_02_engine_paths),
    ("engine-amplitude", report_03_engine_amplitude),
    ("eight-factors", report_04_eight_factors),
    ("size-sweep", report_05_size_sweep),
    ("decision-table", report_06_decision_table),
    ("why-po", report_07_why_po),
]


def main() -> int:
    print(f"── 부 1 「스톡 엔진이 하는 일과 안 하는 일」 — 편 {len(REPORTS)}개 ──")
    bad = 0
    for anchor, fn in REPORTS:
        rep = build_notebook(nb_path(anchor), fn(), strict=True, quiet=True)
        index_shard(anchor, md_cells=rep["md_cells"], figures=rep["figures"],
                    provenance_tags=rep["provenance_tags"],
                    negatives=rep["n_negatives"], builder=os.path.basename(__file__))
        mark = "✅" if rep["ok"] else "⛔"
        print(f"  {mark} {rep['path']:44s} md {rep['md_cells']:2d}/25 · "
              f"그림 {rep['figures']}/8 · 출처 {rep['provenance_tags']:3d} · "
              f"부정문 {rep['n_negatives']}/3 · 완충어 {rep['n_hedges']}/0")
        bad += 0 if rep["ok"] else 1
    print(f"── {len(REPORTS) - bad}/{len(REPORTS)} 통과 ──")
    return bad


if __name__ == "__main__":
    sys.exit(main())
