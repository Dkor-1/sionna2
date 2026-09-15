# -*- coding: utf-8 -*-
"""
isac_plan_positioning_0915.py -- citable records for the ISAC detection+tracking plan: repo decisions,
standards alignment, prior work, candidate contributions, and conflicts with the uncommitted 0915 draft.

Purpose
    The Korean report notebook "ISAC detection+tracking plan" cites every number and every recorded
    decision through a ledger key. This script builds that ledger for the positioning chapter:
      * repo_quotes            repo text lines, re-opened and checked at run time (path, line, quote, sha256)
      * standards_numbers      values copied by key path from outputs/isac_standard_gaps.json (never retyped)
      * corpus_counts          counts over outputs/elev_sweep_shards file names, parsed with src/arm_grammar.py
      * alignment_checks       carrier / bandwidth / channel-map numbers read from repo files and draft ledgers
      * draft_files, draft_grep_counts, draft_conflicts
                               the other session's UNCOMMITTED draft (docs/ISAC_DETECTION_TRACKING_REVIEW_0915.md,
                               outputs/isac_campaign_design_0915.json and three companion files), hashed as read;
                               every conflict carries prose_assertions that re-check its prose against the run-time
                               counts, and a failed assertion sets _meta.status to complete_with_failures
      * prior_work             arXiv papers re-opened on 2026-09-15 plus two repo records
      * candidate_contributions, stale_repo_records, open_questions

Run (from the repo root)
    CUDA_VISIBLE_DEVICES="" /workspace/.venvs/py312/bin/python benchmark/isac_plan_positioning_0915.py
    optional: --root <repo root> --out <ledger path> --core <cpu core>

Runtime
    about 2-5 s on one CPU core (reads text files and about 8,000 shard file NAMES; no shard is opened).

Scope
    These are simulation / code / bookkeeping checks with no comparison against RF measurements.
    Literature statements are what the cited documents say about their own work; nothing here says
    which simulation engine is right, and PathSolver levels are never converted to scattering areas.
"""
from __future__ import annotations

import os
import sys

# CPU only, one core -- set before any other import.
os.environ["CUDA_VISIBLE_DEVICES"] = ""


def _pin_one_core() -> int:
    core = None
    for i, a in enumerate(sys.argv):
        if a == "--core" and i + 1 < len(sys.argv):
            core = int(sys.argv[i + 1])
        elif a.startswith("--core="):
            core = int(a.split("=", 1)[1])
    if core is None:
        core = min(os.sched_getaffinity(0))
    os.sched_setaffinity(0, {core})
    return core


CORE = _pin_one_core()
sys.dont_write_bytecode = True  # never write __pycache__ into the repo when importing src/ modules

import argparse  # noqa: E402
import ast  # noqa: E402
import datetime as _dt  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import platform  # noqa: E402
import re  # noqa: E402
import subprocess  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

NAME = "isac_plan_positioning_0915"
GENERATOR = f"benchmark/{NAME}.py"
COMMAND = f'CUDA_VISIBLE_DEVICES="" /workspace/.venvs/py312/bin/python {GENERATOR}'
RETRIEVED = "2026-09-15"  # date the web documents in SOURCES were re-opened

# --------------------------------------------------------------------------------------------------------
# SOURCES -- external literature / specification statements. Every non-repo statement in this ledger comes
# from this one table and is copied into the ledger under "sources". Quotes are as returned when the arXiv
# abstract or HTML page was re-opened on RETRIEVED.
# --------------------------------------------------------------------------------------------------------
SOURCES = [
    dict(id="SRC_2608_05826", document_id="arXiv:2608.05826v1",
         url="https://arxiv.org/abs/2608.05826", url_html="https://arxiv.org/html/2608.05826v1",
         title="5G ISAC-Based UAV Detection and 3-D Tracking Using Uplink Sounding Reference Signals on an "
               "End-to-End O-RAN Simulation Testbed",
         authors="Arun K. Gurung, Satha K. Sathananthan, Shiva R. Pokhrel", date="submitted 2026-08-06",
         quotes=[
             dict(locator="abstract", text="built from open-source components: OpenAirInterface, FlexRIC and Sionna RT"),
             dict(locator="abstract", text="the NR Uplink Sounding Reference Signal is repurposed as a passive radar waveform"),
             dict(locator="abstract", text="a PHY-layer sensing stage inside the gNB produces detections that reach an "
                                          "Extended Kalman Filter tracking xApp"),
             dict(locator="abstract", text="Detection coverage is preserved under a concurrent 10 Mbps uplink communications load.",
                  url="https://arxiv.org/abs/2608.05826", retrieved=RETRIEVED),
             dict(locator="HTML Sec. III-B (Signal Model)",
                  text="all rays that scatter off the UAV are coherently summed into a single echo tap, so the target "
                       "is rendered as one point scatterer rather than as a body with extent"),
             dict(locator="HTML Sec. III-B (Signal Model)", text="fuselage multi-bounce and rotor micro-Doppler are not modeled"),
             dict(locator="HTML Sec. V-B (Clutter-Subspace Deflation)",
                  text="The disturbance — the direct path and the static ground return... is removed by deflating the "
                       "leading Kc such directions"),
             dict(locator="HTML Table III", text="Antenna element pattern: Isotropic; both gNB Rx and nrUE Tx"),
             dict(locator="HTML Table III", text="CFAR P_FA: 10^-4"),
             dict(locator="HTML Table III", text="4 (half-λ ULA)"),
             dict(locator="HTML Table IV", text="low-permittivity dry-ground floor, buildings removed for the flat-LOS benchmark"),
             dict(locator="HTML Sec. VI-A (Metric Definitions)",
                  text="Track continuity is the fraction of a target's observable CPIs in which it is tracked"),
         ],
         note="Closest simulation precedent: Sionna RT outdoor scene, UAV detection and EKF tracking; NIS/NEES "
              "consistency discussed in Sec. VI-C."),
    dict(id="SRC_2608_10784", document_id="arXiv:2608.10784",
         url="https://arxiv.org/abs/2608.10784", url_html="https://arxiv.org/html/2608.10784",
         title="Multi-UAV Tracking Evaluation Using 5G Uplink Signals on an O-RAN ISAC Simulation Testbed",
         authors="Arun K. Gurung, Satha K. Sathananthan", date="2026-08 (arXiv 2608)",
         quotes=[
             dict(locator="HTML Sec. III-C / Table I", text="fc=3319.68 MHz"),
             dict(locator="HTML Table I", text="Channel bandwidth 40 MHz nominal; 106 PRBs == 38.16 MHz occupied"),
             dict(locator="HTML Table I", text="gNB Rx antennas (Nrx): 8, as a 2×4 half-λ uniform planar array (UPA)"),
             dict(locator="HTML Table I", text="Antenna element pattern: Isotropic; both gNB Rx and nrUE Tx"),
             dict(locator="HTML Sec. III-C (Scope of the target model)",
                  text="Each UAV is a single diffuse sphere: one point-like scattering center with an aspect-dependent "
                       "bistatic return supplied by the ray tracer."),
             dict(locator="HTML Sec. III-C (Scope of the target model)",
                  text="It excludes extended-body scattering (a real airframe is several scattering centers whose "
                       "relative phases sweep with aspect), rotor micro-Doppler (the spectral signature counter-UAS "
                       "classifiers most often exploit), inter-target occlusion and shadowing, polarization, and any "
                       "target-to-target coupling."),
         ],
         note="Companion of arXiv:2608.05826 on the same testbed, multi-UAV tracking."),
    dict(id="SRC_2412_20788", document_id="arXiv:2412.20788",
         url="https://arxiv.org/abs/2412.20788", url_html="https://arxiv.org/html/2412.20788v1",
         title="An Experimental Study of Passive UAV Tracking with Digital Arrays and Cellular Downlink Signals",
         authors="Yifei Sun, Chao Yu, Yan Luo, Tony Xiao Han, Haisheng Tan, Rui Wang, Francis C. M. Lau",
         date="submitted 2024-12-30",
         quotes=[
             dict(locator="abstract", text="a passive sensing receiver with two digital antenna arrays is proposed and "
                                          "developed to capture both the line-of-sight (LoS) signal and the scattered "
                                          "signal off a target UAV"),
             dict(locator="abstract", text="the widely deployed long-term evolution (LTE) base station (BS) is exploited "
                                          "to illuminate UAVs in bistatic trajectory tracking"),
             dict(locator="abstract", text="the proposed UAV tracking system can achieve a meter-level accuracy"),
             dict(locator="abstract", text="In order to address missed detections and false alarms of passive sensing, a "
                                          "multi-target tracking framework is adopted to track the trajectory of the target UAV.",
                  url="https://arxiv.org/abs/2412.20788", retrieved=RETRIEVED),
             dict(locator="arXiv comments field", text="13 pages, 10 figures, submitted to IEEE Journal for possible publication"),
         ],
         note="The abstract page does not name LIPASE or a dataset; identity with the repo's LIPASE record "
              "(Sun et al., IEEE OJ-COMS 2025) is not established by this page."),
    dict(id="SRC_2509_25732", document_id="arXiv:2509.25732",
         url="https://arxiv.org/abs/2509.25732", url_html=None,
         title="Doppler-Based Multistatic Drone Tracking via Cellular Downlink Signals",
         authors="Chenqing Ji, Qionghui Liu, Jiahong Liu, Chao Yu, Yifei Sun, Rui Wang, Fan Liu",
         date="submitted 2025-09-30",
         quotes=[
             dict(locator="abstract", text="three passive sensing receivers are deployed at different locations"),
             dict(locator="abstract", text="the LTE base stations (BSs) are exploited as signal illuminators"),
             dict(locator="abstract", text="the target drone and all the sensing receivers are around 200 meters away "
                                          "from the illuminating BSs"),
             dict(locator="abstract", text="the complicated trajectories can be tracked with 90% errors below 90 centimeters"),
         ],
         note="Measured multistatic passive tracking from bistatic Doppler."),
    dict(id="SRC_2504_05168", document_id="arXiv:2504.05168v2",
         url="https://arxiv.org/abs/2504.05168", url_html="https://arxiv.org/html/2504.05168v2",
         title="Modeling Micro-Doppler Signature of Multi-Propeller Drones in Distributed ISAC",
         authors="Heraldo Cesar Alves Costa, Saw J. Myint, Carsten Andrich, Sebastian W. Giehl, Maximilian "
                 "Engelhardt, Christian Schneider, Reiner S. Thomä",
         date="submitted 2025-04-07, revised 2025-09-10; journal-ref IEEE J. Sel. Topics Electromagn. Antennas "
              "Propag. 1(1):208-222, Sept. 2025",
         quotes=[
             dict(locator="abstract", text="The proposed model adapts the classic thin-wire model to include bistatic "
                                          "sensing configuration with an OFDM-like signal."),
             dict(locator="abstract", text="by incorporating multiple propellers and integrating the reflectivity of the "
                                          "drone's static parts"),
             dict(locator="abstract", text="Measurements were performed to collect ground truth data for verification of the "
                                          "proposed model.",
                  url="https://arxiv.org/abs/2504.05168", retrieved=RETRIEVED),
             dict(locator="HTML Appendix B", text="After that, time domain gating is applied to filter out the residual reflections."),
             dict(locator="HTML Appendix C", text="a back-to-back measurement as a reference for proper calibration"),
             dict(locator="HTML Introduction", text="intended to become an interesting tool for future development of "
                                                   "ISAC target classification algorithms"),
         ],
         note="Reading of the HTML on RETRIEVED (a summary, not a verbatim quote): no ground or environment "
              "multipath model and no detection, CFAR or tracking."),
    dict(id="SRC_2605_23561", document_id="arXiv:2605.23561",
         url="https://arxiv.org/abs/2605.23561", url_html=None,
         title="Reliable UAV Detection with ISAC",
         authors="Stephan Saur, Mark Doll, Artjom Grudnitsky, Silvio Mandelli, Lucas Giroto, Marcus Henninger, "
                 "Thorsten Wild", date="submitted 2026-05-22",
         quotes=[
             dict(locator="abstract", text="detection of a small UAV using unmodified commercial 5G hardware for "
                                          "mono-static Orthogonal Frequency-Division Multiplexing (OFDM) radar"),
             dict(locator="abstract", text="reliable detection with sub-meter accuracy is still possible in over 500 "
                                          "meters distance in a challenging radio environment rich of strong clutter"),
         ],
         note="Measured monostatic 5G detection; only the abstract page was re-opened."),
    dict(id="SRC_2603_14351", document_id="arXiv:2603.14351",
         url="https://arxiv.org/abs/2603.14351", url_html=None,
         title="Clutter-Resilient ISAC for Low-Altitude Wireless Networks: A 5G Base Station-Compatible Protocol, "
               "Waveform, and Prototype",
         authors="Jie Wang, Zhen Du, Ying Wang, Weijie Yuan, Fan Liu, Xingdong Liang, Yong Zeng",
         date="submitted 2026-03-15",
         quotes=[
             dict(locator="abstract", text="The developed 5G-A GBS can effectively track weak and slow targets at "
                                          "distances exceeding 1 kilometer, while incurring only a 1.2% downlink rate "
                                          "loss relative to commercial 5G-A GBS."),
         ],
         note="Base-station prototype; only the abstract page was re-opened."),
]

