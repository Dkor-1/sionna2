# -*- coding: utf-8 -*-
"""mono_vs_passive.py — **패시브 대 모노스태틱 경계**를 숫자로 긋는다
====================================================================================================

■ 이 스크립트가 확정하는 것

  ① 모노스태틱은 우리 법칙의 **예외가 아니라 β=0 절편**이다.
        v_max(β, δ) = λ·PRF_ref / (4 cos(β/2) cos δ)        [바이스태틱 일반형]
        v_max       = λ·PRF_ref / (4 cos δ)                  [β=0 — 모노스태틱]
        v_max       = λ·PRF_ref / 4                          [β=0, δ=0 — 공통 하한]
     ⭐ 그래서 우리가 발표한 1.07 m/s 는 **모노스태틱 값이자 동시에 바이스태틱 최악값**이다.
        헤드라인은 기하로 부풀린 수가 아니라 기하로 깎은 수다 — 보수적이다.
     이 절편 동일성은 주장이 아니라 **저장소 함수로 재현**한다(§1: TX=RX 로 놓고 fs_params 호출).

  ② 설계자유도 축 — 모노스태틱은 반복률을 얼마나 자유롭게 고르는가.
     ⚠ 프레이밍을 그대로 믿지 않고 시험한다. 결과는 "자유롭다"가 아니라 **"10배만큼, 13단계로,
        천장이 있는 자유"** 다. 그리고 그 천장(3GPP sub-6 CSI-RS 500 Hz)조차 3.5 GHz 에서
        10.71 m/s 이라 **공개된 어떤 기체 최고속도도 못 덮는다**.

  ③ 양방향 비용원장 — 모노스태틱이 사는 것과 무는 것, 패시브의 거울상.
     자기간섭은 인용만 하지 않고 **저장소 링크버짓 + 저장소 σ** 로 직접 계산한다(§3).

  ④ 리뷰어가 필요로 하는 한 장 — v_max 대 PRF_ref, 패시브는 **고정점**(우리가 못 옮긴다),
     모노스태틱은 **구간**(설계 선택), 실기체 속도를 겹친다.

■ 계산하지 않고 **저장소 함수를 부른다**(재구현 금지)
    freespace_scene.fs_params / target_pos / heading_velocity / look_el_deg / nyquist_gate
    freespace_scene.M_from_prf / doppler_bin_hz / C0
    link_budget.LinkBudget / link_terms / lin2db          (자기간섭·직접파 예산의 단일 출처)
    drones.DRONES                                          (기체 최고속도의 단일 출처)
  숫자는 전부 outputs/*.json 또는 저장소 상수에서 읽는다. 손으로 적은 수는 없다.

■ 입력(읽기 전용)
    outputs/refrate_law.json          법칙·조명원표·설계규칙(패리티 대조 대상)
    outputs/vmax_hardening.json       X1~X6 정정(완화계수 장면통계 포함)
    outputs/monostatic_prior.json     LaSen/Chen/Barneto 원문 인용과 서지(이번 라운드 선행조사)
    outputs/report13_sigma_grid.mavic4pro.json   σ(3.5 GHz) — 자기간섭 예산의 표적 단면적

■ 산출
    outputs/mono_vs_passive.json
    outputs/figures/mono_vs_passive_f{1,2}_*.{png,pdf}     (그림 텍스트 전부 영어)

⚠ 이 스크립트는 refrate_law.py / refrate_law.json 을 **건드리지 않는다**. 두 파일 모두 다른
  워크플로가 지금 작업 중인 미추적 파일이다. 대신 §5 가 적용 가능한 **패치를 JSON 에 적어** 넘긴다.

실행:  cd sionna2 && PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/mono_vs_passive.py
       빠른 확인:  --smoke   (그림 생략)
"""
from __future__ import annotations

import argparse
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

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "4")

import numpy as np                                          # noqa: E402

import freespace_scene as fss                               # noqa: E402
import drones as drn                                        # noqa: E402
from link_budget import LinkBudget, link_terms, lin2db      # noqa: E402

C0 = fss.C0
OUT_JSON = os.path.join(_ROOT, "outputs", "mono_vs_passive.json")
OUT_FIG = os.path.join(_ROOT, "outputs", "figures")

IN_REFRATE = os.path.join(_ROOT, "outputs", "refrate_law.json")
IN_HARDEN = os.path.join(_ROOT, "outputs", "vmax_hardening.json")
IN_PRIOR = os.path.join(_ROOT, "outputs", "monostatic_prior.json")
IN_SIGMA = os.path.join(_ROOT, "outputs", "report13_sigma_grid.mavic4pro.json")

FC_N78 = 3.5e9                      # 같은 반송파에서 비교한다 — 경계의 공정성 조건
LAM_N78 = C0 / FC_N78


def _load(path, what):
    """입력 JSON 을 읽는다. 없으면 **실패로 멈춘다** — 손으로 적은 수로 때우지 않는다."""
    if not os.path.exists(path):
        raise SystemExit(f"[mono_vs_passive] 필수 입력이 없다: {path} ({what})")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# =========================================================================== #
#  §0  출처 원장 — 이 파일이 인용하는 모든 외부 문장
#      verification 등급:
#        pdf_quote     로컬 아카이브 PDF 에서 이번 실행자가 직접 확인한 문장
#        recorded      outputs/monostatic_prior.json 이 원문 대조로 기록해 둔 문장(재확인 안 함)
#        spec_derived  규격 수치들로부터의 산술(식을 함께 적는다)
#        repo          저장소 상수/함수 출력
#        second_hand   원문 미확보 — 제3자 요약. 결론을 여기에 걸지 않는다
# =========================================================================== #
SRC = {
    "csirs_ceiling_500hz": dict(
        doc="LaSen, Proc. ACM/IEEE SenSys '26, Saint Malo, France, May 11-14 2026, "
            "ACM pp. 732-745, DOI 10.1145/3774906.3800504 (published), §1, citing 3GPP TS 38.331",
        quote="The maximum configurable repetition frequency for Sub-6 GHz Channel State "
              "Information Reference Signals (CSI-RS) is 500 Hz [3], falling short of the Nyquist "
              "sampling requirements for resolving high-speed targets like drones.",
        verification="pdf_quote",
        pdf="/data/public/jeong/papers/5G/26_LaSen.pdf"),
    "csirs_multiset": dict(
        doc="LaSen (SenSys '26, published), §3.1.1",
        quote="To enhance temporal density, the gNB can configure multiple Non-Zero Power (NZP) "
              "CSI-RS resource sets with time offsets. As illustrated in Figure 3(a), which shows "
              "two sets of periodic CSI-RS with a period of 100 Hz and a 5 ms offset, achieving a "
              "maximum sampling rate of 200 Hz.",
        verification="pdf_quote",
        pdf="/data/public/jeong/papers/5G/26_LaSen.pdf"),
    "nr_numerology": dict(
        doc="LaSen (SenSys '26, published), §2.1",
        quote="a 30 kHz SCS configuration yields 0.5 ms slots and 14 OFDM symbols",
        verification="pdf_quote",
        pdf="/data/public/jeong/papers/5G/26_LaSen.pdf"),
    "lasen_traffic": dict(
        doc="LaSen (SenSys '26, published), §4.2.1 / §7",
        quote="our measurements reveal that, for a given gNB, less than 5% of total time duration "
              "exhibits a resource-utilization density above 7.1% (Figure 5(b))",
        verification="recorded",
        where="outputs/monostatic_prior.json : lasen.traffic_statistics_measured.quote_2"),
    "lasen_si": dict(
        doc="LaSen (SenSys '26, published), §5 Implementation / §8 Discussion",
        quote="a conductive shielding plate between the transmitter and receiver antennas to "
              "mitigate near-field coupling, and a static background removal algorithm to suppress "
              "residual self-interference ... practical deployments would benefit from advanced "
              "active cancellation techniques ... which can achieve >50 dB suppression in "
              "full-duplex OFDM systems",
        verification="pdf_quote",
        pdf="/data/public/jeong/papers/5G/26_LaSen.pdf"),
    "barneto_si": dict(
        doc="C. B. Barneto, T. Riihonen, M. Turunen, L. Anttila, M. Fleischer, K. Stadius, "
            "J. Ryynanen, M. Valkama, 'Full-Duplex OFDM Radar With LTE and 5G NR Waveforms: "
            "Challenges, Solutions, and Measurements', IEEE Trans. Microwave Theory Techn., "
            "vol. 67, no. 10, pp. 4042-4054, Oct. 2019 (published)",
        quote="more than 100 dB of total SI suppression is required, which calls for multiple "
              "complementary methods as no single technique can facilitate such high isolation",
        verification="recorded",
        where="outputs/monostatic_prior.json : monostatic_literature[barneto2019]"),
    "barneto_counter": dict(
        doc="Barneto et al., IEEE TMTT 67(10):4042-4054, 2019 (published)",
        quote="from the OFDM radar processing perspective, limited TX-RX isolation is primarily a "
              "concern in detection of static targets while moving targets are inherently more "
              "robust to transmitter self-interference",
        verification="recorded",
        where="outputs/monostatic_prior.json : monostatic_literature[barneto2019].quotes[4]",
        why_here="⭐ 우리에게 **불리한** 인용이다. 100 dB 를 드론 검출의 관문처럼 쓰면 과장이므로 "
                 "원장에서 이 문장을 함께 짊어진다."),
    "chen_formula": dict(
        doc="P. Chen, L. Tian, Y. Bai, J. Wang, 'Rotating Target Detection Using Commercial 5G "
            "Signal', Applied Sciences (MDPI), vol. 14, no. 10, art. 4282, 2024, "
            "DOI 10.3390/app14104282 (published, open access), Eq. (4) and §5",
        quote="In experiments, the CSI-RS signal period is 20 ms, and the maximum unambiguous "
              "Doppler frequency is 50 Hz. The measurable Doppler frequency shift range is "
              "[-25 Hz, 25 Hz].",
        verification="recorded",
        where="outputs/monostatic_prior.json : priority_check.hits[0]",
        why_here="⭐ 우선권. 우리 식과 기호가 같은 선행이다 — 이 파일의 어떤 문장도 '우리가 처음'을 "
                 "주장하지 않는다."),
    "golzadeh_ssb": dict(
        doc="M. Golzadeh, E. Tiirola, L. Anttila, J. Talvitie, K. Hooli, O. Tervo, I. Peruga, "
            "S. Hakola, M. Valkama, 'Downlink Sensing in 5G-Advanced and 6G: SIB1-assisted SSB "
            "Approach', Proc. IEEE VTC2023-Spring, Florence, June 2023, "
            "DOI 10.1109/VTC2023-Spring57618.2023.10200933 (published)",
        quote="using only the SSB has challenges related to radar ambiguity while being also "
              "limited in both distance and velocity resolution",
        verification="recorded",
        where="outputs/monostatic_prior.json : monostatic_literature[golzadeh2023] (abstract only; "
              "본문 미확보 — 본문 문장으로 인용 금지)",
        why_here="⭐ 모노스태틱(망측) 다운링크 센싱도 SSB 반복률 문제에서 자유롭지 않다는 직접 증거."),
    "marchese_nfb": dict(
        doc="M. Marchese, M. F. Keskin, P. Savazzi, H. Wymeersch, 'Monostatic ISAC Without Full "
            "Buffers: Revisiting Spatial Trade-Offs Under Bursty Traffic', arXiv:2601.12963, "
            "19 Jan 2026 (PREPRINT — 게재지 미상, 게재로 인용 금지)",
        quote="In such cases, a data-only ISAC system would simply fall silent, causing sensing to "
              "halt whenever there is no user data to send.",
        verification="recorded",
        where="outputs/monostatic_prior.json : monostatic_literature[marchese2026]"),
    "csirs_slot_set": dict(
        doc="3GPP TS 38.331 CSI-ResourcePeriodicityAndOffset (슬롯 주기 집합). 우리가 가진 근거는 "
            "Chen 2024 §3.3 의 목록(제3자 기록)과, LaSen 이 원문 인용한 500 Hz 천장의 산술 일치뿐이다.",
        derived="30 kHz SCS 에서 슬롯 0.5 ms → 최소 4 슬롯 = 2 ms = 500 Hz. LaSen 이 규격에서 인용한 "
                "sub-6 천장 500 Hz 와 정확히 일치한다 → 4-슬롯 최소값은 산술로 교차확인된다.",
        verification="spec_derived + second_hand",
        caveat="⚠ 집합 {4,5,8,10,16,20,32,40,64,80,160,320,640} 슬롯 자체는 우리가 규격 원문에서 "
               "확인하지 않았다. 사다리의 **양 끝**(500 Hz 천장, 320 ms 바닥)만 결론에 쓰고, "
               "중간 단의 정확한 목록에는 어떤 결론도 걸지 않는다."),
    "ssb_period_set": dict(
        doc="3GPP TS 38.331 ssb-PeriodicityServingCell",
        derived="{5,10,20,40,80,160} ms → {200,100,50,25,12.5,6.25} Hz",
        verification="recorded",
        where="outputs/refrate_law.json : illuminators.rows.nr_ssb.prf_source.configurable"),
    "sharma_dpi": dict(
        doc="Sharma, Gonzalez-Prelcic et al., arXiv:2607.11955 (2026) (PREPRINT)",
        quote="the UAV echo is about 44 to 49 dB weaker than the LOS in the considered geometry",
        verification="recorded",
        where="outputs/monostatic_prior.json : side_by_side.lanes[0].interference_source",
        caveat="⚠ 실외 도심 30~200 m 기하다. 우리 자유공간 장면(L=500 m, R≈1030 m)과 다르므로 "
               "**우리 숫자를 이 값으로 대체하지 않는다** — §3 은 저장소 링크버짓으로 직접 계산한다."),
}

