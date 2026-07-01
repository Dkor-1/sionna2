# -*- coding: utf-8 -*-
"""
viz_animations.py — 실험별 애니메이션(GIF) 모음 (matplotlib, GPU 불필요)
=========================================================================
이미 있는 GIF: turntable_*(report1), report3_articulation, report4_tracking.
여기서 추가로 만드는 것:
  report2_anim_rcs.png/gif        : 표적 회전 → RCS 글린트 + 조명면 변화 (report2)
  report3_anim_microdoppler.gif   : 회전 프로펠러 + 스펙트로그램 시간커서 (report3)
  report2_anim_occupancy.gif      : 점유 G1→G2→G3 그리드 채움 + 거리분해능 (report2)
"""
from __future__ import annotations
import os
import numpy as np

import vizstyle
vizstyle.use_korean()
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.patches import Polygon as MplPoly
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from drones import DRONES, build_drone, build_propeller, drone_colors
from rcs_po import drone_rcs_pattern, dbsm, C0

FIG = os.path.join(os.path.dirname(__file__), "..", "outputs", "figures")
_NAME = {k: DRONES[k].name.replace("DJI ", "") for k in DRONES}


def _face_geom(mesh):
    V = np.array(mesh.v); F = np.array(mesh.f)
    v0, v1, v2 = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    nrm = np.cross(v1 - v0, v2 - v0)
    area = 0.5 * np.linalg.norm(nrm, axis=1)
    nhat = nrm / (np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-30)
    return V, F, nhat, area


def _look(az_deg, el_deg):
    az, el = np.radians(az_deg), np.radians(el_deg)
    return np.array([np.cos(el)*np.cos(az), np.cos(el)*np.sin(az), np.sin(el)])


# --------------------------------------------------------------------------- #
#  (1) report2 — RCS 글린트 스윕 (표적 회전 시 RCS 출렁 + 조명면)
# --------------------------------------------------------------------------- #
def anim_rcs_aspect(outdir=FIG, target="mavic4pro", fc=3.5e9, el=22.0, n_frames=48, fps=12):
    spec = DRONES[target]; mesh = build_drone(spec)
    V, F, nhat, area = _face_geom(mesh)
    tris0 = [[V[a], V[b], V[c]] for (a, b, c) in mesh.f]
    az_fine = np.arange(0, 360, 2.0)
    sig, _ = drone_rcs_pattern(target, fc, az_fine, el_deg=el)
    rcs_db = dbsm(sig)
    az_frames = np.linspace(0, 360, n_frames, endpoint=False)
    cmap = cm.inferno
    b0, b1 = V.min(0), V.max(0); c = (b0+b1)/2; half = (b1-b0).max()/2

    fig = plt.figure(figsize=(12, 5.6), constrained_layout=True)
    ax3 = fig.add_subplot(1, 2, 1, projection="3d")
    axp = fig.add_subplot(1, 2, 2, projection="polar")
    fig.suptitle(f"RCS 글린트 — {_NAME[target]} 를 레이더가 여러 방위에서 볼 때 @ {fc/1e9:.1f}GHz\n"
                 "왼쪽: 레이더로 향한 면(노랑=강)  ·  오른쪽: RCS(방위) — 특정 각도서 번쩍",
                 fontsize=12.5, fontweight="bold")

    def update(kf):
        azd = az_frames[kf]; u = _look(azd, el)
        proj = nhat @ u; contrib = np.maximum(proj, 0.0)*area
        cn = contrib/(contrib.max()+1e-30)
        cols = [cmap(x) if p > 0 else (0.22, 0.22, 0.25) for x, p in zip(cn, proj)]
        ax3.clear()
        ax3.add_collection3d(Poly3DCollection(tris0, facecolors=cols, edgecolors=(0, 0, 0, 0.12), linewidths=0.1))
        base = c + u*half*1.5; tip = c + u*half*1.05
        ax3.quiver(base[0], base[1], base[2], *(tip-base), color="#1565c0", lw=2.2, arrow_length_ratio=0.3)
        L = half*1.6
        ax3.set_xlim(c[0]-L, c[0]+L); ax3.set_ylim(c[1]-L, c[1]+L); ax3.set_zlim(c[2]-L, c[2]+L)
        try: ax3.set_box_aspect((1, 1, 1))
        except Exception: pass
        ax3.set_axis_off(); ax3.view_init(elev=el, azim=azd)
        # 폴라 RCS
        axp.clear()
        axp.plot(np.radians(az_fine), rcs_db, color="#c62828", lw=1.3)
        cur = dbsm(sig[np.argmin(np.abs(az_fine-azd % 360))])
        axp.plot([np.radians(azd)], [cur], "o", color="#1565c0", ms=11)
        axp.plot([np.radians(azd), np.radians(azd)], [rcs_db.min(), cur], color="#1565c0", lw=1, alpha=0.5)
        axp.set_theta_zero_location("N"); axp.set_theta_direction(-1)
        axp.set_title(f"방위 {azd:.0f}° → RCS {cur:.1f} dBsm", fontsize=11)
        return ()

    anim = FuncAnimation(fig, update, frames=n_frames, blit=False)
    os.makedirs(outdir, exist_ok=True)
    fn = os.path.join(outdir, "report2_anim_rcs.gif")
    anim.save(fn, writer=PillowWriter(fps=fps), dpi=84)
    plt.close(fig); print("[anim]", os.path.relpath(fn)); return fn


