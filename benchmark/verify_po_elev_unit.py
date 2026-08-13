# -*- coding: utf-8 -*-
"""
verify_po_elev_unit.py — ⭐⭐ **해석 단위시험: 답을 아는 문제로 PO 커널을 잰다**
================================================================================

왜 만드나 (2026-08-11)
  앙각 스윕에서 내가 쓴 두 잣대 —「위상 변동폭(np.unwrap 의 peak-to-peak)」과
  「전 구간 단일 Hann FFT 의 −20 dB 폭」— 이 단조롭지 않았다. 그걸 곧바로 «커널이
  이상하다» 로 읽으면 안 된다. **잣대가 부실할 수 있기 때문이다.**
  그래서 답이 **해석적으로 정확히 알려진** 문제를 만들어 커널과 잣대를 함께 잰다.

■ 답을 아는 문제
  반경 r 의 수평 원을 도는 **점산란체 하나**. 레이더가 앙각 el 에 있으면 (원거리장)

      f_d(t) = ±(2/λ)·2π f_rev·r·cos(el)·sin(2π f_rev t)
      max|f_d| = f_tip(el) = (2/λ)·2π f_rev·r·cos(el)        ← cos(el) 로 줄고
      el = −90° 에서 **정확히 0** (v ⟂ û 이고 |p−p_tx| = √(r²+R²) 이 아예 안 변한다)

  더 강한 기준도 있다 — **파형 자체**. 커널의 위상 규약을 그대로 쓰면

      E_ana(t) = Σ_i exp(+j 2k (|p_i(t) − p_tx| − R))        (근사 없이 3D 거리 그대로)

  이걸 커널 출력과 **복소 상관**으로 맞대면 미분·언랩을 아예 안 거치고 판정할 수 있다.

■ 표적 두 개 — 두 번째는 «잣대» 를 잡으려고 넣는다
  (a) `one_sphere`  반경 a 의 작은 구 하나가 반경 r 로 공전   → 진폭이 거의 일정
  (b) `two_spheres` 같은 구 두 개를 180° 마주보게(2엽 로터)   → E ≈ 2cos(β cos ωt),
      **주기적으로 0 을 지난다**. 물리는 (a) 와 같은 도플러 지지집합인데, np.unwrap 의
      peak-to-peak 은 여기서 폭발한다. 즉 그 잣대의 폭발은 **커널이 아니라 널(null)** 이
      만든다 — 답을 아는 문제에서 그걸 증명한다.

■ 커널 규약을 그대로 따른다 (생산 경로와 같은 축)
  · `sbr_field(..., grid_ref=얼린격자, range_m=R)` — 앙각 스윕과 같은 배선
  · û 는 자세마다 안 바뀐다(평행 광선 격자). 위상만 구면파.
  · 재질은 float 1.0 (=|Γ|, PEC 경계조건) → 각도의존 Γ·셸 투과가 안 켜진다.
  · 격자 사다리 λ/12(생산) · λ/24 · λ/48 — 생산 간격이 부족하면 그렇게 적는다.

■ ⛔ 이 스크립트는 커널을 «맞다» 로 몰지 않는다. 게이트는 숫자로 떨어지고,
   틀리면 verdict 에 FAIL 로 적힌다.

    SIONNA2_GPU=2 PYTHONPATH=src:benchmark \
        /workspace/.venvs/py312/bin/python benchmark/verify_po_elev_unit.py
"""
from __future__ import annotations

import json
import os
import sys
import time

os.environ.setdefault("SIONNA2_GPU", "2")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np                                                       # noqa: E402

C0 = 299792458.0
FC = 3.5e9
LAM = C0 / FC
K = 2.0 * np.pi / LAM

#  ── 운동학 — 앙각 스윕(matrice4e)과 **같은 숫자**를 쓴다 ────────────────────
RPM = 3800.0                      # matrice4e hover_rpm
F_REV = RPM / 60.0                # 63.3333 Hz
R_ORB = 0.137                     # 프롭 반경 274 mm / 2
A_SPH = 0.020                     # 산란체(구) 반경 — 지름 0.04 m ≈ 0.47 λ
RANGE_M = 10.0                    # 앙각 스윕과 같은 구면 반경
AZ_DEG = 0.0
ELS = (0.0, -30.0, -60.0, -75.0, -90.0)

#  슬로타임 — **정수 회전수**로 끊어 스펙트럼 누설을 0 으로 만든다
N_POSE = 512
PRF = 256.0 * F_REV               # 16213.33 Hz → 512 표본 = 정확히 2 회전
SEG, RINGS = 20, 10               # 구 메쉬 (faceting 오차 a(1−cos π/20) = 0.25 mm = λ/340)

DIVS_ONE = (12, 24, 48)           # one_sphere 격자 사다리 (12 = 생산)
DIVS_TWO = (12, 48)               # two_spheres — 생산 간격 + 수렴 간격

OUT_JSON = os.path.join(ROOT, "outputs", "verify_po_elev_unit.json")
OUT_NPZ = os.path.join(ROOT, "outputs", "verify_po_elev_unit.npz")
OUT_PNG = os.path.join(ROOT, "outputs", "verify_po_elev_unit.png")


def los(az_deg: float, el_deg: float) -> np.ndarray:
    a, e = np.radians(az_deg), np.radians(el_deg)
    return np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])


def f_tip_pred(el_deg: float) -> float:
    """원거리장 해석값 (2/λ)·2π f_rev r cos(el)."""
    return (2.0 / LAM) * (2.0 * np.pi * F_REV * R_ORB) * np.cos(np.radians(el_deg))


def scat_pos(theta: np.ndarray, n_scat: int) -> np.ndarray:
    """(n_scat, T, 3) 산란체 중심 궤적. n_scat=2 면 180° 마주본다."""
    out = []
    for i in range(n_scat):
        th = theta + i * (2.0 * np.pi / n_scat)
        out.append(np.stack([R_ORB * np.cos(th), R_ORB * np.sin(th),
                             np.zeros_like(th)], axis=-1))
    return np.stack(out, axis=0)


