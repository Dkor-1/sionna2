# -*- coding: utf-8 -*-
"""
viz_radar.py — (report2) 레이더/RCS/파형 비교 시각화 (matplotlib)
==================================================================
생성물 (outputs/figures/, report2_ 접두어)
  report2_setup.png        : 모노스태틱 구성 + 원거리장 도식
  report2_rcs_polar.png    : 드론 5종 RCS(방위각) 극좌표 + RCS(주파수)
  report2_rcs_bands.png    : LTE/5G/WiFi 반송파에서의 5종 RCS 비교(막대)
  report2_wave_spectra.png : 세 파형의 스펙트럼(점유대역) + 시간파형
  report2_range_profiles.png : 같은 표적, 세 파형 거리프로파일(분해능 비교)
  report2_summary.png      : 표준별 요약표 + RCS 추정 비교
"""
from __future__ import annotations
import os
import numpy as np

import vizstyle
vizstyle.use_korean()
import matplotlib.pyplot as plt

from drones import DRONES
from rcs_po import drone_rcs_pattern, drone_rcs_pattern_bw, angular_smooth, dbsm
from waveforms import all_waveforms, always_on_waveforms
from radar_process import range_profile, mainlobe_width_m, sphere_calib, estimate_rcs_dbsm
from radar_scene import ANT_POS, TGT_POS, farfield_distance, target_extent  # sionna 지연 import 라 가벼움

FIG = os.path.join(os.path.dirname(__file__), "..", "outputs", "figures")
_COL = {"mini5pro": "#1565c0", "mavic4pro": "#2e7d32", "matrice4e": "#ef6c00",
        "s1000plus": "#000000", "phantom4": "#c62828"}
_NAME = {k: DRONES[k].name.split("  ")[0].replace("DJI ", "") for k in DRONES}


def fig_setup(outdir=FIG):
    R = abs(TGT_POS[0] - ANT_POS[0])
    fig, ax = plt.subplots(figsize=(12, 4.6), constrained_layout=True)
    ax.add_patch(plt.Rectangle((0, 0), 30, 11, fill=False, ec="0.5", lw=1.5))
    ax.text(15, 11.4, "Semi-anechoic chamber cross-section (30 m × 11 m)  ·  walls + ceiling = RF absorber, floor = reflective",
            ha="center", fontsize=10, color="0.4")
    # 안테나
    ax.plot(ANT_POS[0], ANT_POS[2], "^", ms=16, color="#c62828")
    ax.text(ANT_POS[0], ANT_POS[2] - 1.1, "Monostatic\nantenna (TX≈RX)", ha="center", fontsize=9, color="#c62828")
    # 표적
    ax.plot(TGT_POS[0], TGT_POS[2], "o", ms=12, color="k")
    ax.text(TGT_POS[0], TGT_POS[2] + 0.8, "Target drone\n(quiet zone)", ha="center", fontsize=9)
    # 빔/왕복
    ax.annotate("", xy=TGT_POS[::2], xytext=ANT_POS[::2],
                arrowprops=dict(arrowstyle="->", color="#1565c0", lw=2))
    ax.annotate("", xy=ANT_POS[::2], xytext=TGT_POS[::2],
                arrowprops=dict(arrowstyle="->", color="#1565c0", lw=2, ls=":"))
    ax.text((ANT_POS[0]+TGT_POS[0])/2, ANT_POS[2]+0.5, f"R = {R:.0f} m  (round trip 2R/c)",
            ha="center", fontsize=10, color="#1565c0")
    # 원거리장 표 (λ 는 NanumGothic 에 글리프가 없어 □ 로 깨짐 → mathtext 로 렌더)
    txt = "Far-field " + r"$2D^2/\lambda$" + " check @3.5GHz (D = max horizontal span incl. props):  "
    for k in DRONES:
        D = target_extent(k); rff = farfield_distance(D, 3.5e9)
        ok = "○" if rff <= R else "×"        # (✓/✗ 는 NanumGothic 에 글리프가 없어 □ 로 깨짐)
        txt += f"{_NAME[k]} {rff:.0f}m{ok}  "
    ax.text(15, -1.6, txt, ha="center", fontsize=8.5, color="#444")
    ax.set_xlim(-2, 32); ax.set_ylim(-2.5, 13); ax.axis("off")
    ax.set_title("Monostatic setup — antenna ↔ target (quiet zone)", fontsize=13, fontweight="bold")
    fn = os.path.join(outdir, "report2_setup.png"); fig.savefig(fn, dpi=130); plt.close(fig)
    print("[radar]", os.path.relpath(fn)); return fn


