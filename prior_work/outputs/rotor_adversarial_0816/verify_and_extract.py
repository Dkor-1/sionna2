# -*- coding: utf-8 -*-
"""내려받은 PX4 로그 70건을 실제로 파싱해 ① esc_status 유무 ② 회전수 유효성 ③ 호버 창 추출.

⚠1차 «앞머리 문자열» 필터의 적중률(32~39 %)은 **믿을 수 없다** — PX4 는 구독하지 않은
토픽의 포맷 정의도 앞머리에 적기 때문이다. 여기서 pyulog 로 파싱해 **진짜 유효율**을 센다.
"""
import concurrent.futures as cf
import json
import os

import numpy as np
from pyulog import ULog

HERE = os.path.dirname(os.path.abspath(__file__))
DL = f"{HERE}/px4_logs"
V_HOVER, MIN_DUR, TILE_S = 0.3, 3.0, 20.0


def find_runs(mask, t, min_dur, max_gap=0.5):
    idx = np.where(mask)[0]
    if len(idx) == 0:
        return []
    brk = np.where((np.diff(t[idx]) > max_gap) | (np.diff(idx) > 1))[0]
    return [s for s in np.split(idx, brk + 1) if t[s[-1]] - t[s[0]] >= min_dur]


def one(fn):
    path = f"{DL}/{fn}"
    rec = {"log": fn[:-4], "ok": False, "reason": "", "segments": []}
    try:
        u = ULog(path, message_name_filter_list=["esc_status", "vehicle_local_position"])
    except Exception as e:
        rec["reason"] = f"parse:{type(e).__name__}"
        return rec, {}
    names = {d.name for d in u.data_list}
    if "esc_status" not in names:
        rec["reason"] = "no esc_status topic"
        return rec, {}
    esc = [d for d in u.data_list if d.name == "esc_status"][0]
    have = [i for i in range(8) if f"esc[{i}].esc_rpm" in esc.data]
    if len(have) < 4:
        rec["reason"] = f"only {len(have)} esc fields"
        return rec, {}
    t = esc.data["timestamp"] / 1e6
    rpm = np.vstack([esc.data[f"esc[{i}].esc_rpm"] for i in have[:4]]).astype(float)
    if np.nanmax(rpm) < 500:
        rec["reason"] = "esc_rpm all ~0 (telemetry not wired)"
        return rec, {}
    fs = float(1.0 / np.median(np.diff(t)))
    rec["fs_hz"] = round(fs, 2)
    rec["max_rpm"] = float(np.nanmax(rpm))
    if "vehicle_local_position" not in names:
        rec["reason"] = "esc ok but no local_position"
        rec["ok"] = True
        return rec, {}
    lp = [d for d in u.data_list if d.name == "vehicle_local_position"][0]
    tl = lp.data["timestamp"] / 1e6
    v = np.sqrt(lp.data["vx"] ** 2 + lp.data["vy"] ** 2 + lp.data["vz"] ** 2)
    vi = np.interp(t, tl, v)
    med = np.median(rpm[rpm > 0])
    running = (rpm > 0.5 * med).all(axis=0)
    hover = running & (vi < V_HOVER)
    segs = {}
    fs_g = min(50.0, max(4.0, round(fs)))
    for i, sel in enumerate(find_runs(hover, t, MIN_DUR)):
        tt = t[sel]
        tg = np.arange(tt[0], tt[-1], 1.0 / fs_g)
        if len(tg) < int(8 * fs_g):
            continue
        g = np.vstack([np.interp(tg, tt, rpm[k, sel]) for k in range(4)])
        tile = int(TILE_S * fs_g)
        n_tile = max(1, g.shape[1] // tile)
        for j in range(n_tile):
            seg = g[:, j * tile:(j + 1) * tile] if g.shape[1] >= tile else g
            if seg.shape[1] < int(8 * fs_g):
                continue
            segs[f"{fn[:-4][:8]}_r{i}t{j}"] = (seg, fs_g)
    rec["ok"] = True
    rec["n_hover_seg"] = len(segs)
    rec["hover_frac"] = float(hover.mean())
    return rec, segs


files = sorted(os.listdir(DL))
recs, allsegs = [], {}
with cf.ThreadPoolExecutor(max_workers=16) as ex:
    for rec, segs in ex.map(one, files):
        recs.append(rec)
        allsegs.update(segs)
        print(rec["log"][:8], rec["ok"], rec.get("reason", ""), rec.get("fs_hz", ""),
              rec.get("n_hover_seg", 0), flush=True)

ok = [r for r in recs if r["ok"]]
print(f"\nPARSED {len(recs)}  REAL esc_rpm {len(ok)}  ({len(ok)/len(recs):.1%})")
print("with hover segments:", len([r for r in ok if r.get("n_hover_seg", 0) > 0]))
print("total hover segments:", len(allsegs))
np.savez_compressed(f"{HERE}/px4_fleet_corpus.npz",
                    **{f"{k}__rpm": v[0] for k, v in allsegs.items()},
                    **{f"{k}__fs": np.array([v[1]]) for k, v in allsegs.items()})
json.dump(recs, open(f"{HERE}/px4_fleet_records.json", "w"), indent=1)
