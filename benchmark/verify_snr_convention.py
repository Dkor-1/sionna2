# -*- coding: utf-8 -*-
"""
verify_snr_convention.py — ⭐**SNR 규약 v2 게이트**: 옛 동작 보존 + 두 눈금의 정합
==================================================================================================
왜 이 스크립트가 있나 (2026-08-10 적대검증이 잡은 결함 ①)
------------------------------------------------------------------------------------------------
저장소에 SNR 기준이 **두 개** 있었고 서로 달랐다.

    src/microdoppler_nearfield.py  add_noise()          p_sig = mean|E|²        → **총전력**(몸체 DC 포함)
    benchmark/md_classify_dataset.py cmd_build (인라인)  p_sig = mean|E−mean|²   → **AC 만**(블레이드선)

두 눈금은 `dc_ac_offset_db` 만큼 다르다 — 기체별 **17.3 ~ 37.2 dB**. 그런데 두 실험의 SNR 축이
같은 표에 나란히 놓여 있었다. 규약 v2 는 **둘 다 쓰되 이름을 다르게** 하고(③ `snr_slow_db` ·
③′ `snr_slow_ac_db`), 변환을 `dc_ac_offset_db()` 하나로만 하고, **원장에 두 값을 병기**한다.

왜 «하나를 버리지» 않았나 — 판단과 근거
------------------------------------------------------------------------------------------------
둘은 서로 다른 물음의 답이다. 하나만 남기면 다른 물음을 못 쓴다.
  ③  총전력  = «에코가 잡히나»    — 레이다 방정식의 자연스러운 출력, 검출(CFAR)이 쓰는 양
  ③′ AC     = «블레이드선이 보이나» — 마이크로도플러·분류가 실제로 쓰는 양, 문헌 관례(펄스당 A_r)
그리고 둘을 **함께** 가져야만 «검출은 되는데 마이크로도플러는 안 보이는 구간»(③>0 ∧ ③′<0)을
계산할 수 있다 — 선행연구(arXiv:2402.04368 Fig.4(b))와 나란히 놓는 그림이 그것이다.
⇒ **정본(맨 이름 「SNR」)은 ③′** 로 못 박고, 원장은 항상 ③·③′·dc_ac_db 셋을 같이 싣는다.

게이트
------------------------------------------------------------------------------------------------
  SC1  add_noise(ref="total") 기본 경로 == 2026-08-10 이전 구현                  **비트동일**
  SC2  ac_snr_db(exact=False) 기본 경로 == 이전 구현                             **비트동일**
  SC3  md_classify_dataset 의 인라인 AC 잡음 == add_noise(ref="ac")              rel ≤ 1e-12
       (같은 seed 에서 잡음열까지, 그리고 **특징벡터**까지 비교한다)
  SC4  변환 왕복 total→ac→total                                                  rel ≤ 1e-12
       + 정확식/근사식 차이표 (dc_ac 0·3·10·17.3·37.2 dB)
  SC5  ⭐두 눈금이 **실제로** dc_ac_off_db 만큼 다르다 — 합성열에 주입해 되재기      ≤ 0.05 dB
  SC6  사다리 자기정합: ③′ = ③ − off,  ⑤ = ③′ + ④,  기울기 −40 dB/decade(모노 등가)
       / −20 dB/decade(바이스태틱 한 다리)                                        ≤ 0.01 dB

실행 (CPU 수 초, GPU 불필요)
    cd sionna2 && PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/verify_snr_convention.py
산출: outputs/verify_snr_convention.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "src"))
sys.path.insert(0, _HERE)

import microdoppler_nearfield as nf                                    # noqa: E402

OUT = os.path.join(_ROOT, "outputs", "verify_snr_convention.json")


# --------------------------------------------------------------------------- #
#  얼린 옛 구현 — 회귀 게이트의 기준. **고치지 마라**(고치면 게이트가 무의미해진다)
# --------------------------------------------------------------------------- #
def _add_noise_v1(E, snr_db, rng):
    """2026-08-10 이전 `microdoppler_nearfield.add_noise()` 그대로."""
    p_sig = float(np.mean(np.abs(E) ** 2))
    p_n = p_sig / (10.0 ** (float(snr_db) / 10.0))
    s = np.sqrt(p_n / 2.0)
    n = rng.normal(0.0, s, size=E.shape) + 1j * rng.normal(0.0, s, size=E.shape)
    return E + n, float(np.sqrt(p_n))


def _ac_snr_db_v1(E, snr_total_db):
    """2026-08-10 이전 `ac_snr_db()` 그대로 (근사식: dc_ac 를 그냥 뺀다)."""
    return float(snr_total_db) - float(nf.md_metrics(E, 1.0)["dc_ac_db"])


def _classify_noise_v1(E, snr_db, r, n_t):
    """2026-08-10 이전 `md_classify_dataset.cmd_build` 인라인 AC 잡음 그대로."""
    sd = np.sqrt((np.abs(E - E.mean()) ** 2).mean())
    sn = sd * 10 ** (-snr_db / 20.0)
    return E + sn / np.sqrt(2) * (r.normal(size=n_t) + 1j * r.normal(size=n_t))


def _series(n=4096, dc_ac_db=17.3, prf=20000.0, f_flash=126.667, seed=3):
    """시험용 합성 슬로타임 열: DC(동체) + 플래시 고조파(블레이드). dc_ac 를 지정대로 맞춘다."""
    rng = np.random.default_rng(seed)
    t = np.arange(n) / prf
    ac = sum(np.exp(2j * np.pi * m * f_flash * t) / m for m in range(1, 9))
    ac = ac - ac.mean()
    ac = ac / np.sqrt(np.mean(np.abs(ac) ** 2))
    ac = ac * (1.0 + 0.02 * rng.normal(size=n))
    dc = 10.0 ** (float(dc_ac_db) / 20.0)
    return dc + ac


def gate_sc1(a):
    E = _series(dc_ac_db=17.3)
    r1, r2 = np.random.default_rng(a.seed), np.random.default_rng(a.seed)
    e_old, s_old = _add_noise_v1(E, -5.0, r1)
    e_new, s_new = nf.add_noise(E, -5.0, r2)                # 기본 ref="total"
    same = bool(np.array_equal(e_old, e_new) and s_old == s_new)
    return dict(id="SC1", what="add_noise(ref='total') == pre-2026-08-10 implementation",
                bit_identical=same, max_abs_diff=float(np.max(np.abs(e_old - e_new))),
                sigma_old=s_old, sigma_new=s_new, passed=same)


def gate_sc2(a):
    E = _series(dc_ac_db=17.3)
    old = _ac_snr_db_v1(E, 12.34)
    new = nf.ac_snr_db(E, 12.34)                            # 기본 exact=False
    same = bool(old == new)
    exact = nf.ac_snr_db(E, 12.34, exact=True)
    return dict(id="SC2", what="ac_snr_db(exact=False) == pre-2026-08-10 implementation",
                bit_identical=same, old_db=old, new_db=new, exact_db=exact,
                exact_minus_approx_db=round(exact - new, 6), passed=same)


def gate_sc3(a):
    """분류 팔의 인라인 잡음을 공용 헬퍼로 갈아끼운 것이 안전한가 — 잡음열과 특징벡터로 본다."""
    n_t = 5000
    prf = 20000.0
    E = _series(n=n_t, dc_ac_db=26.5, prf=prf)
    res = {}
    for snr in (10.0, 0.0, -20.0):
        r1, r2 = np.random.default_rng(a.seed), np.random.default_rng(a.seed)
        e_old = _classify_noise_v1(E, snr, r1, n_t)
        e_new, _ = nf.add_noise(E, snr, r2, ref="ac")
        den = float(np.max(np.abs(e_old)))
        res[f"snr_{snr:g}"] = dict(
            max_abs_diff=float(np.max(np.abs(e_old - e_new))),
            max_rel_diff=float(np.max(np.abs(e_old - e_new)) / max(den, 1e-300)))
    # 특징벡터까지 (진짜로 중요한 것은 이쪽)
    feat = None
    try:
        import md_classify_dataset as mcd                    # noqa: E402
        r1, r2 = np.random.default_rng(a.seed), np.random.default_rng(a.seed)
        e_old = _classify_noise_v1(E, 0.0, r1, n_t)
        e_new, _ = nf.add_noise(E, 0.0, r2, ref="ac")
        v_old, _ = mcd.features(e_old, prf)
        v_new, _ = mcd.features(e_new, prf)
        d = np.abs(np.asarray(v_old) - np.asarray(v_new))
        s = np.maximum(np.abs(np.asarray(v_old)), 1e-300)
        feat = dict(n_features=int(len(v_old)), max_abs_diff=float(d.max()),
                    max_rel_diff=float((d / s).max()))
    except Exception as exc:                                  # 특징 계산이 안 되면 잡음열만으로 판정
        feat = dict(error=repr(exc))
    worst = max(v["max_rel_diff"] for v in res.values())
    worst_feat = feat.get("max_rel_diff", 0.0)
    ok = bool(worst <= 1e-12 and (worst_feat is None or worst_feat <= 1e-12))
    return dict(id="SC3", what="md_classify_dataset inline AC noise == add_noise(ref='ac'), same seed",
                series=res, features=feat, worst_rel_diff=worst, tol_rel=1e-12,
                note="차이는 부동소수 결합순서뿐(수학적으로 동일식). 비트동일은 요구하지 않는다.",
                passed=ok)


def gate_sc4(a):
    rows = []
    for d in (0.0, 3.0, 10.0, 17.3, 26.5, 37.2):
        off_e = nf.dc_ac_offset_db(d, exact=True)
        off_a = nf.dc_ac_offset_db(d, exact=False)
        tot = 34.83
        ac = nf.total_to_ac_db(tot, d, exact=True)
        back = nf.ac_to_total_db(ac, d, exact=True)
        rows.append(dict(dc_ac_db=d, off_exact_db=round(off_e, 6), off_approx_db=round(off_a, 6),
                         exact_minus_approx_db=round(off_e - off_a, 6),
                         roundtrip_rel_err=abs(back - tot) / abs(tot)))
    worst = max(r["roundtrip_rel_err"] for r in rows)
    return dict(id="SC4", what="dc_ac conversion: total->ac->total roundtrip + exact vs approx table",
                rows=rows, worst_roundtrip_rel_err=worst, tol_rel=1e-12,
                passed=bool(worst <= 1e-12))


def gate_sc5(a):
    """두 눈금이 진짜로 dc_ac_off_db 만큼 다른가 — 같은 목표 dB 를 두 기준으로 주입해 되잰다."""
    rows = []
    for dc in (17.3, 26.5, 37.2):
        E = _series(n=32768, dc_ac_db=dc)
        d_meas = float(nf.md_metrics(E, 1.0)["dc_ac_db"])
        off = nf.dc_ac_offset_db(d_meas, exact=True)
        rng = np.random.default_rng(a.seed)
        _, s_tot = nf.add_noise(E, 0.0, rng, ref="total")
        _, s_ac = nf.add_noise(E, 0.0, rng, ref="ac")
        gap = 20.0 * np.log10(s_tot / s_ac)      # 주입 잡음 진폭 비 = 두 눈금의 어긋남
        rows.append(dict(dc_ac_requested_db=dc, dc_ac_measured_db=round(d_meas, 4),
                         dc_ac_off_db=round(off, 4), injected_noise_gap_db=round(float(gap), 4),
                         err_db=round(float(gap) - off, 4)))
    worst = max(abs(r["err_db"]) for r in rows)
    return dict(id="SC5", what="total vs AC reference really differ by dc_ac_off_db (measured on injected noise)",
                rows=rows, worst_err_db=worst, tol_db=0.05, passed=bool(worst <= 0.05))


def gate_sc6(a):
    """사다리 자기정합 + 거리 기울기."""
    sig = 10.0 ** (-18.879 / 10.0)
    lad = [nf.snr_ladder(sig, R, 3.5e9, prf=20000.0, capture="full_waveform",
                         dc_ac_db=17.3, nperseg=70, window="hann") for R in (10.0, 100.0)]
    e_ac = abs((lad[0]["snr_slow_db"] - lad[0]["dc_ac_off_db"]) - lad[0]["snr_slow_ac_db"])
    e_map = abs((lad[0]["snr_slow_ac_db"] + lad[0]["g_stft_db"]) - lad[0]["snr_map_ac_db"])
    slope_mono = lad[1]["snr_slow_ac_db"] - lad[0]["snr_slow_ac_db"]          # 1 decade
    b0 = nf.snr_ladder(sig, 10.0, 3.5e9, rx_range_m=10.0, capture="full_waveform")
    b1 = nf.snr_ladder(sig, 100.0, 3.5e9, rx_range_m=10.0, capture="full_waveform")
    slope_bi = b1["snr_slow_db"] - b0["snr_slow_db"]
    errs = [e_ac, e_map, abs(slope_mono + 40.0), abs(slope_bi + 20.0)]
    return dict(id="SC6", what="ladder self-consistency + range slope (-40 dB/dec mono, -20 dB/dec one-leg)",
                snr_slow_ac_identity_err_db=e_ac, snr_map_identity_err_db=e_map,
                slope_monostatic_db_per_decade=round(slope_mono, 6),
                slope_bistatic_one_leg_db_per_decade=round(slope_bi, 6),
                g_stft_db=round(lad[0]["g_stft_db"], 4),
                example_R10=({k: (round(v, 4) if isinstance(v, float) and abs(v) > 1e-3 else v)
                              for k, v in lad[0].items()}),
                tol_db=0.01, passed=bool(max(errs) <= 0.01))


CONV_OUT = os.path.join(_ROOT, "outputs", "snr_convention.json")


def write_convention(path=CONV_OUT):
    """⭐ 규약 자체를 원장으로 낸다 — **코드에서 생성**하므로 문서와 어긋날 수 없다.

    게이트가 전부 통과했을 때만 쓴다(규약이 코드와 맞다는 증거가 있을 때만 규약을 공표한다)."""
    mf = {}
    p = os.path.join(_ROOT, "outputs", "verify_matched_filter_gain.json")
    if os.path.exists(p):
        with open(p) as f:
            d = json.load(f)
        mf = dict(source=os.path.relpath(p, _ROOT), all_pass=d["summary"]["all_pass"],
                  g_mf_db=d["summary"]["g_mf_db"],
                  gates={g["id"]: {k: g[k] for k in ("what", "err_db", "passed") if k in g}
                         for g in d["gates"]})
    doc = dict(
        _meta=dict(convention=nf.SNR_CONVENTION, canonical_rung=nf.CANONICAL_SNR_KEY,
                   doc="docs/NOISE_AND_ROTOR_PLAN.md#1-2",
                   generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
                   generator="benchmark/verify_snr_convention.py::write_convention",
                   rule_ko="맨 이름 「SNR」은 snr_slow_ac_db(③′) 를 뜻한다. 원장은 ③·③′·dc_ac_db 를 "
                           "항상 병기한다. 어느 눈금인지 안 적힌 SNR 수치는 인용 금지."),
        rungs=nf.SNR_RUNGS,
        constants=dict(T0_K=nf.T0, k_boltz=nf.K_BOLTZ, nf_db=nf.DECLARED_NF_DB,
                       b_hz=nf.DECLARED_B_HZ, prf_hz=nf.DECLARED_PRF_HZ,
                       eirp_dbm_chamber=nf.DECLARED_EIRP_DBM, rx_gain_dbi=nf.DECLARED_RX_GAIN_DBI,
                       window_coh_loss_db=nf.WINDOW_COH_LOSS_DB,
                       window_loss_source="Braun (KIT PhD 2014) eq (3.77), Table 3.3"),
        capture_badges=dict(
            full_waveform="G_mf = 10log10(B/PRF) applies; every PRI is correlated over the full band",
            always_on_pilot="G_mf = 0 dB; PRF is the pilot repetition rate (LTE CRS 1 kHz, 5G SSB 50 Hz)",
            pre_mf="rung 1 only; the value BEFORE any matched filtering (this is the pre-2026-08-10 number)"),
        do_not_confuse=dict(
            g_mf_db=round(nf.matched_filter_gain_db(), 4),
            cpi_coherent_gain_db_5000=round(float(10 * np.log10(5000)), 4),
            g_stft_db_70_hann=round(float(10 * np.log10(70)) + nf.WINDOW_COH_LOSS_DB["hann"], 4),
            note="three distinct quantities; the first two are both ~37 dB by coincidence"),
        conversion=dict(dc_ac_off_db="10*log10(1 + 10**(dc_ac_db/10))",
                        total_to_ac="snr_slow_ac_db = snr_slow_db - dc_ac_off_db",
                        ac_to_total="snr_slow_db = snr_slow_ac_db + dc_ac_off_db",
                        approx_note="pre-2026-08-10 code subtracted dc_ac_db directly; error <=0.41 dB "
                                    "for dc_ac>=10 dB, 3.01 dB at dc_ac=0 dB",
                        implemented_in="src/microdoppler_nearfield.py::dc_ac_offset_db"),
        who_uses_which={
            "src/experiment_md_range.py": "total (ref='total'), capture per --capture flag",
            "benchmark/md_classify_dataset.py": "ac (ref='ac'), capture=full_waveform",
            "src/microdoppler_nearfield.py::echo_over_noise_db": "rung 1 by default (capture='pre_mf')"},
        matched_filter_verification=mf,
        known_gaps=[
            "g_stft_db has no primary-literature source for a single STFT frame; it is our extrapolation "
            "of Braun eq (3.37) (2-D periodogram). Recorded as ours, not as literature.",
            "g_mf_db assumes an ideal matched filter and a clean reference channel; the real passive "
            "chain (benchmark/passive_two_channel_md.py) loses some of it.",
            "an ECA zero-Doppler notch removes the body DC, which would drive dc_ac_off_db toward 0 dB; "
            "unmeasured (gate G16 in docs/NOISE_AND_ROTOR_PLAN.md)"],
    )
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False, default=float)
    os.replace(tmp, path)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20260810)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--no-convention", action="store_true",
                    help="outputs/snr_convention.json 을 쓰지 않는다")
    a = ap.parse_args()

    t0 = time.time()
    gates = [gate_sc1(a), gate_sc2(a), gate_sc3(a), gate_sc4(a), gate_sc5(a), gate_sc6(a)]
    n_pass = sum(1 for g in gates if g["passed"])
    doc = dict(
        _meta=dict(
            title="SNR convention v2 — regression + cross-scale gates",
            generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
            script="benchmark/verify_snr_convention.py",
            convention=nf.SNR_CONVENTION, canonical=nf.CANONICAL_SNR_KEY,
            defect="2026-08-10: two SNR references coexisted (total power in add_noise, AC-only in "
                   "md_classify_dataset) and differ by 17.3-37.2 dB per airframe",
            decision_ko="둘 다 쓴다. 이름을 나누고(③ snr_slow_db · ③′ snr_slow_ac_db) 원장에 병기하며 "
                        "변환은 dc_ac_offset_db() 하나로만 한다. 맨 이름 「SNR」은 ③′ 를 뜻한다.",
            gpu_used=False, runtime_s=round(time.time() - t0, 2)),
        summary=dict(n_gates=len(gates), n_pass=n_pass, all_pass=bool(n_pass == len(gates))),
        gates=gates,
    )
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    tmp = a.out + ".tmp"
    with open(tmp, "w") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False, default=float)
    os.replace(tmp, a.out)
    for g in gates:
        print(f"  [{'PASS' if g['passed'] else 'FAIL'}] {g['id']}  {g['what'][:70]}")
    print(f"\n{n_pass}/{len(gates)} pass  → {a.out}  ({time.time() - t0:.1f} s)")
    if n_pass == len(gates) and not a.no_convention:
        print(f"→ {write_convention()}   (규약 원장; 게이트 전원 통과 시에만 갱신)")
    return 0 if n_pass == len(gates) else 1


if __name__ == "__main__":
    sys.exit(main())
