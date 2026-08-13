# -*- coding: utf-8 -*-
"""
verify_target_rt.py — **표적 에코를 Sionna RT 로 직접 뽑아 PO 예측과 대조**한다.
=================================================================================
문제 제기(정당함): "Sionna 시뮬레이션이 목적인데 표적 RCS·에코를 PO 로 구하면
Sionna 로 검증했다고 할 수 있나?"

그래서 표적 에코 자체를 두 방법으로 각각 계산해 비교한다. 비교량은 **직접파 대비
표적에코의 진폭비**(절대 보정과 무관해 두 엔진을 공정하게 맞댈 수 있는 양):

  · Sionna RT   : 챔버+표적 장면을 광선추적 → 표적 근방을 지나는 경로들의 복소이득 합
                  a_echo 를 직접파 a_dir 로 나눈 값.
  · PO+링크버짓 : 같은 기하에서 바이스태틱 레이더 방정식으로 같은 비를 예측
                  ratio = L·√(σ/4π) / (R1·R2)

■ 실험 구성
  [A] **교정 표적 = 금속구** (σ = πr², 종횡비·바이스태틱각과 무관하게 알려진 값)
      ⚠️ 처음엔 "구는 어떤 각에서도 정반사점이 있으니 RT 에 가장 유리하다"고 봤는데 **정확히 반대**였다.
         SBR+image-method 는 곡면의 정반사점을 못 잡아(디스코볼 문제) 구는 RT 에 **가장 불리한** 표적이다.
         → 판정의 근거는 이 스크립트가 아니라 benchmark/verify_rt_no_rcs.py (docs/VERIFY_RT_VS_PO.md) 다.
  [B] 드론(mavic4pro) — 실제 관심 표적.
  두 표적 모두 spp(표본수)·seed 를 바꿔가며 **수렴성/산포**를 측정한다.
  경로 분류(표적 근방 판정)의 타당성은 **지연 검증**으로 확인한다: 표적 에코라면
  τ_echo ≈ (R1+R2)/c 여야 한다.

실행: CUDA_VISIBLE_DEVICES=2 python benchmark/verify_target_rt.py
"""
from __future__ import annotations
import os, sys, time, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
sys.path.insert(0, HERE)

from bistatic_scene import TX, RX, TGT, bistatic_params, C0        # noqa: E402
from channel import bistatic_rcs_m2                                # noqa: E402

FC = 3.5e9
DRONE = "mavic4pro"
VEL = (-3.0, 1.8, 0.6)
SPHERE_R = 0.30                      # 교정 금속구 반지름 [m] → σ = πr² = 0.2827 m² = −5.49 dBsm
SCRATCH = "/tmp/claude-1015/-workspace/rt_verify"


def analytic_ratio(sigma_m2, p):
    """바이스태틱 레이더방정식의 (표적에코/직접파) 진폭비.
       P_echo/P_dir = σ·L² / (4π·R1²·R2²)  →  진폭비 = L·√(σ/4π)/(R1·R2)"""
    return p["L"] * np.sqrt(sigma_m2 / (4 * np.pi)) / (p["R1"] * p["R2"])


# --------------------------------------------------------------------------- #
#  RT 실행 (표적 = 임의의 Part 목록)
# --------------------------------------------------------------------------- #
def rt_echo(parts, spp, seed, max_depth=3, echo_radius=2.0, with_chamber=False):
    """장면을 광선추적해 (직접파 대비 표적에코 진폭비, 표적경로수, 에코지연, 클러터수) 반환."""
    from scene_build import build_scene, chamber_parts
    from channel import _CMESH
    import mitsuba as mi
    import sionna.rt as rt

    ps = []
    if with_chamber:
        cparts, _ = chamber_parts(_CMESH, cutaway=False)
        ps += cparts
    ps += parts
    scene = build_scene(ps, fc=FC)
    scene.tx_array = rt.PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="V")
    scene.rx_array = rt.PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="V")
    scene.add(rt.Transmitter("tx", position=mi.Point3f(*[float(v) for v in TX])))
    scene.add(rt.Receiver("rx", position=mi.Point3f(*[float(v) for v in RX])))

    paths = rt.PathSolver()(scene, max_depth=max_depth, los=True,
                            specular_reflection=True, diffuse_reflection=True,
                            refraction=False, samples_per_src=int(spp), seed=int(seed))
    from radar_scene import paths_arrays
    a, tau, dop, V, inter = paths_arrays(paths)
    a = np.asarray(a); tau = np.asarray(tau)

    tgtp = np.asarray(TGT, float)
    depth, P = inter.shape
    any_inter = np.zeros(P, bool); near = np.zeros(P, bool)
    for d in range(depth):
        pres = inter[d] != 0
        any_inter |= pres
        near |= pres & (np.linalg.norm(V[d] - tgtp, axis=-1) < echo_radius)
    is_dir, is_echo = ~any_inter, near
    a_dir = complex(np.sum(a[is_dir])) if is_dir.any() else complex(np.sum(a))
    A = abs(a_dir) + 1e-30
    if not is_echo.any():
        return None, 0, None, int((any_inter & ~near).sum())
    a_e = complex(np.sum(a[is_echo]))
    tau_e = float(np.mean(tau[is_echo]))
    return abs(a_e) / A, int(is_echo.sum()), tau_e, int((any_inter & ~near).sum())


