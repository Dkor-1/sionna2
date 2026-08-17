#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""outputs/material_canon_0816_h5_refraction.json 을 굽는다 — H5 투과 반대항 판정."""
from __future__ import annotations
import datetime as dt, glob, json, os, sys, zoneinfo
import numpy as np
ROOT = "/workspace/sionna"
sys.path.insert(0, f"{ROOT}/src"); sys.path.insert(0, f"{ROOT}/benchmark")
import build_md_atlas as A                                              # noqa: E402
Z, ROW, PRF = A.Z, A.ROW, A.PRF
FFL = float(A.J["_meta"]["f_flash_hz"])
SHD = f"{ROOT}/outputs/elev_sweep_shards"
rng = np.random.default_rng(0)
KST = zoneinfo.ZoneInfo("Asia/Seoul")

OFF100 = "sionna_p4000000000_r15_n8192_d1"
REF100 = "sionna_p4000000000_onlyrefr_r15_n8192"
SETS = {
    "shell0.75_prop0.9": ("sionna_p4000000000_r15_n8192_shell0.75mm_prop0.9mm_d1",
                          "sionna_p4000000000_onlyrefr_r15_n8192_shell0.75mm_prop0.9mm"),
    "shell0.75_prop1.43": ("sionna_p4000000000_r15_n8192_shell0.75mm_prop1.43mm_d1",
                           "sionna_p4000000000_onlyrefr_r15_n8192_shell0.75mm_prop1.43mm"),
}
DA = json.load(open(f"{ROOT}/outputs/depth_axis_verdict_0816.json"))
MV = json.load(open(f"{ROOT}/outputs/material_verdict_0816.json"))
NB = DA["null_bands"]
BAND_AC = {float(k): v for k, v in NB["grid_dispersion_ac_db_by_el"].items()}
BAND_COMB = {float(k): v for k, v in NB["grid_dispersion_comb_db_by_el"].items()}
BAND_RHY = {float(k): v for k, v in NB["grid_dispersion_rhythm_pp_by_el"].items()}
BAND_FLOOR = MV["bands"]["floor_above_tip_grid_db"]


def ser(a, el): return np.asarray(Z[f"{a}/el{el:+.0f}"], complex)
def r3(x): return None if x is None else round(float(x), 3)


def met(E, ft):
    E = np.asarray(E, complex); x = E - E.mean()
    acp = float(np.mean(np.abs(x)**2)); dcp = float(np.abs(E.mean())**2)
    sh, null, fa, degen = A.rhythm_share(E, FFL, ft)
    cb = A.comb_contrast_db(E, FFL, ft)
    p = np.abs(x)**2; v = np.sort(np.abs(x))[::-1]
    return dict(
        ac_power_db=r3(10*np.log10(acp)), dc_power_db=r3(10*np.log10(dcp)),
        ac_over_dc=r3(acp/dcp) if dcp > 0 else None,
        near_numeric_floor=bool(dcp > 0 and acp/dcp < 1e-11),
        floor_above_tip_db=r3(10*np.log10(acp) + 10*np.log10(fa/100.0)) if fa else None,
        comb_contrast_db=r3(cb), rhythm_share_pct=r3(sh), rhythm_null_pct=r3(null),
        above_f_tip_pct=None if fa is None else round(float(fa), 4),
        n_eff_poses=round(float(p.sum()**2/np.sum(p**2)), 1),
        top8_energy_pct=round(100*float(np.sort(p)[::-1][:8].sum()/p.sum()), 3),
        top1_over_median=round(float(v[0]/np.median(np.abs(x))), 2),
        isolation=round(float(v[0]/v[1]), 3))


def worst(series, k):
    n = series[0].size; rel = np.zeros(n)
    for E in series:
        x = E - E.mean(); m = np.median(np.abs(x))
        if m > 0:
            rel = np.maximum(rel, np.abs(x)/m)
    return [int(i) for i in np.argsort(rel)[::-1][:k]]


def replace_poses(E, idx):
    y = np.asarray(E, complex).copy(); n = y.size; s = set(idx)
    for i in idx:
        nb = [j for j in (i-2, i-1, i+1, i+2) if 0 <= j < n and j not in s]
        if nb:
            y[i] = np.mean(np.asarray(E, complex)[nb])
    return y


def shard_np(arm, el):
    fs = sorted(glob.glob(f"{SHD}/{arm}_el{el:+.0f}_*.npz"))
    npa = []
    for f in fs:
        z = np.load(f)
        if "npaths" in z:
            npa.append(np.asarray(z["npaths"]))
        z.close()
    if not npa:
        return None
    v = np.concatenate(npa).astype(float)
    return dict(n_shards=len(fs), n=int(v.size), median=float(np.median(v)),
                mean=round(float(v.mean()), 2), p10=float(np.percentile(v, 10)),
                p90=float(np.percentile(v, 90)), min=float(v.min()), max=float(v.max()))


