# -*- coding: utf-8 -*-
"""
material_gamma_sweep.py — **gamma_po 실효값이 총 RCS 에 얼마나 실리는가**(영향 한계짓기)
=========================================================================================
`benchmark/material_sources.py --stage derive` 가 만든 박막 유도의 **짝**이다.
유도가 "0.28 은 물리적으로 어디쯤인가"를 답한다면, 이 스크립트는 "그게 틀렸을 때 총 RCS 가
얼마나 움직이나"를 답한다. **선언되고 한계지어진 파라미터는 방어 가능하다.**

세 가지를 낸다:
  [1] 기준(base) 대비 각 그룹 gamma 를 흔들었을 때의 밴드별 mean sigma 변화 [dB]
  [2] note 의 주장 "셸 0.28 ↔ 프롭 0.25 차이는 총 RCS 에 0.03 dB 미만" **직접 검증**
  [3] 그룹별 **고립 기여**(그 그룹만 |Gamma|=1, 나머지 0) — 어느 파라미터가 하중을 지는지

⛔ src/materials.py 를 고치지 않는다. group_mat 에 **float 를 직접 주입**해서 우회한다
   (rcs_sbr 는 문자열이면 materials.gamma_po, float 면 그 값을 |Gamma| 로 그대로 쓴다).

실행: CUDA_VISIBLE_DEVICES=2 PYTHONPATH=src:benchmark python benchmark/material_gamma_sweep.py
"""
from __future__ import annotations

import datetime as _dt
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

from rcs_sbr import rcs_sbr_batch                      # noqa: E402
from drones import DRONES, build_drone, DRONE_GROUP_MAT  # noqa: E402
from material_sources import (BANDS, slab_reflection, proj_weighted_mean_gamma,  # noqa: E402
                              OUT_JSON, _merge_write)

C0 = 299792458.0
EPS_R, SIGMA = 2.7, 0.02

DRONES_USED = ["phantom4", "mavic4pro", "mini5pro"]
N_AZ = 180
EL = 15.0
DIV = 12

_MESH = {}


def mesh_for(d):
    if d not in _MESH:
        _MESH[d] = build_drone(DRONES[d])
    return _MESH[d]


def base_map():
    return {g: mat for g, (mat, _) in DRONE_GROUP_MAT.items()}


PLASTIC_GROUPS = [g for g, (m, _) in DRONE_GROUP_MAT.items() if m == "plastic"]
PROP_GROUPS = [g for g, (m, _) in DRONE_GROUP_MAT.items() if m == "prop_plastic"]
CARBON_GROUPS = [g for g, (m, _) in DRONE_GROUP_MAT.items() if m == "carbon"]
PCB_GROUPS = [g for g, (m, _) in DRONE_GROUP_MAT.items() if m == "pcb"]
CAM_GROUPS = [g for g, (m, _) in DRONE_GROUP_MAT.items() if m == "camera_assembly"]


def run(drone, fc, gm, shell_groups=None):
    lam = C0 / fc
    az = np.linspace(0.0, 360.0, N_AZ, endpoint=False)
    sig = rcs_sbr_batch(mesh_for(drone), gm, fc, az_deg=az, el_deg=EL,
                        spacing=lam / DIV, cache_key=None, shell_groups=shell_groups)
    s = np.atleast_1d(np.asarray(sig, float))
    return dict(mean_dbsm=float(10 * np.log10(np.mean(s))),
                median_dbsm=float(10 * np.log10(np.median(s))),
                p10_dbsm=float(10 * np.log10(np.percentile(s, 10))))


def variants_for(drone, fc):
    """(이름, group_mat) 목록. 물리 박막값은 밴드·기종마다 다르다."""
    import material_sources as MS
    ts = json.load(open(OUT_JSON))["propeller"]["per_drone"][drone]
    bn = [k for k, v in BANDS.items() if abs(v - fc) < 1e3][0]
    g_shell_phys = proj_weighted_mean_gamma(EPS_R, SIGMA, fc, 2.0e-3)["unpol"]
    g_prop_phys = proj_weighted_mean_gamma(EPS_R, SIGMA, fc,
                                           ts["t_chordmean_mm"] * 1e-3)["unpol"]
    g_shell_norm = float(abs(slab_reflection(EPS_R, SIGMA, fc, 2.0e-3, 0.0, "TE")))

    V = [("base", {})]
    for g in (0.10, 0.15, 0.20, 0.244, 0.35, 0.46):
        V.append((f"plastic={g:.3f}", {k: g for k in PLASTIC_GROUPS}))
    for g in (0.10, 0.20, 0.28, 0.35, 0.46):
        V.append((f"prop={g:.3f}", {k: g for k in PROP_GROUPS}))
    for g in (0.80, 0.9887, 0.9938, 1.0):
        V.append((f"carbon={g:.4f}", {k: g for k in CARBON_GROUPS}))
    for g in (0.50, 0.65, 1.0):
        V.append((f"pcb={g:.2f}", {k: g for k in PCB_GROUPS}))
    for g in (0.50, 0.70, 1.0):
        V.append((f"camera={g:.2f}", {k: g for k in CAM_GROUPS}))
    # 물리 박막(밴드·기종 의존) — 셸 2 mm, 프롭 = 우리 CAD 의 시위평균 두께
    V.append(("thinslab_proj", {**{k: g_shell_phys for k in PLASTIC_GROUPS},
                                **{k: g_prop_phys for k in PROP_GROUPS}}))
    V.append(("thinslab_normal", {**{k: g_shell_norm for k in PLASTIC_GROUPS},
                                  **{k: float(abs(slab_reflection(
                                      EPS_R, SIGMA, fc, ts["t_chordmean_mm"] * 1e-3, 0.0, "TE")))
                                     for k in PROP_GROUPS}}))
    meta = dict(band=bn, g_shell_proj=g_shell_phys, g_prop_proj=g_prop_phys,
                g_shell_normal=g_shell_norm, t_prop_chordmean_mm=ts["t_chordmean_mm"])
    return V, meta


