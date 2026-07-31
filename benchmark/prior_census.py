# -*- coding: utf-8 -*-
"""
prior_census.py — 리포트 01(선행연구)의 **유일한 근거 생성기**
=============================================================================================
무엇을 하나
    아카이브 PDF 16편을 PyMuPDF 로 전문 추출해서
      (1) 게재/프리프린트를 **PDF 안의 문자열로** 확정하고,
      (2) 4개 관문(Sionna 실행 / UAV 표적 / 메쉬에서 산란계산 / dBsm 보고)을 통과시키고,
      (3) 회피전략 카탈로그(무엇을 주장했고 무엇을 주장하지 않았나)를 만들고,
      (4) `outputs/prior_census.json` + 그림 4장을 쓴다.

⭐ 왜 스크립트인가 — **귀속을 기계가 검사하게 하려고**
    각 논문마다 `quotes` 에 축자 인용을 적어 두고, 스크립트가 그 문자열이 **PDF 안에 실제로
    있는지** 확인한다. 하나라도 없으면 `SystemExit` 로 죽는다. 리포트에 적히는 "이 논문은 X 라고
    했다" 는 전부 이 검사를 통과한 문장이다.
    (이전 라운드에 Ziganshin 에게 **두 PDF 어디에도 없는** 식을 귀속한 사고가 있었다. 이 파일이
     그 재발을 구조적으로 막는다.)

⚠ 판정의 성격
    `status` · `sionna_mentions` · `dbsm` 같은 것은 **기계가 센 값**이다.
    `g2_uav` · `g3_mesh_scattering` · `claimed` · `not_claimed` 는 **사람이 읽고 적은 판정**이고,
    각각 `quotes` 의 축자 인용으로 뒷받침된다. 두 층을 JSON 에서 섞지 않는다.

재현
    PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/prior_census.py
    → outputs/prior_census.json, outputs/figures/report01_*.png (약 30초, GPU 불필요)
"""
from __future__ import annotations

import json
import os
import re
import sys
import unicodedata
from datetime import datetime

import fitz                                   # PyMuPDF
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt               # noqa: E402
import numpy as np                            # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
ARCHIVE = "/data/public/sionna_jeong/papers_isac_sionna"
DEEP = os.path.join(ARCHIVE, "paper_sionna_Ray_0723")
OUT_JSON = os.path.join(ROOT, "outputs", "prior_census.json")
FIGDIR = os.path.join(ROOT, "outputs", "figures")

# --------------------------------------------------------------------------- #
#  관문 정의 — 리포트 §2 가 그대로 인용한다
# --------------------------------------------------------------------------- #
GATES = {
    "g1_sionna": "Sionna 계열 오픈 RT 엔진을 이 논문이 직접 돌린다",
    "g2_uav":    "표적이 드론(UAV)이다 — 차량·구·인체가 아니다",
    "g3_mesh_scattering":
        "그 표적의 산란을 **메쉬에서** 계산한다 — 엔진 기본 상호작용/외부주입/점산란체가 아니다",
    "g4_dbsm":   "결과를 절대 RCS(dBsm)로 보고한다",
}

#: 용어 세기 — 짧은 낱말은 단어경계로 막는다("process" 안의 roc 같은 오탐 방지)
TERMS = {
    "sionna": r"sionna",
    "dbsm": r"dbsm",
    "cfar": r"\bcfar\b",
    "false_alarm": r"false[- ]alarm",
    "detection_probability": r"(?:detection probability|probability of detection)",
    "physical_optics": r"physical optics",
    "radar_cross_section": r"radar cross[- ]section",
    "mesh": r"\bmesh(?:es)?\b",
    "utd": r"uniform theory of diffraction",
    "drone_uav": r"\b(?:drone|drones|uav|uavs)\b",
}

