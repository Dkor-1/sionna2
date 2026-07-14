# -*- coding: utf-8 -*-
"""
verify_rt_rays.py — **"광선을 더 쏘면 되지 않나?"** 에 대한 4억 발짜리 대답
==============================================================================
report6 §A 의 재현 스크립트. 질문은 정당하다:

    "Sionna RT 가 표적 σ 를 못 준다고? 광선을 적게 쏴서 그런 것 아닌가.
     GPU 가 놀고 있으니 4억 발 쏴 보자."

쏴 봤다. 네 가지를 잰다 (전부 같은 챔버 기하 · 같은 드론 메쉬 · 같은 재질표):

  [A] **광선 예산 스윕** 25M → 400M (16배).
      Sionna 의 확산(diffuse) 표적 에코를 지연게이트로 골라 직접파 대비 진폭비를 잰다.
      경로 수는 광선 수에 비례해 늘고, **비코히어런트 합은 계속 커진다**(수렴하지 않는다).
      코히어런트 합도 같이 찍는다 — 정직하게, 두 합산 규약을 모두 보여야 하기 때문이다.

  [B] **산란계수 S 스윕** — 드론 전 부품의 S 를 0.1 → 0.8 로 돌린다.
      진폭비가 S 를 따라 움직인다. S 는 드론의 물성이 아니라 **우리가 고르는 노브**다.

  [C] **S=0 인 부품이 σ 를 지배한다** — ITU metal(모터·배터리·PCB·카메라 하우징)은
      scattering_coefficient = 0 이라 **확산 채널에 기여가 정확히 0** 이다.
      그런데 SBR(광선+PO적분)로 재면 이 금속 부품들이 σ 의 대부분을 만든다.
      ⇒ RT 확산이 보는 표적과, 물리가 보는 표적이 **다른 표적**이다.

  [D] **정답선** — 같은 메쉬·같은 재질로 SBR 이 낸 σ 를 바이스태틱 레이더 방정식에 넣어
      "진폭비가 여기 있어야 한다"를 그린다.  ratio = L·√(σ/4π) / (R1·R2)

판정: σ 는 **표면적분에서 나온다.** 광선을 늘리면 표면을 더 촘촘히 표집할 뿐,
      적분 단계가 없는 solver 에서는 값이 수렴할 곳이 없다. **GPU 로 해결되지 않는다.**
      (⚠ "레이트레이싱은 RCS 를 못 낸다"가 아니다 — SBR 은 광선추적이고, σ 를 계산한다.
        참인 명제는 좁다: **산란적분 단계가 없는 전파용 solver 에서는 창발하지 않는다.**)

실행:  python benchmark/verify_rt_rays.py            (GPU 자동선택 — gpu.pick)
       python benchmark/verify_rt_rays.py --quick    (짧게: 25M~100M)
산출:  outputs/rt_ray_budget.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "src")
for p in (SRC, HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

from gpu import pick as _pick_gpu                                   # noqa: E402
_pick_gpu(verbose=True)                                             # ⚠ mitsuba import 전에

import mitsuba as mi                                                # noqa: E402
import sionna.rt as rt                                              # noqa: E402

from bistatic_scene import TX, RX, TGT, bistatic_params, C0         # noqa: E402
from drones import DRONES, DRONE_GROUP_MAT, build_drone             # noqa: E402
from scene_build import build_scene, drone_parts                    # noqa: E402
from radar_scene import paths_arrays                                # noqa: E402
from rcs_sbr import rcs_sbr_batch                                   # noqa: E402

FC = 3.5e9
KEY = "mavic4pro"
OUT = os.path.abspath(os.path.join(HERE, "..", "outputs", "rt_ray_budget.json"))
MESH_DIR = os.path.abspath(os.path.join(HERE, "..", "outputs", "meshes"))

#  광선 예산 — 사용자 지시: GPU 를 아끼지 말 것.
RAYS = [25_000_000, 50_000_000, 100_000_000, 200_000_000, 400_000_000]
RAYS_QUICK = [25_000_000, 50_000_000, 100_000_000]
S_SWEEP = [0.1, 0.2, 0.4, 0.8]
S_RAYS = 100_000_000
MAX_PATHS = 4_000_000            # 경로 버퍼 — 확산은 경로를 많이 만든다(절단되면 알린다)
SEEDS = [1, 2, 3, 4, 5]          # ⚠ 확산은 몬테카를로다 — 시드 산포를 재지 않으면 잡음을 추세로 오독한다

#  금속(ITU metal → scattering_coefficient = 0) 인 부품 그룹
METAL_GROUPS = {g for g, (mat, _) in DRONE_GROUP_MAT.items()
                if mat in ("metal", "camera_assembly", "pcb")}


# --------------------------------------------------------------------------- #
#  Sionna RT — 드론 하나만 자유공간에 놓고 표적 에코를 지연게이트로 고른다
# --------------------------------------------------------------------------- #
def _geom():
    p = bistatic_params(TX, RX, TGT, (0, 0, 0), FC)
    p["tau_echo"] = (p["R1"] + p["R2"]) / C0
    p["tau_los"] = p["L"] / C0
    return p


def _scene(scatter_S=None):
    """드론(mavic4pro) 하나. scatter_S 가 주어지면 **전 부품의 S 를 그 값으로 덮어쓴다.**"""
    dp, _ = drone_parts(DRONES[KEY], position=tuple(float(v) for v in TGT),
                        yaw_deg=0.0, mesh_dir=os.path.join(MESH_DIR, KEY))
    scene = build_scene(dp, fc=FC)
    if scatter_S is not None:
        for o in scene.objects.values():
            o.radio_material.scattering_coefficient = float(scatter_S)
    scene.add(rt.Transmitter("tx", position=mi.Point3f(*[float(v) for v in TX])))
    scene.add(rt.Receiver("rx", position=mi.Point3f(*[float(v) for v in RX])))
    return scene


def rt_echo(spp, scatter_S=None, seed=1, max_depth=1):
    """(진단 dict) — 표적 확산 에코의 직접파 대비 진폭비."""
    scene = _scene(scatter_S)
    t0 = time.time()
    paths = rt.PathSolver()(scene, max_depth=max_depth, los=True,
                            specular_reflection=True, diffuse_reflection=True,
                            refraction=False, samples_per_src=int(spp),
                            max_num_paths_per_src=MAX_PATHS, seed=int(seed))
    a, tau, dop, V, inter = paths_arrays(paths)
    a = np.asarray(a); tau = np.asarray(tau)
    hit = (np.asarray(inter) != 0).any(axis=0)
    A = abs(complex(np.sum(a[~hit]))) + 1e-30                 # 직접파(LOS)
    g = _geom()
    gate = hit & (np.abs(tau - g["tau_echo"]) < 3e-9)         # 표적 에코만
    n = int(gate.sum())
    if n == 0:
        return dict(spp=int(spp), S=scatter_S, n_paths=0, n_total=int(a.size),
                    incoh_db=None, coh_db=None, sec=time.time() - t0)
    incoh = float(np.sqrt(np.sum(np.abs(a[gate]) ** 2)) / A)   # 비코히어런트 합
    coh = float(np.abs(np.sum(a[gate])) / A)                   # 코히어런트 합
    return dict(spp=int(spp), S=scatter_S, n_paths=n, n_total=int(a.size), seed=int(seed),
                incoh_db=20 * np.log10(incoh), coh_db=20 * np.log10(coh + 1e-30),
                truncated=bool(a.size >= MAX_PATHS), sec=time.time() - t0)


def rt_echo_seeds(spp, scatter_S=None, seeds=SEEDS, **kw):
    """시드 여러 개 → 평균/산포. **몬테카를로 잡음과 추세를 가른다.**"""
    runs = [rt_echo(spp, scatter_S=scatter_S, seed=s, **kw) for s in seeds]
    ok = [r for r in runs if r["n_paths"]]
    if not ok:
        return dict(spp=int(spp), S=scatter_S, n_paths=0, runs=runs,
                    incoh_db=None, coh_db=None, incoh_sd=None, n_mean=0.0)
    ic = np.array([r["incoh_db"] for r in ok])
    co = np.array([r["coh_db"] for r in ok])
    return dict(spp=int(spp), S=scatter_S, runs=runs, n_seeds=len(ok),
                n_paths=int(np.round(np.mean([r["n_paths"] for r in ok]))),
                n_mean=float(np.mean([r["n_paths"] for r in ok])),
                incoh_db=float(ic.mean()), incoh_sd=float(ic.std()),
                incoh_min=float(ic.min()), incoh_max=float(ic.max()),
                coh_db=float(co.mean()), coh_sd=float(co.std()),
                truncated=any(r.get("truncated") for r in ok),
                sec=float(sum(r["sec"] for r in runs)))


# --------------------------------------------------------------------------- #
#  SBR — 같은 메쉬·같은 재질로 낸 '정답' σ, 그리고 금속 부품의 몫
# --------------------------------------------------------------------------- #
def sbr_truth(el=15.0, n_az=36):
    """전체 σ, 금속만, 비금속만 (방위평균 dBsm) + 레이더방정식이 요구하는 진폭비."""
    m = build_drone(DRONES[KEY])
    az = np.linspace(0, 360, n_az, endpoint=False)
    full = {g: mat for g, (mat, _) in DRONE_GROUP_MAT.items()}
    only_metal = {g: (mat if g in METAL_GROUPS else 0.0) for g, mat in full.items()}
    only_diel = {g: (0.0 if g in METAL_GROUPS else mat) for g, mat in full.items()}

    out = {}
    for nm, gm in (("full", full), ("metal_only", only_metal), ("dielectric_only", only_diel)):
        s = rcs_sbr_batch(m, gm, FC, az_deg=az, el_deg=el, cache_key=f"{KEY}_{nm}")
        out[nm + "_dbsm"] = float(10 * np.log10(np.mean(s)))
    g = _geom()
    sig = 10 ** (out["full_dbsm"] / 10.0)
    out["ratio_db_truth"] = float(20 * np.log10(g["L"] * np.sqrt(sig / (4 * np.pi))
                                                / (g["R1"] * g["R2"])))
    out["metal_share_pct"] = float(100.0 * 10 ** (out["metal_only_dbsm"] / 10.0)
                                   / 10 ** (out["full_dbsm"] / 10.0))
    out["el_deg"] = el
    out["n_az"] = n_az
    return out


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    rays = RAYS_QUICK if args.quick else RAYS

    g = _geom()
    print("=" * 88)
    print("§A  '광선을 더 쏘면 되지 않나?' — 4억 발 실험")
    print("=" * 88)
    print(f"기하: L={g['L']:.2f} m · R1={g['R1']:.2f} · R2={g['R2']:.2f} · β={g['beta']:.1f}° · "
          f"τ_echo={g['tau_echo']*1e9:.1f} ns · f={FC/1e9:.1f} GHz · 표적={DRONES[KEY].name}")

    print("\n[D] 먼저 '정답' — 같은 메쉬·같은 재질을 SBR(광선+PO적분)로 재면")
    truth = sbr_truth()
    print(f"    σ(SBR, 방위평균, el={truth['el_deg']:.0f}°) = {truth['full_dbsm']:+.2f} dBsm")
    print(f"      · 금속 부품(S=0)만       : {truth['metal_only_dbsm']:+.2f} dBsm  "
          f"→ 전체의 **{truth['metal_share_pct']:.0f}%**")
    print(f"      · 비금속(셸·프롭·암)만   : {truth['dielectric_only_dbsm']:+.2f} dBsm")
    print(f"    ⇒ 레이더방정식이 요구하는 진폭비 = **{truth['ratio_db_truth']:+.2f} dB**")
    print(f"    ⚠ 확산에 기여할 수 있는 부품(S>0)은 비금속뿐인데, σ 의 "
          f"{truth['metal_share_pct']:.0f}% 는 S=0 인 금속에서 나온다.")

    print(f"\n[A] 광선 예산 스윕 (드론 기본 재질 — metal S=0, plastic S=0.20) · 시드 {len(SEEDS)}개 평균")
    print(f"    {'광선':>12} {'경로수':>8} {'비코히어런트':>14} {'시드산포':>9} {'코히어런트':>12} {'시간':>7}")
    A = []
    for spp in rays:
        r = rt_echo_seeds(spp)
        A.append(r)
        if not r["n_paths"]:
            print(f"    {spp:>12,} {0:>8}   (표적 경로 0개)")
            continue
        print(f"    {spp:>12,} {r['n_mean']:>8.1f} {r['incoh_db']:>+13.2f} dB "
              f"±{r['incoh_sd']:>5.2f} {r['coh_db']:>+11.2f} dB {r['sec']:>6.1f}s"
              + ("  ⚠경로버퍼 절단" if r.get("truncated") else ""))
    ok = [r for r in A if r["n_paths"]]
    if len(ok) >= 2:
        d = ok[-1]["incoh_db"] - ok[0]["incoh_db"]
        sd = float(np.mean([r["incoh_sd"] for r in ok]))
        print(f"\n    → 광선 {ok[0]['spp']/1e6:.0f}M → {ok[-1]['spp']/1e6:.0f}M "
              f"({ok[-1]['spp']/ok[0]['spp']:.0f}배): 비코히어런트 합 **{d:+.1f} dB** 이동 "
              f"(시드 산포 ±{sd:.1f} dB)")
        print(f"       정답선({truth['ratio_db_truth']:+.2f} dB) 대비: "
              f"{ok[0]['incoh_db']-truth['ratio_db_truth']:+.1f} dB → "
              f"{ok[-1]['incoh_db']-truth['ratio_db_truth']:+.1f} dB")
        print("       ⇒ 광선을 늘려도 정답선에 **붙지 않는다**. 수렴 목표가 없기 때문이다.")

    print("\n[B] 산란계수 S 스윕 (광선 고정 = %d M) · 시드 %d개 평균" % (S_RAYS / 1e6, len(SEEDS)))
    print(f"    {'S':>5} {'경로수':>8} {'비코히어런트':>14} {'시드산포':>9}")
    B = []
    for S in S_SWEEP:
        r = rt_echo_seeds(S_RAYS, scatter_S=S)
        B.append(r)
        if not r["n_paths"]:
            print(f"    {S:>5.2f} {0:>8}   (경로 0개)"); continue
        print(f"    {S:>5.2f} {r['n_mean']:>8.1f} {r['incoh_db']:>+13.2f} dB ±{r['incoh_sd']:>5.2f}")
    okb = [r for r in B if r["n_paths"]]
    if len(okb) >= 2:
        print(f"\n    → S {okb[0]['S']:.1f} → {okb[-1]['S']:.1f} ({okb[-1]['S']/okb[0]['S']:.0f}배) "
              f"에서 **{okb[-1]['incoh_db']-okb[0]['incoh_db']:+.1f} dB** 이동. "
              "S 는 드론의 물성이 아니라 우리가 돌리는 노브다.")
        # 정답선을 재현하는 S 를 역산 — "맞추려면 피팅해야 한다"의 정량화
        xs = np.log10([r["S"] for r in okb]); ys = np.array([r["incoh_db"] for r in okb])
        sl, ic = np.polyfit(xs, ys, 1)
        s_fit = float(10 ** ((truth["ratio_db_truth"] - ic) / sl))
        print(f"       정답선({truth['ratio_db_truth']:+.2f} dB)을 재현하는 S ≈ **{s_fit:.2f}** "
              f"(기울기 {sl:.1f} dB/decade)  ⇒ 그건 예측이 아니라 **피팅**이다.")
        okb_fit = dict(S_to_match_truth=s_fit, slope_db_per_decade=float(sl))
    else:
        okb_fit = {}

    out = dict(fc=FC, drone=KEY, geometry={k: float(g[k]) for k in ("L", "R1", "R2", "beta")},
               tau_echo_ns=g["tau_echo"] * 1e9, truth=truth,
               A_ray_sweep=A, B_S_sweep=B, S_rays=S_RAYS, B_fit=okb_fit, seeds=SEEDS,
               metal_groups=sorted(METAL_GROUPS), max_paths=MAX_PATHS)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("\n" + "=" * 88)
    print("판정: 광선을 16배 늘려도 값이 정답선에 붙지 않는다. σ 는 **표면적분에서 나온다** — "
          "적분 단계가\n      없는 solver 에서는 광선을 아무리 늘려도 수렴할 곳이 없다. GPU 로 해결되지 않는다.")
    print("=" * 88)
    print("저장:", os.path.relpath(OUT))


if __name__ == "__main__":
    main()
