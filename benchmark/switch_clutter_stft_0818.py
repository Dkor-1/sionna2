# -*- coding: utf-8 -*-
"""
switch_clutter_stft_0818.py — 클러터를 제대로 지우고 다시 그린 STFT
================================================================================

왜
--
지금까지의 «정지 성분 제거» 판은 **평균 한 값만** 뺀 것이다(도플러 0 Hz 한 칸). 실제 레이다는
정지 클러터를 **띠로** 지운다. 이 파일은 표준 방식 둘을 걸고 같은 자리에서 다시 그린다.

  ⓐ **평균 빼기** — 지금까지 쓰던 판 (도플러 0 Hz 한 칸)
  ⓑ ⭐**ECA 계열 부분공간 소거** — 느린시간에서 |f| ≤ f_cut 인 도플러 부분공간을 **투영으로**
     들어낸다. DFT 격자 위에서 그 부분공간은 직교라 정확히 «그 칸들을 0 으로» 와 같다.
     f_cut = 100 Hz — 날개 박자 첫 선(126.7 Hz)보다 **아래**라 신호는 안 건드린다.
  ⓒ **3-펄스 MTI** — 교과서 대조군 (1, −2, 1) 캔슬러.

⭐적대적 대조 (같은 처리를 통과시킨다)
  A1 백색잡음 → 리듬 몫이 백색값(12.6 %)에서 안 움직여야 한다. 움직이면 처리가 무늬를 **만드는** 것.
  A2 순수 정지 신호(상수) → 처리 뒤 거의 0 이어야 한다.
  A3 봉우리 자리 — 처리 전후로 1 차 선 자리가 126.1 Hz 에서 안 움직여야 한다.
  A4 몫과 절대 dB 를 **함께** 낸다 — 몫만 보면 «분모가 준 것» 을 «신호가 는 것» 으로 오독한다.

⛔GPU 없음. 산출: outputs/switch_grid_clutter_0818.json ·
   outputs/figures/swgrid_maps_eca.png

실행:  cd /workspace/sionna && PYTHONPATH=src:benchmark \
       /workspace/.venvs/py312/bin/python benchmark/switch_clutter_stft_0818.py
"""
from __future__ import annotations

import glob
import json
import os
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                        # noqa: E402
import numpy as np                                                     # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)
from md_mapstyle import auto_periods, flash_spec, draw                 # noqa: E402

SHD = os.path.join(ROOT, "outputs", "elev_sweep_shards")
FIG = os.path.join(ROOT, "outputs", "figures")
OUT = os.path.join(ROOT, "outputs", "switch_grid_clutter_0818.json")

TJ = json.load(open(os.path.join(ROOT, "outputs", "switch_grid.json")))["_meta"]
EL = float(TJ["el_deg"])
PRF = 19700.0
FFL = float(TJ["f_flash_hz"])
FTIP = float(TJ["f_tip_hz"])
HW = 8.0
FCUT = 100.0                        # ⭐ECA 노치 반폭 — f_flash(126.7) 보다 아래
PERIODS = auto_periods(PRF, FFL)
T0, TSPAN = 0.0, 0.058              # 맵 창 — 기존 그림과 같은 자리

ARMS = [
    ("ours_r15_n8192", "Our kernel"),
    ("sionna_p4000000000_r15_n8192_d1", "all off"),
    ("sionna_p4000000000_onlyrefr_r15_n8192", "refraction only"),
    ("sionna_p4000000000_onlyedge_r15_n8192", "edge only"),
    ("sionna_p4000000000_onlydiffr_r15_n8192", "diffraction only"),
    ("sionna_p4000000000_swR0D1E1F1_r15_n8192_d1", "diffraction + edge"),
    ("sionna_p4000000000_swR1D1E0F1_r15_n8192_d1", "refraction + diffraction"),
    ("sionna_p4000000000_phys_r15_n8192_d1", "all on"),
]


def load(arm: str):
    fs = sorted(glob.glob(f"{SHD}/{arm}_el{EL:+.0f}_*.npz"))
    E = seen = None
    for f in fs:
        d = np.load(f)
        n = int(np.asarray(d["meta"], float)[3])
        if E is None:
            E = np.zeros(n, complex)
            seen = np.zeros(n, bool)
        ii = d["idx"].astype(int)
        E[ii] = d["E"]
        seen[ii] = True
    if E is None:
        raise SystemExit(f"⛔ 샤드가 없다: {arm}")
    return E, int((~seen).sum())


