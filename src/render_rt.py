# -*- coding: utf-8 -*-
"""
render_rt.py — (report7) **Sionna RT 자체 렌더러**로 시뮬레이션을 눈으로 보여준다
==================================================================================
지금까지 리포트의 그림은 대부분 matplotlib 도식이었다. 이 모듈은 **Sionna RT 가 실제로
추적한 광선을 Sionna 의 렌더러로 그대로 그린다** — 즉 "우리가 계산한 것"이 아니라
"시뮬레이터가 본 것"이다.

무엇을 그리나
  1. 챔버 외관 / 컷어웨이(clip_at) — 씬 그 자체
  2. **추적된 경로**(paths=) — 직접파 · 바닥 반사 · 벽 다중반사가 3D 광선으로 그려진다
  3. **라디오맵**(radio_map=) — 챔버 안 전파 세기 분포 (바닥이 왜 중요한지 한눈에)
  4. 드론 5종 클로즈업 — 공식 외형에 맞춰 수정된 메쉬
  5. 비행 프레임 — 드론이 날며 경로가 바뀌는 모습

실행:  CUDA_VISIBLE_DEVICES=2 python src/render_rt.py            (전체)
       CUDA_VISIBLE_DEVICES=2 python src/render_rt.py --quick    (빠른 미리보기)
출력:  outputs/renders/rt_*.png

⚠ 표적(드론) 경로는 여기 거의 안 나온다 — **그게 요점이다**. 18 m 떨어진 60 cm 표적은
  입체각이 7e-4 sr 라 광선이 거의 안 맞는다(spp 32M 에서도 경로 0~7개, 시드별 진폭 33 dB 요동).
  그래서 **환경 = RT, 표적 = 거울상 기하 + PO** 하이브리드가 강제된다(docs/VERIFY_RT_VS_PO.md).
"""
from __future__ import annotations

import argparse
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
_BENCH = os.path.abspath(os.path.join(_HERE, "..", "benchmark"))
if _BENCH not in sys.path:
    sys.path.insert(0, _BENCH)

import numpy as np                                    # noqa: E402
from scene_build import build_scene, chamber_parts, drone_parts   # noqa: E402  (CUDA_VISIBLE_DEVICES=2 선점)
import mitsuba as mi                                  # noqa: E402
import sionna.rt as rt                                # noqa: E402
from drones import DRONES                             # noqa: E402
from bistatic_scene import TX, RX, TGT                # noqa: E402

ROOT = os.path.abspath(os.path.join(_HERE, ".."))
OUT = os.path.join(ROOT, "outputs", "renders")
CMESH = os.path.join(ROOT, "assets", "meshes", "chamber")
DMESH = os.path.join(ROOT, "assets", "meshes", "drones")
FC = 3.5e9
W, D, H = 30.0, 20.0, 11.0                            # 챔버 내부 치수


# --------------------------------------------------------------------------- #
def make_scene(drone="mavic4pro", tgt=TGT, with_chamber=True, cutaway=False,
               vel=(-3.0, 0.0, 0.0), fc=FC):
    """챔버(+드론) 씬 + TX/RX. 드론에는 속도를 실어 RT 가 도플러를 계산하게 한다."""
    parts = []
    if with_chamber:
        cparts, _ = chamber_parts(CMESH, cutaway=cutaway)
        parts += cparts
    if drone:
        dp, _ = drone_parts(DRONES[drone], position=tuple(map(float, tgt)), yaw_deg=0.0,
                            mesh_dir=os.path.join(DMESH, drone))
        parts += dp
    scene = build_scene(parts, fc=fc)
    if drone and vel is not None:
        for name, obj in scene.objects.items():
            if name.startswith(drone):
                obj.velocity = mi.Vector3f(*[float(v) for v in vel])
    scene.tx_array = rt.PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="V")
    scene.rx_array = rt.PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="V")
    T = rt.Transmitter("tx", position=mi.Point3f(*[float(v) for v in TX]))
    R = rt.Receiver("rx", position=mi.Point3f(*[float(v) for v in RX]))
    # 기본 마커 반경은 max(0.005·씬, 0.5) = 0.5 m 로 챔버에선 지나치게 크다(경로를 가린다).
    T.display_radius = 0.30
    R.display_radius = 0.30
    scene.add(T); scene.add(R)
    return scene


def cam(pos, look=(W / 2, D / 2, H / 2)):
    return rt.Camera(position=mi.Point3f(*[float(v) for v in pos]),
                     look_at=mi.Point3f(*[float(v) for v in look]))


def shot(scene, name, camera, paths=None, radio_map=None, res=(1280, 900), spp=256,
         clip=None, fov=70.0, **kw):
    p = os.path.join(OUT, f"{name}.png")
    t0 = time.time()
    scene.render_to_file(camera=camera, filename=p, num_samples=spp, resolution=res,
                         paths=paths, radio_map=radio_map, clip_at=clip, fov=fov, **kw)
    print(f"  [render] {os.path.relpath(p, ROOT):48s} ({time.time()-t0:5.1f}s)")
    return p


