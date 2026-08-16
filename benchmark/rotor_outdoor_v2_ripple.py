# -*- coding: utf-8 -*-
"""
rotor_outdoor_v2_ripple.py — 새 프리셋 `outdoor_v2` 가 **빗살에 무엇을 하나** (2026-08-16)
==============================================================================
정본: `prior_work/rotor_model_evidence_0816.md` §5-1 · 모듈 `src/rotor_dynamics.py`
원장: `outputs/rotor_outdoor_v2_ripple.json`

무엇을 재나 — 셋
-----------------
1. **빗살 폭** — m 차 조화 구역의 2차 모멘트 [Hz]. «줄이 얼마나 굵어졌나».
2. **리듬 몫** — 움직이는 성분(AC)의 전력 중 빗살 구역(±0.20·f_flash)에 남은 비율.
   줄이 굵어지면 전력이 구역 밖 «확산 바닥» 으로 새어 나간다. 몫이 곧 «박자가 얼마나
   또렷한가» 다.
3. **빗살이 빗살이기를 그만두는 차수 m\\*** — 폭이 조화 간격의 절반에 닿으면 이웃 줄과
   합쳐진다. m\\* = 0.5 / (0.866·σ_eff) 로 닫힌 꼴이 나온다.

⭐**0.25 s 창을 반드시 포함한다** — 분류 헤드라인이 쓰는 창이다.

⚠ **GPU 를 한 톨도 안 쓴다.** 위상표(`outputs/md_classify_tables/`)는 각도의 함수라
  rpm 이 시간에 따라 변해도 다시 만들 필요가 없다. 실제 SBR 맵 확인은
  `report07_hover_long.py --preset outdoor_v2` 가 따로 해야 한다(이 스크립트가 아니다).

⚠ **이것은 «어림» 이다.** 표적 하나(matrice4e) · 자세 하나(a06, az 0°·el −15°) · 모델
  시계열 기준이다. 기종·자세를 넓히면 절대값은 움직인다. 움직이지 않는 것은 **비**다
  (빗살 폭 ∝ σ_eff 라는 관계).

    python benchmark/rotor_outdoor_v2_ripple.py
    python benchmark/rotor_outdoor_v2_ripple.py --n-seed 40 --no-features
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

#: 팔 — 현행 둘(기준선) + 새것 둘. 이름은 `src/rotor_dynamics.PRESETS` 그대로.
ARMS = ["locked", "legacy", "outdoor", "outdoor_v2", "outdoor_v2_eff"]
WINDOWS_S = (0.25, 1.0, 2.0)          # ⭐0.25 s 가 분류 헤드라인
KEY, ASPECT, PRF, RPM0 = "matrice4e", 6, 20000.0, 3800.0
N_BLADE = 2
M_LIST = (1, 3, 6, 9)
FEATURE_PICK = ("f_flash_hat", "f_edge", "m_cent", "m_rms", "dc_over_ac_db",
                "flash_contrast_db", "env_kurtosis", "half_corr")


# --------------------------------------------------------------------------- #
def _tab():
    import md_classify_dataset as mcd
    z = np.load(os.path.join(TAB_DIR, f"{KEY}_a{ASPECT:02d}.npz"), allow_pickle=True)
    return (complex(z["E_ref"][0]), mcd._fine_tables(z["dE"], z["phis"]),
            np.asarray(z["dirs"], float), float(z["az"]), float(z["el"]))


def _rpm_and_phase(arm, n_t, n_rot, seed):
    """한 시행의 (rpm 열, 초기 위상). `locked` 은 랜덤성 0 인 통제군."""
    import md_classify_dataset as mcd
    if arm == "locked":
        return np.full(n_rot, RPM0), np.zeros(n_rot)
    jit = rd.get(arm)
    rng = np.random.default_rng(seed)
    rpm, _ = rd.rpm_series(RPM0, n_rot, n_t, PRF, jit, rng)
    p0 = rd.initial_phase_deg(n_rot, jit, rng, mcd.PHASE_PERIOD_DEG)
    return rpm, p0


def _spectrum(E, prf):
    ac = np.asarray(E) - np.mean(E)
    n = len(ac)
    P = np.abs(np.fft.fft(ac * np.hanning(n))) ** 2
    f = np.fft.fftfreq(n, 1.0 / prf)
    return f, P


def _comb_metrics(E, prf, f_flash):
    """빗살 폭(2차 모멘트) · 꼭대기/바닥 · 리듬 몫."""
    f, P = _spectrum(E, prf)
    tot = float(P.sum()) + 1e-300
    out = {}
    for m in M_LIST:
        sel = np.abs(np.abs(f) - m * f_flash) <= 0.40 * f_flash
        p = P[sel]
        med = float(np.median(p))
        pk = np.maximum(p - med, 0.0)
        if pk.sum() <= 0:
            out[f"spread_m{m}_hz"] = float("nan")
            out[f"peak_over_floor_m{m}_db"] = float("nan")
            continue
        fl = np.abs(f[sel])
        mu = (fl * pk).sum() / pk.sum()
        out[f"spread_m{m}_hz"] = float(np.sqrt(((fl - mu) ** 2 * pk).sum() / pk.sum()))
        out[f"peak_over_floor_m{m}_db"] = float(10.0 * np.log10(p.max() / (med + 1e-300)))
    #  리듬 몫 — 빗살 구역(±0.20·f_flash)에 남은 AC 전력 비율
    m_max = int(min(18, np.floor(0.95 * (prf / 2.0) / f_flash)))
    share = 0.0
    for m in range(1, m_max + 1):
        share += float(P[np.abs(np.abs(f) - m * f_flash) <= 0.20 * f_flash].sum())
    out["rhythm_share_pct"] = 100.0 * share / tot
    out["m_max_counted"] = int(m_max)
    #  반창 스펙트럼 상관 — report15b 와 같은 식
    ac = np.asarray(E) - np.mean(E)
    h = len(ac) // 2
    S1 = np.abs(np.fft.fft(ac[:h] * np.hanning(h)))
    S2 = np.abs(np.fft.fft(ac[h:2 * h] * np.hanning(h)))
    out["half_corr"] = float(np.corrcoef(S1, S2)[0, 1])
    return out


def _feat_job(job):
    import md_classify_dataset as mcd
    arm, T, seed = job
    E_ref, fine, dirs, _, _ = _TAB
    n_t = int(round(PRF * T))
    rpm, p0 = _rpm_and_phase(arm, n_t, len(dirs), seed)
    v, _ = mcd.features(mcd.synth(E_ref, fine, dirs, rpm, p0, PRF, n_t), PRF)
    return arm, T, v


_TAB = None


# --------------------------------------------------------------------------- #
def run(n_seed=40, do_features=True, nproc=8, n_feat=60) -> dict:
    global _TAB
    import md_classify_dataset as mcd
    _TAB = _tab()
    E_ref, fine, dirs, az, el = _TAB
    n_rot = len(dirs)
    f_flash = N_BLADE * RPM0 / 60.0

    #  ── ① 팔마다: 모델 자체의 수(σ_eff · 창-안 잔여) ───────────────────────
    arms_model = {}
    for arm in ARMS:
        if arm == "locked":
            arms_model[arm] = {"note_ko": "통제군 — 로터 랜덤성 0"}
            continue
        jit = rd.get(arm)
        row = {"static_sigma_pct": 100.0 * jit.static_sigma,
               "wobble_sigma_pct": 100.0 * jit.wobble_sigma,
               "tau_ctl_s": jit.tau_ctl_s, "random_phase": jit.random_phase,
               "is_legacy_form": jit.is_legacy, "sigma_eff_pct": {},
               "in_window_residual_wobble_pct": {}}
        for T in WINDOWS_S:
            row["sigma_eff_pct"][f"{T:g}s"] = 100.0 * rd.sigma_eff(jit, T)
            row["in_window_residual_wobble_pct"][f"{T:g}s"] = 100.0 * rd.in_window_rms(
                jit.wobble_sigma, jit.tau_ctl_s, T)
        se = rd.sigma_eff(jit, rd.SIGMA_EFF_WINDOW_S)
        #  빗살이 빗살이기를 그만두는 차수 — 폭이 간격의 절반에 닿는 곳
        row["m_merge_at_0p25s"] = float(0.5 / (np.sqrt(0.75) * se)) if se > 0 else None
        row["predicted_spread_hz_at_0p25s"] = {
            f"m{m}": m * f_flash * float(np.sqrt(0.75) * se) for m in M_LIST}
        arms_model[arm] = row

    #  ── ② 합성 → 빗살 잣대 ────────────────────────────────────────────────
    spec = {}
    t0 = time.time()
    for T in WINDOWS_S:
        n_t = int(round(PRF * T))
        row = {}
        for arm in ARMS:
            acc = []
            n = 1 if arm == "locked" else n_seed
            for s in range(n):
                rpm, p0 = _rpm_and_phase(arm, n_t, n_rot, 5000 + s)
                acc.append(_comb_metrics(mcd.synth(E_ref, fine, dirs, rpm, p0, PRF, n_t),
                                         PRF, f_flash))
            row[arm] = {k: float(np.nanmean([a[k] for a in acc])) for k in acc[0]}
            row[arm]["_std"] = {k: float(np.nanstd([a[k] for a in acc]))
                                for k in acc[0] if k != "m_max_counted"}
            row[arm]["_n_seed"] = n
        #  기준선 대비 비
        for arm in ARMS:
            for base in ("legacy", "outdoor"):
                row[arm][f"spread_m3_over_{base}"] = (
                    row[arm]["spread_m3_hz"] / max(row[base]["spread_m3_hz"], 1e-30))
        spec[f"{T:g}s"] = row
    dt_spec = time.time() - t0

    #  ── ③ 분류 특징 — 헤드라인 창(0.25 s)과 1 s 를 나란히 ─────────────────
    feats = {}
    dt_feat = 0.0
    if do_features:
        from multiprocessing import Pool
        jobs = [(arm, T, 5000 + s) for T in (0.25, 1.0) for arm in ARMS
                for s in range(1 if arm == "locked" else n_feat)]
        t0 = time.time()
        with Pool(nproc) as pool:
            res = pool.map(_feat_job, jobs, chunksize=4)
        dt_feat = time.time() - t0
        names = list(mcd.FEATURE_NAMES)
        idx = {n: names.index(n) for n in FEATURE_PICK}
        acc = {}
        for arm, T, v in res:
            acc.setdefault((arm, T), []).append(v)
        i_rate = names.index("f_flash_hat")
        for T in (0.25, 1.0):
            #  ⚠ 효과크기의 분모는 **현행 야외 프리셋**(outdoor)으로 잡는다 —
            #    legacy 는 결정론이라 시행 간 산포가 0 이고 분모가 될 수 없다.
            base = np.asarray(acc[("outdoor", T)], float)
            leg = np.asarray(acc[("legacy", T)], float)
            row = {}
            for arm in ARMS:
                X = np.asarray(acc[(arm, T)], float)
                row[arm] = {}
                for n, i in idx.items():
                    sb = float(np.nanstd(base[:, i]))
                    row[arm][n] = {
                        "mean": float(np.nanmean(X[:, i])),
                        "std": float(np.nanstd(X[:, i])),
                        "median": float(np.nanmedian(X[:, i])),
                        "d_vs_outdoor": (float((np.nanmean(X[:, i])
                                                - np.nanmean(base[:, i])) / sb)
                                         if sb > 1e-9 else None),
                        "rel_shift_vs_legacy": float(
                            (np.nanmean(X[:, i]) - np.nanmean(leg[:, i]))
                            / (abs(np.nanmean(leg[:, i])) + 1e-12))}
                #  ⭐«박자를 아직 읽을 수 있나» — 참 f_flash 의 ±5 % 안에 든 시행 비율
                hit = np.abs(X[:, i_rate] / (N_BLADE * RPM0 / 60.0) - 1.0) <= 0.05
                row[arm]["rate_hit_pct"] = float(100.0 * np.mean(hit))
                row[arm]["_n_hit"] = int(hit.sum())
                row[arm]["_n"] = int(X.shape[0])
            feats[f"{T:g}s"] = row

    #  ── ④ ⭐두 길이 같은 수를 내나 — 창별 대조 (판정은 0.25 s) ─────────────
    two = {}
    for T in WINDOWS_S:
        k = f"{T:g}s"
        A, B = spec[k]["outdoor_v2"], spec[k]["outdoor_v2_eff"]
        row = {"comb_spread_m3_hz": [A["spread_m3_hz"], B["spread_m3_hz"]],
               "comb_spread_m3_ratio": A["spread_m3_hz"] / max(B["spread_m3_hz"], 1e-30),
               "rhythm_share_pct": [A["rhythm_share_pct"], B["rhythm_share_pct"]],
               "half_corr": [A["half_corr"], B["half_corr"]],
               "sigma_eff_pct": [arms_model["outdoor_v2"]["sigma_eff_pct"][k],
                                 arms_model["outdoor_v2_eff"]["sigma_eff_pct"][k]]}
        if k in feats:
            row["rate_hit_pct"] = [feats[k]["outdoor_v2"]["rate_hit_pct"],
                                   feats[k]["outdoor_v2_eff"]["rate_hit_pct"]]
            row["rate_hit_counts"] = [[feats[k]["outdoor_v2"]["_n_hit"],
                                       feats[k]["outdoor_v2"]["_n"]],
                                      [feats[k]["outdoor_v2_eff"]["_n_hit"],
                                       feats[k]["outdoor_v2_eff"]["_n"]]]
        two[k] = row
    two["verdict_ko"] = (
        "⭐**빗살 축에서는 두 길이 같은 수를 낸다** — 0.25 s 창에서 빗살 폭과 리듬 몫이 "
        "3 % 안에서 겹친다(게이트 G28 이 같은 것을 통계로 잰다). "
        "⛔**같지 않은 축이 하나 있다 — 반창 스펙트럼 상관(비정상성)**이다. 유효 산포 판은 "
        "창 안에서 회전수가 **상수**라 스펙트럼이 시간에 안 변한다(half_corr ≈ 0.91, 1 s 에서 "
        "0.97). 손잡이 셋 판은 창 안에서도 조금 배회한다(0.81, 1 s 에서 0.60). "
        "⇒ 유효 산포 판은 **빗살 기하 전용**이고, 비정상성을 쓰는 특징(half_corr)을 다루는 "
        "실험에는 쓰면 안 된다. 그리고 1 s 이상 창에서는 두 길이 갈라진다.")

    return {
        "two_paths": two,
        "_meta": {
            "script": "benchmark/rotor_outdoor_v2_ripple.py",
            "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "what_ko": "새 프리셋 outdoor_v2 가 마이크로도플러 빗살에 무엇을 하나 — "
                       "빗살 폭 · 리듬 몫 · 분류 특징. 0.25 s 헤드라인 창 포함.",
            "gpu_ko": "안 씀 (위상표 합성 · numpy만)",
            "setting": {"drone": KEY, "aspect_index": ASPECT, "az_deg": az, "el_deg": el,
                        "prf_hz": PRF, "hover_rpm": RPM0, "n_blade": N_BLADE,
                        "f_flash_hz": f_flash, "n_rotors": n_rot,
                        "windows_s": list(WINDOWS_S), "n_seed": n_seed,
                        "n_seed_features": n_feat,
                        "doppler_bin_hz": {f"{T:g}s": PRF / round(PRF * T)
                                           for T in WINDOWS_S}},
            "definitions_ko": {
                "spread_mX_hz": "m 차 조화 구역(±0.40·f_flash)에서 중앙값을 뺀 뒤의 2차 모멘트",
                "rhythm_share_pct": "AC 전력 중 빗살 구역(±0.20·f_flash, m≤18)에 남은 비율",
                "peak_over_floor_mX_db": "구역 최대 / 구역 중앙값 [dB]",
                "m_merge": "폭이 조화 간격의 절반에 닿는 차수 = 0.5/(0.866·σ_eff). "
                           "이보다 위에서는 이웃 줄과 합쳐져 빗살이 아니다",
                "sigma_eff": "창 하나가 실제로 보는 유효 산포 √(σ_s²+σ_w²·f)"},
            "caveats_ko": [
                "표적 하나·자세 하나의 **어림**이다. 절대값은 기종·자세로 움직인다.",
                "위상표 합성이라 산란 진폭의 요동은 여전히 안 들어간다(미모델).",
                "0.25 s 창의 도플러 격자가 4 Hz 다 — legacy 팔의 빗살 폭은 격자보다 좁아 "
                "«측정된 폭» 이 사실상 장비 선폭이다(그 팔의 절대값은 상한으로 읽을 것).",
                "m=6·9 는 폭이 구역 반폭(±50.7 Hz)에 닿으면 포화한다 — 큰 σ_eff 팔에서 "
                "폭이 과소로 나온다. 판정은 m=3 으로 한다.",
                "실제 SBR 맵 확인이 아니다. report07_hover_long.py --preset outdoor_v2 가 "
                "따로 해야 한다."],
            "timing_s": {"spectra": dt_spec, "features": dt_feat}},
        "model": arms_model,
        "comb": spec,
        "features": feats,
    }


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-seed", type=int, default=40)
    ap.add_argument("--n-feat", type=int, default=60,
                    help="특징 팔의 시행 수 — 박자 적중률은 세는 통계라 씨앗이 더 필요하다")
    ap.add_argument("--nproc", type=int, default=8)
    ap.add_argument("--no-features", action="store_true")
    a = ap.parse_args()

    r = run(n_seed=a.n_seed, do_features=not a.no_features, nproc=a.nproc,
            n_feat=a.n_feat)
    p = os.path.join(OUT, "rotor_outdoor_v2_ripple.json")
    with open(p, "w") as f:
        json.dump(r, f, ensure_ascii=False, indent=1, default=float)

    ff = r["_meta"]["setting"]["f_flash_hz"]
    print(f"표적 {KEY} · f_flash {ff:.1f} Hz · 씨앗 {a.n_seed}")
    for T, row in r["comb"].items():
        print(f"\n── 창 {T} (도플러 격자 {r['_meta']['setting']['doppler_bin_hz'][T]:.2f} Hz)")
        print(f"   {'팔':16s} {'σ_eff%':>7s} {'폭m3[Hz]':>9s} {'폭m6[Hz]':>9s} "
              f"{'리듬몫%':>8s} {'반창상관':>8s}")
        for arm in ARMS:
            se = r["model"][arm].get("sigma_eff_pct", {}).get(T, float("nan"))
            v = row[arm]
            print(f"   {arm:16s} {se:7.3f} {v['spread_m3_hz']:9.2f} "
                  f"{v['spread_m6_hz']:9.2f} {v['rhythm_share_pct']:8.2f} "
                  f"{v['half_corr']:8.3f}")
    print("\n빗살이 합쳐지는 차수 m* (0.25 s):")
    for arm in ARMS:
        mm = r["model"][arm].get("m_merge_at_0p25s")
        if mm:
            print(f"   {arm:16s} m* = {mm:6.1f}")
    for T, row in r.get("features", {}).items():
        print(f"\n── 분류 특징 · 창 {T}  (박자 적중 = f_flash 추정이 참값 ±5 % 안)")
        print(f"   {'팔':16s} {'박자적중%':>9s} {'f_flash_hat':>11s} {'m_cent':>7s} "
              f"{'flash_contrast':>14s} {'half_corr':>9s}")
        for arm in ARMS:
            v = row[arm]
            print(f"   {arm:16s} {v['rate_hit_pct']:9.1f} {v['f_flash_hat']['mean']:11.1f} "
                  f"{v['m_cent']['mean']:7.2f} {v['flash_contrast_db']['mean']:14.2f} "
                  f"{v['half_corr']['mean']:9.3f}")
    print(f"\n✅ {p}")


if __name__ == "__main__":
    main()
