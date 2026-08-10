# -*- coding: utf-8 -*-
"""
viz_md_range.py — 거리 스윕 마이크로도플러 3-팔 분리 실험 그림
================================================================
입력: outputs/md_range_sweep.json (experiment_md_range.py)
     + 스펙트로그램 그림(F1/F3)은 시계열이 필요하므로 이 스크립트가 직접 재계산한다.
산출: outputs/figures/md_range_*.png

그림 텍스트는 전부 영어(하우스 규약). 본문·주석은 한국어.

F1  spectrogram_grid   4팔 × 4거리 스펙트로그램 격자 — 헤드라인
F2  attribution        AC 상관 vs 거리, 팔별 — ⭐ 두 효과의 귀속을 보여주는 핵심 그림
F3  doppler_marginal   거리별 도플러 주변분포(A2) + f_tip 이론선
F4  collapse           R/R_ff 정규화 축에서 전 기종이 겹치는가
F5  dsigma             Δσ_eq(구면−평면) vs 거리, 드론·밴드별
F6  snr_wall           거리별 샘플 SNR 과 스펙트로그램 가시성
F7  farfield_map       드론 × 밴드 원거리장 경계 지도 (1/5/10/20 m 표시)
F8  prf_feasibility    상시 기준신호로 f_tip 을 볼 수 있는가
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)

import vizstyle                                            # noqa: E402
vizstyle.use_korean()
import matplotlib.pyplot as plt                            # noqa: E402

from drones import DRONES                                # noqa: E402
import microdoppler_nearfield as nf                        # noqa: E402
from microdoppler import spectrogram                       # noqa: E402
#  ⭐ 마이크로도플러 맵 표시 규약 — 한 자리(md_mapstyle)에서만 가져온다.
from md_mapstyle import auto_periods, draw as md_draw, flash_spec   # noqa: E402

SRC = os.path.join(_ROOT, "outputs", "md_range_sweep.json")
FIGDIR = os.path.join(_ROOT, "outputs", "figures")
HEADLINE_DRONE = "mavic4pro"
HEADLINE_BAND = "5G NR 3.5 GHz"
SHOW_RANGES = [1.0, 5.0, 10.0, 20.0]
ARM_LABEL = {
    "A0_reference": "A0  plane wave, no noise\n(far-field ideal)",
    "A1_snr_only": "A1  plane wave + range noise\n(visibility only)",
    "A2_nearfield": "A2  spherical wave, no noise\n(wavefront curvature only)",
    "A3_both": "A3  spherical + range noise\n(what you would observe)",
}
ARM_COLOR = {"A0_reference": "#455a64", "A1_snr_only": "#1565c0",
             "A2_nearfield": "#c62828", "A3_both": "#6a1b9a"}


def _load():
    with open(SRC) as f:
        return json.load(f)


def _cell(doc, drone, band):
    for c in doc["cells"]:
        if c["drone"] == drone and c["band"] == band:
            return c
    raise KeyError(f"{drone}/{band} not in {SRC}")


def _save(fig, name):
    os.makedirs(FIGDIR, exist_ok=True)
    p = os.path.join(FIGDIR, f"md_range_{name}.png")
    fig.savefig(p, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"  → {os.path.relpath(p, _ROOT)}")
    return p


# --------------------------------------------------------------------------- #
def _series_for(doc, drone, band, R, arm, rng):
    """그림용 시계열 재계산 (실험과 같은 설정)."""
    m = doc["meta"]
    spec = DRONES[drone]
    fc = _cell(doc, drone, band)["fc_hz"]
    prf, n_t, n_ph = m["slow_time"]["prf_hz"], m["slow_time"]["n_t"], m["slow_time"]["n_phase"]
    wv = "plane" if arm in ("A0_reference", "A1_snr_only") else "spherical"
    R_use = 1000.0 if arm in ("A0_reference", "A1_snr_only") else R
    _, E, info = nf.microdoppler_nf(spec, fc, R_use, m["geometry"]["az_deg"],
                                    m["geometry"]["el_deg"], wavefront=wv,
                                    prf=prf, n_t=n_t, n_phase=n_ph)
    if arm in ("A1_snr_only", "A3_both"):
        snr = nf.echo_over_noise_db(info["sigma_eq_mean_m2"], R, fc)
        E, _ = nf.add_noise(E, snr, rng)
    return E, info, prf


def f1_spectrogram_grid(doc):
    """F1 — 4팔 × 4거리 스펙트로그램. 한 장으로 두 효과가 눈에 보인다."""
    rng = np.random.default_rng(7)
    c = _cell(doc, HEADLINE_DRONE, HEADLINE_BAND)
    arms = list(ARM_LABEL)
    fig, axes = plt.subplots(len(arms), len(SHOW_RANGES),
                             figsize=(4.1 * len(SHOW_RANGES), 3.1 * len(arms)),
                             sharex=True, sharey=True)
    for i, arm in enumerate(arms):
        for j, R in enumerate(SHOW_RANGES):
            ax = axes[i, j]
            E, info, prf = _series_for(doc, HEADLINE_DRONE, HEADLINE_BAND, R, arm, rng)
            #  ⭐ 표시 규약은 src/md_mapstyle.py 한 자리가 정한다(우회 금지).
            #     옛 판은 nperseg 를 256 으로 **고정**해 두어, 기체·PRF 가 바뀌면 조각이
            #     블레이드 주기의 몇 배인지가 그림마다 달라졌다. 규약은 «주기의 배수» 로 잡는다.
            ffl = float(info["flash_hz"])
            f, tt, S, _n = flash_spec(E, prf, ffl, auto_periods(prf, ffl))
            im = md_draw(ax, tt, f, S, info["f_tip"])
            if i == 0:
                ax.set_title(f"R = {R:g} m" + ("   (far field)" if R >= c["r_ff_m"]
                                               else "   (NEAR field)"),
                             fontsize=11, fontweight="bold",
                             color="#2e7d32" if R >= c["r_ff_m"] else "#c62828")
            if j == 0:
                ax.set_ylabel(ARM_LABEL[arm] + "\n\nDoppler [Hz]", fontsize=8.5)
            if i == len(arms) - 1:
                ax.set_xlabel("Slow time [ms]", fontsize=9)
    fig.colorbar(im, ax=axes, shrink=0.6, pad=0.012, label="Magnitude [dB re max]")
    fig.suptitle(f"Micro-Doppler vs range — three-arm separation   "
                 f"({HEADLINE_DRONE}, {HEADLINE_BAND}, monostatic, el 15°)\n"
                 f"far-field boundary $2D^2/\\lambda$ = {c['r_ff_m']:.2f} m   |   "
                 f"white dashed = kinematic $\\pm f_{{tip}}$ = {c['f_tip_hz']:.0f} Hz",
                 fontsize=13, fontweight="bold", y=0.995)
    return _save(fig, "f1_spectrogram_grid")


def f2_attribution(doc):
    """F2 ⭐ — 팔별 AC 상관 vs 거리. 두 효과의 귀속을 한 장에."""
    c = _cell(doc, HEADLINE_DRONE, HEADLINE_BAND)
    R = np.array([r["R_m"] for r in c["rows"]])
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.0))
    for ax, key, lab in ((axes[0], "ac_corr_vs_ref", "AC correlation vs far-field reference"),
                         (axes[1], "spec_corr_vs_ref", "Spectrogram correlation vs reference")):
        for arm in ("A1_snr_only", "A2_nearfield", "A3_both"):
            y = [r["arms"][arm][key] for r in c["rows"]]
            ax.semilogx(R, y, "o-", color=ARM_COLOR[arm], lw=2, ms=6,
                        label=ARM_LABEL[arm].split("\n")[0])
        ax.axvline(c["r_ff_m"], color="k", ls=":", lw=1.6)
        ax.text(c["r_ff_m"], 0.02, f"  $2D^2/\\lambda$ = {c['r_ff_m']:.1f} m",
                rotation=90, va="bottom", fontsize=9)
        for x in SHOW_RANGES:
            ax.axvline(x, color="#bbbbbb", lw=0.7, zorder=0)
        ax.set_xlabel("Monostatic range R [m]")
        ax.set_ylabel(lab)
        ax.set_ylim(-0.02, 1.05)
        ax.grid(alpha=0.3, which="both")
        ax.legend(loc="lower right", fontsize=9)
    axes[0].set_title("Coherent time series (harsh metric)", fontweight="bold")
    axes[1].set_title("Spectrogram magnitude — what you would actually look at", fontweight="bold")
    fig.suptitle("Two opposing walls: wavefront curvature (A2, red) closes in from SHORT range, "
                 "noise (A1, blue) closes in from LONG range\n"
                 f"{HEADLINE_DRONE}, {HEADLINE_BAND}, monostatic — "
                 "the crossing is where the pattern is best preserved",
                 fontsize=12.5, fontweight="bold")
    fig.tight_layout()
    return _save(fig, "f2_attribution")


def f3_doppler_marginal(doc):
    """F3 — 거리별 도플러 주변분포(A2, 무잡음) + f_tip 이론선."""
    rng = np.random.default_rng(3)
    c = _cell(doc, HEADLINE_DRONE, HEADLINE_BAND)
    fig, ax = plt.subplots(figsize=(11, 5.4))
    cmap = plt.cm.viridis
    show = [1.0, 2.0, 5.0, 10.0, 20.0, 1000.0]
    for i, R in enumerate(show):
        E, info, prf = _series_for(doc, HEADLINE_DRONE, HEADLINE_BAND, R, "A2_nearfield", rng)
        ac = E - E.mean()
        S = np.abs(np.fft.fftshift(np.fft.fft(ac * np.hanning(len(ac))))) ** 2
        f = np.fft.fftshift(np.fft.fftfreq(len(ac), 1 / prf))
        S = 10 * np.log10(S / S.max())
        sel = np.abs(f) <= 2.0 * info["f_tip"]
        lab = f"R = {R:g} m" + ("  (far)" if R >= c["r_ff_m"] else "  (NEAR)")
        ax.plot(f[sel], S[sel], color=cmap(i / max(1, len(show) - 1)), lw=1.5, label=lab)
    for s in (+1, -1):
        ax.axvline(s * c["f_tip_hz"], color="#c62828", ls="--", lw=1.4)
    ax.text(c["f_tip_hz"], 2, f" kinematic $f_{{tip}}$ = {c['f_tip_hz']:.0f} Hz",
            color="#c62828", fontsize=9.5)
    ax.axhline(-20, color="k", ls=":", lw=1.0)
    ax.text(-2.0 * c["f_tip_hz"], -19.4, " −20 dB edge criterion", fontsize=9)
    ax.set_xlabel("Doppler [Hz]"); ax.set_ylabel("AC spectrum [dB re peak]")
    ax.set_ylim(-55, 5); ax.grid(alpha=0.3); ax.legend(fontsize=9, ncol=2)
    ax.set_title(f"Doppler extent is kinematic — the near field blunts the edge, it does not move it\n"
                 f"{HEADLINE_DRONE}, {HEADLINE_BAND}, arm A2 (spherical wave, noiseless)",
                 fontweight="bold")
    fig.tight_layout()
    return _save(fig, "f3_doppler_marginal")


def f4_collapse(doc):
    """F4 — R/R_ff 정규화 축에서 전 기종이 하나의 곡선으로 겹치는가."""
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.0))
    cells = [c for c in doc["cells"] if c["band"] == HEADLINE_BAND]
    cmap = plt.cm.tab10
    for i, c in enumerate(cells):
        x = np.array([r["R_over_Rff"] for r in c["rows"]])
        y1 = [r["arms"]["A2_nearfield"]["ac_corr_vs_ref"] for r in c["rows"]]
        y2 = [r["arms"]["A2_nearfield"]["flash_contrast_db"] for r in c["rows"]]
        lab = f"{c['drone']}  ($R_{{ff}}$={c['r_ff_m']:.1f} m)"
        axes[0].semilogx(x, y1, "o-", color=cmap(i), lw=1.8, ms=5, label=lab)
        axes[1].semilogx(x, y2, "o-", color=cmap(i), lw=1.8, ms=5, label=lab)
    for ax, yl, ttl in ((axes[0], "AC correlation vs far-field reference",
                         "Pattern fidelity collapses onto $R/R_{ff}$"),
                        (axes[1], "Flash contrast [dB]",
                         "Flash sharpness vs normalised range")):
        ax.axvline(1.0, color="k", ls=":", lw=1.6)
        ax.text(1.0, ax.get_ylim()[0], "  $R = 2D^2/\\lambda$", rotation=90,
                va="bottom", fontsize=9)
        ax.set_xlabel("$R / R_{ff}$   (normalised range)")
        ax.set_ylabel(yl); ax.grid(alpha=0.3, which="both")
        ax.legend(fontsize=8.5); ax.set_title(ttl, fontweight="bold")
    fig.suptitle(f"Is $2D^2/\\lambda$ the right ruler?  Five airframes, {HEADLINE_BAND}, arm A2",
                 fontsize=12.5, fontweight="bold")
    fig.tight_layout()
    return _save(fig, "f4_collapse")


def f5_dsigma(doc):
    """F5 — Δσ_eq (구면 − 평면) vs 거리."""
    fig, ax = plt.subplots(figsize=(11, 5.4))
    cmap = plt.cm.tab10
    key = ("d_sigma_aspect_mean_db" if "d_sigma_aspect_mean_db" in doc["cells"][0]["rows"][0]
           else "d_sigma_db")
    for i, c in enumerate(doc["cells"]):
        R = [r["R_m"] for r in c["rows"]]
        d = [r[key] for r in c["rows"]]
        ls = "-" if c["band"] == HEADLINE_BAND else "--"
        ax.semilogx(R, d, ls, marker="o", ms=4, lw=1.7, color=cmap(i % 10),
                    label=f"{c['drone']} / {c['band'].split()[0]}")
        ax.plot([c["r_ff_m"]], [np.interp(c["r_ff_m"], R, d)], "k*", ms=11, zorder=5)
    ax.axhline(0, color="k", lw=1.0)
    ax.set_xlabel("Monostatic range R [m]")
    lab = ("azimuth-averaged (36 aspects)" if key.endswith("aspect_mean_db")
           else "SINGLE ASPECT az=0 — non-monotone through nulls, not citable")
    ax.set_ylabel("$\\Delta\\sigma_{eq}$ = spherical − plane [dB]")
    ax.grid(alpha=0.3, which="both"); ax.legend(fontsize=8, ncol=2)
    ax.set_title(f"Near-field level bias vanishes with range — {lab}\n"
                 "(black stars = each curve's own $2D^2/\\lambda$)", fontweight="bold")
    fig.tight_layout()
    return _save(fig, "f5_dsigma")


def f6_snr_wall(doc):
    """F6 — 거리별 샘플 SNR (팔 A1/A3 이 쓰는 값) 과 패턴 상관의 동시 표시."""
    c = _cell(doc, HEADLINE_DRONE, HEADLINE_BAND)
    R = np.array([r["R_m"] for r in c["rows"]])
    snr = np.array([r["snr_sample_sph_db"] for r in c["rows"]])
    fig, ax = plt.subplots(figsize=(11, 5.4))
    lb0 = doc["meta"]["link_budget"]["eirp_dbm"]
    ax.semilogx(R, snr, "o-", color="#00695c", lw=2, ms=6,
                label=f"per-sample SNR, EIRP {lb0:g} dBm (used by A1/A3)")
    # ⚠ SNR 벽은 **선언 EIRP 의 함수**다. 실제 셀룰러 조명원(63 dBm)이면 통째로 이동한다.
    ax.semilogx(R, snr + (63.0 - lb0), "^--", color="#8d6e63", lw=1.8, ms=6,
                label="same at EIRP 63 dBm (macro cell) — wall moves out $10^{51/40}$ = 18.8×")
    # 블레이드선(AC)의 실효 SNR = 전체 SNR − DC/AC 비
    dcac = float(c["rows"][0]["arms"]["A0_reference"]["dc_ac_db"])
    ax.semilogx(R, snr - dcac, ":", color="#00695c", lw=1.6,
                label=f"AC (blade-line) SNR = total − DC/AC ({dcac:.1f} dB)")
    ax.axhline(0, color="#c62828", ls="--", lw=1.3)
    ax.text(R[0], 1.0, " SNR = 0 dB", color="#c62828", fontsize=9.5)
    ax.set_xlabel("Monostatic range R [m]"); ax.set_ylabel("Per-sample SNR [dB]")
    ax.grid(alpha=0.3, which="both")
    ax2 = ax.twinx()
    for arm in ("A1_snr_only", "A3_both"):
        y = [r["arms"][arm]["ac_corr_vs_ref"] for r in c["rows"]]
        ax2.semilogx(R, y, "s--", color=ARM_COLOR[arm], lw=1.6, ms=5, alpha=0.85,
                     label=ARM_LABEL[arm].split("\n")[0])
    ax2.set_ylabel("AC correlation vs reference"); ax2.set_ylim(-0.02, 1.05)
    ax.axvline(c["r_ff_m"], color="k", ls=":", lw=1.5)
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=9, loc="upper right")
    lb = doc["meta"]["link_budget"]
    ax.set_title(f"Visibility wall vs pattern wall   ({HEADLINE_DRONE}, {HEADLINE_BAND})\n"
                 f"declared link budget: EIRP {lb['eirp_dbm']:g} dBm, "
                 f"$G_{{rx}}$ {lb['rx_gain_dbi']:g} dBi, NF {lb['noise_figure_db']:g} dB, "
                 f"B {lb['noise_bw_hz']/1e6:g} MHz", fontweight="bold")
    fig.tight_layout()
    return _save(fig, "f6_snr_wall")


def f7_farfield_map(doc):
    """F7 — 드론 × 밴드 원거리장 경계, 1/5/10/20 m 를 겹쳐 표시."""
    from radar_scene import target_extent
    bands = doc["meta"]["bands"]
    drones = [c["drone"] for c in doc["cells"] if c["band"] == HEADLINE_BAND]
    M = np.array([[nf.farfield_range_m(target_extent(d), f) for f in bands.values()]
                  for d in drones])
    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    im = ax.imshow(M, cmap="YlOrRd", aspect="auto")
    ax.set_xticks(range(len(bands)), [b.replace(" ", "\n") for b in bands], fontsize=9)
    ax.set_yticks(range(len(drones)), drones, fontsize=10)
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            n_near = sum(1 for R in SHOW_RANGES if R < M[i, j])
            ax.text(j, i, f"{M[i, j]:.1f} m\n{n_near}/4 near", ha="center", va="center",
                    fontsize=9.5, fontweight="bold",
                    color="white" if M[i, j] > M.max() * 0.55 else "black")
    fig.colorbar(im, ax=ax, label="far-field boundary $2D^2/\\lambda$ [m]")
    ax.set_title("How many of the four test ranges (1 / 5 / 10 / 20 m) are in the NEAR field\n"
                 "$D$ = mesh bounding-box max horizontal extent (props included)",
                 fontweight="bold")
    fig.tight_layout()
    return _save(fig, "f7_farfield_map")


def f8_prf_feasibility(doc):
    """F8 — 상시 기준신호 반복률로 f_tip 을 접힘 없이 볼 수 있는가."""
    cells = [c for c in doc["cells"] if c["band"] == HEADLINE_BAND]
    drones = [c["drone"] for c in cells]
    need = np.array([2.0 * c["f_tip_hz"] for c in cells])
    modes = list(cells[0]["prf_feasibility"])
    fig, ax = plt.subplots(figsize=(11, 5.4))
    x = np.arange(len(drones))
    ax.bar(x, need, color="#37474f", label="required PRF = $2 f_{tip}$")
    cols = ["#1565c0", "#2e7d32", "#c62828", "#ef6c00"]
    for i, m in enumerate(modes):
        p = cells[0]["prf_feasibility"][m]["mode_prf_hz"]
        ax.axhline(p, color=cols[i % 4], ls="--", lw=1.6)
        ax.text(len(drones) - 0.4, p * 1.04, f"{m}  ({p:g} Hz)", color=cols[i % 4],
                fontsize=9, ha="right")
    ax.set_yscale("log")
    ax.set_xticks(x, drones, fontsize=10)
    ax.set_ylabel("Slow-time rate [Hz]")
    ax.grid(alpha=0.3, axis="y", which="both")
    ax.legend(fontsize=9, loc="upper left")
    ax.set_title("Can an always-on communication pilot sample the blade line at all?\n"
                 f"({HEADLINE_BAND}; the experiment itself runs at "
                 f"{doc['meta']['slow_time']['prf_hz']:g} Hz = full-waveform capture)",
                 fontweight="bold")
    fig.tight_layout()
    return _save(fig, "f8_prf_feasibility")


def main():
    doc = _load()
    print(f"md_range_sweep: {len(doc['cells'])} cells, "
          f"{len(doc['meta']['ranges_m'])} ranges")
    for fn in (f1_spectrogram_grid, f2_attribution, f3_doppler_marginal, f4_collapse,
               f5_dsigma, f6_snr_wall, f7_farfield_map, f8_prf_feasibility):
        try:
            fn(doc)
        except Exception as exc:                          # noqa: BLE001
            print(f"  [skip] {fn.__name__}: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
