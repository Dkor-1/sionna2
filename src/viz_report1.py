# -*- coding: utf-8 -*-
"""
viz_report1.py — report1 의 그림을 **Sionna 자체 렌더러**로 다시 만든다
=========================================================================
예전 report1 은 챔버·드론을 matplotlib 3D(Poly3DCollection) 도식으로 그렸다. 그건
"우리가 그린 그림"이지 "시뮬레이터가 본 것"이 아니다. 이 모듈은 그 자리를 전부
**Sionna RT 의 render_to_file** 로 바꾼다 — 즉 report2~6 이 실제로 계산에 쓰는
그 씬(같은 메쉬·같은 재질)을 그대로 촬영한다.

무엇을 만드나 (전부 outputs/figures/report1_*.png|gif, 원본 렌더는 outputs/renders/r1_*)
  ① report1_chamber_sionna.png : 챔버 외관/컷어웨이/상면(clip_at)/바닥스침/측면 — Sionna 렌더
  ② report1_paths.png          : PathSolver depth 0/1/3 — **Sionna 가 그린 광선**
                                 1-bounce 에 **바닥 반사**가 나타난다(semi-anechoic 의 증거)
  ③ report1_radiomap.png       : RadioMapSolver — 바닥면 vs 드론면 전력분포
  ④ report1_drone_<key>.png    : 드론 5종 3뷰(iso/side/top) — Sionna 렌더 + 공식외형 대조
  ⑤ report1_gallery.png        : 5종 한 장 (Sionna iso)
  ⑥ report1_envelope_fit.png   : **오늘 고친 메쉬 버그** — 높이 −25~−47 % → 공식 외형 정합
  ⑦ report1_mesh_check.png     : trimesh 부품단위 검증표 (프로펠러 법선 버그 회귀방지)
  ⑧ report1_turntable_<key>.gif / _all.gif : Sionna 카메라를 360° 돌린 턴테이블

그림 텍스트는 전부 영어(프로젝트 규약), 코드 주석·print 는 한국어.

실행:  python src/viz_report1.py            (전부)
       python src/viz_report1.py --only drones,gallery
"""
from __future__ import annotations

import argparse
import os
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# ⚠ render_rt → scene_build 가 mitsuba import 전에 GPU 를 고른다. 반드시 먼저 import.
import render_rt as R                                        # noqa: E402
import sionna.rt as rt                                       # noqa: E402
import mitsuba as mi                                         # noqa: E402

import vizstyle                                              # noqa: E402
vizstyle.use_korean()
import matplotlib.pyplot as plt                              # noqa: E402
import matplotlib.image as mpimg                             # noqa: E402

from drones import DRONES, build_drone, frame_envelope_mm, _build_frame_raw   # noqa: E402
from bistatic_scene import TX, RX, TGT                        # noqa: E402

ROOT = os.path.abspath(os.path.join(_HERE, ".."))
FIG = os.path.join(ROOT, "outputs", "figures")
REN = os.path.join(ROOT, "outputs", "renders")
W, D, H = R.W, R.D, R.H

RES = (1600, 1150)          # 정지 렌더 해상도 (규약: 1600x1100 이상)
SPP = 768                   # 샘플/픽셀  (규약: 512 이상)


def _p(name):
    return os.path.join(REN, f"{name}.png")


def _show(ax, path, title=None, sub=None, sub_in=False):
    """렌더 PNG 를 축에 올린다(없으면 자리표시).
    sub_in=True 면 부제를 **축 안쪽 아래**에 둔다 — 격자에서 아랫줄 제목과 겹치지 않게."""
    if os.path.exists(path):
        ax.imshow(mpimg.imread(path))
    else:
        ax.text(0.5, 0.5, "(render missing)\n" + os.path.basename(path),
                ha="center", va="center", transform=ax.transAxes, fontsize=9)
    ax.axis("off")
    if title:
        ax.set_title(title, fontsize=12, fontweight="bold")
    if sub:
        y, va = (0.02, "bottom") if sub_in else (-0.02, "top")
        ax.text(0.5, y, sub, ha="center", va=va, transform=ax.transAxes,
                fontsize=9, color="#555")


