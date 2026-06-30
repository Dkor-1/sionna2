# -*- coding: utf-8 -*-
"""
viz_mesh.py — (report2) **드론 메쉬를 주인공으로** 한 실험 시각화 (matplotlib 3D)
=================================================================================

report2 의 분석 실험들을 추상 그래프가 아니라, report1 에서 만든 **실제 3D 메쉬** 위에
얹어 '예쁘게' 보여준다. 모든 그림이 드론 메쉬를 중심에 둔다(GPU 불필요).

생성물 (outputs/figures/, report2_mesh_ 접두어)
  report2_mesh_setup.png    : 모노스태틱 측정 3D 장면 (챔버 + 드론메쉬 + 안테나 + 빔 + 원거리장)
  report2_mesh_rcs_balloon.png : 드론별 RCS '풍선'(방위×고각 3D 패턴)을 메쉬 둘레에 — 글린트가 보임
  report2_mesh_rcs_facets.png  : 시선별로 '번쩍이는 면(조명면)'을 메쉬에 색칠 (PO 가 더하는 면)
  report2_mesh_doppler.png  : 드론메쉬 + 속도벡터 + 표준별 파일럿반복률→최대속도(v_max=PRF·λ/4)

좌표: 드론 로컬 z-up, 전방 = +x (drones.py 와 동일). RCS 시선 û 도 같은 프레임.
"""
from __future__ import annotations
import os
import numpy as np

import vizstyle
vizstyle.use_korean()
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.colors import Normalize
from mpl_toolkits.mplot3d.art3d import Poly3DCollection, Line3DCollection

from drones import DRONES, build_drone, drone_colors
from rcs_po import mesh_to_points, rcs_from_points, dbsm, C0
from waveforms import PILOT_RATE_HZ

FIG = os.path.join(os.path.dirname(__file__), "..", "outputs", "figures")

# radar_scene.py 와 동일한 모노스태틱 기하(여기선 sionna/mitsuba import 회피 위해 직접 명시)
ANT_POS = (2.0, 10.0, 5.5)
TGT_POS = (12.0, 10.0, 5.5)

_COL = {"mini5pro": "#1565c0", "mavic4pro": "#2e7d32", "matrice4e": "#ef6c00",
        "s1000plus": "#000000", "phantom4": "#c62828"}
_NAME = {k: DRONES[k].name.replace("DJI ", "") for k in DRONES}


# --------------------------------------------------------------------------- #
#  메쉬 → matplotlib 3D 보조
# --------------------------------------------------------------------------- #
def _mesh_polys(mesh, cmap, default=(0.6, 0.6, 0.6), alpha=1.0, ec=(0, 0, 0, 0.12), lw=0.15):
    V = np.array(mesh.v)
    tris = [[V[a], V[b], V[c]] for (a, b, c) in mesh.f]
    cols = [cmap.get(g, default) for g in mesh.g]
    return Poly3DCollection(tris, facecolors=cols, edgecolors=ec, linewidths=lw, alpha=alpha)


def _equal_3d(ax, lo, hi, pad=1.05):
    c = (np.asarray(lo) + np.asarray(hi)) / 2
    r = (np.asarray(hi) - np.asarray(lo)).max() * pad / 2
    ax.set_xlim(c[0]-r, c[0]+r); ax.set_ylim(c[1]-r, c[1]+r); ax.set_zlim(c[2]-r, c[2]+r)
    try: ax.set_box_aspect((1, 1, 1))
    except Exception: pass


def _scaled_mesh_verts(mesh, target_extent, center=(0, 0, 0)):
    """메쉬를 원점 중심으로 옮기고 최대치수가 target_extent 가 되게 스케일한 꼭짓점."""
    V = np.array(mesh.v)
    b0, b1 = V.min(0), V.max(0)
    c = (b0 + b1) / 2
    s = target_extent / max((b1 - b0).max(), 1e-9)
    return (V - c) * s + np.asarray(center), s


def _face_geom(mesh):
    V = np.array(mesh.v); F = np.array(mesh.f)
    v0, v1, v2 = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    nrm = np.cross(v1 - v0, v2 - v0)
    area = 0.5 * np.linalg.norm(nrm, axis=1)
    nhat = nrm / (np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-30)
    cen = (v0 + v1 + v2) / 3.0
    return V, F, cen, nhat, area


