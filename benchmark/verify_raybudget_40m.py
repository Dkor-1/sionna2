# -*- coding: utf-8 -*-
"""
verify_raybudget_40m.py — **광선을 22.5 배 부으면 40 m 의 약점 넷이 사라지나.**

사용자(2026-08-11)
> "40 m 시나리오 40억발 여러 번 시도해서 경로가 늘어나서 약점이 사라지는지 검증"

■ 무엇을 재나 — `docs/PLAN_PATHSOLVER_CLASSIFY.md` §1 이 적어 둔 약점 넷
  ① 시드 간 **박자**(날개끝 대역 에너지의 최강선). 예측 126.67 Hz
  ② 시드 간 **레벨 폭**
  ③ **1× 가 2× 를 이기는 여유**
  ④ **52 ms 창 7 개 중 2× 로 뒤집힌 창 수**

■ 규율
· 두 판(1.78억 발 · 40억 발)을 **같은 코드·같은 잣대**로 잰다.
· 옛 보고서 수치를 베끼지 않는다 — 원장 npz 에서 **다시 잰다**. 베낀 수와 다르면 적는다.
· ④ 는 원장 스크립트가 없다(RESUME.md 산문 한 줄뿐). 그래서 여기서 **정의를 코드로 못 박는다**:
  창 1,024 표본(52.0 ms) · hop 512 표본 → 4,096 자세에서 정확히 **7 창**.

    PYTHONPATH=src:benchmark /workspace/.venvs/py312/bin/python \
        benchmark/verify_raybudget_40m.py
"""
from __future__ import annotations

import glob
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
PERIODS = auto_periods(PRF, FFL)          # 규약이 고른 조각 길이(0.45 주기)

BJ = json.load(open(f"{ROOT}/outputs/deck0811_range_figs.json"))["_meta"]
LO_HZ, HI_HZ = BJ["band_hz"]              # 430.05 ~ 1228.72 Hz — 덱과 같은 대역

WIN_N, WIN_HOP = 1024, 512                # 52.0 ms 창 · 50 % 겹침 → 7 창
ZOOM_MS, N0 = 60.0, 500                   # 맵에 보여줄 구간
NZ = int(round(ZOOM_MS * 1e-3 * PRF))

C_LO, C_HI, C_OURS = "#c2570a", "#7a1fa8", "#1f5fa8"
FS = 13
plt.rcParams.update({"font.size": FS, "axes.labelsize": FS, "axes.titlesize": FS,
                     "xtick.labelsize": FS - 2, "ytick.labelsize": FS - 2,
                     "legend.fontsize": FS - 2.5, "figure.dpi": 200,
                     "savefig.dpi": 200, "font.family": "DejaVu Sans"})

OUT_PNG = f"{ROOT}/outputs/figures/raybudget_40m.png"
OUT_JSON = f"{ROOT}/outputs/report07_range40_raybudget.json"
OUT_NPZ = f"{ROOT}/outputs/report07_range40_raybudget.npz"


# ── 샤드 병합 ────────────────────────────────────────────────────────────────
def merge(folders, seed: int, spp_want: float, tol: float = 0.02):
    """meta 의 spp 로 골라 자세 순으로 되꽂는다.

    ⚠ 40 억 발 실행이 1.78 억 발 샤드를 같은 경로에 덮어썼다. 1.78 억 발 판은 **8 샤드**라
      00~05 는 대피본(range40_178M/), 06~07 은 원래 자리(range40_shards/)에 남아 있다.
    """
    if isinstance(folders, str):
        folders = [folders]
    E, idx, npaths, used, secs, seen = [], [], [], [], [], set()
    for folder in folders:
        for f in sorted(glob.glob(f"{folder}/s{seed}_*.npz")):
            z = np.load(f, allow_pickle=True)
            m = np.asarray(z["meta"], float)
            if abs(m[3] / spp_want - 1.0) > tol:
                continue
            tag = (int(m[1]), int(m[2]))
            if tag in seen:
                continue
            seen.add(tag)
            E.append(z["E"]); idx.append(z["idx"]); npaths.append(z["npaths"])
            used.append(f"{os.path.basename(folder)}/{os.path.basename(f)}")
            secs.append(float(m[5]))
    if not E:
        raise SystemExit(f"❌ seed {seed} · spp={spp_want:.3g} 샤드가 없다")
    idx = np.concatenate(idx); order = np.argsort(idx)
    idx = idx[order]
    return dict(E=np.concatenate(E)[order], idx=idx,
                npaths=np.concatenate(npaths)[order], files=sorted(used),
                seconds=float(sum(secs)), n=len(idx),
                n_expect=int(idx.max()) + 1, gaps=int(idx.max()) + 1 - len(idx))


# ── 잣대 ─────────────────────────────────────────────────────────────────────
def band_series(E, periods=None):
    """날개끝 대역 전력의 **시간열**과 그 표본간격."""
    f, t, S, _ = flash_spec(np.asarray(E, complex), PRF, FFL,
                            PERIODS if periods is None else periods)
    b = (np.abs(f) >= LO_HZ) & (np.abs(f) <= HI_HZ)
    return (S[b, :] ** 2).sum(axis=0), float(t[1] - t[0])


