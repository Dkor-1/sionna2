# -*- coding: utf-8 -*-
"""적대적 감사 2 — 추정기 해부 + 독립 수렴(코시) 검사.

1. 평활 커널이 f_body 보다 넓다: 4·f_flash = 506.7 Hz (반폭 253 Hz) > 0.15·f_tip = 184 Hz.
   → 분모(블레이드 대역)에 **몸통 DC 봉우리가 번져 들어간다**. 얼마나?
2. 팔마다 **자기 사다리 안에서** 수렴하는가 (코시 검사, 기준을 froz 로 두지 않는다).
3. 얼린 팔이 «진짜 블레이드 신호» 를 깎았나 — phase 팔(격자는 그대로, 위상원점만 고정)과 비교.
4. 비수렴 성분이 **결정론적**인가 (div 에 무관한 성분).
"""
from __future__ import annotations
import json, os, sys
import numpy as np

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
J = json.load(open(os.path.join(_ROOT, "outputs", "sbr_grid_convergence.json")))
M = J["_meta"]
PRF = float(M["prf_hz"]); FTIP = float(M["f_tip_hz"]); FFL = float(M["f_flash_hz"])
Z = np.load(os.path.join(_ROOT, "outputs", "sbr_grid_convergence.npz"))
DIVS = M["divs"]; NT = int(M["n"])


def spec(E, pad=4):
    E = np.asarray(E, complex)
    S = np.fft.fftshift(np.abs(np.fft.fft(E * np.hanning(len(E)), int(pad * len(E)))))
    f = np.fft.fftshift(np.fft.fftfreq(int(pad * len(E)), 1.0 / PRF))
    return f, S


def smooth(P, f, hz):
    df = float(f[1] - f[0]); n = max(3, int(round(hz / df)) | 1)
    return np.convolve(P, np.ones(n) / n, mode="same"), n, df


f0, _ = spec(Z["E_prod_div12"])
_, KN, DF = smooth(np.zeros_like(f0), f0, 4.0 * FFL)
KERNEL_HALF_HZ = (KN - 1) / 2 * DF
FB = 0.15 * FTIP

# ── 1. 평활이 분모에 몸통을 얼마나 흘려넣나 ─────────────────────────────────
leak = []
for dv in DIVS:
    row = {"div": dv}
    for arm in ("prod", "phase", "froz"):
        f, S = spec(Z[f"E_{arm}_div{dv}"])
        P = S ** 2
        Pdc_only = np.where(np.abs(f) <= FB, P, 0.0)       # 몸통 대역만 남긴다
        Pbl_only = np.where(np.abs(f) > FB, P, 0.0)        # 블레이드 대역만 남긴다
        Es, _, _ = smooth(P, f, 4.0 * FFL)
        Ed, _, _ = smooth(Pdc_only, f, 4.0 * FFL)
        Eb, _, _ = smooth(Pbl_only, f, 4.0 * FFL)
        bl = np.abs(f) > FB
        ou = np.abs(f) > FTIP
        tot_den = float(Es[bl].sum())
        row[f"{arm}_den_total"] = tot_den / NT ** 2
        row[f"{arm}_den_from_dc_frac"] = float(Ed[bl].sum() / tot_den)
        row[f"{arm}_den_own_frac"] = float(Eb[bl].sum() / tot_den)
        # ⭐DC 번짐을 뺀 «정직한» 분모로 다시 잰 대역밖 비율
        row[f"{arm}_frac_clean"] = float(Es[ou].sum() / Eb[bl].sum())
        row[f"{arm}_frac_paper"] = float(Es[ou].sum() / tot_den)
    row["gain_paper_db"] = 10 * np.log10(row["prod_frac_paper"] / row["froz_frac_paper"])
    row["gain_clean_db"] = 10 * np.log10(row["prod_frac_clean"] / row["froz_frac_clean"])
    leak.append(row)

# ── 1b. 평활 없이 왜 뒤집히나 ────────────────────────────────────────────────
nosm = []
for dv in DIVS:
    row = {"div": dv}
    for arm in ("prod", "froz"):
        f, S = spec(Z[f"E_{arm}_div{dv}"])
        P = S ** 2
        bl = np.abs(f) > FB; ou = np.abs(f) > FTIP
        mid = bl & (np.abs(f) <= FTIP)
        row[f"{arm}_out"] = float(P[ou].sum()) / NT ** 2
        row[f"{arm}_blade"] = float(P[bl].sum()) / NT ** 2
        row[f"{arm}_mid"] = float(P[mid].sum()) / NT ** 2
        row[f"{arm}_dc"] = float(P[np.abs(f) <= FB].sum()) / NT ** 2
    row["d_out_db"] = 10 * np.log10(row["prod_out"] / row["froz_out"])
    row["d_blade_db"] = 10 * np.log10(row["prod_blade"] / row["froz_blade"])
    row["d_mid_db"] = 10 * np.log10(row["prod_mid"] / row["froz_mid"])
    row["d_dc_db"] = 10 * np.log10(row["prod_dc"] / row["froz_dc"])
    nosm.append(row)

