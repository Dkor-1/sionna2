# -*- coding: utf-8 -*-
"""verify_po_elev_attack2.py — 기하 기준·예측을 독립 재계산하고, PO 투영면적 가중을 넣어
「−60/−75 에서 우리 폭이 기하 기준의 0.53/0.59 배」의 대안 설명을 시험한다.

⛔ 기존 원장 수정 금지. 산출물은 outputs/verify_po_elev_attack2.json.
⛔ GPU 미사용.
"""
from __future__ import annotations
import json, os, sys, time
import numpy as np

ROOT = "/home/yunjung/workspace/sionna2"
for p in (ROOT + "/src", ROOT + "/benchmark"):
    if p not in sys.path:
        sys.path.insert(0, p)

C0 = 299792458.0
FC = 3.5e9
LAM = C0 / FC
PRF = 19700.0
RANGE_M = 10.0
ELS = (0.0, -15.0, -30.0, -45.0, -60.0, -75.0, -90.0)
EK = [f"{e:+.0f}" for e in ELS]
F_FLASH = 126.66666666666667
F_TIP0 = 1272.91
QS = (0.75, 0.90, 0.95)
OUT = ROOT + "/outputs/verify_po_elev_attack2.json"
RPMS = np.array([3808.36, 3791.64, 3795.402, 3804.598])

from verify_po_elev_attack import wq, spec_ac, pear, spear   # 같은 독립 구현 재사용

import articulated_fast as AF
from drones import DRONES

t0 = time.time()
spec = DRONES["matrice4e"]
fp = AF.FastPoser(spec)
F = np.asarray(fp.f, int)
g = np.asarray(fp.g, dtype=object)
Fp = F[g == "prop"]
sel = np.unique(Fp.ravel())
remap = np.full(int(F.max()) + 1, -1, int)
remap[sel] = np.arange(sel.size)
Fp_l = remap[Fp]
k = 2 * np.pi / LAM
N = 4096
ph = AF.rotor_phases(np.arange(N) / PRF, RPMS, fp.dirs)


def los(az, el):
    a, e = np.radians(az), np.radians(el)
    return np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])


V0 = np.asarray(fp.pose(ph[0]).v, float)
cen = 0.5 * (V0.min(0) + V0.max(0))
TX = {e: cen + RANGE_M * los(0.0, e) for e in ELS}

J = {"_meta": dict(generator="benchmark/verify_po_elev_attack2.py",
                   date=time.strftime("%Y-%m-%d %H:%M:%S"),
                   gpu="사용 안 함", range_m=RANGE_M, n_poses=N)}

# ═══ 1. 기하 기준 신호 독립 재계산 ══════════════════════════════════
hp = {e: np.zeros(N, complex) for e in ELS}
CH = 256
for s in range(0, N, CH):
    ee = min(N, s + CH)
    Vs = np.stack([np.asarray(fp.pose(ph[i]).v, float) for i in range(s, ee)])[:, sel, :]
    for e in ELS:
        hp[e][s:ee] = np.exp(-2j * k * np.linalg.norm(Vs - TX[e], axis=2)).sum(1)
print("geom 신호", round(time.time() - t0, 1), "s", flush=True)

LED = json.load(open(ROOT + "/outputs/verify_po_elev_metric.json"))
G1 = {}
for e in ELS:
    m = wq(hp[e])
    G1[f"{e:+.0f}"] = dict(mine_W90=round(m["W90"], 1),
                           ledger_W90=round(LED["rows"]["geom_prop"][f"{e:+.0f}"]["W90"], 1))
J["geom_signal_reproduction"] = G1
print("1 geom W90 (내 계산 vs 원장):", {k2: (v["mine_W90"], v["ledger_W90"]) for k2, v in G1.items()})

