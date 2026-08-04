# -*- coding: utf-8 -*-
"""
verify_ptd_regression.py — PTD 모듈(src/ptd_edges.py) 도입 **회귀 검증 + 매끄러운 물체 온전성**
================================================================================================
세 부분으로 나뉜다. 파트는 환경변수 `PTD_REG_PART` 로 고른다(gpu / cpu / merge).

  [R] 회귀 (ptd=False)  — 기존 검증 3종이 **한 자리도 안 변했음**을 증명한다.
        R0 출처: 레거시 커널 파일의 sha256·mtime + 'ptd' 문자열 부재 (순수 추가분 증명)
        R1 항등: rcs_po_ptd(ptd=False) 가 rcs_po.rcs_from_points 와 **비트 동일**
        R2 PEC 구 (Yuan 교정체 r=17.8 cm, r=25 cm) 3대역 재실행 vs outputs/rcs_anchor.json
        R3 kr 스윕 48방향(21 kr × div{12,16}) 재실행 vs outputs/sbr_kr_sweep.json
        R4 이면반사체 4 크기(1/2-bounce) 재실행 vs outputs/sbr_defect_fixes.json
      ⚠ R2~R4 는 GPU(Mitsuba)를 쓴다. R0·R1 은 CPU.

  [B] 매끄러운 구에 PTD 켜기 — 구는 진짜 모서리가 없다 → 잡히는 것은 **삼각메쉬의 인공 모서리**
      뿐이다. 메쉬 해상도를 올리며 그 기여가 **0 으로 수렴하는지** 본다.
      ⭐ 기본 문턱 sharp_deg=5° 는 해상도가 올라가면 이음매를 **전부 버려서** 기여를 0 으로
        만든다(적도 이음매 이면각 편차 ≈ 360/seg 도). 그건 수렴이 아니라 문턱 효과다.
        그래서 **sharp_deg=0(전부 유지)** 로도 같이 재고, 그 쪽을 정직한 과녁으로 삼는다.

  [C] 이면반사체에 PTD 켜기 — 진짜 모서리가 있는 표적. 기여가 물리적으로 말이 되는가.
        C1 모서리 목록이 형상과 맞는가 (N=α/π, 길이, 경계/쐐기 구분)
        C2 개각(opening angle) ψ: 90°→180° 로 펴면 모서리 기여가 **스스로 0 으로 가는가**
        C3 크기 사다리 a: |A_edge|/|A_PO| 가 ∝ λ/a 로 줄어드는가(선적분 vs 면적분)
        C4 고도각 스윕: PO 널에서만 모서리항이 지배하는가
        C5 해석해 8πa²b²/λ² 대비 — PTD 는 **빠진 2-bounce 를 대신하지 못한다**(그래야 정상)

실행
  cd /home/yunjung/workspace/sionna2
  PTD_REG_PART=cpu PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/verify_ptd_regression.py
  PTD_REG_PART=gpu SIONNA2_GPU=0 SIONNA2_GPU_MEM=3000 PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/verify_ptd_regression.py
  PTD_REG_PART=merge ~/.venvs/py312/bin/python benchmark/verify_ptd_regression.py
산출: outputs/ptd_regression.json   (파트별 중간산출은 outputs/_ptd_reg_{gpu,cpu}.json)
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (os.path.join(_ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

C0 = 299792458.0
FC = 3.5e9
LAM = C0 / FC
#  ptd=True 경로 전용 PO 간격 — λ/20 (D-8). ptd=False 회귀(A 절)는 옛 간격 그대로 둔다.
SP_PTD = LAM / 20
OUT_DIR = os.path.join(_ROOT, "outputs")
OUT_GPU = os.path.join(OUT_DIR, "_ptd_reg_gpu.json")
OUT_CPU = os.path.join(OUT_DIR, "_ptd_reg_cpu.json")
OUT = os.path.join(OUT_DIR, "ptd_regression.json")

# 기준(baseline) — PTD 도입 **이전**에 생성된 산출물.
BASE_ANCHOR = os.path.join(OUT_DIR, "rcs_anchor.json")
BASE_KR = os.path.join(OUT_DIR, "sbr_kr_sweep.json")
BASE_DEF = os.path.join(OUT_DIR, "sbr_defect_fixes.json")
#  rcs_anchor.py 가 **지금 GPU2 에서 재생성 중**이라 파일이 덮여쓰일 수 있다 → 라운드 시작 시
#  떠 둔 스냅샷을 우선 쓴다(경로는 환경변수로 주입).
BASE_SNAP = os.environ.get("PTD_REG_BASELINE_DIR", "")


def _baseline(path):
    if BASE_SNAP:
        cand = os.path.join(BASE_SNAP, os.path.basename(path))
        if os.path.exists(cand):
            return json.load(open(cand, encoding="utf-8")), cand
    return json.load(open(path, encoding="utf-8")), path


def _sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:16]


def _db(x):
    return float(10.0 * np.log10(max(float(x), 1e-300)))


# =========================================================================== #
#  R0 — 출처: PTD 는 순수 추가분인가
# =========================================================================== #
def r0_provenance():
    files = {
        "src/rcs_po.py": "PO 면적분 커널 (레거시)",
        "src/rcs_sbr.py": "SBR+PO 커널 (레거시, 생산 경로)",
        "src/geom.py": "메쉬 (레거시)",
        "benchmark/mie_pec_sphere.py": "구 기준해 (레거시)",
        "src/ptd_edges.py": "PTD 모서리 (신규)",
    }
    rows = {}
    for rel, role in files.items():
        p = os.path.join(_ROOT, rel)
        src = open(p, encoding="utf-8").read()
        n_ptd = src.lower().count("ptd")
        rows[rel] = dict(role=role, sha256_16=_sha(p),
                         mtime=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(p))),
                         bytes=len(src.encode()), n_ptd_mentions=int(n_ptd))
    legacy = [k for k in files if k != "src/ptd_edges.py"]
    return dict(files=rows,
                legacy_files_mentioning_ptd=[k for k in legacy if rows[k]["n_ptd_mentions"] > 0],
                pure_addition=bool(all(rows[k]["n_ptd_mentions"] == 0 for k in legacy)),
                note=("레거시 커널 어디에도 'ptd' 문자열이 없다 → PTD 는 호출되지 않는 순수 추가분이다. "
                      "그래도 아래 R1~R4 로 숫자를 직접 재확인한다(문자열 부재는 증거이지 증명이 아니다)."))


# =========================================================================== #
#  R1 — ptd=False 항등 (비트 단위)
# =========================================================================== #
def r1_identity():
    import ptd_edges as pe
    from rcs_po import mesh_to_points, rcs_from_points, _plate_mesh
    from geom import uv_sphere
    from rcs_sbr import dihedral_mesh

    def bits(a):
        return np.ascontiguousarray(np.asarray(a, np.float64)).tobytes()

    cases = [
        ("yuan_sphere_r0.178", uv_sphere(0.178, seg=180, rings=90, group="metal"), LAM / 8, 0.0),
        ("kr_sweep_sphere_kr30", uv_sphere(30.0 * LAM / (2 * np.pi), seg=240, rings=120,
                                           group="metal"), LAM / 16, 20.0),
        ("dihedral_a0.30", dihedral_mesh(0.30), LAM / 12, 45.0),
        ("plate_0.30", _plate_mesh(0.30), LAM / 10, 90.0),
    ]
    out = {}
    az = np.arange(0.0, 360.0, 15.0)
    for name, mesh, sp, el in cases:
        P, N, dA = mesh_to_points(mesh, sp)
        ref = rcs_from_points(P, N, dA, FC, az, el)
        sig, meta = pe.rcs_po_ptd(mesh, FC, az, el_deg=el, spacing=sp, ptd=False)
        E = pe._po_field_dirs(P, N, dA, FC, az, el)
        sig2 = (4 * np.pi / LAM ** 2) * np.abs(E) ** 2
        out[name] = dict(
            n_points=int(len(dA)), n_tri=int(len(mesh.f)),
            wrapper_bit_identical=bool(bits(ref) == bits(sig)),
            replicated_kernel_bit_identical=bool(bits(ref) == bits(sig2)),
            max_abs_diff_wrapper=float(np.max(np.abs(ref - sig))),
            max_abs_diff_kernel=float(np.max(np.abs(ref - sig2))),
            sigma_mean_dbsm=_db(float(np.mean(ref))))
    out["all_bit_identical"] = bool(all(v["wrapper_bit_identical"] and v["replicated_kernel_bit_identical"]
                                        for v in out.values() if isinstance(v, dict)))
    return out


# =========================================================================== #
#  R2 — Yuan 교정구 재실행
# =========================================================================== #
def r2_sphere(tol_db=1e-9):
    from rcs_anchor import sphere_calibration
    base, base_path = _baseline(BASE_ANCHOR)
    bands = [("LTE 1.843 GHz", 1.843e9), ("5G 3.5 GHz", 3.5e9), ("WiFi 5.21 GHz", 5.21e9)]
    rows, worst = [], 0.0
    for label, fc in bands:
        got = sphere_calibration(fc)
        b = base["sphere_calibration"][label]
        for gs, bs in zip(got["spheres"], b["spheres"]):
            d = gs["sbr_dbsm"] - bs["sbr_dbsm"]
            worst = max(worst, abs(d))
            rows.append(dict(band=label, radius_m=gs["radius_m"], ka=gs["ka"],
                             baseline_sbr_dbsm=bs["sbr_dbsm"], rerun_sbr_dbsm=gs["sbr_dbsm"],
                             delta_db=float(d),
                             baseline_dev_vs_mie_db=bs["dev_db_vs_mie"],
                             rerun_dev_vs_mie_db=gs["dev_db_vs_mie"]))
            print(f"  [R2] {label:16s} r={gs['radius_m']:.3f} m  기준 {bs['sbr_dbsm']:+.6f} → "
                  f"재실행 {gs['sbr_dbsm']:+.6f} dBsm   Δ={d:+.3e} dB")
    return dict(baseline_path=os.path.relpath(base_path, _ROOT), rows=rows,
                max_abs_delta_db=float(worst), tol_db=tol_db,
                unchanged=bool(worst <= tol_db))


# =========================================================================== #
#  R3 — kr 스윕 48방향 재실행
# =========================================================================== #
def r3_kr_sweep(tol_db=1e-9):
    import verify_sbr_kr_sweep as ks
    base, base_path = _baseline(BASE_KR)
    assert ks.AZ_N * len(ks.EL_SET) == 48, f"입사방향 {ks.AZ_N*len(ks.EL_SET)} ≠ 48"
    rows = ks.sweep()
    bmap = {(r["kr"], r["div"]): r for r in base["rows"] if "skipped" not in r}
    cmp_rows, worst = [], 0.0
    for r in rows:
        if "skipped" in r:
            continue
        b = bmap.get((r["kr"], r["div"]))
        if b is None:
            continue
        d = _db(r["sigma_sbr_m2"]) - _db(b["sigma_sbr_m2"])
        worst = max(worst, abs(d))
        cmp_rows.append(dict(kr=r["kr"], div=r["div"], n_tri=r["n_tri"],
                             baseline_dbsm=_db(b["sigma_sbr_m2"]), rerun_dbsm=_db(r["sigma_sbr_m2"]),
                             delta_db=float(d),
                             baseline_rel_sd=b["incidence_rel_sd"], rerun_rel_sd=r["incidence_rel_sd"]))
    inv = ks.scale_invariance()
    return dict(baseline_path=os.path.relpath(base_path, _ROOT),
                n_incidence=int(ks.AZ_N * len(ks.EL_SET)), el_set=list(ks.EL_SET), az_n=int(ks.AZ_N),
                n_compared=len(cmp_rows), rows=cmp_rows,
                max_abs_delta_db=float(worst), tol_db=tol_db, unchanged=bool(worst <= tol_db),
                scale_invariance_rerun=inv,
                scale_invariance_baseline_dev_db=base["scale_invariance"]["dev_db"])


# =========================================================================== #
#  R4 — 이면반사체 재실행
# =========================================================================== #
def r4_dihedral(tol_db=1e-9):
    from rcs_sbr import (dihedral_mesh, dihedral_exact_sigma, rcs_sbr,
                         DEFAULT_DIV, _PEC_GROUP_MAT)
    base, base_path = _baseline(BASE_DEF)
    bmap = {r["a_m"]: r for r in base["d3_multibounce_phase"]["rows"]}
    rows, worst = [], 0.0
    for a in (0.15, 0.20, 0.30, 0.40):
        dm = dihedral_mesh(a)
        ex = dihedral_exact_sigma(a, fc=FC)
        s1 = float(rcs_sbr(dm, _PEC_GROUP_MAT, FC, az_deg=0.0, el_deg=45.0,
                           spacing=LAM / DEFAULT_DIV, max_bounce=1))
        s2 = float(rcs_sbr(dm, _PEC_GROUP_MAT, FC, az_deg=0.0, el_deg=45.0,
                           spacing=LAM / DEFAULT_DIV, max_bounce=2))
        b = bmap[a]
        d1 = _db(max(s1, 1e-30)) - b["sbr_1bounce_dbsm"]
        d2 = _db(s2) - b["sbr_2bounce_dbsm"]
        worst = max(worst, abs(d1), abs(d2))
        rows.append(dict(a_m=a, exact_dbsm=_db(ex),
                         baseline_b1_dbsm=b["sbr_1bounce_dbsm"], rerun_b1_dbsm=_db(max(s1, 1e-30)),
                         delta_b1_db=float(d1),
                         baseline_b2_dbsm=b["sbr_2bounce_dbsm"], rerun_b2_dbsm=_db(s2),
                         delta_b2_db=float(d2),
                         rerun_err_2bounce_db=float(_db(s2) - _db(ex)),
                         baseline_err_2bounce_db=b["err_2bounce_db"]))
        print(f"  [R4] a={a:.2f} m  1-bnc Δ={d1:+.3e}  2-bnc Δ={d2:+.3e} dB")
    return dict(baseline_path=os.path.relpath(base_path, _ROOT), rows=rows,
                max_abs_delta_db=float(worst), tol_db=tol_db, unchanged=bool(worst <= tol_db))


# =========================================================================== #
#  B — 매끄러운 구: 인공 모서리 기여의 해상도 수렴
# =========================================================================== #
SEG_LADDER = (24, 32, 48, 64, 96, 128, 192, 256, 384)
SPHERE_R = 0.178                     # Yuan 교정체와 같은 반경 → kr=13.06 @3.5 GHz
AZ_B = np.arange(0.0, 360.0, 30.0)   # 12 방위
SP_B = LAM / 20                      # PO 점구름 간격은 **메쉬와 무관하게 고정**.
#  λ/20 인 이유: ptd=True 경로는 PO 중점구적 오차가 프린지 항과 섞이지 않아야 한다(D-8).


def b_sphere_convergence(radius=SPHERE_R, seg_ladder=SEG_LADDER):
    import ptd_edges as pe
    from geom import uv_sphere
    from rcs_po import dbsm

    SPHERE_R = float(radius)
    SEG_LADDER = tuple(seg_ladder)
    kr = 2 * np.pi * SPHERE_R / LAM
    res = dict(r_m=SPHERE_R, fc_hz=FC, kr=float(kr), az_deg=AZ_B.tolist(), el_deg=0.0,
               po_spacing_m=float(SP_B), seg_ladder=list(SEG_LADDER),
               production_facet_rule="면 변 ≤ λ/8  ⇒  seg ≥ 8·kr = %.0f" % (8 * kr))
    by_res = {}
    for seg in SEG_LADDER:
        rings = max(4, seg // 2)
        mesh = uv_sphere(SPHERE_R, seg=seg, rings=rings, group="metal")
        facet_m = 2 * np.pi * SPHERE_R / seg              # 적도 이음매 변 길이
        s_po, m0 = pe.rcs_po_ptd(mesh, FC, AZ_B, spacing=SP_B, ptd=False)
        row = dict(seg=int(seg), rings=int(rings), n_tri=int(len(mesh.f)),
                   n_po_points=int(m0["n_points"]),
                   facet_m=float(facet_m), facets_per_lambda=float(LAM / facet_m),
                   seam_dihedral_dev_deg=float(360.0 / seg),   # 적도에서의 |α−180°| 근사
                   sigma_po_dbsm_mean=float(dbsm(np.mean(s_po))),
                   t_surface_s=float(m0["t_surface_s"]))
        for sd in (5.0, 0.0):
            t0 = time.perf_counter()
            edges = pe.extract_edges(mesh, sharp_deg=sd)
            t_ex = time.perf_counter() - t0
            sub = dict(n_edges_total=edges.stats["n_edges_total"],
                       n_kept=edges.stats["n_kept"],
                       n_dropped_flat=edges.stats["n_dropped_flat"],
                       alpha_deg_min=edges.stats["alpha_deg_min"],
                       alpha_deg_max=edges.stats["alpha_deg_max"],
                       t_extract_s=float(t_ex))
            worst_d, worst_r = 0.0, -300.0
            for pol in ("V", "H"):
                s, m = pe.rcs_po_ptd(mesh, FC, AZ_B, spacing=SP_B, ptd=True, pol=pol, edges=edges)
                d = dbsm(s) - dbsm(s_po)
                ratio = 20 * np.log10(np.maximum(np.array(m["A_edge_abs"]) /
                                                 np.array(m["A_po_abs"]), 1e-30))
                sub[pol] = dict(max_abs_delta_db=float(np.max(np.abs(d))),
                                mean_abs_delta_db=float(np.mean(np.abs(d))),
                                max_edge_over_po_db=float(np.max(ratio)),
                                median_edge_over_po_db=float(np.median(ratio)),
                                max_A_edge_abs=float(np.max(m["A_edge_abs"])),
                                mean_A_edge_abs=float(np.mean(m["A_edge_abs"])),
                                mean_A_po_abs=float(np.mean(m["A_po_abs"])),
                                n_seg_used=int(m["edge"]["n_seg_used"]),
                                n_drop_sin_a=int(m["edge"]["n_drop_sin_a"]),
                                n_regularized=int(m["edge"]["n_regularized"]),
                                t_edge_s=float(m["t_edge_s"]))
                worst_d = max(worst_d, sub[pol]["max_abs_delta_db"])
                worst_r = max(worst_r, sub[pol]["max_edge_over_po_db"])
            sub["max_abs_delta_db"] = worst_d
            sub["max_edge_over_po_db"] = worst_r
            row[f"sharp_deg={sd:g}"] = sub
        by_res[f"seg{seg}"] = row
        print(f"  [B] seg={seg:4d} ({row['facets_per_lambda']:5.2f} facet/λ, "
              f"이음매 편차 {row['seam_dihedral_dev_deg']:5.2f}°)  "
              f"sharp5: kept={row['sharp_deg=5']['n_kept']:6d} maxΔ={row['sharp_deg=5']['max_abs_delta_db']:.4f} dB | "
              f"sharp0: kept={row['sharp_deg=0']['n_kept']:6d} maxΔ={row['sharp_deg=0']['max_abs_delta_db']:.4f} dB "
              f"(A_e/A_PO {row['sharp_deg=0']['max_edge_over_po_db']:+.2f} dB)")
    res["by_resolution"] = by_res

    # 수렴 판정 — 정직한 축은 sharp_deg=0
    fp = np.array([by_res[f"seg{s}"]["facets_per_lambda"] for s in SEG_LADDER])
    for sd in ("5", "0"):
        art = np.array([by_res[f"seg{s}"][f"sharp_deg={sd}"]["max_abs_delta_db"] for s in SEG_LADDER])
        rat = np.array([by_res[f"seg{s}"][f"sharp_deg={sd}"]["max_edge_over_po_db"] for s in SEG_LADDER])
        pos = art > 0
        slope = None
        if pos.sum() >= 3:
            slope = float(np.polyfit(np.log10(fp[pos]), np.log10(art[pos]), 1)[0])
        res[f"convergence_sharp_deg={sd}"] = dict(
            artifact_db=art.tolist(), edge_over_po_db=rat.tolist(),
            facets_per_lambda=fp.tolist(),
            monotone_decreasing=bool(np.all(np.diff(art) <= 1e-12)),
            first=float(art[0]), last=float(art[-1]),
            ratio_first_over_last=float(art[0] / art[-1]) if art[-1] > 0 else None,
            loglog_slope_vs_facets_per_lambda=slope,
            at_production_density=float(
                art[int(np.argmin(np.abs(fp - 8.0)))]),
        )
    return res


# =========================================================================== #
#  C — 이면반사체(진짜 모서리)에 PTD
# =========================================================================== #
def _bent_sheet(a, b, psi_deg, group="metal"):
    """개각 ψ 의 굽은 판 — ψ=90° 가 직각 이면반사체, ψ=180° 가 평판.
    판① z=0, x∈[0,a]; 판② 는 y축 둘레로 ψ 만큼 꺾인다. 둘 다 y∈[0,b]."""
    from geom import Mesh, quad
    m = Mesh(group)
    m.merge(quad((0, 0, 0), (a, 0, 0), (a, b, 0), (0, b, 0), group=group))
    ps = np.radians(psi_deg)
    q = (a * np.cos(ps), 0.0, a * np.sin(ps))
    m.merge(quad((0, 0, 0), (0, b, 0), (q[0], b, q[2]), (q[0], 0, q[2]), group=group))
    return m


def c_dihedral():
    import ptd_edges as pe
    from rcs_po import dbsm
    from rcs_sbr import dihedral_mesh, dihedral_exact_sigma

    out = {"fc_hz": FC, "lambda_m": LAM}

    # ── C1 모서리 목록 ────────────────────────────────────────────────────── #
    a = 0.30
    dm = dihedral_mesh(a)
    es = pe.extract_edges(dm)
    per = []
    for i in range(len(es)):
        per.append(dict(P0=[round(float(v), 6) for v in es.P0[i]],
                        P1=[round(float(v), 6) for v in es.P1[i]],
                        L_m=float(es.L[i]), N=float(es.Nw[i]),
                        alpha_deg=float(180.0 * es.Nw[i]),
                        boundary=bool(es.boundary[i])))
    out["c1_edge_inventory"] = dict(
        a_m=a, n_tri=int(len(dm.f)), stats=dict(es.stats), edges=per,
        note=("⚠ 이 메쉬는 **두께 0** 판 두 장이다. 두께 0 굽은 판의 이음선은 Ufimtsev 쐐기가 "
              "아니라 '두 반평면의 접합'이다 — 코드의 볼록/오목 판정이 그것을 α=90°(N=0.5) "
              "안쪽 공기쐐기로 해석한다. 실물(두께 t>0) 반사체라면 안쪽 90° 와 바깥쪽 270° "
              "두 쐐기가 **둘 다** 존재한다. 현재 메쉬에는 바깥 270° 쐐기가 아예 없다."))

    # ── C2 개각 ψ: 90°→180° 에서 모서리 기여가 스스로 죽는가 ─────────────── #
    psis = (90.0, 110.0, 130.0, 150.0, 165.0, 174.0, 176.0, 178.0, 179.0, 180.0)
    az = np.array([0.0])
    rows = []
    for ps in psis:
        mesh = _bent_sheet(a, a, ps)
        el = ps / 2.0                       # 이등분선 입사
        s_po, _ = pe.rcs_po_ptd(mesh, FC, az, el_deg=el, spacing=SP_PTD, ptd=False)
        #  keep_reentrant=True: 오목 쐐기(N<1)는 기본적으로 버려지지만(D-3) 여기서는 그 가지
        #  자체를 진단하는 절이므로 명시적으로 되살린다. 생산 경로가 아니다.
        edges = pe.extract_edges(mesh, sharp_deg=0.0, keep_reentrant=True)     # 문턱 없이
        # 이음선만 남긴다(경계 모서리 제외) → 개각의 효과를 순수하게 본다
        sel = ~edges.boundary
        seam = pe.EdgeSet(P0=edges.P0[sel], P1=edges.P1[sel], T=edges.T[sel], X=edges.X[sel],
                          Y=edges.Y[sel], L=edges.L[sel], Nw=edges.Nw[sel],
                          boundary=edges.boundary[sel], gmin=edges.gmin[sel],
                          n1=edges.n1[sel], n2=edges.n2[sel])
        seam.stats = dict(edges.stats)
        r = dict(psi_deg=ps, el_deg=el, n_seam_edges=int(sel.sum()),
                 seam_N=[float(v) for v in np.unique(np.round(seam.Nw, 6))],
                 sigma_po_dbsm=float(dbsm(s_po[0])))
        for pol in ("V", "H"):
            s, m = pe.rcs_po_ptd(mesh, FC, az, el_deg=el, spacing=SP_PTD, ptd=True,
                                 pol=pol, edges=seam)
            r[pol] = dict(sigma_ptd_dbsm=float(dbsm(s[0])),
                          delta_db=float(dbsm(s[0]) - dbsm(s_po[0])),
                          edge_over_po_db=float(20 * np.log10(
                              max(m["A_edge_abs"][0] / max(m["A_po_abs"][0], 1e-300), 1e-30))),
                          A_edge_abs=float(m["A_edge_abs"][0]))
        rows.append(r)
        print(f"  [C2] ψ={ps:6.1f}°  이음선 N={r['seam_N']}  "
              f"|A_e/A_PO| V={r['V']['edge_over_po_db']:+8.2f} dB  Δσ={r['V']['delta_db']:+7.3f} dB")
    a90 = max(rows[0]["V"]["A_edge_abs"], rows[0]["H"]["A_edge_abs"])
    a180 = max(rows[-1]["V"]["A_edge_abs"], rows[-1]["H"]["A_edge_abs"])
    out["c2_opening_angle"] = dict(
        rows=rows, a_m=a,
        seam_amp_at_90=float(a90), seam_amp_at_180=float(a180),
        db_180_minus_90=float(20 * np.log10(max(a180, 1e-300) / max(a90, 1e-300))),
        vanishes_at_flat=bool(a180 / max(a90, 1e-300) < 1e-6),
        monotone_towards_flat=bool(all(
            max(rows[i]["V"]["A_edge_abs"], rows[i]["H"]["A_edge_abs"]) >=
            max(rows[i + 1]["V"]["A_edge_abs"], rows[i + 1]["H"]["A_edge_abs"]) - 1e-18
            for i in range(len(rows) - 4, len(rows) - 1))))

    # ── C3 크기 사다리: |A_e/A_PO| ∝ λ/a 인가 ────────────────────────────── #
    #    PO 널을 피하려고 고도각 창(35~55°) 중앙값으로 잰다.
    el_win = np.arange(35.0, 55.1, 2.5)
    rows = []
    for aa in (0.10, 0.15, 0.20, 0.30, 0.40, 0.60, 0.80):
        mesh = dihedral_mesh(aa)
        edges = pe.extract_edges(mesh, keep_reentrant=True)   # 이면각 진단 전용(D-3)
        rr = []
        for el in el_win:
            _, m = pe.rcs_po_ptd(mesh, FC, [0.0], el_deg=float(el), spacing=SP_PTD,
                                 ptd=True, pol="V", edges=edges)
            rr.append(20 * np.log10(max(m["A_edge_abs"][0] / max(m["A_po_abs"][0], 1e-300), 1e-30)))
        rows.append(dict(a_m=aa, a_over_lambda=float(aa / LAM),
                         median_edge_over_po_db=float(np.median(rr)),
                         min_db=float(np.min(rr)), max_db=float(np.max(rr))))
        print(f"  [C3] a={aa:.2f} m ({aa/LAM:4.1f}λ)  |A_e/A_PO| 중앙값 "
              f"{rows[-1]['median_edge_over_po_db']:+7.2f} dB")
    x = np.log10([r["a_over_lambda"] for r in rows])
    y = np.array([r["median_edge_over_po_db"] for r in rows]) / 20.0   # 진폭 log10
    sl = float(np.polyfit(x, y, 1)[0])
    out["c3_size_scaling"] = dict(rows=rows, loglog_slope_amp_vs_a=sl,
                                  expected_slope=-1.0, slope_err=float(sl + 1.0),
                                  note="선적분(∝a)/면적분(∝a²) → 진폭비 ∝ 1/a, log-log 기울기 −1 이 기대값")

    # ── C4 고도각 스윕 ───────────────────────────────────────────────────── #
    a = 0.30
    mesh = dihedral_mesh(a)
    edges = pe.extract_edges(mesh, keep_reentrant=True)       # 이면각 진단 전용(D-3)
    els = np.arange(2.0, 89.1, 2.0)
    s_po = np.array([pe.rcs_po_ptd(mesh, FC, [0.0], el_deg=float(e), spacing=SP_PTD,
                                   ptd=False)[0][0] for e in els])
    sweep = dict(a_m=a, el_deg=els.tolist(), sigma_po_dbsm=dbsm(s_po).tolist())
    for pol in ("V", "H"):
        sg, ratio = [], []
        for e in els:
            s, m = pe.rcs_po_ptd(mesh, FC, [0.0], el_deg=float(e), spacing=SP_PTD,
                                 ptd=True, pol=pol, edges=edges)
            sg.append(s[0])
            ratio.append(20 * np.log10(max(m["A_edge_abs"][0] / max(m["A_po_abs"][0], 1e-300), 1e-30)))
        sg = np.array(sg); ratio = np.array(ratio)
        d = dbsm(sg) - dbsm(s_po)
        sweep[pol] = dict(sigma_ptd_dbsm=dbsm(sg).tolist(), delta_db=d.tolist(),
                          edge_over_po_db=ratio.tolist(),
                          max_abs_delta_db=float(np.max(np.abs(d))),
                          median_abs_delta_db=float(np.median(np.abs(d))),
                          delta_at_bisector_db=float(d[np.argmin(np.abs(els - 45.0))]),
                          edge_dominates_frac=float(np.mean(ratio > 0.0)))
    out["c4_elevation_sweep"] = sweep

    # ── C5 해석해 대비 ───────────────────────────────────────────────────── #
    rows = []
    for aa in (0.15, 0.20, 0.30, 0.40):
        mesh = dihedral_mesh(aa)
        edges = pe.extract_edges(mesh, keep_reentrant=True)   # 이면각 진단 전용(D-3)
        ex = dihedral_exact_sigma(aa, fc=FC)
        s0, _ = pe.rcs_po_ptd(mesh, FC, [0.0], el_deg=45.0, spacing=SP_PTD, ptd=False)
        r = dict(a_m=aa, exact_2bounce_dbsm=_db(ex), po_only_dbsm=float(dbsm(s0[0])))
        for pol in ("V", "H"):
            s, m = pe.rcs_po_ptd(mesh, FC, [0.0], el_deg=45.0, spacing=SP_PTD, ptd=True,
                                 pol=pol, edges=edges)
            r[pol] = dict(po_plus_ptd_dbsm=float(dbsm(s[0])),
                          gap_to_exact_db=float(dbsm(s[0]) - _db(ex)),
                          delta_vs_po_db=float(dbsm(s[0]) - dbsm(s0[0])))
        rows.append(r)
    out["c5_vs_exact"] = dict(
        rows=rows,
        note=("PO(+PTD) 는 1-bounce 다 — 이면반사체의 해석해 8πa²b²/λ² 는 **2회 반사**에서 나온다. "
              "따라서 PO+PTD 가 해석해에 가까워지면 오히려 이상하다. 여기서 볼 것은 '얼마나 "
              "멀리 있는가'(=PTD 가 빠진 다중반사를 대신하지 않는다)뿐이다."))
    return out


# =========================================================================== #
def main():
    part = os.environ.get("PTD_REG_PART", "cpu").lower()
    t0 = time.time()
    os.makedirs(OUT_DIR, exist_ok=True)

    if part == "gpu":
        from gpu import pick
        pick()
        out = dict(part="gpu", generated=time.strftime("%Y-%m-%d %H:%M:%S"),
                   gpu=os.environ.get("CUDA_VISIBLE_DEVICES"))
        print("== R2 PEC 구 (Yuan 교정체 r=17.8 cm) 재실행 ==")
        out["R2_sphere_yuan"] = r2_sphere()
        print("\n== R4 이면반사체 재실행 ==")
        out["R4_dihedral"] = r4_dihedral()
        print("\n== R3 kr 스윕(48방향) 재실행 ==")
        out["R3_kr_sweep"] = r3_kr_sweep()
        out["wall_s"] = round(time.time() - t0, 1)
        json.dump(out, open(OUT_GPU, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        print(f"\n저장 → {OUT_GPU}  ({out['wall_s']:.0f}s)")
        return 0

    if part == "cpu":
        out = dict(part="cpu", generated=time.strftime("%Y-%m-%d %H:%M:%S"))
        print("== R0 출처 ==")
        out["R0_provenance"] = r0_provenance()
        print(json.dumps(out["R0_provenance"]["files"], indent=1, ensure_ascii=False))
        print("\n== R1 ptd=False 비트 항등 ==")
        out["R1_identity"] = r1_identity()
        print(json.dumps({k: v for k, v in out["R1_identity"].items()}, indent=1, ensure_ascii=False))
        print("\n== B 매끄러운 구 해상도 수렴 (r=0.178 m, kr=13.06) ==")
        out["B_sphere_artifact"] = b_sphere_convergence()
        print("\n== B2 두 번째 반경 교차확인 (r=0.5 m, kr=36.68) ==")
        out["B2_sphere_artifact_r0p5"] = b_sphere_convergence(radius=0.5,
                                                              seg_ladder=(60, 120, 240, 360))
        print("\n== C 이면반사체 PTD ==")
        out["C_dihedral_ptd"] = c_dihedral()
        out["wall_s"] = round(time.time() - t0, 1)
        json.dump(out, open(OUT_CPU, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        print(f"\n저장 → {OUT_CPU}  ({out['wall_s']:.0f}s)")
        return 0

    # merge
    cpu = json.load(open(OUT_CPU, encoding="utf-8"))
    gpu = json.load(open(OUT_GPU, encoding="utf-8")) if os.path.exists(OUT_GPU) else {}
    res = dict(generated=time.strftime("%Y-%m-%d %H:%M:%S"),
               generated_by="benchmark/verify_ptd_regression.py",
               fc_hz=FC, lambda_m=LAM)
    res.update({k: v for k, v in cpu.items() if k.startswith(("R", "B", "C"))})
    res.update({k: v for k, v in gpu.items() if k.startswith("R")})
    reg = [("R1", res["R1_identity"]["all_bit_identical"])]
    for k in ("R2_sphere_yuan", "R3_kr_sweep", "R4_dihedral"):
        if k in res:
            reg.append((k, bool(res[k]["unchanged"])))
    res["verdict"] = dict(
        regression_checks=dict(reg),
        regression_clean=bool(all(v for _, v in reg)),
        parts_present=dict(cpu=True, gpu=bool(gpu)),
        cpu_wall_s=cpu.get("wall_s"), gpu_wall_s=gpu.get("wall_s"))
    json.dump(res, open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(json.dumps(res["verdict"], indent=2, ensure_ascii=False))
    print(f"\n저장 → {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
