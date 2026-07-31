# -*- coding: utf-8 -*-
"""
make_report01_prior.py — 리포트 01 「선행연구」 빌더  →  report01_prior.ipynb
============================================================================================
계약서: `docs/REBUILD_2026-07-30.md` (골격 §2 의 01편, 서술규약 §5).
규약 강제는 `src/report_style.py` — 숫자·캡션·서두·한계·분량이 전부 거기서 검사된다.

이 편이 답하는 질문 하나
    **드론 메쉬에서 산란을 계산해 게재된 전례가 있는가?**

근거는 전부 `outputs/prior_census.json` 한 개다. 그 JSON 을 만드는 것은
`benchmark/prior_census.py` 이고, 거기서 **PDF 원문 대조**가 끝난다:
  · 논문마다 축자 인용을 PDF 안에서 찾지 못하면 그 자리에서 죽는다(귀속 위조 방지)
  · 게재/프리프린트는 PDF 메타데이터 `subject` 또는 본문 문자열로 확정한다
  · "한 번도 안 쓴다" 류 **부정 주장**은 낱말 빈도로 대조한다(`EXPECT`)
  · 설치된 Sionna 를 직접 열어 RCS API 유무를 센다(§1 의 근거)

이 파일이 하는 일
    JSON 을 읽어 노트북을 조립하는 것뿐이다. 그림 4장은 이미 census 스크립트가 그렸다.
    **계산도 그림도 여기서 새로 하지 않는다** — 근거와 서술을 한 파일에 섞지 않기 위해서다.

실행
    cd /home/yunjung/workspace/sionna2
    PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/prior_census.py   # 근거
    PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python src/make_report01_prior.py  # 리포트

⚠ GPU 도 Sionna 실행도 필요 없다(census 쪽이 sionna.rt 를 임포트만 한다). 수 초.
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (_HERE, os.path.join(_ROOT, "benchmark")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from report_style import (build_notebook, caption, from_json,          # noqa: E402
                          header, limits, md, table, table_from)

CENSUS = "outputs/prior_census.json"
NB_OUT = os.path.join(_ROOT, "report01_prior.ipynb")

#: census JSON 의 `papers` 배열은 순서가 고정돼 있다(게재 0~9 · 프리프린트 10~15).
#: 표를 쪼갤 때 이 인덱스를 쓴다 — 이름이 아니라 순서로 뽑아야 표 하나에 출처 하나가 된다.
PUB_MEAS = [0, 1, 2, 3, 4, 5]      # 측정 · 피팅 · 해석 · 상수가정 (Sionna 미사용)
PUB_RT = [6, 7, 8, 9]              # Sionna 를 직접 돌린 게재 4편
PRE = [10, 11, 12, 13, 14, 15]     # 프리프린트 6편
CAT_A = [0, 1, 2, 3, 4, 5, 6, 7]   # 회피 카탈로그 상단
CAT_B = [8, 9, 10, 11, 12, 13, 14, 15]

PAPER_COLS = [("논문", "short"), ("게재", "venue_status"), ("Sionna", "sionna_role_ko"),
              ("표적", "target_ko"), ("전략", "strategy_label_ko")]
CAT_COLS = [("논문", "short"), ("전략", "strategy_label_ko"),
            ("주장한 것", "claimed_ko"), ("주장하지 않은 것", "not_claimed_ko")]


def blocks(C):
    B = []

    # ── 서두 6블록 ─────────────────────────────────────────────────────────
    B.append(header(
        num=1,
        title="선행연구 — 메쉬 표적으로 산란을 계산한 전례가 있는가",
        question="드론 메쉬에서 산란을 계산해 게재된 전례가 있는가?",
        conclusion_lines=[
            f"아카이브 PDF {C.num('meta.pdf_in_scope', 41, '{:.0f}')}편 중 전문을 판정한 "
            f"{C.num('meta.n_papers', 16, '{:.0f}')}편이 이 census 다 — 게재 "
            f"{C.num('counts.published', 10, '{:.0f}')}편 · 프리프린트 "
            f"{C.num('counts.preprint', 6, '{:.0f}')}편, 논문마다 PDF 로 확정했다.",
            f"Sionna 계열 엔진을 직접 돌린 것이 "
            f"{C.num('funnel.all.g1_sionna', 7, '{:.0f}')}편, 그중 표적이 드론인 것이 "
            f"{C.num('funnel.all.g2_uav', 3, '{:.0f}')}편, **그 드론 메쉬에서 산란을 계산한 것은 "
            f"{C.num('funnel.all.g3_mesh_scattering', 0, '{:.0f}')}편**이다.",
            "가장 가까운 게재 전례(Ziganshin, EuCAP 2025)는 Sionna-RT 위에 산란을 얹어 "
            "**차량** RCS 를 내고, 드론을 향후 과제로 그 단어 그대로 적는다.",
            f"검출 쪽도 비어 있다 — CFAR 도 false alarm 도 전문에 0회인 논문이 "
            f"{C.num('counts.zero_cfar_and_falsealarm', 13, '{:.0f}')}편이다.",
        ],
        claims=[
            "16편의 **게재/프리프린트 구분** — PDF 메타데이터 또는 본문 문자열로 확정",
            "각 논문이 표적 서명을 **무엇으로 대신했는가**(회피 전략)와 그 대가",
            "이 census 범위에서 **드론 메쉬 산란을 Sionna 계열 엔진에서 계산한 게재 전례 0편**",
            "낱말 빈도로 확인되는 **부정 사실** — dBsm · CFAR · false alarm 이 몇 번 나오는가",
        ],
        non_claims=[
            "**'세계 최초'** — census 는 16편이고, 비영어 DB 와 유료 프로시딩 다수가 탐색 밖이다",
            "우리 방법이 **더 정확하다**는 것 — 이 편은 문헌 지도이지 성능 비교가 아니다",
            "선행 수치와 우리 수치의 **사과-대-사과 대조** — 02편(σ)·05편(검출)의 몫이다",
            "읽지 않은 논문에 대한 판정 — census 밖 편은 이 편의 근거로 지지되지 않는다",
        ],
        prereq=[],
        repro=dict(
            cmd=["# ① 근거 — PDF 원문 대조 + 그림 4장",
                 "PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/prior_census.py",
                 "# ② 이 리포트",
                 "PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python src/make_report01_prior.py"],
            out=CENSUS,
            runtime=f"census {C.num('meta.runtime_s', fmt='{:.0f}', unit='s')} "
                    f"(GPU 불필요) · 리포트 빌드 수 초",
            note="아카이브 PDF 는 /data/public/sionna_jeong/papers_isac_sionna 에 있다",
        ),
    ))

    # ── §1 ─────────────────────────────────────────────────────────────────
    B.append(md(
        "## §1. 이 질문이 왜 걸려 있나 — Sionna RT 는 전파 도구다", "",
        "Sionna 의 `PathSolver` 는 **송신기에서 수신기로 가는 경로**를 푼다. "
        "각 면을 국소 무한 평면으로 보고 프레넬 계수를 곱한다(기하광학).", "",
        f"벽에는 맞는 가정이다. λ 가 "
        f"{C.num('context.lambda_cm.5G 3.5 GHz', fmt='{:.1f}', unit='cm')} 인 5G 밴드에서 "
        f"대각 수십 cm 짜리 드론에는 틀린다.", "",
        table(["RT 가 주는 것", "표적 서명에 필요한 것"],
              [["경로 지연 τ · 도플러", "표적 크기·자세에 따른 진폭 σ"],
               ["면별 프레넬 계수 |Γ|", "조명된 면 위의 **위상 코히런트 면적분**"],
               ["확산산란 계수 S(우리가 고르는 노브)", "회절(에지·정점) 항"],
               ["가림·다중반사 기하", "그 기하를 σ 로 환산하는 단계"]])))

    B.append(md(
        f"설치본을 직접 열어 세면: Sionna "
        f"{C.num('sionna_api.version')} 의 `sionna.rt` 공개 이름 "
        f"{C.num('sionna_api.rt_public_names', 161, '{:.0f}')}개 중 RCS·산란단면적을 계산하는 것은 "
        f"{C.num('sionna_api.rcs_api_names', 0, '{:.0f}')}개다.",
        f"`ScatteringPattern` 계열 "
        f"{C.num('sionna_api.scattering_api_names', 5, '{:.0f}')}개는 확산반사의 **각분포 함수**이지 "
        f"σ 가 아니다.", "",
        "⚠ 주장 범위를 좁게 잡는다. **\"광선추적이 RCS 를 못 낸다\" 는 거짓**이다 — SBR 계열 "
        "솔버는 낸다.", "",
        "참인 문장은 **\"Sionna 기본 경로 solver 에 표면적분 단계가 없다\"** 뿐이다. "
        "광선을 더 쏘아도 σ 가 나오지 않는다는 **실측 시연**은 02편 §2 에 있다.", "",
        "그래서 표적 서명이 필요한 논문은 전부 그것을 **다른 데서** 가져와야 했다. "
        "무엇을 가져왔는지가 이 편의 §3 이다."))

    # ── §2 ─────────────────────────────────────────────────────────────────
    B.append(md(
        "## §2. 센서스 — 무엇을, 어떻게 세었나", "",
        f"아카이브 PDF {C.num('meta.pdf_in_scope', 41, '{:.0f}')}편 중 "
        f"{C.num('meta.n_papers', 16, '{:.0f}')}편을 전문 추출해 판정했다. "
        f"축자 인용 {C.num('meta.n_quotes', fmt='{:.0f}')}건이 PDF 안에 실제로 있는지 "
        f"기계가 확인하고, 없으면 빌드가 죽는다(`benchmark/prior_census.py:450`).", "",
        "게재상태는 논문마다 PDF 메타데이터 `subject`(IEEE 조판이 박는 "
        "\"게재처;연도;권;호;DOI\") 또는 본문 문자열로 확정했다. 근거가 없으면 census 에 넣지 않는다.",
        "", table(["관문", "통과 조건"],
                  [["G1", "Sionna 계열 오픈 RT 엔진을 이 논문이 직접 돌린다"],
                   ["G2", "표적이 드론이다 — 차량·구·인체가 아니다"],
                   ["G3", "그 표적의 산란을 **메쉬에서** 계산한다"],
                   ["G4", "결과를 절대 RCS(dBsm)로 보고한다"]])))

    B.append(md(
        f"![gate funnel]({C.get('figures.funnel')})", "",
        caption(1, "관문을 하나씩 걸면 몇 편이 남는가?")))

    B.append(md(
        "### §2.1. 게재본 — Sionna 를 쓰지 않는 쪽", "",
        table_from((CENSUS, "papers"), PAPER_COLS, order=PUB_MEAS)))

    B.append(md(
        "### §2.2. 게재본 — Sionna 를 직접 돌리는 쪽", "",
        table_from((CENSUS, "papers"), PAPER_COLS, order=PUB_RT)))

    B.append(md(
        "### §2.3. 프리프린트 — 게재본과 섞어 인용하지 않는다", "",
        table_from((CENSUS, "papers"), PAPER_COLS, order=PRE)))

    B.append(md(
        "### §2.4. ⭐ Ziganshin 은 두 판이 다르다", "",
        "이 편에서 가장 미끄러운 자리다. **어느 판인지 밝히지 않으면 두 문장이 다 틀린다.**", "",
        table(["판", "게재상태", "RCS(dBsm)", "표적"],
              [["회의판 (EuCAP 2025)", "게재", "낸다 — Fig.6 `RCS (dBsm)`", "단순화 차량(PEC)"],
               ["저널판 (`arXiv:2604.05991`)", "프리프린트", "전문에 0회", "구·원기둥·차량"]]), "",
        "회의판이 드론을 향후 과제로 **그 단어 그대로** 적는다: "
        "*\"can also be applied to compute scattering from other objects, such as drones, "
        "humans, and micro-Doppler effects\"*.",
        "우리가 서 있는 자리는 그 문장 바로 뒤다."))

    # ── §3 ─────────────────────────────────────────────────────────────────
    B.append(md(
        "## §3. ⭐ 회피 카탈로그 — 무엇을 대신 썼고, 무엇을 포기했나", "",
        "표적 서명이 필요했는데 메쉬에서 계산하지 않은 논문들이 무엇을 대신 썼는가. "
        "전략은 열 갈래로 갈라지지만, 잃는 것은 셋뿐이다.", "",
        table(["잃는 것", "누가 잃나", "왜"],
              [["절대 눈금(dBsm)", "해석 모델 · stock 방치 · 확산계수",
                "무차원 반사도나 임의 상수로 끝난다"],
               ["자세 구조", "상수 가정 · 외부 주입 · 점표적",
                "기하가 없으니 각도 의존이 나올 데가 없다"],
               ["다른 기체로의 이식", "측정 · 피팅",
                "그 기체 그 대역의 계수표일 뿐이다"]])))

    B.append(md(
        f"![avoidance matrix]({C.get('figures.matrix')})", "",
        caption(2, "각 전략은 어느 주장 칸을 비워 두는가?")))

    B.append(md(
        "### §3.1. 카탈로그 (1/2)", "",
        table_from((CENSUS, "papers"), CAT_COLS, order=CAT_A)))

    B.append(md(
        "### §3.2. 카탈로그 (2/2)", "",
        table_from((CENSUS, "papers"), CAT_COLS, order=CAT_B)))

    B.append(md(
        f"![dbsm counts]({C.get('figures.dbsm')})", "",
        caption(3, "Sionna 를 돌리면서 절대 σ 를 찍은 논문이 있는가?"), "",
        f"전문에 `dBsm` 이 한 번이라도 나오는 논문이 "
        f"{C.num('counts.reports_dbsm', 5, '{:.0f}')}편, 그중 Sionna 를 돌리는 것은 "
        f"{C.num('counts.reports_dbsm_and_runs_sionna', 1, '{:.0f}')}편이고 그 표적은 차량이다.",
        "나머지는 전부 무향실 측정이거나 Sionna 밖 자체 솔버다."))

    B.append(md(
        f"![detection vocabulary]({C.get('figures.detect')})", "",
        caption(4, "오경보율을 통제하는 논문이 있는가?"), "",
        f"CFAR 도 false alarm 도 전문에 0회인 논문이 "
        f"{C.num('counts.zero_cfar_and_falsealarm', 13, '{:.0f}')}편이다. "
        f"실시간 ISAC 플랫폼인 OpenISAC 조차 CFAR·false alarm·detection probability 가 전부 0회다.",
        "", "야외 실측은 잡음·클러터 분포를 통제하지 못해 명목 Pfa 를 고정할 수 없다. "
        "**통제 시뮬만 할 수 있는 일**이고, 그 자리가 04편이다."))

    # ── §4 ─────────────────────────────────────────────────────────────────
    B.append(md(
        "## §4. 그래서 비어 있는 칸, 그리고 우리가 주장하는 범위", "",
        table(["비어 있는 칸", "가장 가까운 선행", "무엇이 모자라나"],
              [["드론 메쉬에서 계산한 절대 σ", "Ziganshin (EuCAP 2025, 게재)",
                "표적이 PEC 차량이고 드론은 향후 과제다"],
               ["부품별 재질 + 광선추적 가림", "Clutter-Aware ISAC (Proc. IEEE 2026, 게재)",
                "메쉬를 넣되 엔진 기본 상호작용에 맡기고 σ 를 보고하지 않는다"],
               ["Pfa 교정된 검출 벤치마크", "OpenISAC (프리프린트)",
                "CFAR·false alarm·Pd 가 전문에 0회다"],
               ["한 표적·한 검출기로 세 파형 비교", "없음",
                "census 안에 파형을 공정 비교한 편이 없다"]])))

    B.append(md(
        "### §4.1. 주장 범위 — 어느 축이 어디서 오나", "",
        "빈칸이 있다고 그 칸을 다 채웠다는 뜻은 아니다. 이 프로젝트가 **무엇을 어디서 받는지**를 "
        "먼저 못박는다.", "",
        table(["축", "지지 근거", "어느 편"],
              [["자세 구조(σ 의 각도 모양)", "기하 — 부품별 재질 + 광선추적 가림", "02"],
               ["절대 σ 레벨", "외부 측정 앵커(Das, IEEE WCL 2026)", "02 §4"],
               ["주파수 의존성",
                f"외부 측정 앵커 — 우리 PO 기울기가 측정보다 "
                f"{C.num('context.slope_ratio.lo', fmt='{:.1f}')}~"
                f"{C.num('context.slope_ratio.hi', fmt='{:.1f}')}배 가파르다", "02 §4"],
               ["바이스태틱", "β≤45° 로 제한", "02"],
               ["마이크로도플러", "주장하지 않음 — future work", "—"],
               ["검출 성능(Pd/Pfa)", "통제 시뮬 + CFAR 교정", "04 · 05"]])))

    B.append(md(
        "### §4.2. 다음 편으로 넘기는 것", "",
        table(["이 편이 남긴 질문", "받는 편"],
              [["그 메쉬와 엔진이 실제로 무엇만큼 정확한가", "02 표적 모델"],
               ["세 조명원(LTE·5G·WiFi)의 격차는 σ 와 무관한가", "03 조명원"],
               ["명목 Pfa 와 경험 Pfa 가 얼마나 다른가", "04 검출기"],
               ["어느 파형·몇 개 수신기로 어느 거리까지 보이나", "05 검출 결과"],
               ["무엇을 재면 위 주장 중 어느 것이 결판나나", "06 실측 계획"]])))

    # ── 한계 ───────────────────────────────────────────────────────────────
    B.append(limits([
        ("census 가 16편이다 — 아카이브 나머지 편은 이 JSON 에 판정이 없다",
         "`benchmark/prior_census.py:77` 의 `P` 에 항목을 추가하고 `quotes` 로 귀속을 잠근 뒤 재실행"),
        ("IEEE 유료 프로시딩과 비영어 DB(CNKI·万方)가 탐색 밖이다 — md-rt 가 그런 경로의 논문이다",
         "Xplore 본문 검색 권한을 확보한 뒤 ICCT·EuRAD·RadarConf 프로시딩부터 같은 관문에 통과시킬 것"),
        ("전방인용 추적 시점이 2026-07 에 멈춰 있다",
         "`prior_work/sionna_sensing_survey.md` 의 라운드 규칙대로 갱신하고 census 에 반영"),
        ("선행 수치와 우리 수치를 나란히 놓지 않았다 — 이 편은 지도이지 대조표가 아니다",
         "02편 §4 앵커 원장과 05편 검출 비교에서 사과-대-사과 검사를 먼저 통과시킬 것"),
    ], sec="§5."))

    return B


# =========================================================================== #
def main():
    print("── 리포트 01 빌드 ──")
    C = from_json(CENSUS)
    for k in ("funnel", "matrix", "dbsm", "detect"):
        p = os.path.join(_ROOT, C.get(f"figures.{k}"))
        if not os.path.exists(p):
            raise SystemExit(f"그림이 없다: {p}\n  → benchmark/prior_census.py 를 먼저 돌려라.")
    rep = build_notebook(NB_OUT, blocks(C), strict=True)
    print(f"✅ {os.path.relpath(NB_OUT, _ROOT)}")
    return rep


if __name__ == "__main__":
    main()