# 3GPP 프레임 구조가 주는 이산 격자 — §2 가 이 두 집합만으로 자유도를 계산한다
SCS_KHZ = 30.0                                  # sub-6 대표 numerology (LaSen §2.1)
SLOT_S = 1e-3 / (SCS_KHZ / 15.0)                # 1 ms / 2^mu = 0.5 ms
SSB_PERIOD_MS = (5.0, 10.0, 20.0, 40.0, 80.0, 160.0)
SSB_DEFAULT_MS = 20.0
CSIRS_SLOTS = (4, 5, 8, 10, 16, 20, 32, 40, 64, 80, 160, 320, 640)


def law_v_max(lam, prf, beta_deg=0.0, delta_deg=0.0):
    """닫힌형 v_max [m/s] = λ·PRF / (4·cos(β/2)·cos δ).  β=δ=0 이면 λ·PRF/4.

    refrate_law.law_v_max 와 **같은 식**이다(그 파일은 다른 워크플로가 작업 중이라 import 하지
    않고 같은 형태를 여기 둔다 — §1 이 저장소 함수 출력과 수치 대조로 정당화한다)."""
    b = math.radians(float(beta_deg))
    d = math.radians(float(delta_deg))
    return float(lam) * float(prf) / max(4.0 * math.cos(b / 2.0) * math.cos(d), 1e-12)


# =========================================================================== #
#  §1  모노스태틱을 **다뤄진 경우**로 올린다 — 각주가 아니라 절편
# =========================================================================== #
def sec1_geometry(refrate, harden, n_psi=3600, seed=11):
    """네 가지를 각각 **저장소 함수로** 확인한다.

    M1 공선(collocation) 항등식 : TX=RX 로 fs_params 를 부르면 β=0·u1=u2 가 되고
                                 f_d 가 (2v/λ)cos δ 로 정확히 떨어지는가
    M2 하한 동일성             : 접힘이 시작되는 속도가 모노/바이스태틱(β→0) 양쪽에서
                                 λ·PRF/4 인가 — nyquist_gate 로 이분법 탐색
    M3 완화계수                : 1/cos(β/2) 를 β 축에 펼치고 장면통계와 맞댄다
    M4 헤드라인 패리티         : 1.07 m/s 가 모노값이자 바이스태틱 최악값인가
    """
    rng = np.random.default_rng(seed)
    psi = np.linspace(0.0, 360.0, int(n_psi), endpoint=False)
    lam = LAM_N78
    v = 5.0                                     # freespace_scene.FS_SPEED[0]

    # --- M1: 공선 항등식 ---------------------------------------------------- #
    rows = []
    for _ in range(200):
        d = float(rng.uniform(60.0, 5000.0))
        phi = float(rng.uniform(0.0, 360.0))
        alt = float(rng.uniform(20.0, 300.0))
        tgt = fss.target_pos(d, phi, 0.0, alt)                  # L=0 → TX 와 RX 가 같은 점
        p = fss.fs_params(fss.FS_TX, fss.FS_TX, tgt, (0.0, 0.0, 0.0), FC_N78)
        V = fss.heading_velocity(psi, v)
        fd = (V @ (p["u1"] + p["u2"])) / lam                    # 저장소 식 그대로
        el = fss.look_el_deg(p["u1"], p["u2"])
        fd_repo = float(np.max(np.abs(fd)))
        fd_mono = (2.0 * v / lam) * math.cos(math.radians(el))  # 모노스태틱 닫힌형
        rows.append(dict(d_m=d, phi_deg=phi, alt_m=alt,
                         beta_deg=float(p["beta"]), el_deg=float(el),
                         u_gap=float(np.max(np.abs(p["u1"] - p["u2"]))),
                         Rb_over_2R=float(p["Rb"] / (2.0 * p["R1"])),
                         fd_max_repo_hz=fd_repo, fd_max_mono_hz=fd_mono,
                         rel_err=abs(fd_repo - fd_mono) / max(abs(fd_mono), 1e-12)))
    rel = np.array([r["rel_err"] for r in rows])
    m1 = dict(
        n_geometries=len(rows), psi_grid=int(n_psi),
        max_beta_deg=float(max(r["beta_deg"] for r in rows)),
        max_u1_minus_u2=float(max(r["u_gap"] for r in rows)),
        max_rel_err=float(rel.max()), median_rel_err=float(np.median(rel)),
        Rb_over_2R_span=[float(min(r["Rb_over_2R"] for r in rows)),
                         float(max(r["Rb_over_2R"] for r in rows))],
        statement_en=("With TX and RX collocated the repository's bistatic parameter function "
                      "returns beta = 0 and u1 = u2 exactly, so f_d = v.(u1+u2)/lambda collapses "
                      "to the monostatic 2v.u/lambda and the bistatic range Rb collapses to the "
                      "two-way range 2R. Monostatic is not a different law; it is beta = 0."),
        statement_ko=("TX 와 RX 를 같은 점에 놓으면 저장소 바이스태틱 함수가 β=0·u1=u2 를 정확히 "
                      "돌려주고, f_d = v·(u1+u2)/λ 가 모노스태틱 2v·û/λ 로, Rb 가 왕복거리 2R 로 "
                      "떨어진다. 모노스태틱은 다른 법칙이 아니라 β=0 이다."),
        worst=max(rows, key=lambda r: r["rel_err"]))

    # --- M2: 하한 동일성 (접힘 시작 속도) ----------------------------------- #
    #  모노: TX=RX, 표적을 같은 높이로 아주 멀리 → β=0, δ=0
    #  바이: L=500 m, 표적을 같은 높이로 아주 멀리 → β→0, δ→0 (refrate_law V2 와 같은 구성)
    def _onset(uu, prf):
        lo, hi = 1e-6, law_v_max(lam, prf) * 4.0
        for _ in range(90):
            mid = 0.5 * (lo + hi)
            fd = (fss.heading_velocity(psi, mid) @ uu) / lam
            if float(np.mean(~np.asarray(fss.nyquist_gate(fd, prf)))) > 0.0:
                hi = mid
            else:
                lo = mid
        return 0.5 * (lo + hi)

    D_FAR = 3.0e6
    p_mono = fss.fs_params(fss.FS_TX, fss.FS_TX,
                           fss.target_pos(D_FAR, 0.0, 0.0, fss.FS_TX[2]),
                           (0.0, 0.0, 0.0), FC_N78)
    p_bi = fss.fs_params(fss.FS_TX, fss.FS_RX(500.0),
                         fss.target_pos(D_FAR, 0.0, 500.0, fss.FS_TX[2]),
                         (0.0, 0.0, 0.0), FC_N78)
    uu_mono = p_mono["u1"] + p_mono["u2"]
    uu_bi = p_bi["u1"] + p_bi["u2"]

    m2 = []
    for prf in (6.25, 12.5, 25.0, 50.0, 100.0, 200.0, 500.0, 1000.0):
        vmax = law_v_max(lam, prf)
        vm, vb = _onset(uu_mono, prf), _onset(uu_bi, prf)
        m2.append(dict(prf_hz=prf, v_max_closed_ms=vmax,
                       v_onset_monostatic_ms=float(vm), v_onset_bistatic_beta0_ms=float(vb),
                       rel_err_mono=float(abs(vm - vmax) / vmax),
                       rel_err_bi=float(abs(vb - vmax) / vmax),
                       mono_equals_bistatic_floor=bool(abs(vm - vb) / vmax < 1e-6)))
    m2_all_match = all(r["mono_equals_bistatic_floor"] and r["rel_err_mono"] < 1e-6
                       for r in m2)

    # --- M3: 완화계수 -------------------------------------------------------- #
    betas = (0.0, 15.0, 30.0, 45.0, 60.0, 75.0, 90.0, 120.0, 150.0, 179.0)
    relief = {("%gdeg" % b): dict(
        relief_1_over_cos_half_beta=1.0 / math.cos(math.radians(b) / 2.0),
        v_max_ms_at_ssb=law_v_max(lam, 50.0, b, 0.0)) for b in betas}
    scene = harden["A_formula"]["relief_factor_G"]["beta_le_90_only"]
    m3 = dict(
        formula="relief(beta, delta) = 1 / (cos(beta/2) cos delta) >= 1",
        by_beta=relief,
        monostatic_relief=1.0,
        delta_is_shared=("δ(이등분선 앙각) 항은 모노/바이 공통이다 — 모노스태틱도 표적이 위에 있으면 "
                         "1/cos δ 만큼 완화받는다. 하한 λPRF/4 는 β=0 **이고** δ=0 인 절편이다."),
        scene_statistics_beta_le_90=dict(
            source="outputs/vmax_hardening.json : A_formula.relief_factor_G.beta_le_90_only",
            min=scene["min"], p50=scene["p50"], p90=scene["p90"], max=scene["max"]),
        verdict_ko=("바이스태틱이 모노스태틱보다 **관대하다**. 그러나 우리 장면(β≤90°)에서 완화는 "
                    "중앙값 {p50:.3f}배·최대 {mx:.3f}배뿐이라 1.07 → 최대 {vm:.2f} m/s 로만 오른다."
                    ).format(p50=scene["p50"], mx=scene["max"],
                             vm=harden["A_formula"]["v_max_G1_ms"]["best_in_scene"]))

    # --- M4: 헤드라인 패리티 ------------------------------------------------- #
    row = refrate["illuminators"]["rows"]["nr_ssb"]
    v_mono = law_v_max(lam, row["prf_hz"], 0.0, 0.0)
    v_bi_floor = law_v_max(lam, row["prf_hz"], 0.0, 0.0)
    v_bi_45 = law_v_max(lam, row["prf_hz"], 45.0, 0.0)
    v_bi_90 = law_v_max(lam, row["prf_hz"], 90.0, 0.0)
    m4 = dict(
        published_v_max_ms=row["v_max_ms"],
        source="outputs/refrate_law.json : illuminators.rows.nr_ssb.v_max_ms",
        monostatic_v_max_ms=v_mono,
        bistatic_floor_v_max_ms=v_bi_floor,
        rel_err_vs_published=float(abs(v_mono - row["v_max_ms"]) / row["v_max_ms"]),
        identical=bool(abs(v_mono - row["v_max_ms"]) / row["v_max_ms"] < 1e-12),
        bistatic_at_45deg_ms=v_bi_45, bistatic_at_90deg_ms=v_bi_90,
        headline_en=("The published 1.07 m/s is simultaneously the monostatic value at 3.5 GHz / "
                     "50 Hz and the bistatic worst case. Every bistatic geometry with beta > 0 "
                     "measures a HIGHER unambiguous speed. The headline is therefore conservative, "
                     "not geometry-flattered."),
        headline_ko=("⭐ 발표한 {v:.4g} m/s 는 3.5 GHz·50 Hz 에서 **모노스태틱 값이자 동시에 "
                     "바이스태틱 최악값**이다. β>0 인 모든 바이스태틱 기하는 이보다 **큰** 무모호 "
                     "속도를 갖는다(β=45° {a:.3f}, β=90° {b:.3f} m/s). 그러므로 헤드라인은 기하로 "
                     "부풀린 값이 아니라 기하로 깎은 값이다 — 보수적이다."
                     ).format(v=row["v_max_ms"], a=v_bi_45, b=v_bi_90))

    # --- 무엇이 모노/바이에서 **다른가** (도플러 축 밖) ---------------------- #
    differences = [
        dict(axis="Doppler (this file's axis)",
             monostatic="f_d = 2 v_r / lambda",
             bistatic="f_d = (2 v / lambda) cos(beta/2) cos(delta)",
             consequence="bistatic is the more forgiving one; monostatic IS the beta=0 floor",
             verification="repo (§1 M1/M2)"),
        dict(axis="range/delay",
             monostatic="two-way range 2R; the repository's Rb collapses to 2R when TX=RX "
                        "(verified in M1: Rb/2R = 1 to machine precision)",
             bistatic="Rb = R1 + R2 - L, an ellipse; one receiver gives an iso-range ellipse, "
                      "not a range",
             consequence="monostatic localizes with range+angle from one site; bistatic needs "
                         "geometry knowledge or more receivers",
             verification="repo (§1 M1: Rb_over_2R span)"),
        dict(axis="RCS",
             monostatic="backscatter sigma — our production path (rcs_sbr_batch is monostatic)",
             bistatic="bistatic sigma, restricted to beta <= 45 deg in this project by the "
                      "reciprocity/obliquity limits of the PO kernel",
             consequence="⭐ the RCS layer is BETTER covered for monostatic than for bistatic in "
                         "this repository — the opposite of the detection layer",
             verification="repo policy (project memory: sionna2-rcs-methodology)"),
        dict(axis="interference",
             monostatic="own-transmitter self-interference (see §3)",
             bistatic="direct-path interference from a transmitter you do not control (see §3)",
             consequence="both are ~100 dB problems, for different reasons",
             verification="repo link budget (§3)"),
    ]

    return dict(
        M1_collocation_identity=m1,
        M2_floor_equality=dict(rows=m2, all_match=bool(m2_all_match),
                               method="bisection on freespace_scene.nyquist_gate over 3600 headings",
                               verdict_ko=("모노스태틱과 β→0 바이스태틱의 접힘 시작 속도가 8개 "
                                           "반복률 전부에서 λ·PRF/4 와 상대오차 1e-6 미만으로 "
                                           "일치한다." if m2_all_match else "불일치 발견 — 재검토")),
        M3_bistatic_relief=m3,
        M4_headline_parity=m4,
        what_differs_besides_doppler=differences,
        treated_case_statement_ko=(
            "모노스태틱은 이제 각주가 아니다. §1 은 (a) 저장소 함수로 β=0 절편임을 재현하고, "
            "(b) 접힘 시작 속도가 λPRF/4 로 동일함을 나이퀴스트 게이트로 확인하고, "
            "(c) 완화계수를 β 축에 펼치고, (d) 헤드라인이 모노값이자 바이스태틱 최악값임을 "
            "패리티로 못박는다."),
    )