# ═══ 2. 예측 히스토그램 — 균일 면적 vs PO 투영면적(|cos| 가중) ══════
STRIDE = 4
idx = np.arange(0, N - 1, STRIDE)
NB = 4000
EDG = np.linspace(0.0, 2000.0, NB + 1)
hist_u = {e: np.zeros(NB) for e in ELS}
hist_p = {e: np.zeros(NB) for e in ELS}
hist_pf = {e: np.zeros(NB) for e in ELS}      # 투영면적 × (앞면만)
dt = 1.0 / PRF
t1 = time.time()
for i in idx:
    Va = np.asarray(fp.pose(ph[int(i)]).v, float)
    Vb = np.asarray(fp.pose(ph[int(i) + 1]).v, float)
    ca = (Va[Fp[:, 0]] + Va[Fp[:, 1]] + Va[Fp[:, 2]]) / 3.0
    cb = (Vb[Fp[:, 0]] + Vb[Fp[:, 1]] + Vb[Fp[:, 2]]) / 3.0
    nrm = np.cross(Va[Fp[:, 1]] - Va[Fp[:, 0]], Va[Fp[:, 2]] - Va[Fp[:, 0]])
    ar = 0.5 * np.linalg.norm(nrm, axis=1)
    nh = nrm / np.maximum(np.linalg.norm(nrm, axis=1)[:, None], 1e-30)
    for e in ELS:
        da = np.linalg.norm(ca - TX[e], axis=1)
        db = np.linalg.norm(cb - TX[e], axis=1)
        fd = np.abs(2.0 * (db - da) / dt / LAM)
        u = (TX[e] - ca)
        u /= np.linalg.norm(u, axis=1)[:, None]
        ci = np.einsum("ij,ij->i", nh, u)
        hist_u[e] += np.histogram(fd, bins=EDG, weights=ar)[0]
        hist_p[e] += np.histogram(fd, bins=EDG, weights=ar * np.abs(ci))[0]
        hist_pf[e] += np.histogram(fd, bins=EDG, weights=ar * np.clip(ci, 0, None))[0]
print("2 예측 히스토그램", round(time.time() - t1, 1), "s", flush=True)


def hq(h, qs=QS):
    c = np.cumsum(h) / h.sum()
    o = {}
    for q in qs:
        o[f"W{int(q*100)}"] = float(EDG[1:][np.searchsorted(c, q)])
    nz = np.nonzero(h)[0]
    o["f_max"] = float(EDG[1:][nz[-1]]) if nz.size else 0.0
    return o


P2 = {}
for e in ELS:
    ku, kp, kf = hq(hist_u[e]), hq(hist_p[e]), hq(hist_pf[e])
    P2[f"{e:+.0f}"] = dict(
        uniform_area=dict(W90=round(ku["W90"], 1), f_max=round(ku["f_max"], 1)),
        projected_abs=dict(W90=round(kp["W90"], 1)),
        projected_front=dict(W90=round(kf["W90"], 1)),
        ledger_pred_W90=round(LED["prediction_geometric"][f"{e:+.0f}"]["W90"], 1),
        ledger_pred_fmax=round(LED["prediction_geometric"][f"{e:+.0f}"]["f_max"], 1),
        analytic_ff=round(F_TIP0 * float(np.cos(np.radians(e))), 1))
J["prediction_weightings"] = P2
print("2 예측 W90 균일 / |cos| / 앞면 / 원장:",
      {k2: (v["uniform_area"]["W90"], v["projected_abs"]["W90"],
            v["projected_front"]["W90"], v["ledger_pred_W90"]) for k2, v in P2.items()})

# ═══ 3. −90 근거리장 도플러 해석 검산 ═══════════════════════════════
P = V0[sel]
c2 = P[:, :2] - cen[:2]
q = np.sign(c2[:, 0]) * 2 + np.sign(c2[:, 1])
rows = []
for s in sorted(set(q.tolist())):
    m = q == s
    hub = P[m][:, :2].mean(0)
    a = float(np.linalg.norm(hub))
    r = float(np.linalg.norm(P[m][:, :2] - hub, axis=1).max())
    w = 2 * np.pi * float(RPMS.mean()) / 60.0
    rows.append(dict(hub_offset_m=round(a, 4), blade_R_m=round(r, 4),
                     f_dop_max_hz=round(2 * (a * r * w) / RANGE_M / LAM, 2)))
