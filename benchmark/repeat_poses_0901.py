# -*- coding: utf-8 -*-
"""repeat_poses_0901.py — 같은 판을 여섯 번 돌리면 어디가 다른가 (덱 10 장).

⛔옛 그림(s09_engine_rolls_dice.png)을 버린다 — el −90 칸을 쓰는데 거기서는
   f_tip = f_tip(−30)·cos(−90) ≈ 0 이라 **빗살 대비가 정의되지 않는다.** 게다가
   덱이 쓰지 않는 스칼라를 눈금 없는 축에 5 배 확대해 그렸다(적대 검증 2026-09-01).

⛔**거리 함정** — `_rep1..rep5` 중 `_r15` 가 **없는** 판은 10 m 다(cfg[0]=10).
   기준 판(15 m)과 섞으면 거리 차이를 재현성으로 읽게 된다. 여기서는 `_r15` 계열만 쓴다.

    CUDA_VISIBLE_DEVICES="" PYTHONPATH=src:benchmark \
      /workspace/.venvs/py312/bin/python benchmark/repeat_poses_0901.py
"""
import os
import sys

import numpy as np

ROOT = "/workspace/sionna"
sys.path.insert(0, f"{ROOT}/benchmark")
sys.path.insert(0, f"{ROOT}/src")
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
os.environ.setdefault("SWGRID_EL", "-30")

import matplotlib.pyplot as plt                                        # noqa: E402
import build_switch_grid_figs as G                                     # noqa: E402

SH = f"{ROOT}/outputs/elev_sweep_shards"
MESH = "mfixbatteryi5_blperairframe"
BASE = f"sionna_p4000000000_swR1D1E1F1_r15_n8192{{tag}}_{MESH}_d2"
TAGS = ["", "_rep1", "_rep2", "_rep3", "_rep4", "_rep5"]
DEG, MINUS = chr(176), chr(8722)


def load(tag):
    """샤드 두 쪽을 8,192 칸에 흩뿌린다(build_switch_grid_figs.load 와 같은 규약)."""
    E = np.full(8192, np.nan, complex)
    NP = np.full(8192, -1, int)
    rng_m = None
    for part in ("00", "01"):
        f = f"{SH}/{BASE.format(tag=tag)}_el-30_{part}.npz"
        z = np.load(f, allow_pickle=True)
        E[z["idx"]] = z["E"]
        NP[z["idx"]] = z["npaths"]
        rng_m = float(z["cfg"][0])
    miss = int(np.isnan(E).sum())
    assert miss == 0, f"{tag}: 빈 칸 {miss} — 구멍 난 판으로는 그리지 않는다"
    assert rng_m == 15.0, f"{tag}: 거리 {rng_m} m — 15 m 아닌 판을 섞으면 안 된다"
    return E, NP


