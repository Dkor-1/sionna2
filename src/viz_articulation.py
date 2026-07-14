# -*- coding: utf-8 -*-
"""
viz_articulation.py — (report3 토대) 분절 드론 **메쉬 검증 도해** (matplotlib)
==============================================================================
생성물 (outputs/figures/, report3_ 접두어)
  report3_articulation.png  : 몸체 자세(RPY) ⟂ 블레이드 회전 분리 — 메쉬 스냅샷 격자(검증)
  report3_articulation.gif  : 몸체가 흔들리는 동안 프로펠러가 도는 회전 애니메이션

⚠ 마이크로도플러 그림은 **여기서 빠졌다**(2026-07-14). 예전엔 이 파일이
  microdoppler_series()(순수 PO, **가림 없음**)로 report3_microdoppler.png 를 그렸는데,
  그건 동체 내부·블레이드 뒷면의 **가려진 면을 정적 산란체로 계상**해 DC 를 부풀린다.
  이제 마이크로도플러는 **SBR(가림 포함)** 로 viz_report3.py 가 그린다.
  이 파일은 '메쉬 자유도 분리'를 눈으로 확인하는 **검증 도해**만 남긴다(공학 도해라 mpl 이 정당).
  같은 실험의 **Sionna 렌더판**은 viz_report3.fig_rt_articulation() 이다.
"""
from __future__ import annotations
import os
import numpy as np

import vizstyle
vizstyle.use_korean()
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from drones import DRONES, pose_articulated, drone_colors

FIG = os.path.join(os.path.dirname(__file__), "..", "outputs", "figures")
_NAME = {k: DRONES[k].name.replace("DJI ", "") for k in DRONES}


def _polys(mesh, cmap):
    V = np.array(mesh.v)
    tris = [[V[a], V[b], V[c]] for (a, b, c) in mesh.f]
    cols = [cmap.get(g, (0.6, 0.6, 0.6)) for g in mesh.g]
    return Poly3DCollection(tris, facecolors=cols, edgecolors=(0, 0, 0, 0.35), linewidths=0.22)


def _equal(ax, mesh, pad=1.05):
    b0, b1 = mesh.bounds(); c = (b0 + b1) / 2; r = (b1 - b0).max() * pad / 2
    ax.set_xlim(c[0]-r, c[0]+r); ax.set_ylim(c[1]-r, c[1]+r); ax.set_zlim(c[2]-r, c[2]+r)
    try: ax.set_box_aspect((1, 1, 1))
    except Exception: pass
    ax.set_axis_off()


# --------------------------------------------------------------------------- #
#  (1) 분절 검증 — 몸체 자세(RPY) ⟂ 블레이드 회전
# --------------------------------------------------------------------------- #
def fig_articulation(outdir=FIG, target="mavic4pro"):
    spec = DRONES[target]; cmap = drone_colors(spec)
    fig = plt.figure(figsize=(15, 7.6), constrained_layout=True)
    fig.suptitle(f"Articulation check — {_NAME[target]}", fontsize=16, fontweight="bold")
    # 1행: 몸체 자세 변화 (프로펠러 위상 0)
    row1 = [("level", (0, 0, 0)), ("roll 30°", (30, 0, 0)),
            ("pitch 30°", (0, 30, 0)), ("yaw 45°", (0, 0, 45))]
    for j, (lab, rpy) in enumerate(row1):
        ax = fig.add_subplot(2, 4, j + 1, projection="3d")
        m = pose_articulated(spec, body_rpy=rpy)
        ax.add_collection3d(_polys(m, cmap)); _equal(ax, m); ax.view_init(elev=20, azim=-60)
        ax.set_title(f"Body {lab}", fontsize=11)
    # 2행: 몸체 수평 고정, 프로펠러만 회전 (위상 증가) → 분리 입증
    for j, ph in enumerate((0, 25, 50, 80)):
        ax = fig.add_subplot(2, 4, 4 + j + 1, projection="3d")
        phases = [ph] * spec.num_rotors
        m = pose_articulated(spec, body_rpy=(0, 0, 0), rotor_phase_deg=phases)
        ax.add_collection3d(_polys(m, cmap)); _equal(ax, m); ax.view_init(elev=58, azim=-60)
        ax.set_title(f"Propeller spin {ph}°", fontsize=11)
    # 각 행의 통제조건(위=몸체만 기울임 / 아래=프로펠러만 회전)은 패널 제목에서 빼고 캡션 한 줄로
    fig.supxlabel("Top row: body tilt only · Bottom row: propellers spin only → the two degrees of freedom are decoupled",
                  fontsize=8.5, color="0.45")
    fn = os.path.join(outdir, "report3_articulation.png"); fig.savefig(fn, dpi=130); plt.close(fig)
    print("[artic]", os.path.relpath(fn)); return fn


# --------------------------------------------------------------------------- #
#  (2) 회전 애니메이션 — 몸체 흔들림 + 프로펠러 스핀 동시
# --------------------------------------------------------------------------- #
def gif_articulation(outdir=FIG, target="mavic4pro", frames=36, fps=18):
    spec = DRONES[target]; cmap = drone_colors(spec)
    n_rot = spec.num_rotors
    fig = plt.figure(figsize=(5.2, 5.2))
    ax = fig.add_subplot(111, projection="3d")
    m0 = pose_articulated(spec)
    b0, b1 = m0.bounds(); c = (b0 + b1) / 2; rr = (b1 - b0).max() * 1.15 / 2

    def update(i):
        ax.clear()
        roll = 18 * np.sin(2 * np.pi * i / frames)
        pitch = 12 * np.sin(4 * np.pi * i / frames)
        yaw = 360.0 * i / frames * 0.25
        spin = (i * 60) % 360                                   # 프로펠러 빠른 스핀
        dirs = [(1 if k % 2 == 0 else -1) for k in range(n_rot)]
        phases = [d * spin for d in dirs]
        m = pose_articulated(spec, body_rpy=(roll, pitch, yaw), rotor_phase_deg=phases)
        ax.add_collection3d(_polys(m, cmap))
        ax.set_xlim(c[0]-rr, c[0]+rr); ax.set_ylim(c[1]-rr, c[1]+rr); ax.set_zlim(c[2]-rr, c[2]+rr)
        try: ax.set_box_aspect((1, 1, 1))
        except Exception: pass
        ax.set_axis_off(); ax.view_init(elev=22, azim=-60)
        ax.set_title(f"{_NAME[target]} — wobble + spin", fontsize=11)
        return ()

    anim = FuncAnimation(fig, update, frames=frames, blit=False)
    os.makedirs(outdir, exist_ok=True)
    fn = os.path.join(outdir, "report3_articulation.gif")
    anim.save(fn, writer=PillowWriter(fps=fps), dpi=84)
    plt.close(fig); print("[artic-gif]", os.path.relpath(fn)); return fn


def build_all(outdir=FIG):
    fig_articulation(outdir)
    gif_articulation(outdir)
    print("분절 검증 도해 완료 →", os.path.relpath(outdir),
          "(마이크로도플러는 viz_report3.py — SBR)")


if __name__ == "__main__":
    build_all()
