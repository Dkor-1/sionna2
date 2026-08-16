# -*- coding: utf-8 -*-
"""
rotor_log_traces_px4ab.py — 권고 ① 실행: PX4 로그 2건을 창 규약으로 재측정 + 10 Hz A/B (2026-08-16)
==============================================================================
정본: prior_work/rotor_jitter_sources.md §2-3 행동 1.
입력(원시 사본): prior_work/outputs/rotor_jitter_raw/
  - fe7c9eed-…ulg  S500 쿼드, 위치유지 호버 626 s, esc_status @~9.8 Hz
  - 1e858ce3-…ulg  레이싱 쿼드, 과격 호버 64 s, esc_status 평균 ~67 Hz(불균일)
창 규약(outputs/rotor_rpm_web_anchor.json method_note · rotor_log_traces.json
measurement_convention 을 그대로): 호버 창 = |v|<0.3 m/s 연속 & 모터 가동, 최소 3 s.
정적 산포 = 창 내 모터별 평균의 모터간 std/전체평균 [%] (ddof=0).
흔들림 = 모터별 상대 rpm 의 0.3–min(5.0, 0.45·fs) Hz 대역 rms×√2 [%], 피크 = 대역 PSD 피크.
σ_w 환산 = outputs/rotor_jitter_model.json 의 F-공식 (T = tau_ctl_s).

A/B(«4 Hz 앨리어싱 단서» 정량화): 67 Hz 로그의 각 구간을
  native(67 Hz 균일 격자) ↔ 10 Hz 표본유지(sample-hold) ↔ 4 Hz 표본유지
로 다시 재고, 대역을 규약대로 잘라(10 Hz→0.3–4.5, 4 Hz→0.3–1.8) 세 몫으로 분해한다:
  aliasing = ds/native(같은 대역) · band_clip = native(잘린 대역)/native(0.3–5) · total = 곱.

출력: outputs/rotor_log_traces.json 에 «후보» 행 2개 + aliasing A/B 절 **추가**
(기존 항목은 바이트 수준이 아니라 값 수준으로 보존을 검증한다 — 재직렬화 전 dict 동등성 확인).
⛔ src/rotor_dynamics.py PRESETS, 다른 rotor_*.json 원장은 건드리지 않는다.

실행: /workspace/.venvs/py312/bin/python benchmark/rotor_log_traces_px4ab.py
"""
import copy
import json
import math
import os

import numpy as np
from pyulog import ULog
from scipy.signal import periodogram

ROOT = "/workspace/sionna"
RAW = f"{ROOT}/prior_work/outputs/rotor_jitter_raw"
TRACES = f"{ROOT}/outputs/rotor_log_traces.json"
MODEL = f"{ROOT}/outputs/rotor_jitter_model.json"
LOG_S500 = "fe7c9eed-8dff-4283-a2a0-117185b41505"
LOG_RACE = "1e858ce3-07df-4a9f-9336-7670c953874f"

V_HOVER = 0.3      # m/s, 규약
MIN_DUR = 3.0      # s, 규약(px4)
F_LO = 0.3         # Hz, 규약
F_HI_NOM = 5.0     # Hz, 규약(상한은 0.45*fs 로 잘림)
TILE_S = 10.0      # S500 확장: 613 s 연속 호버를 분포 통계용으로 등분하는 타일 길이


def r(x, n=3):
    if isinstance(x, (list, tuple, np.ndarray)):
        return [r(v, n) for v in x]
    return round(float(x), n)


def load_log(name):
    u = ULog(f"{RAW}/{name}.ulg",
             message_name_filter_list=["esc_status", "vehicle_local_position"])
    esc = [d for d in u.data_list if d.name == "esc_status"][0]
    lp = [d for d in u.data_list if d.name == "vehicle_local_position"][0]
    t = esc.data["timestamp"] / 1e6
    rpm = np.vstack([esc.data[f"esc[{i}].esc_rpm"] for i in range(4)]).astype(float)
    tl = lp.data["timestamp"] / 1e6
    v = np.sqrt(lp.data["vx"] ** 2 + lp.data["vy"] ** 2 + lp.data["vz"] ** 2)
    vi = np.interp(t, tl, v)
    return t, rpm, vi


def band_stats(x, fs, f_lo, f_hi):
    """상대 신호[%] 1개의 대역 rms*sqrt(2) 진폭과 피크 주파수."""
    f, p = periodogram(x, fs=fs, window="boxcar", detrend="constant",
                       scaling="density")
    m = (f >= f_lo) & (f <= f_hi)
    if not m.any():
        return float("nan"), float("nan")
    df = f[1] - f[0]
    rms = math.sqrt(float(np.sum(p[m]) * df))
    pk = float(f[m][int(np.argmax(p[m]))])
    return rms * math.sqrt(2.0), pk


