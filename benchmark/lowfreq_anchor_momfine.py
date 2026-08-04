# -*- coding: utf-8 -*-
"""
lowfreq_anchor_momfine.py — PO−참값 간극을 **폭 축에서 조밀하게** 훑는다
================================================================================
`lowfreq_anchor.py mom` 은 커널을 돌린 5 개 폭에서만 참값을 냈다(사과-대-사과용).
그런데 "간극이 어느 특징/λ 에서 폭발하는가"(드론의 blade/λ=0.2712 전이와 견줄 값)는
그 5 점으로는 위치를 못 짚는다. 여기서는 **MoM 만** 폭 축을 조밀하게 훑는다(GPU 불필요).

산출: outputs/partial/lowfreq_anchor/momfine.json
"""
from __future__ import annotations

import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (os.path.join(_ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

C0 = 299792458.0
PART = os.path.join(_ROOT, "outputs", "partial", "lowfreq_anchor")
FC = 1.8e9
A_LAM = (0.05, 0.08, 0.10, 0.12, 0.15, 0.18, 0.20, 0.25, 0.2712, 0.30, 0.35, 0.40,
         0.50, 0.60, 0.70, 0.80, 1.00, 1.25, 1.50, 2.00, 2.50, 3.00, 4.00)
SEG_PER_LAM, SEG_MIN, SEG_MAX = 400, 60, 220


def _one(al):
    import mom2d_reference as mom
    lam = C0 / FC
    k = 2 * np.pi / lam
    a = al * lam
    M = int(np.clip(round(SEG_PER_LAM * al), SEG_MIN, SEG_MAX))
    u = np.array([0.0, 1.0]); e_r = np.array([-1.0, 0.0])
    nd = mom.strip_nodes(a, M)
    W_tm = (mom.Z0 / 2) * mom.solve_tm(mom.assemble_tm(nd, k), u)[0]
    W_te = (mom.Z0 / 2) * mom.solve_te(mom.assemble_te(nd, k, closed=False), u, e_r)[0]
    s_po, s_tm, s_te = k * a ** 2, k * abs(W_tm) ** 2, k * abs(W_te) ** 2
    s_ptd = k * (a ** 2 + 1.0 / k ** 2)          # PO + 1차 PTD (정면입사 닫힌형)
    db = lambda x, y: float(10 * np.log10(x / y))
    return dict(a_lam=float(al), a_mm=float(a * 1e3), n_seg=M,
                sigma2d_po=float(s_po), sigma2d_tm=float(s_tm), sigma2d_te=float(s_te),
                sigma2d_po_ptd=float(s_ptd),
                po_minus_tm_db=db(s_po, s_tm), po_minus_te_db=db(s_po, s_te),
                po_ptd_minus_tm_db=db(s_ptd, s_tm), po_ptd_minus_te_db=db(s_ptd, s_te),
                tm_minus_te_db=db(s_tm, s_te))


def main():
    os.makedirs(PART, exist_ok=True)
    t0 = time.perf_counter()
    print(f"[momfine] 폭 {len(A_LAM)} 점, f={FC/1e9:.2f} GHz, 정면입사, CPU 병렬")
    with ProcessPoolExecutor(max_workers=16) as ex:
        rows = list(ex.map(_one, A_LAM))
    for r in rows:
        print(f"    a={r['a_lam']:6.4f}λ ({r['a_mm']:6.2f} mm) M={r['n_seg']:4d}  "
              f"PO−TM {r['po_minus_tm_db']:+7.3f}  PO−TE {r['po_minus_te_db']:+7.3f}  "
              f"TM−TE {r['tm_minus_te_db']:+7.3f}  |  +PTD: TM {r['po_ptd_minus_tm_db']:+7.3f} "
              f"TE {r['po_ptd_minus_te_db']:+7.3f}")
    #  간극이 1 dB 를 넘는 구간의 상단(=무릎) — 두 편파 중 나쁜 쪽 기준
    worst = [(r["a_lam"], max(abs(r["po_minus_tm_db"]), abs(r["po_minus_te_db"]))) for r in rows]
    above = [a for a, g in worst if g > 1.0]
    knee = float(max(above)) if above else None
    #  1 dB 를 마지막으로 넘은 점과 그 다음 점 사이를 선형보간해 무릎을 더 정확히
    knee_interp = None
    ws = sorted(worst)
    for (a0, g0), (a1, g1) in zip(ws[:-1], ws[1:]):
        if g0 > 1.0 >= g1:
            knee_interp = float(a0 + (a1 - a0) * (g0 - 1.0) / (g0 - g1))
    out = dict(part="momfine", generated=time.strftime("%Y-%m-%d %H:%M:%S"),
               fc_hz=FC, lam_mm=float(C0 / FC * 1e3), a_lam=list(A_LAM), rows=rows,
               knee_a_over_lam_last_above_1db=knee,
               knee_a_over_lam_interp_1db=knee_interp,
               knee_rule="max(|PO−MoM TM|,|PO−MoM TE|) 가 1 dB 를 넘는 구간의 상단",
               runtime_s=float(time.perf_counter() - t0))
    p = os.path.join(PART, "momfine.json")
    with open(p, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"\n[momfine] 무릎 a/λ = {knee} (보간 {knee_interp})  → {p}  "
          f"({out['runtime_s']:.0f} s)")


if __name__ == "__main__":
    main()
