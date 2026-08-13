# -*- coding: utf-8 -*-
"""
capability_matrix.py — 선행연구 능력 매트릭스 (사용자 추적표 형식의 확장판)
==========================================================================
사용자가 보여준 추적표는 논문을 **능력 열**로 세운다:
    Sionna RT | drone Mesh | material | Aspect/RCS | Rotor | diffraction
이 스크립트는 그 형식을 우리 포지셔닝에 필요한 세 열로 확장한다:
    + amplitude VALIDATED against what | geometry config | unambiguous velocity

⭐ 증거 규칙(이 워크플로의 존재 이유)
  한 칸(cell)의 값은 셋 중 하나다.
    QUOTED      — 내가 이번 실행에서 직접 연 PDF 의 축자 문장. 스크립트가 매 실행마다
                  그 문장을 PDF 텍스트 레이어에 **재대조**한다. 대조 실패하면 자동으로
                  UNVERIFIED 로 강등된다(수동 개입 불가).
    COMPUTED    — 디스크의 JSON 또는 PDF 전문 용어 계수처럼 우리가 계산했고 재현 가능한 값.
    DERIVED     — '해당 없음' 판정 전용. 같은 행의 **인용된 칸**에서 논리적으로 따라온다
                  (예: 표적이 승용차라고 인용된 행의 Rotor 열). 어느 칸에서 왔는지 적는다.
                  ⚠ 이 등급을 만든 이유는 정직성 때문이다 — N/A 를 COMPUTED 로 올리면 계산하지
                  않은 것을 계산했다고 말하는 것이고, UNVERIFIED 로 내리면 확인한 것을 확인
                  안 했다고 말하는 것이다. 셋 다 아니므로 넷째 칸을 만들고 수를 따로 센다.
    UNVERIFIED  — 위 어느 것도 아님. 발표에 쓰면 안 되는 칸.
  회절 열과 무모호속도 열의 '없음' 판정은 **PDF 전문 용어 계수 0** 으로 뒷받침한다
  (추론이 아니라 측정이다. 다만 '언급이 없다'와 '구현이 없다'는 다른 명제이므로
   라벨에 그대로 적는다).

⚠ 우리 행은 만점이 아니다. 회절(PTD/UTD) 부재는 실제 약점이고 매트릭스에 그렇게 찍힌다.

실행:
  cd /workspace/sionna && PYTHONPATH=src:benchmark \\
    ~/.venvs/py312/bin/python benchmark/capability_matrix.py

산출:
  outputs/capability_matrix.json
  outputs/figures/capability_matrix.{png,pdf}         — 전체 매트릭스
  outputs/figures/capability_matrix_slide.{png,pdf}   — 슬라이드용 축약본(16:9)
"""
from __future__ import annotations

import json
import math
import os
import re
import sys
import time
import unicodedata

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
OUT = os.path.join(_ROOT, "outputs")
OUT_FIG = os.path.join(OUT, "figures")
REFLIB = os.path.join(OUT, "reference_library.json")

# =========================================================================== #
#  0. 열 정의 · 마크 척도 · 증거 등급
# =========================================================================== #
COLUMNS = [
    ("engine",     "Ray engine",            "어떤 엔진에서 산란장이 계산되는가"),
    ("mesh",       "Target mesh",           "표적이 3-D 표면 메시인가"),
    ("material",   "Material model",        "재질이 부여되는가(부위별인가)"),
    ("aspect",     "Aspect-resolved RCS",   "자세각에 따라 분해된 RCS/반사도인가"),
    ("rotor",      "Rotor motion",          "회전 로터의 운동이 모형에 있는가"),
    ("diffraction", "Diffraction",          "회절 처리(UTD/PTD/정점/쐐기)가 있는가"),
    ("validation", "Amplitude validation",  "산란 '진폭'을 무엇과 대조했는가"),
    ("geometry",   "Geometry mono/bi/multi", "어느 기하를 다루는가"),
    ("vmax",       "Unambiguous velocity",  "무모호 속도를 보고하는가"),
]
COL_IDS = [c[0] for c in COLUMNS]

MARKS = {2: ("FULL", "●"), 1: ("PARTIAL", "◐"),
         0: ("NONE", "○"), -1: ("NOT_APPLICABLE", "–")}

GRADES = {
    "QUOTED": "내가 이번 실행에서 연 PDF 의 축자 문장이고, 스크립트가 재대조에 성공했다.",
    "COMPUTED": "디스크의 JSON 또는 PDF 전문 용어 계수에서 우리가 계산했다. 재현 가능.",
    "DERIVED": "'해당 없음' 판정 전용 — 같은 행의 인용된 칸에서 따라온다. derived_from 에 출처 칸을 적는다.",
    "UNVERIFIED": "1차 출처로 확인하지 않았다. 발표에 쓰지 말 것.",
}

ROW_GROUPS = {
    "S": "Scattering computed from a target geometry",
    "T": "Target inside a ray-traced scene, no scattering integral",
    "M": "Measurement-based signature anchor",
    "V": "Reports unambiguous velocity, no target scattering",
    "O": "This work",
}

# =========================================================================== #
#  1. PDF 스캔 — 매 실행마다 원문을 다시 연다
# =========================================================================== #
DIFF_PATS = {
    "diffract": r"diffract\w*",
    "UTD": r"\bUTD\b",
    "PTD": r"\bPTD\b",
    "GTD": r"\bGTD\b",
    "wedge": r"\bwedges?\b",
    "creeping": r"creeping wave",
}
VMAX_PATS = {
    "unambiguous": r"unambiguous",
    "aliasing": r"aliasing|aliased",
    "nyquist": r"Nyquist",
}
GEO_PATS = {"monostatic": r"monostatic", "bistatic": r"bistatic",
            "multistatic": r"multistatic", "sionna": r"Sionna"}
#: 능력 열의 '용어가 아예 없다' 판정을 뒷받침하는 패턴. 셀에 count=(키,"zero") 를 달면
#  스크립트가 **매 실행마다 세고**, 0 이 아니면 그 칸을 UNVERIFIED 로 강등한다.
COL_PATS = {
    "rotor": r"\brotors?\b|\bpropellers?\b|\bblades?\b|micro-?doppler",
    "material": r"\bpermittivity\b|\bconductivity\b|\bPEC\b|perfectly conducting|\bdielectric\b",
    "aspect": r"\baspect angle\b|aspect-dependent|\bRCS (?:pattern|versus|vs\.?)",
    "mesh": r"\bmesh\b|\bfacets?\b|\bCAD\b|Blender|3-?D model",
    "validation": r"\bvalidat\w+",
    "dbsm": r"\bdBsm\b",
}

_LIG = {"ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl",
        "’": "'", "‘": "'", "“": '"', "”": '"',
        "–": "-", "—": "-", "−": "-", " ": " "}


def _norm(s: str) -> str:
    """축자 대조용 정규화 — 합자·따옴표·줄바꿈 붙임표·공백만 없앤다. 단어는 건드리지 않는다.
    'rein- forced' 같은 **줄바꿈 하이픈**은 저자의 글자가 아니라 조판 산물이므로 붙인다."""
    s = unicodedata.normalize("NFKC", s)
    for a, b in _LIG.items():
        s = s.replace(a, b)
    s = re.sub(r"-\s*", "", s)          # 하이픈 제거(줄바꿈 하이픈 접합 포함) - 양쪽 동일 적용
    s = re.sub(r"\s+", "", s)
    return s.lower()


def scan_pdfs(paths: dict) -> dict:
    import fitz
    out = {}
    for key, p in paths.items():
        if not p or not os.path.exists(p):
            out[key] = {"error": "PDF_NOT_ON_DISK", "pdf": p}
            continue
        doc = fitz.open(p)
        pages = [pg.get_text() for pg in doc]
        txt = "\n".join(pages)
        rec = {"pdf": p, "n_pages": len(pages),
               "diff": {k: len(re.findall(v, txt, re.IGNORECASE if k in
                                          ("diffract", "wedge", "creeping") else 0))
                        for k, v in DIFF_PATS.items()},
               "vmax": {k: len(re.findall(v, txt, re.IGNORECASE))
                        for k, v in VMAX_PATS.items()},
               "geo": {k: len(re.findall(v, txt, re.IGNORECASE))
                       for k, v in GEO_PATS.items()},
               "cols": {k: len(re.findall(v, txt, re.IGNORECASE))
                        for k, v in COL_PATS.items()},
               "_norm": _norm(txt)}
        out[key] = rec
    return out


# =========================================================================== #
#  2. 셀 생성기
# =========================================================================== #
def C(level, label, quote=None, loc=None, computed=None, source=None, note=None,
      derived=None, count=None):
    """셀 하나. 등급은 build 단계에서 PDF 재대조 결과로 확정된다.
    count=(패턴키, 'zero'|'report') 를 주면 computed 문자열을 **실행 시점 계수**로 만든다."""
    return dict(level=level, label=label, quote=quote, loc=loc,
                computed=computed, source=source, note=note, derived_from=derived,
                count=count)


def NA(label, derived):
    """'해당 없음' 칸 — 반드시 같은 행의 어느 칸에서 따라오는지 적는다."""
    return C(-1, label, derived=derived)


# =========================================================================== #
#  3. 행 — 논문 + 우리
# =========================================================================== #
#: PDF 경로는 reference_library.json 에서 끌어오되, G1/G2 두 편은 verify_chen.json 에서 온다.
EXTRA_PDF = {
    "abratkiewicz_ssb_jstars23":
        "/data/public/sionna_jeong/reference_library/g1g2/abratkiewicz2023_jstars.pdf",
    "chen_rotating_applsci24":
        "/data/public/sionna_jeong/reference_library/g1g2/chen2024_applsci_14_4282.pdf",
    #: ⚠ reference_library 의 pdf_paths[0] 은 Ezuma/Semkin 의 **다른 논문**(arXiv 2112.09774)이다.
    #  IEEE Access 2020 본편을 명시적으로 지정한다.
    #: ⭐ 게재판(JSTEAP)을 쓴다. reference_library 의 pdf_paths[0] 은 arXiv 판(2504.05168)이다.
    "costa_bistatic_md_jsteap25":
        "/data/public/sionna_jeong/papers_isac_sionna/paper_sionna_Ray_0723/"
        "Modeling_Micro-Doppler_Signature_of_Multi-Propeller_Drones_in_Distributed_ISAC.pdf",
    "semkin_drone_rcs_access20":
        "/data/public/sionna_jeong/papers_isac_sionna/new_0731/"
        "ieeeaccess2020_semkin__drone-rcs-mmwave-26-40ghz.pdf",
}

