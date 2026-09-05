# -*- coding: utf-8 -*-
"""refrate_law.py — **기준신호 반복률 법칙**: 패시브 바이스태틱의 무모호 반경속도를 일반화한다
====================================================================================================

■ 이 스크립트가 확정하는 것

    패시브 바이스태틱 수신기가 모호 없이 잴 수 있는 표적 반경속도의 상한은
    **상시 기준신호의 반복률**이 정한다.

        v_max(β, δ) = λ · PRF_ref / (4 · cos(β/2) · cos δ)      [바이스태틱 일반형]
        v_max       = λ · PRF_ref / 4                            [β=0, δ=0 — 하한(worst case)
                                                                  이자 모노스태틱 등가형]

    유도 사슬은 **규격 → 산술 → 나이퀴스트 → 운동학** 뿐이다. σ(RCS)가 한 번도 안 들어간다.

■ 왜 이 형태여야 하는가
  · CPI 를 늘리면 도플러 **빈폭**(1/T)이 좁아진다. 무모호 구간(±PRF/2)은 그대로다.
    즉 이 한계는 **표본화율**의 성질이지 적분시간의 성질이 아니다(cpi_guard_sweep §s2 가 실측).
  · 그래서 이 값은 "5G 가 나쁘다" 가 아니라 **"기준신호가 몇 Hz 로 오느냐"** 의 함수다.
    같은 5G 라도 PRS(200 Hz)면 4.28 m/s 가 되고, WiFi 도 비콘(9.77 Hz)만 쓰면 0.14 m/s 다.

■ 계산하지 않고 **저장소 함수를 부른다**(재구현 금지)
    freespace_scene.fs_params / target_pos / heading_velocity / folded_doppler / nyquist_gate
    freespace_scene.prf_hz / doppler_bin_hz / look_el_deg / M_from_prf
    waveforms.all_waveforms · waveforms.PILOT_RATE_HZ      (λ·PRF·기준신호 이름의 단일 출처)
    drones.DRONES                                          (기체 최고속도의 단일 출처)
  닫힌형(λ·PRF/4)은 **저장소 함수 출력과 수치로 대조**해서만 채택한다(§1 verification).

■ 산출
    outputs/refrate_law.json
    outputs/figures/refrate_law_f{1,2,3}_*.{png,pdf}    (그림 텍스트 전부 영어)

실행:  cd sionna2 && PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/refrate_law.py
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
from waveforms import all_waveforms, PILOT_RATE_HZ          # noqa: E402

C0 = fss.C0
OUT_JSON = os.path.join(_ROOT, "outputs", "refrate_law.json")
OUT_FIG = os.path.join(_ROOT, "outputs", "figures")
CPI_JSON = os.path.join(_ROOT, "outputs", "cpi_guard_sweep.json")


# =========================================================================== #
#  0. 출처 원장 — 반복률 하나마다 규격 조항 또는 인용 측정을 붙인다
#     ⭐ 출처 없는 숫자는 이 표에 못 들어온다. verification 등급을 함께 적는다:
#        "spec_clause"  규격 조항을 직접 지목(조항 번호 + 문장)
#        "spec_derived" 규격 수치들로부터의 산술(식을 함께 적는다)
#        "repo"         저장소 상수(단일 진리원 파일:심볼)
#        "literature"   게재 논문의 문장
#        "convention"   트래픽/설정 의존이라 규격이 정하지 않는 자유 파라미터
# =========================================================================== #
SRC = {
    "nr_ssb": dict(
        doc="3GPP TS 38.213", clause="§4.1 (Cell search)",
        text=("For initial cell selection a UE may assume that half frames with SS/PBCH blocks "
              "occur with a periodicity of 2 frames = 20 ms."),
        derived="T_SSB = 20 ms  ->  PRF = 1/0.020 = 50 Hz",
        configurable=("TS 38.331 ssb-PeriodicityServingCell in {5,10,20,40,80,160} ms "
                      "-> 200 ... 6.25 Hz after cell access"),
        verification="spec_clause",
        url="https://www.3gpp.org/ftp/Specs/archive/38_series/38.213/"),
    "nr_prs": dict(
        doc="3GPP TS 38.211", clause="§7.4.1.7.4 (DL-PRS-Periodicity)",
        text=("DL-PRS periodicity is configured in slots; the SCS-dependent sets start at "
              "{5,10,20,20} slots for 15/30/60/120 kHz, with {4,8,16,32,64} slots additionally "
              "supported for consistency with CSI-RS."),
        derived=("mu=1 (30 kHz SCS, slot 0.5 ms): 4 slots = 2 ms -> 500 Hz ceiling; "
                 "the repository uses the typical positioning-session value 200 Hz"),
        configurable="positioning session only — not an ambient always-on signal",
        verification="spec_clause",
        url="https://www.3gpp.org/ftp/Specs/archive/38_series/38.211/"),
    "lte_crs": dict(
        doc="3GPP TS 36.211", clause="§6.10.1 (Cell-specific reference signals)",
        text=("Cell-specific reference signals shall be transmitted in all downlink subframes in "
              "a cell supporting PDSCH transmission; for antenna port 0 they occupy OFDM symbols "
              "0 and N_symb-3 of every slot."),
        derived=("subframe = 1 ms  ->  PRF = 1000 Hz (repository convention: one slow-time "
                 "sample per subframe). Per-CRS-symbol sampling would give 4 symbols/subframe "
                 "= 4000 Hz — a x4 headroom the receiver may claim, see design_rule.headroom"),
        configurable="none — CRS is mandatory and always on",
        verification="spec_clause",
        url="https://www.3gpp.org/ftp/Specs/archive/36_series/36.211/"),
    "lte_prs": dict(
        doc="3GPP TS 36.211", clause="§6.10.4.3 (PRS subframe configuration)",
        text="T_PRS is one of {160, 320, 640, 1280} subframes, selected by the PRS configuration index I_PRS.",
        derived="min T_PRS = 160 subframes = 160 ms  ->  PRF = 6.25 Hz",
        configurable="positioning session only — not ambient",
        verification="spec_clause",
        url="https://www.3gpp.org/ftp/Specs/archive/36_series/36.211/"),
    "wifi_vhtltf": dict(
        doc="IEEE Std 802.11", clause="Clause 21 (VHT PHY), VHT-LTF field of the VHT PPDU",
        text=("The VHT-LTF is transmitted once per VHT PPDU. Its repetition rate is therefore the "
              "PPDU (packet) rate, which the standard does not fix — it is traffic dependent."),
        derived="PRF = packet rate. Repository default 1000 Hz = congested-AP representative value.",
        configurable="first-class sensitivity axis {10, 100, 1000, 5000} Hz (PAPER_SPEC F9)",
        verification="convention",
        url="https://standards.ieee.org/ieee/802.11/7028/"),
    "wifi_beacon": dict(
        doc="IEEE Std 802.11", clause="Beacon interval / aBeaconPeriod, TU = 1024 us",
        text=("The beacon interval defaults to 100 TU and one TU is 1024 us, so beacons are "
              "transmitted every 102.4 ms."),
        derived="T = 100 x 1024 us = 102.4 ms  ->  PRF = 9.7656 Hz",
        configurable="AP-settable; 100 TU is the near-universal default",
        verification="spec_derived",
        url="https://standards.ieee.org/ieee/802.11/7028/"),
    "dvbt_continual": dict(
        doc="ETSI EN 300 744", clause="§4.1 (OFDM parameters), §4.5 (pilot insertion)",
        text=("8K mode on an 8 MHz channel: elementary period T = 7/64 us, useful symbol part "
              "Tu = 8192 T = 896 us; guard 1/4 adds 224 us. Continual pilots are present in every "
              "OFDM symbol; scattered pilots repeat with a period of 4 symbols."),
        derived="Ts = 896 + 224 = 1120 us  ->  continual-pilot PRF = 892.9 Hz",
        configurable="2K mode Tu = 224 us; guard 1/8, 1/16, 1/32 shorten Ts",
        verification="spec_derived",
        url="https://www.etsi.org/deliver/etsi_en/300700_300799/300744/01.06.02_60/en_300744v010602p.pdf"),
    "dvbt_scattered": dict(
        doc="ETSI EN 300 744", clause="§4.5.3 (Scattered pilot cells)",
        text="Each continual pilot coincides with a scattered pilot every fourth symbol.",
        derived="4 x Ts = 4.48 ms  ->  scattered-pilot PRF = 223.2 Hz (8K, guard 1/4)",
        configurable="same guard-interval dependence as the continual-pilot row",
        verification="spec_derived",
        url="https://www.etsi.org/deliver/etsi_en/300700_300799/300744/01.06.02_60/en_300744v010602p.pdf"),
    "dab_phaseref": dict(
        doc="ETSI EN 300 401", clause="§14 (Transmission signal structure), Transmission mode I",
        text="The transmitted signal is organised in frames of 96 ms duration (Transmission mode I).",
        derived="one null + phase-reference symbol per 96 ms frame  ->  PRF = 10.417 Hz",
        configurable="modes II/III/IV shorten the frame to 24/24/48 ms",
        verification="spec_derived",
        url="https://www.etsi.org/deliver/etsi_en/300400_300499/300401/02.01.01_60/en_300401v020101p.pdf"),
    "dtmb_pn420": dict(
        doc="GB 20600-2006 (DTMB)", clause="signal frame = PN frame header + 3780-symbol frame body",
        text=("PN420 frame header consists of 420 symbols with a total duration of 55.56 us; the "
              "frame body is 3780 symbols at 7.56 Msymbol/s = 500 us; one signal frame is 555.6 us "
              "in PN420 + C3780 mode."),
        derived="T_frame = 555.56 us  ->  PRF = 1800 Hz",
        configurable="PN945 header (125 us) gives 625 us -> 1600 Hz",
        verification="literature",
        cite=("Y. Zhao et al., 'Joint suppression method for range-Doppler ambiguity sidelobes in "
              "DTMB-based passive bistatic radar', Sci. Rep. 14, 2024, DOI 10.1038/s41598-024-82020-7 "
              "— quotes the frame-header durations and the 666 MHz carrier used in trials."),
        url="https://www.nature.com/articles/s41598-024-82020-7"),
    "dtmb_pn945": dict(
        doc="GB 20600-2006 (DTMB)", clause="signal frame, PN945 header mode",
        text="PN945 frame header consists of 945 symbols with a duration of 125 us.",
        derived="T_frame = 125 + 500 = 625 us  ->  PRF = 1600 Hz",
        configurable="PN420 mode gives 1800 Hz",
        verification="literature",
        cite="same Sci. Rep. 14 (2024) source as dtmb_pn420",
        url="https://www.nature.com/articles/s41598-024-82020-7"),
    "fm_analog": dict(
        doc="analogue FM broadcast (ITU-R BS.450)", clause="continuous transmission — no frame structure",
        text=("Analogue FM has no repeating reference structure. The passive receiver's reference is "
              "the continuously sampled direct signal, so the slow-time rate is the CAF batch rate "
              "1/T_batch chosen by the receiver designer, not by the transmitter."),
        derived="PRF = 1/T_batch (receiver-chosen). At T_batch = 1 ms, PRF = 1000 Hz.",
        configurable="receiver design parameter",
        verification="literature",
        cite=("P. E. Howland, D. Maksimiuk, G. Reitsma, 'FM radio based bistatic radar', "
              "IEE Proc. Radar Sonar Navig. 152(3):107-115, 2005 — the canonical FM PBR reference."),
        url=""),
    "reconstructed": dict(
        doc="(receiver architecture, not a signal specification)",
        clause="demodulate-and-remodulate reference reconstruction",
        text=("If the receiver demodulates the illuminator's data and rebuilds the full transmitted "
              "waveform, the reference becomes continuous and the repetition limit disappears — the "
              "slow-time rate is again the batch rate 1/T_batch."),
        derived="PRF = 1/T_batch (receiver-chosen)",
        configurable="costs a full standard-compliant demodulator per illuminator",
        verification="convention", url=""),
}

# --------------------------------------------------------------------------- #
#  반송파 원장 — λ 가 v_max 에 직접 들어가므로 반복률과 같은 등급으로 출처를 붙인다
# --------------------------------------------------------------------------- #
FC_SRC = {
    3.500e9: dict(text="5G NR band n78 mid-band (3.3-3.8 GHz)",
                  source="src/waveforms.py : nr_downlink(carrier_hz=3.5e9) — 저장소 단일 진리원",
                  verification="repo"),
    1.843e9: dict(text="LTE band 3 downlink (1805-1880 MHz)",
                  source="src/waveforms.py : lte_downlink(carrier_hz=1.843e9)",
                  verification="repo"),
    5.210e9: dict(text="802.11ac 80 MHz channel 42, U-NII-1, centre 5.210 GHz",
                  source="src/waveforms.py : wifi_80211ac(carrier_hz=5.21e9)",
                  verification="repo"),
    2.437e9: dict(text="802.11 2.4 GHz channel 6 centre frequency 2.437 GHz",
                  source="IEEE Std 802.11 channel plan", verification="spec_derived"),
    0.600e9: dict(text="DVB-T UHF band IV/V (470-694 MHz); 600 MHz taken as representative",
                  source="ETSI EN 300 744 operating bands", verification="representative"),
    0.666e9: dict(text="DTMB trial carrier 666 MHz",
                  source=("Sci. Rep. 14 (2024) DTMB PBR paper: 'operating at a frequency of "
                          "666 MHz'; DTMB band is 470-860 MHz"),
                  verification="literature"),
    0.220e9: dict(text="DAB VHF band III (174-240 MHz); 220 MHz taken as representative",
                  source="ETSI EN 300 401 operating bands", verification="representative"),
    0.100e9: dict(text="FM broadcast band 87.5-108 MHz; 100 MHz taken as representative",
                  source="ITU-R BS.450 FM band", verification="representative"),
}

# --------------------------------------------------------------------------- #
#  조명원 표 — (반복률, 반송파) 는 전부 위 SRC 원장 또는 저장소 상수에서 온다
#  ambient=True  : 트래픽이 없어도 항상 존재하는 신호(패시브가 의지할 수 있는 것)
#  continuous=True: 반복 구조가 없어 반복률 상한이 수신기 설계로 넘어가는 신호
# --------------------------------------------------------------------------- #
ILLUM = [
    # key,           label,                    family, src key,       PRF[Hz], fc[Hz],     ambient, continuous
    ("nr_ssb",       "5G NR SSB",              "cellular", "nr_ssb",       50.0, 3.500e9,  True,  False),
    ("nr_prs",       "5G NR PRS (session)",    "cellular", "nr_prs",      200.0, 3.500e9,  False, False),
    ("nr_prs_max",   "5G NR PRS (4-slot min)", "cellular", "nr_prs",      500.0, 3.500e9,  False, False),
    ("lte_crs",      "LTE CRS",                "cellular", "lte_crs",    1000.0, 1.843e9,  True,  False),
    ("lte_crs_sym",  "LTE CRS (per-symbol)",   "cellular", "lte_crs",    4000.0, 1.843e9,  True,  False),
    ("lte_prs",      "LTE PRS (session)",      "cellular", "lte_prs",       6.25, 1.843e9, False, False),
    ("wifi_vhtltf",  "WiFi VHT-LTF @1 kHz",    "wlan",     "wifi_vhtltf",1000.0, 5.210e9,  True,  False),
    ("wifi_vhtltf_lo", "WiFi VHT-LTF @10 Hz",  "wlan",     "wifi_vhtltf",  10.0, 5.210e9,  True,  False),
    ("wifi_beacon",  "WiFi beacon (5 GHz)",    "wlan",     "wifi_beacon",   1000.0 / 102.4, 5.210e9, True, False),
    ("wifi_beacon24", "WiFi beacon (2.4 GHz)", "wlan",     "wifi_beacon",   1000.0 / 102.4, 2.437e9, True, False),
    # DVB-T 8K: T = 7/64 us, Tu = 8192 T, guard 1/4 = 2048 T  ->  Ts = 10240 T = 1120 us
    ("dvbt_scattered", "DVB-T scattered pilots", "broadcast", "dvbt_scattered", 1.0 / (4 * 10240 * 7 / 64e6), 0.600e9, True, False),
    ("dvbt_continual", "DVB-T continual pilots", "broadcast", "dvbt_continual", 1.0 / (10240 * 7 / 64e6), 0.600e9, True, False),
    ("dab_phaseref", "DAB phase-ref symbol",   "broadcast", "dab_phaseref", 1000.0 / 96.0, 0.220e9, True, False),
    # DTMB: symbol rate 7.56 Msym/s; frame = PN header symbols + 3780-symbol body
    ("dtmb_pn420",   "DTMB frame (PN420)",     "broadcast", "dtmb_pn420",  7.56e6 / (420 + 3780), 0.666e9, True, False),
    ("dtmb_pn945",   "DTMB frame (PN945)",     "broadcast", "dtmb_pn945",  7.56e6 / (945 + 3780), 0.666e9, True, False),
    ("fm_batch1ms",  "FM (1 ms batch)",        "broadcast", "fm_analog",  1000.0, 0.100e9,  True,  True),
    ("fm_batch10ms", "FM (10 ms batch)",       "broadcast", "fm_analog",   100.0, 0.100e9,  True,  True),
    ("nr_recon",     "5G full-waveform (1 ms batch)", "cellular", "reconstructed", 1000.0, 3.500e9, False, True),
]

# 저장소 정본과 반드시 일치해야 하는 세 행(파형 모듈이 단일 진리원)
REPO_PARITY = {"nr_ssb": ("nr", "G1"), "lte_crs": ("lte", "G1"), "wifi_vhtltf": ("wifi", "G1")}

# 그림 라벨 충돌을 없애는 짧은 코드(그림 안에서만 쓴다 — JSON 은 긴 이름이 정본)
SHORT = {
    "nr_ssb": "SSB", "nr_prs": "PRS-NR", "nr_prs_max": "PRS-NR max", "lte_crs": "CRS",
    "lte_crs_sym": "CRS/sym", "lte_prs": "PRS-LTE", "wifi_vhtltf": "VHT-LTF 1k",
    "wifi_vhtltf_lo": "VHT-LTF 10", "wifi_beacon": "BCN 5G", "wifi_beacon24": "BCN 2.4G",
    "dvbt_scattered": "DVB-T sp", "dvbt_continual": "DVB-T cp", "dab_phaseref": "DAB",
    "dtmb_pn420": "DTMB 420", "dtmb_pn945": "DTMB 945",
    "fm_batch1ms": "FM 1 ms", "fm_batch10ms": "FM 10 ms", "nr_recon": "5G recon",
}

# --------------------------------------------------------------------------- #
#  드론 속도축 — 게재 스펙만 넣는다. 게재가 없으면 null 로 둔다(발명 금지).
#  normal_mode_ms: 제조사가 "Normal/positioning 모드 최대 수평속도" 로 공표한 값
# --------------------------------------------------------------------------- #
DRONE_SPEED_PUB = {
    "mavic4pro": dict(normal_mode_ms=6.0, tracking_ms=15.0,
                      source="DJI Mavic 4 Pro specification sheet: max horizontal speed 25 m/s "
                             "(Sport), 6 m/s (Normal, not tracking), 15 m/s (tracking), 6 m/s (Cine)",
                      verification="spec_sheet"),
    "phantom4":  dict(normal_mode_ms=14.0, tracking_ms=None,
                      source="DJI Phantom 4 Pro specification: 20 m/s in S-mode, 14 m/s in P-mode. "
                             "WARNING the P-mode figure is the Phantom 4 **Pro** sheet; the original "
                             "Phantom 4 publishes only the 20 m/s Sport figure",
                      verification="spec_sheet_adjacent_model"),
    "mini5pro":  dict(normal_mode_ms=None, tracking_ms=None,
                      source="DJI publishes 19 m/s Sport (Plus battery) / 18 m/s (standard battery); "
                             "no Normal-mode horizontal speed is published",
                      verification="not_published"),
    "matrice4e": dict(normal_mode_ms=None, tracking_ms=None,
                      source="DJI publishes 21 m/s forward / 18 backward / 19 lateral; no mode split",
                      verification="not_published"),
    "typhoonh480": dict(normal_mode_ms=None, tracking_ms=None,
                        source="Yuneec publishes 13.5 m/s (30 mph) in Angle mode; no further split",
                        verification="not_published"),
    "s1000plus": dict(normal_mode_ms=None, tracking_ms=None,
                      source="DJI publishes no max speed for the S1000+ airframe",
                      verification="not_published"),
    "x500v2":    dict(normal_mode_ms=None, tracking_ms=None,
                      source="airframe kit — speed depends on the build; nothing published",
                      verification="not_published"),
}

# 저장소 장면 규약(모든 검출 결과가 실제로 계산된 속도) — 여기가 '전형 순항'의 단일 출처다
SCENE_SPEEDS = {"scene_slow_ms": float(fss.FS_SPEED[0]), "scene_fast_ms": float(fss.FS_SPEED[1])}

HOVER_CAVEAT = ("v=0 은 모호가 없지만 검출도 없다 — f_d=0 이라 0-도플러 가드가 지운다. 이 법칙은 "
                "빠른 표적의 상한을 정할 뿐 호버를 구제하지 않는다. 호버는 반복률과 무관하게 모든 "
                "조명원에서 블라인드다 ⟨outputs/cpi_guard_sweep.json : speed_sweep.0.1.*[speed_ms=0] "
                "→ blind_hard = 1.0⟩.")


# =========================================================================== #
#  §1  법칙 — 유도와 수치 검증
# =========================================================================== #
def law_v_max(lam, prf, beta_deg=0.0, delta_deg=0.0):
    """닫힌형 v_max [m/s] = λ·PRF / (4·cos(β/2)·cos δ).  β=δ=0 이면 λ·PRF/4."""
    b = math.radians(float(beta_deg))
    d = math.radians(float(delta_deg))
    denom = 4.0 * math.cos(b / 2.0) * math.cos(d)
    return float(lam) * float(prf) / max(denom, 1e-12)


def verify_law(n_psi=2880, seed=7):
    """닫힌형을 **저장소 함수 출력**과 대조한다 — 세 가지를 각각 검증한다.

    V1 기하인자   : max_ψ |f_d(ψ)| 가 (2v/λ)·cos(β/2)·cos(el) 과 같은가
                    (f_d 는 fs_params, el 은 look_el_deg — 둘 다 저장소 함수)
    V2 나이퀴스트 : v = v_max·(1∓ε) 에서 nyquist_gate 가 접힘 없음/있음으로 갈리는가
    V3 CPI 무관   : 같은 v·PRF 에서 접힘비율이 CPI 로 안 변하는가(적분시간이 아니라 표본화율)
    """
    rng = np.random.default_rng(seed)
    psi = np.linspace(0.0, 360.0, int(n_psi), endpoint=False)
    lam = C0 / 3.5e9
    v = 5.0

    # --- V1: 여러 기하에서 닫힌형 대 저장소 -------------------------------- #
    rows = []
    for _ in range(200):
        L = float(rng.uniform(50.0, 2000.0))
        d = float(rng.uniform(60.0, 5000.0))
        phi = float(rng.uniform(0.0, 360.0))
        alt = float(rng.uniform(20.0, 300.0))
        tgt = fss.target_pos(d, phi, L, alt)
        p = fss.fs_params(fss.FS_TX, fss.FS_RX(L), tgt, (0.0, 0.0, 0.0), C0 / lam)
        V = fss.heading_velocity(psi, v)                       # (N,3), 수평비행
        fd = (V @ (p["u1"] + p["u2"])) / lam                   # 저장소 식 그대로
        fd_max_repo = float(np.max(np.abs(fd)))
        beta = float(p["beta"])
        el = fss.look_el_deg(p["u1"], p["u2"])
        fd_max_closed = (2.0 * v / lam) * math.cos(math.radians(beta) / 2.0) * math.cos(math.radians(el))
        rows.append(dict(L_m=L, d_m=d, phi_deg=phi, alt_m=alt, beta_deg=beta, el_deg=el,
                         fd_max_repo_hz=fd_max_repo, fd_max_closed_hz=fd_max_closed,
                         rel_err=abs(fd_max_repo - fd_max_closed) / max(abs(fd_max_closed), 1e-12)))
    rel = np.array([r["rel_err"] for r in rows])
    v1 = dict(n_geometries=len(rows), max_rel_err=float(rel.max()), median_rel_err=float(np.median(rel)),
              psi_grid=int(n_psi),
              note=("잔차는 ψ 격자 양자화(1/{n} 회전)뿐이다 — 닫힌형은 max_ψ 를 정확히, 격자는 근사로 "
                    "잡는다").format(n=n_psi),
              beta_range_deg=[float(min(r["beta_deg"] for r in rows)),
                              float(max(r["beta_deg"] for r in rows))],
              worst=max(rows, key=lambda r: r["rel_err"]))

    # --- V2: 접힘이 **시작되는 속도**를 이분법으로 찾아 닫힌형과 맞댄다 ------ #
    #  β=0·el=0 을 만들려면 표적이 TX·RX 와 같은 높이에서 아주 멀리 있어야 한다.
    L = 500.0
    d = 3.0e6                                   # β→0 극한
    tgt = fss.target_pos(d, 0.0, L, fss.FS_TX[2])
    p = fss.fs_params(fss.FS_TX, fss.FS_RX(L), tgt, (0.0, 0.0, 0.0), C0 / lam)
    beta0 = float(p["beta"])
    el0 = fss.look_el_deg(p["u1"], p["u2"])
    uu = p["u1"] + p["u2"]

    def _alias_frac(v, prf):
        fd = (fss.heading_velocity(psi, float(v)) @ uu) / lam
        return float(np.mean(~np.asarray(fss.nyquist_gate(fd, prf))))

    v2 = []
    for prf in (9.765625, 50.0, 200.0, 1000.0, 1800.0):
        vmax = law_v_max(lam, prf, 0.0, 0.0)
        lo, hi = 1e-6, vmax * 4.0                      # alias(lo)=0, alias(hi)>0
        for _ in range(80):                            # 이분법 — 첫 접힘 속도
            mid = 0.5 * (lo + hi)
            if _alias_frac(mid, prf) > 0.0:
                hi = mid
            else:
                lo = mid
        v_onset = 0.5 * (lo + hi)
        v2.append(dict(
            prf_hz=prf, v_max_closed_ms=vmax, beta_deg=beta0, el_deg=el0,
            v_alias_onset_ms=float(v_onset),
            rel_err=float(abs(v_onset - vmax) / vmax),
            alias_frac_at_0p98=_alias_frac(vmax * 0.98, prf),
            alias_frac_at_1p02=_alias_frac(vmax * 1.02, prf),
            alias_frac_at_2p00=_alias_frac(vmax * 2.00, prf),
            note=("첫 접힘은 δ=0 헤딩에서만 일어난다 — 그래서 v_max 를 갓 넘기면 접힘 헤딩 비율이 "
                  "0 에서 작은 값으로 열린다. v_max 는 '전부 접힌다' 가 아니라 '접히기 시작한다' 다.")))

    # --- V3: CPI 무관성 ---------------------------------------------------- #
    v3 = []
    tgt = fss.target_pos(1000.0, 90.0, fss.L_REF, fss.FS_ALT[0])
    p = fss.fs_params(fss.FS_TX, fss.FS_RX(fss.L_REF), tgt, (0.0, 0.0, 0.0), C0 / lam)
    V = fss.heading_velocity(psi, 5.0)
    fd = (V @ (p["u1"] + p["u2"])) / lam
    for T in (0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0):
        prf = 50.0
        M = fss.M_from_prf(T, prf)
        v3.append(dict(T_cpi_s=T, M=int(M), prf_hz=prf,
                       doppler_bin_hz=float(fss.doppler_bin_hz(T, prf, M)),
                       alias_frac=float(np.mean(~np.asarray(fss.nyquist_gate(fd, prf))))))
    alias_set = sorted({round(r["alias_frac"], 12) for r in v3})

    return dict(
        V1_geometry_factor=v1,
        V2_nyquist_threshold=v2,
        V3_cpi_independence=dict(rows=v3, distinct_alias_fracs=alias_set,
                                 bin_hz_span=[v3[0]["doppler_bin_hz"], v3[-1]["doppler_bin_hz"]],
                                 verdict=("도플러 빈폭은 {a:g}→{b:g} Hz 로 {r:g}배 변하는데 접힘비율은 "
                                          "{n}개 값 중 1개뿐이다").format(
                                     a=v3[0]["doppler_bin_hz"], b=v3[-1]["doppler_bin_hz"],
                                     r=v3[0]["doppler_bin_hz"] / v3[-1]["doppler_bin_hz"],
                                     n=len(v3)) if len(alias_set) == 1 else "CPI 의존 발견 — 재검토"),
    )


def repo_parity(illum_rows):
    """저장소 파형 모듈·cpi_guard_sweep.json 과 세 행이 정확히 일치하는지 대조한다."""
    ws = all_waveforms("G1")
    out = {}
    for key, (std, mode) in REPO_PARITY.items():
        row = illum_rows[key]
        w = ws[std]
        prf_repo = fss.prf_hz(std, mode)
        out[key] = dict(
            table_prf_hz=row["prf_hz"], repo_prf_hz=float(prf_repo),
            prf_match=bool(abs(row["prf_hz"] - prf_repo) < 1e-9),
            table_fc_hz=row["fc_hz"], repo_fc_hz=float(w.carrier_hz),
            fc_match=bool(abs(row["fc_hz"] - w.carrier_hz) < 1.0),
            table_v_max_ms=row["v_max_ms"], repo_v_unambiguous_ms=float(w.v_unambiguous_ms),
            v_match_rel=float(abs(row["v_max_ms"] - w.v_unambiguous_ms) / max(w.v_unambiguous_ms, 1e-12)),
            repo_ref_name=w.ref_name, repo_ref_bw_hz=float(w.ref_bw_hz))
    # cpi_guard_sweep 과의 대조(있으면)
    if os.path.exists(CPI_JSON):
        cg = json.load(open(CPI_JSON, encoding="utf-8"))
        us = cg.get("unambiguous_speed", {})
        m = {"nr_ssb": "G1", "lte_crs": "L1", "wifi_vhtltf": "W1"}
        for key, mode in m.items():
            if mode in us:
                out[key]["cpi_guard_v_mono_equiv_ms"] = us[mode]["v_unambiguous_mono_equiv_ms"]
                out[key]["cpi_guard_v_bistatic_ms"] = us[mode]["v_unambiguous_ms"]
                out[key]["cpi_guard_match_rel"] = float(
                    abs(illum_rows[key]["v_max_ms"] - us[mode]["v_unambiguous_mono_equiv_ms"])
                    / max(us[mode]["v_unambiguous_mono_equiv_ms"], 1e-12))
    out["all_match"] = all(v["prf_match"] and v["fc_match"] and v["v_match_rel"] < 1e-9
                           for k, v in out.items() if isinstance(v, dict))
    return out


# =========================================================================== #
#  §2  조명원 표
# =========================================================================== #
def build_illuminator_table():
    rows = {}
    for key, label, family, srckey, prf, fc, ambient, continuous in ILLUM:
        lam = C0 / fc
        rows[key] = dict(
            key=key, label=label, family=family, prf_hz=float(prf), fc_hz=float(fc),
            lambda_m=float(lam),
            v_max_ms=law_v_max(lam, prf),
            v_max_kmh=law_v_max(lam, prf) * 3.6,
            f_d_per_ms_hz=2.0 / lam,                     # β=0 에서 1 m/s 당 도플러[Hz]
            ref_period_ms=1000.0 / prf,
            ambient=bool(ambient), continuous_reference=bool(continuous),
            prf_source=SRC[srckey],
            fc_source=FC_SRC[round(fc, 3)],
        )
    return rows


# =========================================================================== #
#  §3  드론 속도 겹치기
# =========================================================================== #
def build_drone_table():
    out = {}
    for key, spec in drn.DRONES.items():
        pub = DRONE_SPEED_PUB.get(key, {})
        regimes = {
            "hover": dict(v_ms=0.0, provenance="definition (station keeping; manufacturers publish "
                                               "hovering accuracy, not a hover speed)"),
            "normal_mode": dict(v_ms=pub.get("normal_mode_ms"),
                                provenance=pub.get("source"), verification=pub.get("verification")),
            "tracking": dict(v_ms=pub.get("tracking_ms"),
                             provenance=pub.get("source"), verification=pub.get("verification")),
            "scene_slow": dict(v_ms=SCENE_SPEEDS["scene_slow_ms"],
                               provenance="src/freespace_scene.py : FS_SPEED[0] — the speed every "
                                          "detection result in this project is computed at"),
            "scene_fast": dict(v_ms=SCENE_SPEEDS["scene_fast_ms"],
                               provenance="src/freespace_scene.py : FS_SPEED[1]"),
            "max": dict(v_ms=(float(spec.max_speed_ms) if spec.max_speed_ms is not None else None),
                        provenance="src/drones.py : DroneSpec.max_speed_ms (sourced in "
                                   "docs/drone_research.json)",
                        verification=("spec_sheet" if spec.max_speed_ms is not None else "not_published")),
        }
        out[key] = dict(drone=key, weight_g=float(getattr(spec, "weight_g", float("nan"))),
                        max_speed_ms=(float(spec.max_speed_ms) if spec.max_speed_ms is not None else None),
                        regimes=regimes)
    return out


def overlay(illum_rows, drone_rows):
    """조명원 × (기체, 속도영역) → 모호 없이 재는가.

    `ratio = v / v_max` 가 헤드라인 양이고, `intervals_spanned = ceil(ratio)` 는 그 속도가 무모호
    구간 몇 개 폭인지를 뜻한다(접힘 '횟수' 를 세지 않는다 — 경계에서 정의가 갈리는 양이라 안 쓴다).
    """
    grid = {}
    for ik, ir in illum_rows.items():
        cells = {}
        for dk, dr in drone_rows.items():
            for rk, rr in dr["regimes"].items():
                v = rr["v_ms"]
                if v is None:
                    continue
                vm = ir["v_max_ms"]
                cells[f"{dk}/{rk}"] = dict(
                    v_ms=float(v), v_max_ms=float(vm),
                    ratio=float(v / vm) if vm > 0 else None,
                    intervals_spanned=int(math.ceil(v / vm)) if vm > 0 else None,
                    unambiguous=bool(v <= vm),
                    caveat=(HOVER_CAVEAT if v == 0.0 else None))
        n = len(cells)
        ok = sum(1 for c in cells.values() if c["unambiguous"])
        grid[ik] = dict(cells=cells, n_cells=n, n_unambiguous=ok,
                        frac_unambiguous=(ok / n if n else None))
    # 기체 관점 요약: 각 기체의 최고속도를 모호 없이 재는 조명원 목록
    #  ⭐ 반복률이 **송신기 규격으로 고정된** 조명원과, 연속기준이라 반복률이 **수신기 설계로**
    #     넘어가는 조명원을 절대 섞지 않는다. 패시브의 제약은 전자에만 있다.
    fixed = {k: r for k, r in illum_rows.items() if r["ambient"] and not r["continuous_reference"]}
    per_drone = {}
    for dk, dr in drone_rows.items():
        vmaxd = dr["max_speed_ms"]
        if vmaxd is None:
            per_drone[dk] = dict(max_speed_ms=None, note="published max speed unavailable")
            continue
        good = sorted([k for k, r in fixed.items() if vmaxd <= r["v_max_ms"]],
                      key=lambda k: fixed[k]["v_max_ms"])
        bad = sorted([k for k, r in fixed.items() if vmaxd > r["v_max_ms"]],
                     key=lambda k: fixed[k]["v_max_ms"])
        per_drone[dk] = dict(
            max_speed_ms=float(vmaxd),
            unambiguous_ambient_illuminators=good, aliasing_ambient_illuminators=bad,
            n_unambiguous=len(good), n_aliasing=len(bad),
            required_prf_hz_by_carrier={
                FC_SRC[round(fc, 3)]["text"].split(";")[0]:
                    dict(fc_hz=fc, required_prf_hz=4.0 * vmaxd / (C0 / fc),
                         required_max_ref_period_ms=1000.0 * (C0 / fc) / (4.0 * vmaxd))
                for fc in (0.100e9, 0.600e9, 1.843e9, 2.437e9, 3.500e9, 5.210e9)},
            scope="ambient fixed-repetition illuminators only (continuous references excluded)")
    # 상시(ambient) 조명원 두 부류
    cont = {k: r for k, r in illum_rows.items() if r["ambient"] and r["continuous_reference"]}
    return dict(by_illuminator=grid, by_drone=per_drone,
                ambient_fixed_prf=sorted(fixed, key=lambda k: fixed[k]["v_max_ms"]),
                ambient_continuous_reference=sorted(cont, key=lambda k: cont[k]["v_max_ms"]),
                partition_note=("continuous_reference=True 행의 PRF 는 송신기가 아니라 **수신기의 "
                                "배치 길이**가 정한다 — v_max 가 커 보이는 것은 설계 선택이지 신호의 "
                                "성질이 아니다. 법칙의 제약은 fixed 행에만 걸린다."),
                hover_caveat=HOVER_CAVEAT)


# =========================================================================== #
#  §4  설계 규칙 — 역산
# =========================================================================== #
def design_rule(illum_rows):
    """엔지니어가 쓰는 형태로 뒤집는다.

      (a) 속도 v 를 보려면 반복률이 얼마여야 하나       PRF_req = 4v/λ = 4 v f_c / c
      (b) 그 반복률은 주기로 얼마인가                   T_ref,max = λ/(4v)
      (c) 반복률이 고정이면 반송파를 얼마까지 올릴 수 있나  f_c,max = c·PRF/(4v)
    """
    speeds = [1.0, 3.0, 5.0, 10.0, 15.0, 20.0, 25.0]
    carriers = [("FM 100 MHz", 0.100e9), ("UHF 600 MHz", 0.600e9), ("LTE 1.8 GHz", 1.843e9),
                ("WiFi 2.4 GHz", 2.437e9), ("5G n78 3.5 GHz", 3.500e9), ("WiFi 5.2 GHz", 5.210e9)]
    req = []
    for v in speeds:
        row = dict(v_ms=v, v_kmh=v * 3.6, by_carrier={})
        for cl, fc in carriers:
            lam = C0 / fc
            prf_req = 4.0 * v / lam
            row["by_carrier"][cl] = dict(
                fc_hz=fc, lambda_m=lam,
                required_prf_hz=prf_req,
                required_max_ref_period_ms=1000.0 / prf_req,
                satisfied_by=sorted([k for k, r in illum_rows.items()
                                     if abs(r["fc_hz"] - fc) < 1.0 and r["prf_hz"] >= prf_req]),
                satisfied_by_any_ambient=sorted(
                    [k for k, r in illum_rows.items() if r["ambient"] and r["prf_hz"] >= prf_req],
                    key=lambda k: illum_rows[k]["prf_hz"]),
            )
        req.append(row)

    # (c) 고정 반복률에서 허용 반송파 상한
    carrier_ceiling = []
    for k, r in sorted(illum_rows.items(), key=lambda kv: kv[1]["prf_hz"]):
        carrier_ceiling.append(dict(
            illuminator=k, prf_hz=r["prf_hz"], fc_actual_hz=r["fc_hz"],
            fc_max_for_5ms_hz=C0 * r["prf_hz"] / (4.0 * 5.0),
            fc_max_for_15ms_hz=C0 * r["prf_hz"] / (4.0 * 15.0),
            fc_max_for_25ms_hz=C0 * r["prf_hz"] / (4.0 * 25.0),
            headroom_at_5ms=float(C0 * r["prf_hz"] / (4.0 * 5.0) / r["fc_hz"])))

    # LTE→5G 이설이 관측성에 하는 일 (인프라 서사의 수치 형태)
    lte, nr = illum_rows["lte_crs"], illum_rows["nr_ssb"]
    migration = dict(
        from_="LTE CRS", to_="5G NR SSB",
        prf_ratio=float(lte["prf_hz"] / nr["prf_hz"]),
        lambda_ratio=float(lte["lambda_m"] / nr["lambda_m"]),
        v_max_from_ms=lte["v_max_ms"], v_max_to_ms=nr["v_max_ms"],
        v_max_ratio=float(lte["v_max_ms"] / nr["v_max_ms"]),
        decomposition=("v_max 가 {r:.1f}배 줄어드는데, 그중 {a:.1f}배는 반복률(1000→50 Hz)이고 "
                       "{b:.2f}배는 파장(16.3→8.57 cm)이다 — 지배항은 반복률이다").format(
            r=lte["v_max_ms"] / nr["v_max_ms"], a=lte["prf_hz"] / nr["prf_hz"],
            b=lte["lambda_m"] / nr["lambda_m"]),
    )

    # CRS 의 per-symbol 여유(설계자가 실제로 당길 수 있는 레버)
    headroom = dict(
        lte_crs_per_subframe_hz=1000.0, lte_crs_per_symbol_hz=4000.0,
        gain_factor=4.0,
        v_max_per_subframe_ms=illum_rows["lte_crs"]["v_max_ms"],
        v_max_per_symbol_ms=illum_rows["lte_crs_sym"]["v_max_ms"],
        note=("CRS 는 서브프레임당 4개 OFDM 심볼에 실린다(포트 0, 슬롯당 2개). 슬로타임 표본을 "
              "심볼 단위로 잡으면 반복률이 4배가 된다. 5G SSB 에는 이 레버가 없다 — 버스트 사이에는 "
              "기준신호 자체가 존재하지 않는다."))
    return dict(required_prf=req, carrier_ceiling=carrier_ceiling,
                lte_to_5g_migration=migration, receiver_side_headroom=headroom,
                formulas=dict(
                    required_prf="PRF_req = 4 v / lambda = 4 v f_c / c",
                    max_reference_period="T_ref,max = lambda / (4 v)",
                    max_carrier="f_c,max = c PRF / (4 v)",
                    bistatic_relief="all three relax by 1/(cos(beta/2) cos delta) >= 1"))


# =========================================================================== #
#  §5  범위 · 신규성 가드
# =========================================================================== #
def intra_burst_alternative():
    """"버스트 내부 OFDM 심볼로 도플러를 재면 되지 않나" 에 수치로 답한다.

    SSB 버스트 내부(심볼 간격 Ts)로 재면 무모호 속도는 거대하지만 **분해능이 없다**.
    파라미터는 저장소 파형 객체에서 읽는다(손으로 안 친다).
    """
    w = all_waveforms("G1")["nr"]
    cp = int(np.asarray(w.cp_lens).ravel()[-1])         # 일반 심볼 CP
    Ts = (w.fft + cp) / w.fs_hz                          # 심볼 길이[s]
    n_sym_ssb = 4                                        # SSB = PSS+PBCH+SSS+PBCH
    T_burst = n_sym_ssb * Ts
    lam = C0 / w.carrier_hz
    v_u_intra = lam * w.scs_hz / 2.0                     # |v_u| <= lambda*SCS/2 (OFDM 레이더 형)
    dv_intra = lam / (2.0 * T_burst)                     # 속도 분해능 = lambda*(1/T_burst)/2
    # 버스트 간(우리 규약)
    prf = float(PILOT_RATE_HZ["nr"]["PSS"])
    v_u_inter = law_v_max(lam, prf)
    T_cpi = fss.T_CPI_REF_S
    M = fss.M_from_prf(T_cpi, prf)
    dv_inter = lam * float(fss.doppler_bin_hz(T_cpi, prf, M)) / 2.0
    return dict(
        symbol_s=float(Ts), symbols_per_ssb=n_sym_ssb, burst_s=float(T_burst),
        scs_hz=float(w.scs_hz), lambda_m=float(lam),
        intra_burst=dict(v_unambiguous_ms=float(v_u_intra), velocity_resolution_ms=float(dv_intra),
                         resolvable_cells_up_to_25ms=float(25.0 / dv_intra)),
        inter_burst=dict(prf_hz=prf, v_unambiguous_ms=float(v_u_inter),
                         T_cpi_s=T_cpi, M=int(M), velocity_resolution_ms=float(dv_inter)),
        verdict=("버스트 내부 처리는 무모호 속도 {a:.0f} m/s 를 주지만 속도 분해능이 {b:.0f} m/s 라 "
                 "드론 속도대(0~25 m/s)를 한 셀로 뭉갠다. 버스트 간 처리는 분해능 {c:.2f} m/s 를 주지만 "
                 "무모호 속도가 {d:.2f} m/s 다. 두 축은 교환관계이고, 우리 법칙은 **버스트 간** 축의 "
                 "상한이다.").format(a=v_u_intra, b=dv_intra, c=dv_inter, d=v_u_inter))


def ssb_burst_set_caveat():
    """⭐ 심사자가 반드시 때리는 지점: "SSB 버스트셋 안에 블록이 8개 있지 않나".

    사실이다 — 그래서 50 Hz 가 **보수적 읽기**임을 수치로 못박고, 그 위를 노리는 대가를 적는다.
    """
    lam = C0 / 3.5e9
    T_set = 0.020                                  # SSB 버스트셋 주기(TS 38.213 §4.1 초기접속)
    W = 0.005                                      # 버스트셋이 갇히는 창
    L_max = 8                                      # FR1 3-6 GHz
    return dict(
        spec=dict(doc="3GPP TS 38.213", clause="§4.1",
                  text=("An SS burst set is always confined to a 5 ms window and is located in the "
                        "first or second half of a 10 ms radio frame; the maximum number of "
                        "candidate SS/PBCH blocks L_max is 8 for 3-6 GHz."),
                  verification="spec_clause"),
        burst_set_period_s=T_set, window_s=W, L_max=L_max,
        conservative_reading=dict(
            prf_hz=1.0 / T_set, v_max_ms=law_v_max(lam, 1.0 / T_set),
            why=("한 지점의 수신기는 자기를 비추는 빔의 SSB 하나만 쓴다. 나머지 7개는 다른 방향을 "
                 "향한다. 검출기가 쓰는 규약이고 이 표의 정본이다.")),
        optimistic_ceiling=dict(
            prf_hz=L_max / T_set, v_max_ms=law_v_max(lam, L_max / T_set),
            why=("8빔을 전부 받고 그 격자가 균일하다면 400 Hz 다. 두 전제가 모두 거짓이다 — "
                 "8개가 5 ms 안에 몰리고 15 ms 는 비며(듀티 25%), 빔마다 이득·위상이 달라 "
                 "코히어런트 슬로타임 적분이 그냥은 안 선다.")),
        nonuniform_grid=dict(
            in_window_mean_spacing_ms=1000.0 * W / L_max,
            gap_ms=1000.0 * (T_set - W), duty=W / T_set,
            cost=("비균일 표본화로 모호를 풀면 스펙트럼 사이드로브 받침이 올라간다 — 모호를 "
                  "사이드로브와 교환하는 것이지 없애는 게 아니다. 그리고 빔별 이득·위상 보정이 "
                  "선행돼야 한다.")),
        verdict=("50 Hz 는 보수적 하한이고 400 Hz 는 도달 불가능한 상한이다. 그 사이를 실제로 "
                 "얼마나 회수하는지는 빔 수신성과 비균일 추정기의 성능에 달렸다 — 열린 과제로 "
                 "적고, 표의 숫자는 보수적 읽기를 쓴다."),
    )


DESIGN_LEVERS = [
    dict(lever="반송파를 낮춘다", formula="f_c,max = c*PRF/(4v)",
         gain="λ 에 선형 — 3.5 GHz → 600 MHz 면 5.8배",
         cost="그 대역에 조명원이 있어야 한다. 5G 상시기준은 n78 에 있다",
         who_pays="없음(대역 선택)"),
    dict(lever="같은 신호에서 더 촘촘한 기준을 뽑는다",
         formula="LTE CRS: 서브프레임당 1 → 심볼당 4",
         gain="4배 (40.7 → 162.7 m/s)",
         cost="심볼 단위 슬로타임 재정합. 5G SSB 에는 이 레버가 **없다** — 버스트 사이엔 기준이 없다",
         who_pays="수신기 신호처리"),
    dict(lever="파형을 재구성한다(demod-remod)", formula="PRF = 1/T_batch (수신기 선택)",
         gain="사실상 무제한", cost="표준 준수 복조기 한 벌 + 기준의 모호함수가 트래픽에 따라 변한다",
         who_pays="수신기 하드웨어·소프트웨어 전부"),
    dict(lever="SSB 버스트셋의 비균일 격자를 쓴다", formula="8 blocks / 5 ms window / 20 ms period",
         gain="이론상 최대 8배", cost="다중빔 수신 + 빔별 위상보정 + 사이드로브 받침 상승",
         who_pays="수신 배열과 추정기"),
    dict(lever="운동모형으로 해모호한다", formula="track-before-detect / 단일표적 unwrap",
         gain="모호 차수를 푼다", cost="단일표적 가정 — 선행(Abratkiewicz 2023)이 이미 이 길이다",
         who_pays="추적기(그리고 다중표적 포기)"),
    dict(lever="망에 PRS 를 요청한다", formula="NR-PRS 200 Hz (설정상한 500 Hz)",
         gain="1.07 → 4.28 m/s (상한 10.7)", cost="측위 세션이므로 더 이상 opportunistic 이 아니다",
         who_pays="망 운영자와의 협조 — 패시브의 전제를 버린다"),
]


NOVELTY_GUARD = [
    dict(claim_we_do_not_make="SSB 반복률이 속도 모호를 만든다는 사실을 우리가 처음 지적했다",
         prior=("K. Abratkiewicz, A. Ksiezyk, M. Plotka, P. Samczynski, J. Wszolek, T. Zielinski, "
                "'SSB-Based Signal Processing for Passive Radar Using a 5G Network', IEEE J. Sel. "
                "Topics Appl. Earth Obs. Remote Sens., vol. 16, pp. 3469-3484, 2023, "
                "DOI 10.1109/JSTARS.2023.3262291"),
         what_they_already_did=("SSB 를 주기 펄스로 보는 5G PCL 처리사슬을 세우고, 'SSB periodicity "
                                "limits the velocity ambiguity' 를 명시한 뒤 단일표적 해모호 방법을 "
                                "제안했다. 시뮬 + 실측 5G 데이터로 검증했다."),
         verification="web metadata (title/venue/vol/pages/DOI) — PDF 는 로컬 아카이브에 없음",
         our_position="법칙 자체는 선행이 있다. 우리가 새로 놓는 것은 아래 세 가지다."),
    dict(claim_we_do_not_make="무모호 속도 공식이 새롭다",
         prior=("P. Jopanya, D. P. M. Osorio, 'Utilizing 5G NR SSB Blocks for Passive Detection and "
                "Localization of Low-Altitude Drones', arXiv:2504.02641"),
         what_they_already_did=("SSB 로 저고도 드론을 패시브 검출/측위한다. 단 그들의 무모호 속도는 "
                                "|v_u| <= lambda*SCS/2 로 **버스트 내부** OFDM 축의 값이다 — 우리 "
                                "법칙(버스트 간 축)과 다른 국면이고, 둘의 교환관계는 "
                                "scope.intra_burst_alternative 에 수치로 있다."),
         verification="arXiv HTML 본문에서 공식·파라미터 확인",
         our_position="같은 신호를 다른 축에서 본다. 두 축을 함께 적는 것이 우리 기여의 일부다."),
    dict(claim_we_do_not_make="도플러 모호가 패시브 레이더에서 새 문제다",
         prior=("Doppler ambiguity analysis and suppression for LTE-based passive bistatic radars, "
                "Front. Inf. Technol. Electron. Eng., DOI 10.1631/FITEE.2000143"),
         what_they_already_did="LTE 패시브에서 도플러 모호를 분석·억제한다(단일 표준 내부).",
         verification="검색 메타데이터만 — 본문 미확보. 표의 어떤 수치도 이 논문에 의존하지 않는다",
         our_position="표준 내부 문제로 다뤄져 왔다. 우리는 표준 **사이**의 선택 기준으로 올린다."),
]

CONTRIBUTION = [
    "① 근거 붙은 교차표준 표: 상시 기준신호 8종의 반복률을 규격 조항·게재 측정으로 각각 못박고, "
    "그 자리에서 v_max 로 환산했다. 셀룰러/WLAN/방송을 한 축에 올린 표는 선행에 없다.",
    "② 실기체 속도 겹치기: 7기종의 게재 최고속도를 같은 축에 얹어, 어느 조명원이 어느 기체를 "
    "모호 없이 재는지를 표 하나로 판정한다.",
    "③ 설계 규칙으로의 역산: PRF_req = 4v/lambda, T_ref,max = lambda/4v, f_c,max = c*PRF/4v. "
    "'흥미롭다' 를 '쓴다' 로 바꾸는 형태다.",
    "④ 인프라 서사: 사업자가 LTE 를 5G 로 옮기면 패시브가 쓸 수 있는 상시 기준의 반복률이 20배 "
    "떨어지고 속도 관측성이 40.7 -> 1.07 m/s 로 무너진다. 파장 기여는 1.90배뿐이고 나머지가 반복률이다.",
]

RETRACTION = dict(
    retracted="5G coverage = 0 at every heading (report05 headline)",
    why=("그 '0' 은 T_CPI=100 ms 와 **선언** 2.5빈 가드가 동시에 성립하는 한 점의 산물이다. 검출기가 "
         "실제로 지우는 1.5빈 규약에서는 같은 CPI 에서 blind=0.636, 200 ms 에서 0.303 이다. 게다가 "
         "전 헤딩 블라인드는 5G 전용이 아니다 — LTE 도 짧은 CPI 에서 blind=1.000 이 된다."),
    evidence_keys=[
        "outputs/cpi_guard_sweep.json : verdict.artifact.blind_hard_same_cpi = 0.6361",
        "outputs/cpi_guard_sweep.json : verdict.artifact.blind_hard_at_200ms = 0.3028",
        "outputs/cpi_guard_sweep.json : structural.by_mode.L1.T_max_total_blind_declared_s = 0.005 "
        "(기구 A — 가드가 접힘축 전체를 덮는 조건 M<=2g)",
        "outputs/cpi_guard_sweep.json : verdict.artifact.text — LTE 는 CPI<=0.0393 s 에서 "
        "blind=1.000 (기구 B — 가드가 도플러 진폭을 덮는다)",
        "outputs/cpi_guard_sweep.json : verdict.headline_claim_status = 'must_change'",
    ],
    replaced_by=("패시브 바이스태틱의 무모호 반경속도는 상시 기준신호의 반복률이 정한다: "
                 "v_max = lambda*PRF_ref/4. 5G SSB 는 1.07 m/s 이고 이것은 CPI 로 못 고친다."),
    why_the_replacement_is_stronger=("유도 사슬이 3GPP 규격 -> 산술 -> 나이퀴스트 -> 운동학 뿐이라 "
                                     "sigma 가 한 번도 안 들어간다. 프로젝트에서 가장 약한 양(미검증 "
                                     "절대 RCS)이 헤드라인에 관여하지 않는다."),
    what_survives_from_the_old_result=(
        "같은 CPI 에서의 **배수**는 살아남는다: blind_hard 비 G1/W1 = 12.05 (100 ms), 12.11 / 14.33 / "
        "19.00 / 11.00 (200/500/1000/2000 ms) ⟨cpi_guard_sweep.json : equal_cpi_penalty⟩. 그리고 "
        "접힘비율 자체가 CPI 무관 상수라는 것 ⟨verdict.structural.s2_alias_floor⟩."),
)

# 헤드라인 숫자의 출처 원장 — 리포트가 그대로 인용할 키
PROVENANCE = {
    "v_max = lambda*PRF/4": "benchmark/refrate_law.py : law_v_max (닫힌형, law.verification 에서 검증)",
    "5G SSB v_max 1.071 m/s": "outputs/refrate_law.json : illuminators.rows.nr_ssb.v_max_ms",
    "WiFi VHT-LTF v_max 14.385 m/s": "outputs/refrate_law.json : illuminators.rows.wifi_vhtltf.v_max_ms",
    "LTE CRS v_max 40.666 m/s": "outputs/refrate_law.json : illuminators.rows.lte_crs.v_max_ms",
    "WiFi beacon v_max 0.140 m/s": "outputs/refrate_law.json : illuminators.rows.wifi_beacon.v_max_ms",
    "LTE->5G v_max 38.0x drop": "outputs/refrate_law.json : design_rule.lte_to_5g_migration",
    "law verified to <1e-4 rel": "outputs/refrate_law.json : law.verification.V1_geometry_factor.max_rel_err",
    "alias onset == closed form": "outputs/refrate_law.json : law.verification.V2_nyquist_threshold[*].rel_err",
    "CPI independence": "outputs/refrate_law.json : law.verification.V3_cpi_independence.verdict",
    "repo parity (3 rows)": "outputs/refrate_law.json : law.repo_parity.all_match",
    "equal-CPI penalty 12.05x": "outputs/cpi_guard_sweep.json : equal_cpi_penalty[0].ratio_G1_over_W1",
    "drone max speeds": "src/drones.py : DRONES[*].max_speed_ms (sourced in docs/drone_research.json)",
    "scene speeds 5 / 15 m/s": "src/freespace_scene.py : FS_SPEED",
}


# =========================================================================== #
#  §6  그림 (텍스트 전부 영어 · 벡터 PDF + 300 dpi PNG)
# =========================================================================== #
def make_figures(illum_rows, drone_rows):
    """네 장. 그림 하나 = 질문 하나. 텍스트 전부 영어, 색+마커/선종 이중부호화(흑백 판별).

    색은 dataviz 규약의 검증된 categorical 슬롯 1/2/3(blue/orange/aqua)만 쓴다 — 세 슬롯은
    all-pairs CVD 검사를 통과한다. 발산맵은 중간이 중립(흰색)인 RdBu 로 쓴다(빨강-초록 금지).
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

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

    # dataviz 검증 슬롯 1/2/3 + 마커(이중부호화)
    FAM = {"cellular": ("#2a78d6", "o"), "wlan": ("#eb6834", "s"), "broadcast": ("#1baf7a", "^")}
    FAMLAB = {"cellular": "cellular (3GPP)", "wlan": "WLAN (802.11)", "broadcast": "broadcast"}
    INK, INK2 = "#0b0b0b", "#52514e"

    fixed = [k for k in illum_rows
             if illum_rows[k]["ambient"] and not illum_rows[k]["continuous_reference"]]
    fixed.sort(key=lambda k: illum_rows[k]["v_max_ms"])
    dmax = {k: v["max_speed_ms"] for k, v in drone_rows.items() if v["max_speed_ms"] is not None}
    v_fastest = max(dmax.values())
    v_slowest = min(dmax.values())

    # ------------------------------------------------------------------ #
    #  F1  "어느 상시 조명원이 어느 드론을 모호 없이 재는가"  — 정렬 점-막대
    # ------------------------------------------------------------------ #
    fig, ax = plt.subplots(figsize=(7.6, 5.4))
    XMIN, XMAX = 0.08, 700.0
    ax.axvspan(XMIN, v_fastest, color="#2a78d6", alpha=0.07, lw=0, zorder=0)
    for i, k in enumerate(fixed):
        r = illum_rows[k]
        c, mk = FAM[r["family"]]
        ok = r["v_max_ms"] >= v_fastest
        ax.plot([XMIN, r["v_max_ms"]], [i, i], "-", color=c, lw=1.6, alpha=0.55, zorder=2)
        ax.plot(r["v_max_ms"], i, mk, ms=8.5, mfc=(c if ok else "white"), mec=c, mew=1.6, zorder=3)
        ax.text(r["v_max_ms"] * 1.22, i, "%.2f" % r["v_max_ms"] if r["v_max_ms"] < 10
                else "%.0f" % r["v_max_ms"], va="center", ha="left", fontsize=8, color=INK)
    for v, lab, ls, yy in ((5.0, "scene speed 5 m/s", ":", 0.0),
                           (v_slowest, "slowest airframe max 13.5 m/s  (Typhoon H480)", "--", 1.0),
                           (v_fastest, "fastest airframe max 25 m/s  (Mavic 4 Pro)", "-", 2.0)):
        ax.axvline(v, color=INK2, lw=1.0, ls=ls, zorder=1)
        ax.text(v * 1.10, yy, lab, rotation=0, fontsize=7.4, color=INK2,
                va="center", ha="left", zorder=6,
                bbox=dict(fc="white", ec="none", alpha=0.8, pad=1.2))
    ax.set_yticks(range(len(fixed)))
    ax.set_yticklabels(["%s   (%g Hz, %.2f GHz)"
                        % (illum_rows[k]["label"], round(illum_rows[k]["prf_hz"], 2),
                           illum_rows[k]["fc_hz"] / 1e9) for k in fixed], fontsize=8)
    ax.set_xscale("log")
    ax.set_xlim(XMIN, XMAX)
    ax.set_ylim(-0.8, len(fixed) + 0.6)
    ax.set_xlabel("Max unambiguous radial speed  $v_{max}=\\lambda\\,\\mathrm{PRF}_{ref}/4$   [m/s]")
    ax.set_title("Which ambient illuminator can measure which drone without aliasing")
    ax.text(XMIN * 1.15, len(fixed) + 0.30,
            "shaded band: the fastest published airframe (25 m/s) aliases on every illuminator here",
            fontsize=7.4, color="#1a4f8f", va="center")
    ax.grid(axis="y", alpha=0.0)
    ax.legend(handles=[Line2D([], [], ls="none", marker=FAM[f][1], mfc=FAM[f][0], mec=FAM[f][0],
                              ms=8, label=FAMLAB[f]) for f in ("cellular", "wlan", "broadcast")]
                     + [Line2D([], [], ls="none", marker="o", mfc="white", mec=INK2, mew=1.6,
                               ms=8, label="hollow: aliases the fastest airframe")],
              loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=4, frameon=False,
              handletextpad=0.4, columnspacing=1.6)
    save(fig, "refrate_law_f1_ranking",
         "Maximum unambiguously measurable radial speed of every always-on illuminator "
         "considered, computed as v_max = lambda*PRF_ref/4 from the repetition rate each "
         "specification mandates. Vertical rules mark published airframe maxima; hollow markers "
         "are illuminators on which the fastest airframe aliases.")

    # ------------------------------------------------------------------ #
    #  F2  "왜 그런가" — 법칙 자체(등-λ 직선 위의 점들)
    # ------------------------------------------------------------------ #
    fig, ax = plt.subplots(figsize=(7.2, 5.0))
    prf_ax = np.logspace(np.log10(4.0), np.log10(6000.0), 300)
    for cl, fc, ls in (("$\\lambda$ = 3.00 m  (FM 100 MHz)", 0.100e9, ":"),
                       ("$\\lambda$ = 50.0 cm  (UHF 600 MHz)", 0.600e9, (0, (5, 1, 1, 1))),
                       ("$\\lambda$ = 16.3 cm  (LTE 1.84 GHz)", 1.843e9, "--"),
                       ("$\\lambda$ = 8.57 cm  (5G 3.50 GHz)", 3.500e9, "-"),
                       ("$\\lambda$ = 5.75 cm  (WiFi 5.21 GHz)", 5.210e9, "-.")):
        ax.plot(prf_ax, (C0 / fc) * prf_ax / 4.0, linestyle=ls, color="0.45", lw=1.0, label=cl,
                zorder=1)
    for k in fixed:
        r = illum_rows[k]
        c, mk = FAM[r["family"]]
        ax.plot(r["prf_hz"], r["v_max_ms"], mk, ms=7.5, mfc=c, mec="white", mew=0.8, zorder=4)
        dx, dy = {"dvbt_continual": (8, -3), "dtmb_pn945": (8, -4), "wifi_vhtltf": (8, -3),
                  "wifi_beacon24": (8, 3), "wifi_beacon": (8, -9), "wifi_vhtltf_lo": (8, 4),
                  "nr_ssb": (8, -3), "dtmb_pn420": (-6, 8), "lte_crs_sym": (-12, 9),
                  }.get(k, (8, 4))
        ax.annotate(SHORT[k], (r["prf_hz"], r["v_max_ms"]), textcoords="offset points",
                    xytext=(dx, dy), fontsize=7.4, color=INK, zorder=5)
    ax.axhspan(0.05, v_fastest, color="#2a78d6", alpha=0.07, lw=0, zorder=0)
    ax.axhline(v_fastest, color=INK2, lw=1.0)
    ax.text(4.4, v_fastest * 1.12, "fastest published airframe maximum, 25 m/s",
            fontsize=7.4, color=INK2)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlim(4.0, 9000.0); ax.set_ylim(0.08, 400.0)
    ax.set_xlabel("Reference-signal repetition rate  $\\mathrm{PRF}_{ref}$   [Hz]")
    ax.set_ylabel("$v_{max}$   [m/s]")
    ax.set_title("The law: $v_{max}=\\lambda\\,\\mathrm{PRF}_{ref}/4$\n"
                 "grey lines are the law at five carriers; markers are real always-on references")
    leg1 = ax.legend(loc="upper left", framealpha=0.95, labelspacing=0.35)
    ax.add_artist(leg1)
    ax.legend(handles=[Line2D([], [], ls="none", marker=FAM[f][1], mfc=FAM[f][0], mec="white",
                              mew=0.8, ms=7.5, label=FAMLAB[f])
                       for f in ("cellular", "wlan", "broadcast")],
              loc="lower right", framealpha=0.95)
    save(fig, "refrate_law_f2_law",
         "The unambiguous-speed law. Grey lines are v_max = lambda*PRF/4 at five carriers; each "
         "marker is a real always-on reference signal placed at its specified repetition rate. "
         "Codes: SSB 5G NR sync block, CRS LTE cell-specific reference, VHT-LTF 802.11ac long "
         "training field, BCN 802.11 beacon, DVB-T sp/cp scattered/continual pilots, DTMB frame "
         "header modes, DAB phase-reference symbol.")

    # ------------------------------------------------------------------ #
    #  F3  "어느 조합이 몇 번 접히는가" — 조명원 x 기체 행렬
    # ------------------------------------------------------------------ #
    dorder = sorted(dmax, key=lambda k: dmax[k])
    rows_m = fixed[::-1]                                   # F1 과 같은 순서(위=좋음)
    Z = np.array([[dmax[dk] / illum_rows[ik]["v_max_ms"] for dk in dorder] for ik in rows_m])
    fig, ax = plt.subplots(figsize=(6.0, 6.2))
    im = ax.imshow(np.log10(Z), aspect="auto", cmap="RdBu_r", vmin=-2.2, vmax=2.2)
    for i in range(len(rows_m)):
        for j in range(len(dorder)):
            ok = Z[i, j] <= 1.0
            ax.text(j, i, ("OK" if ok else ("%.0f×" % Z[i, j] if Z[i, j] >= 10
                                            else "%.1f×" % Z[i, j])),
                    ha="center", va="center", fontsize=7.2,
                    color=("#0b0b0b" if abs(np.log10(Z[i, j])) < 1.2 else "white"),
                    fontweight=("bold" if ok else "normal"))
    ax.set_xticks(range(len(dorder)))
    ax.set_xticklabels(["%s\n%g m/s" % (k, dmax[k]) for k in dorder], fontsize=7.4)
    ax.set_yticks(range(len(rows_m)))
    ax.set_yticklabels(["%s  (%.2f m/s)" % (illum_rows[k]["label"], illum_rows[k]["v_max_ms"])
                        for k in rows_m], fontsize=7.4)
    ax.set_title("Aliasing factor  $v_{max,\\;airframe}\\,/\\,v_{max,\\;illuminator}$\n"
                 "bold OK = the airframe's published maximum is measurable unambiguously")
    cb = fig.colorbar(im, ax=ax, fraction=0.036, pad=0.02,
                      ticks=[-2, -1, 0, 1, 2])
    cb.ax.set_yticklabels(["0.01×", "0.1×", "1×", "10×", "100×"],
                          fontsize=7.5)
    cb.set_label("aliasing factor (log scale)", fontsize=8)
    ax.grid(False)
    save(fig, "refrate_law_f3_matrix",
         "Ratio of each airframe's published maximum speed to each illuminator's unambiguous "
         "speed limit. A value above 1 is how many unambiguous intervals wide the airframe's "
         "maximum speed is: the Doppler wraps and the measured speed is not the true one. "
         "Entries marked OK need no unwrapping.")

    # ------------------------------------------------------------------ #
    #  F4  설계 규칙 — 역산
    # ------------------------------------------------------------------ #
    fig, ax = plt.subplots(figsize=(7.6, 5.2))
    VMAXX = 30.0
    v_ax = np.linspace(0.5, VMAXX, 400)
    for cl, fc, ls in (("100 MHz  (FM)", 0.100e9, ":"),
                       ("600 MHz  (UHF TV)", 0.600e9, (0, (5, 1, 1, 1))),
                       ("1.84 GHz  (LTE)", 1.843e9, "--"),
                       ("3.50 GHz  (5G n78)", 3.500e9, "-"),
                       ("5.21 GHz  (WiFi)", 5.210e9, "-.")):
        ax.plot(v_ax, 4.0 * v_ax * fc / C0, linestyle=ls, lw=1.3, color="0.42", label=cl, zorder=2)
    # 실제 상시 신호가 **공급하는** 반복률 — 자기 반송파의 곡선과 만나는 곳이 그 신호의 v_max 다
    for k in ("wifi_beacon", "nr_ssb", "nr_prs", "wifi_vhtltf", "lte_crs", "dtmb_pn420"):
        r = illum_rows[k]
        c, mk = FAM[r["family"]]
        xend = min(max(r["v_max_ms"], 0.5), VMAXX)
        ax.plot([0.5, xend], [r["prf_hz"]] * 2, "-", color=c, lw=1.7, alpha=0.85, zorder=3)
        inside = 0.5 <= r["v_max_ms"] <= VMAXX
        below = r["v_max_ms"] < 0.5
        ax.plot(xend, r["prf_hz"], mk if inside else ("<" if below else ">"),
                ms=(7.5 if inside else 6.5), mfc=(c if inside else "white"), mec=c, mew=1.4,
                zorder=4)
        ax.text(0.75, r["prf_hz"] * {"wifi_vhtltf": 0.79, "lte_crs": 1.20}.get(k, 1.15),
                "%s supplies %g Hz at %.2f GHz%s"
                % (SHORT[k], round(r["prf_hz"], 2), r["fc_hz"] / 1e9,
                   ("   ->  enough to %.2f m/s" % r["v_max_ms"]) if inside
                   else ("   ->  enough past 30 m/s" if not below
                         else "   ->  runs out at %.2f m/s, off scale left" % r["v_max_ms"])),
                fontsize=7.3, color=c, zorder=5)
    ax.set_yscale("log")
    ax.set_xlim(0.5, VMAXX); ax.set_ylim(4.0, 9000.0)
    ax.set_xlabel("Radial speed the sensor must observe unambiguously   $v$   [m/s]")
    ax.set_ylabel("Reference repetition rate   [Hz]")
    ax.set_title("Design rule: the repetition rate a passive sensor requires, and what real signals supply\n"
                 "a coloured rule meets its own carrier curve exactly at that signal's $v_{max}$")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=5, frameon=False,
              handletextpad=0.4, columnspacing=1.3, title="required rate, by carrier")
    save(fig, "refrate_law_f4_design_rule",
         "Inverted form of the law. Grey curves give the reference repetition rate a passive "
         "receiver requires to observe a given radial speed at a given carrier; coloured rules give "
         "what real always-on signals supply, and each rule meets its own carrier curve exactly at "
         "that signal's maximum unambiguous speed.")
    return figs