# ── 2. 코시 검사 — 팔마다 자기 사다리 안에서 수렴하나 (기준을 froz 로 안 둔다) ─
def lp(E, fc=FTIP):
    X = np.fft.fft(np.asarray(E, complex))
    fr = np.fft.fftfreq(len(X), 1.0 / PRF)
    X[np.abs(fr) > fc] = 0
    return np.fft.ifft(X)


def nrm(a, b):
    return float(np.linalg.norm(np.asarray(a) - np.asarray(b)) / np.linalg.norm(np.asarray(b)))


cauchy = {}
for arm in ("prod", "phase", "froz"):
    seq = []
    for i in range(len(DIVS) - 1):
        a = Z[f"E_{arm}_div{DIVS[i]}"]; b = Z[f"E_{arm}_div{DIVS[i+1]}"]
        seq.append(dict(pair=[DIVS[i], DIVS[i + 1]],
                        nrmse_full=nrm(a, b), nrmse_inband=nrm(lp(a), lp(b))))
    # 가장 촘촘한 두 판끼리
    cauchy[arm] = dict(successive=seq,
                       finest_pair_nrmse_full=seq[-1]["nrmse_full"],
                       finest_pair_nrmse_inband=seq[-1]["nrmse_inband"])

# 팔끼리 (같은 div) — 세 팔이 한 점으로 모이나
cross = []
for dv in DIVS:
    ep = Z[f"E_prod_div{dv}"]; eh = Z[f"E_phase_div{dv}"]; ef = Z[f"E_froz_div{dv}"]
    cross.append(dict(div=dv,
                      phase_vs_froz_full=nrm(eh, ef), phase_vs_froz_inband=nrm(lp(eh), lp(ef)),
                      prod_vs_froz_full=nrm(ep, ef)))

# ── 3. 얼린 팔이 진짜 블레이드 신호를 깎았나 — phase 팔이 심판 ─────────────
sig = []
for dv in DIVS:
    r = {"div": dv}
    for arm in ("prod", "phase", "froz"):
        f, S = spec(Z[f"E_{arm}_div{dv}"])
        P, _, _ = smooth(S ** 2, f, 4.0 * FFL)
        mid = (np.abs(f) > FB) & (np.abs(f) <= FTIP)
        r[f"{arm}_Pmid"] = float(P[mid].sum()) / NT ** 2
        r[f"{arm}_level_db"] = float(10 * np.log10(np.mean(np.abs(Z[f'E_{arm}_div{dv}']) ** 2)))
    r["froz_minus_phase_Pmid_db"] = 10 * np.log10(r["froz_Pmid"] / r["phase_Pmid"])
    r["prod_minus_phase_Pmid_db"] = 10 * np.log10(r["prod_Pmid"] / r["phase_Pmid"])
    r["froz_minus_phase_level_db"] = r["froz_level_db"] - r["phase_level_db"]
    sig.append(r)

lv_p = [r["prod_level_db"] for r in sig if r["div"] >= 12]
lv_f = [r["froz_level_db"] for r in sig if r["div"] >= 12]
level_stability = dict(
    note=("⭐대역밖 «비율» 지표는 스케일 불변이라 레벨(=σ) 오차를 **구조적으로 못 본다**. "
          "λ/12 이상 사다리에서 각 팔의 평균 전력이 얼마나 흔들리는가."),
    prod_level_spread_db_ge12=float(max(lv_p) - min(lv_p)),
    froz_level_spread_db_ge12=float(max(lv_f) - min(lv_f)),
    prod_levels_ge12=lv_p, froz_levels_ge12=lv_f)