CITATION = {
    "ziganshin_multistatic_eucap25": (
        "A. Ziganshin et al., \"Ray-based simulation of multistatic scattering from target "
        "objects in ISAC,\" Proc. 19th European Conf. Antennas and Propagation (EuCAP), 2025, "
        "doi:10.23919/EuCAP63536.2025.10999367", "EuCAP 2025", "PUBLISHED", 2025,
        "Ziganshin, EuCAP'25"),
    "ziganshin_curved_arxiv26": (
        "A. Ziganshin et al., \"Ray-based simulation of scattering from discretized curved "
        "bodies,\" arXiv:2604.05991, 2026", "arXiv 2604.05991", "PREPRINT", 2026,
        "Ziganshin, arXiv'26"),
    "sagitta_sbr_po_arxiv26": (
        "Sagitta: GPU/MPI shooting-and-bouncing-rays RCS solver, arXiv:2604.09243, 2026",
        "arXiv 2604.09243", "PREPRINT", 2026, "Sagitta SBR, arXiv'26"),
    "kirik_ptd_sbr_sigma19": (
        "O. Kirik and O. Ozdemir, \"A compact PTD implementation for SBR-based RCS "
        "prediction (Predics),\" Sigma J. Eng. Nat. Sci., 2019", "Sigma J. Eng. Nat. Sci. 2019",
        "PUBLISHED", 2019, "Kirik, Sigma'19"),
    "lee_dynamic_rcs_jees21": (
        "Dynamic RCS of drone propellers by MoM, J. Electromagn. Eng. Sci. 21(4), 2021",
        "JEES 2021", "PUBLISHED", 2021, "Lee, JEES'21"),
    "rzewuski_nato21": (
        "S. Rzewuski et al., \"Drone detectability feasibility study using passive radars "
        "operating in WiFi and DVB-T band,\" NATO STO-MP-MSG-SET-183, 2021",
        "NATO STO 2021", "PUBLISHED", 2021, "Rzewuski, NATO'21"),
    "li_mdrt_icct25": (
        "C. Li et al., \"Micro-Doppler signature simulation of multirotor UAVs using ray "
        "tracing,\" Proc. IEEE ICCT, 2025, pp.359-364, doi:10.1109/ICCT67417.2025.11374154",
        "IEEE ICCT 2025", "PUBLISHED", 2025, "Li (md-rt), ICCT'25"),
    "clutteraware_procieee26": (
        "R. Liu, P. Li, M. Li, A. L. Swindlehurst, \"Clutter-aware integrated sensing and "
        "communication,\" Proc. IEEE 114(1), 2026", "Proc. IEEE 2026", "PUBLISHED", 2026,
        "Clutter-Aware ISAC, ProcIEEE'26"),
    "lambda_dataset_arxiv26": (
        "LAMBDA: a low-altitude multimodal base dataset for UAV sensing and communication, "
        "arXiv:2607.03826, 2026", "arXiv 2607.03826", "PREPRINT", 2026, "LAMBDA, arXiv'26"),
    "radartwin_arxiv26": (
        "RadarTwin: paired real-simulated mmWave radar dataset, arXiv:2606.28396, 2026",
        "arXiv 2606.28396", "PREPRINT", 2026, "RadarTwin, arXiv'26"),
    "greatx_arxiv25": (
        "Great-X: \"Unreal is all you need\" multimodal ISAC data simulation, "
        "arXiv:2507.08716, 2025", "arXiv 2507.08716", "PREPRINT", 2025, "Great-X, arXiv'25"),
    "fwa_cube_arxiv26": (
        "AI-empowered low-altitude economy: cooperative sensing with fixed wireless access, "
        "arXiv:2605.07623, 2026", "arXiv 2605.07623", "PREPRINT", 2026, "FWA cube, arXiv'26"),
    "cellsense_arxiv26": (
        "CellSense: cellular ISAC sensing prototype, arXiv:2606.07900, 2026",
        "arXiv 2606.07900", "PREPRINT", 2026, "CellSense, arXiv'26"),
    "dmsnet_arxiv26": (
        "DMSNet: cross-band learning for multi-target sensing in multi-band ISAC, "
        "arXiv:2607.17655, 2026", "arXiv 2607.17655", "PREPRINT", 2026, "DMSNet, arXiv'26"),
    "caviar_arxiv24": (
        "CAVIAR: co-simulation of 6G communications, 3D scenarios and AI, arXiv:2401.03310, "
        "2024", "arXiv 2401.03310", "PREPRINT", 2024, "CAVIAR, arXiv'24"),
    "wang_neural_isac_jsac25": (
        "Wang et al., neural ISAC MIMO-OFDM receiver, IEEE JSAC, to appear (arXiv:2509.21118)",
        "IEEE JSAC", "ACCEPTED_TO_APPEAR", 2025, "Wang, JSAC (to appear)"),
    "das_multiband_wcl26": (
        "Das et al., \"Multiband monostatic and bistatic RCS characterization of AAVs for "
        "ISAC channel modeling,\" IEEE Wireless Commun. Lett. 15, pp.3731-3735, 2026",
        "IEEE WCL 15:3731-3735", "PUBLISHED", 2026, "Das, WCL'26"),
    "zhang_unified_rcs_jsac26": (
        "Zhang et al., \"A unified RCS modeling of typical targets for 3GPP ISAC channel "
        "standardization,\" IEEE JSAC 44, 2026", "IEEE JSAC 2026", "PUBLISHED", 2026,
        "Zhang (3GPP RCS), JSAC'26"),
    #: ⭐ 게재판(JSTEAP)을 쓴다. reference_library 의 pdf_paths[0] 은 arXiv 판(2504.05168)이다.
    "costa_bistatic_md_jsteap25":
        "/data/public/sionna_jeong/papers_isac_sionna/paper_sionna_Ray_0723/"
        "Modeling_Micro-Doppler_Signature_of_Multi-Propeller_Drones_in_Distributed_ISAC.pdf",
    "semkin_drone_rcs_access20": (
        "V. Semkin et al., \"Analyzing radar cross section signatures of diverse drone models "
        "at mmWave frequencies,\" IEEE Access 8, 2020", "IEEE Access 2020", "PUBLISHED", 2020,
        "Semkin, Access'20"),
    "costa_bistatic_md_jsteap25": (
        "H. C. A. Costa, S. J. Myint, C. Andrich, S. W. Giehl, M. Engelhardt, C. Schneider, "
        "and R. S. Thoma, \"Modeling micro-Doppler signature of multi-propeller drones in "
        "distributed ISAC,\" IEEE J. Sel. Topics Electromagn. Antennas Propag. (JSTEAP), "
        "vol. 1, pp. 208-, 2025, doi:10.1109/JSTEAP.2025.3604407 (published 1 Sep 2025, CC BY 4.0)",
        "IEEE JSTEAP vol.1", "PUBLISHED", 2025, "Costa, JSTEAP'25"),
    "wei_rotor_md_twc25": (
        "J. Wei et al., \"UAV's rotor micro-Doppler feature extraction using ISAC signal,\" "
        "IEEE Trans. Wireless Commun. 24(12), 2025", "IEEE TWC 24(12)", "PUBLISHED", 2025,
        "Wei, TWC'25"),
    "abratkiewicz_ssb_jstars23": (
        "K. Abratkiewicz et al., \"SSB-based signal processing for passive radar using a 5G "
        "network,\" IEEE J. Sel. Topics Appl. Earth Observ. Remote Sens. 16, pp.3469-3484, "
        "2023, doi:10.1109/JSTARS.2023.3262291", "IEEE JSTARS 16:3469-3484", "PUBLISHED",
        2023, "Abratkiewicz, JSTARS'23"),
    "chen_rotating_applsci24": (
        "P. Chen, L. Tian, Y. Bai, J. Wang, \"Rotating target detection using commercial 5G "
        "signal,\" Applied Sciences 14(10):4282, 2024, doi:10.3390/app14104282",
        "Appl. Sci. 14(10):4282", "PUBLISHED", 2024, "Chen, Appl.Sci.'24"),
    "geng_lte_multistatic_ietrsn20": (
        "Geng et al., \"LTE-based multistatic passive radar system for UAV detection,\" "
        "IET Radar Sonar Navig. 14(7), 2020", "IET RSN 14(7)", "PUBLISHED", 2020,
        "Geng, IET RSN'20"),
    "jopanya_ssb_spawc25": (
        "Jopanya et al., \"Utilizing 5G NR SSB blocks for passive detection and localization "
        "of low-altitude drones,\" Proc. IEEE SPAWC, 2025", "IEEE SPAWC 2025", "PUBLISHED",
        2025, "Jopanya, SPAWC'25"),
    "ours": (
        "This work (sionna2): SBR on Sionna's Mitsuba ray engine + our PO surface integral",
        "unpublished", "IN PREPARATION", 2026, "OURS (sionna2)"),
}