J["nearfield_minus90_analytic"] = dict(
    per_rotor=rows,
    max_hz=round(max(x["f_dop_max_hz"] for x in rows), 2),
    ledger_pred_fmax_hz=round(LED["prediction_geometric"]["-90"]["f_max"], 2),
    plane_wave_prediction_hz=0.0)
print("3 −90 해석 f_dop_max:", J["nearfield_minus90_analytic"]["max_hz"],
      "vs 원장", J["nearfield_minus90_analytic"]["ledger_pred_fmax_hz"])

# ═══ 4. 빗 양자화 — W90 이 f_flash 의 몇 배에 앉나 + 반쪽 재현성 ════
d = np.load(ROOT + "/outputs/elevation_sweep_md.npz")
Q4 = {}
for e in ELS:
    x = d[f"ours/el{e:+.0f}"]
    w_all = wq(x)["W90"]
    w_h1 = wq(x[:2048])["W90"]
    w_h2 = wq(x[2048:])["W90"]
    w_q = [wq(x[i * 1024:(i + 1) * 1024])["W90"] for i in range(4)]
    gv = LED["rows"]["geom_prop"][f"{e:+.0f}"]["W90"]
    Q4[f"{e:+.0f}"] = dict(
        ours_W90=round(w_all, 1), ours_in_flash_units=round(w_all / F_FLASH, 2),
        geom_W90=round(gv, 1), geom_in_flash_units=round(gv / F_FLASH, 2),
        ratio=round(w_all / gv, 2),
        half_split=[round(w_h1, 1), round(w_h2, 1)],
        quarter_split=[round(v, 1) for v in w_q],
        quarter_spread=round(max(w_q) / max(min(w_q), 1e-9), 2),
        ratio_if_one_comb_step=[round((w_all - F_FLASH) / gv, 2),
                                round((w_all + F_FLASH) / gv, 2)])
J["comb_quantisation_and_stability"] = Q4
print("4 flash 단위 (ours, geom):",
      {k2: (v["ours_in_flash_units"], v["geom_in_flash_units"]) for k2, v in Q4.items()})
print("4 사분할 산포:", {k2: v["quarter_spread"] for k2, v in Q4.items()})

# ═══ 5. 우리 신호에서 빗선 에너지를 빼면 폭이 어디로 가나 ═══════════
def comb_notch(x, nmax=40, hw_hz=25.0):
    """n·f_flash 선을 좁게 도려낸 뒤(=플래시 AM 제거) 남은 연속체."""
    xa = np.asarray(x, complex) - np.mean(x)
    n = len(xa)
    Z = np.fft.fft(xa)
    f = np.fft.fftfreq(n, 1.0 / PRF)
    m = np.zeros(n, bool)
    for j in range(1, nmax + 1):
        m |= np.abs(np.abs(f) - j * F_FLASH) < hw_hz
    Zn = Z.copy(); Zn[m] = 0.0
    Zc = Z.copy(); Zc[~m] = 0.0
    return (np.fft.ifft(Zn), np.fft.ifft(Zc),
            float((np.abs(Z[m]) ** 2).sum() / max((np.abs(Z) ** 2).sum(), 1e-300)))


Q5 = {}
for e in ELS:
    x = d[f"ours/el{e:+.0f}"]
    xn, xc, frac = comb_notch(x)
    gx = hp[e]
    gn, gc, gfrac = comb_notch(gx)
    Q5[f"{e:+.0f}"] = dict(
        ours_comb_energy_frac=round(frac, 3),
        ours_W90_all=round(wq(x)["W90"], 1),
        ours_W90_comb_only=round(wq(xc)["W90"], 1),
        ours_W90_continuum=round(wq(xn)["W90"], 1),
        geom_comb_energy_frac=round(gfrac, 3),
        geom_W90_comb_only=round(wq(gc)["W90"], 1))
J["comb_vs_continuum"] = Q5
print("5 빗선 에너지 몫 (ours, geom):",
      {k2: (v["ours_comb_energy_frac"], v["geom_comb_energy_frac"]) for k2, v in Q5.items()})

with open(OUT, "w") as fh:
    json.dump(J, fh, ensure_ascii=False, indent=1)
print("\nOK", OUT, round(time.time() - t0, 1), "s")
