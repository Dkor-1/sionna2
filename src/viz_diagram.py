# -*- coding: utf-8 -*-
"""
viz_diagram.py — '쉽게 이해되는' 도면식 시각화 (matplotlib, Sionna 불필요)
==========================================================================

Sionna 렌더(사진풍)와 별개로, **치수가 또렷이 적힌 공학 도면**을 만든다.
사용자가 "이 드론이 얼마나 크고 어떻게 생겼는지"를 숫자와 함께 한눈에 본다.

만드는 그림
  1) 드론 카드(드론별)   : 3D 색칠 모델 + 위에서 본 도면(대각/프롭원) +
                           옆에서 본 도면(높이) + 제원 표  → outputs/figures/card_*.png
  2) 크기 비교 1장        : 5종을 '같은 축척'으로 나란히 + 대각/무게 막대그래프
                           → outputs/figures/size_compare.png
  3) 차폐시설 도면 1장    : 30×20×11 m 박스 + 흡수체/골조/문 치수
                           → outputs/figures/chamber_schematic.png
"""
from __future__ import annotations

import os
import math
import numpy as np

import vizstyle
vizstyle.use_korean()
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, Rectangle
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from drones import DRONES, build_drone, drone_colors, _motor_angles
from vizstyle import RELEASE_BADGE

FIG = os.path.join(os.path.dirname(__file__), "..", "outputs", "figures")


# --------------------------------------------------------------------------- #
#  메쉬 → 3D 색칠 (Poly3DCollection)
# --------------------------------------------------------------------------- #
def _mesh_polys(mesh, color_map, default=(0.6, 0.6, 0.6)):
    V = np.array(mesh.v)
    tris = [[V[a], V[b], V[c]] for (a, b, c) in mesh.f]
    cols = [color_map.get(g, default) for g in mesh.g]
    pc = Poly3DCollection(tris, facecolors=cols, edgecolors=(0, 0, 0, 0.12),
                          linewidths=0.15)
    return pc


def _set_equal_3d(ax, mesh, pad=1.15):
    b0, b1 = mesh.bounds()
    c = (b0 + b1) / 2
    rng = (b1 - b0).max() * pad / 2
    ax.set_xlim(c[0]-rng, c[0]+rng)
    ax.set_ylim(c[1]-rng, c[1]+rng)
    ax.set_zlim(c[2]-rng, c[2]+rng)
    try:
        ax.set_box_aspect((1, 1, 1))
    except Exception:
        pass