def main():
    runs = [load(t) for t in TAGS]
    print(f"  여섯 판 · 8,192 자세 · 빈 칸 0 · 전부 15 m")

    fig, (ax, bx) = plt.subplots(1, 2, figsize=(17.6, 6.9),
                                 gridspec_kw=dict(width_ratios=[1.38, 1.0], wspace=0.20))

    # ── A. 변조 스펙트럼 여섯 겹치기
    h1 = []
    for i, (E, _NP) in enumerate(runs):
        fr, Y = G.modspec(E)
        ax.plot(fr, 10 * np.log10(Y / Y.max() + 1e-30), color="#1565c0",
                lw=1.2, alpha=0.75, zorder=3)
        df = fr[1] - fr[0]
        b = int(round(G.FFL / df))
        fl = float(np.median(Y[(fr > 20) & (fr < 500)]))
        h1.append(10 * np.log10(Y[max(0, b - 3):b + 4].max() / fl))
    for k in range(1, 9):
        ax.axvline(k * G.FFL, color="0.35", lw=1.0, ls=(0, (4, 4)), zorder=1)
    ax.set_xlim(0, 1000); ax.set_ylim(-52, 4)
    ax.set_xlabel("modulation rate [Hz]"); ax.set_ylabel("line level [dB]")
    ax.set_title("six identical runs, overlaid", fontsize=18, color="#141926",
                 weight="bold", pad=9)
    ax.grid(True, color="#D5D5D5", lw=0.7); ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    # ⛔0.05 에 두면 곡선 꼬리와 겹친다 — 왼쪽 아래 빈 곳으로 옮긴다
    ax.text(0.030, 0.055,
            f"first blade line over its local floor:\n"
            f"{' / '.join(f'{v:.2f}' for v in sorted(h1))} dB    "
            f"(spread {max(h1)-min(h1):.3f} dB)",
            transform=ax.transAxes, ha="left", va="bottom", fontsize=13,
            color="#141926", linespacing=1.4,
            bbox=dict(fc="white", ec="none", alpha=0.82, pad=4))

    # ── B. 자세별 상대차 — 어디가 다른가
    Ea, NPa = runs[0]
    Eb, NPb = runs[1]
    d = np.abs(Eb - Ea) / np.maximum(np.abs(Ea), 1e-300)
    hi = np.where(d > 1e-12)[0]
    same = hi[NPa[hi] == NPb[hi]]
    diff = hi[NPa[hi] != NPb[hi]]
    bx.semilogy(np.arange(d.size), np.maximum(d, 1e-18), ".", ms=1.6,
                color="#B8C0CC", zorder=2)
    bx.semilogy(diff, d[diff], "o", ms=9, color="#C81E3C", zorder=5,
                label=f"path count changed ({len(diff)})")
    bx.semilogy(same, d[same], "o", ms=9, mfc="none", mec="#C81E3C", mew=2.0,
                zorder=5, label=f"same count, different value ({len(same)})")
    bx.axhline(1e-15, color="#141926", lw=1.4, ls=(0, (6, 4)), zorder=3)
    bx.text(8100, 1.6e-15, "float64 rounding", ha="right", fontsize=13,
            color="#141926")
    bx.set_xlim(0, 8192); bx.set_ylim(1e-18, 1.0)
    bx.set_xlabel("pose index"); bx.set_ylabel("relative field difference")
    bx.set_title("run 1 vs run 2, pose by pose", fontsize=18, color="#141926",
                 weight="bold", pad=9)
    bx.grid(True, color="#D5D5D5", lw=0.7); bx.set_axisbelow(True)
    for s in ("top", "right"):
        bx.spines[s].set_visible(False)
    bx.legend(fontsize=13, frameon=False, loc="upper left")

    # ── 열다섯 짝 전부
    n_pair, ever, worst = [], set(), 0.0
    for i in range(len(runs)):
        for j in range(i + 1, len(runs)):
            dd = np.abs(runs[j][0] - runs[i][0]) / np.maximum(np.abs(runs[i][0]), 1e-300)
            w = np.where(dd > 1e-12)[0]
            n_pair.append(len(w)); ever |= set(w.tolist())
            if len(w):
                worst = max(worst, float(dd[w].max()))
    print(f"  15 짝 · 짝마다 다른 자세 {min(n_pair)}~{max(n_pair)} 개 · "
          f"한 번이라도 다른 자세 {len(ever)} 개 · 최대 상대차 {100*worst:.1f} %")
    fig.subplots_adjust(top=0.815, bottom=0.125, left=0.055, right=0.988)
    fig.text(0.5, 0.955, "the same run, six times",
             ha="center", fontsize=24, color="#141926", weight="bold")
    # ⛔빨간줄 삭제(라벨 검증) — 슬라이드 리드·결론바가 같은 말을 한다.
    fig.text(0.5, 0.862, f"matrice4e {chr(183)} 15 m {chr(183)} el {MINUS}30{DEG} "
             f"{chr(183)} refraction+diffraction {chr(183)} 4e9 rays {chr(183)} depth 2",
             ha="center", fontsize=14, color="#5E5E5E")
    fig.text(0.008, 0.012, f"over all 15 pairs: {min(n_pair)}-{max(n_pair)} poses differ "
             f"per pair, largest single-pose difference {100*worst:.1f} %   "
             f"{chr(183)}   NVlabs/sionna discussion #1175",
             ha="left", fontsize=12, color="#5E5E5E")
    p = f"{ROOT}/outputs/figures/repeat_poses_0901.png"
    fig.savefig(p, dpi=130); plt.close(fig)
    print(f"  ✅ {p}")


if __name__ == "__main__":
    print("═══ 같은 판 여섯 번 ═══")
    main()