# ═══ 잣대 ═══════════════════════════════════════════════════════════════════
def inst_freq(E: np.ndarray, prf: float):
    """⭐**언랩을 안 쓰는** 순시 주파수. 연속표본 위상차를 (−π,π] 로 감싸 읽는다 —
    표본당 위상변화가 π 미만(= 나이퀴스트 안)이면 이게 정답이고, |E| 가 0 근처를
    지나도 **누적 오류가 안 생긴다**(np.unwrap 은 여기서 무너진다)."""
    return np.angle(E[1:] * np.conj(E[:-1])) * prf / (2.0 * np.pi)


def inst_stats(E: np.ndarray, prf: float):
    """순시 주파수 요약. ⚠**널 게이트**는 앞뒤 표본이 **둘 다** 살아있어야 통과시킨다 —
    한쪽만 보면 널을 건너뛴 위상 점프(π)가 그대로 들어와 PRF/2 스파이크가 된다.
    ⚠ 성분이 여럿인 신호(2엽)에서는 순시주파수 자체가 도플러 지지집합이 아니다 —
      그때는 스펙트럼 잣대를 봐야 한다(이 사실을 원장에 적으려고 둘 다 낸다)."""
    f = inst_freq(E, prf)
    m = np.abs(E)
    thr = 0.3 * float(np.sqrt((m ** 2).mean()))
    g = (m[:-1] > thr) & (m[1:] > thr)
    a = np.abs(f[g]) if g.any() else np.abs(f)
    #  ⭐**최대치를 그대로 쓰지 마라.** 격자 표본화 잡음이 표본 하나만 튀겨도 max 는 그걸 문다
    #    (실측: λ/12·el −90° 에서 해석 0 Hz 인데 max 가 689 Hz). f_d(t)=f_tip·sin(ωt) 라면
    #    |f| 의 p95 = f_tip·sin(0.95·π/2) = 0.997·f_tip 이라 **편의가 0.3% 뿐**이다.
    return dict(inst_f_absmax_hz=float(np.abs(f).max()),
                inst_f_p99_hz=float(np.percentile(a, 99.0)),
                inst_f_p95_hz=float(np.percentile(a, 95.0)),
                inst_f_gate_kept_pct=float(g.mean() * 100.0),
                inst_f_rms_hz=float(np.sqrt((f ** 2).mean())),
                #  PRF 에 안 매인 잣대 — 표본당 위상 증분의 표준편차 [deg]
                phase_step_std_deg=float(np.std(np.angle(E[1:] * np.conj(E[:-1]))) *
                                         180.0 / np.pi))


def spec_metrics(E: np.ndarray, prf: float, f_ref: float, drop_dc: bool = False):
    """정수 주기 표본 → 창 없이 FFT(누설 0). 지지집합을 **에너지**로 잰다.

    drop_dc=True 면 0 Hz 빈을 뺀 뒤 잰다 — 실제 기체 신호에서 **정지한 동체**의 기여가
    0 Hz 에 몰려 있어, 그걸 두면 rms 대역폭이 «동체 대 로터 세기비» 를 재게 된다."""
    T = len(E)
    Z = np.fft.fft(E) / T
    f = np.fft.fftfreq(T, 1.0 / prf)
    P = np.abs(Z) ** 2
    dc_pct = float(P[0] / P.sum() * 100.0) if P.sum() > 0 else None
    if drop_dc:
        P = P.copy(); P[0] = 0.0
    tot = P.sum()
    if tot <= 0:
        return dict(f_rms_hz=None, f_edge99_hz=None, beyond_ftip_pct=None,
                    f_mean_hz=None, dc_power_pct=dc_pct)
    f_mean = float((f * P).sum() / tot)
    f_rms = float(np.sqrt((f ** 2 * P).sum() / tot))
    o = np.argsort(np.abs(f))
    c = np.cumsum(P[o]) / tot
    j = int(np.searchsorted(c, 0.99))
    f99 = float(abs(f[o[min(j, T - 1)]]))
    beyond = (float(P[np.abs(f) > 1.05 * f_ref].sum() / tot * 100.0)
              if f_ref > 1e-9 else None)
    return dict(f_rms_hz=f_rms, f_edge99_hz=f99, beyond_ftip_pct=beyond,
                f_mean_hz=f_mean, dc_power_pct=dc_pct)


def legacy_metrics(E: np.ndarray, prf: float):
    """⭐**내가 앙각 스윕에서 쓴 두 잣대를 그대로 재현한다** — 여기서 부실함을 보인다.
    (a) np.unwrap 위상의 peak-to-peak [deg]
    (b) 전 구간 단일 Hann FFT 의 −20 dB 가장자리 [Hz]"""
    ptp = float(np.ptp(np.unwrap(np.angle(E))) * 180.0 / np.pi)
    T = len(E)
    Z = np.abs(np.fft.fft(E * np.hanning(T)))
    f = np.fft.fftfreq(T, 1.0 / prf)
    if Z.max() <= 0:
        return dict(unwrap_ptp_deg=ptp, edge20_hz=None)
    m = Z >= Z.max() * 10 ** (-20.0 / 20.0)
    return dict(unwrap_ptp_deg=ptp, edge20_hz=float(np.abs(f[m]).max()))


def match(Ek: np.ndarray, Ea: np.ndarray):
    """커널 대 해석 — **미분도 언랩도 안 거치는** 복소 정합.
    ρ = |<Ek,Ea>|/(‖Ek‖‖Ea‖), 최적 복소 스케일 c 를 뺀 잔차 nrmse."""
    ip = complex(np.vdot(Ea, Ek))                       # Σ conj(Ea)·Ek
    na, nk = float(np.linalg.norm(Ea)), float(np.linalg.norm(Ek))
    if na <= 0 or nk <= 0:
        return dict(rho=None, nrmse=None, const_phase_deg=None)
    c = ip / (na ** 2)
    r = np.linalg.norm(Ek - c * Ea) / nk
    #  잔차 위상 — 커널이 해석보다 «얼마나 다르게 위상을 도는가». 널이 없으면 상수여야 한다.
    q = Ek * np.conj(c * Ea)
    ph = np.angle(q * np.conj(np.exp(1j * np.angle(q.sum()))))
    return dict(rho=float(abs(ip) / (na * nk)), nrmse=float(r),
                const_phase_deg=float(np.angle(c) * 180.0 / np.pi),
                resid_phase_std_deg=float(np.std(ph) * 180.0 / np.pi),
                resid_phase_ptp_deg=float(np.ptp(ph) * 180.0 / np.pi))


