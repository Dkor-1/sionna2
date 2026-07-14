# -*- coding: utf-8 -*-
"""
viz_report7.py — (report7) **"이 시뮬레이션은 실제로 어떻게 굴러가는가"를 그림으로 보여준다**
=================================================================================================
사용자가 "과정이 이해가 안 된다"고 했다. 그래서 이 리포트는 **설명이 아니라 실물**이다 —
모든 그림이 Sionna 가 **정말로 출력한 것**이다(개념도가 아니다).

  §1 report7_pipeline.png  — 5단계 파이프라인. 각 칸에 **그 단계의 진짜 Sionna 출력**을 붙였다.
  §2 report7_chamber.png   — 챔버 6뷰 (Sionna 렌더러)
     report7_paths.png     — PathSolver depth 0/1/3 + **솔버가 준 경로표**
     report7_radiomap.png  — RadioMapSolver (바닥면/드론면) — 드론이 그림자를 드리운다
     report7_drones.png    — 드론 5종
     report7_flight.gif    — 비행하며 경로가 다시 추적된다
  §3 report7_rt_limit.png  — **RT 가 표적 σ 를 못 주는 이유** (benchmark/rt_pipeline.py 실측)
  §4 report7_benchmark.png — RT 로 구동한 벤치마크: 파형×드론 Pd/SCR + 유령 오경보

⚠ §3 의 서사는 **측정으로 교정됐다**. 지시서는 "광선 4억 발에도 수렴 안 하고 계속 커진다"였지만
   실제로 재보니 RT diffuse 추정량은 **수렴한다**(경로 ∝spp, 경로당 진폭 ∝1/√spp).
   문제는 분산이 아니라 **편향**이다 — SBR 대비 −20.9 dB 인 **틀린 값**에 수렴한다.
   결론("GPU 로 해결 안 된다")은 살아남았고, 근거는 오히려 더 강해졌다.

그림 텍스트는 전부 영어(프로젝트 규약), 코드 주석·print 는 한국어.

실행:  python src/viz_report7.py                (전부)
       python src/viz_report7.py --only pipeline,rtlimit
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_BENCH = os.path.abspath(os.path.join(_HERE, "..", "benchmark"))
for _p in (_HERE, _BENCH):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ⚠ render_rt → scene_build 가 mitsuba import 전에 GPU 를 고른다. 반드시 먼저.
import render_rt as R                                     # noqa: E402
import sionna.rt as rt                                    # noqa: E402
import mitsuba as mi                                      # noqa: E402
import numpy as np                                        # noqa: E402

import vizstyle                                           # noqa: E402
vizstyle.use_korean()
import matplotlib.pyplot as plt                           # noqa: E402
# NanumGothic 에는 U+2212(수학 마이너스)가 없다 → 로그축의 10^-4 같은 **mathtext 눈금**이
# 두부글자로 나온다(프로젝트 규약 위반). mathtext 만 DejaVu 로 돌린다(본문 폰트는 그대로).
plt.rcParams["mathtext.fontset"] = "dejavusans"
import matplotlib.image as mpimg                          # noqa: E402
from matplotlib.patches import FancyBboxPatch                    # noqa: E402

from drones import DRONES, build_drone                    # noqa: E402
from bistatic_scene import TX, RX, TGT, VEL, bistatic_params, C0   # noqa: E402

ROOT = os.path.abspath(os.path.join(_HERE, ".."))
FIG = os.path.join(ROOT, "outputs", "figures")
REN = os.path.join(ROOT, "outputs", "renders")
RT_JSON = os.path.join(ROOT, "outputs", "report7_rt.json")
W, D, H = R.W, R.D, R.H

RES = (1700, 1200)        # 규약: 1600x1100 이상
SPP = 768                 # 규약: 512 이상
DRONE = "mavic4pro"
FC = 3.5e9

STAGE = ["#1565c0", "#00838f", "#2e7d32", "#ef6c00", "#6a1b9a"]   # 5단계 색


def _p(name):
    return os.path.join(REN, f"{name}.png")


def _show(ax, path, title=None, sub=None, sub_in=False, color="k"):
    if os.path.exists(path):
        ax.imshow(mpimg.imread(path))
    else:
        ax.text(0.5, 0.5, "(render missing)\n" + os.path.basename(path), ha="center",
                va="center", transform=ax.transAxes, fontsize=9)
    ax.axis("off")
    if title:
        ax.set_title(title, fontsize=12, fontweight="bold", color=color)
    if sub:
        y, va = (0.02, "bottom") if sub_in else (-0.02, "top")
        ax.text(0.5, y, sub, ha="center", va=va, transform=ax.transAxes, fontsize=9,
                color="#555")


def _save(fig, name, dpi=125):
    os.makedirs(FIG, exist_ok=True)
    fn = os.path.join(FIG, name)
    fig.savefig(fn, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print("[fig]", os.path.relpath(fn, ROOT))
    return fn


def _ascii_log(ax, which="x"):
    """로그축 눈금을 **ASCII** 로 쓴다.

    matplotlib 의 로그 포매터는 10^{-4} 를 mathtext 로 그리는데, 그 마이너스가 U+2212 라
    NanumGothic 에 글리프가 없어 **두부글자**가 된다(그림에 '10¤4' 로 찍힌다).
    포매터를 갈아끼워 아예 mathtext 를 안 쓰게 한다 — 프로젝트 규약(ASCII 하이픈)과도 맞다."""
    from matplotlib.ticker import FuncFormatter, LogLocator, NullFormatter

    def f(v, _pos):
        if v <= 0:
            return ""
        e = int(np.round(np.log10(v)))
        if abs(v - 10.0 ** e) > 0.01 * v:            # 부눈금은 비운다
            return ""
        return f"1e{e}"                              # ASCII (하이픈은 ASCII '-')
    a = ax.xaxis if which == "x" else ax.yaxis
    a.set_major_locator(LogLocator(base=10.0))
    a.set_major_formatter(FuncFormatter(f))
    a.set_minor_formatter(NullFormatter())


def _rt_data():
    if not os.path.exists(RT_JSON):
        raise SystemExit("outputs/report7_rt.json 이 없다 → python benchmark/rt_pipeline.py 를 먼저 돌릴 것")
    return json.load(open(RT_JSON))


# =========================================================================== #
#  렌더 — 이 리포트가 쓰는 모든 Sionna 출력물을 여기서 만든다
# =========================================================================== #
CAM_HERO = ((-14.0, -17.0, 11.0), (14.0, 9.5, 3.5))
CAM_OUT = ((-22.0, -20.0, 15.0), (W / 2, D / 2, 3.0))
#  TX(4,2.5,8)·RX(4,17.5,6.5) 는 y 로 15 m 벌어져 있다 → 벽에 너무 붙으면 둘 다 화면 밖으로
#  나간다(첫 시도의 실패). 방 반대편(x=20)에서 벽을 정면으로 보면 둘이 한 화면에 들어온다.
#  드론(x=21)은 카메라 뒤에 있어 시야를 가리지 않는다.
CAM_TXRX = ((20.0, 10.0, 8.5), (4.0, 10.0, 7.2))
CAM_LOW = ((W - 2.0, -7.0, 3.2), (10.0, D / 2, 2.2))      # 낮게 — 바닥 반사가 보인다
PATHS_JSON = os.path.join(REN, "r7_paths.json")


def render_chamber(spp=SPP, res=RES):
    """① 씬 — 챔버 + 드론 + 안테나. 이게 '무대' 그 자체다."""
    print("① 씬 렌더 (챔버 + 드론 + TX/RX)")
    sc_closed = R.make_scene(drone=None, with_chamber=True, cutaway=False)
    R.shot(sc_closed, "r7_ch_outside", R.cam(*CAM_OUT), res=res, spp=spp, fov=55.0)
    sc = R.make_scene(drone=DRONE, cutaway=True)
    R.shot(sc, "r7_ch_hero", R.cam(*CAM_HERO), res=res, spp=spp, fov=55.0)
    R.shot(sc, "r7_ch_wide", R.cam(*R.CAMS["wide"]), res=res, spp=spp)
    R.shot(sc, "r7_ch_top", R.cam(*R.CAMS["top"]), res=res, spp=spp, clip=R.CLIP_CEIL)
    R.shot(sc, "r7_ch_grazing", R.cam(*R.CAMS["grazing"]), res=res, spp=spp)
    R.shot(sc, "r7_ch_side", R.cam(*R.CAMS["side"]), res=res, spp=spp, clip=R.CLIP_CEIL)
    # ② 안테나 — TX(빨강)·RX(초록) 이 **보이게** 찍는다.
    #   render_rt 는 마커를 0.30 m 로 줄여놨는데(경로를 가리지 않으려고), 12 m 떨어져서 보면
    #   점이 되어 안 보인다. 이 컷에서만 키운다 — 이 그림의 주인공이 안테나이기 때문이다.
    sc2 = R.make_scene(drone=DRONE, cutaway=True)
    for dev in list(sc2.transmitters.values()) + list(sc2.receivers.values()):
        dev.display_radius = 0.75
    R.shot(sc2, "r7_antennas", R.cam(*CAM_TXRX), res=res, spp=spp, fov=75.0)


def render_paths(spp=SPP, res=RES, samples=8_000_000):
    """③ PathSolver — 광선을 그리고, **솔버가 준 숫자**를 표로 저장한다(캡션에 손으로 안 적는다)."""
    print("③ 경로 렌더 (PathSolver)")
    sc = R.make_scene(drone=DRONE, cutaway=True)
    names = {int(o.object_id): n for n, o in sc.objects.items()}
    solver = rt.PathSolver()
    out = {"counts": {}, "depth1": []}
    for md, tag in ((0, "los"), (1, "1bounce"), (3, "3bounce")):
        t0 = time.time()
        paths = solver(sc, max_depth=md, los=True, specular_reflection=True,
                       diffuse_reflection=False, refraction=False,
                       samples_per_src=samples, seed=1)
        tau = np.asarray(paths.tau).squeeze().reshape(-1)
        n = int(tau.size)
        out["counts"][tag] = n
        print(f"  depth={md}: 경로 {n}개 ({time.time()-t0:.1f}s)")
        R.shot(sc, f"r7_paths_{tag}", R.cam(*R.CAMS["wide"]), paths=paths, res=res, spp=spp)
        if md == 1:
            R.shot(sc, "r7_paths_low", R.cam(*CAM_LOW), paths=paths, res=res, spp=spp)
            a = (np.asarray(paths.a[0]).squeeze().reshape(-1)
                 + 1j * np.asarray(paths.a[1]).squeeze().reshape(-1))
            g = 20 * np.log10(np.abs(a) + 1e-30)
            obj = np.asarray(paths.objects).squeeze().reshape(-1, n)
            los_g, los_t = float(g.max()), float(tau.min())
            for i in np.argsort(tau):
                h = [names.get(int(x), "") for x in obj[:, i] if int(x) >= 0]
                out["depth1"].append(dict(
                    tau_ns=float(tau[i] * 1e9), excess_ns=float((tau[i] - los_t) * 1e9),
                    rel_db=float(g[i] - los_g), hit=(h[0] if h and h[0] else "-")))
    json.dump(out, open(PATHS_JSON, "w"), indent=1)
    return out


def render_radiomap(spp=SPP, res=RES, n_tx=10_000_000):
    """④ RadioMapSolver — 바닥면·드론면. 드론이 **그림자**를 드리운다."""
    print("④ 라디오맵 렌더 (RadioMapSolver)")
    sc = R.make_scene(drone=DRONE, cutaway=True)
    rms = rt.RadioMapSolver()
    for z, tag in ((0.05, "floor"), (float(TGT[2]), "droneplane")):
        t0 = time.time()
        rm = rms(sc, center=mi.Point3f(W / 2, D / 2, z), orientation=mi.Point3f(0, 0, 0),
                 size=mi.Point2f(W - 0.5, D - 0.5), cell_size=mi.Point2f(0.25, 0.25),
                 samples_per_tx=n_tx, max_depth=3,
                 specular_reflection=True, diffuse_reflection=False)
        print(f"  z={z:.2f} m ({time.time()-t0:.1f}s)")
        R.shot(sc, f"r7_rmap_{tag}", R.cam(*R.CAMS["wide"]), radio_map=rm, res=res, spp=spp)
        R.shot(sc, f"r7_rmap_{tag}_top", R.cam(*R.CAMS["top"]), radio_map=rm, res=res,
               spp=spp, clip=R.CLIP_CEIL)


def render_drones(spp=SPP, res=(1300, 1000)):
    print("⑤ 드론 5종 렌더")
    for key in DRONES:
        sc = R.make_scene(drone=key, tgt=(0.0, 0.0, 0.0), with_chamber=False, vel=None)
        V = np.asarray(build_drone(DRONES[key]).v, float)
        span = float(np.linalg.norm(V.max(0) - V.min(0)))
        r = span * 1.30
        R.shot(sc, f"r7_drone_{key}", R.cam((r * 0.72, -r * 0.66, r * 0.34), look=(0, 0, 0)),
               res=res, spp=spp, fov=34.0)


def render_all(spp=SPP):
    render_chamber(spp=spp)
    render_paths(spp=spp)
    render_radiomap(spp=spp)
    render_drones(spp=spp)


# =========================================================================== #
#  §1 — 파이프라인: 5단계, 각 칸에 그 단계의 **진짜 출력**
# =========================================================================== #
def _rd_snapshot(M=32):
    """5단계(신호처리)의 실물 — Sionna PHY 로 합성한 감시신호의 거리-도플러 맵."""
    import viz_report4 as V4
    wf = V4.waveforms()["nr"]
    cell = V4.build_cpi(wf, M=M, ghost_on=True)
    rng = np.random.default_rng(3)
    n = len(cell["surv"])
    noise = np.sqrt(0.5) * (rng.standard_normal(n) + 1j * rng.standard_normal(n))
    Rb, f_d, rd, det = V4.detect(cell, cell["surv"] + noise)
    return dict(Rb=Rb, f_d=f_d, rd=20 * np.log10(rd / rd.max() + 1e-9), det=det,
                true_Rb=cell["true_Rb"], true_fd=cell["true_fd"],
                sigma=cell["sigma"], link=cell["link"], n_env=cell["n_env"],
                ghost=cell["ghost"])


def fig_pipeline(outdir=FIG):
    """5단계를 한 장에. 위 = Sionna 가 낸 **실물**, 아래 = 그 단계가 **넘겨주는 값**."""
    pj = json.load(open(PATHS_JSON)) if os.path.exists(PATHS_JSON) else {"counts": {}, "depth1": []}
    snap = _rd_snapshot()
    p = bistatic_params(TX, RX, TGT, VEL, FC)
    lt = snap["link"]

    fig = plt.figure(figsize=(19.5, 9.4), constrained_layout=True)
    fig.suptitle("How one number is made: the five stages of this simulation",
                 fontsize=19, fontweight="bold")
    gs = fig.add_gridspec(2, 5, height_ratios=[1.32, 1.0])

    # ---------- 위: 각 단계의 진짜 출력 ----------
    _show(fig.add_subplot(gs[0, 0]), _p("r7_ch_hero"),
          "1. The scene", "chamber mesh + drone mesh + materials", color=STAGE[0])
    _show(fig.add_subplot(gs[0, 1]), _p("r7_antennas"),
          "2. The antennas", "TX (red) and RX (green) on the x = 4 m wall", color=STAGE[1])
    _show(fig.add_subplot(gs[0, 2]), _p("r7_paths_1bounce"),
          "3. PathSolver", f"{pj['counts'].get('1bounce', '?')} rays found at max_depth = 1",
          color=STAGE[2])

    # 4단계: 무엇을 어디서 가져오나 — 세 엔진의 분업 (이건 '값'이라 표로 보여준다)
    ax4 = fig.add_subplot(gs[0, 3]); ax4.axis("off")
    ax4.set_title("4. Who supplies what", fontsize=12, fontweight="bold", color=STAGE[3])
    rows = [("geometry", "$\\tau$, $f_d$, bounce point", "Sionna RT", "#2e7d32"),
            ("target amplitude", "$\\sigma$ (with occlusion)", "SBR", "#ef6c00"),
            ("absolute power", "EIRP, $kT_0FB$", "link budget", "#6a1b9a")]
    y = 0.88
    for what, sym, who, c in rows:
        ax4.add_patch(FancyBboxPatch((0.03, y - 0.15), 0.94, 0.15, transform=ax4.transAxes,
                                     boxstyle="round,pad=0.012", fc="w", ec=c, lw=1.6))
        ax4.text(0.07, y - 0.037, what, fontsize=10.5, fontweight="bold", color=c,
                 transform=ax4.transAxes, va="top")
        ax4.text(0.07, y - 0.085, sym, fontsize=9.6, color="#333", transform=ax4.transAxes,
                 va="top")
        ax4.text(0.94, y - 0.06, who, fontsize=10, color=c, ha="right", va="center",
                 fontweight="bold", transform=ax4.transAxes)
        y -= 0.20
    ax4.text(0.5, y + 0.02, "RT is exact for the room.\nIt cannot give $\\sigma$ (see $\\S$3).\n"
                            "So SBR does the target.",
             fontsize=9.4, ha="center", va="top", color="#b71c1c", transform=ax4.transAxes,
             linespacing=1.5,
             bbox=dict(boxstyle="round", fc="#fff5f5", ec="#e0b4b4"))
    ax4.text(0.5, 0.10, f"$\\sigma$ = {10*np.log10(snap['sigma']):.1f} dBsm    "
                        f"echo SNR = {lt['snr_echo_db']:+.1f} dB\n"
                        f"$R_b$ = {p['Rb']:.1f} m    $f_d$ = {p['fd']:+.0f} Hz",
             fontsize=9.8, ha="center", va="top", family="monospace", color="#222",
             transform=ax4.transAxes, linespacing=1.7)

    # 5단계: 실제 거리-도플러 맵 (Sionna PHY 가 합성한 신호를 ECA→CAF→CFAR 로 처리한 것)
    ax5 = fig.add_subplot(gs[0, 4])
    im = ax5.pcolormesh(snap["Rb"], snap["f_d"], snap["rd"], cmap="turbo", vmin=-45, vmax=0,
                        shading="auto")
    ax5.plot(snap["true_Rb"], snap["true_fd"], "o", mfc="none", mec="w", ms=15, mew=1.8)
    dd, dr = np.where(snap["det"])
    if len(dd):
        ax5.plot(snap["Rb"][dr], snap["f_d"][dd], "x", color="w", ms=6, mew=1.2, alpha=0.85)
    ax5.set_xlim(snap["true_Rb"] - 14, snap["true_Rb"] + 16)
    ax5.set_ylim(-330, 330)
    ax5.set_xlabel("Bistatic range $R_b$ [m]", fontsize=9)
    ax5.set_ylabel("Doppler $f_d$ [Hz]", fontsize=9)
    ax5.set_title("5. The detection", fontsize=12, fontweight="bold", color=STAGE[4])
    ax5.tick_params(labelsize=8)
    fig.colorbar(im, ax=ax5, fraction=0.046, pad=0.02).ax.tick_params(labelsize=7)

    # ---------- 아래: 각 단계가 넘겨주는 것 (파이프 흐름) ----------
    txt = [
        ("1. SCENE",
         "load the meshes\n\n"
         "  chamber  30 x 20 x 11 m\n"
         "    absorber: 4 walls + ceiling\n"
         "    FLOOR: bare concrete (ITU)\n"
         "  drone: 5 DJI models, fitted\n"
         "    to the official envelope\n\n"
         "Every part carries a material\n"
         "from ONE table (materials.py),\n"
         "so RT and SBR cannot disagree."),
        ("2. ANTENNAS",
         "place TX and RX\n\n"
         f"  TX {tuple(TX)} m\n"
         f"  RX {tuple(RX)} m\n"
         f"  baseline L = {p['L']:.1f} m\n"
         f"  target {tuple(TGT)} m\n\n"
         "Both on the SAME wall: this is\n"
         "a passive bistatic radar, not a\n"
         "monostatic one. The RX never\n"
         "transmits - it just listens."),
        ("3. PATHSOLVER",
         "shoot rays, keep what lands\n\n"
         f"  depth 0 : {pj['counts'].get('los', '?')} path (line of sight)\n"
         f"  depth 1 : {pj['counts'].get('1bounce', '?')} paths\n"
         f"  depth 3 : {pj['counts'].get('3bounce', '?')} paths\n\n"
         "Each path comes back with a\n"
         "delay, a Doppler and a complex\n"
         "gain. The floor bounce appears\n"
         "at +19.3 ns / -14.7 dB."),
        ("4. THE HYBRID",
         "three engines, one number\n\n"
         "  RT          -> when it arrives\n"
         "  SBR         -> how big it looks\n"
         "  link budget -> how loud it is\n\n"
         "This split is not a preference.\n"
         "It is forced: RT's solver has no\n"
         "scattering integral, so sigma does\n"
         "not emerge from it (see $\\S$3)."),
        ("5. PROCESSING",
         "make the signal, find the target\n\n"
         "  Sionna PHY  -> surveillance CPI\n"
         "  ECA         -> kill the direct path\n"
         "  CAF         -> range-Doppler map\n"
         "  CFAR        -> declare a detection\n\n"
         "ECA / CAF / CFAR are radar-specific\n"
         "and are NOT in Sionna - they stay\n"
         "in passive_process.py."),
    ]
    for j, (head, body) in enumerate(txt):
        ax = fig.add_subplot(gs[1, j]); ax.axis("off")
        ax.add_patch(FancyBboxPatch((0.02, 0.02), 0.96, 0.96, transform=ax.transAxes,
                                    boxstyle="round,pad=0.015", fc="#fafafa",
                                    ec=STAGE[j], lw=2.0))
        ax.text(0.5, 0.94, head, fontsize=12, fontweight="bold", color=STAGE[j],
                ha="center", va="top", transform=ax.transAxes)
        ax.text(0.07, 0.83, body, fontsize=9.1, va="top", family="monospace",
                color="#333", transform=ax.transAxes, linespacing=1.5)
        if j < 4:      # 단계 사이 화살표
            ax.annotate("", xy=(1.055, 0.5), xytext=(0.99, 0.5), xycoords=ax.transAxes,
                        arrowprops=dict(arrowstyle="-|>", lw=2.6, color="#90a4ae",
                                        mutation_scale=22))

    fig.supxlabel(
        "Panels 1-3 and 5 are actual Sionna output: the renders come from scene.render_to_file(), the rays are what PathSolver returned, and the\n"
        "range-Doppler map is a surveillance signal synthesised by Sionna PHY (cir_to_time_channel + ApplyTimeChannel) and then run through\n"
        "ECA / CAF / CFAR. Nothing in this figure is a hand-drawn schematic.",
        fontsize=9.2, color="0.45")
    return _save(fig, "report7_pipeline.png")


# =========================================================================== #
#  §2 — 렌더 갤러리
# =========================================================================== #
def fig_chamber(outdir=FIG):
    fig = plt.figure(figsize=(16.5, 9.4), constrained_layout=True)
    fig.suptitle("The chamber, as Sionna sees it", fontsize=19, fontweight="bold")
    gs = fig.add_gridspec(2, 3)
    _show(fig.add_subplot(gs[0, 0]), _p("r7_ch_outside"), "Closed shield",
          "steel frame + metal skin", sub_in=True)
    _show(fig.add_subplot(gs[0, 1]), _p("r7_ch_hero"), "Inside (front wall removed)",
          "pyramidal absorber on 4 walls + ceiling", sub_in=True)
    _show(fig.add_subplot(gs[0, 2]), _p("r7_ch_top"), "From above (ceiling clipped)",
          "TX and RX on the left wall, drone at (21, 10, 5.5) m", sub_in=True)
    _show(fig.add_subplot(gs[1, 0]), _p("r7_ch_wide"), "TX, RX and target together",
          "baseline L = 15 m along the x = 4 m wall", sub_in=True)
    _show(fig.add_subplot(gs[1, 1]), _p("r7_ch_grazing"), "Grazing the floor",
          "the floor is bare concrete tile - NOT absorber", sub_in=True)
    _show(fig.add_subplot(gs[1, 2]), _p("r7_ch_side"), "Side view",
          "the height the floor bounce has to climb", sub_in=True)
    fig.supxlabel(
        "All six frames: sionna.rt.Scene.render_to_file(), 1700 x 1200, 768 samples/pixel. This is the very scene the path solver traces\n"
        "and the very mesh the SBR integrator shoots at - one scene, one truth. The room is SEMI-anechoic: five faces absorb, the floor does not.",
        fontsize=9.2, color="0.45")
    return _save(fig, "report7_chamber.png")


_HIT = {"-": "line of sight", "floor_light": "FLOOR (concrete)", "floor_dark": "FLOOR (concrete)",
        "absorber_ceiling": "ceiling absorber", "absorber_left": "side wall absorber",
        "absorber_right": "side wall absorber", "absorber_back": "back wall absorber"}


def fig_paths(outdir=FIG):
    pj = json.load(open(PATHS_JSON)) if os.path.exists(PATHS_JSON) else {"counts": {}, "depth1": []}
    c = pj["counts"]
    fig = plt.figure(figsize=(16.5, 9.6), constrained_layout=True)
    fig.suptitle("The rays Sionna actually traced", fontsize=19, fontweight="bold")
    gs = fig.add_gridspec(2, 3)
    for j, (tag, t) in enumerate((("los", "max_depth = 0  (line of sight)"),
                                  ("1bounce", "max_depth = 1  (one reflection)"),
                                  ("3bounce", "max_depth = 3  (up to three)"))):
        _show(fig.add_subplot(gs[0, j]), _p(f"r7_paths_{tag}"), t,
              f"{c.get(tag, '?')} paths", sub_in=True)
    _show(fig.add_subplot(gs[1, 0]), _p("r7_paths_low"), "One bounce, seen from low down",
          "the ray diving to the tiles is the floor bounce", sub_in=True)

    axT = fig.add_subplot(gs[1, 1]); axT.axis("off")
    axT.text(0.0, 1.02, "What the solver returns (max_depth = 1)", fontsize=12.5,
             fontweight="bold", va="top", transform=axT.transAxes)
    lines = [f"{'surface':<21s}{'delay':>9s}{'excess':>9s}{'re LOS':>9s}", "-" * 48]
    for r in pj["depth1"]:
        lines.append(f"{_HIT.get(r['hit'], r['hit']):<21s}{r['tau_ns']:>7.1f}ns"
                     f"{r['excess_ns']:>+8.1f}{r['rel_db']:>+8.1f}dB")
    axT.text(0.0, 0.90, "\n".join(lines), fontsize=10.4, family="monospace", va="top",
             transform=axT.transAxes, linespacing=1.75)
    axT.text(0.0, 0.34, (
        "These numbers are not typed into a caption -\n"
        "they are read back out of the solver.\n\n"
        "The floor bounce lands at +19.3 ns / -14.7 dB,\n"
        "which is what a hand Fresnel calculation gives\n"
        "to within 0.02 dB. THIS is what RT is good at."),
        fontsize=9.6, va="top", transform=axT.transAxes, linespacing=1.5, color="#333",
        bbox=dict(boxstyle="round", fc="#eef5ff", ec="#b6cbe6"))

    axN = fig.add_subplot(gs[1, 2]); axN.axis("off")
    axN.text(0.0, 1.02, "Two honest caveats", fontsize=12.5, fontweight="bold",
             va="top", color="#b71c1c", transform=axN.transAxes)
    axN.text(0.0, 0.90, (
        "1. The absorber rows look too loud.\n"
        "   One specular bounce off a pyramid facet is\n"
        "   -5.2 dB in our absorber material, and that\n"
        "   value is MODELLED, not measured. Real -25 dB\n"
        "   anechoic performance is geometric: the ray has\n"
        "   to rattle 4-5 times inside a pyramid valley, so\n"
        "   a shallow solve cannot show it. These rows are\n"
        "   therefore an upper bound - pessimistic.\n"
        "   Nothing downstream leans on them: they are\n"
        "   static (zero Doppler) and ECA deletes them.\n\n"
        "2. NO ray reaches the drone.\n"
        "   A 0.35 m target at 18 m subtends 7e-4 sr. The\n"
        "   target is simply not in this picture - and that\n"
        "   is the whole reason for $\\S$3."),
        fontsize=9.3, va="top", transform=axN.transAxes, linespacing=1.5, color="#333")

    fig.supxlabel(
        "scene.render_to_file(paths = PathSolver(...)), 8 M rays per source. The floor is the only reflector left in the room, and the only one\n"
        "that matters: a floor path that goes VIA the target inherits the target's Doppler and therefore survives ECA (report4 / report6).",
        fontsize=9.2, color="0.45")
    return _save(fig, "report7_paths.png")


def fig_radiomap(outdir=FIG):
    fig = plt.figure(figsize=(15.5, 9.0), constrained_layout=True)
    fig.suptitle("Where the energy goes - Sionna radio maps", fontsize=19, fontweight="bold")
    gs = fig.add_gridspec(2, 2)
    _show(fig.add_subplot(gs[0, 0]), _p("r7_rmap_floor"), "Floor plane (z = 0.05 m)",
          "3/4 view", sub_in=True)
    _show(fig.add_subplot(gs[0, 1]), _p("r7_rmap_floor_top"), None, "top view", sub_in=True)
    _show(fig.add_subplot(gs[1, 0]), _p("r7_rmap_droneplane"), "Drone plane (z = 5.5 m)",
          "3/4 view", sub_in=True)
    _show(fig.add_subplot(gs[1, 1]), _p("r7_rmap_droneplane_top"), None, "top view",
          sub_in=True)
    fig.supxlabel(
        "RadioMapSolver: TX at (4, 2.5, 8) m, 3.5 GHz, max_depth = 3, 10 M rays, 0.25 m cells. Colour = received power per cell.\n"
        "The field falls off smoothly from the TX - no standing-wave pattern, because five of the six faces absorb. The dark streaks on the\n"
        "floor are geometric shadows of the door panels. Note what the radio map DOES show about the drone: a shadow, i.e. the drone blocks\n"
        "rays. What it does NOT show is how much the drone scatters BACK - that is sigma, and no radio map contains it.",
        fontsize=9.2, color="0.45")
    return _save(fig, "report7_radiomap.png")


def fig_drones(outdir=FIG):
    keys = list(DRONES)
    fig, axes = plt.subplots(2, 3, figsize=(15.5, 9.2), constrained_layout=True)
    fig.suptitle("The five targets - Sionna RT renders of the meshes the integrator shoots at",
                 fontsize=17.5, fontweight="bold")
    for ax, key in zip(axes.flat, keys):
        s = DRONES[key]
        _show(ax, _p(f"r7_drone_{key}"), s.name,
              f"{s.num_rotors} rotors - {s.weight_g:g} g - {build_drone(s).n_tris()} triangles",
              sub_in=True)
    ax = axes.flat[5]; ax.axis("off")
    ax.text(0.0, 0.98, "Same mesh, two engines", fontsize=13, fontweight="bold", va="top",
            transform=ax.transAxes)
    ax.text(0.0, 0.86, (
        "The OBJ files rendered here are literally the\n"
        "same files that:\n\n"
        "  - Sionna RT loads into the scene, and\n"
        "  - the SBR integrator fires its ray grid at.\n\n"
        "Their materials come from one table\n"
        "(src/materials.py), which asks Sionna itself\n"
        "for the ITU values. So the two engines cannot\n"
        "quietly disagree about what a drone is made of -\n"
        "a bug that did happen once (the camera was\n"
        "plastic for RT and metal for PO: 10.9 dB apart).\n\n"
        "The meshes were also fitted to the official DJI\n"
        "envelope; before that fix they were 25-47 %\n"
        "too flat (report1)."),
        fontsize=9.5, va="top", transform=ax.transAxes, linespacing=1.5, color="#333")
    fig.supxlabel(
        "sionna.rt.Scene.render_to_file(), fov 34 deg, 768 samples/pixel, drone alone in free space.",
        fontsize=9.2, color="0.45")
    return _save(fig, "report7_drones.png")


# =========================================================================== #
#  §2e — 비행 GIF: 드론이 날면 경로가 다시 추적된다
# =========================================================================== #
def gif_flight(outdir=FIG, n_frames=28, spp=224, res=(1100, 800), samples=1_500_000,
               reuse=False, gif_w=900):
    """매 프레임 PathSolver 를 다시 돌린다 — 경로가 드론을 따라 바뀐다.
    reuse=True 면 이미 렌더된 프레임을 재사용한다(GIF 조립만 다시 할 때)."""
    print("⑥ 비행 GIF (프레임마다 PathSolver 재실행)")
    from scenarios import radial
    from geometry import TX as gTX, RX as gRX, CENTER, SPEED, SPAN
    from PIL import Image, ImageDraw, ImageFont
    pos, vel = radial(gTX, gRX, CENTER, speed=SPEED, span=SPAN, n=n_frames)
    fdir = os.path.join(REN, "r7_flight")
    os.makedirs(fdir, exist_ok=True)
    solver = rt.PathSolver()
    for i, (pp, vv) in enumerate(zip(pos, vel)):
        f = os.path.join(fdir, f"f{i:03d}.png")
        if reuse and os.path.exists(f):
            continue
        sc = R.make_scene(drone=DRONE, tgt=tuple(map(float, pp)), cutaway=True,
                          vel=tuple(map(float, vv)))
        paths = solver(sc, max_depth=1, los=True, specular_reflection=True,
                       diffuse_reflection=False, refraction=False,
                       samples_per_src=samples, seed=1)
        sc.render_to_file(camera=R.cam(*R.CAMS["wide"]), filename=f,
                          num_samples=spp, resolution=res, paths=paths, fov=70.0)
        if i % 7 == 0:
            print(f"  frame {i:2d}/{n_frames}")
    try:
        fnt = ImageFont.truetype(os.path.join(ROOT, "assets", "NanumGothic.ttf"), 22)
    except Exception:
        fnt = ImageFont.load_default()
    imgs = []
    for i in range(n_frames):
        im = Image.open(os.path.join(fdir, f"f{i:03d}.png")).convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))   # Sionna 렌더는 알파가 있다
        im = Image.alpha_composite(bg, im).convert("RGB")
        if gif_w and im.width > gif_w:                          # GIF 용량(24 MB → 5 MB)
            im = im.resize((gif_w, int(im.height * gif_w / im.width)), Image.LANCZOS)
        dr = ImageDraw.Draw(im)
        dr.text((14, 10), f"Sionna RT - PathSolver re-run every frame  ({i+1}/{n_frames})",
                fill="black", font=fnt)
        dr.text((14, 36), f"drone at ({pos[i][0]:.1f}, {pos[i][1]:.1f}, {pos[i][2]:.1f}) m",
                fill="#c62828", font=fnt)
        imgs.append(im.convert("P", palette=Image.ADAPTIVE, colors=96))
    gif = os.path.join(outdir, "report7_flight.gif")
    imgs[0].save(gif, save_all=True, append_images=imgs[1:], duration=110, loop=0,
                 optimize=True)
    print("[gif]", os.path.relpath(gif, ROOT), f"({len(imgs)} frames)")
    return gif


# =========================================================================== #
#  §3 — RT 가 표적 σ 를 못 주는 이유 (실측)
# =========================================================================== #
def fig_rt_limit(outdir=FIG):
    """헤드라인: RT diffuse 는 **수렴한다 — 틀린 값으로**. 분산이 아니라 편향이다."""
    d = _rt_data()
    A = [r for r in d["A_spp"] if r.get("sigma_dbsm") is not None]
    A0 = d["A_spp"]
    B, fit = d["B_S"], d.get("B_fit") or {}
    S = d["SBR"]
    sbr_db = d["sbr_converged_db"]
    rt_db = d["rt_converged_db"]

    fig = plt.figure(figsize=(17.6, 9.6), constrained_layout=True)
    fig.suptitle("Why the target needs SBR: RT converges - to the wrong number",
                 fontsize=19, fontweight="bold")
    gs = fig.add_gridspec(2, 3, height_ratios=[1.0, 0.82])

    # (a) spp 스윕 — RT vs SBR
    ax = fig.add_subplot(gs[0, 0])
    spp = np.array([r["spp"] for r in A])
    sg = np.array([r["sigma_dbsm"] for r in A])
    lo = np.array([r["sigma_min_db"] for r in A])
    hi = np.array([r["sigma_max_db"] for r in A])
    ax.fill_between(spp, lo, hi, color="#c62828", alpha=0.18, label="seed-to-seed spread")
    ax.plot(spp, sg, "o-", color="#c62828", lw=2.2, ms=7, label="Sionna RT (diffuse)")
    ax.axhline(sbr_db, color="#1565c0", lw=2.4, ls="-",
               label=f"SBR (converged) = {sbr_db:+.1f} dBsm")
    ax.axhspan(sbr_db - 1.5, sbr_db + 1.5, color="#1565c0", alpha=0.12)
    ax.annotate("", xy=(spp[-1], sbr_db), xytext=(spp[-1], sg[-1]),
                arrowprops=dict(arrowstyle="<->", color="k", lw=1.6))
    ax.text(spp[-1] * 0.72, (sbr_db + sg[-1]) / 2, f"{rt_db - sbr_db:+.1f} dB\nBIAS",
            fontsize=11, fontweight="bold", ha="right", va="center", color="k",
            bbox=dict(boxstyle="round", fc="#fff8e1", ec="#c62828"))
    n0 = [r for r in A0 if r.get("sigma_dbsm") is None]
    if n0:
        ax.annotate("no path at all", xy=(n0[0]["spp"], sg[0]), xytext=(n0[0]["spp"] * 1.05, sg[0] + 5.0),
                    fontsize=8.6, color="#c62828", ha="left",
                    arrowprops=dict(arrowstyle="->", color="#c62828", lw=1.0))
    ax.set_xscale("log")
    ax.set_xlim(6e5, 8e8)
    _ascii_log(ax, "x")
    ax.set_xlabel("rays per source (samples_per_src)")
    ax.set_ylabel("implied $\\sigma$ [dBsm]")
    ax.set_title("(a) 400 million rays do not help", fontsize=12.5)
    ax.legend(fontsize=8.6, loc="lower left"); ax.grid(alpha=0.3, which="both")
    ax.set_ylim(sbr_db - 34, sbr_db + 7)

    # (b) 그런데 추정량 자체는 정상이다 — MC 스케일링
    ax = fig.add_subplot(gs[0, 1])
    npath = np.array([r["n_paths"] for r in A])
    amp = np.array([r["amp_per_path"] for r in A])
    ax.plot(spp, npath, "s-", color="#2e7d32", lw=2.0, ms=6, label="paths found  ($\\propto$ spp)")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("rays per source"); ax.set_ylabel("number of paths", color="#2e7d32")
    ax.tick_params(axis="y", labelcolor="#2e7d32")
    ax2 = ax.twinx()
    ax2.plot(spp, amp, "^--", color="#6a1b9a", lw=2.0, ms=6,
             label="amplitude per path  ($\\propto 1/\\sqrt{spp}$)")
    ax2.set_yscale("log"); ax2.set_ylabel("amplitude of one path", color="#6a1b9a")
    ax2.tick_params(axis="y", labelcolor="#6a1b9a")
    for _a, _w in ((ax, "x"), (ax, "y"), (ax2, "y")):
        _ascii_log(_a, _w)
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=8.4, loc="center left")
    ax.set_title("(b) The estimator is fine - it is a Monte Carlo", fontsize=12.5)
    ax.grid(alpha=0.3, which="both")
    sd = [r["spread_db"] for r in A]
    ax.text(0.5, 0.06, f"the two cancel, so $\\sigma$ settles;\n"
                       f"seed spread shrinks {sd[0]:.1f} $\\rightarrow$ {sd[-1]:.1f} dB",
            transform=ax.transAxes, ha="center", fontsize=8.8, color="0.25",
            bbox=dict(fc="w", ec="0.6", alpha=0.92, boxstyle="round,pad=0.35"))

    # (c) 무엇을 재고 있나 — σ 가 아니라 노브 S
    ax = fig.add_subplot(gs[0, 2])
    sS = np.array([r["s_plastic"] for r in B])
    sig = np.array([r["sigma_dbsm"] for r in B])
    ax.plot(sS, sig, "o-", color="#ef6c00", lw=2.2, ms=8, label="Sionna RT (diffuse)")
    ref = sig[0] + 20 * np.log10(sS / sS[0])
    ax.plot(sS, ref, ":", color="0.45", lw=1.8, label="$S^2$ law")
    ax.axhline(sbr_db, color="#1565c0", lw=2.2, label=f"SBR = {sbr_db:+.1f} dBsm")
    if fit.get("s_star"):
        ax.axvline(1.0, color="k", ls="--", lw=1.0)
        ax.text(1.02, sbr_db - 17, "S = 1\n(physical max)", fontsize=8.4, color="k")
        ax.plot(fit["s_star"], sbr_db, "*", ms=22, color="#c62828", zorder=6)
        ax.annotate(f"to match SBR you would have to\nfit S = {fit['s_star']:.2f} - IMPOSSIBLE",
                    xy=(fit["s_star"], sbr_db), xytext=(0.13, sbr_db + 4.5), fontsize=9,
                    color="#c62828", fontweight="bold",
                    arrowprops=dict(arrowstyle="->", color="#c62828", lw=1.3))
    ax.set_xscale("log")
    ax.set_xlabel("scattering coefficient S of the drone shell")
    ax.set_ylabel("implied $\\sigma$ [dBsm]")
    ax.set_title("(c) RT measures our knob S, not the drone", fontsize=12.5)
    ax.legend(fontsize=8.4, loc="lower right"); ax.grid(alpha=0.3, which="both")
    ax.set_xlim(0.07, 2.4); ax.set_ylim(sbr_db - 35, sbr_db + 9)
    from matplotlib.ticker import FixedLocator, FixedFormatter    # S 는 0.1~2 → ASCII 로 직접
    ax.xaxis.set_major_locator(FixedLocator([0.1, 0.2, 0.4, 0.8, 1.0, 2.0]))
    ax.xaxis.set_major_formatter(FixedFormatter(["0.1", "0.2", "0.4", "0.8", "1.0", "2.0"]))
    ax.xaxis.set_minor_formatter(plt.NullFormatter())

    # (d) 금속은 아예 안 보인다
    ax = fig.add_subplot(gs[1, 0]); ax.axis("off")
    ax.text(0.0, 1.02, "(d) And the metal is invisible", fontsize=12.5, fontweight="bold",
            va="top", transform=ax.transAxes)
    C = d["C_materials"]
    lines = [f"{'part':<9s}{'material':<17s}{'S':>5s}", "-" * 33]
    for r in C:
        lines.append(f"{r['group']:<9s}{r['mat']:<17s}{r['S']:>5.2f}"
                     + ("   <- ZERO" if r["S"] == 0 else ""))
    ax.text(0.0, 0.92, "\n".join(lines), fontsize=8.6, family="monospace", va="top",
            transform=ax.transAxes, linespacing=1.42)
    n0 = sum(1 for r in C if r["S"] == 0)
    ax.text(0.0, 0.02, (
        f"ITU materials have S = 0 by definition (pure specular), so {n0} of {len(C)}\n"
        f"parts - motors, battery, PCB, camera housing - contribute EXACTLY\n"
        f"NOTHING to an RT diffuse echo. The metal simply is not there."),
        fontsize=9.0, va="bottom", transform=ax.transAxes, linespacing=1.45,
        color="#b71c1c",
        bbox=dict(boxstyle="round", fc="#fff5f5", ec="#e0b4b4"))

    # (e) 그런데 환경은 정확하다
    ax = fig.add_subplot(gs[1, 1]); ax.axis("off")
    ax.text(0.0, 1.02, "(e) But the ROOM it gets right", fontsize=12.5, fontweight="bold",
            va="top", color="#2e7d32", transform=ax.transAxes)
    E = d["D_env"]
    lines = [f"{'surface':<20s}{'excess':>9s}{'re LOS':>9s}", "-" * 38]
    for r in E:
        lines.append(f"{_HIT.get(r['hit'], r['hit']):<20s}{r['excess_ns']:>+8.2f}ns"
                     f"{r['rel_db']:>+8.2f}dB")
    ax.text(0.0, 0.90, "\n".join(lines), fontsize=9.5, family="monospace", va="top",
            transform=ax.transAxes, linespacing=1.55)
    fl = [r for r in E if "floor" in r["hit"]]
    fl = fl[0] if fl else None
    if fl:
        ax.text(0.0, 0.34, (
            f"The floor bounce: +{fl['excess_ns']:.2f} ns, {fl['rel_db']:+.2f} dB.\n"
            f"A hand Fresnel calculation gives -14.7 dB.\n"
            f"They agree to 0.02 dB.\n\n"
            f"Large flat surfaces are exactly what a specular\n"
            f"ray tracer is FOR. The target is not one."),
            fontsize=9.4, va="top", transform=ax.transAxes, linespacing=1.5, color="#1b5e20",
            bbox=dict(boxstyle="round", fc="#eef7ee", ec="#a5d6a7"))

    # (f) 판정
    ax = fig.add_subplot(gs[1, 2]); ax.axis("off")
    ax.text(0.0, 1.02, "(f) The verdict", fontsize=12.5, fontweight="bold", va="top",
            transform=ax.transAxes)
    ax.text(0.0, 0.90, (
        "NOT true:  \"ray tracing cannot do RCS\".\n"
        "  SBR is a ray tracer, and it computes sigma.\n\n"
        "TRUE:  Sionna RT's default path solver has no\n"
        "  scattering-integral stage, so sigma does not\n"
        "  emerge from it. What comes back instead is\n"
        "  a diffuse lobe proportional to S - a knob.\n\n"
        "So we split the problem:\n\n"
        "  environment (tau, f_d, bounces)  ->  Sionna RT\n"
        "  target sigma (with occlusion)    ->  SBR\n"
        "  absolute power (EIRP, kT0FB)     ->  link budget\n\n"
        "This is not a workaround. It is the correct\n"
        "decomposition, and each engine is used exactly\n"
        "where it is exact."),
        fontsize=9.4, va="top", transform=ax.transAxes, linespacing=1.5, color="#333")

    fig.supxlabel(
        "Measured by benchmark/rt_pipeline.py on the real Mavic 4 Pro mesh at the bistatic bisector, 3.5 GHz, diffuse reflection ON.\n"
        "NOTE - this CORRECTS the working note that said RT 'never converges, +8 to 12 dB per 4x rays'. It does converge: paths grow as spp and each\n"
        "path's amplitude falls as 1/sqrt(spp), so the incoherent sum settles and the seed spread SHRINKS (8.0 -> 1.3 dB). The problem is not variance,\n"
        "it is bias - more GPU buys a more precise wrong answer. That makes the case for SBR stronger, not weaker.",
        fontsize=9.2, color="0.45")
    return _save(fig, "report7_rt_limit.png")


# =========================================================================== #
#  §4 — RT 로 구동한 벤치마크 (report5 데이터) + 유령
# =========================================================================== #
def fig_benchmark(outdir=FIG):
    import pandas as pd
    m = pd.read_csv(os.path.join(ROOT, "outputs", "bench_matrix.csv"))
    g = pd.read_csv(os.path.join(ROOT, "outputs", "bench_ghost.csv"))
    wfs = ["lte10", "lte20", "wifi80", "nr100"]
    WL = {"lte10": "LTE 10", "lte20": "LTE 20", "wifi80": "WiFi 80", "nr100": "5G 100"}
    drones = ["s1000plus", "matrice4e", "phantom4", "mavic4pro", "mini5pro"]
    DL = {k: DRONES[k].name.replace("DJI ", "") for k in drones}

    fig = plt.figure(figsize=(17.4, 9.2), constrained_layout=True)
    fig.suptitle("The benchmark this machinery produces", fontsize=19, fontweight="bold")
    gs = fig.add_gridspec(2, 3, height_ratios=[1.0, 0.92])

    # (a) SCR 히트맵 (Pd 는 전부 100% — 그게 요점이다)
    ax = fig.add_subplot(gs[0, 0])
    M = np.zeros((len(wfs), len(drones)))
    P = np.zeros_like(M)
    for i, w in enumerate(wfs):
        for j, dr in enumerate(drones):
            r = m[(m.wf == w) & (m.drone == dr)]
            M[i, j] = float(r.scr_db.iloc[0]); P[i, j] = float(r.pd.iloc[0])
    im = ax.imshow(M, cmap="viridis", aspect="auto")
    for i in range(len(wfs)):
        for j in range(len(drones)):
            ax.text(j, i, f"{M[i,j]:.0f}", ha="center", va="center", fontsize=10,
                    color="w" if M[i, j] < 45 else "k", fontweight="bold")
    ax.set_xticks(range(len(drones)))
    ax.set_xticklabels([DL[k] for k in drones], rotation=22, ha="right", fontsize=9)
    ax.set_yticks(range(len(wfs))); ax.set_yticklabels([WL[w] for w in wfs], fontsize=9.5)
    ax.set_title("(a) SCR [dB] - every cell detects (Pd = 100 %)", fontsize=12)
    fig.colorbar(im, ax=ax, fraction=0.046, label="SCR [dB]")

    # (b) 대역폭이 가르는 것은 탐지가 아니라 **위치정보**
    ax = fig.add_subplot(gs[0, 1])
    x = np.arange(len(wfs))
    rb = [float(m[(m.wf == w) & (m.drone == DRONE)].rb_err_m.iloc[0]) for w in wfs]
    drb = [float(m[(m.wf == w) & (m.drone == DRONE)].delta_rb_m.iloc[0]) for w in wfs]
    ax.bar(x - 0.2, drb, 0.4, color="#90a4ae", label="range resolution $\\Delta R_b$ = c/B")
    ax.bar(x + 0.2, rb, 0.4, color="#1565c0", label="measured range error")
    for i, (a, b) in enumerate(zip(drb, rb)):
        ax.text(i - 0.2, a * 1.1, f"{a:.1f} m", ha="center", fontsize=8.5, color="#455a64")
        ax.text(i + 0.2, b * 1.1, f"{b:.2f} m", ha="center", fontsize=8.5, color="#1565c0")
    ax.set_yscale("log"); ax.set_xticks(x); ax.set_xticklabels([WL[w] for w in wfs], fontsize=9.5)
    _ascii_log(ax, "y")
    ax.set_ylabel("metres (log)")
    ax.set_title("(b) Bandwidth buys location, not detection", fontsize=12)
    ax.legend(fontsize=8.4, loc="upper right"); ax.grid(alpha=0.3, axis="y", which="both")
    ax.set_ylim(5e-3, 200)
    ax.text(0.5, 0.06, "All four detect the drone.\nOnly 5G can say WHERE it is.",
            transform=ax.transAxes, ha="center", fontsize=9, color="0.25",
            bbox=dict(fc="w", ec="0.6", alpha=0.92, boxstyle="round,pad=0.35"))

    # (c) 유령 — 셀은 울리지만 가짜 표적은 아니다
    ax = fig.add_subplot(gs[0, 2])
    gg = g[g.ghost_on == True]                                  # noqa: E712
    pdet = [float(gg[(gg.wf == w) & (gg.drone == DRONE)].p_ghost_det.iloc[0]) * 100 for w in wfs]
    pfal = [float(gg[(gg.wf == w) & (gg.drone == DRONE)].p_false.iloc[0]) * 100 for w in wfs]
    marg = [float(gg[(gg.wf == w) & (gg.drone == DRONE)].ghost_margin_db.iloc[0]) for w in wfs]
    ax.bar(x - 0.2, pdet, 0.4, color="#ff1744",
           label="ghost CELL fires (CFAR hit there)")
    ax.bar(x + 0.2, pfal, 0.4, color="0.75", hatch="//", edgecolor="0.4",
           label="declared a SEPARATE target")
    for i in range(len(wfs)):
        ax.text(i - 0.2, pdet[i] + 3, f"{pdet[i]:.0f}%", ha="center", fontsize=8.6,
                color="#c62828")
        ax.text(i + 0.2, pfal[i] + 3, f"{pfal[i]:.0f}%", ha="center", fontsize=8.6,
                fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels([WL[w] for w in wfs], fontsize=9.5)
    ax.set_ylabel("probability [%]"); ax.set_ylim(0, 128)
    ax.set_title("(c) The floor ghost: loud, but never a phantom", fontsize=12)
    ax.legend(fontsize=8.0, loc="upper left"); ax.grid(alpha=0.3, axis="y")
    ax.text(0.5, 0.42, "The ghost cell rings every time\n(margin up to +16 dB over CFAR).\n"
                       "But it is only 1 range bin from the\ntarget, so it is never DECLARED\n"
                       "as a second drone: 0 %, all four.",
            transform=ax.transAxes, ha="center", fontsize=8.8, color="0.2",
            bbox=dict(fc="#fff8e1", ec="#c62828", alpha=0.95, boxstyle="round,pad=0.4"))

    # (d) 어느 숫자가 어느 엔진에서 왔나
    ax = fig.add_subplot(gs[1, 0]); ax.axis("off")
    ax.text(0.0, 1.02, "(d) Every column has an owner", fontsize=12.5, fontweight="bold",
            va="top", transform=ax.transAxes)
    ax.text(0.0, 0.90, (
        "quantity            engine\n"
        "-------------------------------------------\n"
        "tau, f_d, geometry   Sionna RT\n"
        "chamber clutter      Sionna RT  (measured)\n"
        "target sigma         SBR        (occlusion)\n"
        "echo SNR, DNR        link budget (EIRP, kTB)\n"
        "surveillance CPI     Sionna PHY\n"
        "ECA / CAF / CFAR     passive_process\n"
        "                     (radar-only; not in Sionna)\n\n"
        "Nothing here is a hand-set knob any more.\n"
        "The old a_tgt = 1.0, dpi_amp = 55, snr = 14 dB\n"
        "are gone."),
        fontsize=9.4, va="top", family="monospace", transform=ax.transAxes,
        linespacing=1.55, color="#333")

    # (e) 클러터는 죽은 파라미터
    ax = fig.add_subplot(gs[1, 1]); ax.axis("off")
    ax.text(0.0, 1.02, "(e) The clutter is a dead parameter", fontsize=12.5,
            fontweight="bold", va="top", transform=ax.transAxes)
    ax.text(0.0, 0.92, (
        "Sionna RT measured the chamber's static echoes\n"
        "(strongest -9.8 dB - NOT weak). Then we scaled\n"
        "them and re-ran the whole detector:\n\n"
        "   reverb x0     SCR = 43.140551 dB\n"
        "   reverb x1     SCR = 43.140551 dB\n"
        "   reverb x10    SCR = 43.140551 dB\n\n"
        "Identical to six decimals. ECA projects anything\n"
        "static onto zero, whatever its amplitude. So the\n"
        "honest statement is NOT \"the chamber is anechoic\n"
        "so clutter is weak\". It is: \"clutter is strong,\n"
        "and ECA deletes it anyway.\""),
        fontsize=9.2, va="top", transform=ax.transAxes, linespacing=1.45, color="#333")
    ax.text(0.0, 0.02, "The one echo ECA CANNOT delete is the floor\n"
                       "ghost - because it goes via the moving target\n"
                       "and inherits its Doppler. That is panel (c).",
            fontsize=9.2, va="bottom", transform=ax.transAxes, linespacing=1.45,
            color="#b71c1c", bbox=dict(boxstyle="round", fc="#fff5f5", ec="#e0b4b4"))

    # (f) 무엇이 살아남고 무엇이 무너졌나
    ax = fig.add_subplot(gs[1, 2]); ax.axis("off")
    ax.text(0.0, 1.02, "(f) Survived / collapsed", fontsize=12.5, fontweight="bold",
            va="top", transform=ax.transAxes)
    items = [
        ("OK", "Bandwidth splits LOCATION, not detection", "#2e7d32"),
        ("OK", "Occupancy costs about 18 dB of EIRP", "#2e7d32"),
        ("OK", "Hover is blind (zero-Doppler notch): Pd = 0", "#2e7d32"),
        ("OK", "Sionna RT is exact for the room (0.02 dB)", "#2e7d32"),
        ("NO", "\"Anechoic, so clutter is weak\"", "#c62828"),
        ("NO", "\"RT approx Analytic, so the model is verified\"", "#c62828"),
        ("NO", "\"5G resolves the ghost into a 2nd drone\"", "#c62828"),
        ("NEW", "sigma drops 7.1 dB once occlusion is in (SBR)", "#1565c0"),
        ("NEW", "RT sigma is biased -21 dB, not noisy ($\\S$3)", "#1565c0"),
    ]
    y = 0.90
    for tag, s, c in items:
        ax.text(0.0, y, tag, fontsize=9.2, fontweight="bold", color=c,
                transform=ax.transAxes, va="top")
        ax.text(0.13, y, s, fontsize=9.3, color="#333", transform=ax.transAxes, va="top")
        y -= 0.098

    fig.supxlabel(
        "Data: outputs/bench_matrix.csv and bench_ghost.csv (report5), EIRP 12 dBm, N = 100 trials per cell, Pfa = 1e-4, radial pass.\n"
        "Panel (c) reconciles report4 and report5: report5's 'P = 100 %' is the p_ghost_det column (the CELL fires), while p_false - a hit at a bin\n"
        "the target does not already own - is 0 % everywhere. report4's floor-OFF control then showed the cell fires just as often with no floor at\n"
        "all, so those hits are the target's own range sidelobes. The ghost is real and it survives ECA; it just never becomes a second drone.",
        fontsize=9.2, color="0.45")
    return _save(fig, "report7_benchmark.png")


# =========================================================================== #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="render,pipeline,chamber,paths,radiomap,drones,rtlimit,benchmark,flight")
    ap.add_argument("--spp", type=int, default=SPP)
    a = ap.parse_args()
    only = set(a.only.split(","))
    os.makedirs(FIG, exist_ok=True); os.makedirs(REN, exist_ok=True)
    t0 = time.time()
    if "render" in only:
        render_all(spp=a.spp)
    if "pipeline" in only:
        fig_pipeline()
    if "chamber" in only:
        fig_chamber()
    if "paths" in only:
        fig_paths()
    if "radiomap" in only:
        fig_radiomap()
    if "drones" in only:
        fig_drones()
    if "rtlimit" in only:
        fig_rt_limit()
    if "benchmark" in only:
        fig_benchmark()
    if "flight" in only:
        gif_flight()
    print(f"\n✅ report7 그림 완료 ({time.time()-t0:.0f}s) → outputs/figures/report7_*")


if __name__ == "__main__":
    main()
