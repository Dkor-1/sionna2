# -*- coding: utf-8 -*-
"""
detection_gpu.py — **GPU 배치 디텍션 커널** (torch): 거리-도플러 + 2D CA-CFAR 를 한 번에 수천 트라이얼
=====================================================================================================
느린 이유였던 것: 드론은 느려서(3 m/s) 도플러가 작다 → **긴 CPI(수십 ms, 수백만 샘플)** 가 있어야
0-도플러 능선 밖으로 나온다. 그걸 numpy 로 트라이얼마다 돌리면 몬테카를로가 몇 시간이다.

→ **torch 로 B개 트라이얼을 GPU 에서 한꺼번에** 처리한다. GPU 메모리를 크게 쓰고(사용자 방침), 빠르다.
  · range_doppler 배치 : (B, M, Lf) FFT
  · 2D CA-CFAR 배치     : 적분영상(summed-area)으로 numpy ca_cfar_2d 와 **수치적으로 동일**하게
  · 피크검출 배치       : 마스크된 argmax → (도플러빈, 거리빈)

passive_process.ca_cfar_2d 와 **동일 출력**임을 validate() 로 검증한다(믿지 말고 재라).
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import numpy as np                                    # noqa: E402


def _torch():
    import torch
    return torch


def rd_batch(surv, ref_frame, M, n_range, device=None):
    """surv (B, M*Lf) 복소텐서 → |RD| (B, M, n_range). ref_frame (Lf,) 복소텐서.
    passive_process.range_doppler 와 동일 규약(프레임 정합필터 + slow-time Hann + FFT)."""
    torch = _torch()
    B, Ns = surv.shape
    Lf = Ns // M
    S = surv.view(B, M, Lf)
    Rf = torch.conj(torch.fft.fft(ref_frame))                       # (Lf,)
    RP = torch.fft.ifft(torch.fft.fft(S, dim=2) * Rf.view(1, 1, Lf), dim=2)[:, :, :n_range]
    win = torch.hann_window(M, periodic=False, dtype=surv.real.dtype,
                            device=surv.device).view(1, M, 1)
    RD = torch.fft.fftshift(torch.fft.fft(RP * win, dim=1), dim=1)   # (B, M, n_range)
    return RD.abs()


def cfar_batch(rd, guard=(2, 2), train=(6, 6), pfa=1e-4):
    """배치 2D CA-CFAR. rd (B, nd, nr) → (det (B,nd,nr) bool, thr (B,nd,nr)).
    passive_process.ca_cfar_2d 를 배치·적분영상으로 그대로 벡터화(가변 학습셀 수 포함)."""
    torch = _torch()
    P = rd ** 2
    B, nd, nr = P.shape
    gd, gr = guard; td, tr = train
    win_d, win_r = gd + td, gr + tr
    dev = P.device

    S = torch.zeros((B, nd + 1, nr + 1), dtype=P.dtype, device=dev)
    S[:, 1:, 1:] = torch.cumsum(torch.cumsum(P, dim=1), dim=2)

    i = torch.arange(nd, device=dev); j = torch.arange(nr, device=dev)
    r0 = torch.clamp(i - win_d, 0, nd)[:, None].expand(nd, nr)
    r1 = torch.clamp(i + win_d + 1, 0, nd)[:, None].expand(nd, nr)
    c0 = torch.clamp(j - win_r, 0, nr)[None, :].expand(nd, nr)
    c1 = torch.clamp(j + win_r + 1, 0, nr)[None, :].expand(nd, nr)
    gr0 = torch.clamp(i - gd, 0, nd)[:, None].expand(nd, nr)
    gr1 = torch.clamp(i + gd + 1, 0, nd)[:, None].expand(nd, nr)
    gc0 = torch.clamp(j - gr, 0, nr)[None, :].expand(nd, nr)
    gc1 = torch.clamp(j + gr + 1, 0, nr)[None, :].expand(nd, nr)

    def box(a, b, c, d):                                            # S[:, a, c] 형태 (B,nd,nr)
        return (S[:, a, c] - S[:, b, c] - S[:, a, d] + S[:, b, d])
    # box_sum(r0,r1,c0,c1) = S[r1,c1]-S[r0,c1]-S[r1,c0]+S[r0,c0]
    tot = S[:, r1, c1] - S[:, r0, c1] - S[:, r1, c0] + S[:, r0, c0]
    gblk = S[:, gr1, gc1] - S[:, gr0, gc1] - S[:, gr1, gc0] + S[:, gr0, gc0]
    ntr = (r1 - r0) * (c1 - c0) - (gr1 - gr0) * (gc1 - gc0)         # (nd,nr) 학습셀 수
    ntr = ntr.to(P.dtype)[None]                                    # (1,nd,nr)
    ok = ntr > 0
    noise = torch.where(ok, (tot - gblk) / torch.where(ok, ntr, torch.ones_like(ntr)),
                        torch.zeros_like(tot))
    ntr_safe = torch.where(ok, ntr, torch.ones_like(ntr))
    alpha = ntr_safe * (pfa ** (-1.0 / ntr_safe) - 1.0)
    thr = alpha * noise
    det = ok & (P > thr)
    return det, torch.sqrt(torch.clamp(thr, min=0))


def peak_batch(rd, det, guard_zd=1):
    """배치 피크: 0-도플러 능선 가드 후 마스크 argmax → (di (B,), ri (B,), val (B,), found (B,)).
    빈 검출이면 found=False."""
    torch = _torch()
    B, nd, nr = rd.shape
    zd = nd // 2                                                   # fftshift 후 중앙 = 0 도플러
    d = det.clone()
    lo, hi = max(0, zd - guard_zd), min(nd, zd + guard_zd + 1)
    d[:, lo:hi, :] = False
    masked = torch.where(d, rd, torch.zeros_like(rd))
    flat = masked.view(B, -1)
    val, idx = flat.max(dim=1)
    di = (idx // nr); ri = (idx % nr)
    found = val > 0
    return di, ri, val, found


# --------------------------------------------------------------------------- #
def validate(verbose=True):
    """GPU CFAR/RD 가 numpy 기준과 일치하는지 검증."""
    import torch
    from passive_process import ca_cfar_2d, range_doppler
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    rng = np.random.default_rng(0)
    # 임의 RD 맵으로 CFAR 대조
    nd, nr = 64, 24
    rd_np = np.abs(rng.standard_normal((nd, nr)) + 1j * rng.standard_normal((nd, nr)))
    rd_np[40, 10] += 8.0                                           # 표적 하나
    det_np, thr_np, _ = ca_cfar_2d(rd_np, pfa=1e-4)
    rd_t = torch.tensor(rd_np, dtype=torch.float64, device=dev)[None]
    det_t, thr_t = cfar_batch(rd_t, pfa=1e-4)
    det_match = bool((torch.tensor(det_np, device=dev)[None] == det_t).all().item())
    thr_err = float((thr_t[0].cpu().numpy() - thr_np).__abs__().max())
    # RD 대조
    Lf, M = 512, 16
    ref = (rng.standard_normal(Lf) + 1j * rng.standard_normal(Lf))
    surv = (rng.standard_normal(M * Lf) + 1j * rng.standard_normal(M * Lf))
    _, _, rd_ref = range_doppler(surv, np.tile(ref, M), 1e6, M, n_range=nr)
    surv_t = torch.tensor(surv, dtype=torch.complex128, device=dev)[None]
    ref_t = torch.tensor(ref, dtype=torch.complex128, device=dev)
    rd_g = rd_batch(surv_t, ref_t, M, nr)[0].cpu().numpy()
    rd_err = float(np.abs(rd_g - rd_ref).max() / (rd_ref.max() + 1e-30))
    if verbose:
        print(f"[validate] device={dev}")
        print(f"  CFAR det 일치: {det_match}   thr 최대오차: {thr_err:.2e}")
        print(f"  RD 상대오차: {rd_err:.2e}")
        print("  ✅ GPU 커널이 numpy 기준과 일치" if (det_match and rd_err < 1e-9)
              else "  ⚠ 불일치 — 점검 필요")
    return det_match and rd_err < 1e-9


if __name__ == "__main__":
    from gpu import pick
    pick(verbose=True)
    validate()
