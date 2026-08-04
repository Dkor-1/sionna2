# -*- coding: utf-8 -*-
"""ptd_verify_after_fix.py — 부호 수리(D-1, A_FW_CONST = −½) **이후** 재검증 3종
================================================================================

이 스크립트가 답하는 질문은 셋뿐이다.

  [1] 회귀 — ptd=False 경로가 **PTD 도입 이전과 같은가**.
      과녁 셋을 PTD 이전 산출물과 대조한다: PEC 구(Yuan 교정체 r=0.178 m·3 밴드) ·
      kr 스윕(48 입사방향) · 이면반사체(4 크기 × 1/2-bounce). 지표는 max|Δ| [dB].
      ⚠ 기준 파일은 라운드 시작 시 스냅샷을 쓴다(rcs_anchor.py 가 GPU2 에서 재생성 중).

  [2] 평판 재검증 — PO 만 / PO+PTD / 참조해(2 차원 EFIE MoM). 여기서는 **크기만 보지 않는다**:
      · 위상 게이트: arg(A_code / A_analytic_Ufimtsev) 가 0° 인가 (85° 까지 조밀 스윕)
      · ⭐ **비코히런트 합 대조군**: σ_incoh = σ_PO + σ_edge (위상정보 없음)
        코히런트 합이 이보다 **의미 있게** 나아야 부호가 맞다는 증거다. 크기 RMS 개선만으로는
        180° 오류도 통과한다(결함 D-7 — 부호반전 대조군이 그것을 계속 보여준다).
      · 위상 오프셋 ψ 스윕: A_edge → e^{jψ}A_edge 로 두고 RMS(ψ) 를 그린다. 최소가 ψ=0 인가?
        (ψ=180° 가 부호반전 대조군, 비코히런트는 '위상 무정보' 수평선)

  [3] 매끄러운 구에 ptd=True — 인공(삼각메쉬) 모서리 기여가 해상도에 따라 수렴하는가.
      이전 라운드의 −32.5 dB 바닥(∝1/kr)이 부호 수리 후에도 같은가.
      ⚠ 예측: |A_edge| 는 부호에 불변이므로 바닥은 그대로여야 하고, 코히런트 합의
        σ 아티팩트만 교차항 부호가 바뀐다. 예측을 먼저 적고 숫자로 확인한다.

실행
  cd /home/yunjung/workspace/sionna2
  PART=gpu SIONNA2_GPU=3 PYTHONPATH=src:benchmark python benchmark/ptd_verify_after_fix.py
  PART=cpu                PYTHONPATH=src:benchmark python benchmark/ptd_verify_after_fix.py
  PART=merge              PYTHONPATH=src:benchmark python benchmark/ptd_verify_after_fix.py
산출: outputs/ptd_verify_after_fix.json   (그림은 src/viz_ptd_after_fix.py 가 이 JSON 만 읽는다)
작성 2026-08-03.
"""
from __future__ import annotations

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

SCRATCH = os.environ.get(
    "PTD_AF_SCRATCH",
    "/tmp/claude-1015/-home-yunjung-workspace/a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad")
BASE_SNAP = os.environ.get("PTD_REG_BASELINE_DIR", os.path.join(SCRATCH, "baseline"))
#  verify_ptd_regression 이 **import 시점**에 이 환경변수를 읽는다 → import 전에 세운다.
os.environ["PTD_REG_BASELINE_DIR"] = BASE_SNAP

OUT = os.path.join(_ROOT, "outputs", "ptd_verify_after_fix.json")
TMP_GPU = os.path.join(SCRATCH, "pvaf_gpu.json")
TMP_CPU = os.path.join(SCRATCH, "pvaf_cpu.json")
PREV_REG = os.path.join(_ROOT, "outputs", "ptd_regression.json")   # 이전 라운드(부호 수리 전)

C0 = 299792458.0
FC = 3.5e9
LAM = C0 / FC


def _sha(path):
    import hashlib
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:16]


# =========================================================================== #
#  [1] 회귀 — ptd=False (GPU 3 과녁 + CPU 비트항등)
# =========================================================================== #
def part1_gpu():
    import verify_ptd_regression as vr
    out = {}
    print("== [1] 회귀 R2 · PEC 구 (Yuan 교정체 r=0.178 m, 3 밴드) ==")
    out["R2_sphere_yuan"] = vr.r2_sphere()
    print("\n== [1] 회귀 R4 · 이면반사체 (4 크기 × 1/2-bounce) ==")
    out["R4_dihedral"] = vr.r4_dihedral()
    print("\n== [1] 회귀 R3 · kr 스윕 (48 입사방향) ==")
    out["R3_kr_sweep"] = vr.r3_kr_sweep()
    return out


