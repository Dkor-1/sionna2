# -*- coding: utf-8 -*-
"""az_falsify_rhythm.py — az45 정면 에코 소실의 «움직이는 부분» 을 반증 검사.
GPU 안 씀(sionna.rt·mitsuba 임포트 없음). 저장된 원장·npz 만 읽는다."""
import json, os
import numpy as np

ROOT = "/workspace/sionna"
Z = np.load(f"{ROOT}/outputs/elevation_sweep_md.npz", allow_pickle=True)
LED = json.load(open(f"{ROOT}/outputs/elevation_sweep_md.json"))
M = LED["_meta"]
PRF = float(M["prf_hz"]); FFL = float(M["f_flash_hz"])
N = 8192
FR = np.fft.fftfreq(N, 1.0 / PRF)
W = np.hanning(N)


def db(x):
    x = float(np.real(x))
    return -999.0 if x <= 0 else 10 * np.log10(x)


def levels(k):
    x = np.asarray(Z[k]).astype(complex)
    dc = x.mean()
    ac = x - dc
    return dict(total_db=round(db(np.mean(np.abs(x) ** 2)), 2),
                dc_db=round(db(abs(dc) ** 2), 2),
                ac_db=round(db(np.mean(np.abs(ac) ** 2)), 2),
                dc_abs=float(abs(dc)),
                ac_rms=float(np.sqrt(np.mean(np.abs(ac) ** 2))))


def spec(k):
    """DC 제거 후 스펙트럼. 리듬 몫 = f_flash 정수배 ±8 Hz 가 차지하는 몫."""
    x = np.asarray(Z[k]).astype(complex)
    x = (x - x.mean()) * W
    P = np.abs(np.fft.fft(x)) ** 2
    return P


def rhythm(P, f_tip, tol=8.0):
    """above = |f| >= f_tip. 리듬 몫 = above 안에서 f_flash 정수배 ±tol 몫."""
    tot = P.sum()
    above = np.abs(FR) >= f_tip
    Pa = P[above]; Fa = FR[above]
    harm = np.abs(np.abs(Fa) / FFL - np.round(np.abs(Fa) / FFL)) * FFL <= tol
    share_above = 100.0 * Pa[harm].sum() / max(Pa.sum(), 1e-300)
    # 전대역 리듬 몫도 같이 낸다(위 규약과 별개)
    harm_all = np.abs(np.abs(FR) / FFL - np.round(np.abs(FR) / FFL)) * FFL <= tol
    share_all = 100.0 * P[harm_all].sum() / max(tot, 1e-300)
    # 백색잡음 중립값 = 뽑히는 빈 개수 비율
    neutral_above = 100.0 * harm.sum() / max(harm.size, 1)
    neutral_all = 100.0 * harm_all.sum() / max(harm_all.size, 1)
    return dict(share_above_pct=round(share_above, 2), share_all_pct=round(share_all, 2),
                neutral_above_pct=round(neutral_above, 2), neutral_all_pct=round(neutral_all, 2),
                above_frac_pct=round(100.0 * Pa.sum() / max(tot, 1e-300), 2))


def line_strength(P, f0, tol=6.0):
    """f0 근처 선의 세기 / 주변 바닥(중앙값) — dB."""
    m = np.abs(np.abs(FR) - f0) <= tol
    side = (np.abs(np.abs(FR) - f0) > 3 * tol) & (np.abs(np.abs(FR) - f0) < 12 * tol)
    if not m.any() or not side.any():
        return None
    return round(10 * np.log10(P[m].max() / np.median(P[side])), 2)


def peak_hz(P, lo=20.0, hi=None):
    hi = hi if hi else PRF / 2
    m = (np.abs(FR) >= lo) & (np.abs(FR) <= hi)
    i = np.argmax(np.where(m, P, 0.0))
    return round(abs(FR[i]), 2)


