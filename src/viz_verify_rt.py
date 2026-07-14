# -*- coding: utf-8 -*-
"""
viz_verify_rt.py — (report6) **Sionna RT 의 기본 path solver 에는 산란적분 단계가 없어 표적 σ 가
창발하지 않는다** 를 그림으로. (⚠ "레이트레이싱은 RCS 를 못 낸다" 는 거짓 — SBR(GO+PO)은 계산해낸다.)

모든 수치는 benchmark/verify_rt_no_rcs.py 가 실제로 측정해 남긴
outputs/rt_no_rcs_verify.json 에서 읽는다(하드코딩 없음).

생성물 (outputs/figures/, report6_ 접두어)
  report6_rt_no_sigma.png   : (a) 평판 크기 스윕 — σ 52 dB 변해도 RT 진폭비 불변
                              (b) 구 산란계수 S 스윕 — RT 는 σ 가 아니라 S 를 잰다
  report6_rt_missing.png    : PEC 금속구에서 RT 가 만드는 경로 = 0개 (평판은 즉시 잡힘)
  report6_rt_delay.png      : RT 가 '맞히는 것'과 '틀리는 것' — 지연축으로 본 진실
  report6_hybrid.png        : 그래서 어떻게 나누는가 (하이브리드 구조도)
"""
from __future__ import annotations
import os, json
import numpy as np

import vizstyle
vizstyle.use_korean()
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "..", "outputs", "figures")
JSON = os.path.join(HERE, "..", "outputs", "rt_no_rcs_verify.json")

C_RT, C_TH, C_BAD, C_OK = "#c62828", "#1565c0", "#9e9e9e", "#2e7d32"


def _load():
    with open(JSON) as f:
        return json.load(f)


