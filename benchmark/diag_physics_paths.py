# -*- coding: utf-8 -*-
"""⭐물리 스위치를 **하나씩** 켜서 경로 수가 왜 줄어드는지 가른다.

사용자 물음(2026-08-11): *"물리를 키면 왜 저렇게까지 낮아지니? 경로수가 엄청나게 줄어드네?"*

앙각 스윕에서 `--physics` 는 네 스위치(refraction · diffraction · edge_diffraction ·
max_depth 1→3)를 **한꺼번에** 켠다. 그래서 경로가 9~12 → 5~6 으로 준 원인을 못 짚는다.
여기서는 광선 예산을 고정하고 스위치를 하나씩만 바꿔 **귀속**한다.
"""
import os, sys, json, time
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, f"{ROOT}/src"); sys.path.insert(0, f"{ROOT}/benchmark")
os.environ.setdefault("CUDA_DEVICE_ORDER", "PCI_BUS_ID")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "3")
os.environ.setdefault("SIONNA2_GPU", "3")
from gpu import pick; pick(verbose=False)
import report15_probe as RP
from articulated_fast import FastPoser, rotor_phases
from drones import DRONES, DRONE_GROUP_MAT, drone_colors

FC, RANGE_M, SPP = 3.5e9, 10.0, 11_111_111
EL = float(sys.argv[1]) if len(sys.argv) > 1 else -90.0
NP_ = int(sys.argv[2]) if len(sys.argv) > 2 else 24        # 자세 수(빠르게)
TJ = json.load(open(f"{ROOT}/outputs/report07_three_engines.json"))["_meta"]
spec = DRONES["matrice4e"]; fp = FastPoser(spec); cols = drone_colors(spec)
ph = rotor_phases(np.arange(int(TJ["n"]))/float(TJ["prf_hz"]),
                  np.asarray(TJ["rpm_per_rotor"], float), fp.dirs)
idx = np.linspace(0, int(TJ["n"])-1, NP_).astype(int)

def los(az, el):
    a, e = np.radians(az), np.radians(el)
    return np.array([np.cos(e)*np.cos(a), np.cos(e)*np.sin(a), np.sin(e)])

CASES = [
    ("기준(지금까지의 실행)",  dict(max_depth=1, refraction=False, diffraction=False, edge_diffraction=False)),
    ("굴절만 켬",             dict(max_depth=1, refraction=True,  diffraction=False, edge_diffraction=False)),
    ("회절만 켬",             dict(max_depth=1, refraction=False, diffraction=True,  edge_diffraction=False)),
    ("모서리회절만 켬",        dict(max_depth=1, refraction=False, diffraction=False, edge_diffraction=True)),
    ("다중반사만 (depth 3)",   dict(max_depth=3, refraction=False, diffraction=False, edge_diffraction=False)),
    ("전부 켬 (--physics)",    dict(max_depth=3, refraction=True,  diffraction=True,  edge_diffraction=True)),
]

u = los(float(TJ.get("az_deg", 0.0)), EL)
out = {"_meta": dict(el_deg=EL, n_poses=NP_, spp=SPP, range_m=RANGE_M, fc_hz=FC,
                     question_ko="물리 스위치를 하나씩 켜면 경로 수와 레벨이 어떻게 되나"),
       "cases": {}}
print(f"  el {EL:+.0f}° · {NP_} 자세 · 광선 {SPP:,}\n")
print(f"  {'설정':<24}{'경로 중앙값':>12}{'경로 평균':>11}{'레벨[dB]':>11}{'AC/DC[dB]':>11}{'초/자세':>9}")
for name, kw in CASES:
    E = np.zeros(NP_, complex); npa = np.zeros(NP_, int); t0 = time.time()
    for j, i in enumerate(idx):
        m = fp.pose(ph[int(i)]).to_mesh()
        dd = os.path.join(RP.SCRATCH, f"diag_{os.getpid()}_{j%2}")
        paths_obj = m.write_obj_per_group(dd, spec.key)
        parts = [RP.Part(name=f"{spec.key}_{g}_{j%2}", obj=p,
                         mat_key=DRONE_GROUP_MAT[g][0], color=cols[g])
                 for g, p in paths_obj.items()]
        sc = RP.build_scene(parts, fc=FC)
        RP.place(sc, az=float(TJ.get("az_deg", 0.0)), el=EL, rng=RANGE_M, baseline=0.0)
        p_ = RP.rt.PathSolver()(sc, los=True, specular_reflection=True,
                                diffuse_reflection=True, samples_per_src=SPP,
                                max_num_paths_per_src=RP.MAX_PATHS, seed=1, **kw)
        try:
            aa, tau, _, O = RP.unpack(p_)
        except ValueError:
            aa = np.zeros(0)
        if aa.size:
            hit = (O != RP.NO_OBJ).any(axis=0) if O.size else np.zeros(aa.size, bool)
            E[j] = complex(np.sum(aa[hit]*np.exp(-1j*2*np.pi*FC*tau[hit])))
            npa[j] = int(hit.sum())
        RP.drop_scratch(dd)
    sec = (time.time()-t0)/NP_
    lvl = 20*np.log10(np.abs(E).mean()+1e-300)
    x = E - E.mean()
    ac = 10*np.log10((np.abs(x)**2).mean()/max(abs(E.mean())**2, 1e-300))
    out["cases"][name] = dict(npaths_median=int(np.median(npa)), npaths_mean=float(npa.mean()),
                              level_db=round(float(lvl), 2), ac_over_dc_db=round(float(ac), 2),
                              sec_per_pose=round(sec, 3), **{k: (v if not isinstance(v, bool) else bool(v)) for k, v in kw.items()})
    print(f"  {name:<24}{np.median(npa):12.0f}{npa.mean():11.1f}{lvl:11.2f}{ac:11.2f}{sec:9.2f}")
p = f"{ROOT}/outputs/diag_physics_paths_el{EL:+.0f}.json"
json.dump(out, open(p, "w"), ensure_ascii=False, indent=1)
print(f"\n  → {p}")
