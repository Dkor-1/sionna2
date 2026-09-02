# -*- coding: utf-8 -*-
"""noise_all_arms_0901.py — 잡음을 **다섯 팔 모두**에 넣는다 (덱 12 장 확장).

⭐사용자 지시(2026-09-01): 「노이즈 모델링을 우리 커널에만 할 것이 아니라
   시오나 패스 솔버 경로에도 적용해서 슬라이드에 실어주면 좋겠는데」

■ 잡음 규약 — 12 장과 **똑같은 절차**를 팔마다 되풀이한다
    x0   = E[창] − mean(E[창])            DC(몸통 상수) 제거
    pac  = ⟨|x0|²⟩                        그 팔의 AC 전력
    n    ~ CN(0, pac/10^(SNR/10))         복소 백색가우스, 실·허 각각 절반
    x    = x0 + n
  ⇒ SNR 은 **그 팔 자신의 AC** 를 기준으로 한다.

⛔**왜 팔마다 자기 AC 로 재는가.** 우리 커널의 E 는 1/r 확산을 넣지 않아 절대 크기가
   «그 거리의 수신 전력» 이 아니다(rcs_sbr.py · rx_noise.py 서두). PathSolver 의 장과
   **같은 자로 잴 수 없다.** 그래서 공통 절대 잡음을 한 번에 얹으면 그림이 거짓말을 한다.
   팔마다 자기 AC 를 기준으로 하면 「이 팔의 무늬가 잡음에 얼마나 견디나」 만 비교하게 되고,
   그건 엔진 눈금과 무관하다.
⛔이 그림은 «어느 엔진이 실제로 더 세다» 를 말하지 않는다. 그건 절대 눈금(σ 앵커)과
   수신 예산이 있어야 하고, 우리는 실측 대조가 0 건이다.

    CUDA_VISIBLE_DEVICES="" PYTHONPATH=src:benchmark \
      /workspace/.venvs/py312/bin/python benchmark/noise_all_arms_0901.py
"""
import importlib
import os
import sys

import numpy as np

ROOT = "/workspace/sionna"
sys.path.insert(0, f"{ROOT}/benchmark")
sys.path.insert(0, f"{ROOT}/src")
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

import matplotlib.pyplot as plt                                        # noqa: E402

FIG = f"{ROOT}/outputs/figures"
MESH = "mfixbatteryi5_blperairframe"
EL = -30.0
SEED = 20260901
DEG = chr(176)
MINUS = chr(8722)

#: ⛔행 이름은 짧게 — "refraction+diffraction" 은 옆 행 이름과 겹쳤다
ARMS = [("all off", "R0D0E0F1"), ("refraction", "R1D0E0F1"),
        ("diffraction", "R0D1E1F1"), ("both", "R1D1E1F1"),
        ("ours", None)]
LV = [None, 20.0, 10.0, 3.0, 0.0]


def arm_key(bits):
    if bits is None:
        return f"ours_r15_n8192_{MESH}"
    return f"sionna_p4000000000_sw{bits}_r15_n8192_{MESH}_d2"


def main():
    Z = np.load(f"{ROOT}/outputs/elevation_sweep_md.npz")
    os.environ["SWGRID_EL"] = f"{EL:g}"
    import build_switch_grid_figs as G
    importlib.reload(G)
    n0 = int(round(G.T0 * G.PRF))
    nz = int(round(G.TSPAN * G.PRF))

    fig, ax = plt.subplots(len(ARMS), len(LV),
                           figsize=(3.55 * len(LV), 2.35 * len(ARMS)),
                           sharex=True, sharey=True)
    for i, (lab, bits) in enumerate(ARMS):
        E = np.asarray(Z[f"{arm_key(bits)}/el{EL:+.0f}"])
        x0 = E[n0:n0 + nz]
        x0 = x0 - x0.mean()
        pac = float((np.abs(x0) ** 2).mean())
        rng = np.random.default_rng(SEED + i)      # 팔마다 다른 흐름, 재현 가능
        for j, sv in enumerate(LV):
            x = x0 if sv is None else x0 + np.sqrt(pac / 10 ** (sv / 10) / 2) * (
                rng.normal(size=x0.size) + 1j * rng.normal(size=x0.size))
            f_, t_, S_, _ = G.flash_spec(x, G.PRF, G.FFL, G.PERIODS)
            a = ax[i, j]
            G.draw(a, t_, f_, S_, G.FT30)
            a.set_ylim(-2000, 2000)
            if i == 0:
                a.set_title("no noise" if sv is None else f"SNR {sv:.0f} dB",
                            fontsize=17, color="#141926", weight="bold", pad=8)
            if j == 0:
                a.set_ylabel(lab, fontsize=15, color="#141926", weight="bold", labelpad=8)
            if i == len(ARMS) - 1:
                a.set_xlabel("time [ms]", fontsize=12)
        print(f"  {lab:<24} AC {10*np.log10(pac):7.1f} dB")

    fig.subplots_adjust(top=0.858, bottom=0.085, left=0.070, right=0.992,
                        hspace=0.16, wspace=0.05)
    fig.text(0.5, 0.960, "the same noise, on every arm",
             ha="center", fontsize=24, color="#141926", weight="bold")
    fig.text(0.5, 0.921, f"matrice4e {chr(183)} 15 m {chr(183)} el {MINUS}30{DEG} "
             f"{chr(183)} complex white gaussian added to the stored series",
             ha="center", fontsize=15, color="#C81E3C", weight="bold")
    fig.text(0.5, 0.888, "SNR is measured against each arm's own moving part   "
             f"{chr(183)}   each panel scaled to its own peak",
             ha="center", fontsize=13, color="#5E5E5E")
    # ⛔각주 삭제(2026-09-02) — 「엔진끼리 세기를 견주는 게 아니다」는 노트에 있다.
    p = f"{FIG}/vol_noise_all_arms.png"
    fig.savefig(p, dpi=125)
    plt.close(fig)
    print(f"  ✅ {p}")


if __name__ == "__main__":
    print("═══ 잡음 · 다섯 팔 전부 ═══")
    main()