def amp_depth(E: np.ndarray):
    m = np.abs(E)
    return dict(min_over_max=float(m.min() / max(m.max(), 1e-300)),
                mod_depth=float((m.max() - m.min()) / max(m.max() + m.min(), 1e-300)))


# ═══ 실행 ═══════════════════════════════════════════════════════════════════
def run():
    t_all = time.time()
    from gpu import pick
    pick(verbose=True)
    from geom import Mesh, uv_sphere
    from rcs_sbr import sbr_field, grid_ref_from

    gm = {"sph": 1.0}                                   # float = |Γ| = 1 (PEC 경계조건)
    t = np.arange(N_POSE) / PRF
    theta = 2.0 * np.pi * F_REV * t

    def build(th: float, n_scat: int):
        m = Mesh("sph")
        for i in range(n_scat):
            a = th + i * (2.0 * np.pi / n_scat)
            m.merge(uv_sphere(A_SPH, center=(R_ORB * np.cos(a), R_ORB * np.sin(a), 0.0),
                              seg=SEG, rings=RINGS, group="sph"))
        return m

    J = dict(meta=dict(
        script="benchmark/verify_po_elev_unit.py",
        purpose_ko=("해석해가 있는 최소 표적으로 PO/SBR 커널의 **운동학**을 재는 단위시험. "
                    "커널 판정 전에 잣대부터 세운다."),
        fc_hz=FC, lambda_m=LAM, range_m=RANGE_M, az_deg=AZ_DEG,
        elevations_deg=list(ELS), n_pose=N_POSE, prf_hz=PRF,
        revolutions=float(N_POSE / PRF * F_REV),
        rpm=RPM, f_rev_hz=F_REV, orbit_radius_m=R_ORB, sphere_radius_m=A_SPH,
        sphere_ka=float(2 * np.pi * A_SPH / LAM),
        beta_rad=float(2 * K * R_ORB),
        f_tip_el0_hz=float(f_tip_pred(0.0)),
        illumination="spherical-wave phase (range_m), parallel ray grid, frozen grid",
        material="float 1.0 (|Γ|=1, PEC boundary) — angle-Γ and shell penetration off",
        phase_convention_ko=("커널은 exp(+j2k·range) 를 쓴다 → 순시주파수 = +(2/λ)dR/dt. "
                             "표준 도플러(−(2/λ)dR/dt)와 **부호가 반대**다. "
                             "Sionna 경로(exp(−j2πfτ))와도 반대 — 크기 비교만 유효."),
        gpu=os.environ.get("SIONNA2_GPU"),
        stamp=time.strftime("%Y-%m-%d %H:%M:%S")), cases=[])

    series = {}
    jobs = [("one_sphere", 1, DIVS_ONE), ("two_spheres", 2, DIVS_TWO)]
    for tgt, n_scat, divs in jobs:
        bnd = [np.asarray(build(x, n_scat).v, float)
               for x in np.linspace(0, 2 * np.pi, 65)[:-1]]
        P = scat_pos(theta, n_scat)                      # (n_scat, T, 3)
        for div in divs:
            d = LAM / div
            gref = grid_ref_from(bnd, FC, spacing=d)
            for el in ELS:
                u = los(AZ_DEG, el)
                p_tx = np.asarray(gref.ctr, float) + RANGE_M * u
                # 해석 파형 — 커널과 **같은 위상 규약**, 3D 거리 근사 없이
                dist = np.linalg.norm(P - p_tx[None, None, :], axis=-1)   # (n_scat,T)
                Ea = np.exp(1j * 2.0 * K * (dist - RANGE_M)).sum(axis=0)

                Ek = np.zeros(N_POSE, complex)
                t0 = time.time()
                for i in range(N_POSE):
                    Ek[i] = sbr_field(build(float(theta[i]), n_scat), gm, FC, u,
                                      spacing=d, grid_ref=gref, range_m=RANGE_M)
                    if i and i % 128 == 0:
                        e = time.time() - t0
                        print(f"    {tgt} div{div} el{el:+.0f}: {i}/{N_POSE} "
                              f"{e:.0f}s ETA {(N_POSE-i)/i*e:.0f}s", flush=True)
                secs = time.time() - t0

                ft = f_tip_pred(el)
                row = dict(
                    target=tgt, n_scatterers=n_scat, div=div, spacing_m=float(d),
                    n_rays=int(gref.n) ** 2, el_deg=float(el),
                    cos_el=float(np.cos(np.radians(el))),
                    f_tip_pred_hz=float(ft),
                    #  ⚠시험 산란체는 **점이 아니라 반지름 a 의 구**다 → 바깥 가장자리는
                    #    r+a 로 돈다. 커널의 도플러는 이 둘 사이에 있어야 한다.
                    f_tip_outer_hz=float(ft * (R_ORB + A_SPH) / R_ORB),
                    #  ⭐일정진폭 신호라면 스펙트럼 rms 대역폭이 정확히 f_tip/√2 다
                    f_rms_pred_hz=float(ft / np.sqrt(2.0)),
                    #  ⭐한 산란체의 **물리적** 위상 진폭 = 2k·2r·cos(el) [deg]
                    phase_excursion_pred_deg=float(4.0 * K * R_ORB *
                                                   np.cos(np.radians(el)) * 180.0 / np.pi),
                    seconds=round(secs, 1),
                    sigma_dbsm=float(10 * np.log10(4 * np.pi / LAM ** 2 *
                                                   (np.abs(Ek) ** 2).mean())),
                    kernel=dict(**inst_stats(Ek, PRF), **spec_metrics(Ek, PRF, ft),
                                **amp_depth(Ek), legacy=legacy_metrics(Ek, PRF)),
                    analytic=dict(**inst_stats(Ea, PRF), **spec_metrics(Ea, PRF, ft),
                                  **amp_depth(Ea), legacy=legacy_metrics(Ea, PRF)),
                    match=match(Ek, Ea))
                #  커널 ÷ 해석 — 상대오차 [%]
                for key in ("inst_f_absmax_hz", "inst_f_p95_hz", "inst_f_p99_hz",
                            "f_rms_hz", "f_edge99_hz"):
                    a_, k_ = row["analytic"][key], row["kernel"][key]
                    row.setdefault("rel_err_pct", {})[key] = (
                        float((k_ - a_) / a_ * 100.0) if a_ and abs(a_) > 1e-9 else None)
                #  해석 원거리장 법칙 대비 (⭐p95 — max 는 표본 하나에 물린다)
                row["rel_err_pct"]["inst_f_p95_vs_ftip"] = (
                    float((row["kernel"]["inst_f_p95_hz"] - ft) / ft * 100.0)
                    if ft > 1e-9 else None)
                J["cases"].append(row)
                series[f"{tgt}/d{div}/el{el:+.0f}/kernel"] = Ek
                series[f"{tgt}/d{div}/el{el:+.0f}/analytic"] = Ea
                print(f"  ✅ {tgt:11s} λ/{div:<2d} el{el:+5.0f}  ρ={row['match']['rho']:.4f} "
                      f"nrmse={row['match']['nrmse']:.3f}  "
                      f"fd_p95 {row['kernel']['inst_f_p95_hz']:8.1f} Hz "
                      f"(해석 {row['analytic']['inst_f_p95_hz']:8.1f}, "
                      f"예측 {ft:8.1f})   max {row['kernel']['inst_f_absmax_hz']:8.1f}"
                      f"  {secs:.0f}s", flush=True)

    J["meta"]["seconds_total"] = float(time.time() - t_all)
    J["gates"] = gates(J["cases"])
    J["real_sweep_recheck"] = recheck_real_sweep()
    np.savez_compressed(OUT_NPZ, t=t, **series)
    with open(OUT_JSON, "w") as f:
        json.dump(J, f, ensure_ascii=False, indent=1)
    print(f"\n✅ {OUT_JSON}\n✅ {OUT_NPZ}")
    return J


