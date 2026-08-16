# -*- coding: utf-8 -*-
"""
rotor_log_corpus.py — 공개 비행로그 대량 채굴로 로터 회전수 통계 코퍼스 만들기 (2026-08-16)
=============================================================================================
무엇을 하나
-----------
PX4 Flight Review 공개 DB(448,189건)에서 **실기체 멀티로터 + ESC 텔레메트리(esc_status)**
로그를 골라 내려받고, 호버 구간을 같은 규약으로 잘라 로터 회전수의 통계를 낸다.
결과는 `outputs/rotor_log_corpus_0816.json`.

⭐이전 라운드(2026-08-10/16)와 무엇이 다른가 — 넷
-------------------------------------------------
1. **표본 수**: 2건 → 수십 건. 메타데이터 API + HTTP Range 로 «머리 200 KB 만 받아
   구독 토픽 목록을 읽는» 선별기를 써서 수천 건을 싸게 훑는다.
2. **텔레메트리 글리치 제거**: 양방향 DShot 은 깨진 프레임을 그대로 rpm 으로 올린다
   (실측: 9400 rpm 로터에 285,257 rpm 한 점). 안 걸러내면 σ_w 가 부풀려진다.
   Hampel(중앙값 기반) 필터로 걸러 내고 **걸러낸 비율을 기록**한다.
3. **σ_w 를 대역몫 가정 없이 직접 잰다**: 이전에는 0.3–5 Hz 대역 rms → «등가 사인» →
   OU 코너 τ=0.227 s **를 가정해** σ_w 로 환산했다(순환 논법의 위험).
   여기서는 PSD 에 OU 모형을 **직접 적합**해 σ 와 τ 를 동시에 얻고, 백색 바닥 N0 도 같이
   푼다(측정 잡음 분리). 자기상관 1/e 시간으로 교차검증한다.
4. **공통모드/차동 분해**: 모델은 로터별 «독립» OU 다. 실제 로그에서 네 로터가 함께
   움직이는 몫(고도 유지 스로틀)과 따로 움직이는 몫을 나눠 재서 그 가정을 시험한다.

규약(이전 원장과 비교 가능하도록 옛 규약도 같이 낸다)
------------------------------------------------------
- 호버 창 : |v| < 0.3 m/s 연속 구간, 모든 활성 로터 rpm > 0.4×비행중앙값, 길이 ≥ MIN_WIN_S
- σ_s     : 창 내 로터별 평균의 로터 간 std / 전체평균 [%] (ddof=0, 옛 규약과 동일)
- σ_w     : 로터별 상대신호를 0.05 Hz 고역통과한 뒤의 std [%] 의 로터 중앙값
- 옛 규약 : 0.3–5 Hz 대역 rms × √2 (등가 사인 진폭) — 비교용으로만
"""
from __future__ import annotations

import json, os, sys, math
import numpy as np

SPEED_HOVER_MS = 0.30      # 호버 판정 속도 상한
MIN_WIN_S      = 20.0      # 창 최소 길이 [s] — 0.05 Hz 까지 보려고 옛 3 s 에서 늘렸다
MIN_WIN_S_FALLBACK = 8.0   # 20 s 창이 하나도 없을 때만 쓰는 짧은 창(플래그를 단다)
MAX_WIN_PER_LOG = 6        # 로그당 가장 긴 창 몇 개까지
HP_HZ          = 0.05      # 고역통과 — 배터리 처짐 같은 초저주파 표류를 뺀다
LEGACY_BAND    = (0.3, 5.0)
HAMPEL_K       = 7         # Hampel 창 반폭 [샘플]
HAMPEL_NSIG    = 6.0       # 중앙값에서 6·MAD 넘으면 글리치


# --------------------------------------------------------------------------- #
def hampel(x, k=HAMPEL_K, nsig=HAMPEL_NSIG):
    """중앙값 기반 이상점 제거. (수리된 배열, 수리된 표본 비율) 반환."""
    x = np.asarray(x, float)
    n = len(x)
    if n < 2 * k + 3:
        return x.copy(), 0.0
    idx = np.arange(n)
    lo = np.clip(idx - k, 0, n - 1)
    win = np.lib.stride_tricks.sliding_window_view(
        np.pad(x, (k, k), mode='edge'), 2 * k + 1)
    med = np.median(win, axis=1)
    mad = np.median(np.abs(win - med[:, None]), axis=1) * 1.4826
    mad = np.maximum(mad, 1e-9 * max(1.0, abs(np.median(x))))
    bad = np.abs(x - med) > nsig * mad
    y = x.copy()
    y[bad] = med[bad]
    return y, float(bad.mean())


