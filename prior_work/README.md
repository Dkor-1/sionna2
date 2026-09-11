# prior_work/ — 선행 연구·도구 조사 (Sionna 기반 ISAC 센싱)

질문 두 개에 답하는 조사 리포트 시리즈:

1. **선행 논문들은 Sionna 로 ISAC 센싱을 했는가?** 했다면 우리가 마주한 간극
   (소형 표적 산란적분 부재, report06)을 **어떻게 해결했는가** — 대형 표적 경면 반사?
   산란계수(S) 가정? 외부 RCS 주입(하이브리드)? 
2. **오픈소스 도구 지도** — ns3sionna·MaxRay·RadarSimPy·Great-X 등 무엇이 실재하고
   무엇을 해 주는가, 우리 프로젝트에 수용할 만한 것이 있는가.

원칙:
- **웹 검증된 사실만** 싣는다 — 다른 AI 답변에 등장한 논문·도구명은 환각 가능성이
  있으므로 실재 확인 후에만 인용한다.
  ⚠2026-09-11 정정 — 여기 예로 들었던 "SimART" 는 **실재가 확인됐다**(arXiv 2605.13309,
  소장본에 있고 `sionna_sensing_survey.md` §R1 · `sionna_solver_settings_survey.md` 에 등재).
  이 줄의 «미확인» 은 그 뒤 조사에서 풀렸는데 문면이 안 따라왔다.
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

## 2026-09-11 — 공백 구간 조사 (`build_survey_0911.py`)

소장본 `/data/public/sionna_jeong/` 이 **2026-08-11 에서 멈춰 있었다**(PDF 373 · arXiv 번호
206 개 · 가장 새 번호 2607). 그 뒤 두 달을 arXiv API **목록 조회**로 훑었다.

    CUDA_VISIBLE_DEVICES="" taskset -c 8-11 \
      /workspace/.venvs/py312/bin/python prior_work/src/build_survey_0911.py

- 축 일곱(드론 ISAC · 마이크로도플러 · 광선추적 ISAC · Sionna · UAV RCS · 패시브 통신신호 ·
  sim-to-real) · 걸린 것 **64 편** → 상 39 · 중 4 · 하 21 · **43 편 내려받음**
- 원장 `/data/public/sionna_jeong/survey_0911/survey_0911.json` ·
  읽는 문서 `/data/public/sionna_jeong/survey_0911/INDEX.md`
- ⛔**초록까지만** 읽고 쓴 판정이다. 본문을 열면 바뀔 수 있다. ⛔arXiv 밖은 손으로 확인했다.

⭐**가장 큰 것** — `2608.05826` · `2608.10784`(Gurung 외)가 **OpenAirInterface + FlexRIC +
Sionna RT** 로 5G NR 상향 SRS 를 패시브 레이다 파형으로 쓰는 O-RAN 시험대를 세웠다.
우리 틀과 같은 자리다. 초록 기준 그들의 표적 RCS 는 **값으로 주어진다**(−8 ~ −20 dBsm) —
기체 메시에서 계산한 것이 아니다. ⛔이것은 초록만 본 말이라 **본문 확인 전에는 인용하지 않는다.**

⭐**유지되는 것** — 「망 신호로 비춘 드론 에코 공개셋」은 두 달 치를 더 훑어도 LIPASE 하나다.
2026-02 Nature Scientific Data 의 다중센서 드론 자료는 **CW·FMCW 능동 레이다**라 해당하지 않는다.

---

## 2026-09-11(2) — ⭐**게재지를 정본으로** 다시 (`build_toptier_0911.py`)

> **사용자 지적** — 「선행 연구는 아카이브뿐만 아니라 **탑티어 논문**을 찾는 것이 주 목표여야 한다」
> 「**ICASSP · MobiCom · SIGCOMM · SenSys · MobiSys** 계열도 우리 목표 탑티어로 봐 달라」

같은 날 먼저 한 arXiv 조사(위)는 **설계가 틀렸다.** 프리프린트는 「게재됐나·어디에」를 안 준다.

    CUDA_VISIBLE_DEVICES="" taskset -c 8-11 \
      /workspace/.venvs/py312/bin/python prior_work/src/build_toptier_0911.py

- **Crossref**(ISSN·DOI 앞자리 · 제목) + **OpenAlex**(초록까지) 두 채널 — 학술지 25 종 +
  **학회 11 종**, 2025-01 이후 **275 편**(정본 123 · 일반 152)
- 탑티어 기준은 `dl_toptier_anchors.md` 의 것을 따르고 주제 학술지·학회를 얹었다(까닭은 원장에)
- ⭐**네 판을 거쳤다**(자기감사 수치):

  | 항목 | 1 판 | 2 판 | 3 판 | 지금 |
  |---|---|---|---|---|
  | 편 수 | 366 | 191 | 263 | **275** |
  | 제어·비전 오염 | 14 % | 0 % | 0 % | **0 %** |
  | 재현율(아는 6 편) | 3/6 | 3/6 | 4/6 | **4/6** |
  | 게재지 딱지 오염 | MMAR→RadarConf | 0 | 0 | **0** |
  | 잘림 경고 | 페이징 없음 | — | 95 | **0** |
  | RadarConf · EuCAP | 31 · 0 | 0 · 0 | 16 · 16 | **63 · 66** |

