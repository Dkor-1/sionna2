# -*- coding: utf-8 -*-
"""
verify_facet_mechanism_probe.py — 본 실험(verify_facet_mechanism.py)이 남긴 두 구멍을 막는다.
==============================================================================================
본 실험 결과:
  [B] 같은 평판을 세분하면 전력이 정확히 20·log10(N) 만큼 뛴다(N=1,2,3 = 경로 개수).
      → '면이 늘어 산란이 커진' 게 아니라 **같은 정반사 경로가 N 번 중복 계수**된 것으로 보인다.
  [C] 구는 어떤 테셀레이션·어떤 반지름(r/R=0.01~4)에서도 경로가 0 이다.

두 경우 모두 **정반사점이 메쉬의 격자점(꼭짓점/모서리)에 정확히 얹혀 있다**는 공통점이 있다
(평판: 중심이 격자 꼭짓점 / 구: θ=180°·φ=90° 가 uv_sphere 의 꼭짓점 자오선·적도).
따라서 위 두 결과가 **일반 현상인지, 대칭 퇴화(degeneracy)의 산물인지** 갈라야 한다.

  [E] 평판을 자기 평면 안에서 셀의 비대칭 분수만큼 밀어 정반사점을 **삼각형 내부**로 보낸다.
      중복이 사라지면 → [B] 는 퇴화 산물. 남으면 → 일반 현상.
  [F] 구를 반 패싯만큼 돌리거나 seg/rings 를 홀수로 잡아 정반사점을 **패싯 내부**로 보낸다.
      경로가 생기면 → [C] 는 퇴화 산물. 여전히 0 이면 → 곡면 자체가 안 잡힌다.
  [G] 중복 경로들의 지연·진폭을 그대로 찍어 '동일 경로의 복사본'인지 확인한다.

실행: SIONNA2_GPU=3 python benchmark/verify_facet_mechanism_probe.py
"""
from __future__ import annotations

import os
import sys
import json
import math

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

os.environ.setdefault("SIONNA2_GPU", "3")
from gpu import pick  # noqa: E402

pick()

import verify_facet_mechanism as V  # noqa: E402  (기하·재질·RT 실행을 그대로 재사용)
from geom import Mesh, uv_sphere  # noqa: E402

OUT = os.path.join(ROOT, "outputs", "facet_mechanism.json")
SEEDS = [1, 2, 3]
SPP = 16_000_000


def plate_offset_mesh(side, k, du=0.0, dv=0.0):
    """평판을 **자기 평면 안에서** (du,dv) 만큼 민다 → 정반사점은 그대로 TGT 근처인데
    격자에 대한 상대 위치만 바뀐다(퇴화 해소용)."""
    m = Mesh(group="plate")
    h = side / 2.0
    idx = [[0] * (k + 1) for _ in range(k + 1)]
    for i in range(k + 1):
        for j in range(k + 1):
            s = -h + side * i / k + du
            t = -h + side * j / k + dv
            idx[i][j] = m.add_vertex(*(V.TGT + s * V.AX + t * V.BX))
    for i in range(k):
        for j in range(k):
            m.add_quad(idx[i][j], idx[i + 1][j], idx[i + 1][j + 1], idx[i][j + 1])
    return m


def rotated_sphere(r, center, seg, rings, yaw_deg=0.0, pitch_deg=0.0):
    """uv_sphere 를 중심 기준으로 돌린다(정반사점을 패싯 내부로 보내기 위함)."""
    m = uv_sphere(r, center=(0.0, 0.0, 0.0), seg=seg, rings=rings)
    cy, sy = math.cos(math.radians(yaw_deg)), math.sin(math.radians(yaw_deg))
    cp, sp = math.cos(math.radians(pitch_deg)), math.sin(math.radians(pitch_deg))
    Rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1.0]])
    Ry = np.array([[cp, 0, sp], [0, 1.0, 0], [-sp, 0, cp]])
    M = Rz @ Ry
    c = np.asarray(center, float)
    m.v = [tuple(map(float, M @ np.array(p) + c)) for p in m.v]
    return m


