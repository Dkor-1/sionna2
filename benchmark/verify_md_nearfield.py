# -*- coding: utf-8 -*-
"""
verify_md_nearfield.py — 근거리장 마이크로도플러 모듈 검증 하네스
==================================================================
`src/microdoppler_nearfield.py` 가 신뢰할 만한지 **게이트로** 판정한다.
전 게이트 통과 전에는 `experiment_md_range.py` 의 어떤 수치도 인용 금지.

게이트 (전부 통과해야 gates_pass=True)
  G1 PLANE_EQ_REPO   평면파 팔 ≡ 저장소 기존 `microdoppler.microdoppler_series`
                     (같은 설정에서 AC 상관 ≥ 0.9999). — **회귀 잠금**: 새 코드가
                     기존 물리를 바꾸지 않았음을 증명한다.
  G2 CONVERGE        구면파 → 평면파 (R→∞). R=10 km 에서 |Δσ_eq| ≤ 0.05 dB, AC 상관 ≥ 0.9999.
                     ⭐ 이게 없으면 구면파 팔의 정규화가 틀린 것이다.
  G3 ROT_EXACT       회전 등가식 |A−(Rz(θ)P+C)| = |Rz(−θ)(A−C)−P| 수치 확인 (≤1e-12 m).
  G4 FRESNEL_RATE    평면파 대비 **레벨** 편차가 프레넬 항 ~1/R 로 줄어드는가.
                     R 을 10× 늘리면 |Δσ_eq|[dB] 가 단조 감소해야 한다.
                     ⚠ 최초 판 은 "단일자세 **패턴상관**도 단조" 를 함께 요구했고 **실패했다**
                     (ac_corr 0.537 → 0.256 @R=3 m → 0.883 → …). 코드가 아니라 **게이트 진술이
                     틀린 것**이었다 — 잡음변수 MC 에서 결합 prior 단조율 **65.7%**, 표면지터
                     λ/50 단독과 수신대역 단독은 **0.0%** 였다(세 번에 한 번 실패하는 것은
                     게이트가 아니다). R=3 m 는 R_ff=6.65 m 아래 **프레넬 영역**이고 거기서
                     널이 메워지며 로브가 비단조 이동하는 것은 기대 거동이다. 레벨은 그와
                     무관하게 깨끗이 단조다. 패턴상관은 **측정해 기록**만 하고, 참인 진술인
                     **자세평균** 쪽은 experiment_md_range 가 36자세로 검증한다.
  G5 FTIP_FF_INVAR   도플러 가장자리 f_edge 가 **원거리장(R ≥ R_ff) 구간에서 거리 불변**. 스프레드 ≤ 5%.
                     ⚠ 최초 판 은 "전 거리 불변" 이었고 **실패했다**(스프레드 0.114, R=1 m 만 이탈).
                     그건 코드 결함이 아니라 **게이트 진술이 틀린 것**이었다 — f_tip=2v_tip cos(el)/λ 는
                     평면파·원거리장에서 유도된 양이라 근거리장에는 그대로 적용되지 않는다.
                     근거리장 축소분은 게이트가 아니라 **측정값으로 별도 기록**한다(nearfield_rows).
  G6 NPHASE_CONV     n_phase 480 ↔ 960 에서 AC 상관 ≥ 0.999 (위상테이블 보간 충분).
  G7 SPACING_CONV    블레이드 점간격 λ/11 ↔ λ/22 에서 AC 상관 ≥ 0.99 (근거리장 R=1 m 에서).
                     ⚠ 근거리장은 표면 위상변화가 빨라 원거리장 간격 규칙이 부족할 수 있다.
  G8 FINITE          NaN/Inf 없음, DC/AC 유한.
  G9 PERIOD_ASSUMP   ⭐ 위상테이블 주기 가정 감사. 옛 규약 period=360/n_blades 가 1회전 테이블 대비
                     얼마나 틀리는지 **측정해 기록**한다(게이트는 1회전 테이블을 쓰는 이 모듈이
                     그 근사를 안 쓴다는 것만 확인). 프로펠러 점구름이 180° 자기대칭이 아니라
                     로터 회전수의 홀수 하모닉이 통째로 사라지는 문제 —
                     ⚠ **기존 `microdoppler.microdoppler_sbr` 가 이 근사를 쓴다**(report08 파급).

실행:  cd sionna2 && PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/verify_md_nearfield.py
산출:  outputs/verify_md_nearfield.json
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "src"))

from drones import DRONES                                   # noqa: E402
from radar_scene import target_extent                       # noqa: E402
import microdoppler as md_old                               # noqa: E402
import microdoppler_nearfield as nf                         # noqa: E402

OUT = os.path.join(_ROOT, "outputs", "verify_md_nearfield.json")

REF_DRONE = "mavic4pro"
FC = 3.5e9
AZ, EL = 0.0, 15.0
PRF, N_T = 20000.0, 6144


def _series(drone, R, wavefront, **kw):
    spec = DRONES[drone]
    return nf.microdoppler_nf(spec, FC, R, AZ, EL, wavefront=wavefront,
                              prf=PRF, n_t=N_T, **kw)


# --------------------------------------------------------------------------- #
def g1_plane_eq_repo():
    """평면파 팔이 저장소 기존 순수-PO 마이크로도플러와 같은가 (회귀 잠금)."""
    spec = DRONES[REF_DRONE]
    # 기존 구현: 같은 spacing 규약(frame λ/6, blade λ/11), blade_n=26
    t_o, E_o, i_o = md_old.microdoppler_series(spec, fc=FC, az=AZ, el=EL,
                                               prf=PRF, n_t=N_T, blade_n=26)
    # 신규 평면파 팔: 위상테이블을 촘촘히 (보간오차 배제), 1회전 주기
    _, E_n, i_n = _series(REF_DRONE, 10.0, "plane", n_phase=1440, period_deg=360.0)
    corr = nf.ac_correlation(E_o, E_n)
    # 절대 레벨도 비교 (전역 위상 무관하게 |E| 평균)
    lvl_db = float(20 * np.log10(np.mean(np.abs(E_n)) / np.mean(np.abs(E_o))))
    ok = bool(corr >= 0.9999 and abs(lvl_db) <= 0.5)
    return dict(name="PLANE_EQ_REPO", ok=ok, ac_corr=float(corr), level_delta_db=lvl_db,
                tol=dict(ac_corr=0.9999, level_db=0.5),
                note="신규 평면파 팔 ↔ microdoppler.microdoppler_series 회귀 잠금",
                f_tip_old=float(i_o["f_tip"]), f_tip_new=float(i_n["f_tip"]))


def g2_converge():
    """구면파 → 평면파 수렴 (R=10 km)."""
    _, Ep, ip = _series(REF_DRONE, 1e4, "plane")
    _, Es, isp = _series(REF_DRONE, 1e4, "spherical")
    d_db = float(10 * np.log10(isp["sigma_eq_mean_m2"] / ip["sigma_eq_mean_m2"]))
    corr = nf.ac_correlation(Ep, Es)
    ok = bool(abs(d_db) <= 0.05 and corr >= 0.9999)
    return dict(name="CONVERGE", ok=ok, R_m=1e4, d_sigma_db=d_db, ac_corr=float(corr),
                tol=dict(d_sigma_db=0.05, ac_corr=0.9999),
                note="구면파 정규화가 옳다면 원거리장에서 평면파와 같아야 한다")


def g3_rot_exact():
    """회전 등가식의 수치 정확성."""
    rng = np.random.default_rng(0)
    errs = []
    for _ in range(2000):
        P = rng.normal(size=3) * 0.2
        C = rng.normal(size=3) * 0.3
        A = rng.normal(size=3) * 50.0
        th = rng.uniform(0, 2 * np.pi)
        lhs = np.linalg.norm(A - (nf._rz(th) @ P + C))
        rhs = np.linalg.norm(nf._rz(-th) @ (A - C) - P)
        errs.append(abs(lhs - rhs))
        # 법선 내적도 로컬↔월드 동일해야 한다
    e = float(np.max(errs))
    # 법선 내적 등가
    nerrs = []
    for _ in range(2000):
        P = rng.normal(size=3) * 0.2
        n = rng.normal(size=3); n /= np.linalg.norm(n)
        C = rng.normal(size=3) * 0.3
        A = rng.normal(size=3) * 50.0
        th = rng.uniform(0, 2 * np.pi)
        R = nf._rz(th)
        Pw, nw = R @ P + C, R @ n
        uw = (A - Pw) / np.linalg.norm(A - Pw)
        Al = nf._rz(-th) @ (A - C)
        ul = (Al - P) / np.linalg.norm(Al - P)
        nerrs.append(abs(float(nw @ uw) - float(n @ ul)))
    ne = float(np.max(nerrs))
    ok = bool(e <= 1e-12 and ne <= 1e-12)
    return dict(name="ROT_EXACT", ok=ok, max_dist_err_m=e, max_ndotu_err=ne,
                tol=1e-12, n_trials=2000,
                note="블레이드 회전 ≡ 안테나 역회전 (근거리장에서도 엄밀)")


def g4_fresnel_rate():
    """**레벨** 편차가 R 과 함께 단조 감소하는가 (프레넬 항 소멸).

    ⚠ 2026-07-29 게이트 재서술 — 원래 이 게이트는 레벨 단조 **AND 단일자세 패턴상관 단조**를
      요구했고 **실패했다**(az=0·el=15·3.5 GHz 에서 ac_corr 0.537 → **0.256** @R=3 m → 0.883 → …).
      조사 결과 **코드가 아니라 게이트 진술이 틀린 것**이었다. 근거(400+600 draw 잡음변수 MC,
      `scratchpad/prior_out.json`):

        · 표면지터 λ/50(=1.7 mm 제작공차) 단독: 200 draw 중 **단조 0.0%**,
          Δ=corr(3)−corr(1) = **−0.284 ± 0.0025** — 산포가 거의 0 인 **결정론적** 특징이다.
        · 수신대역 U(3.45,3.55 GHz) 단독: 단조 **0.0%**.
        · 결합 prior(az·el ±1°, fc, 지터): 단조 **65.7%** → 이 게이트는 잡음변수만으로
          **세 번에 한 번 실패**한다. 그런 것은 게이트가 될 수 없다.

      물리적으로도 R=3 m 는 R_ff=6.65 m 아래의 **방사근거리장(프레넬 영역)** 이고, 그 구간에서
      패턴 널이 메워지고 로브가 비단조로 이동하는 것은 기대되는 거동이다. 레벨(Δσ)은 그와
      무관하게 ~1/R 로 깨끗이 단조 감소한다 — **그게 이 게이트가 원래 확인하려던 프레넬 주장**이다.

      → 단일자세 패턴상관은 **게이트에서 빼고 측정값으로 기록**한다(G5 가 f_tip 에 대해 이미
        쓰는 방식과 같다). 패턴상관의 참인 진술은 **자세평균**에서만 성립하며, 그건
        `src/experiment_md_range.py` 가 36자세로 이미 검증했다(AC 0.334±0.096 @1 m →
        0.995±0.004 @20 m). 리포트가 인용하는 것도 그 자세평균 쪽이다."""
    rows = []
    _, Ep, ip = _series(REF_DRONE, 10.0, "plane")
    p_lvl = ip["sigma_eq_mean_m2"]
    for R in (1.0, 3.0, 10.0, 30.0, 100.0, 1000.0, 10000.0):
        _, Es, isp = _series(REF_DRONE, R, "spherical")
        rows.append(dict(R_m=float(R),
                         d_sigma_db=float(10 * np.log10(isp["sigma_eq_mean_m2"] / p_lvl)),
                         ac_corr=float(nf.ac_correlation(Ep, Es))))
    dev = [abs(r["d_sigma_db"]) for r in rows]
    mono = all(dev[i] >= dev[i + 1] - 1e-9 for i in range(len(dev) - 1))
    # 측정만 하고 판정에는 넣지 않는다 (위 docstring 의 근거 참조)
    corr_mono = all(rows[i]["ac_corr"] <= rows[i + 1]["ac_corr"] + 1e-9 for i in range(len(rows) - 1))
    ok = bool(mono)
    return dict(name="FRESNEL_RATE", ok=ok, monotone_dev=bool(mono),
                monotone_corr_measured=bool(corr_mono),   # ← 판정 아님, 기록
                corr_dip_delta=float(rows[1]["ac_corr"] - rows[0]["ac_corr"]),
                rows=rows,
                r_ff_m=float(nf.farfield_range_m(target_extent(REF_DRONE), FC)),
                note=("판정 = **레벨** 편차 |Δσ| 가 R 과 함께 단조 감소(프레넬 항 ~1/R 소멸). "
                      "단일자세 패턴상관 단조는 **판정에서 제외**했다 — 잡음변수 MC 에서 결합 prior "
                      "단조율 65.7%, 지터·주파수 단독은 0.0% 로, 참이 아닌 진술이었다. "
                      "패턴상관의 참인 진술은 자세평균이며 experiment_md_range 가 검증한다."))


def g5_ftip_ff_invariant():
    """도플러 가장자리가 **원거리장 구간에서** 거리 불변인가.

    ⚠ 게이트 진술 교정 이력: 최초 판은 R=1 m 까지 포함해 "전 거리 불변" 을 요구했고 실패했다
    (스프레드 0.114). 원인은 코드가 아니라 게이트다 — f_tip = 2 v_tip cos(el)/λ 는
    **평면파·원거리장** 유도량이므로 근거리장에 강제할 근거가 없다.
    근거리장 축소분은 이 실험의 **결과**이지 위반이 아니므로 nearfield_rows 에 기록만 한다.
    """
    r_ff = float(nf.farfield_range_m(target_extent(REF_DRONE), FC))
    rows = []
    for R in (1.0, 2.0, 5.0, 10.0, 20.0, 50.0, 1000.0):
        _, Es, isp = _series(REF_DRONE, R, "spherical")
        m = nf.md_metrics(Es, PRF, flash_hz=isp["flash_hz"], f_tip=isp["f_tip"])
        rows.append(dict(R_m=float(R), in_farfield=bool(R >= r_ff),
                         fd_edge_hz=m["fd_edge_hz"],
                         flash_contrast_db=m["flash_contrast_db"],
                         f_tip_theory_hz=float(isp["f_tip"])))
    ff = np.array([r["fd_edge_hz"] for r in rows if r["in_farfield"]])
    spread = float((ff.max() - ff.min()) / max(ff.mean(), 1e-9)) if len(ff) else float("nan")
    ok = bool(len(ff) >= 2 and spread <= 0.05)
    nfr = [r for r in rows if not r["in_farfield"]]
    ref = float(ff.mean()) if len(ff) else float("nan")
    return dict(name="FTIP_FF_INVAR", ok=ok, r_ff_m=r_ff,
                farfield_edge_spread_frac=spread, tol=0.05, rows=rows,
                nearfield_rows=[dict(R_m=r["R_m"],
                                     fd_edge_hz=r["fd_edge_hz"],
                                     edge_shrink_frac=float(1.0 - r["fd_edge_hz"] / ref))
                                for r in nfr],
                note="원거리장에서 f_edge 불변을 강제. 근거리장 축소는 결과로 기록(게이트 아님)")


def g6_nphase_conv():
    rows = []
    for R in (1.0, 20.0):
        _, Ea, _ = _series(REF_DRONE, R, "spherical", n_phase=480)
        _, Eb, _ = _series(REF_DRONE, R, "spherical", n_phase=960)
        rows.append(dict(R_m=float(R), ac_corr=float(nf.ac_correlation(Ea, Eb))))
    ok = bool(all(r["ac_corr"] >= 0.999 for r in rows))
    return dict(name="NPHASE_CONV", ok=ok, rows=rows, tol=0.999,
                note="위상테이블 480 ↔ 960 (1회전 기준, 선형보간 아티팩트 점검)")


def g7_spacing_conv():
    rows = []
    for R in (1.0, 20.0):
        _, Ea, _ = _series(REF_DRONE, R, "spherical", blade_div=11.0, frame_div=6.0)
        _, Eb, _ = _series(REF_DRONE, R, "spherical", blade_div=22.0, frame_div=12.0)
        rows.append(dict(R_m=float(R), ac_corr=float(nf.ac_correlation(Ea, Eb))))
    ok = bool(all(r["ac_corr"] >= 0.99 for r in rows))
    return dict(name="SPACING_CONV", ok=ok, rows=rows, tol=0.99,
                note="근거리장은 표면 위상변화가 빨라 간격 규칙이 부족할 수 있다 — R=1 m 가 관건")


def g9_period_assumption():
    """⭐ 옛 규약 period=360/n_blades 의 오차를 **측정해 기록**한다.

    프로펠러 점구름이 180° 자기대칭이 아니라(삼각분할·바리센트릭 샘플링 비대칭),
    반주기 테이블은 로터 회전수의 **홀수 하모닉**을 통째로 버린다.
    이 모듈은 1회전 테이블을 쓰므로 근사를 안 쓴다 — 게이트는 그 사실만 확인한다.
    ⚠ 기존 `microdoppler.microdoppler_sbr` 는 반주기 규약을 쓴다(report08 파급).
    """
    from scipy.spatial import cKDTree
    from drones import build_propeller
    from rcs_po import mesh_to_points

    spec = DRONES[REF_DRONE]
    lam = nf.C0 / FC
    P, N, dA = mesh_to_points(build_propeller(spec, n=26), lam / 11.0)
    Rm = nf._rz(2 * np.pi / int(spec.prop_blades))
    d, _ = cKDTree(P).query(P @ Rm.T)
    sym = dict(p50_mm=float(1e3 * np.median(d)), p95_mm=float(1e3 * np.percentile(d, 95)),
               max_mm=float(1e3 * d.max()), max_over_lam=float(d.max() / lam),
               roundtrip_phase_deg=float(np.degrees(2 * (2 * np.pi / lam) * d.max())))

    # 반주기 테이블 ↔ 1회전 테이블 비교 (같은 φ 해상도)
    half = 360.0 / int(spec.prop_blades)
    _, E_half, _ = _series(REF_DRONE, 10.0, "spherical", n_phase=240, period_deg=half)
    _, E_full, _ = _series(REF_DRONE, 10.0, "spherical", n_phase=480, period_deg=360.0)
    corr = float(nf.ac_correlation(E_half, E_full))
    lost = float(1.0 - corr ** 2)
    return dict(name="PERIOD_ASSUMP", ok=True,
                module_period_deg=360.0, legacy_period_deg=half,
                pointcloud_symmetry=sym, ac_corr_half_vs_full=corr,
                ac_power_lost_frac=lost,
                note="이 모듈은 1회전 테이블(근사 없음). 위 수치는 옛 반주기 규약의 오차 측정치.")


def g8_finite():
    bad = []
    for R in (1.0, 5.0, 10.0, 20.0):
        for wv in nf.WAVEFRONTS:
            _, E, i = _series(REF_DRONE, R, wv, n_phase=240)
            if not np.all(np.isfinite(E)) or not np.isfinite(i["sigma_eq_mean_m2"]):
                bad.append(f"{wv}@{R}m")
    return dict(name="FINITE", ok=(len(bad) == 0), bad=bad)


GATES = [g1_plane_eq_repo, g2_converge, g3_rot_exact, g4_fresnel_rate,
         g5_ftip_ff_invariant, g6_nphase_conv, g7_spacing_conv, g8_finite,
         g9_period_assumption]


def main():
    t0 = time.time()
    checks = {}
    for fn in GATES:
        t1 = time.time()
        try:
            r = fn()
        except Exception as exc:                       # noqa: BLE001
            r = dict(name=fn.__name__, ok=False, error=f"{type(exc).__name__}: {exc}")
        r["seconds"] = round(time.time() - t1, 2)
        checks[r["name"]] = r
        flag = "PASS" if r.get("ok") else "FAIL"
        print(f"[{flag}] {r['name']:16s} ({r['seconds']:6.1f} s)"
              + (f"  err={r['error']}" if "error" in r else ""))

    doc = dict(
        meta=dict(generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
                  module="src/microdoppler_nearfield.py",
                  ref_drone=REF_DRONE, fc_hz=FC, az_deg=AZ, el_deg=EL,
                  prf_hz=PRF, n_t=N_T,
                  r_ff_m=float(nf.farfield_range_m(target_extent(REF_DRONE), FC)),
                  runtime_s=round(time.time() - t0, 1)),
        checks=checks,
        summary=dict(n_checks=len(checks),
                     n_fail=sum(0 if c.get("ok") else 1 for c in checks.values()),
                     gates_pass=all(bool(c.get("ok")) for c in checks.values())),
    )
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    tmp = OUT + ".tmp"
    with open(tmp, "w") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
    os.replace(tmp, OUT)
    print(f"\ngates_pass={doc['summary']['gates_pass']}  "
          f"({doc['summary']['n_checks'] - doc['summary']['n_fail']}"
          f"/{doc['summary']['n_checks']})  → {OUT}")
    return 0 if doc["summary"]["gates_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