# =========================================================================== #
#  main
# =========================================================================== #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true", help="그림 생략 · 검증 격자 축소")
    a = ap.parse_args()
    t0 = time.time()

    illum = build_illuminator_table()
    dro = build_drone_table()
    ver = verify_law(n_psi=(360 if a.smoke else 2880))
    par = repo_parity(illum)
    ov = overlay(illum, dro)
    des = design_rule(illum)
    scope = intra_burst_alternative()

    figs = {} if a.smoke else make_figures(illum, dro)

    doc = dict(
        meta=dict(
            script="benchmark/refrate_law.py",
            generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
            question=("패시브 바이스태틱의 무모호 반경속도를 정하는 것은 무엇인가 — "
                      "그리고 그것이 실제 조명원·실제 기체에 무엇을 하는가"),
            smoke=bool(a.smoke), runtime_s=None,
            repo_functions_used=[
                "freespace_scene.fs_params", "freespace_scene.target_pos",
                "freespace_scene.heading_velocity", "freespace_scene.folded_doppler",
                "freespace_scene.nyquist_gate", "freespace_scene.look_el_deg",
                "freespace_scene.prf_hz", "freespace_scene.doppler_bin_hz",
                "freespace_scene.M_from_prf", "waveforms.all_waveforms",
                "waveforms.PILOT_RATE_HZ", "drones.DRONES"],
            house_rules="figure text English; prose Korean; every number carries a source",
        ),

        law=dict(
            statement_en=("For a passive bistatic receiver whose matched filter locks onto an ambient "
                          "reference signal that repeats at PRF_ref, the maximum unambiguously "
                          "measurable target radial speed is v_max = lambda * PRF_ref / 4."),
            statement_ko=("패시브 바이스태틱 수신기가 반복률 PRF_ref 의 상시 기준신호에 정합하면, "
                          "모호 없이 잴 수 있는 표적 반경속도의 상한은 v_max = lambda*PRF_ref/4 다."),
            derivation=[
                "1. 바이스태틱 도플러:  f_d = v . (u1 + u2) / lambda   "
                "(u1 = 표적->TX, u2 = 표적->RX 단위벡터; freespace_scene.fs_params 의 식 그대로)",
                "2. |u1 + u2| = 2 cos(beta/2) 이므로  f_d = (2 v / lambda) cos(beta/2) cos(delta), "
                "delta = 속도벡터와 이등분선 사이 각",
                "3. 기준신호가 PRF_ref 로만 오면 슬로타임 표본화율이 PRF_ref 다. 나이퀴스트: "
                "|f_d| < PRF_ref / 2   (freespace_scene.nyquist_gate)",
                "4. 대입:  v < lambda PRF_ref / (4 cos(beta/2) cos(delta))",
                "5. cos(beta/2) cos(delta) <= 1 이므로 최악(beta=0, delta=0)이 하한을 준다:  "
                "v_max = lambda PRF_ref / 4",
            ],
            forms=dict(
                bistatic_general="v_max(beta, delta) = lambda PRF / (4 cos(beta/2) cos delta)",
                bistatic_floor="v_max = lambda PRF / 4      (beta = 0, delta = 0)",
                monostatic="v_max = lambda PRF / 4      (beta = 0 by definition; f_d = 2v/lambda)",
                relation=("바이스태틱은 모노스태틱보다 **관대하다** — 같은 PRF 에서 v_max 가 "
                          "1/(cos(beta/2) cos delta) >= 1 배 크다. beta -> 180 도(전방산란)에서 "
                          "도플러가 0 으로 죽어 모호는 사라지지만 속도 정보도 사라진다."),
            ),
            geometry_assumption=(
                "표적은 수평비행(roll=pitch=0)이고 속도는 수평면 안에 있다. 그래서 delta 는 "
                "이등분선의 앙각과 헤딩이 함께 만든다 — 지상 TX/RX + 공중 표적이면 cos(delta) 는 "
                "이등분선 앙각의 코사인만큼 자동으로 1보다 작아지고, v_max 는 그만큼 커진다."),
            what_does_not_enter=dict(
                sigma="RCS 는 유도 사슬 어디에도 없다",
                cpi=("CPI 는 도플러 빈폭 1/T 를 정할 뿐 무모호 구간 +-PRF/2 를 못 바꾼다 — "
                     "V3 에서 도플러 빈폭이 {a:g}→{b:g} Hz 로 {r:g}배 변해도 접힘비율은 "
                     "{f:.4f} 로 {n}행 모두 같았다").format(
                         a=ver["V3_cpi_independence"]["bin_hz_span"][0],
                         b=ver["V3_cpi_independence"]["bin_hz_span"][1],
                         r=(ver["V3_cpi_independence"]["bin_hz_span"][0]
                            / ver["V3_cpi_independence"]["bin_hz_span"][1]),
                         f=ver["V3_cpi_independence"]["distinct_alias_fracs"][0],
                         n=len(ver["V3_cpi_independence"]["rows"])),
                bandwidth="기준신호 대역(거리분해능)과 반복률(속도모호)은 서로 독립이다",
                power="송신전력·경로손실은 검출확률을 바꾸지 종횡비를 안 바꾼다"),
            verification=ver,
            repo_parity=par,
        ),

        illuminators=dict(
            rows=illum,
            ranking_ambient_fixed_prf=[
                (k, illum[k]["prf_hz"], illum[k]["fc_hz"], illum[k]["v_max_ms"])
                for k in sorted([k for k in illum
                                 if illum[k]["ambient"] and not illum[k]["continuous_reference"]],
                                key=lambda k: illum[k]["v_max_ms"])],
            ranking_ambient_continuous=[
                (k, illum[k]["prf_hz"], illum[k]["fc_hz"], illum[k]["v_max_ms"])
                for k in sorted([k for k in illum
                                 if illum[k]["ambient"] and illum[k]["continuous_reference"]],
                                key=lambda k: illum[k]["v_max_ms"])],
            headline=dict(
                nr_ssb_v_max_ms=illum["nr_ssb"]["v_max_ms"],
                wifi_vhtltf_v_max_ms=illum["wifi_vhtltf"]["v_max_ms"],
                lte_crs_v_max_ms=illum["lte_crs"]["v_max_ms"],
                worst_ambient_fixed=min([k for k in illum if illum[k]["ambient"]
                                         and not illum[k]["continuous_reference"]],
                                        key=lambda k: illum[k]["v_max_ms"]),
                best_ambient_fixed=max([k for k in illum if illum[k]["ambient"]
                                        and not illum[k]["continuous_reference"]],
                                       key=lambda k: illum[k]["v_max_ms"]),
                note=("⭐ 최악의 상시 기준은 5G SSB 가 아니라 **WiFi 비콘**(9.77 Hz, 5 GHz 에서 "
                      "0.14 m/s)이다. 법칙이 반-5G 주장이 아니라 반복률의 함수임을 이 행 하나가 "
                      "증명한다. 방송 조명원(DVB-T·DTMB·FM)이 편한 이유도 반복률이 빠른 데 더해 "
                      "파장이 5~50배 길기 때문이다."),
                span=("상시·고정반복 조명원의 v_max 는 %.2f m/s(WiFi 비콘 5 GHz)에서 %.1f m/s"
                      "(DTMB PN420)까지 %.0f배 벌어진다."
                      % (min(illum[k]["v_max_ms"] for k in illum
                             if illum[k]["ambient"] and not illum[k]["continuous_reference"]),
                         max(illum[k]["v_max_ms"] for k in illum
                             if illum[k]["ambient"] and not illum[k]["continuous_reference"]),
                         max(illum[k]["v_max_ms"] for k in illum
                             if illum[k]["ambient"] and not illum[k]["continuous_reference"])
                         / min(illum[k]["v_max_ms"] for k in illum
                               if illum[k]["ambient"] and not illum[k]["continuous_reference"])))),
        ),

        drones=dict(rows=dro, scene_speeds=SCENE_SPEEDS,
                    speed_axis_policy=("게재된 제원만 넣는다. 'typical cruise' 는 제조사가 공표하지 "
                                       "않으므로 (a) 공표된 Normal 모드 값이 있으면 그것을, (b) 없으면 "
                                       "null 을 두고, 별도로 저장소 장면속도 5/15 m/s 를 함께 싣는다 — "
                                       "이 프로젝트의 모든 검출 결과가 실제로 그 두 속도에서 계산됐다.")),

        overlay=ov,
        design_rule=des,
        scope=dict(intra_burst_alternative=scope,
                   ssb_burst_set=ssb_burst_set_caveat(),
                   applies_to=("슬로타임(기준신호 반복 사이) 축의 도플러 처리. 버스트 내부 OFDM 축은 "
                               "별개이고 그 교환관계는 intra_burst_alternative 가 수치로 준다."),
                   assumes=["수평 등속 직선비행", "단일 표적(다중표적 해모호는 별건)",
                            "기준신호가 반복 사이에는 존재하지 않음(SSB 는 실제로 그렇다)",
                            "슬로타임 표본이 균일 간격(SSB 버스트셋은 실은 비균일 — ssb_burst_set 참조)"],
                   does_not_assume=["특정 RCS", "특정 송신전력", "특정 CPI", "특정 대역폭"]),
        design_levers=DESIGN_LEVERS,
        novelty_guard=NOVELTY_GUARD,
        contribution=CONTRIBUTION,
        retraction=RETRACTION,
        provenance=PROVENANCE,
        figures=figs,
    )
    doc["meta"]["runtime_s"] = time.time() - t0

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1, default=float)

    # ---- 콘솔 요약(한국어) ------------------------------------------------ #
    print("=" * 78)
    print("법칙:  v_max = lambda * PRF_ref / 4      (바이스태틱 하한 = 모노스태틱 등가)")
    print("일반형: v_max(beta,delta) = lambda*PRF / (4 cos(beta/2) cos delta)")
    print("-" * 78)
    print("검증 V1 기하인자   최대 상대오차 %.3e  (기하 %d개, beta %.1f~%.1f도)"
          % (ver["V1_geometry_factor"]["max_rel_err"], ver["V1_geometry_factor"]["n_geometries"],
             *ver["V1_geometry_factor"]["beta_range_deg"]))
    for r in ver["V2_nyquist_threshold"]:
        print("검증 V2 PRF %7.2f Hz  닫힌형 v_max %8.3f  접힘개시 %8.3f m/s  상대오차 %.2e"
              % (r["prf_hz"], r["v_max_closed_ms"], r["v_alias_onset_ms"], r["rel_err"]))
    print("검증 V3 %s" % ver["V3_cpi_independence"]["verdict"])
    print("저장소 정합: %s" % ("전부 일치" if par["all_match"] else "불일치 있음 — JSON 확인"))
    print("-" * 78)
    print("상시·**고정반복** 조명원 v_max 순위 [m/s] (패시브가 실제로 묶이는 것):")
    for k, prf, fc, v in doc["illuminators"]["ranking_ambient_fixed_prf"]:
        print("   %-22s PRF %9.2f Hz  fc %6.3f GHz  ->  v_max %8.2f m/s"
              % (illum[k]["label"], prf, fc / 1e9, v))
    print("상시·연속기준(반복률 = 수신기 배치 선택):")
    for k, prf, fc, v in doc["illuminators"]["ranking_ambient_continuous"]:
        print("   %-22s batch %6.0f Hz  fc %6.3f GHz  ->  v_max %8.2f m/s"
              % (illum[k]["label"], prf, fc / 1e9, v))
    print("-" * 78)
    for dk, r in ov["by_drone"].items():
        if r.get("max_speed_ms") is None:
            print("   %-12s 최고속도 미공표" % dk); continue
        print("   %-12s max %5.1f m/s  →  모호없음 %d / 접힘 %d  (상시·고정반복 %d종 중)"
              % (dk, r["max_speed_ms"], r["n_unambiguous"], r["n_aliasing"],
                 r["n_unambiguous"] + r["n_aliasing"]))
        print("        접히는 것: %s" % ", ".join(illum[k]["label"] for k in r["aliasing_ambient_illuminators"]))
    print("-" * 78)
    print("설계 규칙:  PRF_req = 4v/lambda   T_ref,max = lambda/(4v)   f_c,max = c*PRF/(4v)")
    print("   25 m/s 를 3.5 GHz 에서 보려면 PRF >= %.0f Hz (기준주기 <= %.2f ms)"
          % (des["required_prf"][-1]["by_carrier"]["5G n78 3.5 GHz"]["required_prf_hz"],
             des["required_prf"][-1]["by_carrier"]["5G n78 3.5 GHz"]["required_max_ref_period_ms"]))
    print("   LTE→5G 이설:  %s" % des["lte_to_5g_migration"]["decomposition"])
    print("-" * 78)
    print("범위: %s" % scope["verdict"])
    bs = doc["scope"]["ssb_burst_set"]
    print("SSB 버스트셋: 보수 %.0f Hz(%.2f m/s) ↔ 상한 %.0f Hz(%.2f m/s) — %s"
          % (bs["conservative_reading"]["prf_hz"], bs["conservative_reading"]["v_max_ms"],
             bs["optimistic_ceiling"]["prf_hz"], bs["optimistic_ceiling"]["v_max_ms"],
             "표는 보수적 읽기를 쓴다"))
    print("=" * 78)
    print("wrote %s  (%.1f s)" % (OUT_JSON, doc["meta"]["runtime_s"]))
    for stem, p in figs.items():
        print("  fig %s -> %s | %s" % (stem, p["png"], p["pdf"]))


if __name__ == "__main__":
    main()
