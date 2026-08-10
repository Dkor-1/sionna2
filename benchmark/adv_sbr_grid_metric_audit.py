# -*- coding: utf-8 -*-
"""적대적 감사 — «대역밖 비율» 지표가 얼린 팔에 유리하게 정의됐나.

기존 실험(benchmark/sbr_grid_convergence_md.py)의 결론:
  "대역밖 바닥의 지배 원인은 이산화가 아니라 자세마다 격자를 재정의하는 것.
   얼리면 9.3 dB 내려가고 d² 로 수렴한다."

이 파일은 **깨뜨리려고** 쓴다. GPU 재계산 없이 저장된 슬로타임 계열
(outputs/sbr_grid_convergence.npz + outputs/archive/sbr_grid_conv_parts/*.npz)만으로
지표를 다시 정의해 본다. 원장은 건드리지 않고 새 이름으로 남긴다.
"""
from __future__ import annotations
import glob, json, os, sys
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, os.path.join(_ROOT, "src"))
sys.path.insert(0, _HERE)

J = json.load(open(os.path.join(_ROOT, "outputs", "sbr_grid_convergence.json")))
M = J["_meta"]
PRF = float(M["prf_hz"]); FTIP = float(M["f_tip_hz"]); FFL = float(M["f_flash_hz"])
Z = np.load(os.path.join(_ROOT, "outputs", "sbr_grid_convergence.npz"))
DIVS = M["divs"]


def spectrum(E, prf, pad=4):
    E = np.asarray(E, complex)
    w = np.hanning(len(E))
    nf = int(pad * len(E))
    S = np.fft.fftshift(np.abs(np.fft.fft(E * w, nf)))
    f = np.fft.fftshift(np.fft.fftfreq(nf, 1.0 / prf))
    return f, S


def envelope(f, S, smooth_hz):
    P = np.asarray(S, float) ** 2
    df = float(f[1] - f[0])
    n = max(3, int(round(smooth_hz / df)) | 1)
    return np.convolve(P, np.ones(n) / n, mode="same")


def parts(E, prf=PRF, ftip=FTIP, ffl=FFL, hann=True, pad=4):
    """원장과 **같은 추정기**로 스펙트럼을 낸 뒤 절대 전력 조각을 그대로 돌려준다."""
    E = np.asarray(E, complex)
    if hann:
        f, S = spectrum(E, prf, pad)
    else:
        nf = int(pad * len(E))
        S = np.fft.fftshift(np.abs(np.fft.fft(E, nf)))
        f = np.fft.fftshift(np.fft.fftfreq(nf, 1.0 / prf))
    P = envelope(f, S, 4.0 * ffl)
    fb = 0.15 * ftip
    blade = np.abs(f) > fb
    out = np.abs(f) > ftip
    inb = np.abs(f) <= ftip                     # DC/몸통 + 블레이드 본대역
    mid = blade & inb                            # 순수 블레이드 본대역
    dc = np.abs(f) <= fb
    # ⭐절대 전력은 계열 길이/윈도우로 나눠 스케일을 통일한다(팔·div 간 비교 가능)
    norm = len(E) ** 2
    return dict(
        P_out=float(P[out].sum()) / norm,
        P_blade=float(P[blade].sum()) / norm,
        P_mid=float(P[mid].sum()) / norm,
        P_dc=float(P[dc].sum()) / norm,
        P_tot=float(P.sum()) / norm,
        mean_pow=float(np.mean(np.abs(E) ** 2)),
        frac_paper=float(P[out].sum() / P[blade].sum()),
        frac_of_total=float(P[out].sum() / P.sum()),
        frac_of_mid=float(P[out].sum() / P[mid].sum()),
        frac_of_dc=float(P[out].sum() / P[dc].sum()),
    )


