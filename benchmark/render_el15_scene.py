# -*- coding: utf-8 -*-
"""
render_el15_scene.py — ⭐리포트 16 재설계판의 **실험 시나리오를 Sionna 렌더로** 보여준다.

왜
--
사용자 지시: *"16번 레포트에 실험 시나리오도 시오나 렌더링을 토대로 그려줘."*
조각 78 의 «그림 1» 은 지금까지 matplotlib 도식(`ch1_f0_geometry.png`)이었다.
같은 기하를 **실제 씬 렌더**로 내면, 도식이 약속한 배치가 계산이 실제로 본 배치와
같다는 것을 눈으로 확인할 수 있다.

무엇이 달라졌나 — 10 m 판과의 차이
    거리   10 m → **15 m** (2D²/λ = 14.076 m 경계 **밖** = 원거리장)
    자세   4,096 → **8,192** (박자 Δf 4.92 → 2.43 Hz)
    깊이   --physics 에 묶여 있던 max_depth 를 **1 · 2 로 갈라** 귀속 가능하게
    광선   전 조건 **4,000M 발 고정**

⚠ 15 m 는 3 m 판과 달리 드론(대각 0.78 m)과 구면(반경 15 m)의 크기 차가 19 배다.
  한 컷에 둘 다 담으면 드론이 점이 되므로 **세 컷으로 나눈다.**

세 컷
    el15_f0a  전체 기하 — 15 m 구면 위 앙각 7 점에 수신점을 전부 찍는다.
              드론은 작게 보이지만 «어느 자리에서 보는가» 가 한눈에 들어온다.
    el15_f0b  표적 근접 — 레이더가 실제로 보는 드론(기본 el −15°).
    el15_f0c  같은 씬에 PathSolver 경로를 겹친 컷.
              ⚠렌더용 광선 수는 본판(4,000M)이 아니라 **가시화용 1M** 이다 —
                경로 «수» 를 이 그림에서 인용하면 안 된다.

    PYTHONPATH=src:benchmark python benchmark/render_el15_scene.py
"""
from __future__ import annotations

import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from gpu import pick                                                   # noqa: E402
pick(verbose=True)

import mitsuba as mi                                                   # noqa: E402
import numpy as np                                                     # noqa: E402
import sionna.rt as rt                                                 # noqa: E402

import report15_probe as RP                                            # noqa: E402
from drones import DRONES                                              # noqa: E402

FIGDIR = os.path.join(ROOT, "outputs", "figures")

# ⭐재설계판의 규약 — benchmark/elevation_sweep_md.py 와 같은 값이어야 한다
AZ, RNG, BASE = 0.0, 15.0, 0.0
ELS = (0.0, -15.0, -30.0, -45.0, -60.0, -75.0, -90.0)
EL_NEAR = -15.0                      # 근접 컷이 쓰는 앙각

# 렌더 품질 — ⚠render_md_scene 실측: 2560×1600×spp4096 = 34 GB OOM
_RW = int(os.environ.get("EL15_RES_W", "1760"))
_RH = int(os.environ.get("EL15_RES_H", "1100"))
_SPP = int(os.environ.get("EL15_SPP", "512"))


def cam(pos, look, up=None):
    kw = dict(position=mi.Point3f(*[float(v) for v in pos]),
              look_at=mi.Point3f(*[float(v) for v in look]))
    if up is not None:
        kw["orientation"] = None
    return rt.Camera(**kw)


def shot(scene, name, camera, fov=55.0, paths=None):
    p = os.path.join(FIGDIR, f"{name}.png")
    t0 = time.time()
    kw = dict(camera=camera, filename=p, num_samples=_SPP,
              resolution=(_RW, _RH), fov=fov)
    if paths is not None:
        kw["paths"] = paths
    scene.render_to_file(**kw)
    print(f"  ✅ {os.path.relpath(p, ROOT)}  ({time.time()-t0:.1f}s)", flush=True)


