# -*- coding: utf-8 -*-
"""az_falsify_comb.py — az0/az45 el0 의 «움직이는 부분» 을 빗살(프로펠러 선)과
바닥(잡음)으로 갈라 잰다. GPU 안 씀. 저장 원장·샤드만 읽는다."""
import glob, json, os
import numpy as np

ROOT = "/workspace/sionna"
Z = np.load(f"{ROOT}/outputs/elevation_sweep_md.npz", allow_pickle=True)
LED = json.load(open(f"{ROOT}/outputs/elevation_sweep_md.json"))
PRF = float(LED["_meta"]["prf_hz"]); FFL = float(LED["_meta"]["f_flash_hz"])
N = 8192; FR = np.fft.fftfreq(N, 1 / PRF); W = np.hanning(N)
CG = (W ** 2).sum()          # 창 이득 — 전력 정규화


def P_of(k):
    x = np.asarray(Z[k]).astype(complex)
    x = (x - x.mean()) * W
    return np.abs(np.fft.fft(x)) ** 2 / CG   # 합 = AC 전력


def split_comb(P, tol_hz=4.0, nharm=60):
    """빗살(=f_flash 정수배 ±tol) 안의 **초과분** 과 바닥을 가른다.
    바닥 = 빗살 밖 빈들의 중앙값 × 전체 빈 수 (백색 가정)."""
    fa = np.abs(FR)
    kh = np.round(fa / FFL)
    on = (kh >= 1) & (kh <= nharm) & (np.abs(fa - kh * FFL) <= tol_hz)
    off = ~on
    floor_per_bin = np.median(P[off])
    comb_tot = P[on].sum()
    comb_excess = max(comb_tot - floor_per_bin * on.sum(), 0.0)
    return dict(ac_total=float(P.sum()),
                comb_bins=int(on.sum()),
                comb_total=float(comb_tot),
                comb_excess=float(comb_excess),
                floor_per_bin=float(floor_per_bin),
                floor_total=float(floor_per_bin * P.size),
                comb_excess_frac_pct=round(100 * comb_excess / max(P.sum(), 1e-300), 3))


def db(v):
    return -999.0 if v <= 0 else round(10 * np.log10(v), 2)


ARMS = {
 "ps_nophys_az0":  "sionna_p4000000000_r15_n8192_d1",
 "ps_nophys_az45": "sionna_p4000000000_r15_n8192_az45_d1",
 "ps_phys_az0":    "sionna_p4000000000_phys_r15_n8192_d1",
 "ps_phys_az45":   "sionna_p4000000000_phys_r15_n8192_az45_d1",
 "ours_az0":       "ours_r15_n8192",
 "ours_az45":      "ours_r15_n8192_az45",
 "ours_free_az0":  "ours_free_r15_n8192",
 "ps_partsprop_az0": "sionna_p4000000000_partsprop_r15_n8192_d1",
 "ps_partsnoprop_az0": "sionna_p4000000000_partsnoprop_r15_n8192_d1",
 "ps_phys_partsprop_az0": "sionna_p4000000000_phys_partsprop_r15_n8192_d1",
}
out = {"_meta": {"generator": "benchmark/az_falsify_comb.py",
                 "gpu_ko": "⛔GPU 안 씀. sionna.rt·mitsuba 임포트 없음.",
                 "recipe_ko": "AC 스펙트럼(hann, 전력보존)을 «빗살 초과분» 과 «백색 바닥» 으로 가른다. "
                              "빗살 = f_flash(126.67 Hz) 1~60 배 ±4 Hz. 바닥 = 빗살 밖 중앙값×빈수.",
                 "f_flash_hz": FFL, "prf_hz": PRF}}
