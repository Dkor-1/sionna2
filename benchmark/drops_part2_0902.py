# -*- coding: utf-8 -*-
"""drops_part2_0902.py — 덱 2 부 「갑작스런 낙차」 그림 둘.

⭐사용자 제안(2026-09-02): 낙차를 4·7 쪽의 곁다리로 두지 말고 **2 부로 독립**시킨다.
   4 쪽이 두 번 고쳐도 안 닿은 이유가 그것이었다 — 이번 세션에서 가장 확실한 발견을
   세 번째 열 하나에 욱여넣고 있었다.

⛔틀은 「PathSolver 에 결함이 있다」가 아니라 **「우리가 무엇을 쟀나」** 다.
   기전을 아직 모르므로 원인을 단정하지 않는다.

  A  the_record   기록이 두 값만 갖는다 — 자세별 |E| 궤적 + 분포
  C  where_works  어디까지 통하나 — 팔·각도별 일관성

실행:
  CUDA_VISIBLE_DEVICES="" PYTHONPATH=src:benchmark \
    /workspace/.venvs/py312/bin/python benchmark/drops_part2_0902.py
"""
import os
import sys

import numpy as np

ROOT = "/workspace/sionna"
sys.path.insert(0, f"{ROOT}/benchmark")
sys.path.insert(0, f"{ROOT}/src")
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

import matplotlib.pyplot as plt                                        # noqa: E402
from clutter_parts_ladder_0824 import load, cs_eca, f_tip, PRF, FFL     # noqa: E402
from md_mapstyle import auto_periods, flash_spec, draw                 # noqa: E402

PERIODS = auto_periods(PRF, FFL)
NZ = int(round(0.058 * PRF))
ENGINES = [("Our kernel",  "ours_r15_n8192"),
           ("Physics off", "sionna_p4000000000_r15_n8192_d1"),
           ("Physics on",  "sionna_p4000000000_phys_r15_n8192_d1")]

INK, GRAY, ACC, NAVY = "#141926", "#5E5E5E", "#C81E3C", "#1F3864"
DEG, MINUS = chr(176), chr(8722)
OUT = f"{ROOT}/outputs/figures"
W_ARM = "sionna_p4000000000_r15_n8192_d1"
P_ARM = "sionna_p4000000000_partsprop_r15_n8192_d1"


def dips(E, thr=0.9):
    E = np.asarray(E)
    m = np.median(np.abs(E))
    return np.where(np.abs(E) / m < thr)[0], m


def fill(E):
    E = np.asarray(E)
    bad, _ = dips(E)
    g = np.setdiff1d(np.arange(E.size), bad)
    R = E.copy()
    if len(bad):
        R[bad] = (np.interp(bad, g, E[g].real) + 1j * np.interp(bad, g, E[g].imag))
    return R, bad


def corr(a, b):
    a = np.asarray(a) - np.mean(a)
    b = np.asarray(b) - np.mean(b)
    return float(np.abs(np.vdot(a, b))
                 / np.sqrt((np.abs(a) ** 2).sum() * (np.abs(b) ** 2).sum()))


