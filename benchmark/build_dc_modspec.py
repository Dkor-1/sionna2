# -*- coding: utf-8 -*-
"""
build_dc_modspec.py — **정지 성분(DC)을 빼기 전과 뺀 뒤**를 네 판으로 나란히 낸다.

사용자 지시(2026-08-14): 「물리 on/off 까지 비교한 STFT 결과물, 블레이드 대역 전력의
변조 스펙트럼, DC 제거를 한 이후의 변조 스펙트럼 및 그 상태에서의 블레이드 대역 전력의
변조 스펙트럼까지 다 실어서 정리해 줘」.

왜 DC 를 빼나
-------------
자세 시계열 E 에서 **평균**은 «자세가 바뀌어도 안 변하는 성분» 이다 — 가만히 있는 동체의
반사다. 그것이 맵 에너지의 32~66 % 를 차지해 색눈금과 대역 전력을 모두 가져간다.
평균을 빼면 남는 것이 **움직이는 것만** 이라, 세 팔의 차이가 드러난다.

⚠주의 — 이 빼기는 «잣대» 가 아니다. 2026-08-14 적대 검증이 무너뜨린 AC/DC 는 뺀 **뒤의
크기를 팔끼리 dB 로 견준** 것이었다. 여기서는 크기를 견주지 않고 **모양**만 본다.

굽는 것
    outputs/dc_modspec.json                        네 판의 수치(리포트가 인용한다)
    outputs/figures/dcms_stft_raw.png              ① STFT — 뺀 적 없음
    outputs/figures/dcms_band_raw.png              ② 대역 전력의 변조 스펙트럼 — 뺀 적 없음
    outputs/figures/dcms_stft_dc.png               ③ STFT — 정지 성분 제거
    outputs/figures/dcms_band_dc.png               ④ 대역 전력의 변조 스펙트럼 — 제거 후

    PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/build_dc_modspec.py
"""
from __future__ import annotations

import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                       # noqa: E402
import numpy as np                                                    # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, HERE)
from md_mapstyle import auto_periods, flash_spec, draw                 # noqa: E402
from comb_snr import band_g                                            # noqa: E402

FIG = os.path.join(ROOT, "outputs", "figures")
os.makedirs(FIG, exist_ok=True)

J = json.load(open(f"{ROOT}/outputs/elevation_sweep_md.json"))
Z = np.load(f"{ROOT}/outputs/elevation_sweep_md.npz", allow_pickle=True)
M = J["_meta"]
assert int(np.asarray(Z["phase_sign_v2"]).ravel()[0]) == 1, "⛔ 부호 정정본이 아니다"

PRF = float(M["prf_hz"])
FFL = float(M["f_flash_hz"])
PERIODS = auto_periods(PRF, FFL)
ROW = {(r["engine"], r["el_deg"]): r for r in J["rows"]}
ELS = [0.0, -30.0, -60.0]

ARMS = [
    ("ours_r15_n8192", "Our kernel", "#c62828"),
    ("sionna_p4000000000_r15_n8192_d1", "Sionna, physics off", "#8e9aab"),
    ("sionna_p4000000000_phys_r15_n8192_d1", "Sionna, physics on", "#1565c0"),
]
SHORT = {"Our kernel": "Ours", "Sionna, physics off": "Physics off",
         "Sionna, physics on": "Physics on"}
T0, TSPAN = 0.020, 0.060

plt.rcParams.update({
    "font.size": 19, "axes.titlesize": 22, "axes.labelsize": 19,
    "xtick.labelsize": 17, "ytick.labelsize": 17,
    "figure.facecolor": "white", "savefig.facecolor": "white",
})


def series(arm, el, *, drop_dc):
    E = np.asarray(Z[f"{arm}/el{el:+.0f}"], complex)
    return E - E.mean() if drop_dc else E


# ══ ①③ STFT 격자 ═══════════════════════════════════════════════════════════
def stft_grid(drop_dc, stem):
    n0, nz = int(round(T0 * PRF)), int(round(TSPAN * PRF))
    fig, ax = plt.subplots(len(ELS), 3, figsize=(27.5, 3.1 * len(ELS) + 0.5),
                           sharex=True, sharey=True)
    for r, el in enumerate(ELS):
        for c, (arm, nm, _c) in enumerate(ARMS):
            a = ax[r, c]
            E = series(arm, el, drop_dc=drop_dc)[n0:n0 + nz]
            f, t, S, _ = flash_spec(E, PRF, FFL, PERIODS)
            draw(a, t, f, S, float(ROW[(arm, el)]["f_tip_hz"]))
            a.set_ylim(-2000, 2000)
            if r == 0:
                a.set_title(SHORT[nm], pad=8)
            if c == 0:
                a.set_ylabel(("looking level" if el == 0 else
                              f"{abs(el):.0f}" + chr(176) + " below")
                             + "\nDoppler [Hz]")
            if r == len(ELS) - 1:
                a.set_xlabel("time [ms]")
    cb = fig.colorbar(ax[0, 0].collections[0], ax=ax, fraction=0.014, pad=0.008)
    cb.set_label("dB below the brightest point in that panel", fontsize=17)
    out = f"{FIG}/{stem}.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✅ {out}")


