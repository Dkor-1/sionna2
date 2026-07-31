# -*- coding: utf-8 -*-
"""
viz_anim.py — 드론 회전(turntable) 애니메이션 GIF (matplotlib, Sionna 불필요)
=============================================================================

각 드론을 한 바퀴 빙 돌려 보는 GIF 를 만든다. 정지 이미지보다 형상을 훨씬
직관적으로 이해할 수 있다. (GPU 불필요 — CPU 만 사용)

생성물 (outputs/figures/)
  turntable_<key>.gif : 드론 1종 360° 회전
  turntable_all.gif    : 전 기종을 한 화면에서 동시에 회전
"""
from __future__ import annotations

import os
import numpy as np

import vizstyle
vizstyle.use_korean()
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from drones import DRONES, build_drone, drone_colors, drone_label

FIG = os.path.join(os.path.dirname(__file__), "..", "outputs", "figures")


def _polys(mesh, cmap):
    V = np.array(mesh.v)
    tris = [[V[a], V[b], V[c]] for (a, b, c) in mesh.f]
    cols = [cmap.get(g, (0.6, 0.6, 0.6)) for g in mesh.g]
    return Poly3DCollection(tris, facecolors=cols, edgecolors=(0, 0, 0, 0.10),
                            linewidths=0.12)


def _equal(ax, mesh, pad=1.1):
    b0, b1 = mesh.bounds(); c = (b0 + b1) / 2; rng = (b1 - b0).max() * pad / 2
    ax.set_xlim(c[0]-rng, c[0]+rng); ax.set_ylim(c[1]-rng, c[1]+rng)
    ax.set_zlim(c[2]-rng, c[2]+rng)
    try: ax.set_box_aspect((1, 1, 1))
    except Exception: pass
    ax.set_axis_off()


def turntable(key, outdir=FIG, frames=36, fps=18):
    spec = DRONES[key]; mesh = build_drone(spec); cmap = drone_colors(spec)
    fig = plt.figure(figsize=(4.6, 4.6))
    ax = fig.add_subplot(111, projection="3d")
    ax.add_collection3d(_polys(mesh, cmap)); _equal(ax, mesh)
    ax.set_title(spec.name, fontsize=11, fontweight="bold")

    def update(i):
        ax.view_init(elev=20, azim=i * 360 / frames)
        return ()

    anim = FuncAnimation(fig, update, frames=frames, blit=False)
    os.makedirs(outdir, exist_ok=True)
    fn = os.path.join(outdir, f"turntable_{key}.gif")
    anim.save(fn, writer=PillowWriter(fps=fps), dpi=82)
    plt.close(fig)
    print("[turntable]", os.path.relpath(fn))
    return fn


def turntable_all(outdir=FIG, frames=36, fps=18):
    keys = list(DRONES.keys())
    meshes = {k: build_drone(DRONES[k]) for k in keys}
    cmaps = {k: drone_colors(DRONES[k]) for k in keys}
    # ⚠ 열 수는 **기종 수**다. 예전엔 `add_subplot(1, 5, ...)` 로 5 가 박혀 있어 기종이 6개가
    #   되는 순간 ValueError(num must be 1 <= num <= 5) 로 죽었다.
    fig = plt.figure(figsize=(3.0 * len(keys), 3.4))
    axes = {}
    for j, k in enumerate(keys):
        ax = fig.add_subplot(1, len(keys), j + 1, projection="3d")
        ax.add_collection3d(_polys(meshes[k], cmaps[k])); _equal(ax, meshes[k])
        ax.set_title(drone_label(k), fontsize=10)
        axes[k] = ax
    fig.suptitle(f"{len(keys)} target drones - turntable (not to scale)", fontsize=13, fontweight="bold")

    def update(i):
        for ax in axes.values():
            ax.view_init(elev=20, azim=i * 360 / frames)
        return ()

    anim = FuncAnimation(fig, update, frames=frames, blit=False)
    os.makedirs(outdir, exist_ok=True)
    fn = os.path.join(outdir, "turntable_all.gif")
    anim.save(fn, writer=PillowWriter(fps=fps), dpi=80)
    plt.close(fig)
    print("[turntable]", os.path.relpath(fn))
    return fn


if __name__ == "__main__":
    for k in DRONES:
        turntable(k)
    turntable_all()
    print("회전 GIF 생성 완료 →", os.path.relpath(FIG))
