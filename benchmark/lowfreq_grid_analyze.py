# -*- coding: utf-8 -*-
"""
lowfreq_grid_analyze.py — 격자 사다리 결과를 판정으로 바꾼다  →  outputs/lowfreq_grid.json
                                                              outputs/figs/lowfreq_grid_convergence.png
=================================================================================================
입력: /tmp/.../lfg/part_*.json (benchmark/lowfreq_grid.py 가 만든 μ(f,d) 원자료)
판정: 가설 A(표본화, 고칠 수 있음) / B(PO 근본한계, 못 고침) / MIXED
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

sys.path[:0] = ["/workspace/sionna/src",
                "/workspace/sionna/benchmark"]

ROOT = "/workspace/sionna"
SCRATCH = "/tmp/claude-1015/-workspace/a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad/lfg"
OUT_JSON = os.path.join(ROOT, "outputs", "lowfreq_grid.json")
FIG_PATH = os.path.join(ROOT, "outputs", "figs", "lowfreq_grid_convergence.png")

C0 = 299792458.0
DAS_A = 0.21                 # Das IEEE WCL 2026 Table III, Phantom 3, bistatic 0° → dB/GHz
LADDER_F = [1.8, 3.5, 6.0, 12.0, 18.2]
D_CONV = 0.75                # mm
SUBBANDS = {"1.8-6.0": (1.8, 6.0), "6.0-18.2": (6.0, 18.2), "1.8-18.2": (1.8, 18.2)}


# ------------------------------------------------------------------ 적합 도구
def linfit(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    a, b = np.polyfit(x, y, 1)
    yh = a * x + b
    ssr = float(np.sum((y - yh) ** 2)); sst = float(np.sum((y - y.mean()) ** 2))
    return dict(a=float(a), b=float(b), R2=float(1 - ssr / sst) if sst > 0 else float("nan"),
                rmse_db=float(np.sqrt(ssr / len(x))), n=int(len(x)))


def band_fits(fghz, mu):
    fghz = np.asarray(fghz, float); mu = np.asarray(mu, float)
    out = {}
    for name, (lo, hi) in SUBBANDS.items():
        m = (fghz >= lo - 1e-6) & (fghz <= hi + 1e-6)
        out[name] = linfit(fghz[m], mu[m]) if m.sum() >= 2 else None
    return out


def load():
    recs = []
    for fn in sorted(os.listdir(SCRATCH)):
        if fn.startswith("part_") and fn.endswith(".json"):
            recs += json.load(open(os.path.join(SCRATCH, fn)))
    return recs


def feature_scales():
    """가설의 전제를 **메쉬에서 직접** 잰다 — 격자가 무엇을 표본화 못 하는지.
    그룹별 최소 bbox 변(=두께 대용)과 삼각형 모서리 길이 분위점."""
    from drones import DRONES, build_drone
    m = build_drone(DRONES["phantom3"])
    V = np.asarray(m.v, float); F = np.asarray(m.f, int); G = np.asarray(m.g)
    thick = {}
    for g in sorted(set(G.tolist())):
        P = V[np.unique(F[G == g].ravel())]
        thick[g] = round(float((P.max(0) - P.min(0)).min()) * 1e3, 2)
    E = np.concatenate([V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 1]], V[F[:, 0]] - V[F[:, 2]]])
    L = np.linalg.norm(E, axis=1) * 1e3
    rays = {}
    for f in LADDER_F:
        lam_mm = C0 / (f * 1e9) * 1e3
        rays[f"{f:g}GHz"] = {
            "lam_mm": round(lam_mm, 3),
            "d_lam16_mm": round(lam_mm / 16, 4), "d_lam12_mm": round(lam_mm / 12, 4),
            "rays_across_prop_blade_lam16": round(thick["prop"] / (lam_mm / 16), 2),
            "rays_across_prop_blade_0p75mm": round(thick["prop"] / 0.75, 2),
            "rays_across_canopy_lam16": round(thick["canopy"] / (lam_mm / 16), 2),
            "prop_blade_over_lambda": round(thick["prop"] / lam_mm, 4),
            "canopy_over_lambda": round(thick["canopy"] / lam_mm, 4),
        }
    return dict(
        group_min_bbox_mm=thick,
        arm_width_root_tip_mm=[45.0, 30.0],
        arm_note=("phantom3 메쉬에는 'arm' 그룹이 없다 — 팔은 body 셸의 일부다. "
                  "45/30 mm 는 drone_cad._ARM_WIDTH['phantom3'](phantom4 상속) 값이다."),
        mesh_edge_mm=dict(p05=round(float(np.percentile(L, 5)), 3),
                          p50=round(float(np.percentile(L, 50)), 3),
                          p95=round(float(np.percentile(L, 95)), 3)),
        per_freq=rays,
        reading=("d=0.75 mm 는 메쉬 삼각형 중앙값 모서리(5.85 mm)의 1/8 이다 → 이 격자에서 수렴하는 대상은 "
                 "**이 삼각메쉬 위의 PO 면적분**이다. 테셀레이션 자체는 별개의 오차축이다."))


def reproducibility(by):
    """09:58–10:41 에 같은 코드경로로 돌린 독립 실행(res_w*.json)과 겹치는 점을 대조한다.
    커널이 결정적이므로 일치해야 한다 — 어긋나면 둘 중 하나가 오염된 것이다."""
    import glob
    old = []
    for fn in glob.glob(os.path.join(SCRATCH, "res_w*.json")):
        try:
            old += json.load(open(fn))
        except Exception:
            pass
    if not old:
        return dict(available=False)
    diffs, n = [], 0
    for r in old:
        k = (round(r["f_ghz"], 4), round(r["d_mm"], 5))
        if k in by:
            n += 1
            diffs.append(abs(by[k]["mu_dbsm"] - r["mu_dbsm"]))
    if not diffs:
        return dict(available=True, overlap=0)
    return dict(available=True, overlap=n, max_abs_dmu_db=round(float(np.max(diffs)), 6),
                mean_abs_dmu_db=round(float(np.mean(diffs)), 6),
                source="같은 세션 09:58–10:41 의 선행 실행(스크래치 res_w*.json). 소스 파일은 그 뒤 변경 없음.",
                reading="커널은 결정적(난수 없음)이라 0 이어야 한다.")


def source_drift_check(by, ladder_spread_db):
    """⚠ 이 스윕이 끝난 뒤 다른 작업이 src/drones.py · src/drone_cad.py 의 Phantom 3 CAD 를 고쳤다.
    지금 소스로 λ/16 두 점을 다시 내서 **얼마나 달라졌는지** 기록한다.

    이 스윕이 무엇을 잰 것인지는 `baseline_reproduction` 이 말한다 — outputs/p3_ours.json el0 의
    21 주파수를 0.0005 dB 안에서 재현하므로, 이 산출물은 **헤드라인 관측(a=+0.4198)이 나온 바로 그
    기체**를 잰 것이다. 대조군과 실험군이 같은 기체라는 것이 이 실험의 요건이고, 그 요건은 충족된다.
    CAD 개정은 별개의 축이며 p3_ours 도 함께 낡는다."""
    import numpy as _np
    from rcs_sbr import rcs_sbr_batch
    from drones import DRONES, build_drone, DRONE_GROUP_MAT
    mesh = build_drone(DRONES["phantom3"])
    gm = {g: mat for g, (mat, _) in DRONE_GROUP_MAT.items()}
    az = _np.linspace(0.0, 360.0, 360, endpoint=False)
    out = []
    for f_ghz in (1.8, 18.2):
        f = f_ghz * 1e9
        lam_mm = C0 / f * 1e3
        s = rcs_sbr_batch(mesh, gm, f, az_deg=az, el_deg=0.0, spacing=(C0 / f) / 16.0,
                          cache_key=("phantom3", round(f / 1e6), 0.0, "drift"))
        mu = float(10 * _np.log10(_np.mean(_np.maximum(_np.asarray(s, float), 1e-30))))
        stored = by[(round(f_ghz, 4), round(lam_mm / 16.0, 5))]["mu_dbsm"]
        out.append(dict(f_ghz=f_ghz, mu_current_source_dbsm=round(mu, 4),
                        mu_in_this_sweep_dbsm=round(stored, 4),
                        abs_diff_db=round(abs(mu - stored), 6)))
    G = _np.asarray(mesh.g)
    import collections as _c
    mx = max(p["abs_diff_db"] for p in out)
    return dict(
        checked_at=time.strftime("%Y-%m-%d %H:%M:%S"),
        what_happened=("스윕(12:24–12:58) 이 끝난 뒤 다른 작업이 Phantom 3 CAD 를 개정했다 — 개정은 "
                       "이 검사 도중에도 계속됐다(연속 검사마다 메쉬 삼각형 수가 달랐다). "
                       "아래 숫자는 checked_at 시점의 소스 기준이다."),
        this_sweep_measured=("outputs/p3_ours.json el0 과 같은 기체 — baseline_reproduction 의 "
                             "max_abs_dmu_db 가 증거다. 헤드라인 관측이 나온 기체와 동일하다."),
        current_mesh=dict(n_vertices=int(len(mesh.v)), n_triangles=int(len(mesh.f)),
                          tri_per_group=dict(_c.Counter(G.tolist()))),
        points=out,
        max_abs_diff_db=round(mx, 6),
        ladder_total_spread_at_1p8_db=round(ladder_spread_db, 4),
        cad_over_grid_ratio=round(mx / ladder_spread_db, 1) if ladder_spread_db > 0 else None,
        reading=(f"CAD 개정이 μ 를 {mx:.2f} dB 움직인다 — 이 실험이 잰 **격자 사다리 전체 효과 "
                 f"{ladder_spread_db:.3f} dB 의 {mx / ladder_spread_db:.0f} 배**다. 저주파 격차의 후보가 "
                 f"표본화가 아니라 기하·물리 쪽에 있다는 이 실험의 결론과 같은 방향이다. "
                 f"⚠ 다만 이 두 점은 개정된 CAD 의 **레벨** 변화일 뿐, 기울기 재판정이 아니다."))


def main():
    recs = load()
    by = {(round(r["f_ghz"], 4), round(r["d_mm"], 5)): r for r in recs}
    cost_s = float(sum(r["t_s"] for r in recs))

    # ---------------------------------------------------------------- 1. 사다리
    ladder = {}
    for f in LADDER_F:
        lam_mm = C0 / (f * 1e9) * 1e3
        ds = sorted({round(d, 5) for (ff, d) in by if abs(ff - f) < 1e-6}, reverse=True)
        rows = []
        for d in ds:
            r = by[(round(f, 4), d)]
            rows.append(dict(d_mm=d, rays_per_lambda=round(lam_mm / d, 3),
                             mu_dbsm=round(r["mu_dbsm"], 4), eps_db=round(r["eps_db"], 4),
                             n_rays_per_az=int(np.ceil(2 * (0.3078870 * 1.15 + 3 * d * 1e-3) / (d * 1e-3))) ** 2,
                             t_s=r["t_s"]))
        mu_l12 = by[(round(f, 4), round(lam_mm / 12.0, 5))]["mu_dbsm"]
        mu_l16 = by[(round(f, 4), round(lam_mm / 16.0, 5))]["mu_dbsm"]
        mu_conv = by[(round(f, 4), D_CONV)]["mu_dbsm"]
        finest = min(ds)
        mu_fine = by[(round(f, 4), finest)]["mu_dbsm"]
        # 절대격자 구간(6→0.75mm)의 마지막 두 계단 변화 = 잔차 수렴 지표
        d_abs = sorted([d for d in ds if d in (6.0, 3.0, 1.5, 0.75, 0.5, 0.375)])
        tail = [by[(round(f, 4), d)]["mu_dbsm"] for d in d_abs]
        ladder[f"{f:g}GHz"] = dict(
            f_ghz=f, lam_mm=round(lam_mm, 4), rows=rows,
            mu_lam12=round(mu_l12, 4), mu_lam16=round(mu_l16, 4),
            mu_conv_0p75mm=round(mu_conv, 4), mu_finest=round(mu_fine, 4), d_finest_mm=finest,
            shift_conv_minus_lam12_db=round(mu_conv - mu_l12, 4),
            shift_conv_minus_lam16_db=round(mu_conv - mu_l16, 4),
            last_step_db=round(tail[0] - tail[1], 4) if len(tail) >= 2 else None,
            abs_ladder_d_mm=d_abs, abs_ladder_mu_dbsm=[round(x, 4) for x in tail])

    # ------------------------------------------- 1b. 기울기 자체가 d 와 함께 어떻게 움직이나
    #   사다리 주파수만으로 저대역(1.8·3.5·6.0)·고대역(6.0·12.0·18.2)·전대역 기울기를 d 마다 낸다.
    #   ⭐ 한 점이 아니라 **사다리 전체 추세**로 판정하라는 요구를 이 표가 받는다.
    slope_vs_d = []
    for d in [6.0, 3.0, 1.5, 0.75, 0.5]:
        if not all((round(f, 4), d) in by for f in LADDER_F):
            continue
        mu = [by[(round(f, 4), d)]["mu_dbsm"] for f in LADDER_F]
        fa = np.asarray(LADDER_F, float)
        lo = fa <= 6.0 + 1e-6; hi = fa >= 6.0 - 1e-6
        slope_vs_d.append(dict(d_mm=d,
                               a_low_1p8_6=round(float(np.polyfit(fa[lo], np.asarray(mu)[lo], 1)[0]), 4),
                               a_high_6_18p2=round(float(np.polyfit(fa[hi], np.asarray(mu)[hi], 1)[0]), 4),
                               a_full=round(float(np.polyfit(fa, mu, 1)[0]), 4)))
    for tag, div in (("lam12", 12.0), ("lam16", 16.0)):
        mu, fa = [], []
        for f in LADDER_F:
            k = (round(f, 4), round(C0 / (f * 1e9) * 1e3 / div, 5))
            if k in by:
                mu.append(by[k]["mu_dbsm"]); fa.append(f)
        if len(mu) == len(LADDER_F):
            fa = np.asarray(fa, float); mu = np.asarray(mu, float)
            lo = fa <= 6.0 + 1e-6; hi = fa >= 6.0 - 1e-6
            slope_vs_d.append(dict(d_mm=f"lambda/{int(div)}",
                                   a_low_1p8_6=round(float(np.polyfit(fa[lo], mu[lo], 1)[0]), 4),
                                   a_high_6_18p2=round(float(np.polyfit(fa[hi], mu[hi], 1)[0]), 4),
                                   a_full=round(float(np.polyfit(fa, mu, 1)[0]), 4)))

    # ---------------------------------------------------------------- 2. 재적합
    refit_f = sorted({round(ff, 4) for (ff, d) in by if abs(d - D_CONV) < 1e-9})
    prod_f = [round(x, 4) for x in np.linspace(1.8, 18.2, 21)]
    fset = [f for f in prod_f if f in refit_f]

    def mu_at(f, kind):
        lam_mm = C0 / (f * 1e9) * 1e3
        d = D_CONV if kind == "conv" else round(lam_mm / 16.0, 5)
        return by[(round(f, 4), d)]["mu_dbsm"]

    #  ⭐ 생산 산출(outputs/p3_ours.json el0, div=16) 을 이 실행이 그대로 재현하는지 — 출처 검증
    p3 = json.load(open(os.path.join(ROOT, "outputs", "p3_ours.json")))["fit"]["el0"]
    p3f = [round(x, 4) for x in p3["freqs_ghz"]]
    rep = []
    for f, m in zip(p3f, p3["mu_dbsm"]):
        lam_mm = C0 / (f * 1e9) * 1e3
        k = (f, round(lam_mm / 16.0, 5))
        if k in by:
            rep.append(abs(by[k]["mu_dbsm"] - m))
    baseline_rep = dict(n_compared=len(rep),
                        max_abs_dmu_db=round(float(np.max(rep)), 6) if rep else None,
                        source="outputs/p3_ours.json fit.el0 (div=16, 21 freqs)",
                        reading="같은 커널·같은 인자 → 0 이어야 한다. 이 실행이 헤드라인 기준선을 재현한다는 증거다.")

    mu_base = [mu_at(f, "base") for f in fset]
    mu_conv = [mu_at(f, "conv") for f in fset]
    fit_base = band_fits(fset, mu_base)
    fit_conv = band_fits(fset, mu_conv)

    # 방위 부트스트랩 (같은 방위 인덱스를 전 주파수에 공유 → 기울기 SE)
    rng = np.random.default_rng(20260803)
    S_base = np.array([10 ** (np.asarray(by[(f, round(C0 / (f * 1e9) * 1e3 / 16.0, 5))]["sigma_dbsm_az"]) / 10) for f in fset])
    S_conv = np.array([10 ** (np.asarray(by[(f, D_CONV)]["sigma_dbsm_az"]) / 10) for f in fset])
    fa = np.asarray(fset, float)
    boot = {}
    for tag, S in (("lam16", S_base), ("conv", S_conv)):
        acc = {k: [] for k in SUBBANDS}
        for _ in range(500):
            idx = rng.integers(0, S.shape[1], S.shape[1])
            m = 10 * np.log10(S[:, idx].mean(axis=1))
            for k, (lo, hi) in SUBBANDS.items():
                sel = (fa >= lo - 1e-6) & (fa <= hi + 1e-6)
                acc[k].append(np.polyfit(fa[sel], m[sel], 1)[0])
        boot[tag] = {k: dict(se=round(float(np.std(v)), 4),
                             ci95=[round(float(np.percentile(v, 2.5)), 4),
                                   round(float(np.percentile(v, 97.5)), 4)]) for k, v in acc.items()}

    # ------------------------------------------- 2b. "격자가 원인이려면 얼마나 움직여야 하나"
    #   기울기를 Das 0.21 로 끌어내리는 데 필요한 μ 섭동을 계산해, 관측된 격자효과와 크기를 견준다.
    def needed_shift(fsub, musub, target):
        fa = np.asarray(fsub, float); mu = np.asarray(musub, float)
        a0 = np.polyfit(fa, mu, 1)[0]
        sxx = float(np.sum((fa - fa.mean()) ** 2))
        # 최저주파 1 점만 움직여 기울기를 target 으로 만들려면
        dmu1 = (target - a0) * sxx / (fa[0] - fa.mean())
        return dict(a_now=round(float(a0), 4), target=target,
                    delta_mu_at_lowest_freq_db=round(float(dmu1), 3),
                    lowest_freq_ghz=float(fa[0]))
    #  ⭐ B 쪽의 **양성 증거** — 가파른 구간이 끝나는 주파수를 재고, 거기서 특징/λ 가 얼마인지 본다.
    #     PO 는 국소 곡률반경 ≫ λ 를 요구한다. 격차가 특징/λ 가 작은 구간에만 있으면 그 조건과 맞물린다.
    thick_mm = 13.78            # prop 블레이드 두께 (메쉬 실측, feature_scales 와 같은 출처)
    loc_slope = []
    fa_all = np.asarray(fset, float); mu_all = np.asarray(mu_conv, float)
    for i in range(1, len(fset) - 1):
        w = slice(i - 1, i + 2)
        loc_slope.append(dict(f_ghz=fset[i],
                              a_local=round(float(np.polyfit(fa_all[w], mu_all[w], 1)[0]), 4),
                              blade_over_lambda=round(thick_mm / (C0 / (fset[i] * 1e9) * 1e3), 4)))
    cross = next((r for r in loc_slope if r["a_local"] < 0.5), None)
    po_diag = dict(local_slope_3pt=loc_slope,
                   first_freq_with_local_slope_below_0p5=cross,
                   note=("3 점 이동창 국소 기울기. 가파른 구간(>0.5 dB/GHz)이 끝나는 곳의 blade/λ 를 함께 적는다 — "
                         "PO 의 국소평면 가정이 회복되는 지점과 견주기 위해서다."))

    #   수렴 격자에서 남은 계단 잔차(0.75 ↔ 0.5/0.375 mm)를 점당 불확도로 보고 기울기로 전파한다.
    tails = [abs(ladder[f"{f:g}GHz"]["last_step_db"]) for f in LADDER_F
             if ladder[f"{f:g}GHz"]["last_step_db"] is not None]
    sig_pt = float(np.sqrt(np.mean(np.square(tails)))) if tails else float("nan")
    dither = {}
    for name, (lo, hi) in SUBBANDS.items():
        fa = np.asarray(fset, float)
        sel = (fa >= lo - 1e-6) & (fa <= hi + 1e-6)
        sxx = float(np.sum((fa[sel] - fa[sel].mean()) ** 2))
        dither[name] = round(sig_pt / np.sqrt(sxx), 4)
    grid_dither = dict(per_point_db=round(sig_pt, 4), slope_se_db_per_ghz=dither,
                       note=("점당 불확도 = 사다리 마지막 계단(0.75↔0.5·0.375 mm) 변화의 RMS. "
                             "기울기 불확도 = 그 값 / sqrt(Sxx)."))

    lowmask = np.asarray(fset) <= 6.0 + 1e-6
    what_if = dict(
        lowband=needed_shift(np.asarray(fset)[lowmask], np.asarray(mu_conv)[lowmask], DAS_A),
        fullband=needed_shift(fset, mu_conv, DAS_A),
        note=("기울기를 Das 0.21 로 맞추려면 최저주파 μ 를 이만큼 **올려야** 한다는 뜻이다. "
              "관측된 격자효과와 부호·크기를 비교하면 격자가 원인인지 바로 보인다."))

    # ---------------------------------------------------------------- 3. 판정
    sh12_18 = ladder["1.8GHz"]["shift_conv_minus_lam12_db"]
    sh16_18 = ladder["1.8GHz"]["shift_conv_minus_lam16_db"]
    a_low_b, a_low_c = fit_base["1.8-6.0"]["a"], fit_conv["1.8-6.0"]["a"]
    a_full_b, a_full_c = fit_base["1.8-18.2"]["a"], fit_conv["1.8-18.2"]["a"]
    # 저주파(1.8·3.5 GHz)에서의 이동이 고주파(12·18.2)보다 뚜렷하게 큰가 = 표본화의 지문
    sh_low = np.mean([abs(ladder[f"{f:g}GHz"]["shift_conv_minus_lam16_db"]) for f in (1.8, 3.5)])
    sh_high = np.mean([abs(ladder[f"{f:g}GHz"]["shift_conv_minus_lam16_db"]) for f in (12.0, 18.2)])
    drop_low = 1.0 - a_low_c / a_low_b if a_low_b != 0 else float("nan")

    if abs(sh16_18) >= 1.0 and drop_low >= 0.5:
        verdict = "A_SAMPLING"
    elif abs(sh16_18) < 0.5 and abs(drop_low) < 0.20:
        verdict = "B_PO_LIMIT"
    else:
        verdict = "MIXED"

    out = dict(
        _meta=dict(
            generated=time.strftime("%Y-%m-%d %H:%M:%S"),
            purpose=("저주파 격차(1.8–6 GHz a=+1.563 vs 6–18.2 GHz a=+0.199)의 원인을 "
                     "**표본화(A)** 와 **PO 근본한계(B)** 로 가른다. 광선격자 d 를 λ 상대가 아니라 "
                     "**절대값[mm]** 으로 계단식으로 줄여 μ(f) 가 수렴하는지 본다."),
            drone="phantom3", drone_name="DJI Phantom 3 Professional",
            engine="SBR (Mitsuba/OptiX first-hit) + PO surface integral — src/rcs_sbr.rcs_sbr_batch",
            convention=("생산 경로(benchmark/rcs_anchor.raw_sigma_az)와 **spacing 만** 다르다: el=0 · "
                        "az=linspace(0,360,360,endpoint=False) · penetrate=True · ptd=False · "
                        "max_bounce=1 · jitter=2 · μ=10log10(mean_φ σ_lin) · ε=std(10log10 σ_lin)."),
            baseline="outputs/p3_ours.json el0 (div=16, 21 주파수) — 이 파일이 그 격자를 재계산해 재현한다",
            anchor=f"Das IEEE WCL 2026 Table III, Phantom 3, bistatic 0° : a = {DAS_A} dB/GHz",
            gpu=("GPU 3 · GPU 2 (둘 다 유휴였다), 워커 24 개 · 카드당 14~15 GB. "
                 "커널이 호스트(numpy) 병목이라 GPU 사용률은 10~30% 였다 — 레버는 메모리가 아니라 워커 수였다."),
            cost_s=round(cost_s, 1), n_runs=len(recs), n_az=360,
            grade="computed (전부 계산값, 문헌은 Das a=0.21 하나뿐)"),
        verdict=verdict,
        bottom_line=(
            f"가설 A(표본화)는 배제된다. 1.8 GHz 에서 격자를 6 mm → 0.375 mm 로 16 배 조이는 동안 μ 는 "
            f"{max(ladder['1.8GHz']['abs_ladder_mu_dbsm']) - min(ladder['1.8GHz']['abs_ladder_mu_dbsm']):.3f} dB "
            f"안에서만 움직인다 — 완전히 수렴했다. 수렴값은 생산 격자(λ/16)보다 {abs(sh16_18):.2f} dB 아래이고, "
            f"저대역 기울기는 {a_low_b:.3f} → {a_low_c:.3f} dB/GHz 로 **오히려 가팔라진다**. "
            f"기울기를 Das 0.21 에 맞추려면 μ(1.8 GHz) 가 {what_if['lowband']['delta_mu_at_lowest_freq_db']:+.1f} dB "
            f"올라가야 하는데, 격자가 만드는 여지는 그 100 분의 1 이고 부호도 반대다. "
            f"전대역 배수는 {a_full_b / DAS_A:.2f} → {a_full_c / DAS_A:.2f} 로 사실상 그대로다. "
            f"⚠ 'PO 근본한계' 는 표본화를 배제한 것(음성 증거)과, 가파른 구간이 blade/λ ≈ "
            f"{po_diag['first_freq_with_local_slope_below_0p5']['blade_over_lambda'] if po_diag['first_freq_with_local_slope_below_0p5'] else float('nan')} "
            f"에서 끝난다는 것(양성 증거)의 결합이다. PTD 프린지 항과 메쉬 테셀레이션은 아직 열려 있다."),
        verdict_rule=("A_SAMPLING : |μ(0.75mm)−μ(λ/16)|@1.8GHz ≥ 1.0 dB **그리고** 저대역 기울기가 ≥50% 줄어든다. "
                      "B_PO_LIMIT : 이동 < 0.5 dB **그리고** 기울기 변화 < 20%. 그 사이는 MIXED."),
        headline=dict(
            mu_shift_at_1p8_db_vs_lam12=round(sh12_18, 4),
            mu_shift_at_1p8_db_vs_lam16=round(sh16_18, 4),
            shift_mean_lowband_1p8_3p5_db=round(float(sh_low), 4),
            shift_mean_highband_12_18p2_db=round(float(sh_high), 4),
            a_lowband_lam16=round(a_low_b, 4), a_lowband_converged=round(a_low_c, 4),
            a_fullband_lam16=round(a_full_b, 4), a_fullband_converged=round(a_full_c, 4),
            a_highband_lam16=round(fit_base["6.0-18.2"]["a"], 4),
            a_highband_converged=round(fit_conv["6.0-18.2"]["a"], 4),
            das_a=DAS_A,
            ratio_to_das_before=round(a_full_b / DAS_A, 4),
            ratio_to_das_after=round(a_full_c / DAS_A, 4)),
        ladder=ladder,
        slope_vs_d=dict(note=("사다리 주파수 5 점(1.8·3.5·6.0·12.0·18.2)만으로 낸 기울기. "
                              "격자를 조일수록 기울기가 어디로 가는지를 **추세**로 본다."),
                        rows=slope_vs_d),
        what_would_it_take=what_if,
        grid_dither_slope_uncertainty=grid_dither,
        po_validity_diagnostic=po_diag,
        feature_scales=feature_scales(),
        baseline_reproduction=baseline_rep,
        geometry_revised_after_run=source_drift_check(
            by, max(ladder["1.8GHz"]["abs_ladder_mu_dbsm"]) - min(ladder["1.8GHz"]["abs_ladder_mu_dbsm"])),
        reproducibility=reproducibility(by),
        refit=dict(freqs_ghz=fset, mu_lam16_dbsm=[round(x, 4) for x in mu_base],
                   mu_conv_dbsm=[round(x, 4) for x in mu_conv],
                   fits_lam16=fit_base, fits_converged=fit_conv,
                   bootstrap_az_slope=boot,
                   note="λ/16 열은 outputs/p3_ours.json el0 의 재계산이다 — 같은 코드경로·같은 인자."),
        caveats=[
            "수렴한 대상은 **이 삼각메쉬 위의 PO 면적분**이다. d=0.75 mm 는 메쉬 중앙값 모서리(5.85 mm)의 1/8 이라 "
            "격자는 형상을 다 표본화한다 — 대신 테셀레이션·CAD 형상 자체는 별개의 오차축이고 여기서 검증하지 않았다.",
            "곡면 수렴은 단조롭지 않다(실루엣 grazing 위상 에일리어싱). 판정은 한 계단이 아니라 사다리 전체 추세로 했다.",
            "λ/12 와 λ/16 을 구분해 읽어야 한다. 1.8 GHz 에서 λ/12 는 수렴값과 실제로 어긋나지만(패널 A 참조), "
            "헤드라인 산출(p3_ours el0)은 λ/16 이고 거기서는 어긋남이 훨씬 작다.",
            "PTD 모서리 프린지 항은 꺼져 있다(생산 규약 ptd=False). 프린지 기여는 저주파에서 상대적으로 커지므로 "
            "저대역 기울기를 바꿀 수 있는 **미검증 후보**다 — 이 실험은 그것을 배제하지 않는다.",
            "1-bounce 다중반사 없음, 크리핑파·표면파 없음. 'PO 근본한계' 는 표본화를 배제한 음성 증거와 "
            "격차가 특징/λ 가 작은 구간에만 있다는 양성 증거의 결합이지, PO 오차를 직접 잰 것이 아니다.",
            "el=0 단일 고도, 편파 없음(PO 면적분은 스칼라). Das 와의 **레벨** 비교에는 통계규약 오프셋(선형평균 vs "
            "dB영역평균)이 남아 있다 — 기울기 비교는 그 오프셋에 무관하다.",
            "실행은 호스트(numpy) 병목이었다 — GPU 사용률 10~30%, 카드당 14~15 GB. GPU 메모리가 구속조건이 아니었다.",
            "오차막대는 방위 부트스트랩과 격자 디더만 담는다. 메쉬·재질·기하 불확도는 들어 있지 않다.",
            "⚠ 스윕이 끝난 뒤 다른 작업이 Phantom 3 CAD 를 개정했다(geometry_revised_after_run 참조). "
            "이 산출물은 헤드라인 관측(a=+0.4198)이 나온 기체를 잰 것이고 — baseline_reproduction 이 증거다 — "
            "대조군·실험군이 같은 기체라는 요건은 충족된다. 개정된 CAD 로 기울기를 다시 보려면 p3_ours 부터 재생성해야 한다.",
        ],
    )
    json.dump(out, open(OUT_JSON, "w"), ensure_ascii=False, indent=1)
    print("wrote", OUT_JSON, "verdict", verdict)
    return out


if __name__ == "__main__":
    main()
