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
  워크스페이스 미러는 이 폴더의 `refs/`.

구성(조사 완료 후 생성):
- `pw01_sionna_isac_papers.ipynb` — Sionna-ISAC 선행 논문: 실재 검증·표적 산란 처리 방식 분류
- `pw02_opensource_tools.ipynb` — 오픈소스 센싱/ISAC 도구 능력 매트릭스와 수용성 평가
- `pw03_positioning.ipynb` — 우리 방법의 위치: 선행 방법론 대비 동일점·차이점·수용 계획
생성기는 `src/make_pw0N.py` (하우스 규약: 노트북=생성물, 수치·인용=검증 JSON에서).
