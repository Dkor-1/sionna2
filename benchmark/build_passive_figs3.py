# -*- coding: utf-8 -*-
"""
build_passive_figs3.py — 패시브 2채널 실험의 **그림 3**.

⭐ 그림 3 — **마이크로도플러는 검출이 죽은 뒤에도 남는가**
    질문: 기준채널이 나빠져 CFAR 가 표적을 놓치는 지점에서, 로터 플래시는 아직 읽히는가.
    답:   (1) Pd 가 0 이 된 **한 칸**에서도 플래시 선은 배경 위에 남는다 — 다만 그때는
              이상 팔에서 60 dB 넘게 잃은 뒤이고, 그 손실의 대부분은 Pd 가 아직 살아 있는
              첫 칸에서 이미 빠진다. «검출이 먼저 죽는다» 는 순서는 마지막 칸에서만 참이다.
              ⚠ Pd 는 E1b(검출 CPI), 플래시는 E2(별도 슬로타임 사슬) — 팔 이름만 같다.
          (2) 그런데 죽는 방식이 하나가 아니다. ECA 를 끄면 동체선이 날개끝을 덮고(+45.4 dB),
              5G SSB 처럼 조명원의 프레임률이 2 kHz 면 날개끝은 **잡음이 아니라 접힘으로**
              사라진다 — 무모호 도플러 ±1 kHz 밖에 있는 f_tip 1229 Hz 는 −771 Hz 로 접힌다.

무엇을 어디서 읽나 — 손으로 적은 수치는 하나도 없다
    md_survival[arm]              flash_contrast_db · flash_line_db · zero_bin_rel_tip_db
    md_survival.ledger_direct     사슬을 안 탄 원장 자체의 플래시 선(상한)
    md_survival.nr_alias          prf · f_unamb · f_tip · aliased  (5G 접힘 패널의 모든 수치)
    md_ledger                     f_tip_hz · f_flash_hz
    E1b[W1].rows                  팔별 Pd — 표적이 **같은 마이크로도플러 원장**인 검출 실험
    E2.wifi_b1.meta / nr_b1.meta  prf · f_unamb (사슬 자체의 도플러 한계)
    npz e2_wifi__*__{S,f,t}       STFT 맵 (팔 5개) · e2_nr__ideal__* (5G 팔)

읽는 것: outputs/passive_two_channel.json + .npz   (원장 — 절대 안 건드린다)
쓰는 것: outputs/figures/passive_f3.{png,pdf}

무결성 게이트(그림을 그리기 전에 통과해야 한다)
    · npz 맵에서 지표를 **다시 계산**해 원장 md_survival 과 맞는지 본다(1e-6).
      맵과 숫자가 다른 원장이면 그림이 거짓말을 한다.
    · md_survival 과 E2.wifi_b1.metrics 가 같은 값인지 본다(원장 내부 두 갈래 대조).

표시 규약
    · 그림 안 글자는 전부 영어(하우스 규약). 설정값(조각 길이·hop·n_taps 등)은 안 적는다.
    · 시간-주파수 맵은 **STFT 만** 쓰고, 그리기는 src/md_mapstyle.py 를 그대로 부른다
      (jet · 0~−40 dB · gouraud · ±f_tip 흰 파선). 우회하면 규약이 갈라진다.
    · (a)~(d) 는 **공통 기준**으로 정규화한다 — 팔마다 자기 최댓값에 맞추면 «바닥이 올라온다»
      는 이 그림의 핵심이 사라진다. (h)·(i) 는 축이 다른 대조군이라 각자 자기 최댓값이 기준이고,
      그 사실을 컬러바 이름에 적는다.
    · 닿지 못하는 도플러(±무모호 밖)는 **회색으로 덮는다** — 하양으로 비우면 «값이 없다» 가
      아니라 «값이 0 이다» 로 읽힌다.
    · 색: dataviz 팔레트 슬롯 1·4·7·8 + 잉크. all-pairs 게이트 실측(OKLab×100)
      최악 정상시야 ΔE 16.3, 최악 색각이상 ΔE 13.4 — 통과. 선 모양을 2차 부호로 얹는다.
      (⚠ 맵의 jet 은 하우스 규약이라 그대로 둔다 — 팔레트 규칙보다 md_mapstyle 이 우선이다.)
"""
from __future__ import annotations