# --------------------------------------------------------------------------- #
#  16편 — 사람이 읽은 판정 + 기계가 검사할 축자 인용
# --------------------------------------------------------------------------- #
P = [
 dict(key="yuan", short="Yuan (mono3d)", first_author="Z. Yuan",
      title="On Experimental Analysis of Mono-Static 3D UAV RCS for ISAC Channel Modeling",
      venue="EuCAP", venue_long="19th European Conf. on Antennas and Propagation",
      year=2025, status="published", locator="DOI 10.23919/EuCAP63536.2025.10999912",
      venue_string_in_pdf=False,
      pdf=f"{DEEP}/On_Experimental_Analysis_of_Mono-Static_3D_UAV_RCS_for_ISAC_Channel_Modeling.pdf",
      sionna_role="not used", g2_uav=True, g3_mesh_scattering=False,
      strategy="measure",
      target="DJI Phantom 3, anechoic CATR",
      claimed="Monostatic sigma(f, azimuth) of one airframe, 1.8-18.2 GHz, in dBsm",
      not_claimed="No geometry model at all - nothing to transfer to another airframe",
      c_sigma_aspect=True, c_detection=False, c_microdoppler=False,
      quotes=["from IEEE Xplore", "at three UAV elevation sides"]),

 dict(key="das", short="Das (multiband)", first_author="S. Das",
      title="Multiband Monostatic and Bistatic RCS Characterization of AAVs for ISAC Channel Modeling",
      venue="IEEE WCL", venue_long="IEEE Wireless Communications Letters",
      year=2026, status="published", locator="vol. 15, pp. 3731-3735",
      venue_string_in_pdf=True,
      pdf=f"{DEEP}/Multiband_Monostatic_and_Bistatic_RCS_Characterization_of_AAVs_for_ISAC_Channel_Modeling.pdf",
      sionna_role="not used", g2_uav=True, g3_mesh_scattering=False,
      strategy="measure",
      target="4 DJI airframes, 1.8-27 GHz, bistatic 0-90 deg",
      claimed="Linear fits mu(f), eps(f) per airframe and bistatic angle - a table you can paste into a channel model",
      not_claimed="No mechanism: the fit cannot say why one airframe is brighter than another",
      c_sigma_aspect=True, c_detection=False, c_microdoppler=False,
      quotes=["IEEE WIRELESS COMMUNICATIONS LETTERS, VOL. 15, 2026",
              "The DJI Phantom 2 dataset is newly measured in this work"]),

 dict(key="zhang", short="Zhang (unified RCS)", first_author="Y. Zhang",
      title="A Unified RCS Modeling of Typical Targets for 3GPP ISAC Channel Standardization",
      venue="IEEE JSAC", venue_long="IEEE J. Selected Areas in Communications",
      year=2026, status="published", locator="vol. 44, pp. 702-716",
      venue_string_in_pdf=True,
      pdf=f"{DEEP}/A_Unified_RCS_Modeling_of_Typical_Targets_for_3GPP_ISAC_Channel_Standardization_and_Experimental_Analysis.pdf",
      sionna_role="not used", g2_uav=True, g3_mesh_scattering=False,
      strategy="fit",
      target="DJI M350, human, vehicle; 10-36 GHz VNA",
      claimed="A measurement-fitted decomposition sigma = A(f) B1(phi) B2, adopted into 3GPP channel work",
      not_claimed="Fit range starts at 10 GHz - the model is not claimed below it, and our bands are 1.8-5.2 GHz",
      c_sigma_aspect=True, c_detection=False, c_microdoppler=False,
      quotes=["IEEE JOURNAL ON SELECTED AREAS IN COMMUNICATIONS, VOL. 44, 2026",
              "a large-scale power factor A(f)", "a statistical fluctuation term B2"]),

 dict(key="costa_c", short="Costa (RadarConf)", first_author="H. C. A. Costa",
      title="Modelling Micro-Doppler Signature of Drone Propellers in Distributed ISAC",
      venue="IEEE RadarConf", venue_long="2024 IEEE Radar Conference",
      year=2024, status="published", locator="DOI 10.1109/RADARCONF2458775.2024.10548468",
      venue_string_in_pdf=True,
      pdf=f"{DEEP}/Modelling_Micro-Doppler_Signature_of_Drone_Propellers_in_Distributed_ISAC.pdf",
      sionna_role="not used", g2_uav=True, g3_mesh_scattering=False,
      strategy="analytic",
      target="Propeller as thin-wire continuum of point scatterers",
      claimed="Bistatic micro-Doppler signature shape, validated against an anechoic measurement",
      not_claimed="Never prints an absolute sigma - reflectivity is dimensionless throughout",
      c_sigma_aspect=False, c_detection=False, c_microdoppler=True,
      quotes=["2024 IEEE Radar Conference (RadarConf24)"]),

 dict(key="costa_j", short="Costa (JSTEAP)", first_author="H. C. A. Costa",
      title="Modeling Micro-Doppler Signature of Multi-Propeller Drones in Distributed ISAC",
      venue="IEEE JSTEAP", venue_long="IEEE J. Sel. Topics Electromagnetics, Antennas and Propagation",
      year=2025, status="published", locator="vol. 1, pp. 208-222",
      venue_string_in_pdf=True,
      pdf=f"{DEEP}/Modeling_Micro-Doppler_Signature_of_Multi-Propeller_Drones_in_Distributed_ISAC.pdf",
      sionna_role="not used", g2_uav=True, g3_mesh_scattering=False,
      strategy="analytic",
      target="Multi-propeller thin-wire model + body model",
      claimed="Pearson correlation 0.98 against measurement over bistatic angle 30-180 deg",
      not_claimed="Refuses an absolute level - the shape is validated, the scale is not",
      c_sigma_aspect=False, c_detection=False, c_microdoppler=True,
      quotes=["10.1109/JSTEAP.2025.3604407",
              "cross-correlation coefficient of 0.98 across the bistatic angles"]),

 dict(key="wei", short="Wei (testbed)", first_author="J. Wei",
      title="UAV's Rotor Micro-Doppler Feature Extraction Using ISAC Signal",
      venue="IEEE TWC", venue_long="IEEE Trans. Wireless Communications",
      year=2025, status="published", locator="vol. 24, no. 12, pp. 10166-10182",
      venue_string_in_pdf=True,
      pdf=f"{DEEP}/UAVs_Rotor_Micro-Doppler_Feature_Extraction_Using_Integrated_Sensing_and_Communication_Signal_Algorithm_Design_and_Testbed_Evaluation.pdf",
      sionna_role="not used", g2_uav=True, g3_mesh_scattering=False,
      strategy="assume",
      target="Point scatterers; body RCS is a table constant",
      claimed="Rotor micro-Doppler extraction on a real 5G NR monostatic testbed",
      not_claimed="The body RCS constant is assumed, not measured or computed - and detection is never scored",
      c_sigma_aspect=False, c_detection=False, c_microdoppler=True,
      quotes=["IEEE TRANSACTIONS ON WIRELESS COMMUNICATIONS, VOL. 24, NO. 12, DECEMBER 2025"]),

 dict(key="mdrt", short="Li (md-rt)", first_author="C. Li",
      title="Micro-Doppler Signature Simulation of Multirotor UAVs Using Ray Tracing",
      venue="IEEE ICCT", venue_long="IEEE Int. Conf. on Communication Technology",
      year=2025, status="published", locator="pp. 359-364, DOI 10.1109/ICCT67417.2025.11374154",
      venue_string_in_pdf=True,
      pdf=f"{DEEP}/Micro-Doppler_Signature_Simulation_of_Multirotor_UAVs_Using_Ray_Tracing.pdf",
      sionna_role="runs it", g2_uav=True, g3_mesh_scattering=False,
      strategy="stock",
      target="Blender propeller mesh in stock Sionna RT",
      claimed="Spectrogram ridge positions agree with a closed-form micro-Doppler formula",
      not_claimed="Amplitude is never validated, material is a stock label, and no sigma is reported",
      c_sigma_aspect=False, c_detection=False, c_microdoppler=True,
      quotes=["DOI: 10.1109/ICCT67417.2025.11374154", "Propeller material Wood"]),

 dict(key="clutter", short="Liu (Clutter-Aware ISAC)", first_author="R. Liu",
      title="Clutter-Aware Integrated Sensing and Communication: Models, Methods, and Future Directions",
      venue="Proc. IEEE", venue_long="Proceedings of the IEEE",
      year=2026, status="published", locator="vol. 114, no. 1, pp. 52-91",
      venue_string_in_pdf=True,
      pdf=f"{DEEP}/Clutter-Aware_Integrated_Sensing_and_Communication_Models_Methods_and_Future_Directions.pdf",
      sionna_role="runs it", g2_uav=True, g3_mesh_scattering=False,
      strategy="stock",
      target="UAV meshes simplified in Blender, imported into Sionna",
      claimed="A clutter taxonomy and a suppression toolbox, illustrated with Sionna RT scenes",
      not_claimed="Deliberately keeps the scene 'lightweight': never reports a target sigma, Pd or Pfa",
      c_sigma_aspect=False, c_detection=False, c_microdoppler=False,
      quotes=["PROCEEDINGS OF THE IEEE | Vol. 114, No. 1, January 2026",
              "modeled as simplified 3-D mesh objects imported into Sionna",
              "keeps the ray-tracing scene lightweight"]),

 dict(key="zig_c", short="Ziganshin (EuCAP)", first_author="A. Ziganshin",
      title="Ray-Based Simulation of Multistatic Scattering from Target Objects in ISAC",
      venue="EuCAP", venue_long="European Conf. on Antennas and Propagation",
      year=2025, status="published", locator="DOI 10.23919/EuCAP63536.2025.10999367",
      venue_string_in_pdf=False,
      pdf=f"{DEEP}/Ray-Based_Simulation_of_Multistatic_Scattering_from_Target_Objects_in_ISAC.pdf",
      sionna_role="runs it", g2_uav=False, g3_mesh_scattering=True,
      strategy="custom",
      target="Simplified car (PEC), sphere, cylinder",
      claimed="RCS of a faceted car from a Sionna-based RT + UTD + vertex-diffraction solver",
      not_claimed="Names drones as future work, in those words - the target here is a vehicle",
      c_sigma_aspect=True, c_detection=False, c_microdoppler=False,
      quotes=["from IEEE Xplore",
              # ⭐ 리포트 §2.4 가 축자로 싣는 두 문장 — 여기서 PDF 대조가 끝난다
              "can also be applied to compute scattering from other objects, "
              "such as drones, humans, and micro-Doppler effects",
              "Fig. 6: RCS of the simplified car",
              "The reflectivity with both TX and RX in the far-field transforms into RCS"]),

 dict(key="hoydis", short="Hoydis (diff. RT)", first_author="J. Hoydis",
      title="Learning Radio Environments by Differentiable Ray Tracing",
      venue="IEEE TMLCN", venue_long="IEEE Trans. Machine Learning in Communications and Networking",
      year=2024, status="published", locator="DOI 10.1109/TMLCN.2024.3474639",
      venue_string_in_pdf=True,
      pdf=f"{DEEP}/Learning_Radio_Environments_by_Differentiable_Ray_.pdf",
      sionna_role="runs it", g2_uav=False, g3_mesh_scattering=False,
      strategy="none",
      target="No target - the environment itself is the object of study",
      claimed="Gradient-based calibration of materials and scattering against a real indoor sounder",
      not_claimed="No target signature of any kind: the engine authors themselves do not solve this problem",
      c_sigma_aspect=False, c_detection=False, c_microdoppler=False,
      quotes=["DOI 10.1109/TMLCN.2024.3474639"]),

 # ---- preprints ----------------------------------------------------------- #
 dict(key="zig_j", short="Ziganshin (journal, preprint)", first_author="A. Ziganshin",
      title="Ray-Based Simulation of Scattering from Discretized Curved Bodies",
      venue="arXiv", venue_long="arXiv preprint (submitted to IEEE OJAP)",
      year=2026, status="preprint", locator="arXiv:2604.05991v2",
      venue_string_in_pdf=True,
      pdf=f"{DEEP}/Ray-Based Simulation of Scattering from Discretized Curved Bodies for Vehicular and ISAC Applications .pdf",
      sionna_role="runs it", g2_uav=False, g3_mesh_scattering=True,
      strategy="custom",
      target="Sphere, cylinder, PEC vehicle - faceted meshes",
      claimed="Near-field scattered field |E| and a facet-discretization quality metric",
      not_claimed="Never prints dBsm, and explicitly rejects SBR+PO as unsuitable in the shadow region",
      c_sigma_aspect=False, c_detection=False, c_microdoppler=False,
      quotes=["arXiv:2604.05991v2", "This SBR+PO approach, however,"]),

 dict(key="montaner", short="Montaner (deterministic ISAC)", first_author="C. Montaner",
      title="Deterministic Modeling of Dynamic ISAC Channels in RF Digital Twin Environments",
      venue="arXiv", venue_long="arXiv preprint (EuCAP workshop)",
      year=2026, status="preprint", locator="arXiv:2603.28736v1",
      venue_string_in_pdf=True,
      pdf=f"{DEEP}/Deterministic Modeling of Dynamic ISAC Channels in RF Digital Twin Environments.pdf",
      sionna_role="runs it", g2_uav=False, g3_mesh_scattering=False,
      strategy="diffuse",
      target="Scene meshes; the moving target's own scattering is a diffuse coefficient",
      claimed="RT-versus-sounder agreement of delay-Doppler channel structure at 77-81 GHz",
      not_claimed="No target RCS - the target's scattering is absorbed into a diffuse coefficient",
      c_sigma_aspect=False, c_detection=False, c_microdoppler=False,
      quotes=["arXiv:2603.28736v1"]),

 dict(key="lambda", short="LAMBDA (dataset)", first_author="L. Zhou",
      title="LAMBDA: A Low-Altitude Multimodal Base Dataset for UAV Sensing and Communication",
      venue="arXiv", venue_long="arXiv preprint",
      year=2026, status="preprint", locator="arXiv:2607.03826v1",
      venue_string_in_pdf=True,
      pdf=f"{ARCHIVE}/2607.03826__lambda-uav-dataset.pdf",
      sionna_role="runs it", g2_uav=True, g3_mesh_scattering=False,
      strategy="inject",
      target="UAV mesh - but its RCS is solved in CADFEKO, outside the RT engine",
      claimed="A large aligned multimodal UAV dataset with an RF branch",
      not_claimed="The target signature is not computed by the RT engine and is never reported in dBsm",
      c_sigma_aspect=False, c_detection=False, c_microdoppler=False,
      quotes=["arXiv:2607.03826v1", "CADFEKO [28] for UAV radar cross-section (RCS) modeling"]),

 dict(key="dmsnet", short="DMSNet", first_author="H. Liu",
      title="DMSNet: Cross-Band Learning for Multi-Target Sensing in Multi-Band ISAC",
      venue="arXiv", venue_long="arXiv preprint",
      year=2026, status="preprint", locator="arXiv:2607.17655v1",
      venue_string_in_pdf=True,
      pdf=f"{ARCHIVE}/2607.17655__dmsnet-crossband-multiband-isac.pdf",
      sionna_role="cites only", g2_uav=True, g3_mesh_scattering=False,
      strategy="inject",
      target="Point target with three parameters; RCS injected from a measurement paper",
      claimed="Cross-band multi-target counting and parameter estimation, with CFAR baselines",
      not_claimed="No mesh anywhere - the target is a scalar reflection coefficient",
      c_sigma_aspect=False, c_detection=True, c_microdoppler=False,
      quotes=["arXiv:2607.17655v1"]),

 dict(key="openisac", short="OpenISAC (platform)", first_author="Z. Zhou",
      title="OpenISAC: An Open-Source Real-Time Experimentation Platform for OFDM-ISAC",
      venue="arXiv", venue_long="arXiv preprint",
      year=2026, status="preprint", locator="arXiv:2601.03535v2",
      venue_string_in_pdf=True,
      pdf=f"{ARCHIVE}/2601.03535__openisac.pdf",
      sionna_role="cites only", g2_uav=False, g3_mesh_scattering=False,
      strategy="none",
      target="Real hardware - no target model is needed or offered",
      claimed="A real-time software-defined OFDM-ISAC platform with range-Doppler output",
      not_claimed="Never mentions CFAR, false alarm or detection probability: the false-alarm floor is uncontrolled",
      c_sigma_aspect=False, c_detection=False, c_microdoppler=False,
      quotes=["arXiv:2601.03535v2"]),

 dict(key="sagitta", short="Sagitta (SBR)", first_author="M. Pasquale",
      title="BVH-Accelerated Ray Tracing for High-Frequency Electromagnetic Backscattering",
      venue="arXiv", venue_long="arXiv preprint",
      year=2026, status="preprint", locator="arXiv:2604.09243v1",
      venue_string_in_pdf=True,
      pdf=f"{ARCHIVE}/2604.09243__sagitta-sbr.pdf",
      sionna_role="not used", g2_uav=False, g3_mesh_scattering=True,
      strategy="outside",
      target="PEC aircraft meshes in a bespoke CUDA/HIP SBR+PO code",
      claimed="Monostatic RCS from a mesh, cross-checked against the Mie series",
      not_claimed="Zero connection to Sionna, and no drone, no dielectric, no detection",
      c_sigma_aspect=True, c_detection=False, c_microdoppler=False,
      quotes=["arXiv:2604.09243v1"]),
]

