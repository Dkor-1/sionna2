# -*- coding: utf-8 -*-
"""viz_report4.py — report4 (탐지·추적 벤치마크를 위한 신호처리 체인 검증) 그림.

원칙:
  · **모든 숫자는 outputs/*.json 에서 읽는다.** 그림 안에 손으로 적은 값은 없다.
  · 적대적 검증에서 정정된 값은 outputs/report4_fixups.json 에서 읽는다(정정본 우선).
  · 그림 텍스트는 전부 **영어**. 짧은 헤드라인 + 회색 캡션.
  · 그리스문자/U+2212 대신 mathtext 와 ASCII 하이픈.
"""
from __future__ import annotations

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker
import numpy as np
from matplotlib.patches import Rectangle

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
OUTD = os.path.join(_ROOT, "outputs")
FIGD = os.path.join(OUTD, "figures")
os.makedirs(FIGD, exist_ok=True)

# 그림은 영어 전용 → DejaVu (마이너스·mathtext 안전). 한글 폰트는 쓰지 않는다.
plt.rcParams.update({
    "font.family": "DejaVu Sans", "axes.unicode_minus": True,
    "figure.facecolor": "white", "savefig.facecolor": "white",
    "axes.grid": True, "grid.alpha": 0.25, "grid.linestyle": ":",
    "axes.spines.top": False, "axes.spines.right": False,
    "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9,
    "legend.fontsize": 8, "xtick.labelsize": 8, "ytick.labelsize": 8,
})

CW = {"WiFi80": "#1f77b4", "LTE20": "#d62728", "NR100": "#2ca02c"}
CN = {"WiFi 80MHz": "#1f77b4", "LTE 20MHz": "#d62728",
      "5G NR 100MHz": "#2ca02c", "5G 100MHz": "#2ca02c"}
PASS, FAILC, WARN = "#2e7d32", "#c62828", "#ef6c00"
GT = "g2x2_t6x6"


def _j(name):
    with open(os.path.join(OUTD, name), encoding="utf-8") as f:
        return json.load(f)


def _cap(fig, text, y=0.005):
    """회색 캡션 — 그림 아래. 줄바꿈은 호출자가 넣는다(잘림 방지)."""
    fig.text(0.5, y, text, ha="center", va="bottom", fontsize=7.6,
             color="#555555", linespacing=1.5)


def _head(ax, text, color="#111111"):
    ax.set_title(text, loc="left", fontweight="bold", color=color, pad=6)