import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import md_mapstyle as MS                                                  # noqa: E402

LEDGER = f"{ROOT}/outputs/passive_two_channel.json"
NPZ = f"{ROOT}/outputs/passive_two_channel.npz"
FIGDIR = f"{ROOT}/outputs/figures"

# ── 표시 규약 (그림 1 과 같은 손) ────────────────────────────────────────────
FS = 10.0
plt.rcParams.update({
    "font.size": FS, "axes.labelsize": FS, "axes.titlesize": FS,
    "xtick.labelsize": FS - 1, "ytick.labelsize": FS - 1, "legend.fontsize": FS - 1.5,
    "axes.linewidth": 0.9, "figure.dpi": 200, "savefig.dpi": 200,
    "font.family": "DejaVu Sans",
})
INK, INK2, INK3 = "#1a1a19", "#4a4a45", "#8a8a82"
GRAY_BLIND = "#c9c8c2"          # 「측정 불가」 회색
C_NR = "#1baf7a"                # 5G 계열색(그림 1 과 같은 배정)

# 팔(arm) — 순서가 곧 사다리다. 색은 위 게이트를 통과한 조합.
ARMS = [
    dict(key="ideal", name="ideal reference", short="ideal",
         color=INK, ls="-", lw=2.0),
    dict(key="refSNR+20dB", name="reference SNR +20 dB", short="ref +20",
         color="#eda100", ls=(0, (5, 2)), lw=2.0),
    dict(key="refSNR+10dB", name="reference SNR +10 dB", short="ref +10",
         color="#e34948", ls=(0, (1.6, 1.6)), lw=2.0),
    dict(key="MDR-20dB", name="reference multipath -20 dB", short="MDR -20",
         color="#2a78d6", ls=(0, (7, 2, 1.5, 2)), lw=2.0),
    dict(key="noECA", name="ECA off (control)", short="no ECA",
         color="#4a3aa7", ls=(0, (3, 1.4, 1.4, 1.4)), lw=2.0),
]
LADDER = ARMS[:4]               # (a)~(d) — 공통 눈금으로 그리는 사다리
PANEL_TAG = {"ideal": "(a)", "refSNR+20dB": "(b)", "refSNR+10dB": "(c)", "MDR-20dB": "(d)"}


# --------------------------------------------------------------------------- #
#  원장 읽기 + 무결성 게이트
# --------------------------------------------------------------------------- #
def _tip_band_series(S, f, f_tip):
    """날개끝 띠(0.35~1.00·f_tip)의 시간축 전력 — md_metrics 와 **같은 정의**."""
    P = S ** 2
    fa = np.abs(f)
    band = (fa >= 0.35 * f_tip) & (fa <= 1.00 * f_tip)
    return P[band, :].sum(axis=0) + 1e-300, band


def _recompute(S, f, t, f_tip, f_flash):
    """npz 맵에서 원장 지표를 다시 계산한다(benchmark/passive_two_channel_md.md_metrics 정의)."""
    P = S ** 2
    tb, band = _tip_band_series(S, f, f_tip)
    tb_db = 10 * np.log10(tb)
    contrast = float(np.percentile(tb_db, 95) - np.percentile(tb_db, 5))
    x = tb - tb.mean()
    w = np.hanning(len(x))
    Sx = np.abs(np.fft.rfft(x * w)) ** 2
    fx = np.fft.rfftfreq(len(x), d=float(t[1] - t[0]))
    k = max(1, int(np.argmin(np.abs(fx - f_flash))))
    lo, hi = max(1, k - 2), min(len(Sx), k + 3)
    line = float(10 * np.log10(Sx[lo:hi].max() / (np.median(Sx[1:]) + 1e-300)))
    df = abs(float(f[1] - f[0]))
    zb = np.abs(f) <= 0.5 * df
    zrel = float(10 * np.log10(P[zb, :].mean() / P[band, :].mean()))
    return dict(flash_contrast_db=contrast, flash_line_db=line, zero_bin_rel_tip_db=zrel)


