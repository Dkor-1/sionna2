# -*- coding: utf-8 -*-
"""
verify_ground_kernel.py — **우리 커널의 실외(평평한 지면) 갈래가 옳은가**
==========================================================================================
왜 있나
    `rcs_sbr.sbr_field_ground` 는 거울상 법으로 지면 반사를 넣는다. 새 물리를 넣었으니
    ⓐ **기존 것이 안 바뀌었는지** ⓑ **새 것이 이미 있는 2선 모델과 맞는지** 를 기계로 지킨다.

무엇을 지키나
    G1 바이스태틱 평면파 모노 특수화 == `sbr_field` 평면파            (기존 불변량 · 재확인)
    G2 바이스태틱 **구면파** 모노 특수화 == `sbr_field` 구면파        (⭐이번에 넣은 것)
    G3 행로차 항등식 — R_img − R == `two_ray_path_diff` 의 Δ
    G4 ⭐**조합 식** — 세 항이 같을 때 E/E₀ == |1 + Γ·e^{−jkΔ}|² == `two_ray_F`²  (커널과 분리)
    G5 직접 항이 `sbr_field` 와 **비트 동일** — 지면을 넣어도 자유공간 항은 그대로다
    G6 상호성 — ⚠정확히는 성립 못 한다(격자가 û_i 로 깔린다). 이산화를 촘촘히 하면 주는지만 본다
    G7 지면 항이 직접 항 대비 몇 dB 를 더하나 (수만 낸다)

⛔판정 문장을 쓰지 않는다. 통과/실패와 수만 낸다.
실행
    cd /workspace/sionna
    CUDA_VISIBLE_DEVICES="" SIONNA2_ALLOW_CPU=1 PYTHONPATH=src /workspace/.venvs/py312/bin/python benchmark/verify_ground_kernel.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "outputs", "verify_ground_kernel.json")

from freespace_link import fresnel_gamma, two_ray_F, two_ray_path_diff   # noqa: E402
from rcs_sbr import (C0, ground_combine, ground_eps_sigma, sbr_field,  # noqa: E402
                     sbr_field_bistatic, sbr_field_ground)


def los(az, el):
    az, el = np.radians(az), np.radians(el)
    return np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])


def small_sphere_ish(size_m: float, n: int = 6):
    """작은 **정팔면체 껍질** — 점 표적 극한용.

    ⚠평판 하나로는 안 된다. 판은 자기 법선 쪽만 되쏘므로 거울상 방향(û′)으로는 조명·수신
      게이트가 통째로 닫혀 E(û′,û)=0 이 되고, «점 표적이면 세 항이 같다» 는 극한이 성립하지
      않는다. 사방을 보는 닫힌 껍질이라야 방향 쏠림이 작다.
    """
    from geom import Mesh                                          # noqa: PLC0415
    h = size_m / 2.0
    m = Mesh(group="pt")
    idx = [m.add_vertex(*p) for p in
           ((h, 0, 0), (-h, 0, 0), (0, h, 0), (0, -h, 0), (0, 0, h), (0, 0, -h))]
    xp, xm, yp, ym, zp, zm = idx
    for a, b, c in ((xp, yp, zp), (yp, xm, zp), (xm, ym, zp), (ym, xp, zp),
                    (yp, xp, zm), (xm, yp, zm), (ym, xm, zm), (xp, ym, zm)):
        m.add_tri(a, b, c, "pt")
    return m


def main() -> int:
    fc, R, H = 3.5e9, 15.0, 20.0
    lam = C0 / fc
    az, el = 0.0, -30.0
    u = los(az, el)
    res, bad = {}, 0

    def gate(name, ok, **kw):
        nonlocal bad
        res[name] = dict(pass_=bool(ok), **kw)
        if not ok:
            bad += 1
        print(f"  {'✅' if ok else '❌'} {name}  " +
              " · ".join(f"{k}={v}" for k, v in kw.items()))

    # ── G3 행로차 항등식 (메쉬가 필요 없다)
    off = np.array([R * u[0], R * u[1], -2 * H - R * u[2]])
    R_img = float(np.linalg.norm(off))
    dR, psi = two_ray_path_diff(H, H + R * u[2], R * float(np.hypot(u[0], u[1])))
    gate("G3_행로차_항등식", abs((R_img - R) - dR) < 1e-9,
         R_img=round(R_img, 6), R=R, delta_kernel=round(R_img - R, 9),
         delta_helper=round(float(dR), 9), psi_deg=round(float(psi), 4))

    # ── 메쉬가 필요한 게이트
    try:
        from drones import build_drone                              # noqa: PLC0415
        mesh, gm = None, None
    except Exception:                                               # noqa: BLE001
        mesh, gm = None, None
    plate = small_sphere_ish(0.03)                     # λ/3 남짓 껍질 — 방향 쏠림이 작다
    gmp = {"pt": "metal"}
    d = lam / 12.0

    # ── G1 평면파 모노 특수화
    a = sbr_field(plate, gmp, fc, u, spacing=d)
    b = sbr_field_bistatic(plate, gmp, fc, u, u, spacing=d)
    gate("G1_평면파_모노특수화", abs(a - b) <= 1e-12 * max(abs(a), 1e-30),
         rel=float(abs(a - b) / max(abs(a), 1e-30)))

    # ── G2 구면파 모노 특수화 (이번에 넣은 것)
    c = sbr_field(plate, gmp, fc, u, spacing=d, range_m=R)
    e = sbr_field_bistatic(plate, gmp, fc, u, u, spacing=d, range_i=R, range_s=R)
    gate("G2_구면파_모노특수화", abs(c - e) <= 1e-12 * max(abs(c), 1e-30),
         rel=float(abs(c - e) / max(abs(c), 1e-30)))

    # ── G4 ⭐**조합 식** 이 2선 모델과 정확히 같은가 — 커널과 떼어 놓고 시험한다.
    #    세 항이 같으면(점 표적) E/E₀ = (1 + Γe^{−jkΔ})² = F² 여야 한다.
    eps_r, sig = ground_eps_sigma(fc)
    Gam = complex(fresnel_gamma(float(psi), eps_r=eps_r, cond=sig, pol="v", fc=fc))
    E0 = 1.0 + 0.0j
    got = abs(ground_combine(E0, E0, E0, Gam, float(dR), fc, spread_ratio=1.0))
    F = float(two_ray_F(float(psi), float(dR), None, lam,
                        eps_r=eps_r, cond=sig, pol="v"))
    gate("G4_조합식_2선일치", abs(got - F ** 2) <= 1e-12 * max(F ** 2, 1e-30),
         combine=round(got, 12), two_ray_F2=round(F ** 2, 12),
         rel=float(abs(got - F ** 2) / max(F ** 2, 1e-30)),
         gamma_abs=round(abs(Gam), 6))

    # ── G6 상호성 — ⚠**정확히 성립할 수 없다.** 광선 격자가 û_i 로 깔리므로 i·s 를 바꾸면
    #    이산화가 달라진다(`sbr_field_bistatic` 독스트링이 그렇게 적는다). 값을 **재서 적고**,
    #    격자를 촘촘히 할수록 줄어드는지를 함께 본다. 물리가 아니라 이산화의 크기다.
    u_img = off / R_img
    rec = {}
    for div in (12, 24, 48):
        dd = lam / div
        pp = sbr_field_bistatic(plate, gmp, fc, u_img, u, spacing=dd,
                                range_i=R_img, range_s=R)
        qq = sbr_field_bistatic(plate, gmp, fc, u, u_img, spacing=dd,
                                range_i=R, range_s=R_img)
        rec[f"div{div}"] = round(float(abs(pp - qq) / max(abs(pp), 1e-30)), 6)
    shrink = rec["div48"] <= rec["div12"] * 1.05
    gate("G6_상호성_이산화가_줄어드나", shrink, **rec)

    # ── G7 지면 항이 실제로 무언가를 더하나 (드론 메쉬로 한 번)
    Et, T = sbr_field_ground(plate, gmp, fc, u, ground_alt_m=H, range_m=R,
                             spacing=d, return_terms=True)
    ratio_db = 20.0 * np.log10(abs(Et) / max(abs(T["E_dd"]), 1e-30))
    gate("G7_지면항_기여", np.isfinite(ratio_db),
         total_over_direct_db=round(float(ratio_db), 4),
         spread_ratio=round(T["spread_ratio"], 6),
         gamma_abs=round(abs(T["gamma"]), 6), psi_deg=round(T["psi_deg"], 3))

    # ── G5 직접 항이 자유공간과 비트 동일
    gate("G5_직접항_비트동일", T["E_dd"] == c, E_dd=str(T["E_dd"]), sbr_field=str(c))

    doc = {"_meta": {
        "generator": "benchmark/verify_ground_kernel.py",
        "question_ko": "우리 커널의 실외(평평한 지면) 갈래가 기존 것을 안 바꾸고 2선 모델과 맞는가",
        "scope_ko": f"작은 금속 껍질 {0.03} m · {fc/1e9} GHz · 거리 {R} m · 고도 {H} m · 앙각 {el}°",
        "caution_ko": "⛔이 게이트는 «지면 모델이 현실을 맞춘다» 를 말하지 않는다 — "
                      "저장소의 2선 모델과 **자기일치** 한다는 것만 잰다. 실측 대조는 0 건이다.",
    }, "gates": res, "n_fail": bad}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1, default=str)
    print(f"\n{'✅ 전부 통과' if bad == 0 else f'❌ 실패 {bad} 건'} → {OUT}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
