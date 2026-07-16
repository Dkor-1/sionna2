# -*- coding: utf-8 -*-
"""
render_anim.py — **Sionna RT 애니메이션(GIF) 대량 생성** — 리포트를 '움직이는 그림'으로
==============================================================================================
정적 렌더(rt_*.png)에 더해, **카메라 오빗 · 드론 회전 · 경로 반사수 증가 · 라디오맵 높이 스캔 ·
감시배열 증설(Rx 1→4)** 을 GIF 로 만든다. 각 리포트가 '무슨 실험인지 눈으로' 보이게.

전부 **Sionna RT 렌더러**(Mitsuba 백엔드)로 실제 광선을 그린다 — 도식이 아니라 시뮬레이터가 본 것.

실행(한 GPU 에 여러 개 동시에 올려 GPU 를 꽉 채운다 — 사용자 방침):
  SIONNA2_GPU=3 python src/render_anim.py --which orbit_chamber
  SIONNA2_GPU=3 python src/render_anim.py --which spin --drone mavic4pro
  SIONNA2_GPU=3 python src/render_anim.py --which paths_build
  SIONNA2_GPU=3 python src/render_anim.py --which radiomap_scan
  SIONNA2_GPU=3 python src/render_anim.py --which rx_array
출력:  outputs/renders/anim/<name>.gif  (+ 프레임은 anim/<name>/frame_*.png)
"""
from __future__ import annotations

import argparse
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_BENCH = os.path.abspath(os.path.join(_HERE, "..", "benchmark"))
for _p in (_HERE, _BENCH):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np                                    # noqa: E402
from render_rt import (make_scene, cam, shot, make_gif, CAMS, CLIP_CEIL,  # noqa: E402
                       OUT, W, D, H, FC)
from bistatic_scene import TX, RX, TGT               # noqa: E402
import mitsuba as mi                                  # noqa: E402
import sionna.rt as rt                                # noqa: E402
from drones import DRONES                             # noqa: E402

ANIM = os.path.join(OUT, "anim")
HIQ_SPP = int(os.environ.get("ANIM_SPP", "256"))      # 프레임당 spp (오래 걸려도 고품질)
HIQ_RES = (int(os.environ.get("ANIM_W", "1280")), int(os.environ.get("ANIM_H", "860")))


def _framedir(name):
    d = os.path.join(ANIM, name)
    os.makedirs(d, exist_ok=True)
    return d


def _render_frames(scene, name, cams, paths_list=None, radio_list=None, clip=None,
                   res=HIQ_RES, spp=HIQ_SPP, fov=70.0, ms=110):
    """cams(=[(pos,look),…]) 마다 1프레임 → GIF. paths_list/radio_list 로 프레임별 오버레이."""
    fdir = _framedir(name)
    t0 = time.time()
    for i, (pos, look) in enumerate(cams):
        p = os.path.join(fdir, f"frame_{i:03d}.png")
        kw = {}
        if paths_list is not None:
            kw["paths"] = paths_list[i]
        if radio_list is not None:
            kw["radio_map"] = radio_list[i]
        scene.render_to_file(camera=cam(pos, look), filename=p, num_samples=spp,
                             resolution=res, clip_at=clip, fov=fov, **kw)
    gif = os.path.join(OUT, "anim", f"{name}.gif")
    make_gif(fdir, gif, ms=ms)
    print(f"  ✅ {name}.gif  ({len(cams)}프레임, {time.time()-t0:.0f}s)")
    return gif


# --------------------------------------------------------------------------- #
#  ① 챔버 오빗 — 카메라가 표적 둘레를 돈다 (report01·09·12)
# --------------------------------------------------------------------------- #
def orbit_chamber(n=48, drone="mavic4pro", radius=13.0, height=8.5, name="orbit_chamber"):
    scene = make_scene(drone=drone, cutaway=True, vel=(-3.0, 0.0, 0.0))
    look = (W / 2, D / 2, 4.5)
    cams = []
    for k in range(n):
        th = 2 * np.pi * k / n
        pos = (W / 2 + radius * np.cos(th), D / 2 + radius * np.sin(th), height)
        cams.append((pos, look))
    return _render_frames(scene, name, cams, clip=CLIP_CEIL, ms=90)


# --------------------------------------------------------------------------- #
#  ② 드론 회전 클로즈업 — 표적을 뱅글 돌려 3D 형상을 보여준다 (report02·03)
# --------------------------------------------------------------------------- #
def spin_drone(drone="mavic4pro", n=36, name=None):
    from drones import build_drone
    name = name or f"spin_{drone}"
    scene = make_scene(drone=drone, tgt=(0.0, 0.0, 0.0), with_chamber=False, vel=None)
    V = np.asarray(build_drone(DRONES[drone]).v, float)
    span = float(np.linalg.norm(V.max(0) - V.min(0)))
    r = span * 1.35
    cams = []
    for k in range(n):
        th = 2 * np.pi * k / n
        pos = (r * 0.8 * np.cos(th), r * 0.8 * np.sin(th), r * 0.42)
        cams.append((pos, (0, 0, 0)))
    return _render_frames(scene, name, cams, res=(1100, 900), fov=32.0, ms=80)


