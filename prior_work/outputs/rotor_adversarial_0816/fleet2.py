# -*- coding: utf-8 -*-
"""④ 프리셋 백분위 — 품질 게이트 붙인 판.

1차 판의 오류(스스로 적발): 내려받은 함대 17기 중 **5기가 PX4_SITL(시뮬 기체)** 였고
그 로그의 rpm 은 769 처럼 비물리적이거나 완전 대칭이라 «실기체 분포» 에 섞으면 안 된다.
여기서는 sys_hw 로 SITL 을 갈라내고, rpm 물리 범위(1500–20000)도 건다.

또 하나: σ_w 를 «등가사인 → OU 대역몫 F» 로 환산하면 **OU 가 맞다는 가정**이 들어간다.
이번 라운드가 그 가정을 흔들었으므로, 환산 없는 **대역 등가사인 진폭**도 나란히 낸다.
"""
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, "/workspace/sionna/src")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rotor_dynamics as rd     # noqa: E402
import rstats                    # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
F_LO, F_HI_NOM = 0.3, 5.0

HW = {}
for d in json.load(open(f"{HERE}/esc_pick.json")):
    HW[d["log_id"][:8]] = dict(hw=d.get("sys_hw") or "", af=d.get("airframe_name") or "",
                               date=d.get("log_date"), dur=d.get("duration_s"))
HW["px4_s500"] = dict(hw="PIXHAWK6C", af="S500", date="known", dur=626)
HW["px4_race"] = dict(hw="KAKUTEH7", af="racing", date="known", dur=64)
HW["dregon_cmd"] = dict(hw="MIKROKOPTER", af="DREGON(cmd)", date="2017", dur=64)
HW["dregon_meas"] = dict(hw="MIKROKOPTER", af="DREGON(meas)", date="2018", dur=64)


def sigma_w_from_amp(amp, f1, f2, T=rd.TAU_CTL_S):
    F = (2 / math.pi) * (math.atan(2 * math.pi * f2 * T) - math.atan(2 * math.pi * f1 * T))
    return amp / math.sqrt(2.0) / math.sqrt(F), F


def collect(npz, tagger):
    z = np.load(npz)
    out = []
    for k in sorted({x.split("__")[0] for x in z.files}):
        rpm, fs = z[f"{k}__rpm"], float(z[f"{k}__fs"][0])
        f_hi = min(F_HI_NOM, 0.45 * fs)
        if f_hi <= F_LO + 0.2:
            continue
        st = rstats.full(rpm, fs, band=(F_LO, f_hi))
        amp = st.get("band_amp_equiv_sine_rel")
        if amp is None or not np.isfinite(amp):
            continue
        sw, F = sigma_w_from_amp(amp, F_LO, f_hi)
        v = tagger(k)
        h = HW.get(v, {})
        out.append(dict(key=k, vehicle=v, hw=h.get("hw", "?"), af=h.get("af", ""),
                        fs=fs, dur_s=st["dur_s"], sigma_s=st["static_std_rel"],
                        amp=amp, sigma_w=sw, band_hz=[F_LO, f_hi],
                        base_rpm=st["base_rpm"], wob_total=st["wobble_std_rel"],
                        pair_corr=st["pair_corr_mean"],
                        common_share=st["common_mode_share"],
                        uniform_share=st["uniform_mode_share"],
                        split_share=st.get("static_best_split_share"),
                        kurt=st["excess_kurtosis"], acf_tau=st.get("acf_exp_tau_s"),
                        ou_fc=st.get("ou_fc_hz"), alpha=st.get("powerlaw_alpha"),
                        ou_fit_rms=st.get("ou_fit_rms_db")))
    return out


rows = collect(f"{HERE}/px4_fleet_corpus.npz", lambda k: k.split("_r")[0])
rows += collect(f"{HERE}/rotor_corpus.npz",
                lambda k: ("px4_s500" if k.startswith("px4_s500") else
                           "px4_race" if "race" in k else
                           "dregon_meas" if "_meas_" in k else "dregon_cmd"))

sitl = [r for r in rows if "SITL" in r["hw"].upper()]
real = [r for r in rows if "SITL" not in r["hw"].upper()]
bad = [r for r in real if not (1500 <= r["base_rpm"] <= 20000) and r["vehicle"] not in
       ("dregon_cmd", "dregon_meas")]