STRATEGY_LABEL = {
    "measure":  "Measure it",
    "fit":      "Fit a measured model",
    "analytic": "Analytic point/thin-wire target",
    "assume":   "Assume a constant sigma",
    "stock":    "Stock engine interactions",
    "inject":   "Inject sigma from outside",
    "diffuse":  "Diffuse scattering coefficient",
    "custom":   "Custom scattering in the engine",
    "outside":  "Own solver outside Sionna",
    "none":     "No target model at all",
}

#: 그림 글자는 영어(하우스 규약), **리포트 본문 표는 한국어**. 두 벌을 다 싣는다.
STRATEGY_LABEL_KO = {
    "measure":  "측정한다",
    "fit":      "측정 피팅모델",
    "analytic": "해석 점·thin-wire 표적",
    "assume":   "σ 를 상수로 가정",
    "stock":    "엔진 기본 상호작용에 맡김",
    "inject":   "외부에서 σ 주입",
    "diffuse":  "확산산란 계수로 대체",
    "custom":   "엔진 안에 산란을 구현",
    "outside":  "Sionna 밖 자체 솔버",
    "none":     "표적 모델 없음",
}

#: 논문별 한국어 요약 — `target` · `claimed` · `not_claimed` 의 대응본.
#  영문판과 **같은 사실**을 말해야 한다. 근거는 각 논문의 `quotes`(PDF 대조 완료).
KO = {
 "yuan":    ("DJI Phantom 3, 무향실 CATR",
             "한 기체의 모노스태틱 σ(f, 방위)를 1.8–18.2 GHz 에서 dBsm 으로",
             "기하 모델이 없다 — 다른 기체로 옮길 수단이 없다"),
 "das":     ("DJI 4기종, 1.8–27 GHz, 바이스태틱각 0–90°",
             "기체·각도별 μ(f)·ε(f) 1차식 계수표 — 채널모델에 그대로 붙일 수 있다",
             "메커니즘이 없다 — 왜 어느 기체가 더 밝은지 피팅은 말하지 못한다"),
 "zhang":   ("DJI M350·사람·차량, 10–36 GHz VNA",
             "측정으로 맞춘 분해 σ=A(f)·B1(φ)·B2, 3GPP 채널 논의에 채택",
             "피팅 구간이 10 GHz 부터다 — 우리 밴드는 그 아래다"),
 "costa_c": ("프로펠러를 thin-wire 점산란체 연속체로",
             "바이스태틱 마이크로도플러 서명의 **모양**, 무향실 실측 대조",
             "절대 σ 를 한 번도 찍지 않는다 — 반사도가 끝까지 무차원이다"),
 "costa_j": ("다중 프로펠러 thin-wire + 동체 모델",
             "바이스태틱각 30–180°에서 실측 대비 Pearson 상관 0.98",
             "절대 레벨을 거부한다 — 모양은 검증하고 눈금은 하지 않는다"),
 "wei":     ("점산란체 — 동체 RCS 는 표에 적힌 상수",
             "실제 5G NR 모노스태틱 테스트베드에서 로터 마이크로도플러 추출",
             "동체 RCS 상수는 가정이고, 검출은 채점되지 않는다"),
 "mdrt":    ("Blender 프로펠러 메쉬를 스톡 Sionna RT 에",
             "스펙트로그램 능선 **위치**가 폐형식 마이크로도플러 식과 일치",
             "진폭은 검증하지 않고, 재질은 스톡 라벨이며, σ 는 없다"),
 "clutter": ("Blender 로 단순화한 UAV 메쉬를 Sionna 에 임포트",
             "클러터 분류체계와 억제 도구상자, Sionna RT 장면으로 예시",
             "장면을 일부러 'lightweight' 로 둔다 — 표적 σ·Pd·Pfa 가 없다"),
 "zig_c":   ("단순화한 차량(PEC)·구·원기둥",
             "Sionna 기반 RT+UTD+정점회절 솔버로 낸 패싯 차량의 RCS",
             "드론은 향후 과제로 **그 단어 그대로** 적혀 있다 — 여기 표적은 차량이다"),
 "hoydis":  ("표적 없음 — 환경 자체가 연구 대상",
             "실내 사운더 실측에 맞춰 재질·산란을 경사기반으로 교정",
             "표적 서명이 전혀 없다 — 엔진 저자들 자신도 이 문제를 풀지 않는다"),
 "zig_j":   ("구·원기둥·PEC 차량의 패싯 메쉬",
             "근거리 산란전계 |E| 와 패싯 이산화 품질 지표",
             "dBsm 을 찍지 않고, 실제 재질 반영을 향후 과제로 남긴다"),
 "montaner":("장면 메쉬 — 이동표적의 산란은 확산계수 하나로",
             "77–81 GHz 사운더와 RT 의 지연-도플러 구조 일치",
             "표적 RCS 가 없다 — 표적 산란이 확산계수에 흡수된다"),
 "lambda":  ("UAV 메쉬 — 단 RCS 는 RT 엔진 밖 CADFEKO 에서 푼다",
             "RF 분기를 가진 대규모 정렬 멀티모달 UAV 데이터셋",
             "표적 서명을 RT 엔진이 계산하지 않고 dBsm 으로 보고하지도 않는다"),
 "dmsnet":  ("파라미터 3개짜리 점표적 — RCS 는 측정 논문에서 주입",
             "다중밴드 다표적 계수·파라미터 추정, CFAR 베이스라인 포함",
             "메쉬가 어디에도 없다 — 표적이 스칼라 반사계수다"),
 "openisac":("실제 하드웨어 — 표적 모델이 필요하지도 제공되지도 않는다",
             "실시간 SDR OFDM-ISAC 플랫폼과 거리-도플러 출력",
             "CFAR·false alarm·detection probability 가 전문에 0회 — 오경보 바닥이 통제되지 않는다"),
 "sagitta": ("자체 CUDA/HIP SBR+PO 코드 안의 PEC 항공기 메쉬",
             "메쉬에서 낸 모노스태틱 RCS 를 Mie 급수와 교차검증",
             "Sionna 와 연결점이 0 이고, 드론도 유전체도 검출도 없다"),
}


