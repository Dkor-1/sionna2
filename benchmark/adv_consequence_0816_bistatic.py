# -*- coding: utf-8 -*-
"""
adv_consequence_0816_bistatic.py — 형상 오차의 **바이스태틱** 대가 (2026-08-16 보강)
=====================================================================================

왜 따로인가
-----------
`adv_consequence_0816.py` 의 측정은 전부 **모노스태틱**(후방산란)이다. 그런데 헤드라인
마이크로도플러 팔은 바이스태틱이고(감사 §4-2: f_tip 비로 역산한 β≈81°), 감사 자신이
«바이스태틱에서 형상 민감도가 커진다»(모노 +0.24 dB ↔ β=120° +1.29 dB) 고 적었다.
그래서 «그래서 결과가 바뀌나» 를 모노에서만 재고 끝내면 유리한 각도만 고른 셈이 된다.

무엇을 쓰나 — ⚠**여기서만 커널을 확장한다(선언)**
--------------------------------------------------
`rcs_po.po_field_dir` 는 모노스태틱 전용(위상 exp(j2k P·û))이다. 바이스태틱 스칼라 PO 의
표준형은

    E = Σ [n̂·û_i>0][n̂·û_s>0] |Γ| (n̂·û_i) ΔA · exp(j k P·(û_i+û_s))

이고 û_i=û_s 에서 위 식으로 **정확히 되돌아간다**. 그 회귀를 이 스크립트가 수치로
확인한 뒤(β=0 에서 출하 커널과 상대오차 0)에 쓴다. ⚠이것은 **감사가 C5 에서 쓴 것과 같은
근사**(가림 없음·1차 산란)이고, 절대 σ 앵커로 쓸 물건이 아니다. 두 판의 **비**만 읽는다.

산출: outputs/mesh_adv_refute_consequence_0816.json 의 `H_bistatic` 절에 병합.
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

from adv_consequence_0816 import (GAMMA, FC, LAM, K, SPACING, PRF, AZ_DEG,   # noqa: E402
                                  look_dir, rotz_T, rotor_phase_table,
                                  band_masks, OUT)
from drones import DRONES, build_frame, build_propeller, rotor_layout        # noqa: E402
from rcs_po import mesh_to_points, po_field_dir                              # noqa: E402


def po_field_bistatic(P, N, dA, w, Vi, Vs):
    """바이스태틱 스칼라 PO 장 (방향쌍 배치). Vi=Vs 면 모노스태틱과 같은 식."""
    out = np.empty(len(Vi), complex)
    amp = dA if w is None else dA * w
    chunk = max(1, int(5e5 // max(1, len(dA))))   # 큰 임시배열 회피(공용 머신)
    for s in range(0, len(Vi), chunk):
        a, b = Vi[s:s + chunk], Vs[s:s + chunk]
        NI = N @ a.T
        NS = N @ b.T
        PH = P @ (a + b).T
        g = np.where((NI > 0) & (NS > 0), NI, 0.0)
        out[s:s + chunk] = (g * amp[:, None] * np.exp(1j * K * PH)).sum(axis=0)
    return out


def run(key="matrice4e", el=-30.0, betas=(0.0, 81.0, 120.0), n_poses=2048):
    spec = DRONES[key]
    f_flash = spec.prop_blades * spec.hover_rpm / 60.0
    v_tip = math.pi * (spec.prop_dia_mm / 1000.0) * spec.hover_rpm / 60.0
    rl = rotor_layout(spec)
    ph, _ = rotor_phase_table(spec, n_poses)
    res = {}
    for law in ("legacy", "dji_mini2"):
        frame = build_frame(spec)
        Pf, Nf, dAf, wf = mesh_to_points(frame, SPACING, gamma=GAMMA)
        props = {+1: build_propeller(spec, blade_law=law),
                 -1: build_propeller(spec, blade_law=law, mirror=True)}
        pts = {d: mesh_to_points(m, SPACING, gamma=GAMMA) for d, m in props.items()}
        # β=0 회귀 — 출하 커널과 같은 답인가
        u = look_dir(AZ_DEG, el)
        Pp, Np_, dAp, wp = pts[1]
        ref = po_field_dir(Pp, Np_, dAp, FC, u, w=wp)
        got = po_field_bistatic(Pp, Np_, dAp, wp, u[None, :], u[None, :])[0]
        reg = float(abs(ref - got) / abs(ref))
        res[law] = {"mono_regression_rel_err": reg}
        for b in betas:
            ui = look_dir(AZ_DEG - b / 2.0, el)
            us = look_dir(AZ_DEG + b / 2.0, el)
            Ef = po_field_bistatic(Pf, Nf, dAf, wf, ui[None, :], us[None, :])[0]
            E = np.full(n_poses, Ef, complex)
            for i, rot in enumerate(rl):
                Pp, Np_, dAp, wp = pts[1 if rot["dir"] > 0 else -1]
                th = rot["base_ang"] + ph[:, i]
                Vi, Vs = rotz_T(ui, th), rotz_T(us, th)
                c = np.exp(1j * K * float(np.dot(rot["center"], ui + us)))
                E += c * po_field_bistatic(Pp, Np_, dAp, wp, Vi, Vs)
            # f_tip 은 바이스태틱에서 cos(β/2) 로 줄어든다(원장 규약)
            f_tip = 2.0 * v_tip / LAM * math.cos(math.radians(el)) * math.cos(math.radians(b / 2))
            band, comb = band_masks(n_poses, max(f_tip, 1e-6), f_flash)
            x = (E - E.mean()) * np.hanning(n_poses)
            Pw = np.abs(np.fft.fft(x)) ** 2
            sig = 4 * np.pi / LAM ** 2 * np.abs(E) ** 2
            res[law][f"beta{b:.0f}"] = dict(
                f_tip_hz=round(f_tip, 2),
                sigma_mean_dbsm=round(float(10 * np.log10(sig.mean())), 3),
                comb_energy=float(Pw[comb].sum()),
                ac_power=float((np.abs(E - E.mean()) ** 2).mean()))
            print(f"  {law} β={b:.0f} 끝", flush=True)
    delta = {}
    for b in betas:
        a = res["legacy"][f"beta{b:.0f}"]; c = res["dji_mini2"][f"beta{b:.0f}"]
        d_comb = 10 * math.log10(c["comb_energy"] / a["comb_energy"])
        d_sig = c["sigma_mean_dbsm"] - a["sigma_mean_dbsm"]
        d_ac = 10 * math.log10(c["ac_power"] / a["ac_power"])
        delta[f"beta{b:.0f}"] = dict(
            d_comb_db=round(d_comb, 3), d_sigma_total_db=round(d_sig, 3),
            d_ac_db=round(d_ac, 3),
            d_R50_pct_if_anchor_unchanged=round(100 * (10 ** (d_comb / 40) - 1), 2))
    return dict(airframe=key, el_deg=el, n_poses=n_poses, per_law=res, delta=delta,
                kernel_note_ko="바이스태틱 스칼라 PO(가림 없음). β=0 에서 출하 "
                               "rcs_po.po_field_dir 과 상대오차 "
                               f"{max(res[l]['mono_regression_rel_err'] for l in res):.2e}")


if __name__ == "__main__":
    t0 = time.time()
    out = run()
    payload = json.load(open(OUT))
    payload["H_bistatic"] = out
    payload["_meta"]["bistatic_appended"] = time.strftime("%Y-%m-%d %H:%M:%S")
    json.dump(payload, open(OUT, "w"), ensure_ascii=False, indent=1)
    print(json.dumps(out["delta"], ensure_ascii=False, indent=1))
    print("merged into", OUT, round(time.time() - t0, 1), "s")
