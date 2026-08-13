# -*- coding: utf-8 -*-
"""
build_raybudget_40m_fig.py — **40 m 에서 광선을 22배 늘리면 시드 불안정이 사라지나.**

사용자(2026-08-11)
> "40억발 쏜 것의 STFT 그림도 내가 보려면 어디서 봐야하니?"

■ 무엇을 나란히 놓나
같은 거리(40 m)·같은 기체·같은 자세열(4,096)·같은 STFT 규약에서 **광선 수만** 바꾼 두 판을,
각 판마다 **난수 시드 두 개**로 그린다.

    윗줄   1.78 억 발  (덱 v19 가 인용한 판)      seed 1 · seed 2
    아랫줄 40   억 발  (2^32 상한 바로 아래)      seed 1 · seed 2
    맨아래 날개끝 대역 에너지의 변조율 스펙트럼 — 두 판을 왼쪽·오른쪽에 갈라 놓고
           각 판 안에서 시드 두 개를 겹쳐 그린다. **시드끼리 겹치면 안정된 것이다.**

■ 읽는 법
· 맵이 각자 최대값으로 정규화된다(잡음이 없으므로 절대 눈금이 의미가 없다).
  그래서 «40 m 가 3 m 보다 약하다» 는 이 그림에서 안 보인다 — 그건 잡음을 넣어야 보인다.
· 예측선 126.67 Hz = 날개 2장 × 3,800 rpm ÷ 60. **회전수(63.3 Hz)가 아니라 플래시율**이다.

■ 자료
· 40 억 발  : outputs/range40_shards/s{1,2}_{00..05}.npz  (nshards=6, spp=4.0e9)
· 1.78억 발 : outputs/range40_178M/s{1,2}_*.npz           (git HEAD 에서 대피시킨 원본)
  ⚠ 40 억 발 실행이 1.78 억 발 샤드를 **같은 경로에 덮어썼다**. 그래서 옛 판은 저 폴더에만 있다.
  ⚠ outputs/range40_shards/ 에 남은 s*_06·s*_07 은 옛 8-샤드 실행의 잔재다. 섞으면 안 된다 —
    이 스크립트는 meta 의 spp 로 걸러낸다.

    PYTHONPATH=src:benchmark /workspace/.venvs/py312/bin/python \
        benchmark/build_raybudget_40m_fig.py
"""
from __future__ import annotations

import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                          # noqa: E402
import numpy as np                                                       # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, f"{ROOT}/src")
sys.path.insert(0, f"{ROOT}/benchmark")

from md_mapstyle import auto_periods, draw, flash_spec                   # noqa: E402

TJ = json.load(open(f"{ROOT}/outputs/report07_three_engines.json"))["_meta"]
PRF, FFL, FTIP = TJ["prf_hz"], TJ["f_flash_hz"], TJ["f_tip_hz"]
PERIODS = auto_periods(PRF, FFL)

BAND_LO, BAND_HI = 0.35, 1.00                    # 날개끝 대역 (f_tip 배수) — 덱과 동일
LO_HZ, HI_HZ = BAND_LO * FTIP, BAND_HI * FTIP
ZOOM_MS, N0 = 60.0, 500
NZ = int(round(ZOOM_MS * 1e-3 * PRF))

C_LO, C_HI = "#c2570a", "#7a1fa8"                # 1.78억발 / 40억발
SEED_LS = {1: "-", 2: "--"}
FS = 13
plt.rcParams.update({"font.size": FS, "axes.labelsize": FS, "axes.titlesize": FS,
                     "xtick.labelsize": FS - 2, "ytick.labelsize": FS - 2,
                     "legend.fontsize": FS - 2.5, "figure.dpi": 200,
                     "savefig.dpi": 200, "font.family": "DejaVu Sans"})

OUT_PNG = f"{ROOT}/outputs/figures/raybudget_40m.png"
OUT_JSON = f"{ROOT}/outputs/report07_range40_raybudget.json"


