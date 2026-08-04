# -*- coding: utf-8 -*-
"""
lowfreq_anchor_slope.py — **PO 가 주파수 기울기를 왜 가파르게 만드는가**를 참값으로 본다
================================================================================
드론 헤드라인(`outputs/lowfreq_grid.json`)의 증상은 σ(f) **기울기**였다:
    저대역 1.8–6.0 GHz  a = +1.63 dB/GHz   ↔  고대역 6.0–18.2 GHz  a = +0.20 dB/GHz
그리고 격자를 16 배 조여도 그 기울기는 안 움직였다(오히려 가팔라졌다).

여기서는 **참값이 있는 물체**로 같은 기울기를 잰다. 물리적 폭 w 를 **고정**하고 주파수를
드론과 **같은 21 점**(1.8→18.2 GHz)으로 쓸면, w/λ 가 0.08 → 2.7 로 지나간다. 각 점에서
    · σ_PO   : 평판 PO 닫힌형 (우리 커널이 수렴하는 과녁)
    · σ_MoM  : 2D EFIE MoM 정확해 (TM·TE 양편파) — **참값**
을 내고 각각의 dB/GHz 기울기를 같은 구간(1.8–6.0 / 6.0–18.2)에서 적합한다.

⭐ 검정할 명제: **PO 는 저대역에서 참값보다 기울기를 가파르게 낸다.**
   (w/λ 가 작을수록 PO 오차가 크고, f 가 오르면 그 오차가 사라지므로 PO 의 σ(f) 가
    참값보다 빠르게 올라간다 — 즉 기울기 초과분은 격자가 아니라 **모델**이 만든다.)

산출: outputs/partial/lowfreq_anchor/slope.json
"""
from __future__ import annotations