def build_rows(scan, ours):
    """행별 셀. 인용문은 전부 이번 실행에서 연 PDF 에서 온 것이고 재대조를 받는다."""
    R = {}

    # ------------------------------------------------------------------ S 그룹
    R["ziganshin_multistatic_eucap25"] = dict(group="S", cells=dict(
        engine=C(2, "Sionna RT + author extension (UTD + vertex diffraction)",
                 quote="An open-source parallelizable framework, Sionna RT [11], is utilized to conduct simulations.",
                 loc="Sec. III"),
        mesh=C(2, "faceted vehicle mesh (3.3x2.1x1.7 m)",
               quote="An alternative approach, as mentioned before, is to dis- cretize the curved surface into flat and small polygons - usually triangles - called ”facets” and to apply conventional ray tracing techniques in combination with the Uniform Theory of Diffraction (UTD) under the assumption that facets are larger than the wavelength.",
               loc="Sec. I"),
        material=C(0, "PEC only, no per-part materials (the term appears in cited UTD titles)",
                   count=("material", "report")),
        aspect=C(2, "scattered field vs angle 0-180 deg",
                 quote="0 20 40 60 80 100 120 140 160 180 Angle (deg) 40 35 30 25 20 15 10 5 0 |Escat| (dBV/m) EM (MLFMM) RT+UTD RT+UTD+VD Fig.",
                 loc="Fig. (results)"),
        rotor=NA("vehicle target, no rotor", "mesh cell (quoted): faceted vehicle mesh"),
        diffraction=C(2, "UTD + vertex diffraction (the point of the paper)",
                      quote="We show that more comprehensive diffraction methods are required to achieve realistic results: one of them is vertex diffraction, and its implementation in the RT framework is considered in this work.",
                      loc="Abstract"),
        validation=C(2, "vs MLFMM (FEKO) and PO solvers",
                     quote="Simulations by thus augmented RT are compared with simulations by MLFMM and PO solvers for discretized spheres and a simplified car, respectively.",
                     loc="Abstract"),
        geometry=C(2, "multistatic (title)",
                   quote="Ray-Based Simulation of Multistatic Scattering from Target Objects in ISAC",
                   loc="Title, p.1"),
    ))

    R["ziganshin_curved_arxiv26"] = dict(group="S", cells=dict(
        engine=C(2, "Sionna-RT v0.19, extended by the authors",
                 quote="Consequently, reference RT tools, such as the open-source, parallelizable framework Sionna-RT [19] and other tools [20], naturally support faceted geometries.",
                 loc="Sec. I"),
        mesh=C(2, "faceted vehicle mesh; curvature-linked facet size rule",
               quote="A discretization strategy linking facet size to local curvature and wavelength is proposed to balance geometric fidelity, diffraction modeling, and efficiency.",
               loc="Abstract"),
        material=C(0, "PEC assumed for every object",
                   quote="All objects considered in this work are assumed to be perfectly electrically conducting (PEC), as vehicle bodies can often be approximated by PEC boundary conditions.",
                   loc="Sec. (geometry)"),
        aspect=C(2, "backscattering and forward/shadow region vs angle",
                 quote="This work investigates ray-tracing-based modeling of near-field scattering from curved bodies, both in the backscattering and in the forward (shadow) region",
                 loc="Abstract"),
        rotor=NA("vehicle target, no rotor", "material cell (quoted): PEC vehicle bodies"),
        diffraction=C(2, "UTD + vertex diffraction + double-bounce, heuristic edge/vertex combination",
                      quote="in the ray-tracing tool, diffraction is modeled according to the Uniform Theory of Diffraction (UTD), extended with vertex diffraction and double-bounce interactions",
                      loc="Abstract"),
        validation=C(2, "analytical solutions + full-wave; vehicle vs bistatic measurement",
                     quote="Validation is initially performed against analytical solutions and full-wave simulations for canonical geometries (sphere and circular cylinder).",
                     loc="Abstract"),
        geometry=C(2, "bistatic / multistatic near-field reflectivity",
                   quote="However, very few investigations have applied pure ray-based techniques to the multistatic solution of near-field reflectivity problems encountered in vehicular applications [12]–[14].",
                   loc="Sec. I"),
    ))

    R["sagitta_sbr_po_arxiv26"] = dict(group="S", cells=dict(
        engine=C(2, "own GPU(+MPI) SBR with BVH, not Sionna",
                 quote="This work targets that dominant bottleneck by accelerating ray–triangle intersection with a bounding volume hierarchy (BVH), a hierarchical spatial data structure that reduces intersection cost by culling large portions of the mesh using bounding boxes [12].",
                 loc="Sec. (method)"),
        mesh=C(2, "PEC sphere + complex aircraft geometry (triangle mesh)",
               quote="We validate against analytical Mie solutions for a per- fectly electrically conducting (PEC) sphere and demonstrate applicability to a complex aircraft geometry for monostatic radar cross-section prediction.",
               loc="Abstract"),
        material=C(0, "PEC only",
                   quote="Backscattering analysis for electrically large PEC objects (𝐷≫𝜆) necessitates asymptotic methods, as full- wave discretizations become computationally prohibitive.",
                   loc="Sec. 3"),
        aspect=C(2, "RCS pattern vs angle (null structure discussed)",
                 quote="If Δ𝑠is too large relative to the wavelength, the discrete sum undersamples the phase variation across the surface and produces nonphysical oscillations and incorrect null structure in the RCS pattern.",
                 loc="Sec. (accuracy)"),
        rotor=NA("aircraft/sphere target, no rotor", "mesh cell (quoted): PEC sphere + aircraft geometry"),
        diffraction=C(0, "explicitly absent; named as a known limitation",
                      quote="A known modeling limitation of classical GO+PO SBR is the absence of diffraction mechanisms, which can be important near edges, tips, or shadow boundaries.",
                      loc="Sec. (limitations)"),
        validation=C(2, "analytical Mie solution for a PEC sphere",
                     quote="We validate accuracy against analytical Mie solutions for a perfectly conducting sphere and demonstrate applicability to a complex aircraft configuration for monostatic radar cross-section prediction.",
                     loc="Abstract"),
        geometry=C(1, "monostatic only",
                   count=("geo", "report")),
    ))

    R["kirik_ptd_sbr_sigma19"] = dict(group="S", cells=dict(
        engine=C(2, "Predics: SBR (ray + field tracing), not Sionna",
                 quote="This PTD implementation is unique such a way that it is specially tailored to shooting and bouncing ray (SBR) technique via ray tracing and field tracing techniques.",
                 loc="Abstract"),
        mesh=C(2, "CAD benchmark targets; edges/wedges auto-detected from the CAD file",
               quote="Prior to PTD implementation, the edges and the wedges of the target’s CAD file should be identified.",
               loc="Sec. 2"),
        material=C(0, "PEC benchmark targets",
                   quote="For this purpose, a PEC plate of 15 cm x 15 cm is considered and the monostatic RCS simulation of horizontal polarization at 6 GHz was carried out at for the azimuth angles from -90° to 90° for a total of 361 discrete angle points.",
                   loc="Sec. 3"),
        aspect=C(2, "monostatic RCS over 361 azimuth points",
                 quote="the monostatic RCS simulation of horizontal polarization at 6 GHz was carried out at for the azimuth angles from -90° to 90° for a total of 361 discrete angle points",
                 loc="Sec. 3"),
        rotor=NA("canonical benchmark targets, no rotor", "material cell (quoted): 15 cm PEC plate etc."),
        diffraction=C(2, "PTD bolted onto SBR - the entire contribution",
                      quote="Therefore, there is a need for improving the accuracy of SBR tools with the addition of diffracted field calculation from the wedges of the simulated targets.",
                      loc="Sec. 1"),
        validation=C(2, "benchmark targets with analytical or measured RCS",
                     quote="The success and the validity of the proposed PTD implementation to the ray-launching RCS simulator have been tested with several benchmark targets that have either analytical or measured RCS values.",
                     loc="Abstract"),
        geometry=C(1, "monostatic",
                   count=("geo", "report")),
    ))

    R["lee_dynamic_rcs_jees21"] = dict(group="S", cells=dict(
        engine=C(2, "MoM full-wave solver (impedance matrix reused across rotation)",
                 quote="Therefore, using the relative angle between a rotating propeller and the incident field, mesh generation can be done just once along with the construction of the impedance and admittance matrices.",
                 loc="Sec. (method)"),
        mesh=C(1, "propeller CAD only - no airframe",
               quote="It is well known that the impedance matrix in the MoM is constructed from the interaction among the mesh elements of a scatterer.",
               loc="Sec. (method)"),
        material=C(0, "PEC assumed (carbon fiber approximated as PEC)",
                   quote="Because the dynamic RCSs of propellers with carbon fiber and a perfect electric conductor (PEC) are very similar in terms of RCS level and patterns [16, 17], the material of the propellers was simply assumed to be the PEC.",
                   loc="Sec. (model)"),
        aspect=C(2, "dynamic RCS over arbitrary azimuth angle",
                 quote="Dynamic RCS of Multiple Propellers in the Azimuth Plane Because a radar can be oriented in any direction, the RCS es- timation of multiple propellers for the arbitrary azimuth angle is needed.",
                 loc="Sec. (results)"),
        rotor=C(2, "rotation is the subject; rotation mapped onto incidence angle",
                quote="Instead of rotating the propeller, if the incident azimuth angle, 𝜙inc, is rotated in the direction opposite to the rotation direction of the propeller, thus keeping the incident elevation angle, 𝜃inc, fixed",
                loc="Sec. (method)"),
        validation=C(1, "full-wave MoM is itself the reference; no measurement comparison found",
                     count=("validation", "report")),
        geometry=C(1, "monostatic",
                   count=("geo", "report")),
    ))

    R["rzewuski_nato21"] = dict(group="S", cells=dict(
        engine=C(2, "QuickWave-3D FDTD (full-wave), outside any ray tracer",
                 computed="reference_library.json master_table.engine 및 참고문헌 [3] QuickWave-3D, QWED",
                 source="outputs/reference_library.json : rzewuski_nato21"),
        mesh=C(2, "EM model of a real Parrot AR.Drone 2.0 airframe",
               computed="reference_library.json target_representation: 실물 드론 + 그 드론의 EM 모델(폴리프로필렌 기체)",
               source="outputs/reference_library.json : rzewuski_nato21"),
        material=C(1, "polypropylene body stated, no per-part table found in the text layer",
                   count=("material", "zero")),
        aspect=C(0, "no aspect-resolved RCS pattern in the text layer",
                 count=("aspect", "zero")),
        rotor=C(0, "rotors named as the physics, not modelled",
                quote="The algorithms implemented in such a system must distinguish between UAV’s and birds and the most promising methods will be based on analyse of micro-doppler signature of a bird wings and rotor propelled drone/UAV.",
                loc="Sec. 1"),
        validation=C(1, "RCS estimation/measurement deferred to a companion paper",
                     quote="The details of the RCS estimation and measurement can be found in [4].",
                     loc="Sec. (RCS)"),
        geometry=C(2, "bistatic passive radar (WiFi and DVB-T)",
                   quote="Crossambiguity function (WIFI signal – duty factor 18%) with drone present during flight.",
                   loc="Fig. caption"),
    ))

    R["li_mdrt_icct25"] = dict(group="S", cells=dict(
        engine=C(2, "Sionna RT with conical (not spherical) ray sampling",
                 quote="In this study, the Sionna RT module is used to construct various simulation scenarios and obtain Channel State Information (CSI) data for analysis.",
                 loc="Sec. III"),
        mesh=C(1, "one propeller (2 blades) in Blender - no airframe",
               quote="The target consists of either Sionna’s built-in reflector model or a physical model of a propeller modeled using Blender.",
               loc="Sec. III"),
        material=C(1, "single material 'Wood', Sionna built-in EM parameters",
                   quote="The model’s coordinates are located at its geometric center, and electromagnetic parameters such as conductivity are based on Sionna’s built-in settings.",
                   loc="Sec. III"),
        aspect=C(1, "azimuth-angle effect on the micro-Doppler signature, not on RCS level",
                 quote="We focus on analyzing the impact of azimuth angle and carrier frequency f on the Micro-Doppler signatures generated by the rotor.",
                 loc="Sec. IV"),
        rotor=C(2, "rotor rotation is the subject of the paper",
                quote="The feasibility of using Sionna RT to simulate micro-Doppler effects induced by UAV rotor motion is validated.",
                loc="Sec. I (contributions)"),
        validation=C(0, "kinematics only - ridge position vs its own closed form; no amplitude",
                     count=("dbsm", "zero"),
                     note="이전 정독(reference_library intersection X01)과 이번 계수가 일치한다."),
        geometry=C(1, "monostatic (Tx and Rx at the same origin)",
                   computed="monostatic/bistatic 언급은 참고문헌 제목뿐; 기하는 본문 'transmitter and receiver remain stationary at origin Q'",
                   source="outputs/reference_library.json : intersection X01 quotes"),
    ))

    R["clutteraware_procieee26"] = dict(group="S", cells=dict(
        engine=C(2, "NVIDIA Sionna RT, interaction depth 3",
                 quote="The maximum interaction depth for Sionna is set to three, so each ray undergoes at most three interactions with scene objects.",
                 loc="Sec. (site-specific)"),
        mesh=C(2, "simplified 3-D UAV meshes imported into Sionna",
               quote="The ToI and UAVs are modeled as simplified 3D mesh objects imported into Sionna.",
               loc="Sec. (site-specific)"),
        material=C(2, "flexible per-object material assignment via Sionna XML",
                   quote="These meshes are obtained by simplifying publicly available 3D models in Blender and exporting them in Sionna’s XML format, which keeps the ray-tracing scene lightweight while enabling flexible material assignment.",
                   loc="Sec. (site-specific)"),
        aspect=C(1, "azimuth-only far-field specialization of the reflectivity",
                 quote="For simplicity, we will specialize to the far-field, single-polarization, azimuth- only case in which ϑ reduces to the scalar θ, representing the azimuth angle.",
                 loc="Sec. (model)"),
        rotor=C(0, "no rotor model (the words appear, the model does not)",
                count=("rotor", "report")),
        diffraction=C(0, "diffraction named, no diffraction model (no UTD/PTD/GTD/wedge)",
                      count=("diff", "report")),
        validation=C(0, "no amplitude validation at all - the word 'validat*' never appears",
                     count=("validation", "zero"),
                     note="이전 라운드에서 직접 셌고(reference_library intersection X02) 이번 계수도 같다."),
        geometry=C(1, "monostatic developed; bistatic/multistatic as a remark",
                   quote="The same for- mulation extends to bistatic and multistatic operation when the illuminator and the sensing receiver are at different locations.",
                   loc="Remark 1"),
    ))

    R["lambda_dataset_arxiv26"] = dict(group="S", cells=dict(
        engine=C(1, "Sionna RT for propagation; UAV scattering from CADFEKO (injected)",
                 quote="In the RF channel and radar branch, the same UE5 assets are exported through Blender, converted into radio-scene meshes, assigned elec- tromagnetic material properties, and imported into Sionna RT for ray tracing and CSI generation.",
                 loc="Sec. (pipeline)"),
        mesh=C(2, "AirSim/UE5 UAV 3-D model exported as a radio-scene mesh",
               quote="UE5 scene assets are exported through Blender, assigned customized electromagnetic material properties, and then imported into Sionna RT.",
               loc="Sec. (pipeline)"),
        material=C(2, "customized EM material properties per scene object",
                   quote="It is generated through a high-fidelity digital-twin pipeline with detailed scene geometry, refined material assignment, and electromag- netic modeling of UAVs.",
                   loc="Abstract"),
        aspect=C(1, "UAV reflection characteristics modelled externally; no aspect cut shown",
                 count=("aspect", "zero")),
        rotor=C(0, "no rotor model",
                count=("rotor", "zero")),
        validation=C(0, "dataset-level validation only, no EM amplitude reference",
                     count=("validation", "report")),
        geometry=C(0, "geometry configuration not stated",
                   count=("geo", "report")),
    ))

    R["radartwin_arxiv26"] = dict(group="S", cells=dict(
        engine=C(2, "Mitsuba 3 (CUDA) + RF-Genesis pipeline, Fresnel, 4 bounces",
                 quote="The simulator builds on Mitsuba 3 [16] (cuda_ad_rgb variant, CUDA backend) and the RF-Genesis ray-tracing pipeline [6], with material physics replaced to follow ITU-R P.2040-4 [15] on a per-surface basis.",
                 loc="Sec. (simulator)"),
        mesh=C(2, "reconstructed real scene meshes (household objects)",
               quote="Rays are cast once from the sensor position and Fresnel reflection is evaluated at every ray-surface intersection, recursing up to four bounces. The four-bounce limit is validated empirically",
               loc="Sec. (simulator)"),
        material=C(2, "ITU-R P.2040-4 per-surface material physics",
                   quote="with material physics replaced to follow ITU-R P.2040-4 [15] on a per-surface basis",
                   loc="Sec. (simulator)"),
        aspect=C(2, "360-degree rotation sweep exposes shape via angular harmonics",
                 quote="Rotation sweeps the full 360◦aspect angle and exposes shape through the low-order angular harmonic ratio of the rotation enve- lope.",
                 loc="Sec. (dataset)"),
        rotor=NA("household objects, not drones", "aspect cell (quoted): rotation sweep of cans/objects"),
        validation=C(1, "paired real-vs-simulated measurement, but no absolute RCS anchor",
                     quote="The simulator sees the full mesh and can introduce a size-brightness trend that the real radar does not measure.",
                     loc="Sec. (findings)",
                     note="⚠ reference_library.json 에 실린 같은 문장은 끝이 'that the real system "
                          "cannot resolve' 로 적혀 있었다 — 원문과 다르다. 이번 재대조에서 잡아 고쳤다."),
        geometry=C(1, "monostatic mmWave radar; angular response synthesized analytically",
                   quote="Each scatterer contributes its array-geometry phase offset per virtual channel, so the angular response is preserved analytically rather than by multistatic tracing.",
                   loc="Sec. (simulator)"),
    ))

    R["greatx_arxiv25"] = dict(group="S", cells=dict(
        engine=C(1, "Sionna RT re-implemented inside Unreal Engine (not Sionna itself)",
                 quote="This single-engine multimodal data twin platform reconstructs the ray-tracing computation of Sionna within Unreal Engine and is deeply integrated with autonomous driving tools.",
                 loc="Abstract"),
        mesh=C(2, "realistic 3-D UAV models from Unreal assets",
               computed="reference_library.json target_representation: 'Realistic 3D UAV models in Great-X' (Fig.1a)",
               source="outputs/reference_library.json : greatx_arxiv25"),
        material=C(1, "ITU parameter definitions for non-magnetic dielectrics; no per-part UAV table",
                   quote="For analysis, this paper assumes that both media are uniform and non-magnetic dielectrics and adopts the parameter definitions in ITU recommendations [14].",
                   loc="Sec. (propagation model)",
                   note="⚠ 이 칸은 처음에 '재질 언급 없음(레벨 0)' 으로 적었다가 이번 실행의 용어 계수가 "
                        "1 을 돌려주어 원문을 다시 열고 고쳤다 - 계수 검사가 잡아낸 오류다."),
        aspect=C(0, "no aspect-resolved RCS",
                 count=("aspect", "zero")),
        rotor=C(0, "no rotor model",
                count=("rotor", "zero")),
        validation=C(0, "cross-platform positioning error only, not amplitude",
                     quote="To assess the effectiveness of the simulation platform, we conducted a bidirectional cross-platform evaluation between Great-X and SionnaRT.",
                     loc="Sec. (evaluation)"),
        geometry=C(0, "geometry configuration not stated",
                   count=("geo", "report")),
    ))

    # ------------------------------------------------------------------ T 그룹
    R["fwa_cube_arxiv26"] = dict(group="T", cells=dict(
        engine=C(1, "Sionna RT PathSolver (propagation paths, no scattering integral)",
                 computed="reference_library.json engine 필드 + 인용문(경로 유형 라벨을 Sionna 가 준다)",
                 source="outputs/reference_library.json : fwa_cube_arxiv26"),
        mesh=C(0, "UAV replaced by a metallic cube",
               computed="reference_library.json quote: 'The UAV is modeled as a metallic cube located at p = (x, y, 60)'",
               source="outputs/reference_library.json : fwa_cube_arxiv26"),
        material=C(0, "'metallic' only, no material table",
                   count=("material", "zero")),
        aspect=C(0, "no aspect dependence (a cube stands in for the airframe)",
                 count=("aspect", "zero")),
        rotor=C(0, "no rotor",
                count=("rotor", "zero")),
        validation=C(0, "labels come from Sionna's own path types, not from an EM reference",
                     computed="reference_library.json validated 필드: 경로 유형(확산 반사) 자체가 라벨",
                     source="outputs/reference_library.json : fwa_cube_arxiv26"),
        geometry=C(1, "monostatic-ish cooperative FWA links",
                   count=("geo", "report")),
    ))

    R["cellsense_arxiv26"] = dict(group="T", cells=dict(
        engine=C(1, "Sionna-based OFDM link-level simulation of a Blender scene",
                 computed="reference_library.json engine 필드; 표적은 사람 큐보이드",
                 source="outputs/reference_library.json : cellsense_arxiv26"),
        mesh=C(0, "1.8 x 0.5 x 0.25 m cuboid standing in for a human (not a drone)",
               computed="reference_library.json quote: 'we model a mobile object as a 1.8 m x 0.5 m x 0.25 m cuboid'",
               source="outputs/reference_library.json : cellsense_arxiv26"),
        material=C(0, "no material statement in the text layer",
                   count=("material", "zero")),
        aspect=C(0, "no aspect-resolved RCS", count=("aspect", "zero")),
        rotor=NA("human target, no rotor", "mesh cell (computed): 1.8x0.5x0.25 m human cuboid"),
        validation=C(0, "Pd/Pfa against a baseline method, not an amplitude reference",
                     computed="reference_library.json validated: Pd 0.74 / Pfa 0.10 vs baseline",
                     source="outputs/reference_library.json : cellsense_arxiv26"),
        geometry=C(1, "bistatic BS-UE focal ellipse",
                   count=("geo", "report")),
    ))

    R["dmsnet_arxiv26"] = dict(group="T", cells=dict(
        engine=C(1, "Sionna RT used to generate a dual-band dataset",
                 computed="reference_library.json quote: dual-band UAV sensing dataset generated in a 1:1 digital twin using Sionna RT",
                 source="outputs/reference_library.json : dmsnet_arxiv26"),
        mesh=C(0, "target representation never stated; signal model uses a complex coefficient",
               computed="reference_library.json target_representation: 표적은 (r,v,theta) + 복소 산란계수 rho, RCS = |rho|^2",
               source="outputs/reference_library.json : dmsnet_arxiv26"),
        material=C(0, "no material statement", count=("material", "zero")),
        aspect=C(0, "no aspect dependence", count=("aspect", "zero")),
        rotor=C(0, "no rotor", count=("rotor", "zero")),
        validation=C(0, "detection/estimation benchmarks only",
                     computed="reference_library.json validated: EM 검증 없음, 개수추정 정확도 벤치마크",
                     source="outputs/reference_library.json : dmsnet_arxiv26"),
        geometry=C(0, "geometry configuration not stated",
                   count=("geo", "report")),
    ))

    R["caviar_arxiv24"] = dict(group="T", cells=dict(
        engine=C(1, "Sionna (RT + link/PHY) inside an AirSim co-simulation",
                 computed="reference_library.json quote: each UAV instantiated as a receiver in Sionna",
                 source="outputs/reference_library.json : caviar_arxiv24"),
        mesh=C(1, "drone mesh present but decimated, and it is a terminal, not a target",
               computed="reference_library.json quote: version used in Sionna does not use textures and underwent decimation in Blender",
               source="outputs/reference_library.json : caviar_arxiv24"),
        material=C(1, "ITU metal assigned to the drone (single material)",
                   computed="reference_library.json quote (Table V): 'Radio material (drone) ITU metal'",
                   source="outputs/reference_library.json : caviar_arxiv24"),
        aspect=C(0, "no aspect-resolved RCS", count=("aspect", "zero")),
        rotor=C(0, "no rotor", count=("rotor", "zero")),
        validation=C(0, "beam-selection / mission performance, no scattering amplitude",
                     computed="reference_library.json validated: 빔 선택 정확도, RCS 0회",
                     source="outputs/reference_library.json : caviar_arxiv24"),
        geometry=C(0, "geometry configuration not stated",
                   count=("geo", "report")),
    ))

    R["wang_neural_isac_jsac25"] = dict(group="T", cells=dict(
        engine=C(1, "NVIDIA Sionna generates CIRs; detection is learned",
                 computed="reference_library.json quote: Sionna scene seed including material properties and shape information of the targets",
                 source="outputs/reference_library.json : wang_neural_isac_jsac25"),
        mesh=C(1, "Blender scene seed exported as XML with shape information",
               computed="reference_library.json target_representation: 메시(재질+형상 정보가 붙는다)",
               source="outputs/reference_library.json : wang_neural_isac_jsac25"),
        material=C(1, "material properties in the scene seed, no per-part drone table",
                   computed="reference_library.json quote 동일 문장",
                   source="outputs/reference_library.json : wang_neural_isac_jsac25"),
        aspect=C(0, "no aspect-resolved RCS", count=("aspect", "zero")),
        rotor=C(0, "no rotor", count=("rotor", "zero")),
        diffraction=C(1, "diffraction claimed as included in CIR generation, no model given",
                      quote="The reﬂection, scattering, and diffraction effects are considered in CIR generation.",
                      loc="Sec. (simulation)"),
        validation=C(0, "joint sensing/communication performance, not amplitude",
                     computed="reference_library.json validated 필드",
                     source="outputs/reference_library.json : wang_neural_isac_jsac25"),
        geometry=C(0, "geometry configuration not developed",
                   count=("geo", "report")),
    ))

    # ------------------------------------------------------------------ M 그룹
    R["das_multiband_wcl26"] = dict(group="M", cells=dict(
        engine=NA("measurement (anechoic turntable), no ray engine", "aspect cell (quoted): turntable S21 measurement"),
        mesh=NA("real airframes, no mesh", "aspect cell (quoted): the AAV is mounted on the turntable"),
        material=C(1, "material response inherent in the measurement, not modelled",
                   quote="The lower bistatic values are likely due to directional scattering, reduced specular contributions, and aspect-dependent structural and material responses of the AAV, although isolating the contribution of each factor remains challenging.",
                   loc="Sec. (results)"),
        aspect=C(2, "azimuth phi swept for each bistatic angle theta_b",
                 quote="Target measurement: The AAV is mounted on the turntable, and its response SDUT 21 (θb, f, φ) is measured for each azimuth angle φ and bistatic angle θb.",
                 loc="Sec. II"),
        rotor=C(0, "rotor micro-Doppler explicitly excluded",
                quote="This effect is not considered here because the proposed model focuses on RCS amplitude statistics, while the measurement system provides quasi- static AAV backscatter characterization and does not resolve rotor-induced micro-Doppler [6], [8].",
                loc="Sec. (model)"),
        diffraction=NA("measurement - no EM model to carry diffraction", "engine cell: measurement only"),
        validation=C(2, "this IS the measurement anchor (calibrated, dBsm reported)",
                     quote="Furthermore, a measurement-validated Gaussian-cluster representation is proposed as a geometry-based stochastic model to reproduce angular AAV RCS fluctuations in ISAC channel simulations.",
                     loc="Abstract"),
        geometry=C(2, "monostatic AND bistatic in one campaign",
                   quote="Since RCS is strongly aspect-dependent, ISAC channel models should account for both monostatic and bistatic configurations [1], [2].",
                   loc="Sec. I"),
    ))

    R["zhang_unified_rcs_jsac26"] = dict(group="M", cells=dict(
        engine=NA("measurement + a fitted unified RCS model, no ray engine", "validation cell (quoted): sphere calibration measurement"),
        mesh=NA("real DJI M350, human and vehicle", "validation cell (quoted): measured targets"),
        material=C(1, "material discussed as a high-frequency-method issue, not per-part",
                   quote="High-frequency methods such as physical optics (PO) [20], geometric optics (GO) [21], and the physical theory of diffraction (PTD) [22] provide approximate solutions with reduced computational complexity but sacrifice accuracy and require corrections for specific scenarios.",
                   loc="Sec. II"),
        aspect=C(2, "aspect-resolved RCS at 10/15/20/28/36 GHz",
                 computed="reference_library.json headline_numbers.frequencies_GHz + aspect 문장 8건",
                 source="outputs/reference_library.json : zhang_unified_rcs_jsac26"),
        rotor=C(0, "rotor arms described geometrically; no rotation model",
                count=("rotor", "report")),
        diffraction=C(0, "PTD cited as prior art only, not used in the model",
                      count=("diff", "report")),
        validation=C(2, "0.5 m metal sphere: theory -7.07 dBsm vs measured -8.96 dBsm",
                     quote="RCS is -7.07 dBsm, while the measured average is -8.96 dBsm, with a discrepancy of less than 2 dBsm, confirming the high accuracy of the measurements.",
                     loc="Sec. (calibration)"),
        geometry=C(1, "monostatic dominant (bistatic mentioned)",
                   count=("geo", "report")),
    ))

    R["semkin_drone_rcs_access20"] = dict(group="M", cells=dict(
        engine=C(1, "measurement + CST (ray tracing for the calibration cuboid, "
                 "Integral Equation solver for drone parts)",
                 quote="To demonstrate the validity of the measurement setup, the RCS of an identical cuboid was calculated via electromagnetic simulations in the CST Microwave Studio ray tracing tool.",
                 loc="Sec. (measurement setup)",
                 note="부품별 기여 추정은 같은 논문의 CST Integral Equation solver 절에서 나온다."),
        mesh=NA("9 real airframes, no mesh of our own", "material cell (quoted): measured drone groups"),
        material=C(2, "CFRP vs plastic split is the paper's headline (7 dB)",
                   quote="Mean RCS values of Group II are roughly 7 dB higher than those of Group I. This is predictable, since drones from Group II are mostly made of carbon fiber reinforced polymer material (CFRP)",
                   loc="Sec. (results)"),
        aspect=C(2, "monostatic RCS vs azimuth AND elevation; spread sigma about 6 dB",
                 quote="Monostatic RCS of drones from Group II, with respect to the azimuth and elevation angles.",
                 loc="Fig. caption"),
        rotor=C(0, "static measurement - rotors present but not turning",
                count=("rotor", "report")),
        diffraction=NA("measurement campaign - diffraction not a modelling choice here", "engine cell (quoted): CST used only for the calibration cuboid / parts"),
        validation=C(2, "measurement vs CST ray tracing of the same geometry",
                     computed="reference_library.json validated: 최대 10.2 dBsm 지점에서 일치, 정반사 밖에서는 점근 솔버 탓에 차이",
                     source="outputs/reference_library.json : semkin_drone_rcs_access20"),
        geometry=C(1, "monostatic 26-40 GHz",
                   count=("geo", "report")),
    ))

    R["costa_bistatic_md_jsteap25"] = dict(group="M", cells=dict(
        engine=C(1, "analytic thin-wire scatterer model + BiRa measurement",
                 quote="We proposed the model of a single propeller in [35], that assumes each pro- peller blade behaving as a thin-wire scatterer with negligible thickness and uniform material properties.",
                 loc="Sec. (model)"),
        mesh=C(0, "no mesh - blades are thin wires, body is a simplified reflectivity",
               quote="This is clearly a simplification, as real drone bodies exhibit intricate reflectivity patterns that depend on the shape, material and aspect angle.",
               loc="Sec. (model)"),
        material=C(0, "uniform material properties assumed",
                   quote="This provides a computationally efficient approximation, though real-world blades exhibit material-dependent scattering effects that are not captured.",
                   loc="Sec. (model)"),
        aspect=C(1, "aspect dependence named as the thing the model does not capture",
                 quote="This is clearly a simplification, as real drone bodies exhibit intricate reflectivity patterns that depend on the shape, material and aspect angle.",
                 loc="Sec. (model)"),
        rotor=C(2, "multi-propeller bistatic micro-Doppler is the paper",
                quote="To address this gap, this work introduces an OFDM- based bistatic micro-Doppler model for multi-propeller drones.",
                loc="Abstract"),
        diffraction=C(0, "diffraction explicitly not taken into account",
                      quote="Compared to these methods, the proposed model tends to be less accurate since it does not take into account some EM phenomena, such as diffraction and multipath.",
                      note="⚠ arXiv 판(2504.05168)은 같은 문장을 'some electromagnetic phenomena' 로 "
                           "적는다. 여기 인용은 게재판(JSTEAP) 문장이다 - 판본을 섞지 말 것.",
                      loc="Sec. (model)"),
        validation=C(1, "BiRa measurement gives ground truth for the signature, not for sigma",
                     quote="Measurements were performed to collect ground truth data for verification of the proposed model.",
                     loc="Sec. (measurement)"),
        geometry=C(2, "bistatic (74 mentions) in a distributed ISAC setting",
                   count=("geo", "report")),
    ))

    R["wei_rotor_md_twc25"] = dict(group="M", cells=dict(
        engine=C(1, "analytic echo model with time-varying RCS + ISAC testbed",
                 quote="This expression accounts for the time-varying radar cross section (RCS) induced by the UAV’s rotor rotation, which leads to periodic variations in rotor echo intensity.",
                 loc="Sec. II"),
        mesh=C(0, "no geometry - rotor echo is analytic",
               count=("mesh", "zero")),
        material=C(0, "no material model", count=("material", "zero")),
        aspect=C(0, "no aspect-resolved RCS", count=("aspect", "zero")),
        rotor=C(2, "rotor micro-Doppler extraction is the entire paper (rmD-NSP + SET)",
                quote="A new mathematical model for UAV micro-Doppler in monostatic ISAC systems is proposed.",
                loc="Sec. I (contributions)"),
        diffraction=C(0, "no diffraction (GTD appears once, in a reference title)",
                      count=("diff", "report")),
        validation=C(1, "testbed evaluation of the extracted signature, not of amplitude",
                     count=("validation", "report")),
        geometry=C(1, "monostatic ISAC",
                   quote="A new mathematical model for UAV micro-Doppler in monostatic ISAC systems is proposed.",
                   loc="Sec. I"),
        vmax=C(0, "the word 'unambiguous' appears once, about features - not a velocity limit",
               quote="In this sensing mode, the extracted micro-Doppler features are unambiguous.",
               loc="Sec. (sensing mode)",
               note="⚠ 자동 계수만 보면 '무모호 언급 1회' 라 부분점수가 붙는다. 원문을 열어보면 "
                    "속도 모호성이 아니라 특징의 모호성 얘기다 - 수동으로 0 으로 내렸다."),
    ))

    # ------------------------------------------------------------------ V 그룹
    R["abratkiewicz_ssb_jstars23"] = dict(group="V", cells=dict(
        engine=NA("measurement + signal processing (USRP X310), no ray engine", "geometry cell: USRP X310 field measurement"),
        mesh=NA("target was a car (Volvo XC90), no mesh", "outputs/verify_chen.json A9 quote"),
        material=NA("no EM model in the paper", "outputs/verify_chen.json: abratkiewicz2023_DID_NOT"),
        aspect=C(0, "no aspect-resolved RCS", computed="산란 계산 자체가 없다",
                 source="outputs/verify_chen.json : what_they_did_and_did_not"),
        rotor=C(0, "no rotor; drones left as future work",
                computed="결론에서 드론을 future work 로 남긴다(A10)",
                source="outputs/verify_chen.json : quotes_abratkiewicz2023"),
        diffraction=NA("no EM model", "outputs/verify_chen.json: no electromagnetic simulation"),
        validation=NA("no scattering amplitude to validate", "outputs/verify_chen.json: no RCS computed"),
        geometry=C(2, "passive bistatic 5G, GPS-synchronized",
                   count=("geo", "report")),
        vmax=C(2, "eq.(16): Vb in [-lambda/(4T), +lambda/(4T)] - THE prior art for our law",
               quote="The Doppler range is limited by T",
               loc="Sec. IV, eq. (16), p.3476",
               note="⭐ 이 식이 우리 v_max = lambda*PRF/4 의 1차 출처다. 2023년 출판. "
                    "⚠ 같은 논문 eq.(18) 은 전폭 lambda/2T 를 Vmax 라 부른다 - 규약 이중성."),
    ))

    R["chen_rotating_applsci24"] = dict(group="V", cells=dict(
        engine=NA("measurement (5G lab gNB + commercial gNB), no ray engine", "outputs/verify_chen.json C6/C7 quotes"),
        mesh=NA("stepper-motor rotating model, not a drone", "outputs/verify_chen.json: chen2024_DID_NOT"),
        material=NA("no EM model in the paper", "outputs/verify_chen.json: chen2024_DID_NOT"),
        aspect=C(0, "no aspect-resolved RCS", computed="RCS/전자기 산란 계산이 없다",
                 source="outputs/verify_chen.json : what_they_did_and_did_not"),
        rotor=C(1, "rotating target echo model; drone rotors are motivation only",
                computed="표적은 스테퍼 모터 회전 모형; 드론 로터는 초록/서론의 동기",
                source="outputs/verify_chen.json : what_they_did_and_did_not"),
        diffraction=NA("no EM model", "outputs/verify_chen.json: no RCS/EM scattering computation"),
        validation=NA("no scattering amplitude to validate", "outputs/verify_chen.json: chen2024_DID_NOT"),
        geometry=C(2, "passive bistatic with CSI-RS, 4.5 m baseline",
                   computed="bistatic Doppler eq.(4) f_d=(2v/lambda)cos(beta/2)cos(delta)",
                   source="outputs/verify_chen.json : quotes_chen2024 C1"),
        vmax=C(1, "numeric instantiation only - NO closed form is displayed",
               computed="⭐ 우리 기록 정정: Chen 은 닫힌 식을 표시하지 않는다. 20 ms -> 50 Hz -> "
                        "[-25,25] Hz -> 0.56 rps 라는 수치 대입뿐이다.",
               source="outputs/verify_chen.json : what_they_did_and_did_not.chen2024_DID_NOT"),
    ))

    R["geng_lte_multistatic_ietrsn20"] = dict(group="V", cells=dict(
        engine=NA("ambiguity-function simulation, no ray engine", "mesh cell: UAV is a simulated point target"),
        mesh=C(0, "UAV is a simulated point target", computed="산란 계산 없음(모호함수 해석)",
               source="outputs/reference_library.json : geng_lte_multistatic_ietrsn20"),
        material=NA("no EM model", "mesh cell: point target"),
        aspect=C(0, "no aspect dependence", count=("aspect", "zero")),
        rotor=C(0, "no rotor", count=("rotor", "zero")),
        diffraction=NA("no EM model", "mesh cell: point target"),
        validation=NA("no scattering amplitude to validate", "mesh cell: point target"),
        geometry=C(2, "LTE multistatic passive radar",
                   count=("geo", "report")),
        vmax=C(2, "maximum unambiguous velocity reported explicitly (2647 m/s at 10 ms)",
               quote="10 ms), the maximum unambiguous velocity (MUV) is 2647 m/s and the velocity resolution is 18 m/s (i.",
               loc="Sec. (waveform analysis)"),
    ))

    R["jopanya_ssb_spawc25"] = dict(group="V", cells=dict(
        engine=NA("point-target simulation + CRB, no ray engine", "mesh cell: simulated point target"),
        mesh=C(0, "simulated point target", computed="표적은 점표적, 2D-FFT 추정기를 CRB 와 비교",
               source="outputs/reference_library.json : jopanya_ssb_spawc25"),
        material=NA("no EM model", "mesh cell: point target"),
        aspect=C(0, "no aspect dependence", count=("aspect", "zero")),
        rotor=C(0, "no rotor", count=("rotor", "zero")),
        diffraction=NA("no EM model", "mesh cell: point target"),
        validation=NA("no scattering amplitude to validate", "mesh cell: point target"),
        geometry=C(2, "passive bistatic 5G SSB",
                   count=("geo", "report")),
        vmax=C(2, "unambiguous velocity written as a closed form",
               quote="The unambiguous velocity is the range of maximum and minimum relative radial velocities, which can be defined as |𝑣u| ≤𝜆𝑐𝑓Δ/2.",
               loc="Sec. II"),
    ))

    # ------------------------------------------------------------------ O 그룹 (우리)
    R["ours"] = dict(group="O", cells=ours)
    return R


