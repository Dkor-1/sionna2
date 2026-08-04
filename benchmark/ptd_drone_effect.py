# -*- coding: utf-8 -*-
"""
ptd_drone_effect.py — 검증 3: 드론에서 PTD 모서리항의 **효과와 비용**
=====================================================================

묻는 것 네 가지
  1. 모서리가 많은 기체 / 적은 기체에서 ptd=False vs ptd=True 의 σ
  2. ⭐ **대역 기울기(dB/GHz)** 가 PTD 로 어떻게 변하는가 — Das 측정 0.210 dB/GHz 와의 격차가 줄어드는가
  3. **비용** — 면적분 시간 대 모서리 선적분 시간 (Gao 의 +4.6~17.2% 옆에)
  4. **per-pose 절대 런타임** — Ziganshin "PO cascade negates RT advantage" 반론용

⚠ 세 가지 정직성 경고를 결과와 함께 들고 다닌다.
  (a) **엔진** — 여기는 PO 점구름 엔진(가림 없음, CPU)이다. 생산 σ 는 SBR(가림 포함, GPU) 이다.
      `ptd_edges.attach_to_sbr_field` 는 Mitsuba 가 필요해 이 실행에서 쓰지 않았다.
      비교를 위해 생산 SBR 값(outputs/report13_sigma_grid.json)을 같은 표에 실어 놓는다.
  (b) **정규화** — `edge_field` 의 상수는 **−½ 이고 크기·부호 둘 다 검증됐다**(2026-08-03,
      결함 D-1 수리). 평판 on-cone 모서리에서 `arg(A_code/A_analytic)=0°`, `|ratio|−1=1.4e−14`.
      ×0.5/×2 감도는 '상수를 몰라서'가 아니라 재질·형상 민감도 표시용으로만 남긴다.
      ⚠ 대신 살아 있는 경고는 **오목 모서리(N<1) 제외**(D-3)와 **이음매 문턱 밴드**(D-5)다.
  (c) **밴드 구간** — 우리 1.8~5.8 GHz vs Das 1.8~18.2 GHz. **같은 창이 아니다.**

3점 적합은 코히어런트 반점(speckle) 때문에 기울기가 요동한다. 그래서 기울기의 본선은
**조밀 주파수 격자(1.8~5.8 GHz, 0.25 GHz)** 회귀로 내고, 3점 적합은 기존 헤드라인 규약과의
연결용으로 같이 낸다. 기울기마다 표준오차를 붙인다.

CPU 전용. GPU 를 쓰지 않는다.

    PYTHONPATH=src python benchmark/ptd_drone_effect.py
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_SRC = os.path.join(ROOT, "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import ptd_edges as pe                                                    # noqa: E402
from rcs_po import C0, mesh_to_points, dbsm                               # noqa: E402
from drones import DRONES, build_drone, drone_gamma_map                   # noqa: E402

# --------------------------------------------------------------------------- #
#  설정
# --------------------------------------------------------------------------- #
#  기체 두 대 — 모서리 많은 것 / 적은 것. 판정 근거는 **금속 모서리 총길이** L_metal
#  (PTD 선적분에 실제로 들어가는 양). 편대 실측:
#     s1000plus 18.20 m = 213 λ @3.5 GHz  ← 최대 (열린 카본 트러스 프레임)
#     mini5pro   5.93 m =  69 λ, 총 모서리길이 41.65 m 로 편대 최소 (닫힌 셸)
DRONE_MANY = "s1000plus"
DRONE_FEW = "mini5pro"

#: 3점 밴드 두 벌. 'project' = src/experiment_freespace_sigma.BANDS (기존 헤드라인이 나온 격자)
#:                'task'    = 의뢰문이 적은 근사 반송파 (LTE~2.1 / 5G~3.5 / WiFi~5.8)
BAND_SETS = {
    "project_1p843_3p5_5p21": {"LTE 1.843 GHz": 1.843e9, "5G 3.5 GHz": 3.500e9,
                               "WiFi 5.21 GHz": 5.210e9},
    "task_2p1_3p5_5p8": {"LTE 2.1 GHz": 2.100e9, "5G 3.5 GHz": 3.500e9,
                         "WiFi 5.8 GHz": 5.800e9},
}
NAMED_F = sorted({f for s in BAND_SETS.values() for f in s.values()})
DENSE_F = sorted(set(np.round(np.arange(1.80, 5.801, 0.25) * 1e9).tolist()) | set(NAMED_F))

#: 대표 자세 — 방위는 생산 격자 그대로(0..357°, 3°). 고도는 EL_GRID 의 양끝 + 생산 대표값 3 컷만.
AZ = np.arange(0.0, 360.0, 3.0)
EL_CUTS = [0.0, -2.0, -20.0]
POLS = ("V", "H")
#  SPACING_DIV: ptd=True 로 코히어런트 합을 하는 순간 PO 는 λ/20 이하여야 한다(D-8).
#  λ/7(rcs_po 기본)에서는 PO 중점구적 오차가 프린지 진폭의 3~11 % 라 '보정'과
#  '자기 구적오차 상쇄'가 분리되지 않는다.
SPACING_DIV = 20
AZ_CHUNK = 24                         # 면적분 메모리 상한용 (값에는 영향 없음)

DAS_SLOPE = 0.210                     # Das, IEEE WCL 15:3731 (2026), Phantom 3, 1.8–18.2 GHz
DAS_BAND_GHZ = (1.8, 18.2)
OUR_BAND_GHZ = (1.8, 5.8)

#: 생산 SBR 대조 (물리적 타당성 검사용)
PROD_GRID = os.path.join(ROOT, "outputs", "report13_sigma_grid.json")


# --------------------------------------------------------------------------- #
def _po_chunked(P, Nv, dA, fc, az, el, w=None):
    """_po_field_dirs 를 방위 묶음으로 쪼개 부른다. 방위별 합은 서로 독립이라 값은 동일하다."""
    out = np.zeros(len(az), dtype=np.complex128)
    for s in range(0, len(az), AZ_CHUNK):
        e = min(s + AZ_CHUNK, len(az))
        out[s:e] = pe._po_field_dirs(P, Nv, dA, fc, az[s:e], el, w=w)
    return out


def run_config(mesh, gm, edges, fc, az, el, keep_arrays=False):
    """한 (기체, 주파수, 고도) 조합. PO 는 한 번만 계산해 두 편파·두 모드가 공유한다."""
    lam = C0 / fc
    sp = lam / SPACING_DIV

    t0 = time.perf_counter()
    P, Nv, dA, w = mesh_to_points(mesh, sp, gamma=gm)
    t_pc = time.perf_counter() - t0

    t0 = time.perf_counter()
    E = _po_chunked(P, Nv, dA, fc, az, el, w=w)
    t_su = time.perf_counter() - t0

    K = 4 * np.pi / lam ** 2
    sig_po = K * np.abs(E) ** 2

    rec = dict(fc_hz=float(fc), lam_m=float(lam), el_deg=float(el), n_az=int(len(az)),
               n_points=int(len(dA)), spacing_m=float(sp),
               t_pointcloud_s=t_pc, t_surface_s=t_su,
               sigma_po_mean_dbsm=float(dbsm(sig_po.mean())),
               sigma_po_median_dbsm=float(dbsm(np.median(sig_po))))

    U = pe._look_dirs(az, el)
    for pol in POLS:
        A = np.zeros(len(az), dtype=np.complex128)
        nseg_used = nseg_tot = ndrop_mat = ndrop_sina = ndrop_edgeon = nreg = 0
        Lused = 0.0
        t0 = time.perf_counter()
        for i, u in enumerate(U):
            a, m = pe.edge_field(edges, fc, u, pol=pol)
            A[i] = a
            nseg_used += m["n_seg_used"]; nseg_tot += m["n_seg_total"]
            ndrop_mat += m["n_drop_material"]; ndrop_sina += m["n_drop_sin_a"]
            ndrop_edgeon += m["n_drop_edge_on"]; nreg += m["n_regularized"]
            Lused += m["length_used_m"]
        t_ed = time.perf_counter() - t0

        sig_pt = K * np.abs(E + A) ** 2
        sig_ed = K * np.abs(A) ** 2                    # 모서리항 **단독** σ (기울기 진단용)
        d = dbsm(sig_pt) - dbsm(sig_po)
        sens = {}
        for c in (0.5, 2.0):
            s_c = K * np.abs(E + c * A) ** 2
            sens[f"x{c:g}"] = float(dbsm(s_c.mean()) - dbsm(sig_po.mean()))

        rec[pol] = dict(
            t_edge_s=t_ed,
            sigma_ptd_mean_dbsm=float(dbsm(sig_pt.mean())),
            sigma_ptd_median_dbsm=float(dbsm(np.median(sig_pt))),
            sigma_edge_only_mean_dbsm=float(dbsm(sig_ed.mean())),
            delta_mean_db=float(dbsm(sig_pt.mean()) - dbsm(sig_po.mean())),
            delta_median_db=float(dbsm(np.median(sig_pt)) - dbsm(np.median(sig_po))),
            delta_per_pose_db=dict(min=float(d.min()), p50=float(np.median(d)),
                                   max=float(d.max()), mean_abs=float(np.mean(np.abs(d)))),
            frac_poses_changed_gt1db=float(np.mean(np.abs(d) > 1.0)),
            edge_over_po_amp_db=float(20 * np.log10(max(np.abs(A).mean(), 1e-30)
                                                    / max(np.abs(E).mean(), 1e-30))),
            n_seg_used_per_pose=nseg_used / len(az),
            n_seg_total_per_pose=nseg_tot / len(az),
            n_drop_material_per_pose=ndrop_mat / len(az),
            n_drop_sin_a_per_pose=ndrop_sina / len(az),
            n_drop_edge_on_per_pose=ndrop_edgeon / len(az),
            n_regularized_per_pose=nreg / len(az),
            length_used_m_per_pose=Lused / len(az),
            norm_const_sensitivity_delta_mean_db=sens,
        )
        if keep_arrays:
            rec[pol]["_sigma_ptd_dbsm"] = [round(float(x), 4) for x in dbsm(sig_pt)]
    if keep_arrays:
        rec["_sigma_po_dbsm"] = [round(float(x), 4) for x in dbsm(sig_po)]
        rec["_az_deg"] = az.tolist()
    return rec


def lsq_slope(f_ghz, mu_db):
    """μ(f)=a f+b 최소자승. 반환 (a, b, R², a 의 표준오차)."""
    f = np.asarray(f_ghz, float); y = np.asarray(mu_db, float)
    n = len(f)
    a, b = np.polyfit(f, y, 1)
    yh = a * f + b
    ss = float(np.sum((y - yh) ** 2)); st = float(np.sum((y - y.mean()) ** 2))
    r2 = (1.0 - ss / st) if st > 0 else float("nan")
    se = (float(np.sqrt(ss / (n - 2) / np.sum((f - f.mean()) ** 2)))
          if n > 2 else float("nan"))
    return float(a), float(b), r2, se


def _fit_block(fg, mu_po, mu_ptd, mu_edge=None):
    a0, _, r0, s0 = lsq_slope(fg, mu_po)
    a1, _, r1, s1 = lsq_slope(fg, mu_ptd)
    blk = dict(n_freq=len(fg), f_ghz=[float(x) for x in fg],
               mu_po_dbsm=[float(x) for x in mu_po],
               mu_ptd_dbsm=[float(x) for x in mu_ptd],
               slope_po_db_per_ghz=a0, se_po=s0, r2_po=r0,
               slope_ptd_db_per_ghz=a1, se_ptd=s1, r2_ptd=r1,
               delta_slope_db_per_ghz=a1 - a0,
               gap_po_x=abs(a0) / DAS_SLOPE, gap_ptd_x=abs(a1) / DAS_SLOPE,
               gap_reduced=bool(abs(a1) < abs(a0)),
               gap_change_factor=(abs(a1) / abs(a0)) if abs(a0) > 1e-12 else float("nan"))
    if mu_edge is not None:
        ae, _, re, se = lsq_slope(fg, mu_edge)
        blk["mu_edge_only_dbsm"] = [float(x) for x in mu_edge]
        blk["slope_edge_only_db_per_ghz"] = ae
        blk["se_edge_only"] = se
        blk["r2_edge_only"] = re
    return blk


# --------------------------------------------------------------------------- #
def main():
    t_wall0 = time.perf_counter()
    out = {
        "meta": dict(
            script="benchmark/ptd_drone_effect.py",
            question="does the PTD edge term move our band slope toward the measured 0.210 dB/GHz",
            engine="PO point-cloud (rcs_po.mesh_to_points + PO surface integral), NO occlusion, CPU",
            engine_caveat=("production sigma uses the SBR engine (Mitsuba rays, occlusion, GPU). "
                           "ptd_edges.attach_to_sbr_field is untested (needs Mitsuba), so this run "
                           "is PO-only. The ptd=False slope here is the PO-engine slope, not the "
                           "production SBR slope; both are tabulated in production_sbr_control."),
            normalization_warning=("edge_field's overall constant is -1/2 and BOTH its magnitude "
                                   "and its sign are now verified against the analytic Ufimtsev "
                                   "edge wave on a flat plate (|ratio|-1 = 1.4e-14, |arg| <= "
                                   "5.8e-13 deg; defect D-1 fixed 2026-08-03). The x0.5/x2 "
                                   "sensitivity rows are kept as a material/geometry sensitivity "
                                   "display, not as a normalisation uncertainty."),
            open_defects=list(pe.OPEN_DEFECTS),
            missing_physics=list(pe.NOT_IMPLEMENTED),
            az_deg="0..357 step 3 (120 poses, = experiment_freespace_sigma.AZ_GRID)",
            el_cuts_deg=EL_CUTS,
            dense_f_ghz=[f / 1e9 for f in DENSE_F],
            spacing="lambda/20 (required whenever the fringe term is added coherently, D-8; the rcs_po engine default lambda/7 is too coarse for that)",
            pols=list(POLS), cpu_only=True,
            statistic="linear azimuth mean of sigma, then 10log10 (project convention)",
            das_slope_db_per_ghz=DAS_SLOPE, das_band_ghz=list(DAS_BAND_GHZ),
            our_band_ghz=list(OUR_BAND_GHZ),
            band_span_warning=("BAND SPANS ARE NOT THE SAME. Ours spans 1.8-5.8 GHz (4.0 GHz); "
                               "Das fits 1.8-18.2 GHz (16.4 GHz). A slope fitted on a 4 GHz window "
                               "is not the same estimator as one fitted on 16.4 GHz - our own "
                               "full-band fit (validate_measured_airframe 4_fullband_sweep) drops "
                               "from 1.657 dB/GHz on 1.8-5.21 GHz to 0.435 dB/GHz on 1.8-18.2 GHz "
                               "for the SAME simulated airframe. Every 'gap' factor below is "
                               "therefore a different-window comparison."),
        ),
        "drones": {},
    }

    for role, key in (("many_edges", DRONE_MANY), ("few_edges", DRONE_FEW)):
        spec = DRONES[key]
        mesh = build_drone(spec)
        gm = drone_gamma_map(spec)
        t0 = time.perf_counter()
        edges = pe.extract_edges(mesh, gamma=gm)
        t_ex = time.perf_counter() - t0

        V = np.asarray(mesh.v); F = np.asarray(mesh.f)
        v0, v1, v2 = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
        area = float(0.5 * np.linalg.norm(np.cross(v1 - v0, v2 - v0), axis=1).sum())
        D = float(np.linalg.norm(V.max(0) - V.min(0)))

        d = dict(drone=key, role=role, n_faces=int(len(F)), n_vertices=int(len(V)),
                 max_dim_m=D, surface_area_m2=area,
                 t_extract_edges_s=t_ex, edge_stats=dict(edges.stats),
                 L_metal_lambda_at_3p5GHz=float(edges.stats["length_metal_m"] / (C0 / 3.5e9)),
                 configs={})
        print(f"\n=== {role}: {key}  F={len(F)}  L_metal={edges.stats['length_metal_m']:.2f} m "
              f"({d['L_metal_lambda_at_3p5GHz']:.0f} lambda @3.5 GHz)  t_extract={t_ex:.2f} s",
              flush=True)

        for el in EL_CUTS:
            for fc in DENSE_F:
                r = run_config(mesh, gm, edges, fc, AZ, el, keep_arrays=(fc in NAMED_F))
                d["configs"][f"el{el:+.1f}_f{fc/1e9:.3f}"] = r
                tag = " *" if fc in NAMED_F else "  "
                print(f"  el={el:+5.1f} f={fc/1e9:5.3f}{tag} n_pts={r['n_points']:7d}  "
                      f"PO {r['sigma_po_mean_dbsm']:+7.2f}  "
                      f"+PTD(V) {r['V']['sigma_ptd_mean_dbsm']:+7.2f} "
                      f"(D {r['V']['delta_mean_db']:+6.2f})  "
                      f"edge-only(V) {r['V']['sigma_edge_only_mean_dbsm']:+7.2f}  "
                      f"t_su={r['t_surface_s']*1e3:7.1f} ms t_ed={r['V']['t_edge_s']*1e3:6.1f} ms",
                      flush=True)
        out["drones"][key] = d

    # ------------------------------------------------------------------ #
    #  기울기 — (A) 조밀 격자 본선  (B) 3점 적합(기존 헤드라인 규약)
    # ------------------------------------------------------------------ #
    slopes = {}
    for key, d in out["drones"].items():
        C = d["configs"]

        def mu(el, fs, what, pol=None):
            o = []
            for f in fs:
                r = C[f"el{el:+.1f}_f{f/1e9:.3f}"]
                if what == "po":
                    o.append(r["sigma_po_mean_dbsm"])
                elif what == "ptd":
                    o.append(r[pol]["sigma_ptd_mean_dbsm"])
                else:
                    o.append(r[pol]["sigma_edge_only_mean_dbsm"])
            return o

        def mu_pool(fs, what, pol=None):
            o = []
            for f in fs:
                lin = [10 ** (np.array(mu(el, [f], what, pol))[0] / 10) for el in EL_CUTS]
                o.append(float(dbsm(np.mean(lin))))
            return o

        rec = {"dense": {}, "three_band": {}}
        fg = [f / 1e9 for f in DENSE_F]
        for cut in [f"el{el:+.1f}" for el in EL_CUTS] + ["el_pooled"]:
            for pol in POLS:
                if cut == "el_pooled":
                    blk = _fit_block(fg, mu_pool(DENSE_F, "po"), mu_pool(DENSE_F, "ptd", pol),
                                     mu_pool(DENSE_F, "edge", pol))
                else:
                    el = float(cut[2:])
                    blk = _fit_block(fg, mu(el, DENSE_F, "po"), mu(el, DENSE_F, "ptd", pol),
                                     mu(el, DENSE_F, "edge", pol))
                rec["dense"].setdefault(cut, {})[pol] = blk
        for bs_name, bands in BAND_SETS.items():
            fs = list(bands.values())
            fg3 = [f / 1e9 for f in fs]
            for cut in [f"el{el:+.1f}" for el in EL_CUTS] + ["el_pooled"]:
                for pol in POLS:
                    if cut == "el_pooled":
                        blk = _fit_block(fg3, mu_pool(fs, "po"), mu_pool(fs, "ptd", pol),
                                         mu_pool(fs, "edge", pol))
                    else:
                        el = float(cut[2:])
                        blk = _fit_block(fg3, mu(el, fs, "po"), mu(el, fs, "ptd", pol),
                                         mu(el, fs, "edge", pol))
                    rec["three_band"].setdefault(bs_name, {}).setdefault(cut, {})[pol] = blk
        slopes[key] = rec
    out["slopes"] = slopes

    # ------------------------------------------------------------------ #
    #  생산 SBR 대조 — 레벨이 물리적으로 말이 되는지 (모서리항 타당성 검사)
    # ------------------------------------------------------------------ #
    ctrl = {"source": "outputs/report13_sigma_grid.json (production SBR, occlusion on, GPU)",
            "note": ("apples-to-apples on the azimuth-mean statistic and the same el cut; the "
                     "production run uses lambda/16 spacing, 3-carrier band averaging and the SBR "
                     "engine, so a 2-3 dB level offset from the PO engine is expected. What is "
                     "NOT expected is a 20 dB offset."), "rows": []}
    if os.path.exists(PROD_GRID):
        pg = json.load(open(PROD_GRID))["sigma"]["grid"]
        for key, d in out["drones"].items():
            if key not in pg:
                continue
            for b, v in pg[key].items():
                fc = v["fc_hz"]
                el = np.array(v["el_deg"]); S = 10 ** (np.array(v["sigma_dbsm"]) / 10)
                for e in EL_CUTS:
                    i = int(np.argmin(np.abs(el - e)))
                    cn = f"el{e:+.1f}_f{fc/1e9:.3f}"
                    if cn not in d["configs"]:
                        continue
                    r = d["configs"][cn]
                    prod = float(dbsm(S[i].mean()))
                    ctrl["rows"].append(dict(
                        drone=key, band=b, fc_ghz=fc / 1e9, el_deg=float(el[i]),
                        production_sbr_dbsm=prod,
                        our_po_dbsm=r["sigma_po_mean_dbsm"],
                        our_po_ptd_V_dbsm=r["V"]["sigma_ptd_mean_dbsm"],
                        po_minus_production_db=r["sigma_po_mean_dbsm"] - prod,
                        po_ptd_minus_production_db=r["V"]["sigma_ptd_mean_dbsm"] - prod))
        for tag, fld in (("po", "po_minus_production_db"), ("po_ptd", "po_ptd_minus_production_db")):
            for key in out["drones"]:
                v = [x[fld] for x in ctrl["rows"] if x["drone"] == key]
                if v:
                    ctrl.setdefault("summary", {}).setdefault(key, {})[tag] = dict(
                        min=float(min(v)), median=float(np.median(v)), max=float(max(v)))
    out["production_sbr_control"] = ctrl

    # ------------------------------------------------------------------ #
    #  비용
    # ------------------------------------------------------------------ #
    cost = {"note": (
        "t_surface = PO area integral only (point cloud excluded). t_pointcloud = building the PO "
        "point cloud, a one-off per (airframe, frequency) reused by every pose in the batch. "
        "t_edge = the entire edge line integral over the SAME 120 poses, one polarization. "
        "t_extract = one-off edge extraction per airframe, frequency-independent.")}
    rows = []
    for key, d in out["drones"].items():
        npos = len(AZ)
        for cname, r in d["configs"].items():
            for pol in POLS:
                inc_su = 100.0 * r[pol]["t_edge_s"] / r["t_surface_s"]
                inc_all = 100.0 * r[pol]["t_edge_s"] / (r["t_surface_s"] + r["t_pointcloud_s"])
                amort = 100.0 * (r[pol]["t_edge_s"] + d["t_extract_edges_s"]) / \
                    (r["t_surface_s"] + r["t_pointcloud_s"])
                rows.append(dict(
                    drone=key, config=cname, pol=pol, fc_ghz=r["fc_hz"] / 1e9,
                    n_points=r["n_points"],
                    t_surface_ms_per_pose=1e3 * r["t_surface_s"] / npos,
                    t_pointcloud_ms_per_pose=1e3 * r["t_pointcloud_s"] / npos,
                    t_edge_ms_per_pose=1e3 * r[pol]["t_edge_s"] / npos,
                    t_extract_ms_per_pose_amortized=1e3 * d["t_extract_edges_s"] / npos,
                    increase_pct_vs_surface_integral=inc_su,
                    increase_pct_vs_surface_plus_pointcloud=inc_all,
                    increase_pct_incl_edge_extraction=amort,
                    po_only_ms_per_pose=1e3 * (r["t_surface_s"] + r["t_pointcloud_s"]) / npos,
                    po_plus_ptd_ms_per_pose=1e3 * (r["t_surface_s"] + r["t_pointcloud_s"]
                                                   + r[pol]["t_edge_s"]
                                                   + d["t_extract_edges_s"]) / npos))
    cost["rows"] = rows
    for tag, fld in (("vs_surface_integral", "increase_pct_vs_surface_integral"),
                     ("vs_surface_plus_pointcloud", "increase_pct_vs_surface_plus_pointcloud"),
                     ("incl_edge_extraction_amortized_over_120_poses",
                      "increase_pct_incl_edge_extraction")):
        v = np.array([r[fld] for r in rows])
        cost.setdefault("summary_pct", {})[tag] = dict(
            min=float(v.min()), median=float(np.median(v)), max=float(v.max()))
        for key in out["drones"]:
            vv = np.array([r[fld] for r in rows if r["drone"] == key])
            cost["summary_pct"].setdefault("by_drone", {}).setdefault(key, {})[tag] = dict(
                min=float(vv.min()), median=float(np.median(vv)), max=float(vv.max()))
    cost["gao_2012"] = dict(
        printed_pct=[4.6, 17.2],
        source="Gao et al., PIER 122, 137-154 (2012), Table 1",
        caveat_from_our_doc=("docs/PTD_ILDC_FORMULATION.md §0: Gao's 4.6-17.2 % is WALL CLOCK, not "
                             "arithmetic. His TW-ILDC term alone costs 913.9 s vs 1311 s for the "
                             "whole SBR run (aircraft A) and 2428.2 s vs 2302.7 s (aircraft B) - "
                             "the edge term is comparable in arithmetic to the entire surface "
                             "solve, and the small percentage comes from overlapping the CPU edge "
                             "work with the GPU SBR work."),
        not_apples_to_apples=("Gao's targets are ~3920 lambda aircraft; ours are 5-37 lambda "
                              "drones. Edge cost scales with edge length / lambda and surface cost "
                              "with area / lambda^2, so the ratio MUST differ with electrical "
                              "size. This is a context number, not a benchmark match."))
    out["cost"] = cost

    # ------------------------------------------------------------------ #
    #  per-pose 절대 런타임
    # ------------------------------------------------------------------ #
    pp = np.array([r["po_plus_ptd_ms_per_pose"] for r in rows])
    po = np.array([r["po_only_ms_per_pose"] for r in rows])
    ed = np.array([r["t_edge_ms_per_pose"] for r in rows])
    out["per_pose_runtime_ms"] = dict(
        po_only=dict(min=float(po.min()), median=float(np.median(po)), max=float(po.max())),
        edge_term_only=dict(min=float(ed.min()), median=float(np.median(ed)), max=float(ed.max())),
        po_plus_ptd=dict(min=float(pp.min()), median=float(np.median(pp)), max=float(pp.max())),
        by_drone={k: dict(
            po_only_median=float(np.median([r["po_only_ms_per_pose"] for r in rows
                                            if r["drone"] == k])),
            edge_median=float(np.median([r["t_edge_ms_per_pose"] for r in rows
                                         if r["drone"] == k])),
            po_plus_ptd_median=float(np.median([r["po_plus_ptd_ms_per_pose"] for r in rows
                                                if r["drone"] == k])))
            for k in out["drones"]},
        hardware="host CPU, single-thread numpy (GPU untouched: GPU2 was busy with rcs_anchor.py)",
        baselines=dict(
            stock_sionna_published_s_per_pose=[0.0592, 0.204, 0.286],
            stock_sionna_published_note=("A5000 0.0592 s; RTX 4090 0.204 s and 0.286 s "
                                         "(outputs/runtime_benchmark.json published_baselines)"),
            stock_sionna_same_card_ms=[72.8, 128.0],
            our_production_sbr_ms=dict(min=9.2, median=38.1, max=356.2,
                                       note="GPU SBR, outputs/runtime_benchmark.json"),
            ziganshin_per_angular_point_ms=[1.94, 52.8]),
        caveat=("our PO here runs on the CPU while production PO runs on the GPU, so the PO column "
                "is NOT the production number. The number that transfers is the EDGE column: that "
                "is the incremental cost PTD would add to a pose."))

    out["wall_s"] = time.perf_counter() - t_wall0
    dst = os.path.join(ROOT, "outputs", "ptd_drone_effect.json")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "w") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
    print(f"\n저장: {dst}   ({out['wall_s']:.1f} s)")
    return out


if __name__ == "__main__":
    main()
