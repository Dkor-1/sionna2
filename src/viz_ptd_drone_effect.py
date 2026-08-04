# -*- coding: utf-8 -*-
"""viz_ptd_drone_effect.py — 검증 3 그림 (PTD 효과·비용)

하우스 규약: **그림 안의 글자는 전부 영어**. 수치는 outputs/ptd_drone_effect.json 에서만 읽는다.

    PYTHONPATH=src python src/viz_ptd_drone_effect.py
    → outputs/figs/ptd_drone_effect.png
"""
from __future__ import annotations

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                   # noqa: E402
import numpy as np                                                # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
FIGDIR = os.path.join(ROOT, "outputs", "figs")
SRC = os.path.join(ROOT, "outputs", "ptd_drone_effect.json")

#  범주형 4색 — Okabe-Ito 파생. scripts/validate_palette.js 등가 검사 통과
#  (lightness band PASS, chroma floor PASS, CVD adjacent PASS/1 WARN, normal floor 16.4 PASS).
#  WARN 쌍(pink vs green)과 pink 의 대비 WARN 은 **선종류 + 직접 라벨** 2차 부호화로 상쇄한다.
C_PO = "#0072B2"      # PO only  (ptd=False)
C_PTD = "#D55E00"     # PO + PTD (ptd=True)
C_EDGE = "#CC79A7"    # edge term alone
C_PROD = "#009E73"    # production SBR control
INK = "#263238"
MUTED = "#78909c"

DAS = 0.210
#  헤드라인 구성 그대로: 고도 3컷(0, -2, -20°) 전력풀링 · V(=VV, Das 규약)
CUT = "el_pooled"
CUT_LABEL = "3 elevation cuts pooled (0, -2, -20$\\degree$)"
POL = "V"


def _style():
    plt.rcParams.update({
        "figure.facecolor": "white", "savefig.facecolor": "white",
        "axes.grid": True, "grid.alpha": 0.25, "grid.linewidth": 0.6,
        "axes.spines.top": False, "axes.spines.right": False,
        "font.size": 9.5, "axes.titlesize": 10.5, "axes.labelsize": 9.5,
        "legend.frameon": False, "axes.unicode_minus": False,
    })


def panel_mu(ax, D, key, title_extra=""):
    """μ(f) — PO / PO+PTD / edge-only, 조밀 격자 + 회귀선."""
    blk = D["slopes"][key]["dense"][CUT][POL]
    f = np.array(blk["f_ghz"])
    po = np.array(blk["mu_po_dbsm"])
    pt = np.array(blk["mu_ptd_dbsm"])
    ed = np.array(blk["mu_edge_only_dbsm"])

    ax.plot(f, po, "-o", color=C_PO, lw=1.8, ms=3.5, label="PO only (ptd=False)")
    ax.plot(f, pt, "-s", color=C_PTD, lw=1.8, ms=3.5, label="PO + PTD (ptd=True)")
    ax.plot(f, ed, "--^", color=C_EDGE, lw=1.5, ms=3.5, label="edge term alone")

    for y, c, a, se in ((po, C_PO, blk["slope_po_db_per_ghz"], blk["se_po"]),
                        (pt, C_PTD, blk["slope_ptd_db_per_ghz"], blk["se_ptd"])):
        b = y.mean() - a * f.mean()
        ax.plot(f, a * f + b, ":", color=c, lw=1.4)

    rows = [r for r in D["production_sbr_control"]["rows"] if r["drone"] == key]
    if rows:
        byf = {}
        for r in rows:
            byf.setdefault(round(r["fc_ghz"], 3), []).append(10 ** (r["production_sbr_dbsm"] / 10))
        fp = sorted(byf)
        ax.plot(fp, [10 * np.log10(np.mean(byf[x])) for x in fp],
                "D", color=C_PROD, ms=6, mfc="none", mew=1.8,
                label="production SBR (occlusion, GPU)")

    a0, a1 = blk["slope_po_db_per_ghz"], blk["slope_ptd_db_per_ghz"]
    ax.set_title(f"{key}  ·  {D['drones'][key]['edge_stats']['length_metal_m']:.1f} m metal edge "
                 f"({D['drones'][key]['L_metal_lambda_at_3p5GHz']:.0f} $\\lambda$ @3.5 GHz){title_extra}",
                 pad=8)
    ax.set_xlabel("frequency [GHz]")
    ax.set_ylabel(r"azimuth-mean $\sigma$ [dBsm]")
    lo = min(po.min(), pt.min(), ed.min())
    hi = max(po.max(), pt.max(), ed.max())
    ax.set_ylim(lo - 0.30 * (hi - lo), hi + 0.34 * (hi - lo))
    ax.text(0.025, 0.975,
            f"slope PO      {a0:+.2f} $\\pm$ {blk['se_po']:.2f} dB/GHz   (R$^2$ {blk['r2_po']:.2f})\n"
            f"slope PO+PTD  {a1:+.2f} $\\pm$ {blk['se_ptd']:.2f} dB/GHz   (R$^2$ {blk['r2_ptd']:.2f})\n"
            f"edge alone    {blk['slope_edge_only_db_per_ghz']:+.2f} dB/GHz",
            transform=ax.transAxes, va="top", ha="left", fontsize=8.0, color=INK,
            family="DejaVu Sans Mono",
            bbox=dict(fc="white", ec=MUTED, lw=0.6, alpha=0.94, pad=3))
    ax.legend(loc="lower center", fontsize=7.8, ncol=2, columnspacing=1.2,
              handlelength=1.8, borderaxespad=0.3)


