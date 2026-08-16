# -*- coding: utf-8 -*-
"""③ 마무리 — 4로터 현실 조건에서 «어느 손잡이가 빗살을 움직이나» 사다리."""
import sys

import numpy as np

sys.path.insert(0, "/workspace/sionna/src")
sys.path.insert(0, "/tmp/claude-0/-workspace/e9e31991-b542-4f3a-b8e2-570320d555ba/scratchpad/rotor_adv")
import rotor_dynamics as rd            # noqa: E402
from comb import (F_FLASH, PRF, RPM0, comb_metrics, echo, half_corr,     # noqa: E402
                  spectrum, spline_up)

FS = 200.0
N = 40
CASES = [
    ("legacy   σ_s 0.22 σ_w 0.00", 0.0022, 0.0000, 0.227),
    ("indoor   σ_s 0.54 σ_w 0.65", 0.0054, 0.0065, 0.227),
    ("outdoor  σ_s 2.35 σ_w 2.45", 0.0235, 0.0245, 0.227),
    ("실측중앙  σ_s 5.60 σ_w 1.40", 0.0560, 0.0140, 0.227),
    ("실측중앙+τ교정          ", 0.0560, 0.0140, 1.040),
    ("σ_s만 실측(σ_w outdoor) ", 0.0560, 0.0245, 0.227),
    ("σ_w만 실측(σ_s outdoor) ", 0.0235, 0.0140, 0.227),
]
for win in (0.25, 1.0):
    n = int(win * FS) + 4
    n_t = int(PRF * win)
    print("=" * 96)
    print(f"### 창 {win} s · 4로터 · f_flash 126.7 Hz · 씨앗 {N}")
    print(f"{'설정':30s}{'퍼짐m3':>9s}{'퍼짐m6':>9s}{'퍼짐m9':>9s}"
          f"{'꼭대기m6':>10s}{'꼭대기m9':>10s}{'참여비m9':>10s}{'반창상관':>9s}")
    for lbl, ss, sw, tau in CASES:
        acc = []
        for s in range(N):
            rng = np.random.default_rng(700000 + s)
            if sw > 0:
                e = rd.ou_process(n, 1 / FS, 1.0, tau, rng, n_ch=4)
                e = e / e.std() * sw
            else:
                e = np.zeros((n, 4))
            sk = rng.normal(0, ss, 4)
            sk -= sk.mean()
            ph0 = rng.uniform(0, 180.0, 4)
            rpm = RPM0 * (1.0 + sk[None, :] + spline_up(e.T, FS, n_t, PRF))
            ec = echo(rpm, PRF, ph0)
            f, P = spectrum(ec, PRF)
            cm = comb_metrics(f, P, F_FLASH)
            cm["hc"] = half_corr(ec, PRF, F_FLASH)
            acc.append(cm)

        def g(k, m):
            return float(np.median([a[k][m] for a in acc if m in a[k]]))
        print(f"{lbl:30s}{g('spread_hz',3):9.2f}{g('spread_hz',6):9.2f}{g('spread_hz',9):9.2f}"
              f"{g('peak_over_median_db',6):10.1f}{g('peak_over_median_db',9):10.1f}"
              f"{g('occupancy',9):10.3f}{np.median([a['hc'] for a in acc]):9.3f}", flush=True)