# --------------------------------------------------------------------------- #
#  ① 씬 그 자체 — 챔버 외관 / 컷어웨이 / 배치
# --------------------------------------------------------------------------- #
#  카메라 프리셋 — 챔버 **안쪽**에서 본다(밖에서 보면 벽에 막힌다).
#  천장은 clip_at 으로 잘라내야 위에서 내려다볼 수 있다(cutaway 는 앞벽만 뗀다).
CLIP_CEIL = 9.0                                        # z=9 m 위를 잘라냄 (천장·상단 흡수체 제거)

#  ※ TX(4,2.5,8)·RX(4,17.5,6.5) 는 **한쪽 벽(x=4)** 에 y 로 15 m 벌어져 있고, 표적은 (21,10,5.5).
#     그래서 'TX·RX·표적을 한 화면에' 담으려면 x 가 큰 쪽에서 -x 방향으로 봐야 한다.
CAMS = {
    "wide":        ((W - 1.0, D / 2, 9.0), (TX[0], D / 2, 5.0)),   # 반대편 벽 상단 → TX·RX·표적 전부
    # ⚠ 2026-07-14 수정: z = TGT[2]+7 = 12.5 m 는 **챔버 천장(11 m) 위**라, clip 없이 쓰면
    #   천장 뒷면만 찍혀 **완전히 빈 그림**이 나온다(report1 에이전트 발견). 9.2 m 로 내린다.
    "over_target": ((TGT[0] + 6, TGT[1] - 9, 9.2), (10.0, D / 2, 5.0)),
    "behind_tx":   ((TX[0] - 3.0, TX[1] - 3.0, TX[2] + 2.0), TGT),
    "grazing":     ((W - 1.5, D / 2, 1.0), (TX[0], D / 2, 1.0)),   # 바닥 스침
    "top":         ((W / 2, D / 2 - 0.01, 26.0), (W / 2, D / 2, 0.0)),
    "side":        ((W / 2, -6.0, 6.0), (W / 2, D / 2, 5.0)),      # y 밖에서 → 바닥반사 삼각형이 보임
}


def render_scene_tour(quick=False):
    print("① 씬 투어 (챔버 + 배치)")
    spp = 64 if quick else 384
    sc_out = make_scene(cutaway=False)
    shot(sc_out, "rt_01_chamber_outside", cam((-26, -22, 18)), spp=spp)
    sc = make_scene(cutaway=True)
    for tag, key in (("02_wide", "wide"), ("03_top", "top"), ("04_over_target", "over_target"),
                     ("05_grazing_floor", "grazing"), ("06_behind_tx", "behind_tx"), ("07_side", "side")):
        clip = CLIP_CEIL if key in ("top", "side") else None
        shot(sc, f"rt_{tag}", cam(*CAMS[key]), spp=spp, clip=clip)


# --------------------------------------------------------------------------- #
#  ② 추적된 경로 — Sionna 가 실제로 찾은 광선
# --------------------------------------------------------------------------- #
def render_paths(quick=False, max_depth=3, spp_rt=2_000_000):
    print("② 추적된 경로 (Sionna 가 그린다)")
    spp = 64 if quick else 384
    sc = make_scene(cutaway=True)
    solver = rt.PathSolver()
    for md, tag in ((0, "los"), (1, "1bounce"), (max_depth, f"{max_depth}bounce")):
        t0 = time.time()
        paths = solver(sc, max_depth=md, los=True, specular_reflection=True,
                       diffuse_reflection=False, refraction=False,
                       samples_per_src=spp_rt, seed=1)
        n = int(np.asarray(paths.tau).size)
        print(f"  depth={md}: 경로 {n}개  ({time.time()-t0:.1f}s)")
        shot(sc, f"rt_10_paths_{tag}_wide", cam(*CAMS["wide"]), paths=paths, spp=spp)
        shot(sc, f"rt_11_paths_{tag}_top", cam(*CAMS["top"]), paths=paths, spp=spp, clip=CLIP_CEIL)
        shot(sc, f"rt_12_paths_{tag}_side", cam(*CAMS["side"]), paths=paths, spp=spp, clip=CLIP_CEIL)


# --------------------------------------------------------------------------- #
#  ③ 라디오맵 — 챔버 안 전파 세기 분포
# --------------------------------------------------------------------------- #
def render_radio_map(quick=False):
    print("③ 라디오맵 (RadioMapSolver)")
    spp = 64 if quick else 384
    n_tx = 200_000 if quick else 3_000_000
    sc = make_scene(cutaway=True)
    rms = rt.RadioMapSolver()
    for z, tag in ((0.05, "floor"), (float(TGT[2]), "droneplane")):
        t0 = time.time()
        rm = rms(sc, center=mi.Point3f(W / 2, D / 2, z),
                 orientation=mi.Point3f(0, 0, 0),
                 size=mi.Point2f(W - 0.5, D - 0.5),
                 cell_size=mi.Point2f(0.25, 0.25),
                 samples_per_tx=n_tx, max_depth=3,
                 specular_reflection=True, diffuse_reflection=False)
        print(f"  z={z:.2f}m 라디오맵 ({time.time()-t0:.1f}s)")
        shot(sc, f"rt_20_radiomap_{tag}", cam(*CAMS["wide"]), radio_map=rm, spp=spp)
        shot(sc, f"rt_21_radiomap_{tag}_top", cam(*CAMS["top"]), radio_map=rm, spp=spp, clip=CLIP_CEIL)


