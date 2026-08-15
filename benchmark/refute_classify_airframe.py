# -*- coding: utf-8 -*-
"""
refute_classify_airframe.py — classify_airframe.py 적대적 반증 라운드 (CPU 전용)
================================================================================
공격 렌즈: 교정·누출·통계.
  A. 결정론 재현 — 저장된 JSON 수치가 재계산과 일치하나.
  B. 널 씨앗 민감도 — 셔플 씨앗 5개에서 널 정확도가 우연(1/3) 근방에 머무나,
     널 예측이 정말 matrice4e 고정으로 쏠리나(문서화된 기전 검증).
  C. 창 규약 — 창 경계를 256 자세 밀어도(offset), 창 크기를 바꿔도(8×1024, 32×256)
     결론이 버티나(경계 우연에 업힌 100% 인지).
  D. 덮개율 편향 — 빗살 몫을 덮개율로 보정(score−coverage, score/coverage)하면
     argmax 가 뒤집히나(불균등 덮개율이 진짜 판정을 훔쳤나).
  E. 템플릿 누출 대조 — 세 템플릿을 공통 +5/+10 Hz 밀면 정확도가 무너져야 한다
     (진짜 고조파 정합이라면). 안 무너지면 빗살이 신호 아닌 다른 것을 세는 것.
  F. 스펙트럼 보존 대리자료 — 위상 무작위화(전체 |FFT| 보존)·원형 이동은 정확도가
     유지되어야 한다(셔플 널 붕괴가 '백색화' 때문임을 확정하는 양성 대조).
  G. 유효 표본 수 — 336 창은 독립이 아니다: 같은 (엔진×기체×앙각) 시계열 안 16 창의
     판정 일치율을 세서 독립 판정 단위(=42 시계열)를 문서화.
⛔ GPU/솔버 없음 · 기존 파일 수정 없음(산출은 outputs/refute_classify_airframe.json 뿐).
"""
from __future__ import annotations

import json
import os
import time

import numpy as np

import classify_airframe as ca  # 저자 코드 그대로 재사용(동일 파이프라인 보장)

OUT = "outputs/refute_classify_airframe.json"

AF = ca.AIRFRAMES
ENG = ca.ENGINES


def load():
    led, npz = ca.load_ledger()
    prf = float(led["_meta"]["prf_hz"])
    lam = ca.C_LIGHT / float(led["_meta"]["fc_hz"])
    els = [float(e) for e in led["_meta"]["elevations_deg"]]
    tmpl = ca.spec_templates(lam)
    cand = {a: tmpl[a]["f_flash_hz_spec"] for a in AF}
    E = {}
    for eng in ENG:
        for a in AF:
            arm = ca.CHOSEN_ARM[eng][a]
            for el in els:
                E[(eng, a, el)] = np.asarray(npz[f"{arm}/{ca.elkey_of(el)}"])
    return prf, els, cand, E


def acc_from_scores(prf, els, cand, E, score_fn):
    """score_fn(E_series) -> (N_WIN,3) 점수. 반환: 엔진별 정확도·혼동행렬·앙각별 정확도."""
    out = {}
    for eng in ENG:
        cm = np.zeros((3, 3), int)
        per_el = {}
        for el in els:
            cme = np.zeros((3, 3), int)
            for i, a in enumerate(AF):
                sc = score_fn(E[(eng, a, el)], prf, cand)
                for p in sc.argmax(axis=1):
                    cme[i, p] += 1
            cm += cme
            per_el[f"{el:+.0f}"] = round(float(np.trace(cme)) / cme.sum(), 4)
        out[eng] = {"accuracy": round(float(np.trace(cm)) / cm.sum(), 4),
                    "confusion": cm.tolist(), "per_el_accuracy": per_el}
    return out


def windows_variant(E, prf, cand, win_len, n_win, offset=0):
    """저자 레시피 그대로(창별 DC 제거·hanning·NFFT 제로패딩·AC 빗살 몫), 창 규약만 변형."""
    freqs = np.fft.fftfreq(ca.NFFT, d=1.0 / prf)
    ac = np.abs(freqs) >= ca.AC_MIN_HZ
    masks = {a: ca.comb_masks(freqs, cand[a]) & ac for a in AF}
    han = np.hanning(win_len)
    out = np.zeros((n_win, 3))
    for w in range(n_win):
        x = E[offset + w * win_len: offset + (w + 1) * win_len]
        x = x - x.mean()
        P = np.abs(np.fft.fft(x * han, ca.NFFT)) ** 2
        tot = P[ac].sum()
        for j, a in enumerate(AF):
            out[w, j] = P[masks[a]].sum() / tot if tot > 0 else 0.0
    return out


