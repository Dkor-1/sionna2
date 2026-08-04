# -*- coding: utf-8 -*-
"""monostatic_prior.py — **모노스태틱 ISAC 선행연구 조사**: "그냥 모노스태틱 하면 되지 않나"에 답한다
======================================================================================================

■ 이 스크립트가 확정하는 것

    우리 헤드라인(v_max = λ·PRF_ref/(4 cos(β/2) cos δ), 하한 λ·PRF_ref/4)은 **패시브에 특정된**
    발견이라고 서술해 왔다. 그 서술이 성립하려면 두 가지가 참이어야 한다.

        (가) 모노스태틱 ISAC 센서는 자기 기준신호 반복률을 **자유롭게 고를 수 있다**
        (나) 그 법칙을 **아무도 먼저 말하지 않았다**

    원문을 열어 확인한 결과 **(가)는 절반만 참이고 (나)는 거짓이다.** 이 파일은 그 근거를
    문헌 인용문 단위로 적고, 모노/패시브를 같은 축에 올린 비교표를 만든다.

■ 계산 규약
    v_max = λ·PRF/4  는 **반쪽 구간**(±) 규약이다 — 우리 집 규약이고 LaSen·Chen 도 같다.
    Wei(TVT 2022)·I-SCOUT 은 **전체 폭** 규약(c/(2·K·Ts·fc))이라 우리 값의 2배가 나온다.
    비교표에서는 전부 우리 규약으로 환산해 적고, 원문 값은 따로 남긴다.

■ 산출
    outputs/monostatic_prior.json

실행:  cd sionna2 && PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/monostatic_prior.py
"""
from __future__ import annotations