RFLOOR_DBSM = -45.0    # 폴라 RCS 반경축 바닥(대역평균 후엔 최저 ≈−48 dBsm 라 거의 닿지 않는다)
BW_HZ = 100e6          # 방위 패턴을 평균낼 신호 대역(5G n78 100MHz) — "레이더가 실제로 보는 값"
SMOOTH_DEG = 3.0       # 방위 스무딩 창(안테나 빔폭·표적 요 지터·유한 샘플링이 하는 평활)


def fig_rcs_polar(outdir=FIG, fc=3.5e9):
    az = np.arange(0, 360, 1.0)
    fig = plt.figure(figsize=(13, 5.8), constrained_layout=True)
    fig.suptitle("Drone RCS — SBR (rays + PO integral)", fontsize=14, fontweight="bold")
    fig.supxlabel("Engine: rcs_po.drone_rcs_pattern(engine='sbr') -- Mitsuba rays find the first-hit "
                  "surface, PO integrates it. Occlusion included.",
                  fontsize=8.5, color="0.45")
    axp = fig.add_subplot(1, 2, 1, projection="polar")
    for k in DRONES:
        # **대역폭 평균**(5G 100MHz)으로 그린다 — 단일주파수 코히런트 PO 의 깊은 널은
        # 이산화에 따라 위치가 춤추는 수치 아티팩트이고(λ/7↔λ/12 에서 최저점 330°→127°),
        # 유한 대역폭을 가진 실제 레이더는 그 널을 보지 못한다(최저값 +20 dB 상승). rcs_po 참조.
        sig, _ = drone_rcs_pattern_bw(k, fc, BW_HZ, az)
        sig = angular_smooth(sig, SMOOTH_DEG, float(az[1] - az[0]))
        axp.plot(np.radians(az), np.maximum(dbsm(sig), RFLOOR_DBSM),
                 color=_COL[k], lw=1.3, label=_NAME[k])
    axp.set_title(f"(a) RCS vs azimuth @ {fc/1e9:.1f} GHz\n"
                  f"(as a radar sees it: {BW_HZ/1e6:.0f} MHz band, {SMOOTH_DEG:.0f}° window)",
                  fontsize=11)
    axp.set_theta_zero_location("N"); axp.set_theta_direction(-1)
    axp.set_rlim(RFLOOR_DBSM, None)
    axp.set_rlabel_position(135); axp.legend(loc="upper right", bbox_to_anchor=(1.18, 1.1), fontsize=8)
    # RCS vs frequency
    axf = fig.add_subplot(1, 2, 2)
    freqs = np.linspace(1.0e9, 6.0e9, 26)
    azc = np.arange(0, 360, 3.0)
    for k in DRONES:
        mean_rcs = []
        for f in freqs:
            sig, _ = drone_rcs_pattern(k, f, azc)
            mean_rcs.append(dbsm(sig.mean()))
        axf.plot(freqs/1e9, mean_rcs, color=_COL[k], lw=1.8, marker="o", ms=3, label=_NAME[k])
    for fb, lab in [(1.84, "LTE"), (3.5, "5G"), (5.21, "WiFi")]:
        axf.axvline(fb, color="0.6", ls="--", lw=1); axf.text(fb, axf.get_ylim()[1], lab, fontsize=8, ha="center", va="bottom")
    axf.set_xlabel("Frequency [GHz]"); axf.set_ylabel("Azimuth-avg RCS [dBsm]")
    axf.set_title("(b) RCS vs frequency", fontsize=11); axf.grid(alpha=0.3); axf.legend(fontsize=8)
    fn = os.path.join(outdir, "report2_rcs_polar.png")
    fig.savefig(fn, dpi=130, bbox_inches="tight"); plt.close(fig)
    print("[radar]", os.path.relpath(fn)); return fn


