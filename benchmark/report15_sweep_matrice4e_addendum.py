# -*- coding: utf-8 -*-
"""
report15_sweep_matrice4e_addendum.py — 본 실험 JSON 에 두 가지를 덧붙인다.

  (A) §1b 판정 재계산 — **RT 를 다시 돌리지 않는다.** 기록된 rows 에서 순수 유도한다.
      최초 판정은 '경로수가 정확히 같아야 기능적 동일' 이라는 너무 엄한 규칙을 썼다.
      수천 개 중 1 개 차이(상대 2e−4)에 −108 dB 복소차인데 '다르다' 고 적는 것은 틀린 보고다.
      → 상대량 기준으로 바꿔 다시 판정하고, 두 값을 **둘 다** 남긴다.

  (B) 정규화 실측 — 확산 경로 진폭이 **|a| ∝ 1/√N** 인가.
      §4 는 (Σ|a|² 수렴) + (|Σa| ∝ √N) 을 보였다. 그 둘을 한 문장으로 잇는 것이
      '진폭이 전력합 보존으로 정규화돼 있다' 는 사실이다. 추론으로 두지 말고 직접 잰다.

  (C) 변조 **깊이**를 dB 로 재계산 — 기록된 격자에서만(RT 재실행 없음).
      본 실행의 harm_absdb/harm_incdb 는 평균을 뺀 계열에 걸어서 `*_rel_dc` 가 0 으로 나눈
      쓰레기다(비율의 분모가 사라졌다). SNR 은 멀쩡하지만 **인용할 크기**가 없다.
      → 조화 1 성분의 진폭을 **dB 단위 그대로** 꺼내 "블레이드 조화가 Σ|a|² 를 몇 dB
        흔드는가" 라는 바로 쓸 수 있는 수로 만든다(peak-to-peak = 2×|Z₁|).

  (D) 경로수 거동 요약 — '연속으로 변하나 껐다 켜지나' 를 격자 전체에서 한 줄로.

⛔ src/drones.py · src/drone_cad.py 는 읽기만. 출력은 기존 본 실험 JSON 에 **추가**만 한다.
"""
from __future__ import annotations