# --------------------------------------------------------------------------------------------------------
# Repo text lines to verify at run time. `line` is where the quote was found when this script was written;
# if the file has changed, the script searches the whole file and records where it is now. A quote with
# n_lines > 1 is searched in that many consecutive lines, each stripped and joined with one space.
# --------------------------------------------------------------------------------------------------------
QUOTES = [
    # -- decisions and directions
    dict(id="Q_engine_roles_0915_evening", topic="decision", path="AGENTS.md", line=30, n_lines=4,
         quote="Engine roles (user decision 2026-09-15, evening KST; supersedes the \"PathSolver only\" note in "
               "runners/jobs_0936_attrib.txt:3): our kernel is the free-space reference that establishes under which "
               "settings PathSolver output is reasonable, and environments are then modelled and simulated with "
               "PathSolver alone.",
         gloss_en="Current engine roles (English in source). Supersedes Q_pathsolver_only_decision."),
    dict(id="Q_engine_roles_0915_user_wording", topic="decision", path="AGENTS.md", line=33, n_lines=3,
         quote="「방향성을 free space에서 우리 커널과 비교했을때 PathSolver로도 충분히 합리적이라고 볼 수 있는 결과물을 "
               "낼 수 있는 방법론들을 정리해뒀으며 그 내용을 토대로 환경 모델링해서 PathSolver만으로 시뮬레이션을 돌릴 수 "
               "있다가 되면」",
         gloss_en="User wording: once methods are written down that, compared with our kernel in free space for "
                  "directionality, let PathSolver produce results that can be regarded as reasonable, environments can "
                  "be modelled on that basis and simulated with PathSolver alone."),
    dict(id="Q_engine_roles_relative_only", topic="decision", path="AGENTS.md", line=35, n_lines=2,
         quote="Compare the engines only on relative quantities; never compare their absolute levels or declare either one right.",
         gloss_en="Engine comparison rule attached to the engine roles (English in source)."),
    dict(id="Q_matrice4e_on_hand", topic="decision", path="AGENTS.md", line=37,
         quote="A real DJI Matrice 4E (the simulated airframe `matrice4e`) is on hand (user, 2026-09-15).",
         gloss_en="The airframe simulated as matrice4e exists as real hardware for X410 captures (English in source)."),
    dict(id="Q_pathsolver_only_decision", topic="decision_superseded", path="runners/jobs_0936_attrib.txt", line=3,
         quote="사용자 결정(2026-09-15): 커널은 다른 논문으로 가고, 이 쪽은 **PathSolver 만으로** 간다.",
         gloss_en="User decision 2026-09-15: the kernel goes to a different paper; this side proceeds with PathSolver only. "
                  "Superseded the same evening by Q_engine_roles_0915_evening (see stale_repo_records)."),
    dict(id="Q_path_provenance_asset", topic="decision", path="runners/jobs_0936_attrib.txt", line=4,
         quote="그때 광선 추적기만이 가진 것이 **경로별 출처**다",
         gloss_en="Then what only the ray tracer has is per-path provenance."),
    dict(id="Q_attribution_retraction", topic="decision", path="runners/jobs_0936_attrib.txt", line=13,
         quote="⛔⛔철회 (2026-09-15) — 이 발주서가 적었던 「camera 66.6 % · motor 14.1 %」를 **버린다.**",
         gloss_en="Retraction 2026-09-15: the per-part shares this queue file once wrote are discarded."),
    dict(id="Q_attribution_rule_first", topic="decision", path="runners/jobs_0936_attrib.txt", line=31,
         quote="부위별로 가르려면 **배분 규칙을 먼저 정해야 한다.**",
         gloss_en="To split by part, an allocation rule must be fixed first."),
    dict(id="Q_diffuse_always_on", topic="rule", path="docs/EXPERIMENT_BACKLOG.md", line=234,
         quote="**확산 F 는 항상 켠다**",
         gloss_en="Diffuse reflection (switch F) is always on."),
    dict(id="Q_diffraction_new_build_only", topic="rule", path="docs/SIONNA_UPGRADE_0914.md", line=152,
         quote="사용자 결정(2026-09-14): 「회절은 어차피 한동안 안 쓰고 **신버전에서만** 사용하기로 했어」.",
         gloss_en="User decision 2026-09-14: diffraction is not used for a while, and only on the new Sionna build when used."),
    dict(id="Q_not_fixed_to_passive_bistatic", topic="rule", path="docs/PAPER_SPEC.md", line=12,
         quote="태스크를 **패시브 바이스태틱으로 고정하는 것이 아니라**",
         gloss_en="User instruction 2026-07-31: the task is not fixed to passive bistatic (benchmark both monostatic and bistatic)."),
    # -- src/experiment_x410.py
    dict(id="Q_x410_direction_date", topic="x410_record", path="src/experiment_x410.py", line=7,
         quote="프로젝트 방향 (2026-07-14 확정",
         gloss_en="Project direction (fixed 2026-07-14)."),
    dict(id="Q_x410_detection_not_tracking", topic="x410_record", path="src/experiment_x410.py", line=8,
         quote="**태스크 = 디텍션**. 트래킹 아님.",
         gloss_en="Task = detection. Not tracking."),
    dict(id="Q_x410_rx0_reference", topic="x410_record", path="src/experiment_x410.py", line=37,
         quote="RX0 = **기준 채널**",
         gloss_en="RX0 = reference channel."),
    dict(id="Q_x410_rx123_half_wavelength_ula", topic="x410_record", path="src/experiment_x410.py", line=38,
         quote="RX1,2,3 = **감시 배열** — 표적 방향, λ/2 간격 균일선형배열(ULA)",
         gloss_en="RX1,2,3 = surveillance array toward the target, uniform linear array with lambda/2 spacing."),
    dict(id="Q_x410_detection_one_tracking_three", topic="x410_record", path="src/experiment_x410.py", line=40,
         quote="**디텍션은 감시 1채널로 충분**하고, **트래킹은 배열 3채널**이 필요하다",
         gloss_en="Detection needs one surveillance channel; tracking needs the three-channel array."),
    dict(id="Q_x410_carrier_default", topic="x410_record", path="src/experiment_x410.py", line=116,
         quote="carrier_hz: float = 3.5e9", gloss_en="Scenario carrier default."),
    dict(id="Q_x410_geometry_tx", topic="x410_geometry", path="src/experiment_x410.py", line=117,
         quote="tx_pos: tuple = (4.0, 2.5, 8.0)", gloss_en="Old indoor scenario: transmit horn position (on one wall)."),
    dict(id="Q_x410_geometry_ref", topic="x410_geometry", path="src/experiment_x410.py", line=118,
         quote="ref_pos: tuple = (4.0, 4.0, 8.0)", gloss_en="Old indoor scenario: RX0 reference position near TX."),
    dict(id="Q_x410_geometry_surv", topic="x410_geometry", path="src/experiment_x410.py", line=119,
         quote="surv_center: tuple = (4.0, 17.5, 6.5)", gloss_en="Old indoor scenario: surveillance array centre (opposite wall)."),
    dict(id="Q_x410_geometry_target", topic="x410_geometry", path="src/experiment_x410.py", line=122,
         quote="target: tuple = (21.0, 10.0, 5.5)", gloss_en="Old indoor scenario: drone position."),
    dict(id="Q_x410_aoa_formula", topic="x410_record", path="src/experiment_x410.py", line=167,
         quote="np.degrees(0.886 * 2.0 / N)", gloss_en="Printed angle-resolution formula for an N-element lambda/2 array."),
    # -- prior_work/isac_standard_scenarios.md (first-hand 3GPP extraction)
    dict(id="Q_std_umaav_scenario", topic="standard", path="prior_work/isac_standard_scenarios.md", line=45,
         quote="**UAV 는 `UMa-AV`(도심 매크로 · 공중 UE 확장) 가 표준 시나리오다.**",
         gloss_en="For UAVs, UMa-AV (urban macro, aerial-UE extension) is the standard scenario."),
    dict(id="Q_std_small_uav_size", topic="standard", path="prior_work/isac_standard_scenarios.md", line=47,
         quote="표적은 **소형 UAV 0.3×0.4×0.2 m**",
         gloss_en="The target is a small UAV of 0.3 x 0.4 x 0.2 m (its scattering value is left to the link-budget ledger)."),
    dict(id="Q_std_umaav_altitude_speed", topic="standard", path="prior_work/isac_standard_scenarios.md", line=47,
         quote="고도 25–300 m, 수평속도 0–180 km/h,",
         gloss_en="UMa-AV small-UAV target: altitude 25-300 m, horizontal speed 0-180 km/h."),
    dict(id="Q_std_umaav_gnb_height", topic="standard", path="prior_work/isac_standard_scenarios.md", line=48,
         quote="gNB 높이 25 m.", gloss_en="UMa-AV gNB height 25 m."),
    dict(id="Q_std_fr1_carrier", topic="standard", path="prior_work/isac_standard_scenarios.md", line=336,
         quote="| Carrier | **4 or 4.9 GHz**, 옵션 6 GHz |", gloss_en="TR 38.765 Annex A FR1 carrier: 4 or 4.9 GHz, option 6 GHz."),
    dict(id="Q_std_fr1_bandwidth", topic="standard", path="prior_work/isac_standard_scenarios.md", line=337,
         quote="| System bandwidth | **100 MHz** |", gloss_en="TR 38.765 Annex A FR1 system bandwidth: 100 MHz."),
    dict(id="Q_std_fr1_scs", topic="standard", path="prior_work/isac_standard_scenarios.md", line=338,
         quote="| Numerology | SCS 30 kHz |", gloss_en="TR 38.765 Annex A FR1 numerology: 30 kHz subcarrier spacing."),
    dict(id="Q_std_isolation", topic="standard", path="prior_work/isac_standard_scenarios.md", line=346,
         quote="| **안테나 격리** | **65 dB, 80 dB** |", gloss_en="TR 38.765 Annex A antenna isolation: 65 dB, 80 dB."),
    dict(id="Q_std_passive_contribution_surface", topic="positioning_old", path="prior_work/isac_standard_scenarios.md",
         line=405, quote="passive-receiver bistatic case unaddressed by the standard — that gap is our contribution",
         gloss_en="Older positioning sentence: the passive-receiver bistatic case is our contribution surface."),
    dict(id="Q_std_passive_no_self_interference", topic="positioning_old", path="prior_work/isac_standard_scenarios.md",
         line=415, quote="**패시브 바이스태틱은 이 항이 원천적으로 없다**",
         gloss_en="Older positioning: passive bistatic has no self-interference term at all."),
    dict(id="Q_std_repo_carrier_differs", topic="standard", path="prior_work/isac_standard_scenarios.md", line=785,
         quote="| 반송파 | **4 또는 4.9 GHz** (옵션 6) | 1.8 / **3.5** / 5.2 GHz | 다르다.",
         gloss_en="Repo comparison table: carrier differs (TR 38.765 4 or 4.9 GHz, option 6; repo 1.8 / 3.5 / 5.2 GHz)."),
    dict(id="Q_std_repo_nr_arm_matches_bandwidth", topic="standard", path="prior_work/isac_standard_scenarios.md", line=786,
         quote="| 대역폭 | FR1 **100 MHz** | 5G NR **100 MHz** (LTE 20 · WiFi 80) | **5G 팔은 일치** |",
         gloss_en="Repo comparison table: bandwidth, the 5G NR arm matches at 100 MHz (LTE 20, Wi-Fi 80)."),
    dict(id="Q_std_repo_nr_arm_matches_scs", topic="standard", path="prior_work/isac_standard_scenarios.md", line=787,
         quote="| Numerology | **SCS 30 kHz** | 5G NR **30 kHz** ⟨`src/waveforms.py:46`⟩ | **일치** |",
         gloss_en="Repo comparison table: the repo NR arm matches TR 38.765 at 30 kHz."),
    dict(id="Q_std_non_rotating_point", topic="standard", path="prior_work/isac_standard_scenarios.md", line=828,
         quote="3GPP 의 소형 UAV 표적은 «회전하지 않는 등방 점» 이다.",
         gloss_en="The 3GPP small-UAV target is a non-rotating isotropic point."),
    dict(id="Q_std_pmd_definition", topic="standard_metric", path="prior_work/isac_standard_scenarios.md", line=883,
         quote="**오검출 P_md** = `Σ_n (D_n / M_n) / N`",
         gloss_en="Missed detection P_md = sum_n (D_n / M_n) / N, D_n = true targets not associated with a detected object."),
    dict(id="Q_std_pfa_type1_definition", topic="standard_metric", path="prior_work/isac_standard_scenarios.md", line=884,
         quote="**오경보 Type 1** = 표적이 **없는** 드롭에서 무언가를 잡을 확률",
         gloss_en="False alarm Type 1 = probability of detecting something in a drop with no target."),
    dict(id="Q_std_pfa_type2_definition", topic="standard_metric", path="prior_work/isac_standard_scenarios.md", line=885,
         quote="**오경보 Type 2** = 표적이 **있는** 드롭에서 참표적과 **연결되지 않은** 검출객체의 비율",
         gloss_en="False alarm Type 2 = fraction of detected objects not associated with a true target in drops with targets."),
    dict(id="Q_std_both_pfa_mandatory", topic="standard_metric", path="prior_work/isac_standard_scenarios.md", line=886,
         quote="NOTE: Both False alarm probability types are mandatory.", gloss_en="TR 38.765 section 4 note, verbatim."),
    dict(id="Q_std_not_metrics_a", topic="standard_metric", path="prior_work/isac_standard_scenarios.md", line=893,
         quote="Sensing resolution, sensing service latency and refreshing rate are not",
         gloss_en="TR 38.765 section 4.1 verbatim, first half."),
    dict(id="Q_std_not_metrics_b", topic="standard_metric", path="prior_work/isac_standard_scenarios.md", line=894,
         quote="considered as performance metrics** for the evaluation of NR ISAC.",
         gloss_en="TR 38.765 section 4.1 verbatim, second half."),
    dict(id="Q_std_type2_needs_multitarget", topic="standard_metric", path="prior_work/isac_standard_scenarios.md",
         line=1006, quote="**P_fa Type 2** 를 낼 수 있는 다표적 드롭",
         gloss_en="Open to-do: multi-target drops that can produce P_fa Type 2."),
    dict(id="Q_std_clutter_enabled", topic="standard_result", path="prior_work/isac_standard_scenarios.md", line=935,
         quote="clutter mobility and low power clusters enabled",
         gloss_en="TR 38.765 section 6.3.1 condition, verbatim (one source)."),
    dict(id="Q_std_clutter_results", topic="standard_result", path="prior_work/isac_standard_scenarios.md", line=936,
         quote="**P_md 20.00 % · P_fa Type 1 91.00 % · P_fa Type 2 79.00 %**",
         gloss_en="With that clutter setting: P_md 20%, P_fa Type 1 91%, P_fa Type 2 79%."),
    dict(id="Q_std_bistatic_zero", topic="standard_result", path="prior_work/isac_standard_scenarios.md", line=949,
         quote="**바이스태틱 평가는 0 건이다.** 130 건 전부 gNB 모노스태틱이고",
         gloss_en="Bistatic evaluations: 0. All 130 results are gNB monostatic."),
    dict(id="Q_std_detection_focus_link", topic="standard_result", path="prior_work/isac_standard_scenarios.md", line=931,
         quote="[[sionna2-main-task-detection]] 으로 탐지·분류에 집중한 판단이",
         gloss_en="Links the standard's detection bottleneck to the recorded detection-and-classification focus."),
    # -- docs/DRONE_ISAC_PRIOR_READING.md
    dict(id="Q_prf_gate_rule", topic="prior_reading", path="docs/DRONE_ISAC_PRIOR_READING.md", line=233,
         quote="PRF >= 2 f_mD^max", gloss_en="md-testbed quote: PRF must be at least twice the maximum micro-Doppler frequency."),
    dict(id="Q_prf_gate_2_of_45", topic="prior_reading", path="docs/DRONE_ISAC_PRIOR_READING.md", line=247,
         quote="**45개 조합 중 2개만 통과**", gloss_en="Only 2 of 45 (airframe x always-on reference mode) combinations pass."),
    dict(id="Q_protocol_header", topic="x410_protocol", path="docs/DRONE_ISAC_PRIOR_READING.md", line=312,
         quote="**X410 외부 실측 프로토콜 고정**", gloss_en="Fix the X410 outdoor measurement protocol."),
    dict(id="Q_protocol_background_subtraction", topic="x410_protocol", path="docs/DRONE_ISAC_PRIOR_READING.md", line=312,
         quote="배경 S21 코히어런트 차감", gloss_en="Coherent background S21 subtraction."),
    dict(id="Q_protocol_back_to_back", topic="x410_protocol", path="docs/DRONE_ISAC_PRIOR_READING.md", line=312,
         quote="**back-to-back(Tx→Rx 직결) 교정**을 필수 단계로", gloss_en="Back-to-back (TX to RX direct) calibration as a mandatory step."),
    dict(id="Q_protocol_rpm_logged", topic="x410_protocol", path="docs/DRONE_ISAC_PRIOR_READING.md", line=312,
         quote="rpm 은 가정하지 말고 계측한다", gloss_en="Measure rpm rather than assume it."),
    dict(id="Q_mdrt_record", topic="prior_reading", path="docs/DRONE_ISAC_PRIOR_READING.md", line=39,
         quote="**Sionna RT(EM 설정은 스톡, 광선발사기는 개조) + Blender 블레이드 메쉬**로 UAV 로터 마이크로도플러",
         gloss_en="md-rt record: Sionna RT (stock EM settings, modified ray launcher) + Blender blade meshes for rotor micro-Doppler."),
    dict(id="Q_mdrt_citation_authors_title", topic="prior_reading", path="docs/DRONE_ISAC_PRIOR_READING.md", line=39,
         quote="**md-rt** — Li(Changjun)·Mu·Jiang·Feng·Gao·Xu(상하이대/XJTLU), *Micro-Doppler Signature Simulation of "
               "Multirotor UAVs Using Ray Tracing*, IEEE ICCT 2025, pp.359–364",
         gloss_en="md-rt citation as recorded: authors, title, venue, pages."),
    dict(id="Q_mdrt_citation_venue_doi", topic="prior_reading", path="docs/DRONE_ISAC_PRIOR_READING.md", line=597,
         quote="| md-rt | 2025 IEEE 25th International Conference on Communication Technology (ICCT), pp. 359–364 | "
               "DOI 10.1109/ICCT67417.2025.11374154 |",
         gloss_en="md-rt venue and DOI as recorded."),
    dict(id="Q_mdrt_citation_library", topic="prior_reading", path="docs/REFERENCE_LIBRARY.md", line=1531,
         quote="C. Li, S. Mu, J. Jiang, L. Feng, Y. Gao, and S. Xu, \"Micro-Doppler signature simulation of multirotor "
               "UAVs using ray tracing,\" in Proc. IEEE 25th Int. Conf. Commun. Technol. (ICCT), 2025, pp. 359-364, "
               "doi: 10.1109/ICCT67417.2025.11374154.",
         gloss_en="md-rt citation draft in the reference library."),
    dict(id="Q_mdrt_no_amplitude", topic="prior_reading", path="docs/REFERENCE_LIBRARY.md", line=1530,
         quote="산란 진폭은 논문 전체에 한 번도 등장하지 않는다",
         gloss_en="md-rt record: scattering amplitude does not appear anywhere in the paper."),
    dict(id="Q_mdrt_no_amplitude_claim", topic="prior_reading", path="docs/REFERENCE_LIBRARY.md", line=1893,
         quote="진폭 주장 0건", gloss_en="md-rt record: zero amplitude claims."),
    dict(id="Q_mdrt_single_propeller", topic="prior_reading", path="docs/REFERENCE_LIBRARY.md", line=1893,
         quote="표적이 목재 프로펠러 1개이고", gloss_en="md-rt record: the target is one wooden propeller."),
    # -- docs/PRIOR_READING_LOG.md
    dict(id="Q_taylor_poullin_precedent", topic="prior_reading", path="docs/PRIOR_READING_LOG.md", line=202,
         quote="**최근접 선례 — Taylor & Poullin, IEEE TAES 61(4), August 2025, pp.8804-, 게재**",
         gloss_en="Closest precedent: Taylor & Poullin, IEEE TAES 61(4), August 2025, published."),
    dict(id="Q_taylor_poullin_must_cite", topic="prior_reading", path="docs/PRIOR_READING_LOG.md", line=217,
         quote="선행은 있다(Taylor & Poullin, IEEE TAES 61(4), 2025) — 우리 벤치마크 설계의 선행 방법론으로 반드시",
         gloss_en="There is a published precedent (Taylor & Poullin 2025) that must be cited as the method precedent of our benchmark."),
    dict(id="Q_taylor_poullin_doi", topic="prior_reading", path="docs/REFERENCE_LIBRARY.md", line=487,
         quote="DOI `10.1109/TAES.2025.3545000`", gloss_en="Taylor & Poullin DOI as recorded in the repo library."),
    dict(id="Q_taylor_poullin_authors", topic="prior_reading", path="docs/REFERENCE_LIBRARY.md", line=487,
         quote="A. Taylor and D. Poullin. *IEEE Trans. Aerosp. Electron. Syst.*, 2025.",
         gloss_en="Taylor & Poullin authors and journal as recorded in the repo library."),
    dict(id="Q_acquire_2505_24763", topic="prior_reading", path="docs/PRIOR_READING_LOG.md", line=393,
         quote="`2505.24763__detecting-airborne-objects-5gnr-radars.pdf`(5G NR PRS 모노스태틱 UAV 미검출률 곡선",
         gloss_en="To acquire: 2505.24763, 5G NR PRS monostatic UAV miss-rate curves."),
    dict(id="Q_lipase_dataset", topic="prior_reading", path="docs/PRIOR_READING_LOG.md", line=434,
         quote="공개 데이터셋 `github.com/yfsun0327/LIPASE-dataset` (Sun 외 IEEE OJ-COMS 2025",
         gloss_en="Public LIPASE dataset linked from Sun et al., IEEE OJ-COMS 2025."),
    # -- docs/PRIOR_WORK_COMPARISON.md
    dict(id="Q_maksymiuk_2022", topic="prior_reading", path="docs/PRIOR_WORK_COMPARISON.md", line=240,
         quote="Maksymiuk 외, Rényi Entropy…, *Remote Sensing* 2022", gloss_en="Maksymiuk et al., Remote Sensing 2022 (5G SSB passive radar)."),
    dict(id="Q_maksymiuk_2025", topic="prior_reading", path="docs/PRIOR_WORK_COMPARISON.md", line=241,
         quote="\"UAV Intrusion Detection with Passive Radar Based on the 5G Network\", Asilomar 2025",
         gloss_en="Maksymiuk et al., Asilomar 2025, 5G passive radar UAV intrusion detection."),
    dict(id="Q_lipase_12_antennas", topic="prior_reading", path="docs/PRIOR_WORK_COMPARISON.md", line=781,
         quote="**감시 8소자 + 기준 4소자 = 12안테나**", gloss_en="LIPASE: 8 surveillance + 4 reference elements = 12 antennas."),
    dict(id="Q_sionna_detection_range_zero", topic="positioning_old", path="docs/PRIOR_WORK_COMPARISON.md", line=939,
         quote="**Sionna 로 드론 검지거리를 낸 선행 0편.**", gloss_en="Zero precedents that produced drone detection range with Sionna."),
    dict(id="Q_three_standard_novelty", topic="positioning_old", path="docs/PRIOR_WORK_COMPARISON.md", line=1023,
         quote="**통제된 3표준 head-to-head 조명원 벤치마크.**", gloss_en="Surviving novelty 1: controlled three-standard head-to-head illuminator benchmark."),
    dict(id="Q_occupancy_axis_flat", topic="positioning_old", path="docs/PRIOR_WORK_COMPARISON.md", line=1025,
         quote="**점유 축은 SNR50 위에서 사실상 죽어 있다**(WiFi 0.34 dB, LTE 0.09 dB)",
         gloss_en="The occupancy axis is practically flat on SNR50 (WiFi 0.34 dB, LTE 0.09 dB)."),
    dict(id="Q_empirical_pfa_curve", topic="positioning_old", path="docs/PRIOR_WORK_COMPARISON.md", line=1031,
         quote="**명목-vs-경험 Pfa 교정 곡선.**", gloss_en="Surviving novelty 4: nominal-vs-empirical Pfa calibration curve."),
    # -- pw01 notebook
    dict(id="Q_pw01_novelty_combination", topic="positioning_old", path="prior_work/pw01_sionna_isac_papers.ipynb", line=83,
         quote="우리 기여는 **결합**(패시브 바이스태틱 + 자작 SBR+PO 드론 RCS + 상시vs세션 9모드)이다.",
         gloss_en="Our contribution is the combination (passive bistatic + in-house SBR+PO drone scattering + always-on vs session 9 modes)."),
    # -- queues and sweep script
    dict(id="Q_0940_reality_check", topic="queue", path="runners/jobs_0940_antenna.txt", line=20,
         quote="Reality check (AGENTS.md): the real rig is one USRP X410 with six directional antennas whose models,",
         gloss_en="Queue 0940 header (English in source)."),
    dict(id="Q_0940_outdoor_aimed_line", topic="queue", path="runners/jobs_0940_antenna.txt", line=29,
         quote="--els=-60 --env outdoor01_ground --ant-pattern tr38901 --shard 0 --nshards 2",
         gloss_en="First job line of queue 0940: el -60, outdoor ground scene, aimed 3GPP element, shard 0 of 2 "
                  "(unique in the file; n_matches in repo_quotes)."),
    dict(id="Q_0940_supersedes_0938", topic="queue", path="runners/jobs_0940_antenna.txt", line=1,
         quote="# 0940 directional antenna, revised (2026-09-15) — supersedes runners/jobs_0938_antenna.txt",
         gloss_en="Queue 0940 header (English in source)."),
    dict(id="Q_0938_superseded", topic="queue", path="runners/jobs_0938_antenna.txt", line=1,
         quote="# SUPERSEDED 2026-09-15 by runners/jobs_0940_antenna.txt before any line was launched (review fixes).",
         gloss_en="Queue 0938 header (English in source)."),
    dict(id="Q_munich_not_a_result", topic="corpus", path="runners/jobs_0934_bridge2.txt", line=14,
         quote="⛔뮌헨은 결과가 아니다.", gloss_en="Queue 0934 header: the Munich scene is not a result."),
    dict(id="Q_0938_needs_8192_poses", topic="queue", path="runners/jobs_0938_antenna.txt", line=24,
         quote="Whether the BLADE CONTRAST returns needs 8,192 poses.", gloss_en="Queue 0938 header (English in source)."),
    dict(id="Q_sweep_default_carrier", topic="corpus", path="benchmark/elevation_sweep_md.py", line=97,
         quote="FC, RANGE_M = 3.5e9, 10.0", gloss_en="Sweep default carrier constant."),
    dict(id="Q_sweep_carrier_tag_rule", topic="corpus", path="benchmark/elevation_sweep_md.py", line=300,
         quote="안 주면 규약값 3.5 GHz 라 꼬리표가 없다.",
         gloss_en="If --fc-ghz is not given the convention value 3.5 GHz is used and the name carries no carrier tag."),
]