# ── 4. 비수렴 성분은 결정론적인가 — div 에 무관한 스펙트럼 성분 ─────────────
det = []
f, _ = spec(Z["E_prod_div12"])
band = lambda lo, hi: (np.abs(f) >= lo * FTIP) & (np.abs(f) < hi * FTIP)
BANDS = [(1.0, 1.5), (1.5, 2.0), (2.0, 3.0), (3.0, 8.0)]
for arm in ("prod", "phase", "froz"):
    row = {"arm": arm}
    for lo, hi in BANDS:
        vals = []
        for dv in DIVS:
            _, S = spec(Z[f"E_{arm}_div{dv}"])
            P, _, _ = smooth(S ** 2, f, 4.0 * FFL)
            vals.append(float(P[band(lo, hi)].sum()) / NT ** 2)
        v12 = [v for d, v in zip(DIVS, vals) if d >= 12]
        x12 = [d for d in DIVS if d >= 12]
        A = np.stack([np.log(x12), np.ones(len(x12))], 1)
        c, *_ = np.linalg.lstsq(A, np.log(v12), rcond=None)
        row[f"{lo}-{hi}"] = dict(values=vals, slope_ge12=float(c[0]),
                                 db_drop_12_to_32=float(10 * np.log10(v12[0] / v12[-1])))
    det.append(row)

OUT = os.path.join(_ROOT, "outputs", "adv_sbr_grid_metric_audit2.json")
json.dump(dict(_meta=dict(
    purpose="추정기 해부 + 독립 코시 수렴 검사 (원장 미수정)",
    smoothing_kernel_hz=float(4.0 * FFL), smoothing_kernel_half_hz=float(KERNEL_HALF_HZ),
    f_body_hz=float(FB), f_tip_hz=FTIP,
    kernel_wider_than_fbody=bool(KERNEL_HALF_HZ > FB),
    df_hz=float(DF), kernel_bins=int(KN)),
    denominator_dc_leak=leak, no_smoothing_breakdown=nosm,
    cauchy_within_arm=cauchy, cross_arm=cross,
    signal_preserved=sig, level_blindspot=level_stability,
    deterministic_component=det),
    open(OUT, "w"), ensure_ascii=False, indent=1)
print("→", OUT)

print(f"\n[A] 평활 커널 반폭 {KERNEL_HALF_HZ:.1f} Hz  vs  f_body {FB:.1f} Hz  "
      f"→ 분모에 몸통이 번진다: {KERNEL_HALF_HZ > FB}")
print(f"{'div':>4} {'분모중 DC번짐 prod':>18} {'froz':>8} | {'논문 이득 dB':>12} {'DC번짐 뺀 이득 dB':>17}")
for r in leak:
    print(f"{r['div']:>4} {r['prod_den_from_dc_frac']*100:>17.1f}% "
          f"{r['froz_den_from_dc_frac']*100:>7.1f}% | {r['gain_paper_db']:>12.2f} "
          f"{r['gain_clean_db']:>17.2f}")

print("\n[B] 평활 없이 (raw periodogram) prod−froz [dB]")
print(f"{'div':>4} {'out':>8} {'blade':>8} {'mid':>8} {'dc':>8}")
for r in nosm:
    print(f"{r['div']:>4} {r['d_out_db']:>8.2f} {r['d_blade_db']:>8.2f} "
          f"{r['d_mid_db']:>8.2f} {r['d_dc_db']:>8.2f}")

print("\n[C] 코시 — 팔마다 자기 사다리에서 이웃 판끼리 상대오차")
for arm, c in cauchy.items():
    print(f"  {arm:>6}: " + "  ".join(f"{s['pair'][0]}→{s['pair'][1]} {s['nrmse_full']:.4f}"
                                      for s in c["successive"]))

print("\n[D] 팔끼리 (같은 div)")
for c in cross:
    print(f"  div {c['div']:>3}  phase↔froz full {c['phase_vs_froz_full']:.4f}  "
          f"inband {c['phase_vs_froz_inband']:.4f}  prod↔froz full {c['prod_vs_froz_full']:.4f}")

print("\n[E] 얼리기가 진짜 블레이드 신호를 깎았나 (심판 = phase 팔)")
print(f"{'div':>4} {'froz−phase P_mid dB':>20} {'prod−phase P_mid dB':>20} "
      f"{'froz−phase level dB':>20}")
for r in sig:
    print(f"{r['div']:>4} {r['froz_minus_phase_Pmid_db']:>20.2f} "
          f"{r['prod_minus_phase_Pmid_db']:>20.2f} {r['froz_minus_phase_level_db']:>20.2f}")
print(f"  레벨 흔들림(λ/12↑): prod {level_stability['prod_level_spread_db_ge12']:.2f} dB · "
      f"froz {level_stability['froz_level_spread_db_ge12']:.2f} dB")

print("\n[F] 대역별 수렴 기울기 (λ/12 이상)")
for row in det:
    print(f"  {row['arm']:>6}: " + "  ".join(
        f"{b} slope {row[b]['slope_ge12']:+.2f} ({row[b]['db_drop_12_to_32']:+.1f} dB)"
        for b in ("1.0-1.5", "1.5-2.0", "2.0-3.0", "3.0-8.0")))