def main():
    spec = DRONES["matrice4e"]
    scene, mesh, scratch = RP.build_posed_scene(spec, 0.0, "REN15")

    # ── ① 전체 기하 — 앙각 7 점 전부에 수신점을 찍는다 ──────────────────────
    #   place() 는 tx/rx 를 하나씩만 두므로, 여기서는 직접 7 개를 넣는다.
    for nm in list(scene.transmitters):
        scene.remove(nm)
    for nm in list(scene.receivers):
        scene.remove(nm)
    scene.tx_array = rt.PlanarArray(num_rows=1, num_cols=1, pattern="iso",
                                    polarization="V")
    scene.rx_array = rt.PlanarArray(num_rows=1, num_cols=1, pattern="iso",
                                    polarization="V")
    pos = {}
    for el in ELS:
        u = RP.look_dir(AZ, el)
        p = RNG * np.asarray(u, float)
        pos[el] = p
        r = rt.Receiver(f"el{el:+.0f}", position=mi.Point3f(*[float(v) for v in p]))
        scene.add(r)
        #   ⚠공을 드론(대각 0.78 m)보다 크게 잡으면 «표적이 장치보다 작은» 그림이
        #     되어 비율을 오독하게 된다. 0.30 m 면 드론의 40 % 라 읽힌다.
        scene.get(f"el{el:+.0f}").display_radius = 0.30

    # 카메라 — ⭐드론(원점)과 호(弧)를 **함께** 담는다. 앙각면(az=0)이라 x–z 평면이
    #   호를 이루므로 +y 쪽 정측면에서 보면 사분원으로 보인다.
    arc = np.stack([pos[e] for e in ELS])
    pts = np.vstack([arc, np.zeros(3)])            # 원점(드론)을 프레임에 포함
    lo, hi = pts.min(axis=0), pts.max(axis=0)
    ctr = 0.5 * (lo + hi)
    span = float(np.linalg.norm(hi - lo))
    fov_a = 46.0
    dist = span / (2.0 * np.tan(np.radians(fov_a / 2.0))) * 1.18   # 여백 18 %
    shot(scene, "el15_f0a",
         cam(ctr + np.array([0.16 * dist, dist, 0.10 * dist]), ctr), fov=fov_a)
    print(f"  · 호 span {span:.1f} m · 카메라 거리 {dist:.1f} m · "
          f"수신점 {len(ELS)} 개", flush=True)

    # ── ①-b ⭐앙각 7 점 각각에서 «레이더가 보는 드론» ────────────────────────
    #   이 실험이 바꾸는 축이 바로 이것이다. 나딧로 갈수록 동체가 로터를 덮는
    #   과정이 그림으로 보인다(조각 78 «메쉬를 통째로 넣은 대가» 의 근거).
    for nm in list(scene.receivers):
        scene.remove(nm)
    for el in ELS:
        pl = RP.place(scene, az=AZ, el=el, rng=RNG, baseline=BASE)
        t = np.array(pl["tx"], float)
        for nm in ("tx", "rx"):
            scene.get(nm).display_radius = 0.02
        u = -t / np.linalg.norm(t)                  # 레이더 → 드론
        # 카메라를 «레이더 자리 쪽» 1.1 m 앞에 두고 드론을 본다 = 레이더 시선
        shot(scene, f"el15_view_el{el:+03.0f}",
             cam(-1.1 * u, np.zeros(3)), fov=30.0)

    # ── ② 표적 근접 — 레이더가 보는 드론 ────────────────────────────────────
    for nm in list(scene.receivers):
        scene.remove(nm)
    pl = RP.place(scene, az=AZ, el=EL_NEAR, rng=RNG, baseline=BASE)
    tx = np.array(pl["tx"], float)
    for nm in ("tx", "rx"):
        scene.get(nm).display_radius = 0.05
    u = -tx / np.linalg.norm(tx)                    # 레이더 → 드론 방향
    shot(scene, "el15_f0b",
         cam(-1.1 * u + np.array([0.0, 0.0, 0.10]), np.zeros(3)), fov=30.0)

    # ── ③ 경로 겹침 ─────────────────────────────────────────────────────────
    #   ⚠가시화용 1M 발. 본판은 4,000M 이므로 이 그림의 경로 «수» 는 인용 금지.
    #   ⚠15 m 에서 1M 발은 경로가 **0 개**다(실측) — 규칙값 (R/3)²×1M = 25M 부터
    #     맞기 시작한다. 0 개면 unpack 이 빈 배열로 터지므로 사다리로 올린다.
    paths, spp_used, a, n_hit = None, 0, np.zeros(0), 0
    for spp in (25_000_000, 100_000_000, 400_000_000):
        paths = rt.PathSolver()(scene, max_depth=1, los=True,
                                specular_reflection=True, diffuse_reflection=True,
                                refraction=False, samples_per_src=spp,
                                max_num_paths_per_src=RP.MAX_PATHS, seed=1)
        spp_used = spp
        try:
            a, _, _, O = RP.unpack(paths)
        except ValueError:
            print(f"  · {spp/1e6:.0f}M 발 → 경로 0 개, 올린다", flush=True)
            continue
        n_hit = int(((O != RP.NO_OBJ).any(axis=0)).sum()) if O.size else 0
        if a.size:
            break
        print(f"  · {spp/1e6:.0f}M 발 → 경로 0 개, 올린다", flush=True)
    print(f"  경로 {a.size}개 (표적경유 {n_hit}개) — "
          f"⚠가시화용 {spp_used/1e6:.0f}M 발, 본판(4,000M) 아님 · 원장 아님",
          flush=True)
    mid = 0.5 * (np.zeros(3) + tx)
    shot(scene, "el15_f0c",
         cam(mid + np.array([0.30 * RNG, 0.85 * RNG, 0.20 * RNG]), mid),
         fov=46.0, paths=paths)

    RP.drop_scratch(scratch)
    print("═══ 완료 ═══")


if __name__ == "__main__":
    main()