def main():
    t0 = time.time()
    res = {}
    for drone in DRONES_USED:
        res[drone] = {}
        for bn, fc in BANDS.items():
            V, meta = variants_for(drone, fc)
            row = dict(_variant_meta=meta)
            for name, ov in V:
                gm = base_map()
                gm.update(ov)
                row[name] = run(drone, fc, gm)
            b = row["base"]["mean_dbsm"]
            for name in list(row):
                if name.startswith("_"):
                    continue
                row[name]["delta_vs_base_db"] = float(row[name]["mean_dbsm"] - b)
            res[drone][bn] = row
            print(f"[{time.time()-t0:7.1f}s] {drone:11s} {bn:14s} base={b:+7.2f} dBsm  "
                  f"thinslab_proj={row['thinslab_proj']['delta_vs_base_db']:+6.3f} dB  "
                  f"prop0.28={row['prop=0.280']['delta_vs_base_db']:+6.3f} dB", flush=True)

    # ⭐ 밴드 루프 결과를 **먼저 저장**한다 (고립 스윕이 죽어도 잃지 않는다).
    _merge_write(dict(impact_sweep=dict(
        _meta=dict(generated=_dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                   generator="benchmark/material_gamma_sweep.py",
                   n_az=N_AZ, el_deg=EL, div=DIV, drones=DRONES_USED,
                   runtime_s=float(time.time() - t0), stage="bands_only",
                   metric="mean_dbsm = 10log10(mean_az(sigma_lin)) — rcs_anchor 규약과 동일",
                   note="기준 대비 delta 만 의미가 있다(격자 절대레벨 불확실도는 공통모드로 상쇄)."),
        by_drone=res)))

    # 그룹 고립 기여 (3.5 GHz 만)
    #  ⚠ 셸(body/canopy)을 |Γ|=1 로 두면 rcs_sbr 의 셸 가드가 (정당하게) 예외를 던진다.
    #    셸을 표적으로 볼 땐 shell_groups=() 로 **투과 경로 자체를 끈다**(어차피 나머지가 0 이라
    #    내부 기여가 없다). 내부 부품을 볼 땐 셸 |Γ|=0 → τ=1 로 **완전 투명**하게 두고 본다.
    iso = {}
    fc = BANDS["5G 3.5 GHz"]
    SHELLS = ("body", "canopy")
    for drone in DRONES_USED:
        mesh = mesh_for(drone)
        groups = sorted(set(np.asarray(mesh.g).tolist()))
        iso[drone] = {}
        for g in groups:
            gm = {k: (1.0 if k == g else 0.0) for k in base_map()}
            sg = () if g in SHELLS else None
            try:
                iso[drone][g] = run(drone, fc, gm, shell_groups=sg)["mean_dbsm"]
            except Exception as e:                       # 죽지 말고 기록하고 넘어간다
                iso[drone][g] = None
                print(f"[iso-FAIL] {drone}/{g}: {e}", flush=True)
        gm_all = {k: 1.0 for k in base_map()}
        iso[drone]["_ALL_PEC"] = run(drone, fc, gm_all, shell_groups=())["mean_dbsm"]
        iso[drone]["_BASE"] = res[drone]["5G 3.5 GHz"]["base"]["mean_dbsm"]
        print(f"[iso] {drone}: " + " ".join(f"{k}={v:+.1f}" for k, v in iso[drone].items()
                                            if v is not None), flush=True)

    # 밴드 기울기 (dB/GHz): base vs thinslab_proj
    slope = {}
    fgh = np.array([BANDS[b] / 1e9 for b in BANDS])
    for drone in DRONES_USED:
        slope[drone] = {}
        for var in ("base", "thinslab_proj", "prop=0.280"):
            y = np.array([res[drone][b][var]["mean_dbsm"] for b in BANDS])
            a, c = np.polyfit(fgh, y, 1)
            slope[drone][var] = dict(slope_db_per_ghz=float(a), intercept_dbsm=float(c))

    out = dict(impact_sweep=dict(
        _meta=dict(generated=_dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                   generator="benchmark/material_gamma_sweep.py",
                   n_az=N_AZ, el_deg=EL, div=DIV, drones=DRONES_USED,
                   runtime_s=float(time.time() - t0), stage="complete",
                   metric="mean_dbsm = 10log10(mean_az(sigma_lin)) — rcs_anchor 규약과 동일",
                   note="기준 대비 delta 만 의미가 있다(격자 절대레벨 불확실도는 공통모드로 상쇄).",
                   isolated_note="고립 기여: 그 그룹만 |Γ|=1, 나머지 0. 셸(body/canopy)이 표적일 "
                                 "땐 shell_groups=() 로 투과경로를 끄고, 내부 부품이 표적일 땐 "
                                 "셸 |Γ|=0(τ=1, 완전 투명)으로 둔다."),
        by_drone=res, isolated_group_dbsm_3p5=iso, band_slope=slope))
    _merge_write(out)


if __name__ == "__main__":
    main()