# --------------------------------------------------------------------------- #
#  (1) 모노스태틱 측정 3D 장면 — 챔버 + 드론메쉬 + 안테나 + 빔
# --------------------------------------------------------------------------- #
def fig_setup_3d(outdir=FIG, target="phantom4", fc=3.5e9, exagg=12.0):
    from rcs_po import C0 as _c
    W, D, H = 30.0, 20.0, 11.0
    R = abs(TGT_POS[0] - ANT_POS[0])
    spec = DRONES[target]
    mesh = build_drone(spec)
    Dext = max(np.array(mesh.v).max(0) - np.array(mesh.v).min(0))      # 표적 크기 D[m]
    rff = 2 * Dext**2 / (_c / fc)

    fig = plt.figure(figsize=(13, 7.6), constrained_layout=True)
    ax = fig.add_subplot(111, projection="3d")
    fig.suptitle("모노스태틱 측정 장면 — 안테나(한쪽 끝) ↔ 드론(quiet zone)",
                 fontsize=15, fontweight="bold")

    # 챔버 와이어프레임(반투명) + 바닥 체커 격자 느낌
    corners = np.array([[0,0,0],[W,0,0],[W,D,0],[0,D,0],[0,0,H],[W,0,H],[W,D,H],[0,D,H]], float)
    edges = [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]
    ax.add_collection3d(Line3DCollection([[corners[a], corners[b]] for a,b in edges],
                                         colors="0.55", linewidths=1.0))
    for gx in np.arange(0, W+0.1, 5):
        ax.plot([gx, gx], [0, D], [0, 0], color="0.85", lw=0.5)
    for gy in np.arange(0, D+0.1, 5):
        ax.plot([0, W], [gy, gy], [0, 0], color="0.85", lw=0.5)

    # 안테나(빨간 콘 마커) — 모노스태틱 TX≈RX
    ax.scatter(*ANT_POS, s=180, marker="^", color="#c62828", depthshade=False, zorder=5)
    ax.text(ANT_POS[0]-1.0, ANT_POS[1], ANT_POS[2]-3.0, "모노스태틱\n안테나(TX≈RX)",
            color="#c62828", fontsize=9, ha="center")

    # 빔(왕복) 화살표
    ax.quiver(*ANT_POS, *(np.array(TGT_POS)-np.array(ANT_POS)), color="#1565c0",
              lw=2.2, arrow_length_ratio=0.06)
    ax.text((ANT_POS[0]+TGT_POS[0])/2, 10, 7.6, f"R = {R:.0f} m  (왕복 2R/c)",
            color="#1565c0", fontsize=10, ha="center")

    # 드론 메쉬(보이게 ×exagg 확대) — 실제 위치 quiet zone
    Vs, s = _scaled_mesh_verts(mesh, target_extent=Dext*exagg, center=TGT_POS)
    tris = [[Vs[a], Vs[b], Vs[c]] for (a,b,c) in mesh.f]
    cmap = drone_colors(spec)
    cols = [cmap.get(g, (0.6,0.6,0.6)) for g in mesh.g]
    ax.add_collection3d(Poly3DCollection(tris, facecolors=cols, edgecolors=(0,0,0,0.15), linewidths=0.1))
    ax.text(TGT_POS[0], TGT_POS[1], TGT_POS[2]+2.6,
            f"표적: {_NAME[target]}\n(메쉬 ×{exagg:.0f} 확대표시)", color="k", fontsize=9, ha="center")

    # 원거리장 점검 박스
    ok = "OK (far-field 만족)" if rff <= R else "NG (챔버 부족)"
    ax.text2D(0.01, 0.02,
              "원거리장 " r"$2D^2/\lambda$" f" @ {fc/1e9:.1f}GHz:  D={Dext:.2f}m → R_ff={rff:.1f}m  vs  R={R:.0f}m  [{ok}]",
              transform=ax.transAxes, fontsize=9.5, color="#333",
              bbox=dict(boxstyle="round", fc="#eef3fb", ec="#1565c0", alpha=0.9))

    ax.set_xlim(0, W); ax.set_ylim(0, D); ax.set_zlim(0, H)        # 방 실제 비율
    try: ax.set_box_aspect((W, D, H))
    except Exception: pass
    ax.set_xlabel("x [m] (전방)"); ax.set_ylabel("y [m]"); ax.set_zlabel("z [m]")
    ax.view_init(elev=18, azim=-62); ax.tick_params(labelsize=7)
    fn = os.path.join(outdir, "report2_mesh_setup.png"); fig.savefig(fn, dpi=130); plt.close(fig)
    print("[mesh]", os.path.relpath(fn)); return fn


