# -*- coding: utf-8 -*-
"""③ «모델이 못 담는 것» 이 마이크로도플러 빗살에 얼마나 영향 주나 — 직접 계산 (CPU)

무엇을 하나
-----------
로터 회전수 열 rpm_k(t) 를 여러 방식으로 만들고, **같은** 블레이드 산란 모형에
집어넣어 도플러 스펙트럼(빗살)을 그린 뒤 빗살 품질 지표를 잰다.

팔
  A_measured  : 실측 로그의 ε_k(t)·s_k (그 로그의 표집률 fs → 3차 스플라인으로 PRF)
  B_sameband  : 우리 OU 를 **같은 fs 로 생성**하고 같은 스플라인으로 올린 것.
                σ_s·σ_w 레벨도 그 발췌에 맞춘다 ⇒ 남는 차이는 **순수 «모양» 차이**.
  C_outdoor   : PRESETS['outdoor'] 를 생산 경로대로(200 Hz 생성) — 지금 우리가 쓰는 것
  D_locked    : 흔들림 0 · 산포 0 (이상 하한, 기준선)

⭐공정성: A 와 B 는 **같은 대역·같은 보간**을 지난다. 10 Hz 로그는 5 Hz 위를 못 담으므로
그 한계는 두 팔에 똑같이 걸린다. C 만 200 Hz(=100 Hz 대역)라 «생산 설정»의 몫을 따로 본다.

산란 모형: 로터 k, 날개 b, 반경 r 산란자의 시선 사거리 변화 = r·cos θ·cos(el)
⇒ 위상 −(4π/λ)·r·cos θ·cos(el). 동체·차폐·재질은 일부러 뺀다(빗살 축에 곱셈 상수).
"""
import json
import os
import sys

import numpy as np
from scipy.interpolate import CubicSpline

sys.path.insert(0, "/workspace/sionna/src")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rotor_dynamics as rd            # noqa: E402
import rstats                           # noqa: E402
from compare import matched_jitter      # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

PRF = 20000.0
DUR = 1.0
RPM0 = 3800.0          # matrice4e hover_rpm (src/drones.py)
N_BLADE, N_ROTOR = 2, 4
R_PROP = 0.274 / 2
FC = 3.5e9
LAM = 299792458.0 / FC
EL_DEG = -15.0
NR = 24
F_FLASH = N_BLADE * RPM0 / 60.0        # 126.667 Hz
DIRS = np.array([1.0, -1.0, 1.0, -1.0])


def echo(rpm_t, prf, phase0_deg):
    n_t, n_rot = rpm_t.shape
    dirs = DIRS[:n_rot]
    ang = np.cumsum(360.0 * rpm_t / 60.0 / prf, axis=0)
    th = np.deg2rad(phase0_deg[:n_rot][None, :] + dirs[None, :] * ang)
    r = np.linspace(0.18 * R_PROP, R_PROP, NR)
    k = 4 * np.pi / LAM * np.cos(np.deg2rad(EL_DEG))
    s = np.zeros(n_t, complex)
    for b in range(N_BLADE):
        c = np.cos(th + b * (2 * np.pi / N_BLADE))
        s += np.exp(-1j * k * c[:, :, None] * r[None, None, :]).mean(axis=2).sum(axis=1)
    return s


def spectrum(s, prf):
    n = len(s)
    S = np.fft.fftshift(np.fft.fft(s * np.hanning(n)))
    f = np.fft.fftshift(np.fft.fftfreq(n, 1 / prf))
    P = np.abs(S) ** 2
    return f, P / P.max()


def comb_metrics(f, P, f_flash, m_max=12):
    """차수 m 의 «구역»(m·f_flash ± 0.5 f_flash) 안에서 빗살이 얼마나 뭉개졌나.

    ⚠최대점의 반치폭(FWHM)은 **쓰지 않는다** — 로터 4개가 산포 때문에 각자 선을
      내므로 구역 안에 뾰족한 봉우리가 여러 개 서고, 그 중 하나만 재면 «안 넓어졌다»
      는 거짓 결론이 나온다(1차 시도에서 실제로 그렇게 나왔다).
      대신 구역 전체의 **에너지 퍼짐(2차 모멘트)**·**꼭대기/중앙값 비**·
      **참여비(몇 개 빈이 실질적으로 에너지를 갖나)** 로 잰다."""
    db = 10 * np.log10(P + 1e-30)
    out = {"spread_hz": {}, "peak_over_median_db": {}, "occupancy": {}, "peak_db": {}}
    for m in range(1, m_max + 1):
        f0 = m * f_flash
        sel = (f > f0 - 0.5 * f_flash) & (f < f0 + 0.5 * f_flash)
        if sel.sum() < 16:
            continue
        p, fz = P[sel], f[sel]
        w = p / p.sum()
        fbar = float((w * fz).sum())
        out["spread_hz"][m] = float(np.sqrt((w * (fz - fbar) ** 2).sum()))
        out["peak_over_median_db"][m] = float(10 * np.log10(p.max() / np.median(p)))
        out["occupancy"][m] = float(1.0 / (w ** 2).sum() / w.size)      # 참여비
        out["peak_db"][m] = float(db[sel].max())
    band = (np.abs(f) > 0.5 * f_flash) & (np.abs(f) < (m_max + 0.5) * f_flash)
    p = P[band] / P[band].sum()
    out["spec_entropy"] = float(-np.sum(p * np.log(p + 1e-30)) / np.log(p.size))
    return out


