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
  B) 신호×드론     : {5G100, WiFi80, LTE20, LTE10} × 드론 **전 기종** × radial, 고정 EIRP.
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

실행:  /workspace/.venvs/py312/bin/python run_matrix.py            (전체, ~수 분)
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
from bistatic_scene import C0, bistatic_params                   # noqa: E402
from link_budget import LinkBudget                               # noqa: E402
from channel import AnalyticChannel, sbr_sigma_prefill, rt_chamber_clutter  # noqa: E402
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
#  벤치 B 섹션의 드론 행 — **레지스트리에서 유도**한다(2026-07-30 Phase 3).
#  ⭐ 예전 이름은 `DRONES5` 였고 값도 5종 하드코딩이라, 기종을 추가해도 **에러 없이**
#     신규 기체가 신호×드론 행렬에서 빠졌다(이름 자체가 개수를 박아 놓아 더 안 고쳐졌다).
#     앞머리는 옛 '크기 내림차순' 순서를 유지하고 레지스트리의 나머지가 뒤에 붙는다.
#  ⚠ 개수를 세야 하면 `len(BENCH_DRONES)`. 상수 5 를 쓰지 말 것.
from drones import drone_order as _drone_order, drone_label as _drone_label   # noqa: E402
BENCH_DRONES = _drone_order(("s1000plus", "phantom4", "matrice4e", "mavic4pro", "mini5pro"))
SNAPS = [0, 4, 8, 13, 17, 22, 26, 31]     # C 섹션이 평가하는 궤적 스냅샷 (σ 프리필과 공유)

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


# --- 환경(정적 잔향) = **RT 실측** (캐시). 없으면 옛 가정치로 폴백 ------------------
#  ※ 정적 클러터는 죽은 파라미터라 수치는 안 바뀐다 — 이건 **정직함**의 문제다(§D).
_ENV_CACHE: dict = {}


def env_clutter(fc):
    c = _ENV_CACHE.get(fc)
    if c is None:
        c = rt_chamber_clutter(fc) or CH_CLUTTER_RATIO      # 캐시 히트 or 폴백
        _ENV_CACHE[fc] = c
    return c


def _job_pos_vel(job):
    """job → (pos, vel). **_cell_task 와 σ 프리필이 같은 궤적을 보도록** 단일 진리원."""
    _, _, scen, snap = job[0], job[1], job[2], job[3]
    pos, vel = SCENARIOS[scen](TX, RX, CENTER, speed=SPEED, span=SPAN, n=32)
    if snap is not None:                       # 궤적 특정 스냅샷 1개만 평가
        pos, vel = pos[snap:snap + 1], vel[snap:snap + 1]
    return pos, vel


def prefill_sigma(jobs, verbose=True):
    """모든 셀의 **대표 스냅샷 시선각**을 모아 SBR σ 를 GPU 로 미리 계산해 캐시에 넣는다.
    (run_cell 은 궤적 중앙 스냅샷 1개에서 링크텀을 유도한다 → 셀당 시선 1개.)
    ⚠ **mitsuba import 전에** 부를 것 — parallel_over_gpus 가 fork 로 GPU 를 나눠 잡는다."""
    reqs = []
    for job in jobs:
        (std, bw, carrier, occ), drone = job[0], job[1]
        pos, vel = _job_pos_vel(job)
        mid = len(pos) // 2
        p = bistatic_params(TX, RX, pos[mid], vel[mid], carrier)
        reqs.append((drone, carrier, p["u1"], p["u2"], 8.0, 5))    # AnalyticChannel 기본 자세평균
    return sbr_sigma_prefill(reqs, verbose=verbose)


def _worker_init():
    """워커는 **GPU 를 건드리지 않는다** — σ 는 캐시 조회만(미스는 큰 소리로 실패)."""
    os.environ["SIONNA2_NO_GPU"] = "1"