- ⛔고친 것 넷 — ⓐ쪽 수 5→20 + 마른 쪽 조기종료 ⓑOpenAlex 채널(제목만 보던 한계)
  ⓒ게재지 층(정본/일반) ⓓ학회는 `query.container-title` 이 **필터가 아니라 퍼지 검색**이라
  엉뚱한 논문집(LCN·NordPac)을 돌려줬다 ⇒ 학회 이름을 **주제어에 섞어** 묻고 되짚어 고른다.
  (그 전 판들: `type:journal-article` 로 걸러 학회가 통째로 빠졌고, IEEE 학회는 ISSN 필터가
  안 먹는다 — 실측 ICASSP ISSN 조회 0 건.)
- ⛔**아직 안 된 것** — 재현율 4/6(Zhang JSAC·Clutter-Aware 는 제목에 우리 낱말이 없다) ·
  초록을 다 못 읽었다 · NeurIPS·CVPR 은 Crossref 색인이 고르지 않다 · 구독지(IET/Wiley) 403.
- 원장 `/data/public/sionna_jeong/toptier_0911/toptier_0911.json` · 문서 `.../INDEX.md`

⭐**가장 큰 것 — 소장본 373 편은 거의 전부 arXiv 였고 게재지 축이 사실상 비어 있었다**(중복 2 편).
그 축에 우리 물음의 **직격탄**이 있었다:

| 게재판 | 무엇 |
|---|---|
| IEEE **TWC** 24(12) 2025 `10.1109/twc.2025.3578033` | **ISAC 신호로 로터 마이크로도플러** 추출 + 시험대. 우리 틀과 가장 가까운 게재판. 프리프린트 arXiv 2408.16415 는 **소장에 없었다** |
| IEEE **TAES** 61(4) 2025 `10.1109/taes.2025.3545000` | **4G-LTE 패시브 레이다**로 드론 검출, 비협조 송신기 실측 |
| **IET RSN** 19(1) 2025 `10.1049/rsn2.70092` | **LTE450 패시브 레이다** 드론 검출 실증 — OFDM **기준 요소만** 써서 |
| IEEE **OJAP** 2026 `10.1109/ojap.2026.3720651` | **미분 가능 광선추적**을 저고도 드론 채널에 **보정**. 우리가 못 한 그 자리 |
| **EuCAP 2026** | ⭐«Monostatic-Bistatic Equivalence Theorem for **Drone RCS**» — 우리 SBR 이 모노스태틱만 낸다는 **바로 그 한계** · «**Propeller Blade Orientation** 이 마이크로도플러에 미치는 영향» — 우리 blperairframe 축과 같은 물음 · «**Multi-Link** Micro-Doppler **Measurements** for ISAC» |
| **IET RSN** 20(1) 2026 `10.1049/rsn2.70201` | **완전파(HFSS)**로 드론 전방산란 RCS 100 MHz~5 GHz |

⭐**일곱 편을 정독했다**(반증까지) — 표적 반사 세기를 어디서 가져오나:
  · **값 주입** TWC(동체 σ=0.1 m² 상수 + 날개 계수를 IEEE Access 2019 에서 인용)
  · **모델 없음** TAES·IET RSN(세기는 실측 그 자체)
  · **계산** IET RSN 완전파(HFSS, 단 **PEC**) · EuCAP 날개방향(**점산란체** PO)
  · **측정** EuCAP 등가정리(실물 Phantom 3, 회로망분석기, 11–26 GHz, 방위 360 점)
  ⇒ 일곱 가운데 **기체 메시에 재질을 먹여** 산란을 풀고 광선 엔진에 얹는 편은 **없다**.
  ⛔단 「우리가 처음」으로 쓰지 않는다 — 일곱 편을 읽은 범위 안의 말이다.
  ⛔셋 다(TWC·TAES·IET RSN) **자료를 공개하지 않았다** — IET RSN 은 «The authors have nothing to report.»

⛔**이 정독이 우리 사실 하나를 뒤집었다** — `REC.phantom`(Taylor & Poullin 표적 기체).
  공백이 지워진 PDF 추출문에서 «없다» 를 센 탓이었다. 자세히는 커밋 240d4abb.

⚠**랩카드 주장의 범위** — 망 신호로 드론을 잰 **게재 논문은 여럿 있다**(우리가 처음이 아니다).
공개 **데이터셋**은 여전히 LIPASE 하나이고 **우리 자신의 실측은 0 건**이다.
⇒ 살아남는 문장은 「우리 손에 없다」·「공개된 자료가 드물다」 뿐이다.
⛔「아무도 안 했다」·「우리가 처음」류의 말을 덱·카드·문서 어디에도 쓰지 않는다.

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
표2 행으로 편입) · md-rt 는 **광선발사기를 개조**했다 · ⭐Ziganshin 저널판은 **2026-08-17 부로
OJAP 게재 확정**(DOI `10.1109/OJAP.2026.3717211`, Crossref `journal-article` · 단 쪽 `1-1`
= **Early Access** 이므로 권·쪽 인용 금지 — 자세히는 `po_refinement_survey.md` §4.1) ·
OpenISAC 은 **프리프린트** · LAMBDA 의 **CADFEKO 는 원문에 두 번 명시** ·
Sionna RT 1차 사료 2편은 등급 **[W]→[P](=`PRIMARY`)** · Wypich & Zielinski 는 **원문 미확보**
로 강등 · Ezuma/Güvenç 앵커 3행의 `VERIFIED` 제거.

    ~/.venvs/py312/bin/python prior_work/src/build_prior_survey.py   # 근거 + 그림
    PYTHONPATH=src ~/.venvs/py312/bin/python src/make_report01_prior.py
