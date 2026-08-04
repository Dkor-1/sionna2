# -*- coding: utf-8 -*-
"""
lowfreq_anchor_ptd.py — **1 차 PTD 를 얹으면 저주파 간극이 닫히는가**
================================================================================
드론 라운드(`outputs/lowfreq_grid.json` caveat 3)가 열어 둔 후보를 닫는다:

    "PTD 모서리 프린지 항은 꺼져 있다(생산 규약 ptd=False). 프린지 기여는 저주파에서
     상대적으로 커지므로 저대역 기울기를 바꿀 수 있는 **미검증 후보**다."

얇은 띠에는 참값(2D MoM)이 있으므로 여기서는 그 후보를 **직접 검정**할 수 있다.
생산 커널을 ptd=False / ptd=True(V·H) 로 각각 돌리고, 정면입사 해석 과녁

    σ_PO      = 4π(ab)²/λ²
    σ_PO+PTD  = 4π b²(a² + 1/k²)/λ²      ← θ=0 에서 f¹=g¹=−1/2 이므로 |W_soft|=|W_hard|

와, 그리고 **참값** MoM TM·TE 와 나란히 놓는다.

⭐ 예상되는 결론: 1 차 프린지는 정면입사에서 **편파를 가르지 못한다**(V·H 가 같은 값). 참값은
   0.15λ 에서 11.5 dB 갈라진다 → 스칼라 PO(+1차 PTD)로는 원리적으로 못 맞춘다.

산출: outputs/partial/lowfreq_anchor/ptd.json
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (os.path.join(_ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

C0 = 299792458.0
PART = os.path.join(_ROOT, "outputs", "partial", "lowfreq_anchor")
FC = 1.8e9
A_LAM = (0.15, 0.30, 0.60, 1.00, 2.00)
B_LAM = 6.0
DIVS = (12, 64, 256)
JITTER = 3


def main():
    from gpu import pick, gpu_status
    pick()
    from geom import quad
    from rcs_sbr import rcs_sbr_batch

    os.makedirs(PART, exist_ok=True)
    t0 = time.perf_counter()
    lam = C0 / FC
    k = 2 * np.pi / lam
    b = B_LAM * lam
    rows = []
    print(f"[ptd] f={FC/1e9:.2f} GHz λ={lam*1e3:.3f} mm  b={B_LAM}λ  jitter={JITTER}")
    print(f"    {'a/λ':>6} {'λ/d':>5} {'σ(PO)':>9} {'σ(+PTD V)':>10} {'σ(+PTD H)':>10} "
          f"{'PO목표':>9} {'PO+PTD목표':>10} {'V−H[dB]':>9}")
    for al in A_LAM:
        a = al * lam
        pl = quad((-a / 2, -b / 2, 0.0), (a / 2, -b / 2, 0.0),
                  (a / 2, b / 2, 0.0), (-a / 2, b / 2, 0.0), group="metal")
        s_po_t = 4 * np.pi * (a * b) ** 2 / lam ** 2
        s_ptd_t = 4 * np.pi * b ** 2 * (a ** 2 + 1.0 / k ** 2) / lam ** 2
        for div in DIVS:
            d = lam / div
            kw = dict(az_deg=0.0, el_deg=90.0, spacing=d, jitter=JITTER,
                      penetrate=False, cache_key=("lfa_ptd", al))
            s0 = float(rcs_sbr_batch(pl, {"metal": 1.0}, FC, ptd=False, **kw))
            sV = float(rcs_sbr_batch(pl, {"metal": 1.0}, FC, ptd=True, ptd_pol="V", **kw))
            sH = float(rcs_sbr_batch(pl, {"metal": 1.0}, FC, ptd=True, ptd_pol="H", **kw))
            db = lambda x: float(10 * np.log10(max(x, 1e-300)))
            rows.append(dict(a_lam=al, div=div, d_mm=float(d * 1e3),
                             samples_across_width=float(a / d),
                             po_dbsm=db(s0), ptd_v_dbsm=db(sV), ptd_h_dbsm=db(sH),
                             target_po_dbsm=db(s_po_t), target_po_ptd_dbsm=db(s_ptd_t),
                             kernel_po_minus_target_db=db(s0) - db(s_po_t),
                             kernel_ptd_minus_target_db=db(sV) - db(s_ptd_t),
                             v_minus_h_db=db(sV) - db(sH)))
            r = rows[-1]
            print(f"    {al:6.2f} {div:5d} {r['po_dbsm']:+9.3f} {r['ptd_v_dbsm']:+10.3f} "
                  f"{r['ptd_h_dbsm']:+10.3f} {r['target_po_dbsm']:+9.3f} "
                  f"{r['target_po_ptd_dbsm']:+10.3f} {r['v_minus_h_db']:+9.6f}", flush=True)

    out = dict(part="ptd", generated=time.strftime("%Y-%m-%d %H:%M:%S"),
               fc_hz=FC, lam_m=float(lam), b_lam=B_LAM, divs=list(DIVS), jitter=JITTER,
               rows=rows,
               max_abs_v_minus_h_db=float(max(abs(r["v_minus_h_db"]) for r in rows)),
               analytic_note=("정면입사에서 1차 Ufimtsev 계수는 f¹=g¹=−1/2 이므로 "
                              "W_soft=a−j/k, W_hard=a+j/k → |W| 가 같다. 즉 1차 PTD 는 "
                              "정면입사에서 편파를 **못 가른다**. 커널의 V·H 일치가 그 확인이다."),
               gpu=os.environ.get("CUDA_VISIBLE_DEVICES", "?"), gpu_status=gpu_status(),
               runtime_s=float(time.perf_counter() - t0))
    p = os.path.join(PART, "ptd.json")
    with open(p, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"\n[ptd] → {p}  (V−H 최대 {out['max_abs_v_minus_h_db']:.2e} dB, "
          f"{out['runtime_s']:.0f} s)")


if __name__ == "__main__":
    main()