# =========================================================================== #
#  4. 우리 행 — 전부 디스크의 JSON/소스에서 실행 시점에 읽는다
# =========================================================================== #
def _read_json(name):
    p = os.path.join(OUT, name)
    with open(p, encoding="utf-8") as f:
        return json.load(f), os.path.relpath(p, _ROOT)


def build_our_row():
    kr, kr_src = _read_json("sbr_kr_sweep.json")
    sa, sa_src = _read_json("sigma_anchor.json")
    gg, gg_src = _read_json("geometry_grid.json")
    cf, cf_src = _read_json("verify_cfar.json")

    max_db = kr["summary_div16"]["max_abs_db_vs_po"]
    n_inc = kr["meta"]["n_incidence"]
    krmin, krmax = kr["summary_div16"]["kr_min"], kr["summary_div16"]["kr_max"]

    # 앵커: 레벨 이동 0.00 dB (기울기만 측정에서 받는다)
    exps = sa["our_kernel_size_exponent"]["by_band"]
    das_slope = sa["anchor_sensitivity"]["das_phantom3_mono"]["slope_db_per_ghz"]
    yuan_slope = sa["anchor_sensitivity"]["yuan_phantom3_azplane"]["slope_db_per_ghz"]

    # 우리 커널에 회절이 있는가 — 소스를 직접 센다
    diff_hits = 0
    kernel_files = []
    for fn in ("rcs_sbr.py", "rcs_po.py"):
        p = os.path.join(_ROOT, "src", fn)
        kernel_files.append("src/" + fn)
        if os.path.exists(p):
            src = open(p, encoding="utf-8").read()
            # 주석/독스트링의 'PTD 를 넣는다'(향후 과제) 는 코드가 아니다 -> 함수 정의만 센다
            diff_hits += len(re.findall(r"def\s+\w*(?:ptd|utd|diffract|wedge)\w*\s*\(",
                                        src, re.IGNORECASE))

    cpi = cf["meta"]["runtime_s"]
    phi_head = gg["headline"]

    # 재질표는 하드코딩하지 않고 소스에서 직접 읽는다 (이름이 바뀌면 여기서 터진다)
    sys.path.insert(0, os.path.join(_ROOT, "src"))
    import drones as _DR
    _g = _DR.drone_gamma_map(_DR.DRONES["mavic4pro"])
    gamma_txt = ", ".join("%s %.2f" % (k, v) for k, v in sorted(_g.items()))
    n_drones = len(_DR.DRONES)
    n_groups = len(_g)

    cells = dict(
        engine=C(2, "SBR on Sionna's Mitsuba ray engine + our PO surface integral",
                 computed="src/rcs_sbr.py - Mitsuba 광선이 맞은 지점에서 PO 표면적분. "
                          "Sionna 기본 PathSolver 에는 산란적분 단계가 없다(benchmark/verify_rt_no_rcs.py).",
                 source="src/rcs_sbr.py · benchmark/verify_rt_no_rcs.py"),
        mesh=C(2, "%d whole drone airframes, %d per-part groups incl. internal scatterers"
               % (n_drones, n_groups),
               computed="src/drones.py DRONES 에 기체 %d종, drone_gamma_map 이 돌려주는 부위 그룹 "
                        "%d개(%s). 전부 이번 실행에서 소스를 import 해 센 값이다."
                        % (n_drones, n_groups, ", ".join(sorted(_g))),
               source="src/drones.py : DRONES · build_frame"),
        material=C(2, "per-part |Gamma| derived from materials.MATERIALS: %s" % gamma_txt,
                   computed="src/drones.py drone_gamma_map() 를 이번 실행에서 직접 호출해 얻은 "
                            "그룹별 PO 진폭 반사계수다(하드코딩 아님). Sionna 와 같은 재질표에서 "
                            "유도된다. 전부 PEC 로 두면 플라스틱 셸 기여가 과대계상된다.",
                   source="src/drones.py : drone_gamma_map · src/materials.py : MATERIALS"),
        aspect=C(2, "sigma(phi, theta) per airframe per band; size exponent %.2f-%.2f"
                 % (min(v["exponent"] for v in exps.values()),
                    max(v["exponent"] for v in exps.values())),
                 computed="outputs/sigma_anchor.json our_kernel_size_exponent.by_band",
                 source=sa_src),
        rotor=C(0, "code exists but DEMOTED to future work - excluded from the reports",
                computed="docs/PAPER_DRAFT.md N12: 마이크로도플러는 리포트에서 제외(코드 보존). "
                         "자체 검증 수단이 없고 Costa(JSTSP, 게재)가 해석 경로를 이미 갖는다.",
                source="docs/PAPER_DRAFT.md : N12 · src/microdoppler.py"),
        diffraction=C(0, "NONE - no PTD, no UTD, no creeping wave. THIS IS OUR GAP.",
                      computed="src/rcs_sbr.py + src/rcs_po.py 안에 회절 함수 정의 %d개. "
                               "결과: 우리 밴드 기울기 +0.96~+1.40 dB/GHz 대 실측 %.3f(Das) / %.3f(Yuan) "
                               "dB/GHz - 3~8배 가파르다. PO 면적분만으로는 A^2/lambda^2(~f^2)로 스케일하고, "
                               "엣지 회절항이 저주파를 들어올려 기울기를 완만하게 만드는 물리가 빠져 있다."
                               % (diff_hits, das_slope, yuan_slope),
                      source=sa_src + " · docs/AUDIT_FINDINGS_0722.md:348-351 · " + " · ".join(kernel_files)),
        validation=C(1, "analytic PO sphere to %.4f dB (kr %g-%g, %d incidence dirs); "
                     "NOT measurement-anchored in absolute level"
                     % (max_db, krmin, krmax, n_inc),
                     computed="outputs/sbr_kr_sweep.json summary_div16.max_abs_db_vs_po = %.10f. "
                              "⚠ Mie 와 해석 PO 는 기준해이지 우리 출력이 아니다. 절대 레벨은 측정 앵커가 없다 "
                              "- 앵커는 주파수 '기울기' 만 받고 레벨 이동은 0.00 dB." % max_db,
                     source=sa_src + " · " + kr_src),
        geometry=C(2, "A active-monostatic / B passive quasi-monostatic / C passive bistatic, "
                   "as one 3x3 grid with WiFi/LTE/5G",
                   computed="outputs/geometry_grid.json configurations_and_grid - 세 기하 x 세 조명원. "
                            "모노 v_max == 바이 beta=0 (차이 0 m/s) 이므로 우리 수치는 두 기하의 최악값.",
                   source=gg_src,
                   note="⚠ " + phi_head[phi_head.find("⚠"):][:180] if "⚠" in phi_head else None),
        vmax=C(2, "cross-standard table under one stated convention, overlaid on published "
               "airframe maxima; CFAR-calibrated detection linked",
               computed="benchmark/vmax_grid.py - LTE CRS 1 kHz @1.843 GHz, WiFi VHT-LTF 1 kHz "
                        "@5.21 GHz, 5G SSB 50 Hz @3.5 GHz, WiFi beacon 9.77 Hz. CFAR 는 %.0f s "
                        "GPU 몬테카를로로 경험적 Pfa 에 교정했다." % cpi,
               source=cf_src + " · outputs/geometry_grid.json",
               note="⚠ 식 자체는 우리 것이 아니다 - Abratkiewicz, IEEE JSTARS 2023, eq.(16). "
                    "우리 몫은 표준 간 표와 기체 최고속도 겹침, 그리고 검출성능과의 연결."),
    )
    return cells


