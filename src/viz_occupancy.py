# -*- coding: utf-8 -*-
"""
viz_occupancy.py — (report2 보강) 점유 상태 '리소스 그리드 사진' + 점유 실험
=============================================================================
생성물 (outputs/figures/)
  report2_grids_<std>.png   : 표준별 G1/G2/G3 리소스 그리드 사진(채널 색칠)
  report2_occupancy.png     : 점유모드 실험 — 거리프로파일 + 점유율/에너지/분해능/SNR
사진 = 시간(OFDM 심볼) × 주파수(부반송파) 격자에서 각 자원요소(RE)가 어떤
채널(SSB/PRS/CRS/DMRS/PDCCH/PDSCH/…)을 싣는지 색으로 표시.
"""
from __future__ import annotations
import os
import numpy as np

import vizstyle
vizstyle.use_korean()
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.patches import Patch

from waveforms import (wifi_80211ac, lte_downlink, nr_downlink, all_waveforms,
                       CH, CH_NAME, CH_COLOR, C0, MODE_DESC)
from rcs_po import drone_rcs_pattern, dbsm
from radar_process import range_profile, mainlobe_width_m
from drones import DRONES

FIG = os.path.join(os.path.dirname(__file__), "..", "outputs", "figures")
_BUILD = {"wifi": wifi_80211ac, "lte": lte_downlink, "nr": nr_downlink}
_TITLE = {"wifi": "WiFi 802.11ac", "lte": "LTE Rel-9", "nr": "5G NR Rel-16"}
# 모드 설명은 표준별로 다르므로 waveforms.MODE_DESC 사용 (단일 소스)
def _mdesc(std, mode):
    return f"{mode} · {MODE_DESC[std][mode]}"
# 사진에 등장하는 채널만 범례로
_LEGEND_CH = ["PSS", "SSS", "PBCH", "PRS", "CRS", "DMRS", "PDCCH", "PDSCH",
              "LSTF", "LLTF", "WSIG", "WDATA"]
_KOR = {"PSS": "PSS(동기)", "SSS": "SSS(동기)", "PBCH": "PBCH(방송=SSB)", "PRS": "PRS(측위기준)",
        "CRS": "CRS(셀기준)", "DMRS": "DMRS(복조기준)", "PDCCH": "PDCCH(제어)", "PDSCH": "PDSCH(데이터)",
        "LSTF": "L-STF", "LLTF": "L-LTF(기준)", "WSIG": "SIG(제어)", "WDATA": "DATA"}


def _grid_image(ax, wf, fmax_show=None):
    """한 파형의 리소스 그리드(라벨)를 사진으로 그린다. y=주파수, x=심볼."""
    L = wf.labels
    fft = wf.fft
    half = len(wf.used) // 2
    lo, hi = fft // 2 - half, fft // 2 + half
    img = L[:, lo:hi].T                      # (nfreq, nsym)
    # 표시 대역 제한(가독성)
    fr = (np.arange(img.shape[0]) - img.shape[0] / 2) * wf.scs_hz / 1e6
    vals = sorted(CH_COLOR.keys())
    cmap = ListedColormap([CH_COLOR[v] for v in vals])
    norm = BoundaryNorm([v - 0.5 for v in vals] + [vals[-1] + 0.5], cmap.N)
    ax.imshow(img, aspect="auto", origin="lower", cmap=cmap, norm=norm,
              extent=[-0.5, img.shape[1] - 0.5, fr[0], fr[-1]], interpolation="nearest")
    ax.set_xlabel("OFDM 심볼", fontsize=8); ax.set_ylabel("기저대역 [MHz]", fontsize=8)
    ax.tick_params(labelsize=7)
    ax.set_title(f"{_mdesc(wf.std, wf.mode)}\n점유율 {wf.occupancy_frac*100:.0f}% · "
                 f"기준 {wf.ref_name} {wf.ref_bw_hz/1e6:.0f}MHz · 분해능 {wf.range_resolution_m:.1f}m",
                 fontsize=8.5)


