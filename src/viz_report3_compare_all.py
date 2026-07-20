# -*- coding: utf-8 -*-
"""viz_report3_compare_all.py — report03: 다운로드 실기체 4종을 한 표에서 통일 비교(결과).

각 행 = 다운로드한 원본(왼쪽) · 그 기체를 우리 방식으로 다시 만든 메쉬(가운데) ·
        형상 일치도(오른쪽, Δ투영면적·Δσ, 둘 다 PEC). 네 기체 모두 ±1 dB 근방이면
        '스펙시트 → 형상 → 밝기' 파이프라인의 눈금이 맞는다는 뜻.
원본: 제조사 실물 CAD(Typhoon)·커뮤니티 메쉬(M100·M600)·실물 0.4mm 스캔(Phantom 4).
출력: outputs/figures/report03_compare_all.png (그림 텍스트 영어 규약).
"""
from __future__ import annotations
import json, os, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, ".."))
for p in (HERE, os.path.join(ROOT, "benchmark")):
    if p not in sys.path:
        sys.path.insert(0, p)

from mesh_compare import load_reference                                    # noqa: E402
from compare_real_cad import ours_body_only                               # noqa: E402
from compare_community import M100, M600, ours_full, load_community        # noqa: E402
from drones import DRONES, build_drone                                     # noqa: E402

REAL = json.load(open(os.path.join(ROOT, "outputs", "real_cad_compare.json")))
COMM = json.load(open(os.path.join(ROOT, "outputs", "community_compare.json")))
PH4 = json.load(open(os.path.join(ROOT, "outputs", "phantom4_scan_compare.json")))
SCAN = np.load(os.path.join(ROOT, "assets", "meshes", "cad", "phantom4_scan_points.npz"))
OUT = os.path.join(ROOT, "outputs", "figures", "report03_compare_all.png")

C_REF = (0.60, 0.62, 0.66)     # 원본 — 중립 회색
C_OURS = (0.30, 0.50, 0.85)    # 우리 재현 — steel-blue(재질색 metal 톤)
C_OK, C_WARN = "#2e7d32", "#e08e0b"


def _decim(m, cap=70000):
    if len(m.faces) <= cap:
        return m
    try:
        return m.simplify_quadric_decimation(cap)
    except Exception:
        return m


def _our_phantom():
    m = build_drone(DRONES["phantom4"]); V = np.asarray(m.v, float); F = np.asarray(m.f)
    keep = np.array([g not in ("prop", "camera") for g in m.g])
    fk = F[keep]; used = np.unique(fk); remap = {o: n for n, o in enumerate(used)}
    return V[used] - (V[used].max(0) + V[used].min(0)) / 2, np.vectorize(remap.get)(fk)


def _mesh_panel(ax, m, color, lim):
    m = _decim(m); V = np.asarray(m.vertices, float); tris = V[np.asarray(m.faces)]
    nrm = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    ln = np.linalg.norm(nrm, axis=1, keepdims=True); ln[ln < 1e-9] = 1
    sh = 0.5 + 0.5 * np.clip(nrm[:, 2:3] / ln * 0.6 + 0.5, 0, 1)
    ax.add_collection3d(Poly3DCollection(tris, facecolors=np.clip(np.array(color)[None, :] * sh, 0, 1), edgecolors="none"))
    _lim3d(ax, lim)


def _tris_panel(ax, V, F, color, lim):
    tris = V[F]
    nrm = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    ln = np.linalg.norm(nrm, axis=1, keepdims=True); ln[ln < 1e-9] = 1
    sh = 0.5 + 0.5 * np.clip(nrm[:, 2:3] / ln * 0.6 + 0.5, 0, 1)
    ax.add_collection3d(Poly3DCollection(tris, facecolors=np.clip(np.array(color)[None, :] * sh, 0, 1), edgecolors="none"))
    _lim3d(ax, lim)


def _pts_panel(ax, P, lim):
    ax.scatter(P[:, 0], P[:, 1], P[:, 2], c=P[:, 2], cmap="viridis", s=1.1, alpha=0.85, linewidths=0)
    _lim3d(ax, lim)


def _lim3d(ax, lim):
    ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim); ax.set_zlim(-lim * 0.6, lim * 0.6)
    ax.set_box_aspect((1, 1, 0.6)); ax.view_init(22, -58); ax.set_axis_off()


def _rad(V):
    c = (V.max(0) + V.min(0)) / 2
    return float(np.linalg.norm(V - c, axis=1).max())