def runs_of_true(mask, min_len):
    """연속 True 구간의 (시작, 끝) 인덱스 목록."""
    m = np.concatenate(([False], np.asarray(mask, bool), [False]))
    d = np.diff(m.astype(np.int8))
    starts, ends = np.where(d == 1)[0], np.where(d == -1)[0]
    return [(s, e) for s, e in zip(starts, ends) if e - s >= min_len]


def highpass_fft(x, fs, f_hp):
    """FFT 로 f_hp 아래를 잘라 낸다(창 평균 제거 포함)."""
    x = np.asarray(x, float) - np.mean(x)
    n = len(x)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1.0 / fs)
    X[f < f_hp] = 0.0
    return np.fft.irfft(X, n=n)


def band_rms(x, fs, f1, f2):
    """[f1,f2] 대역 성분의 rms (Parseval)."""
    x = np.asarray(x, float) - np.mean(x)
    n = len(x)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1.0 / fs)
    sel = (f >= f1) & (f <= f2)
    p = (np.abs(X[sel]) ** 2).sum() * 2.0 / (n * n)
    if n % 2 == 0 and sel.size and sel[-1]:
        p -= (np.abs(X[-1]) ** 2) / (n * n)
    return float(np.sqrt(max(p, 0.0)))


def ou_psd(f, sigma, tau):
    """OU 한쪽 PSD. ∫₀^∞ S df = σ²."""
    return 4.0 * sigma * sigma * tau / (1.0 + (2.0 * np.pi * f * tau) ** 2)


def fit_ou(f, S, f_lo, f_hi, with_floor=True):
    """로그영역 최소제곱으로 (σ, τ, N0) 적합. 실패하면 None."""
    from scipy.optimize import least_squares
    sel = (f >= f_lo) & (f <= f_hi) & (S > 0)
    if sel.sum() < 6:
        return None
    ff, SS = f[sel], S[sel]
    s0 = math.sqrt(max(np.trapezoid(SS, ff), 1e-18))
    p0 = [math.log(max(s0, 1e-9)), math.log(0.25)] + ([math.log(max(SS.min(), 1e-18))] if with_floor else [])

    def resid(p):
        sig, tau = math.exp(p[0]), math.exp(p[1])
        m = ou_psd(ff, sig, tau)
        if with_floor:
            m = m + math.exp(p[2])
        return np.log(m) - np.log(SS)

    try:
        r = least_squares(resid, p0, method='lm', max_nfev=6000)
    except Exception:
        return None
    sig, tau = math.exp(r.x[0]), math.exp(r.x[1])
    n0 = math.exp(r.x[2]) if with_floor else 0.0
    if not (np.isfinite(sig) and np.isfinite(tau)) or tau <= 0 or tau > 100:
        return None
    return {'sigma': sig, 'tau_s': tau, 'f_corner_hz': 1.0 / (2 * math.pi * tau),
            'noise_floor': n0, 'cost': float(r.cost), 'n_bins': int(sel.sum())}


def acf_tau(x, fs, max_lag_s=5.0):
    """자기상관이 1/e 로 떨어지는 시간 [s] — OU 적합의 교차검증."""
    x = np.asarray(x, float) - np.mean(x)
    n = len(x)
    if n < 8:
        return None
    nl = min(int(max_lag_s * fs), n - 2)
    if nl < 3:
        return None
    X = np.fft.rfft(x, n=2 * n)
    ac = np.fft.irfft(np.abs(X) ** 2)[:nl + 1]
    if ac[0] <= 0:
        return None
    ac /= ac[0]
    below = np.where(ac < math.exp(-1.0))[0]
    if below.size == 0:
        return None
    i = below[0]
    if i == 0:
        return 0.0
    y0, y1 = ac[i - 1], ac[i]
    frac = (y0 - math.exp(-1.0)) / max(y0 - y1, 1e-12)
    return float((i - 1 + frac) / fs)