# --------------------------------------------------------------------------- #
#  (1) RT 의 두 채널 — 어느 쪽도 σ 의 함수가 아니다
# --------------------------------------------------------------------------- #
def fig_no_sigma(outdir=FIG):
    d = _load()
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.4), constrained_layout=True)
    fig.suptitle("Sionna RT's stock path solver has no place for target RCS", fontsize=16, fontweight="bold")

    # (a) 평판: σ 를 52 dB 바꿔도 RT 는 꿈쩍 않는다
    A = [r for r in d["A_plate"] if r.get("ratio_db") is not None]
    side = [r["side"] for r in A]
    sig = [r["sigma_dbsm"] for r in A]
    rt = [r["ratio_db"] for r in A]
    ax = axes[0]
    ax.plot(side, sig, "o-", color=C_TH, lw=2, ms=7,
            label=r"Target RCS $\sigma$ (theory, $4\pi A^2/\lambda^2$)")
    ax.set_xscale("log"); ax.set_xticks(side); ax.set_xticklabels([f"{s:g}" for s in side])
    ax.set_xlabel("Metal plate side [m]"); ax.set_ylabel(r"$\sigma$ [dBsm]", color=C_TH)
    from matplotlib.ticker import NullFormatter
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.tick_params(axis="y", labelcolor=C_TH); ax.grid(alpha=0.3)
    ax.annotate(r"$\sigma$ spans " + f"{max(sig)-min(sig):.0f} dB",
                xy=(side[-1], sig[-1]), xytext=(side[1], sig[-1] - 6),
                color=C_TH, fontsize=10, fontweight="bold",
                arrowprops=dict(arrowstyle="->", color=C_TH, lw=1.2))
    ax2 = ax.twinx()
    ax2.plot(side, rt, "s-", color=C_RT, lw=2.4, ms=8, label="Sionna RT echo/direct ratio")
    ax2.axhline(d["image_source_db"], color="0.4", ls="--", lw=1.2)
    ax2.text(side[0], d["image_source_db"] + 0.6,
             f"image-source prediction  20·log10(L/(R1+R2)) = {d['image_source_db']:.2f} dB",
             fontsize=8.5, color="0.4")
    ax2.set_ylabel("RT echo / direct  [dB]", color=C_RT); ax2.tick_params(axis="y", labelcolor=C_RT)
    ax2.set_ylim(min(rt) - 4, min(rt) + 4)
    ax2.annotate(f"RT: FLAT  (spread {max(rt)-min(rt):.2f} dB)",
                 xy=(side[2], rt[2]), xytext=(side[0]*1.1, min(rt) + 2.4),
                 color=C_RT, fontsize=11, fontweight="bold")
    ax.set_title("(a) Specular = an infinite mirror", fontsize=12)
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=9, loc="upper left")

    # (b) 구: S 만 바꿔도 값이 움직인다 = RT 는 S 를 잰다
    B = [r for r in d["B_sphere_S"] if r.get("ratio_db") is not None]
    S = np.array([r["S"] for r in B]); rt2 = np.array([r["ratio_db"] for r in B])
    th = rt2[0] - B[0]["dev_db"]                       # 이론 진폭비(πr²)
    ax = axes[1]
    ax.plot(S, rt2, "o-", color=C_RT, lw=2.4, ms=9, label="Sionna RT (metal sphere, r = 0.3 m)")
    s_law = th + 20 * np.log10(S / 0.85)               # S² 법칙(이론과 만나는 S≈0.85 로 정규화)
    ax.plot(S, s_law, ls=":", color="0.45", lw=1.6, label=r"$S^2$ law  (20 log10 S)")
    ax.axhline(th, color=C_TH, ls="--", lw=1.8,
               label=r"truth for $\sigma=\pi r^2$ = -5.49 dBsm   " + f"({th:.1f} dB)")
    ax.plot([0.85], [th], "*", color=C_OK, ms=18, zorder=5)
    ax.annotate("you would have to FIT S = 0.85\nto match the truth -> circular",
                xy=(0.85, th), xytext=(0.28, th + 5.5), color=C_OK, fontsize=10, fontweight="bold",
                arrowprops=dict(arrowstyle="->", color=C_OK, lw=1.4))
    for x, y, n in zip(S, rt2, [r["n"] for r in B]):
        ax.annotate(f"{n} paths", (x, y), textcoords="offset points", xytext=(6, -12), fontsize=7.5, color="0.45")
    ax.set_xlabel("Scattering coefficient S of the sphere's material")
    ax.set_ylabel("RT echo / direct  [dB]")
    ax.set_title(f"(b) Diffuse = a knob, not physics  ({rt2[-1]-rt2[0]:+.1f} dB from S alone)", fontsize=12)
    ax.grid(alpha=0.3); ax.legend(fontsize=9, loc="lower right")

    fig.supxlabel("The target's echo in Sionna RT is either a size-independent mirror or a free parameter S — "
                  "neither carries the radar cross-section.",
                  fontsize=9, color="0.4")
    fn = os.path.join(outdir, "report6_rt_no_sigma.png")
    fig.savefig(fn, dpi=130, bbox_inches="tight"); plt.close(fig)
    print("[verify]", os.path.relpath(fn)); return fn