def load(ledger_path: str = LEDGER, npz_path: str = NPZ):
    """원장 두 갈래를 읽고 **맵 ↔ 숫자** 가 같은 물건인지 확인한다."""
    led = json.load(open(ledger_path))
    arr = np.load(npz_path)
    f_tip = float(led["md_ledger"]["f_tip_hz"])
    f_flash = float(led["md_ledger"]["f_flash_hz"])
    surv = led["md_survival"]
    e2m = led["E2"]["wifi_b1"]["metrics"]

    maps = {}
    for a in ARMS:
        k = a["key"]
        S, f, t = (arr[f"e2_wifi__{k}__{s}"] for s in ("S", "f", "t"))
        maps[k] = dict(S=S, f=f, t=t)
        got = _recompute(S, f, t, f_tip, f_flash)
        for m in ("flash_contrast_db", "flash_line_db", "zero_bin_rel_tip_db"):
            assert abs(got[m] - surv[k][m]) < 1e-6, (k, m, got[m], surv[k][m])   # 맵↔숫자
            assert abs(e2m[k][m] - surv[k][m]) < 1e-9, (k, m)                    # 원장 내부
    nr = dict(S=arr["e2_nr__ideal__S"], f=arr["e2_nr__ideal__f"], t=arr["e2_nr__ideal__t"])

    pd_e1b = {r["arm"]: float(r["pd"]) for r in
              next(b for b in led["E1b"] if b["mode"] == "W1")["rows"]}
    return dict(led=led, maps=maps, nr=nr, f_tip=f_tip, f_flash=f_flash,
                surv=surv, pd=pd_e1b,
                wmeta=led["E2"]["wifi_b1"]["meta"], nmeta=led["E2"]["nr_b1"]["meta"],
                alias=surv["nr_alias"], ledger_direct=surv["ledger_direct"])


# --------------------------------------------------------------------------- #
#  그림
# --------------------------------------------------------------------------- #
def _cbar(fig, ax, mesh, label, dx=0.007, w=0.008, on_top=False):
    """패널 오른쪽에 컬러바를 **정확한 자리**로 붙인다(레이아웃이 흔들리지 않게).

    on_top : 이름을 컬러바 **위**에 놓는다 — 옆으로 세워 붙이면 다음 패널의 축 이름을 덮는다."""
    p = ax.get_position()
    cax = fig.add_axes([p.x1 + dx, p.y0, w, p.height])
    cb = fig.colorbar(mesh, cax=cax)
    if on_top:
        cb.ax.set_title(label, fontsize=FS - 2.6, color=INK2, pad=4, loc="left")
    else:
        cb.set_label(label, fontsize=FS - 2.4)
    cb.ax.tick_params(labelsize=FS - 2.6, length=2.5)
    cb.outline.set_linewidth(0.7)
    return cb