# ══ ②④ 대역 전력의 변조 스펙트럼 ═══════════════════════════════════════════
def band_spec(E, el):
    """블레이드 대역 전력 g(t) 의 변조 스펙트럼.

    반환 (주파수, 선 전력 Y, 국소 바닥) — **같은 배열**에서 dB 도 바닥도 낸다.
    ⚠전에 정규화한 dB 를 되돌려 원 배열의 바닥으로 나눴다가 120~256 dB 가 나왔다.
    """
    g, fs = band_g(E, PRF, el)
    if g is None:
        return None, None, None
    n = g.size
    Y = np.abs(np.fft.rfft((g - g.mean()) * np.hanning(n))) ** 2
    fr = np.fft.rfftfreq(n, 1.0 / fs)
    floor = float(np.median(Y[(fr > 20) & (fr < 500)]))
    return fr, Y, floor


def band_grid(drop_dc, stem, rec):
    fig, ax = plt.subplots(1, len(ELS), figsize=(26.0, 8.2), sharey=True)
    for j, el in enumerate(ELS):
        a = ax[j]
        for arm, nm, col in ARMS:
            fr, Y, floor = band_spec(series(arm, el, drop_dc=drop_dc), el)
            if fr is None:
                continue
            m = fr <= 420.0
            a.plot(fr[m], 10 * np.log10(Y[m] / Y[m].max()), color=col, lw=2.2, label=nm)
            # 원장에 남길 값 — 1·2·3 차 선이 국소 바닥 위 몇 dB 인가
            df = fr[1] - fr[0]
            key = f"{'dc_removed' if drop_dc else 'raw'}/{nm}/el{el:+.0f}"
            rec[key] = {}
            for k in (1, 2, 3):
                b = int(round(k * FFL / df))
                seg = Y[max(0, b - 3):b + 4]
                rec[key][f"h{k}_over_floor_db"] = (
                    None if seg.size == 0 else round(float(10 * np.log10(seg.max() / floor)), 2))
                pk = max(0, b - 6) + int(np.argmax(Y[max(0, b - 6):b + 7]))
                rec[key][f"h{k}_peak_hz"] = round(float(fr[pk]), 2)
        for k in (1, 2, 3):
            a.axvline(k * FFL, color="0.35", ls="--", lw=1.4, zorder=1)
        a.set_xlim(0, 420)
        a.set_ylim(-50, 4)
        a.set_title("looking level" if el == 0 else
                    "looking up from " + f"{abs(el):.0f}" + chr(176) + " below", pad=8)
        a.set_xlabel("modulation rate [Hz]")
        a.grid(alpha=0.25)
        a.set_axisbelow(True)
        if j == 0:
            a.set_ylabel("line level [dB]")
            a.legend(fontsize=17, loc="lower right", framealpha=0.95)
    fig.subplots_adjust(top=0.885, bottom=0.105, left=0.055, right=0.985, wspace=0.06)
    fig.text(0.5, 0.945, f"dashed lines mark {FFL:.1f} Hz and its multiples, "
                         f"the rate the blades should make",
             ha="center", fontsize=19, color="0.35")
    out = f"{FIG}/{stem}.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  ✅ {out}")


def dc_share():
    """맵 에너지에서 «0 Hz 근처» 가 차지하는 몫 — 왜 빼는지의 근거."""
    n0, nz = int(round(T0 * PRF)), int(round(TSPAN * PRF))
    out = {}
    for el in ELS:
        for arm, nm, _c in ARMS:
            E = np.asarray(Z[f"{arm}/el{el:+.0f}"], complex)[n0:n0 + nz]
            f, t, S, _ = flash_spec(E, PRF, FFL, PERIODS)
            P = S ** 2
            out[f"{nm}/el{el:+.0f}"] = round(
                float(100.0 * P[np.abs(f) < 150].sum() / P.sum()), 2)
    return out


if __name__ == "__main__":
    print("═══ 정지 성분 제거 전후 ═══")
    rec = {}
    stft_grid(False, "dcms_stft_raw")
    band_grid(False, "dcms_band_raw", rec)
    stft_grid(True, "dcms_stft_dc")
    band_grid(True, "dcms_band_dc", rec)

    doc = {
        "_meta": {
            "generator": "benchmark/build_dc_modspec.py",
            "purpose_ko": "정지 성분(DC)을 빼기 전과 뺀 뒤를 STFT 와 대역 전력 변조 "
                          "스펙트럼 두 축으로 나란히 낸다",
            "dc_meaning_ko": "자세 시계열 E 의 평균 — 자세가 바뀌어도 안 변하는 성분이라 "
                             "가만히 있는 동체의 반사다",
            "warning_ko": "⚠뺀 뒤의 **크기**를 팔끼리 dB 로 견주지 마라. 2026-08-14 검증이 "
                          "무너뜨린 AC/DC 가 정확히 그 실수다. 여기서 읽는 것은 모양과 "
                          "선의 자리(peak position)뿐이다",
            "band_ko": "블레이드 대역 = 0.35~1.0 × f_tip(el), benchmark/comb_snr.py:band_g",
            "stft_ko": f"flash_spec 기본값 — 블레이드 주기의 {PERIODS:.2f} 배 조각, hop 2",
            "f_flash_hz": FFL,
            "prf_hz": PRF,
            "elevations_deg": ELS,
            "figures": ["outputs/figures/dcms_stft_raw.png",
                        "outputs/figures/dcms_band_raw.png",
                        "outputs/figures/dcms_stft_dc.png",
                        "outputs/figures/dcms_band_dc.png"],
        },
        "dc_share_pct": dc_share(),
        "lines": rec,
    }
    p = f"{ROOT}/outputs/dc_modspec.json"
    json.dump(doc, open(p, "w"), ensure_ascii=False, indent=1)
    print(f"  ✅ {p}")