def main():
    t0 = time.time()
    prf, els, cand, E = load()
    saved = json.load(open(ca.OUT_JSON, encoding="utf-8"))
    rep = {"_meta": {"generator": "benchmark/refute_classify_airframe.py",
                     "target": "benchmark/classify_airframe.py",
                     "prf_hz": prf, "elevations_deg": els, "templates_hz": cand}}

    # ---------- A. 결정론 재현 ----------
    base = acc_from_scores(prf, els, cand, E, ca.window_scores)
    rep["A_reproduction"] = {
        eng: {"recomputed_accuracy": base[eng]["accuracy"],
              "saved_accuracy": saved["results"][eng]["aggregate_accuracy"],
              "match": base[eng]["accuracy"] == saved["results"][eng]["aggregate_accuracy"],
              "recomputed_confusion": base[eng]["confusion"],
              "saved_confusion": saved["results"][eng]["aggregate_confusion"]}
        for eng in ENG}

    # ---------- B. 널 씨앗 민감도 + 고정예측 기전 ----------
    seeds = [1, 7, 12345, 20260815, 987654321]
    null_sweep = {}
    for eng in ENG:
        rows = []
        for sd in seeds:
            rng = np.random.default_rng(sd)
            cm = np.zeros((3, 3), int)
            for el in els:
                for i, a in enumerate(AF):
                    x = E[(eng, a, el)]
                    xn = x[rng.permutation(x.size)]
                    for p in ca.window_scores(xn, prf, cand).argmax(axis=1):
                        cm[i, p] += 1
            pred_frac = (cm.sum(axis=0) / cm.sum()).round(4).tolist()  # 예측 열 분포
            rows.append({"seed": sd, "null_accuracy": round(float(np.trace(cm)) / cm.sum(), 4),
                         "pred_fraction_[mini,matrice,s1000]": pred_frac})
        accs = [r["null_accuracy"] for r in rows]
        null_sweep[eng] = {"per_seed": rows,
                          "min": min(accs), "max": max(accs),
                          "all_within_1/3±0.15": all(abs(v - 1 / 3) < 0.15 for v in accs)}
    rep["B_null_seed_sweep"] = null_sweep

    # ---------- C. 창 규약 변형 ----------
    variants = {
        "offset256_15win512": lambda x, p, c: windows_variant(x, p, c, 512, 15, offset=256),
        "win1024_x8": lambda x, p, c: windows_variant(x, p, c, 1024, 8),
        "win256_x32": lambda x, p, c: windows_variant(x, p, c, 256, 32),
    }
    rep["C_window_convention"] = {name: acc_from_scores(prf, els, cand, E, fn)
                                  for name, fn in variants.items()}

    # ---------- D. 덮개율 보정 점수 ----------
    cover = ca.coverage_fracs(prf, cand)
    cov = np.array([cover[a] for a in AF])

    def sub_cov(x, p, c):
        return ca.window_scores(x, p, c) - cov[None, :]

    def div_cov(x, p, c):
        return ca.window_scores(x, p, c) / cov[None, :]

    rep["D_coverage_normalized"] = {
        "coverage": cover,
        "score_minus_coverage": acc_from_scores(prf, els, cand, E, sub_cov),
        "score_div_coverage": acc_from_scores(prf, els, cand, E, div_cov),
    }

    # ---------- E. 템플릿 공통 이동(누출 대조: 무너져야 정상) ----------
    shift_res = {}
    for dz in (5.0, 10.0):
        cand_s = {a: cand[a] + dz for a in AF}
        shift_res[f"+{dz:.0f}Hz"] = acc_from_scores(prf, els, cand_s, E, ca.window_scores)
    rep["E_template_shift_control"] = shift_res

    # ---------- F. 스펙트럼 보존 대리자료(유지되어야 정상) ----------
    rng = np.random.default_rng(2468)
    accs_pr, accs_roll = {}, {}
    for eng in ENG:
        cm_pr = np.zeros((3, 3), int)
        cm_roll = np.zeros((3, 3), int)
        for el in els:
            for i, a in enumerate(AF):
                x = E[(eng, a, el)]
                X = np.fft.fft(x - x.mean())
                surr = np.fft.ifft(np.abs(X) * np.exp(1j * rng.uniform(0, 2 * np.pi, X.size)))
                for p in ca.window_scores(surr, prf, cand).argmax(axis=1):
                    cm_pr[i, p] += 1
                for p in ca.window_scores(np.roll(x, int(rng.integers(1, x.size))), prf, cand).argmax(axis=1):
                    cm_roll[i, p] += 1
        accs_pr[eng] = round(float(np.trace(cm_pr)) / cm_pr.sum(), 4)
        accs_roll[eng] = round(float(np.trace(cm_roll)) / cm_roll.sum(), 4)
    rep["F_spectrum_preserving_controls"] = {
        "phase_randomized_accuracy": accs_pr, "circular_shift_accuracy": accs_roll,
        "note_ko": "위상만 무작위(전체 |FFT| 보존)·원형 이동은 높게 유지되어야 하고, "
                   "그래야 셔플 널의 붕괴가 '백색화' 때문이라는 저자 기전이 선다."}

    # ---------- G. 유효 표본 수(창 상관) ----------
    per_series = {}
    for eng in ENG:
        unanimous = 0
        n_series = 0
        for el in els:
            for i, a in enumerate(AF):
                pred = ca.window_scores(E[(eng, a, el)], prf, cand).argmax(axis=1)
                n_series += 1
                if (pred == pred[0]).all():
                    unanimous += 1
        per_series[eng] = {"n_series": n_series, "unanimous_series": unanimous,
                           "unanimity_frac": round(unanimous / n_series, 4)}
    rep["G_effective_sample_size"] = {
        **per_series,
        "note_ko": "같은 시계열의 16 창은 강하게 상관 — 336 창은 독립 판정 336개가 아니라 "
                   "엔진당 21 시계열(3기체×7앙각)이 실질 단위다."}

    rep["_meta"]["elapsed_s"] = round(time.time() - t0, 1)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=1,
                  default=lambda o: o.item() if hasattr(o, "item") else str(o))  # numpy 스칼라 변환

    # 콘솔 요약
    print("=== A 재현 ===")
    for eng in ENG:
        r = rep["A_reproduction"][eng]
        print(f"  {eng}: recomputed {r['recomputed_accuracy']} vs saved {r['saved_accuracy']} match={r['match']}")
    print("=== B 널 씨앗 5개 ===")
    for eng in ENG:
        s = rep["B_null_seed_sweep"][eng]
        print(f"  {eng}: min {s['min']} max {s['max']} within±0.15={s['all_within_1/3±0.15']}")
        for row in s["per_seed"]:
            print(f"     seed {row['seed']}: {row['null_accuracy']} pred_frac {row['pred_fraction_[mini,matrice,s1000]']}")
    print("=== C 창 규약 변형 ===")
    for name, res in rep["C_window_convention"].items():
        print(f"  {name}: " + ", ".join(f"{e} {res[e]['accuracy']}" for e in ENG))
        for e in ENG:
            print(f"     {e} per-el: {res[e]['per_el_accuracy']}")
    print("=== D 덮개율 보정 ===")
    for name in ("score_minus_coverage", "score_div_coverage"):
        res = rep["D_coverage_normalized"][name]
        print(f"  {name}: " + ", ".join(f"{e} {res[e]['accuracy']}" for e in ENG))
        for e in ENG:
            print(f"     {e} per-el: {res[e]['per_el_accuracy']}")
    print("=== E 템플릿 이동(무너져야 정상) ===")
    for name, res in rep["E_template_shift_control"].items():
        print(f"  {name}: " + ", ".join(f"{e} {res[e]['accuracy']}" for e in ENG))
    print("=== F 스펙트럼 보존 대조(유지되어야 정상) ===")
    print("  phase-randomized:", rep["F_spectrum_preserving_controls"]["phase_randomized_accuracy"])
    print("  circular-shift  :", rep["F_spectrum_preserving_controls"]["circular_shift_accuracy"])
    print("=== G 유효 표본 ===")
    for eng in ENG:
        print(f"  {eng}: {per_series[eng]}")


if __name__ == "__main__":
    main()