def main():
    res = json.load(open(OUT))
    res["_probe_meta"] = {
        "why": "B(세분→+20log10(N))·C(구 0경로)가 '대칭 퇴화' 때문인지 일반 현상인지 가른다.",
        "spp": SPP, "max_depth": 1, "seeds": SEEDS,
        "note": "본 실험과 동일한 기하·재질·솔버 설정을 재사용한다.",
    }

    # ---- [E] 정반사점을 삼각형 내부로 밀어 넣기 ------------------------------ #
    print("=== [E] 평판 격자 오프셋(정반사점을 삼각형 내부로) ===")
    E = []
    for side in (1.0, 0.2):
        for k in (1, 2, 4, 8, 16):
            cell_w = side / k
            for tag, (du, dv) in (("aligned", (0.0, 0.0)),
                                  ("offset_037", (0.37 * cell_w, 0.23 * cell_w))):
                m = plate_offset_mesh(side, k, du, dv)
                obj = V.write_obj(m, f"E_{side:g}_k{k}_{tag}")
                c = V.cell(obj, SPP, SEEDS, max_depth=1)
                E.append(dict(side_m=side, k=k, n_tri=len(m.f), offset=tag,
                              du=du, dv=dv, detect_rate=c["detect_rate"],
                              coh_db=c["coh_db"], n_paths_target_set=c["n_paths_target_set"]))
                print(f"  side={side:4.1f} k={k:2d} {tag:11s} n={c['n_paths_target_set']} "
                      f"coh={c['coh_db']}")
    res["E_subdivide_offset"] = E

    # ---- [F] 구의 정반사점을 패싯 내부로 ------------------------------------- #
    print("\n=== [F] 구 퇴화 해소(회전 / 홀수 seg) ===")
    F = []
    for r in (0.5, 5.0, 40.0):
        ctr = (float(V.TGT[0] + r), 0.0, 0.0)
        for tag, (seg, rings, yaw, pitch) in (
                ("even_aligned", (64, 32, 0.0, 0.0)),
                ("even_yaw_half", (64, 32, 360 / 64 / 2, 0.0)),
                ("even_yawpitch", (64, 32, 360 / 64 / 2, 180 / 32 / 2)),
                ("odd_seg", (63, 31, 0.0, 0.0)),
                ("odd_seg_yaw", (63, 31, 1.7, 1.1)),
                ("fine_odd", (255, 127, 1.7, 1.1))):
            m = rotated_sphere(r, ctr, seg, rings, yaw, pitch)
            obj = V.write_obj(m, f"F_{r:g}_{tag}")
            c = V.cell(obj, SPP, SEEDS, max_depth=1)
            F.append(dict(r_m=r, tag=tag, seg=seg, rings=rings, yaw_deg=yaw,
                          pitch_deg=pitch, n_tri=len(m.f),
                          detect_rate=c["detect_rate"], coh_db=c["coh_db"],
                          n_paths_target_set=c["n_paths_target_set"]))
            print(f"  r={r:5.1f} {tag:13s} tri={len(m.f):6d} det={c['detect_rate']:.1f} "
                  f"coh={c['coh_db']}")
    res["F_sphere_degeneracy"] = F

    # ---- [G] 중복 경로의 정체 — 지연·진폭을 그대로 본다 ---------------------- #
    print("\n=== [G] 중복 경로 정체 ===")
    G = []
    import mitsuba as mi
    import sionna.rt as rt
    for gi, (side, k) in enumerate(((1.0, 16), (1.0, 8), (1.0, 1), (0.2, 4), (0.2, 1))):
        obj = V.write_obj(V.plate_mesh(side, k), f"G_{side:g}_k{k}")
        # ⚠ RadioMaterial 은 한 장면에만 붙일 수 있다 → 반복마다 새 이름으로 만든다.
        mat = rt.RadioMaterial(name=f"g_metal_{gi}", relative_permittivity=1.0,
                               conductivity=1e7, scattering_coefficient=0.0)
        scene = rt.load_scene(); scene.frequency = V.FC
        scene.tx_array = rt.PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="V")
        scene.rx_array = rt.PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="V")
        o = rt.SceneObject(fname=obj, name="tgt", radio_material=mat)
        scene.edit(add=[o])
        scene.add(rt.Transmitter("tx", position=mi.Point3f(*[float(v) for v in V.TX])))
        scene.add(rt.Receiver("rx", position=mi.Point3f(*[float(v) for v in V.RX])))
        p = rt.PathSolver()(scene, max_depth=1, los=True, specular_reflection=True,
                            diffuse_reflection=False, refraction=False,
                            samples_per_src=SPP, seed=1)
        ar = np.asarray(p.a[0]); ai = np.asarray(p.a[1])
        a = (ar + 1j * ai).reshape(-1, ar.shape[-1])[0]
        P = a.shape[0]
        tau = np.asarray(p.tau).reshape(-1, P)[0]
        inter = np.asarray(p.interactions)[:, 0, 0, :]
        vert = np.asarray(p.vertices)[:, 0, 0, :, :]
        hit = (inter != 0).any(axis=0)
        rows = []
        for i in np.where(hit)[0]:
            rows.append(dict(amp_db=float(20 * np.log10(abs(a[i]))),
                             phase_deg=float(np.degrees(np.angle(a[i]))),
                             tau_ns=float(tau[i] * 1e9),
                             vertex=[float(x) for x in vert[0, i]]))
        coh = float(20 * np.log10(abs(complex(np.sum(a[hit]))))) if hit.any() else None
        G.append(dict(side_m=side, k=k, n_tri=2 * k * k, n_paths=int(hit.sum()),
                      coh_db=coh,
                      amp_spread_db=(float(np.ptp([rr["amp_db"] for rr in rows]))
                                     if rows else None),
                      tau_spread_ns=(float(np.ptp([rr["tau_ns"] for rr in rows]))
                                     if rows else None),
                      paths=rows))
        del scene, p
        print(f"  side={side} k={k}: n={hit.sum()} coh={coh}")
        for rr in rows:
            print(f"    amp={rr['amp_db']:.4f} dB  ph={rr['phase_deg']:8.3f}  "
                  f"tau={rr['tau_ns']:.6f} ns  v={[round(x,5) for x in rr['vertex']]}")
    res["G_duplicate_paths"] = G

    with open(OUT, "w") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print("\n[saved]", OUT)


if __name__ == "__main__":
    main()
