# -*- coding: utf-8 -*-
"""
render_m350rtk_mesh.py — m350rtk 메쉬 온전성 렌더 (2026-08-03)
================================================================

무엇을 하나
  새로 등록한 `m350rtk`(DJI Matrice 350 RTK) 메쉬를 네 방향 직교투영으로 그려
  `outputs/figs/m350rtk_mesh.png` 에 저장한다. 색은 저장소 규약대로 **순수 재질 5색**이고,
  그림 안 글자는 전부 영어다(주석·print 는 한국어).

왜 별도 스크립트인가
  `src/viz_mesh_gallery.py` 는 전 기종 원장(`outputs/mesh_gallery.json`)과 그림을 통째로
  다시 쓴다. 지금은 다른 워크플로가 같은 원장을 만지고 있어서, **이 기체 한 장만** 새 경로에
  낸다. 렌더러 자체는 그 모듈 것을 그대로 재사용한다(음영·직교카메라 규약 동일).

실행
  cd /workspace/sionna
  SIONNA2_CPU=1 PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/render_m350rtk_mesh.py
"""
from __future__ import annotations

import os

import numpy as np

import vizstyle
vizstyle.use_korean()
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

import viz_mesh_gallery as G
from drones import DRONES, MATERIAL_COLOR, DRONE_GROUP_MAT, build_drone, build_frame, frame_envelope_mm

KEY = "m350rtk"
OUTDIR = os.path.join(G.ROOT, "outputs", "figs")
OUTPNG = os.path.join(OUTDIR, f"{KEY}_mesh.png")

#  (라벨, elev, azim) — 정면·측면·상면·아이소
VIEWS = (("front  (+x toward viewer)", 0.0, 0.0),
         ("side   (looking along +y)", 0.0, 90.0),
         ("top", 89.0, 0.0),
         ("iso  el 22 / az 38", 22.0, 38.0))


def face_colors(mesh) -> np.ndarray:
    """면별 순수 재질색 — `DRONE_GROUP_MAT` → `MATERIAL_COLOR` 단일 경로."""
    out = np.zeros((len(mesh.f), 3), float)
    for i, g in enumerate(mesh.g):
        mat = DRONE_GROUP_MAT.get(g, ("plastic", ""))[0]
        out[i] = MATERIAL_COLOR[mat]
    return out


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    spec = DRONES[KEY]
    drone = build_drone(spec)
    frame = build_frame(spec)
    V = np.asarray(drone.v, float)
    F = np.asarray(drone.f, int)
    rgb = face_colors(drone)
    cen = 0.5 * (V.max(0) + V.min(0))
    half = G.common_half(V, cen, views=[(t, e, a, "") for t, e, a in VIEWS])

    env = frame_envelope_mm(spec)
    ext = np.asarray(env["lwh_mm"], float)
    extd = (V.max(0) - V.min(0)) * 1000.0
    Vf = np.asarray(frame.v, float)

    fig, axes = plt.subplots(2, 2, figsize=(11.2, 10.4))
    for ax, (tag, elev, azim) in zip(axes.ravel(), VIEWS):
        basis = G.view_basis(elev, azim)
        G.draw_mesh(ax, V - cen, F, rgb, basis)
        G.set_view(ax, (0.0, 0.0), half)
        G.scale_bar(ax, half, (0.0, 0.0))
        ax.text(0.02, 0.98, tag, transform=ax.transAxes, ha="left", va="top", fontsize=10.5)

    mats = sorted({DRONE_GROUP_MAT.get(g, ("plastic", ""))[0] for g in drone.g})
    fig.legend(handles=[Patch(facecolor=MATERIAL_COLOR[m], label=m) for m in mats],
               loc="lower center", ncol=len(mats), frameon=False, fontsize=10,
               bbox_to_anchor=(0.5, 0.012))

    fig.suptitle("DJI Matrice 350 RTK  —  mesh (colour = pure material)", fontsize=14, y=0.988)
    sub = (f"triangles {len(F):,}  (frame {len(frame.f):,} + 4 propellers)   "
           f"frame bbox {ext[0]:.0f} x {ext[1]:.0f} x {ext[2]:.0f} mm  "
           f"vs published 810 x 670 x 430 (props excl.)\n"
           f"with propellers {extd[0]:.0f} x {extd[1]:.0f} x {extd[2]:.0f} mm   "
           f"wheelbase {env['wheelbase_opposite_mm']:.1f} mm vs published 895.0   "
           f"envelope fit scale {tuple(round(s, 4) for s in env['fit_scale'])}\n"
           f"frame z-range {Vf[:, 2].min() * 1000:+.0f} .. {Vf[:, 2].max() * 1000:+.0f} mm "
           f"(z = 0 is the arm axis at the motor station)")
    fig.text(0.5, 0.963, sub, ha="center", va="top", fontsize=9, color="#333")
    fig.subplots_adjust(top=0.885, bottom=0.062, left=0.02, right=0.98, hspace=0.02, wspace=0.02)
    fig.savefig(OUTPNG, dpi=170)
    plt.close(fig)
    print(f"[m350rtk] 렌더 저장: {OUTPNG}")
    print(f"          삼각형 {len(F)} · 프레임 bbox {np.round(ext, 1)} mm · "
          f"휠베이스 {env['wheelbase_opposite_mm']:.1f} mm")


if __name__ == "__main__":
    main()
