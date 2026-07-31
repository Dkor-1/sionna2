# -*- coding: utf-8 -*-
"""
build_prior_survey.py — 리포트 01 의 근거 JSON `outputs/prior_work_survey.json` 을 만든다.
============================================================================================
이 파일이 하는 일
    아카이브 PDF 21편을 **직접 열어** 판정표를 만든다. 판정마다 축자 인용을 PDF 안에서
    기계가 대조하고, 못 찾으면 그 자리에서 죽는다(귀속 위조 방지). 그림 4장도 여기서 그린다.

무엇이 `benchmark/prior_census.py` 와 다른가
    census 는 16편을 셌다. 2026-07-31 1차 사료 정산이 5편을 더 읽었고(Rzewuski · FWA cube ·
    Great-X · CellSense · Temporal-GNN), 기존 판정 몇 개를 뒤집었다. 이 파일은 그 결과를
    한 장의 표로 합친다 — 다음 라운드가 diff 로 비교할 수 있도록.

정산의 출처(모두 이 저장소 안)
    outputs/prior_settled_h8.json        H8 4관문 판정 · 조달 카탈로그 · Rzewuski
    outputs/prior_settled_sionna.json    Sionna RT 1차 사료 · Clutter-Aware · md-rt
    outputs/prior_settled_ziganshin.json Ziganshin 두 판 · Sagitta · LAMBDA · Montaner
    outputs/prior_settled_anchor.json    Das · Yuan · Zhang 앵커

규칙 (E1~E6 재발 방지)
    사실 한 줄에 (a) PDF 경로 (b) 어느 판 (c) 축자 문장이 전부 붙는다. 하나라도 없으면
    UNVERIFIED 로 적는다. 숫자는 PDF 나 저장소 JSON 에서만 오고, 기억에서 오지 않는다.

실행
    cd /home/yunjung/workspace/sionna2
    ~/.venvs/py312/bin/python prior_work/src/build_prior_survey.py
    → outputs/prior_work_survey.json + outputs/figures/report01_survey_*.png  (CPU, 수 초)
"""
from __future__ import annotations

import json
import os
import re
import unicodedata
from datetime import datetime

import fitz                                    # PyMuPDF
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                # noqa: E402
import numpy as np                             # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
ARC = "/data/public/sionna_jeong/papers_isac_sionna"
RAY = ARC + "/paper_sionna_Ray_0723"
TASK = "/data/public/sionna_jeong/sionna_papers_by_task/channel_modeling_raytracing"
PASSIVE = "/data/public/jeong/papers/Wifi"
OUT = os.path.join(ROOT, "outputs", "prior_work_survey.json")
FIGDIR = os.path.join(ROOT, "outputs", "figures")

# --------------------------------------------------------------------------- #
#  PDF 원문 대조
# --------------------------------------------------------------------------- #
_CACHE: dict[str, list[str]] = {}


def norm(s: str, join: str = "-") -> str:
    """리가처·소프트하이픈·줄바꿈 하이픈·공백을 정규화한다(인용 대조용).

    PDF 는 줄 끝에서 낱말을 자른다. 그 자리가 원래 하이픈이었는지("finite-difference")
    단순 음절 분리였는지("elec- trically") 텍스트만 봐서는 갈리지 않는다. 그래서 두 가지로
    정규화해 두고 **둘 중 하나만 맞아도** 통과시킨다.
    """
    s = unicodedata.normalize("NFKC", str(s)).replace("­", "")
    s = re.sub(r"[\x00-\x1f]", " ", s)     # 조판 글리프(도 기호 등)가 제어문자로 나온다
    s = re.sub(r"-\s+", join, s)
    return re.sub(r"\s+", " ", s).strip()


def pages(pdf: str, join: str = "-") -> list[str]:
    ck = f"{pdf}|{join}"
    if ck not in _CACHE:
        if not os.path.exists(pdf):
            raise SystemExit(f"PDF 가 없다: {pdf}")
        with fitz.open(pdf) as d:
            _CACHE[ck] = [norm(p.get_text(), join) for p in d]
    return _CACHE[ck]


def check(pdf: str, page: int, quote: str) -> dict:
    """축자 인용이 그 PDF 그 쪽에 실제로 있는지 확인한다. 없으면 빌드를 죽인다."""
    P, Q = pages(pdf, "-"), pages(pdf, "")
    if not (1 <= page <= len(P)):
        raise SystemExit(f"쪽 번호가 범위 밖이다: {pdf} p{page} (전체 {len(P)}쪽)")
    hit = (norm(quote, "-") in P[page - 1]) or (norm(quote, "") in Q[page - 1])
    if not hit:
        where = [i + 1 for i in range(len(P))
                 if norm(quote, "-") in P[i] or norm(quote, "") in Q[i]]
        raise SystemExit(f"인용을 PDF 에서 못 찾았다 — {os.path.basename(pdf)} p{page}\n"
                         f"  인용: {quote[:90]}…\n"
                         f"  실제로 있는 쪽: {where or '없음'}")
    return dict(pdf=pdf, page=page, quote=quote)


TERM_PATTERNS = {
    "sionna": r"sionna",
    "ray_tracing": r"ray[- ]trac",
    "dbsm": r"dBsm",
    "rcs": r"\bRCS\b|radar cross[- ]section",
    "cfar": r"\bCFAR\b",
    "false_alarm": r"false[- ]alarm",
    "detection_probability": r"detection probability|probability of detection",
    "physical_optics": r"physical optics",
    "drone_uav": r"drone|\bUAV\b|\bAAV\b",
    "validate": r"validat",
    "mesh": r"\bmesh(?:es)?\b",
}


def terms(pdf: str) -> dict:
    t = " ".join(pages(pdf))
    return {k: len(re.findall(v, t, re.I)) for k, v in TERM_PATTERNS.items()}


# --------------------------------------------------------------------------- #
#  조달 경로 — Q2 카탈로그. 표적 서명을 어디서 가져왔나, 그것이 무슨 주장을 사 주나.
# --------------------------------------------------------------------------- #
ROUTES = {
    "R1": dict(label_ko="그 기체를 직접 잰다 (무향실·CATR)", label_en="Chamber measurement",
               short_ko="무향실 측정",
               bought_ko="그 기체 그 대역의 절대 σ 와 계수표"),
    "R2": dict(label_ko="full-wave 솔버로 그 기체를 푼다 (광선엔진 밖)",
               label_en="Full-wave solver (FDTD/MoM)", short_ko="full-wave 솔버",
               bought_ko="바이스태틱 절대 σ 와 그것을 먹는 커버리지 예산"),
    "R3": dict(label_ko="외부 σ 를 광선경로에 주입한다", label_en="External RCS injected",
               short_ko="외부 σ 주입",
               bought_ko="엔진을 건드리지 않고 얻는 자세의존 진폭"),
    "R4": dict(label_ko="해석 표적 모델 (thin-wire · 점산란체 연속체)",
               label_en="Analytic target model", short_ko="해석 표적 모델",
               bought_ko="마이크로도플러 서명의 모양과 상관계수"),
    "R5": dict(label_ko="추상 계수 · 점산란체 · 기하 프리미티브",
               label_en="Abstract coefficient / primitive", short_ko="추상 계수·프리미티브",
               bought_ko="폐형식 신호모델과 검출·추정 통계"),
    "R6": dict(label_ko="엔진 기본 상호작용에 맡긴다 (스톡 재질·확산계수)",
               label_en="Stock engine interactions", short_ko="엔진 기본 상호작용",
               bought_ko="운동학 서명 · 지연-도플러 구조 · 데이터셋"),
    "R7": dict(label_ko="엔진 안에서 메쉬 산란을 계산한다", label_en="Mesh scattering in-engine",
               short_ko="엔진 안 메쉬 산란",
               bought_ko="기하와 일관된 서명, 멀티스태틱 확장 가능"),
}

# --------------------------------------------------------------------------- #
#  판정표 — 21편. gates 는 순차 관문, prongs 는 H8 4관문.
# --------------------------------------------------------------------------- #
G = lambda a, b, c, d: dict(g1_engine=a, g2_drone_mesh=b, g3_mesh_scattering=c, g4_dbsm=d)  # noqa: E731

