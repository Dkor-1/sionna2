# -*- coding: utf-8 -*-
"""ptd_plate_validation.py — 검증 1: 평판 (docs/PTD_ILDC_FORMULATION.md §8 **Rung 2**)

무엇을 하는가
-------------
도체 직사각 평판의 **모노스태틱 RCS 대 입사각** 을 세 가지로 내고 서로 대조한다.

  (1) PO 만          — `rcs_po.rcs_from_points` (기존 커널, 그대로)
  (2) PO + PTD       — `ptd_edges.rcs_po_ptd(ptd=True)` (새 구현, **손대지 않은 상태**)
  (3) 참조해         — **2 차원 EFIE MoM** (`benchmark/mom2d_reference.py`).
                       근사 없음. 원형 실린더 정확해로 < 0.005 dB 검증됨.

추가로 (2b) **부호를 일부러 뒤집은 PTD** 를 음성대조군으로 같이 낸다 — 아래 §부호 참조.

왜 3 차원 MoM 이 아니라 2 차원인가
----------------------------------
문서 §8 Rung 2 가 지정한 참조(R2-a Öztürk Fig 3.7 / R2-c Ross 실측 / R2-d Knott 교재)는
§10 이 적었듯 **전부 그림 또는 미확보**라 숫자를 읽어올 수 없다. 그래서 참조를 직접 푼다.
3 차원 RWG MoM 은 6λ 판에서 1 만 미지수를 넘고 자체 검증 부담이 커서, 대신 **정확한
2 차원↔3 차원 대응**을 쓴다.

  판을 a(기울임 방향) × b(시선에 수직) 로 두고 주평면(φ=0) 컷을 보면, b 방향 위상이
  일정하므로 b 적분이 그대로 인수분해된다:

        sigma_3D(theta) = (2 b^2 / lam) * sigma_2D(theta)

  이 관계는 **PO 항에 대해 정확**하고(스크립트가 수치로 확인한다), 길이 b 인 두 모서리
  (t̂·û = 0, on-cone)의 프린지 항에 대해서도 정확하다. 길이 a 인 나머지 두 모서리는
  2 차원 모형에 없다 — b 가 커질수록 상대적으로 사라지며, 그 잔차를 **직접 측정해서**
  `contamination` 에 싣는다(전체 4 모서리 vs on-cone 2 모서리).

편파
----
  코드 pol="H" : ê = ŷ ∥ 길이 b 모서리 → 2 차원 **TM**(soft, Ufimtsev f¹)
  코드 pol="V" : ê ⊥ 그 모서리        → 2 차원 **TE**(hard, Ufimtsev g¹)

부호 — 이 스크립트가 찾아냈고, 이제는 지키는 것 (결함 D-1, 2026-08-03 수리)
--------------------------------------------------------------------------
평판의 on-cone 모서리에서 우리 코드의 프린지 장은 Ufimtsev 모서리파 해석형과 비교된다.

        A_edge = +(j/k) * L * sum_i f¹_i e^{j 2k r_i·û}      (soft, 코드 pol=H)
        A_edge = -(j/k) * L * sum_i g¹_i e^{j 2k r_i·û}      (hard, 코드 pol=V)

같은 상수 +(j/k) 가 **PO 항의 끝점 전개**도 정확 PO 폐형해로 재현한다(A_PO 끝점전개 =
Ufimtsev (3.33)) — 이 스크립트가 수치로 확인한다. 그래서 부호는 취향이 아니라 PO 항과의
**상대부호**다.

수리 전 이 프로브는 |ratio| = 1.000000 인데 arg = 180° 를 읽었다(크기만 맞고 부호 반대).
지금은 A_FW_CONST = −½ 로 고쳐져 |arg| ≤ 1e−12° 다. 프로브는 **상설 게이트**로 남는다 —
크기비만 보는 지표는 180° 오류를 통과시키기 때문이다(결함 D-7). 그것을 눈으로 보라고
**부호를 일부러 뒤집은 곡선**(`sign_flipped_control`)을 계속 같이 낸다.

출력
----
  outputs/ptd_plate_validation.json      (모든 곡선·수치)
  그림은 src/viz_ptd_plate_validation.py 가 이 JSON 만 읽어서 그린다.

실행:  PYTHONPATH=src python benchmark/ptd_plate_validation.py
작성 2026-08-03.
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (_HERE, os.path.join(_ROOT, "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import mom2d_reference as mom                                        # noqa: E402
import ptd_edges as pe                                               # noqa: E402
from geom import Mesh                                                # noqa: E402
from rcs_po import C0, mesh_to_points, rcs_from_points               # noqa: E402

FC = 3.5e9
LAM = C0 / FC
K = 2 * np.pi / LAM

A_LAM = 6.0            # 기울임 방향 폭 [λ]  — 문서 §8 Rung 2 의 표적 치수
B_LAM = 40.0           # 시선수직 span [λ]   — 2D↔3D 대응이 성립하도록 길게
A_M = A_LAM * LAM
B_M = B_LAM * LAM
#  PO 점구름 간격. λ/10 이면 중점법 구적오차가 첨두 대비 −70 dB 부근에 바닥을 깔아서
#  깊은 사이드로브(−65 dB 이하)에서 σ 가 최대 3 dB 흔들린다 — 그건 PO 물리가 아니라
#  우리 적분격자다. λ/20 으로 −12 dB 더 내리고, 그 잔차를 analytic_checks 에 실어 보고한다.
SPACING = LAM / 20.0

#  θ 격자: PO 의 sinc 널(sinθ = n λ/2a, n=1..)에 **정확히** 올라앉으면 dB 오차가 발산한다.
#  0.35° 간격은 6λ 판의 널(4.78/9.59/14.48/19.47/24.62/30.00/35.69/41.81/48.59/56.44/66.44°)
#  어디에도 걸리지 않는다. 격자를 바꾸면 널 근처 RMS 가 바뀐다는 사실을 JSON 에 적어 둔다.
TH = np.arange(0.0, 85.0, 0.35)
TH_NULL1 = float(np.degrees(np.arcsin(LAM / (2 * A_M))))     # 첫 널 = 정반사 로브 경계
TH_3DB = float(np.degrees(np.arcsin(1.39156 / (2 * np.pi / LAM * A_M))))   # 주엽 −3 dB
PO_NULLS = np.degrees(np.arcsin(np.arange(1, int(2 * A_LAM) + 1) / (2 * A_LAM)))
NULL_GUARD_DEG = 0.3         # 널에서 이만큼 떨어진 각도만 쓰는 '널 제외' 지표용

M_TM = 720             # MoM 세그먼트 수 (TM) — 120 seg/λ
M_TE = 360             # MoM 세그먼트 수 (TE) — 60 seg/λ (조립이 O(M²) python 루프)
M_TM_COARSE = 480
M_TE_COARSE = 240


def dbsm(x):
    return 10.0 * np.log10(np.maximum(np.asarray(x, float), 1e-300))


# --------------------------------------------------------------------------- #
#  기하
# --------------------------------------------------------------------------- #
def rect_plate(a, b):
    """z=0 평면, 법선 +z, x 방향 a, y 방향 b 인 직사각 평판(사각형 1 개 = 삼각형 2 개)."""
    m = Mesh("plate")
    hx, hy = a / 2.0, b / 2.0
    i = [m.add_vertex(*p) for p in ((-hx, -hy, 0), (hx, -hy, 0), (hx, hy, 0), (-hx, hy, 0))]
    m.add_quad(*i)
    return m


def subset_edges(es, keep):
    import dataclasses
    return dataclasses.replace(
        es, P0=es.P0[keep], P1=es.P1[keep], T=es.T[keep], X=es.X[keep], Y=es.Y[keep],
        L=es.L[keep], Nw=es.Nw[keep], boundary=es.boundary[keep], gmin=es.gmin[keep],
        n1=es.n1[keep], n2=es.n2[keep])


# --------------------------------------------------------------------------- #
#  Ufimtsev 반평면 모노스태틱 프린지 계수 (문서 §3.6 닫힌형)
# --------------------------------------------------------------------------- #
def f1g1(phi0):
    s, c = np.sin(phi0), np.cos(phi0)
    t = (1.0 - s) / c
    return 0.5 * (t - 1.0), -0.5 * (1.0 + t)


def analytic_2d(theta_rad, a, k):
    """2 차원 띠(width a)의 해석형 등가폭 W [m].  sigma_2D = k |W|^2.

    W_PO   = a cos θ sinc(k a sin θ)                         (PO 닫힌형, 정확)
    W_soft = W_PO + (j/k) Σ f¹_i e^{jφ_i}                    (PO + Ufimtsev 프린지)
    W_hard = W_PO − (j/k) Σ g¹_i e^{jφ_i}
    모서리는 x=±a/2, 국소 방위 φ' = 90°∓θ, 위상 φ_i = ±k a sin θ.
    """
    th = np.atleast_1d(theta_rad)
    X = k * a * np.sin(th)
    W_po = a * np.cos(th) * np.sinc(X / np.pi)
    f1p, g1p = f1g1(np.pi / 2 + th)          # x = +a/2
    f1m, g1m = f1g1(np.pi / 2 - th)          # x = −a/2
    Sf = f1p * np.exp(1j * X) + f1m * np.exp(-1j * X)
    Sg = g1p * np.exp(1j * X) + g1m * np.exp(-1j * X)
    return W_po, W_po + (1j / k) * Sf, W_po - (1j / k) * Sg


# --------------------------------------------------------------------------- #
#  2 차원 MoM 참조해
# --------------------------------------------------------------------------- #
def mom_reference(a, k, th_rad, m_tm, m_te, tag=""):
    t0 = time.perf_counter()
    nd_tm = mom.strip_nodes(a, m_tm)
    nd_te = mom.strip_nodes(a, m_te)
    pre_tm = mom.assemble_tm(nd_tm, k)
    t_tm = time.perf_counter() - t0
    t0 = time.perf_counter()
    pre_te = mom.assemble_te(nd_te, k, closed=False)
    t_te = time.perf_counter() - t0
    W_tm = np.empty(len(th_rad), complex)
    W_te = np.empty(len(th_rad), complex)
    for i, r in enumerate(th_rad):
        u = np.array([np.sin(r), np.cos(r)])
        e_r = np.array([-np.cos(r), np.sin(r)])
        W_tm[i] = (mom.Z0 / 2) * mom.solve_tm(pre_tm, u)[0]
        W_te[i] = (mom.Z0 / 2) * mom.solve_te(pre_te, u, e_r)[0]
    print("   MoM%s  TM %d seg (%.1f s)  TE %d seg (%.1f s)" % (tag, m_tm, t_tm, m_te, t_te))
    return W_tm, W_te


# --------------------------------------------------------------------------- #
#  지표
# --------------------------------------------------------------------------- #
def band_stats(th, err):
    err = np.asarray(err, float)
    return dict(n=int(err.size),
                rms_db=float(np.sqrt(np.mean(err ** 2))) if err.size else None,
                mean_abs_db=float(np.mean(np.abs(err))) if err.size else None,
                median_abs_db=float(np.median(np.abs(err))) if err.size else None,
                max_abs_db=float(np.max(np.abs(err))) if err.size else None,
                max_abs_at_theta_deg=float(th[int(np.argmax(np.abs(err)))]) if err.size else None)


def all_bands(th, err):
    core = th <= TH_3DB
    spec = th <= TH_NULL1
    obl = th > TH_NULL1
    dnull = np.array([np.min(np.abs(PO_NULLS - t)) for t in th])
    obl_off = obl & (dnull > NULL_GUARD_DEG)
    return dict(specular_core_3db=band_stats(th[core], err[core]),
                specular_lobe=band_stats(th[spec], err[spec]),
                oblique=band_stats(th[obl], err[obl]),
                oblique_off_null=band_stats(th[obl_off], err[obl_off]),
                all_angles=band_stats(th, err))


# --------------------------------------------------------------------------- #
def main():
    t_wall = time.perf_counter()
    print("== 검증 1 · 평판 (Rung 2) ==")
    print("   fc %.2f GHz  lam %.4f m   plate %.1f x %.1f lam  (%.3f x %.3f m)"
          % (FC / 1e9, LAM, A_LAM, B_LAM, A_M, B_M))
    print("   first PO null (specular-lobe edge) = %.3f deg" % TH_NULL1)

    out = dict(
        case="rectangular PEC flat plate, monostatic, principal-plane cut",
        fc_hz=FC, lambda_m=LAM, a_lambda=A_LAM, b_lambda=B_LAM, a_m=A_M, b_m=B_M,
        po_spacing_m=SPACING, theta_deg=TH.tolist(), first_null_deg=TH_NULL1,
        specular_core_3db_deg=TH_3DB, po_null_deg=PO_NULLS.tolist(),
        null_guard_deg=NULL_GUARD_DEG,
        theta_grid_note=("0.35 deg step deliberately misses every PO sinc null "
                         "(sin th = n lam/2a); on a grid that lands on a null the dB error "
                         "of the PO-only curve is unbounded and the RMS is grid-dependent."),
        pol_map={"H": "E parallel to the length-b edges -> 2-D TM (soft, Ufimtsev f1)",
                 "V": "E perpendicular to them          -> 2-D TE (hard, Ufimtsev g1)"},
    )

    th_r = np.radians(TH)

    # ---- 0. 참조해 솔버 자체 검증 ---------------------------------------- #
    print("\n-- 0. reference solver self-test (exact PEC circular cylinder)")
    out["reference_solver_selftest"] = mom.selftest(verbose=False)
    print("   worst |err| %.4f dB @240 seg -> %s"
          % (out["reference_solver_selftest"]["worst_abs_db_at_240seg"],
             "PASS" if out["reference_solver_selftest"]["passes"] else "FAIL"))

    # ---- 1. 3 차원 커널 (PO / PO+PTD / 부호반전 PTD) ---------------------- #
    print("\n-- 1. our 3-D kernels")
    mesh = rect_plate(A_M, B_M)
    P, Nv, dA = mesh_to_points(mesh, SPACING)
    edges = pe.extract_edges(mesh)
    out["edges"] = dict(edges.stats)
    oncone = np.abs(edges.T[:, 1]) > 0.99            # t̂ ∥ ŷ → 시선에 수직 (on-cone)
    edges_oncone = subset_edges(edges, oncone)
    print("   points %d   edges kept %d (on-cone %d)"
          % (len(dA), len(edges), int(oncone.sum())))

    E_po = np.empty(len(TH), complex)
    A_e = {"V": np.empty(len(TH), complex), "H": np.empty(len(TH), complex)}
    A_e_oncone = {"V": np.empty(len(TH), complex), "H": np.empty(len(TH), complex)}
    t0 = time.perf_counter()
    for i, th in enumerate(TH):
        el = 90.0 - th
        E_po[i] = pe._po_field_dirs(P, Nv, dA, FC, [0.0], el)[0]
        u = np.array([np.sin(np.radians(th)), 0.0, np.cos(np.radians(th))])
        for pol in ("V", "H"):
            A_e[pol][i] = pe.edge_field(edges, FC, u, pol=pol)[0]
            A_e_oncone[pol][i] = pe.edge_field(edges_oncone, FC, u, pol=pol)[0]
    t_kernel = time.perf_counter() - t0
    print("   swept %d angles x 2 pol in %.1f s" % (len(TH), t_kernel))

    C34 = 4 * np.pi / LAM ** 2
    sig = {"po": C34 * np.abs(E_po) ** 2}
    for pol in ("V", "H"):
        sig["ptd_" + pol] = C34 * np.abs(E_po + A_e[pol]) ** 2
        sig["ptdflip_" + pol] = C34 * np.abs(E_po - A_e[pol]) ** 2   # 음성대조군(부호 반전)

    # ---- 1b. 배포 경로 회귀 (일부 각도에서 래퍼와 일치하는가) ------------- #
    print("-- 1b. shipped-wrapper regression (rcs_po_ptd)")
    idx = np.linspace(0, len(TH) - 1, 21).astype(int)
    d_po = d_ptd = 0.0
    for i in idx:
        el = 90.0 - TH[i]
        s0 = rcs_from_points(P, Nv, dA, FC, [0.0], el)[0]
        d_po = max(d_po, abs(dbsm(s0) - dbsm(sig["po"][i])))
        for pol in ("V", "H"):
            s1 = pe.rcs_po_ptd(mesh, FC, [0.0], el_deg=el, spacing=SPACING,
                               ptd=True, pol=pol, edges=edges)[0][0]
            d_ptd = max(d_ptd, abs(dbsm(s1) - dbsm(sig["ptd_" + pol][i])))
    out["shipped_path_regression"] = dict(
        n_angles_checked=int(len(idx)),
        max_abs_db_po=float(d_po), max_abs_db_po_ptd=float(d_ptd),
        passes=bool(d_po < 1e-9 and d_ptd < 1e-9),
        note="fast path (_po_field_dirs + edge_field) vs the shipped wrappers "
             "(rcs_from_points, rcs_po_ptd). Must be identical or the sweep is not "
             "measuring the shipped code.")
    print("   max |Δ| PO %.2e dB, PO+PTD %.2e dB -> %s"
          % (d_po, d_ptd, "PASS" if out["shipped_path_regression"]["passes"] else "FAIL"))

    # ---- 2. 해석형 교차검사 (PO 닫힌형 + 2D↔3D 대응) --------------------- #
    print("\n-- 2. analytic cross-checks")
    W_po_a, W_soft_a, W_hard_a = analytic_2d(th_r, A_M, K)
    sig_po_closed = C34 * np.abs(W_po_a * B_M) ** 2
    d_all = np.abs(dbsm(sig["po"]) - dbsm(sig_po_closed))
    dnull = np.array([np.min(np.abs(PO_NULLS - t)) for t in TH])
    off = dnull > NULL_GUARD_DEG
    conv = (2 * B_M ** 2 / LAM)
    d_conv = float(np.max(np.abs(dbsm(sig_po_closed) - dbsm(conv * K * np.abs(W_po_a) ** 2))))
    out["analytic_checks"] = dict(
        po_numeric_vs_closed_form_max_abs_db=float(np.max(d_all)),
        po_numeric_vs_closed_form_max_abs_db_off_null=float(np.max(d_all[off])),
        po_numeric_vs_closed_form_rms_db_off_null=float(np.sqrt(np.mean(d_all[off] ** 2))),
        null_guard_deg=NULL_GUARD_DEG,
        two_d_to_three_d_conversion_max_abs_db=d_conv,
        sigma_po_normal_dbsm=float(dbsm(sig["po"][0])),
        sigma_po_normal_exact_dbsm=float(dbsm(4 * np.pi * (A_M * B_M) ** 2 / LAM ** 2)),
        note="A_PO closed form a b cos(th) sinc(k a sin th); the 2-D<->3-D factor "
             "sigma_3D = (2 b^2/lam) sigma_2D is exact for the PO term. The residual is "
             "the midpoint-rule quadrature floor of our own point-cloud PO, not physics; "
             "it only shows up in the deep sidelobes and right at the sinc nulls.")
    #  1 차 PTD 는 on-cone 모서리 쌍만으로는 두 편파의 |sigma| 를 **정확히 같게** 만든다.
    #  (W_soft, W_hard 의 허수부만 부호가 반대라 크기가 같다.) 실측·MoM 은 갈라지므로
    #  평판의 편파 갈라짐은 1 차 PTD 가 낼 수 없는 양이라는 뜻 — 문서 §8 Rung 2 의
    #  "PO+PTD 가 편파를 가른다" 는 기대와 어긋난다. 숫자로 남긴다.
    split = np.abs(dbsm(np.abs(W_soft_a) ** 2) - dbsm(np.abs(W_hard_a) ** 2))
    out["analytic_checks"]["first_order_ptd_pol_split_max_db"] = float(np.max(split))
    print("   PO numeric vs closed form   max |Δ| %.4f dB (off-null %.4f dB)"
          % (np.max(d_all), np.max(d_all[off])))
    print("   2D->3D conversion identity  max |Δ| %.4f dB" % d_conv)
    print("   1st-order PTD pol split (analytic, strip) max %.2e dB" % np.max(split))

    # ---- 3. 부호 프로브 (코드 프린지 vs Ufimtsev 모서리파 해석형) --------- #
    print("\n-- 3. sign probe: code edge field vs analytic Ufimtsev edge wave")
    probe = []
    for th in (10.0, 20.0, 30.0, 45.0, 60.0, 75.0):
        r = np.radians(th)
        u = np.array([np.sin(r), 0.0, np.cos(r)])
        X = K * A_M * np.sin(r)
        f1p, g1p = f1g1(np.pi / 2 + r)
        f1m, g1m = f1g1(np.pi / 2 - r)
        Sf = f1p * np.exp(1j * X) + f1m * np.exp(-1j * X)
        Sg = g1p * np.exp(1j * X) + g1m * np.exp(-1j * X)
        for pol, ref in (("H", (1j / K) * Sf * B_M), ("V", -(1j / K) * Sg * B_M)):
            a_code = pe.edge_field(edges_oncone, FC, u, pol=pol)[0]
            ratio = a_code / ref
            probe.append(dict(theta_deg=th, pol=pol, abs_ratio=float(abs(ratio)),
                              phase_deg=float(np.degrees(np.angle(ratio)))))
    mx_arg = float(max(abs(p["phase_deg"]) for p in probe))
    mx_abs = float(max(abs(p["abs_ratio"] - 1.0) for p in probe))
    out["sign_probe"] = dict(
        rows=probe,
        max_abs_ratio_dev=mx_abs,
        max_abs_phase_deg=mx_arg,
        min_abs_phase_deg=float(min(abs(p["phase_deg"]) for p in probe)),
        gate="abs(arg(A_code / A_analytic)) < 1e-6 deg",
        passes=bool(mx_arg < 1e-6 and mx_abs < 1e-9),
        verdict=("PHASE is the gate, not magnitude: a magnitude-only test passes with a 180 deg "
                 "sign error and did so until 2026-08-03 (defect D-1/D-7). After the repair "
                 "(A_FW_CONST = -0.5) both magnitude and phase agree with the analytic Ufimtsev "
                 "edge wave."),
        analytic_form="A_edge = +(j/k) L sum f1_i e^{j2k r_i.u} (soft) ; "
                      "-(j/k) L sum g1_i e^{j2k r_i.u} (hard). Same constant maps the PO "
                      "endpoint expansion onto Ufimtsev f0 (3.33), verified numerically.")
    print("   |A_code/A_analytic| dev %.2e   max |phase| %.2e deg -> %s"
          % (mx_abs, mx_arg, "PASS" if out["sign_probe"]["passes"] else "FAIL"))
    if not out["sign_probe"]["passes"]:
        raise AssertionError("위상 게이트 실패: max|arg| = %.3e deg (허용 1e-6)" % mx_arg)

    # ---- 4. MoM 참조해 ---------------------------------------------------- #
    print("\n-- 4. MoM reference (2-D strip, both polarisations)")
    W_tm, W_te = mom_reference(A_M, K, th_r, M_TM, M_TE)
    W_tm_c, W_te_c = mom_reference(A_M, K, th_r, M_TM_COARSE, M_TE_COARSE, tag=" coarse")
    sig_ref = {"H": conv * K * np.abs(W_tm) ** 2,       # TM  = E ∥ edges = code pol H
               "V": conv * K * np.abs(W_te) ** 2}       # TE  = E ⊥ edges = code pol V
    sig_ref_c = {"H": conv * K * np.abs(W_tm_c) ** 2,
                 "V": conv * K * np.abs(W_te_c) ** 2}
    out["reference_convergence"] = {
        p: dict(max_abs_db=float(np.max(np.abs(dbsm(sig_ref[p]) - dbsm(sig_ref_c[p])))),
                rms_db=float(np.sqrt(np.mean((dbsm(sig_ref[p]) - dbsm(sig_ref_c[p])) ** 2))))
        for p in ("H", "V")}
    out["reference_convergence"]["n_seg_fine"] = dict(TM=M_TM, TE=M_TE)
    out["reference_convergence"]["n_seg_coarse"] = dict(TM=M_TM_COARSE, TE=M_TE_COARSE)
    print("   discretisation sensitivity  H %.3f dB   V %.3f dB (max)"
          % (out["reference_convergence"]["H"]["max_abs_db"],
             out["reference_convergence"]["V"]["max_abs_db"]))

    # ---- 5. 2 차원 참조와 3 차원 판의 대응 오염 (끝 모서리) --------------- #
    cont = {}
    for pol in ("V", "H"):
        s_full = C34 * np.abs(E_po + A_e[pol]) ** 2            # 수리된 커널로 잰다
        s_on = C34 * np.abs(E_po + A_e_oncone[pol]) ** 2
        d = dbsm(s_full) - dbsm(s_on)
        cont[pol] = dict(max_abs_db=float(np.max(np.abs(d))),
                         rms_db=float(np.sqrt(np.mean(d ** 2))),
                         max_abs_at_theta_deg=float(TH[int(np.argmax(np.abs(d)))]))
    out["contamination_end_edges"] = dict(
        per_pol=cont,
        note=("the two length-a edges exist in the 3-D plate but not in the 2-D strip "
              "reference. This is the residual mismatch of the comparison itself, "
              "measured as sigma(all 4 edges) - sigma(2 on-cone edges). It shrinks like "
              "a/b."))
    print("\n-- 5. 2-D<->3-D residual (end edges absent from the reference)")
    print("   max |Δ| H %.2f dB   V %.2f dB" % (cont["H"]["max_abs_db"], cont["V"]["max_abs_db"]))

    # ---- 5b. 참조해의 독립 물리 확인: 진행파(traveling-wave) 로브 -------- #
    #  E ⊥ 모서리(V) 편파에서 판 위를 달리는 진행파가 만드는 로브. 고전 근사각은
    #  스침각 기준 49.35/sqrt(L/λ) 도(Knott 계열). 이건 PO 도 1 차 PTD 도 못 내는 현상이라
    #  MoM 이 진짜로 그 물리를 담고 있는지 보는 **외부 대조**가 된다.
    obl = TH > 40.0
    i_pk = int(np.argmax(dbsm(sig_ref["V"])[obl]))
    th_pk = float(TH[obl][i_pk])
    th_tw = float(90.0 - 49.35 / np.sqrt(A_LAM))
    out["traveling_wave_check"] = dict(
        mom_V_peak_theta_deg=th_pk,
        mom_V_peak_dbsm=float(dbsm(sig_ref["V"])[obl][i_pk]),
        classic_estimate_theta_deg=th_tw,
        delta_deg=float(th_pk - th_tw),
        note=("classic travelling-wave lobe angle 90 - 49.35/sqrt(L/lam) deg for L = a. "
              "It appears only in the E-perpendicular-to-edge (V / hard) polarisation and "
              "is absent from both PO and first-order PTD, so this is an independent check "
              "that the MoM reference carries physics the asymptotic curves do not."))
    print("   travelling-wave lobe: MoM(V) peak %.2f deg vs classic %.2f deg (Δ %.2f)"
          % (th_pk, th_tw, th_pk - th_tw))

    # ---- 6. 오차 지표 ----------------------------------------------------- #
    print("\n-- 6. error vs reference")
    curves, errs = {}, {}
    for pol in ("H", "V"):
        ref_db = dbsm(sig_ref[pol])
        e_po = dbsm(sig["po"]) - ref_db
        e_ptd = dbsm(sig["ptd_" + pol]) - ref_db
        e_flip = dbsm(sig["ptdflip_" + pol]) - ref_db
        e_ana = dbsm(conv * K * np.abs(W_soft_a if pol == "H" else W_hard_a) ** 2) - ref_db
        errs[pol] = dict(po_only=all_bands(TH, e_po),
                         po_ptd=all_bands(TH, e_ptd),
                         po_ptd_sign_flipped_control=all_bands(TH, e_flip),
                         analytic_ufimtsev_ptd=all_bands(TH, e_ana))
        curves[pol] = dict(
            sigma_ref_dbsm=ref_db.tolist(),
            sigma_po_dbsm=dbsm(sig["po"]).tolist(),
            sigma_po_closed_form_dbsm=dbsm(sig_po_closed).tolist(),
            sigma_po_ptd_dbsm=dbsm(sig["ptd_" + pol]).tolist(),
            sigma_po_ptd_signflip_control_dbsm=dbsm(sig["ptdflip_" + pol]).tolist(),
            sigma_analytic_ptd_dbsm=dbsm(
                conv * K * np.abs(W_soft_a if pol == "H" else W_hard_a) ** 2).tolist())
        print("   pol %s  oblique RMS  PO %.2f dB | PO+PTD %.2f dB | (부호반전 대조군 %.2f dB)"
              % (pol, errs[pol]["po_only"]["oblique"]["rms_db"],
                 errs[pol]["po_ptd"]["oblique"]["rms_db"],
                 errs[pol]["po_ptd_sign_flipped_control"]["oblique"]["rms_db"]))
    out["curves"] = curves
    out["errors"] = errs

    # 편파 합산(헤드라인)
    def pooled(key, band):
        v = [errs[p][key][band]["rms_db"] for p in ("H", "V")]
        n = [errs[p][key][band]["n"] for p in ("H", "V")]
        return float(np.sqrt(sum(nn * vv ** 2 for nn, vv in zip(n, v)) / sum(n)))

    head = {}
    for band in ("specular_core_3db", "specular_lobe", "oblique", "oblique_off_null",
                 "all_angles"):
        head[band] = {k: pooled(k, band) for k in
                      ("po_only", "po_ptd", "po_ptd_sign_flipped_control",
                       "analytic_ufimtsev_ptd")}
    worst = {}
    for key in ("po_only", "po_ptd", "po_ptd_sign_flipped_control"):
        cand = [(errs[p][key]["all_angles"]["max_abs_db"],
                 errs[p][key]["all_angles"]["max_abs_at_theta_deg"], p) for p in ("H", "V")]
        m = max(cand)
        worst[key] = dict(abs_db=m[0], theta_deg=m[1], pol=m[2])
    out["headline_rms_db_pooled_over_pol"] = head
    out["worst_abs_error"] = worst
    out["verdict"] = dict(
        phase_gate_passes=bool(out["sign_probe"]["passes"]),
        specular_agreement=bool(head["specular_core_3db"]["po_only"] < 0.5
                                and head["specular_core_3db"]["po_ptd"] < 0.5),
        ptd_improves=bool(head["oblique"]["po_ptd"] < head["oblique"]["po_only"]),
        sign_flipped_control_also_improves=bool(
            head["oblique"]["po_ptd_sign_flipped_control"] < head["oblique"]["po_only"]),
        sign_defect_history=("found here 2026-08-03 07:57 (arg = 180 deg), fixed the same day in "
                             "src/ptd_edges.py A_FW_CONST = -0.5"),
        text=("PO and PO+PTD agree with the reference inside the specular lobe. In the oblique "
              "region PO alone departs badly and the PTD term recovers most of it. ⚠ The RMS "
              "improvement ALONE is not evidence of a correct kernel: the deliberately "
              "sign-flipped control also improves it (that is defect D-7), so the phase gate "
              "above is what decides. A several-dB oscillation remains in the hard polarisation "
              "that first-order PTD cannot represent (multiple edge interaction / travelling "
              "wave)."))

    out["limitations"] = [
        "Reference is a 2-D EFIE MoM of an infinite strip mapped to the a x b plate by the "
        "exact relation sigma_3D = (2 b^2/lam) sigma_2D. Exact for the PO term and for the "
        "two on-cone edges; the two end edges of the real plate are absent from the "
        "reference (residual measured in contamination_end_edges).",
        "First-order PTD only. Second-order (edge-to-edge) diffraction, corner diffraction "
        "and the truncated-wedge (Johansen) correction are all absent from the "
        "implementation (ptd_edges.NOT_IMPLEMENTED) and from the analytic curve.",
        "Angles beyond 85 deg (grazing / edge-on) are excluded: PO -> 0 there and both PO "
        "and first-order PTD are known to fail (Ross 1966, doc 8 Rung 2).",
        "dB-domain RMS is dominated by the PO sinc nulls, where the PO error is unbounded. "
        "median_abs_db is reported alongside for that reason.",
    ]
    out["wall_s"] = time.perf_counter() - t_wall

    dst = os.path.join(_ROOT, "outputs", "ptd_plate_validation.json")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "w") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)
    print("\n저장: %s   (%.1f s)" % (dst, out["wall_s"]))
    return out


if __name__ == "__main__":
    main()
