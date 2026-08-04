# -*- coding: utf-8 -*-
"""
report15_probe_harmonics.py — 위상축 h(φ) 가 **구조를 갖는가** (탐침의 사후분석)
================================================================================

`report15_probe.py` 가 낸 outputs/report15_probe.json 을 읽어, 위상 스윕이 만든
h(φ) 가 **주기적 구조**를 갖는지 두 가지로 검사하고 같은 파일에 `analysis` 로 덧붙인다.
⛔ 광선을 다시 쏘지 않는다(측정 재사용). ⛔ 다른 산출물을 건드리지 않는다.

왜 필요한가 — ANOVA 만으로는 부족하다:
  분산분석은 "위상마다 평균이 다르다"까지만 말한다. 몬테카를로 잡음도 시드평균이
  위상마다 조금씩 다르므로, 표본이 커지면 F 는 언젠가 유의해진다. **진짜 로터 변조라면
  거기에 더해 (a) 이웃 위상끼리 이어져 매끈하고 (b) 블레이드 주기의 조화성분에
  에너지가 몰려야** 한다. 잡음은 둘 다 못 한다.

검사 ①  조화 분해 — h(φ) 의 dB 계열을 위상축으로 DFT.
        스윕 구간이 한 주기(=360/n_blades)이므로 빈 m 은 **회전당 m·n_blades 사이클**이다.
        m=1 이 곧 블레이드 플래시(2날이면 회전당 2회)다.
        비교 기준: 시드잡음이 만드는 빈당 기대 진폭 ≈ σ_noise/√(S·N/2).
검사 ②  매끈함 — 위상축 잔차의 **lag-1 순환 자기상관** ρ₁.
        독립잡음이면 ρ₁≈0(±1/√N), 매끈한 곡선이면 ρ₁→1.
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
JSON = os.path.join(ROOT, "outputs", "report15_probe.json")


def _lag1(x):
    """순환 lag-1 자기상관 (평균 제거 후)."""
    x = np.asarray(x, float) - np.mean(x)
    d = float(np.dot(x, x))
    return float(np.dot(x, np.roll(x, 1)) / d) if d > 0 else 0.0


def analyse(rows_verdict, sweep_rows, noise_std, channel) -> dict:
    """한 (기체, 자세, 모드, 채널) 조합의 구조 분석."""
    y = rows_verdict.get("phase_mean_amp_db")
    if not y or len(y) < 4:
        return dict(ok=False, reason="위상 표본 부족")
    y = np.asarray(y, float)
    N = y.size
    S = int(rows_verdict.get("seeds_per_phase") or 1)
    Y = np.fft.rfft(y - y.mean()) / N
    amp = 2.0 * np.abs(Y)                       # 단측 진폭 [dB 단위의 진폭]
    order = np.arange(amp.size)                 # 빈 m: 회전당 m·n_blades 사이클
    # 잡음이 한 빈에 넣을 기대 진폭 — 위상평균의 표준오차가 N 개 빈에 퍼진다
    se = (float(noise_std) / math.sqrt(S)) if noise_std else None
    bin_noise = (se * math.sqrt(2.0 / N)) if se else None
    k = int(np.argmax(amp[1:]) + 1) if amp.size > 1 else 0
    res = y - y.mean()
    if k:                                       # 최강 조화를 뺀 잔차의 매끈함도 본다
        t = np.arange(N)
        c = np.cos(2 * np.pi * k * t / N); s = np.sin(2 * np.pi * k * t / N)
        res = res - (2 * (res @ c) / N) * c - (2 * (res @ s) / N) * s
    return dict(
        ok=True, channel=channel, n_phase=N, seeds_per_phase=S,
        amp_db_by_bin=[float(v) for v in amp],
        bin_cycles_per_rev=[int(v) for v in order * 2],   # 2날 기준 표기(빈×n_blades)
        dominant_bin=int(k), dominant_amp_db=float(amp[k]) if amp.size > 1 else None,
        noise_amp_per_bin_db=bin_noise,
        dominant_over_noise=(float(amp[k] / bin_noise) if (bin_noise and amp.size > 1) else None),
        harmonic_concentration=float(amp[k] ** 2 / max(np.sum(amp[1:] ** 2), 1e-30))
        if amp.size > 1 else None,
        lag1_autocorr=_lag1(y), lag1_autocorr_after_fit=_lag1(res),
        lag1_null_sd=float(1.0 / math.sqrt(N)),
        smooth=bool(_lag1(y) > 3.0 / math.sqrt(N)),
        structured=bool(bin_noise and amp.size > 1 and amp[k] > 3.0 * bin_noise
                        and _lag1(y) > 3.0 / math.sqrt(N)),
        note=("빈 m 은 회전당 m·n_blades 사이클. m=1 이 블레이드 플래시. "
              "structured = 최강 조화가 잡음빈의 3배 초과 AND 위상축이 매끈(ρ₁>3/√N)."))


def main():
    with open(JSON) as f:
        J = json.load(f)
    out = {}
    for key, R in J["airframes"].items():
        per = {}
        for tag, vkey in (("ref", "verdict"), ("hot", "verdict_hot")):
            V = R.get(vkey)
            if not V:
                continue
            sw = R.get("D_sweep" if tag == "ref" else "D_sweep_hot")
            for ck, v in V.items():
                if not v.get("ok"):
                    continue
                mode = ck.split("/")[0]; ch = ck.split("/")[1]
                per[f"{tag}/{ck}"] = analyse(v, (sw or {}).get("by_mode", {}).get(mode, []),
                                             v.get("noise_floor_std_db"), ch)
        out[key] = per
        for ck, a in per.items():
            if a.get("ok"):
                print(f"  [{key}] {ck:22s} 최강조화 m={a['dominant_bin']} "
                      f"진폭 {a['dominant_amp_db']:.3f} dB  잡음빈 "
                      f"{(('%.3f' % a['noise_amp_per_bin_db']) if a['noise_amp_per_bin_db'] else 'n/a')} dB "
                      f"(×{(('%.1f' % a['dominant_over_noise']) if a['dominant_over_noise'] else 'n/a')})"
                      f"  ρ₁={a['lag1_autocorr']:+.3f}  구조적={a['structured']}")
    J["analysis_harmonics"] = out
    with open(JSON, "w") as f:
        json.dump(J, f, ensure_ascii=False, indent=1)
    print(f"\n✅ analysis_harmonics 추가 → {JSON}")
    return out


if __name__ == "__main__":
    sys.exit(0 if main() is not None else 1)