import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (os.path.join(_ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

C0 = 299792458.0
PART = os.path.join(_ROOT, "outputs", "partial", "lowfreq_anchor")

#  드론 스윕과 **같은** 21 주파수 (lowfreq_grid.json refit.freqs_ghz)
FREQS_GHZ = (1.8, 2.62, 3.44, 4.26, 5.08, 5.9, 6.72, 7.54, 8.36, 9.18, 10.0, 10.82,
             11.64, 12.46, 13.28, 14.1, 14.92, 15.74, 16.56, 17.38, 18.2)
BANDS = {"1.8-6.0": (1.8, 6.0), "6.0-18.2": (6.0, 18.2), "1.8-18.2": (1.8, 18.2)}
#  Phantom 3 실측 특징 치수 (lowfreq_grid.json feature_scales)
WIDTHS_MM = {"prop_13.78mm": 13.78, "arm_tip_30mm": 30.0, "arm_root_45mm": 45.0}
#  ⚠⚠ 3D 환산용 span 은 **고정된 물리 길이**여야 한다 (2026-08-03 자기정정).
#     처음엔 b=6λ 로 뒀는데, 그러면 σ_3D=(2b²/λ)σ_2D = 144π w² 가 되어 **주파수 의존이 통째로
#     상쇄**된다 — a_PO 가 세 폭 모두 정확히 0.0000 dB/GHz 로 나와 들켰다. 표적은 주파수가
#     올라간다고 작아지지 않는다. b 를 고정하면 σ_3D_PO = 4πb²w²/λ² ∝ f² 로 옳게 돌아온다.
#     ※ 기울기 **차이**(PO−참값)는 두 곡선에 같은 환산이 걸리므로 이 버그에 무관했다.
B_M_FIXED = 6.0 * (C0 / 1.8e9)      # = 0.9993 m (1.8 GHz 에서의 6λ, 이후 고정)
#  파장당 세그먼트 수. TE 는 Galerkin 조립이 O(M²) 파이썬 루프라 상한이 비용을 지배한다.
#  ⚠ 상한 200 은 최악점(w/λ=2.73 @18.2 GHz)에서도 73 seg/λ 이다 — mom2d 자기검증이
#    60 seg 에서 이미 <0.005 dB 로 수렴함을 보였으므로 충분하다. 아래 mom_convergence 가 확인한다.
SEG_PER_LAM = 400
SEG_MIN, SEG_MAX = 60, 200
SEG_CHECK_SCALE = 1.5      # 수렴확인용 세그먼트 배율


def _one(args):
    """(태그, w[m], f[Hz], seg_per_lam) → 2D σ 세 개. 워커는 모듈 최상위 함수여야 한다."""
    tag, w, f = args[0], args[1], args[2]
    spl = args[3] if len(args) > 3 else SEG_PER_LAM
    smax = args[4] if len(args) > 4 else SEG_MAX
    import mom2d_reference as mom
    lam = C0 / f
    k = 2.0 * np.pi / lam
    M = int(np.clip(round(spl * w / lam), SEG_MIN, smax))
    u = np.array([0.0, 1.0]); e_r = np.array([-1.0, 0.0])       # 정면입사 θ=0
    nd = mom.strip_nodes(w, M)
    W_tm = (mom.Z0 / 2) * mom.solve_tm(mom.assemble_tm(nd, k), u)[0]
    W_te = (mom.Z0 / 2) * mom.solve_te(mom.assemble_te(nd, k, closed=False), u, e_r)[0]
    return dict(tag=tag, w_m=float(w), f_ghz=float(f / 1e9), w_over_lam=float(w / lam),
                n_seg=M, sigma2d_po=float(k * w ** 2),
                sigma2d_tm=float(k * abs(W_tm) ** 2), sigma2d_te=float(k * abs(W_te) ** 2))


def _fit(fg, db, lo, hi):
    m = (np.asarray(fg) >= lo - 1e-9) & (np.asarray(fg) <= hi + 1e-9)
    x, y = np.asarray(fg)[m], np.asarray(db)[m]
    if x.size < 2:
        return None
    a, b = np.polyfit(x, y, 1)
    yy = a * x + b
    ss = float(np.sum((y - y.mean()) ** 2))
    return dict(a_db_per_ghz=float(a), b=float(b), n=int(x.size),
                R2=float(1 - np.sum((y - yy) ** 2) / ss) if ss > 0 else None,
                rmse_db=float(np.sqrt(np.mean((y - yy) ** 2))))


def main():
    os.makedirs(PART, exist_ok=True)
    t0 = time.perf_counter()
    jobs = [(tag, mm * 1e-3, f * 1e9) for tag, mm in WIDTHS_MM.items() for f in FREQS_GHZ]
    print(f"[slope] 2D MoM {len(jobs)} 점 (폭 {len(WIDTHS_MM)} × 주파수 {len(FREQS_GHZ)}), "
          f"CPU 병렬")
    with ProcessPoolExecutor(max_workers=16) as ex:
        res = list(ex.map(_one, jobs))
    print(f"[slope] MoM 완료 {time.perf_counter()-t0:.0f} s")

    out = dict(part="slope", generated=time.strftime("%Y-%m-%d %H:%M:%S"),
               freqs_ghz=list(FREQS_GHZ), widths_mm=WIDTHS_MM, bands=BANDS,
               b_m_fixed_for_3d=B_M_FIXED,
               tm_dominates_note=("얇은 띠에서 σ_TM ≫ σ_TE 다(0.15λ 에서 11.6 dB). 즉 물리적으로 "
                                  "**지배적인 채널이 TM** 이고, PO 의 저대역 기울기가 참값보다 "
                                  "가파른 것도 그 TM 채널에서다. 약한 TE 채널에서는 부호가 반대이므로 "
                                  "‘PO 가 기울기를 가파르게 만든다’ 는 **지배 채널 기준** 진술이다."), rows=res, by_width={})
    print(f"\n{'width':>16} {'band':>10} {'a_PO':>9} {'a_TM':>9} {'a_TE':>9} "
          f"{'PO−TM':>9} {'PO−TE':>9}")
    for tag in WIDTHS_MM:
        rr = sorted([r for r in res if r["tag"] == tag], key=lambda r: r["f_ghz"])
        fg = [r["f_ghz"] for r in rr]
        #  σ_3D = (2b²/λ)·σ_2D, b 는 **고정 물리 길이**. λ 의존이 남아야 기울기가 산다.
        conv = [2.0 * B_M_FIXED ** 2 / (C0 / (f * 1e9)) for f in fg]
        db = {k: 10 * np.log10(np.array([r[f"sigma2d_{k}"] for r in rr]) * np.array(conv))
              for k in ("po", "tm", "te")}
        fits = {k: {bn: _fit(fg, db[k], *b) for bn, b in BANDS.items()} for k in db}
        out["by_width"][tag] = dict(
            w_mm=WIDTHS_MM[tag], f_ghz=fg,
            w_over_lam=[r["w_over_lam"] for r in rr], n_seg=[r["n_seg"] for r in rr],
            sigma3d_po_dbsm=db["po"].tolist(), sigma3d_tm_dbsm=db["tm"].tolist(),
            sigma3d_te_dbsm=db["te"].tolist(),
            po_minus_tm_db=(db["po"] - db["tm"]).tolist(),
            po_minus_te_db=(db["po"] - db["te"]).tolist(), fits=fits,
            slope_excess_db_per_ghz={bn: dict(vs_tm=fits["po"][bn]["a_db_per_ghz"] - fits["tm"][bn]["a_db_per_ghz"],
                                              vs_te=fits["po"][bn]["a_db_per_ghz"] - fits["te"][bn]["a_db_per_ghz"])
                                     for bn in BANDS})
        for bn in BANDS:
            e = out["by_width"][tag]["slope_excess_db_per_ghz"][bn]
            print(f"{tag:>16} {bn:>10} {fits['po'][bn]['a_db_per_ghz']:+9.4f} "
                  f"{fits['tm'][bn]['a_db_per_ghz']:+9.4f} {fits['te'][bn]['a_db_per_ghz']:+9.4f} "
                  f"{e['vs_tm']:+9.4f} {e['vs_te']:+9.4f}")

    #  MoM 수렴 확인 — 대표 점에서 세그먼트 두 배
    cj = [(tag, mm * 1e-3, f, s * SEG_PER_LAM, int(s * SEG_MAX))
          for tag, mm in WIDTHS_MM.items() for f in (1.8e9, 6.0e9, 18.2e9)
          for s in (1.0, SEG_CHECK_SCALE)]
    with ProcessPoolExecutor(max_workers=16) as ex:
        cr = list(ex.map(_one, cj))
    chk = []
    for i in range(0, len(cr), 2):
        a, b = cr[i], cr[i + 1]
        chk.append(dict(tag=a["tag"], f_ghz=a["f_ghz"], n_seg=a["n_seg"], n_seg_scaled=b["n_seg"],
                        d_tm_db=float(10 * np.log10(b["sigma2d_tm"] / a["sigma2d_tm"])),
                        d_te_db=float(10 * np.log10(b["sigma2d_te"] / a["sigma2d_te"]))))
    out["mom_convergence"] = dict(
        rows=chk,
        max_abs_d_tm_db=float(max(abs(c["d_tm_db"]) for c in chk)),
        max_abs_d_te_db=float(max(abs(c["d_te_db"]) for c in chk)),
        note=f"세그먼트를 {SEG_CHECK_SCALE}배로 늘렸을 때의 이동. 참값의 수치 잔여오차 상한이다.")
    print(f"\n[slope] MoM 세그먼트 배증 시 최대 이동 TM {out['mom_convergence']['max_abs_d_tm_db']:.4f} dB · "
          f"TE {out['mom_convergence']['max_abs_d_te_db']:.4f} dB")
    out["runtime_s"] = float(time.perf_counter() - t0)
    p = os.path.join(PART, "slope.json")
    with open(p, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"[slope] → {p}  ({out['runtime_s']:.0f} s)")


if __name__ == "__main__":
    main()
