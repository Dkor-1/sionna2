# -*- coding: utf-8 -*-
"""적대적 재계산 — «자세마다 격자 재정의»를 부분으로 쪼갠다.

한 자세에 씬을 **한 번만** 짓고 여러 격자를 쏜다(추가 팔은 거의 공짜).

팔
  prod      자세마다 ctr=bbox중심 · Rout=3D반경·pad+3d      (생산 그대로)
  froz      ctr0 · Rout0 고정                                (원장의 얼린 팔)
  frozHalf  ctr0 + ½d(e1+e2) · Rout0                         ⭐«운 좋은 격자» 반증
  frozQrt   ctr0 + (0.37,−0.21)d · Rout0+1.5d (n 다름)       ⭐두번째 반증
  sizeOnly  ctr0 고정 · Rout 은 자세마다                      → n 튐(홀짝) 만의 몫
  ctrOnly   ctr = ctr0 + (c_i−ctr0)_가로 · Rout0 고정         → 가로 중심흔들림 만의 몫
  uOnly     ctr = ctr0 + ((c_i−ctr0)·û)û · Rout0 고정         → 위상원점 흔들림 만의 몫
"""
from __future__ import annotations
import argparse, json, os, sys, time
import numpy as np
_H = os.path.dirname(os.path.abspath(__file__)); _R = os.path.abspath(os.path.join(_H, ".."))
for _p in (os.path.join(_R, "src"), _H):
    if _p not in sys.path: sys.path.insert(0, _p)