def _cell_task(job):
    """워커 프로세스에서 셀 1개 실행 → 직렬화 가능한 요약 dict.
    job: (wf_spec(std,bw,carrier,occ), drone, scen, snap|None, eirp_dbm, N, pref_occ, ghost)
    pref_occ: 전력 정규화 기준 점유(예: 'G1' 셀에 'G3' — per-RE 전력 동일 가정). None=자기 자신.
    ghost   : True 면 **표적 경유 바닥 유령**(도플러 실림 → ECA 통과)을 주입."""
    (std, bw, carrier, occ), drone, scen, snap, eirp, N, pref_occ, ghost = job
    wf = make_wf(std, bw, carrier, occ)
    pref_tx = make_wf(std, bw, carrier, pref_occ).tx if pref_occ else None
    lb = LinkBudget(eirp_dbm=eirp)
    ch = AnalyticChannel(clutter=env_clutter(carrier))     # σ=SBR(캐시), 잔향=RT 실측
    pos, vel = _job_pos_vel(job)
    res = run_cell(wf, drone, pos, vel, lb, channel=ch, power_ref_tx=pref_tx,
                   M=m_for(wf), N=N, pfa=PFA, floor_ghost_on=ghost,
                   seed0=_seed(std, bw, occ, drone, scen, snap, eirp))
    st, lt = res["state"], res["link"]
    g = res.get("ghost")
    return dict(wf=f"{std}{bw/1e6:.0f}", occ=occ, drone=drone, scen=scen, snap=snap,
                eirp_dbm=eirp, N=N, M=res["M"], ghost_on=bool(ghost),
                pd=res["pd"], pd_lo=res["pd_lo"], pd_hi=res["pd_hi"],
                scr_db=res["scr_mean"], scr_std=res["scr_std"],
                rb_err_m=res["rb_err_m"],
                sigma_dbsm=float(10 * np.log10(st.sigma_m2)),
                snr_echo_db=lt["snr_echo_db"], dnr_db=lt["dnr_db"],
                snr_echo_eff_db=res["snr_echo_eff_db"],   # 점유차+잡음대역 보정 반영(실주입)
                fd_hz=st.fd, rb_m=st.tau * C0, delta_rb_m=C0 / wf.bw_hz,
                ref_bw_mhz=wf.ref_bw_hz / 1e6, occupancy_frac=wf.occupancy_frac,
                n_clutter=len(st.clutter),
                p_false=(g["p_false"] if g else None),
                p_ghost_det=(g["p_det"] if g else None),
                ghost_margin_db=(g["margin_db"] if g else None),
                ghost_bins_apart=(str(g["bins_apart"]) if g else None),
                ghost_sep_m=(g["sep_m"] if g else None),
                ghost_amp_db=(g["amp_db"] if g else None),
                ghost_fd_hz=(g["fd"] if g else None),
                ghost_resolved=(g["resolved"] if g else None))


