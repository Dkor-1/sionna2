# -*- coding: utf-8 -*-
"""기체 교차 판정 — outputs/material_canon_0816_airframes.json

물음: matrice4e 에서 나온 «껍데기는 무관 · 프로펠러가 손잡이» 가 mini5pro · s1000plus 에서도
      성립하나. 기체마다 프롭 크기·재질 비중·백색 널이 다르니 효과 크기를 나란히 놓고,
      각 기체의 **자기 널**로 채점한다.

⛔GPU 0 · ⛔git 없음 · 저장된 원장만 읽는다 (CPU numpy/trimesh).
"""
from __future__ import annotations
import glob
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, "/workspace/sionna/src")
sys.path.insert(0, "/workspace/sionna/benchmark")

import build_md_atlas as A                                    # noqa: E402
from md_mapstyle import flash_spec                            # noqa: E402
from drones import DRONES, DRONE_GROUP_MAT                    # noqa: E402
import material_sources as MS                                 # noqa: E402

OUT = "/workspace/sionna/outputs/material_canon_0816_airframes.json"
MESHDIR = "/workspace/sionna/assets/meshes/drones"

J, Z = A.J, A.Z
PRF = float(J["_meta"]["prf_hz"])
ROWS = {(r["engine"], round(float(r["el_deg"]), 3)): r for r in J["rows"]}
EL = -30.0
HW = 8.0            # 빗살 창 반폭 [Hz] — build_md_atlas.RHY_HW 와 같다
AC_MIN = 8.0
FC = 3.5e9
C = 299792458.0
EPS0 = 8.8541878128e-12

PAIRS = {
    "matrice4e": ("sionna_p4000000000_r15_n8192_d1",
                  "sionna_p4000000000_r15_n8192_shell0.75mm_prop0.9mm_d1"),
    "mini5pro": ("sionna_p4000000000_mini5pro_r15_n8192_d1",
                 "sionna_p4000000000_mini5pro_r15_n8192_shell0.75mm_prop0.9mm_d1"),
    "s1000plus": ("sionna_p4000000000_s1000plus_r15_n8192_d1",
                  "sionna_p4000000000_s1000plus_r15_n8192_shell0.75mm_prop0.9mm_d1"),
}
#: matrice4e 전용 대조군 — 다른 기체엔 **없다**(이번 큐 미착지)
SHELL_ONLY_M4E = {0.5: "sionna_p4000000000_r15_n8192_shell0.5mm_d1",
                  0.75: "sionna_p4000000000_r15_n8192_shell0.75mm_d1",
                  1.5: "sionna_p4000000000_r15_n8192_shell1.5mm_d1"}
PROP_LADDER_M4E = {0.5: "sionna_p4000000000_r15_n8192_shell0.75mm_prop0.5mm_d1",
                   0.9: "sionna_p4000000000_r15_n8192_shell0.75mm_prop0.9mm_d1",
                   1.43: "sionna_p4000000000_r15_n8192_shell0.75mm_prop1.43mm_d1",
                   2.0: "sionna_p4000000000_r15_n8192_shell0.75mm_prop2mm_d1",
                   100.0: "sionna_p4000000000_r15_n8192_shell0.75mm_d1"}

#: 격자 산포 밴드 — ⚠전부 **우리 커널 · matrice4e** 에서 나온 값이다(빌려 씀)
GRID_BAND_AC_DB_BY_EL = {0.0: 3.86, -15.0: 1.31, -30.0: 0.37, -45.0: 0.09,
                         -60.0: 0.02, -75.0: 0.10, -90.0: 5.62}
GRID_BAND_AC_DB_GLOBAL = 3.861
GRID_BAND_FLOOR_DB_AT_M30 = 9.295      # material_verdict_0816.bands
GRID_BAND_RHYTHM_PP = 21.8
GRID_BAND_COMB_DB_BY_EL_M30 = 4.6
GRID_BAND_COMB_DB_GLOBAL = 4.04
GRID_BAND_ABOVE_PP = 12.5549
GRID_BAND_DC_DB = 6.613
SEED_SD_DB = 1.833
COMB_NULL_DB = 3.0                     # 백색 널 자리 폭(실측 백색 +0.4 dB)
TRIM_K = (0, 1, 8)
TRIM_HEADLINE = 1


# ── 잣대(전부 DC 제거 후) ────────────────────────────────────────────────────
def _spec(E):
    x = np.asarray(E, complex)
    x = x - x.mean()
    n = x.size
    P = np.abs(np.fft.fft(x * np.hanning(n))) ** 2
    fa = np.abs(np.fft.fftfreq(n, 1.0 / PRF))
    return x, P, fa


def band_masks(fa, ffl, ft):
    k = np.round(fa / ffl)
    on = np.abs(fa - k * ffl) <= HW
    above = fa >= ft
    below = (fa >= AC_MIN) & (fa < ft)
    return on, above, below


def metrics(E, ffl, ft):
    E = np.asarray(E, complex)
    dc = complex(E.mean())
    x, P, fa = _spec(E)
    on, above, below = band_masks(fa, ffl, ft)
    rs, null, frac_above, degen = A.rhythm_share(E, ffl, ft)
    comb = A.comb_contrast_db(E, ffl, ft)
    ac_lin = float((np.abs(x) ** 2).mean())
    ac_db = 10 * math.log10(ac_lin + 1e-300)
    dc_db = 10 * math.log10(abs(dc) ** 2 + 1e-300)
    d = dict(
        dc_power_db=round(dc_db, 3), ac_power_db=round(ac_db, 3),
        ac_over_dc=float(ac_lin / (abs(dc) ** 2 + 1e-300)),
        rhythm_share_pct=None if rs is None else round(rs, 3),
        rhythm_null_pct=round(null, 3),
        above_f_tip_pct=round(frac_above, 4),
        comb_contrast_db=None if comb is None else round(comb, 3),
        floor_above_tip_db=round(ac_db + 10 * math.log10(frac_above / 100.0), 3),
        p_below_on=float(P[below & on].sum()), p_below_off=float(P[below & ~on].sum()),
        p_above_on=float(P[above & on].sum()), p_above_off=float(P[above & ~on].sum()),
        tip_ceiling_degenerate=bool(degen),
    )
    d["near_numeric_floor"] = bool(d["ac_over_dc"] < 1e-11)
    return d


def dd(a, b):
    return None if (a is None or b is None) else round(a - b, 3)


def db_ratio(a, b):
    return None if not (a > 0 and b > 0) else round(10 * math.log10(a / b), 3)