# =========================================================================== #
#  §2  ⭐ 설계자유도 축 — 모노스태틱의 PRF 는 실제로 얼마나 자유로운가
# =========================================================================== #
def sec2_freedom(refrate, sigma_json):
    lam = LAM_N78

    # --- D1  3GPP 프레임 구조가 허용하는 **이산** 사다리 --------------------- #
    passive_ladder = []
    for T_ms in SSB_PERIOD_MS:
        prf = 1000.0 / T_ms
        passive_ladder.append(dict(period_ms=T_ms, prf_hz=prf,
                                   v_max_ms=law_v_max(lam, prf),
                                   is_repo_default=bool(T_ms == SSB_DEFAULT_MS)))
    mono_ladder = []
    for n in CSIRS_SLOTS:
        T = n * SLOT_S
        prf = 1.0 / T
        mono_ladder.append(dict(slots=int(n), period_ms=T * 1e3, prf_hz=prf,
                                v_max_ms=law_v_max(lam, prf)))
    prf_ceiling = max(r["prf_hz"] for r in mono_ladder)
    v_ceiling = law_v_max(lam, prf_ceiling)
    prf_floor_mono = min(r["prf_hz"] for r in mono_ladder)

    # 천장의 산술 교차확인: 4 슬롯 × 0.5 ms = 2 ms = 500 Hz  ==  LaSen 이 규격에서 인용한 값
    ceiling_crosscheck = dict(
        derived_hz=prf_ceiling, quoted_hz=500.0,
        rel_err=float(abs(prf_ceiling - 500.0) / 500.0),
        match=bool(abs(prf_ceiling - 500.0) / 500.0 < 1e-9),
        source=SRC["csirs_ceiling_500hz"],
        note_ko=("4 슬롯 × {s:.1f} ms = {p:.1f} ms → {f:g} Hz. LaSen 이 TS 38.331 에서 인용한 "
                 "sub-6 천장과 정확히 같다 — 사다리의 위쪽 끝은 규격으로 닫힌다."
                 ).format(s=SLOT_S * 1e3, p=1.0 / prf_ceiling * 1e3, f=prf_ceiling))

    # 저장소 패리티: refrate_law 에 이미 500 Hz 행이 있다(nr_prs_max)
    par = refrate["illuminators"]["rows"]["nr_prs_max"]
    ceiling_parity = dict(repo_row="illuminators.rows.nr_prs_max",
                          repo_v_max_ms=par["v_max_ms"], ours_v_max_ms=v_ceiling,
                          rel_err=float(abs(par["v_max_ms"] - v_ceiling) /
                                        max(par["v_max_ms"], 1e-12)),
                          match=bool(abs(par["v_max_ms"] - v_ceiling) < 1e-9))

    # --- D2  천장 시험: 최선의 합법 모노스태틱 반복률이 실기체를 덮는가 ------ #
    speeds = {k: v.max_speed_ms for k, v in drn.DRONES.items() if v.max_speed_ms is not None}
    scene = dict(scene_slow=fss.FS_SPEED[0], scene_fast=fss.FS_SPEED[1])
    v_passive_default = law_v_max(lam, 1000.0 / SSB_DEFAULT_MS)
    v_passive_best = law_v_max(lam, max(r["prf_hz"] for r in passive_ladder))
    cover = {}
    for name, v in list(speeds.items()) + list(scene.items()):
        cover[name] = dict(
            speed_ms=float(v),
            passive_default_covers=bool(v_passive_default >= v),
            passive_best_legal_covers=bool(v_passive_best >= v),
            monostatic_ceiling_covers=bool(v_ceiling >= v))
    n_air = len(speeds)
    n_air_cov = sum(1 for k in speeds if cover[k]["monostatic_ceiling_covers"])
    d2 = dict(
        v_passive_default_ms=v_passive_default,
        v_passive_best_legal_ms=v_passive_best,
        v_monostatic_ceiling_ms=v_ceiling,
        airframe_speeds_ms=speeds,
        airframe_source="src/drones.py : DroneSpec.max_speed_ms (docs/drone_research.json)",
        scene_speeds_ms=scene, scene_source="src/freespace_scene.py : FS_SPEED",
        coverage=cover,
        airframes_covered_by_monostatic_ceiling="%d/%d" % (n_air_cov, n_air),
        slowest_airframe_max_ms=float(min(speeds.values())),
        verdict_ko=("⭐ 3.5 GHz 에서 **기준신호 레인의 천장은 {vc:.2f} m/s** 다. 공개된 기체 최고속도 "
                    "중 가장 느린 것({sl:.1f} m/s)조차 못 덮는다({cov} 커버). 우리 장면속도 5 m/s 는 "
                    "천장에서만 덮이고(패시브 최선 합법설정 {vb:.2f} m/s 로는 못 덮는다), 15 m/s 는 "
                    "천장으로도 못 덮는다. 즉 모노스태틱의 '자유'는 5 m/s 를 사는 데까지다."
                    ).format(vc=v_ceiling, sl=min(speeds.values()),
                             cov="%d/%d" % (n_air_cov, n_air), vb=v_passive_best))

    # --- D3  반송파 축 — 밴드를 바꾸면 넘는가 -------------------------------- #
    v_target = float(max(speeds.values()))
    fc_max_mono = C0 * prf_ceiling / (4.0 * v_target)
    fc_max_passive = C0 * (1000.0 / SSB_DEFAULT_MS) / (4.0 * v_target)
    bands = {"n71 (600 MHz)": 0.6e9, "n28 (700 MHz)": 0.7e9, "n8 (900 MHz)": 0.9e9,
             "n3 (1.8 GHz)": 1.8e9, "n78 (3.5 GHz)": 3.5e9}
    band_rows = {}
    for lab, fc in bands.items():
        lm = C0 / fc
        band_rows[lab] = dict(
            fc_hz=fc,
            v_max_passive_ssb50_ms=law_v_max(lm, 1000.0 / SSB_DEFAULT_MS),
            v_max_mono_ceiling_ms=law_v_max(lm, prf_ceiling),
            passive_covers_fastest=bool(law_v_max(lm, 1000.0 / SSB_DEFAULT_MS) >= v_target),
            mono_covers_fastest=bool(law_v_max(lm, prf_ceiling) >= v_target))
    # ⚠ 500 Hz 천장은 **30 kHz SCS**(슬롯 0.5 ms)의 4-슬롯 최소값이다. 저밴드는 보통 15 kHz SCS 라
    #   같은 4-슬롯 규칙이 250 Hz 밖에 안 준다 — 밴드 탈출 논증에 결정적이므로 따로 계산한다.
    scs_rows = {}
    for mu, scs in ((0, 15.0), (1, 30.0), (2, 60.0)):
        slot = 1e-3 / (2 ** mu)
        prf_mu = 1.0 / (min(CSIRS_SLOTS) * slot)
        scs_rows["mu%d_%gkHz" % (mu, scs)] = dict(
            scs_khz=scs, slot_ms=slot * 1e3, min_slots=min(CSIRS_SLOTS), prf_max_hz=prf_mu,
            fc_max_for_fastest_airframe_hz=C0 * prf_mu / (4.0 * v_target),
            v_max_by_band_ms={lab: law_v_max(C0 / fc, prf_mu) for lab, fc in bands.items()})
    prf_low = scs_rows["mu0_15kHz"]["prf_max_hz"]
    fc_cross_low = C0 * prf_low / (4.0 * v_target)
    for lab, fc in bands.items():
        band_rows[lab]["v_max_mono_ceiling_15kHz_scs_ms"] = law_v_max(C0 / fc, prf_low)
        band_rows[lab]["mono_covers_fastest_15kHz_scs"] = bool(
            law_v_max(C0 / fc, prf_low) >= v_target)

    d3 = dict(
        formula="f_c,max = c*PRF/(4*v)   (outputs/refrate_law.json : design_rule.formulas)",
        fastest_airframe_ms=v_target,
        fc_max_for_monostatic_ceiling_hz=fc_max_mono,
        fc_max_for_monostatic_ceiling_15kHz_scs_hz=fc_cross_low,
        fc_max_for_passive_ssb_default_hz=fc_max_passive,
        bands=band_rows,
        scs_dependence=dict(
            rows=scs_rows,
            why_it_matters=("⚠ 500 Hz 는 30 kHz SCS(슬롯 0.5 ms)의 4-슬롯 최소값이다. 저밴드에서 "
                            "흔히 쓰는 15 kHz SCS 면 같은 규칙이 250 Hz 밖에 안 준다 — 밴드로 "
                            "탈출한다는 논증이 정확히 이 지점에서 반쯤 깎인다."),
            verification="spec_derived (슬롯 길이는 규격 산술, 4-슬롯 최소는 SRC.csirs_slot_set)",
            unverified=("어느 밴드가 실제로 어느 numerology 로 배치되는지는 우리가 확인하지 않았다. "
                        "저밴드=15 kHz 는 통념이고 근거를 우리가 갖고 있지 않다.")),
        verdict_ko=("모노스태틱이 가장 빠른 기체({v:.0f} m/s)를 30 kHz SCS 천장({p:g} Hz)으로 덮으려면 "
                    "반송파가 {f:.2f} GHz 이하여야 한다. ⚠ 그러나 저밴드는 보통 15 kHz SCS 이고 그러면 "
                    "천장이 {q:g} Hz 로 반토막나 경계가 {h:.2f} GHz 로 내려온다 — 그 경우 n8(0.9 GHz)은 "
                    "{n8:.1f} m/s 로 **실패**하고 n71·n28 만 남는다. 패시브가 SSB 기본설정으로 같은 "
                    "일을 하려면 {g:.0f} MHz 이하여야 하고 그런 상시 5G 조명원은 없다. ⚠ 게다가 저밴드는 "
                    "대역폭이 좁아 거리분해능을 내주므로 공짜 교환이 아니다."
                    ).format(v=v_target, p=prf_ceiling, f=fc_max_mono / 1e9, q=prf_low,
                             h=fc_cross_low / 1e9,
                             n8=band_rows["n8 (900 MHz)"]["v_max_mono_ceiling_15kHz_scs_ms"],
                             g=fc_max_passive / 1e6))

    # --- D4  듀플렉싱 — 송신을 멈추고 들을 수 있는가 ------------------------- #
    sym_s = 1.0 / (SCS_KHZ * 1e3)               # OFDM 유효심볼 (CP 제외)
    rt = {("%gm" % R): 2.0 * R / C0 * 1e6 for R in (30.0, 100.0, 300.0, 1000.0)}
    R_after_one_symbol = 0.5 * C0 * sym_s
    d4 = dict(
        scs_khz=SCS_KHZ, slot_ms=SLOT_S * 1e3,
        ofdm_symbol_us=sym_s * 1e6,
        round_trip_delay_us=rt,
        range_whose_echo_lands_after_one_symbol_m=R_after_one_symbol,
        source_numerology=SRC["nr_numerology"],
        argument_en=("A target echo returns within a fraction of one OFDM symbol: 0.67 us at "
                     "100 m against a 33.3 us symbol at 30 kHz SCS. Only a target beyond "
                     "%.1f km would have its echo arrive after the transmitter stopped. Waiting "
                     "for the TDD uplink slot is therefore not an option — the echo has long "
                     "passed. Monostatic sensing means receiving DURING one's own transmission, "
                     "i.e. in-band full duplex." % (R_after_one_symbol / 1e3)),
        verdict_ko=("모노스태틱 센싱에는 '송신을 멈추고 듣는' 선택지가 없다. 100 m 표적의 왕복지연 "
                    "{a:.2f} us 는 30 kHz SCS 심볼 {b:.1f} us 의 {c:.1%} 에 불과하고, 심볼이 끝난 "
                    "뒤 도착하려면 표적이 {d:.1f} km 밖이어야 한다. 그래서 자기간섭이 **선택이 아니라 "
                    "구조**다."
                    ).format(a=rt["100m"], b=sym_s * 1e6, c=rt["100m"] / (sym_s * 1e6),
                             d=R_after_one_symbol / 1e3),
        honesty_note=("LaSen 은 'TDD' 를 0회 언급하고, 자기 실험은 5.8 GHz 비면허대역에서 분리 "
                      "안테나 + 차폐판으로 이 문제를 우회했다 ⟨outputs/monostatic_prior.json : "
                      "lasen.self_interference_handling⟩. 즉 실제 TDD gNB 에서 어떻게 하는지는 "
                      "선행에도 없다."))

    # --- D5  자기간섭 예산 — 인용이 아니라 **저장소로 계산** ----------------- #
    sig_sorted = np.asarray(sigma_json["sigma"]["stats"]["mavic4pro"]["sigma_sorted_dbsm"], float)
    sig_dbsm = float(np.median(sig_sorted))
    sig_m2 = 10.0 ** (sig_dbsm / 10.0)
    lb = LinkBudget()
    eirp_w = 10.0 ** (lb.eirp_dbm / 10.0) * 1e-3
    bw_hz = float(refrate["law"]["repo_parity"]["nr_ssb"]["repo_ref_bw_hz"])
    p_noise = lb.noise_power_w(bw_hz)

    si = {}
    for R in (50.0, 100.0, 200.0):
        p_echo = lb.echo_power_w(lam, sig_m2, R, R)            # 모노스태틱: R1=R2=R
        echo_below_eirp = float(lin2db(p_echo / eirp_w))
        req_iso = -echo_below_eirp
        si["%gm" % R] = dict(
            range_m=R, echo_below_eirp_db=echo_below_eirp,
            isolation_for_SI_equal_to_echo_db=req_iso,
            shortfall_vs_barneto_100dB_db=req_iso - 100.0,
            echo_snr_db=float(lin2db(p_echo / p_noise)))
    p_si_res = eirp_w * 10.0 ** (-100.0 / 10.0)               # Barneto 실측 100 dB 적용 후
    si_above_noise_db = float(lin2db(p_si_res / p_noise))
    M_cpi = int(fss.M_from_prf(0.1, prf_ceiling))
    coh_gain_db = 10.0 * math.log10(M_cpi)

    # 패시브 거울상: 같은 저장소 링크버짓으로 직접파-에코비
    tgt = fss.target_pos(1000.0, 90.0, fss.L_REF, fss.FS_ALT[0])
    pp = fss.fs_params(fss.FS_TX, fss.FS_RX(fss.L_REF), tgt, (0.0, 0.0, 0.0), FC_N78)
    lt = link_terms(lb, lam, sig_m2, pp["R1"], pp["R2"], pp["L"], bw_hz)

    # ⭐ 두 간섭 문제의 **정확한** 차이 — 거리에 무관한 닫힌형
    #    mono_req / passive_DNR = EIRP / P_direct = (4 pi L / lambda)^2 / G_rx
    #    즉 모노스태틱이 더 무는 양은 **패시브 직접파가 베이스라인에서 겪는 경로손실**이다.
    offset_db = float(lin2db(eirp_w / lb.direct_power_w(lam, pp["L"])))
    offset_closed_db = 20.0 * math.log10(4.0 * math.pi * pp["L"] / lam) - lb.rx_gain_dbi
    chk = []
    for R in (50.0, 100.0, 200.0, 1000.0):
        mono_req = -float(lin2db(lb.echo_power_w(lam, sig_m2, R, R) / eirp_w))
        pas_dnr = float(lin2db(lb.direct_power_w(lam, pp["L"]) /
                               lb.echo_power_w(lam, sig_m2, R, R)))
        chk.append(dict(R_m=R, mono_required_iso_db=mono_req, passive_dnr_db=pas_dnr,
                        difference_db=mono_req - pas_dnr))
    axis = dict(
        offset_db=offset_db, offset_closed_form_db=offset_closed_db,
        closed_form="mono_required_isolation - passive_direct_to_echo = 20 log10(4 pi L / lambda) "
                    "- G_rx  =  the free-space loss the illuminator's direct path suffers over the "
                    "baseline",
        rel_err=float(abs(offset_db - offset_closed_db) / max(abs(offset_closed_db), 1e-12)),
        range_independence_check=chk,
        range_independent=bool(max(r["difference_db"] for r in chk)
                               - min(r["difference_db"] for r in chk) < 1e-6),
        baseline_m=float(pp["L"]),
        continuity_ko=("⭐ 이 차이는 표적거리에 **무관**하다(둘 다 R^4 로 간다). 그리고 베이스라인 L 로 "
                       "닫힌다 — L 을 줄이면 패시브의 직접파 문제가 모노스태틱의 자기간섭 문제로 "
                       "연속적으로 수렴한다. 즉 간섭 축에서도 모노스태틱은 별종이 아니라 **L→0 "
                       "극한**이다. 도플러 축의 β=0 절편과 같은 이야기다."))

    d5 = dict(
        sigma_dbsm=sig_dbsm, sigma_source="outputs/report13_sigma_grid.mavic4pro.json : "
                                          "sigma.stats.mavic4pro.sigma_sorted_dbsm (median of %d)"
                                          % sig_sorted.size,
        link_budget=dict(eirp_dbm=lb.eirp_dbm, rx_gain_dbi=lb.rx_gain_dbi,
                         noise_figure_db=lb.noise_figure_db, bw_hz=bw_hz,
                         source="benchmark/link_budget.py : LinkBudget() defaults; bandwidth from "
                                "outputs/refrate_law.json law.repo_parity.nr_ssb.repo_ref_bw_hz"),
        monostatic=si,
        barneto=dict(measured_isolation_db=100.0, source=SRC["barneto_si"],
                     residual_SI_above_noise_floor_db=si_above_noise_db,
                     adc_bits_for_residual_SI=si_above_noise_db / 6.02,
                     coherent_gain_at_ceiling_db=coh_gain_db, M_pulses=M_cpi,
                     T_cpi_s=0.1),
        passive_mirror=dict(
            geometry="freespace scene: L=%.0f m, d=1000 m, alt=%.0f m, beta=%.1f deg"
                     % (pp["L"], fss.FS_ALT[0], pp["beta"]),
            direct_to_echo_ratio_db=lt["dnr_db"], echo_snr_db=lt["snr_echo_db"],
            source="benchmark/link_budget.link_terms with repository geometry",
            literature_comparison=SRC["sharma_dpi"]),
        interference_axis=axis,
        verdict_ko=("모노스태틱: 100 m 드론 에코는 자기 EIRP 보다 {a:.1f} dB 아래라, 잔여 자기간섭을 "
                    "에코 밑으로 넣으려면 {b:.1f} dB 격리가 필요하다 — 실측 최고치 100 dB 로는 "
                    "{c:.1f} dB 부족하다. 패시브: 우리 기준 기하(R≈{Rq:.0f} m)에서 직접파가 에코보다 "
                    "{d:.1f} dB 크다. ⚠ 이 두 숫자는 표적거리가 달라 그대로 빼면 안 된다 — **같은 "
                    "100 m 에서** 비교하면 모노 {b:.1f} dB 대 패시브 {pm:.1f} dB 로 모노 쪽이 "
                    "{g:.1f} dB 더 무겁고, 그 차이는 정확히 패시브 직접파가 베이스라인 {L:.0f} m 에서 "
                    "겪는 경로손실이다(20log10(4πL/λ)−G_rx, 표적거리에 무관). 대신 성질이 다르다: 모노의 "
                    "잔여 SI 는 0-도플러에 앉아 있어 이동표적 검출에는 덜 치명적이고(Barneto 자신의 "
                    "문장), 위협하는 것은 수신단 포화다 — 100 dB 를 걷어낸 뒤에도 잔여 SI 가 잡음바닥보다 "
                    "{e:.1f} dB 높아 ADC 에 {f:.1f} 비트를 그냥 먹인다."
                    ).format(a=-si["100m"]["echo_below_eirp_db"],
                             b=si["100m"]["isolation_for_SI_equal_to_echo_db"],
                             c=si["100m"]["shortfall_vs_barneto_100dB_db"],
                             d=lt["dnr_db"], e=si_above_noise_db, f=si_above_noise_db / 6.02,
                             g=offset_db, L=pp["L"], Rq=pp["R_eq"],
                             pm=[r for r in chk if r["R_m"] == 100.0][0]["passive_dnr_db"]),
        honesty_note=SRC["barneto_counter"])

    # --- D6  데이터심볼 레인 — PRF 라는 양이 정의되지 않는다 ----------------- #
    full_rate = 1.0 / (SLOT_S / 14.0)           # 슬롯당 14 심볼 → 만재 슬로타임 표본율
    d6 = dict(
        full_buffer_symbol_rate_hz=full_rate,
        full_buffer_v_max_ms=law_v_max(lam, full_rate),
        cross_check_with_prior=dict(
            prior_hz=27777.777777777777,
            source="outputs/monostatic_prior.json : "
                   "verification_of_our_law_against_prior_measurements.lasen_full_load_ceiling",
            rel_err=float(abs(full_rate - 27777.777777777777) / 27777.777777777777)),
        measured_traffic=SRC["lasen_traffic"],
        theory_counterpart=SRC["marchese_nfb"],
        who_can_use="monostatic only — the receiver must know X[m,n], which only the transmitter does",
        passive_toll=("패시브도 전 파형을 쓸 수 있지만 유료다: 깨끗한 기준채널 + 표준 준수 복조/재변조. "
                      "refrate_law 의 nr_recon 행(ambient=False, continuous_reference=True)이 그 레인이다."),
        verdict_ko=("만재 가정이면 {r:.1f} kHz 표본율 → {v:.0f} m/s 로 벽이 사라진다. 그러나 이것은 "
                    "**반복률이 아니라 트래픽**이고, 실측 상용망은 시간의 95%를 RE 점유율 7.1% 아래에서 "
                    "보낸다. 즉 데이터심볼 레인의 v_max 는 설계변수가 아니라 부하의 함수다 — "
                    "PRF 라는 양 자체가 정의되지 않는다."
                    ).format(r=full_rate / 1e3, v=law_v_max(lam, full_rate)))

    # --- D7  자유도 판정 ----------------------------------------------------- #
    freedom_ratio = v_ceiling / v_passive_default
    d7 = dict(
        question="For a monostatic ISAC sensor, how free is PRF_ref really?",
        answer_en=("Bounded, quantized, and smaller than the framing implies. The reference-signal "
                   "repetition rate is not a continuous design variable: it is a discrete ladder "
                   "of slot-multiples, capped by 3GPP at %g Hz for sub-6 CSI-RS. Against the "
                   "passive default that is a factor of %.1f in v_max — real, but finite, and it "
                   "still does not reach the slowest published airframe maximum at 3.5 GHz."
                   % (prf_ceiling, freedom_ratio)),
        freedom_ratio_v_max=freedom_ratio,
        freedom_is_quantized_to_n_steps=len(CSIRS_SLOTS),
        ladder_span_hz=[prf_floor_mono, prf_ceiling],
        ladder_span_v_max_ms=[law_v_max(lam, prf_floor_mono), v_ceiling],
        what_the_framing_got_wrong=[
            "'모노스태틱은 PRF 를 자유롭게 고른다' — 틀렸다. 3GPP 가 sub-6 CSI-RS 에 500 Hz 천장을 "
            "걸었고 ⟨SRC.csirs_ceiling_500hz, LaSen 원문 인용⟩, 값은 슬롯 배수로 양자화된다.",
            "'그래서 모노스태틱이면 이 문제가 없다' — 틀렸다. 천장의 v_max 는 {v:.2f} m/s 로 "
            "가장 느린 기체 최고속도({s:.1f} m/s)에도 못 미친다.".format(
                v=v_ceiling, s=min(speeds.values())),
            "'모노스태틱은 송신을 멈추고 들으면 된다' — 틀렸다. 왕복지연이 심볼길이의 "
            "{p:.1%} 라 인밴드 전이중이 강제된다(D4).".format(
                p=(2 * 100.0 / C0) / sym_s),
        ],
        what_the_framing_got_right=[
            "선택권의 **소재**는 맞다. 모노스태틱은 사다리 위 어느 칸을 쓸지 **고를 수 있고**, "
            "패시브는 망이 고른 칸을 받는다. 같은 200 Hz 라도 모노에겐 설계값이고 패시브에겐 운이다.",
            "벽을 실제로 넘는 길(전 파형/데이터심볼)이 모노스태틱에겐 공짜라는 것도 맞다 — "
            "다만 그 길은 반복률이 아니라 트래픽에 종속된다(D6).",
        ],
        honest_finding=(
            "⚠ 프레이밍이 시사하는 것보다 자유는 **작다**. 그러나 그것이 우리 경계논증을 약화시키지 "
            "않는다 — 오히려 강화한다. 약화되는 것은 '패시브만의 문제'라는 옛 서사이고, 새로 서는 "
            "것은 '반복률 벽은 모노/패시브 공통이며, 3.5 GHz 에서는 **어느 쪽도** 실기체를 못 덮는다' "
            "는 더 강한 명제다. 리뷰어의 '왜 모노스태틱을 안 하느냐'에 대한 답은 '모노스태틱도 "
            "{v:.2f} m/s 에서 멈춘다'이다."
        ).format(v=v_ceiling),
    )

    return dict(
        carrier_hz=FC_N78, lambda_m=lam,
        convention="v_max is the half-window (+/-) value: v_max = lambda*PRF/4 at beta=delta=0",
        D1_discrete_ladder=dict(
            passive_ssb=passive_ladder, monostatic_csirs=mono_ladder,
            slot_s=SLOT_S, scs_khz=SCS_KHZ,
            ceiling_crosscheck=ceiling_crosscheck, ceiling_repo_parity=ceiling_parity,
            multiset_lever=SRC["csirs_multiset"],
            slot_set_caveat=SRC["csirs_slot_set"],
            ssb_set_source=SRC["ssb_period_set"],
            who_chooses=dict(
                passive="the network operator; the sensor has no vote. The passive 'range' is "
                        "DEPLOYMENT UNCERTAINTY, not a design choice.",
                monostatic="the sensor, within the 3GPP ceiling, paying communication overhead "
                           "at the top of the ladder. This IS a design choice.",
                sharpest_line_ko=("⭐ 패시브가 좋은 셀을 만나 얻는 최선(SSB 5 ms = {a:.2f} m/s)은 "
                                  "LaSen 이 상용 N41 에서 **실측한** 모노스태틱 CSI-RS 값(200 Hz = "
                                  "{a:.2f} m/s)과 같다. 즉 운 좋은 패시브 = 전형적 모노스태틱이다."
                                  ).format(a=v_passive_best))),
        D2_ceiling_test=d2,
        D3_carrier_axis=d3,
        D4_duplexing=d4,
        D5_self_interference=d5,
        D6_data_symbol_lane=d6,
        D7_verdict=d7,
    )


