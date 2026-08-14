# -*- coding: utf-8 -*-
"""
test_px4_bridge_smoke.py — 브리지 + 잡음 모듈 **소규모** 스모크 (생산 실행 아님)
================================================================================
펄스 수십 개만 돈다(⚠생산 투입은 PTD 수리 게이트 뒤 — px4_bridge docstring).

  G1 창 로더: grade_2 → 64 펄스, 기하·회전수 유한/합리
  G2 우리 커널 × 선배 메쉬(재질 senior/ours 두 모드): 16 펄스 유한·비영
  G3 우리 커널 × 우리 CAD(matrice4e): 8 펄스 유한·비영
  G4 잡음 모듈: 앵커 눈금·SNR 스케일링(20 m→40 m −12.04 dB)·리듬 몫 널/천장
  G5 탐지 곡선 초안: 합성 이상 로터로 잡음선 교차 R 산출
  G6 (선택) Sionna 팔 2 펄스 — GPU/OptiX 안 되면 SKIP 으로 기록

    CUDA_VISIBLE_DEVICES=0 DRJIT_LIBOPTIX_PATH=... PYTHONPATH=src:benchmark \
        python benchmark/test_px4_bridge_smoke.py
"""
from __future__ import annotations

import json
import os
import sys
import traceback

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

RES = {}


def gate(name):
    def deco(fn):
        def run():
            try:
                out = fn()
                RES[name] = {"pass": True, **(out or {})}
                print(f"  ✅ {name}: {json.dumps(out, ensure_ascii=False, default=str)[:300]}")
            except Exception as e:
                RES[name] = {"pass": False, "error": f"{type(e).__name__}: {e}"}
                print(f"  ❌ {name}: {e}")
                traceback.print_exc()
        return run
    return deco


import px4_bridge as PB                                    # noqa: E402
import rx_noise as RX                                      # noqa: E402

WIN = None


@gate("G1_window")
def g1():
    global WIN
    WIN = PB.load_window(grade=2, n_pulses=64)
    rr = PB.rotor_rates_hz(WIN)
    assert np.isfinite(WIN.R).all() and (WIN.R > 1).all()
    assert np.allclose(np.linalg.norm(WIN.u_body, axis=1), 1.0, atol=1e-9)
    assert all(20 < f < 200 for f in rr["f_rev_hz"]), rr   # 호버 ~75 rev/s (4500rpm)
    return dict(R_m=round(float(WIN.R.mean()), 1), f_rev_hz=rr["f_rev_hz"],
                f_flash_hz=rr["f_flash_hz"])


E_SEN = None


@gate("G2_ours_kernel_senior_mesh")
def g2():
    global E_SEN
    from gpu import pick
    pick(verbose=False)
    sp = PB.SeniorMeshPoser()
    outs = {}
    for mode in ("senior", "ours"):
        r = PB.run_ours(sp, WIN, div=8, mat_mode=mode, blade_mat="nylon",
                        pulses=slice(0, 16), progress_every=0)
        s = r["s"]
        assert np.isfinite(s).all() and np.abs(s).max() > 0
        outs[mode] = round(float(20 * np.log10(np.abs(s).mean())), 2)
        if mode == "senior":
            E_SEN = s
    # 재질 모드가 실제로 달라야 한다(같으면 매핑이 안 붙은 것)
    assert outs["senior"] != outs["ours"], outs
    return dict(level_db=outs, prop_radius_m=round(sp.prop_radius_m, 4))


@gate("G3_ours_kernel_our_cad")
def g3():
    op = PB.OursPoser("matrice4e")
    r = PB.run_ours(op, WIN, div=8, pulses=slice(0, 8), progress_every=0)
    s = r["s"]
    assert np.isfinite(s).all() and np.abs(s).max() > 0
    assert op.n_rotors == 4
    return dict(level_db=round(float(20 * np.log10(np.abs(s).mean())), 2))


@gate("G4_noise_module")
def g4():
    fc, prf = WIN.fc, WIN.prf
    ref = RX.sigma_ref_from_literature(fc, "phantom4")
    E = E_SEN if E_SEN is not None else (np.ones(16) + 0j)
    spec = RX.RxSpec()
    a = RX.rx_series(E, 20.0, fc, prf, spec, ref["sigma_ref_dbsm"], noiseless=True)
    b = RX.rx_series(E, 40.0, fc, prf, spec, ref["sigma_ref_dbsm"], noiseless=True)
    dsnr = a["snr_sample_db"] - b["snr_sample_db"]
    assert abs(dsnr - 40 * np.log10(2)) < 0.05, dsnr       # 1/R⁴ → 12.04 dB
    # 리듬 몫: 이상 로터 ≈100, 백색잡음 ≈ noise_line
    t = np.arange(8192) / prf
    ffl = 126.0
    ideal = np.sum([np.exp(1j * 2 * np.pi * k * ffl * t) for k in range(2, 30)], 0)
    hi = RX.rhythm_share(ideal, prf, ffl)
    nl = RX.noise_line(prf, ffl, n=8192, n_trial=8)
    assert hi > 90.0 and 5.0 < nl["mean_pct"] < 25.0, (hi, nl)
    return dict(sigma_ref_dbsm=round(ref["sigma_ref_dbsm"], 2),
                snr20_db=a["snr_sample_db"], d_snr_20to40_db=round(dsnr, 3),
                ideal_share_pct=round(hi, 1), noise_line=nl)