def loglog_slope(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    m = (x > 0) & (y > 0)
    A = np.stack([np.log(x[m]), np.ones(m.sum())], 1)
    coef, *_ = np.linalg.lstsq(A, np.log(y[m]), rcond=None)
    pred = A @ coef
    ss = float(np.sum((np.log(y[m]) - np.log(y[m]).mean()) ** 2))
    r2 = float(1 - np.sum((np.log(y[m]) - pred) ** 2) / ss) if ss > 0 else float("nan")
    return float(coef[0]), r2


def db(a, b):
    return float(10 * np.log10(a / b))


# ───────────────────────────────────────────────────────────── 1. 절대 전력 감사
rows = []
for dv in DIVS:
    r = {"div": dv}
    for arm in ("prod", "phase", "froz"):
        p = parts(Z[f"E_{arm}_div{dv}"])
        for k, v in p.items():
            r[f"{arm}_{k}"] = v
    rows.append(r)

audit_abs = []
for r in rows:
    audit_abs.append(dict(
        div=r["div"],
        # 논문 지표(비율)의 이득
        gain_ratio_db=db(r["prod_frac_paper"], r["froz_frac_paper"]),
        # ⭐분자 절대 전력의 이득 — 비율이 아니라 대역밖 전력 그 자체
        gain_abs_Pout_db=db(r["prod_P_out"], r["froz_P_out"]),
        # 분모가 어떻게 움직였나
        d_Pblade_db=db(r["froz_P_blade"], r["prod_P_blade"]),
        d_Pmid_db=db(r["froz_P_mid"], r["prod_P_mid"]),
        d_Pdc_db=db(r["froz_P_dc"], r["prod_P_dc"]),
        d_Ptot_db=db(r["froz_P_tot"], r["prod_P_tot"]),
        d_meanpow_db=db(r["froz_mean_pow"], r["prod_mean_pow"]),
        # 분모 바꿔치기
        gain_frac_of_total_db=db(r["prod_frac_of_total"], r["froz_frac_of_total"]),
        gain_frac_of_dc_db=db(r["prod_frac_of_dc"], r["froz_frac_of_dc"]),
        prod_frac=r["prod_frac_paper"], froz_frac=r["froz_frac_paper"],
        prod_P_out=r["prod_P_out"], froz_P_out=r["froz_P_out"],
    ))

# ───────────────────────────────────── 2. 절대 전력으로도 d² 로 수렴하나
conv_abs = {}
for arm in ("prod", "phase", "froz"):
    for key in ("P_out", "frac_paper", "frac_of_total", "frac_of_dc", "P_blade", "P_mid"):
        y = [r[f"{arm}_{key}"] for r in rows]
        s, r2 = loglog_slope(DIVS, y)
        s12, r212 = loglog_slope([d for d in DIVS if d >= 12],
                                 [v for d, v in zip(DIVS, y) if d >= 12])
        conv_abs[f"{arm}_{key}"] = dict(values=y, slope=s, r2=r2, slope_ge12=s12, r2_ge12=r212)

# ─────────────────────────────── 3. 5점 회귀 과적합 — leave-one-out / 부분집합
def loo(arm, key):
    y = np.array([r[f"{arm}_{key}"] for r in rows])
    x = np.array(DIVS, float)
    out = []
    for i in range(len(x)):
        m = np.ones(len(x), bool); m[i] = False
        s, r2 = loglog_slope(x[m], y[m])
        out.append(dict(dropped_div=int(x[i]), slope=s, r2=r2))
    # 인접 두 점 기울기(회귀 없이) — 가장 정직한 국소 기울기
    local = [dict(pair=[int(x[i]), int(x[i + 1])],
                  slope=float(np.log(y[i + 1] / y[i]) / np.log(x[i + 1] / x[i])))
             for i in range(len(x) - 1)]
    return dict(loo=out, local_slopes=local,
                loo_slope_min=float(min(o["slope"] for o in out)),
                loo_slope_max=float(max(o["slope"] for o in out)),
                local_slope_min=float(min(l["slope"] for l in local)),
                local_slope_max=float(max(l["slope"] for l in local)))

overfit = {f"{a}_{k}": loo(a, k) for a in ("prod", "froz")
           for k in ("frac_paper", "P_out")}

# ──────────────────────────── 4. 얼린 팔이 표적을 놓쳤나 (히트 수·격자 크기)
hits = []
for p in sorted(glob.glob(os.path.join(_ROOT, "outputs", "archive",
                                       "sbr_grid_conv_parts", "div*.npz"))):
    z = np.load(p)
    dv = int(z["div"][0]); d = float(z["d"][0])
    n0 = int(np.ceil(2 * float(z["Rout0"][0]) / d))
    lp = z["n_lit_prod"].astype(float); lf = z["n_lit_froz"].astype(float)
    hits.append(dict(
        div=dv, n0_frozen=n0,
        n_prod_min=int(z["n_grid"].min()), n_prod_max=int(z["n_grid"].max()),
        rays_frozen=n0 ** 2, rays_prod_mean=float((z["n_grid"].astype(float) ** 2).mean()),
        ray_ratio_froz_over_prod=float(n0 ** 2 / (z["n_grid"].astype(float) ** 2).mean()),
        n_lit_prod_mean=float(lp.mean()), n_lit_froz_mean=float(lf.mean()),
        lit_ratio_froz_over_prod=float(lf.mean() / lp.mean()),
        lit_ratio_db=db(lf.mean(), lp.mean()),
        n_lit_prod_cv=float(lp.std() / lp.mean()),
        n_lit_froz_cv=float(lf.std() / lf.mean()),
        # ⭐히트 수의 슬로타임 변동 = 표본 켜짐/꺼짐 잡음의 직접 대리지표
        n_lit_prod_ptp=int(lp.max() - lp.min()), n_lit_froz_ptp=int(lf.max() - lf.min()),
    ))

# ───────────────── 5. 얼린 격자가 물리를 놓치는 자세가 있나 — bbox 커버리지
cover = None
try:
    from articulated_fast import FastPoser, rotor_phases
    from drones import DRONES
    fp = FastPoser(DRONES[M["drone"]])
    NT = int(M["n"])
    tt = np.arange(NT) / PRF
    ph = rotor_phases(tt, np.asarray(M["rpm_per_rotor"], float), fp.dirs)
    a, e = np.radians(M["az_deg"]), np.radians(M["el_deg"])
    u = np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])
    tmp = np.array([0.0, 0.0, 1.0]) if abs(u[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    e1 = np.cross(u, tmp); e1 /= np.linalg.norm(e1)
    e2 = np.cross(u, e1)
    lo = np.full(3, np.inf); hi = np.full(3, -np.inf)
    Cs = np.zeros((NT, 3)); Rp = np.zeros(NT)
    T1 = np.zeros(NT); T2 = np.zeros(NT)      # 자세별 횡단 반경 (e1,e2 평면)
    for i in range(NT):
        V = np.asarray(fp.pose(ph[i]).v, float)
        lo = np.minimum(lo, V.min(0)); hi = np.maximum(hi, V.max(0))
        c = 0.5 * (V.max(0) + V.min(0)); Cs[i] = c
        Rp[i] = float(np.linalg.norm(V - c, axis=1).max())
    ctr0 = 0.5 * (lo + hi)
    Rmax = 0.0
    for i in range(NT):
        V = np.asarray(fp.pose(ph[i]).v, float)
        Rmax = max(Rmax, float(np.linalg.norm(V - ctr0, axis=1).max()))
        T1[i] = np.abs((V - ctr0) @ e1).max()
        T2[i] = np.abs((V - ctr0) @ e2).max()
    cover = dict(
        note=("얼린 격자 반경 Rout0 = Rmax·1.15+3d. 자세별 표적의 **횡단 최대 반경**(e1,e2)이 "
              "Rout0 를 넘으면 그 자세에서 표적 일부가 격자 밖으로 나가 잘린다."),
        Rmax_global_m=float(Rmax),
        transverse_max_e1_m=float(T1.max()), transverse_max_e2_m=float(T2.max()),
        per_div=[dict(div=dv,
                      Rout0_m=float(Rmax * 1.15 + 3 * (299792458.0 / M["fc_hz"]) / dv),
                      margin_over_transverse_m=float(
                          Rmax * 1.15 + 3 * (299792458.0 / M["fc_hz"]) / dv
                          - max(T1.max(), T2.max())),
                      clipped=bool(Rmax * 1.15 + 3 * (299792458.0 / M["fc_hz"]) / dv
                                   < max(T1.max(), T2.max())))
                 for dv in DIVS],
        prod_transverse_margin_note=("생산 팔은 자세별 R=max|V-c|·1.15+3d 이므로 항상 덮는다. "
                                     "얼린 팔은 전역 Rmax 를 쓰므로 생산보다 **크다**."))
except Exception as ex:      # 메쉬 로딩 실패해도 나머지는 낸다
    cover = dict(error=repr(ex))

# ───────────────── 6. 추정기 자체 흔들기 — Hann 없이 / 평활 없이 / 다른 f_body
robust = []
for dv in DIVS:
    e_p = Z[f"E_prod_div{dv}"]; e_f = Z[f"E_froz_div{dv}"]
    row = {"div": dv}
    row["gain_hann_db"] = db(parts(e_p)["frac_paper"], parts(e_f)["frac_paper"])
    row["gain_nohann_db"] = db(parts(e_p, hann=False)["frac_paper"],
                               parts(e_f, hann=False)["frac_paper"])
    # 평활 없이 (raw periodogram 합)
    def raw(E):
        f, S = spectrum(E, PRF)
        P = S ** 2
        blade = np.abs(f) > 0.15 * FTIP
        out = np.abs(f) > FTIP
        return float(P[out].sum() / P[blade].sum()), float(P[out].sum() / len(E) ** 2)
    fp_, ap_ = raw(e_p); ff_, af_ = raw(e_f)
    row["gain_nosmooth_ratio_db"] = db(fp_, ff_)
    row["gain_nosmooth_abs_db"] = db(ap_, af_)
    # f_body 를 바꾼다 (0.15 → 0.05 / 0.30 / 0.50 f_tip)
    for fb in (0.05, 0.30, 0.50):
        def frac_fb(E, fb=fb):
            f, S = spectrum(E, PRF)
            P = envelope(f, S, 4.0 * FFL)
            bl = np.abs(f) > fb * FTIP
            ou = np.abs(f) > FTIP
            return float(P[ou].sum() / P[bl].sum())
        row[f"gain_fbody{fb}_db"] = db(frac_fb(e_p), frac_fb(e_f))
    # 대역밖 경계를 바꾼다 (f_tip → 1.5·2·3 f_tip) — 절대 전력으로
    for mfac in (1.5, 2.0, 3.0):
        def pout(E, mf=mfac):
            f, S = spectrum(E, PRF)
            P = envelope(f, S, 4.0 * FFL)
            return float(P[np.abs(f) > mf * FTIP].sum()) / len(E) ** 2
        row[f"gain_abs_beyond{mfac}ftip_db"] = db(pout(e_p), pout(e_f))
    robust.append(row)

# ───────────────── 7. 얼린 팔의 오차가 «사라졌나» 아니면 «DC 로 옮겨갔나»
#   같은 div 의 prod(위상보정판)·froz 를 더 촘촘한 격자(div32)의 froz 와 견준다.
ref = Z["E_froz_div32"]
def lp(E, fcut=FTIP):
    X = np.fft.fft(np.asarray(E, complex))
    fr = np.fft.fftfreq(len(X), 1.0 / PRF)
    X[np.abs(fr) > fcut] = 0
    return np.fft.ifft(X)

def nrmse(a, b):
    a = np.asarray(a, complex); b = np.asarray(b, complex)
    return float(np.linalg.norm(a - b) / np.linalg.norm(b))

acc = []
for dv in DIVS:
    ep = Z[f"E_phase_div{dv}"]; ef = Z[f"E_froz_div{dv}"]
    acc.append(dict(
        div=dv,
        # 본대역(|f|<=f_tip) 파형이 촘촘한 기준과 얼마나 다른가
        nrmse_phase_vs_ref_inband=nrmse(lp(ep), lp(ref)),
        nrmse_froz_vs_ref_inband=nrmse(lp(ef), lp(ref)),
        # 전대역
        nrmse_phase_vs_ref_full=nrmse(ep, ref),
        nrmse_froz_vs_ref_full=nrmse(ef, ref),
        # ⭐평균 레벨 편향 (DC 로 옮겨간 오차)
        mean_abs_phase=float(np.mean(np.abs(ep))),
        mean_abs_froz=float(np.mean(np.abs(ef))),
        mean_abs_ref=float(np.mean(np.abs(ref))),
        bias_phase_db=db(np.mean(np.abs(ep) ** 2), np.mean(np.abs(ref) ** 2)),
        bias_froz_db=db(np.mean(np.abs(ef) ** 2), np.mean(np.abs(ref) ** 2)),
    ))

OUT = os.path.join(_ROOT, "outputs", "adv_sbr_grid_metric_audit.json")
json.dump(dict(
    _meta=dict(purpose=("적대적 반증 — «대역밖 비율» 지표가 얼린 팔에 유리하게 정의됐는지. "
                        "GPU 재계산 없이 저장 계열만 재측정."),
               source_ledger="outputs/sbr_grid_convergence.json (수정하지 않음)",
               series="outputs/sbr_grid_convergence.npz",
               inherits=dict(prf_hz=PRF, f_tip_hz=FTIP, f_flash_hz=FFL, divs=DIVS)),
    absolute_power_audit=audit_abs,
    convergence_alt_metrics=conv_abs,
    overfit_check=overfit,
    frozen_hit_audit=hits,
    frozen_coverage=cover,
    estimator_robustness=robust,
    accuracy_vs_finer_reference=acc,
), open(OUT, "w"), ensure_ascii=False, indent=1)
print("→", OUT)

# ── 화면 요약 ────────────────────────────────────────────────────────────
print("\n[1] 비율 이득 vs 절대 대역밖 전력 이득 (prod → froz)")
print(f"{'div':>4} {'ratio dB':>9} {'abs P_out dB':>13} {'ΔP_blade dB':>12} "
      f"{'ΔP_mid dB':>10} {'ΔP_dc dB':>10} {'Δmean|E|² dB':>13}")
for a in audit_abs:
    print(f"{a['div']:>4} {a['gain_ratio_db']:>9.2f} {a['gain_abs_Pout_db']:>13.2f} "
          f"{a['d_Pblade_db']:>12.2f} {a['d_Pmid_db']:>10.2f} {a['d_Pdc_db']:>10.2f} "
          f"{a['d_meanpow_db']:>13.2f}")

print("\n[2] 절대 대역밖 전력의 수렴 기울기")
for k in ("prod_P_out", "phase_P_out", "froz_P_out"):
    c = conv_abs[k]
    print(f"  {k:>12}  slope {c['slope']:+.3f} (R² {c['r2']:.3f})   "
          f"≥12 구간 {c['slope_ge12']:+.3f} (R² {c['r2_ge12']:.3f})")

print("\n[3] 과적합 — leave-one-out / 인접쌍 국소 기울기")
for k, v in overfit.items():
    print(f"  {k:>18}  LOO [{v['loo_slope_min']:+.2f}, {v['loo_slope_max']:+.2f}]  "
          f"local [{v['local_slope_min']:+.2f}, {v['local_slope_max']:+.2f}]")

print("\n[4] 얼린 팔이 표적을 놓쳤나")
print(f"{'div':>4} {'n0':>5} {'n_prod':>12} {'rays x':>7} {'lit froz/prod':>14} "
      f"{'lit dB':>7} {'lit CV prod':>11} {'lit CV froz':>11}")
for h in hits:
    print(f"{h['div']:>4} {h['n0_frozen']:>5} {h['n_prod_min']:>4}-{h['n_prod_max']:<7} "
          f"{h['ray_ratio_froz_over_prod']:>7.2f} {h['lit_ratio_froz_over_prod']:>14.4f} "
          f"{h['lit_ratio_db']:>7.3f} {h['n_lit_prod_cv']:>11.4f} {h['n_lit_froz_cv']:>11.4f}")

print("\n[5] 얼린 격자 커버리지")
if "error" in (cover or {}):
    print("  ", cover["error"])
else:
    for c in cover["per_div"]:
        print(f"  div {c['div']:>3}  Rout0 {c['Rout0_m']:.4f} m  여유 "
              f"{c['margin_over_transverse_m']*1e3:+.1f} mm  잘림={c['clipped']}")

print("\n[6] 추정기 흔들기 — 이득[dB] 이 정의에 얼마나 의존하나")
hdr = [k for k in robust[0] if k != "div"]
print("  div  " + "  ".join(f"{h[5:]:>18}" for h in hdr))
for r in robust:
    print(f"  {r['div']:>3}  " + "  ".join(f"{r[h]:>18.2f}" for h in hdr))

print("\n[7] 더 촘촘한 기준(froz div32) 대비 정확도")
print(f"{'div':>4} {'phase inband':>13} {'froz inband':>12} {'phase full':>11} "
      f"{'froz full':>10} {'bias phase dB':>14} {'bias froz dB':>13}")
for a in acc:
    print(f"{a['div']:>4} {a['nrmse_phase_vs_ref_inband']:>13.4f} "
          f"{a['nrmse_froz_vs_ref_inband']:>12.4f} {a['nrmse_phase_vs_ref_full']:>11.4f} "
          f"{a['nrmse_froz_vs_ref_full']:>10.4f} {a['bias_phase_db']:>14.3f} "
          f"{a['bias_froz_db']:>13.3f}")