# =========================================================================== #
#  §3  비용원장 — 양방향. 숫자가 있는 행은 숫자를, 없는 행은 없다고 적는다
# =========================================================================== #
def sec3_ledger(freedom):
    d5 = freedom["D5_self_interference"]
    d2 = freedom["D2_ceiling_test"]
    d7 = freedom["D7_verdict"]

    def row(side, kind, item, number, unit, source, grade, note=""):
        return dict(side=side, kind=kind, item=item, number=number, unit=unit,
                    source=source, verification=grade, note=note)

    ledger = [
        # --- 모노스태틱이 사는 것 ------------------------------------------- #
        row("monostatic", "buys", "chosen repetition rate (a design variable)",
            d7["freedom_ratio_v_max"], "x v_max vs the passive SSB default",
            "this file §2 D1/D7", "computed",
            "quantized to %d ladder steps and capped at %g Hz"
            % (d7["freedom_is_quantized_to_n_steps"], d7["ladder_span_hz"][1])),
        row("monostatic", "buys", "known transmit symbols X[m,n] -> the data-symbol lane",
            freedom["D6_data_symbol_lane"]["full_buffer_v_max_ms"], "m/s (full-buffer ideal)",
            "this file §2 D6; LaSen §3.1.2", "computed + pdf_quote",
            "traffic dependent: measured <5% of time above 7.1% RE utilization"),
        row("monostatic", "buys", "no reference channel needed (self-synchronized)",
            None, None, "structural", "argument",
            "the passive receiver must acquire a clean copy of the illuminator's waveform"),
        row("monostatic", "buys", "one-site localization (range + angle, not an ellipse)",
            None, None, "this file §1 what_differs_besides_doppler", "argument",
            "Rb collapses to 2R when TX=RX — verified numerically in §1 M1"),
        row("monostatic", "buys", "RCS layer already covered in this repository",
            None, None, "project memory: sionna2-rcs-methodology; src/rcs_sbr.py is monostatic",
            "repo", "the production RCS path is monostatic; bistatic is restricted to beta <= 45 deg"),
        # --- 모노스태틱이 무는 것 ------------------------------------------- #
        row("monostatic", "costs", "in-band full duplex is structural, not optional",
            freedom["D4_duplexing"]["range_whose_echo_lands_after_one_symbol_m"] / 1e3,
            "km (range whose echo would arrive after one OFDM symbol)",
            "this file §2 D4", "computed",
            "listening in a TDD uplink slot cannot work for targets at drone ranges"),
        row("monostatic", "costs", "self-interference suppression to put residual SI at the echo",
            d5["monostatic"]["100m"]["isolation_for_SI_equal_to_echo_db"], "dB at R = 100 m",
            "this file §2 D5 (repo link budget + repo sigma)", "computed",
            "measured state of the art is 100 dB (Barneto TMTT 2019) -> %.1f dB short"
            % d5["monostatic"]["100m"]["shortfall_vs_barneto_100dB_db"]),
        row("monostatic", "costs", "receiver dynamic range consumed by residual SI",
            d5["barneto"]["adc_bits_for_residual_SI"], "ADC bits",
            "this file §2 D5", "computed",
            "residual SI sits %.1f dB above the noise floor after 100 dB of suppression"
            % d5["barneto"]["residual_SI_above_noise_floor_db"]),
        row("monostatic", "costs", "a transmitter, a licence, and licensed spectrum",
            None, None, "structural", "argument",
            "LaSen's own prototype avoided this by transmitting in the 5.8 GHz unlicensed band"),
        row("monostatic", "costs", "communication resource overhead at the top of the ladder",
            None, None, "LaSen §3.1.1 ('these benefits come at the cost of increased resource "
                        "overhead')", "recorded",
            "no published number; we do not invent one"),
        row("monostatic", "costs", "it is no longer covert — the sensor radiates",
            None, None, "structural", "argument", ""),
        row("monostatic", "costs", "it does not exploit existing infrastructure",
            None, None, "structural", "argument",
            "every sensing site needs a transmit chain; passive rides transmitters already deployed"),
        # --- 패시브가 사는 것 ------------------------------------------------ #
        row("passive", "buys", "no transmitter, no licence, no spectrum, covert",
            None, None, "structural", "argument", ""),
        row("passive", "buys", "rides infrastructure that is already deployed and always on",
            None, None, "outputs/refrate_law.json : illuminators.rows (ambient = True rows)",
            "repo", ""),
        row("passive", "buys", "no self-interference — nothing to cancel that it emitted",
            None, None, "structural", "argument",
            "the interference it does face carries the reference it needs"),
        # --- 패시브가 무는 것 ------------------------------------------------ #
        row("passive", "costs", "PRF_ref is not a design variable at all",
            d2["v_passive_default_ms"], "m/s at the 5G SSB default (20 ms)",
            "this file §2 D1/D2", "computed",
            "best legal cell configuration gives %.2f m/s; the sensor does not choose which"
            % d2["v_passive_best_legal_ms"]),
        row("passive", "costs", "direct-path interference from the illuminator",
            d5["passive_mirror"]["direct_to_echo_ratio_db"], "dB (direct / echo)",
            "this file §2 D5 (repo link budget, repository free-space geometry)", "computed",
            "the literature figure for an outdoor urban geometry is 44-49 dB "
            "(Sharma et al. arXiv:2607.11955, PREPRINT) — a DIFFERENT geometry, not our number"),
        row("passive", "costs", "the data-symbol lane must be bought with demod/remod",
            None, None, "outputs/refrate_law.json : illuminators.rows.nr_recon", "repo",
            "a standard-compliant demodulator plus a reference whose ambiguity function moves "
            "with the traffic"),
        row("passive", "costs", "the deployed SSB periodicity distribution is unmeasured",
            None, None, "outputs/vmax_hardening.json : configuration_dependence.unknown",
            "recorded", "listed there as the number one X410 field-measurement observable"),
    ]

    return dict(
        rows=ledger,
        interference_axis_finding_ko=(
            "⭐ 원장을 세우니 간섭 축에서도 같은 구조가 나왔다. **같은 100 m 표적**에서 모노는 "
            "{a:.1f} dB 격리가 필요하고 패시브는 직접파가 에코보다 {b:.1f} dB 크다 — 차이 {c:.1f} dB 는 "
            "표적거리에 무관하고, 정확히 20log10(4πL/λ)−G_rx, 즉 **패시브 직접파가 베이스라인에서 겪는 "
            "경로손실**이다. 그래서 L 을 줄이면 패시브의 문제가 모노스태틱의 문제로 연속 수렴한다 — "
            "도플러 축의 β=0 절편과 정확히 같은 이야기다(간섭 축에서는 L→0 극한). "
            "성질은 여전히 다르다: 패시브의 간섭은 **전파되어 오는 신호**라 지울 수 있고 그 안에 필요한 "
            "기준이 들어 있다. 모노의 간섭은 **자기 송신기**라 정확히 알지만 프론트엔드를 포화시킨다."
        ).format(a=d5["monostatic"]["100m"]["isolation_for_SI_equal_to_echo_db"],
                 b=[r for r in d5["interference_axis"]["range_independence_check"]
                    if r["R_m"] == 100.0][0]["passive_dnr_db"],
                 c=d5["interference_axis"]["offset_db"]),
        counts=dict(monostatic_buys=sum(1 for r in ledger
                                        if r["side"] == "monostatic" and r["kind"] == "buys"),
                    monostatic_costs=sum(1 for r in ledger
                                         if r["side"] == "monostatic" and r["kind"] == "costs"),
                    passive_buys=sum(1 for r in ledger
                                     if r["side"] == "passive" and r["kind"] == "buys"),
                    passive_costs=sum(1 for r in ledger
                                      if r["side"] == "passive" and r["kind"] == "costs")),
    )


