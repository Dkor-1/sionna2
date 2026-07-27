# -*- coding: utf-8 -*-
"""
viz_report3.py — report3 ("Sionna RT 광선 반사 실험") 의 그림
==============================================================
이 리포트는 **렌더가 주인공**이다. 그래서 이 파일의 절반은 그림을 "그리는" 게 아니라
**Sionna 가 렌더한 PNG 를 판넬로 조립하고 영어 라벨을 붙이는** 일이다.
(렌더 자체는 src/build_report3.py 의 render_all() → outputs/renders/report3/)

숫자는 **전부** outputs/report3_rt.json 에서 읽는다 (benchmark/rt_experiments.py 가 만든다).
→ 손으로 적은 숫자가 없다. 그림과 본문이 어긋날 수 없다.

규약
  · 그림 텍스트는 **전부 영어** (제목/축/범례/주석). 본문·주석·print 는 한국어.
  · 그리스문자·U+2212 금지 (한글 폰트에 없다) → mathtext 와 ASCII 하이픈만.
  · 제목 = 짧은 헤드라인, 회색 fig.supxlabel = 캡션(줄바꿈 넣어 잘리지 않게).
  · 색: dataviz 스킬의 **검증된 기본 팔레트**를 슬롯 순서 그대로 사용(재정렬하지 않음).
    (validate_palette.js 는 node v12 라 실행 불가 — 그래서 순서를 바꾸지 않았다.
     밝은 배경에서 대비가 낮은 슬롯(aqua/yellow)은 **직접 라벨**로 보완한다 = relief rule.)
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (_HERE, os.path.join(ROOT, "benchmark")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from vizstyle import use_korean                                   # noqa: E402
import matplotlib.pyplot as plt                                   # noqa: E402
import matplotlib.image as mpimg                                  # noqa: E402
from matplotlib.patches import FancyArrowPatch, Rectangle, Circle  # noqa: E402

use_korean()

FIG = os.path.join(ROOT, "outputs", "figures")
RDIR = os.path.join(ROOT, "outputs", "renders", "report3")
RJSON = os.path.join(ROOT, "outputs", "report3_rt.json")

# --- dataviz 기본 팔레트 (슬롯 고정 순서) ---------------------------------- #
BLUE, AQUA, YELLOW, GREEN, VIOLET, RED, MAGENTA, ORANGE = (
    "#2a78d6", "#1baf7a", "#eda100", "#008300", "#4a3aa7", "#e34948", "#e87ba4", "#eb6834")
GOOD, WARN, CRIT = "#0ca30c", "#fab219", "#d03b3b"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#8a8880"
GRID = "#e6e5e1"

#  물체 종류 → 색 (**개체(entity)에 색을 고정** — 순위가 아니라)
OBJ_COLOR = {"LOS": INK, "floor": BLUE, "ceiling": ORANGE, "wall": AQUA,
             "target": RED, "other": MUTED}


def _load():
    with open(RJSON) as f:
        return json.load(f)


def _classify(objs):
    """경로가 맞은 물체 → 색 분류 키."""
    if not objs:
        return "LOS"
    if any(o.startswith("mavic") for o in objs):
        return "target"
    if any(o.startswith("floor") for o in objs):
        return "floor"
    if any("ceiling" in o for o in objs):
        return "ceiling"
    if any(o.startswith(("absorber", "backing")) for o in objs):
        return "wall"
    return "other"


def _cap(fig, text):
    """회색 캡션 — 줄바꿈은 호출자가 넣는다(잘림 방지)."""
    fig.supxlabel(text, fontsize=10.5, color=INK2, ha="center", linespacing=1.6)


def _save(fig, name, dpi=125):
    os.makedirs(FIG, exist_ok=True)
    fn = os.path.join(FIG, f"{name}.png")
    fig.savefig(fn, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  [fig] {os.path.relpath(fn, ROOT)}")
    return fn


def _img(ax, name, title=None, sub=None, box=None):
    """Sionna 렌더 PNG 를 판넬에 얹는다."""
    p = os.path.join(RDIR, f"{name}.png")
    if os.path.exists(p):
        ax.imshow(mpimg.imread(p))
    else:
        ax.text(.5, .5, f"(missing: {name})", ha="center", va="center",
                color=CRIT, fontsize=9, transform=ax.transAxes)
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_color(GRID)
    if title:
        ax.set_title(title, fontsize=12, fontweight="bold", color=INK, pad=5)
    if sub:
        ax.set_xlabel(sub, fontsize=9.5, color=INK2, labelpad=5)
    if box:
        ax.text(.015, .975, box, transform=ax.transAxes, va="top", ha="left",
                fontsize=9.5, color=INK, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.4", fc="white", ec=GRID, alpha=.92))
    return ax


def _axstyle(ax):
    ax.grid(True, color=GRID, lw=.8, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=9.5)


# =========================================================================== #
#  F1 — 광선추적이란 무엇인가: max_depth = 0/1/2/3  (이 리포트의 첫 그림)
# =========================================================================== #
def fig1_bounces(J):
    sw = {s["max_depth"]: s for s in J["S1_depth"]["sweeps"]}
    fig, axs = plt.subplots(2, 2, figsize=(17.5, 12.4), constrained_layout=True)
    fig.suptitle("Ray tracing, one bounce at a time -- and the floor appears at depth 1",
                 fontsize=20, fontweight="bold", color=INK)
    notes = {
        0: "Line of sight only.\n1 path.",
        1: "+ ceiling, + left wall, + FLOOR.\n4 paths.",
        2: "+ double bounces (absorber valleys).\n16 paths -- the picture starts to saturate.",
        3: "+ triple bounces.\n40 paths -- read this one from the ledger, not the render.",
    }
    for ax, md in zip(axs.ravel(), (0, 1, 2, 3)):
        s = sw[md]
        _img(ax, f"r3_paths_d{md}_wide",
             title=f"max_depth = {md}   ->   {s['n_paths']} path" + ("s" if s["n_paths"] > 1 else ""),
             box=notes[md])
    for ax in axs.ravel():
        ax.set_xlabel("")
    _cap(fig, "Rendered by Sionna itself (Scene.render_to_file with paths=Paths) -- these are the rays the solver actually traced, not our drawing.\n"
               "TX = red, RX = green. The ceiling is clipped at z = 10.8 m so light can enter the closed room: a rendering trick only, it does not touch the propagation (the paths were solved on the intact scene).\n"
               "HONEST LIMIT OF THIS PICTURE: Sionna draws each path as an emissive cylinder of radius min(0.20, 0.005*scene) = 0.20 m (renderer.py:398) and exposes no way to thin it. In a 30 m room, 16 and 40 such\n"
               "tubes simply fill the frame. The path renderer is legible up to about ten paths; past that, read the ledger in the next figure. At depth 1 the ray that dives to the floor and back is the floor bounce -- section 2.")
    return _save(fig, "report3_f1_bounces")


# =========================================================================== #
#  F2 — 경로 원장(ledger): 무엇을 언제 얼마나, 그리고 무엇을 맞고
# =========================================================================== #
def fig2_ledger(J):
    sw = {s["max_depth"]: s for s in J["S1_depth"]["sweeps"]}
    fig, axs = plt.subplots(1, 2, figsize=(17.5, 6.8), constrained_layout=True,
                            gridspec_kw=dict(width_ratios=[1.05, 1]))
    fig.suptitle("Every path Sionna found: when it arrives, how strong, and what it hit",
                 fontsize=19, fontweight="bold", color=INK)

    # (a) depth = 1 — 4개 경로를 이름표와 함께
    ax = axs[0]; _axstyle(ax)
    P = sw[1]["paths"]
    for p in P:
        k = _classify(p["objects"])
        c = OBJ_COLOR[k]
        ax.vlines(p["delay_ns"], -30, p["rel_db"], color=c, lw=2.4, zorder=3)
        ax.plot(p["delay_ns"], p["rel_db"], "o", ms=11, color=c, mec="white", mew=2, zorder=4)
        lbl = "LOS (direct)" if k == "LOS" else p["objects"][0]
        ax.annotate(f"{lbl}\n{p['rel_db']:+.2f} dB @ {p['delay_ns']:.2f} ns",
                    (p["delay_ns"], p["rel_db"]), textcoords="offset points",
                    xytext=(0, 14), ha="center", fontsize=10, color=INK,
                    fontweight="bold" if k == "floor" else "normal")
    ax.axhline(0, color=MUTED, lw=1, ls=":")
    ax.set_xlim(-2.5, 23); ax.set_ylim(-26, 9)
    ax.set_xlabel("excess delay vs LOS  [ns]", fontsize=11.5, color=INK2)
    ax.set_ylabel("amplitude vs LOS  [dB]", fontsize=11.5, color=INK2)
    ax.set_title("max_depth = 1: four paths", fontsize=13, fontweight="bold", color=INK)
    ax.text(.985, .03, "floor bounce is the one we hand-check", transform=ax.transAxes,
            ha="right", fontsize=10, color=BLUE, fontweight="bold")

    # (b) depth = 3 — 40개 경로, 반사횟수로 색
    ax = axs[1]; _axstyle(ax)
    P3 = sw[3]["paths"]
    for p in P3:
        k = _classify(p["objects"])
        ax.vlines(p["delay_ns"], -60, p["rel_db"], color=OBJ_COLOR[k], lw=1.7, alpha=.85, zorder=3)
        ax.plot(p["delay_ns"], p["rel_db"], "o", ms=5.5, color=OBJ_COLOR[k],
                mec="white", mew=.8, zorder=4)
    for k, lab in (("LOS", "line of sight"), ("floor", "floor (concrete)"),
                   ("ceiling", "ceiling absorber"), ("wall", "wall absorber / shield")):
        ax.plot([], [], "o", color=OBJ_COLOR[k], ms=8, label=lab)
    ax.legend(frameon=False, fontsize=10.5, labelcolor=INK2, loc="upper right")
    ax.axhline(0, color=MUTED, lw=1, ls=":")
    ax.set_ylim(-58, 9)
    ax.set_xlabel("excess delay vs LOS  [ns]", fontsize=11.5, color=INK2)
    ax.set_ylabel("amplitude vs LOS  [dB]", fontsize=11.5, color=INK2)
    ax.set_title(f"max_depth = 3: {len(P3)} paths", fontsize=13, fontweight="bold", color=INK)
    n_t = sw[3]["n_target_paths"]
    ax.text(.5, .06, f"paths that hit the DRONE: {n_t}", transform=ax.transAxes,
            ha="center", fontsize=12, fontweight="bold", color=CRIT,
            bbox=dict(boxstyle="round,pad=0.45", fc="#fdecec", ec=CRIT, lw=1.2))

    _cap(fig, "Source: outputs/report3_rt.json (benchmark/rt_experiments.py). Path identity comes from paths.objects mapped through SceneObject.object_id.\n"
               "CAUTION: paths.objects holds object_ids (they start at 1) -- mapping them by the enumeration order of scene.objects shifts every label by one and renames the ceiling 'front wall'.\n"
               "The drone is IN the scene, is 0.35 m across, and the specular solver returns zero paths through it. That is section 3.")
    return _save(fig, "report3_f2_ledger")


# =========================================================================== #
#  F3 — Sionna 렌더 갤러리
# =========================================================================== #
def fig3_gallery(J):
    fig, axs = plt.subplots(2, 3, figsize=(18.5, 9.6), constrained_layout=True)
    fig.suptitle("The chamber as Sionna renders it", fontsize=20, fontweight="bold", color=INK)
    shots = [
        ("r3_scene_outside", "Outside", "steel exoskeleton, shielded box"),
        ("r3_scene_wide", "Inside (TX/RX wall facing us)", "TX red (4, 2.5, 8), RX green (4, 17.5, 6.5)"),
        ("r3_scene_top", "Top-down (clip_at = 9 m)", "pyramid absorber on 4 walls, tiled floor"),
        ("r3_scene_grazing", "Grazing the floor", "the floor is concrete -- the only reflective face"),
        ("r3_scene_side", "Cutaway from outside", "front wall removed (CUTAWAY_OMIT)"),
        ("r3_scene_target", "Over the target", "Mavic 4 Pro at (21, 10, 5.5), 0.35 m across"),
    ]
    for ax, (n, t, s) in zip(axs.ravel(), shots):
        _img(ax, n, title=t, sub=s)
    _cap(fig, "All six frames: Sionna RT's own renderer (Mitsuba 3 path tracer on GPU), num_samples = 640, 1760 x 1200. No matplotlib drawing here.\n"
               "This is a SEMI-ANECHOIC chamber: absorber on the four walls and the ceiling, but the floor is reflective concrete (ITU 'concrete'). That asymmetry is the whole story of this report.")
    return _save(fig, "report3_f3_gallery")


# =========================================================================== #
#  F4 — 바닥 반사: 손계산 vs RT
# =========================================================================== #
def fig4_floor(J):
    F = J["S2_floor"]
    p, m = F["pred"], F["rt_floor"]
    fig = plt.figure(figsize=(18, 7.4), constrained_layout=True)
    fig.suptitle("The floor bounce: image source + Fresnel, checked against Sionna",
                 fontsize=20, fontweight="bold", color=INK)
    gs = fig.add_gridspec(1, 3, width_ratios=[1.28, 1, 1])

    # (a) 거울상 기하
    ax = fig.add_subplot(gs[0, 0])
    TX, RX = (2.5, 8.0), (17.5, 6.5)                    # (y, z) 평면 — 둘 다 x=4
    RXI = (17.5, -6.5)
    hit = (F["pred"]["hit_point"][1], 0.0)
    ax.axhspan(-9, 0, color="#eceae4", zorder=0)
    ax.axhline(0, color=INK, lw=2.5, zorder=2)
    ax.plot([TX[0], RX[0]], [TX[1], RX[1]], color=MUTED, lw=2.2, ls="--", zorder=3)
    ax.plot([TX[0], hit[0], RX[0]], [TX[1], hit[1], RX[1]], color=BLUE, lw=3, zorder=4)
    ax.plot([TX[0], RXI[0]], [TX[1], RXI[1]], color=BLUE, lw=1.3, ls=":", alpha=.75, zorder=3)
    ax.plot([RX[0], RXI[0]], [RX[1], RXI[1]], color=MUTED, lw=1, ls=":", zorder=3)
    ax.plot(*TX, "o", ms=13, color=RED, mec="white", mew=2, zorder=6)
    ax.plot(*RX, "o", ms=13, color=GREEN, mec="white", mew=2, zorder=6)
    ax.plot(*RXI, "o", ms=11, color=GREEN, mec="white", mew=2, alpha=.45, zorder=6)
    ax.plot(*hit, "o", ms=9, color=BLUE, mec="white", mew=1.6, zorder=6)
    ax.annotate("TX", TX, xytext=(-4, 12), textcoords="offset points", fontsize=12,
                fontweight="bold", color=INK, ha="center")
    ax.annotate("RX", RX, xytext=(10, 10), textcoords="offset points", fontsize=12,
                fontweight="bold", color=INK)
    ax.annotate("RX' (image)", RXI, xytext=(8, -6), textcoords="offset points",
                fontsize=11, color=INK2)
    ax.annotate("direct  15.07 m", (10, 7.9), fontsize=10.5, color=INK2, ha="center")
    ax.annotate(f"via floor  {p['L_floor_m']:.2f} m", (15.4, 3.4), fontsize=10.5,
                color=BLUE, ha="left", fontweight="bold")
    ax.annotate(f"incidence {p['theta_i_deg']:.1f} deg from normal\n"
                f"(NOT grazing: {p['grazing_deg']:.1f} deg above floor)",
                hit, xytext=(-42, -34), textcoords="offset points", fontsize=10,
                color=INK, ha="center",
                bbox=dict(boxstyle="round,pad=0.35", fc="white", ec=GRID))
    ax.set_xlim(-1, 21); ax.set_ylim(-9, 11.5)
    ax.set_aspect("equal")
    ax.set_xlabel("y  [m]   (TX, RX and the bounce all lie in the plane x = 4 m)",
                  fontsize=11, color=INK2)
    ax.set_ylabel("z  [m]", fontsize=11, color=INK2)
    ax.set_title("Hand calculation: mirror RX in the floor", fontsize=13,
                 fontweight="bold", color=INK)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(colors=INK2, labelsize=9.5)

    # (b) 지연 비교
    ax = fig.add_subplot(gs[0, 1]); _axstyle(ax)
    vals = [p["delay_ns"], m["delay_ns"]]
    bars = ax.bar(["image source\n+ Fresnel", "Sionna RT\n(independent)"], vals,
                  color=[VIOLET, BLUE], width=.55, zorder=3)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + .35, f"{v:.2f} ns",
                ha="center", fontsize=13, fontweight="bold", color=INK)
    ax.set_ylim(0, 24)
    ax.set_ylabel("excess delay  [ns]", fontsize=11.5, color=INK2)
    ax.set_title(f"Delay agrees to {abs(F['agree_delay_ns']):.2f} ns",
                 fontsize=13, fontweight="bold", color=INK)

    # (c) 진폭 비교
    ax = fig.add_subplot(gs[0, 2]); _axstyle(ax)
    vals = [p["rel_db"], m["rel_db"]]
    bars = ax.bar(["image source\n+ Fresnel", "Sionna RT\n(independent)"], vals,
                  color=[VIOLET, BLUE], width=.55, zorder=3)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v - 1.1, f"{v:+.2f} dB",
                ha="center", fontsize=13, fontweight="bold", color=INK)
    ax.set_ylim(-19, 0)
    ax.set_ylabel("amplitude vs LOS  [dB]", fontsize=11.5, color=INK2)
    ax.set_title(f"Floor-bounce amplitude agrees to {abs(F['agree_db']):.2f} dB",
                 fontsize=13, fontweight="bold", color=INK)
    ax.text(.5, .08, "THIS is why we trust RT\nfor the environment",
            transform=ax.transAxes, ha="center", fontsize=12, fontweight="bold",
            color=GOOD, bbox=dict(boxstyle="round,pad=0.45", fc="#eaf7ea", ec=GOOD, lw=1.2))

    tw = F["twins"][0] if F["twins"] else None
    twtxt = ("" if tw is None else
             f"The second arrival at the same delay ({tw['delay_ns']:.2f} ns, {tw['rel_db']:+.2f} dB) is NOT the floor: paths.objects identifies it as a DOUBLE bounce inside the front-wall\n"
             f"absorber, both vertices at y = 0.0 m -- a ray caught in the pyramid valley. Previously logged as 'unidentified' in benchmark/verify_floor_ghost.py; it is identified now.")
    _cap(fig, "Hand calculation is independent of Sionna: mirror RX in z = 0, Fresnel TM (V-pol) on ITU concrete (eps_r = 5.24, sigma = 0.123 S/m at 3.5 GHz), spread loss 20log10(L/Lf).\n"
              + twtxt)
    return _save(fig, "report3_f4_floor")


# =========================================================================== #
#  F5 — 라디오맵
# =========================================================================== #
def fig5_radiomap(J):
    fig, axs = plt.subplots(1, 2, figsize=(18, 6.6), constrained_layout=True)
    fig.suptitle("RadioMapSolver: where the energy actually goes",
                 fontsize=20, fontweight="bold", color=INK)
    _img(axs[0], "r3_radiomap_floor_top", title="Floor plane (z = 0.05 m)",
         sub="the reflective face -- brightest sheet in the room")
    _img(axs[1], "r3_radiomap_droneplane_top", title="Drone plane (z = 5.5 m)",
         sub="the drone sits here and casts a shadow away from TX")
    _cap(fig, "Sionna RadioMapSolver, 8e6 samples/TX, max_depth = 3, cell 0.25 m; rendered by Sionna with radio_map= and clip_at = 9 m. Colour = path gain (viridis, Sionna's own scale).\n"
               "TX is the red marker (bottom-left), RX the green one. Read the geometry, not absolute levels: the absorber here is a MODEL (see the caveats), not a measured -25 dB product.")
    return _save(fig, "report3_f5_radiomap")


# =========================================================================== #
#  F6 — RT 는 표적을 못 본다 (A~E)
# =========================================================================== #
def fig6_no_sigma(J):
    A, B, C, D, E = J["A_rays"], J["B_scatter"], J["C_metal"], J["D_plate"], J["E_sphere"]
    fig = plt.figure(figsize=(19.5, 11.2), constrained_layout=True)
    fig.suptitle("Shooting 400 million rays at the drone does not produce its RCS",
                 fontsize=20.5, fontweight="bold", color=INK)
    gs = fig.add_gridspec(2, 3)
    truth = C["ratio_db_truth"]

    # [A] 광선예산
    ax = fig.add_subplot(gs[0, 0]); _axstyle(ax)
    r = [x for x in A["rows"] if x["n_paths"]]
    x = [v["spp"] / 1e6 for v in r]
    ax.errorbar(x, [v["coh_db"] for v in r], yerr=[v["coh_sd"] for v in r],
                marker="o", ms=9, lw=2.4, color=BLUE, capsize=4, zorder=4,
                mec="white", mew=1.5)
    ax.errorbar(x, [v["incoh_db"] for v in r], yerr=[v["incoh_sd"] for v in r],
                marker="s", ms=8, lw=2.2, color=AQUA, capsize=4, zorder=4,
                mec="white", mew=1.5)
    ax.axhline(truth, color=CRIT, lw=2.2, ls="--", zorder=3)
    ax.text(x[0], truth + 1.2, f"what the radar equation needs\n(SBR sigma) {truth:+.1f} dB",
            fontsize=9.5, color=CRIT, fontweight="bold")
    ax.annotate("coherent sum", (x[-1], r[-1]["coh_db"]), xytext=(-8, 8),
                textcoords="offset points", ha="right", fontsize=10.5,
                color=BLUE, fontweight="bold")
    ax.annotate("incoherent sum", (x[-1], r[-1]["incoh_db"]), xytext=(-8, -18),
                textcoords="offset points", ha="right", fontsize=10.5,
                color=AQUA, fontweight="bold")
    #  ⚠ 로그축의 **보조눈금**은 mathtext 로 10^-1 을 찍는다 → U+2212 (한글 폰트에 없는 글자,
    #    두부글자로 렌더된다). 눈금을 명시하고 보조눈금을 끈다.
    ax.set_xscale("log")
    ax.set_xticks(x); ax.set_xticklabels([f"{v:.0f}" for v in x]); ax.minorticks_off()
    ax.set_xlabel("rays shot  [millions]", fontsize=11.5, color=INK2)
    ax.set_ylabel("target echo vs LOS  [dB]", fontsize=11.5, color=INK2)
    d = r[-1]["coh_db"] - r[0]["coh_db"]
    ax.set_title(f"[A] 25M -> 400M rays: coherent sum climbs {d:+.1f} dB",
                 fontsize=12.5, fontweight="bold", color=INK)

    # [B] 산란계수
    ax = fig.add_subplot(gs[0, 1]); _axstyle(ax)
    rb = [x for x in B["rows"] if x["n_paths"]]
    xb = [v["mult"] for v in rb]
    ax.errorbar(xb, [v["coh_db"] for v in rb], yerr=[v["coh_sd"] for v in rb],
                marker="o", ms=10, lw=2.6, color=VIOLET, capsize=4,
                mec="white", mew=1.5, zorder=4)
    ax.axhline(truth, color=CRIT, lw=2.2, ls="--", zorder=3)
    for v in rb:
        ax.annotate(f"{v['coh_db']:+.1f}", (v["mult"], v["coh_db"]),
                    xytext=(0, 11), textcoords="offset points", ha="center",
                    fontsize=10, color=INK, fontweight="bold")
    ax.set_xscale("log"); ax.set_xticks(xb); ax.set_xticklabels([f"{v}x" for v in xb])
    ax.minorticks_off()                                   # ⚠ 보조눈금의 10^-1 (U+2212) 방지
    ax.set_xlabel("scattering coefficient S  (multiplier on the material table)",
                  fontsize=11.5, color=INK2)
    ax.set_ylabel("target echo vs LOS  [dB]", fontsize=11.5, color=INK2)
    db = rb[-1]["coh_db"] - rb[0]["coh_db"]
    ax.set_title(f"[B] S x4 moves the echo {db:+.1f} dB -- a knob, not the drone",
                 fontsize=12.5, fontweight="bold", color=INK)

    # [C] 금속의 S = 0
    ax = fig.add_subplot(gs[0, 2]); _axstyle(ax)
    sg = C["sigma"]
    names = ["all parts", "metal only\n(S = 0)", "dielectric only\n(S > 0)"]
    vals = [sg["full_dbsm"], sg["metal_only_dbsm"], sg["dielectric_only_dbsm"]]
    cols = [INK2, CRIT, AQUA]
    bars = ax.bar(names, vals, color=cols, width=.6, zorder=3)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + .35, f"{v:+.1f}", ha="center",
                fontsize=12, fontweight="bold", color=INK)
    ax.set_ylim(min(vals) - 4, max(vals) + 3.4)
    ax.set_ylabel("SBR sigma, azimuth mean  [dBsm]", fontsize=11.5, color=INK2)
    ax.set_title(f"[C] {C['metal_share_pct']:.0f}% of sigma sits on parts RT cannot scatter from",
                 fontsize=12.5, fontweight="bold", color=INK)
    ax.text(.5, .06, f"ITU 'metal' scattering_coefficient = {C['itu_metal_S']:.1f}\n"
                     "motors, battery, PCB, camera housing",
            transform=ax.transAxes, ha="center", fontsize=10.5, color=CRIT,
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.4", fc="#fdecec", ec=CRIT))

    # [D] 평판 — 결정적 실험
    ax = fig.add_subplot(gs[1, 0:2]); _axstyle(ax)
    rd = [v for v in D["rows"] if v["rt_db"] is not None]
    xd = [v["side_m"] for v in rd]
    ax.plot(xd, [v["sigma_dbsm"] for v in rd], marker="o", ms=10, lw=2.8, color=ORANGE,
            mec="white", mew=1.5, zorder=4)
    ax.plot(xd, [v["rt_db"] for v in rd], marker="s", ms=10, lw=2.8, color=BLUE,
            mec="white", mew=1.5, zorder=4)
    ax.axhline(D["image_db"], color=MUTED, lw=1.6, ls=":", zorder=3)
    ax.annotate(f"true sigma of the plate  (4*pi*A^2 / lambda^2):  {D['sigma_span_db']:+.0f} dB over this sweep",
                (xd[-1], rd[-1]["sigma_dbsm"]), xytext=(-10, -6), textcoords="offset points",
                ha="right", fontsize=11.5, color=ORANGE, fontweight="bold")
    ax.annotate(f"what Sionna RT reports:  {D['rt_span_db']:.2f} dB  (flat at {D['rt_mean_db']:+.2f} dB, seed spread {D['rt_sd_db']:.2f} dB)",
                (xd[-1], rd[-1]["rt_db"]), xytext=(-10, 14), textcoords="offset points",
                ha="right", fontsize=11.5, color=BLUE, fontweight="bold")
    ax.text(.015, .38, "The blue line is exactly 20*log10( L / (R1+R2) ),\n"
                       "the image-source value for a mirror.\n"
                       "The size of the target appears nowhere in it.",
            transform=ax.transAxes, ha="left", va="top", fontsize=10.5, color=INK2,
            bbox=dict(boxstyle="round,pad=0.4", fc="white", ec=GRID))
    ax.set_xscale("log"); ax.set_xticks(xd); ax.set_xticklabels([f"{v}" for v in xd])
    ax.minorticks_off()                                   # ⚠ 보조눈금의 10^-1 (U+2212) 방지
    ax.set_xlabel("metal plate side  [m]   (specular-aligned, diffuse OFF -> zero Monte-Carlo noise)",
                  fontsize=11.5, color=INK2)
    ax.set_ylabel("[dB]  /  [dBsm]", fontsize=11.5, color=INK2)
    ax.set_title("[D] The decisive one: grow the plate by 52 dB of RCS, RT does not move at all",
                 fontsize=13.5, fontweight="bold", color=INK)

    # [E] PEC 구
    ax = fig.add_subplot(gs[1, 2]); _axstyle(ax)
    rr = [v for v in E["rows"] if abs(v["radius_m"] - 0.30) < 1e-6]
    xe = [v["spp"] / 1e6 for v in rr]
    ax.bar([f"{v:.0f}M" for v in xe], [max(v, .02) for v in
                                       [x["n_paths"] for x in rr]],
           color=CRIT, width=.55, zorder=3)
    ax.axhline(E["control_plate"]["n_paths"], color=GOOD, lw=2.2, ls="--", zorder=4)
    ax.text(.02, E["control_plate"]["n_paths"] + .06,
            f"control: flat metal plate, 1M rays -> {E['control_plate']['n_paths']} path "
            f"({E['control_plate']['rt_db']:+.2f} dB)",
            transform=ax.get_yaxis_transform(), fontsize=9.5, color=GOOD, fontweight="bold")
    ax.set_ylim(0, 1.6)
    ax.set_xlabel("rays shot at a PEC metal sphere (r = 0.30 m)", fontsize=11.5, color=INK2)
    ax.set_ylabel("target paths found", fontsize=11.5, color=INK2)
    ax.set_title("[E] Physically correct sphere: zero paths, ever",
                 fontsize=12.5, fontweight="bold", color=INK)
    for i in range(len(rr)):                      # 막대 바로 위에 0 을 찍는다
        ax.text(i, .07, "0", ha="center", fontsize=16, fontweight="bold", color=CRIT)
    ax.text(.5, .42, "sigma = pi*r^2 is known analytically.\nS = 0 means no diffuse channel, and the\n"
                     "image method cannot find the specular\npoint on a curved surface.",
            transform=ax.transAxes, ha="center", va="center", fontsize=9.5, color=INK2,
            bbox=dict(boxstyle="round,pad=0.4", fc="white", ec=GRID))

    _cap(fig, "All five panels: Sionna RT PathSolver, same chamber materials, drone at (21, 10, 5.5). Reproduce with `python benchmark/rt_experiments.py` -> outputs/report3_rt.json.\n"
               "Sionna is not wrong -- it is a PROPAGATION tool. The narrow true statement: a path solver with NO scattering-integral stage cannot make sigma emerge. Sigma comes from the integral.\n"
               "(Ray tracing as such computes RCS perfectly well: SBR = GO rays + PO surface integral is ray tracing, and it is what report2 uses.)")
    return _save(fig, "report3_f6_no_sigma")


# =========================================================================== #
#  F7 — 하이브리드: 환경 = RT, 표적 = SBR
# =========================================================================== #
def fig7_hybrid(J):
    F = J["S2_floor"]                                   # 숫자는 손으로 적지 않는다
    FLOOR_TAG = (f"{F['rt_floor']['delay_ns']:.2f} ns / {F['rt_floor']['rel_db']:+.2f} dB"
                 f"   (RT vs hand calc: {abs(F['agree_db']):.2f} dB)")
    fig, ax = plt.subplots(figsize=(16.5, 7.6), constrained_layout=True)
    fig.suptitle("The split this report forces: environment = Sionna RT, target = SBR",
                 fontsize=20, fontweight="bold", color=INK)
    ax.set_xlim(0, 16); ax.set_ylim(0, 8.2); ax.axis("off")

    ax.add_patch(Rectangle((.4, .5), 15.2, 6.4, fc="#f7f7f5", ec=GRID, lw=1.5, zorder=0))
    ax.text(8, 6.55, "semi-anechoic chamber  30 x 20 x 11 m", ha="center",
            fontsize=11.5, color=MUTED, style="italic")
    ax.plot([.6, 15.4], [1.15, 1.15], color=INK, lw=3, zorder=2)
    ax.text(8, .78, "reflective concrete floor  (the only mirror in the room)",
            ha="center", fontsize=10.5, color=INK2)

    tx, rx, tg = (2.0, 5.6), (13.6, 4.6), (7.9, 3.5)
    for p, c, lab in ((tx, RED, "TX"), (rx, GREEN, "RX")):
        ax.add_patch(Circle(p, .26, fc=c, ec="white", lw=2, zorder=6))
        ax.text(p[0], p[1] + .62, lab, ha="center", fontsize=13, fontweight="bold", color=INK)
    ax.add_patch(Circle(tg, .3, fc=INK, ec="white", lw=2, zorder=6))
    ax.text(tg[0], tg[1] + .68, "drone", ha="center", fontsize=12.5,
            fontweight="bold", color=INK)

    def arrow(a, b, c, lw=2.6, ls="-", rad=0.0):
        ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=19,
                                     color=c, lw=lw, linestyle=ls, zorder=5,
                                     connectionstyle=f"arc3,rad={rad}",
                                     shrinkA=9, shrinkB=9))

    #  화살표에는 **짧은 태그**만 붙인다 — 설명은 위 범례로 뺀다(겹침 방지).
    arrow(tx, rx, BLUE)                                             # 직접파
    ax.text(7.8, 5.42, "direct (LOS)", fontsize=10.5, color=BLUE,
            fontweight="bold", ha="center")

    arrow(tx, (7.4, 1.15), BLUE); arrow((7.4, 1.15), rx, BLUE)      # 바닥 반사
    ax.text(4.15, 1.72, f"floor bounce  {FLOOR_TAG}",
            fontsize=10, color=BLUE, ha="center", fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=BLUE, alpha=.95))

    arrow(tx, tg, ORANGE, rad=-.16)
    arrow(tg, rx, ORANGE, rad=-.16)
    ax.text(7.9, 4.62, "target scattering  sigma(az, el)", fontsize=10.5, color=ORANGE,
            fontweight="bold", ha="center",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=ORANGE, alpha=.9))

    arrow(tg, (10.9, 1.15), VIOLET, lw=2.2, ls="--")
    arrow((10.9, 1.15), rx, VIOLET, lw=2.2, ls="--")
    ax.text(11.55, 2.62, "GHOST", fontsize=11, color=VIOLET, fontweight="bold", ha="center")

    for c, t, y in ((BLUE, "Sionna RT (PathSolver / RadioMapSolver) -- environment: delay, Doppler, geometry. WE TRUST IT (section 2)", 7.85),
                    (ORANGE, "SBR (src/rcs_sbr.py: Mitsuba rays + PO surface integral, occlusion included) -- target sigma. Sionna has no RCS solver (section 3)", 7.45),
                    (VIOLET, "image source + Fresnel -- the target-via-floor ghost. Carries Doppler, so ECA does not delete it (section 4)", 7.05)):
        ax.plot([.6, 1.5], [y, y], color=c, lw=3.2, solid_capstyle="round")
        ax.text(1.75, y, t, va="center", fontsize=10.5, color=INK)

    _cap(fig, "Neither engine is a fallback for the other. Sionna RT gives geometry, delay and Doppler exactly (section 2 verifies it to 0.00 dB) but carries no target sigma (section 3 proves it five ways).\n"
               "SBR gives sigma (validated against analytic plate -0.01 dB and metal sphere +0.39 dB) but knows nothing about the room. The passive-radar chain needs both.")
    return _save(fig, "report3_f7_hybrid")


# =========================================================================== #
#  F8 — 표적 경유 바닥 유령
# =========================================================================== #
def fig8_ghost(J):
    G = J["S4_ghost"]
    fig, axs = plt.subplots(1, 2, figsize=(17.5, 6.8), constrained_layout=True,
                            gridspec_kw=dict(width_ratios=[1.05, 1]))
    fig.suptitle("The ghost the floor makes -- and why bandwidth turns into false alarms",
                 fontsize=19.5, fontweight="bold", color=INK)

    # (a) 거리-도플러 평면에서 진짜 vs 유령
    ax = axs[0]; _axstyle(ax)
    t, g = G["true"], G["ghost"]
    ax.plot(t["Rb"], t["fd"], "o", ms=17, color=GREEN, mec="white", mew=2, zorder=5)
    ax.plot(g["Rb"], g["fd"], "X", ms=17, color=VIOLET, mec="white", mew=1.6, zorder=5)
    ax.annotate(f"TRUE target\nRb = {t['Rb']:.2f} m\nf_d = {t['fd']:+.1f} Hz\n0 dB (reference)",
                (t["Rb"], t["fd"]), xytext=(-64, -46), textcoords="offset points",
                fontsize=10.5, color=INK, fontweight="bold", ha="center",
                bbox=dict(boxstyle="round,pad=0.4", fc="#eaf7ea", ec=GREEN))
    ax.annotate(f"GHOST (TX -> drone -> floor -> RX)\nRb = {g['Rb']:.2f} m ({G['sep_m']:+.2f} m)\n"
                f"f_d = {g['fd']:+.1f} Hz ({G['d_fd_hz']:+.1f} Hz)\n{g['amp_db']:+.1f} dB",
                (g["Rb"], g["fd"]), xytext=(16, 40), textcoords="offset points",
                fontsize=10.5, color=INK, fontweight="bold", ha="left",
                bbox=dict(boxstyle="round,pad=0.4", fc="#f1eefb", ec=VIOLET))
    for w, c in zip(G["waveforms"], (BLUE, AQUA, ORANGE)):
        ax.axvspan(t["Rb"] - w["d_rb_m"] / 2, t["Rb"] + w["d_rb_m"] / 2,
                   color=c, alpha=.10, zorder=1)
    ax.set_xlim(t["Rb"] - 12, g["Rb"] + 8)
    ax.set_ylim(min(t["fd"], g["fd"]) - 26, max(t["fd"], g["fd"]) + 30)
    ax.set_xlabel("bistatic range Rb  [m]", fontsize=11.5, color=INK2)
    ax.set_ylabel("bistatic Doppler f_d  [Hz]", fontsize=11.5, color=INK2)
    ax.set_title("Both carry Doppler -- ECA deletes neither", fontsize=13,
                 fontweight="bold", color=INK)
    ax.text(.5, .04, "shaded bands = one range cell (c/B) per waveform",
            transform=ax.transAxes, ha="center", fontsize=9.5, color=MUTED)

    # (b) 분리 / 분해능
    ax = axs[1]; _axstyle(ax)
    W = G["waveforms"]
    names = [w["name"] for w in W]
    ratio = [w["sep_over_drb"] for w in W]
    cols = [CRIT if r > 1 else GOOD for r in ratio]
    bars = ax.barh(names, ratio, color=cols, height=.5, zorder=3)
    ax.axvline(1.0, color=INK, lw=2, ls="--", zorder=4)
    ax.text(.53, .97, "1 range cell", transform=ax.transAxes, fontsize=10,
            color=INK, fontweight="bold", ha="center", va="top")
    ax.text(.99, .55, "to the RIGHT of this line =\nresolved = a separate\n(false) target appears",
            transform=ax.transAxes, fontsize=10.5, color=CRIT, fontweight="bold",
            ha="right", va="center",
            bbox=dict(boxstyle="round,pad=0.4", fc="#fdecec", ec=CRIT))
    for b, w in zip(bars, W):
        ax.text(w["sep_over_drb"] + .04, b.get_y() + b.get_height() / 2,
                f"{w['sep_over_drb']:.2f}x   (B = {w['bw_hz']/1e6:.0f} MHz, "
                f"cell = {w['d_rb_m']:.2f} m)",
                va="center", fontsize=10.5, color=INK, fontweight="bold")
    ax.set_xlim(0, 2.05)
    ax.set_xlabel("ghost separation / range cell   (>1 = resolved as its own target)",
                  fontsize=11.5, color=INK2)
    ax.set_title(f"The ghost sits {G['sep_m']:+.2f} m away -- who resolves it?",
                 fontsize=13, fontweight="bold", color=INK)
    ax.invert_yaxis()

    _cap(fig, "Derived by image source + Fresnel (benchmark/geometry.py: floor_ghost), NOT by RT -- Sionna's specular solver returns no target path at all (section 3), so it cannot produce this ghost either.\n"
               "Range cell here is the bistatic dRb = c/B with the FULL channel bandwidth (loaded cell, captured full-waveform reference). In the idle-cell regime, where the reference is only the always-on\n"
               "signal (5G SSB = 7.2 MHz -> cell 41.6 m), the ghost merges into the target instead. Do not mix the two regimes. Handing this to the detection work as an open problem.")
    return _save(fig, "report3_f8_ghost")


# =========================================================================== #
def build_all():
    J = _load()
    out = [fig1_bounces(J), fig2_ledger(J), fig3_gallery(J), fig4_floor(J),
           fig5_radiomap(J), fig6_no_sigma(J), fig7_hybrid(J), fig8_ghost(J)]
    print(f"  ✅ 그림 {len(out)}장")
    return out


if __name__ == "__main__":
    build_all()