PAPERS = [
    dict(key="yuan", short="Yuan (EuCAP 2025)", short_ko="Yuan (모노 3D)",
         first_author="Z. Yuan", year=2025, venue_ko="EuCAP", venue_en="EuCAP",
         status="published", status_ko="게재",
         locator="DOI 10.23919/EuCAP63536.2025.10999912",
         venue_evidence="PDF 메타데이터 subject", pdf=f"{RAY}/On_Experimental_Analysis_of_Mono-Static_3D_UAV_RCS_for_ISAC_Channel_Modeling.pdf",
         engine_ko="미사용", target_ko="DJI Phantom 3 · 무향실 CATR · VV",
         route="R1", claimed_ko="한 기체의 모노스태틱 σ(f, 방위)를 1.8–18.2 GHz 에서 dBsm 으로",
         gates=G(0, 0, 0, 1),
         quotes=[(2, "the DJI Phantom 3, featuring four symmetrical rotors with a horizontal diagonal of 35 cm"),
                 (2, "Both the transmitter and receiver (TX and RX) were equipped with vertically polarized directional antennas"),
                 (4, "the regression parameters mean values {a, b, c, d} are calculated as")]),
    dict(key="das", short="Das (WCL 2026)", short_ko="Das (멀티밴드)",
         first_author="S. Das", year=2026, venue_ko="IEEE WCL", venue_en="IEEE WCL",
         status="published", status_ko="게재",
         locator="vol. 15, pp. 3731–3735, DOI 10.1109/LWC.2026.3705634",
         venue_evidence="PDF 메타데이터 subject + 본문 러닝헤드",
         pdf=f"{RAY}/Multiband_Monostatic_and_Bistatic_RCS_Characterization_of_AAVs_for_ISAC_Channel_Modeling.pdf",
         engine_ko="미사용", target_ko="DJI 4기종 · 1.8–27 GHz · 바이스태틱각 0–90°",
         route="R1", claimed_ko="기체·각도별 μ(f)·ε(f) 1차식 계수표 — 채널모델에 그대로 붙는다",
         gates=G(0, 0, 0, 1),
         quotes=[(1, "Monostatic and bistatic RCS measurements for four AAVs"),
                 (2, "The mean RCS is defined as"),
                 (2, "the target is effectively point-like within each sub-band")]),
    dict(key="zhang", short="Zhang (JSAC 2026)", short_ko="Zhang (통합 RCS)",
         first_author="P. Zhang", year=2026, venue_ko="IEEE JSAC", venue_en="IEEE JSAC",
         status="published", status_ko="게재",
         locator="vol. 44, pp. 702–716, DOI 10.1109/JSAC.2025.3608732",
         venue_evidence="PDF 메타데이터 subject + p1 러닝헤드",
         pdf=f"{RAY}/A_Unified_RCS_Modeling_of_Typical_Targets_for_3GPP_ISAC_Channel_Standardization_and_Experimental_Analysis.pdf",
         engine_ko="미사용", target_ko="DJI M350 · 사람 · 차량 · 10–36 GHz VNA",
         route="R1", claimed_ko="측정으로 맞춘 분해 σ = A(f)·B1(φ)·B2, 3GPP TSG RAN1 채택",
         gates=G(0, 0, 0, 1),
         quotes=[(7, "The AAV used is the DJI M350"),
                 (9, "calculating the linear average of the RCS values measured at all angles"),
                 (7, "adopted by the 3GPP Technical Specification Group Radio Access Network Working Group 1")]),
    dict(key="rzewuski", short="Rzewuski (NATO STO 2021)", short_ko="Rzewuski (WiFi 패시브)",
         first_author="S. Rzewuski", year=2021, venue_ko="NATO STO-MP-MSG-SET-183",
         venue_en="NATO STO", status="published", status_ko="게재",
         locator="STO-MP-MSG-SET-183, paper 13",
         venue_evidence="전 쪽 보고서 코드 + PDF 메타데이터 subject 'MSG-SET-183'",
         pdf=f"{PASSIVE}/21_Drone Detectability Feasibility Study using Passive Radars Operating in WIFI and DVB-T Band.pdf",
         engine_ko="미사용 (FDTD QuickWave-3D)", target_ko="Parrot AR.Drone 2.0 · WiFi/DVB-T 패시브",
         route="R2", claimed_ko="WiFi 대역 드론 바이스태틱 σ(−40~0 dBsm)와 실측 검출 50 m",
         gates=G(0, 0, 0, 1),
         quotes=[(4, "Mono- and bi-static radar cross-sections (RCS) of the Parrot AR.Drone 2.0 were computed with a finite-difference time-domain (FDTD) method implemented in the commercial software package, QuickWave-3D"),
                 (5, "the RCS range for WIFI band is between -40dBsm and 0dBsm"),
                 (9, "it is possible to detect small size Parrot AR. Drone on bistatic distance equal to 50m")]),
    dict(key="costa_c", short="Costa conf. (RadarConf 2024)", short_ko="Costa (회의판)",
         first_author="H. C. A. Costa", year=2024, venue_ko="IEEE RadarConf",
         venue_en="IEEE RadarConf", status="published", status_ko="게재",
         locator="IEEE Xplore 다운로드 스탬프(전 쪽)", venue_evidence="본문 · Xplore 스탬프",
         pdf=f"{RAY}/Modelling_Micro-Doppler_Signature_of_Drone_Propellers_in_Distributed_ISAC.pdf",
         engine_ko="미사용", target_ko="프로펠러를 thin-wire 점산란체 연속체로",
         route="R4", claimed_ko="바이스태틱 마이크로도플러 서명의 모양, 실측 대조 상관 0.98",
         gates=G(0, 0, 0, 0),
         quotes=[(5, "returns a cross-correlation coefficient of approximately 0.98")]),
    dict(key="costa_j", short="Costa jour. (JSTEAP 2025)", short_ko="Costa (저널판)",
         first_author="H. C. A. Costa", year=2025, venue_ko="IEEE JSTEAP", venue_en="IEEE JSTEAP",
         status="published", status_ko="게재",
         locator="vol. 1, pp. 208–222, DOI 10.1109/JSTEAP.2025.3604407",
         venue_evidence="PDF 메타데이터 subject",
         pdf=f"{RAY}/Modeling_Micro-Doppler_Signature_of_Multi-Propeller_Drones_in_Distributed_ISAC.pdf",
         engine_ko="미사용", target_ko="다중 프로펠러 thin-wire + 동체(가우시안·측정 반사율)",
         route="R4", claimed_ko="바이스태틱각 30–180°에서 실측 대비 Pearson 상관 0.98",
         gates=G(0, 0, 0, 0),
         quotes=[(2, "the most used method for modeling rotating propellers is the thin wire model"),
                 (6, "This produces a cross-correlation coefficient of 0.98 across the bistatic angles from 30 to 180")]),
    dict(key="wei", short="Wei (TWC 2025)", short_ko="Wei (테스트베드)",
         first_author="J. Wei", year=2025, venue_ko="IEEE TWC", venue_en="IEEE TWC",
         status="published", status_ko="게재",
         locator="vol. 24, no. 12, pp. 10166–10182, DOI 10.1109/TWC.2025.3578033",
         venue_evidence="PDF 메타데이터 subject + p1 러닝헤드",
         pdf=f"{RAY}/UAVs_Rotor_Micro-Doppler_Feature_Extraction_Using_Integrated_Sensing_and_Communication_Signal_Algorithm_Design_and_Testbed_Evaluation.pdf",
         engine_ko="미사용", target_ko="점산란체 집합 — 동체 RCS 는 표에 적힌 상수",
         route="R5", claimed_ko="실제 5G NR 모노스태틱 테스트베드에서 로터 마이크로도플러 추출",
         gates=G(0, 0, 0, 0),
         quotes=[(3, "the UAV is modeled as a set of point scatterers")]),
    dict(key="mdrt", short="md-rt (ICCT 2025)", short_ko="Li (md-rt)",
         first_author="C. Li", year=2025, venue_ko="IEEE ICCT", venue_en="IEEE ICCT",
         status="published", status_ko="게재",
         locator="pp. 359–364, DOI 10.1109/ICCT67417.2025.11374154",
         venue_evidence="PDF 메타데이터 subject + 본문 쪽번호",
         pdf=f"{RAY}/Micro-Doppler_Signature_Simulation_of_Multirotor_UAVs_Using_Ray_Tracing.pdf",
         engine_ko="직접 돌림 — 스톡 EM 설정, 광선발사기는 개조(구면→원뿔 샘플링)",
         target_ko="Blender 프로펠러 1개(재질 Wood) — 기체 없음",
         route="R6", claimed_ko="스펙트로그램 능선 **위치**가 폐형식 마이크로도플러 식과 일치",
         gates=G(1, 1, 0, 0),
         prongs=dict(P1="예", P2="일부 — 프로펠러 1개, 기체 없음", P3="예 — Sionna RT",
                     P4="아니오 — 자체 해석식 대비 운동학 일치"),
         quotes=[(1, "We propose an improved directional ray-tracing strategy based on Sionna RT, which replaces spherical sampling with conical sampling"),
                 (3, "Propeller material Wood"),
                 (1, "To date, no research has systematically employed ray tracing to model and analyze signal spectrum variations caused by rotational motions of multirotor UAVs")]),
    dict(key="clutter", short="Clutter-Aware (Proc. IEEE 2026)", short_ko="Liu (Clutter-Aware ISAC)",
         first_author="F. Liu", year=2026, venue_ko="Proc. IEEE", venue_en="Proc. IEEE",
         status="published", status_ko="게재",
         locator="vol. 114, no. 1, DOI 10.1109/JPROC.2026.3675476",
         venue_evidence="PDF 메타데이터 subject + p29 러닝풋터",
         pdf=f"{RAY}/Clutter-Aware_Integrated_Sensing_and_Communication_Models_Methods_and_Future_Directions.pdf",
         engine_ko="직접 돌림 — 사이트별 사례연구 1건", target_ko="Blender 로 단순화한 UAV 메쉬를 Sionna XML 로 임포트",
         route="R6", claimed_ko="클러터 분류체계와 억제 도구상자, Sionna RT 장면으로 예시",
         gates=G(1, 1, 0, 0),
         prongs=dict(P1="예", P2="예 — 단순화 UAV 메쉬", P3="예 — Sionna RT",
                     P4="아니오 — 41쪽에 `validat*` 0회, dBsm 0회"),
         quotes=[(23, "The ToI and UAVs are modeled as simplified 3-D mesh objects imported into Sionna"),
                 (23, "which keeps the ray-tracing scene lightweight while enabling flexible material assignment"),
                 (6, "capture the combined effects of RCS, path loss, and multipath-induced phase variations")]),
    dict(key="zig_c", short="Ziganshin conf. (EuCAP 2025)", short_ko="Ziganshin (학회판)",
         first_author="A. Ziganshin", year=2025, venue_ko="EuCAP", venue_en="EuCAP",
         status="published", status_ko="게재",
         locator="DOI 10.23919/EuCAP63536.2025.10999367",
         venue_evidence="PDF 메타데이터 subject + 전 쪽 Xplore 스탬프",
         pdf=f"{RAY}/Ray-Based_Simulation_of_Multistatic_Scattering_from_Target_Objects_in_ISAC.pdf",
         engine_ko="직접 돌림 — RT+UTD+정점회절로 확장", target_ko="단순화 차량(PEC) 3.3×2.1×1.7 m · 구",
         route="R7", claimed_ko="Sionna 기반 확장 솔버가 낸 패싯 차량의 RCS(dBsm), FEKO 대조",
         gates=G(1, 0, 1, 1),
         prongs=dict(P1="예", P2="아니오 — 차량", P3="예 — Sionna RT 확장",
                     P4="예 — FEKO MLFMM·PO 대조"),
         quotes=[(5, "The proposed solution can also be applied to compute scattering from other objects, such as drones, humans, and micro-Doppler effects"),
                 (5, "RCS of the simplified car"),
                 (3, "EM simulation is performed with the commercial FEKO package")]),
    dict(key="hoydis", short="Hoydis (TMLCN 2024)", short_ko="Hoydis (미분가능 RT)",
         first_author="J. Hoydis", year=2024, venue_ko="IEEE TMLCN", venue_en="IEEE TMLCN",
         status="published", status_ko="게재", locator="DOI 10.1109/TMLCN.2024.3474639",
         venue_evidence="PDF 메타데이터 + 본문", pdf=f"{ARC}/2311.18558__hoydis_learning-radio-env.pdf",
         engine_ko="직접 돌림 — 엔진 자체가 연구 대상", target_ko="표적 없음 — 환경 재질을 실측에 맞춘다",
         route="R6", claimed_ko="실내 사운더 실측에 맞춰 재질·산란을 경사기반으로 교정",
         gates=G(1, 0, 0, 0),
         quotes=[(1, "determining material characteristics requires precise calibration using channel measurements")]),
    dict(key="zig_j", short="Ziganshin jour. (preprint)", short_ko="Ziganshin (저널판)",
         first_author="A. Ziganshin", year=2026, venue_ko="IEEE OJAP 투고",
         venue_en="arXiv (OJAP submitted)", status="preprint", status_ko="프리프린트",
         locator="arXiv:2604.05991v2 (2026-07-02)",
         venue_evidence="p1 교신저자 각주 'submitted' + arXiv 스탬프",
         pdf=f"{ARC}/2604.05991__ziganshin_curved-body-scattering.pdf",
         engine_ko="직접 돌림 — Sionna-RT v0.19 를 개조", target_ko="구·원기둥·PEC 차량의 패싯 메쉬",
         route="R7", claimed_ko="근거리 산란전계 |E| 와 패싯 이산화 품질지표 E²/(Rλ)",
         gates=G(1, 0, 1, 0),
         prongs=dict(P1="아니오 — 프리프린트", P2="아니오 — 차량", P3="예 — Sionna-RT 확장",
                     P4="예, 단 저자가 정성적 검증이라 명시"),
         quotes=[(1, "This is a preprint version of a manuscript submitted to the IEEE Open Journal of Antennas and Propagation"),
                 (3, "Sionna-RT (v0.19) [19] was used as a basic RT framework"),
                 (7, "The comparison should be interpreted as a qualitative validation rather than an attempt to exactly reproduce the measurements")]),
    dict(key="montaner", short="Montaner (preprint)", short_ko="Montaner (결정론 ISAC)",
         first_author="J. Montaner", year=2026, venue_ko="arXiv", venue_en="arXiv",
         status="preprint", status_ko="프리프린트 (EuCAP 2026 채택 주장은 PDF 밖 · 미검증)",
         locator="arXiv:2603.28736v1", venue_evidence="p1 arXiv 스탬프 · 'accepted' 0회",
         pdf=f"{RAY}/Deterministic Modeling of Dynamic ISAC Channels in RF Digital Twin Environments.pdf",
         engine_ko="직접 돌림", target_ko="장면 메쉬 — 이동표적 산란은 확산계수 하나로",
         route="R6", claimed_ko="77–81 GHz 사운더와 RT 의 지연-도플러 구조 일치",
         gates=G(1, 0, 0, 0),
         quotes=[(2, "Purely specular RT on low-polygon meshes underestimates power at mmWave/sub-THz due to electromagnetic roughness; direct meshing at O(λ/10) is infeasible at E-band"),
                 (1, "This paper instantiates and validates a calibrated RT-based RF-DT for ISAC at 77–81 GHz")]),
    dict(key="lambda", short="LAMBDA (preprint)", short_ko="LAMBDA (데이터셋)",
         first_author="LAMBDA", year=2026, venue_ko="arXiv", venue_en="arXiv",
         status="preprint", status_ko="프리프린트", locator="arXiv:2607.03826v1 (2026-07-04)",
         venue_evidence="p1 arXiv 스탬프", pdf=f"{ARC}/2607.03826__lambda-uav-dataset.pdf",
         engine_ko="직접 돌림 — 전파 경로만", target_ko="UAV 메쉬 — σ 는 엔진 밖 CADFEKO 에서 푼다",
         route="R3", claimed_ko="RF 분기를 가진 대규모 정렬 멀티모달 UAV 데이터셋",
         gates=G(1, 1, 0, 0),
         prongs=dict(P1="아니오 — 프리프린트", P2="예 — AirSim UAV 메쉬",
                     P3="아니오 — σ 는 CADFEKO", P4="아니오 — 진폭 대조 없음"),
         quotes=[(3, "CADFEKO [28] for UAV radar cross-section (RCS) modeling"),
                 (7, "the RCS term is obtained from CADFEKO simulations of the AirSim UAV model and queried according to the UAV attitude")]),
    dict(key="dmsnet", short="DMSNet (preprint)", short_ko="DMSNet (다중밴드)",
         first_author="H. Liu", year=2026, venue_ko="arXiv", venue_en="arXiv",
         status="preprint", status_ko="프리프린트", locator="arXiv:2607.17655v1",
         venue_evidence="p1 arXiv 스탬프", pdf=f"{ARC}/2607.17655__dmsnet-crossband-multiband-isac.pdf",
         engine_ko="인용만", target_ko="복소 산란계수 ρ 로 표현한 점표적",
         route="R5", claimed_ko="다중밴드 다표적 계수·파라미터 추정, CA-CFAR 베이스라인 포함",
         gates=G(0, 0, 0, 0),
         quotes=[(2, "the corresponding radar cross section (RCS) is denoted by")]),
    dict(key="openisac", short="OpenISAC (preprint)", short_ko="OpenISAC (플랫폼)",
         first_author="OpenISAC", year=2026, venue_ko="arXiv", venue_en="arXiv",
         status="preprint", status_ko="프리프린트", locator="arXiv:2601.03535v2 (2026-07-06)",
         venue_evidence="p1 arXiv 스탬프 · 'IoT-J' 0회",
         pdf=f"{ARC}/2601.03535__openisac.pdf",
         engine_ko="인용만 — Sionna 시뮬레이션 없음", target_ko="실제 하드웨어 — 레이더식의 σ_RCS 한 항",
         route="R5", claimed_ko="실시간 SDR OFDM-ISAC 플랫폼과 거리-도플러 출력",
         gates=G(0, 0, 0, 0),
         quotes=[(4, "For a specific reflection p with radar cross section (RCS)")]),
    dict(key="sagitta", short="SagittaSBR (ICCS 2026 ext.)", short_ko="Sagitta (자체 SBR)",
         first_author="SagittaSBR", year=2026, venue_ko="arXiv", venue_en="arXiv (ICCS 2026 accepted)", status="preprint",
         status_ko="프리프린트 확장판 · 기반판 ICCS 2026 채택 (본문 p1 명시)",
         locator="arXiv:2604.09243v1", venue_evidence="p1 Note 문장",
         pdf=f"{ARC}/2604.09243__sagitta-sbr.pdf",
         engine_ko="Sionna 미사용 — 자체 CUDA/HIP SBR+PO", target_ko="PEC A380 여객기 (80×73×21 m)",
         route="R7", claimed_ko="메쉬에서 낸 모노스태틱 RCS 를 Mie 급수와 교차검증",
         gates=G(0, 0, 1, 1),
         prongs=dict(P1="일부 — 기반판이 ICCS 2026 채택", P2="아니오 — A380 여객기",
                     P3="아니오 — 자체 솔버, Sionna 아님", P4="예 — PEC 구 Mie 대조"),
         quotes=[(1, "This manuscript is an extended version of the paper accepted at the 26th International Conference on Computational Science (ICCS 2026)"),
                 (9, "an A380 aircraft was selected as a primary benchmark"),
                 (8, "we analyzed the computed RCS of a PEC sphere against analytical Mie scattering theory")]),
    dict(key="fwa_cube", short="FWA cube (preprint)", short_ko="Zhang (FWA 협동센싱)",
         first_author="J. Zhang", year=2026, venue_ko="arXiv",
         venue_en="arXiv", status="preprint",
         status_ko="프리프린트 — 본문 p.1 이 부분 채택을 명시 (IEEE ICC Workshops 2026)",
         locator="arXiv:2605.07623", venue_evidence="p.1 본문 문장 'partly accepted by IEEE ICC Workshops 2026'",
         pdf=f"{ARC}/2605.07623__lowalt-cooperative-cube-csi.pdf",
         engine_ko="직접 돌림", target_ko="금속 정육면체 — UAV 를 큐브로 둔다",
         route="R5", claimed_ko="Sionna 기반 UAV 검출에서 정량 검출성능",
         gates=G(1, 0, 0, 0),
         prongs=dict(P1="일부 — 본문이 IEEE ICC Workshops 2026 부분 채택을 적는다", P2="아니오 — 금속 큐브",
                     P3="예 — Sionna RT", P4="아니오"),
         quotes=[(1, "This work has been partly accepted by IEEE ICC Workshops 2026"),
                 (8, "The UAV is modeled as a metallic cube"),
                 (8, "The dataset is generated through ray-tracing, using OpenStreetMap (OSM), Blender, and Sionna RT")]),
    dict(key="greatx", short="Great-X (preprint)", short_ko="Great-X (Unreal ISAC)",
         first_author="K. Huang", year=2025, venue_ko="arXiv", venue_en="arXiv",
         status="preprint", status_ko="프리프린트", locator="arXiv:2507.08716",
         venue_evidence="p1 arXiv", pdf=f"{ARC}/2507.08716__great-x_unreal-isac.pdf",
         engine_ko="Sionna 미사용 — Unreal Engine 렌더러, Sionna 는 비교 기준",
         target_ko="3-D UAV 모델을 Unreal 장면에",
         route="R6", claimed_ko="멀티모달 ISAC 데이터 생성과 미터 단위 측위 오차",
         gates=G(0, 0, 0, 0),
         prongs=dict(P1="아니오 — 프리프린트", P2="예 — 3-D UAV 모델",
                     P3="아니오 — Sionna 계열 엔진 아님", P4="아니오 — RCS·dBsm 0회"),
         quotes=[(5, "Great-X employs an Unreal Engine-based renderer"),
                 (4, "we utilized the Great-X to import a 3D model of a UAV")]),
    dict(key="cellsense", short="CellSense (preprint)", short_ko="CellSense (셀룰러 패시브)",
         first_author="B. Kumar", year=2026, venue_ko="arXiv", venue_en="arXiv",
         status="preprint", status_ko="프리프린트", locator="arXiv:2606.07900",
         venue_evidence="p1 arXiv", pdf=f"{ARC}/2606.07900__cellsense.pdf",
         engine_ko="직접 돌림 + OAI/USRP 실측", target_ko="드론 없음 — 실내 창고·옥외 장면",
         route="R6", claimed_ko="Sionna 링크레벨 + USRP 프로토타입의 클러터 강건 패시브 센싱",
         gates=G(1, 0, 0, 0),
         quotes=[(4, "Site-specific Sionna ray-tracing environments generated in Blender")]),
    dict(key="tgnn", short="Temporal-GNN (preprint)", short_ko="Temporal-GNN (검출·추적)",
         first_author="S. M. Sanaie", year=2026, venue_ko="arXiv", venue_en="arXiv",
         status="preprint", status_ko="프리프린트", locator="arXiv:2604.08306",
         venue_evidence="p1 arXiv", pdf=f"{ARC}/2604.08306__temporal-gnn-isac.pdf",
         engine_ko="직접 돌림", target_ko="점산란체 1개",
         route="R5", claimed_ko="Sionna CIR 위에서 그래프신경망 검출·추적",
         gates=G(1, 0, 0, 0),
         quotes=[(1, "the CIR is generated using the Sionna ray-tracing tool"),
                 (2, "The bi-static RCS relies on the assumption that the target is a point scatterer")]),
]