# =========================================================================== #
#  §4  경계 판정 + 우선권 위치
# =========================================================================== #
def sec4_verdict(geom, freedom, prior):
    d2 = freedom["D2_ceiling_test"]
    d7 = freedom["D7_verdict"]
    return dict(
        the_boundary_en=(
            "The wall v_max = lambda*PRF_ref/4 is COMMON to monostatic and passive; monostatic is "
            "its beta = 0 slice, not an exception to it. What differs is WHO CHOOSES PRF_ref. A "
            "passive receiver takes whatever the network broadcasts (5G SSB, %.2f m/s at n78). A "
            "monostatic ISAC sensor picks a rung on a discrete ladder that 3GPP caps at %g Hz for "
            "sub-6 CSI-RS, i.e. %.2f m/s at n78 — a factor of %.1f, not a release. Since %.2f m/s "
            "is below every published airframe maximum (slowest %.1f m/s), NEITHER lane measures a "
            "drone's top speed unambiguously at 3.5 GHz using reference signals alone. The only "
            "escape is the full waveform: free for a monostatic transmitter that knows X[m,n], "
            "purchased with demod/remod for a passive receiver, and traffic-dependent for both."
            % (d2["v_passive_default_ms"], d7["ladder_span_hz"][1], d2["v_monostatic_ceiling_ms"],
               d7["freedom_ratio_v_max"], d2["v_monostatic_ceiling_ms"],
               d2["slowest_airframe_max_ms"])),
        the_boundary_ko=(
            "벽 v_max = λ·PRF_ref/4 는 모노스태틱과 패시브 **공통**이다 — 모노스태틱은 그 벽의 β=0 "
            "절편이지 예외가 아니다. 다른 것은 **누가 PRF_ref 를 고르느냐**다. 패시브는 망이 뿌리는 "
            "것을 받고(5G SSB, n78 에서 {a:.2f} m/s), 모노스태틱은 3GPP 가 sub-6 CSI-RS 에 {c:g} Hz "
            "천장을 건 이산 사다리에서 한 칸을 고른다(n78 에서 {b:.2f} m/s — {r:.1f}배이지 해방이 "
            "아니다). 그리고 {b:.2f} m/s 는 공개된 어떤 기체 최고속도보다도 낮아서(최저 {s:.1f} m/s), "
            "3.5 GHz 에서 기준신호만으로는 **어느 쪽도** 드론의 최고속도를 무모호로 못 잰다. 유일한 "
            "탈출구는 전 파형이고, 그건 X[m,n] 를 아는 모노스태틱 송신기에겐 공짜, 패시브에겐 "
            "복조/재변조라는 유료이며, 양쪽 다 트래픽에 종속된다."
        ).format(a=d2["v_passive_default_ms"], b=d2["v_monostatic_ceiling_ms"],
                 c=d7["ladder_span_hz"][1], r=d7["freedom_ratio_v_max"],
                 s=d2["slowest_airframe_max_ms"]),
        the_reviewer_question=dict(
            question="Why not just do monostatic ISAC instead?",
            answer_ko=("(1) 반복률 벽은 모노스태틱도 못 넘는다 — 천장이 {b:.2f} m/s 다. "
                       "(2) 넘으려면 데이터 심볼이 필요한데 실측 상용망은 시간의 95% 를 RE 점유율 "
                       "7.1% 아래에서 보낸다. "
                       "(3) 그 대가로 인밴드 전이중(100 m 표적 왕복지연이 심볼의 {p:.1%})·"
                       "{i:.0f} dB급 자기간섭 억압·송신기·면허대역·비은밀성을 문다. "
                       "(4) 그러면서 우리가 잃는 것은 '이미 깔린 인프라를 그냥 쓴다'는 패시브의 "
                       "존재 이유 전부다."
                       ).format(b=d2["v_monostatic_ceiling_ms"],
                                p=(2 * 100.0 / C0) / (1.0 / (SCS_KHZ * 1e3)),
                                i=freedom["D5_self_interference"]["monostatic"]["100m"]
                                        ["isolation_for_SI_equal_to_echo_db"]),
            what_we_could_not_answer_before="the boundary had never been worked; §2 works it"),
        headline_is_conservative=geom["M4_headline_parity"]["headline_ko"],
        novelty_position=dict(
            must_stop_claiming=prior["priority_check"]["verdict_for_our_paper"]["must_stop_claiming"],
            can_still_claim=prior["priority_check"]["verdict_for_our_paper"]["can_still_claim"],
            what_this_file_adds=[
                "모노스태틱을 각주에서 **다뤄진 경우**로 올리고, β=0 절편임을 저장소 함수로 재현했다"
                "(§1 M1/M2 — 주장이 아니라 수치).",
                "설계자유도를 **양자화된 사다리 + 규격 천장**으로 정량화했다(§2 D1/D7). 선행 중 "
                "이 비교를 숫자로 한 편은 monostatic_prior 조사에서 못 찾았다.",
                "천장 시험 — 최선의 합법 모노스태틱 반복률이 기체 최고속도를 **못 덮는다**는 판정"
                "(§2 D2). 이것이 리뷰어 질문의 답이다.",
                "자기간섭을 인용이 아니라 **저장소 링크버짓 + 저장소 σ** 로 계산하고, 패시브의 "
                "직접파비와 나란히 놓았다(§2 D5, §3).",
            ],
            priority_holder=dict(
                formula="Chen, Tian, Bai, Wang, Applied Sciences 14(10):4282, 2024 (MDPI, "
                        "published, open access) — same equation, same symbols, two years earlier",
                source="outputs/monostatic_prior.json : priority_check.hits[0]",
                action_required="outputs/refrate_law.json novelty_guard 에 이 항목이 없다 — §5 패치"),
        ),
    )