def _run_jobs(jobs, workers, tag):
    t0 = time.time()
    if workers <= 1:
        out = [_cell_task(j) for j in jobs]     # 직렬 실행은 메인 프로세스(캐시 미스 시 SBR 가능)
    else:
        with ProcessPoolExecutor(max_workers=workers, initializer=_worker_init) as ex:
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
            f"[2] Derived (physics)\nRCS = SBR (rays + PO integral,\nself-shadowing included)\n"
            f"R1={p['R1']:.0f}m R2={p['R2']:.0f}m\n$\\rightarrow$ echo SNR",
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
    for x, t in [(1.25, "Fixed budget\nEIRP·G_rx·NF"), (3.4, "Target RCS\n(SBR, occluded)"),
                 (5.55, "Geometry\n(Sionna RT / closed-form)"), (7.7, "Noise\nkTFB")]:
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
    axf.text(4.5, 0.95, "SCR·Pd·position error = measured  →  A occupancy · B signal×drone · C motion · "
             "E floor ghost · D RT cross-check",
             ha="center", fontsize=9.3, bbox=box_out, fontweight="bold")
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
    jobs = [(("nr", 100e6, 3.5e9, occ), "mavic4pro", "radial", None, e, N, "G3", False)
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
    ax.set_title("Occupancy fairness — same 5G 100MHz, yet what is 'on' (grids above) drives Pd (semi-anechoic chamber)\n"
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
    jobs = [((std, bw, car, "G3"), d, "radial", None, EIRP_DBM, N, None, False)
            for wfk, (std, bw, car) in WAVEFORMS.items() for d in BENCH_DRONES]
    rows = _run_jobs(jobs, workers, "B 신호×드론")
    # **옛 엔진(순수 PO, 가림 없음) σ 를 같은 시선각에서 함께 재서 기록**한다 —
    #   노트북이 "가림이 σ 를 얼마나 내렸나"를 수기 수치 없이 인용할 수 있도록.
    po = AnalyticChannel(rcs_engine="po")
    for job, r in zip(jobs, rows):
        (std, bw, car, occ), drone = job[0], job[1]
        pos, vel = _job_pos_vel(job)
        mid = len(pos) // 2
        st = po.state(TX, RX, pos[mid], vel[mid], car, drone)
        r["sigma_po_dbsm"] = float(10 * np.log10(st.sigma_m2))
        r["occlusion_db"] = r["sigma_dbsm"] - r["sigma_po_dbsm"]
    d = [r["occlusion_db"] for r in rows]
    print(f"  [B] 가림(SBR−PO) 효과: 평균 {np.mean(d):+.1f} dB  (중앙값 {np.median(d):+.1f}, "
          f"범위 {min(d):+.1f}~{max(d):+.1f})")
    return dict(N=N, rows=rows, occlusion_db_mean=float(np.mean(d)),
                occlusion_db_median=float(np.median(d)))


def write_csv(b, path=os.path.join(OUTDIR, "bench_matrix.csv"), ghost=False):
    cols = ["wf", "occ", "drone", "scen", "eirp_dbm", "sigma_dbsm", "sigma_po_dbsm",
            "occlusion_db",
            "snr_echo_db", "snr_echo_eff_db", "dnr_db", "delta_rb_m", "rb_m", "fd_hz",
            "scr_db", "scr_std", "pd", "pd_lo", "pd_hi", "rb_err_m", "M", "N"]
    if ghost:
        cols += ["ghost_on", "p_ghost_det", "ghost_margin_db", "p_false", "ghost_bins_apart",
                 "ghost_sep_m", "ghost_amp_db", "ghost_fd_hz", "ghost_resolved"]
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
    P = np.zeros((len(BENCH_DRONES), len(wfs)))
    S = np.zeros_like(P)
    for r in b["rows"]:
        i = BENCH_DRONES.index(r["drone"])
        j = [f"{s}{bw/1e6:.0f}" for s, bw, c in WAVEFORMS.values()].index(r["wf"])
        P[i, j] = r["pd"]; S[i, j] = r["scr_db"]
    E = np.zeros_like(P)                                   # 위치오차 [m]
    for r in b["rows"]:
        i = BENCH_DRONES.index(r["drone"])
        j = [f"{s}{bw/1e6:.0f}" for s, bw, c in WAVEFORMS.values()].index(r["wf"])
        E[i, j] = r["rb_err_m"] if r["rb_err_m"] is not None else np.nan

    # 왼쪽에 드론 3D 메쉬 썸네일 열 — '행이 어떤 드론인지' 보이게 (report2 스타일)
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    from drones import build_drone, drone_colors
    # 높이는 **행 수에서 유도** — 고정 7.0 이면 기종이 늘 때 셀이 짜부라진다.
    fig = plt.figure(figsize=(13.6, 1.4 * len(BENCH_DRONES)), constrained_layout=True)
    gs = fig.add_gridspec(len(BENCH_DRONES), 2, width_ratios=[1.0, 5.6])
    for i, key in enumerate(BENCH_DRONES):
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
    dr_lab = [f"{_drone_label(k)}\n(diag {DRONES[k].diagonal_mm:.0f} mm)"
              for k in BENCH_DRONES]
    # 분해능 라벨은 실제 점유대역 기준(wf.bw_hz) — 본문/CSV 의 delta_rb_m 과 동일 규약
    wf_lab = [f"{k}\nres {C0/make_wf(*WAVEFORMS[k]).bw_hz:.0f} m" for k in wfs]
    ax.set_xticks(range(len(wfs)), wf_lab, fontsize=9)
    ax.set_yticks(range(len(BENCH_DRONES)), dr_lab, fontsize=9)
    ax.set_title("Signal × drone matrix — fixed budget (EIRP %.0f dBm) · radial · G3 · $\\sigma$ from SBR (rays + PO integral, self-shadowing included)\n"
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
    snaps = SNAPS
    jobs = [(("nr", 100e6, 3.5e9, "G3"), "mavic4pro", scen, s, EIRP_DBM, N, None, False)
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
#  E) **유령을 켠 매트릭스** — 표적 경유 바닥 유령(TX→표적→바닥→RX)
# --------------------------------------------------------------------------- #
#  이것이 report5 의 진짜 질문이다. 정적 클러터는 ECA 가 진폭과 무관하게 지운다(죽은 파라미터).
#  그러나 **표적을 거쳐 바닥에 반사되는 경로는 표적과 함께 도플러가 실린다** → ECA 의 영공간
#  밖 → 지워지지 않고 RD 맵에 **가짜 표적**으로 남는다. 그리고 **대역폭이 넓을수록 진짜와 잘
#  분리되어 별개 표적으로 보인다** — §B 에서 광대역의 장점이었던 '거리축 분리'가 그대로
#  오검출로 되돌아온다. Pd 는 안 떨어지는데 **P(가짜표적)** 이 올라간다.
def _rdmap(res):
    Rb, f_d, rd, st, lt, (ri, di), true_Rb = res["example"]
    rdb = 20 * np.log10(rd / rd.max() + 1e-9)
    return dict(rb=np.asarray(Rb).round(2).tolist(),
                fd=np.asarray(f_d).round(1).tolist(),
                rd_db=np.asarray(rdb).round(1).tolist(),
                true_rb=float(true_Rb), true_fd=float(st.fd))


def section_e(workers, quick=False):
    N = 30 if quick else 100
    jobs = [((std, bw, car, "G3"), d, "radial", None, EIRP_DBM, N, None, gh)
            for std, bw, car in WAVEFORMS.values() for d in BENCH_DRONES
            for gh in (False, True)]
    rows = _run_jobs(jobs, workers, "E 유령 off/on")
    # 예시 RD맵 1장(5G100 × mavic4pro, 유령 on) — 메인 프로세스에서 example 을 받는다
    wf = make_wf("nr", 100e6, 3.5e9, "G3")
    pos, vel = SCENARIOS["radial"](TX, RX, CENTER, speed=SPEED, span=SPAN, n=32)
    ex = run_cell(wf, "mavic4pro", pos, vel, LinkBudget(eirp_dbm=EIRP_DBM),
                  channel=AnalyticChannel(clutter=env_clutter(3.5e9)),
                  M=m_for(wf), N=4, pfa=PFA, floor_ghost_on=True, seed0=_seed("ghost-ex"))
    g = ex["ghost"]
    return dict(N=N, rows=rows, map=_rdmap(ex),
                ghost=dict(rb_m=g["rb_m"], fd=g["fd"], sep_m=g["sep_m"],
                           amp_db=g["amp_db"], gamma=g["gamma"],
                           theta_i_deg=g["theta_i_deg"], p_det=g["p_det"],
                           p_false=g["p_false"], margin_db=g["margin_db"],
                           bins_apart=list(g["bins_apart"]), d_rb_m=g["d_rb_m"],
                           resolved=g["resolved"]))


def fig_ghost(e, outdir=FIGDIR):
    """좌: 유령이 보이는 RD맵. 중: P(가짜표적) — 대역폭이 넓을수록 유령이 '분리'된다.
    우: Pd 는 그대로다(탐지는 안 죽는다 — 죽는 건 신뢰다)."""
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(16.8, 5.4), constrained_layout=True,
                             gridspec_kw=dict(width_ratios=[1.2, 1.0, 1.0]))
    g = e["ghost"]
    wfs = list(WAVEFORMS.keys())

    # (a) RD 맵 — 진짜 표적 옆에 유령
    m = e["map"]
    Rb = np.asarray(m["rb"]); fd = np.asarray(m["fd"]); rdb = np.asarray(m["rd_db"])
    ax = axes[0]
    im = ax.pcolormesh(Rb, fd, rdb, cmap="turbo", vmin=-50, vmax=0, shading="auto")
    ax.plot(m["true_rb"], m["true_fd"], "o", mfc="none", mec="w", ms=15, mew=1.8,
            label="True target")
    ax.plot(g["rb_m"], g["fd"], "s", mfc="none", mec="#ff1744", ms=15, mew=1.8,
            label="Floor ghost (via target)")
    ax.annotate("", xy=(g["rb_m"], g["fd"]), xytext=(m["true_rb"], m["true_fd"]),
                arrowprops=dict(arrowstyle="<->", color="w", lw=1.4))
    ax.text((g["rb_m"] + m["true_rb"]) / 2, m["true_fd"] - 62,
            f"$\\Delta$Rb = {g['sep_m']:+.2f} m", color="w", fontsize=9.5, ha="center")
    # 유령이 보이도록 표적 근방으로 확대 (전체 축이면 유령이 표적 픽셀에 묻힌다)
    ax.set_xlim(max(0.0, m["true_rb"] - 14), m["true_rb"] + 16)
    ax.set_ylim(m["true_fd"] - 190, m["true_fd"] + 190)
    ax.set_xlabel("Bistatic range Rb [m]  (zoomed on the target)")
    ax.set_ylabel("Doppler f_d [Hz]")
    ax.set_title(f"(a) 5G 100MHz — the ghost survives ECA\n"
                 f"TX-target-floor-RX: {g['amp_db']:.1f} dB below the echo, "
                 f"it carries Doppler ({g['fd']:+.0f} Hz)", fontsize=10.5)
    ax.legend(loc="upper right", fontsize=8.5)
    fig.colorbar(im, ax=ax, fraction=0.046, label="Normalized [dB]")

    # (b) 분해능 vs 유령 분리거리 — 유령이 '별개 표적'이 되는가는 오직 ΔRb 가 정한다.
    #     ※ merged 인 파형에서는 '유령 셀' = '표적 셀' 이라 CFAR 여유를 재봐야 표적을 다시
    #        재는 것일 뿐이다(무의미). 그래서 여유(dB)는 **resolved 인 경우에만** 표기한다.
    ax = axes[1]
    sep = abs(g["sep_m"])
    drb, marg, pdet, res_flag = [], [], [], []
    for k in wfs:
        std, bw, car = WAVEFORMS[k]
        rr = [r for r in e["rows"] if r["ghost_on"] and r["wf"] == f"{std}{bw/1e6:.0f}"]
        drb.append(C0 / make_wf(*WAVEFORMS[k]).bw_hz)
        marg.append(float(np.mean([r["ghost_margin_db"] for r in rr])))
        pdet.append(float(np.mean([r["p_ghost_det"] for r in rr])))
        res_flag.append(bool(np.all([r["ghost_resolved"] for r in rr])))
    cols = ["#c62828" if f else "#78909c" for f in res_flag]
    ax.bar(range(len(wfs)), drb, color=cols, width=0.62)
    ax.axhline(sep, color="#1a1a1a", lw=1.6, ls="--")
    ax.text(len(wfs) - 0.42, sep + 1.0, f"ghost is {sep:.2f} m from the target",
            ha="right", fontsize=8.5, color="#1a1a1a")
    tr = ax.get_xaxis_transform()          # x=데이터, y=축비율 → 축 아래에 라벨
    for i, k in enumerate(wfs):
        ax.text(i, drb[i] + 1.0, f"$\\Delta$Rb = {drb[i]:.1f} m", ha="center", fontsize=9)
        if res_flag[i]:
            ax.text(i, -0.10, f"RESOLVED\n$\\rightarrow$ phantom drone\n"
                    f"{marg[i]:+.1f} dB over CFAR\nP(det) = {pdet[i]*100:.0f}%",
                    transform=tr, ha="center", va="top", fontsize=8.5,
                    color="#c62828", fontweight="bold")
        else:
            ax.text(i, -0.10, "merged into\nthe target cell\n(no phantom, but\nthe echo is corrupted)",
                    transform=tr, ha="center", va="top", fontsize=8.5, color="#546e7a")
    ax.set_xticks(range(len(wfs)), wfs, fontsize=9.5)
    ax.set_ylim(0, 42)
    ax.set_ylabel("Range resolution $\\Delta$Rb = c/B [m]")
    ax.set_title("(b) Only the bandwidth that resolves the ghost\nturns it into a second 'drone'", fontsize=10.5)
    ax.grid(alpha=0.3, axis="y", which="both")

    # (c) Pd 는 그대로 — 무너지는 건 신뢰(가짜 표적/거리 편향)
    ax = axes[2]
    x = np.arange(len(wfs))
    err = {}
    for j, (gh, col, lab) in enumerate([(False, "#2e7d32", "ghost off"),
                                        (True, "#ef6c00", "ghost on")]):
        y = []
        for k in wfs:
            std, bw, car = WAVEFORMS[k]
            rr = [r for r in e["rows"] if r["ghost_on"] == gh and r["wf"] == f"{std}{bw/1e6:.0f}"]
            y.append(float(np.mean([r["pd"] for r in rr])) * 100)
            err[(k, gh)] = float(np.mean([r["rb_err_m"] for r in rr if r["rb_err_m"] is not None]))
        ax.bar(x + (j - 0.5) * 0.34, y, width=0.32, color=col, label=lab)
    for i, k in enumerate(wfs):
        ax.text(i, 104, f"peak range err\n{err[(k, False)]:.2f} $\\rightarrow$ {err[(k, True)]:.2f} m",
                ha="center", fontsize=8, color="#37474f")
    ax.set_xticks(x, wfs, fontsize=9.5)
    ax.set_ylim(0, 128); ax.set_ylabel("Detection probability Pd [%] (drone-averaged)")
    ax.set_title("(c) Pd is untouched — what breaks is trust,\nnot detection", fontsize=10.5)
    ax.legend(fontsize=9, loc="lower right"); ax.grid(alpha=0.3, axis="y")

    fig.suptitle("Ghost matrix — the floor ghost goes via the target, so it carries Doppler and ECA cannot cancel it",
                 fontsize=13, fontweight="bold")
    fig.supxlabel(f"Static clutter is a dead parameter (ECA projects it out). The target-borne floor ghost is not: {g['amp_db']:.0f} dB below the echo, "
                  f"it still stands {marg[0]:+.0f} dB above the CFAR threshold at 5G.\n"
                  "The range resolution that made wideband attractive is exactly what turns the ghost into a second 'drone'; narrowband merely hides it inside the target cell. "
                  "Pd never moves — what the ghost costs is trust in the detection.",
                  fontsize=9.5, color="0.35")
    fn = os.path.join(outdir, "report5_ghost.png")
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

    # 3) 같은 셀을 RT 채널(경로를 광선추적으로)로 재실행 vs Analytic(닫힌형 기하).
    #    ⚠ **두 백엔드의 σ 는 이제 둘 다 SBR 이다** — 다른 것은 '환경 경로'뿐이다.
    #    그리고 정적 클러터는 ECA 가 진폭과 무관하게 지운다(죽은 파라미터) → 일치는 **항등식**.
    #    즉 이 비교는 클러터 모델을 검증하지 **못한다**. 검증하는 것은 기하·직접파·지연이다.
    res_rt = run_cell(wf, "mavic4pro", pos, vel, lb,
                      channel=SionnaRTChannel(with_chamber=True, spp=spp),
                      M=m_for(wf), N=N, pfa=PFA, seed0=_seed("rt-cell"))
    res_an = run_cell(wf, "mavic4pro", pos, vel, lb,
                      channel=AnalyticChannel(clutter=env_clutter(wf.carrier_hz)),
                      M=m_for(wf), N=N, pfa=PFA, seed0=_seed("rt-cell"))
    out["cell"] = dict(
        rt=dict(pd=res_rt["pd"], scr=res_rt["scr_mean"], n_clutter=len(res_rt["state"].clutter),
                sigma_dbsm=float(10 * np.log10(res_rt["state"].sigma_m2)), map=_rdmap(res_rt)),
        analytic=dict(pd=res_an["pd"], scr=res_an["scr_mean"],
                      n_clutter=len(res_an["state"].clutter),
                      sigma_dbsm=float(10 * np.log10(res_an["state"].sigma_m2)),
                      map=_rdmap(res_an)),
        N=N)

    # 4) **클러터가 죽은 파라미터임을 이 자리에서 증명한다** — 잔향 진폭을 ×0 / ×1 / ×10 로
    #    바꿔도 SCR 이 소수점 아래까지 안 움직인다(ECA 사영이 지운다). "RT≈Analytic 이므로
    #    클러터 모델이 검증됐다"는 옛 결론이 왜 공허했는지의 근거.
    dead = []
    for scale, tag in ((0.0, "none"), (1.0, "RT-measured"), (10.0, "RT x10")):
        cl = tuple((dt, r * scale) for dt, r in st_c.clutter) if scale else ()
        r = run_cell(wf, "mavic4pro", pos, vel, lb, channel=AnalyticChannel(clutter=cl),
                     M=m_for(wf), N=4, pfa=PFA, seed0=_seed("dead"))
        dead.append(dict(tag=tag, scale=scale, scr=r["scr_mean"], pd=r["pd"]))
    out["clutter_dead"] = dead
    print(f"  [D RT] 자유공간 클러터={out['free']['n_clutter']}  "
          f"챔버 잔향 {len(out['chamber_clutter'])}개  "
          f"Pd RT={res_rt['pd']*100:.0f}% vs Analytic={res_an['pd']*100:.0f}%  "
          f"SCR RT={res_rt['scr_mean']:.1f} vs {res_an['scr_mean']:.1f} dB")
    print("  [D RT] 클러터 죽은 파라미터 증명: " +
          "  ".join(f"{d['tag']}→SCR {d['scr']:.6f}dB" for d in dead))
    return out


def fig_rt(d, outdir=FIGDIR):
    """좌·중: 같은 셀의 RD맵 — Analytic(가정 잔향) vs Sionna RT(광선추적 실측 잔향).
    우: 챔버 잔향 스펙트럼(RT 실측 vs 가정) — 두 백엔드가 일치함을 눈으로 확인."""
    import matplotlib.pyplot as plt
    have_maps = "map" in d["cell"]["rt"]
    if have_maps:
        fig, axes = plt.subplots(1, 3, figsize=(16.5, 5.4), constrained_layout=True,
                                 gridspec_kw=dict(width_ratios=[1.15, 1.15, 1.0]))
        for ax, key, tag in [(axes[0], "analytic", "Analytic paths (closed-form geometry) + SBR $\\sigma$"),
                             (axes[1], "rt", "Sionna RT paths (ray-traced chamber) + SBR $\\sigma$")]:
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
    ax.set_title("Chamber reverberation\nRT-measured vs the old assumption", fontsize=10.5)
    ax.set_ylim(-58, 4)
    ax.grid(alpha=0.3); ax.legend(fontsize=8.5, loc="lower right")
    dead = d.get("clutter_dead")
    if dead:
        txt = "\n".join(f"  clutter {x['tag']:<12s} SCR {x['scr']:.6f} dB" for x in dead)
        ax.text(0.03, 0.97, "Static clutter is a DEAD parameter\n(ECA projects it out; SCR identical to 6 decimals)\n" + txt,
                transform=ax.transAxes, va="top", ha="left", fontsize=8,
                family="monospace", color="#37474f",
                bbox=dict(boxstyle="round,pad=0.35", fc="#eceff1", ec="#90a4ae"))
    fig.suptitle("Sionna RT cross-check — what it does and does NOT prove",
                 fontsize=12.5, fontweight="bold")
    fig.supxlabel(f"It proves the geometry, the direct path and the delays (RT and closed-form agree; "
                  f"{d['free']['n_clutter']} clutter paths in free space).\n"
                  "It does NOT validate the clutter model: ECA cancels static clutter regardless of its amplitude, so any clutter model would have 'agreed'.",
                  fontsize=9.5, color="0.35")
    fn = os.path.join(outdir, "report5_rt_clutter.png")
    fig.savefig(fn, dpi=130); plt.close(fig)
    print("[matrix]", os.path.relpath(fn)); return fn


# --------------------------------------------------------------------------- #
def _rt_env_worker(fcs):
    """자식 프로세스에서 RT 실측 잔향을 뽑아 캐시에 쓴다 — **부모는 mitsuba 를 import 하지
    않는다**(부모가 CUDA 컨텍스트를 만들면 이후 ProcessPool fork 가 위험해진다)."""
    from channel import rt_chamber_clutter
    for fc in fcs:
        rt_chamber_clutter(fc, compute=True)
    return True


def prep_env(carriers, verbose=True):
    """반송파별 RT 실측 챔버 잔향을 캐시에 채운다(이미 있으면 건너뜀)."""
    need = [fc for fc in carriers if not rt_chamber_clutter(fc)]
    if not need:
        if verbose:
            print("[RT] 챔버 잔향 캐시 적중 — 다시 광선추적하지 않음")
        return
    if verbose:
        print(f"[RT] 챔버 잔향 실측 {len(need)}개 반송파 (Sionna RT, GPU)")
    with ProcessPoolExecutor(max_workers=1) as ex:
        ex.submit(_rt_env_worker, need).result()
    _ENV_CACHE.clear()
    import channel as _ch
    _ch._RTC = None                       # 자식이 쓴 캐시를 부모가 다시 읽게 한다


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="빠른 점검(셀·trial 축소)")
    ap.add_argument("--only", default="a,b,c,d,e", help="실행 섹션 (예: a,b)")
    ap.add_argument("--workers", type=int, default=min(12, os.cpu_count() or 4))
    ap.add_argument("--replot", action="store_true",
                    help="계산은 건너뛰고 캐시된 report5_results.json 으로 그림만 다시 그린다 "
                         "(제목·캡션 문구만 고쳤을 때 — 몬테카를로 수 분을 아낀다)")
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

    if args.replot:                             # 캐시된 결과로 그림만 재생성
        have = {"a": ("A_occupancy", fig_occupancy), "b": ("B_matrix", fig_matrix),
                "c": ("C_scenarios", fig_scenarios), "d": ("D_rt", fig_rt),
                "e": ("E_ghost", fig_ghost)}
        for s in ("a", "b", "c", "d", "e"):
            if s in only:
                key, fn = have[s]
                if key not in results:
                    raise SystemExit(f"[matrix] --replot 불가: {out} 에 {key} 없음 — 먼저 계산을 돌리세요.")
                fn(results[key])
        print(f"[matrix] replot 완료 ({time.time()-t0:.0f}s) — 계산은 건너뜀")
        return

    # ---- 준비 1: 표적 σ 를 **SBR(가림 포함)** 로 미리 계산해 캐시 (GPU 여러 장에 분배) ----
    #      ⚠ 반드시 mitsuba import 전에. 워커는 이 표를 조회만 한다(SIONNA2_NO_GPU).
    pre = []
    if "a" in only:
        pre += [(("nr", 100e6, 3.5e9, "G3"), "mavic4pro", "radial", None)]
    if {"b", "d", "e"} & only:
        pre += [((std, bw, car, "G3"), d, "radial", None)
                for std, bw, car in WAVEFORMS.values() for d in BENCH_DRONES]
    if "c" in only:
        pre += [(("nr", 100e6, 3.5e9, "G3"), "mavic4pro", scen, s)
                for scen in ("radial", "waypoint", "tangential", "hover") for s in SNAPS]
    prefill_sigma(pre)

    # ---- 준비 2: 환경(정적 잔향) = **Sionna RT 실측** (반송파별 1회, 자식 프로세스) ----
    prep_env(sorted({car for _, _, car in WAVEFORMS.values()}))

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
    if "e" in only:
        results["E_ghost"] = section_e(args.workers, args.quick); _save()
        write_csv(results["E_ghost"], os.path.join(OUTDIR, "bench_ghost.csv"), ghost=True)
        fig_ghost(results["E_ghost"])
    if "d" in only:                             # RT 는 **맨 마지막** (부모가 mitsuba 를 물고 나면
        results["D_rt"] = section_d(args.quick); _save()   # 이후 fork 가 위험하다)
        fig_rt(results["D_rt"])

    _save()
    print(f"[matrix] {os.path.relpath(out)}  (총 {time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
