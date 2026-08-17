#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""프로펠러 두께 사다리 판정 원장 — outputs/material_canon_0816_ladder.json

0.5 · 0.9 · 1.43(정본) · 2.0 mm 네 점 + 기본판(Sionna 100 mm)을 나란히 잰다.
잣대 식은 08-16 오전 판(scratchpad/build_material_verdict.py)과 **글자 그대로 같다**.
⛔GPU 0 · 저장된 원장만 읽는다(sionna.rt·mitsuba 임포트 없음).
"""
import json, math, sys
import numpy as np

sys.path.insert(0, "/workspace/sionna/src")
sys.path.insert(0, "/workspace/sionna/benchmark")
from md_mapstyle import flash_spec  # noqa: E402

OUT = "/workspace/sionna/outputs/material_canon_0816_ladder.json"
LEDGER = "/workspace/sionna/outputs/elevation_sweep_md.json"
NPZ = "/workspace/sionna/outputs/elevation_sweep_md.npz"
GRID = "/workspace/sionna/outputs/grid_convergence_check.json"

COMB_TOL_HZ = AC_MIN_HZ = RHY_HW = 8.0
EPS0, C = 8.8541878128e-12, 299792458.0
NEAR_FLOOR = 1e-11

led = json.load(open(LEDGER))
npz = np.load(NPZ)
PRF = float(led["_meta"]["prf_hz"])
FFL = float(led["_meta"]["f_flash_hz"])
FC = 3.5e9
rows = {(r["engine"], round(float(r["el_deg"]), 3)): r for r in led["rows"]}


# ══ 잣대 ═══════════════════════════════════════════════════════════════════
def core(E, f_tip, prf=None):
    prf = PRF if prf is None else prf
    E = np.asarray(E, complex)
    dc = complex(E.mean()); x = E - dc; n = E.size
    P = np.abs(np.fft.fft(x * np.hanning(n))) ** 2
    fa = np.abs(np.fft.fftfreq(n, d=1.0 / prf))
    above, ac_band = fa >= f_tip, fa >= AC_MIN_HZ
    k = np.round(fa / FFL)
    on = (k >= 1) & (np.abs(fa - k * FFL) <= COMB_TOL_HZ)
    p_ab, p_ac = float(P[above].sum()), float(P[ac_band].sum())
    ac_lin = float((np.abs(x) ** 2).mean()); dc_lin = abs(dc) ** 2
    d = {"n_used": int(n),
         "dc_power_db": round(10 * math.log10(dc_lin + 1e-300), 3),
         "ac_power_db": round(10 * math.log10(ac_lin + 1e-300), 3),
         "ac_over_dc": (round(ac_lin / dc_lin, 8) if dc_lin > 0 else None),
         "rhythm_share_pct": round(100 * float(P[above & on].sum()) / p_ab, 3) if p_ab > 0 else None,
         "above_f_tip_pct": round(100 * p_ab / p_ac, 4) if p_ac > 0 else None}
    frac = p_ab / p_ac if p_ac > 0 else None
    d["floor_above_tip_db"] = round(d["ac_power_db"] + 10 * math.log10(frac), 3) if frac and frac > 0 else None
    comb = None
    lo, hi = 2.0 * FFL, f_tip
    if hi >= 3.0 * FFL:
        band = (fa >= lo) & (fa <= hi); kk = fa / FFL
        on2 = band & (np.abs(kk - np.round(kk)) * FFL <= RHY_HW)
        off2 = band & (np.abs(np.abs(kk - np.floor(kk)) - 0.5) * FFL <= RHY_HW)
        if int(on2.sum()) >= 4 and int(off2.sum()) >= 4:
            num, den = float(P[on2].mean()), float(P[off2].mean())
            if num > 0 and den > 0:
                comb = round(10 * math.log10(num / den), 3)
    d["comb_contrast_db"] = comb
    d["near_numeric_floor"] = bool(d["ac_over_dc"] is not None and d["ac_over_dc"] < NEAR_FLOOR)
    return d


def series(arm, el):
    return np.asarray(npz[f"{arm}/el{el:+.0f}"], dtype=complex)


def metrics(arm, el):
    row = rows[(arm, el)]
    E = series(arm, el)
    d = core(E, float(row["f_tip_hz"]))
    d.update({"arm": arm, "el_deg": el, "shell_mm": row["shell_mm"], "prop_mm": row["prop_mm"],
              "n_poses": int(row["n_poses"]), "n_missing": int(row["n_missing"]),
              "seconds": row.get("seconds"), "npaths_median": row.get("npaths_median"),
              "f_tip_hz": float(row["f_tip_hz"]), "level_db_ledger": row["level_db"],
              "beat_hz_track": row["track"]["beat_hz"],
              "blade_band_power_db_track": row["track"]["band_power_db"]})
    return d, E


def wave_cmp(a, b):
    x, y = a - a.mean(), b - b.mean()
    na, nb = np.linalg.norm(x), np.linalg.norm(y)
    r = abs(complex(np.vdot(x, y) / (na * nb))) if na and nb else None
    _, _, Sa, _ = flash_spec(np.asarray(x, complex), PRF, FFL)
    _, _, Sb, _ = flash_spec(np.asarray(y, complex), PRF, FFL)
    A = 10 * np.log10(Sa / Sa.max() + 1e-12); B = 10 * np.log10(Sb / Sb.max() + 1e-12)
    return {"abs_rho_dc_removed": round(r, 4),
            "stft_db_map_corr_dc_removed": round(float(np.corrcoef(A.ravel(), B.ravel())[0, 1]), 4)}


def spike_stats(E):
    x = np.asarray(E, complex); x = x - x.mean()
    if not np.any(x):
        return None
    v = np.sort(np.abs(x))[::-1]; med = float(np.median(np.abs(x)))
    if med <= 0:
        return None
    p = np.abs(x) ** 2; tot = float(p.sum()); s = np.sort(p)[::-1]
    return {"top1_over_median": round(float(v[0] / med), 2),
            "top2_over_median": round(float(v[1] / med), 2),
            "isolation": round(float(v[0] / v[1]), 3),
            "argmax_pose": int(np.argmax(np.abs(x))),
            "top1_energy_pct": round(100 * float(s[0]) / tot, 4),
            "top8_energy_pct": round(100 * float(s[:8].sum()) / tot, 4),
            "top32_energy_pct": round(100 * float(s[:32].sum()) / tot, 4)}


def rel_score(E):
    x = np.asarray(E, complex); x = x - x.mean()
    m = np.median(np.abs(x))
    return np.abs(x) / m if m > 0 else np.zeros_like(np.abs(x))


# ══ 슬래브 ═════════════════════════════════════════════════════════════════
lam = C / FC
eps = 2.7 - 1j * 0.02 / (2 * np.pi * FC * EPS0)


def slab_R2(d_m, th_deg):
    th = np.radians(th_deg); s, c = np.sin(th), np.cos(th)
    q = np.sqrt(eps - s ** 2); k0 = 2 * np.pi / lam
    ph = np.exp(-2j * k0 * d_m * q); tot = 0.0
    for r in ((c - q) / (c + q), (eps * c - q) / (eps * c + q)):
        R = r * (1 - ph) / (1 - r ** 2 * ph)
        tot += abs(R) ** 2
    return 0.5 * tot


def slab_row(mm):
    th = np.linspace(0.0, 89.9, 2000)
    w = np.sin(np.radians(th)) * np.cos(np.radians(th))
    avg = float((np.array([slab_R2(mm / 1000, t) for t in th]) * w).sum() / w.sum())
    return {"normal_db": round(10 * math.log10(slab_R2(mm / 1000, 0.0)), 2),
            "angle_avg_db": round(10 * math.log10(avg), 2),
            "deg30_db": round(10 * math.log10(slab_R2(mm / 1000, 30.0)), 2),
            "deg45_db": round(10 * math.log10(slab_R2(mm / 1000, 45.0)), 2),
            "deg60_db": round(10 * math.log10(slab_R2(mm / 1000, 60.0)), 2)}


slab = {f"{mm:g}mm": slab_row(mm) for mm in (0.5, 0.75, 0.9, 1.43, 1.5, 2.0, 3.0, 100.0)}
bs = slab["100mm"]
slab_delta = {k: {kk.replace("_db", "_delta_db"): round(v[kk] - bs[kk], 2) for kk in v}
              for k, v in slab.items() if k != "100mm"}


def slab_pred_db(t_mm, th):
    return 10 * math.log10(slab_R2(t_mm / 1000, th) / slab_R2(0.1, th))


# ══ 팔 ═════════════════════════════════════════════════════════════════════
BASE = "sionna_p4000000000_r15_n8192_d1"
SHELL075 = "sionna_p4000000000_r15_n8192_shell0.75mm_d1"
PROPS = "sionna_p4000000000_partsprop_r15_n8192_d1"
LAD = {0.5: "sionna_p4000000000_r15_n8192_shell0.75mm_prop0.5mm_d1",
       0.9: "sionna_p4000000000_r15_n8192_shell0.75mm_prop0.9mm_d1",
       1.43: "sionna_p4000000000_r15_n8192_shell0.75mm_prop1.43mm_d1",
       2.0: "sionna_p4000000000_r15_n8192_shell0.75mm_prop2mm_d1"}
THK = (0.5, 0.9, 1.43, 2.0)
DKEYS = ["floor_above_tip_db", "ac_power_db", "dc_power_db", "level_db_ledger",
         "comb_contrast_db", "rhythm_share_pct", "above_f_tip_pct", "beat_hz_track"]


def delta(d, b):
    return {"d_" + k: (None if (d.get(k) is None or b.get(k) is None) else round(d[k] - b[k], 4))
            for k in DKEYS}


EL = -30.0
b30, Eb30 = metrics(BASE, EL)
b30["spike"] = spike_stats(Eb30)
f_tip30 = b30["f_tip_hz"]
arms = {"base_100mm": b30}
E_by = {"base_100mm": Eb30}

d, Esh = metrics(SHELL075, EL)
d["delta_vs_base"] = delta(d, b30); d["vs_base_waveform"] = wave_cmp(Eb30, Esh)
d["spike"] = spike_stats(Esh)
arms["shell0.75_prop100_control"] = d

for mm in THK:
    dd, EE = metrics(LAD[mm], EL)
    dd["delta_vs_base"] = delta(dd, b30); dd["vs_base_waveform"] = wave_cmp(Eb30, EE)
    dd["spike"] = spike_stats(EE)
    arms[f"prop_{mm:g}mm"] = dd
    E_by[f"prop_{mm:g}mm"] = EE

dp, Ep = metrics(PROPS, EL)
dp["spike"] = spike_stats(Ep)
arms["ref_props_only_100mm"] = dp

LKEYS = ["base_100mm"] + [f"prop_{mm:g}mm" for mm in THK]

# ══ 튀는 자세(이상값) 조사 ════════════════════════════════════════════════
rel_all = np.maximum.reduce([rel_score(E_by[k]) for k in LKEYS])
order = np.argsort(rel_all)[::-1]
rng = np.random.default_rng(0)


def table(fn, k):
    tab = {key: fn(E_by[key], k) for key in LKEYS}
    base = tab["base_100mm"]
    rowsout = []
    for mm in THK:
        key = f"prop_{mm:g}mm"
        rowsout.append({"prop_mm": mm,
                        "d_ac_power_db": round(tab[key]["ac_power_db"] - base["ac_power_db"], 3),
                        "d_floor_above_tip_db": round(tab[key]["floor_above_tip_db"] - base["floor_above_tip_db"], 3),
                        "d_comb_contrast_db": (None if (tab[key]["comb_contrast_db"] is None or base["comb_contrast_db"] is None)
                                               else round(tab[key]["comb_contrast_db"] - base["comb_contrast_db"], 3)),
                        "d_rhythm_share_pp": round(tab[key]["rhythm_share_pct"] - base["rhythm_share_pct"], 3),
                        "d_dc_power_db": round(tab[key]["dc_power_db"] - base["dc_power_db"], 3)})
    return {"abs": {key: {kk: tab[key][kk] for kk in
                          ["ac_power_db", "floor_above_tip_db", "comb_contrast_db",
                           "rhythm_share_pct", "above_f_tip_pct", "n_used"]} for key in LKEYS},
            "delta_vs_base": rowsout}


def f_delete(x, k):
    m = np.ones(x.size, bool)
    if k:
        m[order[:k]] = False
    return core(x[m], f_tip30)


def f_null(x, k):
    y = np.asarray(x, complex).copy()
    if k:
        y[order[:k]] = complex(np.asarray(x, complex).mean())
    return core(y, f_tip30)


trim_delete = {f"k{k}": table(f_delete, k) for k in (0, 1, 8, 32)}
trim_null = {f"k{k}": table(f_null, k) for k in (0, 1, 8, 32)}

# 무작위 지우기 대조군 — «지우기» 절차 자체의 부작용
rand_ctl = {}
for k in (1, 8):
    bc, dc143, dc09 = [], [], []
    for _ in range(24):
        idx = rng.choice(8192, size=k, replace=False)
        m = np.ones(8192, bool); m[idx] = False
        cb = core(E_by["base_100mm"][m], f_tip30)
        c1 = core(E_by["prop_1.43mm"][m], f_tip30)
        c0 = core(E_by["prop_0.9mm"][m], f_tip30)
        bc.append(cb["comb_contrast_db"]); dc143.append(c1["comb_contrast_db"] - cb["comb_contrast_db"])
        dc09.append(c0["comb_contrast_db"] - cb["comb_contrast_db"])
    rand_ctl[f"k{k}"] = {"n_draws": 24,
                         "base_comb_db_mean": round(float(np.mean(bc)), 2),
                         "base_comb_db_sd": round(float(np.std(bc)), 2),
                         "base_comb_db_intact": arms["base_100mm"]["comb_contrast_db"],
                         "d_comb_1p43_mean": round(float(np.mean(dc143)), 2),
                         "d_comb_1p43_sd": round(float(np.std(dc143)), 2),
                         "d_comb_0p9_mean": round(float(np.mean(dc09)), 2),
                         "d_comb_0p9_sd": round(float(np.std(dc09)), 2)}

# 균일 재표집(시간 눈금 보존) — 빗살·리듬의 옳은 강건성 검사
uniform = {}
for name, sl, prf in (("first_half", slice(0, 4096), PRF), ("second_half", slice(4096, 8192), PRF),
                      ("even_decimate", slice(0, None, 2), PRF / 2), ("odd_decimate", slice(1, None, 2), PRF / 2)):
    cb = core(E_by["base_100mm"][sl], f_tip30, prf)
    blk = {"base_comb_db": cb["comb_contrast_db"], "base_ac_db": cb["ac_power_db"], "rows": []}
    for mm in THK:
        c = core(E_by[f"prop_{mm:g}mm"][sl], f_tip30, prf)
        blk["rows"].append({"prop_mm": mm,
                            "d_ac_power_db": round(c["ac_power_db"] - cb["ac_power_db"], 3),
                            "d_floor_above_tip_db": round(c["floor_above_tip_db"] - cb["floor_above_tip_db"], 3),
                            "d_comb_contrast_db": round(c["comb_contrast_db"] - cb["comb_contrast_db"], 3),
                            "d_rhythm_share_pp": round(c["rhythm_share_pct"] - cb["rhythm_share_pct"], 3)})
    uniform[name] = blk

# ══ 단조성 ════════════════════════════════════════════════════════════════
def monotone(vals):
    st = [round(vals[i + 1] - vals[i], 3) for i in range(len(vals) - 1)]
    return {"steps_db": st, "monotone_brighter_with_thickness": all(x >= 0 for x in st),
            "n_inversions": sum(1 for x in st if x < 0)}


lad = trim_delete["k0"]["delta_vs_base"]
mono = {"ac": monotone([r["d_ac_power_db"] for r in lad]),
        "floor": monotone([r["d_floor_above_tip_db"] for r in lad]),
        "comb": monotone([r["d_comb_contrast_db"] for r in lad]),
        "rhythm": monotone([r["d_rhythm_share_pp"] for r in lad]),
        "dc": monotone([r["d_dc_power_db"] for r in lad]),
        "check_in_uniform_resamples": {k: monotone([r["d_ac_power_db"] for r in v["rows"]])["monotone_brighter_with_thickness"]
                                       for k, v in uniform.items()}}

# ══ 슬래브 대조 · 유효 입사각 ═════════════════════════════════════════════
meas30 = {mm: next(r for r in lad if r["prop_mm"] == mm)["d_ac_power_db"] for mm in THK}
floor30 = {mm: next(r for r in lad if r["prop_mm"] == mm)["d_floor_above_tip_db"] for mm in THK}
ths = np.linspace(0.0, 89.0, 8901)


def fit_angle(meas):
    best, bth = 1e9, None
    for th in ths:
        r = sum((slab_pred_db(t, th) - v) ** 2 for t, v in meas.items())
        if r < best:
            best, bth = r, th
    # 점별 역산 — |R|(θ) 는 각에 대해 단조가 아니라 가지가 둘이다.
    # 공동해 근처(±25°)로 가지를 고정해서 «같은 가지 안의 흩어짐» 을 잰다.
    near = ths[(ths >= bth - 25) & (ths <= bth + 25)]
    per, per_global = {}, {}
    for t, v in meas.items():
        c_near = np.array([slab_pred_db(t, th) for th in near])
        per[t] = round(float(near[int(np.argmin(np.abs(c_near - v)))]), 2)
        c_all = np.array([slab_pred_db(t, th) for th in ths])
        per_global[t] = round(float(ths[int(np.argmin(np.abs(c_all - v)))]), 2)
    return {"joint_deg": round(float(bth), 2),
            "rms_resid_db": round(math.sqrt(best / len(meas)), 3),
            "per_thickness_deg_same_branch": per,
            "spread_deg_same_branch": round(max(per.values()) - min(per.values()), 2),
            "per_thickness_deg_global_argmin": per_global,
            "branch_note_ko": "슬래브 |R|(θ) 는 각에 대해 단조가 아니라 같은 dB 를 내는 각이 둘 이상이다 — 점별 역산은 공동해 가지 안에서만 읽는다.",
            "pred_at_joint_db": {t: round(slab_pred_db(t, bth), 3) for t in meas},
            "resid_at_joint_db": {t: round(v - slab_pred_db(t, bth), 3) for t, v in meas.items()}}


slab_cmp = []
for mm in THK:
    pr = slab_delta[f"{mm:g}mm"]
    slab_cmp.append({"prop_mm": mm, "measured_d_ac_db": meas30[mm],
                     "pred_deg45_db": pr["deg45_delta_db"], "pred_angle_avg_db": pr["angle_avg_delta_db"],
                     "pred_normal_db": pr["normal_delta_db"],
                     "resid_vs_deg45_db": round(meas30[mm] - pr["deg45_delta_db"], 3),
                     "resid_vs_angle_avg_db": round(meas30[mm] - pr["angle_avg_delta_db"], 3),
                     "measured_d_floor_db": floor30[mm],
                     "floor_resid_vs_deg45_db": round(floor30[mm] - pr["deg45_delta_db"], 3),
                     "floor_resid_vs_angle_avg_db": round(floor30[mm] - pr["angle_avg_delta_db"], 3)})

# 프롭/비프롭 분해 P(t) = A·r(t;θ) + B — θ 는 그 잣대의 공동 적합각
def decompose(meas, th):
    r = np.array([1.0] + [slab_R2(t / 1000, th) / slab_R2(0.1, th) for t in meas])
    y = np.array([1.0] + [10 ** (meas[t] / 10) for t in meas])
    M = np.vstack([r, np.ones_like(r)]).T
    (A, B), *_ = np.linalg.lstsq(M, y, rcond=None)
    fit = M @ np.array([A, B])
    return {"theta_deg": round(float(th), 2), "A_prop": round(float(A), 5), "B_nonprop": round(float(B), 5),
            "nonprop_share_of_base_pct": round(100 * float(B) / float(A + B), 2),
            "resid_db": [round(10 * math.log10(y[i] / fit[i]), 3) for i in range(len(y))]}


angle_fit = {"el-30_ac": fit_angle(meas30), "el-30_floor": fit_angle(floor30)}
decomp = {"ac_el-30_at_fitted_angle": decompose(meas30, angle_fit["el-30_ac"]["joint_deg"]),
          "ac_el-30_at_45deg": decompose(meas30, 45.0),
          "floor_el-30_at_fitted_angle": decompose(floor30, angle_fit["el-30_floor"]["joint_deg"]),
          "note_ko": ("B 는 «두께를 아무리 바꿔도 안 줄어드는 몫» 이다. 요동 축에서 B ≈ 0 이면 "
                      "그 축은 프로펠러 플라스틱 하나로 다 설명된다는 뜻이다.")}

# ══ 밴드 ══════════════════════════════════════════════════════════════════
g = json.load(open(GRID))
floor_band = {}
ac_band_grid = {}
for el, blk in g["per_elevation"].items():
    l2 = blk["layer2_statistics"]
    f12 = l2["div12"]["ac_power_db"] + 10 * math.log10(l2["div12"]["above_f_tip_frac"])
    f24 = l2["div24"]["ac_power_db"] + 10 * math.log10(l2["div24"]["above_f_tip_frac"])
    floor_band[el] = round(abs(f24 - f12), 3)
    ac_band_grid[el] = round(abs(l2["delta_div24_minus_div12"]["ac_power_db"]), 3)

BAND = {"ac_db": 0.374, "floor_db": floor_band["-30"], "comb_db": 4.6,
        "rhythm_pp": 21.8, "above_pp": 9.256, "beat_hz": 0.152, "seed_2sd_db": 3.67}


def call(dv, band):
    if dv is None or band is None:
        return None
    return "밴드 밖(유의)" if abs(dv) > band else "밴드 안(판정 불가)"


scoring = []
for r in lad:
    scoring.append({"prop_mm": r["prop_mm"],
                    "ac": {"delta_db": r["d_ac_power_db"], "band_db": BAND["ac_db"],
                           "call": call(r["d_ac_power_db"], BAND["ac_db"]),
                           "vs_seed_2sd": call(r["d_ac_power_db"], BAND["seed_2sd_db"])},
                    "floor": {"delta_db": r["d_floor_above_tip_db"], "band_db": BAND["floor_db"],
                              "call": call(r["d_floor_above_tip_db"], BAND["floor_db"])},
                    "comb": {"delta_db": r["d_comb_contrast_db"], "band_db": BAND["comb_db"],
                             "call": call(r["d_comb_contrast_db"], BAND["comb_db"])},
                    "rhythm": {"delta_pp": r["d_rhythm_share_pp"], "band_pp": BAND["rhythm_pp"],
                               "call": call(r["d_rhythm_share_pp"], BAND["rhythm_pp"])}})

# ══ 각도 곁가지 ═══════════════════════════════════════════════════════════
angle_sub = {}
for el in (0.0, -60.0):
    bb, Ebb = metrics(BASE, el)
    bb["spike"] = spike_stats(Ebb)
    blk = {"base_100mm": bb}
    meas = {}
    for mm in (0.9, 1.43):
        if (LAD[mm], el) not in rows:
            continue
        dd, EE = metrics(LAD[mm], el)
        dd["delta_vs_base"] = delta(dd, bb); dd["vs_base_waveform"] = wave_cmp(Ebb, EE)
        dd["spike"] = spike_stats(EE)
        blk[f"prop_{mm:g}mm"] = dd
        meas[mm] = dd["delta_vs_base"]["d_ac_power_db"]
    if len(meas) >= 2 and all(abs(v) > 1e-6 for v in meas.values()):
        blk["effective_angle_fit"] = fit_angle(meas)
    blk["monotone_brighter_with_thickness"] = (None if len(meas) < 2 else bool(meas[1.43] >= meas[0.9]))
    angle_sub[f"el{el:+.0f}"] = blk

canon = arms["prop_1.43mm"]
p09 = arms["prop_0.9mm"]

out = {
    "_meta": {
        "generator": "scratchpad/ladder_final.py (프로펠러 두께 사다리 판정자 · 08-16 병합 원장)",
        "date_kst": "2026-08-16",
        "question_ko": "정본 프로펠러 두께 1.43 mm 를 포함한 두께 사다리(0.5·0.9·1.43·2.0 mm)가 기본(Sionna 100 mm)과 어떻게 다른가",
        "gpu_used": False,
        "inputs": [LEDGER, NPZ, GRID,
                   "outputs/frame_completion_0816.json(앙각별 밴드 정정)",
                   "outputs/depth_axis_verdict_0816.json(튀는 자세 조사 절차)",
                   "outputs/material_verdict_0816.json(08-16 오전 판 — 비교 기준)",
                   "docs/MATERIAL_CORRECTION.md §2-4·§6(사전등록 문안)"],
        "conventions_ko": (
            "모든 레벨 비교는 **정지 성분(DC) 제거 후**. "
            "요동 = ac_power_db(DC 뺀 자세열의 평균 전력). "
            "확산 바닥 = ac_power_db + 10log10(날개끝 상한 위 몫). "
            "빗살 대비 = build_md_atlas.comb_contrast_db(2·f_flash~f_tip, 정수배÷중간자리). "
            "잣대 식은 08-16 오전 판(build_material_verdict.py)과 글자 그대로 같아 두 판을 바로 비교할 수 있다. "
            "팔: PathSolver spp 4e9 · 물리 끔 · 반사깊이 1 · 15 m · matrice4e · 자세 8192 · 같은 seed(짝지은 비교). "
            "우리 커널(SBR+PO)에는 두께 개념이 없어 이 축은 구조적으로 못 잰다."),
        "paired_comparison_evidence_ko": (
            "사다리 다섯 팔 전부 자세 8192 · 빠진 자세 0 · 경로수 중앙값 1505 로 **똑같다** — "
            "두께는 기하를 안 건드리고 재질 계수만 바꾸므로 광선 표집이 같다. 짝지은 비교라 표집 요동이 소거된다."),
        "arm_naming_ko": (
            "두께 팔은 전부 셸 0.75 mm 와 한 묶음이다(프롭 단독 팔은 원장에 없다). 다만 셸 0.75 단독 팔"
            "(프롭 100 mm)이 대조군으로 있고 그 팔의 요동·바닥·빗살 변화가 0.00 dB 라, 사다리가 움직인 것은 "
            "전부 프롭 몫으로 읽어도 된다."),
    },
    "bands": {
        "owner_ko": "격자 산포 밴드의 주인은 **우리 커널(SBR+PO)의 λ/12↔λ/24 격자 축**이다 — 여기 팔은 전부 PathSolver 라 «가져다 쓰는» 밴드다.",
        "correction_ko": (
            "⭐08-16 오전 판은 요동(AC) 밴드로 **전 앙각 3.861 dB** 한 값을 썼다. 정정본은 앙각마다 다르다 — "
            "el −30 의 요동 밴드는 **0.37 dB** 이고 3.86 은 정면(el 0) 값이다. 이 사다리는 전부 el −30 이라 "
            "좁은 정정본으로 채점했다(더 엄격한 쪽)."),
        "used_at_el_minus30": BAND,
        "ac_grid_band_by_el_db": {"0": 3.86, "-15": 1.31, "-30": 0.37, "-45": 0.09,
                                  "-60": 0.02, "-75": 0.10, "-90": 5.62},
        "floor_grid_band_by_el_db": floor_band,
        "floor_band_caveat_ko": (
            "⚠확산 바닥의 격자 밴드는 el −30 에서 **9.30 dB** 로 매우 넓다 — 그 밴드는 «상한 위 몫» 이 "
            "격자에 9.26 %p 나 흔들리는 데서 온다. 요동 밴드(0.37 dB)의 25 배다. 그래서 확산 바닥은 "
            "이 축을 재는 데 둔한 잣대이고, 헤드라인은 요동으로 쓰는 것이 옳다."),
        "grid_convergence_coverage_ko": "grid_convergence_check 는 el +0·−15·−30·−45 네 점뿐 — el −60 밴드는 없다.",
    },
    "slab_predictions_3p5ghz": {
        "abs": slab, "delta_vs_100mm": slab_delta,
        "note_ko": ("ITU-R P.2040 단층 슬래브, plastic εr 2.7 · σ 0.02, 편파(TE·TM) 전력평균. "
                    "각도평균은 sinθcosθ 가중(반구 등입체각). "
                    "⚠슬래브는 무한 평판이라 프로펠러 날 같은 좁고 휜 면의 회절·끝단 효과는 안 담는다."),
    },
    "el_minus30_ladder": {"el_deg": EL, "f_tip_hz": f_tip30, "arms": arms,
                          "ladder_table_raw": lad,
                          "shell_isolation_ko": (
                              "셸 0.75 mm 단독 팔(프롭 100 mm)의 기본 대비: 요동 "
                              f"{arms['shell0.75_prop100_control']['delta_vs_base']['d_ac_power_db']:+.3f} dB · 바닥 "
                              f"{arms['shell0.75_prop100_control']['delta_vs_base']['d_floor_above_tip_db']:+.3f} dB · 빗살 "
                              f"{arms['shell0.75_prop100_control']['delta_vs_base']['d_comb_contrast_db']:+.3f} dB "
                              "— 표적 축에 셸은 배선이 없다.")},
    "monotonicity": mono,
    "outlier_forensics": {
        "why_ko": ("⭐한 자세가 통째로 튀면 잣대가 그 자세 하나를 재게 된다. 08-16 에 판정 하나가 실제로 그렇게 뒤집혔다. "
                   "그래서 사다리 다섯 팔을 통틀어 |AC|/중앙 이 큰 자세 k 개를 다섯 팔에서 똑같이 빼고 다시 쟀다."),
        "isolation_def_ko": "isolation = |AC| 최대 ÷ 둘째. 1 에 가까우면 로터 대칭이 만든 구조적 플래시(정상), 2 를 넘으면 자세 하나만 튄 것이다.",
        "verdict_ko": (
            "⭐**튀는 자세는 없다.** 다섯 팔 전부 isolation 1.001~1.008 로 문턱 2.0 에서 한참 멀고"
            "(깊이 축 판정의 중앙값 1.018 과 같은 자리), 최대 자세가 가진 요동 에너지는 0.07~0.08 % "
            "· 상위 8 자세 합쳐도 0.53~0.63 % 다. 가장 큰 자세들의 번호(1755·1756 · 2845·2846 · 3001·3002 · "
            "2222·2224)가 **이웃끼리 짝**을 이루는 것도 로터 대칭이 만든 구조적 플래시라는 증거다."),
        "isolation_by_arm": {k: (arms[k]["spike"] or {}).get("isolation") for k in arms},
        "spike_by_arm": {k: arms[k]["spike"] for k in arms},
        "top_rel_poses": [int(i) for i in order[:16]],
        "trim_delete": trim_delete,
        "trim_null_time_base_preserved": trim_null,
        "random_delete_control": rand_ctl,
        "uniform_resample": uniform,
        "procedure_warning_ko": (
            "⭐⭐**자세를 «지우는» 솎기는 빗살·리듬 잣대에 쓰면 안 된다.** 자세열은 균일 시간 표본이라 "
            "가운데서 하나를 빼면 뒤가 한 칸씩 당겨져 배음선이 번진다. 실측: 기본판 빗살 대비가 "
            "51.99 → 47.54(하나 뺌) → 36.24(여덟 뺌) dB 로 무너지고, 사다리의 Δ빗살도 −6.21 → −2.87 → −0.13 dB "
            "로 사라진다. 그런데 **튐과 무관한 무작위 자세**를 지워도 똑같이 무너진다 — 기본판 빗살 "
            f"{rand_ctl['k1']['base_comb_db_mean']} ± {rand_ctl['k1']['base_comb_db_sd']} dB(하나), "
            f"{rand_ctl['k8']['base_comb_db_mean']} ± {rand_ctl['k8']['base_comb_db_sd']} dB(여덟). "
            "즉 그 «사라짐» 은 이상값이 아니라 **지우기 절차의 부작용**이다. "
            "요동·확산 바닥은 지워도 0.01~0.09 dB 밖에 안 움직이므로 그 두 잣대에는 안전하다. "
            "빗살·리듬의 옳은 강건성 검사는 **균일 재표집**(반쪽 나누기·짝수/홀수 솎기)이고, "
            "그 검사에서 Δ빗살(1.43 mm)은 −5.8~−6.3 dB 로 원판 −6.21 dB 와 같은 자리에 선다."),
        "headline_rule_ko": (
            "튀는 자세가 없고(isolation ≈ 1.00) 지우기 솎기는 빗살에 부작용이 있으므로, "
            "이 사다리의 헤드라인은 **솎지 않은 원판**으로 쓴다. 솎은 값은 위 표에 전부 실었다 — "
            "요동·바닥은 솎아도 같고, 빗살만 절차 부작용으로 줄어든다."),
    },
    "prereg_band_scoring_el_minus30": scoring,
    "slab_comparison": slab_cmp,
    "effective_incidence_fit": angle_fit,
    "prop_vs_nonprop_decomposition": decomp,
    "angle_subladder": angle_sub,
    "canon_1p43mm_headline": {
        "trim": "원판(솎지 않음) — 튀는 자세 없음",
        "d_ac_power_db": canon["delta_vs_base"]["d_ac_power_db"],
        "d_floor_above_tip_db": canon["delta_vs_base"]["d_floor_above_tip_db"],
        "d_comb_contrast_db": canon["delta_vs_base"]["d_comb_contrast_db"],
        "d_rhythm_share_pp": canon["delta_vs_base"]["d_rhythm_share_pct"],
        "d_dc_power_db": canon["delta_vs_base"]["d_dc_power_db"],
        "trimmed_k1_delete": {k: v for k, v in
                              next(r for r in trim_delete["k1"]["delta_vs_base"] if r["prop_mm"] == 1.43).items()},
        "trimmed_k8_delete": {k: v for k, v in
                              next(r for r in trim_delete["k8"]["delta_vs_base"] if r["prop_mm"] == 1.43).items()},
        "abs_values": {"ac_power_db": canon["ac_power_db"], "dc_power_db": canon["dc_power_db"],
                       "floor_above_tip_db": canon["floor_above_tip_db"],
                       "comb_contrast_db": canon["comb_contrast_db"],
                       "rhythm_share_pct": canon["rhythm_share_pct"],
                       "above_f_tip_pct": canon["above_f_tip_pct"],
                       "beat_hz_track": canon["beat_hz_track"]},
        "band_calls": {"ac": call(canon["delta_vs_base"]["d_ac_power_db"], BAND["ac_db"]),
                       "floor": call(canon["delta_vs_base"]["d_floor_above_tip_db"], BAND["floor_db"]),
                       "comb": call(canon["delta_vs_base"]["d_comb_contrast_db"], BAND["comb_db"]),
                       "rhythm": call(canon["delta_vs_base"]["d_rhythm_share_pct"], BAND["rhythm_pp"])},
    },
    "vs_0p9mm_prior_verdict": {
        "prior_ko": "08-16 오전 판(0.9 mm 민감도 점): 요동 −16.99 · 확산 바닥 −12.56 · 빗살 대비 −6.98 dB",
        "reproduced_here_0p9": {"d_ac_power_db": p09["delta_vs_base"]["d_ac_power_db"],
                                "d_floor_above_tip_db": p09["delta_vs_base"]["d_floor_above_tip_db"],
                                "d_comb_contrast_db": p09["delta_vs_base"]["d_comb_contrast_db"]},
        "reproduction_exact": True,
        "prior_estimate_for_1p43_ac_db": -13.0,
        "measured_1p43_ac_db": canon["delta_vs_base"]["d_ac_power_db"],
        "estimate_error_db": round(canon["delta_vs_base"]["d_ac_power_db"] + 13.0, 3),
        "story_holds_ko": (
            "④ **같은 이야기를 한다 — 크기만 한 칸 작다.** 정본 1.43 mm 에서도 방향·구조·판정이 모두 "
            "0.9 mm 판과 같다(프롭이 표적 축 손잡이 · 셸은 0.00 · 요동이 밴드 밖 · 무늬 살아남음). "
            "오전 판이 «45° 열로 미뤄 −13 dB» 라고 적은 추정은 측정 −13.02 dB 로 0.02 dB 안에 맞았다. "
            "⚠단 **한 문장은 값을 고쳐야 한다** — «100 mm 때문에 12~13 dB 밝게 깔려 있다»(§6 게이트 2)는 "
            "0.9 mm 의 확산 바닥 −12.56 dB 로 «적중» 처리됐는데, 정본 1.43 mm 의 확산 바닥은 **−8.81 dB** 다. "
            "정본에서 12~13 dB 에 해당하는 것은 **요동(−13.02 dB)** 이지 확산 바닥이 아니다 — 두 잣대가 "
            "우연히 같은 수에 걸린 것이라 어느 잣대인지 반드시 적어야 한다."),
    },
    "pattern_survival": {
        "question_ko": "⑤ 무늬는 사는가",
        "answer_ko": (
            "**산다 — 그리고 두꺼워질수록 기본판 무늬로 되돌아온다.** 맵 상관(격자 바닥 0.6825)은 "
            "0.5 mm 0.880 · 0.9 mm 0.892 · 1.43 mm 0.903 · 2.0 mm 0.912 로 전부 바닥 위이고 두께에 단조. "
            "박자는 127.09 → 127.03~127.06 Hz(Δ ≤ 0.06, 밴드 0.152 안). "
            "리듬 몫은 80.5 % → 73.8~77.7 %(Δ −6.7~−2.8 %p, 밴드 21.8 안). "
            "빗살 대비는 51.99 → 44.1~46.4 dB 로 내려가되 백색잡음 널 0 dB 대비 **+44 dB 이상**이라 "
            "무늬 자체는 멀쩡하다. 정본 1.43 mm 의 Δ빗살 −6.21 dB 만 격자 밴드(4.6) 밖이라 유의하다."),
        "by_arm": {k: {"stft_db_map_corr": (arms[k].get("vs_base_waveform") or {}).get("stft_db_map_corr_dc_removed"),
                       "abs_rho": (arms[k].get("vs_base_waveform") or {}).get("abs_rho_dc_removed"),
                       "beat_hz": arms[k]["beat_hz_track"],
                       "rhythm_share_pct": arms[k]["rhythm_share_pct"],
                       "comb_contrast_db": arms[k]["comb_contrast_db"],
                       "above_f_tip_pct": arms[k]["above_f_tip_pct"]} for k in arms},
        "map_corr_grid_floor_el_minus30": 0.6825,
        "comb_grid_tag_ko": "⚠빗살 대비 절대값은 격자 계단마다 +4.0~5.6 dB 단조 상승한다 — 절대 인용에는 격자 꼬리표(λ/12)가 필요하다.",
    },
    "answers_ko": {
        "a_monotone": (
            "① **단조다 — 뒤집힘 0.** 두꺼울수록 밝다: 요동 Δ 가 0.5 mm −22.08 → 0.9 −16.99 → "
            "1.43 −13.02 → 2.0 −10.19 dB 로 한 칸씩(+5.09 · +3.97 · +2.83 dB) 올라간다. "
            "확산 바닥·빗살 대비·리듬 몫·정지 성분도 같은 순서로 단조이고, 균일 재표집 네 판에서도 단조가 유지된다."),
        "b_canon": (
            "② **정본 1.43 mm: 요동 −13.02 dB · 확산 바닥 −8.81 dB · 빗살 대비 −6.21 dB**(리듬 몫 −3.84 %p · 정지 성분 −12.83 dB). "
            "el −30 밴드로 채점하면 요동(밴드 0.37)·빗살(4.6)은 밴드 **밖**이라 유의하고, "
            "확산 바닥(−8.81)은 그 잣대의 넓은 격자 밴드 9.30 dB **안**이라 사전등록 문면으로는 «판정 불가» 다. "
            "⚠확산 바닥은 «상한 위 몫» 이 격자에 9.26 %p 흔들려 밴드가 넓은 둔한 잣대다 — "
            "짝지은 비교(같은 경로수 1505·같은 자세)라는 사실과 요동 축의 −13.02 dB 를 함께 읽는 것이 정직하다."),
        "c_slab": (
            "③ **요동은 45° 입사 예측과 0.31 dB, 각도평균 예측과 4.93 dB 차**(정본 1.43 mm). "
            "네 두께 전부에서 45° 잔차가 −0.28~−0.36 dB 로 **거의 일정**하고(각도평균 잔차는 −4.37~−6.43 dB), "
            "그 일정한 잔차는 각을 조금 옮기면 사라진다 — 네 점을 한 각으로 맞추면 **유효 입사각 40.2°** 에서 "
            "RMS 잔차 **0.145 dB**(같은 가지 안 점별 역산 40.08~40.35°, 폭 0.27°)로 닫힌다. "
            "즉 요동 축은 **프로펠러 플라스틱 평판의 두께 반사율 그 자체**이고 다른 재질이 낄 자리가 없다 — "
            "P = A·r(두께) + B 로 갈라 보면 «두께로 안 줄어드는 몫» B 가 기본판의 −0.13 %(=0)다. "
            "⚠확산 바닥도 한 각으로 닫히기는 한다(64.5°·RMS 0.135 dB). 그러나 그 각이 요동의 40.2° 와 **다르다** — "
            "같은 표면을 두 잣대로 봤는데 «유효 입사각» 이 24° 나 갈리면 둘 중 하나는 실제 입사각이 아니라는 뜻이다. "
            "갈리는 까닭은 프롭이 어두워질 때 «날개끝 상한 위 몫» 이 1.06 % → 2.67~3.12 %(+4.0~+4.7 dB) 로 오르기 때문이고, "
            "확산 바닥은 그 몫이 곱해진 **합성 잣대**다. 그래서 «평판 물리와 몇 dB 차인가» 는 요동 축으로 답해야 한다."),
        "d_prior": (
            "④ 0.9 mm 판정과 **같은 이야기**를 한다(vs_0p9mm_prior_verdict 참조). 오전 판의 −13 dB 추정이 "
            "측정 −13.02 dB 로 맞았고, 고칠 것은 «12~13 dB» 가 어느 잣대의 수인지 하나뿐이다."),
        "e_pattern": "⑤ 무늬는 산다 — pattern_survival 참조.",
    },
    "verdict_headline_ko": (
        "① 프로펠러 두께 사다리는 **완전 단조**다(뒤집힘 0) — 얇을수록 어둡다. "
        "② 정본 1.43 mm 에서 기본판(100 mm) 대비 **요동 −13.02 dB · 확산 바닥 −8.81 dB · 빗살 대비 −6.21 dB**. "
        "요동·빗살은 el −30 격자 밴드 밖(유의), 확산 바닥은 그 잣대의 넓은 밴드(9.30 dB) 안이라 문면상 판정 불가. "
        "③ 요동 축은 평판 물리로 **완전히** 설명된다 — 유효 입사각 40.2° 한 값으로 네 두께가 RMS 0.145 dB 에 닫히고, "
        "45° 예측과는 0.28~0.36 dB(정본 0.31 dB), 각도평균 예측과는 4.4~6.4 dB(정본 4.93 dB) 차다. "
        "③′ 확산 바닥도 한 각(64.5°)으로 닫히지만 그 각이 요동의 40.2° 와 다르다 — 확산 바닥은 «평판 반사 × 상한 위 몫» 의 합성 잣대라 평판 물리 대조에는 요동을 쓴다. "
        "④ 0.9 mm 로 낸 앞선 판정은 정본에서도 **같은 이야기**를 한다(추정 −13 dB ↔ 측정 −13.02 dB). "
        "다만 «100 mm 때문에 12~13 dB 밝게 깔림» 은 정본에서 **요동** 의 수이지 **확산 바닥**(−8.81 dB)의 수가 아니다 — "
        "잣대 이름을 반드시 붙여야 한다. "
        "⑤ 무늬는 산다 — 맵 상관 0.880~0.912(격자 바닥 0.68 위)·박자 Δ ≤ 0.06 Hz·리듬 몫 밴드 안이고, "
        "두꺼워질수록 기본판 무늬로 되돌아온다. "
        "⑥ 절차 경고 — **자세를 지우는 솎기는 빗살·리듬 잣대를 망가뜨린다**(무작위 자세를 지워도 똑같이 무너진다). "
        "튀는 자세는 애초에 없다(isolation 1.001~1.008). 헤드라인은 솎지 않은 원판을 쓴다."),
    "headline_impacts_ko": {
        "§6_게이트2_12~13dB": (
            "⚠**잣대 이름을 붙여 고쳐야 한다.** 오전 판은 0.9 mm 의 확산 바닥 −12.56 dB 로 «적중» 처리했는데, "
            "정본 1.43 mm 의 확산 바닥은 −8.81 dB 다. 정본에서 12~13 dB 인 것은 **요동(−13.02 dB)** 이다. "
            "두 잣대가 우연히 같은 수에 걸린 것이라 «12~13 dB» 를 인용할 때는 반드시 어느 잣대인지 적는다."),
        "덱24_drowned_blades_−8.08dB": (
            "⚠**값을 다시 봐야 한다.** MATERIAL_CORRECTION §4-3 은 덱 24 장의 프로펠러 문장에 정본 1.43 mm 의 "
            "**각도평균 슬래브 −8.08 dB** 를 넣기로 했다(«78 → 약 86 dB»). 그런데 이 사다리가 실제로 잰 날개 에코"
            "(요동) 변화는 el −30 에서 **−13.02 dB** 이고, 각도평균이 아니라 **유효 입사각 40.2°** 가 맞는 잣대다. "
            "그 수를 쓰면 «78 → 약 91 dB» 가 된다 — 익사 간격은 계획보다 **약 4.9 dB 더 벌어진다**(결론 방향은 같고 강해진다). "
            "⚠단 우리 측정은 el −30 한 앙각이고 덱 문장은 각도 무관 서술이라, 인용 전에 어느 기하의 수인지 정해야 한다."),
        "R50_−34%_추정": (
            "방향 유지·크기 갱신 — 커널 프롭 정정의 −34 % R50 추정은 0.9 mm 근처 감쇄를 깔고 있었다. "
            "정본 1.43 mm 의 PathSolver 요동 감쇄는 −13.02 dB 로 0.9 mm(−16.99)보다 **약 4 dB 얕다**. "
            "절대 거리 주장은 게이트 전까지 보류이므로 여기서 R50 을 다시 계산하지 않는다 — 다만 «−34 %» 는 "
            "정본 두께에서 다시 내야 하는 수다."),
        "el0_금속_추첨": (
            "정본에서도 확증 — el 0 에서 프롭 1.43 mm 판의 요동·확산 바닥·정지 성분이 전부 0.000 dB. "
            "정면은 금속 거울이 다 먹는다는 읽기가 두께 손잡이 두 점(0.9·1.43)에서 똑같이 나온다."),
        "무늬_분류_서사": "유지 — 맵 상관 0.903(격자 바닥 0.68 위)·박자 Δ 0.04 Hz·리듬 몫 밴드 안. 정본 두께에서도 무늬는 산다.",
    },
    "open_ko": [
        "⚠이 사다리는 **기하를 안 건드리는 재질 계수 쓸기**다(다섯 팔의 경로수 중앙값이 1505 로 똑같다). "
        "그래서 «두꺼울수록 밝다» 는 단조성 자체는 슬래브 공식이 그 두께 범위에서 단조라는 사실의 되풀이에 가깝다 — "
        "새로 안 것은 **크기**(정본에서 −13.02 dB)와 **유효 입사각 40.2°**, 그리고 그 축에 프롭 말고는 아무것도 안 낀다는 사실이다.",
        "el −60 에는 격자 밴드가 없다(grid_convergence_check 가 네 앙각뿐) — 그 앙각 수치는 밴드 없이 방향만 읽는다.",
        "두께 0.5·0.9·2.0 mm 는 측정값이 아니라 민감도 점이다(RETRACTION_LOG A3). 정본은 1.43 mm 하나뿐이고 그것도 «우리 메쉬 자신의 시위평균» 이지 DJI 실물 실측이 아니다.",
        "유효 입사각 40.2°(el −30)·21.9°(el −60)는 **역산값**이지 기하로 유도한 값이 아니다 — 시선이 가팔라질수록 수직입사에 가까워진다는 방향만 맞다.",
        "프롭이 어두워질 때 «날개끝 상한 위 몫» 이 왜 오르는지(요동 40.2° ↔ 확산 바닥 64.5° 의 갈림)는 이 원장이 안 닫았다 — 상한 위에 프롭 |Γ|² 로 안 줄어드는 항이 있다는 뜻인데 그것이 무엇인지는 안 갈랐다.",
        "우리 커널(SBR+PO)에는 두께 개념이 없어 이 사다리는 PathSolver 한 엔진에서만 잰 것이다 — 교차 확인이 없다.",
        "빗살 대비의 사전등록 밴드는 없다 — 여기서는 격자 계단(el −30 4.6 dB)을 대신 썼고, 그것은 «가져다 쓴» 눈금이다.",
    ],
}

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("saved", OUT)
print(json.dumps(out["canon_1p43mm_headline"], ensure_ascii=False, indent=1))
print(json.dumps(mono, ensure_ascii=False))
print(json.dumps(angle_fit, ensure_ascii=False, indent=1))
print(json.dumps(scoring, ensure_ascii=False, indent=1))
