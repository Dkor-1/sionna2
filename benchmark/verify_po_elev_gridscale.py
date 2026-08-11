# -*- coding: utf-8 -*-
"""
verify_po_elev_gridscale.py — ⭐**앙각 −90° 의 초과 대역이 물리인가 격자인가**

`verify_po_elev_geomref.py` 가 찾은 것: el=−90° 에서 우리 커널의 요동 에너지 **53 %** 가
기하가 원리적으로 낼 수 없는 대역(Carson 상한 156 Hz 밖)에 있고, 그 스펙트럼은 Nyquist 까지
**평평한 빗**(m·f_flash 에 정확히 얹힌다)이다.

가설 두 개
  H_phys  날개가 동체 그림자를 드나드는 **진짜 하드 스위칭**이다 → 격자를 조밀하게 해도 안 변한다
  H_grid  회전하는 날개 실루엣과 **얼린 정사각 광선격자**의 모아레다 → 초과 에너지가 간격 d 에
          비례해 줄어든다(덮는 칸 수 오차 ∝ 둘레·d / 면적)

⭐ el=−90° 는 날개가 **등거리(iso-range)** 라 칸 수 오차가 전부 **같은 위상**으로 더해진다 —
   다른 앙각에서는 무작위 위상으로 상쇄되던 것이 여기서는 안 상쇄된다. 그래서 최악이다.

간격 사다리 d = λ/8, λ/12(생산), λ/16 · 앞 512 자세 · 다른 축은 전부 고정.
⛔ 가벼운 작업(자세당 광선 ~n², n≈180). 기존 원장 안 건드림.
"""
from __future__ import annotations

import json
import os
import sys
import time

os.environ.setdefault("SIONNA2_GPU", "2")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np                                                    # noqa: E402

import argparse
_ap = argparse.ArgumentParser(); _ap.add_argument("--el", type=float, default=-90.0)
_ap.add_argument("--divs", default="8,12,16"); _A, _ = _ap.parse_known_args()
FC, RANGE_M, EL, AZ = 3.5e9, 10.0, _A.el, 0.0
LAM = 299792458.0 / FC
DIVS = tuple(int(x) for x in _A.divs.split(","))
N_USE = 512
OUT = os.path.join(ROOT, "outputs", "verify_po_elev_gridscale.json" if EL == -90.0
                   else f"verify_po_elev_gridscale_el{EL:+.0f}.json")
TJ = json.load(open(os.path.join(ROOT, "outputs", "report07_three_engines.json")))["_meta"]


def main():
    from gpu import pick
    pick(verbose=True)
    from articulated_fast import FastPoser, rotor_phases
    from drones import DRONES, DRONE_GROUP_MAT
    from rcs_sbr import sbr_field, grid_ref_from

    spec = DRONES[TJ.get("drone", "matrice4e")]
    fp = FastPoser(spec)
    prf, n = float(TJ["prf_hz"]), int(TJ["n"])
    rpms = np.asarray(TJ["rpm_per_rotor"], float)
    ph = rotor_phases(np.arange(n) / prf, rpms, fp.dirs)
    gm = {g: m for g, (m, _) in DRONE_GROUP_MAT.items()}
    u = np.array([np.cos(np.radians(EL)) * np.cos(np.radians(AZ)),
                  np.cos(np.radians(EL)) * np.sin(np.radians(AZ)),
                  np.sin(np.radians(EL))])
    J = dict(_meta=dict(generator="benchmark/verify_po_elev_gridscale.py",
                        stamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                        question_ko="el=−90° 초과대역이 물리(하드 스위칭)인가 격자 모아레인가",
                        el_deg=EL, range_m=RANGE_M, fc_hz=FC, prf_hz=prf, n_used=N_USE,
                        divs=list(DIVS), drone=spec.key,
                        axis_ko="격자 간격 하나만 바꾼다 — 자세·rpm·재질·거리 전부 동일"),
             runs={})
    for div in DIVS:
        d = LAM / div
        gref = grid_ref_from([fp.pose(ph[i]) for i in range(0, n, max(1, n // 64))],
                             FC, spacing=d)
        E = np.zeros(N_USE, complex)
        t0 = time.time()
        for i in range(N_USE):
            E[i] = sbr_field(fp.pose(ph[i]), gm, FC, u, spacing=d,
                             grid_ref=gref, range_m=RANGE_M)
            if i and i % 128 == 0:
                print(f"  div{div}: {i}/{N_USE} {time.time()-t0:.0f}s", flush=True)
        J["runs"][f"div{div}"] = dict(
            div=div, spacing_m=float(d), n_grid=int(gref.n), sec=float(time.time() - t0),
            E_re=[float(x) for x in E.real], E_im=[float(x) for x in E.imag])
        with open(OUT, "w") as f:
            json.dump(J, f, ensure_ascii=False)
        print(f"✅ div{div} 완료 ({time.time()-t0:.0f}s, n_grid={gref.n})", flush=True)
    print(f"\n✅ 저장 → {OUT}")


if __name__ == "__main__":
    main()
