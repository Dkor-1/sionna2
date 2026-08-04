# -*- coding: utf-8 -*-
"""
phi_sweep_fig.py — outputs/phi_sweep.json → outputs/figs/phi_sweep.png (그림 텍스트는 전부 영어)

패널 구성(2×3) — "φ=90° 가 특이 방위인가" 를 한 장에서 판정할 수 있게 배치한다.
  (a) 모노 vs 바이 **확산항 차** — 게이트 전/후를 같은 축에 (23.17 dB 헤드라인의 정체)
  (b) R90(φ) — σ 격자 조회(정본 경로)
  (c) R90(φ) — σ 고정 통제군 (b 와 **같은 y 범위**: 평평함이 눈에 보이게)
  (d) R90(φ) — 헤딩 ψ 평균 (자세를 지운 값)
  (e) 고정거리 d=1 km 의 닫힌형 SNR(φ)
  (f) 신뢰도 — σ 격자 밖 앙각 비율 · 유효게이트 통과 비율

색: dataviz 기본 검증 팔레트의 고정 슬롯 순서(1 blue · 2 orange · 3 aqua)를 파형에 고정 배정한다.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                        # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
JSON_PATH = os.path.join(ROOT, "outputs", "phi_sweep.json")
FIG_PATH = os.path.join(ROOT, "outputs", "figs", "phi_sweep.png")

# 고정 슬롯 순서 — 파형 정체성에 묶는다(순위로 재배정 금지)
C = {"W1": "#2a78d6", "L1": "#eb6834", "G1": "#1baf7a"}
LABEL = {"W1": "WiFi 5.2 GHz (VHT-LTF)", "L1": "LTE 1.8 GHz (CRS)", "G1": "5G NR 3.5 GHz (SSB)"}
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#8a8984"
GEO1, GEO2, GEO3 = "#4a3aa7", "#eda100", "#e87ba4"
PHI_MARK = "#b0102a"
MODES = ("W1", "L1", "G1")


def _ax_style(ax, xlabel="Scene azimuth phi [deg]"):
    ax.set_xlim(0, 355)
    ax.set_xticks([0, 45, 90, 135, 180, 225, 270, 315])
    ax.grid(True, color="#e6e5e1", lw=0.7, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#cfcec9")
    ax.tick_params(colors=INK2, labelsize=8, length=3)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=8.5, color=INK2)


def _title(ax, title, sub=None):
    """제목 + 회색 부제 — 한 덩어리로 올려 축 위 겹침을 막는다."""
    ax.set_title(title, fontsize=10.5, color=INK, loc="left", pad=17)
    if sub:
        ax.annotate(sub, xy=(0.0, 1.0), xycoords="axes fraction", xytext=(0, 5),
                    textcoords="offset points", fontsize=7.8, color=MUTED, va="bottom")


def _mark90(ax, text=None):
    ax.axvline(90.0, color=PHI_MARK, lw=1.4, ls=(0, (4, 2)), zorder=3)
    if text:
        ax.annotate(text, xy=(90, 1.0), xycoords=("data", "axes fraction"),
                    xytext=(-5, -10), textcoords="offset points",
                    fontsize=7.8, color=PHI_MARK, ha="right", va="top")


def main():
    with open(JSON_PATH) as f:
        D = json.load(f)
    drone = D["aspect_averaged"]["drone"]
    phi = np.array(D["geometry"]["axis"]["phi_deg"], float)

    fig, axes = plt.subplots(2, 3, figsize=(15.2, 8.4))
    fig.patch.set_facecolor("#fcfcfb")
    for ax in axes.ravel():
        ax.set_facecolor("#fcfcfb")

    # ── (a) 확산항 차 ────────────────────────────────────────────────────────
    ax = axes[0, 0]
    g = D["geometry"]["axis"]
    y_un = np.abs(np.array(g["n2_absmax_db"], float))
    y_gt = np.abs(np.array([np.nan if v is None else v for v in g["n2_gated_absmax_db"]], float))
    y_md = np.abs(np.array(g["n2_median_db"], float))
    ax.plot(phi, y_un, color=GEO1, lw=3.4, alpha=0.5, zorder=4,
            label="max over full d-grid (as published)")
    ax.plot(phi, y_gt, color=GEO2, lw=1.8, ls=(0, (5, 2)), zorder=5,
            label="max over VALID cells only (beta<=90, far field)")
    ax.plot(phi, y_md, color=GEO3, lw=2.0, zorder=5, label="median over full d-grid")
    ax.set_yscale("log")
    s = D["geometry"]["summary"]
    ax.plot([90], [abs(s["n2_absmax_at_phi90_db"])], "o", ms=7, mfc="#ffffff",
            mec=GEO1, mew=1.8, zorder=6)
    ax.annotate(f"{abs(s['n2_absmax_at_phi90_db']):.3f} dB", xy=(90, abs(s["n2_absmax_at_phi90_db"])),
                xytext=(8, -2), textcoords="offset points", fontsize=8, color=INK)
    imax = int(np.nanargmax(y_un))
    ax.annotate(f"{y_un[imax]:.1f} dB", xy=(phi[imax], y_un[imax]), xytext=(0, 8),
                textcoords="offset points", fontsize=8.5, color=INK, ha="center")
    _ax_style(ax)
    _mark90(ax, "phi = 90 deg\npublished cut")
    ax.set_ylabel("|monostatic - bistatic| spread term [dB]", fontsize=8.5, color=INK2)
    _title(ax, "(a)  Geometry term: how far apart are the two geometries?",
           "monostatic node at the receiver; delta = 20 log10(R2/R1)")
    ax.set_ylim(2e-3, 90)
    ax.legend(fontsize=7.0, loc="lower center", ncol=1, labelcolor=INK2, frameon=True,
              facecolor="#fcfcfb", edgecolor="#dedcd6", framealpha=0.95)

    # ── (b)(c)(d) R90 세 팔 — 같은 y 범위 ───────────────────────────────────
    def _r90(ax, axis_of_mode, title, sub):
        allv = []
        i90 = int(np.argmin(np.abs(phi - 90)))
        for m in MODES:
            y = np.array([np.nan if v is None else v for v in axis_of_mode[m]], float)
            allv.append(y)
            ax.plot(phi, y, color=C[m], lw=2.0, zorder=5, label=LABEL[m])
            ax.plot([90], [y[i90]], "o", ms=6, mfc="#ffffff", mec=C[m], mew=1.6, zorder=6)
        stacked = np.vstack(allv)
        span = np.nanmax(100.0 * (np.nanmax(stacked, axis=1) - np.nanmin(stacked, axis=1))
                         / stacked[:, i90])
        _ax_style(ax)
        _mark90(ax)
        ax.set_yscale("log")
        ax.set_ylabel("R90 detection range [m]", fontsize=8.5, color=INK2)
        _title(ax, title, sub)
        ax.annotate(f"worst-case swing over the full circle: {span:.2f} %",
                    xy=(0.5, 0.965), xycoords="axes fraction", ha="center", va="top",
                    fontsize=8.2, color=INK,
                    bbox=dict(boxstyle="round,pad=0.32", fc="#ffffff", ec="#dedcd6", lw=0.8))
        return np.concatenate(allv)

    sg = D["sigma_grid"][drone]["by_mode"]
    v1 = _r90(axes[0, 1], {m: sg[m]["axis"]["R90_m"] for m in MODES},
              "(b)  Detection range, sigma from the RCS grid",
              f"{drone}, single aspect (heading psi = 0) - geometry AND aspect move together")
    sf = D["sigma_fixed"]["by_mode"]
    v2 = _r90(axes[0, 2], {m: sf[m]["axis"]["R90_m"] for m in MODES},
              "(c)  CONTROL: sigma held constant at 0.01 m^2",
              "pure geometry - flat means geometry does not move the link budget")
    ap = D["aspect_averaged"]["by_mode"]
    v3 = _r90(axes[1, 0], {m: ap[m]["axis"]["R90_mean_over_psi_m"] for m in MODES},
              "(d)  Detection range, averaged over all 72 headings",
              f"{drone}, sigma from the grid but aspect averaged out")
    lo = np.nanmin(np.concatenate([v1, v2, v3])) * 0.82
    hi = np.nanmax(np.concatenate([v1, v2, v3])) * 1.35
    for ax in (axes[0, 1], axes[0, 2], axes[1, 0]):
        ax.set_ylim(lo, hi)
    axes[0, 1].legend(fontsize=7.4, loc="lower left", labelcolor=INK2, frameon=True,
                      facecolor="#fcfcfb", edgecolor="#dedcd6", framealpha=0.95)

    # ── (e) 고정거리 SNR ────────────────────────────────────────────────────
    ax = axes[1, 1]
    sn = D["snr_at_1km"][drone]
    for m in MODES:
        y = np.array(sn[m]["snr_db"], float)
        ax.plot(phi, y, color=C[m], lw=2.0, zorder=5, label=LABEL[m])
    snf = D["snr_at_1km"]["_sigma_fixed"]
    for m in MODES:
        ax.plot(phi, np.array(snf[m]["snr_db"], float), color=C[m], lw=1.2, ls=(0, (3, 2)),
                alpha=0.75, zorder=4)
    _ax_style(ax)
    _mark90(ax)
    ax.set_ylim(18, 48)
    ax.set_ylabel("closed-form RD SNR at d = 1 km [dB]", fontsize=8.5, color=INK2)
    _title(ax, "(e)  Same sky position, all three illuminators",
           "solid = sigma from the grid   |   dashed = constant-sigma control")
    ax.legend(fontsize=7.4, loc="lower left", labelcolor=INK2, ncol=3,
              columnspacing=1.0, handlelength=1.4, frameon=True,
              facecolor="#fcfcfb", edgecolor="#dedcd6", framealpha=0.95)

    # ── (f) 신뢰도 ──────────────────────────────────────────────────────────
    ax = axes[1, 2]
    oor = 100.0 * np.array(g["frac_el_outside_sigma_grid"], float)
    val = 100.0 * np.array(g["valid_frac"], float)
    ax.plot(phi, oor, color=GEO2, lw=2.0, zorder=5,
            label="d-cells whose look elevation is OUTSIDE the sigma grid")
    ax.plot(phi, val, color=GEO1, lw=2.0, zorder=5,
            label="d-cells passing the validity gate (beta, far field)")
    ax.fill_between(phi, 0, oor, color=GEO2, alpha=0.12, zorder=2)
    _ax_style(ax)
    _mark90(ax)
    ax.set_ylim(0, 108)
    ax.set_ylabel("share of the 240-point d-grid [%]", fontsize=8.5, color=INK2)
    _title(ax, "(f)  Where the sigma grid and the gates run out",
           "the sigma-grid arm is clamped wherever the orange curve is high")
    ax.legend(fontsize=7.2, loc="center left", labelcolor=INK2, frameon=True,
              facecolor="#fcfcfb", edgecolor="#dedcd6", framealpha=0.95)

    meta = D["meta"]
    fig.suptitle("Scene azimuth phi sweep - is the published detection result a phi = 90 deg artefact?",
                 fontsize=14, color=INK, x=0.007, ha="left", y=0.988)
    fig.text(0.007, 0.958,
             "phi = horizontal azimuth of the target about the baseline midpoint; 0 deg points "
             "illuminator -> receiver, 90 deg is the perpendicular bisector, where R1 = R2 holds by "
             "construction.\n"
             f"Passive bistatic, baseline L = {meta['L_m']:.0f} m, altitude {meta['alt_m']:.0f} m, "
             f"CPI {meta['T_cpi_s']} s, single receiver, EIRP {meta['link_budget']['eirp_dbm']:.0f} dBm "
             "(declared). Closed form throughout - no GPU, the RCS grid is re-read and never re-run.",
             fontsize=8.6, color=INK2, ha="left", va="top", linespacing=1.5)
    fig.text(0.007, 0.012,
             "Data: outputs/phi_sweep.json   |   sigma grid: outputs/report13_sigma_grid.json "
             f"(generated {meta.get('sigma_file_generated')}, PRE-DATES the 2026-07-31 mesh rebuild - "
             "absolute levels are stale, read phi-relative only)   |   "
             f"Pd=0.9 threshold {meta['snr90_db']['W1']:.2f} dB reused from the published run.",
             fontsize=7.4, color=MUTED, ha="left", va="bottom")
    fig.tight_layout(rect=(0.0, 0.028, 1.0, 0.905))
    os.makedirs(os.path.dirname(FIG_PATH), exist_ok=True)
    fig.savefig(FIG_PATH, dpi=170, facecolor=fig.get_facecolor())
    print(f"[fig] → {FIG_PATH}")


if __name__ == "__main__":
    sys.exit(main())