# =========================================================================== #
#  §5  handoff — refrate_law.py 에 그대로 적용할 패치(우리는 그 파일을 건드리지 않는다)
# =========================================================================== #
def sec5_handoff(geom, freedom):
    m4 = geom["M4_headline_parity"]
    d7 = freedom["D7_verdict"]
    d2 = freedom["D2_ceiling_test"]
    return dict(
        why_a_patch_and_not_an_edit=(
            "benchmark/refrate_law.py 와 outputs/refrate_law.json 은 git 미추적(??) 상태의 "
            "**다른 워크플로 작업물**이다. 동시편집으로 그 라운드를 깨지 않기 위해 여기서는 "
            "패치만 넘긴다. 적용하면 refrate_law.json 에 law.monostatic 이 생기고 "
            "novelty_guard 에 Chen 2024 가 들어간다."),
        patch_1=dict(
            file="benchmark/refrate_law.py",
            where="§1 law dict — `forms` 아래에 형제 키로 `monostatic` 추가",
            anchor='"relation": "바이스태틱은 모노스태틱보다 **관대하다** ...',
            insert_json_block={
                "monostatic": {
                    "status": "TREATED CASE — not a footnote",
                    "form": "v_max = lambda*PRF_ref/(4 cos delta);  = lambda*PRF_ref/4 at delta=0",
                    "why_it_is_the_same_law": (
                        "모노스태틱은 TX=RX 이므로 u1=u2 이고 beta=0 이다. 저장소 fs_params 를 "
                        "TX=RX 로 부르면 beta=0·u1=u2·Rb=2R 이 정확히 나오고 f_d 가 2v/lambda 로 "
                        "떨어진다 (mono_vs_passive.json : L1.M1, %d 기하에서 상대오차 최대 %.2e)."
                        % (geom["M1_collocation_identity"]["n_geometries"],
                           geom["M1_collocation_identity"]["max_rel_err"])),
                    "floor_equality_verified": (
                        "nyquist_gate 이분법으로 찾은 접힘 시작 속도가 모노스태틱과 beta->0 "
                        "바이스태틱에서 %d 개 반복률 전부 lambda*PRF/4 와 일치한다 "
                        "(mono_vs_passive.json : L1.M2)."
                        % len(geom["M2_floor_equality"]["rows"])),
                    "headline_reading": m4["headline_ko"],
                    "design_freedom": (
                        "모노스태틱은 PRF 를 고를 수 있지만 3GPP sub-6 CSI-RS 천장 %g Hz 에 "
                        "묶인다 → n78 에서 %.4g m/s. 패시브 기본값의 %.1f 배이고, 가장 느린 기체 "
                        "최고속도 %.1f m/s 에도 못 미친다 (mono_vs_passive.json : L2)."
                        % (d7["ladder_span_hz"][1], d2["v_monostatic_ceiling_ms"],
                           d7["freedom_ratio_v_max"], d2["slowest_airframe_max_ms"])),
                    "cross_reference": "outputs/mono_vs_passive.json",
                }},
            note="`law.forms.relation` 문장은 그대로 두면 된다 — 이 블록이 그것을 정량화한다."),
        patch_2=dict(
            file="benchmark/refrate_law.py",
            where="§ novelty_guard 리스트 — **맨 앞**에 삽입(우선권이 가장 강한 항목)",
            append_item={
                "claim_we_do_not_make":
                    "v_max = lambda*PRF_ref/(4 cos(beta/2) cos delta) 라는 식이 새롭다",
                "prior": "P. Chen, L. Tian, Y. Bai, J. Wang, 'Rotating Target Detection Using "
                         "Commercial 5G Signal', Applied Sciences (MDPI), vol. 14, no. 10, "
                         "art. 4282, 2024, DOI 10.3390/app14104282 (published, open access)",
                "what_they_already_did":
                    "Eq. (4) f_d = (2v/lambda) cos(beta/2) cos(delta) 를 **같은 기호로** 쓰고, "
                    "CSI-RS 주기 20 ms -> 무모호 도플러 50 Hz -> 0.56 rps 를 실측(실험용 + 상용 "
                    "gNB)까지 붙여 냈다. 패시브 바이스태틱이다. 'The presence of the double base "
                    "angle makes the maximum measurable speed slightly greater than 0.56 rps' "
                    "라고 써서 1/cos(beta/2) 완화(우리 X1 정정)까지 같다.",
                "verification": "outputs/monostatic_prior.json priority_check.hits[0] "
                                "(원문 PDF 대조 기록)",
                "our_position": "식은 우리 것이 아니다. 우리 법칙이 그들의 0.56 rps 를 상대오차 "
                                "3.0e-05 로 재현한다 — 우리는 재현자이지 최초 제기자가 아니다. "
                                "새로 놓는 것은 교차표준 표·설계규칙 역산·인프라 이전 서사·"
                                "검출성능 연결, 그리고 패시브↔모노스태틱 경계(outputs/"
                                "mono_vs_passive.json)다.",
            }),
        patch_3=dict(
            file="benchmark/refrate_law.py",
            where="§ design_levers 리스트 — '망에 PRS 를 요청한다' 항목의 cost 문장 보강",
            replace_cost_with=("측위 세션이므로 더 이상 opportunistic 이 아니다. 그리고 이 레버는 "
                               "모노스태틱 ISAC 의 레버이기도 한데, 그쪽도 3GPP sub-6 CSI-RS "
                               "천장 %g Hz 에서 멈춘다 — n78 에서 %.4g m/s 로 가장 느린 기체 "
                               "최고속도에도 못 미친다(outputs/mono_vs_passive.json : L2.D2)."
                               % (d7["ladder_span_hz"][1], d2["v_monostatic_ceiling_ms"])),
        ),
        do_not_apply_blindly="세 패치 모두 문자열 삽입이다. 적용 후 refrate_law.py 를 다시 실행해 "
                             "refrate_law.json 을 재생성해야 반영된다.",
    )