# Draft files written by another session (uncommitted when this script was written). They may change.
DRAFT_FILES = [
    dict(file_id="review_md", path="docs/ISAC_DETECTION_TRACKING_REVIEW_0915.md", role="draft review (primary)"),
    dict(file_id="campaign_json", path="outputs/isac_campaign_design_0915.json", role="draft campaign ledger (primary)"),
    dict(file_id="waveform_json", path="outputs/isac_waveform_benchmark_design_0915.json", role="draft waveform benchmark ledger (companion)"),
    dict(file_id="sources_memo", path="work/isac_sources_0915.md", role="draft source memo (companion)"),
    dict(file_id="queue_json", path="work/isac_queue_latest_0915.json",
         role="draft queue snapshot ledger (companion; linked from the review's queue paragraph)"),
]

GREP_TERMS = [
    # (term_id, group, mode, pattern)
    ("kernel_en", "kernel", "ci", "kernel"), ("kernel_ko", "kernel", "cs", "커널"), ("PathSolver", "kernel", "cs", "PathSolver"),
    ("GHz_2.45", "carrier", "cs", "2.45 GHz"), ("GHz_5.8", "carrier", "cs", "5.8 GHz"), ("GHz_3.5", "carrier", "cs", "3.5 GHz"),
    ("GHz_4.9", "carrier", "cs", "4.9 GHz"), ("MHz_100", "carrier", "cs", "100 MHz"), ("MHz_20", "carrier", "cs", "20 MHz"),
    ("kHz_30", "carrier", "cs", "30 kHz"), ("kHz_15", "carrier", "cs", "15 kHz"),
    ("RX0", "channel_map", "cs", "RX0"), ("reference_channel_ko", "channel_map", "cs", "기준 채널"),
    ("lambda_half", "channel_map", "cs", "λ/2"), ("half_wavelength_ko", "channel_map", "cs", "반파장"),
    ("TR_38.765", "metrics", "cs", "38.765"), ("Type_1", "metrics", "cs", "Type 1"), ("Type_2", "metrics", "cs", "Type 2"),
    ("P_md", "metrics", "cs", "P_md"), ("UMa-AV", "metrics", "cs", "UMa-AV"), ("GOSPA", "metrics", "cs", "GOSPA"),
    ("diffuse_en", "diffuse", "ci", "diffuse"), ("diffuse_ko", "diffuse", "cs", "확산"),
    ("F1_token", "diffuse", "re", r"(?<![A-Za-z0-9])F1(?![0-9])"), ("R0D0E0F1", "diffuse", "cs", "R0D0E0F1"),
    ("arXiv_2608.05826", "related_work", "cs", "2608.05826"), ("arXiv_2608.10784", "related_work", "cs", "2608.10784"),
    ("arXiv_2412.20788", "related_work", "cs", "2412.20788"), ("arXiv_2509.25732", "related_work", "cs", "2509.25732"),
    ("arXiv_2504.05168", "related_work", "cs", "2504.05168"), ("arXiv_2605.23561", "related_work", "cs", "2605.23561"),
    ("arXiv_2603.14351", "related_work", "cs", "2603.14351"), ("arXiv_2505.24763", "related_work", "cs", "2505.24763"),
    ("Taylor", "related_work", "cs", "Taylor"), ("Poullin", "related_work", "cs", "Poullin"),
    ("Maksymiuk", "related_work", "cs", "Maksymiuk"), ("LIPASE", "related_work", "cs", "LIPASE"),
    ("jobs_0936_line3", "kernel", "cs", "jobs_0936_attrib.txt:3"), ("free_space_ko", "kernel", "cs", "자유공간"),
    ("free_space_en", "kernel", "ci", "free space"), ("free_space_hyphen_en", "kernel", "ci", "free-space"),
    ("experiment_x410", "channel_map", "cs", "experiment_x410"),
    ("jobs_0938", "queue", "cs", "jobs_0938_antenna"), ("jobs_0940", "queue", "cs", "jobs_0940_antenna"),
]

# Anchor texts searched in the drafts at run time (line numbers are found, not assumed).
DRAFT_ANCHORS = {
    "D01_kernel_arms": [
        ("review_md", "주 실험은 PathSolver를 중심으로 구성하고, 우리 커널은 표적 산란의 민감도 비교 및 후속 결합 모델로 둔다."),
        ("review_md", "**권장 하이브리드 식.**"),
        ("review_md", "자세별 정적 커널, 로터 포함 복소 커널, 동적 메쉬 PathSolver"),
        ("review_md", "| 커널·경로 출처를 통제 비교에 연결한다"),
        ("review_md", "출처 발주서의 이전 논문 분리 결정도 이 구성에 반영했다."),
        ("review_md", "근거: `runners/jobs_0936_attrib.txt:3`"),
        ("review_md", "KS[커널 표적 응답 비교] -. 교정된 후속 결합 .-> ENV"),
        ("review_md", "**PathSolver의 담당 범위.** 경로 지연·입출사각·복소 계수·배열·차폐·환경 반사를 만드는 주 채널 생성기로 사용한다."),
        ("review_md", "**실외 모델링 순서.** 점표적 자유공간"),
    ],
    "D02_carrier_bandwidth": [
        ("review_md", "안테나 지원 여부를 확인할 후보는 2.45 GHz, 다른 후보는 5.8 GHz다."),
        ("review_md", "반송파를 바꾸면 자료를 재계산한다."),
        ("review_md", "| 명목 활성 대역 | 15.625 MHz |"),
        ("review_md", "| NR FR1 downlink normal CP, mu=0 | 20 MHz | 1272 | 15 kHz |"),
    ],
    "D03_channel_map": [
        ("review_md", "| X410 감시 RX | 동시 감시 배열 | 3 |"),
        ("review_md", "| X410 통신 RX | 분리 배치한 안테나에서 통신 수신·복호 | 1 |"),
        ("review_md", "자체 송신 심볼을 디지털 참조로 쓸 수 있다."),
        ("sources_memo", "물리 크기와 위상중심 때문에 반파장 간격이 불가능할 수 있고"),
        ("sources_memo", "| RX0 → 기준/통신 수신 안테나 |"),
    ],
    "D04_tr38765_metrics": [
        ("review_md", "**보고할 성능.** 같은 프레임 오경보율의 Pd"),
        ("review_md", "다중 표적 확장에는 GOSPA와 ID 전환을 따로 보고한다."),
        ("sources_memo", "따라서 이번 검토에서는 저장소의 종전 표준 요약만으로 최신 채택값이나 규격 준수 여부를 추가 단정하지 않았다."),
    ],
    "D05_diffuse_switch": [
        ("review_md", "**실외 모델링 순서.**"),
        ("review_md", "**PathSolver의 담당 범위.**"),
    ],
    "D06_related_work": [
        ("review_md", "**문헌과의 위치.**"),
        ("review_md", "**Sionna 연계도 구체적인 차별점이 필요하다.**"),
    ],
    "D07_queue_snapshot": [
        ("review_md", "지향성 큐 발주 30줄 중 시작 기록은 0줄이다."),
        ("queue_json", '"job_file": "runners/jobs_0938_antenna.txt"'),
    ],
    "D08_rotor_relinking_followup": [
        ("sources_memo", "| 후속: 로터 정보가 트랙 재연결에 주는 추가 가치 |"),
    ],
}

FORBIDDEN_IN_LEDGER = ["chamber", "챔버", "무향실", "anechoic", "dbsm", "validated", "verified against measurement"]

# --------------------------------------------------------------------------------------------------------


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Ledger:
    def __init__(self, root: Path, out: Path):
        self.root, self.out = root, out
        self.hashes: dict[str, str] = {}
        self.data: dict = {}

    def rel(self, p: Path) -> str:
        try:
            return str(p.resolve().relative_to(self.root))
        except ValueError:
            return str(p)

    def read_text(self, relpath: str) -> str:
        p = self.root / relpath
        txt = p.read_text(encoding="utf-8")
        self.hashes[relpath] = sha256_file(p)
        return txt

    def read_json(self, relpath: str):
        return json.loads(self.read_text(relpath))

    def checkpoint(self, status: str):
        self.data["_meta"]["status"] = status
        self.data["_meta"]["source_hashes"] = [dict(path=k, sha256=v) for k, v in sorted(self.hashes.items())]
        self.out.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.out.with_suffix(".json.partial")
        tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        os.replace(tmp, self.out)


def git_head(root: Path) -> str | None:
    try:
        return subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True,
                              check=True).stdout.strip()
    except Exception:
        return None


def git_tracked(root: Path, relpath: str) -> bool | None:
    try:
        r = subprocess.run(["git", "-C", str(root), "ls-files", "--", relpath], capture_output=True, text=True, check=True)
        return bool(r.stdout.strip())
    except Exception:
        return None


def get_path(obj, path: str):
    """Follow a dotted key path with [i] list indices (keys here contain no dots)."""
    cur = obj
    for part in re.findall(r"[^.\[\]]+|\[\d+\]", path):
        cur = cur[int(part[1:-1])] if part.startswith("[") else cur[part]
    return cur


# -------------------------------------------------------------------------------------------- sections


def _window(lines: list[str], start: int, n: int) -> str:
    """Text of n consecutive lines starting at 1-based line `start`; a single line is kept as is."""
    if n == 1:
        return lines[start - 1]
    return " ".join(x.strip() for x in lines[start - 1:start - 1 + n])


def section_repo_quotes(L: Ledger) -> dict:
    rows, failures = [], 0
    cache: dict[str, list[str]] = {}
    for q in QUOTES:
        path = q["path"]
        if path not in cache:
            cache[path] = L.read_text(path).splitlines()
        lines = cache[path]
        want, n = q["line"], int(q.get("n_lines", 1))
        hits = [i for i in range(1, len(lines) - n + 2) if q["quote"] in _window(lines, i, n)]
        status, line = "not_found", None
        if want in hits:
            status, line = "ok", want
        elif len(hits) == 1:
            status, line = "moved", hits[0]
        elif len(hits) > 1:
            status, line = "ambiguous", hits[0]
        if status in ("not_found", "ambiguous"):
            failures += 1
        rows.append(dict(id=q["id"], topic=q["topic"], path=path, line=line, expected_line=want, n_lines=n,
                         line_end=None if line is None else line + n - 1, n_matches=len(hits), status=status,
                         quote=q["quote"], gloss_en=q["gloss_en"], sha256=L.hashes[path]))
    L.data["repo_quotes"] = rows
    return dict(n_quotes=len(rows), n_failures=failures,
                n_moved=sum(r["status"] == "moved" for r in rows))


def quote_line_text(L: Ledger, qid: str) -> str:
    row = next(r for r in L.data["repo_quotes"] if r["id"] == qid)
    if row["line"] is None:
        raise SystemExit(f"quote {qid} not found; cannot parse numbers from it")
    return (L.root / row["path"]).read_text(encoding="utf-8").splitlines()[row["line"] - 1]


