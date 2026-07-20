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
    """프레임 디렉토리를 만들되 **옛 frame_*.png 를 먼저 지운다**. 이전엔 안 지워서, 프레임 수가
    줄면(예: 72→48) 남은 옛 프레임이 새 GIF 에 섞여 표적이 순간이동하는 아티팩트가 있었다
    (적대적 감사 발견). make_gif 가 디렉토리의 모든 png 를 읽으므로 반드시 청소해야 한다."""
    import glob as _glob
    d = os.path.join(ANIM, name)
    os.makedirs(d, exist_ok=True)
    for _f in _glob.glob(os.path.join(d, "frame_*.png")):
        os.remove(_f)
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
def orbit_chamber(n=48, drone="mavic4pro", height=10.2, name="orbit_chamber"):
    # 카메라는 챔버 **내부**를 돈다. 원형 궤도(반지름 13)는 깊이 20 m 벽(±10)을 뚫고 밖으로
    # 나가 프레임 절반이 검은 공허가 됐다 → 방 크기(30×20)에 맞춘 **타원 궤도**로 가둔다.
    # 여백 rx=W/2−4·5, ry=D/2−4 로 사방 벽에서 최소 4 m 떨어져 항상 내부 벽이 화면을 채운다.
    # 천장을 연(cutaway) 챔버를 **높은 곳에서 아래로 내려다보며** 한 바퀴 돈다. 원래 문제는
    # 원형 반경 13 이 깊이 20 m 벽(±10)을 뚫어 th≈90°/270° 에서 카메라가 밖으로 나가 검은 공허가
    # 생긴 것뿐 → **타원 궤도**(rx=10.5, ry=6.5)로 사방 footprint 안에 가둔다. 높은 시점 + 아래를
    # 겨눈 look(z=2.0)으로 화면을 바닥·벽 아래쪽이 채워 열린 천장(검은 배경)이 프레임에 안 들어온다.
    scene = make_scene(drone=drone, cutaway=True, vel=(-3.0, 0.0, 0.0))
    look = (W / 2, D / 2, 0.8)
    rx, ry = W / 2 - 5.0, D / 2 - 4.0
    cams = []
    for k in range(n):
        th = 2 * np.pi * k / n
        pos = (W / 2 + rx * np.cos(th), D / 2 + ry * np.sin(th), height)
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


# --------------------------------------------------------------------------- #
#  ⑥ 관측 모호성 — 표적을 TX-RX 축 둘레로 돌려도 R_b·f_d 가 안 변한다 (report11 §5)
# --------------------------------------------------------------------------- #
def obs_baseline_ring(n=36, name="obs_baseline_ring", drone="mavic4pro"):
    """**엄밀 대칭의 시각화**: 표적을 송수신 축(baseline) 둘레로 회전시키며 렌더.
    R_b(바이스태틱 거리)와 f_d 가 **바뀌지 않으므로**, 이 원 위 어디에 있든 레이더는 구분 못 한다
    → 단일 TX-RX 쌍으로 3D 위치가 관측 불가한 이유(report11 §5).
    각 프레임에 실제로 계산한 R_b 를 찍어 '변하지 않음'을 증거로 보인다."""
    tx = np.asarray(TX, float); rx = np.asarray(RX, float); tgt = np.asarray(TGT, float)
    u = (rx - tx); u /= np.linalg.norm(u)                     # baseline 축 방향
    L = float(np.linalg.norm(rx - tx))

    def rot_axis(p, ang):                                     # Rodrigues: TX 기준 u 축 회전
        v = p - tx; c, s = np.cos(ang), np.sin(ang)
        return tx + v * c + np.cross(u, v) * s + u * (u @ v) * (1 - c)

    fdir = _framedir(name)
    rbs = []
    t0 = time.time()
    for i in range(n):
        ang = 2 * np.pi * i / n
        p = rot_axis(tgt, ang)
        rb = float(np.linalg.norm(p - tx) + np.linalg.norm(rx - p) - L)   # 바이스태틱 거리
        rbs.append(rb)
        sc = make_scene(drone=drone, tgt=tuple(map(float, p)), cutaway=True, vel=(-3.0, 0.0, 0.0))
        sc.render_to_file(camera=cam(*CAMS["wide"]), filename=os.path.join(fdir, f"frame_{i:03d}.png"),
                          num_samples=HIQ_SPP, resolution=HIQ_RES, clip_at=CLIP_CEIL, fov=70.0)
    gif = os.path.join(OUT, "anim", f"{name}.gif")
    make_gif(fdir, gif, ms=110)
    print(f"  ✅ {name}.gif  ({n}프레임, {time.time()-t0:.0f}s)")
    print(f"     R_b 범위: {min(rbs):.6f} ~ {max(rbs):.6f} m  (변동 {max(rbs)-min(rbs):.2e} m "
          f"= 기계정밀도 → 이 원 위 어디든 레이더에겐 동일)")
    return gif


WHICH = {
    "obs_ring": obs_baseline_ring,
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