def spike_stats(E):
    x = np.asarray(E, complex)
    x = x - x.mean()
    v = np.sort(np.abs(x))[::-1]
    med = float(np.median(np.abs(x)))
    if med <= 0:
        return None
    return dict(top1_over_median=round(float(v[0] / med), 2),
                top2_over_median=round(float(v[1] / med), 2),
                isolation=round(float(v[0] / v[1]), 3),
                argmax_pose=int(np.argmax(np.abs(x))))


def trimmed(Eb, Ec, ffl, ft, k):
    """두 팔 통틀어 |AC|/중앙 이 가장 큰 자세 k 개를 **양쪽에서 똑같이** 빼고 다시 잰다."""
    xb = np.asarray(Eb, complex) - np.asarray(Eb, complex).mean()
    xc = np.asarray(Ec, complex) - np.asarray(Ec, complex).mean()
    mb, mc = np.median(np.abs(xb)), np.median(np.abs(xc))
    if not (mb > 0 and mc > 0):
        return None
    rel = np.maximum(np.abs(xb) / mb, np.abs(xc) / mc)
    mask = np.ones(xb.size, bool)
    if k:
        mask[np.argsort(rel)[::-1][:k]] = False
    a, b = metrics(np.asarray(Eb)[mask], ffl, ft), metrics(np.asarray(Ec)[mask], ffl, ft)
    return dict(
        k_trimmed=k, n_kept=int(mask.sum()),
        d_ac_power_db=dd(b["ac_power_db"], a["ac_power_db"]),
        d_dc_power_db=dd(b["dc_power_db"], a["dc_power_db"]),
        d_floor_above_tip_db=dd(b["floor_above_tip_db"], a["floor_above_tip_db"]),
        d_rhythm_pp=dd(b["rhythm_share_pct"], a["rhythm_share_pct"]),
        d_comb_contrast_db=dd(b["comb_contrast_db"], a["comb_contrast_db"]),
        d_above_f_tip_pp=dd(b["above_f_tip_pct"], a["above_f_tip_pct"]),
        d_blade_line_db=db_ratio(b["p_below_on"], a["p_below_on"]),
        d_offcomb_below_db=db_ratio(b["p_below_off"], a["p_below_off"]),
        d_offcomb_above_db=db_ratio(b["p_above_off"], a["p_above_off"]),
        rhythm_base_pct=a["rhythm_share_pct"], rhythm_thin_pct=b["rhythm_share_pct"],
        comb_base_db=a["comb_contrast_db"], comb_thin_db=b["comb_contrast_db"],
    )


# ── 슬래브(ITU-R P.2040 단층, plastic εr 2.7 · σ 0.02, 편파 전력평균) ────────
LAM = C / FC
EPS = 2.7 - 1j * 0.02 / (2 * np.pi * FC * EPS0)


def slab_R2(d_m, th_deg):
    th = np.radians(th_deg)
    s, c = np.sin(th), np.cos(th)
    q = np.sqrt(EPS - s ** 2)
    ph = np.exp(-2j * (2 * np.pi / LAM) * d_m * q)
    tot = 0.0
    for r in ((c - q) / (c + q), (EPS * c - q) / (EPS * c + q)):
        R = r * (1 - ph) / (1 - r ** 2 * ph)
        tot += abs(R) ** 2
    return 0.5 * tot


def slab_row(mm):
    th = np.linspace(0.0, 89.9, 2000)
    w = np.sin(np.radians(th)) * np.cos(np.radians(th))
    avg = float((np.array([slab_R2(mm / 1000, t) for t in th]) * w).sum() / w.sum())
    return dict(normal_db=round(10 * math.log10(slab_R2(mm / 1000, 0.0)), 2),
                angle_avg_db=round(10 * math.log10(avg), 2),
                deg45_db=round(10 * math.log10(slab_R2(mm / 1000, 45.0)), 2))


# ── 재질 비중(메쉬 표면적) ──────────────────────────────────────────────────
def area_census(af):
    import trimesh
    tot = {}
    for f in sorted(glob.glob(os.path.join(MESHDIR, af, f"{af}__*.obj"))):
        grp = os.path.basename(f).split("__")[1][:-4]
        mat = DRONE_GROUP_MAT.get(grp, ("unknown", ""))[0]
        m = trimesh.load(f, process=False, force="mesh")
        tot[mat] = tot.get(mat, 0.0) + float(m.area)
    S = sum(tot.values())
    return dict(total_cm2=round(S * 1e4, 1),
                by_material_cm2={k: round(v * 1e4, 1) for k, v in
                                 sorted(tot.items(), key=lambda kv: -kv[1])},
                by_material_pct={k: round(100 * v / S, 2) for k, v in
                                 sorted(tot.items(), key=lambda kv: -kv[1])})