def rowmeta(arm, el):
    r = ROW[(arm, el)]
    return dict(arm=arm, el_deg=el, shell_mm=r["shell_mm"], prop_mm=r["prop_mm"],
                max_depth=r["max_depth"], range_m=r["range_m"], spp=r["spp"],
                az_deg=r["az_deg"], fc_hz=r["fc_hz"], n_poses=r["n_poses"],
                n_missing=r["n_missing"], f_tip_hz=r["f_tip_hz"],
                npaths_median=r["npaths_median"], ledger_level_db=r["level_db"],
                seconds=r["seconds"])


# ── 칸 ──────────────────────────────────────────────────────────────────────
cells = {}
for arm, els in [(OFF100, (0.0, -30.0)), (REF100, (0.0, -30.0)),
                 (SETS["shell0.75_prop0.9"][0], (0.0, -30.0)),
                 (SETS["shell0.75_prop0.9"][1], (0.0, -30.0)),
                 (SETS["shell0.75_prop1.43"][0], (-30.0,)),
                 (SETS["shell0.75_prop1.43"][1], (-30.0,))]:
    for el in els:
        ft = ROW[(arm, el)]["f_tip_hz"]
        cells[f"{arm}/el{el:+.0f}"] = {**rowmeta(arm, el), **met(ser(arm, el), ft),
                                       "npaths_shard": shard_np(arm, el)}

# ── 짝 ──────────────────────────────────────────────────────────────────────
KEYS = ["ac_power_db", "dc_power_db", "floor_above_tip_db", "comb_contrast_db",
        "rhythm_share_pct", "above_f_tip_pct"]