# --------------------------------------------------------------------------- #
#  (2) report3 — 회전 프로펠러 + 마이크로도플러 스펙트로그램 커서
# --------------------------------------------------------------------------- #
def anim_microdoppler(outdir=FIG, target="mavic4pro", rpm=6000.0, n_frames=48, fps=12):
    from microdoppler import microdoppler_series, spectrogram
    spec = DRONES[target]
    prf, n_t = 20000.0, 6144
    t, E, info = microdoppler_series(spec, rpm=rpm, prf=prf, n_t=n_t, az=0.0, el=15.0)
    f, tt, Sdb = spectrogram(E, prf, nperseg=64, noverlap=58, nfft=1024)
    # 프로펠러 1개(허브 로컬) 상단투영 폴리곤
    prop = build_propeller(spec, n=12)
    Vp = np.array(prop.v)
    tris = [[Vp[a][:2], Vp[b][:2], Vp[c][:2]] for (a, b, c) in prop.f]  # xy 투영
    R = spec.prop_dia_mm/1000/2
    omega = 2*np.pi*rpm/60.0
    t_frames = np.linspace(tt[0], tt[-1], n_frames)
    u2 = _look(0, 0)[:2]                          # 레이더 LOS(방위 0) 상단투영

    fig, (axm, axs) = plt.subplots(1, 2, figsize=(12.5, 5.4), constrained_layout=True)
    fig.suptitle(f"마이크로-도플러의 원리 — {_NAME[target]} 프로펠러 회전 ↔ 블레이드 플래시\n"
                 f"왼쪽: 회전 프로펠러(파란=레이더 방향)  ·  오른쪽: 스펙트로그램 시간커서 (플래시=블레이드 ⊥ 레이더)",
                 fontsize=12, fontweight="bold")

    def update(kf):
        tk = t_frames[kf]; ph = np.degrees(omega*tk)
        cph, sph = np.cos(np.radians(ph)), np.sin(np.radians(ph))
        Rz = np.array([[cph, -sph], [sph, cph]])
        axm.clear()
        for tri in tris:
            poly = (Rz @ np.array(tri).T).T
            axm.add_patch(MplPoly(poly, closed=True, facecolor="0.2", edgecolor="0.35", lw=0.3))
        axm.arrow(0, 0, u2[0]*R*1.3, u2[1]*R*1.3, color="#1565c0", lw=2.5,
                  head_width=R*0.12, length_includes_head=True, zorder=5)
        axm.text(u2[0]*R*1.45, u2[1]*R*1.1, "레이더", color="#1565c0", fontsize=9)
        axm.set_xlim(-R*1.5, R*1.5); axm.set_ylim(-R*1.5, R*1.5); axm.set_aspect("equal")
        axm.set_axis_off(); axm.set_title(f"t={tk*1e3:.1f} ms · 회전 {ph % 360:.0f}°", fontsize=10.5)
        axs.clear()
        axs.pcolormesh(tt*1e3, f, Sdb, cmap="turbo", vmin=-45, vmax=0, shading="gouraud")
        for sgn in (+1, -1):
            axs.axhline(sgn*info["f_tip"], color="k", ls="--", lw=1.2, zorder=4)
        axs.axvline(tk*1e3, color="w", lw=1.6, zorder=5)
        axs.set_ylim(-1.5*info["f_tip"], 1.5*info["f_tip"])
        axs.set_xlabel("시간 [ms]"); axs.set_ylabel("도플러 [Hz]")
        axs.set_title(f"팁 도플러 ±{info['f_tip']:.0f}Hz · 플래시 {info['flash_hz']:.0f}Hz", fontsize=10.5)
        return ()

    anim = FuncAnimation(fig, update, frames=n_frames, blit=False)
    os.makedirs(outdir, exist_ok=True)
    fn = os.path.join(outdir, "report3_anim_microdoppler.gif")
    anim.save(fn, writer=PillowWriter(fps=fps), dpi=86)
    plt.close(fig); print("[anim]", os.path.relpath(fn)); return fn


