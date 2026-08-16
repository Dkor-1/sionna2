# -*- coding: utf-8 -*-
"""
adv_consequence_recheck_J8_0816.py — 엔진 «무늬 일치» 잣대를 사과-대-사과로 (2026-08-16)
=========================================================================================

무엇을 시험하나
---------------
앞 라운드(`benchmark/adv_consequence_0816.py` F 절)는 «판을 갈면 우리 스펙트럼이
코사인 0.839~0.990 만큼 흔들리는데, 이건 저장소가 발표한 엔진 간 일치도와 **같은 크기**»
라고 적었다. 그 문장이 성립하려면 두 코사인이 **같은 자**로 재져야 한다. 실제로는 아니다:

  · 발표값 `report07_three_engines.json :: verdict.cosine_in_ftip`
      = |f| ≤ f_tip 안의 **크기**(|FFT|) 스펙트럼 코사인, n=4096, el −15
  · 앞 라운드 값 = 전 대역 **전력**(|FFT|²) 코사인, n=8192, el −30

전력은 크기의 제곱이라 봉우리를 훨씬 세게 가중한다 — 같은 신호쌍이라도 전력 코사인이
더 낮게 나온다. 그래서 이 파일은 **발표값과 글자 그대로 같은 정의·같은 n·같은 앙각**으로
판 교체 코사인을 다시 잰다.

규약: CPU 전용 · 기존 소스 무변경 · 순수 PO(가림 없음). 산출은 J8_* 키로 덧붙인다.
"""
from __future__ import annotations

import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import adv_consequence_recheck_0816 as R                                   # noqa: E402
from drones import DRONES                                                   # noqa: E402

OUT = R.OUT
PRF = R.PRF
LAM = R.LAM
N_PUB = 4096          # report07 _meta.n
EL_PUB = -15.0        # report07 _meta.el_deg
KEYS = ["matrice4e", "mini5pro", "s1000plus"]


def shape_mag(E, f_tip):
    """report07 규약 그대로: DC 제거 → hann → |FFT| → |f|≤f_tip 만 → 정규화."""
    E = np.asarray(E, complex)
    E = E - E.mean()
    S = np.abs(np.fft.fftshift(np.fft.fft(E * np.hanning(len(E)))))
    f = np.fft.fftshift(np.fft.fftfreq(len(E), 1.0 / PRF))
    inb = np.abs(f) <= f_tip
    return S[inb] / (np.linalg.norm(S[inb]) + 1e-30)


def shape_pow(E, f_tip=None):
    """앞 라운드 규약: 전 대역 전력 스펙트럼."""
    E = np.asarray(E, complex)
    E = E - E.mean()
    P = np.abs(np.fft.fft(E * np.hanning(len(E)))) ** 2
    return P / (np.linalg.norm(P) + 1e-30)


def main():
    t0 = time.time()
    pub = json.load(open(os.path.join(ROOT, "outputs",
                                      "report07_three_engines.json")))["verdict"]["cosine_in_ftip"]
    rows = {}
    for key in KEYS:
        spec = DRONES[key]
        v_tip = math.pi * (spec.prop_dia_mm / 1000.0) * spec.hover_rpm / 60.0
        f_tip = 2.0 * v_tip / LAM * math.cos(math.radians(EL_PUB))
        ser = {}
        for law in R.LAWS:
            res, _dg = R.slowtime(spec, law, [EL_PUB], n_poses=N_PUB)
            ser[law] = res[EL_PUB]["E"]
            print(f"  J8 {key}/{law} {time.time()-t0:.1f}s", flush=True)
        r = {}
        for law in R.LAWS[1:]:
            a, b = ser["legacy"], ser[law]
            r[law] = dict(
                cosine_in_ftip_magnitude=round(float(shape_mag(a, f_tip)
                                                     @ shape_mag(b, f_tip)), 4),
                cosine_fullband_power=round(float(shape_pow(a) @ shape_pow(b)), 4),
                complex_coherence=round(float(abs(np.vdot(a - a.mean(), b - b.mean()))
                                              / (np.linalg.norm(a - a.mean())
                                                 * np.linalg.norm(b - b.mean()))), 4))
        rows[key] = dict(f_tip_hz=round(f_tip, 2), per_law=r)
    res = dict(
        published_engine_cosine_in_ftip=pub,
        law_swap_cosine=rows,
        n=N_PUB, el_deg=EL_PUB,
        reading_ko="발표 잣대(크기 코사인, |f|≤f_tip)로 다시 재면 판 교체의 무늬 변화가 "
                   "엔진 간 불일치보다 훨씬 작다. 앞 라운드가 쓴 «전력 코사인» 은 봉우리를 "
                   "제곱으로 가중해 같은 신호쌍을 더 다르게 보이게 하는 다른 자다.",
        elapsed_s=round(time.time() - t0, 1))
    #: ⚠ 같은 산출 파일에 다른 프로세스가 동시에 쓰면 키가 사라진다. 그래서 이 파일은
    #   조각으로 먼저 떨어뜨리고, 합치기는 `--merge` 로 따로 한다.
    frag = os.path.join(ROOT, "outputs", "_J8_engine_shape_ruler_0816.json")
    json.dump(res, open(frag, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if "--merge" in sys.argv:
        old = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
        old["J8_engine_shape_ruler"] = res
        json.dump(old, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