#: 읽었고 H8 과 무관하다고 판정한 편 — 구멍이 아니라 판정 결과다.
READ_AND_EXCLUDED = [
    dict(pdf="2401.03310__caviar-digital-twin.pdf", why_ko="Sionna+AirSim 탐색구조 — UAV 는 통신 플랫폼, RCS 0회"),
    dict(pdf="2605.13309__simart.pdf", why_ko="ROS/Unreal 공동시뮬 플랫폼 — 표적 산란 없음"),
    dict(pdf="2607.03411__s-icdf.pdf", why_ko="Sionna GNSS 간섭 데이터셋"),
    dict(pdf="2501.17881__rayloc.pdf", why_ko="실내 측위용 SBR — 드론·RCS 없음"),
    dict(pdf="2511.03220__multimodal-wireless.pdf", why_ko="데이터셋 도구"),
    dict(pdf="2606.07328__wu_3gpp-isac-simulator.pdf", why_ko="3GPP ISAC 시뮬레이터 — 표적은 통계모델"),
    dict(pdf="2408.11295__luo_3gpp-bistatic-sensing.pdf", why_ko="3GPP 바이스태틱 — 광선엔진 미사용"),
    dict(pdf="2402.16591__beuster_multisensor-isac-drone.pdf", why_ko="다중센서 드론 실측 — 광선엔진 미사용"),
    dict(pdf="2602.08203__ji_cellular-uav-bistatic.pdf", why_ko="셀룰러 UAV 바이스태틱 해석"),
    dict(pdf="2601.10846__colone_ris-lowrcs-radar.pdf", why_ko="RIS 저RCS 표적 — 드론 메쉬 없음"),
    dict(pdf="2512.24889__he_caf-clutter-suppression.pdf", why_ko="CAF 클러터 억제 신호처리"),
]

