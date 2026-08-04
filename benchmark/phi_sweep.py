# -*- coding: utf-8 -*-
"""
phi_sweep.py — ⭐ 장면방위 φ 를 쓸어 "기하는 링크버짓에 영향 없다" 가 φ=90° 의 산물인지 판정한다
=================================================================================================

■ 왜 (docs/DECK_FACTS.md F27 · G5, docs/GEOMETRY_BENCHMARK.md 표 6행)
  발표된 검출 결과가 **전부 φ=90° 한 컷**이다. φ=90° 는 베이스라인 TX—RX 의 **수직이등분선**이라
  R1≈R2 가 **구조적으로** 성립한다 — 두 기하(모노/바이)의 확산항 차가 나타날 수 없는 유일한 방위다.
  실측(outputs/geometry_grid.json:range_normalisation): |Δspread| = 0.118 dB @φ=90° vs 23.17 dB @φ=180°.

■ φ 의 정의 (freespace_scene.target_pos)
      O = (TX+RX)/2 = (L/2, 0, ·)        TX=(0,0,25) · RX=(L,0,3) · L=500 m
      P(d,φ) = (L/2 + d·cosφ, d·sinφ, alt)
  즉 φ 는 **베이스라인 중점 O 를 원점**으로 한 **수평면 방위각**이고, **0° 는 TX→RX 방향(+x)**,
  **90° 는 베이스라인의 수직이등분선**, **180° 는 TX 너머**다. d 는 O 에서 표적까지의 **수평거리**이지
  R1·R2·Rb 어느 것도 아니다. φ 와 360−φ 는 y 에 대한 거울상이라 **기하는 동일**하고,
  σ 조회 방위 az_look 만 부호가 뒤집힌다(σ 자세 패턴의 비대칭만 남는다).

■ 무엇을 다시 계산하나 — **기하만**. GPU 0 회.
  · σ 격자(outputs/report13_sigma_grid.json)는 **읽기만** 한다. φ 가 바꾸는 것은 조회 좌표
    (az_look, el_look) 이지 격자 자체가 아니다.
  · 검출기 전이곡선 SNR90 도 재사용한다 — Pd 는 **출력 SNR 의 함수**라 거리·방위 불변이다
    (experiment_freespace_range 모듈 docstring 함정 1).
  · 즉 이 스윕은 닫힌형이고, 문서가 예상한 "GPU 1~4시간" 은 실제로는 **CPU 수 분**이다.

■ 세 팔
  A. sigma_grid  : σ 를 격자에서 조회(정본 경로). ⚠ 격자 el 행이 0~−20° 뿐이라 φ 가 0/180° 로
                   갈수록 이등분선 앙각이 격자 밖으로 떨어져 **클램프**된다 → 팔 C 가 그 통제군.
  B. sigma_fixed : σ ≡ 0.01 m² 고정(격자 미사용). **순수 기하** 통제군 — 여기서 남는 φ 의존은
                   전부 R1·R2·β·게이트 때문이다.
  C. geometry    : σ·파형과 무관한 기하 사실 — N2/N3 확산항 차(모노 vs 바이), R1/R2, β, el_look.
                   benchmark/geometry_grid.py 의 7점 φ 목록을 72점으로 조밀화한 것이다.

실행: CUDA_VISIBLE_DEVICES="" PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/phi_sweep.py
산출: outputs/phi_sweep.json · outputs/figs/phi_sweep.png
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (os.path.join(ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")     # 닫힌형 — GPU 를 잡지 않는다

import numpy as np                                                     # noqa: E402

import experiment_freespace_range as R                                 # noqa: E402
import freespace_scene as FS                                           # noqa: E402
import freespace_link as FL                                            # noqa: E402

OUT_JSON = os.path.join(ROOT, "outputs", "phi_sweep.json")
OUT_FIG = os.path.join(ROOT, "outputs", "figs", "phi_sweep.png")

# ── 스윕 규약 ─────────────────────────────────────────────────────────────────
#  φ 격자: 5° 간격 전원(72점). 왜 이 점들인가 —
#   · **전원(0~355°)**: φ 와 360−φ 는 기하가 같으므로 절반이면 충분하지만, σ 조회 방위 az_look 이
#     부호를 뒤집으므로 **σ 자세 패턴의 비대칭**을 보려면 한 바퀴가 필요하다(대칭성 자체가 검사항목).
#   · **5° 간격**: 확산항이 φ→0/180° 에서 급격히 벌어지므로 성긴 격자면 최대값을 놓친다.
#   · **90° 포함**: 발표 수치와 같은 컷을 반드시 격자에 넣어 옛 숫자를 대조한다.
#   · **0/30/60/90/120/150/180 포함**: geometry_grid.py 의 7점과 교차검증한다.
#  (최소 요구는 3점이었다. 닫힌형이라 한 팔이 ~30 s 라 72점을 전부 돌린다.)
PHI_GRID = [float(v) for v in range(0, 360, 5)]
MODES = ("W1", "L1", "G1")                # 상시 3인방: WiFi VHT-LTF · LTE CRS · 5G SSB
DRONES = ("mini5pro", "mavic4pro", "s1000plus")
L_REF = float(FS.L_REF)                   # 500 m
ALT = float(FS.FS_ALT[0])                 # 60 m
D_GRID = np.geomspace(100.0, 20000.0, 240)
D_FIXED = 1000.0                          # 고정 장면거리(순위 비교용) — R90 역해와 독립인 지표
MONO_NODE = FS.FS_TX                      # 모노 노드 = 조명원 자리(geometry_grid.py 와 동일 규약)

#  SNR90 — **발표된 정본 실행(outputs/report13_freespace.json)의 측정값을 그대로 쓴다.**
#  그 실행은 modes[0]=W1 의 전이곡선 값을 세 모드에 공통으로 넣었다(main() 의 snr90 추출 경로).
#  같은 값을 쓰면 φ 차이가 **순수 기하**에서만 온다. 모드별 측정값도 meta 에 함께 남긴다.
SNR90_PUBLISHED_DB = 11.86143572621035


def _load(p):
    try:
        with open(p) as f:
            return json.load(f)
    except Exception:
        return None


def _git_rev():
    try:
        return subprocess.check_output(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"],
                                       stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return ""


# --------------------------------------------------------------------------- #
#  팔 C — 기하만 (σ·파형 무관).  geometry_grid.py:259-290 의 N2/N3 을 72점으로.
# --------------------------------------------------------------------------- #
def geometry_arm(phi_grid=None, L=L_REF, alt=ALT, d_grid=D_GRID, gate_drone="mini5pro") -> dict:
    """φ 마다 모노 vs 바이 **확산항 차**와 기하 사실을 낸다(닫힌형·σ 무관).

    N2 = 20log10(R2/R1)                : 모노 노드를 **수신기 자리**에 둔 비교(R2 고정)
    N3 = 40log10(R_mono / R_eq_bistatic): 모노 노드를 **조명원 자리**에 둔 비교(장면거리 d 고정)
    N1 (R_eq 고정) 은 정의상 항등 0 이라 φ 축이 없다 — 규약이지 발견이 아니다.

    ⭐ **게이트를 적용한 값도 함께 낸다**(`*_gated_*`). geometry_grid.py 의 23.17 dB 는 d 격자
      **전체**의 절대최대인데, 그 최대는 표적이 TX/RX 바로 위를 지나는 셀에서 나온다 —
      거기는 β>90°(SBR 유효범위 밖)·원거리장 밖이라 `stage_solve` 가 이미 `valid=False` 로
      해에서 빼는 구간이다. 검지거리 결론에 실제로 들어오는 크기를 보려면 게이트 뒤 값을 봐야 한다.
    """
    phi_grid = PHI_GRID if phi_grid is None else phi_grid
    fc = 3.5e9                    # geometry_grid 와 동일하게 NR 반송파(확산항은 fc 무관)
    v0 = np.zeros(3)
    rows = []
    i1k = int(np.argmin(np.abs(d_grid - D_FIXED)))
    for ph in phi_grid:
        tgt = FS.target_pos(d_grid, ph, L, alt)
        pb = FS.fs_params(FS.FS_TX, FS.FS_RX(L), tgt, v0, fc)
        pm = FS.fs_params(MONO_NODE, MONO_NODE, tgt, v0, fc)
        R1 = np.asarray(pb["R1"], float); R2 = np.asarray(pb["R2"], float)
        d2 = 20.0 * np.log10(R2 / R1)
        d3 = 40.0 * np.log10(np.asarray(pm["R1"], float) / np.asarray(pb["R_eq"], float))
        beta = np.asarray(pb["beta"], float)
        el = np.asarray(pb["el_deg"], float)
        # stage_solve 와 **같은** 유효범위 게이트: β≤90° AND min(R1,R2) ≥ 2D²/λ
        vmask = np.asarray(FS.beta_gate(beta), bool) & np.array(
            [bool(FS.farfield_gate(min(R1[i], R2[i]), gate_drone, fc)) for i in range(len(d_grid))])
        def _g(a, mask=vmask):
            s = np.asarray(a, float)[mask]
            return (float(np.max(np.abs(s))) if s.size else None,
                    float(np.median(s)) if s.size else None)
        n2g_absmax, n2g_med = _g(d2)
        n3g_absmax, n3g_med = _g(d3)
        rows.append(dict(
            phi_deg=float(ph),
            n2_median_db=float(np.median(d2)), n2_absmax_db=float(np.max(np.abs(d2))),
            n2_at_d1km_db=float(d2[i1k]),
            n3_median_db=float(np.median(d3)), n3_absmax_db=float(np.max(np.abs(d3))),
            n3_at_d1km_db=float(d3[i1k]),
            n2_gated_absmax_db=n2g_absmax, n2_gated_median_db=n2g_med,
            n3_gated_absmax_db=n3g_absmax, n3_gated_median_db=n3g_med,
            valid_frac=float(np.mean(vmask)),
            r1_over_r2_at_d1km=float(R1[i1k] / R2[i1k]),
            beta_deg_at_d1km=float(beta[i1k]), el_look_deg_at_d1km=float(el[i1k]),
            beta_gate_frac=float(np.mean(FS.beta_gate(beta))),
            el_look_min_deg=float(np.min(el)), el_look_max_deg=float(np.max(el)),
            frac_el_outside_sigma_grid=float(np.mean(el < -20.0))))
    n2m = np.array([r["n2_absmax_db"] for r in rows])
    n3m = np.array([r["n3_absmax_db"] for r in rows])
    n2g = np.array([np.nan if r["n2_gated_absmax_db"] is None else r["n2_gated_absmax_db"]
                    for r in rows], float)
    head = next(r for r in rows if r["phi_deg"] == 90.0)
    return dict(
        convention=dict(
            N1="R_eq = sqrt(R1 R2) held equal -> spread difference is identically 0 (a CONVENTION, "
               "not a finding); no phi axis exists for it",
            N2="R2 (receiver-target) held equal; monostatic node placed at the RECEIVER. "
               "delta_db = 20 log10(R2/R1)",
            N3="scene ground range d held equal; monostatic node placed at the ILLUMINATOR. "
               "delta_db = 40 log10(R_mono / R_eq_bistatic)",
            d_grid="geomspace(100, 20000, 240) m, same as benchmark/geometry_grid.py",
            gated=f"'_gated_' keys keep only cells with beta<=90 deg AND min(R1,R2)>=2D^2/lambda "
                  f"({gate_drone} at 3.5 GHz) - the same validity mask stage_solve applies before "
                  f"inverting for R90. Ungated keys reproduce geometry_grid.py verbatim."),
        rows=rows,
        axis=dict(phi_deg=[r["phi_deg"] for r in rows],
                  n2_median_db=[r["n2_median_db"] for r in rows],
                  n2_absmax_db=[r["n2_absmax_db"] for r in rows],
                  n2_gated_absmax_db=[r["n2_gated_absmax_db"] for r in rows],
                  n2_gated_median_db=[r["n2_gated_median_db"] for r in rows],
                  n3_median_db=[r["n3_median_db"] for r in rows],
                  n3_absmax_db=[r["n3_absmax_db"] for r in rows],
                  n3_gated_absmax_db=[r["n3_gated_absmax_db"] for r in rows],
                  valid_frac=[r["valid_frac"] for r in rows],
                  beta_gate_frac=[r["beta_gate_frac"] for r in rows],
                  frac_el_outside_sigma_grid=[r["frac_el_outside_sigma_grid"] for r in rows]),
        summary=dict(
            n2_absmax_at_phi90_db=head["n2_absmax_db"],
            n2_absmax_over_phi_db=float(n2m.max()),
            phi_at_n2_absmax_deg=float(rows[int(np.argmax(n2m))]["phi_deg"]),
            n2_absmax_min_over_phi_db=float(n2m.min()),
            phi_at_n2_absmax_min_deg=float(rows[int(np.argmin(n2m))]["phi_deg"]),
            n3_absmax_at_phi90_db=head["n3_absmax_db"],
            n3_absmax_over_phi_db=float(n3m.max()),
            ratio_absmax_over_phi90=float(n2m.max() / max(head["n2_absmax_db"], 1e-12)),
            n2_median_at_phi90_db=head["n2_median_db"],
            n2_median_absmax_over_phi_db=float(np.max(np.abs(
                [r["n2_median_db"] for r in rows]))),
            n2_gated_absmax_at_phi90_db=head["n2_gated_absmax_db"],
            n2_gated_absmax_over_phi_db=float(np.nanmax(n2g)),
            phi_at_n2_gated_absmax_deg=float(rows[int(np.nanargmax(n2g))]["phi_deg"]),
            gated_vs_ungated_note="the 23.17 dB headline is an UNGATED extremum; the gated column "
                                  "is what actually reaches the R90 inversion"))


# --------------------------------------------------------------------------- #
#  고정거리 SNR — 순위(파형 랭킹)를 R90 역해의 비선형과 분리해서 본다
# --------------------------------------------------------------------------- #
def snr_at_fixed_d(sig_json, drone, modes=MODES, phi_grid=None,
                   d=D_FIXED, L=L_REF, alt=ALT, T_cpi=0.1) -> dict:
    """φ 마다 **고정 장면거리 d 에서의 닫힌형 RD SNR** [dB] (모드별).

    R90 은 최외곽 하강교차 역해라 격자·게이트가 섞인다. 순위가 뒤집히는지는
    **같은 하늘 위치에서의 SNR** 로 보는 쪽이 깨끗하다. σ 는 정본 경로와 같은 조회를 쓴다.
    """
    phi_grid = PHI_GRID if phi_grid is None else phi_grid
    out = {}
    for mode in modes:
        std, occ = R.MODE_STD[mode]
        bname, fc, bw = R._BAND_BY_STD[std]
        lam = R.C0 / fc
        lookup = R._sigma_lookup(sig_json, drone, bname) if sig_json else None
        snrs, sigs, els = [], [], []
        for ph in phi_grid:
            tgt = FS.target_pos(d, ph, L, alt)
            p = FS.fs_params(FS.FS_TX, FS.FS_RX(L), tgt, (0.0, 0.0, 0.0), fc)
            az, _ = R._look_az(p["u1"], p["u2"])
            el = float(np.ravel(p["el_deg"])[0])
            sg = R._sigma_at(lookup, float(np.ravel(az)[0]), el, warn=False)
            snrs.append(float(FL.snr_rd_db(R.EIRP_DBM, R.GRX_DBI, lam, sg,
                                           float(np.ravel(p["R1"])[0]),
                                           float(np.ravel(p["R2"])[0]),
                                           nf=R.NF_DB, eta_ref=0.0, T=T_cpi,
                                           losses=0.0, k_mode=0.0)))
            sigs.append(float(10.0 * np.log10(max(sg, 1e-30))))
            els.append(el)
        out[mode] = dict(band=bname, phi_deg=list(phi_grid), snr_db=snrs,
                         sigma_dbsm=sigs, el_look_deg=els, d_m=float(d))
    return out


# --------------------------------------------------------------------------- #
#  자세평균 팔 — σ 조회 방위(aspect)의 φ 의존을 기하의 φ 의존과 분리한다
# --------------------------------------------------------------------------- #
def aspect_arm(sig_json, drone, modes=MODES, phi_grid=None, L=L_REF, alt=ALT,
               snr90_by_mode=None, T_cpi=0.1, verbose=True) -> dict:
    """φ 마다 **헤딩 ψ 전체에 대한 R90(ψ)** 를 모아 평균/중앙/최소최대를 낸다.

    왜 필요한가 — `stage_solve` 의 단일 R90 은 σ 를 `az_look`(=드론 요 0° 기준 정면방위)에서
    한 번 조회한다. φ 를 돌리면 `az_look` 이 같이 돌아가므로, R90(φ) 의 변화에는
    **기하**(R1·R2·게이트)와 **자세**(드론 σ 의 방위패턴)가 섞여 있다. `heading_polar` 는
    이미 ψ 를 72점 돌므로, 그 평균은 **자세를 평균으로 지운 R90** 이다 — 여기 남는 φ 의존이
    기하 몫에 훨씬 가깝다. `stage_solve` 를 호출만 하고 재구현하지 않는다.
    """
    phi_grid = PHI_GRID if phi_grid is None else phi_grid
    snr90_by_mode = dict(snr90_by_mode or {})
    out = {}
    for mode in modes:
        rows = []
        for ph in phi_grid:
            n0 = R.SIGMA_OOR["n"]
            s = R.stage_solve(mode=mode, drone=drone, L=L, alt=alt, T_cpi=T_cpi, N=1,
                              snr90_db=snr90_by_mode.get(mode), sig_json=sig_json,
                              phi_deg=float(ph), verbose=False)
            hp = np.array(s["heading_polar"]["R90_m"], float)
            fin = hp[hp > 0]
            rows.append(dict(
                phi_deg=float(ph),
                R90_psi0_m=R._flt(s["R_m"]),
                R90_mean_over_psi_m=(float(np.mean(fin)) if fin.size else None),
                R90_median_over_psi_m=(float(np.median(fin)) if fin.size else None),
                R90_min_over_psi_m=(float(np.min(fin)) if fin.size else None),
                R90_max_over_psi_m=(float(np.max(fin)) if fin.size else None),
                n_psi_zero=int(np.sum(hp <= 0)), n_psi=int(hp.size),
                blind_frac=R._flt(s["coverage"]["blind_frac"]),
                coverage_C=R._flt(s["coverage"]["C"]),
                E_psi_Pd=R._flt(s["coverage"]["E_psi_Pd"]),
                el_look_at_R_deg=None, sigma_oor_n=int(R.SIGMA_OOR["n"] - n0)))
        arr = np.array([r["R90_mean_over_psi_m"] if r["R90_mean_over_psi_m"] else np.nan
                        for r in rows], float)
        i90 = int(np.argmin(np.abs(np.array([r["phi_deg"] for r in rows]) - 90.0)))
        out[mode] = dict(
            rows=rows,
            axis=dict(phi_deg=[r["phi_deg"] for r in rows],
                      R90_psi0_m=[r["R90_psi0_m"] for r in rows],
                      R90_mean_over_psi_m=[r["R90_mean_over_psi_m"] for r in rows],
                      blind_frac=[r["blind_frac"] for r in rows],
                      E_psi_Pd=[r["E_psi_Pd"] for r in rows]),
            summary=dict(
                R90_mean_at_phi90_m=rows[i90]["R90_mean_over_psi_m"],
                R90_mean_min_m=float(np.nanmin(arr)), R90_mean_max_m=float(np.nanmax(arr)),
                phi_at_min_deg=float(rows[int(np.nanargmin(arr))]["phi_deg"]),
                phi_at_max_deg=float(rows[int(np.nanargmax(arr))]["phi_deg"]),
                span_db_equiv=float(40.0 * np.log10(np.nanmax(arr) / max(np.nanmin(arr), 1e-9))),
                span_pct_vs_phi90=float(100.0 * (np.nanmax(arr) - np.nanmin(arr))
                                        / max(rows[i90]["R90_mean_over_psi_m"] or np.nan, 1e-9))))
        if verbose:
            s = out[mode]["summary"]
            print(f"    [aspect] {mode}: mean_ψ R90(φ=90°)={s['R90_mean_at_phi90_m']:.0f} m · "
                  f"min {s['R90_mean_min_m']:.0f}@{s['phi_at_min_deg']:.0f}° · "
                  f"max {s['R90_mean_max_m']:.0f}@{s['phi_at_max_deg']:.0f}° · "
                  f"span {s['span_db_equiv']:.2f} dB-equiv", flush=True)
    return out


# --------------------------------------------------------------------------- #
#  순위 뒤집힘 판정
# --------------------------------------------------------------------------- #
def ranking_flips(by_mode_axis: dict, modes=MODES, key="R90_m", tol=0.0) -> dict:
    """φ 마다 세 파형의 순위(내림차순)를 내고, φ=90° 순위와 다른 φ 를 센다.

    `by_mode_axis[mode]` 는 φ 격자와 같은 길이의 값 배열이다. None/nan 은 최하위로 민다.
    tol>0 이면 그 폭 안의 차이는 동률로 본다(잡음성 뒤집힘 배제)."""
    phis = None
    vals = {}
    for m in modes:
        v = np.array([np.nan if x is None else float(x) for x in by_mode_axis[m]["values"]], float)
        vals[m] = v
        phis = by_mode_axis[m]["phi_deg"] if phis is None else phis
    order_by_phi, spread = [], []
    for i in range(len(phis)):
        pairs = sorted(((m, (vals[m][i] if np.isfinite(vals[m][i]) else -np.inf)) for m in modes),
                       key=lambda t: -t[1])
        order_by_phi.append([m for m, _ in pairs])
        finite = [v for _, v in pairs if np.isfinite(v)]
        spread.append(float(max(finite) - min(finite)) if len(finite) > 1 else None)
    i90 = int(np.argmin(np.abs(np.asarray(phis, float) - 90.0)))
    ref = order_by_phi[i90]
    diff = [i for i, o in enumerate(order_by_phi) if o != ref]
    # 동률 허용 재판정
    strict = []
    for i in diff:
        gaps = sorted((vals[m][i] for m in modes), reverse=True)
        gaps = [g for g in gaps if np.isfinite(g)]
        if len(gaps) < 2 or (gaps[0] - gaps[-1]) > tol:
            strict.append(i)
    return dict(key=key, phi_deg=list(phis), order_by_phi=order_by_phi,
                spread=spread, order_at_phi90=ref,
                n_phi_with_different_order=len(strict),
                phi_with_different_order=[float(phis[i]) for i in strict],
                distinct_orders=sorted({tuple(o) for o in order_by_phi}.__iter__(),
                                       key=lambda t: tuple(t)),
                n_distinct_orders=len({tuple(o) for o in order_by_phi}),
                flips=bool(strict),
                tol=float(tol),
                note="order is descending by the metric; phi=90 order is the published one")


# --------------------------------------------------------------------------- #
def main():
    t0 = time.time()
    sig = _load(R.SIGMA_JSON)
    pub = _load(os.path.join(ROOT, "outputs", "report13_freespace.json")) or {}
    snr90 = {m: SNR90_PUBLISHED_DB for m in MODES}
    measured = {}
    for m in MODES:
        try:
            dop = pub["threshold"]["S_G"][m]["1"]["dopoff"]
            v = [d["snr90_db"] for d in dop.values() if not d.get("skipped")]
            measured[m] = (float(np.mean(v)) if v else None)
        except Exception:
            measured[m] = None

    out = dict(meta=dict(
        script="benchmark/phi_sweep.py", generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
        git_rev=_git_rev(),
        question="Is 'geometry does not move the link budget' an artefact of the single scene "
                 "azimuth phi=90 deg that every published detection number was computed at?",
        phi_definition=("phi is the HORIZONTAL AZIMUTH of the target about the baseline MIDPOINT "
                        "O=(TX+RX)/2, measured from the +x axis which points TX->RX. "
                        "P(d,phi) = (L/2 + d cos phi, d sin phi, alt), TX=(0,0,25), RX=(L,0,3), "
                        "L=500 m. phi=0 -> target beyond the RECEIVER on the baseline; "
                        "phi=90 -> perpendicular bisector of the baseline (R1 = R2 by construction); "
                        "phi=180 -> target beyond the ILLUMINATOR. d is the horizontal range from O, "
                        "not R1, R2 or Rb. phi and 360-phi are mirror images in y: identical geometry, "
                        "sigma look azimuth negated."),
        phi_grid_deg=PHI_GRID, n_phi=len(PHI_GRID), headline_phi_deg=90.0,
        phi_grid_rationale=("5 deg over the full circle (72 points). Full circle because sigma "
                            "aspect asymmetry (not geometry) distinguishes phi from 360-phi; 5 deg "
                            "because the spread term blows up near phi=0/180 and a coarse grid "
                            "misses the maximum; contains 90 deg (the published cut) and "
                            "0/30/60/90/120/150/180 (cross-check against geometry_grid.py)."),
        modes=list(MODES), mode_bands={m: R._BAND_BY_STD[R.MODE_STD[m][0]][0] for m in MODES},
        drones=list(DRONES), L_m=L_REF, alt_m=ALT, T_cpi_s=0.1, N=1, speed_mps=5.0,
        d_grid="geomspace(100, 20000, 240) m", d_fixed_m=D_FIXED,
        snr90_db=snr90, snr90_source=("published run outputs/report13_freespace.json used the W1 "
                                      "transfer curve value for all three modes; reused verbatim so "
                                      "that any phi dependence is pure geometry"),
        snr90_measured_by_mode=measured,
        gpu="none - closed form. stage_phi_sweep recomputes geometry only; the sigma grid is "
            "re-read, never re-run, and the detector transfer curve is reused because Pd is a "
            "function of output SNR, not of range or azimuth. CUDA_VISIBLE_DEVICES was set empty.",
        sigma_file=R.SIGMA_JSON,
        sigma_file_generated=((sig or {}).get("meta") or {}).get("generated"),
        sigma_file_git_rev=((sig or {}).get("meta") or {}).get("git_rev"),
        link_budget=dict(eirp_dbm=R.EIRP_DBM, rx_gain_dbi=R.GRX_DBI, noise_figure_db=R.NF_DB,
                         provenance="DECLARED - no source doc (report13 spec 15-1)")))

    # ── 팔 C: 기하만 ───────────────────────────────────────────────────────────
    print("[phi] 팔 C — 기하(모노 vs 바이 확산항)…", flush=True)
    out["geometry"] = geometry_arm()
    g = out["geometry"]["summary"]
    print(f"    N2 |Δspread| absmax: φ=90° {g['n2_absmax_at_phi90_db']:.3f} dB → "
          f"φ 전체 최대 {g['n2_absmax_over_phi_db']:.3f} dB @φ={g['phi_at_n2_absmax_deg']:.0f}°",
          flush=True)

    # ── 팔 A: σ 격자 조회 (정본 경로) ─────────────────────────────────────────
    out["sigma_grid"] = {}
    for drone in DRONES:
        print(f"[phi] 팔 A — σ 격자 · {drone} …", flush=True)
        t = time.time()
        out["sigma_grid"][drone] = R.stage_phi_sweep(
            sig, modes=MODES, drone=drone, snr90_by_mode=snr90, phi_grid=PHI_GRID,
            L=L_REF, alt=ALT, speed=5.0, T_cpi=0.1, N=1, psi_n=72, verbose=False)
        for m in MODES:
            s = out["sigma_grid"][drone]["by_mode"][m].get("summary", {})
            print(f"    {drone} {m}: R90(φ=90°)={s.get('R90_at_phi90_m')} "
                  f"min={s.get('R90_min_m')}@{s.get('phi_at_R90_min_deg')}° "
                  f"max={s.get('R90_max_m')}@{s.get('phi_at_R90_max_deg')}° "
                  f"span={s.get('R90_span_db')} dB-equiv", flush=True)
        print(f"    ({time.time()-t:.0f}s)", flush=True)

    # ── 팔 B: σ 고정 통제군 (순수 기하) ───────────────────────────────────────
    print("[phi] 팔 B — σ≡0.01 m² 고정(순수 기하 통제군)…", flush=True)
    out["sigma_fixed"] = R.stage_phi_sweep(
        None, modes=MODES, drone=DRONES[0], snr90_by_mode=snr90, phi_grid=PHI_GRID,
        L=L_REF, alt=ALT, speed=5.0, T_cpi=0.1, N=1, psi_n=72, verbose=False)
    out["sigma_fixed"]["meta"]["sigma_model"] = ("constant 0.01 m^2 (-20 dBsm) everywhere - the "
                                                 "sigma grid is NOT consulted. Any phi dependence "
                                                 "left here is pure geometry (R1, R2, beta, gates).")
    for m in MODES:
        s = out["sigma_fixed"]["by_mode"][m].get("summary", {})
        print(f"    fixed-σ {m}: R90(φ=90°)={s.get('R90_at_phi90_m')} "
              f"min={s.get('R90_min_m')}@{s.get('phi_at_R90_min_deg')}° "
              f"max={s.get('R90_max_m')}@{s.get('phi_at_R90_max_deg')}°", flush=True)

    # ── 자세평균 팔 ───────────────────────────────────────────────────────────
    print(f"[phi] 자세평균 팔 — heading ψ 72점 평균 R90 · {DRONES[0]} …", flush=True)
    out["aspect_averaged"] = dict(
        drone=DRONES[0],
        note=("R90 averaged over the 72 heading angles psi (freespace_scene.heading_velocity / "
              "stage_solve heading_polar). Averaging over psi removes the drone ASPECT pattern, "
              "so the phi dependence left here is much closer to the pure geometry share."),
        by_mode=aspect_arm(sig, DRONES[0], snr90_by_mode=snr90))

    # ── 고정거리 SNR ──────────────────────────────────────────────────────────
    print("[phi] 고정거리 SNR(d=1 km)…", flush=True)
    out["snr_at_1km"] = {d: snr_at_fixed_d(sig, d) for d in DRONES}
    out["snr_at_1km"]["_sigma_fixed"] = snr_at_fixed_d(None, DRONES[0])

    # ── 순위 뒤집힘 ───────────────────────────────────────────────────────────
    rank = {}
    for drone in DRONES:
        node = out["sigma_grid"][drone]["by_mode"]
        rank[f"R90_{drone}"] = ranking_flips(
            {m: dict(phi_deg=node[m]["axis"]["phi_deg"], values=node[m]["axis"]["R90_m"])
             for m in MODES}, key=f"R90_m ({drone}, sigma grid)")
        s = out["snr_at_1km"][drone]
        rank[f"SNR1km_{drone}"] = ranking_flips(
            {m: dict(phi_deg=s[m]["phi_deg"], values=s[m]["snr_db"]) for m in MODES},
            key=f"snr_db at d=1 km ({drone}, sigma grid)")
    nf = out["sigma_fixed"]["by_mode"]
    rank["R90_sigma_fixed"] = ranking_flips(
        {m: dict(phi_deg=nf[m]["axis"]["phi_deg"], values=nf[m]["axis"]["R90_m"])
         for m in MODES}, key="R90_m (constant sigma control)")
    sf = out["snr_at_1km"]["_sigma_fixed"]
    rank["SNR1km_sigma_fixed"] = ranking_flips(
        {m: dict(phi_deg=sf[m]["phi_deg"], values=sf[m]["snr_db"]) for m in MODES},
        key="snr_db at d=1 km (constant sigma control)")
    out["rankings"] = rank
    for k, v in rank.items():
        print(f"    [rank] {k}: φ=90° 순위 {v['order_at_phi90']} · 다른 순위 φ "
              f"{v['n_phi_with_different_order']}/{len(PHI_GRID)}개 · 서로 다른 순위 "
              f"{v['n_distinct_orders']}종", flush=True)

    out["meta"]["runtime_s"] = round(time.time() - t0, 1)
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    tmp = OUT_JSON + ".tmp"
    with open(tmp, "w") as f:
        json.dump(out, f)
    os.replace(tmp, OUT_JSON)
    print(f"\n[phi] 완료 ({out['meta']['runtime_s']}s) → {OUT_JSON}")
    return out


if __name__ == "__main__":
    main()
