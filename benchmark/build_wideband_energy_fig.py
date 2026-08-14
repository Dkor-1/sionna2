# -*- coding: utf-8 -*-
"""build_wideband_energy_fig.py — ⭐대역 에너지를 **넓은 관찰범위**로 다시 그린다.

■ 사용자 지시 (2026-08-11)
    *"에너지를 볼 때 기존에 430~1300 언저리를 그렸는데, 그 flatten 한 뒤
      관찰범위를 더 넓게 그려보자는 거야."*

■ 왜 넓게 보면 값어치가 있나
    블레이드 끝 속도가 정하는 **물리 상한**은 f_tip = 1272.9·cos(el) Hz 다.
    그 **위에 있는 에너지는 블레이드 도플러일 수 없다** — 인공물이다.
    지금까지 430~1229 Hz 만 봐서 그 인공물을 **아예 못 보고 있었다.**
    관찰 상한은 나이퀴스트 PRF/2 = 9,850 Hz 다.

    ⭐이 그림이 새로 주는 것: **«물리 상한 위로 새는 에너지 비율»** 이라는 잣대.
      엔진을 가르는 데 대역 안 에너지보다 강력하다(아래 §숫자 참조).

■ 무엇을 그리나 (3 단)
    (a) 앙각별 **전대역 스펙트럼** — x 축을 f_tip 으로 정규화해 겹친다.
        x = 1 이 물리 상한. 그 오른쪽은 전부 인공물이다.
    (b) **대역별 에너지 몫** — 0~500 / 500~f_tip / f_tip~2·f_tip / 2~4·f_tip / 4·f_tip~나이퀴스트
    (c) ⭐**물리 상한 위로 새는 비율 대 앙각** — 팔마다. 낮을수록 좋다.

⛔팔 사이 **레벨**을 나란히 놓지 않는다 — 정규화가 달라 우리 −54 대 PathSolver −125 dB 다.
   전부 **자기 전체 전력 대비 몫**으로만 그린다(눈금 무관).
⛔STFT 만 쓴다(재할당·WVD 금지). 여기는 슬로타임 FFT 라 해당 없음.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import matplotlib                                                    # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                      # noqa: E402

NPZ = f"{ROOT}/outputs/elevation_sweep_md.npz"
JSN = f"{ROOT}/outputs/elevation_sweep_md.json"
#: ⭐2026-08-14 — 같은 코드로 여러 거리 판을 굽는다(옛 10 m 는 기본값 그대로).
#      WB_ARMS = "키|표시이름|색 ; ..."   (구분자는 세미콜론 — 이름에 쉼표가 들어간다)
#      WB_TAG  = "_r15"                   출력 파일 뒤에 붙는 꼬리
TAG = os.environ.get("WB_TAG", "")
OUTP = f"{ROOT}/outputs/figures/wideband_energy{TAG}.png"
OUTJ = f"{ROOT}/outputs/wideband_energy{TAG}.json"

ELS = [0.0, -15.0, -30.0, -45.0, -60.0, -75.0, -90.0]
if os.environ.get("WB_ARMS"):
    ARMS = [tuple(x.strip() for x in spec.split("|"))
            for spec in os.environ["WB_ARMS"].split(";")]
else:
    ARMS = [("ours", "Ours (SBR+PO)", "tab:blue"),
            ("sionna", "PathSolver 11.1M", "tab:orange"),
            ("sionna_p250000000", "PathSolver 250M", "tab:green"),
            ("sionna_phys", "PathSolver + physics", "tab:red")]
FTIP0 = 1272.9


def spectrum(E: np.ndarray, prf: float):
    """0 Hz(정지 동체)를 뺀 양쪽 스펙트럼. 마이크로도플러는 부호가 있으므로 fft 를 쓴다."""
    E = np.asarray(E, complex)
    n = E.size
    x = E - E.mean()
    S = np.abs(np.fft.fft(x * np.hanning(n))) ** 2
    fr = np.fft.fftfreq(n, 1 / prf)
    o = np.argsort(fr)
    return fr[o], S[o], float(S.sum())


def main() -> None:
    d = np.load(NPZ, allow_pickle=True)
    meta = json.load(open(JSN))["_meta"]
    rows = {(r["engine"], r["el_deg"]): r for r in json.load(open(JSN))["rows"]}
    prf = float(meta["prf_hz"])
    nyq = prf / 2

    out = {"_meta": {
        "generator": "benchmark/build_wideband_energy_fig.py",
        "question_ko": "관찰범위를 물리 상한 위까지 넓히면 무엇이 보이나",
        "prf_hz": prf, "nyquist_hz": nyq, "f_tip_el0_hz": FTIP0,
        "physical_limit_ko": ("f_tip = 1272.9·cos(el) 가 날개끝 속도가 정하는 상한이다. "
                              "그 위의 에너지는 블레이드 도플러일 수 없다 — 인공물이다."),
        "normalisation_ko": "전부 그 팔의 전체 전력 대비 몫. 팔 사이 레벨은 비교하지 않는다.",
        "incomplete_excluded_ko": "n_missing > 0 인 행은 제외했다(부분 병합은 시계열에 0 이 박힌다).",
    }, "cells": {}}

    fig, ax = plt.subplots(3, 1, figsize=(11, 13))

    # ── (a) f_tip 으로 정규화한 전대역 스펙트럼 (el 0 · −45 만, 겹치면 안 보인다)
    for eli, elv in [(0, 0.0), (1, -45.0)]:
        pass
    for arm, label, col in ARMS:
        key = f"{arm}/el+0"
        r = rows.get((arm, 0.0))
        if key not in d or (r and r["n_missing"]):
            continue
        fr, S, tot = spectrum(d[key], prf)
        m = fr > 0
        ax[0].semilogx(fr[m] / FTIP0, 10 * np.log10(S[m] / S[m].max() + 1e-16),
                       lw=0.8, alpha=0.85, color=col, label=label)
    ax[0].axvline(1.0, color="k", ls="--", lw=1.4)
    ax[0].text(1.03, -3, "physical limit  f_tip", fontsize=9, rotation=90, va="top")
    ax[0].axvspan(1.0, nyq / FTIP0, color="red", alpha=0.05)
    ax[0].text(2.2, -8, "above physical limit = artefact", fontsize=9, color="darkred")
    ax[0].set_xlim(0.02, nyq / FTIP0)
    ax[0].set_ylim(-70, 2)
    ax[0].set_xlabel("Doppler / f_tip   (1.0 = blade tip speed limit)")
    ax[0].set_ylabel("power [dB, own max]")
    ax[0].set_title("(a) Full-band Doppler spectrum at el 0 deg, normalised to each arm's own maximum")
    ax[0].grid(alpha=0.3, which="both")
    ax[0].legend(fontsize=8)

    # ── (b)(c) 대역별 몫 · 상한 위 누설
    def bands_for(ft: float):
        ft = max(ft, 1e-9)
        return [(0, 500, "0-500 Hz"), (500, ft, "500-f_tip"),
                (ft, 2 * ft, "f_tip-2f_tip"), (2 * ft, 4 * ft, "2-4 f_tip"),
                (4 * ft, nyq, "4f_tip-Nyquist")]

    leak = {a: [] for a, _, _ in ARMS}
    leak_el = {a: [] for a, _, _ in ARMS}
    for arm, label, col in ARMS:
        for elv in ELS:
            key = f"{arm}/el{elv:+.0f}"
            r = rows.get((arm, elv))
            if key not in d or (r and r["n_missing"]):
                continue
            ft = FTIP0 * np.cos(np.radians(elv))
            fr, S, tot = spectrum(d[key], prf)
            cell = {}
            for lo, hi, nm in bands_for(ft):
                if hi <= lo:
                    cell[nm] = None
                    continue
                w = (np.abs(fr) >= lo) & (np.abs(fr) < hi)
                cell[nm] = round(float(10 * np.log10(S[w].sum() / tot + 1e-300)), 2)
            # ⭐물리 상한 위로 새는 비율
            if ft > 1:
                above = float(S[np.abs(fr) >= ft].sum() / tot)
                cell["above_f_tip_frac"] = round(above, 5)
                cell["above_f_tip_db"] = round(float(10 * np.log10(above + 1e-300)), 2)
                leak[arm].append(100 * above)
                leak_el[arm].append(elv)
            cell["f_tip_hz"] = round(ft, 1)
            out["cells"][key] = cell

    w, xs = 0.2, np.arange(len(ELS))
    for i, (arm, label, col) in enumerate(ARMS):
        v = [out["cells"].get(f"{arm}/el{e:+.0f}", {}).get("500-f_tip") for e in ELS]
        ax[1].bar(xs + (i - 1.5) * w, [np.nan if x is None else x for x in v],
                  w, color=col, label=label)
    ax[1].set_xticks(xs); ax[1].set_xticklabels([f"{e:+.0f}" for e in ELS])
    ax[1].set_xlabel("elevation [deg]"); ax[1].set_ylabel("share of total power [dB]")
    ax[1].set_title("(b) Energy inside the physical blade band (500 Hz to f_tip)")
    ax[1].grid(alpha=0.3, axis="y"); ax[1].legend(fontsize=8)

    for arm, label, col in ARMS:
        if leak[arm]:
            ax[2].plot(leak_el[arm], leak[arm], "o-", color=col, label=label)
    ax[2].set_xlabel("elevation [deg]")
    ax[2].set_ylabel("energy above f_tip [% of total]")
    ax[2].set_title("(c) Leakage above the physical limit — lower is better "
                    "(no blade Doppler can exist there)")
    ax[2].grid(alpha=0.3); ax[2].legend(fontsize=8)
    ax[2].set_ylim(0, None)

    fig.tight_layout()
    os.makedirs(f"{ROOT}/outputs/figures", exist_ok=True)
    fig.savefig(OUTP, dpi=150)
    json.dump(out, open(OUTJ, "w"), ensure_ascii=False, indent=1)

    print(f"  {'팔':<26}{'el':>5}{'f_tip':>8}{'대역내[dB]':>11}{'⭐상한위[%]':>12}")
    for k, v in out["cells"].items():
        if "above_f_tip_frac" in v:
            print(f"  {k:<26}{k.split('el')[-1]:>5}{v['f_tip_hz']:8.0f}"
                  f"{(v.get('500-f_tip') or float('nan')):11.2f}"
                  f"{100*v['above_f_tip_frac']:12.2f}")
    print(f"\n  → {OUTP}\n  → {OUTJ}")


if __name__ == "__main__":
    main()