def section_standards_numbers(L: Ledger):
    src = "outputs/isac_standard_gaps.json"
    g = L.read_json(src)
    keys = [
        ("perf_missed_detection", "tr38765_clause9.performance_objectives.missed_detection"),
        ("perf_false_alarm_type1", "tr38765_clause9.performance_objectives.false_alarm_type1"),
        ("perf_false_alarm_type2", "tr38765_clause9.performance_objectives.false_alarm_type2"),
        ("perf_horizontal_accuracy_m_90pct", "tr38765_clause9.performance_objectives.horizontal_accuracy_m_at_90pct"),
        ("perf_vertical_accuracy_m_90pct", "tr38765_clause9.performance_objectives.vertical_accuracy_m_at_90pct"),
        ("perf_velocity_accuracy_mps_90pct", "tr38765_clause9.performance_objectives.velocity_accuracy_mps_at_90pct"),
        ("n_results_total", "tr38765_clause9.n_results.total"),
        ("n_results_baseline1", "tr38765_clause9.n_results.baseline1"),
        ("n_results_baseline2", "tr38765_clause9.n_results.baseline2"),
        ("n_results_other", "tr38765_clause9.n_results.other"),
        ("n_results_bistatic", "tr38765_clause9.n_results.bistatic"),
        ("not_metrics_quote", "tr38765_clause9.not_metrics_ko"),
        ("umaav_elevation_median_deg", "umaav_geometry.elevation_deg_our_convention.median"),
        ("umaav_elevation_p5_deg", "umaav_geometry.elevation_deg_our_convention.p5"),
        ("umaav_elevation_p95_deg", "umaav_geometry.elevation_deg_our_convention.p95"),
        ("umaav_elevation_convention", "umaav_geometry.elevation_deg_our_convention.convention_ko"),
        ("umaav_frac_el_below_minus20", "umaav_geometry.frac_el_below_minus20"),
        ("umaav_n_samples", "umaav_geometry.n_samples"),
        ("umaav_source", "umaav_geometry.source"),
        ("tr38765_source", "tr38765_clause9.source"),
        ("umaav_bs_height_m", "umaav_geometry.assumptions.bs_height_m"),
        ("umaav_target_height_m", "umaav_geometry.assumptions.target_height_m"),
        ("umaav_min_bs_target_3d_m", "umaav_geometry.assumptions.min_bs_target_3d_m"),
    ]
    rows = [dict(id=i, source=src, key_path=k, value=get_path(g, k)) for i, k in keys]
    L.data["standards_numbers"] = rows
    val = {r["id"]: r["value"] for r in rows}
    alt = _nums(r"고도 ([\d.]+)–([\d.]+) m", quote_line_text(L, "Q_std_umaav_altitude_speed"))
    spd = _nums(r"수평속도 ([\d.]+)–([\d.]+) km/h", quote_line_text(L, "Q_std_umaav_altitude_speed"))
    gnb = _nums(r"gNB 높이 ([\d.]+) m", quote_line_text(L, "Q_std_umaav_gnb_height"))[0]
    L.data["standards_numbers_quote_checks"] = [
        dict(id="umaav_target_height_quote_vs_ledger", repo_quote_id="Q_std_umaav_altitude_speed",
             standards_number_id="umaav_target_height_m", parsed_from_quote=alt, ledger_value=val["umaav_target_height_m"],
             agree=[float(x) for x in val["umaav_target_height_m"]] == alt),
        dict(id="umaav_bs_height_quote_vs_ledger", repo_quote_id="Q_std_umaav_gnb_height",
             standards_number_id="umaav_bs_height_m", parsed_from_quote=gnb, ledger_value=val["umaav_bs_height_m"],
             agree=float(val["umaav_bs_height_m"]) == gnb),
        dict(id="umaav_horizontal_speed_kmh_quote_only", repo_quote_id="Q_std_umaav_altitude_speed",
             standards_number_id=None, parsed_from_quote=spd, ledger_value=None, agree=None),
    ]
    L.data["standards_numbers_source_meta"] = dict(source=src, generator=g.get("_meta", {}).get("script"),
                                                   generated=g.get("_meta", {}).get("generated"),
                                                   primary_sources=g.get("_meta", {}).get("primary_sources"))


def section_corpus_counts(L: Ledger):
    src_dir = L.root / "outputs" / "elev_sweep_shards"
    sys.path.insert(0, str(L.root / "src"))
    import arm_grammar  # noqa: E402  (repo module; parses arm names by grammar, never by substring)
    L.hashes["src/arm_grammar.py"] = sha256_file(L.root / "src" / "arm_grammar.py")
    L.read_text("benchmark/elevation_sweep_md.py")  # hash only: the naming rule quoted in repo_quotes lives here

    names = sorted(n for n in os.listdir(src_dir) if n.endswith(".npz"))
    suffix = re.compile(r"^(.*)_el([+-]?[0-9.]+)_(\d+)$")
    parsed, bad = [], []
    for n in names:
        m = suffix.match(n[:-4])
        if not m:
            bad.append(dict(name=n, reason="no _el<deg>_<shard> suffix"))
            continue
        try:
            parsed.append(arm_grammar.parse(m.group(1)))
        except Exception as e:  # noqa: BLE001 -- recorded, never silently dropped
            bad.append(dict(name=n, reason=f"{type(e).__name__}: {str(e)[:160]}"))

    def is_outdoor(f):
        return str(f.get("env") or "").startswith("outdoor")

    outdoor = [f for f in parsed if is_outdoor(f)]
    env_counts: dict[str, int] = {}
    for f in parsed:
        key = str(f.get("env"))
        env_counts[key] = env_counts.get(key, 0) + 1
    nvidia = [f for f in parsed if str(f.get("env") or "").startswith("sionna-")]
    ps_outdoor = [f for f in outdoor if f.get("engine") == "sionna"]
    fbit = lambda f: (f.get("switches") or "")[-2:]  # noqa: E731  e.g. 'F1'
    dbit = lambda f: re.search(r"D(\d)", f.get("switches") or "")  # noqa: E731

    fields_all = sorted({k for f in parsed for k in f})
    motion_like = [k for k in fields_all if re.search(r"vel|traj|speed|motion", k)]
    rows = [
        dict(id="shards_total", count=len(names), definition="*.npz files in outputs/elev_sweep_shards"),
        dict(id="shards_parse_failures", count=len(bad), definition="file names that src/arm_grammar.py could not parse"),
        dict(id="shards_default_carrier", count=sum(f.get("fc") is None for f in parsed),
             definition="parsed names with no _fc tag, i.e. the default carrier of benchmark/elevation_sweep_md.py "
                        "(see repo_quotes Q_sweep_default_carrier, Q_sweep_carrier_tag_rule)"),
        dict(id="shards_with_carrier_tag", count=sum(f.get("fc") is not None for f in parsed),
             definition="parsed names with an _fc<MHz> tag"),
        dict(id="outdoor01_family_shards", count=sum(str(f.get("env") or "").startswith("outdoor01") for f in parsed),
             definition="parsed names whose env starts with 'outdoor01' (outdoor01, outdoor01_ground, outdoor01_bldg; "
                        "per-env counts in corpus_counts_detail.env_counts); the NVIDIA stock scenes are counted "
                        "separately below"),
        dict(id="nvidia_scene_shards", count=len(nvidia),
             definition="parsed names whose env starts with 'sionna-' (NVIDIA stock scenes shipped with Sionna RT)",
             result_use="see the two per-scene rows"),
        dict(id="nvidia_simple_street_canyon_shards",
             count=sum(f.get("env") == "sionna-simple_street_canyon" for f in parsed),
             definition="parsed names with env 'sionna-simple_street_canyon'", result_use="counted as corpus"),
        dict(id="nvidia_munich_shards", count=sum(f.get("env") == "sionna-munich" for f in parsed),
             definition="parsed names with env 'sionna-munich'", result_use="not used as a result",
             repo_quote_ids=["Q_munich_not_a_result"]),
        dict(id="outdoor_pathsolver_shards", count=len(ps_outdoor), definition="outdoor shards with engine 'sionna' (PathSolver)"),
        dict(id="outdoor_pathsolver_diffuse_on", count=sum(fbit(f) == "F1" for f in ps_outdoor),
             definition="outdoor PathSolver shards whose switch tag ends in F1 (diffuse on)"),
        dict(id="outdoor_pathsolver_diffuse_off", count=sum(fbit(f) == "F0" for f in ps_outdoor),
             definition="outdoor PathSolver shards whose switch tag ends in F0"),
        dict(id="outdoor_pathsolver_diffraction_on", count=sum(bool(dbit(f)) and dbit(f).group(1) == "1" for f in ps_outdoor),
             definition="outdoor PathSolver shards with D1 in the switch tag (diffraction on)"),
        dict(id="outdoor_pathsolver_default_carrier", count=sum(f.get("fc") is None for f in ps_outdoor),
             definition="outdoor PathSolver shards with no _fc tag"),
        dict(id="outdoor_pathsolver_rt210", count=sum(f.get("solver_build") == "210" for f in ps_outdoor),
             definition="outdoor PathSolver shards carrying the _rt210 build tag"),
        dict(id="outdoor_ground_rt210_depth2_8192", count=sum(
            f.get("solver_build") == "210" and f.get("max_depth") == "2" and f.get("n_poses") == "8192"
            and str(f.get("env")).startswith("outdoor01_ground") for f in ps_outdoor),
             definition="outdoor01_ground* PathSolver shards at build 2.1.0, depth 2, 8192 poses (any antenna)"),
        dict(id="outdoor_directional_antenna_shards", count=sum(f.get("ant") is not None for f in ps_outdoor),
             definition="outdoor PathSolver shards whose name carries an antenna-pattern tag (ant)"),
        dict(id="arm_grammar_motion_fields", count=len(motion_like),
             definition="fields in the parsed arm grammar whose name mentions velocity/trajectory/speed/motion "
                        f"(fields seen: {len(fields_all)})"),
    ]
    L.data["corpus_counts"] = rows
    L.data["corpus_counts_detail"] = dict(parse_failure_examples=bad[:10], fields_seen=fields_all,
                                          motion_like_fields=motion_like,
                                          env_counts=[dict(env=k, count=v) for k, v in sorted(env_counts.items())])


def _ast_defaults(src: str) -> dict:
    tree = ast.parse(src)
    out = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                out[node.targets[0].id] = ast.literal_eval(node.value)
            except Exception:  # noqa: BLE001
                pass
        if isinstance(node, ast.ClassDef):
            for st in node.body:
                if isinstance(st, ast.AnnAssign) and isinstance(st.target, ast.Name) and st.value is not None:
                    try:
                        out[f"{node.name}.{st.target.id}"] = ast.literal_eval(st.value)
                    except Exception:  # noqa: BLE001
                        pass
    return out


def _nums(pattern: str, text: str) -> list[float]:
    m = re.search(pattern, text)
    if not m:
        raise SystemExit(f"pattern {pattern!r} not found in {text!r}")
    return [float(x) for x in m.groups()]


def section_alignment(L: Ledger):
    x410_src = L.read_text("src/experiment_x410.py")
    d = _ast_defaults(x410_src)
    c0 = d["C0"]
    fc_x = d["X410Scenario.carrier_hz"]
    n_surv = d["X410Scenario.n_surv"]
    n_rx = d["X410.n_rx"]
    k_a, k_b = _nums(r"np\.degrees\(([\d.]+) \* ([\d.]+) / N\)", quote_line_text(L, "Q_x410_aoa_formula"))
    half_lambda_cm = c0 / fc_x / 2.0 * 100.0
    aoa_deg = math.degrees(k_a * k_b / n_surv)

    tr_fc = [v * 1e9 for v in _nums(r"\*\*([\d.]+) or ([\d.]+) GHz\*\*", quote_line_text(L, "Q_std_fr1_carrier"))]
    tr_bw = _nums(r"\*\*([\d.]+) MHz\*\*", quote_line_text(L, "Q_std_fr1_bandwidth"))[0] * 1e6
    tr_scs = _nums(r"SCS ([\d.]+) kHz", quote_line_text(L, "Q_std_fr1_scs"))[0] * 1e3
    corpus_fc = _nums(r"FC, RANGE_M = ([\d.e+]+),", quote_line_text(L, "Q_sweep_default_carrier"))[0]

    camp_path, wf_path = "outputs/isac_campaign_design_0915.json", "outputs/isac_waveform_benchmark_design_0915.json"
    rows = []

    def add(id_, value, source, note):
        rows.append(dict(id=id_, value=value, source=source, note=note))

    add("x410_record_carrier_hz", fc_x, "src/experiment_x410.py:X410Scenario.carrier_hz (ast)", "recorded scenario carrier")
    add("x410_record_n_rx", n_rx, "src/experiment_x410.py:X410.n_rx (ast)", "receive channels of the recorded X410 model")
    add("x410_record_n_surveillance", n_surv, "src/experiment_x410.py:X410Scenario.n_surv (ast)", "RX1-3 surveillance array size")
    add("x410_record_n_reference", n_rx - n_surv, "computed n_rx - n_surv", "RX0 reference channel count in the recorded map")
    add("x410_record_half_wavelength_cm", half_lambda_cm, "computed C0 / carrier_hz / 2 (C0 from src/experiment_x410.py)",
        "element spacing the recorded map needs at its carrier")
    add("x410_record_aoa_resolution_deg", aoa_deg, "computed with the formula at src/experiment_x410.py:167",
        "angle resolution the recorded script prints for the 3-element lambda/2 array")
    add("tr38765_fr1_carriers_hz", tr_fc, "parsed from repo_quotes Q_std_fr1_carrier", "TR 38.765 Annex A FR1 carriers")
    add("tr38765_fr1_bandwidth_hz", tr_bw, "parsed from repo_quotes Q_std_fr1_bandwidth", "TR 38.765 Annex A FR1 bandwidth")
    add("tr38765_fr1_scs_hz", tr_scs, "parsed from repo_quotes Q_std_fr1_scs", "TR 38.765 Annex A FR1 subcarrier spacing")
    add("corpus_default_carrier_hz", corpus_fc, "parsed from repo_quotes Q_sweep_default_carrier", "PathSolver corpus default carrier")
    add("corpus_carrier_in_tr38765_fr1", any(abs(corpus_fc - t) < 1.0 for t in tr_fc), "computed",
        "True if the corpus default carrier equals a TR 38.765 FR1 carrier (the repo table records the carrier as "
        "different: repo_quotes Q_std_repo_carrier_differs)")

    draft_ok = (L.root / camp_path).exists()
    if draft_ok:
        camp = L.read_json(camp_path)
        fcs = [f["fc_hz"] for f in camp["waveform"]["frequencies"]]
        hw = camp["hardware"]
        add("draft_campaign_carriers_hz", fcs, f"{camp_path}:waveform.frequencies[*].fc_hz", "draft candidate carriers")
        add("draft_campaign_half_wavelengths_m", [f["half_wavelength_m"] for f in camp["waveform"]["frequencies"]],
            f"{camp_path}:waveform.frequencies[*].half_wavelength_m", "draft's own lambda/2 at its carriers")
        add("draft_campaign_active_bandwidth_hz", camp["waveform"]["active_bandwidth_hz"],
            f"{camp_path}:waveform.active_bandwidth_hz", "draft custom OFDM active band")
        add("draft_campaign_scs_hz", camp["waveform"]["subcarrier_spacing_hz"], f"{camp_path}:waveform.subcarrier_spacing_hz",
            "draft custom OFDM subcarrier spacing")
        add("draft_campaign_any_carrier_equals_corpus", any(abs(f - corpus_fc) < 1.0 for f in fcs), "computed",
            "True if a draft carrier equals the corpus default carrier")
        add("draft_campaign_any_carrier_in_tr38765_fr1", any(abs(f - t) < 1.0 for f in fcs for t in tr_fc), "computed",
            "True if a draft carrier equals a TR 38.765 FR1 carrier")
        add("draft_campaign_bandwidth_over_tr38765", camp["waveform"]["active_bandwidth_hz"] / tr_bw, "computed",
            "draft active band divided by the TR 38.765 FR1 bandwidth")
        for k in ("x410_tx_used", "x410_sensing_rx_used", "x410_communication_rx_used", "spare_antennas",
                  "directional_antennas_owned"):
            add(f"draft_campaign_{k}", hw[k], f"{camp_path}:hardware.{k}", "draft channel/antenna allocation")
        rx_keys = sorted(k for k in hw if k.endswith("_rx_used"))
        ref_keys = [k for k in rx_keys if re.search(r"ref", k, re.IGNORECASE)]
        x410_rx_keys = [k for k in rx_keys if k.startswith("x410_")]
        add("draft_campaign_reference_rx_used", sum(int(hw[k]) for k in ref_keys),
            f"computed: sum of {camp_path}:hardware.*_rx_used keys whose name contains 'ref' "
            f"(rx_used keys present: {rx_keys}; matching: {ref_keys})",
            "RX channels the draft allocates as a reference channel (0 when no such key exists)")
        add("draft_campaign_x410_rx_allocated", sum(int(hw[k]) for k in x410_rx_keys),
            f"computed: sum of {camp_path}:hardware.x410_*_rx_used ({x410_rx_keys})", "X410 RX channels the draft allocates")
        add("draft_campaign_x410_rx_unallocated", n_rx - sum(int(hw[k]) for k in x410_rx_keys),
            "computed x410_record_n_rx - draft_campaign_x410_rx_allocated",
            "X410 RX channels left for a reference channel under the draft allocation")
        tm = camp["model_comparison"]["target_models"]
        add("draft_campaign_target_models", tm, f"{camp_path}:model_comparison.target_models", "draft comparison arms")
        add("draft_campaign_kernel_arms_n", sum("kernel" in s.lower() for s in tm), "computed over target_models",
            "entries mentioning 'kernel'")
        add("draft_campaign_kernel_only_arms_n", sum("kernel" in s.lower() and "pathsolver" not in s.lower() for s in tm),
            "computed over target_models", "entries mentioning 'kernel' but not 'PathSolver' (kernel comparison arms)")
        add("draft_campaign_environment_kernel_coupled_arms_n",
            sum("kernel" in s.lower() and "pathsolver" in s.lower() and "environment" in s.lower() for s in tm),
            "computed over target_models", "entries mentioning 'environment', 'PathSolver' and 'kernel' together "
                                            "(a kernel target model coupled into environment channels)")
        add("draft_campaign_pathsolver_arms_n", sum("pathsolver" in s.lower() for s in tm), "computed over target_models",
            "entries mentioning 'PathSolver'")
    if (L.root / wf_path).exists():
        wf = L.read_json(wf_path)
        profs = [dict(id=p["id"], stage=p["stage"], nominal_channel_bandwidth_hz=p["nominal_channel_bandwidth_hz"],
                      subcarrier_spacing_hz=p["subcarrier_spacing_hz"]) for p in wf["profiles"]]
        add("draft_waveform_profiles", profs, f"{wf_path}:profiles[*]", "draft standard profiles")
        add("draft_waveform_nr_mu0_20mhz_15khz_profiles_n",
            sum(p["id"].startswith("nr_") and "mu0" in p["id"] and abs(p["nominal_channel_bandwidth_hz"] - 20e6) < 1
                and abs(p["subcarrier_spacing_hz"] - 15e3) < 1 for p in profs),
            "computed over profiles", "NR mu=0 profiles with 20 MHz nominal bandwidth and 15 kHz spacing")
        main = [p for p in profs if p["stage"] == "main"]
        add("draft_waveform_main_profiles_matching_tr38765_bw_and_scs",
            sum(abs(p["nominal_channel_bandwidth_hz"] - tr_bw) < 1 and abs(p["subcarrier_spacing_hz"] - tr_scs) < 1 for p in main),
            "computed", f"main-stage profiles with TR 38.765 FR1 bandwidth and spacing (of {len(main)})")
        add("draft_waveform_any_profile_matching_tr38765_bw_and_scs",
            sum(abs(p["nominal_channel_bandwidth_hz"] - tr_bw) < 1 and abs(p["subcarrier_spacing_hz"] - tr_scs) < 1 for p in profs),
            "computed", f"all profiles with TR 38.765 FR1 bandwidth and spacing (of {len(profs)})")
    L.data["alignment_checks"] = rows


