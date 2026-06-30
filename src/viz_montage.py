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

from drones import DRONES
from vizstyle import RELEASE_BADGE

REN = os.path.join(os.path.dirname(__file__), "..", "outputs", "renders")
FIG = os.path.join(os.path.dirname(__file__), "..", "outputs", "figures")


def _show(ax, path, title, sub=None, badge=None):
    if os.path.exists(path):
        ax.imshow(mpimg.imread(path))
    else:
        ax.text(0.5, 0.5, "(렌더 없음)\n" + os.path.basename(path),
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
    fig.suptitle("DJI 드론 5종 — Sionna RT 렌더 카탈로그 (실측 제원 기반 3D 모델)",
                 fontsize=17, fontweight="bold")
    for ax, key in zip(axes.flat, keys):
        s = DRONES[key]
        sub = f"대각 {s.diagonal_mm:.0f} mm · {s.weight_g:.0f} g · 로터 {s.num_rotors}"
        _show(ax, os.path.join(REN, f"studio_{key}.png"),
              s.name.split("  ")[0], sub, RELEASE_BADGE.get(s.release))
    # 마지막 칸: 비행 장면
    _show(axes.flat[5], os.path.join(REN, "flight_scene.png"),
          "차폐시설 안의 드론들", "30 m × 20 m × 11 m 무반사실 (실제 축척)")
    fn = os.path.join(outdir, "catalog.png")
    os.makedirs(outdir, exist_ok=True)
    fig.savefig(fn, dpi=120); plt.close(fig)
    print("[montage]", os.path.relpath(fn))
    return fn


def facility_views(outdir=FIG):
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.6), constrained_layout=True)
    fig.suptitle("대형 차폐시설(전파무반사실) — Sionna RT 렌더", fontsize=16, fontweight="bold")
    _show(axes[0], os.path.join(REN, "facility_hero.png"), "전체 모습 (앞벽 절개)")
    _show(axes[1], os.path.join(REN, "facility_corner.png"), "코너 근접")
    _show(axes[2], os.path.join(REN, "lineup_floor.png"), "바닥에 늘어선 5종")
    fn = os.path.join(outdir, "facility_views.png")
    os.makedirs(outdir, exist_ok=True)
    fig.savefig(fn, dpi=120); plt.close(fig)
    print("[montage]", os.path.relpath(fn))
    return fn


if __name__ == "__main__":
    catalog()
    facility_views()
    print("몽타주 생성 완료 →", os.path.relpath(FIG))