def window_stats(rpm_u, fs, f_lo, f_hi):
    """균일 격자 rpm (4,N) → 규약 통계."""
    mean_m = rpm_u.mean(axis=1)
    mean_all = float(mean_m.mean())
    dev = (mean_m / mean_all - 1.0) * 100.0
    static_std = float(np.std(dev))          # ddof=0, 기존 행과 동일
    amps, pks = [], []
    for k in range(4):
        rel = (rpm_u[k] / mean_m[k] - 1.0) * 100.0
        a, p = band_stats(rel, fs, f_lo, f_hi)
        amps.append(a)
        pks.append(p)
    return dict(level_mean=mean_all, static_dev_pct=dev.tolist(),
                static_std_pct=static_std,
                static_maxabs_pct=float(np.max(np.abs(dev))),
                static_range_pct=float(dev.max() - dev.min()),
                wobble_amp_pct=amps, wobble_peak_hz=pks)


def regrid(t, rpm, i0, i1, fs):
    """[i0:i1] 구간을 fs 균일 격자로 선형보간."""
    tt = t[i0:i1 + 1]
    tg = np.arange(tt[0], tt[-1], 1.0 / fs)
    return np.vstack([np.interp(tg, tt, rpm[k, i0:i1 + 1]) for k in range(4)]), tg


def sample_hold(t, rpm, t0, t1, fs):
    """실제 저속 로거처럼: fs 틱마다 «그 시점 이전의 마지막 원시 표본» 유지."""
    ticks = np.arange(t0, t1, 1.0 / fs)
    idx = np.searchsorted(t, ticks, side="right") - 1
    idx = np.clip(idx, 0, len(t) - 1)
    return rpm[:, idx], ticks


def find_runs(mask, t, min_dur, max_gap=0.5, strict=True):
    """mask 참인 표본들의 연속 런. strict=True 면 표본 하나만 빠져도 끊고(규약 «연속»),
    False 면 0.5 s 미만의 무효 표본 틈은 다리 놓는다(불균일 고속 로그용 — 보간은
    유효 표본만 쓴다)."""
    idx = np.where(mask)[0]
    if len(idx) == 0:
        return []
    cond = np.diff(t[idx]) > max_gap
    if strict:
        cond = cond | (np.diff(idx) > 1)
    brk = np.where(cond)[0]
    return [s for s in np.split(idx, brk + 1) if t[s[-1]] - t[s[0]] >= min_dur]


def regrid_idx(t, rpm, sel, fs):
    """유효 표본 인덱스 sel 만 써서 fs 균일 격자로 선형보간 (글리치 미유입)."""
    tt = t[sel]
    tg = np.arange(tt[0], tt[-1], 1.0 / fs)
    return np.vstack([np.interp(tg, tt, rpm[k, sel]) for k in range(4)]), tg


def sample_hold_idx(t, rpm, sel, fs):
    """유효 표본만 대상으로 fs 틱마다 직전 표본 유지 (저속 로거 모사)."""
    tt = t[sel]
    ticks = np.arange(tt[0], tt[-1], 1.0 / fs)
    idx = np.searchsorted(tt, ticks, side="right") - 1
    idx = np.clip(idx, 0, len(tt) - 1)
    return rpm[:, sel[idx]], ticks


def power_fractions(rpm_u, fs, cuts):
    """AC 스펙트럼(DC 제외, 나이퀴스트까지)에서 각 컷 기준 파워 비율. 4모터 평균."""
    out = {}
    for k in range(4):
        mean_k = rpm_u[k].mean()
        rel = (rpm_u[k] / mean_k - 1.0) * 100.0
        f, p = periodogram(rel, fs=fs, window="boxcar", detrend="constant",
                           scaling="density")
        tot = float(np.sum(p[f > 0]))
        for label, (lo, hi) in cuts.items():
            m = (f > lo) & (f <= hi)
            out.setdefault(label, []).append(float(np.sum(p[m]) / tot))
    return {k: r(float(np.mean(v)), 3) for k, v in out.items()}


def pairwise_corr(rpm_u):
    rel = rpm_u / rpm_u.mean(axis=1, keepdims=True) - 1.0
    rel = rel - rel.mean(axis=1, keepdims=True)
    c = np.corrcoef(rel)
    iu = np.triu_indices(4, 1)
    return float(np.mean(c[iu]))


def flatten_stats(windows):
    amps = np.array([a for w in windows for a in w["wobble_amp_pct"]])
    pks = np.array([p for w in windows for p in w["wobble_peak_hz"]])
    stds = np.array([w["static_std_pct"] for w in windows])
    return {
        "static_std_pct": {"median": r(np.median(stds)), "min": r(stds.min()),
                           "max": r(stds.max())},
        "wobble_amp_pct": {"median": r(np.median(amps)), "p25": r(np.percentile(amps, 25)),
                           "p75": r(np.percentile(amps, 75)), "min": r(amps.min()),
                           "max": r(amps.max())},
        "wobble_peak_hz": {"median": r(np.median(pks)), "p25": r(np.percentile(pks, 25)),
                           "p75": r(np.percentile(pks, 75))},
    }