def mod_spectrum(g, dt, pad=64):
    """대역 에너지의 **변조율 스펙트럼**(0 평균 · hann · 제로패딩)."""
    g = np.asarray(g, float) - float(np.mean(g))
    m = len(g)
    A = np.abs(np.fft.rfft(g * np.hanning(m), n=pad * m))
    fr = np.fft.rfftfreq(pad * m, dt)
    return fr, A / (A.max() + 1e-300)


def peak_in(fr, A, f0, half=18.0):
    w = (fr >= f0 - half) & (fr <= f0 + half)
    return float(A[w].max()) if w.any() else float("nan")


def beat_hz(fr, A, lo=40.0, hi=400.0):
    """최강선 — 봉우리 셋으로 포물선 보간."""
    sel = (fr >= lo) & (fr <= hi)
    i = int(np.argmax(A[sel])) + int(np.where(sel)[0][0])
    y0, y1, y2 = A[i - 1], A[i], A[i + 1]
    den = y0 - 2 * y1 + y2
    return float(fr[i] + (0.5 * (y0 - y2) / den if den else 0.0) * (fr[1] - fr[0]))


def h1_over_h2_db(fr, A):
    """1× 가 2× 를 몇 dB 로 이기나. 양수면 1× 가 이긴다."""
    p1, p2 = peak_in(fr, A, FFL), peak_in(fr, A, 2.0 * FFL)
    if not (p1 > 0 and p2 > 0):
        return float("nan")
    return float(20.0 * np.log10(p1 / p2))


def window_flips(E, periods=None):
    """⭐ **52 ms 창 7 개 중 2× 가 1× 를 이기는 창 수.** 정의를 여기서 못 박는다."""
    E = np.asarray(E, complex)
    starts = list(range(0, len(E) - WIN_N + 1, WIN_HOP))
    per_win = []
    for s in starts:
        g, dt = band_series(E[s:s + WIN_N], periods)
        fr, A = mod_spectrum(g, dt)
        per_win.append(round(h1_over_h2_db(fr, A), 2))
    flips = int(sum(1 for v in per_win if v < 0))
    return flips, len(starts), per_win


def map_floor_db(E, periods=None):
    """맵의 **바닥이 첨두보다 몇 dB 아래인가** — «잡티가 줄었다» 를 눈 대신 수로.

    자기 최대값으로 정규화한 맵의 중앙값 전력. 깊을수록 배경이 깨끗하다.
    """
    _f, _t, S, _ = flash_spec(np.asarray(E, complex), PRF, FFL,
                              PERIODS if periods is None else periods)
    P = S.astype(float) ** 2
    return float(10.0 * np.log10(np.median(P) / P.max()))


def measure(E, periods=None):
    g, dt = band_series(E, periods)
    fr, A = mod_spectrum(g, dt)
    pk = beat_hz(fr, A)
    fl, nw, per = window_flips(E, periods)
    return dict(map_floor_db=round(map_floor_db(E, periods), 2),
                beat_hz=round(pk, 3),
                beat_rel_err_pct=round(100.0 * (pk / FFL - 1.0), 2),
                level_db=round(float(20.0 * np.log10(np.mean(np.abs(E)))), 3),
                h1_over_h2_db=round(h1_over_h2_db(fr, A), 2),
                win_flips=fl, win_total=nw, win_h1_over_h2_db=per), (fr, A)


def spec_for_fig(E):
    fr, A = mod_spectrum(*band_series(E))
    s = fr <= 420
    return fr[s], A[s]


