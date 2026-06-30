# -*- coding: utf-8 -*-
"""
viz_articulation.py — (report3 토대) 분절 드론 + 마이크로도플러 **메쉬 시각화**
==============================================================================
생성물 (outputs/figures/, report3_ 접두어)
  report3_articulation.png  : 몸체 자세(RPY) ⟂ 블레이드 회전 분리 — 메쉬 스냅샷 격자(검증)
  report3_microdoppler.png  : 회전 블레이드의 마이크로도플러 스펙트로그램(블레이드 플래시)
  report3_articulation.gif  : 몸체가 흔들리는 동안 프로펠러가 도는 회전 애니메이션
"""
from __future__ import annotations
import os
import numpy as np

import vizstyle
vizstyle.use_korean()
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.animation import FuncAnimation, PillowWriter
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from drones import DRONES, pose_articulated, drone_colors
from microdoppler import microdoppler_series, spectrogram

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
    fig.suptitle(f"분절(articulation) 검증 — {_NAME[target]}: 몸체 자세(롤·피치·요)와 프로펠러 회전은 독립",
                 fontsize=14, fontweight="bold")
    # 1행: 몸체 자세 변화 (프로펠러 위상 0)
    row1 = [("수평(level)", (0, 0, 0)), ("롤 30°", (30, 0, 0)),
            ("피치 30°", (0, 30, 0)), ("요 45°", (0, 0, 45))]
    for j, (lab, rpy) in enumerate(row1):
        ax = fig.add_subplot(2, 4, j + 1, projection="3d")
        m = pose_articulated(spec, body_rpy=rpy)
        ax.add_collection3d(_polys(m, cmap)); _equal(ax, m); ax.view_init(elev=20, azim=-60)
        ax.set_title(f"몸체 {lab}\n(프로펠러 위상 0)", fontsize=9.5)
    # 2행: 몸체 수평 고정, 프로펠러만 회전 (위상 증가) → 분리 입증
    for j, ph in enumerate((0, 25, 50, 80)):
        ax = fig.add_subplot(2, 4, 4 + j + 1, projection="3d")
        phases = [ph] * spec.num_rotors
        m = pose_articulated(spec, body_rpy=(0, 0, 0), rotor_phase_deg=phases)
        ax.add_collection3d(_polys(m, cmap)); _equal(ax, m); ax.view_init(elev=58, azim=-60)
        ax.set_title(f"프로펠러 스핀 {ph}°\n(몸체 수평 고정)", fontsize=9.5)
    fig.text(0.5, 0.005, "위: 몸체만 기울임(프로펠러 정지)   ·   아래: 몸체 고정 + 프로펠러만 회전  "
             "→ 두 자유도가 분리됨(몸체 RPY 와 블레이드 스핀이 독립)", ha="center", fontsize=10, color="#1565c0")
    fn = os.path.join(outdir, "report3_articulation.png"); fig.savefig(fn, dpi=130); plt.close(fig)
    print("[artic]", os.path.relpath(fn)); return fn


# --------------------------------------------------------------------------- #
#  (2) 마이크로도플러 스펙트로그램
# --------------------------------------------------------------------------- #
def fig_microdoppler(outdir=FIG, targets=("mavic4pro", "s1000plus"),
                     rpm=6000.0, prf=20000.0, n_t=6144):
    fig, axes = plt.subplots(1, len(targets), figsize=(14, 5.4), constrained_layout=True)
    if len(targets) == 1:
        axes = [axes]
    fig.suptitle("회전 프로펠러의 마이크로-도플러 — 표적이 호버해도 블레이드가 만드는 시간변조 후방산란\n"
                 "(세로 줄무늬=블레이드 플래시, 검은 점선=±팁 도플러 한계, 정적 몸체 0-도플러는 클러터로 제거)  PO 복소장 E(t) STFT",
                 fontsize=12.5, fontweight="bold")
    for ax, key in zip(axes, targets):
        spec = DRONES[key]
        t, E, info = microdoppler_series(spec, rpm=rpm, prf=prf, n_t=n_t, az=0.0, el=15.0)
        # 짧은 윈도우(<플래시 주기) → 블레이드 플래시·사인 도플러 트랙이 드러남(특유의 마이크로도플러)
        f, tt, Sdb = spectrogram(E, prf, nperseg=64, noverlap=58, nfft=1024)
        im = ax.pcolormesh(tt * 1e3, f, Sdb, cmap="turbo", vmin=-45, vmax=0, shading="gouraud")
        for sgn in (+1, -1):
            ax.axhline(sgn * info["f_tip"], color="k", ls="--", lw=1.8, zorder=5)
        ax.text(tt[-1] * 1e3 * 0.99, info["f_tip"], f" 팁 도플러 +{info['f_tip']:.0f}Hz",
                color="k", fontsize=8, ha="right", va="bottom", zorder=6)
        ax.set_ylim(-1.5 * info["f_tip"], 1.5 * info["f_tip"])
        ax.set_xlabel("시간 [ms]"); ax.set_ylabel("도플러 주파수 [Hz]")
        ax.set_title(f"{_NAME[key]}  ·  로터 {info['n_rotors']}개 @ {rpm:.0f}rpm\n"
                     f"팁속도 {info['v_tip']:.0f}m/s → f_tip≈±{info['f_tip']:.0f}Hz · 플래시 {info['flash_hz']:.0f}Hz",
                     fontsize=10)
        fig.colorbar(im, ax=ax, fraction=0.046, label="정규화 세기 [dB]")
    fig.text(0.5, -0.02, "※ f_tip 이 수백~수천 Hz → 모호 없이 보려면 PRF≳2·f_tip(수 kHz↑) 필요. "
             "5G SSB(50Hz)/CSI-RS(200Hz)/LTE CRS(1kHz) 파일럿률로는 블레이드 도플러가 접힘.",
             ha="center", fontsize=9.5, color="#444")
    fn = os.path.join(outdir, "report3_microdoppler.png"); fig.savefig(fn, dpi=130, bbox_inches="tight")
    plt.close(fig); print("[micro]", os.path.relpath(fn)); return fn


# --------------------------------------------------------------------------- #
#  (3) 회전 애니메이션 — 몸체 흔들림 + 프로펠러 스핀 동시
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
        ax.set_title(f"{_NAME[target]} — 몸체 RPY 흔들림 + 프로펠러 스핀", fontsize=10)
        return ()

    anim = FuncAnimation(fig, update, frames=frames, blit=False)
    os.makedirs(outdir, exist_ok=True)
    fn = os.path.join(outdir, "report3_articulation.gif")
    anim.save(fn, writer=PillowWriter(fps=fps), dpi=84)
    plt.close(fig); print("[artic-gif]", os.path.relpath(fn)); return fn


def build_all(outdir=FIG):
    fig_articulation(outdir)
    fig_microdoppler(outdir)
    gif_articulation(outdir)
    print("분절/마이크로도플러 시각화 완료 →", os.path.relpath(outdir))


if __name__ == "__main__":
    build_all()
