# -*- coding: utf-8 -*-
"""clutter_methods_0901.py — 정지 클러터 제거 방식을 견준다 (사용자 요청 2026-09-01).

「지금 뭘 쓰고 있나 · MTI 같은 다른 방식과 차이는 뭔가」

■ 지금 덱이 쓰는 것 — `clutter_parts_ladder_0824.cs_eca`
    도플러 |f| ≤ 100 Hz 칸을 DFT 위에서 0 으로 만든다(직각 노치). 100 Hz 는 날개 박자
    126.7 Hz **아래**라 신호를 안 건드린다는 뜻으로 골랐다.

■ 견주는 방식
    none      아무것도 안 함 (기준)
    mean      평균만 뺀다 — 0 Hz 한 칸
    eca100    DFT 노치 |f| ≤ 100 Hz          ← 지금 쓰는 것
    eca50     DFT 노치 |f| ≤ 50 Hz           (좁게)
    mti2      2 펄스 소거 y[n] = x[n] − x[n−1]
    mti3      3 펄스 소거 y[n] = x[n] − 2x[n−1] + x[n−2]
    mti4      4 펄스 소거 (이항계수 1,−3,3,−1)
    svd1/2/3  부분공간 소거 — 느린시간을 행렬로 접어 상위 k 특이성분을 뺀다(ECA-B 계열)

■ 잣대 — 세 가지를 같이 본다. 하나만 보면 속는다.
    comb   빗살 대비 [dB]   (날개 배음 자리 ÷ 그 사이)
    corr   프롭 단독과의 상관 (되찾았나)
    dip%   낙차 자세가 남은 변동에서 갖는 몫 [%]  ⭐필터가 계단을 지웠나

    CUDA_VISIBLE_DEVICES="" PYTHONPATH=src:benchmark \
      /workspace/.venvs/py312/bin/python benchmark/clutter_methods_0901.py
"""
import json
import math
import os
import sys

import numpy as np

ROOT = "/workspace/sionna"
sys.path.insert(0, f"{ROOT}/benchmark")
sys.path.insert(0, f"{ROOT}/src")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

from clutter_parts_ladder_0824 import load, f_tip, PRF, FFL, HW   # noqa: E402

ARM_W = "sionna_p4000000000_r15_n8192_d1"
ARM_P = "sionna_p4000000000_partsprop_r15_n8192_d1"
ELS = (0.0, -30.0, -60.0)


# ── 방식들 ───────────────────────────────────────────────────────────────────
def m_none(x):
    return x


def m_mean(x):
    return x - x.mean()


def eca(fcut):
    def f(x):
        X = np.fft.fft(x)
        fr = np.fft.fftfreq(x.size, 1.0 / PRF)
        X[np.abs(fr) <= fcut] = 0.0
        return np.fft.ifft(X)
    return f


def mti(k):
    """k 펄스 소거 — 이항계수 (1−z⁻¹)^(k−1)."""
    c = np.array([(-1) ** i * math.comb(k - 1, i) for i in range(k)], float)
    def f(x):
        y = np.zeros_like(x)
        y[k - 1:] = sum(c[i] * x[k - 1 - i: x.size - i] for i in range(k))
        return y
    return f


def svd_sub(k, rows=64):
    """부분공간 소거 — 느린시간을 (rows × n/rows) 로 접고 상위 k 특이성분을 뺀다."""
    def f(x):
        n = (x.size // rows) * rows
        M = x[:n].reshape(rows, -1)
        U, S, Vh = np.linalg.svd(M, full_matrices=False)
        S2 = S.copy(); S2[:k] = 0.0
        y = np.zeros_like(x)
        y[:n] = (U @ np.diag(S2) @ Vh).ravel()
        return y
    return f


METHODS = [("none", m_none), ("mean", m_mean),
           ("eca100", eca(100.0)), ("eca50", eca(50.0)),
           ("mti2", mti(2)), ("mti3", mti(3)), ("mti4", mti(4)),
           ("svd1", svd_sub(1)), ("svd2", svd_sub(2)), ("svd3", svd_sub(3))]


# ── 잣대 ─────────────────────────────────────────────────────────────────────
def comb_db(x, ft):
    ac = x - x.mean()
    n = ac.size
    P = np.abs(np.fft.fft(ac * np.hanning(n))) ** 2
    fr = np.abs(np.fft.fftfreq(n, 1.0 / PRF))
    if ft < 3 * FFL:
        return float("nan")
    band = (fr >= 2 * FFL) & (fr <= ft)
    k = fr / FFL
    on = band & (np.abs(k - np.round(k)) * FFL <= HW)
    off = band & (np.abs(np.abs(k - np.floor(k)) - 0.5) * FFL <= HW)
    if on.sum() < 4 or off.sum() < 4:
        return float("nan")
    return float(10 * np.log10(P[on].mean() / max(P[off].mean(), 1e-300)))


def corr(a, b):
    a = a - a.mean(); b = b - b.mean()
    d = np.sqrt((np.abs(a) ** 2).sum() * (np.abs(b) ** 2).sum())
    return float(np.abs(np.vdot(a, b)) / max(d, 1e-300))


def main():
    out = {}
    for el in ELS:
        W, P = load(ARM_W, el)[0], load(ARM_P, el)[0]
        med = np.median(np.abs(W))
        bad = np.where(np.abs(W) / med < 0.9)[0]
        ft = f_tip(el)
        print(f"\n═══ el {el:+.0f}{chr(176)}   낙차 {len(bad)} 자세 · f_tip {ft:.0f} Hz")
        print(f"  {'방식':<9}{'comb [dB]':>11}{'corr':>9}{'dip 몫 [%]':>12}   비고")
        row = {}
        for name, fn in METHODS:
            y = fn(W)
            ac = np.abs(y - y.mean()) ** 2
            dip = 100.0 * ac[bad].sum() / max(ac.sum(), 1e-300) if len(bad) else 0.0
            c, r = comb_db(y, ft), corr(y, P)
            row[name] = dict(comb_db=None if np.isnan(c) else round(c, 2),
                             corr=round(r, 4), dip_pct=round(dip, 1))
            note = ""
            if name == "eca100":
                note = "← 지금 덱이 쓰는 것"
            print(f"  {name:<9}{c:>11.2f}{r:>9.4f}{dip:>12.1f}   {note}")
        out[f"el{el:+.0f}"] = row
    p = f"{ROOT}/outputs/clutter_methods_0901.json"
    json.dump(dict(_meta=dict(generator="benchmark/clutter_methods_0901.py",
                              arm_whole=ARM_W, arm_prop=ARM_P, prf_hz=PRF,
                              f_flash_hz=FFL, dip_rule="|E| < 0.9 x median",
                              note_ko=("정지 클러터 제거 방식 비교. comb=빗살 대비, "
                                       "corr=프롭 단독과의 상관, dip 몫=낙차 자세가 "
                                       "남은 변동에서 차지하는 비율.")),
                   **out), open(p, "w"), ensure_ascii=False, indent=1)
    print(f"\n  ✅ {p}")


if __name__ == "__main__":
    print("═══ 정지 클러터 제거 방식 비교 ═══")
    main()