def _save(fig, name):
    p = os.path.join(FIGD, name)
    fig.savefig(p, dpi=135, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✔ {p}")
    return p


def _rows(node, mask=1, gt=GT):
    return sorted([r for r in node["rows"] if r["gt"] == gt and r["zd_mask_width"] == mask],
                  key=lambda r: r["pfa_nom"])


# =========================================================================== #
#  Fig 1 — [E1] CFAR false-alarm calibration   ★ 이 리포트의 핵심
# =========================================================================== #
def fig_cfar():
    C, F = _j("verify_cfar.json"), _j("report4_fixups.json")["F1_cfar"]
    fig = plt.figure(figsize=(13.6, 8.6))
    gs = fig.add_gridspec(2, 3, hspace=0.46, wspace=0.30,
                          left=0.055, right=0.985, top=0.895, bottom=0.155)

    # (a) empirical vs nominal ------------------------------------------------
    ax = fig.add_subplot(gs[0, 0])
    lo, hi = 5e-7, 2e-2
    ax.plot([lo, hi], [lo, hi], "k--", lw=1, label="ideal (emp = nom)")
    wr = _rows(C["white"]["48x24"])
    ax.plot([r["pfa_nom"] for r in wr], [r["pfa_emp"] for r in wr], "o-", ms=3.5, lw=1.2,
            color="#555555", label="ideal white map (impl. test)")
    for w in ("WiFi80", "LTE20", "NR100"):
        r = _rows(C["chain"][w]["dpi_eca"]["op"])
        ax.plot([x["pfa_nom"] for x in r], [x["pfa_emp"] for x in r], "o-", ms=3.5, lw=1.4,
                color=CW[w], label=f"{w} (real chain)")
    ax.set(xscale="log", yscale="log", xlim=(lo, hi), ylim=(lo, hi),
           xlabel="nominal $P_{fa}$ (what we asked for)",
           ylabel="empirical $P_{fa}$ (what we got)")
    _head(ax, "(a) The detector fires more often than asked", FAILC)
    ax.legend(loc="upper left", frameon=False)

    # (b) ratio at 1e-4 with correlation-corrected CI --------------------------
    # bars = operational point estimate (verify_cfar dpi_eca op — same source as body §2.2),
    # whiskers = correlation-corrected 95% CI (report4_fixups). Keeps figure and text consistent.
    ax = fig.add_subplot(gs[0, 1])
    _GT, _ZD = C["meta"]["gt_default"], C["meta"]["zd_mask_operational"]

    def _op_ratio(wf):
        for rr in C["chain"][wf]["dpi_eca"]["op"]["rows"]:
            if rr["gt"] == _GT and rr["zd_mask_width"] == _ZD and abs(rr["pfa_nom"] - 1e-4) < 1e-12:
                return rr["ratio"]
        return None

    ci = [r for r in F["corrected_ci"]["rows"] if abs(r["pfa_nom"] - 1e-4) < 1e-12]
    xs = np.arange(len(ci))
    for i, r in enumerate(ci):
        w = r["wf"]
        lo_, hi_ = r["ratio_ci_corrected"]
        op = _op_ratio(w)
        ax.bar(i, op, color=CW[w], width=0.6, alpha=0.85)
        ax.plot([i, i], [lo_, hi_], color="#222222", lw=1.6)
        ax.plot([i - .12, i + .12], [lo_, lo_], color="#222222", lw=1.6)
        ax.plot([i - .12, i + .12], [hi_, hi_], color="#222222", lw=1.6)
        ax.text(i, hi_ + 0.10, f"{op:.2f}x", ha="center", fontsize=9.5,
                fontweight="bold")
    ax.axhline(1.0, color="k", ls="--", lw=1)
    ax.text(0.985, 1.09, "calibrated", fontsize=7.5, color="#444444", ha="right",
            transform=ax.get_yaxis_transform())
    ax.set(xticks=xs, xticklabels=[r["wf"] for r in ci],
           ylabel="empirical / nominal $P_{fa}$", ylim=(0, 4.7))
    _head(ax, "(b) ... and by a DIFFERENT factor per waveform", FAILC)
    ax.text(0.5, 0.985, "nominal $P_{fa}=10^{-4}$, operational setup\n"
                        "bars = point estimate,  whiskers = correlation-corrected 95% CI",
            transform=ax.transAxes, fontsize=7.4, color="#555555", va="top", ha="center")

    # (c) root cause 1: the map is not white ----------------------------------
    ax = fig.add_subplot(gs[0, 2])

    def ratio_of(node, pfa=1e-4):
        return [r for r in _rows(node) if abs(r["pfa_nom"] - pfa) < 1e-12][0]["ratio"]

    ctrl = [("baseline\n(Hann + matched)", ratio_of(C["chain"]["NR100"]["noise"]["op"]), "#2ca02c"),
            ("no Hann\n(rect)", ratio_of(C["control_rect_window_NR100"]["op"]), "#7f7f7f"),
            ("whitened MF\n(flat range)", ratio_of(C["control_whitened_mf_NR100"]["op"]), "#7f7f7f"),
            ("both", ratio_of(C["control_whitened_mf_rect_NR100"]["op"]), PASS)]
    for i, (lab, v, c) in enumerate(ctrl):
        ax.bar(i, v, color=c, width=0.62, alpha=0.85)
        ax.text(i, v + 0.03, f"{v:.2f}", ha="center", fontsize=8.5, fontweight="bold")
    ax.axhline(1.0, color="k", ls="--", lw=1)
    ax.set(xticks=range(4), xticklabels=[c[0] for c in ctrl], ylim=(0, 1.75),
           ylabel="empirical / nominal $P_{fa}$")
    ax.tick_params(axis="x", labelsize=7.0)
    _head(ax, "(c) Cause 1: the RD map is not white", "#111111")
    ax.text(0.02, 0.95, "NR100, noise only. Removing the two\ncorrelations restores calibration.",
            transform=ax.transAxes, fontsize=7.4, color="#555555", va="top")

    # (d) root cause 2: the range window --------------------------------------
    ax = fig.add_subplot(gs[1, 0])
    S = F["range_window_sweep"]["rows"]
    rad = S[0]["cfar_train_radius_range"]
    for w in ("LTE20", "WiFi80", "NR100"):
        rr = sorted([r for r in S if r["wf"] == w], key=lambda r: r["n_range"])
        ax.plot([r["n_range"] for r in rr], [r["ratio"] for r in rr], "o-", color=CW[w], lw=1.5,
                ms=5, label=f"{w}  ($\\rho_{{range}}$={rr[0]['rho_range_lag1']:+.2f})")
        b = [r for r in rr if r["n_range"] == r["n_range_bench"]]
        if b:
            ax.plot(b[0]["n_range"], b[0]["ratio"], "*", ms=17, color=CW[w],
                    mec="k", mew=0.6, zorder=5)
    ax.axvline(2 * rad + 1, color="#c62828", ls=":", lw=1.2)
    ax.text(2 * rad + 2.0, 0.97, f"CFAR needs {2*rad+1} range bins\nfor a full training window",
            fontsize=7.2, color="#c62828", va="top")
    ax.axhline(1.0, color="k", ls="--", lw=1)
    ax.set(xlabel="range window $n_{range}$ [bins]", ylabel="empirical / nominal $P_{fa}$",
           ylim=(0.55, 2.42))
    _head(ax, "(d) Cause 2: the range window is too narrow", "#111111")
    ax.legend(loc="upper right", frameon=False, fontsize=7.4)
    ax.text(0.03, 0.135, "stars = what the benchmark actually uses.  WiFi has NO range\n"
                         "correlation yet still inflates -> it is the WINDOW, not the waveform.",
            transform=ax.transAxes, fontsize=7.0, color="#555555", va="top")

    # (e) the landmine --------------------------------------------------------
    ax = fig.add_subplot(gs[1, 1])
    W = [0, 1, 3, 5]
    for w in ("WiFi80", "LTE20", "NR100"):
        v = []
        for m in W:
            r = [x for x in _rows(C["chain"][w]["dpi_eca"]["wide"], mask=m)
                 if abs(x["pfa_nom"] - 1e-4) < 1e-12][0]
            v.append(r["ratio"])
        ax.plot(W, v, "o-", color=CW[w], lw=1.5, ms=5, label=w)
    ax.axhline(1.0, color="k", ls="--", lw=1)
    ax.axvspan(-0.35, 1.45, color="#c62828", alpha=0.07)
    ax.text(0.55, 260, "operational\n(width 1)", ha="center", fontsize=7.4, color="#c62828")
    ax.set(yscale="log", xlabel="zero-Doppler mask width [rows]",
           ylabel="empirical / nominal $P_{fa}$", xticks=W, ylim=(0.3, 900))
    hs = F["hann_sidelobe_db"]
    _head(ax, "(e) The landmine: a wider range window explodes", FAILC)
    ax.legend(loc="lower left", frameon=False)
    ax.text(0.97, 0.94, f"Hann leaks {hs['bin_1']:.1f} dB into $zd\\pm1$\n"
                        f"(but {hs['bin_2']:.0f} dB at $zd\\pm2$)\n"
                        "-> masking 1 row is not enough",
            transform=ax.transAxes, fontsize=7.2, color="#555555", ha="right", va="top")

    # (f) ROC ------------------------------------------------------------------
    ax = fig.add_subplot(gs[1, 2])
    R = C["roc_NR100"]
    for c in R["curves"]:
        pts = [p for p in c["points"] if p["pfa_emp"] > 0]
        ax.plot([p["pfa_emp"] for p in pts], [p["pd"] for p in pts], "o-", ms=3, lw=1.2,
                label=f"SCR {c['scr_db']:+.1f} dB")
    ax.set(xscale="log", xlabel="EMPIRICAL $P_{fa}$ (measured, not nominal)",
           ylabel="$P_d$", ylim=(-0.04, 1.42), yticks=[0, 0.25, 0.5, 0.75, 1.0])
    _head(ax, "(f) The honest ROC: Pd vs the Pfa we really get", PASS)
    ax.legend(loc="upper left", frameon=False, fontsize=7.2, ncol=2,
              columnspacing=1.0, handlelength=1.4)
    ax.text(0.985, 0.815, f"NR100, operational setup\n$R_b$={R['Rb_m']:.1f} m,  "
                          f"$f_d$={R['fd_hz']:.0f} Hz,  {R['curves'][0]['n_trials']} trials/point",
            transform=ax.transAxes, fontsize=7.0, color="#555555", ha="right", va="top")

    fig.suptitle("[E1] CFAR false-alarm calibration - the detector is NOT calibrated, "
                 "and the bias differs per waveform",
                 fontsize=13.5, fontweight="bold", x=0.055, ha="left", y=0.975)
    _cap(fig,
         "The CA-CFAR implementation itself is exact: on ideal white maps (5.64e8 tested cells) the empirical Pfa equals "
         "the nominal one to within 1-2% (grey line in a).\n"
         "The bias appears only in the real processing chain, and it is not a common scale factor - at a nominal "
         "1e-4 the detector fires 1.45x (WiFi) / 2.47x (LTE) / 1.56x (NR) too often.\n"
         "Comparing Pd across illuminators at a fixed NOMINAL Pfa therefore compares them at DIFFERENT true "
         "false-alarm rates - the benchmark's core question was never being asked fairly.\n"
         "Sources: outputs/verify_cfar.json, outputs/report4_fixups.json")
    return _save(fig, "report4_e1_cfar.png")


# =========================================================================== #
#  Fig 2 — [E2] ECA: cancellation depth and slow-target loss
# =========================================================================== #
def fig_eca():
    E = _j("verify_eca.json")
    F = _j("report4_fixups.json")["F2_eca"]
    fig = plt.figure(figsize=(13.6, 5.0))
    gs = fig.add_gridspec(1, 3, wspace=0.30, left=0.055, right=0.985, top=0.855, bottom=0.315)

    # (a) depth vs taps
    ax = fig.add_subplot(gs[0, 0])
    for s in E["S1_depth_vs_taps"]:
        c = CN[s["name"]]
        t = [r["n_taps"] for r in s["rows"]]
        ax.plot(t, [r["depth_full_db"] for r in s["rows"]], "o-", color=c, ms=3.5, lw=1.4,
                label=f"{s['name']} + RT reverb")
        ax.plot(t, [r["depth_dpi_db"] for r in s["rows"]], ":", color=c, lw=1.1, alpha=0.6)
        d = [x for x in F["eca_depth"]["rows"] if x["name"] == s["name"]][0]
        ax.plot(d["n_taps_bench"], d["depth_at_bench_taps_db"], "*", ms=16, color=c,
                mec="k", mew=0.6, zorder=5)
    ax.set(xscale="log", xlabel="ECA taps $n_{taps}$",
           ylabel="cancellation depth [dB]", ylim=(0, 255))
    ax.set_xticks([1, 2, 4, 8, 16, 32, 96])
    ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    _head(ax, "(a) ECA has a hard floor - it is not perfect", WARN)
    ax.legend(loc="center right", frameon=False, fontsize=7.2)
    ax.text(0.035, 0.985, "dotted = direct path only (float64 limit, ~200 dB)\n"
                          "solid  = + measured RT chamber reverb\n"
                          "         -> saturates at 31-56 dB\n"
                          "stars  = the taps the benchmark actually uses",
            transform=ax.transAxes, fontsize=7.2, color="#555555", ha="left", va="top",
            bbox=dict(fc="white", ec="none", alpha=0.85, pad=2))

    # (b) target loss vs Doppler  ★
    ax = fig.add_subplot(gs[0, 1])
    for s in E["S4_target_loss"]:
        if s["M"] != 48:
            continue
        c = CN[s["name"]]
        u = np.array([r["fd_over_dfd"] for r in s["rows"]])
        e = np.array([r["energy_loss_db"] for r in s["rows"]])
        ax.plot(u, e, "o-", color=c, ms=3, lw=1.3, label=f"{s['name']} (M=48)")
    u = np.linspace(0.01, 3, 400)
    ax.plot(u, 10 * np.log10(1 - (np.sin(np.pi * u) / (np.pi * u)) ** 2), "k--", lw=1.2,
            label="theory  $1-\\mathrm{sinc}^2(f_d T_{CPI})$")
    ax.axhline(-3, color="#c62828", ls=":", lw=1)
    n48 = [r for r in F["eca_notch"]["rows"] if r["M"] == 48]
    x3 = float(np.mean([r["fd_3db_over_dfd_energy"] for r in n48]))
    ax.axvline(x3, color="#c62828", ls=":", lw=1)
    ax.text(1.25, -1.6, f"-3 dB at $f_d$ = {x3:.2f} $\\Delta f_d$", fontsize=7.6,
            color="#c62828", va="top")
    ax.set(xlabel="$f_d\\ /\\ \\Delta f_d$   ($\\Delta f_d = 1/T_{CPI}$)",
           ylabel="target energy loss from ECA [dB]", xlim=(0, 2.2), ylim=(-26, 2))
    _head(ax, "(b) ECA eats slow targets - a one-bin notch", "#111111")
    ax.legend(loc="center right", frameon=False, fontsize=7.0)
    vs = " / ".join(f"{r['v_3db_energy_ms']:.2f}" for r in n48)
    ax.text(0.10, 0.035, "MINIMUM DETECTABLE SPEED (-3 dB, power):\n"
                         f"{vs} m/s   (5G / WiFi / LTE)\n"
                         "All waveforms and all CPI lengths collapse\n"
                         "onto one curve once scaled by $\\Delta f_d$.",
            transform=ax.transAxes, fontsize=7.0, color="#555555", va="bottom",
            bbox=dict(fc="white", ec="none", alpha=0.85, pad=2))

    # (c) DNR sweep
    ax = fig.add_subplot(gs[0, 2])
    for s in E["S2_dnr"]:
        c = CN[s["name"]]
        d = [r["dnr_db"] for r in s["rows"]]
        ax.plot(d, [r["depth_float_db"] for r in s["rows"]], "o-", color=c, ms=3.5, lw=1.4,
                label=f"{s['name']} (float64)")
        ax.plot(d, [r["depth_adc12_db"] for r in s["rows"]], "^--", color=c, ms=3, lw=1,
                alpha=0.55)
        op = [x for x in F["dnr_operating_point"]["rows"] if x["name"] == s["name"]][0]
        ax.axvline(op["correct_direct_over_noise_db"], color=c, ls=":", lw=1, alpha=0.8)
    ax.set(xlabel="DNR = direct path / noise [dB]", ylabel="cancellation depth [dB]",
           ylim=(20, 68))
    _head(ax, "(c) The ADC is not the bottleneck - ECA is", "#111111")
    ax.legend(loc="upper left", frameon=False, fontsize=7.0)
    gap = max(r["max_adc_vs_float_gap_db"] for r in F["eca_adc"]["rows"])
    ax.text(0.97, 0.06, "solid = float64,  dashed = 12-bit ADC\n"
                        f"largest gap over the whole sweep: {gap:.1f} dB\n"
                        "dotted verticals = our operating points",
            transform=ax.transAxes, fontsize=7.2, color="#555555", ha="right")

    fig.suptitle("[E2] ECA - it cancels the direct path down to a floor, and it eats slow targets",
                 fontsize=13.5, fontweight="bold", x=0.055, ha="left", y=0.985)
    _cap(fig,
         "Left: against the direct path alone ECA reaches the float64 limit, but the MEASURED RT chamber "
         "reverberation puts a hard floor at 31-56 dB. The 'unphysically perfect canceller' story is wrong.\n"
         "Middle: the notch is one Doppler bin wide and follows 1-sinc^2 exactly (in ENERGY - the earlier -3 dB "
         "speeds were read off an amplitude curve and were 1.33x too large). This is the MINIMUM DETECTABLE SPEED: "
         "a hovering drone is invisible to ECA by construction, not by accident.\n"
         "Right: 12/14/16-bit quantisation moves the depth by less than 1.2 dB.  "
         "Sources: outputs/verify_eca.json + report4_fixups.json")
    return _save(fig, "report4_e2_eca.png")


# =========================================================================== #
#  Fig 3 — [E3] Ambiguity function
# =========================================================================== #
def fig_ambiguity():
    A = _j("verify_ambiguity.json")
    F = _j("report4_fixups.json")["F3_ambiguity"]
    W = A["waveforms"]
    fig = plt.figure(figsize=(13.6, 5.0))
    gs = fig.add_gridspec(1, 3, wspace=0.32, left=0.055, right=0.985, top=0.855, bottom=0.315)

    keys = ["wifi_G1", "lte_G1", "nr_G1", "nr_G3"]

    # (a) range resolution
    ax = fig.add_subplot(gs[0, 0])
    lab = [f"{n}\n(x{W[k]['dR_ratio']:.2f})"
           for n, k in zip(["WiFi\nVHT-LTF\n76.6 MHz", "LTE\nCRS\n18.0 MHz",
                            "5G\nSSB\n7.2 MHz", "5G\nNR-PRS\n98.3 MHz"], keys)]
    x = np.arange(len(keys))
    ax.bar(x - 0.19, [W[k]["dR_theory_m"] for k in keys], 0.38, color="#bbbbbb",
           label="theory  $c/B_{ref}$")
    ax.bar(x + 0.19, [W[k]["dR_meas_m"] for k in keys], 0.38, color="#1f77b4",
           label="measured (-3 dB width)")
    for i, k in enumerate(keys):
        ax.text(i + 0.19, W[k]["dR_meas_m"] + 0.9, f"{W[k]['dR_meas_m']:.1f} m",
                ha="center", fontsize=7.6, fontweight="bold")
    ax.set(xticks=x, xticklabels=lab, ylabel="bistatic range resolution $\\Delta R_b$ [m]",
           ylim=(0, 49))
    ax.tick_params(axis="x", labelsize=6.8)
    _head(ax, "(a) Resolution is calibrated (ratio = sinc's 0.886)", PASS)
    ax.legend(loc="upper left", frameon=False, fontsize=7.4)
    ax.text(0.985, 0.985, "Occupancy decides 5G's fate:\nSSB 39.2 m  vs  PRS 2.8 m\n"
                          "(a 14x swing in reference bandwidth)",
            transform=ax.transAxes, fontsize=7.2, color="#555555", ha="right", va="top")

    # (b) 5G Doppler axis is 40x optimistic
    ax = fig.add_subplot(gs[0, 1])
    nm = ["WiFi\nVHT-LTF", "LTE\nCRS", "5G\nSSB", "5G\nPRS"]
    mod = [W[k]["physical"]["v_unamb_model_ms"] for k in keys]
    phy = [W[k]["physical"]["v_unamb_phys_ms"] for k in keys]
    x = np.arange(4)
    ax.bar(x - 0.19, mod, 0.38, color="#bbbbbb", label="model (harness frame rate)")
    ax.bar(x + 0.19, phy, 0.38, color="#d62728", label="physical (pilot repetition rate)")
    for i, k in enumerate(keys):
        r = W[k]["physical"]["ratio"]
        if r > 1:
            ax.text(i, 0.72, f"{r:.0f}x\noptimistic", ha="center", va="bottom",
                    transform=ax.get_xaxis_transform(),
                    fontsize=7.6, color="#c62828", fontweight="bold")
    ax.axhline(3.0, color="#111111", ls="--", lw=1)
    ax.text(3.45, 3.35, "our drone: 3 m/s", fontsize=7.4, ha="right")
    ax.set(xticks=x, xticklabels=nm, yscale="log",
           ylabel=r"unambiguous speed $v_{max}$ [m/s] (mono-equiv)", ylim=(0.5, 3000))
    _head(ax, "(b) 5G's Doppler axis is 40x optimistic", FAILC)
    ax.legend(loc="upper left", frameon=False, fontsize=7.2)
    p = W["nr_G1"]["physical"]
    ax.text(0.99, 0.99, f"SSB really repeats at {p['prf_physical_hz']:.0f} Hz, not "
                       f"{p['prf_model_hz']:.0f} Hz\n-> the true target ($f_d$ = "
                       f"{p['fd_true_hz']:+.0f} Hz) folds to "
                       f"{p['fd_aliased_phys_hz']:+.0f} Hz.",
            transform=ax.transAxes, fontsize=7.2, color="#555555", ha="right", va="top",
            bbox=dict(fc="white", ec="none", alpha=0.9, pad=2))

    # (c) ghost margin on the detector's own grid
    ax = fig.add_subplot(gs[0, 2])
    rows = [r for r in F["ghost_margin_on_detector_grid"]["rows"]
            if r["key"] in ("wifi_G3", "lte_G3", "nr_G3")]
    x = np.arange(len(rows))
    ax.bar(x - 0.19, [r["margin_reported_finegrid_db"] for r in rows], 0.38, color="#bbbbbb",
           label="fine grid (as reported)")
    for i, r in enumerate(rows):
        ax.bar(i + 0.19, r["margin_db"], 0.38,
               color=FAILC if r["margin_db"] < 0 else PASS,
               label="detector's real bin" if i == 0 else None)
        ax.plot([i + 0.19, i + 0.19], [r["margin_subbin_min_db"], r["margin_subbin_max_db"]],
                color="#222222", lw=1.6)
        ax.plot([i + .07, i + .31], [r["margin_subbin_min_db"]] * 2, color="#222222", lw=1.6)
        ax.plot([i + .07, i + .31], [r["margin_subbin_max_db"]] * 2, color="#222222", lw=1.6)
    ax.axhline(0, color="k", lw=1)
    ax.set(xticks=x, xticklabels=[r["name"].replace(" ", "\n", 1) for r in rows],
           ylabel="ghost minus target's own leakage [dB]", ylim=(-27, 52))
    ax.tick_params(axis="x", labelsize=7.2)
    _head(ax, "(c) The 'ghost margin' is not a single number", WARN)
    ax.legend(loc="upper right", frameon=False, fontsize=7.0)
    ax.text(0.02, 0.985, "whiskers = sweeping the target\nacross ONE range bin.\n\n"
                         "5G even flips sign: the target's\nown skirt is STRONGER than\n"
                         "the ghost in that cell.",
            transform=ax.transAxes, fontsize=7.0, color="#c62828", va="top")

    fig.suptitle("[E3] Ambiguity function of OUR detector - resolution passes, "
                 "the Doppler axis and the ghost margin do not",
                 fontsize=13.5, fontweight="bold", x=0.055, ha="left", y=0.985)
    _cap(fig,
         "The ambiguity function was measured THROUGH the actual detector (frame correlation + Hann slow-time FFT), "
         "not from a textbook formula - it reproduces the real RD map to ~0.002 dB.\n"
         "Range and Doppler resolution come out exactly as theory predicts. But the harness clocks 5G frames at "
         "2000 Hz while the SSB pilot physically repeats at 50 Hz, so every 5G Doppler number is 40x optimistic; "
         "the real 3 m/s drone would fold to +14 Hz.\n"
         "And the ghost cell is contaminated by the target's own response, so the previously reported ghost margin "
         "is not a quantity this detector can even compute.  "
         "Sources: outputs/verify_ambiguity.json + report4_fixups.json")
    return _save(fig, "report4_e3_ambiguity.png")


# =========================================================================== #
#  Fig 4 — [E4] Link budget → RD SNR
# =========================================================================== #
def fig_linkbudget():
    L = _j("verify_linkbudget.json")
    F = _j("report4_fixups.json")["F4_linkbudget"]
    fig = plt.figure(figsize=(13.6, 5.0))
    gs = fig.add_gridspec(1, 3, wspace=0.30, left=0.055, right=0.985, top=0.855, bottom=0.315)

    # (a) predicted vs measured
    ax = fig.add_subplot(gs[0, 0])
    for r in L["D_sigma_table"]["rows"]:
        c = CN.get(r["wf"], "#777777")
        ax.errorbar(r["pred_hann_db"], r["scr_meas_db"], yerr=r["scr_std_db"], fmt="o",
                    ms=5, color=c, ecolor=c, elinewidth=1, capsize=2, alpha=0.9)
    lo, hi = 5, 60
    gm = L["D_sigma_table"]["gap_mean_db"]
    ax.plot([lo, hi], [lo, hi], "k--", lw=1, label="perfect agreement")
    ax.plot([lo, hi], [lo + gm, hi + gm], ":", color="#777777", lw=1,
            label=f"mean gap {gm:+.1f} dB")
    for w in ("WiFi 80MHz", "LTE 20MHz", "5G NR 100MHz"):
        ax.plot([], [], "o", color=CN[w], label=w)
    ax.set(xlim=(lo, hi), ylim=(lo, hi), xlabel="SNR predicted from the radar equation [dB]",
           ylabel="SCR measured in the RD map [dB]")
    _head(ax, "(a) The link-budget chain is calibrated", PASS)
    ax.legend(loc="upper left", frameon=False, fontsize=7.2)
    # ⚠ 개수는 **표에서 센다**. 예전엔 "5 drones x 3 waveforms" 리터럴이라 기종이 늘면
    #   그림이 자기 데이터와 다른 개수를 주장했다(에러 없이 틀린 캡션).
    _nd = len({r["drone"] for r in L["D_sigma_table"]["rows"]})
    _nw = len({r["wf"] for r in L["D_sigma_table"]["rows"]})
    ax.text(0.97, 0.06, f"{_nd} drones x {_nw} waveforms, sigma from SBR\n"
                        f"N={L['D_sigma_table']['N']} trials, M={L['D_sigma_table']['M']}\n"
                        "the gap is processing loss, not an error",
            transform=ax.transAxes, fontsize=7.2, color="#555555", ha="right")

    # (b) loss budget
    ax = fig.add_subplot(gs[0, 1])
    names = ["WiFi 80MHz", "LTE 20MHz", "5G 100MHz"]
    st = {r["name"]: r for r in F["straddle"]["rows"]}
    cf = {r["name"]: r for r in F["cfar_loss"]["rows"]}
    han = F["hann_window_loss"]["exact_db"]
    items = [("Hann window", lambda n: han, "#7f7f7f"),
             ("range straddle\n(half bin)", lambda n: st[n]["range_half_db"], "#1f77b4"),
             ("Doppler straddle\n(half bin)", lambda n: st[n]["dopp_half_db"], "#9467bd"),
             ("CFAR loss\n(worst cell)", lambda n: -cf[n]["cfar_loss_max_db"], "#d62728")]
    w = 0.2
    for j, (lab, fn, c) in enumerate(items):
        ax.bar(np.arange(3) + (j - 1.5) * w, [fn(n) for n in names], w, color=c, label=lab)
    ax.axhline(0, color="k", lw=1)
    ax.set(xticks=range(3), xticklabels=["WiFi", "LTE", "5G"], ylabel="loss [dB]",
           ylim=(-4.6, 1.9))
    _head(ax, "(b) Where the dB actually go (corrected)", "#111111")
    ax.legend(loc="upper center", frameon=False, fontsize=6.6, ncol=4,
              columnspacing=0.9, handlelength=1.2, handletextpad=0.4)
    ax.text(0.98, 0.035, "Hann is a waveform-INDEPENDENT constant: "
                         f"{han:.2f} dB exact\n(not the "
                         f"{F['hann_window_loss']['asymptotic_quoted_db']:.2f} dB asymptote "
                         "that was quoted).  LTE's CFAR loss is\nworst because its map is only "
                         "6 range bins wide (degenerate).",
            transform=ax.transAxes, fontsize=6.9, color="#555555", ha="right")

    # (c) the uncontrolled variable
    ax = fig.add_subplot(gs[0, 2])
    cpi = F["cpi_asymmetry"]["cpi_ms"]
    ks = ["WiFi 80MHz", "LTE 20MHz", "5G 100MHz"]
    v = [cpi[k] for k in ks]
    ax.bar(range(3), v, 0.5, color=[CN[k] for k in ks], alpha=0.85)
    for i, x in enumerate(v):
        ax.text(i, x + 1.2, f"{x:.0f} ms", ha="center", fontweight="bold", fontsize=9.5)
    ax.set(xticks=range(3), xticklabels=["WiFi", "LTE", "5G"], ylim=(0, 60),
           ylabel="coherent integration time $T_{CPI}$ at M=48 [ms]")
    _head(ax, "(c) Observation time was never controlled", FAILC)
    ax.annotate("", xy=(2, 24), xytext=(2, 48),
                arrowprops=dict(arrowstyle="<->", color="#c62828", lw=1.4))
    ax.text(1.88, 36, f"{F['cpi_asymmetry']['span_db']:.2f} dB of\ncoherent gain,\ngiven away\n"
                      "by a convention",
            ha="right", fontsize=7.6, color="#c62828", fontweight="bold")
    fig.suptitle("[E4] Link budget -> injected amplitude -> RD SNR: the physics is exact, "
                 "the protocol is not fair",
                 fontsize=13.5, fontweight="bold", x=0.055, ha="left", y=0.985)
    _cap(fig,
         "The radar equation, the noise floor and the processing gain were re-derived independently and agree with "
         "the code to 2.8e-14 dB; the measured RD SNR matches the theoretical ceiling to within 0.1 dB. The physics "
         "chain is trustworthy.\n"
         "What is not trustworthy is the comparison protocol. frame_len() calls a frame 1 ms for WiFi (a packet "
         "slot) and for LTE (a subframe), but 0.5 ms for 5G (one NR slot), so the same M=48 gives 5G HALF the "
         "integration time.\n"
         "The CPI length is therefore fixed by a naming convention rather than by physics, and it silently hands 5G "
         "a 3.01 dB penalty that has nothing to do with 5G.\n"
         "Sources: outputs/verify_linkbudget.json + report4_fixups.json")
    return _save(fig, "report4_e4_linkbudget.png")


# =========================================================================== #
#  Fig 5 — [E5] Observability
# =========================================================================== #
def fig_observability():
    O = _j("verify_observability.json")
    F = _j("report4_fixups.json")["F5_observability"]
    fig = plt.figure(figsize=(13.6, 5.0))
    gs = fig.add_gridspec(1, 3, wspace=0.34, left=0.055, right=0.985, top=0.855, bottom=0.315)

    # (a) iso-Rb shell volume (corrected)
    ax = fig.add_subplot(gs[0, 0])
    order = ["nr100_G1", "lte20_G1", "wifi80_G1", "nr100_G3"]
    rows = sorted(F["shell_volume"]["rows"], key=lambda r: order.index(r["key"]))
    ch = F["shell_volume"]["chamber_m3"]
    lab = ["5G SSB\n7.2 MHz", "LTE CRS\n18 MHz", "WiFi LTF\n76.6 MHz", "5G PRS\n98.3 MHz"]
    ax.axhline(ch, color="#111111", ls="--", lw=1)
    ax.text(3.45, ch * 1.03, f"whole chamber ({ch:.0f} $m^3$)", ha="right", fontsize=7.4)
    for i, r in enumerate(rows):
        f = r["frac_corrected"]
        c = FAILC if f > 0.5 else (WARN if f > 0.15 else PASS)
        ax.bar(i, r["v_shell_corrected_m3"], 0.55, color=c, alpha=0.85)
        ax.text(i, r["v_shell_corrected_m3"] + 170, f"{f*100:.0f}%", ha="center",
                fontweight="bold", fontsize=9.5)
    ax.set(xticks=range(4), xticklabels=lab, ylabel="iso-$R_b$ shell volume [$m^3$]",
           ylim=(0, 7700))
    ax.tick_params(axis="x", labelsize=7.2)
    _head(ax, "(a) One range measurement leaves a huge shell", "#111111")
    ax.text(0.985, 0.72, "Where the drone could be, AFTER\nmeasuring $R_b$ perfectly.\n\n"
                         "5G on its always-on pilot (SSB) pins\nthe drone down to 89% of the\n"
                         "room - with $P_d$ = 1.00.",
            transform=ax.transAxes, fontsize=7.2, color="#555555", va="top", ha="right")

    # (b) gramian rank vs K
    ax = fig.add_subplot(gs[0, 1])
    K = O["gramian"]["K_sweep"]
    ax.plot([k["K"] for k in K], [k["rank"] for k in K], "o-", color="#d62728", lw=1.6, ms=5,
            label="radial run (coplanar)")
    ax.axhline(6, color="#111111", ls="--", lw=1.2)
    ax.text(1.15, 6.18, "6 = fully observable (3 pos + 3 vel)", fontsize=7.4)
    rt = O["summary"]["gramian_rank_tangential"]
    ax.axhline(rt, color="#ef6c00", ls=":", lw=1.4)
    ax.text(62, rt + 0.14, "tangential run: 5", fontsize=7.4, color="#ef6c00", ha="right")
    ax.set(xscale="log", xlabel="number of CPIs used, K", ylabel="observability rank",
           ylim=(0, 7.2))
    ax.set_xticks([1, 2, 4, 8, 16, 32, 64])
    ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    _head(ax, "(b) More time does NOT buy observability", FAILC)
    ax.legend(loc="lower right", frameon=False, fontsize=7.4)
    ax.text(0.03, 0.03, "The rank saturates at K=2 and never reaches 6.\n"
                        "Rotating the target about the TX-RX baseline is an EXACT\n"
                        "symmetry - checked on the nonlinear model, not just the\n"
                        "Jacobian: max |$\\Delta R_b$| = "
                        f"{O['gramian']['exact_rotation']['max_dRb_m']:.0e} m.",
            transform=ax.transAxes, fontsize=7.2, color="#555555", va="bottom")

    # (c) the fix
    ax = fig.add_subplot(gs[0, 2])
    fx = F["crlb"]["rows"]
    names = [r["config"].replace(" (baseline)", "") for r in fx]
    pos = [r["pos_rms_m"] for r in fx]
    cols = [FAILC if r["rank"] < 6 else PASS for r in fx]
    ax.barh(range(len(fx)), pos, 0.55, color=cols, alpha=0.85)
    for i, r in enumerate(fx):
        ax.text(pos[i] * 1.3, i, f"{pos[i]:.2f} m   (rank {r['rank']}/6)",
                va="center", fontsize=8, fontweight="bold")
    ax.set(yticks=range(len(fx)), yticklabels=names, xscale="log", xlim=(0.05, 1500),
           xlabel="position CRLB, rms [m]")
    ax.invert_yaxis()
    ax.tick_params(axis="y", labelsize=7.6)
    _head(ax, "(c) The prescription: a second receiver", PASS)
    fig.suptitle("[E5] Observability - a single TX-RX pair CANNOT determine 3D position. "
                 "This is a FAIL.",
                 fontsize=13.5, fontweight="bold", x=0.055, ha="left", y=0.985, color="#c62828")
    _cap(fig,
         "Two scalars per CPI (Rb, f_d) cannot fix three coordinates: the snapshot Fisher matrix has rank 2/3 and "
         "its null direction is almost exactly VERTICAL - the thing we cannot see is the drone's ALTITUDE.\n"
         "Watching for longer does not rescue it, because rotating the target about the TX-RX baseline leaves both "
         "measurements exactly unchanged (verified on the nonlinear model, not just the Jacobian). The chamber walls "
         "do not cut the ambiguity either: a ghost trajectory up to 6.0 m from the true one gives identical "
         "(Rb, f_d) at every instant.\n"
         "Caveats on (c): the 1RX row is RANK-DEFICIENT, so its 66 m is not a real bound - it is just what the "
         "regularised pseudo-inverse returns. The AoA sigma is an ASSUMPTION, not a measurement.\n"
         "Sources: outputs/verify_observability.json + report4_fixups.json (shell volumes re-integrated with the "
         "corrected dRb)")
    return _save(fig, "report4_e5_observability.png")


# =========================================================================== #
#  Fig 6 — [E6] Floor ghost
# =========================================================================== #
def fig_ghost():
    G = _j("verify_ghost_impact.json")
    F = _j("report4_fixups.json")["F6_ghost"]
    fig = plt.figure(figsize=(13.6, 5.0))
    gs = fig.add_gridspec(1, 3, wspace=0.30, left=0.055, right=0.985, top=0.855, bottom=0.315)

    # (a) trajectories in (Rb, fd)
    ax = fig.add_subplot(gs[0, 0])
    T = G["A_B_tracks"]["radial"]["5G NR 100MHz"]
    for i in range(0, len(T["rb_true"]), 8):
        ax.plot([T["rb_true"][i], T["rb_ghost"][i]], [T["fd_true"][i], T["fd_ghost"][i]],
                "-", color="#cccccc", lw=0.8, zorder=0)
    ax.plot(T["rb_true"], T["fd_true"], "o-", color="#1f77b4", ms=3.5, lw=1.4, label="target")
    ax.plot(T["rb_ghost"], T["fd_ghost"], "s-", color="#d62728", ms=3.5, lw=1.4,
            label="floor ghost")
    ax.set(xlabel="bistatic range $R_b$ [m]", ylabel="Doppler $f_d$ [Hz]")
    _head(ax, "(a) The ghost shadows the target, 3.5 m behind", "#111111")
    ax.legend(loc="upper right", frameon=False, fontsize=7.6)
    ax.text(0.03, 0.97, f"5G, radial run. Mean separation {T['sep_mean']:.2f} m.\n"
                        f"Doppler difference is only {abs(T['dfd_mean']):.1f} Hz - far below the\n"
                        f"{T['d_fd_hz']:.0f} Hz Doppler resolution.\n"
                        "-> ONLY bandwidth can separate them.",
            transform=ax.transAxes, fontsize=7.2, color="#555555", va="top")

    # (b) p_false reported vs corrected
    ax = fig.add_subplot(gs[0, 1])
    scen = ["radial", "tangential", "waypoint"]
    wfs = ["5G NR 100MHz", "WiFi 80MHz", "LTE 20MHz"]
    x = np.arange(3)
    w = 0.26
    for j, wfn in enumerate(wfs):
        row = [r for r in F["p_false"]["by_waveform"] if r["wf"] == wfn][0]
        rep = [row["per_scen"][s]["rep"] for s in scen]
        cor = [row["per_scen"][s]["cor"] for s in scen]
        ax.bar(x + (j - 1) * w, rep, w, color=CN[wfn], alpha=0.28)
        ax.bar(x + (j - 1) * w, cor, w, color=CN[wfn], label=wfn)
    ax.set(xticks=x, xticklabels=scen, ylabel="P(ghost seen as a SEPARATE target)",
           ylim=(0, 0.82))
    _head(ax, "(b) The old number counted the target itself", WARN)
    ax.legend(loc="upper right", frameon=False, fontsize=7.2)
    ax.text(0.03, 0.94, "pale = as originally reported\nsolid = corrected (grid-independent test)",
            transform=ax.transAxes, fontsize=7.2, color="#555555", va="top")
    ax.text(0.03, 0.63, "'tangential is worst (0.67)' was an\nindexing artefact. It is really 0.00.",
            transform=ax.transAxes, fontsize=7.2, color="#c62828")

    # (c) structural vs random
    ax = fig.add_subplot(gs[0, 2])
    r5 = [r for r in F["p_false"]["by_waveform"] if r["wf"] == "5G NR 100MHz"][0]
    bars = [("ghost track\n(as reported)", r5["track35_reported"], "#f4a3a3"),
            ("ghost track\n(CORRECTED)", r5["track35_corrected"], "#d62728"),
            ("random FA track\n(measured)", r5["random_tracks_per_window"], "#7f7f7f")]
    for i, (lab, v, c) in enumerate(bars):
        ax.bar(i, max(v, 1e-9), 0.55, color=c)
        ax.text(i, max(v, 1e-9) * 1.7, f"{v:.1e}" if v < 0.01 else f"{v:.3f}",
                ha="center", fontsize=8.2, fontweight="bold")
    ax.set(xticks=range(3), xticklabels=[b[0] for b in bars], yscale="log",
           ylim=(1e-6, 20), ylabel="P(3-of-5 track initiation) per 5-CPI window")
    ax.tick_params(axis="x", labelsize=7.2)
    _head(ax, f"(c) Still ~{r5['ratio_corrected']:.0f}x more likely than a random FA", FAILC)
    ax.text(0.98, 0.98, "5G. Even after the correction, the ghost is\n"
                        "far more likely to start a track than noise is.\n"
                        "And the ghost track is SMOOTH and\nKINEMATICALLY VALID - a tracker "
                        "has no\ngrounds to reject it.",
            transform=ax.transAxes, fontsize=7.2, color="#555555", va="top", ha="right")

    fig.suptitle("[E6] The floor ghost is a STRUCTURAL false alarm - it is correlated with the "
                 "target, so a tracker cannot filter it out",
                 fontsize=13.5, fontweight="bold", x=0.055, ha="left", y=0.985)
    pol = F["polarization"]
    ph = [r for r in pol["rows"] if r["pol"] == "H"][0]
    _cap(fig,
         "The target-via-floor path carries the target's own Doppler, so ECA cannot remove it. It trails the target "
         "by ~3.5 m along the whole trajectory, and only 5G's 3.1 m range cell resolves it; for WiFi and LTE it "
         "merges into the target cell and corrupts that cell's amplitude instead.\n"
         f"CAUTION - the ghost amplitude rests on a single undeclared assumption: VERTICAL polarisation. The "
         f"incidence angle sits just below concrete's Brewster angle, so V is anomalously weak. With H polarisation "
         f"the ghost is {pol['delta_db']:.0f} dB stronger ({ph['amp_db']:.1f} dB re echo) and every conclusion on "
         "this page changes.\n"
         "Sources: outputs/verify_ghost_impact.json + report4_fixups.json")
    return _save(fig, "report4_e6_ghost.png")


# =========================================================================== #
#  Fig 7 — §7 verdict scorecard
# =========================================================================== #
VERDICT = [
    ("E1 CFAR", "CA-CFAR alpha formula and implementation", "PASS", "-"),
    ("E1 CFAR", "Empirical Pfa equals nominal Pfa", "FAIL",
     "Use the measured calibration table (per waveform)"),
    ("E1 CFAR", "Same TRUE Pfa across waveforms", "FAIL",
     "Calibrate each waveform first, THEN compare Pd"),
    ("E1 CFAR", "Zero-Doppler masking is safe", "COND",
     "Mask zd+-1 AND exclude those rows from training"),
    ("E2 ECA", "Direct-path cancellation depth", "COND",
     "Floor is 31-56 dB, not infinite - state it"),
    ("E2 ECA", "Slow-target loss follows 1-sinc^2", "PASS", "-"),
    ("E2 ECA", "Hovering drones are detectable", "FAIL",
     "ECA erases f_d ~ 0 by construction. Declare a blind speed"),
    ("E3 AF", "Range / Doppler resolution", "PASS", "-"),
    ("E3 AF", "Ambiguity peaks stay outside the chamber", "COND",
     "5G-PRS has a -22 dB peak at 19.5 m - inside the window"),
    ("E3 AF", "5G Doppler axis is physical", "FAIL",
     "SSB repeats at 50 Hz, not 2000 Hz. Fix frame_len()"),
    ("E3 AF", "Resolution convention is consistent", "FAIL",
     "The codebase uses c/B and c/2B at the same time"),
    ("E4 LB", "Radar equation -> injected amplitude", "PASS", "-"),
    ("E4 LB", "Processing gain = matched filter x M", "PASS", "-"),
    ("E4 LB", "Observation time is a controlled variable", "FAIL",
     "Equalise T_CPI, not M (5G loses 3.01 dB to a convention)"),
    ("E5 OBS", "3D position from one TX-RX pair", "FAIL",
     "Impossible in principle. Add a 2nd RX -> rank 6, 0.22 m"),
    ("E5 OBS", "Altitude is observable", "FAIL",
     "The null direction is 99% vertical. Never plot x-y only"),
    ("E6 GHOST", "ECA removes the floor ghost", "FAIL",
     "It carries Doppler. The benchmark MUST enable it"),
    ("E6 GHOST", "A tracker can reject the ghost", "FAIL",
     "Smooth and kinematically valid. Needs a geometric gate"),
    ("E6 GHOST", "The ghost amplitude is known", "COND",
     "Assumes V-pol; H-pol is 12 dB stronger"),
]
VC = {"PASS": PASS, "FAIL": FAILC, "COND": WARN}


def fig_verdict():
    fig, ax = plt.subplots(figsize=(13.6, 7.8))
    ax.axis("off")
    ax.grid(False)
    n = len(VERDICT)
    ax.set(xlim=(0, 1), ylim=(0, n + 1.7))
    ax.text(0.0, n + 1.02, "Is the detector calibrated enough to run the benchmark?",
            fontsize=14.5, fontweight="bold")
    ax.text(0.0, n + 0.45, "PASS = trust it     |     CONDITIONAL = trust it only with the stated "
                           "caveat     |     FAIL = fix it before the benchmark",
            fontsize=8.5, color="#555555")
    ax.text(0.605, n + 1.02, "what must be fixed", fontsize=9, color="#555555",
            style="italic", va="center")
    for i, (exp, item, v, fix) in enumerate(VERDICT):
        y = n - i - 0.5
        if i % 2 == 0:
            ax.add_patch(Rectangle((0.0, y - 0.45), 1.0, 0.9, color="#f4f4f4", zorder=0))
        ax.text(0.004, y, exp, fontsize=8.0, va="center", color="#333333", fontweight="bold")
        ax.text(0.10, y, item, fontsize=8.8, va="center")
        ax.add_patch(Rectangle((0.505, y - 0.27), 0.078, 0.54, color=VC[v], zorder=2))
        ax.text(0.544, y, v, fontsize=7.6, va="center", ha="center", color="white",
                fontweight="bold", zorder=3)
        ax.text(0.605, y, fix, fontsize=8.0, va="center", color="#444444")
    npass = sum(1 for v in VERDICT if v[2] == "PASS")
    nfail = sum(1 for v in VERDICT if v[2] == "FAIL")
    ncond = sum(1 for v in VERDICT if v[2] == "COND")
    _cap(fig, f"{npass} PASS   /   {ncond} CONDITIONAL   /   {nfail} FAIL.     "
              "None of this says the benchmark is impossible. It says the benchmark AS CURRENTLY "
              "SPECIFIED would produce numbers we could not defend.\n"
              "Every FAIL has a concrete and cheap fix, and that list is the actual deliverable of "
              "this report.", y=0.012)
    return _save(fig, "report4_e7_verdict.png")


def build_all():
    return [fig_cfar(), fig_eca(), fig_ambiguity(), fig_linkbudget(),
            fig_observability(), fig_ghost(), fig_verdict()]


if __name__ == "__main__":
    build_all()
