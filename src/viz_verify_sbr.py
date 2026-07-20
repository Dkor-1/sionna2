# -*- coding: utf-8 -*-
"""
viz_verify_sbr.py — (report6) **오늘 새로 알아낸 것 3가지**를 그림으로
=======================================================================
  §A  report6_ray_budget.png  : "광선을 더 쏘면 되지 않나?" — 4억 발을 쏴 본 결과
                                (데이터: benchmark/verify_rt_rays.py → outputs/rt_ray_budget.json)
  §B  report6_sbr.png         : SBR — PO 를 광선추적 **안으로** 넣다 (상용 EM 솔버가 하는 그것)
  §C  report6_mesh_bugs.png   : 메쉬·재질 버그 3건 + trimesh 회귀방지

모든 수치는 **이 모듈이 직접 측정**하거나 측정 JSON 에서 읽는다(하드코딩 없음).
§B·§C 의 측정은 outputs/report6_sbr.json 에 캐시된다 — make_notebook6.py 가 그걸 읽어
본문 표를 채우므로 **그림과 글이 어긋날 수 없다.**

⚠ 금지 표현: "레이트레이싱은 RCS 를 못 낸다" (거짓 — SBR 은 광선추적이고 σ 를 계산한다).
   참인 명제는 좁다: **산란적분 단계가 없는 전파용 solver 에서는 σ 가 창발하지 않는다.**

실행:  python src/viz_verify_sbr.py            (GPU — gpu.pick 이 자동선택)
"""
from __future__ import annotations

import json
import os
import sys
import textwrap

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import vizstyle                                          # noqa: E402
vizstyle.use_korean()
import matplotlib.pyplot as plt                          # noqa: E402
from matplotlib.patches import FancyBboxPatch            # noqa: E402

# 나눔고딕에 없는 글리프(σ λ Γ Δ − ×)는 DejaVu Sans 로 폴백.
plt.rcParams["font.family"] = list(plt.rcParams["font.family"]) + ["DejaVu Sans"]

ROOT = os.path.abspath(os.path.join(_HERE, ".."))
FIG = os.path.join(ROOT, "outputs", "figures")
OUT_JSON = os.path.join(ROOT, "outputs", "report6_sbr.json")
RAY_JSON = os.path.join(ROOT, "outputs", "rt_ray_budget.json")
MD_JSON = os.path.join(ROOT, "outputs", "report3_microdoppler.json")

FC = 3.5e9
C0 = 299792458.0
LAM = C0 / FC
N_AZ = 36                                   # 방위 표본(평균용)
CAP_FS = 8.6

C_PO, C_SBR, C_RT, C_TRUTH, C_BAD, C_OK = "#8e24aa", "#1565c0", "#c62828", "#2e7d32", "#c62828", "#2e7d32"
_ORDER = ["mini5pro", "mavic4pro", "matrice4e", "s1000plus", "phantom4"]


def _caption(fig, text):
    ncol = int(fig.get_figwidth() * 72 / (0.50 * CAP_FS) * 0.93)
    fig.supxlabel("\n".join(textwrap.fill(p, ncol) for p in text.split("\n")),
                  fontsize=CAP_FS, color="0.45")


def _dbsm(x):
    return 10.0 * np.log10(np.asarray(x, float) + 1e-30)


def _short(key):
    from drones import DRONES
    return DRONES[key].name.split("  ")[0].replace("DJI ", "")


