# -*- coding: utf-8 -*-
"""
verify_sbr_defect_fixes.py — **SBR 커널 결함 3건(D2·D3·D4) 정정의 계측**
=============================================================================
2026-07-30 적대검증에서 확정된 커널 결함 세 가지를 고치고, **고쳤다는 주장을 숫자로 남긴다**.
리포트는 이 파일이 쓰는 `outputs/sbr_defect_fixes.json` 에서만 숫자를 주입할 것(손으로 적지 말 것).

  D3 다중반사 위상 — `rcs_sbr()` 의 위상이 **도착 세그먼트를 빠뜨린** 값을 쓰고 있었다.
     과녁: PEC 직각 이면반사체 σ = 8πa²b²/λ² (구·평판은 볼록이라 이 결함을 **진단 못 한다**).
  D2 상반성 — σ(û_i,û_s) ≠ σ(û_s,û_i). 상반성은 **정리**이므로 위반은 전부 모형오차다.
     `symmetrize=True` (σ_sym=√(σ(i,s)σ(s,i))) 를 옵트인으로 넣고, **정말 줄어드는지 아니면
     두 틀린 값을 평균해 가리는 것뿐인지**를 구분해서 잰다.
  D4 출사 가시성 — 수신 게이트가 법선 판정뿐이라, 수신기를 향하지만 기체에 **가려진** 면이
     100% 진폭으로 계상됐다. 히트점마다 û_s 로 그림자광선을 1발 쏘도록 고쳤다(기본 ON).

■ D2 를 정직하게 가르는 방법 — **평판(볼록·해석 가능)** 을 먼저 쓴다
  평면 판 하나에서는 커널의 비대칭이 닫힌형으로 나온다. 조명 격자를 û_i 로 쏘면 히트 밀도가
  투영면적을 재므로
      E(i,s) = ∫ e^{jk(û_i+û_s)·p} (n̂·û_i) dS,   E(s,i) = ∫ e^{jk(û_i+û_s)·p) (n̂·û_s) dS
  위상항이 **같고** obliquity 만 다르다 → σ(i,s)/σ(s,i) = (cosθ_i/cosθ_s)² 가 **정확히** 예측된다.
  그리고 그 기하평균은 √((n̂·û_i)(n̂·û_s)) 라는 **상반성을 복원하는 대칭 obliquity** 와 정확히
  같은 답이다 — 광선별로 그 비를 곱하려던 옛 시도가 grazing 에서 폭발했던 것과 달리, 적분 뒤
  σ 레벨에서 기하평균을 내면 특이점이 없다. 즉 **평판에서는 대칭화가 '가리는' 것이 아니라
  알려진 위반원인을 정확히 제거한다**.
  비볼록 기체에서는 여기에 게이트·가림·단일조명격자 재사용에서 오는 성분이 더해지고, 그 성분의
  부호는 알 수 없다 → 그 부분에 대해서는 대칭화가 **상반성 성질만 보장**할 뿐 정확도 개선의
  증거가 없다. 이 스크립트는 두 성분을 나눠서 보고한다.

실행:  cd sionna2 && SIONNA2_GPU=2 PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python \
         benchmark/verify_sbr_defect_fixes.py
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (os.path.join(_ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np                                          # noqa: E402

import rcs_sbr as rsb                                          # noqa: E402
from rcs_sbr import (C0, rcs_sbr_multistatic, validate, _look,   # noqa: E402
                     _PEC_GROUP_MAT)
from geom import quad                                       # noqa: E402

OUT = os.path.join(_ROOT, "outputs", "sbr_defect_fixes.json")

DIV = 16          # ★report2·experiment_freespace_sigma 와 동일
JITTER = 2        # 생산 기본값
EL = -2.0         # 생산 멀티스태틱 점검과 동일한 고도각
BETA = (0, 15, 30, 45, 60, 75, 90)


def _db(x):
    return float(10.0 * np.log10(max(float(x), 1e-30)))


def _rotate_toward(u, beta_deg):
    """û 를 임의 수직축 둘레로 β[deg] 회전(experiment_freespace_sigma 와 같은 규약)."""
    u = np.asarray(u, float) / np.linalg.norm(u)
    tmp = np.array([0.0, 0.0, 1.0]) if abs(u[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    e = np.cross(u, tmp); e /= np.linalg.norm(e)
    b = np.radians(beta_deg)
    return u * np.cos(b) + e * np.sin(b)


# --------------------------------------------------------------------------- #
#  D3 — 다중반사 위상: 이면반사체 해석해 대조
# --------------------------------------------------------------------------- #
def d3_dihedral(fc=3.5e9, verbose=True):
    """`validate()` 의 [3] 절을 그대로 재사용해 JSON 으로 남긴다(숫자 출처 단일화)."""
    r = validate(fc=fc, verbose=verbose)
    rows = []
    for a in (0.15, 0.20, 0.30, 0.40):
        rows.append(dict(a_m=a,
                         exact_dbsm=r[f"dihedral_a{a}_exact_dbsm"],
                         sbr_1bounce_dbsm=r[f"dihedral_a{a}_b1_dbsm"],
                         sbr_2bounce_dbsm=r[f"dihedral_a{a}_b2_dbsm"],
                         err_2bounce_db=r[f"dihedral_a{a}_b2_err_db"]))
    from rcs_sbr import DEFAULT_DIV
    return dict(fc_hz=float(fc), div=int(DEFAULT_DIV),
                exact_formula="sigma = 8*pi*a^2*b^2/lambda^2 (bisector incidence, a=b)",
                rows=rows,
                max_abs_err_db=float(max(abs(x["err_2bounce_db"]) for x in rows)),
                sphere_and_plate=dict(
                    sphere_vs_po_db={k: float(v) for k, v in r.items() if k.startswith("sphere_lam/") and k.endswith("_vs_po")},
                    plate_db={k: float(v) for k, v in r.items() if k.startswith("plate_lam/")}))


# --------------------------------------------------------------------------- #
#  D2 — 상반성: (a) 평판(해석 예측) (b) 기체(잔여 성분)
# --------------------------------------------------------------------------- #
def d2_plate(fc=3.5e9, a=0.08, div=32, beta=tuple(range(5, 76, 5)), verbose=True):
    """평면 PEC 판: 커널의 상반성 위반이 **(cosθ_i/cosθ_s)² 로 정확히 예측**되는가.

    û_i = ẑ(수직입사) 고정, û_s 를 x–z 면에서 β 만큼 벌린다 → 예측 10log10 비 = −20log10(cos β).

    ■ 판 크기를 왜 **작게**(a=0.08 m ≈ 0.93λ) 잡는가 — 시행착오의 기록
      처음엔 검증용 0.4 m 판을 썼는데, 바이스태틱 패턴 sinc(πa·sinβ/λ) 의 널이
      sinβ = mλ/a 에서 촘촘히 서고(12.4°/25.4°/40.0°/58.9°) 그 바닥에서는 두 방향의 격자
      샘플링 차이가 신호보다 커져 비가 무의미해진다(β=60° 에서 잔차 +20.7 dB, β=85° 에서
      +43.4 dB — 예측이 틀린 게 아니라 **두 값 모두 널 바닥의 수치잡음**이었다).
      a < λ 로 줄이면 λ/a > 1 이라 **0~90° 안에 널이 하나도 없다** → 패턴이 매끄러워
      obliquity 비만 남는다.

    ⚠ 큰 β 에서는 **역방향 기하의 개구가 몇 셀 안 된다**(투영폭 a·cosβ). 그 자체가 이 커널의
      실제 한계이므로 숨기지 않고 `cells_across_reverse` 로 같이 적는다."""
    plate = quad((-a / 2, -a / 2, 0), (a / 2, -a / 2, 0), (a / 2, a / 2, 0), (-a / 2, a / 2, 0),
                 group="metal")
    lam = C0 / fc
    d = lam / float(div)
    ui = np.array([0.0, 0.0, 1.0])
    rows = []
    for b in beta:
        us = np.array([np.sin(np.radians(b)), 0.0, np.cos(np.radians(b))])
        ck = ("plate_d2", round(fc / 1e6))
        s_is = float(np.atleast_1d(np.asarray(rcs_sbr_multistatic(
            plate, _PEC_GROUP_MAT, fc, ui, [us], spacing=d, penetrate=False,
            jitter=JITTER, cache_key=ck), float))[0])
        s_si = float(np.atleast_1d(np.asarray(rcs_sbr_multistatic(
            plate, _PEC_GROUP_MAT, fc, us, [ui], spacing=d, penetrate=False,
            jitter=JITTER, cache_key=ck), float))[0])
        s_sym = float(np.atleast_1d(np.asarray(rcs_sbr_multistatic(
            plate, _PEC_GROUP_MAT, fc, ui, [us], spacing=d, penetrate=False,
            jitter=JITTER, symmetrize=True, cache_key=ck), float))[0])
        meas = _db(s_is) - _db(s_si)
        pred = -20.0 * np.log10(np.cos(np.radians(b)))
        x = np.pi * a * np.sin(np.radians(b)) / lam          # 판 바이스태틱 패턴 sinc 인자
        pat = 20.0 * np.log10(max(abs(np.sinc(x / np.pi)), 1e-12))   # 첨두(β=0) 대비 dB
        rows.append(dict(beta_deg=int(b), sigma_is_dbsm=_db(s_is), sigma_si_dbsm=_db(s_si),
                         sigma_sym_dbsm=_db(s_sym), violation_db=meas,
                         predicted_db=float(pred), residual_db=float(meas - pred),
                         pattern_db=float(pat),
                         cells_across_reverse=float(a * np.cos(np.radians(b)) / d),
                         sym_minus_geomean_db=float(_db(s_sym) - 0.5 * (_db(s_is) + _db(s_si)))))
        if verbose:
            print(f"  [D2·평판] β={b:3d}°  위반 {meas:+8.3f} dB  예측 {pred:+7.3f} dB  "
                  f"잔차 {meas - pred:+8.3f} dB  (패턴 {pat:+6.1f} dB · 역방향 "
                  f"{rows[-1]['cells_across_reverse']:.1f} 셀)")
    has_null = bool(lam / a <= 1.0)
    return dict(target=f"PEC flat plate {a}x{a} m ({a/lam:.2f} lambda)", fc_hz=float(fc), div=int(div),
                prediction="10log10(sigma(i,s)/sigma(s,i)) = -20log10(cos beta)",
                pattern_has_null_in_0_90=has_null, rows=rows,
                max_abs_residual_db=float(max(abs(r["residual_db"]) for r in rows)),
                rms_residual_db=float(np.sqrt(np.mean([r["residual_db"] ** 2 for r in rows]))),
                max_sym_minus_geomean_db=float(max(abs(r["sym_minus_geomean_db"]) for r in rows)),
                max_abs_residual_db_beta_le_60=float(max(
                    abs(r["residual_db"]) for r in rows if r["beta_deg"] <= 60)),
                sampling_note=("beta>=65 에서 잔차가 커지는 것은 예측이 틀려서가 아니라 역방향 "
                               "기하의 투영개구가 a*cos(beta)/d 셀로 줄어 격자 양자화가 지배하기 "
                               "때문이다(cells_across_reverse 참조)."),
                verdict=("평판(볼록·널 없음)에서 커널의 상반성 위반은 obliquity 비 "
                         "(cos_i/cos_s)^2 로 설명된다 → 기하평균은 대칭 obliquity "
                         "sqrt((n.u_i)(n.u_s)) 와 같은 답이며, 이 경우 대칭화는 '가리기'가 아니라 "
                         "알려진 위반원인의 제거다."))


def d2_drone(drone="mavic4pro", fc=3.5e9, n_az=12, exit_vis=True, verbose=True):
    """기체(비볼록): β 스윕으로 상반성 위반 rms·최악, 대칭화 전/후.

    exit_vis 를 함께 재는 이유: **D4 자체가 상반성 위반을 줄인다**. 출사 가시성을 넣으면
    기여하는 면 집합이 '입사로도 뚫려 있고 출사로도 뚫려 있는 면' 이 되어 i↔s 교환에 대해
    **대칭**이 된다. 법선 판정만 있던 옛 게이트는 입사 가림만 보므로 비대칭이었다."""
    from drones import DRONES, build_drone
    from channel import _group_mat
    mesh = build_drone(DRONES[drone])
    gm = _group_mat(drone)
    lam = C0 / fc
    az = np.linspace(0.0, 360.0, int(n_az), endpoint=False)
    rows = []
    for b in BETA:
        v_raw, v_sym, s_fwd, s_rev = [], [], [], []
        for a in az:
            ui = _look(a, EL)
            us = _rotate_toward(ui, b)
            kw = dict(spacing=lam / DIV, penetrate=True, jitter=JITTER, exit_vis=exit_vis,
                      cache_key=(drone, round(fc / 1e6)))
            f = float(np.atleast_1d(np.asarray(
                rcs_sbr_multistatic(mesh, gm, fc, ui, [us], **kw), float))[0])
            rv = float(np.atleast_1d(np.asarray(
                rcs_sbr_multistatic(mesh, gm, fc, us, [ui], **kw), float))[0])
            sy = float(np.atleast_1d(np.asarray(
                rcs_sbr_multistatic(mesh, gm, fc, ui, [us], symmetrize=True, **kw), float))[0])
            sy2 = float(np.atleast_1d(np.asarray(
                rcs_sbr_multistatic(mesh, gm, fc, us, [ui], symmetrize=True, **kw), float))[0])
            v_raw.append(_db(f) - _db(rv))
            v_sym.append(_db(sy) - _db(sy2))
            s_fwd.append(_db(f)); s_rev.append(_db(rv))
        v_raw = np.asarray(v_raw); v_sym = np.asarray(v_sym)
        rows.append(dict(beta_deg=int(b), n_az=int(n_az),
                         rms_db=float(np.sqrt(np.mean(v_raw ** 2))),
                         worst_db=float(np.max(np.abs(v_raw))),
                         rms_sym_db=float(np.sqrt(np.mean(v_sym ** 2))),
                         worst_sym_db=float(np.max(np.abs(v_sym))),
                         median_abs_db=float(np.median(np.abs(v_raw))),
                         mean_sigma_fwd_dbsm=float(np.mean(s_fwd)),
                         mean_sigma_rev_dbsm=float(np.mean(s_rev))))
        if verbose:
            r = rows[-1]
            print(f"  [D2·{drone}·exit_vis={int(exit_vis)}] β={b:3d}°  위반 rms {r['rms_db']:6.3f}"
                  f" / 최악 {r['worst_db']:7.3f} dB"
                  f"   → 대칭화 후 rms {r['rms_sym_db']:.2e} / 최악 {r['worst_sym_db']:.2e} dB")
    return dict(drone=drone, fc_hz=float(fc), div=DIV, el_deg=EL, exit_vis=bool(exit_vis), rows=rows,
                rms_range_db=[float(min(r["rms_db"] for r in rows)),
                              float(max(r["rms_db"] for r in rows))],
                worst_db=float(max(r["worst_db"] for r in rows)),
                worst_after_symmetrize_db=float(max(r["worst_sym_db"] for r in rows)),
                honest_note=("대칭화는 σ_sym(i,s)=σ_sym(s,i) 를 구성상 정확히 만든다(잔차 ~1e-14 dB, "
                             "부동소수 수준). 그러나 두 평가값의 dB 차이(=위반량)는 그대로다 — "
                             "평판처럼 위반원인이 알려진 경우에만 '제거' 이고, 기체의 잔여 성분에 "
                             "대해서는 '상반성 성질 보장' 일 뿐 정확도 개선의 증거가 아니다."))


# --------------------------------------------------------------------------- #
#  D4 — 출사 가시성
# --------------------------------------------------------------------------- #
def d4_exit_visibility(drones=("mavic4pro", "mini5pro", "s1000plus"), fc=3.5e9,
                       n_az=12, verbose=True):
    """exit_vis ON/OFF 의 Δσ(β) — β 가 커질수록 음의 보정이 커져야 한다."""
    from drones import DRONES, build_drone
    from channel import _group_mat
    lam = C0 / fc
    az = np.linspace(0.0, 360.0, int(n_az), endpoint=False)
    out = {}
    for drone in drones:
        mesh = build_drone(DRONES[drone])
        gm = _group_mat(drone)
        on = np.zeros((len(az), len(BETA)))
        off = np.zeros_like(on)
        for i, a in enumerate(az):
            ui = _look(a, EL)
            us_list = [_rotate_toward(ui, b) for b in BETA]
            for tag, arr, ev in (("on", on, True), ("off", off, False)):
                s = np.atleast_1d(np.asarray(rcs_sbr_multistatic(
                    mesh, gm, fc, ui, us_list, spacing=lam / DIV, penetrate=True,
                    jitter=JITTER, exit_vis=ev, cache_key=(drone, round(fc / 1e6))), float))
                arr[i] = [_db(v) for v in s]
        d = on - off
        rows = []
        for j, b in enumerate(BETA):
            rows.append(dict(beta_deg=int(b),
                             mean_delta_db=float(np.mean(d[:, j])),
                             median_delta_db=float(np.median(d[:, j])),
                             worst_delta_db=float(np.min(d[:, j])),
                             p95_abs_delta_db=float(np.percentile(np.abs(d[:, j]), 95)),
                             sigma_exit_on_dbsm=float(np.mean(on[:, j])),
                             sigma_exit_off_dbsm=float(np.mean(off[:, j]))))
        out[drone] = dict(rows=rows, n_az=int(n_az),
                          monostatic_noop_max_abs_db=float(np.max(np.abs(d[:, 0]))))
        if verbose:
            print(f"  [D4·{drone}] " + "  ".join(
                f"β{r['beta_deg']}:{r['mean_delta_db']:+.2f}" for r in rows)
                + f"   (β=0 no-op 최대 {out[drone]['monostatic_noop_max_abs_db']:.1e} dB)")
    return dict(fc_hz=float(fc), div=DIV, el_deg=EL, by_drone=out,
                clearance_m=float(rsb.EXIT_CLEARANCE), cosmin=float(rsb.EXIT_COSMIN),
                note=("Δ = 10log10(sigma_exit_vis_on / sigma_off). β=0(모노)에서 0 이어야 한다 — "
                      "first-hit 이 이미 그 가림을 뺐으므로(Sagitta arXiv:2604.09243 각주 1)."))


def d4_epsilon_sensitivity(drones=("mavic4pro", "s1000plus"), fc=3.5e9, n_az=8, verbose=True):
    """그림자광선 여유(clearance)·cos 하한을 10배씩 흔들어도 Δσ 가 흔들리지 않는가.

    가시성 판정이 **임의의 수치 노브에 지배되지 않음**을 보이는 게이트다."""
    from drones import DRONES, build_drone
    from channel import _group_mat
    lam = C0 / fc
    az = np.linspace(0.0, 360.0, int(n_az), endpoint=False)
    base = (rsb.EXIT_CLEARANCE, rsb.EXIT_COSMIN)
    combos = ((1e-5, 0.02), (3e-5, 0.02), (1e-4, 0.02), (1e-5, 0.05), (1e-5, 0.005))
    betas = (0, 30, 60, 90)
    rows = []
    try:
        for cl, cm in combos:
            rsb._exit_visible.__defaults__ = (cl, cm)
            rec = dict(clearance_m=cl, cosmin=cm, by_drone={})
            for drone in drones:
                mesh = build_drone(DRONES[drone])
                gm = _group_mat(drone)
                dd = []
                for a in az:
                    ui = _look(a, EL)
                    usl = [_rotate_toward(ui, b) for b in betas]
                    x = np.asarray(rcs_sbr_multistatic(mesh, gm, fc, ui, usl, spacing=lam / DIV,
                                                       penetrate=True, jitter=JITTER, exit_vis=True,
                                                       cache_key=(drone, round(fc / 1e6))), float)
                    y = np.asarray(rcs_sbr_multistatic(mesh, gm, fc, ui, usl, spacing=lam / DIV,
                                                       penetrate=True, jitter=JITTER, exit_vis=False,
                                                       cache_key=(drone, round(fc / 1e6))), float)
                    dd.append(10 * np.log10(x / y))
                dd = np.asarray(dd)
                rec["by_drone"][drone] = dict(
                    beta_deg=list(betas),
                    mean_delta_db=[float(v) for v in dd.mean(0)],
                    monostatic_noop_max_abs_db=float(np.max(np.abs(dd[:, 0]))))
            rows.append(rec)
    finally:
        rsb._exit_visible.__defaults__ = base
    spread = {}
    for drone in drones:
        arr = np.array([r["by_drone"][drone]["mean_delta_db"] for r in rows])
        spread[drone] = dict(beta_deg=list(betas),
                             max_spread_db=[float(v) for v in (arr.max(0) - arr.min(0))])
    if verbose:
        for drone, v in spread.items():
            print(f"  [D4·감도] {drone}: 노브 10배 변화에도 Δσ 산포 "
                  + " ".join(f"β{b}:{s:.3f}" for b, s in zip(v['beta_deg'], v['max_spread_db'])) + " dB")
    return dict(combos=rows, spread=spread, n_az=int(n_az),
                max_spread_db=float(max(max(v["max_spread_db"]) for v in spread.values())))


def main():
    res = {"meta": dict(generated_by="benchmark/verify_sbr_defect_fixes.py",
                        div=DIV, jitter=JITTER, el_deg=EL, beta_deg=list(BETA))}
    print("=" * 82)
    print("D3 — 다중반사 위상 (이면반사체 해석해 σ=8πa²b²/λ²)")
    print("=" * 82)
    res["d3_multibounce_phase"] = d3_dihedral()
    print("\n" + "=" * 82)
    print("D2 — 상반성 (평판: 해석 예측 / 기체: 잔여)")
    print("=" * 82)
    res["d2_reciprocity_plate"] = d2_plate()
    res["d2_reciprocity_drone"] = d2_drone(exit_vis=True)
    res["d2_reciprocity_drone_no_exit_vis"] = d2_drone(exit_vis=False)
    _a, _b = res["d2_reciprocity_drone"], res["d2_reciprocity_drone_no_exit_vis"]
    res["d2_exit_vis_effect_on_reciprocity"] = dict(
        beta_deg=[r["beta_deg"] for r in _a["rows"]],
        rms_with_exit_vis_db=[r["rms_db"] for r in _a["rows"]],
        rms_without_exit_vis_db=[r["rms_db"] for r in _b["rows"]],
        worst_with_exit_vis_db=_a["worst_db"], worst_without_exit_vis_db=_b["worst_db"],
        note=("출사 가시성을 켜면 기여 면 집합이 i<->s 교환에 대칭이 되므로 상반성 위반이 "
              "줄어야 한다. D4 정정이 D2 결함도 부분적으로 갚는다는 뜻이다."))
    print("\n" + "=" * 82)
    print("D4 — 출사 가시성")
    print("=" * 82)
    res["d4_exit_visibility"] = d4_exit_visibility()
    res["d4_epsilon_sensitivity"] = d4_epsilon_sensitivity()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(res, fh, indent=1, ensure_ascii=False)
    print(f"\n→ {OUT}")
    return res


if __name__ == "__main__":
    main()
