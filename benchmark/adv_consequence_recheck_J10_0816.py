# -*- coding: utf-8 -*-
"""
adv_consequence_recheck_J10_0816.py — «R50 이 몇 % 움직이나» 를 방위로 흔들어 본다 (2026-08-16)
==============================================================================================

왜
--
앞 라운드와 이 라운드의 R50 변화(−5 ~ +6.6 %)는 **방위 한 곳(az 0)** 에서 나왔다.
방위를 바꾸면 프롭 플래시의 위상·가림이 달라지므로 그 %가 방위 인공물일 수 있다.
그리고 그 %를 읽을 **자** 도 필요하다 — 저장소 자신의 R50 추정기가 씨앗만 바꿔도
얼마나 흔들리는지(부트스트랩 신뢰구간·다른 씨앗 재실행)를 같이 적는다.

규약: CPU 전용 · 소스 무변경 · 순수 PO. 조각 산출: outputs/_J10_azimuth_r50_0816.json
"""
from __future__ import annotations

import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import adv_consequence_recheck_0816 as R                                   # noqa: E402
from drones import DRONES, build_frame, build_propeller, rotor_layout       # noqa: E402
from rcs_po import mesh_to_points, po_field_dir                             # noqa: E402

AZS = [0.0, 23.0, 45.0, 90.0]
ELS = [-30.0]
KEYS = ["matrice4e", "mini5pro"]


def slowtime_az(spec, law, az_deg, els, n_poses=R.N_POSES):
    """R.slowtime 과 같되 방위를 인자로 받는다."""
    frame = build_frame(spec)
    Pf, Nf, dAf, wf = mesh_to_points(frame, R.SPACING, gamma=R.GAMMA)
    props = {+1: build_propeller(spec, blade_law=law),
             -1: build_propeller(spec, blade_law=law, mirror=True)}
    pts = {d: mesh_to_points(m, R.SPACING, gamma=R.GAMMA) for d, m in props.items()}
    rl = rotor_layout(spec)
    ph, _rpms = R.rotor_phase_table(spec, n_poses)
    out = {}
    for el in els:
        u = R.look_dir(az_deg, el)
        E = po_field_dir(Pf, Nf, dAf, R.FC, u, w=wf)
        Ep = np.zeros(n_poses, complex)
        for i, rot in enumerate(rl):
            Pp, Np_, dAp, wp = pts[1 if rot["dir"] > 0 else -1]
            V = R.rotz_T(u, rot["base_ang"] + ph[:, i])
            Ep += np.exp(1j * 2 * R.K * float(np.dot(rot["center"], u))) \
                * R.po_batch(Pp, Np_, dAp, wp, V)
        out[el] = E + Ep
    return out


def main():
    t0 = time.time()
    rows = {}
    for key in KEYS:
        spec = DRONES[key]
        f_flash = spec.prop_blades * spec.hover_rpm / 60.0
        v_tip = math.pi * (spec.prop_dia_mm / 1000.0) * spec.hover_rpm / 60.0
        per_az = {}
        for az in AZS:
            ser = {law: slowtime_az(spec, law, az, ELS) for law in R.LAWS}
            per_el = {}
            for el in ELS:
                f_tip = 2.0 * v_tip / R.LAM * math.cos(math.radians(el))
                stat = {}
                for law in R.LAWS:
                    E = ser[law][el]
                    n = E.size
                    _band, comb = R.masks_of(n, max(f_tip, 1e-6), f_flash)
                    P = np.abs(np.fft.fft((E - E.mean()) * np.hanning(n))) ** 2
                    sig = 4 * np.pi / R.LAM ** 2 * np.abs(E) ** 2
                    stat[law] = dict(comb=float(P[comb].sum()), sig=float(sig.mean()))
                per_el[f"{el:+.0f}"] = {}
                for law in R.LAWS[1:]:
                    d_comb = 10 * math.log10(stat[law]["comb"] / stat["legacy"]["comb"])
                    d_anch = 10 * math.log10(stat[law]["sig"] / stat["legacy"]["sig"])
                    d_snr = d_comb - d_anch
                    per_el[f"{el:+.0f}"][law] = dict(
                        d_comb_db=round(d_comb, 3), d_anchor_db=round(d_anch, 3),
                        d_snr_db=round(d_snr, 3),
                        d_R50_pct=round(100 * (10 ** (d_snr / 40) - 1), 2))
            per_az[f"{az:.0f}"] = per_el
            print(f"  J10 {key} az{az:.0f} {time.time()-t0:.1f}s", flush=True)
        rows[key] = per_az

    #: 자 — 저장소 자신의 R50 추정기가 얼마나 흔들리나
    boot = json.load(open(os.path.join(ROOT, "outputs",
                                       "detection_curves_attack_bootstrap.json")))["R50_bootstrap"]
    base = json.load(open(os.path.join(ROOT, "outputs", "detection_curves.json")))
    seed777 = json.load(open(os.path.join(ROOT, "outputs",
                                          "detection_curves_attack_seed777.json")))
    def r50(j, arm):
        return next(a["R50_m"]["comb"] for a in j["arms"] if a["arm_id"] == arm)
    ruler = {}
    for arm in ("ours_el-30", "ours_el+0", "ours_el-60"):
        p = boot[arm]["comb"]["R50_point"]
        lo, hi = boot[arm]["comb"]["ci95"]
        ruler[arm] = dict(
            R50_point_m=round(p, 2),
            bootstrap_ci95_pct=[round(100 * (lo / p - 1), 2), round(100 * (hi / p - 1), 2)],
            other_seed_shift_pct=round(100 * (r50(seed777, arm) / r50(base, arm) - 1), 2))
    ruler["engine_gap_R50_pct"] = round(
        100 * (r50(base, "sionna_el-30") / r50(base, "ours_el-30") - 1), 2)

    res = dict(azimuth_sweep=rows, estimator_ruler=ruler, azs=AZS, els=ELS,
               reading_ko="같은 판 교체가 방위마다 R50 을 얼마나 다르게 움직이나, 그리고 "
                          "그 폭이 R50 추정기 자신의 흔들림(부트스트랩 95 % 구간·다른 씨앗) "
                          "보다 큰가.",
               elapsed_s=round(time.time() - t0, 1))
    json.dump(res, open(os.path.join(ROOT, "outputs", "_J10_azimuth_r50_0816.json"),
                        "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1)[:4000])


if __name__ == "__main__":
    main()