import json
import math
import os
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (os.path.join(ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import report15_sweep_matrice4e as M                                   # noqa: E402
import sionna.rt as rt                                                 # noqa: E402

OUT = M.OUT_JSON
NO_OBJ = M.NO_OBJ


def amp_stats(scene, spp, seed, id2grp):
    """표적경유 경로의 **진폭 통계** — 경로수 N 과 평균 |a| 의 관계를 보기 위한 것."""
    p = rt.PathSolver()(scene, max_depth=1, los=True, specular_reflection=True,
                        diffuse_reflection=True, refraction=False,
                        samples_per_src=int(spp), max_num_paths_per_src=M.MAX_PATHS,
                        seed=int(seed))
    ar = np.asarray(p.a[0]); ai = np.asarray(p.a[1])
    a = (ar + 1j * ai).reshape(-1, ar.shape[-1])[0]
    P = int(a.shape[0])
    if P == 0:
        return None
    O = np.asarray(p.objects)[:, 0, 0, :]
    hit = (O != NO_OBJ).any(axis=0)
    if not hit.any():
        return None
    aa = np.abs(a[hit])
    tau = np.asarray(p.tau, dtype=np.float64).reshape(-1, P)[0][hit]
    ph = np.exp(-1j * 2.0 * np.pi * M.FC * tau)
    s = complex(np.sum(a[hit] * ph))
    return dict(n=int(hit.sum()), mean_abs_a=float(aa.mean()),
                median_abs_a=float(np.median(aa)),
                sum_abs2=float(np.sum(aa ** 2)),
                coh_abs=float(abs(s)))


def sec_normalization(spps=(16_000_000, 64_000_000, 256_000_000,
                            1_024_000_000, 4_096_000_000), seed=1) -> dict:
    """<|a|> 와 N 의 관계를 log-log 기울기로 **계산**한다.
      · −0.5 이면 |a| ∝ 1/√N → Σ|a|² 가 보존되도록 정규화된 것(전력합 규약).
      · 0 이면 진폭이 표본수와 무관 → 그때는 Σ|a|² 가 발산해야 한다.
    이 한 줄이 '코히런트 합을 물리적 산란장으로 읽으면 안 되는 이유' 의 뿌리다."""
    scene, d = M.build_posed_scene(0.0, "NORM")
    g2 = M.id_to_group(scene)
    out = {}
    for R in M.RANGES:
        M.place(scene, 0.0, 15.0, R)
        #  ⚠ 경로가 0 인 spp 는 빠질 수 있다 — spp 와 결과를 **짝으로** 들고 가야 열이 안 어긋난다.
        pairs = [(s, r) for s, r in ((s, amp_stats(scene, s, seed, g2)) for s in spps) if r]
        if len(pairs) < 3:
            continue
        used = [s for s, _ in pairs]
        rows = [r for _, r in pairs]
        n = np.array([r["n"] for r in rows], float)
        ma = np.array([r["mean_abs_a"] for r in rows], float)
        s2 = np.array([r["sum_abs2"] for r in rows], float)
        co = np.array([r["coh_abs"] for r in rows], float)
        sl = lambda y: float(np.polyfit(np.log10(n), np.log10(y), 1)[0])   # noqa: E731
        out[f"{R:g}"] = dict(
            range_m=float(R), spps=[int(s) for s in used],
            n_paths=[int(x) for x in n],
            mean_abs_a=[float(x) for x in ma],
            slope_log_mean_abs_a_vs_log_N=sl(ma),
            slope_log_sum_abs2_vs_log_N=sl(s2),
            slope_log_coh_vs_log_N=sl(co),
            power_normalised=bool(abs(sl(ma) + 0.5) < 0.1 and abs(sl(s2)) < 0.1),
            coherent_grows_as_sqrtN=bool(abs(sl(co) - 0.5) < 0.15))
    #  ⭐ 관측량 정의의 근거를 이 실행 안에서도 한 번 확인해 둔다:
    #    Paths.a 가 **패스밴드**(전파위상 없음)라는 것. imag 성분이 정확히 0 이어야 한다.
    M.place(scene, 0.0, 15.0, 3.0)
    r = M.trace(scene, 256_000_000, 1, True, g2, want_groups=True)
    passband = dict(a_imag_absmax=r.get("a_imag_absmax"), n_paths=r.get("n"),
                    tau_min_ns=r.get("tau_min_ns"), tau_ptp_ns=r.get("tau_ptp_ns"),
                    is_passband=bool((r.get("a_imag_absmax") or 1.0) == 0.0),
                    note_ko=("a 의 허수부가 정확히 0 이면 전파위상이 a 에 없다는 뜻 — 위상은 τ 가 "
                             "나른다. 그래서 관측량을 Σa 가 아니라 Σa·exp(−j2πfτ) 로 잡았다."))
    M.drop(d)
    return dict(
        by_range=out, seed=int(seed), passband_check=passband,
        conclusion_ko=(
            "확산 경로의 진폭은 |a| ∝ N^(−1/2) 로 정규화돼 있다 → Σ|a|² 는 표본수에 무관하게 "
            "수렴한다(전력합 보존). 그 표본들의 위상은 서로 독립이 아니라 기하가 정하므로, "
            "다시 **코히런트로** 더하면 합이 √N 으로 자란다. 따라서 "
            "h_coh = Σ a·exp(−j2πfτ) 의 **절대값은 물리적 산란장이 아니다** — "
            "광선예산을 바꾸면 값이 바뀐다. 이 실험의 물리 판정을 Σ|a|² 와 정반사 채널에 "
            "기대는 이유가 이것이다."),
        note_ko=("⚠ 이것은 Sionna 의 버그가 아니다. 확산 산란은 원래 **전력**으로 합치라고 "
                 "만들어진 모델이다. 버그는 그것을 코히런트로 다시 더한 쪽에 있다."))


def _two_sided(Z: np.ndarray) -> dict:
    """⭐ **양·음 측대역**(전진날 vs 후퇴날)을 따로 본다.

    마이크로도플러의 정의적 지문은 크기 변조가 아니라 **± 측대역의 비대칭**이다.
    복소 h(φ) 의 스펙트럼에서 +k 와 −k 를 갈라 봐야 그것이 보인다.
    (실수 dB 계열은 켤레대칭이라 +k 만 보면 되지만, 복소 계열은 아니다 —
     본 실행의 harm_complex 는 +k 만 훑었으므로 여기서 보완한다.)

    Z : [k, seed] 복소 FFT. 신호 = 시드 평균, 잡음 = 평균의 분산.
    """
    N, S = Z.shape
    Zm = Z.mean(axis=1)
    nse = (np.sum(np.abs(Z - Zm[:, None]) ** 2, axis=1) / (S - 1) / S) if S > 1 else np.zeros(N)
    ny = N // 2
    rows = []
    for k in range(1, ny):
        pk, mk = float(np.abs(Zm[k])), float(np.abs(Zm[N - k]))
        np_, nm = float(nse[k]), float(nse[N - k])
        rows.append(dict(
            bin=k, plus_abs=pk, minus_abs=mk,
            asym_db=float(20 * np.log10((pk + 1e-300) / (mk + 1e-300))),
            plus_snr_db=(None if np_ <= 0 else float(10 * np.log10(pk ** 2 / np_))),
            minus_snr_db=(None if nm <= 0 else float(10 * np.log10(mk ** 2 / nm)))))
    b1 = rows[0] if rows else None
    return dict(
        blade_flash=b1, per_bin=rows[:8],
        max_abs_asym_db=(float(max(abs(r["asym_db"]) for r in rows)) if rows else None),
        note_ko=("asym_db = 20log10(|Z(+k)|/|Z(−k)|). 진폭변조만 있으면 0 dB 에 가깝고, "
                 "진짜 도플러(전진/후퇴 분리)면 크게 벌어진다. ⭐ 단 이 계열은 코히런트 합이라 "
                 "spp 에 수렴하지 않는다(§4) — 구조는 읽되 절대값은 인용하지 말 것."))


def sec_depth(J: dict) -> dict:
    """(C)+(D) — 기록된 격자에서만 계산한다. RT 를 다시 돌리지 않는다.

    관측량마다 조화 1(=블레이드 플래시) 성분의 **크기를 dB 로** 낸다:
      · depth_pp_db = 2·|Z₁|   (그 조화가 만드는 peak-to-peak 흔들림, dB 계열이므로 단위가 dB)
      · snr_db      = 시드 재추첨 널 대비
    그리고 경로수 거동(연속/껐다켜짐, 스텝당 최대 상대변화)을 함께 묶는다."""
    G = J.get("grid") or {}
    blocks = G.get("blocks") or {}
    seeds = G.get("seeds") or []
    out, roll = {}, dict(continuous=0, onoff=0, empty=0)
    for key, B in blocks.items():
        for ch in ("all", "prop"):
            kn = "n" if ch == "all" else "n_prop"
            kr, ki = ("hr", "hi") if ch == "all" else ("hpr", "hpi")
            kinc = "inc" if ch == "all" else "inc_prop"
            n = np.array(B[kn], float)
            if n.size == 0:
                continue
            zero = float(np.mean(n == 0))
            if zero == 1.0:
                roll["empty"] += 1
                out[f"{key}/{ch}"] = dict(n_paths_behaviour="모든 칸에서 경로 0",
                                          zero_path_cell_frac=1.0)
                continue
            roll["onoff" if zero > 0 else "continuous"] += 1
            z = np.array(B[kr], float) + 1j * np.array(B[ki], float)
            inc = np.array([[np.nan if v is None else v for v in r] for r in B[kinc]], float)
            amp = 20 * np.log10(np.abs(z) + 1e-300)
            npm = n.mean(axis=1)
            dif = np.abs(np.diff(np.r_[npm, npm[0]]))
            rec = dict(zero_path_cell_frac=zero,
                       n_paths_behaviour=("껐다켜짐 (경로수가 0 을 오간다)" if zero > 0
                                          else "연속 (모든 칸에 경로 존재)"),
                       n_paths_mean=float(n.mean()),
                       n_paths_step_max_frac=float(dif.max() / max(1e-9, npm.mean())),
                       n_paths_step_median_frac=float(np.median(dif) / max(1e-9, npm.mean())))
            for nm, X in (("coh_db", amp), ("inc_db", inc)):
                if not np.all(np.isfinite(X)):
                    continue
                H = M._harm_seeded(X - X.mean())
                #  ⚠ 실수열의 FFT/N 은 진폭 A 의 성분을 |Z_k| = A/2 로 준다(에너지가 ±k 로 갈리므로).
                #    따라서 진폭 = 2|Z_k|, peak-to-peak = 4|Z_k|. (초안에서 2|Z_k| 를 pp 로
                #    적었다가 **2배 과소보고**할 뻔했다 — 여기 명시해 둔다.)
                rec[nm] = dict(
                    blade_flash_amp_db=float(2.0 * H["harm_abs"][0]),
                    blade_flash_depth_pp_db=float(4.0 * H["harm_abs"][0]),
                    blade_flash_snr_db=H["blade_flash_snr_db"],
                    noise_degenerate=H["noise_degenerate"],
                    dominant_bin=H["dominant_bin"],
                    dominant_depth_pp_db=(float(4.0 * H["harm_abs"][H["dominant_bin"] - 1])
                                          if H["dominant_bin"] else None),
                    n_bins_snr_gt_10db=H["n_bins_snr_gt_10db"],
                    total_ptp_db=float(np.nanmax(X.mean(axis=1)) - np.nanmin(X.mean(axis=1))),
                    seed_noise_std_db=float(np.mean(np.std(X, axis=1, ddof=1))))
            #  ⭐ 복소 h 의 ± 측대역 비대칭 (마이크로도플러의 정의적 지문)
            if np.all(np.isfinite(z)) and z.shape[1] > 1:
                rec["two_sided_complex"] = _two_sided(np.fft.fft(z, axis=0) / z.shape[0])
            out[f"{key}/{ch}"] = rec
    return dict(
        by_block=out, n_seeds=len(seeds), rollup=roll,
        note_ko=("depth_pp_db 는 그 조화 하나가 만드는 peak-to-peak 흔들림[dB]이다 "
                 "(실수열이므로 4·|Z_k|; amp_db = 2·|Z_k| 는 진폭). "
                 "⭐ inc_db(=Σ|a|², **수렴하는 양**)의 depth 가 물리적 진폭변조의 크기이고, "
                 "coh_db 의 depth 는 수렴하지 않는 추정량의 흔들림이라 물리량으로 인용하면 안 된다. "
                 "본 실행 JSON 의 grid_analysis[*].harm_absdb/harm_incdb 의 `*_rel_dc`·"
                 "`highest_bin_above_1pct` 필드는 평균을 뺀 계열이라 분모가 0 이다 — **쓰지 말 것**. "
                 "SNR·harm_abs 는 유효하다. 여기 by_block 이 그 대체값이다."))


def sec_statistic_validation(n_phase=64, n_seed=5, trials=400, thr_db=10.0) -> dict:
    """⭐ **판정 통계 자체를 합성자료로 검증**한다 — 이 실험의 결론이 전부 여기 걸려 있다.

    (a) 널: 신호를 넣지 않고 잡음만 → 문턱을 넘는 비율이 곧 **거짓양성률**.
    (b) 주입: 알려진 진폭의 블레이드 조화를 넣고 → 크기를 되찾는지(편향), 얼마나 잡는지(검정력).
    ⚠ 다중비교: 블록×채널×관측량 수만큼 검정을 하므로 거짓양성 기대 개수를 함께 적는다.
    """
    rng = np.random.default_rng(0)
    null = []
    for _ in range(trials):
        X = rng.normal(0.0, 1.0, (n_phase, n_seed))
        null.append(M._harm_seeded(X - X.mean())["blade_flash_snr_db"])
    null = np.array(null, float)
    inj = {}
    for A in (0.3, 1.0, 3.0):
        s, d = [], []
        for _ in range(trials // 2):
            X = (A * np.cos(2 * np.pi * np.arange(n_phase) / n_phase)[:, None]
                 + rng.normal(0.0, 1.0, (n_phase, n_seed)))
            H = M._harm_seeded(X - X.mean())
            s.append(H["blade_flash_snr_db"]); d.append(4.0 * H["harm_abs"][0])
        inj[f"{A:g}"] = dict(injected_amp_db=float(A), injected_pp_db=float(2 * A),
                             snr_median_db=float(np.median(s)),
                             detection_rate=float(np.mean(np.array(s) > thr_db)),
                             recovered_pp_db_median=float(np.median(d)),
                             bias_pp_db=float(np.median(d) - 2 * A))
    return dict(
        n_phase=int(n_phase), n_seed=int(n_seed), trials=int(trials),
        threshold_db=float(thr_db), noise_sigma_db=1.0,
        null_snr_median_db=float(np.median(null)),
        null_snr_p95_db=float(np.percentile(null, 95)),
        false_positive_rate=float(np.mean(null > thr_db)),
        injection=inj,
        note_ko=("널 거짓양성률이 문턱 10 dB 에서 얼마인지가 핵심이다. 블록·채널·관측량마다 "
                 "검정을 돌리므로 **기대 거짓양성 개수 = 거짓양성률 × 검정 수** 를 반드시 "
                 "함께 읽어야 한다(expected_false_positives). 개별 칸 하나가 '유의' 라고 "
                 "떴다고 그것만 인용하면 안 된다."))


def sec_material_matched(J: dict) -> dict:
    """⭐ 재질 반사실을 **공정하게** 비교한다.

    ⚠ 두 인구조사가 **다른 위상 집합**을 돌았다(생산 4위상 / PEC 2위상). 총계를 그대로
      나란히 놓으면 '재질을 바꾸니 정반사가 줄었다' 는 가짜 결론이 나온다. 공유 위상만
      골라 칸 대 칸으로 맞춰야 한다. 여기서 그것을 한다(RT 재실행 없음).

    기대: 재질은 경로의 **진폭**만 바꾸고 **존재 여부**는 못 바꾼다(기하가 정한다).
    """
    pr = J["specular_census"].get("production")
    pe = J["specular_census"].get("pec_prop")
    if not (pr and pe):
        return {}
    shared = sorted(set(pr["phases_deg"]) & set(pe["phases_deg"]))
    key = lambda r: (r["phase_deg"], r["range_m"], r["az_deg"], r["el_deg"])   # noqa: E731
    A = {key(r): r for r in pr["hit_cells"] if r["phase_deg"] in shared}
    B = {key(r): r for r in pe["hit_cells"] if r["phase_deg"] in shared}
    both = sorted(set(A) & set(B))
    only_a = sorted(set(A) - set(B))
    only_b = sorted(set(B) - set(A))
    dd = []
    for k in both:
        if A[k]["amp_db"] is not None and B[k]["amp_db"] is not None:
            dd.append(dict(cell=list(k), n_prod=A[k]["n"], n_pec=B[k]["n"],
                           prop_prod=A[k]["n_prop"], prop_pec=B[k]["n_prop"],
                           amp_prod_db=A[k]["amp_db"], amp_pec_db=B[k]["amp_db"],
                           delta_db=float(B[k]["amp_db"] - A[k]["amp_db"])))
    dprop = [x["delta_db"] for x in dd if x["prop_prod"] > 0]
    return dict(
        shared_phases_deg=shared,
        n_specular_cells_production=len(A), n_specular_cells_pec=len(B),
        n_cells_in_both=len(both), n_only_production=len(only_a), n_only_pec=len(only_b),
        path_existence_identical=bool(not only_a and not only_b),
        n_prop_specular_cells_production=int(sum(1 for k in A if A[k]["n_prop"] > 0)),
        n_prop_specular_cells_pec=int(sum(1 for k in B if B[k]["n_prop"] > 0)),
        amp_delta_db_on_prop_cells=dprop,
        amp_delta_db_median_on_prop_cells=(float(np.median(dprop)) if dprop else None),
        expected_delta_db_pec_vs_plastic=float(
            -J["materials"]["by_group"]["prop"]["gamma_db_vs_pec"]),
        per_cell=dd,
        conclusion_ko=(
            "공유 위상에서 경로 **존재 여부**가 같으면, 재질은 정반사의 유무를 못 바꾼다는 뜻이다 "
            "— 블레이드 글린트가 드문 것은 **반사계수가 낮아서가 아니라 기하·솔버 때문**이다. "
            "진폭 차이(delta_db)는 |Γ| 비 예측값과 맞아야 한다."))


def main():
    with open(OUT) as f:
        J = json.load(f)

    #  (A) §1b 판정 재계산 — 기록된 rows 에서만
    rp = J.get("rt_periodicity")
    if rp and rp.get("rows"):
        old = {k: rp.get(k) for k in ("path_count_identical", "bit_identical",
                                      "functionally_identical")}
        new = M._periodicity_verdict(rp["rows"], rp["phases_deg"], rp["seeds"], rp["spp"])
        new["superseded_verdict_from_first_pass"] = old
        new["rule_change_ko"] = (
            "1차 규칙은 '경로수가 **정확히** 같아야 기능적 동일' 이었다. 60쌍 중 한 쌍이 "
            "수천 개 중 1 개(상대 %.1e) 달랐고 그때도 복소 상대차는 %.1e(%.1f dB)였다. "
            "절대 0 을 요구하면 '파이프라인이 비결정론적' 이라는 잘못된 보고가 된다 → "
            "상대량 기준(경로수 상대차 <1e−3, 복소 상대차 <1e−3, |Δ|h||<1e−3 dB)으로 바꿨다. "
            "bit_identical(절대 0)은 그대로 함께 남긴다."
            % (new.get("max_rel_dn") or 0.0, new.get("max_rel_complex_diff") or 0.0,
               new.get("max_rel_complex_diff_db") or 0.0))
        J["rt_periodicity"] = new

    #  (B) 정규화 실측
    t0 = time.time()
    J["normalization"] = sec_normalization()
    J["normalization"]["seconds"] = float(time.time() - t0)
    for k, v in J["normalization"]["by_range"].items():
        print(f"  R={k:>4} m  d log<|a|>/d log N = {v['slope_log_mean_abs_a_vs_log_N']:+.3f} "
              f"(−0.5 이면 전력정규화)   d log Σ|a|²/d log N = "
              f"{v['slope_log_sum_abs2_vs_log_N']:+.3f}   d log|Σa|/d log N = "
              f"{v['slope_log_coh_vs_log_N']:+.3f}  → 전력정규화={v['power_normalised']}",
              flush=True)

    #  재질 반사실 — 공유 위상만 맞춰 비교
    mm = sec_material_matched(J)
    if mm:
        J["specular_census"]["material_matched"] = mm
        print(f"  재질 반사실(공유위상 {mm['shared_phases_deg']}): 정반사 칸 "
              f"생산 {mm['n_specular_cells_production']} vs PEC {mm['n_specular_cells_pec']}, "
              f"존재 동일={mm['path_existence_identical']}, 프롭칸 "
              f"{mm['n_prop_specular_cells_production']} vs {mm['n_prop_specular_cells_pec']}, "
              f"진폭차 중앙 {mm['amp_delta_db_median_on_prop_cells']} dB "
              f"(예측 {mm['expected_delta_db_pec_vs_plastic']:.2f} dB)", flush=True)

    #  판정 통계 검증 (합성자료, GPU 불필요)
    ns = len(J.get("grid", {}).get("seeds") or [1, 2, 3, 4, 5])
    npz = len(J.get("grid", {}).get("phases_deg") or [0] * 64)
    J["statistic_validation"] = sec_statistic_validation(n_phase=npz, n_seed=ns)
    sv = J["statistic_validation"]
    print(f"  통계검증: 널 거짓양성률 {sv['false_positive_rate']:.3f} @ {sv['threshold_db']:.0f} dB, "
          f"주입 1 dB 검출률 {sv['injection']['1']['detection_rate']:.2f}, "
          f"pp 편향 {sv['injection']['1']['bias_pp_db']:+.3f} dB", flush=True)

    #  (C)+(D) 기록된 격자에서만 재계산
    if J.get("grid", {}).get("blocks"):
        J["modulation_depth"] = sec_depth(J)
        r = J["modulation_depth"]["rollup"]
        print(f"  경로수 거동 집계: 연속 {r['continuous']} / 껐다켜짐 {r['onoff']} / "
              f"전부 0 {r['empty']} (블록·채널 단위)", flush=True)

    #  규약 차이를 JSON 안에 명시 (읽는 사람이 두 섹션을 같은 축으로 착각하지 않게)
    bc = J.get("baseline_control")
    if bc is not None:
        bc["phase_span_deg"] = 360.0
        bc["convention_warning_ko"] = (
            "⚠ 이 대조의 위상축은 **한 바퀴(360°)** 다 — 본 격자(grid)는 한 주기(180°)를 "
            "n_phase 등분한다. 주기가 180° 이므로 여기서는 같은 형상을 두 번 훑는다. "
            "거리 추세 비교용으로만 쓰고, 조화 차수를 grid 와 나란히 놓지 말 것.")

    #  헤드라인 갱신 (판정이 바뀐 필드가 있으므로)
    if "grid_analysis" in J and "headline" in J:
        J["headline"] = M.headline(J)
        if "modulation_depth" in J:
            J["headline"]["blade_flash_depth_pp_db"] = {
                k: dict(coh=(v.get("coh_db") or {}).get("blade_flash_depth_pp_db"),
                        inc=(v.get("inc_db") or {}).get("blade_flash_depth_pp_db"))
                for k, v in J["modulation_depth"]["by_block"].items()
                if v.get("coh_db") or v.get("inc_db")}
            J["headline"]["n_paths_behaviour_rollup"] = J["modulation_depth"]["rollup"]
        #  ⚠ 다중비교 — 개별 '유의' 칸을 그것만 떼어 인용하지 않도록 기대 거짓양성 수를 박아 둔다.
        n_tests = 2 * len([1 for v in J["grid_analysis"]["by_block"].values() if v.get("ok")])
        J["headline"]["n_significance_tests"] = int(n_tests)
        J["headline"]["false_positive_rate_per_test"] = sv["false_positive_rate"]
        J["headline"]["expected_false_positives"] = float(n_tests * sv["false_positive_rate"])
    J.setdefault("meta", {})["addendum"] = dict(
        script="benchmark/report15_sweep_matrice4e_addendum.py",
        stamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        added=["rt_periodicity(판정 재계산 — RT 재실행 없음)", "normalization(신규 측정)"])

    def _clean(o):
        if isinstance(o, dict):
            return {k: _clean(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [_clean(v) for v in o]
        if isinstance(o, (float, np.floating)):
            f = float(o)
            return None if (math.isnan(f) or math.isinf(f)) else f
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.bool_):
            return bool(o)
        return o

    with open(OUT, "w") as f:
        json.dump(_clean(J), f, ensure_ascii=False, indent=1, allow_nan=False)
    print(f"✅ 덧붙임 저장 → {OUT}")


if __name__ == "__main__":
    main()