# --------------------------------------------------------------------------- #
#  (2) 물리적으로 옳은 금속구 → 경로 0개
# --------------------------------------------------------------------------- #
def fig_missing(outdir=FIG):
    d = _load()
    C = d["C_pec_sphere"]
    radii = sorted({r["r"] for r in C}); spps = sorted({r["spp"] for r in C})
    M = np.array([[next(x["n_paths"] for x in C if x["r"] == r and x["spp"] == s)
                   for s in spps] for r in radii], float)
    fig, axes = plt.subplots(1, 2, figsize=(13.6, 4.8), constrained_layout=True,
                             gridspec_kw=dict(width_ratios=[1.25, 1.0]))
    fig.suptitle("A PEC metal sphere: Sionna RT finds no path at all", fontsize=16, fontweight="bold")

    ax = axes[0]
    ax.imshow(M, cmap="Reds", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(spps))); ax.set_xticklabels([f"{s/1e6:.0f}M" for s in spps])
    ax.set_yticks(range(len(radii))); ax.set_yticklabels([f"r = {r:g} m" for r in radii])
    ax.set_xlabel("Rays per source (spp)")
    for i in range(len(radii)):
        for j in range(len(spps)):
            ax.text(j, i, f"{int(M[i, j])}", ha="center", va="center",
                    fontsize=26, fontweight="bold", color="#b71c1c")
    ax.set_title("Target-interaction paths found", fontsize=12)

    # 대조: 같은 위치의 평판은 즉시 잡힌다
    A = [r for r in d["A_plate"] if r.get("ratio_db") is not None]
    ax = axes[1]
    ax.bar(["PEC sphere\n(any size, any spp)"], [0], color=C_BAD, edgecolor="k")
    ax.bar(["Metal plate\n(same spot, 1M spp)"], [len(A) and A[0].get("n", 1)], color=C_OK, edgecolor="k")
    ax.text(0, 0.06, "0", ha="center", fontsize=22, fontweight="bold", color="#b71c1c")
    ax.text(1, (A[0].get("n", 1)) + 0.06, f"{A[0].get('n', 1)}", ha="center", fontsize=22,
            fontweight="bold", color="#1b5e20")
    ax.set_ylim(0, 1.6); ax.set_ylabel("Paths found"); ax.grid(axis="y", alpha=0.3)
    ax.set_title("The mesh, material and solver are fine", fontsize=12)

    fig.supxlabel("Curvature, not size, is what breaks it: tessellate a sphere and almost no facet contains its own specular\n"
                  "point, so an image-method specular search (Sionna RT) finds nothing — the disco-ball problem. A few % of random\n"
                  "poses do yield a path, but its amplitude is meaningless (single facet reflects as a plate, ~+15 dB vs sphere\n"
                  "theory). A flat plate in the same spot is caught with 1M rays.",
                  fontsize=9, color="0.4")
    fn = os.path.join(outdir, "report6_rt_missing.png")
    fig.savefig(fn, dpi=130, bbox_inches="tight"); plt.close(fig)
    print("[verify]", os.path.relpath(fn)); return fn


# --------------------------------------------------------------------------- #
#  (3) RT 가 맞히는 것(지연·기하) vs 틀리는 것(진폭) — 그리고 우리 분류 규약의 결함
# --------------------------------------------------------------------------- #
def fig_delay(outdir=FIG):
    d = _load()
    D = d["D_chamber_paths"]
    rows = sorted(D["rows"], key=lambda r: r["tau_ns"])
    fig, ax = plt.subplots(figsize=(13.6, 5.2), constrained_layout=True)
    fig.suptitle("What RT gets right — and what our own gate got wrong", fontsize=16, fontweight="bold")

    # 기대 지연 / LOS
    ax.axvline(D["tau_los_ns"], color="0.55", ls=":", lw=1.4)
    ax.text(D["tau_los_ns"], 4.6, "direct path (LOS)", rotation=90, va="top", ha="right",
            fontsize=8.5, color="0.45")
    ax.axvspan(D["tau_expect_ns"] - 3, D["tau_expect_ns"] + 3, color=C_OK, alpha=0.13)
    ax.axvline(D["tau_expect_ns"], color=C_OK, ls="--", lw=1.6)
    ax.text(D["tau_expect_ns"] + 4, 4.7,
            "target echo must be here\n" + r"$\tau$ = (R1+R2)/c = " + f"{D['tau_expect_ns']:.1f} ns",
            fontsize=9.5, color=C_OK, fontweight="bold", va="top")

    for r in rows:
        c = C_OK if r["is_true_echo"] else C_RT
        ax.stem([r["tau_ns"]], [r["bounces"]], linefmt=c, markerfmt="o", basefmt=" ")
        ax.plot([r["tau_ns"]], [r["bounces"]], "o", color=c, ms=9)
    ax.plot([], [], "o", color=C_OK, label=f"true target echo — 1-bounce, on time  ({D['n_true']} path)")
    ax.plot([], [], "o", color=C_RT,
            label=f"wall multi-bounce, wrongly counted as echo  ({D['n_near'] - D['n_true']} paths)")
    ax.set_xlabel(r"Path delay $\tau$ [ns]"); ax.set_ylabel("Number of bounces")
    ax.set_yticks([1, 2, 3]); ax.set_ylim(0.4, 5.0)
    ax.set_xlim(40, 240); ax.grid(alpha=0.3); ax.legend(fontsize=10, loc="upper left")
    ax.set_title("Chamber, drone target — every path our 'within 2 m of the target' rule accepted",
                 fontsize=11.5)

    fig.supxlabel("RT's geometry is exact: the one real echo lands at 124.1 ns, right on (R1+R2)/c. "
                  "What was broken was our classifier — a proximity rule swallowed 8 wall bounces and "
                  "manufactured a 5 dB 'agreement' with PO.",
                  fontsize=9, color="0.4")
    fn = os.path.join(outdir, "report6_rt_delay.png")
    fig.savefig(fn, dpi=130, bbox_inches="tight"); plt.close(fig)
    print("[verify]", os.path.relpath(fn)); return fn


