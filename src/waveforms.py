# -*- coding: utf-8 -*-
"""
waveforms.py — (report2) 실제 상용 OFDM 파형 합성: WiFi / LTE / 5G NR
======================================================================

목표: "레이더를 어떻게 쏘는가" 를 **실제 상용 신호 구조 그대로** 만든다.
세 표준을 illuminator(조명 신호)로 써서 드론을 비추고 비교한다.

표준별 핵심(조사+검증: docs/waveform_research.json)
  WiFi  802.11ac VHT : CP-OFDM, SCS 312.5 kHz, BW 20/40/80 MHz, FFT 64/128/256.
                       레이더 기준신호 = L-LTF(전대역·기지·thumbtack 자기상관).
  LTE   Rel-9 FDD    : CP-OFDM, SCS 15 kHz, 20 MHz=FFT2048/30.72 MHz, normal CP.
                       기준 = PRS(측위기준신호)/CRS. 10 ms 프레임·14 sym/subframe.
  5G NR Rel-16 n78   : CP-OFDM, SCS 30 kHz(μ=1), 100 MHz=FFT4096/122.88 MHz.
                       기준 = NR-PRS(전대역)/SSB. 14 sym/slot, 20 slot/frame.

레이더 관점에서 중요한 충실도
  ① 뉴머롤로지(SCS·FFT·CP·표본율) → **대역폭 = 거리분해능 c/2B** 이 정확해야 함
  ② 기준신호(L-LTF/PRS/SSB)를 올바른 시간-주파수 위치에 배치 → 정합필터/모호함수
  ③ 반송파(carrier) → RCS(f) 비교
채널코딩의 비트단위 일치는 레이더에 불필요(데이터는 어차피 미지) → 데이터 RE 는
임의 QAM, 기준신호는 3GPP 골드수열/표준 L-LTF 로 충실히 채운다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import numpy as np

C0 = 299792458.0


@dataclass
class Waveform:
    name: str
    carrier_hz: float
    bw_hz: float            # 점유 대역폭(거리분해능 기준)
    scs_hz: float
    fft: int
    fs_hz: float            # 표본율 = fft × scs
    tx: np.ndarray          # 시간영역 복소 베이스밴드 송신신호
    ref: np.ndarray         # 정합필터용 '기지' 기준(능동: 전체 tx, 그 외: 기준신호)
    ref_name: str
    n_used: int
    notes: str = ""

    @property
    def range_resolution_m(self):
        return C0 / (2 * self.bw_hz)

    @property
    def duration_us(self):
        return len(self.tx) / self.fs_hz * 1e6


# --------------------------------------------------------------------------- #
#  공통 DSP
# --------------------------------------------------------------------------- #
def gold_seq(c_init: int, length: int, Nc: int = 1600) -> np.ndarray:
    """3GPP 길이-31 골드수열 c(n) (TS 38.211 §5.2.1 / 36.211 §7.2). 0/1 배열."""
    x1 = np.zeros(Nc + length + 31, dtype=np.int8)
    x2 = np.zeros(Nc + length + 31, dtype=np.int8)
    x1[0] = 1
    for i in range(31):
        x2[i] = (c_init >> i) & 1
    for n in range(Nc + length):
        x1[n + 31] = (x1[n + 3] ^ x1[n]) & 1
        x2[n + 31] = (x2[n + 3] ^ x2[n + 2] ^ x2[n + 1] ^ x2[n]) & 1
    c = (x1[Nc:Nc + length] ^ x2[Nc:Nc + length]).astype(np.int8)
    return c


def qpsk_from_gold(c_init: int, n: int) -> np.ndarray:
    """골드수열 2n비트 → QPSK n심볼 (3GPP 기준신호 변조)."""
    c = gold_seq(c_init, 2 * n)
    return ((1 - 2 * c[0::2]) + 1j * (1 - 2 * c[1::2])) / np.sqrt(2)


def rand_qam(rng, n, order=4):
    """데이터 RE 용 임의 QAM (PDSCH/DATA 페이로드 대용)."""
    m = int(np.sqrt(order))
    lv = np.arange(-(m - 1), m, 2)
    pts = (rng.choice(lv, n) + 1j * rng.choice(lv, n))
    return pts / np.sqrt((np.abs(np.unique(lv))**2).mean() * 2)


def ofdm_modulate(grid: np.ndarray, fft: int, cp_lens) -> np.ndarray:
    """주파수그리드(nsym, fft, DC=중앙) → 시간영역 CP-OFDM.
    cp_lens: 정수(모든 심볼 동일) 또는 심볼별 길이 리스트."""
    nsym = grid.shape[0]
    if np.isscalar(cp_lens):
        cp_lens = [int(cp_lens)] * nsym
    out = []
    for i in range(nsym):
        t = np.fft.ifft(np.fft.ifftshift(grid[i])) * np.sqrt(fft)  # DC중앙 → 시간
        cp = cp_lens[i]
        out.append(np.concatenate([t[fft - cp:], t]))              # CP 앞에 붙임
    return np.concatenate(out)


def _place(grid_row, fft, idx_centered, vals):
    """DC중앙 그리드 한 심볼에 '중앙기준 부반송파 인덱스'로 값 배치."""
    grid_row[fft // 2 + np.asarray(idx_centered)] = vals


# --------------------------------------------------------------------------- #
#  WiFi 802.11ac (VHT)
# --------------------------------------------------------------------------- #
# 레거시 L-LTF 53-탭 BPSK 시퀀스(부반송파 -26..+26, DC=0) — IEEE 802.11 표준값
_LLTF = np.array([0,0,0,0,0,0,1,1,-1,-1,1,1,-1,1,-1,1,1,1,1,1,1,-1,-1,1,1,-1,1,
                  -1,1,1,1,1,0,1,-1,-1,1,1,-1,1,-1,1,-1,-1,-1,-1,-1,1,1,-1,-1,1,
                  -1,1,-1,1,1,1,1,0,0,0,0,0], dtype=float)  # 길이 64 (인덱스 -32..31)


def wifi_80211ac(bw_hz=80e6, carrier_hz=5.21e9, n_data_sym=12, seed=1) -> Waveform:
    scs = 312.5e3
    fft = int(round(bw_hz / scs))                 # 20→64, 40→128, 80→256
    fs = fft * scs
    cp = fft // 4                                  # 0.8 µs guard interval
    rng = np.random.default_rng(seed)
    # 점유 부반송파(legacy 26/64 비율을 BW 에 맞게 확장): 가장자리·DC 널
    half = int(fft * 26 / 64)
    used = np.r_[np.arange(-half, 0), np.arange(1, half + 1)]
    n_used = len(used)

    # --- L-LTF (기준신호): 64FFT 패턴을 BW 에 맞게 타일/확장 ---
    lltf_row = np.zeros(fft, complex)
    base = np.fft.ifftshift(_LLTF)                 # -32..31 → 0..63 표준 배치
    reps = fft // 64
    lltf_full = np.tile(base, reps) if reps >= 1 else base[:fft]
    lltf_row[:] = lltf_full[:fft]
    # L-STF: 12개 부반송파만(검출용) — 구조만 반영
    stf_row = np.zeros(fft, complex)
    stf_idx = used[::4]
    stf_row[fft // 2 + stf_idx] = np.sqrt(13/6) * (1 + 1j)
    # --- DATA OFDM 심볼들(임의 QAM = 페이로드) ---
    data_rows = np.zeros((n_data_sym, fft), complex)
    for s in range(n_data_sym):
        _place(data_rows[s], fft, used, rand_qam(rng, n_used, 16))

    grid = np.vstack([stf_row, lltf_row, lltf_row, data_rows])     # STF + LTF×2 + DATA
    tx = ofdm_modulate(grid, fft, cp)
    ref = ofdm_modulate(lltf_row[None, :], fft, cp)                # 기준 = L-LTF 한 심볼
    return Waveform("WiFi 802.11ac", carrier_hz, n_used * scs, scs, fft, fs,
                    tx, ref, "L-LTF", n_used,
                    notes=f"VHT {bw_hz/1e6:.0f}MHz, FFT{fft}, GI 0.8µs, 5GHz")


# --------------------------------------------------------------------------- #
#  LTE Rel-9 다운링크 (PRS/CRS/PDSCH)
# --------------------------------------------------------------------------- #
def lte_downlink(bw_hz=20e6, carrier_hz=1.843e9, n_subframes=1, n_id=0, seed=2) -> Waveform:
    scs = 15e3
    fft = 2048 if bw_hz >= 20e6 else 1024
    fs = fft * scs                                 # 30.72 MHz
    n_rb = {20e6: 100, 15e6: 75, 10e6: 50, 5e6: 25}.get(bw_hz, 100)
    n_used = n_rb * 12                              # 1200 부반송파
    used = np.r_[np.arange(-n_used // 2, 0), np.arange(1, n_used // 2 + 1)]
    # normal CP: 슬롯당 7심볼, 첫 심볼 CP=160, 나머지=144 (30.72MHz 기준)
    cp_slot = [160] + [144] * 6
    n_slot = 2 * n_subframes
    cp_lens = cp_slot * n_slot
    nsym = 7 * n_slot
    rng = np.random.default_rng(seed)
    grid = np.zeros((nsym, fft), complex)

    # PDSCH: 전체 RE 를 임의 QAM 으로 먼저 채움
    for l in range(nsym):
        _place(grid[l], fft, used, rand_qam(rng, n_used, 16))

    # CRS (port0): 슬롯내 l=0,4 심볼, 6부반송파 간격, shift=n_id%6 / (n_id+3)%6
    for sl in range(n_slot):
        for li, shift in ((0, n_id % 6), (4, (n_id + 3) % 6)):
            l = sl * 7 + li
            crs_idx = np.arange(-n_used // 2 + shift, n_used // 2, 6)
            seq = qpsk_from_gold((sl * 7 + li + 1) * (2 * n_id + 1) * 2**10 + n_id, len(crs_idx))
            grid[l, fft // 2 + crs_idx] = seq * np.sqrt(2)

    # PRS (Rel-9): comb-6, 심볼마다 대각 주파수 shift (l=3,5,6 / 슬롯) — 전대역
    prs_syms = [3, 5, 6]
    for sl in range(n_slot):
        for li in prs_syms:
            l = sl * 7 + li
            shift = (n_id + li) % 6
            prs_idx = np.arange(-n_used // 2 + shift, n_used // 2, 6)
            seq = qpsk_from_gold((2**22) + (sl * 7 + li) * 97 + n_id, len(prs_idx))
            grid[l, fft // 2 + prs_idx] = seq * np.sqrt(2)

    tx = ofdm_modulate(grid, fft, cp_lens)
    # 기준 = PRS 부반송파만 남긴 그리드의 시간신호(패시브레이더 측위기준)
    prs_grid = np.zeros_like(grid)
    for sl in range(n_slot):
        for li in prs_syms:
            l = sl * 7 + li
            prs_grid[l] = grid[l] * 0
            shift = (n_id + li) % 6
            prs_idx = np.arange(-n_used // 2 + shift, n_used // 2, 6)
            prs_grid[l, fft // 2 + prs_idx] = grid[l, fft // 2 + prs_idx]
    ref = ofdm_modulate(prs_grid, fft, cp_lens)
    return Waveform("LTE Rel-9", carrier_hz, n_used * scs, scs, fft, fs,
                    tx, ref, "PRS", n_used,
                    notes=f"FDD {bw_hz/1e6:.0f}MHz, FFT{fft}, normalCP, 1.8GHz, {n_subframes}subframe")


# --------------------------------------------------------------------------- #
#  5G NR Rel-16 다운링크 (SSB/PRS/PDSCH-DMRS/PDSCH)
# --------------------------------------------------------------------------- #
def nr_downlink(bw_hz=100e6, scs_hz=30e3, carrier_hz=3.5e9, n_slots=2, n_id=1, seed=3) -> Waveform:
    fft = 4096
    fs = fft * scs_hz                              # 122.88 MHz (30kHz)
    n_rb = 273 if bw_hz >= 100e6 else 51           # 100MHz@30k → 273 RB
    n_used = n_rb * 12                             # 3276
    used = np.r_[np.arange(-n_used // 2, 0), np.arange(1, n_used // 2 + 1)]
    cp = 288                                       # normal CP 근사(μ=1)
    nsym = 14 * n_slots                            # slot=14 sym
    rng = np.random.default_rng(seed)
    grid = np.zeros((nsym, fft), complex)

    # PDSCH: 전체 임의 QAM
    for l in range(nsym):
        _place(grid[l], fft, used, rand_qam(rng, n_used, 64))

    # PDSCH-DMRS: 슬롯당 l=2 심볼, comb-2 (DMRS type1)
    for sl in range(n_slots):
        l = sl * 14 + 2
        dmrs_idx = np.arange(-n_used // 2, n_used // 2, 2)
        grid[l, fft // 2 + dmrs_idx] = qpsk_from_gold((sl + 1) * 2**11 + n_id, len(dmrs_idx))

    # NR-PRS: 전대역 comb-4, 심볼 l=4..9 대각 shift (Rel-16 핵심 기준)
    prs_syms = list(range(4, 10)); comb = 4
    for sl in range(n_slots):
        for li in prs_syms:
            l = sl * 14 + li
            shift = (li * 1) % comb
            prs_idx = np.arange(-n_used // 2 + shift, n_used // 2, comb)
            grid[l, fft // 2 + prs_idx] = qpsk_from_gold((2**20) + (sl * 14 + li) * 131 + n_id, len(prs_idx)) * np.sqrt(comb)

    # SSB: 첫 슬롯 l=0..3, 중앙 240 부반송파(20 RB)에 PSS/SSS/PBCH
    ssb_sc = np.arange(-120, 120)
    for li in range(4):
        grid[li, fft // 2 + ssb_sc] = qpsk_from_gold(li * 777 + n_id, len(ssb_sc))

    tx = ofdm_modulate(grid, fft, cp)
    # 기준 = NR-PRS 만
    prs_grid = np.zeros_like(grid)
    for sl in range(n_slots):
        for li in prs_syms:
            l = sl * 14 + li
            shift = (li * 1) % comb
            prs_idx = np.arange(-n_used // 2 + shift, n_used // 2, comb)
            prs_grid[l, fft // 2 + prs_idx] = grid[l, fft // 2 + prs_idx]
    ref = ofdm_modulate(prs_grid, fft, cp)
    return Waveform("5G NR Rel-16", carrier_hz, n_used * scs_hz, scs_hz, fft, fs,
                    tx, ref, "NR-PRS", n_used,
                    notes=f"n78 {bw_hz/1e6:.0f}MHz, 30kHz SCS, FFT{fft}, {n_slots}slot, 3.5GHz")


def all_waveforms():
    return {"wifi": wifi_80211ac(), "lte": lte_downlink(), "nr": nr_downlink()}


def autocorr_resolution(ref, fs):
    """기준신호 |자기상관| 주엽 -3 dB 폭 → 유효 거리분해능[m] (경험 확인용)."""
    r = np.correlate(ref, ref, mode="full")
    r = np.abs(r) / np.abs(r).max()
    pk = len(r) // 2
    half = np.where(r[pk:] < 0.707)[0]
    w = (half[0] if len(half) else 1)
    return w / fs * C0 / 2, r


if __name__ == "__main__":
    for key, wf in all_waveforms().items():
        dr_emp, _ = autocorr_resolution(wf.ref, wf.fs_hz)
        print(f"{wf.name:16s} fc={wf.carrier_hz/1e9:.2f}GHz  B={wf.bw_hz/1e6:6.1f}MHz  "
              f"FFT={wf.fft:5d}  fs={wf.fs_hz/1e6:6.2f}MHz  used={wf.n_used:4d}  "
              f"len={len(wf.tx):6d}({wf.duration_us:5.1f}µs)  "
              f"dR(c/2B)={wf.range_resolution_m:5.2f}m  기준={wf.ref_name}")
