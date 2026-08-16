# -*- coding: utf-8 -*-
"""② «모델이 못 담는 것» 을 하나씩 넣어 보고 ③ 빗살이 얼마나 움직이나 — 성분 분해 실험.

총 흔들림 크기 σ_w 를 **고정**해 놓고 «모양·구조» 만 바꾼다. 그래야 «크기 탓» 과
«모양 탓» 이 안 섞인다.

성분(전부 이번 라운드 실측에서 나온 것)
  base      : 우리 모델 그대로 — OU τ=0.227 s(코너 0.7 Hz), 로터 독립
  slow_tau  : OU τ=1.04 s — 실측 자기상관 지수적합(px4_s500 중앙값)
  hf_mix    : OU 80 % + 넓은 잡음 20 % — 실측이 2–5 Hz 에 갖고 우리는 없는 몫
  drift_mix : OU 80 % + 아주 느린 배회 20 % — 실측이 0.0625–0.125 Hz 에 갖는 몫(3.0배)
  full_mix  : slow_tau + hf_mix + drift_mix 를 실측 옥타브 몫에 맞춰 합침
  common50  : 로터 간 공통 성분 50 %
  common93  : 로터 간 공통 성분 93 % — 실측 기동(레이싱) 값
  anti      : 로터 간 −0.13 상관 — 실측 호버(px4_s500) 값
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, "/workspace/sionna/src")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rotor_dynamics as rd            # noqa: E402
from comb import (DIRS, F_FLASH, N_ROTOR, PRF, RPM0, comb_metrics, echo,   # noqa: E402
                  half_corr, spectrum, spline_up)

HERE = os.path.dirname(os.path.abspath(__file__))
DUR = 1.0
FS_GEN = 200.0
SIGMA_W = 0.0140          # px4_s500 호버 중앙 총 흔들림
SIGMA_S = 0.0235          # 같은 로그의 정적 산포
N_SEED = 200


def ou(n, dt, sigma, tau, rng, n_ch):
    return rd.ou_process(n, dt, sigma, tau, rng, n_ch=n_ch)


def band_noise(n, dt, sigma, rng, n_ch, f_hi=50.0):
    """0–f_hi 에 평평한 잡음(넓은 성분). σ 는 총 std."""
    x = rng.standard_normal((n, n_ch))
    # 간단한 이동평균 저역통과로 f_hi 위를 깎고 분산 회복
    w = max(1, int(round(1.0 / (2 * f_hi * dt))))
    if w > 1:
        k = np.ones(w) / w
        x = np.apply_along_axis(lambda v: np.convolve(v, k, mode="same"), 0, x)
        x /= x.std()
    return sigma * x


def make(kind, n, dt, rng):
    """(n, 4) 상대 흔들림 ε. 총 std 는 어떤 종류든 SIGMA_W 로 맞춘다."""
    T = rd.TAU_CTL_S
    if kind == "base":
        e = ou(n, dt, 1.0, T, rng, N_ROTOR)
    elif kind == "slow_tau":
        e = ou(n, dt, 1.0, 1.04, rng, N_ROTOR)
    elif kind == "hf_mix":
        e = np.sqrt(0.8) * ou(n, dt, 1.0, T, rng, N_ROTOR) + \
            np.sqrt(0.2) * band_noise(n, dt, 1.0, rng, N_ROTOR)
    elif kind == "drift_mix":
        e = np.sqrt(0.8) * ou(n, dt, 1.0, T, rng, N_ROTOR) + \
            np.sqrt(0.2) * ou(n, dt, 1.0, 8.0, rng, N_ROTOR)
    elif kind == "full_mix":
        e = (np.sqrt(0.5) * ou(n, dt, 1.0, 1.04, rng, N_ROTOR) +
             np.sqrt(0.25) * ou(n, dt, 1.0, 8.0, rng, N_ROTOR) +
             np.sqrt(0.25) * band_noise(n, dt, 1.0, rng, N_ROTOR))
    elif kind.startswith("common"):
        rho = float(kind[6:]) / 100.0
        c = ou(n, dt, 1.0, T, rng, 1)
        i = ou(n, dt, 1.0, T, rng, N_ROTOR)
        e = np.sqrt(rho) * c + np.sqrt(1 - rho) * i
    elif kind == "anti":
        # 로터 간 −1/3 상관은 «합이 0» 구속의 극한. 실측 −0.13 은 그 중간 →
        # 합제약을 부분적으로 건다: e = i − a·mean(i), a 를 상관에 맞춰 푼다.
        i = ou(n, dt, 1.0, T, rng, N_ROTOR)
        a = 0.42                      # ρ ≈ −0.13 이 되는 값(아래에서 실측 확인)
        e = i - a * i.mean(axis=1, keepdims=True)
    else:
        raise ValueError(kind)
    e = e / e.std() * SIGMA_W
    return e


def run():
    n = int(DUR * FS_GEN) + 4
    n_t = int(PRF * DUR)
    dt = 1.0 / FS_GEN
    kinds = ["base", "slow_tau", "hf_mix", "drift_mix", "full_mix",
             "common50", "common93", "anti"]
    rows = []
    for kind in kinds:
        for s in range(N_SEED):
            rng = np.random.default_rng(9000 + s)
            e = make(kind, n, dt, rng)
            rng2 = np.random.default_rng(50000 + s)
            s_k = rng2.normal(0, SIGMA_S, N_ROTOR)
            s_k -= s_k.mean()
            ph0 = rng2.uniform(0, 180.0, N_ROTOR)
            ec = e - e.mean(axis=0, keepdims=True)
            cc = np.corrcoef(ec.T)
            iu = np.triu_indices(N_ROTOR, 1)
            rho_hat = float(np.mean(cc[iu]))
            for mode in ("single", "quad"):
                if mode == "single":
                    rpm_t = RPM0 * (1.0 + spline_up(e[:, :1].T, FS_GEN, n_t, PRF))
                else:
                    rpm_t = RPM0 * (1.0 + s_k[None, :] +
                                    spline_up(e.T, FS_GEN, n_t, PRF))
                ech = echo(rpm_t, PRF, ph0)
                f, P = spectrum(ech, PRF)
                cm = comb_metrics(f, P, F_FLASH)
                cm["half_corr"] = half_corr(ech, PRF, F_FLASH)
                cm.update(_kind=kind, _mode=mode, _seed=s, _rho=rho_hat)
                rows.append(cm)
        print("done", kind, flush=True)
    json.dump(dict(rows=rows, cfg=dict(sigma_w=SIGMA_W, sigma_s=SIGMA_S, dur=DUR,
                                       fs_gen=FS_GEN, prf=PRF, n_seed=N_SEED,
                                       f_flash=F_FLASH)),
              open(f"{HERE}/ingredient_rows.json", "w"))
    print("rows", len(rows))


if __name__ == "__main__":
    run()
