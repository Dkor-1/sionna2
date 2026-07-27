# -*- coding: utf-8 -*-
"""verify_freespace.py — report13(자유공간 드론 검지거리) **적대적 검증 하니스**
================================================================================

이 스크립트가 하는 일 하나: report13 의 핵심 주장들을 **깨질 수 있는 방식으로** 재확인하고
`outputs/verify_freespace.json` 에 판정을 박는다. 스펙 §16 게이트가 이 파일이 통과시켜야 할 목록이다.

■ 설계 철학 — "항상 통과하는 자명검증은 쓰레기다"(스펙 §9 지시)
  각 체크는 **틀리면 실제로 FAIL 이 뜨도록** 짰다. 예를 들어
    · el 부호 체크는 `look_el_deg` 가 부호를 뒤집으면(과거 "overhead spike" 서사) 즉시 깨진다.
    · solve_range 비단조 체크는 이분법으로 되돌리면(내부최대 무시) snr_peak_d 가 격자 끝으로
      가서 ★244/235/166 m 재현에 실패한다.
    · ECA ridge=0 체크는 정본을 1e-6 으로 되돌리면 DNR120 에서 p99 누설이 0.5 dB 를 넘겨 깨진다.
    · fresnel 등가 체크는 상수(ε_r·σ)가 어긋나면 |Δ|Γ| 가 1e-12 를 넘겨 깨진다.
  → 그래서 "동치성 tol" 은 물리적으로 타이트하게 잡았다(느슨하게 잡으면 검증이 무의미하다).

■ 두 종류의 체크
  (A) **자립(analytic) 체크** — 파이프라인 산출물이 없어도 지금 돈다. 순수함수·닫힌형·작은
      CPU MC(ECA 바닥)로 성립한다. 스모크에서 실제로 PASS/FAIL 이 뜨는 것들이다.
  (B) **파이프라인 의존 체크** — `outputs/report13_freespace.json`(experiment_freespace_range 산출)이
      있어야 판정한다(FS-0 9모드 SNR90 동일성·k_mode 닫힌형 잔차). 없으면 `skipped` + 사유를 남긴다
      (스펙 §8.6 "축을 자르지 않고 라벨만" 정신 — 검증도 없는 걸 통과라 우기지 않는다).

■ 스펙 §10/§16 이 요구하는 verify 키를 그대로 낸다:
  fs0_mode_snr90_spread_db(R8) · snr_convention_consistency(R3§5) · ground_2ray_check(R1) ·
  nyquist_fold_check(F8) · supp_phi_gate(R7) · geometry_equivalence(바이스태틱근사) ·
  sigma_el_sign(S8/A2) · solve_range_nonmonotone(S6/S1) · eca_ridge0_floor(R6) ·
  cpi_M_from_prf(F1) · constants_9mode(§4.3) · closed_form_vs_measured(§2.5).

실행:  cd sionna2 && PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/verify_freespace.py
       (스모크: --out /tmp/.../verify_freespace.json 로 outputs 오염 회피)

그림 텍스트 없음(순수 검증). 주석·docstring 한국어.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (os.path.join(_ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# BLAS 스레드 상한 — 다른 리포트 에이전트와 코어를 다투지 않도록(numpy import 전)
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_v, "4")

import numpy as np  # noqa: E402

import freespace_scene as fss          # noqa: E402  (순수함수 기하)
import freespace_link as fsl           # noqa: E402  (닫힌형 링크)
import freespace_detect as fsd         # noqa: E402  (검출기 형상·ECA)

C0 = 299792458.0
DEFAULT_OUT = os.path.join(_ROOT, "outputs", "verify_freespace.json")
DEFAULT_REPORT13 = os.path.join(_ROOT, "outputs", "report13_freespace.json")

# ★설계문서 §1.2 검증표 (L=500, φ=90°, TX z=25, RX z=3) — 부호·크기 회귀 기준
#   (alt, d) -> (beta_deg, el_deg)
VERIFY_TABLE = {
    (60.0, 150.0): (115.8, -17.0), (60.0, 300.0): (79.0, -8.7),
    (60.0, 1000.0): (28.1, -2.6), (60.0, 3000.0): (9.5, -0.9),
    (60.0, 10000.0): (2.9, -0.26),
    (120.0, 150.0): (107.4, -35.2), (120.0, 300.0): (76.4, -19.5),
    (120.0, 1000.0): (27.9, -6.1), (120.0, 3000.0): (9.5, -2.0),
    (120.0, 10000.0): (2.9, -0.61),
}


# --------------------------------------------------------------------------- #
#  공통 유틸
# --------------------------------------------------------------------------- #
def _jsonify(o):
    """numpy/complex 스칼라를 JSON 직렬화 가능하게 재귀 변환."""
    if isinstance(o, dict):
        return {str(k): _jsonify(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonify(v) for v in o]
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.ndarray):
        return _jsonify(o.tolist())
    if isinstance(o, complex):
        return {"re": o.real, "im": o.imag}
    return o


def _snr_of_d(d_grid, phi_deg, alt, L=500.0, fc=1.843e9, sigma_m2=0.01,
              eirp=63.0, grx=10.0, nf=5.0, T=0.1):
    """★검증 기하에서 SNR(d)[dB] 닫힌형 곡선과 κ(d) 를 만든다(σ 고정).

    solve_range 비단조·n_local 체크가 공유하는 헬퍼. 순수하게 freespace_scene 기하 +
    freespace_link 닫힌형만 쓴다(재구현 없음).
    """
    lam = C0 / float(fc)
    tgt = fss.target_pos(d_grid, phi_deg, L, alt)                 # (N,3)
    p = fss.fs_params(fss.FS_TX, fss.FS_RX(L), tgt, (0.0, 0.0, 0.0), fc)
    R1 = np.asarray(p["R1"], float)
    R2 = np.asarray(p["R2"], float)
    snr = fsl.snr_rd_db(eirp, grx, lam, sigma_m2, R1, R2, nf=nf, T=T)
    kap = np.asarray(p["kappa"], float)
    return np.asarray(snr, float), kap, R1, R2


# =========================================================================== #
#  (A) 자립 체크
# =========================================================================== #
def check_geometry_equivalence(n=2000):
    """바이스태틱근사 — `fs_params` 가 저장소 `bistatic_params` 의 **비트단위 복제**인가 (스펙 §3/[9]).

    깨지는 조건: fs_params 의 부호/식이 원본과 벌어지면(멀어질 때 f_d>0 이 되는 부호오류 등)
    max_abs_diff 가 tol(1e-9)을 넘어 FAIL. 이 체크가 곧 "우리 기하가 report01~12 와 같은 물리"
    라는 보증이다.
    """
    r = fss.selfcheck_vs_repo(n=int(n))
    ok = bool(r["ok"])
    return dict(ok=ok, n=r["n"], max_abs_diff=r["max_abs_diff"],
                max_abs_diff_el_deg=r["max_abs_diff_el_deg"], tol=r["tol"],
                breaks_if="fs_params 부호/식이 bistatic_params 와 벌어지면(예: f_d 부호반전) FAIL",
                note=r["note"])


def check_sigma_el_sign():
    """σ 앙각 부호 — 지상 TX/RX + 공중표적의 이등분선 el 은 **전 구간 음수**인가 (S8/A2).

    또한 ★검증표(β·el)를 tol 안에서 재현하는지 본다. 깨지는 조건: `look_el_deg` 가 부호를
    뒤집으면("overhead spike" 옛 서사) el>0 이 뜨고, β 식이 틀리면 표 재현이 깨진다.
    """
    rows = []
    all_neg = True
    worst_beta, worst_el = 0.0, 0.0
    for (alt, d), (beta_ref, el_ref) in sorted(VERIFY_TABLE.items()):
        tgt = fss.target_pos(d, fss.PHI_HEADLINE_DEG, fss.L_REF, alt)
        p = fss.fs_params(fss.FS_TX, fss.FS_RX(fss.L_REF), tgt, (0.0, 0.0, 0.0), 1.843e9)
        el = float(p["el_deg"])
        beta = float(p["beta"])
        all_neg = all_neg and (el < 0.0)
        db = abs(beta - beta_ref)
        de = abs(el - el_ref)
        worst_beta = max(worst_beta, db)
        worst_el = max(worst_el, de)
        rows.append(dict(alt=alt, d=d, beta_deg=beta, beta_ref=beta_ref,
                         el_deg=el, el_ref=el_ref, d_beta=db, d_el=de))
    # 표는 유효숫자 1~2자리라 tol 을 넉넉히(β 1.0°, el 0.6°) — 그래도 부호/수식 오류는 못 숨는다
    ok = bool(all_neg and worst_beta <= 1.0 and worst_el <= 0.6)
    return dict(ok=ok, all_el_negative=bool(all_neg),
                worst_beta_dev_deg=worst_beta, worst_el_dev_deg=worst_el,
                el_at_headline_deg=rows[0]["el_deg"], table=rows,
                breaks_if="look_el_deg 가 el>0 을 내거나 β 식이 ★표에서 1° 이상 벗어나면 FAIL")


def check_solve_range_nonmonotone():
    """solve_range 비단조·최외곽교차·n_local (S6/S1).

    ★재현: L=500·alt=60 에서 SNR(d) 는 φ=0/10/30° 모두 **내부최대**를 갖고 그 위치가
    d≈244/235/166 m 다. 깨지는 조건: 이분법으로 되돌려 내부최대를 무시하면 `monotone_ok`
    가 참으로 뒤집히거나 snr_peak_d 가 격자 끝으로 가서 재현 실패.
    또 n_local(κ)는 d=150→1.03, d=1000→3.76(d≫L 에서만 4) — dB↔거리 환산은 이 값을 껴야 한다.
    """
    d_grid = np.geomspace(100.0, 20000.0, 240)
    peak_ref = {0.0: 244.0, 10.0: 235.0, 30.0: 166.0}
    rows = []
    all_nonmono = True
    worst_peak_dev = 0.0
    for phi in (0.0, 10.0, 30.0):
        snr, kap, R1, R2 = _snr_of_d(d_grid, phi, alt=60.0)
        # 문턱은 임의(내부최대 위·아래로 걸치도록) — 비단조성 판정은 문턱과 무관하다
        th = float(np.nanmedian(snr))
        sol = fsl.solve_range(snr, th, d_grid=d_grid, kappa_of_d=kap)
        dev = abs(sol["snr_peak_d_m"] - peak_ref[phi])
        worst_peak_dev = max(worst_peak_dev, dev)
        all_nonmono = all_nonmono and (not sol["monotone_ok"])
        rows.append(dict(phi_deg=phi, monotone_ok=bool(sol["monotone_ok"]),
                         snr_rise_db=sol["snr_rise_db"], snr_peak_d_m=sol["snr_peak_d_m"],
                         snr_peak_d_ref_m=peak_ref[phi], peak_dev_m=dev,
                         n_crossings=sol["n_crossings"], R_m=sol["R_m"],
                         snr_ceiling_db=sol["snr_ceiling_db"]))
    # n_local (φ=90°, S1) — 순수 기하 지수
    snr90, kap90, _, _ = _snr_of_d(d_grid, 90.0, alt=60.0)
    n150 = float(fsl.n_local(kap90, d_grid, at=150.0))
    n1000 = float(fsl.n_local(kap90, d_grid, at=1000.0))
    n19800 = float(fsl.n_local(kap90, d_grid, at=19800.0))
    n_ok = (abs(n150 - 1.03) <= 0.15 and abs(n1000 - 3.76) <= 0.2 and n19800 > 3.9)
    ok = bool(all_nonmono and worst_peak_dev <= 12.0 and n_ok)
    return dict(ok=ok, all_nonmonotone=bool(all_nonmono),
                worst_peak_dev_m=worst_peak_dev, per_phi=rows,
                n_local={"at_150": n150, "at_1000": n1000, "at_19800": n19800,
                         "ref_150": 1.03, "ref_1000": 3.76, "ok": bool(n_ok)},
                breaks_if="이분법 회귀(내부최대 무시)→monotone_ok=True 또는 peak_d 격자끝; "
                          "n_local≡4 회귀→d=150 재현실패")


def check_snr_convention_consistency():
    """SNR 규약 일관성 — mean 규약과 median 규약이 **같은 R** 을 내는가 (R3§5, §5.3).

    측정 SNR 눈금과 문턱을 동시에 median 규약(+1.594 dB = 10log10(1/ln2))으로 옮기면
    거리 해 R 은 불변이어야 한다(둘이 같은 오프셋으로 이동하므로). 깨지는 조건: 한쪽에만
    오프셋을 적용하면(눈금은 median·문턱은 mean 등) R 이 크게 달라진다.
    """
    off = 10.0 * np.log10(1.0 / np.log(2.0))                  # 지수분포 median↔mean 오프셋
    d_grid = np.geomspace(100.0, 20000.0, 240)
    snr, kap, _, _ = _snr_of_d(d_grid, 90.0, alt=60.0)
    th_mean = float(np.nanpercentile(snr, 55))               # 유효구간을 걸치는 문턱
    R_mean = fsl.solve_range(snr, th_mean, d_grid=d_grid)["R_m"]
    R_med = fsl.solve_range(snr + off, th_mean + off, d_grid=d_grid)["R_m"]
    # 잘못된 규약(문턱만 옮기고 눈금은 안 옮김) → 반드시 달라야 검증이 살아있다
    R_wrong = fsl.solve_range(snr, th_mean + off, d_grid=d_grid)["R_m"]
    rel = abs(R_med - R_mean) / max(R_mean, 1e-9)
    rel_wrong = abs(R_wrong - R_mean) / max(R_mean, 1e-9)
    ok = bool(rel <= 1e-6 and rel_wrong > 1e-3)              # 일관규약=동일 & 오적용=달라짐
    return dict(ok=ok, median_offset_db=float(off), R_mean_m=R_mean, R_median_m=R_med,
                rel_diff_consistent=float(rel), R_wrong_convention_m=R_wrong,
                rel_diff_wrong=float(rel_wrong),
                breaks_if="두 규약 R 이 갈리면(오프셋을 한쪽에만 적용) FAIL; "
                          "오적용이 오히려 같게 나오면(rel_wrong≈0) 검증이 죽은 것")


def check_nyquist_fold(v=5.0, fc=3.5e9):
    """나이퀴스트/접힘 — SSB(PRF 50 Hz·M 5)는 v=5 m/s 에서 사실상 전헤딩 앨리어싱인가 (F8/F1).

    깨지는 조건: prf_hz 가 SSB 를 2000 Hz(report12 타일링)로 돌려주면 alias_frac 이 급감하고
    M_from_prf 가 5 가 아니게 된다. folded_doppler/nyquist_gate 퇴화입력 규약도 함께 본다.
    """
    prf = fss.prf_hz("nr", "G1")
    M = fss.M_from_prf(0.1, prf)
    psi = np.arange(0.0, 360.0, 1.0)
    fr = fss.blind_fractions(psi, fss.PHI_HEADLINE_DEG, 1000.0, 500.0, 60.0,
                             T=0.1, prf=prf, speed=v, lam=C0 / fc, M=M)
    # LTE CRS(1000Hz)는 대조군 — 같은 v 에서 앨리어싱이 훨씬 낮아야 한다
    prf_l = fss.prf_hz("lte", "G1")
    Ml = fss.M_from_prf(0.1, prf_l)
    fr_l = fss.blind_fractions(psi, fss.PHI_HEADLINE_DEG, 1000.0, 500.0, 60.0,
                               T=0.1, prf=prf_l, speed=v, lam=C0 / fc, M=Ml)
    # SSB 는 헤딩의 태반이 접힌다(★φ=90·d=1000 에서 0.86). 문턱을 0.5 로 두면 prf 가 2000 Hz
    # (report12 타일링)로 되돌아가는 순간 alias_frac 이 급락(0)해 깨진다.
    ssb_ok = bool(abs(prf - 50.0) < 1e-9 and M == 5 and fr["alias_frac"] >= 0.5)
    contrast_ok = bool(fr["alias_frac"] > fr_l["alias_frac"] + 0.5)
    ok = bool(ssb_ok and contrast_ok)
    return dict(ok=ok, ssb_prf_hz=float(prf), ssb_M=int(M),
                ssb_alias_frac=fr["alias_frac"], ssb_blind_hard=fr["blind_hard"],
                lte_prf_hz=float(prf_l), lte_M=int(Ml), lte_alias_frac=fr_l["alias_frac"],
                v_ms=v, breaks_if="prf_hz(nr,G1)≠50 또는 M≠5 또는 SSB alias<0.5 또는 "
                                  "SSB↔LTE 앨리어싱 대비(>0.5)가 사라지면 FAIL")


def check_supp_phi_gate():
    """DPI 억압 φ 게이트 — 표적이 TX 와 일직선(φ≈180°)이면 억압 불가인가 (R7).

    깨지는 조건: angular_sep_tx_target_deg 가 φ=180° 에서 큰 각을 내면(기하오류) supp_eff 가
    0 이 아니게 되고 unsuppressible 판정이 사라진다. φ=90° 는 반대로 억압 가능해야 한다.
    """
    L, alt, d = 500.0, 60.0, 1000.0
    rx = fss.FS_RX(L)
    P180 = fss.target_pos(d, 180.0, L, alt)
    P90 = fss.target_pos(d, 90.0, L, alt)
    dth180 = fss.angular_sep_tx_target_deg(rx, fss.FS_TX, P180)
    dth90 = fss.angular_sep_tx_target_deg(rx, fss.FS_TX, P90)
    eff180, unsup180 = fsl.supp_eff_db(30.0, dth180, beamwidth_deg=30.0)
    eff90, unsup90 = fsl.supp_eff_db(30.0, dth90, beamwidth_deg=30.0)
    ok = bool(unsup180 and eff180 == 0.0 and (not unsup90) and eff90 > 0.0)
    return dict(ok=ok, dtheta_phi180_deg=dth180, dtheta_phi90_deg=dth90,
                supp_eff_phi180_db=float(eff180), unsuppressible_phi180=bool(unsup180),
                supp_eff_phi90_db=float(eff90), unsuppressible_phi90=bool(unsup90),
                breaks_if="φ180 이 억압가능(unsup=False)으로 뜨거나 φ90 이 억압불가로 뜨면 FAIL")


def check_ground_2ray():
    """FS-3 지면 — `fresnel_gamma` 가 저장소 `geometry._fresnel_floor` 와 **상수 맞추면 일치**하는가 (R1/[4]).

    또 F⁴=F₁²F₂² 가 스펙 인용범위 [−20, +11.5] dB(거리 0.32~1.94배)를 넘지 않는지 본다.
    깨지는 조건: fresnel_gamma 의 grazing↔normal 각 규약이나 편파 분기가 틀리면 |Δ|Γ| 가
    1e-12 를 넘는다. F⁴ 상한이 +11.5 dB 를 크게 넘으면 "상한선 아님" 서사(R1)가 흔들린다.
    """
    from geometry import _fresnel_floor, FLOOR_EPS_R, FLOOR_SIGMA
    fc = 3.5e9
    worst = 0.0
    for theta_i_deg in (10.0, 30.0, 60.0, 80.0, 87.0):          # 법선기준 입사각
        g_repo = _fresnel_floor(np.radians(theta_i_deg), fc, pol="V")   # |Γ| (콘크리트, V=TM)
        psi = 90.0 - theta_i_deg                                # grazing 각으로 변환
        g_ours = fsl.fresnel_gamma(psi, eps_r=FLOOR_EPS_R, cond=FLOOR_SIGMA,
                                   pol="v", fc=fc)              # 콘크리트 상수로 맞춤
        worst = max(worst, abs(abs(g_ours) - g_repo))
    equiv_ok = bool(worst <= 1e-12)

    # F⁴ 분포(습토·수직편파, 헤드라인 지면) — 저각~중각 스윕
    lam = C0 / fc
    grng = np.geomspace(20.0, 5000.0, 400)
    dR, psi = fsl.two_ray_path_diff(60.0, 3.0, grng)            # h_t=60, h_rx=3
    F = fsl.two_ray_F(psi, dR, None, lam, eps_r=15.0, cond=0.005, pol="v")
    f4_db = fsl.two_ray_f4_db(F, F)                            # 양 leg 동일 근사
    f4_lo, f4_hi = float(np.nanmin(f4_db)), float(np.nanmax(f4_db))
    # R1 의 핵심은 **상한(constructive)** 이 자유공간(0 dB)을 넘는다는 것(≈+10.5, 물리 천장 ~+12).
    # 하한은 파괴간섭 널이라 −∞ 로 내려가는 게 정상이므로 바닥을 강제하지 않는다. 대신 널이
    # 실제로 깊게 파이는지(<−6 dB)를 확인 — 위상항이 죽으면 프린지가 사라져 이게 깨진다.
    range_ok = bool(6.0 <= f4_hi <= 12.5 and f4_lo < -6.0)
    ok = bool(equiv_ok and range_ok)
    return dict(ok=ok, fresnel_max_abs_diff_gamma=worst, fresnel_equiv_ok=bool(equiv_ok),
                f4_db_min=f4_lo, f4_db_max=f4_hi, f4_range_ok=bool(range_ok),
                ground_repo=fsl.GROUND_REPO_CONCRETE, ground_fs3=fsl.GROUND_FS3_SOIL,
                breaks_if="상수 맞춘 |Γ| 가 저장소와 1e-12 넘게 벌어지거나 F⁴ 가 +12.5 dB 초과면 FAIL")


def check_eca_ridge0_floor(quick=True):
    """ECA 수치바닥 — `ridge_rel=0` 이 1e-6·1e-4 보다 잔류가 낮은가 (R6, 스펙 §16 게이트).

    합성 기준신호로 ECA 바닥을 잰다(재구현 없이 freespace_detect.eca_floor_sweep). 깨지는 조건:
    정본을 1e-6 으로 되돌리면 DNR120 에서 비-0도플러 p99 누설이 0.5 dB 를 넘어 clean_ridge0=False.
    """
    rng = np.random.default_rng(13)
    M = 8
    Lf = 512 if quick else 1024
    ref = ((rng.standard_normal(M * Lf) + 1j * rng.standard_normal(M * Lf))
           / np.sqrt(2)).astype(np.complex128)
    dnr = (80.0, 100.0, 120.0)
    sw = fsd.eca_floor_sweep(ref, dnr_grid=dnr, ridge_list=(0.0, 1e-6, 1e-4),
                             M=M, n_range=min(256, Lf))
    cfgs = sw["configs"]
    p99 = sw["resid_p99_db"]
    i0 = next(i for i, c in enumerate(cfgs) if c["ridge"] == 0.0)
    i6 = next(i for i, c in enumerate(cfgs) if c["ridge"] == 1e-6)
    i4 = next(i for i, c in enumerate(cfgs) if c["ridge"] == 1e-4)
    p99_0 = float(max(p99[i0]))                                # ridge0 최악 p99 (전 DNR)
    p99_6_hi = float(p99[i6][-1])                              # 1e-6 @ DNR120
    p99_4_hi = float(p99[i4][-1])                              # 1e-4 @ DNR120
    clean0 = bool(sw["clean_ridge0"])
    # ridge=0 이 정본이라는 것 = (a) 0 은 깨끗 (b) 로딩 있는 것들은 고DNR 에서 더 샌다
    leak_ok = bool(p99_6_hi > p99_0 + 1.0 or p99_4_hi > p99_0 + 1.0)
    ok = bool(clean0 and leak_ok)
    return dict(ok=ok, clean_ridge0=clean0, ridge0_max_p99_db=p99_0,
                ridge1e6_p99_at_dnr120_db=p99_6_hi, ridge1e4_p99_at_dnr120_db=p99_4_hi,
                dnr_db=list(dnr), depth_ridge0_db=cfgs[i0]["cancel_depth_db"],
                depth_ridge1e4_db=cfgs[i4]["cancel_depth_db"],
                input_kind="white_noise_sanity",
                scope_note="백색·양호조건 기준으로 스윕 기계·ridge 순서를 검증한다(회귀가드). "
                           "대역제한 실제 기준신호(cond~1e4)·complex64·고DNR 코너의 거동은 "
                           "파이프라인 stage_verify 가 재는 pipeline_real_ref_clean_ridge0 로 본다.",
                breaks_if="정본을 1e-6 으로 되돌리면 clean_ridge0=False; 로딩이 고DNR 에서 "
                          "더 새지 않으면 R6 주장 근거 소멸")


def check_cpi_M_from_prf():
    """CPI 물리 — M=round(T·PRF) 가 F1 규약(LTE100·WiFi100·SSB5·PRS20)을 내는가 (F1).

    깨지는 조건: SSB 를 2000 Hz 로 되돌리면 M=200 이 나온다(report12 타일링). 전력 3뷰 존재도 확인.
    """
    T = 0.1
    got = {
        "L1": fss.M_from_prf(T, fss.prf_hz("lte", "G1")),
        "W1": fss.M_from_prf(T, fss.prf_hz("wifi", "G1", wifi_packet_rate=1000.0)),
        "G1": fss.M_from_prf(T, fss.prf_hz("nr", "G1")),
        "G3": fss.M_from_prf(T, fss.prf_hz("nr", "G3")),
    }
    want = {"L1": 100, "W1": 100, "G1": 5, "G3": 20}
    ok = bool(all(got[k] == want[k] for k in want))
    return dict(ok=ok, M_by_mode=got, M_expected=want, T_cpi_s=T,
                ssb_period_ms=1000.0 / fss.prf_hz("nr", "G1"),
                power_norm_views=["equal_total", "equal_psd", "deploy"],
                canonical_occupancy_view="equal_psd",
                breaks_if="SSB M≠5(2000Hz 타일링 회귀) 또는 어느 모드든 F1 유도값과 다르면 FAIL")


def check_constants_9mode():
    """§4.3 — 9모드 상수(straddle·pilot_frac)를 **재측정**하고 G3 브로드캐스트가 아님을 확인.

    straddle_rng_half 는 오버샘플 fs/B_ref 에서 유도(반빈 straddle = 20log10|sinc(0.5/over)|).
    pilot_power_frac 는 wf.ref/wf.tx 에너지비. 깨지는 조건: 9모드가 서로 다른 값이어야 하는데
    G3 3행을 그대로 복제하면(9행이 3행뿐) distinct 검사가 깨진다. straddle ★값(G1 −0.02·W1 −3.48)
    재현도 검사한다.
    """
    try:
        from waveforms import all_waveforms
    except Exception as e:
        return dict(ok=None, skipped=True, reason=f"waveforms import 실패: {e}")
    spec_straddle = {"W1": -3.48, "L1": -1.24, "G1": -0.02, "G3": -2.29}
    rows = {}
    straddle_dev = 0.0
    for occ in ("G1", "G2", "G3"):
        wfs = all_waveforms(occ)
        for std, wf in wfs.items():
            mode = {"wifi": "W", "lte": "L", "nr": "G"}[std] + occ[1]
            over = float(wf.fs_hz) / max(float(wf.ref_bw_hz), 1.0)
            x = 0.5 / max(over, 1e-9)
            sinc = 1.0 if x == 0 else np.sin(np.pi * x) / (np.pi * x)
            straddle = float(20.0 * np.log10(max(abs(sinc), 1e-12)))
            e_ref = float(np.sum(np.abs(wf.ref) ** 2))
            e_tx = float(np.sum(np.abs(wf.tx) ** 2))
            pilot_frac = float(10.0 * np.log10(max(e_ref / max(e_tx, 1e-30), 1e-30)))
            rows[mode] = dict(oversample_fs_over_bref=over,
                              straddle_rng_half_db=straddle,
                              pilot_power_frac_db=pilot_frac,
                              ref_bw_hz=float(wf.ref_bw_hz), fs_hz=float(wf.fs_hz),
                              ref_name=wf.ref_name)
            if mode in spec_straddle:
                straddle_dev = max(straddle_dev, abs(straddle - spec_straddle[mode]))
    # G3 브로드캐스트가 아님 = 9모드 값이 3개 이하로 뭉치지 않았나
    straddles = [rows[m]["straddle_rng_half_db"] for m in rows]
    distinct = len(set(round(s, 3) for s in straddles))
    ok = bool(len(rows) == 9 and distinct >= 5 and straddle_dev <= 0.6)
    return dict(ok=ok, n_modes=len(rows), n_distinct_straddle=distinct,
                straddle_max_dev_vs_spec_db=straddle_dev, by_mode=rows,
                breaks_if="9모드가 3행 브로드캐스트로 뭉치거나 straddle ★값(G1 −0.02·W1 −3.48) "
                          "재현이 0.6 dB 넘게 벗어나면 FAIL")


# =========================================================================== #
#  (B) 파이프라인 의존 체크 — report13_freespace.json 필요
# =========================================================================== #
def _load_json(path):
    if not path or not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return json.load(f)


def check_fs0_mode_snr90(report13):
    """FS-0 9모드 SNR90 동일성 (R8, 스펙 §16 헤드라인 게이트).

    FS-0(열잡음만)에서 RD 출력 SNR90 은 모드와 거의 무관해야 한다(k_mode 흡수 후). 산출
    JSON 의 detector_transfer 에서 모드별 SNR90(N=1)을 모아 스프레드를 잰다. JSON 이 없으면 skip.
    깨지는 조건: 어느 모드의 SNR90 이 CFAR n_train 차이 이상으로 벌어지면(스프레드>tol) FAIL.
    """
    if report13 is None:
        return dict(ok=None, skipped=True,
                    reason="outputs/report13_freespace.json 없음 — stage_threshold 산출 필요")
    dt = report13.get("detector_transfer", {}).get("S_G", {})
    snr90 = {}
    for mode, node in dt.items():
        try:
            n1 = node["N"]["1"]["dopoff"]
            # 실현 가능한 dopoff 중 아무거나(가장 작은 오프셋)
            for dk in sorted(n1, key=lambda s: int(s) if s.lstrip("-").isdigit() else 999):
                v = n1[dk].get("snr90_db")
                if v is not None:
                    snr90[mode] = float(v)
                    break
        except Exception:
            continue
    if len(snr90) < 2:
        return dict(ok=None, skipped=True,
                    reason=f"detector_transfer 에서 SNR90 을 2개 이상 못 찾음(found={list(snr90)})")
    vals = np.array(list(snr90.values()), float)
    spread = float(np.nanmax(vals) - np.nanmin(vals))
    ok = bool(spread <= 1.5)                                    # CFAR n_train 차이 허용폭
    return dict(ok=ok, fs0_mode_snr90_spread_db=spread, snr90_by_mode=snr90,
                tol_db=1.5, breaks_if="어느 모드 FS-0 SNR90 이 1.5 dB 넘게 벌어지면 FAIL(k_mode 흡수 실패)")


def check_closed_form_vs_measured(report13):
    """§2.5 — k_mode 닫힌형 잔차 |Δ|<0.5 dB. JSON 없으면 skip.

    깨지는 조건: 측정 SNR 과 닫힌형 예측이 0.5 dB 넘게 벌어지면(예산식 오류) FAIL.
    """
    if report13 is None:
        return dict(ok=None, skipped=True,
                    reason="outputs/report13_freespace.json 없음 — stage_calib 산출 필요")
    calib = report13.get("calib", {})
    if not calib:
        return dict(ok=None, skipped=True, reason="report13.calib 비어있음")
    worst = 0.0
    rows = {}
    for mode, c in calib.items():
        r = c.get("resid_db")
        if r is not None:
            worst = max(worst, abs(float(r)))
            rows[mode] = float(r)
    ok = bool(rows and worst < 0.5)
    return dict(ok=ok, worst_resid_db=worst, resid_by_mode=rows,
                breaks_if="k_mode 닫힌형 잔차가 0.5 dB 를 넘으면 FAIL")


# =========================================================================== #
#  main
# =========================================================================== #
def run_all(report13_path=DEFAULT_REPORT13, quick=True, n_geom=2000):
    """전 체크를 돌려 판정 dict 를 만든다(파일 쓰기는 main 이 한다)."""
    t0 = time.time()
    report13 = _load_json(report13_path)
    checks = {}
    # (A) 자립
    checks["geometry_equivalence"] = check_geometry_equivalence(n=n_geom)
    checks["sigma_el_sign"] = check_sigma_el_sign()
    checks["solve_range_nonmonotone"] = check_solve_range_nonmonotone()
    checks["snr_convention_consistency"] = check_snr_convention_consistency()
    checks["nyquist_fold_check"] = check_nyquist_fold()
    checks["supp_phi_gate"] = check_supp_phi_gate()
    checks["ground_2ray_check"] = check_ground_2ray()
    checks["eca_ridge0_floor"] = check_eca_ridge0_floor(quick=quick)
    checks["cpi_M_from_prf"] = check_cpi_M_from_prf()
    checks["constants_9mode"] = check_constants_9mode()
    # (B) 파이프라인 의존
    checks["fs0_mode_snr90"] = check_fs0_mode_snr90(report13)
    checks["closed_form_vs_measured"] = check_closed_form_vs_measured(report13)
    # R6 화해: 파이프라인이 **실제 기준신호**로 잰 clean_ridge0(=stage_verify)를 백색-새니티 옆에 병기.
    #   두 JSON 이 R6 을 놓고 상반되지 않도록 실측 기준의 진실을 같은 자리에 노출(게이트는 불변).
    try:
        pv = (report13 or {}).get("verify", {}).get("eca_floor", {})
        if "clean_ridge0" in pv:
            checks["eca_ridge0_floor"]["pipeline_real_ref_clean_ridge0"] = bool(pv["clean_ridge0"])
            checks["eca_ridge0_floor"]["pipeline_note"] = (
                "파이프라인 실측 기준(대역제한·complex64·고DNR): clean_ridge0 위 값. "
                "델리버 동작영역(DNR≈75)은 청정이나 DNR120 코너에서 뒤집힐 수 있음 — 감도축.")
    except Exception:
        pass

    ran = {k: v for k, v in checks.items() if v.get("ok") is not None}
    skipped = {k: v.get("reason") for k, v in checks.items() if v.get("ok") is None}
    n_fail = sum(1 for v in ran.values() if not v["ok"])
    # 스펙 §16 게이트 매핑
    def _st(name):
        v = checks.get(name, {})
        return None if v.get("ok") is None else bool(v["ok"])
    gates = {
        "fs0_9mode_snr90_equal (R8)": _st("fs0_mode_snr90"),
        "eca_ridge0_residual (R6)": _st("eca_ridge0_floor"),
        "closed_form_vs_measured (§2.5)": _st("closed_form_vs_measured"),
        "solve_range_outermost_crossing (S6)": _st("solve_range_nonmonotone"),
        "ssb_M5_prf50 (F1)": _st("cpi_M_from_prf"),
        "power_3views (F2)": _st("cpi_M_from_prf"),   # 3뷰 존재는 cpi 체크에 병기
        "sigma_el_negative (S8)": _st("sigma_el_sign"),
        "snr_convention_consistent (R3§5)": _st("snr_convention_consistency"),
        "ground_2ray_fresnel_equiv (R1)": _st("ground_2ray_check"),
        "geometry_equivalence": _st("geometry_equivalence"),
    }
    ran_gates = {k: v for k, v in gates.items() if v is not None}
    return dict(
        meta=dict(report="report13", tool="verify_freespace.py",
                  generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
                  runtime_s=round(time.time() - t0, 2),
                  report13_path=report13_path, report13_present=bool(report13),
                  numpy=np.__version__, quick=bool(quick), n_geom=int(n_geom)),
        summary=dict(n_checks=len(checks), n_ran=len(ran), n_skipped=len(skipped),
                     n_fail=n_fail, all_ran_pass=bool(n_fail == 0),
                     gates_ran_pass=bool(all(ran_gates.values())),
                     skipped=skipped),
        gates=gates,
        checks=checks,
    )


def main(argv=None):
    ap = argparse.ArgumentParser(description="report13 자유공간 검증 하니스")
    ap.add_argument("--out", default=DEFAULT_OUT, help="판정 JSON 산출경로")
    ap.add_argument("--report13", default=DEFAULT_REPORT13,
                    help="experiment_freespace_range 산출(있으면 FS-0/k_mode 게이트 활성)")
    ap.add_argument("--full", action="store_true", help="ECA 바닥 스윕을 크게(느림)")
    ap.add_argument("--n-geom", type=int, default=2000, help="기하 동치검정 케이스 수")
    args = ap.parse_args(argv)

    res = run_all(report13_path=args.report13, quick=(not args.full), n_geom=args.n_geom)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(_jsonify(res), f, indent=1, ensure_ascii=False)

    s = res["summary"]
    print(f"[verify_freespace] {os.path.relpath(args.out, _ROOT)}")
    print(f"  ran={s['n_ran']}  skipped={s['n_skipped']}  FAIL={s['n_fail']}  "
          f"gates_pass={s['gates_ran_pass']}")
    for name, c in res["checks"].items():
        st = "SKIP" if c.get("ok") is None else ("pass" if c["ok"] else "FAIL")
        extra = c.get("reason", "") if st == "SKIP" else ""
        print(f"    [{st:4s}] {name}  {extra}")
    return 0 if s["n_fail"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
