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
  ⭐2026-08-16 새 프리셋 `outdoor_v2` 와 함께 넷을 더 얹었다:
  G26 사다리 검산(닫힌 꼴) — (σ_w, τ) 짝이 실측 창-안 rms 밴드 안. **통제**: 현행 τ=0.227 s 는
      어떤 σ_w 로도 두 rung 을 동시에 못 맞춘다(«σ_w 만 손보면 된다» 를 반증)
  G27 사다리 몬테카를로 — 실제로 만든 OU 열의 창-안 rms 가 닫힌 꼴과 ±3 %
  G28 ⭐**두 길이 같은 수를 내나** — (σ_s,σ_w,τ) 세 손잡이 판 vs 유효 산포 하나(σ_eff) 판
  G29 ⭐**비트동일 회귀** — 새 프리셋을 **안 고른** 판이 2026-08-11 코드와 한 비트도 안 다르다

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
#  ⭐ G29 용 **동결표** — 2026-08-16 새 프리셋을 넣기 **전**의 코드가 낸 값이다.
#     만드는 법: 그날 손대기 전의 `src/rotor_dynamics.py` 사본을 따로 불러
#     같은 (rpm0, n_rotors, n_t, prf, seed) 로 `rpm_series` 를 돌리고 그 float64
#     바이트의 sha256 앞 16 자를 적었다(사본 md5 c7d63aaabff9808eded0ee781522aa28).
#     ⛔여기가 깨지면 «인자를 안 주면 예전과 같다» 는 약속이 깨진 것이다.
_FROZEN_CASES = [(3800.0, 4, 39400, 19700.0, 0), (3800.0, 4, 39400, 19700.0, 7),
                 (5500.0, 4, 5000, 20000.0, 4242), (9200.0, 6, 20000, 20000.0, 11),
                 (1500.0, 8, 800, 200.0, 3)]
_FROZEN_RPM_SHA16 = {
    "legacy": ["f04349f3a4923ebb", "f04349f3a4923ebb", "8a32c8383e2ad789",
               "b6bf2bcc570fc2e1", "46f8df05fbd48a55"],
    "legacy_outdoor": ["5fe070de65bfc1b9", "5fe070de65bfc1b9", "a541d7862c6dd15b",
                       "65982ff19fdeb9c0", "a3afe828be63d4fc"],
    "sitl": ["4ff4e7d6a07eed05", "9483d3ec5281359f", "3e780e02dc7873b7",
             "06947bca39146947", "d8d459ef6626567c"],
    "indoor": ["9ad919cb0c7dd1e8", "176a9828ebc3f623", "fe19e27d0d50b31e",
               "68c377da115b0a47", "9efeb8832f3f804a"],
    "outdoor": ["0c9f613a23a17330", "3cb61ebb032e73e0", "daf7831e590ba63d",
                "e1e6dbaf29f1edd1", "e4e26b2ba970e4e1"],
    "lit_iid": ["82292de1a1d794dc", "ec71aed7672143e2", "fab01d11f97d6889",
                "f3a899684706d4b6", "aa3ae81cb42faa0f"],
}
#: 같은 날 원장(`outputs/rotor_jitter_model.json`, 2026-08-11 생성)이 적어 둔 파라미터.
_FROZEN_PARAMS = {
    "legacy": (0.0022, 0.0, 0.22736420441699334, False),
    "legacy_outdoor": (0.02, 0.0, 0.22736420441699334, False),
    "sitl": (0.0022, 0.0, 0.22736420441699334, True),
    "indoor": (0.0054, 0.0065, 0.22736420441699334, True),
    "outdoor": (0.0235, 0.0245, 0.22736420441699334, True),
    "lit_iid": (0.0099, 0.0, 0.22736420441699334, True),
}


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

    G += gates_v2()

    return {"gates": G,
            "n_pass": sum(1 for g in G if g["pass"]), "n_total": len(G)}


# ═══════════════════════════════════════════════════════════════════════════
#  ⭐ A-2. 새 프리셋 `outdoor_v2` 게이트 (2026-08-16)
# ═══════════════════════════════════════════════════════════════════════════
def _in_window_rms_measured(e, prf, window_s):
    """만들어 낸 열의 **창-안 rms** — 창평균을 뺀 뒤의 rms(겹치지 않는 창)."""
    m = int(round(window_s * prf))
    k = e.shape[0] // m
    x = e[:k * m].reshape(k, m, -1)
    return float(np.sqrt(((x - x.mean(axis=1, keepdims=True)) ** 2).mean()))


