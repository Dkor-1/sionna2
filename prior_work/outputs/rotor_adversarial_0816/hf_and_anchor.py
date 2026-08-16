# -*- coding: utf-8 -*-
"""(가) 고속 로그로 «흔들림의 고주파 몫» 상한 재기 — 우리 OU 는 5 Hz 위가 사실상 0.
(나) **모델 없는 앵커** — 창 안 상대 rms. 빗살 넓힘은 이 값에만 걸린다(OU 가정 불필요).
"""
import json
import os

import numpy as np
from pyulog import ULog
from scipy.signal import welch

HERE = os.path.dirname(os.path.abspath(__file__))
DL = f"{HERE}/px4_logs"
RAW = "/workspace/sionna/prior_work/outputs/rotor_jitter_raw"


def find_runs(mask, t, min_dur):
    idx = np.where(mask)[0]
    if not len(idx):
        return []
    brk = np.where((np.diff(t[idx]) > 0.5) | (np.diff(idx) > 1))[0]
    return [s for s in np.split(idx, brk + 1) if t[s[-1]] - t[s[0]] >= min_dur]


def load(path):
    u = ULog(path, message_name_filter_list=["esc_status", "vehicle_local_position"])
    n = {d.name for d in u.data_list}
    if not {"esc_status", "vehicle_local_position"} <= n:
        return None
    esc = [d for d in u.data_list if d.name == "esc_status"][0]
    if "esc[3].esc_rpm" not in esc.data:
        return None
    t = esc.data["timestamp"] / 1e6
    rpm = np.vstack([esc.data[f"esc[{i}].esc_rpm"] for i in range(4)]).astype(float)
    if np.nanmax(rpm) < 1500:
        return None
    lp = [d for d in u.data_list if d.name == "vehicle_local_position"][0]
    tl = lp.data["timestamp"] / 1e6
    v = np.sqrt(lp.data["vx"] ** 2 + lp.data["vy"] ** 2 + lp.data["vz"] ** 2)
    return t, rpm, np.interp(t, tl, v), float(1 / np.median(np.diff(t)))


# ---------------- (가) 고주파 몫 ------------------------------------------
print("### (가) 표집률 ≥40 Hz 로그에서 흔들림 파워의 대역별 몫  [%]")
print(f"{'로그':10s}{'fs':>7s}{'창수':>5s}{'<0.5':>8s}{'0.5-2':>8s}{'2-5':>8s}"
      f"{'5-10':>8s}{'10-20':>8s}{'>20':>8s}")
files = [(f"{DL}/{f}", f[:8]) for f in sorted(os.listdir(DL))]
files += [(f"{RAW}/fe7c9eed-8dff-4283-a2a0-117185b41505.ulg", "s500")]
hf_rows = []
for p, tag in files:
    try:
        r = load(p)
    except Exception:
        r = None
    if r is None:
        continue
    t, rpm, vi, fs = r
    if fs < 40:
        continue
    med = np.median(rpm[rpm > 0])
    run = (rpm > 0.5 * med).all(axis=0)
    runs = find_runs(run & (vi < 0.3), t, 8.0)
    if not runs:
        continue
    fr = {k: [] for k in ["<0.5", "0.5-2", "2-5", "5-10", "10-20", ">20"]}
    for sel in runs:
        tt = t[sel]
        tg = np.arange(tt[0], tt[-1], 1 / fs)
        g = np.vstack([np.interp(tg, tt, rpm[k, sel]) for k in range(4)])
        eps = g / g.mean(axis=1, keepdims=True) - 1
        nps = int(min(eps.shape[1], 2 ** int(np.floor(np.log2(eps.shape[1])))))
        f, P = welch(eps, fs=fs, axis=1, nperseg=nps, detrend="constant")
        Pm = P.mean(axis=0)
        tot = np.trapezoid(Pm[f > 0], f[f > 0])
        for lbl, (a, b) in {"<0.5": (0, .5), "0.5-2": (.5, 2), "2-5": (2, 5),
                            "5-10": (5, 10), "10-20": (10, 20),
                            ">20": (20, 0.45 * fs)}.items():
            m = (f > a) & (f <= b)
            fr[lbl].append(float(np.trapezoid(Pm[m], f[m]) / tot) if m.sum() > 1 else 0.0)
    row = {k: 100 * np.median(v) for k, v in fr.items()}
    hf_rows.append(dict(tag=tag, fs=fs, n=len(runs), **row))
    print(f"{tag:10s}{fs:7.0f}{len(runs):5d}" + "".join(f"{row[k]:8.1f}" for k in fr))

if hf_rows:
    print(f"{'중앙':10s}{'':7s}{'':5s}" + "".join(
        f"{np.median([r[k] for r in hf_rows]):8.1f}"
        for k in ["<0.5", "0.5-2", "2-5", "5-10", "10-20", ">20"]))
print("⭐우리 OU(τ=0.227 s)의 같은 몫: ", end="")
tau = 0.227
def ou_frac(a, b):
    return (2 / np.pi) * (np.arctan(2 * np.pi * b * tau) - np.arctan(2 * np.pi * a * tau))
tot = ou_frac(0.0, 100.0)
print("".join(f"{100*ou_frac(a,b)/tot:8.1f}" for a, b in
               [(0, .5), (.5, 2), (2, 5), (5, 10), (10, 20), (20, 100)]))
tau = 1.04
print("   τ=1.04 s 로 고치면:      ", end="")
tot = ou_frac(0.0, 100.0)
print("".join(f"{100*ou_frac(a,b)/tot:8.1f}" for a, b in
               [(0, .5), (.5, 2), (2, 5), (5, 10), (10, 20), (20, 100)]))

# ---------------- (나) 모델 없는 앵커 --------------------------------------
print()
print("### (나) 모델 없는 앵커 — 창 안 상대 rms [%] (빗살 퍼짐 = m·f_flash·이 값)")
for win, fs_min in [(1.0, 9.0), (0.25, 45.0)]:
    vals = {}
    for p, tag in files:
        try:
            r = load(p)
        except Exception:
            r = None
        if r is None:
            continue
        t, rpm, vi, fs = r
        if fs < fs_min:
            continue
        med = np.median(rpm[rpm > 0])
        run = (rpm > 0.5 * med).all(axis=0)
        acc = []
        for sel in find_runs(run & (vi < 0.3), t, 4.0):
            tt = t[sel]
            tg = np.arange(tt[0], tt[-1], 1 / fs)
            g = np.vstack([np.interp(tg, tt, rpm[k, sel]) for k in range(4)])
            w = int(win * fs)
            if w < 4:
                continue
            for j in range(g.shape[1] // w):
                seg = g[:, j * w:(j + 1) * w]
                e = seg / seg.mean(axis=1, keepdims=True) - 1
                acc.append(float(e.std()))
        if acc:
            vals[tag] = float(np.median(acc)) * 100
    if vals:
        a = np.array(list(vals.values()))
        print(f" 창 {win:4.2f} s (fs≥{fs_min:g} Hz, 기체 {len(a)}대): "
              f"중앙 {np.median(a):.2f} %  p25 {np.percentile(a,25):.2f}  "
              f"p75 {np.percentile(a,75):.2f}  범위 {a.min():.2f}–{a.max():.2f}")
        print("    " + "  ".join(f"{k}:{v:.2f}" for k, v in sorted(vals.items())))
json.dump(hf_rows, open(f"{HERE}/hf_rows.json", "w"), indent=1)
