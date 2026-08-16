# -*- coding: utf-8 -*-
"""로터 rpm 열 하나에 대한 «같은 잣대» 통계 모음.

실측 로그든 우리 모델이 만든 열이든 **똑같은 이 함수**를 통과시킨다.
그래야 «모델이 실측을 재현하는가»가 공정한 비교가 된다.
"""
import numpy as np
from scipy import stats
from scipy.optimize import curve_fit
from scipy.signal import welch


def relparts(rpm):
    """(4,N) rpm → 정적 편차 s_k[상대], 시간 성분 eps (4,N)[상대], 기준 rpm."""
    rpm = np.asarray(rpm, float)
    mu_k = rpm.mean(axis=1)
    base = float(mu_k.mean())
    s_k = mu_k / base - 1.0
    eps = rpm / mu_k[:, None] - 1.0
    return s_k, eps, base


def ou_psd(f, sigma2, tau):
    return 4.0 * sigma2 * tau / (1.0 + (2 * np.pi * f * tau) ** 2)


def psd_shape(eps, fs, f_lo=None, f_hi=None):
    """4로터 평균 PSD 에 OU(1극)와 순수 멱법칙을 각각 맞춰 본다.

    돌려주는 것: 맞춘 코너주파수 fc(=1/2πτ), OU 적합의 log-log 잔차 rms[dB],
    멱법칙 지수 α 와 그 잔차, 그리고 «어느 쪽이 더 맞나» 판정.
    """
    n = eps.shape[1]
    nps = int(min(n, max(64, 2 ** int(np.floor(np.log2(n))))))
    f, P = welch(eps, fs=fs, axis=1, nperseg=nps, detrend="constant")
    Pm = P.mean(axis=0)
    lo = f_lo if f_lo is not None else max(2.0 * fs / nps, 0.05)
    hi = f_hi if f_hi is not None else 0.45 * fs
    m = (f >= lo) & (f <= hi) & (Pm > 0)
    if m.sum() < 6:
        return {}
    fm, pm = f[m], Pm[m]
    ldb = 10 * np.log10(pm)

    out = {"psd_band_hz": [float(lo), float(hi)], "psd_nperseg": int(nps),
           "psd_df_hz": float(fs / nps)}
    # --- OU 적합 (log 영역 최소제곱: 모양을 재는 것이지 레벨이 아니다) ---
    def f_ou(x, log_s2, tau):
        return 10 * np.log10(ou_psd(x, 10 ** log_s2, tau) + 1e-300)
    try:
        p0 = [np.log10(max(pm[0] * 1e-2, 1e-20)), 0.23]
        popt, _ = curve_fit(f_ou, fm, ldb, p0=p0, maxfev=20000,
                            bounds=([-30, 1e-3], [10, 100.0]))
        res = ldb - f_ou(fm, *popt)
        out["ou_tau_s"] = float(popt[1])
        out["ou_fc_hz"] = float(1.0 / (2 * np.pi * popt[1]))
        out["ou_fit_rms_db"] = float(np.sqrt(np.mean(res ** 2)))
    except Exception:
        pass
    # --- 순수 멱법칙 적합 S ∝ f^-alpha ---
    A = np.polyfit(np.log10(fm), ldb, 1)
    out["powerlaw_alpha"] = float(-A[0] / 10.0)          # dB/decade → 지수
    out["powerlaw_fit_rms_db"] = float(np.sqrt(np.mean((ldb - np.polyval(A, np.log10(fm))) ** 2)))
    # --- 고주파 기울기(코너 4배 위) ---
    fc = out.get("ou_fc_hz", 0.7)
    sel = (fm >= 4 * fc) & (fm <= hi)
    if sel.sum() >= 5:
        a = np.polyfit(np.log10(fm[sel]), ldb[sel], 1)
        out["hf_slope_db_per_decade"] = float(a[0])
    # --- 저주파 파워 몫 ---
    tot = float(np.trapezoid(pm, fm))
    for c in (0.5, 1.0, 2.0):
        if fm[0] < c < fm[-1]:
            s = fm <= c
            out[f"pow_frac_below_{c}Hz"] = float(np.trapezoid(pm[s], fm[s]) / tot)
    return out


