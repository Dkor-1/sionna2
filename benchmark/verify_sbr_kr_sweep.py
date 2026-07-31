# -*- coding: utf-8 -*-
"""
verify_sbr_kr_sweep.py — SBR+PO 커널의 **유효 kr 구간을 근거와 함께 선언**한다
================================================================================
왜 (이 저장소가 스스로 적어둔 부채):
  `docs/PRIOR_WORK_COMPARISON.md:415` 는 Sagitta(arXiv:2604.09243)의 **kr 스윕 검증**을
  "adopt" 라고 선언해 놓고 **한 번도 실행하지 않았다**. 실제 검증은 구 반경 **하나**(r=0.5 m)
  뿐이라 **kr 단일점**이고, 그 kr=36.7 은 Sagitta 가 밝힌 유효 하한 kr=30 의 1.22배 —
  즉 "유효하다고 공표된 구간의 가장 시끄러운 가장자리" 에서 한 점만 재고 있었다.

이 스크립트가 고치는 것 **세 가지**
  ① 기준해 — 옛 검증은 **πr²**(ka→∞ 광학 점근값)을 "해석해" 라 불렀다. ka 가 작으면 참값이
     아니다. 여기서는 **정확 Mie** 와 **해석적 PO** 를 **둘 다** 기준으로 놓는다.
         (커널 − Mie) = (커널 − 해석PO) + (해석PO − Mie)
                         ↑ 우리 수치오차      ↑ PO 근사의 대가(줄일 수 없음)
     커널이 PO 이므로 **수치 수렴의 과녁은 해석 PO** 이고, Mie 잔차는 별도의 자다.
  ② 축 — 옛 산포는 **kr 고정 + 광선격자 밀도축**에서 쟀는데 Sagitta 는 **입사방향 평균 후
     kr 축**에서 잰다. 서로 다른 양을 6배라 비교해 왔다. 여기서는 Sagitta 와 같은 축으로 잰다.
     ⚠ 그래도 완전 동일은 아니다 — 우리 구는 uv_sphere(극 특이점 있음), Sagitta 는 자체 메쉬다.
  ③ 코드 경로 — 옛 검증은 디더 없는 `rcs_sbr()` 를 썼는데 모든 생산 수치는
     `rcs_sbr_batch(jitter=…)` 에서 나온다. 여기서는 **생산 커널만** 쓴다.

메쉬 규약
  uv_sphere 의 면 변 길이 ≈ 2πr/seg 를 **λ/FACET_PER_LAM 이하**로 유지 → seg = FACET_PER_LAM·kr.
  즉 메쉬는 kr 에 **선형**으로 커진다(삼각형 수는 kr²). 이것이 상한을 정한다.

실행:
  SIONNA2_GPU=2 python benchmark/verify_sbr_kr_sweep.py            # 기본 사다리
  SIONNA2_KR_MAX=300 …                                             # 더 밀어보기
산출: outputs/sbr_kr_sweep.json
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

from gpu import pick                                                   # noqa: E402
pick()

from geom import uv_sphere                                             # noqa: E402
from rcs_sbr import rcs_sbr_batch                                      # noqa: E402
from mie_pec_sphere import mie_pec_backscatter_norm, po_sphere_norm    # noqa: E402

C0 = 299792458.0
FC = float(os.environ.get("SIONNA2_KR_FC", 3.5e9))
# ⭐ 2026-07-30 조밀화 — 적대검증 지적: kr>=30 이 div당 **3점뿐**이라 "산포 0.47%" 가 3개 수의
#   표준편차였다. 게다가 우리 표적의 실제 kr 은 **8.4~79.7** 로 대부분 이 사다리의 성긴 구간에 있다
#   (21조합 중 kr>=30 은 7개뿐, LTE 는 7종 전부 미달). 판정하려면 그 대역을 조밀하게 재야 한다.
KR_LADDER = [1.0, 2.0, 3.0, 5.0, 8.0, 10.0, 12.0, 15.0, 18.0, 22.0, 26.0, 30.0,
             35.0, 40.0, 45.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
KR_MAX = float(os.environ.get("SIONNA2_KR_MAX", 100.0))
DIVS = (12, 16)                       # 광선 격자 밀도 λ/div (생산 기본 12, 정밀 16)
JITTER = 3                            # 생산 커널 규약
FACET_PER_LAM = 8                     # 면 변 길이 ≤ λ/8

OUT = os.path.join(_ROOT, "outputs", "sbr_kr_sweep.json")
PEC = {"metal": 1.0}                  # ⚠ 문자열 'pec' 는 재질이 아니다 — float 1.0 이 |Γ|


# 입사방향 격자 — ⚠ `rcs_sbr_batch` 는 **az 만 배열**을 받고 el 은 스칼라다
#   (rcs_sbr.py:241 이 el 하나로 단일 입사벡터 u 를 만든다). 그래서 구면 균등샘플(피보나치)을
#   한 번에 넘길 수 없고, el 을 돌면서 az 배열을 넘기는 **격자**로 평균한다.
#   구는 등방이지만 **메쉬는 아니다** — uv_sphere 는 극에 특이점이 있어서 극/적도 입사가
#   다른 면 배열을 본다. el 을 넓게 잡는 이유가 그것이다.
EL_SET = (0.0, 20.0, 45.0, 70.0)
# ⚠ 2026-07-31 — 기본값을 6 → 12 로 올렸다(입사방향 24 → 48).
#   리포트가 인용하는 "≤0.201 dB" 는 48방향에서 잰 값인데, 기본값이 6 이라 파이프라인이
#   재생성할 때마다 **더 성긴 24방향 판**(0.1952 dB)으로 조용히 덮어썼다. 숫자가 흔들리니
#   리포트 고정값이 깨지고, 깨진 값으로 다시 박는 일이 실제로 일어났다.
#   ⭐ 24 vs 48 은 수렴을 확인했다: 0.1952 vs 0.2006 dB (차이 0.005 dB, 111 s vs 176 s).
#   같은 측정이므로 **발표한 밀도를 기본값으로** 두는 것이 맞다. 더 밀어보려면 SIONNA2_KR_NAZ 를 올려라.
AZ_N = int(os.environ.get("SIONNA2_KR_NAZ", 12))


def sweep():
    lam = C0 / FC
    kr_list = [k for k in KR_LADDER if k <= KR_MAX + 1e-9]
    az_all = np.linspace(0.0, 360.0, AZ_N, endpoint=False)
    n_inc = len(EL_SET) * AZ_N
    rows = []
    print(f"kr 스윕 @ {FC/1e9:.2f} GHz (λ={lam*100:.3f} cm), 입사 {n_inc}방향 평균"
          f"(el {EL_SET} × az {AZ_N}), "
          f"면≤λ/{FACET_PER_LAM}, 생산커널 jitter={JITTER}")
    print(f"{'kr':>7} {'r[m]':>8} {'seg×ring':>11} {'삼각형':>10} {'div':>4} "
          f"{'σ_SBR':>9} {'σ_PO':>9} {'σ_Mie':>9} {'SBR/PO':>8} {'SBR/Mie':>8} {'PO/Mie':>8}")
    print("-" * 106)
    for kr in kr_list:
        r = kr * lam / (2 * np.pi)
        seg = max(24, int(np.ceil(FACET_PER_LAM * kr)))
        seg += seg % 2
        rings = max(12, seg // 2)
        try:
            sph = uv_sphere(r, seg=seg, rings=rings, group="metal")
        except Exception as e:                                   # 메쉬가 너무 크다
            print(f"{kr:7.1f}  메쉬 생성 실패 — {type(e).__name__}: {e}")
            rows.append(dict(kr=kr, skipped=f"mesh:{type(e).__name__}"))
            continue
        n_tri = len(sph.f)
        pi_r2 = np.pi * r ** 2
        s_po = float(po_sphere_norm(kr)) * pi_r2
        s_mie = float(mie_pec_backscatter_norm(kr)) * pi_r2
        for div in DIVS:
            d = lam / div
            try:
                acc = []
                for _el in EL_SET:
                    v = rcs_sbr_batch(sph, PEC, FC, az_deg=az_all, el_deg=float(_el),
                                      spacing=d, jitter=JITTER, penetrate=False)
                    acc.append(np.atleast_1d(np.asarray(v, float)))
                sig = np.concatenate(acc)
                s_sbr = float(np.mean(sig))                      # **입사방향 평균** (Sagitta 축)
                s_sd = float(np.std(sig / s_sbr))                # 방향 간 산포(메쉬 아티팩트 지표)
            except Exception as e:
                print(f"{kr:7.1f} {r:8.4f} {seg:5d}×{rings:<5d} {n_tri:10,d} {div:4d}  "
                      f"실패 {type(e).__name__}")
                rows.append(dict(kr=kr, div=div, skipped=f"{type(e).__name__}"))
                continue
            R_po = s_sbr / s_po
            R_mie = s_sbr / s_mie
            G = s_po / s_mie
            rows.append(dict(
                kr=float(kr), r_m=float(r), div=int(div), seg=int(seg), rings=int(rings),
                n_tri=int(n_tri), n_inc=int(len(EL_SET) * AZ_N),
                el_set=list(EL_SET), az_n=int(AZ_N),
                sigma_sbr_m2=s_sbr, sigma_po_m2=s_po, sigma_mie_m2=s_mie,
                sigma_pir2_m2=float(pi_r2),
                ratio_sbr_over_po=float(R_po), ratio_sbr_over_mie=float(R_mie),
                ratio_po_over_mie=float(G),
                db_sbr_over_po=float(10 * np.log10(R_po)),
                db_sbr_over_mie=float(10 * np.log10(R_mie)),
                db_po_over_mie=float(10 * np.log10(G)),
                incidence_rel_sd=s_sd))
            print(f"{kr:7.1f} {r:8.4f} {seg:5d}×{rings:<5d} {n_tri:10,d} {div:4d} "
                  f"{10*np.log10(s_sbr):+9.3f} {10*np.log10(s_po):+9.3f} {10*np.log10(s_mie):+9.3f} "
                  f"{10*np.log10(R_po):+8.3f} {10*np.log10(R_mie):+8.3f} {10*np.log10(G):+8.3f}")
    return rows


def scale_invariance():
    """같은 kr 을 **다른 (r, f) 조합**으로 만들어 결과가 같은지 — 절대 길이가 하드코딩돼
    있으면 여기서 깨진다. 2분이면 되는 값싼 함정 탐지기."""
    kr = 30.0
    out = []
    for fc in (3.5e9, 14.0e9):
        lam = C0 / fc
        r = kr * lam / (2 * np.pi)
        seg = int(np.ceil(FACET_PER_LAM * kr)); seg += seg % 2
        sph = uv_sphere(r, seg=seg, rings=seg // 2, group="metal")
        az = np.linspace(0.0, 360.0, 6, endpoint=False)
        acc = [np.atleast_1d(np.asarray(
            rcs_sbr_batch(sph, PEC, fc, az_deg=az, el_deg=float(e),
                          spacing=lam / 16, jitter=JITTER, penetrate=False), float))
            for e in (0.0, 45.0)]
        norm = float(np.mean(np.concatenate(acc))) / (np.pi * r ** 2)
        out.append(dict(fc_hz=fc, r_m=r, sigma_over_pir2=norm))
        print(f"  스케일 불변성  f={fc/1e9:5.1f} GHz  r={r:.4f} m  σ/(πr²)={norm:.6f}")
    dev_db = 10 * np.log10(out[0]["sigma_over_pir2"] / out[1]["sigma_over_pir2"])
    ok = abs(dev_db) < 0.05
    print(f"  → 두 조합 차이 {dev_db:+.4f} dB  {'PASS' if ok else 'FAIL(절대길이 하드코딩 의심)'}")
    return dict(points=out, dev_db=float(dev_db), pass_=bool(ok), tol_db=0.05)


def main():
    t0 = time.time()
    rows = sweep()
    print()
    inv = scale_invariance()

    good = [r for r in rows if "skipped" not in r]
    res = dict(
        meta=dict(
            generated=time.strftime("%Y-%m-%d %H:%M:%S"),
            fc_hz=FC, kr_ladder=[r["kr"] for r in good], divs=list(DIVS), jitter=JITTER,
            facet_per_lambda=FACET_PER_LAM, n_incidence=len(EL_SET) * AZ_N,
            el_set=list(EL_SET), az_n=AZ_N,
            gpu=os.environ.get("CUDA_VISIBLE_DEVICES") or "(auto)",
            runtime_s=None,
            reference_note=(
                "기준해 둘: 정확 Mie 와 해석적 PO. 커널이 PO 이므로 **수치 수렴의 과녁은 해석 PO** 이고, "
                "Mie 잔차는 'PO 근사를 쓴 대가' 라는 별도의 자다. 옛 검증이 쓰던 πr² 은 ka→∞ 점근값일 뿐 "
                "참값이 아니다(ka=13 에서 +0.305 dB 틀림)."),
            axis_note=(
                "⭐ Sagitta 와 **같은 축**에서 쟀다 — 입사방향 평균 후 kr 스윕. "
                "옛 '6배 나쁨' 헤드라인은 kr 고정 + 광선격자 밀도축 산포라 애초에 다른 양이었다. "
                "⚠ 그래도 완전한 사과-대-사과는 아니다: 메쉬(uv_sphere, 극 특이점)와 구현이 다르다."),
        ),
        rows=rows,
        scale_invariance=inv,
    )

    # ── 유효구간 판정 ────────────────────────────────────────────────────────
    for div in DIVS:
        sel = [r for r in good if r["div"] == div]
        if not sel:
            continue
        rp = np.array([r["ratio_sbr_over_po"] for r in sel])
        rm = np.array([r["ratio_sbr_over_mie"] for r in sel])
        krs = np.array([r["kr"] for r in sel])
        # 광학영역(kr≥30)만으로 산포 — Sagitta 가 보는 구간
        opt = krs >= 30
        res[f"summary_div{div}"] = dict(
            n_points=int(len(sel)), kr_min=float(krs.min()), kr_max=float(krs.max()),
            std_sbr_over_po_pct=float(np.std(rp) * 100),
            std_sbr_over_mie_pct=float(np.std(rm) * 100),
            std_sbr_over_po_pct_kr_ge30=float(np.std(rp[opt]) * 100) if opt.any() else None,
            std_sbr_over_mie_pct_kr_ge30=float(np.std(rm[opt]) * 100) if opt.any() else None,
            max_abs_db_vs_po=float(np.abs(10 * np.log10(rp)).max()),
            max_abs_db_vs_mie=float(np.abs(10 * np.log10(rm)).max()),
        )
    res["meta"]["runtime_s"] = round(time.time() - t0, 1)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)

    print("\n=== 요약 (과녁별 산포) ===")
    for div in DIVS:
        s = res.get(f"summary_div{div}")
        if not s:
            continue
        print(f"  λ/{div}: 점 {s['n_points']}개, kr {s['kr_min']:.0f}~{s['kr_max']:.0f}")
        print(f"        해석PO 대비 산포 {s['std_sbr_over_po_pct']:.2f}%"
              f"  (kr≥30 만: {s['std_sbr_over_po_pct_kr_ge30'] if s['std_sbr_over_po_pct_kr_ge30'] is None else round(s['std_sbr_over_po_pct_kr_ge30'],2)}%)"
              f"  최대 |편차| {s['max_abs_db_vs_po']:.3f} dB")
        print(f"        Mie   대비 산포 {s['std_sbr_over_mie_pct']:.2f}%"
              f"  (kr≥30 만: {s['std_sbr_over_mie_pct_kr_ge30'] if s['std_sbr_over_mie_pct_kr_ge30'] is None else round(s['std_sbr_over_mie_pct_kr_ge30'],2)}%)"
              f"  최대 |편차| {s['max_abs_db_vs_mie']:.3f} dB")
    print(f"\n✅ 저장 → {os.path.relpath(OUT, _ROOT)}  ({res['meta']['runtime_s']:.0f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