# --------------------------------------------------------------------------- #
def analyse_log(path, meta=None):
    """ulog 하나 → 창별 통계 목록 + 로그 수준 요약."""
    from pyulog import ULog
    out = {'file': os.path.basename(path), 'meta': meta or {}}
    try:
        u = ULog(path, ['esc_status', 'vehicle_local_position', 'actuator_motors'])
    except Exception as e:
        out['err'] = 'parse:' + type(e).__name__ + ':' + str(e)[:120]
        return out
    esc = {d.name: d for d in u.data_list}.get('esc_status')
    lpos = {d.name: d for d in u.data_list}.get('vehicle_local_position')
    if esc is None or lpos is None:
        out['err'] = 'missing_topic'
        return out
    t = np.asarray(esc.data['timestamp'], float) / 1e6
    if len(t) < 200:
        out['err'] = 'too_few_esc_samples:%d' % len(t)
        return out
    dt = np.median(np.diff(t))
    if not np.isfinite(dt) or dt <= 0:
        out['err'] = 'bad_dt'
        return out
    fs = 1.0 / dt
    out['fs_hz'] = round(float(fs), 2)
    out['esc_dur_s'] = round(float(t[-1] - t[0]), 1)

    n_esc = int(np.max(esc.data['esc_count'])) if 'esc_count' in esc.data else 0
    keys = [k for k in esc.data if k.endswith('.esc_rpm')]
    keys.sort(key=lambda s: int(s.split('[')[1].split(']')[0]))
    R = []
    for k in keys:
        v = np.asarray(esc.data[k], float)
        med = np.median(v[v > 0]) if (v > 0).any() else 0.0
        if med < 200:                       # 배선 안 된 채널
            continue
        R.append(v)
    if len(R) < 3:
        out['err'] = 'active_rotors=%d' % len(R)
        return out
    R = np.vstack(R)                        # (n_rotor, n_t)
    out['n_rotors'] = int(R.shape[0])
    out['esc_count_field'] = n_esc

    # --- 글리치 수리 -------------------------------------------------------- #
    rep = []
    Rc = np.empty_like(R)
    for i in range(R.shape[0]):
        Rc[i], f_rep = hampel(R[i])
        rep.append(f_rep)
    out['glitch_repaired_frac'] = round(float(np.mean(rep)), 5)
    out['glitch_repaired_max_rotor'] = round(float(np.max(rep)), 5)

    # --- 양자화 계단 추정 --------------------------------------------------- #
    d0 = np.diff(np.unique(Rc[0][Rc[0] > 0]))
    q = float(np.median(d0)) if d0.size > 5 else float('nan')
    lvl_all = float(np.median(Rc[Rc > 0]))
    out['quant_step_rpm'] = round(q, 3) if np.isfinite(q) else None
    out['quant_step_pct'] = round(100 * q / lvl_all, 4) if (np.isfinite(q) and lvl_all > 0) else None

    # --- 속도를 esc 시각에 맞춰 보간 ---------------------------------------- #
    tl = np.asarray(lpos.data['timestamp'], float) / 1e6
    try:
        vx = np.asarray(lpos.data['vx'], float); vy = np.asarray(lpos.data['vy'], float)
        vz = np.asarray(lpos.data['vz'], float)
    except KeyError:
        out['err'] = 'no_velocity_fields'
        return out
    sp = np.sqrt(vx * vx + vy * vy + vz * vz)
    ok = np.isfinite(sp)
    if ok.sum() < 10:
        out['err'] = 'no_valid_velocity'
        return out
    sp_i = np.interp(t, tl[ok], sp[ok], left=np.nan, right=np.nan)

    med_r = np.median(Rc, axis=1)
    running = np.all(Rc > 0.4 * med_r[:, None], axis=0)
    hov = (sp_i < SPEED_HOVER_MS) & running & np.isfinite(sp_i)
    out['hover_frac'] = round(float(np.mean(hov)), 4)

    runs = runs_of_true(hov, int(MIN_WIN_S * fs))
    short = False
    if not runs:                                    # 긴 창이 없으면 짧은 창으로 후퇴(플래그)
        runs = runs_of_true(hov, int(MIN_WIN_S_FALLBACK * fs))
        short = bool(runs)
    out['short_window_fallback'] = short
    runs.sort(key=lambda ab: ab[1] - ab[0], reverse=True)

    # 명령 신호(actuator_motors) — «광대역 성분이 진짜 제어인가 텔레메트리 잡음인가» 대조용
    cmd = _cmd_series(u, t)
    out['has_cmd'] = cmd is not None

    wins = []
    for (a, b) in runs[:MAX_WIN_PER_LOG]:
        w = window_stats(t[a:b], Rc[:, a:b], R[:, a:b], fs, float(np.nanmean(sp_i[a:b])),
                         cmd=(cmd[:, a:b] if cmd is not None else None), short=short)
        if w:
            wins.append(w)
    out['n_windows'] = len(wins)
    out['total_hover_s'] = round(sum(w['dur_s'] for w in wins), 1)
    out['windows'] = wins
    return out