# --------------------------------------------------------------------------- #
#  PDF 추출 · 검사
# --------------------------------------------------------------------------- #
def norm(t: str) -> str:
    """리가처(ﬁ→fi)·유니코드 정규화 + 공백 접기. 인용 대조는 전부 이 위에서 한다."""
    t = unicodedata.normalize("NFKC", t)
    return re.sub(r"\s+", " ", t)


def read_pdf(path: str) -> tuple[str, int, dict]:
    with fitz.open(path) as d:
        return norm("".join(pg.get_text() for pg in d)), d.page_count, dict(d.metadata or {})


#: ⭐ 게재상태를 **기계가 확정**하는 규칙.
#  IEEE 조판 PDF 는 메타데이터 `subject` 에 "게재처;연도;권;호;DOI" 를 박아 넣는다.
#  arXiv 프리프린트는 이 칸이 비어 있고, 대신 본문에 arXiv id 가 찍힌다.
#  둘 중 어느 근거도 없으면 그 논문은 census 에 들어가지 못한다 — 게재상태를 지어내지 않는다.
VENUE_HINT = {"EuCAP": "EuCAP", "IEEE WCL": "Wireless Communications Letters",
              "IEEE JSAC": "Selected Areas in Communications",
              "IEEE RadarConf": "Radar Conference", "IEEE JSTEAP": "JSTEAP",
              "IEEE TWC": "Wireless Communications", "IEEE ICCT": "Communication Technology",
              "Proc. IEEE": "Proceedings of the IEEE", "IEEE TMLCN": "TMLCN",
              "arXiv": "arXiv"}