def acf_stats(eps, fs, max_lag_s=5.0):
    """자기상관: 1/e 시간, 지수적합 잔차, 음의 로브(2차 동역학 신호)."""
    out = {}
    n = eps.shape[1]
    L = int(min(n // 2, max_lag_s * fs))
    if L < 8:
        return out
    accs = []
    for k in range(eps.shape[0]):
        x = eps[k] - eps[k].mean()
        c = np.correlate(x, x, mode="full")[n - 1:n - 1 + L]
        c = c / c[0]
        accs.append(c)
    c = np.mean(accs, axis=0)
    lag = np.arange(L) / fs
    below = np.where(c < np.exp(-1.0))[0]
    out["acf_tau_1e_s"] = float(lag[below[0]]) if len(below) else float("nan")
    # 지수 적합 (ACF 가 0.05 로 떨어질 때까지)
    end = np.where(c < 0.05)[0]
    e = int(end[0]) if len(end) else L
    e = max(e, 8)
    if e > 8:
        y = c[:e]
        ok = y > 1e-3
        if ok.sum() > 6:
            a = np.polyfit(lag[:e][ok], np.log(y[ok]), 1)
            out["acf_exp_tau_s"] = float(-1.0 / a[0]) if a[0] < 0 else float("nan")
            out["acf_exp_fit_rms"] = float(np.sqrt(np.mean((y - np.exp(np.polyval(a, lag[:e]))) ** 2)))
    out["acf_min"] = float(c.min())          # OU 는 음수로 안 내려간다(이론상 ≥0)
    out["acf_min_lag_s"] = float(lag[int(np.argmin(c))])
    return out


def dist_stats(eps):
    """분포 꼬리 — 로터별로 표준화한 뒤 합친다."""
    z = (eps - eps.mean(axis=1, keepdims=True)) / eps.std(axis=1, keepdims=True)
    z = z.ravel()
    out = {"excess_kurtosis": float(stats.kurtosis(z)),
           "skew": float(stats.skew(z)),
           "q99_over_sigma": float(np.percentile(np.abs(z), 99)),
           "q999_over_sigma": float(np.percentile(np.abs(z), 99.9)),
           "max_abs_z": float(np.abs(z).max())}
    try:
        out["anderson_A2"] = float(stats.anderson(z, "norm").statistic)
    except Exception:
        pass
    return out


def rotor_structure(s_k, eps):
    """로터 간 구조 — 공통 성분 몫, 쌍 대칭, 정적 편차의 모드 분해."""
    out = {}
    e = eps - eps.mean(axis=1, keepdims=True)
    c = np.corrcoef(e)
    iu = np.triu_indices(e.shape[0], 1)
    out["pair_corr_mean"] = float(np.mean(c[iu]))
    out["pair_corr_min"] = float(np.min(c[iu]))
    out["pair_corr_max"] = float(np.max(c[iu]))
    # 공통 성분 몫 = 공분산 최대 고윳값 / 합
    C = np.cov(e)
    w = np.linalg.eigvalsh(C)
    out["common_mode_share"] = float(w[-1] / w.sum())
    # «모두 같이 오르내리는» 성분의 몫 (1/2)(1,1,1,1) 방향
    u = np.ones(e.shape[0]) / np.sqrt(e.shape[0])
    out["uniform_mode_share"] = float(u @ C @ u / np.trace(C))
    # 정적 편차의 모드 분해 (쿼드 4로터일 때만)
    if len(s_k) == 4:
        v = np.asarray(s_k, float)
        v = v - v.mean()
        # PX4/DREGON 모터 번호 관례: 0,1 이 한 회전방향 · 2,3 이 반대라고 가정하지
        # 않는다. 대신 «두 개 vs 두 개» 로 나누는 3가지 분할의 대비를 전부 잰다.
        splits = {"01_vs_23": [1, 1, -1, -1], "02_vs_13": [1, -1, 1, -1],
                  "03_vs_12": [1, -1, -1, 1]}
        tot = float(np.sum(v ** 2)) + 1e-30
        for name, p in splits.items():
            p = np.asarray(p, float) / 2.0
            out[f"static_split_{name}_share"] = float((v @ p) ** 2 / tot)
        out["static_best_split_share"] = max(out[f"static_split_{k}_share"] for k in splits)
    return out


def full(rpm, fs, band=(0.3, 5.0)):
    s_k, eps, base = relparts(rpm)
    n = rpm.shape[1]
    out = {"n": int(n), "fs_hz": float(fs), "dur_s": float(n / fs),
           "base_rpm": base,
           "static_std_rel": float(np.std(s_k)),
           "static_range_rel": float(s_k.max() - s_k.min()),
           "static_dev_rel": [float(v) for v in s_k],
           "wobble_std_rel": float(eps.std()),
           "wobble_std_per_rotor": [float(v) for v in eps.std(axis=1)]}
    f_hi = min(band[1], 0.45 * fs)
    nps = int(min(n, max(64, 2 ** int(np.floor(np.log2(n))))))
    f, P = welch(eps, fs=fs, axis=1, nperseg=nps, detrend="constant")
    m = (f >= band[0]) & (f <= f_hi)
    if m.sum() > 1:
        rms = np.sqrt(np.trapezoid(P[:, m], f[m], axis=1))
        out["band_rms_rel"] = float(rms.mean())
        out["band_amp_equiv_sine_rel"] = float(rms.mean() * np.sqrt(2))
        out["band_hz"] = [float(band[0]), float(f_hi)]
    out.update(psd_shape(eps, fs))
    out.update(acf_stats(eps, fs))
    out.update(dist_stats(eps))
    out.update(rotor_structure(s_k, eps))
    return out