# =========================================================================== #
#  §6  그림 (텍스트 전부 영어 · 벡터 PDF + 300 dpi PNG)
# =========================================================================== #
def make_figures(refrate, geom, freedom):
    """두 장. 그림 하나 = 질문 하나.

    F1  "모노스태틱은 어디에 있는가" — v_max 대 β. 모노는 β=0 절편이자 하한이다.
    F2  ⭐ "경계" — v_max 대 PRF_ref. 패시브는 고정점, 모노스태틱은 구간, 실기체 속도를 겹친다.

    색: dataviz 검증 슬롯. categorical #2a78d6 / #eb6834 / #1baf7a 는 all-pairs CVD 검사 통과
    (worst deutan ΔE 9.2, normal ΔE 24.0). δ 축은 ordinal 이라 단일 색상 램프
    #86b4e6→#134580(검증 통과: monotone L, ΔL>=0.06, light-end contrast 2.11:1).
    contrast WARN(#1baf7a 2.74:1)은 **직접 라벨**로 구제한다 — 모든 계열에 라벨을 붙인다.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch

    plt.rcParams.update({"font.size": 9, "axes.titlesize": 10.5, "axes.labelsize": 9.5,
                         "legend.fontsize": 8, "xtick.labelsize": 8.5, "ytick.labelsize": 8.5,
                         "figure.dpi": 110, "savefig.dpi": 300, "pdf.fonttype": 42,
                         "axes.grid": True, "grid.alpha": 0.22, "grid.linewidth": 0.5,
                         "axes.spines.top": False, "axes.spines.right": False})
    os.makedirs(OUT_FIG, exist_ok=True)
    figs = {}

    def save(fig, stem, caption):
        png = os.path.join(OUT_FIG, stem + ".png")
        pdf = os.path.join(OUT_FIG, stem + ".pdf")
        fig.savefig(png, bbox_inches="tight", facecolor="white")
        fig.savefig(pdf, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        figs[stem] = dict(png=os.path.relpath(png, _ROOT), pdf=os.path.relpath(pdf, _ROOT),
                          caption=caption)

    C_PAS, C_MONO, C_DATA = "#2a78d6", "#eb6834", "#1baf7a"
    RAMP = ["#86b4e6", "#5490d4", "#2a6cba", "#134580"]
    INK, INK2 = "#0b0b0b", "#52514e"

    lam = LAM_N78
    d1 = freedom["D1_discrete_ladder"]
    d2 = freedom["D2_ceiling_test"]
    d7 = freedom["D7_verdict"]
    v_floor = d2["v_passive_default_ms"]
    v_ceil = d2["v_monostatic_ceiling_ms"]
    prf_ceil = d7["ladder_span_hz"][1]

    # ------------------------------------------------------------------ #
    #  F1  모노스태틱은 β=0 절편이자 하한이다
    # ------------------------------------------------------------------ #
    fig, ax = plt.subplots(figsize=(7.4, 4.9))
    beta = np.linspace(0.0, 120.0, 601)
    DELTAS = (0.0, 10.0, 20.0, 30.0)
    for i, dl in enumerate(DELTAS):
        v = np.array([law_v_max(lam, 50.0, b, dl) for b in beta])
        ax.plot(beta, v, "-", color=RAMP[i], lw=2.0, zorder=3)
    ax.plot([0.0], [v_floor], "o", ms=10, mfc=RAMP[0], mec=INK, mew=1.4, zorder=6)
    ax.annotate("monostatic  ($\\beta$ = 0, $\\delta$ = 0)\n= %.3f m/s = the published headline\n"
                "= the bistatic WORST case" % v_floor,
                xy=(0.0, v_floor), xytext=(9.0, 0.62),
                fontsize=8.4, color=INK, ha="left", va="top",
                arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.1,
                                shrinkA=2, shrinkB=6))
    ax.axhline(v_floor, color=INK2, lw=1.0, ls="--", zorder=1)
    ax.text(118.0, v_floor * 0.94, "floor  $v_{max} = \\lambda\\,\\mathrm{PRF}/4$ = %.3f m/s"
            % v_floor, fontsize=7.8, color=INK2, ha="right", va="top")
    ax.axvspan(0.0, 90.0, color=C_PAS, alpha=0.06, lw=0, zorder=0)
    ax.text(45.0, 0.14, "geometries this project uses ($\\beta \\leq 90\\degree$):  "
                        "median relief x%.3f, max x%.3f"
            % (geom["M3_bistatic_relief"]["scene_statistics_beta_le_90"]["p50"],
               geom["M3_bistatic_relief"]["scene_statistics_beta_le_90"]["max"]),
            fontsize=7.8, color="#1a4f8f", ha="center", va="bottom")
    ax.set_xlim(-3.0, 121.0)
    ax.set_ylim(0.0, 2.9)
    ax.set_xlabel("Bistatic angle  $\\beta$  [deg]")
    ax.set_ylabel("$v_{max}$  [m/s]   (5G NR SSB, 50 Hz, 3.5 GHz)")
    ax.set_title("Monostatic is not an exception to the law — it is its $\\beta$ = 0 floor")
    ax.legend(handles=[Line2D([], [], color=RAMP[i], lw=2.0,
                              label="$\\delta$ = %g$\\degree$" % dl)
                       for i, dl in enumerate(DELTAS)]
                      + [Line2D([], [], color=INK2, lw=1.0, ls="--", label="floor")],
              loc="upper left", frameon=False, ncol=1,
              title="bisector elevation $\\delta$\n(shared by both geometries)",
              title_fontsize=8, alignment="left")
    save(fig, "mono_vs_passive_f1_geometry",
         "Maximum unambiguous radial speed against bistatic angle for the 5G NR SSB reference "
         "rate (50 Hz) at 3.5 GHz. Monostatic sits at beta = 0; with the bisector in the "
         "horizontal plane (delta = 0) it coincides exactly with the bistatic floor "
         "lambda*PRF/4, which is the value this project publishes. Every bistatic geometry with "
         "beta > 0 measures a higher unambiguous speed, so the published headline is the "
         "conservative end of the family, not a geometry-flattered one. The delta family shows "
         "the elevation relief, which monostatic and bistatic share.")

    # ------------------------------------------------------------------ #
    #  F2  ⭐ 경계 — v_max 대 PRF_ref
    # ------------------------------------------------------------------ #
    fig, axes = plt.subplots(1, 2, figsize=(13.2, 5.6),
                             gridspec_kw=dict(width_ratios=[1.32, 1.0], wspace=0.24))
    ax = axes[0]
    prf_ax = np.logspace(np.log10(2.0), np.log10(6.0e4), 400)
    ax.plot(prf_ax, lam * prf_ax / 4.0, "-", color=INK2, lw=1.2, zorder=2)
    ax.text(2.3, 0.037, "$v_{max} = \\lambda\\,\\mathrm{PRF}_{ref}/4$   at 3.5 GHz (n78)",
            fontsize=8.2, color=INK2, ha="left", va="bottom")

    # 실기체 최고속도 띠 + 장면속도
    sp = d2["airframe_speeds_ms"]
    lo_air, hi_air = min(sp.values()), max(sp.values())
    ax.axhspan(lo_air, hi_air, color=INK2, alpha=0.13, lw=0, zorder=0)
    ax.text(2.3, hi_air * 1.15, "published airframe maxima  %.1f - %.0f m/s  (%d aircraft)"
            % (lo_air, hi_air, len(sp)), fontsize=7.8, color=INK, va="bottom", ha="left")
    for v, lab in ((d2["scene_speeds_ms"]["scene_slow"], "scene slow flight 5 m/s"),
                   (d2["scene_speeds_ms"]["scene_fast"], "scene transit 15 m/s")):
        ax.axhline(v, color=INK2, lw=0.9, ls=":", zorder=1)
        ax.text(5.2e4, v * 1.10, lab, fontsize=7.4, color=INK2, ha="right", va="bottom")

    # 패시브 — 고정점(우리가 못 옮긴다)
    pas = d1["passive_ssb"]
    ax.plot([r["prf_hz"] for r in pas], [r["v_max_ms"] for r in pas], "o", ms=7.0,
            mfc="white", mec=C_PAS, mew=1.7, zorder=5)
    dflt = [r for r in pas if r["is_repo_default"]][0]
    ax.plot([dflt["prf_hz"]], [dflt["v_max_ms"]], "o", ms=11.0, mfc=C_PAS, mec=INK, mew=1.3,
            zorder=6)
    ax.annotate("PASSIVE = a FIXED POINT\n5G SSB, 20 ms default: %.3f m/s.\n"
                "The network picks the rung, not the\nsensor. Open circles: %g - %g Hz."
                % (dflt["v_max_ms"], min(r["prf_hz"] for r in pas),
                   max(r["prf_hz"] for r in pas)),
                xy=(dflt["prf_hz"], dflt["v_max_ms"]), xytext=(4.8e2, 0.245),
                fontsize=8.3, color=C_PAS, ha="right", va="top", zorder=7,
                arrowprops=dict(arrowstyle="-|>", color=C_PAS, lw=1.2, shrinkA=2, shrinkB=8))

    # 모노스태틱 — 구간(설계 선택), 500 Hz 천장
    mono = d1["monostatic_csirs"]
    mp = [r["prf_hz"] for r in mono]
    ax.plot(mp, [r["v_max_ms"] for r in mono], "s", ms=5.4, mfc="white", mec=C_MONO, mew=1.5,
            zorder=5)
    seg = np.array(sorted(mp))
    ax.plot(seg, lam * seg / 4.0, "-", color=C_MONO, lw=4.6, alpha=0.32, solid_capstyle="butt",
            zorder=3)
    ax.axvline(prf_ceil, color=C_MONO, lw=1.6, ls="--", zorder=4)
    ax.plot([prf_ceil], [v_ceil], "s", ms=10.5, mfc=C_MONO, mec=INK, mew=1.3, zorder=6)
    ax.annotate("MONOSTATIC = a RANGE the sensor chooses\n"
                "— but a discrete %d-rung ladder, capped by 3GPP\n"
                "at %g Hz for sub-6 CSI-RS: %.2f m/s.\n"
                "x%.1f the passive default, and still below\nevery published airframe maximum."
                % (len(mono), prf_ceil, v_ceil, d7["freedom_ratio_v_max"]),
                xy=(prf_ceil, v_ceil), xytext=(17.0, 90.0),
                fontsize=8.3, color=C_MONO, ha="left", va="bottom",
                arrowprops=dict(arrowstyle="-|>", color=C_MONO, lw=1.2, shrinkA=2, shrinkB=9))

    # 데이터심볼 레인
    full = freedom["D6_data_symbol_lane"]["full_buffer_symbol_rate_hz"]
    v_full = freedom["D6_data_symbol_lane"]["full_buffer_v_max_ms"]
    ax.axvspan(prf_ceil, 6.0e4, color=C_DATA, alpha=0.10, lw=0, zorder=0)
    ax.plot([full], [v_full], "^", ms=10.0, mfc=C_DATA, mec=INK, mew=1.2, zorder=6)
    ax.text(full * 0.72, v_full, "full-buffer ideal\n%.1f kHz $\\rightarrow$ %.0f m/s"
            % (full / 1e3, v_full), fontsize=7.8, color="#0d7a55", ha="right", va="center")
    ax.text(5.2e4, 0.037, "DATA-SYMBOL LANE — monostatic only\n(the receiver must know $X[m,n]$).\n"
                          "Measured commercial traffic: < 5% of time\nabove 7.1% RE utilization.",
            fontsize=8.0, color="#0d7a55", ha="right", va="bottom")

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(2.0, 6.0e4)
    ax.set_ylim(0.03, 1.2e3)
    ax.set_xlabel("Reference repetition rate  $\\mathrm{PRF}_{ref}$  [Hz]")
    ax.set_ylabel("Max unambiguous radial speed  $v_{max}$  [m/s]")
    ax.set_title("(a) The boundary at one carrier (n78, 3.5 GHz): who chooses $\\mathrm{PRF}_{ref}$")
    ax.legend(handles=[
        Line2D([], [], ls="none", marker="o", mfc=C_PAS, mec=INK, ms=9,
               label="passive: fixed point (network's choice)"),
        Line2D([], [], ls="none", marker="o", mfc="white", mec=C_PAS, mew=1.7, ms=8,
               label="other legal SSB periodicities"),
        Line2D([], [], color=C_MONO, lw=4.2, alpha=0.45,
               label="monostatic: design range, capped at %g Hz" % prf_ceil),
        Line2D([], [], ls="none", marker="^", mfc=C_DATA, mec=INK, ms=9,
               label="data-symbol lane (transmitter only)")],
        loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=2, frameon=False,
        handletextpad=0.5, columnspacing=1.4)

    # --- (b) 반송파 축 --------------------------------------------------- #
    ax = axes[1]
    fc_ax = np.logspace(np.log10(0.4e9), np.log10(6.0e9), 300)
    v_pas = C0 / fc_ax * (1000.0 / SSB_DEFAULT_MS) / 4.0
    v_mon = C0 / fc_ax * prf_ceil / 4.0
    prf_low = freedom["D3_carrier_axis"]["scs_dependence"]["rows"]["mu0_15kHz"]["prf_max_hz"]
    v_mon_lo = C0 / fc_ax * prf_low / 4.0
    ax.plot(fc_ax / 1e9, v_pas, "-", color=C_PAS, lw=2.2, zorder=3)
    ax.plot(fc_ax / 1e9, v_mon, "-", color=C_MONO, lw=2.2, zorder=3)
    ax.plot(fc_ax / 1e9, v_mon_lo, "--", color=C_MONO, lw=1.8, dashes=(5, 2.5), zorder=3)
    ax.text(0.43, C0 / 0.43e9 * (1000.0 / SSB_DEFAULT_MS) / 4.0 * 0.72,
            "passive\nSSB 50 Hz", fontsize=8.2, color=C_PAS, ha="left", va="top")
    ax.text(0.43, C0 / 0.43e9 * prf_ceil / 4.0 * 1.30,
            "monostatic ceiling\n%g Hz (30 kHz SCS)" % prf_ceil, fontsize=8.2, color=C_MONO,
            ha="left", va="bottom")
    ax.text(1.02, C0 / 1.02e9 * prf_low / 4.0 * 0.62,
            "%g Hz (15 kHz SCS,\ntypical in low band)" % prf_low, fontsize=8.0, color=C_MONO,
            ha="left", va="top")
    ax.axhspan(lo_air, hi_air, color=INK2, alpha=0.13, lw=0, zorder=0)
    ax.text(5.8, hi_air * 1.20, "airframe maxima", fontsize=7.8, color=INK,
            ha="right", va="bottom")
    for lab, row in freedom["D3_carrier_axis"]["bands"].items():
        f = row["fc_hz"] / 1e9
        ax.axvline(f, color=INK2, lw=0.6, ls=":", alpha=0.6, zorder=1)
        ax.text(f * 1.04, 0.035, lab.split(" ")[0], fontsize=7.4, color=INK2, rotation=90,
                ha="left", va="bottom")
        for v, c in ((row["v_max_passive_ssb50_ms"], C_PAS),
                     (row["v_max_mono_ceiling_ms"], C_MONO)):
            ax.plot([f], [v], "o", ms=6.0, mfc=c, mec="white", mew=1.0, zorder=5)
    f_cross = freedom["D3_carrier_axis"]["fc_max_for_monostatic_ceiling_hz"] / 1e9
    f_cross_lo = freedom["D3_carrier_axis"]["fc_max_for_monostatic_ceiling_15kHz_scs_hz"] / 1e9
    ax.plot([f_cross], [hi_air], "*", ms=16.0, mfc=C_MONO, mec=INK, mew=1.0, zorder=6)
    ax.plot([f_cross_lo], [hi_air], "*", ms=16.0, mfc="white", mec=C_MONO, mew=1.6, zorder=6)
    ax.annotate("the monostatic ceiling clears the fastest\nairframe (%.0f m/s) only below "
                "%.2f GHz —\nand only %.2f GHz if the low band runs\n15 kHz SCS, which leaves "
                "n71 and n28" % (hi_air, f_cross, f_cross_lo),
                xy=(f_cross, hi_air), xytext=(1.95, 1.7e2),
                fontsize=8.0, color=INK, ha="left", va="bottom",
                arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.0, shrinkA=2, shrinkB=9))
    ax.text(0.43, 0.115, "low band buys $v_{max}$ with bandwidth,\nhence with range resolution",
            fontsize=7.8, color=INK2, ha="left", va="bottom")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(0.4, 6.0)
    ax.set_ylim(0.03, 1.2e3)
    ax.set_xticks([0.5, 0.7, 1.0, 2.0, 3.5, 5.0])
    ax.get_xaxis().set_major_formatter(matplotlib.ticker.FixedFormatter(
        ["0.5", "0.7", "1.0", "2.0", "3.5", "5.0"]))
    ax.get_xaxis().set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.set_xlabel("Carrier  $f_c$  [GHz]")
    ax.set_ylabel("$v_{max}$  [m/s]")
    ax.set_title("(b) Can either lane escape by changing band?")
    save(fig, "mono_vs_passive_f2_boundary",
         "(a) Maximum unambiguous radial speed against reference repetition rate at a single "
         "carrier (3.5 GHz), the fair same-carrier comparison. A passive receiver occupies a "
         "FIXED POINT chosen by the network (5G SSB, 20 ms default, filled circle; the open "
         "circles are the other legal ssb-Periodicity values it might be handed). A monostatic "
         "ISAC sensor occupies a RANGE it selects itself, but that range is a discrete ladder of "
         "slot multiples capped by 3GPP at 500 Hz for sub-6 CSI-RS, which lands below every "
         "published airframe maximum. Only the data-symbol lane crosses, and only a transmitter "
         "that knows its own symbols can use it. (b) The same question on the carrier axis: the "
         "monostatic ceiling reaches the fastest airframe only in low band, at the cost of "
         "bandwidth and hence range resolution.")

    return figs


# =========================================================================== #
#  main
# =========================================================================== #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true", help="그림 생략(빠른 확인)")
    args = ap.parse_args()
    t0 = time.time()

    refrate = _load(IN_REFRATE, "기준신호 반복률 법칙")
    harden = _load(IN_HARDEN, "v_max 정정 X1~X6")
    prior = _load(IN_PRIOR, "모노스태틱 선행조사")
    sigma = _load(IN_SIGMA, "mavic4pro sigma grid @3.5 GHz")

    geom = sec1_geometry(refrate, harden)
    freedom = sec2_freedom(refrate, sigma)
    ledger = sec3_ledger(freedom)
    verdict = sec4_verdict(geom, freedom, prior)
    handoff = sec5_handoff(geom, freedom)
    figs = {} if args.smoke else make_figures(refrate, geom, freedom)

    d2 = freedom["D2_ceiling_test"]
    out = dict(
        meta=dict(
            script="benchmark/mono_vs_passive.py",
            generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
            question="패시브와 모노스태틱(LaSen 류)을 둘 다 넣으면 경계는 어디에 그어지는가",
            smoke=bool(args.smoke),
            runtime_s=None,
            carrier_hz=FC_N78, lambda_m=LAM_N78,
            convention="v_max 는 **반쪽 구간**(±) 값 λ·PRF/4 다. Wei(TVT 2023)·I-SCOUT 은 전체 폭 "
                       "규약이라 2배로 나온다 ⟨outputs/monostatic_prior.json meta.convention⟩.",
            repo_functions_used=[
                "freespace_scene.fs_params / target_pos / heading_velocity / look_el_deg",
                "freespace_scene.nyquist_gate / M_from_prf / C0 / FS_TX / FS_RX / FS_SPEED / L_REF",
                "link_budget.LinkBudget / link_terms / lin2db",
                "drones.DRONES",
            ],
            inputs=[os.path.relpath(p, _ROOT) for p in (IN_REFRATE, IN_HARDEN, IN_PRIOR, IN_SIGMA)],
            house_rules="figure text English; prose Korean; every number carries a source; "
                        "citations carry venue + publication status + year",
            does_not_edit=["benchmark/refrate_law.py", "outputs/refrate_law.json",
                           "benchmark/vmax_hardening.py", "outputs/vmax_hardening.json"],
        ),
        headline_ko=verdict["the_boundary_ko"],
        headline_en=verdict["the_boundary_en"],
        one_line_ko=("모노스태틱은 벽의 예외가 아니라 β=0 절편이다. 다른 것은 누가 PRF 를 고르느냐뿐이고, "
                     "그 선택의 폭은 3.5 GHz 에서 {a:.2f} → {b:.2f} m/s({r:.1f}배)로 유한하며, "
                     "그 끝조차 가장 느린 기체 최고속도({s:.1f} m/s)에 못 미친다."
                     ).format(a=d2["v_passive_default_ms"], b=d2["v_monostatic_ceiling_ms"],
                              r=freedom["D7_verdict"]["freedom_ratio_v_max"],
                              s=d2["slowest_airframe_max_ms"]),
        L1_monostatic_as_treated_case=geom,
        L2_design_freedom=freedom,
        L3_cost_ledger=ledger,
        L4_boundary_verdict=verdict,
        L5_refrate_law_handoff=handoff,
        sources=SRC,
        figures=figs,
        figure_palette=dict(
            categorical=["#2a78d6 passive", "#eb6834 monostatic reference-signal",
                         "#1baf7a monostatic data-symbol"],
            ordinal_delta=["#86b4e6", "#5490d4", "#2a6cba", "#134580"],
            validator="dataviz scripts/validate_palette.js",
            categorical_result="light, --pairs all: ALL CHECKS PASS (worst CVD deutan dE 9.2, "
                               "normal dE 24.0); WARN contrast #1baf7a 2.74:1 -> relieved by "
                               "direct labels on every series",
            ordinal_result="light, --ordinal: ALL CHECKS PASS (monotone L, adjacent dL >= 0.06, "
                           "light-end contrast 2.11:1, hue spread 4 deg)"),
        open_questions=[
            "CSI-RS 슬롯 주기 집합의 **중간 단**은 규격 원문에서 확인하지 못했다(SRC.csirs_slot_set). "
            "결론은 양 끝(500 Hz 천장·320 ms 바닥)에만 걸려 있다.",
            "NZP CSI-RS 자원세트를 N 개 엮으면 500 Hz 천장을 넘는가? LaSen 원문은 천장을 500 Hz 로 "
            "쓰면서 자기 실측은 2세트 200 Hz(천장 아래)다 — 총량 상한인지 세트당 상한인지 미해결. "
            "넘는다면 우리 D2 판정이 완화된다(방향: 우리에게 불리).",
            "FR2(mmWave)는 평가하지 않았다. SCS 가 크면 슬롯이 짧아 사다리가 위로 열리지만 λ 가 "
            "짧아져 상쇄된다 — 부호를 계산하지 않았다.",
            "⚠ 어느 밴드가 실제로 어느 numerology 로 배치되는지 확인하지 못했다. 500 Hz 천장은 "
            "30 kHz SCS 의 값이고 15 kHz SCS 면 250 Hz 다 — D3 는 두 경우를 모두 계산해 두었지만, "
            "'저밴드=15 kHz' 는 통념일 뿐 우리가 근거를 갖고 있지 않다. n8(0.9 GHz)의 판정이 이 "
            "가정 하나로 뒤집힌다.",
            "모노스태틱 천장 반복률의 **통신 오버헤드**에 공개 숫자가 없다. LaSen 의 정성문장뿐이라 "
            "원장에 수치를 못 넣었다.",
            "우리 D5 자기간섭 계산은 EIRP 를 격리 기준면으로 삼는다(TX 안테나 이득을 누설경로에 "
            "넣지 않음). 보수/낙관 방향을 정밀화하려면 실제 프론트엔드 모형이 필요하다.",
        ],
        provenance={
            "monostatic == bistatic beta=0 floor":
                "this file §1 M1/M2 — freespace_scene.fs_params(TX=RX) + nyquist_gate bisection",
            "published 1.07 m/s is the monostatic value":
                "outputs/refrate_law.json illuminators.rows.nr_ssb.v_max_ms, reproduced here at "
                "rel err %.1e" % geom["M4_headline_parity"]["rel_err_vs_published"],
            "bistatic relief 1/cos(beta/2)":
                "this file §1 M3; scene statistics from outputs/vmax_hardening.json A_formula",
            "sub-6 CSI-RS ceiling 500 Hz":
                "LaSen (SenSys '26, published) §1 quoting 3GPP TS 38.331 — verbatim from "
                "/data/public/jeong/papers/5G/26_LaSen.pdf",
            "monostatic ceiling v_max %.4g m/s" % d2["v_monostatic_ceiling_ms"]:
                "this file §2 D1; parity with outputs/refrate_law.json illuminators.rows."
                "nr_prs_max (rel err %.1e)"
                % freedom["D1_discrete_ladder"]["ceiling_repo_parity"]["rel_err"],
            "airframe maxima": "src/drones.py DroneSpec.max_speed_ms",
            "scene speeds 5 / 15 m/s": "src/freespace_scene.py FS_SPEED",
            "self-interference budget":
                "benchmark/link_budget.py LinkBudget defaults + outputs/report13_sigma_grid."
                "mavic4pro.json median sigma %.2f dBsm"
                % freedom["D5_self_interference"]["sigma_dbsm"],
            "100 dB measured SI suppression":
                "Barneto et al., IEEE TMTT 67(10):4042-4054, 2019 (published), recorded in "
                "outputs/monostatic_prior.json",
            "traffic sparsity < 5% above 7.1% RE":
                "LaSen (SenSys '26, published) §4.2.1, recorded in outputs/monostatic_prior.json",
            # ⭐ 정정 R1 (docs/RETRACTION_LOG.md) — Chen 귀속은 두 번째 오답이었다.
            "formula priority": "Abratkiewicz et al., IEEE JSTARS 16:3469-3484 (2023), "
                                "eq. (16) p.3476 (published) — identical half-window "
                                "convention. NOT Chen 2024, which prints no closed form "
                                "('PRF' appears 0 times); the earlier Chen attribution is "
                                "RETRACTED. See docs/RETRACTION_LOG.md R1",
        },
    )
    out["meta"]["runtime_s"] = time.time() - t0

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    print("[mono_vs_passive] %s  (%.2f s)" % (os.path.relpath(OUT_JSON, _ROOT),
                                              out["meta"]["runtime_s"]))
    print("  §1 모노스태틱 절편 : collocation rel err max %.2e / floor equality %s"
          % (geom["M1_collocation_identity"]["max_rel_err"],
             "일치" if geom["M2_floor_equality"]["all_match"] else "불일치"))
    print("  §1 헤드라인        : %.5g m/s = 모노값 = 바이스태틱 최악값 (patch parity %s)"
          % (geom["M4_headline_parity"]["monostatic_v_max_ms"],
             "OK" if geom["M4_headline_parity"]["identical"] else "FAIL"))
    print("  §2 자유도          : PRF %g→%g Hz (%d 단) · v_max %.3f→%.3f m/s (×%.1f)"
          % (freedom["D7_verdict"]["ladder_span_hz"][0],
             freedom["D7_verdict"]["ladder_span_hz"][1],
             freedom["D7_verdict"]["freedom_is_quantized_to_n_steps"],
             freedom["D7_verdict"]["ladder_span_v_max_ms"][0],
             freedom["D7_verdict"]["ladder_span_v_max_ms"][1],
             freedom["D7_verdict"]["freedom_ratio_v_max"]))
    print("  §2 천장 시험       : 기체 %s 커버 · 장면 5 m/s %s · 15 m/s %s"
          % (d2["airframes_covered_by_monostatic_ceiling"],
             "O" if d2["coverage"]["scene_slow"]["monostatic_ceiling_covers"] else "X",
             "O" if d2["coverage"]["scene_fast"]["monostatic_ceiling_covers"] else "X"))
    print("  §3 원장            : mono %d사고/%d무름 · passive %d사고/%d무름"
          % (ledger["counts"]["monostatic_buys"], ledger["counts"]["monostatic_costs"],
             ledger["counts"]["passive_buys"], ledger["counts"]["passive_costs"]))
    for k, v in figs.items():
        print("  fig %s" % v["png"])


if __name__ == "__main__":
    main()