# --------------------------------------------------------------------------- #
#  (3) report2 — 점유 G1→G2→G3 그리드 채움 + 거리프로파일
# --------------------------------------------------------------------------- #
def anim_occupancy(outdir=FIG, target="mavic4pro", R=10.0, hold=10, fps=6):
    from waveforms import nr_downlink, CH_COLOR, MODE_DESC
    from radar_process import range_profile, mainlobe_width_m
    modes = ["G1", "G2", "G3"]
    wfs = {m: nr_downlink(occupancy=m) for m in modes}
    sig, _ = drone_rcs_pattern(target, wfs["G3"].carrier_hz, np.array([0.0])); sig = float(sig[0])
    vals = sorted(CH_COLOR.keys())
    cmap = ListedColormap([CH_COLOR[v] for v in vals])
    norm = BoundaryNorm([v-0.5 for v in vals] + [vals[-1]+0.5], cmap.N)
    order = modes * 1
    seq = [m for m in order for _ in range(hold)]

    fig, (axg, axr) = plt.subplots(1, 2, figsize=(13, 5.2), constrained_layout=True)
    fig.suptitle("5G 점유 상태 진행 — 리소스 그리드가 채워질수록 기준신호 대역↑ → 거리분해능↑",
                 fontsize=12.5, fontweight="bold")

    def update(kf):
        m = seq[kf]; wf = wfs[m]
        axg.clear()
        Lg = wf.labels; half = len(wf.used)//2; lo, hi = wf.fft//2-half, wf.fft//2+half
        img = Lg[:, lo:hi].T
        fr = (np.arange(img.shape[0])-img.shape[0]/2)*wf.scs_hz/1e6
        axg.imshow(img, aspect="auto", origin="lower", cmap=cmap, norm=norm,
                   extent=[-0.5, img.shape[1]-0.5, fr[0], fr[-1]], interpolation="nearest")
        axg.set_xlabel("OFDM 심볼", fontsize=8); axg.set_ylabel("기저대역 [MHz]", fontsize=8)
        axg.set_title(f"{m} · {MODE_DESC['nr'][m]} · 점유 {wf.occupancy_frac*100:.0f}%", fontsize=10.5)
        axr.clear()
        rm, prof, pr, pv = range_profile(wf, R, sig, snr_db=18, passive=True, rng=np.random.default_rng(kf))
        pdb = 20*np.log10(prof/prof.max()+1e-12); res = mainlobe_width_m(rm, prof)
        axr.plot(rm, pdb, color="#2e7d32", lw=1.6); axr.axvline(R, color="k", ls="--", lw=1)
        axr.set_xlim(0, 2*R+5); axr.set_ylim(-40, 2)
        axr.set_xlabel("거리 [m]"); axr.set_ylabel("정합필터 [dB]")
        axr.set_title(f"기준 {wf.ref_name} {wf.ref_bw_hz/1e6:.0f}MHz → 분해능 ≈ {res:.1f} m", fontsize=10.5)
        return ()

    anim = FuncAnimation(fig, update, frames=len(seq), blit=False)
    os.makedirs(outdir, exist_ok=True)
    fn = os.path.join(outdir, "report2_anim_occupancy.gif")
    anim.save(fn, writer=PillowWriter(fps=fps), dpi=90)
    plt.close(fig); print("[anim]", os.path.relpath(fn)); return fn


def build_all(outdir=FIG):
    anim_rcs_aspect(outdir)
    anim_microdoppler(outdir)
    anim_occupancy(outdir)
    print("실험 애니메이션 완료 →", os.path.relpath(outdir))


if __name__ == "__main__":
    build_all()