# =========================================================================== #
#  5. 조립 · 등급 확정 · 자기검증
# =========================================================================== #
def finalize(rows, scan):
    """인용문을 PDF 에 재대조하고 등급을 확정한다. 실패하면 자동 강등."""
    selfcheck = {"checked": 0, "passed": 0, "failed": []}
    count_failures = []
    _z = lambda: {"QUOTED": 0, "COMPUTED": 0, "DERIVED": 0, "UNVERIFIED": 0}
    grade_counts = _z()
    per_col = {c: _z() for c in COL_IDS}

    for key, row in rows.items():
        sc = scan.get(key, {})
        for col in COL_IDS:
            cell = row["cells"].get(col)
            if cell is None:
                # 열이 비어 있으면 스캔으로 자동 채운다 (회절/무모호속도)
                cell = auto_cell(col, key, sc)
                row["cells"][col] = cell
            spec, count_bad = cell.get("count"), None
            if spec:
                txt, count_bad = live_count_text(spec, sc)
                cell["computed"] = txt
                cell["source"] = sc.get("pdf", "PDF not on disk")
                if count_bad:
                    cell["note"] = ((cell.get("note") or "") + " " + count_bad)
                    count_failures.append({"row": key, "column": col, "why": count_bad})
            q = cell.get("quote")
            if count_bad:
                cell["grade"] = "UNVERIFIED"
            elif q:
                selfcheck["checked"] += 1
                ok = (("_norm" in sc) and (_norm(q) in sc["_norm"]))
                if ok:
                    selfcheck["passed"] += 1
                    cell["grade"] = "QUOTED"
                else:
                    selfcheck["failed"].append({"row": key, "column": col,
                                                "quote_head": q[:90]})
                    cell["grade"] = "UNVERIFIED"
                    cell["note"] = ((cell.get("note") or "") +
                                    " ⚠ 인용문이 PDF 재대조에 실패했다 - 등급 강등.")
            elif cell.get("computed"):
                cell["grade"] = "COMPUTED"
            elif cell.get("derived_from"):
                cell["grade"] = "DERIVED"
            else:
                cell["grade"] = "UNVERIFIED"
            grade_counts[cell["grade"]] += 1
            per_col[col][cell["grade"]] += 1
            cell["mark"] = MARKS[cell["level"]][0]
    selfcheck["count_claim_failures"] = count_failures
    return selfcheck, grade_counts, per_col