@gate("G5_detection_curve")
def g5():
    fc, prf = WIN.fc, WIN.prf
    ffl = 126.0
    t = np.arange(4096) / prf
    rng = np.random.default_rng(3)
    # 합성: 이상 로터 빗살 + 임의 위상 — E [m² 눈금은 앵커가 다시 잡으므로 임의]
    E = np.sum([np.exp(1j * (2 * np.pi * k * ffl * t + rng.uniform(0, 2 * np.pi)))
                for k in range(1, 25)], 0) * 1e-3
    ref = RX.sigma_ref_from_literature(fc, "phantom4")
    out = RX.detection_curve(
        E, fc, prf, ffl, spec=RX.RxSpec(eirp_dbm=30.0),
        sigma_ref_dbsm=ref["sigma_ref_dbsm"],
        R_grid=np.geomspace(10, 3000, 13), n_noise=6,
        out_json=os.path.join(os.environ.get("SMOKE_OUT", "/tmp"),
                              "px4_bridge_detection_smoke.json"))
    hit = out["R_hit_m"]
    assert hit["at_noise_mean_plus_2std"] is not None
    return dict(R_hit_m=hit, first=out["rows"][0], last=out["rows"][-1])


@gate("G6_sionna_arm_2pulses")
def g6():
    sp = PB.SeniorMeshPoser()
    # ⚠배관 시험 — 실거리 R≈69 m 는 규칙 예산이 5×10⁸ 라 스모크에 못 태운다.
    #   rng_override_m=15 로 기하를 줄이고 규칙값 (15/3)²×1M=25M 을 쓴다(수치 인용 금지).
    spp = int(round(1e6 * (15.0 / 3.0) ** 2))
    r = PB.run_sionna_window(sp, WIN, spp=spp, pulses=slice(0, 2),
                             rng_override_m=15.0, progress_every=0)
    npaths = [int(x) for x in r["npaths"]]
    assert all(n > 0 for n in npaths), f"경로 0 — spp={spp} 부족 또는 place/OBJ 결함"
    assert np.isfinite(r["s"]).all() and np.abs(r["s"]).max() > 0
    return dict(spp=spp, rng_override_m=15.0,
                E_abs=[float(x) for x in np.abs(r["s"])], npaths=npaths)


@gate("G7_phase_convention_crosscheck")
def g7():
    """우리 커널(선배 메쉬·선배 재질) ↔ 선배 PO 직접 호출 — 같은 96 펄스.

    물리 차이(가림 방식·1/R²·Γ(θ) 각도의존·격자 vs facet)가 있으므로 1.0 은 기대하지
    않는다. 판정: DC 뺀 정규화 복소 상관이 공통 규약(E·e^{−j2kR})에서 conj 대조군보다
    높아야 한다(부호 검산 px4_bridge docstring 의 실측 확인)."""
    sp = PB.SeniorMeshPoser()
    n = 96
    po = PB.run_senior_po(sp, WIN, pulses=slice(0, n))["s"]
    ours = PB.run_ours(sp, WIN, div=8, mat_mode="senior", pulses=slice(0, n),
                       progress_every=0)
    k = 2 * np.pi * WIN.fc / PB.C0
    bulk = np.exp(-1j * 2 * k * WIN.R[:n])
    a = ours["E_raw"] * bulk                        # 공통 규약(=ours["s"])
    b_wrong = np.conj(ours["E_raw"]) * bulk         # 상대위상 부호를 뒤집은 대조군
    po_ac = po - po.mean()

    def corr(u):
        u = u - u.mean()
        return float(np.abs(np.vdot(u, po_ac)) /
                     max(np.linalg.norm(u) * np.linalg.norm(po_ac), 1e-300))
    c_ok, c_flip = corr(a), corr(b_wrong)
    assert c_ok > c_flip, (c_ok, c_flip)
    return dict(corr_common_convention=round(c_ok, 3),
                corr_sign_flipped=round(c_flip, 3))


if __name__ == "__main__":
    print("═══ px4_bridge + rx_noise 스모크 (소규모, 생산 아님) ═══")
    for g in (g1, g2, g3, g4, g5, g6, g7):
        g()
    npass = sum(1 for v in RES.values() if v["pass"])
    print(f"\n게이트 {npass}/{len(RES)} 통과")
    outp = os.path.join(os.environ.get("SMOKE_OUT", "/tmp"),
                        "px4_bridge_smoke.json")
    json.dump(RES, open(outp, "w"), ensure_ascii=False, indent=1, default=str)
    print(f"✅ {outp}")
    sys.exit(0 if npass == len(RES) else 1)
