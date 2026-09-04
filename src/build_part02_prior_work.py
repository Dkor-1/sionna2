# -*- coding: utf-8 -*-
"""
build_part02_prior_work.py — 부 2 「선행연구」 → 편 08~14
==========================================================================================
부 2 가 답하는 질문 하나
    **남들은 표적 신호를 어디서 얻었나.**

편 하나 = 중심 메시지 하나 (제목이 곧 그 편의 결론 문장이다)

    08 census-published     게재본 중 드론 메쉬 산란을 엔진 안에서 «검증» 한 것은 0편이다
    09 census-preprint      프리프린트는 따로 세고, Ziganshin 은 두 판을 구별해 인용한다
    10 procurement          조달처가 그 논문이 낼 수 있는 주장의 크기를 정한다
    11 procurement-catalog  조달처 일곱 갈래 R1~R7 을 전수로 적었다
    12 injection            외부 σ 주입은 게재돼 있고, 그 값의 대가는 검증이 치른다
    13 where-we-stand       네 관문 동시 통과 게재본은 0편이고, 최근접 3편은 다른 관문에서 걸린다
    14 borrowed             선행에서 빌린 절차와 아직 안 빌린 절차를 비용과 함께 센다

어디서 왔나 (재구성 전 → 후)
    `report01_prior.ipynb` c4~c22  ·  `report00_foundations.ipynb` c20~c21
    논문 문단 두 개(report01 c20 신규성 · c23 방법)는 리포트에서 빼서 `docs/paper/` 로 옮긴다 —
    사용자 지시 *"논문 작성 측면, 재현 관련은 아예 별도로 각각 따로 메모"*.
    계획: `outputs/restruct_exec_plan.json : reports[no in 08..14]`

실행
    cd /workspace/sionna
    PYTHONPATH=src ~/.venvs/py312/bin/python src/build_part02_prior_work.py

⚠ GPU 도 Sionna 실행도 필요 없다.
"""
from __future__ import annotations