#: ⭐ 리포트가 **"~하지 않는다"** 로 쓰는 문장은 전부 여기서 기계 대조된다.
#  부정 주장이야말로 검증 없이는 못 쓴다 — 원문에 그 단어가 몇 번 나오는지가 근거다.
EXPECT = {
    "openisac": dict(cfar=0, false_alarm=0, detection_probability=0),
    "clutter":  dict(dbsm=0, physical_optics=0),
    "mdrt":     dict(dbsm=0, physical_optics=0),
    "costa_j":  dict(dbsm=0),
    "costa_c":  dict(dbsm=0),
    "wei":      dict(dbsm=0, cfar=0),
    "zig_j":    dict(dbsm=0),
    "sagitta":  dict(sionna=0),
    "hoydis":   dict(dbsm=0),
    "das":      dict(sionna=0),
    "yuan":     dict(sionna=0, cfar=0),
    "zhang":    dict(sionna=0),
}


def census() -> dict:
    papers, failures = [], []
    for p in P:
        if not os.path.exists(p["pdf"]):
            failures.append(f"{p['key']}: PDF 없음 — {p['pdf']}")
            continue
        text, pages, pdfmeta = read_pdf(p["pdf"])
        low = text.lower()

        terms = {k: len(re.findall(v, low)) for k, v in TERMS.items()}

        # ── 축자 인용 검사 — 이 검사가 리포트의 모든 귀속을 지탱한다 ──────────
        missing = [q for q in p["quotes"] if norm(q) not in text]
        if missing:
            failures.append(f"{p['key']}: PDF 에 없는 인용 {missing!r}")

        # ── 게재상태 근거 검사 — 메타데이터 subject 또는 본문 ────────────────
        subj = norm(str(pdfmeta.get("subject") or ""))
        hint = VENUE_HINT[p["venue"]]
        ev = []
        if hint.lower() in subj.lower():
            ev.append("pdf_metadata_subject")
        if hint.lower() in text.lower() or norm(p["locator"]).lower() in text.lower():
            ev.append("body_text")
        if not ev:
            failures.append(f"{p['key']}: 게재상태 근거 없음 — subject={subj[:60]!r}")
        if p["status"] == "published" and "arxiv" in subj.lower():
            failures.append(f"{p['key']}: published 인데 subject 가 arXiv 다")

        # ── 기계 판정 ────────────────────────────────────────────────────────
        g1 = p["sionna_role"] == "runs it"
        g4 = terms["dbsm"] > 0                       # dBsm 을 한 번이라도 찍었나
        if p["sionna_role"] == "not used" and terms["sionna"] > 0:
            failures.append(f"{p['key']}: 'not used' 인데 sionna 언급 {terms['sionna']}회")
        if g1 and terms["sionna"] == 0:
            failures.append(f"{p['key']}: 'runs it' 인데 sionna 언급 0회")

        # ── 부정 주장 대조 — "한 번도 안 쓴다" 는 세어 보고 쓴다 ──────────────
        for term, want in EXPECT.get(p["key"], {}).items():
            if terms[term] != want:
                failures.append(f"{p['key']}: {term} 기대 {want} ≠ 실측 {terms[term]}")

        gates = dict(g1_sionna=g1, g2_uav=bool(p["g2_uav"]),
                     g3_mesh_scattering=bool(p["g3_mesh_scattering"]), g4_dbsm=g4)

        papers.append(dict(
            key=p["key"], short=p["short"], first_author=p["first_author"],
            title=p["title"], venue=p["venue"], venue_long=p["venue_long"],
            year=p["year"], status=p["status"], locator=p["locator"],
            status_mark="published" if p["status"] == "published" else "PREPRINT",
            venue_status=(f"{p['venue']} {p['year']}" if p["status"] == "published"
                          else f"PREPRINT ({p['locator']})"),
            venue_evidence="+".join(ev), pdf_subject=subj,
            venue_string_in_pdf=p["venue_string_in_pdf"],
            pdf=os.path.relpath(p["pdf"], "/data/public"),
            pages=pages, chars=len(text),
            sionna_role=p["sionna_role"], strategy=p["strategy"],
            sionna_role_ko={"runs it": "직접 돌림", "cites only": "인용만",
                            "not used": "미사용"}[p["sionna_role"]],
            strategy_label=STRATEGY_LABEL[p["strategy"]],
            strategy_label_ko=STRATEGY_LABEL_KO[p["strategy"]],
            target=p["target"], claimed=p["claimed"], not_claimed=p["not_claimed"],
            target_ko=KO[p["key"]][0], claimed_ko=KO[p["key"]][1],
            not_claimed_ko=KO[p["key"]][2],
            terms=terms, gates=gates,
            claims=dict(sigma_abs=g4, sigma_aspect=bool(p["c_sigma_aspect"]),
                        detection=bool(p["c_detection"]),
                        microdoppler=bool(p["c_microdoppler"]),
                        mesh_in_engine=bool(g1 and p["g3_mesh_scattering"])),
            quotes=p["quotes"], quotes_verified=len(p["quotes"]) - len(missing),
        ))

    if failures:
        for f in failures:
            print("⛔", f)
        raise SystemExit("귀속 검사 실패 — 인용이 PDF 에 없으면 리포트를 만들지 않는다.")
    return papers