res = {}
for nm, arm in ARMS.items():
    for el in ("el+0", "el-30", "el-60", "el-90"):
        k = f"{arm}/{el}"
        if k not in Z:
            continue
        x = np.asarray(Z[k]).astype(complex)
        s = split_comb(P_of(k))
        res[f"{nm}|{el}"] = dict(
            dc_db=db(abs(x.mean()) ** 2),
            ac_db=db(s["ac_total"]),
            comb_excess_db=db(s["comb_excess"]),
            floor_total_db=db(s["floor_total"]),
            comb_over_floor_db=round(db(s["comb_excess"]) - db(s["floor_total"]), 2),
            comb_excess_frac_pct=s["comb_excess_frac_pct"])
out["comb_split"] = res

# ── 빗살·바닥의 az0→az45 변화 ────────────────────────────────────────────
deltas = {}
for pair, (a, b) in {"ps_nophys": ("ps_nophys_az0", "ps_nophys_az45"),
                     "ps_phys": ("ps_phys_az0", "ps_phys_az45"),
                     "ours": ("ours_az0", "ours_az45")}.items():
    for el in ("el+0", "el-30", "el-60", "el-90"):
        ka, kb = f"{a}|{el}", f"{b}|{el}"
        if ka in res and kb in res:
            deltas[f"{pair}|{el}"] = dict(
                d_dc_db=round(res[kb]["dc_db"] - res[ka]["dc_db"], 2),
                d_ac_db=round(res[kb]["ac_db"] - res[ka]["ac_db"], 2),
                d_comb_db=round(res[kb]["comb_excess_db"] - res[ka]["comb_excess_db"], 2),
                d_floor_db=round(res[kb]["floor_total_db"] - res[ka]["floor_total_db"], 2))
out["deltas"] = deltas

# ── 샤드의 경로 수 · 광선잡음 진단 (el0) ─────────────────────────────────
def shard_npaths(prefix, el="el+0"):
    fs = sorted(glob.glob(f"{ROOT}/outputs/elev_sweep_shards/{prefix}_{el}_*.npz"))
    if not fs:
        return None
    idx, npz_, Ez = [], [], []
    for f in fs:
        d = np.load(f)
        if "npaths" not in d:
            return None
        idx.append(d["idx"]); npz_.append(d["npaths"]); Ez.append(d["E"])
    idx = np.concatenate(idx); npp = np.concatenate(npz_); E = np.concatenate(Ez)
    o = np.argsort(idx)
    return idx[o], npp[o], E[o]


diag = {}
for nm, pre in {"ps_nophys_az0": "sionna_p4000000000_r15_n8192_d1",
                "ps_nophys_az45": "sionna_p4000000000_r15_n8192_az45_d1",
                "ps_phys_az0": "sionna_p4000000000_phys_r15_n8192_d1",
                "ps_phys_az45": "sionna_p4000000000_phys_r15_n8192_az45_d1"}.items():
    r = shard_npaths(pre)
    if r is None:
        diag[nm] = "샤드 없음/경로수 없음"; continue
    idx, npp, E = r
    a = np.abs(E)
    ac = E - E.mean()
    # 경로 수와 |E| 의 상관, 그리고 |E| 의 상대 산포
    cc = float(np.corrcoef(npp.astype(float), a)[0, 1])
    diag[nm] = dict(n=int(idx.size),
                    npaths_min=int(npp.min()), npaths_med=int(np.median(npp)),
                    npaths_max=int(npp.max()), npaths_std=round(float(npp.std()), 1),
                    corr_npaths_absE=round(cc, 3),
                    absE_mean=float(a.mean()), absE_std=float(a.std()),
                    rel_std_pct=round(100 * float(a.std() / a.mean()), 3),
                    ac_over_dc_db=db(np.mean(np.abs(ac) ** 2) / abs(E.mean()) ** 2))
out["shard_diag_el0"] = diag

json.dump(out, open(f"{ROOT}/outputs/az_falsify_comb.json", "w"), ensure_ascii=False, indent=1)
for k, v in res.items():
    print(f"{k:34s} {v}")
print("---- deltas ----")
for k, v in deltas.items():
    print(f"{k:22s} {v}")
print("---- shard diag el0 ----")
for k, v in diag.items():
    print(f"{k:18s} {v}")