# ── 클러터 소거 세 가지 ────────────────────────────────────────────────────
def cs_mean(x):
    """ⓐ 평균 빼기 — 도플러 0 Hz 한 칸."""
    return x - x.mean()


def cs_eca(x, fcut=FCUT):
    """ⓑ ECA 계열 — |f| ≤ fcut 도플러 부분공간을 투영으로 들어낸다.

    DFT 격자 위의 복소지수들은 서로 직교하므로, 그 부분공간에 대한 직교투영은
    해당 칸을 0 으로 두는 것과 **정확히** 같다(별도 최소제곱 풀이가 필요없다).
    """
    X = np.fft.fft(x)
    fr = np.fft.fftfreq(x.size, 1.0 / PRF)
    X[np.abs(fr) <= fcut] = 0.0
    return np.fft.ifft(X)


def cs_mti3(x):
    """ⓒ 3-펄스 MTI (1, −2, 1) — 교과서 대조군. 길이가 2 줄어든다."""
    return x[2:] - 2.0 * x[1:-1] + x[:-2]


CS = [("raw", "no suppression", lambda v: v),
      ("mean", "mean removed", cs_mean),
      ("eca", f"ECA notch |f| <= {FCUT:.0f} Hz", cs_eca),
      ("mti3", "3-pulse MTI", cs_mti3)]


# ── 잣대 ──────────────────────────────────────────────────────────────────
def metrics(x):
    ac = x - x.mean()
    n = ac.size
    P = np.abs(np.fft.fft(ac * np.hanning(n))) ** 2
    fr = np.fft.fftfreq(n, 1.0 / PRF)
    ab = np.abs(fr) >= FTIP
    k = np.round(np.abs(fr) / FFL)
    on = np.abs(np.abs(fr) - k * FFL) <= HW
    comb_bins, floor_bins = ab & on, ab & ~on
    comb_db = float(10 * np.log10(P[comb_bins].mean() / P[floor_bins].mean()))
    # 1 차 선 자리 — 블레이드 대역 전력의 변조 스펙트럼
    nper = max(8, int(round(0.45 * PRF / FFL)))
    from numpy.lib.stride_tricks import sliding_window_view
    w = np.hanning(nper + 1)[:-1]
    frm = sliding_window_view(ac, nper)[::2]
    S = np.abs(np.fft.fft(frm * w, n=8 * nper, axis=1)).T / w.sum()
    f2 = np.fft.fftshift(np.fft.fftfreq(8 * nper, 1.0 / PRF))
    S = np.fft.fftshift(S, axes=0)
    m2 = (np.abs(f2) >= 0.35 * FTIP) & (np.abs(f2) <= FTIP)
    g = (S ** 2)[m2, :].sum(axis=0)
    Y = np.abs(np.fft.rfft((g - g.mean()) * np.hanning(g.size))) ** 2
    fr2 = np.fft.rfftfreq(g.size, 1.0 / (PRF / 2.0))
    b = int(round(FFL / (fr2[1] - fr2[0])))
    pk = max(0, b - 6) + int(np.argmax(Y[max(0, b - 6):b + 7]))
    return dict(
        ac_db=round(float(10 * np.log10((np.abs(ac) ** 2).mean())), 2),
        above_tip_pct=round(float(100 * P[ab].sum() / P.sum()), 2),
        rhythm_pct=round(float(100 * P[comb_bins].sum() / P[ab].sum()), 2),
        comb_over_floor_db=round(comb_db, 2),
        h1_peak_hz=round(float(fr2[pk]), 2),
        lag1=round(float(abs(np.vdot(ac[:-1], ac[1:])) / np.vdot(ac, ac).real), 4))