pairs = []
for tag, (offT, refT) in SETS.items():
    for el in (0.0, -30.0):
        if (refT, el) not in ROW or (offT, el) not in ROW:
            continue
        ft = ROW[(OFF100, el)]["f_tip_hz"]
        S = dict(off_100=ser(OFF100, el), off_thin=ser(offT, el),
                 ref_100=ser(REF100, el), ref_thin=ser(refT, el))
        M = {k: met(v, ft) for k, v in S.items()}
        d_off = {k: r3(M["off_thin"][k]-M["off_100"][k]) for k in KEYS}
        d_ref = {k: r3(M["ref_thin"][k]-M["ref_100"][k]) for k in KEYS}
        did = {k: r3(d_ref[k]-d_off[k]) for k in KEYS}

        # 솎기 — 삭제 vs 갈아끼우기(두 방법 다 싣는다)
        trim = {}
        for k_ in (1, 8):
            bad = worst(list(S.values()), k_)
            for how, f in (("drop", lambda v: np.delete(v, bad)),
                           ("replace", lambda v: replace_poses(v, bad))):
                Mt = {kk: met(f(v), ft) for kk, v in S.items()}
                do = {kk: r3(Mt["off_thin"][kk]-Mt["off_100"][kk]) for kk in KEYS}
                dr = {kk: r3(Mt["ref_thin"][kk]-Mt["ref_100"][kk]) for kk in KEYS}
                trim[f"{how}{k_}"] = dict(worst_poses=bad,
                                          did={kk: r3(dr[kk]-do[kk]) for kk in KEYS})

        # 무해 검사 — 죄 없는 자세 하나를 40 번 갈아 끼운다
        acc = []
        for _ in range(40):
            i = int(rng.integers(0, 8192))
            Mt = {kk: met(replace_poses(v, [i]), ft) for kk, v in S.items()}
            acc.append((Mt["ref_thin"]["ac_power_db"]-Mt["ref_100"]["ac_power_db"])
                       - (Mt["off_thin"]["ac_power_db"]-Mt["off_100"]["ac_power_db"]))
        innocent = dict(mean=r3(np.mean(acc)), sd=round(float(np.std(acc)), 4),
                        min=r3(np.min(acc)), max=r3(np.max(acc)))

        # 반쪽·블록 부트스트랩(스스로 잰 문턱 — 빌려 온 밴드가 아니다)
        def did_ac(sub):
            m = {kk: met(v, ft) for kk, v in sub.items()}
            return ((m["ref_thin"]["ac_power_db"]-m["ref_100"]["ac_power_db"])
                    - (m["off_thin"]["ac_power_db"]-m["off_100"]["ac_power_db"]))
        halves = {nm: r3(did_ac({k: v[sl] for k, v in S.items()}))
                  for nm, sl in (("A", slice(0, 4096)), ("B", slice(4096, 8192)))}
        boots = []
        for _ in range(200):
            st = rng.integers(0, 8192-64, size=128)
            idx = np.concatenate([np.arange(s, s+64) for s in st])
            boots.append(did_ac({k: v[idx] for k, v in S.items()}))
        boot = dict(block=64, n=200, mean=r3(np.mean(boots)), sd=r3(np.std(boots)),
                    ci95=[r3(np.percentile(boots, 2.5)), r3(np.percentile(boots, 97.5))])

        # 굴절 스위치가 만든 차이(같은 시드·같은 자세 복소 차)
        def chan(a, b):
            x, y = S[a]-S[a].mean(), S[b]-S[b].mean()
            r = y - x
            return dict(ac_power_db=r3(10*np.log10(np.mean(np.abs(r)**2))),
                        rel_to_off_db=r3(10*np.log10(np.mean(np.abs(r)**2)/np.mean(np.abs(x)**2))),
                        abs_rho=round(float(abs(np.vdot(x, y))/(np.linalg.norm(x)*np.linalg.norm(y))), 6),
                        contain_coeff=round(float(abs(np.vdot(x, y)/np.vdot(x, x))), 6))
        c1, c2 = chan("off_100", "ref_100"), chan("off_thin", "ref_thin")

        # 자세별 진폭비
        xo, xr = S["off_thin"]-S["off_thin"].mean(), S["ref_thin"]-S["ref_thin"].mean()
        g = np.abs(xr)/np.maximum(np.abs(xo), 1e-300)
        xo0, xr0 = S["off_100"]-S["off_100"].mean(), S["ref_100"]-S["ref_100"].mean()
        g0 = np.abs(xr0)/np.maximum(np.abs(xo0), 1e-300)

        readable = M["ref_thin"]["n_eff_poses"] >= 100
        pairs.append(dict(
            tag=tag, el_deg=el, f_tip_hz=ft,
            arms=dict(off_100=OFF100, off_thin=offT, ref_100=REF100, ref_thin=refT),
            npaths_median={k: ROW[(a, el)]["npaths_median"] for k, a in
                           (("off_100", OFF100), ("off_thin", offT),
                            ("ref_100", REF100), ("ref_thin", refT))},
            metrics=M,
            d_thickness_off_arm=d_off, d_thickness_ref_arm=d_ref, did=did,
            trim=trim, innocent_replace40_ac=innocent,
            split_half_ac=halves, block_bootstrap_ac=boot,
            refraction_switch_effect=dict(at_100mm=c1, at_thin=c2,
                                          d_ac_db=r3(c2["ac_power_db"]-c1["ac_power_db"])),
            pose_ratio_ref_over_off_db=dict(
                at_100mm=dict(median=r3(20*np.log10(np.median(g0))),
                              p10=r3(20*np.log10(np.percentile(g0, 10))),
                              p90=r3(20*np.log10(np.percentile(g0, 90))),
                              frac_ref_brighter_pct=round(100*float((g0 > 1).mean()), 2)),
                at_thin=dict(median=r3(20*np.log10(np.median(g))),
                             p10=r3(20*np.log10(np.percentile(g, 10))),
                             p90=r3(20*np.log10(np.percentile(g, 90))),
                             frac_ref_brighter_pct=round(100*float((g > 1).mean()), 2))),
            bands=dict(grid_ac_db=BAND_AC.get(el), grid_comb_db=BAND_COMB.get(el),
                       grid_rhythm_pp=BAND_RHY.get(el),
                       grid_floor_db_max_abs=BAND_FLOOR["max_abs"],
                       pathsolver_rerun_ac_db_diffraction_off=
                       NB["pathsolver_repeatability"]["diffraction_off"]["band_ac_db"],
                       seed_sd_db=NB["seed_dispersion"]["sd_level_db"]),
            readable=bool(readable),
            readable_note_ko=(
                "읽을 수 있다 — 유효 자세 수 %.0f 개(8192 중), 튀는 자세 하나가 끄는 칸이 아니다"
                % M["ref_thin"]["n_eff_poses"] if readable else
                "⛔읽을 수 없다 — 굴절 얇은 칸의 요동이 사실상 자세 %.0f 개에 몰려 있다"
                "(상위 8 자세가 %.2f %%). 갈아끼우는 자세 수를 1·8·32 로 바꾸면 DiD 가 "
                "−7.9 · −62.8 · −11.9 dB 로 요동친다 — 물리로 읽지 않는다."
                % (M["ref_thin"]["n_eff_poses"], M["ref_thin"]["top8_energy_pct"])),
        ))

# ── 구조 증거 ───────────────────────────────────────────────────────────────
thickness_arms = sorted({a for (a, el), r in ROW.items()
                         if (r["shell_mm"] not in (None, 100.0)
                             or r["prop_mm"] not in (None, 100.0))})
thickness_depths = sorted({ROW[(a, el)]["max_depth"] for (a, el), r in ROW.items()
                           if (r["shell_mm"] not in (None, 100.0)
                               or r["prop_mm"] not in (None, 100.0))})
refr_arms = {}
for (a, el), r in ROW.items():
    if "onlyrefr" in a or "swR1D0E0F1" in a:
        refr_arms.setdefault(a, dict(max_depth=r["max_depth"], shell_mm=r["shell_mm"],
                                     prop_mm=r["prop_mm"], els=[]))
        refr_arms[a]["els"].append(el)
for v in refr_arms.values():
    v["els"] = sorted(v["els"])

