# -*- coding: utf-8 -*-
"""
build_passive_figs.py — 패시브 2채널 실험(outputs/passive_two_channel.json)의 그림들.

⭐ 그림 1 — **기준채널 품질 사다리**
    질문:  «기준채널이 현실적이면(잡음·다중경로) 패시브 검출은 얼마를 잃는가»
    답:    잡음축은 **절벽**, 다중경로축은 **평지**다. 그 대비가 이 그림의 전부다.

무엇을 어디서 읽나 — 손으로 적은 수치는 하나도 없다
    E1[*].rows            팔(arm)마다 axis_value · loss_db · pd  (그림의 모든 점)
    summary[mode]         loss_db_by_refsnr · pd_by_refsnr · loss_db_by_mdr (교차검증용)
                          ref_snr_needed_for_3db_loss · ref_antenna_gain_needed_db
    E1[*].ref_name/ref_bw_mhz   범례 이름

읽는 것: outputs/passive_two_channel.json   (원장 — 절대 안 건드린다)
쓰는 것: outputs/figures/passive_f1.{png,pdf}

표시 규약
    · 그림 안 글자는 전부 영어(하우스 규약).
    · 설정값(CPI·Pfa·M·n_taps 등)은 그림에 안 적는다 — 리포트 본문이 담는다.
    · 두 패널은 **세로 눈금을 공유**한다. 공유하지 않으면 «절벽 vs 평지» 가 사라진다.
    · 색은 dataviz 팔레트 슬롯 1~3(주황·파랑·청록) — 최근 판(vmax_grid.py)과 같은 배정.
      표식 모양(o/s/^)을 2차 부호로 얹어 색각 이상에서도 갈린다.
    · 표식 채움 = Pd. 꽉 참 = 1.00, 빈 것 = 0.00, 중간은 섞인 색(아래 Pd 띠에 숫자로도 적는다).
"""
from __future__ import annotations

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, to_rgb
from matplotlib.lines import Line2D

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LEDGER = f"{ROOT}/outputs/passive_two_channel.json"
FIGDIR = f"{ROOT}/outputs/figures"

# ── 표시 규약 ────────────────────────────────────────────────────────────────
FS = 10.0
plt.rcParams.update({
    "font.size": FS, "axes.labelsize": FS, "axes.titlesize": FS,
    "xtick.labelsize": FS - 1, "ytick.labelsize": FS - 1, "legend.fontsize": FS - 1.5,
    "axes.linewidth": 0.9, "figure.dpi": 200, "savefig.dpi": 200,
    "font.family": "DejaVu Sans",
})

# dataviz 팔레트 슬롯 1~3 — 세 계열은 all-pairs 게이트를 통과하는 조합이다.
COL = {"wifi": "#eb6834", "lte": "#2a78d6", "nr": "#1baf7a"}
MARK = {"wifi": "o", "lte": "s", "nr": "^"}
STD_NAME = {"wifi": "WiFi", "lte": "LTE", "nr": "5G NR"}
INK, INK2, INK3 = "#1a1a19", "#4a4a45", "#8a8a82"
C_CLIFF = "#e34948"          # 절벽 음영(상태색 — 계열색으로 안 쓴다)
CMAP_PD = LinearSegmentedColormap.from_list("pd", ["#f4f4f0", "#2b2b28"])


def _blend(c: str, frac: float) -> tuple:
    """흰색 → 계열색을 frac 만큼 섞는다. 표식 채움으로 Pd 를 나타내는 데 쓴다."""
    r, g, b = to_rgb(c)
    f = float(np.clip(frac, 0.0, 1.0))
    return (1 - f + f * r, 1 - f + f * g, 1 - f + f * b)