def _window_mean_spread(jit, n_trial, window_s=0.25, prf=20000.0, n_rot=4, seed=2026):
    """0.25 s 창 하나가 **실제로 보는** 로터 간 산포 — 창평균 rpm 의 로터간 std(ddof0).

    ⭐이것이 빗살 폭을 정하는 양이다. 손잡이 셋 판이든 유효 산포 하나 판이든
      이 값이 같으면 «같은 수를 낸다» 는 뜻이다."""
    n_t = int(round(prf * window_s))
    rng = np.random.default_rng(seed)
    out = np.empty(n_trial)
    for i in range(n_trial):
        rpm, _ = rd.rpm_series(1.0, n_rot, n_t, prf, jit, rng)
        out[i] = rpm.mean(axis=0).std()
    return out


def _comb_spread_hz(E, prf, f_flash, m, half_frac=0.40):
    """m 차 조화 구역의 2차 모멘트 [Hz] — «빗살이 얼마나 굵어졌나»."""
    ac = np.asarray(E) - np.mean(E)
    n = len(ac)
    P = np.abs(np.fft.fft(ac * np.hanning(n))) ** 2
    f = np.fft.fftfreq(n, 1.0 / prf)
    sel = np.abs(np.abs(f) - m * f_flash) <= half_frac * f_flash
    p = np.maximum(P[sel] - np.median(P[sel]), 0.0)
    if p.sum() <= 0:
        return float("nan")
    fl = np.abs(f[sel])
    mu = (fl * p).sum() / p.sum()
    return float(np.sqrt(((fl - mu) ** 2 * p).sum() / p.sum()))


def _comb_spread_arm(jit, n_seed=24, window_s=0.25, prf=20000.0, m=3,
                     key="matrice4e", ai=6, rpm0=3800.0):
    """위상표로 합성한 빗살 폭 [Hz] 평균 (GPU 불필요)."""
    import md_classify_dataset as mcd
    E_ref, fine, dirs = _load_tab(key, ai)
    ff = 2.0 * rpm0 / 60.0
    n_t = int(round(prf * window_s))
    vals = []
    for s in range(n_seed):
        rng = np.random.default_rng(5000 + s)
        rpm, _ = rd.rpm_series(rpm0, len(dirs), n_t, prf, jit, rng)
        p0 = rd.initial_phase_deg(len(dirs), jit, rng, mcd.PHASE_PERIOD_DEG)
        vals.append(_comb_spread_hz(mcd.synth(E_ref, fine, dirs, rpm, p0, prf, n_t),
                                    prf, ff, m))
    return float(np.nanmean(vals)), float(np.nanstd(vals)), ff


