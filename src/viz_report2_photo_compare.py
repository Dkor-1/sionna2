# -*- coding: utf-8 -*-
"""viz_report2_photo_compare.py — report2 용 **실제 제품 사진 vs 우리 메쉬** 대조 그림.

왼쪽 = 사용자가 모은 실제 제품 사진(assets/photos/<key>/), 오른쪽 = 우리가 스펙시트로 만든
파라메트릭 메쉬(같은 재질색). 스펙 치수는 그대로 두고 형상을 사진에 맞춰 개선한 결과를 눈으로 검증.
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


def _render_front(key):
    """정면 Mitsuba 렌더(검정 배경)를 로드 → 밝기 알파로 흰 배경 합성 → 내용에 맞춰 크롭.
    렌더는 재질색(흰 동체·주황 짐벌·파랑 모터)을 그대로 쓰므로 사진급이면서 부품이 구분된다."""
    p = os.path.join(ROOT, "outputs", "renders", f"rt_30_drone_{key}_front.png")
    if not os.path.exists(p):
        return None
    im = np.asarray(Image.open(p).convert("RGB"), float) / 255.0
    lum = 0.299 * im[..., 0] + 0.587 * im[..., 1] + 0.114 * im[..., 2]
    a = np.clip((lum - 0.025) / 0.14, 0, 1)                     # 검정→투명, 드론(밝음)→불투명
    comp = im * a[..., None] + (1 - a[..., None])               # 흰 배경 위 합성
    ys, xs = np.where(a > 0.12)                                 # 내용 bbox 로 크롭(여백 제거)
    if len(xs) > 20:
        m = 14
        y0, y1 = max(ys.min() - m, 0), min(ys.max() + m, comp.shape[0])
        x0, x1 = max(xs.min() - m, 0), min(xs.max() + m, comp.shape[1])
        comp = comp[y0:y1, x0:x1]
    return np.clip(comp, 0, 1)


nrow = len(ROWS)
fig = plt.figure(figsize=(8.6, 2.6 * nrow), dpi=128)
for r, (key, disp, _view) in enumerate(ROWS):
    axP = fig.add_subplot(nrow, 2, 2 * r + 1)
    ph = _photo(key)
    if ph is not None:
        axP.imshow(ph)
    axP.set_axis_off()
    axP.set_title(f"{disp} — real product photo", fontsize=10, fontweight="bold")
    axM = fig.add_subplot(nrow, 2, 2 * r + 2)
    rend = _render_front(key)
    if rend is not None:
        axM.imshow(rend)
    axM.set_axis_off()
    axM.set_title("our render (spec-built mesh, front)", fontsize=10, fontweight="bold",
                  color=(0.20, 0.34, 0.60))
fig.suptitle("Real product photo vs our spec-built mesh (photorealistic render, matched front view)",
             fontsize=13, fontweight="bold", y=0.998)
fig.tight_layout(rect=[0, 0, 1, 0.99])
os.makedirs(os.path.dirname(OUT), exist_ok=True)
fig.savefig(OUT, dpi=128, facecolor="white"); plt.close(fig)
print(f"✅ {os.path.relpath(OUT)}")
