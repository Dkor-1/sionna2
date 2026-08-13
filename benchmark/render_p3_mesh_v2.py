# -*- coding: utf-8 -*-
"""
render_p3_mesh_v2.py — Phantom 3 **재제작 메쉬** 온전성 렌더 (2026-08-03)
=========================================================================

무엇을 하나
  사진 실측으로 다시 만든 `phantom3` 메쉬를 네 방향 직교투영으로 그리고, **구판**(사진이
  한 장도 없던 시절 phantom4 형상표를 상속하던 메쉬)을 같은 카메라·같은 축척으로 바로
  아래에 나란히 놓는다. 결과는 `outputs/figs/p3_mesh_v2.png`.

  구판 메쉬는 이 저장소에 코드로 남아 있지 않으므로(덮어썼다) 스크래치에 떠 둔
  `p3_old_mesh.npz`(정점·면·그룹)를 읽는다. 없으면 신판만 그린다.

왜 별도 스크립트인가
  `src/viz_mesh_gallery.py` 는 전 기종 원장과 그림을 통째로 다시 쓴다. 지금 다른
  워크플로가 같은 원장을 만지고 있어 **이 기체 한 장만** 새 경로에 낸다. 렌더러 자체는
  그 모듈 것을 그대로 재사용한다(음영·직교카메라 규약 동일).
  benchmark/render_mini2_mesh.py · render_m350rtk_mesh.py 와 같은 형식이다.

실행
  cd /workspace/sionna
  SIONNA2_CPU=1 PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/render_p3_mesh_v2.py
"""
from __future__ import annotations

import os

import numpy as np

import vizstyle
vizstyle.use_korean()
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

import viz_mesh_gallery as G
from drones import (DRONES, MATERIAL_COLOR, DRONE_GROUP_MAT, build_drone, build_frame,
                    frame_envelope_mm)

KEY = "phantom3"
OUTDIR = os.path.join(G.ROOT, "outputs", "figs")
OUTPNG = os.path.join(OUTDIR, "p3_mesh_v2.png")
OLD_NPZ = ("/tmp/claude-1015/-workspace/"
           "a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad/p3/p3_old_mesh.npz")

#  (라벨, elev, azim) — 정면·측면·상면·아이소
VIEWS = (("front  (+x toward viewer)", 0.0, 0.0),
         ("side   (looking along +y)", 0.0, 90.0),
         ("top", 89.0, 0.0),
         ("iso  el 22 / az 38", 22.0, 38.0))

#  DJI 공표(프롭 제외). 그림에 대조로 적는다.
PUB_BBOX_MM = (289.5, 289.0, 185.0)
PUB_DIAG_MM = 350.0