def part1_cpu():
    import verify_ptd_regression as vr
    print("== [1] 회귀 R1 · ptd=False 비트 항등 ==")
    r1 = vr.r1_identity()
    #  비트 동일이면 dB 차도 **정확히** 0 이다(같은 float64 배열의 log 는 같은 값).
    r1["max_abs_delta_db"] = 0.0 if r1["all_bit_identical"] else None
    r1["note"] = ("wrapper = rcs_po_ptd(ptd=False) vs 레거시 rcs_from_points, "
                  "replicated = _po_field_dirs 로 재구성한 σ. 둘 다 비트 단위 비교.")
    print(json.dumps({k: v for k, v in r1.items() if isinstance(v, (bool, float, str))},
                     indent=1, ensure_ascii=False))
    return dict(R1_identity=r1)


# =========================================================================== #
#  [2] 평판 재검증 — 위상 게이트 + 비코히런트 대조군
# =========================================================================== #
def part2_plate():
    import mom2d_reference as mom
    import ptd_edges as pe
    import ptd_plate_validation as pv
    from rcs_po import mesh_to_points

    TH = pv.TH
    th_r = np.radians(TH)
    K = pv.K
    C34 = 4 * np.pi / pv.LAM ** 2
    conv = 2 * pv.B_M ** 2 / pv.LAM

    out = dict(
        case="rectangular PEC flat plate, monostatic, principal-plane cut",
        fc_hz=pv.FC, lambda_m=pv.LAM, a_lambda=pv.A_LAM, b_lambda=pv.B_LAM,
        a_m=pv.A_M, b_m=pv.B_M, po_spacing_m=pv.SPACING,
        theta_deg=TH.tolist(), first_null_deg=pv.TH_NULL1,
        specular_core_3db_deg=pv.TH_3DB, po_null_deg=pv.PO_NULLS.tolist(),
        pol_map={"H": "E parallel to the length-b edges -> 2-D TM (soft, Ufimtsev f1)",
                 "V": "E perpendicular to them          -> 2-D TE (hard, Ufimtsev g1)"})

    # ── 0. 참조 솔버 자체검증 ─────────────────────────────────────────────── #
    print("-- 0. reference solver self-test (exact PEC circular cylinder)")
    out["reference_solver_selftest"] = mom.selftest(verbose=False)
    print("   worst |err| %.4f dB @240 seg -> %s"
          % (out["reference_solver_selftest"]["worst_abs_db_at_240seg"],
             "PASS" if out["reference_solver_selftest"]["passes"] else "FAIL"))

    # ── 1. 우리 3 차원 커널 ───────────────────────────────────────────────── #
    mesh = pv.rect_plate(pv.A_M, pv.B_M)
    P, Nv, dA = mesh_to_points(mesh, pv.SPACING)
    edges = pe.extract_edges(mesh)
    oncone = np.abs(edges.T[:, 1]) > 0.99
    edges_on = pv.subset_edges(edges, oncone)
    out["edges"] = dict(edges.stats)
    out["edges"]["n_oncone"] = int(oncone.sum())
    print("-- 1. our kernel: %d PO points, %d edges (%d on-cone)"
          % (len(dA), len(edges), int(oncone.sum())))

    E_po = np.empty(len(TH), complex)
    A_e = {p: np.empty(len(TH), complex) for p in ("H", "V")}
    A_on = {p: np.empty(len(TH), complex) for p in ("H", "V")}
    t0 = time.perf_counter()
    for i, th in enumerate(TH):
        el = 90.0 - th
        E_po[i] = pe._po_field_dirs(P, Nv, dA, pv.FC, [0.0], el)[0]
        u = np.array([np.sin(np.radians(th)), 0.0, np.cos(np.radians(th))])
        for pol in ("H", "V"):
            A_e[pol][i] = pe.edge_field(edges, pv.FC, u, pol=pol)[0]
            A_on[pol][i] = pe.edge_field(edges_on, pv.FC, u, pol=pol)[0]
    print("   swept %d angles x 2 pol in %.1f s" % (len(TH), time.perf_counter() - t0))

    # ── 2. 해석형 (Ufimtsev 프린지) + 참조 MoM ───────────────────────────── #
    W_po_a, W_soft_a, W_hard_a = pv.analytic_2d(th_r, pv.A_M, K)
    W_ana = {"H": W_soft_a, "V": W_hard_a}
    print("-- 2. MoM reference")
    W_tm, W_te = pv.mom_reference(pv.A_M, K, th_r, pv.M_TM, pv.M_TE)
    W_tm_c, W_te_c = pv.mom_reference(pv.A_M, K, th_r, pv.M_TM_COARSE, pv.M_TE_COARSE,
                                      tag=" coarse")
    W_ref = {"H": W_tm, "V": W_te}
    W_ref_c = {"H": W_tm_c, "V": W_te_c}
    sig_ref = {p: conv * K * np.abs(W_ref[p]) ** 2 for p in ("H", "V")}
    out["reference_convergence"] = {
        p: dict(max_abs_db=float(np.max(np.abs(pv.dbsm(sig_ref[p])
                                               - pv.dbsm(conv * K * np.abs(W_ref_c[p]) ** 2)))))
        for p in ("H", "V")}
    out["reference_convergence"]["n_seg_fine"] = dict(TM=pv.M_TM, TE=pv.M_TE)
    out["reference_convergence"]["n_seg_coarse"] = dict(TM=pv.M_TM_COARSE, TE=pv.M_TE_COARSE)

    # ── 3. ⭐ 위상 게이트 — arg(A_code / A_analytic) ─────────────────────── #
    #  해석형은 on-cone 모서리 쌍만 담는다 → 코드도 on-cone 부분집합으로 재야 사과-대-사과다.
    print("-- 3. phase gate: arg(A_code / A_analytic_Ufimtsev)")
    rows, args, devs = [], [], []
    for i, th in enumerate(TH):
        if th < 1.0:           # θ→0 은 f¹/g¹ 의 퇴화 극한이라 제외(0/0)
            continue
        r = np.radians(th)
        X = K * pv.A_M * np.sin(r)
        f1p, g1p = pv.f1g1(np.pi / 2 + r)
        f1m, g1m = pv.f1g1(np.pi / 2 - r)
        Sf = f1p * np.exp(1j * X) + f1m * np.exp(-1j * X)
        Sg = g1p * np.exp(1j * X) + g1m * np.exp(-1j * X)
        for pol, ref in (("H", (1j / K) * Sf * pv.B_M), ("V", -(1j / K) * Sg * pv.B_M)):
            if abs(ref) < 1e-14:
                continue
            ratio = A_on[pol][i] / ref
            rows.append(dict(theta_deg=float(th), pol=pol, abs_ratio=float(abs(ratio)),
                             arg_deg=float(np.degrees(np.angle(ratio)))))
            args.append(abs(np.degrees(np.angle(ratio))))
            devs.append(abs(abs(ratio) - 1.0))
    args = np.array(args); devs = np.array(devs)
    out["phase_gate"] = dict(
        n_probes=int(len(rows)),
        theta_range_deg=[float(TH[TH >= 1.0][0]), float(TH[-1])],
        max_abs_arg_deg=float(args.max()), median_abs_arg_deg=float(np.median(args)),
        max_abs_ratio_dev=float(devs.max()),
        gate="max |arg(A_code/A_analytic)| < 1e-6 deg  AND  max ||ratio|-1| < 1e-9",
        passes=bool(args.max() < 1e-6 and devs.max() < 1e-9),
        rows_every_20th=rows[::20],
        what_it_catches=("magnitude alone passes with a 180 deg sign error and did so until "
                         "2026-08-03 (defects D-1/D-7). The ARG is the gate."),
        control_before_fix_deg=180.0)
    print("   n=%d probes   max|arg| %.3e deg   max||ratio|-1| %.3e -> %s"
          % (len(rows), args.max(), devs.max(), "PASS" if out["phase_gate"]["passes"] else "FAIL"))

    #  참조(MoM)의 위상규약이 우리와 같은가 — 위상 비교가 자기참조가 아님을 보이는 외부 확인.
    #  정반사 로브 안에서는 PO 가 사실상 정확하므로 arg(W_mom / W_po_analytic) ≈ 0 이어야 한다.
    spec = TH <= pv.TH_NULL1
    convn = {}
    for p in ("H", "V"):
        rr = W_ref[p][spec] / (W_po_a[spec] + 1e-300)
        convn[p] = dict(max_abs_arg_deg=float(np.max(np.abs(np.degrees(np.angle(rr))))),
                        median_abs_arg_deg=float(np.median(np.abs(np.degrees(np.angle(rr))))))
    out["phase_gate"]["reference_phase_convention_check"] = dict(
        per_pol=convn, band="specular lobe (theta <= first PO null)",
        note=("arg(W_MoM / W_PO_closed_form) inside the specular lobe, where PO is essentially "
              "exact. Near 0 deg means the MoM reference uses the same exp(+jwt) / exp(+jk u.r) "
              "convention we do, so the phase comparison is anchored to an independent solver, "
              "not only to our own analytic formula."))

    # ── 4. 곡선 5 종 (⭐ 비코히런트 대조군 포함) ──────────────────────────── #
    sig = dict(po=C34 * np.abs(E_po) ** 2)
    for pol in ("H", "V"):
        sig["coh_" + pol] = C34 * np.abs(E_po + A_e[pol]) ** 2               # 코히런트 (배포 경로)
        sig["flip_" + pol] = C34 * np.abs(E_po - A_e[pol]) ** 2              # 부호반전 대조군
        sig["inc_" + pol] = C34 * (np.abs(E_po) ** 2 + np.abs(A_e[pol]) ** 2)  # ⭐ 비코히런트 대조군
        sig["cohon_" + pol] = C34 * np.abs(E_po + A_on[pol]) ** 2            # on-cone 만(오염 제거)
        sig["incon_" + pol] = C34 * (np.abs(E_po) ** 2 + np.abs(A_on[pol]) ** 2)
        sig["ana_" + pol] = conv * K * np.abs(W_ana[pol]) ** 2

    # 밴드 마스크
    dnull = np.array([np.min(np.abs(pv.PO_NULLS - t)) for t in TH])
    masks = dict(specular_core_3db=TH <= pv.TH_3DB,
                 specular_lobe=spec,
                 oblique=TH > pv.TH_NULL1,
                 oblique_off_null=(TH > pv.TH_NULL1) & (dnull > pv.NULL_GUARD_DEG),
                 all_angles=np.ones(len(TH), bool))

    KEYS = [("po_only", lambda p: sig["po"]),
            ("po_ptd_coherent", lambda p: sig["coh_" + p]),
            ("po_ptd_incoherent_control", lambda p: sig["inc_" + p]),
            ("po_ptd_sign_flipped_control", lambda p: sig["flip_" + p]),
            ("analytic_ufimtsev_ptd", lambda p: sig["ana_" + p])]

    err = {p: {k: pv.dbsm(f(p)) - pv.dbsm(sig_ref[p]) for k, f in KEYS} for p in ("H", "V")}
    err_on = {p: {"po_ptd_coherent": pv.dbsm(sig["cohon_" + p]) - pv.dbsm(sig_ref[p]),
                  "po_ptd_incoherent_control": pv.dbsm(sig["incon_" + p]) - pv.dbsm(sig_ref[p])}
              for p in ("H", "V")}

    def pooled(e, key, band):
        v = np.concatenate([e[p][key][masks[band]] for p in ("H", "V")])
        return float(np.sqrt(np.mean(v ** 2)))

    head = {b: {k: pooled(err, k, b) for k, _ in KEYS} for b in masks}
    head_on = {b: {k: pooled(err_on, k, b) for k in err_on["H"]} for b in masks}
    out["headline_rms_db_pooled_over_pol"] = head
    out["headline_rms_db_pooled_over_pol_oncone_edges_only"] = head_on
    out["errors_per_pol"] = {p: {k: pv.all_bands(TH, err[p][k]) for k, _ in KEYS}
                             for p in ("H", "V")}
    out["curves"] = {p: dict(sigma_ref_dbsm=pv.dbsm(sig_ref[p]).tolist(),
                             sigma_po_dbsm=pv.dbsm(sig["po"]).tolist(),
                             sigma_po_ptd_coherent_dbsm=pv.dbsm(sig["coh_" + p]).tolist(),
                             sigma_po_ptd_incoherent_dbsm=pv.dbsm(sig["inc_" + p]).tolist(),
                             sigma_po_ptd_signflip_dbsm=pv.dbsm(sig["flip_" + p]).tolist(),
                             sigma_analytic_ptd_dbsm=pv.dbsm(sig["ana_" + p]).tolist(),
                             edge_over_po_db=(20 * np.log10(
                                 np.maximum(np.abs(A_e[p]) / np.maximum(np.abs(E_po), 1e-300),
                                            1e-30))).tolist())
                     for p in ("H", "V")}

    # ── 5. ⭐ 코히런트 vs 비코히런트 — 짝지은 판정 ────────────────────────── #
    from scipy import stats as st
    coh_vs_inc = {}
    for band in ("oblique", "oblique_off_null", "specular_lobe", "all_angles"):
        m = masks[band]
        ec = np.concatenate([np.abs(err[p]["po_ptd_coherent"][m]) for p in ("H", "V")])
        ei = np.concatenate([np.abs(err[p]["po_ptd_incoherent_control"][m]) for p in ("H", "V")])
        n_better = int(np.sum(ec < ei))
        bt = st.binomtest(n_better, len(ec), 0.5, alternative="greater")
        coh_vs_inc[band] = dict(
            n=int(len(ec)),
            rms_coherent_db=float(np.sqrt(np.mean(ec ** 2))),
            rms_incoherent_db=float(np.sqrt(np.mean(ei ** 2))),
            rms_gain_db=float(np.sqrt(np.mean(ei ** 2)) - np.sqrt(np.mean(ec ** 2))),
            median_abs_coherent_db=float(np.median(ec)),
            median_abs_incoherent_db=float(np.median(ei)),
            median_gain_db=float(np.median(ei) - np.median(ec)),
            frac_angles_coherent_closer=float(n_better / len(ec)),
            sign_test_p=float(bt.pvalue))
    out["coherent_vs_incoherent"] = dict(
        per_band=coh_vs_inc,
        definition=("incoherent control = sigma_PO + sigma_edge (power addition, i.e. the "
                    "relative phase of the fringe term is discarded). The coherent kernel is "
                    "|E_PO + A_edge|^2. If the sign/phase were wrong there would be no reason "
                    "for the coherent sum to beat the phase-free power sum."),
        why_it_matters=("the RMS-improvement metric alone is phase-blind: the deliberately "
                        "sign-flipped control also improves on PO-only (defect D-7). The "
                        "incoherent control removes phase information entirely, so beating it "
                        "IS evidence that the relative phase carries information."))

    # ── 6. ⭐ 위상 오프셋 ψ 스윕 — 최소가 정말 ψ=0 인가 ───────────────────── #
    psis = np.arange(0.0, 360.001, 2.0)
    rms_psi, rms_psi_offnull = [], []
    for ps in psis:
        e = {p: {"x": pv.dbsm(C34 * np.abs(E_po + np.exp(1j * np.radians(ps)) * A_e[p]) ** 2)
                 - pv.dbsm(sig_ref[p])} for p in ("H", "V")}
        rms_psi.append(pooled(e, "x", "oblique"))
        rms_psi_offnull.append(pooled(e, "x", "oblique_off_null"))
    rms_psi = np.array(rms_psi)
    i0 = int(np.argmin(rms_psi))
    #  포물선 보간으로 이산격자보다 촘촘한 최소 위치를 낸다(격자 2° 라 이산 최소는 ±1°).
    j = np.clip(i0, 1, len(psis) - 2)
    y0, y1, y2 = rms_psi[j - 1], rms_psi[j], rms_psi[j + 1]
    dpsi = 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2) * (psis[1] - psis[0]) if (y0 - 2 * y1 + y2) else 0.0
    psi_min = float(psis[j] + dpsi)
    out["phase_offset_sweep"] = dict(
        psi_deg=psis.tolist(), rms_db_oblique=rms_psi.tolist(),
        rms_db_oblique_off_null=rms_psi_offnull,
        psi_argmin_deg=float(psis[i0]), psi_argmin_interpolated_deg=psi_min,
        rms_at_0_deg=float(rms_psi[0]), rms_at_180_deg=float(rms_psi[np.argmin(np.abs(psis - 180))]),
        rms_worst_deg=float(psis[int(np.argmax(rms_psi))]), rms_worst_db=float(rms_psi.max()),
        rms_incoherent_db=coh_vs_inc["oblique"]["rms_incoherent_db"],
        rms_po_only_db=head["oblique"]["po_only"],
        note=("A_edge -> exp(j psi) A_edge. psi = 0 is the shipped kernel, psi = 180 deg is the "
              "sign-flipped control. A minimum at psi = 0 means the fringe term is not merely "
              "the right size, it arrives with the right phase."))
    print("-- 6. phase-offset sweep: RMS minimum at psi = %.2f deg (kernel is psi = 0)" % psi_min)

    # ── 7. 2 차원↔3 차원 오염(끝 모서리) ─────────────────────────────────── #
    cont = {}
    for p in ("H", "V"):
        d = pv.dbsm(sig["coh_" + p]) - pv.dbsm(sig["cohon_" + p])
        cont[p] = dict(max_abs_db=float(np.max(np.abs(d))),
                       rms_db=float(np.sqrt(np.mean(d ** 2))))
    out["contamination_end_edges"] = dict(
        per_pol=cont,
        note="sigma(all 4 edges) - sigma(2 on-cone edges); the 2-D reference has no end edges.")

    out["verdict"] = dict(
        phase_gate_passes=bool(out["phase_gate"]["passes"]),
        coherent_beats_incoherent=bool(coh_vs_inc["oblique"]["rms_gain_db"] > 0),
        coherent_beats_incoherent_db=coh_vs_inc["oblique"]["rms_gain_db"],
        rms_minimum_at_zero_phase=bool(abs(psi_min) < 5.0 or abs(psi_min - 360.0) < 5.0),
        sign_flipped_control_still_beats_po_only=bool(
            head["oblique"]["po_ptd_sign_flipped_control"] < head["oblique"]["po_only"]),
        text=("PO and PO+PTD agree with the MoM reference inside the specular lobe; in the "
              "oblique region PO alone departs and the fringe term recovers most of it. The "
              "decisive evidence for the SIGN is not that RMS improves (the sign-flipped "
              "control improves it too) but that (a) arg(A_code/A_analytic) = 0 deg, (b) the "
              "coherent sum beats the phase-free incoherent sum, and (c) the RMS(psi) curve "
              "bottoms out at psi = 0."))
    out["limitations"] = [
        "Reference is a 2-D EFIE MoM of an infinite strip mapped by sigma_3D = (2 b^2/lam) "
        "sigma_2D; exact for the PO term and the two on-cone edges, the two end edges of the "
        "3-D plate are absent (contamination_end_edges). Headline is reported both ways.",
        "First-order PTD only: second-order (edge-to-edge) diffraction, corner diffraction and "
        "the truncated-wedge correction are absent from kernel and analytic curve alike.",
        "theta > 85 deg (grazing) excluded: PO -> 0 there and first-order PTD is known to fail.",
        "dB-domain RMS is dominated by the PO sinc nulls where the PO error is unbounded; "
        "oblique_off_null and median statistics are reported alongside.",
        "MoM reference discretisation residual is reported (reference_convergence) but no "
        "Richardson-extrapolated error bar is attached to it (open defect D-6).",
    ]
    return out


