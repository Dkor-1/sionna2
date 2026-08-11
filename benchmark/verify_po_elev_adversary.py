# -*- coding: utf-8 -*-
"""
verify_po_elev_adversary.py — ⭐앞선 «기하 위상 기준» 판정을 **반증하러** 간다.

앞 판정의 주장은 셋이었다.
  G1  기하 기준이 Carson 상한을 지킨다 → 자(ruler)가 옳다
  G3  물리대역 안에서 우리 커널이 기하 기준과 «일치» 한다 (edge20 비 0.84~1.00, 빗 코사인 0.71~1.00)
  G4~G6  Carson 밖 초과 에너지는 격자 표본화 잡음이다 (∝ d^1.03)

⛔이 판은 **G3 에 음성대조(negative control)가 없다**는 데서 출발한다. 「우리 것이 기준과
맞는다」는 잣대가 **틀린 기준과는 안 맞는다**는 것을 보여야 증거가 된다. 안 보였다.
그래서 여기서는 일부러 **틀린 기준**을 여럿 만들어 같은 잣대에 건다:

  D1  이웃 앙각의 기하 기준        (공짜 — 이미 계산된 것)
  D2  시간축 워프 α = 0.6/0.75/0.9/1.1/1.25/1.4  → **회전수가 α 배 틀린** 기준
  D3  날개 반경 β = 0.6/0.75/0.9/1.25 배         → **f_tip 만** 틀리고 f_flash 는 맞는 기준
  D4  Carson 안 대역제한 백색잡음                → 도플러 «내용» 이 아예 없는 기준

D1~D4 가 정답 기준과 **같은 점수**를 받으면 G3 은 증거가 아니라 통과 의례다.

그리고 초과대역(G4)을 세 가지 독립 방법으로 다시 잰다 — 창 3종(BH4/Hann/Nuttall) ·
창 없는 주기도 · 시간영역 이상적 대역차단 에너지. 방법에 따라 답이 흔들리면 그 수치도 못 쓴다.

⛔GPU 안 씀. 기존 원장 안 건드림. 새 산출물 하나: outputs/verify_po_elev_adversary.json
"""
from __future__ import annotations

import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

C0 = 299792458.0
FC = 3.5e9
LAM = C0 / FC
K = 2.0 * np.pi / LAM
RANGE_M = 10.0
ELS = (0.0, -15.0, -30.0, -45.0, -60.0, -75.0, -90.0)
OUT = os.path.join(ROOT, "outputs", "verify_po_elev_adversary.json")
NPZ_IN = os.path.join(ROOT, "outputs", "elevation_sweep_md.npz")
TJ = json.load(open(os.path.join(ROOT, "outputs", "report07_three_engines.json")))["_meta"]


# ═══ 잣대 (앞 판정과 **같은 정의** — 사과 대 사과) ═══════════════════════════
def win(n, kind):
    x = 2 * np.pi * np.arange(n) / n
    if kind == "bh4":
        a = (0.35875, 0.48829, 0.14128, 0.01168)
    elif kind == "nuttall":
        a = (0.3635819, 0.4891775, 0.1365995, 0.0106411)
    elif kind == "hann":
        return np.hanning(n)
    elif kind == "rect":
        return np.ones(n)
    else:
        raise ValueError(kind)
    return a[0] - a[1] * np.cos(x) + a[2] * np.cos(2 * x) - a[3] * np.cos(3 * x)


def spectrum(z, prf, kind="bh4", pad=4):
    n = len(z)
    w = win(n, kind)
    Z = np.fft.fftshift(np.fft.fft(z * w, n=pad * n)) / w.sum()
    f = np.fft.fftshift(np.fft.fftfreq(pad * n, 1.0 / prf))
    return f, np.abs(Z)


def inband_edge20(f, A, guard, f_hi):
    m = (np.abs(f) > guard) & (np.abs(f) <= f_hi)
    if not m.any() or A[m].max() <= 0:
        return None
    pk = A[m].max()
    sel = m & (A >= pk * 0.1)
    return float(np.abs(f[sel]).max())


def comb(f, A, f_flash, m_max, half=0.45):
    out = {}
    for m in range(-m_max, m_max + 1):
        if m == 0:
            continue
        c = m * f_flash
        w = (f >= c - half * f_flash) & (f <= c + half * f_flash)
        out[m] = float(A[w].max()) if w.any() else 0.0
    return out