# ═══ 게이트 ═════════════════════════════════════════════════════════════════
def gates(cases):
    """숫자로 떨어지는 판정. ⛔ 통과를 목표로 삼지 않는다 — 사실을 적는다."""
    g = []

    def add(name, ok, detail, why):
        g.append(dict(name=name, pass_=bool(ok), detail=detail, why_ko=why))

    one = [c for c in cases if c["target"] == "one_sphere"]
    prod = [c for c in one if c["div"] == 12]
    fine = [c for c in one if c["div"] == 48]

    for tag, sub in (("prod_div12", prod), ("fine_div48", fine)):
        mv = [c["match"]["rho"] for c in sub if c["el_deg"] != -90.0]
        add(f"G1_waveform_match_{tag}", min(mv) >= 0.98 if mv else False,
            dict(rho_min=round(min(mv), 4) if mv else None,
                 per_el={f"{c['el_deg']:+.0f}": round(c["match"]["rho"], 4) for c in sub}),
            "커널 파형이 해석 점산란체 파형과 코히어런트로 맞나 (ρ≥0.98). "
            "미분·언랩을 안 거치는 가장 강한 기준이다.")
        er = [abs(c["rel_err_pct"]["inst_f_p95_hz"]) for c in sub
              if c["el_deg"] != -90.0 and c["rel_err_pct"]["inst_f_p95_hz"] is not None]
        add(f"G2_fdmax_vs_analytic_{tag}", max(er) <= 5.0 if er else False,
            dict(metric="inst_f_p95_hz (⭐max 는 표본 하나에 물려 못 쓴다)",
                 max_abs_err_pct=round(max(er), 2) if er else None,
                 per_el={f"{c['el_deg']:+.0f}": round(c["rel_err_pct"]["inst_f_p95_hz"], 2)
                         for c in sub if c["rel_err_pct"]["inst_f_p95_hz"] is not None},
                 raw_absmax_err_pct={
                     f"{c['el_deg']:+.0f}": round(c["rel_err_pct"]["inst_f_absmax_hz"], 1)
                     for c in sub if c["rel_err_pct"]["inst_f_absmax_hz"] is not None}),
            "순시 도플러(p95)가 같은 잣대로 잰 해석값과 5% 안에 드나. "
            "raw_absmax 를 함께 적는 이유는 **최대치 잣대가 왜 못 쓰는지** 보이려는 것이다.")
        z = [c for c in sub if c["el_deg"] == -90.0]
        if z:
            ac = 100.0 - z[0]["kernel"]["dc_power_pct"]
            add(f"G3_nadir_null_{tag}", ac <= 1.0,
                dict(ac_power_pct=round(ac, 5),
                     ac_below_dc_db=round(float(10 * np.log10(max(ac, 1e-12) /
                                                              max(100 - ac, 1e-12))), 2),
                     resid_phase_ptp_deg=round(z[0]["match"]["resid_phase_ptp_deg"], 3),
                     phase_step_std_deg=round(z[0]["kernel"]["phase_step_std_deg"], 4),
                     amp_mod_depth=round(z[0]["kernel"]["mod_depth"], 5),
                     inst_f_rms_hz=round(z[0]["kernel"]["inst_f_rms_hz"], 2),
                     inst_f_rms_hz_note_ko="⚠이 Hz 값은 PRF 에 비례한다 — 잡음을 Hz 로 "
                                           "읽으면 안 된다. 판정은 AC 전력비로 한다."),
                "⭐직하방에서는 |p−p_tx| = √(r²+R²) 가 아예 안 변한다 → 해석 도플러 **정확히 0**, "
                "장도 상수. 커널이 내는 변동은 전부 **광선 격자 표본화 잡음**이고, "
                "이 칸이 그 바닥값이다.")
        #  ⭐G4 는 «커널이 해석 파형과 같은 만큼만 f_tip 밖으로 새는가» 를 묻는다.
        #    ⚠**절대 문턱(예전 2%)은 틀린 잣대였다** — 유한 CPI 의 위상변조 톤은 원래
        #    ±f_tip 밖에 베셀 꼬리(n>β 측대역)를 갖는다. 해석 파형도 똑같이 샌다.
        bt = [(c["kernel"]["beyond_ftip_pct"], c["analytic"]["beyond_ftip_pct"]) for c in sub
              if c["el_deg"] != -90.0 and c["kernel"]["beyond_ftip_pct"] is not None]
        dd = [abs(k - a) for k, a in bt]
        add(f"G4_support_matches_analytic_{tag}", max(dd) <= 0.5 if dd else False,
            dict(max_abs_diff_pp=round(max(dd), 4) if dd else None,
                 per_el={f"{c['el_deg']:+.0f}": [round(c["kernel"]["beyond_ftip_pct"], 3),
                                                 round(c["analytic"]["beyond_ftip_pct"], 3)]
                         for c in sub if c["kernel"]["beyond_ftip_pct"] is not None},
                 legend="[커널, 해석] % of energy beyond ±1.05·f_tip"),
            "±1.05·f_tip 밖 에너지 비율이 **해석 파형과 같은가**(차이 ≤0.5 pp). "
            "⚠절대 문턱으로 재면 안 된다 — 유한 CPI 위상변조 톤은 해석적으로도 "
            "베셀 꼬리를 갖는다(이것도 내 잣대가 틀렸던 자리다).")
        #  G2b — 시험 산란체가 유한 크기라 도플러가 f_tip(r)~f_tip(r+a) 사이면 물리적으로 옳다
        br = [(c["el_deg"], c["kernel"]["inst_f_p95_hz"], c["f_tip_pred_hz"],
               c["f_tip_outer_hz"]) for c in sub if c["el_deg"] != -90.0]
        okb = all(0.95 * p <= v <= 1.05 * o for _, v, p, o in br)
        add(f"G2b_fd_within_finite_size_bracket_{tag}", okb,
            dict(per_el={f"{e:+.0f}": dict(p95=round(v, 1), lo=round(0.95 * p, 1),
                                           hi=round(1.05 * o, 1)) for e, v, p, o in br}),
            "구 반지름 a 때문에 바깥 가장자리는 r+a 로 돈다 → 커널의 p95 가 "
            "[0.95·f_tip(r), 1.05·f_tip(r+a)] 안이면 물리적으로 정당하다.")
        fr = [abs(c["kernel"]["f_rms_hz"] / c["f_rms_pred_hz"] - 1) * 100
              for c in sub if c["el_deg"] != -90.0 and c["f_rms_pred_hz"] > 1e-9]
        add(f"G6_rms_bandwidth_law_{tag}", max(fr) <= 8.0 if fr else False,
            dict(max_err_pct=round(max(fr), 2) if fr else None,
                 per_el={f"{c['el_deg']:+.0f}": round(c["kernel"]["f_rms_hz"] /
                                                      c["f_rms_pred_hz"], 4)
                         for c in sub if c["f_rms_pred_hz"] > 1e-9}),
            "⭐일정진폭 위상변조라면 스펙트럼 rms 대역폭이 **정확히** f_tip/√2 다 "
            "(<(dφ/dt)²> = (β ω)²/2). 이게 −20 dB 폭을 대신할 잣대다.")

    #  cos(el) 법칙 — 측정치 ÷ cos(el) 가 상수여야 한다
    for tag, sub in (("prod_div12", prod), ("fine_div48", fine)):
        r = [(c["cos_el"], c["kernel"]["inst_f_p95_hz"]) for c in sub if c["cos_el"] > 1e-6]
        if r:
            k = [v / (f_tip_pred(0.0) * ce) for ce, v in r]
            spread = (max(k) - min(k)) / np.mean(k) * 100.0
            add(f"G5_cos_law_{tag}", spread <= 6.0,
                dict(metric="inst_f_p95_hz", cos_el=[round(x[0], 4) for x in r],
                     ratio_to_costimes_ftip0=[round(x, 4) for x in k],
                     spread_pct=round(float(spread), 2)),
                "f_d(p95) ÷ (f_tip(0)·cos el) 가 앙각마다 같은 값인가 = ⭐cos 법칙 검증. "
                "이게 사용자 질문(«계속 줄어야 하는 거 아니야?»)에 곧바로 답하는 칸이다.")

    #  ⭐⭐잣대 시험 — 답을 아는 문제에서 **내 옛 잣대**가 어떻게 무너지나
    two = [c for c in cases if c["target"] == "two_spheres"]
    if two:
        def rr(c, side):
            ph = c["phase_excursion_pred_deg"]
            e20 = c[side]["legacy"]["edge20_hz"]
            fr = c[side]["f_rms_hz"]
            return dict(
                unwrap_ptp_deg=round(c[side]["legacy"]["unwrap_ptp_deg"], 1),
                unwrap_over_physical=(round(c[side]["legacy"]["unwrap_ptp_deg"] / ph, 2)
                                      if ph > 1e-6 else None),
                edge20_over_ftip=(round(e20 / c["f_tip_pred_hz"], 3)
                                  if e20 and c["f_tip_pred_hz"] > 1e-9 else None),
                f_rms_over_pred=(round(fr / c["f_rms_pred_hz"], 3)
                                 if fr and c["f_rms_pred_hz"] > 1e-9 else None),
                beyond_ftip_pct=(round(c[side]["beyond_ftip_pct"], 3)
                                 if c[side]["beyond_ftip_pct"] is not None else None),
                amp_min_over_max=round(c[side]["min_over_max"], 5))
        rows = {f"{c['el_deg']:+.0f}": dict(kernel=rr(c, "kernel"),
                                            analytic=rr(c, "analytic"),
                                            rho=round(c["match"]["rho"], 4)) for c in two}

        def fold(v):                # 1 에서 몇 «배» 벗어났나 (위·아래 대칭)
            return max(v, 1.0 / v) if v and v > 0 else None

        #  M0: 널이 없는 깨끗한 1개 산란체에서는 옛 잣대가 **맞는다**
        o1 = {f"{c['el_deg']:+.0f}": round(c["kernel"]["legacy"]["unwrap_ptp_deg"] /
                                           c["phase_excursion_pred_deg"], 3)
              for c in prod if c["phase_excursion_pred_deg"] > 1e-6}
        f1 = [fold(v) for v in o1.values() if fold(v)]
        add("M0_legacy_unwrap_ok_when_no_nulls", max(f1) <= 1.15 if f1 else False,
            dict(unwrap_over_physical=o1, max_fold=round(max(f1), 3) if f1 else None),
            "널이 없는 산란체 1개에서는 np.unwrap ptp 가 물리적 위상진폭 4k·r·cos(el) 을 "
            "제대로 잰다 — 즉 그 잣대가 «항상» 틀린 게 아니라 **널에서만** 무너진다.")
        #  M1: **해석 파형**(커널 오차 0)에서 이미 옛 잣대가 물리와 어긋나면 그 잣대가 범인이다
        bad = [fold(v["analytic"]["unwrap_over_physical"]) for v in rows.values()
               if v["analytic"]["unwrap_over_physical"]]
        add("M1_legacy_unwrap_broken_by_nulls", max(bad) > 2.0 if bad else False,
            dict(max_fold_error=round(max(bad), 2) if bad else None, per_el=rows),
            "⭐**해석적으로 완벽한** 2엽 파형에 np.unwrap ptp 를 대면 물리적 위상진폭"
            "(4k·r·cos el)의 몇 «배» 가 나오나. 2 배 넘게 벗어나면 그 잣대는 커널이 아니라 "
            "**널(|E|→0)의 π 점프**를 잰 것이다 — 커널 무죄의 직접 증거.")
        #  M2: 고친 잣대(스펙트럼)는 같은 널에서도 살아남는가 — 격자 간격마다
        for div in sorted({c["div"] for c in two}):
            ok = [c for c in two if c["div"] == div and c["el_deg"] != -90.0]
            fe = [abs(c["kernel"]["f_rms_hz"] / c["analytic"]["f_rms_hz"] - 1) * 100
                  for c in ok if c["analytic"]["f_rms_hz"]]
            add(f"M2_spectral_metric_survives_nulls_div{div}",
                max(fe) <= 5.0 if fe else False,
                dict(max_frms_err_pct=round(max(fe), 2) if fe else None,
                     per_el={f"{c['el_deg']:+.0f}":
                             round(c["kernel"]["f_rms_hz"] / c["analytic"]["f_rms_hz"], 3)
                             for c in ok if c["analytic"]["f_rms_hz"]},
                     inst_f_p95_kernel_over_analytic={
                         f"{c['el_deg']:+.0f}":
                         (round(c["kernel"]["inst_f_p95_hz"] /
                                c["analytic"]["inst_f_p95_hz"], 1)
                          if c["analytic"]["inst_f_p95_hz"] > 1e-9 else None) for c in ok}),
                "널이 깊은 2엽 신호에서 **스펙트럼 rms 대역폭**이 해석값과 붙어 있나. "
                "⭐같은 칸의 inst_f_p95 비율도 보라 — 순시주파수 잣대는 여기서 "
                "**해석값 자체가 ~0 Hz** 라 아예 못 쓴다(다성분 신호의 순시주파수는 "
                "도플러 지지집합이 아니다). 이것이 −20 dB 폭 대신 무엇을 써야 하는가의 답이다.")
    return g


