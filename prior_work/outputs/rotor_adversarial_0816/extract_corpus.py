# -*- coding: utf-8 -*-
"""로터 rpm 실측 코퍼스 추출 — 적대적 검증 1단계 (2026-08-16)

원시 사본 5종(PX4 .ulg 2 · DREGON .mat 3)에서 «호버/준정상» 구간을 뽑아
균일 격자 rpm (4, N) 로 저장한다. 창 규약은 outputs/rotor_rpm_web_anchor.json
method_note 그대로: |v|<0.3 m/s(PX4), 최소 3 s.

DREGON 은 속도 신호가 이 사본에 없다 → «모터 전부 가동 + 창 내 전체평균의
느린 추세가 작은» 준정상 구간을 대신 쓴다(그 사실을 라벨에 적는다).
"""
import json
import os

import numpy as np
import scipy.io
from pyulog import ULog

RAW = "/workspace/sionna/prior_work/outputs/rotor_jitter_raw"
OUT = os.path.dirname(os.path.abspath(__file__))
LOG_S500 = "fe7c9eed-8dff-4283-a2a0-117185b41505"
LOG_RACE = "1e858ce3-07df-4a9f-9336-7670c953874f"


def find_runs(mask, t, min_dur, max_gap=0.5, strict=True):
    idx = np.where(mask)[0]
    if len(idx) == 0:
        return []
    cond = np.diff(t[idx]) > max_gap
    if strict:
        cond = cond | (np.diff(idx) > 1)
    brk = np.where(cond)[0]
    return [s for s in np.split(idx, brk + 1) if t[s[-1]] - t[s[0]] >= min_dur]


def regrid(t, rpm, sel, fs):
    tt = t[sel]
    tg = np.arange(tt[0], tt[-1], 1.0 / fs)
    return np.vstack([np.interp(tg, tt, rpm[k, sel]) for k in range(4)]), tg


def load_ulg(name):
    u = ULog(f"{RAW}/{name}.ulg",
             message_name_filter_list=["esc_status", "vehicle_local_position"])
    esc = [d for d in u.data_list if d.name == "esc_status"][0]
    lp = [d for d in u.data_list if d.name == "vehicle_local_position"][0]
    t = esc.data["timestamp"] / 1e6
    rpm = np.vstack([esc.data[f"esc[{i}].esc_rpm" ] for i in range(4)]).astype(float)
    tl = lp.data["timestamp"] / 1e6
    v = np.sqrt(lp.data["vx"] ** 2 + lp.data["vy"] ** 2 + lp.data["vz"] ** 2)
    return t, rpm, np.interp(t, tl, v)


segs = {}          # key -> dict(rpm=(4,N), fs, label, kind)
meta = []


