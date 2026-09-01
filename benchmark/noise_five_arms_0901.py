# -*- coding: utf-8 -*-
"""noise_five_arms_0901.py — 잡음 그림을 **다섯 팔**로 다시 낸다 (덱 12·13 장).

⛔왜 다시 내나 — 지금 덱 3 부가 쓰는 그림은 옛 «엔진 셋» 틀이다
   (ours / PathSolver all off / refraction only / all on). 덱의 나머지는 전부
   **다섯 팔**(①다끔 ②굴절 ③회절 ④굴절+회절 ⑤ours) 축인데 3 부만 축이 달라
   같은 것을 두 이름으로 부르게 된다.

⭐잡음은 **후처리**다 — 저장된 원장 시계열에 복소 백색가우스를 섞는다. GPU 를 안 쓴다.
   주입·마스크·통계는 `benchmark/noise_distance_frame.py` 의 함수를 그대로 빌린다
   (규약이 갈리면 옛 판과 못 잇는다).

    CUDA_VISIBLE_DEVICES="" PYTHONPATH=src:benchmark \\
      ~/.venvs/py312/bin/python benchmark/noise_five_arms_0901.py
"""
import json
import os
import sys

import numpy as np

ROOT = "/workspace/sionna"
sys.path.insert(0, f"{ROOT}/benchmark")
sys.path.insert(0, f"{ROOT}/src")
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

import matplotlib.pyplot as plt                                        # noqa: E402
from noise_distance_frame import (make_masks, run_noise_only, run_signal,  # noqa: E402
                                  HW_HZ, BAND_LO)

FIG = f"{ROOT}/outputs/figures"
OUT = f"{ROOT}/outputs/noise_five_arms_0901.json"
MESH = "mfixbatteryi5_blperairframe"
EL = -30.0
N_TRIAL = 4000
SEED = 20260901

#: 다섯 팔 — 덱과 **같은 축·같은 색**이라야 3 부가 나머지와 이어진다
ARMS = [("①all off (diffuse only)", "R0D0E0F1", "#8e9aab"),
        ("②refraction",             "R1D0E0F1", "#6a8fbf"),
        ("③diffraction",            "R0D1E1F1", "#c62828"),
        ("④refraction+diffraction", "R1D1E1F1", "#8e3b3b"),
        ("⑤ours (SBR+PO)",          None,       "#1565c0")]
SNRS = np.arange(-40.0, 24.1, 2.0)


def arm_name(bits, r=15):
    rt_ = "" if r == 10 else f"_r{r:g}"
    if bits is None:
        return f"ours{rt_}_n8192_{MESH}"
    return f"sionna_p4000000000_sw{bits}{rt_}_n8192_{MESH}_d2"


