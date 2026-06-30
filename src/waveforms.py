# -*- coding: utf-8 -*-
"""
waveforms.py — (report2) 실제 상용 OFDM 파형 + **점유 상태(occupancy) 모드**
==============================================================================

핵심 추가(현실성): 실제 LTE/5G 셀은 **항상 꽉 차 있지 않습니다.** 한가한 셀은
동기/방송 신호(SSB)만, 측위 중이면 기준신호(PRS/CRS) 위주, 트래픽이 많을 때만
데이터(PDSCH)까지 꽉 찹니다. 패시브 레이더는 보통 **기지(known) 파일럿/기준신호만**
활용하므로, 이 점유 상태별 차이를 실험으로 비교합니다.

점유 모드 G1/G2/G3 — **표준마다 의미가 다르다**(아래 MODES 참고). 실제 셀의 전형적
점유 단계를 표준별 채널 구성으로 옮긴 것:
  G1  한가한 셀  : WiFi=프리앰블만 / LTE=동기+CRS(상시·전대역) / 5G=SSB(협대역 비콘)만
  G2  기준+제어  : + 측위/기준신호(PRS 등) + 제어(PDCCH/SIG) — 데이터 없음
  G3  풀로드     : + 데이터(PDSCH/DATA) 까지 꽉 — 상용 풀로드
  ※ 핵심 차이: **LTE 는 CRS 가 매 서브프레임 전대역 상시** → 한가해도(G1) 거리분해능이
    좋다. **5G 는 상시 셀기준이 없어** 한가하면 SSB(협대역)뿐 → G1 거리분해능이 나쁨
    (이것이 5G 패시브레이더의 고유 난제 — Rényi/LaSen 계열 문헌의 출발점).

각 자원요소(RE)에 **채널 라벨**을 달아 '리소스 그리드 사진'(시간×주파수 이미지)으로
보여주고, 모드별로 (a)송신에너지 (b)정합필터 기준신호의 대역 → 거리분해능
(c)탐지 SNR 이 어떻게 달라지는지 비교합니다.

두 축(독립)으로 성능이 갈립니다:
  * **주파수축** — 기준신호가 점유한 *대역*  → 거리분해능 ΔR = c/2B  (range_resolution_m)
  * **시간축**   — 기준신호의 *반복률(PRF)* → 최대속도 v_max = PRF·λ/4 (v_unambiguous_ms)
LTE 의 CRS 는 상시 전대역(B 큼)+매 서브프레임(PRF 큼) → 두 축 다 좋다. 5G 는 한가하면
SSB 뿐 → 협대역(B 작음)+저반복(PRF 작음) → 두 축 다 나쁘다(= 5G 패시브레이더의 이중고).

표준별(조사: docs/waveform_research.json)
  WiFi  802.11ac : 패킷형. G1=프리앰블(L-STF/L-LTF), G3=+DATA. (프리앰블이 광대역→분해능 유지)
  LTE   Rel-9    : 15 kHz SCS, 20 MHz. PSS/SSS·CRS·PRS·PDCCH·PDSCH.
  5G NR Rel-16   : 30 kHz SCS, 100 MHz. SSB·PRS·DMRS·PDCCH·PDSCH.
"""
from __future__ import annotations

