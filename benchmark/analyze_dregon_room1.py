# -*- coding: utf-8 -*-
"""
analyze_dregon_room1.py — DREGON room1 (명령+실측) 재측정, 권고 ② 실행
=======================================================================
정본: prior_work/rotor_jitter_sources.md §2-3 행동 2.
규약: outputs/rotor_rpm_web_anchor.json method_note / rotor_log_traces.json
  measurement_convention 을 그대로 따른다:
  - 정적 산포 = 창 내 모터별 평균의 모터간 std / 전체평균 [%]
  - 흔들림 = 모터별 상대 신호의 0.3–5.0 Hz 대역 rms×√2 (등가 사인 진폭) [%]
  - 지배 주파수 = 그 대역 PSD 피크
  - σ_w 환산 = outputs/rotor_jitter_model.json F-공식 (OU, tau_ctl=0.22736420441699334)
⚠규약 이탈 1건(정직 기록): 호버 창 |v|<0.3 m/s 판정 불가 — 이 .mat 에는 모터 신호만
  있고 속도가 없다. 대신 «모터 정상운전 안정 구간»(램프 제외 t=8–62 s)을 창으로 쓴다.
  room1 은 자유비행이라 진성 호버가 아니다.
⚠절대 단위(rps 추정)는 미확정 — % 통계만 원장에 싣는다.
"""
import json
import numpy as np
import scipy.io as sio

RAW = '/workspace/sionna/prior_work/outputs/rotor_jitter_raw/dregon_ff_room1_motors.mat'
TAU_CTL = 0.22736420441699334
BAND = (0.3, 5.0)
FS_GRID = 1000.0          # 균일 재표집 격자 (원본 중앙 dt 0.998 ms)
T_STABLE = (8.0, 62.0)    # 안정 구간 (2-s 빈 프로파일로 선정, 램프 제외)
WIN_S = 6.0               # 원장 다른 원천과 같은 자릿수의 창 길이 (3–18 s 관례 안)


def band_fraction_F(f1, f2, T):
    return (2.0 / np.pi) * (np.arctan(2 * np.pi * f2 * T) - np.arctan(2 * np.pi * f1 * T))


def band_rms_equiv_sine_pct(rel, fs, f1, f2):
    """상대 신호(평균 1 근방) → 대역 rms×√2 [%] + 지배 주파수 [Hz] (rfft 대역 절단)"""
    x = rel - rel.mean()
    n = len(x)
    X = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(n, 1.0 / fs)
    keep = (freqs >= f1) & (freqs <= f2)
    Xb = np.where(keep, X, 0.0)
    xb = np.fft.irfft(Xb, n)
    rms = np.sqrt(np.mean(xb ** 2))
    p = np.abs(X) ** 2
    p[~keep] = 0.0
    fpk = freqs[int(np.argmax(p))] if keep.any() else np.nan
    return 100.0 * rms * np.sqrt(2.0), fpk