def gates_v2() -> list:
    """`outdoor_v2` · `outdoor_v2_eff` 전용 게이트 넷. 나머지 게이트와 독립이다."""
    import hashlib
    from scipy.stats import ks_2samp

    G = []
    v2 = rd.PRESETS["outdoor_v2"]
    eff = rd.PRESETS["outdoor_v2_eff"]

    # ── G26 · 사다리 검산(닫힌 꼴) + 통제 ───────────────────────────────────
    lc = rd.ladder_check(v2)
    ctrl = rd.ladder_check(rd.PRESETS["outdoor"])
    G.append(_g("G26", "outdoor_v2 (σ_w, τ) 짝이 실측 창-안 rms 사다리 밴드 안", lc["pass"],
                {"rungs": lc["rungs"], "sigma_w_feasible_pct": lc["sigma_w_feasible_pct"],
                 "all_four_rungs_in_band": all(r["in_band"] for r in lc["rungs"].values())},
                "0.25 s·20 s 두 rung 모두 밴드 안",
                "⭐세 값은 짝이다 — τ 를 옮기면 σ_w 도 옮겨야 같은 관측이 나온다"))
    G.append(_g("G26b", "통제 — 현행 τ=0.227 s 로는 **어떤 σ_w 로도** 두 rung 동시 불가",
                ctrl["sigma_w_feasible_empty"],
                {"sigma_w_feasible_pct": ctrl["sigma_w_feasible_pct"],
                 "empty": ctrl["sigma_w_feasible_empty"],
                 "outdoor_rungs": ctrl["rungs"]},
                "허용 구간이 비어 있어야 한다(lo > hi)",
                "«σ 만 손보면 된다» 를 코드가 반증한다 — 고쳐야 하는 것은 τ 다"))

    # ── G27 · 사다리 몬테카를로 ─────────────────────────────────────────────
    fs = 200.0
    e = rd.ou_process(int(4000.0 * fs), 1.0 / fs, v2.wobble_sigma, v2.tau_ctl_s,
                      np.random.default_rng(5), n_ch=8)
    rows, ok27 = {}, True
    for T in sorted(rd.LADDER_ANCHORS):
        meas = _in_window_rms_measured(e, fs, T)
        pred = rd.in_window_rms(v2.wobble_sigma, v2.tau_ctl_s, T)
        rel = meas / pred - 1.0
        ok27 &= abs(rel) <= 0.03
        rows[f"{T:g}s"] = {"measured_pct": 100.0 * meas, "closed_form_pct": 100.0 * pred,
                           "rel_err": rel, "band_pct": [100.0 * b
                                                        for b in rd.LADDER_ANCHORS[T]]}
    G.append(_g("G27", "만들어 낸 OU 열의 창-안 rms == 닫힌 꼴", ok27,
                {"rows": rows, "n_ch": 8, "dur_s": 4000.0, "fs_hz": fs},
                "|rel| ≤ 0.03",
                "사다리 판정이 «식» 이 아니라 **실제로 만든 열**에서도 성립하는가"))

    # ── G28 · ⭐두 길이 같은 수를 내나 ──────────────────────────────────────
    se = rd.sigma_eff(v2, rd.SIGMA_EFF_WINDOW_S)
    d_an = abs(eff.static_sigma / se - 1.0)
    a = _window_mean_spread(v2, 1500)
    b = _window_mean_spread(eff, 1500, seed=2027)
    rms_a, rms_b = float(np.sqrt((a ** 2).mean())), float(np.sqrt((b ** 2).mean()))
    pred_rms = float(np.sqrt(0.75) * se)      # 로터 4개 · 창평균 몫 → 0.866·σ_eff
    ks = ks_2samp(a, b)
    sp_a, sd_a, ff = _comb_spread_arm(v2)
    sp_b, sd_b, _ = _comb_spread_arm(eff)
    ok28 = (d_an <= 1e-12 and abs(rms_a / rms_b - 1.0) <= 0.03
            and abs(rms_a / pred_rms - 1.0) <= 0.05 and ks.pvalue > 0.01
            and abs(sp_a / sp_b - 1.0) <= 0.10)
    G.append(_g("G28", "두 길(손잡이 셋 ↔ 유효 산포 하나)이 0.25 s 창에서 같은 수를 내나", ok28,
                {"analytic": {"sigma_eff_pct": 100.0 * se,
                              "preset_static_sigma_pct": 100.0 * eff.static_sigma,
                              "rel_err": d_an},
                 "window_mean_spread": {
                     "path_A_three_knobs_rms_pct": 100.0 * rms_a,
                     "path_B_single_sigma_rms_pct": 100.0 * rms_b,
                     "predicted_0p866_sigma_eff_pct": 100.0 * pred_rms,
                     "A_over_B": rms_a / rms_b, "n_trial": int(a.size),
                     "ks_p": float(ks.pvalue), "ks_stat": float(ks.statistic)},
                 "comb_spread_m3_hz": {
                     "path_A": sp_a, "path_B": sp_b, "A_over_B": sp_a / sp_b,
                     "std_A": sd_a, "std_B": sd_b, "f_flash_hz": ff,
                     "predicted_m_fflash_0p866_sigma_eff":
                         3.0 * ff * np.sqrt(0.75) * se},
                 "residual_in_window_wobble_pct": 100.0 * rd.in_window_rms(
                     v2.wobble_sigma, v2.tau_ctl_s, rd.SIGMA_EFF_WINDOW_S)},
                "해석 동일 · 창평균 산포 ±3 % · KS p>0.01 · 빗살 폭 ±10 %",
                "⭐두 번째 길이 성립하는 이유는 f(0.25 s)=0.955 — 흔들림의 95.5 % 가 "
                "그 창에서는 «상수 오프셋» 으로 보이기 때문이다. 창이 길어지면 갈라진다"))

    # ── G29 · ⭐비트동일 회귀 (새 프리셋을 안 고른 판) ──────────────────────
    bad_p = {k: {"now": (rd.PRESETS[k].static_sigma, rd.PRESETS[k].wobble_sigma,
                         rd.PRESETS[k].tau_ctl_s, rd.PRESETS[k].random_phase),
                 "frozen": v}
             for k, v in _FROZEN_PARAMS.items()
             if (rd.PRESETS[k].static_sigma, rd.PRESETS[k].wobble_sigma,
                 rd.PRESETS[k].tau_ctl_s, rd.PRESETS[k].random_phase) != v}
    bad_h = []
    for k, hs in _FROZEN_RPM_SHA16.items():
        for (rpm0, nr, n_t, prf, seed), h in zip(_FROZEN_CASES, hs):
            r, _ = rd.rpm_series(rpm0, nr, n_t, prf, k, np.random.default_rng(seed))
            got = hashlib.sha256(np.ascontiguousarray(r, np.float64).tobytes()).hexdigest()[:16]
            if got != h:
                bad_h.append({"preset": k, "case": [rpm0, nr, n_t, prf, seed],
                              "frozen": h, "now": got})
    f025 = rd.window_mean_variance_fraction(rd.TAU_CTL_S, 0.25)
    ok29 = (not bad_p and not bad_h and rd.DEFAULT_PRESET == "legacy"
            and rd.TAU_CTL_S == 0.22736420441699334
            and abs(f025 - 0.7155771196527009) < 1e-15)
    G.append(_g("G29", "새 프리셋을 **안 고른** 판이 2026-08-11 코드와 비트동일", ok29,
                {"n_presets_checked": len(_FROZEN_PARAMS),
                 "n_rpm_series_cases": len(_FROZEN_PARAMS) * len(_FROZEN_CASES),
                 "param_mismatch": bad_p, "digest_mismatch": bad_h,
                 "DEFAULT_PRESET": rd.DEFAULT_PRESET, "TAU_CTL_S": rd.TAU_CTL_S,
                 "window_mean_variance_fraction(TAU,0.25)": f025,
                 "new_presets_added": [k for k in rd.PRESETS
                                       if k not in _FROZEN_PARAMS]},
                "파라미터·rpm 열 digest·기본 프리셋 전부 동결값과 일치",
                "⭐«인자를 안 주면 예전과 같다» 가 이 저장소의 규약이다. 동결표는 "
                "새 프리셋을 넣기 전 코드 사본이 낸 값이다(G29 머리 주석 참조)"))
    return G


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