# --------------------------------------------------------------------------- #
#  드론 카드 (드론 1종 = 그림 1장)
# --------------------------------------------------------------------------- #
def drone_card(key, outdir=FIG):
    spec = DRONES[key]
    mesh = build_drone(spec)
    cmap = drone_colors(spec)
    diag = spec.diagonal_mm / 1000.0
    r = diag / 2
    prop_r = spec.prop_dia_mm / 1000.0 / 2

    fig = plt.figure(figsize=(13, 8.2), constrained_layout=True)
    badge, bcol = RELEASE_BADGE.get(spec.release, ("", "#555"))
    fig.suptitle(f"{spec.name}", fontsize=19, fontweight="bold")

    # --- (A) 3D 색칠 모델 ------------------------------------------------- #
    axA = fig.add_subplot(2, 2, 1, projection="3d")
    axA.add_collection3d(_mesh_polys(mesh, cmap))
    _set_equal_3d(axA, mesh)
    axA.view_init(elev=24, azim=-58)
    axA.set_title("3D 모델 (색=부위)", fontsize=12)
    axA.set_xlabel("x (전방)"); axA.set_ylabel("y"); axA.set_zlabel("z")
    axA.tick_params(labelsize=7)

    # --- (B) 위에서 본 도면 : 대각거리 + 프로펠러 원반 -------------------- #
    axB = fig.add_subplot(2, 2, 2)
    axB.set_aspect("equal")
    # 동체
    bl, bw = spec.body_frac*diag*1.15, spec.body_frac*diag*0.85
    axB.add_patch(Rectangle((-bl/2, -bw/2), bl, bw, facecolor=cmap["body"],
                            edgecolor="k", lw=1.2, zorder=3))
    angs = _motor_angles(spec)
    for a in angs:
        mx, my = r*math.cos(math.radians(a)), r*math.sin(math.radians(a))
        axB.plot([0, mx], [0, my], color=(0.15, 0.15, 0.15), lw=2, zorder=2)  # 암
        axB.add_patch(Circle((mx, my), prop_r, fill=False, ls="--",
                             edgecolor="#1565c0", lw=1.0, alpha=0.8, zorder=2))  # 프롭원
        axB.add_patch(Circle((mx, my), 0.03*diag, facecolor="0.2", zorder=4))   # 모터
    # 대각 치수선(마주보는 두 모터)
    a0 = math.radians(angs[0]); a2 = math.radians(angs[len(angs)//2])
    p0 = (r*math.cos(a0), r*math.sin(a0)); p2 = (r*math.cos(a2), r*math.sin(a2))
    axB.annotate("", xy=p0, xytext=p2,
                 arrowprops=dict(arrowstyle="<->", color="#c62828", lw=1.8))
    axB.text(0, 0.06*diag, f"대각 {spec.diagonal_mm:.0f} mm", color="#c62828",
             ha="center", fontsize=11, fontweight="bold",
             bbox=dict(boxstyle="round", fc="white", ec="#c62828", alpha=0.9))
    # 전방 화살표
    lim = (r + prop_r) * 1.2
    axB.annotate("전방", xy=(lim*0.78, 0), xytext=(lim*0.5, 0),
                 arrowprops=dict(arrowstyle="->", color="g", lw=2),
                 color="g", fontsize=10, va="center")
    axB.set_xlim(-lim, lim); axB.set_ylim(-lim, lim)
    axB.set_title("위에서 본 도면 — 점선=프로펠러 회전원", fontsize=12)
    axB.set_xlabel("x [m]"); axB.set_ylabel("y [m]"); axB.grid(alpha=0.25)

    # --- (C) 옆에서 본 도면 : 높이 ---------------------------------------- #
    axC = fig.add_subplot(2, 2, 3)
    axC.set_aspect("equal")
    bh = spec.body_h_mm/1000.0
    b0, b1 = mesh.bounds()
    total_h = (b1[2]-b0[2])
    # 동체 측면(간단 박스) + 메쉬 측면 외곽(x-z 투영 점)
    V = np.array(mesh.v)
    axC.scatter(V[:, 0], V[:, 2], s=2, c="0.5", alpha=0.35)
    axC.add_patch(Rectangle((-bl/2, -0.2*bh), bl, 0.5*bh, facecolor=cmap["body"],
                            edgecolor="k", lw=1.0, zorder=3))
    # 전체 높이 치수
    xline = b1[0] + 0.06*diag
    axC.annotate("", xy=(xline, b0[2]), xytext=(xline, b1[2]),
                 arrowprops=dict(arrowstyle="<->", color="#c62828", lw=1.6))
    axC.text(xline+0.01*diag, (b0[2]+b1[2])/2, f"전체높이\n{total_h*1000:.0f} mm",
             color="#c62828", fontsize=9, va="center")
    axC.axhline(0, color="0.7", lw=0.6, ls=":")
    axC.set_title("옆에서 본 도면 (전방 = 오른쪽)", fontsize=12)
    axC.set_xlabel("x [m]"); axC.set_ylabel("z [m]"); axC.grid(alpha=0.25)

    # --- (D) 제원 표 ------------------------------------------------------ #
    axD = fig.add_subplot(2, 2, 4); axD.axis("off")
    axD.text(0.02, 0.96, badge, transform=axD.transAxes, fontsize=12,
             fontweight="bold", color="white", va="top",
             bbox=dict(boxstyle="round", fc=bcol, ec="none"))
    rows = [
        ("로터 / 암", f"{spec.num_rotors} 개 / {spec.num_rotors} 암"
                       + ("  (옥토콥터)" if spec.num_rotors == 8 else "  (쿼드콥터)")),
        ("대각거리(휠베이스)", f"{spec.diagonal_mm:.0f} mm"),
        ("이륙중량", f"{spec.weight_g:.0f} g"),
        ("프로펠러", f"Ø{spec.prop_dia_mm:.0f} mm × {spec.prop_blades}날 × {spec.num_rotors}"),
        ("언폴드 L×W×H", f"{spec.body_l_mm:.0f} × {spec.body_w_mm:.0f} × {spec.body_h_mm:.0f} mm"),
        ("최고속도", f"{spec.max_speed_ms} m/s" if spec.max_speed_ms else "—"),
        ("RTK(정밀측위)", "예" if spec.rtk else "아니오"),
        ("착륙장치", {"none":"없음(암 접지)","feet":"소형 발","legs":"고정 다리",
                       "tall":"격납형 다리"}.get(spec.gear, spec.gear)),
        ("자료 신뢰도", {"high":"높음","medium":"보통","low":"낮음"}.get(spec.confidence)),
    ]
    y = 0.85
    for k, v in rows:
        axD.text(0.02, y, k, transform=axD.transAxes, fontsize=10.5, color="#444")
        axD.text(0.46, y, v, transform=axD.transAxes, fontsize=10.5, fontweight="bold")
        y -= 0.087
    axD.text(0.02, y-0.01, "주의: " + spec.note, transform=axD.transAxes,
             fontsize=8.4, color="#b71c1c", va="top", wrap=True)

    os.makedirs(outdir, exist_ok=True)
    fn = os.path.join(outdir, f"card_{key}.png")
    fig.savefig(fn, dpi=135); plt.close(fig)
    print("[card]", os.path.relpath(fn))
    return fn


# --------------------------------------------------------------------------- #
#  5종 크기 비교 (같은 축척)
# --------------------------------------------------------------------------- #
def size_comparison(outdir=FIG):
    keys = list(DRONES.keys())
    specs = [DRONES[k] for k in keys]
    fig = plt.figure(figsize=(14, 8.5), constrained_layout=True)
    gs = fig.add_gridspec(2, 2, height_ratios=[1.5, 1])

    # (위) 같은 축척 평면 비교 — 프로펠러 회전원 기준
    axT = fig.add_subplot(gs[0, :]); axT.set_aspect("equal")
    maxspan = max((s.diagonal_mm/1000 + s.prop_dia_mm/1000) for s in specs)
    x = 0.0
    for s in specs:
        diag = s.diagonal_mm/1000; r = diag/2; pr = s.prop_dia_mm/1000/2
        span = diag + 2*pr
        cx = x + maxspan*0.62
        for a in _motor_angles(s):
            mx = cx + r*math.cos(math.radians(a)); my = r*math.sin(math.radians(a))
            axT.add_patch(Circle((mx, my), pr, facecolor=s.body_rgb, alpha=0.30,
                                 edgecolor=s.body_rgb, lw=1.2))
            axT.plot([cx, mx], [0, my], color="0.3", lw=1.2)
        axT.add_patch(Circle((cx, 0), 0.04*diag, facecolor="0.2"))
        axT.text(cx, -maxspan*0.62, f"{s.name.split('  ')[0]}\n대각 {s.diagonal_mm:.0f}mm · {s.weight_g:.0f}g",
                 ha="center", va="top", fontsize=9.5)
        x += maxspan*1.24
    axT.set_xlim(-maxspan*0.1, x); axT.set_ylim(-maxspan*0.8, maxspan*0.62)
    axT.set_title("5종 드론 크기 비교 (같은 축척 · 점선원=프로펠러 회전영역)",
                  fontsize=14, fontweight="bold")
    axT.set_xlabel("← S1000+ 가 압도적으로 큼  (1 칸 ≈ 1.4 m)"); axT.set_yticks([])

    # (아래좌) 대각거리 막대
    axL = fig.add_subplot(gs[1, 0])
    names = [s.name.split("  ")[0].replace("DJI ", "") for s in specs]
    dias = [s.diagonal_mm for s in specs]
    cols = [s.body_rgb if max(s.body_rgb) < 0.9 else (0.6, 0.6, 0.65) for s in specs]
    axL.barh(names, dias, color=cols, edgecolor="k")
    for i, d in enumerate(dias):
        axL.text(d+10, i, f"{d:.0f}", va="center", fontsize=9)
    axL.set_title("대각거리 [mm]", fontsize=12); axL.invert_yaxis(); axL.grid(axis="x", alpha=0.3)

    # (아래우) 무게 막대 (로그축 — 250g~4400g)
    axR = fig.add_subplot(gs[1, 1])
    wts = [s.weight_g for s in specs]
    axR.barh(names, wts, color=cols, edgecolor="k")
    for i, w in enumerate(wts):
        axR.text(w*1.03, i, f"{w:.0f} g", va="center", fontsize=9)
    axR.set_xscale("log"); axR.set_title("이륙중량 [g, 로그축]", fontsize=12)
    axR.invert_yaxis(); axR.grid(axis="x", alpha=0.3)

    os.makedirs(outdir, exist_ok=True)
    fn = os.path.join(outdir, "size_compare.png")
    fig.savefig(fn, dpi=135); plt.close(fig)
    print("[size]", os.path.relpath(fn))
    return fn


# --------------------------------------------------------------------------- #
#  차폐시설 도면
# --------------------------------------------------------------------------- #
def chamber_schematic(outdir=FIG, W=30, D=20, H=11, ab_h=0.4):
    fig = plt.figure(figsize=(13, 6), constrained_layout=True)
    fig.suptitle("대형 차폐시설(전파무반사실) — 30 m × 20 m × 11 m", fontsize=16, fontweight="bold")

    # (좌) 평면도
    ax1 = fig.add_subplot(1, 2, 1); ax1.set_aspect("equal")
    ax1.add_patch(Rectangle((0, 0), W, D, fill=False, edgecolor="k", lw=2))
    ax1.add_patch(Rectangle((ab_h, ab_h), W-2*ab_h, D-2*ab_h, fill=True,
                            facecolor="#eef3fb", edgecolor="#1565c0", ls="--", lw=1))
    # 흡수체 빗금(테두리)
    for x in np.arange(0, W, 0.8):
        ax1.plot([x, x+ab_h], [0, ab_h], color="0.6", lw=0.5)
        ax1.plot([x, x+ab_h], [D, D-ab_h], color="0.6", lw=0.5)
    ax1.text(W/2, D/2, "실내 사용공간\n(전파흡수체로 둘러싸인 무반사 영역)",
             ha="center", va="center", fontsize=10, color="#1565c0")
    ax1.annotate("", xy=(0, -1.2), xytext=(W, -1.2),
                 arrowprops=dict(arrowstyle="<->", lw=1.5))
    ax1.text(W/2, -2.2, f"{W:.0f} m", ha="center", fontsize=11, fontweight="bold")
    ax1.annotate("", xy=(-1.2, 0), xytext=(-1.2, D),
                 arrowprops=dict(arrowstyle="<->", lw=1.5))
    ax1.text(-2.4, D/2, f"{D:.0f} m", va="center", rotation=90, fontsize=11, fontweight="bold")
    # 문 2개(뒷벽)
    for xc in (W*0.40, W*0.62):
        ax1.add_patch(Rectangle((xc-1, D-0.2), 2, 0.4, facecolor="#90a4ae", edgecolor="k"))
    ax1.text(W*0.51, D+0.5, "출입문 ×2", ha="center", fontsize=9)
    ax1.set_xlim(-4, W+2); ax1.set_ylim(-3.5, D+2); ax1.axis("off")
    ax1.set_title("평면도 (위에서)", fontsize=12)

    # (우) 입면도(단면)
    ax2 = fig.add_subplot(1, 2, 2); ax2.set_aspect("equal")
    ax2.add_patch(Rectangle((0, 0), W, H, fill=False, edgecolor="k", lw=2))
    # 천장/벽 흡수체(피라미드 빗금)
    for x in np.arange(0, W, 0.7):
        ax2.plot([x, x+0.35, x+0.7], [H, H-ab_h, H], color="0.55", lw=0.5)  # 천장
    for z in np.arange(0, H, 0.7):
        ax2.plot([0, ab_h, 0], [z, z+0.35, z+0.7], color="0.55", lw=0.5)    # 좌벽
        ax2.plot([W, W-ab_h, W], [z, z+0.35, z+0.7], color="0.55", lw=0.5)  # 우벽
    ax2.add_patch(Rectangle((0, 0), W, 0.25, facecolor="0.85", edgecolor="k"))  # 바닥타일
    ax2.annotate("", xy=(W+1.2, 0), xytext=(W+1.2, H),
                 arrowprops=dict(arrowstyle="<->", lw=1.5))
    ax2.text(W+1.8, H/2, f"{H:.0f} m", va="center", rotation=90, fontsize=11, fontweight="bold")
    ax2.text(W/2, H*0.55, "← 4면 벽 + 천장 = 전파흡수체\n바닥 = 체커보드 타일",
             ha="center", fontsize=9, color="#444")
    ax2.set_xlim(-1, W+4); ax2.set_ylim(-1, H+1.5); ax2.axis("off")
    ax2.set_title("입면도 (단면)", fontsize=12)

    os.makedirs(outdir, exist_ok=True)
    fn = os.path.join(outdir, "chamber_schematic.png")
    fig.savefig(fn, dpi=135); plt.close(fig)
    print("[chamber]", os.path.relpath(fn))
    return fn


if __name__ == "__main__":
    chamber_schematic()
    size_comparison()
    for k in DRONES:
        drone_card(k)
    print("모든 도면 생성 완료 →", os.path.relpath(FIG))