def live_count_text(spec, sc):
    """셀의 계수 근거를 **이번 실행의 PDF 계수**로 만든다. 낡은 숫자가 남을 수 없다."""
    kind, mode = spec
    if not sc or "error" in sc:
        return "PDF not on disk - count unavailable", "⚠ PDF 부재로 계수 불가."
    npg = sc["n_pages"]
    if kind == "geo":
        g = sc["geo"]
        return ("full-text term counts (%d pages, counted by this script): monostatic=%d, "
                "bistatic=%d, multistatic=%d" % (npg, g["monostatic"], g["bistatic"],
                                                 g["multistatic"])), None
    if kind == "diff":
        d = sc["diff"]
        return ("full-text diffraction term counts (%d pages, counted by this script): %s"
                % (npg, ", ".join("%s=%d" % (k, v) for k, v in d.items()))), None
    c = sc["cols"].get(kind)
    pat = COL_PATS[kind]
    txt = ("full-text term count (%d pages, counted by this script): /%s/ = %d occurrences"
           % (npg, pat, c))
    bad = None
    if mode == "zero" and c != 0:
        bad = ("⚠ 이 칸은 '용어 부재' 를 근거로 삼았는데 이번 계수는 %d 이다 - 등급 강등." % c)
    return txt, bad


def auto_cell(col, key, sc):
    """회절·무모호속도 열의 '없음' 판정은 PDF 전문 용어 계수로 뒷받침한다."""
    if "error" in sc or not sc:
        return C(0, "not checked", note="PDF not on disk")
    if col == "diffraction":
        d = sc["diff"]
        tot = sum(d.values())
        if tot == 0:
            return C(0, "no diffraction treatment (term absent from the full text)",
                     computed="diffract*/UTD/PTD/GTD/wedge/creeping-wave = 0 occurrences in the "
                              "full text layer (%d pages), scanned by this script" % sc["n_pages"],
                     source=sc["pdf"],
                     note="⚠ '언급이 없다'와 '구현이 없다'는 다른 명제다. 여기서는 언급 부재를 적는다.")
        model_terms = d["UTD"] + d["PTD"] + d["GTD"] + d["wedge"] + d["creeping"]
        lvl = 1 if model_terms else 0
        what = ("diffraction-model terms present (%s) - level PARTIAL, needs a manual read"
                % ", ".join("%s=%d" % (k, v) for k, v in d.items() if v)) if model_terms else \
               ("diffraction named %d time(s) but no diffraction-model term "
                "(UTD/PTD/GTD/wedge/creeping = 0)" % d["diffract"])
        return C(lvl, what,
                 computed="full-text diffraction term counts (%d pages, counted by this "
                          "script): %s" % (sc["n_pages"],
                                           ", ".join("%s=%d" % (k, v) for k, v in d.items())),
                 source=sc["pdf"])
    if col == "vmax":
        v = sc["vmax"]
        if v["unambiguous"] == 0:
            return C(0, "unambiguous velocity not reported",
                     computed="'unambiguous' = 0 occurrences in the full text layer (%d pages)"
                              % sc["n_pages"], source=sc["pdf"])
        return C(1, "ambiguity discussed (%d mentions) but no unambiguous-velocity figure quoted here"
                 % v["unambiguous"],
                 computed="'unambiguous' %d회 · 'aliasing' %d회 · 'Nyquist' %d회"
                          % (v["unambiguous"], v["aliasing"], v["nyquist"]),
                 source=sc["pdf"])
    return C(0, "not checked")