def half_corr(s, prf, f_flash, m_max=12):
    n = len(s) // 2
    f1, P1 = spectrum(s[:n], prf)
    _, P2 = spectrum(s[n:2 * n], prf)
    b = (np.abs(f1) > 0.5 * f_flash) & (np.abs(f1) < (m_max + 0.5) * f_flash)
    return float(np.corrcoef(10 * np.log10(P1[b] + 1e-30), 10 * np.log10(P2[b] + 1e-30))[0, 1])


def spline_up(eps_lo, fs_lo, n_hi, prf):
    """(4, n_lo) → (n_hi, 4). 실측·모델 팔이 **같은** 보간을 지나게 하는 함수."""
    t_lo = np.arange(eps_lo.shape[1]) / fs_lo
    t_hi = np.clip(np.arange(n_hi) / prf, t_lo[0], t_lo[-1])
    return CubicSpline(t_lo, eps_lo, axis=1)(t_hi).T


def model_lowrate(jit, n_lo, fs_lo, rng):
    """모델을 fs_lo 격자에서 정확 이산화로 생성 → (s_k, eps (4,n_lo))."""
    s_k = rd.static_offsets(N_ROTOR, jit, rng)
    eps = rd._wobble(n_lo, fs_lo, N_ROTOR, jit, rng, coarse_hz=None).T
    return s_k, eps


def run():
    z = np.load(f"{HERE}/rotor_corpus.npz")
    keys = sorted({k.split("__")[0] for k in z.files})
    n_t = int(PRF * DUR)
    rows = []
    for k in keys:
        rpm = z[f"{k}__rpm"]
        fs = float(z[f"{k}__fs"][0])
        n_lo = int(DUR * fs) + 4
        if rpm.shape[1] < n_lo + 4:
            continue
        st = rstats.full(rpm, fs)
        fam = ("px4_s500" if k.startswith("px4_s500") else
               "px4_race_manv" if "race_manv" in k else
               "dregon_meas" if "_meas_" in k else "dregon_cmd")
        starts = list(range(0, rpm.shape[1] - n_lo, max(1, int(2 * fs))))[:6]
        for si, s0 in enumerate(starts):
            sub = rpm[:, s0:s0 + n_lo]
            mu_k = sub.mean(axis=1)
            base = float(mu_k.mean())
            s_k = mu_k / base - 1.0
            eps = sub / mu_k[:, None] - 1.0
            rng = np.random.default_rng(1234 + si)
            ph0 = rng.uniform(0, 360.0 / N_BLADE, N_ROTOR)

            # 이 발췌의 레벨에 맞춘 OU
            jm = matched_jitter({"static_std_rel": float(np.std(s_k)),
                                 "wobble_std_rel": float(eps.std())}, DUR)
            arms = {}
            arms["A_measured"] = RPM0 * (1.0 + s_k[None, :] + spline_up(eps, fs, n_t, PRF))
            r2 = np.random.default_rng(hash((k, "B", si)) % 2 ** 31)
            sb, eb = model_lowrate(jm, n_lo, fs, r2)
            arms["B_sameband"] = RPM0 * (1.0 + sb[None, :] + spline_up(eb, fs, n_t, PRF))
            r3 = np.random.default_rng(hash((k, "C", si)) % 2 ** 31)
            sc, ec = model_lowrate(rd.PRESETS["outdoor"], int(DUR * 200) + 4, 200.0, r3)
            arms["C_outdoor"] = RPM0 * (1.0 + sc[None, :] + spline_up(ec, 200.0, n_t, PRF))
            arms["D_locked"] = np.full((n_t, N_ROTOR), RPM0)

            for nm, rpm_t in arms.items():
                for mode in ("quad", "single"):
                    # single = 로터 1개·정적산포 0 ⇒ **시간 흔들림만**의 선 넓힘을 분리한다
                    x = rpm_t if mode == "quad" else (
                        rpm_t[:, :1] / rpm_t[:, :1].mean() * RPM0)
                    e = echo(x, PRF, ph0)
                    f, P = spectrum(e, PRF)
                    cm = comb_metrics(f, P, F_FLASH)
                    cm["half_corr"] = half_corr(e, PRF, F_FLASH)
                    cm.update(_key=k, _arm=nm, _family=fam, _exc=si, _mode=mode,
                              _sw=float(eps.std()), _ss=float(np.std(s_k)))
                    rows.append(cm)
        print("done", k, flush=True)
    with open(f"{HERE}/comb_rows.json", "w") as fh:
        json.dump(dict(rows=rows, cfg=dict(prf=PRF, dur=DUR, rpm0=RPM0, f_flash=F_FLASH,
                                           lam=LAM, el_deg=EL_DEG, nr=NR, n_blade=N_BLADE,
                                           n_rotor=N_ROTOR, r_prop=R_PROP, fc=FC)), fh)
    print("rows", len(rows))


if __name__ == "__main__":
    run()