# --------------------------------------------------------------------------- #
#  (2) RCS '풍선' — 방위×고각 3D 패턴을 메쉬 둘레에
# --------------------------------------------------------------------------- #
def _rcs_grid(key, fc, az, el, spacing=None):
    """드론 1종의 σ(el, az)[m²] 격자. 점구름 한 번 만들고 el 별로 az 벡터화."""
    lam = C0 / fc; spacing = spacing or lam / 6.0
    mesh = build_drone(DRONES[key])
    P, N, dA = mesh_to_points(mesh, spacing)
    S = np.zeros((len(el), len(az)))
    for i, e in enumerate(el):
        S[i] = rcs_from_points(P, N, dA, fc, az, e)
    return S, mesh


def _balloon_xyz(S_db, az, el, floor_db):
    """dBsm 격자 → 단위반경 풍선 좌표 (X,Y,Z) 와 정규화 색값 [0,1]."""
    ceil_db = S_db.max()
    rng = max(ceil_db - floor_db, 1e-6)
    r = np.clip((S_db - floor_db) / rng, 0.0, 1.0)            # (nel, naz) 0..1
    AZ, EL = np.meshgrid(np.radians(az), np.radians(el))
    X = r * np.cos(EL) * np.cos(AZ)
    Y = r * np.cos(EL) * np.sin(AZ)
    Z = r * np.sin(EL)
    return X, Y, Z, r


def fig_rcs_balloon(outdir=FIG, fc=3.5e9):
    az = np.arange(0, 361, 5.0)                              # 닫힌 둘레(360 포함)
    el = np.arange(-80, 81, 8.0)
    keys = list(DRONES.keys())
    fig = plt.figure(figsize=(15, 9.2), constrained_layout=True)
    fig.suptitle(f"드론 RCS '풍선' — 메쉬 둘레의 방위×고각 후방산란 패턴 @ {fc/1e9:.1f} GHz (PO)\n"
                 "반경·색 = RCS[dBsm].  뾰족한 로브 = 글린트(특정 각도서 번쩍).  ＋ = 전방(+x)",
                 fontsize=14, fontweight="bold")
    cmap = cm.turbo
    norm = None
    for j, key in enumerate(keys):
        ax = fig.add_subplot(2, 3, j+1, projection="3d")
        S, mesh = _rcs_grid(key, fc, az, el)
        Sdb = dbsm(S)
        floor = Sdb.max() - 25.0                             # 상위 25 dB 동적범위
        X, Y, Z, r = _balloon_xyz(Sdb, az, el, floor)
        norm = Normalize(vmin=floor, vmax=Sdb.max())
        ax.plot_surface(X, Y, Z, facecolors=cmap(norm(Sdb)), rstride=1, cstride=1,
                        linewidth=0, antialiased=True, alpha=0.45, shade=False)  # 반투명→메쉬 비침
        # 메쉬(중심에, 풍선 사이로 보이게)
        Vs, _ = _scaled_mesh_verts(mesh, target_extent=0.62)
        dc = drone_colors(DRONES[key])
        tris = [[Vs[a], Vs[b], Vs[c]] for (a, b, c) in mesh.f]
        ax.add_collection3d(Poly3DCollection(tris, facecolors=[dc.get(g,(.6,.6,.6)) for g in mesh.g],
                                             edgecolors=(0,0,0,0.10), linewidths=0.08))
        ax.quiver(0, 0, 0, 1.15, 0, 0, color="g", lw=1.5, arrow_length_ratio=0.12)  # 전방
        ax.text(1.25, 0, 0, "＋", color="g", fontsize=11)
        ax.set_title(f"{_NAME[key]}\n평균 {dbsm(S.mean()):.0f} · 최대 {Sdb.max():.0f} dBsm",
                     fontsize=10)
        _equal_3d(ax, [-1,-1,-1], [1,1,1], pad=1.0)
        ax.set_axis_off(); ax.view_init(elev=22, azim=-60)
    # 마지막 칸: 설명 + 컬러바
    axL = fig.add_subplot(2, 3, 6); axL.axis("off")
    sm = cm.ScalarMappable(cmap=cmap, norm=Normalize(0, 1)); sm.set_array([])
    cb = fig.colorbar(sm, ax=axL, fraction=0.5, aspect=12)
    cb.set_label("정규화 RCS (각 드론 최대=1.0,  하위 -25 dB)", fontsize=9)
    axL.text(0.0, 0.92,
             "읽는 법\n"
             "• 풍선이 클수록(바깥) 그 방향 RCS 큼\n"
             "• 뾰족한 돌출 = 글린트(평판·암이 거울처럼 반사)\n"
             "• 쿼드(4암 X자)는 90° 주기 로브, 옥토(S1000+)는\n"
             "  더 촘촘·전체적으로 큼\n"
             "• 메쉬의 +x(초록 화살표)가 전방 기준",
             transform=axL.transAxes, fontsize=10, va="top")
    fn = os.path.join(outdir, "report2_mesh_rcs_balloon.png"); fig.savefig(fn, dpi=130); plt.close(fig)
    print("[mesh]", os.path.relpath(fn)); return fn


