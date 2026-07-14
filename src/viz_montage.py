# -*- coding: utf-8 -*-
"""
viz_montage.py — 렌더 이미지들을 라벨 붙여 한 장으로 모은 '카탈로그/시설뷰'
============================================================================
이미 만들어진 PNG 렌더(outputs/renders/)를 불러와 제목과 함께 격자로 배치한다.
  catalog.png        : 5종 드론 스튜디오 렌더 모음 (카탈로그)
  facility_views.png : 차폐시설 주요 시점 모음
(렌더가 먼저 생성돼 있어야 함 → render_drones.py 실행 후 호출)
"""
from __future__ import annotations
import os
import matplotlib.image as mpimg

import vizstyle
vizstyle.use_korean()
import matplotlib.pyplot as plt

from drones import DRONES, frame_envelope_mm
from vizstyle import RELEASE_BADGE

REN = os.path.join(os.path.dirname(__file__), "..", "outputs", "renders")
FIG = os.path.join(os.path.dirname(__file__), "..", "outputs", "figures")


def _show(ax, path, title, sub=None, badge=None):
    if os.path.exists(path):
        ax.imshow(mpimg.imread(path))
    else:
        ax.text(0.5, 0.5, "(render missing)\n" + os.path.basename(path),
                ha="center", va="center", transform=ax.transAxes)
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.axis("off")
    if sub:
        ax.text(0.5, -0.04, sub, ha="center", va="top", transform=ax.transAxes,
                fontsize=9.5, color="#444")
    if badge:
        lbl, col = badge
        ax.text(0.02, 0.97, lbl, transform=ax.transAxes, fontsize=10,
                fontweight="bold", color="white", va="top",
                bbox=dict(boxstyle="round", fc=col, ec="none"))


def catalog(outdir=FIG):
    keys = list(DRONES.keys())
    fig, axes = plt.subplots(2, 3, figsize=(15, 8.4), constrained_layout=True)
    fig.suptitle("5 DJI drones — Sionna RT render catalog (3D models from real specs)",
                 fontsize=17, fontweight="bold")
    for ax, key in zip(axes.flat, keys):
        s = DRONES[key]
        # 2026-07-14: 대각거리는 **메쉬**(공식 외형 정합) 기준. Mini/Mavic 은 DJI 미발표라
        #   카탈로그값이 추정치였고, Mavic 은 공식 외형과 기하학적으로 모순이었다(†).
        d = frame_envelope_mm(s)["diagonal_effective_mm"]
        dag = f"{d:.0f} mm†" if key in ("mini5pro", "mavic4pro") else f"{d:.0f} mm"
        sub = f"diag {dag} · {s.weight_g:g} g · {s.num_rotors} rotors"
        _show(ax, os.path.join(REN, f"studio_{key}.png"),
              s.name.split("  ")[0], sub, RELEASE_BADGE.get(s.release))
    # 마지막 칸: 비행 장면
    _show(axes.flat[5], os.path.join(REN, "flight_scene.png"),
          "Drones inside the semi-anechoic chamber",
          "30 m × 20 m × 11 m semi-anechoic chamber (true scale) — walls + ceiling absorber, floor reflective")
    # '†' 를 달아 놓고 범례가 없으면 "저 단검 뭐냐"만 부른다 → 키를 그림 안에 남긴다.
    #   (constrained_layout=True 라 supxlabel 자리는 레이아웃이 확보해 준다. bbox_inches="tight" 는
    #    금지 — 1800x1008 크기가 바뀌면 build_deck_v15.py 의 이미지 스왑 키가 깨진다.)
    fig.supxlabel("Diagonal is measured on the mesh, which is fitted to DJI's official envelope.   "
                  "† DJI does not publish a wheelbase for these two models, so this value is implied by that envelope.",
                  fontsize=8.5, color="0.45")
    fn = os.path.join(outdir, "catalog.png")
    os.makedirs(outdir, exist_ok=True)
    fig.savefig(fn, dpi=120); plt.close(fig)
    print("[montage]", os.path.relpath(fn))
    return fn


def facility_views(outdir=FIG):
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.6), constrained_layout=True)
    fig.suptitle("Large semi-anechoic chamber (shielded facility) — Sionna RT renders", fontsize=16, fontweight="bold")
    _show(axes[0], os.path.join(REN, "facility_hero.png"), "Overall view (front wall cut away)")
    # HERO_CAM2 렌더는 '코너 접사'가 아니라 벽이 닫힌 외관 뷰다(재렌더 금지 — 제목만 실물에 맞춤).
    _show(axes[1], os.path.join(REN, "facility_corner.png"),
          "Exterior view (shield walls closed)", "metal shield box + steel frame")
    _show(axes[2], os.path.join(REN, "lineup_floor.png"), "5 drones lined up on the floor")
    fn = os.path.join(outdir, "facility_views.png")
    os.makedirs(outdir, exist_ok=True)
    # 이미지 축은 aspect=equal 이라 축 박스가 그림 하단에 바짝 붙는다. sub 텍스트(축 밖 y=-0.04)가
    # 잘리지 않도록 저장 시 bbox 를 넓힌다(constrained_layout 은 자유 텍스트를 계산에 넣지 않음).
    fig.savefig(fn, dpi=120, bbox_inches="tight"); plt.close(fig)
    print("[montage]", os.path.relpath(fn))
    return fn


if __name__ == "__main__":
    catalog()
    facility_views()
    print("몽타주 생성 완료 →", os.path.relpath(FIG))