# --------------------------------------------------------------------------- #
#  H8 — 네 관문. 하나라도 빠지면 반증이 아니다.
# --------------------------------------------------------------------------- #
H8_PRONGS = [
    ("P1 게재", "동료심사 지면에 실렸다. arXiv 전용 원고는 제외하고, 본문에 명명된 지면 채택을 적은 원고는 포함한다"),
    ("P2 드론 메쉬", "표적이 기체의 3-D 표면 메쉬다. 큐브·점산란체·블레이드 1장·추상 복소계수는 제외한다"),
    ("P3 Sionna 계열 엔진", "산란전계를 미분가능 GPU 광선엔진 **안에서** 계산한다. FEKO·FDTD 로 낸 σ 를 경로에 곱하는 것은 주입이다"),
    ("P4 진폭 검증", "계산한 산란 **진폭**을 측정 또는 기준해와 맞댄다. 도플러 위치·회전주기·능선 모양 일치는 운동학이라 여기 못 든다"),
]

NEAR_MISS = [
    dict(rank=1, paper="Rzewuski (NATO STO 2021)", gap_ko="엔진 한 칸 — 광선엔진 대신 FDTD 로 풀었다",
         why_ko="같은 최종물: WiFi 대역 드론 바이스태틱 σ → 패시브 커버리지 → 실측 검출 50 m"),
    dict(rank=2, paper="Ziganshin 학회판(게재) + 저널판(프리프린트)", gap_ko="표적 종류 하나 — 차량이다",
         why_ko="메쉬 산란을 Sionna 안에서 계산하고 바이스태틱 실측·FEKO MLFMM 과 맞댄다"),
    dict(rank=3, paper="Clutter-Aware ISAC (Proc. IEEE 2026)", gap_ko="검증 한 칸 — 41쪽에 `validat*` 0회, dBsm 0회",
         why_ko="게재본이고 UAV 메쉬가 실제로 Sionna 안에 있다"),
    dict(rank=4, paper="md-rt (IEEE ICCT 2025)", gap_ko="프로펠러 1개, 검증은 운동학",
         why_ko="게재본 · Sionna · 드론 기하 · Sionna RT 정확도 검증을 명시적으로 주장"),
    dict(rank=5, paper="LAMBDA (프리프린트)", gap_ko="엔진 분업 — σ 는 CADFEKO, 경로는 Sionna RT",
         why_ko="커뮤니티가 실제로 쓰는 주입 구조를 가장 깨끗하게 보여준다"),
    dict(rank=6, paper="Great-X (프리프린트)", gap_ko="산란 진폭도 검증도 없고 엔진도 Sionna 계열이 아니다",
         why_ko="GPU 광선 파이프라인 안에 실제 3-D UAV 모델이 들어가 레이더 에코를 낸다"),
    dict(rank=7, paper="FWA 협동센싱 (프리프린트)", gap_ko="표적이 금속 큐브다",
         why_ko="Sionna 기반 UAV 검출에서 정량 검출성능을 낸다"),
]

