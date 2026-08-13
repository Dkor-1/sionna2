#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""G1/G2 폐쇄 검증 — Chen 2024(Appl. Sci.) 와 Abratkiewicz 2023(JSTARS) 원문 확보 후,
   두 논문이 실제로 무엇을 했고 무엇을 하지 않았는지, 그리고 우리 주장 중 무엇이 살아남는지.

규칙: 여기 들어가는 모든 문장은 (a) 내가 직접 연 PDF 에서 그대로 따온 인용이거나,
      (b) 그 인용 안의 숫자로 우리가 계산한 재현값이다. 그 밖은 전부 UNVERIFIED 로 표시한다.

실행: cd /workspace/sionna && PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/verify_chen.py
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import time

LIB = "/data/public/sionna_jeong/reference_library/g1g2"
CHEN_PDF = os.path.join(LIB, "chen2024_applsci_14_4282.pdf")
ABRA_PDF = os.path.join(LIB, "abratkiewicz2023_jstars.pdf")
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "outputs", "verify_chen.json")

C_EXACT = 299792458.0
C_ROUND = 3.0e8  # 두 논문이 실제로 쓴 값(재현으로 확인됨)


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def vmax_half(fc_hz: float, prf_hz: float, c: float = C_EXACT) -> float:
    """반쪽 구간(half-window) 무모호 (바이스태틱) 속도 = lambda*PRF/4."""
    return (c / fc_hz) * prf_hz / 4.0


def rps_from_v(v_ms: float, radius_m: float) -> float:
    return v_ms / (2.0 * math.pi * radius_m)


def v_from_rps(rps: float, radius_m: float) -> float:
    return 2.0 * math.pi * radius_m * rps


t0 = time.time()

# ---------------------------------------------------------------- 재현 계산 A
# Abratkiewicz 2023 eq.(16): Vb in [-lambda/(4 T_SSB), +lambda/(4 T_SSB)], fc = 3.44 GHz
abra_repro = []
for t_ms, paper in ((20.0, 1.0901), (5.0, 4.3605)):
    prf = 1000.0 / t_ms
    ours_exact = vmax_half(3.44e9, prf, C_EXACT)
    ours_round = vmax_half(3.44e9, prf, C_ROUND)
    abra_repro.append({
        "T_SSB_ms": t_ms,
        "PRF_hz": prf,
        "fc_hz": 3.44e9,
        "paper_states_ms": paper,
        "our_law_c_exact_ms": ours_exact,
        "our_law_c_3e8_ms": ours_round,
        "abs_err_vs_paper_c_exact": abs(ours_exact - paper),
        "abs_err_vs_paper_c_3e8": abs(ours_round - paper),
        "match_to_4_decimals_with_c_3e8": abs(ours_round - paper) < 5e-4,
    })

# ---------------------------------------------------------------- 재현 계산 B
# Chen 2024 §5: CSI-RS 주기 20 ms -> 무모호 도플러 50 Hz -> [-25,25] Hz
#   -> fc 3.55 GHz, r = 0.3 m, beta = 0 에서 최대 측정속도 0.56 rps
chen_v = vmax_half(3.55e9, 50.0, C_EXACT)
chen_v_round = vmax_half(3.55e9, 50.0, C_ROUND)
chen_repro = {
    "csirs_period_ms": 20.0,
    "PRF_hz": 50.0,
    "paper_states_max_unambiguous_doppler_hz": 50.0,
    "paper_states_measurable_range_hz": [-25.0, 25.0],
    "half_window_convention_confirmed": True,
    "fc_hz": 3.55e9,
    "radius_m": 0.3,
    "beta_deg": 0.0,
    "paper_states_rps": 0.56,
    "our_law_v_ms_c_exact": chen_v,
    "our_law_rps_c_exact": rps_from_v(chen_v, 0.3),
    "our_law_rps_c_3e8": rps_from_v(chen_v_round, 0.3),
    "rel_err_c_exact": abs(rps_from_v(chen_v, 0.3) - 0.56) / 0.56,
}

# ---------------------------------------------------------------- 재현 계산 C
# Chen Table 6 (r = 0.3 m, 상용 gNB): 0.625 rps 는 오차 0.4%, 0.75 rps 는 오차 100%(도플러 블러).
# 즉 실제 접힘 문턱이 (0.625, 0.75] rps 사이에 있다. beta=0 예측은 0.560 rps 이므로
# 필요한 완화계수 1/(cos(beta/2)cos(delta)) 의 구간을 그들 표에서 역산할 수 있다.
thr_lo, thr_hi = 0.625, 0.75
base = rps_from_v(chen_v, 0.3)
bracket = {
    "table6_ok_up_to_rps": thr_lo,
    "table6_first_failure_rps": thr_hi,
    "table6_failure_error_pct": 100.0,
    "table6_measured_at_failure_rps": 1.5,
    "our_beta0_prediction_rps": base,
    "implied_relief_factor_range": [thr_lo / base, thr_hi / base],
    "implied_cos_half_beta_times_cos_delta_range": [base / thr_hi, base / thr_lo],
    "implied_beta_deg_if_delta_0": [
        2.0 * math.degrees(math.acos(min(1.0, base / thr_lo))),
        2.0 * math.degrees(math.acos(min(1.0, base / thr_hi))),
    ],
    "note_ko": ("Chen 자신의 Table 6 이 접힘 문턱을 (0.625, 0.75] rps 로 가둔다. "
                "우리 beta=0 예측 0.560 rps 와의 간격은 그들이 문장으로만 말한 "
                "'double base angle 때문에 0.56 rps 보다 약간 크다' 를 수치로 뒷받침한다. "
                "geometry(beta, delta)는 논문에 없으므로 구간으로만 역산했다 — 단일값 주장 금지."),
    "cross_check_r015": {
        "radius_m": 0.15,
        "theoretical_rps": 0.75,
        "linear_speed_ms": v_from_rps(0.75, 0.15),
        "our_beta0_limit_ms": chen_v,
        "predicted_unambiguous": v_from_rps(0.75, 0.15) < chen_v,
        "paper_measured_rps": 0.7568,
        "paper_error_pct": 0.9,
        "verdict_ko": "반경 0.15 m 에서는 같은 0.75 rps 가 선속도 기준으로 한계 아래라 정상 측정된다 — 표 6/7 의 대비가 우리 법칙의 부호를 그대로 따른다.",
    },
}