# --------------------------------------------------------------------------- #
#  (3) 조명면(번쩍이는 면) — 시선별 PO 기여를 메쉬에 색칠
# --------------------------------------------------------------------------- #
def _look_dir(az_deg, el_deg):
    az, el = np.radians(az_deg), np.radians(el_deg)
    return np.array([np.cos(el)*np.cos(az), np.cos(el)*np.sin(az), np.sin(el)])


def fig_rcs_facets(outdir=FIG, target="phantom4", fc=3.5e9, aspects=(0, 45, 90), el=34.0):
    """레이더를 살짝 위(el)에서 보게 해서 윗면/측면 조명면이 카메라를 향하도록 한다.
    (el=0 수평이면 평평한 드론의 조명면이 얇게 보여 오해를 부름.)"""
    spec = DRONES[target]; mesh = build_drone(spec)
    V, F, cen, nhat, area = _face_geom(mesh)
    tris0 = [[V[a], V[b], V[c]] for (a, b, c) in mesh.f]
    b0, b1 = V.min(0), V.max(0); c = (b0 + b1) / 2; half = (b1 - b0).max() / 2
    fig = plt.figure(figsize=(15, 5.6), constrained_layout=True)
    fig.suptitle(f"'번쩍이는 면' — {_NAME[target]} 를 보는 각도에 따라 빛나는(레이더로 향한) 면 @ {fc/1e9:.1f} GHz\n"
                 "색 = PO 기여 " r"$(\hat{n}\cdot\hat{u})\,\Delta A$"
                 "  (노랑=강, 보라=약, 회색=뒷면).  파란 화살표 = 레이더 입사 방향(카메라가 레이더 위치)",
                 fontsize=13, fontweight="bold")
    cmap = cm.inferno
    for j, azd in enumerate(aspects):
        ax = fig.add_subplot(1, len(aspects), j+1, projection="3d")
        u = _look_dir(azd, el)                               # 표적→레이더 (살짝 위에서)
        proj = nhat @ u
        contrib = np.maximum(proj, 0.0) * area
        cn = contrib / (contrib.max() + 1e-30)
        cols = [cmap(c2) if p > 0 else (0.22, 0.22, 0.25) for c2, p in zip(cn, proj)]
        ax.add_collection3d(Poly3DCollection(tris0, facecolors=cols,
                                             edgecolors=(0, 0, 0, 0.10), linewidths=0.1))
        # 레이더 입사 화살표(밖→드론, +u 쪽에서 들어옴)
        base = c + u * half * 1.45; tip = c + u * half * 1.0
        ax.quiver(base[0], base[1], base[2], *(tip - base), color="#1565c0",
                  lw=2.2, arrow_length_ratio=0.3)
        L = half * 1.5
        ax.set_xlim(c[0]-L, c[0]+L); ax.set_ylim(c[1]-L, c[1]+L); ax.set_zlim(c[2]-L, c[2]+L)
        try: ax.set_box_aspect((1, 1, 1))
        except Exception: pass
        ax.set_axis_off()
        ax.view_init(elev=el, azim=azd)                      # 카메라 = 레이더 시선
        nlit = int((proj > 0).sum())
        ax.set_title(f"레이더 방위 {azd}° · 고각 {el:.0f}°  ·  조명면 {nlit}/{len(F)}", fontsize=10)
    fn = os.path.join(outdir, "report2_mesh_rcs_facets.png"); fig.savefig(fn, dpi=130); plt.close(fig)
    print("[mesh]", os.path.relpath(fn)); return fn


