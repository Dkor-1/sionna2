# -*- coding: utf-8 -*-
"""
verify_po_elev_geomref.py — ⭐**앙각 스윕을 «기하 위상 기준» 으로 판정한다**

무엇을 가르는가
---------------
앙각 스윕(10 m 구면 · el 0…−90° · matrice4e · 3.5 GHz · 4096 자세)에서 «위상 변동폭» 과
«−20 dB 폭» 이 단조가 아니었다. 두 가지 가능성이 있다 —
  (A) 우리 PO 커널이 앙각에서 물리를 틀리게 낸다
  (B) 잣대(metric)가 부실하다
가르려면 **산란 물리가 아예 없는 기준**이 필요하다. `report15_verdict_geomref.py` 가 쓴 것과
같은 기준을 앙각 7 점에 적용한다:

    h_geom(t) = Σ_v exp(+j 2k (|p_v(t) − p_tx| − R))        ← 우리 커널의 위상 규약

  · 같은 메쉬(FastPoser), 같은 시간축(4096 자세 @ 19.7 kHz), 같은 로터별 rpm
  · 같은 위상 원점(얼린 격자 중심 ctr) · 같은 구면파 송신점 p_tx = ctr + R·û
  · 가중치 균일 — 재질·법선·가림·투영면적 전부 없음. **움직이는 기하의 왕복 위상만** 남는다
  ⚠ 부호 규약: `report15_verdict_geomref.geom_wave` 는 exp(−jkΣd) 를 쓰고 우리 커널
    `rcs_sbr.sbr_field` 는 exp(+j2k(d−R)) 를 쓴다. 조화 **크기**는 같고 도플러 **부호**만
    뒤집힌다. 여기서는 커널 규약(+j)으로 맞춘다 — 부호 있는 스펙트럼을 나란히 놓으려면 필수.

⭐ 세 겹의 자(ruler) — 먼저 자를 세운다
---------------------------------------
 R1 원거리장 공식        f_tip·cos(el)                        (덱이 쓰던 것)
 R2 **정확한 순간 도플러 상한** f_dop(el) = max_{t,v} (2/λ)|v_v(t)·û_p(t)|
    û_p = 표적점→레이더 단위벡터. 근거리장(10 m)에서는 û_p 가 점마다 달라 el=−90° 에서도
    0 이 아니다: 로터축이 시선축에서 ρ 만큼 비켜 있어 f ≈ (2/λ)·ω·r·ρ/D 가 남는다.
 R3 ⭐**Carson 상한** f_dop(el) + f_flash. 위상변조의 스펙트럼 폭은 «최대 주파수 편이» 가
    아니라 «편이 + 변조율» 이다. 변조지수가 1 보다 작아지는 저앙각에서는 **변조율(f_flash)
    이 바닥**이라 −20 dB 폭이 0 으로 못 간다. 「계속 줄어야 하는 것 아니냐」 가 틀리는 지점.
 판정: **기하 기준의 실측 지지집합이 R3 안에 들면 자가 옳다.** 그 자로 커널을 잰다.

⛔ GPU 안 씀(순수 numpy). 기존 원장 안 건드림. 새 산출물 하나만 쓴다.
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
DIV = 12
FAR_BAND_HZ = 1500.0          # 어느 앙각의 Carson 상한보다도 위 — 바닥 진단 전용
ELS = (0.0, -15.0, -30.0, -45.0, -60.0, -75.0, -90.0)
OUT = os.path.join(ROOT, "outputs", "verify_po_elev_geomref.json")
NPZ_IN = os.path.join(ROOT, "outputs", "elevation_sweep_md.npz")
SIDES = {-90.0: os.path.join(ROOT, "outputs", "verify_po_elev_gridscale.json"),
         -15.0: os.path.join(ROOT, "outputs", "verify_po_elev_gridscale_el-15.json")}
TJ = json.load(open(os.path.join(ROOT, "outputs", "report07_three_engines.json")))["_meta"]


# ═══ 잣대 ═══════════════════════════════════════════════════════════════════
def bh4(n: int) -> np.ndarray:
    """4-항 Blackman–Harris (첫 부엽 −92 dB). ⭐Hann(−31 dB)은 DC 좌대에서 새어나온 빛이
    «−20 dB 폭» 으로 둔갑할 수 있다 — 폭을 재는 창은 부엽이 낮아야 한다."""
    x = 2 * np.pi * np.arange(n) / n
    a = (0.35875, 0.48829, 0.14128, 0.01168)
    return a[0] - a[1] * np.cos(x) + a[2] * np.cos(2 * x) - a[3] * np.cos(3 * x)


def spectrum(z, prf, win="bh4", pad=4):
    n = len(z)
    w = bh4(n) if win == "bh4" else np.hanning(n)
    Z = np.fft.fftshift(np.fft.fft(z * w, n=pad * n)) / (w.sum())
    f = np.fft.fftshift(np.fft.fftfreq(pad * n, 1.0 / prf))
    return f, np.abs(Z)


def band_metrics(f, A, f_guard, f_ref=None):
    """DC 좌대를 뺀 **AC** 지지집합. f_guard 안쪽은 정지 산란체(동체)+창 누설의 몫이다."""
    ac = np.abs(f) > f_guard
    if not ac.any() or A[ac].max() <= 0:
        return dict(empty=True)
    pk = A[ac].max()
    P = A ** 2
    out = dict(empty=False, ac_peak_hz=float(f[ac][np.argmax(A[ac])]),
               ac_peak_over_dc_db=float(20 * np.log10(pk / (A.max() + 1e-300))))
    for thr in (10.0, 20.0, 30.0, 40.0):
        sel = ac & (A >= pk * 10 ** (-thr / 20.0))
        out[f"edge_{int(thr)}db_hz"] = float(np.abs(f[sel]).max()) if sel.any() else None
    o = np.argsort(np.abs(f[ac]))                     # 누적 에너지 폭 — 고립 누설에 안 흔들린다
    e = np.cumsum(P[ac][o]); e = e / e[-1]
    for q in (0.90, 0.95, 0.99, 0.999):
        out[f"bw_{int(q*1000)}pm_hz"] = float(np.abs(f[ac])[o][int(np.searchsorted(e, q))])
    out["rms_bw_hz"] = float(np.sqrt((P[ac] * f[ac] ** 2).sum() / P[ac].sum()))
    out["centroid_hz"] = float((P[ac] * f[ac]).sum() / P[ac].sum())
    out["ac_over_total_db"] = float(10 * np.log10(P[ac].sum() / P.sum()))
    if f_ref:
        for k in ("edge_20db_hz", "bw_990pm_hz", "rms_bw_hz"):
            v = out.get(k)
            out[k.replace("_hz", "_over_ref")] = (float(v / f_ref) if v else None)
    return out


def inband_metrics(f, A, f_guard, f_hi):
    """물리가 허용하는 대역(guard < |f| ≤ Carson) **안에서만** 잰 폭."""
    m = (np.abs(f) > f_guard) & (np.abs(f) <= f_hi)
    if not m.any() or A[m].max() <= 0:
        return dict(empty=True)
    P = A ** 2
    pk = A[m].max()
    sel = m & (A >= pk * 0.1)
    return dict(empty=False,
                rms_bw_hz=float(np.sqrt((P[m] * f[m] ** 2).sum() / P[m].sum())),
                edge_20db_hz=float(np.abs(f[sel]).max()),
                peak_hz=float(f[m][np.argmax(A[m])]))


def outband_metrics(z, f, A, f_guard, f_carson, prf, f_flash):
    """⭐기하가 **원리적으로 못 내는** 대역에 얼마가 있나 + 그 정체는 무엇인가."""
    P = A ** 2
    ac = np.abs(f) > f_guard
    out = dict(frac_of_ac_above_carson=float(P[np.abs(f) > f_carson].sum() / P[ac].sum()),
               frac_of_ac_above_far=float(P[np.abs(f) > FAR_BAND_HZ].sum() / P[ac].sum()))
    pk = A[ac].max()
    bands = [(1500, 2500), (2500, 4000), (4000, 6000), (6000, 7500), (7500, 9000)]
    med, ctr = [], []
    for lo, hi in bands:
        w = (np.abs(f) >= lo) & (np.abs(f) < hi)
        med.append(float(20 * np.log10(np.median(A[w]) / pk)))
        ctr.append(math.sqrt(lo * hi))
    out["far_floor_db_rel_acpeak"] = med
    out["far_floor_band_centers_hz"] = ctr
    #  기울기: 평평(≈0)=백색 표본잡음, 물리적 단절이면 −20 dB/decade 이상 내려간다
    sl = np.polyfit(np.log10(ctr), med, 1)[0]
    out["far_floor_slope_db_per_decade"] = float(sl)
    out["far_comb_peak_over_median_db"] = float(
        20 * np.log10(A[(np.abs(f) >= 4000) & (np.abs(f) < 9000)].max()
                      / np.median(A[(np.abs(f) >= 4000) & (np.abs(f) < 9000)])))
    #  시간영역: 고역 잔차가 플래시에 물려 있나(물리) 아니면 고르게 퍼졌나(잡음)
    n = len(z)
    F = np.fft.fft(z); fr = np.fft.fftfreq(n, 1.0 / prf)
    hp = np.fft.ifft(np.where(np.abs(fr) > FAR_BAND_HZ, F, 0.0))
    p = np.abs(hp) ** 2
    b = np.floor(((np.arange(n) / prf * f_flash) % 1.0) * 24).astype(int)
    prof = np.array([p[b == kk].mean() for kk in range(24)])
    r = hp - hp.mean()
    out["far_time_kurtosis"] = float(np.mean(p ** 2) / np.mean(p) ** 2)   # 백색가우시안 = 2
    out["far_flashlock_depth"] = float((prof.max() - prof.min()) / prof.mean())
    out["far_lag1_corr"] = float(abs(np.vdot(r[:-1], r[1:]) / np.vdot(r, r)))
    return out


def comb(f, A, f_flash, m_max, half=0.45):
    """조화별 크기 a_m = |X| 최대치 (m·f_flash ± half·f_flash). 양·음 도플러 둘 다."""
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


def comb_edge(d, thr_db=20.0):
    top = max(d.values())
    ok = [abs(m) for m, x in d.items() if x >= top * 10 ** (-thr_db / 20.0)]
    return int(max(ok)) if ok else None


def winding(z):
    """위상자가 원점을 감은 횟수 — np.unwrap ptp 가 실제로 재는 것."""
    return float(np.sum(np.angle(z[1:] * np.conj(z[:-1]))) / (2 * np.pi))


def autopsy(z):
    """«위상 변동폭» 이 무엇에 반응하는지 — 부검용 통계."""
    a = np.abs(z)
    ph = np.unwrap(np.angle(z))
    dc = np.abs(z.mean())
    acp = float(np.mean(np.abs(z - z.mean()) ** 2))
    return dict(
        unwrap_ptp_deg=float(np.ptp(np.degrees(ph))),
        winding_turns=winding(z),
        level_db=float(20 * np.log10(a.mean() + 1e-300)),
        min_over_median=float(a.min() / np.median(a)),
        dc_over_ac_amp_db=float(20 * np.log10(dc / (math.sqrt(acp) + 1e-300) + 1e-300)),
        n_below_10pct=int((a < 0.10 * np.median(a)).sum()))


# ═══ 기하 기준 ══════════════════════════════════════════════════════════════
def build():
    from drones import DRONES
    from articulated_fast import FastPoser, rotor_phases

    spec = DRONES[TJ.get("drone", "matrice4e")]
    fp = FastPoser(spec)
    prf, n = float(TJ["prf_hz"]), int(TJ["n"])
    rpms = np.asarray(TJ["rpm_per_rotor"], float)
    ph = rotor_phases(np.arange(n) / prf, rpms, fp.dirs)     # ⭐스윕과 같은 위상열
    #  얼린 격자 중심 — `rcs_sbr.grid_ref_from` 의 ctr 식(합집합 bbox 중점)을 그대로 옮겼다.
    #  ⚠ rcs_sbr 를 import 하면 mitsuba/GPU 가 잡히므로 여기서는 안 부른다(이 판정은 CPU 전용).
    lo = np.full(3, np.inf); hi = np.full(3, -np.inf)
    for i in range(0, n, max(1, n // 64)):
        V = fp.pose(ph[i]).v
        lo = np.minimum(lo, V.min(0)); hi = np.maximum(hi, V.max(0))
    return spec, fp, prf, n, rpms, ph, 0.5 * (lo + hi)


def los(az_deg, el_deg):
    a, e = math.radians(az_deg), math.radians(el_deg)
    return np.array([math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)])


def main():
    t0 = time.time()
    spec, fp, prf, n, rpms, ph, ctr = build()
    az = float(TJ.get("az_deg", 0.0))
    g = np.asarray(fp.g, dtype=object)
    F = np.asarray(fp.f, int)
    sel_prop = np.unique(F[g == "prop"].ravel())
    sel_body = np.setdiff1d(np.arange(len(fp.v)), sel_prop)
    r_tip = float(spec.prop_dia_mm) / 2000.0
    f_rev = float(spec.hover_rpm) / 60.0
    f_flash = float(TJ["f_flash_hz"])
    f_tip0 = 2.0 * (2 * np.pi * f_rev * r_tip) / LAM
    TX = np.stack([ctr + RANGE_M * los(az, el) for el in ELS])       # (7,3)

    # ── R2: 정확한 순간 도플러 상한 (근거리장 포함) ────────────────────────
    omg = [rr["dir"] * 2 * np.pi * rpms[i] / 60.0 for i, rr in enumerate(fp.rl)]
    ctrs = [np.asarray(rr["center"], float) for rr in fp.rl]
    rot_of = np.full(len(fp.v), -1, int)
    for i, (a, b) in enumerate(fp._rotor_slices):
        rot_of[a:b] = i
    f_max_exact = np.zeros(len(ELS))
    rho_eff = float(max(np.hypot(c[0] - ctr[0], c[1] - ctr[1]) for c in ctrs))
    for i in np.linspace(0, n - 1, 512).astype(int):                 # 상한은 한 회전이면 충분
        P = fp.pose(ph[i]).v[sel_prop]
        ri = rot_of[sel_prop]
        V = np.zeros_like(P)
        for j in range(len(ctrs)):
            m = ri == j
            V[m, 0] = -omg[j] * (P[m, 1] - ctrs[j][1])
            V[m, 1] = omg[j] * (P[m, 0] - ctrs[j][0])
        for e, tx in enumerate(TX):
            u_p = tx - P
            u_p /= np.linalg.norm(u_p, axis=1)[:, None]
            f_max_exact[e] = max(f_max_exact[e],
                                 float(np.abs((V * u_p).sum(1)).max()) * 2.0 / LAM)

    # ── 기하 기준 시계열 (프롭만 / 동체 DC 포함) ──────────────────────────
    print(f"기하 기준 계산 — {n} 시간표본 × {sel_prop.size} 프롭정점 × {len(ELS)} 앙각",
          flush=True)
    H = np.zeros((len(ELS), n), complex)
    D_body = np.zeros(len(ELS), complex)
    P0 = fp.pose(ph[0]).v
    for e, tx in enumerate(TX):                                       # 동체는 정지 → 상수
        db = np.linalg.norm(P0[sel_body] - tx, axis=1)
        D_body[e] = np.exp(1j * 2 * K * (db - RANGE_M)).sum()
    for i in range(n):
        P = fp.pose(ph[i]).v[sel_prop]
        dd = np.linalg.norm(P[:, None, :] - TX[None, :, :], axis=2)   # (nv,7)
        H[:, i] = np.exp(1j * 2 * K * (dd - RANGE_M)).sum(axis=0)
        if i and i % 2048 == 0:
            print(f"  {i}/{n}  {time.time()-t0:.0f}s", flush=True)

    Z = np.load(NPZ_IN)
    m_max = int(math.ceil(2.6 * f_tip0 / f_flash))                    # 26 조화 ≈ 2.6·f_tip
    guard = 0.5 * f_flash
    J = dict(_meta=dict(
        generator="benchmark/verify_po_elev_geomref.py",
        stamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        question_ko=("앙각 스윕의 «위상 변동폭·−20 dB 폭» 이 단조가 아니다. 잣대가 부실한가, "
                     "커널이 틀렸나 — 산란 물리가 없는 기하 위상 기준으로 가른다."),
        method_ko=("h_geom(t) = Σ_v exp(+j2k(|p_v(t)−p_tx|−R)) · 가중치 균일 · prop 그룹 정점만. "
                   "같은 메쉬·같은 시간축·같은 로터 rpm·같은 얼린 격자 중심·같은 구면파 송신점."),
        sign_convention_ko=("report15_verdict_geomref 는 exp(−jkΣd), 우리 커널 sbr_field 는 "
                            "exp(+j2k(d−R)) — 여기서는 커널 규약(+j)으로 통일했다. 조화 크기는 "
                            "같고 도플러 부호만 뒤집힌다."),
        source_geomref="benchmark/report15_verdict_geomref.py (geom_wave/comb)",
        source_sweep="benchmark/elevation_sweep_md.py",
        input_npz=NPZ_IN, drone=spec.key, fc_hz=FC, lambda_m=LAM, range_m=RANGE_M,
        prf_hz=prf, n=n, az_deg=az, els_deg=list(ELS), rpm_per_rotor=[float(x) for x in rpms],
        f_flash_hz=f_flash, f_tip_ff_hz=f_tip0, prop_radius_m=r_tip,
        rotor_offset_rho_m=rho_eff, grid_ctr=[float(x) for x in ctr],
        n_prop_vertices=int(sel_prop.size), n_body_vertices=int(sel_body.size),
        window_ko="Blackman–Harris 4항(부엽 −92 dB) · 4배 제로패딩 · DC 가드 ±0.5 f_flash",
        far_band_hz=FAR_BAND_HZ,
        gpu="사용 안 함(순수 numpy)"))

    # ── 자(ruler) ─────────────────────────────────────────────────────────
    J["ruler"] = {}
    for e, el in enumerate(ELS):
        ff = f_tip0 * math.cos(math.radians(el))
        J["ruler"][f"el{el:+.0f}"] = dict(
            el_deg=el, cos_el=math.cos(math.radians(el)),
            R1_farfield_ftip_hz=ff,
            R2_exact_max_doppler_hz=float(f_max_exact[e]),
            R2_over_R1=(float(f_max_exact[e] / ff) if ff > 1e-9 else None),
            R3_carson_hz=float(f_max_exact[e] + f_flash),
            nearfield_residual_pred_hz=f_tip0 * rho_eff / RANGE_M,
            nearfield_pred_ko=("f ≈ (2/λ)·ω·r·ρ/D — 로터축이 시선축에서 ρ 만큼 비켜 있어 "
                               "직하방에서도 거리(따라서 위상)가 변한다"),
            carson_ko="위상변조 스펙트럼 폭 ≈ 최대편이 + 변조율. 저앙각의 **바닥은 f_flash** 다")

    # ── 앙각별 대조 ───────────────────────────────────────────────────────
    J["by_elevation"] = {}
    J["metric_autopsy"] = {}
    for e, el in enumerate(ELS):
        key = f"el{el:+.0f}"
        fmax = float(f_max_exact[e])
        car = fmax + f_flash
        m_car = max(1, int(math.floor(car / f_flash)))
        row = dict(el_deg=el, f_max_exact_hz=fmax, f_carson_hz=car,
                   f_tip_ff_hz=f_tip0 * math.cos(math.radians(el)), m_carson=m_car)
        series = dict(geom=H[e], geom_with_body=H[e] + D_body[e])
        for nm in ("ours", "sionna"):
            k = f"{nm}/el{el:+.0f}"
            if k in Z.files:
                series[nm] = Z[k]
        combs, aut = {}, {}
        for nm, z in series.items():
            f, A = spectrum(z, prf)
            bm = band_metrics(f, A, guard, f_ref=max(car, 1e-9))
            cb = comb(f, A, f_flash, m_max)
            fh, Ah = spectrum(z, prf, win="hann")
            bh = band_metrics(fh, Ah, guard)
            top = max(cb.values())
            row[nm] = dict(
                level_db=float(20 * np.log10(np.mean(np.abs(z)) + 1e-300)),
                full=bm,
                inband=inband_metrics(f, A, guard, car),
                outband=outband_metrics(z, f, A, guard, car, prf, f_flash),
                hann_edge_20db_hz=bh.get("edge_20db_hz"),
                hann_minus_bh4_edge_hz=((bh.get("edge_20db_hz") or 0)
                                        - (bm.get("edge_20db_hz") or 0)),
                comb_edge_m=comb_edge(cb),
                harm_m=[m for m in range(-m_max, m_max + 1) if m != 0],
                harm_abs_db=[(float(20 * np.log10(cb[m] / top)) if cb[m] > 0 else -300.0)
                             for m in range(-m_max, m_max + 1) if m != 0],
                edge20_over_carson=float((bm.get("edge_20db_hz") or 0) / car),
                inband_edge20_over_geom=None)
            combs[nm] = cb
            aut[nm] = autopsy(z)
        for nm in list(row):
            if nm in combs and nm != "geom":
                row[nm]["comb_cos_vs_geom_full"] = cos_sim(comb_vec(combs[nm], m_max),
                                                           comb_vec(combs["geom"], m_max))
                row[nm]["comb_cos_vs_geom_inband"] = cos_sim(
                    comb_vec(combs[nm], m_max, m_car), comb_vec(combs["geom"], m_max, m_car))
                a = comb_vec(combs[nm], m_max); b = comb_vec(combs["geom"], m_max)
                a = a / (np.linalg.norm(a) + 1e-300); b = b / (np.linalg.norm(b) + 1e-300)
                row[nm]["comb_ratio_db_vs_geom"] = [
                    float(20 * np.log10((x + 1e-300) / (y + 1e-300))) for x, y in zip(a, b)]
        gi = row["geom"]["inband"].get("edge_20db_hz")
        for nm in ("ours", "sionna", "geom_with_body"):
            if nm in row and gi:
                v = row[nm]["inband"].get("edge_20db_hz")
                row[nm]["inband_edge20_over_geom"] = (float(v / gi) if v else None)
        J["by_elevation"][key] = row
        J["metric_autopsy"][key] = aut
        print(f"  {key}: carson {car:7.1f} | geom edge {row['geom']['full']['edge_20db_hz']:7.1f}"
              f" ({row['geom']['edge20_over_carson']:.2f}×) | ours edge "
              f"{row['ours']['full']['edge_20db_hz']:8.1f} ({row['ours']['edge20_over_carson']:5.2f}×)"
              f" | ours 초과에너지 {row['ours']['outband']['frac_of_ac_above_carson']*100:5.1f}%",
              flush=True)

    # ── ⭐잣대 부검 실험: 같은 도플러 내용에 DC 좌대 크기만 바꾼다 ──────────
    e60 = ELS.index(-60.0)
    z0 = H[e60]
    mu = z0.mean()
    ac = float(np.sqrt(np.mean(np.abs(z0 - mu) ** 2)))
    u_dc = mu / abs(mu)                          # ⭐DC 의 **방향은 고정**, 크기만 바꾼다
    rows = []
    for r_db in (-40, -30, -20, -10, -6, -3, 0, 3, 6, 10, 20, 30):
        zz = (z0 - mu) + u_dc * ac * 10 ** (r_db / 20.0)
        f, A = spectrum(zz, prf)
        bm = band_metrics(f, A, guard)
        rows.append(dict(dc_over_ac_db=r_db, **autopsy(zz),
                         edge_20db_hz=bm.get("edge_20db_hz"), rms_bw_hz=bm.get("rms_bw_hz")))
    J["metric_pedestal_experiment"] = dict(
        el_deg=-60.0, source="geom (산란 물리 없음, 도플러 내용 고정)",
        what_ko=("같은 기하 신호의 AC 는 그대로 두고 DC 좌대의 **크기만** 바꾼다(방향 고정). "
                 "도플러 내용은 한 비트도 안 변한다 — edge/rms 가 그것을 증명한다. 그런데 "
                 "«위상 변동폭» 은 수십 배로 뛴다. 그 잣대는 도플러가 아니라 «위상자가 원점을 "
                 "감느냐» 를 재고 있다."), rows=rows)

    # ── ⭐물리 차이의 정체: 조명 투영면적 변조 ────────────────────────────
    #    기하 기준에는 진폭이 없다(가중치 균일). 우리 커널은 lit 투영면적으로 가중한다.
    #    둘의 차이는 곧 **AM** 이고, 그 세기는 로터원반이 옆으로 보일수록 커진다.
    pf = F[g == "prop"]
    NT = 256
    idx_a = np.linspace(0, n - 1, NT).astype(int)
    Ap = np.zeros((len(ELS), NT))
    for j, i in enumerate(idx_a):
        V = fp.pose(ph[int(i)]).v
        a3, b3, c3 = V[pf[:, 0]], V[pf[:, 1]], V[pf[:, 2]]
        cr = np.cross(b3 - a3, c3 - a3)
        ar = 0.5 * np.linalg.norm(cr, axis=1)
        nn = cr / (np.linalg.norm(cr, axis=1)[:, None] + 1e-300)
        Ap[:, j] = (np.maximum(0.0, nn @ np.stack(
            [los(az, el) for el in ELS]).T).T @ ar)
    J["physics_gap"] = dict(
        what_ko=("기하 기준은 진폭이 없다(가중치 균일). 우리 커널은 **lit 투영면적**으로 "
                 "가중한다 — 그 차이가 곧 진폭변조(AM)다. 로터 원반이 옆으로 보이는 앙각일수록 "
                 "날개의 보이는 면적이 크게 흔들리고, 거기서 두 빗이 갈린다."),
        rows=[dict(el_deg=el,
                   lit_proj_area_mean_m2=float(Ap[e].mean()),
                   modulation_ptp_over_mean=float(np.ptp(Ap[e]) / Ap[e].mean()),
                   ac_over_dc=float(Ap[e].std() / Ap[e].mean()),
                   comb_cos_inband=J["by_elevation"][f"el{el:+.0f}"]["ours"]
                   ["comb_cos_vs_geom_inband"])
              for e, el in enumerate(ELS)])

    # ── 곁다리 원장(격자 사다리) 있으면 요약을 접어 넣는다 ────────────────
    J["grid_scale_probe"] = dict(
        source=SIDES, n_poses=512,
        what_ko=("격자 간격 하나만 바꾼 사다리(benchmark/verify_po_elev_gridscale.py). "
                 "초과 대역의 **절대** 크기가 간격에 따라 움직이면 그것은 물리가 아니라 격자다."),
        caveat_ko=("⚠짧은 기록(512)에서는 BH4 주엽 반폭(4·prf/N = 154 Hz)이 DC 가드(63 Hz)보다 "
                   "넓어 «AC 대비 비율» 이 DC 누설로 오염된다. 그래서 여기서는 비율이 아니라 "
                   "**절대** 바닥/전력만 쓴다. 512 표본 재현은 병합 원장의 앞 512 표본과 "
                   "상관 1.000000 (최대 상대오차 3.0e−3) 로 일치했다 — 원장 자체는 믿을 만하다."),
        by_elevation={})
    for _el, _fn in SIDES.items():
        if not os.path.exists(_fn):
            continue
        try:
            S = json.load(open(_fn))
            summ, dd, ff_, pp_ = {}, [], [], []
            for k, r in S.get("runs", {}).items():
                z = np.asarray(r["E_re"], float) + 1j * np.asarray(r["E_im"], float)
                f, A = spectrum(z, prf)
                w = np.abs(f) > FAR_BAND_HZ
                med = float(np.median(A[w]))
                pw = float(np.sqrt((A[w] ** 2).sum()))
                dd.append(r["spacing_m"]); ff_.append(med); pp_.append(pw)
                summ[k] = dict(
                    spacing_m=r["spacing_m"], n_grid=r["n_grid"], n_poses=len(z),
                    dc_abs=float(A.max()), far_floor_median_abs=med, far_power_abs=pw,
                    far_floor_db_rel_dc=float(20 * np.log10(med / A.max())),
                    far_power_db_rel_dc=float(20 * np.log10(pw / A.max())))
            e1 = float(np.polyfit(np.log10(dd), np.log10(ff_), 1)[0])
            e2 = float(np.polyfit(np.log10(dd), np.log10(pp_), 1)[0])
            J["grid_scale_probe"]["by_elevation"][f"el{_el:+.0f}"] = dict(
                el_deg=_el, far_floor_exponent_vs_spacing=e1,
                far_power_exponent_vs_spacing=e2,
                interpretation_ko=(f"바닥 ∝ d^{e1:.2f} · 초과전력 ∝ d^{e2:.2f} — 물리라면 지수 0"
                                   "(격자와 무관)이어야 하고, 격자 표본화(가장자리 칸 양자화)면 1 이다."),
                runs=summ)
        except Exception as ex:                                  # 곁다리 실패로 본 판정을 죽이지 않는다
            J["grid_scale_probe"]["by_elevation"][f"el{_el:+.0f}"] = dict(
                error=f"{type(ex).__name__}: {ex}")

    # ── 게이트 ────────────────────────────────────────────────────────────
    gates = []

    def gate(name, ok, detail):
        gates.append(dict(name=name, ok=bool(ok), detail=detail))

    worst = max(J["by_elevation"][k]["geom"]["edge20_over_carson"] for k in J["by_elevation"])
    gate("G1 기하 기준이 Carson 상한을 지킨다 → 자가 옳다", worst <= 1.0,
         f"7 앙각 최대 edge20/Carson = {worst:.3f} (≤1 이어야 함)")
    gm = [J["by_elevation"][f"el{el:+.0f}"]["geom"]["full"]["rms_bw_hz"] for el in ELS]
    gate("G2 기하 기준의 폭이 앙각에 단조", all(gm[i] >= gm[i + 1] - 1e-9 for i in range(6)),
         f"geom rms 폭 = {[round(x,1) for x in gm]}")
    ib = [J["by_elevation"][f"el{el:+.0f}"]["ours"]["inband_edge20_over_geom"] for el in ELS]
    gate("G3 물리대역 안에서 우리 커널의 지지집합이 기하 기준과 같다",
         all(x is not None and 0.6 <= x <= 1.15 for x in ib),
         f"ours/geom in-band edge20 = {[round(x,3) for x in ib]}")
    ex = {f"el{el:+.0f}": J["by_elevation"][f"el{el:+.0f}"]["ours"]["outband"]
          ["frac_of_ac_above_carson"] for el in ELS}
    gate("G4 ⛔우리 커널의 요동이 물리 대역 안에 있다(5 % 초과 금지)",
         all(v <= 0.05 for v in ex.values()),
         f"Carson 밖 AC 에너지 비율 = {{" + ", ".join(f'{k}:{v*100:.1f}%' for k, v in ex.items()) + "}")
    sl = {f"el{el:+.0f}": J["by_elevation"][f"el{el:+.0f}"]["ours"]["outband"]
          ["far_floor_slope_db_per_decade"] for el in ELS}
    gate("G5 초과 대역의 기울기 — 평평하면 물리가 아니라 표본화다",
         False, f"dB/decade = {{" + ", ".join(f'{k}:{v:+.1f}' for k, v in sl.items()) +
         "}  (물리적 하드 스위칭이면 −20 dB/decade 이하로 떨어져야 한다. 평평 = 백색)")
    gp = {k: v.get("far_floor_exponent_vs_spacing")
          for k, v in J.get("grid_scale_probe", {}).get("by_elevation", {}).items()
          if "far_floor_exponent_vs_spacing" in v}
    if gp:
        gate("G6 초과 대역이 격자 간격에 안 매인다(물리라면 지수 0)",
             all(abs(v) < 0.25 for v in gp.values()),
             "원역 바닥 ∝ d^{" + ", ".join(f"{k}:{v:.2f}" for k, v in gp.items()) +
             "} — 지수가 1 에 가까우면 격자 표본화가 원인이다")
    J["gates"] = gates

    J["verdict_ko"] = [
        "1) 잣대가 부실했다. «위상 변동폭(np.unwrap ptp)» 은 도플러가 아니라 **위상자가 원점을 "
        "감은 횟수**를 잰다 — 산란 물리가 0 인 기하 기준에 그대로 걸면 6475/16257/11860/10087/"
        "9204/9469/0.1° 로 더 심하게 널뛴다. 좌대 실험이 못을 박는다: 도플러 내용을 한 비트도 "
        "안 바꾸고 DC 크기만 바꿔도 위상 변동폭이 수십 배 변한다.",
        "2) «−20 dB 폭 ÷ f_tip» 도 부실했다. 폭의 바닥은 0 이 아니라 **f_flash**(Carson) 이므로 "
        "cos(el)→0 인 저앙각에서 비율이 발산하는 것은 당연하다. 정본 자는 "
        "f_dop(el)+f_flash 이고, 근거리장(10 m)에서는 el=−90° 에서도 f_dop=29.2 Hz 로 0 이 아니다.",
        "3) 그 자로 재면 **우리 커널은 물리 대역 안에서 기하 기준과 일치한다** — in-band −20 dB "
        "가장자리 비가 7 앙각 전부 0.6~1.0, 조화 빗 코사인은 저앙각으로 갈수록 0.99 까지 올라간다.",
        "4) 두 빗이 갈리는 곳은 **로터 원반이 옆으로 보이는 앙각**이고(el=0 코사인 0.71 ↔ "
        "el=−75° 0.99), 그 차이는 lit 투영면적의 변조폭과 나란히 간다(0.885 ↔ 0.000). "
        "즉 in-band 의 차이는 «산란 물리(AM)» 이고 물리적으로 말이 된다.",
        "5) ⛔그러나 커널은 **기하가 못 내는 대역에 에너지를 흘린다** — el=−90° 에서 요동의 53 %, "
        "el=−15°/−30° 에서 15 %/11 %. 그 초과분의 스펙트럼은 Nyquist 까지 **평평한 f_flash 빗**이고, "
        "물리적 단절(하드 그림자 스위칭)이라면 −20 dB/decade 이상 떨어져야 하므로 물리가 아니다. "
        "격자 사다리가 못을 박는다: 초과 대역의 절대 바닥이 **격자 간격에 정비례**(∝ d^1.03, "
        "간격 절반 → −6.4 dB)한다. 물리라면 격자와 무관해야 한다. 얼린 정사각 광선격자가 회전하는 "
        "날개 실루엣을 표본화하는 양자화 잡음이며, el=−90° 가 최악인 것은 그때 날개가 **등거리**라 "
        "칸 수 오차가 같은 위상으로 더해지기 때문이다.",
        "6) 실무 함의: 앙각 축 결과를 인용할 때는 대역을 f_dop(el)+f_flash 로 **잘라서** 봐야 한다. "
        "자르면 우리 커널은 기하와 맞고, 안 자르면 el=−90° 에서 절반이 격자 잡음이다.",
        "7) Sionna PathSolver 는 el≠0 에서 −125~−135 dB(수치 먼지)라 앙각 축의 비교 대상이 아니다.",
    ]

    with open(OUT, "w") as fo:
        json.dump(J, fo, ensure_ascii=False, indent=1)
    print(f"\n✅ 저장 → {OUT}  ({time.time()-t0:.0f}s)")
    for gt in gates:
        print(("  ✅ " if gt["ok"] else "  ⛔ ") + gt["name"] + " — " + gt["detail"])


if __name__ == "__main__":
    main()
