# -*- coding: utf-8 -*-
"""
report15_attack_polarization.py — Q2 보강: **교차편파도 켜봤는가**
================================================================================
report15 격자는 TX/RX 를 둘 다 V 단일편파로 놓았다. 회전하는 얇은 블레이드는 교차편파를
만드는 대표적 산란체이므로, "Sionna 에게 가장 유리한 조건" 을 주장하려면 교차편파 채널도
봐야 한다. 여기서 RX 를 이중편파(VH)로 바꿔 **같은 격자**를 돌리고 co/cross 를 나란히 낸다.

⛔ src/drones.py · src/drone_cad.py 읽기만. 신규 산출물 하나만 쓴다.
"""
from __future__ import annotations

import json
import math
import os
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (os.path.join(ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

SCRATCH_BASE = ("/tmp/claude-1015/-workspace/"
                "a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad")
os.environ.setdefault("REPORT15_SCRATCH", os.path.join(SCRATCH_BASE, "r15attackpol"))

import report15_verdict as VD                                          # noqa: E402
import report15_sweep_matrice4e as SW                                  # noqa: E402
import sionna.rt as rt                                                 # noqa: E402
import mitsuba as mi                                                   # noqa: E402
from drones import DRONES, rotor_layout                                # noqa: E402

OUT_JSON = os.path.join(ROOT, "outputs", "report15_attack_polarization.json")
N_PHASE = 64
SPP = 2_048_000_000
SEEDS = (1, 2)
CELLS = [("1/hot", 1.0, 0.0, 0.0), ("1/disc", 1.0, 0.0, 75.0)]


def place_dualpol(scene, az, el, rng, baseline=SW.BASELINE_M):
    """SW.place 와 같은 좌표에 놓되 **RX 를 이중편파(VH)** 로 만든다."""
    u = SW.look_dir(az, el)
    e1, _ = SW.basis_perp(u)
    tx = rng * u + 0.5 * baseline * e1
    rx = rng * u - 0.5 * baseline * e1
    for nm in list(scene.transmitters):
        scene.remove(nm)
    for nm in list(scene.receivers):
        scene.remove(nm)
    scene.tx_array = rt.PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="V")
    scene.rx_array = rt.PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="VH")
    scene.add(rt.Transmitter("tx", position=mi.Point3f(*[float(v) for v in tx])))
    scene.add(rt.Receiver("rx", position=mi.Point3f(*[float(v) for v in rx])))
    return dict(tx=[float(v) for v in tx], rx=[float(v) for v in rx])


def trace_pol(scene, spp, seed, id2grp):
    """co(V) · cross(H) 두 편파의 h 를 한 번의 추적에서 뽑는다."""
    p = rt.PathSolver()(scene, max_depth=1, los=True, specular_reflection=True,
                        diffuse_reflection=True, refraction=False,
                        samples_per_src=int(spp), max_num_paths_per_src=SW.MAX_PATHS,
                        seed=int(seed))
    ar = np.asarray(p.a[0]); ai = np.asarray(p.a[1])
    A = (ar + 1j * ai).reshape(-1, ar.shape[-1])     # [rx·rxant·tx·txant, path]
    P = int(A.shape[-1])
    out = dict(n_rows=int(A.shape[0]), n_paths=P)
    if P == 0 or A.shape[0] < 2:
        out.update(co=0j, cross=0j, co_prop=0j, cross_prop=0j, n_prop=0)
        return out
    tau = np.asarray(p.tau, dtype=np.float64).reshape(-1, P)[0]
    O = np.asarray(p.objects)[:, 0, 0, :]
    hit = (O != SW.NO_OBJ).any(axis=0)
    ph = np.exp(-1j * 2.0 * np.pi * SW.FC * tau)
    pid = np.array([o for o, g in id2grp.items() if g == "prop"], dtype=np.int64)
    pm = np.isin(O, pid).any(axis=0) if pid.size else np.zeros(P, bool)
    out.update(
        co=complex(np.sum(A[0][hit] * ph[hit])), cross=complex(np.sum(A[1][hit] * ph[hit])),
        co_prop=complex(np.sum(A[0][pm] * ph[pm])), cross_prop=complex(np.sum(A[1][pm] * ph[pm])),
        co_inc=float(10 * np.log10(float(np.sum(np.abs(A[0][hit]) ** 2)) + 1e-300)),
        cross_inc=float(10 * np.log10(float(np.sum(np.abs(A[1][hit]) ** 2)) + 1e-300)),
        n_prop=int(pm.sum()), n=int(hit.sum()))
    return out