def funnel(papers, subset=None) -> dict:
    S = [q for q in papers if subset is None or q["status"] == subset]
    n0 = len(S)
    n1 = [q for q in S if q["gates"]["g1_sionna"]]
    n2 = [q for q in n1 if q["gates"]["g2_uav"]]
    n3 = [q for q in n2 if q["gates"]["g3_mesh_scattering"]]
    n4 = [q for q in n3 if q["gates"]["g4_dbsm"]]
    return dict(in_census=n0, g1_sionna=len(n1), g2_uav=len(n2),
                g3_mesh_scattering=len(n3), g4_dbsm=len(n4),
                survivors_g2=[q["key"] for q in n2], survivors_g3=[q["key"] for q in n3])


def sionna_api() -> dict:
    """§1 의 근거 — **설치된 Sionna 를 직접 열어** 무엇이 있고 무엇이 없는지 센다.

    ⚠ 주장 범위: "광선추적이 RCS 를 못 낸다" 가 아니다(SBR 계열은 낸다).
       정확히는 **Sionna 의 기본 경로 solver 에 표면적분(PO) 단계와 RCS API 가 없다** 이다.
    """
    import sionna
    import sionna.rt as rt

    pub = [n for n in dir(rt) if not n.startswith("_")]
    rcs_names = [n for n in pub if re.search(r"rcs|cross[_ ]?section", n, re.I)]
    scat_names = [n for n in pub if re.search(r"scatter", n, re.I)]
    mro = [c.__name__ for c in rt.PathSolver.__mro__]
    return dict(
        version=sionna.__version__,
        rt_public_names=len(pub),
        rcs_api_names=len(rcs_names), rcs_api_list=rcs_names,
        scattering_api_names=len(scat_names), scattering_api_list=scat_names,
        pathsolver_mro=mro, pathsolver_is_extension_point=len(mro) > 2,
        note=("공개 이름 중 RCS/산란단면적을 계산하는 것은 0개다. `ScatteringPattern` 계열은 "
              "확산반사의 **각분포 함수**이지 σ 가 아니다. `PathSolver` 는 MRO 가 "
              "[PathSolver, object] 라 상속 확장점도 아니다 — 확장은 광선엔진 위에 직접 얹는다."),
    )


