# -*- coding: utf-8 -*-
"""
lowfreq_anchor_jitter.py — **"격자가 안 움직인 게 아니라 jitter 가 가린 것 아니냐"** 에 답한다
================================================================================
가장 강한 반론: ka=1·λ/12 에서 광선격자는 구를 가로질러 겨우 ~4 칸(전체 121 발)이다.
그런데도 σ 가 최고격자와 0.05 dB 밖에 안 다르다. 이건 수렴이 아니라 **격자위상 평균(jitter)**
이 격자 오차를 지워버린 결과일 수 있다 — 그렇다면 "격자는 무관하다" 는 결론이 아니라
"우리 규약이 격자 오차를 잘 지운다" 는 다른 진술이 된다.

여기서는 그 둘을 가른다. 같은 점에서 **jitter=1(단일격자)** 과 **jitter=3(생산 규약, J²=9 오프셋)**
을 나란히 잰다.
  · jitter=1 이 이미 수렴값에 붙어 있으면 → 격자가 정말로 무관한 것.
  · jitter=1 이 크게 흔들리는데 jitter=3 이 붙어 있으면 → 평균이 일을 하고 있는 것.
    ⚠ 그래도 **결론은 바뀌지 않는다**: 어느 쪽이든 수렴 목적지는 해석 PO 이고 Mie 와의
      간극은 그대로다. 다만 "격자는 아무 상관 없다" 가 아니라 "생산 규약이 격자 오차를
      이미 처리하고 있다" 로 진술이 정확해진다. 그 차이를 숫자로 남긴다.

산출: outputs/partial/lowfreq_anchor/jitter.json
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
R = 0.10
KAS = (1.0, 2.0, 3.0, 6.0, 12.0)
DIVS_REL = (12,)
D_ABS_MM = (0.5,)
JITTERS = (1, 2, 3)
EL = (0.0, 25.0, 50.0, 75.0)
AZ_N = 6


def main():
    from gpu import pick, gpu_status
    pick()
    from geom import uv_sphere
    from rcs_sbr import rcs_sbr_batch
    from mie_pec_sphere import mie_pec_backscatter_norm, po_sphere_norm

    os.makedirs(PART, exist_ok=True)
    t0 = time.perf_counter()
    az = np.linspace(0.0, 360.0, AZ_N, endpoint=False)
    sph = uv_sphere(R, seg=720, rings=360, group="metal")
    pir2 = np.pi * R ** 2
    rows = []
    print(f"[jitter] r={R} m, 메쉬 seg=720, 입사 {len(EL)*AZ_N} 방향")
    print(f"    {'ka':>5} {'격자':>12} {'J':>2} {'σ[dBsm]':>9} {'−PO[dB]':>9} {'−Mie[dB]':>9}")
    for ka in KAS:
        lam = 2 * np.pi * R / ka
        fc = C0 / lam
        s_po = float(po_sphere_norm(ka)) * pir2
        s_mie = float(mie_pec_backscatter_norm(ka)) * pir2
        grids = [(f"lam/{v}", lam / v) for v in DIVS_REL] + \
                [(f"{v}mm", v * 1e-3) for v in D_ABS_MM]
        for gname, d in grids:
            for J in JITTERS:
                acc = []
                for el in EL:
                    v = rcs_sbr_batch(sph, {"metal": 1.0}, fc, az_deg=az, el_deg=float(el),
                                      spacing=float(d), jitter=J, penetrate=False,
                                      chunk_az=AZ_N, cache_key=("lfa_jit", 720))
                    acc.append(np.atleast_1d(np.asarray(v, float)))
                mu = float(np.concatenate(acc).mean())
                db = float(10 * np.log10(mu))
                rows.append(dict(ka=ka, grid=gname, d_mm=float(d * 1e3), jitter=J,
                                 n_offsets=J * J, sigma_dbsm=db,
                                 vs_po_db=db - float(10 * np.log10(s_po)),
                                 vs_mie_db=db - float(10 * np.log10(s_mie)),
                                 po_minus_mie_db=float(10 * np.log10(s_po / s_mie))))
                r = rows[-1]
                print(f"    {ka:5.1f} {gname:>12} {J:2d} {db:+9.3f} {r['vs_po_db']:+9.3f} "
                      f"{r['vs_mie_db']:+9.3f}", flush=True)

    #  요약: 같은 (ka, 격자) 에서 J=1 과 J=3 이 얼마나 다른가 / 각각 해석 PO 에서 얼마나 떨어졌나
    summ = {}
    for ka in KAS:
        for gname in {r["grid"] for r in rows if r["ka"] == ka}:
            sel = {r["jitter"]: r for r in rows if r["ka"] == ka and r["grid"] == gname}
            summ[f"ka{ka:g}_{gname}"] = dict(
                ka=ka, grid=gname,
                j1_vs_po_db=sel[1]["vs_po_db"], j3_vs_po_db=sel[3]["vs_po_db"],
                j1_minus_j3_db=sel[1]["sigma_dbsm"] - sel[3]["sigma_dbsm"],
                j1_vs_mie_db=sel[1]["vs_mie_db"], j3_vs_mie_db=sel[3]["vs_mie_db"],
                po_minus_mie_db=sel[1]["po_minus_mie_db"])
    worst_j1_po = max(abs(v["j1_vs_po_db"]) for v in summ.values())
    worst_j3_po = max(abs(v["j3_vs_po_db"]) for v in summ.values())
    lam12_low = [v for k, v in summ.items() if v["grid"] == "lam/12" and v["ka"] <= 3]
    out = dict(part="jitter", generated=time.strftime("%Y-%m-%d %H:%M:%S"),
               radius_m=R, kas=list(KAS), jitters=list(JITTERS), rows=rows, summary=summ,
               worst_abs_j1_vs_po_db=float(worst_j1_po),
               worst_abs_j3_vs_po_db=float(worst_j3_po),
               lowka_lam12_j1_vs_po_db=[v["j1_vs_po_db"] for v in lam12_low],
               lowka_lam12_j3_vs_po_db=[v["j3_vs_po_db"] for v in lam12_low],
               verdict_note=("어느 J 에서든 커널이 향하는 곳은 **해석 PO** 이고, Mie 와의 간극은 "
                             "po_minus_mie_db 그대로다. J 는 그 간극을 조금도 건드리지 않는다."),
               gpu=os.environ.get("CUDA_VISIBLE_DEVICES", "?"), gpu_status=gpu_status(),
               runtime_s=float(time.perf_counter() - t0))
    p = os.path.join(PART, "jitter.json")
    with open(p, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"\n[jitter] J=1 최악 |−PO| {worst_j1_po:.3f} dB · J=3 최악 {worst_j3_po:.3f} dB → {p}")


if __name__ == "__main__":
    main()
