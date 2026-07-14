# -*- coding: utf-8 -*-
"""
build_report3.py — report3 ("Sionna RT 광선 반사 실험") 산출물 생성
====================================================================
이 리포트는 **렌더가 주인공**이다. 그림의 대부분은 우리가 그린 도식이 아니라
**Sionna 가 자기 렌더러(Mitsuba 3)로 그린, 자기가 추적한 광선**이다.

단계
  1) benchmark/rt_experiments.py  — 모든 숫자 → outputs/report3_rt.json
  2) 이 파일의 render_all()        — **Sionna 렌더** (씬/경로/라디오맵) → outputs/renders/report3/
  3) src/viz_report3.py            — 렌더를 판넬로 조립 + 실험 그래프 → outputs/figures/
  4) src/make_notebook3.py         — report3.ipynb (숫자는 1) 의 JSON 에서 읽어 주입)

렌더 품질 (사용자 지시: **GPU 를 아끼지 말 것**)
  num_samples = 640 (>= 512),  해상도 = 1760x1200 (>= 1600x1100).

실행:
    python src/build_report3.py                  # 전체
    python src/build_report3.py --no-rt          # 측정 재사용 (report3_rt.json)
    python src/build_report3.py --no-render      # 렌더 재사용 (그림 문구만 고칠 때)
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
_BENCH = os.path.join(_ROOT, "benchmark")
for _p in (_HERE, _BENCH):
    if _p not in sys.path:
        sys.path.insert(0, _p)

RJSON = os.path.join(_ROOT, "outputs", "report3_rt.json")
RDIR = os.path.join(_ROOT, "outputs", "renders", "report3")

SPP = 640                    # >= 512  (사용자 지시)
RES = (1760, 1200)           # >= 1600x1100
RT_SPP = 4_000_000           # PathSolver 광선 (렌더에 그릴 경로 찾기)

#  ⚠ **닫힌 방은 새까맣게 렌더된다.** Sionna 의 렌더러는 환경광(environment emitter)으로
#     비추는데, 6면이 막힌 챔버 안으로는 빛이 못 들어온다. 그래서 천장을 `clip_at` 으로
#     열어 빛을 들인다. 이건 **렌더 조명일 뿐 전파 시뮬레이션과 무관하다**
#     (경로는 clip 하지 않은 전체 씬에서 이미 계산돼 있다).
CLIP_WIDE = 10.8             # 천장 흡수체 피라미드만 살짝 열어 빛을 들인다 (천장 반사점 z=10.75 는 남는다)
CLIP_TOP = 9.0               # 상면도 — 천장/상단 흡수체를 통째로 걷어낸다


# --------------------------------------------------------------------------- #
#  Sionna 렌더 — 씬 · 추적된 광선 · 라디오맵
# --------------------------------------------------------------------------- #
def render_all(spp=SPP, res=RES, quick=False):
    """**Sionna RT 렌더러**가 그린다 — 우리가 matplotlib 로 그리는 게 아니다."""
    import numpy as np
    from gpu import pick
    pick(verbose=True)                                  # ⚠ mitsuba import 전에
    import mitsuba as mi
    import sionna.rt as rt
    from render_rt import make_scene, cam, CAMS, CLIP_CEIL, W, D
    from bistatic_scene import TGT

    os.makedirs(RDIR, exist_ok=True)
    if quick:
        spp, res = 96, (900, 620)

    def _shot(scene, name, camera, **kw):
        p = os.path.join(RDIR, f"{name}.png")
        t0 = time.time()
        scene.render_to_file(camera=camera, filename=p,
                             num_samples=kw.get("spp", spp), resolution=kw.get("res", res),
                             paths=kw.get("paths"), radio_map=kw.get("radio_map"),
                             clip_at=kw.get("clip"), fov=kw.get("fov", 70.0))
        print(f"    [render] {os.path.relpath(p, _ROOT):50s} ({time.time()-t0:5.1f}s)")
        return p

    # ---- ① 씬 갤러리 — 챔버를 여러 눈으로 -------------------------------- #
    #  ⚠ **경로 렌더는 반드시 cutaway=False(전체 씬)로 한다.**
    #     cutaway 는 앞벽(absorber_front/backing_front/frame_front)을 **지운다** → 씬이 달라지고
    #     경로 수가 달라진다(depth2: 16 → 13). 하필 19.33 ns 의 그 두 번째 경로가
    #     **absorber_front 이중반사**라서, cutaway 렌더에는 그게 아예 없다.
    #     카메라(wide/top/grazing)는 전부 챔버 **안**에 있으므로 cutaway 없이도 내부가 보인다.
    #     (밖에서 보는 side 카메라만 cutaway 가 필요하다.)
    print("\n  ① 씬 갤러리")
    sc = make_scene(cutaway=False)                      # ← 측정과 **같은 씬**
    _shot(sc, "r3_scene_outside", cam((-26, -22, 18)))                 # 밖 — 강철 골조
    _shot(sc, "r3_scene_wide", cam(*CAMS["wide"]), clip=CLIP_WIDE)     # 안 — 전체 배치
    _shot(sc, "r3_scene_top", cam(*CAMS["top"]), clip=CLIP_TOP)        # 상면
    _shot(sc, "r3_scene_grazing", cam(*CAMS["grazing"]), clip=CLIP_WIDE)   # 바닥 스침
    _shot(sc, "r3_scene_target", cam(*CAMS["over_target"]), clip=CLIP_WIDE)  # 표적 근접
    sc_cut = make_scene(cutaway=True)                   # 밖에서 들여다보는 컷어웨이 (갤러리용)
    _shot(sc_cut, "r3_scene_side", cam(*CAMS["side"]), clip=CLIP_TOP)

    # ---- ② 추적된 광선 — max_depth = 0/1/2/3 (이 리포트의 첫 그림) ------- #
    print("\n  ② 추적된 광선 (max_depth 0/1/2/3)")
    #  ⚠ 카메라 선택이 중요하다: TX(4,2.5,8) · RX(4,17.5,6.5) · 바닥반사점(4,10.8,0) 은
    #    **모두 x=4 평면 위**에 있다. CAMS["wide"] 는 그 평면을 정면으로 보므로
    #    바닥 반사 삼각형(TX ↘ 바닥 ↗ RX)이 찌그러지지 않고 그대로 보인다.
    solver = rt.PathSolver()
    for md in (0, 1, 2, 3):
        paths = solver(sc, max_depth=md, los=True, specular_reflection=True,
                       diffuse_reflection=False, refraction=False,
                       samples_per_src=RT_SPP, seed=1)
        n = int(np.asarray(paths.tau).size)
        print(f"    depth={md}: 경로 {n}개")
        _shot(sc, f"r3_paths_d{md}_wide", cam(*CAMS["wide"]), paths=paths, clip=CLIP_WIDE)
        _shot(sc, f"r3_paths_d{md}_top", cam(*CAMS["top"]), paths=paths, clip=CLIP_TOP)
    #  표적(드론) 근접 — 드론이 씬에 **있는데도** 표적 경유 경로가 없다(§3 의 예고)
    paths3 = solver(sc, max_depth=3, los=True, specular_reflection=True,
                    diffuse_reflection=False, refraction=False,
                    samples_per_src=RT_SPP, seed=1)
    _shot(sc, "r3_paths_d3_target", cam(*CAMS["over_target"]), paths=paths3, clip=CLIP_WIDE)

    # ---- ③ 라디오맵 — 바닥면 / 드론 평면 --------------------------------- #
    print("\n  ③ 라디오맵 (RadioMapSolver)")
    rms = rt.RadioMapSolver()
    n_tx = 400_000 if quick else 8_000_000
    for z, tag in ((0.05, "floor"), (float(TGT[2]), "droneplane")):
        t0 = time.time()
        rm = rms(sc, center=mi.Point3f(W / 2, D / 2, z),
                 orientation=mi.Point3f(0, 0, 0),
                 size=mi.Point2f(W - 0.5, D - 0.5),
                 cell_size=mi.Point2f(0.25, 0.25),
                 samples_per_tx=n_tx, max_depth=3,
                 specular_reflection=True, diffuse_reflection=False)
        print(f"    z={z:.2f} m ({time.time()-t0:.1f}s)")
        _shot(sc, f"r3_radiomap_{tag}_top", cam(*CAMS["top"]), radio_map=rm, clip=CLIP_TOP)
        _shot(sc, f"r3_radiomap_{tag}_wide", cam(*CAMS["wide"]), radio_map=rm, clip=CLIP_WIDE)
    print(f"\n  ✅ 렌더 → {os.path.relpath(RDIR, _ROOT)}/")


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-rt", action="store_true", help="측정 재사용(report3_rt.json)")
    ap.add_argument("--no-render", action="store_true", help="Sionna 렌더 재사용")
    ap.add_argument("--no-nb", action="store_true", help="노트북 생성 생략")
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    t0 = time.time()

    print("=" * 78)
    print("▶ 1) 측정 — benchmark/rt_experiments.py  (리포트의 **모든 숫자**가 여기서 나온다)")
    print("=" * 78)
    if a.no_rt and os.path.exists(RJSON):
        print("  (기존 outputs/report3_rt.json 재사용)")
    else:
        cmd = [sys.executable, os.path.join(_BENCH, "rt_experiments.py")]
        if a.quick:
            cmd.append("--quick")
        subprocess.run(cmd, check=True)

    print("\n" + "=" * 78)
    print("▶ 2) Sionna 렌더 — 씬 · 추적된 광선 · 라디오맵")
    print("=" * 78)
    if a.no_render:
        print("  (기존 렌더 재사용)")
    else:
        render_all(quick=a.quick)

    print("\n" + "=" * 78)
    print("▶ 3) 그림 — 렌더 조립 + 실험 그래프 (src/viz_report3.py)")
    print("=" * 78)
    import viz_report3 as V
    V.build_all()

    if not a.no_nb:
        print("\n" + "=" * 78)
        print("▶ 4) 노트북 — report3.ipynb (src/make_notebook3.py)")
        print("=" * 78)
        subprocess.run([sys.executable, os.path.join(_HERE, "make_notebook3.py")], check=True)

    print(f"\n✅ report3 완료 ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