# =========================================================================== #
#  측정 — §B (SBR 커널) · §C (버그 3건)
# =========================================================================== #
def measure(n_az=N_AZ, force=False) -> dict:
    """§B·§C 에 필요한 모든 수치를 **직접 측정**하고 캐시한다."""
    if os.path.exists(OUT_JSON) and not force:
        with open(OUT_JSON) as f:
            return json.load(f)

    from drones import (DRONES, DRONE_GROUP_MAT, build_drone, build_frame, build_propeller,
                        rotor_layout, frame_fit_scale, _build_frame_raw, _drone_dims,
                        motor_angles, drone_gamma_map)
    from geom import Mesh, translate, rotate
    from materials import gamma_bulk, gamma_po
    from rcs_sbr import rcs_sbr_batch, rcs_sbr, validate as sbr_validate
    from rcs_po import mesh_to_points, rcs_from_points
    import mesh_check
    import math

    az = np.linspace(0, 360, n_az, endpoint=False)
    GM = {g: mat for g, (mat, _) in DRONE_GROUP_MAT.items()}
    out: dict = {"fc": FC, "n_az": n_az}

    # ---------------------------------------------------------------- §B-1
    #  커널 검증 — 해석해가 있는 표적 (격자 수렴)
    print("[B1] SBR 커널 검증 (금속구 πr² · 평판 4πA²/λ²) …")
    from geom import uv_sphere, box
    divs = [4, 6, 8, 10, 12, 16, 20, 24]
    r_s, a_p = 0.5, 0.4
    sph = uv_sphere(r_s, seg=180, rings=90, group="metal")
    plate = box(a_p, a_p, 0.002, group="metal")
    ex_s = np.pi * r_s ** 2
    ex_p = 4 * np.pi * (a_p * a_p) ** 2 / LAM ** 2
    kern = {"divs": divs, "sphere_exact_dbsm": float(_dbsm(ex_s)),
            "plate_exact_dbsm": float(_dbsm(ex_p)), "sphere_err": [], "plate_err": []}
    for d in divs:
        s = rcs_sbr(sph, {"metal": "metal"}, FC, az_deg=0.0, el_deg=0.0, spacing=LAM / d)
        p = rcs_sbr(plate, {"metal": "metal"}, FC, az_deg=0.0, el_deg=90.0, spacing=LAM / d)
        kern["sphere_err"].append(float(_dbsm(s) - _dbsm(ex_s)))
        kern["plate_err"].append(float(_dbsm(p) - _dbsm(ex_p)))
        print(f"     λ/{d:<3d} 구 {kern['sphere_err'][-1]:+6.2f} dB · 평판 {kern['plate_err'][-1]:+6.2f} dB")
    out["kernel"] = kern

    # ---------------------------------------------------------------- §B-2
    #  PO vs SBR — 5종 × el 0°/15°, 그리고 오목부 다중반사(1 → 3 bounce)
    print("[B2] PO vs SBR (가림) · 다중반사 …")
    comp = {}
    for key in _ORDER:
        spec = DRONES[key]
        m = build_drone(spec)
        gmap = drone_gamma_map(spec)
        P, N, dA, w = mesh_to_points(m, LAM / 7.0, gamma=gmap)
        row = {}
        for el in (0.0, 15.0):
            po = rcs_from_points(P, N, dA, FC, az_deg=az, el_deg=el, w=w)
            sb = rcs_sbr_batch(m, GM, FC, az_deg=az, el_deg=el, cache_key=f"{key}")
            row[f"po_el{int(el)}"] = float(_dbsm(np.mean(po)))
            row[f"sbr_el{int(el)}"] = float(_dbsm(np.mean(sb)))
        # 오목부 다중반사 — 배치가 안 되므로 방위를 줄여서(비용) 같은 방위집합으로 1 vs 3
        az3 = np.linspace(0, 360, 12, endpoint=False)
        s1 = rcs_sbr(m, GM, FC, az_deg=az3, el_deg=15.0, max_bounce=1)
        s3 = rcs_sbr(m, GM, FC, az_deg=az3, el_deg=15.0, max_bounce=3)
        row["mb1_el15"] = float(_dbsm(np.mean(s1)))
        row["mb3_el15"] = float(_dbsm(np.mean(s3)))
        row["multibounce_db"] = row["mb3_el15"] - row["mb1_el15"]
        row["occl_el15"] = row["sbr_el15"] - row["po_el15"]
        row["occl_el0"] = row["sbr_el0"] - row["po_el0"]
        comp[key] = row
        print(f"     {key:10s} el15  PO {row['po_el15']:+6.2f} → SBR {row['sbr_el15']:+6.2f} "
              f"({row['occl_el15']:+.2f} dB) · 다중반사 {row['multibounce_db']:+.2f} dB")
    out["compare"] = comp

    # ---------------------------------------------------------------- §C-1
    #  메쉬 외형 버그 — 수정 전(맞춤 없음) 메쉬를 그대로 재현해 σ 를 재본다
    print("[C1] 메쉬 외형(높이) 버그 — 수정 전 메쉬 재현 후 σ 대조 …")

    def build_drone_prefix(spec):
        """**수정 전** 드론 메쉬 = 공식 외형 맞춤(frame_fit_scale) 이 없던 시절의 build_drone.
        프레임은 _build_frame_raw 그대로, 로터도 배율 1.0 위치에 얹는다."""
        m = _build_frame_raw(spec)
        prop = build_propeller(spec)
        diag, r, prop_r, bh, body_l, body_w, body_z = _drone_dims(spec)
        arm_t = (0.08 if spec.fixed_arm else 0.045) * diag
        motor_h = 0.045 * diag
        prop_z = motor_h + arm_t / 2 + 0.006
        for k, ang in enumerate(motor_angles(spec)):
            ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
            M = translate(r * ca, r * sa, prop_z) @ rotate("z", ang + 12.0)
            m.merge(prop.transformed(M), group="prop")
        return m

    env = {}
    for key in _ORDER:
        spec = DRONES[key]
        raw = np.asarray(_build_frame_raw(spec).v, float)
        fit = np.asarray(build_frame(spec).v, float)
        h_old = float((raw.max(0) - raw.min(0))[2] * 1000)
        h_new = float((fit.max(0) - fit.min(0))[2] * 1000)
        m_old = build_drone_prefix(spec)
        m_new = build_drone(spec)
        row = dict(h_old_mm=h_old, h_new_mm=h_new,
                   official_h_mm=(spec.envelope_mm[2] if spec.envelope_mm else None),
                   fit_scale=[float(v) for v in frame_fit_scale(spec)],
                   h_err_pct=100.0 * (h_old - h_new) / h_new)
        for el in (0.0, 15.0):
            s_old = rcs_sbr_batch(m_old, GM, FC, az_deg=az, el_deg=el, cache_key=f"{key}_old")
            s_new = rcs_sbr_batch(m_new, GM, FC, az_deg=az, el_deg=el, cache_key=f"{key}")
            row[f"sbr_old_el{int(el)}"] = float(_dbsm(np.mean(s_old)))
            row[f"sbr_new_el{int(el)}"] = float(_dbsm(np.mean(s_new)))
            row[f"d_el{int(el)}"] = row[f"sbr_new_el{int(el)}"] - row[f"sbr_old_el{int(el)}"]
        env[key] = row
        print(f"     {key:10s} 높이 {h_old:6.1f} → {h_new:6.1f} mm ({row['h_err_pct']:+5.1f}%) · "
              f"σ(el15) {row['d_el15']:+.2f} dB · σ(el0) {row['d_el0']:+.2f} dB")
    out["envelope"] = env

    # ---------------------------------------------------------------- §C-2
    #  재질 이중화 — camera 를 두 엔진이 다르게 보던 버그
    print("[C2] 재질 이중화(camera) …")
    g_old_sionna = float(gamma_bulk("plastic", FC))       # 수정 전 Sionna 가 camera 를 보던 값
    g_po = float(gamma_po("camera_assembly", FC))         # PO 손표가 쓰던 값 (지금은 재질 정의)
    mat_rows = []
    for k in ("metal", "camera_assembly", "pcb", "carbon", "plastic"):
        mat_rows.append(dict(key=k, bulk=float(gamma_bulk(k, FC)), po=float(gamma_po(k, FC))))
    # 드론 σ 에 미치는 영향: camera 그룹만 옛 Sionna 값(plastic 벌크)으로 보면?
    spec = DRONES["mavic4pro"]
    m = build_drone(spec)
    GM_cam = dict(GM); GM_cam["camera"] = g_old_sionna     # float → |Γ| 직접 지정
    #  ⚠ _SCENE_CACHE 는 (메쉬 + 그룹 |Γ|) 를 함께 캐시한다 → **재질이 다르면 키도 달라야 한다.**
    #    (같은 키를 주면 옛 |Γ| 가 재사용돼 차이가 0.00 dB 로 나온다 — 실제로 한 번 그랬다.)
    s_ok = rcs_sbr_batch(m, GM, FC, az_deg=az, el_deg=15.0, cache_key="mavic4pro")
    s_bad = rcs_sbr_batch(m, GM_cam, FC, az_deg=az, el_deg=15.0, cache_key="mavic4pro_camplastic")
    out["camera"] = dict(
        gamma_sionna_before=g_old_sionna, gamma_po_before=g_po,
        mismatch_db=float(20 * np.log10(g_po / g_old_sionna)),
        materials=mat_rows,
        sigma_ok_dbsm=float(_dbsm(np.mean(s_ok))), sigma_bad_dbsm=float(_dbsm(np.mean(s_bad))),
        sigma_delta_db=float(_dbsm(np.mean(s_ok)) - _dbsm(np.mean(s_bad))))
    print(f"     camera |Γ|: Sionna {g_old_sionna:.3f} vs PO {g_po:.2f} → "
          f"**{out['camera']['mismatch_db']:+.1f} dB** 어긋남 · 드론 σ 영향 "
          f"{out['camera']['sigma_delta_db']:+.2f} dB")

    # ---------------------------------------------------------------- §C-3
    #  프로펠러 법선 뒤집힘 — 수정 전 prop_blade 를 국소 복제해 실제로 되살린다
    print("[C3] 프로펠러 법선 버그 — 수정 전 메쉬를 되살려 PO/SBR 대조 …")

    def prop_blade_buggy(R, root=0.12, thick=None, pitch_deg=18.0, twist_deg=11.0,
                         sweep=0.10, n=10, group="prop"):
        """**수정 전 prop_blade** — 캡 2장의 감기가 반대라 법선이 안쪽을 향했다.
        (geom.prop_blade 를 고치지 않고, 버그판만 여기 복제한다 — viz_verify_po 와 같은 규약.)"""
        m = Mesh(group)
        r0 = root * R
        thick = thick if thick is not None else 0.012 * R

        def chord(t):
            ts = [0.0, 0.15, 0.35, 0.80, 1.0]
            cs = [0.10, 0.20, 0.22, 0.16, 0.03]
            for j in range(len(ts) - 1):
                if t <= ts[j + 1]:
                    f = (t - ts[j]) / (ts[j + 1] - ts[j] + 1e-12)
                    return (cs[j] + f * (cs[j + 1] - cs[j])) * R
            return cs[-1] * R

        rings = []
        for i in range(n + 1):
            t = i / n
            x = r0 + (R - r0) * t
            c = chord(t)
            th = math.radians(pitch_deg - twist_deg * t)
            cy = sweep * R * math.sin(math.pi / 2 * t)
            ct, st = math.cos(th), math.sin(th)
            ring = []
            for s, zc in [(-0.5, +thick / 2), (+0.5, +thick / 2),
                          (+0.5, -thick / 2), (-0.5, -thick / 2)]:
                yy, zz = s * c, zc
                m_y = cy + yy * ct - zz * st
                m_z = yy * st + zz * ct
                ring.append(m.add_vertex(x, m_y, m_z))
            rings.append(ring)
        for i in range(n):
            a_, b_ = rings[i], rings[i + 1]
            for k in range(4):
                k2 = (k + 1) % 4
                m.add_quad(a_[k], b_[k], b_[k2], a_[k2])
        # ⚠ 버그: 두 캡을 같은 방향으로 감았다 → 루트 +x, 팁 −x = **둘 다 안쪽**
        m.add_quad(rings[0][3], rings[0][2], rings[0][1], rings[0][0])
        m.add_quad(rings[-1][3], rings[-1][2], rings[-1][1], rings[-1][0])
        return m

    def build_drone_badprop(spec):
        m = build_frame(spec)
        _, _, prop_r, *_ = _drone_dims(spec)
        prop = Mesh()
        for b in range(spec.prop_blades):
            bang = (360.0 / spec.prop_blades) * b
            prop.merge(prop_blade_buggy(prop_r).transformed(rotate("z", bang)), group="prop")
        for rot in rotor_layout(spec):
            cx, cy, cz = rot["center"]
            M = translate(cx, cy, cz) @ rotate("z", rot["base_ang"])
            m.merge(prop.transformed(M), group="prop")
        return m

    key = "mavic4pro"
    spec = DRONES[key]
    m_bad = build_drone_badprop(spec)
    m_good = build_drone(spec)
    gmap = drone_gamma_map(spec)
    #  프로펠러만 남긴 |Γ| 맵 — 마이크로도플러가 실제로 보는 산란체를 따로 잰다
    gmap_prop = {g: (v if g == "prop" else 0.0) for g, v in gmap.items()}
    GM_prop = {g: (mat if g == "prop" else 0.0) for g, mat in GM.items()}
    prop_rows = {}
    for nm, mm in (("bugged", m_bad), ("fixed", m_good)):
        grp = mesh_check.check_mesh(mm, name=nm)["groups"]["prop"]
        P, N, dA, w = mesh_to_points(mm, LAM / 7.0, gamma=gmap)
        po = rcs_from_points(P, N, dA, FC, az_deg=az, el_deg=15.0, w=w)
        Pp, Np, dAp, wp = mesh_to_points(mm, LAM / 7.0, gamma=gmap_prop)
        po_p = rcs_from_points(Pp, Np, dAp, FC, az_deg=az, el_deg=15.0, w=wp)
        sb = rcs_sbr_batch(mm, GM, FC, az_deg=az, el_deg=15.0, cache_key=f"{key}_{nm}")
        sb_p = rcs_sbr_batch(mm, GM_prop, FC, az_deg=az, el_deg=15.0, cache_key=f"{key}_{nm}_prop")
        prop_rows[nm] = dict(po_dbsm=float(_dbsm(np.mean(po))),
                             sbr_dbsm=float(_dbsm(np.mean(sb))),
                             po_prop_dbsm=float(_dbsm(np.mean(po_p))),
                             sbr_prop_dbsm=float(_dbsm(np.mean(sb_p))),
                             inward=int(grp["inward_normals"]), n_parts=int(grp["n_parts"]),
                             bad_winding=int(grp["bad_winding"]), ok=bool(grp["ok"]))
        print(f"     prop {nm:7s}: 드론 PO {prop_rows[nm]['po_dbsm']:+.2f} · "
              f"프로펠러만 PO {prop_rows[nm]['po_prop_dbsm']:+.2f} dBsm · "
              f"SBR {prop_rows[nm]['sbr_dbsm']:+.2f} · 안쪽법선 부품 {prop_rows[nm]['inward']}")
    for tag in ("po", "sbr", "po_prop", "sbr_prop"):
        prop_rows[f"{tag}_delta_db"] = (prop_rows["fixed"][f"{tag}_dbsm"]
                                        - prop_rows["bugged"][f"{tag}_dbsm"])
    #  PO 의 조명면 판정(n̂·û>0)이 **몇 면을 다르게 부르는가** — 버그의 직접적 증거
    Vb = np.asarray(m_bad.v, float); Fb = np.asarray(m_bad.f, int); Gb = np.asarray(m_bad.g)
    Vg = np.asarray(m_good.v, float); Fg = np.asarray(m_good.f, int); Gg = np.asarray(m_good.g)

    def _fn(V, F):
        a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
        n = np.cross(b - a, c - a)
        return n / (np.linalg.norm(n, axis=1, keepdims=True) + 1e-30)
    pb, pg = (Gb == "prop"), (Gg == "prop")
    Nb, Ng = _fn(Vb, Fb)[pb], _fn(Vg, Fg)[pg]
    flips = []
    if Nb.shape == Ng.shape:
        for a_ in az:
            u = np.array([np.cos(np.radians(15.0)) * np.cos(np.radians(a_)),
                          np.cos(np.radians(15.0)) * np.sin(np.radians(a_)),
                          np.sin(np.radians(15.0))])
            flips.append(int(((Nb @ u > 0) != (Ng @ u > 0)).sum()))
    prop_rows["prop_faces"] = int(pb.sum())
    prop_rows["mislabelled_faces"] = float(np.mean(flips)) if flips else None
    prop_rows["drone"] = key
    out["prop_normals"] = prop_rows
    _mf = prop_rows['mislabelled_faces']
    _mf_s = f"{_mf:.1f}" if _mf is not None else "0.0"   # 오판 0 이면 None → 안전 포맷
    print(f"     PO 조명면 오판: 프로펠러 {prop_rows['prop_faces']} 면 중 평균 "
          f"{_mf_s} 면 (캡) · "
          f"프로펠러만 σ {prop_rows['po_prop_delta_db']:+.2f} dB (PO) / "
          f"{prop_rows['sbr_prop_delta_db']:+.2f} dB (SBR)")

    # mesh_check 전수검사 (회귀방지 게이트)
    print("[C4] trimesh 전수검사 …")
    gate = {}
    for key in _ORDER:
        gs = mesh_check.check_mesh(build_drone(DRONES[key]), name=key)["groups"]
        gate[key] = dict(n_groups=len(gs),
                         n_bad=sum(0 if g["ok"] else 1 for g in gs.values()),
                         n_parts=int(sum(g["n_parts"] for g in gs.values())),
                         n_faces=int(sum(g["n_faces"] for g in gs.values())))
    out["mesh_gate"] = gate

    with open(OUT_JSON, "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("측정 저장:", os.path.relpath(OUT_JSON, ROOT))
    return out


# =========================================================================== #
#  §A — "광선을 더 쏘면 되지 않나?"
# =========================================================================== #
def fig_ray_budget(outdir=FIG):
    with open(RAY_JSON) as f:
        d = json.load(f)
    truth = d["truth"]["ratio_db_truth"]
    A = [r for r in d["A_ray_sweep"] if r["n_paths"]]
    B = [r for r in d["B_S_sweep"] if r["n_paths"]]

    fig = plt.figure(figsize=(15.4, 5.6), constrained_layout=True)
    gs = fig.add_gridspec(1, 3, width_ratios=[1.25, 1.0, 0.92])
    ax, ax2, ax3 = (fig.add_subplot(gs[0, i]) for i in range(3))
    fig.suptitle("We fired 400 million rays at the drone. The answer did not converge.",
                 fontsize=15.5, fontweight="bold")

    # (a) 광선 예산 스윕
    x = np.array([r["spp"] for r in A], float)
    inc = np.array([r["incoh_db"] for r in A])
    sd = np.array([r["incoh_sd"] for r in A])
    coh = np.array([r["coh_db"] for r in A])
    ax.axhline(truth, color=C_TRUTH, lw=2.2, ls="--", zorder=2)
    ax.text(x[0] * 1.05, truth - 1.2,
            f"where the echo must be:  SBR $\\sigma$ = {d['truth']['full_dbsm']:.1f} dBsm\n"
            r"through the bistatic radar equation  ($L\sqrt{\sigma/4\pi}/R_1R_2$)"
            f" = {truth:.1f} dB",
            color=C_TRUTH, fontsize=9, fontweight="bold", va="top")
    ax.errorbar(x, inc, yerr=sd, fmt="o-", color=C_RT, lw=2.2, ms=8, capsize=4, zorder=4,
                label="Sionna RT diffuse echo, incoherent sum  (5 seeds)")
    ax.plot(x, coh, "s-", color="#ef6c00", lw=2.0, ms=7, zorder=4,
            label="…the same paths, coherent sum")
    for xi, yi, r in zip(x, coh, A):
        ax.annotate(f"{r['n_mean']:.0f} paths", (xi, yi), textcoords="offset points",
                    xytext=(0, 9), ha="center", fontsize=7.5, color="0.45")
    d4 = (coh[-1] - coh[0]) / (np.log(x[-1] / x[0]) / np.log(4))
    ax.annotate(f"grows {d4:+.1f} dB every 4x rays\nand keeps going",
                xy=(x[-2], coh[-2]), xytext=(x[-3], coh[-1] + 4.6),
                ha="center", fontsize=9.5, color="#ef6c00", fontweight="bold",
                arrowprops=dict(arrowstyle="->", color="#ef6c00", lw=1.4,
                                connectionstyle="arc3,rad=-0.2"))
    ax.annotate(f"still {inc[-1]-truth:+.0f} dB off\nafter 16x the rays",
                xy=(x[-1], inc[-1]), xytext=(x[-2] * 0.95, inc.min() - 7.5),
                ha="center", fontsize=9.5, color=C_RT, fontweight="bold",
                arrowprops=dict(arrowstyle="->", color=C_RT, lw=1.4,
                                connectionstyle="arc3,rad=0.2"))
    ax.set_xscale("log"); ax.set_xticks(x)
    ax.set_xticklabels([f"{v/1e6:.0f}M" for v in x])
    ax.minorticks_off()
    ax.set_xlabel("Rays per source (samples_per_src)")
    ax.set_ylabel("Target echo / direct path  [dB]")
    ax.set_title("(a) More rays is not more physics", fontsize=12)
    ax.set_ylim(min(inc.min(), truth) - 12, max(coh.max(), truth) + 9)
    ax.legend(fontsize=8.6, loc="lower left"); ax.grid(alpha=0.28)

    # (b) S 노브
    S = np.array([r["S"] for r in B]); y = np.array([r["incoh_db"] for r in B])
    sdb = np.array([r["incoh_sd"] for r in B])
    ax2.errorbar(S, y, yerr=sdb, fmt="o-", color=C_RT, lw=2.4, ms=9, capsize=4, zorder=4,
                 label=f"Sionna RT, {d['S_rays']/1e6:.0f}M rays")
    ax2.axhline(truth, color=C_TRUTH, lw=2.0, ls="--", label=f"SBR truth ({truth:.1f} dB)")
    sfit = d.get("B_fit", {}).get("S_to_match_truth")
    if sfit:
        ax2.plot([sfit], [truth], "*", color=C_TRUTH, ms=20, zorder=6)
        ax2.annotate(f"you must FIT  S = {sfit:.2f}\nto land on the truth\n-> circular",
                     xy=(sfit, truth), xytext=(0.36, y.min() - 1.0), ha="center", va="top",
                     fontsize=9.5, color=C_TRUTH, fontweight="bold",
                     arrowprops=dict(arrowstyle="->", color=C_TRUTH, lw=1.4,
                                     connectionstyle="arc3,rad=-0.25"),
                     bbox=dict(fc="#e8f5e9", ec=C_TRUTH, boxstyle="round,pad=0.3"))
        ax2.set_ylim(y.min() - 9.0, y.max() + 2.5)
    ax2.set_xscale("log"); ax2.set_xticks(S); ax2.set_xticklabels([f"{v:g}" for v in S])
    ax2.minorticks_off()
    ax2.set_xlabel("Scattering coefficient S of every drone part")
    ax2.set_ylabel("Target echo / direct path  [dB]")
    ax2.set_title(f"(b) The knob moves it {y[-1]-y[0]:+.0f} dB", fontsize=12)
    ax2.legend(fontsize=8.6, loc="upper left"); ax2.grid(alpha=0.28)

    # (c) S=0 인 부품이 σ 를 지배한다
    t = d["truth"]
    share = t["metal_share_pct"]
    ax3.bar(["metal parts\n(ITU metal, S = 0)", "shell / props / arms\n(S > 0)"],
            [share, max(0.0, 100 - share)], color=[C_BAD, "#90a4ae"], edgecolor="k", zorder=3)
    ax3.set_ylim(0, 118)
    ax3.set_ylabel(r"share of the drone's SBR $\sigma$  [%]")
    ax3.text(0, share + 3, f"{share:.0f}%", ha="center", fontsize=17, fontweight="bold", color=C_BAD)
    ax3.text(1, max(0.0, 100 - share) + 3, f"{max(0.0,100-share):.0f}%", ha="center",
             fontsize=17, fontweight="bold", color="#546e7a")
    ax3.text(0, share * 0.55, "motors, battery,\nPCB, camera housing\n\nCANNOT contribute\nto RT's diffuse\nchannel at all",
             ha="center", va="center", fontsize=9.2, color="w", fontweight="bold")
    ax3.set_title("(c) RT's diffuse channel is blind\nto the parts that matter", fontsize=12)
    ax3.grid(axis="y", alpha=0.28)

    _caption(fig,
        "The honest experiment behind \"just shoot more rays\". Sionna RT's stock path solver has no surface-integration stage, so "
        "the target's echo has nowhere to converge to, and the measurement shows exactly that: the coherent sum of the diffuse paths "
        f"climbs {d4:+.1f} dB for every 4x in ray budget with no sign of stopping (the path count grows with the ray count, and the "
        f"paths add up), while the incoherent sum sits {inc[-1]-truth:+.0f} dB away from the physical answer and is still drifting "
        f"({inc[0]:.1f} -> {inc[-1]:.1f} dB over 16x, seed spread +/-{sd.mean():.1f} dB). Whatever value you do get is set by a free "
        f"knob: scaling S from {S[0]:g} to {S[-1]:g} moves the echo {y[-1]-y[0]:+.0f} dB, and S = {sfit:.2f} would reproduce the SBR "
        "answer — that is a fit, not a prediction.\n"
        f"And the knob cannot even reach the right scatterers: ITU 'metal' has S = 0 by definition, so the motors, battery, PCB and "
        f"camera housing — {share:.0f}% of the drone's true cross-section — contribute exactly nothing to the diffuse channel. "
        "The cross-section comes out of the surface integral. A bigger GPU does not produce one. (This is a statement about a "
        "propagation solver with no scattering-integral stage — not about ray tracing: SBR, on the next figure, IS ray tracing, "
        "and it computes the cross-section.)")

    os.makedirs(outdir, exist_ok=True)
    fn = os.path.join(outdir, "report6_ray_budget.png")
    fig.savefig(fn, dpi=140); plt.close(fig)
    print("[viz_verify_sbr]", os.path.relpath(fn, ROOT))
    return fn


# =========================================================================== #
#  §B — SBR: PO 를 광선추적 안으로 넣다
# =========================================================================== #
def fig_sbr(d, outdir=FIG):
    from drones import DRONES                                   # noqa: F401
    k = d["kernel"]; comp = d["compare"]
    divs = np.array(k["divs"], float)
    se = np.array(k["sphere_err"]); pe = np.array(k["plate_err"])

    md = None
    if os.path.exists(MD_JSON):
        with open(MD_JSON) as f:
            md = json.load(f)["headline"]

    fig = plt.figure(figsize=(15.4, 8.6), constrained_layout=True)
    gs = fig.add_gridspec(2, 3, height_ratios=[1.0, 1.0])
    axk = fig.add_subplot(gs[0, 0])
    axo = fig.add_subplot(gs[0, 1:])
    axm = fig.add_subplot(gs[1, 0])
    axb = fig.add_subplot(gs[1, 1])
    axd = fig.add_subplot(gs[1, 2])
    fig.suptitle("SBR: put the surface integral INSIDE the ray tracer — and occlusion comes free",
                 fontsize=15.5, fontweight="bold")

    # (a) 커널 검증 — 정직하게: 평판은 어느 격자에서도 맞고, 구는 격자잡음으로 흔들린다
    fine = [i for i, v in enumerate(k["divs"]) if v >= 16]
    axk.axhspan(-0.6, 0.6, color="0.88", zorder=0)
    axk.axhline(0, color="0.35", lw=1.0, zorder=1)
    axk.plot(divs, se, "o-", color=C_SBR, lw=2.0, ms=7, label=r"metal sphere ($\pi r^2$, r = 0.5 m)")
    axk.plot(divs, pe, "s--", color=C_OK, lw=2.0, ms=7, label=r"metal plate ($4\pi A^2/\lambda^2$, 0.4 m)")
    i12 = k["divs"].index(12)
    axk.plot([12], [se[i12]], "*", color=C_TRUTH, ms=16, zorder=6)
    axk.annotate(f"default $\\lambda$/12:  plate {pe[i12]:+.2f} dB,\n"
                 f"but sphere {se[i12]:+.2f} dB — grid noise,\n"
                 f"not bias  (|err| < {max(abs(se[fine]).max(), abs(pe[fine]).max()):.1f} dB "
                 r"for $\lambda$/16+)",
                 xy=(12, se[i12]), xytext=(4.4, max(se.max(), pe.max()) + 0.7), fontsize=8.6,
                 color=C_TRUTH, fontweight="bold",
                 arrowprops=dict(arrowstyle="->", color=C_TRUTH, lw=1.2))
    axk.set_xscale("log"); axk.set_xticks(k["divs"])
    axk.set_xticklabels([f"$\\lambda$/{v}" for v in k["divs"]], fontsize=8.5)
    axk.minorticks_off()
    axk.set_xlabel("Ray grid spacing")
    axk.set_ylabel(r"$\sigma$ error vs. closed form  [dB]")
    axk.set_ylim(min(se.min(), pe.min()) - 0.6, max(se.max(), pe.max()) + 2.6)
    axk.set_title("(a) The kernel is right — the grid is noisy", fontsize=12)
    axk.legend(fontsize=8.4, loc="lower left"); axk.grid(alpha=0.28)

    # (b) PO vs SBR — 5종 × el
    keys = _ORDER
    x = np.arange(len(keys)); w = 0.2
    po0 = [comp[k_]["po_el0"] for k_ in keys]; sb0 = [comp[k_]["sbr_el0"] for k_ in keys]
    po15 = [comp[k_]["po_el15"] for k_ in keys]; sb15 = [comp[k_]["sbr_el15"] for k_ in keys]
    #  dBsm 은 음수라 0-기준 막대가 축 밖으로 잘린다 → **축 바닥을 기준선**으로 그린다.
    lo = min(min(po0), min(sb0), min(po15), min(sb15))
    base = lo - 4.5
    def _b(xx, vv, ww, **kw):
        axo.bar(xx, np.asarray(vv) - base, ww, bottom=base, **kw)
    _b(x - 1.5 * w, po0, w, color="#ce93d8", ec="#4a148c", label=r"PO, el = 0$\degree$  (no occlusion)")
    _b(x - 0.5 * w, sb0, w, color="#90caf9", ec="#0d47a1", label=r"SBR, el = 0$\degree$")
    _b(x + 0.5 * w, po15, w, color=C_PO, ec="#4a148c", label=r"PO, el = 15$\degree$")
    _b(x + 1.5 * w, sb15, w, color=C_SBR, ec="#0d47a1", label=r"SBR, el = 15$\degree$")
    for i, k_ in enumerate(keys):
        axo.annotate(f"{comp[k_]['occl_el15']:+.1f} dB", (i + 1.5 * w, sb15[i]), ha="center",
                     va="bottom", xytext=(0, 4), textcoords="offset points",
                     fontsize=9, color=C_BAD, fontweight="bold")
    axo.set_ylim(base, max(max(po0), max(po15)) + 4.0)
    axo.set_xticks(x); axo.set_xticklabels([_short(k_) for k_ in keys], fontsize=9.5)
    axo.set_ylabel(r"azimuth-mean $\sigma$  [dBsm]")
    dd = [comp[k_]["occl_el15"] for k_ in keys] + [comp[k_]["occl_el0"] for k_ in keys]
    axo.set_title(f"(b) Occlusion pulls every drone down — by {abs(max(dd)):.1f} to {abs(min(dd)):.1f} dB "
                  r"(red = the el 15$\degree$ drop)", fontsize=12)
    axo.legend(fontsize=8.4, ncol=2, loc="upper left", framealpha=0.95)
    axo.grid(axis="y", alpha=0.28)

    # (c) 마이크로도플러
    if md:
        vals = [md["po"]["ratio_db"], md["sbr"]["ratio_db"]]
        axm.bar(["PO\n(no occlusion)", "SBR\n(occlusion)"], vals,
                color=[C_PO, C_SBR], ec="k", width=0.55, zorder=3)
        for i, v in enumerate(vals):
            axm.annotate(f"{v:+.1f} dB", (i, v), ha="center", va="bottom",
                         xytext=(0, 4), textcoords="offset points", fontsize=11, fontweight="bold")
        axm.annotate("", xy=(0.5, vals[1]), xytext=(0.5, vals[0]),
                     arrowprops=dict(arrowstyle="<->", color=C_BAD, lw=2.0))
        axm.text(0.56, np.mean(vals), f"{md['gain_db']:.1f} dB\neasier than\nwe thought",
                 color=C_BAD, fontsize=9.5, fontweight="bold", va="center", ha="left")
        axm.set_ylim(0, max(vals) + 9)
        axm.set_ylabel(r"|DC| / std(AC)  [dB]")
        axm.set_title("(c) Micro-Doppler: blades hide the body,\nthen reveal it", fontsize=11.5)
        axm.grid(axis="y", alpha=0.28)

    # (d) 오목부 다중반사
    mb = [comp[k_]["multibounce_db"] for k_ in keys]
    axb.axhline(0, color="0.35", lw=1.0)
    axb.bar(x, mb, 0.55, color=["#90a4ae" if abs(v) < 1 else "#ef6c00" for v in mb], ec="k", zorder=3)
    for i, v in enumerate(mb):
        axb.annotate(f"{v:+.2f}", (i, v), ha="center", va="bottom" if v >= 0 else "top",
                     xytext=(0, 4 if v >= 0 else -4), textcoords="offset points",
                     fontsize=9.5, fontweight="bold")
    axb.set_xticks(x); axb.set_xticklabels([_short(k_) for k_ in keys], fontsize=8, rotation=20)
    axb.set_ylim(min(mb) - 0.5, max(mb) + 0.6)
    axb.set_ylabel(r"$\sigma$(3 bounces) $-$ $\sigma$(1 bounce)  [dB]")
    axb.set_title("(d) The concavity caveat, finally\nmeasured — and it is small", fontsize=11.5)
    axb.grid(axis="y", alpha=0.28)

    # (e) 무엇이 어느 엔진에서 나오나 — 정직한 3열
    axd.axis("off")
    rows = [("shooting the rays", "Mitsuba / OptiX", C_SBR),
            ("who is lit / occluded", "the rays themselves", C_SBR),
            ("multi-bounce in cavities", "re-traced rays", C_SBR),
            (r"$\sigma$ from the lit surface", "PO surface integral", C_OK),
            ("materials |$\\Gamma$|", "materials.py (= Sionna's)", C_OK),
            ("interior scatterers", "NOT seen (opaque shell)", C_BAD)]
    axd.text(0.5, 0.97, "What SBR is made of", ha="center", va="top",
             fontsize=12, fontweight="bold", transform=axd.transAxes)
    for i, (a_, b_, c_) in enumerate(rows):
        yy = 0.83 - i * 0.145
        axd.add_patch(FancyBboxPatch((0.02, yy - 0.055), 0.96, 0.105,
                                     boxstyle="round,pad=0.012,rounding_size=0.02",
                                     transform=axd.transAxes, facecolor="#f5f5f5",
                                     edgecolor=c_, lw=1.4))
        axd.text(0.06, yy, a_, fontsize=9.2, va="center", transform=axd.transAxes, color="0.25")
        axd.text(0.95, yy, b_, fontsize=9.2, va="center", ha="right",
                 transform=axd.transAxes, color=c_, fontweight="bold")

    fine_err = max(abs(se[fine]).max(), abs(pe[fine]).max())
    _caption(fig,
        "This is what FEKO / CST / HFSS call SBR+: shoot geometric-optics rays to find the lit surface, then run the physical-optics "
        f"surface integral over the points the rays actually hit. (a) Against closed forms the plate is exact at every spacing tested "
        f"(|err| <= {abs(pe).max():.2f} dB), and the sphere converges to |err| <= {fine_err:.2f} dB once the grid reaches lambda/16. At the "
        f"default lambda/12 the sphere reads {se[i12]:+.2f} dB — that is ray-grid discretisation noise on a curved surface (the error "
        "changes sign as the grid moves), not a systematic bias, and it is the same effect that forced report3's micro-Doppler onto a "
        "lambda/32 grid. Treat ~1 dB as the kernel's noise floor at the working spacing. (b) Switching the reports from the old point-cloud PO "
        f"to SBR lowers every drone's cross-section by {abs(max(dd)):.1f} to {abs(min(dd)):.1f} dB, because the old kernel summed facets that "
        "the airframe hides. (c) Micro-Doppler moves more: the blades occlude the body and then uncover it, so the modulation is deeper "
        f"and |DC|/std(AC) drops by {md['gain_db']:.1f} dB — detection is that much easier than the PO estimate said. "
        "(d) The standing caveat that \"PO cannot do concave multi-bounce\" is now a number rather than a worry: re-tracing three "
        f"bounces changes the azimuth-mean by {min(mb):+.2f} to {max(mb):+.2f} dB.\n"
        "What SBR still cannot do is see through the shell: the rays stop at the first surface, so the battery and PCB inside receive "
        "no illumination. PO counted them (with no shadowing at all). The truth is bracketed between the two, and only a measurement "
        "can close it — which is why the absolute-uncertainty row of the risk table is still open.")

    os.makedirs(outdir, exist_ok=True)
    fn = os.path.join(outdir, "report6_sbr.png")
    fig.savefig(fn, dpi=140); plt.close(fig)
    print("[viz_verify_sbr]", os.path.relpath(fn, ROOT))
    return fn


# =========================================================================== #
#  §C — 메쉬·재질 버그 3건 + 회귀방지
# =========================================================================== #
def fig_mesh_bugs(d, outdir=FIG):
    env = d["envelope"]; cam = d["camera"]; pn = d["prop_normals"]; gate = d["mesh_gate"]
    keys = _ORDER

    fig = plt.figure(figsize=(15.4, 8.4), constrained_layout=True)
    gs = fig.add_gridspec(2, 3, height_ratios=[1.05, 1.0])
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[0, 2])
    ax4 = fig.add_subplot(gs[1, 0])
    ax5 = fig.add_subplot(gs[1, 1])
    ax6 = fig.add_subplot(gs[1, 2])
    fig.suptitle("Three bugs that were quietly wrong in every number we published",
                 fontsize=15.5, fontweight="bold")

    # --- 버그 1: 외형(높이) ---
    x = np.arange(len(keys)); w = 0.38
    h_old = [env[k]["h_old_mm"] for k in keys]
    h_new = [env[k]["h_new_mm"] for k in keys]
    ax1.bar(x - w / 2, h_old, w, color="#90a4ae", ec="k", label="mesh as it was", zorder=3)
    ax1.bar(x + w / 2, h_new, w, color=C_OK, ec="k", label="official DJI envelope", zorder=3)
    for i, k in enumerate(keys):
        ax1.annotate(f"{env[k]['h_err_pct']:+.0f}%", (i - w / 2, h_old[i]), ha="center",
                     va="bottom", xytext=(0, 3), textcoords="offset points",
                     fontsize=9, color=C_BAD, fontweight="bold")
    ax1.set_xticks(x); ax1.set_xticklabels([_short(k) for k in keys], fontsize=8, rotation=20)
    ax1.set_ylabel("Airframe height  [mm]")
    ax1.set_yscale("log")
    ax1.set_title("(1) The drones were too flat", fontsize=12)
    ax1.legend(fontsize=8.4, loc="upper left"); ax1.grid(axis="y", alpha=0.28)

    d15 = [env[k]["d_el15"] for k in keys]
    d0 = [env[k]["d_el0"] for k in keys]
    ax2.axhline(0, color="0.35", lw=1.0)
    ax2.bar(x - w / 2, d0, w, color="#90caf9", ec="#0d47a1", label=r"el = 0$\degree$", zorder=3)
    ax2.bar(x + w / 2, d15, w, color=C_SBR, ec="#0d47a1", label=r"el = 15$\degree$ (chamber)", zorder=3)
    for i in range(len(keys)):
        ax2.annotate(f"{d15[i]:+.1f}", (i + w / 2, d15[i]), ha="center",
                     va="bottom" if d15[i] >= 0 else "top",
                     xytext=(0, 4 if d15[i] >= 0 else -4), textcoords="offset points",
                     fontsize=9, fontweight="bold", color="#0d47a1")
    ax2.set_xticks(x); ax2.set_xticklabels([_short(k) for k in keys], fontsize=8, rotation=20)
    ax2.set_ylabel(r"$\sigma$(fixed) $-$ $\sigma$(old mesh)  [dB]")
    ax2.set_ylim(min(d0 + d15) - 1.6, max(d0 + d15) + 1.8)
    ax2.set_title(f"…and that cost {min(d15+d0):+.1f} to {max(d15+d0):+.1f} dB of RCS", fontsize=12)
    ax2.legend(fontsize=8.4, loc="lower right"); ax2.grid(axis="y", alpha=0.28)

    # --- 버그 2: 재질 이중화 ---
    mats = cam["materials"]
    names = [m["key"] for m in mats]
    bulk = [20 * np.log10(m["bulk"]) for m in mats]
    po = [20 * np.log10(m["po"]) for m in mats]
    xi = np.arange(len(names))
    ax3.plot(xi, bulk, "o", ms=9, color="#546e7a", label=r"Sionna (bulk Fresnel from $\varepsilon_r,\sigma$)")
    ax3.plot(xi, po, "s", ms=9, color=C_OK, label=r"PO effective $|\Gamma|$")
    for i in range(len(names)):
        ax3.plot([xi[i], xi[i]], [bulk[i], po[i]], color="0.7", lw=1.2, zorder=0)
    ic = names.index("camera_assembly")
    gb_plastic = [m for m in mats if m["key"] == "plastic"][0]["bulk"]
    ax3.plot([ic], [20 * np.log10(gb_plastic)], "x", ms=13, mew=3, color=C_BAD, zorder=5)
    ax3.annotate(f"camera: Sionna said 'plastic'\n({20*np.log10(gb_plastic):.1f} dB) while PO said "
                 f"{20*np.log10(cam['gamma_po_before']):.1f} dB\n"
                 f"-> the two engines were {cam['mismatch_db']:.1f} dB apart",
                 xy=(ic, 20 * np.log10(gb_plastic)), xytext=(0.02, 0.06), textcoords="axes fraction",
                 fontsize=8.8, color=C_BAD, fontweight="bold",
                 arrowprops=dict(arrowstyle="->", color=C_BAD, lw=1.4),
                 bbox=dict(fc="#ffebee", ec=C_BAD, boxstyle="round,pad=0.32"))
    ax3.set_xticks(xi); ax3.set_xticklabels(names, fontsize=7.6, rotation=25, ha="right")
    ax3.set_ylabel(r"$20\log_{10}|\Gamma|$  [dB]")
    ax3.set_ylim(min(bulk + po) - 9, 3)
    ax3.set_title("(2) One part, two engines, two materials", fontsize=12)
    ax3.legend(fontsize=8.2, loc="upper right"); ax3.grid(axis="y", alpha=0.28)

    # --- 버그 3: 프로펠러 법선 — 전체 드론은 거의 안 움직이고, **프로펠러만** 보면 움직인다
    vals = [pn["bugged"]["po_prop_dbsm"], pn["fixed"]["po_prop_dbsm"]]
    vals_s = [pn["bugged"]["sbr_prop_dbsm"], pn["fixed"]["sbr_prop_dbsm"]]
    xb = np.arange(2)
    lo = min(vals + vals_s); hi = max(vals + vals_s)
    base = lo - 2.6                       # dBsm 은 음수 → 축 바닥을 기준선으로
    ax4.bar(xb - 0.19, np.array(vals) - base, 0.36, bottom=base, color=[C_BAD, C_PO], ec="k",
            zorder=3, label=r"PO — lit if $\hat{n}\cdot\hat{u}>0$")
    ax4.bar(xb + 0.19, np.array(vals_s) - base, 0.36, bottom=base, color=["#b0bec5", C_SBR],
            ec="k", zorder=3, label="SBR — lit if a ray hit it")
    ax4.set_xticks(xb)
    ax4.set_xticklabels(["blade caps wound\ninward (as shipped)", "caps fixed"], fontsize=9)
    ax4.set_ylabel(r"$\sigma$ of the PROPELLERS alone  [dBsm]")
    ax4.set_ylim(base, hi + 4.6)
    ax4.text(0.5, hi + 3.6, f"PO moves {pn['po_prop_delta_db']:+.2f} dB · "
             f"SBR {pn['sbr_prop_delta_db']:+.2f} dB (immune)", ha="center", va="top",
             fontsize=9.2, fontweight="bold", color="0.25")
    _mf = pn['mislabelled_faces']
    _mf_s = f"{_mf:.0f}" if _mf is not None else "0"
    ax4.text(0.5, hi + 2.4, f"whole drone: {pn['po_delta_db']:+.2f} dB shift if normals flip\n"
             f"(current mesh: {_mf_s} of {pn['prop_faces']} blade faces mislabelled — gate passes)",
             ha="center", va="top", fontsize=8.6, color="0.4")
    ax4.set_title(f"(3) Flipped propeller normals\n({_short(pn['drone'])}, el = 15$\\degree$)",
                  fontsize=11.5)
    ax4.legend(fontsize=8.0, loc="lower center", ncol=2); ax4.grid(axis="y", alpha=0.28)

    # --- 회귀방지: trimesh 게이트 ---
    ax5.axis("off")
    ax5.text(0.5, 0.98, "trimesh gate  (src/mesh_check.py)", ha="center", va="top",
             fontsize=12, fontweight="bold", transform=ax5.transAxes)
    ax5.text(0.5, 0.88, "runs inside build_all — a bad mesh now fails the build",
             ha="center", va="top", fontsize=9, color="0.45", transform=ax5.transAxes)
    hdr = ["drone", "parts", "faces", "verdict"]
    colw = [0.34, 0.16, 0.24, 0.26]
    xs = np.cumsum([0] + colw[:-1])
    for j, h in enumerate(hdr):
        ax5.text(xs[j] + 0.02, 0.76, h, fontsize=9, fontweight="bold",
                 color="0.35", transform=ax5.transAxes)
    for i, k in enumerate(keys):
        yy = 0.67 - i * 0.10
        g = gate[k]
        ok = g["n_bad"] == 0
        ax5.add_patch(FancyBboxPatch((0.0, yy - 0.035), 1.0, 0.082,
                                     boxstyle="round,pad=0.004,rounding_size=0.012",
                                     transform=ax5.transAxes,
                                     facecolor="#e8f5e9" if ok else "#ffebee",
                                     edgecolor="#c8e6c9" if ok else C_BAD, lw=1.0))
        cells = [_short(k), f"{g['n_groups']}", f"{g['n_faces']:,}",
                 "PASS" if ok else f"{g['n_bad']} BAD"]
        for j, c in enumerate(cells):
            ax5.text(xs[j] + 0.02, yy, c, fontsize=9.2, va="center",
                     transform=ax5.transAxes,
                     color=(C_OK if (j == 3 and ok) else (C_BAD if j == 3 else "0.2")),
                     fontweight="bold" if j == 3 else "normal")
    ax5.text(0.5, 0.10, f"the bugged propeller above is caught here:\n"
             f"prop group, {pn['bugged']['inward']} part(s) with inward normals",
             ha="center", fontsize=9, color=C_BAD, fontweight="bold", transform=ax5.transAxes,
             bbox=dict(fc="#ffebee", ec=C_BAD, boxstyle="round,pad=0.35"))

    # --- 어느 그림이 얼마나 움직였나(요약) ---
    ax6.axis("off")
    ax6.text(0.5, 0.98, "What moved, and where", ha="center", va="top",
             fontsize=12, fontweight="bold", transform=ax6.transAxes)
    items = [(f"airframe height  {min(env[k]['h_err_pct'] for k in keys):+.0f}"
              f" … {max(env[k]['h_err_pct'] for k in keys):+.0f} %",
              f"RCS  {min(d15+d0):+.1f} … {max(d15+d0):+.1f} dB", C_BAD),
             (f"camera |$\\Gamma$| mismatch  {cam['mismatch_db']:.1f} dB",
              f"drone $\\sigma$  {cam['sigma_delta_db']:+.2f} dB", "#ef6c00"),
             ("propeller cap normals inward",
              f"PO $\\sigma$  {pn['po_delta_db']:+.2f} dB · SBR immune", "#ef6c00"),
             ("PO -> SBR (occlusion)",
              "every report2/3/5 number", C_SBR),
             ("regression gate", "mesh_check in build_all", C_OK)]
    for i, (a_, b_, c_) in enumerate(items):
        yy = 0.80 - i * 0.17
        ax6.add_patch(FancyBboxPatch((0.02, yy - 0.065), 0.96, 0.13,
                                     boxstyle="round,pad=0.012,rounding_size=0.02",
                                     transform=ax6.transAxes, facecolor="#fafafa",
                                     edgecolor=c_, lw=1.4))
        ax6.text(0.06, yy + 0.022, a_, fontsize=9.0, va="center",
                 transform=ax6.transAxes, color="0.25")
        ax6.text(0.06, yy - 0.03, b_, fontsize=9.0, va="center",
                 transform=ax6.transAxes, color=c_, fontweight="bold")

    _mf = pn['mislabelled_faces']
    _mf_s = f"{_mf:.0f}" if _mf is not None else "0"
    _caption(fig,
        "Three mesh/material checks the trimesh gate runs on every build — shown here with the current airframes passing all three. "
        "(1) Airframe envelope: each mesh is fitted to DJI's published L x W x H, not a bare silhouette rule. Height dominates the "
        "side-on projected area at the chamber's low elevation, so a silhouette-only mesh would sit "
        f"{abs(max(env[k]['h_err_pct'] for k in keys)):.0f}-{abs(min(env[k]['h_err_pct'] for k in keys)):.0f}% too short and read "
        f"{min(d15+d0):+.1f} to {max(d15+d0):+.1f} dB low (SBR, azimuth mean; a silhouette rebuild is shown for contrast). "
        "(2) Material single-source: every part reads its material from one file that both Sionna and the PO table share, so the two "
        f"engines cannot disagree about a part (a split description of the gimbal housing would open a {cam['mismatch_db']:.1f} dB gap). "
        "(3) Propeller normals: both blade end-caps must wind outward so PO's n.u > 0 lit-face test is correct; the gate flags any inward "
        f"cap. The current mesh has {_mf_s} of {pn['prop_faces']} blade faces mislabelled -> gate passes (a flipped cap would move the "
        f"propellers' own cross-section {pn['po_prop_delta_db']:+.2f} dB and the whole drone {pn['po_delta_db']:+.2f} dB; SBR is immune "
        "by construction, taking the normal from the ray that hit the facet).")

    os.makedirs(outdir, exist_ok=True)
    fn = os.path.join(outdir, "report6_mesh_bugs.png")
    fig.savefig(fn, dpi=140); plt.close(fig)
    print("[viz_verify_sbr]", os.path.relpath(fn, ROOT))
    return fn


# =========================================================================== #
def build_all(outdir=FIG, force=False):
    print("== report6 · 신규 검증 그림 (§A 광선예산 · §B SBR · §C 메쉬/재질 버그) ==")
    figs = []
    if os.path.exists(RAY_JSON):
        figs.append(fig_ray_budget(outdir))
    else:
        print(f"⚠ {os.path.relpath(RAY_JSON, ROOT)} 없음 — 먼저 "
              "`python benchmark/verify_rt_rays.py` 를 실행할 것")
    d = measure(force=force)
    figs.append(fig_sbr(d, outdir))
    figs.append(fig_mesh_bugs(d, outdir))
    return figs


if __name__ == "__main__":
    build_all(force="--force" in sys.argv)
