# -*- coding: utf-8 -*-
"""
material_gamma_carbon.py — **carbon gamma_po 보충 스윕**
=========================================================
`material_gamma_sweep.py` 의 carbon 행이 세 기종(phantom4/mavic4pro/mini5pro) 전부에서
**정확히 +0.000 dB** 로 나왔다. 버그가 아니다 — 이 세 기종은 `arm_style='body'` 라
암이 플라스틱 셸 그룹으로 들어가고, **carbon 재질을 쓰는 그룹이 메쉬에 아예 없다**.
(고립 기여표에 'arm'/'deck'/'gear_cf' 행이 없는 것이 그 증거다.)

그래서 carbon 을 실제로 쓰는 기종으로 따로 잰다:
  x500v2   — Holybro X500 V2 (열린 프레임: carbon deck + carbon 튜브 착륙장치 + carbon 암)
  s1000plus — DJI S1000+ (arm_style='carbon')
⚠ 열린 프레임은 셸이 없으므로 `shell_groups=()` 로 넘긴다(rcs_sbr 규약).

실행: CUDA_VISIBLE_DEVICES=2 PYTHONPATH=src:benchmark python benchmark/material_gamma_carbon.py
"""
from __future__ import annotations

import datetime as _dt
import os
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (os.path.join(_ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from rcs_sbr import rcs_sbr_batch                        # noqa: E402
from drones import DRONES, build_drone, DRONE_GROUP_MAT  # noqa: E402
from material_sources import BANDS, _merge_write         # noqa: E402

C0 = 299792458.0
N_AZ, EL, DIV = 180, 15.0, 12
CARBON_GROUPS = [g for g, (m, _) in DRONE_GROUP_MAT.items() if m == "carbon"]


def main():
    t0 = time.time()
    out = {}
    for drone in ("x500v2", "s1000plus"):
        mesh = build_drone(DRONES[drone])
        groups = sorted(set(np.asarray(mesh.g).tolist()))
        has_shell = any(g in ("body", "canopy") for g in groups)
        sg = None if has_shell else ()
        out[drone] = dict(_groups=groups, _has_shell=bool(has_shell),
                          _carbon_groups_present=[g for g in groups if g in CARBON_GROUPS])
        for bn, fc in BANDS.items():
            lam = C0 / fc
            az = np.linspace(0.0, 360.0, N_AZ, endpoint=False)
            row = {}
            for name, ov in [("base", {})] + [(f"carbon={g:.4f}",
                                               {k: g for k in CARBON_GROUPS})
                                              for g in (0.70, 0.80, 0.9887, 0.9938, 1.0)]:
                gm = {g: m for g, (m, _) in DRONE_GROUP_MAT.items()}
                gm.update(ov)
                s = np.atleast_1d(np.asarray(
                    rcs_sbr_batch(mesh, gm, fc, az_deg=az, el_deg=EL, spacing=lam / DIV,
                                  cache_key=None, shell_groups=sg), float))
                row[name] = float(10 * np.log10(np.mean(s)))
            b = row["base"]
            out[drone][bn] = {k: dict(mean_dbsm=v, delta_vs_base_db=float(v - b))
                              for k, v in row.items()}
            print(f"[{time.time()-t0:7.1f}s] {drone:10s} {bn:14s} base={b:+7.2f}  "
                  + "  ".join(f"{k.split('=')[1]}:{v-b:+.3f}" for k, v in row.items()
                              if k != "base"), flush=True)
    _merge_write(dict(carbon_supplement=dict(
        _meta=dict(generated=_dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                   generator="benchmark/material_gamma_carbon.py",
                   n_az=N_AZ, el_deg=EL, div=DIV, runtime_s=float(time.time() - t0),
                   why="주 스윕의 carbon 행이 0.000 dB 인 이유는 그 세 기종에 carbon 그룹이 "
                       "없기 때문이다(arm_style='body'). carbon 을 실제로 쓰는 기종으로 다시 잰다."),
        by_drone=out)))


if __name__ == "__main__":
    main()