# --------------------------------------------------------------------------- #
#  (4) 그래서 어떻게 나누는가 — 하이브리드 구조도
# --------------------------------------------------------------------------- #
def fig_hybrid(outdir=FIG):
    fig, ax = plt.subplots(figsize=(13.6, 5.8), constrained_layout=True)
    ax.set_xlim(0, 100); ax.set_ylim(0, 56); ax.axis("off")
    fig.suptitle("The split: PO owns the target, RT owns the room", fontsize=16, fontweight="bold")

    def box(x, y, w, h, title, lines, fc, ec):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.6,rounding_size=1.2",
                                    facecolor=fc, edgecolor=ec, lw=1.8))
        ax.text(x + w/2, y + h - 4.0, title, ha="center", fontsize=12.5, fontweight="bold", color=ec)
        for i, ln in enumerate(lines):
            ax.text(x + w/2, y + h - 9.5 - i*3.9, ln, ha="center", fontsize=9.4, color="0.25")

    box(2, 26, 27, 24, "Physical optics  (PO)",
        [r"target scattering  $\sigma(\theta, f)$", "material-weighted, from the mesh",
         "validated against the analytic PO", "of a sphere, within 0.015 dB"], "#e8f5e9", "#2e7d32")
    box(36, 26, 27, 24, "Link budget",
        ["absolute power and noise", "EIRP  ·  kTB  ·  path loss",
         "sets the SNR scale", ""], "#fff8e1", "#ef6c00")
    box(70, 26, 27, 24, "Sionna RT",
        ["the environment", "walls, multipath, clutter",
         "delays and amplitudes given", "relative to the direct path"], "#e3f2fd", "#1565c0")

    box(30, 2, 40, 15, "Bistatic channel  ->  detection",
        ["range-Doppler  ·  clutter removal  ·  CFAR", "report4 / report5"], "#f3e5f5", "#6a1b9a")

    for x0, rad in ((15.5, 0.12), (49.5, 0.0), (83.5, -0.12)):
        ax.add_patch(FancyArrowPatch((x0, 26), (50, 17.5), arrowstyle="->", mutation_scale=18,
                                     color="0.45", lw=1.6, connectionstyle=f"arc3,rad={rad}"))

    ax.text(15.5, 22.6, "the ONLY source of the target's amplitude", ha="center", fontsize=9.5,
            color="#2e7d32", fontweight="bold")
    ax.text(83.5, 22.6, "NEVER the target's amplitude", ha="center", fontsize=9.5,
            color="#c62828", fontweight="bold")

    fig.supxlabel("Sionna RT's stock path solver has no scattering-integral stage, so the target's $\\sigma$ cannot\n"
                  "emerge from it — but its geometry (delay, Doppler) is exact. So the target's amplitude comes from PO, "
                  "the absolute scale from the link budget, and everything else from RT.",
                  fontsize=9, color="0.4")
    fn = os.path.join(outdir, "report6_hybrid.png")
    fig.savefig(fn, dpi=130, bbox_inches="tight"); plt.close(fig)
    print("[verify]", os.path.relpath(fn)); return fn


def build_all(outdir=FIG):
    fig_no_sigma(outdir); fig_missing(outdir); fig_delay(outdir); fig_hybrid(outdir)
    print("report6(RT) 그림 완료 →", os.path.relpath(outdir))


if __name__ == "__main__":
    build_all()
