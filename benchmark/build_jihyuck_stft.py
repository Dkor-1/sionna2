# -*- coding: utf-8 -*-
"""
build_jihyuck_stft.py — 선배(jihyuck) PX4 파이프라인 산출물의 **STFT 맵**을 그린다.

사용자 지시(2026-08-14): 「해당 mesh 들과 그 비행 로그 데이터를 토대로 저것들도 STFT
그려보는 작업」. 입력은 po_mdoppler 가 만든 window_XXXXX.npz 이고, 이 스크립트는
**읽어서 그리기만** 한다(⛔ jihyuck/ 안은 안 고친다 — 정본 보호).

우리 판과 뭐가 다른가
  · 반송파 9.85 GHz(X-대역) · PRF 35 kHz — 우리 3.5 GHz·19.7 kHz 판과 눈금이 다르다.
  · ⭐«기동» 이 들어 있다 — PX4 로그의 위치·자세·로터별 RPM 이 시간에 따라 변한다.
    우리 앙각 스윕(자세 고정·회전만)에는 없는 축이다.
  · 벌크 도플러(기체 이동)가 사후 보정 없이 그대로 실려 있다 — 맵에서 0 Hz 가 아니라
    움직이는 능선으로 보이는 것이 정상이다.

    PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/build_jihyuck_stft.py --grade 2 \
        --in outputs/jihyuck_po --out outputs/figures
"""
from __future__ import annotations

import argparse
import glob
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                       # noqa: E402
import numpy as np                                                    # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
from md_mapstyle import auto_periods, flash_spec, draw                 # noqa: E402

#: 재질 3 종 × 가림 full(= body_occ + blade_occ_X). 선배 패키지의 ablation 규약 그대로.
COMBOS = [("nylon", "nylon blades"), ("cf", "carbon fiber blades"),
          ("metal", "metal blades")]

plt.rcParams.update({
    "font.size": 19, "axes.titlesize": 22, "axes.labelsize": 19,
    "xtick.labelsize": 17, "ytick.labelsize": 17,
    "figure.facecolor": "white", "savefig.facecolor": "white",
})


def load_grade(d):
    ws = sorted(glob.glob(os.path.join(d, "window_*.npz")))
    if not ws:
        raise SystemExit(f"⛔ 윈도우가 없다: {d}")
    meta = np.load(os.path.join(d, "metadata.npz"), allow_pickle=True)
    sig = {f"{occ}_{m}": [] for occ in ("none", "occ") for m, _ in COMBOS}
    for w in ws:
        z = np.load(w)
        for m, _ in COMBOS:
            sig[f"none_{m}"].append(z["body_none"] + z[f"blade_none_{m}"])
            sig[f"occ_{m}"].append(z["body_occ"] + z[f"blade_occ_{m}"])
    return ({k: np.concatenate(v) for k, v in sig.items()},
            float(meta["prf"]), float(meta["rpm_scale"]), len(ws))


def rates_from_esc(grade, rpm_scale, n_blades=2):
    """ESC 로그의 평균 RPM × 스케일 → (플래시 박자, 날개끝 주파수) 어림.

    ⚠플래시 박자는 **로터 하나** 기준이다(우리 집 규약과 같다) — 로터 수를 곱하면
      STFT 조각이 4 배 짧아져 맵이 통째로 뭉개진다(스모크에서 실측).
    """
    import pandas as pd
    p = f"{ROOT}/jihyuck/po_mdoppler/data/sim_data/grade_{grade}/clean_esc.csv"
    df = pd.read_csv(p)
    #: ⭐선배 규약 그대로 — po_sim/kinematics.py:24 의 ESC_COLS 네 열만 쓴다.
    #  «esc» 가 든 열을 다 긁으면 timestamp·padding 이 섞여 rpm 이 5×10⁷ 이 된다(실측).
    cols = [f"esc[{i}].esc_rpm" for i in range(4)]
    rpm = float(np.nanmean(df[cols].values))
    frev = rpm * rpm_scale / 60.0
    ffl = frev * n_blades                      # 한 로터의 날개 통과율
    R = 0.178 / 2.0                            # 블레이드 반경(메쉬 실측 178 mm 지름)
    lam = 2.998e8 / 9.85e9
    ftip = 2.0 * (2 * np.pi * frev * R) / lam  # 왕복 도플러 상한
    return ffl, ftip


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grade", type=int, required=True)
    ap.add_argument("--in", dest="ind", default=f"{ROOT}/outputs/jihyuck_po")
    ap.add_argument("--out", default=f"{ROOT}/outputs/figures")
    ap.add_argument("--span-s", type=float, default=1.0,
                    help="그릴 구간 길이 [s] — 기동이 보일 만큼")
    a = ap.parse_args()

    d = os.path.join(a.ind, f"grade_{a.grade}")
    sig, prf, rpm_scale, nw = load_grade(d)
    ffl, ftip = rates_from_esc(a.grade, rpm_scale)
    per = auto_periods(prf, ffl)
    nz = int(round(a.span_s * prf))

    fig, ax = plt.subplots(2, 3, figsize=(26.0, 10.0), sharex=True, sharey=True)
    for r, occ in enumerate(("none", "occ")):
        for c, (m, nm) in enumerate(COMBOS):
            E = sig[f"{occ}_{m}"][:nz]
            f, t, S, _ = flash_spec(E, prf, ffl, per)
            #: ⚠hop 2 로 1 초를 썰면 열이 1.7 만 개다 — pcolormesh 가 멈춘다(실측).
            #  표시용으로만 열을 솎는다. 계산 규약(조각 길이·hop)은 그대로다.
            step = max(1, S.shape[1] // 2500)
            t, S = t[::step], S[:, ::step]
            axi = ax[r, c]
            draw(axi, t, f, S, ftip)               # 점선 = ESC 평균 회전수의 날개끝 상한
            axi.set_ylim(-1.6 * ftip, 1.6 * ftip)
            if r == 0:
                axi.set_title(nm, pad=8)
            if c == 0:
                axi.set_ylabel(("no occlusion" if occ == "none" else "full occlusion")
                               + "\nDoppler [Hz]")
            if r == 1:
                axi.set_xlabel("time [ms]")
    fig.text(0.5, 0.955,
             f"PX4 flight log grade {a.grade}, X band 9.85 GHz, PRF {prf:,.0f} Hz, "
             f"{nw} windows, prior work pipeline",
             ha="center", fontsize=19, color="0.35")
    fig.subplots_adjust(top=0.90, bottom=0.09, left=0.06, right=0.95,
                        hspace=0.16, wspace=0.08)
    cax = fig.add_axes([0.958, 0.09, 0.008, 0.81])
    cb = fig.colorbar(ax[0, 0].collections[0], cax=cax)
    cb.set_label("dB below the brightest point in that panel", fontsize=17)
    out = os.path.join(a.out, f"jihyuck_stft_grade{a.grade}.png")
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  ✅ {out}")


if __name__ == "__main__":
    main()
