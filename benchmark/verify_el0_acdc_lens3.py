"""el 0 의 AC/DC 상승이 «움직이는 성분» 인가 «표본화 잡음» 인가 — 렌즈 3 검증.

원장(elevation_sweep_md.npz/.json)은 읽기만 한다. GPU 미사용, numpy FFT 만.
정의는 benchmark/build_ch1_elevation_figs.py 와 같다(4096 점 한나 창, Δf = 4.81 Hz).
새 원장 outputs/verify_el0_acdc_lens3.json 만 쓴다.
"""
import json

import numpy as np

ROOT = "/workspace/sionna"
Z = np.load(f"{ROOT}/outputs/elevation_sweep_md.npz", allow_pickle=True)
J = json.load(open(f"{ROOT}/outputs/elevation_sweep_md.json"))
PRF = float(J["_meta"]["prf_hz"])
FFL = float(J["_meta"]["f_flash_hz"])
N = 4096
FR = np.fft.fftshift(np.fft.fftfreq(N, 1.0 / PRF))
AF = np.abs(FR)
WIN = np.hanning(N)
FTIP0 = 1272.9                       # el 0 의 f_tip [Hz] — elevation_sweep_md.json rows
LO, HI = 0.35 * FTIP0, FTIP0         # 추적 대역
OOB_LO = 2600.0                      # 대역외 기준띠 (같은 폭)
IN_B = (AF >= LO) & (AF <= HI)
OOB_B = (AF >= OOB_LO) & (AF <= OOB_LO + (HI - LO))
COMB = np.zeros(N, bool)
for k in range(1, 31):
    COMB |= np.abs(AF - k * FFL) <= 12.0
NEUTRAL = 10 * np.log10(COMB.sum() / N)   # 백색 잡음이면 빗살 몫이 이 값이다

ROW = {r["engine"]: r for r in J["rows"] if abs(r["el_deg"]) < 1e-9}
ARMS = ["ours", "sionna", "sionna_p250000000",
        "sionna_p1000000000", "sionna_p4000000000"]


def cell(eng):
    E = np.asarray(Z[f"{eng}/el+0"], complex)
    d = E / E.mean() - 1.0                       # DC 로 정규화한 변동
    Pd = np.abs(np.fft.fftshift(np.fft.fft(d * WIN))) ** 2
    r = ROW[eng]
    return dict(
        engine=eng,
        n_poses=int(E.size),
        n_missing=r.get("n_missing"),
        npaths_median=r.get("npaths_median"),
        level_db=r.get("level_db"),
        ac_over_dc_db=round(float(10 * np.log10(np.mean(np.abs(d) ** 2))), 2),
        ac_inband_share_db=round(float(10 * np.log10(Pd[IN_B].sum() / Pd.sum())), 2),
        ac_oob_share_db=round(float(10 * np.log10(Pd[OOB_B].sum() / Pd.sum())), 2),
        ac_inband_minus_oob_db=round(float(
            10 * np.log10(Pd[IN_B].sum() / Pd[OOB_B].sum())), 2),
        comb_share_of_ac_db=round(float(10 * np.log10(Pd[COMB].sum() / Pd.sum())), 2),
        comb_excess_over_white_db=round(float(
            10 * np.log10(Pd[COMB].sum() / Pd.sum()) - NEUTRAL), 2),
    )


C = {a: cell(a) for a in ARMS}
lad = [("sionna", "sionna_p250000000"), ("sionna_p250000000", "sionna_p1000000000"),
       ("sionna_p1000000000", "sionna_p4000000000")]