# --------------------------------------------------------------------------- #
#  §1 엔진 — Sionna RT 1차 사료
# --------------------------------------------------------------------------- #
SIONNA_TR = f"{TASK}/2504.21719__sionna-rt-technical-report-v1.pdf"
SIONNA_FOUND = f"{TASK}/2303.11103__sionna-rt-founding.pdf"


def engine_block() -> dict:
    tr, fd = pages(SIONNA_TR), pages(SIONNA_FOUND)
    joined = " ".join(tr)
    cnt = dict(
        physical_optics=len(re.findall(r"physical optics", joined, re.I)),
        radar_cross_section=len(re.findall(r"\bRCS\b|radar cross[- ]section", joined, re.I)),
        dbsm=len(re.findall(r"dBsm", joined, re.I)),
        induced_current=len(re.findall(r"induced current", joined, re.I)),
        kirchhoff=len(re.findall(r"kirchhoff", joined, re.I)),
        surface_integral=len(re.findall(r"surface integral", joined, re.I)),
        sbr=len(re.findall(r"\bSBR\b", joined)),
        fresnel=len(re.findall(r"fresnel", joined, re.I)),
    )
    return dict(
        technical_report=dict(
            pdf=SIONNA_TR, version="Version 1.2 (2025-11-24)", pages=len(tr),
            filename_trap="아카이브 파일이름은 v1 이지만 내용은 Version 1.2 다",
            term_counts=cnt,
            quotes=[check(SIONNA_TR, 1, "2025-11-24 – Version 1.2"),
                    check(SIONNA_TR, 1, "For CIRs, Sionna RT integrates shooting and bouncing of rays (SBR) with the image method"),
                    check(SIONNA_TR, 9, "Sionna RT currently supports four types of interactions with scene objects"),
                    check(SIONNA_TR, 16, "Sionna RT currently supports only first-order diffraction"),
                    check(SIONNA_TR, 46, "The Fresnel equations provide relationships between the incident, reflected, and refracted field components"),
                    check(SIONNA_TR, 50, "we denote by S2 the fraction of the reflected energy that is diffusely scattered")]),
        founding_paper=dict(
            pdf=SIONNA_FOUND, pages=len(fd),
            describes_version="v0.14 (TensorFlow 시기)",
            use_ko="출처 표기용으로만 인용한다. 솔버 거동은 기술보고서 v1.2 에서 인용한다 — 우리 스택이 2.0.1 이다",
            term_counts=dict(physical_optics=len(re.findall(r"physical optics", " ".join(fd), re.I)),
                             radar_cross_section=len(re.findall(r"\bRCS\b|radar cross[- ]section", " ".join(fd), re.I)),
                             sbr=len(re.findall(r"\bSBR\b", " ".join(fd)))),
            quotes=[check(SIONNA_FOUND, 1, "Since release v0.14 it integrates a differentiable ray tracer")]),
        interactions_ko=["정반사 R — 프레넬 계수 곱(식 127–130, p.46)",
                         "확산반사 S — 산란계수 S 와 정규화 산란패턴(p.50–52)",
                         "굴절 T — 슬래브 투과",
                         "회절 D — 1차까지"],
        scope_guard_ko=("SBR 은 기술보고서에 %d 회 나온다 — 광선을 쏘고 튕기는 것은 있다. "
                        "면적분과 RCS 출력이 그 위에 얹히는 층이다."),
        precise_wording_en="Sionna RT's stock solver: SBR + image method, four interactions, "
                           "empirical diffuse scattering pattern. No PO surface integral, no RCS output.",
    )


def _census() -> dict:
    return json.load(open(os.path.join(ROOT, "outputs", "prior_census.json"), encoding="utf-8"))


def sionna_api_block() -> dict:
    """설치본 Sionna 의 공개 이름 개수 — `benchmark/prior_census.py` 가 임포트해서 센 값."""
    a = _census()["sionna_api"]
    return dict(version=a["version"], rt_public_names=a["rt_public_names"],
                rcs_api_names=a["rcs_api_names"], scattering_api_names=a["scattering_api_names"],
                scattering_api_list=a["scattering_api_list"],
                measured_by="benchmark/prior_census.py — 설치된 sionna.rt 를 직접 임포트해 이름을 센다",
                note_ko="RCS 를 계산하는 공개 이름은 0개이고, ScatteringPattern 계열은 확산반사의 각분포 함수다")


def bands_block() -> dict:
    c = _census()["context"]
    return dict(bands_hz=c["bands_hz"], lambda_cm=c["lambda_cm"],
                drone_diag_m=0.40,
                note_ko="5G 3.5 GHz 에서 λ 는 8.6 cm — 대각 40 cm 급 드론은 파장의 다섯 배 규모 유한 물체다")


