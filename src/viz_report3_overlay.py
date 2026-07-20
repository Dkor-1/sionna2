# -*- coding: utf-8 -*-
"""viz_report3_overlay.py — report03 용 **인터넷 mesh vs 자작 mesh 시각 비교** 그림.

report03 은 지금까지 '숫자(σ·면적 차이)'로만 대조했는데, 이 그림은 그 대조를 **눈으로** 보여준다:
왼쪽 = 인터넷에서 가져온 실물/커뮤니티 3D 모델, 오른쪽 = 우리가 스펙시트로 만든 같은 기체.
둘을 같은 축척·같은 시점으로 나란히 놓아 형상이 얼마나 겹치는지 확인한다.

출력: outputs/figures/report03_mesh_overlay.png
숫자(σ·면적 차이)는 outputs/{real_cad_compare,community_compare}.json 에서 읽어 캡션에 주입.
"""
from __future__ import annotations

import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
for p in (HERE, os.path.join(ROOT, "benchmark")):
    if p not in sys.path:
        sys.path.insert(0, p)

from mesh_compare import load_reference                          # noqa: E402
from compare_real_cad import ours_body_only                      # noqa: E402
from compare_community import M100, M600, ours_full, load_community  # noqa: E402

OUT = os.path.join(ROOT, "outputs", "figures", "report03_mesh_overlay.png")
REAL = json.load(open(os.path.join(ROOT, "outputs", "real_cad_compare.json")))
COMM = json.load(open(os.path.join(ROOT, "outputs", "community_compare.json")))

C_REF = (0.62, 0.64, 0.68)     # 인터넷 mesh — 중립 회색
C_OURS = (0.30, 0.50, 0.85)    # 자작 mesh — steel-blue (재질색 metal 과 같은 톤)


def _decimate(mesh, cap=55000):
    """표시용 축소 — 무작위 샘플(구멍)이 아니라 quadric decimation(솔리드 유지). 실패 시 원본."""
    if len(mesh.faces) <= cap:
        return mesh
    try:
        return mesh.simplify_quadric_decimation(cap)
    except Exception:
        return mesh


def _panel(ax, mesh, color, title, lim, tcolor="black"):
    m = _decimate(mesh)
    V = np.asarray(m.vertices, float)
    tris = V[np.asarray(m.faces)]
    # z-법선 기반 간단 음영(솔리드가 입체로 보이게)
    nrm = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    ln = np.linalg.norm(nrm, axis=1, keepdims=True); ln[ln < 1e-9] = 1
    sh = 0.5 + 0.5 * np.clip(nrm[:, 2:3] / ln * 0.6 + 0.5, 0, 1)
    fc = np.clip(np.array(color)[None, :] * sh, 0, 1)
    ax.add_collection3d(Poly3DCollection(tris, facecolors=fc, edgecolors="none"))
    ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim); ax.set_zlim(-lim * 0.6, lim * 0.6)
    try:
        ax.set_box_aspect((1, 1, 0.6))
    except Exception:
        pass
    ax.view_init(elev=22, azim=-58)
    ax.set_axis_off()
    ax.set_title(title, fontsize=10.5, fontweight="bold", color=tcolor, pad=1, linespacing=1.35)


# 그림 텍스트는 전부 영어(프로젝트 규약). (name, internet mesh, our mesh, dσ dB, dArea dB, source)
ROWS = [
    ("Yuneec Typhoon H480 — body/frame", load_reference("main_body_remeshed_v3.stl"),
     ours_body_only(), REAL["typhoon"]["d_sigma_db"], REAL["typhoon"]["d_area_db"],
     "real manufacturer CAD (Apache-2.0)"),
    ("DJI Matrice 100 — 2015 quad", load_community("dji_m100.dae"),
     ours_full(M100), COMM["m100"]["d_sigma_db"], COMM["m100"]["d_area_db"],
     "community mesh (visual shell)"),
    ("DJI Matrice 600 Pro — 2016 hexa", load_community("dji_m600.dae"),
     ours_full(M600), COMM["m600"]["d_sigma_db"], COMM["m600"]["d_area_db"],
     "community mesh (visual shell)"),
]

def _rad(m):
    V = np.asarray(m.vertices); c = (V.max(0) + V.min(0)) / 2
    return float(np.linalg.norm(V - c, axis=1).max())


# 짧은 기체 라벨(패널 제목에 넣어 겹침 방지)
SHORT = ["Typhoon H480 (frame)", "Matrice 100 (2015)", "Matrice 600 (2016)"]

nrow = len(ROWS)
fig, axes = plt.subplots(nrow, 2, figsize=(8.4, 3.0 * nrow), dpi=130,
                         subplot_kw=dict(projection="3d"),
                         gridspec_kw=dict(hspace=0.42, wspace=0.02))
for r, (name, ref, ours, dsig, darea, src) in enumerate(ROWS):
    lim = max(_rad(ref), _rad(ours)) * 1.05
    axL, axR = axes[r]
    # 모든 텍스트를 패널 제목에만(matplotlib 이 각 subplot 위에 정확히 배치 → 겹침 없음), 간결하게
    _panel(axL, ref, C_REF,
           f"{SHORT[r]} · internet CAD\n{len(ref.faces):,} faces", lim, tcolor="black")
    _panel(axR, ours, C_OURS,
           f"ours (from spec) · Δσ {dsig:+.1f} dB\n{len(ours.faces):,} faces", lim,
           tcolor=(0.20, 0.34, 0.60))

fig.suptitle("Internet mesh vs our spec-built mesh  (both PEC, shape only)",
             fontsize=13, fontweight="bold", y=0.995)
fig.tight_layout(rect=[0, 0, 1, 0.97])
os.makedirs(os.path.dirname(OUT), exist_ok=True)
fig.savefig(OUT, dpi=130, bbox_inches="tight", facecolor="white")
plt.close(fig)
print(f"✅ {os.path.relpath(OUT)}")
