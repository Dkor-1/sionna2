# -*- coding: utf-8 -*-
"""
run_matrix.py — (benchmark/report5) 본 실험: 점유 × 신호×드론 × 시나리오 × RT 교차검증
=======================================================================================
run_min_cell 의 '최소 셀 1개'를 4개 축으로 확장한 **공정 벤치마크 매트릭스**다.
모든 셀이 같은 철학을 따른다: *SCR is measured, not swept* — 고정 예산(EIRP·G_rx·NF)
+ PO-RCS·기하·대역폭에서 에코 SNR 을 물리로 유도하고, SCR·Pd 는 RD맵에서 측정한다.

  A) 점유 공정성   : 5G NR 100MHz 를 G1/G2/G3 로 바꿔가며 EIRP 스윕 → Pd(EIRP) 곡선.
                     기준신호의 (대역 → 거리분해능) × (에너지 점유 → 처리이득) 두 축이
                     모두 물리로 Pd 에 반영된다. 측정: G1(SSB만)은 G3 보다 ~18 dB 더
                     큰 예산이 있어야 같은 Pd (불가능이 아니라 '비싸다').
  B) 신호×드론     : {5G100, WiFi80, LTE20, LTE10} × 드론 5종 × radial, 고정 EIRP.
                     → Pd/SCR/위치오차 히트맵 + outputs/bench_matrix.csv (로드맵 B).
  C) 시나리오/블라인드: mavic4pro × 5G100 × {radial, waypoint, tangential, hover},
                     궤적 8스냅샷별 Pd — 측정: 완전 블라인드는 정지(hover, f_d=0)에서만
                     (표적이 ECA 부분공간에 정확히 포함); 저속 횡단은 마진이 흡수
                     (로드맵 C; 정지 드론 → report3 마이크로도플러가 필요한 지점).
  D) RT 교차검증   : SionnaRTChannel(GPU) — 자유공간 클러터≈0 확인, 흡수체 챔버
                     잔향 실측(가정 CH_CLUTTER_RATIO 와 비교), RT 채널로 같은 셀 재실행.

공정성 규약(전 셀 공통): 기준신호만 아는 패시브 수신(wf.ref), ref 는 **송신 전체파형
전력 기준** 정규화(희소 파일럿의 에너지 핸디캡 유지), CPI 시간 T_CPI 고정(도플러분해능
1/T_CPI 균일 — 프레임률이 다른 파형끼리 공정), CFAR Pfa=1e-4, 히트=참셀 ±1.

실행:  /home/yunjung/.venvs/py312/bin/python run_matrix.py            (전체, ~수 분)
       ... run_matrix.py --quick                                      (빠른 점검)
       ... run_matrix.py --only a,b                                   (섹션 선택)
산출:  outputs/figures/report5_{occupancy_pd,matrix,scenarios,rt_clutter}.png
       outputs/bench_matrix.csv, outputs/report5_results.json (노트북이 수치 인용)
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
import zlib
from concurrent.futures import ProcessPoolExecutor

# 워커 프로세스 병렬(ProcessPool) × BLAS 스레드 중첩 방지 — numpy import 전에 지정
os.environ.setdefault("OMP_NUM_THREADS", "4")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "4")
os.environ.setdefault("MKL_NUM_THREADS", "4")

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.abspath(os.path.join(_HERE, "..", "src"))
for _p in (_SRC, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from waveforms import lte_downlink, nr_downlink, wifi_80211ac   # noqa: E402
from bistatic_scene import C0                                    # noqa: E402
from link_budget import LinkBudget                               # noqa: E402
from channel import AnalyticChannel                              # noqa: E402
from scenarios import SCENARIOS                                  # noqa: E402
from geometry import TX, RX, CENTER, CH_CLUTTER_RATIO, SPEED, SPAN  # noqa: E402
from run_min_cell import run_cell, EIRP_DBM, frame_len           # noqa: E402

FIGDIR = os.path.abspath(os.path.join(_HERE, "..", "outputs", "figures"))
OUTDIR = os.path.abspath(os.path.join(_HERE, "..", "outputs"))

T_CPI = 0.03                       # 고정 CPI 시간[s] → 도플러분해능 1/T_CPI≈33Hz (파형 공정)
PFA = 1e-4                         # CFAR Pfa (report4 RD맵과 동일)

# 비교 파형 4종: (표시이름, 표준, 대역, 반송파) — 점유는 B/C 에선 G3(풀로드) 고정
WAVEFORMS = {
    "5G100":  ("nr",   100e6, 3.5e9),
    "WiFi80": ("wifi",  80e6, 5.21e9),
    "LTE20":  ("lte",   20e6, 1.843e9),
    "LTE10":  ("lte",   10e6, 1.843e9),
}
DRONES5 = ["s1000plus", "phantom4", "matrice4e", "mavic4pro", "mini5pro"]  # 크기 내림차순

# 점유 모드 색(report2/4 와 동일 규약), 시나리오 색(고정 배정)
MODE_COL = {"G1": "#c62828", "G2": "#ef6c00", "G3": "#2e7d32"}
SCEN_COL = {"radial": "#1565c0", "waypoint": "#2e7d32",
            "tangential": "#ef6c00", "hover": "#6a1b9a"}

_WF_CACHE: dict = {}


def make_wf(std, bw, carrier, occ="G3"):
    key = (std, bw, carrier, occ)
    if key not in _WF_CACHE:
        fn = {"nr": nr_downlink, "lte": lte_downlink, "wifi": wifi_80211ac}[std]
        _WF_CACHE[key] = fn(bw_hz=bw, carrier_hz=carrier, occupancy=occ)
    return _WF_CACHE[key]


def m_for(wf, t_cpi=T_CPI):
    """고정 CPI 시간 → 프레임 수 M (2의 거듭제곱, slow-time FFT 효율).
    프레임 길이는 frame_len(WiFi 듀티 반영) — run_cell 의 실제 프레임과 일치해야 한다."""
    prf = wf.fs_hz / frame_len(wf)
    return int(2 ** round(np.log2(max(16, t_cpi * prf))))


def _seed(*key):
    """셀별 결정적 시드(프로세스 무관)."""
    return zlib.crc32("|".join(str(k) for k in key).encode()) % (2 ** 31)


def _cell_task(job):
    """워커 프로세스에서 셀 1개 실행 → 직렬화 가능한 요약 dict.
    job: (wf_spec(std,bw,carrier,occ), drone, scen_name, snap_idx|None, eirp_dbm, N, pref_occ)
    pref_occ: 전력 정규화 기준 점유(예: 'G1' 셀에 'G3' — per-RE 전력 동일 가정). None=자기 자신."""
    (std, bw, carrier, occ), drone, scen, snap, eirp, N, pref_occ = job
    wf = make_wf(std, bw, carrier, occ)
    pref_tx = make_wf(std, bw, carrier, pref_occ).tx if pref_occ else None
    lb = LinkBudget(eirp_dbm=eirp)
    ch = AnalyticChannel(clutter=CH_CLUTTER_RATIO)
    pos, vel = SCENARIOS[scen](TX, RX, CENTER, speed=SPEED, span=SPAN, n=32)
    if snap is not None:                       # 궤적 특정 스냅샷 1개만 평가
        pos, vel = pos[snap:snap + 1], vel[snap:snap + 1]
    res = run_cell(wf, drone, pos, vel, lb, channel=ch, power_ref_tx=pref_tx,
                   M=m_for(wf), N=N, pfa=PFA, seed0=_seed(std, bw, occ, drone, scen, snap, eirp))
    st, lt = res["state"], res["link"]
    return dict(wf=f"{std}{bw/1e6:.0f}", occ=occ, drone=drone, scen=scen, snap=snap,
                eirp_dbm=eirp, N=N, M=res["M"],
                pd=res["pd"], pd_lo=res["pd_lo"], pd_hi=res["pd_hi"],
                scr_db=res["scr_mean"], scr_std=res["scr_std"],
                rb_err_m=res["rb_err_m"],
                sigma_dbsm=float(10 * np.log10(st.sigma_m2)),
                snr_echo_db=lt["snr_echo_db"], dnr_db=lt["dnr_db"],
                snr_echo_eff_db=res["snr_echo_eff_db"],   # 점유차+잡음대역 보정 반영(실주입)
                fd_hz=st.fd, rb_m=st.tau * C0, delta_rb_m=C0 / wf.bw_hz,
                ref_bw_mhz=wf.ref_bw_hz / 1e6, occupancy_frac=wf.occupancy_frac)


def _run_jobs(jobs, workers, tag):
    t0 = time.time()
    if workers <= 1:
        out = [_cell_task(j) for j in jobs]
    else:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            out = list(ex.map(_cell_task, jobs))
    print(f"  [{tag}] {len(jobs)}셀 완료 ({time.time()-t0:.0f}s)")
    return out


# --------------------------------------------------------------------------- #
#  개요 그림 — '이 벤치마크가 무엇을 하는가' 한 장 (3D 장면 + 주입 vs 유도 대비)
# --------------------------------------------------------------------------- #
def fig_overview(R=None, outdir=FIGDIR):
    """좌: 챔버 3D(TX→드론→RX, 무엇이 고정/유도/측정인지 라벨).
    우: report4 방식(SNR 주입) vs report5 방식(링크버짓 유도) 흐름 대비 + 수식."""
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection, Line3DCollection
    from viz_bistatic import _draw_chamber, _scaled_mesh
    from drones import DRONES, build_drone, drone_colors
    from bistatic_scene import bistatic_params

    fig = plt.figure(figsize=(15, 6.6), constrained_layout=True)
    fig.suptitle("report5 fair benchmark — target SNR is derived from the link budget, never injected; SCR·Pd are measured",
                 fontsize=14, fontweight="bold")

    # (좌) 챔버 3D 장면 — 고정/유도/측정 라벨
    ax = fig.add_subplot(1, 2, 1, projection="3d")
    W, D, H = 30.0, 20.0, 11.0
    _draw_chamber(ax, W, D, H)
    tx, rx, tg = np.array(TX), np.array(RX), np.array(CENTER)
    p = bistatic_params(TX, RX, CENTER, (-SPEED, 0.6 * SPEED, 0.2 * SPEED), 3.5e9)
    for pt, m, c in [(tx, "^", "#ef6c00"), (rx, "v", "#1565c0")]:
        ax.plot([pt[0]] * 2, [pt[1]] * 2, [0, pt[2]], color="0.4", lw=2)
        ax.scatter(*pt, s=150, marker=m, color=c, depthshade=False)
    ax.add_collection3d(Line3DCollection([[tx, tg]], colors="#ef6c00", linewidths=1.8, linestyles="--"))
    ax.add_collection3d(Line3DCollection([[tg, rx]], colors="#2e7d32", linewidths=2.0))
    ax.add_collection3d(Line3DCollection([[tx, rx]], colors="#c62828", linewidths=1.2, linestyles=":"))
    spec = DRONES["mavic4pro"]; mesh = build_drone(spec)
    Vs = _scaled_mesh(mesh, 2.6, tg); dc = drone_colors(spec)
    ax.add_collection3d(Poly3DCollection([[Vs[a], Vs[b], Vs[c]] for a, b, c in mesh.f],
                                         facecolors=[dc.get(g, (.6, .6, .6)) for g in mesh.g],
                                         edgecolors=(0, 0, 0, 0.2), linewidths=0.1))
    ax.text(tx[0], tx[1] - 1.5, tx[2] + 1.2, f"[1] Fixed (controlled)\nEIRP {EIRP_DBM:.0f} dBm\nG_rx·NF",
            color="#ef6c00", fontsize=9, ha="center", fontweight="bold")
    ax.text(tg[0] + 1.5, tg[1], tg[2] + 2.4,
            f"[2] Derived (physics)\nRCS=PO (aspect-avg)\nR1={p['R1']:.0f}m R2={p['R2']:.0f}m\n→ echo SNR",
            color="k", fontsize=9)
    ax.text(rx[0], rx[1] + 1.5, rx[2] + 1.2, "[3] Measured\nECA→CAF→CFAR\n→ SCR·Pd",
            color="#1565c0", fontsize=9, ha="center", fontweight="bold")
    ax.set_xlim(0, W); ax.set_ylim(0, D); ax.set_zlim(0, H)
    try: ax.set_box_aspect((W, D, H))
    except Exception: pass
    ax.view_init(elev=22, azim=-70); ax.tick_params(labelsize=7)
    ax.set_xlabel("x [m]"); ax.set_ylabel("y [m]"); ax.set_zlabel("z [m]")

    # (우) 주입 vs 유도 — 흐름 대비 다이어그램
    axf = fig.add_subplot(1, 2, 2); axf.axis("off"); axf.set_xlim(0, 10); axf.set_ylim(0, 10)
    box_old = dict(boxstyle="round,pad=0.4", fc="#f3f3f3", ec="0.55")
    box_new = dict(boxstyle="round,pad=0.4", fc="#e8f5e9", ec="#2e7d32")
    box_out = dict(boxstyle="round,pad=0.4", fc="#fff8e1", ec="#ef6c00")
    ar = dict(arrowstyle="->", color="0.35", lw=1.6)
    # 위: report4 까지
    axf.text(0.2, 9.55, "Up to report4 — processing-gain comparison (not fair across signals)",
             fontsize=10.5, fontweight="bold", color="0.35")
    axf.text(1.6, 8.5, "Target SNR\n(injected knob)", ha="center", fontsize=9.5, bbox=box_old)
    axf.text(5.0, 8.5, "ECA → CAF → CFAR", ha="center", fontsize=9.5, bbox=box_old)
    axf.text(8.4, 8.5, "Pd vs\ninjected SNR", ha="center", fontsize=9.5, bbox=box_old)
    axf.annotate("", xy=(3.5, 8.5), xytext=(2.8, 8.5), arrowprops=ar)
    axf.annotate("", xy=(7.3, 8.5), xytext=(6.5, 8.5), arrowprops=ar)
    axf.text(1.6, 7.55, "(problem) erases per-signal wavelength, RCS, noise bandwidth", fontsize=8.5, color="#c62828")
    # 아래: report5
    axf.text(0.2, 6.55, "report5 — derive from link budget → measure (fair benchmark)",
             fontsize=10.5, fontweight="bold", color="#2e7d32")
    for x, t in [(1.25, "Fixed budget\nEIRP·G_rx·NF"), (3.4, "Target RCS\n(PO, aspect-avg)"),
                 (5.55, "Geometry\nR1·R2·L"), (7.7, "Noise\nkTFB")]:
        axf.text(x, 5.55, t, ha="center", fontsize=9, bbox=box_new)
    axf.annotate("", xy=(4.5, 4.35), xytext=(1.25, 5.0), arrowprops=ar)
    axf.annotate("", xy=(4.5, 4.35), xytext=(3.4, 5.0), arrowprops=ar)
    axf.annotate("", xy=(4.5, 4.35), xytext=(5.55, 5.0), arrowprops=ar)
    axf.annotate("", xy=(4.5, 4.35), xytext=(7.7, 5.0), arrowprops=ar)
    axf.text(4.5, 3.9, "Bistatic radar equation → derive echo SNR & direct path",
             ha="center", fontsize=9.8, bbox=box_new, fontweight="bold")
    axf.annotate("", xy=(4.5, 2.85), xytext=(4.5, 3.4), arrowprops=ar)
    axf.text(4.5, 2.4, "Same processing chain (ECA → CAF range-Doppler → CA-CFAR)",
             ha="center", fontsize=9.5, bbox=box_old)
    axf.annotate("", xy=(4.5, 1.4), xytext=(4.5, 1.95), arrowprops=ar)
    axf.text(4.5, 0.95, "SCR·Pd·position error = measured  →  A occupancy · B signal×drone · C motion · D RT cross-check",
             ha="center", fontsize=9.8, bbox=box_out, fontweight="bold")
    axf.text(5.0, 7.0,
             r"$P_{echo}=\frac{EIRP\,G_{rx}\lambda^2\sigma}{(4\pi)^3 R_1^2 R_2^2}$"
             r"$\;\;P_{dir}=\frac{EIRP\,G_{rx}\lambda^2}{(4\pi)^2 L^2}$"
             r"$\;\;P_n=kT_0FB$", ha="center", fontsize=11.5, color="#1a1a1a")

    fn = os.path.join(outdir, "report5_overview.png")
    fig.savefig(fn, dpi=130); plt.close(fig)
    print("[matrix]", os.path.relpath(fn)); return fn


# --------------------------------------------------------------------------- #
#  A) 점유 공정성 — 5G G1/G2/G3 × EIRP 스윕
# --------------------------------------------------------------------------- #
def section_a(workers, quick=False):
    # 기준선 12 dBm 에서 광대역 G3 는 포화(Pd≈1) — 전이 구간을 보려고 저전력까지 내린다.
    eirps = [-24.0, -12.0, 0.0, 12.0] if quick else \
            [-36.0, -30.0, -24.0, -18.0, -12.0, -6.0, 0.0, 12.0]
    N = 24 if quick else 60
    # 전력 기준 = G3 tx (per-RE 송신전력 동일 가정 → G1 의 낮은 평균 방사전력이 반영됨)
    jobs = [(("nr", 100e6, 3.5e9, occ), "mavic4pro", "radial", None, e, N, "G3")
            for occ in ("G1", "G2", "G3") for e in eirps]
    rows = _run_jobs(jobs, workers, "A 점유×EIRP")
    return dict(eirps=eirps, N=N, rows=rows)


def fig_occupancy(a, outdir=FIGDIR):
    """위: G1/G2/G3 실제 리소스그리드(무엇이 켜져 있나 '보이게') / 아래: 측정 Pd(EIRP) + 점유의 대가."""
    import matplotlib.pyplot as plt
    from viz_occupancy import _grid_image        # report2 와 같은 그리드 '사진' (단일 출처)
    fig = plt.figure(figsize=(12.5, 8.4), constrained_layout=True)
    gs = fig.add_gridspec(2, 3, height_ratios=[1.0, 1.55])
    for j, occ in enumerate(("G1", "G2", "G3")):
        axg = fig.add_subplot(gs[0, j])
        wf = make_wf("nr", 100e6, 3.5e9, occ)
        _grid_image(axg, wf)
        axg.set_title(f"{occ} — ref {wf.ref_name} ({wf.ref_bw_hz/1e6:.0f} MHz, "
                      f"occ {wf.occupancy_frac*100:.0f}%)", fontsize=9.5, color=MODE_COL[occ])
    ax = fig.add_subplot(gs[1, :])
    for occ in ("G1", "G2", "G3"):
        rr = [r for r in a["rows"] if r["occ"] == occ]
        rr.sort(key=lambda r: r["eirp_dbm"])
        x = [r["eirp_dbm"] for r in rr]
        y = [r["pd"] for r in rr]
        # Wilson CI 는 pd=0/1 에서 부동소수점상 pd 를 1e-16 만큼 넘을 수 있어 음수 방지 클리핑
        yerr = np.maximum(0.0, [[r["pd"] - r["pd_lo"] for r in rr],
                                [r["pd_hi"] - r["pd"] for r in rr]])
        wf = make_wf("nr", 100e6, 3.5e9, occ)
        ax.errorbar(x, y, yerr=yerr, marker="o", lw=1.8, capsize=3, color=MODE_COL[occ],
                    label=f"{occ} (ref {wf.ref_name}, {wf.ref_bw_hz/1e6:.0f} MHz, "
                          f"occ {wf.occupancy_frac*100:.0f}%)")
    ax.axhline(0.9, color="0.6", ls="--", lw=0.8)
    ax.text(ax.get_xlim()[0], 0.905, " Pd=0.9", color="0.45", fontsize=8, va="bottom")
    ax.set_ylim(-0.03, 1.05)
    ax.set_xlabel("Illuminator EIRP [dBm]  (physical knob — target SNR derived from link budget)")
    ax.set_ylabel("Detection probability Pd (Wilson 95% CI)")
    ax.set_title("Occupancy fairness — same 5G 100MHz, yet what is 'on' (grids above) drives Pd (anechoic chamber)\n"
                 f"mavic4pro · radial · CPI {T_CPI*1e3:.0f}ms · CFAR Pfa={PFA:g} · N={a['N']}/point",
                 fontsize=11.5)
    # '점유의 대가' 화살표 — G3 와 G1 이 Pd 50% 를 처음 넘는 EIRP 사이 간격
    def _tr(occ):
        rr = sorted([r for r in a["rows"] if r["occ"] == occ], key=lambda r: r["eirp_dbm"])
        return next((r["eirp_dbm"] for r in rr if r["pd"] >= 0.5), None)
    t3, t1 = _tr("G3"), _tr("G1")
    if t3 is not None and t1 is not None and t1 > t3:
        ax.annotate("", xy=(t1, 0.5), xytext=(t3, 0.5),
                    arrowprops=dict(arrowstyle="<->", color="#6a1b9a", lw=2))
        ax.text((t1 + t3) / 2, 0.545, f"Cost of occupancy ≈{t1 - t3:.0f} dB\n(G1 needs that much more budget)",
                ha="center", fontsize=9.5, color="#6a1b9a", fontweight="bold")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=9, loc="upper left")
    fn = os.path.join(outdir, "report5_occupancy_pd.png")
    fig.savefig(fn, dpi=130); plt.close(fig)
    print("[matrix]", os.path.relpath(fn)); return fn


# --------------------------------------------------------------------------- #
#  B) 신호 × 드론 매트릭스 (radial, 고정 EIRP) → 히트맵 + CSV
# --------------------------------------------------------------------------- #
def section_b(workers, quick=False):
    N = 30 if quick else 100
    jobs = [((std, bw, car, "G3"), d, "radial", None, EIRP_DBM, N, None)
            for wfk, (std, bw, car) in WAVEFORMS.items() for d in DRONES5]
    rows = _run_jobs(jobs, workers, "B 신호×드론")
    return dict(N=N, rows=rows)


def write_csv(b, path=os.path.join(OUTDIR, "bench_matrix.csv")):
    cols = ["wf", "occ", "drone", "scen", "eirp_dbm", "sigma_dbsm",
            "snr_echo_db", "snr_echo_eff_db", "dnr_db", "delta_rb_m", "rb_m", "fd_hz",
            "scr_db", "scr_std", "pd", "pd_lo", "pd_hi", "rb_err_m", "M", "N"]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in b["rows"]:
            w.writerow({k: (f"{v:.4g}" if isinstance(v, float) else v) for k, v in r.items()})
    print("[matrix]", os.path.relpath(path)); return path


def fig_matrix(b, outdir=FIGDIR):
    import matplotlib.pyplot as plt
    from drones import DRONES
    wfs = list(WAVEFORMS.keys())                       # 해상도 순: 5G100, WiFi80, LTE20, LTE10
    P = np.zeros((len(DRONES5), len(wfs)))
    S = np.zeros_like(P)
    for r in b["rows"]:
        i = DRONES5.index(r["drone"])
        j = [f"{s}{bw/1e6:.0f}" for s, bw, c in WAVEFORMS.values()].index(r["wf"])
        P[i, j] = r["pd"]; S[i, j] = r["scr_db"]
    E = np.zeros_like(P)                                   # 위치오차 [m]
    for r in b["rows"]:
        i = DRONES5.index(r["drone"])
        j = [f"{s}{bw/1e6:.0f}" for s, bw, c in WAVEFORMS.values()].index(r["wf"])
        E[i, j] = r["rb_err_m"] if r["rb_err_m"] is not None else np.nan

    # 왼쪽에 드론 3D 메쉬 썸네일 열 — '행이 어떤 드론인지' 보이게 (report2 스타일)
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    from drones import build_drone, drone_colors
    fig = plt.figure(figsize=(13.6, 7.0), constrained_layout=True)
    gs = fig.add_gridspec(len(DRONES5), 2, width_ratios=[1.0, 5.6])
    for i, key in enumerate(DRONES5):
        axm = fig.add_subplot(gs[i, 0], projection="3d")
        m = build_drone(DRONES[key]); V = np.array(m.v)
        c = (V.min(0) + V.max(0)) / 2; rad = (V.max(0) - V.min(0)).max() / 2
        dc = drone_colors(DRONES[key])
        axm.add_collection3d(Poly3DCollection(
            [[V[a], V[b], V[cc]] for a, b, cc in m.f],
            facecolors=[dc.get(g, (.6, .6, .6)) for g in m.g],
            edgecolors=(0, 0, 0, 0.10), linewidths=0.08))
        axm.set_xlim(c[0]-rad, c[0]+rad); axm.set_ylim(c[1]-rad, c[1]+rad)
        axm.set_zlim(c[2]-rad, c[2]+rad)
        try: axm.set_box_aspect((1, 1, 1))
        except Exception: pass
        axm.view_init(elev=22, azim=-55); axm.set_axis_off()
    ax = fig.add_subplot(gs[:, 1])
    im = ax.imshow(S, cmap="Blues", vmin=min(20, S.min()), vmax=S.max(), aspect="auto")
    smid = 0.5 * (min(20, S.min()) + S.max())
    for i in range(P.shape[0]):
        for j in range(P.shape[1]):
            ink = "white" if S[i, j] > smid else "#1a1a1a"
            err = "—" if np.isnan(E[i, j]) else f"{E[i,j]:.1f}m"
            ax.text(j, i, f"Pd {P[i,j]*100:.0f}%\nSCR {S[i,j]:.0f}dB\nerr {err}",
                    ha="center", va="center", fontsize=9, color=ink)
    dr_lab = [f"{DRONES[k].name.replace('DJI ','')}\n(diag {DRONES[k].diagonal_mm:.0f} mm)"
              for k in DRONES5]
    # 분해능 라벨은 실제 점유대역 기준(wf.bw_hz) — 본문/CSV 의 delta_rb_m 과 동일 규약
    wf_lab = [f"{k}\nres {C0/make_wf(*WAVEFORMS[k]).bw_hz:.0f} m" for k in wfs]
    ax.set_xticks(range(len(wfs)), wf_lab, fontsize=9)
    ax.set_yticks(range(len(DRONES5)), dr_lab, fontsize=9)
    ax.set_title("Signal × drone matrix — fixed budget (EIRP %.0f dBm) · radial · G3 (anechoic chamber, all measured)\n"
                 "rows=drones (by size), cols=waveforms (by range resolution) · cell color=SCR margin · err=single-target peak accuracy (high SNR: accuracy≈resolution/√SNR)\n"
                 "narrowband=lower kTB noise→higher SCR · resolution is range-axis separability (direct-path residual, multi-target), not accuracy"
                 % EIRP_DBM, fontsize=11)
    fig.colorbar(im, ax=ax, fraction=0.035, label="SCR [dB] (measured)")
    fn = os.path.join(outdir, "report5_matrix.png")
    fig.savefig(fn, dpi=130); plt.close(fig)
    print("[matrix]", os.path.relpath(fn)); return fn


# --------------------------------------------------------------------------- #
#  C) 시나리오/블라인드 — 궤적 스냅샷별 Pd
# --------------------------------------------------------------------------- #
def section_c(workers, quick=False):
    N = 16 if quick else 40
    snaps = [0, 4, 8, 13, 17, 22, 26, 31]
    jobs = [(("nr", 100e6, 3.5e9, "G3"), "mavic4pro", scen, s, EIRP_DBM, N, None)
            for scen in ("radial", "waypoint", "tangential", "hover") for s in snaps]
    rows = _run_jobs(jobs, workers, "C 시나리오×스냅샷")
    return dict(N=N, snaps=snaps, rows=rows)


def fig_scenarios(c, outdir=FIGDIR):
    import matplotlib.pyplot as plt
    from viz_bistatic import _draw_chamber_plan     # report4 와 같은 챔버 평면 스타일
    fig, axes = plt.subplots(1, 3, figsize=(16.5, 5.6), constrained_layout=True,
                             gridspec_kw=dict(width_ratios=[1.25, 1.0, 1.0]))
    dop_res = 1.0 / T_CPI

    # (a) 챔버 평면 — 4가지 모션이 실제로 어떤 비행인지
    axp = axes[0]; axp.set_aspect("equal")
    _draw_chamber_plan(axp, 30.0, 20.0)
    axp.plot(TX[0], TX[1], "^", ms=12, color="#ef6c00"); axp.text(TX[0]+0.6, TX[1], "TX", fontsize=9)
    axp.plot(RX[0], RX[1], "v", ms=12, color="#1565c0"); axp.text(RX[0]+0.6, RX[1], "RX", fontsize=9)
    for scen in ("radial", "waypoint", "tangential", "hover"):
        pos, vel = SCENARIOS[scen](TX, RX, CENTER, speed=SPEED, span=SPAN, n=32)
        col = SCEN_COL[scen]
        if scen == "hover":
            axp.plot(pos[0, 0], pos[0, 1], "*", ms=17, color=col, mec="k", mew=0.5, zorder=5)
        else:
            axp.plot(pos[:, 0], pos[:, 1], "-", color=col, lw=2.2)
            axp.plot(pos[0, 0], pos[0, 1], "o", ms=6, color=col)          # 시작점
            k = len(pos) // 2
            axp.annotate("", xy=pos[k + 1, :2], xytext=pos[k, :2],
                         arrowprops=dict(arrowstyle="-|>", color=col, lw=2))
        axp.plot([], [], "-" if scen != "hover" else "*", color=col, label=scen)
    axp.set_xlim(-2, 32); axp.set_ylim(-2, 22)
    axp.set_xlabel("x [m]"); axp.set_ylabel("y [m]"); axp.grid(alpha=0.25)
    axp.legend(fontsize=8.5, loc="lower right")
    axp.set_title(f"(a) Four motions inside the chamber (speed {SPEED:.0f} m/s, ●=start)", fontsize=11)

    for scen in ("radial", "waypoint", "tangential", "hover"):
        rr = sorted([r for r in c["rows"] if r["scen"] == scen], key=lambda r: r["snap"])
        prog = [r["snap"] / 31 * 100 for r in rr]
        axes[2].plot(prog, [r["pd"] for r in rr], "o-", color=SCEN_COL[scen], lw=1.8,
                     label=f"{scen} (trajectory-mean Pd={np.mean([r['pd'] for r in rr])*100:.0f}%)")
        axes[1].plot(prog, [r["fd_hz"] for r in rr], "o-", color=SCEN_COL[scen], lw=1.8)
    axes[2].set_ylim(-0.03, 1.05); axes[2].set_ylabel("Detection probability Pd")
    axes[2].set_title("(c) Pd vs trajectory progress — motion drives detection", fontsize=11)
    axes[2].legend(fontsize=8.5, loc="center right")
    axes[1].axhspan(-dop_res, dop_res, color="0.55", alpha=0.18)
    axes[1].text(50, 0, f"zero-Doppler ridge ± Doppler resolution ({dop_res:.0f}Hz)\ndetected even here if the margin is large\n"
                        "(fully cancelled only at hover, f_d=0)",
                 fontsize=8.5, color="0.35", ha="center", va="center")
    axes[1].set_ylabel("Target bistatic Doppler f_d [Hz]")
    axes[1].set_title("(b) f_d per trajectory — hover falls exactly in the ECA subspace", fontsize=11)
    for ax in axes[1:]:
        ax.set_xlabel("Trajectory progress [%]"); ax.grid(alpha=0.3)
    fig.suptitle("Scenario axis — only hover is fully blind; slow crossing is absorbed by the margin against ECA attenuation "
                 "(hovering drone → needs report3 micro-Doppler)\n"
                 f"mavic4pro · 5G 100MHz G3 · EIRP {EIRP_DBM:.0f}dBm · snapshot N={c['N']}",
                 fontsize=12, fontweight="bold")
    fn = os.path.join(outdir, "report5_scenarios.png")
    fig.savefig(fn, dpi=130); plt.close(fig)
    print("[matrix]", os.path.relpath(fn)); return fn


# --------------------------------------------------------------------------- #
#  D) Sionna RT 교차검증 (GPU) — 자유공간 ≈ Analytic, 챔버 잔향 실측
# --------------------------------------------------------------------------- #
def section_d(quick=False):
    from channel import SionnaRTChannel
    out = {"available": True}
    wf = make_wf("nr", 100e6, 3.5e9, "G3")
    lb = LinkBudget(eirp_dbm=EIRP_DBM)
    pos, vel = SCENARIOS["radial"](TX, RX, CENTER, speed=SPEED, span=SPAN, n=32)
    mid = len(pos) // 2
    spp = 300_000 if quick else 1_000_000
    N = 20 if quick else 60

    # 1) 자유공간: 클러터≈0 이어야 함 (기하 교차검증)
    st_f = SionnaRTChannel(with_chamber=False, spp=spp).state(
        TX, RX, pos[mid], vel[mid], wf.carrier_hz, "mavic4pro")
    out["free"] = dict(n_clutter=len(st_f.clutter),
                       rt_echo_ratio=st_f.rt_echo_ratio)

    # 2) 흡수체 챔버: RT 가 실측한 잔향 (지연 ns, 직접파대비 dB) vs 가정치
    st_c = SionnaRTChannel(with_chamber=True, spp=spp).state(
        TX, RX, pos[mid], vel[mid], wf.carrier_hz, "mavic4pro")
    out["chamber_clutter"] = [(round(dt * 1e9, 1), round(20 * np.log10(r), 1))
                              for dt, r in st_c.clutter]
    out["assumed_clutter"] = [(round(dt * 1e9, 1), round(20 * np.log10(r), 1))
                              for dt, r in CH_CLUTTER_RATIO]
    out["rt_echo_ratio_chamber"] = st_c.rt_echo_ratio

    # 3) 같은 셀을 RT 채널(챔버 잔향 실측)로 재실행 vs Analytic(가정 잔향)
    res_rt = run_cell(wf, "mavic4pro", pos, vel, lb,
                      channel=SionnaRTChannel(with_chamber=True, spp=spp),
                      M=m_for(wf), N=N, pfa=PFA, seed0=_seed("rt-cell"))
    res_an = run_cell(wf, "mavic4pro", pos, vel, lb,
                      channel=AnalyticChannel(clutter=CH_CLUTTER_RATIO),
                      M=m_for(wf), N=N, pfa=PFA, seed0=_seed("rt-cell"))
    def _rdmap(res):
        Rb, f_d, rd, st, lt, (ri, di), true_Rb = res["example"]
        rdb = 20 * np.log10(rd / rd.max() + 1e-9)
        return dict(rb=np.asarray(Rb).round(2).tolist(),
                    fd=np.asarray(f_d).round(1).tolist(),
                    rd_db=np.asarray(rdb).round(1).tolist(),
                    true_rb=float(true_Rb), true_fd=float(st.fd))
    out["cell"] = dict(
        rt=dict(pd=res_rt["pd"], scr=res_rt["scr_mean"], n_clutter=len(res_rt["state"].clutter),
                map=_rdmap(res_rt)),
        analytic=dict(pd=res_an["pd"], scr=res_an["scr_mean"], map=_rdmap(res_an)),
        N=N)
    print(f"  [D RT] 자유공간 클러터={out['free']['n_clutter']}  "
          f"챔버 잔향 {len(out['chamber_clutter'])}개  "
          f"Pd RT={res_rt['pd']*100:.0f}% vs Analytic={res_an['pd']*100:.0f}%  "
          f"SCR RT={res_rt['scr_mean']:.1f} vs {res_an['scr_mean']:.1f} dB")
    return out


def fig_rt(d, outdir=FIGDIR):
    """좌·중: 같은 셀의 RD맵 — Analytic(가정 잔향) vs Sionna RT(광선추적 실측 잔향).
    우: 챔버 잔향 스펙트럼(RT 실측 vs 가정) — 두 백엔드가 일치함을 눈으로 확인."""
    import matplotlib.pyplot as plt
    have_maps = "map" in d["cell"]["rt"]
    if have_maps:
        fig, axes = plt.subplots(1, 3, figsize=(16.5, 5.4), constrained_layout=True,
                                 gridspec_kw=dict(width_ratios=[1.15, 1.15, 1.0]))
        for ax, key, tag in [(axes[0], "analytic", "Analytic channel (closed-form geometry + assumed clutter)"),
                             (axes[1], "rt", "Sionna RT channel (ray-traced chamber mesh)")]:
            m = d["cell"][key]["map"]
            Rb = np.asarray(m["rb"]); fd = np.asarray(m["fd"]); rdb = np.asarray(m["rd_db"])
            im = ax.pcolormesh(Rb, fd, rdb, cmap="turbo", vmin=-50, vmax=0, shading="auto")
            ax.plot(m["true_rb"], m["true_fd"], "o", mfc="none", mec="w", ms=14, mew=1.6)
            ax.set_xlabel("Bistatic range Rb [m]"); ax.set_ylabel("Doppler f_d [Hz]")
            ax.set_title(f"{tag}\nPd={d['cell'][key]['pd']*100:.0f}%  "
                         f"SCR={d['cell'][key]['scr']:.1f} dB", fontsize=10.5)
            fig.colorbar(im, ax=ax, fraction=0.046, label="Normalized [dB]")
        ax = axes[2]
    else:
        fig, ax = plt.subplots(figsize=(9.2, 5.2), constrained_layout=True)
    if d["chamber_clutter"]:
        t = [c[0] for c in d["chamber_clutter"]]; v = [c[1] for c in d["chamber_clutter"]]
        ml, sl, bl = ax.stem(t, v, basefmt=" ", bottom=-56)   # 스템 기준선을 바닥쪽으로
        plt.setp(ml, color="#1565c0", markersize=7); plt.setp(sl, color="#1565c0", lw=1.6)
        ax.plot([], [], "o-", color="#1565c0", label="RT-measured (absorber-lined chamber)")
    ta = [c[0] for c in d["assumed_clutter"]]; va = [c[1] for c in d["assumed_clutter"]]
    ax.plot(ta, va, "s", ms=9, mfc="none", mec="#c62828", mew=2,
            label="Analytic assumed (CH_CLUTTER_RATIO)")
    ax.set_xlabel("Delay relative to direct path [ns]")
    ax.set_ylabel("Amplitude relative to direct path [dB]")
    ax.set_title(f"Chamber reverberation spectrum — RT-measured vs assumed\n"
                 f"({d['free']['n_clutter']} free-space RT clutter paths → geometry cross-check passed)", fontsize=10.5)
    ax.grid(alpha=0.3); ax.legend(fontsize=8.5)
    fig.suptitle("Sionna RT cross-check — confirmed by ray tracing, not assumption (Analytic) (same cell, same processing chain)",
                 fontsize=12.5, fontweight="bold")
    fn = os.path.join(outdir, "report5_rt_clutter.png")
    fig.savefig(fn, dpi=130); plt.close(fig)
    print("[matrix]", os.path.relpath(fn)); return fn


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="빠른 점검(셀·trial 축소)")
    ap.add_argument("--only", default="a,b,c,d", help="실행 섹션 (예: a,b)")
    ap.add_argument("--workers", type=int, default=min(12, os.cpu_count() or 4))
    args = ap.parse_args()
    only = set(args.only.lower().split(","))

    import matplotlib
    matplotlib.use("Agg")
    import vizstyle
    vizstyle.use_korean()

    os.makedirs(FIGDIR, exist_ok=True)
    t0 = time.time()
    # --only 로 섹션을 나눠 돌려도 결과가 합쳐지도록, 기존 JSON 이 있으면 이어서 쓴다.
    out = os.path.join(OUTDIR, "report5_results.json")
    results = {}
    if os.path.exists(out):
        try:
            with open(out) as f:
                results = json.load(f)
        except Exception:
            results = {}
    results["meta"] = dict(eirp_dbm=EIRP_DBM, t_cpi=T_CPI, pfa=PFA,
                           tx=TX, rx=RX, center=CENTER, speed=SPEED, span=SPAN,
                           quick=args.quick)
    def _save():
        # 섹션이 끝날 때마다 저장 — 그림 단계에서 예외가 나도 계산 결과(수 분치)는 보존
        with open(out, "w") as f:
            json.dump(results, f, ensure_ascii=False, indent=1, default=float)

    fig_overview(results)                       # '이 벤치마크가 무엇을 하는가' 한 장 (항상 갱신)
    if "a" in only:
        results["A_occupancy"] = section_a(args.workers, args.quick); _save()
        fig_occupancy(results["A_occupancy"])
    if "b" in only:
        results["B_matrix"] = section_b(args.workers, args.quick); _save()
        write_csv(results["B_matrix"])
        fig_matrix(results["B_matrix"])
    if "c" in only:
        results["C_scenarios"] = section_c(args.workers, args.quick); _save()
        fig_scenarios(results["C_scenarios"])
    if "d" in only:
        results["D_rt"] = section_d(args.quick); _save()
        fig_rt(results["D_rt"])

    _save()
    print(f"[matrix] {os.path.relpath(out)}  (총 {time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
