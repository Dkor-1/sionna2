# -*- coding: utf-8 -*-
"""PAPERS.md 생성기 — outputs/md_classification_dl_survey.json 원장에서 값을 그대로 옮긴다.
값(제목·연도·기법·데이터·정확도·링크)은 원장 복사, «우리와의 관계» 열만 이 스크립트가 얹는다."""
import json, io

SRC = "/workspace/sionna/outputs/md_classification_dl_survey.json"
OUT = "/workspace/team_meeting/dl_framework_papers/PAPERS.md"

d = json.load(open(SRC))

# «우리와의 관계» — 파이프라인 문서(DL_PIPELINE.md 부록 A·§4-3 차용표)에서 요약한 저자 주석.
rel_cls = [
    "문제 설정의 원조(드론 vs 새 프레임). 기체 홀드아웃 항목의 근거 중 하나",                      # Molchanov 2014
    "계보 정정용 — 첫 딥러닝은 CNN 이 아니라 DBN 이었다는 사실 확인. 직접 차용 없음",              # Mendis 2016
    "«데이터가 아니라 판정을 합쳐라» 교훈 — 우리 late fusion(늦은 결합) 방침의 근거",              # Ritchie 2016
    "표현 병합의 첫 증거(+5.4 pp) — 우리 CVD 병합 팔의 출발점",                                    # Kim 2017
    "고전 특징 기준선의 선례 — 딥러닝이 이겨야 할 선을 같은 데이터로 재는 형식",                    # Björklund 2018
    "같은 데이터에서 딥러닝이 고전을 이긴 선례(수치는 미공개)",                                     # Björklund 2019
    "⭐주춧돌 — 백본 고정·표현 5종 겨루기·날짜 분리 경고·WSP 팔 전부 이 편에서 차용",               # Gérard 2020
    "⭐주춧돌 — 경량 CNN 출발점·«전처리만 바꿔 +10 pp»·Adam 1e-4 의 근거",                          # Park(J.) 2020
    "전이학습 성숙기의 대표 사례(맥락 참조)",                                                       # Rahman&Robertson 2020
    "실수부·허수부 2채널 입력 규약을 이 편에서 가져옴",                                             # Park(D.) 2021
    "증강 3종(시간 이동·SNR 주입·결측 흉내)과 F1 vs SNR 곡선 보고 규약 차용",                       # Raval 2021
    "공개 데이터셋 DIAT-μSAT · VGG 전이 기준선(맥락 참조)",                                        # DIAT-μSAT 2022
    "«경량 전용 CNN 으로 충분» 방침의 근거 중 하나(0.45 M · 97.3 %)",                              # DIAT-RadSATNet 2022
    "물리 파라미터 재추첨 증강 차용 — 단 섭동 크기를 시험셋으로 튜닝한 점은 안 따르고 사전등록으로 대체", # Rojhani 2023
    "어텐션 갈래 대표(맥락 참조)",                                                                  # Dai 2023
    "⭐주춧돌 — 그룹(비행) 단위 분할·검증 분리·씨앗 짝맞춤·반합성 −3.1 pp·4팔 구조 전부 차용",       # White 2023/24
    "3종 표현 융합 >97 % — 표현 병합 이득의 추가 근거",                                             # Chen 2024
    "복소 시계열 직행 갈래 + 펄스당 SNR 정의(우리 잡음 축 규약의 근거)",                            # Malarvanan 2024
    "임베디드 지향 경량 CNN 사례(맥락 참조)",                                                       # Zhang(L.) 2025
    "시계열 직행 4종 비교 — 우리 1D 분기 규약과 Adam 1e-4·patience 5 의 근거",                      # Larrat 2025
    "통신 파형 실측 에코를 딥러닝으로 분류한 유일 확인 사례 — 우리 ISAC 맥락의 최근접 이웃",         # Xue DC-Former 2025
    "공개 벤치마크 LSS-FMCWR-1.0 사용 사례(맥락 참조, 밴드 표기 주의 — §3-4 정정 13)",              # PinpuNet 2025
    "가변 크기 스펙트로그램을 그대로 다루는 ViT 사례(맥락 참조)",                                   # Czuba 2025
    "듀얼밴드 late fusion 차용의 직접 근거",                                                        # Zhang&Song 2026
    "기체 홀드아웃 Fig.12·SNR 11단 증강의 근거 — 동시에 분할 규약 미기재의 반면교사",                # AirGuard 2026
    "seen(같은 조건 안) 설정의 대조 사례 + 미지 서브타입 일반화(개방집합에 가장 가까움)",            # Networked ISAC 2026
    "⭐주춧돌 — 표본별 정규화·측정 단위 분할·macro-F1 묶음·소데이터 고전 기준선 전부 차용",          # Mustafa 2026
    "⭐주춧돌 — «저충실도 시뮬 단독 학습은 무작위 추측 수준» 경고 + 물리유도 갈래의 대표",           # Kearney&Gurbuz 2026
    "협조적 태깅 갈래(태그를 붙인 드론만 식별) — 비협조 표적인 우리 문제엔 이전 불가, 맥락 참조",    # μDopplerTag 2026
]
rel_anchor = [
    "물리 앵커 — 드론 마이크로도플러는 몸체 대비 −20~−40 dB 라는 기준 수치의 출처",                 # Rahman&Robertson 2018
    "실기 모터속도 로그 주입으로 시뮬 충실도를 올린 선례 — White 반합성 편의 전신",                 # White 2022
    "⭐주춧돌 — NCC 0.7 물리 게이트·CAD 정밀도 민감성·합성 전용→실측의 한정적 예외(§주의 절)",       # Moore 2024
    "Sionna RT 로 멀티로터 마이크로도플러를 뽑은 사례(분류 없음) — 우리와 도구가 겹침",              # Li 2025
    "바이스태틱 OFDM 마이크로도플러 모델 — 학습을 후속과제로 비워 둔 그 자리가 우리 자리",           # Costa 2025
]
rel_survey = [
    "본문 미확보(로컬 PDF 가 차단 페이지) — 인용 금지 상태",                                        # Hanif 2022
    "레이다 인식 6기술 체계 참조(투고판/게재판 구별 주의 — §3-4 정정 20)",                          # Semenyuk 2024
    "능동/패시브/드론 자체 RF 를 절 단위로 나눈 체계 참조(수치 예시는 전부 능동)",                  # Khawaja 2025
    "패시브 한정 서베이 — 분류 정확도 인용이 0건이라는 사실 자체가 우리 자리의 방증",                # Tang 2025
    "통신 파형 한정 서베이 — DC-Former·PinpuNet 두 편의 1차 정보원(재인용 위치 §III-C)",             # Bai 2026
]

