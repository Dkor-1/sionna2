# -*- coding: utf-8 -*-
"""
report15_attack_diffr_alias.py — **회절을 켠 채널이 64 스텝으로 분해되는가**
================================================================================
공격 실험에서 회절(UTD)을 켜자 확산 채널의 스펙트럼 가장자리가 나이키스트 빈(=32)까지
올라갔다. 그 자체가 "스펙트럼이 f_tip 보다 넓다" 는 뜻일 수도 있고, "64 스텝으로는 그
채널이 안 잡힌다(접힌다)" 는 뜻일 수도 있다. 둘은 완전히 다른 결론이므로 **가른다**.

같은 칸을 위상 128 스텝(회전당 256)으로 돌리고, 그 부분집합인 64 스텝 빗과 비교한다.
  · 64 빗이 128 빗의 앞 32 빈과 같으면 → 접힘 없음. 회절 채널이 정말 넓다.
  · 다르면 → 64 스텝이 부족했던 것이고, 회절 켠 (b) 판정은 격자부터 다시 잡아야 한다.

⛔ src/drones.py · src/drone_cad.py 읽기만. 신규 산출물 하나만.
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

os.environ.setdefault("REPORT15_SCRATCH",
                      "/tmp/claude-1015/-home-yunjung-workspace/"
                      "a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad/r15diffralias")

import report15_verdict as VD                                          # noqa: E402
import report15_attack_physics as AP                                   # noqa: E402
import report15_sweep_matrice4e as SW                                  # noqa: E402
from drones import DRONES, rotor_layout                                # noqa: E402

OUT_JSON = os.path.join(ROOT, "outputs", "report15_attack_diffr_alias.json")
N_HI = 128
SPP = 2_048_000_000
SEEDS = (1, 2)
CFG = dict(diffuse=True, diffr=True, edge=True, refr=False, depth=1)
CELLS = [("1/hot", 1.0, 0.0, 0.0), ("1/disc", 1.0, 0.0, 75.0)]


def run(key) -> dict:
    SW.KEY = key
    SW._SPEC = DRONES[key]
    SW._DIRS = [r["dir"] for r in rotor_layout(SW._SPEC)]
    spec = SW._SPEC
    period = 360.0 / int(spec.prop_blades)
    phis = np.arange(N_HI) * (period / N_HI)
    Z = {c[0]: np.zeros((N_HI, len(SEEDS)), complex) for c in CELLS}
    t0 = time.time()
    for i, phd in enumerate(phis):
        scene, dd = SW.build_posed_scene(float(phd), f"D{i:03d}")
        g2 = SW.id_to_group(scene)
        for cname, R, az, el in CELLS:
            SW.place(scene, az, el, R)
            for j, sd in enumerate(SEEDS):
                r = AP.trace_cfg(scene, CFG, SPP, sd, g2)
                Z[cname][i, j] = complex(r["hpr"], r["hpi"])
        SW.drop(dd)
        if i % 16 == 0:
            print(f"   [{key}] {i+1}/{N_HI}  {time.time()-t0:.0f}s", flush=True)
    ny_hi = N_HI // 2
    ny_lo = N_HI // 4
    out = dict(airframe=key, name=spec.name, seconds=float(time.time() - t0), cells={})
    for cname, R, az, el in CELLS:
        X = Z[cname]
        H_hi = VD.harm_seeded(X)
        H_lo = VD.harm_seeded(X[::2])
        a_hi = np.asarray(H_hi["harm_abs"], float)
        a_lo = np.asarray(H_lo["harm_abs"], float)
        E_hi, E_lo = VD.edge_bin(H_hi), VD.edge_bin(H_lo)
        tot = float(np.sum(a_hi ** 2))
        out["cells"][cname] = dict(
            range_m=R, el_deg=el,
            edge_bin_128=E_hi["edge_bin"], nyquist_bin_128=int(ny_hi),
            edge_bin_64=E_lo["edge_bin"], nyquist_bin_64=int(ny_lo),
            edge_at_nyquist_128=bool(E_hi["edge_bin"] == ny_hi),
            edge_at_nyquist_64=bool(E_lo["edge_bin"] == ny_lo),
            comb_cos_first32=AP.comb_cos(a_lo[:ny_lo], a_hi[:ny_lo]),
            energy_frac_above_bin32=float(np.sum(a_hi[ny_lo:] ** 2) / (tot + 1e-300)),
            ac_over_noise_db_128=H_hi["total_ac_over_noise_db"],
            ac_over_noise_db_64=H_lo["total_ac_over_noise_db"],
            harm_abs_128=[float(x) for x in a_hi],
            harm_abs_64=[float(x) for x in a_lo])
    return out


def main():
    t0 = time.time()
    J = dict(meta=dict(
        script="benchmark/report15_attack_diffr_alias.py",
        role="회절 ON 채널이 위상 64 스텝으로 분해되는지 — 128 스텝과 대조",
        config=dict(CFG), spp=SPP, seeds=list(SEEDS), n_phase_hi=N_HI,
        cells=[dict(name=c[0], range_m=c[1], el_deg=c[3]) for c in CELLS],
        gpu=os.environ.get("CUDA_VISIBLE_DEVICES", "?"),
        stamp=time.strftime("%Y-%m-%d %H:%M:%S")), airframes={})
    for key in ("matrice4e", "mini2"):
        print(f"\n회절 격자 분해 — {key}")
        J["airframes"][key] = run(key)
        with open(OUT_JSON, "w") as f:
            json.dump(AP._f(J), f, ensure_ascii=False)
    J["meta"]["seconds_total"] = float(time.time() - t0)
    with open(OUT_JSON, "w") as f:
        json.dump(AP._f(J), f, ensure_ascii=False)
    print(f"\n✅ 저장 → {OUT_JSON}  ({J['meta']['seconds_total']:.0f}s)")


if __name__ == "__main__":
    main()