def fig3_md_survival(ledger_path: str = LEDGER, npz_path: str = NPZ,
                     outdir: str = FIGDIR) -> str:
    D = load(ledger_path, npz_path)
    led, maps, surv = D["led"], D["maps"], D["surv"]
    f_tip, f_flash = D["f_tip"], D["f_flash"]

    fig = plt.figure(figsize=(16.6, 12.4))
    # ⭐ 줄마다 따로 격자를 깐다 — 한 격자로 묶으면 컬러바가 옆 패널의 축 이름을 덮는다.
    gsA = fig.add_gridspec(1, 4, left=0.052, right=0.928, top=0.880, bottom=0.700,
                           wspace=0.13)
    gsB = fig.add_gridspec(1, 3, left=0.052, right=0.988, top=0.630, bottom=0.398,
                           wspace=0.30, width_ratios=[1.30, 1.00, 0.86])
    gsC = fig.add_gridspec(1, 3, left=0.052, right=0.988, top=0.318, bottom=0.078,
                           wspace=0.30)

    # ── (a)~(d) 사다리 맵 — 공통 기준 ────────────────────────────────────────
    ref_common = max(float(maps[a["key"]]["S"].max()) for a in LADDER)
    ax_map = []
    mesh = None
    for i, a in enumerate(LADDER):
        ax = fig.add_subplot(gsA[0, i])
        m = maps[a["key"]]
        mesh = MS.draw(ax, m["t"], m["f"], m["S"], f_tip, ref=ref_common)
        ax.set_title(f"{PANEL_TAG[a['key']]}  {a['name']}", loc="left", color=INK,
                     fontsize=FS, pad=5)
        ax.set_xlabel("Time  [ms]")
        if i == 0:
            ax.set_ylabel("Doppler  [Hz]")
        else:
            ax.set_yticklabels([])
        ax.text(0.025, 0.045, f"flash line {surv[a['key']]['flash_line_db']:.1f} dB",
                transform=ax.transAxes, fontsize=FS - 2.4, color="white", va="bottom",
                bbox=dict(fc="#1a1a19", ec="none", alpha=0.62, pad=2.2))
        ax.tick_params(length=3)
        ax_map.append(ax)

    # ── (e) 도플러 주변분포 — 절대 눈금 하나로 «바닥이 올라온다» 를 잰다 ─────
    axE = fig.add_subplot(gsB[0, 0])
    ref_pow_db = 20 * np.log10(maps["ideal"]["S"].max())      # 이상 팔의 표적 피크 = 0 dB
    for a in ARMS:
        m = maps[a["key"]]
        f = m["f"]
        view = np.abs(f) <= MS.YLIM_FTIP * f_tip
        y = 10 * np.log10((m["S"] ** 2).mean(axis=1)) - ref_pow_db
        o = np.argsort(f[view])
        axE.plot(f[view][o], y[view][o], color=a["color"], ls=a["ls"], lw=a["lw"],
                 marker="o", ms=3.2, mew=0, zorder=3, label=a["name"])
    for s in (+1, -1):
        axE.axvspan(s * 0.35 * f_tip, s * 1.00 * f_tip, color=INK3, alpha=0.13, lw=0,
                    zorder=0)
        axE.axvline(s * f_tip, color=INK3, ls=(0, (4, 3)), lw=0.9, zorder=1)
    axE.annotate("wingtip band", xy=(0.675 * f_tip, 0.045), xycoords=("data", "axes fraction"),
                 ha="center", va="bottom", fontsize=FS - 2.4, color=INK2)
    zr = surv["noECA"]["zero_bin_rel_tip_db"]
    y0 = (10 * np.log10((maps["noECA"]["S"] ** 2).mean(axis=1))
          )[np.argmin(np.abs(maps["noECA"]["f"]))] - ref_pow_db
    axE.annotate(f"ECA off:\nthe zero-Doppler bin sits\n{zr:.1f} dB over the wingtips",
                 xy=(0.0, y0), xytext=(0.60 * f_tip, y0 - 5.0),
                 fontsize=FS - 2.4, color=INK2, ha="left", va="top", linespacing=1.35,
                 arrowprops=dict(arrowstyle="-", color=INK3, lw=0.9,
                                 connectionstyle="angle3,angleA=0,angleB=80"))
    axE.annotate("multipath -20 dB lies on the ideal curve",
                 xy=(-1.55 * f_tip, -21.8), xytext=(-1.80 * f_tip, -13.5),
                 fontsize=FS - 2.4, color=INK2, ha="left", va="bottom",
                 arrowprops=dict(arrowstyle="-", color=INK3, lw=0.9,
                                 connectionstyle="angle3,angleA=0,angleB=80"))
    axE.set_xlim(-MS.YLIM_FTIP * f_tip, MS.YLIM_FTIP * f_tip)
    axE.set_xlabel("Doppler  [Hz]")
    axE.set_ylabel("Time-averaged power,\nrelative to the ideal-reference peak  [dB]")
    axE.set_title("(e)  The target peak stays put — the floor comes up", loc="left",
                  color=INK, pad=5)
    axE.grid(alpha=0.22, lw=0.5)
    axE.set_axisbelow(True)
    leg = axE.legend(loc="upper left", frameon=True, framealpha=0.94, borderpad=0.5,
                     handlelength=2.6, labelspacing=0.35)
    leg.get_frame().set_edgecolor("#dddad2")
    leg.get_frame().set_linewidth(0.8)

    # ── (f) 플래시 빗살 — 띠 전력의 시간축 ───────────────────────────────────
    axF = fig.add_subplot(gsB[0, 1])
    n_per = 6.0                                   # 보여 주는 창 = 블레이드 플래시 6 주기
    t_win = n_per / f_flash * 1e3
    step = 16.0
    for i, a in enumerate(ARMS[::-1]):
        m = maps[a["key"]]
        tb, _ = _tip_band_series(m["S"], m["f"], f_tip)
        y = 10 * np.log10(tb)
        y = y - np.median(y) + i * step
        t_ms = m["t"] * 1e3
        w = t_ms <= t_ms[0] + t_win
        axF.plot(t_ms[w], y[w], color=a["color"], lw=1.5, zorder=3)
        axF.text(t_ms[w][-1] + 0.8, i * step, a["short"], color=a["color"],
                 fontsize=FS - 2.6, va="center", ha="left", weight="bold")
    t0 = maps["ideal"]["t"][0] * 1e3
    yb = (len(ARMS) - 0.55) * step
    axF.annotate("", xy=(t0 + 1e3 / f_flash, yb), xytext=(t0, yb),
                 arrowprops=dict(arrowstyle="<->", color=INK2, lw=1.0))
    axF.text(t0 + 0.5e3 / f_flash, yb + 1.2, "one blade-flash period", ha="center",
             va="bottom", fontsize=FS - 2.4, color=INK2)
    axF.set_xlim(t0 - 0.5, t0 + t_win + 9.0)
    axF.set_ylim(-step * 1.15, yb + step * 0.55)
    axF.set_yticks([])
    axF.set_xlabel("Time  [ms]")
    axF.set_title("(f)  The comb the detector never sees", loc="left", color=INK, pad=5)
    axF.grid(alpha=0.22, lw=0.5, axis="x")
    axF.set_axisbelow(True)
    # 세로 눈금 막대 — 눈금을 지운 대신 크기를 남긴다.
    y_bar = -step * 1.02
    axF.plot([t0 + 0.5 * t_win] * 2, [y_bar, y_bar + 10], color=INK2, lw=2.0,
             solid_capstyle="butt")
    axF.text(t0 + 0.5 * t_win + 0.9, y_bar + 5, "10 dB", fontsize=FS - 2.4, color=INK2,
             va="center", ha="left")

    # ── (g) 플래시 선 세기 막대 + Pd 띠 ─────────────────────────────────────
    sub = gsB[0, 2].subgridspec(2, 1, height_ratios=[1.0, 0.30], hspace=0.10)
    axG = fig.add_subplot(sub[0])
    axP = fig.add_subplot(sub[1], sharex=axG)
    xs = np.arange(len(ARMS))
    vals = [surv[a["key"]]["flash_line_db"] for a in ARMS]
    axG.bar(xs, vals, width=0.66, color=[a["color"] for a in ARMS], zorder=3)
    for x, v in zip(xs, vals):
        axG.text(x, v + 2.0, f"{v:.1f}", ha="center", va="bottom", fontsize=FS - 2.2,
                 color=INK)
    ld = float(D["ledger_direct"]["flash_line_db"])
    axG.axhline(ld, color=INK3, ls=(0, (5, 4)), lw=1.0, zorder=2)
    axG.text(len(ARMS) - 0.55, ld - 3.5, f"ledger, chain bypassed  {ld:.1f} dB",
             ha="right", va="top", fontsize=FS - 2.6, color=INK2)
    axG.set_ylim(0, ld * 1.10)
    axG.set_ylabel("Flash-line strength  [dB]")
    axG.set_title("(g)  Flash line vs Pd", loc="left", color=INK, pad=5)
    axG.text(0.02, 0.985, "bars and Pd strip are measured on different chains",
             transform=axG.transAxes, ha="left", va="top", fontsize=FS - 2.6, color=INK2)
    axG.grid(alpha=0.22, lw=0.5, axis="y")
    axG.set_axisbelow(True)
    plt.setp(axG.get_xticklabels(), visible=False)

    # Pd 띠 — 같은 마이크로도플러 표적으로 잰 검출률(E1b). noECA 는 그 실험에 없다.
    for i, a in enumerate(ARMS):
        pd = D["pd"].get(a["key"])
        if pd is None:
            axP.add_patch(plt.Rectangle((i - 0.33, 0.08), 0.66, 0.84, fc="#f1f0ec",
                                        ec="#dddad2", lw=0.8, hatch="////"))
            axP.text(i, 0.5, "n/a", ha="center", va="center", fontsize=FS - 2.4,
                     color=INK3)
            continue
        shade = 1.0 - 0.86 * pd
        axP.add_patch(plt.Rectangle((i - 0.33, 0.08), 0.66, 0.84,
                                    fc=(shade, shade, shade * 0.98), ec="white", lw=1.2))
        axP.text(i, 0.5, f"{pd:.2f}", ha="center", va="center", fontsize=FS - 2.0,
                 color="white" if pd > 0.55 else INK)
    axP.set_ylim(0, 1)
    axP.set_xlim(-0.6, len(ARMS) - 0.4)
    axP.set_xticks(xs)
    axP.set_xticklabels([a["short"] for a in ARMS], fontsize=FS - 2.0)
    axP.set_yticks([])
    axP.set_ylabel("Pd", rotation=0, ha="right", va="center", labelpad=12,
                   fontsize=FS - 1)
    for sp in axP.spines.values():
        sp.set_visible(False)
    axP.tick_params(length=0)

    # ── (h) ECA off — 동체선이 날개끝을 덮는다 ──────────────────────────────
    axH = fig.add_subplot(gsC[0, 0])
    m = maps["noECA"]
    meshH = MS.draw(axH, m["t"], m["f"], m["S"], f_tip)
    axH.set_title("(h)  ECA off — the body line buries the wingtips", loc="left",
                  color=INK, pad=5)
    axH.set_xlabel("Time  [ms]")
    axH.set_ylabel("Doppler  [Hz]")
    axH.text(0.025, 0.045,
             f"zero-Doppler bin  +{surv['noECA']['zero_bin_rel_tip_db']:.1f} dB "
             f"over the wingtip band",
             transform=axH.transAxes, fontsize=FS - 2.4, color="white", va="bottom",
             bbox=dict(fc="#1a1a19", ec="none", alpha=0.62, pad=2.2))

    # ── (i) 5G 접힘 — 닿지 못하는 도플러는 회색으로 덮는다 ──────────────────
    axI = fig.add_subplot(gsC[0, 1])
    nr = D["nr"]
    f_unamb = float(D["alias"]["f_unamb_hz"])
    prf_nr = float(D["alias"]["prf_hz"])
    f_fold = f_tip - prf_nr                                   # 접혀서 떨어지는 자리
    meshI = MS.draw(axI, nr["t"], nr["f"], nr["S"], f_tip)
    axI.set_facecolor(GRAY_BLIND)
    lim = MS.YLIM_FTIP * f_tip
    for lo, hi in ((f_unamb, lim), (-lim, -f_unamb)):
        axI.axhspan(lo, hi, color=GRAY_BLIND, lw=0, zorder=3)
    axI.axhline(f_unamb, color=INK2, lw=1.0, zorder=4)
    axI.axhline(-f_unamb, color=INK2, lw=1.0, zorder=4)
    for s in (+1, -1):
        axI.axhline(s * f_tip, color=C_NR, ls=(0, (5, 2)), lw=1.5, zorder=5)
        axI.axhline(s * f_fold, color=C_NR, ls=(0, (1.6, 1.6)), lw=1.5, zorder=5)
    t_a = nr["t"][int(0.42 * len(nr["t"]))] * 1e3
    axI.annotate("", xy=(t_a, f_fold), xytext=(t_a, f_tip),
                 arrowprops=dict(arrowstyle="-|>", color=C_NR, lw=1.6,
                                 connectionstyle="arc3,rad=0.28"), zorder=6)
    axI.text(nr["t"][2] * 1e3, f_tip + 0.09 * f_tip,
             f"true wingtip  {f_tip:.0f} Hz — outside the window", color=INK,
             fontsize=FS - 2.4, va="bottom", zorder=6)
    axI.text(0.5 * (nr["t"][0] + nr["t"][-1]) * 1e3, -0.5 * (f_unamb + lim),
             f"beyond ±{f_unamb:.0f} Hz — not measurable", color=INK2,
             fontsize=FS - 2.2, ha="center", va="center", zorder=6)
    axI.text(nr["t"][-1] * 1e3 - 2.0, f_fold + 0.06 * f_tip,
             f"it lands here instead:  {f_fold:.0f} Hz", color=C_NR, fontsize=FS - 2.4,
             ha="right", va="bottom", weight="bold", zorder=6,
             bbox=dict(fc="#1a1a19", ec="none", alpha=0.66, pad=2.0))
    axI.set_title(f"(i)  5G SSB frame rate {prf_nr/1e3:.0f} kHz — the wingtip folds",
                  loc="left", color=INK, pad=5)
    axI.set_xlabel("Time  [ms]")
    axI.set_ylabel("Doppler  [Hz]")

    # ── (j) 접힘 자([ruler]) — 참 도플러가 어디로 떨어지나 ───────────────────
    axJ = fig.add_subplot(gsC[0, 2])
    lim_j = 2.6 * f_unamb
    xr = np.linspace(-lim_j, lim_j, 4001)
    yr = ((xr + f_unamb) % prf_nr) - f_unamb
    yr_break = np.where(np.abs(np.diff(yr)) > f_unamb, np.nan, 1.0)
    axJ.plot(xr, xr, color=INK3, ls=(0, (5, 4)), lw=1.0, zorder=2)
    axJ.plot(xr[:-1], yr[:-1] * yr_break, color=C_NR, lw=2.2, zorder=4)
    axJ.axhspan(f_unamb, lim_j, color=GRAY_BLIND, lw=0, zorder=1)
    axJ.axhspan(-lim_j, -f_unamb, color=GRAY_BLIND, lw=0, zorder=1)
    axJ.text(-0.95 * lim_j, 1.85 * f_unamb, "no measurement can land here",
             fontsize=FS - 2.4, color=INK2, va="center", zorder=5)
    # 직접 이름표 — 범례 상자 없이(패널이 좁다)
    axJ.text(0.62 * f_unamb, 0.62 * f_unamb + 0.10 * f_unamb, "an unfolded sensor",
             color=INK2, fontsize=FS - 2.6, rotation=45, rotation_mode="anchor",
             ha="center", va="bottom", zorder=5)
    axJ.text(-1.75 * f_unamb, -0.75 * f_unamb + 0.10 * f_unamb,
             f"what the {prf_nr/1e3:.0f} kHz frame rate reports", color=C_NR, fontsize=FS - 2.6,
             rotation=45, rotation_mode="anchor", ha="center", va="bottom", zorder=5,
             weight="bold")
    for s in (+1, -1):
        axJ.plot([s * f_tip], [s * f_fold], marker="o", ms=8.0, mfc=C_NR, mec="white",
                 mew=1.4, zorder=6, ls="none")
        axJ.plot([s * f_tip, s * f_tip], [s * f_fold, s * f_tip], color=C_NR, lw=0.9,
                 ls=":", zorder=3)
    axJ.annotate(f"wingtip {f_tip:.0f} Hz  →  {f_fold:.0f} Hz\n"
                 f"(reads as a receding blade)",
                 xy=(f_tip, f_fold), xytext=(-0.20 * f_unamb, -1.90 * f_unamb),
                 fontsize=FS - 2.2, color=INK2, ha="left", va="center", linespacing=1.35,
                 zorder=6,
                 arrowprops=dict(arrowstyle="-", color=INK3, lw=0.9,
                                 connectionstyle="angle3,angleA=0,angleB=75"))
    w_unamb = float(D["wmeta"]["f_unamb_hz"])
    axJ.text(0.5, 1.012,
             f"the WiFi chain in (a)-(d) reads to ±{w_unamb/1e3:.1f} kHz — nothing folds",
             transform=axJ.transAxes, ha="center", va="bottom", fontsize=FS - 2.4,
             color=INK2)
    axJ.set_xlim(-lim_j, lim_j)
    axJ.set_ylim(-lim_j, lim_j)
    axJ.set_xlabel("True Doppler  [Hz]")
    axJ.set_ylabel("Measured Doppler  [Hz]")
    axJ.set_title("(j)  Where the fold puts it", loc="left", color=INK, pad=16)
    axJ.grid(alpha=0.22, lw=0.5)
    axJ.set_axisbelow(True)

    # ── 컬러바 ──────────────────────────────────────────────────────────────
    fig.canvas.draw()
    _cbar(fig, ax_map[-1], mesh, "Relative power  [dB]\ncommon scale for (a)-(d)")
    _cbar(fig, axH, meshH, "dB\nown peak", on_top=True)
    _cbar(fig, axI, meshI, "dB\nown peak", on_top=True)

    # ── 제목 ────────────────────────────────────────────────────────────────
    pd_txt = " → ".join(f"{D['pd'][a['key']]:.2f}" for a in LADDER[:3])
    fl_txt = " → ".join(f"{surv[a['key']]['flash_line_db']:.1f}" for a in LADDER[:3])
    fig.suptitle("Does the micro-Doppler survive after the detector has died?",
                 x=0.052, ha="left", fontsize=FS + 2.6, color=INK, weight="bold", y=0.972)
    fl_drop = surv[LADDER[0]["key"]]["flash_line_db"] - surv[LADDER[2]["key"]]["flash_line_db"]
    fig.text(0.052, 0.933,
             f"Down the reference-SNR ladder detection collapses (Pd {pd_txt}) and the "
             f"blade-flash line loses {fl_drop:.0f} dB ({fl_txt} dB) — still above the "
             f"background at the rung where the detector reports nothing.",
             ha="left", fontsize=FS + 0.2, color=INK2)
    fig.text(0.052, 0.910,
             "But the comb dies two other ways that noise never causes:  with ECA off the "
             f"body line buries it, and at a {prf_nr/1e3:.0f} kHz illuminator frame rate "
             "the wingtip folds inside the window.",
             ha="left", fontsize=FS + 0.2, color=INK2)
    fig.text(0.052, 0.012,
             "Every map is read at the target's known range bin — survival here is a "
             "statement about recognising a target, not about finding one.  The Pd strip "
             "in (g) comes from a separate detection run whose slow-time chain differs "
             "from the one these maps use.",
             ha="left", fontsize=FS - 2.0, color=INK3)

    os.makedirs(outdir, exist_ok=True)
    png = f"{outdir}/passive_f3.png"
    fig.savefig(png)
    fig.savefig(f"{outdir}/passive_f3.pdf")
    plt.close(fig)

    print(f"✔ {png}")
    print("  무결성 게이트: npz 맵에서 다시 계산한 지표 == 원장 md_survival (1e-6) 통과")
    for a in ARMS:
        s = surv[a["key"]]
        pd = D["pd"].get(a["key"])
        print(f"  {a['key']:12s} flash_line {s['flash_line_db']:6.2f} dB · "
              f"contrast {s['flash_contrast_db']:5.2f} dB · "
              f"body/tip {s['zero_bin_rel_tip_db']:6.2f} dB · "
              f"Pd(E1b) {'n/a' if pd is None else f'{pd:.2f}'}")
    print(f"  5G 접힘: PRF {prf_nr:.0f} Hz → 무모호 ±{f_unamb:.0f} Hz, "
          f"f_tip {f_tip:.1f} Hz → {f_fold:.1f} Hz (aliased={D['alias']['aliased']})")
    print(f"  WiFi 사슬 무모호 ±{w_unamb:.0f} Hz — 접힘 없음")
    return png


if __name__ == "__main__":
    fig3_md_survival()