# ── 샤드 병합 ────────────────────────────────────────────────────────────────
def merge(folders, seed: int, spp_want: float, tol: float = 0.02):
    """meta 의 spp 가 spp_want 인 샤드만 모아 자세 순으로 되꽂는다.

    ⚠ 폴더를 여러 개 받는다. 1.78 억 발 판은 **8 샤드** 실행이었는데 40 억 발 실행(6 샤드)이
      00~05 를 덮어써서, 대피본(range40_178M/)에는 00~05 만 있고 06·07 은 원래 자리
      (range40_shards/)에 남아 있다. 둘을 합쳐야 4,096 자세가 다 찬다.
      같은 (seed, shard) 가 두 폴더에 다 있으면 **먼저 온 폴더** 것을 쓴다.
    """
    import glob
    if isinstance(folders, str):
        folders = [folders]
    E, idx, npaths, used, secs, seen = [], [], [], [], [], set()
    for folder in folders:
        for f in sorted(glob.glob(f"{folder}/s{seed}_*.npz")):
            z = np.load(f, allow_pickle=True)
            m = np.asarray(z["meta"], float)
            if abs(m[3] / spp_want - 1.0) > tol:
                continue                               # ⚠ 다른 예산의 잔재 — 버린다
            tag = (int(m[1]), int(m[2]))               # (shard, nshards)
            if tag in seen:
                continue                               # 같은 조각이 두 폴더에 — 먼저 것을 쓴다
            seen.add(tag)
            E.append(z["E"]); idx.append(z["idx"]); npaths.append(z["npaths"])
            used.append(f"{os.path.basename(folder)}/{os.path.basename(f)}")
            secs.append(float(m[5]))
    if not E:
        raise SystemExit(f"❌ {folder} seed {seed} 에 spp={spp_want:.3g} 샤드가 없다")
    idx = np.concatenate(idx); order = np.argsort(idx)
    idx = idx[order]
    Ea = np.concatenate(E)[order]
    Np = np.concatenate(npaths)[order]
    n_expect = int(idx.max()) + 1
    gaps = n_expect - len(idx)
    return dict(E=Ea, idx=idx, npaths=Np, files=used, seconds=sum(secs),
                n=len(idx), n_expect=n_expect, gaps=gaps)


def band_energy(E):
    """날개끝 대역 전력을 시간축으로 보고 다시 FFT — 덱과 **글자 그대로 같은 함수**."""
    f, t, S, _ = flash_spec(np.asarray(E, complex), PRF, FFL, PERIODS)
    b = (np.abs(f) >= LO_HZ) & (np.abs(f) <= HI_HZ)
    g = (S[b, :] ** 2).sum(axis=0)
    g = g - g.mean()
    dt = float(t[1] - t[0]); m = len(g)
    A = np.abs(np.fft.rfft(g * np.hanning(m), n=64 * m))
    fr = np.fft.rfftfreq(64 * m, dt)
    A = A / A.max()
    s = fr <= 420
    sel = (fr >= 40) & (fr <= 400)
    i0 = int(np.where(sel)[0][0]); i = int(np.argmax(A[sel])) + i0
    y0, y1, y2 = A[i - 1], A[i], A[i + 1]
    den = y0 - 2 * y1 + y2
    pk = fr[i] + (0.5 * (y0 - y2) / den if den else 0.0) * (fr[1] - fr[0])
    return fr[s], A[s], float(pk)


def h1_over_h2_db(fr, A):
    """1x 가 2x 를 몇 dB 로 이기나. 두 봉우리를 각자 좁은 창에서 찾는다."""
    def peak(f0, half=18.0):
        w = (fr >= f0 - half) & (fr <= f0 + half)
        return float(A[w].max()) if w.any() else np.nan
    p1, p2 = peak(FFL), peak(2.0 * FFL)
    return 20.0 * np.log10(p1 / p2) if (p1 > 0 and p2 > 0) else np.nan


def _map(ax, E):
    seg = np.asarray(E, complex)[N0:N0 + NZ]
    f, t, S, _ = flash_spec(seg, PRF, FFL, PERIODS)
    return draw(ax, t + N0 / PRF, f, S, FTIP)