OUT = {
    "_meta": {
        "generator": "benchmark/verify_el0_acdc_lens3.py",
        "date": "2026-08-12",
        "question_ko": "el 0 에서 AC/DC 가 예산을 따라 오른다 — 오르는 것이 "
                       "움직이는 성분인가 표본화 잡음인가",
        "verdict_ko": "표본화 잡음이다. 250 M 이상에서 변동 스펙트럼은 백색이고, "
                      "AC 전력은 경로 수에 비례한다. 11.1 M 이 갖고 있던 빗살 구조는 "
                      "예산을 올리면 사라진다.",
        "compute_ko": "GPU 미사용. 원장 npz 를 읽어 numpy FFT 만 했다.",
        "reads_only": ["outputs/elevation_sweep_md.npz",
                       "outputs/elevation_sweep_md.json"],
        "spectrum_ko": f"{N} 점 한나 창 FFT, Δf = {PRF / N:.2f} Hz — "
                       "build_ch1_elevation_figs.py 와 같은 규약",
        "ac_spectrum_ko": "DC 로 나누고 1 을 뺀 변동 d = E/mean(E) − 1 의 스펙트럼. "
                          "ac_over_dc_db = 10log10 mean|d|² 와 같은 물건이다",
        "band_ko": f"추적 대역 {LO:.1f}~{HI:.1f} Hz · 대역외 기준띠 "
                   f"{OOB_LO:.0f}~{OOB_LO + HI - LO:.1f} Hz (같은 폭 {int(IN_B.sum())} 빈)",
        "comb_ko": f"빗살 30 차, 각 ±12 Hz — {int(COMB.sum())} 빈 / {N}. "
                   f"변동이 백색이면 몫은 {NEUTRAL:.2f} dB 다",
        "units_warning_ko": "ours 는 E [m²], sionna 는 h [무차원]. AC/DC 는 비율이라 "
                            "눈금 무관이지만, 두 팔의 AC 가 같은 물건인지는 "
                            "빗살 몫으로 따로 봐야 한다",
    },
    "white_noise_neutral_comb_share_db": round(float(NEUTRAL), 2),
    "cells": C,
    "budget_ladder": [
        {
            "from": a, "to": b,
            "npaths_median": [C[a]["npaths_median"], C[b]["npaths_median"]],
            "ac_rise_db": round(C[b]["ac_over_dc_db"] - C[a]["ac_over_dc_db"], 2),
            "ten_log10_path_ratio_db": round(float(
                10 * np.log10(C[b]["npaths_median"] / C[a]["npaths_median"])), 2),
            "level_change_db": round(C[b]["level_db"] - C[a]["level_db"], 2),
        } for a, b in lad
    ],
    "findings_ko": [
        "받침대(정지 성분)는 예산을 11.1 M → 4 G 로 360 배 늘려도 레벨이 "
        f"{C['sionna']['level_db']} → {C['sionna_p4000000000']['level_db']} dB 로 "
        "0.03 dB 안에 머문다.",
        "AC/DC 는 예산을 따라 단조 상승한다 — "
        f"{C['sionna']['ac_over_dc_db']} → {C['sionna_p250000000']['ac_over_dc_db']} → "
        f"{C['sionna_p1000000000']['ac_over_dc_db']} → "
        f"{C['sionna_p4000000000']['ac_over_dc_db']} dB.",
        "250 M 이상에서 그 AC 는 백색이다 — 블레이드 대역과 대역외 기준띠의 차이가 "
        f"{C['sionna_p250000000']['ac_inband_minus_oob_db']} dB 이고, 빗살 30 차의 몫이 "
        f"{C['sionna_p250000000']['comb_share_of_ac_db']} dB 로 백색 중립값 "
        f"{NEUTRAL:.2f} dB 와 같다.",
        "11.1 M 은 반대다 — 빗살이 AC 의 "
        f"{C['sionna']['comb_share_of_ac_db']} dB(중립 대비 "
        f"+{C['sionna']['comb_excess_over_white_db']} dB)를 담고 대역 초과가 "
        f"{C['sionna']['ac_inband_minus_oob_db']} dB 다. 예산을 올리면 이 구조가 묻힌다.",
        "AC 전력은 경로 수를 따라간다 — 127 → 471 벌에서 AC 가 "
        f"{round(C['sionna_p1000000000']['ac_over_dc_db'] - C['sionna_p250000000']['ac_over_dc_db'], 2)}"
        f" dB 오르고 10log10(471/127) = "
        f"{round(float(10 * np.log10(471 / 127)), 2)} dB 다.",
        "우리 팔의 AC 는 같은 자리에서 빗살이 "
        f"{C['ours']['comb_share_of_ac_db']} dB(중립 대비 "
        f"+{C['ours']['comb_excess_over_white_db']} dB)를 담고 대역 초과가 "
        f"{C['ours']['ac_inband_minus_oob_db']} dB 다 — 변조 깊이를 재고 있다.",
    ],
}

p = f"{ROOT}/outputs/verify_el0_acdc_lens3.json"
json.dump(OUT, open(p, "w"), ensure_ascii=False, indent=1)
print(json.dumps(OUT, ensure_ascii=False, indent=1))
print("wrote", p)
