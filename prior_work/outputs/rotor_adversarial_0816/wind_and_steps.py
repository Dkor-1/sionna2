# -*- coding: utf-8 -*-
"""② 모델이 못 담는 것 둘 — (가) 바람 손잡이 (나) 스로틀 계단(수직 기동) 응답.

(가) 바람 — 공개 로그에 풍속은 거의 없다(내려받은 26건 중 wind_estimate 2건뿐).
    그래서 **물리 대리값**을 쓴다: 호버 중 기체 «기울기»(수평면에서 벗어난 각).
    바람 속에서 위치를 지키려면 바람 쪽으로 기울여야 하고 tan(기울기) = 항력/무게 다.
    기울기 ↔ σ_w 상관을 재면 Heutschi 2020 의 «바람 1 m/s 당 σ +0.52~1.09 %p» 가
    독립 데이터에서 재현되는지 볼 수 있다.

(나) 스로틀 계단 — 상승·하강 구간에서 네 로터가 **함께** 몇 % 를 몇 초에 움직이나.
    우리 모델은 평균 rpm 이 상수라 이 성분이 **원리적으로 0** 이다.
"""
import json
import os

import numpy as np
from pyulog import ULog
from scipy.signal import periodogram

HERE = os.path.dirname(os.path.abspath(__file__))
DL = f"{HERE}/px4_logs"
RAW = "/workspace/sionna/prior_work/outputs/rotor_jitter_raw"


def q_to_tilt(q):
    """쿼터니언 (n,4) → 수평에서 벗어난 각[deg]. 몸체 z 축과 −중력의 각."""
    w, x, y, z = q[:, 0], q[:, 1], q[:, 2], q[:, 3]
    czz = 1 - 2 * (x * x + y * y)
    return np.degrees(np.arccos(np.clip(czz, -1, 1)))


def band_amp(x, fs, f1, f2):
    f, p = periodogram(x, fs=fs, window="boxcar", detrend="constant")
    m = (f >= f1) & (f <= f2)
    if m.sum() < 2:
        return np.nan
    return float(np.sqrt(np.sum(p[m]) * (f[1] - f[0])) * np.sqrt(2))


def find_runs(mask, t, min_dur):
    idx = np.where(mask)[0]
    if not len(idx):
        return []
    brk = np.where((np.diff(t[idx]) > 0.5) | (np.diff(idx) > 1))[0]
    return [s for s in np.split(idx, brk + 1) if t[s[-1]] - t[s[0]] >= min_dur]


def analyse(path, tag):
    try:
        u = ULog(path, message_name_filter_list=["esc_status", "vehicle_local_position",
                                                 "vehicle_attitude"])
    except Exception:
        return [], []
    names = {d.name for d in u.data_list}
    if not {"esc_status", "vehicle_local_position", "vehicle_attitude"} <= names:
        return [], []
    esc = [d for d in u.data_list if d.name == "esc_status"][0]
    if "esc[3].esc_rpm" not in esc.data:
        return [], []
    t = esc.data["timestamp"] / 1e6
    rpm = np.vstack([esc.data[f"esc[{i}].esc_rpm"] for i in range(4)]).astype(float)
    if np.nanmax(rpm) < 1500:
        return [], []
    lp = [d for d in u.data_list if d.name == "vehicle_local_position"][0]
    at = [d for d in u.data_list if d.name == "vehicle_attitude"][0]
    tl = lp.data["timestamp"] / 1e6
    vh = np.sqrt(lp.data["vx"] ** 2 + lp.data["vy"] ** 2)
    vz = lp.data["vz"]
    v = np.sqrt(vh ** 2 + vz ** 2)
    ta = at.data["timestamp"] / 1e6
    q = np.vstack([at.data[f"q[{i}]"] for i in range(4)]).T
    tilt = q_to_tilt(q)
    vi = np.interp(t, tl, v)
    vzi = np.interp(t, tl, vz)
    ti = np.interp(t, ta, tilt)
    fs = float(1.0 / np.median(np.diff(t)))
    med = np.median(rpm[rpm > 0])
    run = (rpm > 0.5 * med).all(axis=0)

    # ---- (가) 호버 창: 기울기 vs σ_w -----------------------------------
    wind_rows = []
    if fs >= 8:
        for sel in find_runs(run & (vi < 0.3), t, 8.0):
            tt, rr = t[sel], rpm[:, sel]
            tg = np.arange(tt[0], tt[-1], 1 / fs)
            g = np.vstack([np.interp(tg, tt, rr[k]) for k in range(4)])
            f_hi = min(5.0, 0.45 * fs)
            amps = [band_amp(g[k] / g[k].mean() - 1, fs, 0.3, f_hi) for k in range(4)]
            wind_rows.append(dict(tag=tag, dur=float(tg[-1] - tg[0]), fs=fs,
                                  tilt_deg=float(np.mean(ti[sel])),
                                  tilt_p90=float(np.percentile(ti[sel], 90)),
                                  amp=float(np.nanmean(amps)),
                                  base_rpm=float(g.mean())))
    # ---- (나) 수직 기동: 공통 rpm 계단 ---------------------------------
    step_rows = []
    mean_rpm = rpm.mean(axis=0)
    for sel in find_runs(run & (np.abs(vzi) > 1.0), t, 2.0):
        seg = mean_rpm[sel]
        base = np.median(mean_rpm[run])
        step_rows.append(dict(tag=tag, dur=float(t[sel][-1] - t[sel][0]),
                              d_rpm_pct=float((seg.max() - seg.min()) / base * 100),
                              rate_pct_s=float((seg.max() - seg.min()) / base * 100 /
                                               max(t[sel][-1] - t[sel][0], 1e-6)),
                              vz_max=float(np.abs(vzi[sel]).max())))
    return wind_rows, step_rows


