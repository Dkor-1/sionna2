# -*- coding: utf-8 -*-
"""
viz_mesh_reports.py — report_mesh 시리즈 전용 그림 빌더
========================================================================================
모든 그림 텍스트는 영어(하우스 규약). 수치는 mesh_verify.json / 소스 모듈에서 직접.
생성물: report_mesh/outputs/figures/*.png
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SRC = os.path.join(ROOT, "src")
OUT = os.path.abspath(os.path.join(HERE, "..", "outputs"))
FIG = os.path.join(OUT, "figures")
os.makedirs(FIG, exist_ok=True)
for p in (SRC, HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

from drones import (DRONES, MATERIAL_COLOR, DRONE_GROUP_MAT, build_drone,   # noqa: E402
                    build_propeller, drone_colors, drone_gamma_map)

C0 = 299_792_458.0
FC = 3.5e9

with open(os.path.join(OUT, "mesh_verify.json"), encoding="utf-8") as f:
    VJ = json.load(f)

NAME = {"mini5pro": "Mini 5 Pro", "mavic4pro": "Mavic 4 Pro", "matrice4e": "Matrice 4E",
        "s1000plus": "S1000+", "phantom4": "Phantom 4"}
ORDER = ["mini5pro", "mavic4pro", "matrice4e", "s1000plus", "phantom4"]


def _save(fig, name):
    p = os.path.join(FIG, name + ".png")
    fig.savefig(p, dpi=140, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  [fig] {name}.png")


def _mesh_poly(ax, mesh, colors, groups=None, alpha=1.0, lw=0.0, edge=None):
    """geom.Mesh → Poly3DCollection (그룹 필터/색). 반환: 실제 그린 그룹 목록."""
    V = np.asarray(mesh.v, float)
    drawn = []
    for grp in sorted(set(mesh.g)):
        if groups is not None and grp not in groups:
            continue
        F = np.asarray([f for f, g in zip(mesh.f, mesh.g) if g == grp], int)
        if not len(F):
            continue
        tris = V[F]
        pc = Poly3DCollection(tris, alpha=alpha, linewidths=lw)
        pc.set_facecolor(colors.get(grp, (0.7, 0.7, 0.7)))
        if edge:
            pc.set_edgecolor(edge)
        ax.add_collection3d(pc)
        drawn.append(grp)
    return drawn


def _fit_axes(ax, V, pad=1.08):
    c = (V.max(0) + V.min(0)) / 2
    r = (V.max(0) - V.min(0)).max() / 2 * pad
    ax.set_xlim(c[0] - r, c[0] + r)
    ax.set_ylim(c[1] - r, c[1] + r)
    ax.set_zlim(c[2] - r, c[2] + r)
    ax.set_box_aspect((1, 1, 1))
    ax.set_axis_off()


# --------------------------------------------------------------------------- #
#  1) 재질 범례 — 색 = 재질 = |Γ| (출처 포함)
# --------------------------------------------------------------------------- #
def fig_material_legend():
    gm = drone_gamma_map(DRONES["phantom4"], FC)          # 전 그룹 커버(gear 포함)
    rows = []          # (material, color, groups, gamma, provenance)
    prov = {"plastic": "custom ABS (er~2.8)", "carbon": "custom CFRP (conductive)",
            "metal": "Sionna ITU-R P.2040 'metal'", "prop_plastic": "custom nylon/PC",
            "camera_assembly": "custom: metal housing + glass lens (PO eff. 0.85)",
            "pcb": "custom FR-4 + Cu ground plane"}
    for mat, col in MATERIAL_COLOR.items():
        grps = [g for g, (m, _) in DRONE_GROUP_MAT.items() if m == mat]
        gam = np.mean([gm[g] for g in grps if g in gm])
        rows.append((mat, col, grps, gam, prov.get(mat, "custom")))
    fig, ax = plt.subplots(figsize=(10.5, 3.6))
    ax.set_xlim(0, 10.5)
    ax.set_ylim(-0.4, len(rows))
    for i, (mat, col, grps, gam, pv) in enumerate(rows[::-1]):
        y = i
        ax.add_patch(plt.Rectangle((0.1, y + 0.08), 0.72, 0.72, color=col, ec="k", lw=0.6))
        ax.text(1.0, y + 0.44, mat, va="center", fontsize=11, fontweight="bold")
        ax.text(3.15, y + 0.44, f"|Γ|@3.5GHz = {gam:.2f}", va="center", fontsize=10)
        ax.text(5.1, y + 0.44, ", ".join(grps), va="center", fontsize=9, color="0.25")
        ax.text(7.6, y + 0.44, pv, va="center", fontsize=8.5, color="0.4")
    ax.text(0.1, len(rows) - 0.1 + 0.55, "color", fontsize=9, color="0.4")
    ax.text(1.0, len(rows) - 0.1 + 0.55, "material", fontsize=9, color="0.4")
    ax.text(3.15, len(rows) - 0.1 + 0.55, "reflection (amplitude)", fontsize=9, color="0.4")
    ax.text(5.1, len(rows) - 0.1 + 0.55, "mesh groups", fontsize=9, color="0.4")
    ax.text(7.6, len(rows) - 0.1 + 0.55, "radio-material source", fontsize=9, color="0.4")
    ax.set_axis_off()
    ax.set_title("Mesh color = material = radio property  (same rule for all 5 drones)",
                 fontsize=12)
    _save(fig, "material_legend")


# --------------------------------------------------------------------------- #
#  2) 드론별 부위 분해(색=재질) + 와이어프레임
# --------------------------------------------------------------------------- #
def fig_wireframes():
    for key in ORDER:
        spec = DRONES[key]
        mesh = build_drone(spec)
        cols = drone_colors(spec)
        V = np.asarray(mesh.v, float)
        fig = plt.figure(figsize=(12, 4.6))
        for i, (title, kw) in enumerate([
                ("shaded (color = material)", dict(alpha=1.0, lw=0.0)),
                ("wireframe (triangles)", dict(alpha=0.15, lw=0.18, edge="k")),
                ("top view", dict(alpha=1.0, lw=0.0))]):
            ax = fig.add_subplot(1, 3, i + 1, projection="3d")
            _mesh_poly(ax, mesh, cols, **kw)
            _fit_axes(ax, V)
            ax.view_init(elev=90 if i == 2 else 18, azim=-90 if i == 2 else -60)
            ax.set_title(title, fontsize=10)
        ng = VJ["A_geometry"][key]
        fig.suptitle(f"{NAME[key]} — {ng['n_faces']:,} triangles / "
                     f"{ng['n_groups']} parts (groups)", fontsize=13)
        _save(fig, f"wireframe_{key}")


# --------------------------------------------------------------------------- #
#  3) 몸체 빌드 단계 — 실제 최종 메쉬의 그룹을 누적 표시
# --------------------------------------------------------------------------- #
def fig_build_stages(key="mavic4pro"):
    spec = DRONES[key]
    mesh = build_drone(spec)
    cols = drone_colors(spec)
    V = np.asarray(mesh.v, float)
    stages = [("1. body (superellipse loft)", ["body"]),
              ("2. + canopy/battery lid", ["body", "canopy"]),
              ("3. + motors", ["body", "canopy", "motor"]),
              ("4. + internal battery & PCB", ["body", "canopy", "motor", "battery", "pcb"]),
              ("5. + gimbal camera", ["body", "canopy", "motor", "battery", "pcb", "camera"]),
              ("6. + propellers (full)", None)]
    fig = plt.figure(figsize=(15, 8.4))
    for i, (title, grps) in enumerate(stages):
        ax = fig.add_subplot(2, 3, i + 1, projection="3d")
        alpha = 0.55 if (grps and ("battery" in grps and "camera" not in grps)) else 1.0
        _mesh_poly(ax, mesh, cols, groups=grps, alpha=alpha)
        _fit_axes(ax, V)
        ax.view_init(elev=16, azim=-55)
        ax.set_title(title, fontsize=10)
    fig.suptitle(f"{NAME[key]} — assembly order of the parametric CAD "
                 f"(each part = one OBJ = one Sionna material)", fontsize=13)
    _save(fig, "build_stages")


# --------------------------------------------------------------------------- #
#  4) 프로펠러 익형 — NACA 단면 + 피치/시위 분포
# --------------------------------------------------------------------------- #
def fig_airfoil():
    from drone_cad import _airfoil
    fig = plt.figure(figsize=(13, 7.6))
    # (a) NACA 단면
    ax = fig.add_subplot(2, 2, 1)
    for tr, c in [(0.10, "C0"), (0.16, "C1")]:
        poly = _airfoil(1.0, thick_ratio=tr)                  # shapely Polygon
        pts = np.asarray(poly.exterior.coords)
        ax.plot(pts[:, 0], pts[:, 1], c, lw=2, label=f"thickness {tr*100:.0f}%")
    ax.set_aspect("equal")
    ax.legend(fontsize=9)
    ax.set_title("(a) blade cross-section (NACA-style airfoil), chord=1", fontsize=10)
    ax.grid(alpha=0.3)
    # (b) 피치각 θ(r)=atan(P/2πr)
    ax = fig.add_subplot(2, 2, 2)
    for key in ORDER:
        s = DRONES[key]
        if not s.prop_pitch_in:
            continue
        R = s.prop_dia_mm / 2000.0
        P = s.prop_pitch_in * 0.0254
        r = np.linspace(0.15 * R, R, 60)
        th = np.degrees(np.arctan(P / (2 * np.pi * r)))
        ax.plot(r * 1000, th, lw=2, label=f"{NAME[key]} (P={s.prop_pitch_in}\")")
    ax.set_xlabel("radius r [mm]")
    ax.set_ylabel("blade pitch angle θ(r) [deg]")
    ax.set_title("(b) geometric pitch  θ(r) = atan(P / 2πr)  — per-model, from spec pitch",
                 fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    # (c) 프로펠러 3D (mavic)
    for j, key in enumerate(["mavic4pro", "s1000plus"]):
        ax = fig.add_subplot(2, 2, 3 + j, projection="3d")
        pm = build_propeller(DRONES[key])
        V = np.asarray(pm.v, float)
        cols = {g: MATERIAL_COLOR["prop_plastic"] for g in set(pm.g)}
        _mesh_poly(ax, pm, cols, alpha=0.95, lw=0.15, edge="k")
        _fit_axes(ax, V)
        ax.view_init(elev=28, azim=-50)
        ax.set_title(f"(c{j+1}) {NAME[key]} propeller — loft of twisted airfoil sections",
                     fontsize=10)
    _save(fig, "airfoil_profile")


# --------------------------------------------------------------------------- #
#  5) 인터넷에서 가져온 원본 모델 갤러리 (출처·라이선스 라벨)
# --------------------------------------------------------------------------- #
def fig_originals():
    import trimesh
    from mesh_compare import load_reference, typhoon_h480_real
    fig = plt.figure(figsize=(15, 4.8))
    # (a) Phantom4 실기체 스캔 점구름
    ax = fig.add_subplot(1, 3, 1, projection="3d")
    S = np.load(os.path.join(ROOT, "assets", "meshes", "cad", "phantom4_scan_points.npz"))
    P = np.asarray(S["P"], float)
    sel = np.random.default_rng(0).choice(len(P), min(9000, len(P)), replace=False)
    ax.scatter(P[sel, 0], P[sel, 1], P[sel, 2], s=0.8, c=P[sel, 2], cmap="viridis")
    _fit_axes(ax, P)
    ax.view_init(elev=18, azim=-60)
    ax.set_title("DJI Phantom 4 — real-unit 3D scan (0.4 mm)\n"
                 "Thingiverse thing:1456295, CC-BY (NeverDun)", fontsize=9)
    # (b) Typhoon H480 실물 CAD 조립
    ax = fig.add_subplot(1, 3, 2, projection="3d")
    try:
        tm = typhoon_h480_real()
        V, F = tm.vertices, tm.faces
        pc = Poly3DCollection(V[F], alpha=0.9, linewidths=0)
        pc.set_facecolor((0.55, 0.6, 0.65))
        ax.add_collection3d(pc)
        _fit_axes(ax, V)
        ax.view_init(elev=18, azim=-60)
    except BaseException as e:
        ax.text2D(0.1, 0.5, f"load error: {e}", transform=ax.transAxes)
    ax.set_title("Yuneec Typhoon H480 — real product CAD\n"
                 "ethz-asl/rotors_simulator, Apache-2.0", fontsize=9)
    # (c) 3DR Solo
    ax = fig.add_subplot(1, 3, 3, projection="3d")
    try:
        tm = load_reference("solo.stl")
        V, F = tm.vertices, tm.faces
        pc = Poly3DCollection(V[F], alpha=0.9, linewidths=0)
        pc.set_facecolor((0.5, 0.52, 0.55))
        ax.add_collection3d(pc)
        _fit_axes(ax, V)
        ax.view_init(elev=18, azim=-60)
    except BaseException as e:
        ax.text2D(0.1, 0.5, f"load error: {e}", transform=ax.transAxes)
    ax.set_title("3DR Solo — real product CAD\n"
                 "ethz-asl/rotors_simulator, Apache-2.0", fontsize=9)
    fig.suptitle("Downloaded ORIGINALS used only for verification "
                 "(our 5 DJI targets are built from official spec sheets, not these)",
                 fontsize=12)
    _save(fig, "originals_gallery")


# --------------------------------------------------------------------------- #
#  6) 치수 대조 — 공식 vs 메쉬 실측
# --------------------------------------------------------------------------- #
def fig_dims():
    C = VJ["C_dims"]
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.4))
    ax = axes[0]
    labels, offs, meas = [], [], []
    for key in ORDER:
        for chk, v in C[key]["checks"].items():
            labels.append(f"{NAME[key]}\n{chk}")
            offs.append(v["official"])
            meas.append(v["measured"])
    x = np.arange(len(labels))
    ax.bar(x - 0.2, offs, 0.4, label="official spec", color="0.55")
    ax.bar(x + 0.2, meas, 0.4, label="our mesh (measured)", color="C0")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=6.2, rotation=45, ha="right")
    ax.set_ylabel("mm")
    ax.legend(fontsize=9)
    ax.set_title("official spec vs mesh measurement", fontsize=11)
    ax = axes[1]
    errs = [C[k]["worst_err_pct"] for k in ORDER]
    ax.bar([NAME[k] for k in ORDER], errs, color="C1")
    ax.axhline(2.0, color="r", ls="--", lw=1, label="2 % guide")
    ax.set_ylabel("worst |error| [%]")
    ax.set_title("worst dimensional error per drone", fontsize=11)
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3, axis="y")
    _save(fig, "dims_check")


# --------------------------------------------------------------------------- #
#  7) 대칭 — frame vs full(프로펠러 카이럴성)
# --------------------------------------------------------------------------- #
def fig_symmetry():
    B = VJ["B_symmetry"]
    fig, ax = plt.subplots(figsize=(9.5, 4.2))
    x = np.arange(len(ORDER))
    fr = [B[k]["frame_only"]["chamfer_mm"]["p95"] for k in ORDER]
    fu = [B[k]["full"]["chamfer_mm"]["p95"] for k in ORDER]
    ax.bar(x - 0.2, fr, 0.4, label="airframe only (props excluded)", color="C0")
    ax.bar(x + 0.2, fu, 0.4, label="full drone (props included)", color="C3")
    ax.set_yscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels([NAME[k] for k in ORDER], fontsize=9)
    ax.set_ylabel("mirror chamfer p95 [mm]  (log)")
    ax.set_title("Left-right symmetry: airframe is symmetric (≈ sampling res.);\n"
                 "large full-drone values are the CHIRAL propellers (CW/CCW), not a defect",
                 fontsize=11)
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3, axis="y")
    _save(fig, "symmetry_chamfer")


# --------------------------------------------------------------------------- #
#  8) 스캔 대조 — CAD vs 실기체 스캔 오버레이 + chamfer
# --------------------------------------------------------------------------- #
def fig_scan_overlay():
    from scipy.spatial import cKDTree
    from verify_mesh_suite import _sample_points
    G = VJ["G_scan"]
    S = np.load(os.path.join(ROOT, "assets", "meshes", "cad", "phantom4_scan_points.npz"))
    Ps = np.asarray(S["P"], float)
    mesh = build_drone(DRONES["phantom4"])
    Pc, _, _ = _sample_points(mesh, spacing=3e-3,
                              exclude_groups=("prop", "camera", "gimbal"))
    Ps = Ps - Ps.mean(0) * np.array([1, 1, 0])
    Pc = Pc - Pc.mean(0) * np.array([1, 1, 0])
    Ps = Ps + np.array([0, 0, G["z_shift_mm"] / 1000.0])
    d = cKDTree(Pc).query(Ps, k=1)[0] * 1000.0
    fig = plt.figure(figsize=(14, 4.6))
    ax = fig.add_subplot(1, 3, 1, projection="3d")
    rng = np.random.default_rng(1)
    sel = rng.choice(len(Ps), 6000, replace=False)
    sc = rng.choice(len(Pc), 6000, replace=False)
    ax.scatter(Pc[sc, 0], Pc[sc, 1], Pc[sc, 2], s=0.6, c="C0", label="our CAD")
    ax.scatter(Ps[sel, 0], Ps[sel, 1], Ps[sel, 2], s=0.6, c="C3", label="real scan")
    _fit_axes(ax, np.vstack([Ps, Pc]))
    ax.view_init(elev=14, azim=-60)
    ax.legend(fontsize=8, loc="upper right")
    ax.set_title("overlay (props/gimbal excluded — absent in scan)", fontsize=9)
    ax = fig.add_subplot(1, 3, 2, projection="3d")
    p = ax.scatter(Ps[sel, 0], Ps[sel, 1], Ps[sel, 2], s=0.8, c=np.minimum(d[sel], 30),
                   cmap="inferno")
    _fit_axes(ax, Ps)
    ax.view_init(elev=14, azim=-60)
    fig.colorbar(p, ax=ax, shrink=0.6, label="scan→CAD distance [mm]")
    ax.set_title("where does the scan differ from our CAD?", fontsize=9)
    ax = fig.add_subplot(1, 3, 3)
    ax.hist(d, bins=60, color="C0", alpha=0.85)
    for q, c in [(50, "k"), (90, "C3")]:
        v = np.percentile(d, q)
        ax.axvline(v, color=c, ls="--", lw=1.2)
        ax.text(v, ax.get_ylim()[1] * 0.9, f" p{q}={v:.1f}mm", fontsize=8, color=c)
    ax.set_xlabel("scan→CAD nearest distance [mm]")
    ax.set_title("chamfer distance histogram", fontsize=9)
    ax.grid(alpha=0.3)
    fig.suptitle("Phantom 4: our parametric CAD vs real-unit 3D scan "
                 "(Thingiverse thing:1456295, CC-BY)", fontsize=12)
    _save(fig, "scan_overlay")


# --------------------------------------------------------------------------- #
#  9) 물리 수렴 — PO 점간격 / SBR 광선간격
# --------------------------------------------------------------------------- #
def fig_convergence():
    from rcs_po import drone_rcs_pattern
    H = VJ["H_po_convergence"]
    I = VJ["I_sbr_subdiv"]
    az = np.arange(0.0, 360.0, 5.0)
    lam = C0 / FC
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 4.4))
    ax = axes[0]
    for s, tag, c in [(lam / 10, "PO points λ/10", "C0"), (lam / 20, "PO points λ/20", "C3")]:
        sig, _ = drone_rcs_pattern("mavic4pro", FC, az, el_deg=15.0, spacing=s)
        ax.plot(az, 10 * np.log10(np.maximum(sig, 1e-12)), c, lw=1.2, alpha=0.85, label=tag)
    h = H["mavic4pro"]
    ax.set_title(f"(a) PO sampling convergence — Mavic 4 Pro @3.5 GHz\n"
                 f"azimuth-average shift {h['azavg_dbsm']['diff']:+.2f} dB "
                 f"(per-angle max {h['per_angle_absdiff_db']['max']:.1f} dB at deep nulls)",
                 fontsize=10)
    ax.set_xlabel("azimuth [deg]")
    ax.set_ylabel("RCS [dBsm]")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)
    ax = axes[1]
    r = I["ray_spacing_convergence"]
    labels = ["subdivision ×4\n(same surface)", "ray grid λ/12→λ/24\n(true numerical knob)"]
    means = [I["subdivision_invariance"]["per_angle_absdiff_db"]["mean"],
             r["per_angle_absdiff_db"]["mean"]]
    maxs = [I["subdivision_invariance"]["per_angle_absdiff_db"]["max"],
            r["per_angle_absdiff_db"]["max"]]
    x = np.arange(2)
    ax.bar(x - 0.18, means, 0.36, label="mean |Δσ| [dB]", color="C0")
    ax.bar(x + 0.18, maxs, 0.36, label="max |Δσ| [dB]", color="C3")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.axhline(1.0, color="k", ls=":", lw=1)
    ax.text(1.35, 1.05, "1 dB", fontsize=8)
    ax.set_title(f"(b) SBR robustness — Mavic 4 Pro, {I['n_az']} azimuths (GPU)\n"
                 f"azimuth-average shift {r['azavg_dbsm']['diff']:+.2f} dB when rays ×2 denser",
                 fontsize=10)
    ax.set_ylabel("|Δ RCS| [dB]")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3, axis="y")
    _save(fig, "convergence")


# --------------------------------------------------------------------------- #
#  10) 부위 겹침 매트릭스 (조립식 의도 겹침 공개)
# --------------------------------------------------------------------------- #
def fig_overlap():
    F = VJ["F_overlap"]
    fig, axes = plt.subplots(1, len(ORDER), figsize=(16, 3.4))
    for ax, key in zip(axes, ORDER):
        pairs = F[key]["pairs"]
        grps = sorted({p["a"] for p in pairs} | {p["b"] for p in pairs})
        n = len(grps)
        M = np.zeros((n, n))
        for p in pairs:
            i, j = grps.index(p["a"]), grps.index(p["b"])
            M[i, j] = M[j, i] = p["overlap_cm3"]
        im = ax.imshow(M, cmap="YlOrRd")
        ax.set_xticks(range(n))
        ax.set_yticks(range(n))
        ax.set_xticklabels(grps, fontsize=6, rotation=90)
        ax.set_yticklabels(grps, fontsize=6)
        ax.set_title(f"{NAME[key]}\n{F[key]['overlap_pct_of_volume']:.1f}% of volume",
                     fontsize=8.5)
        fig.colorbar(im, ax=ax, shrink=0.75)
    fig.suptitle("Intentional assembly overlaps between parts [cm³] — parts are separate "
                 "closed solids pushed into each other (no boolean union; SBR occlusion "
                 "hides buried surfaces)", fontsize=11)
    _save(fig, "overlap_matrix")


# --------------------------------------------------------------------------- #
#  11) 삼각형 품질 — 최소각·엣지길이 vs 파장
# --------------------------------------------------------------------------- #
def fig_tri_quality():
    A = VJ["A_geometry"]
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.2))
    ax = axes[0]
    for key in ORDER:
        mesh = build_drone(DRONES[key])
        V = np.asarray(mesh.v, float)
        Fc = np.asarray(mesh.f, int)
        E = np.concatenate([V[Fc[:, 1]] - V[Fc[:, 0]], V[Fc[:, 2]] - V[Fc[:, 1]],
                            V[Fc[:, 0]] - V[Fc[:, 2]]])
        el = np.linalg.norm(E, axis=1) * 1000.0
        ax.hist(el, bins=70, histtype="step", lw=1.4, label=NAME[key], density=True)
    lam52 = C0 / 5.21e9 * 1e3
    ax.axvline(lam52, color="r", ls="--", lw=1.2)
    ax.text(lam52 * 1.03, ax.get_ylim()[1] * 0.9, f"λ@5.2GHz = {lam52:.0f} mm",
            color="r", fontsize=8)
    ax.set_xlabel("edge length [mm]")
    ax.set_ylabel("density")
    ax.set_xlim(0, 40)
    ax.set_title("edge lengths vs the shortest wavelength", fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    ax = axes[1]
    x = np.arange(len(ORDER))
    p1 = [A[k]["tri_min_angle_deg"]["p1"] for k in ORDER]
    med = [A[k]["tri_min_angle_deg"]["median"] for k in ORDER]
    ax.bar(x - 0.2, p1, 0.4, label="1st percentile", color="C3")
    ax.bar(x + 0.2, med, 0.4, label="median", color="C0")
    ax.set_xticks(x)
    ax.set_xticklabels([NAME[k] for k in ORDER], fontsize=9)
    ax.set_ylabel("triangle min angle [deg]")
    ax.set_title("triangle quality (no degenerate faces — see A_geometry)", fontsize=10)
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3, axis="y")
    _save(fig, "triangle_quality")


# --------------------------------------------------------------------------- #
#  12) 파이프라인 지도 — 자료 → CAD → 검증
# --------------------------------------------------------------------------- #
def fig_pipeline_map():
    fig, ax = plt.subplots(figsize=(13, 6.2))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 10)
    ax.set_axis_off()

    def box(x, y, w, h, text, fc="#eef3fa", ec="C0", fs=8.6):
        ax.add_patch(plt.Rectangle((x, y), w, h, facecolor=fc, edgecolor=ec, lw=1.4))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs)

    def arrow(x0, y0, x1, y1):
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle="->", lw=1.3, color="0.35"))

    # 자료층
    box(0.2, 7.8, 3.6, 1.7, "DJI official spec sheets\n(dji.com/specs per model)\n"
        "→ docs/drone_research.json\n→ docs/SPECS.md (verified)", fc="#fdf3e7", ec="C1")
    box(4.2, 7.8, 4.2, 1.7, "Real-unit 3D scan (verify only)\nPhantom 4, Thingiverse "
        "thing:1456295\nCC-BY → phantom4_scan_points.npz", fc="#fdf3e7", ec="C1")
    box(8.8, 7.8, 4.0, 1.7, "Real product CADs (verify only)\nTyphoon H480 / Solo "
        "(Apache-2.0)\nX500 parts (BSD-3) — SOURCES.md", fc="#fdf3e7", ec="C1")
    # 제작층
    box(0.2, 5.0, 4.4, 1.9, "Parametric CAD build\nsrc/drones.py (DroneSpec: official numbers)\n"
        "src/drone_cad.py + src/cadkit.py\n(trimesh + manifold3d: loft/sweep/boolean)")
    box(5.2, 5.0, 3.4, 1.9, "Per-part OBJ export\n1 part = 1 OBJ = 1 material\n"
        "assets/meshes/drones/<key>/")
    box(9.2, 5.0, 3.6, 1.9, "Radio materials\nsrc/materials.py\nSionna ITU-R P.2040 + custom\n"
        "color = material (MATERIAL_COLOR)")
    # 검증층
    box(0.2, 1.6, 6.2, 2.4, "Geometry verification\nA watertight/normals/winding/degenerate\n"
        "B symmetry (mirror chamfer)  C dims vs official\nD volume sanity  E material coverage\n"
        "F part-overlap disclosure", fc="#eefaef", ec="C2")
    box(6.9, 1.6, 5.9, 2.4, "Physics verification\nG chamfer vs real scan (mm)\n"
        "H PO point-density convergence\nI SBR subdivision + ray-density (GPU)\n"
        "+ report03/07/08 cross-checks", fc="#eefaef", ec="C2")
    box(3.6, 0.1, 5.6, 1.0, "evidence JSON → report_mesh/outputs/mesh_verify.json\n"
        "(all report numbers come from here)", fc="#f5eefa", ec="C4", fs=8.2)
    arrow(2.0, 7.8, 2.2, 6.9)
    arrow(6.3, 7.8, 9.5, 4.0)
    arrow(10.8, 7.8, 10.4, 4.0)
    arrow(4.6, 5.9, 5.2, 5.9)
    arrow(8.6, 5.9, 9.2, 5.9)
    arrow(2.4, 5.0, 2.6, 4.0)
    arrow(6.9, 5.0, 8.5, 4.0)
    arrow(5.0, 1.6, 5.4, 1.1)
    arrow(8.6, 1.6, 8.2, 1.1)
    ax.set_title("Mesh pipeline: where every piece of information comes from, "
                 "and how it is verified", fontsize=12.5)
    _save(fig, "pipeline_map")


def build_all():
    fig_material_legend()
    fig_wireframes()
    fig_build_stages()
    fig_airfoil()
    fig_originals()
    fig_dims()
    fig_symmetry()
    fig_scan_overlay()
    fig_convergence()
    fig_overlap()
    fig_tri_quality()
    fig_pipeline_map()
    print("✅ report_mesh figures 완료")


if __name__ == "__main__":
    build_all()
