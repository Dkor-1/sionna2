# -*- coding: utf-8 -*-
"""
verify_cfar.py — [E1] **CFAR 오경보율(Pfa) 교정 검증**
=========================================================
질문 하나: **ca_cfar_2d(pfa=1e-4) 를 주면 진짜로 1e-4 가 나오는가?**

안 나오면 report4/report5 의 **모든 Pd 숫자가 무의미하다** (문턱이 명목과 다른 지점에
찍혀 있다는 뜻이므로, "같은 Pfa 에서 어느 조명원이 낫나"라는 비교 자체가 성립하지 않는다).

측정 방법 — **표적 없이 잡음만** 넣은 거리-도플러 맵을 대량으로 만들고 CFAR 히트 비율을 센다:
  (A) white  : 이상적 iid 복소가우시안 RD 맵 (파형·처리체인 없음) → **구현 자체**의 교정 검증
  (B) noise  : 실제 파형 기준신호로 정합필터+도플러FFT 를 통과한 잡음 → **처리체인**의 효과
  (C) dpi_eca: 잡음 + 직접파(DPI) + 정적클러터 → **ECA** → RD (report4/5 의 실제 운용 형상)
  (D) white_mf: (B) 와 같되 **기준신호를 스펙트럼 백색화**한 정합필터 → 원인 규명용 대조군

이론: CA-CFAR 문턱계수 alpha = N*(Pfa^(-1/N) - 1),  N = 훈련셀 수.
  이 식은 **셀 전력이 iid 지수분포**(복소가우시안의 |.|^2)일 때만 명목 Pfa 를 준다.
  RD 맵에서 이 가정이 깨지는 경로:
    · 정합필터 = 기준신호 스펙트럼 |Ref(f)|^2 로 잡음을 **색칠**한다 → 거리셀들이 상관됨
      (기준이 파일럿-빗살이면 거리축 상관이 아주 강하다)
    · slow-time Hann 창 → 도플러셀들이 상관됨
    · 가장자리 셀은 훈련창이 잘려 N 이 작다 (구현은 셀별 가변 N 을 쓴다 → 그건 맞음)
    · ECA 는 0-도플러 행을 **파내고**(notch) DPI 데이터성분 잔류를 그 행에 남긴다

산출:
  · 명목 Pfa (1e-2..1e-6) × guard/train × 0-도플러 마스킹(on/off) → **경험적 Pfa**
  · **교정 룩업표**: 원하는 경험적 Pfa 를 얻으려면 명목 Pfa 를 얼마로 줘야 하나
  · ROC: 알려진 표적 진폭에서 Pd vs **경험적** Pfa

전부 outputs/verify_cfar.json 에 남긴다. **숫자를 손으로 적지 않는다.**

실행:  python benchmark/verify_cfar.py            (기본: 논문용 대량 MC, GPU)
       python benchmark/verify_cfar.py --quick    (빠른 점검)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.abspath(os.path.join(_HERE, "..", "src"))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (_SRC, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from gpu import pick                                              # noqa: E402  ← torch 보다 먼저!
pick()
import torch                                                      # noqa: E402

from waveforms import wifi_80211ac, lte_downlink, nr_downlink, PILOT_RATE_HZ   # noqa: E402
from passive_process import ca_cfar_2d, range_doppler, ECACanceller, make_cpi  # noqa: E402
from geometry import TX, RX, CENTER, CH_CLUTTER_RATIO, chamber_window, SPEED   # noqa: E402
from link_budget import LinkBudget                                # noqa: E402
from bistatic_scene import bistatic_params, C0                    # noqa: E402
from run_min_cell import frame_len, wilson_ci, EIRP_DBM           # noqa: E402

DEV = torch.device("cuda" if torch.cuda.is_available() else "cpu")
CDTYPE = torch.complex128          # DPI 를 60 dB 지우려면 float32 로는 부족하다 → 배정밀도

M_CPI = 48                         # report4/5 와 동일한 CPI 프레임 수
N_RANGE_WIDE = 256                 # 통계용 '넓은' 맵 (가장자리 비중을 낮춰 내부 통계를 본다)

PFA_NOM = [1e-2, 3e-3, 1e-3, 3e-4, 1e-4, 3e-5, 1e-5, 3e-6, 1e-6]
GT = [((2, 2), (6, 6)),            # ← report4/5 기본값
      ((1, 1), (4, 4)),
      ((3, 3), (8, 8)),
      ((2, 2), (10, 10))]
GT_DEFAULT = 0
# 0-도플러 마스킹 폭: 0=없음, 1=zd 행만(**report4/5 의 현재 운용값**), 3=zd±1, 5=zd±2.
#   slow-time Hann 창의 DFT 는 ±1 빈으로 -5.75 dB 만 감쇠해 샌다 → DPI 잔류는 zd 뿐 아니라
#   **zd±1 행에도 실린다**. width=1 로는 그 두 행이 안 지워진다.
ZD_MASK_W = (0, 1, 3, 5)
ZD_MASK_OP = 1                     # 현재 코드베이스가 실제로 쓰는 값(det[zd,:]=False)


def _gpu_budget_bytes(default=2e9):
    """지금 이 카드의 실제 예산 [bytes]. gpu.py 를 못 쓰면 보수적 기본값."""
    try:
        from gpu import budget_mb, refresh_budget
        refresh_budget()                           # 타 사용자가 방금 잡았을 수도 있다
        return float(budget_mb()) * 1024 * 1024
    except Exception:
        return float(default)


def batch_for(chain, budget_bytes=None):
    """CPI 길이에 맞춰 GPU 메모리를 채우는 배치 크기 (complex128, FFT 임시버퍼 ~5배 여유).

    ⚠ 2026-07-29: 예전에는 `budget_bytes=6e9` **하드코딩**이라 실제 여유와 무관하게 6 GB 를
    가정했다. 공용 카드에서 여유가 3.9 GB 일 때 그대로 6 GB 짜리 배치를 잡아 **19분을 계산하고
    막판에 OOM 으로 전부 날렸다**(`exp_roc` → `chain.rd`, 1.10 GiB 할당 실패).
    이제 `gpu.budget_mb()` 로 **지금 이 카드의 실제 예산**을 묻는다."""
    if budget_bytes is None:
        budget_bytes = _gpu_budget_bytes()
    per = chain.N * 16 * 5
    return int(max(1, min(64, budget_bytes // per)))


def _oom_retry(fn, batch, min_batch=1, tries=10):
    """`fn(B)` 를 부르되 CUDA OOM 이면 **배치를 반으로 줄여** 다시 부른다.
    반환 (결과, 실제로 쓴 배치). 호출부는 반환된 배치만큼만 `done` 을 늘려야 한다.

    ⚠ 2026-07-29: verify_cfar 가 19분을 계산하고 막판 `exp_roc`→`chain.rd` 에서 1.10 GiB
      할당 실패로 **전부 날렸다**. 근본원인은 `batch_for` 의 6e9 하드코딩 예산이었고 그건
      따로 고쳤지만, 공용 카드에서는 **실행 도중에도** 여유가 줄어든다. 그래서 재시도가 필요하다.
    ⚠ 재현성: 배치가 줄면 난수 소비 순서가 바뀌어 비트단위로는 달라진다(통계는 유효).
      배치가 안 줄면 종전과 완전히 동일하다."""
    import torch
    B = int(batch)
    for k in range(tries):
        try:
            return fn(B), B
        except torch.OutOfMemoryError:
            torch.cuda.empty_cache()
            if B <= min_batch:
                raise
            B = max(min_batch, B // 2)
            print(f"[cfar] OOM → 배치 {B} 로 줄여 재시도 ({k+1}/{tries})", flush=True)
    raise RuntimeError("_oom_retry: 재시도 소진")


def gt_key(g, t):
    return f"g{g[0]}x{g[1]}_t{t[0]}x{t[1]}"


# =========================================================================== #
#  0. alpha 식 감사 — 코드의 alpha 가 N*(Pfa^(-1/N)-1) 인가, 그리고 전력단위인가
# =========================================================================== #
def audit_alpha():
    """ca_cfar_2d 를 **상수 맵**에 물려 문턱을 역산 → alpha_code 를 이론식과 대조.
    rd=const=c 이면 훈련셀 평균전력 noise=c^2, thr=sqrt(alpha)*c  → alpha_code=(thr/c)^2."""
    out = {}
    for (g, t) in GT:
        nd, nr = 48, 24
        for c in (1.0, 7.3):                                   # 스케일 불변성(전력단위) 확인
            rd = np.full((nd, nr), c)
            det, thr, noise = ca_cfar_2d(rd, guard=g, train=t, pfa=1e-4)
            a_code = (thr / c) ** 2
            # 이론 N: 내부 셀 = (2(g+t)+1)^2 - (2g+1)^2
            wd, wr = g[0] + t[0], g[1] + t[1]
            N_int = (2 * wd + 1) * (2 * wr + 1) - (2 * g[0] + 1) * (2 * g[1] + 1)
            a_th = N_int * (1e-4 ** (-1.0 / N_int) - 1.0)
            i, j = nd // 2, nr // 2                            # 내부 셀
            out[gt_key(g, t)] = dict(
                N_interior=int(N_int),
                alpha_code_interior=float(a_code[i, j]),
                alpha_theory_interior=float(a_th),
                rel_err=float(abs(a_code[i, j] - a_th) / a_th),
                noise_est_over_power=float(noise[i, j] / c ** 2),   # =1 이면 전력단위 정확
                any_det_on_flat_map=bool(det.any()),               # 평평한 맵 → 히트 0 이어야
            )
    return out


# =========================================================================== #
#  1. 빠른 CFAR 통계 (ca_cfar_2d 와 동일 출력 — 배치·다중 Pfa 재사용용)
# =========================================================================== #
def cfar_stats_t(rd, guard, train):
    """torch 판 cfar_stats — (B,nd,nr) float64 텐서 → (P, noise, ntr).
    numpy cfar_stats 와 동일 로직(적분영상). MC 가 커서 계수까지 GPU 에서 돈다."""
    P = rd ** 2
    gd, gr = guard; td, tr = train
    B, nd, nr = P.shape
    win_d, win_r = gd + td, gr + tr
    S = torch.zeros((B, nd + 1, nr + 1), dtype=torch.float64, device=P.device)
    S[:, 1:, 1:] = torch.cumsum(torch.cumsum(P, dim=1), dim=2)

    def box(r0, r1, c0, c1):
        return S[:, r1, c1] - S[:, r0, c1] - S[:, r1, c0] + S[:, r0, c0]

    i = torch.arange(nd, device=P.device); j = torch.arange(nr, device=P.device)
    r0 = (i - win_d).clamp(0, nd)[:, None]; r1 = (i + win_d + 1).clamp(0, nd)[:, None]
    c0 = (j - win_r).clamp(0, nr)[None, :]; c1 = (j + win_r + 1).clamp(0, nr)[None, :]
    gr0 = (i - gd).clamp(0, nd)[:, None]; gr1 = (i + gd + 1).clamp(0, nd)[:, None]
    gc0 = (j - gr).clamp(0, nr)[None, :]; gc1 = (j + gr + 1).clamp(0, nr)[None, :]
    tot = box(r0, r1, c0, c1); gblk = box(gr0, gr1, gc0, gc1)
    ntr = ((r1 - r0) * (c1 - c0) - (gr1 - gr0) * (gc1 - gc0)).to(torch.float64)
    ok = ntr > 0
    noise = torch.where(ok, (tot - gblk) / torch.where(ok, ntr, torch.ones_like(ntr)),
                        torch.zeros_like(tot))
    return P, noise, ntr


def critical_pfa(P, noise, ntr):
    """셀별 **임계 명목 Pfa**: 이 값보다 큰 명목 Pfa 를 주면 이 셀이 검출된다.
        det ⟺ P > N(pfa^(-1/N)-1)·noise ⟺ pfa > (1 + r/N)^(-N),   r = P/noise
    → pc 를 한 번만 계산하면 **모든 명목 Pfa 의 히트 수**를 비교 한 번으로 얻는다
      (문턱을 Pfa 마다 다시 만드는 것보다 훨씬 싸다 — 수억 셀 MC 에 필수)."""
    N = torch.where(ntr > 0, ntr, torch.ones_like(ntr))
    r = P / torch.where(noise > 0, noise, torch.ones_like(noise))
    return torch.pow(1.0 + r / N, -N)


def cfar_stats(rd, guard, train):
    """rd: (B, nd, nr) → (P, noise, ntr).  ca_cfar_2d 의 적분영상 로직 그대로,
    다만 배치·pfa 재사용을 위해 문턱 적용 전 단계까지만 계산한다(동일성은 아래에서 검증)."""
    P = rd ** 2
    gd, gr = guard; td, tr = train
    B, nd, nr = P.shape
    win_d, win_r = gd + td, gr + tr
    S = np.zeros((B, nd + 1, nr + 1))
    S[:, 1:, 1:] = np.cumsum(np.cumsum(P, axis=1), axis=2)

    def box(r0, r1, c0, c1):
        return (S[:, r1, c1] - S[:, r0, c1] - S[:, r1, c0] + S[:, r0, c0])

    i = np.arange(nd); j = np.arange(nr)
    r0 = np.clip(i - win_d, 0, nd)[:, None]; r1 = np.clip(i + win_d + 1, 0, nd)[:, None]
    c0 = np.clip(j - win_r, 0, nr)[None, :]; c1 = np.clip(j + win_r + 1, 0, nr)[None, :]
    gr0 = np.clip(i - gd, 0, nd)[:, None]; gr1 = np.clip(i + gd + 1, 0, nd)[:, None]
    gc0 = np.clip(j - gr, 0, nr)[None, :]; gc1 = np.clip(j + gr + 1, 0, nr)[None, :]
    tot = box(r0, r1, c0, c1); gblk = box(gr0, gr1, gc0, gc1)
    ntr = (r1 - r0) * (c1 - c0) - (gr1 - gr0) * (gc1 - gc0)
    ok = ntr > 0
    noise = np.where(ok, (tot - gblk) / np.where(ok, ntr, 1), 0.0)
    return P, noise, np.where(ok, ntr, 0)


def alpha_of(ntr, pfa):
    n = np.where(ntr > 0, ntr, 1)
    return n * (pfa ** (-1.0 / n) - 1.0)


def verify_fast_equals_reference(rd2d, guard, train, pfa):
    """MC 에 쓰는 빠른 경로(cfar_stats / GPU critical_pfa)가 **실제로 검증 대상인**
    passive_process.ca_cfar_2d 와 같은 검출을 내는지 확인. 두 경로 모두 대조한다."""
    det_ref, _, _ = ca_cfar_2d(rd2d, guard=guard, train=train, pfa=pfa)
    P, noise, ntr = cfar_stats(rd2d[None], guard, train)
    det_np = (ntr > 0) & (P[0] > alpha_of(ntr, pfa) * noise[0])
    t = torch.as_tensor(rd2d[None], dtype=torch.float64, device=DEV)
    Pt, nt, ntrt = cfar_stats_t(t, guard, train)
    pc = critical_pfa(Pt, nt, ntrt)
    det_gpu = ((ntrt > 0)[None] & (pc < pfa))[0].cpu().numpy()
    return bool(np.array_equal(det_ref, det_np) and np.array_equal(det_ref, det_gpu))


# =========================================================================== #
#  2. 누산기 — 맵 배치를 받아 (pfa × guard/train × mask) 별 히트를 센다
# =========================================================================== #
class Counter:
    """(gt × pfa × 0-도플러마스킹) 별 히트 누산. 추가로
       · interior(훈련창이 안 잘린 셀) vs edge(잘린 셀) 분리 — 가장자리 처리 검증
       · 도플러 행별 FA 프로파일 — ECA 노치/ DPI 잔류가 어느 행에 FA 를 몰아주나"""

    def __init__(self, zd_index, row_pfa=1e-4, row_gt=GT[GT_DEFAULT], widths=ZD_MASK_W):
        self.zd = zd_index
        self.widths = tuple(widths)
        self.hits = {}          # (gt, pfa, mask) -> 히트 셀 수
        self.fa_maps = {}       # (gt, pfa, mask) -> 히트가 하나라도 있는 맵 수
        self.cells = {}         # (gt, mask) -> 검사한 셀 수
        self.hits_in = {}; self.cells_in = {}     # interior 전용
        self.hits_ed = {}; self.cells_ed = {}     # edge 전용
        self.row_hits = None; self.row_cells = 0
        self.row_pfa = row_pfa; self.row_gt = gt_key(*row_gt)
        self.n_maps = 0
        self.psum = 0.0; self.pcnt = 0
        self.zd_pow = 0.0; self.zd_cnt = 0
        self.off_pow = 0.0; self.off_cnt = 0

    def add(self, rd, pfa_list, gts):
        """rd: (B,nd,nr) float64 **torch 텐서**(GPU). 셀별 임계Pfa(pc)로 전 Pfa 를 한 번에 센다."""
        B, nd, nr = rd.shape
        self.n_maps += B
        P0 = rd ** 2
        self.psum += float(P0.sum()); self.pcnt += P0.numel()
        self.zd_pow += float(P0[:, self.zd, :].sum()); self.zd_cnt += B * nr
        off = torch.ones(nd, dtype=torch.bool, device=rd.device); off[self.zd] = False
        self.off_pow += float(P0[:, off, :].sum()); self.off_cnt += B * (nd - 1) * nr
        if self.row_hits is None:
            self.row_hits = np.zeros(nd, np.int64)
        for (g, t) in gts:
            k = gt_key(g, t)
            P, noise, ntr = cfar_stats_t(rd, g, t)
            pc = critical_pfa(P, noise, ntr)                     # (B,nd,nr) 임계 명목 Pfa
            valid = ntr > 0
            interior = valid & (ntr == ntr.max())                # 훈련창이 잘리지 않은 셀
            edge = valid & ~interior
            BIG = torch.tensor(2.0, dtype=torch.float64, device=rd.device)  # 검사 제외 셀
            for mask in self.widths:
                vm = valid.clone(); im = interior.clone(); em = edge.clone()
                if mask > 0:                      # 0-도플러 ±(mask//2) 행 마스킹
                    h = mask // 2
                    lo, hi = max(0, self.zd - h), min(nd, self.zd + h + 1)
                    vm[lo:hi, :] = False; im[lo:hi, :] = False; em[lo:hi, :] = False
                self.cells[(k, mask)] = self.cells.get((k, mask), 0) + B * int(vm.sum())
                self.cells_in[(k, mask)] = self.cells_in.get((k, mask), 0) + B * int(im.sum())
                self.cells_ed[(k, mask)] = self.cells_ed.get((k, mask), 0) + B * int(em.sum())
                pc_v = torch.where(vm[None], pc, BIG)            # 제외 셀은 절대 히트 안 나게
                pc_i = torch.where(im[None], pc, BIG)
                pc_e = torch.where(em[None], pc, BIG)
                pc_min = pc_v.amin(dim=(1, 2))                   # 맵별 최소 pc → 맵당 FA
                for pfa in pfa_list:
                    key = (k, pfa, mask)
                    self.hits[key] = self.hits.get(key, 0) + int((pc_v < pfa).sum())
                    self.hits_in[key] = self.hits_in.get(key, 0) + int((pc_i < pfa).sum())
                    self.hits_ed[key] = self.hits_ed.get(key, 0) + int((pc_e < pfa).sum())
                    self.fa_maps[key] = self.fa_maps.get(key, 0) + int((pc_min < pfa).sum())
                    if mask == 0 and k == self.row_gt and pfa == self.row_pfa:
                        self.row_hits += (pc_v < pfa).sum(dim=(0, 2)).cpu().numpy()
                        self.row_cells += B * nr

    def result(self):
        rows = []
        for (k, pfa, mask), h in sorted(self.hits.items()):
            n = self.cells[(k, mask)]
            lo, hi = wilson_ci(h, n)
            ni = self.cells_in[(k, mask)]; ne = self.cells_ed[(k, mask)]
            rows.append(dict(gt=k, pfa_nom=pfa,
                             zd_mask_width=mask,      # 0=마스킹 없음, 1=zd 행만, 3=zd±1, 5=zd±2
                             zd_mask=bool(mask),      # (호환) 기존 운용값 = width 1
                             hits=int(h), cells=int(n),
                             pfa_emp=h / n if n else float("nan"),
                             pfa_lo=lo, pfa_hi=hi,
                             ratio=(h / n) / pfa if n else float("nan"),
                             pfa_interior=self.hits_in[(k, pfa, mask)] / ni if ni else float("nan"),
                             cells_interior=int(ni),
                             pfa_edge=self.hits_ed[(k, pfa, mask)] / ne if ne else float("nan"),
                             cells_edge=int(ne),
                             p_fa_per_map=self.fa_maps[(k, pfa, mask)] / self.n_maps))
        return dict(n_maps=int(self.n_maps),
                    mean_cell_power=self.psum / max(self.pcnt, 1),
                    zd_row_power=self.zd_pow / max(self.zd_cnt, 1),
                    offzd_power=self.off_pow / max(self.off_cnt, 1),
                    row_profile=dict(pfa_nom=self.row_pfa, gt=self.row_gt,
                                     zd_index=int(self.zd),
                                     # 행별 셀 수 = n_maps * n_range = row_cells (행마다 동일)
                                     pfa_by_doppler_row=(self.row_hits / max(self.row_cells, 1)).tolist()
                                     if self.row_hits is not None else []),
                    rows=rows)


# =========================================================================== #
#  3. GPU 처리체인 (numpy passive_process 와 수치 동일 — 아래에서 검증)
# =========================================================================== #
class Chain:
    """noise → (+DPI/클러터) → (ECA) → 정합필터 → 도플러FFT → |RD|.
    passive_process.range_doppler / ECACanceller 를 torch 로 옮긴 것(동일성 검증 포함)."""

    def __init__(self, wf, n_taps, whiten=False, window="hann"):
        self.wf = wf
        self.fs = wf.fs_hz
        self.M = M_CPI
        txrms = float(np.sqrt(np.mean(np.abs(wf.tx) ** 2)))
        ref_f = (wf.ref.astype(complex) / txrms)
        tx_f = (wf.tx.astype(complex) / txrms)
        Lf = frame_len(wf)
        if Lf > len(tx_f):
            pad = np.zeros(Lf - len(tx_f), complex)
            ref_f = np.concatenate([ref_f, pad]); tx_f = np.concatenate([tx_f, pad])
        self.Lf = Lf
        self.ref_frame = ref_f
        self.tx_frame = tx_f
        self.N = self.M * Lf
        self.ref_cpi_np = np.tile(ref_f, self.M)
        self.ref = torch.as_tensor(self.ref_cpi_np, dtype=CDTYPE, device=DEV)
        Rf = torch.conj(torch.fft.fft(torch.as_tensor(ref_f, dtype=CDTYPE, device=DEV)))
        if whiten:
            # 대조군: 필터를 conj(Ref)/|Ref| 로 (점유 빈에서 크기 1) → 출력 잡음 PSD 가
            # 점유대역 안에서 평평 = 거리축 부엽/상관이 최소인 '부정합(백색화) 필터'.
            # (1/|Ref|^2 로 나누면 |Ref|가 작은 빈에서 이득이 폭발해 오히려 색이 진해진다.)
            mag = torch.abs(Rf)
            keep = mag > 1e-3 * mag.max()
            Rf = torch.where(keep, Rf / (mag + 1e-30), torch.zeros_like(Rf))
        self.Rf = Rf
        w = np.hanning(self.M) if window == "hann" else np.ones(self.M)
        self.window = window
        self.win = torch.as_tensor(w, dtype=torch.float64, device=DEV)[None, :, None]
        self.n_taps = int(n_taps)
        # ECA 프리컴퓨트 (XᴴX 의 Cholesky) — passive_process.ECACanceller 와 동일 구성
        r = self.ref
        R = torch.stack([torch.vdot(r[: self.N - d], r[d:]) for d in range(self.n_taps)])
        idx = torch.arange(self.n_taps, device=DEV)
        D = idx[None, :] - idx[:, None]
        XhX = torch.where(D <= 0, R[D.abs()], torch.conj(R[D.abs()])) \
            + 1e-6 * torch.eye(self.n_taps, dtype=CDTYPE, device=DEV)
        self.XhX = XhX
        self.prf = self.fs / Lf
        self.f_d = np.fft.fftshift(np.fft.fftfreq(self.M, d=1 / self.prf))
        self.zd = int(np.argmin(np.abs(self.f_d)))

    def cancel(self, surv):                          # (B, N) → ECA 잔차
        B = surv.shape[0]
        C = torch.stack([(torch.conj(self.ref[: self.N - i])[None, :] * surv[:, i:]).sum(1)
                         for i in range(self.n_taps)], dim=1)          # (B, n_taps) = Xᴴs
        w = torch.linalg.solve(self.XhX, C.transpose(0, 1))            # (n_taps, B)
        out = surv.clone()
        for k in range(self.n_taps):                                   # ref ∗ w (인과 FIR) 제거
            out[:, k:] -= w[k][:, None] * self.ref[None, : self.N - k]
        return out

    def rd(self, surv, n_range):                     # (B,N) → |RD| (B, M, n_range)
        B = surv.shape[0]
        S = surv.view(B, self.M, self.Lf)
        RP = torch.fft.ifft(torch.fft.fft(S, dim=2) * self.Rf[None, None, :], dim=2)[:, :, :n_range]
        RD = torch.fft.fftshift(torch.fft.fft(RP * self.win, dim=1), dim=1)
        return torch.abs(RD)

    def noise(self, B, gen):
        n = torch.randn(B, self.N, 2, dtype=torch.float64, device=DEV, generator=gen)
        return torch.view_as_complex(n) / np.sqrt(2.0)   # per-sample 전력 = 1

    def dpi_det(self, dpi_amp, clutter):
        """DPI(=전체 송신신호 tx) + 정적 클러터 의 결정론적 감시신호 성분 (1, N)."""
        tx_cpi = np.tile(self.tx_frame, self.M)
        f = np.fft.fftfreq(self.N, d=1 / self.fs)
        F = np.fft.fft(tx_cpi)
        s = dpi_amp * tx_cpi
        for (ctau, camp) in clutter:
            s = s + camp * np.fft.ifft(F * np.exp(-1j * 2 * np.pi * f * ctau))
        return torch.as_tensor(s[None, :], dtype=CDTYPE, device=DEV)

    def target(self, a_tgt, tau, fd):
        """표적 에코(기준성분만 코히어런트) — run_min_cell 과 동일 모델."""
        f = np.fft.fftfreq(self.N, d=1 / self.fs)
        d = a_tgt * np.fft.ifft(np.fft.fft(self.ref_cpi_np) * np.exp(-1j * 2 * np.pi * f * tau))
        n = np.arange(self.N)
        s = d * np.exp(1j * 2 * np.pi * fd * n / self.fs)
        return torch.as_tensor(s[None, :], dtype=CDTYPE, device=DEV)


def verify_chain_against_numpy(chain):
    """GPU 체인이 passive_process(numpy) 와 같은 RD/ECA 를 내는지 — 1 trial 상대오차."""
    rng = np.random.default_rng(7)
    x = (rng.standard_normal(chain.N) + 1j * rng.standard_normal(chain.N)) / np.sqrt(2)
    # RD
    _, _, rd_np = range_doppler(x, chain.ref_cpi_np, chain.fs, chain.M, n_range=64)
    rd_gpu = chain.rd(torch.as_tensor(x[None], dtype=CDTYPE, device=DEV), 64)[0].cpu().numpy()
    e_rd = float(np.max(np.abs(rd_gpu - rd_np)) / (rd_np.max() + 1e-30))
    # ECA
    res_np = ECACanceller(chain.ref_cpi_np, chain.n_taps).cancel(x)
    res_gpu = chain.cancel(torch.as_tensor(x[None], dtype=CDTYPE, device=DEV))[0].cpu().numpy()
    e_eca = float(np.max(np.abs(res_gpu - res_np)) / (np.max(np.abs(res_np)) + 1e-30))
    return dict(rd_rel_err=e_rd, eca_rel_err=e_eca)


# =========================================================================== #
#  4. 실험 A — 이상적 백색 맵 (구현 자체의 교정)
# =========================================================================== #
def exp_white(shape, n_maps, batch, seed=11):
    nd, nr = shape
    gen = torch.Generator(device=DEV); gen.manual_seed(seed)
    cnt = Counter(zd_index=nd // 2)
    done = 0
    while done < n_maps:
        B = min(batch, n_maps - done)
        z = torch.randn(B, nd, nr, 2, dtype=torch.float64, device=DEV, generator=gen)
        rd = torch.abs(torch.view_as_complex(z) / np.sqrt(2.0))
        cnt.add(rd, PFA_NOM, GT)
        done += B
    return cnt.result()


# =========================================================================== #
#  5. 실험 B/C/D — 실제 처리체인 잡음 맵
# =========================================================================== #
def rd_whiteness(rd):
    """RD 맵 잡음의 '백색성' 진단.
      · 전력 지수분포성: mean/std 비 (지수분포면 1.0), 사분위 대비 이론값
      · 인접 셀 전력 상관계수 (거리축/도플러축 lag 1..4)
      · 유효 독립셀 수 비율 = 1/(1+2*sum rho_k) 근사 (거리·도플러 각각)"""
    P = rd ** 2
    mu = P.mean(); sd = P.std()
    out = dict(power_mean=float(mu), power_std_over_mean=float(sd / (mu + 1e-30)))
    x = P - mu
    def corr(axis, lag):
        if x.shape[axis + 1] <= lag:
            return float("nan")
        a = np.take(x, np.arange(0, x.shape[axis + 1] - lag), axis=axis + 1)
        b = np.take(x, np.arange(lag, x.shape[axis + 1]), axis=axis + 1)
        return float((a * b).mean() / (x.var() + 1e-30))
    out["rho_range"] = [corr(1, k) for k in range(1, 5)]     # axis1=doppler,axis2=range
    out["rho_doppler"] = [corr(0, k) for k in range(1, 5)]
    sr = 1 + 2 * sum(max(v, 0) for v in out["rho_range"] if np.isfinite(v))
    sdop = 1 + 2 * sum(max(v, 0) for v in out["rho_doppler"] if np.isfinite(v))
    out["eff_indep_frac_range"] = 1.0 / sr
    out["eff_indep_frac_doppler"] = 1.0 / sdop
    out["eff_indep_frac_2d"] = 1.0 / (sr * sdop)
    return out


def exp_chain(chain, n_maps, batch, mode, dpi_amp=0.0, clutter=(), n_range_op=16, seed=23):
    """mode: 'noise' | 'dpi_eca'.  반환 (op 결과, wide 결과, 백색성 진단)."""
    gen = torch.Generator(device=DEV); gen.manual_seed(seed)
    nw = min(N_RANGE_WIDE, chain.Lf)
    c_op = Counter(chain.zd); c_wd = Counter(chain.zd)
    det_sig = chain.dpi_det(dpi_amp, clutter) if mode == "dpi_eca" else None
    diag = None
    done = 0
    while done < n_maps:
        B = min(batch, n_maps - done)

        def _mk(bb):
            s = chain.noise(bb, gen)
            if det_sig is not None:
                s = s + det_sig
                s = chain.cancel(s)
            return chain.rd(s, nw)
        rd, B = _oom_retry(_mk, B)      # OOM 이면 배치 반감 재시도 (아래 카운터 갱신 전에 끝난다)
        batch = min(batch, B)
        c_wd.add(rd, PFA_NOM, GT)
        c_op.add(rd[:, :, :n_range_op].contiguous(), PFA_NOM, GT)
        if diag is None:
            diag = rd_whiteness(rd.cpu().numpy())
        done += B
    return c_op.result(), c_wd.result(), diag


# =========================================================================== #
#  6. 교정 룩업표 — 경험적 Pfa 목표 → 줘야 할 명목 Pfa (log-log 보간)
# =========================================================================== #
def calibration_table(rows, gt, mask, targets=(1e-2, 1e-3, 1e-4, 1e-5, 1e-6)):
    r = sorted([x for x in rows if x["gt"] == gt and x["zd_mask_width"] == mask],
               key=lambda x: x["pfa_nom"])
    xs = np.array([x["pfa_nom"] for x in r])                 # 명목
    ys = np.array([x["pfa_emp"] for x in r])                 # 경험
    ok = ys > 0
    if ok.sum() < 2:
        return {"note": "히트 부족 — 보간 불가", "points": []}
    lx, ly = np.log10(xs[ok]), np.log10(ys[ok])
    o = np.argsort(ly)
    tab = []
    for tgt in targets:
        lt = np.log10(tgt)
        if lt < ly[o].min() or lt > ly[o].max():
            need = float("nan"); extrap = True
        else:
            need = float(10 ** np.interp(lt, ly[o], lx[o])); extrap = False
        tab.append(dict(pfa_target_emp=tgt, pfa_nominal_needed=need, extrapolated=extrap))
    slope, icpt = np.polyfit(lx, ly, 1)                       # log10(emp) = a*log10(nom)+b
    return dict(loglog_slope=float(slope), loglog_intercept=float(icpt),
                points=tab,
                measured=[dict(nom=float(a), emp=float(b)) for a, b in zip(xs, ys)])


# =========================================================================== #
#  7. ROC — 알려진 표적 진폭에서 Pd vs 경험적 Pfa
# =========================================================================== #
def exp_roc(chain, amps, n_trials, batch, dpi_amp, clutter, tau, fd, n_range_op,
            emp_map, gt=GT[GT_DEFAULT], seed=41):
    """dpi_eca 형상에 표적을 넣고 Pd(참셀 ±1 히트) 측정. emp_map: 명목→경험 Pfa(같은 형상)."""
    gen = torch.Generator(device=DEV); gen.manual_seed(seed)
    det_sig = chain.dpi_det(dpi_amp, clutter)
    Rb_axis = np.arange(n_range_op) * C0 / chain.fs
    ri = int(np.argmin(np.abs(Rb_axis - tau * C0)))
    di = int(np.argmin(np.abs(chain.f_d - fd)))
    g, t = gt
    out = []
    for a in amps:
        tg = chain.target(a, tau, fd)
        hits = {p: 0 for p in PFA_NOM}
        scr = []
        done = 0
        while done < n_trials:
            B = min(batch, n_trials - done)
            # ⭐ 여기가 2026-07-29 에 19분치를 날린 자리다. OOM 이면 배치를 줄여 재시도하고,
            #   줄어든 배치를 **이후 반복에도 유지**한다(매 반복 다시 터지며 시간 버리지 않게).
            def _mk(bb, _tg=tg):
                s = chain.noise(bb, gen) + det_sig + _tg
                return chain.rd(chain.cancel(s), n_range_op).cpu().numpy()
            rd, B = _oom_retry(_mk, B)
            batch = min(batch, B)
            P, noise, ntr = cfar_stats(rd, g, t)
            valid = ntr > 0
            valid[chain.zd, :] = False                        # 0-도플러 마스킹(운용 그대로)
            sl = (slice(None), slice(max(0, di - 1), di + 2), slice(max(0, ri - 1), ri + 2))
            for p in PFA_NOM:
                det = valid[None] & (P > alpha_of(ntr, p)[None] * noise)
                hits[p] += int(det[sl].any(axis=(1, 2)).sum())
            # SCR: 표적셀 최대전력 / (표적·0도플러 제외) 평균전력
            m = np.ones(rd.shape[1:], bool)
            m[max(0, chain.zd - 1):chain.zd + 2, :] = False
            m[max(0, di - 3):di + 4, max(0, ri - 3):ri + 4] = False
            num = (rd[sl] ** 2).max(axis=(1, 2))
            den = (rd ** 2)[:, m].mean(axis=1) + 1e-30
            scr += list(10 * np.log10(num / den))
            done += B
        pts = []
        for p in PFA_NOM:
            pd = hits[p] / n_trials
            lo, hi = wilson_ci(hits[p], n_trials)
            pts.append(dict(pfa_nom=p, pfa_emp=emp_map.get(p, float("nan")),
                            pd=pd, pd_lo=lo, pd_hi=hi))
        out.append(dict(a_tgt=float(a), scr_db=float(np.mean(scr)), n_trials=int(n_trials),
                        points=pts))
    return out


# =========================================================================== #
#  main
# =========================================================================== #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--maps", type=int, default=10_000, help="체인 잡음맵 수(파형·모드별)")
    ap.add_argument("--white", type=int, default=500_000, help="이상 백색맵 수")
    ap.add_argument("--roc", type=int, default=1000, help="ROC trial 수(진폭별)")
    ap.add_argument("--out", default=os.path.join(_ROOT, "outputs", "verify_cfar.json"))
    a = ap.parse_args()
    if a.quick:
        a.maps, a.white, a.roc = 200, 20_000, 100

    t0 = time.time()
    # ⚠ 2026-07-29: meta 에 **생성 시각이 없었다**. `passive_process` 가 이 파일에서 Pfa 교정표를
    #   읽어 쓰는데, 시각이 없으면 "그 사본이 어느 측정에서 왔나" 를 추적할 수 없다(provenance 단절).
    res = dict(meta=dict(generated=time.strftime("%Y-%m-%d %H:%M:%S"),
                         M_cpi=M_CPI, pfa_nominal=PFA_NOM,
                         guard_train=[gt_key(g, t) for (g, t) in GT],
                         gt_default=gt_key(*GT[GT_DEFAULT]),
                         n_range_wide=N_RANGE_WIDE,
                         dtype=str(CDTYPE), device=str(DEV),
                         zd_mask_widths=list(ZD_MASK_W), zd_mask_operational=ZD_MASK_OP,
                         n_maps_chain=a.maps, n_maps_white=a.white, n_roc=a.roc,
                         eirp_dbm=EIRP_DBM))

    # --- 0) alpha 식 감사 -------------------------------------------------- #
    res["alpha_audit"] = audit_alpha()
    rng = np.random.default_rng(3)
    rd_probe = np.abs(rng.standard_normal((48, 24)) + 1j * rng.standard_normal((48, 24))) / np.sqrt(2)
    res["fast_path_identical_to_ca_cfar_2d"] = all(
        verify_fast_equals_reference(rd_probe, g, t, p) for (g, t) in GT for p in (1e-2, 1e-4, 1e-6))
    print(f"[0] alpha 감사 완료. fast-path 동일성={res['fast_path_identical_to_ca_cfar_2d']}")

    # --- 1) 이상적 백색 맵 -------------------------------------------------- #
    res["white"] = {}
    for tag, shape in [("48x24", (48, 24)), ("48x256", (48, 256))]:
        n = a.white if shape[1] == 24 else max(a.white // 10, 100)
        res["white"][tag] = exp_white(shape, n, batch=20000 if shape[1] == 24 else 2000)
        r0 = [x for x in res["white"][tag]["rows"]
              if x["gt"] == gt_key(*GT[GT_DEFAULT]) and x["zd_mask_width"] == 0
              and x["pfa_nom"] == 1e-4][0]
        print(f"[1] white {tag}: cells={r0['cells']:.3g} pfa(1e-4)={r0['pfa_emp']:.3e} "
              f"ratio={r0['ratio']:.2f}  ({time.time()-t0:.0f}s)")

    # --- 2) 체인 --------------------------------------------------------- #
    wfs = [("WiFi80", wifi_80211ac(bw_hz=80e6, carrier_hz=5.21e9)),
           ("LTE20", lte_downlink(bw_hz=20e6, carrier_hz=1.843e9)),
           ("NR100", nr_downlink(bw_hz=100e6, carrier_hz=3.5e9))]
    lb = LinkBudget(eirp_dbm=EIRP_DBM)
    L = float(np.linalg.norm(np.array(TX) - np.array(RX)))
    res["chain"] = {}
    res["chain_verify"] = {}
    for name, wf in wfs:
        n_range, n_taps = chamber_window(wf)
        ch = Chain(wf, n_taps)
        res["chain_verify"][name] = verify_chain_against_numpy(ch)
        # 물리 DPI: 링크버짓 직접파/잡음 + 잡음대역보정(run_min_cell 규약)
        bw_corr = float(np.sqrt(wf.bw_hz / wf.fs_hz))
        dpi = float(np.sqrt(lb.direct_power_w(C0 / wf.carrier_hz, L)
                            / lb.noise_power_w(wf.bw_hz))) * bw_corr
        clut = tuple((dt, dpi * r) for (dt, r) in CH_CLUTTER_RATIO)
        # ⚠ 2026-07-29: 이 3.0e6 도 하드코딩 예산이었다(batch_for 의 6e9 와 같은 병).
        #   실제 카드 예산에 비례해 깎는다 — 기준 6 GB 에서 옛 값과 같아지도록 맞췄다.
        _scale = min(1.0, max(0.05, (_gpu_budget_bytes() / 6.0e9)))
        batch = max(1, int(3.0e6 / (M_CPI * ch.Lf) * 12 * _scale))
        entry = dict(fs_hz=wf.fs_hz, Lf=ch.Lf, prf_hz=ch.prf, n_range_op=n_range,
                     n_taps=n_taps, ref_bw_hz=wf.ref_bw_hz, dpi_amp=dpi,
                     dnr_db=float(20 * np.log10(dpi + 1e-30)), batch=batch)
        for si, mode in enumerate(("noise", "dpi_eca")):
            op, wd, diag = exp_chain(ch, a.maps, batch, mode, dpi_amp=dpi, clutter=clut,
                                     n_range_op=n_range, seed=1000 + 10 * len(name) + si)
            entry[mode] = dict(op=op, wide=wd, whiteness=diag)
            k = gt_key(*GT[GT_DEFAULT])
            for msk in ZD_MASK_W:
                entry[mode][f"calib_op_mask{msk}"] = calibration_table(op["rows"], k, msk)
                entry[mode][f"calib_wide_mask{msk}"] = calibration_table(wd["rows"], k, msk)
            r0 = [x for x in op["rows"] if x["gt"] == k and x["zd_mask_width"] == ZD_MASK_OP
                  and x["pfa_nom"] == 1e-4][0]
            rw = [x for x in wd["rows"] if x["gt"] == k and x["zd_mask_width"] == ZD_MASK_OP
                  and x["pfa_nom"] == 1e-4][0]
            rw3 = [x for x in wd["rows"] if x["gt"] == k and x["zd_mask_width"] == 3
                   and x["pfa_nom"] == 1e-4][0]
            entry[mode]["wide_mask1_vs_mask3_ratio_at_1e4"] = [rw["ratio"], rw3["ratio"]]
            print(f"[2] {name}/{mode}: op cells={r0['cells']:.3g} "
                  f"pfa_emp(1e-4,mask1)={r0['pfa_emp']:.3e} ratio={r0['ratio']:.2f} | "
                  f"WIDE ratio mask1={rw['ratio']:.1f} mask3={rw3['ratio']:.2f} | "
                  f"rho_range={diag['rho_range'][0]:+.2f} rho_dop={diag['rho_doppler'][0]:+.2f} "
                  f"({time.time()-t0:.0f}s)")
        res["chain"][name] = entry

    # --- 3) 대조군 (원인 규명) — 5G: 백색화 정합필터 / 도플러창 제거 ------- #
    k = gt_key(*GT[GT_DEFAULT])
    wf = dict(wfs)["NR100"]
    n_range, n_taps = chamber_window(wf)
    for tag, kw in [("whitened_mf", dict(whiten=True)),
                    ("rect_window", dict(window="rect")),
                    ("whitened_mf_rect", dict(whiten=True, window="rect"))]:
        chw = Chain(wf, n_taps, **kw)
        batch = batch_for(chw)
        op, wd, diag = exp_chain(chw, a.maps, batch, "noise", n_range_op=n_range, seed=99)
        res[f"control_{tag}_NR100"] = dict(op=op, wide=wd, whiteness=diag, kwargs=str(kw))
        r0 = [x for x in wd["rows"] if x["gt"] == k and x["zd_mask_width"] == ZD_MASK_OP
              and x["pfa_nom"] == 1e-4][0]
        print(f"[3] NR100/{tag}: (wide) pfa_emp(1e-4)={r0['pfa_emp']:.3e} ratio={r0['ratio']:.2f} "
              f"rho_range={diag['rho_range'][0]:+.2f} rho_dop={diag['rho_doppler'][0]:+.2f} "
              f"({time.time()-t0:.0f}s)")
    res["control_note"] = ("whitened_mf = conj(Ref)/|Ref| 부정합필터(거리축 색칠 제거), "
                           "rect_window = slow-time Hann 제거(도플러축 상관 제거). "
                           "두 대조군이 경험적 Pfa 를 명목으로 되돌리면, 어긋남의 원인이 "
                           "'RD 맵의 셀간 상관'임이 증명된다.")

    # --- 4) ROC (5G, 운용 형상 dpi_eca) ------------------------------------ #
    ch = Chain(wf, n_taps)
    bw_corr = float(np.sqrt(wf.bw_hz / wf.fs_hz))
    dpi = float(np.sqrt(lb.direct_power_w(C0 / wf.carrier_hz, L) / lb.noise_power_w(wf.bw_hz))) * bw_corr
    clut = tuple((dt, dpi * r) for (dt, r) in CH_CLUTTER_RATIO)
    p = bistatic_params(TX, RX, CENTER, (-SPEED, 0.0, 0.0), wf.carrier_hz)
    emp = {x["pfa_nom"]: x["pfa_emp"] for x in res["chain"]["NR100"]["dpi_eca"]["op"]["rows"]
           if x["gt"] == k and x["zd_mask_width"] == ZD_MASK_OP}
    batch = batch_for(ch)
    amps = [3e-4, 6e-4, 1e-3, 2e-3, 4e-3, 8e-3]
    res["roc_NR100"] = dict(
        tau_s=p["tau"], fd_hz=p["fd"], Rb_m=p["tau"] * C0, gt=k, zd_mask_width=ZD_MASK_OP,
        curves=exp_roc(ch, amps, a.roc, batch, dpi, clut, p["tau"], p["fd"], n_range,
                       emp_map=emp))
    for c in res["roc_NR100"]["curves"]:
        pt = [q for q in c["points"] if q["pfa_nom"] == 1e-4][0]
        print(f"[4] ROC a={c['a_tgt']:.1e} SCR={c['scr_db']:+.1f}dB → "
              f"Pd(nom 1e-4)={pt['pd']:.2f} @ emp Pfa={pt['pfa_emp']:.2e}")

    res["meta"]["runtime_s"] = time.time() - t0
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w") as f:
        json.dump(res, f, indent=1, default=float)
    print(f"\n저장: {a.out}  ({res['meta']['runtime_s']:.0f}s)")


if __name__ == "__main__":
    main()