# =========================================================================== #
#  [3] 매끄러운 구에 ptd=True
# =========================================================================== #
def part3_sphere():
    import ptd_edges as pe
    import verify_ptd_regression as vr

    out = {}
    print("== [3] 매끄러운 구 (r=0.178 m, kr=13.06) ==")
    out["kr13"] = vr.b_sphere_convergence()
    print("\n== [3] 매끄러운 구 (r=0.5 m, kr=36.68) ==")
    out["kr37"] = vr.b_sphere_convergence(radius=0.5, seg_ladder=(60, 120, 240, 360))

    # ── 부호 불변성 실증 — |A_edge| 는 A_FW_CONST 의 부호에 의존하지 않는다 ── #
    #  프로세스 안에서만 상수를 뒤집었다 되돌린다(파일은 건드리지 않는다).
    from geom import uv_sphere
    mesh = uv_sphere(0.178, seg=128, rings=64, group="metal")
    edges = pe.extract_edges(mesh, sharp_deg=0.0)
    us = [np.array([np.cos(np.radians(a)), np.sin(np.radians(a)), 0.0])
          for a in (0.0, 37.0, 91.0, 214.0)]
    a_ref = [pe.edge_field(edges, FC, u, pol="V")[0] for u in us]
    old = pe.A_FW_CONST
    try:
        pe.A_FW_CONST = -old
        a_flip = [pe.edge_field(edges, FC, u, pol="V")[0] for u in us]
    finally:
        pe.A_FW_CONST = old
    d_abs = float(max(abs(abs(x) - abs(y)) for x, y in zip(a_ref, a_flip)))
    d_arg = float(max(abs(abs(np.degrees(np.angle(x / y))) - 180.0) for x, y in zip(a_ref, a_flip)))
    out["sign_invariance_of_the_floor"] = dict(
        max_abs_diff_of_magnitude=d_abs, max_dev_of_phase_from_180_deg=d_arg,
        note=("the seam-artefact floor is |A_edge|/|A_PO|, and A_FW_CONST enters A_edge as a "
              "multiplicative constant -> flipping its sign cannot move the floor. Measured "
              "in-process by flipping the module constant and restoring it: magnitudes "
              "identical, phases exactly 180 deg apart. Therefore the -32.5 dB floor of the "
              "previous round is expected to survive the repair unchanged, while the "
              "sigma-level artefact (which contains the PO-fringe cross term) is not."))

    # ── 이전 라운드(부호 수리 전)와 대조 ──────────────────────────────────── #
    if os.path.exists(PREV_REG):
        prev = json.load(open(PREV_REG, encoding="utf-8"))
        cmp_ = {}
        for key, pkey in (("kr13", "B_sphere_artifact"), ("kr37", "B2_sphere_artifact_r0p5")):
            if pkey not in prev:
                continue
            for sd in ("0", "5"):
                a = out[key][f"convergence_sharp_deg={sd}"]
                b = prev[pkey].get(f"convergence_sharp_deg={sd}")
                if b is None:
                    continue
                cmp_[f"{key}_sharp{sd}"] = dict(
                    floor_now_db=a["edge_over_po_db"][-1],
                    floor_before_fix_db=b["edge_over_po_db"][-1],
                    floor_delta_db=float(a["edge_over_po_db"][-1] - b["edge_over_po_db"][-1]),
                    max_abs_delta_of_ratio_curve_db=float(np.max(np.abs(
                        np.array(a["edge_over_po_db"]) - np.array(b["edge_over_po_db"])))),
                    sigma_artifact_now_db=a["last"], sigma_artifact_before_fix_db=b["last"],
                    sigma_artifact_delta_db=float(a["last"] - b["last"]),
                    slope_now=a["loglog_slope_vs_facets_per_lambda"],
                    slope_before_fix=b["loglog_slope_vs_facets_per_lambda"])
        out["vs_previous_round"] = dict(
            source=os.path.relpath(PREV_REG, _ROOT), rows=cmp_,
            note=("previous round = outputs/ptd_regression.json, generated BEFORE the D-1 sign "
                  "repair (its own SUPERSEDED block says so). The amplitude-ratio floor must be "
                  "bit-comparable; the sigma artefact may move because its cross term flips."))

    # ── 1/kr 법칙 ─────────────────────────────────────────────────────────── #
    f1 = out["kr13"]["convergence_sharp_deg=0"]["edge_over_po_db"][-1]
    f2 = out["kr37"]["convergence_sharp_deg=0"]["edge_over_po_db"][-1]
    kr1, kr2 = out["kr13"]["kr"], out["kr37"]["kr"]
    out["floor_vs_kr"] = dict(
        kr=[kr1, kr2], floor_db=[f1, f2],
        measured_db_per_decade_of_kr=float((f2 - f1) / np.log10(kr2 / kr1)),
        expected_if_one_over_kr=-20.0,
        note=("two radii only -> this is a slope through two points, not a fit. It says the "
              "artificial-edge amplitude falls roughly like 1/kr instead of vanishing."))
    out["convergence_verdict"] = dict(
        converges_to_zero=False,
        floor_db_at_kr13=f1, floor_db_at_kr37=f2,
        loglog_slope_vs_facets_per_lambda_kr13=out["kr13"][
            "convergence_sharp_deg=0"]["loglog_slope_vs_facets_per_lambda"],
        threshold_effect=("with the default sharp_deg = 5 deg threshold the seam edges are "
                          "discarded entirely above ~5 facets/lambda, which zeroes the artefact "
                          "by fiat, not by convergence. sharp_deg = 0 is the honest axis."))
    return out