def esc(s):
    return s.replace("|", "\\|") if isinstance(s, str) else s

def table(rows, rels, with_acc=True):
    buf = []
    buf.append("| 논문 | 연도 | 기법 | 데이터 | 정확도 | 우리와의 관계 | 링크 |")
    buf.append("|---|---|---|---|---|---|---|")
    assert len(rows) == len(rels), (len(rows), len(rels))
    for row, rel in zip(rows, rels):
        buf.append("| {p} | {y} | {m} | {d} | {a} | {r} | {l} |".format(
            p=esc(row["paper"]), y=row["year"], m=esc(row["method"]),
            d=esc(row["data"]), a=esc(row.get("accuracy", "—") or "—"),
            r=rel, l=row["link"]))
    return "\n".join(buf)

head = """# 전체 목록 — 원문 검증을 통과한 선행 논문 39편

> 이 표의 **제목·연도·기법·데이터·정확도·링크는 전부 수치 원장**
> `sionna2` 저장소 `outputs/md_classification_dl_survey.json` **에서 그대로 옮긴 것**이고,
> 값은 하나도 고치지 않았다. 이 폴더에서 새로 쓴 것은 «우리와의 관계» 열 하나뿐이다.
> 굵게·⭐·⚠ 표시도 원장 그대로다(⚠ 는 «원문에서 그대로 확인 못 한 부분이 있다»는 단서).
>
> 읽는 법 — 표는 서베이 §3 과 같은 세 덩이다. **분류 실험이 있는 논문 29편**,
> **분류기 없는 물리·시뮬 앵커 5편**(분류는 안 했지만 물리 수치나 시뮬 방법의 기준이 되는 편),
> **서베이·리뷰 5편**. 정확도 칸의 단위는 편마다 다르다(정확도·F1·AUC·ACRR) —
> **한 열에 있다고 같은 잣대가 아니다.**

"""

parts = [head]
parts.append("## 1. 분류 실험이 있는 논문 (29편)\n")
parts.append(table(d["table_classification_papers"], rel_cls))
parts.append("\n\n## 2. 분류기 없는 물리·시뮬 앵커 (5편)\n")
parts.append(table(d["table_simulation_anchors"], rel_anchor))
parts.append("\n\n## 3. 서베이·리뷰 (5편)\n")
parts.append(table(d["table_surveys"], rel_survey))
parts.append("""

---

## 표 밖의 논문 — 넣지 않은 것들 (정직 단서)

서베이가 수집한 45편 중 위 표에 없는 6편은 다음과 같다(서베이 §5 그대로).

- **판정 «불통과» 2편** — 검색엔진 요약이 두 논문을 섞은 오염 사례 1편(Kaushal 2025 EAIC)과,
  저널판과 제목이 다른 학회판 1편(Kearney & Gurbuz 의 학회판). 표에는 안 싣는다.
- **판정 자체를 못 받은 4편** — Huizing 2019(표준 인용처인데 미확정) · Vorobev 2019 ·
  Cao 2025 · Kulpa 2025. ⭐**패시브 후보 3편이 전부 이 칸에 몰려 있다**는 점이 중요하다 —
  «패시브 + 딥러닝 분류 0편»이라는 문장은 앞 조사 판정(셋 다 딥러닝 아님)까지 합쳐야 살아남는다.

자세한 사연은 서베이 원문 `prior_work/md_classification_dl_survey.md` §5 에 있다.
""")

out = "\n".join(parts)
assert ";" not in out.replace("&#59", ""), "세미콜론 금지 규약 위반"
io.open(OUT, "w", encoding="utf-8").write(out)
n = len(d["table_classification_papers"]) + len(d["table_simulation_anchors"]) + len(d["table_surveys"])
print("wrote", OUT, "papers:", n)