# ═══ ⭐고친 잣대를 **실제 앙각 스윕**에 되먹인다 (읽기만·GPU 안 씀) ══════════
def recheck_real_sweep():
    """outputs/elevation_sweep_md.npz 를 **다시 읽어** 고친 잣대로 잰다.
    ⚠ 기존 원장(elevation_sweep_md.json)은 **안 건드린다** — 여기 새 칸에만 적는다."""
    npz = os.path.join(ROOT, "outputs", "elevation_sweep_md.npz")
    if not os.path.exists(npz):
        return dict(available=False, path=npz)
    meta = json.load(open(os.path.join(ROOT, "outputs",
                                       "elevation_sweep_md.json")))["_meta"]
    prf = float(meta["prf_hz"])
    lam = C0 / float(meta["fc_hz"])
    r_tip, rpm = 0.137, 3800.0                  # matrice4e (274 mm 프롭 · hover 3800 rpm)
    f_rev = rpm / 60.0
    out = dict(available=True, source=npz,
               note_ko=("단위시험에서 세운 **고친 잣대**를 실제 스윕 데이터에 그대로 적용. "
                        "위상 변동폭(unwrap)·−20 dB 폭은 참고로만 남기고, 판정은 "
                        "스펙트럼 rms 대역폭·f_tip 밖 에너지·널 게이트한 순시주파수로 한다."),
               prf_hz=prf, rows=[])
    Z = np.load(npz)
    for key in sorted(Z.files):
        E = np.asarray(Z[key], complex)
        if E.ndim != 1 or E.size < 16:
            continue
        try:
            el = float(key.split("el")[-1])
        except ValueError:
            continue
        ft = (2.0 / lam) * (2.0 * np.pi * f_rev * r_tip) * np.cos(np.radians(el))
        m = np.abs(E)
        row = dict(series=key, el_deg=el, f_tip_pred_hz=round(float(ft), 1),
                   n=int(E.size),
                   amp_min_over_max=round(float(m.min() / max(m.max(), 1e-300)), 5),
                   amp_mod_depth=round(float((m.max() - m.min()) /
                                             max(m.max() + m.min(), 1e-300)), 4),
                   phase_excursion_pred_deg=round(float(4 * np.pi / lam * 2 * r_tip *
                                                        np.cos(np.radians(el)) *
                                                        180 / np.pi), 1))
        row["legacy"] = {k: (round(v, 2) if v is not None else None)
                         for k, v in legacy_metrics(E, prf).items()}

        def pack(sm):
            return dict(
                f_rms_hz=round(sm["f_rms_hz"], 2) if sm["f_rms_hz"] else None,
                f_edge99_hz=round(sm["f_edge99_hz"], 2) if sm["f_edge99_hz"] else None,
                beyond_ftip_pct=(round(sm["beyond_ftip_pct"], 3)
                                 if sm["beyond_ftip_pct"] is not None else None),
                f_rms_over_pred=(round(sm["f_rms_hz"] / (ft / np.sqrt(2)), 3)
                                 if sm["f_rms_hz"] and ft > 1e-9 else None))
        sm = spec_metrics(E, prf, ft)
        row["dc_power_pct"] = round(sm["dc_power_pct"], 4)
        row["ac_power_pct"] = round(100.0 - sm["dc_power_pct"], 4)
        row["fixed"] = dict(**{k: (round(v, 2) if isinstance(v, float) else v)
                               for k, v in inst_stats(E, prf).items()}, **pack(sm))
        #  ⭐0 Hz(정지 동체)를 뺀 판 — 로터가 만든 변조만 남긴다
        row["fixed_ac"] = pack(spec_metrics(E, prf, ft, drop_dc=True))
        out["rows"].append(row)
    #  ⭐우리 커널(ours) 만 뽑아 «단조롭나» 를 두 잣대로 나란히 답한다
    ours = [r for r in out["rows"] if r["series"].startswith("ours/")]
    ours.sort(key=lambda r: -r["el_deg"])
    nad = [r for r in ours if r["el_deg"] == -90.0]
    out["monotonic_check"] = dict(
        el_deg=[r["el_deg"] for r in ours],
        legacy_unwrap_ptp_deg=[r["legacy"]["unwrap_ptp_deg"] for r in ours],
        legacy_edge20_over_ftip=[
            (round(r["legacy"]["edge20_hz"] / r["f_tip_pred_hz"], 3)
             if r["legacy"]["edge20_hz"] and r["f_tip_pred_hz"] > 1e-9 else None)
            for r in ours],
        amp_min_over_max=[r["amp_min_over_max"] for r in ours],
        ac_power_pct=[r["ac_power_pct"] for r in ours],
        ac_f_rms_hz=[r["fixed_ac"]["f_rms_hz"] for r in ours],
        ac_f_rms_over_pred=[r["fixed_ac"]["f_rms_over_pred"] for r in ours],
        ac_beyond_ftip_pct=[r["fixed_ac"]["beyond_ftip_pct"] for r in ours],
        nadir_ac_floor_pct=(nad[0]["ac_power_pct"] if nad else None),
        finding_ko=(
            "① 옛 «위상 변동폭» 이 튄 앙각(−30·−60)은 |E| 최소/최대 가 각각 0.055·0.005 로 "
            "**널이 가장 깊은** 두 자리와 정확히 겹친다 → 커널이 아니라 널이 만든 값이다. "
            "② 실제 기체 신호는 정지한 동체가 0 Hz 에 전력의 5~99.99% 를 몰아넣는다 — "
            "그 비중이 앙각마다 크게 달라지므로 **어떤 단일 스칼라도 cos(el) 을 곧바로 "
            "따라가지 않는다**. 운동학 검증은 이 스윕이 아니라 단위시험이 해야 한다. "
            "③ 직하방의 AC 비중이 이 데이터의 **격자 표본화 잡음 바닥**이다."),
        open_item_ko=("el −15° 의 AC 대역 밖 에너지 비율이 이웃보다 눈에 띄게 크다 — "
                      "이 라운드에서 원인을 규명하지 못했다. 미해결로 남긴다."))
    return out