W, S = [], []
files = [(f"{DL}/{f}", f[:8]) for f in sorted(os.listdir(DL))]
files += [(f"{RAW}/fe7c9eed-8dff-4283-a2a0-117185b41505.ulg", "px4_s500"),
          (f"{RAW}/1e858ce3-07df-4a9f-9336-7670c953874f.ulg", "px4_race")]
for p, tag in files:
    w, s = analyse(p, tag)
    W += w
    S += s
print(f"호버 창 {len(W)}개 (기체 {len({r['tag'] for r in W})}) · 수직기동 구간 {len(S)}개")

if W:
    a = np.array([r["amp"] for r in W]) * 100
    ti = np.array([r["tilt_deg"] for r in W])
    ok = np.isfinite(a) & np.isfinite(ti)
    a, ti = a[ok], ti[ok]
    from scipy import stats
    r_p = stats.pearsonr(ti, a)
    r_s = stats.spearmanr(ti, a)
    print("\n(가) 호버 기울기(바람 대리값) vs 흔들림 등가사인 진폭")
    print(f"   n={len(a)}  Pearson r={r_p.statistic:+.3f} (p={r_p.pvalue:.2g}) · "
          f"Spearman ρ={r_s.statistic:+.3f} (p={r_s.pvalue:.2g})")
    sl, ic = np.polyfit(ti, a, 1)
    print(f"   회귀: 흔들림[%] = {ic:.2f} + {sl:.3f}·기울기[deg]")
    for lo, hi in [(0, 2), (2, 4), (4, 6), (6, 90)]:
        m = (ti >= lo) & (ti < hi)
        if m.sum() >= 3:
            print(f"   기울기 {lo}–{hi}°: n={m.sum():3d}  흔들림 중앙 {np.median(a[m]):.2f} %")
if S:
    d = np.array([r["d_rpm_pct"] for r in S])
    rt = np.array([r["rate_pct_s"] for r in S])
    print("\n(나) 수직 기동 중 **네 로터 공통** rpm 계단")
    print(f"   n={len(S)}  진폭 중앙 {np.median(d):.1f} %  p90 {np.percentile(d,90):.1f} %  "
          f"최대 {d.max():.1f} %")
    print(f"   변화율 중앙 {np.median(rt):.1f} %/s  p90 {np.percentile(rt,90):.1f} %/s")
    print("   ⛔우리 모델은 평균 rpm 이 상수라 이 성분이 원리적으로 0 이다.")
json.dump(dict(wind=W, steps=S), open(f"{HERE}/wind_steps.json", "w"), indent=1)