# --------------------------------------------------------------------------- #
#  ④ 드론 5종 클로즈업 — 공식 외형으로 수정된 메쉬
# --------------------------------------------------------------------------- #
def render_drone_gallery(quick=False):
    print("④ 드론 5종 (공식 외형에 맞춘 수정 메쉬)")
    spp = 96 if quick else 512
    import numpy as _np
    from drones import build_drone
    for key in DRONES:
        sc = make_scene(drone=key, tgt=(0.0, 0.0, 0.0), with_chamber=False, vel=None)
        V = _np.asarray(build_drone(DRONES[key]).v, float)       # 실제 메쉬 크기로 프레이밍
        span = float(_np.linalg.norm(V.max(0) - V.min(0)))       # 대각 크기 [m]
        r = span * 1.35                                          # fov 35° 에 꽉 차게
        for tag, p in (("iso", (r * 0.75, -r * 0.62, r * 0.35)),
                       ("side", (0.0, -r, 0.03 * span)),         # 측면 — 높이(수정된 부분)가 보인다
                       ("top", (0.01 * span, 0.0, r))):
            shot(sc, f"rt_30_drone_{key}_{tag}", cam(p, look=(0, 0, 0)),
                 res=(1000, 750), spp=spp, fov=35.0)


# --------------------------------------------------------------------------- #
#  ⑤ 비행 — 드론이 날며 경로가 바뀐다
# --------------------------------------------------------------------------- #
def render_flight(n_frames=24, quick=False):
    print(f"⑤ 비행 프레임 ×{n_frames}")
    spp = 48 if quick else 256
    sys.path.insert(0, _BENCH)
    from geometry import TX as gTX, RX as gRX, CENTER, SPEED, SPAN
    from scenarios import radial
    pos, vel = radial(gTX, gRX, CENTER, speed=SPEED, span=SPAN, n=n_frames)
    solver = rt.PathSolver()
    fdir = os.path.join(OUT, "flight")
    os.makedirs(fdir, exist_ok=True)
    for i, (p, v) in enumerate(zip(pos, vel)):
        sc = make_scene(tgt=tuple(map(float, p)), cutaway=True, vel=tuple(map(float, v)))
        paths = solver(sc, max_depth=2, los=True, specular_reflection=True,
                       diffuse_reflection=False, refraction=False,
                       samples_per_src=500_000, seed=1)
        f = os.path.join(fdir, f"frame_{i:03d}.png")
        sc.render_to_file(camera=cam(*CAMS["wide"]), filename=f, num_samples=spp,
                          resolution=(960, 700), paths=paths, fov=70.0)
        if i % 6 == 0:
            print(f"  frame {i:3d}/{n_frames}")
    make_gif(fdir, os.path.join(OUT, "rt_40_flight.gif"))


def make_gif(frame_dir, gif_path, ms=120):
    """PNG 프레임 → GIF. imageio 가 없어도 되도록 PIL(matplotlib 의존)만 쓴다."""
    from PIL import Image
    files = sorted(f for f in os.listdir(frame_dir) if f.endswith(".png"))
    if not files:
        print("  (프레임 없음)"); return None
    imgs = [Image.open(os.path.join(frame_dir, f)).convert("P", palette=Image.ADAPTIVE)
            for f in files]
    imgs[0].save(gif_path, save_all=True, append_images=imgs[1:], duration=ms, loop=0,
                 optimize=True)
    print(f"  [gif] {os.path.relpath(gif_path, ROOT)}  ({len(imgs)} frames)")
    return gif_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="빠른 미리보기(샘플 수 축소)")
    ap.add_argument("--only", default="scene,paths,radiomap,drones,flight")
    ap.add_argument("--frames", type=int, default=24)
    a = ap.parse_args()
    only = set(a.only.split(","))
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    if "scene" in only:
        render_scene_tour(a.quick)
    if "paths" in only:
        render_paths(a.quick)
    if "radiomap" in only:
        render_radio_map(a.quick)
    if "drones" in only:
        render_drone_gallery(a.quick)
    if "flight" in only:
        render_flight(a.frames, a.quick)
    print(f"\n✅ 렌더 완료 ({time.time()-t0:.0f}s) → {os.path.relpath(OUT, ROOT)}/")


if __name__ == "__main__":
    main()