# =========================================================================== #
#  6. 그림 — 텍스트 전부 영어
# =========================================================================== #
EVIDENCE_FOOTER = ("Every cell is graded: quoted verbatim from a PDF re-checked at build time, "
                   "computed by us from a JSON or a full-text term count, or derived from a "
                   "quoted cell in the same row (not-applicable calls only).")

def make_figure(rows, order, path_stem, title, subtitle, row_in, pad_in, width_in):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, FancyBboxPatch

    plt.rcParams.update({"font.size": 9, "pdf.fonttype": 42, "savefig.dpi": 300,
                         "figure.dpi": 110})

    SURF = "#fcfcfb"
    INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
    HAIR = "#e1e0d9"
    FILL = {2: "#1c5cab", 1: "#86b6ef", 0: "#f0efec", -1: "#fcfcfb"}
    GLYPHC = {2: "#ffffff", 1: "#0b0b0b", 0: "#898781", -1: "#c3c2b7"}
    WARN = "#fab219"
    GROUP_C = {"S": "#2a78d6", "T": "#898781", "M": "#eb6834", "V": "#4a3aa7", "O": "#008300"}

    #: 회전 머리글이 위로 먹는 높이. 한 행 = 1 데이터단위 = row_in 인치이므로
    #  (글자수 x 9pt 글자폭 x sin38도) / (row_in x 72pt) 데이터단위만큼 올라간다.
    head_rise = (max(len(h) for _, h, _ in COLUMNS) * 5.6 * math.sin(math.radians(38))
                 / (row_in * 72.0)) + 0.75
    import textwrap
    sub_lines = textwrap.wrap(subtitle, 118)

    n = len(order)
    top = n + head_rise + 0.55 + 0.42 * len(sub_lines) + 0.55
    fig, ax = plt.subplots(figsize=(width_in, row_in * (top + 3.05) + 0 * pad_in))
    ax.set_xlim(-0.02, len(COL_IDS) + 0.02)
    ax.set_ylim(-2.75, top + 0.30)
    ax.axis("off")
    ax.set_facecolor(SURF)
    fig.patch.set_facecolor(SURF)

    # 열 머리
    for j, (cid, head, _) in enumerate(COLUMNS):
        ax.text(j + 0.5, n + 0.22, head, rotation=38, ha="left", va="bottom",
                fontsize=9, color=INK,
                rotation_mode="anchor")

    prev_group = None
    for i, key in enumerate(order):
        y = n - 1 - i
        row = rows[key]
        g = row["group"]
        # 그룹 구분선 + 좌측 그룹 색띠
        if g != prev_group:
            if prev_group is not None:
                ax.plot([-0.02, len(COL_IDS)], [y + 0.94, y + 0.94], color=HAIR,
                        lw=1.1, zorder=1)
            prev_group = g
        ax.add_patch(Rectangle((-0.028, y + 0.06), 0.02, 0.86, transform=ax.transData,
                               facecolor=GROUP_C[g], edgecolor="none",
                               clip_on=False, zorder=3))
        lbl = row["short"]
        is_ours = key == "ours"
        ax.text(-0.09, y + 0.5, lbl, ha="right", va="center",
                fontsize=9.2 if is_ours else 8.6,
                color=INK if is_ours else INK2,
                fontweight="bold" if is_ours else "normal", clip_on=False)
        if is_ours:
            ax.add_patch(Rectangle((-0.02, y + 0.03), len(COL_IDS) + 0.02, 0.94,
                                   facecolor="none", edgecolor="#008300", lw=1.6,
                                   zorder=6, clip_on=False))
        for j, cid in enumerate(COL_IDS):
            c = row["cells"][cid]
            lv = c["level"]
            ax.add_patch(FancyBboxPatch((j + 0.06, y + 0.12), 0.88, 0.76,
                                        boxstyle="round,pad=0,rounding_size=0.07",
                                        facecolor=FILL[lv],
                                        edgecolor=HAIR if lv <= 0 else "none",
                                        lw=0.6, zorder=4))
            ax.text(j + 0.5, y + 0.5, MARKS[lv][1], ha="center", va="center",
                    fontsize=11.5, color=GLYPHC[lv], zorder=5)
            if c["grade"] == "UNVERIFIED":
                ax.text(j + 0.86, y + 0.80, "?", ha="center", va="center",
                        fontsize=8, color="#8a5c00", zorder=6,
                        bbox=dict(boxstyle="circle,pad=0.12", fc=WARN, ec="#8a5c00",
                                  lw=0.5))

    # ---------------- 범례 (그림 아래, 서로 겹치지 않게 3단) ----------------
    CW = 0.0455          # 7.8 pt 글자 하나가 먹는 데이터 폭(경험값)

    # 1단: 마크 범례
    ly = -0.75
    lx = 0.0
    for lv, lab in [(2, "capability present"), (1, "partial"), (0, "absent"),
                    (-1, "not applicable")]:
        ax.add_patch(Rectangle((lx, ly - 0.15), 0.26, 0.30, facecolor=FILL[lv],
                               edgecolor=HAIR if lv <= 0 else "none", lw=0.6,
                               clip_on=False))
        ax.text(lx + 0.13, ly, MARKS[lv][1], ha="center", va="center",
                fontsize=9.5, color=GLYPHC[lv], clip_on=False)
        ax.text(lx + 0.33, ly, lab, ha="left", va="center", fontsize=7.8,
                color=INK2, clip_on=False)
        lx += 0.33 + len(lab) * CW + 0.30
    ax.text(lx, ly, "?", ha="center", va="center", fontsize=8,
            color="#8a5c00", clip_on=False,
            bbox=dict(boxstyle="circle,pad=0.12", fc=WARN, ec="#8a5c00", lw=0.5))
    ax.text(lx + 0.18, ly, "UNVERIFIED - not backed by a primary source",
            ha="left", va="center", fontsize=7.8, color=INK2, clip_on=False)

    # 2단: 행 그룹 색띠
    gy = -1.45
    gx = 0.0
    ax.text(gx, gy, "row groups:", ha="left", va="center", fontsize=7.6,
            color=MUTED, clip_on=False)
    gx += 11 * CW + 0.22
    SHORT_G = {"S": "scattering computed from a target geometry",
               "T": "target in a ray-traced scene, no scattering integral",
               "M": "measurement-based signature anchor",
               "V": "ambiguity law, no target scattering",
               "O": "this work"}
    present = {rows[k]["group"] for k in order}
    for g in ["S", "T", "M", "V", "O"]:
        if g not in present:
            continue
        lab = SHORT_G[g]
        w = 0.10 + len(lab) * CW + 0.28
        if gx + w > len(COL_IDS):          # 줄바꿈
            gx, gy = 0.0, gy - 0.42
        ax.add_patch(Rectangle((gx, gy - 0.07), 0.055, 0.17, facecolor=GROUP_C[g],
                               edgecolor="none", clip_on=False))
        ax.text(gx + 0.10, gy, lab, ha="left", va="center", fontsize=7.6,
                color=INK2, clip_on=False)
        gx += w

    # 3단: 증거 등급 각주
    ax.text(0.0, gy - 0.62, EVIDENCE_FOOTER, ha="left", va="center", fontsize=7.4,
            color=MUTED, clip_on=False)

    ax.text(-0.02, top - 0.20, title, ha="left", va="center", fontsize=14,
            color=INK, fontweight="bold", clip_on=False)
    for li, ln in enumerate(sub_lines):
        ax.text(-0.02, top - 0.75 - 0.42 * li, ln, ha="left", va="center", fontsize=8.6,
                color=MUTED, clip_on=False)

    os.makedirs(OUT_FIG, exist_ok=True)
    out = {}
    for ext in ("png", "pdf"):
        p = os.path.join(OUT_FIG, path_stem + "." + ext)
        fig.savefig(p, bbox_inches="tight", facecolor=SURF)
        out[ext] = os.path.relpath(p, _ROOT)
    import matplotlib.pyplot as _plt
    _plt.close(fig)
    return out