def face_colors(groups) -> np.ndarray:
    """면별 순수 재질색 — `DRONE_GROUP_MAT` → `MATERIAL_COLOR` 단일 경로."""
    out = np.zeros((len(groups), 3), float)
    for i, g in enumerate(groups):
        mat = DRONE_GROUP_MAT.get(str(g), ("plastic", ""))[0]
        out[i] = MATERIAL_COLOR[mat]
    return out


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    spec = DRONES[KEY]
    drone, frame = build_drone(spec), build_frame(spec)
    V = np.asarray(drone.v, float)
    F = np.asarray(drone.f, int)
    rgb = face_colors(drone.g)
    Vf = np.asarray(frame.v, float)

    old = None
    if os.path.exists(OLD_NPZ):
        z = np.load(OLD_NPZ, allow_pickle=True)
        old = dict(v=z["v"], f=z["f"], rgb=face_colors(list(z["g"])),
                   fv=z["fv"], ff=z["ff"])

    #  두 메쉬를 **같은 축척**으로 본다 — 크기 차이가 눈에 보여야 한다.
    allV = V if old is None else np.vstack([V, old["v"]])
    cen = 0.5 * (allV.max(0) + allV.min(0))
    half = G.common_half(allV, cen, views=[(t, e, a, "") for t, e, a in VIEWS])

    env = frame_envelope_mm(spec)
    ext = np.asarray(env["lwh_mm"], float)
    extd = (V.max(0) - V.min(0)) * 1000.0

    nrow = 1 if old is None else 2
    fig, axes = plt.subplots(nrow, 4, figsize=(19.2, 5.4 * nrow))
    axes = np.atleast_2d(axes)
    for j, (tag, elev, azim) in enumerate(VIEWS):
        basis = G.view_basis(elev, azim)
        ax = axes[0, j]
        G.draw_mesh(ax, V - cen, F, rgb, basis)
        G.set_view(ax, (0.0, 0.0), half)
        G.scale_bar(ax, half, (0.0, 0.0))
        ax.text(0.02, 0.98, tag, transform=ax.transAxes, ha="left", va="top", fontsize=10.5)
        if j == 0:
            ax.text(0.02, 0.915, "NEW  (photo-measured, 2026-08-03)", transform=ax.transAxes,
                    ha="left", va="top", fontsize=11.5, fontweight="bold", color="#0b6")
        if old is not None:
            ax2 = axes[1, j]
            G.draw_mesh(ax2, old["v"] - cen, old["f"], old["rgb"], basis)
            G.set_view(ax2, (0.0, 0.0), half)
            G.scale_bar(ax2, half, (0.0, 0.0))
            ax2.text(0.02, 0.98, tag, transform=ax2.transAxes, ha="left", va="top", fontsize=10.5)
            if j == 0:
                ax2.text(0.02, 0.915, "OLD  (phantom4 tables inherited)", transform=ax2.transAxes,
                         ha="left", va="top", fontsize=11.5, fontweight="bold", color="#b60")

    mats = sorted({DRONE_GROUP_MAT.get(g, ("plastic", ""))[0] for g in drone.g})
    fig.legend(handles=[Patch(facecolor=MATERIAL_COLOR[m], label=m) for m in mats],
               loc="lower center", ncol=len(mats), frameon=False, fontsize=10,
               bbox_to_anchor=(0.5, 0.008))

    fig.suptitle("DJI Phantom 3 Professional  —  mesh rebuilt from photographs "
                 "(colour = pure material)", fontsize=15, y=0.985)
    ovf = ""
    if old is not None:
        oext = (old["fv"].max(0) - old["fv"].min(0)) * 1000.0
        ovf = (f"OLD: triangles {len(old['f']):,}   frame bbox "
               f"{oext[0]:.1f} x {oext[1]:.1f} x {oext[2]:.1f} mm\n")
    sub = (f"NEW: triangles {len(F):,}  (frame {len(frame.f):,} + 4 propellers)   "
           f"frame bbox {ext[0]:.1f} x {ext[1]:.1f} x {ext[2]:.1f} mm  "
           f"vs published {PUB_BBOX_MM[0]:.1f} x {PUB_BBOX_MM[1]:.1f} x {PUB_BBOX_MM[2]:.1f} "
           f"(props excl.)\n" + ovf +
           f"wheelbase {env['wheelbase_opposite_mm']:.2f} mm vs published {PUB_DIAG_MM:.1f}   "
           f"envelope fit scale {tuple(round(s, 4) for s in env['fit_scale'])}   "
           f"with propellers {extd[0]:.0f} x {extd[1]:.0f} x {extd[2]:.0f} mm\n"
           f"frame z-range {Vf[:, 2].min() * 1000:+.1f} .. {Vf[:, 2].max() * 1000:+.1f} mm "
           f"(z = 0 is the arm axis at the motor station; the published 185 mm is shell crown "
           f"to feet, NOT motor top to feet)")
    fig.text(0.5, 0.958, sub, ha="center", va="top", fontsize=8.8, color="#333")
    fig.subplots_adjust(top=0.845, bottom=0.055, left=0.012, right=0.988,
                        hspace=0.03, wspace=0.02)
    fig.savefig(OUTPNG, dpi=160)
    plt.close(fig)
    print(f"[phantom3] 렌더 저장: {OUTPNG}")
    print(f"           삼각형 {len(F)} · 프레임 bbox {np.round(ext, 2)} mm · "
          f"휠베이스 {env['wheelbase_opposite_mm']:.2f} mm · "
          f"fit_scale {tuple(round(s, 4) for s in env['fit_scale'])}")


if __name__ == "__main__":
    main()