def main() -> None:
    SH, S178 = f"{ROOT}/outputs/range40_shards", f"{ROOT}/outputs/range40_178M"
    ARMS = [("1.78e8", [S178, SH], 1.78e8, "178 M rays", C_LO),
            ("4.0e9", [SH], 4.0e9, "4,000 M rays", C_HI)]

    data, rows = {}, []
    for key, folder, spp, label, col in ARMS:
        for seed in (1, 2):
            d = merge(folder, seed, spp)
            fr, A, pk = band_energy(d["E"])
            rows.append(dict(
                arm=key, spp=spp, label=label, seed=seed,
                n_poses=d["n"], gaps=d["gaps"], shards=d["files"],
                seconds=round(d["seconds"], 1),
                npaths_median=int(np.median(d["npaths"])),
                npaths_max=int(d["npaths"].max()),
                npaths_zero=int((d["npaths"] == 0).sum()),
                beat_hz=round(pk, 2),
                beat_rel_err_pct=round(100.0 * (pk / FFL - 1.0), 2),
                level_db=round(20.0 * np.log10(np.mean(np.abs(d["E"]))), 2),
                h1_over_h2_db=round(float(h1_over_h2_db(fr, A)), 2)))
            data[(key, seed)] = (d, fr, A, pk)
            print(f"  {label:12s} seed {seed}: 자세 {d['n']}/{d['n_expect']} "
                  f"(빠짐 {d['gaps']}) · 경로중앙 {rows[-1]['npaths_median']:>4d} · "
                  f"박자 {pk:7.2f} Hz · 레벨 {rows[-1]['level_db']:7.2f} dB · "
                  f"1x-2x {rows[-1]['h1_over_h2_db']:+5.2f} dB", flush=True)

    # ── 그림 ────────────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(12.6, 11.4))
    gs = fig.add_gridspec(3, 3, width_ratios=[1, 1, 0.038],
                          height_ratios=[1, 1, 0.92],
                          wspace=0.10, hspace=0.34,
                          left=0.085, right=0.945, top=0.925, bottom=0.062)
    m = None
    for r, (key, _f, _s, label, col) in enumerate(ARMS):
        for c, seed in enumerate((1, 2)):
            ax = fig.add_subplot(gs[r, c])
            m = _map(ax, data[(key, seed)][0]["E"])
            ax.set_title(f"seed {seed}", color=col, fontweight="bold", pad=6)
            if c == 0:
                ax.set_ylabel(f"{label}\nDoppler [Hz]", color=col)
            else:
                plt.setp(ax.get_yticklabels(), visible=False)
            ax.set_xlabel("Time [ms]")
            for sp in ax.spines.values():
                sp.set_color(col); sp.set_linewidth(1.8)
    cax = fig.add_subplot(gs[0:2, 2])
    cb = fig.colorbar(m, cax=cax); cb.set_label("Normalised power [dB]")

    for c, (key, _f, _s, label, col) in enumerate(ARMS):
        ax = fig.add_subplot(gs[2, c])
        for seed in (1, 2):
            _d, fr, A, pk = data[(key, seed)]
            ax.plot(fr, 20 * np.log10(np.maximum(A, 1e-6)), SEED_LS[seed],
                    color=col, lw=1.5, label=f"seed {seed}")
        ax.axvline(FFL, color="0.35", lw=1.0, ls=":")
        ax.axvline(2 * FFL, color="0.62", lw=0.9, ls=":")
        ax.set_xlim(0, 420); ax.set_ylim(-60, 3)
        ax.set_xlabel("Modulation frequency [Hz]")
        ax.set_title(label, color=col, fontweight="bold", pad=6)
        ax.grid(alpha=0.25, lw=0.5)
        ax.legend(frameon=False, loc="upper right")
        if c == 0:
            ax.set_ylabel("Band energy [dB]")
        else:
            plt.setp(ax.get_yticklabels(), visible=False)
        ax.annotate("1x", (FFL, 1.0), ha="center", va="top", fontsize=FS - 3, color="0.3")
        ax.annotate("2x", (2 * FFL, 1.0), ha="center", va="top", fontsize=FS - 3, color="0.55")

    fig.suptitle("Blade tip band at 40 m — does a larger ray budget remove the seed dependence?",
                 fontweight="bold", y=0.972)
    os.makedirs(os.path.dirname(OUT_PNG), exist_ok=True)
    fig.savefig(OUT_PNG, bbox_inches="tight")
    fig.savefig(OUT_PNG.replace(".png", ".pdf"), bbox_inches="tight")
    plt.close(fig)

    # ── 덱용 가로판 ─────────────────────────────────────────────────────────
    # 8/11 덱의 그림틀은 25.09 x 6.35 in (가로 3.95:1) 이라 위 세로판이 안 들어간다.
    # 맵 4 칸만 한 줄로 세워 «배경이 깨끗해졌다» 하나만 보이게 한다.
    figd = plt.figure(figsize=(24.0, 7.0))
    gsd = figd.add_gridspec(1, 5, width_ratios=[1, 1, 1, 1, 0.022],
                            wspace=0.07, left=0.045, right=0.972, top=0.845, bottom=0.135)
    md = None
    for c, (key, seed) in enumerate([("1.78e8", 1), ("1.78e8", 2),
                                     ("4.0e9", 1), ("4.0e9", 2)]):
        col = C_LO if key == "1.78e8" else C_HI
        lab = "178 M rays" if key == "1.78e8" else "4,000 M rays"
        ax = figd.add_subplot(gsd[0, c])
        md = _map(ax, data[(key, seed)][0]["E"])
        ax.set_title(f"{lab}   ·   seed {seed}", color=col, fontweight="bold",
                     fontsize=FS + 3, pad=9)
        ax.set_xlabel("Time [ms]", fontsize=FS + 1)
        if c == 0:
            ax.set_ylabel("Doppler [Hz]", fontsize=FS + 1)
        else:
            plt.setp(ax.get_yticklabels(), visible=False)
        for sp in ax.spines.values():
            sp.set_color(col); sp.set_linewidth(2.2)
    caxd = figd.add_subplot(gsd[0, 4])
    cbd = figd.colorbar(md, cax=caxd); cbd.set_label("Normalised power [dB]", fontsize=FS)
    OUT_STRIP = f"{ROOT}/outputs/figures/raybudget_40m_deck.png"
    figd.savefig(OUT_STRIP, bbox_inches="tight")
    plt.close(figd)
    print(f"\n✅ {OUT_STRIP}  (덱용 가로판)")

    # ── 덱용 나란히판 — 40 억 발 PathSolver ↔ 우리 PO ────────────────────────
    # 사용자(2026-08-11): "40 억 발 쏜 거랑 PO 로 뽑은 STFT 결과물 같이 나란히"
    OZ = np.load(f"{ROOT}/outputs/deck_ours_by_range.npz")
    E_ours = OZ["R40/E"]
    C_OURS = "#1f5fa8"                                # 덱의 «우리 팔» 색
    figs = plt.figure(figsize=(22.0, 8.2))
    gss = figs.add_gridspec(1, 4, width_ratios=[1, 1, 1, 0.028],
                            wspace=0.09, left=0.055, right=0.965, top=0.865, bottom=0.115)
    ms = None
    panels = [(data[("4.0e9", 1)][0]["E"], "Sionna Path Solver\n4,000 M rays  ·  seed 1", C_HI),
              (data[("4.0e9", 2)][0]["E"], "Sionna Path Solver\n4,000 M rays  ·  seed 2", C_HI),
              (E_ours,                     "Ours (SBR + PO)\nno randomness",              C_OURS)]
    for c, (E, ttl, col) in enumerate(panels):
        ax = figs.add_subplot(gss[0, c])
        ms = _map(ax, E)
        ax.set_title(ttl, color=col, fontweight="bold", fontsize=FS + 4, pad=10)
        ax.set_xlabel("Time [ms]", fontsize=FS + 2)
        if c == 0:
            ax.set_ylabel("Doppler [Hz]", fontsize=FS + 2)
        else:
            plt.setp(ax.get_yticklabels(), visible=False)
        for sp in ax.spines.values():
            sp.set_color(col); sp.set_linewidth(2.4)
    caxs = figs.add_subplot(gss[0, 3])
    cbs = figs.colorbar(ms, cax=caxs); cbs.set_label("Normalised power [dB]", fontsize=FS + 1)
    OUT_SIDE = f"{ROOT}/outputs/figures/raybudget_40m_vs_ours.png"
    figs.savefig(OUT_SIDE, bbox_inches="tight")
    plt.close(figs)
    print(f"✅ {OUT_SIDE}  (덱용 나란히판 — 40 m, 두 엔진)")

    # ── 판정 ────────────────────────────────────────────────────────────────
    def spread(arm, field):
        v = [r[field] for r in rows if r["arm"] == arm]
        return round(float(max(v) - min(v)), 3)

    verdict = dict(
        beat_spread_hz={a: spread(a, "beat_hz") for a in ("1.78e8", "4.0e9")},
        level_spread_db={a: spread(a, "level_db") for a in ("1.78e8", "4.0e9")},
        h1_over_h2_spread_db={a: spread(a, "h1_over_h2_db") for a in ("1.78e8", "4.0e9")},
        path_scaling_ko=(
            "경로 수 중앙값 "
            f"{[r['npaths_median'] for r in rows if r['arm']=='1.78e8']} → "
            f"{[r['npaths_median'] for r in rows if r['arm']=='4.0e9']} "
            f"(광선 {4.0e9/1.78e8:.1f} 배)"),
        caveat_ko=(
            "⚠ 시드가 판마다 2개뿐이다. «폭이 줄었다» 는 두 추첨의 차이일 뿐이고 "
            "통계적 주장이 아니다. 판정을 굳히려면 시드를 더 늘려야 한다."))

    json.dump({"_meta": {
        "generator": "benchmark/build_raybudget_40m_fig.py",
        "question_ko": "40 m 에서 광선을 22.5 배 늘리면 PathSolver 의 시드 불안정이 사라지나",
        "range_m": 40.0, "drone": TJ.get("name"),
        "prf_hz": PRF, "f_flash_hz": FFL, "f_tip_hz": FTIP,
        "stft_ko": f"flash_spec 규약 — periods={PERIODS:.3f}, hop·pad 는 md_mapstyle 기본",
        "band_hz": [LO_HZ, HI_HZ],
        "band_energy_ko": "날개끝 대역 전력을 시간축으로 다시 FFT 한 변조율 스펙트럼. "
                          "그 최강선이 «박자» 이고 예측은 f_flash 다.",
        "normalisation_ko": "맵은 각자 최대값 정규화(잡음 미모델). 거리에 따른 약해짐은 안 보인다.",
        "shard_hazard_ko": "40 억 발 실행이 1.78 억 발 샤드를 같은 경로에 덮어썼다. "
                           "옛 판은 outputs/range40_178M/ 에만 있다. "
                           "range40_shards/ 의 s*_06·s*_07 은 옛 8-샤드 잔재라 spp 로 걸러 버린다.",
        "figure": OUT_PNG},
        "rows": rows, "verdict": verdict},
        open(OUT_JSON, "w"), ensure_ascii=False, indent=1)

    print(f"\n⭐박자 폭  1.78억발 {verdict['beat_spread_hz']['1.78e8']:>7.2f} Hz"
          f"  →  40억발 {verdict['beat_spread_hz']['4.0e9']:>7.2f} Hz")
    print(f"  레벨 폭  1.78억발 {verdict['level_spread_db']['1.78e8']:>7.2f} dB"
          f"  →  40억발 {verdict['level_spread_db']['4.0e9']:>7.2f} dB")
    print(f"  1x-2x 폭 1.78억발 {verdict['h1_over_h2_spread_db']['1.78e8']:>7.2f} dB"
          f"  →  40억발 {verdict['h1_over_h2_spread_db']['4.0e9']:>7.2f} dB")
    print(f"\n✅ {OUT_PNG}\n✅ {OUT_JSON}")


if __name__ == "__main__":
    main()