import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (_HERE, os.path.join(_ROOT, "benchmark")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from report_registry import (index_shard, nb_path, ref,                  # noqa: E402
                             ref_doc, ref_paper, ref_part)
from report_style import (build_notebook, caption, fetch, header, md,    # noqa: E402
                          next_steps, num, table, table_from)

# --------------------------------------------------------------------------- #
#  근거 파일
# --------------------------------------------------------------------------- #
SURVEY = "outputs/prior_work_survey.json"      # 21건 전문 판정 · 갈래 · 낱말 빈도 · 앵커
PAPER = "outputs/report01_paper.json"          # 4관문 집계 · 인용 · 갈래별 게재수
KR = "outputs/sbr_kr_sweep.json"
DFX = "outputs/sbr_defect_fixes.json"  # 출사 가시성·상반성 — β 창의 원장
CFAR = "outputs/verify_cfar.json"
S2R = "outputs/s2r_prior.json"
POC = "outputs/report00_po_case.json"

INJ_ARCHIVE = "outputs/injection_archive.json"
INJ_AUDIT = "outputs/injection_classification_audit.json"
INJ_VERDICT = "outputs/injection_verdict.json"
INJ_HUNT = "outputs/injection_validation_hunt.json"
CLUTTER = "outputs/facet_attack.json"

FIG = "../outputs/figures"

#: survey JSON 의 `papers` 배열은 순서가 고정돼 있다(게재 0~10 · 프리프린트 11~20).
PUB_OUTSIDE = [0, 1, 2, 3, 4, 5, 6]      # 게재본, 광선엔진 밖에서 서명을 얻은 쪽
PUB_ENGINE = [7, 8, 9, 10]               # 게재본, 광선엔진을 직접 돌리는 쪽
PRE_A = [11, 12, 13, 14, 15]             # 프리프린트 (1/2)
PRE_B = [16, 17, 18, 19, 20]             # 프리프린트 (2/2)
CAT = [[0, 1, 2, 3, 4, 5, 6], [7, 8, 9, 10, 11, 12, 13], [14, 15, 16, 17, 18, 19, 20]]

CENSUS_COLS = [("논문", "short_ko"), ("게재처 · 연도", "venue_status_ko"),
               ("상태", "status_ko"), ("엔진 안 표적", "target_ko")]
CAT_COLS = [("논문", "short_ko"), ("상태", "status_ko"),
            ("표적 서명의 조달처", "route_tag"), ("그 편이 산 주장", "claimed_ko")]
ROUTE_COLS = [("갈래", None), ("조달처", "label_ko"),
              ("그것이 사 주는 주장", "bought_ko"), ("문서", "papers"), ("게재", "published")]


def _n(key: str, src: str, fmt: str | None = None, unit: str = "") -> str:
    return num(None, (src, key), fmt, unit)


def _fig(no: int, stem: str, question: str) -> list[str]:
    return [f"![{stem}]({FIG}/{stem}.png)", "", caption(no, question)]


#: 원장에 남아 있는 **옛 권 이름 → 현행 주소**. 원장(`outputs/*.json`)은 읽기 전용이라
#  치환은 렌더 단계에서만 한다. 열쇠는 낱말 경계로 잡으므로
#  `outputs/report13_sigma_grid.json` 같은 파일 이름은 그대로 남는다.
#  절대 σ 판정과 앵커를 드는 자리는 지금 부 5 «앵커와 검증» 이다.
_RELABEL: list[tuple[str, str]] = [
    (r"report08(?![_0-9A-Za-z])", ref_part(5)),
]


def _relabel(rendered: str) -> str:
    """`table_from()` 이 낸 표에서 옛 권 이름을 현행 주소로 바꾼다."""
    out = rendered
    for pat, new in _RELABEL:
        out = re.sub(pat, lambda _m, _s=new: _s, out)
    return out


def _repro(cmd_extra: list[str], out: list[str], runtime: str, note: str = "") -> dict:
    d = dict(cmd=cmd_extra + ["PYTHONPATH=src python src/build_part02_prior_work.py"],
             out=out, runtime=runtime)
    if note:
        d["note"] = note
    return d


_SURVEY_CMD = "~/.venvs/py312/bin/python prior_work/src/build_prior_survey.py"
_PAPER_CMD = "PYTHONPATH=src python src/report01_paper_facts.py"
_FIGS_CMD = "PYTHONPATH=src python src/figs_report01.py"


# =========================================================================== #
#  편 08 — census-published
# =========================================================================== #
def report_08_census_published():
    return [
        header(
            num=8,
            #: ⛔«계산한» 이 아니라 «검증한» 이다 — 원장 h8.claim_ko 가 그렇게 적고 관문 P4 도
#  «진폭 **검증**» 이다. 계산 자체는 남들도 했다(md-rt·clutter 가 표적 반환을 냈다).
#  관문 이름 g3_mesh_scattering 의 설명만 «계산» 이라 그대로 제목이 됐다(2026-09-04 정정).
            title="전문 판정한 게재본 중 드론 메쉬 산란을 엔진 안에서 «검증» 한 것은 0편이다",
            did="아카이브 문서의 전문을 추출해 관문 넷에 통과시키고, 게재본을 «광선엔진 밖에서 "
                "서명을 얻은 쪽» 과 «엔진을 직접 돌리는 쪽» 으로 갈라 표로 적었다.",
            results=[
                f"문서 {_n('corpus.documents', PAPER, '{:.0f}', '건')}(저작 "
                f"{_n('corpus.distinct_works', PAPER, '{:.0f}', '편')})을 전문 판정했다 — 게재 "
                f"{_n('counts.published', SURVEY, '{:.0f}', '편')} · 프리프린트 "
                f"{_n('counts.preprint', SURVEY, '{:.0f}', '편')}, 축자 인용 "
                f"{_n('counts.quotes_verified', SURVEY, '{:.0f}', '건')} 은 PDF 안 그 쪽에서 "
                f"기계가 다시 찾는다.",

                f"게재본 {_n('funnel.published.in_survey', SURVEY, '{:.0f}', '편')} 중 "
                f"광선엔진을 직접 돌리는 편은 "
                f"{_n('funnel.published.g1_engine', SURVEY, '{:.0f}', '편')}, 그 엔진 안 표적이 "
                f"드론 메쉬인 편은 "
                f"{_n('funnel.published.g2_drone_mesh', SURVEY, '{:.0f}', '편')}, 그 메쉬에서 "
                f"산란 진폭을 계산한 편은 "
                f"{_n('funnel.published.g3_mesh_scattering', SURVEY, '{:.0f}', '편')} 이다 — "
                f"프리프린트까지 합친 문서 "
                f"{_n('funnel.all.in_survey', SURVEY, '{:.0f}', '건')} 기준으로는 "
                f"{_n('counts.runs_engine', SURVEY, '{:.0f}', '편')} → "
                f"{_n('counts.drone_mesh_in_engine', SURVEY, '{:.0f}', '편')} → "
                f"{_n('counts.mesh_scattering_in_engine', SURVEY, '{:.0f}', '편')} 이다.",

                f"1차 사료 정산이 "
                f"{_n('counts.added_since_census', SURVEY, '{:.0f}', '편')} 을 더해 판정 문서가 "
                f"{_n('counts.papers', SURVEY, '{:.0f}', '건')} 이 됐다 — 더한 것 중 "
                f"Rzewuski 는 최종물이 우리와 가장 가깝고 아카이브 밖에 있었다.",

                f"전문 쪽수 합계는 "
                f"{_n('counts.pages_total', SURVEY, '{:,.0f}', '쪽')} 이고, 읽고 범위 밖으로 "
                f"뺀 문서가 {_n('counts.read_and_excluded', SURVEY, '{:.0f}', '건')} 이다 — "
                f"뺀 사유를 원장에 함께 남겼다.",
            ],
            method=[
                ("범위", f"아카이브 2곳 + 패시브레이더 코퍼스에서 "
                        f"{_n('meta.corpus_swept_pdfs', SURVEY, '{:.0f}', '편')} 을 낱말 대조하고, "
                        f"{_n('corpus.documents', PAPER, '{:.0f}', '건')} 을 전문 판정했다"),
                ("귀속", "판정마다 축자 인용을 PDF 그 쪽에서 기계가 찾는다 — 못 찾으면 빌드가 죽는다 "
                        "(`prior_work/src/build_prior_survey.py:85`)"),
                ("게재상태", "PDF 메타데이터 `subject`(IEEE 조판이 박는 \"게재처;연도;권;호;DOI\") · "
                            "지면 스탬프 · arXiv 스탬프로 문서마다 확정했다"),
                ("관문", "G1 엔진 · G2 드론 메쉬 · G3 그 메쉬에서 산란 진폭 · G4 절대 dBsm 보고"),
            ],
            repro=_repro([_SURVEY_CMD, _PAPER_CMD, _FIGS_CMD], [SURVEY, PAPER],
                         f"근거 {_n('meta.runtime_s', SURVEY, '{:.0f}', 's')} · "
                         f"나머지 각 수 초 · CPU 만 쓴다",
                         "아카이브는 /data/public/sionna_jeong/papers_isac_sionna 와 "
                         "sionna_papers_by_task, 패시브 코퍼스는 /data/public/jeong/papers 다"),
        ),

        md("## 관문 넷과 그것이 세는 것", "",
           f"{_n('corpus.documents', PAPER, '{:.0f}', '건')} 을 전문 추출해 관문 네 개에 "
           f"통과시켰다. 문서 {_n('corpus.documents', PAPER, '{:.0f}', '건')} 은 저작 "
           f"{_n('corpus.distinct_works', PAPER, '{:.0f}', '편')} 이다 — Costa 와 Ziganshin 은 "
           f"회의판·저널판을 따로 세고, 그 이유는 {ref('census-preprint')} 에 있다.", "",
           table(["관문", "통과 조건"],
                 [["G1", "이 논문이 Sionna 계열 광선엔진을 직접 돌린다"],
                  ["G2", "그 엔진 안의 표적이 드론 기하(메쉬)다 — 큐브·점산란체와 구분한다"],
                  ["G3", "그 메쉬에서 산란 **진폭**을 계산한다"],
                  ["G4", "결과를 절대 RCS(dBsm)로 보고한다"]])),

        md("## 관문을 하나씩 걸면 몇 건이 남는가", "",
           *_fig(1, "report01_p1_funnel", "관문을 하나씩 걸면 몇 건이 남는가?"), "",
           f"게재본 열은 G1 {_n('funnel.published.g1_engine', SURVEY, '{:.0f}', '편')} → G2 "
           f"{_n('funnel.published.g2_drone_mesh', SURVEY, '{:.0f}', '편')} → G3 "
           f"{_n('funnel.published.g3_mesh_scattering', SURVEY, '{:.0f}', '편')} 이고, 이 편의 "
           f"아래 두 표가 그 열이다. 그림의 깔때기는 프리프린트를 합친 문서 "
           f"{_n('funnel.all.in_survey', SURVEY, '{:.0f}', '건')} 기준이라 G1 "
           f"{_n('counts.runs_engine', SURVEY, '{:.0f}', '편')} → G2 "
           f"{_n('counts.drone_mesh_in_engine', SURVEY, '{:.0f}', '편')} → G3 "
           f"{_n('counts.mesh_scattering_in_engine', SURVEY, '{:.0f}', '편')} 로 읽는다 — "
           f"막대는 게재본과 프리프린트를 쌓고, 괄호 안 숫자가 게재본 몫이다.", "",
           f"프리프린트 열은 {ref('census-preprint')} 가 따로 든다. "
           f"⭐ 이 깔때기가 이 편의 제목이고, 그 마지막 칸이 우리가 서는 자리다."),

        md("## 게재본 — 표적 서명을 광선엔진 밖에서 얻은 쪽", "",
           table_from((SURVEY, "papers"), CENSUS_COLS, order=PUB_OUTSIDE)),

        md("## 게재본 — 광선엔진을 직접 돌리는 쪽", "",
           "아래 표의 `PEC` 는 전기를 완벽히 통하는 이상적 금속이다.", "",
           table_from((SURVEY, "papers"), CENSUS_COLS, order=PUB_ENGINE)),

        next_steps([
            ("프리프린트를 같은 관문에 따로 통과시킨다",
             "«게재» 라는 낱말이 이 편의 주장을 얼마나 떠받치는지가 확정된다",
             ref("census-preprint", short=True)),
            ("각 편이 표적 서명을 어디서 조달했는지를 갈래로 묶는다",
             "조달처가 사 주는 주장의 크기가 갈래마다 확정된다",
             ref("procurement", short=True)),
            ("Xplore 본문 검색 권한으로 ICCT · EuRAD · RadarConf 프로시딩을 같은 관문에 넣는다",
             "유료 프로시딩까지 포함한 관문 통과 편수가 확정된다",
             "`prior_work/src/build_prior_survey.py:PAPERS`"),
        ]),
    ]


# =========================================================================== #
#  편 09 — census-preprint
# =========================================================================== #
def report_09_census_preprint():
    return [
        header(
            num=9,
            title="프리프린트는 따로 세고, Ziganshin 은 두 판을 구별해 인용한다",
            did="프리프린트를 게재본과 다른 표에 담고, 같은 저작의 회의판과 저널판이 보고량까지 "
                "다르다는 것을 판별해 판 단위로 셌다.",
            results=[
                f"프리프린트는 {_n('counts.preprint', SURVEY, '{:.0f}', '편')} 이고 게재본은 "
                f"{_n('counts.published', SURVEY, '{:.0f}', '편')} 이다 — 같은 표에 섞지 않는다. "
                f"프리프린트 열만 관문에 걸면 G1 "
                f"{_n('funnel.preprint.g1_engine', SURVEY, '{:.0f}', '편')} → G2 "
                f"{_n('funnel.preprint.g2_drone_mesh', SURVEY, '{:.0f}', '편')} → G3 "
                f"{_n('funnel.preprint.g3_mesh_scattering', SURVEY, '{:.0f}', '편')} 이다.",

                f"문서 {_n('corpus.documents', PAPER, '{:.0f}', '건')} 은 저작 "
                f"{_n('corpus.distinct_works', PAPER, '{:.0f}', '편')} 이다. 차이는 Costa 와 "
                f"Ziganshin 의 판 쌍이고, 판마다 게재상태와 보고량이 갈린다.",

                "Ziganshin 학회판(EuCAP 2025)은 게재본이고 패싯 차량 RCS 를 dBsm 으로 인쇄한다. "
                "저널판(arXiv 프리프린트)은 근거리 산란전계와 패싯 이산화 품질을 보고한다.",

                "본문에 지면 채택을 적은 arXiv 원고는 `일부` 로 세고 프리프린트로 남긴다 — "
                "이 편의 모든 계수가 그 규칙 아래에서 계산됐다.",
            ],
            method=[
                ("판 단위 계수", "판마다 게재상태와 보고량이 달라 저작이 아니라 판으로 센다 — "
                               "저작 수를 같은 화면에 함께 적는다"),
                ("게재상태 확정", "PDF 메타데이터 · 지면 스탬프 · arXiv 스탬프 셋으로 문서마다 "
                                "확정한다. 본문의 채택 문장은 `일부` 로 센다"),
                ("드론 문장", "학회판 결론의 축자 인용을 그대로 싣는다 — 요약하지 않는다"),
            ],
            repro=_repro([_SURVEY_CMD, _PAPER_CMD], [SURVEY, PAPER],
                         "약 1분 (CPU 만 쓴다)"),
        ),

        md("## 왜 따로 세는가", "",
           f"«게재» 라는 낱말이 {ref('census-published')} 의 주장을 떠받친다. 그러니 그 낱말이 "
           f"무엇을 세는지가 흔들리면 주장의 크기도 같이 흔들린다. 프리프린트를 같은 표에 넣으면 "
           f"간극이 이음매로 좁아지고, 그 사실을 감추지 않기 위해 표를 따로 둔다.", "",
           f"프리프린트 {_n('counts.preprint', SURVEY, '{:.0f}', '편')} 을 두 표로 나눠 싣는다. "
           f"이 열의 관문 통과는 G1 "
           f"{_n('funnel.preprint.g1_engine', SURVEY, '{:.0f}', '편')} → G2 "
           f"{_n('funnel.preprint.g2_drone_mesh', SURVEY, '{:.0f}', '편')} → G3 "
           f"{_n('funnel.preprint.g3_mesh_scattering', SURVEY, '{:.0f}', '편')} 이다. 게재본 열"
           f"(G1 {_n('funnel.published.g1_engine', SURVEY, '{:.0f}', '편')} → G2 "
           f"{_n('funnel.published.g2_drone_mesh', SURVEY, '{:.0f}', '편')} → G3 "
           f"{_n('funnel.published.g3_mesh_scattering', SURVEY, '{:.0f}', '편')})은 "
           f"{ref('census-published')} 가 들고, 두 열을 합친 것이 그 편 그림 1 의 깔때기다."),

        md("## 프리프린트 (1/2)", "",
           table_from((SURVEY, "papers"), CENSUS_COLS, order=PRE_A)),

        md("## 프리프린트 (2/2)", "",
           table_from((SURVEY, "papers"), CENSUS_COLS, order=PRE_B)),

        md("## Ziganshin — 두 판을 구별해 인용한다", "",
           "어느 판을 인용하는지가 사실을 가른다. 판마다 게재상태와 보고량이 다르다.", "",
           table(["판", "게재상태", "보고한 양", "표적"],
                 [["학회판 (EuCAP 2025, DOI 10.23919/EuCAP63536.2025.10999367)", "게재",
                   "패싯 차량 RCS 를 dBsm 으로 (Fig.6)", "단순화 차량(PEC)"],
                  ["저널판 (`arXiv:2604.05991v2`)", "IEEE OJAP 투고 프리프린트",
                   "근거리 산란전계 |E| 와 패싯 이산화 품질", "구·원기둥·PEC 차량"]]), "",
           "드론을 향후 과제로 그 단어 그대로 적는 문장은 **학회판 p.5 결론**에 있다: "
           "*\"can also be applied to compute scattering from other objects, such as drones, "
           "humans, and micro-Doppler effects\"*. 우리가 서 있는 자리는 그 문장 바로 뒤이고, "
           "그 문장은 동료심사를 통과한 문장이다."),

        next_steps([
            ("두 판의 판정 차이를 관문 표에 그대로 반영한다",
             "«게재» 를 넣고 뺄 때 관문 통과 편수가 어떻게 바뀌는지가 확정된다",
             ref("where-we-stand", short=True)),
            ("각 편이 서명을 어디서 조달했는지 갈래로 묶는다",
             "판 구분과 무관하게 갈래별 주장의 크기가 확정된다",
             ref("procurement", short=True)),
            ("Ziganshin 저널판의 이산화 품질 지표를 우리 커널 눈금과 같은 축에 올린다",
             "메쉬 이산화가 σ 에 주는 크기가 두 구현 사이에서 비교 가능해진다",
             ref("kernel-vs-reference", short=True)),
            ("Wypich & Zielinski(원문 미확보 · 표적은 차량 5.8 GHz)를 입수해 "
             "ECA(직접파를 빼내는 소거기)→CFAR 선례를 재검증한다",
             "우리 하드웨어 선례가 인용 가능한지 확정된다",
             "`prior_work/outputs/prior_work.json`"),
        ]),
    ]


# =========================================================================== #
#  편 10 — procurement
# =========================================================================== #
def report_10_procurement():
    return [
        header(
            num=10,
            title="표적 서명을 어디서 조달했는지가 그 논문이 낼 수 있는 주장의 크기를 정한다",
            did="편마다 표적 서명의 조달처를 판정해 갈래로 묶고, 갈래가 사 주는 주장의 크기를 "
                "게재 편수와 함께 적었다.",
            results=[
                f"갈래는 {len(fetch((PAPER, 'route_status')))}개다 — 측정은 절대 σ 를, 스톡 엔진은 "
                f"운동학 서명을, 엔진 안 산란 구현은 메쉬에서 낸 RCS 의 **각도 구조**를 산다.",

                f"절대 σ 를 dBsm(1 m² 를 0 으로 잡은 dB 눈금)으로 찍는 편은 "
                f"{_n('counts.prints_dbsm', SURVEY, '{:.0f}', '편')} 이고, 그중 광선엔진을 "
                f"돌리는 것은 "
                f"{_n('counts.prints_dbsm_and_runs_engine', SURVEY, '{:.0f}', '편')} 이며 "
                f"그 표적은 차량이다.",

                f"전문에 `CFAR` 도 `false alarm` 도 0회인 논문이 "
                f"{_n('counts.zero_cfar_and_false_alarm', SURVEY, '{:.0f}', '편')} 이다 — "
                f"오경보 바닥을 명목값에 고정하는 것은 잡음·클러터 분포를 통제하는 시뮬이 하는 "
                f"일이다.",

                "두 극단의 표본이 갈래의 뜻을 보여준다 — md-rt 는 자기 폐형식 운동학 식을 대조 "
                "기준으로 삼고, LAMBDA 는 σ 를 CADFEKO 에서 풀어 광선경로에 조회로 싣는다.",
            ],
            method=[
                ("갈래 판정", "편마다 «서명을 어디서 가져왔나» 를 축자 인용과 함께 판정하고, "
                            "갈래는 그 판정의 묶음이다"),
                ("게재 편수", "갈래마다 게재본 수를 따로 세어 갈래의 무게를 함께 적는다"),
                ("낱말 계수", "`dBsm` · `CFAR` · `false alarm` 은 전문 문자열 계수다 — "
                            "필요조건 검사이고 방법의 척도가 아니다"),
            ],
            repro=_repro([_SURVEY_CMD, _PAPER_CMD, _FIGS_CMD], [SURVEY, PAPER],
                         "약 1분 (CPU 만 쓴다)"),
        ),

        md("## 고른 조달처가 주장의 크기를 정한다", "",
           "편마다 표적 서명의 조달처를 골랐고, 고른 조달처가 그 편이 낼 수 있는 주장의 크기를 "
           "정한다. 무향실 측정은 기체 한 대의 절대 RCS 를 사고, 외부 완전파 솔버는 바이스태틱 "
           "RCS 와 그것을 먹는 커버리지 예산을 사며, 미리 계산한 RCS 의 주입은 엔진을 건드리지 "
           "않고 자세별 진폭을 산다.", "",
           f"해석 블레이드 모형은 마이크로도플러 서명의 **모양**을 사고, 추상 계수는 폐형식 신호 "
           f"모형을 사며, 광선엔진의 스톡 상호작용은 운동학 구조를 산다. 갈래 전수와 편수는 "
           f"{ref('procurement-catalog')} 에 있다."),

        md("## 각 갈래에 몇 건이 서 있는가", "",
           *_fig(1, "report01_p2_routes", "각 갈래에 몇 건이 서 있는가?"), "",
           "md-rt 는 Sionna RT 의 회전 마이크로도플러 정확도 검증을 스스로 주장하고, 대조 기준은 "
           "자기 폐형식 운동학 식이다 — 그래서 진폭 검증 관문에서 걸리고 전문의 dBsm 도 0회다.", "",
           "LAMBDA 는 반대쪽 끝의 표본이다. UAV 메쉬는 Sionna RT 에 넣되 σ 는 CADFEKO 에서 풀어 "
           "자세별로 조회한다(p.3 · p.7) — 엔진을 건드리지 않고 진폭을 얻는 주입 구조다."),

        md("## 절대 σ 를 dBsm 으로 찍는 편은 어디인가", "",
           *_fig(2, "report01_p3_dbsm", "절대 σ 를 dBsm 으로 찍는 편은 어디인가?"), "",
           f"전문에 `dBsm` 이 한 번이라도 나오는 논문이 "
           f"{_n('counts.prints_dbsm', SURVEY, '{:.0f}', '편')}, 그중 광선엔진을 돌리는 것은 "
           f"{_n('counts.prints_dbsm_and_runs_engine', SURVEY, '{:.0f}', '편')} 이고 그 표적은 "
           f"차량이다. 나머지는 무향실 측정 · FDTD · Sionna 밖 자체 솔버가 낸 값이다.", "",
           f"CFAR(잡음을 보고 스스로 올라가 오경보율을 일정하게 붙잡는 문턱)도 false alarm 도 "
           f"전문에 0회인 논문이 "
           f"{_n('counts.zero_cfar_and_false_alarm', SURVEY, '{:.0f}', '편')} 이다. 오경보 바닥을 "
           f"경험 Pfa 로 교정하는 일은 {ref_part(9)} 가 GPU 몬테카를로 "
           f"{_n('meta.runtime_s', CFAR, '{:.0f}', 's')} 로 수행한다."),

        next_steps([
            ("갈래 일곱과 그 안의 편들을 전수 표로 편다",
             "어느 편이 어느 갈래에 서 있는지가 행 단위로 확정된다",
             ref("procurement-catalog", short=True)),
            ("엔진 밖에서 조달한 게재본이 무엇을 검증했는지 아카이브 전수로 다시 센다",
             "주입 아키텍처의 전례와 그 값이 치른 검증의 크기가 확정된다",
             ref("injection", short=True)),
            ("우리가 고른 갈래의 비용과 정확도를 다섯 갈래 지도 위에 놓는다",
             "우리 선택이 어느 비용대에서 최선인지가 확정된다",
             ref("why-po", short=True)),
            ("Costa(JSTEAP, 게재)의 해석 마이크로도플러 경로를 우리 기하 위에서 재현한다",
             "해석 블레이드 모형 갈래가 우리 커널 위에서 어디까지 재현되는지가 확정된다",
             ref_part(7)),
        ]),
    ]


# =========================================================================== #
#  편 11 — procurement-catalog
# =========================================================================== #
def report_11_procurement_catalog():
    return [
        header(
            num=11,
            title="조달처 일곱 갈래 R1~R7 을 전수로 적었다",
            did="갈래마다 조달처와 그것이 사 주는 주장을 적고, 판정한 문서 전부를 갈래 태그와 "
                "게재상태와 함께 세 표로 실었다.",
            results=[
                f"갈래는 {len(fetch((PAPER, 'route_status')))}개이고, 갈래마다 문서 수와 게재 "
                f"편수를 함께 센다.",

                f"카탈로그는 판정 문서 "
                f"{_n('corpus.documents', PAPER, '{:.0f}', '건')} 전수를 담는다 — 표를 셋으로 "
                f"나눈 이유는 화면 하나에 들어가게 하기 위해서다.",

                "각 행은 «논문 · 상태 · 조달처 · 그 편이 산 주장» 네 칸이다. 마지막 칸이 이 권의 "
                "중심 문장을 행마다 반복해서 보여준다.",

                f"이 표가 논문 II 절 표의 원형이고, 그 문단은 "
                f"{ref_paper('01_prior')} 로 옮겨 두었다.",
            ],
            method=[
                ("갈래 태그", "편마다 축자 인용으로 판정한 조달처를 `route_tag` 한 칸으로 압축한다"),
                ("게재상태 열", "논문 II 절 표의 원형이라 게재상태 열을 함께 싣는다"),
                ("표 분할", "행 순서는 근거 JSON 의 고정 순서 그대로이고, 인덱스로 잘랐다"),
            ],
            repro=_repro([_SURVEY_CMD, _PAPER_CMD], [SURVEY, PAPER],
                         "약 1분 (CPU 만 쓴다)"),
        ),

        md("## 갈래 일곱 — 조달처와 그것이 사 주는 주장", "",
           "아래 표의 `CIR` 은 채널 임펄스 응답, 즉 한 번 때린 신호가 되돌아오는 모양이다.", "",
           table_from((PAPER, "route_status"), ROUTE_COLS, key_col="갈래")),

        md("## 카탈로그 (1/3)", "",
           table_from((SURVEY, "papers"), CAT_COLS, order=CAT[0])),

        md("## 카탈로그 (2/3)", "",
           table_from((SURVEY, "papers"), CAT_COLS, order=CAT[1])),

        md("## 카탈로그 (3/3)", "",
           table_from((SURVEY, "papers"), CAT_COLS, order=CAT[2])),

        next_steps([
            ("엔진 밖 조달 갈래를 아카이브 전수로 다시 센다",
             f"판정 {_n('corpus.documents', PAPER, '{:.0f}', '건')} 이라는 모집단 밖에서도 "
             f"같은 그림이 서는지가 확정된다",
             ref("injection", short=True)),
            ("갈래별 게재 편수를 네 관문 판정과 교차시킨다",
             "어느 갈래가 어느 관문에서 걸리는지가 확정된다",
             ref("where-we-stand", short=True)),
            ("우리 갈래의 절차를 선행에서 얼마나 빌렸는지 센다",
             "빌린 절차와 남은 절차가 비용과 함께 확정된다",
             ref("borrowed", short=True)),
        ]),
    ]


# =========================================================================== #
#  편 12 — injection
# =========================================================================== #
def report_12_injection():
    return [
        header(
            num=12,
            title="외부 σ 주입은 게재돼 있고, 그 값의 대가는 검증이 치른다",
            did="주입을 아카이브 고유문서 인구조사와 거기에 베뉴 탐색을 더한 마스터 표 두 "
                "모집단에서 좁은 정의와 넓은 정의로 갈라 세고, 게재된 사례가 무엇을 인쇄했는지 "
                "판독했다.",
            results=[
                f"모집단은 셋이다 — 아카이브 고유문서 "
                f"{_n('method.unique_documents_after_text_hash_dedup', INJ_ARCHIVE, '{:.0f}', '편')}"
                f"(텍스트 해시 중복 제거 후) 인구조사, 거기에 웹·Crossref 베뉴 탐색을 더한 마스터 "
                f"표, 그리고 전문 판정 문서 "
                f"{_n('corpus.documents', PAPER, '{:.0f}', '건')} 이다.",

                f"인구조사가 읽어 판정한 주입 사례는 "
                f"{_n('headline_answer.counts.injection_instances_found_and_read', INJ_ARCHIVE, '{:.0f}', '건')}"
                f"(게재 "
                f"{_n('headline_answer.counts.of_which_published_in_a_peer_reviewed_venue_per_the_pdf', INJ_ARCHIVE, '{:.0f}', '편')}"
                f")이고, 넓은 정의(외부 서명표 → 시뮬 경로·링크)로 마스터 표까지 넓히면 "
                f"{_n('counts.injection_instances_in_the_master_table', INJ_VERDICT, '{:.0f}', '건')}"
                f"(게재 {_n('counts.peer_reviewed', INJ_VERDICT, '{:.0f}', '편')})이다.",

                f"인구조사를 PDF 로 다시 열어 판정하면 확정 게재 주입은 "
                f"{_n('corrected_tally.peer_reviewed_confirmed_injections', INJ_AUDIT, '{:.0f}', '편')} "
                f"이다(인구조사 주장 "
                f"{_n('corrected_tally.census_claimed.peer_reviewed', INJ_AUDIT, '{:.0f}', '편')}).",

                "⭐ 게재된 주입 사례가 인쇄한 것은 아키텍처가 아니라 **검증**이다 — 금속구와 "
                "held-out 밴드, 자동차 레이다 end-to-end, 정규화 서명 상관이 그것이다.",
            ],
            method=[
                ("두 정의", "좁은 정의는 `외부 상용 솔버 → 광선추적 경로계수`, 넓은 정의는 "
                          "`외부 서명표 → 시뮬 경로·링크` 다. 한 문장에 섞지 않는다"),
                ("모집단 명시", "행마다 모집단을 칸 안에 적는다 — 아카이브 전수 인구조사와, "
                              "웹·Crossref 베뉴 탐색을 더한 마스터 표와, 전문 판정 표는 셋 다 "
                              "다른 모집단이다"),
                ("재판독 감사", "인구조사가 주장한 건을 PDF 로 다시 열어 확정 주입 · 예산수준 · "
                              "주입 아님 셋으로 가른다"),
            ],
            repro=_repro([], [INJ_ARCHIVE, INJ_AUDIT, INJ_VERDICT, INJ_HUNT],
                         "약 1분 (CPU 만 쓴다 — 다른 워크플로의 원장을 읽는다)",
                         "네 원장은 다른 워크플로의 산출물이고 이 빌더는 값만 읽는다"),
        ),

        md("## 주입을 두 정의로 갈라 다시 세면", "",
           f"주입(엔진 밖에서 만든 σ 표를 자세로 조회해 시뮬 경로에 곱하는 구조)을 두 모집단에서 "
           f"센다. ① 아카이브 고유문서 "
           f"{_n('method.unique_documents_after_text_hash_dedup', INJ_ARCHIVE, '{:.0f}', '편')} "
           f"인구조사가 읽어 판정한 사례가 "
           f"{_n('headline_answer.counts.injection_instances_found_and_read', INJ_ARCHIVE, '{:.0f}', '건')}"
           f", ② 거기에 베뉴 탐색을 더한 마스터 표가 "
           f"{_n('counts.injection_instances_in_the_master_table', INJ_VERDICT, '{:.0f}', '건')} "
           f"이다. 정의를 둘로 갈라 적는다 — 좁은 정의는 `외부 상용 솔버 → 광선추적 경로계수`, "
           f"넓은 정의는 `외부 서명표 → 시뮬 경로·링크` 다.", "",
           f"② 를 어디서 찾았는지와 그 사각지대는 원장이 이렇게 적는다 — "
           f"{_n('search_coverage.how_they_were_queried', INJ_VERDICT)}", "",
           table(["갈래 · 정의", "모집단", "이 조사가 센 것", "게재", "인쇄된 검증"],
                 [["좁은 정의 — 외부 상용 솔버 → 광선추적 경로계수",
                   "② 마스터 표",
                   _n("headline_answer.the_single_paper_that_does_that", INJ_VERDICT),
                   _n("headline_answer.of_the_peer_reviewed_set_how_many_computed_the_table_in"
                      "_a_commercial_full_wave_solver_and_multiplied_it_onto_ray_traced_paths",
                      INJ_VERDICT, "{:.0f}", "편"),
                   _n("answer.strict_verdict", INJ_HUNT)],
                  ["넓은 정의 — 외부 서명표 → 시뮬 경로·링크",
                   "② 마스터 표 (아카이브 + 웹·Crossref 탐색)",
                   _n("counts.injection_instances_in_the_master_table",
                      INJ_VERDICT, "{:.0f}", "건"),
                   _n("counts.peer_reviewed", INJ_VERDICT, "{:.0f}", "편") + " (프리프린트 "
                   + _n("counts.preprint_only", INJ_VERDICT, "{:.0f}", "편") + ")",
                   _n("answer.broad_verdict", INJ_HUNT)],
                  ["재판독 감사 — 인구조사를 PDF 로 다시 열어 판정",
                   "① 아카이브 인구조사",
                   "인구조사 " + _n("corrected_tally.census_claimed.instances",
                                 INJ_AUDIT, "{:.0f}", "건") + " 재판독",
                   _n("corrected_tally.peer_reviewed_confirmed_injections",
                      INJ_AUDIT, "{:.0f}", "편"),
                   "확정 주입 · 예산수준 · 주입 아님 셋으로 갈린다"]])),

        md("## 통계 추출 — 표적 진폭을 분포에서 뽑는 쪽", "",
           f"엔진 밖 조달의 다른 갈래는 표적 진폭을 식 (108) CN(0, σ²) 에서 뽑는다. 그 클러터 "
           f"서베이(Proc. IEEE)의 41쪽 전문을 세면 `physical optics` "
           f"{_n('attack_5_clutter_survey.what_is_genuinely_unreported.fulltext_counts_41p.physical_optics', CLUTTER, '{:.0f}', '회')} · "
           f"`dBsm` "
           f"{_n('attack_5_clutter_survey.what_is_genuinely_unreported.fulltext_counts_41p.dBsm', CLUTTER, '{:.0f}', '회')} · "
           f"`max_depth` "
           f"{_n('attack_5_clutter_survey.what_is_genuinely_unreported.fulltext_counts_41p.max_depth', CLUTTER, '{:.0f}', '회')} · "
           f"`mesh` "
           f"{_n('attack_5_clutter_survey.what_is_genuinely_unreported.fulltext_counts_41p.mesh', CLUTTER, '{:.0f}', '회')} · "
           f"`Blender` "
           f"{_n('attack_5_clutter_survey.what_is_genuinely_unreported.fulltext_counts_41p.Blender', CLUTTER, '{:.0f}', '회')} "
           f"다.", "",
           "클러터 서베이가 표적 축을 비운 것은 그 편의 설계다 — 표적 진폭은 통계 추출이고 "
           "광선추적은 건물 클러터에 쓴다. 그 빈 칸이 우리 자리이고, 메쉬 해상도·광선예산·기종을 "
           "인쇄하는 것이 우리 재현성 규약이다."),

        md("## 입장료는 검증이다", "",
           "⭐ **게재된 주입 사례가 인쇄한 것은 아키텍처가 아니라 검증이다** — 0.5 m 금속구와 "
           "28 GHz held-out 밴드(Zhang, IEEE JSAC), 77 GHz 자동차 레이다 end-to-end(Deep, "
           "IET RSN), 정규화 서명 상관(Costa, IEEE J-STEAP).", "",
           "⚠ 그 셋을 한 줄로 «검증됐다» 라고 묶으면 크기가 부풀려진다. 검증된 양이 편마다 "
           "다르고, 원장이 그 차이를 이렇게 적는다.", "",
           table(["편", "검증된 것이 정확히 무엇인가"],
                 [["Costa (IEEE J-STEAP)",
                   _n("cross_reference.my_refinements[0]", INJ_HUNT)],
                  ["Deep (IET RSN)", _n("cross_reference.my_refinements[1]", INJ_HUNT)],
                  ["Zhang (IEEE JSAC)", _n("cross_reference.my_refinements[2]", INJ_HUNT)]]), "",
           f"입장료가 거기 있으므로 우리도 같은 값을 치른다. 그 값을 치르는 자리가 "
           f"{ref_part(5)} 와 {ref_part(11)} 이고, 검증량이 σ 자체에서 서명 형태까지 갈린다는 "
           f"사실이 우리 검증 층 설계의 근거다."),

        next_steps([
            ("우리 σ 를 금속구·held-out 밴드와 같은 방식으로 맞댄다",
             "우리 값이 게재 사례와 같은 입장료를 치렀는지가 확정된다",
             ref("calibration-sphere", short=True)),
            ("네 관문 판정에서 주입 갈래가 어느 칸에 앉는지 확정한다",
             "«주입은 전례가 있다» 와 «우리 기여는 엔진이다» 가 같은 표에서 양립하는지가 확정된다",
             ref("where-we-stand", short=True)),
            ("좁은 정의의 단일 사례를 원문으로 다시 판독한다",
             "좁은 정의의 판정 문자열이 그 편의 실제 구조와 맞는지가 확정된다",
             "`outputs/injection_verdict.json`"),
        ]),
    ]


# =========================================================================== #
#  편 13 — where-we-stand
# =========================================================================== #
def report_13_where_we_stand():
    return [
        header(
            num=13,
            title="네 관문을 동시에 통과한 게재본은 0편이고, 최근접 3편은 각각 다른 관문에서 걸린다",
            did="후보를 네 관문으로 하나씩 판정하고, 우리 파이프라인이 각 축에서 한 일을 값과 "
                "함께 같은 표에 올렸다.",
            results=[
                f"후보 {_n('h8.n_adjudicated', PAPER, '{:.0f}', '편')} 을 네 관문으로 판정해 동시 "
                f"통과는 {_n('h8.n_passing_all_prongs', PAPER, '{:.0f}', '편')} 이다.",

                "가장 가까운 셋은 각각 **다른** 관문에서 걸린다 — 그래서 «한 편만 넘으면 된다» 는 "
                "요약이 성립하지 않는다.",

                f"우리 자세 패턴은 해석 PO 구 대비 "
                f"{_n('summary_div16.max_abs_db_vs_po', KR, '{:.3f}', 'dB')}(입사 "
                f"{_n('meta.n_incidence', KR, '{:.0f}', '방향')})이고, 밴드 기울기는 Das 적합계수 "
                f"{_n('anchors.das.mu_a_db_per_ghz', SURVEY, '{:.2f}', 'dB/GHz')} 에 맞춘다.",

                f"실측 전이까지 보는 축으로 좁히면 모집단이 달라진다 — "
                f"{_n('combo_verdict.statement', S2R)}",

                f"레벨 규약은 우리 앵커 파일 둘(`src/sigma_anchor.py` · "
                f"`outputs/rcs_anchor.json`) 사이에서 갈린다 — 잔차 최소화 변환을 쓰는 쪽이 "
                f"{_n('anchors.level_convention_split.pipeline_offset_db', SURVEY, '{:.2f}', 'dB')} "
                f"만큼 밝다.",
            ],
            method=[
                ("관문 판정", "후보별 4관문 판정으로 따로 센다 "
                            "(`src/report01_paper_facts.py:scorecard`) — 깔때기와 모집단이 다르다"),
                ("P1 규칙", "지면 기록이 있는 프로시딩을 P1 통과로 정의했다. 이 정의는 우리 "
                          "신규성을 좁히는 쪽이다"),
                ("우리 축의 값", "축마다 그 값이 나온 편과 근거 JSON 을 같은 행에 붙였다"),
                ("앵커 규약", "우리 앵커 파일 둘이 같은 인쇄값을 다른 통계로 읽는다 — "
                            "`outputs/rcs_anchor.json` 은 인쇄값을 그대로 싣고, "
                            "`src/sigma_anchor.py` 는 그것을 dB 방위평균으로 읽어 선형평균으로 "
                            "옮긴다. 생산 경로는 기울기만 쓴다"),
            ],
            repro=_repro([_SURVEY_CMD, _PAPER_CMD, _FIGS_CMD],
                         [SURVEY, PAPER, KR, CFAR, S2R],
                         "약 1분 (CPU 만 쓴다)",
                         "신규성 문단과 방법 문단은 리포트에서 빼서 docs/paper/ 로 옮겼다"),
        ),

        md("## 실측 전이까지 보면 모집단이 달라진다", "",
           f"sim-to-real 정찰의 센서스가 그 범위를 문장 안에 적는다 — "
           f"{_n('combo_verdict.statement', S2R)}", "",
           "세 요소는 사이트트윈 · 계산 σ · 분류이고, 거기에 실측 전이 보고까지 본 것이다. "
           "최근접은 LAMBDA 다."),

        md("## 네 관문", "",
           f"드론 메쉬에서 계산한 산란 서명을 Sionna 계열 엔진 안에서 검증한 **게재** 논문은 "
           f"{_n('h8.n_passing_all_prongs', PAPER, '{:.0f}', '편')} 이다. 네 관문으로 쪼개 후보마다 "
           f"따로 판정했고, P1 은 집계가 적용한 규칙 그대로 적는다.", "",
           table_from((PAPER, "h8.prongs"), [("관문", "prong"), ("통과 조건", "test_ko")])),

        md("## 후보마다 어느 관문에서 걸리는가", "",
           *_fig(1, "report01_p4_prongs", "후보마다 어느 관문에서 걸리는가?"), "",
           f"후보 {_n('h8.n_adjudicated', PAPER, '{:.0f}', '편')} 을 관문별로 판정했고, 넷을 동시에 "
           f"통과한 편은 {_n('h8.n_passing_all_prongs', PAPER, '{:.0f}', '편')} 이다. 가장 가까운 "
           f"셋은 각각 다른 관문에서 걸린다.", "",
           table_from((SURVEY, "h8.near_miss"),
                      [("가장 가까운 편", "paper"), ("남은 간격", "gap_ko")], order=[0, 1, 2])),

        md("## 우리 파이프라인이 각 축에서 한 일", "",
           "우리는 Sionna 의 Mitsuba/OptiX 광선엔진으로 first-hit(광선이 처음 부딪히는 면만 "
           "조명면으로 치는 판정) 가림을 풀고, 조명면 위에 부품별 재질 PO 를 적분한다. "
           "레벨과 주파수 의존성은 측정 적합계수에서 받는다.", "",
           table(["축", "우리가 한 일", "값", "어디서 자세히"],
                 [["자세 패턴", "광선엔진 first-hit 가림 + 조명면 PO 적분, 부품별 재질",
                   f"해석 PO 구 대비 {_n('summary_div16.max_abs_db_vs_po', KR, '{:.3f}', 'dB')}, "
                   f"입사 {_n('meta.n_incidence', KR, '{:.0f}', '방향')}",
                   ref("kernel-vs-reference", short=True)],
                  ["절대 레벨 · 밴드 기울기", "A(f)·B1(φ)·B2 분해로 Das 적합계수에 정렬",
                   _n("anchors.das.mu_a_db_per_ghz", SURVEY, "{:.2f}", "dB/GHz"),
                   ref("anchor-mode", short=True)],
                  ["바이스태틱", "수신기 방향 그림자 광선으로 출사쪽 가시성 판정",
                   "β ≤ " + _n('d2_exit_vis_effect_on_reciprocity.beta_deg[3]', DFX,
                               '{:.0f}', '°'),
                   ref("bistatic-exit", short=True)],
                  ["검출", "경험 Pfa(실제로 울린 오경보율)로 CFAR 문턱 교정",
                   "GPU 몬테카를로 " + _n("meta.runtime_s", CFAR, "{:.0f}", "s"),
                   ref("cfar-calib", short=True)],
                  ["파형 비교", "한 표적 · 한 검출기로 LTE · 5G · WiFi",
                   "점유 · 대역폭 · PRF(펄스 반복 주파수)", ref_part(8)],
                  ["조달", "σ 를 광선엔진 안에서 계산해 같은 엔진의 경로에 싣는다",
                   "게재 확정 주입 "
                   + _n("corrected_tally.peer_reviewed_confirmed_injections",
                        INJ_AUDIT, "{:.0f}", "편")
                   + " 은 σ 를 낸 곳과 쓰는 곳이 다른 엔진이다",
                   ref("injection", short=True)]])),

        md("## 앵커의 세 문헌, 그리고 규약이 갈리는 자리", "",
           "Das 는 평균을 **측정한 방위 구간의 선형평균**으로 정의하고(Phantom 3 는 반평면), "
           "Zhang 식 (15)는 전 각도의 선형평균이다. Yuan 은 정의를 적지 않으므로 같은 축으로 "
           f"읽는 것은 우리 추론이다 ⟨{SURVEY} : anchors.yuan.statistic_ko⟩.", "",
           table(["문헌", "기체 · 대역", "기울기", "우리가 쓰는 자리"],
                 [["Das (IEEE WCL 2026)",
                   "Phantom 3 · " + _n("anchors.das.band_ghz[0]", SURVEY, "{:.1f}") + "–"
                   + _n("anchors.das.band_ghz[1]", SURVEY, "{:.1f}", "GHz"),
                   _n("anchors.das.mu_a_db_per_ghz", SURVEY, "{:.2f}", "dB/GHz"), "기울기 앵커"],
                  ["Yuan (EuCAP 2025)", "Phantom 3 · 같은 실험실 · VV",
                   _n("anchors.yuan.slopes_db_per_ghz.theta90", SURVEY, "{:.3f}", "dB/GHz"),
                   "고도 3측면 대조"],
                  ["Zhang (IEEE JSAC 2026)", "M350 · 10–36 GHz",
                   _n("anchors.zhang.a_slope_db_per_ghz", SURVEY, "{:.2f}", "dB/GHz"),
                   "분해 σ=A(f)·B1(φ)·B2 형식"]]), "",
           f"⚠ 위 표의 대역은 **앵커로 쓰는 부분**이다 — Das 논문 자체는 "
           f"{_n('papers[1].target_ko', SURVEY)} 를 재고, 우리가 끊어 쓰는 것은 그중 "
           f"{_n('anchors.das.platform', SURVEY)} 한 대의 구간이다.", "",
           f"Das 의 Phantom 3 자료는 Das 자신의 참고문헌 [7](Wang 외, China Communications)에서 "
           f"왔고 ⟨{SURVEY} : anchors.das.provenance_ko⟩, 우리가 쓰는 것은 그 기울기 하나다. "
           f"우리가 앵커로 받는 통계 정의를 원장은 이렇게 적는다: "
           f"{_n('anchors.das.statistic_ko', SURVEY)}.", "",
           f"레벨 규약이 갈리는 자리는 우리 앵커 파일 둘이다 — `outputs/rcs_anchor.json` 은 "
           f"인쇄값을 그대로 들고, `src/sigma_anchor.py` 는 같은 인쇄값을 "
           f"{_n('anchors.level_convention_split.sigma_anchor_statistic', SURVEY)} 으로 읽어 "
           f"선형평균으로 옮기므로 "
           f"{_n('anchors.level_convention_split.pipeline_offset_db', SURVEY, '{:.2f}', 'dB')} "
           f"만큼 밝다. 원장은 그 갈림을 "
           f"{_n('anchors.level_convention_split.status', SURVEY)} 로 적고, 규약을 하나로 맞추는 "
           f"자리가 {ref('anchor-mode')} 다."),

        next_steps([
            ("`src/sigma_anchor.py` 와 `outputs/rcs_anchor.json` 의 통계 규약을 하나로 맞춘다",
             f"앵커 레벨 "
             f"{_n('anchors.level_convention_split.pipeline_offset_db', SURVEY, '{:.2f}', 'dB')} "
             f"가 어느 쪽으로 확정된다",
             ref("anchor-mode", short=True)),
            ("Rzewuski 의 FDTD σ(WiFi 대역 −40~0 dBsm)를 우리 σ 격자와 같은 축에 올린다",
             "우리 WiFi 대역 σ 가 독립 full-wave 결과와 몇 dB 떨어져 있는지 확정된다",
             ref("anchor-ledger", short=True)),
            ("Das 의 참고문헌 [7](Wang 외, China Communications)을 입수해 원 측정 조건을 대조한다",
             "기울기 앵커의 편파·자세 구간이 우리 격자와 같은 축인지 확정된다",
             "`src/report01_paper_facts.py:anchor_provenance`"),
            ("sim-to-real 센서스를 실측 사이트 축으로 좁혀 다시 건다",
             "사이트트윈 + 계산 σ + 검출 조합의 최근친이 확정된다",
             "`outputs/s2r_prior.json`"),
            ("덱 축자 감사가 낸 정정을 카탈로그 행에 전파한다",
             "선행 서술이 원문 축자와 한 축에 선다",
             ref("procurement-catalog", short=True)),
        ]),
    ]


# =========================================================================== #
#  편 14 — borrowed
# =========================================================================== #
def report_14_borrowed():
    return [
        header(
            num=14,
            title="선행에서 빌린 절차와 아직 안 빌린 절차를 비용과 함께 센다",
            did="선행에서 이미 빌린 절차와 아직 안 빌린 절차를 순위·비용과 함께 세고, "
                "의도적으로 안 빌린 셋에는 그 이유를 붙였다.",
            results=[
                f"이미 빌린 절차는 "
                f"{len(fetch((POC, 's5_prior_work.already_borrowed')))}가지이고, 항목마다 "
                f"«어디서 빌렸나» 와 «그것이 사 준 것» 을 같은 행에 적었다.",

                f"아직 안 빌린 절차는 "
                f"{len(fetch((POC, 's5_prior_work.not_yet_borrowed')))}가지이고 순위와 비용이 "
                f"붙어 있다 — 맨 위 두 줄이 이 편의 다음 단계와 같다.",

                f"의도적으로 안 빌린 것은 "
                f"{len(fetch((POC, 's5_prior_work.deliberately_not_borrowed')))}가지다. "
                f"«{_n('s5_prior_work.deliberately_not_borrowed[1].what', POC)}» 가 그중 하나다.",

                f"밴드 기울기 앵커 "
                f"{_n('anchors.das.mu_a_db_per_ghz', SURVEY, '{:.2f}', 'dB/GHz')} 는 빌린 쪽의 "
                f"대표 항목이고, 그 값이 우리 σ 의 주파수 축을 정한다.",
            ],
            method=[
                ("빌린 것의 정의", "절차·규약·값 중 선행 문헌에서 그대로 가져온 것만 센다 — "
                                 "영감이나 문제의식은 세지 않는다"),
                ("순위와 비용", "안 빌린 항목마다 그것을 빌이는 데 드는 비용을 함께 적는다 — "
                              "순위가 곧 다음 단계의 순서다"),
                ("안 빌린 이유", "도구가 다르면 그 이유를 문장으로 적는다. «필요 없다» 로 "
                               "끝내지 않는다"),
            ],
            repro=_repro(["PYTHONPATH=src python benchmark/build_report00_po_case.py"],
                         [POC], "약 1분 (GPU 0장 — JSON 읽기다)"),
        ),

        md("## 선행에서 무엇을 빌렸나", "",
           f"⚠ 원장이 든 옛 권 이름은 현행 주소({ref_part(5)})로 바꿔 싣는다 — 원장은 읽기 "
           f"전용이므로 치환은 렌더 단계에서만 한다.", "",
           _relabel(table_from(f"{POC}:s5_prior_work.already_borrowed",
                               [("빌린 것", "what"), ("어디서", "from"),
                                ("그것이 사 준 것", "what_it_bought")]))),

        md("## 아직 안 빌린 것 — 순위와 값", "",
           _relabel(table_from(f"{POC}:s5_prior_work.not_yet_borrowed",
                               [("순위", "rank"), ("무엇을", "what"),
                                ("어디서", "from"), ("비용", "cost")]))),

        md("## 의도적으로 안 빌린 것", "",
           f"맨 위 두 줄이 이 편의 다음 단계와 같다 — 유효성 바닥을 기체 × 밴드 표로 인쇄하는 "
           f"일과, 정준체를 캠페인 패드에 올려 절대 σ 에 처음으로 실측 검사를 붙이는 일이다.", "",
           f"의도적으로 안 빌린 것도 "
           f"{len(fetch((POC, 's5_prior_work.deliberately_not_borrowed')))}가지다. "
           f"«{_n('s5_prior_work.deliberately_not_borrowed[1].what', POC)}» 가 그중 하나이고, "
           f"이유는 도구가 다르다는 것이다: D 는 σ 가 아니라 경로계수를 만들고, wedge 각을 "
           f"인접 두 면의 법선에서 읽으므로 면분할된 셸에서 그 각은 기체의 성질이 아니라 "
           f"**우리 메싱의 성질**이 된다.", "",
           f"⭐ 그래서 이 표는 «빚 목록» 이 아니라 **다음 라운드의 작업 순서**다. 같은 목록이 "
           f"{ref('kernel-open-items')} 의 열린 항목과 짝을 이룬다."),

        next_steps([
            ("공개된 세 유효성 바닥을 기체 × 밴드 표로 인쇄한다",
             "«전기적 소형» 이 고백에서 표가 되고, 어느 기체·어느 밴드가 공개 바닥 아래인지가 "
             "행 단위로 확정된다",
             "`benchmark/verify_sbr_kr_sweep.py` → " + ref("po-knee", short=True)),
            ("정준체(구·원통)를 캠페인 패드에 올려 우리 커널과 같은 자로 잰다",
             "절대 σ 에 처음으로 실측 검사가 붙는다 — 레벨이 자체 앵커를 갖는다",
             ref("calibration-sphere", short=True)),
            ("PO 면적분을 편파 있는 커널로 올린다",
             "가장 가는 시험 폭에서 참값이 갈라지는 크기가 우리 σ 의 어느 쪽 오차인지가 확정된다",
             "`src/rcs_sbr.py` → " + ref("kernel-open-items", short=True)),
        ]),
    ]


# =========================================================================== #
#  논문 문단 두 개 — 리포트에서 빼서 docs/paper/ 로 옮긴다
#  (사용자 지시: 논문 작성 측면은 리포트에 쓰지 않고 따로 메모한다)
# =========================================================================== #
NOVELTY = [
    "Prior work obtains a UAV target signature along one of seven routes, and the route fixes "
    "the size of the claim a paper can make: chamber measurement buys an absolute RCS for one "
    "airframe, an external full-wave solver buys a bistatic RCS and the coverage budget that "
    "consumes it, injection of a pre-computed RCS buys aspect-dependent amplitude without "
    "touching the engine, an analytic blade model buys the shape of a micro-Doppler signature, "
    "an abstract coefficient buys a closed-form signal model, and the stock interactions of a "
    "ray engine buy kinematic structure.",
    "We adjudicate twelve candidates against four prongs — (P1) published in a venue of record, "
    "(P2) the UAV carried as a 3-D surface mesh, (P3) the scattered field computed inside a "
    "Sionna-class differentiable GPU ray engine, and (P4) the computed amplitude compared "
    "against measurement or a reference solution — and no candidate satisfies all four. "
    "Two qualifications bound that statement.",
    "First, the end product exists in published prior art: Rzewuski et al. [4] solved the "
    "monostatic and bistatic RCS of a Parrot AR.Drone with FDTD, fed it into a passive-radar "
    "coverage budget, and closed with an over-the-air detection at 50 m; the whole of their gap "
    "to our four prongs is the engine prong. Our contribution is therefore the engine, its "
    "integration into a single pipeline, and the calibrated waveform comparison it enables.",
    "Second, the word published carries the claim: with preprints admitted the gap narrows to a "
    "seam, because LAMBDA [14] ships UAV RCS beside Sionna ray paths and the journal version of "
    "Ziganshin et al. [12] validates mesh scattering inside Sionna against a bistatic "
    "measurement, a validation its authors themselves call qualitative. Neither work does both, "
    "and neither has been refereed.",
]


def _method_para() -> str:
    g = lambda k: num(None, (SURVEY, k))          # noqa: E731
    return (
        f"Literature adjudication. We term-swept n_pdfs={g('meta.corpus_swept_pdfs')} paper PDFs "
        "across two ISAC/Sionna archives and a passive-radar corpus with PyMuPDF 1.28.0, "
        f"extracted the full text of n_documents={g('counts.papers')} of them, and adjudicated "
        "each against four prongs: (P1) published in a venue of record, (P2) the UAV carried as "
        "a 3-D surface mesh, (P3) the scattered field computed inside a Sionna-class "
        "differentiable GPU ray engine, (P4) the computed amplitude compared against measurement "
        "or a reference solution. Every factual line carries a verbatim quotation that the build "
        "re-locates on the named PDF page and the build aborts when a quotation is not found "
        f"there; n_quotes={g('counts.quotes_verified')} quotations currently re-locate. "
        "Publication status was fixed per document from the PDF metadata subject field written "
        "by IEEE typesetting, from the page footer stamp, and from the arXiv stamp; an "
        "acceptance sentence inside the body of an arXiv manuscript scores partial and the "
        "document remains a preprint, which is the rule under which every count in this report "
        "was computed. Engine facts were read first-hand from the Sionna RT technical report "
        f"(document {g('engine.technical_report.version')}, {g('engine.technical_report.pages')} "
        "pages) and from the installed Sionna 2.0.1 package, whose sionna.rt namespace was "
        "enumerated programmatically."
    )


def write_paper_docs() -> list[str]:
    """report01 c20(신규성 문단) · c23(방법 문단) → `docs/paper/` 두 파일."""
    d = os.path.join(_ROOT, "docs", "paper")
    os.makedirs(d, exist_ok=True)
    out = []

    p = os.path.join(d, "00_novelty.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write("<!-- from: 편 13 where-we-stand (구 report01_prior.ipynb c20) -->\n")
        f.write("# 신규성 문단 — 논문 II 절에 그대로 붙인다\n\n")
        f.write("참조번호 [4] · [12] · [14] 는 `outputs/report01_paper.json:citations` 의 "
                "`n` 번호를 가리킨다 (Rzewuski · Ziganshin 저널판 · LAMBDA).\n\n")
        for para in NOVELTY:
            f.write("> " + para + "\n>\n")
        f.write("\n## 두 단서의 근거\n\n")
        f.write("- **Q1** — Rzewuski 는 Parrot AR.Drone 2.0 의 모노·바이스태틱 RCS 를 "
                "FDTD(QuickWave-3D)로 풀어 WiFi 대역 −40~0 dBsm 을 보고하고(p.5), 패시브 "
                "커버리지 예산을 세워 바이스태틱 50 m 실측 검출까지 닫았다(p.9) "
                "⟨outputs/report01_paper.json : h8.q1_counter_paper⟩.\n")
        f.write("- **Q2** — Ziganshin 저널판은 검증을 저자 스스로 정성적이라 적는다(p.7) "
                "⟨outputs/prior_settled_h8.json : h8_candidates⟩.\n")
        f.write("- **주입** — 주입 아키텍처 자체는 이미 게재돼 있다. 재판독으로 확정된 게재 주입 "
                + num(None, (INJ_AUDIT,
                             "corrected_tally.peer_reviewed_confirmed_injections"),
                      "{:.0f}", "편")
                + " 은 전부 자기 서명을 실측 또는 기준체와 맞대고 수치를 인쇄했다.\n")
        f.write("\n생성기: `src/build_part02_prior_work.py:write_paper_docs`\n")
    out.append(p)

    p = os.path.join(d, "01_prior.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write("<!-- from: 부 2 선행연구 (구 report01_prior.ipynb c23 methods) -->\n")
        f.write("# 방법 문단 — Literature adjudication\n\n")
        f.write("도구: PyMuPDF 1.28.0 · Sionna 2.0.1 · Python 3.12\n\n")
        f.write(_method_para() + "\n\n")
        f.write("생성기: `src/build_part02_prior_work.py:write_paper_docs`\n")
    out.append(p)
    return out


# =========================================================================== #
REPORTS = [
    ("census-published", report_08_census_published),
    ("census-preprint", report_09_census_preprint),
    ("procurement", report_10_procurement),
    ("procurement-catalog", report_11_procurement_catalog),
    ("injection", report_12_injection),
    ("where-we-stand", report_13_where_we_stand),
    ("borrowed", report_14_borrowed),
]


def main() -> int:
    print(f"── 부 2 「선행연구」 — 편 {len(REPORTS)}개 ──")
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
    for p in write_paper_docs():
        print(f"  📝 {os.path.relpath(p, _ROOT)}")
    print(f"── {len(REPORTS) - bad}/{len(REPORTS)} 통과 ──")
    return bad


if __name__ == "__main__":
    sys.exit(main())
