# -*- coding: utf-8 -*-
"""
report15_verdict_nulls_vs_range.py — **널 대조군을 거리축으로 넓힌다**
================================================================================

왜 필요한가
  판정 규칙 (c) 는 "구 널대조가 변조를 안 낸다" 이고, 내야 할 그림 1 은
  "스펙트로그램 — Sionna / PO / 구 / 로터제거, **거리별**" 이다.
  기존 outputs/report15_null_control.json 은 **R=3 m 한 거리**뿐이다.
  판정을 R=1·3·10 m 에서 내려면 널도 그 세 거리에 있어야 한다 — 안 그러면
  "R=1 m 의 신호" 를 "R=3 m 의 널" 과 비교하는 셈이 된다.

무엇을 도는가 (전부 Sionna 본 격자와 **같은 위상축**: 한 주기 180° 를 64 등분)
  · full_mini2 / full_matrice4e        신호 (로터 위상 스텝)
  · norotor_mini2                      프롭 제거 → 메쉬 완전 동결 (파이프라인 결정성)
  · disc_mini2                         프롭 → 같은 반경·두께의 **회전대칭 원판** (가장 강한 널)
  · sphere_mini2_plastic               등가부피 구 z 회전
  · sphere_matrice4e_plastic           〃 (matrice4e)

⭐ 메쉬·재질·씬조립·관측량은 report15_null_control.build_arms / report15_probe.rt_echo 를
   **그대로 불러 쓴다**. 정의가 갈라지면 기존 R=3 m 결과와 나란히 놓을 수 없다.

⛔ src/drones.py · src/drone_cad.py 는 읽기만. 신규 파일 하나만 쓴다.
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (os.path.join(ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import report15_null_control as NC                                     # noqa: E402
import report15_probe as P                                             # noqa: E402
from report15_probe import id_to_group, rt_echo                        # noqa: E402
from drones import DRONES, DRONE_GROUP_MAT, drone_colors, pose_articulated  # noqa: E402

RANGES = (1.0, 3.0, 10.0)
AZ, EL = 0.0, 15.0            # Sionna 격자의 'nose' 자세
N_PHASE = 64                  # 한 주기(180°) 64 등분 — Sionna 본 격자와 동일
SEEDS = (1, 2)
SPP = 2_048_000_000           # Sionna 본 격자와 동일 광선예산
ARM_KEYS = ("full_mini2", "norotor_mini2", "disc_mini2",
            "sphere_mini2_plastic", "sphere_matrice4e_plastic")

OUT_JSON = os.path.join(ROOT, "outputs", "report15_verdict_nulls_vs_range.json")
SCRATCH = os.path.join(NC.SCRATCH, "vs_range")


def matrice4e_signal_arm():
    """full_matrice4e — build_arms 에 없으므로 여기서 **같은 규약으로** 만든다
    (sec2_grid.posed_mesh 와 동일: 로터 k 의 스핀 = dir_k·φ)."""
    spec = DRONES["matrice4e"]
    m0 = pose_articulated(spec, rotor_phase_deg=NC.rotor_phase_vector(spec, 0.0))
    matmap = {g: DRONE_GROUP_MAT[g][0] for g in m0.groups()}
    return NC.Arm("full_matrice4e", "matrice4e · 로터 위상 스텝(기준 신호)", "signal", True,
                  lambda phi, s=spec: pose_articulated(
                      s, rotor_phase_deg=NC.rotor_phase_vector(s, float(phi))),
                  matmap, drone_colors(spec))


def run_arm_vs_range(arm, phis, ranges=RANGES, seeds=SEEDS, spp=SPP) -> dict:
    """한 팔을 (거리 × 위상 × 시드) 로 돈다. 위상이 바깥 루프 — 씬 조립이 가장 비싸다."""
    out = {f"{R:g}": dict(range_m=float(R), az_deg=AZ, el_deg=EL,
                          n=[[0] * len(seeds) for _ in range(len(phis))],
                          n_prop=[[0] * len(seeds) for _ in range(len(phis))],
                          hr=[[0.0] * len(seeds) for _ in range(len(phis))],
                          hi=[[0.0] * len(seeds) for _ in range(len(phis))],
                          hpr=[[0.0] * len(seeds) for _ in range(len(phis))],
                          hpi=[[0.0] * len(seeds) for _ in range(len(phis))],
                          incoh=[[None] * len(seeds) for _ in range(len(phis))],
                          spec_n=[None] * len(phis))
           for R in ranges}
    t0 = time.time()
    for i, phd in enumerate(phis):
        m = arm.mesh_at(float(phd))
        scene, dd = NC.scene_from_mesh(m, arm.key, f"V{i:03d}", arm.matmap, arm.colmap)
        g2 = id_to_group(scene, arm.key)
        for R in ranges:
            P.place(scene, az=AZ, el=EL, rng=float(R))
            B = out[f"{R:g}"]
            for j, sd in enumerate(seeds):
                r = rt_echo(scene, spp, seed=sd, diffuse=True, id2grp=g2)
                B["n"][i][j] = int(r["n_paths"]); B["n_prop"][i][j] = int(r["n_prop"])
                B["hr"][i][j] = float(r["h_re"]); B["hi"][i][j] = float(r["h_im"])
                B["hpr"][i][j] = float(r["hp_re"]); B["hpi"][i][j] = float(r["hp_im"])
                B["incoh"][i][j] = (float(r["incoh_db"])
                                    if r["incoh_db"] is not None else None)
            #  ⭐ 정반사 채널이 비어 있다는 주장은 **재도록** 한다(위상당 1회, 시드 1)
            rs = rt_echo(scene, spp, seed=seeds[0], diffuse=False, id2grp=g2)
            B["spec_n"][i] = int(rs["n_paths"])
        NC.drop_scratch(dd)
        if (i + 1) % 8 == 0 or i + 1 == len(phis):
            el_ = time.time() - t0
            print(f"    {arm.key:26s} φ={phd:7.3f}° ({i+1}/{len(phis)})  "
                  f"{el_:6.0f}s (예상 {el_/(i+1)*len(phis):6.0f}s)", flush=True)
    return dict(key=arm.key, label_ko=arm.label_ko, role=arm.role,
                expect_modulation=bool(arm.expect),
                materials=dict(arm.matmap), extra=arm.extra,
                mesh=NC.mesh_metrics(arm.mesh_at(float(phis[0]))),
                phases_deg=[float(x) for x in phis], seeds=[int(s) for s in seeds],
                spp=int(spp), seconds=float(time.time() - t0), by_range=out)


def main():
    t0 = time.time()
    os.makedirs(SCRATCH, exist_ok=True)
    NC.SCRATCH = SCRATCH                      # 기존 널 산출물 폴더를 건드리지 않는다

    phis = np.arange(N_PHASE) * (180.0 / N_PHASE)
    print(f"⭐ 널 대조 거리스윕 — 거리 {RANGES}  자세 az={AZ}/el={EL}  "
          f"위상 {N_PHASE}(한 주기 180°)  시드 {SEEDS}  spp={SPP:,}")

    arms_all, geo = NC.build_arms(keys=("full", "norotor", "disc", "sphere"))
    by_key = {a.key: a for a in arms_all}
    by_key["full_matrice4e"] = matrice4e_signal_arm()
    arms = [by_key[k] for k in ARM_KEYS if k in by_key]
    missing = [k for k in ARM_KEYS if k not in by_key]
    print(f"   팔 {len(arms)}개: {[a.key for a in arms]}" + (f"  ⚠ 누락 {missing}" if missing else ""))
    print(f"   총 추적 ≈ {len(arms)*len(RANGES)*N_PHASE*(len(SEEDS)+1):,}")

    J = dict(meta=dict(
        script="benchmark/report15_verdict_nulls_vs_range.py",
        role="널·신호 대조군을 R=1·3·10 m 로 넓힌다 — 판정 (c) 와 그림 1(거리별)",
        harness="report15_null_control.build_arms + report15_probe.rt_echo (정의 갈라짐 0)",
        observable="h = Σ_p a_p·exp(−j2πf_c·τ_p)",
        fc_hz=P.FC, lambda_m=P.LAM, baseline_m=P.BASELINE_M,
        ranges_m=[float(r) for r in RANGES], az_deg=AZ, el_deg=EL,
        n_phase=N_PHASE, phase_period_deg=180.0,
        phases_deg=[float(x) for x in phis], seeds=list(SEEDS), spp=SPP,
        arm_keys=list(ARM_KEYS), missing_arms=missing,
        related=dict(nulls_at_R3="outputs/report15_null_control.json",
                     sionna_grid_matrice4e="outputs/report15_sionna_sweep_matrice4e.json",
                     sionna_grid_mini2="outputs/report15_verdict_grid_mini2.json"),
        gpu=os.environ.get("CUDA_VISIBLE_DEVICES", "?"),
        stamp=time.strftime("%Y-%m-%d %H:%M:%S")), geometry=geo, arms={})

    def save():
        with open(OUT_JSON, "w") as f:
            json.dump(NC._j(J) if hasattr(NC, "_j") else J, f, ensure_ascii=False,
                      default=float)

    for a in arms:
        print(f"\n▶ {a.key}  ({a.label_ko})")
        J["arms"][a.key] = run_arm_vs_range(a, phis)
        J["meta"]["seconds_so_far"] = float(time.time() - t0)
        save()

    J["meta"]["seconds_total"] = float(time.time() - t0)
    save()
    NC.drop_scratch(SCRATCH)
    print(f"\n✅ 저장 → {OUT_JSON}  ({J['meta']['seconds_total']:.0f}s)")


if __name__ == "__main__":
    main()