ARMS = {
    "ours": ("ours_r15_n8192", "ours_r15_n8192_az45"),
    "ps_nophys": ("sionna_p4000000000_r15_n8192_d1", "sionna_p4000000000_r15_n8192_az45_d1"),
    "ps_phys": ("sionna_p4000000000_phys_r15_n8192_d1", "sionna_p4000000000_phys_r15_n8192_az45_d1"),
}
ELS = ["el+0", "el-30", "el-60", "el-90"]
FTIP = {r["el_deg"]: r["f_tip_hz"] for r in LED["rows"] if r["engine"] == "ours_r15_n8192"}

out = {"_meta": {
    "generator": "benchmark/az_falsify_rhythm.py",
    "gpu_ko": "⛔GPU 안 씀 — sionna.rt·mitsuba 임포트 없음. 저장 원장만 읽었다.",
    "prf_hz": PRF, "f_flash_hz": FFL, "n": N, "df_hz": round(PRF / N, 4),
    "recipe_ko": "AC = 시계열 평균 제거 후 전력. 스펙트럼은 hann 창. 리듬 몫은 f_flash 정수배 ±8 Hz.",
}}

cells = {}
for eng, (a0, a45) in ARMS.items():
    for el in ELS:
        k0, k45 = f"{a0}/{el}", f"{a45}/{el}"
        if k0 not in Z or k45 not in Z:
            continue
        eld = float(el.replace("el", ""))
        ft = FTIP.get(eld, 1272.9)
        L0, L45 = levels(k0), levels(k45)
        P0, P45 = spec(k0), spec(k45)
        cells[f"{eng}|{el}"] = dict(
            f_tip_hz=ft,
            az0=L0, az45=L45,
            d_ac_db=round(L45["ac_db"] - L0["ac_db"], 2),
            d_dc_db=round(L45["dc_db"] - L0["dc_db"], 2),
            ac_over_dc_az0_db=round(L0["ac_db"] - L0["dc_db"], 2),
            ac_over_dc_az45_db=round(L45["ac_db"] - L45["dc_db"], 2),
            rhythm_az0=rhythm(P0, ft), rhythm_az45=rhythm(P45, ft),
            flash_line_db_az0=line_strength(P0, FFL), flash_line_db_az45=line_strength(P45, FFL),
            flash2_line_db_az0=line_strength(P0, 2 * FFL), flash2_line_db_az45=line_strength(P45, 2 * FFL),
            peak_hz_az0=peak_hz(P0), peak_hz_az45=peak_hz(P45),
            bitidentical=bool(np.array_equal(np.asarray(Z[k0]), np.asarray(Z[k45]))),
        )
out["cells"] = cells

# ── 분해 팔 (프로펠러만 / 프로펠러 뺀 나머지) — az0 el0 ────────────────────
DEC = {}
for k in ("sionna_p4000000000_partsprop_r15_n8192_d1/el+0",
          "sionna_p4000000000_partsnoprop_r15_n8192_d1/el+0",
          "sionna_p4000000000_phys_partsprop_r15_n8192_d1/el+0",
          "sionna_p4000000000_r15_n8192_d1/el+0",
          "sionna_p4000000000_r15_n8192_az45_d1/el+0",
          "sionna_p4000000000_phys_r15_n8192_d1/el+0",
          "sionna_p4000000000_phys_r15_n8192_az45_d1/el+0",
          "ours_r15_n8192/el+0", "ours_free_r15_n8192/el+0",
          "ours_r15_n8192_az45/el+0"):
    if k in Z:
        P = spec(k)
        DEC[k] = dict(levels(k), rhythm=rhythm(P, 1272.9),
                      flash_line_db=line_strength(P, FFL), peak_hz=peak_hz(P))
out["decomposition_el0"] = DEC

json.dump(out, open(f"{ROOT}/outputs/az_falsify_rhythm.json", "w"),
          ensure_ascii=False, indent=1)
print(json.dumps(out["cells"], ensure_ascii=False, indent=1)[:200])
print("saved")
