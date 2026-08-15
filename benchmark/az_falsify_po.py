# -*- coding: utf-8 -*-
"""az_falsify_po.py — 제3의 심판: **평면파 물리광학(PO) 적분**을 직접 짜서
방위 0°↔45° 의 «가만히 있는 부분» 이 물리적으로 얼마나 줄어야 하는지 계산한다.
두 엔진 어느 쪽 코드도 쓰지 않는다(numpy 만). GPU 안 씀."""
import json, sys
import numpy as np

ROOT = "/workspace/sionna"
sys.path.insert(0, f"{ROOT}/src")
from drones import DRONES                                       # noqa: E402
from articulated_fast import FastPoser, rotor_phases            # noqa: E402

FC = 3.5e9; C = 2.998e8; LAM = C / FC; K = 2 * np.pi / LAM
spec = DRONES["matrice4e"]; fp = FastPoser(spec)
ph = rotor_phases(np.array([0.0]), np.array([3808.36, 3791.64, 3795.402, 3804.598]), fp.dirs)
mv = fp.pose(ph[0])
V, F, G = mv.v, mv.f, np.asarray(mv.g)

# ── 삼각형을 무게중심으로 잘게 쪼갠다(위상 변화를 제대로 적분하려고) ─────
NSUB = 6                                     # 한 변을 6 등분 → 삼각형 36 조각
bary = []
for i in range(NSUB):
    for j in range(NSUB - i):
        # 정삼각격자 — 위쪽 삼각형
        bary.append(((i + 1 / 3) / NSUB, (j + 1 / 3) / NSUB))
        if i + j < NSUB - 1:
            bary.append(((i + 2 / 3) / NSUB, (j + 2 / 3) / NSUB))
bary = np.array(bary)                        # (NS,2) — 합 = NSUB²
NS = bary.shape[0]
assert NS == NSUB * NSUB, (NS, NSUB * NSUB)

a = V[F[:, 0]]; b = V[F[:, 1]]; c = V[F[:, 2]]
cr = np.cross(b - a, c - a); A = 0.5 * np.linalg.norm(cr, axis=1)
good = A > 1e-12
a, b, c, cr, A, Gf = a[good], b[good], c[good], cr[good], A[good], G[good]
n_hat = cr / (2 * A)[:, None]
# 조각 중심 좌표 (NF, NS, 3)
u1 = (b - a); u2 = (c - a)
P = a[:, None, :] + bary[None, :, 0, None] * u1[:, None, :] + bary[None, :, 1, None] * u2[:, None, :]
Asub = (A / NS)[:, None] * np.ones((1, NS))


def los(az, el):
    az, el = np.radians(az), np.radians(el)
    return np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])


def po_field(u, mask=None):
    """단상태 스칼라 PO: E ∝ Σ (n̂·û)·dA·exp(-j2k û·r).  가림은 «앞을 보는 면만» 으로 근사."""
    m = (n_hat @ u) > 0.0
    if mask is not None:
        m &= mask
    if not m.any():
        return 0.0 + 0j
    w = (n_hat[m] @ u)[:, None] * Asub[m]
    phase = np.exp(-2j * K * (P[m] @ u))
    return complex(np.sum(w * phase))


NONPROP = ~np.isin(Gf, ["prop"])
out = {"_meta": {
    "generator": "benchmark/az_falsify_po.py",
    "gpu_ko": "⛔GPU 안 씀. 두 엔진 코드도 안 씀 — numpy 로 짠 평면파 PO 적분이다.",
    "recipe_ko": "삼각형마다 36 조각으로 나눠 E = Σ(n̂·û)·dA·exp(-j2k û·r). "
                 "가림은 '앞면만' 으로 근사(그림자 무시) — 절대값이 아니라 **방위 비율** 을 보려는 계산이다.",
    "fc_hz": FC, "lambda_m": round(LAM, 5), "nsub_per_triangle": NS,
    "n_faces_used": int(A.size),
    "caveat_ko": "그림자를 무시하므로 절대 σ 는 못 믿는다. 같은 앙각에서 방위만 바꾼 비율은 믿을 만하다.",
}}

sweeps = {}
for el in (0.0, -30.0, -60.0, -90.0):
    rows = []
    for az in np.arange(0, 90.5, 1.0):
        u = los(az, el)
        e_all = po_field(u)
        e_np = po_field(u, NONPROP)
        rows.append(dict(az=float(az),
                         all_db=round(20 * np.log10(abs(e_all) + 1e-300), 2),
                         nonprop_db=round(20 * np.log10(abs(e_np) + 1e-300), 2)))
    sweeps[f"el{el:+.0f}"] = rows
out["po_azimuth_sweep_db"] = sweeps

cmp = {}
LEDG = {  # 관측된 «가만히 있는 부분» 변화 [dB] (outputs/az_falsify_comb.json)
    "el+0": dict(ps_nophys=-57.07, ps_phys=-38.51, ours=-1.64),
    "el-30": dict(ps_nophys=0.60, ps_phys=-52.51, ours=-0.74),
    "el-60": dict(ps_nophys=2.78, ps_phys=-26.50, ours=18.05),
    "el-90": dict(ps_nophys=0.00, ps_phys=-0.01, ours=0.00),
}
for el, rows in sweeps.items():
    r = {x["az"]: x for x in rows}
    d_all = round(r[45.0]["all_db"] - r[0.0]["all_db"], 2)
    d_np = round(r[45.0]["nonprop_db"] - r[0.0]["nonprop_db"], 2)
    band = [x["all_db"] for x in rows]
    cmp[el] = dict(po_d_az45_minus_az0_db=d_all, po_nonprop_d_db=d_np,
                   po_az_spread_db=round(max(band) - min(band), 2),
                   po_az0_db=r[0.0]["all_db"], po_az45_db=r[45.0]["all_db"],
                   observed_d_dc_db=LEDG[el])
out["po_vs_observed"] = cmp

json.dump(out, open(f"{ROOT}/outputs/az_falsify_po.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(cmp, ensure_ascii=False, indent=1))
print("el+0 PO(az):", [(r["az"], r["all_db"]) for r in sweeps["el+0"]][::5])
print("el-60 PO(az):", [(r["az"], r["all_db"]) for r in sweeps["el-60"]][::5])