real = [r for r in real if r not in bad and "race" not in r["vehicle"]]
print(f"세그먼트 총 {len(rows)} → SITL {len(sitl)}(기체 {len({r['vehicle'] for r in sitl})}) · "
      f"비물리 rpm 제외 {len(bad)} · **실기체 호버 {len(real)}**"
      f"(기체 {len({r['vehicle'] for r in real})})")


def pct(vals, x):
    v = np.sort(np.asarray(vals, float))
    return float(100.0 * np.searchsorted(v, x, side="right") / len(v))


def report(R, label, keys=(("sigma_s", "σ_s"), ("sigma_w", "σ_w(OU환산)"), ("amp", "대역등가사인"))):
    if not R:
        return
    veh = sorted({r["vehicle"] for r in R})
    print("=" * 96)
    print(f"### {label}  세그먼트 {len(R)} · 기체 {len(veh)}")
    for wname, W in [("세그먼트", None), ("기체(중앙값 1표)", veh)]:
        print(f"-- {wname} 가중")
        for fld, nm in keys:
            a = (np.array([np.median([r[fld] for r in R if r["vehicle"] == v]) for v in W])
                 if W else np.array([r[fld] for r in R])) * 100
            print(f"   {nm:12s} 중앙 {np.median(a):5.2f}  p10 {np.percentile(a,10):5.2f}"
                  f"  p25 {np.percentile(a,25):5.2f}  p75 {np.percentile(a,75):5.2f}"
                  f"  p90 {np.percentile(a,90):5.2f}  범위 {a.min():.2f}–{a.max():.2f}")
        S = ([np.median([r["sigma_s"] for r in R if r["vehicle"] == v]) for v in W] if W
             else [r["sigma_s"] for r in R])
        Wq = ([np.median([r["sigma_w"] for r in R if r["vehicle"] == v]) for v in W] if W
              else [r["sigma_w"] for r in R])
        print(f"   ⭐백분위  outdoor(2.35/2.45): σ_s {pct(S,0.0235):5.1f}%ile · "
              f"σ_w {pct(Wq,0.0245):5.1f}%ile   |   indoor(0.54/0.65): "
              f"σ_s {pct(S,0.0054):5.1f}%ile · σ_w {pct(Wq,0.0065):5.1f}%ile   |   "
              f"legacy σ_s 0.22 %: {pct(S,0.0022):5.1f}%ile")


report(real, "실기체 호버 (SITL·비물리 제외)")
report([r for r in real if r["fs"] >= 9.0], "실기체 호버 · 표집률 ≥9 Hz (σ_w 를 믿을 수 있는 것)")
report(sitl, "PX4 SITL (시뮬 기체) — 대조군")

print("=" * 96)
print("### 기체별 (실기체 호버)")
print(f"{'기체':10s}{'hw':17s}{'n':>3s}{'fs':>6s}{'rpm':>7s}{'σ_s%':>7s}{'σ_w%':>7s}"
      f"{'쌍상관':>7s}{'공통몫':>7s}{'균일몫':>7s}{'쌍분할':>7s}{'ACFτ':>7s}{'OUfc':>7s}{'α':>6s}")
for v in sorted({r["vehicle"] for r in real}):
    R = [r for r in real if r["vehicle"] == v]

    def m(f):
        x = [r[f] for r in R if r[f] is not None and np.isfinite(r[f])]
        return np.median(x) if x else np.nan
    print(f"{v[:9]:10s}{R[0]['hw'][:16]:17s}{len(R):3d}{m('fs'):6.0f}{m('base_rpm'):7.0f}"
          f"{m('sigma_s')*100:7.2f}{m('sigma_w')*100:7.2f}{m('pair_corr'):7.2f}"
          f"{m('common_share'):7.2f}{m('uniform_share'):7.2f}{m('split_share'):7.2f}"
          f"{m('acf_tau'):7.2f}{m('ou_fc'):7.2f}{m('alpha'):6.2f}")

json.dump(dict(real=real, sitl=sitl, excluded=bad), open(f"{HERE}/fleet_rows.json", "w"), indent=1)