def fig_rcs_bands(outdir=FIG):
    bands = [("LTE 1.8GHz", 1.84e9), ("5G 3.5GHz", 3.5e9), ("WiFi 5.2GHz", 5.21e9)]
    az = np.arange(0, 360, 2.0)
    keys = list(DRONES.keys())
    data = np.zeros((len(keys), len(bands)))
    for i, k in enumerate(keys):
        for j, (_, f) in enumerate(bands):
            sig, _ = drone_rcs_pattern(k, f, az); data[i, j] = dbsm(sig.mean())
    fig, ax = plt.subplots(figsize=(11, 5.2), constrained_layout=True)
    x = np.arange(len(keys)); w = 0.26
    for j, (lab, _) in enumerate(bands):
        ax.bar(x + (j-1)*w, data[:, j], w, label=lab)
    ax.set_xticks(x); ax.set_xticklabels([_NAME[k] for k in keys])
    ax.set_ylabel("Azimuth-avg RCS [dBsm]")
    ax.set_title("RCS per standard carrier", fontsize=13, fontweight="bold")
    ax.legend(); ax.grid(axis="y", alpha=0.3)
    for i in range(len(keys)):
        for j in range(len(bands)):
            ax.text(x[i]+(j-1)*w, data[i, j]+0.3, f"{data[i,j]:.0f}", ha="center", fontsize=7.5)
    fig.supxlabel("Engine: SBR (Mitsuba rays + PO integral, occlusion included).",
                  fontsize=8.5, color="0.45")
    fn = os.path.join(outdir, "report2_rcs_bands.png")
    fig.savefig(fn, dpi=130, bbox_inches="tight"); plt.close(fig)
    print("[radar]", os.path.relpath(fn)); return fn


def _psd_db(x, fs):
    """정규화 PSD [dB] 와 baseband 주파수축 [MHz]."""
    f = np.fft.fftshift(np.fft.fftfreq(len(x), 1/fs))/1e6
    P = np.fft.fftshift(np.abs(np.fft.fft(x))**2)
    return f, 10*np.log10(P/(P.max()+1e-30) + 1e-12)


