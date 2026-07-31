# prior_work/ — 선행 연구·도구 조사 (Sionna 기반 ISAC 센싱)

질문 두 개에 답하는 조사 리포트 시리즈:

1. **선행 논문들은 Sionna 로 ISAC 센싱을 했는가?** 했다면 우리가 마주한 간극
   (소형 표적 산란적분 부재, report06)을 **어떻게 해결했는가** — 대형 표적 경면 반사?
   산란계수(S) 가정? 외부 RCS 주입(하이브리드)? 
2. **오픈소스 도구 지도** — ns3sionna·MaxRay·RadarSimPy·Great-X 등 무엇이 실재하고
   무엇을 해 주는가, 우리 프로젝트에 수용할 만한 것이 있는가.

원칙:
- **웹 검증된 사실만** 싣는다 — 다른 AI 답변에 등장한 논문·도구명은 환각 가능성이
  있으므로(예: "SimART" 실재 여부 미확인) 실재 확인 후에만 인용한다.
- 사실마다 출처 링크(arXiv/IEEE/GitHub)를 단다.
- 각 선행 방법이 우리 리포트(report06 Q&A·report12 §2b)와 정합하는지/모순인지 명시한다.
- 조사 원문 요약은 `/data/public/sionna_jeong/papers_isac_sionna/` 에도 저장(지속 확인용),
  워크스페이스 미러는 저장소 루트의 `refs/drone_papers/`.

구성(조사 완료 후 생성):
- `pw01_sionna_isac_papers.ipynb` — Sionna-ISAC 선행 논문: 실재 검증·표적 산란 처리 방식 분류
- `pw02_opensource_tools.ipynb` — 오픈소스 센싱/ISAC 도구 능력 매트릭스와 수용성 평가
- `pw03_positioning.ipynb` — 우리 방법의 위치: 선행 방법론 대비 동일점·차이점·수용 계획
- `pw04_rcs_solution_by_target.ipynb` — **Sionna 로 센싱한 연구는 RCS 문제를 어떻게 해결했나**: Sionna 사용 논문만 대상, A1(외부 EM solver)·A2(Sionna 확장)·B(외생/점산란체)·C(mesh 반사 우회)·D(구현 미보고) 5갈래 + 표3(외부 RCS 모델·설계근거) + 방식별 비교·이중계산 경고·복소 산란행렬·권장구조·연구공백. 3중 워크플로(60여 에이전트) + 타 LLM 조사 대조, 1차 출처 검증(오류 2건 제외·과장 3건 정정). 데이터: `src/pw04_data.py`
생성기는 `src/make_pw0N.py` (하우스 규약: 노트북=생성물, 수치·인용=검증 JSON에서).

---

## 2026-07-31 — 1차 사료 정산과 `build_prior_survey.py`

리포트 01 의 근거는 이제 `outputs/prior_work_survey.json` 한 개다. 생성기는
`src/build_prior_survey.py` 이고, **PDF 를 직접 열어** 판정한다:

- 논문 21편(게재 11 · 프리프린트 10) — census 16편 + 5편(Rzewuski · FWA cube · Great-X ·
  CellSense · Temporal-GNN)
- 축자 인용 46건을 **PDF 그 쪽에서** 기계가 찾는다. 못 찾으면 빌드가 죽는다
- 낱말 빈도(dBsm · CFAR · false alarm · physical optics · validate)를 전문에서 직접 센다
- H8 을 네 관문(P1 게재 · P2 드론 메쉬 · P3 Sionna 계열 엔진 · P4 진폭 검증)으로 쪼개 후보 8편을 판정
- 그림 4장(`outputs/figures/report01_survey_*.png`)도 여기서 그린다

정산으로 뒤집힌 것(자세한 원장은 `outputs/prior_settled_*.json` 4개 · survey JSON 의
`contradictions`): Clutter-Aware ISAC 은 **Sionna 를 쓴다**(pw04 의 제외 항목을 삭제하고
표2 행으로 편입) · md-rt 는 **광선발사기를 개조**했다 · Ziganshin 저널판은 **OJAP 투고
프리프린트** · OpenISAC 은 **프리프린트** · LAMBDA 의 **CADFEKO 는 원문에 두 번 명시** ·
Sionna RT 1차 사료 2편은 등급 **[W]→[P](=`PRIMARY`)** · Wypich & Zielinski 는 **원문 미확보**
로 강등 · Ezuma/Güvenç 앵커 3행의 `VERIFIED` 제거.

    ~/.venvs/py312/bin/python prior_work/src/build_prior_survey.py   # 근거 + 그림
    PYTHONPATH=src ~/.venvs/py312/bin/python src/make_report01_prior.py