# --------------------------------------------------------------------------- #
#  ③ 경로 반사수 증가 — LoS→1반사→2→3 (Sionna 가 찾은 광선) (report01·07)
# --------------------------------------------------------------------------- #
def paths_build(name="paths_build", spp_rt=1_500_000):
    scene = make_scene(cutaway=True)
    solver = rt.PathSolver()
    cams = [CAMS["wide"]] * 8
    plist = []
    for md in (0, 0, 1, 1, 2, 2, 3, 3):
        paths = solver(scene, max_depth=md, los=True, specular_reflection=True,
                       diffuse_reflection=False, refraction=False,
                       samples_per_src=spp_rt, seed=1)
        plist.append(paths)
    return _render_frames(scene, name, cams, paths_list=plist, ms=350)


# --------------------------------------------------------------------------- #
#  ④ 라디오맵 높이 스캔 — 바닥→표적면 (report01·09)
# --------------------------------------------------------------------------- #
def radiomap_scan(name="radiomap_scan", n=10, n_tx=6_000_000):
    scene = make_scene(cutaway=True)
    rms = rt.RadioMapSolver()
    zs = np.linspace(0.05, H - 1.5, n)
    rlist = []
    for z in zs:
        rm = rms(scene, center=mi.Point3f(W / 2, D / 2, float(z)),
                 orientation=mi.Point3f(0, 0, 0), size=mi.Point2f(W - 0.5, D - 0.5),
                 cell_size=mi.Point2f(0.3, 0.3), samples_per_tx=n_tx, max_depth=3,
                 specular_reflection=True, diffuse_reflection=False)
        rlist.append(rm)
    cams = [CAMS["wide"]] * n
    return _render_frames(scene, name, cams, radio_list=rlist, ms=200)


# --------------------------------------------------------------------------- #
#  ⑤ 감시배열 증설 Rx 1→4 — 수신기가 늘어나는 모습 (report12)
#     (λ/2 간격은 챔버 스케일에서 안 보이므로 시각화용으로 간격을 크게 과장한다)
# --------------------------------------------------------------------------- #
def rx_array(name="rx_array", n_hold=6):
    """RX 소자를 1→4 로 늘리며 각 상태를 여러 프레임 유지 → GIF. 시각적 과장 간격 0.6 m."""
    from render_rt import make_scene as _ms
    fdir = _framedir(name)
    surv_c = np.array([4.0, 17.5, 6.5]); axis = np.array([0.0, 1.0, 0.0])
    frame = 0
    t0 = time.time()
    for N in (1, 2, 3, 4):
        scene = _ms(drone="mavic4pro", cutaway=True, vel=(-3.0, 0.0, 0.0))
        # 추가 RX 마커
        k = np.arange(N) - (N - 1) / 2.0
        for j, kk in enumerate(k):
            pos = surv_c + kk * 0.6 * axis
            R = rt.Receiver(f"rx_s{j}", position=mi.Point3f(*[float(v) for v in pos]))
            R.display_radius = 0.35
            scene.add(R)
        for _ in range(n_hold):
            p = os.path.join(fdir, f"frame_{frame:03d}.png"); frame += 1
            scene.render_to_file(camera=cam(*CAMS["over_target"]), filename=p,
                                 num_samples=HIQ_SPP, resolution=HIQ_RES, clip_at=CLIP_CEIL, fov=70.0)
    gif = os.path.join(OUT, "anim", f"{name}.gif")
    make_gif(fdir, gif, ms=180)
    print(f"  ✅ {name}.gif ({frame}프레임, {time.time()-t0:.0f}s)")
    return gif


WHICH = {
    "orbit_chamber": orbit_chamber,
    "spin": lambda **kw: spin_drone(**{k: v for k, v in kw.items() if k in ("drone", "n", "name")}),
    "paths_build": paths_build,
    "radiomap_scan": radiomap_scan,
    "rx_array": rx_array,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--which", required=True, choices=list(WHICH))
    ap.add_argument("--drone", default="mavic4pro")
    ap.add_argument("--n", type=int, default=None)
    a = ap.parse_args()
    os.makedirs(ANIM, exist_ok=True)
    kw = {}
    if a.which == "spin":
        kw["drone"] = a.drone
    if a.n:
        kw["n"] = a.n
    WHICH[a.which](**kw)


if __name__ == "__main__":
    main()