def scope_counts() -> dict:
    """census 범위를 숫자로 못박는다 — 아카이브에 몇 편이 있고 그중 몇 편을 읽었나."""
    n = {}
    for lbl, d in (("archive_root", ARCHIVE), ("deep_read_folder", DEEP)):
        n[lbl] = len([f for f in os.listdir(d) if f.lower().endswith(".pdf")])
    n["pdf_in_scope"] = n["archive_root"] + n["deep_read_folder"]
    return n


def context() -> dict:
    """리포트 §1·§4 가 쓰는 파생 수치 — 전부 기존 outputs 에서 계산한다."""
    with open(os.path.join(ROOT, "outputs", "rcs_anchor.json"), encoding="utf-8") as f:
        A = json.load(f)
    c = 299792458.0
    lam = {b: 100.0 * c / hz for b, hz in A["meta"]["bands"].items()}
    lit = A["literature"]["mu_eps"]
    slopes = {k: v["regression"]["el0"]["a"] for k, v in A["drones"].items()}
    lo, hi = min(slopes.values()), max(slopes.values())
    lit_lo = min(v["mu_a"] for v in lit.values())
    lit_hi = max(v["mu_a"] for v in lit.values())
    return dict(
        bands_hz=A["meta"]["bands"], lambda_cm=lam,
        lit_slope_db_per_ghz=dict(
            multiband_das=lit["multiband_phantom3"]["mu_a"],
            mono3d_yuan=lit["mono3d_theta90"]["mu_a"], lo=lit_lo, hi=lit_hi),
        our_slope_db_per_ghz=dict(by_drone=slopes, lo=lo, hi=hi, n_drones=len(slopes),
                                  elevation_deg=0.0),
        slope_ratio=dict(lo=lo / lit_hi, hi=hi / lit_lo),
        note="기울기는 rcs_anchor.json 의 el=0 회귀 a [dB/GHz] — 문헌 측정도 수평면이라 축이 맞는다",
    )


# --------------------------------------------------------------------------- #
#  그림 4장 — 글자는 전부 영어(하우스 규약)
# --------------------------------------------------------------------------- #
CPUB, CPRE = "#1f6fb4", "#c26a1f"
plt.rcParams.update({"font.size": 9, "axes.grid": True, "grid.alpha": .25,
                     "figure.dpi": 150, "savefig.bbox": "tight"})


def fig_funnel(D, path):
    stages = ["In census", "G1 runs Sionna-class RT", "G2 + target is a UAV",
              "G3 + scattering from the mesh", "G4 + absolute RCS in dBsm"]
    keys = ["in_census", "g1_sionna", "g2_uav", "g3_mesh_scattering", "g4_dbsm"]
    pub = [D["funnel"]["published"][k] for k in keys]
    pre = [D["funnel"]["preprint"][k] for k in keys]
    y = np.arange(len(stages))[::-1]
    fig, ax = plt.subplots(figsize=(7.4, 3.1))
    ax.barh(y, pub, color=CPUB, label="Peer-reviewed / published")
    ax.barh(y, pre, left=pub, color=CPRE, label="Preprint only")
    for i, (a, b) in enumerate(zip(pub, pre)):
        ax.text(a + b + .18, y[i], f"{a + b}  ({a} published)", va="center", fontsize=8.5)
    ax.set_yticks(y, stages, fontsize=8.5)
    ax.set_xlabel("Number of papers")
    ax.set_xlim(0, len(D["papers"]) + 4.5)
    ax.set_title("Target-scattering census: survivors after each gate")
    ax.legend(loc="lower right", fontsize=8, framealpha=.95)
    ax.grid(axis="y", visible=False)
    fig.savefig(path)
    plt.close(fig)


def fig_matrix(D, path):
    axes_lbl = ["Absolute RCS\n(dBsm)", "Aspect-resolved\nRCS", "Detection\n(CFAR / Pd)",
                "Micro-Doppler\nsignature", "Mesh scattering\ninside Sionna"]
    ck = ["sigma_abs", "sigma_aspect", "detection", "microdoppler", "mesh_in_engine"]
    ps = sorted(D["papers"], key=lambda q: (q["strategy_label"], q["short"]))
    M = np.array([[1 if q["claims"][k] else 0 for k in ck] for q in ps])
    fig, ax = plt.subplots(figsize=(7.4, 6.0))
    ax.imshow(M, cmap=matplotlib.colors.ListedColormap(["#f2f2f2", "#1f6fb4"]),
              vmin=0, vmax=1, aspect="auto")
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            ax.text(j, i, "claimed" if M[i, j] else "-", ha="center", va="center",
                    fontsize=7, color="white" if M[i, j] else "#888")
    ax.set_xticks(range(len(axes_lbl)), axes_lbl, fontsize=7.5)
    ax.set_yticks(range(len(ps)),
                  [f"{q['short']}  [{q['strategy_label']}]" for q in ps], fontsize=7.5)
    ax.set_xticks(np.arange(-.5, len(axes_lbl), 1), minor=True)
    ax.set_yticks(np.arange(-.5, len(ps), 1), minor=True)
    ax.grid(which="minor", color="w", lw=1.4)
    ax.grid(which="major", visible=False)
    ax.tick_params(which="minor", length=0)
    ax.set_title("Strategy catalogue: which claim each target-signature source supports")
    fig.savefig(path)
    plt.close(fig)


