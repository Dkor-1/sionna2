# -*- coding: utf-8 -*-
"""viz_report2_photo_compare.py — report2 용 **실제 제품 사진 vs 우리 v2 메쉬** 대조 그림.

왼쪽 = 사용자가 모은 실제 제품 사진(assets/photos/<key>/), 오른쪽 = 우리가 스펙시트로 만든
v2 파라메트릭 메쉬(같은 재질색). 스펙 치수는 그대로 두고 형상을 사진에 맞춰 개선한 결과를 눈으로 검증.
출력: outputs/figures/report2_photo_compare.png. 그림 텍스트는 전부 영어(규약).
"""
from __future__ import annotations
import glob
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from drones import DRONES, build_drone, drone_colors            # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, ".."))
OUT = os.path.join(ROOT, "outputs", "figures", "report2_photo_compare.png")

# 표시명 + 대표 사진 인덱스(iso/front 잘 보이는 것) + 렌더 시점
ROWS = [
    ("mavic4pro", "Mavic 4 Pro", (16, -70)),
    ("matrice4e", "Matrice 4E", (16, -70)),
    ("mini5pro", "Mini 5 Pro", (16, -70)),
    ("phantom4", "Phantom 4 Pro", (16, -70)),
    ("s1000plus", "S1000+", (18, -60)),
]


def _photo(key):
    fs = sorted(glob.glob(os.path.join(ROOT, "assets", "photos", key, "*")))
    if not fs:
        return None
    im = Image.open(fs[0]).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    return Image.alpha_composite(bg, im).convert("RGB")


def _render_mesh(ax, key, view):
    m = build_drone(DRONES[key]); cmap = drone_colors(DRONES[key])
    V = np.array(m.v, float); F = np.array(m.f); tris = V[F]
    cols = [cmap.get(g, (0.6, 0.6, 0.6)) for g in m.g]
    nrm = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    ln = np.linalg.norm(nrm, axis=1, keepdims=True); ln[ln < 1e-9] = 1
    sh = 0.55 + 0.45 * np.clip(nrm[:, 2:3] / ln * .6 + .5, 0, 1)
    fc = np.clip(np.array(cols) * sh, 0, 1)
    ax.add_collection3d(Poly3DCollection(tris, facecolors=fc, edgecolors="none"))
    c = (V.max(0) + V.min(0)) / 2; r = np.linalg.norm(V - c, axis=1).max() * 1.02
    ax.set_xlim(c[0] - r, c[0] + r); ax.set_ylim(c[1] - r, c[1] + r); ax.set_zlim(c[2] - r * .6, c[2] + r * .6)
    ax.set_box_aspect((1, 1, .55)); ax.view_init(*view); ax.set_axis_off()


nrow = len(ROWS)
fig = plt.figure(figsize=(8.2, 2.5 * nrow), dpi=125)
for r, (key, disp, view) in enumerate(ROWS):
    axP = fig.add_subplot(nrow, 2, 2 * r + 1)
    ph = _photo(key)
    if ph is not None:
        axP.imshow(ph)
    axP.set_axis_off()
    axP.set_title(f"{disp} — real product photo", fontsize=10, fontweight="bold")
    axM = fig.add_subplot(nrow, 2, 2 * r + 2, projection="3d")
    _render_mesh(axM, key, view)
    axM.set_title("our mesh (from spec)", fontsize=10, fontweight="bold",
                  color=(0.20, 0.34, 0.60))
fig.suptitle("Real product photo vs our spec-built mesh", fontsize=13, fontweight="bold", y=0.997)
fig.tight_layout(rect=[0, 0, 1, 0.985])
os.makedirs(os.path.dirname(OUT), exist_ok=True)
fig.savefig(OUT, dpi=125, facecolor="white"); plt.close(fig)
print(f"✅ {os.path.relpath(OUT)}")
