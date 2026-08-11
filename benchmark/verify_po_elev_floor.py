# -*- coding: utf-8 -*-
"""verify_po_elev_floor.py — ⭐**물리 상한으로 우리 커널의 수치 바닥을 잰다** (GPU 안 씀).

■ 시험 ① — |f| > f_tip 의 전력은 있을 수 없다
드론에서 가장 빠른 산란점은 블레이드 팁이다. 단일 반사(sbr_field 는 first-hit 뿐)라면
슬로타임 스펙트럼은 **|f| ≤ f_tip 밖으로 나갈 수 없다.** 그 밖의 전력은 전부
이산화·표본화의 산물이다 ⇒ 그게 곧 **AC 채널의 수치 바닥**이다.
(윈도 누설 여유 15 % 를 준다. 다중반사는 없으므로 2× 도플러 경로도 없다.)

■ 시험 ② — 동체 면법선을 앙각으로 투영
«밑에서 볼수록 동체 배면이 정면을 향한다» 가 맞나. 정반사(법선이 시선 10° 안) 면적과
코히어런트 상쇄량(비코히어런트 상한 − 코히어런트 합)을 앙각으로 훑는다.
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np                                                      # noqa: E402
from articulated_fast import FastPoser                                  # noqa: E402
from drones import DRONES, DRONE_GROUP_MAT                              # noqa: E402
from materials import gamma_po, gamma_shape                             # noqa: E402

FC = 3.5e9
LAM = 2.998e8 / FC
K = 2 * np.pi / LAM
OUT = f"{ROOT}/outputs/verify_po_elev_floor.json"
M = json.load(open(f"{ROOT}/outputs/elevation_sweep_md.json"))
TJ = json.load(open(f"{ROOT}/outputs/report07_three_engines.json"))["_meta"]
ELS = [0, -15, -30, -45, -60, -75, -90]

# ═══ ① 물리 상한 바닥 ════════════════════════════════════════════════════════
Z = np.load(f"{ROOT}/outputs/elevation_sweep_md.npz")
prf = float(M["_meta"]["prf_hz"])
ftip = {int(r["el_deg"]): r["f_tip_hz"] for r in M["rows"] if r["engine"] == "ours"}
band = []
for el in ELS:
    E = Z[f"ours/el{el:+d}"]
    n = E.size
    A = E - E.mean()
    w = np.hanning(n)
    w /= np.sqrt(np.mean(w ** 2))
    S = np.fft.fftshift(np.abs(np.fft.fft(A * w)) ** 2) / n ** 2
    f = np.fft.fftshift(np.fft.fftfreq(n, 1 / prf))
    ft = max(ftip[el], 1e-9)
    inb = np.abs(f) <= 1.15 * ft
    Pin, Pout = float(S[inb].sum()), float(S[~inb].sum())
    hi = np.abs(f) > 4000.0
    band.append(dict(
        el_deg=el, f_tip_hz=round(ft, 1),
        P_ac_db=round(10 * np.log10(Pin + Pout), 2),
        P_in_band_db=round(10 * np.log10(Pin + 1e-300), 2),
        P_out_of_band_db=round(10 * np.log10(Pout + 1e-300), 2),
        out_of_band_frac_pct=round(100 * Pout / (Pin + Pout), 2),
        white_floor_db=round(10 * np.log10(float(S[hi].sum()) + 1e-300), 2)))
floor_db = float(np.median([b["white_floor_db"] for b in band]))
for b in band:
    b["snr_over_floor_db"] = round(b["P_ac_db"] - floor_db, 2)

# ═══ ② 동체 면법선 투영 ══════════════════════════════════════════════════════
spec = DRONES[TJ.get("drone", "matrice4e")]
fp = FastPoser(spec)
az = float(TJ.get("az_deg", 0.0))
GAM = {g: gamma_po(m, FC) for g, (m, _) in DRONE_GROUP_MAT.items()}
MK = {g: m for g, (m, _) in DRONE_GROUP_MAT.items()}
G = np.asarray(fp.g)
BODY = G != "prop"
mv = fp.pose([0.0, 0.0, 0.0, 0.0])
V = mv.v
T = V[mv.f]
nr = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
Ar = 0.5 * np.linalg.norm(nr, axis=1)
nh = nr / (2 * Ar[:, None] + 1e-300)
cen = T.mean(1) - 0.5 * (V.max(0) + V.min(0))


def los(el):
    a, e = np.radians(az), np.radians(el)
    return np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])


geo = []
for el in np.arange(-90.0, 0.001, 1.0):
    u = los(el)
    cs = nh @ u
    lit = (cs > 1e-6) & BODY
    Ap = float(np.sum(Ar[lit] * cs[lit]))
    s10 = lit & (cs > np.cos(np.radians(10.0)))
    amp = np.zeros(Ar.size)
    for g in set(G[lit].tolist()):
        s = lit & (G == g)
        amp[s] = Ar[s] * cs[s] * GAM[g] * np.asarray(gamma_shape(MK[g], FC, cs[s]))
    ph = np.zeros(Ar.size, complex)
    ph[lit] = np.exp(1j * 2 * K * (cen[lit] @ u))
    coh = 20 * np.log10(abs(complex(np.sum(amp * ph))) + 1e-300)
    inc = 20 * np.log10(float(np.sum(np.abs(amp))) + 1e-300)
    geo.append(dict(el_deg=round(float(el), 1),
                    A_proj_cm2=round(1e4 * Ap, 1),
                    A_spec10_cm2=round(1e4 * float(np.sum(Ar[s10] * cs[s10])), 3),
                    spec_frac_pct=round(1e2 * float(np.sum(Ar[s10] * cs[s10])) / max(Ap, 1e-12), 4),
                    E_coh_db=round(coh, 2), E_incoh_db=round(inc, 2),
                    coh_loss_db=round(inc - coh, 2)))

json.dump({"_meta": {
    "generator": "benchmark/verify_po_elev_floor.py",
    "fc_hz": FC, "drone": TJ.get("drone"), "az_deg": az,
    "test1_ko": "|f| > 1.15·f_tip 의 슬로타임 전력은 물리적으로 불가능하다(팁보다 빠른 "
                "산란체가 없고 sbr_field 는 단일 반사라 2× 도플러 경로도 없다) ⇒ 수치 바닥",
    "test2_ko": "동체 면법선을 앙각으로 투영 — 정반사(10°) 면적과 코히어런트 상쇄량",
    "geo_note_ko": "②는 광선을 안 쏜다(면적분만) — 가림·투과 없음. 널의 «위치» 를 광선격자와 "
                   "무관하게 확인하는 독립 경로다.",
    "numerical_floor_db": round(floor_db, 2)},
    "band_limit_test": band, "body_normals": geo},
    open(OUT, "w"), ensure_ascii=False, indent=1)

print(f"수치 바닥(중앙값) {floor_db:.1f} dB\n")
print(f"{'el':>5} {'f_tip':>7} {'P_ac':>8} {'대역내':>8} {'대역밖':>8} {'초과%':>7} {'바닥대비':>8}")
for b in band:
    print(f"{b['el_deg']:>5} {b['f_tip_hz']:>7.0f} {b['P_ac_db']:>8.1f} "
          f"{b['P_in_band_db']:>8.1f} {b['P_out_of_band_db']:>8.1f} "
          f"{b['out_of_band_frac_pct']:>7.2f} {b['snr_over_floor_db']:>+8.1f}")
print(f"\n{'el':>5} {'투영[cm²]':>10} {'정반사10°[cm²]':>14} {'몫%':>8} {'상쇄[dB]':>9}")
for t in ELS:
    r = geo[int(np.argmin(np.abs(np.array([g['el_deg'] for g in geo]) - t)))]
    print(f"{t:>5} {r['A_proj_cm2']:>10.1f} {r['A_spec10_cm2']:>14.2f} "
          f"{r['spec_frac_pct']:>8.3f} {r['coh_loss_db']:>9.1f}")
print(f"\n✅ {OUT}")