def _count(text: str, mode: str, pat: str) -> int:
    if mode == "cs":
        return text.count(pat)
    if mode == "ci":
        return text.lower().count(pat.lower())
    return len(re.findall(pat, text))


def section_drafts(L: Ledger):
    files, counts, texts = [], [], {}
    for df in DRAFT_FILES:
        p = L.root / df["path"]
        exists = p.exists()
        row = dict(file_id=df["file_id"], path=df["path"], role=df["role"], exists=exists,
                   git_tracked=git_tracked(L.root, df["path"]) if exists else None,
                   sha256=None, size_bytes=None, n_lines=None, mtime_utc=None)
        if exists:
            txt = L.read_text(df["path"])
            texts[df["file_id"]] = txt
            st = p.stat()
            row.update(sha256=L.hashes[df["path"]], size_bytes=st.st_size, n_lines=len(txt.splitlines()),
                       mtime_utc=_dt.datetime.fromtimestamp(st.st_mtime, _dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
        files.append(row)
        for term_id, group, mode, pat in GREP_TERMS:
            counts.append(dict(file_id=df["file_id"], term_id=term_id, group=group, mode=mode, pattern=pat,
                               count=_count(texts[df["file_id"]], mode, pat) if exists else None))
    L.data["draft_files"] = files
    L.data["draft_grep_counts"] = counts
    return texts


def _anchor_rows(texts: dict, cid: str) -> list[dict]:
    out = []
    path_of = {d["file_id"]: d["path"] for d in DRAFT_FILES}
    for fid, anchor in DRAFT_ANCHORS[cid]:
        lines = texts.get(fid, "").splitlines()
        hits = [i + 1 for i, s in enumerate(lines) if anchor in s]
        out.append(dict(file_id=fid, path=path_of[fid], anchor=anchor, lines=hits,
                        status="found" if hits else ("file_missing" if fid not in texts else "anchor_not_found")))
    return out


def _snippets(texts: dict, fid: str, pat: str, width: int = 50) -> list[dict]:
    out = []
    for i, s in enumerate(texts.get(fid, "").splitlines(), 1):
        j = s.find(pat)
        while j >= 0:
            out.append(dict(line=i, snippet=s[max(0, j - width):j + len(pat) + width]))
            j = s.find(pat, j + 1)
    return out


def _gc(L: Ledger, fid: str, term_ids: list[str]) -> list[dict]:
    return [dict(file_id=r["file_id"], term_id=r["term_id"], count=r["count"])
            for r in L.data["draft_grep_counts"] if r["file_id"] == fid and r["term_id"] in term_ids]


def _cc(L: Ledger, ids: list[str]) -> list[dict]:
    return [dict(id=r["id"], count=r["count"]) for r in L.data["corpus_counts"] if r["id"] in ids]


def _ac(L: Ledger, ids: list[str]) -> list[dict]:
    return [dict(id=r["id"], value=r["value"]) for r in L.data["alignment_checks"] if r["id"] in ids]


_OPS = {
    "eq": lambda o, e: o == e,
    "ge": lambda o, e: o is not None and o >= e,
    "gt": lambda o, e: o is not None and o > e,
    "in": lambda o, e: o in e,
}


def _observe(L: Ledger, texts: dict, kind: str, ref: dict):
    if kind == "grep":
        return next(r["count"] for r in L.data["draft_grep_counts"]
                    if r["file_id"] == ref["file_id"] and r["term_id"] == ref["term_id"])
    if kind == "alignment":
        hit = [r["value"] for r in L.data["alignment_checks"] if r["id"] == ref["id"]]
        return hit[0] if hit else None
    if kind == "corpus":
        return next(r["count"] for r in L.data["corpus_counts"] if r["id"] == ref["id"])
    if kind == "quote":
        return next(r[ref["field"]] for r in L.data["repo_quotes"] if r["id"] == ref["id"])
    if kind == "anchors_missing":
        return sum(a["status"] != "found" for a in _anchor_rows(texts, ref["conflict_id"]))
    raise ValueError(kind)


def _pa(L: Ledger, texts: dict, claim: str, kind: str, ref: dict, op: str, expected, observed=None) -> dict:
    """One prose assertion: the observed run-time value must satisfy op against the value the prose states."""
    if kind != "value":
        observed = _observe(L, texts, kind, ref)
    return dict(claim=claim, kind=kind, ref=ref, op=op, expected=expected, observed=observed,
                holds=bool(_OPS[op](observed, expected)))


def section_conflicts(L: Ledger, texts: dict):
    rel = ["arXiv_2608.05826", "arXiv_2608.10784", "arXiv_2412.20788", "arXiv_2509.25732", "arXiv_2504.05168",
           "arXiv_2605.23561", "arXiv_2603.14351", "arXiv_2505.24763", "Taylor", "Poullin", "Maksymiuk", "LIPASE",
           "TR_38.765"]
    four = ("review_md", "campaign_json", "waveform_json", "sources_memo")
    jobs0940 = L.read_text("runners/jobs_0940_antenna.txt").splitlines()
    jobs0938 = L.read_text("runners/jobs_0938_antenna.txt").splitlines()
    n_job_lines = sum(1 for x in jobs0940 if x.startswith("--engine"))
    n_job_lines_0938 = sum(1 for x in jobs0938 if x.startswith("--engine"))
    q0938 = None
    if "queue_json" in texts:
        q0938 = json.loads(texts["queue_json"]).get("queues", {}).get("0938")
    review_30 = re.search(r"지향성 큐 발주 (\d+)줄 중 시작 기록은 (\d+)줄이다", texts.get("review_md", ""))
    sd = next(r["count"] for r in L.data["corpus_counts"] if r["id"] == "shards_default_carrier")
    st = next(r["count"] for r in L.data["corpus_counts"] if r["id"] == "shards_total")
    frac_default = sd / st if st else None

    def A(claim, kind, ref, op, expected, observed=None):
        return _pa(L, texts, claim, kind, ref, op, expected, observed)

    def G(fid, term, op, expected, claim):
        return A(claim, "grep", dict(file_id=fid, term_id=term), op, expected)

    ok_status = ["ok", "moved"]
    rows = [
        dict(id="D01_kernel_arms",
             draft_location=_anchor_rows(texts, "D01_kernel_arms"),
             conflict="Restated against the engine roles recorded on 2026-09-15 evening (AGENTS.md): our kernel is the "
                      "free-space reference that establishes under which settings PathSolver output is reasonable, and "
                      "environments are then simulated with PathSolver alone, comparing the engines only on relative "
                      "quantities. The draft keeps PathSolver as the main environment channel generator, which matches. "
                      "It differs in the kernel's role: the draft couples a kernel target model into environment channels "
                      "(hybrid formula, flow-diagram edge, campaign arm 'environment PathSolver plus local kernel') and "
                      "lists kernel comparison arms in the campaign, whereas under the new roles the kernel belongs in "
                      "free-space cross-checks and the environment runs are PathSolver-only. The draft also cites "
                      "runners/jobs_0936_attrib.txt:3, the note that the new roles supersede.",
             matches_new_roles=[
                 "The main experiment is centred on PathSolver (main-experiment sentence).",
                 "PathSolver is the main channel generator for delays, angles, complex coefficients, arrays, blocking "
                 "and environment reflections (PathSolver scope paragraph); the campaign lists PathSolver arms.",
                 "The outdoor modelling order starts from a point target in free space before ground, wall and "
                 "building scenes, i.e. free space comes first.",
                 "The kernel stays in the work rather than being dropped.",
             ],
             differs_from_new_roles=[
                 "The kernel is kept as a target-scattering sensitivity comparison and a later coupling model, not as "
                 "the free-space reference that fixes PathSolver settings.",
                 "A kernel target model is coupled into environment channels: the recommended hybrid formula, the "
                 "flow-diagram edge from the kernel response to the PathSolver environment, and the campaign arm "
                 "'environment PathSolver plus local kernel after interface calibration'. Under the new roles the "
                 "environment runs are PathSolver-only.",
                 "Pose-dependent static and rotating complex kernel arms are listed as campaign comparison arms next to "
                 "PathSolver arms. Under the new roles these belong in free-space cross-checks.",
                 "The review's two free-space mentions are the point-target start of the modelling order and a unit "
                 "convention; neither is a kernel-versus-PathSolver cross-check on relative quantities.",
                 "The review cites runners/jobs_0936_attrib.txt:3 (paper split, PathSolver only), superseded by the "
                 "AGENTS.md engine roles.",
             ],
             recorded_decision_or_rule=["Q_engine_roles_0915_evening", "Q_engine_roles_0915_user_wording",
                                        "Q_engine_roles_relative_only", "Q_path_provenance_asset"],
             superseded_decision_ids=["Q_pathsolver_only_decision"],
             evidence=dict(grep_counts=_gc(L, "review_md", ["kernel_ko", "PathSolver", "jobs_0936_line3", "free_space_ko",
                                                            "free_space_en", "free_space_hyphen_en"]) +
                           _gc(L, "campaign_json", ["kernel_en", "PathSolver"]),
                           alignment=_ac(L, ["draft_campaign_target_models", "draft_campaign_kernel_arms_n",
                                             "draft_campaign_kernel_only_arms_n",
                                             "draft_campaign_environment_kernel_coupled_arms_n",
                                             "draft_campaign_pathsolver_arms_n"]),
                           review_free_space_ko_hit_snippets=_snippets(texts, "review_md", "자유공간", width=16),
                           reading_of_snippets="Each review hit was read when this script was written: one is the "
                                               "point-target free-space start of the outdoor modelling order, the other a "
                                               "free-space unit convention for the kernel-to-channel coefficient. Re-read "
                                               "the snippets if the draft hash differs."),
             prose_assertions=[
                 G("review_md", "jobs_0936_line3", "ge", 1, "The review cites runners/jobs_0936_attrib.txt:3."),
                 G("review_md", "kernel_ko", "ge", 1, "The review names our kernel."),
                 G("review_md", "PathSolver", "ge", 1, "The review names PathSolver."),
                 A("Every D01 anchor (main-experiment sentence, hybrid formula, kernel arm list, next-steps row, "
                   "jobs_0936 citation, flow-diagram edge, PathSolver scope, modelling order) is found in the review.",
                   "anchors_missing", dict(conflict_id="D01_kernel_arms"), "eq", 0),
                 A("The campaign lists kernel comparison arms (kernel without PathSolver).", "alignment",
                   dict(id="draft_campaign_kernel_only_arms_n"), "ge", 1),
                 A("The campaign couples a kernel target model into an environment PathSolver arm.", "alignment",
                   dict(id="draft_campaign_environment_kernel_coupled_arms_n"), "ge", 1),
                 A("The campaign lists PathSolver arms.", "alignment", dict(id="draft_campaign_pathsolver_arms_n"), "ge", 1),
                 G("review_md", "free_space_ko", "eq", 2, "The review has two free-space mentions (the two snippets read)."),
                 G("review_md", "free_space_en", "eq", 0, "The review has no English 'free space'."),
                 G("review_md", "free_space_hyphen_en", "eq", 0, "The review has no English 'free-space'."),
                 A("The engine-roles quote is present in AGENTS.md.", "quote",
                   dict(id="Q_engine_roles_0915_evening", field="status"), "in", ok_status),
             ],
             resolution_needed="Restate the kernel as the free-space reference: move the pose-dependent and rotating kernel "
                               "arms into free-space cross-checks against PathSolver on relative quantities (with a "
                               "flat-ground bridge at matched geometry), remove the hybrid formula, the flow-diagram "
                               "coupling edge and the 'environment PathSolver plus local kernel' arm from the environment "
                               "campaign, run environment arms PathSolver-only, and cite the AGENTS.md engine roles instead "
                               "of runners/jobs_0936_attrib.txt:3."),
        dict(id="D02_carrier_bandwidth",
             draft_location=_anchor_rows(texts, "D02_carrier_bandwidth"),
             conflict="The draft moves to candidate carriers 2.45 and 5.8 GHz, a custom OFDM with a 15.625 MHz active "
                      "band, and 20 MHz standard profiles with 15 kHz spacing for NR mu=0. The existing PathSolver corpus "
                      "sits almost entirely (at least 90% of shard names) at the 3.5 GHz default carrier. The repo's "
                      "recorded comparison with TR 38.765 FR1 (4 or 4.9 GHz, 100 MHz, 30 kHz) records the alignment as "
                      "bandwidth (the 5G NR arm at 100 MHz) and subcarrier spacing (30 kHz); the carrier differs (repo "
                      "1.8 / 3.5 / 5.2 GHz, and the corpus default carrier is not a TR 38.765 FR1 carrier). No draft "
                      "carrier equals the corpus carrier or a TR 38.765 FR1 carrier, and no draft main-stage profile has "
                      "the TR 38.765 FR1 bandwidth and spacing. The draft states that a carrier change means recomputing; "
                      "the review never names TR 38.765 and does not state the loss of corpus reuse or of the recorded "
                      "bandwidth and spacing alignment.",
             recorded_decision_or_rule=["Q_std_fr1_carrier", "Q_std_fr1_bandwidth", "Q_std_fr1_scs",
                                        "Q_std_repo_carrier_differs", "Q_std_repo_nr_arm_matches_bandwidth",
                                        "Q_std_repo_nr_arm_matches_scs", "Q_sweep_default_carrier", "Q_sweep_carrier_tag_rule",
                                        "Q_x410_carrier_default"],
             evidence=dict(grep_counts=_gc(L, "review_md", ["GHz_2.45", "GHz_5.8", "GHz_3.5", "GHz_4.9", "MHz_100", "kHz_30",
                                                            "kHz_15", "TR_38.765"]),
                           corpus=_cc(L, ["shards_total", "shards_default_carrier", "outdoor_pathsolver_shards",
                                          "outdoor_pathsolver_default_carrier"]),
                           values=[dict(id="corpus_default_carrier_fraction", value=frac_default,
                                        source="computed shards_default_carrier / shards_total")],
                           alignment=_ac(L, ["corpus_default_carrier_hz", "corpus_carrier_in_tr38765_fr1",
                                             "tr38765_fr1_carriers_hz", "tr38765_fr1_bandwidth_hz",
                                             "tr38765_fr1_scs_hz", "draft_campaign_carriers_hz", "draft_campaign_active_bandwidth_hz",
                                             "draft_campaign_any_carrier_equals_corpus", "draft_campaign_any_carrier_in_tr38765_fr1",
                                             "draft_campaign_bandwidth_over_tr38765",
                                             "draft_waveform_main_profiles_matching_tr38765_bw_and_scs",
                                             "draft_waveform_nr_mu0_20mhz_15khz_profiles_n"])),
             prose_assertions=[
                 G("review_md", "GHz_2.45", "ge", 1, "The review names 2.45 GHz."),
                 G("review_md", "GHz_5.8", "ge", 1, "The review names 5.8 GHz."),
                 G("review_md", "kHz_15", "ge", 1, "The review names 15 kHz."),
                 A("Every D02 anchor is found in the review.", "anchors_missing",
                   dict(conflict_id="D02_carrier_bandwidth"), "eq", 0),
                 A("The campaign candidate carriers are 2.45 and 5.8 GHz.", "alignment",
                   dict(id="draft_campaign_carriers_hz"), "eq", [2.45e9, 5.8e9]),
                 A("The campaign active band is 15.625 MHz.", "alignment", dict(id="draft_campaign_active_bandwidth_hz"),
                   "eq", 15.625e6),
                 A("The waveform ledger has an NR mu=0 profile at 20 MHz and 15 kHz.", "alignment",
                   dict(id="draft_waveform_nr_mu0_20mhz_15khz_profiles_n"), "ge", 1),
                 A("The corpus default carrier is 3.5 GHz.", "alignment", dict(id="corpus_default_carrier_hz"), "eq", 3.5e9),
                 A("At least 90% of shard names sit at the default carrier.", "value",
                   dict(id="corpus_default_carrier_fraction"), "ge", 0.9, observed=frac_default),
                 A("The corpus default carrier is not a TR 38.765 FR1 carrier.", "alignment",
                   dict(id="corpus_carrier_in_tr38765_fr1"), "eq", False),
                 A("The repo table records the carrier as different.", "quote",
                   dict(id="Q_std_repo_carrier_differs", field="status"), "in", ok_status),
                 A("The repo table records the 5G NR bandwidth as matching.", "quote",
                   dict(id="Q_std_repo_nr_arm_matches_bandwidth", field="status"), "in", ok_status),
                 A("The repo table records the subcarrier spacing as matching.", "quote",
                   dict(id="Q_std_repo_nr_arm_matches_scs", field="status"), "in", ok_status),
                 A("No draft carrier equals the corpus carrier.", "alignment",
                   dict(id="draft_campaign_any_carrier_equals_corpus"), "eq", False),
                 A("No draft carrier equals a TR 38.765 FR1 carrier.", "alignment",
                   dict(id="draft_campaign_any_carrier_in_tr38765_fr1"), "eq", False),
                 A("No draft main-stage profile has the TR 38.765 FR1 bandwidth and spacing.", "alignment",
                   dict(id="draft_waveform_main_profiles_matching_tr38765_bw_and_scs"), "eq", 0),
                 G("review_md", "TR_38.765", "eq", 0, "The review never names TR 38.765."),
             ],
             resolution_needed="Decide the carrier after the six antennas' bands and the legal outdoor transmit band are "
                               "read; if it leaves 3.5 GHz, say that the corpus must be recomputed; if the standard profiles "
                               "leave 100 MHz and 30 kHz, say that the recorded TR 38.765 bandwidth and spacing alignment is "
                               "given up."),
        dict(id="D03_channel_map",
             draft_location=_anchor_rows(texts, "D03_channel_map"),
             conflict="The recorded X410 map uses RX0 as a reference channel and RX1-3 as a lambda/2 surveillance array. "
                      "The review and the campaign ledger allocate 1 TX, 3 sensing RX, 1 separately placed communication "
                      "RX and 1 spare antenna, which uses all 4 RX channels of the recorded X410 model and leaves none for a "
                      "reference channel; they use the transmitted symbols as a digital self-reference, name no reference "
                      "channel and never name src/experiment_x410.py, so they do not say that the recorded map is replaced. "
                      "The companion source memo's X410-only table still maps RX0 to a reference/communication antenna and "
                      "RX1-3 to surveillance, so the drafts also differ from each other; the memo notes that "
                      "half-wavelength spacing may be physically impossible with directional antennas.",
             recorded_decision_or_rule=["Q_x410_rx0_reference", "Q_x410_rx123_half_wavelength_ula",
                                        "Q_x410_detection_one_tracking_three"],
             evidence=dict(grep_counts=_gc(L, "review_md", ["RX0", "reference_channel_ko", "lambda_half", "experiment_x410"]) +
                           _gc(L, "campaign_json", ["RX0", "experiment_x410"]) +
                           _gc(L, "sources_memo", ["RX0", "half_wavelength_ko"]),
                           alignment=_ac(L, ["x410_record_n_rx", "x410_record_n_reference", "x410_record_n_surveillance",
                                             "x410_record_half_wavelength_cm", "x410_record_aoa_resolution_deg",
                                             "draft_campaign_x410_tx_used", "draft_campaign_x410_sensing_rx_used",
                                             "draft_campaign_x410_communication_rx_used", "draft_campaign_spare_antennas",
                                             "draft_campaign_reference_rx_used", "draft_campaign_x410_rx_allocated",
                                             "draft_campaign_x410_rx_unallocated"])),
             prose_assertions=[
                 A("Every D03 anchor is found.", "anchors_missing", dict(conflict_id="D03_channel_map"), "eq", 0),
                 A("The campaign uses 1 TX.", "alignment", dict(id="draft_campaign_x410_tx_used"), "eq", 1),
                 A("The campaign uses 3 sensing RX.", "alignment", dict(id="draft_campaign_x410_sensing_rx_used"), "eq", 3),
                 A("The campaign uses 1 communication RX.", "alignment", dict(id="draft_campaign_x410_communication_rx_used"),
                   "eq", 1),
                 A("The campaign keeps 1 spare antenna.", "alignment", dict(id="draft_campaign_spare_antennas"), "eq", 1),
                 A("The campaign allocates no reference RX.", "alignment", dict(id="draft_campaign_reference_rx_used"), "eq", 0),
                 A("The recorded X410 model has 4 RX channels.", "alignment", dict(id="x410_record_n_rx"), "eq", 4),
                 A("The draft allocation leaves no RX channel for a reference.", "alignment",
                   dict(id="draft_campaign_x410_rx_unallocated"), "eq", 0),
                 G("review_md", "RX0", "eq", 0, "The review never names RX0."),
                 G("review_md", "reference_channel_ko", "eq", 0, "The review never names a reference channel."),
                 G("campaign_json", "RX0", "eq", 0, "The campaign ledger never names RX0."),
                 G("review_md", "experiment_x410", "eq", 0, "The review never names src/experiment_x410.py."),
                 G("campaign_json", "experiment_x410", "eq", 0, "The campaign ledger never names src/experiment_x410.py."),
                 G("sources_memo", "RX0", "ge", 1, "The source memo still names RX0."),
                 G("sources_memo", "half_wavelength_ko", "ge", 1, "The source memo discusses half-wavelength spacing."),
             ],
             resolution_needed="Record which map is current and why; update src/experiment_x410.py or mark it superseded."),
        dict(id="D04_tr38765_metrics_absent",
             draft_location=_anchor_rows(texts, "D04_tr38765_metrics"),
             conflict="The draft reports Pd at a frame false-alarm rate, detection delay, continuity and GOSPA. The repo's "
                      "recorded TR 38.765 definitions make P_md, P_fa Type 1 and P_fa Type 2 mandatory (with 90% accuracy "
                      "targets) and exclude resolution, latency and refresh rate as metrics; the review, the campaign "
                      "ledger, the waveform ledger and the source memo never name TR 38.765, Type 1, Type 2, P_md or "
                      "UMa-AV, and multi-target drops for Type 2 remain an open to-do.",
             recorded_decision_or_rule=["Q_std_pmd_definition", "Q_std_pfa_type1_definition", "Q_std_pfa_type2_definition",
                                        "Q_std_both_pfa_mandatory", "Q_std_not_metrics_a", "Q_std_not_metrics_b",
                                        "Q_std_type2_needs_multitarget", "Q_std_umaav_scenario"],
             evidence=dict(grep_counts=[g for fid in four
                                        for g in _gc(L, fid, ["TR_38.765", "Type_1", "Type_2", "P_md", "UMa-AV", "GOSPA"])],
                           standards_numbers=["perf_missed_detection", "perf_false_alarm_type1", "perf_false_alarm_type2",
                                              "perf_horizontal_accuracy_m_90pct", "perf_vertical_accuracy_m_90pct",
                                              "perf_velocity_accuracy_mps_90pct"]),
             prose_assertions=[
                 A("Every D04 anchor is found.", "anchors_missing", dict(conflict_id="D04_tr38765_metrics"), "eq", 0),
                 G("review_md", "GOSPA", "ge", 1, "The review names GOSPA."),
             ] + [G(fid, t, "eq", 0, f"{fid} never names {t}.")
                  for fid in four for t in ("TR_38.765", "Type_1", "Type_2", "P_md", "UMa-AV")] + [
                 A("The Type 2 multi-target to-do is present in the repo.", "quote",
                   dict(id="Q_std_type2_needs_multitarget", field="status"), "in", ok_status),
             ],
             resolution_needed="Report in TR 38.765 form next to the tracking metrics, and plan multi-target drops."),
        dict(id="D05_diffuse_switch_not_stated",
             draft_location=_anchor_rows(texts, "D05_diffuse_switch"),
             conflict="The draft's outdoor modelling order and PathSolver scope paragraphs do not state the diffuse "
                      "switch; the recorded rule keeps diffuse reflection on in every arm, and diffraction is reserved "
                      "for the new build. The Korean word that means both diffuse and spreading appears twice in the "
                      "review, and the recorded snippets show path and propagation spreading, not the switch; the review, "
                      "the campaign ledger, the waveform ledger and the source memo never name 'diffuse', F1 or R0D0E0F1.",
             recorded_decision_or_rule=["Q_diffuse_always_on", "Q_diffraction_new_build_only"],
             evidence=dict(grep_counts=[g for fid in four
                                        for g in _gc(L, fid, ["diffuse_en", "diffuse_ko", "F1_token", "R0D0E0F1"])],
                           review_diffuse_ko_hit_snippets=_snippets(texts, "review_md", "확산"),
                           reading_of_snippets="Each review hit was read when this script was written: path spreading "
                                               "and propagation spreading, not the diffuse-reflection switch. Re-read "
                                               "the snippets if the draft hash differs.",
                           corpus=_cc(L, ["outdoor_pathsolver_shards", "outdoor_pathsolver_diffuse_on",
                                          "outdoor_pathsolver_diffuse_off", "outdoor_pathsolver_diffraction_on"])),
             prose_assertions=[
                 A("Every D05 anchor is found.", "anchors_missing", dict(conflict_id="D05_diffuse_switch"), "eq", 0),
                 G("review_md", "diffuse_ko", "eq", 2, "The Korean diffuse/spreading word appears twice in the review "
                                                      "(the two snippets read)."),
             ] + [G(fid, t, "eq", 0, f"{fid} never names {t}.")
                  for fid in four for t in ("diffuse_en", "F1_token", "R0D0E0F1")],
             resolution_needed="State diffuse on (F1) for every arm and no diffraction lines in any campaign derived from the draft."),
        dict(id="D06_related_work_missing",
             draft_location=_anchor_rows(texts, "D06_related_work"),
             conflict="The review cites 2412.20788, 2509.25732, 2504.05168 and 2608.05826, but not the companion "
                      "2608.10784, the 5G detection/tracking hardware works 2605.23561 and 2603.14351, or the repo's own "
                      "recorded precedents (Taylor & Poullin 2025 as the required method precedent, the Maksymiuk 5G "
                      "passive-radar line, LIPASE, TR 38.765).",
             recorded_decision_or_rule=["Q_taylor_poullin_must_cite", "Q_taylor_poullin_precedent", "Q_maksymiuk_2022",
                                        "Q_maksymiuk_2025", "Q_lipase_12_antennas", "Q_acquire_2505_24763"],
             evidence=dict(grep_counts=_gc(L, "review_md", rel) + _gc(L, "campaign_json", rel)),
             prose_assertions=[
                 A("Every D06 anchor is found.", "anchors_missing", dict(conflict_id="D06_related_work"), "eq", 0),
             ] + [G("review_md", t, "ge", 1, f"The review cites {t}.")
                  for t in ("arXiv_2412.20788", "arXiv_2509.25732", "arXiv_2504.05168", "arXiv_2608.05826")]
               + [G("review_md", t, "eq", 0, f"The review does not cite {t}.")
                  for t in ("arXiv_2608.10784", "arXiv_2605.23561", "arXiv_2603.14351", "Taylor", "Poullin", "Maksymiuk",
                            "LIPASE", "TR_38.765")],
             resolution_needed="Add the missing works to the related-work paragraph (see prior_work rows)."),
        dict(id="D07_queue_snapshot_dated",
             draft_location=_anchor_rows(texts, "D07_queue_snapshot"),
             conflict="The review records a dated observation that none of 30 directional-antenna queue lines had started. "
                      "The queue ledger it links counts those 30 orders (0 launch records) from runners/jobs_0938_antenna.txt, "
                      "which has 30 job lines and is now headed as superseded by runners/jobs_0940_antenna.txt; the revised "
                      "queue has 34 job lines. The 30 and the 34 therefore count different files, and the queue ledger "
                      "never names the 0940 file. This is a snapshot, not a decision; shards with an antenna-pattern tag "
                      "now exist on disk.",
             recorded_decision_or_rule=["Q_0940_outdoor_aimed_line", "Q_0940_supersedes_0938", "Q_0938_superseded",
                                        "Q_0938_needs_8192_poses"],
             evidence=dict(corpus=_cc(L, ["outdoor_directional_antenna_shards"]),
                           grep_counts=_gc(L, "queue_json", ["jobs_0938", "jobs_0940"]) +
                           _gc(L, "review_md", ["jobs_0938", "jobs_0940"]),
                           values=[dict(id="jobs_0940_engine_lines", value=n_job_lines,
                                        source="runners/jobs_0940_antenna.txt lines starting with --engine"),
                                   dict(id="jobs_0938_engine_lines", value=n_job_lines_0938,
                                        source="runners/jobs_0938_antenna.txt lines starting with --engine"),
                                   dict(id="review_queue_lines_stated", value=int(review_30.group(1)) if review_30 else None,
                                        source="number parsed from the D07 anchor sentence in the review"),
                                   dict(id="review_queue_started_stated", value=int(review_30.group(2)) if review_30 else None,
                                        source="second number parsed from the D07 anchor sentence in the review"),
                                   dict(id="queue_json_0938_job_file", value=(q0938 or {}).get("job_file"),
                                        source="work/isac_queue_latest_0915.json:queues.0938.job_file"),
                                   dict(id="queue_json_0938_orders_n", value=len((q0938 or {}).get("orders", [])) if q0938 else None,
                                        source="len(work/isac_queue_latest_0915.json:queues.0938.orders)"),
                                   dict(id="queue_json_0938_launch_records", value=(q0938 or {}).get("launch_records"),
                                        source="work/isac_queue_latest_0915.json:queues.0938.launch_records")]),
             prose_assertions=[
                 A("Every D07 anchor is found.", "anchors_missing", dict(conflict_id="D07_queue_snapshot"), "eq", 0),
                 A("The review states 30 queue lines.", "value", dict(id="review_queue_lines_stated"), "eq", 30,
                   observed=int(review_30.group(1)) if review_30 else None),
                 A("The review states 0 started lines.", "value", dict(id="review_queue_started_stated"), "eq", 0,
                   observed=int(review_30.group(2)) if review_30 else None),
                 A("The queue ledger's directional queue file is runners/jobs_0938_antenna.txt.", "value",
                   dict(id="queue_json_0938_job_file"), "eq", "runners/jobs_0938_antenna.txt",
                   observed=(q0938 or {}).get("job_file")),
                 A("The queue ledger counts 30 orders for it.", "value", dict(id="queue_json_0938_orders_n"), "eq", 30,
                   observed=len((q0938 or {}).get("orders", [])) if q0938 else None),
                 A("The queue ledger has 0 launch records for it.", "value", dict(id="queue_json_0938_launch_records"),
                   "eq", 0, observed=(q0938 or {}).get("launch_records")),
                 A("runners/jobs_0938_antenna.txt has 30 job lines.", "value", dict(id="jobs_0938_engine_lines"), "eq", 30,
                   observed=n_job_lines_0938),
                 A("runners/jobs_0940_antenna.txt has 34 job lines.", "value", dict(id="jobs_0940_engine_lines"), "eq", 34,
                   observed=n_job_lines),
                 A("The 0938 file is headed as superseded.", "quote", dict(id="Q_0938_superseded", field="status"),
                   "in", ok_status),
                 A("The 0940 file is headed as superseding 0938.", "quote", dict(id="Q_0940_supersedes_0938", field="status"),
                   "in", ok_status),
                 A("The 0940 first-line quote is unique in its file.", "quote",
                   dict(id="Q_0940_outdoor_aimed_line", field="n_matches"), "eq", 1),
                 G("queue_json", "jobs_0940", "eq", 0, "The queue ledger never names the 0940 file."),
                 A("Shards with an antenna-pattern tag exist.", "corpus", dict(id="outdoor_directional_antenna_shards"),
                   "gt", 0),
             ],
             resolution_needed="Refresh the queue paragraph from runners/jobs_0940_antenna.txt and the current shard list "
                               "before reuse."),
        dict(id="D08_rotor_relinking_followup_conditional",
             draft_location=_anchor_rows(texts, "D08_rotor_relinking_followup"),
             conflict="The memo's follow-up (rotor features to reduce identity switches after crossings) assumes rotor "
                      "lines are observable outdoors. Whether they stand above the ground-raised floor depends on antenna "
                      "and mounting; that evidence is kept in the corpus ledger and is not restated here.",
             recorded_decision_or_rule=["Q_0938_needs_8192_poses", "Q_prf_gate_rule", "Q_prf_gate_2_of_45"],
             evidence=dict(other_ledger="outputs/isac_plan_corpus_0915.json (separate script; numbers not copied)"),
             prose_assertions=[
                 A("The D08 anchor is found.", "anchors_missing", dict(conflict_id="D08_rotor_relinking_followup"), "eq", 0),
             ],
             resolution_needed="Keep the follow-up conditional on the corpus result and on a waveform whose sampling "
                               "passes the PRF gate."),
    ]
    L.data["draft_conflicts"] = rows
    all_pa = [(r["id"], a) for r in rows for a in r["prose_assertions"]]
    failed = [dict(conflict_id=cid, claim=a["claim"], expected=a["expected"], observed=a["observed"])
              for cid, a in all_pa if not a["holds"]]
    L.data["_meta"]["prose_assertions_summary"] = dict(n_assertions=len(all_pa), n_failed=len(failed), failed=failed)
    return len(failed)


def section_prior_work(L: Ledger):
    s = {x["id"]: x for x in SOURCES}

    def web(sid):
        return dict(url=s[sid]["url"], url_html=s[sid]["url_html"], retrieved=RETRIEVED, source_id=sid,
                    citation=f'{s[sid]["authors"]}, "{s[sid]["title"]}", {s[sid]["document_id"]}, {s[sid]["date"]}')

    rows = [
        dict(id="PW_gurung_2608_05826", **web("SRC_2608_05826"), verification="re-opened (abstract and HTML)",
             what_they_did="End-to-end O-RAN testbed (OpenAirInterface, FlexRIC, Sionna RT) using the NR uplink SRS as a "
                           "passive radar waveform; outdoor dry-ground floor; CFAR at P_FA 1e-4; UAV detection and 3-D EKF "
                           "tracking; reports detection coverage (the abstract: preserved under a concurrent 10 Mbps uplink "
                           "communications load), RMSE, track continuity and NIS/NEES consistency.",
             what_is_not_modelled="UAV rendered as one point scatterer (all UAV rays summed into one echo tap); isotropic "
                                  "elements; fuselage multi-bounce and rotor micro-Doppler not modelled; static ground return "
                                  "removed by clutter-subspace deflation.",
             relation_to_this_plan="Sionna RT + outdoor ground + CFAR/EKF tracking of a UAV is already published. This plan "
                                   "must differ through rotor-resolved, pose-varying paths (including ground-involved paths "
                                   "that change with rotor pose) and must cite it as the closest simulation precedent."),
        dict(id="PW_gurung_2608_10784", **web("SRC_2608_10784"), verification="re-opened (HTML)",
             what_they_did="Multi-UAV tracking on the same O-RAN/Sionna testbed at fc 3319.68 MHz, 38.16 MHz occupied, "
                           "2x4 half-wavelength UPA.",
             what_is_not_modelled="Isotropic elements; each UAV is one point-like scattering centre; explicitly excludes "
                                  "extended-body scattering, rotor micro-Doppler, inter-target occlusion and shadowing, and "
                                  "polarization.",
             relation_to_this_plan="Companion that the draft does not cite. Its stated exclusions are exactly the axes this "
                                   "plan can add with rotor-resolved PathSolver channels."),
        dict(id="PW_sun_2412_20788", **web("SRC_2412_20788"), verification="re-opened (abstract)",
             what_they_did="Experimental passive UAV tracking with two digital antenna arrays and LTE downlink illumination; "
                           "a multi-target tracking framework adopted to address missed detections and false alarms of "
                           "passive sensing (abstract quote in sources); meter-level accuracy.",
             what_is_not_modelled="Measurement study; the abstract describes no site-specific channel model and no "
                                  "rotor-resolved target model.",
             relation_to_this_plan="Measured cellular passive tracking exists, so tracking with communication signals is not "
                                   "new by itself. Identity with the repo's LIPASE record (Sun et al., IEEE OJ-COMS 2025) "
                                   "could not be verified from this page."),
        dict(id="PW_ji_2509_25732", **web("SRC_2509_25732"), verification="re-opened (abstract)",
             what_they_did="Doppler-based multistatic drone tracking with three passive receivers using LTE base stations; "
                           "drone and receivers about 200 m from the base stations; 90% errors below 90 cm.",
             what_is_not_modelled="Measurement study; the abstract describes no ray-traced environment or rotor model.",
             relation_to_this_plan="Measured multi-receiver tracking reference; relevant if the plan adds receivers."),
        dict(id="PW_costa_2504_05168", **web("SRC_2504_05168"), verification="re-opened (abstract and HTML)",
             what_they_did="Thin-wire multi-propeller micro-Doppler model with the drone's static parts for bistatic "
                           "OFDM-like sensing; in the authors' words, measurements were performed to collect ground truth "
                           "data for verification of the proposed model; their measurement processing uses time-domain "
                           "gating and back-to-back calibration.",
             what_is_not_modelled="Per the HTML reading: no ground or environment multipath and no detection, CFAR or tracking "
                                  "(signature modelling for classification data).",
             relation_to_this_plan="Rotor-signature model precedent without environment; the plan's question is what happens "
                                   "to such signatures once site-specific ground and building paths are present."),
        dict(id="PW_saur_2605_23561", **web("SRC_2605_23561"), verification="re-opened (abstract)",
             what_they_did="Detection of a small UAV with unmodified commercial 5G hardware as monostatic OFDM radar; "
                           "sub-meter accuracy beyond 500 m in a clutter-rich environment (measured).",
             what_is_not_modelled="Only the abstract was checked; it describes a hardware measurement, not a ray-traced "
                                  "rotor-resolved model.",
             relation_to_this_plan="Measured reference in the same monostatic family as Rel-20 and a co-located X410 link; "
                                   "missing from the draft."),
        dict(id="PW_wang_2603_14351", **web("SRC_2603_14351"), verification="re-opened (abstract)",
             what_they_did="5G-A base-station-compatible ISAC protocol, waveform and prototype; tracks weak, slow targets "
                           "beyond 1 km with 1.2% downlink rate loss relative to a commercial 5G-A base station.",
             what_is_not_modelled="Only the abstract was checked; no site-specific ray-traced target model is described.",
             relation_to_this_plan="Precedent for reporting sensing together with communication cost (rate loss); relevant "
                                   "to the joint comm-and-sensing benchmark; missing from the draft."),
        dict(id="PW_taylor_poullin_taes2025", url=None, url_html=None, retrieved=None, source_id=None,
             citation="A. Taylor and D. Poullin, IEEE Trans. Aerosp. Electron. Syst. 61(4), Aug. 2025, pp. 8804- "
                      "(repo record; DOI 10.1109/TAES.2025.3545000)",
             verification="repo record only (docs/PRIOR_READING_LOG.md, docs/REFERENCE_LIBRARY.md); not re-opened here",
             repo_quote_ids=["Q_taylor_poullin_authors", "Q_taylor_poullin_precedent", "Q_taylor_poullin_must_cite",
                             "Q_taylor_poullin_doi"],
             what_they_did="Per the repo record: a controlled comparison of signal-resource subsets inside one LTE downlink, "
                           "one drone target, one CFAR detector, at a calibrated false-alarm rate.",
             what_is_not_modelled="Per the repo record: different illuminator types (Wi-Fi/LTE/NR) are not compared; one geometry.",
             relation_to_this_plan="Required method precedent for any waveform/illuminator benchmark; the plan must not claim "
                                   "a first controlled comparison."),
        dict(id="PW_mdrt_icct2025", url=None, url_html=None, retrieved=None, source_id=None,
             citation="C. Li, S. Mu, J. Jiang, L. Feng, Y. Gao, and S. Xu, \"Micro-Doppler Signature Simulation of "
                      "Multirotor UAVs Using Ray Tracing\", IEEE 25th Int. Conf. Commun. Technol. (ICCT) 2025, pp. 359-364, "
                      "DOI 10.1109/ICCT67417.2025.11374154 (repo record)",
             verification="repo record only; the paper is not open access and was not re-opened; could not verify whether "
                          "any environment or ground is included",
             repo_quote_ids=["Q_mdrt_citation_authors_title", "Q_mdrt_citation_venue_doi", "Q_mdrt_citation_library",
                             "Q_mdrt_record", "Q_mdrt_single_propeller", "Q_mdrt_no_amplitude", "Q_mdrt_no_amplitude_claim"],
             what_they_did="Per the repo record: Sionna RT with stock EM settings and a modified (conical) ray launcher plus "
                           "Blender blade meshes to produce rotor micro-Doppler spectrograms, matched to an analytic Doppler "
                           "frequency and period; target is one wooden propeller.",
             what_is_not_modelled="Per the repo record: scattering amplitude is not reported (Q_mdrt_no_amplitude, "
                                  "Q_mdrt_no_amplitude_claim). Environment/ground: could not verify.",
             relation_to_this_plan="Rotor micro-Doppler inside a Sionna-class ray tracer exists for a propeller; the plan's "
                                   "difference must rest on a full airframe in a site-specific outdoor scene with detection "
                                   "and tracking, not on rotor micro-Doppler in Sionna alone."),
    ]
    L.data["prior_work"] = rows


def section_candidates(L: Ledger):
    rows = [
        dict(id="C1_ground_hides_rotor_lines",
             statement="A free-space cross-model consistency protocol between PathSolver and the PO kernel on relative "
                       "quantities; a flat-ground bridge between the kernel image-method arm and the PathSolver ground scene "
                       "at matched geometry; then PathSolver-only site-specific scenes with directional antennas and path "
                       "provenance.",
             stages=[
                 dict(stage=1, name="free_space_consistency_protocol",
                      text="PathSolver and the PO kernel in free space, compared on relative quantities only (for example "
                           "level differences between poses, rotor-line contrast, spectral shape), to write down under which "
                           "PathSolver settings the output is consistent with the kernel.",
                      repo_quote_ids=["Q_engine_roles_0915_evening", "Q_engine_roles_0915_user_wording",
                                      "Q_engine_roles_relative_only"]),
                 dict(stage=2, name="flat_ground_bridge",
                      text="The kernel's image-method ground arm and the PathSolver ground scene at matched geometry, again "
                           "on relative quantities, so that the step from free space to one ground plane is checked before "
                           "any site-specific scene.",
                      other_ledger="outputs/isac_plan_kernel_match_0915.json (geometry_match, pairs, "
                                   "within_engine_ground_effect; separate script; numbers not copied)"),
                 dict(stage=3, name="pathsolver_only_site_scenes",
                      text="PathSolver-only site-specific outdoor scenes with directional antennas and per-path provenance. "
                           "The scene question: when do ground-involved paths that change with rotor pose hide the rotor's "
                           "spectral lines, and which antenna pattern, aim, mounting height and assumed front-to-back ratio "
                           "let those lines stand out again?",
                      repo_quote_ids=["Q_path_provenance_asset", "Q_0940_outdoor_aimed_line", "Q_0938_needs_8192_poses",
                                      "Q_diffuse_always_on"]),
             ],
             question="Under which PathSolver settings is the output consistent with the PO kernel in free space and over one "
                      "flat ground plane (relative quantities only), and, in PathSolver-only site-specific outdoor scenes "
                      "with directional antennas and path provenance, when do ground-involved paths that change with rotor "
                      "pose hide the rotor's spectral lines (the lines at multiples of the blade-passing rate), and which "
                      "antenna pattern, aim, mounting height and assumed front-to-back ratio let those lines stand out again "
                      "above the level that the ground-involved paths add between them?",
             differs_from=[
                 dict(prior_work_id="PW_gurung_2608_05826", difference="point target summed into a single echo tap, isotropic elements, no rotor, "
                                                                        "static ground removed by subspace deflation"),
                 dict(prior_work_id="PW_gurung_2608_10784", difference="excludes rotor micro-Doppler, extended body, polarization"),
                 dict(prior_work_id="PW_costa_2504_05168", difference="rotor model without ground or environment paths"),
                 dict(prior_work_id="PW_mdrt_icct2025", difference="single propeller, Doppler frequency/period only; no "
                                                                    "scattering amplitude in the repo record; environment not known"),
                 dict(repo_quote_id="Q_std_non_rotating_point", difference="3GPP small UAV is a non-rotating isotropic point"),
             ],
             repo_support=dict(repo_quote_ids=["Q_engine_roles_0915_evening", "Q_engine_roles_relative_only",
                                               "Q_path_provenance_asset", "Q_0940_outdoor_aimed_line",
                                               "Q_0938_needs_8192_poses", "Q_diffuse_always_on", "Q_matrice4e_on_hand"],
                               superseded_repo_quote_ids=["Q_pathsolver_only_decision"],
                               corpus_count_ids=["outdoor_pathsolver_shards", "outdoor_ground_rt210_depth2_8192",
                                                 "outdoor_directional_antenna_shards", "outdoor_pathsolver_diffuse_on"],
                               other_ledger="outputs/isac_plan_corpus_0915.json holds the spectral-line contrast numbers; "
                                            "outputs/isac_plan_kernel_match_0915.json holds the kernel/PathSolver pairing"),
             new_compute_needed=[
                 "a written free-space consistency protocol: which relative quantities, which PathSolver settings, which "
                 "tolerance, fixed before the comparison is read",
                 "the flat-ground bridge cells at matched geometry (kernel image-method arm and PathSolver ground scene)",
                 "finish the aimed-antenna production cells (8192 poses, depth 2, build 2.1.0) and their isotropic partners",
                 "mounting-height and assumed front-to-back-ratio sweeps, with the owned antennas' patterns once they are read",
                 "per-path provenance with a coherent allocation rule fixed before any per-part or per-path share is quoted",
                 "a ray-count ladder to separate physical pose-varying ground paths from pose-to-pose changes in the ray set",
             ],
             guardrails=[
                 "consistency between PathSolver and the kernel is not validation: both are approximations",
                 "no absolute-level comparison between the engines; relative quantities only; do not call either engine "
                 "right or wrong",
                 "X410 measurements (with the Matrice 4E on hand) are the reality check; no comparison against RF "
                 "measurements until X410 captures exist",
                 "environment runs are PathSolver-only; the kernel stays in the free-space and flat-ground cross-checks",
                 "describe results as PathSolver behaviour, not as how real drones behave",
                 "diffuse on (F1) for every arm; no diffraction lines",
                 "keep the _rt210 build tag and production settings (8192 poses, depth 2)",
                 "levels are PathSolver level in dB (arbitrary reference), never scattering areas",
                 "say that aimed results at el -60 depend on the assumed attenuation cap",
             ]),
        dict(id="C2_clustered_misses_to_track_loss",
             question="How do misses that cluster in time because of rotor pose and ground paths turn into track loss "
                      "outdoors? One CFAR-then-EKF chain is fed (i) a single coherent tap reduced from the same PathSolver "
                      "paths and (ii) the full per-path rotor-resolved channel, and the difference is reported.",
             differs_from=[
                 dict(prior_work_id="PW_gurung_2608_05826", difference="tracks a point target summed into a single echo tap"),
                 dict(prior_work_id="PW_gurung_2608_10784", difference="one scattering centre per UAV"),
                 dict(prior_work_id="PW_sun_2412_20788", difference="measured tracking without a per-path channel model"),
                 dict(prior_work_id="PW_ji_2509_25732", difference="measured Doppler tracking without a per-path channel model"),
             ],
             repo_support=dict(repo_quote_ids=["Q_std_pmd_definition", "Q_std_pfa_type1_definition", "Q_std_pfa_type2_definition",
                                               "Q_std_both_pfa_mandatory", "Q_empirical_pfa_curve", "Q_path_provenance_asset"],
                               standards_number_ids=["perf_missed_detection", "perf_false_alarm_type1", "perf_false_alarm_type2",
                                                     "perf_horizontal_accuracy_m_90pct"],
                               corpus_count_ids=["shards_default_carrier", "arm_grammar_motion_fields"]),
             new_compute_needed=[
                 "a wideband or waveform-level channel (each corpus shard is one carrier)",
                 "moving trajectories (the arm grammar has no target-motion field; corpus cells are hover cases)",
                 "multi-target drops so that P_fa Type 2 is defined",
                 "false-alarm calibration on target-free outdoor frames",
             ],
             guardrails=[
                 "report P_md, P_fa Type 1 and Type 2 and 90% accuracy in TR 38.765 form next to continuity, fragmentation "
                 "and re-acquisition; do not report resolution or latency as performance metrics",
                 "state the association rule",
                 "the single-tap control must be reduced from the same paths, so the comparison isolates the target model",
                 "label all results as simulation",
             ]),
        dict(id="C3_comm_constrained_waveform_benchmark",
             question="On one co-located X410 link, what do Wi-Fi, LTE and NR frames give for detection at a calibrated "
                      "frame false-alarm rate when decoded packet error and goodput are reported at the same time, how does "
                      "measured transmit-to-receive leakage compare with the 65/80 dB isolation assumed in TR 38.765, and "
                      "how much does reference access (full known data, pilots only, re-modulated decoded data) change it?",
             differs_from=[
                 dict(prior_work_id="PW_taylor_poullin_taes2025", difference="resource subsets inside one LTE signal, no "
                                                                             "communication outcome"),
                 dict(prior_work_id="PW_wang_2603_14351", difference="one 5G-A prototype with a rate-loss figure, not a "
                                                                     "cross-standard comparison"),
                 dict(prior_work_id="PW_saur_2605_23561", difference="detection only with commercial 5G hardware"),
             ],
             repo_support=dict(repo_quote_ids=["Q_three_standard_novelty", "Q_occupancy_axis_flat", "Q_std_isolation",
                                               "Q_taylor_poullin_must_cite", "Q_not_fixed_to_passive_bistatic"],
                               draft_files=["outputs/isac_waveform_benchmark_design_0915.json (uncommitted draft)"]),
             new_compute_needed=[
                 "standard bit chains and decoders for the chosen profiles, with per-frame references",
                 "leakage and isolation measurement plan on the X410",
                 "a carrier and bandwidth decision (see draft_conflicts D02)",
             ],
             guardrails=[
                 "cite Taylor & Poullin as the method precedent; do not claim a first controlled multi-standard comparison",
                 "the occupancy axis was nearly flat on SNR50 before, so the headline must be joint communication and "
                 "detection/tracking outcomes, not occupancy",
                 "state carrier, bandwidth and reference-access tier for every row",
                 "whether this belongs in the same paper is an open question for the user",
             ]),
    ]
    L.data["candidate_contributions"] = rows


def section_stale(L: Ledger):
    q = {r["id"]: r for r in L.data["repo_quotes"]}

    def row(qid, why, proposed, evidence, superseded_by=None):
        r = q[qid]
        return dict(id=qid, path=r["path"], line=r["line"], quote=r["quote"], quote_id=qid, quote_status=r["status"],
                    why_stale=why, proposed_update=proposed, evidence=evidence, superseded_by=superseded_by)

    rows = [
        row("Q_pathsolver_only_decision",
            "Superseded. The AGENTS.md engine-roles bullet (user decision 2026-09-15, evening KST) names this line and "
            "replaces it: the kernel does not move to another paper; it is the free-space reference that establishes under "
            "which settings PathSolver output is reasonable, and environments are then simulated with PathSolver alone. "
            "The 'PathSolver only' part survives for environment runs; the paper-split part does not.",
            "Add a dated superseded note on runners/jobs_0936_attrib.txt pointing to the AGENTS.md engine-roles bullet; "
            "keep the line as history.",
            dict(repo_quote_ids=["Q_engine_roles_0915_evening", "Q_engine_roles_0915_user_wording",
                                 "Q_engine_roles_relative_only"], draft_file_ids=["review_md"],
                 draft_conflict_ids=["D01_kernel_arms"]),
            superseded_by="Q_engine_roles_0915_evening"),
        row("Q_x410_detection_not_tracking",
            "The plan now covers detection and tracking; the 2026-07-14 direction still reads detection only. No committed "
            "repo record states the change yet (the review that adds tracking is uncommitted).",
            "Add a dated 2026-09-15 note that tracking joins detection and point to the new plan; keep the old line as history.",
            dict(repo_quote_ids=["Q_x410_direction_date"], draft_file_ids=["review_md"])),
        row("Q_x410_geometry_tx",
            "The scenario coordinates are the old indoor layout (horn on one wall, array on the opposite wall), while "
            "production queues now use outdoor scenes.",
            "Replace the default geometry with an outdoor scene before X410Scenario is reused.",
            dict(repo_quote_ids=["Q_x410_geometry_ref", "Q_x410_geometry_surv", "Q_x410_geometry_target",
                                 "Q_0940_outdoor_aimed_line"], corpus_count_ids=["outdoor01_family_shards"])),
        row("Q_x410_rx123_half_wavelength_ula",
            "The recorded map needs lambda/2 spacing (computed in alignment_checks) with RX0 as reference; the draft uses a "
            "different allocation and six directional antennas whose sizes are not yet read.",
            "Record the chosen channel map and the antenna sizes; if lambda/2 is not possible, state the angle method that replaces it.",
            dict(repo_quote_ids=["Q_x410_rx0_reference", "Q_0940_reality_check"],
                 alignment_ids=["x410_record_half_wavelength_cm", "x410_record_aoa_resolution_deg"])),
        row("Q_std_passive_contribution_surface",
            "The recorded user framing does not fix the task to passive bistatic, the engine roles now place the kernel as "
            "the free-space reference with PathSolver-only environments, and the co-located X410 plan sits in the Rel-20 "
            "monostatic family.",
            "Retire the sentence as positioning; keep passive bistatic only as a benchmark condition.",
            dict(repo_quote_ids=["Q_not_fixed_to_passive_bistatic", "Q_engine_roles_0915_evening", "Q_std_bistatic_zero"])),
        row("Q_std_passive_no_self_interference",
            "A co-located X410 transmitter and receiver inherits the self-interference and isolation constraint that this "
            "line calls absent for passive bistatic.",
            "Qualify it: true for a separate passive receiver only; the co-located plan must budget isolation (65/80 dB in TR 38.765).",
            dict(repo_quote_ids=["Q_std_isolation"])),
        row("Q_std_detection_focus_link",
            "Links the standard's detection bottleneck to the recorded detection-and-classification focus (the quoted "
            "line names both); the 2026-09-15 plan adds tracking to that focus.",
            "Annotate that tracking joins detection and classification since 2026-09-15.",
            dict(repo_quote_ids=["Q_x410_detection_not_tracking"])),
        row("Q_pw01_novelty_combination",
            "The combination names in-house SBR+PO drone scattering as part of the contribution (under the engine roles the "
            "kernel is the free-space reference, not an environment arm) and passive bistatic (not the headline).",
            "Mark the sentence as superseded for the ISAC paper.",
            dict(repo_quote_ids=["Q_engine_roles_0915_evening", "Q_not_fixed_to_passive_bistatic", "Q_occupancy_axis_flat"])),
        row("Q_three_standard_novelty",
            "The later reading log narrows this: a published controlled comparison at calibrated false-alarm rate exists "
            "inside one LTE signal and must be cited.",
            "Narrow to 'different illuminator types' and cite Taylor & Poullin 2025 next to it.",
            dict(repo_quote_ids=["Q_taylor_poullin_precedent", "Q_taylor_poullin_must_cite", "Q_occupancy_axis_flat"])),
        row("Q_sionna_detection_range_zero",
            "Scoped to the corpus read then; arXiv:2608.05826 (Aug 2026) reports UAV detection and tracking with Sionna RT.",
            "Add a dated note naming arXiv:2608.05826 and arXiv:2608.10784 so the zero-precedent line is not reused.",
            dict(prior_work_ids=["PW_gurung_2608_05826", "PW_gurung_2608_10784"])),
    ]
    L.data["stale_repo_records"] = rows


def section_open_questions(L: Ledger):
    L.data["open_questions"] = [
        dict(id="OQ_antenna_bands", question="Which bands, gains, front-to-back ratios, polarisations and sizes do the six "
                                             "owned directional antennas have?",
             why="Decides the carrier (D02), whether any array spacing is possible (D03) and replaces the assumed attenuation cap."),
        dict(id="OQ_legal_band", question="Which band may legally be used for outdoor transmission with the X410 at the site?",
             why="Carrier decision (D02)."),
        dict(id="OQ_floor_cause", question="Do the pose-varying floor paths come from physical ground paths or from pose-to-pose "
                                           "changes in PathSolver's ray set?", why="Scope of C1; needs provenance and a ray-count ladder."),
        dict(id="OQ_deflation", question="Would clutter-subspace deflation as in arXiv:2608.05826 remove the pose-varying ground "
                                         "part or only its static part?", why="Sharpens the difference from the closest precedent."),
        dict(id="OQ_lipase_identity", question="Is arXiv:2412.20788 the same work as the repo's LIPASE record (IEEE OJ-COMS 2025)?",
             why="Citation hygiene (PW_sun_2412_20788)."),
        dict(id="OQ_mdrt_environment", question="Does md-rt (ICCT 2025) include any environment or ground?",
             why="Could not verify from repo records (PW_mdrt_icct2025)."),
        dict(id="OQ_same_paper", question="Should the Wi-Fi/LTE/NR benchmark (C3) be in the same paper as detection and tracking?",
             why="Only the user can decide."),
        dict(id="OQ_legacy_radio", question="Is the legacy radio a USRP-2921, and does its band exclude the chosen carrier?",
             why="Whether it can join any experiment."),
    ]


# -------------------------------------------------------------------------------------------- main


def main() -> int:
    here = Path(__file__).resolve()
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", default=str(here.parents[1]), help="repo root (default: parent of this script's directory)")
    ap.add_argument("--out", default=None, help="ledger path (default: ROOT/outputs/isac_plan_positioning_0915.json)")
    ap.add_argument("--core", type=int, default=None, help="CPU core to pin to (default: lowest core in current affinity)")
    a = ap.parse_args()
    root = Path(a.root).resolve()
    out = Path(a.out).resolve() if a.out else root / "outputs" / f"{NAME}.json"
    t0 = time.time()

    L = Ledger(root, out)
    L.data["_meta"] = dict(
        generator=GENERATOR, command=COMMAND, argv=sys.argv[1:], started_utc=utc_now(), finished_utc=None,
        wall_time_s=None, git_head=git_head(root), cpu_core=CORE,
        package_versions=dict(python=platform.python_version(), third_party=[]),
        scope="Simulation / code / bookkeeping checks with no comparison against RF measurements. Literature rows state "
              "what the cited documents report; nothing here judges which simulation engine is right.",
        definitions=dict(
            repo_quotes="Each quote is searched in the stated line of the file as it is on disk at run time. status ok = found "
                        "on that line; moved = found exactly once elsewhere (line is the new line); ambiguous/not_found = "
                        "counted as failures and the script exits 1. sha256 is of the whole file as read.",
            repo_quotes_n_lines="Number of consecutive lines the quote spans; for n_lines > 1 each line is stripped and the "
                                "lines are joined with one space before the substring test.",
            repo_quotes_line_end="Last line of the span where the quote was found (line + n_lines - 1), or null.",
            repo_quotes_n_matches="Number of start lines in the file at which the quote is found (1 = unique in the file).",
            sources="External literature statements. Each quote has locator and text; quotes that also carry url and "
                    "retrieved were re-fetched from that URL on that date (arXiv abstract page).",
            standards_numbers="Values copied from outputs/isac_standard_gaps.json by key path, not retyped.",
            standards_numbers_quote_checks="Numbers parsed at run time from verified repo quotes (prior_work/"
                                           "isac_standard_scenarios.md) next to the value copied by key path; agree is "
                                           "exact float equality, null where the ledger has no such key.",
            corpus_counts_result_use="Label for the NVIDIA stock-scene rows: whether the scene's shards are counted as corpus "
                                     "or not used as a result (repo_quote_ids give the repo line).",
            corpus_counts_detail_env_counts="Shard-name counts per parsed env value ('None' = no env tag).",
            corpus_counts="Counts over *.npz file names in outputs/elev_sweep_shards. The '_el<deg>_<shard>' suffix is "
                          "stripped and the rest is parsed with src/arm_grammar.parse (strict round trip). No shard is opened.",
            alignment_checks="Numbers read from src/experiment_x410.py (ast literal defaults), parsed from verified repo "
                             "quotes, or read from the draft ledgers by key; comparisons use an absolute tolerance of 1 "
                             "(Hz) or 1 (Hz spacing).",
            draft_grep_counts="Occurrence counts over the full file text as read: cs = case-sensitive substring count, ci = "
                              "case-insensitive substring count, re = regex findall count. A count is not a reading; "
                              "a nonzero Korean word count may refer to another sense of the word.",
            draft_conflicts="draft_location lines are found at run time by searching anchor text; evidence references "
                            "rows of draft_grep_counts, corpus_counts, alignment_checks and standards_numbers by id.",
            draft_conflicts_prose_assertions="Each factual statement in a conflict's prose is re-checked at run time: kind "
                                             "grep/alignment/corpus/quote reads that ledger row, anchors_missing counts "
                                             "anchors not found, value is computed in the section; holds = observed op "
                                             "expected (eq, ge, gt, in). Any holds=false sets _meta.status to "
                                             "complete_with_failures and the script exits 1.",
            draft_conflicts_matches_new_roles="D01 only: statements in the draft that agree with the 2026-09-15 evening "
                                              "engine roles (repo_quotes Q_engine_roles_0915_evening).",
            draft_conflicts_differs_from_new_roles="D01 only: statements in the draft that differ from those engine roles.",
            draft_conflicts_superseded_decision_ids="Repo quotes whose decision the current roles supersede.",
            prose_assertions_summary="Count of all draft_conflicts prose assertions and the failed ones.",
            candidate_contributions_statement="One-sentence form of the candidate contribution.",
            candidate_contributions_stages="Ordered stages of the candidate contribution, with the repo quotes or ledgers "
                                           "each stage rests on.",
            stale_repo_records_id="Row id; equal to quote_id.",
            stale_repo_records_superseded_by="Repo quote id of the record that supersedes this line, or null when the "
                                             "line is only out of date.",
            prior_work="Web rows: arXiv abstract/HTML pages re-opened on the retrieved date; quotes are in sources. Repo "
                       "rows: only what the repo records say, with the quote ids that were verified.",
        ),
        assumptions=[
            dict(id="A1_default_carrier_by_name", flagged=True,
                 text="A shard whose name has no _fc tag was produced at the sweep default carrier. This relies on the "
                      "naming rule quoted in Q_sweep_carrier_tag_rule having held for every shard, including older ones."),
            dict(id="A2_env_prefix_outdoor", flagged=True,
                 text="An 'outdoor' shard is one whose parsed env starts with 'outdoor'."),
            dict(id="A3_web_quotes", flagged=True,
                 text="Quotes in sources were returned by a page-reading tool on the retrieved date from arXiv abstract or "
                      "HTML pages; they were not re-checked character by character against the PDFs."),
            dict(id="A4_repo_records_as_given", flagged=True,
                 text="Rows marked 'repo record only' restate repo notes and were not checked against the papers."),
            dict(id="A5_draft_may_change", flagged=True,
                 text="The draft files are uncommitted and may change after this run; draft_files records the hash read."),
        ],
        seeds=dict(note="no random numbers are used"),
        status="started",
    )
    L.data["sources"] = SOURCES
    L.checkpoint("started")

    qsum = section_repo_quotes(L); L.data["_meta"]["repo_quotes_summary"] = qsum; L.checkpoint("repo_quotes")
    section_standards_numbers(L); L.checkpoint("standards_numbers")
    section_corpus_counts(L); L.checkpoint("corpus_counts")
    section_alignment(L); L.checkpoint("alignment_checks")
    texts = section_drafts(L); L.checkpoint("draft_grep_counts")
    n_prose_failed = section_conflicts(L, texts); L.checkpoint("draft_conflicts")
    section_prior_work(L); L.checkpoint("prior_work")
    section_candidates(L); L.checkpoint("candidate_contributions")
    section_stale(L); L.checkpoint("stale_repo_records")
    section_open_questions(L)

    L.data["_meta"]["finished_utc"] = utc_now()
    L.data["_meta"]["wall_time_s"] = round(time.time() - t0, 3)
    text = json.dumps(L.data, ensure_ascii=False, indent=2, allow_nan=False).lower()
    hits = [w for w in FORBIDDEN_IN_LEDGER if w.lower() in text]
    L.data["_meta"]["wording_guard"] = dict(forbidden_terms=FORBIDDEN_IN_LEDGER, hits=hits)
    ok = not hits and qsum["n_failures"] == 0 and n_prose_failed == 0
    L.checkpoint("complete" if ok else "complete_with_failures")
    print(f"wrote {out}  quotes={qsum}  prose_failed={n_prose_failed}  wording_hits={hits}  "
          f"wall={L.data['_meta']['wall_time_s']} s")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