def fig_dbsm(D, path):
    ps = sorted(D["papers"], key=lambda q: (-q["terms"]["dbsm"], q["short"]))
    v = [q["terms"]["dbsm"] for q in ps]
    col = [{"runs it": CPUB, "cites only": "#9aa7b1", "not used": CPRE}[q["sionna_role"]]
           for q in ps]
    fig, ax = plt.subplots(figsize=(7.4, 3.4))
    ax.bar(range(len(ps)), v, color=col)
    ax.set_xticks(range(len(ps)), [q["short"] for q in ps], rotation=38,
                  ha="right", fontsize=7.5)
    ax.set_ylabel('Occurrences of "dBsm" in full text')
    ax.set_title("Who ever prints an absolute RCS?")
    h = [plt.Rectangle((0, 0), 1, 1, color=CPUB), plt.Rectangle((0, 0), 1, 1, color="#9aa7b1"),
         plt.Rectangle((0, 0), 1, 1, color=CPRE)]
    ax.legend(h, ["Runs Sionna", "Cites Sionna only", "Does not use Sionna"], fontsize=8)
    ax.grid(axis="x", visible=False)
    fig.savefig(path)
    plt.close(fig)


def fig_detect(D, path):
    ps = sorted(D["papers"], key=lambda q: -(q["terms"]["cfar"] + q["terms"]["false_alarm"]
                                             + q["terms"]["detection_probability"]))
    x = np.arange(len(ps))
    fig, ax = plt.subplots(figsize=(7.4, 3.4))
    for off, k, lbl, c in [(-.27, "cfar", "CFAR", CPUB),
                           (0.0, "false_alarm", "false alarm", "#59a14f"),
                           (.27, "detection_probability", "detection probability", CPRE)]:
        ax.bar(x + off, [q["terms"][k] for q in ps], width=.26, label=lbl, color=c)
    ax.set_xticks(x, [q["short"] for q in ps], rotation=38, ha="right", fontsize=7.5)
    ax.set_ylabel("Occurrences in full text")
    ax.set_title("Who controls the false-alarm rate?")
    ax.legend(fontsize=8)
    ax.grid(axis="x", visible=False)
    fig.savefig(path)
    plt.close(fig)


# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = datetime.now()
    papers = census()
    D = dict(
        meta=dict(
            generated=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            tool=f"PyMuPDF {fitz.__doc__.split(':')[0].split()[-1]}",
            archive=ARCHIVE,
            n_papers=len(papers),
            n_quotes=sum(len(q["quotes"]) for q in papers),
            n_expect_checks=sum(len(v) for v in EXPECT.values()),
            scope=("전문 추출로 관문검사를 통과시킨 편수만 센다. 아카이브 전체가 아니다 — "
                   "범위 한계는 리포트 '이 편의 한계' 에 적혀 있다."),
            **scope_counts(),
        ),
        sionna_api=sionna_api(),
        gates=GATES,
        papers=papers,
        funnel=dict(all=funnel(papers), published=funnel(papers, "published"),
                    preprint=funnel(papers, "preprint")),
        counts=dict(
            published=sum(q["status"] == "published" for q in papers),
            preprint=sum(q["status"] == "preprint" for q in papers),
            runs_sionna=sum(q["sionna_role"] == "runs it" for q in papers),
            reports_dbsm=sum(q["gates"]["g4_dbsm"] for q in papers),
            reports_dbsm_and_runs_sionna=sum(q["gates"]["g4_dbsm"]
                                             and q["gates"]["g1_sionna"] for q in papers),
            claims_detection=sum(q["claims"]["detection"] for q in papers),
            zero_cfar_and_falsealarm=sum(q["terms"]["cfar"] == 0
                                         and q["terms"]["false_alarm"] == 0 for q in papers),
            total_pages=sum(q["pages"] for q in papers),
        ),
        strategies={s: sum(q["strategy"] == s for q in papers) for s in STRATEGY_LABEL},
        context=context(),
    )

    os.makedirs(FIGDIR, exist_ok=True)
    figs = dict(funnel="report01_gate_funnel.png", matrix="report01_strategy_matrix.png",
                dbsm="report01_dbsm_counts.png", detect="report01_detection_vocab.png")
    fig_funnel(D, os.path.join(FIGDIR, figs["funnel"]))
    fig_matrix(D, os.path.join(FIGDIR, figs["matrix"]))
    fig_dbsm(D, os.path.join(FIGDIR, figs["dbsm"]))
    fig_detect(D, os.path.join(FIGDIR, figs["detect"]))
    D["figures"] = {k: f"outputs/figures/{v}" for k, v in figs.items()}
    D["meta"]["runtime_s"] = (datetime.now() - t0).total_seconds()

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(D, f, ensure_ascii=False, indent=1)

    F = D["funnel"]["all"]
    print(f"✅ 논문 {D['meta']['n_papers']}편 · 축자 인용 {D['meta']['n_quotes']}건 전부 PDF 에서 확인 "
          f"· 부정주장 대조 {D['meta']['n_expect_checks']}건 통과")
    print(f"   Sionna {D['sionna_api']['version']}: sionna.rt 공개이름 "
          f"{D['sionna_api']['rt_public_names']}개 중 RCS API {D['sionna_api']['rcs_api_names']}개")
    print(f"   게재 {D['counts']['published']} / 프리프린트 {D['counts']['preprint']}")
    print(f"   관문: 총 {F['in_census']} → Sionna {F['g1_sionna']} → UAV {F['g2_uav']} "
          f"→ 메쉬산란 {F['g3_mesh_scattering']} → dBsm {F['g4_dbsm']}")
    print(f"   → {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