def main():
    d = sio.loadmat(RAW, squeeze_me=True)
    m = d['motor']
    ts = m['timestamps'].item().astype(float)
    cmd = m['command'].item().astype(float)
    mea = m['measured'].item().astype(float)
    t = ts - ts[0]

    # --- 안정 구간 + 균일 격자 재표집 (타임스탬프 불균일 dt 0.15~23.9 ms) ---
    tg = np.arange(T_STABLE[0], T_STABLE[1], 1.0 / FS_GRID)
    C = np.stack([np.interp(tg, t, cmd[:, k]) for k in range(4)], axis=1)
    M = np.stack([np.interp(tg, t, mea[:, k]) for k in range(4)], axis=1)

    out = {'file': RAW.split('/')[-1], 'fs_native_hz_median': round(1.0 / np.median(np.diff(t)), 1),
           'duration_total_s': round(float(t[-1] - t[0]), 1),
           'stable_segment_s': list(T_STABLE), 'fs_grid_hz': FS_GRID}

    F = band_fraction_F(BAND[0], BAND[1], TAU_CTL)
    out['band_hz'] = list(BAND)
    out['band_fraction_F'] = round(float(F), 4)

    # --- 전 구간(54 s) 통계 ---
    for name, X in (('measured', M), ('command', C)):
        mu = X.mean(0)                      # 로터별 평균
        g = mu.mean()                       # 전체 평균
        seg = {
            'rotor_mean_ratio': [round(float(v / g), 4) for v in mu],
            'static_spread_std_pct': round(float(100 * mu.std(ddof=0) / g), 2),
            'static_spread_range_pct': round(float(100 * (mu.max() - mu.min()) / g), 2),
            'cv_per_rotor_pct': [round(float(100 * X[:, k].std() / mu[k]), 2) for k in range(4)],
        }
        wob, fpk = [], []
        for k in range(4):
            rel = X[:, k] / mu[k]
            a, f = band_rms_equiv_sine_pct(rel, FS_GRID, *BAND)
            wob.append(round(float(a), 2)); fpk.append(round(float(f), 2))
        seg['wobble_amp_pct'] = wob
        seg['wobble_peak_hz'] = fpk
        seg['sigma_w_pct'] = [round(float(a / np.sqrt(2) / np.sqrt(F)), 2) for a in wob]
        out[name + '_full54s'] = seg

    # --- 저주파 파워 몫 (스펙트럼 모양 확인) ---
    from numpy.fft import rfft, rfftfreq
    frac = []
    for k in range(4):
        x = M[:, k] / M[:, k].mean() - 1.0
        X = rfft(x - x.mean()); f = rfftfreq(len(x), 1 / FS_GRID)
        p = np.abs(X) ** 2
        tot = p[(f >= 0.1)].sum()
        frac.append(round(float(p[(f >= 0.1) & (f < 1.0)].sum() / tot), 3))
    out['power_fraction_0p1to1hz_of_ge0p1'] = frac

    # --- 6-s 창 9개 (원장 형식 행) ---
    wins = []
    n_win = int((T_STABLE[1] - T_STABLE[0]) / WIN_S)
    for w in range(n_win):
        s = slice(int(w * WIN_S * FS_GRID), int((w + 1) * WIN_S * FS_GRID))
        Xw = M[s]
        mu = Xw.mean(0); g = mu.mean()
        wob, fpk = [], []
        for k in range(4):
            a, f = band_rms_equiv_sine_pct(Xw[:, k] / mu[k], FS_GRID, *BAND)
            wob.append(round(float(a), 3)); fpk.append(round(float(f), 2))
        # 추종오차 (창별)
        trk = [round(float(100 * (Xw[:, k] - C[s][:, k]).std() / mu[k]), 3) for k in range(4)]
        wins.append({
            't0': round(T_STABLE[0] + w * WIN_S, 1), 'dur_s': WIN_S,
            'v_mean': None, 'n_motor': 4, 'fs_hz': FS_GRID,
            'level_mean': round(float(g), 1),
            'static_dev_pct': [round(float(100 * (v - g) / g), 3) for v in mu],
            'static_std_pct': round(float(100 * mu.std(ddof=0) / g), 3),
            'static_maxabs_pct': round(float(100 * np.abs(mu - g).max() / g), 3),
            'wobble_amp_pct': wob, 'wobble_peak_hz': fpk,
            'tracking_err_std_pct': trk,
        })
    out['windows'] = wins

    def med_stats(vals):
        v = np.array(vals)
        return {'median': round(float(np.median(v)), 2), 'min': round(float(v.min()), 2),
                'max': round(float(v.max()), 2)}

    out['win_static_std_pct'] = med_stats([w['static_std_pct'] for w in wins])
    allwob = [a for w in wins for a in w['wobble_amp_pct']]
    v = np.array(allwob)
    out['win_wobble_amp_pct'] = {'median': round(float(np.median(v)), 2),
                                 'p25': round(float(np.percentile(v, 25)), 2),
                                 'p75': round(float(np.percentile(v, 75)), 2),
                                 'min': round(float(v.min()), 2), 'max': round(float(v.max()), 2)}
    allpk = np.array([f for w in wins for f in w['wobble_peak_hz']])
    out['win_wobble_peak_hz'] = {'median': round(float(np.median(allpk)), 2),
                                 'p25': round(float(np.percentile(allpk, 25)), 2),
                                 'p75': round(float(np.percentile(allpk, 75)), 2)}
    out['win_sigma_w_pct_median'] = round(float(np.median(v) / np.sqrt(2) / np.sqrt(F)), 2)

    # --- 명령 vs 실측 추종오차 (전 구간) ---
    mu = M.mean(0)
    trk_full = [round(float(100 * (M[:, k] - C[:, k]).std() / mu[k]), 3) for k in range(4)]
    out['tracking_err_std_pct_full54s'] = trk_full
    # 대역 한정판 (0.3-5 Hz) — 요동 규약과 같은 대역에서의 추종오차
    trk_band = []
    for k in range(4):
        a, _ = band_rms_equiv_sine_pct((M[:, k] - C[:, k]) / mu[k] + 1.0, FS_GRID, *BAND)
        trk_band.append(round(float(a / np.sqrt(2)), 3))   # rms 로 환원 (등가사인 아님)
    out['tracking_err_bandrms_pct_full54s'] = trk_band
    # 1-s 창 CV (정본 문서 «1 s 창만 보면 1.0~1.4 %» 대조)
    cv1 = []
    for w in range(int(T_STABLE[1] - T_STABLE[0])):
        s = slice(int(w * FS_GRID), int((w + 1) * FS_GRID))
        Xw = M[s]
        cv1.extend([100 * Xw[:, k].std() / Xw[:, k].mean() for k in range(4)])
    cv1 = np.array(cv1)
    out['cv_1swin_pct'] = {'p10': round(float(np.percentile(cv1, 10)), 2),
                           'median': round(float(np.median(cv1)), 2),
                           'p90': round(float(np.percentile(cv1, 90)), 2)}

    print(json.dumps(out, indent=1, ensure_ascii=False))
    with open('dregon_room1_stats.json', 'w') as f:
        json.dump(out, f, indent=1, ensure_ascii=False)


if __name__ == '__main__':
    main()
