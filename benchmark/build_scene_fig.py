# -*- coding: utf-8 -*-
"""
build_scene_fig.py — 렌더 두 컷을 주석 달아 한 장으로 (report07_f0).

렌더 자체(f0a/f0b)에는 아무것도 안 그린다 — 주석은 matplotlib 이 위에 얹는다.
그림 안 글자는 최소한의 라벨만(하우스 규약: 그림 글자는 영어), 수치 설명은 캡션·본문이 담는다.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = f"{ROOT}/outputs/figures"
FS = 9.5
plt.rcParams.update({"font.size": FS, "figure.dpi": 200, "savefig.dpi": 200,
                     "font.family": "DejaVu Sans"})

A = mpimg.imread(f"{FIG}/report07_f0a.png")
B = mpimg.imread(f"{FIG}/report07_f0b.png")

fig, axes = plt.subplots(1, 2, figsize=(11.0, 3.9),
                         gridspec_kw={"width_ratios": [1.35, 1.0], "wspace": 0.03})
ax = axes[0]
ax.imshow(A); ax.axis("off")
ax.set_title("(a) Geometry, seen from the side", fontsize=FS)
H, W = A.shape[:2]
# 라벨 — 렌더에서 읽은 위치(드론 우상단, TX/RX 좌하단)
ax.annotate("drone (hovering, origin)", xy=(0.815*W, 0.38*H), xytext=(0.56*W, 0.20*H),
            fontsize=FS-1, arrowprops=dict(arrowstyle="->", lw=1.1))
ax.annotate("TX", xy=(0.185*W, 0.615*H), xytext=(0.10*W, 0.50*H), color="#c62828",
            fontsize=FS-1, arrowprops=dict(arrowstyle="->", color="#c62828", lw=1.1))
ax.annotate("RX", xy=(0.175*W, 0.66*H), xytext=(0.10*W, 0.80*H), color="#2e7d32",
            fontsize=FS-1, arrowprops=dict(arrowstyle="->", color="#2e7d32", lw=1.1))
ax.annotate("", xy=(0.79*W, 0.40*H), xytext=(0.22*W, 0.63*H),
            arrowprops=dict(arrowstyle="<->", color="#455a64", lw=1.2, ls="--"))
ax.text(0.50*W, 0.585*H, "3 m,  el $-15^\\circ$", fontsize=FS-1, color="#455a64",
        ha="center", rotation=-13)

ax = axes[1]
ax.imshow(B); ax.axis("off")
ax.set_title("(b) What the radar sees — belly view", fontsize=FS)
H2, W2 = B.shape[:2]
ax.text(0.245*W2, 0.86*H2, "TX", color="white", fontsize=FS, ha="center", weight="bold")
ax.text(0.755*W2, 0.86*H2, "RX", color="#1b5e20", fontsize=FS, ha="center", weight="bold")

fig.suptitle("Micro-Doppler scenario — DJI Matrice 4E hovering in free space, "
             "quasi-monostatic radar 3 m below-front (Sionna render)",
             fontsize=FS + 0.5, y=1.02)
for e in ("png", "pdf"):
    fig.savefig(f"{FIG}/report07_f0.{e}", bbox_inches="tight", facecolor="white")
print("  ✅ outputs/figures/report07_f0.png")