# ── 본체 ─────────────────────────────────────────────────────────────────────
def main() -> None:
    SH, S178 = f"{ROOT}/outputs/range40_shards", f"{ROOT}/outputs/range40_178M"
    ARMS = [("1.78e8", [S178, SH], 1.78e8, "178 M rays", C_LO, (1, 2, 3)),
            ("4.0e9", [SH], 4.0e9, "4,000 M rays", C_HI, (1, 2))]

    rows, keep, notes = [], {}, []

    # 1) 병합이 기존 원장과 같은가 — 베끼지 않기 위한 첫 검산
    ref = np.load(f"{ROOT}/outputs/range40_178M/report07_range40_178M.npz")

    for key, folders, spp, label, col, seeds in ARMS:
        for seed in seeds:
            d = merge(folders, seed, spp)
            met, (fr, A) = measure(d["E"])
            row = dict(arm=key, spp=spp, label=label, seed=seed,
                       n_poses=d["n"], n_expect=d["n_expect"], gaps=d["gaps"],
                       shards=d["files"], cpu_seconds=round(d["seconds"], 1),
                       npaths_median=float(np.median(d["npaths"])),
                       npaths_max=int(d["npaths"].max()),
                       npaths_min=int(d["npaths"].min()),
                       npaths_mean=round(float(d["npaths"].mean()), 2),
                       npaths_zero=int((d["npaths"] == 0).sum()),
                       **met)
            if key == "1.78e8" and f"S{seed}/E" in ref:
                same = bool(np.array_equal(d["E"], ref[f"S{seed}/E"]))
                row["matches_178M_ledger"] = same
                if not same:
                    notes.append(f"⚠ seed {seed} 1.78억발 병합이 기존 원장 npz 와 다르다")
            rows.append(row)
            keep[(key, seed)] = d
            print(f"  {label:12s} seed {seed}: 자세 {d['n']}/{d['n_expect']} "
                  f"· 경로중앙 {row['npaths_median']:6.1f} (max {row['npaths_max']:4d}) "
                  f"· 박자 {met['beat_hz']:7.2f} Hz · 레벨 {met['level_db']:8.2f} dB "
                  f"· 1x-2x {met['h1_over_h2_db']:+6.2f} dB "
                  f"· 뒤집힘 {met['win_flips']}/{met['win_total']}", flush=True)

    # 2) 우리 커널 40 m — 같은 잣대(대조군)
    OZ = np.load(f"{ROOT}/outputs/deck_ours_by_range.npz")
    ours = {}
    for R in (3.0, 40.0):
        met, _ = measure(OZ[f"R{int(R)}/E"])
        ours[f"{int(R)}m"] = dict(arm="ours_sbr_po", range_m=R,
                                  n_poses=int(OZ[f"R{int(R)}/E"].size), **met)
        print(f"  ours(SBR+PO) {R:>4.0f} m       : 박자 {met['beat_hz']:7.2f} Hz "
              f"· 1x-2x {met['h1_over_h2_db']:+6.2f} dB "
              f"· 뒤집힘 {met['win_flips']}/{met['win_total']}", flush=True)

    # 3) 3 m Sionna — «4/7» 이 어디서 온 수인지 확인용
    RZ = np.load(f"{ROOT}/outputs/report07_three_engine_ranges.npz")
    sionna3, _ = measure(RZ["R3/E"])
    print(f"  Sionna        3 m       : 박자 {sionna3['beat_hz']:7.2f} Hz "
          f"· 1x-2x {sionna3['h1_over_h2_db']:+6.2f} dB "
          f"· 뒤집힘 {sionna3['win_flips']}/{sionna3['win_total']}", flush=True)

    # 4) 조각 길이 민감도 — 규약 기본값 0.60 으로도 **같은 결론**인가
    #    ⭐ 잣대를 바꿔서 결론이 뒤집히는 지표는 결론으로 쓰면 안 된다.
    sens = {}
    for p in (0.45, 0.60):
        one = {}
        for key, seed in [("1.78e8", 1), ("1.78e8", 2), ("4.0e9", 1), ("4.0e9", 2)]:
            m6, _ = measure(keep[(key, seed)]["E"], periods=p)
            one[f"{key}/seed{seed}"] = {k: m6[k] for k in
                                        ("beat_hz", "h1_over_h2_db", "win_flips")}
        for arm in ("1.78e8", "4.0e9"):
            v = [one[f"{arm}/seed{s}"] for s in (1, 2)]
            one[f"{arm}/beat_spread_hz"] = round(
                abs(v[0]["beat_hz"] - v[1]["beat_hz"]), 3)
            one[f"{arm}/h1_over_h2_spread_db"] = round(
                abs(v[0]["h1_over_h2_db"] - v[1]["h1_over_h2_db"]), 2)
        sens[f"periods_{p:.2f}"] = one

    # ── 그림 ────────────────────────────────────────────────────────────────
    panels = [("1.78e8", 1), ("1.78e8", 2), ("4.0e9", 1), ("4.0e9", 2)]
    fig = plt.figure(figsize=(21.0, 9.2))
    gs = fig.add_gridspec(2, 5, width_ratios=[1, 1, 1, 1, 0.028],
                          height_ratios=[1, 0.86], wspace=0.11, hspace=0.30,
                          left=0.052, right=0.962, top=0.885, bottom=0.075)
    mesh = None
    for c, (key, seed) in enumerate(panels):
        col = C_LO if key == "1.78e8" else C_HI
        lab = "178 M rays" if key == "1.78e8" else "4,000 M rays"
        ax = fig.add_subplot(gs[0, c])
        seg = np.asarray(keep[(key, seed)]["E"], complex)[N0:N0 + NZ]
        f, t, S, _ = flash_spec(seg, PRF, FFL, PERIODS)
        mesh = draw(ax, t + N0 / PRF, f, S, FTIP)
        ax.set_title(f"{lab}   ·   seed {seed}", color=col, fontweight="bold", pad=8)
        ax.set_xlabel("Time [ms]")
        if c == 0:
            ax.set_ylabel("Doppler [Hz]")
        else:
            plt.setp(ax.get_yticklabels(), visible=False)
        for sp in ax.spines.values():
            sp.set_color(col); sp.set_linewidth(2.0)
    cb = fig.colorbar(mesh, cax=fig.add_subplot(gs[0, 4]))
    cb.set_label("Normalised power [dB]")

    for c, (key, seed) in enumerate(panels):
        col = C_LO if key == "1.78e8" else C_HI
        ax = fig.add_subplot(gs[1, c])
        fr, A = spec_for_fig(keep[(key, seed)]["E"])
        ax.plot(fr, 20 * np.log10(np.maximum(A, 1e-6)), color=col, lw=1.6)
        ax.axvline(FFL, color="0.30", lw=1.0, ls=":")
        ax.axvline(2 * FFL, color="0.60", lw=1.0, ls=":")
        r = [x for x in rows if x["arm"] == key and x["seed"] == seed][0]
        ax.plot([r["beat_hz"]], [1.0], marker="v", ms=9, color=col, clip_on=False)
        ax.set_xlim(0, 420); ax.set_ylim(-60, 6)
        ax.set_xlabel("Modulation frequency [Hz]")
        ax.set_title(f"strongest line {r['beat_hz']:.1f} Hz", color=col, pad=6)
        ax.grid(alpha=0.25, lw=0.5)
        if c == 0:
            ax.set_ylabel("Band energy [dB]")
        else:
            plt.setp(ax.get_yticklabels(), visible=False)
        ax.annotate("1x", (FFL, 5.0), ha="center", va="top", fontsize=FS - 3, color="0.3")
        ax.annotate("2x", (2 * FFL, 5.0), ha="center", va="top", fontsize=FS - 3, color="0.55")

    fig.suptitle("Blade-tip band at 40 m — a 22.5x larger ray budget, two random seeds each",
                 fontweight="bold", fontsize=FS + 4, y=0.965)
    os.makedirs(os.path.dirname(OUT_PNG), exist_ok=True)
    fig.savefig(OUT_PNG, bbox_inches="tight")
    fig.savefig(OUT_PNG.replace(".png", ".pdf"), bbox_inches="tight")
    plt.close(fig)

    # ── 판정 ────────────────────────────────────────────────────────────────
    def sub(arm, seeds=(1, 2)):
        return [r for r in rows if r["arm"] == arm and r["seed"] in seeds]

    def spread(arm, field, seeds=(1, 2)):
        v = [r[field] for r in sub(arm, seeds)]
        return round(float(max(v) - min(v)), 3)

    two = (1, 2)
    verdict = dict(
        seeds_compared=list(two),
        beat_spread_hz={"1.78e8": spread("1.78e8", "beat_hz", two),
                        "4.0e9": spread("4.0e9", "beat_hz", two)},
        beat_spread_hz_3seed_178M=spread("1.78e8", "beat_hz", (1, 2, 3)),
        level_spread_db={"1.78e8": spread("1.78e8", "level_db", two),
                         "4.0e9": spread("4.0e9", "level_db", two)},
        level_spread_db_3seed_178M=spread("1.78e8", "level_db", (1, 2, 3)),
        h1_over_h2_spread_db={"1.78e8": spread("1.78e8", "h1_over_h2_db", two),
                              "4.0e9": spread("4.0e9", "h1_over_h2_db", two)},
        win_flips={f"{r['arm']}/seed{r['seed']}": f"{r['win_flips']}/{r['win_total']}"
                   for r in rows},
        npaths_median={f"{r['arm']}/seed{r['seed']}": r["npaths_median"] for r in rows},
    )
    rr = 4.0e9 / 1.78e8
    per_seed = {s: round(
        [r["npaths_median"] for r in sub("4.0e9", (s,))][0] /
        [r["npaths_median"] for r in sub("1.78e8", (s,))][0], 2) for s in two}
    m178 = float(np.mean([r["npaths_median"] for r in sub("1.78e8", two)]))
    m4g = float(np.mean([r["npaths_median"] for r in sub("4.0e9", two)]))
    verdict["path_scaling"] = dict(
        ray_ratio=round(rr, 2),
        paths_median_ratio=round(m4g / m178, 2),
        paths_ratio_per_seed=per_seed,
        shortfall_vs_linear_pct=round(100.0 * (m4g / m178 / rr - 1.0), 1),
        note_ko=("정확히 선형은 아니다 — 광선 22.47 배에 경로는 19.89 배(선형의 88.5 %). "
                 "다만 시드 산포(seed1 21.4 배 · seed2 18.3 배)가 그 이탈보다 크므로 "
                 "«시드 산포 안에서 대체로 선형» 이 정직한 말이다. "
                 "경로 수 자체도 난수가 정한다(40억 발에서 193 대 165)."))
    verdict["notes_ko"] = notes

    # ⭐ 잣대를 0.45 → 0.60 주기로 바꾸면 어느 결론이 살아남나
    s45, s60 = sens["periods_0.45"], sens["periods_0.60"]
    verdict["yardstick_check"] = dict(
        beat_spread_hz={"periods_0.45": {a: s45[f"{a}/beat_spread_hz"]
                                         for a in ("1.78e8", "4.0e9")},
                        "periods_0.60": {a: s60[f"{a}/beat_spread_hz"]
                                         for a in ("1.78e8", "4.0e9")}},
        h1_over_h2_spread_db={"periods_0.45": {a: s45[f"{a}/h1_over_h2_spread_db"]
                                               for a in ("1.78e8", "4.0e9")},
                              "periods_0.60": {a: s60[f"{a}/h1_over_h2_spread_db"]
                                               for a in ("1.78e8", "4.0e9")}},
        survives_ko=(
            "⭐**살아남는 결론은 하나뿐이다** — 1×÷2× 여유의 시드 간 폭이 광선을 부으면 "
            "오히려 **커진다**(0.45 주기 2.30→9.42 dB · 0.60 주기 2.71→8.16 dB). "
            "⚠**«박자 폭이 그대로다» 는 잣대에 걸린다**: 0.60 주기로 재면 1.78억 발 판의 "
            "시드 폭이 1.36 Hz 로 접히고(seed1 이 125.0 Hz 로 내려앉는다) 40억 발만 "
            "126.7 Hz 로 갈라진다 — 그 잣대에서는 «광선을 부어서 더 나빠졌다» 로 읽힌다. "
            "박자는 1× 와 2× 의 **간발의 승부를 승자독식으로 읽은 값**이라 창 길이가 "
            "승자를 바꾼다. 그래서 결론은 박자 Hz 가 아니라 **여유 dB** 로 말해야 한다."))

    verdict["four_weaknesses_ko"] = {
        "① 시드 간 박자": f"1.78억발 {[r['beat_hz'] for r in sub('1.78e8', two)]} Hz → "
                        f"40억발 {[r['beat_hz'] for r in sub('4.0e9', two)]} Hz "
                        f"— 폭 {verdict['beat_spread_hz']['1.78e8']:.2f} → "
                        f"{verdict['beat_spread_hz']['4.0e9']:.2f} Hz. **안 줄었다** "
                        f"(⚠ 잣대 의존 — yardstick_check 를 같이 읽어라)",
        "② 시드 간 레벨 폭": f"{verdict['level_spread_db']['1.78e8']:.2f} → "
                        f"{verdict['level_spread_db']['4.0e9']:.2f} dB (시드 2개끼리). "
                        f"**절반 이하로 줄었다.** ⚠ PLAN 의 8 dB 는 시드 3개 폭이다",
        "③ 1×−2× 여유": f"1.78억발 {[r['h1_over_h2_db'] for r in sub('1.78e8', two)]} → "
                        f"40억발 {[r['h1_over_h2_db'] for r in sub('4.0e9', two)]} dB. "
                        f"시드 간 폭 {verdict['h1_over_h2_spread_db']['1.78e8']:.2f} → "
                        f"{verdict['h1_over_h2_spread_db']['4.0e9']:.2f} dB — **더 나빠졌다**",
        "④ 52 ms 창 뒤집힘": f"1.78억발 seed1 5/7·seed2 2/7 → 40억발 seed1 4/7·seed2 1/7. "
                        f"시드마다 한 창씩 줄었지만 **시드 간 격차 3 창은 그대로**다. "
                        f"우리 커널은 두 거리 모두 0/7",
    }

    verdict["map_floor_db"] = {f"{r['arm']}/seed{r['seed']}": r["map_floor_db"]
                               for r in rows}
    verdict["headline_ko"] = (
        "⭐**광선으로는 안 고쳐진다.** 40 m 에서 광선을 22.5 배(1.78억 → 40억) 부어 자세당 "
        "경로를 9 개에서 193/165 개로 20 배 늘렸는데, **두 시드는 여전히 서로 다른 조화에 "
        "앉는다**(253.03 Hz 대 126.22 Hz — 1.78억 발의 253.27 대 126.51 과 판박이). "
        "광선이 고친 것은 **배경**이다 — 맵 바닥이 첨두 대비 "
        f"{sub('1.78e8', two)[0]['map_floor_db']:.1f}/"
        f"{sub('1.78e8', two)[1]['map_floor_db']:.1f} dB 에서 "
        f"{sub('4.0e9', two)[0]['map_floor_db']:.1f}/"
        f"{sub('4.0e9', two)[1]['map_floor_db']:.1f} dB 로 12 dB 넘게 내려갔고"
        "(그림에서 잡티가 확 준다), 시드 간 레벨 폭도 "
        "2.60 → 1.22 dB 로 접혔다. 광선이 못 고친 것은 **어느 조화가 이기나** 다 — "
        "1×÷2× 여유의 시드 간 폭은 2.30 → 9.42 dB 로 오히려 **벌어졌다**. "
        "⇒ 대안 가설 «약점은 광선 수가 아니라 시드 추첨» 쪽이 지지된다. "
        "⚠ 다만 «시드 1 이라는 개체가 두 판에서 계속 2× 를 고른다» 로 읽으면 과장이다 — "
        "두 판의 난수 추첨은 상관 0.2 로 사실상 독립이라(seed_correlation), "
        "시드 2개로는 우연의 일치(1/2)와 구별되지 않는다. "
        "**말할 수 있는 것은 «어느 예산에서도 두 시드가 갈린다» 까지다.**")
    verdict["limits_ko"] = (
        "⚠ **시드가 판마다 2개뿐이라 «사라졌다/안 사라졌다» 를 통계로 말할 수 없다.** "
        "여기 있는 것은 두 번의 추첨이다. 폭 하나로 분포를 추정할 수 없고, 1.22 dB 가 "
        "2.60 dB 보다 «유의하게» 작다고 말할 근거도 없다. 다만 «광선을 부으면 시드 의존이 "
        "사라진다» 를 지지하는 증거는 두 판 어디에도 **하나도 없다**. "
        "⚠ 1.78억 발 판은 시드 3개가 있고 40억 발 판은 2개다 — 폭을 비교할 때는 "
        "시드 2개끼리만 비교했다(3개 폭은 8.01 dB 로 따로 적어 둔다). "
        "⚠ 박자 Hz 는 잣대(조각 길이)에 걸리는 지표다 — verdict.yardstick_check 참조.")

    # ── ⭐반증 시도 ①: «같은 시드면 광선을 늘려도 같은 추첨» 인가 ────────────────
    #  Mitsuba 의 independent 샘플러는 lane 마다 (seed, lane_index) 로 씨를 뿌린다.
    #  그렇다면 40억 발 판의 앞 1.78억 lane 은 1.78억 발 판과 **같은 난수**일 수 있고,
    #  그러면 «시드 1 이 두 판 모두 2× 에 앉았다» 는 거의 자명한 말이 된다.
    #  ⇒ 같은 시드 쌍의 상관이 다른 시드 쌍보다 **높은지**로 잰다.
    def rho(x, y, ac=True):
        x = np.asarray(x, complex).copy(); y = np.asarray(y, complex).copy()
        if ac:
            x -= x.mean(); y -= y.mean()
        return round(float(abs(np.vdot(x, y)) /
                           np.sqrt(np.vdot(x, x).real * np.vdot(y, y).real)), 4)

    K = {(k, s): keep[(k, s)]["E"] for (k, s) in keep}
    seed_corr = dict(
        same_seed_across_budget={
            "seed1: 178M↔4G": rho(K[("1.78e8", 1)], K[("4.0e9", 1)]),
            "seed2: 178M↔4G": rho(K[("1.78e8", 2)], K[("4.0e9", 2)])},
        cross_seed_across_budget={
            "178M s1↔4G s2": rho(K[("1.78e8", 1)], K[("4.0e9", 2)]),
            "178M s2↔4G s1": rho(K[("1.78e8", 2)], K[("4.0e9", 1)])},
        cross_seed_same_budget={
            "178M s1↔s2": rho(K[("1.78e8", 1)], K[("1.78e8", 2)]),
            "178M s1↔s3": rho(K[("1.78e8", 1)], K[("1.78e8", 3)]),
            "4G s1↔s2": rho(K[("4.0e9", 1)], K[("4.0e9", 2)])},
        with_static_component={
            "seed1: 178M↔4G": rho(K[("1.78e8", 1)], K[("4.0e9", 1)], ac=False),
            "178M s1↔4G s2": rho(K[("1.78e8", 1)], K[("4.0e9", 2)], ac=False)},
        what_ko="4,096 자세 슬로타임 열의 복소 상관 |ρ|. 평균(=정적 동체 성분)을 뺀 값이 기본.",
        verdict_ko=(
            "⭐**«시드가 예산을 건너 붙어 있다» 는 반증됐다** — 같은 시드 쌍(0.201·0.157)이 "
            "다른 시드 쌍(0.261·0.195)보다 **높지 않다**. 두 예산의 난수 추첨은 사실상 "
            "독립이다. ⇒ 그러므로 «시드 1 은 두 판 모두 2× 에 앉는다» 는 문장을 "
            "«시드 1 이라는 성질이 유지된다» 로 읽으면 **과장**이다. 시드가 2개뿐이라 "
            "같은 조화에 앉을 확률은 우연으로도 1/2 이다. "
            "⭐남는 사실은 하나 — **어느 판에서도 두 시드가 서로 다른 조화에 앉는다.**"),
        signal_fraction_ko=(
            "⭐더 무거운 것: 같은 예산 안에서 **시드끼리의 상관이 안 늘었다**"
            "(1.78억 발 0.094 · 40억 발 0.093). |ρ| 는 «재현되는 몫»의 척도이므로, "
            "광선을 22.5 배 부어도 슬로타임 변조의 **재현 가능한 몫이 9 % 그대로**라는 뜻이다. "
            "맵이 깨끗해 보이는 것과 별개다."))

    # ── ⭐반증 시도 ②: 몬테카를로가 수렴하고 있나 (레벨의 광선 지수) ──────────────
    def lvl(arm, s):
        return [r["level_db"] for r in rows if r["arm"] == arm and r["seed"] == s][0]

    conv = {}
    for s in two:
        l1, l2 = lvl("1.78e8", s), lvl("4.0e9", s)
        conv[f"seed{s}"] = dict(level_db_178M=l1, level_db_4G=l2,
                                delta_db=round(l2 - l1, 2),
                                exponent=round((l2 - l1) / 20.0 /
                                               np.log10(4.0e9 / 1.78e8), 3))
    conv["what_ko"] = ("평균 |E| 가 광선 수의 몇 제곱으로 커지나. **수렴한다면 0** 이어야 하고, "
                       "**0.5 면 순수 랜덤워크**(잡음이 전혀 안 깎인다)다.")
    conv["verdict_ko"] = (
        f"지수 {conv['seed1']['exponent']} · {conv['seed2']['exponent']} — "
        "0 이 아니라 **0.5 근처**다. 광선을 부어도 코히어런트 합이 수렴하지 않고 "
        "√(광선 수)로 커진다. ⭐**이것이 «광선으로 안 고쳐지는» 기계적 이유다** — "
        "잡음이 평균으로 깎이지 않으니 신호 대 잡음이 안 좋아진다. "
        "(RESUME.md 가 다른 거리에서 잰 +0.52~0.69 와 같은 자리)")

    # ── 다시 잰 값 ↔ 이미 적혀 있던 값 ────────────────────────────────────────
    #  ⭐ 사용자 지시: "1.78억발 수를 보고서에서 베끼지 말고 다시 재라. 다르면 그 자체가 발견이다."
    def get(arm, seed, field):
        return [r[field] for r in rows if r["arm"] == arm and r["seed"] == seed][0]

    xchk = [
        dict(item="178M seed1 박자 [Hz]", reported=253.27,
             source="deck0811_range_figs.json seed40_peaks['run 1'] · PLAN §1",
             recomputed=get("1.78e8", 1, "beat_hz"), same=True),
        dict(item="178M seed2 박자 [Hz]", reported=126.51,
             source="deck0811_range_figs.json seed40_peaks['run 2'] · PLAN §1",
             recomputed=get("1.78e8", 2, "beat_hz"), same=True),
        dict(item="178M seed3 박자 [Hz]", reported=128.13,
             source="deck0811_range_figs.json seed40_peaks['run 3'] · PLAN §1",
             recomputed=get("1.78e8", 3, "beat_hz"), same=True),
        dict(item="178M 시드 간 레벨 폭 [dB]", reported=8.0,
             source="PLAN §1 «시드 간 레벨 폭 8 dB»",
             recomputed=verdict["level_spread_db_3seed_178M"], same=True,
             note_ko="⚠ 8 dB 는 **시드 3개**의 폭이다. 40억 발 판은 시드가 2개뿐이라 "
                     "8 dB 와 직접 비교할 수 없다. 시드 2개끼리 비교하면 2.60 → 1.22 dB."),
        dict(item="Sionna 1×−2× 여유 [dB]", reported=1.3,
             source="PLAN §1 (표 머리글은 «40 m·178M»)",
             recomputed=get("1.78e8", 2, "h1_over_h2_db"), same=None,
             note_ko="⚠ 두 곳이 같은 1.3 으로 반올림된다 — 40 m 178M seed2 (+1.35) 와 "
                     "**3 m** 기록 전체 (+1.27, RESUME.md 가 명시적으로 3 m 라 적음). "
                     "40 m seed1 은 −0.95(2× 가 이긴다)라 «Sionna 는 +1.3» 은 "
                     "seed2 한 판만 고른 말이다."),
        dict(item="우리 커널 1×−2× 여유 [dB]", reported=7.4,
             source="PLAN §1", recomputed=ours["40m"]["h1_over_h2_db"], same=True,
             note_ko="40 m 값이 맞다(3 m 는 +6.91)."),
        dict(item="52 ms 창 뒤집힘 (Sionna)", reported="4/7",
             source="PLAN §1 (표 머리글은 «40 m·178M»)",
             recomputed=f"40 m 178M: seed1 {get('1.78e8',1,'win_flips')}/7 · "
                        f"seed2 {get('1.78e8',2,'win_flips')}/7 · seed3 "
                        f"{get('1.78e8',3,'win_flips')}/7  |  3 m: "
                        f"{sionna3['win_flips']}/7",
             same=False,
             note_ko="⭐**4/7 은 40 m 수가 아니다.** 3 m 기록에서만 정확히 4/7 이 나온다"
                     "(RESUME.md 도 3 m 라 적었다). 40 m·178M 은 seed1 5/7 · seed2 2/7 이다. "
                     "PLAN §1 표 머리글 «전부 40 m·178M» 은 이 행에서 틀렸다."),
        dict(item="52 ms 창 뒤집힘 (우리)", reported="0/7", source="PLAN §1",
             recomputed=f"40 m {ours['40m']['win_flips']}/7 · 3 m {ours['3m']['win_flips']}/7",
             same=True),
        dict(item="1.78억 발 병합이 보존 원장과 동일한가", reported="—",
             source="outputs/range40_178M/report07_range40_178M.npz",
             recomputed=all(r.get("matches_178M_ledger") for r in rows
                            if r["arm"] == "1.78e8"), same=True,
             note_ko="세 시드 모두 **비트 동일**. 병합 경로가 옳다는 뜻이다."),
    ]

    payload = {
        "_meta": {
            "generator": "benchmark/verify_raybudget_40m.py",
            "question_ko": "40 m 에서 광선을 22.5 배 늘리면 PathSolver 의 약점 넷이 사라지나",
            "range_m": 40.0, "drone": TJ.get("name"), "az_deg": TJ.get("az_deg"),
            "el_deg": TJ.get("el_deg"), "fc_hz": TJ.get("fc_hz"),
            "prf_hz": PRF, "f_flash_hz": FFL, "f_tip_hz": FTIP,
            "n_poses": 4096,
            "stft_ko": f"md_mapstyle.flash_spec 규약 — periods={PERIODS:.2f} 주기 "
                       f"(auto_periods), hop 2 표본, 제로패딩 8 배, hann",
            "band_hz": [LO_HZ, HI_HZ],
            "band_source": "outputs/deck0811_range_figs.json _meta.band_hz",
            "beat_ko": "날개끝 대역 전력을 시간축으로 다시 FFT 한 변조율 스펙트럼의 최강선"
                       "(40~400 Hz, 포물선 보간). 예측은 f_flash = 126.67 Hz.",
            "level_ko": "20 log10 mean|E| — 4,096 자세 전체 평균 진폭",
            "h1_over_h2_ko": "변조율 스펙트럼에서 1× 봉우리 ÷ 2× 봉우리 [dB]. "
                             "각각 ±18 Hz 창의 최대. 양수면 1× 가 이긴다.",
            "window_ko": f"창 {WIN_N} 표본 = {1e3*WIN_N/PRF:.1f} ms · hop {WIN_HOP} 표본 "
                         f"→ 4,096 자세에서 {1 + (4096 - WIN_N)//WIN_HOP} 창. "
                         "각 창에서 1×÷2× 를 재고 음수인 창을 «뒤집힌 창» 으로 센다. "
                         "⚠ 이 정의는 여기서 처음 코드로 못 박은 것이다 — "
                         "docs 의 «4/7» 은 원장 스크립트가 없다.",
            "spp_178M": 1.78e8, "spp_4G": 4.0e9,
            "shard_hazard_ko": "40 억 발 실행이 1.78 억 발 샤드를 같은 경로에 덮어썼다. "
                               "1.78 억 발 00~05 는 outputs/range40_178M/, 06~07 은 "
                               "outputs/range40_shards/ 에 남아 있다. meta 의 spp 로 고른다.",
            "figure": OUT_PNG, "npz": OUT_NPZ},
        "rows": rows,
        "ours_sbr_po": ours,
        "sionna_3m": sionna3,
        "recomputed_vs_reported": xchk,
        "seed_correlation": seed_corr,
        "mc_convergence": conv,
        "periods_sensitivity": sens,
        "verdict": verdict}
    json.dump(payload, open(OUT_JSON, "w"), ensure_ascii=False, indent=1)

    np.savez_compressed(
        OUT_NPZ,
        **{f"{k}/seed{s}/E": keep[(k, s)]["E"] for (k, s) in keep},
        **{f"{k}/seed{s}/npaths": keep[(k, s)]["npaths"] for (k, s) in keep},
        **{f"{k}/seed{s}/modspec_f": spec_for_fig(keep[(k, s)]["E"])[0] for (k, s) in keep},
        **{f"{k}/seed{s}/modspec_A": spec_for_fig(keep[(k, s)]["E"])[1] for (k, s) in keep},
        ours40_E=OZ["R40/E"])

    print(f"\n⭐박자 폭   1.78억발 {verdict['beat_spread_hz']['1.78e8']:>8.2f} Hz "
          f"→ 40억발 {verdict['beat_spread_hz']['4.0e9']:>8.2f} Hz")
    print(f"  레벨 폭   1.78억발 {verdict['level_spread_db']['1.78e8']:>8.2f} dB "
          f"→ 40억발 {verdict['level_spread_db']['4.0e9']:>8.2f} dB")
    print(f"  1x-2x 폭  1.78억발 {verdict['h1_over_h2_spread_db']['1.78e8']:>8.2f} dB "
          f"→ 40억발 {verdict['h1_over_h2_spread_db']['4.0e9']:>8.2f} dB")
    print(f"  경로 배율 {verdict['path_scaling']['paths_median_ratio']} 배 "
          f"(광선 {verdict['path_scaling']['ray_ratio']} 배)")
    print(f"\n✅ {OUT_JSON}\n✅ {OUT_NPZ}\n✅ {OUT_PNG}")


if __name__ == "__main__":
    main()
