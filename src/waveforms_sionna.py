# -*- coding: utf-8 -*-
"""
waveforms_sionna.py — **Sionna PHY 로 파형을 만들고, 자작 waveforms.py 를 교차검증한다**
==========================================================================================
지금까지 WiFi/LTE/5G 자원격자는 `waveforms.py` 에서 **손으로** 구성했다(3GPP/IEEE 스펙을
읽고 CRS/SSB/PRS/VHT-LTF 위치를 직접 배치). 이제 Sionna PHY 의 OFDM 기계를 쓴다:

    sionna.phy.ofdm.ResourceGrid   — 부반송파 배치(가드·DC널·CP·파일럿 심볼)
    sionna.phy.ofdm.OFDMModulator  — IFFT + CP 삽입 (시간영역 파형)
    sionna.phy.nr.CarrierConfig    — **진짜 3GPP 5G NR 뉴머롤로지**(μ, SCS, 슬롯, CP 길이)

■ 무엇을 얻나
  1. **뉴머롤로지를 우리가 안 짠다** — CarrierConfig 가 3GPP 표를 안다.
  2. **OFDM 변조를 우리가 안 짠다** — 가드·DC널·CP 를 Sionna 가 처리한다.
  3. **교차검증** — 자작 파형과 Sionna 파형의 스펙트럼·자기상관·거리분해능을 대조한다.
     일치하면 자작 구현이 옳다는 강한 증거고, 어긋나면 **버그를 찾은 것**이다.

■ Sionna 에 없는 것 (정직하게)
  · **WiFi(802.11)·LTE 는 Sionna PHY 에 없다.** 5G NR 만 있다.
    → WiFi/LTE 는 ResourceGrid 로 **뉴머롤로지만** 맞추고, 파일럿(VHT-LTF/CRS) 배치는
      여전히 우리가 스펙대로 넣는다. 그건 피할 수 없다.
  · SSB(동기신호블록) 생성기도 Sionna 에 없다(PUSCH/PDSCH 위주).
  → 그래서 waveforms.py 를 **버리지 않는다**. Sionna 는 **검증자**이자 **OFDM 엔진**이다.
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from gpu import pick as _pick_gpu     # noqa: E402  (torch import 전에)
_pick_gpu(verbose=False)

import numpy as np                    # noqa: E402
import torch                          # noqa: E402
from sionna.phy.ofdm import ResourceGrid, OFDMModulator   # noqa: E402
from sionna.phy.nr import CarrierConfig                    # noqa: E402

C0 = 299792458.0


# --------------------------------------------------------------------------- #
#  3GPP 5G NR — 뉴머롤로지는 **Sionna 에게 물어본다**
# --------------------------------------------------------------------------- #
def nr_numerology(scs_khz: int = 30, n_size_grid: int = 273):
    """CarrierConfig 로 진짜 3GPP 뉴머롤로지를 얻는다.
      scs 15/30/60/120 kHz → μ = 0/1/2/3.  n_size_grid = 자원블록 수(RB, 12 부반송파/RB)."""
    mu = {15: 0, 30: 1, 60: 2, 120: 3}[int(scs_khz)]
    cc = CarrierConfig(subcarrier_spacing=int(scs_khz), n_size_grid=int(n_size_grid))
    return dict(
        mu=mu, scs_hz=float(scs_khz) * 1e3,
        n_size_grid=int(n_size_grid),
        num_subcarriers=int(n_size_grid) * 12,
        num_symbols_per_slot=int(cc.num_symbols_per_slot),
        num_slots_per_frame=int(cc.num_slots_per_frame),
        slot_duration_s=float(cc.frame_duration) / float(cc.num_slots_per_frame),
        cyclic_prefix=str(cc.cyclic_prefix),
        cp_length_samples=int(np.asarray(cc.cyclic_prefix_length).reshape(-1)[0])
        if np.asarray(cc.cyclic_prefix_length).size else 0,
    )


# --------------------------------------------------------------------------- #
#  Sionna ResourceGrid 로 OFDM 파형 만들기
# --------------------------------------------------------------------------- #
def ofdm_from_grid(grid: np.ndarray, fft_size: int, cp_len):
    """부반송파 격자 [n_sym, fft_size] → 시간영역 파형. **Sionna OFDMModulator** 가 IFFT+CP 담당.

    cp_len : 정수(전 심볼 동일) 또는 **심볼별 배열**.
      ⚠ LTE/NR 은 슬롯 첫 심볼의 CP 가 더 길다(3GPP). 배열을 그대로 넘겨야 한다 —
        첫 값만 쓰면 심볼 경계가 어긋나 파형이 완전히 달라진다(교차검증에서 확인)."""
    g = np.asarray(grid, np.complex64)
    if g.shape[1] != fft_size:
        raise ValueError(f"격자 폭 {g.shape[1]} ≠ fft_size {fft_size}")
    cp = np.atleast_1d(np.asarray(cp_len))
    cp_arg = int(cp[0]) if cp.size == 1 else torch.from_numpy(cp.astype(np.int64))
    mod = OFDMModulator(cyclic_prefix_length=cp_arg)
    x = torch.from_numpy(g)[None, None, None]          # (1,1,1,n_sym,fft)
    y = mod(x)
    return y.detach().cpu().numpy().reshape(-1)


def sionna_resource_grid(n_sym: int, fft_size: int, scs_hz: float, cp_len: int,
                         guard=(0, 0), dc_null=False, pilot_sym=None):
    """우리 파형의 뉴머롤로지로 Sionna ResourceGrid 를 만든다 (구조 검증·문서화용)."""
    return ResourceGrid(num_ofdm_symbols=int(n_sym), fft_size=int(fft_size),
                        subcarrier_spacing=float(scs_hz),
                        cyclic_prefix_length=int(cp_len),
                        num_guard_carriers=tuple(int(x) for x in guard),
                        dc_null=bool(dc_null),
                        pilot_pattern=("kronecker" if pilot_sym else None),
                        pilot_ofdm_symbol_indices=(list(pilot_sym) if pilot_sym else None))


# --------------------------------------------------------------------------- #
#  교차검증 — 자작 waveforms.py ↔ Sionna OFDMModulator
# --------------------------------------------------------------------------- #
def crosscheck(verbose=True):
    """같은 자원격자를 (a) 자작 ofdm_modulate 와 (b) Sionna OFDMModulator 로 변조해 대조한다.
    두 파형이 같으면 자작 OFDM 구현이 옳다. 다르면 **어느 쪽이 틀렸는지** 찾아야 한다."""
    from waveforms import all_waveforms, ofdm_modulate, autocorr_resolution

    rows = []
    for key, wf in all_waveforms("G3").items():
        # 자작 파형이 실제로 쓴 격자·FFT·CP 를 그대로 가져와 Sionna 로 다시 변조
        grid = np.asarray(wf.grid)                       # [n_sym, fft] 중앙기준
        fft = int(wf.fft)
        cps = np.atleast_1d(np.asarray(wf.cp_lens))
        same_cp = bool(np.all(cps == cps[0]))

        x_ours = np.asarray(wf.tx, complex)
        try:
            x_sio = ofdm_from_grid(grid, fft, cps)      # **심볼별 CP 배열을 그대로** 넘긴다
        except Exception as e:
            rows.append(dict(name=wf.name, ok=False, note=f"Sionna 변조 실패: {e}"))
            continue

        n = min(len(x_ours), len(x_sio))
        if n == 0:
            rows.append(dict(name=wf.name, ok=False, note="길이 0")); continue
        a, b = x_ours[:n], x_sio[:n]
        # 전력 정규화 후 상관 (스케일 규약이 다를 수 있다)
        a = a / (np.sqrt(np.mean(np.abs(a) ** 2)) + 1e-30)
        b = b / (np.sqrt(np.mean(np.abs(b) ** 2)) + 1e-30)
        corr = float(abs(np.vdot(a, b)) / n)
        nmse = float(np.mean(np.abs(a - b) ** 2))

        rows.append(dict(name=wf.name, n=n, same_cp=same_cp, corr=corr, nmse_db=10*np.log10(nmse+1e-30),
                         ok=(corr > 0.99), note=("" if same_cp else "심볼별 CP (LTE/NR: 슬롯 첫 심볼이 김)")))

    if verbose:
        print("=" * 92)
        print("교차검증 — 자작 ofdm_modulate  vs  Sionna OFDMModulator (같은 자원격자)")
        print("=" * 92)
        print(f"{'파형':22s} {'샘플':>8} {'상관':>8} {'NMSE':>10}  판정   비고")
        for r in rows:
            if "corr" not in r:
                print(f"{r['name']:22s} {'—':>8} {'—':>8} {'—':>10}  ❌     {r['note']}")
                continue
            print(f"{r['name']:22s} {r['n']:8,d} {r['corr']:8.4f} {r['nmse_db']:9.1f}dB"
                  f"  {'✅' if r['ok'] else '❌'}     {r['note']}")
    return rows


def nr_table(verbose=True):
    """Sionna 가 아는 3GPP NR 뉴머롤로지 — 우리가 표를 안 짠다."""
    rows = []
    for scs, rb, bw in ((15, 106, "20 MHz"), (30, 273, "100 MHz"), (60, 135, "100 MHz")):
        try:
            rows.append(dict(bw=bw, **nr_numerology(scs, rb)))
        except Exception as e:
            rows.append(dict(bw=bw, scs_hz=scs * 1e3, error=str(e)[:40]))
    if verbose:
        print("\n" + "=" * 92)
        print("3GPP 5G NR 뉴머롤로지 — **Sionna CarrierConfig 가 알려준 값** (우리가 안 짬)")
        print("=" * 92)
        print(f"{'대역':10s} {'SCS':>8} {'μ':>3} {'RB':>5} {'부반송파':>9} {'심볼/슬롯':>9} "
              f"{'슬롯/프레임':>11} {'슬롯길이':>10} {'CP':>8}")
        for r in rows:
            if "error" in r:
                print(f"{r['bw']:10s} {r['scs_hz']/1e3:7.0f}k  ❌ {r['error']}"); continue
            print(f"{r['bw']:10s} {r['scs_hz']/1e3:7.0f}k {r['mu']:3d} {r['n_size_grid']:5d} "
                  f"{r['num_subcarriers']:9,d} {r['num_symbols_per_slot']:9d} "
                  f"{r['num_slots_per_frame']:11d} {r['slot_duration_s']*1e6:9.1f}µs {r['cyclic_prefix']:>8s}")
    return rows


if __name__ == "__main__":
    nr_table()
    print()
    crosscheck()