# --------------------------------------------------------------------------- #
#  §4 앵커 — Das · Yuan · Zhang, 그리고 규약 갈림
# --------------------------------------------------------------------------- #
def anchor_block() -> dict:
    bands = {"LTE 1.843 GHz": 1.843, "5G 3.5 GHz": 3.5, "WiFi 5.21 GHz": 5.21}
    das_a, das_b = 0.21, -19.19
    rc = json.load(open(os.path.join(ROOT, "outputs", "rcs_anchor.json"), encoding="utf-8"))
    sa = json.load(open(os.path.join(ROOT, "outputs", "sigma_anchor.json"), encoding="utf-8"))
    off = sa["statistic_resolution"]["reconcile"]["by_kind"]["exponential"]["offset_db"]
    pub = {k: das_a * f + das_b for k, f in bands.items()}
    return dict(
        das=dict(pdf=next(p["pdf"] for p in PAPERS if p["key"] == "das"),
                 venue="IEEE WCL vol.15 pp.3731–3735 (2026), DOI 10.1109/LWC.2026.3705634",
                 platform="DJI Phantom 3 (Table I 35 cm × 20 cm)",
                 band_ghz=[1.8, 18.2], mu_a_db_per_ghz=das_a, mu_b_dbsm=das_b,
                 statistic_ko="선형 방위평균 — §III-1 이 σ_m = (1/K)Σσ(φ_k) 로 정의한다",
                 statistic_quote=check(next(p["pdf"] for p in PAPERS if p["key"] == "das"),
                                       2, "The mean RCS is defined as"),
                 polarisation_ko="Phantom 3 에 대해 Das 는 편파를 적지 않는다. VV 는 Yuan §II-A 에서 인용한다",
                 provenance_ko="Das 는 Phantom 3 자료를 자신의 참고문헌 [7] (Wang 등, China Communications) 에 귀속한다",
                 bistatic_ko="Phantom 3 의 바이스태틱 7열은 기울기와 ε 가 같고 절편만 총 0.63 dB 움직인다",
                 table3_source="outputs/prior_settled_anchor.json (650 dpi 렌더 판독, 56칸 일치)"),
        yuan=dict(pdf=next(p["pdf"] for p in PAPERS if p["key"] == "yuan"),
                  venue="EuCAP 2025, DOI 10.23919/EuCAP63536.2025.10999912",
                  platform="DJI Phantom 3 (수평 대각 35 cm, 높이 20 cm) — Das 와 같은 기체",
                  slopes_db_per_ghz={"theta90": 0.315, "theta0": 0.231, "theta180": 0.175},
                  polarisation="VV (§II-A)",
                  statistic_ko="Yuan 은 평균의 정의를 적지 않는다 — '선형 방위평균' 은 우리 추론이다"),
        zhang=dict(pdf=next(p["pdf"] for p in PAPERS if p["key"] == "zhang"),
                   venue="IEEE JSAC vol.44 pp.702–716 (2026), DOI 10.1109/JSAC.2025.3608732",
                   decomposition="σ(f,φ) = A(f) × B1(f,φ) × B2, 고도각 90° 고정",
                   a_slope_db_per_ghz=0.31, fit_rmse_db=rc["literature"]["fit_rmse_db"]["AAV"],
                   fit_band_ghz=[10, 36],
                   statistic_ko="A(f) 는 전 각도 σ 의 선형평균 — Das §III-1 과 같은 통계다",
                   table_v_note="Table V 는 게재본에서 텍스트 추출이 안 된다. arXiv:2505.20673 p.11 로 인용한다"),
        level_convention_split=dict(
            das_published_dbsm=pub,
            pipeline_offset_db=off,
            pipeline_dbsm={k: v + off for k, v in pub.items()},
            rcs_anchor_json=rc["literature"]["mu_eps"]["multiband_phantom3"]["mu_at_bands"],
            sigma_anchor_statistic=sa["sources"]["anchors"]["das_phantom3_mono"]["statistic"],
            status="EVIDENCE_SPLIT",
            what_decides_ko="Das §III-1 의 정의를 그대로 쓰면 인쇄값이고, 잔차 최소화 변환을 쓰면 +2.51 dB 다. "
                            "두 파일이 서로 다른 쪽을 쓴다",
            where_ko="02편 §4 에서 하나로 맞춘다"),
        slope_compare_db_per_ghz=dict(das_phantom3=das_a, yuan_theta90=0.315, zhang_aav=0.31),
    )


# --------------------------------------------------------------------------- #
#  정산된 모순 — 어디서 무엇이 뒤집혔나 (다음 라운드가 diff 로 본다)
# --------------------------------------------------------------------------- #
CONTRADICTIONS = [
    dict(id="X-C1", verdict="REFUTED", topic_ko="Clutter-Aware ISAC 가 Sionna 를 쓰는가",
         settled_ko="쓴다. UAV 메쉬를 Blender 로 단순화해 Sionna XML 로 임포트한다(p.23). "
                    "'Sionna·광선추적·메쉬를 전혀 쓰지 않는다' 는 거짓이다",
         fixed_in=["prior_work/src/pw04_data.py", "prior_work/pw04_rcs_solution_by_target.ipynb"]),
    dict(id="X-C2", verdict="REFUTED (산문) / CONFIRMED (기계 계수)",
         topic_ko="Clutter-Aware 의 CFAR 어휘",
         settled_ko="CFAR 4회 · false alarm 3회는 실재한다. ROC · detection probability · P_FA 값 · "
                    "ECA/CLEAN/CAF 는 0회다",
         fixed_in=["docs/DRONE_ISAC_PRIOR_READING.md"]),
    dict(id="X-C4", verdict="REFUTED (전제)", topic_ko="LAMBDA 의 CADFEKO 인용",
         settled_ko="경쟁하던 두 인용이 **둘 다** 실재한다(p.3 파이프라인, p.7 레이더 합성). "
                    "'원문에 미명시' 가 거짓이다",
         fixed_in=["prior_work/sionna_sensing_survey.md"]),
    dict(id="X-C5", verdict="REFUTED", topic_ko="Ziganshin 저널판의 게재상태",
         settled_ko="프리프린트다. p1 각주가 'submitted to the IEEE Open Journal of Antennas and "
                    "Propagation' 이고 OJAP DOI 문자열은 0회다",
         fixed_in=["prior_work/sionna_sensing_survey.md"]),
    dict(id="X-C6", verdict="SETTLED", topic_ko="'drones, humans, micro-Doppler' 향후과제 문장의 판",
         settled_ko="학회판(EuCAP 2025) p.5 결론에만 있다. 저널판에는 'drone' 이 참고문헌 제목 안에만 나온다. "
                    "우리 위치 문장은 **동료심사된** 문장 뒤에 선다",
         fixed_in=["docs/DRONE_ISAC_PRIOR_READING.md", "src/make_report01_prior.py"]),
    dict(id="X-C7", verdict="REFUTED", topic_ko="OpenISAC 의 게재상태",
         settled_ko="프리프린트(arXiv:2601.03535v2)다. 'IoT-J' 문자열 0회",
         fixed_in=["prior_work/sionna_sensing_survey.md"]),
    dict(id="X-C9", verdict="REFUTED", topic_ko="Montaner 의 EuCAP 2026 채택",
         settled_ko="PDF 안에 채택 문장이 없다('accepted' 0회). 인용마다 '주장은 PDF 밖, 미검증' 을 붙인다",
         fixed_in=["prior_work/outputs/prior_work.json"]),
    dict(id="X-C10", verdict="VERIFIED — 인용이 범위를 잃었다", topic_ko="Montaner 의 λ/10 문장",
         settled_ko="원문은 두 절 모두에 대역 한정을 달고 논문 전체가 77–81 GHz 다. "
                    "3.5 GHz 에서 λ/10 = 8.6 mm 라 그 논거는 우리 대역에서 뒤집힌다",
         fixed_in=["prior_work/outputs/prior_work.json"]),
    dict(id="X-C13", verdict="CLOSED — [W]→[P] 승격", topic_ko="Sionna RT 1차 사료",
         settled_ko="두 PDF 모두 디스크에 있었다. 기술보고서 59쪽에 physical optics · radar cross section · "
                    "dBsm 이 0회이고, 유일한 'surface integral' 은 라디오맵 면적분용 참고문헌이다",
         fixed_in=["docs/PRIOR_WORK_COMPARISON.md", "prior_work/outputs/prior_work.json"]),
    dict(id="X-C17", verdict="UNVERIFIED — 원문 부재", topic_ko="Wypich & Zielinski ECA→CFAR 선례",
         settled_ko="/data/public 전체 268 PDF 에 파일이 없다. 별표를 떼고 인용마다 "
                    "'원문 미확보 · 표적은 차량(5.8 GHz)' 을 붙인다",
         fixed_in=["prior_work/outputs/prior_work.json", "prior_work/src/make_pw01.py"]),
    dict(id="X-C18", verdict="REFUTED", topic_ko="Ezuma/Guvenc RCS 앵커의 VERIFIED 표시",
         settled_ko="세 행 모두 디스크에 PDF 가 없다. Mavic Pro 두 행은 노트조차 없다",
         fixed_in=["prior_work/outputs/prior_work.json"]),
    dict(id="H1", verdict="VERIFIED 3/4", topic_ko="Clutter-Aware 가 스톡 프레넬을 받아들인다",
         settled_ko="메쉬 임포트 · 'lightweight' 동기 · 산란 감사 없음은 확인됐다. "
                    "'스톡 프레넬' 은 우리 추론이다 — 논문에 'Fresnel' 0회. "
                    "'표면 모델을 적지도 감사하지도 않는다' 가 지지되는 형태다",
         fixed_in=["docs/DRONE_ISAC_PRIOR_READING.md"]),
    dict(id="H6", verdict="REFUTED ('스톡' 절)", topic_ko="md-rt 가 스톡 Sionna 다",
         settled_ko="EM 설정은 스톡이지만 광선발사기를 개조했다 — 기여 2번이 구면 샘플링을 원뿔 샘플링으로 "
                    "바꾼 것이다",
         fixed_in=["prior_work/src/pw04_data.py", "src/make_report01_prior.py"]),
    dict(id="H7", verdict="REFUTED (쓰인 대로)", topic_ko="Ziganshin·Sagitta·LAMBDA·OpenISAC 은 프리프린트뿐",
         settled_ko="Ziganshin 학회판은 EuCAP 2025 게재본이고, Sagitta 는 ICCS 2026 채택본의 확장판이다. "
                    "프리프린트만인 것은 Ziganshin 저널판 · LAMBDA · OpenISAC 이다",
         fixed_in=["prior_work/sionna_sensing_survey.md"]),
    dict(id="N-01", verdict="REFUTED (이번 라운드 신규)", topic_ko="FWA 협동센싱(2605.07623)의 게재 주장 위치",
         settled_ko="채택 문장이 **PDF 본문 p.1 에 있다** — \"This work has been partly accepted by IEEE ICC "
                    "Workshops 2026\". '아카이브 분류일 뿐 PDF 내 미확인' 은 거짓이다",
         fixed_in=["prior_work/src/build_prior_survey.py", "outputs/prior_work_survey.json"]),
    dict(id="N-02", verdict="REFUTED (이번 라운드 신규)", topic_ko="CellSense 의 MILCOM 2026 귀속",
         settled_ko="PDF 안 `MILCOM` 3회는 전부 참고문헌 [5](2024년 타 논문)이고, `accepted`·`submitted` 는 "
                    "0회다. CellSense 는 프리프린트로 센다",
         fixed_in=["prior_work/src/pw04_data.py", "prior_work/pw04_rcs_solution_by_target.ipynb"]),
    dict(id="H9", verdict="VERIFIED", topic_ko="OpenISAC 에 CFAR·false alarm·검출확률이 0회",
         settled_ko="세 정규식 모두 0. 게다가 Sionna 시뮬레이션 자체를 돌리지 않는다(언급 4회, 관련연구)",
         fixed_in=["prior_work/sionna_sensing_survey.md"]),
]

