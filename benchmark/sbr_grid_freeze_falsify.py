# -*- coding: utf-8 -*-
"""sbr_grid_freeze_falsify.py — ⭐«얼린 팔이 그냥 신호를 깎은 것 아니냐» 를 깨러 간다.

`outputs/sbr_grid_convergence.json` 의 결론은 이렇다:

  대역밖 바닥의 지배 원인은 이산화가 아니라 **자세마다 격자를 다시 정의하는 것**이다.
  격자를 얼리면 9.3 dB 내려가고 d² 로 수렴한다.

이 스크립트는 그 결론을 **반증하려고** 만들어졌다. 반증 시나리오는 셋이다.

  (F1) «운 좋은 한 판»  — 얼린 격자가 우연히 좋은 서브셀 오프셋을 뽑았을 뿐이다.
       → `froz_half` : 같은 격자를 **반 칸 옆으로** 통째로 밀어 얼린다. 오프셋만 다른
         또 한 판이다. 바닥이 다시 올라가면 «운» 이 맞다.
  (F2) «얼리기가 신호를 깎았다» — 얼린 팔이 표적 일부를 놓쳤거나 변조를 지웠다.
       → 히트 수·대역내 파형을 독립 엔진(순수 PO)과 대조한다.
  (F3) «격자 재정의는 원인이 아니다» — 상관일 뿐 인과가 아니다.
       → ⭐**역방향 실험**: 얼린 격자에 **일부러 흔들림을 되먹인다**.
         · `dith`     자세마다 무작위 서브셀 오프셋(가로 ⊥ û — 위상 원점은 그대로다)
         · `replay`   생산이 실제로 겪은 ctr 의 **가로 성분만** 그대로 재생
         · `nflip`    격자 칸 수 n 만 자세마다 ±1 토글(= 격자가 통째로 d/2 밀린다)
         셋 중 하나라도 바닥을 생산 수준으로 되돌리면 **인과가 확인된다**.
         아무것도 안 올라가면 결론이 깨진다.

⚠ 원장은 새 이름으로만 쓴다: outputs/sbr_grid_freeze_falsify.json / .npz
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import socket
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (os.path.join(_ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np                                                      # noqa: E402

SRC = os.path.join(_ROOT, "outputs", "report07_three_engines.json")
PARTS = os.path.join(_ROOT, "outputs", "archive", "sbr_grid_conv_parts")
OUTJ = os.path.join(_ROOT, "outputs", "sbr_grid_freeze_falsify.json")
OUTZ = os.path.join(_ROOT, "outputs", "sbr_grid_freeze_falsify.npz")
PAD = 1.15


def look(az_deg, el_deg):
    a, e = np.radians(az_deg), np.radians(el_deg)
    return np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])


def _trace(rsb, mi, scene, shptr, gam, matk, ctr, n, d, u, e1, e2, Rout, fc, k):
    """`_field_grid` 의 광선/합산부와 **같은 식**. n 을 호출자가 준다(정수 튐을 통제하려고)."""
    t = (np.arange(n) - (n - 1) / 2.0) * d
    A, B = np.meshgrid(t, t, indexing="ij")
    O = (ctr + Rout * u)[None, :] + A.ravel()[:, None] * e1 + B.ravel()[:, None] * e2
    D = np.tile(-u, (O.shape[0], 1))
    ray = mi.Ray3f(o=mi.Point3f(*O.T.astype(np.float32)),
                   d=mi.Vector3f(*D.T.astype(np.float32)))
    si = scene.ray_intersect(ray)
    valid = np.asarray(si.is_valid()).astype(bool)
    P = np.asarray(mi.Point3f(si.p)).T
    Nn = np.asarray(mi.Vector3f(si.n)).T
    g = np.zeros(P.shape[0]); which = np.full(P.shape[0], -1, int)
    for _i, (sp, gm) in enumerate(zip(shptr, gam)):
        hit = np.asarray(si.shape == sp).astype(bool)
        g = np.where(hit, gm, g); which = np.where(hit, _i, which)
    sgn = np.sign(Nn @ u); sgn[sgn == 0] = 1.0
    Nn = Nn * sgn[:, None]
    cos_i = Nn @ u
    lit = valid & (cos_i > 1e-6)
    if rsb.ANGLE_GAMMA and matk is not None:
        from materials import gamma_shape as _gsh
        for _i, _key in enumerate(matk):
            if _key is None:
                continue
            sel = (which == _i) & lit
            if sel.any():
                g[sel] = g[sel] * _gsh(_key, fc, cos_i[sel])
    ph = np.exp(1j * 2.0 * k * ((P - ctr) @ u))
    return valid, lit, g, ph, si


def run(div=12, nt=2048, seed=0):
    os.environ.setdefault("SIONNA2_GPU", "2")
    from gpu import pick
    pick(verbose=True)
    import mitsuba as mi
    import rcs_sbr as rsb
    from articulated_fast import FastPoser, rotor_phases
    from drones import DRONES, DRONE_GROUP_MAT

    GM = {g: m for g, (m, _) in DRONE_GROUP_MAT.items()}
    M = json.load(open(SRC))["_meta"]
    fp = FastPoser(DRONES[M["drone"]])
    rpms = np.asarray(M["rpm_per_rotor"], float)
    PRF = float(M["prf_hz"]); FC = float(M["fc_hz"])
    u = look(M["az_deg"], M["el_deg"])
    lam = rsb.C0 / FC; k = 2 * np.pi / lam; d = lam / div
    tt = np.arange(nt) / PRF
    ph = rotor_phases(tt, rpms, fp.dirs)
    group_names = sorted(set(np.asarray(fp.g).tolist()))
    shells = rsb._resolve_shells(group_names, GM, None)
    tmp = np.array([0.0, 0.0, 1.0]) if abs(u[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    e1 = np.cross(u, tmp); e1 /= np.linalg.norm(e1)
    e2 = np.cross(u, e1)

    # ── 얼린 격자: ⭐원 실험이 쓴 ctr₀·Rout₀ 를 **그대로 상속**한다.
    #    (원 실험은 4096 자세 전체의 bbox 로 잡았다. 상속해야 `froz` 팔이 원장의 E_froz 와
    #     비트 단위로 같아지고 — 그것이 이 스크립트의 회귀 게이트다.)
    pp = os.path.join(PARTS, f"div{div:03d}.npz")
    if os.path.exists(pp):
        zz = np.load(pp)
        ctr0 = np.asarray(zz["ctr0"], float); Rout0 = float(zz["Rout0"][0])
        print(f"[falsify] 얼린 격자 상속 ← {pp}")
    else:
        lo = np.full(3, np.inf); hi = np.full(3, -np.inf)
        for i in range(nt):
            V = fp.pose(ph[i]).v
            lo = np.minimum(lo, V.min(0)); hi = np.maximum(hi, V.max(0))
        ctr0 = 0.5 * (lo + hi)
        Rmax = max(float(np.linalg.norm(fp.pose(ph[i]).v - ctr0, axis=1).max())
                   for i in range(nt))
        Rout0 = Rmax * PAD + 3 * d
    n0 = int(np.ceil(2 * Rout0 / d))
    print(f"[falsify] div {div} d={d*1e3:.3f}mm n0={n0} nt={nt}", flush=True)

    rng = np.random.default_rng(seed)
    r1 = rng.random(nt); r2 = rng.random(nt)                 # 무작위 서브셀 오프셋
    ARMS = ("froz", "froz_half", "dith", "replay", "nflip")
    E = {a: np.zeros(nt, complex) for a in ARMS}
    NL = {a: np.zeros(nt, int) for a in ARMS}
    ctr_prod = np.zeros((nt, 3))

    t0 = time.time()
    for i in range(nt):
        mv = fp.pose(ph[i])
        V = np.asarray(mv.v, float)
        cp = 0.5 * (V.max(0) + V.min(0))
        ctr_prod[i] = cp
        dc = cp - ctr0
        # 생산 격자가 실제로 겪는 가로 이동만 (⊥ û — 위상 원점은 건드리지 않는다)
        dperp = (dc @ e1) * e1 + (dc @ e2) * e2

        scene, shapes, gammas, matk = rsb._scene_for(mv, GM, None, FC)
        shptr = [mi.ShapePtr(s) for s in shapes]
        shell_pos = [j for j, gn in enumerate(group_names) if gn in shells]
        do_pen = len(shell_pos) > 0
        if do_pen:
            sc_i, sh_i, gm_i, mk_i = rsb._scene_for(mv, GM, None, FC, exclude=shells)
            shp_i = [mi.ShapePtr(s) for s in sh_i]

        variants = dict(
            froz=(ctr0, n0),
            froz_half=(ctr0 + 0.5 * d * e1, n0),
            dith=(ctr0 + r1[i] * d * e1 + r2[i] * d * e2, n0),
            replay=(ctr0 + dperp, n0),
            nflip=(ctr0, n0 + (i % 2)),
        )
        for a, (c, n) in variants.items():
            valid, lit, g, phs, si = _trace(rsb, mi, scene, shptr, gammas, matk,
                                            c, n, d, u, e1, e2, Rout0, FC, k)
            acc = np.sum(np.where(lit, g, 0.0) * phs)
            nl = int(lit.sum())
            if do_pen:
                tau = np.zeros(valid.shape[0])
                for j in shell_pos:
                    tau = np.where(np.asarray(si.shape == shptr[j]).astype(bool),
                                   1.0 - gammas[j] ** 2, tau)
                _, lit2, g2, ph2, _ = _trace(rsb, mi, sc_i, shp_i, gm_i, mk_i,
                                             c, n, d, u, e1, e2, Rout0, FC, k)
                acc = acc + np.sum(np.where(lit2 & (tau > 0), tau * g2, 0.0) * ph2)
                nl += int((lit2 & (tau > 0)).sum())
            E[a][i] = acc * d * d
            NL[a][i] = nl
        if i and i % 256 == 0:
            el = time.time() - t0
            print(f"    {i}/{nt}  {el:.0f}s  ETA {(nt-i)/i*el/60:.1f}분", flush=True)
    print(f"[falsify] ✅ {time.time()-t0:.0f}s", flush=True)

    np.savez_compressed(OUTZ, ctr0=ctr0, Rout0=np.array([Rout0]), n0=np.array([n0]),
                        d=np.array([d]), div=np.array([div]), nt=np.array([nt]),
                        r1=r1, r2=r2, ctr_prod=ctr_prod,
                        **{f"E_{a}": E[a] for a in ARMS},
                        **{f"nlit_{a}": NL[a] for a in ARMS})
    print(f"→ {OUTZ}")
    return E, NL


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--div", type=int, default=12)
    ap.add_argument("--nt", type=int, default=2048)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    run(a.div, a.nt, a.seed)