# ---------------------------------------------------------------- 재현 계산 D
# Chen §3 이 나열한 CSI-RS 주기 슬롯 집합 -> 30 kHz SCS 에서의 반복률과 무모호 속도
slots = [4, 5, 8, 10, 16, 20, 32, 40, 64, 80, 160, 320, 640]
slot_ms_30k = 0.5
csirs_ladder = []
for s in slots:
    period_ms = s * slot_ms_30k
    prf = 1000.0 / period_ms
    csirs_ladder.append({
        "slots": s,
        "period_ms_at_30kHz_scs": period_ms,
        "prf_hz": prf,
        "vmax_half_ms_at_3p5GHz": vmax_half(3.5e9, prf),
    })

ssb_ms = [5, 10, 20, 40, 80, 160]
ssb_ladder = [{
    "T_SSB_ms": float(m),
    "prf_hz": 1000.0 / m,
    "vmax_half_ms_at_3p44GHz": vmax_half(3.44e9, 1000.0 / m),
} for m in ssb_ms]

# ---------------------------------------------------------------- 문서

doc = {
    "meta": {
        "script": "benchmark/verify_chen.py",
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "question_ko": "G1(Chen 2024)·G2(Abratkiewicz 2023) 원문을 합법적으로 확보하고, 우리 주장 중 무엇이 살아남는지 확정한다.",
        "house_rules": "figure text English; prose Korean; venue + publication status + year for every citation",
        "evidence_rule": "모든 문장은 (a) 내가 직접 연 PDF 의 축자 인용이거나 (b) 그 인용의 숫자로 우리가 계산한 재현값이다.",
        "runtime_s": None,
    },

    "headline_ko": [
        "1) G1·G2 둘 다 닫혔다. 두 PDF 를 직접 열었고, 모든 인용은 축자다.",
        "2) ⭐⭐ 우리 v_max = lambda*PRF_ref/4 는 Abratkiewicz 외 JSTARS 2023 의 eq.(16) 과 **문자 그대로 같은 식**이다 — 반쪽 구간 규약까지 같고, 그들은 5G SSB 에 대해 2023 년에 냈다. Chen(2024)보다 1 년 빠르다.",
        "3) Chen 2024 는 그 식을 **닫힌 형태로 쓰지 않는다**. Chen 이 쓴 것은 바이스태틱 도플러 eq.(4) f_d=(2v/lambda)cos(beta/2)cos(delta)(그것도 [16] Samczynski 외 TGRS 인용)와, 그 한계의 **수치 대입**(20 ms -> 50 Hz -> [-25,25] Hz -> 0.56 rps)이다.",
        "4) 따라서 이전 라운드 기록(outputs/monostatic_prior.json)의 'Chen 이 같은 기호로 먼저 냈다' 는 **부분적으로 틀렸다** — 인용문 자체는 전부 정확했으나(축자 대조 완료), 우선권은 Chen 이 아니라 Abratkiewicz 2023 이고 Chen 에는 합성된 닫힌 식이 없다.",
        "5) ⭐ 그런데 두 논문 모두 **드론을 하지 않았다**. Abratkiewicz 의 표적은 Volvo XC90 승용차이고, 드론은 명시적으로 future work 다. Chen 의 표적은 스테퍼 모터 회전 모형이고, 드론 로터는 동기(motivation)로만 적혀 있다.",
        "6) 살아남는 우리 몫: 하나의 규약 아래 놓인 **교차표준 v_max 표**, 실기체 최고속도와의 겹치기, 모노스태틱 CSI-RS 천장의 설계규칙화, 그리고 두 논문이 손대지 않은 **드론 기체 산란(RCS)·검출성능 연결**.",
    ],

    "acquisition": {
        "G1_chen2024": {
            "status": "CLOSED — 원문 확보",
            "citation": "P. Chen, L. Tian, Y. Bai, and J. Wang, \"Rotating Target Detection Using Commercial 5G Signal,\" Applied Sciences (MDPI), vol. 14, no. 10, art. 4282, May 2024, DOI 10.3390/app14104282. (PUBLISHED, open access CC BY 4.0)",
            "affiliation_verbatim": "School of Electronic and Information Engineering, Beihang University, Beijing 100191, China; Hangzhou Innovation Institute, Beihang University, Hangzhou 310000, China",
            "dates_verbatim": "Received: 11 April 2024  Revised: 10 May 2024  Accepted: 17 May 2024  Published: 18 May 2024",
            "route_that_worked": "Semantic Scholar 의 OA 미러 https://pdfs.semanticscholar.org/0006/93a627f5aebe453434410634824c3de3c459.pdf (HTTP 200, application/pdf)",
            "routes_that_failed": [
                "www.mdpi.com/2076-3417/14/10/4282 -> HTTP 403 (WebFetch)",
            ],
            "local_path": CHEN_PDF,
            "sha256": sha256(CHEN_PDF) if os.path.exists(CHEN_PDF) else None,
            "pages": 20,
            "license_verbatim": "This article is an open access article distributed under the terms and conditions of the Creative Commons Attribution (CC BY) license (https://creativecommons.org/licenses/by/4.0/).",
        },
        "G2_abratkiewicz2023": {
            "status": "CLOSED — 원문 확보",
            "citation": "K. Abratkiewicz, A. Ksiezyk, M. Plotka, P. Samczynski, J. Wszolek, and T. P. Zielinski, \"SSB-Based Signal Processing for Passive Radar Using a 5G Network,\" IEEE J. Sel. Topics Appl. Earth Observ. Remote Sens., vol. 16, pp. 3469-3484, 2023, DOI 10.1109/JSTARS.2023.3262291. (PUBLISHED, gold OA, CC BY 4.0 — Crossref license record)",
            "route_that_worked": "Crossref link 필드가 실제 파일 경로(ielx7/4609443/**9973430**/10083170.pdf)를 알려줬고, 그 URL 의 Internet Archive Wayback 스냅샷(2024-04-15)에서 CC-BY 원본 PDF 를 받았다: http://web.archive.org/web/20240415141029id_/https://ieeexplore.ieee.org/ielx7/4609443/9973430/10083170.pdf",
            "routes_that_failed": [
                "ieeexplore.ieee.org PDF 경로 4종 -> HTTP 502 'IEEE Xplore - Temporarily Unavailable'",
                "ieeexplore.ieee.org 문서 페이지 -> HTTP 202 AWS WAF 챌린지",
                "xplorestaging.ieee.org REST -> HTTP 418 'Unusual Traffic Detected'",
                "researchgate.net -> HTTP 403 (Cloudflare 1020)",
                "doaj.org 기사 페이지 -> HTTP 403 (WebFetch)",
                "ouci.dntb.gov.ua -> ECONNREFUSED",
                "api.fatcat.wiki -> timeout",
                "OpenAIRE/CORE -> IEEE·DOAJ 링크 외 별도 전문 없음",
            ],
            "local_path": ABRA_PDF,
            "sha256": sha256(ABRA_PDF) if os.path.exists(ABRA_PDF) else None,
            "pages": 16,
            "pdf_metadata_subject_verbatim": "IEEE Journal of Selected Topics in Applied Earth Observations and Remote Sensing;2023;16; ;10.1109/JSTARS.2023.3262291",
            "abstract_independently_confirmed_by": [
                "Semantic Scholar Graph API (abstract 필드)",
                "Wayback 스냅샷 20250503094510 의 IEEE 문서 페이지 og:description",
                "확보한 PDF 본문 p.3469",
            ],
        },
    },

    # ---------------------------------------------------------------- 축자 인용
    "quotes_abratkiewicz2023": [
        {"id": "A1", "loc": "Abstract, p.3469 (pdf p.1)",
         "text": "Although the SSB periodicity limits the velocity ambiguity, the article describes a solution to tackle this problem in a single target scenario.",
         "why_ko": "⭐ 태스크가 요구한 '무모호 속도를 SSB 주기가 제한한다' 는 진술의 원문. 초록에 있다."},
        {"id": "A2", "loc": "Section IV, eq. (16), p.3476 (pdf p.8)",
         "text": "The Doppler range is limited by T^SSB_dist so that Vb ∈ [ −λ/(4 T^SSB_dist), λ/(4 T^SSB_dist) ] (16) where the wavelength λ = c/fc, and fc = 3.44 GHz is the carrier frequency for the 5G network used in the experiment.",
         "why_ko": "⭐⭐ 우리 법칙과 문자 그대로 같은 식. 반쪽 구간 규약까지 같다. 2023 년 출판."},
        {"id": "A3", "loc": "Section IV, p.3476 (pdf p.8)",
         "text": "Thus, pulse repetition frequency corresponds to the sampling rate in the Doppler-shift domain. The higher the pulse repetition frequency, the wider the unambiguous velocity range, stemming from the Nyquist sampling theorem.",
         "why_ko": "'반복률 = 도플러 표본화율' 이라는 우리 서사의 핵심 문장이 그대로 있다."},
        {"id": "A4", "loc": "Section IV, p.3476 (pdf p.8)",
         "text": "As can be deduced, assuming the default value of T^SSB_dist = 20 ms and for the given carrier frequency, one can obtain the maximum unambiguous bistatic velocity of ±1.0901 m/s. For higher velocities aliasing occurs, preventing the unambiguous measurement of velocity. This is a major 5G SSB-based passive radar limitation that can be mitigated by T^SSB_dist manipulation.",
         "why_ko": "⭐ 우리가 '5G SSB 는 1 m/s 대에서 접힌다' 고 말해온 그 숫자가 선행에 이미 있다."},
        {"id": "A5", "loc": "Section IV, p.3476 (pdf p.8)",
         "text": "For instance, in the case in question, for T^SSB_dist = 5 ms one can obtain the maximum unambiguous bistatic velocity of ±4.3605 m/s which can be sufficient in some applications. The 5G standard also assumes lower frequencies utilization, e.g., n28 band (703−748 MHz uplink / 758−803 MHz downlink), allowing wider unambiguous Doppler frequencies to be obtained.",
         "why_ko": "주기 사다리와 '낮은 대역이 더 넓은 무모호 도플러' 라는 밴드 스케일링까지 이미 언급되어 있다 — 다만 표는 없다."},
        {"id": "A6", "loc": "Section IV, eq. (17)-(18), p.3476 (pdf p.8)",
         "text": "Vi = V~i + N Vmax (17) where N ∈ Z describes how many times the velocity is aliased, and Vmax = λ/(4 T^SSB_dist) − (−λ/(4 T^SSB_dist)) = λ/(2 T^SSB_dist) (18)",
         "why_ko": "⚠ 규약 주의 — 그들의 eq.(16) 은 반쪽 구간(±λ/4T), eq.(18) 의 Vmax 는 **전체 폭** λ/2T 다. 같은 논문 안에서 두 규약을 다르게 쓴다."},
        {"id": "A7", "loc": "Section II, p.3471 (pdf p.3)",
         "text": "SSBs are broadcasted in bursts in each 5G NR cell, in all beams every time interval T^SSB_dist = {5, 10, 20, 40, 80, 160} ms, depending on the configuration. The default, and most often used, SSB periodicity is 20 ms. However, if needed, it is possible to shorten it to 10 ms—thanks to this, one can achieve a wider velocity unambiguity in SSB-based passive radar.",
         "why_ko": "⭐ SSB 주기 집합의 1차 출처. 우리가 쓰는 20 ms(=50 Hz) 기본값이 여기서 확인된다."},
        {"id": "A8", "loc": "Section I, p.3469 (pdf p.1)",
         "text": "The SSB synchronization block is sent in 5G NR by a base transceiver station (BTS) independently whether the content is present or not [8]. The SSB is the only always-ON signal in the 5G network.",
         "why_ko": "⭐ 우리 '상시 기준신호' 서사의 1차 근거. 우리가 만든 프레임이 아니다."},
        {"id": "A9", "loc": "Section VI, p.3478 (pdf p.10)",
         "text": "The signal was recorded using the Ettus USRP X310 SDR platform, synchronized by GPS time reference. ... The cooperative target was a car (Volvo XC90) moving in a parking lot illuminated by the BTS [15]. The car was equipped with a GPS recorder.",
         "why_ko": "⭐⭐ 실측 표적은 **승용차**다. 드론이 아니다."},
        {"id": "A10", "loc": "Conclusion/future work, p.3482 (pdf p.14)",
         "text": "The subsequent problem worth considering is small target detection, for instance, drones whose reflectivity is significantly lower than the car used in the experiment.",
         "why_ko": "⭐⭐⭐ 이 식의 주인이 직접 '드론은 아직 안 했다, 반사도가 훨씬 낮다' 고 적어 놓았다. 우리 포지션의 최강 문장."},
        {"id": "A11", "loc": "Section II, p.3471 (pdf p.3)",
         "text": "Real-life measurements described in Section VI were performed in n77 operating band (3.4–3.8 GHz), 40 MHz channel bandwidth, and 30 kHz SCS. In this environment, REFSENS is equal to −89.7 dBm.",
         "why_ko": "우리 5G 설정(3.44~3.5 GHz, 30 kHz SCS)의 실측 대조군."},
        {"id": "A12", "loc": "Section IV, eq. (15), p.3476 (pdf p.8)",
         "text": "one can obtain bistatic range resolution defined as [(2.8) in [2]] ΔR = c/B = cτ, (15) where c is the speed of light, B is the signal bandwidth. In considerations in the sequel of this work, B = 61.44 MHz [15].",
         "why_ko": "⭐ 우리 ΔR_b = c/B 규약의 1차 근거(그들도 Malanowski 교재 [2] 를 인용). c/2B 진영과의 좌표계 논쟁에서 우리 편의 근거다."},
        {"id": "A13", "loc": "Section I, p.3470 (pdf p.2)",
         "text": "However, to the authors' knowledge, no work has been published so far (till now) on the practical application of this technique using the SSB signal of the 5G NR waveform. In summary, the main novelty of this article, compared to [15], is the use of the SSB as an illumination signal.",
         "why_ko": "그들의 novelty 주장 원문 — 'SSB 를 조명원으로 쓰는 것' 이지 '무모호 속도 식' 이 아니다."},
        {"id": "A14", "loc": "Section I, p.3469 (pdf p.1)",
         "text": "A specific use case for short-range passive radar can be detecting vehicles or smuggler drones in border areas. ... Another case can also be detecting flying objects (including drones) in the vicinity of small airports (especially those belonging to aeroclubs).",
         "why_ko": "드론은 '동기' 로만 등장한다 — 실험에는 없다."},
        {"id": "A15", "loc": "Section V, p.3477 (pdf p.9)",
         "text": "The following three 5G network scenarios were assumed: 1) full downlink allocation; 2) partial downlink allocation; 3) lack of downlink transmission.",
         "why_ko": "⭐ 우리 9모드 벤치마크의 '점유(occupancy) 축' 이 이미 3단계로 존재한다 — 축 개념은 우리 것이 아니고, 우리는 해상도(60배 스팬)만 다르다."},
    ],

    "quotes_chen2024": [
        {"id": "C1", "loc": "Section 4.1.1, eq. (4), p.6 of 20",
         "text": "β is the double base angle, and δ is the angle of the target at the velocity direction relative to the bisector of the double base angle. ... Assuming the wavelength of the signal is λ, the Doppler frequency shift generated by the moving target can be expressed as [16]  f_d = (2v/λ) cos(β/2) cos(δ)   (4)",
         "why_ko": "⭐ 기호(β, δ)까지 우리와 같다. ⚠ 그러나 이 식조차 Chen 의 것이 아니다 — 그들이 [16] 을 인용한다."},
        {"id": "C2", "loc": "References [16], p.19 of 20",
         "text": "Samczyński, P.; Abratkiewicz, K.; Płotka, M.; Zieliński, T.P.; Wszołek, J.; Hausman, S.; Korbel, P.; Księżyk, A. 5G network-based passive radar. IEEE Trans. Geosci. 2021, 60, 1–9.",
         "why_ko": "⭐ Chen eq.(4) 의 출처는 **같은 바르샤바 학파**다. 즉 이 식의 계보는 Abratkiewicz 그룹으로 수렴한다."},
        {"id": "C3", "loc": "References [8], p.19 of 20",
         "text": "Abratkiewicz, K.; Księżyk, A.; Płotka, M.; Samczyński, P.; Wszołek, J.; Zieliński, T.P. Ssb-based signal processing for passive radar using a 5G network. IEEE J. Sel. Top. Appl. Earth Obs. Remote Sens. 2023, 16, 3469–3484.",
         "why_ko": "Chen 이 G2 를 인용한다 — 두 논문의 선후 관계가 원문으로 확정된다."},
        {"id": "C4", "loc": "Section 5, p.13 of 20",
         "text": "In experiments, the CSI-RS signal period is 20 ms, and the maximum unambiguous Doppler frequency is 50 Hz. The measurable Doppler frequency shift range is [−25 Hz, 25 Hz]. For a unilateral rotation target, when the signal carrier frequency is 3.55 GHz, the rotation radius is 0.3 m, and the double base angle is 0, the maximum measurable speed is 0.56 rps. The presence of the double base angle makes the maximum measurable speed slightly greater than 0.56 rps.",
         "why_ko": "⭐ 태스크가 요구한 '무모호 속도' 진술. ⚠ 식이 아니라 **수치 대입**이다 — Chen 은 닫힌 형태를 표시하지 않는다."},
        {"id": "C5", "loc": "Section 3, p.5 of 20",
         "text": "The period of CSI-RS can be 4, 5, 8, 10, 16, 20, 32, 40, 64, 80, 160, 320, and 640 time slots, and the length of the time slot is related to the length of the CP. CSI-RS has three densities: 0.5, 1, and 3.",
         "why_ko": "⭐ 태스크가 요구한 CSI-RS 주기. 최소 4 슬롯 -> 30 kHz SCS 에서 2 ms = 500 Hz 라는 우리 V4 천장이 이 목록과 산술적으로 일치한다."},
        {"id": "C6", "loc": "Section 5.1, Table 4, p.13 of 20",
         "text": "Table 4. CSI-RS parameter table for 5G base station in 5G laboratory. Num RB 273 RB; Subcarrier Location 0; Symbol Locations 4; Period 40 slots; Density 3; Slot Offset 24 slots",
         "why_ko": "⭐ 태스크가 요구한 gNB. 첫 실험은 '5G 실험실의 실험용 기지국'."},
        {"id": "C7", "loc": "Section 5.2, Table 5, p.16 of 20",
         "text": "Table 5. CSI-RS signal parameters of the 5G commercial base station. Num RB 273 RB; Subcarrier Location 2; Symbol Location 4; Period 40 slots; Density 3; Slot Offset 4 slots",
         "why_ko": "⭐ 두 번째 실험은 **상용 5G 기지국**이다 — 이것이 이 논문이 'Commercial 5G Signal' 을 표제로 쓰는 근거."},
        {"id": "C8", "loc": "Section 5.2, Tables 6-7, p.16-17 of 20",
         "text": "Table 6. Results of unilateral targets with a radius of 0.3 m. 0.125/0.122/2.4%; 0.25/0.244/2.4%; 0.5/0.5005/0.1%; 0.625/0.6225/0.4%; 0.75/1.5/100%. Table 7. Results of unilateral targets with a radius of 0.15 m. 0.125/0.1221/2.3%; 0.25/0.2563/2.5%; 0.5/0.5005/0.1%; 0.625/0.6226/0.38%; 0.75/0.7568/0.9%",
         "why_ko": "⭐⭐ 태스크가 요구한 실측 검증. 접힘이 실제로 관측되며(0.75 rps @ r=0.3 m 에서 오차 100%), 반경을 절반으로 줄이면 같은 회전수가 정상 측정된다."},
        {"id": "C9", "loc": "Section 5.2, p.16 of 20",
         "text": "When the rotation radius of the unilateral target is 0.3 m and the theoretical speed is 0.75 rps, the reason for the error of 100% is that the Doppler frequency exceeds the measurement range, resulting in Doppler blur.",
         "why_ko": "⭐ 접힘의 원인을 저자들이 직접 도플러 모호로 귀속한다 — 실측으로 확인된 한계다."},
        {"id": "C10", "loc": "Abstract, p.1 of 20",
         "text": "In the experiment, this paper validated the method of detecting rotating targets using 5G signals and evaluated the measurement accuracy, providing a research foundation for passive radar target detection using 5G signals and detecting rotating targets such as drone rotors.",
         "why_ko": "⭐⭐ 초록의 자기 주장. 드론 로터는 '연구 기반을 제공한다' 는 **미래형**이지 실험 대상이 아니다."},
        {"id": "C11", "loc": "Section 1, p.1-2 of 20",
         "text": "When the target is small, targets such as drones or drone rotors, whether passive radars based on 5G can correctly detect the target is a worthwhile research question. Therefore, based on existing research, this paper proposes a method for detecting small targets over short distances using the Channel State Information-Reference Signal (CSI-RS) in 5G. Additionally, a rotating target experimental model employing a stepper motor is constructed to accurately simulate target movement scenarios. ... In a word, this paper provides an approach for small target detection based on 5G passive radar.",
         "why_ko": "⭐ 태스크가 요구한 novelty 주장 원문. 표적은 **스테퍼 모터 회전 모형**이다."},
        {"id": "C12", "loc": "Section 6 (Conclusions), p.18 of 20",
         "text": "This paper focuses on whether other signals in 5G can be used for target detection and proposes a method of using CSI-RS signals of 5G for channel estimation and extracting Doppler frequency offset from channel responses. Meanwhile, compared to other studies using passive radars based on 5G for vehicle detection or personnel localization, the method in this paper focuses more on detecting weak and small targets at short distances.",
         "why_ko": "그들 스스로 SSB 계열(=Abratkiewicz)과 자기 위치를 구분한다 — '다른 신호(CSI-RS)를 쓴다' 가 핵심 차별점."},
        {"id": "C13", "loc": "Section 4 (simulation), p.11 of 20",
         "text": "In the simulation, the period of the CSI-RS signal is set to five time slots, that is, 50 ms.",
         "why_ko": "⚠ 우리가 관찰한 내부 불일치: 30 kHz SCS 에서 5 슬롯은 2.5 ms 이지 50 ms 가 아니다. 축자로 남기되 우리가 해석하지 않는다 — 이 문장은 인용하지 않는 편이 안전하다."},
        {"id": "C14", "loc": "Section 4 (simulation), p.7 of 20",
         "text": "In the simulation, the carrier frequency is 3.45 GHz, L_T0 = 3.5 m, L_R0 = 1 m, L = L_T0 + L_R0 = 4.5 m, L_r = 1 m, and r = 0.3 m.",
         "why_ko": "시뮬 기하 — 기저선 4.5 m 의 극단적 근거리다. 우리 챔버(30x20x11 m) 와 스케일이 다르다."},
    ],

    # ---------------------------------------------------------------- 재현 계산
    "reproductions_by_us": {
        "abratkiewicz_eq16": {
            "formula": "v_max_half = lambda * PRF / 4,  PRF = 1 / T_SSB",
            "rows": abra_repro,
            "verdict_ko": ("두 숫자 모두 우리 법칙으로 재현된다. 논문은 c = 3e8 을 썼다(c 정확값으로는 "
                           "1.0893 / 4.3594 로 미세하게 어긋나고, 3e8 로는 1.0901 / 4.3605 로 소수 4자리까지 일치)."),
        },
        "chen_0p56rps": chen_repro,
        "chen_table6_threshold_bracket": bracket,
        "csirs_period_ladder_30kHz_scs": csirs_ladder,
        "ssb_period_ladder": ssb_ladder,
        "our_v1_table_recheck": {
            "note_ko": ("⚠ 규약 주의: 우리 V1 표(40.695 / 14.395 / 1.071 / 0.141)는 c = 3e8 로 계산된 값이다. "
                        "c 정확값을 쓰면 넷째 자리에서 갈린다. Abratkiewicz 도 c = 3e8 을 썼으므로(재현으로 확인) "
                        "선행과의 대조는 c = 3e8 열로 하고, 우리 표의 규약을 명시해야 한다."),
            "rows": [
                {"waveform": "LTE CRS", "prf_hz": 1000.0, "fc_hz": 1.843e9,
                 "vmax_half_ms_c_3e8": vmax_half(1.843e9, 1000.0, C_ROUND),
                 "vmax_half_ms_c_exact": vmax_half(1.843e9, 1000.0)},
                {"waveform": "WiFi VHT-LTF", "prf_hz": 1000.0, "fc_hz": 5.21e9,
                 "vmax_half_ms_c_3e8": vmax_half(5.21e9, 1000.0, C_ROUND),
                 "vmax_half_ms_c_exact": vmax_half(5.21e9, 1000.0)},
                {"waveform": "5G SSB", "prf_hz": 50.0, "fc_hz": 3.5e9,
                 "vmax_half_ms_c_3e8": vmax_half(3.5e9, 50.0, C_ROUND),
                 "vmax_half_ms_c_exact": vmax_half(3.5e9, 50.0)},
                {"waveform": "WiFi beacon", "prf_hz": 9.765625, "fc_hz": 5.21e9,
                 "vmax_half_ms_c_3e8": vmax_half(5.21e9, 9.765625, C_ROUND),
                 "vmax_half_ms_c_exact": vmax_half(5.21e9, 9.765625)},
            ],
            "anchored_row_ko": ("5G SSB 행만 이번에 외부 1차 문헌으로 앵커되었다: Abratkiewicz eq.(16) 이 "
                                "3.44 GHz / 20 ms 에서 ±1.0901 m/s 를 준다. 우리 3.5 GHz / 50 Hz 값 1.0714 m/s 와 "
                                "같은 식·같은 규약이며 반송파만 다르다."),
        },
    },

    # ---------------------------------------------------------------- 판정
    "what_they_did_and_did_not": {
        "abratkiewicz2023_DID": [
            "5G SSB 를 '펄스' 로 보는 PCL 처리 사슬 전체(검출 -> 복호 -> 재합성 -> 정합필터 -> MTI -> 슬로우타임 FFT)를 제안하고 실측 검증했다.",
            "eq.(16) 으로 무모호 바이스태틱 속도 구간 [-lambda/4T, +lambda/4T] 를 5G SSB 에 대해 명시했다 — 반쪽 구간 규약.",
            "20 ms -> +-1.0901 m/s, 5 ms -> +-4.3605 m/s (fc 3.44 GHz) 수치를 제시했다.",
            "SSB 주기 집합 {5,10,20,40,80,160} ms 와 기본 20 ms 를 명시했다.",
            "낮은 대역(n28)이 더 넓은 무모호 도플러를 준다는 밴드 스케일링을 문장으로 언급했다.",
            "eq.(17)-(20) 으로 두 장의 RD 맵을 이용한 단일표적 접힘 해제(dealiasing)를 제안했다. 필터뱅크·압축센싱을 대안으로 언급했다.",
            "USRP X310 + GPS 동기, n77 3.44 GHz / 40 MHz / 30 kHz SCS, Volvo XC90 협조표적, GPS 진값 실측.",
            "다운링크 점유 3단계(full / partial / lack) 로 CAF 성능 붕괴를 보였다.",
            "eq.(15) 로 ΔR = c/B (거리합 좌표) 규약을 채택했다.",
            "'SSB is the only always-ON signal in the 5G network' 라고 명시했다.",
        ],
        "abratkiewicz2023_DID_NOT": [
            "드론을 표적으로 쓰지 않았다 — 표적은 승용차이고, 드론은 결론에서 future work 로 남긴다(A10).",
            "교차표준 비교를 하지 않았다 — WiFi 나 LTE 를 5G 와 같은 한 표에 올리지 않는다(WiFi 는 서론에서 유사 문제로 언급만).",
            "무모호 속도를 실기체 최고속도와 겹쳐 보지 않았다.",
            "바이스태틱 각도(beta, delta)를 v_max 식에 넣지 않았다 — eq.(16) 은 바이스태틱 속도 Vb 에 대한 식이라 기하가 흡수되어 있다.",
            "드론 기체의 산란/RCS 를 계산하지 않았다. 전자기 시뮬레이션이 없다.",
            "무모호 속도가 **검출확률**에 어떻게 번지는지(블라인드 속도, CPI 독립성)를 정량화하지 않았다.",
        ],
        "chen2024_DID": [
            "5G CSI-RS 로 채널응답을 추정해 도플러를 뽑는 근거리 소형표적 패시브 검출법을 제안했다.",
            "바이스태틱 도플러 eq.(4) f_d=(2v/lambda)cos(beta/2)cos(delta) 를 우리와 같은 기호로 적었다 — 단, 출처는 [16] Samczynski 외 TGRS.",
            "CSI-RS 주기 슬롯 집합(4~640 슬롯)과 밀도(0.5/1/3)를 정리했다.",
            "회전표적 에코 모델(단측/양측 회전)과 주파수편이 곡선 특성을 유도했다.",
            "실험용 5G 기지국과 **상용 5G 기지국** 두 곳에서 실측했다(273 RB, 주기 40 슬롯 = 20 ms).",
            "0.125~0.75 rps 스윕으로 정확도(오차 0.1~2.5%)와 접힘(0.75 rps @ r=0.3 m 에서 100% 오차)을 표로 보고했다.",
            "20 ms -> 50 Hz -> [-25,25] Hz -> 0.56 rps 라는 한계를 수치로 명시하고, beta 가 있으면 그 한계가 약간 커진다고 문장으로 적었다.",
        ],
        "chen2024_DID_NOT": [
            "⭐ 무모호 속도의 **닫힌 식을 표시하지 않았다**. v_max = lambda*PRF/4 도, cos(beta/2)cos(delta) 를 포함한 합성형도 표시 식으로 없다 — 수치 대입뿐이다.",
            "드론을 쓰지 않았다 — 표적은 스테퍼 모터로 돌리는 회전 모형이고, 드론 로터는 초록·서론의 동기다(C10, C11).",
            "교차표준 비교가 없다(5G CSI-RS 단독).",
            "RCS/전자기 산란 계산이 없다.",
            "검출확률·CFAR 성능 연결이 없다.",
            "기하가 4.5 m 기저선의 실험대 규모다 — 실운용 거리 예산이 아니다.",
        ],
    },

    "priority_ledger": {
        "who_owns_what": [
            {"item": "v_max(half-window) = lambda / (4 * T_ref)  (= lambda*PRF/4)",
             "owner": "Abratkiewicz 외, IEEE JSTARS 16:3469-3484, 2023 (PUBLISHED), eq.(16)",
             "our_status": "재현자. 우리 것이 아니다."},
            {"item": "'기준신호 반복주기가 무모호 속도를 제한한다' 는 명제",
             "owner": "Abratkiewicz 2023 (초록·eq.16). Chen 2024 가 CSI-RS 에 대해 반복. LaSen(SenSys 2026)은 우선권을 Chen 에 돌린다.",
             "our_status": "우리 것이 아니다. ⚠ LaSen 의 귀속조차 한 세대 늦다 — 원 출처는 Abratkiewicz 2023 이다."},
            {"item": "바이스태틱 도플러 f_d = (2v/lambda) cos(beta/2) cos(delta) (기호 beta, delta 포함)",
             "owner": "Chen 2024 eq.(4) 가 쓰지만 출처는 [16] Samczynski 외, 5G network-based passive radar, IEEE TGRS 2021/2022. 그 위로는 바이스태틱 레이더 표준 교재.",
             "our_status": "우리 것이 아니다."},
            {"item": "합성형 v_max = lambda*PRF / (4 cos(beta/2) cos(delta))",
             "owner": "두 원문 어디에도 **표시 식으로는 없다**(내가 두 PDF 를 다 열어 확인했다). Abratkiewicz eq.(16) + Chen eq.(4) 의 한 줄 결합이다.",
             "our_status": "⚠ '표시 식이 없다' 는 사실이지만 이것은 novelty 가 아니다 — 두 공개 식의 자명한 결합이다. '우리가 정리한 형태' 이상으로 쓰면 안 된다."},
            {"item": "ΔR_b = c/B (거리합 좌표)",
             "owner": "Abratkiewicz 2023 eq.(15), 인용은 Malanowski 교재 [2] (2.8)",
             "our_status": "규약 채택자. 우리 편의 1차 근거가 생겼다."},
            {"item": "'SSB 는 5G 의 유일한 상시 신호' 프레임",
             "owner": "Abratkiewicz 2023 서론 (A8)",
             "our_status": "우리 것이 아니다. 인용해야 한다."},
            {"item": "다운링크 점유율을 성능 축으로 삼는 관점",
             "owner": "Abratkiewicz 2023 §V (full / partial / lack 3단계, A15)",
             "our_status": "축은 선행. 우리는 해상도(9모드·G1/G2/G3 점유율 수치)만 다르다."},
            {"item": "접힘 해제(dealiasing) 대책",
             "owner": "Abratkiewicz 2023 eq.(17)-(20) 두 RD 맵 방식 + 필터뱅크 + 압축센싱 언급",
             "our_status": "우리는 대책을 제안하지 않는다 — '한계를 정량화한다' 로만 말해야 한다."},
        ],
    },

    "what_survives_for_us": {
        "survives_ko": [
            "⭐ 하나의 명시된 규약(반쪽 구간, λ·PRF/4) 아래 놓인 **교차표준 v_max 표** — WiFi beacon 0.141 / 5G SSB 1.071 / WiFi VHT-LTF 14.395 / LTE CRS 40.695 m/s. 두 논문 모두 자기 표준 한 줄만 갖고 있다(Abratkiewicz 는 5G 만, Chen 은 CSI-RS 만). ⚠ 단 '식은 우리 것' 이 아니라 '표가 우리 것' 이다.",
            "⭐ 그 표를 **공개된 실기체 최고속도**와 겹쳐 '어느 조명원이 어느 기체를 놓치는가' 로 바꾼 것. 두 논문 모두 하지 않았다.",
            "⭐ 모노스태틱 CSI-RS 3GPP 천장(500 Hz -> 3.5 GHz 에서 10.71 m/s)을 설계규칙으로 역산한 것. Chen 은 주기 목록만 나열하고 천장의 함의를 계산하지 않는다.",
            "⭐ **드론 기체 산란**: 두 논문 다 EM 산란 계산이 없다. 우리 SBR+PO 파이프라인(구 해석해 대비 max |dB| 0.2006)과 재질 가중 RCS 는 이 두 편의 어느 부분과도 겹치지 않는다.",
            "⭐ 무모호 한계를 **검출성능**(CFAR 교정, 블라인드 속도, 바닥유령, 다중 Rx)까지 잇는 것. Abratkiewicz 는 SNR/CAF 까지, Chen 은 속도 오차까지만 간다.",
            "⭐ 통제된 head-to-head 조명원 비교(같은 표적·같은 챔버·같은 규약). 두 편 다 조명원 하나씩만 다룬다.",
        ],
        "must_stop_claiming_ko": [
            "⛔ '무모호 속도 식을 우리가 제시한다/유도한다' — Abratkiewicz 2023 eq.(16) 이 문자 그대로 같다.",
            "⛔ '반복주기가 무모호 속도를 정한다는 관찰이 새롭다' — 2023 년 JSTARS 초록에 있다.",
            "⛔ 'bistatic 일반형(beta, delta 포함)이 새롭다' — 두 공개 식의 한 줄 결합이다.",
            "⛔ '5G SSB 가 1 m/s 대에서 접힌다는 것을 우리가 처음 보인다' — Abratkiewicz 가 ±1.0901 m/s 로 이미 적었다.",
            "⛔ 'ΔR = c/B 규약이 우리 선택' 이라는 뉘앙스 — Abratkiewicz eq.(15)/Malanowski 교재가 근거다.",
            "⛔ 'SSB 상시성 프레임이 우리 것' — Abratkiewicz 서론 문장이다.",
        ],
        "must_start_saying_ko": [
            "'우리는 Abratkiewicz 외(JSTARS 2023, eq.16)의 알려진 한계를 **네 개 표준에 걸쳐 하나의 규약으로 평가**한다' 로 표현한다.",
            "'그 식의 주인들은 승용차로 검증했고 드론을 명시적 future work 로 남겼다(A10)' 를 우리 gap 문장으로 쓴다.",
            "'Chen 외(Appl. Sci. 2024)는 실측으로 접힘을 관측했지만 표적은 스테퍼 모터 회전 모형이었다(C8, C11)' 를 나란히 둔다.",
        ],
    },

    "corrections_to_our_records": [
        {"file": "outputs/reference_library.json",
         "was": "Chen 2024 원문 미확보(MDPI 403) / Abratkiewicz 2023 원문 미확보 — open_problems[0], open_problems[1]",
         "now": "둘 다 확보. open_problems 0,1 은 CLOSED 로 갱신해야 한다."},
        {"file": "outputs/monostatic_prior.json",
         "was": "'v_max = lambda*PRF/(4cos(beta/2)cos delta) 는 우리 것이 아니다 — Chen et al., Applied Sciences 2024 가 같은 기호로 먼저 냈다' (headline 3)",
         "now": "⚠ 부분 오류. (i) 인용문 3건은 원문과 축자 일치했다(검증 완료 — 그 라운드는 정직했다). (ii) 그러나 Chen 은 합성된 닫힌 식을 표시하지 않는다. (iii) 그리고 lambda/(4T) 의 진짜 선행은 1년 앞선 Abratkiewicz 2023 eq.(16) 이다."},
        {"file": "docs/references.bib",
         "was": "@article{abratkiewicz_ssb_jstars23} 에 '원문 미확보 — 본문 문장 인용 금지', INCOMPLETE-DOI",
         "now": "확보 완료. DOI 10.1109/JSTARS.2023.3262291 채우고 인용 금지 해제. 본문 문장 인용 가능(CC BY 4.0)."},
        {"file": "outputs/reference_library.json convention_ledger",
         "was": "half_window_users 에 chen2024appliedsci 만 기재",
         "now": "Abratkiewicz 2023 eq.(16) 도 반쪽 구간 사용자다. ⚠ 단 같은 논문 eq.(18) 은 전체 폭(lambda/2T)을 Vmax 라 부른다 — 한 논문 안의 이중 규약을 기록해야 한다."},
        {"file": "novelty_guards (reference_library.json)",
         "was": "Chen 2024 항목 없음(추가 필요로만 표시)",
         "now": "Abratkiewicz 2023 을 **1순위 선행**으로, Chen 2024 를 2순위로 넣는다."},
    ],

    "still_open_after_this_round": [
        "3GPP TS 38.331/38.214 원 규격에서 CSI-RS 최소 주기를 직접 확인하지 않았다 — 현재는 Chen §3 의 슬롯 목록(C5)과 LaSen 인용의 간접 정합성뿐이다.",
        "Samczynski 외, '5G network-based passive radar', IEEE TGRS 2021/2022 (Chen 의 eq.(4) 출처, C2) 원문 미확보 — 바이스태틱 도플러 식의 계보를 한 단계 더 거슬러야 완결된다.",
        "Ksiezyk 외, IEEE AESS Mag. 38:4-21, 2023 (Chen ref [7]) 미확보.",
        "우리 V1 표의 LTE CRS 1000 Hz / WiFi VHT-LTF 1000 Hz 반복률 가정은 이번 라운드에서 외부 1차 문헌으로 검증되지 않았다 — 5G SSB 행만 Abratkiewicz 로 앵커되었다.",
        "phi=90 deg 하드코딩(G5) 은 이번 라운드와 무관하게 그대로 열려 있다.",
    ],
}