from dataclasses import dataclass, field
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
#   WiFi : 패킷형(CSMA). 프리앰블(L-LTF)은 어떤 패킷에도 있고 늘 광대역 → 항상 기준 확보.
#          점유는 '패킷 종류'(프리앰블만 / +제어헤더 / +데이터)로 구분.
#   LTE  : CRS 가 매 서브프레임 전대역 상시 송신 → G1(한가한 셀)도 전대역 기준 보유.
#   5G NR: 상시 셀기준 없음. 한가하면 SSB(중앙 240부반송파, 협대역)만 → G1 분해능 나쁨.
MODES = {
    "wifi": {                                          # 802.11ac PPDU 구성요소
        "G1": {"LSTF", "LLTF"},                                  # 프리앰블만(짧은 관리/ACK)
        "G2": {"LSTF", "LLTF", "WSIG"},                          # + SIG 제어헤더(제어 프레임)
        "G3": {"LSTF", "LLTF", "WSIG", "WDATA"},                 # + DATA 페이로드(데이터 프레임)
    },
    "lte": {                                           # Rel-9 다운링크
        "G1": {"PSS", "SSS", "CRS"},                             # 동기 + CRS(상시·전대역 기준)
        "G2": {"PSS", "SSS", "CRS", "PRS", "PDCCH"},             # + PRS(측위) + 제어영역
        "G3": {"PSS", "SSS", "CRS", "PRS", "PDCCH", "PDSCH"},    # + 데이터
    },
    "nr": {                                            # Rel-16 다운링크
        "G1": {"PSS", "SSS", "PBCH"},                            # SSB(협대역 비콘)만
        "G2": {"PSS", "SSS", "PBCH", "PRS", "DMRS", "PDCCH"},    # + PRS(전대역 측위)+DMRS+제어
        "G3": {"PSS", "SSS", "PBCH", "PRS", "DMRS", "PDCCH", "PDSCH"},  # + 데이터
    },
}
# 점유 모드 한글 설명(표준별) — 시각화/노트북이 공유하는 단일 소스
MODE_DESC = {
    "wifi": {"G1": "프리앰블만(L-LTF·광대역)", "G2": "+SIG 제어헤더", "G3": "+DATA 페이로드"},
    "lte":  {"G1": "동기+CRS상시(전대역기준)",  "G2": "+PRS측위+제어",  "G3": "+PDSCH 데이터"},
    "nr":   {"G1": "SSB만(협대역 비콘)",        "G2": "+PRS측위+DMRS",  "G3": "+PDSCH 데이터"},
}
# 정합필터 기준으로 쓰는 '기지' 채널(패시브레이더 관점)
REF_CH = {"PRS", "PSS", "SSS", "PBCH", "CRS", "DMRS", "LLTF"}

# --- 시간축(slow-time) 파일럿 반복률 → 최대 무모호 속도 ---------------------- #
# 패시브레이더는 '기준신호가 반복될 때마다' 채널을 한 번 샘플한다. 그 반복률(PRF)이
# 표적 도플러의 Nyquist 한계를 정한다:  f_d = 2v/λ,  PRF ≥ 2·f_d,max  →  v_max = PRF·λ/4.
# 기준신호마다 시간축 반복률이 다르다(전형적 배치값; 실제로는 설정가변):
#   LTE  CRS  : 매 서브프레임(1ms) 존재          → ~1 kHz   (드론 ~42 m/s 까지 OK)
#   5G   SSB  : SS 버스트 주기 20ms              → ~50 Hz   (~1.1 m/s — 한가한 5G의 한계)
#   5G   PRS/CSI-RS : 측위/추적 설정             → ~200 Hz  (~4.3 m/s)
#   WiFi L-LTF: 패킷당 1회(트래픽 의존)          → ~1 kHz(혼잡 AP) / ~333 Hz(비콘만)
# ※ 이 '반복률'(속도 한계)은 주파수축 대역(거리분해능)과 **독립**이다. 그래서 5G 는
#   한가하면 SSB 뿐 → 거리(협대역)도 속도(저반복률)도 모두 나쁘다 = 5G 패시브레이더의 이중고.
#   (DMRS 는 데이터에 종속·간헐적이라 slow-time 기준에서 제외.)
PILOT_RATE_HZ = {
    "wifi": {"LLTF": 1000.0},                                  # 패킷률(혼잡 AP 대표값)
    "lte":  {"CRS": 1000.0, "PSS": 200.0, "SSS": 200.0, "PRS": 100.0},
    "nr":   {"PSS": 50.0, "SSS": 50.0, "PBCH": 50.0,           # SSB 20ms 버스트 → 50Hz
             "PRS": 200.0},                                    # 촘촘한 측위/추적 설정(≤5ms)일 때의 상한; 유휴시엔 50~100Hz로 더 낮음
}
# ※ WiFi 의 기준은 코드에선 L-LTF 를 80MHz 전대역으로 타일링한다. 엄밀히 802.11ac 80MHz의
#   전대역 기준은 VHT-LTF 이며(레거시 L-LTF 는 20MHz 중복), 여기선 그 전대역 기준을 근사한다.


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
    def range_resolution_m(self):                       # 기준신호 대역 기준
        return C0 / (2 * max(self.ref_bw_hz, 1.0))
    @property
    def channel_res_m(self):                            # 채널 대역 기준(이상적)
        return C0 / (2 * self.bw_hz)
    @property
    def pilot_rate_hz(self):
        """기준신호가 slow-time 으로 반복되는 최대 속도[Hz] (가장 촘촘한 기지 파일럿)."""
        present = set(self.labels.ravel().tolist())
        rates = [r for ch, r in PILOT_RATE_HZ.get(self.std, {}).items()
                 if CH.get(ch) in present]
        return max(rates) if rates else 0.0
    @property
    def v_unambiguous_ms(self):
        """최대 무모호(no-alias) 속도 v_max = PRF·λ/4 [m/s]. PRF=pilot_rate_hz."""
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
            return "L-LTF"
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