# --------------------------------------------------------------------------- #
#  그림 — 글자는 전부 영어(하우스 규약)
# --------------------------------------------------------------------------- #
CPUB, CPRE, CACC = "#1f6fb4", "#c26a1f", "#59a14f"
plt.rcParams.update({"font.size": 9, "axes.grid": True, "grid.alpha": .25,
                     "figure.dpi": 150, "savefig.bbox": "tight"})


def fig_funnel(D, path):
    stages = ["Adjudicated from full text", "G1  runs a Sionna-class ray engine",
              "G2  + drone geometry inside it", "G3  + scattering computed on that mesh",
              "G4  + absolute RCS in dBsm"]
    keys = ["in_survey", "g1_engine", "g2_drone_mesh", "g3_mesh_scattering", "g4_dbsm"]
    pub = [D["funnel"]["published"][k] for k in keys]
    pre = [D["funnel"]["preprint"][k] for k in keys]
    y = np.arange(len(stages))[::-1]
    fig, ax = plt.subplots(figsize=(7.4, 3.2))
    ax.barh(y, pub, color=CPUB, label="Peer-reviewed / published")
    ax.barh(y, pre, left=pub, color=CPRE, label="Preprint only")
    for i, (a, b) in enumerate(zip(pub, pre)):
        ax.text(a + b + .25, y[i], f"{a + b}   ({a} published)", va="center", fontsize=8.5)
    ax.set_yticks(y, stages, fontsize=8.5)
    ax.set_xlabel("Number of papers")
    ax.set_xlim(0, len(D["papers"]) + 6)
    ax.set_title("Who computes a drone's scattering inside the ray engine?")
    ax.legend(loc="lower right", fontsize=8, framealpha=.95)
    ax.grid(axis="y", visible=False)
    fig.savefig(path)
    plt.close(fig)


def fig_prongs(D, path):
    rows = [p for p in D["papers"] if p.get("prongs")]
    rows.sort(key=lambda q: q["short"])
    cols = ["P1 published", "P2 drone mesh", "P3 Sionna-class engine", "P4 validated amplitude"]
    score = {"예": (1.0, "yes"), "일부": (.5, "partial"),
             "미검증": (.5, "unverified"), "아니오": (0.0, "no")}

    def val(s):
        head = str(s).split("—")[0].strip().split()[0]
        return score.get(head, (.5, "partial"))
    M = np.array([[val(p["prongs"][k])[0] for k in ("P1", "P2", "P3", "P4")] for p in rows])
    L = [[val(p["prongs"][k])[1] for k in ("P1", "P2", "P3", "P4")] for p in rows]
    fig, ax = plt.subplots(figsize=(7.4, 3.6))
    ax.imshow(M, cmap=matplotlib.colors.ListedColormap(["#f2f2f2", "#f0c98a", CPUB]),
              vmin=0, vmax=1, aspect="auto")
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            ax.text(j, i, L[i][j], ha="center", va="center", fontsize=7.5,
                    color="white" if M[i, j] == 1 else "#333")
    ax.set_xticks(range(len(cols)), cols, fontsize=8)
    ax.set_yticks(range(len(rows)), [p["short"] for p in rows], fontsize=8)
    ax.set_xticks(np.arange(-.5, len(cols), 1), minor=True)
    ax.set_yticks(np.arange(-.5, len(rows), 1), minor=True)
    ax.grid(which="minor", color="w", lw=1.4)
    ax.grid(which="major", visible=False)
    ax.tick_params(which="minor", length=0)
    ax.set_title("H8 scorecard: every candidate fails at least one prong")
    fig.savefig(path)
    plt.close(fig)


def fig_routes(D, path):
    order = list(ROUTES)
    cnt = [D["route_counts"][r]["papers"] for r in order]
    pub = [D["route_counts"][r]["published"] for r in order]
    y = np.arange(len(order))[::-1]
    fig, ax = plt.subplots(figsize=(7.4, 3.4))
    ax.barh(y, pub, color=CPUB, label="Peer-reviewed / published")
    ax.barh(y, [c - p for c, p in zip(cnt, pub)], left=pub, color=CPRE, label="Preprint only")
    for i, r in enumerate(order):
        ax.text(cnt[i] + .12, y[i], D["routes"][r]["label_en"], va="center", fontsize=8)
    ax.set_yticks(y, order, fontsize=9)
    ax.set_xlim(0, max(cnt) + 4.2)
    ax.set_xlabel("Number of papers")
    ax.set_title("Where each paper got its target signature")
    ax.legend(loc="lower right", fontsize=8, framealpha=.95)
    ax.grid(axis="y", visible=False)
    fig.savefig(path)
    plt.close(fig)