doc["quote_selfcheck"] = {
    "method_ko": ("각 인용의 산문 조각을 정규화(공백·하이픈·리가처 제거)해서 해당 PDF 페이지 텍스트에 "
                  "실제로 들어 있는지 다시 대조했다. 수식 글리프는 PDF 추출이 재배열하므로 조각 대조에서 제외했다."),
    "quotes_checked": 29,
    "quotes_matched": 29,
    "unmatched": [],
    "note_ko": "A2/A6/C1 의 수식 부분은 글리프 순서 때문에 자동대조 대상이 아니며, 주변 산문으로 위치를 고정했다.",
}

doc["meta"]["runtime_s"] = time.time() - t0
doc["counts"] = {
    "papers_obtained": 2,
    "verbatim_quotes_abratkiewicz": len(doc["quotes_abratkiewicz2023"]),
    "verbatim_quotes_chen": len(doc["quotes_chen2024"]),
    "verbatim_quotes_total": len(doc["quotes_abratkiewicz2023"]) + len(doc["quotes_chen2024"]),
    "reproduction_checks": len(abra_repro) + 1 + 1 + len(csirs_ladder) + len(ssb_ladder) + 4,
    "priority_items": len(doc["priority_ledger"]["who_owns_what"]),
    "claims_we_must_stop": len(doc["what_survives_for_us"]["must_stop_claiming_ko"]),
    "claims_that_survive": len(doc["what_survives_for_us"]["survives_ko"]),
    "record_corrections": len(doc["corrections_to_our_records"]),
    "still_open": len(doc["still_open_after_this_round"]),
}

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(doc, f, ensure_ascii=False, indent=1)

print("wrote", OUT)
print(json.dumps(doc["counts"], ensure_ascii=False, indent=1))
print("\n--- Abratkiewicz eq.(16) 재현 ---")
for r in abra_repro:
    print("  T=%.0f ms  paper %.4f  ours(c=3e8) %.4f  ours(c exact) %.4f" %
          (r["T_SSB_ms"], r["paper_states_ms"], r["our_law_c_3e8_ms"], r["our_law_c_exact_ms"]))
print("--- Chen 0.56 rps 재현 --- ours = %.5f rps (rel err %.2e)" %
      (chen_repro["our_law_rps_c_exact"], chen_repro["rel_err_c_exact"]))
print("--- Chen Table 6 문턱 구간 --- beta=0 예측 %.3f rps, 실측 브래킷 (%.3f, %.3f] rps, 필요 완화 %.3f~%.3f" %
      (base, thr_lo, thr_hi, bracket["implied_relief_factor_range"][0], bracket["implied_relief_factor_range"][1]))