#  ⭐ 분해 팔 — «정적 산포» 와 «시간 흔들림» 중 무엇이 맵을 바꾸나를 가른다.
#    `outdoor` 는 둘 다 켜져 있어 단독으로는 원인을 못 가린다.
_PROBE = {
    "outdoor_static_only": rd.PRESETS["outdoor"].with_(
        name="outdoor_static_only", wobble_sigma=0.0),
    "outdoor_wobble_only": rd.PRESETS["outdoor"].with_(
        name="outdoor_wobble_only", static_sigma=0.0),
    "outdoor_aligned_phase": rd.PRESETS["outdoor"].with_(
        name="outdoor_aligned_phase", random_phase=False),
}


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
        jit = _PROBE.get(arm) or rd.get(arm)
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
                        jobs.append((key, ai, di, arm,
                                     7_000_000 + 977 * di + 13 * ai, prf, T, sc))
    t0 = time.time()
    with Pool(nproc) as pool:
        res = pool.map(_feat_job, jobs, chunksize=8)
    print(f"  특징 {len(jobs)} 건 {time.time()-t0:.0f}s", flush=True)

    names = list(mcd.FEATURE_NAMES)
    nf = len(names)
    #  (arm, T) → {"X": (n, nf), "drone": [...], "cell": [...]}
    acc = {}
    for key, ai, di, arm, T, v, hc in res:
        a = acc.setdefault((arm, T), {"X": [], "drone": [], "cell": [], "hc": []})
        a["X"].append(v)
        a["drone"].append(key)
        a["cell"].append(f"{key}/a{ai:02d}")
        a["hc"].append(hc)
    for a in acc.values():
        a["X"] = np.asarray(a["X"], float)
        a["drone"] = np.asarray(a["drone"])
        a["cell"] = np.asarray(a["cell"])
        a["hc"] = np.asarray(a["hc"], float)

    base_arm = arms[0]
    out = {"_setting": {
        "prf_hz": prf, "n_draw_per_aspect": n_draw, "drones": list(drones),
        "n_aspects": 18, "windows_s": list(windows), "arms": list(arms),
        "baseline_arm": base_arm, "n_features": nf,
        "effect_size_definition_ko": (
            "⭐d 는 **(기체,자세) 칸 안에서** 잰다: d = median_칸[(평균_팔 − 평균_기준) / "
            "표준편차_기준]. 전체를 한 덩이로 재면 분모가 기체·자세 차이에 지배되어 "
            "효과가 희석된다(그렇게 재면 outdoor 의 중앙 |d| 가 0.22, 칸 안에서 재면 훨씬 크다)."),
        "fratio_definition_ko": (
            "F = 기체간 분산 / 기체내 분산. **분류가 쓸 수 있는 정보의 양**이다. "
            "로터 랜덤성이 분류를 어렵게 만든다면 이 값이 내려가야 한다.")},
        "windows": {}}

    def _fratio(X, drone):
        """기체간 분산 / 기체내 분산 (특징별). 표준화한 뒤 잰다."""
        mu, sd = np.nanmean(X, axis=0), np.nanstd(X, axis=0)
        Z = (X - mu) / np.where(sd > 0, sd, np.nan)
        ks = np.unique(drone)
        gm = np.array([np.nanmean(Z[drone == k], axis=0) for k in ks])
        wv = np.nanmean([np.nanvar(Z[drone == k], axis=0) for k in ks], axis=0)
        return np.nanvar(gm, axis=0) / np.where(wv > 0, wv, np.nan)

    for T in windows:
        B = acc[(base_arm, T)]
        fb = _fratio(B["X"], B["drone"])
        wrow = {"baseline_n": int(B["X"].shape[0]),
                "baseline_half_corr_mean": float(np.nanmean(B["hc"])),
                "arms": {}}
        cells = np.unique(B["cell"])
        for arm in arms[1:]:
            A = acc[(arm, T)]
            #  ── 칸 안 효과크기 ────────────────────────────────────────────
            dcell = np.full((len(cells), nf), np.nan)
            for ci, c in enumerate(cells):
                b, a = B["X"][B["cell"] == c], A["X"][A["cell"] == c]
                sb = np.nanstd(b, axis=0)
                dcell[ci] = (np.nanmean(a, axis=0) - np.nanmean(b, axis=0)) / \
                    np.where(sb > 0, sb, np.nan)
            d = np.nanmedian(dcell, axis=0)
            #  ── 분류 정보량 ──────────────────────────────────────────────
            fa = _fratio(A["X"], A["drone"])
            per = {n: {"d_within_cell": float(d[i]),
                       "base_mean": float(np.nanmean(B["X"][:, i])),
                       "arm_mean": float(np.nanmean(A["X"][:, i])),
                       "rel_shift": float((np.nanmean(A["X"][:, i])
                                           - np.nanmean(B["X"][:, i]))
                                          / (abs(np.nanmean(B["X"][:, i])) + 1e-12)),
                       "f_base": float(fb[i]), "f_arm": float(fa[i]),
                       "f_ratio_arm_over_base": float(fa[i] / fb[i]) if fb[i] > 0 else None}
                   for i, n in enumerate(names)}
            fin = d[np.isfinite(d)]
            fr = np.array([per[n]["f_ratio_arm_over_base"] for n in names
                           if per[n]["f_ratio_arm_over_base"] is not None], float)
            wrow["arms"][arm] = {
                "n": int(A["X"].shape[0]),
                "half_corr_mean": float(np.nanmean(A["hc"])),
                "n_moved_d_ge_1": int((np.abs(fin) >= 1.0).sum()),
                "n_moved_d_ge_0p5": int((np.abs(fin) >= 0.5).sum()),
                "n_moved_d_ge_0p2": int((np.abs(fin) >= 0.2).sum()),
                "n_features_finite": int(fin.size),
                "median_abs_d": float(np.median(np.abs(fin))),
                "max_abs_d": float(np.max(np.abs(fin))),
                "fratio_median_arm_over_base": float(np.nanmedian(fr)),
                "n_features_fratio_down_20pct": int((fr < 0.8).sum()),
                "top10_abs_d": sorted(per.items(),
                                      key=lambda kv: -abs(kv[1]["d_within_cell"]))[:10],
                "top10_fratio_loss": sorted(
                    [kv for kv in per.items()
                     if kv[1]["f_ratio_arm_over_base"] is not None],
                    key=lambda kv: kv[1]["f_ratio_arm_over_base"])[:10],
                "per_feature": per}
        out["windows"][str(T)] = wrow

    np.savez_compressed(
        os.path.join(OUT, "rotor_jitter_effect_features.npz"),
        feature_names=np.array(names),
        **{f"{arm}|{T}|X": acc[(arm, T)]["X"] for arm in arms for T in windows},
        **{f"{arm}|{T}|drone": acc[(arm, T)]["drone"] for arm in arms for T in windows},
        **{f"{arm}|{T}|cell": acc[(arm, T)]["cell"] for arm in arms for T in windows},
        **{f"{arm}|{T}|half_corr": acc[(arm, T)]["hc"] for arm in arms for T in windows})
    return out


