# -*- coding: utf-8 -*-
"""
render_md_scene.py — ⭐마이크로도플러 시나리오 배치를 **Sionna 렌더**로 보여준다.

왜
--
사용자 지적: *"시나리오 배치를 sionna 렌더링해서 보여주고, 그 뒤 마이크로 도플러 그림을
보여주면 안될까?"* — 맞다. TX/RX 가 어디 있고 드론을 어느 각도에서 보는지 **그림으로**
먼저 보여야 맵이 읽힌다. §0 의 좌표 표를 렌더가 뒷받침한다.

무엇을 그리나 — 세 엔진 비교(그림 3)의 배치 그대로
    드론      DJI Matrice 4E, 원점, 호버 자세
    TX        (+2.898, −0.100, −0.776) m   ← 거리 3 m · el −15° · 기선 0.2 m
    RX        (+2.898, +0.100, −0.776) m
    바이스태틱각 3.8° (준-모노스태틱)

두 컷
    f0a  옆에서 본 전체 — TX/RX 공과 드론이 한 화면에 (기하가 한눈에)
    f0b  TX/RX 쪽에서 드론을 본 근접 — 레이더가 보는 배 쪽 모습

    python benchmark/render_md_scene.py
"""
from __future__ import annotations

import os
import sys
import time

os.environ.setdefault("SIONNA2_GPU", "2")

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
AZ, EL, RNG, BASE = 0.0, -15.0, 3.0, 0.0   # ⭐기선 0 = 진짜 모노스태틱(2026-08-10)
#   ⚠0.2(준-모노)였다. 그림 3 절이 «진짜 모노스태틱» 을 선언하는데 그 절의 렌더만
#     준-모노여서 그림과 글이 어긋났다 — 적대적 검증이 잡은 불일치.


def main():
    spec = DRONES["matrice4e"]
    # 세 엔진 비교와 같은 자세(위상 0) · 같은 배치
    scene, mesh, scratch = RP.build_posed_scene(spec, 0.0, "REN")
    pl = RP.place(scene, az=AZ, el=EL, rng=RNG, baseline=BASE)
    tx, rx = np.array(pl["tx"]), np.array(pl["rx"])
    mid = 0.5 * (tx + rx)

    # 장치 공 크기 — 3 m 씬에서 보이게
    for nm in ("tx", "rx"):
        scene.get(nm).display_radius = 0.09

    def cam(pos, look):
        return rt.Camera(position=mi.Point3f(*[float(v) for v in pos]),
                         look_at=mi.Point3f(*[float(v) for v in look]))

    # ⭐고화질 오버라이드(2026-08-10, 사용자 지시: GPU2 전유 — 메모리 크게)
    #   ⚠주의 실측: 2560×1600 × spp4096 = 34 GB OOM. spp2048 은 ~17 GB 로 안전.
    _RW = int(os.environ.get("MDSCENE_RES_W", "1760"))
    _RH = int(os.environ.get("MDSCENE_RES_H", "1100"))
    _SPP = int(os.environ.get("MDSCENE_SPP", "1024"))

    def shot(name, camera, res=None, spp=None, fov=55.0):
        res = res or (_RW, _RH)
        spp = spp or _SPP
        p = os.path.join(FIGDIR, f"{name}.png")
        t0 = time.time()
        scene.render_to_file(camera=camera, filename=p, num_samples=spp,
                             resolution=res, fov=fov)
        print(f"  ✅ {os.path.relpath(p, ROOT)}  ({time.time()-t0:.1f}s)", flush=True)

    # f0a — 옆(+y)에서 본 전체 기하: 드론(원점)과 TX/RX(3 m 아래-앞)가 한 화면
    center = 0.5 * (mid + np.zeros(3))
    shot("report07_f0a", cam(center + np.array([0.0, 3.6, 0.9]), center), fov=62.0)

    # f0b — TX/RX 뒤에서 드론을 본 시선: 레이더가 보는 배 쪽 모습
    u = -mid / np.linalg.norm(mid)                     # TX/RX → 드론 방향
    shot("report07_f0b", cam(mid - 0.9 * u + np.array([0, 0, 0.18]),
                             np.zeros(3)), fov=26.0)

    # ⭐ f0c — 그림 3(세 엔진)의 씬 그대로: PathSolver 가 실제로 찾은 경로를 겹쳐 그린다.
    #   경로해 설정은 세 엔진 실행(report07_three_engine_maps.py)과 동일하다.
    paths = rt.PathSolver()(scene, max_depth=1, los=True, specular_reflection=True,
                            diffuse_reflection=True, refraction=False,
                            samples_per_src=1_000_000,
                            max_num_paths_per_src=RP.MAX_PATHS, seed=1)
    a, _, _, O = RP.unpack(paths)
    n_hit = int(((O != RP.NO_OBJ).any(axis=0)).sum()) if O.size else 0
    print(f"  경로 {a.size}개 (표적경유 {n_hit}개)", flush=True)
    p = os.path.join(FIGDIR, "report07_f0c.png")
    t0 = time.time()
    scene.render_to_file(camera=cam(center + np.array([0.9, 3.2, 0.75]), center),
                         filename=p, num_samples=_SPP, resolution=(_RW, _RH),
                         paths=paths, fov=58.0)
    print(f"  ✅ {os.path.relpath(p, ROOT)}  ({time.time()-t0:.1f}s)", flush=True)

    RP.drop_scratch(scratch)


if __name__ == "__main__":
    main()