def band_eca(data, lo, hi, stem):
    """블레이드 대역 에너지 — 클러터 소거를 **먼저 걸고** 나서 스펙트럼으로 만든다.

    배치는 기존 빌더 band() 와 같게 둔다(우리 커널을 옅게 깔고 조합 하나만 진하게).
    잣대 식은 build_switch_grid_figs.modspec 을 **그대로 가져다 쓴다** — 정본은 구현이
    하나여야 한다(다시 짜면 두 그림이 다른 잣대를 쓰게 된다).
    """
    import build_switch_grid_figs as B                                  # noqa: E402
    fr0, Y0 = B.modspec(cs_eca(data[ARMS[0][0]]))
    m0 = (fr0 >= lo) & (fr0 <= hi)
    ref_db = 10 * np.log10(Y0[m0] / Y0[m0].max())
    fig, ax = plt.subplots(2, 4, figsize=(27.0, 9.6), sharex=True, sharey=True)
    for i, (arm, nm) in enumerate(ARMS):
        a = ax[i // 4, i % 4]
        if i:
            a.plot(fr0[m0], ref_db, color="#c62828", lw=1.2, alpha=0.35, label="Our kernel")
        fr, Y = B.modspec(cs_eca(data[arm]))
        m = (fr >= lo) & (fr <= hi)
        a.plot(fr[m], 10 * np.log10(Y[m] / Y[m].max()),
               color="#c62828" if not i else "#1565c0", lw=1.8, label=nm)
        for k in range(max(1, int(np.ceil(lo / FFL))), int(hi / FFL) + 1):
            a.axvline(k * FFL, color="0.35", ls="--", lw=1.0, zorder=1)
        a.set_xlim(lo, hi)
        if hi > 500:
            a.set_xticks(np.arange(200, hi + 1, 200))
        a.set_ylim(-52, 4)
        a.set_title(nm, pad=7)
        a.grid(alpha=0.25)
        a.set_axisbelow(True)
        if i % 4 == 0:
            a.set_ylabel("line level [dB]")
        if i // 4 == 1:
            a.set_xlabel("modulation rate [Hz]")
        if i == 1:
            a.legend(fontsize=13, loc="lower right", framealpha=0.95)
    fig.subplots_adjust(top=0.865, bottom=0.10, left=0.055, right=0.985,
                        hspace=0.22, wspace=0.06)
    fig.text(0.5, 0.945, "after cancelling static clutter, blade band power over time turned "
                         f"into a spectrum, dashed lines mark {FFL:.1f} Hz and its multiples, "
                         "the faint red curve repeats our kernel for reference",
             ha="center", fontsize=18, color="0.35")
    out = f"{FIG}/{stem}.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  ✅ {out}")