switch_100 = {}
for af, (o, r_) in {"matrice4e": (OFF100, REF100),
                    "mini5pro": ("sionna_p4000000000_mini5pro_r15_n8192_d1",
                                 "sionna_p4000000000_onlyrefr_mini5pro_r15_n8192"),
                    "s1000plus": ("sionna_p4000000000_s1000plus_r15_n8192_d1",
                                  "sionna_p4000000000_onlyrefr_s1000plus_r15_n8192")}.items():
    for el in (0.0, -15.0, -30.0, -45.0, -60.0, -75.0, -90.0):
        if (o, el) not in ROW or (r_, el) not in ROW:
            continue
        ft = ROW[(o, el)]["f_tip_hz"]
        switch_100[f"{af}/el{el:+.0f}"] = dict(
            d_ac_db=r3(met(ser(r_, el), ft)["ac_power_db"] - met(ser(o, el), ft)["ac_power_db"]),
            npaths_off=ROW[(o, el)]["npaths_median"], npaths_ref=ROW[(r_, el)]["npaths_median"])

depth_cross = {}
for el in (-30.0,):
    ft = ROW[(OFF100, el)]["f_tip_hz"]
    q = {"off_d1": OFF100, "off_d3": "sionna_p4000000000_onlydepth3_r15_n8192",
         "ref_d1": REF100, "ref_d3": "sionna_p4000000000_swR1D0E0F1_r15_n8192_d3"}
    m = {k: met(ser(a, el), ft) for k, a in q.items()}
    depth_cross[f"el{el:+.0f}"] = dict(
        arms=q, ac_power_db={k: v["ac_power_db"] for k, v in m.items()},
        npaths={k: ROW[(a, el)]["npaths_median"] for k, a in q.items()},
        depth_gain_off_db=r3(m["off_d3"]["ac_power_db"]-m["off_d1"]["ac_power_db"]),
        depth_gain_ref_db=r3(m["ref_d3"]["ac_power_db"]-m["ref_d1"]["ac_power_db"]),
        interaction_did_db=r3((m["ref_d3"]["ac_power_db"]-m["ref_d1"]["ac_power_db"])
                              - (m["off_d3"]["ac_power_db"]-m["off_d1"]["ac_power_db"])))

off_ladder = {}
for a, lab in [(OFF100, "prop100_shell100"),
               ("sionna_p4000000000_r15_n8192_shell0.5mm_d1", "shell0.5_only"),
               ("sionna_p4000000000_r15_n8192_shell0.75mm_d1", "shell0.75_only"),
               ("sionna_p4000000000_r15_n8192_shell1.5mm_d1", "shell1.5_only"),
               ("sionna_p4000000000_r15_n8192_shell0.75mm_prop0.5mm_d1", "prop0.5"),
               ("sionna_p4000000000_r15_n8192_shell0.75mm_prop0.9mm_d1", "prop0.9"),
               ("sionna_p4000000000_r15_n8192_shell0.75mm_prop1.43mm_d1", "prop1.43"),
               ("sionna_p4000000000_r15_n8192_shell0.75mm_prop2mm_d1", "prop2.0")]:
    if (a, -30.0) in ROW:
        off_ladder[lab] = dict(ac_power_db=met(ser(a, -30.0), 1102.4)["ac_power_db"],
                               npaths=ROW[(a, -30.0)]["npaths_median"])

