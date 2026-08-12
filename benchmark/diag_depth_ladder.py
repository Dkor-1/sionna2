# -*- coding: utf-8 -*-
"""diag_depth_ladder.py — ⭐`max_depth` 사다리 (1 · 2 · 3 · 4)

■ 사용자 물음 (2026-08-11)
    *"그 max_depth 이거는 2 로도 실험해줄래? 지금 1 이랑 3 만 해본 거지?"*

맞다. `benchmark/diag_physics_paths.py` 는 **1(기준)과 3** 만 쟀다. 2 와 4 가 비어 있어
「무감하다」를 두 점으로만 말하고 있었다. 여기서 네 점으로 채운다.

■ 왜 사다리인가
    두 점은 «같다» 만 말하고 **추세**를 못 말한다. 네 점이면
      · 단조로 조금씩 오르는가(다중반사가 실제로 기여하나)
      · 들쭉날쭉한가(광선 표본 잡음)
      · 어디서 포화하는가
    를 가를 수 있다. ⭐그리고 «2 에서만 튀는» 경우를 잡아낸다 — 이중반사는 오목한
    두 면이 마주 볼 때 생기므로 깊이 2 가 특별한 자리다.

■ 축을 하나만 바꾼다
    굴절·회절·모서리회절은 **전부 끈 채** `max_depth` 만 바꾼다. 광선 예산도 고정한다.
    그래야 차이를 깊이에 귀속할 수 있다.

■ ⚠판정 잣대
    레벨(dB)뿐 아니라 **경로 수**와 **AC/DC**(변조 깊이)도 함께 본다.
    레벨이 같아도 경로 구성이 바뀌면 마이크로도플러가 달라질 수 있다.
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, f"{ROOT}/src")
sys.path.insert(0, f"{ROOT}/benchmark")
os.environ.setdefault("CUDA_DEVICE_ORDER", "PCI_BUS_ID")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "3")
os.environ.setdefault("SIONNA2_GPU", "3")

from gpu import pick                                                  # noqa: E402
pick(verbose=False)
import report15_probe as RP                                           # noqa: E402
from articulated_fast import FastPoser, rotor_phases                  # noqa: E402
from drones import DRONES, DRONE_GROUP_MAT, drone_colors              # noqa: E402

FC, RANGE_M, SPP = 3.5e9, 10.0, 11_111_111
DEPTHS = (1, 2, 3, 4)
EL = float(sys.argv[1]) if len(sys.argv) > 1 else -90.0
NP_ = int(sys.argv[2]) if len(sys.argv) > 2 else 24

TJ = json.load(open(f"{ROOT}/outputs/report07_three_engines.json"))["_meta"]
spec = DRONES["matrice4e"]
fp = FastPoser(spec)
cols = drone_colors(spec)
prf, n_all = float(TJ["prf_hz"]), int(TJ["n"])
az = float(TJ.get("az_deg", 0.0))
ph = rotor_phases(np.arange(n_all) / prf, np.asarray(TJ["rpm_per_rotor"], float), fp.dirs)
idx = np.linspace(0, n_all - 1, NP_).astype(int)


def los(az_deg: float, el_deg: float) -> np.ndarray:
    a, e = np.radians(az_deg), np.radians(el_deg)
    return np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])


u = los(az, EL)
out = {"_meta": dict(
    el_deg=EL, n_poses=NP_, spp=SPP, range_m=RANGE_M, fc_hz=FC, drone="matrice4e",
    depths=list(DEPTHS),
    question_ko="max_depth 를 1·2·3·4 로 올리면 레벨·경로수·변조가 어떻게 되나",
    single_axis_ko=("굴절·회절·모서리회절은 전부 끈 채 max_depth 만 바꾼다. "
                    "광선 예산도 고정한다 — 차이를 깊이에 귀속하기 위해서다."),
), "cases": {}}

print(f"  el {EL:+.0f}° · {NP_} 자세 · 광선 {SPP:,} · 굴절·회절 모두 끔\n")
print(f"  {'max_depth':>10}{'경로 중앙값':>12}{'경로 평균':>11}"
      f"{'레벨[dB]':>11}{'AC/DC[dB]':>11}{'초/자세':>9}")
base = None
for d in DEPTHS:
    E = np.zeros(NP_, complex)
    npa = np.zeros(NP_, int)
    t0 = time.time()
    for j, i in enumerate(idx):
        m = fp.pose(ph[int(i)]).to_mesh()
        dd = os.path.join(RP.SCRATCH, f"depth_{os.getpid()}_{j % 2}")
        paths_obj = m.write_obj_per_group(dd, spec.key)
        parts = [RP.Part(name=f"{spec.key}_{g}_{j % 2}", obj=p,
                         mat_key=DRONE_GROUP_MAT[g][0], color=cols[g])
                 for g, p in paths_obj.items()]
        sc = RP.build_scene(parts, fc=FC)
        RP.place(sc, az=az, el=EL, rng=RANGE_M, baseline=0.0)
        p_ = RP.rt.PathSolver()(
            sc, los=True, specular_reflection=True, diffuse_reflection=True,
            max_depth=d, refraction=False, diffraction=False, edge_diffraction=False,
            samples_per_src=SPP, max_num_paths_per_src=RP.MAX_PATHS, seed=1)
        try:
            aa, tau, _, O = RP.unpack(p_)
        except ValueError:
            aa = np.zeros(0)
        if aa.size:
            hit = (O != RP.NO_OBJ).any(axis=0) if O.size else np.zeros(aa.size, bool)
            E[j] = complex(np.sum(aa[hit] * np.exp(-1j * 2 * np.pi * FC * tau[hit])))
            npa[j] = int(hit.sum())
        RP.drop_scratch(dd)
    sec = (time.time() - t0) / NP_
    lvl = float(20 * np.log10(np.abs(E).mean() + 1e-300))
    x = E - E.mean()
    ac = float(10 * np.log10((np.abs(x) ** 2).mean() / max(abs(E.mean()) ** 2, 1e-300)))
    if base is None:
        base = lvl
    out["cases"][str(d)] = dict(
        max_depth=d, npaths_median=int(np.median(npa)), npaths_mean=float(npa.mean()),
        level_db=round(lvl, 3), ac_over_dc_db=round(ac, 3),
        sec_per_pose=round(sec, 3), delta_vs_depth1_db=round(lvl - base, 3))
    print(f"  {d:>10}{np.median(npa):>12.0f}{npa.mean():>11.1f}"
          f"{lvl:>11.2f}{ac:>11.2f}{sec:>9.2f}")

lv = [out["cases"][str(d)]["level_db"] for d in DEPTHS]
np_ = [out["cases"][str(d)]["npaths_median"] for d in DEPTHS]
out["verdict"] = dict(
    level_ptp_db=round(float(max(lv) - min(lv)), 3),
    npaths_ptp=int(max(np_) - min(np_)),
    monotonic_level=bool(all(b >= a for a, b in zip(lv, lv[1:]))),
    cost_ratio_4_over_1=round(out["cases"]["4"]["sec_per_pose"]
                              / max(out["cases"]["1"]["sec_per_pose"], 1e-9), 3),
    reading_ko=("레벨 폭이 작고 단조가 아니면 «깊이는 무감하고 남은 흔들림은 광선 표본 잡음» "
                "이다. 폭이 크거나 단조로 오르면 다중반사가 실제로 기여한다."),
)
p = f"{ROOT}/outputs/diag_depth_ladder_el{EL:+.0f}.json"
json.dump(out, open(p, "w"), ensure_ascii=False, indent=1)
print(f"\n  레벨 폭 {out['verdict']['level_ptp_db']:.3f} dB · 경로 폭 {out['verdict']['npaths_ptp']}"
      f" · 단조 {out['verdict']['monotonic_level']}"
      f" · 비용 4/1 = {out['verdict']['cost_ratio_4_over_1']:.2f} 배")
print(f"  → {p}")