def _cmd_series(u, t_esc):
    """actuator_motors(정규화 스로틀 명령)를 esc 시각 격자로 보간. 없으면 None."""
    am = {d.name: d for d in u.data_list}.get('actuator_motors')
    if am is None:
        return None
    keys = sorted([k for k in am.data if k.startswith('control[')],
                  key=lambda s: int(s.split('[')[1].split(']')[0]))
    if len(keys) < 3:
        return None
    ta = np.asarray(am.data['timestamp'], float) / 1e6
    cols = []
    for k in keys[:8]:
        v = np.asarray(am.data[k], float)
        if not np.isfinite(v).any() or np.nanmedian(np.abs(v)) < 1e-3:
            continue
        cols.append(np.interp(t_esc, ta, np.nan_to_num(v)))
    if len(cols) < 3:
        return None
    return np.vstack(cols)


def window_stats(tw, Rw, Rraw, fs, v_mean, cmd=None, short=False):
    """창 하나의 통계. Rw=(n_rotor, n) 수리본, Rraw=원본(비교용), cmd=명령 신호."""
    n = Rw.shape[1]
    if n < int(min(MIN_WIN_S, MIN_WIN_S_FALLBACK if short else MIN_WIN_S) * fs) or n < 32:
        return None
    lvl_k = Rw.mean(axis=1)
    lvl = float(lvl_k.mean())
    if lvl <= 0:
        return None
    rel = Rw / lvl_k[:, None] - 1.0                    # 로터별 상대 신호

    # 정적 산포(옛 규약과 동일: ddof=0)
    sig_s0 = float(np.std(lvl_k, ddof=0) / lvl)
    sig_s1 = float(np.std(lvl_k, ddof=1) / lvl)
    off_range = float((lvl_k.max() - lvl_k.min()) / lvl)

    # 시간 흔들림 — 직접 측정(0.05 Hz 고역통과 뒤 std)
    hp = np.vstack([highpass_fft(rel[k], fs, HP_HZ) for k in range(rel.shape[0])])
    sig_w_k = hp.std(axis=1)
    # 옛 규약(0.3–5 Hz 등가 사인 진폭) — 비교 전용
    f2 = min(LEGACY_BAND[1], 0.45 * fs)
    amp_leg_k = np.array([band_rms(rel[k], fs, LEGACY_BAND[0], f2) * math.sqrt(2) for k in range(rel.shape[0])])

    # 글리치 수리 전/후 비교 — 옛 수치가 얼마나 오염됐나
    relr = Rraw / Rraw.mean(axis=1)[:, None] - 1.0
    hpr = np.vstack([highpass_fft(relr[k], fs, HP_HZ) for k in range(relr.shape[0])])
    sig_w_raw = float(np.median(hpr.std(axis=1)))

    # 공통모드 / 차동 분해 — «로터별 독립» 가정 시험
    com = hp.mean(axis=0)
    dif = hp - com[None, :]
    sig_com = float(com.std())
    sig_dif = float(np.median(dif.std(axis=1)))

    # 로터 간 상관 (고역통과 뒤)
    nr = hp.shape[0]
    cors = []
    for i in range(nr):
        for j in range(i + 1, nr):
            a, b = hp[i], hp[j]
            sa, sb = a.std(), b.std()
            if sa > 0 and sb > 0:
                cors.append(float(np.mean((a - a.mean()) * (b - b.mean())) / (sa * sb)))
    cor_mean = float(np.mean(cors)) if cors else None

    # PSD + OU 적합
    from scipy.signal import welch
    nper = int(min(n, max(64, fs * min(32.0, n / fs / 2.0))))
    Ps = []
    for k in range(rel.shape[0]):
        f, P = welch(rel[k], fs=fs, nperseg=nper, noverlap=nper // 2, detrend='linear')
        Ps.append(P)
    P = np.mean(Ps, axis=0)
    f_lo = max(HP_HZ, 2.0 / (n / fs))
    f_hi = min(0.40 * fs, 8.0)
    fit = fit_ou(f, P, f_lo, f_hi, with_floor=True)
    fit_nf = fit_ou(f, P, f_lo, f_hi, with_floor=False)

    def frac(a, b):
        s = (f >= f_lo) & (f <= f_hi)
        tot = np.trapezoid(P[s], f[s])
        m = (f >= max(a, f_lo)) & (f <= min(b, f_hi))
        return round(float(np.trapezoid(P[m], f[m]) / tot), 4) if tot > 0 and m.sum() > 1 else None

    tau_ac = float(np.median([x for x in (acf_tau(hp[k], fs) for k in range(hp.shape[0])) if x is not None] or [np.nan]))

    # 명령(actuator_motors) 대조 — 광대역 성분이 제어인지 텔레메트리 잡음인지
    cmd_stat = None
    if cmd is not None and cmd.shape[1] == n:
        cr = cmd / np.maximum(np.abs(cmd.mean(axis=1))[:, None], 1e-9) - 1.0
        chp = np.vstack([highpass_fft(cr[k], fs, HP_HZ) for k in range(cr.shape[0])])
        Pc = []
        for k in range(cr.shape[0]):
            fc, Pk = welch(cr[k], fs=fs, nperseg=nper, noverlap=nper // 2, detrend='linear')
            Pc.append(Pk)
        Pc = np.mean(Pc, axis=0)
        sc = (fc >= f_lo) & (fc <= f_hi)
        totc = np.trapezoid(Pc[sc], fc[sc]) if sc.sum() > 1 else 0.0
        m2 = (fc >= 2.0) & (fc <= f_hi)
        cmd_stat = {
            'sigma_cmd_pct': round(100 * float(np.median(chp.std(axis=1))), 3),
            'cmd_pow_frac_gt2hz': (round(float(np.trapezoid(Pc[m2], fc[m2]) / totc), 4)
                                   if totc > 0 and m2.sum() > 1 else None),
        }

    return {
        'dur_s': round(float(tw[-1] - tw[0]), 1), 'n': int(n),
        'v_mean_ms': round(float(v_mean), 3),
        'level_rpm': round(lvl, 1),
        'level_per_rotor_rpm': [round(float(x), 1) for x in lvl_k],
        'sigma_s_pct': round(100 * sig_s0, 3),
        'sigma_s_pct_ddof1': round(100 * sig_s1, 3),
        'rotor_offset_range_pct': round(100 * off_range, 3),
        'sigma_w_pct': round(100 * float(np.median(sig_w_k)), 3),
        'sigma_w_pct_per_rotor': [round(100 * float(x), 3) for x in sig_w_k],
        'sigma_w_pct_unrepaired': round(100 * sig_w_raw, 3),
        'legacy_amp_pct_0p3_5hz': round(100 * float(np.median(amp_leg_k)), 3),
        'sigma_common_pct': round(100 * sig_com, 3),
        'sigma_diff_pct': round(100 * sig_dif, 3),
        'inter_rotor_corr': round(cor_mean, 3) if cor_mean is not None else None,
        'ou_fit': ({k: (round(v, 5) if isinstance(v, float) else v) for k, v in fit.items()} if fit else None),
        'ou_fit_nofloor': ({k: (round(v, 5) if isinstance(v, float) else v) for k, v in fit_nf.items()} if fit_nf else None),
        'tau_acf_s': round(tau_ac, 4) if np.isfinite(tau_ac) else None,
        'pow_frac_lt0p5hz': frac(0.0, 0.5), 'pow_frac_0p5_2hz': frac(0.5, 2.0),
        'pow_frac_2_5hz': frac(2.0, 5.0), 'pow_frac_gt5hz': frac(5.0, 1e9),
        'fit_band_hz': [round(f_lo, 3), round(f_hi, 2)],
        'short_window': bool(short),
        'cmd': cmd_stat,
    }


if __name__ == '__main__':
    import glob
    res = [analyse_log(p) for p in sorted(glob.glob(sys.argv[1]))]
    print(json.dumps(res, indent=1, ensure_ascii=False)[:6000])