def _mf_range_db(ref, fs, rmax=45.0, up=8):
    """기준신호 자기상관(=이상적 점표적의 정합필터 응답)을 '거리[m]' 축으로.
    - np.correlate(O(n²))는 NR 6만 샘플에서 수십 분 → **FFT 상관**(O(n log n)).
    - 거리축 원샘플 간격 c/2fs 는 LTE 에서 4.9 m 나 되어 곡선이 톱니가 된다 →
      상관 스펙트럼을 제로패딩해 시간축을 `up`배 **보간**(대역제한 신호라 정보 왜곡 없음)."""
    n = len(ref)
    nf = 1 << int(np.ceil(np.log2(2 * n)))          # 제로패딩 → 순환상관이 아닌 선형상관
    S = np.abs(np.fft.fft(ref, nf)) ** 2            # 자기상관의 스펙트럼(실수·비음수)
    Su = np.zeros(nf * up, complex)                 # 스펙트럼 가운데를 0 으로 채워 시간축 보간
    Su[:nf // 2] = S[:nf // 2]; Su[-(nf // 2):] = S[nf // 2:]
    r = np.abs(np.fft.ifft(Su))[: n * up]
    r /= r.max() + 1e-30
    rng = np.arange(n * up) / (fs * up) * 299792458.0 / 2.0
    m = rng <= rmax
    return rng[m], 20*np.log10(r[m] + 1e-12)


def fig_wave_spectra(outdir=FIG):
    """상시(always-on) 기준신호가 실제로 점유하는 대역과, 그것이 만드는 정합필터 응답.
    핵심 메시지: 패시브 레이더가 언제나 기댈 수 있는 건 LTE=CRS · 5G=SSB · WiFi=프리앰블뿐이고,
    5G 의 SSB 는 100MHz 채널 한가운데의 7.2MHz 조각이라 거리가 흐릿하다(PRS 는 측위 세션 옵션)."""
    ch = all_waveforms("G3")                      # 채널(풀로드) 스펙트럼 — 배경
    on = always_on_waveforms()                    # 상시 기준신호 — 주인공
    prs = all_waveforms("G2")["nr"]               # 측위 세션이 켜졌을 때의 5G 기준(비교용)
    col = {"wifi": "#1565c0", "lte": "#ef6c00", "nr": "#2e7d32"}
    fig, axes = plt.subplots(2, 3, figsize=(14.4, 6.8), constrained_layout=True)
    fig.suptitle("The always-on reference signal of each standard", fontsize=14, fontweight="bold")
    for j, key in enumerate(("wifi", "lte", "nr")):
        wf, wch = on[key], ch[key]
        # (위) 채널 점유대역(회색) 위에 상시 기준신호가 덮는 대역(색)
        f0, P0 = _psd_db(wch.tx, wch.fs_hz)
        f1, P1 = _psd_db(wf.ref, wf.fs_hz)
        ax = axes[0, j]
        ax.plot(f0, P0, lw=0.5, color="0.72", label=f"channel ({wch.bw_hz/1e6:.0f} MHz)")
        ax.plot(f1, P1, lw=0.6, color=col[key], label=f"{wf.ref_name} ({wf.ref_bw_hz/1e6:.0f} MHz)")
        ax.set_title(f"{wf.name} · {wf.carrier_hz/1e9:.2f} GHz", fontsize=10.5, fontweight="bold")
        ax.set_xlabel("Baseband frequency [MHz]"); ax.set_ylabel("PSD [dB, self-normalized]")
        ax.set_ylim(-60, 3); ax.grid(alpha=0.3); ax.legend(fontsize=7.6, loc="lower center")
        # (아래) 그 기준신호의 정합필터 응답 → 거리분해능
        ax = axes[1, j]
        rr, pp = _mf_range_db(wf.ref, wf.fs_hz)
        ax.plot(rr, pp, lw=1.5, color=col[key],
                label=f"{wf.ref_name} → {wf.range_resolution_m:.1f} m")
        if key == "nr":                            # 5G 만: PRS 가 켜지면 어떻게 되는지 점선으로
            rr2, pp2 = _mf_range_db(prs.ref, prs.fs_hz)
            ax.plot(rr2, pp2, lw=1.3, ls="--", color="#7b1fa2",
                    label=f"NR-PRS → {prs.range_resolution_m:.1f} m")
        ax.axhline(-3, color="0.6", ls=":", lw=1)
        ax.set_xlim(0, 45); ax.set_ylim(-40, 3)
        ax.set_xlabel("Range [m]"); ax.set_ylabel("Matched-filter output [dB]")
        ax.set_title("Range response", fontsize=9.5)
        ax.grid(alpha=0.3); ax.legend(fontsize=8, loc="upper right")
    fig.text(0.5, -0.012,
             "LTE has an always-on wideband pilot (CRS). 5G does not — an idle gNB emits only SSB. "
             "PRS is a positioning-session option.",
             ha="center", fontsize=8.5, color="0.45")
    fn = os.path.join(outdir, "report2_wave_spectra.png"); fig.savefig(fn, dpi=130, bbox_inches="tight"); plt.close(fig)
    print("[radar]", os.path.relpath(fn)); return fn


def fig_range_profiles(outdir=FIG, target="mavic4pro", R=10.0, snr_db=20.0):
    """같은 표적을 세 표준의 **상시 기준신호**로 재본다(+5G 는 PRS 가 켜졌을 때를 점선으로).
    '5G 가 제일 날카롭다'는 PRS 를 가정할 때만 참이고, 유휴 셀에선 5G 가 가장 거칠다."""
    wfs = always_on_waveforms()
    prs = all_waveforms("G2")["nr"]
    fig, ax = plt.subplots(figsize=(12.4, 5.6), constrained_layout=True)
    col = {"wifi": "#1565c0", "lte": "#ef6c00", "nr": "#2e7d32"}
    def _trace(wf):
        """패시브 처리(기준신호만 아는 상관) + 거리축 보간(up=8).
        보간 없이 원격자(c/2fs: LTE 4.9 m)에서 재면 -3dB 폭이 격자에 양자화돼 이론과 어긋난다."""
        sig, _ = drone_rcs_pattern(target, wf.carrier_hz, np.array([0.0])); sig = float(sig[0])
        rm, p, _, _ = range_profile(wf, R, sig, snr_db=snr_db, passive=True, up=8,
                                    rng=np.random.default_rng(7))
        return rm, 20*np.log10(p/p.max()+1e-12), mainlobe_width_m(rm, p)

    for key, wf in wfs.items():
        rm, pdb, res = _trace(wf)
        ax.plot(rm, pdb, color=col[key], lw=1.7,
                label=f"{wf.ref_name} · {wf.ref_bw_hz/1e6:.0f} MHz  →  {wf.range_resolution_m:.1f} m")
    rm, pdb, _ = _trace(prs)
    ax.plot(rm, pdb, color="#7b1fa2", lw=1.4, ls="--",
            label=f"NR-PRS · {prs.ref_bw_hz/1e6:.0f} MHz  →  {prs.range_resolution_m:.1f} m   (PRS session only)")
    ax.axvline(R, color="k", ls="--", lw=1, label=f"True range {R:.0f} m")
    ax.set_xlim(0, 2*R+5); ax.set_ylim(-40, 2)
    ax.set_xlabel("Range [m]"); ax.set_ylabel("Matched-filter output [dB]")
    ax.set_title(f"Range profile with each always-on reference — {_NAME[target]}",
                 fontsize=13, fontweight="bold")
    fig.text(0.5, -0.02, "An idle 5G cell is the blurriest (SSB, 21 m); it only sharpens to 1.5 m if PRS is switched on.",
             ha="center", fontsize=8.5, color="0.45")
    ax.legend(fontsize=9, loc="upper right"); ax.grid(alpha=0.3)
    fn = os.path.join(outdir, "report2_range_profiles.png"); fig.savefig(fn, dpi=130, bbox_inches="tight"); plt.close(fig)
    print("[radar]", os.path.relpath(fn)); return fn


def fig_summary(outdir=FIG, target="mavic4pro", R=10.0):
    """요약표 — 상시 기준신호 3종 + '5G 에 PRS 가 켜졌을 때'를 마지막 행에 따로."""
    rows, rowkind = [], []
    entries = [(k, wf, True) for k, wf in always_on_waveforms().items()]
    entries.append(("nr_prs", all_waveforms("G2")["nr"], False))
    for key, wf, always in entries:
        sig, _ = drone_rcs_pattern(target, wf.carrier_hz, np.array([0.0])); sig = float(sig[0])
        rng_m, prof, pkr, pkv = range_profile(wf, R, sig, snr_db=20.0, passive=True, up=8,
                                              rng=np.random.default_rng(7))
        res = mainlobe_width_m(rng_m, prof)
        cpk, csig = sphere_calib(wf, R, passive=True, up=8)   # 표적과 동일 처리(안 그러면 보정 상수가 안 상쇄)
        est = estimate_rcs_dbsm(pkv, cpk, csig)
        name = wf.name if always else "5G NR  (PRS session)"
        rows.append([name, f"{wf.carrier_hz/1e9:.2f} GHz", f"{wf.bw_hz/1e6:.0f} MHz",
                     wf.ref_name if always else f"{wf.ref_name} (optional)",
                     f"{wf.ref_bw_hz/1e6:.1f} MHz",
                     f"{wf.range_resolution_m:.2f} m", f"{res:.1f} m",
                     f"{wf.v_unambiguous_ms:.1f} m/s", f"{dbsm(sig):.1f}", f"{est:.1f}"])
        rowkind.append(always)
    fig, ax = plt.subplots(figsize=(15, 3.4), constrained_layout=True); ax.axis("off")
    cols = ["Standard", "Carrier", "Channel BW", "Reference signal", "Reference BW",
            "Range res.\nc/2B (theory)", "Measured\n-3 dB width", "Max speed\n" + r"PRF$\cdot\lambda$/4",
            "True RCS\n[dBsm]", "Estimated RCS\n[dBsm]"]
    t = ax.table(cellText=rows, colLabels=cols, loc="center", cellLoc="center")
    t.auto_set_font_size(False); t.set_fontsize(10.0); t.scale(1, 2.0)
    for c in range(len(cols)):
        t[0, c].set_facecolor("#1565c0"); t[0, c].set_text_props(color="white", fontweight="bold")
    for i, always in enumerate(rowkind, start=1):          # PRS 행은 '옵션'이라 흐리게
        if not always:
            for c in range(len(cols)):
                t[i, c].set_facecolor("#f3e5f5"); t[i, c].set_text_props(color="#4a148c")
    ax.set_title(f"Always-on references vs the PRS option — {_NAME[target]} @ R = {R:.0f} m",
                 fontsize=13, fontweight="bold", pad=12)
    fn = os.path.join(outdir, "report2_summary.png"); fig.savefig(fn, dpi=130); plt.close(fig)
    print("[radar]", os.path.relpath(fn)); return fn


def fig_rcs_materials(outdir=FIG, fc=3.5e9, el=15.0):
    """재질 가중의 효과 — **SBR 로 측정**(가림 포함). 전부 PEC(고전 PO 가정) vs 재질 |Γ|.

    ⚠ 2026-07-14 엔진 교체: 이 그림은 예전에 **순수 PO**(rcs_from_points, 가림 없음)로 그려서
      같은 리포트의 polar/bands(SBR)와 σ 가 4~5 dB 어긋나 있었다. 이제 셋 다 SBR 이다.

    ⚠ 그리고 **서사가 바뀌었다**: 1-bounce SBR 은 첫 충돌만 채택하므로 반투명 셸을 **투과**해
      내부(배터리·PCB)를 때리는 경로가 없다 — 실측: 그 두 그룹의 광선 적중 수 = **0**.
      그래서 여기서 재질 가중이 하는 일은 순수하게 **외피의 |Γ| 를 낮추는 것**이다
      (플라스틱 0.28 · 프로펠러 0.25 · 카본 0.90 · 금속 1.0). 내부 산란체의 기여는
      viz_report2.fig_po_vs_sbr 의 분해 패널에서 따로 정량화한다(+1.74 dB, PO 기준)."""
    from drones import build_drone, DRONE_GROUP_MAT
    from rcs_sbr import rcs_sbr_batch
    az = np.arange(0, 360, 2.0)
    g_mat = {g: mat for g, (mat, _) in DRONE_GROUP_MAT.items()}
    g_pec = {g: 1.0 for g in DRONE_GROUP_MAT}            # 전부 PEC = 고전 PO 가정

    fig, axes = plt.subplots(1, 2, figsize=(13.6, 5.4), constrained_layout=True,
                             gridspec_kw=dict(width_ratios=[1.15, 1.0]))
    # (a) mavic4pro 패턴
    spec = DRONES["mavic4pro"]; mesh = build_drone(spec)
    s_old = rcs_sbr_batch(mesh, g_pec, fc, az_deg=az, el_deg=el, cache_key=("mavic4pro", "pec"))
    s_new = rcs_sbr_batch(mesh, g_mat, fc, az_deg=az, el_deg=el, cache_key=("mavic4pro", "mat"))
    axes[0].plot(az, dbsm(s_old), color="0.55", lw=1.4, label="all-PEC (classic PO assumption)")
    axes[0].plot(az, dbsm(s_new), color="#2e7d32", lw=1.8,
                 label=r"material-weighted $|\Gamma|$ (plastic 0.28, prop 0.25, carbon 0.90)")
    axes[0].axhline(dbsm(s_old.mean()), color="0.55", ls="--", lw=1)
    axes[0].axhline(dbsm(s_new.mean()), color="#2e7d32", ls="--", lw=1)
    axes[0].set_xlim(0, 360); axes[0].set_xticks([0, 90, 180, 270, 360])
    axes[0].set_xlabel("Azimuth [deg]"); axes[0].set_ylabel("RCS [dBsm]")
    axes[0].set_title(f"(a) Mavic 4 Pro azimuth pattern @ {fc/1e9:.1f} GHz, "
                      f"el = {el:.0f}" + r"$^\circ$" + "  (SBR)", fontsize=11)
    axes[0].grid(alpha=0.3); axes[0].legend(fontsize=8.5, loc="lower right")
    # (b) 5종 방위평균 비교
    keys = list(DRONES.keys()); olds, news = [], []
    for k in keys:
        m2 = build_drone(DRONES[k])
        olds.append(dbsm(rcs_sbr_batch(m2, g_pec, fc, az_deg=az, el_deg=el,
                                       cache_key=(k, "pec")).mean()))
        news.append(dbsm(rcs_sbr_batch(m2, g_mat, fc, az_deg=az, el_deg=el,
                                       cache_key=(k, "mat")).mean()))
    x = np.arange(len(keys)); wbar = 0.38
    # S1000+ 의 PEC 값이 ≈−5 dBsm 이라 baseline=0 막대는 높이가 음수 → 바닥을 내려 그린다.
    base = float(np.floor(min(olds + news))) - 3.0
    axes[1].bar(x - wbar/2, np.array(olds) - base, wbar, bottom=base, color="0.6", label="all-PEC")
    axes[1].bar(x + wbar/2, np.array(news) - base, wbar, bottom=base, color="#2e7d32",
                label="material-weighted")
    for xi, (o, n) in enumerate(zip(olds, news)):
        axes[1].text(xi - wbar/2, o + 0.4, f"{o:+.1f}", ha="center", fontsize=7.5, color="0.35")
        axes[1].text(xi + wbar/2, n + 0.4, f"{n-o:+.1f} dB", ha="center", fontsize=8.5)
    axes[1].set_ylim(base, max(olds) + 3.5)
    axes[1].set_xticks(x, [_NAME[k] for k in keys], fontsize=8.5)
    axes[1].set_ylabel("Azimuth-avg RCS [dBsm]")
    axes[1].set_title("(b) Azimuth-mean per drone", fontsize=10.5)
    axes[1].grid(axis="y", alpha=0.3); axes[1].legend(fontsize=9)
    fig.suptitle("A drone is not a lump of metal — material weighting costs 4 to 10 dB",
                 fontsize=13, fontweight="bold")
    fig.supxlabel("Engine: SBR (Mitsuba rays + PO integral, occlusion included) -- same engine as the "
                  "polar and band figures.\n"
                  "1-bounce SBR is opaque: no ray reaches the battery or the PCB through the shell "
                  "(measured: 0 hits), so this is a pure exterior-" + r"$|\Gamma|$" + " effect.",
                  fontsize=8.5, color="0.45")
    fn = os.path.join(outdir, "report2_rcs_materials.png")
    fig.savefig(fn, dpi=130, bbox_inches="tight"); plt.close(fig)
    print("[radar]", os.path.relpath(fn)); return fn


def fig_rcs_shape_ab(outdir=FIG):
    """형상 민감도 A/B — 파라메트릭 메쉬 vs **실기체 3D 스캔**(Phantom 4, CC-BY).
    두 모델 모두 PEC + 동일 부위구성(스캔에 없는 프로펠러·카메라 **및 내부 산란체(배터리/PCB)** 는
    파라메트릭에서도 제외)으로 맞춰 **순수 형상 차이만** 측정한다. λ=6~16cm 에선 λ/8 이하
    디테일이 안 보인다는 주장을 데이터로 검증하는 그림.

    ⚠ **이 그림만 SBR 이 아니라 PO 다 — 그럴 수밖에 없다.**
      SBR 은 광선을 쏠 **삼각형 메쉬**가 있어야 하는데, 스캔 자산은 `phantom4_scan_points.npz`
      (P/N/dA **점구름**)뿐이고 원본 STL(154 MB)은 저장소에 없다(prep_cad_scan.py 참조).
      → 두 모델 **모두 같은 PO 엔진**으로 재므로 가림 편향이 **양쪽에 똑같이** 걸려 상쇄된다.
        이 그림이 주장하는 것은 절대 σ 가 아니라 **형상 A/B 의 차이(Δ dB)** 이므로 결론은 유효하다.
      → 절대값을 인용하려면 SBR 값(§SBR 전환)을 쓸 것."""
    from drones import build_drone
    from rcs_po import mesh_to_points, rcs_from_points
    npz = os.path.join(os.path.dirname(__file__), "..", "assets", "meshes", "cad",
                       "phantom4_scan_points.npz")
    d = np.load(npz)
    Ps, Ns, dAs = d["P"].astype(float), d["N"].astype(float), d["dA"].astype(float)
    spec = DRONES["phantom4"]; mesh = build_drone(spec)
    az = np.arange(0, 360, 1.0)
    bands = [("LTE 1.84", 1.84e9), ("5G 3.5", 3.5e9), ("WiFi 5.21", 5.21e9)]
    # 비교 가능 부위만: 스캔에 없는 프로펠러/카메라(+내부 산란체)는 파라메트릭에서 제외
    g_cmp = {"prop": 0.0, "camera": 0.0, "battery": 0.0, "pcb": 0.0}

    fig, axes = plt.subplots(1, 2, figsize=(13.6, 5.4), constrained_layout=True,
                             gridspec_kw=dict(width_ratios=[1.25, 1.0]))
    fc0 = 3.5e9
    Pp, Np_, dAp, wp = mesh_to_points(mesh, (299792458.0 / fc0) / 7.0, gamma=g_cmp)
    s_par = rcs_from_points(Pp, Np_, dAp, fc0, az, w=wp)
    s_scan = rcs_from_points(Ps, Ns, dAs, fc0, az)
    # 방위 오프셋 정렬(스캔의 기수 방향은 미지 — dB 패턴 순환상관 최대점으로 정렬, 쿼드 90° 모호)
    a_p, a_s = dbsm(s_par), dbsm(s_scan)
    xc = [np.corrcoef(a_p, np.roll(a_s, k))[0, 1] for k in range(360)]
    k0 = int(np.argmax(xc))
    axes[0].plot(az, a_p, color="0.55", lw=1.5, label="parametric mesh (spec-sheet)")
    axes[0].plot(az, np.roll(a_s, k0), color="#1565c0", lw=1.6,
                 label=f"real-body 3D scan (az-aligned {k0}°)")
    axes[0].axhline(dbsm(s_par.mean()), color="0.55", ls="--", lw=1)
    axes[0].axhline(dbsm(s_scan.mean()), color="#1565c0", ls="--", lw=1)
    axes[0].set_xlabel("Azimuth [deg]"); axes[0].set_ylabel("RCS [dBsm]")
    axes[0].set_title(f"(a) Phantom 4 azimuth pattern @ {fc0/1e9:.1f} GHz", fontsize=11)
    axes[0].grid(alpha=0.3); axes[0].legend(fontsize=9, loc="lower left")
    # (b) 대역별 방위평균
    means_p, means_s = [], []
    for _, f in bands:
        Pp2, Np2, dAp2, wp2 = mesh_to_points(mesh, (299792458.0 / f) / 7.0, gamma=g_cmp)
        means_p.append(dbsm(rcs_from_points(Pp2, Np2, dAp2, f, az, w=wp2).mean()))
        means_s.append(dbsm(rcs_from_points(Ps, Ns, dAs, f, az).mean()))
    x = np.arange(len(bands)); wb = 0.38
    # 값이 전부 음수(dBsm)라 bottom=0 으로 그리면 막대가 0 에서 아래로 늘어져 '기둥'처럼 보인다.
    # 바닥을 최저값 아래로 내려 **차이가 보이도록** 그린다(fig_rcs_materials 와 같은 규약).
    base = float(np.floor(min(means_p + means_s))) - 2.0
    axes[1].bar(x - wb/2, np.array(means_p) - base, wb, bottom=base, color="0.6", label="parametric")
    axes[1].bar(x + wb/2, np.array(means_s) - base, wb, bottom=base, color="#1565c0", label="3D scan")
    for xi, (mp, ms) in enumerate(zip(means_p, means_s)):
        axes[1].text(xi, max(mp, ms) + 0.25, f"{ms-mp:+.1f} dB", ha="center",
                     fontsize=9.5, fontweight="bold")
    axes[1].set_ylim(base, max(means_p + means_s) + 1.6)
    axes[1].set_xticks(x, [b[0] + " GHz" for b in bands], fontsize=9)
    axes[1].set_ylabel("Azimuth-avg RCS [dBsm]")
    axes[1].set_title("(b) Azimuth-mean per band", fontsize=11)
    axes[1].grid(axis="y", alpha=0.3); axes[1].legend(fontsize=9)
    fig.suptitle("Shape A/B — parametric mesh vs real-body 3D scan", fontsize=13, fontweight="bold")
    fig.supxlabel("Engine: PO for BOTH sides -- the scan asset is a point cloud, not a mesh, so rays "
                  "cannot be shot at it. The occlusion bias is therefore identical on both curves\n"
                  "and cancels in the difference. Read the delta, not the absolute level "
                  "(for absolute RCS use the SBR figures).\n"
                  "Scan: 'DJI PHANTOM 4 HI RES SCAN' by NeverDun, Thingiverse 1456295 (CC-BY)",
                  fontsize=8.5, color="0.45")
    fn = os.path.join(outdir, "report2_rcs_shape_ab.png")
    fig.savefig(fn, dpi=130, bbox_inches="tight"); plt.close(fig)
    print("[radar]", os.path.relpath(fn)); return fn


def build_all(outdir=FIG):
    fig_setup(outdir); fig_rcs_polar(outdir); fig_rcs_bands(outdir)
    fig_rcs_materials(outdir); fig_rcs_shape_ab(outdir)
    fig_wave_spectra(outdir); fig_range_profiles(outdir); fig_summary(outdir)
    print("report2 그림 생성 완료 →", os.path.relpath(outdir))


if __name__ == "__main__":
    build_all()
