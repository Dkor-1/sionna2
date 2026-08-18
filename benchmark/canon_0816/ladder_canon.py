#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""프로펠러 두께 사다리 판정 — outputs/material_canon_0816_ladder.json

0.5 · 0.9 · 1.43(정본) · 2.0 mm 네 점 + 기본판(Sionna 100 mm)을 나란히 잰다.
잣대 정의는 scratchpad/build_material_verdict.py(08-16 오전 판)와 **글자 그대로 같다** —
그래야 앞선 0.9 mm 판정과 직접 비교가 된다.
⛔GPU 0 · 저장된 원장만 읽는다.
"""
import json, math, sys, os
import numpy as np

sys.path.insert(0, "/workspace/sionna/src")
sys.path.insert(0, "/workspace/sionna/benchmark")
from md_mapstyle import flash_spec  # noqa: E402

OUT = "/workspace/sionna/outputs/material_canon_0816_ladder.json"
LEDGER = "/workspace/sionna/outputs/elevation_sweep_md.json"
NPZ = "/workspace/sionna/outputs/elevation_sweep_md.npz"
GRID = "/workspace/sionna/outputs/grid_convergence_check.json"

COMB_TOL_HZ = 8.0
AC_MIN_HZ = 8.0
RHY_HW = 8.0
EPS0 = 8.8541878128e-12
C = 299792458.0
NEAR_FLOOR = 1e-11

led = json.load(open(LEDGER))
npz = np.load(NPZ)
meta = led["_meta"]
PRF = float(meta["prf_hz"])
FFL = float(meta["f_flash_hz"])
FC = 3.5e9
rows = {(r["engine"], round(float(r["el_deg"]), 3)): r for r in led["rows"]}


def series(arm, el):
    return np.asarray(npz[f"{arm}/el{el:+.0f}"], dtype=complex)


# ── 표준 잣대(전부 DC 제거) — 08-16 오전 판과 동일식 ─────────────────────────
def core(E, f_tip):
    E = np.asarray(E, complex)
    dc = complex(E.mean())
    x = E - dc
    n = E.size
    P = np.abs(np.fft.fft(x * np.hanning(n))) ** 2
    fr = np.fft.fftfreq(n, d=1.0 / PRF)
    fa = np.abs(fr)
    above = fa >= f_tip
    ac_band = fa >= AC_MIN_HZ
    k = np.round(fa / FFL)
    on = (k >= 1) & (np.abs(fa - k * FFL) <= COMB_TOL_HZ)
    p_above, p_ac = float(P[above].sum()), float(P[ac_band].sum())
    ac_lin = float((np.abs(x) ** 2).mean())
    dc_lin = abs(dc) ** 2
    d = {
        "n_used": int(n),
        "dc_power_db": round(10 * math.log10(dc_lin + 1e-300), 3),
        "ac_power_db": round(10 * math.log10(ac_lin + 1e-300), 3),
        "ac_over_dc": (round(ac_lin / dc_lin, 8) if dc_lin > 0 else None),
        "rhythm_share_pct": round(100 * float(P[above & on].sum()) / p_above, 3) if p_above > 0 else None,
        "above_f_tip_pct": round(100 * p_above / p_ac, 4) if p_ac > 0 else None,
    }
    frac = p_above / p_ac if p_ac > 0 else None
    d["floor_above_tip_db"] = round(d["ac_power_db"] + 10 * math.log10(frac), 3) if frac and frac > 0 else None
    lo, hi = 2.0 * FFL, f_tip
    comb = None
    if hi >= 3.0 * FFL:
        band = (fa >= lo) & (fa <= hi)
        kk = fa / FFL
        on2 = band & (np.abs(kk - np.round(kk)) * FFL <= RHY_HW)
        off2 = band & (np.abs(np.abs(kk - np.floor(kk)) - 0.5) * FFL <= RHY_HW)
        if int(on2.sum()) >= 4 and int(off2.sum()) >= 4:
            num, den = float(P[on2].mean()), float(P[off2].mean())
            if num > 0 and den > 0:
                comb = round(10 * math.log10(num / den), 3)
    d["comb_contrast_db"] = comb
    d["near_numeric_floor"] = bool(d["ac_over_dc"] is not None and d["ac_over_dc"] < NEAR_FLOOR)
    return d


def metrics(arm, el):
    row = rows[(arm, el)]
    E = series(arm, el)
    f_tip = float(row["f_tip_hz"])
    d = core(E, f_tip)
    d.update({
        "arm": arm, "el_deg": el,
        "shell_mm": row["shell_mm"], "prop_mm": row["prop_mm"],
        "n_poses": int(row["n_poses"]), "n_missing": int(row["n_missing"]),
        "seconds": row.get("seconds"), "npaths_median": row.get("npaths_median"),
        "f_tip_hz": f_tip,
        "level_db_ledger": row["level_db"],
        "beat_hz_track": row["track"]["beat_hz"],
        "blade_band_power_db_track": row["track"]["band_power_db"],
    })
    return d, E


def wave_cmp(a, b):
    x, y = a - a.mean(), b - b.mean()
    na, nb = np.linalg.norm(x), np.linalg.norm(y)
    r = abs(complex(np.vdot(x, y) / (na * nb))) if na and nb else None
    _, _, Sa, _ = flash_spec(np.asarray(x, complex), PRF, FFL)
    _, _, Sb, _ = flash_spec(np.asarray(y, complex), PRF, FFL)
    A = 10 * np.log10(Sa / Sa.max() + 1e-12)
    B = 10 * np.log10(Sb / Sb.max() + 1e-12)
    mc = float(np.corrcoef(A.ravel(), B.ravel())[0, 1])
    # 담김 계수 — b 안에 a 가 얼마나 들어 있나(진폭비 포함)
    cc = abs(complex(np.vdot(x, y) / np.vdot(x, x))) if na else None
    return {"abs_rho_dc_removed": round(r, 4), "stft_db_map_corr_dc_removed": round(mc, 4),
            "contain_coeff": round(cc, 4)}


def spike_stats(E):
    x = np.asarray(E, complex)
    x = x - x.mean()
    if not np.any(x):
        return None
    v = np.sort(np.abs(x))[::-1]
    med = float(np.median(np.abs(x)))
    if med <= 0:
        return None
    return {"top1_over_median": round(float(v[0] / med), 2),
            "top2_over_median": round(float(v[1] / med), 2),
            "isolation": round(float(v[0] / v[1]), 3),
            "argmax_pose": int(np.argmax(np.abs(x)))}


def rel_score(E):
    x = np.asarray(E, complex)
    x = x - x.mean()
    m = np.median(np.abs(x))
    return np.abs(x) / m if m > 0 else np.zeros_like(np.abs(x))


# ── 슬래브 예측(ITU-R P.2040, plastic εr 2.7 · σ 0.02, 편파 전력평균) ────────
lam = C / FC
eps = 2.7 - 1j * 0.02 / (2 * np.pi * FC * EPS0)


def slab_R2(d_m, th_deg):
    th = np.radians(th_deg)
    s, c = np.sin(th), np.cos(th)
    q = np.sqrt(eps - s ** 2)
    k0 = 2 * np.pi / lam
    ph = np.exp(-2j * k0 * d_m * q)
    tot = 0.0
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
            "deg45_db": round(10 * math.log10(slab_R2(mm / 1000, 45.0)), 2),
            "deg30_db": round(10 * math.log10(slab_R2(mm / 1000, 30.0)), 2),
            "deg60_db": round(10 * math.log10(slab_R2(mm / 1000, 60.0)), 2)}


THKS = (0.5, 0.75, 0.9, 1.43, 1.5, 2.0, 3.0, 100.0)
slab = {f"{mm:g}mm": slab_row(mm) for mm in THKS}
base_s = slab["100mm"]
slab_delta = {k: {kk.replace("_db", "_delta_db"): round(v[kk] - base_s[kk], 2) for kk in v}
              for k, v in slab.items() if k != "100mm"}

# ── 팔 ───────────────────────────────────────────────────────────────────────
BASE = "sionna_p4000000000_r15_n8192_d1"
SHELL075 = "sionna_p4000000000_r15_n8192_shell0.75mm_d1"
PROPS = "sionna_p4000000000_partsprop_r15_n8192_d1"
LADDER = {
    0.5: "sionna_p4000000000_r15_n8192_shell0.75mm_prop0.5mm_d1",
    0.9: "sionna_p4000000000_r15_n8192_shell0.75mm_prop0.9mm_d1",
    1.43: "sionna_p4000000000_r15_n8192_shell0.75mm_prop1.43mm_d1",
    2.0: "sionna_p4000000000_r15_n8192_shell0.75mm_prop2mm_d1",
}
DKEYS = ["floor_above_tip_db", "ac_power_db", "dc_power_db", "level_db_ledger",
         "comb_contrast_db", "rhythm_share_pct", "above_f_tip_pct", "beat_hz_track"]


def delta(d, b):
    out = {}
    for k in DKEYS:
        if d.get(k) is None or b.get(k) is None:
            out["d_" + k] = None
        else:
            out["d_" + k] = round(d[k] - b[k], 4)
    return out


EL = -30.0
b30, Eb30 = metrics(BASE, EL)
f_tip30 = b30["f_tip_hz"]
arms = {"base_100mm": b30}
E_by = {"base_100mm": Eb30}
b30["spike"] = spike_stats(Eb30)

d, Esh = metrics(SHELL075, EL)
d["delta_vs_base"] = delta(d, b30)
d["vs_base_waveform"] = wave_cmp(Eb30, Esh)
d["spike"] = spike_stats(Esh)
arms["shell0.75_prop100_control"] = d

for mm in (0.5, 0.9, 1.43, 2.0):
    dd, EE = metrics(LADDER[mm], EL)
    dd["delta_vs_base"] = delta(dd, b30)
    dd["vs_base_waveform"] = wave_cmp(Eb30, EE)
    dd["spike"] = spike_stats(EE)
    arms[f"prop_{mm:g}mm"] = dd
    E_by[f"prop_{mm:g}mm"] = EE

dp, Ep = metrics(PROPS, EL)
dp["spike"] = spike_stats(Ep)
arms["ref_props_only_100mm"] = dp

# ── 튀는 자세(이상값) 솎기 ──────────────────────────────────────────────────
LKEYS = ["base_100mm", "prop_0.5mm", "prop_0.9mm", "prop_1.43mm", "prop_2mm"]
LKEYS = ["base_100mm"] + [f"prop_{mm:g}mm" for mm in (0.5, 0.9, 1.43, 2.0)]
rel_all = np.maximum.reduce([rel_score(E_by[k]) for k in LKEYS])
order = np.argsort(rel_all)[::-1]


def trimmed_table(k):
    mask = np.ones(rel_all.size, bool)
    if k:
        mask[order[:k]] = False
    tab = {}
    for key in LKEYS:
        tab[key] = core(E_by[key][mask], f_tip30)
    base = tab["base_100mm"]
    for key in LKEYS:
        if key == "base_100mm":
            continue
        tab[key]["delta_vs_base"] = {
            "d_" + kk: (None if (tab[key].get(kk) is None or base.get(kk) is None)
                        else round(tab[key][kk] - base[kk], 4))
            for kk in ["floor_above_tip_db", "ac_power_db", "dc_power_db",
                       "comb_contrast_db", "rhythm_share_pct", "above_f_tip_pct"]}
    return {"k_trimmed": k, "n_kept": int(mask.sum()),
            "dropped_poses": [int(i) for i in order[:k]], "arms": tab}


trims = {f"k{k}": trimmed_table(k) for k in (0, 1, 8)}

# 짝지은(pairwise) 솎기 — depth_axis 절차 그대로, 팔마다 기본과 둘이서만 솎는다
pairwise = {}
for mm in (0.5, 0.9, 1.43, 2.0):
    key = f"prop_{mm:g}mm"
    r = np.maximum(rel_score(Eb30), rel_score(E_by[key]))
    o = np.argsort(r)[::-1]
    blk = {}
    for k in (0, 1, 8):
        m = np.ones(r.size, bool)
        if k:
            m[o[:k]] = False
        a = core(Eb30[m], f_tip30)
        b = core(E_by[key][m], f_tip30)
        blk[f"k{k}"] = {kk: (None if (a.get(kk) is None or b.get(kk) is None)
                             else round(b[kk] - a[kk], 4))
                        for kk in ["ac_power_db", "floor_above_tip_db", "comb_contrast_db",
                                   "rhythm_share_pct", "dc_power_db"]}
        blk[f"k{k}"]["dropped_poses"] = [int(i) for i in o[:k]]
    pairwise[key] = blk

# ── 밴드 ────────────────────────────────────────────────────────────────────
g = json.load(open(GRID))
pe = g["per_elevation"]
floor_band = {}
for el, blk in pe.items():
    l2 = blk["layer2_statistics"]
    f12 = l2["div12"]["ac_power_db"] + 10 * math.log10(l2["div12"]["above_f_tip_frac"])
    f24 = l2["div24"]["ac_power_db"] + 10 * math.log10(l2["div24"]["above_f_tip_frac"])
    floor_band[el] = round(f24 - f12, 3)

GRID_BAND_AC_DB = {"0": 3.86, "-15": 1.31, "-30": 0.37, "-45": 0.09,
                   "-60": 0.02, "-75": 0.10, "-90": 5.62}
GRID_BAND_COMB_DB = {"0": 0.1, "-15": 4.1, "-30": 4.6, "-45": 4.6, "-60": 4.0,
                     "-75": None, "-90": None}
GRID_BAND_RHY_PP = {"0": 11.8, "-15": 0.1, "-30": 21.8, "-45": 12.9,
                    "-60": 16.0, "-75": 2.5, "-90": 16.4}

bands = {
    "owner_ko": ("격자 산포 밴드의 주인은 **우리 커널(SBR+PO)의 λ/12↔λ/24 격자 축**이다. "
                 "여기 팔은 전부 PathSolver 라 «가져다 쓰는» 밴드다 — 널의 성격이 다르다."),
    "ac_power_grid_db_by_el": GRID_BAND_AC_DB,
    "ac_power_grid_db_at_el_minus30": 0.37,
    "comb_contrast_grid_db_by_el": GRID_BAND_COMB_DB,
    "rhythm_grid_pp_by_el": GRID_BAND_RHY_PP,
    "floor_above_tip_grid_db": {"per_el": floor_band,
                                "el_minus30": abs(floor_band["-30"]),
                                "note_ko": "grid_convergence_check 는 el +0·−15·−30·−45 네 점뿐 — −60 밴드는 없다"},
    "above_f_tip_grid_pp_global": 12.5549,
    "beat_grid_hz": 0.152,
    "seed_borrowed_db": {"sd": 1.833, "2sd": 3.67, "3sd": 5.5, "tag": "빌려 온 값(el-15·40 m·4e9)"},
    "correction_ko": ("⭐08-16 오전 판(material_verdict_0816)은 요동(AC) 밴드로 **전 앙각 3.861 dB** "
                      "한 값을 썼다. 정정본은 앙각마다 다르다 — el −30 의 요동 밴드는 **0.37 dB** 이고 "
                      "3.86 은 정면(el 0) 값이다. 이 사다리는 전부 el −30 이라 좁은 쪽 밴드로 채점했다. "
                      "밴드를 넓게 잡으면 «판정 불가» 쪽으로 기울므로, 좁은 정정본을 쓰는 것이 더 엄격하다."),
}


def band_call(dv, band, unit="dB"):
    if dv is None or band is None:
        return None
    return "밴드 밖(유의)" if abs(dv) > band else "밴드 안(판정 불가)"


# ── 사다리 표 ───────────────────────────────────────────────────────────────
def ladder_rows(source):
    out = []
    for mm in (0.5, 0.9, 1.43, 2.0):
        key = f"prop_{mm:g}mm"
        a = source["arms"][key] if "arms" in source else arms[key]
        dv = a["delta_vs_base"]
        out.append({"prop_mm": mm,
                    "d_ac_power_db": dv["d_ac_power_db"],
                    "d_floor_above_tip_db": dv["d_floor_above_tip_db"],
                    "d_comb_contrast_db": dv["d_comb_contrast_db"],
                    "d_rhythm_share_pp": dv["d_rhythm_share_pct"],
                    "d_dc_power_db": dv["d_dc_power_db"]})
    return out


lad_raw = ladder_rows(trims["k0"])
lad_k1 = ladder_rows(trims["k1"])
lad_k8 = ladder_rows(trims["k8"])


def monotone(vals):
    """두꺼울수록 밝아져야(덜 어두워져야) 한다 — Δ가 두께에 대해 증가(단조)인가."""
    d = [vals[i + 1] - vals[i] for i in range(len(vals) - 1)]
    return {"steps": [round(x, 3) for x in d],
            "monotone_increasing": all(x >= 0 for x in d),
            "monotone_decreasing": all(x <= 0 for x in d),
            "n_inversions": sum(1 for x in d if x < 0),
            "max_inversion_db": round(min(d), 3) if any(x < 0 for x in d) else 0.0}


mono = {}
for tag, lad in (("raw_k0", lad_raw), ("trimmed_k1", lad_k1), ("trimmed_k8", lad_k8)):
    mono[tag] = {
        "ac": monotone([r["d_ac_power_db"] for r in lad]),
        "floor": monotone([r["d_floor_above_tip_db"] for r in lad]),
        "comb": monotone([r["d_comb_contrast_db"] for r in lad]),
    }

# ── 슬래브 대조 ─────────────────────────────────────────────────────────────
slab_cmp = []
for tag, lad in (("raw_k0", lad_raw), ("trimmed_k1", lad_k1)):
    for r in lad:
        mm = r["prop_mm"]
        pr = slab_delta[f"{mm:g}mm"]
        slab_cmp.append({
            "trim": tag, "prop_mm": mm,
            "measured_d_ac_db": r["d_ac_power_db"],
            "pred_deg45_db": pr["deg45_delta_db"],
            "pred_angle_avg_db": pr["angle_avg_delta_db"],
            "pred_normal_db": pr["normal_delta_db"],
            "resid_vs_deg45_db": round(r["d_ac_power_db"] - pr["deg45_delta_db"], 3),
            "resid_vs_angle_avg_db": round(r["d_ac_power_db"] - pr["angle_avg_delta_db"], 3),
        })

# ── 각도 곁가지(0.9 vs 1.43 가 함께 있는 앙각) ────────────────────────────
angle_sub = {}
for el in (0.0, -60.0):
    blk = {}
    bb, Ebb = metrics(BASE, el)
    blk["base_100mm"] = bb
    for mm in (0.9, 1.43):
        arm = LADDER[mm]
        if (arm, el) not in rows:
            continue
        dd, EE = metrics(arm, el)
        dd["delta_vs_base"] = delta(dd, bb)
        dd["vs_base_waveform"] = wave_cmp(Ebb, EE)
        dd["spike"] = spike_stats(EE)
        blk[f"prop_{mm:g}mm"] = dd
    angle_sub[f"el{el:+.0f}"] = blk

# ── 저장 ────────────────────────────────────────────────────────────────────
canon = arms["prop_1.43mm"]
canon_k1 = trims["k1"]["arms"]["prop_1.43mm"]
p09 = arms["prop_0.9mm"]
p09_k1 = trims["k1"]["arms"]["prop_0.9mm"]

out = {
    "_meta": {
        "generator": "scratchpad/ladder_canon.py (프로펠러 두께 사다리 판정자)",
        "date_kst": "2026-08-16",
        "question_ko": "정본 프로펠러 두께 1.43 mm 를 포함한 두께 사다리(0.5·0.9·1.43·2.0 mm)가 기본(Sionna 100 mm)과 어떻게 다른가",
        "gpu_used": False,
        "inputs": [LEDGER, NPZ, GRID,
                   "outputs/frame_completion_0816.json(앙각별 밴드 정정)",
                   "outputs/depth_axis_verdict_0816.json(튀는 자세 절차)",
                   "outputs/material_verdict_0816.json(08-16 오전 판 — 비교 기준)"],
        "conventions_ko": ("모든 레벨 비교는 **정지 성분(DC) 제거 후**. "
                           "요동 = ac_power_db(DC 뺀 자세열의 평균 전력). "
                           "확산 바닥 = ac_power_db + 10log10(above_f_tip_frac). "
                           "빗살 대비 = build_md_atlas.comb_contrast_db(2·f_flash~f_tip, 정수배÷중간자리). "
                           "잣대 식은 08-16 오전 판(build_material_verdict.py)과 글자 그대로 같다. "
                           "팔: PathSolver spp 4e9 · 물리 끔 · 반사깊이 1 · 15 m · matrice4e · 자세 8192 · seed 1(짝지은 비교). "
                           "우리 커널(SBR+PO)에는 두께 개념이 없어 이 축은 구조적으로 잴 수 없다."),
        "arm_naming_ko": ("두께 팔은 전부 셸 0.75 mm 와 **한 묶음**이다(prop 단독 팔은 원장에 없다). "
                          "다만 셸 0.75 단독 팔(prop 100 mm)이 대조군으로 있고 그 팔의 요동/바닥/빗살 변화가 "
                          "0.00 dB 라, 사다리에서 보이는 변화는 전부 프롭 몫으로 읽어도 된다 — 아래 shell_isolation 참조."),
    },
    "bands": bands,
    "slab_predictions_3p5ghz": {
        "abs": slab, "delta_vs_100mm": slab_delta,
        "note_ko": ("ITU-R P.2040 단층 슬래브, plastic εr 2.7 · σ 0.02, 편파(TE·TM) 전력평균. "
                    "각도평균은 sinθcosθ 가중(반구 등입체각). "
                    "⚠슬래브는 **무한 평판**이라 프로펠러 날 같은 좁고 휜 면의 회절·끝단 효과는 안 담는다."),
    },
    "el_minus30_ladder": {
        "el_deg": EL, "f_tip_hz": f_tip30, "n_poses": 8192,
        "arms": arms,
        "shell_isolation_ko": ("셸 0.75 mm 단독 팔(prop 100 mm)의 기본 대비 변화: "
                               f"요동 {arms['shell0.75_prop100_control']['delta_vs_base']['d_ac_power_db']:+.3f} dB · "
                               f"바닥 {arms['shell0.75_prop100_control']['delta_vs_base']['d_floor_above_tip_db']:+.3f} dB · "
                               f"빗살 {arms['shell0.75_prop100_control']['delta_vs_base']['d_comb_contrast_db']:+.3f} dB "
                               "— 표적 축에 셸은 배선이 없다(구조적 0). 그래서 사다리의 움직임은 프롭 몫이다."),
    },
    "outlier_forensics": {
        "why_ko": ("⭐한 자세가 통째로 튀면 잣대가 그 자세 하나를 재게 된다. 08-16 에 판정 하나가 실제로 그렇게 "
                   "뒤집혔다. 그래서 사다리 다섯 팔을 통틀어 |AC|/중앙 이 가장 큰 자세 k 개를 **다섯 팔에서 "
                   "똑같이** 빼고 다시 쟀다. 헤드라인은 k=1 판이다."),
        "isolation_def_ko": "isolation = |AC| 최대 ÷ 둘째. 1 에 가까우면 로터 대칭이 만든 구조적 플래시(정상), 2 를 넘으면 자세 하나만 튄 것이다.",
        "isolation_by_arm": {k: (arms[k]["spike"] or {}).get("isolation") for k in arms},
        "argmax_pose_by_arm": {k: (arms[k]["spike"] or {}).get("argmax_pose") for k in arms},
        "top1_over_median_by_arm": {k: (arms[k]["spike"] or {}).get("top1_over_median") for k in arms},
        "ladder_common_trim": trims,
        "pairwise_trim": pairwise,
    },
    "ladder_table": {
        "raw_k0": lad_raw, "trimmed_k1": lad_k1, "trimmed_k8": lad_k8,
        "monotonicity": mono,
    },
    "slab_comparison": slab_cmp,
    "angle_subladder": angle_sub,
    "canon_1p43mm_headline": {
        "trim": "k=1(튀는 자세 하나 솎음)",
        "d_ac_power_db": canon_k1["delta_vs_base"]["d_ac_power_db"],
        "d_floor_above_tip_db": canon_k1["delta_vs_base"]["d_floor_above_tip_db"],
        "d_comb_contrast_db": canon_k1["delta_vs_base"]["d_comb_contrast_db"],
        "d_rhythm_share_pp": canon_k1["delta_vs_base"]["d_rhythm_share_pct"],
        "raw_k0": {
            "d_ac_power_db": canon["delta_vs_base"]["d_ac_power_db"],
            "d_floor_above_tip_db": canon["delta_vs_base"]["d_floor_above_tip_db"],
            "d_comb_contrast_db": canon["delta_vs_base"]["d_comb_contrast_db"],
            "d_rhythm_share_pp": canon["delta_vs_base"]["d_rhythm_share_pct"],
        },
        "abs_values_raw": {
            "ac_power_db": canon["ac_power_db"],
            "floor_above_tip_db": canon["floor_above_tip_db"],
            "comb_contrast_db": canon["comb_contrast_db"],
            "rhythm_share_pct": canon["rhythm_share_pct"],
            "beat_hz_track": canon["beat_hz_track"],
        },
        "band_calls": {
            "ac": band_call(canon_k1["delta_vs_base"]["d_ac_power_db"], 0.37),
            "floor": band_call(canon_k1["delta_vs_base"]["d_floor_above_tip_db"], abs(floor_band["-30"])),
            "comb": band_call(canon_k1["delta_vs_base"]["d_comb_contrast_db"], 4.6),
            "rhythm": band_call(canon_k1["delta_vs_base"]["d_rhythm_share_pct"], 21.8),
        },
    },
    "vs_0p9mm_prior_verdict": {
        "prior_ko": "08-16 오전 판(0.9 mm): 요동 −16.99 · 확산 바닥 −12.56 · 빗살 대비 −6.98 dB",
        "reproduced_0p9_here": {
            "d_ac_power_db": p09["delta_vs_base"]["d_ac_power_db"],
            "d_floor_above_tip_db": p09["delta_vs_base"]["d_floor_above_tip_db"],
            "d_comb_contrast_db": p09["delta_vs_base"]["d_comb_contrast_db"],
        },
        "0p9_trimmed_k1": {
            "d_ac_power_db": p09_k1["delta_vs_base"]["d_ac_power_db"],
            "d_floor_above_tip_db": p09_k1["delta_vs_base"]["d_floor_above_tip_db"],
            "d_comb_contrast_db": p09_k1["delta_vs_base"]["d_comb_contrast_db"],
        },
        "prior_estimate_for_1p43_db": -13.0,
    },
    "pattern_survival": {
        "note_ko": "무늬가 사는가 — 맵 상관·박자·리듬 몫·빗살 대비의 절대 수준",
        "by_arm": {k: {"stft_db_map_corr": (arms[k].get("vs_base_waveform") or {}).get("stft_db_map_corr_dc_removed"),
                       "abs_rho": (arms[k].get("vs_base_waveform") or {}).get("abs_rho_dc_removed"),
                       "beat_hz": arms[k]["beat_hz_track"],
                       "rhythm_share_pct": arms[k]["rhythm_share_pct"],
                       "comb_contrast_db": arms[k]["comb_contrast_db"]}
                   for k in arms},
        "map_corr_grid_floor_el_minus30": 0.6825,
    },
}

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("saved", OUT)

# ── 화면 요약 ───────────────────────────────────────────────────────────────
print("\n=== 사다리 (el -30, raw k0) ===")
print(f"{'prop_mm':>8} {'dAC':>9} {'dFLOOR':>9} {'dCOMB':>9} {'dRHY_pp':>9} {'dDC':>9}")
for r in lad_raw:
    print(f"{r['prop_mm']:>8} {r['d_ac_power_db']:>9.3f} {r['d_floor_above_tip_db']:>9.3f} "
          f"{r['d_comb_contrast_db']:>9.3f} {r['d_rhythm_share_pp']:>9.3f} {r['d_dc_power_db']:>9.3f}")
print("\n=== 사다리 (trimmed k=1) ===")
for r in lad_k1:
    print(f"{r['prop_mm']:>8} {r['d_ac_power_db']:>9.3f} {r['d_floor_above_tip_db']:>9.3f} "
          f"{r['d_comb_contrast_db']:>9.3f} {r['d_rhythm_share_pp']:>9.3f} {r['d_dc_power_db']:>9.3f}")
print("\n=== 사다리 (trimmed k=8) ===")
for r in lad_k8:
    print(f"{r['prop_mm']:>8} {r['d_ac_power_db']:>9.3f} {r['d_floor_above_tip_db']:>9.3f} "
          f"{r['d_comb_contrast_db']:>9.3f} {r['d_rhythm_share_pp']:>9.3f} {r['d_dc_power_db']:>9.3f}")
print("\nmono:", json.dumps(mono, ensure_ascii=False))
print("\nisolation:", json.dumps(out["outlier_forensics"]["isolation_by_arm"], ensure_ascii=False))
print("argmax:", json.dumps(out["outlier_forensics"]["argmax_pose_by_arm"], ensure_ascii=False))
print("\nslab cmp:")
for r in slab_cmp:
    print(r)
print("\nabs:", json.dumps({k: {kk: arms[k][kk] for kk in
      ["ac_power_db", "dc_power_db", "floor_above_tip_db", "comb_contrast_db",
       "rhythm_share_pct", "above_f_tip_pct", "beat_hz_track", "level_db_ledger",
       "npaths_median", "ac_over_dc"]} for k in arms}, ensure_ascii=False, indent=1))
print("\npattern:", json.dumps(out["pattern_survival"]["by_arm"], ensure_ascii=False, indent=1))
print("\nangle sub:")
for el, blk in angle_sub.items():
    for k, v in blk.items():
        if "delta_vs_base" in v:
            print(el, k, {kk: v["delta_vs_base"][kk] for kk in
                  ["d_ac_power_db", "d_floor_above_tip_db", "d_comb_contrast_db", "d_rhythm_share_pct", "d_dc_power_db"]},
                  "map_corr", v["vs_base_waveform"]["stft_db_map_corr_dc_removed"])
        else:
            print(el, k, {kk: v[kk] for kk in ["ac_power_db", "floor_above_tip_db", "comb_contrast_db", "ac_over_dc"]})
print("\npairwise:", json.dumps(pairwise, ensure_ascii=False, indent=1))