def sigma_w_from_amp(amp_pct, f_lo, f_hi, T):
    F = (2.0 / math.pi) * (math.atan(2 * math.pi * f_hi * T)
                           - math.atan(2 * math.pi * f_lo * T))
    return amp_pct / math.sqrt(2.0) / math.sqrt(F), F


def main():
    with open(MODEL, encoding="utf-8") as fh:
        T_CTL = json.load(fh)["control_loop"]["tau_ctl_s"]

    # ---------------- S500 (fe7c9eed, ~9.8 Hz) ----------------
    t, rpm, vi = load_log(LOG_S500)
    fs_s500 = float(np.round(1.0 / np.median(np.diff(t)), 2))
    f_hi_s500 = min(F_HI_NOM, 0.45 * fs_s500)
    med_all = np.median(rpm[rpm > 0])
    running = (rpm > 0.5 * med_all).all(axis=0)
    hover = running & (vi < V_HOVER)
    runs = find_runs(hover, t, MIN_DUR)
    literal_windows = []
    for s in runs:
        rpm_u, tg = regrid(t, rpm, s[0], s[-1], fs_s500)
        w = window_stats(rpm_u, fs_s500, F_LO, f_hi_s500)
        literal_windows.append(dict(
            file=f"{LOG_S500}.ulg", t0=r(t[s[0]], 1), dur_s=r(t[s[-1]] - t[s[0]], 1),
            v_mean=r(vi[s].mean()), n_motor=4, fs_hz=fs_s500,
            level_mean=r(w["level_mean"], 1), static_dev_pct=r(w["static_dev_pct"]),
            static_std_pct=r(w["static_std_pct"]),
            static_maxabs_pct=r(w["static_maxabs_pct"]),
            static_range_pct=r(w["static_range_pct"]),
            wobble_amp_pct=r(w["wobble_amp_pct"]),
            wobble_peak_hz=r(w["wobble_peak_hz"], 2)))
    # 10 s 타일(분포 통계용 확장): 가장 긴 연속 호버 런을 등분
    tiles = []
    for s in runs:
        t0w, t1w = t[s[0]], t[s[-1]]
        n_t = int((t1w - t0w) // TILE_S)
        for k in range(n_t):
            a = t0w + k * TILE_S
            m = (t >= a) & (t < a + TILE_S) & hover
            idx = np.where(m)[0]
            if len(idx) < TILE_S * fs_s500 * 0.9:
                continue
            rpm_u, tg = regrid(t, rpm, idx[0], idx[-1], fs_s500)
            w = window_stats(rpm_u, fs_s500, F_LO, f_hi_s500)
            tiles.append(dict(
                file=f"{LOG_S500}.ulg", t0=r(a, 1), dur_s=r(TILE_S, 1),
                v_mean=r(vi[idx].mean()), n_motor=4, fs_hz=fs_s500,
                level_mean=r(w["level_mean"], 1),
                static_dev_pct=r(w["static_dev_pct"]),
                static_std_pct=r(w["static_std_pct"]),
                static_maxabs_pct=r(w["static_maxabs_pct"]),
                wobble_amp_pct=r(w["wobble_amp_pct"]),
                wobble_peak_hz=r(w["wobble_peak_hz"], 2)))
    tile_stats = flatten_stats(tiles)

    # 정본 [A] 대조: 최안정 60 s 창 (CV 합 최소)
    hov_idx = np.where(hover)[0]
    best = None
    for a in np.arange(t[hov_idx[0]], t[hov_idx[-1]] - 60.0, 5.0):
        m = (t >= a) & (t < a + 60.0) & hover
        if m.sum() < 60 * fs_s500 * 0.95:
            continue
        seg = rpm[:, m]
        cv = (seg.std(axis=1) / seg.mean(axis=1)).mean()
        if best is None or cv < best[0]:
            best = (cv, a, m)
    _, a60, m60 = best
    seg = rpm[:, m60]
    idx60 = np.where(m60)[0]
    rpm_u60, _ = regrid(t, rpm, idx60[0], idx60[-1], fs_s500)
    cv60 = seg.std(axis=1) / seg.mean(axis=1) * 100.0
    means60 = seg.mean(axis=1)
    fr60 = power_fractions(rpm_u60, fs_s500,
                           {"lt_0p5hz": (0.0, 0.5), "gt_2hz": (2.0, fs_s500)})
    doc_s500 = dict(
        window_t0_s=r(a60, 1), window_dur_s=60.0,
        per_motor_mean_rpm=r(means60, 0), per_motor_std_rpm=r(seg.std(axis=1), 0),
        per_motor_cv_pct=r(cv60, 2),
        inter_rotor_offset_range_rpm=r(means60.max() - means60.min(), 0),
        inter_rotor_offset_range_pct=r((means60.max() - means60.min())
                                       / means60.mean() * 100.0, 2),
        inter_rotor_wobble_corr_mean=r(pairwise_corr(rpm_u60), 2),
        power_fraction=fr60,
        doc_claims="정본 §1-가: CV 1.4~2.3 % · 오프셋 321 RPM=5.5 % · 상관 -0.10 · <0.5 Hz 50 % · >2 Hz 37 %",
        agreement="CV(1.44~2.25↔1.4~2.3)·오프셋(328 RPM 5.64 %↔321 RPM 5.5 %)·상관(-0.11↔-0.10)·<0.5 Hz(54.5↔50 %) 일치. ⚠어긋남 1건: >2 Hz 파워 24.1 % ↔ 정본 37 % — 창 위치·격자 규약 차이로 보이나 정본 수치를 재현하지 못했다(맞추지 않고 그대로 둔다)")

    amp_med_tiles = tile_stats["wobble_amp_pct"]["median"]
    sw_tiles, F_s500 = sigma_w_from_amp(amp_med_tiles, F_LO, f_hi_s500, T_CTL)
    amp_lit = float(np.median(literal_windows[0]["wobble_amp_pct"])) if literal_windows else float("nan")
    sw_lit, _ = sigma_w_from_amp(amp_lit, F_LO, f_hi_s500, T_CTL)

    s500_entry = {
        "name": "PX4 S500 (Pixhawk 6C, 양방향 DShot300) — fe7c9eed",
        "status": "«후보» — 2026-08-16 추가 (prior_work/rotor_jitter_sources.md §2-3 행동 1). 프리셋 반영은 관문(M0) 담당 몫",
        "venue": "outdoor",
        "signal": "measured rotor speed [rpm] (esc_status, 양방향 DShot 텔레메트리)",
        "access_ok": True,
        "note": "위치유지 자동 호버 626 s. |v|<0.3 m/s 연속 호버가 사실상 비행 전체(613 s 런 1개)라 규약 창이 1개로 퇴화 — 그래서 (a) 규약 그대로의 613 s 창 1개와 (b) 10 s 등분 타일(분포 통계용 확장, 규약의 창 정의에는 없는 등분)을 둘 다 싣는다",
        "n_windows": len(literal_windows),
        "n_tiles_10s": len(tiles),
        "files": [f"{LOG_S500}.ulg"],
        "total_hover_s": r(sum(w["dur_s"] for w in literal_windows), 1),
        "fs_hz": fs_s500,
        "band_hz": [F_LO, r(f_hi_s500, 2)],
        "level_mean": r(float(rpm[:, hover].mean()), 1),
        "windows_literal": literal_windows,
        "tile_stats_10s": tile_stats,
        "windows": tiles,
        "sigma_w_conversion": {
            "formula_source": "outputs/rotor_jitter_model.json sigma_w_calibration",
            "tau_ctl_s": T_CTL, "band_hz": [F_LO, r(f_hi_s500, 2)],
            "band_fraction_F": r(F_s500, 4),
            "from_tile_median_amp": {"amp_equiv_sine_pct": r(amp_med_tiles),
                                     "sigma_w_pct": r(sw_tiles, 3)},
            "from_literal_613s_amp": {"amp_equiv_sine_pct": r(amp_lit),
                                      "sigma_w_pct": r(sw_lit, 3)},
        },
        "doc_crosscheck_60s": doc_s500,
        "caution": "⚠DJI 아님(홀리브로 S500 키트급). 10 Hz 표집이라 4.5 Hz 위는 접힘 여지 — 단 아래 aliasing_ab 절이 67 Hz 로그로 그 여지를 정량화한다. 야외 바람 미상",
    }

    # ---------------- 레이싱 쿼드 (1e858ce3, 평균 ~67 Hz) ----------------
    t2, rpm2, vi2 = load_log(LOG_RACE)
    fs_native = 67.0  # 평균 표집률(4315표본/64.4 s). 대역(≤5 Hz) 통계에는 격자율 선택 무관
    med2 = np.median(rpm2, axis=1)
    valid = ((rpm2 > 0.2 * med2[:, None]) & (rpm2 < 3.0 * med2[:, None])).all(axis=0)
    hover2 = valid & (vi2 < V_HOVER)
    runs2 = find_runs(hover2, t2, MIN_DUR)
    # 규약 이탈 fallback: 스로틀 유지 구간(모든 모터 >0.5·중앙, 글리치 제외).
    # 불균일 고속 로그라 0.5 s 미만의 무효 표본 틈은 다리 놓고, 보간은 유효 표본만 쓴다.
    good2 = valid & (rpm2 > 0.5 * med2[:, None]).all(axis=0)
    segs2 = find_runs(good2, t2, MIN_DUR, max_gap=0.5, strict=False)
    seg_rows, ab_rows = [], []
    for s in segs2:
        dur = t2[s[-1]] - t2[s[0]]
        rpm_u, tg = regrid_idx(t2, rpm2, s, fs_native)
        w = window_stats(rpm_u, fs_native, F_LO, F_HI_NOM)
        seg_rows.append(dict(
            file=f"{LOG_RACE}.ulg", t0=r(t2[s[0]], 1), dur_s=r(dur, 1),
            v_mean=r(vi2[s].mean()), n_motor=4, fs_hz=fs_native,
            level_mean=r(w["level_mean"], 1), static_dev_pct=r(w["static_dev_pct"]),
            static_std_pct=r(w["static_std_pct"]),
            static_maxabs_pct=r(w["static_maxabs_pct"]),
            static_range_pct=r(w["static_range_pct"]),
            wobble_amp_pct=r(w["wobble_amp_pct"]),
            wobble_peak_hz=r(w["wobble_peak_hz"], 2)))
        # ---- A/B: native vs 10 Hz vs 4 Hz ----
        row = dict(t0=r(t2[s[0]], 1), dur_s=r(dur, 1))
        a_full = np.array(w["wobble_amp_pct"])
        for tag, fs_ds in (("ds10", 10.0), ("ds4", 4.0)):
            f_hi_ds = min(F_HI_NOM, 0.45 * fs_ds)
            # native 를 같은 대역으로 자른 판 (band_clip 성분)
            amps_nb = [band_stats((rpm_u[k] / rpm_u[k].mean() - 1) * 100.0,
                                  fs_native, F_LO, f_hi_ds)[0] for k in range(4)]
            rpm_ds, _ = sample_hold_idx(t2, rpm2, s, fs_ds)
            wds = window_stats(rpm_ds, fs_ds, F_LO, f_hi_ds)
            a_ds = np.array(wds["wobble_amp_pct"])
            a_nb = np.array(amps_nb)
            row[tag] = dict(
                band_hz=[F_LO, r(f_hi_ds, 2)],
                amp_native_full=r(a_full), amp_native_band=r(a_nb),
                amp_ds=r(a_ds),
                static_std_native=r(w["static_std_pct"]),
                static_std_ds=r(wds["static_std_pct"]),
                ratio_aliasing=r(float(np.mean(a_ds / a_nb)), 3),
                ratio_band_clip=r(float(np.mean(a_nb / a_full)), 3),
                ratio_total=r(float(np.mean(a_ds / a_full)), 3))
        ab_rows.append(row)

    # 정본 [A] 대조: 최안정 15 s 창 (다리 놓은 런 안에서 탐색, 유효 표본만 보간)
    best2 = None
    for s in segs2:
        if t2[s[-1]] - t2[s[0]] < 15.0:
            continue
        for a in np.arange(t2[s[0]], t2[s[-1]] - 15.0, 0.5):
            sel = s[(t2[s] >= a) & (t2[s] < a + 15.0)]
            if len(sel) < 15 * 40:
                continue
            rpm_u, _ = regrid_idx(t2, rpm2, sel, fs_native)
            cv = (rpm_u.std(axis=1) / rpm_u.mean(axis=1)).mean()
            if best2 is None or cv < best2[0]:
                best2 = (cv, a, sel)
    doc_race = {"doc_claims": "정본 §1-가: 평균 10225~11126 · CV 5.3~6.4 % · <2 Hz 86 % · >10 Hz 3 % · 오프셋 범위 8.4 % · 상관 +0.77 (15 s 창)"}
    if best2 is not None:
        _, a15, sel15 = best2
        rpm_u15, _ = regrid_idx(t2, rpm2, sel15, fs_native)
        cv15 = rpm_u15.std(axis=1) / rpm_u15.mean(axis=1) * 100.0
        means15 = rpm_u15.mean(axis=1)
        doc_race["best_15s_under_our_cleaning"] = dict(
            window_t0_s=r(a15, 1), window_dur_s=15.0,
            per_motor_mean_rpm=r(means15, 0), per_motor_cv_pct=r(cv15, 2),
            note="우리 정제(전 모터>0.5·중앙, 글리치 제외, 틈<0.5 s 다리) 아래 최안정 15 s — CV 가 정본의 5.3~6.4 % 와 크게 어긋난다(과격 구간이라). 정본의 «15 s 창»은 이 창이 아니다")
    # 정본 창의 실제 상대는 조용한 꼬리 구간(≥3 s 런의 마지막) — 평균·오프셋이 정확히 맞는다
    s_q = segs2[-1]
    rpm_uq, _ = regrid_idx(t2, rpm2, s_q, fs_native)
    cvq = rpm_uq.std(axis=1) / rpm_uq.mean(axis=1) * 100.0
    meansq = rpm_uq.mean(axis=1)
    frq = power_fractions(rpm_uq, fs_native,
                          {"lt_2hz": (0.0, 2.0), "gt_10hz": (10.0, fs_native)})
    doc_race["quiet_tail_segment"] = dict(
        window_t0_s=r(t2[s_q[0]], 1), window_dur_s=r(t2[s_q[-1]] - t2[s_q[0]], 1),
        per_motor_mean_rpm=r(meansq, 0), per_motor_cv_pct=r(cvq, 2),
        inter_rotor_offset_range_pct=r((meansq.max() - meansq.min())
                                       / meansq.mean() * 100.0, 2),
        inter_rotor_wobble_corr_mean=r(pairwise_corr(rpm_uq), 2),
        power_fraction=frq,
        agreement="평균 rpm(10238~11137↔10225~11126)·오프셋 범위(8.40↔8.4 %)가 정본과 일치 — 정본의 «15 s 창»은 사실상 이 조용한 꼬리(우리 정제로는 12.2 s). ⚠어긋남도 있다: CV 6.95~7.19 % (정본 5.3~6.4), 상관 +0.89 (정본 +0.77), <2 Hz 55.6 % (정본 86), >10 Hz 7.5 % (정본 3) — 정제·격자 규약 차이로 보이나, 정본 쪽 수치를 그대로 재현하지는 못했다")

    race_stats = flatten_stats(seg_rows)
    amp_med_race = race_stats["wobble_amp_pct"]["median"]
    sw_race, F_race = sigma_w_from_amp(amp_med_race, F_LO, F_HI_NOM, T_CTL)

    race_entry = {
        "name": "PX4 레이싱 쿼드 (KakuteH7, DShot150) — 1e858ce3",
        "status": "«후보» — 2026-08-16 추가 (prior_work/rotor_jitter_sources.md §2-3 행동 1). 프리셋 반영은 관문(M0) 담당 몫",
        "venue": "outdoor (과격 조종 호버)",
        "signal": "measured rotor speed [rpm] (esc_status, DShot 텔레메트리, 평균 ~67 Hz 불균일 표집)",
        "access_ok": True,
        "note": "⚠규약 호버 창 0개: |v|<0.3 m/s 연속 3 s 이상이 없다(최장 1.8 s) — 과격 조종 호버라서. 아래 행들은 «스로틀 유지 구간»(전 모터 >0.5·중앙값, 글리치 제외) fallback 이며 v_mean 이 규약(0.3)을 넘는다. 프리셋 값으로 직접 쓰지 말 것 — 기동 상한과 A/B 앨리어싱 정량화 전용",
        "n_windows": len(runs2),
        "windows": [],
        "n_fallback_segments": len(seg_rows),
        "files": [f"{LOG_RACE}.ulg"],
        "total_hover_s": 0.0,
        "total_fallback_s": r(sum(x["dur_s"] for x in seg_rows), 1),
        "fs_hz": fs_native,
        "fs_note": "메시지 중앙 dt 11.8 ms(~85 Hz)이나 드랍 포함 평균 67 Hz. 표본의 12.6 %는 글리치·스로틀 컷(0~2 kRPM, 1건 285 kRPM)으로 제외",
        "band_hz": [F_LO, F_HI_NOM],
        "level_mean": r(float(rpm2[:, good2].mean()), 1),
        "fallback_segments": seg_rows,
        "fallback_stats": race_stats,
        "sigma_w_conversion_reference_only": {
            "formula_source": "outputs/rotor_jitter_model.json sigma_w_calibration",
            "tau_ctl_s": T_CTL, "band_hz": [F_LO, F_HI_NOM],
            "band_fraction_F": r(F_race, 4),
            "from_fallback_median_amp": {"amp_equiv_sine_pct": r(amp_med_race),
                                         "sigma_w_pct": r(sw_race, 3)},
            "warning": "호버 규약 밖(과격 조종) — outdoor 프리셋 앵커로 쓰면 안 되고 기동 상한 참고치",
        },
        "doc_crosscheck": doc_race,
        "caution": "⚠DJI 아님(레이싱 프레임). 조종 공통 성분이 커서 로터 간 요동이 독립이 아님(정본 §1-가 상관 +0.77) — 호버 프리셋의 독립 OU 가정과 다른 레짐",
    }

    # ---------------- A/B 요약 (레짐 분리: 과격 3구간 vs 준-호버 꼬리 1구간) ----------------
    for row, sr in zip(ab_rows, seg_rows):
        row["v_mean"] = sr["v_mean"]
    aggr = ab_rows[:-1]
    quiet = ab_rows[-1]

    def med(rows, key, tag):
        return r(float(np.median([row[tag][key] for row in rows])), 3)

    ab_section = {
        "purpose": "정본 §2 의 «4 Hz(및 10 Hz) 앨리어싱 단서» 정량화 — 67 Hz 로그를 10/4 Hz 표본유지(sample-hold)로 강등해 같은 규약 통계를 재는 A/B",
        "method": "구간별로 native(67 Hz 균일격자, 0.3–5 Hz) ↔ sample-hold 10 Hz(0.3–4.5 Hz) ↔ 4 Hz(0.3–1.8 Hz). ratio_aliasing = 강등판/같은대역 native (접힘+표본유지 왜곡), ratio_band_clip = 잘린대역 native/전대역 native (대역 상한 손실), ratio_total = 둘의 곱. 4모터 비율 평균. 강등판도 유효 표본만 표본유지(글리치 미유입)",
        "source_segments": "1e858ce3 스로틀 유지 구간 4개 (13.6·5.3·17.6·12.2 s). 앞 3개는 과격 조종(v_mean 3.7~6.1 m/s), 마지막 1개가 준-호버 꼬리(v_mean 0.53 m/s) — 호버 프리셋에 유관한 레짐은 마지막 것",
        "per_segment": ab_rows,
        "summary": {
            "aggressive_3segs_median": {
                "ds10": {"ratio_aliasing": med(aggr, "ratio_aliasing", "ds10"),
                         "ratio_band_clip": med(aggr, "ratio_band_clip", "ds10"),
                         "ratio_total": med(aggr, "ratio_total", "ds10")},
                "ds4": {"ratio_aliasing": med(aggr, "ratio_aliasing", "ds4"),
                        "ratio_band_clip": med(aggr, "ratio_band_clip", "ds4"),
                        "ratio_total": med(aggr, "ratio_total", "ds4")},
                "reading": "저주파 요동이 지배하는 과격 레짐에서는 강등 왜곡이 ±5~10 % 수준",
            },
            "near_hover_quiet_seg": {
                "v_mean_ms": quiet["v_mean"], "dur_s": quiet["dur_s"],
                "ds10": quiet["ds10"], "ds4": quiet["ds4"],
                "reading": f"준-호버에서는 저주파 요동이 작아지는 대신 4.5 Hz 위 성분(고속 성분+텔레메트리 잡음)의 접힘이 상대적으로 커져, 10 Hz 강등이 흔들림 진폭을 ×{quiet['ds10']['ratio_aliasing']}, 4 Hz 강등이 ×{quiet['ds4']['ratio_aliasing']}(같은 대역 대비; 대역 손실까지 곱한 total 은 ×{quiet['ds4']['ratio_total']}) 부풀린다",
            },
            "static_spread": "정적 산포는 표집률에 사실상 불변 (per_segment 의 static_std_native vs static_std_ds)",
        },
    }
    q10, q4 = quiet["ds10"]["ratio_aliasing"], quiet["ds4"]["ratio_aliasing"]
    amp_corr = amp_med_tiles / q10
    sw_corr, _ = sigma_w_from_amp(amp_corr, F_LO, f_hi_s500, T_CTL)
    aq_amp, aq_sw = 2.52, 2.45  # outputs/rotor_jitter_model.json anchors[1]
    aq_sw_corr, _ = sigma_w_from_amp(aq_amp / q4, 0.3, 1.8, T_CTL)
    ab_section["conclusion"] = {
        "direction": "⭐표집 강등은 흔들림 통계를 «깎지» 않고 오히려 «부풀리는» 쪽이다 — 대역 손실(band_clip 0.75~1.00)보다 접힘 유입(aliasing 0.94~1.77)이 크다. 따라서 S500 10 Hz·AQUILA 4 Hz 에서 잰 σ_w 는 과소가 아니라 상한측 추정",
        "s500_implication": f"S500 10 Hz 타일 중앙 amp {r(amp_med_tiles)} % 에 준-호버 비율(÷{q10})을 적용하면 참-대역 amp ≈ {r(amp_corr, 2)} %, σ_w ≈ {r(sw_corr, 2)} % — 즉 S500 σ_w 는 {r(sw_corr, 2)}~{r(sw_tiles, 2)} % 구간",
        "aquila_implication": f"outdoor 프리셋 근거(AQUILA 4 Hz, amp {aq_amp} %→σ_w {aq_sw} %)에 준-호버 비율(÷{q4})을 그대로 옮기면 σ_w ≈ {r(aq_sw_corr, 2)} % 까지 내려갈 수 있다. ⚠단 전이 불확실 — 접힘 몫은 기체·ESC 텔레메트리의 고주파 잡음 구조에 달려 있고(레이싱 쿼드는 그 잡음이 큰 쪽), AQUILA 는 CAN ESC 라 다를 수 있다. 결론: outdoor σ_w 2.45 % 는 «{r(aq_sw_corr, 2)}~2.45 % 대역의 상한측» 으로 읽는 것이 정직하다",
        "doc_caveat_status": "정본 §2-2 의 낙관(«67 Hz 로그의 >10 Hz 파워 3 % 가 앨리어싱 걱정 자체를 줄여 준다»)은 과격 레짐에서만 성립한다. 준-호버 구간에서는 4.5 Hz 위 파워(총 AC 의 ~22 %)의 접힘이 무시 못 할 크기다 — 단 방향이 «부풀림»이므로, 4 Hz 표집 때문에 프리셋이 실측보다 «작게» 잡혔을 걱정은 방향부터 성립하지 않는다. ⚠앨리어싱 단서는 «닫힘»이 아니라 «방향 확정 + 크기 상한(≤×1.77) 확보»로 좁혀졌다",
    }

    # ---------------- 원장에 «후보» 행으로 추가 ----------------
    with open(TRACES, encoding="utf-8") as fh:
        traces = json.load(fh)
    before = copy.deepcopy(traces)
    assert "px4_s500_fe7c9eed" not in traces["sources"]
    assert "px4_racing_1e858ce3" not in traces["sources"]
    traces["sources"]["px4_s500_fe7c9eed"] = s500_entry
    traces["sources"]["px4_racing_1e858ce3"] = race_entry
    traces["aliasing_ab_10hz_20260816"] = ab_section
    traces["amendment_20260816"] = {
        "what": "권고 ①(prior_work/rotor_jitter_sources.md §2-3 행동 1): PX4 로그 2건을 창 규약으로 재측정한 «후보» 행 2개 + 10/4 Hz 앨리어싱 A/B 절 추가. 기존 행 무수정",
        "script": "benchmark/rotor_log_traces_px4ab.py",
        "interpreter": "/workspace/.venvs/py312/bin/python (pyulog·scipy 기설치 — 신규 설치 없음)",
        "convention_source": "outputs/rotor_rpm_web_anchor.json method_note + 본 파일 measurement_convention (동일 규약)",
    }
    # 기존 항목 값 보존 검증
    for k in before["sources"]:
        assert traces["sources"][k] == before["sources"][k], k
    for k in before:
        if k != "sources":
            assert traces[k] == before[k], k
    with open(TRACES, "w", encoding="utf-8") as fh:
        json.dump(traces, fh, ensure_ascii=False, indent=1)
        fh.write("\n")

    # ---------------- 요약 출력 ----------------
    print("== S500 fe7c9eed (fs %.2f Hz, band 0.3–%.1f Hz) ==" % (fs_s500, f_hi_s500))
    print(" literal windows:", len(literal_windows),
          "| 613s window static_std %.2f %% amp(4motor) %s" % (
              literal_windows[0]["static_std_pct"],
              literal_windows[0]["wobble_amp_pct"]))
    print(" tiles(10s) n=%d | static med %.2f [%.2f..%.2f] | amp med %.2f [p25 %.2f p75 %.2f] | peak med %.2f Hz"
          % (len(tiles), tile_stats["static_std_pct"]["median"],
             tile_stats["static_std_pct"]["min"], tile_stats["static_std_pct"]["max"],
             tile_stats["wobble_amp_pct"]["median"], tile_stats["wobble_amp_pct"]["p25"],
             tile_stats["wobble_amp_pct"]["p75"], tile_stats["wobble_peak_hz"]["median"]))
    print(" sigma_w: tiles %.3f %% | literal %.3f %% (F=%.4f)" % (sw_tiles, sw_lit, F_s500))
    print(" doc60s:", json.dumps(doc_s500, ensure_ascii=False))
    print("== racing 1e858ce3 ==")
    print(" convention hover windows:", len(runs2), "(fallback segments:", len(seg_rows), ")")
    for x in seg_rows:
        print("  seg t0 %.1f dur %.1f v_mean %.2f static %.2f amp %s" % (
            x["t0"], x["dur_s"], x["v_mean"], x["static_std_pct"], x["wobble_amp_pct"]))
    print(" fallback stats:", json.dumps(race_stats))
    print(" sigma_w(ref only): %.3f %% (F=%.4f)" % (sw_race, F_race))
    print(" doc15s:", json.dumps(doc_race, ensure_ascii=False))
    print("== A/B ==")
    print(json.dumps(ab_section["summary"], ensure_ascii=False, indent=1))
    for row in ab_rows:
        print(" seg t0 %.1f: ds10 alias %.3f clip %.3f total %.3f | ds4 alias %.3f clip %.3f total %.3f"
              % (row["t0"], row["ds10"]["ratio_aliasing"], row["ds10"]["ratio_band_clip"],
                 row["ds10"]["ratio_total"], row["ds4"]["ratio_aliasing"],
                 row["ds4"]["ratio_band_clip"], row["ds4"]["ratio_total"]))


if __name__ == "__main__":
    main()