def sphere_parts():
    """교정용 금속구 Part (표적 위치에 배치)."""
    from geom import uv_sphere
    os.makedirs(SCRATCH, exist_ok=True)
    m = uv_sphere(SPHERE_R, center=tuple(float(v) for v in TGT), seg=48, rings=24)
    obj = os.path.join(SCRATCH, "sphere.obj")
    m.write_obj(obj)
    from scene_build import Part
    return [Part(name="calib_sphere", obj=obj, mat_key="metal", color=(0.8, 0.8, 0.85))], m


def drone_parts_at_target():
    from channel import _DMESH
    from scene_build import drone_parts
    from drones import DRONES
    dp, mesh = drone_parts(DRONES[DRONE], position=tuple(float(v) for v in TGT),
                           yaw_deg=0.0, mesh_dir=os.path.join(_DMESH, DRONE))
    return dp, mesh


def po_sphere_sigma():
    """같은 구 메쉬에 PO 를 돌려 σ 를 구한다(이론 πr² 와 대조)."""
    from geom import uv_sphere
    from rcs_po import mesh_to_points, rcs_from_points
    m = uv_sphere(SPHERE_R, center=(0, 0, 0), seg=48, rings=24)
    P, N, dA = mesh_to_points(m, (C0 / FC) / 10.0)
    s = rcs_from_points(P, N, dA, FC, np.array([0.0]), 0.0)
    return float(s[0])