# ═══ A — 기록이 두 값만 갖는다 ══════════════════════════════════════════════
def fig_record(el=0.0):
    W = load(W_ARM, el)[0]
    bad, med = dips(W)
    r = np.abs(np.asarray(W)) / med
    t = np.arange(r.size) / PRF * 1e3

    fig, (ax, bx) = plt.subplots(1, 2, figsize=(17.6, 5.6),
                                 gridspec_kw=dict(width_ratios=[1.75, 1.0], wspace=0.20))
    #: 왼쪽 — 앞 60 ms 를 확대해 하나하나 보이게
    n = int(round(0.060 * PRF))
    ax.plot(t[:n], r[:n], "-o", ms=2.5, lw=0.9, color="#7A8494")
    inw = bad[bad < n]
    ax.plot(t[inw], r[inw], "o", ms=10, color=ACC, zorder=5)
    ax.axhline(1.0, color="0.6", lw=1.0, ls=(0, (5, 4)))
    ax.axhline(2 / 3, color=ACC, lw=1.2, ls=(0, (5, 4)))
    ax.text(t[n - 1], 1.012, "usual size", ha="right", fontsize=15, color=GRAY)
    ax.text(t[n - 1], 0.678, "two thirds of it", ha="right", fontsize=15,
            color=ACC, weight="bold")
    ax.set_ylim(0.60, 1.06)
    ax.set_xlim(0, t[n - 1])
    ax.set_xlabel("time [ms]", fontsize=16)
    ax.set_ylabel("echo size, relative to usual", fontsize=16)
    ax.set_title("the first 60 ms, pose by pose", fontsize=19, color=INK,
                 weight="bold", pad=10)
    ax.grid(True, color="#E8E8E8", lw=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)

    #: 오른쪽 — 전체 8,192 자세의 분포. 막대 둘이면 「두 값뿐」이 즉시 보인다
    bins = np.linspace(0.60, 1.10, 201)
    bx.hist(r, bins=bins, color="#7A8494", log=True)
    bx.hist(r[bad], bins=bins, color=ACC, log=True)
    bx.set_xlim(0.60, 1.10)
    bx.set_ylim(0.7, 3e4)
    bx.set_xlabel("echo size, relative to usual", fontsize=16)
    bx.set_ylabel("how many poses", fontsize=15)
    bx.set_title(f"all {r.size:,} poses", fontsize=19, color=INK, weight="bold", pad=10)
    bx.grid(True, axis="y", color="#E8E8E8", lw=0.8)
    bx.set_axisbelow(True)
    for s in ("top", "right"):
        bx.spines[s].set_visible(False)
    bx.annotate(f"{len(bad)} poses", xy=(2 / 3, 60), xytext=(0.76, 900),
                fontsize=16, color=ACC, weight="bold",
                arrowprops=dict(arrowstyle="-|>", color=ACC, lw=2.0))

    fig.subplots_adjust(top=0.845, bottom=0.135, left=0.058, right=0.988)
    fig.text(0.5, 0.945, f"matrice4e  {chr(183)}  15 m  {chr(183)}  el {el:+.0f}{DEG}",
             ha="center", fontsize=16, color=GRAY)
    p = f"{OUT}/drops_record.png"
    fig.savefig(p, dpi=128, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✅ {p}   낙차 {len(bad)}")


# ═══ C — 어디까지 통하나 ════════════════════════════════════════════════════
def fig_where():
    PAIR = [("physics off", W_ARM, P_ARM),
            ("physics on", "sionna_p4000000000_phys_r15_n8192_d1",
                           "sionna_p4000000000_phys_partsprop_r15_n8192_d1")]
    ELS = (0.0, -30.0, -60.0, -90.0)
    rows = []
    for nm, aw, ap in PAIR:
        for el in ELS:
            try:
                W, P = load(aw, el)[0], load(ap, el)[0]
            except Exception:
                continue
            R, bad = fill(W)
            ac = np.abs(np.asarray(W) - np.mean(W)) ** 2
            sh = 100 * ac[bad].sum() / ac.sum() if len(bad) else 0.0
            rows.append((nm, el, len(bad), sh, corr(W, P), corr(R, P)))

    fig, (ax, bx) = plt.subplots(1, 2, figsize=(17.6, 5.6),
                                 gridspec_kw=dict(width_ratios=[1.0, 1.15], wspace=0.26))
    #: 왼쪽 — 낙차가 변동 에너지에서 갖는 몫
    y = np.arange(len(rows))[::-1]
    lab = [f"{n}   el {e:+.0f}{DEG}" for n, e, *_ in rows]
    ax.barh(y, [r[3] for r in rows],
            color=[ACC if r[3] > 90 else "#8e9aab" for r in rows], height=0.62)
    for yi, r in zip(y, rows):
        ax.text(r[3] + 1.5, yi, f"{r[3]:.0f} %   ({r[2]} poses)", va="center",
                fontsize=14, color=INK)
    ax.axvline(90, color=ACC, lw=1.4, ls=(0, (5, 4)))
    ax.set_yticks(y)
    ax.set_yticklabels(lab, fontsize=14)
    ax.set_xlim(0, 128)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xlabel("share of the wobble carried by the drops [%]", fontsize=15)
    ax.set_title("how much of the wobble is drops", fontsize=19, color=INK,
                 weight="bold", pad=10)
    ax.grid(True, axis="x", color="#E8E8E8", lw=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)

    #: 오른쪽 — 무시하기 전/후, 프로펠러 단독과 얼마나 닮았나
    for yi, r in zip(y, rows):
        bx.plot([r[4], r[5]], [yi, yi], "-", color="#C8CDD5", lw=2.4, zorder=2)
        bx.plot(r[4], yi, "o", ms=10, mfc="white", mec="#7A8494", mew=2.2, zorder=4)
        bx.plot(r[5], yi, "o", ms=10, color=ACC if r[3] > 90 else "#8e9aab", zorder=5)
    bx.set_yticks(y)
    bx.set_yticklabels([])
    bx.set_xlim(-0.04, 1.06)
    bx.set_xlabel("how closely it matches the propellers-only record", fontsize=15)
    bx.set_title("before  ○  →  after  ●", fontsize=19, color=INK,
                 weight="bold", pad=10)
    bx.grid(True, axis="x", color="#E8E8E8", lw=0.8)
    bx.set_axisbelow(True)
    for s in ("top", "right", "left"):
        bx.spines[s].set_visible(False)

    fig.subplots_adjust(top=0.845, bottom=0.135, left=0.155, right=0.988)
    fig.text(0.5, 0.945, "red = the drops carry more than 90 % of the wobble",
             ha="center", fontsize=16, color=ACC, weight="bold")
    p = f"{OUT}/drops_where.png"
    fig.savefig(p, dpi=128, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✅ {p}")
    for r in rows:
        print(f"     {r[0]:<12} el {r[1]:>+4.0f}  drops {r[2]:>5}  share {r[3]:5.1f}%  "
              f"{r[4]:.3f} -> {r[5]:.3f}")


# ═══ B — 무시하면 줄무늬가 사라진다 ═════════════════════════════════════════
def fig_stft(el=0.0):
    """⭐**같은 그림을 전/후로.** 필터·창·눈금이 전부 같고 차이는 「58 자세를 무시했나」 하나다."""
    fig, ax = plt.subplots(len(ENGINES), 2, figsize=(17.0, 8.4),
                           sharex=True, sharey=True)
    for r, (eng, arm) in enumerate(ENGINES):
        W = load(arm, el)[0]
        R, bad = fill(W)
        for c, (E, ttl) in enumerate(((W, "as recorded"),
                                      (R, "with those poses ignored"))):
            a = ax[r, c]
            f_, t_, S_, _ = flash_spec(cs_eca(np.asarray(E))[:NZ], PRF, FFL, PERIODS)
            draw(a, t_, f_, S_, f_tip(el))
            a.set_ylim(-2000, 2000)
            if r == 0:
                a.set_title(ttl, fontsize=20, color=INK, weight="bold", pad=10)
            a.tick_params(labelsize=14, labelbottom=(r == len(ENGINES) - 1))
            if r == len(ENGINES) - 1:
                a.set_xlabel("time [ms]", fontsize=16)
            if c == 0:
                a.set_ylabel("Doppler [Hz]", fontsize=15)
            else:
                a.set_yticklabels([])
                a.text(0.985, 0.05, f"{len(bad)} poses", transform=a.transAxes,
                       ha="right", va="bottom", fontsize=15, color="white",
                       weight="bold")
        print(f"     {eng:<12} drops {len(bad)}")
    # ⛔행 이름이 y 축 이름과 겹친다 — 여백을 넓히고 더 왼쪽으로
    fig.subplots_adjust(top=0.885, bottom=0.085, left=0.185, right=0.988,
                        hspace=0.15, wspace=0.05)
    for r, (eng, _a) in enumerate(ENGINES):
        bx = ax[r, 0].get_position()
        fig.text(0.108, bx.y0 + bx.height / 2, eng, ha="right", va="center",
                 fontsize=18, weight="bold", color=INK)
    p = f"{OUT}/drops_stft.png"
    fig.savefig(p, dpi=126, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✅ {p}")


if __name__ == "__main__":
    print("═══ 2 부 · 갑작스런 낙차 ═══")
    fig_record()
    fig_stft()
    fig_where()
