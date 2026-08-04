# -*- coding: utf-8 -*-
"""
smoke_ptd.py — src/ptd_edges.py 스모크 (CPU 전용, GPU 안 씀)
============================================================

필수 4 검사
  (f) ⭐ **위상 게이트** — 평판 on-cone 모서리에서 arg(A_code / A_analytic) = 0° 인가.
      크기비 |ratio| 는 180° 부호오류를 **통과시킨다**(실제로 통과시켰다, D-1/D-7). 그래서
      게이트는 위상이다. 실패하면 즉시 예외를 던지고 나머지를 돌리지 않는다.
  (a) ptd=False 일 때 기존 σ 와 **비트 단위로 동일**한가 (회귀 없음 증명)
  (b) 매끄러운 구에서 모서리 기여가 작은가 (구는 진짜 날카로운 모서리가 없다 — Rung 0)
  (c) 평판에서 0 이 아닌 기여가 나오는가

덤으로 계수 자체를 시험하는 두 칸(공짜라서 넣었다)
  (d) N → 1(평면)에서 프린지가 스스로 0 으로 가는가 — docs §3.7
  (e) 온-콘 반평면에서 Michaeli EEC ↔ Ufimtsev f¹/g¹ 가 **상수비**인가 — docs §8 Rung 1 의
      "⚠ 우리가 아직 확인 안 함. 구현 후 첫 검사로" 항목

정규화 상수(−½)는 (f) 가 크기와 부호를 **둘 다** 고정한다. Rung 2(평판 σ(θ) vs MoM)는 그
위에서 물리 잔차를 재는 칸이다.
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

_SRC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import ptd_edges as pe                                              # noqa: E402
from geom import Mesh                                               # noqa: E402
from rcs_po import (C0, mesh_to_points, rcs_from_points, dbsm,      # noqa: E402
                    _plate_mesh, _sphere_mesh, _look_dirs)

FC = 3.5e9
LAM = C0 / FC
#  ptd=True 경로의 PO 간격 — λ/20 (D-8: 프린지 항이 정확 PO 에 대해 정의돼 있으므로
#  중점구적 오차가 프린지 진폭 대비 충분히 작아야 한다). ptd=False 회귀는 옛 간격 그대로 쓴다.
SP_PTD = LAM / 20.0


def _bits(a):
    return np.ascontiguousarray(np.asarray(a, np.float64)).tobytes()


# --------------------------------------------------------------------------- #
def _rect_plate(a, b):
    """z=0 평면, 법선 +z, x 방향 a, y 방향 b 인 직사각 평판."""
    m = Mesh("plate")
    hx, hy = a / 2.0, b / 2.0
    i = [m.add_vertex(*p) for p in ((-hx, -hy, 0), (hx, -hy, 0), (hx, hy, 0), (-hx, hy, 0))]
    m.add_quad(*i)
    return m


def _subset_edges(es, keep):
    import dataclasses
    return dataclasses.replace(
        es, P0=es.P0[keep], P1=es.P1[keep], T=es.T[keep], X=es.X[keep], Y=es.Y[keep],
        L=es.L[keep], Nw=es.Nw[keep], boundary=es.boundary[keep], gmin=es.gmin[keep],
        n1=es.n1[keep], n2=es.n2[keep])


def _f1g1(phi0):
    """반평면(α=2π) 모노스태틱 Ufimtsev 프린지 계수 (docs §3.6 닫힌형)."""
    s, c = np.sin(phi0), np.cos(phi0)
    t = (1.0 - s) / c
    return 0.5 * (t - 1.0), -0.5 * (1.0 + t)


def test_f_sign_phase(a_lam=6.0, b_lam=40.0):
    """(f) ⭐ 위상 게이트 — 이것이 정규화 상수의 부호를 지키는 유일한 검사다.

    참조: 폭 a 인 띠의 Ufimtsev 모서리파 해석형
        A_edge = +(j/k) L Σ f¹_i e^{j2k r_i·û}   (soft, 코드 pol=H)
        A_edge = −(j/k) L Σ g¹_i e^{j2k r_i·û}   (hard, 코드 pol=V)
    같은 상수 +(j/k) 가 **PO 항의 끝점전개**도 정확 PO 폐형해 a cosθ sinc(ka sinθ) 로
    9 자리까지 재현한다 → 상수의 부호는 취향이 아니라 PO 와의 상대부호다.

    합격: |arg(A_code/A_ref)| < 1e-6 deg  (**|ratio| 만 보면 180° 오류가 통과한다**).
    """
    k = 2 * np.pi / LAM
    a_m, b_m = a_lam * LAM, b_lam * LAM
    mesh = _rect_plate(a_m, b_m)
    edges = pe.extract_edges(mesh)
    eo = _subset_edges(edges, np.abs(edges.T[:, 1]) > 0.99)     # t̂ ∥ ŷ → 시선수직(on-cone)
    rows = []
    for th in (5.0, 10.0, 20.0, 25.0, 30.0, 40.0, 50.0, 60.0, 65.0, 75.0, 80.0, 84.0):
        r = np.radians(th)
        u = np.array([np.sin(r), 0.0, np.cos(r)])
        X = k * a_m * np.sin(r)
        f1p, g1p = _f1g1(np.pi / 2 + r)
        f1m, g1m = _f1g1(np.pi / 2 - r)
        Sf = f1p * np.exp(1j * X) + f1m * np.exp(-1j * X)
        Sg = g1p * np.exp(1j * X) + g1m * np.exp(-1j * X)
        for pol, ref in (("H", (1j / k) * Sf * b_m), ("V", -(1j / k) * Sg * b_m)):
            rt = pe.edge_field(eo, FC, u, pol=pol)[0] / ref
            rows.append(dict(theta_deg=th, pol=pol, abs_ratio=float(abs(rt)),
                             phase_deg=float(np.degrees(np.angle(rt)))))
    mx_abs = max(abs(r["abs_ratio"] - 1.0) for r in rows)
    mx_arg = max(abs(r["phase_deg"]) for r in rows)
    return dict(n_probe=len(rows), rows=rows,
                max_abs_ratio_dev=mx_abs, max_abs_phase_deg=mx_arg,
                a_lambda=a_lam, b_lambda=b_lam,
                constant=pe.A_FW_CONST,
                gate="abs(arg(A_code/A_analytic)) < 1e-6 deg",
                passes=bool(mx_arg < 1e-6 and mx_abs < 1e-9),
                why_phase_not_magnitude=("the magnitude test passes with a 180 deg sign error "
                                         "and did so until 2026-08-03 (defect D-1/D-7)"))


# --------------------------------------------------------------------------- #
def test_a_regression():
    """(a) ptd=False 회귀 — 두 겹으로 본다.
      a1) 래퍼(ptd=False) 출력 vs rcs_po.rcs_from_points 직접 호출  → 비트 동일해야 한다
      a2) 래퍼가 ptd=True 에서 쓰는 복제 커널 _po_field_dirs 로 만든 σ vs 원본 σ
          → 여기까지 비트 동일해야 'PTD 를 껐다 켰다' 가 순수 가산임이 증명된다"""
    out = {}
    for name, mesh, sp, el in [("plate", _plate_mesh(0.30), LAM / 10, 90.0),
                               ("sphere", _sphere_mesh(0.30, seg=30, rings=16), LAM / 8, 0.0)]:
        az = np.arange(0.0, 360.0, 15.0)
        P, N, dA = mesh_to_points(mesh, sp)
        ref = rcs_from_points(P, N, dA, FC, az, el)
        sig, meta = pe.rcs_po_ptd(mesh, FC, az, el_deg=el, spacing=sp, ptd=False)
        E = pe._po_field_dirs(P, N, dA, FC, az, el)
        sig2 = (4 * np.pi / LAM ** 2) * np.abs(E) ** 2
        out[name] = dict(wrapper_bit_identical=(_bits(ref) == _bits(sig)),
                         replicated_kernel_bit_identical=(_bits(ref) == _bits(sig2)),
                         max_abs_diff_wrapper=float(np.max(np.abs(ref - sig))),
                         max_abs_diff_kernel=float(np.max(np.abs(ref - sig2))),
                         t_surface_s=meta["t_surface_s"])
    out["all_identical"] = all(v["wrapper_bit_identical"] and v["replicated_kernel_bit_identical"]
                               for v in out.values() if isinstance(v, dict))
    return out


# --------------------------------------------------------------------------- #
def test_b_sphere():
    """(b) 테셀레이션 구 — 진짜 모서리가 없으므로 PTD 를 켜도 σ 가 거의 안 움직여야 한다."""
    r = 0.30
    mesh = _sphere_mesh(r, seg=60, rings=30)          # rcs_po._sphere_mesh 기본값과 동일
    az = np.arange(0.0, 360.0, 30.0)
    sp = SP_PTD                       # D-8: ptd=True 경로는 λ/20 이하
    s_po, m0 = pe.rcs_po_ptd(mesh, FC, az, spacing=sp, ptd=False)
    res = dict(n_az=len(az), r_m=r, seg=60, rings=30,
               t_surface_s=m0["t_surface_s"], sigma_po_dbsm_mean=float(dbsm(s_po.mean())))
    for pol in ("V", "H"):
        s_pt, m = pe.rcs_po_ptd(mesh, FC, az, spacing=sp, ptd=True, pol=pol)
        d = dbsm(s_pt) - dbsm(s_po)
        res[pol] = dict(max_abs_delta_db=float(np.max(np.abs(d))),
                        mean_abs_delta_db=float(np.mean(np.abs(d))),
                        edge_over_po_db=float(20 * np.log10(
                            max(np.max(np.array(m["A_edge_abs"]) / np.array(m["A_po_abs"])), 1e-30))),
                        t_edge_s=m["t_edge_s"], t_extract_s=m["t_extract_s"],
                        t_surface_s=m["t_surface_s"])
        res.setdefault("edges", m["edges"])
        res.setdefault("edge_meta", m["edge"])
    res["max_abs_delta_db"] = max(res["V"]["max_abs_delta_db"], res["H"]["max_abs_delta_db"])
    res["rung0_gate_0p3dB_pass"] = bool(res["max_abs_delta_db"] < 0.3)

    # 문턱 민감도 — 기본 5° 가 '진짜 일을 하는지', 그리고 0°(전부 유지)에서 얼마나 나빠지는지.
    #  docs §3.7 경고: 촘촘한 가짜 모서리는 코히어런트로 쌓일 수 있다.
    sens = {}
    for sd in (0.0, 2.0, 5.0, 10.0):
        e2 = pe.extract_edges(mesh, sharp_deg=sd)
        w = {}
        for pol in ("V", "H"):
            s2, m2 = pe.rcs_po_ptd(mesh, FC, az, spacing=sp, ptd=True, pol=pol, edges=e2)
            w[pol] = float(np.max(np.abs(dbsm(s2) - dbsm(s_po))))
        sens[f"sharp_deg={sd}"] = dict(n_edges=len(e2), max_abs_delta_db=max(w.values()),
                                       V=w["V"], H=w["H"])
    res["sharp_deg_sensitivity"] = sens
    return res


# --------------------------------------------------------------------------- #
def test_c_plate():
    """(c) 정사각 평판 — 모서리 기여가 0 이 아니어야 한다.
    doc §8 Rung 2 의 표적(6λ×6λ)을 쓰고, 시선은 법선에서 θ 만큼 기운 주평면 컷."""
    a = 6.0 * LAM
    mesh = _plate_mesh(a)
    th = np.array([0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 7.0, 10.0, 15.0, 20.0,
                   25.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0])
    el = 90.0 - th
    sp = SP_PTD                       # D-8: ptd=True 경로는 λ/20 이하
    res = dict(a_m=float(a), a_lambda=6.0, theta_deg=th.tolist(),
               first_null_deg=float(np.degrees(np.arcsin(LAM / (2 * a)))))
    s_po = np.array([pe.rcs_po_ptd(mesh, FC, [0.0], el_deg=e, spacing=sp, ptd=False)[0][0]
                     for e in el])
    res["sigma_po_dbsm"] = dbsm(s_po).tolist()
    res["sigma_po_normal_dbsm"] = float(dbsm(s_po[0]))
    res["sigma_po_normal_exact_dbsm"] = float(dbsm(4 * np.pi * (a * a) ** 2 / LAM ** 2))

    edges = pe.extract_edges(mesh)
    res["edges"] = dict(edges.stats)
    for pol in ("V", "H"):
        sg, dd, ae, t_e = [], [], [], 0.0
        for e in el:
            s, m = pe.rcs_po_ptd(mesh, FC, [0.0], el_deg=e, spacing=sp, ptd=True,
                                 pol=pol, edges=edges)
            sg.append(s[0]); t_e += m["t_edge_s"]
            ae.append(m["A_edge_abs"][0] / max(m["A_po_abs"][0], 1e-300))
        sg = np.array(sg)
        dd = dbsm(sg) - dbsm(s_po)
        lobe = th <= res["first_null_deg"]
        res[pol] = dict(sigma_ptd_dbsm=dbsm(sg).tolist(),
                        delta_db=dd.tolist(),
                        edge_over_po_db=(20 * np.log10(np.maximum(ae, 1e-30))).tolist(),
                        max_abs_delta_db=float(np.max(np.abs(dd))),
                        specular_lobe_max_abs_delta_db=float(np.max(np.abs(dd[lobe]))),
                        nonzero=bool(np.max(np.abs(dd)) > 1e-6),
                        t_edge_s=t_e)
    res["max_abs_delta_db"] = max(res["V"]["max_abs_delta_db"], res["H"]["max_abs_delta_db"])
    res["nonzero"] = res["V"]["nonzero"] and res["H"]["nonzero"]
    return res


# --------------------------------------------------------------------------- #
def test_d_flat_limit():
    """(d) N → 1 (외부각 α → π = 평면) 에서 프린지 계수가 스스로 0 으로 가는가."""
    k = 2 * np.pi / LAM
    rows = []
    for N in (1.0, 1.001, 1.01, 1.1, 1.5, 2.0):
        Nw = np.array([N]); bp = np.array([np.radians(70.0)]); pp = np.array([np.radians(50.0)])
        Ie, Me, _ = pe.fringe_eec(Nw, bp, pp, np.pi - bp, pp, np.array([1.0 + 0j]),
                                  np.array([0.0 + 0j]), k)
        Ih, Mh, _ = pe.fringe_eec(Nw, bp, pp, np.pi - bp, pp, np.array([0.0 + 0j]),
                                  np.array([1.0 / pe.Z0 + 0j]), k)
        rows.append(dict(N=N, alpha_deg=180.0 * N,
                         abs_ZI_Epol=float(abs(pe.Z0 * Ie[0])), abs_M_Hpol=float(abs(Mh[0]))))
    ref = rows[-1]["abs_ZI_Epol"]
    return dict(rows=rows,
                vanishes_at_N1=bool(rows[0]["abs_ZI_Epol"] / ref < 1e-12
                                    and rows[0]["abs_M_Hpol"] / rows[-1]["abs_M_Hpol"] < 1e-12),
                amp_db_at_alpha_180p18deg=float(20 * np.log10(rows[1]["abs_ZI_Epol"] / ref)),
                amp_db_at_alpha_198deg=float(20 * np.log10(rows[3]["abs_ZI_Epol"] / ref)),
                note="doc 3.7 predicts ~-32 dB per edge at 1 deg dihedral deviation vs a real "
                     "270 deg wedge; 0.18 deg here gives -46.3 dB, i.e. -31.4 dB at 1 deg "
                     "(linear in the deviation). Independent agreement with the doc table.")


def test_e_ufimtsev():
    """(e) 온-콘 반평면(N=2, β'=90°, 모노스태틱)에서 Michaeli EEC 가 Ufimtsev f¹/g¹ 를 재현하는가.

    측정된 닫힌관계: `Z·I^f = j(2/k) f¹`, `M^f = j(2/k) g¹`.
    ⚠ 참조식 자체가 φ'→90° 에서 무너진다(f, f⁰ 가 각각 ±∞ 로 발산 — docs §3.6 경고).
      그래서 |cos φ'| < 1e−2 구간은 **참조를 못 믿어서** 비교에서 뺀다. 그 구간은 대신
      해석 불변량(f¹=g¹=−1/2 at φ'=90°, f¹+g¹=−1)으로 따로 시험한다."""
    k = 2 * np.pi / LAM
    c = 2.0 / k
    rows, ef, eg = [], [], []
    for d in np.arange(10.0, 171.0, 2.5):
        if abs(np.cos(np.radians(d))) < 1e-2:          # 참조식 붕괴 구간 제외
            continue
        pp = np.array([np.radians(d)]); Nw = np.array([2.0]); bp = np.array([np.pi / 2])
        f1, g1 = pe.ufimtsev_fringe(np.radians(d), np.radians(d), 2 * np.pi)
        Ie, _, _ = pe.fringe_eec(Nw, bp, pp, np.pi - bp, pp, np.array([1.0 + 0j]),
                                 np.array([0.0 + 0j]), k)
        _, Mh, _ = pe.fringe_eec(Nw, bp, pp, np.pi - bp, pp, np.array([0.0 + 0j]),
                                 np.array([1.0 / pe.Z0 + 0j]), k)
        f_eec = (pe.Z0 * Ie[0] / (1j * c))
        g_eec = (Mh[0] / (1j * c))
        ef.append(abs(f_eec - f1)); eg.append(abs(g_eec - g1))
        rows.append((float(d), float(f1), float(f_eec.real), float(g1), float(g_eec.real)))
    ef = np.array(ef); eg = np.array(eg)

    # 정규화가 발동하는 지점(φ'=90°)의 해석 불변량 — docs §3.6
    pp = np.array([np.pi / 2]); Nw = np.array([2.0]); bp = np.array([np.pi / 2])
    Ie, _, dg = pe.fringe_eec(Nw, bp, pp, np.pi - bp, pp, np.array([1.0 + 0j]),
                              np.array([0.0 + 0j]), k)
    _, Mh, _ = pe.fringe_eec(Nw, bp, pp, np.pi - bp, pp, np.array([0.0 + 0j]),
                             np.array([1.0 / pe.Z0 + 0j]), k)
    f90 = float((pe.Z0 * Ie[0] / (1j * c)).real)
    g90 = float((Mh[0] / (1j * c)).real)

    # f¹+g¹ = −1 (모든 φ') 불변량
    sums = [r[2] + r[4] for r in rows]
    return dict(n_angles=len(rows),
                max_abs_err_f=float(ef.max()), max_abs_err_g=float(eg.max()),
                closed_form="Z*I^f = j*(2/k)*f1,  M^f = j*(2/k)*g1   (measured, exact)",
                invariant_f_plus_g_max_dev=float(np.max(np.abs(np.array(sums) + 1.0))),
                at_phi90_regularized=dict(n_regularized=dg["n_regularized"],
                                          f1=f90, g1=g90, exact=-0.5,
                                          abs_err=float(max(abs(f90 + 0.5), abs(g90 + 0.5)))),
                passes=bool(ef.max() < 1e-9 and eg.max() < 1e-9
                            and np.max(np.abs(np.array(sums) + 1.0)) < 1e-9
                            and max(abs(f90 + 0.5), abs(g90 + 0.5)) < 1e-4))


# --------------------------------------------------------------------------- #
def main():
    t0 = time.perf_counter()
    out = {"fc_hz": FC, "lambda_m": LAM}

    print("== (f) ⭐ 위상 게이트 (정규화 상수의 부호) ==")
    out["f_sign_phase_gate"] = test_f_sign_phase()
    f = out["f_sign_phase_gate"]
    print(f"  상수 A_FW_CONST = {f['constant']}   probes {f['n_probe']}")
    print(f"  max ||ratio|−1| = {f['max_abs_ratio_dev']:.3e}   "
          f"max |arg(ratio)| = {f['max_abs_phase_deg']:.3e} deg")
    print(f"  게이트({f['gate']}): {'PASS' if f['passes'] else 'FAIL'}")
    if not f["passes"]:
        raise AssertionError(
            "위상 게이트 실패 — 프린지 항의 전체 복소상수가 틀렸다. "
            "max|arg| = %.3e deg (허용 1e-6). 나머지 검사를 돌리지 않는다."
            % f["max_abs_phase_deg"])

    print("\n== (a) ptd=False 회귀 ==")
    out["a_regression"] = test_a_regression()
    print(json.dumps(out["a_regression"], indent=2, ensure_ascii=False))

    print("\n== (d) 평면극한 N→1 ==")
    out["d_flat_limit"] = test_d_flat_limit()
    print(json.dumps(out["d_flat_limit"], indent=2, ensure_ascii=False))

    print("\n== (e) 온-콘 Ufimtsev 대조 ==")
    out["e_ufimtsev_oncone"] = test_e_ufimtsev()
    print(json.dumps(out["e_ufimtsev_oncone"], indent=2, ensure_ascii=False))

    print("\n== (b) 테셀레이션 구 (Rung 0) ==")
    out["b_sphere"] = test_b_sphere()
    b = out["b_sphere"]
    print(f"  edges kept={b['edges']['n_kept']}/{b['edges']['n_edges_total']} "
          f"(flat drop {b['edges']['n_dropped_flat']}), alpha {b['edges']['alpha_deg_min']:.2f}"
          f"~{b['edges']['alpha_deg_max']:.2f} deg")
    print(f"  max|Δσ| V={b['V']['max_abs_delta_db']:.4f} dB  H={b['H']['max_abs_delta_db']:.4f} dB"
          f"   |A_edge/A_PO|max={b['V']['edge_over_po_db']:.2f} dB")
    print(f"  Rung0 게이트(<0.3 dB): {'PASS' if b['rung0_gate_0p3dB_pass'] else 'FAIL'}")
    print(f"  비용: 면적분 {b['V']['t_surface_s']*1e3:.1f} ms / 모서리 {b['V']['t_edge_s']*1e3:.1f} ms"
          f" / 추출 {b['V']['t_extract_s']*1e3:.1f} ms")

    print("\n== (c) 평판 (6λ×6λ) ==")
    out["c_plate"] = test_c_plate()
    c = out["c_plate"]
    print(f"  PO 수직입사 {c['sigma_po_normal_dbsm']:.3f} dBsm (정확 PO {c['sigma_po_normal_exact_dbsm']:.3f})"
          f"  첫 널 {c['first_null_deg']:.2f} deg")
    print("   θ[deg]   σ_PO      σ_PO+PTD(V)  Δ(V)     Δ(H)   |A_e/A_PO|(V)")
    for i, t in enumerate(c["theta_deg"]):
        print(f"  {t:6.1f} {c['sigma_po_dbsm'][i]:9.3f} {c['V']['sigma_ptd_dbsm'][i]:11.3f}"
              f" {c['V']['delta_db'][i]:+8.3f} {c['H']['delta_db'][i]:+8.3f}"
              f" {c['V']['edge_over_po_db'][i]:9.2f}")
    print(f"  정반사 로브 안 최대|Δ| V={c['V']['specular_lobe_max_abs_delta_db']:.3f} dB "
          f"(Rung2 제안기준 0.5 dB)")
    print(f"  비용: 모서리 {c['V']['t_edge_s']*1e3:.1f} ms / {len(c['theta_deg'])} 방향")

    out["approximations"] = pe.APPROXIMATIONS
    out["not_implemented"] = pe.NOT_IMPLEMENTED
    out["open_defects"] = pe.OPEN_DEFECTS          # D-11 출처규칙: 열린 결함을 함께 싣는다
    out["sign_convention_verified"] = pe.SIGN_CONVENTION_VERIFIED
    out["wall_s"] = time.perf_counter() - t0

    dst = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                       "..", "outputs", "smoke_ptd.json"))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "w") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)
    print(f"\n저장: {dst}   (총 {out['wall_s']:.1f} s)")
    return out


if __name__ == "__main__":
    main()
