# -*- coding: utf-8 -*-
"""
viz_facet_count.py — outputs/facet_count.json → outputs/figs/facet_count_effect.png
====================================================================================
가설("메쉬 삼각형 수가 스톡 Sionna 표적 에코를 바꾼다")의 검정 결과 그림.
숫자는 **전부 JSON 에서 읽는다** — 손으로 적지 않는다.
그림 텍스트는 영어(하우스 규약), 주석·print 는 한국어.

⭐ 결과가 **두 갈래**라 그림도 두 갈래를 나란히 보여준다:
   · 일반 자세(정반사 없음, 확산 바닥) → 삼각형 수에 **무감**
   · 정반사가 살아 있는 단 하나의 자세 → 면 하나 잃을 때마다 **−6 dB**, 다 잃으면 **소멸**

패널
  (a) 일반 자세의 스톡 RT 에코 vs 삼각형 수 (비코히런트/코히런트)
  (b) 정반사 자세의 스톡 RT 에코 vs 삼각형 수 (+ PEC 정반사 전용 탐침)
  (c) 대조군 — 우리 PO / SBR 의 σ
  (d) 판별자 — 경로 개수는 삼각형 수가 아니라 광선 예산을 따라간다
  (e) 타당성 — 형상 보존 검사
  (f) 요약 — 엔진·설정별 [dB/decade] 기울기

색: dataviz 기준 팔레트 categorical 슬롯 1·2·3·8 (#2a78d6 blue / #eb6834 orange /
    #1baf7a aqua / #e34948 red) — 문서상 게이트를 통과한 조합. (d) 는 서열 자료라
    blue 램프(step 250/450/650).
실행: python src/viz_facet_count.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from vizstyle import use_korean                                       # noqa: E402
use_korean()
import matplotlib.pyplot as plt                                       # noqa: E402

#  ⚠ 이 그림은 **텍스트가 전부 영어**다(하우스 규약). 나눔고딕에는 그리스 문자(σ·Σ·β·λ)가
#     없어 두부(□)로 깨진다 — 영어 전용 그림이므로 DejaVu Sans 로 되돌린다.
plt.rcParams["font.family"] = "DejaVu Sans"

JSON = os.path.join(ROOT, "outputs", "facet_count.json")
FIG = os.path.join(ROOT, "outputs", "figs", "facet_count_effect.png")

C_STOCK = "#2a78d6"      # slot 1 blue   — stock Sionna RT
C_PO = "#eb6834"         # slot 2 orange — our PO
C_SBR = "#1baf7a"        # slot 3 aqua   — our SBR
C_HOT = "#e34948"        # slot 8 red    — 정반사 자세
RAMP = ["#86b6ef", "#2a78d6", "#104281"]   # blue 250/450/650 (서열용)
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#8b8a85", "#e3e2de"
BAD = "#f3efe6"          # 형상 무효 구간 음영
FLOOR = -108.0           # (b) 에서 '경로 소멸'을 그릴 바닥값 [dB]


def _ax(ax):
    """공통 축 꾸밈 — 격자·축선은 뒤로 물린다."""
    ax.grid(True, which="major", color=GRID, lw=0.8, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=9, length=3)


def _label_end(ax, x, y, text, color, dx=1.06, va="center"):
    """마지막 점 옆 직접 라벨(모든 점에 숫자를 붙이지 않는다)."""
    ax.text(x * dx, y, text, color=color, fontsize=8.5, fontweight="bold",
            va=va, ha="left", clip_on=False)


def main():
    with open(JSON) as f:
        D = json.load(f)
    L = D["levels"]
    ntri = np.array([l["n_tri"] for l in L], float)
    okm = np.array([l["shape_ok"] for l in L], bool)
    sl, sp, meta = D["slopes"], D["spans"], D["meta"]
    hot = D["specular_hot_aspect"]
    xlo, xhi = ntri.min() * 0.55, ntri.max() * 2.9
    bad_x = ntri[~okm]
    x_edge = float(bad_x.max()) * 1.6 if bad_x.size else None

    fig, axes = plt.subplots(2, 3, figsize=(19.2, 9.6), dpi=140)
    fig.patch.set_facecolor("white")
    (a, b, c), (d, e, f) = axes

    def shade(ax):
        if x_edge:
            ax.axvspan(xlo, x_edge, color=BAD, zorder=0)

    # ------------------------------------------------------------------ (a)
    inc = np.array([l["rt_incoh_db"] for l in L], float)
    coh = np.array([l["rt_coh_db"] for l in L], float)
    shade(a)
    a.errorbar(ntri, inc, yerr=[l["rt_incoh_sd"] for l in L], color=C_STOCK, lw=2,
               marker="o", ms=7, capsize=3, elinewidth=1.2, zorder=3,
               markeredgecolor="white", markeredgewidth=1.2)
    a.errorbar(ntri, coh, yerr=[l["rt_coh_sd"] for l in L], color=C_STOCK, lw=2, ls="--",
               marker="s", ms=7, mfc="white", capsize=3, elinewidth=1.2, zorder=3,
               markeredgecolor=C_STOCK, markeredgewidth=1.6)
    a.set_xscale("log"); a.set_xlim(xlo, xhi)
    a.set_xlabel("Mesh triangles (same outer shape)", color=INK2, fontsize=10)
    a.set_ylabel("Target echo, rel. direct path  [dB]", color=INK2, fontsize=10)
    a.set_title("(a)  Generic aspects  —  echo is flat", color=INK, fontsize=12,
                fontweight="bold", loc="left")
    _ax(a)
    _label_end(a, ntri.max(), inc[np.argmax(ntri)],
               f"incoherent Σ|a|²\n{sl['stock_incoh']:+.2f} dB/decade", C_STOCK)
    _label_end(a, ntri.max(), coh[np.argmax(ntri)],
               f"coherent |Σa|²\n{sl['stock_coh']:+.2f} dB/decade", C_STOCK)
    a.text(0.03, 0.55,
           f"{len(meta['az_deg'])} azimuths at el = {meta['el_deg']:.0f}°, "
           f"{len(meta['seeds'])} seeds\n"
           f"total swing over {sp['n_tri_span_decades']:.2f} decades: "
           f"{sp['stock_incoh_span_db']:.2f} dB\n"
           "no specular path exists at these aspects —\n"
           "the echo is pure diffuse scattering",
           transform=a.transAxes, fontsize=8.5, color=INK2, va="top",
           bbox=dict(boxstyle="round,pad=0.5", fc="#f7f7f5", ec=GRID))

    # ------------------------------------------------------------------ (b)
    hr = hot["rows"]
    hx = np.array([r["n_tri"] for r in hr], float)
    hc = np.array([r["coh_db"] for r in hr], float)
    hs = np.array([r["spec_only_coh_db"] if r["spec_only_coh_db"] is not None else np.nan
                   for r in hr], float)
    shade(b)
    b.plot(hx, hc, color=C_HOT, lw=2.2, marker="o", ms=7, zorder=4,
           markeredgecolor="white", markeredgewidth=1.2)
    b.plot(hx, hs, color=C_HOT, lw=1.6, ls=":", marker="D", ms=6, mfc="white", zorder=3,
           markeredgecolor=C_HOT, markeredgewidth=1.4)
    npz = [r["n_tri"] for r, s in zip(hr, hs) if not np.isfinite(s)]
    if npz:
        b.plot(npz, [FLOOR] * len(npz), color=C_HOT, marker="x", ms=9, mew=2.2, ls="none",
               zorder=4)
        b.text(min(npz) * 1.15, FLOOR, " PEC probe: no specular path", color=C_HOT,
               fontsize=8.5, va="center", fontweight="bold")
    b.axhline(float(np.mean(inc)), color=C_STOCK, lw=1.4, ls="--", zorder=2)
    b.text(xlo * 1.15, float(np.mean(inc)) + 1.2, "diffuse floor from (a)", color=C_STOCK,
           fontsize=8.5, ha="left", va="bottom")
    b.set_xscale("log"); b.set_xlim(xlo, xhi)
    b.set_xlabel("Mesh triangles (same outer shape)", color=INK2, fontsize=10)
    b.set_ylabel("Target echo, rel. direct path  [dB]", color=INK2, fontsize=10)
    b.set_title(f"(b)  Boresight-facet aspect (az {hot['aspect']['az_deg']:.0f}°, "
                f"el {hot['aspect']['el_deg']:.0f}°)  —  echo falls off a cliff",
                color=INK, fontsize=12, fontweight="bold", loc="left")
    _ax(b)
    _label_end(b, hx[np.argmax(hx)], hc[np.argmax(hx)],
               f"production materials\n{hot['slopes']['coh_db_shapeok']:+.2f} dB/decade*",
               C_HOT)
    b.annotate("PEC probe, specular only\n(sits on top of the solid curve)",
               xy=(hx[3], hs[3]), xytext=(0, -34), textcoords="offset points",
               ha="center", va="top", fontsize=8.5, color=C_HOT,
               arrowprops=dict(arrowstyle="-", color=C_HOT, lw=1))
    steps = [str(l["spec_n_paths_total"]) for l in L]
    b.text(0.97, 0.30,
           f"effective specular facets\n(fine → coarse): {' / '.join(steps)}\n"
           f"2 → 1 facet = {hc[3] - hc[0]:+.2f} dB\n"
           "  (20·log10 ½ = -6.02 dB)\n"
           f"1 → 0 facets = {hc[-1] - hc[3]:+.1f} dB\n"
           "  (specular gone; that level\n   also breaks the shape)",
           transform=b.transAxes, fontsize=8.2, color=INK2, va="bottom", ha="right",
           bbox=dict(boxstyle="round,pad=0.5", fc="#fdf1f1", ec="#f0d5d5"))

    # ------------------------------------------------------------------ (c)
    po = np.array([l["po_dbsm_mean"] for l in L], float)
    sbr = np.array([l["sbr_dbsm_mean"] if l["sbr_dbsm_mean"] is not None else np.nan
                    for l in L], float)
    shade(c)
    c.plot(ntri, po, color=C_PO, lw=2, marker="o", ms=7, zorder=3,
           markeredgecolor="white", markeredgewidth=1.2)
    c.plot(ntri, sbr, color=C_SBR, lw=2, marker="^", ms=8, zorder=3,
           markeredgecolor="white", markeredgewidth=1.2)
    c.set_xscale("log"); c.set_xlim(xlo, xhi)
    c.set_xlabel("Mesh triangles (same outer shape)", color=INK2, fontsize=10)
    c.set_ylabel("Monostatic RCS  σ  [dBsm]", color=INK2, fontsize=10)
    c.set_title("(c)  Control — our surface-integral kernels", color=INK, fontsize=12,
                fontweight="bold", loc="left")
    _ax(c)
    _label_end(c, ntri.max(), po[np.argmax(ntri)], f"PO  {sl['po_shapeok']:+.2f} dB/dec*", C_PO)
    _label_end(c, ntri.max(), sbr[np.argmax(ntri)], f"SBR {sl['sbr_shapeok']:+.2f} dB/dec*", C_SBR)
    c.text(0.97, 0.03, "* shape-preserving levels only;  point grid refined 4x changes it by "
           f"{D['robustness']['po_point_density']['lam_over_28']['slope_shapeok'] - D['robustness']['po_point_density']['lam_over_7']['slope_shapeok']:+.2f}",
           transform=c.transAxes, fontsize=7.6, color=MUTED, ha="right",
           bbox=dict(boxstyle="square,pad=0.3", fc="white", ec="none"))

    # ------------------------------------------------------------------ (d)
    sw = D["budget_sweep"]
    tris = sorted({r["n_tri"] for r in sw}, reverse=True)
    for i, t in enumerate(tris):
        g = sorted([r for r in sw if r["n_tri"] == t], key=lambda r: r["spp"])
        d.plot([r["spp"] for r in g], [r["n_paths"] for r in g],
               color=RAMP[min(i, len(RAMP) - 1)], lw=2, marker="o", ms=6, zorder=3,
               markeredgecolor="white", markeredgewidth=1.0, label=f"{t:,} triangles")
    xr = np.array([min(r["spp"] for r in sw), max(r["spp"] for r in sw)], float)
    yr = 0.30 * max(r["n_paths"] for r in sw) * xr / xr.max()
    d.plot(xr, yr, color=MUTED, lw=1.2, ls=":", zorder=2,
           label="reference: paths ∝ ray budget (slope 1)")
    d.legend(frameon=False, fontsize=8.5, loc="lower right", labelcolor=INK2)
    d.set_xscale("log"); d.set_yscale("log"); d.set_xlim(xr[0] * 0.6, xr[1] * 1.8)
    d.set_xlabel("Ray budget  samples_per_src", color=INK2, fontsize=10)
    d.set_ylabel("Target-via paths found", color=INK2, fontsize=10)
    d.set_title("(d)  Path count tracks rays, not triangles", color=INK, fontsize=12,
                fontweight="bold", loc="left")
    _ax(d)
    d.text(0.03, 0.95, f"at fixed budget, paths ∝ N_tri^{sl['paths_loglog_exp']:.3f}",
           transform=d.transAxes, fontsize=8.5, color=INK2, va="top",
           bbox=dict(boxstyle="round,pad=0.5", fc="#f7f7f5", ec=GRID))

    # ------------------------------------------------------------------ (e)
    shade(e)
    e.axhspan(-10, 10, color="#eef4fb", zorder=1)
    e.axhline(0, color=GRID, lw=1, zorder=2)
    for y, col, mk, nm in (([l["bbox_dev_pct"] for l in L], C_STOCK, "o", "bounding box"),
                           ([l["proj_dev_pct"] for l in L], C_PO, "s", "silhouette area"),
                           ([l["surf_dev_pct"] for l in L], C_SBR, "^", "surface area")):
        e.plot(ntri, y, color=col, lw=2, marker=mk, ms=7, zorder=3,
               markeredgecolor="white", markeredgewidth=1.2, label=nm)
    e.set_xscale("log"); e.set_xlim(xlo, ntri.max() * 1.7)
    e.set_xlabel("Mesh triangles", color=INK2, fontsize=10)
    e.set_ylabel("Deviation from full mesh  [%]", color=INK2, fontsize=10)
    e.set_title("(e)  Validity — is the shape preserved?", color=INK, fontsize=12,
                fontweight="bold", loc="left")
    _ax(e)
    e.legend(frameon=False, fontsize=8.5, loc="lower right", labelcolor=INK2)
    e.text(0.985, 0.60, "±10 % validity gate", transform=e.transAxes, fontsize=8,
           color=MUTED, ha="right", va="center")

    # ------------------------------------------------------------------ (f)
    bars = [("Stock RT — boresight-facet aspect", hot["slopes"]["coh_db_shapeok"], C_HOT),
            ("Our PO (surface integral)", sl["po_shapeok"], C_PO),
            ("Our SBR (ray grid + PO)", sl["sbr_shapeok"], C_SBR),
            ("Stock RT — generic aspects", sl["stock_incoh_shapeok"], C_STOCK)]
    ypos = np.arange(len(bars))[::-1]
    for yp, (nm, v, col) in zip(ypos, bars):
        f.barh(yp, v, height=0.55, color=col, zorder=3)
        f.text(v + 0.5, yp, f"{v:+.2f}", color=INK, fontsize=9.5, fontweight="bold",
               va="center", ha="left")
    f.set_yticks(ypos, [nm for nm, _, _ in bars], color=INK2, fontsize=9.5)
    f.set_xlim(0, max(v for _, v, _ in bars) * 1.32)
    f.set_xlabel("Echo / σ sensitivity to triangle count  [dB per decade]",
                 color=INK2, fontsize=10)
    f.set_title("(f)  Summary — where triangle count matters", color=INK, fontsize=12,
                fontweight="bold", loc="left")
    _ax(f)
    f.grid(axis="y", visible=False)
    f.text(0.98, 0.30,
           "all slopes over shape-preserving levels only\n"
           f"(with the shape-broken level: {hot['slopes']['coh_db']:+.1f} dB/decade)",
           transform=f.transAxes, fontsize=8.2, color=INK2, ha="right", va="center",
           bbox=dict(boxstyle="round,pad=0.5", fc="#f7f7f5", ec=GRID))

    # ------------------------------------------------------------------ 제목
    fig.suptitle("Does mesh triangle count change the target echo in stock Sionna RT?",
                 fontsize=16, fontweight="bold", color=INK, x=0.008, ha="left", y=0.985)
    fig.text(0.008, 0.947,
             f"{meta['drone']} · {meta['fc_hz']/1e9:.1f} GHz · quasi-monostatic R = {meta['range_m']:.0f} m "
             f"(β = {meta['bistatic_deg']:.1f}°) · per-part quadric decimation, "
             f"{int(round(10**sp['n_tri_span_decades']))}x triangle range "
             f"({int(ntri.max()):,} → {int(ntri.min()):,}) · same outer shape",
             fontsize=10, color=INK2, ha="left")
    fig.text(0.008, 0.917,
             f"ANSWER  —  it depends on the aspect.   Generic aspects: "
             f"{sp['stock_incoh_span_db']:.2f} dB over the whole ladder "
             f"({sl['stock_incoh_shapeok']:+.2f} dB/decade), less sensitive than our own PO/SBR."
             f"   Boresight-facet aspect: {hot['slopes']['coh_db_shapeok']:+.2f} dB/decade "
             f"and a {hc[0] - hc[-1]:.0f} dB collapse in all, one exact -6.02 dB step per lost facet.",
             fontsize=10.5, color=INK, fontweight="bold", ha="left")

    fig.tight_layout(rect=(0, 0, 1, 0.895))
    os.makedirs(os.path.dirname(FIG), exist_ok=True)
    fig.savefig(FIG, dpi=140, facecolor="white", bbox_inches="tight")
    print("[fig] 저장:", os.path.relpath(FIG, ROOT))
    return FIG


if __name__ == "__main__":
    main()