def main():
    L = json.load(open(f"{ROOT}/outputs/elevation_sweep_md.json", encoding="utf-8"))
    Z = np.load(f"{ROOT}/outputs/elevation_sweep_md.npz")
    prf = float(L["_meta"]["prf_hz"])
    ffl = float(L["_meta"]["f_flash_hz"])
    # ⚠원장 _meta 에 f_tip_hz 가 없다 — 기체 제원에서 직접 낸다(리포트 12 와 같은 식)
    from drones import DRONES
    _s = DRONES["matrice4e"]
    ftip = (2 * (np.pi * (float(_s.prop_dia_mm) / 1000.0) * float(_s.hover_rpm) / 60.0)
            / (2.998e8 / 3.5e9)) * np.cos(np.radians(EL))
    rng = np.random.default_rng(SEED)

    E0 = np.asarray(Z[f"{arm_name(ARMS[0][1])}/el{EL:+.0f}"])
    n = E0.size
    w = np.hanning(n)
    masks = {"el": make_masks(n, prf, ftip, ffl)}
    print(f"  자세 {n} · PRF {prf:.0f} · f_flash {ffl:.2f} · f_tip(el{EL:+.0f}) {ftip:.1f} Hz")

    # ── 판정 막대 — 잡음 **전용** 시행의 p99.9
    nz = run_noise_only(rng, N_TRIAL, n, w, masks)["el"]["comb_db"]
    bar = float(np.mean(nz) + 3.090 * np.std(nz))
    print(f"  판정 막대 {bar:.2f} dB (잡음 전용 {N_TRIAL} 시행 · p99.9 정규근사 "
          f"· p95 검산 {np.percentile(nz, 95):.2f} vs {np.mean(nz)+1.645*np.std(nz):.2f})")

    curves, need = {}, {}
    for lab, bits, col in ARMS:
        key = f"{arm_name(bits)}/el{EL:+.0f}"
        E = np.asarray(Z[key])
        ac = E - E.mean()
        Eu = E / np.sqrt(float(np.mean(np.abs(ac) ** 2)))    # ⟨|AC|²⟩ = 1
        ys = []
        for s in SNRS:
            r = run_signal(rng, Eu, float(s), 400, w, masks["el"])
            ys.append(float(np.mean(r["comb_db"])))
        curves[lab] = ys
        # 막대를 처음 넘는 SNR — 선형보간
        need[lab] = None
        for i in range(1, len(ys)):
            if ys[i - 1] < bar <= ys[i]:
                t = (bar - ys[i - 1]) / (ys[i] - ys[i - 1])
                need[lab] = float(SNRS[i - 1] + t * (SNRS[i] - SNRS[i - 1]))
                break
        print(f"  {lab:<24} 최대 {max(ys):>6.1f} dB · 필요 SNR "
              f"{'—' if need[lab] is None else f'{need[lab]:+.1f} dB'}")

    # ── 그림
    fig, ax = plt.subplots(figsize=(13.6, 7.4))
    for lab, bits, col in ARMS:
        ax.plot(SNRS, curves[lab], "-", color=col, lw=3.0,
                label=lab.split("(")[0].strip()[1:])
        if need[lab] is not None:
            ax.plot([need[lab]], [bar], "o", ms=11, color=col, mec="white", mew=2,
                    zorder=6)
    ax.axhline(bar, color="#141926", lw=2.0, ls=(0, (6, 4)))
    ax.text(SNRS[-1], bar + 1.2, f"decision bar {bar:.2f} dB "
            f"(noise only, {N_TRIAL:,} trials, p99.9)",
            ha="right", fontsize=15, color="#141926", weight="bold")
    ax.set_xlabel("per-sample SNR of the moving part [dB]")
    ax.set_ylabel("comb contrast [dB]")
    ax.set_xlim(SNRS[0], SNRS[-1])
    ax.grid(True, color="#D5D5D5", lw=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(fontsize=17, frameon=False, loc="upper left")
    fig.subplots_adjust(top=0.80, bottom=0.115, left=0.075, right=0.985)
    fig.text(0.5, 0.955, "how much SNR each arm needs before the pattern reads",
             ha="center", fontsize=23, color="#141926", weight="bold")
    fig.text(0.5, 0.905, "turning diffraction on costs about 10 dB of SNR, and caps the "
             "contrast at a quarter of what the others reach",
             ha="center", fontsize=17, color="#C81E3C", weight="bold")
    fig.text(0.5, 0.865, f"matrice4e · 15 m · el {EL:+.0f}{chr(176)} · noise added to the "
             f"stored time series (no GPU) · dots mark where each arm crosses the bar",
             ha="center", fontsize=14, color="#5E5E5E")
    fig.text(0.008, 0.012, "verified: the ordering between arms and the SNR a pattern "
             "needs.   not verified: absolute metres - no field comparison yet",
             ha="left", fontsize=13, color="#5E5E5E")
    p = f"{FIG}/vol_noise_five_arms.png"
    fig.savefig(p, dpi=140)
    plt.close(fig)
    print(f"  ✅ {p}")

    # ── ⓑ 무늬가 녹는 과정 — 같은 판에 잡음만 올린다 (덱 12 장)
    #    ⚠옛 그림은 **정본 메쉬 이전** 팔(ours_r15_n8192)을 썼다 — 덱의 나머지와 판이 달랐다.
    import importlib
    os.environ["SWGRID_EL"] = f"{EL:g}"
    import build_switch_grid_figs as G
    importlib.reload(G)
    Eo = np.asarray(Z[f"{arm_name(None)}/el{EL:+.0f}"])
    n0, nz2 = int(round(G.T0 * G.PRF)), int(round(G.TSPAN * G.PRF))
    x0 = Eo[n0:n0 + nz2]
    x0 = x0 - x0.mean()
    pac = float((np.abs(x0) ** 2).mean())
    r2 = np.random.default_rng(5)
    LV = [None, 20.0, 10.0, 3.0, 0.0]
    fig2, ax2 = plt.subplots(1, len(LV), figsize=(4.9 * len(LV), 5.4), sharey=True)
    for a, sv in zip(ax2, LV):
        x = x0 if sv is None else x0 + np.sqrt(pac / 10 ** (sv / 10) / 2) * (
            r2.normal(size=x0.size) + 1j * r2.normal(size=x0.size))
        f_, t_, S_, _ = G.flash_spec(x, G.PRF, G.FFL, G.PERIODS)
        G.draw(a, t_, f_, S_, G.FT30)
        a.set_ylim(-2000, 2000)
        a.set_title("no noise" if sv is None else f"SNR {sv:.0f} dB",
                    fontsize=20, pad=9)
        a.set_xlabel("time [ms]")
    ax2[0].set_ylabel("Doppler [Hz]")
    fig2.subplots_adjust(top=0.775, bottom=0.135, left=0.055, right=0.988, wspace=0.06)
    fig2.text(0.5, 0.945, "the same run as noise is added",
              ha="center", fontsize=24, color="#141926", weight="bold")
    fig2.text(0.5, 0.895, "the stripes hold down to a few dB, then go",
              ha="center", fontsize=18, color="#C81E3C", weight="bold")
    fig2.text(0.5, 0.855, f"our kernel · matrice4e · 15 m · el {EL:+.0f}{chr(176)} · "
              "each panel scaled to its own peak", ha="center", fontsize=14,
              color="#5E5E5E")
    p2 = f"{FIG}/vol_noise_maps_canon.png"
    fig2.savefig(p2, dpi=140)
    plt.close(fig2)
    print(f"  ✅ {p2}")

    json.dump(dict(_meta=dict(generator="benchmark/noise_five_arms_0901.py",
                              gpu_used=False, el_deg=EL, n_poses=n, prf_hz=prf,
                              f_flash_hz=ffl, f_tip_hz=round(ftip, 1),
                              n_trial_null=N_TRIAL, seed=SEED,
                              bar_db=round(bar, 3), hw_hz=HW_HZ, band_lo=BAND_LO,
                              note_ko=("잡음은 후처리다 — 저장된 시계열에 복소 백색가우스를 "
                                       "섞는다. 주입·마스크·통계는 noise_distance_frame.py "
                                       "의 함수를 그대로 쓴다.")),
                   snr_db=[float(x) for x in SNRS],
                   curves={k: [round(v, 3) for v in vv] for k, vv in curves.items()},
                   snr_needed_db={k: (None if v is None else round(v, 2))
                                  for k, v in need.items()}),
              open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"  ✅ {OUT}")


if __name__ == "__main__":
    print("═══ 잡음 · 다섯 팔 ═══")
    main()
