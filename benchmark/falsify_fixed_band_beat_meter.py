# -*- coding: utf-8 -*-
"""falsify_fixed_band_beat_meter.py — 반증: «fixed 대역 beat_hz 는 창 누설을 재는 잣대다».

CPU 전용. GPU 안 씀. 기존 원장 안 덮음. 새 파일 outputs/falsify_fixed_band_beat_meter.json.

핵심 반례 설계
  (1) 변조율을 f_flash 가 **아닌** 값으로 바꾼 순수 AM 을 넣는다.
      «누설 잣대» 라면 출력이 입력 변조율과 무관해야 한다.
  (2) 변조가 아예 없는데 대역 안에 **진짜** 에너지만 있는 신호를 넣는다.
  (3) g(t) 의 변조 깊이(std/mean)를 같이 잰다 — 원장이 버린 유의성.
  (4) 실측 el−90 신호를 대역통과만 남겨(진짜 대역 내용물만) 다시 잰다.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from md_mapstyle import auto_periods, flash_spec  # noqa: E402

TJ = json.load(open(f"{ROOT}/outputs/report07_three_engines.json"))["_meta"]
PRF = float(TJ["prf_hz"])
FFL = float(TJ["f_flash_hz"])
FT_DECK = float(TJ["f_tip_hz"])
N = int(TJ["n"])
PER = auto_periods(PRF, FFL)
NPER = int(round(PER * (PRF / FFL)))
LO, HI = 0.35 * FT_DECK, FT_DECK


def band_metrics(E, lo, hi):
    """verify_nadir_flash.band_metrics 의 복제 + g(t) 변조깊이·정규화전 봉우리비 추가."""
    f, t, S, _ = flash_spec(np.asarray(E, complex), PRF, FFL, PER)
    b = (np.abs(f) >= lo) & (np.abs(f) <= hi)
    if b.sum() < 2:
        return dict(n_bins=int(b.sum()), beat_hz=None, band_power_db=None)
    g = (S[b, :] ** 2).sum(axis=0)
    pw = 10 * np.log10(g.mean())
    gm = float(g.mean())
    depth = float(g.std() / (abs(gm) + 1e-300))       # ⭐원장이 버린 유의성
    g = g - g.mean()
    dt = float(t[1] - t[0]); m = len(g)
    A = np.abs(np.fft.rfft(g * np.hanning(m), n=64 * m))
    fr = np.fft.rfftfreq(64 * m, dt)
    if A.max() <= 0:
        return dict(n_bins=int(b.sum()), beat_hz=None, band_power_db=round(pw, 2))
    Amax_abs = float(A.max())
    A = A / A.max()
    sel = (fr >= 40) & (fr <= 400)
    i0 = int(np.where(sel)[0][0]); i = int(np.argmax(A[sel])) + i0
    y0, y1, y2 = A[i - 1], A[i], A[i + 1]
    den = y0 - 2 * y1 + y2
    pk = fr[i] + (0.5 * (y0 - y2) / den if den else 0.0) * (fr[1] - fr[0])
    # 봉우리가 40~400 밖의 전역 최대에 견줘 얼마나 되나 (argmax 가 강제된 것인지)
    peak_in_window_over_global_db = round(float(20 * np.log10(A[sel].max() / A.max())), 2)
    return dict(n_bins=int(b.sum()), beat_hz=round(float(pk), 2),
                band_power_db=round(pw, 2),
                g_modulation_depth=float(f"{depth:.3e}"),
                g_modulation_depth_db=round(float(20 * np.log10(depth + 1e-300)), 1),
                peak_in_window_over_global_db=peak_in_window_over_global_db,
                envelope_peak_abs=float(f"{Amax_abs:.4e}"))


def true_in_band_db(v):
    fr = np.fft.fftshift(np.fft.fftfreq(N, 1 / PRF))
    w = np.hanning(N)
    inb = (np.abs(fr) >= LO) & (np.abs(fr) <= HI)
    P = np.abs(np.fft.fftshift(np.fft.fft(np.asarray(v, complex) * w))) ** 2
    return round(float(10 * np.log10(P[inb].sum() / P.sum())), 1)


def main():
    t = np.arange(N) / PRF
    out = {"_meta": {
        "generator": "benchmark/falsify_fixed_band_beat_meter.py",
        "claim_under_test_ko": "«fixed 대역 beat_hz 는 도플러가 아니라 창 누설을 재는 잣대다 — "
                              "대역 안 에너지가 원리적으로 0 인 신호에도 126.67 Hz 를 낸다»",
        "no_gpu_ko": "GPU 안 씀 · numpy/scipy CPU · 기존 원장 안 덮음",
        "prf_hz": PRF, "f_flash_hz": FFL, "n": N, "nperseg": NPER,
        "bin_hz": round(PRF / NPER, 1), "band_lo_hz": round(LO, 1), "band_hi_hz": round(HI, 1),
    }}

    # ── 반례 1: 변조율을 바꾼다. 누설 잣대라면 출력이 안 변해야 한다 ──────────
    r1 = {}
    for fm in (60.0, 90.0, 126.66666666666667, 180.0, 200.0, 253.33333333333334, 300.0, 350.0):
        v = (1 + 0.3 * np.cos(2 * np.pi * fm * t)).astype(complex)
        m = band_metrics(v, LO, HI)
        r1[f"pure AM at {fm:.2f} Hz, depth 0.3"] = dict(
            input_modulation_hz=round(fm, 2), reported_beat_hz=m["beat_hz"],
            error_hz=round(m["beat_hz"] - fm, 2) if m["beat_hz"] else None,
            reported_band_power_db=m["band_power_db"],
            true_energy_in_band_db=true_in_band_db(v),
            g_modulation_depth=m["g_modulation_depth"])
    out["R1_change_the_modulation_rate"] = {
        "why_ko": "대역 안 참에너지는 여덟 판 모두 −110 dB 언저리(사실상 0)다. 그런데 "
                  "reported_beat_hz 는 **입력 변조율을 그대로 따라간다**.",
        "rows": r1}

    # ── 반례 2: 변조 없이 대역 안에 진짜 에너지만 ────────────────────────────
    r2 = {}
    cases = {
        "constant (no modulation at all)": np.ones(N, complex),
        "constant + real 900 Hz line, NO flash AM": (1 + 0.2 * np.exp(2j * np.pi * 900 * t)).astype(complex),
        "constant + real +-900 Hz pair, NO flash AM": (1 + 0.1 * np.exp(2j * np.pi * 900 * t)
                                                       + 0.1 * np.exp(-2j * np.pi * 900 * t)).astype(complex),
        "white noise only (seed 0)": None,
    }
    rng = np.random.default_rng(0)
    cases["white noise only (seed 0)"] = (rng.standard_normal(N) + 1j * rng.standard_normal(N))
    for k, v in cases.items():
        m = band_metrics(v, LO, HI)
        r2[k] = dict(reported_beat_hz=m["beat_hz"], reported_band_power_db=m["band_power_db"],
                     true_energy_in_band_db=true_in_band_db(v),
                     g_modulation_depth=m["g_modulation_depth"],
                     g_modulation_depth_db=m["g_modulation_depth_db"])
    out["R2_no_modulation_cases"] = {
        "why_ko": "변조가 없으면 g(t) 가 평평해 argmax 가 잡음을 집는다 — 그 결과는 "
                  "126.67 이 **아니다**. 즉 잣대는 «126.67 을 만들어 내는» 기계가 아니다.",
        "rows": r2}

    # ── 반례 3: 실측 신호 — 대역통과만 남긴 것 대 저역통과만 남긴 것 ──────────
    z = np.load(f"{ROOT}/outputs/elevation_sweep_md.npz")
    keys = [k for k in z.files if "/" in k]
    fq = np.fft.fftfreq(N, 1 / PRF)
    inb_f = (np.abs(fq) >= LO) & (np.abs(fq) <= HI)
    r3 = {}
    for key in sorted(keys):
        E = np.asarray(z[key], complex)
        if E.size != N:
            continue
        F = np.fft.fft(E)
        F_bp = np.where(inb_f, F, 0)                       # 진짜 대역 내용물만
        F_lp = F.copy(); F_lp[np.abs(fq) > 300.0] = 0      # 원장의 «누설만»
        F_notch = F.copy(); F_notch[inb_f] = 0             # ⭐대역만 도려낸 것
        m_all, m_bp = band_metrics(E, LO, HI), band_metrics(np.fft.ifft(F_bp), LO, HI)
        m_lp, m_no = band_metrics(np.fft.ifft(F_lp), LO, HI), band_metrics(np.fft.ifft(F_notch), LO, HI)
        r3[key] = dict(
            full_beat_hz=m_all["beat_hz"], full_band_power_db=m_all["band_power_db"],
            bandpass_only_beat_hz=m_bp["beat_hz"], bandpass_only_power_db=m_bp["band_power_db"],
            lowpass300_only_beat_hz=m_lp["beat_hz"], lowpass300_only_power_db=m_lp["band_power_db"],
            band_notched_out_beat_hz=m_no["beat_hz"], band_notched_out_power_db=m_no["band_power_db"],
            true_over_leakage_db=round(m_all["band_power_db"] - m_lp["band_power_db"], 2),
            g_depth_full=m_all["g_modulation_depth"], g_depth_bandpass=m_bp["g_modulation_depth"])
    out["R3_real_signals_split"] = {
        "why_ko": "대역만 남긴 신호(bandpass_only)가 스스로 126~127 Hz 를 내면, 그 대역 안에는 "
                  "진짜 플래시 빗살이 있다는 뜻이다 — 누설 없이도.",
        "rows": r3}

    # ── 반례 4: 원장 자신의 앙각·엔진·예산별 fixed.beat_hz 분포 ──────────────
    sw = json.load(open(f"{ROOT}/outputs/elevation_sweep_md.json"))
    vals = {}
    for r in sw["rows"]:
        fb = r["fixed"]["beat_hz"]
        vals[f"{r['engine']}/el{r['el_deg']:+.0f}"] = fb
    near = {k: v for k, v in vals.items() if v is not None and abs(v - FFL) < 6}
    far = {k: v for k, v in vals.items() if v is not None and abs(v - FFL) >= 6}
    out["R4_ledger_spread"] = {
        "why_ko": "잣대가 «항상 126.67 을 뱉는 기계» 라면 21 행이 모두 126.67 이어야 한다. "
                  "실제로는 6 행이 2×·3× 또는 전혀 다른 값이다.",
        "n_rows": len(vals), "n_near_1x": len(near), "n_not_1x": len(far),
        "not_1x_rows": far, "all_rows": vals}

    p = f"{ROOT}/outputs/falsify_fixed_band_beat_meter.json"
    json.dump(out, open(p, "w"), ensure_ascii=False, indent=1)
    print(f"✅ {p}")
    for sec in ("R1_change_the_modulation_rate", "R2_no_modulation_cases"):
        print(f"\n── {sec}")
        for k, v in out[sec]["rows"].items():
            print(f"  {k:>52} → {v}")
    print("\n── R3 (real)")
    for k, v in out["R3_real_signals_split"]["rows"].items():
        print(f"  {k:>28} full={v['full_beat_hz']} bp={v['bandpass_only_beat_hz']} "
              f"lp300={v['lowpass300_only_beat_hz']} notched={v['band_notched_out_beat_hz']} "
              f"true-leak={v['true_over_leakage_db']} dB")
    print("\n── R4", out["R4_ledger_spread"]["n_not_1x"], "/", out["R4_ledger_spread"]["n_rows"],
          "not 1x:", out["R4_ledger_spread"]["not_1x_rows"])


if __name__ == "__main__":
    main()
