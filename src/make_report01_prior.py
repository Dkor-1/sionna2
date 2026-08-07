# -*- coding: utf-8 -*-
"""
make_report01_prior.py — 리포트 01 「선행연구」 빌더  →  report01_prior.ipynb
============================================================================================
계약서 **두 장**이 동시에 걸린다.

| 계약 | 무엇을 정하나 | 강제 |
|---|---|---|
| `docs/REBUILD_2026-07-30.md` §5 | 서술 규약(여는 블록·톤·분량) | `src/report_style.py` |
| `docs/PAPER_SPEC.md` §4 | 논문 참고자료 규격(대응·방어선·그림·방법·인용) | `src/paper_kit.py` |

이 편이 한 일 하나
    **아카이브 문서 21건의 전문을 판정해, 각 편이 표적 서명을 어디서 조달했고 그 조달처가
    무슨 주장을 사 주었는지 카탈로그로 만들고, H8 을 네 관문으로 후보별 판정했다.**
    §3.4 는 그 카탈로그를 아카이브 전수(고유문서 327편)로 한 번 더 세어 **주입의 좁은/넓은 정의**와
    **게재본이 인쇄한 검증**을 갈라 적는다.

이 편이 먹이는 논문 절 (PAPER_SPEC §3)
    **I. Introduction / II. Related Work** — 조달전략 카탈로그 · 신규성 문단 · H8 4관문 ·
    게재상태가 붙은 인용 목록.

근거 파일 세 갈래
    `outputs/prior_work_survey.json`   — 21건 전문 판정 · 갈래 · 낱말 빈도 · 앵커
                                          (`prior_work/src/build_prior_survey.py`, PDF 원문 대조)
    `outputs/report01_paper.json`      — 논문 파생 원장: 4관문 집계 12편 · 인용 21건 · 갈래별 게재수
                                          (`src/report01_paper_facts.py`)
    `outputs/sbr_kr_sweep.json` · `outputs/verify_cfar.json` — §4.2 가 인용하는 다른 편의 근거

조사 원장 (다른 워크플로 산출 · 이 빌더는 **읽기만** 한다)
    `outputs/injection_archive.json` · `injection_classification_audit.json` ·
    `injection_verdict.json` · `injection_validation_hunt.json` — §3.4 주입 3갈래
    `outputs/facet_attack.json`  — §3.4 클러터 서베이 41쪽 전문 계수
    `outputs/s2r_prior.json`     — §4 · §5 sim-to-real 조합 센서스
    `outputs/tm_claims.json` · `tm_verify_rest.json` — 여는 블록 «검증 규약» · §5 정정 전파

그림 4장은 `src/figs_report01.py` 가 게재 규격(벡터 PDF + 400 dpi PNG · 9 pt · 색+해치)으로 그린다.

이 파일이 하는 일
    JSON 을 읽어 노트북을 조립하는 것뿐이다. **계산도 그림도 여기서 새로 하지 않는다** —
    근거와 서술을 한 파일에 섞지 않기 위해서다.

실행
    cd /home/yunjung/workspace/sionna2
    ~/.venvs/py312/bin/python prior_work/src/build_prior_survey.py       # ① 근거
    PYTHONPATH=src ~/.venvs/py312/bin/python src/report01_paper_facts.py # ② 논문 원장
    PYTHONPATH=src ~/.venvs/py312/bin/python src/figs_report01.py        # ③ 그림 4장
    PYTHONPATH=src ~/.venvs/py312/bin/python src/make_report01_prior.py  # ④ 리포트

⚠ GPU 도 Sionna 실행도 필요 없다. 전부 합쳐 수십 초.
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (_HERE, os.path.join(_ROOT, "benchmark")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from paper_kit import (attach, cite, defence, figure_md, methods,        # noqa: E402
                       paper_appendix, paper_map)
from report_style import (build_notebook, from_json, header, md,         # noqa: E402
                          next_steps, table, table_from)

SURVEY = "outputs/prior_work_survey.json"
PAPER = "outputs/report01_paper.json"
KR = "outputs/sbr_kr_sweep.json"
CFAR = "outputs/verify_cfar.json"
NB_OUT = os.path.join(_ROOT, "report01_prior.ipynb")

#: §3.4 · §4 · 여는 블록이 읽는 조사 원장 — 전부 다른 워크플로가 낸 산출물이고 여기서는 인용만 한다.
#:   주입 3갈래 : 인구조사(archive) → 재판독 감사(classification_audit) → 검증 사냥(validation_hunt)
#:   클러터 서베이 전문 계수 : facet_attack.attack_5_clutter_survey
#:   sim-to-real 센서스 : s2r_prior · 덱 축자 감사 : tm_claims · tm_verify_rest
INJ_ARCHIVE = "outputs/injection_archive.json"
INJ_AUDIT = "outputs/injection_classification_audit.json"
INJ_VERDICT = "outputs/injection_verdict.json"
INJ_HUNT = "outputs/injection_validation_hunt.json"
CLUTTER = "outputs/facet_attack.json"
S2R = "outputs/s2r_prior.json"
TM_CLAIMS = "outputs/tm_claims.json"
TM_VERIFY = "outputs/tm_verify_rest.json"

FIGS = {
    "funnel": "outputs/figures/report01_p1_funnel.png",
    "routes": "outputs/figures/report01_p2_routes.png",
    "dbsm": "outputs/figures/report01_p3_dbsm.png",
    "prongs": "outputs/figures/report01_p4_prongs.png",
}

#: survey JSON 의 `papers` 배열은 순서가 고정돼 있다(게재 0~10 · 프리프린트 11~20).
#: 표를 쪼갤 때 이름이 아니라 이 인덱스로 뽑는다 — 표 하나에 출처 하나가 되도록.
PUB_OUTSIDE = [0, 1, 2, 3, 4, 5, 6]      # 게재본, 광선엔진 밖에서 서명을 얻은 쪽
PUB_ENGINE = [7, 8, 9, 10]               # 게재본, 광선엔진을 직접 돌리는 쪽
PRE_A = [11, 12, 13, 14, 15]             # 프리프린트 (1/2)
PRE_B = [16, 17, 18, 19, 20]             # 프리프린트 (2/2)
CAT = [[0, 1, 2, 3, 4, 5, 6], [7, 8, 9, 10, 11, 12, 13], [14, 15, 16, 17, 18, 19, 20]]

#: §2 센서스 — 행마다 게재처·연도·상태가 붙는다.
CENSUS_COLS = [("논문", "short_ko"), ("게재처 · 연도", "venue_status_ko"),
               ("상태", "status_ko"), ("엔진 안 표적", "target_ko")]
#: §3 조달 카탈로그 — 어디서 가져왔고, 그것이 무슨 주장을 사 주었고, 그 편은 게재본인가.
#:  ⭐ 논문 II 절 표의 원형이다. 그래서 게재상태 열이 붙는다(PAPER_SPEC §4.5).
CAT_COLS = [("논문", "short_ko"), ("상태", "status_ko"),
            ("표적 서명의 조달처", "route_tag"), ("그 편이 산 주장", "claimed_ko")]
ROUTE_COLS = [("갈래", None), ("조달처", "label_ko"),
              ("그것이 사 주는 주장", "bought_ko"), ("문서", "papers"), ("게재", "published")]

# --------------------------------------------------------------------------- #
#  ⭐ 논문 II 절에 그대로 붙이는 신규성 문단 — 이 리포트에서 가장 위험한 문장이다.
#     H8 을 네 관문 그대로 나르고, 두 단서(Q1 Rzewuski · Q2 게재/프리프린트)를 데리고 다닌다.
#     참조번호 [4] [12] [14] 는 아래 인용 목록의 번호와 같다(Rzewuski · Ziganshin 저널판 · LAMBDA).
# --------------------------------------------------------------------------- #
NOVELTY = [
    "> Prior work obtains a UAV target signature along one of seven routes (Fig. 2), and the "
    "route fixes the size of the claim a paper can make: chamber measurement buys an absolute RCS "
    "for one airframe, an external full-wave solver buys a bistatic RCS and the coverage budget "
    "that consumes it, injection of a pre-computed RCS buys aspect-dependent amplitude without "
    "touching the engine, an analytic blade model buys the shape of a micro-Doppler signature, an "
    "abstract coefficient buys a closed-form signal model, and the stock interactions of a ray "
    "engine buy kinematic structure.",
    "> We adjudicate twelve candidates against four prongs — (P1) published in a venue of record, "
    "(P2) the UAV carried as a 3-D surface mesh, (P3) the scattered field computed inside a "
    "Sionna-class differentiable GPU ray engine, and (P4) the computed amplitude compared against "
    "measurement or a reference solution — and no candidate satisfies all four (Fig. 4). Two "
    "qualifications bound that statement.",
    "> First, the end product exists in published prior art: Rzewuski et al. [4] solved the "
    "monostatic and bistatic RCS of a Parrot AR.Drone with FDTD, fed it into a passive-radar "
    "coverage budget, and closed with an over-the-air detection at 50 m; the whole of their gap to "
    "our four prongs is the engine prong. Our contribution is therefore the engine, its "
    "integration into a single pipeline, and the calibrated waveform comparison it enables.",
    "> Second, the word published carries the claim: with preprints admitted the gap narrows to a "
    "seam, because LAMBDA [14] ships UAV RCS beside Sionna ray paths and the journal version of "
    "Ziganshin et al. [12] validates mesh scattering inside Sionna against a bistatic measurement, "
    "a validation its authors themselves call qualitative. Neither work does both, and neither has "
    "been refereed.",
]

#: PAPER_SPEC §4.4 — 논문에 그대로 옮기는 재현 가능한 방법 한 문단(영문).
METHOD_PARA = (
    "Literature adjudication. We term-swept n_pdfs=178 paper PDFs across two ISAC/Sionna archives "
    "and a passive-radar corpus with PyMuPDF 1.28.0, extracted the full text of n_documents=21 of "
    "them, and adjudicated each against four prongs: (P1) published in a venue of record, (P2) the "
    "UAV carried as a 3-D surface mesh, (P3) the scattered field computed inside a Sionna-class "
    "differentiable GPU ray engine, (P4) the computed amplitude compared against measurement or a "
    "reference solution. Every factual line carries a verbatim quotation that the build re-locates "
    "on the named PDF page and the build aborts when a quotation is not found there; n_quotes=46 "
    "quotations currently re-locate. Publication status was fixed per document from the PDF "
    "metadata subject field written by IEEE typesetting, from the page footer stamp, and from the "
    "arXiv stamp; an acceptance sentence inside the body of an arXiv manuscript scores partial and "
    "the document remains a preprint, which is the rule under which every count in this report was "
    "computed. Engine facts were read first-hand from the Sionna RT technical report (document "
    "Version 1.2, 59 pages) and from the installed Sionna 2.0.1 package, whose sionna.rt namespace "
    "was enumerated programmatically."
)


# --------------------------------------------------------------------------- #
def citations(C) -> list[str]:
    """`outputs/report01_paper.json:citations` 를 논문 형식 인용 21건으로 (§4.5).

    `cite()` 가 게재상태를 **필수**로 검사하고, 프리프린트는 arXiv ID 가 없으면 예외를 낸다.
    번호는 JSON 의 `n` 순서 그대로이며 신규성 문단의 [4] · [12] · [14] 가 이 번호를 가리킨다.
    """
    out = []
    for c in C.get("citations"):
        out.append(cite(authors=c["authors"], title=c["title"], venue=c["venue"],
                        volume=c["volume"], pages=c["pages"], year=c["year"],
                        status=c["status"], arxiv=c["arxiv"], doi=c["doi"],
                        note=c["note"]))
    return out


def defence_rows(P, C, V):
    """§4.2 방어선 — 이 편이 논문에 넣는 주장마다 (근거 · 심사자의 공격 · 우리 답)."""
    return [
        ("표적 서명의 조달처는 일곱 갈래이고, 고른 갈래가 그 편이 낼 수 있는 주장의 크기를 정한다",
         "그림 2 · `outputs/report01_paper.json:route_status`",
         "일곱 갈래는 저자가 사후에 만든 범주다",
         f"갈래마다 그 편의 축자 인용을 PDF 쪽 번호와 함께 붙였고, 인용 "
         f"{P.num('counts.quotes_verified', 46, '{:.0f}')}건은 빌드가 그 쪽에서 다시 찾는다"),

        (f"드론 표면메쉬의 산란 진폭을 Sionna 급 광선엔진 안에서 계산해 검증한 게재 논문은 "
         f"{C.num('h8.n_passing_all_prongs', 0, '{:.0f}')}편이다",
         "그림 4 · `outputs/report01_paper.json:h8.scorecard`",
         "Rzewuski 등(NATO STO 2021)이 WiFi 대역 드론 바이스태틱 RCS 를 이미 냈다",
         "그 편은 P3 에서 걸린다 — 엔진이 FDTD full-wave 다. 게재본과 프리프린트를 갈라 세는 것이 "
         "이 주장의 전부이고, 우리 기여는 엔진과 파이프라인 통합이다"),

        ("프리프린트를 넣으면 간극은 이음매로 좁아진다",
         "그림 4 · `outputs/prior_settled_h8.json:H8.mandatory_qualification_2.text`",
         "그렇다면 사실상 선행이 존재하는 것 아닌가",
         "LAMBDA 는 σ 를 CADFEKO 에서 받아 광선경로에 주입하고, Ziganshin 저널판은 차량을 푼다. "
         "두 칸을 한 편에서 채우는 자리가 우리 자리다"),

        ("Rzewuski 를 P1 통과로 세고, 그 편을 H8 후보 모집단 안에 넣는다",
         "그림 4 · `outputs/report01_paper.json:h8.rzewuski_venue_note_ko`",
         "NATO STO 회의 프로시딩을 동료심사 지면으로 세는 근거는 무엇인가",
         "지면 기록이 있는 프로시딩을 P1 통과로 정의했다 "
         "⟨outputs/report01_paper.json : h8.p1_rule_ko⟩. 이 정의는 우리 신규성을 좁히는 쪽이다"),

        ("본문에 지면 채택을 적은 arXiv 원고는 `일부` 로 세고 프리프린트로 남긴다",
         "표 §4.1 · `outputs/report01_paper.json:h8.p1_rule_ko`",
         "Sagitta 와 FWA 협동센싱은 본문에 채택 문장이 있으니 게재로 세야 한다",
         "그 규칙으로 올려도 H8 판정은 그대로다 — Sagitta 는 P2·P3 에서, FWA 협동센싱은 P2 에서 "
         "걸린다 ⟨outputs/report01_paper.json : h8.scorecard⟩"),

        (f"판정한 문서는 {C.num('corpus.documents', 21, '{:.0f}')}건이고 저작 단위로는 "
         f"{C.num('corpus.distinct_works', 19, '{:.0f}')}편이다",
         "§2 · `outputs/report01_paper.json:corpus.version_pairs`",
         "Costa 와 Ziganshin 을 두 번 세어 표본을 부풀렸다",
         "판마다 게재상태와 보고량이 달라 판 단위로 센다 "
         "⟨outputs/report01_paper.json : corpus.version_pairs_ko⟩. 저작 수를 §2 에 함께 적는다"),

        (f"밴드 기울기 앵커는 Das 의 적합계수 "
         f"{P.num('anchors.das.mu_a_db_per_ghz', 0.21, '{:.2f}', 'dB/GHz')} 다",
         "§4.3 · `outputs/prior_work_survey.json:anchors.das.mu_a_db_per_ghz`",
         "Das 는 Phantom 3 를 직접 재지 않았다 — 원 자료는 참고문헌 [7] 에서 왔다",
         "그 귀속을 §4.3 에 적는다 ⟨outputs/prior_work_survey.json : anchors.das.provenance_ko⟩. "
         "우리가 쓰는 것은 기울기 하나이고, 절대 레벨은 세 밴드 공통이라 파형 순위에서 상쇄된다"),

        ("Sionna RT 스톡 솔버는 광선을 쏘고 튕기며, 표면전류 면적분은 그 위에 얹히는 층이다",
         "§1 · `outputs/prior_work_survey.json:engine.technical_report.term_counts.sbr`",
         "'Sionna 에 SBR 이 없다' 고 적은 자료를 봤다",
         f"기술보고서 v1.2 전문에서 `SBR` 을 세면 "
         f"{P.num('engine.technical_report.term_counts.sbr', 44, '{:.0f}')}회다. 스톡에 없는 것은 "
         f"면적분과 RCS 출력이고, 그 두 층이 우리가 얹은 것이다"),

        (f"전문에 `CFAR` 도 `false alarm` 도 0회인 논문이 "
         f"{P.num('counts.zero_cfar_and_false_alarm', 14, '{:.0f}')}편이다",
         "그림 3 · `outputs/prior_work_survey.json:counts.zero_cfar_and_false_alarm`",
         "낱말 빈도가 방법을 재는 척도인가",
         f"낱말 0회는 필요조건 검사다. 오경보 바닥을 경험 Pfa 로 교정하는 일은 04편이 GPU "
         f"몬테카를로 {V.num('meta.runtime_s', fmt='{:.0f}', unit='s')} 로 수행한다"),
    ]


# --------------------------------------------------------------------------- #
def blocks(P, C, S, V):
    B = []

    #: 이번 편이 인용하는 조사 원장 — 값만 읽는다(계산 없음).
    IA = from_json(INJ_AUDIT)      # 주입 인구조사 재판독 감사
    IV = from_json(INJ_VERDICT)    # 주입 사례 마스터표(넓은 정의)
    IH = from_json(INJ_HUNT)       # 주입 σ 검증 사냥(좁은 정의)
    IR = from_json(INJ_ARCHIVE)    # 주입 인구조사(모집단 크기)
    CL = from_json(CLUTTER)        # 클러터 서베이 전문 계수
    SR = from_json(S2R)            # sim-to-real 센서스
    TC = from_json(TM_CLAIMS)      # 덱 주장 추출
    TV = from_json(TM_VERIFY)      # 덱 주장 축자 판정

    # ── 여는 블록 + 논문 대응(셀 +0) ────────────────────────────────────────
    hdr = header(
        num=1,
        title="선행연구: 논문들은 표적 신호를 어디서 얻었나",
        did="아카이브 문서 21건의 전문을 판정해 각 편이 표적 서명을 어디서 조달했고 그 조달처가 "
            "무슨 주장을 사 주었는지 카탈로그로 만들었다.",
        results=[
            f"문서 {C.num('corpus.documents', 21, '{:.0f}')}건(저작 "
            f"{C.num('corpus.distinct_works', 19, '{:.0f}')}편)을 전문 판정했다 — 게재 "
            f"{P.num('counts.published', 11, '{:.0f}')}편 · 프리프린트 "
            f"{P.num('counts.preprint', 10, '{:.0f}')}편, 축자 인용 "
            f"{P.num('counts.quotes_verified', 46, '{:.0f}')}건은 PDF 안 그 쪽에서 기계가 찾는다.",
            f"조달처는 일곱 갈래이고, 갈래가 그 편이 살 수 있는 주장의 크기를 정한다 — 측정은 절대 σ "
            f"를, 스톡 엔진은 운동학 서명을, 엔진 안 산란 구현은 메쉬에서 낸 RCS 의 **각도 구조**를 "
            f"산다(§3). 절대 크기는 모양을 안 닮은 구도 부피를 맞게 골라 넣으면 같은 자리에 "
            f"오므로 측정이 앵커한다(02 §4.6 — 그 부피를 무엇으로 잡는가는 결과를 보고 고를 수 "
            f"있는 값이고, 메쉬 부피로 잡은 구는 두 잣대 모두에서 우리보다 나쁘다).",
            f"H8 후보 {C.num('h8.n_adjudicated', 12, '{:.0f}')}편을 네 관문으로 판정해 동시 통과는 "
            f"{C.num('h8.n_passing_all_prongs', 0, '{:.0f}')}편이고, 가장 가까운 Rzewuski 는 엔진 "
            f"관문 하나에서 걸린다(§4.1).",
            f"절대 σ 를 dBsm 으로 찍는 편은 {P.num('counts.prints_dbsm', 6, '{:.0f}')}편이고 그중 "
            f"광선엔진을 돌리는 것은 {P.num('counts.prints_dbsm_and_runs_engine', 1, '{:.0f}')}편, "
            f"그 표적은 차량이다(Ziganshin 학회판 Fig.6).",
            f"우리는 광선엔진으로 가림을 풀고 조명면에 부품별 재질 PO(물리광학 — 빛이 닿는 면에 "
            f"흐르는 전류를 근사식으로 적어 넣고 그 면을 훑어 더하는 방법)를 적분하며, "
            f"밴드 기울기를 Das 의 "
            f"적합계수 {P.num('anchors.das.mu_a_db_per_ghz', 0.21, '{:.2f}', 'dB/GHz')} 에 "
            f"맞춘다(§4.2).",
        ],
        method=[
            ("범위", f"아카이브 2곳 + 패시브레이더 코퍼스에서 "
                     f"{P.num('meta.corpus_swept_pdfs', 178, '{:.0f}')}편을 낱말 대조하고, "
                     f"{C.num('corpus.documents', 21, '{:.0f}')}건을 전문 판정했다"),
            ("귀속", f"판정마다 축자 인용을 PDF 그 쪽에서 기계가 찾는다 — 못 찾으면 빌드가 죽는다 "
                     f"(`prior_work/src/build_prior_survey.py:85`)"),
            ("검증 규약", f"남의 논문 주장은 원문 축자로 판정한다 — 덱 "
                         f"{TC.num('n_claims', 197, '{:.0f}')}건 중 범위 안 "
                         f"{TV.num('counts.n_claims_in_scope', 165, '{:.0f}')}건을 대조해 "
                         f"{TV.num('counts.wrong', 18, '{:.0f}')}건이 틀렸고, 부재주장은 "
                         f"{TV.num('counts.absence_claims_in_scope', 41, '{:.0f}')}건 중 "
                         f"{TV.num('counts.absence_claims_wrong', 12, '{:.0f}')}건이다. 그래서 이 편의 "
                         f"부재 진술은 모집단을 문장 안에 적는다 "
                         f"(`docs/TEAMMEETING_PRIORWORK_AUDIT.md` §5)"),
            ("게재상태", "PDF 메타데이터 `subject`(IEEE 조판이 박는 \"게재처;연도;권;호;DOI\") · "
                        "지면 스탬프 · arXiv 스탬프로 문서마다 확정했다. 본문에 지면 채택을 적은 "
                        "arXiv 원고는 `일부` 로 세고 프리프린트로 남긴다"),
            ("관문 집계", "H8 은 후보별 4관문 판정으로 따로 센다 "
                         "(`src/report01_paper_facts.py:scorecard`) — G1~G4 깔때기와 모집단이 다르다"),
            ("엔진", f"Sionna RT 1차 사료 2편을 열어 §1 을 뽑았고, 설치본 Sionna "
                     f"{P.num('sionna_api.version')} 의 `sionna.rt` 공개 이름을 직접 세었다"),
        ],
        repro=dict(
            cmd=["# ① 근거 — PDF 원문 대조",
                 "~/.venvs/py312/bin/python prior_work/src/build_prior_survey.py",
                 "# ② 논문 파생 원장 (4관문 집계 · 인용 21건)",
                 "PYTHONPATH=src ~/.venvs/py312/bin/python src/report01_paper_facts.py",
                 "# ③ 그림 4장 (벡터 PDF + 400 dpi PNG)",
                 "PYTHONPATH=src ~/.venvs/py312/bin/python src/figs_report01.py",
                 "# ④ 이 리포트",
                 "PYTHONPATH=src ~/.venvs/py312/bin/python src/make_report01_prior.py"],
            out=[SURVEY, PAPER],
            runtime=f"근거 {P.num('meta.runtime_s', fmt='{:.0f}', unit='s')} · "
                    f"나머지 각 수 초 · CPU 만 쓴다",
            note="아카이브는 /data/public/sionna_jeong/papers_isac_sionna 와 "
                 "sionna_papers_by_task, 패시브 코퍼스는 /data/public/jeong/papers 다",
        ),
    )
    B.append(attach(hdr, paper_map(
        ["I. Introduction", "II. Related Work"],
        claim="드론 표면메쉬의 산란 진폭을 Sionna 급 광선엔진 안에서 계산해 검증한 게재 논문은 0편이고, "
              "우리 기여는 그 엔진과 파이프라인 통합, 그리고 그 위에 세운 교정된 파형 비교다.",
        evidence=["그림 2", "그림 4", "표 §4.1",
                  "outputs/report01_paper.json:h8.n_passing_all_prongs",
                  "outputs/report01_paper.json:route_status",
                  "outputs/prior_work_survey.json:counts.quotes_verified"],
        qualifications=[
            "Q1 — Rzewuski 등(NATO STO 2021)이 FDTD 로 드론 바이스태틱 σ 를 이미 냈다. "
            "우열은 엔진과 파이프라인 통합에 있다",
            "Q2 — '게재' 가 이 주장을 떠받친다. 프리프린트를 넣으면 LAMBDA 와 Ziganshin 저널판이 "
            "간극을 이음매로 좁힌다",
        ],
        report="report01_prior")))

    # ── §1 ─────────────────────────────────────────────────────────────────
    B.append(md(
        "## §1. 표적 서명이 쓰는 양, Sionna RT 가 계산하는 양", "",
        f"Sionna RT 기술보고서 {P.num('engine.technical_report.version')} 를 열어 스톡 솔버가 "
        f"무엇을 계산하는지 1차 사료로 확인했다. 경로는 SBR 로 후보를 만들고 이미지법으로 확정하며, "
        f"면과의 상호작용은 네 가지다(p.9).", "",
        table(["스톡 솔버가 계산하는 것", "표적 서명이 쓰는 것"],
              [["정반사 — 프레넬 계수 곱 (식 127–130, p.46)", "조명면 위의 위상 코히런트 면적분"],
               ["확산반사 — 산란계수 S 와 정규화 산란패턴 (p.50–52)", "자세에 따른 진폭 σ(θ, φ)"],
               ["굴절 · 1차 회절 (p.16)", "에지·정점 회절 항"],
               ["경로 지연 τ · 도플러 · 가림 기하", "그 기하를 σ 로 환산하는 단계"]])))

    B.append(md(
        f"59쪽 전문에서 `physical optics` "
        f"{P.num('engine.technical_report.term_counts.physical_optics', 0, '{:.0f}')}회, "
        f"`radar cross section`/`RCS` "
        f"{P.num('engine.technical_report.term_counts.radar_cross_section', 0, '{:.0f}')}회, "
        f"`dBsm` {P.num('engine.technical_report.term_counts.dbsm', 0, '{:.0f}')}회다. "
        f"`SBR` 은 {P.num('engine.technical_report.term_counts.sbr', 44, '{:.0f}')}회 나온다 — "
        f"광선을 쏘고 튕기는 층은 있고, **면적분과 RCS 출력이 그 위에 얹히는 층**이다.", "",
        f"설치본을 직접 열어 세면 Sionna {P.num('sionna_api.version')} 의 `sionna.rt` 공개 이름 "
        f"{P.num('sionna_api.rt_public_names', 161, '{:.0f}')}개 중 산란단면적을 계산하는 것은 "
        f"{P.num('sionna_api.rcs_api_names', 0, '{:.0f}')}개이고, `ScatteringPattern` 계열 "
        f"{P.num('sionna_api.scattering_api_names', 5, '{:.0f}')}개는 확산반사의 각분포 함수다.", "",
        f"5G 3.5 GHz 에서 λ 는 "
        f"{P.num('bands.lambda_cm.5G 3.5 GHz', fmt='{:.1f}', unit='cm')} 이고 대각 "
        f"{P.num('bands.drone_diag_m', 0.40, '{:.2f}', 'm')} 급 드론은 파장의 다섯 배 규모 유한 "
        f"물체다. 그 크기의 σ 는 조명면 전체의 위상 코히런트 면적분에서 나오므로, 서명이 필요한 편들은 "
        f"그것을 어디선가 조달했다. 무엇을 조달했는지가 §3 이다."))

    # ── §2 ─────────────────────────────────────────────────────────────────
    B.append(md(
        "## §2. 센서스 — 누가, 어느 엔진에서, 무슨 표적을", "",
        f"{C.num('corpus.documents', 21, '{:.0f}')}건을 전문 추출해 관문 4개에 통과시켰다. "
        f"census 16편에 1차 사료 정산이 {P.num('counts.added_since_census', 5, '{:.0f}')}편을 더했다 "
        f"— 그중 Rzewuski 는 최종물이 우리와 가장 가깝고(§4.1) 아카이브 밖에 있었다.", "",
        f"문서 {C.num('corpus.documents', 21, '{:.0f}')}건은 저작 "
        f"{C.num('corpus.distinct_works', 19, '{:.0f}')}편이다 — Costa 와 Ziganshin 은 회의판·저널판을 "
        f"따로 세고, 그 이유는 §2.5 에 있다.", "",
        table(["관문", "통과 조건"],
              [["G1", "이 논문이 Sionna 계열 광선엔진을 직접 돌린다"],
               ["G2", "그 엔진 안의 표적이 드론 기하(메쉬)다 — 큐브·점산란체와 구분한다"],
               ["G3", "그 메쉬에서 산란 **진폭**을 계산한다"],
               ["G4", "결과를 절대 RCS(dBsm)로 보고한다"]])))

    B.append(figure_md(FIGS["funnel"], 1, "관문을 하나씩 걸면 몇 건이 남는가?",
                       report="report01_prior"))

    B.append(md(
        "### §2.1. 게재본 — 표적 서명을 광선엔진 밖에서 얻은 쪽", "",
        table_from((SURVEY, "papers"), CENSUS_COLS, order=PUB_OUTSIDE)))

    B.append(md(
        "### §2.2. 게재본 — 광선엔진을 직접 돌리는 쪽", "",
        table_from((SURVEY, "papers"), CENSUS_COLS, order=PUB_ENGINE)))

    B.append(md(
        "### §2.3. 프리프린트 (1/2) — 게재본과 구분해 인용한다", "",
        table_from((SURVEY, "papers"), CENSUS_COLS, order=PRE_A)))

    B.append(md(
        "### §2.4. 프리프린트 (2/2)", "",
        table_from((SURVEY, "papers"), CENSUS_COLS, order=PRE_B)))

    B.append(md(
        "### §2.5. Ziganshin — 두 판을 구별해 인용한다", "",
        "어느 판을 인용하는지가 사실을 가른다. 판마다 게재상태와 보고량이 다르다.", "",
        table(["판", "게재상태", "보고한 양", "표적"],
              [["학회판 (EuCAP 2025, DOI 10.23919/EuCAP63536.2025.10999367)", "게재",
                "패싯 차량 RCS 를 dBsm 으로 (Fig.6)", "단순화 차량(PEC)"],
               ["저널판 (`arXiv:2604.05991v2`)", "IEEE OJAP 투고 프리프린트",
                "근거리 산란전계 |E| 와 패싯 이산화 품질", "구·원기둥·PEC 차량"]]), "",
        "드론을 향후 과제로 그 단어 그대로 적는 문장은 **학회판 p.5 결론**에 있다: "
        "*\"can also be applied to compute scattering from other objects, such as drones, "
        "humans, and micro-Doppler effects\"*.",
        "우리가 서 있는 자리는 그 문장 바로 뒤이고, 그 문장은 동료심사를 통과한 문장이다."))

    # ── §3 ─────────────────────────────────────────────────────────────────
    B.append(md(
        "## §3. ⭐ 조달 카탈로그 — 표적 서명을 어디서 가져왔고, 그것이 무슨 주장을 사 주었나", "",
        "편마다 표적 서명의 조달처를 골랐고, 고른 조달처가 그 편이 낼 수 있는 주장의 크기를 정한다. "
        "갈래는 7개이고, 갈래마다 게재본 수를 함께 센다.", "",
        table_from((PAPER, "route_status"), ROUTE_COLS, key_col="갈래")))

    B.append(md(
        figure_md(FIGS["routes"], 2, "각 갈래에 몇 건이 서 있는가?", report="report01_prior"), "",
        "md-rt 는 Sionna RT 의 회전 마이크로도플러 정확도 검증을 스스로 주장하고, 대조 기준은 자기 "
        "폐형식 운동학 식이다 — 그래서 P4(진폭 검증)에서 걸리고 전문의 dBsm 도 0회다.", "",
        "LAMBDA 는 반대쪽 끝의 표본이다. UAV 메쉬는 Sionna RT 에 넣되 σ 는 CADFEKO 에서 풀어 "
        "자세별로 조회한다(p.3 · p.7) — 엔진을 건드리지 않고 진폭을 얻는 주입 구조다."))

    for i, order in enumerate(CAT, start=1):
        B.append(md(f"### §3.{i}. 카탈로그 ({i}/3) — 논문 II 절 표의 원형", "",
                    table_from((SURVEY, "papers"), CAT_COLS, order=order)))

    B.append(md(
        figure_md(FIGS["dbsm"], 3, "절대 σ 를 dBsm 으로 찍는 편은 어디인가?",
                  report="report01_prior"), "",
        f"전문에 `dBsm` 이 한 번이라도 나오는 논문이 "
        f"{P.num('counts.prints_dbsm', 6, '{:.0f}')}편, 그중 광선엔진을 돌리는 것은 "
        f"{P.num('counts.prints_dbsm_and_runs_engine', 1, '{:.0f}')}편이고 그 표적은 차량이다. "
        f"나머지는 무향실 측정 · FDTD · Sionna 밖 자체 솔버가 낸 값이다.", "",
        f"CFAR 도 false alarm 도 전문에 0회인 논문이 "
        f"{P.num('counts.zero_cfar_and_false_alarm', 14, '{:.0f}')}편이다. 오경보 바닥을 명목값에 "
        f"고정하는 것은 잡음·클러터 분포를 통제하는 시뮬이 하는 일이고, 그 자리가 04편이다."))

    # ── §3.4 ⭐ 엔진 밖 조달의 두 갈래(주입 · 통계추출)를 아카이브 전수로 다시 셌다 ──
    #    §3 카탈로그는 전문 판정 21건 안에서 세고, 이 절은 아카이브 전수 재판독이다 —
    #    모집단이 다르므로 두 정의를 한 문장에 섞지 않는다.
    B.append(md(
        "### §3.4. ⭐ 엔진 밖에서 조달한 게재본 — 주입은 게재돼 있고, 값은 검증이 치른다", "",
        f"주입(엔진 밖에서 만든 σ 표를 자세로 조회해 시뮬 경로에 곱하는 구조)을 아카이브 고유문서 "
        f"{IR.num('method.unique_documents_after_text_hash_dedup', 327, '{:.0f}')}편(텍스트 해시 "
        f"중복 제거 후) 위에서 다시 셌다. 정의를 둘로 갈라 적는다 — 좁은 정의는 `외부 상용 솔버 → "
        f"광선추적 경로계수`, 넓은 정의는 `외부 서명표 → 시뮬 경로·링크` 다. 아래 계수의 모집단은 "
        f"이 아카이브이고, §3 표(전문 판정 21건)와 다르다.", "",
        table(["갈래 · 정의", "이 조사가 센 것", "게재", "인쇄된 검증 · 파라미터"],
              [["좁은 정의 — 외부 상용 솔버 → 광선추적 경로계수",
                f"{IV.num('headline_answer.the_single_paper_that_does_that')}",
                f"{IV.num('headline_answer.of_the_peer_reviewed_set_how_many_computed_the_table_in_a_commercial_full_wave_solver_and_multiplied_it_onto_ray_traced_paths', 0, '{:.0f}')}편",
                f"실측 · 독립솔버 · 해석해 대조 판정 "
                f"{IH.num('answer.strict_verdict')}"],
               ["넓은 정의 — 외부 서명표 → 시뮬 경로·링크",
                f"{IV.num('counts.injection_instances_in_the_master_table', 16, '{:.0f}')}건",
                f"{IV.num('counts.peer_reviewed', 10, '{:.0f}')}편 (프리프린트 "
                f"{IV.num('counts.preprint_only', 6, '{:.0f}')}편)",
                f"{IH.num('answer.broad_verdict')} — 금속구 · held-out 밴드 · 하드웨어 대조"],
               ["재판독 감사 — 인구조사를 PDF 로 다시 열어 판정",
                f"인구조사 {IA.num('corrected_tally.census_claimed.instances', 10, '{:.0f}')}건 재판독",
                f"{IA.num('corrected_tally.peer_reviewed_confirmed_injections', 3, '{:.0f}')}편 "
                f"(인구조사 주장 "
                f"{IA.num('corrected_tally.census_claimed.peer_reviewed', 5, '{:.0f}')}편)",
                "확정 주입 · 예산수준 · 주입 아님 셋으로 갈린다"],
               ["통계 추출 — 표적 진폭을 식 (108) CN(0, σ²) 에서 뽑는다",
                "클러터 서베이 41쪽 전문 계수",
                "Proc. IEEE 114(1)",
                f"`physical optics` "
                f"{CL.num('attack_5_clutter_survey.what_is_genuinely_unreported.fulltext_counts_41p.physical_optics', 0, '{:.0f}')} · "
                f"`dBsm` "
                f"{CL.num('attack_5_clutter_survey.what_is_genuinely_unreported.fulltext_counts_41p.dBsm', 0, '{:.0f}')} · "
                f"`max_depth` "
                f"{CL.num('attack_5_clutter_survey.what_is_genuinely_unreported.fulltext_counts_41p.max_depth', 0, '{:.0f}')} · "
                f"`mesh` "
                f"{CL.num('attack_5_clutter_survey.what_is_genuinely_unreported.fulltext_counts_41p.mesh', 2, '{:.0f}')} · "
                f"`Blender` "
                f"{CL.num('attack_5_clutter_survey.what_is_genuinely_unreported.fulltext_counts_41p.Blender', 1, '{:.0f}')}"]]), "",
        "⭐ **게재된 주입 사례가 인쇄한 것은 아키텍처가 아니라 검증이다** — 0.5 m 금속구와 28 GHz "
        "held-out 밴드(Zhang, IEEE JSAC), 77 GHz 자동차 레이다 end-to-end(Deep, IET RSN), 정규화 "
        "서명 상관(Costa, IEEE J-STEAP). 입장료가 거기 있으므로 우리도 §4.2 와 06편에서 같은 값을 치른다.", "",
        "클러터 서베이가 표적 축을 비운 것은 그 편의 설계다 — 표적 진폭은 통계 추출이고 광선추적은 "
        "건물 클러터에 쓴다. 그 빈 칸이 우리 자리이고, 메쉬 해상도·광선예산·기종을 인쇄하는 것이 "
        "이 편의 재현성 규약이다."))

    # ── §4 ─────────────────────────────────────────────────────────────────
    B.append(md(
        "## §4. 우리가 선 자리", "",
        f"실측 전이까지 보는 축으로 좁히면 모집단이 달라진다 — sim-to-real 정찰의 센서스가 그 범위를 "
        f"문장 안에 적는다: {SR.num('combo_verdict.statement')} (세 요소 = 사이트트윈 · 계산 σ · "
        f"분류, 거기에 실측 전이 보고까지. 최근접은 LAMBDA 다).", "",
        "### §4.1. H8 판정 — 네 관문을 그대로 나른다", "",
        f"**H8**: 드론 메쉬에서 계산한 산란 서명을 Sionna 계열 엔진 안에서 검증한 **게재** 논문은 "
        f"{C.num('h8.n_passing_all_prongs', 0, '{:.0f}')}편이다. 네 관문으로 쪼개 후보마다 따로 "
        f"판정했고, P1 은 **집계가 적용한 규칙 그대로** 적는다.", "",
        table_from((PAPER, "h8.prongs"),
                   [("관문", "prong"), ("통과 조건", "test_ko")])))

    B.append(md(
        figure_md(FIGS["prongs"], 4, "후보마다 어느 관문에서 걸리는가?", report="report01_prior"), "",
        f"후보 {C.num('h8.n_adjudicated', 12, '{:.0f}')}편을 관문별로 판정했고, 넷을 동시에 통과한 "
        f"편은 {C.num('h8.n_passing_all_prongs', 0, '{:.0f}')}편이다. 가장 가까운 셋은 각각 다른 "
        f"관문에서 걸린다.", "",
        table_from((SURVEY, "h8.near_miss"),
                   [("가장 가까운 편", "paper"), ("남은 간격", "gap_ko")], order=[0, 1, 2])))

    B.append(md(
        "### §4.1.1. ⭐ 신규성 문단 — 논문 II 절에 그대로 붙인다", "",
        f"후보 {C.num('h8.n_adjudicated', 12, '{:.0f}')}편 중 네 관문 동시 통과가 "
        f"{C.num('h8.n_passing_all_prongs', 0, '{:.0f}')}편이라는 사실을, 아래 문단이 두 단서와 "
        f"함께 나른다. 참조번호는 이 편 끝 인용 목록의 번호다.", "",
        *NOVELTY, "",
        "**Q1 근거** — Rzewuski 는 Parrot AR.Drone 2.0 의 모노·바이스태틱 RCS 를 FDTD(QuickWave-3D)로 "
        "풀어 WiFi 대역 −40~0 dBsm 을 보고하고(p.5), 패시브 커버리지 예산을 세워 바이스태틱 50 m "
        "실측 검출까지 닫았다(p.9) ⟨outputs/report01_paper.json : h8.q1_counter_paper⟩.", "",
        "**Q2 근거** — Ziganshin 저널판은 검증을 저자 스스로 정성적이라 적는다(p.7) "
        "⟨outputs/prior_settled_h8.json : h8_candidates⟩.", "",
        f"**주입 근거** — 주입 아키텍처 자체는 이미 게재돼 있다(§3.4). 재판독으로 확정된 게재 주입 "
        f"{IA.num('corrected_tally.peer_reviewed_confirmed_injections', 3, '{:.0f}')}편은 전부 자기 "
        f"서명을 실측 또는 기준체와 맞대고 수치를 인쇄했고, 검증량은 σ 자체(Zhang: 금속구 + held-out "
        f"밴드)에서 서명 형태(Costa: 정규화 서명 상관)까지 갈린다.", "",
        "그래서 이 문단이 세는 것은 아키텍처가 아니라 네 관문이고, 검증 칸은 P4 다."))

    B.append(md(
        "### §4.2. 우리 파이프라인이 각 축에서 한 일", "",
        "우리는 Sionna 의 Mitsuba/OptiX 광선엔진으로 first-hit 가림을 풀고, 조명면 위에 부품별 "
        "재질 PO 를 적분한다. 레벨과 주파수 의존성은 측정 적합계수에서 받는다.", "",
        table(["축", "우리가 한 일", "값", "편"],
              [["자세 패턴", "광선엔진 first-hit 가림 + 조명면 PO 적분, 부품별 재질",
                f"해석 PO 구 대비 "
                f"{S.num('summary_div16.max_abs_db_vs_po', None, '{:.3f}', 'dB')}, "
                f"입사 {S.num('meta.n_incidence', None, '{:.0f}')}방향", "02"],
               ["절대 레벨 · 밴드 기울기",
                "A(f)·B1(φ)·B2 분해로 Das 적합계수에 정렬 (Zhang, IEEE JSAC 2026 의 3GPP 채택 분해)",
                f"{P.num('anchors.das.mu_a_db_per_ghz', 0.21, '{:.2f}', 'dB/GHz')}", "02"],
               ["바이스태틱", "수신기 방향 그림자 광선으로 출사쪽 가시성 판정", "β ≤ 45°", "02"],
               ["검출", "경험 Pfa 로 CFAR 문턱 교정",
                f"GPU 몬테카를로 {V.num('meta.runtime_s', fmt='{:.0f}', unit='s')}", "04"],
               ["파형 비교", "한 표적 · 한 검출기로 LTE · 5G · WiFi", "점유 · 대역폭 · PRF", "03 · 05"],
               ["조달", "σ 를 광선엔진 안에서 계산해 같은 엔진의 경로에 싣는다",
                f"게재 확정 주입 "
                f"{IA.num('corrected_tally.peer_reviewed_confirmed_injections', 3, '{:.0f}')}편은 σ 를 "
                f"낸 곳과 쓰는 곳이 다른 엔진이다", "01 §3.4"]])))

    B.append(md(
        "### §4.3. 앵커의 세 문헌, 그리고 규약이 갈리는 자리", "",
        "Das §III-1 은 평균을 **측정한 방위 구간의 선형평균**으로 정의하고(Phantom 3 는 반평면), "
        "Zhang 식 (15)는 전 각도의 선형평균이다. Yuan 은 정의를 적지 않으므로 같은 축으로 읽는 것은 "
        "우리 추론이다 ⟨outputs/prior_work_survey.json : anchors.yuan.statistic_ko⟩.", "",
        "Das 의 Phantom 3 자료는 Das 자신의 참고문헌 [7](Wang 외, China Communications)에서 왔고 "
        "⟨outputs/prior_work_survey.json : anchors.das.provenance_ko⟩, 우리가 쓰는 것은 그 기울기 "
        "하나다.", "",
        table(["문헌", "기체 · 대역", "기울기", "우리가 쓰는 자리"],
              [["Das (IEEE WCL 2026)",
                "Phantom 3 · " + P.num("anchors.das.band_ghz[0]", fmt="{:.1f}") + "–"
                + P.num("anchors.das.band_ghz[1]", fmt="{:.1f}", unit="GHz"),
                f"{P.num('anchors.das.mu_a_db_per_ghz', 0.21, '{:.2f}', 'dB/GHz')}", "기울기 앵커"],
               ["Yuan (EuCAP 2025)", "Phantom 3 · 같은 실험실 · VV",
                f"{P.num('anchors.yuan.slopes_db_per_ghz.theta90', 0.315, '{:.3f}', 'dB/GHz')}",
                "고도 3측면 대조"],
               ["Zhang (IEEE JSAC 2026)", "M350 · 10–36 GHz",
                f"{P.num('anchors.zhang.a_slope_db_per_ghz', 0.31, '{:.2f}', 'dB/GHz')}",
                "분해 σ=A(f)·B1(φ)·B2 형식"]]), "",
        f"레벨 규약은 출처 논문 안에서 갈린다 — §III-1 정의를 그대로 쓰면 인쇄값이고, 잔차 최소화 "
        f"변환을 쓰면 "
        f"{P.num('anchors.level_convention_split.pipeline_offset_db', 2.5068, '{:.2f}', 'dB')} 만큼 "
        f"밝다. 생산 경로는 기울기만 쓰며, 02편 §4 가 레벨 규약을 하나로 맞춘다."))

    # ── 논문 부속(방어선 · 방법 문단 · 인용) — 셀 하나 ─────────────────────
    B.append(paper_appendix(
        defence_block=defence(defence_rows(P, C, V), sec="§4.4", report="report01_prior"),
        methods_block=methods(METHOD_PARA,
                              tools=["PyMuPDF 1.28.0", "Sionna 2.0.1", "Python 3.12"],
                              report="report01_prior", sec="§4.5"),
        citations=citations(C), sec="§4.6"))

    # ── 다음 단계 ──────────────────────────────────────────────────────────
    B.append(next_steps([
        ("`src/sigma_anchor.py` 와 `outputs/rcs_anchor.json` 의 통계 규약을 하나로 맞춘다",
         f"앵커 레벨 {P.num('anchors.level_convention_split.pipeline_offset_db', 2.5068, '{:.2f}', 'dB')} "
         f"가 어느 쪽으로 확정된다",
         "02편 §4 · `src/sigma_anchor.py`"),
        ("Rzewuski 의 FDTD σ(WiFi 대역 −40~0 dBsm)를 우리 σ 격자와 같은 축에 올린다",
         "우리 WiFi 대역 σ 가 독립 full-wave 결과와 몇 dB 떨어져 있는지 확정된다",
         "02편 §4 앵커 원장"),
        ("Das 의 참고문헌 [7](Wang 외, China Communications)을 입수해 원 측정 조건을 대조한다",
         "기울기 앵커의 편파·자세 구간이 우리 격자와 같은 축인지 확정된다",
         "`src/report01_paper_facts.py:anchor_provenance`"),
        ("Xplore 본문 검색 권한으로 ICCT · EuRAD · RadarConf 프로시딩을 같은 관문에 통과시킨다",
         "유료 프로시딩까지 포함한 H8 의 관문 통과 편수가 확정된다",
         "`prior_work/src/build_prior_survey.py:PAPERS`"),
        ("Wypich & Zielinski(원문 미확보 · 표적은 차량 5.8 GHz)를 입수해 ECA→CFAR 선례를 재검증한다",
         "우리 하드웨어 선례가 인용 가능한지 확정된다",
         "`prior_work/outputs/prior_work.json`"),
        ("Costa(JSTEAP, 게재)의 해석 마이크로도플러 경로를 우리 기하 위에서 재현한다",
         "마이크로도플러를 어느 편의 근거로 올릴지 결정된다",
         "future work — `src/rcs_sbr.py` 위 별건"),
        ("sim-to-real 센서스를 실측 사이트 축으로 좁혀 다시 건다",
         "사이트트윈 + 계산 σ + 검출 조합의 최근친이 확정된다 — 지금 센서스는 분류 축에서 닫혀 있다",
         "`outputs/s2r_prior.json` → 01편 §4"),
        (f"덱 축자 감사가 낸 정정 "
         f"{TV.num('counts.wrong', 18, '{:.0f}')}건을 §2 · §3 카탈로그 행에 전파한다",
         "선행 서술이 원문 축자와 한 축에 선다 — LaSen 서사 · CISSIR 행 · LIPASE GT · OpenISAC "
         "붕괴 지점이 대상이다",
         "`docs/TEAMMEETING_PRIORWORK_AUDIT.md` §3 → `src/make_report01_prior.py`"),
    ], sec="§5."))

    return B


# =========================================================================== #
def main():
    print("── 리포트 01 빌드 ──")
    P = from_json(SURVEY)
    C = from_json(PAPER)
    S = from_json(KR)
    V = from_json(CFAR)
    for k, rel in FIGS.items():
        for ext in (".png", ".pdf"):
            p = os.path.join(_ROOT, os.path.splitext(rel)[0] + ext)
            if not os.path.exists(p):
                raise SystemExit(f"그림이 없다: {p}\n"
                                 f"  → PYTHONPATH=src python src/figs_report01.py 를 먼저 돌려라.")
    rep = build_notebook(NB_OUT, blocks(P, C, S, V), strict=True)
    print(f"✅ {os.path.relpath(NB_OUT, _ROOT)}")
    return rep


if __name__ == "__main__":
    main()