import json
import math
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (os.path.join(_ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import freespace_scene as fss                               # noqa: E402
from waveforms import PILOT_RATE_HZ                         # noqa: E402

C0 = fss.C0
OUT = os.path.join(_ROOT, "outputs", "monostatic_prior.json")


def lam(fc_hz):
    return C0 / float(fc_hz)


def vmax(fc_hz, prf_hz):
    """우리 집 규약: 반쪽 구간 v_max = λ·PRF/4 [m/s] (β=0, δ=0 하한)."""
    return lam(fc_hz) * float(prf_hz) / 4.0


def vmax_bistatic(fc_hz, prf_hz, beta_deg, delta_deg=0.0):
    g = math.cos(math.radians(beta_deg) / 2.0) * math.cos(math.radians(delta_deg))
    return vmax(fc_hz, prf_hz) / g


# ═══════════════════════════════════════════════════════════════════════════════
# §0  검증 — 우리 법칙으로 선행논문의 숫자를 재현한다
#     (재현되면 그들이 같은 법칙을 쓰고 있다는 뜻이고, 그것이 곧 우선권 문제다)
# ═══════════════════════════════════════════════════════════════════════════════
def verify_against_literature():
    v = {}

    # (1) LaSen §6.4: "two groups of CSI-RS resource set ... period of 10 ms and an offset of 5 ms,
    #     achieving a maximum sampling rate of 200 Hz. At the same 5.8 GHz frequency setting, the
    #     method based on CSI-RS estimation has an unambiguous velocity range of up to 2.6 m/s"
    ours = vmax(5.8e9, 200.0)
    v["lasen_csirs_baseline"] = {
        "inputs": {"fc_hz": 5.8e9, "prf_hz": 200.0, "why_200": "CSI-RS 자원세트 2개 × 주기 10 ms, 오프셋 5 ms"},
        "paper_states_ms": 2.6,
        "our_law_ms": ours,
        "abs_err_ms": abs(ours - 2.6),
        "rel_err": abs(ours - 2.6) / 2.6,
        "match": abs(ours - 2.6) / 2.6 < 0.02,
        "note": "우리 법칙이 LaSen 의 베이스라인 숫자를 소수 첫째자리까지 재현한다. 반쪽 구간 규약도 같다.",
    }

    # (2) Chen 2024 §5: CSI-RS 주기 20 ms → 표본화 50 Hz, 도플러 범위 [-25, +25] Hz,
    #     fc = 3.55 GHz, 회전반경 r = 0.3 m, β = 0 → 최대 측정속도 0.56 rps
    r_m = 0.3
    v_lin = vmax(3.55e9, 50.0)
    rps = v_lin / (2.0 * math.pi * r_m)
    v["chen2024_rotation"] = {
        "inputs": {"fc_hz": 3.55e9, "prf_hz": 50.0, "csirs_period_ms": 20.0,
                   "rotation_radius_m": r_m, "beta_deg": 0.0},
        "paper_states_rps": 0.56,
        "our_law_linear_ms": v_lin,
        "our_law_rps": rps,
        "rel_err": abs(rps - 0.56) / 0.56,
        "match": abs(rps - 0.56) / 0.56 < 0.02,
        "note": "Chen 2024 의 0.56 rps 는 우리 λ·PRF/4 를 회전속도로 환산한 값과 같다.",
    }
    # 그들이 말한 β 완화도 우리 식과 같은 방향인가
    v["chen2024_beta_relief"] = {
        "paper_sentence": "The presence of the double base angle makes the maximum measurable speed slightly greater than 0.56 rps.",
        "our_form": "v_max(beta) = lam*PRF/(4*cos(beta/2)*cos(delta))",
        "relief_at_beta": {f"{b}deg": vmax_bistatic(3.55e9, 50.0, b) / v_lin for b in (0, 30, 45, 60, 90)},
        "verdict": "같은 완화계수 1/cos(beta/2). 우리 X1 정정과 문자 그대로 같은 식이다.",
    }

    # (3) LaSen §3.1.2: 30 kHz SCS, 평균 심볼길이 0.036 ms 로 전 RE 가 데이터면 "14 kHz 까지" 측정
    T_sym_s = 0.036e-3
    fs = 1.0 / T_sym_s
    v["lasen_full_load_ceiling"] = {
        "inputs": {"scs_hz": 30e3, "symbol_s": T_sym_s},
        "slow_time_rate_hz": fs,
        "half_window_hz": fs / 2.0,
        "paper_states_hz": 14e3,
        "match": abs(fs / 2.0 - 14e3) / 14e3 < 0.02,
        "vmax_at_3p5GHz_ms": vmax(3.5e9, fs),
        "vmax_at_5p8GHz_ms": vmax(5.8e9, fs),
        "note": "만재(全 RE 데이터) 상한. LaSen 도 반쪽 구간 규약이다(27.8 kHz 표본화 → ±14 kHz).",
    }

    # (4) 모노스태틱 TDD gNB 가 '조용한 슬롯에서 듣기'로 도망갈 수 있는가 — 왕복지연 산술
    rng = [30.0, 100.0, 300.0, 1000.0]
    v["tdd_listen_in_gap_is_impossible"] = {
        "ofdm_symbol_us_at_30kHz_scs": T_sym_s * 1e6,
        "round_trip_delay_us": {f"{r:.0f}m": 2.0 * r / C0 * 1e6 for r in rng},
        "max_range_whose_echo_lands_after_one_symbol_m": C0 * T_sym_s / 2.0,
        "verdict": ("표적 왕복지연이 OFDM 심볼 하나보다 훨씬 짧다 — 100 m 표적은 0.67 us, 심볼은 36 us. "
                    "즉 모노스태틱 gNB 는 자기 송신이 끝난 뒤 듣는 선택지가 없다. "
                    "TDD 상향 슬롯까지 기다리면 에코는 이미 5 km 밖으로 지나갔다. "
                    "모노스태틱 센싱은 **송신 중 수신**, 곧 인밴드 전이중을 요구한다."),
    }
    return v


# ═══════════════════════════════════════════════════════════════════════════════
# §1  모노스태틱이 실제로 얻는 반복률 — 문헌 근거가 붙은 사다리
# ═══════════════════════════════════════════════════════════════════════════════
def prf_ladder():
    FC = 3.5e9                     # n78 중간대. 우리 표(refrate_law)와 같은 반송파로 통일한다
    rows = []

    def add(key, label, prf, kind, who, source, note, caveat=None):
        rows.append({
            "key": key, "label": label, "prf_hz": prf, "kind": kind, "who_can_use": who,
            "fc_hz": FC, "lambda_m": lam(FC), "v_max_ms": vmax(FC, prf),
            "v_max_kmh": vmax(FC, prf) * 3.6,
            "source": source, "note": note, "caveat": caveat,
        })

    add("ssb_idle", "5G SSB (always-on, default 20 ms)", 50.0, "reference-signal", "passive + monostatic",
        {"doc": "3GPP TS 38.213 §4.1 (cell search); LaSen p.734 §3.1.1",
         "quote": "the Synchronization Signal Block (SSB), which spans up to 7.2 MHz and is typically repeated at 50 Hz",
         "verification": "pdf_quote + spec_clause"},
        "우리 헤드라인 행. LaSen 이 같은 50 Hz 를 독립적으로 인용한다.")

    add("csirs_measured_chen", "CSI-RS as measured (Beijing gNB, 40 slots)", 50.0, "reference-signal",
        "passive + monostatic",
        {"doc": "Chen, Tian, Bai, Wang, Appl. Sci. 14(10):4282, 2024 (MDPI, published, open access), Tables 4-5 and §5",
         "quote": "In experiments, the CSI-RS signal period is 20 ms, and the maximum unambiguous Doppler frequency is 50 Hz. The measurable Doppler frequency shift range is [-25 Hz, 25 Hz].",
         "verification": "pdf_quote"},
        "실측 상용 gNB CSI-RS 주기 40 슬롯 = 20 ms(30 kHz SCS). 실험용 gNB 도 동일.",
        "SSB 와 같은 50 Hz — CSI-RS 라고 자동으로 빨라지지 않는다.")

    add("csirs_measured_lasen", "CSI-RS as measured (China Mobile N41, 2 sets)", 200.0, "reference-signal",
        "passive + monostatic",
        {"doc": "LaSen (SenSys '26) p.741 §6.4 and p.734 §3.1.1",
         "quote": "there are two groups of CSI-RS resource set in the measured N41 gNB channel, with a period of 10 ms and an offset of 5 ms, achieving a maximum sampling rate of 200 Hz",
         "verification": "pdf_quote"},
        "자원세트 2개를 시간 오프셋으로 엮어 200 Hz. 망 설정에 달렸다.",
        "같은 문서 초록/서론은 CSI-RS 최대 500 Hz 라고 쓴다 — 설정상한과 실측값의 차이다.")

    add("csirs_spec_max", "CSI-RS, maximum configurable (sub-6)", 500.0, "reference-signal",
        "passive + monostatic",
        {"doc": "LaSen p.732 §1 citing 3GPP TS 38.331 (RRC, Rel-19); Chen 2024 §3.3 lists the slot-period set",
         "quote": "The maximum configurable repetition frequency for Sub-6 GHz Channel State Information Reference Signals (CSI-RS) is 500 Hz [3]",
         "verification": "pdf_quote (spec value quoted second-hand; 4-slot minimum at 30 kHz SCS = 2 ms = 500 Hz is arithmetically consistent with Chen's period list {4,5,8,...,640 slots})"},
        "표준이 허용하는 천장. 모노스태틱 gNB 도 이 위로는 못 간다 — 규격이 정한 값이지 설계자가 정하는 값이 아니다.",
        "이 천장을 쓰면 통신 오버헤드를 계속 문다. LaSen: 'these benefits come at the cost of increased resource overhead'.")

    add("nr_prs_session", "5G NR PRS (positioning session)", 200.0, "reference-signal",
        "monostatic (network must schedule it)",
        {"doc": "repo src/waveforms.py PILOT_RATE_HZ['nr']['PRS']; LaSen p.734 §3.1.1",
         "quote": "3GPP introduced the Positioning Reference Signal (PRS) [2], which offers improved time-frequency resolution and higher resource element density ... However, these benefits come at the cost of increased resource overhead.",
         "verification": "repo + pdf_quote"},
        "우리 refrate_law 의 nr_prs 행과 같은 값.",
        "LaSen: 'PRS availability depends on UE positioning requests' — 상시 신호가 아니다.")

    add("data_symbols_measured", "PDSCH data symbols, as actually scheduled", 0.0, "data-symbol",
        "monostatic only (needs X[m,n])",
        {"doc": "LaSen p.735 §3.2 Challenge 2 and p.742 §7",
         "quote": "less than 5% of total time duration exhibits a resource-utilization density above 7.1% (Figure 5(b))",
         "verification": "pdf_quote"},
        "PRF 를 못 적는다 — 비균일·확률적이라 '반복률'이라는 양 자체가 정의되지 않는다. 그래서 LaSen 은 압축센싱으로 간다.",
        "⭐ 실측된 트래픽 희소성. 헤드라인 결과는 평균 점유율 3% 에서 나왔다.")

    add("data_symbols_fullload", "PDSCH data symbols, full-buffer ideal", 1.0 / 0.036e-3, "data-symbol",
        "monostatic only (needs X[m,n])",
        {"doc": "LaSen p.734 §3.1.2",
         "quote": "Assume that all available REs are occupied by data signals, for a gNB with 30 kHz subcarrier spacing, the average symbol duration is around 0.036 ms, which can measure Doppler frequency up to 14 kHz.",
         "verification": "pdf_quote"},
        "만재 가정의 상한. 실제로는 위 행이 참이다.",
        "'full buffer' 가정은 최근 문헌이 명시적으로 깨고 있다 — Marchese et al. arXiv:2601.12963 (2026).")

    add("lte_crs", "LTE CRS (contrast row)", 1000.0, "reference-signal", "passive + monostatic",
        {"doc": "LaSen p.734 §3.1.1",
         "quote": "LTE utilizes a cell-specific reference signal (CRS) that broadcasts continuously at 1000 Hz",
         "verification": "pdf_quote"},
        "우리 인프라 서사(LTE→5G 이전 시 상시 기준 반복률 20배 하락)를 LaSen 이 같은 숫자로 확인해 준다.",
        None)
    return rows


# ═══════════════════════════════════════════════════════════════════════════════
# §2  같은 축에 올린 비교표 — 리뷰어의 "왜 모노스태틱 안 하나"에 대한 답
# ═══════════════════════════════════════════════════════════════════════════════
def side_by_side():
    FC = 3.5e9
    def row(**kw):
        kw["v_max_ms"] = vmax(FC, kw["prf_ref_hz"]) if kw["prf_ref_hz"] else None
        return kw

    lanes = [
        row(lane="passive-bistatic, reference-signal matched filter (OUR SETTING)",
            prf_ref_hz=50.0,
            reference="5G SSB, whatever the cell broadcasts",
            who_sets_the_rate="the network operator; the sensor has no vote",
            hardware_cost="one receive chain; no transmitter, no licence, no spectrum",
            interference_problem="direct-path interference from the illuminator",
            interference_number_dB=-47.0,
            interference_source="Sharma/Gonzalez-Prelcic et al. arXiv:2607.11955 (2026): 'the UAV echo is about 44 to 49 dB weaker than the LOS in the considered geometry' (outdoor urban 30-200 m; NOT our chamber geometry)",
            escape_hatch="none within reference-signal-only processing; a reference-channel receiver that reconstructs the full downlink escapes to the data-symbol lane and inherits its traffic dependence",
            what_it_pays="total dependence on ambient transmissions"),
        row(lane="monostatic ISAC gNB, reference-signal only",
            prf_ref_hz=500.0,
            reference="CSI-RS at the maximum configurable sub-6 rate",
            who_sets_the_rate="3GPP TS 38.331 sets the ceiling; the scheduler sets the actual value; using the ceiling costs communication resources",
            hardware_cost="full transmit chain + licensed spectrum + in-band full-duplex front end",
            interference_problem="transmitter self-interference into its own receiver",
            interference_number_dB=-100.0,
            interference_source="Barneto et al., IEEE TMTT 67(10):4042-4054, 2019: 'more than 100 dB of total SI suppression is required'; measured ~100 dB total (25 dB circulator+antenna, >50 dB active RF, remainder digital)",
            escape_hatch="raise CSI-RS rate to the 500 Hz ceiling, or request PRS",
            what_it_pays="hardware, spectrum, self-interference, and communication overhead"),
        row(lane="monostatic ISAC gNB, data-symbol aided (the LaSen lane)",
            prf_ref_hz=None,
            reference="every non-empty RE, reference + PDSCH, because the transmitter knows X[m,n]",
            who_sets_the_rate="user traffic; not a design variable at all",
            hardware_cost="same as above, plus a compressive-sensing back end",
            interference_problem="same self-interference, plus non-uniform ill-conditioned measurement matrix",
            interference_number_dB=-100.0,
            interference_source="same (LaSen itself only did passive isolation: shielding plate + static background removal)",
            escape_hatch="sub-Nyquist sparse recovery over the non-uniform grid (LaSen 2D-OMP + hierarchical global/local)",
            what_it_pays="works only when the cell is loaded; LaSen measured <5% of time above 7.1% RE utilization"),
    ]
    return {
        "carrier_hz": FC, "lambda_m": lam(FC),
        "convention": "v_max is the half-window (+/-) value, v_max = lambda*PRF/4, beta=0 delta=0 floor",
        "lanes": lanes,
        "the_answer_to_the_reviewer": (
            "모노스태틱은 반복률을 자유롭게 고르지 못한다. 규격 천장(sub-6 CSI-RS 500 Hz)이 있고, "
            "그 천장을 쓰면 통신 자원을 문다. 3.5 GHz 에서 그 천장의 v_max 는 10.7 m/s 로, "
            "우리 패시브 SSB 값 1.07 m/s 의 정확히 10배다 — 무한대가 아니다. "
            "모노스태틱이 진짜로 그 벽을 넘는 길은 반복률이 아니라 **데이터 심볼**이고, "
            "그건 자기가 보낸 심볼을 아는 송신기만 쓸 수 있으며, 셀이 한가하면 사라진다. "
            "그리고 그 대가로 100 dB 자기간섭 제거와 송신기·면허대역이 붙는다."
        ),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# §3  LaSen 원문 검증 — 프로젝트 메모의 주장을 원문에 대조한다
# ═══════════════════════════════════════════════════════════════════════════════
LASEN = {
    "identity": {
        "title": "LaSen: Low-Altitude Drone Sensing with 5G-NR Signals",
        "authors": ["Qian Yang", "Yongtao Dai", "Mingrui Li", "Qianyi Huang", "Xu Chen",
                    "Jin Zhang", "Guochao Song", "Qian Zhang", "Xiaofeng Tao"],
        "affiliations": ["SUSTech", "Peng Cheng Laboratory", "Sun Yat-sen University",
                         "CAICT", "HKUST", "BUPT"],
        "venue": "ACM/IEEE International Conference on Embedded Artificial Intelligence and Sensing Systems (SenSys '26)",
        "dates": "May 11-14, 2026",
        "location": "Saint Malo, France",
        "publisher": "ACM, New York, NY, USA",
        "pages": "732-745 (14 pages)",
        "doi": "10.1145/3774906.3800504",
        "isbn": "979-8-4007-2309-4/26/05",
        "licence": "CC BY 4.0",
        "publication_status": "PUBLISHED in the conference proceedings (camera-ready, ACM DL DOI assigned). Not a preprint.",
        "year": 2026,
        "pdf": "/data/public/jeong/papers/5G/26_LaSen.pdf (14 pages, 83,055 chars extracted with PyMuPDF)",
        "citation_line": "Q. Yang, Y. Dai, M. Li, Q. Huang, X. Chen, J. Zhang, G. Song, Q. Zhang, X. Tao, 'LaSen: Low-Altitude Drone Sensing with 5G-NR Signals', in Proc. ACM/IEEE SenSys '26, Saint Malo, France, May 2026, pp. 732-745. DOI 10.1145/3774906.3800504. (published)",
    },
    "memory_claim_under_test": "프로젝트 메모 [[sionna2-lasen-monostatic]]: 'LaSen 은 모노스태틱이다. PDSCH 재활용은 패시브 바이스태틱에 이전 불가.'",
    "verdict": "CONFIRMED, 두 군데 정밀화 필요",
    "geometry": {
        "answer": "MONOSTATIC",
        "evidence": [
            {"where": "§2.2.1 (p.733)",
             "quote": "A practical ISAC implementation involves configuring the gNB with an additional receive chain to capture reflections of its own transmitted signals [32], similar to a monostatic radar. In monostatic configurations, since all of X[m,n] are known, it enables the gNB to achieve channel estimates across all non-empty REs (both reference and data-carrying) within the scheduled bandwidth."},
            {"where": "§8 Discussion, Inter-Cell and Intra-Cell Interference (p.743)",
             "quote": "In mono-static sensing architectures, the intra-cell interference happens when transmitter leakage into the receiver chain, which can saturate front-end components and degrade UAV detection performance."},
            {"where": "counts over the full extracted text",
             "quote": "machine counts over the full extracted text (PyMuPDF, case-insensitive): 'monostatic' 6, 'mono-static' 1, 'bistatic' 1 - and that single 'bistatic' sits at char 79510, inside reference [37] (Nataraja et al., IEEE TVT 74(4):6121-6137, 2025), i.e. the word never describes LaSen's own geometry."},
        ],
    },
    "signal_reused": {
        "reference_signals": ["CSI-RS", "SSB", "DM-RS (present in the emulated waveform)"],
        "data": "PDSCH data-bearing symbols, QPSK, pseudo-random payload",
        "key_sentence": "LaSen, which merges reference and downlink data signals for sensing",
        "why_it_needs_monostatic": "the gNB is the transmitter, so X[m,n] is known for the data symbols too; every non-empty RE becomes a channel measurement. A passive receiver does not know X[m,n] unless it captures/reconstructs a clean reference of the full waveform.",
    },
    "repetition_rates_the_paper_states": {
        "lte_crs_hz": 1000.0,
        "nr_ssb_hz": 50.0,
        "nr_csirs_measured_hz": 200.0,
        "nr_csirs_max_configurable_hz": 500.0,
        "full_load_data_symbol_rate_hz": 1.0 / 0.036e-3,
        "quotes": [
            "LTE utilizes a cell-specific reference signal (CRS) that broadcasts continuously at 1000 Hz, which is widely exploited in existing pervasive sensing studies",
            "While in NR, the design principle is to avoid always-on, mandatory signals such as CRS, reducing spectrum waste and unwanted interference.",
            "These relatively low repetition rates (200 Hz for CSI-RS and 50 Hz for SSB) inherently limit Doppler tracking for high-speed targets.",
            "The maximum configurable repetition frequency for Sub-6 GHz Channel State Information Reference Signals (CSI-RS) is 500 Hz [3]",
        ],
    },
    "velocity_claim": {
        "headline_ms": 20.2,
        "what_it_actually_is": ("무모호 속도 상한이 아니다. 실험에서 도달한 최고 속도 구간의 경계이며, "
                                "그 경계를 정한 것은 기체(DJI Matrice 4E, 최고 21 m/s)다."),
        "verbatim": "We did not measure the maximum speed sensing range of LaSen, since the upper speed limit of the drone is 21 m/s.",
        "accuracy_at_the_top_bin": {"velocity_bin_ms": [14.6, 20.2], "range_rmse_m": 2.2, "velocity_rmse_ms": 1.3},
        "baseline_it_beats": {"method": "CSI-RS-only estimation", "fc_hz": 5.8e9, "prf_hz": 200.0,
                              "paper_value_ms": 2.6,
                              "verbatim": "At the same 5.8 GHz frequency setting, the method based on CSI-RS estimation has an unambiguous velocity range of up to 2.6 m/s, while LaSen extends this range to 20.2 m/s."},
        "mechanism": "sub-Nyquist 2D sparse recovery (2D-OMP) over a non-uniform, time-varying measurement matrix, plus a channel-adaptive global/local hierarchy anchored on high-score segments.",
        "why_this_matters_to_us": ("LaSen 은 λ·PRF/4 를 **반증**하지 않는다. 그 법칙은 균일 표본화·푸리에 처리의 성질이고, "
                                   "LaSen 은 균일 표본화를 버리고 비균일 압축센싱으로 간다. 즉 우리 법칙의 **전제**를 바꾼 것이다. "
                                   "그리고 그 탈출구의 통행료는 (a) 송신기여야 X[m,n] 를 알고, (b) 셀에 트래픽이 있어야 하며, "
                                   "(c) 장면이 희소해야 한다는 것이다."),
        "detection_range_m": 108.0,
    },
    "hardware": {
        "sdr": "NI USRP-2954R, two daughterboard slots, separate slots used for TX and RX to maximise RF isolation",
        "internal_inconsistency": "§8 Discussion says 'our SDR prototype (NI USRP X310) has only two receiving channels' - the implementation section says USRP-2954R. One of the two is wrong; flag it if the hardware is ever quoted.",
        "tx": "power amplifier + 12 dBi panel antenna, transmit power within 24.9 dBm",
        "rx": "10 dBi Yagi + shielding plate between TX and RX antennas",
        "carrier": "5.8 GHz unlicensed band (NOT the 3.5 GHz / N41 band of the gNBs it emulates)",
        "waveform": "MATLAB 5G Toolbox, 30 kHz SCS, 92.16 MHz sampling, 3072-point FFT, 78.12 MHz carrier bandwidth, 2604 non-empty subcarriers + 468 guard",
        "sync": "GPS-disciplined NTP server; drone ground truth from RTK",
        "processing": "MATLAB 2024b offline, 100 ms processing window, 50 ms range-velocity interval, Intel i7-13700K + 64 GB",
        "scenarios": "rooftop (emulating BS deployment) and lawn; drones DJI Matrice 4E (307x388x150 mm, 21 m/s) and DJI Mini 4 Pro (298x373x101 mm, 14 m/s); 1335 range-velocity estimates over 35 trajectories",
    },
    "scoping_caveat_that_must_be_stated_when_citing": (
        "⭐ LaSen 은 상용 gNB 를 통해 드론을 잰 적이 없다. 드론 반사는 자기 USRP 가 5.8 GHz 비면허대역에서 "
        "**만재 송신**한 파형으로 측정했고, 상용 gNB(China Mobile N41 2대, 2200 프레임) 는 오직 **RE 점유 마스크**를 "
        "뽑는 데만 쓰였다. 그 마스크를 만재 측정치에 원소별 곱해서 12,079 개 채널 샘플을 합성했다. "
        "따라서 이것은 '실측 트래픽 패턴 × 실측 드론 반사'의 합성 실험이지 상용망 실험이 아니다. "
        "verbatim: 'The final channel frequency response was obtained by performing element-wise multiplication between the "
        "full-band drone measurements and the derived occupancy masks, generating 12079 channel samples for further analysis.'"
    ),
    "self_interference_handling": {
        "what_they_did": "passive isolation only: a conductive shielding plate between TX and RX antennas + static background removal for the residual",
        "their_own_assessment": "While this approach suffices for proof-of-concept validation under controlled conditions, practical deployments would benefit from advanced active cancellation techniques, such as analog or digital domain interference subtraction [8], which can achieve >50 dB suppression in full-duplex OFDM systems.",
        "no_number_given": "LaSen reports no measured TX-RX isolation figure. The >50 dB is quoted from Barneto et al. 2019, not measured by them.",
        "duplexing_never_discussed": "'TDD' appears 0 times in the paper. n41 is a TDD band; LaSen's own testbed transmits continuously in an unlicensed band with two separate antennas. How a real TDD gNB would receive its own echo during its own downlink slot is not addressed.",
    },
    "traffic_statistics_measured": {
        "dense_segment_fraction": 0.05,
        "quote_1": "According to our measurement (Section 4.2.1), dense resource allocation segments constitute just 5% of the total time span, while sparse segments dominate.",
        "quote_2": "our measurements reveal that, for a given gNB, less than 5% of total time duration exhibits a resource-utilization density above 7.1% (Figure 5(b))",
        "quote_3": "LaSen only increases approximately twice the full-band error under an average channel occupancy of just 3%",
        "why_this_is_the_most_useful_number_in_the_paper": (
            "⭐ 모노스태틱의 데이터심볼 탈출구가 실제로 얼마나 열려 있는지에 대한 **실측 상용망 통계**다. "
            "우리 X4 정정(WiFi 1 kHz 는 트래픽 가정)의 셀룰러 대응물이고, 방향이 같다 — "
            "'데이터 심볼을 쓰면 된다'는 만재 가정이며 실측 망은 만재가 아니다."),
    },
    "internal_inconsistencies_found": [
        "CSI-RS 최대 반복률: 서론은 500 Hz(TS 38.331 인용), §3.1.1 은 '200 Hz for CSI-RS' 로 실측값을 규격값처럼 나란히 쓴다. 둘 다 맞지만 문장만 보면 모순으로 읽힌다.",
        "§3.1.1: 'two sets of periodic CSI-RS with a period of 100 Hz and a 5 ms offset' — 'period of 100 Hz' 는 단위 오류다. §6.4 는 같은 것을 'a period of 10 ms and an offset of 5 ms' 로 옳게 쓴다.",
        "SDR 모델: §5 는 USRP-2954R, §8 은 USRP X310.",
    ],
    "what_does_and_does_not_transfer_to_passive_bistatic": {
        "does_not_transfer": [
            "X[m,n] 의 사전 지식 — 모노스태틱만의 자산이다. 패시브 수신기는 데이터 심볼을 모른다.",
            "'추가 자원 소모 없이' 라는 주장 — 패시브는 애초에 망 자원을 안 쓰므로 이 논증 자체가 성립하지 않는다.",
            "정적 배경제거로 자기간섭을 지운다는 처리 — 패시브의 문제는 자기간섭이 아니라 직접파다.",
        ],
        "does_transfer": [
            "⭐ 비균일·부표본 압축센싱이라는 **처리 틀** 자체. 패시브도 기준채널로 전 파형을 복원할 수 있다면 같은 문제를 푼다.",
            "실측 트래픽 희소성 통계(5% / 7.1% / 3%) — 어느 쪽이든 데이터 심볼에 기대는 순간 이 통계에 걸린다.",
            "'NR 은 상시 의무 기준신호를 없앴다'는 규격 서사 — 우리 [[sionna2-passive-ref-narrative]] 와 같은 진술.",
        ],
        "⭐ the_boundary_is_not_where_we_said_it_was": (
            "경계는 '모노 vs 패시브' 가 아니라 **'기준신호만 쓰기 vs 전 파형 쓰기'** 다. "
            "모노스태틱은 후자가 공짜(자기가 보냈으니 안다)이고 패시브는 유료(깨끗한 기준채널 + 복조/재변조)다. "
            "우리 refrate_law 의 nr_recon 행(ambient=False, continuous_reference=True, 1 kHz 배치 → 21.4 m/s)이 "
            "이미 패시브 쪽 전 파형 레인을 갖고 있다 — 그러니 '패시브는 1.07 m/s 에 묶인다'가 아니라 "
            "'기준신호 정합필터에 머무는 패시브는 1.07 m/s 에 묶인다'로 써야 반박당하지 않는다."
        ),
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# §4  주변 모노스태틱 ISAC 문헌 — 실제로 무엇이 반복률을 제약하는가
# ═══════════════════════════════════════════════════════════════════════════════
MONOSTATIC_LIT = [
    {
        "key": "barneto2019",
        "citation": "C. B. Barneto, T. Riihonen, M. Turunen, L. Anttila, M. Fleischer, K. Stadius, J. Ryynanen, M. Valkama, 'Full-Duplex OFDM Radar With LTE and 5G NR Waveforms: Challenges, Solutions, and Measurements', IEEE Transactions on Microwave Theory and Techniques, vol. 67, no. 10, pp. 4042-4054, Oct. 2019. (published; preprint arXiv:1908.03418)",
        "why_it_matters": "모노스태틱 ISAC 이 무엇을 지불하는지에 대한 **측정된** 숫자의 원천. 우리 비교표의 self-interference 행은 전부 여기서 나온다.",
        "numbers": {
            "tx_above_thermal_noise_dB": 140,
            "total_si_suppression_required_dB": 100,
            "passive_isolation_circulator_plus_antenna_dB": 25,
            "active_rf_cancellation_dB": 50,
            "circulator_plus_active_rf_dB": 75,
            "measured_total_isolation_dB": 100,
            "instantaneous_bandwidth_MHz": 40,
            "carrier_GHz": 2.44,
            "drone_measurement": "measured radar image of a static airborne drone at 40 m, with/without RF and digital cancellation",
        },
        "quotes": [
            "since the eNB/gNB transmit power can be even more than 140 dB larger than the receiver thermal noise floor, facilitating sufficient TX-RX isolation as a whole is technically very challenging, particularly in the monostatic shared-antenna OFDM radar case",
            "more than 100 dB of total SI suppression is required, which calls for multiple complementary methods as no single technique can facilitate such high isolation",
            "the total isolation provided by the circulator and the active RF canceller is some 75 dB, which is very essential to prevent receiver saturation",
            "evidencing measured TX-RX isolation of approximately 100 dB",
            "from the OFDM radar processing perspective, limited TX-RX isolation is primarily a concern in detection of static targets while moving targets are inherently more robust to transmitter self-interference",
        ],
        "honest_note": "마지막 인용문은 우리에게 **불리한** 쪽이다 — 이동표적은 자기간섭에 강하다고 그들이 직접 말한다. 드론은 이동표적이므로 100 dB 요구를 그대로 드론 검출의 관문처럼 쓰면 과장이다. 100 dB 는 수신기 포화 방지와 정적표적 검출의 요구치로 인용해야 한다.",
    },
    {
        "key": "keskin2025",
        "citation": "M. F. Keskin, M. M. Mojahedian, J. O. Lacruz, C. Marcus, O. Eriksson, A. Giorgetti, J. Widmer, H. Wymeersch, 'Fundamental Trade-Offs in Monostatic ISAC: A Holistic Investigation Towards 6G', IEEE Transactions on Wireless Communications, vol. 24, no. 9, pp. 7856-7873, 2025. (published; preprint arXiv:2401.18011)",
        "why_it_matters": "모노스태틱 ISAC 의 교환관계를 정식화한 기준 문헌. 데이터 심볼을 센싱에 쓰면 고차 QAM 의 진폭 변동이 사이드로브를 올린다는 것(deterministic-random trade-off)이 핵심이라, LaSen 식 데이터 재활용의 대가를 이론쪽에서 말해 준다.",
        "what_it_does_not_say": "반복률/무모호 속도를 다루지 않는다('unambiguous velocity' 0회, 'periodicity' 0회). 우리 축과는 직교한다.",
    },
    {
        "key": "marchese2026",
        "citation": "M. Marchese, M. F. Keskin, P. Savazzi, H. Wymeersch, 'Monostatic ISAC Without Full Buffers: Revisiting Spatial Trade-Offs Under Bursty Traffic', arXiv:2601.12963, 19 Jan 2026. (PREPRINT - venue not stated in the PDF; do not cite as published)",
        "why_it_matters": "⭐ 모노스태틱 데이터심볼 레인의 전제(full buffer)를 명시적으로 깨는 최신 문헌. LaSen 의 실측 통계와 같은 결론을 이론쪽에서 낸다.",
        "quotes": [
            "a common baseline assumption underlies these studies: the ISAC transceiver is always assumed to have data available for transmission ... the transmitter buffer is considered to be perpetually full",
            "In such cases, a data-only ISAC system would simply fall silent, causing sensing to halt whenever there is no user data to send.",
            "NFB-Loss (non-full buffer loss): as data are not always available at the BS due to the bursty traffic assumption, under a strict sensing requirement and concurrent transmission or pure communication policies, the BS may not collect any observation within the sensing window Ts. As a result, the BS is not able to detect the target and the probability of detection drops.",
        ],
        "how_we_use_it": "'모노스태틱이면 자유롭다'는 프레이밍의 직접 반례. 트래픽이 없으면 데이터기반 모노스태틱 센싱은 **아예 멈춘다**.",
    },
    {
        "key": "wei2022prs",
        "citation": "Z. Wei, Y. Wang, L. Ma, S. Yang, Z. Feng, C. Pan, Q. Zhang, Y. Wang, H. Wu, P. Zhang, '5G PRS-Based Sensing: A Sensing Reference Signal Approach for Joint Sensing and Communication System', IEEE Transactions on Vehicular Technology, vol. 72, no. 3, pp. 3250-3263, 2023 (arXiv:2211.11488, Nov 2022). (published)",
        "why_it_matters": "PRS 를 슬로타임 축으로 쓰는 정식 처리. v_max 를 comb 크기와 심볼길이로 닫아 준다.",
        "their_formula": "v_max = M_J*c/(2*M*Ts*fc) = c/(2*K_comb^PRS*Ts*fc)",
        "convention_hazard": "⭐ 이것은 **전체 폭** 규약이다(FFT 인덱스 0..M_J-1). 우리 반쪽 구간 규약의 2배 값이 나온다. 나란히 적을 때 반드시 환산해야 한다.",
        "constraint_they_name": "sensing refresh time rho = N_f * T_f with T_f = 10 ms (radio frame) - 프레임 구조가 갱신주기를 정한다는 진술",
        "their_axis": "프레임 **안쪽** 심볼축(우리 scope.intra_burst_alternative 와 같은 국면). 프레임 **사이** 축이 아니다.",
    },
    {
        "key": "iscout2024",
        "citation": "'I-SCOUT: Integrated Sensing and Communications to Uncover Moving Targets in NextG Networks', arXiv:2410.08999, Oct 2024. (PREPRINT - venue not verified)",
        "why_it_matters": "모노스태틱 PRS 자원을 동적으로 조절해 센싱/통신을 저울질한다. 반복률이 설계변수인 유일한 사례에 가깝지만, 조절하는 것은 comb 크기와 PRB 수이지 상시 반복률이 아니다.",
        "their_formula": "v_max = c*M_j/(2*M*Ts*fc) = c/(2*K_comb^PRS*Ts*fc)  (Wei 와 같은 전체 폭 규약)",
        "relevant_sentence": "The target velocity and range were estimated using the compliant PRS in a monostatic radar scenario in [11]. In comparison, I-SCOUT offers dynamic adjustment of PRS resource blocks in a monostatic setting to balance the sensing-communication performance tradeoffs.",
    },
    {
        "key": "golzadeh2023",
        "citation": "M. Golzadeh, E. Tiirola, L. Anttila, J. Talvitie, K. Hooli, O. Tervo, I. Peruga, S. Hakola, M. Valkama, 'Downlink Sensing in 5G-Advanced and 6G: SIB1-assisted SSB Approach', in Proc. IEEE 97th Vehicular Technology Conference (VTC2023-Spring), Florence, Italy, June 2023. DOI 10.1109/VTC2023-Spring57618.2023.10200933. (published)",
        "why_it_matters": "⭐ 네트워크측(모노스태틱) 다운링크 센싱에서 **SSB 만 쓰면 레이더 모호가 생긴다**는 것을 명시하고, SIB1/DCI 심볼을 덧붙여 푼다. LaSen 의 5G 판 선배이며, 모노스태틱도 SSB 반복률 문제에서 자유롭지 않다는 직접 증거.",
        "abstract_quote": "In general, the synchronization signal block (SSB) is a suitable candidate for always-on downlink sensing, due to its frequent periodical availability and because of its beam-sweeping nature. However, as this work demonstrates, using only the SSB has challenges related to radar ambiguity while being also limited in both distance and velocity resolution due to limited bandwidth and per-beam time duration, respectively. A novel solution is then introduced by combining SSB with downlink control information (DCI) and system information block 1 (SIB1) symbols.",
        "numbers": {"psl_suppression_dB": 25, "resolution_improvement_pct": [120, 190],
                    "carriers_GHz": [3.5, 28]},
        "verification": "abstract verified verbatim via the Tampere University research portal record; full text NOT read (repository PDF is behind an anti-bot challenge). Do not quote body text.",
    },
    {
        "key": "liu2023monopos",
        "citation": "S. Liu, H. Wang, M. Pan, P. Liu, Y. Ma, Y. Huang, '5G NR monostatic positioning with array impairments: Data-and-model-driven framework and experiment results', in Proc. 3rd ACM MobiCom Workshop on Integrated Sensing and Communications Systems, 2023, pp. 1-6. (published)",
        "why_it_matters": "LaSen 이 '모노스태틱 구성은 gNB 에 수신 체인을 하나 더 다는 것'이라고 말할 때 근거로 다는 [32]. 즉 그 아키텍처 주장의 출처.",
        "verification": "bibliographic only, from LaSen's reference list. PDF not read.",
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
# §5  우선권 점검 — 누가 이미 이 논증을 했는가
# ═══════════════════════════════════════════════════════════════════════════════
PRIORITY = {
    "question": "패시브(또는 어떤) 수신기의 무모호 속도가 기준신호 반복률로 결정된다는 논증을 누가 먼저 했는가",
    "answer": "여러 명이 이미 했다. 그중 하나는 우리 식과 기호까지 같다.",
    "hits": [
        {
            "rank": 1,
            "severity": "⭐⭐ CRITICAL - our formula, symbol for symbol, two years earlier",
            "citation": "P. Chen, L. Tian, Y. Bai, J. Wang, 'Rotating Target Detection Using Commercial 5G Signal', Applied Sciences (MDPI), vol. 14, no. 10, art. 4282, 2024. DOI 10.3390/app14104282. (published, open access)",
            "geometry": "passive bistatic (their words: 'a passive radar target detection method based on 5G signals'; 'Utilizing 5G signals for rotating target detection essentially employs bistatic radar principles')",
            "what_they_already_have": [
                "Eq. (4): f_d = (2v/lambda)*cos(beta/2)*cos(delta), with beta named 'double base angle' and delta 'the angle between the direction of the target velocity and the bisector of the double base angle' - identical to our Eq. and identical symbols.",
                "CSI-RS repetition period -> slow-time sampling rate -> Doppler window: 'the CSI-RS signal period is 20 ms, and the maximum unambiguous Doppler frequency is 50 Hz. The measurable Doppler frequency shift range is [-25 Hz, 25 Hz].'",
                "The substitution carried out numerically: '...when the signal carrier frequency is 3.55 GHz, the rotation radius is 0.3 m, and the double base angle is 0, the maximum measurable speed is 0.56 rps.'",
                "The bistatic relief: 'The presence of the double base angle makes the maximum measurable speed slightly greater than 0.56 rps.'",
                "Real measurements on both a laboratory 5G base station and a commercial 5G base station (CSI-RS period 40 slots in both).",
            ],
            "what_they_do_NOT_have": [
                "closed form written as v_max = lambda*PRF_ref/(4 cos(beta/2) cos delta) - they compose it numerically, not symbolically",
                "any cross-standard table (their world is 5G CSI-RS only; no LTE / WiFi / DVB-T / DAB / DTMB / FM row)",
                "any real aircraft; the target is a 0.3 m rotating arm on a stepper motor, framed as a rotor surrogate",
                "the design inversion (PRF_req = 4v/lambda, f_c,max = c*PRF/4v)",
                "the infrastructure-migration narrative (LTE CRS 1 kHz -> NR SSB 50 Hz)",
                "any detection-performance consequence (Pd, blind fraction, CPI independence)",
            ],
            "what_this_does_to_our_claim": (
                "⭐ 'v_max = λ·PRF_ref/(4 cos(β/2) cos δ) 라는 식' 자체는 **우리 것이 아니다**. "
                "Chen 2024 가 2년 먼저, 같은 기호로, 실측까지 붙여 냈다. "
                "novelty_guard 에 Abratkiewicz 2023 만 적혀 있고 Chen 2024 는 없다 — 즉시 추가해야 한다. "
                "우리가 여전히 새로 놓는 것은 (a) 근거 붙은 **교차표준** 표, (b) 실기체 최고속도 겹치기, "
                "(c) 설계규칙 역산, (d) 인프라 이전 서사, (e) 검출성능(블라인드/접힘/CPI 독립성)까지의 연결이다. "
                "식은 '우리가 정리한 형태'로 쓰되 '우리가 처음'이라고 쓰면 안 된다."
            ),
        },
        {
            "rank": 2,
            "severity": "known - already in our novelty_guard",
            "citation": "K. Abratkiewicz, A. Ksiezyk, M. Plotka, P. Samczynski, J. Wszolek, T. P. Zielinski, 'SSB-Based Signal Processing for Passive Radar Using a 5G Network', IEEE J. Sel. Topics Appl. Earth Obs. Remote Sens., vol. 16, pp. 3469-3484, 2023. DOI 10.1109/JSTARS.2023.3262291. (published)",
            "status": "이미 outputs/refrate_law.json novelty_guard 에 기록되어 있다. 이번 라운드에서 새로 확인한 것: 후속 문헌이 이 논문을 바로 그 논거로 인용한다 - Wu et al. arXiv:2511.14529 (2025): 'the study also highlighted that the maximum unambiguous velocity of PCL is severely constrained by the SSB's long transmission periodicity (e.g., 10 ms minimum)'.",
            "note": "PDF 미확보 상태 그대로다. 위 인용은 **제3자의 요약**이므로 원문 문장으로 쓰면 안 된다.",
        },
        {
            "rank": 3,
            "severity": "the monostatic-side statement of the same problem",
            "citation": "Golzadeh et al., VTC2023-Spring (published) - see MONOSTATIC_LIT.golzadeh2023",
            "status": "네트워크측 다운링크 센싱에서 SSB 만으로는 레이더 모호가 있다고 초록에서 명시. 우리 논지의 모노스태틱 판.",
        },
        {
            "rank": 4,
            "severity": "the whole paper is built on the bound",
            "citation": "LaSen, SenSys '26 (published)",
            "status": "LaSen 의 존재 이유가 '5G 기준신호 반복률이 나이퀴스트를 못 맞춘다'이다. 그들은 그것을 자기 문제제기로 쓰고, 우리 논지를 3.5 GHz/100 mph 산술로 그대로 적는다: 'For a 3.5 GHz carrier, this results in a maximum Doppler shift of 1044 Hz ... the Nyquist-Shannon sampling theorem requires ... 2087 Hz.'",
            "note": "그리고 그들은 이 문제를 이미 **푼 것으로 주장한다**(모노스태틱 + 데이터심볼 + 압축센싱). 우리가 '아무도 안 다뤘다'고 쓰면 즉시 반박당한다.",
        },
        {
            "rank": 5,
            "severity": "second-hand attribution inside LaSen",
            "citation": "LaSen §7 on Chen et al. [10]",
            "quote": "Leveraging commodity gNB CSI-RS, Chen et al. [10] demonstrate rotational motion detection using commercial gNB CSI-RS. It also reveals that the unambiguous velocity is bounded by the CSI-RS repetition period.",
            "status": "⭐ SenSys 2026 논문이 '무모호 속도는 CSI-RS 반복주기가 정한다'는 명제의 **우선권을 명시적으로 Chen 2024 에 돌린다**. 우리가 그 명제의 최초 제기자라고 쓸 여지는 없다.",
        },
    ],
    "verdict_for_our_paper": {
        "must_stop_claiming": [
            "무모호 속도가 상시 기준신호 반복률로 결정된다는 **사실**을 우리가 처음 지적했다는 어떤 형태의 주장",
            # ⭐ 정정 R1 — 근거를 Chen 에서 Abratkiewicz 로 옮긴다(주장 자체는 그대로 금지).
            "그 식의 바이스태틱 일반형(β, δ 포함)이 새롭다는 주장 — Abratkiewicz 외 JSTARS "
            "2023 식 (16) 이 반구간 규약까지 같은 식을 이미 인쇄했다 (Chen 2024 는 닫힌 식 없음)",
            "'모노스태틱은 반복률을 자유롭게 고르므로 이 문제가 없다'는 문장 — 절반만 참이다",
        ],
        "can_still_claim": [
            "규격 조항으로 근거를 댄 **교차표준** 반복률→v_max 표(셀룰러/WLAN/방송 한 축) — 선행에 없다",
            "실기체 게재 최고속도를 같은 축에 얹은 판정",
            "설계규칙 역산(PRF_req, T_ref,max, f_c,max)",
            "인프라 이전 서사(LTE CRS 1 kHz → NR SSB 50 Hz, 40.7 → 1.07 m/s; λ 기여는 1.90배뿐)",
            "⭐ **패시브 대 모노스태틱 경계** 자체를 숫자로 그은 것 — 이번 조사가 그 근거를 마련했다. 선행 중 이 비교를 한 편은 못 찾았다",
            "접힘 ≠ 미검출, CPI 독립성, 멀티스태틱 해모호 같은 **결과쪽** 정량화(X1~X6)",
        ],
        "the_sharper_framing_this_round_buys": (
            "낡은 프레임: '패시브는 1.07 m/s 에 묶인다 — 모노스태틱은 자유롭다.' → 두 절 다 틀렸다.\n"
            "새 프레임: '기준신호 정합필터에 머무는 한 v_max = λ·PRF_ref/4 이고, 이 벽은 모노/패시브 공통이다. "
            "3GPP 가 sub-6 CSI-RS 에 건 천장은 500 Hz(3.5 GHz 에서 10.7 m/s)이고 그마저 통신자원을 문다. "
            "벽을 진짜로 넘는 유일한 길은 전 파형(데이터 심볼)을 쓰는 것인데, 모노스태틱은 그것이 공짜(자기가 보냄)이고 "
            "패시브는 유료(깨끗한 기준채널 + 복조/재변조)다. 그리고 그 길은 양쪽 모두 트래픽에 종속된다 — "
            "실측 상용 gNB 는 시간의 95% 를 RE 점유율 7.1% 아래에서 보낸다.'"
        ),
    },
}


def main():
    t0 = time.time()
    ver = verify_against_literature()
    ladder = prf_ladder()
    table = side_by_side()

    doc = {
        "meta": {
            "script": "benchmark/monostatic_prior.py",
            "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "question": "모노스태틱 ISAC(LaSen 류)까지 넣으면 우리 v_max 서사는 어떻게 되는가 — 그리고 그 논증을 누가 먼저 했는가",
            "house_rules": "figure text English; prose Korean; every number carries a source; venue + publication status + year for every citation",
            "repo_functions_used": ["freespace_scene.C0", "waveforms.PILOT_RATE_HZ"],
            "convention": "v_max = lambda*PRF/4 는 **반쪽 구간**(±) 값이다. Wei(TVT 2022)·I-SCOUT 은 전체 폭 규약이라 2배로 나온다.",
            "archives_searched": [
                "/data/public/jeong/papers (5G 7건 / LTE 7건 / WiFi 7건) — LaSen 원문은 여기 있었다: 5G/26_LaSen.pdf",
                "/data/public/sionna_jeong/papers_isac_sionna (38 항목) — LaSen 사본 없음. R20_verification_0729 에 언급만 존재",
                "arXiv API + web (Barneto 1908.03418, Keskin 2401.18011, Wei 2211.11488, Marchese 2601.12963, I-SCOUT 2410.08999, Wu 2511.14529, Jopanya 2504.02641)",
                "MDPI res.mdpi.com 직접 다운로드 (Chen 2024 applsci-14-04282)",
            ],
            "runtime_s": None,
        },
        "headline_of_this_file": (
            "1) 프로젝트 메모는 옳았다 — LaSen 은 모노스태틱이고, 원문이 두 곳에서 그렇게 쓴다. "
            "2) 그러나 '모노스태틱은 반복률을 자유롭게 고른다'는 우리 프레이밍은 틀렸다 — 3GPP 가 sub-6 CSI-RS 에 500 Hz 천장을 걸었고 "
            "실측 상용 gNB 는 50~200 Hz 로 돈다. 모노스태틱의 진짜 탈출구는 반복률이 아니라 **데이터 심볼**이며, 그것은 트래픽에 종속된다. "
            "3) 그리고 v_max = λ·PRF/(4cos(β/2)cosδ) 는 우리 것이 아니다 — ⭐ 우선권은 "
            "**Abratkiewicz 외, IEEE JSTARS 16:3469-3484 (2023), 식 (16) p.3476** 이고 "
            "반구간 규약까지 같다. (이전 기록의 'Chen 2024 가 같은 기호로 먼저 냈다' 는 "
            "**철회됐다** — Chen 은 닫힌 식을 인쇄하지 않는다. docs/RETRACTION_LOG.md R1) "
            "⭐ 대신 Abratkiewicz 결론 p.3482 가 드론을 향후과제로 명시한다 — 우리 자리다."
        ),
        "verification_of_our_law_against_prior_measurements": ver,
        "lasen": LASEN,
        "prf_ladder_at_3p5GHz": ladder,
        "side_by_side": table,
        "monostatic_literature": MONOSTATIC_LIT,
        "priority_check": PRIORITY,
        "consistency_with_existing_outputs": {
            "refrate_law.json": [
                "illuminators.rows.nr_ssb.v_max_ms = 1.07068735 (3.5 GHz, 50 Hz) — LaSen 이 같은 50 Hz 를 독립 인용하므로 이 행은 외부 지지를 얻었다",
                "illuminators.rows.nr_prs_max.prf_hz = 500.0 — 이번에 LaSen 이 이 500 Hz 를 'CSI-RS 최대 설정 가능 반복률'로 규격 인용한다. 우리 라벨('PRS 4-slot min')과 그들의 라벨(CSI-RS)이 다르지만 값·출처(TS 38.331 슬롯 최소주기)는 같은 뿌리다 — 라벨 문구를 재검토할 것",
                "illuminators.rows.lte_crs.prf_hz = 1000.0 — LaSen 이 'broadcasts continuously at 1000 Hz' 로 확인",
                "illuminators.rows.nr_recon (ambient=False, continuous_reference=True) — 이 행이 곧 '패시브의 전 파형 레인'이고, 이번 조사가 그 레인을 서사의 중심으로 올려야 한다고 말한다",
                "novelty_guard — Chen et al. Appl. Sci. 2024 항목이 **없다**. 추가 필요(우선권 1순위)",
                "design_levers — '망에 PRS 를 요청한다' 레버 옆에 '모노스태틱으로 간다' 레버를 추가할 수 있다: 이득 1.07→10.7 m/s(10배, 규격 천장), 대가 송신기+면허대역+100 dB 자기간섭제거+통신 오버헤드",
            ],
            "vmax_hardening.json": [
                "X1(일반형) — Chen 2024 가 같은 일반형을 이미 갖고 있다는 사실로 보강/양보 필요",
                "X4(WiFi 1 kHz 는 트래픽 가정) — 셀룰러 대응물이 생겼다: LaSen 실측 '시간의 95% 가 RE 점유율 7.1% 미만'. 데이터심볼 기반 주장은 어느 표준이든 트래픽 가정이다",
                "X5(멀티스태틱은 푼다) — 변화 없음",
            ],
        },
        "gaps_this_round_did_not_close": [
            "Abratkiewicz JSTARS 2023 원문 PDF 여전히 미확보(우리 최근접 선행). 지금 기록은 서지+제3자 요약뿐이다",
            "Golzadeh VTC2023 본문 미확보(리포지터리 봇차단). 초록만 축자 확인",
            "3GPP TS 38.331 의 CSI-RS 주기 최소값을 **원 규격에서** 직접 확인하지 않았다 — LaSen 의 500 Hz 인용과 Chen 의 슬롯주기 목록이 서로 맞는다는 간접 정합성뿐이다",
            "NR TDD DL/UL 패턴이 모노스태틱 센싱 듀티에 거는 제약은 왕복지연 산술로만 논증했다. 실제 배치 패턴(DDDSU 등) 통계의 인용 가능한 출처를 못 붙였다",
            "우리 report12 의 LaSen 비판 문장 원문을 이 라운드에서 열어보지 않았다 — 그 문장이 'PDSCH 재활용 불가'를 넘어 과일반화하고 있는지는 별도 점검이 필요하다",
        ],
    }
    doc["meta"]["runtime_s"] = time.time() - t0

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)

    print(f"[monostatic_prior] wrote {OUT}")
    print(f"  LaSen 베이스라인 재현: 논문 2.6 m/s vs 우리 법칙 {ver['lasen_csirs_baseline']['our_law_ms']:.4f} m/s "
          f"(상대오차 {ver['lasen_csirs_baseline']['rel_err']*100:.2f}%)")
    print(f"  Chen 2024 재현: 논문 0.56 rps vs 우리 법칙 {ver['chen2024_rotation']['our_law_rps']:.4f} rps "
          f"(상대오차 {ver['chen2024_rotation']['rel_err']*100:.2f}%)")
    print(f"  LaSen 만재 상한: 논문 14 kHz vs 우리 산술 {ver['lasen_full_load_ceiling']['half_window_hz']/1e3:.2f} kHz")
    print("  3.5 GHz 사다리:")
    for r in ladder:
        p = f"{r['prf_hz']:9.1f} Hz" if r["prf_hz"] else "    n/a   "
        v = f"{r['v_max_ms']:8.2f} m/s" if r["prf_hz"] else "     -     "
        print(f"    {p}  {v}   {r['label']}")


if __name__ == "__main__":
    main()
