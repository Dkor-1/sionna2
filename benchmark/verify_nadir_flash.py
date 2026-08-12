# -*- coding: utf-8 -*-
"""verify_nadir_flash.py — **«나딧에서 도플러는 0 인데 플래시는 남는다» 가 사실인가.**

배경(2026-08-11)
----------------
메인 세션이 사용자에게 «앙각 −90°(바로 아래에서 올려다봄)에서 도플러는 사라지지만 블레이드
플래시는 남는다» 고 말했다. 근거는 `outputs/elevation_sweep_md.json` 의
`ours / el −90 / fixed.beat_hz = 126.78 Hz` 하나뿐이었다.

이 스크립트가 하는 일 — 그 주장을 **의심하고 분해한다.**
  A. 잣대 감사      `elevation_sweep_md.band_metrics` 가 정확히 무엇을 재는지.
                    합성신호로 «대역 안 에너지가 원리적으로 0» 인 것을 넣어 본다.
  B. 신호 분해      E 스펙트럼 대 |E| 스펙트럼, DC/AC, 위상 대 진폭(반송파 기준),
                    빗살 선의 잡음 대비 dB, 430~1229 Hz 의 실제 내용물.
  C. 기전 가르기    ⭐순수 기하(CPU, SBR 호출 없음)로 세 후보를 가른다 —
                    (a) 투영 면적 변화 (b) 간섭 무늬 회전 (c) 격자 잡음.
  D. 거리·각도 의존 근접장 곡률이 원인이면 거리를 늘리면 사라져야 한다. 재 본다.

⚠ GPU 를 쓰지 않는다. `sbr_field` 를 호출하지 않고, 같은 메쉬·같은 로터 위상 위에서
  **평면 패싯 PO 대리모형**(재질·가림·다중반사 없음)만 돌린다. 그래서 이 스크립트의 결론은
  «기전이 무엇인가» 에 대한 것이고, 절대값은 원장(SBR) 쪽을 쓴다.

    PYTHONPATH=src:benchmark python benchmark/verify_nadir_flash.py
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from md_mapstyle import auto_periods, flash_spec, FLASH_HOP   # noqa: E402

OUT_J = f"{ROOT}/outputs/verify_nadir_flash.json"
OUT_P = f"{ROOT}/outputs/verify_nadir_flash.png"
SWEEP_J = f"{ROOT}/outputs/elevation_sweep_md.json"
SWEEP_N = f"{ROOT}/outputs/elevation_sweep_md.npz"

TJ = json.load(open(f"{ROOT}/outputs/report07_three_engines.json"))["_meta"]
PRF = float(TJ["prf_hz"])
FFL = float(TJ["f_flash_hz"])
FT_DECK = float(TJ["f_tip_hz"])
FC, RANGE_M = 3.5e9, 10.0
LAM = 2.998e8 / FC
K = 2 * np.pi / LAM
N = int(TJ["n"])
RPMS = np.asarray(TJ["rpm_per_rotor"], float)
PER = auto_periods(PRF, FFL)
NPER = int(round(PER * (PRF / FFL)))
LO, HI = 0.35 * FT_DECK, FT_DECK          # 덱의 −15° «고정 대역»


# ═══ A. 잣대 감사 ═══════════════════════════════════════════════════════════
def band_metrics(E, lo, hi):
    """`benchmark/elevation_sweep_md.py` 의 band_metrics **복제**(그 파일은 gpu 를 끌어온다)."""
    f, t, S, _ = flash_spec(np.asarray(E, complex), PRF, FFL, PER)
    b = (np.abs(f) >= lo) & (np.abs(f) <= hi)
    if b.sum() < 2:
        return dict(n_bins=int(b.sum()), beat_hz=None, band_power_db=None)
    g = (S[b, :] ** 2).sum(axis=0)
    pw = 10 * np.log10(g.mean())
    g = g - g.mean()
    dt = float(t[1] - t[0]); m = len(g)
    A = np.abs(np.fft.rfft(g * np.hanning(m), n=64 * m))
    fr = np.fft.rfftfreq(64 * m, dt)
    if A.max() <= 0:
        return dict(n_bins=int(b.sum()), beat_hz=None, band_power_db=round(pw, 2))
    A = A / A.max()
    sel = (fr >= 40) & (fr <= 400)
    i0 = int(np.where(sel)[0][0]); i = int(np.argmax(A[sel])) + i0
    y0, y1, y2 = A[i - 1], A[i], A[i + 1]
    den = y0 - 2 * y1 + y2
    pk = fr[i] + (0.5 * (y0 - y2) / den if den else 0.0) * (fr[1] - fr[0])
    return dict(n_bins=int(b.sum()), beat_hz=round(float(pk), 2), band_power_db=round(pw, 2))


def audit_instrument() -> dict:
    t = np.arange(N) / PRF
    fr = np.fft.fftshift(np.fft.fftfreq(N, 1 / PRF))
    w = np.hanning(N)
    tests, rows = {
        "constant (no modulation at all)": np.ones(N, complex),
        "pure AM at f_flash, depth 0.3": (1 + 0.3 * np.cos(2 * np.pi * FFL * t)).astype(complex),
        "pure AM at f_flash, depth 1.0": (1 + 1.0 * np.cos(2 * np.pi * FFL * t)).astype(complex),
        "AM 1x+2x (0.5, 0.3)": (1 + .5 * np.cos(2 * np.pi * FFL * t)
                                + .3 * np.cos(4 * np.pi * FFL * t)).astype(complex),
        "AM + real 900 Hz Doppler line": (1 + 0.3 * np.cos(2 * np.pi * FFL * t)
                                          + 0.2 * np.exp(2j * np.pi * 900 * t)).astype(complex),
    }, {}
    inb = (np.abs(fr) >= LO) & (np.abs(fr) <= HI)
    for k, v in tests.items():
        r = band_metrics(v, LO, HI)
        P = np.abs(np.fft.fftshift(np.fft.fft(v * w))) ** 2
        rows[k] = dict(reported_beat_hz=r["beat_hz"], reported_band_power_db=r["band_power_db"],
                       true_energy_in_band_db=round(float(10 * np.log10(P[inb].sum() / P.sum())), 1))
    return dict(
        nperseg=NPER, bin_hz=round(PRF / NPER, 1),
        hann_mainlobe_halfwidth_hz=round(2 * PRF / NPER, 1),
        band_lo_hz=round(LO, 1), band_hi_hz=round(HI, 1),
        band_lo_in_bins=round(LO / (PRF / NPER), 3),
        what_it_measures=(
            "band_metrics is NOT a spectral line. It (1) makes a 70-sample Hann STFT, "
            "(2) sums S^2 over the band bins to get a band-energy-vs-time envelope g(t), "
            "(3) FFTs g(t) and takes an UNCONSTRAINED argmax over 40-400 Hz. "
            "So beat_hz is the ENVELOPE beat of whatever the band bins contain."),
        why_it_leaks=(
            "The band's lower edge, 430 Hz, is only 1.53 bins from DC while a 70-sample Hann "
            "window's main lobe reaches 2.00 bins (563 Hz). The band therefore sits INSIDE the "
            "main lobe / first sidelobes of the strong zero-Doppler body line, and inherits its "
            "amplitude modulation whether or not any Doppler energy exists there."),
        synthetic_tests=rows)


# ═══ B. 신호 분해 ═══════════════════════════════════════════════════════════
def decompose(z) -> dict:
    fr = np.fft.fftshift(np.fft.fftfreq(N, 1 / PRF))
    w = np.hanning(N)
    inb = (np.abs(fr) >= LO) & (np.abs(fr) <= HI)
    comb = np.zeros(N, bool)
    for kk in range(1, 60):
        comb |= np.abs(np.abs(fr) - kk * FFL) <= 12.0
    rows = {}
    for key in ("ours/el+0", "ours/el-15", "ours/el-45", "ours/el-75", "ours/el-90",
                "sionna/el-15", "sionna/el-90", "sionna_p250000000/el-15",
                "sionna_p250000000/el-90"):
        E = np.asarray(z[key], complex)
        A = np.abs(E)
        d = E / E.mean() - 1.0                     # 반송파 기준 상대 변동
        am, pm = d.real, d.imag                    # 동상 = 진폭, 직교 = 위상
        PE = np.abs(np.fft.fftshift(np.fft.fft(E * w))) ** 2
        PA = np.abs(np.fft.fftshift(np.fft.fft((A - A.mean()) * w))) ** 2
        bad = np.abs(fr) < 20
        for kk in range(1, 40):
            bad |= np.abs(np.abs(fr) - kk * FFL) <= 25
        flE, flA = float(np.median(PE[~bad])), float(np.median(PA[~bad]))

        def ln(P, f0, fl):
            m = np.abs(np.abs(fr) - f0) <= 12
            return round(float(10 * np.log10(P[m].max() / fl)), 1)
        pc = float(PE[inb & comb].sum()); pn = float(PE[inb & ~comb].sum())
        rows[key] = dict(
            level_db=round(float(20 * np.log10(A.mean())), 2),
            ac_over_dc_db=round(float(10 * np.log10(np.mean(np.abs(d) ** 2))), 2),
            am_rms=round(float(am.std()), 5),
            pm_rms_deg=round(float(np.degrees(pm.std())), 2),
            phase_dev_p95_deg=round(float(np.degrees(np.percentile(np.abs(pm), 95))), 2),
            pm_over_am_db=round(float(20 * np.log10(pm.std() / (am.std() + 1e-300))), 2),
            harmonics_over_floor_db={
                f"{k}x": dict(E=ln(PE, k * FFL, flE), absE=ln(PA, k * FFL, flA))
                for k in (1, 2, 3, 4)},
            band_430_1229={
                "share_of_total_power_db": round(float(10 * np.log10(PE[inb].sum() / PE.sum())), 2),
                "peak_line_db_rel_carrier": round(float(10 * np.log10(PE[inb].max() / PE.max())), 1),
                "sum_db_rel_carrier": round(float(10 * np.log10(PE[inb].sum() / PE.max())), 1),
                "peak_over_floor_db": round(float(10 * np.log10(PE[inb].max() / flE)), 1),
                "on_comb_share_db": round(float(10 * np.log10(pc / (pc + pn))), 2)},
        )
        # 고정대역 전력의 «누설 몫» — |f|<300 Hz 로 자른 신호와 비교
        F = np.fft.fft(E); fq = np.fft.fftfreq(N, 1 / PRF)
        F2 = F.copy(); F2[np.abs(fq) > 300.0] = 0
        p_all = band_metrics(E, LO, HI)["band_power_db"]
        p_lp = band_metrics(np.fft.ifft(F2), LO, HI)["band_power_db"]
        rows[key]["fixed_band_power_db"] = p_all
        rows[key]["fixed_band_leakage_only_db"] = p_lp
        rows[key]["fixed_band_true_over_leakage_db"] = round(p_all - p_lp, 2)
    return rows


# ═══ C·D. 순수 기하 대리모형 ════════════════════════════════════════════════
def _facets(v, f):
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    n = np.cross(b - a, c - a)
    ar2 = np.linalg.norm(n, axis=1)
    return n / (ar2[:, None] + 1e-300), 0.5 * ar2, (a + b + c) / 3.0


def geometry(z) -> dict:
    from articulated_fast import FastPoser, rotor_phases
    from drones import DRONES
    fp = FastPoser(DRONES[TJ.get("drone", "matrice4e")])
    ph = rotor_phases(np.arange(N) / PRF, RPMS, fp.dirs)
    f = np.asarray(fp.f); g = np.asarray(fp.g)
    isp = g == "prop"
    c0 = 0.5 * (fp.v.min(0) + fp.v.max(0))
    u90 = np.array([0.0, 0.0, -1.0])
    RS = [10.0, 20.0, 50.0, 100.0, 300.0, 1000.0]
    NEAR = [-90.0, -89.5, -89.0, -88.0, -85.0, -80.0, -75.0]
    A_all = np.zeros(N); A_pr = np.zeros(N)
    Ssph = {R: np.zeros(N, complex) for R in RS}
    Spl = {e: np.zeros(N, complex) for e in NEAR}
    Sprop = np.zeros(N, complex); Sbody = np.zeros(N, complex)
    UN = {e: np.array([np.cos(np.radians(e)), 0.0, np.sin(np.radians(e))]) for e in NEAR}
    t0 = time.time()
    for i in range(N):
        v = fp.pose(ph[i]).v
        nn, ar, cen = _facets(v, f)
        w = np.maximum(nn @ u90, 0.0) * ar
        A_all[i] = w.sum(); A_pr[i] = w[isp].sum()
        for R in RS:
            d = np.linalg.norm(cen - (c0 + R * u90), axis=1)
            q = w * np.exp(-1j * 2 * K * d)
            Ssph[R][i] = q.sum()
            if R == 10.0:
                Sprop[i] = q[isp].sum(); Sbody[i] = q[~isp].sum()
        for e in NEAR:                                   # 평면파 = 원거리장
            uu = UN[e]
            ww = np.maximum(nn @ uu, 0.0) * ar
            Spl[e][i] = (ww * np.exp(-1j * 2 * K * (cen @ uu))).sum()
        if i and i % 1024 == 0:
            print(f"   geometry {i}/{N}  {time.time()-t0:.0f}s", flush=True)

    def acdc(x):
        x = np.asarray(x, complex)
        return round(float(10 * np.log10(np.mean(np.abs(x / x.mean() - 1.0) ** 2) + 1e-300)), 2)

    E90 = np.asarray(z["ours/el-90"], complex)
    dr = E90 / E90.mean() - 1.0
    dp = Ssph[10.0] / Ssph[10.0].mean() - 1.0
    fq = np.fft.fftfreq(N, 1 / PRF)
    comb = np.zeros(N, bool)
    for kk in range(1, 60):
        comb |= np.abs(np.abs(fq) - kk * FFL) <= 12.0
    Fr, Fp = np.fft.fft(dr), np.fft.fft(dp)
    split = {}
    for nm, msk in (("comb", comb), ("off_comb", ~comb)):
        a = np.fft.ifft(np.where(msk, Fr, 0)); b = np.fft.ifft(np.where(msk, Fp, 0))
        split[nm] = dict(
            share_of_measured_ac_db=round(float(10 * np.log10(
                np.mean(np.abs(a) ** 2) / np.mean(np.abs(dr) ** 2))), 2),
            corr_with_proxy=round(float(np.abs(np.vdot(a, b)) /
                                        (np.linalg.norm(a) * np.linalg.norm(b) + 1e-300)), 4))
    # 앙각별 투영면적·대리레벨
    sub = np.arange(0, N, 16)
    lvl, area = {}, {}
    for e in (0, -15, -30, -45, -60, -75, -90):
        uu = np.array([np.cos(np.radians(e)), 0.0, np.sin(np.radians(e))])
        tx = c0 + RANGE_M * uu
        vals = []
        for i in sub:
            nn, ar, cen = _facets(fp.pose(ph[int(i)]).v, f)
            ww = np.maximum(nn @ uu, 0.0) * ar
            if i == sub[0]:
                area[str(e)] = round(float(ww.sum()), 6)
            vals.append(abs((ww * np.exp(-1j * 2 * K *
                                         np.linalg.norm(cen - tx, axis=1))).sum()))
        lvl[str(e)] = round(float(20 * np.log10(np.mean(vals))), 2)
    return dict(
        note=("flat-facet PO proxy: no materials, no occlusion, no multibounce, no lambda/12 grid. "
              "Absolute levels are NOT comparable to the SBR ledger; the point is the MECHANISM."),
        nadir_projected_area_ac_over_dc_db=acdc(A_all.astype(complex)),
        nadir_projected_area_props_ac_over_dc_db=acdc(A_pr.astype(complex)),
        nadir_plane_wave_ac_over_dc_db=acdc(Spl[-90.0]),
        nadir_spherical_10m_ac_over_dc_db=acdc(Ssph[10.0]),
        nadir_spherical_10m_props_only_db=acdc(Sprop),
        nadir_spherical_10m_body_only_db=acdc(Sbody),
        measured_ours_el90_ac_over_dc_db=acdc(E90),
        range_sweep_nadir={f"{int(R)}m": acdc(Ssph[R]) for R in RS},
        offnadir_farfield={f"{e:+.1f}": dict(
            off_nadir_deg=round(90 + e, 2), ac_over_dc_db=acdc(Spl[e]))
            for e in NEAR},
        proxy_vs_measured_split=split,
        projected_area_m2_vs_el=area,
        proxy_level_db_vs_el=lvl)


# ═══ 그림 ═══════════════════════════════════════════════════════════════════
def figure(z, aud, dec, geo) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fr = np.fft.fftshift(np.fft.fftfreq(N, 1 / PRF))
    w = np.hanning(N)
    fig, ax = plt.subplots(2, 2, figsize=(13.6, 9.0))
    fig.suptitle("Is there still a blade flash at nadir (el = -90 deg)?  "
                 "Matrice 4E, 3.5 GHz, 10 m, PRF 19.7 kHz",
                 fontsize=13, fontweight="bold")

    # (a) 스펙트럼
    a = ax[0, 0]
    inb = (np.abs(fr) >= LO) & (np.abs(fr) <= HI)
    for key, col, lab, lw, ty in (("ours/el-15", "tab:blue", "el = -15 deg (deck case)", 0.9, -21),
                                  ("ours/el-90", "tab:red", "el = -90 deg (nadir)", 1.1, -35)):
        E = np.asarray(z[key], complex)
        P = np.abs(np.fft.fftshift(np.fft.fft(E * w))) ** 2
        Pd = 10 * np.log10(P / P.max())
        a.plot(fr, Pd, col, lw=lw, label=lab, alpha=.9)
        i = int(np.where(inb)[0][np.argmax(P[inb])])
        a.plot([fr[i]], [Pd[i]], "o", color=col, ms=8, mfc="none", mew=1.8)
        a.annotate(f"strongest line inside the band: {Pd[i]:.1f} dB",
                   xy=(fr[i], Pd[i]), xytext=(-1460, ty), fontsize=8.5, color=col,
                   arrowprops=dict(arrowstyle="->", color=col, lw=1.1,
                                   connectionstyle="arc3,rad=-0.15"))
    for s in (+1, -1):
        a.axvspan(s * LO, s * HI, color="0.72", alpha=.4, zorder=0)
    a.text(0.5 * (LO + HI), -6, "deck fixed band\n430-1229 Hz", ha="center", va="top",
           fontsize=8, color="0.2")
    for kk in range(1, 11):
        for s in (+1, -1):
            a.axvline(s * kk * FFL, color="k", ls=":", lw=.5, alpha=.35)
    a.set_xlim(-1500, 1500); a.set_ylim(-100, 6)
    a.set_xlabel("Doppler [Hz]"); a.set_ylabel("power [dB rel. carrier]")
    a.set_title("(a) Echo spectrum: at nadir the tip-Doppler shoulder is gone.\n"
                "Only a weak comb at k x 126.67 Hz survives, 30.6 dB lower", fontsize=10)
    a.legend(fontsize=8, loc="lower right", framealpha=.95); a.grid(alpha=.25)

    # (b) 잣대 누설
    b = ax[0, 1]
    m = 4096
    W = np.abs(np.fft.rfft(np.hanning(NPER), n=m)) ** 2
    fw = np.fft.rfftfreq(m, 1 / PRF)
    b.plot(fw, 10 * np.log10(W / W.max()), "k", lw=1.2, label=f"Hann window, {NPER} samples")
    b.axvspan(LO, HI, color="0.75", alpha=.45, zorder=0)
    b.axvline(LO, color="tab:red", lw=1.2)
    b.annotate(f"band edge {LO:.0f} Hz sits at\n1.53 bins - INSIDE the\n2.00-bin main lobe",
               xy=(LO, -18), xytext=(700, -12), fontsize=8, color="tab:red",
               arrowprops=dict(arrowstyle="->", color="tab:red", lw=1))
    b.set_xlim(0, 2000); b.set_ylim(-70, 3)
    b.set_xlabel("offset from the zero-Doppler body line [Hz]")
    b.set_ylabel("window leakage [dB]")
    b.set_title("(b) Why the fixed-band metric lies: leakage of the body line.\n"
                "A pure-AM signal with ZERO energy in the band still reports "
                "beat = 126.67 Hz", fontsize=10)
    b.legend(fontsize=8); b.grid(alpha=.25)

    # (c) 앙각별 변조 깊이
    c = ax[1, 0]
    FLOOR = -66.0
    els = [0, -15, -45, -75, -90]
    ac = [dec[f"ours/el{e:+d}"]["ac_over_dc_db"] for e in els]
    c.plot(els, ac, "o-", color="tab:red", lw=2.0, ms=8,
           label="measured SBR kernel, near field (10 m)")
    ne = sorted((v["off_nadir_deg"], v["ac_over_dc_db"])
                for v in geo["offnadir_farfield"].values())
    xs = [-90 + o for o, _ in ne]
    ys = [max(y, FLOOR) for _, y in ne]
    c.plot(xs[1:], ys[1:], "s--", color="tab:green", lw=1.5, ms=6,
           label="geometry proxy, far field (plane wave)")
    c.plot([-90], [FLOOR], "v", color="tab:green", ms=13, clip_on=False)
    c.annotate("EXACTLY zero at nadir in the far field\n"
               "(-305 dB = float64 round-off).\n"
               "But the null is narrow: -44 dB at 1 deg off,\n"
               "-12 dB at 5 deg off.",
               xy=(-89.6, FLOOR + 1), xytext=(-63, -34), fontsize=8.5, color="tab:green",
               ha="left", arrowprops=dict(arrowstyle="->", color="tab:green", lw=1.2,
                                          connectionstyle="arc3,rad=0.2"))
    c.set_xlabel("elevation [deg]   (-90 = observer straight below, looking up)")
    c.set_ylabel("modulated power / steady power [dB]")
    c.set_ylim(FLOOR, 6); c.set_xlim(-93, 4)
    c.set_title("(c) The flash collapses at nadir: -38.3 dB at 10 m,\n"
                "and exactly zero once the wavefront is flat", fontsize=10)
    c.legend(fontsize=8, loc="lower right", framealpha=.95); c.grid(alpha=.25)

    # (d) 거리 의존
    d = ax[1, 1]
    RS = sorted(float(k[:-1]) for k in geo["range_sweep_nadir"])
    yy = [geo["range_sweep_nadir"][f"{int(R)}m"] for R in RS]
    d.semilogx(RS, yy, "o-", color="tab:purple", lw=1.8, ms=7,
               label="geometry proxy, nadir")
    d.semilogx([10], [geo["measured_ours_el90_ac_over_dc_db"]], "*", color="tab:red", ms=18,
               label="measured SBR kernel at 10 m")
    ref = yy[0] - 40 * np.log10(np.array(RS) / RS[0])
    d.semilogx(RS, ref, "k:", lw=1.2, label="1/r^4 law (2-blade cancellation)")
    d.set_xlabel("range [m]"); d.set_ylabel("modulated power / steady power [dB]")
    d.set_title("(d) The nadir flash is a NEAR-FIELD leftover.\n"
                "It dies as 1/r^4: -79 dB at 100 m, -119 dB at 1 km", fontsize=10)
    d.legend(fontsize=8); d.grid(alpha=.25, which="both")

    fig.tight_layout(rect=(0, 0, 1, 0.965))
    fig.savefig(OUT_P, dpi=150)
    print(f"✅ {OUT_P}")


def main() -> None:
    if os.path.exists(OUT_J) or os.path.exists(OUT_P):
        print("⚠ 기존 산출물이 있다 — 덮어쓴다(내 소유 파일).")
    z = np.load(SWEEP_N)
    print("A. 잣대 감사 …", flush=True)
    aud = audit_instrument()
    print("B. 신호 분해 …", flush=True)
    dec = decompose(z)
    print("C·D. 순수 기하 대리모형 (CPU) …", flush=True)
    geo = geometry(z)
    doc = {
        "_meta": {
            "generator": "benchmark/verify_nadir_flash.py",
            "question_ko": "«앙각 −90°에서 도플러는 0 인데 블레이드 플래시는 남는다» 가 참인가",
            "inputs": {
                "series": "outputs/elevation_sweep_md.npz  (keys ours|sionna|sionna_p250000000 / el±NN)",
                "claim_source": ("outputs/elevation_sweep_md.json  rows[engine=ours, el_deg=-90]"
                                 ".fixed.beat_hz = 126.78 Hz"),
                "kinematics": "report07_three_engines.json _meta (prf_hz, n, f_flash_hz, f_tip_hz, rpm_per_rotor)"},
            "gpu_ko": "GPU 를 쓰지 않았다. sbr_field 호출 없음 — 기하 대리모형만 CPU 로 돌렸다.",
            "verdict_ko": (
                "**부분적으로 참, 그러나 인용된 근거는 잣대 인공물이다.** "
                "(1) 근거였던 fixed 대역 beat_hz 126.78 Hz 는 누설이다 — el−90 에서 그 대역 전력은 "
                "|f|<300 Hz 로 자른 신호와 0.01 dB 차이다. (2) 그래도 126.67 Hz 빗살 자체는 실재한다 "
                "(잡음바닥 위 +39.9 dB). (3) 그러나 그 잔여는 진폭보다 **위상**이 크다(1x 에서 +15.1 dB) — "
                "즉 «도플러가 사라지고 진폭만 남았다» 가 아니라 **아주 작은 도플러가 남았다**. "
                "(4) 기전은 근접장 파면 곡률이다 — 원거리장 평면파에서는 나딧 변조가 **정확히 0**이고"
                "(−305 dB), 거리에 1/r⁴ 로 죽는다."),
        },
        "A_instrument_audit": aud,
        "B_decomposition": dec,
        "C_D_geometry": geo,
        # ⭐탐지에 직결되는 유도량 — «블레이드 선» 하나가 들고 있는 절대 전력.
        #   level_db 는 이미 전력 dB(20log10|E|)이므로 그냥 더한다.
        "E_blade_line_power": {
            "note_ko": ("blade_line_db = level_db + ac_over_dc_db. 즉 «표적이 얼마나 밝은가» 와 "
                        "«그중 얼마가 흔들리는가» 를 곱한 것. 마이크로도플러 탐지는 이 값에 걸린다. "
                        "⚠ 10 m 판이며, 나딧 값은 근접장 곡률이 만든 것이라 거리를 늘리면 "
                        "1/r⁴ 로 사라진다(다른 앙각은 그렇지 않다)."),
            "rows": {k: dict(level_db=v["level_db"], ac_over_dc_db=v["ac_over_dc_db"],
                             blade_line_db=round(v["level_db"] + v["ac_over_dc_db"], 2))
                     for k, v in dec.items() if k.startswith("ours")},
        },
    }
    json.dump(doc, open(OUT_J, "w"), ensure_ascii=False, indent=1)
    print(f"✅ {OUT_J}")
    figure(z, aud, dec, geo)


if __name__ == "__main__":
    main()