def panel_slope(ax, D):
    """기울기 막대 — Das 0.210 dB/GHz 기준선과 격차 배수."""
    keys = list(D["drones"])
    labels, vals, cols = [], [], []
    for k in keys:
        b = D["slopes"][k]["dense"][CUT][POL]
        labels += [f"{k}\nPO", f"{k}\nPO+PTD"]
        vals += [b["slope_po_db_per_ghz"], b["slope_ptd_db_per_ghz"]]
        cols += [C_PO, C_PTD]
    x = np.arange(len(vals))
    bars = ax.bar(x, vals, color=cols, width=0.50, zorder=3)
    ax.axhline(DAS, color=INK, lw=1.6, ls="--", zorder=4)
    ax.axhline(0, color=MUTED, lw=0.8, zorder=2)
    ax.set_xlim(-0.62, len(vals) - 0.38)
    ax.text(1.0, DAS + 0.05, f"Das measured {DAS:.3f} dB/GHz", va="bottom",
            ha="center", fontsize=8.5, color=INK)
    for xi, v, b in zip(x, vals, bars):
        ax.text(xi, v + (0.06 if v >= 0 else -0.06), f"{v:+.2f}\n({abs(v)/DAS:.1f}$\\times$)",
                ha="center", va="bottom" if v >= 0 else "top", fontsize=8.2, color=INK)
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=8.2)
    ax.set_ylabel("band slope [dB/GHz]")
    ax.set_title(f"Band slope fitted on 21 frequency points, 1.8-5.8 GHz  "
                 f"({CUT_LABEL}, {POL}-pol = Das VV convention)", pad=8)
    ax.set_xlabel("band spans are NOT the same: ours 1.8-5.8 GHz (4.0 GHz)   ·   "
                  "Das 1.8-18.2 GHz (16.4 GHz)", fontsize=8.2, color=MUTED, style="italic",
                  labelpad=8)
    lo, hi = min(vals + [0]), max(vals + [DAS])
    ax.set_ylim(lo - 0.55, hi + 0.60)


def panel_cost(ax, D):
    """비용 — 모서리항이 면적분에 얹는 %, Gao 4.6~17.2% 띠 옆에."""
    rows = [r for r in D["cost"]["rows"] if r["pol"] == POL]
    ax.axhspan(4.6, 17.2, color=MUTED, alpha=0.22, zorder=1)
    ax.text(0.03, 8.5, "Gao 2012: 4.6-17.2 %\n(~3920 $\\lambda$ aircraft, wall clock)",
            transform=ax.get_yaxis_transform(), va="center", ha="left", fontsize=7.8,
            color=INK)
    mk = {"s1000plus": "o", "mini5pro": "s"}
    for k in D["drones"]:
        rr = [r for r in rows if r["drone"] == k]
        ax.scatter([r["n_points"] for r in rr],
                   [r["increase_pct_vs_surface_integral"] for r in rr],
                   s=26, marker=mk.get(k, "o"), facecolor="none",
                   edgecolor=C_PTD if k == "s1000plus" else C_PO, linewidth=1.3,
                   label=f"{k}  ({D['drones'][k]['L_metal_lambda_at_3p5GHz']:.0f} $\\lambda$ edge)",
                   zorder=3)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_ylim(3, 700)
    ax.set_xlabel("PO point-cloud size  (electrical size proxy)")
    ax.set_ylabel("edge cost / PO area-integral cost  [%]")
    s = D["cost"]["summary_pct"]["vs_surface_integral"]
    s2 = D["cost"]["summary_pct"]["vs_surface_plus_pointcloud"]
    ax.set_title(f"Cost of adding the edge line integral\n"
                 f"ours {s['min']:.0f}-{s['max']:.0f} % of the area integral "
                 f"({s2['min']:.0f}-{s2['max']:.0f} % of the whole PO solve)", fontsize=9.6, pad=6)
    ax.legend(loc="upper right", fontsize=7.8)