# ═══════════════════════════════════════════════════════════════════════════
#  C. 모델 원장 — 프리셋과 그 근거를 한 파일에
# ═══════════════════════════════════════════════════════════════════════════
def model_ledger() -> dict:
    """`outputs/rotor_jitter_model.json` — 프리셋 표 · σ_w 보정 산술 · 파급 예측."""
    T = rd.TAU_CTL_S
    anchors = [
        {"source": "NeuroBEM (UZH RPG) 실내 무풍", "band_hz": [0.3, 5.0],
         "amp_equiv_sine_pct": 0.74, "static_spread_pct": 0.54,
         "dominant_hz": "0.7-2.2", "vehicle": "레이싱 쿼드 0.772 kg (DJI 아님)"},
        {"source": "PX4 Flight Review CODEV AQUILA V3 야외", "band_hz": [0.3, 2.0],
         "amp_equiv_sine_pct": 2.52, "static_spread_pct": 2.35,
         "dominant_hz": "0.74 (사분 0.5-1.5)", "vehicle": "상용 대형 쿼드 (DJI 아님)"},
        {"source": "DJI Phantom 3 DAT 명령(PWM) 야외", "band_hz": [0.3, 5.0],
         "amp_equiv_sine_pct": 5.3, "static_spread_pct": 5.8,
         "dominant_hz": "0.3-0.9", "vehicle": "⭐진짜 DJI. ⚠명령 proxy — rpm 환산 2.3~4.6 %"},
    ]
    for a in anchors:
        f1, f2 = a["band_hz"]
        a["band_fraction_F"] = round(rd.ou_band_fraction(T, f1, f2), 4)
        a["sigma_w_pct"] = round(100.0 * rd.sigma_w_from_band_amp(
            a["amp_equiv_sine_pct"] / 100.0, f1, f2, T), 4)

    wmf = {str(w): round(rd.window_mean_variance_fraction(T, w), 4)
           for w in (0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 4.0)}

    f_flash, f_tip = 126.6667, 1228.72
    broaden = []
    for nm, sw in (("legacy sine 0.15 % (σ 0.106 %)", 0.0015 / np.sqrt(2.0)),
                   ("sitl 0 %", 0.0), ("indoor σ_w 0.65 %", 0.0065),
                   ("outdoor σ_w 2.45 %", 0.0245)):
        broaden.append({"case": nm, "sigma_w": sw,
                        "dev_ftip_hz": round(f_tip * sw, 3),
                        "dev_m10_hz": round(10 * f_flash * sw, 3),
                        "carson_m10_hz": round(2 * (10 * f_flash * sw + 0.7), 3)})
    return {
        "_meta": {"script": "benchmark/verify_rotor_dynamics.py --only ledger",
                  "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
                  "module": "src/rotor_dynamics.py",
                  "design": "docs/NOISE_AND_ROTOR_PLAN.md §2",
                  "survey": "prior_work/rotor_randomness_survey.md",
                  "model": "rpm_k(t) = rpm0*(1 + s_k + eps_k(t)); "
                           "s_k ~ N(0,sigma_s) mean-removed; "
                           "eps_k(t) = OU(sigma_w, T) independent per rotor; "
                           "theta_k(0) ~ U(0, 360/blades)",
                  "ou_discretisation": "a=exp(-dt/T); e[n+1]=a*e[n]+sigma*sqrt(1-a^2)*N(0,1); "
                                       "e[0]~N(0,sigma)  (exact, stationary start)"},
        "control_loop": {
            "tau_ctl_s": T, "f_ctl_hz": rd.F_CTL_HZ,
            "px4_MC_ROLL_P": 4.0, "px4_hz": 0.6366,
            "ardupilot_ATC_ANG_P": 4.5, "ardupilot_hz": 0.7162,
            "why_lowpass_ko": "백색이면 PRF(19.7 kHz)까지 평평한 흔들림이 되고, 그 rpm 을 "
                              "적분하면 위상이 랜덤워크가 되어 선폭이 무한히 넓어진다. "
                              "자이로 저역통과 20~40 Hz + 로터 관성 τ 5~72 ms 가 상한을 정한다.",
            "tau_motor_optional_s": list(rd.TAU_MOTOR_RANGE_S),
            "tau_motor_note_ko": "2극. 8~20 dB 짜리 세부. 기본 끔 — 우리 표적 기체 값을 못 찾았다."},
        "sigma_w_calibration": {
            "formula": "sigma_w = (amp_equiv_sine/sqrt(2)) / sqrt(F); "
                       "F = (2/pi)*(atan(2*pi*f2*T) - atan(2*pi*f1*T))",
            "why_ko": "원장 rotor_rpm_web_anchor.json 의 wobble amp 는 «등가 사인 진폭»"
                      "(대역 rms × √2)이다. OU 의 파라미터는 진폭이 아니라 σ 이므로 두 번 고친다.",
            "anchors": anchors},
        "presets": rd.preset_table(),
        #  ⭐2026-08-16 — 새 프리셋 `outdoor_v2` 의 근거. 기존 항목은 위 표 그대로다.
        "ladder_2026_08_16": {
            "why_ko": "마이크로도플러가 실제로 보는 양은 σ_w 도 τ 도 아니라 «창 T 안에서 "
                      "회전수가 얼마나 흔들려 보이는가»(창-안 rms) 하나다. 그래서 τ 를 "
                      "옮기면 σ_w 도 같이 옮겨야 같은 관측이 나온다 — **세 값은 짝이다.**",
            "formula": "rms(T) = sigma_w * sqrt(1 - f(T,tau));  "
                       "sigma_eff(T) = sqrt(sigma_s^2 + sigma_w^2 * f(T,tau))",
            "anchors_pct": {f"{k:g}s": [100.0 * v[0], 100.0 * v[1]]
                            for k, v in rd.LADDER_ANCHORS.items()},
            "anchors_source": rd.LADDER_SOURCE,
            "pass_rungs_s": list(rd.LADDER_HARD_RUNGS),
            "checks": {n: rd.ladder_check(n) for n in ("outdoor", "outdoor_v2")},
            "sigma_eff_pct_at_0p25s": {
                n: 100.0 * rd.sigma_eff(n, rd.SIGMA_EFF_WINDOW_S)
                for n in ("legacy", "indoor", "outdoor", "outdoor_v2", "outdoor_v2_eff")},
            "gate": "benchmark/verify_rotor_dynamics.py G26·G26b·G27·G28·G29",
            "ripple": "benchmark/rotor_outdoor_v2_ripple.py → "
                      "outputs/rotor_outdoor_v2_ripple.json",
            "default_unchanged_ko": "기본 프리셋은 여전히 legacy 다. 인자를 안 주면 "
                                    "예전과 비트동일이고 G29 가 그것을 지킨다."},
        "window_mean_variance_fraction": {
            "formula": "(2T/Tw)*(1 - (T/Tw)*(1-exp(-Tw/T)))", "table": wmf,
            "consequence_ko": "0.25 s 창(분류 헤드라인)에서는 흔들림 분산의 71.6 % 가 "
                              "«정적 오프셋»으로 보인다. 그래서 분류 쪽에서 먼저 고칠 것은 "
                              "흔들림이 아니라 정적 산포 값 자체다."},
        "line_broadening_prediction": {
            "drone": "matrice4e", "f_flash_hz": f_flash, "f_tip_hz": f_tip,
            "entries": broaden,
            "resolvability_hz": {"cpi_2s_bin": 0.5, "classify_fft_bin_T0p25": 4.0,
                                 "classify_comb_halfwidth": 0.20 * f_flash,
                                 "flash_spec_df_nseg70": 19700.0 / 70.0}},
        "unresolved_ko": [
            "우리 표적 기체(Mavic 4 Pro · Matrice 4E)의 rpm 통계와 로터 τ 를 못 찾았다 — "
            "DJI 가 최신 DAT 를 암호화한다. 자체 실측이 유일한 경로다.",
            "σ_w(시간 흔들림)를 넣은 마이크로도플러 문헌 선례가 0 건이다. 근거는 실기 로그뿐이고 "
            "셋 다 우리 표적 기체가 아니다. 리포트에서 «문헌이 한다» 라고 쓰면 안 된다.",
            "OU 를 «참» 이라고 가정하고 대역 몫 F 를 계산했다. 실제 스펙트럼이 OU 가 아니면 "
            "F 가 달라지고 σ_w 가 통째로 움직인다.",
            "산란 진폭의 요동은 여전히 미모델이다(White IEEE TRS 2024 도 같은 자백을 한다).",
            "블레이드 플렉싱·피치 변화는 안 넣는다 — 원문 확인 범위에서 사례 0 건."],
    }