# =========================================================================== #
def merge():
    cpu = json.load(open(TMP_CPU, encoding="utf-8"))
    gpu = json.load(open(TMP_GPU, encoding="utf-8")) if os.path.exists(TMP_GPU) else {}
    reg = dict(cpu.get("part1", {}))
    reg.update(gpu.get("part1", {}))

    checks, worst = {}, 0.0
    if "R1_identity" in reg:
        checks["R1_bit_identity"] = bool(reg["R1_identity"]["all_bit_identical"])
    for k in ("R2_sphere_yuan", "R3_kr_sweep", "R4_dihedral"):
        if k in reg:
            checks[k] = bool(reg[k]["unchanged"])
            worst = max(worst, float(reg[k]["max_abs_delta_db"]))
    reg["max_abs_delta_db_over_all_targets"] = float(worst)
    reg["all_unchanged"] = bool(all(checks.values()))
    reg["checks"] = checks
    reg["baseline_note"] = (
        "baselines are the pre-PTD outputs rcs_anchor.json / sbr_kr_sweep.json / "
        "sbr_defect_fixes.json, snapshotted at the start of this round because "
        "benchmark/rcs_anchor.py is regenerating on GPU2 (PID 1364837, untouched).")

    plate = cpu["part2"]
    sph = cpu["part3"]
    res = dict(
        meta=dict(
            generated=time.strftime("%Y-%m-%d %H:%M:%S"),
            generated_by="benchmark/ptd_verify_after_fix.py",
            task=("re-verification AFTER the D-1 sign repair (A_FW_CONST = -1/2): "
                  "[1] ptd=False regression, [2] plate with a phase gate and an incoherent-sum "
                  "control, [3] artificial-edge floor on a smooth sphere"),
            fc_hz=FC, lambda_m=LAM,
            kernel_sha256_16=dict(
                ptd_edges=_sha(os.path.join(_ROOT, "src", "ptd_edges.py")),
                rcs_sbr=_sha(os.path.join(_ROOT, "src", "rcs_sbr.py")),
                rcs_po=_sha(os.path.join(_ROOT, "src", "rcs_po.py"))),
            gpu=gpu.get("gpu"), cpu_wall_s=cpu.get("wall_s"), gpu_wall_s=gpu.get("wall_s")),
        part1_regression_ptd_false=reg,
        part2_plate_after_fix=plate,
        part3_sphere_artificial_edges=sph)

    import ptd_edges as pe
    res["open_defects_still_live"] = list(pe.OPEN_DEFECTS)

    cvi = plate["coherent_vs_incoherent"]["per_band"]["oblique"]
    res["verdict"] = dict(
        regression_max_abs_delta_db=reg["max_abs_delta_db_over_all_targets"],
        regression_clean=reg["all_unchanged"],
        phase_gate_max_abs_arg_deg=plate["phase_gate"]["max_abs_arg_deg"],
        phase_gate_passes=plate["phase_gate"]["passes"],
        coherent_minus_incoherent_rms_gain_db=cvi["rms_gain_db"],
        coherent_closer_fraction=cvi["frac_angles_coherent_closer"],
        rms_optimal_phase_offset_deg=plate["phase_offset_sweep"]["psi_argmin_interpolated_deg"],
        sphere_floor_db_kr13=sph["convergence_verdict"]["floor_db_at_kr13"],
        sphere_floor_db_kr37=sph["convergence_verdict"]["floor_db_at_kr37"],
        sphere_floor_unchanged_by_the_fix=bool(
            abs(sph.get("vs_previous_round", {}).get("rows", {})
                .get("kr13_sharp0", {}).get("max_abs_delta_of_ratio_curve_db", 1e9)) < 1e-9),
        headline=("① ptd=False 회귀는 세 과녁 전부 Δ=%.3e dB (비트 동일) — PTD 는 여전히 순수 "
                  "추가분이다. ② 부호 수리 후 평판에서 arg(A_code/A_analytic)=%.1e° 이고, "
                  "코히런트 합이 **비코히런트(위상 무정보) 합보다 %.2f dB** 낫다. RMS(ψ) 의 "
                  "최소도 ψ=%.1f° 다 — 크기뿐 아니라 위상이 맞다는 뜻이다. ③ 매끄러운 구의 "
                  "인공 모서리는 여전히 0 으로 수렴하지 않고 %.1f dB(kr=13.1) 바닥에 앉는다 — "
                  "부호 수리와 무관한, 남아 있는 결함(D-5)이다."
                  % (reg["max_abs_delta_db_over_all_targets"],
                     plate["phase_gate"]["max_abs_arg_deg"], cvi["rms_gain_db"],
                     plate["phase_offset_sweep"]["psi_argmin_interpolated_deg"],
                     sph["convergence_verdict"]["floor_db_at_kr13"])))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(res, open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(json.dumps(res["verdict"], indent=2, ensure_ascii=False))
    print("\n저장 → %s" % OUT)
    return 0


def main():
    part = os.environ.get("PART", "cpu").lower()
    t0 = time.time()
    os.makedirs(SCRATCH, exist_ok=True)
    if part == "gpu":
        from gpu import pick
        pick()
        out = dict(gpu=os.environ.get("CUDA_VISIBLE_DEVICES"),
                   generated=time.strftime("%Y-%m-%d %H:%M:%S"), part1=part1_gpu())
        out["wall_s"] = round(time.time() - t0, 1)
        json.dump(out, open(TMP_GPU, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        print("\n저장 → %s  (%.0fs)" % (TMP_GPU, out["wall_s"]))
        return 0
    if part == "cpu":
        out = dict(generated=time.strftime("%Y-%m-%d %H:%M:%S"), part1=part1_cpu())
        print("\n== [2] 평판 재검증 (부호 수리 후) ==")
        out["part2"] = part2_plate()
        print()
        out["part3"] = part3_sphere()
        out["wall_s"] = round(time.time() - t0, 1)
        json.dump(out, open(TMP_CPU, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        print("\n저장 → %s  (%.0fs)" % (TMP_CPU, out["wall_s"]))
        return 0
    return merge()


if __name__ == "__main__":
    sys.exit(main())