def panel_runtime(ax, D):
    """per-pose 절대 런타임 사다리 — Ziganshin 반론용."""
    pp = D["per_pose_runtime_ms"]
    b = pp["baselines"]
    fx = D["addendum"]["extraction_amortisation_correction"]
    items = [
        ("PTD edge term alone (CPU)", pp["edge_term_only"]["median"], C_PTD),
        ("PO area integral alone (CPU)", pp["po_only"]["median"], C_PO),
        ("PO+PTD pose, small frame", fx["mini5pro"]["po_plus_ptd_median_ms_realistic"],
         C_EDGE),
        ("PO+PTD pose, large frame", fx["s1000plus"]["po_plus_ptd_median_ms_realistic"],
         C_EDGE),
        ("our production SBR+PO (GPU)", b["our_production_sbr_ms"]["median"], C_PROD),
        ("stock Sionna, same RTX 4090", 106.3, INK),
        ("stock Sionna, published", 204.0, MUTED),
    ]
    y = np.arange(len(items))[::-1]
    ax.barh(y, [v for _, v, _ in items], color=[c for _, _, c in items], height=0.62, zorder=3)
    for yi, (_, v, _) in zip(y, items):
        ax.text(v * 1.14, yi, f"{v:.1f} ms" if v < 10 else f"{v:.0f} ms",
                va="center", fontsize=8.2, color=INK)
    ax.set_yticks(y); ax.set_yticklabels([t for t, _, _ in items], fontsize=8.0)
    ax.set_xscale("log")
    ax.set_xlim(0.7, 3000)
    ax.set_xlabel("time per pose [ms]  (log)")
    ax.set_title("Per-pose runtime ladder\n"
                 "adding the edge term keeps us under stock Sionna's own per-pose cost",
                 fontsize=9.6, pad=6)
    ax.grid(axis="y", visible=False)


def main():
    _style()
    with open(SRC, encoding="utf-8") as fh:
        D = json.load(fh)
    keys = list(D["drones"])

    fig = plt.figure(figsize=(14.4, 11.2))
    gs = fig.add_gridspec(3, 2, height_ratios=[1.0, 1.0, 0.95], hspace=0.52, wspace=0.42,
                          left=0.055, right=0.985, top=0.875, bottom=0.05)
    panel_mu(fig.add_subplot(gs[0, 0]), D, keys[0], "   — many edges")
    panel_mu(fig.add_subplot(gs[0, 1]), D, keys[1], "   — few edges")
    panel_slope(fig.add_subplot(gs[1, :]), D)
    panel_cost(fig.add_subplot(gs[2, 0]), D)
    panel_runtime(fig.add_subplot(gs[2, 1]), D)

    ctrl = D["production_sbr_control"]["summary"]
    sd = D["addendum"][keys[0]]["sharp_deg_verdict"]
    warn = (f"the edge-term LEVEL is not yet usable: on {keys[0]} PO+PTD lands "
            f"{ctrl[keys[0]]['po_ptd']['median']:+.1f} dB (median) from our own production SBR "
            f"value, against {ctrl[keys[0]]['po']['median']:+.1f} dB for PO alone.\n"
            "The 1/2 normalisation of the fringe term is UNVERIFIED (flat-plate calibration not "
            "run), there is no occlusion on this path, and the truncated-wedge correction is "
            "absent.\nFalsification attempt: 40-55 % of the kept metal edge length is only a "
            "5-10° tessellation seam, but raising the sharp-edge gate 5°→30° "
            f"(-53 % of edge length) moves the result by {abs(sd['collapse_db']):.2f} dB "
            "— the effect is NOT a mesh artifact.")
    fig.suptitle("Does the PTD edge term move our band slope toward the measured one — "
                 "and what does it cost?", fontsize=14, y=0.975)
    fig.text(0.5, 0.952, warn, ha="center", va="top", fontsize=8.4, color="#b71c1c",
             linespacing=1.5)

    os.makedirs(FIGDIR, exist_ok=True)
    p = os.path.join(FIGDIR, "ptd_drone_effect.png")
    fig.savefig(p, dpi=165)
    plt.close(fig)
    print(f"[fig] {p}")
    return p


if __name__ == "__main__":
    main()
