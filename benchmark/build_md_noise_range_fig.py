# -*- coding: utf-8 -*-
"""
build_md_noise_range_fig.py — ⭐**거리에 따라 블레이드선이 잡음에 묻히는 과정** 한 장

무엇이 다른가 (이 그림의 존재 이유)
------------------------------------
지금까지의 맵은 **패널마다 자기 최대값으로 정규화**했다(`md_mapstyle.draw(ref=None)`).
그러면 40 m 가 3 m 보다 45 dB 약하다는 사실이 **그림에서 통째로 사라진다** — 어느 패널이나
빨간 동체선과 초록 플래시가 똑같이 예쁘게 보인다. 조사가 지적한 바로 그 함정이다.

그래서 이 그림은 **절대 눈금**을 쓴다:
    색 = 20·log10(|S| / 잡음바닥),  0 dB = **잡음 바닥**,  모든 패널이 **같은 색역**.
잡음 바닥은 예측식이 아니라 **측정값**이다 — 같은 STFT 설정에 잡음만 통과시켜 rms 를 잰다
(`md_mapstyle.noise_rms_from`). 창 손실·겹침 상관이 자동으로 들어가므로 우리가 유추한
`g_stft_db` 를 안 믿어도 그림은 옳다.

잡음은 **슬로타임 시계열에 더하고 그 다음 STFT** 한다(`nf.noisy_series`, 입구 하나).
맵에 직접 더하면 잡음 바닥이 지수분포(χ²₂) 대신 가우시안이 되고 신호×잡음 교차항이 빠진다.

산출
  outputs/figures/md_noise_vs_range.{png,pdf}
  outputs/md_noise_range_fig.json   — 패널마다 시드·사다리 세 층위·측정 첨두

실행:
    cd sionna2 && PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/build_md_noise_range_fig.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                     # noqa: E402
import numpy as np                                                  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

import microdoppler_nearfield as nf                                 # noqa: E402
from drones import DRONES                                           # noqa: E402
from md_mapstyle import (auto_periods, caption_snr, draw, flash_spec,  # noqa: E402
                         noise_rms_from)

FIG = os.path.join(ROOT, "outputs", "figures")
OUT = os.path.join(ROOT, "outputs", "md_noise_range_fig.json")
SWEEP_NEW = os.path.join(ROOT, "outputs", "md_range_sweep_mf.json")
SWEEP_OLD = os.path.join(ROOT, "outputs", "md_range_sweep.json")

DRONE, BAND, FC = "matrice4e", "5G NR 3.5 GHz", 3.5e9
AZ, EL = 0.0, 15.0
PRF, N_T, N_PHASE = 20000.0, 6144, 480
PANEL_R_M = [10.0, 20.0, 30.0, 40.0, 60.0]
EIRP_DBM = nf.DECLARED_EIRP_DBM          # 12 dBm, 선언값(챔버급)
SEED_BASE = 20260811
VMIN_DB, VMAX_DB = -6.0, 50.0            # ⭐다섯 패널 **공통** 색역 [dB above noise]
BAND_LO, BAND_HI = 0.35, 1.00            # 날개끝 띠 (f_tip 배수) — 블레이드선을 재는 창
C_TOT, C_AC, C_MAP = "#00695c", "#c62828", "#6a1b9a"


def _sweep():
    p = SWEEP_NEW if os.path.exists(SWEEP_NEW) else SWEEP_OLD
    with open(p) as f:
        return json.load(f), p


def _cell(doc):
    for c in doc["cells"]:
        if c["drone"] == DRONE and c["band"] == BAND:
            return c
    raise KeyError(f"{DRONE}/{BAND}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ranges", default=",".join(f"{r:g}" for r in PANEL_R_M))
    ap.add_argument("--seed", type=int, default=SEED_BASE)
    a = ap.parse_args()
    t0 = time.time()
    ranges = [float(x) for x in a.ranges.split(",") if x.strip()]

    doc, src = _sweep()
    cell = _cell(doc)
    # ⭐ σ 도 dc_ac 도 **원장에서** 가져온다(새로 지어내지 않는다).
    sigma_dbsm = float(cell["rows"][0]["sigma_eq_aspect_mean_plane_dbsm"])
    sigma_m2 = 10.0 ** (sigma_dbsm / 10.0)
    dc_ac_db = float(cell["rows"][0]["arms"]["A0_reference"]["dc_ac_db"])
    f_tip, f_flash = float(cell["f_tip_hz"]), float(cell["flash_hz"])
    periods = auto_periods(PRF, f_flash)

    #  ── 잡음 바닥 기준: 단위분산 복소잡음을 **같은 STFT** 로 통과시켜 rms 를 잰다 ──
    #     모든 패널이 이 한 수를 0 dB 로 쓴다(그래서 패널끼리 비교가 성립한다).
    rng_n = np.random.default_rng(nf.stable_seed("noise_floor_probe", base=a.seed))
    n0 = (rng_n.normal(0, np.sqrt(0.5), N_T) + 1j * rng_n.normal(0, np.sqrt(0.5), N_T))
    fN, tN, SN, nper = flash_spec(n0, PRF, f_flash, periods)
    noise_rms = noise_rms_from(SN)

    panels, ladders = [], []
    for R in ranges:
        _, E, info = nf.microdoppler_nf(DRONES[DRONE], FC, R, AZ, EL, wavefront="spherical",
                                        prf=PRF, n_t=N_T, n_phase=N_PHASE)
        lad = nf.snr_ladder(sigma_m2, R, FC, prf=PRF, capture="full_waveform",
                            dc_ac_db=dc_ac_db, nperseg=nper, window="hann",
                            eirp_dbm=EIRP_DBM)
        seed = nf.stable_seed(DRONE, BAND, f"{R:g}", "fig", base=a.seed)
        #  ⭐ 잡음 주입 입구 하나. 눈금은 ③(슬로타임 총전력) — add_noise 의 기준과 같다.
        En, prov = nf.noisy_series(E, lad["snr_slow_db"], seed, ref="total", n_real=1,
                                   capture="full_waveform")
        #  잡음 표준편차로 나눠 «잡음 = 단위분산» 으로 옮긴다. 그래야 다섯 패널의 0 dB 가
        #  같은 물리량(열잡음 바닥)이고, 신호는 거리에 따라 실제로 가라앉는다.
        x = En[0] / prov["sigma_n"]
        f, t, S, _ = flash_spec(x, PRF, f_flash, periods)
        band = (np.abs(f) >= BAND_LO * f_tip) & (np.abs(f) <= BAND_HI * f_tip)
        dc = np.abs(f) <= 0.5 * f_flash
        meas = dict(
            blade_band_peak_over_noise_db=float(20 * np.log10(S[band].max() / noise_rms)),
            body_dc_peak_over_noise_db=float(20 * np.log10(S[dc].max() / noise_rms)),
            map_median_over_noise_db=float(20 * np.log10(np.median(S) / noise_rms)))
        panels.append(dict(R_m=R, S=S, f=f, t=t, meas=meas, seed=seed, lad=lad,
                           sigma_n=prov["sigma_n"]))
        ladders.append(lad)

    # ── 그림 ────────────────────────────────────────────────────────────────
    n = len(panels)
    fig = plt.figure(figsize=(3.5 * n + 1.3, 7.4))
    gs = fig.add_gridspec(2, n + 1, height_ratios=[1.0, 0.82],
                          width_ratios=[1] * n + [0.045],
                          left=0.062, right=0.935, top=0.865, bottom=0.085,
                          wspace=0.13, hspace=0.42)
    m = None
    for i, p in enumerate(panels):
        ax = fig.add_subplot(gs[0, i])
        #  ⭐ 절대 눈금 — 모든 패널이 같은 noise_rms, 같은 vmin/vmax (게이트 NI5 가 확인)
        m = draw(ax, p["t"], p["f"], p["S"], f_tip, mode="over_noise",
                 noise_rms=noise_rms, vmin=VMIN_DB, vmax=VMAX_DB)
        ax.set_title(f"R = {p['R_m']:g} m\nblade line (AC) {p['lad']['snr_slow_ac_db']:+.1f} dB",
                     fontsize=11, fontweight="bold",
                     color=("#2e7d32" if p["lad"]["snr_slow_ac_db"] > 0 else "#c62828"))
        ax.set_xlabel("Slow time [ms]", fontsize=9.5)
        if i == 0:
            ax.set_ylabel("Doppler [Hz]", fontsize=10)
        else:
            plt.setp(ax.get_yticklabels(), visible=False)
    cb = fig.colorbar(m, cax=fig.add_subplot(gs[0, n]))
    cb.set_label("dB above the measured noise floor  (same scale in every panel)", fontsize=9.5)

    ax = fig.add_subplot(gs[1, :n])
    Rg = np.logspace(np.log10(3.0), np.log10(300.0), 260)
    L = [nf.snr_ladder(sigma_m2, float(r), FC, prf=PRF, capture="full_waveform",
                       dc_ac_db=dc_ac_db, nperseg=nper, window="hann", eirp_dbm=EIRP_DBM)
         for r in Rg]
    ax.semilogx(Rg, [d["snr_slow_db"] for d in L], "-", color=C_TOT, lw=2.0,
                label="slow-time sample, total power  (rung 3)")
    ax.semilogx(Rg, [d["snr_slow_ac_db"] for d in L], "-", color=C_AC, lw=2.4,
                label=f"blade line, AC  (rung 3', canonical) = total − {L[0]['dc_ac_off_db']:.1f} dB")
    ax.semilogx(Rg, [d["snr_map_ac_db"] for d in L], "--", color=C_MAP, lw=1.8,
                label=f"blade line on the map  (rung 3' + gain_stft {L[0]['g_stft_db']:+.1f} dB, "
                      f"{nper}-sample Hann frame)")
    #  측정한 첨두를 사다리 위에 얹는다 — 예측과 측정을 같은 그림에서 대조한다
    ax.semilogx([p["R_m"] for p in panels],
                [p["meas"]["blade_band_peak_over_noise_db"] for p in panels],
                "o", ms=8, mfc="white", mec=C_MAP, mew=2.0,
                label="measured blade-band peak on the maps above")
    ax.axhline(0.0, color="k", ls=":", lw=1.2)
    ax.text(3.2, 1.0, "noise floor", fontsize=9)
    r0 = nf.range_for_snr_db(0.0, sigma_m2, FC, rung="snr_slow_ac_db", prf=PRF,
                             capture="full_waveform", dc_ac_db=dc_ac_db, eirp_dbm=EIRP_DBM)
    r1 = nf.range_for_snr_db(0.0, sigma_m2, FC, rung="snr_slow_db", prf=PRF,
                             capture="full_waveform", dc_ac_db=dc_ac_db, eirp_dbm=EIRP_DBM)
    ax.axvspan(r0, r1, color="#ffe0b2", alpha=0.75, zorder=0)
    ax.text(np.sqrt(r0 * r1), -33, "detected, but no micro-Doppler\n"
            f"{r0:.0f} – {r1:.0f} m", ha="center", fontsize=9.5, color="#8d4e00")
    for p in panels:
        ax.axvline(p["R_m"], color="0.75", lw=0.8, zorder=0)
    ax.set_xlim(3.0, 300.0); ax.set_ylim(-40, 60)
    ax.set_xlabel("Monostatic-equivalent range R [m]   (both legs move: −40 dB/decade)")
    ax.set_ylabel("SNR [dB]")
    ax.grid(alpha=0.3, which="both")
    ax.legend(fontsize=9, loc="upper right", framealpha=0.93)

    fig.suptitle(
        f"How the blade line drowns with range — {DRONE}, {BAND}, hovering, "
        f"monostatic equivalent, thermal noise only\n"
        f"absolute colour scale (0 dB = measured noise floor), EIRP {EIRP_DBM:g} dBm, "
        f"σ {sigma_dbsm:.2f} dBsm (azimuth mean), DC/AC {dc_ac_db:.1f} dB, "
        f"matched-filter gain {L[0]['g_mf_db']:+.2f} dB included",
        fontsize=12.2, fontweight="bold", y=0.975)

    os.makedirs(FIG, exist_ok=True)
    for e in ("png", "pdf"):
        fig.savefig(f"{FIG}/md_noise_vs_range.{e}", bbox_inches="tight", facecolor="white")
    plt.close(fig)

    led = dict(
        _meta=dict(
            title="blade line vs range under thermal noise, absolute (dB-above-noise) scale",
            generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
            generator="benchmark/build_md_noise_range_fig.py",
            figure="outputs/figures/md_noise_vs_range.png",
            convention=nf.SNR_CONVENTION, canonical_rung=nf.CANONICAL_SNR_KEY,
            drone=DRONE, band=BAND, fc_hz=FC, az_deg=AZ, el_deg=EL,
            capture="full_waveform", noise="thermal_only",
            geometry="monostatic_equivalent",
            sigma_dbsm=sigma_dbsm, sigma_source=f"{os.path.relpath(src, ROOT)}"
                                                "::rows[0].sigma_eq_aspect_mean_plane_dbsm",
            sigma_note="plane-wave azimuth mean; the spherical-wave value differs by <0.05 dB "
                       "for R>=10 m in the same ledger, so the link budget is insensitive to it",
            dc_ac_db=dc_ac_db, eirp_dbm=EIRP_DBM, rx_gain_dbi=nf.DECLARED_RX_GAIN_DBI,
            nf_db=nf.DECLARED_NF_DB, b_hz=nf.DECLARED_B_HZ, prf_hz=PRF, n_t=N_T,
            noise_injection="nf.noisy_series -> complex white Gaussian added to the SLOW-TIME "
                            "series, THEN STFT. Never added to the map.",
            seed_base=a.seed, seed_rule="nf.stable_seed(drone, band, R, 'fig', base=seed_base)",
            stft=dict(nperseg=int(nper), periods_of_blade=float(periods),
                      window="hann", hop=2, zero_pad=8, f_flash_hz=f_flash,
                      dt_ms=round(nper / PRF * 1e3, 3), df_hz=round(PRF / nper, 1)),
            colour=dict(mode="over_noise", vmin_db=VMIN_DB, vmax_db=VMAX_DB,
                        zero_db="measured noise floor (rms magnitude of a noise-only "
                                "spectrogram through the identical STFT)",
                        noise_rms=float(noise_rms),
                        why="normalising each panel to its own peak hides the range dependence "
                            "entirely; that is what the previous map figures did"),
            three_layers=dict(
                snr_sample_db="rung 1, per Rx sample before the matched filter",
                gain_mf_db="rung 2, 10log10(B/PRF)",
                gain_stft_db=f"rung 4, one {int(nper)}-sample Hann STFT frame "
                             "(NOT the whole-CPI coherent gain, which is ~20 dB larger)"),
            caveat="thermal noise only - no clutter, no direct-path residue, no ECA notch, no "
                   "phase noise; and gain_mf_db assumes an ideal matched filter with a clean "
                   "reference channel"),
        noise_floor=dict(measured_rms=float(noise_rms),
                         probe="unit-variance circular complex Gaussian, N_T samples, same STFT"),
        panels=[dict(R_m=p["R_m"], noise_seed=int(p["seed"]), sigma_n=float(p["sigma_n"]),
                     snr_sample_db=round(float(p["lad"]["snr_sample_db"]), 4),
                     gain_mf_db=round(float(p["lad"]["gain_mf_db"]), 4),
                     snr_slow_db=round(float(p["lad"]["snr_slow_db"]), 4),
                     dc_ac_off_db=round(float(p["lad"]["dc_ac_off_db"]), 4),
                     snr_slow_ac_db=round(float(p["lad"]["snr_slow_ac_db"]), 4),
                     gain_stft_db=round(float(p["lad"]["gain_stft_db"]), 4),
                     snr_map_ac_db=round(float(p["lad"]["snr_map_ac_db"]), 4),
                     measured=({k: round(v, 3) for k, v in p["meas"].items()}),
                     predicted_minus_measured_db=round(
                         float(p["lad"]["snr_map_ac_db"]) -
                         p["meas"]["blade_band_peak_over_noise_db"], 3),
                     caption=caption_snr(p["lad"]))
                for p in panels],
        region_ii=dict(inner_m=round(r0, 2), outer_m=round(r1, 2),
                       meaning="echo above noise but blade line below it"),
        runtime_s=round(time.time() - t0, 2),
    )
    tmp = OUT + ".tmp"
    with open(tmp, "w") as f:
        json.dump(led, f, indent=1, ensure_ascii=False, default=float)
    os.replace(tmp, OUT)

    print(f"noise floor rms (STFT, unit-variance noise) = {noise_rms:.5g}")
    for p in led["panels"]:
        print(f"  R={p['R_m']:6.1f} m  rung3 {p['snr_slow_db']:+7.2f}  "
              f"rung3' {p['snr_slow_ac_db']:+7.2f}  rung5 {p['snr_map_ac_db']:+7.2f}  | "
              f"measured blade peak {p['measured']['blade_band_peak_over_noise_db']:+7.2f} dB, "
              f"body DC {p['measured']['body_dc_peak_over_noise_db']:+7.2f} dB")
    print(f"\n→ outputs/figures/md_noise_vs_range.png\n→ {os.path.relpath(OUT, ROOT)} "
          f"({time.time() - t0:.1f} s)")


if __name__ == "__main__":
    main()