def main():
    out = {}
    p = bistatic_params(TX, RX, TGT, VEL, FC)
    tau_expect = (p["R1"] + p["R2"]) / C0
    print("=" * 84)
    print("표적 에코: Sionna RT vs PO — 같은 기하, 같은 양(직접파 대비 진폭비)")
    print("=" * 84)
    print(f"기하: L={p['L']:.2f} m · R1={p['R1']:.2f} m · R2={p['R2']:.2f} m · "
          f"바이스태틱각 β={p['beta']:.1f}°")   # beta 는 이미 도(度) — np.degrees 이중적용 금지
    print(f"표적에코 지연 기대값 τ=(R1+R2)/c = {tau_expect*1e9:.1f} ns\n")

    # ---------- [A] 교정 표적: 금속구 ----------
    sig_th = np.pi * SPHERE_R ** 2
    sig_po = po_sphere_sigma()
    r_th = analytic_ratio(sig_th, p)
    print("-" * 84)
    print(f"[A] 교정 표적 = 금속구 r={SPHERE_R} m")
    print("-" * 84)
    print(f"  이론 σ = πr² = {10*np.log10(sig_th):+.2f} dBsm   ·   PO 계산 σ = {10*np.log10(sig_po):+.2f} dBsm "
          f"(오차 {10*np.log10(sig_po/sig_th):+.2f} dB)")
    print(f"  → 이론 진폭비 = {20*np.log10(r_th):+.2f} dB\n")
    sp, _ = sphere_parts()
    rows_s = []
    for spp in (1_000_000, 4_000_000, 16_000_000):
        for seed in (1, 2):
            t0 = time.time()
            r, npath, tau_e, nclut = rt_echo(sp, spp, seed)
            dt = time.time() - t0
            if r is None:
                print(f"  spp={spp:>10,} seed={seed} → 표적경로 0개 ({dt:.0f}s)")
                rows_s.append(dict(spp=spp, seed=seed, ratio=None))
                continue
            d = 20 * np.log10(r / r_th)
            tag = "OK" if tau_e and abs(tau_e - tau_expect) < 2e-9 else "지연불일치!"
            print(f"  spp={spp:>10,} seed={seed} → RT {20*np.log10(r):+.2f} dB · 이론 대비 {d:+.2f} dB · "
                  f"경로 {npath}개 · τ={tau_e*1e9:.1f} ns [{tag}] ({dt:.0f}s)")
            rows_s.append(dict(spp=spp, seed=seed, ratio=r, dev_db=d, n_paths=npath))
    out["sphere"] = dict(sigma_theory_dbsm=10*np.log10(sig_th), sigma_po_dbsm=10*np.log10(sig_po),
                         ratio_theory_db=20*np.log10(r_th), rows=rows_s)

    # ---------- [B] 드론 ----------
    print("\n" + "-" * 84)
    print(f"[B] 실제 표적 = {DRONE}")
    print("-" * 84)
    sigma = bistatic_rcs_m2(DRONE, FC, p["u1"], p["u2"], az_span_deg=8.0, n_az=5)
    r_po = analytic_ratio(sigma, p)
    print(f"  PO 재질가중 σ(bistatic) = {10*np.log10(sigma):+.2f} dBsm  →  PO 진폭비 = {20*np.log10(r_po):+.2f} dB\n")
    dp, _ = drone_parts_at_target()
    rows_d = []
    for chamber in (False, True):
        for spp in (4_000_000, 16_000_000):
            for seed in (1, 2):
                t0 = time.time()
                r, npath, tau_e, nclut = rt_echo(dp, spp, seed, with_chamber=chamber)
                dt = time.time() - t0
                env = "챔버" if chamber else "자유공간"
                if r is None:
                    print(f"  {env} spp={spp:>10,} seed={seed} → 표적경로 0개 ({dt:.0f}s)")
                    rows_d.append(dict(chamber=chamber, spp=spp, seed=seed, ratio=None))
                    continue
                d = 20 * np.log10(r / r_po)
                tag = "OK" if tau_e and abs(tau_e - tau_expect) < 2e-9 else f"지연 {tau_e*1e9:.0f}ns≠{tau_expect*1e9:.0f}"
                print(f"  {env} spp={spp:>10,} seed={seed} → RT {20*np.log10(r):+.2f} dB · "
                      f"PO 대비 {d:+.2f} dB · 경로 {npath}개 · [{tag}] ({dt:.0f}s)")
                rows_d.append(dict(chamber=chamber, spp=spp, seed=seed, ratio=r, dev_db=d,
                                   n_paths=npath, n_clutter=nclut))
    out["drone"] = dict(sigma_po_dbsm=10*np.log10(sigma), ratio_po_db=20*np.log10(r_po), rows=rows_d)

    # ---------- 판정 ----------
    print("\n" + "=" * 84)
    print("판정")
    print("=" * 84)
    def spread(rows, **f):
        v = [r["dev_db"] for r in rows if r.get("ratio") is not None
             and all(r[k] == vv for k, vv in f.items())]
        return (min(v), max(v), np.mean(v)) if v else (None, None, None)
    lo, hi, mu = spread(rows_s)
    if mu is not None:
        print(f"  [A] 금속구: 이론 대비 평균 {mu:+.2f} dB · 표본/시드 산포 {hi-lo:.2f} dB")
        print("      → RT 가 '정답을 아는 표적'을 얼마나 맞히는지가 RT 표적에코의 신뢰도 상한이다.")
    for ch in (False, True):
        lo, hi, mu = spread(rows_d, chamber=ch)
        if mu is not None:
            print(f"  [B] 드론({'챔버' if ch else '자유공간'}): PO 대비 평균 {mu:+.2f} dB · 산포 {hi-lo:.2f} dB")

    os.makedirs(os.path.join(HERE, "..", "outputs"), exist_ok=True)
    fn = os.path.join(HERE, "..", "outputs", "rt_target_verify.json")
    with open(fn, "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"\n결과 저장: {os.path.relpath(fn)}")


if __name__ == "__main__":
    main()