OUT = dict(
    _meta=dict(
        generator="scratchpad/write_h5.py (H5 투과 반대항 판정자 갈래)",
        written_at_kst=dt.datetime.now(KST).strftime("%Y-%m-%d %H:%M KST"),
        question_ko="굴절만 켠 팔에서 두께를 바꾸면 다 끔 팔과 **다르게** 움직이는가. "
                    "예측(H5): 껍데기가 얇아지면 속 금속(배터리·PCB)이 밝아져 굴절 팔은 "
                    "**덜 어두워진다**.",
        gpu_used="0 — 저장된 원장만 읽는다(sionna.rt·mitsuba 임포트 없음)",
        sources={p: dt.datetime.fromtimestamp(os.path.getmtime(f"{ROOT}/{p}"), KST)
                 .strftime("%Y-%m-%d %H:%M KST") for p in
                 ("outputs/elevation_sweep_md.json", "outputs/elevation_sweep_md.npz",
                  "outputs/material_verdict_0816.json", "outputs/depth_axis_verdict_0816.json")},
        n_ledger_rows=len(A.J["rows"]),
        metric_defs_ko="잣대는 재정의하지 않았다 — 빗살 대비·리듬 몫은 "
                       "benchmark/build_md_atlas.py 의 comb_contrast_db·rhythm_share 를 그대로 "
                       "임포트했고, 확산 바닥은 material_verdict_0816 규약(ac_power_db + "
                       "10log10(f_tip 밖 몫))을 그대로 썼다.",
        conventions_ko=[
            "레벨(dB)은 전부 정지 성분(DC) 제거 후",
            "⭐격자 흔들림 밴드는 앙각마다 다르다 — 0° 3.86 · −30° 0.37 dB",
            "빗살 대비 절대값에는 격자 꼬리표가 필요하다(짝 안의 차이는 자유)",
            "AC/DC < 1e-11 은 near_numeric_floor 로 적고 물리로 안 읽는다",
            "밴드 안이면 «판정 불가» — «안 바뀐다» 로 단정하지 않는다",
            "⭐튀는 자세(이상값) 검사 필수 — 솎기 전/후를 둘 다 싣고 헤드라인은 솎은 값",
        ],
        trim_method_note_ko="⭐솎기는 **두 방법**을 다 실었다. 자세를 **삭제**하면 표본 간격이 "
                            "깨져 FFT 잣대(빗살 대비·리듬 몫)가 그것만으로 흔들린다 — 실제로 "
                            "빗살 DiD 가 −10.9 → −16.0 dB 로 움직였다. 자세를 **이웃 평균으로 "
                            "갈아 끼우면**(0816 절차의 적대검산 ①) −10.9 로 제자리다. 그래서 "
                            "헤드라인은 «갈아끼움» 값을 쓰고 «삭제» 값은 함께 싣되 잣대 흔들림으로 "
                            "읽는다. 요동(AC)은 두 방법이 일치한다(−2.40 ↔ −2.38).",
    ),
    inventory=dict(
        landed_cells_ko="굴절만 × 두께 칸은 **세 칸**뿐이다 — el −30 에 0.9 mm·1.43 mm, el 0 에 0.9 mm. "
                        "짝이 되는 다 끔 칸은 넷 다 있다.",
        refraction_arms_in_ledger=refr_arms,
        thickness_arms_in_ledger=thickness_arms,
        thickness_arm_depths=thickness_depths,
        missing_ko=[
            "⛔굴절만 × 두께 × **깊이 ≥ 2** — 원장 전체에 없다(두께 팔 11 개가 전부 깊이 1)",
            "⛔굴절만 × **셸만** 두께(프롭 100 mm 유지) — 없다. 굴절 팔의 두께 칸은 셸·프롭을 "
            "**함께** 얇게 했다. 다 끔 팔에는 셸만 칸이 셋 있다(0.5·0.75·1.5).",
            "⛔굴절만 × 두께 × el −15 · −45 · −60 · −75 · −90 — 없다(각도 확장이 이 갈래엔 안 왔다)",
            "⛔굴절만 × 두께 × 다른 기체(mini5pro·s1000plus) — 없다",
            "⛔시드 복제(같은 칸 다른 시드) — 없다",
        ],
    ),
    cells=cells,
    pairs=pairs,
    structural_evidence=dict(
        why_ko="⭐예측이 부르는 물리는 «셸을 뚫고 들어가 → 속 금속에 맞고 → 다시 뚫고 나온다» 다. "
               "그건 상호작용이 **최소 두 번**이다. 그런데 원장의 두께 팔은 하나도 빠짐없이 "
               "깊이 1 이다 — 한 번 뚫고 들어가면 되돌아 나올 두 번째 튕김이 아예 없다.",
        every_thickness_arm_is_depth1=dict(arms=thickness_arms, depths=thickness_depths),
        refraction_switch_only_removes_return=dict(
            what_ko="두께를 안 건드리고(100 mm) 굴절 스위치만 켜 보면 — 요동이 **어두워지고** "
                    "경로 수가 준다. 굴절이 속 반사를 **더해** 준다면 최소 한 칸은 밝아져야 한다.",
            table=switch_100,
            n_cells=len(switch_100),
            n_darker=sum(1 for v in switch_100.values() if v["d_ac_db"] < 0),
            n_paths_down=sum(1 for v in switch_100.values()
                             if v["npaths_ref"] < v["npaths_off"]),
            reads_ko="13 칸 중 12 칸에서 어두워지고(−1.51 ~ −9.98 dB), 경로 수는 13/13 에서 준다. "
                     "s1000plus el 0 만 +0.16 dB 인데 그 기체는 열린 프레임이라 뚫을 셸이 없다. "
                     "⇒ 깊이 1 에서 굴절 스위치는 **에너지를 내보내는 구멍**이지 속을 비추는 "
                     "조명이 아니다.",
        ),
        depth_cross_at_100mm=dict(
            what_ko="깊이를 3 으로 올리면 속 반사가 살아나는가 — 100 mm 에서 2×2 로 쟀다",
            table=depth_cross,
            reads_ko="굴절 팔의 깊이 이득은 +0.069 dB(경로 382 → 399), 다 끔 팔은 −0.075 dB. "
                     "상호작용 +0.144 dB — 아무 일도 안 일어난다. 다만 이건 100 mm 라 셸이 "
                     "애초에 안 뚫린다. ⇒ 예측이 필요한 칸은 «얇은 셸 **그리고** 깊이 ≥ 2» 인데, "
                     "원장에는 «얇은 셸 × 깊이 1» 과 «100 mm × 깊이 3» 만 있고 둘의 교집합이 없다.",
        ),
        off_arm_thickness_ladder_el30=dict(
            what_ko="다 끔 팔 el −30 사다리 — 셸만 손잡이는 요동에 **배선이 없고**(0.00 dB) "
                    "프롭 손잡이가 전부다. 그래서 굴절 팔의 두께 칸이 셸·프롭을 함께 얇게 한 것은 "
                    "사실상 **프롭** 실험이다.",
            table=off_ladder,
            shell_only_delta_db=r3(off_ladder["shell0.75_only"]["ac_power_db"]
                                   - off_ladder["prop100_shell100"]["ac_power_db"]),
            prop_monotone=True,
        ),
    ),
    prereg_scoring=dict(
        H5_투과_반대항=dict(
            prereg_ko="굴절 켠 팔은 셸 안쪽 금속이 밝아져(왕복 +6.2 dB) 덜 내려가야",
            landed=True,
            landed_where_ko="el −30 에 두 두께 점(0.9 · 1.43 mm), el 0 에 한 점(0.9 mm)",
            question1_다르게_움직이나=dict(
                verdict="예 — 유의",
                el_minus30_did_ac_db={"shell0.75_prop0.9": -2.398, "shell0.75_prop1.43": -1.224},
                thresholds_ko="스스로 잰 문턱: 블록 부트스트랩 95 % 구간 [−2.84, −1.83] · "
                              "[−1.61, −0.73] — 둘 다 0 을 안 물린다. 빌려 온 격자 밴드 0.37 dB "
                              "기준으로도 6.5 배 · 3.3 배 밖. 같은 물리 재실행 문턱은 회절 끈 팔이라 "
                              "≈1e-15 dB(두 팔 다 회절 꺼짐).",
                robust_ko="솎기(1·8 자세, 삭제·갈아끼움 넷 다) 뒤에도 −2.36 ~ −2.40 · −1.19 ~ −1.22 로 "
                          "안 움직인다. 죄 없는 자세 갈아끼우기 40 회의 산포는 sd 0.0007 dB — "
                          "솎기 자체는 무해하다.",
                caveat_split_half_ko="⚠**반쪽 나누기는 두 점이 다르다.** 0.9 mm 는 앞·뒤 반쪽이 "
                          "−3.00 · −1.64 dB 로 둘 다 살아 있지만, 정본 1.43 mm 는 −2.32 · **+0.00** dB 로 "
                          "뒤 반쪽이 0 이다. 부트스트랩 구간은 여전히 0 을 안 물리지만, 1.43 mm 점은 "
                          "0.9 mm 점보다 **약하다** 고 적는다 — 자세 절반으로는 안 서는 크기다.",
            ),
            question2_방향=dict(
                verdict="⛔예측 반증 — 방향이 반대다",
                measured_ko="굴절 팔이 **덜** 내려가기는커녕 **더** 내려간다. "
                            "0.9 mm: 다 끔 −16.99 dB vs 굴절만 −19.38 dB(굴절 팔이 2.40 dB 더 어둡다). "
                            "1.43 mm: 다 끔 −13.02 dB vs 굴절만 −14.24 dB(1.22 dB 더 어둡다). "
                            "두께 두 점이 단조다 — 얇을수록 더 벌어진다.",
                predicted_db="+6.2 (왕복 투과 이득)",
                observed_db=-2.398,
                miss_db=-8.6,
                channel_ko="굴절 스위치가 만든 차이(같은 시드 복소 차)는 100 mm 에서 다 끔 팔 대비 "
                           "−3.87 dB 인데, 얇아지면 절대 요동이 −12.94 dB(0.9) · −9.47 dB(1.43) "
                           "**더 떨어진다**. 남는 몫(담김계수)은 0.440 → 0.062 로, 굴절 팔이 다 끔 팔 "
                           "에코의 44 % 만 남기다가 6 % 만 남긴다.",
            ),
            question3_예측한_물리를_쟀나=dict(
                verdict="⛔아니다 — 그 물리는 이 칸들에 배선이 없다",
                reasons_ko=[
                    "①두께 팔 11 개가 전부 **깊이 1** 이다. 뚫고 들어간 광선이 속 금속에 맞고 "
                    "되돌아 나오려면 상호작용이 두 번이어야 한다.",
                    "②100 mm 에서 굴절만 켜면 13 칸 중 12 칸이 어두워지고 경로 수가 13/13 에서 준다 — "
                    "깊이 1 의 굴절은 **에너지를 흘려보내는 구멍**이다. 얇아지면 더 흘려보내니 "
                    "더 어두워지는 것은 배선이 강제하는 결과지 표적 물리가 아니다.",
                    "③굴절 팔의 두께 칸은 셸과 프롭을 **함께** 얇게 했는데, el −30 요동은 프롭이 "
                    "사실상 전부다(다 끔 팔 셸만 손잡이 0.00 dB). 예측은 **셸** 이야기였다 — "
                    "셸만 바꾼 굴절 칸은 원장에 없다.",
                ],
                honest_ko="그래서 정직한 문장은 둘이다. ⓐ **문면대로 채점하면 H5 는 반증됐다** — "
                          "있는 칸 셋 어디에도 «덜 어두워진다» 는 없고, 반대 방향이 밴드 밖에서 "
                          "단조로 선다. ⓑ **예측이 부른 기제는 아직 못 쟀다** — 그 기제를 재려면 "
                          "«얇은 셸 × 깊이 ≥ 2 × 셸만» 칸이 필요한데 원장에 없다. "
                          "ⓐ 를 «투과 반대항은 존재하지 않는다» 로 넓혀 쓰면 안 된다.",
            ),
            secondary_metrics=dict(
                floor_did_db={"shell0.75_prop0.9": 1.441, "shell0.75_prop1.43": 1.840},
                floor_verdict_ko="확산 바닥 DiD 는 +1.44 · +1.84 dB 로 **밴드 안**(격자 바닥 밴드 "
                                 "9.30 dB) — 판정 불가. 부호는 굴절 팔 바닥이 덜 내려가는 쪽이라 "
                                 "예측과 같은 방향이지만 밴드 안이라 인용하지 않는다.",
                comb_did_db={"shell0.75_prop0.9": -11.004, "shell0.75_prop1.43": -8.634},
                comb_verdict_ko="빗살 대비 DiD 는 갈아끼움 기준 −11.00 · −8.63 dB 로 격자 밴드 "
                                "4.6 dB **밖**(2.4 배 · 1.9 배). 굴절 팔의 무늬가 두께 정정에 "
                                "더 크게 무너진다. ⚠삭제 방식으로 솎으면 −14.7 ~ −16.0 dB 로 "
                                "부풀어 — 잣대 흔들림이니 갈아끼움 값을 쓴다.",
                rhythm_did_pp={"shell0.75_prop0.9": -17.133, "shell0.75_prop1.43": -17.189},
                rhythm_verdict_ko="리듬 몫 DiD −17.13 · −17.19 %p 는 밴드 21.8 %p **안** — 판정 불가.",
            ),
            el0_control=dict(
                verdict="⛔읽을 수 없다",
                why_ko="굴절 × 얇은 칸의 요동이 사실상 자세 6 개에 몰려 있다(상위 8 자세가 99.93 %). "
                       "갈아끼우는 자세를 0·1·8·32 개로 바꾸면 DiD 가 −7.26 · −7.91 · −62.77 · "
                       "−11.88 dB 로 요동친다. 반면 다 끔 팔은 el 0 에서 두께에 0.000 dB — "
                       "material_verdict H3 의 «금속 추첨» 판정 그대로다.",
                n_eff_poses=6.0, top8_energy_pct=99.927,
            ),
        ),
    ),
    impacts_ko=dict(
        material_verdict_굴절만_거리_생존="⚠**방향 진술 철회 필요**. material_verdict_0816 의 "
            "headline_impacts 는 «정정(셸 0.75 mm)은 왕복 투과를 −6.35 → −0.13 dB 로 밝게 하므로 "
            "굴절 채널 레벨은 **올라가는 쪽**» 이라고 슬래브 수학으로 적었다. 실측은 반대다 — "
            "깊이 1 에서 굴절 팔은 정정 뒤 절대로도(−19.4 dB) 다 끔 대비로도(−2.4 dB) 더 어둡다. "
            "«올라가는 쪽» 은 지우고 «깊이 1 실측으로는 내려가는 쪽·깊이 ≥ 2 는 미측정» 으로 바꾼다. "
            "⚠거리 기울기(완만 감쇄) 자체는 재질 곱셈 이득과 무관하므로 안 흔들린다 — 흔들리는 것은 "
            "**방향 꼬리표**뿐이다.",
        굴절만_레벨_인용="굴절만 팔 레벨을 인용할 때 «100 mm 꼬리표» 는 유지하되, 이제 "
            "«정정하면 더 어두워진다(깊이 1 실측 −19.4 dB · el −30 · 셸 0.75+프롭 0.9)» 를 함께 적는다.",
        회절_덮음="무관 — 이 갈래는 회절을 안 건드린다.",
        표적축_서사="유지 — 굴절 팔에서도 리듬 몫 DiD 는 밴드 안이다. 다만 빗살 대비는 굴절 팔에서 "
            "밴드 밖으로 더 무너지므로(−11.0 dB) «무늬는 재질 정정에 강건» 을 **다 끔 팔 기준** 으로 "
            "한정해 적는다.",
    ),
    open_questions_ko=[
        "⭐«얇은 셸 × 깊이 ≥ 2 × 굴절» 칸 — 투과 반대항을 재려면 이 칸이 있어야 한다. 지금은 없다.",
        "⭐굴절 팔의 **셸만** 두께 칸(프롭 100 mm 고정) — 지금 결과는 셸이 아니라 프롭 실험이다.",
        "굴절 × 두께의 앙각 확장(−15 · −45 · −60 · −75 · −90) — el −30 한 각도로만 섰다.",
        "시드 복제 — DiD 는 네 칸 모두 시드 1 의 짝비교라 시드 편향이 상당 부분 소거될 텐데, "
        "얼마나 소거되는지는 **안 재봤다**(원장에 시드 복제가 없다).",
        "el 0 을 읽으려면 자세 수를 늘리거나 다른 잣대가 필요하다 — 지금은 자세 6 개짜리 추첨이다.",
        "⭐정본 1.43 mm 점은 반쪽 나누기의 뒤 반쪽에서 +0.00 dB 다 — 자세를 늘리거나 앙각을 "
        "늘려 다시 세워야 «정본에서도 선다» 를 단정할 수 있다.",
    ],
    do_not_write_ko=[
        "⛔«투과 반대항은 없다» — 반증된 것은 **예측의 방향**이고, 기제는 배선이 없어 못 쟀다.",
        "⛔«재질을 정정하면 굴절 채널이 밝아진다» — 있는 칸 셋 전부 반대다.",
        "⛔«셸을 얇게 하면 굴절 팔이 어두워진다» — 셸만 바꾼 굴절 칸이 없다. 쟀는지 모르는 것은 "
        "셸·프롭을 **함께** 얇게 한 판이다.",
        "⛔el 0 의 −7.26 dB 를 인용 — 자세 6 개짜리 추첨이라 읽을 수 없다.",
        "⛔확산 바닥 +1.44 dB 와 리듬 −17.1 %p 를 «유의» 로 인용 — 둘 다 밴드 안이다.",
    ],
    verdict_headline_ko=(
        "① **다르게 움직인다 — 유의.** el −30 에서 두께를 100 mm → 0.75/0.9 mm 로 바꾸면 "
        "요동이 다 끔 팔 −16.99 dB · 굴절만 팔 −19.38 dB 로 갈린다(차이 −2.40 dB). "
        "정본 프롭 1.43 mm 점에서도 −13.02 vs −14.24(차이 −1.22 dB) 로 같은 부호이고 "
        "얇을수록 벌어진다. 블록 부트스트랩 95 % 구간 [−2.84, −1.83]·[−1.61, −0.73] 로 0 을 "
        "안 물리고, 튀는 자세를 1·8 개 솎아도(삭제·갈아끼움 넷 다) −2.36 ~ −2.40 으로 안 움직인다. "
        "② **그런데 방향이 예측과 반대다 — H5 는 문면대로 반증.** 예측은 «굴절 팔이 덜 어두워진다» "
        "(+6.2 dB 쪽)였는데 실측은 «더 어두워진다»(−2.40 dB). 8.6 dB 를 반대쪽으로 빗나갔다. "
        "③ **다만 예측이 부른 물리는 애초에 못 재는 판이었다.** 뚫고 들어가 속 금속에 맞고 나오려면 "
        "상호작용이 두 번인데, 원장의 두께 팔 11 개가 **전부 깊이 1** 이다. 실제로 100 mm 에서 "
        "굴절 스위치만 켜면 13 칸 중 12 칸이 어두워지고 경로 수가 13/13 에서 준다 — 깊이 1 의 굴절은 "
        "속을 비추는 조명이 아니라 **에너지가 새는 구멍**이다. 그래서 얇아질수록 더 새고 더 어둡다. "
        "④ 세기의 단서: 0.9 mm 점은 앞·뒤 반쪽에서 다 서지만(−3.00 · −1.64 dB), 정본 1.43 mm 점은 "
        "뒤 반쪽이 +0.00 dB 라 **약하다**. ⑤ 게다가 굴절 팔의 두께 칸은 셸과 프롭을 **함께** 얇게 했고, el −30 요동은 프롭이 사실상 "
        "전부다(다 끔 팔 셸만 손잡이 0.00 dB). 예측은 셸 이야기였으므로 **셸 버전의 H5 는 여전히 "
        "미측정**이다. ⑥ 곁가지: 확산 바닥 DiD +1.44 dB·리듬 −17.1 %p 는 밴드 안(판정 불가), "
        "빗살 대비 DiD −11.00 dB 는 밴드(4.6) 밖 — 굴절 팔의 무늬가 두께 정정에 더 크게 무너진다. "
        "el 0 칸은 자세 6 개짜리 추첨이라 **읽을 수 없다**. "
        "⑦ 파급: material_verdict 의 «정정하면 굴절 채널이 올라가는 쪽» 이라는 슬래브 추론은 "
        "깊이 1 실측에 반증됐으므로 방향 진술을 철회한다."),
)

p = f"{ROOT}/outputs/material_canon_0816_h5_refraction.json"
json.dump(OUT, open(p, "w"), ensure_ascii=False, indent=1)
print("✅", p, os.path.getsize(p), "bytes")
print(OUT["verdict_headline_ko"][:400])