OUTD = os.path.join(_R, "outputs", "archive", "adv_grid_freeze")
ARMS = ["prod", "froz", "frozHalf", "frozQrt", "sizeOnly", "ctrOnly", "uOnly"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--div", type=int, default=12)
    ap.add_argument("--nt", type=int, default=1024)
    ap.add_argument("--tag", default="run")
    a = ap.parse_args()
    os.environ.setdefault("SIONNA2_GPU", "2")
    from gpu import pick; pick(verbose=True)
    import mitsuba as mi
    import rcs_sbr as rsb
    from rcs_sbr import sbr_field
    from articulated_fast import FastPoser, rotor_phases
    from drones import DRONES, DRONE_GROUP_MAT
    GM = {g: m for g, (m, _) in DRONE_GROUP_MAT.items()}
    M = json.load(open(os.path.join(_R, "outputs", "report07_three_engines.json")))["_meta"]
    fp = FastPoser(DRONES[M["drone"]])
    NT = int(a.nt); PRF = float(M["prf_hz"]); FC = float(M["fc_hz"])
    ph = rotor_phases(np.arange(NT) / PRF, np.asarray(M["rpm_per_rotor"], float), fp.dirs)
    az, el = np.radians(M["az_deg"]), np.radians(M["el_deg"])
    u = np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])
    tmp = np.array([0., 0., 1.]) if abs(u[2]) < 0.9 else np.array([1., 0., 0.])
    e1 = np.cross(u, tmp); e1 /= np.linalg.norm(e1); e2 = np.cross(u, e1)
    lam = rsb.C0 / FC; d = lam / a.div; k = 2 * np.pi / lam; PAD = 1.15

    lo = np.full(3, np.inf); hi = np.full(3, -np.inf)
    for i in range(NT):
        V = fp.pose(ph[i]).v; lo = np.minimum(lo, V.min(0)); hi = np.maximum(hi, V.max(0))
    ctr0 = 0.5 * (lo + hi)
    Rmax = 0.0
    for i in range(NT):
        Rmax = max(Rmax, float(np.linalg.norm(fp.pose(ph[i]).v - ctr0, axis=1).max()))
    Rout0 = Rmax * PAD + 3 * d
    gnames = sorted(set(np.asarray(fp.g).tolist()))
    shells = rsb._resolve_shells(gnames, GM, None)

    def trace(scene, shptr, gam, mk, ctr, Rout):
        n = int(np.ceil(2 * Rout / d))
        t = (np.arange(n) - (n - 1) / 2.0) * d
        A, B = np.meshgrid(t, t, indexing="ij")
        O = (ctr + Rout * u)[None, :] + A.ravel()[:, None] * e1 + B.ravel()[:, None] * e2
        D = np.tile(-u, (O.shape[0], 1))
        ray = mi.Ray3f(o=mi.Point3f(*O.T.astype(np.float32)), d=mi.Vector3f(*D.T.astype(np.float32)))
        si = scene.ray_intersect(ray)
        valid = np.asarray(si.is_valid()).astype(bool)
        P = np.asarray(mi.Point3f(si.p)).T; Nn = np.asarray(mi.Vector3f(si.n)).T
        g = np.zeros(P.shape[0]); which = np.full(P.shape[0], -1, int)
        for _i, (sp, gm) in enumerate(zip(shptr, gam)):
            hit = np.asarray(si.shape == sp).astype(bool)
            g = np.where(hit, gm, g); which = np.where(hit, _i, which)
        sgn = np.sign(Nn @ u); sgn[sgn == 0] = 1.0
        cos_i = (Nn * sgn[:, None]) @ u
        lit = valid & (cos_i > 1e-6)
        if rsb.ANGLE_GAMMA and mk is not None:
            from materials import gamma_shape as _gsh
            for _i, _key in enumerate(mk):
                if _key is None: continue
                sel = (which == _i) & lit
                if sel.any(): g[sel] = g[sel] * _gsh(_key, FC, cos_i[sel])
        return lit, g, np.exp(1j * 2.0 * k * ((P - ctr) @ u)), si, n

    E = {arm: np.zeros(NT, complex) for arm in ARMS}
    NL = {arm: np.zeros(NT, int) for arm in ARMS}
    NG = {arm: np.zeros(NT, int) for arm in ARMS}
    t0 = time.time()
    for i in range(NT):
        mv = fp.pose(ph[i]); V = np.asarray(mv.v, float)
        c = 0.5 * (V.max(0) + V.min(0))
        Rp = float(np.linalg.norm(V - c, axis=1).max()) * PAD + 3 * d
        w = c - ctr0; w_perp = w - (w @ u) * u; w_u = (w @ u) * u
        grids = dict(prod=(c, Rp), froz=(ctr0, Rout0),
                     frozHalf=(ctr0 + 0.5 * d * (e1 + e2), Rout0),
                     frozQrt=(ctr0 + 0.37 * d * e1 - 0.21 * d * e2, Rout0 + 1.5 * d),
                     sizeOnly=(ctr0, Rp), ctrOnly=(ctr0 + w_perp, Rout0),
                     uOnly=(ctr0 + w_u, Rout0))
        sc, sh, gam, mk = rsb._scene_for(mv, GM, None, FC)
        shp = [mi.ShapePtr(s) for s in sh]
        sc_i, sh_i, gam_i, mk_i = rsb._scene_for(mv, GM, None, FC, exclude=shells)
        shp_i = [mi.ShapePtr(s) for s in sh_i]
        spos = [j for j, gn in enumerate(gnames) if gn in shells]
        for arm, (ctr, Rout) in grids.items():
            lit, g, phz, si, n = trace(sc, shp, gam, mk, ctr, Rout)
            val = np.sum(np.where(lit, g, 0.0) * phz); nl = int(lit.sum())
            tau = np.zeros(lit.shape[0])
            for j in spos:
                tau = np.where(np.asarray(si.shape == shp[j]).astype(bool), 1.0 - gam[j] ** 2, tau)
            lit2, g2, phz2, _, _ = trace(sc_i, shp_i, gam_i, mk_i, ctr, Rout)
            val = val + np.sum(np.where(lit2 & (tau > 0), tau * g2, 0.0) * phz2)
            nl += int((lit2 & (tau > 0)).sum())
            E[arm][i] = complex(val) * d * d; NL[arm][i] = nl; NG[arm][i] = n
        if i and i % 64 == 0:
            el = time.time() - t0
            print(f"  {i}/{NT} {el:.0f}s ETA {(NT-i)/i*el/60:.1f}min", flush=True)
    sec = time.time() - t0
    # 회귀 게이트 — prod 팔은 커널과 같아야 한다
    worst = 0.0
    for i in (0, 5, 37, min(101, NT - 1)):
        ek = sbr_field(fp.pose(ph[i]), GM, FC, u, spacing=d)
        worst = max(worst, abs(E["prod"][i] - ek) / (abs(ek) + 1e-300))
    print(f"[gate] prod vs rcs_sbr.sbr_field max rel err = {worst:.3e}  ({sec:.0f}s, {sec/NT*1e3:.0f} ms/pose)")
    os.makedirs(OUTD, exist_ok=True)
    p = os.path.join(OUTD, f"{a.tag}_div{a.div:03d}_nt{NT}.npz")
    np.savez_compressed(p, **{f"E_{k}": v for k, v in E.items()},
                        **{f"nlit_{k}": v for k, v in NL.items()},
                        **{f"ngrid_{k}": v for k, v in NG.items()},
                        div=np.array([a.div]), d=np.array([d]), nt=np.array([NT]),
                        ctr0=ctr0, Rout0=np.array([Rout0]), sec=np.array([sec]),
                        gate=np.array([worst]))
    print(f"→ {p}")


if __name__ == "__main__":
    main()