def _ci(g, fft, idx):       # 중앙기준 부반송파 → 절대 인덱스
    return fft // 2 + np.asarray(idx)


def _ref_grid(grid, labels):
    """기지(known) 채널 RE 만 남긴 기준 그리드."""
    keep = np.isin(labels, [CH[c] for c in REF_CH])
    return np.where(keep, grid, 0.0)


def _ref_bw(labels, used_count, scs, fft):
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
    rbw = _ref_bw(labels, len(used), scs, fft)
    return Waveform(name, std, mode, carrier, bw, scs, fft, fs, cp_lens,
                    grid, labels, used, tx, ref, rbw, notes)


# --------------------------------------------------------------------------- #
#  WiFi 802.11ac
# --------------------------------------------------------------------------- #
_LLTF = np.array([0,0,0,0,0,0,1,1,-1,-1,1,1,-1,1,-1,1,1,1,1,1,1,-1,-1,1,1,-1,1,
                  -1,1,1,1,1,0,1,-1,-1,1,1,-1,1,-1,1,-1,-1,-1,-1,-1,1,1,-1,-1,1,
                  -1,1,-1,1,1,1,1,0,0,0,0,0], float)


def wifi_80211ac(bw_hz=80e6, carrier_hz=5.21e9, occupancy="G3", n_data_sym=10, seed=1):
    on = MODES["wifi"][occupancy]; scs = 312.5e3
    fft = int(round(bw_hz / scs)); fs = fft * scs; cp = fft // 4
    rng = np.random.default_rng(seed)
    half = int(fft * 26 / 64); used = np.r_[np.arange(-half, 0), np.arange(1, half + 1)]
    rows, labs = [], []

    def addrow(vals_full, lab_full):
        rows.append(vals_full); labs.append(lab_full)

    # L-STF
    r = np.zeros(fft, complex); l = np.zeros(fft, int)
    if "LSTF" in on:
        idx = used[::4]; r[_ci(r, fft, idx)] = np.sqrt(13/6) * (1 + 1j); l[_ci(l, fft, idx)] = CH["LSTF"]
    addrow(r, l)
    # L-LTF ×2 (광대역 기준)
    base = np.fft.ifftshift(_LLTF); reps = max(1, fft // 64)
    lltf = np.tile(base, reps)[:fft].astype(complex)
    for _ in range(2):
        r = np.zeros(fft, complex); l = np.zeros(fft, int)
        if "LLTF" in on:
            r[:] = lltf; l[np.abs(lltf) > 0] = CH["LLTF"]
        addrow(r, l)
    # SIG (제어 헤더)
    r = np.zeros(fft, complex); l = np.zeros(fft, int)
    if "WSIG" in on:
        r[_ci(r, fft, used)] = (1 - 2 * rng.integers(0, 2, len(used))); l[_ci(l, fft, used)] = CH["WSIG"]
    addrow(r, l)
    # DATA
    for _ in range(n_data_sym):
        r = np.zeros(fft, complex); l = np.zeros(fft, int)
        if "WDATA" in on:
            r[_ci(r, fft, used)] = rand_qam(rng, len(used)); l[_ci(l, fft, used)] = CH["WDATA"]
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
    cp_lens = ([160] + [144] * 6) * 2; nsym = 14
    rng = np.random.default_rng(seed)
    grid = np.zeros((nsym, fft), complex); labels = np.zeros((nsym, fft), int)

    def put(l, idx, vals, ch):
        ai = _ci(grid[l], fft, idx); grid[l, ai] = vals; labels[l, ai] = CH[ch]

    # PDSCH (G3): 먼저 데이터로 채움
    if "PDSCH" in on:
        for l in range(3, nsym):
            put(l, used, rand_qam(rng, n_used), "PDSCH")
    # PDCCH (G2/G3): 제어영역 첫 3 심볼
    if "PDCCH" in on:
        for l in range(3):
            put(l, used, rand_qam(rng, n_used) * 0.9, "PDCCH")
    # CRS (G2/G3): l=0,4,7,11, 6 간격
    if "CRS" in on:
        for sl in range(2):
            for li, sh in ((0, n_id % 6), (4, (n_id + 3) % 6)):
                l = sl * 7 + li; idx = np.arange(-n_used // 2 + sh, n_used // 2, 6)
                put(l, idx, qpsk_from_gold((l + 1) * (2 * n_id + 1) * 1024 + n_id, len(idx)) * np.sqrt(2), "CRS")
    # PRS (G2/G3): comb-6 대각, 전대역, l=3,5,6 (슬롯)
    if "PRS" in on:
        for sl in range(2):
            for li in (3, 5, 6):
                l = sl * 7 + li; sh = (n_id + li) % 6; idx = np.arange(-n_used // 2 + sh, n_used // 2, 6)
                put(l, idx, qpsk_from_gold(2**22 + l * 97 + n_id, len(idx)) * np.sqrt(2), "PRS")
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
    used = np.r_[np.arange(-n_used // 2, 0), np.arange(1, n_used // 2 + 1)]
    cp = 288; nsym = 14
    rng = np.random.default_rng(seed)
    grid = np.zeros((nsym, fft), complex); labels = np.zeros((nsym, fft), int)

    def put(l, idx, vals, ch):
        ai = _ci(grid[l], fft, idx); grid[l, ai] = vals; labels[l, ai] = CH[ch]

    # PDSCH (G3)
    if "PDSCH" in on:
        for l in range(2, nsym):
            put(l, used, rand_qam(rng, n_used, 64), "PDSCH")
    # PDCCH/CORESET (G2/G3): 첫 2 심볼
    if "PDCCH" in on:
        for l in range(2):
            put(l, used, rand_qam(rng, n_used) * 0.9, "PDCCH")
    # PDSCH-DMRS (G2/G3): l=2, comb-2
    if "DMRS" in on:
        idx = np.arange(-n_used // 2, n_used // 2, 2)
        put(2, idx, qpsk_from_gold(2048 + n_id, len(idx)), "DMRS")
    # NR-PRS (G2/G3): comb-4 대각 전대역, l=4..9
    if "PRS" in on:
        for li in range(4, 10):
            sh = li % 4; idx = np.arange(-n_used // 2 + sh, n_used // 2, 4)
            put(li, idx, qpsk_from_gold(2**20 + li * 131 + n_id, len(idx)) * 2.0, "PRS")
    # SSB (항상): 중앙 240 부반송파, l=0..3 (PSS/PBCH/SSS/PBCH)
    ssb = np.arange(-120, 120)
    if "PSS" in on: put(0, ssb, qpsk_from_gold(11 + n_id, len(ssb)), "PSS")
    if "PBCH" in on:
        put(1, ssb, qpsk_from_gold(12 + n_id, len(ssb)), "PBCH")
        put(3, ssb, qpsk_from_gold(14 + n_id, len(ssb)), "PBCH")
    if "SSS" in on: put(2, ssb, qpsk_from_gold(13 + n_id, len(ssb)), "SSS")
    return _finish("5G NR Rel-16", "nr", occupancy, carrier_hz, n_used * scs_hz,
                   scs_hz, fft, fs, cp, grid, labels, used, f"n78 {bw_hz/1e6:.0f}MHz, 30kHz, 3.5GHz")


def all_waveforms(occupancy="G3"):
    return {"wifi": wifi_80211ac(occupancy=occupancy),
            "lte": lte_downlink(occupancy=occupancy),
            "nr": nr_downlink(occupancy=occupancy)}


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