# --------------------------------------------------------------------------- #
#  (4) 도플러/속도 — 메쉬 속도벡터 + 표준별 파일럿반복률 → 최대 무모호 속도
# --------------------------------------------------------------------------- #
def fig_doppler_mesh(outdir=FIG, target="matrice4e"):
    spec = DRONES[target]; mesh = build_drone(spec)
    fig = plt.figure(figsize=(14, 5.8), constrained_layout=True)
    fig.suptitle("빠른 드론엔 빠른 샘플링 — 속도 v → 도플러 " r"$f_d=2v/\lambda$"
                 ",  읽을 수 있는 최대속도 " r"$v_{\max}=\mathrm{PRF}\cdot\lambda/4$",
                 fontsize=14, fontweight="bold")

    # (좌) 드론 메쉬 + 속도 화살표
    axA = fig.add_subplot(1, 2, 1, projection="3d")
    Vs, _ = _scaled_mesh_verts(mesh, target_extent=1.0)
    dc = drone_colors(spec)
    tris = [[Vs[a], Vs[b], Vs[c]] for (a, b, c) in mesh.f]
    axA.add_collection3d(Poly3DCollection(tris, facecolors=[dc.get(g,(.6,.6,.6)) for g in mesh.g],
                                          edgecolors=(0,0,0,0.12), linewidths=0.1))
    axA.quiver(0, 0, 0, 1.1, 0, 0, color="#c62828", lw=3, arrow_length_ratio=0.15)
    axA.text(1.2, 0, 0.05, "v", color="#c62828", fontsize=15, fontweight="bold")
    axA.text2D(0.02, 0.95, f"{_NAME[target]}\n최고속도 {spec.max_speed_ms or '—'} m/s",
               transform=axA.transAxes, fontsize=10, va="top")
    _equal_3d(axA, [-1,-1,-1], [1,1,1], pad=1.0); axA.set_axis_off(); axA.view_init(elev=20, azim=-55)
    axA.set_title("표적 속도가 곧 도플러", fontsize=11)

    # (우) 표준별 기준신호 반복률 → v_max (막대) + 드론 최고속도 기준선
    axB = fig.add_subplot(1, 2, 2)
    # (이름, 반복률Hz, 반송파Hz)  — 표준별 대표 기준신호
    refs = [("LTE CRS\n(1.8GHz)", 1000.0, 1.843e9, "#ef6c00"),
            ("WiFi VHT-LTF\n(5.2GHz)", 1000.0, 5.21e9, "#1565c0"),
            ("5G PRS/CSI-RS\n(3.5GHz, 촘촘)", 200.0, 3.5e9, "#2e7d32"),
            ("5G SSB\n(3.5GHz)", 50.0, 3.5e9, "#6a1b9a")]
    vmax = [prf * (C0/fc) / 4.0 for (_, prf, fc, _c) in refs]
    names = [r[0] for r in refs]; cols = [r[3] for r in refs]
    x = np.arange(len(refs))
    # 일반 소비자 드론 최고속도대(19~25 m/s) 음영 띠 — 깔끔하게 한 줄
    axB.axhspan(19, 25, color="0.55", alpha=0.16, zorder=0)
    axB.text(len(refs)-0.5, 25*1.05, "일반 드론 최고속도 19~25 m/s", color="0.35",
             fontsize=8.5, ha="right", va="bottom")
    axB.bar(x, vmax, color=cols, edgecolor="k", zorder=3)
    for xi, v in zip(x, vmax):
        axB.text(xi, v*1.06, f"{v:.1f}", ha="center", fontsize=10, fontweight="bold")
    axB.set_yscale("log"); axB.set_xticks(x); axB.set_xticklabels(names, fontsize=9)
    axB.set_ylabel("최대 무모호 속도 v_max [m/s, 로그]")
    axB.set_title("기준신호 반복률(PRF)이 읽을 수 있는 최고속도를 가둔다\n"
                  "(LTE CRS 만 일반 드론 ~20 m/s 를 넘김 — 5G SSB/PRS 는 못 읽음)", fontsize=10.5)
    axB.grid(axis="y", alpha=0.3, zorder=0)
    fn = os.path.join(outdir, "report2_mesh_doppler.png"); fig.savefig(fn, dpi=130); plt.close(fig)
    print("[mesh]", os.path.relpath(fn)); return fn


def build_all(outdir=FIG):
    fig_setup_3d(outdir)
    fig_rcs_balloon(outdir)
    fig_rcs_facets(outdir)
    fig_doppler_mesh(outdir)
    print("메쉬 실험 시각화 완료 →", os.path.relpath(outdir))


if __name__ == "__main__":
    build_all()