def _series(led: dict) -> list[dict]:
    """원장에서 파형별 사다리를 뽑는다 — 모든 수치는 여기서만 나온다."""
    out = []
    for e in led["E1"]:
        mode, std = e["mode"], e["std"]
        rows = e["rows"]
        ref = sorted([r for r in rows if r["kind"] == "refsnr"], key=lambda r: r["axis_value"])
        mp = sorted([r for r in rows if r["kind"] == "mp"], key=lambda r: r["axis_value"])
        ideal = [r for r in rows if r["kind"] == "ideal"][0]
        s = led["summary"][mode]

        # 원장의 두 갈래(E1.rows ↔ summary)가 어긋나면 그림을 그리지 않는다.
        for r in ref:
            k = f"+{r['axis_value']:.0f}"
            assert abs(s["loss_db_by_refsnr"][k] - r["loss_db"]) < 1e-6, (mode, k)
            assert abs(s["pd_by_refsnr"][k] - r["pd"]) < 1e-6, (mode, k)
        for r in mp:
            k = f"{r['axis_value']:.0f}"
            assert abs(s["loss_db_by_mdr"][k] - r["loss_db"]) < 1e-6, (mode, k)

        out.append(dict(
            mode=mode, std=std, color=COL[std], marker=MARK[std],
            label=f"{mode} · {STD_NAME[std]} {e['ref_name']} ({e['ref_bw_mhz']:.1f} MHz ref)",
            x_ref=np.array([r["axis_value"] for r in ref], float),
            y_ref=np.array([r["loss_db"] for r in ref], float),
            pd_ref=np.array([r["pd"] for r in ref], float),
            x_mp=np.array([r["axis_value"] for r in mp], float),
            y_mp=np.array([r["loss_db"] for r in mp], float),
            pd_mp=np.array([r["pd"] for r in mp], float),
            pd_ideal=float(ideal["pd"]),
            need_db=float(s["ref_snr_needed_for_3db_loss"]),
            gain_db=float(s["ref_antenna_gain_needed_db"]),
        ))
    return out


def _cliff_band(series: list[dict]) -> tuple[float, float]:
    """Pd 가 무너지는 구간을 **데이터에서** 찾는다(손으로 안 적는다)."""
    lo, hi = [], []
    for s in series:
        fail = s["x_ref"][s["pd_ref"] < 0.5]
        ok = s["x_ref"][s["pd_ref"] >= 0.5]
        if len(fail) and len(ok) and fail.max() < ok.min():
            lo.append(fail.max())
            hi.append(ok.min())
    if not lo:
        return (float("nan"), float("nan"))
    return (max(lo), min(hi))


def _pd_strip(ax, series, xs_key, pd_key, edges, xlim):
    """Pd 를 파형×축값 격자로 깐다. 회색 한 색 램프(중립) — 계열색과 안 겹치게."""
    grid = np.array([s[pd_key] for s in series], float)          # (3, N)
    ax.pcolormesh(edges, np.arange(len(series) + 1), grid[::-1],
                  cmap=CMAP_PD, vmin=0.0, vmax=1.0, edgecolors="white", linewidth=1.4)
    for i, s in enumerate(series[::-1]):
        for j, v in enumerate(s[pd_key]):
            xc = 0.5 * (edges[j] + edges[j + 1])
            ax.text(xc, i + 0.5, f"{v:.2f}", ha="center", va="center",
                    fontsize=FS - 2.2, color="white" if v > 0.55 else INK)
    ax.set_yticks(np.arange(len(series)) + 0.5)
    ax.set_yticklabels([s["mode"] for s in series[::-1]], fontsize=FS - 1.5)
    ax.set_ylim(0, len(series))
    ax.set_xlim(*xlim)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.tick_params(length=0, pad=13)          # 칩이 들어갈 자리를 라벨 앞에 비운다
    # 계열 정체성 칩 — 글자는 잉크색으로 두고 색은 칩이 나른다.
    for i, s in enumerate(series[::-1]):
        ax.plot([xlim[0] - 0.018 * (xlim[1] - xlim[0])], [i + 0.5], marker=s["marker"],
                ms=5.5, color=s["color"], clip_on=False, zorder=6)


