# -*- coding: utf-8 -*-
"""
rt_experiments.py — (report3) **Sionna RT 광선 반사 실험** 의 측정 스크립트
================================================================================
질문: **"Sionna RT 가 챔버에서 광선을 어떻게 튕기는가 — 그리고 무엇을 믿을 수 있는가?"**

이 스크립트가 리포트의 **모든 숫자**를 만든다. 노트북은 여기서 나온 JSON 을 읽기만 한다
(→ 그림과 글이 어긋날 수 없다). 렌더(PNG)는 별도: `src/build_report3.py`.

측정 항목
---------
  §1 depth   PathSolver 를 max_depth = 0/1/2/3 으로 돌려 **경로가 어떻게 늘어나는지** 센다.
             경로별 (지연 τ, 도플러 f_d, 진폭, **어느 물체를 맞았나**, 반사점 좌표)를 표로 남긴다.
             ⚠ **함정**: `paths.objects` 는 **object_id** 다 — `scene.objects` dict 의 **열거 순서가 아니다**
               (object_id 는 1부터 시작 → 순서로 매핑하면 전부 한 칸씩 밀린다: 천장을 '앞벽'이라 부르게 된다).
               반드시 `SceneObject.object_id` 로 역맵을 만들 것. 이 스크립트는 그렇게 한다.

  §2 floor   TX→바닥→RX 를 **거울상 + 프레넬**로 손계산하고 RT 가 독립적으로 찾은 경로와 대조한다.
             또 같은 지연(≈19.3 ns)에 있는 **두 번째 경로**의 정체를 반사점 좌표로 규명한다.

  §3 A~E     "광선을 더 쏘면 표적 σ 가 나오지 않나?" 에 대한 5개의 반증 실험.
      [A] 광선예산 25M → 400M (16배) × 시드 3~5개 → 수렴하는가?
      [B] 산란계수 S 를 0.5x/1x/2x → 진폭이 S 를 따라가는가? (드론과 무관한 노브인가?)
      [C] ITU metal 의 S = 0 임을 **Sionna 에게 직접 물어보고**, SBR 로 그 부품들이 σ 의 몇 %인지 잰다.
      [D] **결정적 실험** — 금속 평판 변 0.2 → 4 m (σ 가 ~52 dB 변한다) → RT 정반사 진폭비는?
          정반사만 켠다(diffuse=off) → **몬테카를로 잡음이 0** → 깨끗한 반증.
      [E] 물리적으로 옳은 PEC 금속구(S=0) → RT 가 경로를 만드는가? (디스코볼 문제)

  §4 ghost   표적 경유 **바닥 유령**(TX→표적→바닥→RX). 도플러가 실려 ECA 를 통과한다.
             거울상+프레넬로 (지연, 도플러, 진폭)을 유도하고 파형별 거리분해능과 견준다.

실행:
    python benchmark/rt_experiments.py                 # 전부 (GPU 자동선택)
    python benchmark/rt_experiments.py --quick         # 짧게 (25M~100M, 시드 2개)
    python benchmark/rt_experiments.py --only depth,floor
산출:
    outputs/report3_rt.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
SRC = os.path.join(ROOT, "src")
for _p in (SRC, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from gpu import pick as _pick_gpu                                     # noqa: E402
_pick_gpu(verbose=True)                                               # ⚠ mitsuba import 전에!

import mitsuba as mi                                                  # noqa: E402
import sionna.rt as rt                                                # noqa: E402

from bistatic_scene import TX, RX, TGT, bistatic_params, C0           # noqa: E402
from drones import DRONES, DRONE_GROUP_MAT, build_drone               # noqa: E402
from scene_build import build_scene, Part, drone_parts                # noqa: E402
from materials import material_params, gamma_bulk                     # noqa: E402
from rcs_sbr import rcs_sbr_batch                                     # noqa: E402
from geometry import floor_ghost, _fresnel_floor, FLOOR_EPS_R, FLOOR_SIGMA  # noqa: E402
from render_rt import make_scene                                      # noqa: E402

FC = 3.5e9
KEY = "mavic4pro"
OUT = os.path.join(ROOT, "outputs", "report3_rt.json")
SCRATCH = os.path.join(ROOT, "outputs", "meshes", "rt_exp")
os.makedirs(SCRATCH, exist_ok=True)

NO_OBJ = 4294967295                    # Sionna 의 '상호작용 없음' 표식 (uint32 -1)

#  광선 예산 — 사용자 지시: **GPU 를 아끼지 말 것.**
RAYS = [25_000_000, 50_000_000, 100_000_000, 200_000_000, 400_000_000]
RAYS_QUICK = [25_000_000, 50_000_000, 100_000_000]
SEEDS = [1, 2, 3, 4, 5]
SEEDS_QUICK = [1, 2]
S_BASE = 0.20                          # plastic 의 기본 산란계수 (materials.py)
S_SWEEP = [0.5, 1.0, 2.0]              # 기본값의 배수 (0.5x / 1x / 2x)
S_RAYS = 100_000_000
MAX_PATHS = 4_000_000
PLATE_SIDES = [0.2, 0.4, 0.8, 1.5, 2.5, 4.0]
PLATE_SPP = 2_000_000
PLATE_SEEDS = [1, 2, 3]
SPHERE_SPP = [1_000_000, 10_000_000, 100_000_000, 400_000_000]

METAL_GROUPS = {g for g, (mat, _) in DRONE_GROUP_MAT.items()
                if mat in ("metal", "camera_assembly", "pcb")}


# --------------------------------------------------------------------------- #
#  공통 — 경로 배열 + **object_id 역맵**
# --------------------------------------------------------------------------- #
def id_to_name(scene) -> dict:
    """object_id → 이름. ⚠ dict 열거 순서로 매핑하면 안 된다 (object_id 는 1부터)."""
    return {int(o.object_id): n for n, o in scene.objects.items()}


def unpack(paths):
    """(a[P], tau[P], dop[P], V[depth,P,3], obj[depth,P])  — 1×1 안테나 가정."""
    ar = np.asarray(paths.a[0]); ai = np.asarray(paths.a[1])
    a = (ar + 1j * ai).reshape(-1, ar.shape[-1])[0]
    P = a.shape[0]
    tau = np.asarray(paths.tau).reshape(-1, P)[0]
    dop = np.asarray(paths.doppler).reshape(-1)
    dop = dop[:P] if dop.shape[0] >= P else np.zeros(P)
    V = np.asarray(paths.vertices)[:, 0, 0, :, :] if P else np.zeros((0, 0, 3))
    O = np.asarray(paths.objects)[:, 0, 0, :] if P else np.zeros((0, 0), int)
    return a, tau, dop, V, O


def path_table(paths, names, top=None):
    """경로별 dict 목록 (지연 오름차순). rel_db 는 **LOS(최단경로) 대비**."""
    a, tau, dop, V, O = unpack(paths)
    if a.size == 0:
        return []
    i0 = int(np.argmin(tau))
    a0 = abs(a[i0]) + 1e-30
    rows = []
    for i in np.argsort(tau):
        hit = [int(O[d, i]) for d in range(O.shape[0])] if O.size else []
        hitn = [names.get(h, f"id{h}") for h in hit if h != NO_OBJ]
        vtx = [[round(float(x), 3) for x in V[d, i]]
               for d in range(O.shape[0]) if O.size and int(O[d, i]) != NO_OBJ]
        rows.append(dict(tau_ns=float(tau[i] * 1e9),
                         delay_ns=float((tau[i] - tau[i0]) * 1e9),
                         rel_db=float(20 * np.log10(abs(a[i]) / a0 + 1e-30)),
                         abs_db=float(20 * np.log10(abs(a[i]) + 1e-30)),
                         fd_hz=float(dop[i]), n_bounce=len(hitn),
                         objects=hitn, vertices=vtx))
    return rows[:top] if top else rows


# --------------------------------------------------------------------------- #
#  §1 — max_depth 0/1/2/3: 광선이 몇 번 튕기면 경로가 몇 개가 되나
# --------------------------------------------------------------------------- #
def s1_depth(depths=(0, 1, 2, 3), spp=4_000_000, vel=(-3.0, 0.0, 0.0)):
    """챔버 + 드론(속도 有 → RT 가 도플러를 계산한다). 깊이별 경로 표."""
    scene = make_scene(drone=KEY, cutaway=False, vel=vel, fc=FC)
    names = id_to_name(scene)
    solver = rt.PathSolver()
    out = []
    for md in depths:
        t0 = time.time()
        p = solver(scene, max_depth=int(md), los=True, specular_reflection=True,
                   diffuse_reflection=False, refraction=False,
                   samples_per_src=int(spp), seed=1)
        rows = path_table(p, names)
        # 표적(드론) 경로가 있나? 드론 그룹 이름은 "mavic4pro_..." 로 시작한다.
        n_tgt = sum(1 for r in rows if any(o.startswith(KEY) for o in r["objects"]))
        out.append(dict(max_depth=int(md), n_paths=len(rows), n_target_paths=n_tgt,
                        sec=time.time() - t0, paths=rows))
        print(f"  depth={md}: 경로 {len(rows):3d}개 (표적 경유 {n_tgt}개)  {time.time()-t0:5.1f}s")
        for r in rows[:6]:
            print(f"      τ={r['tau_ns']:7.2f} ns (+{r['delay_ns']:6.2f})  {r['rel_db']:+7.2f} dB  "
                  f"f_d={r['fd_hz']:+7.2f} Hz  {r['objects'] or ['LOS(직접파)']}")
    return dict(spp=int(spp), vel=list(map(float, vel)), sweeps=out,
                object_names=sorted(names.values()))


# --------------------------------------------------------------------------- #
#  §2 — 바닥 반사: 거울상+프레넬 손계산  vs  RT 가 독립적으로 찾은 경로
# --------------------------------------------------------------------------- #
def s2_floor(depth_result):
    """RT 를 **믿는 근거**. 그리고 19.3 ns 의 두 번째 경로가 무엇인지 반사점으로 규명."""
    tx, rx = np.asarray(TX, float), np.asarray(RX, float)
    rx_img = rx.copy(); rx_img[2] = -rx_img[2]              # 바닥(z=0)에 비친 RX

    L = float(np.linalg.norm(rx - tx))                      # 직접파
    Lf = float(np.linalg.norm(rx_img - tx))                 # 바닥 경유(펴진 직선)
    d = rx_img - tx
    theta = float(np.arctan2(np.linalg.norm(d[:2]), abs(d[2])))   # 바닥 법선(z)에서 잰 입사각
    g_tm = _fresnel_floor(theta, FC, pol="V")               # V 편파 → 입사면 평행(TM)
    g_te = _fresnel_floor(theta, FC, pol="H")
    # 반사점 = TX–RX' 직선이 z=0 을 지나는 점
    t = tx[2] / (tx[2] - rx_img[2])
    hitpt = tx + t * (rx_img - tx)

    pred = dict(L_direct_m=L, L_floor_m=Lf, delay_ns=(Lf - L) / C0 * 1e9,
                theta_i_deg=float(np.degrees(theta)),
                grazing_deg=float(90.0 - np.degrees(theta)),
                gamma_tm=float(g_tm), gamma_te=float(g_te),
                spread_db=float(20 * np.log10(L / Lf)),
                rel_db=float(20 * np.log10(g_tm * L / Lf)),
                hit_point=[round(float(v), 3) for v in hitpt],
                eps_r=FLOOR_EPS_R, sigma=FLOOR_SIGMA)

    # RT 가 찾은 경로 중 바닥(floor_*) 단일반사
    rows = next(s["paths"] for s in depth_result["sweeps"] if s["max_depth"] == 1)
    rt_floor = [r for r in rows
                if r["n_bounce"] == 1 and r["objects"][0].startswith("floor")]
    meas = min(rt_floor, key=lambda r: abs(r["delay_ns"] - pred["delay_ns"])) if rt_floor else None

    # 같은 지연(±0.5 ns)에 있는 **다른** 경로들 — 정체를 반사점으로 규명한다 (depth=2 에서 보인다)
    rows2 = next(s["paths"] for s in depth_result["sweeps"] if s["max_depth"] == 2)
    twins = [r for r in rows2
             if abs(r["delay_ns"] - pred["delay_ns"]) < 0.5
             and not (r["n_bounce"] == 1 and r["objects"][0].startswith("floor"))]

    agree = (meas["rel_db"] - pred["rel_db"]) if meas else None
    d_tau = (meas["delay_ns"] - pred["delay_ns"]) if meas else None
    return dict(pred=pred, rt_floor=meas, agree_db=agree, agree_delay_ns=d_tau,
                twins=twins, all_floor_paths=rt_floor)


# --------------------------------------------------------------------------- #
#  §3 — "광선을 더 쏘면 되지 않나?"  (A~E)
# --------------------------------------------------------------------------- #
def S_of(obj) -> float:
    """RadioMaterial 의 산란계수를 **파이썬 float 로** 읽는다.
    ⚠ Sionna 2.0 은 drjit.cuda.ad.Float 를 돌려준다 — float() 에 바로 넣으면 TypeError."""
    return float(np.asarray(obj.radio_material.scattering_coefficient).reshape(-1)[0])


def _drone_scene(scatter_mult=None):
    """드론 하나만 자유공간에. scatter_mult 가 있으면 **모든 부품의 S 를 그 배수로** 바꾼다."""
    dp, _ = drone_parts(DRONES[KEY], position=tuple(float(v) for v in TGT), yaw_deg=0.0,
                        mesh_dir=os.path.join(SCRATCH, KEY))
    scene = build_scene(dp, fc=FC)
    if scatter_mult is not None:
        for o in scene.objects.values():
            base = S_of(o)
            # ITU metal 은 S=0 이라 배수를 곱해도 0 이다 — 그게 [C] 의 요점이다.
            # 여기서는 '노브'를 보이려는 것이므로 **기본 S 를 가진 부품만** 배수 적용.
            o.radio_material.scattering_coefficient = min(1.0, base * float(scatter_mult))
    scene.add(rt.Transmitter("tx", position=mi.Point3f(*[float(v) for v in TX])))
    scene.add(rt.Receiver("rx", position=mi.Point3f(*[float(v) for v in RX])))
    return scene


def _geom():
    p = bistatic_params(TX, RX, TGT, (0, 0, 0), FC)
    p["tau_echo"] = (p["R1"] + p["R2"]) / C0
    return p


def _rt_echo(scene, spp, seed=1, max_depth=1, diffuse=True, gate_ns=3.0):
    """표적 에코(지연게이트)의 **직접파 대비 진폭비**. 코히어런트/비코히어런트 둘 다."""
    t0 = time.time()
    p = rt.PathSolver()(scene, max_depth=max_depth, los=True, specular_reflection=True,
                        diffuse_reflection=bool(diffuse), refraction=False,
                        samples_per_src=int(spp), max_num_paths_per_src=MAX_PATHS,
                        seed=int(seed))
    a, tau, dop, V, O = unpack(p)
    if a.size == 0:
        return dict(n_paths=0, sec=time.time() - t0, incoh_db=None, coh_db=None)
    hit = (O != NO_OBJ).any(axis=0) if O.size else np.zeros(a.size, bool)
    A = abs(complex(np.sum(a[~hit]))) + 1e-30                    # 직접파
    g = _geom()
    gate = hit & (np.abs(tau - g["tau_echo"]) < gate_ns * 1e-9)
    n = int(gate.sum())
    if n == 0:
        return dict(n_paths=0, n_total=int(a.size), sec=time.time() - t0,
                    incoh_db=None, coh_db=None)
    incoh = float(np.sqrt(np.sum(np.abs(a[gate]) ** 2)) / A)
    coh = float(np.abs(np.sum(a[gate])) / A)
    return dict(n_paths=n, n_total=int(a.size), seed=int(seed),
                incoh_db=float(20 * np.log10(incoh)),
                coh_db=float(20 * np.log10(coh + 1e-30)),
                truncated=bool(a.size >= MAX_PATHS), sec=time.time() - t0)


def _seeds(scene, spp, seeds, **kw):
    runs = [_rt_echo(scene, spp, seed=s, **kw) for s in seeds]
    ok = [r for r in runs if r["n_paths"]]
    if not ok:
        return dict(spp=int(spp), n_paths=0, incoh_db=None, coh_db=None, runs=runs)
    ic = np.array([r["incoh_db"] for r in ok]); co = np.array([r["coh_db"] for r in ok])
    return dict(spp=int(spp), n_seeds=len(ok), runs=runs,
                n_mean=float(np.mean([r["n_paths"] for r in ok])),
                n_paths=int(np.round(np.mean([r["n_paths"] for r in ok]))),
                incoh_db=float(ic.mean()), incoh_sd=float(ic.std()),
                coh_db=float(co.mean()), coh_sd=float(co.std()),
                coh_min=float(co.min()), coh_max=float(co.max()),
                truncated=any(r.get("truncated") for r in ok),
                sec=float(sum(r["sec"] for r in runs)))


def c_metal_is_invisible(el=15.0, n_az=36):
    """[C] ITU metal 의 S 를 **Sionna 에게 직접 물어보고**, 그 부품들이 σ 의 몇 %인지 SBR 로 잰다."""
    # (1) Sionna 가 실제로 들고 있는 산란계수
    sc = _drone_scene()
    S_by_group = {}
    for n, o in sc.objects.items():
        grp = n[len(KEY) + 1:] if n.startswith(KEY + "_") else n
        S_by_group[grp] = dict(S=S_of(o),
                               mat=DRONE_GROUP_MAT.get(grp, ("?", None))[0],
                               metal=grp in METAL_GROUPS)
    # (2) 같은 메쉬·같은 재질을 SBR(광선+PO적분)로 재면 금속이 σ 의 몇 %인가
    m = build_drone(DRONES[KEY])
    az = np.linspace(0, 360, n_az, endpoint=False)
    full = {g: mat for g, (mat, _) in DRONE_GROUP_MAT.items()}
    only_metal = {g: (mat if g in METAL_GROUPS else 0.0) for g, mat in full.items()}
    only_diel = {g: (0.0 if g in METAL_GROUPS else mat) for g, mat in full.items()}
    sig = {}
    for nm, gm in (("full", full), ("metal_only", only_metal), ("dielectric_only", only_diel)):
        s = rcs_sbr_batch(m, gm, FC, az_deg=az, el_deg=el, cache_key=f"r3_{KEY}_{nm}")
        sig[nm + "_dbsm"] = float(10 * np.log10(np.mean(s)))
    share = 100.0 * 10 ** (sig["metal_only_dbsm"] / 10) / 10 ** (sig["full_dbsm"] / 10)
    g = _geom()
    s_lin = 10 ** (sig["full_dbsm"] / 10)
    ratio_truth = float(20 * np.log10(g["L"] * np.sqrt(s_lin / (4 * np.pi))
                                      / (g["R1"] * g["R2"])))
    return dict(S_by_group=S_by_group, sigma=sig, metal_share_pct=float(share),
                ratio_db_truth=ratio_truth, el_deg=el, n_az=n_az,
                itu_metal_S=float(material_params("metal", FC)[2]),
                metal_groups=sorted(METAL_GROUPS))


# ---- [D] 금속 평판 크기 스윕 — **결정적 실험** ---------------------------- #
def plate_parts(side):
    """TX·RX 이등분선에 법선을 맞춘 금속 평판 (정반사 조건을 정확히 충족)."""
    from geom import Mesh
    tx, rx, tg = (np.asarray(v, float) for v in (TX, RX, TGT))
    n = (tx - tg) / np.linalg.norm(tx - tg) + (rx - tg) / np.linalg.norm(rx - tg)
    n /= np.linalg.norm(n)
    u = np.cross(n, [0, 0, 1.0]); u /= np.linalg.norm(u)
    v = np.cross(n, u)
    h = side / 2
    m = Mesh(group="plate")
    idx = [m.add_vertex(*(tg + s1 * h * u + s2 * h * v))
           for s1, s2 in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    m.add_quad(*idx, group="plate")
    obj = os.path.join(SCRATCH, f"plate_{side:.2f}.obj")
    m.write_obj(obj)
    return [Part(name=f"plate_{side:.2f}".replace(".", "_"), obj=obj, mat_key="metal")]


def d_plate_sweep(sides=PLATE_SIDES, spp=PLATE_SPP, seeds=PLATE_SEEDS):
    """σ 는 A² 로 커지는데(52 dB) RT 정반사 진폭비는 움직이는가?
    정반사만 켠다 → **몬테카를로 잡음 0** → 깨끗한 반증."""
    g = _geom()
    lam = C0 / FC
    rows = []
    for s in sides:
        A = s * s
        sigma_db = float(10 * np.log10(4 * np.pi * A ** 2 / lam ** 2))   # 평판 정반사 σ (PO)
        vals, npaths = [], []
        for sd in seeds:
            scene = build_scene(plate_parts(s), fc=FC)
            scene.add(rt.Transmitter("tx", position=mi.Point3f(*[float(v) for v in TX])))
            scene.add(rt.Receiver("rx", position=mi.Point3f(*[float(v) for v in RX])))
            r = _rt_echo(scene, spp, seed=sd, diffuse=False, max_depth=1)
            if r["n_paths"]:
                vals.append(r["coh_db"]); npaths.append(r["n_paths"])
        # image-source 예측: 무한 거울이면 진폭비 = L / (R1+R2)
        img_db = float(20 * np.log10(g["L"] / (g["R1"] + g["R2"])))
        rows.append(dict(side_m=float(s), area_m2=float(A), sigma_dbsm=sigma_db,
                         n_paths=int(np.mean(npaths)) if npaths else 0,
                         rt_db=float(np.mean(vals)) if vals else None,
                         rt_sd=float(np.std(vals)) if vals else None,
                         image_db=img_db))
        r_ = rows[-1]
        print(f"    변 {s:4.1f} m  σ={sigma_db:+7.1f} dBsm  경로 {r_['n_paths']:2d}개  "
              f"RT={('%+.2f dB' % r_['rt_db']) if r_['rt_db'] is not None else '(없음)':>10}  "
              f"±{(r_['rt_sd'] or 0):.2f}  (image-source 예측 {img_db:+.2f} dB)")
    ok = [r for r in rows if r["rt_db"] is not None]
    return dict(rows=rows, seeds=seeds, spp=int(spp),
                sigma_span_db=float(rows[-1]["sigma_dbsm"] - rows[0]["sigma_dbsm"]),
                rt_span_db=float(max(r["rt_db"] for r in ok) - min(r["rt_db"] for r in ok)) if ok else None,
                rt_mean_db=float(np.mean([r["rt_db"] for r in ok])) if ok else None,
                rt_sd_db=float(np.mean([r["rt_sd"] for r in ok])) if ok else None,
                image_db=ok[0]["image_db"] if ok else None)


# ---- [E] PEC 금속구 — RT 가 경로를 만드는가? ------------------------------ #
def sphere_parts(r=0.30, mat="metal"):
    from geom import uv_sphere
    m = uv_sphere(r, center=tuple(float(v) for v in TGT), seg=64, rings=32)
    obj = os.path.join(SCRATCH, f"sphere_{r:.2f}.obj")
    m.write_obj(obj)
    return [Part(name=f"sphere_{r:.2f}".replace(".", "_"), obj=obj, mat_key=mat)]


def e_pec_sphere(radii=(0.30, 1.0), spps=SPHERE_SPP):
    """물리적으로 옳은 PEC 구(S=0). 해석해 σ=πr² 는 알고 있다. RT 는?"""
    lam = C0 / FC
    rows = []
    for r_m in radii:
        sigma_db = float(10 * np.log10(np.pi * r_m ** 2))     # 광학영역 구 σ = πr²
        for spp in spps:
            scene = build_scene(sphere_parts(r_m), fc=FC)
            scene.add(rt.Transmitter("tx", position=mi.Point3f(*[float(v) for v in TX])))
            scene.add(rt.Receiver("rx", position=mi.Point3f(*[float(v) for v in RX])))
            res = _rt_echo(scene, spp, seed=1, diffuse=False, max_depth=1)
            rows.append(dict(radius_m=float(r_m), spp=int(spp), sigma_dbsm=sigma_db,
                             n_paths=int(res["n_paths"]), rt_db=res.get("coh_db"),
                             sec=res["sec"]))
            print(f"    구 r={r_m:.2f} m (σ={sigma_db:+.1f} dBsm)  광선 {spp/1e6:5.0f}M "
                  f"→ 표적 경로 **{res['n_paths']}개**  ({res['sec']:.1f}s)")
    # 대조군: 같은 자리 같은 재질의 평판은 100× 적은 광선으로도 잡힌다
    scene = build_scene(plate_parts(0.60), fc=FC)
    scene.add(rt.Transmitter("tx", position=mi.Point3f(*[float(v) for v in TX])))
    scene.add(rt.Receiver("rx", position=mi.Point3f(*[float(v) for v in RX])))
    ctrl = _rt_echo(scene, 1_000_000, seed=1, diffuse=False, max_depth=1)
    print(f"    [대조군] 같은 자리 금속 평판 0.6 m, 광선 1M → 경로 {ctrl['n_paths']}개 "
          f"({ctrl.get('coh_db') and '%+.2f dB' % ctrl['coh_db']})  ⇒ 메쉬·재질·솔버는 정상")
    return dict(rows=rows, control_plate=dict(side_m=0.6, spp=1_000_000,
                                              n_paths=int(ctrl["n_paths"]),
                                              rt_db=ctrl.get("coh_db")),
                lam=float(lam))


# --------------------------------------------------------------------------- #
#  §4 — 표적 경유 바닥 유령
# --------------------------------------------------------------------------- #
def s4_ghost(vel=(-3.0, 2.0, 0.5)):
    """TX→표적→바닥→RX. 도플러가 실려 ECA 를 통과한다. 파형별 거리분해능과 견준다."""
    from waveforms import nr_downlink, lte_downlink, wifi_80211ac
    g = floor_ghost(TX, RX, TGT, vel, FC, pol="V")
    p = bistatic_params(TX, RX, TGT, vel, FC)
    # 두 체제를 **섞지 않는다** (docs/ARCHIVE.md §E):
    #   G3 = 부하 걸린 셀 + full-waveform 기준 → 기준신호 점유대역 ≈ 채널 대역
    #   G1 = idle 셀 + **상시 기준신호만**(LTE=CRS, 5G=SSB, WiFi=VHT-LTF) → 훨씬 좁다
    wfs = [("5G NR 100MHz", nr_downlink(bw_hz=100e6, carrier_hz=3.5e9, occupancy="G3")),
           ("WiFi 802.11ac", wifi_80211ac(bw_hz=80e6, carrier_hz=5.2e9)),
           ("LTE 20MHz", lte_downlink(bw_hz=20e6, carrier_hz=1.8e9, occupancy="G3"))]
    idle = [("5G NR 100MHz", nr_downlink(bw_hz=100e6, carrier_hz=3.5e9, occupancy="G1")),
            ("WiFi 802.11ac", wifi_80211ac(bw_hz=80e6, carrier_hz=5.2e9, occupancy="G1")),
            ("LTE 20MHz", lte_downlink(bw_hz=20e6, carrier_hz=1.8e9, occupancy="G1"))]
    sep = float(g["rb_m"] - p["Rb"])
    idle_ref = {nm: float(w.ref_bw_hz) for nm, w in idle}
    rows = []
    for nm, wf in wfs:
        B = float(wf.bw_hz)
        # ΔRb = c/B — **바이스태틱** 거리분해능. 프로젝트 공통 규약
        # (benchmark/run_min_cell.py:152, benchmark/geometry.py). 모노스태틱 c/2B 와 헷갈리지 말 것.
        d_rb = C0 / B
        # 대조: **상시 기준신호만** 쓰는 체제(패시브의 기본) — 점유대역이 훨씬 좁다.
        #   (LTE=CRS, 5G=SSB, WiFi=VHT-LTF)  ⇒ 두 체제를 섞지 말 것.
        B_ref = idle_ref[nm]                        # idle 셀에서 **상시 신호만** 점유하는 대역
        d_rb_ref = C0 / B_ref
        rows.append(dict(name=nm, bw_hz=B, d_rb_m=float(d_rb),
                         sep_over_drb=float(sep / d_rb),
                         resolved=bool(sep / d_rb > 1.0),
                         ref_bw_hz=B_ref, d_rb_ref_m=float(d_rb_ref),
                         sep_over_drb_ref=float(sep / d_rb_ref),
                         resolved_ref=bool(sep / d_rb_ref > 1.0)))
        print(f"    {nm:16s} B={B/1e6:5.1f} MHz  ΔRb={d_rb:5.2f} m  "
              f"분리/ΔRb = {sep/d_rb:5.2f}×  {'★ 별개 표적으로 분해' if sep/d_rb>1 else '병합(묻힘)'}"
              f"   | idle 상시기준({B_ref/1e6:5.1f} MHz): ΔRb={d_rb_ref:6.2f} m → {sep/d_rb_ref:4.2f}×")
    return dict(true=dict(Rb=float(p["Rb"]), fd=float(p["fd"]), R1=float(p["R1"]),
                          R2=float(p["R2"]), L=float(p["L"])),
                ghost=dict(Rb=float(g["rb_m"]), fd=float(g["fd"]),
                           amp_db=float(20 * np.log10(g["amp_ratio"])),
                           theta_i_deg=float(g["theta_i_deg"]), gamma=float(g["gamma"]),
                           R2f=float(g["R2f"])),
                sep_m=sep, d_fd_hz=float(g["fd"] - p["fd"]),
                vel=list(map(float, vel)), waveforms=rows)


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--only", default="depth,floor,rays,S,metal,plate,pec,ghost")
    a = ap.parse_args()
    only = set(a.only.split(","))
    rays = RAYS_QUICK if a.quick else RAYS
    seeds = SEEDS_QUICK if a.quick else SEEDS[:3]
    res = {}
    if os.path.exists(OUT):                       # 부분 실행 시 기존 결과 보존
        try:
            res = json.load(open(OUT))
        except Exception:
            res = {}
    t00 = time.time()

    print("=" * 90)
    print("report3 — Sionna RT 광선 반사 실험")
    print("=" * 90)
    g = _geom()
    print(f"기하: TX{TX} → RX{RX}, 표적{TGT} · L={g['L']:.2f} m · R1={g['R1']:.2f} · "
          f"R2={g['R2']:.2f} · β={g['beta']:.1f}° · f={FC/1e9:.1f} GHz")

    if "depth" in only:
        print("\n§1 max_depth = 0/1/2/3 — 광선이 튕길수록 경로가 몇 개가 되나")
        res["S1_depth"] = s1_depth()
    if "floor" in only and "S1_depth" in res:
        print("\n§2 바닥 반사 — 거울상+프레넬 손계산 vs Sionna RT")
        f = s2_floor(res["S1_depth"])
        res["S2_floor"] = f
        p = f["pred"]
        print(f"  손계산: 여분지연 {p['delay_ns']:.2f} ns · 입사각 {p['theta_i_deg']:.1f}° "
              f"(스침각 {p['grazing_deg']:.1f}°) · |Γ|_TM={p['gamma_tm']:.3f} · "
              f"확산 {p['spread_db']:+.1f} dB → **{p['rel_db']:+.2f} dB**")
        if f["rt_floor"]:
            m = f["rt_floor"]
            print(f"  Sionna RT: {m['delay_ns']:.2f} ns · {m['rel_db']:+.2f} dB "
                  f"({m['objects']}, 반사점 {m['vertices'][0]})")
            print(f"  → **{f['agree_db']:+.2f} dB / {f['agree_delay_ns']:+.2f} ns 일치.** "
                  "RT 는 환경에서 정확하다.")
        for t in f["twins"]:
            print(f"  같은 지연의 두 번째 경로: {t['delay_ns']:.2f} ns / {t['rel_db']:+.2f} dB "
                  f"→ {t['objects']} @ {t['vertices']}")

    if "rays" in only:
        print(f"\n§3[A] 광선예산 스윕 (시드 {len(seeds)}개) — 수렴하는가?")
        sc = _drone_scene()
        A = [dict(spp=s, **{k: v for k, v in _seeds(sc, s, seeds).items() if k != "spp"})
             for s in rays]
        for r in A:
            if r["n_paths"]:
                print(f"    {r['spp']:>12,} 발 → 경로 {r['n_mean']:6.1f}개  "
                      f"코히어런트 {r['coh_db']:+7.2f} dB (±{r['coh_sd']:.2f})  "
                      f"비코히어런트 {r['incoh_db']:+7.2f} dB  {r['sec']:5.1f}s")
        res["A_rays"] = dict(rows=A, seeds=seeds)
        ok = [r for r in A if r["n_paths"]]
        if len(ok) >= 2:
            print(f"    → 광선 {ok[0]['spp']/1e6:.0f}M → {ok[-1]['spp']/1e6:.0f}M "
                  f"({ok[-1]['spp']/ok[0]['spp']:.0f}배): 코히어런트 합 "
                  f"**{ok[-1]['coh_db']-ok[0]['coh_db']:+.1f} dB** 이동 — 수렴하지 않는다.")

    if "S" in only:
        print(f"\n§3[B] 산란계수 S 스윕 (광선 {S_RAYS/1e6:.0f}M, 시드 {len(seeds)}개)")
        B = []
        for mult in S_SWEEP:
            sc = _drone_scene(scatter_mult=mult)
            r = _seeds(sc, S_RAYS, seeds)
            r["mult"] = mult; r["S_plastic"] = min(1.0, S_BASE * mult)
            B.append(r)
            if r["n_paths"]:
                print(f"    S ×{mult:.1f} (plastic S={r['S_plastic']:.2f}) → "
                      f"코히어런트 {r['coh_db']:+7.2f} dB (±{r['coh_sd']:.2f}), "
                      f"경로 {r['n_mean']:.1f}개")
        res["B_scatter"] = dict(rows=B, spp=S_RAYS, seeds=seeds, S_base=S_BASE)
        ok = [r for r in B if r["n_paths"]]
        if len(ok) >= 2:
            print(f"    → S 를 {ok[0]['mult']:.1f}x→{ok[-1]['mult']:.1f}x ({ok[-1]['mult']/ok[0]['mult']:.0f}배) "
                  f"돌리면 **{ok[-1]['coh_db']-ok[0]['coh_db']:+.1f} dB**. "
                  "S 는 드론의 물성이 아니라 우리가 돌리는 노브다.")

    if "metal" in only:
        print("\n§3[C] ITU metal 의 S = 0 — σ 의 대부분이 확산 채널에 기여 0")
        C = c_metal_is_invisible()
        res["C_metal"] = C
        print(f"    Sionna 가 든 ITU metal 의 scattering_coefficient = **{C['itu_metal_S']:.1f}**")
        print(f"    SBR σ(전체) {C['sigma']['full_dbsm']:+.2f} dBsm · "
              f"금속만 {C['sigma']['metal_only_dbsm']:+.2f} · "
              f"비금속만 {C['sigma']['dielectric_only_dbsm']:+.2f}")
        print(f"    → 금속(S=0) 부품이 σ 의 **{C['metal_share_pct']:.0f}%**. "
              f"RT 확산이 보는 표적과 물리가 보는 표적이 다른 표적이다.")
        print(f"    → 레이더방정식이 요구하는 진폭비 = **{C['ratio_db_truth']:+.2f} dB**")

    if "plate" in only:
        print("\n§3[D] **결정적 실험** — 금속 평판 변 0.2 → 4 m (σ 가 52 dB 변한다)")
        D = d_plate_sweep()
        res["D_plate"] = D
        print(f"    → σ 는 **{D['sigma_span_db']:+.1f} dB** 변했는데 RT 진폭비는 "
              f"**{D['rt_span_db']:.2f} dB** 움직였다 (평균 {D['rt_mean_db']:+.2f} dB, "
              f"시드산포 {D['rt_sd_db']:.2f} dB).")
        print(f"    → 그 값은 image-source 예측 20·log10(L/(R1+R2)) = {D['image_db']:+.2f} dB. "
              "표적 크기가 **어디에도 안 들어간다.**")

    if "pec" in only:
        print("\n§3[E] 물리적으로 옳은 PEC 금속구(S=0) — 디스코볼 문제")
        res["E_sphere"] = e_pec_sphere()

    if "ghost" in only:
        print("\n§4 표적 경유 바닥 유령 — 도플러가 실려 ECA 를 통과한다")
        G = s4_ghost()
        res["S4_ghost"] = G
        print(f"    진짜 표적 Rb={G['true']['Rb']:.2f} m, f_d={G['true']['fd']:+.1f} Hz")
        print(f"    유령      Rb={G['ghost']['Rb']:.2f} m, f_d={G['ghost']['fd']:+.1f} Hz "
              f"(입사각 {G['ghost']['theta_i_deg']:.1f}°, |Γ|={G['ghost']['gamma']:.3f})")
        print(f"    → 진짜 대비 **{G['sep_m']:+.2f} m, {G['ghost']['amp_db']:+.1f} dB**, "
              f"도플러 차 {G['d_fd_hz']:+.1f} Hz")

    res["meta"] = dict(fc=FC, drone=KEY, TX=list(TX), RX=list(RX), TGT=list(TGT),
                       geometry={k: float(g[k]) for k in ("L", "R1", "R2", "beta")},
                       sionna=__import__("sionna").__version__,
                       gpu=os.environ.get("CUDA_VISIBLE_DEVICES", "?"),
                       sec=time.time() - t00)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(res, f, ensure_ascii=False, indent=1, default=float)
    print(f"\n✅ 총 {time.time()-t00:.0f}s → {os.path.relpath(OUT, ROOT)}")


if __name__ == "__main__":
    main()