def fig_resource_grids(std, outdir=FIG):
    """표준 1개의 G1/G2/G3 리소스 그리드 사진 3장 + 범례."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6), constrained_layout=True)
    fig.suptitle(f"리소스 그리드 '사진' — {_TITLE[std]}  (실제 셀은 항상 꽉 차 있지 않다)",
                 fontsize=14, fontweight="bold")
    for ax, mode in zip(axes, ("G1", "G2", "G3")):
        wf = _BUILD[std](occupancy=mode)
        _grid_image(ax, wf)
    # 범례
    present = set()
    for mode in ("G1", "G2", "G3"):
        present |= set(_BUILD[std](occupancy=mode).labels.ravel().tolist())
    handles = [Patch(facecolor=CH_COLOR[CH[c]], edgecolor="0.4", label=_KOR[c])
               for c in _LEGEND_CH if CH[c] in present]
    fig.legend(handles=handles, loc="lower center", ncol=len(handles), fontsize=8.5,
               bbox_to_anchor=(0.5, -0.04))
    fn = os.path.join(outdir, f"report2_grids_{std}.png"); fig.savefig(fn, dpi=130, bbox_inches="tight")
    plt.close(fig); print("[occ]", os.path.relpath(fn)); return fn


def fig_occupancy_experiment(outdir=FIG, target="mavic4pro", R=10.0, snr_db=18.0):
    """점유모드 실험: (a) 5G 거리프로파일 G1/G2/G3, (b~d) 막대 비교."""
    modes = ["G1", "G2", "G3"]; stds = ["wifi", "lte", "nr"]
    fig = plt.figure(figsize=(19, 8.2), constrained_layout=True)
    gs = fig.add_gridspec(2, 4)
    fig.suptitle("점유 상태(occupancy) 실험 — 파일럿만 vs 꽉 찬 신호 (패시브레이더 현실)",
                 fontsize=15, fontweight="bold")

    # (a) 5G NR 거리프로파일: 모드별 (패시브: 기지 파일럿만 상관)
    axA = fig.add_subplot(gs[0, :])
    col = {"G1": "#c62828", "G2": "#ef6c00", "G3": "#2e7d32"}
    for mode in modes:
        wf = nr_downlink(occupancy=mode)
        sig, _ = drone_rcs_pattern(target, wf.carrier_hz, np.array([0.0])); sig = float(sig[0])
        rm, prof, pr, pv = range_profile(wf, R, sig, snr_db=snr_db, passive=True,
                                         rng=np.random.default_rng(5))
        pdb = 20 * np.log10(prof / prof.max() + 1e-12)
        res = mainlobe_width_m(rm, prof)
        axA.plot(rm, pdb, color=col[mode], lw=1.7,
                 label=f"{_mdesc('nr', mode)}  → 분해능≈{res:.1f}m")
    axA.axvline(R, color="k", ls="--", lw=1, label=f"실제 거리 {R:.0f}m")
    axA.set_xlim(0, 2 * R + 5); axA.set_ylim(-40, 2)
    axA.set_xlabel("거리 [m]"); axA.set_ylabel("정합필터 출력 [dB]")
    axA.set_title("(a) 5G NR — 기지 파일럿만으로 측정 시 점유모드별 거리 프로파일\n"
                  "(G1=SSB만→협대역→거리 흐릿 / G2~G3=PRS→광대역→날카로움)", fontsize=11)
    axA.legend(fontsize=9); axA.grid(alpha=0.3)

    # (b) 점유율  (c) 송신에너지  (d) 거리분해능(현실, 로그)
    metrics = {s: {m: _BUILD[s](occupancy=m) for m in modes} for s in stds}
    x = np.arange(len(stds)); w = 0.26
    labs = [_TITLE[s].replace(" Rel-9", "").replace(" Rel-16", "").replace(" 802.11ac", "") for s in stds]

    axB = fig.add_subplot(gs[1, 0])
    for j, m in enumerate(modes):
        axB.bar(x + (j - 1) * w, [metrics[s][m].occupancy_frac * 100 for s in stds], w, color=col[m], label=m)
    axB.set_xticks(x); axB.set_xticklabels(labs, fontsize=8); axB.set_ylabel("점유율 [%]")
    axB.set_title("(b) 자원 점유율", fontsize=10); axB.legend(fontsize=8); axB.grid(axis="y", alpha=0.3)

    axC = fig.add_subplot(gs[1, 1])
    for j, m in enumerate(modes):
        axC.bar(x + (j - 1) * w, [10 * np.log10(metrics[s][m].tx_energy) for s in stds], w, color=col[m])
    axC.set_xticks(x); axC.set_xticklabels(labs, fontsize=8); axC.set_ylabel("송신 에너지 [dB]")
    axC.set_title("(c) 송신 에너지(↑SNR)", fontsize=10); axC.grid(axis="y", alpha=0.3)

    axD = fig.add_subplot(gs[1, 2])
    for j, m in enumerate(modes):
        axD.bar(x + (j - 1) * w, [metrics[s][m].range_resolution_m for s in stds], w, color=col[m])
    axD.set_xticks(x); axD.set_xticklabels(labs, fontsize=8); axD.set_ylabel("거리분해능 [m]")
    axD.set_yscale("log"); axD.set_title("(d) 거리분해능 ←기준신호 대역(주파수축)", fontsize=10); axD.grid(axis="y", alpha=0.3)

    # (e) 최대 무모호 속도 ← 기준신호 반복률(시간축) v_max=PRF·λ/4
    axE = fig.add_subplot(gs[1, 3])
    for j, m in enumerate(modes):
        axE.bar(x + (j - 1) * w, [metrics[s][m].v_unambiguous_ms for s in stds], w, color=col[m])
    for key in ("mavic4pro", "mini5pro"):                 # 일반 드론 최고속도 기준선
        sp = DRONES[key].max_speed_ms
        axE.axhline(sp, ls="--", lw=1, color="0.4", alpha=0.7)
    axE.text(len(stds)-1, DRONES["mavic4pro"].max_speed_ms*1.05, "일반 드론 19~25m/s",
             fontsize=7.5, color="0.35", ha="right", va="bottom")
    axE.set_xticks(x); axE.set_xticklabels(labs, fontsize=8); axE.set_ylabel("최대속도 v_max [m/s]")
    axE.set_yscale("log"); axE.set_title("(e) 최대 무모호 속도 ←반복률(시간축)", fontsize=10); axE.grid(axis="y", alpha=0.3)

    fn = os.path.join(outdir, "report2_occupancy.png"); fig.savefig(fn, dpi=130); plt.close(fig)
    print("[occ]", os.path.relpath(fn)); return fn


def build_all(outdir=FIG):
    for std in ("wifi", "lte", "nr"):
        fig_resource_grids(std, outdir)
    fig_occupancy_experiment(outdir)
    print("점유 시각화 완료 →", os.path.relpath(outdir))


if __name__ == "__main__":
    build_all()