# ═══════════════════════════════════════════════════════════════════════════
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="all",
                    choices=["all", "gates", "effect", "ledger"])
    ap.add_argument("--nproc", type=int, default=10)
    ap.add_argument("--n-draw", type=int, default=6)
    a = ap.parse_args()

    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    if a.only in ("all", "ledger"):
        with open(os.path.join(OUT, "rotor_jitter_model.json"), "w") as f:
            json.dump(model_ledger(), f, ensure_ascii=False, indent=1, default=float)
        print("✅ outputs/rotor_jitter_model.json")

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
        arms_hc = ["locked", "legacy", "current", "sitl", "lit_iid", "indoor", "outdoor",
                   "outdoor_static_only", "outdoor_wobble_only", "outdoor_aligned_phase"]
        e1 = effect_half_corr(arms_hc)
        for k, v in e1["arms"].items():
            print(f"  half_corr {k:14s} {v['half_corr_mean']:.4f} "
                  f"± {v['half_corr_std']:.4f}  (n={v['n_seeds']})")
        drones = ["mini2", "mini5pro", "phantom4", "matrice4e", "typhoonh480", "s1000plus"]
        e2 = effect_features(["current", "sitl", "indoor", "outdoor"], drones,
                             n_draw=a.n_draw, nproc=a.nproc)
        for T, row in e2["windows"].items():
            for arm, r in row["arms"].items():
                print(f"  특징 T={T}s {arm:9s} |d|≥1: "
                      f"{r['n_moved_d_ge_1']}/{r['n_features_finite']} · "
                      f"≥0.5: {r['n_moved_d_ge_0p5']} · ≥0.2: {r['n_moved_d_ge_0p2']} · "
                      f"중앙|d| {r['median_abs_d']:.2f} · "
                      f"F비 중앙 {r['fratio_median_arm_over_base']:.3f} "
                      f"(20%↓ {r['n_features_fratio_down_20pct']}개)")
        #  ⭐ 설계서 §2-5 의 «반증 가능한 예측» 넷 + §0-3 의 창길이 예측을 판정한다.
        #     예측이 안 맞으면 배선이 안 된 것이다(G24) 또는 규약과 충돌한 것이다.
        w025 = e2["windows"]["0.25"]["arms"]["outdoor"]
        w100 = e2["windows"]["1.0"]["arms"]["outdoor"]
        pf025 = w025["per_feature"]
        pf100 = w100["per_feature"]
        hc_base = e1["arms"]["current"]["half_corr_mean"]
        hc_out = e1["arms"]["outdoor"]["half_corr_mean"]
        preds = {
            "P1_ridges_broaden": {
                "prediction_ko": "2 s 호버 맵의 고차 능선이 눈에 띄게 굵어진다",
                "evidence": "게이트 G23 — m 차 조화의 rms 폭이 m·f_flash·σ_w 에 비례",
                "pass": None,
                "note_ko": "여기서는 안 잰다. G23(verify_rotor_dynamics gates) 과 "
                           "report07_hover_long.py --preset outdoor 가 잰다"},
            "P2_classification_degrades": {
                "prediction_ko": "분류가 어려워진다",
                "metric": "기체간/기체내 분산비 F 의 중앙 변화",
                "T0p25": w025["fratio_median_arm_over_base"],
                "T1p0": w100["fratio_median_arm_over_base"],
                "f_flash_hat_fratio_ratio_T1p0": pf100["f_flash_hat"]["f_ratio_arm_over_base"],
                "pass": bool(w025["fratio_median_arm_over_base"] < 1.0
                             and w100["fratio_median_arm_over_base"] < 1.0)},
            "P3_half_corr_drops": {
                "prediction_ko": "반창 스펙트럼 상관이 내려간다",
                "e1_current": hc_base, "e1_outdoor": hc_out,
                "e2_T0p25_d": pf025["half_corr"]["d_within_cell"],
                "e2_T1p0_d": pf100["half_corr"]["d_within_cell"],
                "pass": bool(hc_out < hc_base and pf025["half_corr"]["d_within_cell"] < 0)},
            "P4_flash_map_unchanged": {
                "prediction_ko": "flash_spec 플래시 맵은 거의 안 변한다(Δf 281 Hz ≫ 63 Hz)",
                "metric": "flash_contrast_db 의 칸 안 효과크기 |d| < 0.5",
                "T0p25_d": pf025["flash_contrast_db"]["d_within_cell"],
                "T1p0_d": pf100["flash_contrast_db"]["d_within_cell"],
                "T0p25_rel_shift": pf025["flash_contrast_db"]["rel_shift"],
                "pass": bool(abs(pf025["flash_contrast_db"]["d_within_cell"]) < 0.5
                             and abs(pf100["flash_contrast_db"]["d_within_cell"]) < 0.5),
                "note_ko": "⚠ 이것이 깨지면 조각 길이 규약과 충돌한 것이므로 멈추고 조사한다"},
            "P5_longer_window_hurts_more": {
                "prediction_ko": "0.25 s 창에서는 흔들림의 71.6 % 가 정적 오프셋으로 보이므로 "
                                 "효과는 1.0 s 팔에서 더 크게 나와야 한다 (설계서 §0-3)",
                "median_abs_d_T0p25": w025["median_abs_d"],
                "median_abs_d_T1p0": w100["median_abs_d"],
                "fratio_T0p25": w025["fratio_median_arm_over_base"],
                "fratio_T1p0": w100["fratio_median_arm_over_base"],
                "pass": bool(w100["median_abs_d"] > w025["median_abs_d"]
                             and w100["fratio_median_arm_over_base"]
                             < w025["fratio_median_arm_over_base"])},
        }
        out = {"_meta": {"script": "benchmark/verify_rotor_dynamics.py effect",
                         "generated": stamp,
                         "what_ko": "로터 랜덤성을 켜면 무엇이 달라지나 — 반창 상관과 분류 특징",
                         "gpu_ko": "안 씀. 위상표(각도의 함수)라 rpm 이 변해도 재계산이 없다",
                         "validated_against_ko": (
                             "legacy 팔의 반창상관 0.8074 는 같은 조건의 **실제 SBR** 원장"
                             "(outputs/report07_hover_long.npz, 0.8085)과 0.13 % 안에서 맞는다 "
                             "— 위상표 합성이 이 지표에 대해 SBR 을 대신할 수 있다는 근거다.")},
               "falsification_gates_G24_G25": preds,
               "E1_half_window_spectrum_corr": e1,
               "E2_classification_features": e2}
        for k, v in preds.items():
            print(f"  {'✅' if v['pass'] else ('—' if v['pass'] is None else '❌')} {k}")
        with open(os.path.join(OUT, "rotor_jitter_effect.json"), "w") as f:
            json.dump(out, f, ensure_ascii=False, indent=1, default=float)
        print("✅ outputs/rotor_jitter_effect.json")


if __name__ == "__main__":
    main()
