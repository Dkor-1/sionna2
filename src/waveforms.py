# -*- coding: utf-8 -*-
"""
waveforms.py — (report2) 실제 상용 OFDM 파형 + **점유 상태(occupancy) 모드**
==============================================================================

핵심 관점(패시브 레이더의 현실): 우리는 송신기를 **빌려 쓴다.** 그러니 "그 셀이 지금
무엇을 내보내고 있는가"가 곧 레이더 성능이다. 그리고 임의의 기지국이 **항상** 내보낸다고
믿을 수 있는 기준신호는 표준마다 딱 하나씩뿐이다:

  **상시(always-on) 기준신호 — 패시브 레이더의 기본선**
    LTE   : **CRS** — 매 서브프레임(1 ms) · 채널 전대역(18 MHz) → ΔR_b≈16.7 m(바이스태틱; 모노 8.3), PRF≈1 kHz
    5G NR : **SSB** — SS 버스트 20 ms 주기 · 중앙 20 RB 협대역(7.2 MHz) → ΔR_b≈41.6 m(바이스태틱; 모노 20.8), PRF≈50 Hz
    WiFi  : **프리앰블 LTF** — 패킷마다 · 광대역(VHT-LTF, 76 MHz) → ΔR_b≈3.9 m(바이스태틱; 모노 2.0), 단 반복률이 트래픽 의존

  ※ **5G 에는 LTE 의 CRS 같은 상시 전대역 셀기준이 없다**(NR 은 스펙트럼 절약을 위해
    파일럿을 얇게 편다). 유휴 gNB 가 늘 내보내는 건 SSB 뿐이며, SSB 는 **협대역 + 저반복**
    이라 거리(ΔR_b≈41.6 m)도 속도(≈1.1 m/s)도 나쁘다 = **5G 패시브 센싱의 이중고**.
    이것이 Rényi/LaSen 계열 문헌이 '기준신호만으로는 부족하다'며 출발하는 지점이다.

  **PRS 는 상시 신호가 아니다 — 측위 세션이 설정됐을 때만 켜지는 옵션이다.**
    PRS 가 켜지면 5G 는 전대역(98 MHz) 기준을 얻어 ΔR≈1.5 m 로 급전환하지만, 남의 셀을
    빌려 쓰는 패시브 수신기는 그것을 **가정할 수 없다**. 아래 점유 모드에서 PRS 는 G2/G3
    에서만 켜지므로, G2/G3 의 5G 성능은 '측위 세션이 켜진 낙관적 상한'으로 읽어야 한다.

점유 모드 G1/G2/G3 — **표준마다 의미가 다르다**(아래 MODES 참고):
  G1  유휴 셀    : **상시 기준신호만** — WiFi=프리앰블 / LTE=동기+CRS / 5G=SSB
                   → 패시브 레이더가 언제나 기댈 수 있는 **기본선(baseline)**
  G2  측위 세션  : + **PRS**(측위용, 전대역) + 제어(PDCCH/SIG) — 데이터 없음
  G3  풀로드     : + 데이터(PDSCH/DATA) 까지 꽉 — 상용 풀로드(+측위 세션)
  ※ 데이터(PDSCH)는 수신기가 **모르는** 신호라 정합필터 템플릿이 못 된다 → G3 가 되어도
    패시브 기준대역은 G2 와 같다(에너지만 늘 뿐). always_on_waveforms() 참고.

각 자원요소(RE)에 **채널 라벨**을 달아 '리소스 그리드 사진'(시간×주파수 이미지)으로
보여주고, 모드별로 (a)송신에너지 (b)정합필터 기준신호의 대역 → 거리분해능
(c)탐지 SNR 이 어떻게 달라지는지 비교합니다.

두 축(독립)으로 성능이 갈립니다:
  * **주파수축** — 기준신호가 점유한 *대역*  → 거리분해능 ΔR_b = c/B (바이스태틱; range_resolution_m). 모노 등가는 range_resolution_mono_m
  * **시간축**   — 기준신호의 *반복률(PRF)* → 최대속도 v_max = PRF·λ/4 (v_unambiguous_ms)
상시 기준신호로 비교하면: **LTE CRS** 는 전대역(18 MHz)+매 서브프레임(1 kHz) → 두 축 다 좋고,
**5G SSB** 는 협대역(7.2 MHz)+저반복(50 Hz) → 두 축 다 나쁘다. 이 대비가 report2 의 뼈대다.

표준별(조사: docs/waveform_research.json)
  WiFi  802.11ac : 패킷형. G1=프리앰블(L-STF/VHT-LTF), G3=+DATA. (프리앰블이 광대역→분해능 유지)
  LTE   Rel-9    : 15 kHz SCS, 20 MHz. PSS/SSS·CRS·PRS·PDCCH·PDSCH.
  5G NR Rel-16   : 30 kHz SCS, 100 MHz. SSB·PRS·DMRS·PDCCH·PDSCH.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np

C0 = 299792458.0

# --------------------------------------------------------------------------- #
#  채널 라벨(리소스 그리드 사진용)
# --------------------------------------------------------------------------- #
CH = {"EMPTY": 0, "PSS": 1, "SSS": 2, "PBCH": 3, "PRS": 4, "CRS": 5,
      "DMRS": 6, "PDCCH": 7, "PDSCH": 8, "LSTF": 9, "LLTF": 10, "WSIG": 11, "WDATA": 12}
CH_NAME = {v: k for k, v in CH.items()}
CH_COLOR = {                                   # 사진 색
    0: "#f2f2f4", 1: "#c62828", 2: "#ad1457", 3: "#6a1b9a", 4: "#1565c0",
    5: "#00897b", 6: "#2e7d32", 7: "#ef6c00", 8: "#cfd8dc",
    9: "#c62828", 10: "#1565c0", 11: "#ef6c00", 12: "#cfd8dc"}
# 점유 모드 → '켜는' 채널.  **표준별로 다르다**(각 표준이 실제로 쓰는 채널만).
#   WiFi : 패킷형(CSMA). 프리앰블 LTF 는 어떤 패킷에도 있고 늘 광대역 → 항상 기준 확보.
#          점유는 '패킷 종류'(프리앰블만 / +제어헤더 / +데이터)로 구분.
#   LTE  : CRS 가 매 서브프레임 전대역 상시 송신 → G1(유휴 셀)도 전대역 기준 보유.
#   5G NR: 상시 셀기준 없음. 유휴면 SSB(중앙 240부반송파, 협대역)만 → G1 분해능 나쁨.
#   ※ PRS 는 '점유가 차서' 켜지는 게 아니라 **측위 세션이 설정돼야** 켜지는 옵션 신호다.
#     여기선 G2/G3 를 '측위 세션이 켜진 셀'로 모형화한다 → G2/G3 의 5G 성능은 낙관적 상한.
MODES = {
    "wifi": {                                          # 802.11ac PPDU 구성요소
        "G1": {"LSTF", "LLTF"},                                  # 프리앰블만(짧은 관리/ACK)
        "G2": {"LSTF", "LLTF", "WSIG"},                          # + SIG 제어헤더(제어 프레임)
        "G3": {"LSTF", "LLTF", "WSIG", "WDATA"},                 # + DATA 페이로드(데이터 프레임)
    },
    "lte": {                                           # Rel-9 다운링크
        "G1": {"PSS", "SSS", "CRS"},                             # 상시: 동기 + CRS(전대역 기준)
        "G2": {"PSS", "SSS", "CRS", "PRS", "PDCCH"},             # + PRS(측위 세션) + 제어영역
        "G3": {"PSS", "SSS", "CRS", "PRS", "PDCCH", "PDSCH"},    # + 데이터
    },
    "nr": {                                            # Rel-16 다운링크
        "G1": {"PSS", "SSS", "PBCH"},                            # 상시: SSB(협대역 비콘)만
        "G2": {"PSS", "SSS", "PBCH", "PRS", "PDCCH"},            # + PRS(측위 세션·전대역) + 제어
        "G3": {"PSS", "SSS", "PBCH", "PRS", "PDCCH", "PDSCH", "DMRS"},  # + 데이터(+그 DMRS)
    },
}
# 점유 모드 한글 설명(표준별) — 시각화/노트북이 공유하는 단일 소스
MODE_DESC = {
    "wifi": {"G1": "프리앰블만(VHT-LTF·광대역)", "G2": "+SIG 제어헤더", "G3": "+DATA 페이로드"},
    "lte":  {"G1": "상시 CRS(전대역 기준)",    "G2": "+PRS측위+제어",  "G3": "+PDSCH 데이터"},
    "nr":   {"G1": "상시 SSB만(협대역 비콘)",  "G2": "+PRS측위+제어",  "G3": "+PDSCH 데이터"},
}
# 정합필터 기준으로 쓰는 '기지' 채널(패시브레이더 관점)
REF_CH = {"PRS", "PSS", "SSS", "PBCH", "CRS", "DMRS", "LLTF"}

# --- 시간축(slow-time) 파일럿 반복률 → 최대 무모호 속도 ---------------------- #
# 패시브레이더는 '기준신호가 반복될 때마다' 채널을 한 번 샘플한다. 그 반복률(PRF)이
# 표적 도플러의 Nyquist 한계를 정한다:  f_d = 2v/λ,  PRF ≥ 2·f_d,max  →  v_max = PRF·λ/4.
# 기준신호마다 시간축 반복률이 다르다(전형적 배치값; 실제로는 설정가변):
#   LTE  CRS  : 매 서브프레임(1ms) 존재          → ~1 kHz   (드론 ~42 m/s 까지 OK)
#   5G   SSB  : SS 버스트 주기 20ms              → ~50 Hz   (~1.1 m/s — 유휴 5G 의 한계)
#   5G   PRS/CSI-RS : 측위 세션 설정 시          → ~200 Hz  (~4.3 m/s)
#   WiFi LTF  : 패킷당 1회(트래픽 의존)          → ~1 kHz(혼잡 AP) / 비콘만이면 ~10 Hz
#     (802.11 기본 비콘 주기 100 TU = 102.4 ms → 9.77 Hz; AP 1대 기준)
#     즉 트래픽이 없으면 WiFi 는 5G SSB(50 Hz)보다도 느려진다(5.2 GHz 에서 v_max≈0.14 m/s).
#     아래 dict 의 1 kHz 는 '혼잡 AP' 대표값이며 report2 그림·report5 듀티 규약의 단일 소스다.
# ※ 이 '반복률'(속도 한계)은 주파수축 대역(거리분해능)과 **독립**이다. 상시 기준신호끼리
#   비교하면 LTE CRS(전대역·1kHz) ≫ 5G SSB(협대역·50Hz) — 5G 는 거리도 속도도 나쁘다(이중고).
#   (DMRS 는 데이터에 종속·간헐적이라 slow-time 기준에서 제외.)
PILOT_RATE_HZ = {
    "wifi": {"LLTF": 1000.0},                                  # 패킷률(혼잡 AP 대표값)
    "lte":  {"CRS": 1000.0, "PSS": 200.0, "SSS": 200.0,
             "PRS": 6.25},                                     # LTE PRS 주기 ≥160ms → ≤6.25Hz. CRS(1kHz)가 max()를 지배해 출력엔 영향 없음
    "nr":   {"PSS": 50.0, "SSS": 50.0, "PBCH": 50.0,           # SSB 20ms 버스트 → 50Hz
             "PRS": 200.0},                                    # 전형적 측위/추적 설정값(설정가변). 표준 최소주기 4슬롯 → μ=1(30kHz)에서 2ms = 최대 ~500Hz(v_max≈10.7 m/s), 유휴시 50~100Hz
}
# ※ WiFi 의 광대역 기준은 **VHT-LTF**(802.11ac 80MHz 전대역, 242톤 ±1)를 모사한다.
#   레거시 L-LTF 는 20MHz 짜리를 4개 서브채널에 복제하는 구조라, 그걸 그대로 타일링해 쓰면
#   시간축에 콤이 생겨 자기상관에 7.5m 주기 거리 고스트가 뜬다(그래서 쓰지 않는다).


@dataclass
class Waveform:
    name: str
    std: str                 # 'wifi'/'lte'/'nr'
    mode: str                # 'G1'/'G2'/'G3'
    carrier_hz: float
    bw_hz: float             # 채널 점유 대역(최대)
    scs_hz: float
    fft: int
    fs_hz: float
    cp_lens: object
    grid: np.ndarray         # (nsym, fft) 복소
    labels: np.ndarray       # (nsym, fft) 채널 라벨
    used: np.ndarray         # 사용 부반송파(중앙기준)
    tx: np.ndarray           # 시간영역 송신
    ref: np.ndarray          # 정합필터 기준(기지 채널만)
    ref_bw_hz: float         # 기준신호가 점유한 대역(→ 실제 거리분해능)
    notes: str = ""

    @property
    def range_resolution_m(self):                       # 기준신호 대역 기준 — **바이스태틱** ΔR_b
        # ⚠ 2026-07-16 규약 통일(정합성 검증): 이 프로젝트는 **바이스태틱** 패시브 레이더다.
        #   RD 맵의 거리축은 바이스태틱 거리 R_b=R1+R2−L(왕복 아님) 이므로 분해능은 c/(2B) 가 아니라
        #   **ΔR_b = c/B** 다(문헌 25_UAV Intrusion·report11 §2 동일). 모노스태틱 등가값은 이 절반.
        return C0 / max(self.ref_bw_hz, 1.0)
    @property
    def channel_res_m(self):                            # 채널 대역 기준(이상적) — 바이스태틱
        return C0 / self.bw_hz
    @property
    def range_resolution_mono_m(self):                  # 모노스태틱 등가(참고용) — c/2B
        return C0 / (2 * max(self.ref_bw_hz, 1.0))
    @property
    def pilot_rate_hz(self):
        """기준신호가 slow-time 으로 반복되는 최대 속도[Hz] (가장 촘촘한 기지 파일럿)."""
        present = set(self.labels.ravel().tolist())
        rates = [r for ch, r in PILOT_RATE_HZ.get(self.std, {}).items()
                 if CH.get(ch) in present]
        return max(rates) if rates else 0.0
    @property
    def v_unambiguous_ms(self):
        """최대 무모호(no-alias) 속도 v_max = PRF·λ/4 [m/s]. PRF=pilot_rate_hz.
        ⚠ 모노스태틱 등가치다 — f_d=2v/λ 를 가정한다. 바이스태틱에서는 도플러가
        f_d=(v/λ)·2cos(β/2)cosδ 이므로 같은 PRF 라도 실제 무모호 속도는 이 값을
        기하인자 1/(cos(β/2)cosδ) 만큼 재배율해야 한다(report04 §도플러 참조).
        여기서는 파형 간 비교용 공통 기준으로 모노 등가치를 반환한다."""
        lam = C0 / self.carrier_hz
        return self.pilot_rate_hz * lam / 4.0
    @property
    def duration_us(self):
        return len(self.tx) / self.fs_hz * 1e6
    @property
    def tx_energy(self):
        return float(np.sum(np.abs(self.tx) ** 2))
    @property
    def occupancy_frac(self):
        return float(np.mean(self.labels != CH["EMPTY"]))
    @property
    def ref_name(self):
        present = set(self.labels.ravel().tolist())
        if self.std == "wifi":
            return "VHT-LTF"                           # 80MHz 전대역 기준(레거시 L-LTF 는 20MHz)
        if CH["PRS"] in present:                       # PRS 켜지면 전대역 측위기준 우선
            return "NR-PRS" if self.std == "nr" else "PRS"
        if self.std == "nr":
            return "SSB"                               # 5G G1: SSB(협대역)
        # LTE: PRS 없으면 CRS(상시·전대역)가 실제 기준, 그것도 없으면 동기만
        return "CRS" if CH["CRS"] in present else "PSS/SSS"


# --------------------------------------------------------------------------- #
#  공통 DSP
# --------------------------------------------------------------------------- #
def gold_seq(c_init, length, Nc=1600):
    x1 = np.zeros(Nc + length + 31, np.int8); x2 = np.zeros(Nc + length + 31, np.int8)
    x1[0] = 1
    for i in range(31):
        x2[i] = (int(c_init) >> i) & 1
    for n in range(Nc + length):
        x1[n + 31] = (x1[n + 3] ^ x1[n]) & 1
        x2[n + 31] = (x2[n + 3] ^ x2[n + 2] ^ x2[n + 1] ^ x2[n]) & 1
    return (x1[Nc:Nc + length] ^ x2[Nc:Nc + length]).astype(np.int8)


def qpsk_from_gold(c_init, n):
    c = gold_seq(c_init, 2 * n)
    return ((1 - 2 * c[0::2]) + 1j * (1 - 2 * c[1::2])) / np.sqrt(2)


def rand_qam(rng, n, order=16):
    m = int(np.sqrt(order)); lv = np.arange(-(m - 1), m, 2)
    return (rng.choice(lv, n) + 1j * rng.choice(lv, n)) / np.sqrt((np.abs(np.unique(lv)) ** 2).mean() * 2)


def ofdm_modulate(grid, fft, cp_lens):
    nsym = grid.shape[0]
    cp_lens = [int(cp_lens)] * nsym if np.isscalar(cp_lens) else list(cp_lens)
    out = []
    for i in range(nsym):
        t = np.fft.ifft(np.fft.ifftshift(grid[i])) * np.sqrt(fft)
        out.append(np.concatenate([t[fft - cp_lens[i]:], t]))
    return np.concatenate(out)


def _ci(fft, idx):          # 중앙기준 부반송파 → 절대 인덱스
    return fft // 2 + np.asarray(idx)


def _ref_grid(grid, labels):
    """기지(known) 채널 RE 만 남긴 기준 그리드."""
    keep = np.isin(labels, [CH[c] for c in REF_CH])
    return np.where(keep, grid, 0.0)


def _ref_bw(labels, scs):
    """기준신호가 차지한 '부반송파 폭' → 대역[Hz]."""
    keep = np.isin(labels, [CH[c] for c in REF_CH])
    cols = np.where(keep.any(axis=0))[0]
    if len(cols) == 0:
        return scs
    return (cols.max() - cols.min() + 1) * scs


def _finish(name, std, mode, carrier, bw, scs, fft, fs, cp_lens, grid, labels, used, notes=""):
    tx = ofdm_modulate(grid, fft, cp_lens)
    refg = _ref_grid(grid, labels)
    ref = ofdm_modulate(refg, fft, cp_lens)
    rbw = _ref_bw(labels, scs)
    return Waveform(name, std, mode, carrier, bw, scs, fft, fs, cp_lens,
                    grid, labels, used, tx, ref, rbw, notes)


# --------------------------------------------------------------------------- #
#  WiFi 802.11ac
# --------------------------------------------------------------------------- #
def wifi_80211ac(bw_hz=80e6, carrier_hz=5.21e9, occupancy="G3", n_data_sym=10, seed=1):
    on = MODES["wifi"][occupancy]; scs = 312.5e3
    fft = int(round(bw_hz / scs)); fs = fft * scs; cp = fft // 4
    rng = np.random.default_rng(seed)
    # 802.11ac VHT80 점유 톤 = **242**(234 데이터 + 8 파일럿). 부반송파 인덱스는 −122..−2, +2..+122
    # (DC 와 ±1 은 널 — IEEE 802.11-2016 §21.3.7). 이전 판은 ±1..±121 이라 개수만 맞고 위치가
    # 한 칸씩 밀려 널 톤(±1)에 에너지를 싣고 ±122 를 비웠다 → 표준 인덱스로 정정.
    sc_max = int(round(fft * 122 / 256))                      # 80MHz(fft=256) → 122
    used = np.r_[np.arange(-sc_max, -1), np.arange(2, sc_max + 1)]
    PILOT_SC = np.array([-103, -75, -39, -11, 11, 39, 75, 103])   # VHT80 파일럿 톤
    data_sc = np.array([k for k in used if k not in set(PILOT_SC.tolist())])
    rows, labs = [], []

    def addrow(vals_full, lab_full):
        rows.append(vals_full); labs.append(lab_full)

    # L-STF: 4의 배수 톤만(±4,8,…) — 시간축 0.8µs 주기성의 근원. used[::4] 는 격자가 어긋나 주기성이 깨졌다.
    r = np.zeros(fft, complex); l = np.zeros(fft, int)
    if "LSTF" in on:
        idx = np.arange(-sc_max, sc_max + 1, 4); idx = idx[idx != 0]
        r[_ci(fft, idx)] = np.sqrt(13/6) * (1 + 1j); l[_ci(fft, idx)] = CH["LSTF"]
    addrow(r, l)
    # VHT-LTF ×1 (정합필터 기준) — 242톤 전체에 ±1 시퀀스.
    #   ※ 레거시 L-LTF(20MHz)를 80MHz 로 '타일링'하면 주파수축이 주기적이 되어 시간축에 콤이 생기고,
    #     자기상관에 7.5 m 주기의 가짜 피크(거리 고스트)가 뜬다 → 쓰지 않는다.
    #   ※ 심볼을 2회 반복하면 자기상관이 심볼 간격(±600 m)에서 −6 dB 로 되살아난다. 802.11ac 는
    #     Nss=1 이면 N_VHTLTF = **1 심볼**이므로 1개만 둔다(고스트 자체가 생기지 않음).
    ltf_vals = (1 - 2 * gold_seq(0x5A5, len(used))).astype(complex)
    r = np.zeros(fft, complex); l = np.zeros(fft, int)
    if "LLTF" in on:
        r[_ci(fft, used)] = ltf_vals; l[_ci(fft, used)] = CH["LLTF"]
    addrow(r, l)
    # SIG (제어 헤더) — 데이터 톤 BPSK + 파일럿 톤
    r = np.zeros(fft, complex); l = np.zeros(fft, int)
    if "WSIG" in on:
        r[_ci(fft, data_sc)] = (1 - 2 * rng.integers(0, 2, len(data_sc)))
        r[_ci(fft, PILOT_SC)] = 1.0
        l[_ci(fft, used)] = CH["WSIG"]
    addrow(r, l)
    # DATA — 234 데이터 톤(QAM) + 8 파일럿 톤(±1 BPSK)
    for _ in range(n_data_sym):
        r = np.zeros(fft, complex); l = np.zeros(fft, int)
        if "WDATA" in on:
            r[_ci(fft, data_sc)] = rand_qam(rng, len(data_sc))
            r[_ci(fft, PILOT_SC)] = 1 - 2 * rng.integers(0, 2, len(PILOT_SC))
            l[_ci(fft, used)] = CH["WDATA"]
        addrow(r, l)
    grid = np.array(rows); labels = np.array(labs)
    return _finish("WiFi 802.11ac", "wifi", occupancy, carrier_hz, len(used) * scs,
                   scs, fft, fs, cp, grid, labels, used, f"VHT {bw_hz/1e6:.0f}MHz, 5GHz")


# --------------------------------------------------------------------------- #
#  LTE Rel-9 다운링크 (1 서브프레임 = 14 sym)
# --------------------------------------------------------------------------- #
def lte_downlink(bw_hz=20e6, carrier_hz=1.843e9, occupancy="G3", n_id=0, seed=2):
    on = MODES["lte"][occupancy]; scs = 15e3
    fft = 2048 if bw_hz >= 20e6 else 1024; fs = fft * scs
    n_rb = {20e6: 100, 10e6: 50, 5e6: 25}.get(bw_hz, 100); n_used = n_rb * 12
    used = np.r_[np.arange(-n_used // 2, 0), np.arange(1, n_used // 2 + 1)]
    # CP 는 fs 에 비례(TS 36.211 의 160/144 는 fs=30.72 Msps 기준) — fft=1024(10 MHz)면 80/72.
    #   고정하면 서브프레임이 1 ms 를 벗어난다(10 MHz 에서 1.067 ms, PRF 937.5 Hz 왜곡).
    sc = fft / 2048
    cp_lens = ([int(160 * sc)] + [int(144 * sc)] * 6) * 2; nsym = 14
    rng = np.random.default_rng(seed)
    grid = np.zeros((nsym, fft), complex); labels = np.zeros((nsym, fft), int)

    def put(l, idx, vals, ch):
        ai = _ci(fft, idx); grid[l, ai] = vals; labels[l, ai] = CH[ch]

    # PDSCH (G3): 먼저 데이터로 채움
    if "PDSCH" in on:
        for l in range(3, nsym):
            put(l, used, rand_qam(rng, n_used), "PDSCH")
    # PDCCH (G2/G3): 제어영역 첫 3 심볼
    if "PDCCH" in on:
        for l in range(3):
            put(l, used, rand_qam(rng, n_used) * 0.9, "PDCCH")
    # ⚠ LTE 는 DC 부반송파를 **송신하지 않고 건너뛴다**(TS 36.211 §6.12) — comb 격자는 'RE 번호'(0..n_used-1)
    #   위에서 세고, 그 다음에 물리 부반송파로 사상해야 한다. 물리축에서 바로 6간격으로 깔면 DC 를 지나며
    #   상반대역이 통째로 1 부반송파(15 kHz) 밀린다(이전 판의 버그).
    def _re_to_sc(k):
        """논리 RE 번호(0..n_used-1) → 물리 부반송파(음수 …, −1, +1, …; DC 없음)."""
        half = n_used // 2
        return np.where(k < half, k - half, k - half + 1)

    # CRS (상시): 포트0 → 슬롯당 l=0,4 · comb-6.  v_shift = n_id % 6 (TS 36.211 §6.10.1.2)
    if "CRS" in on:
        for sl in range(2):
            for li, v in ((0, 0), (4, 3)):
                l = sl * 7 + li
                k = np.arange((v + n_id) % 6, n_used, 6)
                put(l, _re_to_sc(k), qpsk_from_gold((l + 1) * (2 * n_id + 1) * 1024 + n_id, len(k)) * np.sqrt(2), "CRS")
    # PRS (측위 세션): comb-6 대각. TS 36.211 §6.10.4.2 — normal CP 에서 짝수슬롯 l∈{3,5,6},
    #   홀수슬롯 l∈{1,2,3,5,6} (총 8 심볼). 이전 판은 홀수슬롯의 l=1,2 가 빠져 6 심볼뿐이었다.
    if "PRS" in on:
        for sl in range(2):
            for li in ((3, 5, 6) if sl == 0 else (1, 2, 3, 5, 6)):
                l = sl * 7 + li
                k = np.arange((6 - n_id % 6 + li) % 6, n_used, 6)
                put(l, _re_to_sc(k), qpsk_from_gold(2**22 + l * 97 + n_id, len(k)) * np.sqrt(2), "PRS")
    # PSS/SSS (항상): 중앙 62 부반송파, l=6(PSS)/5(SSS) of slot0
    cen = np.r_[np.arange(-31, 0), np.arange(1, 32)]
    if "PSS" in on: put(6, cen, qpsk_from_gold(101, len(cen)), "PSS")
    if "SSS" in on: put(5, cen, qpsk_from_gold(102, len(cen)), "SSS")
    return _finish("LTE Rel-9", "lte", occupancy, carrier_hz, n_used * scs,
                   scs, fft, fs, cp_lens, grid, labels, used, f"FDD {bw_hz/1e6:.0f}MHz, 1.8GHz")


# --------------------------------------------------------------------------- #
#  5G NR Rel-16 다운링크 (1 슬롯 = 14 sym)
# --------------------------------------------------------------------------- #
def nr_downlink(bw_hz=100e6, scs_hz=30e3, carrier_hz=3.5e9, occupancy="G3", n_id=1, seed=3):
    on = MODES["nr"][occupancy]
    fft = 4096; fs = fft * scs_hz
    n_rb = 273 if bw_hz >= 100e6 else 51; n_used = n_rb * 12
    # NR 은 LTE 와 달리 **예약 DC 널이 없다**(TS 38.211 — DC 위치는 시그널링될 뿐 펑처되지 않음).
    # SSB·PRS 도 실제로 k=0 에 송신하므로, 연속 격자를 쓴다(이전 판은 LTE 관습대로 k=0 을 빼 자기모순).
    used = np.arange(-n_used // 2, n_used // 2)
    # NR μ=1 정상 CP: 0.5ms 슬롯(=14 sym) 첫 심볼만 긴 CP(352), 나머지 288 →
    #   14·4096 + 352 + 13·288 = 61440 = 정확히 500 µs (TS 38.211 §5.3.1)
    cp = [352] + [288] * 13; nsym = 14
    rng = np.random.default_rng(seed)
    grid = np.zeros((nsym, fft), complex); labels = np.zeros((nsym, fft), int)

    def put(l, idx, vals, ch):
        ai = _ci(fft, idx); grid[l, ai] = vals; labels[l, ai] = CH[ch]

    # PDSCH (G3)
    if "PDSCH" in on:
        for l in range(2, nsym):
            put(l, used, rand_qam(rng, n_used, 64), "PDSCH")
    # PDCCH/CORESET (G2/G3): 첫 2 심볼
    if "PDCCH" in on:
        for l in range(2):
            put(l, used, rand_qam(rng, n_used) * 0.9, "PDCCH")
    # PDSCH-DMRS (G3 전용): l=2, comb-2 — PDSCH 가 스케줄될 때만 함께 송신된다(TS 38.211).
    #   데이터 없는 슬롯(G2)에 PDSCH-DMRS 만 뜨는 그리드는 표준상 불가능하므로 G2 에서 제외.
    if "DMRS" in on:
        idx = np.arange(-n_used // 2, n_used // 2, 2)
        put(2, idx, qpsk_from_gold(2048 + n_id, len(idx)), "DMRS")
    # NR-PRS (G2/G3): comb-4 대각 전대역, l=4..9
    #   ※ PDSCH 를 먼저 깐 뒤 PRS 로 덮어쓴다 → PRS 와 PDSCH 는 **같은 RE 를 절대 공유하지 않는다.**
    #     이것이 표준의 'PDSCH rate matching around DL-PRS'(TS 38.214)다: PRS 심볼(4~9) 안에서도
    #     PDSCH 는 PRS 가 안 쓰는 나머지 부반송파(comb-4 → 3/4)를 채운다.
    #   ※ 참고로 3GPP 의 'PRS muting' 은 "다른 자원을 비운다"가 아니라, 셀이 자기 PRS 를 일부 occasion
    #     에서 안 쏴서 **이웃 셀 PRS 의 hearability** 를 높이는 셀 간 패턴이다. 다만 실제 망은 측위
    #     정확도를 위해 PRS occasion 에 데이터를 적게 싣는 경향이 있으므로, 여기의 G3(PRS+풀데이터)는
    #     **송신에너지 상한**으로 읽는 게 안전하다. 패시브 결론(PDSCH 는 미지 → 기준 못 됨)은 불변.
    #   ※ comb-N 과 심볼 수는 표준 조합만 유효하다(TS 38.211 Table 7.4.1.7.3-1): comb-4 는 4 또는 12 심볼.
    #     comb-4 × 6심볼은 표준에 없는 조합이라 **comb-4 × 4심볼(l=4..7)** 로 바로잡고, 심볼별 주파수
    #     오프셋도 표준 패턴 [0,2,1,3] 을 쓴다(이전 판은 li%4 선형 램프).
    if "PRS" in on:
        for i, sh in enumerate((0, 2, 1, 3)):
            li = 4 + i
            idx = np.arange(-n_used // 2 + sh, n_used // 2, 4)
            put(li, idx, qpsk_from_gold(2**20 + li * 131 + n_id, len(idx)) * 2.0, "PRS")
    # SSB (항상): 블록 중앙 240 부반송파(20 RB), l=0..3 (TS 38.211 §7.4.3 Table 7.4.3.1-1)
    #   ※ PSS/SSS 시퀀스는 표준의 m-sequence 대신 Gold-QPSK 로 근사한다. 본 리포트에서 PSS/SSS 는
    #     기준신호 대역(PBCH 240 SC 가 결정)·분해능·PRF 어디에도 영향이 없어 결론에 무영향.
    #   PSS(l=0)·SSS(l=2) = 블록 내 중앙 **127** 부반송파, PBCH = l=1,3 전체(240) + **l=2 의 양측 48+48**.
    #   ※ SSB 영역은 다른 채널이 쓰지 못하므로(rate matching around SSB, TS 38.214 §5.1.4)
    #     먼저 블록 전체를 비운 뒤 SSB 를 그린다 — 안 그러면 PDSCH/PDCCH 가 SSB 안으로 침범한다.
    ssb = np.arange(-120, 120)                     # SSB 블록 폭(20 RB)
    ssb_sync = np.arange(-63, 64)                  # PSS/SSS: 중앙 127 부반송파
    ssb_side = np.r_[np.arange(-120, -72), np.arange(72, 120)]   # l=2 의 PBCH 측대역(48+48)
    if "PSS" in on or "PBCH" in on:
        c = fft // 2
        grid[0:4, c - 120:c + 120] = 0.0           # SSB 블록 예약(다른 채널 지움)
        labels[0:4, c - 120:c + 120] = CH["EMPTY"]
    if "PSS" in on: put(0, ssb_sync, qpsk_from_gold(11 + n_id, len(ssb_sync)), "PSS")
    if "PBCH" in on:
        put(1, ssb, qpsk_from_gold(12 + n_id, len(ssb)), "PBCH")
        put(3, ssb, qpsk_from_gold(14 + n_id, len(ssb)), "PBCH")
        put(2, ssb_side, qpsk_from_gold(15 + n_id, len(ssb_side)), "PBCH")   # l=2 측대역
    if "SSS" in on: put(2, ssb_sync, qpsk_from_gold(13 + n_id, len(ssb_sync)), "SSS")
    return _finish("5G NR Rel-16", "nr", occupancy, carrier_hz, n_used * scs_hz,
                   scs_hz, fft, fs, cp, grid, labels, used, f"n78 {bw_hz/1e6:.0f}MHz, 30kHz, 3.5GHz")


def all_waveforms(occupancy="G3"):
    return {"wifi": wifi_80211ac(occupancy=occupancy),
            "lte": lte_downlink(occupancy=occupancy),
            "nr": nr_downlink(occupancy=occupancy)}


def always_on_waveforms():
    """**패시브 레이더의 기본선** — 임의의 셀이 *항상* 내보내는 기준신호만 켠 파형(=G1).

    WiFi=프리앰블 **VHT-LTF**(76MHz) · LTE=**CRS**(전대역 18MHz, 1kHz) · 5G=**SSB**(7.2MHz, 50Hz).
    PRS 는 측위 세션이 설정돼야 켜지므로 여기 없다(그 경우는 all_waveforms('G2'/'G3')).
    남의 송신기를 빌려 쓰는 패시브 수신기가 사전 협상 없이 기댈 수 있는 건 이 집합뿐이다.
    """
    return all_waveforms("G1")


def autocorr_resolution(ref, fs):
    r = np.abs(np.correlate(ref, ref, mode="full")); r /= r.max() + 1e-30
    pk = len(r) // 2; half = np.where(r[pk:] < 0.707)[0]
    return (half[0] if len(half) else 1) / fs * C0 / 2, r


if __name__ == "__main__":
    for mode in ("G1", "G2", "G3"):
        print(f"\n== 점유모드 {mode} ==")
        for k, wf in all_waveforms(mode).items():
            print(f"  {wf.name:15s} 점유율={wf.occupancy_frac*100:5.1f}%  "
                  f"기준={wf.ref_name:7s}  "
                  f"대역={wf.ref_bw_hz/1e6:6.1f}MHz→{wf.range_resolution_m:5.2f}m  "
                  f"반복률={wf.pilot_rate_hz:6.0f}Hz→{wf.v_unambiguous_ms:5.1f}m/s  "
                  f"에너지={10*np.log10(wf.tx_energy+1e-30):6.1f}dB")