# ═══ 그림 ═══════════════════════════════════════════════════════════════════
def figure():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    J = json.load(open(OUT_JSON))
    Z = np.load(OUT_NPZ)
    t = Z["t"]
    cases = J["cases"]
    cols = plt.cm.viridis(np.linspace(0.05, 0.85, len(ELS)))
    fig = plt.figure(figsize=(15.5, 10.4))
    gs = fig.add_gridspec(3, 3, hspace=0.42, wspace=0.27,
                          left=0.062, right=0.985, top=0.895, bottom=0.062)

    # (a) 순시 도플러 시계열 — 커널 vs 해석
    ax = fig.add_subplot(gs[0, :2])
    for c, el in zip(cols, ELS):
        Ek = Z[f"one_sphere/d48/el{el:+.0f}/kernel"]
        Ea = Z[f"one_sphere/d48/el{el:+.0f}/analytic"]
        ax.plot(t[:-1] * 1e3, inst_freq(Ek, PRF), color=c, lw=1.5,
                label=f"el = {el:+.0f}°")
        ax.plot(t[:-1] * 1e3, inst_freq(Ea, PRF), color="k", lw=0.9, ls=":", alpha=0.75)
    ax.axhline(0, color="0.5", lw=0.7)
    ax.set_xlabel("slow time [ms]"); ax.set_ylabel("instantaneous Doppler [Hz]")
    ax.set_title("(a) Wrap-safe instantaneous Doppler — kernel (color) vs analytic (dotted)",
                 fontsize=10.5, loc="left")
    ax.legend(fontsize=8, ncol=5, loc="upper center", framealpha=0.9)
    ax.grid(alpha=0.25)

    # (b) cos 법칙
    ax = fig.add_subplot(gs[0, 2])
    ce = np.linspace(0, 1, 100)
    ax.plot(ce, f_tip_pred(0.0) * ce, "k-", lw=1.2,
            label=r"analytic  $f_{tip}(0)\cos(el)$")
    mk = dict(zip(DIVS_ONE, ("o", "s", "^")))
    for div in DIVS_ONE:
        sub = sorted([c for c in cases
                      if c["target"] == "one_sphere" and c["div"] == div],
                     key=lambda c: c["cos_el"])
        ax.plot([c["cos_el"] for c in sub], [c["kernel"]["inst_f_p95_hz"] for c in sub],
                mk[div] + "-", ms=7, mfc="none", mew=1.6, lw=0.8,
                label=f"kernel  $\\lambda$/{div}")
    ax.set_xlabel(r"$\cos(el)$"); ax.set_ylabel(r"$|f_d|$  p95 [Hz]")
    ax.set_title("(b) cos(el) law", fontsize=10.5, loc="left")
    ax.legend(fontsize=8); ax.grid(alpha=0.25)

    # (c) 스펙트럼 — ⚠회전 조화(f_rev 배수) 빈만 그린다. 2 회전을 담았으므로 그 사이 빈은
    #     해석적으로 0 이고, 그걸 같이 그리면 톱니만 보인다(첫 판의 실수).
    def harm(E, step):
        S = np.abs(np.fft.fft(E)) / len(E)
        f = np.fft.fftfreq(len(E), 1.0 / PRF)
        o = np.argsort(f)
        S, f = S[o], f[o]
        j = int(np.argmin(np.abs(f)))                    # 0 Hz 를 기준으로 step 마다
        m = (np.arange(len(f)) - j) % step == 0
        return f[m], S[m]

    ax = fig.add_subplot(gs[1, :2])
    for c, el in zip(cols, ELS):
        f, S = harm(Z[f"one_sphere/d48/el{el:+.0f}/kernel"], 2)
        ax.plot(f, 20 * np.log10(S / S.max() + 1e-12), color=c, lw=1.2,
                label=f"el = {el:+.0f}°")
        for s in (-1, 1):
            ax.axvline(s * f_tip_pred(el), color=c, ls="--", lw=0.9, alpha=0.7)
    ax.set_xlim(-2200, 2200); ax.set_ylim(-75, 3)
    ax.set_xlabel("Doppler [Hz]"); ax.set_ylabel("normalised |E| [dB]")
    ax.set_title(r"(c) Spectrum (rotation harmonics) — dashed = analytic $\pm f_{tip}(el)$",
                 fontsize=10.5, loc="left")
    ax.legend(fontsize=8, ncol=5, loc="lower center"); ax.grid(alpha=0.25)

    # (d) 직하방 널 — 확대
    ax = fig.add_subplot(gs[1, 2])
    for div, ls in zip(DIVS_ONE, ("-", "--", ":")):
        Ek = Z[f"one_sphere/d{div}/el-90/kernel"]
        ax.plot(t[:-1] * 1e3, inst_freq(Ek, PRF), ls, lw=1.3,
                label=f"kernel $\\lambda$/{div}")
    ax.axhline(0, color="k", lw=1.4, label="analytic  = 0 exactly")
    ax.set_xlabel("slow time [ms]"); ax.set_ylabel("instantaneous Doppler [Hz]")
    ax.set_title("(d) Nadir (el = −90°): grid sampling floor", fontsize=10.5, loc="left")
    ax.legend(fontsize=8); ax.grid(alpha=0.25)

    # (e)(f) ⭐잣대 시연 — 2엽(널 있는) 표적
    el_d = -30.0
    Ek = Z[f"two_spheres/d12/el{el_d:+.0f}/kernel"]
    Ea = Z[f"two_spheres/d12/el{el_d:+.0f}/analytic"]
    ax = fig.add_subplot(gs[2, 0])
    ax.plot(t * 1e3, 20 * np.log10(np.abs(Ek) / np.abs(Ek).max()), lw=1.2, color="#1565c0",
            label="kernel")
    ax.plot(t * 1e3, 20 * np.log10(np.abs(Ea) / np.abs(Ea).max()), lw=0.9, color="k",
            ls=":", label="analytic")
    ax.set_xlabel("slow time [ms]"); ax.set_ylabel("|E| [dB, norm.]")
    ax.set_title(f"(e) Two-blade target, el = {el_d:+.0f}° — deep nulls", fontsize=10.5,
                 loc="left")
    ax.legend(fontsize=8); ax.grid(alpha=0.25)

    ax = fig.add_subplot(gs[2, 1])
    ax.plot(t * 1e3, np.unwrap(np.angle(Ek)) * 180 / np.pi, lw=1.2, color="#c62828",
            label="kernel")
    ax.plot(t * 1e3, np.unwrap(np.angle(Ea)) * 180 / np.pi, lw=0.9, color="k", ls=":",
            label="analytic (exact physics!)")
    ax.set_xlabel("slow time [ms]"); ax.set_ylabel("np.unwrap phase [deg]")
    ax.set_title("(f) The BROKEN metric: unwrap runs away on both", fontsize=10.5,
                 loc="left")
    ax.legend(fontsize=8); ax.grid(alpha=0.25)

    #  ⭐(g) 여기서는 순시주파수도 못 쓴다(다성분 신호). 답은 **스펙트럼**이다.
    ax = fig.add_subplot(gs[2, 2])
    fq, Sk = harm(Ek, 4)                                 # 2엽 → 반 회전이 주기 → 4 빈마다
    _, Sa = harm(Ea, 4)
    ax.plot(fq, 20 * np.log10(Sk / Sk.max() + 1e-12), lw=1.3, color="#2e7d32",
            label="kernel")
    ax.plot(fq, 20 * np.log10(Sa / Sa.max() + 1e-12), lw=0.9, color="k", ls=":",
            label="analytic")
    for s in (-1, 1):
        ax.axvline(s * f_tip_pred(el_d), color="0.35", ls="--", lw=1.0)
    ax.set_xlim(-2000, 2000); ax.set_ylim(-75, 3)
    ax.set_xlabel("Doppler [Hz]"); ax.set_ylabel("normalised |E| [dB]")
    ax.set_title(r"(g) The FIXED metric: spectral support, inside $\pm f_{tip}$",
                 fontsize=10.5, loc="left")
    ax.legend(fontsize=8); ax.grid(alpha=0.25)

    ok = sum(1 for g in J["gates"] if g["pass_"])
    fig.suptitle("Analytic unit test of the PO/SBR kernel — orbiting point scatterer, "
                 f"{FC/1e9:.1f} GHz, R = {RANGE_M:.0f} m, {RPM:.0f} rpm, r = {R_ORB*1e3:.0f} mm"
                 f"     [gates {ok}/{len(J['gates'])} pass]",
                 fontsize=12.5, y=0.968)
    fig.savefig(OUT_PNG, dpi=155)
    print(f"✅ {OUT_PNG}")


if __name__ == "__main__":
    if "--fig" in sys.argv:
        figure()
    else:
        run()
        figure()