def comb_vec(d, m_max, m_lim=None):
    lim = m_max if m_lim is None else min(m_max, m_lim)
    return np.array([d[m] for m in range(-lim, lim + 1) if m != 0], float)


def cos_sim(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return float(a @ b / (na * nb)) if na > 0 and nb > 0 else 0.0


def los(az_deg, el_deg):
    a, e = math.radians(az_deg), math.radians(el_deg)
    return np.array([math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)])


# ═══ 기하 기준 (독립 재구현) ════════════════════════════════════════════════
def main():
    t0 = time.time()
    from drones import DRONES
    from articulated_fast import FastPoser, rotor_phases

    spec = DRONES[TJ.get("drone", "matrice4e")]
    fp = FastPoser(spec)
    prf, n = float(TJ["prf_hz"]), int(TJ["n"])
    rpms = np.asarray(TJ["rpm_per_rotor"], float)
    ph = rotor_phases(np.arange(n) / prf, rpms, fp.dirs)
    az = float(TJ.get("az_deg", 0.0))
    f_flash = float(TJ["f_flash_hz"])
    r_tip = float(spec.prop_dia_mm) / 2000.0
    f_rev = float(spec.hover_rpm) / 60.0
    f_tip0 = 2.0 * (2 * np.pi * f_rev * r_tip) / LAM
    guard = 0.5 * f_flash
    m_max = int(math.ceil(2.6 * f_tip0 / f_flash))

    g = np.asarray(fp.g, dtype=object)
    F = np.asarray(fp.f, int)
    sel_prop = np.unique(F[g == "prop"].ravel())
    rot_of = np.full(len(fp.v), -1, int)
    for i, (a, b) in enumerate(fp._rotor_slices):
        rot_of[a:b] = i
    ri = rot_of[sel_prop]
    ctrs = np.stack([np.asarray(rr["center"], float) for rr in fp.rl])

    #  얼린 격자 중심 (커널과 같은 식)
    lo = np.full(3, np.inf); hi = np.full(3, -np.inf)
    for i in range(0, n, max(1, n // 64)):
        V = fp.pose(ph[i]).v
        lo = np.minimum(lo, V.min(0)); hi = np.maximum(hi, V.max(0))
    ctr = 0.5 * (lo + hi)
    TX = np.stack([ctr + RANGE_M * los(az, el) for el in ELS])

    # ── R2 정확한 순간 도플러 상한 (독립 재계산) ──────────────────────────
    omg = np.array([rr["dir"] * 2 * np.pi * rpms[i] / 60.0 for i, rr in enumerate(fp.rl)])
    f_max_exact = np.zeros(len(ELS))
    for i in np.linspace(0, n - 1, 512).astype(int):
        P = fp.pose(ph[i]).v[sel_prop]
        V = np.zeros_like(P)
        V[:, 0] = -omg[ri] * (P[:, 1] - ctrs[ri, 1])
        V[:, 1] = omg[ri] * (P[:, 0] - ctrs[ri, 0])
        for e, tx in enumerate(TX):
            u = tx - P
            u /= np.linalg.norm(u, axis=1)[:, None]
            f_max_exact[e] = max(f_max_exact[e], float(np.abs((V * u).sum(1)).max()) * 2.0 / LAM)

    # ── 기하 기준 + D3(날개 반경 β) 변형을 한 번에 ────────────────────────
    BETAS = (1.0, 0.6, 0.75, 0.9, 1.25)
    print(f"기하 기준 {n}×{sel_prop.size}×{len(ELS)} 앙각 × β{len(BETAS)}", flush=True)
    H = {b: np.zeros((len(ELS), n), complex) for b in BETAS}
    for i in range(n):
        P0 = fp.pose(ph[i]).v[sel_prop]
        for b in BETAS:
            P = P0.copy()
            if b != 1.0:                       # 로터축 기준 **수평 반경만** 스케일 → f_tip 만 바뀐다
                P[:, :2] = ctrs[ri, :2] + b * (P0[:, :2] - ctrs[ri, :2])
            dd = np.linalg.norm(P[:, None, :] - TX[None, :, :], axis=2)
            H[b][:, i] = np.exp(1j * 2 * K * (dd - RANGE_M)).sum(axis=0)
        if i and i % 1024 == 0:
            print(f"  {i}/{n}  {time.time()-t0:.0f}s", flush=True)

    # ── D2 시간축 워프 (회전수가 α 배 틀린 기준) ──────────────────────────
    ALPHAS = (0.6, 0.75, 0.9, 1.1, 1.25, 1.4)

    def warp(z, a):
        t = np.arange(n) * a
        t = np.clip(t, 0, n - 1)
        i0 = np.floor(t).astype(int); i1 = np.minimum(i0 + 1, n - 1); w = t - i0
        return z[i0] * (1 - w) + z[i1] * w

    Z = np.load(NPZ_IN)
    rng = np.random.default_rng(20260811)

    J = dict(_meta=dict(
        generator="benchmark/verify_po_elev_adversary.py",
        stamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        role_ko="앞선 verify_po_elev_geomref.json 판정에 대한 **반증 시도**(음성대조 + 방법 견고성)",
        target="outputs/verify_po_elev_geomref.json",
        drone=spec.key, fc_hz=FC, range_m=RANGE_M, prf_hz=prf, n=n, az_deg=az,
        els_deg=list(ELS), f_flash_hz=f_flash, f_tip_ff_hz=f_tip0,
        decoys_ko=dict(D1="이웃 앙각의 기하 기준", D2=f"시간축 워프 α={ALPHAS}",
                       D3=f"날개 수평반경 β={BETAS[1:]} (f_tip 만 틀림)",
                       D4="Carson 안 대역제한 백색잡음"),
        gpu="사용 안 함"))

    # ── ⭐음성대조: G3 잣대가 «틀린 기준» 을 걸러내나 ──────────────────────
    J["negative_control_G3"] = {}
    for e, el in enumerate(ELS):
        key = f"el{el:+.0f}"
        car = float(f_max_exact[e]) + f_flash
        m_car = max(1, int(math.floor(car / f_flash)))
        zo = Z[f"ours/el{el:+.0f}"]
        fo, Ao = spectrum(zo, prf)
        eo = inband_edge20(fo, Ao, guard, car)
        co = comb(fo, Ao, f_flash, m_max)
        vo = comb_vec(co, m_max, m_car)

        cands = {"TRUE_geom": H[1.0][e]}
        for j, e2 in enumerate(ELS):                        # D1
            if e2 != el:
                cands[f"D1_geom_el{e2:+.0f}"] = H[1.0][j]
        for a in ALPHAS:                                    # D2
            cands[f"D2_warp_a{a:.2f}"] = warp(H[1.0][e], a)
        for b in BETAS[1:]:                                 # D3
            cands[f"D3_radius_b{b:.2f}"] = H[b][e]
        nz = rng.normal(size=n) + 1j * rng.normal(size=n)   # D4
        Fn = np.fft.fft(nz); fr = np.fft.fftfreq(n, 1.0 / prf)
        cands["D4_bandlimited_noise"] = np.fft.ifft(
            np.where((np.abs(fr) > guard) & (np.abs(fr) <= car), Fn, 0.0))

        rows = {}
        for nm, zr in cands.items():
            fr2, Ar = spectrum(zr, prf)
            er = inband_edge20(fr2, Ar, guard, car)
            cr = comb(fr2, Ar, f_flash, m_max)
            rows[nm] = dict(
                inband_edge20_ratio=(float(eo / er) if (eo and er) else None),
                comb_cos_inband=cos_sim(vo, comb_vec(cr, m_max, m_car)),
                passes_G3_gate=bool(eo and er and 0.6 <= eo / er <= 1.15))
        J["negative_control_G3"][key] = dict(
            el_deg=el, f_carson_hz=car, m_carson=m_car,
            ours_inband_edge20_hz=eo, rows=rows,
            n_decoys_passing_gate=int(sum(r["passes_G3_gate"] for k, r in rows.items()
                                          if k != "TRUE_geom")),
            n_decoys=len(rows) - 1)
        print(f"  {key}: G3 게이트를 통과한 **가짜** 기준 "
              f"{J['negative_control_G3'][key]['n_decoys_passing_gate']}/{len(rows)-1}", flush=True)

    # ── 초과대역(G4)을 5 가지 방법으로 다시 잰다 ──────────────────────────
    J["outband_method_robustness"] = {}
    for e, el in enumerate(ELS):
        key = f"el{el:+.0f}"
        car = float(f_max_exact[e]) + f_flash
        zo = Z[f"ours/el{el:+.0f}"]
        r = {}
        for kind in ("bh4", "nuttall", "hann", "rect"):
            f, A = spectrum(zo, prf, kind=kind)
            P = A ** 2
            ac = np.abs(f) > guard
            r[f"frac_above_carson_{kind}"] = float(P[np.abs(f) > car].sum() / P[ac].sum())
        #  시간영역 이상적 대역차단 (창·패딩 무관) — DC 는 평균 제거로 뺀다
        zz = zo - zo.mean()
        Fz = np.fft.fft(zz); fr = np.fft.fftfreq(n, 1.0 / prf)
        pac = float((np.abs(Fz[np.abs(fr) > guard]) ** 2).sum())
        pob = float((np.abs(Fz[np.abs(fr) > car]) ** 2).sum())
        r["frac_above_carson_timedomain_bruteforce"] = pob / pac
        #  ⭐절대 규모 — «AC 의 53 %» 가 전체에서 얼마인가
        r["outband_power_over_total_power_db"] = float(
            10 * np.log10(pob / float((np.abs(np.fft.fft(zo)) ** 2).sum())))
        r["outband_amp_over_dc_db"] = float(
            20 * np.log10(math.sqrt(pob / n) / (abs(zo.mean()) * math.sqrt(n) + 1e-300)))
        r["ac_over_dc_db"] = float(20 * np.log10(
            np.sqrt(np.mean(np.abs(zz) ** 2)) / (abs(zo.mean()) + 1e-300)))
        #  초과대역이 정말 평평한가 — 옥타브 프로파일(중앙값, AC 봉우리 대비)
        f, A = spectrum(zo, prf)
        pk = A[np.abs(f) > guard].max()
        prof = []
        lo_ = car
        while lo_ < 9000:
            hi_ = min(lo_ * 1.5, 9850.0)
            w = (np.abs(f) >= lo_) & (np.abs(f) < hi_)
            if w.sum() > 8:
                prof.append([float(math.sqrt(lo_ * hi_)),
                             float(20 * np.log10(np.median(A[w]) / pk))])
            lo_ = hi_
        r["octave_profile_hz_db"] = prof
        if len(prof) >= 3:
            x = np.log10([p[0] for p in prof]); y = [p[1] for p in prof]
            r["slope_db_per_decade"] = float(np.polyfit(x, y, 1)[0])
            r["profile_maxmin_spread_db"] = float(max(y) - min(y))
        J["outband_method_robustness"][key] = r

    # ── 격자 사다리 재감사: DC 자체가 수렴했나 ────────────────────────────
    J["grid_ladder_audit"] = {}
    for _el, _fn in ((-90.0, "verify_po_elev_gridscale.json"),
                     (-15.0, "verify_po_elev_gridscale_el-15.json")):
        p = os.path.join(ROOT, "outputs", _fn)
        if not os.path.exists(p):
            continue
        S = json.load(open(p))
        d, dc, fl, pw = [], [], [], []
        for k, rr in S["runs"].items():
            z = np.asarray(rr["E_re"], float) + 1j * np.asarray(rr["E_im"], float)
            f, A = spectrum(z, prf)
            w = np.abs(f) > 1500.0
            d.append(rr["spacing_m"]); dc.append(float(A.max()))
            fl.append(float(np.median(A[w]))); pw.append(float(np.sqrt((A[w] ** 2).sum())))
        d = np.array(d, float)
        ex = lambda y: float(np.polyfit(np.log10(d), np.log10(np.asarray(y, float)), 1)[0])
        J["grid_ladder_audit"][f"el{_el:+.0f}"] = dict(
            n_ladder_points=len(d), spacings_m=[float(x) for x in d],
            dc_abs=dc, dc_spread_db=float(20 * np.log10(max(dc) / min(dc))),
            dc_monotonic_in_d=bool(all(dc[i] >= dc[i + 1] for i in range(len(dc) - 1))
                                   or all(dc[i] <= dc[i + 1] for i in range(len(dc) - 1))),
            exp_far_floor_abs=ex(fl), exp_far_power_abs=ex(pw),
            exp_far_floor_rel_dc=ex(np.asarray(fl) / np.asarray(dc)),
            exp_far_power_rel_dc=ex(np.asarray(pw) / np.asarray(dc)),
            note_ko=("⭐앞 판정은 **절대** 바닥의 지수만 인용했다. DC(=코히어런트 신호) 자체가 "
                     "격자에 따라 움직이면 절대 지수는 신호 레벨의 미수렴을 함께 담는다. "
                     "정직한 지표는 DC 대비 상대 지수다."))

    with open(OUT, "w") as fo:
        json.dump(J, fo, ensure_ascii=False, indent=1)
    print(f"\n✅ 저장 → {OUT}  ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