def main() -> None:
    t0 = time.time()
    data, table = {}, {}
    print("═══ 클러터 소거 뒤 잣대 ═══")
    for arm, nm in ARMS:
        E, miss = load(arm)
        if miss:
            raise SystemExit(f"⛔ {nm}: 결측 {miss} 자세 — 채우고 다시 (주기 0 이 무늬를 만든다)")
        data[arm] = E
        row = {}
        for key, _lab, fn in CS:
            row[key] = metrics(fn(E))
        # 노치가 들어낸 전력 몫 = 정지 클러터가 차지하던 몫
        p_all = float((np.abs(E - E.mean()) ** 2).sum())
        p_eca = float((np.abs(cs_eca(E)) ** 2).sum())
        row["clutter_removed_pct"] = round(100 * (1 - p_eca / max(p_all, 1e-300)), 2)
        table[nm] = row
        print(f"  {nm:26s} 리듬 평균빼기 {row['mean']['rhythm_pct']:5.1f} % → "
              f"ECA {row['eca']['rhythm_pct']:5.1f} % · 빗살 "
              f"{row['mean']['comb_over_floor_db']:+6.2f} → "
              f"{row['eca']['comb_over_floor_db']:+6.2f} dB · "
              f"노치가 들어낸 몫 {row['clutter_removed_pct']:5.1f} %")

    # ── 적대적 대조 ────────────────────────────────────────────────────
    rng = np.random.default_rng(11)
    n = data[ARMS[0][0]].size
    adv = {}
    w = rng.normal(size=n) + 1j * rng.normal(size=n)
    adv["A1_white_through_pipeline"] = {k: metrics(fn(w)) for k, _l, fn in CS}
    const = np.full(n, 3.0 + 1.0j)
    adv["A2_pure_static"] = dict(
        raw_power_db=round(float(10 * np.log10((np.abs(const) ** 2).mean())), 2),
        after_eca_power_db=round(float(10 * np.log10(
            max((np.abs(cs_eca(const)) ** 2).mean(), 1e-300))), 2))
    adv["A3_peak_moves"] = {nm: dict(mean_hz=table[nm]["mean"]["h1_peak_hz"],
                                     eca_hz=table[nm]["eca"]["h1_peak_hz"])
                            for nm in table}
    adv["A4_note_ko"] = ("몫과 절대 dB 를 함께 싣는다 — 리듬 몫이 올라도 ac_db 가 같이 "
                         "내려갔으면 «신호가 늘어난 것» 이 아니라 «분모가 준 것» 이다.")
    adv["reading_ko"] = ("A1 이 백색값 12.6 % 에서 안 움직이면 이 처리는 없는 무늬를 "
                         "만들지 않는다. A2 가 −300 dB 급이면 정지 성분은 실제로 다 지워진다.")
    print("\n═══ 적대적 대조 ═══")
    for k, _l, _f in CS:
        v = adv["A1_white_through_pipeline"][k]
        print(f"  A1 백색 {k:5s}: 리듬 {v['rhythm_pct']:5.2f} % (백색값 12.63) · "
              f"빗살 {v['comb_over_floor_db']:+.2f} dB")
    print(f"  A2 순수 정지: {adv['A2_pure_static']['raw_power_db']:.1f} dB → "
          f"{adv['A2_pure_static']['after_eca_power_db']:.1f} dB")
    moved = [nm for nm, v in adv["A3_peak_moves"].items() if v["mean_hz"] != v["eca_hz"]]
    print(f"  A3 봉우리 자리가 움직인 팔: {moved if moved else '없음'}")

    # ── 그림 ────────────────────────────────────────────────────────────
    skip_maps = "--skip-maps" in sys.argv
    n0, nz = int(round(T0 * PRF)), int(round(TSPAN * PRF))
    if skip_maps:
        print("\n(맵은 건너뛴다 — 대역 에너지 그림만)")
    fig, ax = plt.subplots(2, 4, figsize=(27.0, 9.6), sharex=True, sharey=True)
    for i, (arm, nm) in enumerate(ARMS):
        a = ax[i // 4, i % 4]
        E = cs_eca(data[arm][n0:n0 + nz])
        f, t, S, _ = flash_spec(E, PRF, FFL, PERIODS)
        draw(a, t, f, S, FTIP)
        a.set_ylim(-2000, 2000)
        a.set_title(nm, pad=7)
        if i % 4 == 0:
            a.set_ylabel("Doppler [Hz]")
        if i // 4 == 1:
            a.set_xlabel("time [ms]")
    fig.subplots_adjust(top=0.865, bottom=0.10, left=0.055, right=0.945,
                        hspace=0.22, wspace=0.08)
    fig.text(0.5, 0.945, f"static clutter cancelled by projecting out Doppler within "
                         f"{FCUT:.0f} Hz of zero, every run looking up from 30{chr(176)} below the drone, "
                         "each panel scaled to its own peak",
             ha="center", fontsize=19, color="0.35")
    cax = fig.add_axes([0.953, 0.10, 0.008, 0.765])
    cb = fig.colorbar(ax[0, 0].collections[0], cax=cax)
    cb.set_label("dB below the brightest point in that panel", fontsize=16)
    p = f"{FIG}/swgrid_maps_eca.png"
    if not skip_maps:
        fig.savefig(p, dpi=150)
    plt.close(fig)

    print("\n═══ 대역 에너지 (클러터 소거 뒤) ═══")
    band_eca(data, 100.0, 1000.0, "swgrid_be_wide_eca")
    band_eca(data, 0.0, 420.0, "swgrid_be_zoom_eca")

    doc = {"_meta": {
        "generator": "benchmark/switch_clutter_stft_0818.py",
        "generated_kst": time.strftime("%Y-%m-%d %H:%M:%S (UTC+9)",
                                       time.gmtime(time.time() + 9 * 3600)),
        "purpose_ko": "정지 클러터를 제대로 지운 뒤의 STFT 와 잣대",
        "gpu_used": False,
        "el_deg": EL, "prf_hz": PRF, "f_tip_hz": FTIP, "f_flash_hz": FFL,
        "f_cut_hz": FCUT,
        "methods_ko": {k: l for k, l, _f in CS},
        "elapsed_s": round(time.time() - t0, 2),
    }, "cells": table, "adversarial": adv, "figures": ["outputs/figures/swgrid_maps_eca.png",
                "outputs/figures/swgrid_be_wide_eca.png",
                "outputs/figures/swgrid_be_zoom_eca.png"]}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print(f"\nsaved {OUT}\nsaved {p}")


if __name__ == "__main__":
    main()