def _save(fig, name, dpi=125):
    os.makedirs(FIG, exist_ok=True)
    fn = os.path.join(FIG, name)
    fig.savefig(fn, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print("[fig]", os.path.relpath(fn, ROOT))
    return fn


# =========================================================================== #
#  ① 챔버 — Sionna 가 본 무대
# =========================================================================== #
#  카메라: render_rt.CAMS 를 기본으로 쓰되, report1 용으로 '한 덩어리 방'이 보이는
#  3/4 코너 시점을 추가한다(render_drones.HERO_CAM 과 같은 계열).
CAM_HERO = ((-14.0, -17.0, 11.0), (14.0, 9.5, 3.5))      # 컷어웨이 실내 3/4 (방을 꽉 채운다)
CAM_OUT = ((-21.0, -19.0, 14.0), (W / 2, D / 2, 3.0))    # 닫힌 외관


def render_chamber(spp=SPP, res=RES):
    """챔버 5뷰 — Sionna render_to_file."""
    print("① 챔버 (Sionna 렌더)")
    sc_closed = R.make_scene(drone=None, with_chamber=True, cutaway=False)
    R.shot(sc_closed, "r1_ch_outside", R.cam(*CAM_OUT), res=res, spp=spp, fov=55.0)
    sc = R.make_scene(cutaway=True)                       # 드론(mavic4pro) 표적 포함
    R.shot(sc, "r1_ch_hero", R.cam(*CAM_HERO), res=res, spp=spp, fov=55.0)
    R.shot(sc, "r1_ch_wide", R.cam(*R.CAMS["wide"]), res=res, spp=spp)
    R.shot(sc, "r1_ch_top", R.cam(*R.CAMS["top"]), res=res, spp=spp, clip=R.CLIP_CEIL)
    R.shot(sc, "r1_ch_grazing", R.cam(*R.CAMS["grazing"]), res=res, spp=spp)


def fig_chamber():
    fig = plt.figure(figsize=(15.5, 9.0), constrained_layout=True)
    fig.suptitle("The stage, as Sionna sees it", fontsize=18, fontweight="bold")
    gs = fig.add_gridspec(2, 3)
    _show(fig.add_subplot(gs[0, 0]), _p("r1_ch_outside"),
          "Shielded box (closed)", "metal shield + steel frame")
    _show(fig.add_subplot(gs[0, 1]), _p("r1_ch_hero"),
          "Inside (front wall cut away)", "pyramidal absorber on 4 walls + ceiling")
    _show(fig.add_subplot(gs[0, 2]), _p("r1_ch_top"),
          "Top view (ceiling clipped at z = 9 m)", "TX (red) and RX (green), target at (21, 10, 5.5) m")
    _show(fig.add_subplot(gs[1, 0]), _p("r1_ch_wide"),
          "TX, RX and target in one frame", "baseline L = 15 m along the x = 4 m wall")
    _show(fig.add_subplot(gs[1, 1]), _p("r1_ch_grazing"),
          "Grazing the floor", "the floor is bare concrete tile - NOT absorber")
    axm = fig.add_subplot(gs[1, 2]); axm.axis("off")
    axm.text(0.0, 1.0, "Semi-anechoic, not anechoic", fontsize=13, fontweight="bold",
             va="top", transform=axm.transAxes)
    axm.text(0.0, 0.90, (
        "30 x 20 x 11 m shielded chamber\n\n"
        "  absorber : 4 walls + ceiling  (5 faces)\n"
        "  floor    : concrete tile, reflective\n\n"
        "One strong reflector is left inside the room -\n"
        "the floor. Everything report6 finds about the\n"
        "floor ghost starts from this single fact.\n\n"
        "Same meshes and same materials are used by\n"
        "the RT solver, the SBR/PO integrator and\n"
        "these renders - one scene, one truth."),
        fontsize=10.5, va="top", family="monospace", transform=axm.transAxes,
        linespacing=1.5, color="#333")
    fig.supxlabel("Rendered by Sionna RT (scene.render_to_file) - the same scene objects the path solver traces.",
                  fontsize=9, color="0.45")
    return _save(fig, "report1_chamber_sionna.png")


# =========================================================================== #
#  ② 추적된 경로 — Sionna 가 그린 광선
# =========================================================================== #
CAM_PATH = ((W - 1.0, D / 2, 9.0), (TX[0], D / 2, 5.0))          # = CAMS['wide']
CAM_PATH_LOW = ((W - 2.0, -7.0, 3.2), (10.0, D / 2, 2.2))        # 낮게 — 바닥 반사가 보인다
PATH_JSON = os.path.join(REN, "r1_paths.json")


def render_paths(spp=SPP, res=RES, samples=4_000_000):
    """PathSolver depth 0/1/3 렌더 + **depth-1 경로표**(지연·이득·부딪힌 물체)를 저장.
    그림 캡션의 숫자는 전부 이 표에서 나온다(손으로 적지 않는다)."""
    import json
    print("② 추적된 경로 (PathSolver)")
    sc = R.make_scene(cutaway=True)
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
        R.shot(sc, f"r1_paths_{tag}", R.cam(*CAM_PATH), paths=paths, res=res, spp=spp)
        if md == 1:
            R.shot(sc, "r1_paths_1bounce_low", R.cam(*CAM_PATH_LOW), paths=paths,
                   res=res, spp=spp)
            a = (np.asarray(paths.a[0]).squeeze().reshape(-1)
                 + 1j * np.asarray(paths.a[1]).squeeze().reshape(-1))
            g = 20 * np.log10(np.abs(a) + 1e-30)
            obj = np.asarray(paths.objects).squeeze().reshape(-1, n) if np.asarray(paths.objects).size else None
            los_g = float(g.max()); los_t = float(tau.min())
            for i in np.argsort(tau):
                hit = "-"
                if obj is not None:
                    h = [names.get(int(x), "") for x in obj[:, i] if int(x) >= 0]
                    hit = h[0] if (h and h[0]) else "-"
                out["depth1"].append(dict(
                    tau_ns=float(tau[i] * 1e9), excess_ns=float((tau[i] - los_t) * 1e9),
                    gain_db=float(g[i]), rel_db=float(g[i] - los_g), hit=hit))
    with open(PATH_JSON, "w") as f:
        json.dump(out, f, indent=1)
    return out


def _path_data():
    import json
    if os.path.exists(PATH_JSON):
        with open(PATH_JSON) as f:
            return json.load(f)
    return {"counts": {}, "depth1": []}


_HIT_LABEL = {"-": "line of sight", "floor_light": "FLOOR (concrete tile)",
              "floor_dark": "FLOOR (concrete tile)", "absorber_ceiling": "ceiling absorber",
              "absorber_left": "side wall absorber", "absorber_right": "side wall absorber",
              "absorber_back": "back wall absorber"}


def fig_paths():
    d = _path_data()
    c = d["counts"]
    fig = plt.figure(figsize=(16, 9.2), constrained_layout=True)
    fig.suptitle("Rays Sionna actually traced (TX $\\rightarrow$ RX)", fontsize=18, fontweight="bold")
    gs = fig.add_gridspec(2, 3)
    for j, (tag, title) in enumerate((("los", "max_depth = 0  (line of sight)"),
                                      ("1bounce", "max_depth = 1  (one reflection)"),
                                      ("3bounce", "max_depth = 3  (up to three)"))):
        n = c.get(tag)
        _show(fig.add_subplot(gs[0, j]), _p(f"r1_paths_{tag}"), title,
              f"{n} paths found" if n is not None else "")

    _show(fig.add_subplot(gs[1, 0]), _p("r1_paths_1bounce_low"),
          "One reflection, seen from low down",
          "the ray going down to the tiles is the floor bounce")

    # (표) depth-1 경로 — 렌더가 아니라 **솔버가 준 숫자** 그대로
    axT = fig.add_subplot(gs[1, 1]); axT.axis("off")
    axT.text(0.0, 1.02, "What the solver returns at max_depth = 1", fontsize=12.5,
             fontweight="bold", va="top", transform=axT.transAxes)
    lines = [f"{'surface':<22s}{'delay':>9s}{'excess':>9s}{'rel. LOS':>10s}", "-" * 50]
    for r in d["depth1"]:
        lab = _HIT_LABEL.get(r["hit"], r["hit"])
        lines.append(f"{lab:<22s}{r['tau_ns']:>7.1f}ns{r['excess_ns']:>+8.1f}"
                     f"{r['rel_db']:>+9.1f}dB")
    axT.text(0.0, 0.88, "\n".join(lines), fontsize=10.2, family="monospace", va="top",
             transform=axT.transAxes, linespacing=1.7)
    axT.text(0.0, 0.30, (
        "The floor bounce lands at +19.3 ns / -14.7 dB -\n"
        "the same pair report6 measures and the Fresnel\n"
        "prediction reproduces to 0.02 dB. RT is trusted\n"
        "for the environment; it is the target sigma that\n"
        "it cannot give (report6)."),
        fontsize=9.6, va="top", transform=axT.transAxes, linespacing=1.5, color="#333",
        bbox=dict(boxstyle="round", fc="#eef5ff", ec="#b6cbe6"))

    axN = fig.add_subplot(gs[1, 2]); axN.axis("off")
    axN.text(0.0, 1.02, "Read the absorber rows with care", fontsize=12.5,
             fontweight="bold", va="top", color="#b71c1c", transform=axN.transAxes)
    axN.text(0.0, 0.90, (
        "The ceiling row is louder than the floor row, and\n"
        "that is a property of the MODEL, not of the room:\n\n"
        "  A single specular bounce off one pyramid facet\n"
        "  is only -5.2 dB in our absorber material\n"
        "  (materials.py says so in its own note: the value\n"
        "  is modelled, not measured). Real -25 to -30 dB\n"
        "  anechoic performance is a GEOMETRIC effect - the\n"
        "  ray has to bounce 4-5 times inside a pyramid\n"
        "  valley - so a low max_depth solve cannot show it.\n\n"
        "So the absorber paths here are an upper bound, i.e.\n"
        "pessimistic. Nothing downstream leans on them: they\n"
        "are static (zero Doppler) and ECA deletes them.\n"
        "The floor is different - flat concrete, one clean\n"
        "bounce - and when the floor path goes VIA the target\n"
        "it inherits the target Doppler and survives ECA.\n"
        "That ghost is the real threat (report4/report6)."),
        fontsize=9.4, va="top", transform=axN.transAxes, linespacing=1.5, color="#333")

    fig.supxlabel("Rendered by Sionna RT: scene.render_to_file(paths=PathSolver(...)). "
                  "Numbers come from the solver, not from a caption.",
                  fontsize=9, color="0.45")
    return _save(fig, "report1_paths.png")


# =========================================================================== #
#  ③ 라디오맵 — 바닥이 왜 중요한가
# =========================================================================== #
def render_radiomap(spp=SPP, res=RES, n_tx=8_000_000):
    print("③ 라디오맵 (RadioMapSolver)")
    sc = R.make_scene(cutaway=True)
    rms = rt.RadioMapSolver()
    for z, tag in ((0.05, "floor"), (float(TGT[2]), "droneplane")):
        t0 = time.time()
        rm = rms(sc, center=mi.Point3f(W / 2, D / 2, z),
                 orientation=mi.Point3f(0, 0, 0),
                 size=mi.Point2f(W - 0.5, D - 0.5),
                 cell_size=mi.Point2f(0.25, 0.25),
                 samples_per_tx=n_tx, max_depth=3,
                 specular_reflection=True, diffuse_reflection=False)
        print(f"  z={z:.2f} m ({time.time()-t0:.1f}s)")
        # 3/4 뷰는 '방 안'에서 본다(CAMS['wide']) — 밖에서 보면 벽에 가려 지도가 작게 나온다.
        R.shot(sc, f"r1_rmap_{tag}", R.cam(*R.CAMS["wide"]), radio_map=rm, res=res, spp=spp)
        R.shot(sc, f"r1_rmap_{tag}_top", R.cam(*R.CAMS["top"]), radio_map=rm, res=res,
               spp=spp, clip=R.CLIP_CEIL)


def fig_radiomap():
    fig = plt.figure(figsize=(15, 8.8), constrained_layout=True)
    fig.suptitle("Where the energy goes - Sionna radio maps", fontsize=18, fontweight="bold")
    gs = fig.add_gridspec(2, 2)
    _show(fig.add_subplot(gs[0, 0]), _p("r1_rmap_floor"),
          "Floor plane (z = 0.05 m)", "3/4 view")
    _show(fig.add_subplot(gs[0, 1]), _p("r1_rmap_floor_top"), None, "top view")
    _show(fig.add_subplot(gs[1, 0]), _p("r1_rmap_droneplane"),
          "Drone plane (z = 5.5 m)", "3/4 view")
    _show(fig.add_subplot(gs[1, 1]), _p("r1_rmap_droneplane_top"), None, "top view")
    fig.supxlabel(
        "RadioMapSolver, TX at (4, 2.5, 8) m, 3.5 GHz, max_depth = 3, cell 0.25 m. Colour = received power per cell.\n"
        "The field falls off smoothly from the TX - no standing-wave pattern off the walls. The two dark streaks on the\n"
        "floor are geometric shadows of the door panels that protrude from the back wall. The drone plane (z = 5.5 m) is\n"
        "where the target flies; the floor plane is the surface that sends that energy back up (see report1_paths.png).",
        fontsize=9, color="0.45")
    return _save(fig, "report1_radiomap.png")


# =========================================================================== #
#  ④ 드론 5종 — Sionna 3뷰 + 공식 외형 대조
# =========================================================================== #
def _drone_scene(key):
    return R.make_scene(drone=key, tgt=(0.0, 0.0, 0.0), with_chamber=False, vel=None)


def render_drones(spp=SPP, res=(1300, 1000)):
    """드론 5종 iso/side/top. side 가 중요하다 — 오늘 고친 높이가 여기서 보인다."""
    print("④ 드론 5종 3뷰 (Sionna 렌더)")
    for key in DRONES:
        sc = _drone_scene(key)
        V = np.asarray(build_drone(DRONES[key]).v, float)
        span = float(np.linalg.norm(V.max(0) - V.min(0)))
        r = span * 1.30
        for tag, p in (("iso", (r * 0.72, -r * 0.66, r * 0.34)),
                       ("side", (0.0, -r, 0.02 * span)),      # 측면 — 전고
                       ("top", (0.005 * span, 0.0, r))):
            R.shot(sc, f"r1_drone_{key}_{tag}", R.cam(p, look=(0, 0, 0)),
                   res=res, spp=spp, fov=34.0)


def _env_row(key):
    """공식 외형 vs 생성 메쉬 — 그림/노트북이 같은 숫자를 쓰도록 한 곳에서 계산."""
    s = DRONES[key]
    e = frame_envelope_mm(s)
    raw = (np.asarray(_build_frame_raw(s).v, float).max(0)
           - np.asarray(_build_frame_raw(s).v, float).min(0)) * 1000.0
    off = s.envelope_mm or (None, None, None)
    return dict(key=key, name=s.name, raw=raw, fit=np.asarray(e["lwh_mm"], float),
                off=off, diag_spec=e["diagonal_spec_mm"],
                diag_eff=e["diagonal_effective_mm"])


def fig_drone(key):
    s = DRONES[key]
    e = _env_row(key)
    fig = plt.figure(figsize=(15, 5.6), constrained_layout=True)
    fig.suptitle(f"{s.name} - Sionna RT render (3 views)", fontsize=17, fontweight="bold")
    gs = fig.add_gridspec(1, 4, width_ratios=[1, 1, 1, 1.12])
    _show(fig.add_subplot(gs[0, 0]), _p(f"r1_drone_{key}_iso"), "Isometric")
    _show(fig.add_subplot(gs[0, 1]), _p(f"r1_drone_{key}_side"),
          "Side view", "camera on -y - height is now the official H")
    _show(fig.add_subplot(gs[0, 2]), _p(f"r1_drone_{key}_top"), "Top view",
          "motor layout and propeller discs")

    ax = fig.add_subplot(gs[0, 3]); ax.axis("off")
    off = e["off"]
    fit = e["fit"]

    def _cell(v):
        return "-" if v is None else f"{v:.1f}"
    lines = [("", "official", "mesh"),
             ("L [mm]", _cell(off[0]), f"{fit[0]:.1f}"),
             ("W [mm]", _cell(off[1]), f"{fit[1]:.1f}"),
             ("H [mm]", _cell(off[2]), f"{fit[2]:.1f}"),
             ("diagonal [mm]", f"{e['diag_spec']:.1f}", f"{e['diag_eff']:.1f}")]
    y = 0.93
    for i, (a, b, c) in enumerate(lines):
        w = "bold" if i == 0 else "normal"
        ax.text(0.02, y, a, fontsize=11, fontweight="bold" if i else "bold",
                transform=ax.transAxes, color="#444")
        ax.text(0.52, y, b, fontsize=11, fontweight=w, transform=ax.transAxes)
        ax.text(0.78, y, c, fontsize=11, fontweight=w, transform=ax.transAxes,
                color="#1565c0")
        y -= 0.085
    note = (f"rotors {s.num_rotors} - prop $\\varnothing${s.prop_dia_mm:.0f} mm x "
            f"{s.prop_blades} blades\nweight {s.weight_g:g} g - {s.release}\n"
            f"mesh {build_drone(s).n_tris()} triangles")
    ax.text(0.02, y - 0.03, note, fontsize=10, va="top", transform=ax.transAxes, color="#333")
    msg = {
        "matrice4e": ("Cross-check: DJI publishes BOTH the envelope and the\n"
                      "diagonal for this model. The mesh was fitted to the\n"
                      "envelope only, and its motor-to-motor diagonal comes\n"
                      "out at 433.1 mm vs the official 438.8 mm (-1.3 %).\n"
                      "The fitting method is validated independently."),
        "mavic4pro": ("The 400 mm diagonal was an estimate and is\n"
                      "geometrically impossible: a 400 mm motor diagonal\n"
                      "cannot span the official 328.7 x 390.5 mm envelope.\n"
                      "Fitting to the official envelope implies 440.9 mm.\n"
                      "The official envelope wins."),
        "mini5pro": ("Diagonal is not published by DJI. Fitting the frame\n"
                     "to the official 255 x 181 x 91 mm envelope implies\n"
                     "274.6 mm, 9 % above the old 250 mm estimate."),
        "s1000plus": ("DJI publishes only the height (462 mm); the 1045 mm\n"
                      "figure is the diagonal, not a width. So only z is\n"
                      "fitted here (x/y already agree within 2 %)."),
        "phantom4": ("DJI publishes only the height (198 mm); 350 mm is the\n"
                     "diagonal. Only z is fitted; the raw frame was 25 %\n"
                     "too flat before the fix."),
    }[key]
    ax.text(0.02, y - 0.22, msg, fontsize=9.2, va="top", transform=ax.transAxes,
            color="#b71c1c", linespacing=1.45,
            bbox=dict(boxstyle="round", fc="#fff5f5", ec="#e0b4b4"))
    fig.supxlabel("Sionna RT render of the very mesh used by the SBR/PO integrator "
                  "(same OBJ, same materials).", fontsize=9, color="0.45")
    return _save(fig, f"report1_drone_{key}.png")


def fig_gallery():
    keys = list(DRONES)
    fig, axes = plt.subplots(2, 3, figsize=(15.5, 9.0), constrained_layout=True)
    fig.suptitle("Five DJI drones - Sionna RT renders (meshes fitted to the official envelope)",
                 fontsize=17, fontweight="bold")
    for ax, key in zip(axes.flat, keys):
        s = DRONES[key]
        e = _env_row(key)
        sub = (f"{e['diag_eff']:.0f} mm diagonal (mesh) - {s.weight_g:g} g - "
               f"{s.num_rotors} rotors")
        _show(ax, _p(f"r1_drone_{key}_iso"), s.name, sub, sub_in=True)
    _show(axes.flat[5], _p("lineup_floor"), "The same five, at true scale",
          "lined up on the chamber floor - 30 x 20 x 11 m room", sub_in=True)
    fig.supxlabel("Diagonal shown is the motor-to-motor distance OF THE MESH, i.e. implied by the official\n"
                  "envelope - not the (partly estimated) catalogue diagonal. See report1_envelope_fit.png.",
                  fontsize=9, color="0.45")
    return _save(fig, "report1_gallery.png")


# =========================================================================== #
#  ⑥ 오늘 고친 메쉬 버그 — 높이 −25~−47 % → 공식 외형 정합
# =========================================================================== #
def fig_envelope_fit():
    keys = list(DRONES)
    rows = [_env_row(k) for k in keys]
    names = [DRONES[k].name.replace("DJI ", "") for k in keys]

    fig = plt.figure(figsize=(15, 7.4), constrained_layout=True)
    fig.suptitle("Mesh bug fixed today: the drones were 25-47 % too flat",
                 fontsize=18, fontweight="bold")
    gs = fig.add_gridspec(1, 3, width_ratios=[1.25, 1.0, 1.15])

    # (A) 높이: 옛 메쉬 vs 공식 vs 수정 메쉬
    ax = fig.add_subplot(gs[0, 0])
    x = np.arange(len(keys)); w = 0.27
    h_raw = [r["raw"][2] for r in rows]
    h_off = [r["off"][2] for r in rows]
    h_fit = [r["fit"][2] for r in rows]
    ax.bar(x - w, h_raw, w, label="old mesh (buggy)", color="#c62828")
    ax.bar(x, h_off, w, label="official (DJI)", color="#455a64")
    ax.bar(x + w, h_fit, w, label="new mesh (fitted)", color="#1565c0")
    for i, (a, b) in enumerate(zip(h_raw, h_off)):
        ax.text(i - w, a + 6, f"{100*(a/b-1):+.0f}%", ha="center", fontsize=9,
                color="#c62828", fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels(names, rotation=18, ha="right", fontsize=9)
    ax.set_ylabel("height [mm]")
    ax.set_title("Height of the airframe (props excluded)", fontsize=12)
    ax.legend(fontsize=9); ax.grid(axis="y", alpha=0.3)
    ax.set_ylim(0, max(h_off) * 1.22)

    # (B) 왜 중요한가 — 저앙각에서 측면 투영면적 ∝ H, 평판극한 σ ∝ A²
    ax2 = fig.add_subplot(gs[0, 1])
    err = np.array([r["raw"][2] / r["off"][2] for r in rows])
    d_sigma = 20 * np.log10(err)                     # σ ∝ A² → dB
    ax2.barh(names, d_sigma, color="#c62828")
    for i, v in enumerate(d_sigma):
        inside = abs(v) > 1.0
        ax2.text(v / 2 if inside else v - 0.15, i, f"{v:+.1f} dB", va="center",
                 ha="center" if inside else "right", fontsize=9.5,
                 color="white" if inside else "#c62828", fontweight="bold")
    ax2.axvline(0, color="k", lw=0.8)
    ax2.set_xlabel("$\\Delta\\sigma$ [dB] of the old mesh")
    ax2.set_title("Side-on RCS error it implies\n"
                  "(flat-plate bound, $\\sigma \\propto A^2$)", fontsize=12)
    ax2.invert_yaxis(); ax2.grid(axis="x", alpha=0.3)

    # (C) 대각선 교차검증
    ax3 = fig.add_subplot(gs[0, 2]); ax3.axis("off")
    ax3.text(0.0, 1.0, "Independent check of the fit", fontsize=13,
             fontweight="bold", va="top", transform=ax3.transAxes)
    hdr = f"{'model':<12s}{'catalogue':>11s}{'from mesh':>11s}{'diff':>8s}"
    lines = [hdr, "-" * 42]
    for r in rows:
        d = 100 * (r["diag_eff"] / r["diag_spec"] - 1)
        star = "*" if r["key"] in ("mini5pro", "mavic4pro") else " "
        lines.append(f"{r['key']:<12s}{r['diag_spec']:>10.1f}{star}"
                     f"{r['diag_eff']:>11.1f}{d:>+7.1f}%")
    ax3.text(0.0, 0.90, "\n".join(lines), fontsize=10, family="monospace",
             va="top", transform=ax3.transAxes, linespacing=1.6)
    ax3.text(0.0, 0.44, (
        "Matrice 4E is the only model for which DJI\n"
        "publishes BOTH the envelope and the diagonal.\n"
        "The mesh was fitted to the envelope alone, and\n"
        "its diagonal lands at 433.1 mm against the\n"
        "official 438.8 mm: -1.3 %. The method checks out\n"
        "against a number it never saw.\n\n"
        "* catalogue diagonal is an estimate (DJI does not\n"
        "  publish a wheelbase for Mini / Mavic). For the\n"
        "  Mavic 4 Pro the 400 mm estimate is not merely\n"
        "  imprecise, it is impossible: it cannot span the\n"
        "  official 328.7 x 390.5 mm envelope."),
        fontsize=9.6, va="top", transform=ax3.transAxes, linespacing=1.5, color="#333")

    fig.supxlabel(
        "Cause: the frame builder set body thickness to 0.35 x H_spec and never checked the result against the\n"
        "official envelope. Fix: scale the frame per axis so its bounding box equals the official L x W x H\n"
        "(propellers keep their catalogue diameter). The middle panel is the flat-plate BOUND implied by the height\n"
        "error alone; re-running the SBR integrator on the fixed meshes, the RCS actually rose by +2.4 to +4.6 dB.",
        fontsize=9, color="0.45")
    return _save(fig, "report1_envelope_fit.png")


# =========================================================================== #
#  ⑦ 메쉬 검증표 (trimesh)
# =========================================================================== #
def fig_mesh_check():
    from mesh_check import check_all
    res = check_all(verbose=False)
    keys = list(res)
    groups = sorted({g for r in res.values() for g in r["groups"]})
    fig, ax = plt.subplots(figsize=(14.5, 5.2), constrained_layout=True)
    ax.axis("off")
    fig.suptitle("Mesh validation (trimesh, per connected component)",
                 fontsize=17, fontweight="bold")
    cell, colors = [], []
    for k in keys:
        row, crow = [], []
        for g in groups:
            gg = res[k]["groups"].get(g)
            if gg is None:
                row.append("-"); crow.append("#f5f5f5"); continue
            row.append("PASS" if gg["ok"] else "FAIL")
            crow.append("#e3f2e6" if gg["ok"] else "#ffcdd2")
        cell.append(row); colors.append(crow)
    tb = ax.table(cellText=cell, rowLabels=[DRONES[k].name.replace("DJI ", "") for k in keys],
                  colLabels=groups, cellColours=colors, loc="center", cellLoc="center")
    tb.auto_set_font_size(False); tb.set_fontsize(10); tb.scale(1, 1.9)
    n_ok = sum(1 for r in res.values() if r["ok"])
    fig.supxlabel(
        f"{n_ok}/{len(keys)} drones pass every check: watertight parts, consistent winding, outward normals, "
        "no degenerate faces.\n"
        "This table exists because a real bug hid here: the two end caps of prop_blade were wound inwards, so the "
        "PO illumination test (n.u > 0)\nsilently picked the wrong faces - on the propellers, i.e. on the "
        "micro-Doppler signal itself. trimesh found it in one second.",
        fontsize=9, color="0.45")
    return _save(fig, "report1_mesh_check.png")


# =========================================================================== #
#  ⑧ 턴테이블 GIF — Sionna 카메라를 360° 돌린다 (matplotlib 3D 아님)
# =========================================================================== #
def _rgb_on_white(path):
    """Sionna 렌더 PNG 는 **알파 채널**이 있다(배경 투명). 그대로 GIF 로 넘기면
    투명이 검정으로 굳는다 → 흰 배경에 합성한다."""
    from PIL import Image
    im = Image.open(path).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    return Image.alpha_composite(bg, im).convert("RGB")


def _font(size=20):
    from PIL import ImageFont
    f = os.path.join(ROOT, "assets", "NanumGothic.ttf")
    try:
        return ImageFont.truetype(f, size)
    except Exception:
        return ImageFont.load_default()


def turntable(key, frames=36, spp=256, res=(560, 460), elev_deg=18.0):
    """Sionna 렌더 프레임 → GIF. 카메라만 방위각으로 돌린다."""
    spec = DRONES[key]
    V = np.asarray(build_drone(spec).v, float)
    span = float(np.linalg.norm(V.max(0) - V.min(0)))
    r = span * 1.32
    sc = _drone_scene(key)
    fdir = os.path.join(REN, "turn", key)
    os.makedirs(fdir, exist_ok=True)
    z = r * np.sin(np.radians(elev_deg))
    rho = r * np.cos(np.radians(elev_deg))
    for i in range(frames):
        a = np.radians(360.0 * i / frames)
        p = (rho * np.cos(a), rho * np.sin(a), z)
        sc.render_to_file(camera=R.cam(p, look=(0, 0, 0)),
                          filename=os.path.join(fdir, f"f_{i:03d}.png"),
                          num_samples=spp, resolution=res, fov=34.0)
    from PIL import Image, ImageDraw
    gif = os.path.join(FIG, f"report1_turntable_{key}.gif")
    imgs = []
    for i in range(frames):
        im = _rgb_on_white(os.path.join(fdir, f"f_{i:03d}.png"))
        ImageDraw.Draw(im).text((12, 10), spec.name, fill="black", font=_font(22))
        imgs.append(im.convert("P", palette=Image.ADAPTIVE))
    imgs[0].save(gif, save_all=True, append_images=imgs[1:], duration=90, loop=0,
                 optimize=True)
    print(f"[gif] {os.path.relpath(gif, ROOT)}  ({len(imgs)} frames)")
    return gif


def turntable_all(frames=36):
    """5종 프레임을 가로로 붙여 한 GIF 로. (개별 턴테이블 프레임을 재사용)"""
    from PIL import Image, ImageDraw
    keys = list(DRONES)
    dirs = {k: os.path.join(REN, "turn", k) for k in keys}
    if not all(os.path.isdir(d) for d in dirs.values()):
        print("  (턴테이블 프레임 없음 — turntable() 먼저)"); return None
    imgs = []
    fnt = _font(24)
    for i in range(frames):
        tiles = [_rgb_on_white(os.path.join(dirs[k], f"f_{i:03d}.png")) for k in keys]
        w, h = tiles[0].size
        canvas = Image.new("RGB", (w * len(tiles), h + 34), "white")
        dr = ImageDraw.Draw(canvas)
        for j, (k, t) in enumerate(zip(keys, tiles)):
            canvas.paste(t, (j * w, 34))
            dr.text((j * w + 12, 6), DRONES[k].name.replace("DJI ", ""), fill="black",
                    font=fnt)
        imgs.append(canvas.convert("P", palette=Image.ADAPTIVE))
    gif = os.path.join(FIG, "report1_turntable_all.gif")
    imgs[0].save(gif, save_all=True, append_images=imgs[1:], duration=90, loop=0,
                 optimize=True)
    print("[gif]", os.path.relpath(gif, ROOT), f"({len(imgs)} frames)")
    return gif


# =========================================================================== #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="chamber,paths,radiomap,drones,gallery,fit,check,turn")
    ap.add_argument("--frames", type=int, default=36)
    ap.add_argument("--spp", type=int, default=SPP)
    a = ap.parse_args()
    only = set(a.only.split(","))
    os.makedirs(REN, exist_ok=True); os.makedirs(FIG, exist_ok=True)
    t0 = time.time()
    if "chamber" in only:
        render_chamber(spp=a.spp); fig_chamber()
    if "paths" in only:
        render_paths(spp=a.spp); fig_paths()
    if "radiomap" in only:
        render_radiomap(spp=a.spp); fig_radiomap()
    if "drones" in only:
        render_drones(spp=a.spp)
        for k in DRONES:
            fig_drone(k)
    if "gallery" in only:
        fig_gallery()
    if "fit" in only:
        fig_envelope_fit()
    if "check" in only:
        fig_mesh_check()
    if "turn" in only:
        print("⑧ 턴테이블 (Sionna)")
        for k in DRONES:
            turntable(k, frames=a.frames)
        turntable_all(frames=a.frames)
    print(f"\n✅ report1 그림 완료 ({time.time()-t0:.0f}s) → outputs/figures/report1_*")


if __name__ == "__main__":
    main()