# ═══════════════════════════════════════════════════════════════════════════
def main():
    canon = MS.blade_thickness_stats()["per_drone"]
    slab = {f"{mm:g}mm": slab_row(mm) for mm in
            (0.5, 0.75, 0.796, 0.9, 1.43, 1.5, 1.989, 2.0, 100.0)}
    base_s = slab["100mm"]
    slab_d = {k: {kk.replace("_db", "_delta_db"): round(v[kk] - base_s[kk], 2) for kk in v}
              for k, v in slab.items() if k != "100mm"}

    # ── matrice4e 프롭 두께 사다리(교정 곡선) ────────────────────────────────
    rt_m = A.arm_rates(PAIRS["matrice4e"][0])
    ffl_m, ft_m = rt_m["f_flash_hz"], A.f_tip_at(rt_m, EL)
    Eb_m = np.asarray(Z[f'{PAIRS["matrice4e"][0]}/el{EL:+.0f}'], complex)
    mb_m = metrics(Eb_m, ffl_m, ft_m)
    ladder = {}
    for mm, arm in sorted(PROP_LADDER_M4E.items()):
        d = metrics(np.asarray(Z[f"{arm}/el{EL:+.0f}"], complex), ffl_m, ft_m)
        ladder[f"{mm:g}mm"] = dict(
            arm=arm,
            d_ac_power_db=dd(d["ac_power_db"], mb_m["ac_power_db"]),
            d_blade_line_db=db_ratio(d["p_below_on"], mb_m["p_below_on"]),
            d_floor_above_tip_db=dd(d["floor_above_tip_db"], mb_m["floor_above_tip_db"]),
            d_dc_power_db=dd(d["dc_power_db"], mb_m["dc_power_db"]),
            slab45_delta_db=slab_d.get(f"{mm:g}mm", {}).get("deg45_delta_db"))
    lad_mm = np.array([0.5, 0.9, 1.43, 2.0])
    lad_db = np.array([ladder[f"{m:g}mm"]["d_blade_line_db"] for m in lad_mm])

    def ladder_at(mm):
        return float(np.interp(math.log(mm), np.log(lad_mm), lad_db))

    # ── 기체별 계산 ──────────────────────────────────────────────────────────
    per_af, wave = {}, {}
    for af, (b, c) in PAIRS.items():
        rt = A.arm_rates(b)
        ffl, ft = rt["f_flash_hz"], A.f_tip_at(rt, EL)
        Eb = np.asarray(Z[f"{b}/el{EL:+.0f}"], complex)
        Ec = np.asarray(Z[f"{c}/el{EL:+.0f}"], complex)
        mb, mc = metrics(Eb, ffl, ft), metrics(Ec, ffl, ft)
        rowb, rowc = ROWS[(b, EL)], ROWS[(c, EL)]
        xb, xc = Eb - Eb.mean(), Ec - Ec.mean()
        rho = float(abs(np.vdot(xb, xc)) / (np.linalg.norm(xb) * np.linalg.norm(xc)))
        co = complex(np.vdot(xb, xc) / np.vdot(xb, xb))
        _, _, Sa, _ = flash_spec(xb, PRF, ffl)
        _, _, Sb, _ = flash_spec(xc, PRF, ffl)
        mapcorr = float(np.corrcoef(
            (10 * np.log10(Sa / Sa.max() + 1e-12)).ravel(),
            (10 * np.log10(Sb / Sb.max() + 1e-12)).ravel())[0, 1])

        # 빗살 대역의 배음 개수 · 상한 위 빈 개수(널의 표본오차)
        fa = np.abs(np.fft.fftfreq(xb.size, 1.0 / PRF))
        bandm = (fa >= 2 * ffl) & (fa <= ft)
        kk = fa / ffl
        n_on = int((bandm & (np.abs(kk - np.round(kk)) * ffl <= HW)).sum())
        n_off = int((bandm & (np.abs(np.abs(kk - np.floor(kk)) - 0.5) * ffl <= HW)).sum())
        above = fa >= ft
        n_ab = int(above.sum())
        n_ab_on = int((above & (np.abs(fa - np.round(fa / ffl) * ffl) <= HW)).sum())
        p = n_ab_on / n_ab
        null_sd = 100 * math.sqrt(p * (1 - p) / (n_ab + 1))

        # 재질 무반응(inert) 몫 — x_c = γ·x_prop + x_inert 두 성분 가정
        gam = 10 ** (ladder["0.9mm"]["d_blade_line_db"] / 20.0)   # matrice4e 실측 진폭비
        g2 = gam * gam
        inert = {}
        for kb in ("p_below_on", "p_below_off", "p_above_on", "p_above_off"):
            r = mc[kb] / mb[kb] if mb[kb] > 0 else None
            inert[kb.replace("p_", "")] = (None if r is None else
                                           round(100 * min(1.0, max(0.0, (r - g2) / (1 - g2))), 2))
        xo = (xc - gam * xb) / (1 - gam)
        inert_share_pct = round(100 * float(np.mean(np.abs(xo) ** 2) / np.mean(np.abs(xb) ** 2)), 3)
        r_o = A.rhythm_share(xo, ffl, ft)
        c_o = A.comb_contrast_db(xo, ffl, ft)

        # 널 정규화 리듬 — «백색 널에서 천장까지» 중 어디에 있나
        def nrm(v):
            return None if v is None else round(100 * (v - mb["rhythm_null_pct"]) /
                                                (100.0 - mb["rhythm_null_pct"]), 2)

        tr = {f"k{k}": trimmed(Eb, Ec, ffl, ft, k) for k in TRIM_K}
        hl = tr[f"k{TRIM_HEADLINE}"]

        per_af[af] = dict(
            drone_label=DRONES[af].name,
            base_arm=b, thin_arm=c, el_deg=EL,
            n_rotors=int(DRONES[af].num_rotors), blades=int(DRONES[af].prop_blades),
            hover_rpm=float(DRONES[af].hover_rpm),
            prop_dia_mm=float(DRONES[af].prop_dia_mm),
            f_flash_hz=round(ffl, 3), f_tip_hz_at_el=round(ft, 1),
            n_poses=int(rowb["n_poses"]), n_missing=[int(rowb["n_missing"]), int(rowc["n_missing"])],
            npaths_median=[rowb["npaths_median"], rowc["npaths_median"]],
            canon_prop_t_chordmean_mm=round(canon[af]["t_chordmean_mm"], 4),
            handle_prop_mm=0.9, handle_shell_mm=0.75,
            handle_over_canon=round(0.9 / canon[af]["t_chordmean_mm"], 3),
            base=mb, thin=mc,
            delta_raw=dict(
                d_ac_power_db=dd(mc["ac_power_db"], mb["ac_power_db"]),
                d_dc_power_db=dd(mc["dc_power_db"], mb["dc_power_db"]),
                d_floor_above_tip_db=dd(mc["floor_above_tip_db"], mb["floor_above_tip_db"]),
                d_rhythm_pp=dd(mc["rhythm_share_pct"], mb["rhythm_share_pct"]),
                d_comb_contrast_db=dd(mc["comb_contrast_db"], mb["comb_contrast_db"]),
                d_above_f_tip_pp=dd(mc["above_f_tip_pct"], mb["above_f_tip_pct"]),
                d_blade_line_db=db_ratio(mc["p_below_on"], mb["p_below_on"]),
                d_offcomb_below_db=db_ratio(mc["p_below_off"], mb["p_below_off"]),
                d_offcomb_above_db=db_ratio(mc["p_above_off"], mb["p_above_off"]),
                d_above_on_db=db_ratio(mc["p_above_on"], mb["p_above_on"])),
            trim=tr, trim_headline_k=TRIM_HEADLINE,
            spike_base=spike_stats(Eb), spike_thin=spike_stats(Ec),
            waveform=dict(abs_rho_dc_removed=round(rho, 6),
                          rho_shuffled_null=round(1 / math.sqrt(xb.size), 6),
                          contain_coeff=round(abs(co), 6),
                          contain_db=round(20 * math.log10(abs(co)), 3),
                          stft_db_map_corr=round(mapcorr, 4)),
            nulls=dict(
                rhythm_null_pct=mb["rhythm_null_pct"],
                rhythm_null_sd_pct=round(null_sd, 3),
                n_bins_above_tip=n_ab, n_bins_above_on_comb=n_ab_on,
                comb_band_hz=[round(2 * ffl, 1), round(ft, 1)],
                comb_harmonics_k=[2, int(ft // ffl)],
                comb_n_on_bins=n_on, comb_n_off_bins=n_off,
                comb_null_db=0.0, comb_null_measured_white_db=0.4,
                note_ko=("널은 기체마다 다르다 — 상한 위 빈 중 정수배 창에 드는 비율이 "
                         "박자·상한·자세 수로 정해진다. 빗살 널은 백색 0 dB(실측 +0.4).")),
            null_normalised_rhythm=dict(
                base_pct_of_span=nrm(mb["rhythm_share_pct"]),
                thin_pct_of_span=nrm(mc["rhythm_share_pct"]),
                d_pct_of_span=None if (mb["rhythm_share_pct"] is None) else
                round(nrm(mc["rhythm_share_pct"]) - nrm(mb["rhythm_share_pct"]), 2),
                base_over_null=round(mb["rhythm_share_pct"] / mb["rhythm_null_pct"], 2),
                thin_over_null=round(mc["rhythm_share_pct"] / mb["rhythm_null_pct"], 2),
                explain_ko="널 대비 배수. 1.0 이면 백색과 구별 불가."),
            inert_share=dict(
                gamma_amp_used=round(gam, 5),
                gamma_source_ko="matrice4e 프롭 0.9 mm 사다리의 **실측** 날개선 진폭비",
                total_ac_inert_pct=inert_share_pct,
                by_band_pct=inert,
                inert_part_rhythm_pct=None if r_o[0] is None else round(r_o[0], 2),
                inert_part_comb_db=None if c_o is None else round(c_o, 2),
                caveat_ko=("두 성분 가정(x_thin = γ·x_prop + x_inert)의 **추정**이다. "
                           "γ 를 각도평균 슬래브로 바꾸면 몫이 바뀐다 — 아래 gamma_sensitivity 참조."),
                gamma_sensitivity=None),
            canon_projection=dict(
                canon_mm=round(canon[af]["t_chordmean_mm"], 4),
                measured_at_0p9mm_blade_line_db=db_ratio(mc["p_below_on"], mb["p_below_on"]),
                ladder_m4e_at_0p9_db=ladder["0.9mm"]["d_blade_line_db"],
                ladder_m4e_at_canon_db=round(ladder_at(canon[af]["t_chordmean_mm"]), 3),
                projected_canon_blade_line_db=round(
                    ladder_at(canon[af]["t_chordmean_mm"])
                    + (db_ratio(mc["p_below_on"], mb["p_below_on"])
                       - ladder["0.9mm"]["d_blade_line_db"]), 3),
                method_ko=("matrice4e 실측 사다리(0.5·0.9·1.43·2 mm)를 log-두께로 보간한 곡선에 "
                           "그 기체의 0.9 mm 실측 오프셋을 얹었다. ⚠**추정**이지 측정이 아니다 — "
                           "matrice4e 만 정본 1.43 mm 를 직접 쟀다(−13.01 dB)."),
                is_measured=bool(af == "matrice4e")),
            area_census=area_census(af),
        )
        wave[af] = (Eb, Ec, ffl, ft)

    # γ 민감도 — 각도평균 슬래브로 바꿔 본다
    for af in per_af:
        Eb, Ec, ffl, ft = wave[af]
        xb, xc = Eb - Eb.mean(), Ec - Ec.mean()
        sens = {}
        for tag, dbv in (("slab_45deg", slab_d["0.9mm"]["deg45_delta_db"]),
                         ("slab_angle_avg", slab_d["0.9mm"]["angle_avg_delta_db"]),
                         ("measured_m4e_blade_line", ladder["0.9mm"]["d_blade_line_db"])):
            g = 10 ** (dbv / 20.0)
            xo = (xc - g * xb) / (1 - g)
            sens[tag] = dict(gamma_db=dbv,
                             total_ac_inert_pct=round(100 * float(
                                 np.mean(np.abs(xo) ** 2) / np.mean(np.abs(xb) ** 2)), 3))
        per_af[af]["inert_share"]["gamma_sensitivity"] = sens

    # ── matrice4e 셸-단독 대조군(다른 기체엔 없다) ──────────────────────────
    shell_only = {}
    for mm, arm in sorted(SHELL_ONLY_M4E.items()):
        d = metrics(np.asarray(Z[f"{arm}/el{EL:+.0f}"], complex), ffl_m, ft_m)
        shell_only[f"{mm:g}mm"] = dict(
            arm=arm,
            d_ac_power_db=dd(d["ac_power_db"], mb_m["ac_power_db"]),
            d_dc_power_db=dd(d["dc_power_db"], mb_m["dc_power_db"]),
            d_floor_above_tip_db=dd(d["floor_above_tip_db"], mb_m["floor_above_tip_db"]),
            d_blade_line_db=db_ratio(d["p_below_on"], mb_m["p_below_on"]))

    # ── 채점 ────────────────────────────────────────────────────────────────
    def outside(v, band):
        return None if (v is None or band is None) else bool(abs(v) > band)

    scoring = {}
    for af, p in per_af.items():
        hl = p["trim"][f"k{TRIM_HEADLINE}"]
        raw = p["delta_raw"]
        scoring[af] = dict(
            headline_uses="trim k=1 (가장 튄 자세 하나 제외)",
            ac_level=dict(d_db=hl["d_ac_power_db"], band_by_el=GRID_BAND_AC_DB_BY_EL[EL],
                          band_global=GRID_BAND_AC_DB_GLOBAL, seed_2sd=2 * SEED_SD_DB,
                          outside_by_el=outside(hl["d_ac_power_db"], GRID_BAND_AC_DB_BY_EL[EL]),
                          outside_global=outside(hl["d_ac_power_db"], GRID_BAND_AC_DB_GLOBAL),
                          outside_seed=outside(hl["d_ac_power_db"], 2 * SEED_SD_DB)),
            blade_line=dict(d_db=hl["d_blade_line_db"], band_by_el=GRID_BAND_AC_DB_BY_EL[EL],
                            outside=outside(hl["d_blade_line_db"], GRID_BAND_AC_DB_BY_EL[EL]),
                            note_ko="⭐날개선(상한 아래 정수배 자리) — 프롭 손잡이의 직접 표적"),
            diffuse_floor=dict(d_db=hl["d_floor_above_tip_db"], band=GRID_BAND_FLOOR_DB_AT_M30,
                               outside=outside(hl["d_floor_above_tip_db"], GRID_BAND_FLOOR_DB_AT_M30)),
            dc_level=dict(d_db=hl["d_dc_power_db"], band=GRID_BAND_DC_DB,
                          outside=outside(hl["d_dc_power_db"], GRID_BAND_DC_DB)),
            rhythm=dict(d_pp=hl["d_rhythm_pp"], band_pp=GRID_BAND_RHYTHM_PP,
                        outside=outside(hl["d_rhythm_pp"], GRID_BAND_RHYTHM_PP),
                        null_pct=p["nulls"]["rhythm_null_pct"],
                        base_over_null=p["null_normalised_rhythm"]["base_over_null"],
                        thin_over_null=p["null_normalised_rhythm"]["thin_over_null"],
                        d_pct_of_span=p["null_normalised_rhythm"]["d_pct_of_span"]),
            comb=dict(d_db_raw=raw["d_comb_contrast_db"], d_db_trim1=hl["d_comb_contrast_db"],
                      band_by_el=GRID_BAND_COMB_DB_BY_EL_M30, band_global=GRID_BAND_COMB_DB_GLOBAL,
                      outside_by_el=outside(hl["d_comb_contrast_db"], GRID_BAND_COMB_DB_BY_EL_M30),
                      outside_global=outside(hl["d_comb_contrast_db"], GRID_BAND_COMB_DB_GLOBAL),
                      both_sides_far_from_null=bool(
                          (hl["comb_base_db"] or 0) > COMB_NULL_DB and (hl["comb_thin_db"] or 0) > COMB_NULL_DB),
                      n_harmonics=p["nulls"]["comb_harmonics_k"][1] - 1,
                      trim_flips_verdict=bool(
                          outside(raw["d_comb_contrast_db"], GRID_BAND_COMB_DB_BY_EL_M30)
                          != outside(hl["d_comb_contrast_db"], GRID_BAND_COMB_DB_BY_EL_M30))),
            above_ceiling=dict(d_pp=hl["d_above_f_tip_pp"], band_pp=GRID_BAND_ABOVE_PP,
                               outside=outside(hl["d_above_f_tip_pp"], GRID_BAND_ABOVE_PP)),
            flags=[f for f in ("near_numeric_floor", "tip_ceiling_degenerate")
                   if p["base"][f] or p["thin"][f]],
        )

    # ── matrice4e 앙각 일반성(단일 −30 점이 대표성이 있나) ─────────────────
    el_gen = {}
    for e in (0.0, -15.0, -30.0, -60.0):
        ft_e = A.f_tip_at(rt_m, e)
        a_ = metrics(np.asarray(Z[f'{PAIRS["matrice4e"][0]}/el{e:+.0f}'], complex), ffl_m, ft_e)
        b_ = metrics(np.asarray(Z[f'{PAIRS["matrice4e"][1]}/el{e:+.0f}'], complex), ffl_m, ft_e)
        el_gen[f"el{e:+.0f}"] = dict(
            d_ac_power_db=dd(b_["ac_power_db"], a_["ac_power_db"]),
            d_blade_line_db=db_ratio(b_["p_below_on"], a_["p_below_on"]),
            d_dc_power_db=dd(b_["dc_power_db"], a_["dc_power_db"]),
            d_rhythm_pp=dd(b_["rhythm_share_pct"], a_["rhythm_share_pct"]))

    # ── 프롭만 대조군(matrice4e 전용) — «AC 는 프롭이 전부인가» ────────────
    pm = metrics(np.asarray(Z["sionna_p4000000000_partsprop_r15_n8192_d1/el-30"], complex),
                 ffl_m, ft_m)
    xb_m = Eb_m - Eb_m.mean()
    xp_m = (np.asarray(Z["sionna_p4000000000_partsprop_r15_n8192_d1/el-30"], complex)
            - np.asarray(Z["sionna_p4000000000_partsprop_r15_n8192_d1/el-30"], complex).mean())
    props_only = dict(
        arm="sionna_p4000000000_partsprop_r15_n8192_d1",
        d_ac_power_db=dd(pm["ac_power_db"], mb_m["ac_power_db"]),
        d_dc_power_db=dd(pm["dc_power_db"], mb_m["dc_power_db"]),
        d_blade_line_db=db_ratio(pm["p_below_on"], mb_m["p_below_on"]),
        d_offcomb_below_db=db_ratio(pm["p_below_off"], mb_m["p_below_off"]),
        d_offcomb_above_db=db_ratio(pm["p_above_off"], mb_m["p_above_off"]),
        abs_rho_vs_full=round(float(abs(np.vdot(xb_m, xp_m))
                                    / (np.linalg.norm(xb_m) * np.linalg.norm(xp_m))), 4),
        verdict_ko=("matrice4e 는 프롭만 남겨도 움직이는 부분이 전 대역에서 0.7 dB 안으로 "
                    "재현된다(ρ 0.99) — «AC 는 프롭이 전부» 가 **측정**이다. "
                    "⚠같은 대조군이 mini5pro·s1000plus 에는 없다."))

    # ── 널을 잘못 대면 어떻게 읽히나 ────────────────────────────────────────
    m4e_null = per_af["matrice4e"]["nulls"]["rhythm_null_pct"]
    null_misread = {}
    for af, p in per_af.items():
        own = p["nulls"]["rhythm_null_pct"]
        tv = p["thin"]["rhythm_share_pct"]
        bv = p["base"]["rhythm_share_pct"]
        null_misread[af] = dict(
            own_null_pct=own, borrowed_m4e_null_pct=m4e_null,
            base_over_own=round(bv / own, 2), base_over_borrowed=round(bv / m4e_null, 2),
            thin_over_own=round(tv / own, 2), thin_over_borrowed=round(tv / m4e_null, 2),
            margin_error_pct=round(100 * ((tv / m4e_null) / (tv / own) - 1), 1))

    out = dict(
        _meta=dict(
            generator="scratchpad/build_airframe_canon_verdict.py (기체 교차 판정자 갈래)",
            date_kst="2026-08-16",
            question_ko=("matrice4e 에서 나온 «껍데기는 무관 · 프로펠러가 손잡이» 가 "
                         "mini5pro · s1000plus 에서도 성립하나 — 효과 크기와 기체별 널로 채점"),
            inputs=["outputs/elevation_sweep_md.json", "outputs/elevation_sweep_md.npz",
                    "outputs/material_verdict_0816.json(밴드·사전등록 문면)",
                    "outputs/grid_convergence_check.json(격자 밴드 출처)",
                    "outputs/mesh_audit_0816_prop_geometry.json(정본 두께 감사)",
                    "assets/meshes/drones/*/*.obj(재질 비중)"],
            conventions_ko=(
                "① 모든 레벨은 **정지 성분(DC) 제거 후**. ② 날개선 = 상한 아래 박자 정수배 자리의 "
                "전력, 배경 = 정수배가 아닌 자리. ③ 잣대는 팔마다 **그 기체의 박자·상한**을 쓴다"
                "(matrice4e 126.67 · mini5pro 183.33 · s1000plus 148.90 Hz). "
                "④ 리듬 몫의 백색 널도 기체마다 다르다(12.65 · 8.72 · 10.76 %). "
                "⑤ 튀는 자세(이상값) 솎기 전/후를 둘 다 싣고 헤드라인은 솎은 값(k=1). "
                "⑥ 팔은 전부 PathSolver 4e9 · 물리끔 · 깊이1 · 15 m · seed 1 로 **짝지은 비교**."),
            gpu_used=False,
            landed_arms_ko=("기체 교차에 실제로 착지한 칸은 **앙각 −30° 한 점**뿐이다 — "
                            "mini5pro·s1000plus 는 정정판(셸0.75+프롭0.9)이 −30° 에만 있다."),
        ),
        airframes=per_af,
        matrice4e_reference=dict(
            shell_only_control=shell_only,
            prop_thickness_ladder=ladder,
            props_only_control=props_only,
            elevation_generality=el_gen,
            note_ko=("⭐셸 단독 팔·프롭 사다리·프롭만 대조군은 **matrice4e 에만** 있다. "
                     "다른 두 기체는 결합판(셸0.75+프롭0.9) 한 칸뿐이라 셸과 프롭을 분리할 수 없다. "
                     "앙각 일반성은 matrice4e 에서만 확인된다 — 날개선 변화가 −15·−30·−60 에서 "
                     "−14.1 · −17.0 · −15.0 dB 로 ±1.5 dB 안이라, 단일 −30 점 교차가 "
                     "적어도 matrice4e 에서는 대표성이 있다."),
        ),
        null_misread_check=dict(
            question_ko="matrice4e 의 널(12.65 %)을 다른 기체에 그대로 대면 얼마나 잘못 읽나",
            per_airframe=null_misread,
            verdict_ko=("이번 세 칸에서는 널을 빌려 써도 판정이 **뒤집히지는 않는다** — "
                        "다만 «백색 대비 몇 배인가» 라는 여유가 s1000plus 에서 2.15 → 1.83 배로 "
                        "15 % 줄어 보이고 mini5pro 에서는 9.66 → 6.66 배로 31 % 줄어 보인다. "
                        "s1000plus 처럼 원래 여유가 얇은 기체에서 이 오차가 결론을 건드릴 자리다."),
        ),
        canon_thickness_mm={k: round(v["t_chordmean_mm"], 4) for k, v in canon.items()
                            if k in PAIRS},
        slab_predictions_3p5ghz=dict(abs=slab, delta_vs_100mm=slab_d,
                                     note_ko="ITU-R P.2040 단층 슬래브, plastic εr 2.7·σ 0.02, 편파 전력평균"),
        bands=dict(
            source_ko=("⚠격자 산포 밴드는 전부 **우리 커널 · matrice4e**(λ/12↔λ/24)에서 나왔다. "
                       "mini5pro·s1000plus 에는 자기 격자 밴드가 없어 **빌려 썼다** — "
                       "이 갈래의 가장 큰 잣대 구멍이다."),
            ac_db_by_el=GRID_BAND_AC_DB_BY_EL, ac_db_global=GRID_BAND_AC_DB_GLOBAL,
            floor_db_at_el_minus30=GRID_BAND_FLOOR_DB_AT_M30,
            dc_db=GRID_BAND_DC_DB, rhythm_pp=GRID_BAND_RHYTHM_PP,
            comb_db_at_el_minus30=GRID_BAND_COMB_DB_BY_EL_M30, comb_db_global=GRID_BAND_COMB_DB_GLOBAL,
            above_ceiling_pp=GRID_BAND_ABOVE_PP,
            seed_sd_db=SEED_SD_DB, seed_note_ko="빌려 온 값(el −15 · 40 m · 4e9)",
        ),
        scoring=scoring,
    )

    # ── 효과 크기 나란히 ────────────────────────────────────────────────────
    def col(f):
        return {af: f(per_af[af]) for af in ("matrice4e", "mini5pro", "s1000plus")}

    out["effect_size_side_by_side"] = dict(
        note_ko=("앙각 −30° · 손잡이는 세 기체 모두 같다(셸 0.75 · 프롭 0.9 mm). "
                 "헤드라인은 솎은 값(k=1), 괄호 값은 생값."),
        canon_prop_thickness_mm=col(lambda p: p["canon_prop_t_chordmean_mm"]),
        handle_over_canon=col(lambda p: p["handle_over_canon"]),
        prop_dia_mm=col(lambda p: p["prop_dia_mm"]),
        n_rotors=col(lambda p: p["n_rotors"]),
        prop_area_pct=col(lambda p: p["area_census"]["by_material_pct"].get("prop_plastic")),
        shell_plastic_area_pct=col(lambda p: p["area_census"]["by_material_pct"].get("plastic")),
        carbon_area_pct=col(lambda p: p["area_census"]["by_material_pct"].get("carbon", 0.0)),
        d_blade_line_db_trim1=col(lambda p: p["trim"]["k1"]["d_blade_line_db"]),
        d_blade_line_db_raw=col(lambda p: p["delta_raw"]["d_blade_line_db"]),
        d_ac_power_db_trim1=col(lambda p: p["trim"]["k1"]["d_ac_power_db"]),
        d_floor_above_tip_db_trim1=col(lambda p: p["trim"]["k1"]["d_floor_above_tip_db"]),
        d_dc_power_db_trim1=col(lambda p: p["trim"]["k1"]["d_dc_power_db"]),
        d_comb_contrast_db_raw=col(lambda p: p["delta_raw"]["d_comb_contrast_db"]),
        d_comb_contrast_db_trim1=col(lambda p: p["trim"]["k1"]["d_comb_contrast_db"]),
        d_rhythm_pp_trim1=col(lambda p: p["trim"]["k1"]["d_rhythm_pp"]),
        d_above_ceiling_pp_trim1=col(lambda p: p["trim"]["k1"]["d_above_f_tip_pp"]),
        offcomb_background_delta_db=col(lambda p: [p["delta_raw"]["d_offcomb_below_db"],
                                                  p["delta_raw"]["d_offcomb_above_db"]]),
        material_inert_ac_pct=col(lambda p: p["inert_share"]["total_ac_inert_pct"]),
        material_inert_offcomb_pct=col(lambda p: [p["inert_share"]["by_band_pct"]["below_off"],
                                                  p["inert_share"]["by_band_pct"]["above_off"]]),
        rhythm_null_pct=col(lambda p: p["nulls"]["rhythm_null_pct"]),
        rhythm_over_null_base=col(lambda p: p["null_normalised_rhythm"]["base_over_null"]),
        rhythm_over_null_thin=col(lambda p: p["null_normalised_rhythm"]["thin_over_null"]),
        abs_rho=col(lambda p: p["waveform"]["abs_rho_dc_removed"]),
        stft_map_corr=col(lambda p: p["waveform"]["stft_db_map_corr"]),
        projected_canon_blade_line_db=col(
            lambda p: p["canon_projection"]["projected_canon_blade_line_db"]),
    )

    out["wiring_check"] = dict(
        question_ko=("mini5pro·s1000plus 에는 el 0 배선 대조군이 없다 — 그러면 s1000plus 의 "
                     "ΔDC ≈ 0 이 «물리» 인지 «손잡이가 안 걸린 것» 인지 어떻게 아나"),
        evidence_ko=(
            "손잡이는 확실히 걸렸다 — 같은 팔에서 날개선 전력이 −15.08 dB 내려갔다. "
            "set_thickness_mm(shell=0.75, prop=0.9) 은 plastic·plastic_blue·prop_plastic 을 "
            "**한 번에** 물리므로, 프롭이 반응했다는 것은 셸도 같은 호출로 얇아졌다는 뜻이다. "
            "s1000plus 의 body·canopy·gear·accent 는 전부 DRONE_GROUP_MAT 에서 plastic 이라 "
            "손잡이 범위 안에 있다. 그러므로 ΔDC −0.15 dB 는 배선 실패가 아니라 "
            "«그 기체의 정지 에코가 플라스틱이 아니다» 는 물리다."),
        blade_line_response_db={af: per_af[af]["delta_raw"]["d_blade_line_db"] for af in per_af},
        plastic_groups_in_mesh={af: sorted(
            g for g in ("body", "canopy", "gear", "accent")
            if os.path.exists(os.path.join(MESHDIR, af, f"{af}__{g}.obj"))) for af in per_af},
        residual_risk_ko=("⚠남는 위험은 «셸이 얇아졌는데 DC 가 안 움직였다» 를 직접 본 것이 "
                          "아니라는 점이다. 셸 단독 팔이 있으면 한 칸으로 닫힌다."),
    )

    out["metric_caveats"] = dict(
        comb_harmonic_count_ko=(
            "빗살 대비의 대역(2·f_flash ~ f_tip)에 들어가는 배음 수가 기체마다 다르다 — "
            "matrice4e 7 개(253~1102 Hz) · mini5pro **3 개**(367~887 Hz) · s1000plus 11 개"
            "(298~1802 Hz). mini5pro 는 정의 최소치(3 개) 바로 위라 이 기체의 빗살 수는 "
            "셋 중 가장 약한 통계다 — 판정에 그대로 쓰되 꼬리표를 단다."),
        comb_grid_tag_ko=("빗살 대비 절대값은 격자 계단마다 +4.0~5.6 dB 단조 상승한다 — "
                          "절대 인용에는 항상 격자 꼬리표를 붙인다."),
        band_borrowed_ko=("⚠이 갈래의 모든 밴드는 우리 커널·matrice4e 격자(λ/12↔λ/24)에서 왔다. "
                          "mini5pro·s1000plus 용 격자 밴드는 존재하지 않는다."),
        seed_band_borrowed_ko=("PathSolver 시드 밴드(sd 1.833 dB)도 el −15·40 m 에서 빌려 온 값이다. "
                               "다만 이번 비교는 seed=1 로 고정된 짝지은 비교라 표집 요동이 "
                               "대부분 소거된다."),
    )

    out["verdict"] = dict(
        headline_ko=(
            "① **«프로펠러가 손잡이» 는 세 기체 모두에서 성립한다.** 날개선(박자 정수배 자리) "
            "전력이 프롭 0.9 mm 에서 matrice4e −16.99 · mini5pro −14.51 · s1000plus −15.08 dB "
            "내려간다 — 셋이 2.5 dB 폭 안에 모이고, 전부 그 앙각의 격자 밴드(0.37 dB)와 "
            "시드 밴드(2sd 3.67 dB) 밖이다. 재질 무반응 몫도 날개선에서는 0~1.6 % 뿐이다. "
            "② **«껍데기는 무관» 은 다른 두 기체에서 직접 못 쟀다.** 셸 단독 팔이 matrice4e "
            "에만 착지했고, 결합판 한 칸으로는 셸(0.75 mm, 45° −18.21 dB)과 프롭(0.9 mm, "
            "−16.65 dB)의 감쇠가 1.6 dB 밖에 안 벌어져 분리가 원리적으로 불가능하다. "
            "③ **정지 성분(DC) 쪽은 기체마다 완전히 다르다.** ΔDC 는 matrice4e −13.81 · "
            "mini5pro −15.60 인데 s1000plus 는 **−0.15 dB**(밴드 6.61 안 — 판정 불가, "
            "짝지은 비교라 사실상 0). s1000plus 의 정지 에코는 플라스틱이 아니라 카본·금속이다"
            "(표면적 21.6 % 카본, 두께 손잡이는 카본을 일부러 안 건드린다 — 표피깊이 0.155 mm). "
            "④ **«확산 바닥» 헤드라인은 일반화되지 않는다.** 상한 위 바닥이 matrice4e −12.56 · "
            "mini5pro −14.47 dB 인데 s1000plus 는 −0.07 dB(밴드 9.30 안). s1000plus 는 정수배가 "
            "아닌 배경이 통째로 재질 무반응(추정 ~100 %)이라, 프롭을 −15 dB 어둡게 해도 배경이 "
            "안 따라 내려온다. ⑤ 그래서 s1000plus 만 **스펙트럼의 성격이 바뀐다** — 상한 위 몫 "
            "3.60 → 51.91 %(+48.3 %p, 밴드 12.55 밖)·파형 상관 0.698·맵 상관 0.706, "
            "리듬 여유는 자기 널의 3.37 → 2.15 배로 반 토막. matrice4e·mini5pro 는 "
            "ρ 0.95~0.98 · 맵 상관 0.89 로 무늬가 그대로다."),
        claim_scorecard=dict(
            prop_is_the_handle=dict(matrice4e="성립(측정)", mini5pro="성립(측정)",
                                    s1000plus="성립(측정) — 단 날개선 축에서만"),
            shell_is_irrelevant_to_target_axis=dict(
                matrice4e="성립(측정 — 셸 단독 ΔAC +0.003 dB · ρ 1.0000)",
                mini5pro="판정 불가 — 셸 단독 팔 미착지",
                s1000plus="판정 불가 — 셸 단독 팔 미착지(다만 셸을 얇게 해도 DC 조차 "
                          "안 움직이니 셸 자체가 이 기체에서 거의 안 보인다)"),
            diffuse_floor_drops_with_prop=dict(
                matrice4e="성립(−12.56 dB, 밴드 9.30 밖)",
                mini5pro="성립(−14.47 dB, 밴드 밖)",
                s1000plus="**반증** — −0.07 dB(밴드 안). 이 기체에서는 프롭이 바닥의 손잡이가 아니다"),
            pattern_survives_material_correction=dict(
                matrice4e="성립(리듬 −5.6 %p·빗살 −3.4 dB, 둘 다 밴드 안 · 맵 상관 0.892)",
                mini5pro="대체로 성립(리듬 −4.4 %p 밴드 안, 빗살 −6.45 dB 는 밴드 밖 · 맵 상관 0.894)",
                s1000plus="**흔들린다** — 빗살 −11.52 dB·상한 위 몫 +48.3 %p(둘 다 밴드 밖)·"
                          "맵 상관 0.706(격자 바닥 0.6825 바로 위)"),
        ),
        effect_size_ordering_ko=(
            "같은 손잡이(0.9 mm)에서 날개선 효과 크기는 matrice4e(−16.99) > s1000plus(−15.08) "
            "≳ mini5pro(−14.51) 순이지만, 이 순서는 **비교로서 의미가 약하다** — 0.9 mm 가 "
            "기체마다 자기 정본 두께의 63 % · 45 % · 113 % 로 서로 다른 자리이기 때문이다. "
            "각 기체의 **정본 두께**로 옮기면 순서가 뒤집힌다: mini5pro(0.80 mm) −15.6 · "
            "matrice4e(1.43 mm) −13.0 · s1000plus(1.99 mm) −8.3 dB. 즉 날이 얇은 기체일수록 "
            "재질 정정으로 더 많이 잃는다. ⚠matrice4e 만 정본 점을 직접 쟀고(−13.01 dB) "
            "나머지 둘은 사다리 보간 + 그 기체의 0.9 mm 오프셋으로 만든 **추정**이다."),
        why_s1000plus_differs_ko=(
            "가장 그럴듯한 읽기는 «가려지는 쪽의 재질» 이다. matrice4e 는 프롭만 남겨도 움직이는 "
            "부분이 전 대역 0.7 dB 안으로 재현된다(ρ 0.99) — 움직이는 에코가 곧 프롭 자기 에코다. "
            "s1000plus 는 큰 프롭 8 장이 넓은 카본 프레임 위를 쓸고 지나가는데, 카본은 두께 손잡이가 "
            "손대지 않는 재질이라 그 그림자 변조가 재질 정정에 통째로 무반응으로 남는다. "
            "⚠이건 **추론**이다 — s1000plus 용 «프롭만» 대조군이 없어 확정할 수 없다. "
            "배경이 백색도 아니다(스펙트럼 평탄도 0.09~0.37, 백색 0.56) — 단순 표본잡음으로 "
            "설명하는 읽기도 이 수치가 지지하지 않는다."),
        outlier_forensics_ko=(
            "세 기체 모두 튐 고립도(최대÷둘째)가 1.00~1.03 이다 — 한 자세만 유별난 것이 아니라 "
            "로터 대칭이 만든 **구조적 플래시**라는 뜻이다. 그래도 규약대로 솎아 보면 "
            "**matrice4e 의 빗살 대비만 판정이 뒤집힌다**: 생값 −6.98 dB(밴드 4.6 밖)가 "
            "가장 튄 자세 하나를 빼면 −3.43 dB(밴드 안)가 된다. mini5pro(−6.43→−6.45)와 "
            "s1000plus(−12.81→−11.52)는 안 뒤집힌다. ⭐그래서 material_verdict_0816 의 "
            "«빗살 −6.98 dB» 인용은 솎기에 취약한 수다 — 헤드라인은 −3.43 dB(판정 불가)로 "
            "적는 것이 규약에 맞다."),
        untested_ko=[
            "셸 단독 × mini5pro · s1000plus — 미착지. «껍데기는 무관» 의 다른 기체 판정이 여기 걸려 있다.",
            "프롭만(parts) 대조군 × mini5pro · s1000plus — 미착지. s1000plus 배경의 정체를 못 가른다.",
            "el 0 배선 대조군 × mini5pro · s1000plus — 미착지(결합판이 −30 에만 있다).",
            "기체별 격자 산포 밴드 — 없다. 이번 채점은 matrice4e 밴드를 **빌려 썼다**.",
            "정본 두께 점(mini5pro 0.80 · s1000plus 1.99 mm) 실측 — 미착지. 사다리 보간 추정뿐이다.",
            "빗각 다른 앙각(−15·−60) × mini5pro · s1000plus — 미착지. 교차는 −30 한 점이다.",
        ],
        honest_limits_ko=(
            "이 갈래가 실제로 판정한 것은 «셸 0.75 + 프롭 0.9 결합 정정이 앙각 −30° 에서 "
            "기체마다 무엇을 얼마나 바꾸나» 다. «셸 따로 · 프롭 따로» 는 matrice4e 에서만 "
            "갈렸다. 세 기체 사이의 비교는 밴드를 빌려 쓴 채로 한 것이라, 밴드 근처의 판정"
            "(빗살·리듬)은 밴드가 기체별로 다시 잡히면 바뀔 수 있다."),
    )
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("saved", OUT)
    return out


if __name__ == "__main__":
    o = main()
    for af, p in o["airframes"].items():
        h = p["trim"]["k1"]
        print(f'{af:10s} dAC={h["d_ac_power_db"]:8.3f} dBlade={h["d_blade_line_db"]:8.3f} '
              f'dFloor={h["d_floor_above_tip_db"]:8.3f} dDC={h["d_dc_power_db"]:8.3f} '
              f'dComb={h["d_comb_contrast_db"]} rho={p["waveform"]["abs_rho_dc_removed"]}')