def fig1_reference_ladder(ledger_path: str = LEDGER, outdir: str = FIGDIR) -> str:
    """⭐그림 1 — 기준채널 품질 사다리. 왼쪽=잡음축(절벽), 오른쪽=다중경로축(평지)."""
    led = json.load(open(ledger_path))
    S = _series(led)
    band_lo, band_hi = _cliff_band(S)

    y_max = max(float(np.max(s["y_ref"])) for s in S)
    ylim = (-4.0, y_max * 1.10)
    xlim_a = (-5.0, 45.0)
    xlim_b = (-32.5, -7.5)
    edges_a = np.array([-5, 5, 15, 25, 35, 45], float)
    edges_b = np.array([-32.5, -27.5, -22.5, -17.5, -12.5, -7.5], float)

    fig = plt.figure(figsize=(12.8, 6.3))
    gs = fig.add_gridspec(2, 2, width_ratios=[1.75, 1.0], height_ratios=[1.0, 0.26],
                          left=0.062, right=0.988, top=0.790, bottom=0.110,
                          wspace=0.085, hspace=0.10)
    axA = fig.add_subplot(gs[0, 0])
    axB = fig.add_subplot(gs[0, 1], sharey=axA)
    axPA = fig.add_subplot(gs[1, 0], sharex=axA)
    axPB = fig.add_subplot(gs[1, 1], sharex=axB)

    # ── (a) 잡음축 — 절벽 ────────────────────────────────────────────────────
    # 두 체제(못 봄 / 봄)를 배경으로 갈라 놓는다. 실패 쪽만 칠한다 — 성공 쪽은 흰 바탕.
    if np.isfinite(band_lo):
        for ax in (axA, axPA):
            ax.axvspan(xlim_a[0], band_lo, color=C_CLIFF, alpha=0.055, lw=0, zorder=0)
            ax.axvspan(band_lo, band_hi, color=C_CLIFF, alpha=0.16, lw=0, zorder=0)
        for xv in (band_lo, band_hi):
            axA.axvline(xv, color=C_CLIFF, lw=1.0, ls=(0, (4, 3)), alpha=0.65, zorder=1)
        pd_lo = max(float(s["pd_ref"][s["x_ref"] == band_lo][0]) for s in S)
        axA.text(0.5 * (xlim_a[0] + band_lo), ylim[1] * 0.975,
                 f"no detection   (Pd = {pd_lo:.2f})", ha="center", va="top",
                 fontsize=FS - 0.8, color=C_CLIFF, weight="bold")
        axA.text(0.5 * (band_lo + band_hi), ylim[1] * 0.975, "CLIFF",
                 ha="center", va="top", fontsize=FS - 0.8, color=C_CLIFF, weight="bold")
        axA.text(0.5 * (band_lo + band_hi), ylim[1] * 0.912,
                 f"{band_hi - band_lo:.0f} dB", ha="center", va="top",
                 fontsize=FS - 2.4, color=C_CLIFF)
        axA.text(0.5 * (band_hi + xlim_a[1]), ylim[1] * 0.975, "detection restored",
                 ha="center", va="top", fontsize=FS - 0.8, color=INK2, weight="bold")

    axA.axhline(0.0, color=INK3, lw=0.9, ls=(0, (5, 4)), zorder=1)
    axA.text(xlim_a[0] + 0.6, 0.0, " ideal reference (loss = 0)", ha="left", va="bottom",
             fontsize=FS - 2.4, color=INK3)
    axA.axhline(3.0, color=INK3, lw=0.8, ls=":", zorder=1)
    axA.text(xlim_a[1] - 0.5, 3.4, "3 dB", ha="right", va="bottom",
             fontsize=FS - 2.6, color=INK3)

    for s in S:
        axA.plot(s["x_ref"], s["y_ref"], "-", color=s["color"], lw=2.0, zorder=3,
                 label=s["label"], solid_capstyle="round")
        for x, y, pd in zip(s["x_ref"], s["y_ref"], s["pd_ref"]):
            axA.plot([x], [y], marker=s["marker"], ms=8.0, mew=1.7, zorder=4,
                     mec=s["color"], mfc=_blend(s["color"], pd), ls="none")
        axA.plot([s["need_db"]], [3.0], marker="v", ms=7.0, color=s["color"],
                 mec="white", mew=0.9, zorder=5, clip_on=False)

    w1 = [s for s in S if s["std"] == "wifi"][0]
    need_txt = " · ".join(f"{s['mode']} {s['need_db']:.1f}" for s in S)
    axA.annotate(f"3 dB-loss point ($\\blacktriangledown$)\n{need_txt} dB\n"
                 f"{w1['mode']} needs {w1['gain_db']:.1f} dB of reference-antenna gain",
                 xy=(w1["need_db"], 3.0), xytext=(xlim_a[1] - 0.5, 0.445 * ylim[1]),
                 fontsize=FS - 2.2, color=INK2, ha="right", va="bottom", linespacing=1.45,
                 arrowprops=dict(arrowstyle="-", color=INK3, lw=0.9,
                                 connectionstyle="angle3,angleA=0,angleB=80"))

    ideal_txt = "  /  ".join(f"{s['mode']} {s['pd_ideal']:.2f}" for s in S)
    axA.text(xlim_a[0] + 1.4, 0.075 * ylim[1],
             f"Pd with an ideal reference:  {ideal_txt}", fontsize=FS - 2.2, color=INK2)

    axA.set_ylim(*ylim)
    axA.set_xlim(*xlim_a)
    axA.set_xticks([0, 10, 20, 30, 40])
    axA.set_ylabel("Output SINR loss vs ideal reference  [dB]")
    axA.set_title("(a)  reference-channel noise", loc="left", color=INK, pad=7)
    axA.grid(alpha=0.22, lw=0.5)
    axA.set_axisbelow(True)
    plt.setp(axA.get_xticklabels(), visible=False)

    # ── (b) 다중경로축 — 평지 (세로 눈금은 (a) 와 같다) ──────────────────────
    axB.axhline(0.0, color=INK3, lw=0.9, ls=(0, (5, 4)), zorder=1)
    for s in S:
        axB.plot(s["x_mp"], s["y_mp"], "-", color=s["color"], lw=2.0, zorder=3)
        for x, y, pd in zip(s["x_mp"], s["y_mp"], s["pd_mp"]):
            axB.plot([x], [y], marker=s["marker"], ms=8.0, mew=1.7, zorder=4,
                     mec=s["color"], mfc=_blend(s["color"], pd), ls="none")
    worst = max(abs(float(v)) for s in S for v in s["y_mp"])
    axB.text(0.5, 0.955, f"no cliff — every point within {worst:.2f} dB of the ideal reference",
             transform=axB.transAxes, ha="center", va="top",
             fontsize=FS - 1.4, color=INK, weight="bold")
    axB.set_xlim(*xlim_b)
    axB.set_xticks([-30, -25, -20, -15, -10])
    axB.set_title("(b)  reference-channel multipath  — same vertical scale", loc="left",
                  color=INK, pad=7)
    axB.grid(alpha=0.22, lw=0.5)
    axB.set_axisbelow(True)
    plt.setp(axB.get_yticklabels(), visible=False)
    plt.setp(axB.get_xticklabels(), visible=False)

    # 확대 삽입 — 평지를 ±1 dB 로 늘려도 추세가 없다는 것까지 보인다.
    axin = axB.inset_axes([0.10, 0.40, 0.86, 0.30])
    for s in S:
        axin.plot(s["x_mp"], s["y_mp"], "-", color=s["color"], lw=1.5)
        for x, y, pd in zip(s["x_mp"], s["y_mp"], s["pd_mp"]):
            axin.plot([x], [y], ls="none", marker=s["marker"], ms=5.0,
                      mew=1.2, mec=s["color"], mfc=_blend(s["color"], pd))
    axin.axhline(0.0, color=INK3, lw=0.8, ls=(0, (5, 4)))
    axin.set_xlim(*xlim_b)
    axin.set_ylim(-1.0, 1.0)
    axin.set_yticks([-1, 0, 1])
    axin.set_xticks([-30, -25, -20, -15, -10])
    axin.tick_params(labelsize=FS - 3.2, length=2.5, pad=1.5)
    axin.set_facecolor("#fbfbf8")
    for sp in axin.spines.values():
        sp.set_color(INK3)
        sp.set_linewidth(0.8)
    axin.set_title("detail:  ±1 dB", fontsize=FS - 2.6, color=INK2, pad=2.0)
    axB.indicate_inset_zoom(axin, edgecolor=INK3, alpha=0.85, lw=0.8)

    # ── Pd 띠 두 장 ─────────────────────────────────────────────────────────
    _pd_strip(axPA, S, "x_ref", "pd_ref", edges_a, xlim_a)
    _pd_strip(axPB, S, "x_mp", "pd_mp", edges_b, xlim_b)
    axPA.set_xlabel("Reference-channel SNR  [dB]")
    axPB.set_xlabel("Multipath-to-direct ratio in the reference channel  [dB]")
    axPA.set_ylabel("Pd", rotation=0, ha="right", va="center", labelpad=16, fontsize=FS - 1)
    axPA.set_xticks([0, 10, 20, 30, 40])
    axPB.set_xticks([-30, -25, -20, -15, -10])
    for ax in (axPA, axPB):
        ax.tick_params(axis="x", labelsize=FS - 1, length=3)

    fig.suptitle("How much does passive detection lose when the reference channel is real?",
                 x=0.062, ha="left", fontsize=FS + 2.6, color=INK, weight="bold", y=0.972)
    fig.text(0.062, 0.918,
             "Noise in the reference channel is a cliff  —  multipath in it is flat ground.",
             ha="left", va="top", fontsize=FS + 0.4, color=INK2)

    # 범례는 두 패널 공용이라 그림 수준에 한 줄로 둔다 — 패널 안을 비워야 절벽이 보인다.
    handles = [Line2D([], [], color=s["color"], lw=2.0, marker=s["marker"], ms=8.0,
                      mew=1.7, mec=s["color"], mfc=s["color"], label=s["label"]) for s in S]
    lg = fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.058, 0.885),
                    ncol=3, frameon=False, handlelength=2.4, columnspacing=2.2,
                    handletextpad=0.7, fontsize=FS - 0.5)
    for t in lg.get_texts():
        t.set_color(INK)
    pd_keys = [Line2D([], [], ls="none", marker="o", ms=8, mew=1.7, mec=INK2,
                      mfc=_blend(INK2, f)) for f in (1.0, 0.5, 0.0)]
    lg2 = fig.legend(pd_keys, ["1.00", "0.50", "0.00"], loc="upper right",
                     bbox_to_anchor=(0.988, 0.885), ncol=3, frameon=False,
                     handletextpad=0.35, columnspacing=1.1, fontsize=FS - 1.6,
                     title="marker fill = Pd", title_fontsize=FS - 1.6)
    lg2.get_title().set_color(INK2)
    for t in lg2.get_texts():
        t.set_color(INK2)

    os.makedirs(outdir, exist_ok=True)
    png = f"{outdir}/passive_f1.png"
    fig.savefig(png)
    fig.savefig(f"{outdir}/passive_f1.pdf")
    plt.close(fig)
    print(f"✔ {png}")
    print(f"  cliff band = [{band_lo:g}, {band_hi:g}] dB refSNR (원장에서 찾은 값)")
    for s in S:
        print(f"  {s['mode']}: loss {s['y_ref'][-1]:.2f}→{s['y_ref'][0]:.2f} dB, "
              f"Pd {s['pd_ref'][-1]:.2f}→{s['pd_ref'][0]:.2f}, "
              f"MDR |loss|max {np.max(np.abs(s['y_mp'])):.2f} dB")
    return png


if __name__ == "__main__":
    fig1_reference_ladder()