def fig_dbsm(D, path):
    ps = sorted(D["papers"], key=lambda q: (-q["terms"]["dbsm"], q["short"]))
    v = [q["terms"]["dbsm"] for q in ps]
    col = [CPUB if q["gates"]["g1_engine"] else CACC for q in ps]
    fig, ax = plt.subplots(figsize=(7.4, 3.4))
    ax.bar(range(len(ps)), v, color=col)
    ax.set_xticks(range(len(ps)), [q["short"].split(" (")[0] for q in ps],
                  rotation=40, ha="right", fontsize=7.5)
    ax.set_ylabel('Occurrences of "dBsm" in full text')
    ax.set_title("Absolute RCS is printed outside the ray engine")
    h = [plt.Rectangle((0, 0), 1, 1, color=CPUB), plt.Rectangle((0, 0), 1, 1, color=CACC)]
    ax.legend(h, ["Runs a Sionna-class ray engine", "Does not"], fontsize=8)
    ax.grid(axis="x", visible=False)
    fig.savefig(path)
    plt.close(fig)


# --------------------------------------------------------------------------- #
def build() -> dict:
    t0 = datetime.now()
    papers, nq = [], 0
    for p in PAPERS:
        q = [check(p["pdf"], pg, tx) for pg, tx in p["quotes"]]
        nq += len(q)
        row = {k: v for k, v in p.items() if k != "quotes"}
        row["pages"] = len(pages(p["pdf"]))
        row["terms"] = terms(p["pdf"])
        row["route_ko"] = ROUTES[p["route"]]["label_ko"]
        row["route_tag"] = f'{p["route"]} · {ROUTES[p["route"]]["short_ko"]}'
        row["bought_ko"] = ROUTES[p["route"]]["bought_ko"]
        row["venue_status_ko"] = f"{p['venue_ko']} {p['year']}"
        row["quotes"] = q
        papers.append(row)

    def cnt(sel):
        keys = ["in_survey", "g1_engine", "g2_drone_mesh", "g3_mesh_scattering", "g4_dbsm"]
        S = [q for q in papers if sel(q)]
        out = {"in_survey": len(S)}
        alive = S
        for k in keys[1:]:
            alive = [q for q in alive if q["gates"][k]]
            out[k] = len(alive)
        return out

    funnel = dict(all=cnt(lambda q: True),
                  published=cnt(lambda q: q["status"] == "published"),
                  preprint=cnt(lambda q: q["status"] == "preprint"))
    route_counts = {r: dict(papers=sum(1 for q in papers if q["route"] == r),
                            published=sum(1 for q in papers if q["route"] == r
                                          and q["status"] == "published"),
                            label_ko=ROUTES[r]["label_ko"], bought_ko=ROUTES[r]["bought_ko"],
                            members=[q["short_ko"] for q in papers if q["route"] == r])
                    for r in ROUTES}

    counts = dict(
        papers=len(papers),
        published=sum(1 for q in papers if q["status"] == "published"),
        preprint=sum(1 for q in papers if q["status"] == "preprint"),
        added_since_census=sum(1 for q in papers
                               if q["key"] in ("rzewuski", "fwa_cube", "greatx", "cellsense", "tgnn")),
        quotes_verified=nq,
        pages_total=sum(q["pages"] for q in papers),
        runs_engine=sum(1 for q in papers if q["gates"]["g1_engine"]),
        drone_mesh_in_engine=sum(1 for q in papers if q["gates"]["g2_drone_mesh"]),
        mesh_scattering_in_engine=funnel["all"]["g3_mesh_scattering"],
        prints_dbsm=sum(1 for q in papers if q["terms"]["dbsm"] > 0),
        prints_dbsm_and_runs_engine=sum(1 for q in papers if q["terms"]["dbsm"] > 0
                                        and q["gates"]["g1_engine"]),
        zero_cfar_and_false_alarm=sum(1 for q in papers if q["terms"]["cfar"] == 0
                                      and q["terms"]["false_alarm"] == 0),
        read_and_excluded=len(READ_AND_EXCLUDED),
    )

    eng = engine_block()
    eng["scope_guard_ko"] = eng["scope_guard_ko"] % eng["technical_report"]["term_counts"]["sbr"]

    D = dict(
        meta=dict(
            generated=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            producer="prior_work/src/build_prior_survey.py",
            tool=f"PyMuPDF {fitz.__doc__.split(':')[0].split()[-1]}"
            if fitz.__doc__ else "PyMuPDF",
            archives=[ARC, TASK, PASSIVE],
            rule="사실 한 줄 = (PDF 경로 · 판 · 축자 문장). 셋 중 하나라도 없으면 UNVERIFIED.",
            settled_from=["outputs/prior_settled_h8.json", "outputs/prior_settled_sionna.json",
                          "outputs/prior_settled_ziganshin.json",
                          "outputs/prior_settled_anchor.json"],
            supersedes="outputs/prior_census.json (16편) — 5편 추가, 판정 4건 정정",
            corpus_swept_pdfs=178,
        ),
        counts=counts, funnel=funnel, gates=dict(
            g1_engine="이 논문이 Sionna 계열 광선엔진을 직접 돌린다",
            g2_drone_mesh="그 엔진 안의 표적이 드론 기하(메쉬)다",
            g3_mesh_scattering="그 메쉬에서 산란 진폭을 계산한다",
            g4_dbsm="결과를 절대 RCS(dBsm)로 보고한다"),
        papers=papers, routes=ROUTES, route_counts=route_counts,
        read_and_excluded=READ_AND_EXCLUDED,
        h8=dict(
            claim_ko="드론 메쉬에서 계산한 산란 서명을 Sionna 계열 엔진 안에서 검증한 **게재** 논문은 0편이다.",
            verdict="SURVIVES",
            verdict_ko="살아남았다 — 네 관문을 동시에 통과한 편이 0편이다.",
            prongs=[dict(prong=a, test_ko=b) for a, b in H8_PRONGS],
            n_candidates_adjudicated=sum(1 for q in papers if q.get("prongs")),
            corpus_ko="아카이브 두 곳 178편 + 패시브레이더 코퍼스 21편을 낱말 대조했다",
            qualification_1=dict(
                id="H8-Q1", pdf=next(p["pdf"] for p in PAPERS if p["key"] == "rzewuski"),
                text_ko="'WiFi 패시브용 드론 바이스태틱 RCS 를 아무도 낸 적 없다' 로 바꿔 말하면 거짓이다. "
                        "Rzewuski 등(NATO STO, 2021)이 FDTD 로 그 값을 냈고 실측 검출까지 닫았다. "
                        "우리 새로움은 **엔진과 파이프라인**에 있다."),
            qualification_2=dict(
                id="H8-Q2",
                text_ko="'게재' 가 이 주장을 떠받친다. 프리프린트를 넣으면 간격이 이음매로 좁아진다 — "
                        "LAMBDA 는 UAV RCS 를 Sionna RT 경로와 한 파이프라인에 이미 태웠고, "
                        "Ziganshin 저널판은 메쉬 산란을 Sionna 안에서 실측과 맞댔다."),
            near_miss=NEAR_MISS,
        ),
        sionna_api=sionna_api_block(), bands=bands_block(),
        engine=eng, anchors=anchor_block(), contradictions=CONTRADICTIONS,
        figures=dict(funnel="outputs/figures/report01_survey_funnel.png",
                     prongs="outputs/figures/report01_survey_h8_prongs.png",
                     routes="outputs/figures/report01_survey_routes.png",
                     dbsm="outputs/figures/report01_survey_dbsm.png"),
    )
    os.makedirs(FIGDIR, exist_ok=True)
    fig_funnel(D, os.path.join(ROOT, D["figures"]["funnel"]))
    fig_prongs(D, os.path.join(ROOT, D["figures"]["prongs"]))
    fig_routes(D, os.path.join(ROOT, D["figures"]["routes"]))
    fig_dbsm(D, os.path.join(ROOT, D["figures"]["dbsm"]))
    D["meta"]["runtime_s"] = (datetime.now() - t0).total_seconds()
    return D


def main() -> int:
    D = build()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(D, f, ensure_ascii=False, indent=1)
    c = D["counts"]
    print(f"✅ {os.path.relpath(OUT, ROOT)}")
    print(f"   논문 {c['papers']}편 (게재 {c['published']} · 프리프린트 {c['preprint']}) · "
          f"축자 인용 {c['quotes_verified']}건 PDF 대조 통과")
    print(f"   관문: G1 {D['funnel']['all']['g1_engine']} → G2 {D['funnel']['all']['g2_drone_mesh']} "
          f"→ G3 {D['funnel']['all']['g3_mesh_scattering']} → G4 {D['funnel']['all']['g4_dbsm']}")
    print(f"   H8: {D['h8']['verdict']} · 후보 {D['h8']['n_candidates_adjudicated']}편 판정")
    print(f"   {D['meta']['runtime_s']:.1f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