def _result_panel(ax, d):
    vals = [d["d_area_db"], d["d_sigma_db"]]
    cols = [C_OK if abs(v) <= 1.0 else C_WARN for v in vals]
    XL = 4.6                                         # Δarea 가 -3.7 까지 가므로 넉넉히
    ax.axvspan(-1, 1, color=C_OK, alpha=0.13, label="±1 dB")
    ax.axvline(0, color="0.5", lw=0.8)
    y = [1, 0]
    ax.barh(y, vals, color=cols, edgecolor="0.3", height=0.5)
    for yi, v in zip(y, vals):
        # 라벨은 항상 막대 끝의 0 쪽 안에 둔다(축 밖으로 안 나가게)
        inside = v >= 0
        ax.text(v + (-0.12 if inside else 0.12), yi, f"{v:+.2f}", va="center",
                ha="right" if inside else "left", fontsize=9.5, fontweight="bold",
                color="white" if abs(v) > 0.6 else "0.2")
    ax.set_yticks([1, 0]); ax.set_yticklabels(["Δ area", "Δ σ"], fontsize=9)
    ax.set_xlim(-XL, XL * 0.62); ax.set_xticks([-4, -2, -1, 0, 1, 2])
    ax.tick_params(labelsize=7.5); ax.grid(axis="x", alpha=0.25)
    ax.set_xlabel("ours − original  [dB]", fontsize=8)
    ax.text(0.5, -0.48, f"per-az RMS {d['d_sigma_rms_db']:.1f} dB (nulls, not cited)",
            transform=ax.transAxes, ha="center", fontsize=8, color="0.4")


# 두 골드스탠다드 원본만 — 둘 다 깨끗(원판-프롭 없는 프레임/스캔)·실물. (name, source_label, kind)
ROWS = [
    ("Yuneec Typhoon H480 (frame)", "real manufacturer CAD · Apache-2.0", "typhoon"),
    ("DJI Phantom 4 (whole aircraft)", "real 0.4 mm 3D scan · Thingiverse CC-BY", "phantom"),
]

nrow = len(ROWS)
fig = plt.figure(figsize=(11.5, 3.5 * nrow), dpi=128)
gs = fig.add_gridspec(nrow, 3, width_ratios=[1, 1, 0.95], hspace=0.34, wspace=0.05,
                      left=0.02, right=0.98, top=0.85, bottom=0.04)

for r, (name, src, kind) in enumerate(ROWS):
    # 원본 + 우리 재현 준비
    if kind == "typhoon":
        ref = load_reference("main_body_remeshed_v3.stl"); ours = ours_body_only(); d = REAL["typhoon"]
        refV = np.asarray(ref.vertices); ourV = np.asarray(ours.vertices)
    elif kind == "m100":
        ref = load_community("dji_m100.dae"); ours = ours_full(M100); d = COMM["m100"]
        refV = np.asarray(ref.vertices); ourV = np.asarray(ours.vertices)
    elif kind == "m600":
        ref = load_community("dji_m600.dae"); ours = ours_full(M600); d = COMM["m600"]
        refV = np.asarray(ref.vertices); ourV = np.asarray(ours.vertices)
    else:  # phantom (scan points)
        P = SCAN["P"].astype(float); P = P - (P.max(0) + P.min(0)) / 2
        oV, oF = _our_phantom(); d = PH4
        refV, ourV = P, oV

    lim = max(_rad(refV), _rad(ourV)) * 1.03

    axL = fig.add_subplot(gs[r, 0], projection="3d")
    if kind == "phantom":
        _pts_panel(axL, refV, lim)
    else:
        _mesh_panel(axL, ref, C_REF, lim)
    axL.set_title(f"{name}\ndownloaded original · {src}", fontsize=9.5, fontweight="bold")

    axM = fig.add_subplot(gs[r, 1], projection="3d")
    if kind == "phantom":
        _tris_panel(axM, oV, oF, C_OURS, lim)
    else:
        _mesh_panel(axM, ours, C_OURS, lim)
    axM.set_title("rebuilt our way (from spec)", fontsize=9.5, fontweight="bold", color=(0.20, 0.34, 0.60))

    axR = fig.add_subplot(gs[r, 2])
    _result_panel(axR, d)
    axR.set_title("shape match (both PEC)", fontsize=9.5, fontweight="bold")

fig.suptitle("Rebuilt from spec vs a real manufacturer CAD and a real 0.4 mm scan — mean σ within ~1 dB",
             fontsize=12.5, fontweight="bold", y=0.965)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
fig.savefig(OUT, dpi=128, bbox_inches="tight", facecolor="white"); plt.close(fig)
print(f"✅ {os.path.relpath(OUT)}")