def run(key) -> dict:
    SW.KEY = key
    SW._SPEC = DRONES[key]
    SW._DIRS = [r["dir"] for r in rotor_layout(SW._SPEC)]
    spec = SW._SPEC
    period = 360.0 / int(spec.prop_blades)
    phis = np.arange(N_PHASE) * (period / N_PHASE)
    Z = {f"{c[0]}|{ch}": np.zeros((N_PHASE, len(SEEDS)), complex)
         for c in CELLS for ch in ("co", "cross", "co_prop", "cross_prop")}
    NP = {c[0]: np.zeros((N_PHASE, len(SEEDS))) for c in CELLS}
    t0 = time.time()
    for i, phd in enumerate(phis):
        scene, dd = SW.build_posed_scene(float(phd), f"P{i:03d}")
        g2 = SW.id_to_group(scene)
        for cname, R, az, el in CELLS:
            place_dualpol(scene, az, el, R)
            for j, sd in enumerate(SEEDS):
                r = trace_pol(scene, SPP, sd, g2)
                for ch in ("co", "cross", "co_prop", "cross_prop"):
                    Z[f"{cname}|{ch}"][i, j] = r[ch]
                NP[cname][i, j] = r["n_prop"]
        SW.drop(dd)
        if i % 16 == 0:
            print(f"   [{key}] {i+1}/{N_PHASE}  {time.time()-t0:.0f}s", flush=True)
    rows = {}
    for cname, R, az, el in CELLS:
        for ch in ("co_prop", "cross_prop", "co", "cross"):
            X = Z[f"{cname}|{ch}"]
            if np.all(X == 0):
                rows[f"{cname}/{ch}"] = dict(empty=True)
                continue
            H = VD.harm_seeded(X)
            E = VD.edge_bin(H)
            zm = X.mean(axis=1)
            rows[f"{cname}/{ch}"] = dict(
                empty=False,
                level_db=float(20 * np.log10(np.abs(X).mean() + 1e-300)),
                modulation_ptp_db=float(np.ptp(20 * np.log10(np.abs(zm) + 1e-300))),
                ac_over_noise_db=H["total_ac_over_noise_db"],
                peak_bin=E["peak_bin"], edge_bin=E["edge_bin"],
                harm_abs=[float(x) for x in H["harm_abs"]],
                z_re=[float(x) for x in zm.real], z_im=[float(x) for x in zm.imag])
        a, b = rows.get(f"{cname}/co_prop"), rows.get(f"{cname}/cross_prop")
        if a and b and not a.get("empty") and not b.get("empty"):
            za = np.asarray(a["z_re"]) + 1j * np.asarray(a["z_im"])
            zb = np.asarray(b["z_re"]) + 1j * np.asarray(b["z_im"])
            rows[f"{cname}/xpol_ratio"] = dict(
                cross_minus_co_level_db=float(b["level_db"] - a["level_db"]),
                cross_minus_co_ptp_db=float(b["modulation_ptp_db"] - a["modulation_ptp_db"]),
                waveform_ac_corr=VD.ac_corr(za, zb),
                cross_ac_over_noise_db=b["ac_over_noise_db"],
                co_ac_over_noise_db=a["ac_over_noise_db"])
    return dict(airframe=key, name=spec.name, n_phase=N_PHASE, seeds=list(SEEDS),
                spp=SPP, seconds=float(time.time() - t0), rows=rows)


def main():
    t0 = time.time()
    J = dict(meta=dict(
        script="benchmark/report15_attack_polarization.py",
        role="Q2 보강 — 교차편파(VH) 채널에서도 블레이드 변조가 보이는가",
        tx_pol="V", rx_pol="VH", n_phase=N_PHASE, spp=SPP, seeds=list(SEEDS),
        cells=[dict(name=c[0], range_m=c[1], az_deg=c[2], el_deg=c[3]) for c in CELLS],
        gpu=os.environ.get("CUDA_VISIBLE_DEVICES", "?"),
        stamp=time.strftime("%Y-%m-%d %H:%M:%S")), airframes={})
    for key in ("matrice4e", "mini2"):
        print(f"\n교차편파 — {key}")
        J["airframes"][key] = run(key)
        with open(OUT_JSON, "w") as f:
            json.dump(J, f, ensure_ascii=False)
    J["meta"]["seconds_total"] = float(time.time() - t0)
    with open(OUT_JSON, "w") as f:
        json.dump(J, f, ensure_ascii=False)
    print(f"\n✅ 저장 → {OUT_JSON}  ({J['meta']['seconds_total']:.0f}s)")


if __name__ == "__main__":
    main()
