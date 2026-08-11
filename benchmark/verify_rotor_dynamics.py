# -*- coding: utf-8 -*-
"""
verify_rotor_dynamics.py — 로터 랜덤성 **게이트 + 효과 측정** (2026-08-11)
==============================================================================
설계서 `docs/NOISE_AND_ROTOR_PLAN.md` §3-1 · §3-4 의 게이트를 스크립트 하나로 자동화한다.
원장: `outputs/verify_rotor_dynamics.json` · `outputs/rotor_jitter_effect.json`

두 부분이다.

**A. 게이트** — «제대로 들어갔나»
  G4  legacy 프리셋 rpm_t 가 기존 원장(`report07_hover_long.npz`)과 **비트동일**
  G5  `articulated_fast.rotor_phases()` 1차원 경로 **비트동일**
  G6  `md_classify_dataset.synth()` 1차원 경로 + `_draw_trials(jit=None)` 난수열 **비트동일**
  G17 OU 정상상태 std = σ_w ± 5 % (≥100 T)
  G18 lag-1 자기상관 = exp(−dt/T) ± 1e-4
  G19 PSD 기울기 = −20 dB/decade ± 2 (코너 위)
  G20 대역 rms 역보정 — 생성한 ε 의 0.3–5 / 0.3–2 Hz 등가사인 진폭이 실기 로그 앵커를 ±10 % 로 복원
  G21 위상 적분 무결성 — d θ/dt·60/360 == rpm_t (rel ≤ 1e-12)
  G22 초기위상 분포 — KS 검정 vs U(0, 360/blades), p > 0.01
  G23 선폭 예측 — m 차 조화의 폭 ∝ m·f_flash·σ_w (상관 ≥ 0.95)

**B. 효과** — «켜면 무엇이 달라지나» (⭐이쪽이 본론이다)
  E1 반창 스펙트럼 상관(`half_corr`) — report15b 가 «시간에 따라 변한다» 를 재는 그 지표
  E2 분류 특징 27 개 중 몇 개가 움직이나 — 창 0.25 s 팔과 1.0 s 팔을 나란히

⚠ B 는 **위상표**(`outputs/md_classify_tables/`)로 합성한다. 표는 각도의 함수라 rpm 이
  시간에 따라 변해도 다시 만들 필요가 없다 — **GPU 가 한 톨도 안 든다.**
  실제 SBR 맵의 확인은 `report07_hover_long.py --preset outdoor` 가 따로 한다.

    python benchmark/verify_rotor_dynamics.py            # 전부
    python benchmark/verify_rotor_dynamics.py --only gates
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np                                                      # noqa: E402
import rotor_dynamics as rd                                             # noqa: E402

OUT = os.path.join(ROOT, "outputs")
TAB_DIR = os.path.join(OUT, "md_classify_tables")


def _g(gid, what, ok, measured, spec, note=""):
    return {"id": gid, "what": what, "pass": bool(ok),
            "measured": measured, "spec": spec, "note_ko": note}


# ═══════════════════════════════════════════════════════════════════════════
#  A. 게이트
# ═══════════════════════════════════════════════════════════════════════════
def gates() -> dict:
    from articulated_fast import rotor_phases
    from scipy.stats import kstest
    import md_classify_dataset as mcd

    G = []

    # ── G4 · legacy 비트동일 ────────────────────────────────────────────────
    for name, npz in (("legacy", "report07_hover_long.npz"),
                      ("legacy_outdoor", "report07_hover_long_outdoor.npz")):
        p = os.path.join(OUT, npz)
        if not os.path.exists(p):
            G.append(_g("G4/" + name, f"{npz} 없음", False, None, "bit-identical"))
            continue
        z = np.load(p)
        meta = json.load(open(p.replace(".npz", ".json")))["_meta"]
        ref = z["rpm_t"]
        got, _ = rd.rpm_series(meta["rpm0"], ref.shape[1], meta["n"], meta["prf_hz"],
                               name, np.random.default_rng(0))
        d = float(np.abs(got - ref).max())
        G.append(_g(f"G4/{name}", f"rotor_dynamics '{name}' vs {npz} rpm_t",
                    np.array_equal(got, ref), {"max_abs_diff": d}, "bit-identical (0.0)",
                    "결정론 경로라 시드와 무관해야 한다"))

        # 위상 적분도 옛 식과 같은가
        dirs = np.array([1.0, -1.0] * (ref.shape[1] // 2) + [1.0] * (ref.shape[1] % 2))
        old = dirs[None, :] * np.cumsum(360.0 * ref / 60.0 * (1.0 / meta["prf_hz"]), axis=0)
        new = rd.phases(ref, meta["prf_hz"], dirs)
        G.append(_g(f"G4b/{name}", "rd.phases(2D) vs report07 옛 cumsum 식",
                    np.array_equal(old, new),
                    {"max_abs_diff": float(np.abs(old - new).max())}, "bit-identical"))

    # ── G5 · rotor_phases 1차원 ─────────────────────────────────────────────
    t = np.arange(4096) / 5000.0
    rpm1 = np.array([3800.0, 3790.5, 3805.25, 3794.125])
    dirs = np.array([1.0, -1.0, 1.0, -1.0])
    b = np.array([11.0, 222.0, 33.0, 144.0])
    exp_b = b[None, :] + dirs[None, :] * (360.0 * rpm1[None, :] / 60.0) * t[:, None]
    exp_0 = np.zeros(4)[None, :] + dirs[None, :] * (360.0 * rpm1[None, :] / 60.0) * t[:, None]
    ok5 = (np.array_equal(rotor_phases(t, rpm1, dirs, b), exp_b)
           and np.array_equal(rotor_phases(t, rpm1, dirs), exp_0))
    G.append(_g("G5", "articulated_fast.rotor_phases() 1차원 경로", ok5,
                {"base_given": True, "base_none": True}, "bit-identical",
                "2차원 확장이 1차원 산술을 안 건드렸는지"))

    # ── G6 · md_classify 기본 경로 ──────────────────────────────────────────
    #   ① synth(): 위상 계산을 커널로 옮겼는데 옛 인라인 식과 같은가
    zt = np.load(os.path.join(TAB_DIR, "matrice4e_a06.npz"), allow_pickle=True)
    E_ref = complex(zt["E_ref"][0])
    fine = mcd._fine_tables(zt["dE"], zt["phis"])
    dsr = np.asarray(zt["dirs"], float)
    p0 = np.array([13.0, 77.0, 155.0, 4.0])
    prf, n_t = 20000.0, 5000
    E_new = mcd.synth(E_ref, fine, dsr, rpm1, p0, prf, n_t)

    def _synth_old(E_ref, fine, dirs, rpms, p0, prf, n_t):
        n_fine = fine.shape[1]
        tt = np.arange(n_t) / prf
        E = np.full(n_t, E_ref, complex)
        for k in range(fine.shape[0]):
            ph = p0[k] + dirs[k] * (360.0 * rpms[k] / 60.0) * tt
            idx = np.mod(ph / mcd.PHASE_PERIOD_DEG * n_fine, n_fine)
            i0 = np.floor(idx).astype(np.int64) % n_fine
            i1 = (i0 + 1) % n_fine
            w = idx - np.floor(idx)
            E += fine[k, i0] * (1 - w) + fine[k, i1] * w
        return E
    E_old = _synth_old(E_ref, fine, dsr, rpm1, p0, prf, n_t)
    G.append(_g("G6a", "md_classify_dataset.synth() 1차원 경로",
                np.array_equal(E_new, E_old),
                {"max_abs_diff": float(np.abs(E_new - E_old).max())}, "bit-identical"))

    #   ② _draw_trials(jit=None): 난수 소모 순서까지 같은가
    from drones import DRONES
    spec = DRONES["matrice4e"]
    r1 = np.random.default_rng(mcd.SEED)
    got = [mcd._draw_trials(r1, spec, 4, None) for _ in range(5)]
    r2 = np.random.default_rng(mcd.SEED)
    exp = []
    for _ in range(5):
        base = float(spec.hover_rpm) * float(r2.uniform(1 - mcd.RPM_BASE_FRAC,
                                                        1 + mcd.RPM_BASE_FRAC))
        sig = float(r2.uniform(mcd.RPM_SPREAD_LO, mcd.RPM_SPREAD_HI))
        d = r2.normal(0.0, sig, 4)
        d = d - d.mean()
        exp.append((base * (1.0 + d), r2.uniform(0.0, mcd.PHASE_PERIOD_DEG, 4), base, sig))
    ok6 = all(np.array_equal(a[0], b_[0]) and np.array_equal(a[1], b_[1])
              and a[2] == b_[2] and a[3] == b_[3] for a, b_ in zip(got, exp))
    G.append(_g("G6b", "md_classify_dataset._draw_trials(jit=None) 난수열", ok6,
                {"n_draws": 5}, "bit-identical",
                "RNG 소모 순서가 같아야 기존 특징행렬이 재현된다"))

    # ── G17~G19 · OU 통계 (성근 격자 끄고 직접 생성) ────────────────────────
    TAU = rd.TAU_CTL_S
    sig_w = 0.0245
    fs = 200.0
    n = int(round(400.0 * TAU * fs))          # 400 T
    e = rd.ou_process(n, 1.0 / fs, sig_w, TAU, np.random.default_rng(11), n_ch=8)
    std = float(e.std())
    G.append(_g("G17", "OU 정상상태 std", abs(std / sig_w - 1.0) <= 0.05,
                {"std": std, "sigma_w": sig_w, "rel_err": std / sig_w - 1.0,
                 "n_tau": 400, "n_ch": 8}, "|std/σ_w − 1| ≤ 0.05"))
    #  ⚠ 설계서(§3-4 G18)는 «표본 lag-1 자기상관이 exp(−dt/T) ± 1e-4» 였다.
    #    그 합격선은 **통계적으로 불가능**하다 — AR(1) 의 표본 상관은 표준오차가
    #    √((1−a²)/N) 이라 ±1e-4 를 만족하려면 N ≳ 4×10⁶ 표본이 필요하고, 그래도
    #    실행마다 부호가 바뀐다. 그래서 게이트를 **둘로 쪼갠다**:
    #      G18a 이산화 계수 자체가 exp(−dt/T) 인가 — 결정론, 비트 수준(이것이 구현 게이트다)
    #      G18b 표본 상관이 그 값과 통계오차 안에서 맞나 — 4·SE
    a_impl = rd.ou_process(3, 1.0 / fs, 1.0, TAU, np.random.default_rng(0), n_ch=1)
    rr = np.random.default_rng(0)
    w = rr.standard_normal((3, 1))
    aa = float(np.exp(-(1.0 / fs) / TAU))
    ss = float(np.sqrt(1.0 - aa * aa))
    manual = np.empty((3, 1))
    manual[0] = w[0]
    for i in (1, 2):
        manual[i] = aa * manual[i - 1] + ss * w[i]
    G.append(_g("G18a", "OU 이산화 계수 a = exp(−dt/T) (결정론)",
                np.array_equal(a_impl, manual),
                {"a": aa, "sigma_step": ss,
                 "max_abs_diff": float(np.abs(a_impl - manual).max())},
                "bit-identical", "정확 이산화인가 — 근사(오일러)면 여기서 깨진다"))
    lag1 = float(np.mean([np.corrcoef(e[:-1, k], e[1:, k])[0, 1] for k in range(e.shape[1])]))
    pred = float(np.exp(-(1.0 / fs) / TAU))
    se = float(np.sqrt((1.0 - pred ** 2) / e.size))
    G.append(_g("G18b", "lag-1 표본 자기상관", abs(lag1 - pred) <= 4.0 * se,
                {"measured": lag1, "predicted_exp_dt_over_T": pred,
                 "diff": lag1 - pred, "se": se, "n_samples": int(e.size),
                 "design_spec_was": "±1e-4 — 통계적으로 불가능해 4·SE 로 바꿨다"},
                "|Δ| ≤ 4·SE"))

    s = rd.summary(1000.0 * (1.0 + e), fs, rd.PRESETS["outdoor"])
    slope = s.get("psd_slope_db_per_decade", float("nan"))
    G.append(_g("G19", "PSD 기울기(코너 위)", abs(slope + 20.0) <= 2.0,
                {"slope_db_per_decade": slope, "band_hz": s.get("psd_slope_band_hz")},
                "−20 ± 2 dB/decade", "1극 저역통과의 지문. 백색이면 0 이 나온다"))

    # ── G20 · 대역 rms 역보정 ───────────────────────────────────────────────
    g20 = {}
    ok20 = True
    for nm, sig, (f1, f2), amp_anchor in (("indoor", 0.0065, (0.3, 5.0), 0.74),
                                          ("outdoor", 0.0245, (0.3, 2.0), 2.52)):
        ee = rd.ou_process(int(round(400.0 * TAU * fs)), 1.0 / fs, sig, TAU,
                           np.random.default_rng(23), n_ch=8)
        st = rd.summary(1000.0 * (1.0 + ee), fs, bands=((f1, f2),))
        amp = st["band_rms_rel"][f"amp_equiv_sine_{f1}-{f2}Hz"] * 100.0
        rel = amp / amp_anchor - 1.0
        g20[nm] = {"band_hz": [f1, f2], "amp_equiv_sine_pct": amp,
                   "anchor_pct": amp_anchor, "rel_err": rel,
                   "sigma_w_from_formula": rd.sigma_w_from_band_amp(amp_anchor / 100.0, f1, f2),
                   "sigma_w_in_preset": sig}
        ok20 &= abs(rel) <= 0.10
    G.append(_g("G20", "대역 rms 역보정 — 생성한 ε 가 실기 로그 앵커를 되돌려주나", ok20,
                g20, "|rel| ≤ 0.10",
                "σ_w = (amp/√2)/√F 보정이 맞는지. 틀리면 프리셋 σ 가 통째로 어긋난다"))

    # ── G21 · 위상 적분 무결성 ──────────────────────────────────────────────
    prf2 = 19700.0
    rpm_t, _ = rd.rpm_series(3800.0, 4, 8000, prf2, "outdoor", np.random.default_rng(5))
    th = rd.phases(rpm_t, prf2, dirs, base_deg=np.array([10.0, 20.0, 30.0, 40.0]))
    back = np.diff(th, axis=0) / (1.0 / prf2) * 60.0 / 360.0 / dirs[None, :]
    rel = float(np.abs(back / rpm_t[1:] - 1.0).max())
    #  ⚠ 설계서(G21)의 «≤ 1e-12» 는 부동소수 하한 아래다. diff(cumsum) 은 큰 누적각을
    #    빼는 **상쇄**라 상대오차 하한이 ≈ eps·θ_max/Δθ 다. 실측 1.7e-12 가 정확히
    #    그 자리다. 그래서 합격선을 그 하한의 10 배로 둔다(구현 결함은 이보다 훨씬 크다).
    theta_max = float(np.abs(th).max())
    dtheta = float(np.abs(np.diff(th, axis=0)).mean())
    floor = float(np.finfo(float).eps * theta_max / dtheta)
    G.append(_g("G21", "위상 적분 무결성 dθ/dt·60/360 == rpm", rel <= 10.0 * floor,
                {"max_rel_err": rel, "roundoff_floor": floor,
                 "theta_max_deg": theta_max, "mean_step_deg": dtheta,
                 "design_spec_was": "≤1e-12 — 상쇄오차 하한 아래라 10·floor 로 바꿨다"},
                "≤ 10 × eps·θ_max/Δθ"))

    # ── G22 · 초기위상 분포 ─────────────────────────────────────────────────
    rr = np.random.default_rng(99)
    ph0 = np.concatenate([rd.initial_phase_deg(4, rd.PRESETS["outdoor"], rr, 180.0)
                          for _ in range(1000)])
    ks = kstest(ph0 / 180.0, "uniform")
    G.append(_g("G22", "초기위상 θ_k(0) ~ U(0, 360/blades)", ks.pvalue > 0.01,
                {"n": int(ph0.size), "ks_stat": float(ks.statistic),
                 "p_value": float(ks.pvalue), "min": float(ph0.min()),
                 "max": float(ph0.max())}, "KS p > 0.01"))
    ph_leg = rd.initial_phase_deg(4, rd.PRESETS["legacy"], np.random.default_rng(1), 180.0)
    G.append(_g("G22b", "legacy 는 여전히 정렬(0)", bool(np.all(ph_leg == 0.0)),
                {"phases": ph_leg.tolist()}, "all zero"))

    # ── G23 · 선폭 ∝ m·f_flash·σ_w ─────────────────────────────────────────
    g23 = _linewidth_gate()
    G.append(_g("G23", "m 차 조화 선폭 ∝ m·f_flash·σ_w", g23["r"] >= 0.95,
                g23, "Pearson r ≥ 0.95",
                "랜덤과정은 선을 **넓힌다**. 정현파였다면 폭 대신 빗살이 생긴다"))

    return {"gates": G,
            "n_pass": sum(1 for g in G if g["pass"]), "n_total": len(G)}


def _linewidth_gate():
    """2 s CPI 에서 m 차 조화의 rms 대역폭이 m·f_flash·σ_w 에 비례하나."""
    import md_classify_dataset as mcd
    z = np.load(os.path.join(TAB_DIR, "matrice4e_a06.npz"), allow_pickle=True)
    E_ref = complex(z["E_ref"][0])
    fine = mcd._fine_tables(z["dE"], z["phis"])
    dirs = np.asarray(z["dirs"], float)
    prf, n_t = 19700.0, 39400
    rpm0, f_flash = 3800.0, 3800.0 / 60.0 * 2.0
    rows = []
    for sw in (0.0, 0.0065, 0.0125, 0.0245, 0.05):
        jit = rd.RotorJitter(name="probe", static_sigma=0.0, wobble_sigma=sw,
                             random_phase=False)
        widths = []
        for seed in (3, 17, 29):
            rpm_t, _ = rd.rpm_series(rpm0, len(dirs), n_t, prf, jit,
                                     np.random.default_rng(seed))
            E = mcd.synth(E_ref, fine, dirs, rpm_t, np.zeros(len(dirs)), prf, n_t)
            ac = E - E.mean()
            #  ⚠ E 는 복소라 rfft 를 못 쓴다 — 양의 도플러 쪽만 잘라 쓴다
            S = np.abs(np.fft.fft(ac * np.hanning(n_t))) ** 2
            f = np.fft.fftfreq(n_t, 1.0 / prf)
            pos = f >= 0
            S, f = S[pos], f[pos]
            w = []
            for m in (1, 2, 4, 8):
                fc = m * f_flash
                #  ⚠ 창을 ±0.40·f_flash 로 둔다. 좁으면 넓어진 선의 꼬리가 잘려
                #    폭이 인위적으로 포화한다(±0.25 로 재면 r 0.94 로 떨어졌다).
                sel = np.abs(f - fc) <= 0.40 * f_flash
                p = S[sel]
                p = np.maximum(p - np.median(p), 0.0)
                if p.sum() <= 0:
                    w.append(np.nan)
                    continue
                ff = f[sel]
                mu = (ff * p).sum() / p.sum()
                w.append(float(np.sqrt(((ff - mu) ** 2 * p).sum() / p.sum())))
            widths.append(w)
        wm = np.nanmean(np.asarray(widths), axis=0)
        for m, ww in zip((1, 2, 4, 8), wm):
            rows.append({"sigma_w": sw, "m": m, "pred_hz": m * f_flash * sw,
                         "rms_width_hz": float(ww)})
    pred = np.array([r["pred_hz"] for r in rows])
    meas = np.array([r["rms_width_hz"] for r in rows])
    base = float(np.nanmean([x["rms_width_hz"] for x in rows if x["sigma_w"] == 0.0]))
    #  σ_w = 0 판이 «장비의 선폭»(2 s Hann 창) 이다. 그것을 직교로 뺀다.
    corr = np.sqrt(np.maximum(meas ** 2 - base ** 2, 0.0))
    ok = np.isfinite(meas) & (pred > 0)
    #  창 밖으로 새는 자리는 제외한다 — 폭이 인접 조화에 닿으면 측정이 성립 안 한다
    fit = ok & (pred <= 0.25 * f_flash)
    r = float(np.corrcoef(pred[fit], corr[fit])[0, 1])
    slope = float((pred[fit] * corr[fit]).sum() / (pred[fit] ** 2).sum())
    for row, c in zip(rows, corr):
        row["rms_width_floor_removed_hz"] = float(c)
        row["used_in_fit"] = bool(row["pred_hz"] > 0 and row["pred_hz"] <= 0.25 * f_flash)
    return {"r": r, "n": int(fit.sum()), "slope": slope, "rows": rows,
            "r_raw_all_points": float(np.corrcoef(pred[ok], meas[ok])[0, 1]),
            "zero_wobble_baseline_width_hz": base,
            "slope_note_ko": ("기울기가 1 이 아니라 ≈0.87 이다 — 중앙값 빼기와 Hann 창이 "
                              "선의 꼬리를 깎기 때문이다. 게이트는 **비례성**(r)이지 "
                              "절대 폭이 아니다."),
            "cpi_s": n_t / prf, "doppler_bin_hz": prf / n_t, "f_flash_hz": f_flash}


# ═══════════════════════════════════════════════════════════════════════════
#  B. 효과
# ═══════════════════════════════════════════════════════════════════════════
_TAB = {}


def _load_tab(key, ai):
    import md_classify_dataset as mcd
    k = (key, ai)
    if k not in _TAB:
        z = np.load(os.path.join(TAB_DIR, f"{key}_a{ai:02d}.npz"), allow_pickle=True)
        _TAB[k] = (complex(z["E_ref"][0]), mcd._fine_tables(z["dE"], z["phis"]),
                   np.asarray(z["dirs"], float))
    return _TAB[k]


def _half_corr(E):
    """report15b `_analyse` 와 **같은 식** — 창을 반으로 갈라 두 스펙트럼의 상관."""
    ac = np.asarray(E) - np.mean(E)
    h = len(ac) // 2
    S1 = np.abs(np.fft.fft(ac[:h] * np.hanning(h)))
    S2 = np.abs(np.fft.fft(ac[h:2 * h] * np.hanning(h)))
    return float(np.corrcoef(S1, S2)[0, 1])


def _series(key, ai, arm, seed, prf, n_t, rpm_scale=1.0):
    """한 시행의 슬로타임 열. arm 은 «locked» 또는 프리셋 이름 또는 «current»."""
    import md_classify_dataset as mcd
    from drones import DRONES
    E_ref, fine, dirs = _load_tab(key, ai)
    spec = DRONES[key]
    n_rot = len(dirs)
    rng = np.random.default_rng(seed)
    base = float(spec.hover_rpm) * rpm_scale
    if arm == "locked":
        rpms = np.full(n_rot, base)
        p0 = np.zeros(n_rot)
    elif arm == "current":                       # 현행 md_classify 모델
        sig = float(rng.uniform(mcd.RPM_SPREAD_LO, mcd.RPM_SPREAD_HI))
        d = rng.normal(0.0, sig, n_rot)
        d = d - d.mean()
        rpms = base * (1.0 + d)
        p0 = rng.uniform(0.0, mcd.PHASE_PERIOD_DEG, n_rot)
    else:
        jit = rd.get(arm)
        d = rd.static_offsets(n_rot, jit, rng)
        p0 = rd.initial_phase_deg(n_rot, jit, rng, period_deg=mcd.PHASE_PERIOD_DEG)
        if jit.wobble_sigma > 0:
            rpm_t, _ = rd.rpm_series(base, n_rot, n_t, prf,
                                     jit.with_(static_sigma=0.0), rng)
            rpms = rpm_t + (base * d)[None, :]
        else:
            rpms = base * (1.0 + d)
    return mcd.synth(E_ref, fine, dirs, rpms, p0, prf, n_t)


# ── E1 ─────────────────────────────────────────────────────────────────────
def effect_half_corr(arms, n_seed=8) -> dict:
    """report07 설정(matrice4e · 2 s · PRF 19,700)에서 반창 스펙트럼 상관."""
    prf, n_t, key, ai = 19700.0, 39400, "matrice4e", 6
    out = {"setting": {"drone": key, "aspect_index": ai, "az_deg": 0.0, "el_deg": -15.0,
                       "prf_hz": prf, "n_t": n_t, "seconds": n_t / prf,
                       "doppler_bin_hz": prf / n_t,
                       "source": "위상표 합성(GPU 불필요). 실제 SBR 판은 "
                                 "report07_hover_long.py 가 따로 낸다",
                       "metric": "report15b _analyse 의 half_window_spectrum_corr 와 같은 식"},
           "arms": {}}
    for arm in arms:
        vals, dc = [], []
        n = 1 if arm == "locked" else n_seed
        for s in range(n):
            E = _series(key, ai, arm, 1000 + s, prf, n_t)
            vals.append(_half_corr(E))
            dc.append(float(20 * np.log10(abs(E.mean()) / (np.std(E - E.mean()) + 1e-300))))
        out["arms"][arm] = {"half_corr_mean": float(np.mean(vals)),
                            "half_corr_std": float(np.std(vals)),
                            "half_corr_min": float(np.min(vals)),
                            "half_corr_max": float(np.max(vals)),
                            "n_seeds": n, "dc_ac_db_mean": float(np.mean(dc)),
                            "values": [float(v) for v in vals]}
    return out


# ── E2 ─────────────────────────────────────────────────────────────────────
def _feat_job(job):
    import md_classify_dataset as mcd
    key, ai, di, arm, seed, prf, T, scale = job
    n_t = int(round(prf * T))
    E = _series(key, ai, arm, seed, prf, n_t, rpm_scale=scale)
    v, _ = mcd.features(E, prf)
    return key, ai, di, arm, T, v, _half_corr(E)


def effect_features(arms, drones, n_draw=6, prf=20000.0, windows=(0.25, 1.0),
                    nproc=10) -> dict:
    import md_classify_dataset as mcd
    from multiprocessing import Pool
    rngs = np.random.default_rng(4242)
    scales = {}
    jobs = []
    for key in drones:
        for ai in range(18):
            if not os.path.exists(os.path.join(TAB_DIR, f"{key}_a{ai:02d}.npz")):
                continue
            for di in range(n_draw):
                #  ⭐ base rpm 흩뜨리기는 **모든 팔이 같은 값**을 쓴다 — 팔 사이 차이가
                #     로터 랜덤성에서만 오도록.
                sc = float(rngs.uniform(1 - mcd.RPM_BASE_FRAC, 1 + mcd.RPM_BASE_FRAC))
                scales[(key, ai, di)] = sc
                for T in windows:
                    for arm in arms:
                        jobs.append((key, ai, arm, 7_000_000 + 977 * di + 13 * ai, prf, T, sc))
    t0 = time.time()
    with Pool(nproc) as pool:
        res = pool.map(_feat_job, jobs, chunksize=8)
    print(f"  특징 {len(jobs)} 건 {time.time()-t0:.0f}s", flush=True)

    names = list(mcd.FEATURE_NAMES)
    acc = {}
    for key, arm, T, v in res:
        acc.setdefault((arm, T), []).append(v)
    base_arm = arms[0]
    out = {"_setting": {"prf_hz": prf, "n_draw_per_aspect": n_draw,
                        "drones": list(drones), "n_aspects": 18,
                        "windows_s": list(windows), "arms": list(arms),
                        "baseline_arm": base_arm, "n_features": len(names),
                        "note_ko": "효과크기 d = (평균_팔 − 평균_기준)/표준편차_기준. "
                                   "|d| ≥ 1 이면 «기준 팔의 시행간 산포 하나만큼 움직였다»."},
           "windows": {}}
    for T in windows:
        B = np.asarray(acc[(base_arm, T)], float)
        mb, sb = np.nanmean(B, axis=0), np.nanstd(B, axis=0)
        wrow = {"baseline_n": int(B.shape[0]), "arms": {}}
        for arm in arms[1:]:
            A = np.asarray(acc[(arm, T)], float)
            ma = np.nanmean(A, axis=0)
            d = (ma - mb) / np.where(sb > 0, sb, np.nan)
            per = {n: {"base_mean": float(mb[i]), "arm_mean": float(ma[i]),
                       "base_std": float(sb[i]), "d": float(d[i])}
                   for i, n in enumerate(names)}
            fin = d[np.isfinite(d)]
            wrow["arms"][arm] = {
                "n": int(A.shape[0]),
                "n_moved_d_ge_1": int((np.abs(fin) >= 1.0).sum()),
                "n_moved_d_ge_0p5": int((np.abs(fin) >= 0.5).sum()),
                "n_features_finite": int(fin.size),
                "median_abs_d": float(np.median(np.abs(fin))),
                "max_abs_d": float(np.max(np.abs(fin))),
                "top10": sorted(per.items(), key=lambda kv: -abs(kv[1]["d"]))[:10],
                "per_feature": per}
        out["windows"][str(T)] = wrow
    return out


# ═══════════════════════════════════════════════════════════════════════════
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="all", choices=["all", "gates", "effect"])
    ap.add_argument("--nproc", type=int, default=10)
    ap.add_argument("--n-draw", type=int, default=6)
    a = ap.parse_args()

    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    if a.only in ("all", "gates"):
        print("═══ 게이트 ═══", flush=True)
        gg = gates()
        gg["_meta"] = {"script": "benchmark/verify_rotor_dynamics.py gates",
                       "generated": stamp,
                       "design": "docs/NOISE_AND_ROTOR_PLAN.md §3-1 · §3-4",
                       "module": "src/rotor_dynamics.py"}
        for g in gg["gates"]:
            print(f"  {'✅' if g['pass'] else '❌'} {g['id']:14s} {g['what']}")
        print(f"  → {gg['n_pass']}/{gg['n_total']}")
        with open(os.path.join(OUT, "verify_rotor_dynamics.json"), "w") as f:
            json.dump(gg, f, ensure_ascii=False, indent=1, default=float)
        print("✅ outputs/verify_rotor_dynamics.json")

    if a.only in ("all", "effect"):
        print("\n═══ 효과 ═══", flush=True)
        arms_hc = ["locked", "legacy", "current", "sitl", "lit_iid", "indoor", "outdoor"]
        e1 = effect_half_corr(arms_hc)
        for k, v in e1["arms"].items():
            print(f"  half_corr {k:14s} {v['half_corr_mean']:.4f} "
                  f"± {v['half_corr_std']:.4f}  (n={v['n_seeds']})")
        drones = ["mini2", "mini5pro", "phantom4", "matrice4e", "typhoonh480", "s1000plus"]
        e2 = effect_features(["current", "sitl", "indoor", "outdoor"], drones,
                             n_draw=a.n_draw, nproc=a.nproc)
        for T, row in e2["windows"].items():
            for arm, r in row["arms"].items():
                print(f"  특징 T={T}s {arm:9s} 움직인 개수 |d|≥1: "
                      f"{r['n_moved_d_ge_1']}/{r['n_features_finite']} · "
                      f"|d|≥0.5: {r['n_moved_d_ge_0p5']} · 중앙 |d| {r['median_abs_d']:.2f}")
        out = {"_meta": {"script": "benchmark/verify_rotor_dynamics.py effect",
                         "generated": stamp,
                         "what_ko": "로터 랜덤성을 켜면 무엇이 달라지나 — 반창 상관과 분류 특징",
                         "gpu_ko": "안 씀. 위상표(각도의 함수)라 rpm 이 변해도 재계산이 없다"},
               "E1_half_window_spectrum_corr": e1,
               "E2_classification_features": e2}
        with open(os.path.join(OUT, "rotor_jitter_effect.json"), "w") as f:
            json.dump(out, f, ensure_ascii=False, indent=1, default=float)
        print("✅ outputs/rotor_jitter_effect.json")


if __name__ == "__main__":
    main()