# ---------------------------------------------------------------- PX4 S500
t, rpm, vi = load_ulg(LOG_S500)
fs_raw = float(1.0 / np.median(np.diff(t)))
med = np.median(rpm[rpm > 0])
running = (rpm > 0.5 * med).all(axis=0)
hover = running & (vi < 0.3)
runs = find_runs(hover, t, 3.0)
fs = 10.0
n = 0
for i, sel in enumerate(runs):
    g, tg = regrid(t, rpm, sel, fs)
    if g.shape[1] < 64:
        continue
    # 613 s 연속 호버는 30 s 타일로 쪼갠다(분포 통계용 독립 표본)
    tile = int(30 * fs)
    for j in range(g.shape[1] // tile):
        segs[f"px4_s500_r{i}_t{j}"] = dict(rpm=g[:, j * tile:(j + 1) * tile], fs=fs)
        n += 1
    if g.shape[1] < tile:
        segs[f"px4_s500_r{i}_t0"] = dict(rpm=g, fs=fs)
        n += 1
meta.append(dict(source="px4_s500_fe7c9eed", vehicle="S500 quad (Pixhawk 6C, bidir DShot300)",
                 signal="esc_status.esc_rpm (measured)", fs_raw_hz=round(fs_raw, 2),
                 fs_grid_hz=fs, n_segments=n, tile_s=30.0,
                 window_rule="|v|<0.3 m/s & all motors running, >=3 s, 30 s tiles"))

# ---------------------------------------------------------------- PX4 racing
t, rpm, vi = load_ulg(LOG_RACE)
fs_raw = float(1.0 / np.median(np.diff(t)))
med = np.median(rpm[rpm > 0])
running = (rpm > 0.5 * med).all(axis=0)
hover = running & (vi < 0.3)
fs = 50.0
n_h = 0
for i, sel in enumerate(find_runs(hover, t, 2.0, strict=False)):
    g, tg = regrid(t, rpm, sel, fs)
    if g.shape[1] < 100:
        continue
    segs[f"px4_race_hover_r{i}"] = dict(rpm=g, fs=fs)
    n_h += 1
n_m = 0
for i, sel in enumerate(find_runs(running, t, 5.0, strict=False)):
    g, tg = regrid(t, rpm, sel, fs)
    tile = int(10 * fs)
    for j in range(g.shape[1] // tile):
        segs[f"px4_race_manv_r{i}_t{j}"] = dict(rpm=g[:, j * tile:(j + 1) * tile], fs=fs)
        n_m += 1
meta.append(dict(source="px4_race_1e858ce3", vehicle="racing quad (KakuteH7, DShot150)",
                 signal="esc_status.esc_rpm (measured)", fs_raw_hz=round(fs_raw, 2),
                 fs_grid_hz=fs, n_segments_hover=n_h, n_segments_maneuver=n_m,
                 window_rule="hover=|v|<0.3 m/s >=2 s (rare: median |v| is 2.19 m/s -> this log is "
                             "NOT a hover log); maneuver=all motors running, 10 s tiles"))

# ---------------------------------------------------------------- DREGON
def dregon(fname, field):
    d = scipy.io.loadmat(f"{RAW}/{fname}.mat")["motor"][0, 0]
    ts = np.asarray(d["timestamps"]).ravel()
    x = np.asarray(d[field]).T          # (4, N)
    return ts, x

for fname, field, tag in [("dregon_hover_motors", "command", "cmd"),
                          ("dregon_ff_room1_motors", "command", "cmd"),
                          ("dregon_ff_room1_motors", "measured", "meas"),
                          ("dregon_ff_motors", "command", "cmd")]:
    ts, x = dregon(fname, field)
    fs_raw = float(1.0 / np.median(np.diff(ts)))
    on = (x > 0.4 * np.median(x[x > 0])).all(axis=0)
    # 준정상: 4모터 평균의 2 s 이동평균 기울기가 작다
    fs = 100.0
    runs = find_runs(on, ts, 5.0)
    n = 0
    for i, sel in enumerate(runs):
        g, tg = regrid(ts, x, sel, fs)
        if g.shape[1] < 256:
            continue
        m = g.mean(axis=0)
        w = int(2 * fs)
        sm = np.convolve(m, np.ones(w) / w, mode="same")
        slope = np.abs(np.gradient(sm, 1.0 / fs)) / m.mean()      # 상대 기울기 [1/s]
        ok = slope < 0.03                                          # 3 %/s 미만
        for sub in find_runs(ok, tg, 6.0):
            gg = g[:, sub]
            tile = int(10 * fs)
            for j in range(max(1, gg.shape[1] // tile)):
                seg = gg[:, j * tile:(j + 1) * tile]
                if seg.shape[1] < 256:
                    continue
                segs[f"dregon_{fname.split('_',1)[1]}_{tag}_r{i}_{len(segs)}"] = dict(rpm=seg, fs=fs)
                n += 1
    meta.append(dict(source=f"dregon:{fname}:{field}", vehicle="MikroKopter quad",
                     signal=f"rotor speed [rps] ({field})", fs_raw_hz=round(fs_raw, 1),
                     fs_grid_hz=fs, n_segments=n,
                     window_rule="all motors on & |d(mean)/dt|/mean < 1 %/s for >=8 s, 20 s tiles; "
                                 "NO velocity signal in this copy -> quasi-steady proxy"))

print(json.dumps(meta, indent=1, ensure_ascii=False))
print("total segments:", len(segs))
for k, v in list(segs.items())[:5]:
    print(" ", k, v["rpm"].shape, v["fs"])

np.savez_compressed(f"{OUT}/rotor_corpus.npz",
                    **{f"{k}__rpm": v["rpm"] for k, v in segs.items()},
                    **{f"{k}__fs": np.array([v["fs"]]) for k, v in segs.items()})
with open(f"{OUT}/rotor_corpus_meta.json", "w", encoding="utf-8") as fh:
    json.dump(dict(meta=meta, segments={k: dict(shape=list(v["rpm"].shape), fs=v["fs"])
                                        for k, v in segs.items()}), fh,
              indent=1, ensure_ascii=False)