# =========================================================================== #
#  7. main
# =========================================================================== #
def main():
    t0 = time.time()
    with open(REFLIB, encoding="utf-8") as f:
        reflib = json.load(f)
    mt = {r["key"]: r for r in reflib["master_table"]}

    keys = [k for k in CITATION if k != "ours"]
    paths = {}
    for k in keys:
        if k in EXTRA_PDF:
            paths[k] = EXTRA_PDF[k]
        else:
            pp = (mt.get(k, {}).get("pdf_paths") or [None])[0]
            paths[k] = pp
    missing = [k for k, v in paths.items() if not v or not os.path.exists(v)]

    scan = scan_pdfs(paths)
    ours = build_our_row()
    rows = build_rows(scan, ours)

    for k, row in rows.items():
        cit, venue, status, year, short = CITATION[k]
        row.update(key=k, citation=cit, venue=venue, status=status, year=year,
                   short=short, pdf=paths.get(k))

    selfcheck, grade_counts, per_col = finalize(rows, scan)

    total_cells = sum(grade_counts.values())
    unver = grade_counts["UNVERIFIED"]
    frac_unver = unver / total_cells if total_cells else 1.0
    ready = frac_unver <= 0.05 and not selfcheck["failed"]

    # ---- 행 순서: 그룹 순 -> 그룹 안에서는 산란능력 합계 내림차순
    def score(k):
        return sum(max(c["level"], 0) for c in rows[k]["cells"].values())
    gorder = ["S", "T", "M", "V", "O"]
    order = []
    for g in gorder:
        ks = [k for k in rows if rows[k]["group"] == g]
        ks.sort(key=lambda k: (-score(k), rows[k]["short"]))
        order += ks

    slide_keys = [k for k in order
                  if rows[k]["group"] in ("S", "M", "O")
                  or k == "abratkiewicz_ssb_jstars23"]
    # 슬라이드판은 그룹 순서를 유지한다
    slide_order = [k for k in order if k in slide_keys]

    figs = {}
    figs["full"] = make_figure(
        rows, order, "capability_matrix",
        "What each prior work actually computes for a drone-scale target",
        "Rows: every reference-library paper that puts a target through a scattering or "
        "signature computation, plus the ambiguity-law owners, plus this work.  "
        "Every cell is graded: quoted from a PDF, computed by us, or UNVERIFIED.",
        row_in=0.36, pad_in=0, width_in=15.2)
    figs["slide"] = make_figure(
        rows, slide_order, "capability_matrix_slide",
        "Capability matrix - prior work vs this work",
        "Scattering-computation and measurement-anchor rows only. Marks are graded evidence, "
        "not claims.",
        row_in=0.40, pad_in=0, width_in=15.0)

    # ---- 열별 요약: 어느 행이 그 능력을 실제로 행사하는가
    col_find = {}
    for cid, head, q in COLUMNS:
        lv = {2: [], 1: [], 0: [], -1: []}
        for k in order:
            lv[rows[k]["cells"][cid]["level"]].append(rows[k]["short"])
        col_find[cid] = {
            "header_en": head,
            "n_full": len(lv[2]), "n_partial": len(lv[1]),
            "n_absent": len(lv[0]), "n_not_applicable": len(lv[-1]),
            "rows_full": lv[2],
            "ours_level": MARKS[rows["ours"]["cells"][cid]["level"]][0],
        }

    # ---- 헤드라인은 주장하지 않고 **센다**
    def lv(k, c):
        return rows[k]["cells"][c]["level"]

    full_all = [rows[k]["short"] for k in order
                if all(lv(k, c) == 2 for c in COL_IDS)]
    nfull = {k: sum(1 for c in COL_IDS if lv(k, c) == 2) for k in order}
    best_n = max(nfull.values())
    best_rows = [rows[k]["short"] for k in order if nfull[k] == best_n]
    ours_full = [c for c in COL_IDS if lv("ours", c) == 2]
    ours_empty = [c for c in COL_IDS if lv("ours", c) == 0]
    vmax_scatter = [rows[k]["short"] for k in order
                    if k != "ours" and lv(k, "vmax") >= 1 and lv(k, "mesh") >= 1]
    scatter_vmax = [rows[k]["short"] for k in order
                    if k != "ours" and rows[k]["group"] == "S" and lv(k, "vmax") >= 1]
    headline = [
        "⭐ Diffraction 열: %d행 중 회절을 실제로 모형에 넣은 것은 %d편(%s)뿐이다. 우리를 포함한 "
        "나머지는 이 열이 비어 있다 - 우리 약점인 동시에 이 분야 전체의 빈 칸이다."
        % (len(order), col_find["diffraction"]["n_full"],
           ", ".join(col_find["diffraction"]["rows_full"]) or "없음"),
        "아홉 열을 모두 채운 행은 %d개다. 최다는 %d/9 이고 거기 해당하는 행은 %s 다. 우리 행이 비는 "
        "열은 %s 이고 Amplitude validation 은 해석해까지라 부분이다."
        % (len(full_all), best_n, ", ".join(best_rows), ", ".join(ours_empty) or "없음"),
        "무모호 속도(부분 이상)와 표적 메시를 동시에 가진 선행은 %s 뿐이고, 그 논문은 진폭 검증이 "
        "통째로 없다(validation=NONE). 무모호 속도가 FULL 인 선행 %s 은 전부 산란을 계산하지 않는다. "
        "⚠ 식 자체는 우리 것이 아니다 - Abratkiewicz(IEEE JSTARS 16:3469-3484, 2023, PUBLISHED) eq.(16)."
        % (", ".join(vmax_scatter) or "없음",
           ", ".join(rows[k]["short"] for k in order
                     if k != "ours" and lv(k, "vmax") == 2) or "없음"),
        "우리 행이 FULL 인 열 %d개: %s." % (len(ours_full), ", ".join(ours_full)),
    ]

    doc = {
        "meta": {
            "script": "benchmark/capability_matrix.py",
            "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "run": "cd /workspace/sionna && PYTHONPATH=src:benchmark "
                   "~/.venvs/py312/bin/python benchmark/capability_matrix.py",
            "purpose_ko": "사용자 추적표(Sionna RT | drone Mesh | material | Aspect/RCS | Rotor | "
                          "diffraction)를 우리 포지셔닝에 필요한 3열(진폭검증·기하·무모호속도)로 확장한 "
                          "능력 매트릭스.",
            "house_rules": "산문 한국어, 그림 텍스트 영어. 인용은 게재처 + 게재상태 + 연도.",
            "evidence_rule_ko": "한 칸은 (a) 내가 이번 실행에서 연 PDF 의 축자 인용(매 실행 재대조) "
                                "또는 (b) 디스크 JSON/PDF 전문 계수에서 우리가 계산한 값이어야 한다. "
                                "둘 다 아니면 UNVERIFIED 로 남기고 발표에 쓰지 않는다.",
            "runtime_s": round(time.time() - t0, 2),
            "inputs": ["outputs/reference_library.json", "outputs/verify_chen.json",
                       "outputs/sbr_kr_sweep.json", "outputs/sigma_anchor.json",
                       "outputs/geometry_grid.json", "outputs/verify_cfar.json"],
            "pdfs_opened": len([k for k, v in scan.items() if "error" not in v]),
            "pdfs_missing": missing,
        },
        "columns": [{"id": c[0], "header_en": c[1], "question_ko": c[2]} for c in COLUMNS],
        "mark_scale": {str(k): v[0] for k, v in MARKS.items()},
        "evidence_grades": GRADES,
        "row_groups": ROW_GROUPS,
        "rows": [dict(rows[k], order_index=i) for i, k in enumerate(order)],
        "counts": {
            "rows": len(order),
            "columns": len(COL_IDS),
            "cells": total_cells,
            "by_grade": grade_counts,
            "by_column": per_col,
            "unverified_fraction": round(frac_unver, 4),
            "quote_selfcheck": selfcheck,
        },
        "readiness": {
            "presentable": bool(ready),
            "rule_ko": "UNVERIFIED 비율 5% 이하 그리고 인용 재대조 실패 0건이면 발표 가능으로 본다. "
                       "DERIVED 는 UNVERIFIED 로 세지 않되 수를 따로 보고한다.",
            "verdict_ko": ("발표 가능 — UNVERIFIED %d/%d(%.1f%%), 인용 재대조 실패 %d건."
                           % (unver, total_cells, 100 * frac_unver, len(selfcheck["failed"])))
            if ready else
            ("아직 발표 불가 — UNVERIFIED %d/%d(%.1f%%), 인용 재대조 실패 %d건. "
             "빈 칸을 그럴듯하게 채우지 말고 1차 출처를 열 것."
             % (unver, total_cells, 100 * frac_unver, len(selfcheck["failed"]))),
        },
        "our_row_gaps_ko": [
            "⭐ 회절 0 — PTD·UTD·크리핑파가 우리 커널에 없다. 이것이 우리 밴드 기울기가 실측의 3~8배로 "
            "가파른 이유의 가장 유력한 물리적 후보다(Kirik Sigma'19 이 PTD 가 저주파를 더 들어올린다는 "
            "그림을 준다). 매트릭스에서 우리 행이 이 열에서 비는 것은 사실이다.",
            "진폭 검증이 해석 PO 구까지다 — 절대 레벨을 측정에 앵커링하지 않았다. 앵커는 주파수 기울기만 "
            "받고 레벨 이동은 0.00 dB.",
            "로터 운동은 future work 로 강등했다(코드는 있으나 리포트에서 제외).",
            "⚠ 지금까지의 검출 결과가 전부 장면방위 phi=90 도 단일 컷이다 "
            "(experiment_freespace_range.py:322,773 하드코딩).",
        ],
        "record_corrections_ko": [
            "⭐ Costa 의 게재처는 IEEE JSTSP 가 아니라 **IEEE Journal of Selected Topics in "
            "Electromagnetics, Antennas and Propagation (JSTEAP), vol.1, 2025** 다 — 게재판 1쪽의 "
            "'Digital Object Identifier 10.1109/JSTEAP.2025.3604407' 과 각 쪽 하단의 저널명을 "
            "이번에 직접 읽어 확인했다. outputs/reference_library.json 의 "
            "costa_bistatic_md_jsteap25.venue('IEEE J. Sel. Topics Signal Process.') 는 틀렸다. "
            "사용자 추적표의 'IEEE JSTEAP 2025' 가 맞다.",
            "⚠ Costa 는 arXiv 판과 게재판의 문장이 다르다 — 회절 문장이 arXiv 는 'some "
            "electromagnetic phenomena', 게재판은 'some EM phenomena' 다. 판본을 섞어 인용하면 "
            "축자 대조에서 걸린다(이번에 실제로 걸렸다).",
            "⚠ reference_library 의 radartwin_arxiv26 인용문 끝이 'that the real system cannot "
            "resolve' 로 적혀 있는데 원문은 'that the real radar does not measure' 다. 재대조가 잡았다.",
            "⚠ reference_library 의 semkin_drone_rcs_access20.pdf_paths[0] 은 Ezuma/Semkin 의 "
            "**다른 논문**(arXiv 2112.09774, Comparative Analysis of RCS Based UAV Classification)"
            "이다. IEEE Access 2020 본편은 pdf_paths[1] 이다.",
            "⚠ Great-X(arXiv 2507.08716)의 재질 칸을 처음에 '언급 없음' 으로 적었다가, 이번 실행의 "
            "용어 계수가 1 을 돌려주어 원문을 열고 'ITU 권고의 파라미터 정의를 쓰는 비자성 유전체' "
            "문장을 확인해 PARTIAL 로 고쳤다.",
        ],
        "excluded_rows_ko": {
            "kasdorf_sbr_coneangle": "SBR 정확도 개선 방법론이지만 표적이 없다(터널 전파). 방법 선례로만 인용.",
            "maksymiuk_renyi_rs22": "실측 + 검출 적분 논문. 표적 산란 계산이 없다.",
            "xu_ckm_clam_arxiv25": "점산란체 수준 시뮬레이션. 산란 계산 없음.",
            "he_convex_clutter_arxiv25": "몬테카를로 무작위 표적. 산란 계산 없음.",
            "azim_*/ezuma_*/yuan_uav_rcs_eucap25": "실측 RCS 앵커이지만 이번 매트릭스의 측정행 5편으로 "
            "대표시켰다. 필요하면 같은 스키마로 추가 가능.",
        },
        "column_findings": col_find,
        "headline_ko": headline,
        "figures": figs,
        "how_to_read_ko": [
            "열은 '주장' 이 아니라 '능력' 이다. 채워진 칸은 그 논문이 그 능력을 실제로 행사했다는 뜻이고, "
            "빈 칸은 그 논문이 나쁘다는 뜻이 아니라 그 축을 다루지 않았다는 뜻이다.",
            "'?' 배지가 붙은 칸은 1차 출처로 확인하지 않은 칸이다. 발표에서 그 칸을 근거로 말하지 말 것.",
            "⭐ Diffraction 열은 이 매트릭스에서 가장 정보량이 큰 열이다 — Ziganshin 두 편만 이 열에서 "
            "만점이고, 우리를 포함한 나머지는 대부분 비어 있다.",
        ],
    }

    outp = os.path.join(OUT, "capability_matrix.json")
    with open(outp, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)

    print("wrote", os.path.relpath(outp, _ROOT),
          "(%.1f KB)" % (os.path.getsize(outp) / 1024))
    print("rows %d · cells %d · QUOTED %d · COMPUTED %d · UNVERIFIED %d (%.1f%%)"
          % (len(order), total_cells, grade_counts["QUOTED"], grade_counts["COMPUTED"],
             unver, 100 * frac_unver))
    print("quote self-check: %d/%d passed" % (selfcheck["passed"], selfcheck["checked"]))
    for f_ in selfcheck["failed"]:
        print("  FAILED:", f_["row"], f_["column"], "|", f_["quote_head"])
    print("figures:", figs)
    if missing:
        print("PDF missing:", missing)
    return doc


if __name__ == "__main__":
    main()
