# -*- coding: utf-8 -*-
"""
comb_snr.py — ⭐**프로펠러 줄무늬가 실제로 보이는가**를 재는 잣대 두 개.

왜 새로 만드나
--------------
2026-08-14 적대 검증이 기존 잣대(AC/DC)를 무너뜨렸다. 무너진 이유가 셋이다.

1. AC/DC 의 **분자는 정지 성분 × 변조 성분의 교차항**이다. 정지 성분이 크면 분자도 같이
   부풀어, 정지 성분 제거 전후의 AC/DC 를 dB 로 빼는 것은 **서로 다른 통계를 비교**하는 것이다.
2. 정지 성분을 뺀 AC/DC 는 **주기성이 0 인 백색잡음도 통과**한다(−6.0 ~ −1.8 dB).
3. 실제 줄무늬 세기와 **역상관**이다(Spearman ρ = −0.774) — 순위를 뒤집는다.

⚠ 이 파일의 정의는 **검증에서 살아남은 구현을 그대로 옮긴 것**이다. 임의로 바꾸지 마라.
  제로패딩을 넣거나 median 을 mean 으로 바꾸면 값이 수십 dB 부풀어 판정이 달라진다.

두 잣대
-------
① `comb_snr(E)`   느린시간 FFT 에서 **블레이드 대역 안**의 f_flash 조화선 대 바닥.
                  도플러 스펙트럼에 날개 선이 서 있는가.
② `mod_snr(g)`    블레이드 대역 전력 g(t) 의 변조 스펙트럼에서 f_flash 조화선 대 바닥.
                  «맵에서 줄무늬가 시간축으로 뛰는가» 의 직접 검사.

⭐**문턱은 치환 널** — g(또는 E)의 시간축을 뒤섞어 주기성을 없앤 판을 같은 파이프라인에
통과시킨 값의 **최댓값**. 그 위면 «보인다».

    PYTHONPATH=src:benchmark python benchmark/comb_snr.py --arms <팔> ... --out x.json
"""
from __future__ import annotations

import argparse
import glob
import json
import re
import os
import sys

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SHD = os.path.join(ROOT, "outputs", "elev_sweep_shards")
TJ = json.load(open(os.path.join(ROOT, "outputs",
                                 "report07_three_engines.json")))["_meta"]
F0 = float(TJ["f_flash_hz"])                 # 126.67 Hz — 날개 통과율
FTIP0 = float(TJ["f_tip_hz"]) / np.cos(np.radians(-15.0))
PERIODS, HOP, PAD = 0.45, 2, 8               # 검증에서 쓴 STFT 설정
N_NULL = 60


FC0_HZ = 3.5e9                               # 정본 반송파 — FTIP0 가 이 값에서 나왔다


def carrier_of(arm: str) -> float:
    """팔 이름의 `_fc<MHz>` 꼬리표에서 반송파 [Hz]. 없으면 정본 3.5 GHz.

    ⚠`_partsfc`(비행제어기 그룹) 에 안 걸리도록 **숫자를 반드시** 요구한다
      (`elevation_sweep_md.carrier_of` 와 같은 규칙)."""
    m = re.search(r"_fc(\d+(?:\.\d+)?)", arm or "")
    return FC0_HZ if not m else float(m.group(1)) * 1e6


def f_tip(el, arm=""):
    """⭐날개 끝 도플러 [Hz] — **반송파에 비례한다**(f_tip = 2 v_tip / λ = 2 v_tip fc / c).

    ⛔**2026-09-02 결함**: 여기 반송파 항이 없었다. FTIP0 는 3.5 GHz 원장에서 왔는데
      `--fc-ghz` 판(5.8 / 10 / 24 GHz)을 그대로 읽으면 대역이 최대 6.9 배 어긋나
      **모든 칸이 «빗살 안 보임» 으로 거짓 판정**된다. 팔 이름에서 반송파를 읽어 곱한다.
    """
    return FTIP0 * np.cos(np.radians(float(el))) * (carrier_of(arm) / FC0_HZ)


def load(arm, el):
    """팔 하나 · 앙각 하나. 빠진 자세가 있으면 None."""
    fs = sorted(glob.glob(f"{SHD}/{arm}_el{el:+.0f}_*.npz"))
    if not fs:
        return None, None
    E = prf = seen = None
    for f in fs:
        d = np.load(f)
        m = np.asarray(d["meta"], float)
        if E is None:
            n = int(m[3]); prf = float(m[4])
            E = np.zeros(n, complex); seen = np.zeros(n, bool)
        ii = d["idx"].astype(int)
        E[ii] = d["E"]; seen[ii] = True
    return (E, prf) if seen.all() else (None, None)


def _stft(E, prf):
    nper = max(8, int(round(PERIODS * prf / F0)))
    nfft = PAD * nper
    w = np.hanning(nper + 1)[:-1]
    fr = sliding_window_view(np.asarray(E, complex), nper)[::HOP]
    S = np.abs(np.fft.fft(fr * w, n=nfft, axis=1)).T / w.sum()
    f = np.fft.fftfreq(nfft, 1.0 / prf)
    return np.fft.fftshift(f), np.fft.fftshift(S, axes=0), nper


def band_g(E, prf, el, arm=""):
    """블레이드 대역 전력 g(t) 와 그 표본율."""
    ft = f_tip(el, arm)
    if ft <= 1e-6:
        return None, None
    f, S, nper = _stft(E, prf)
    m = (np.abs(f) >= 0.35 * ft) & (np.abs(f) <= ft)
    if m.sum() < 2:
        return None, None
    return (S ** 2)[m, :].sum(axis=0), prf / HOP


def comb_snr(E, prf, el, guard=3, arm=""):
    """① 느린시간 FFT — 블레이드 대역 안의 f_flash 조화선 대 바닥 [dB]."""
    n = E.size
    x = (E - E.mean()) * np.hanning(n)
    X = np.abs(np.fft.fft(x)) ** 2
    f = np.fft.fftfreq(n, 1 / prf); df = prf / n
    ft = f_tip(el, arm)
    band = (np.abs(f) >= 0.35 * ft) & (np.abs(f) <= ft)
    on = np.zeros(n, bool); harms = []
    k = 1
    while k * F0 <= ft * 1.001:
        if k * F0 >= 0.35 * ft:
            harms.append(k)
        b = int(round(k * F0 / df))
        for s in (1, -1):
            for d in range(-guard, guard + 1):
                on[(s * b + d) % n] = True
        k += 1
    fl = band & ~on
    if not harms or fl.sum() == 0:
        return None
    pk = [max(X[(s * int(round(k * F0 / df)) + d) % n]
              for s in (1, -1) for d in range(-guard, guard + 1)) for k in harms]
    return float(10 * np.log10(np.median(pk) / np.median(X[fl])))


def mod_snr(g, fs_g, kmax=8, guard=4):
    """② g(t) 가 f_flash 로 뛰는가 — «맵에 줄무늬가 보인다» 의 직접 검사 [dB]."""
    n = g.size
    y = (g - g.mean()) * np.hanning(n)
    Y = np.abs(np.fft.rfft(y)) ** 2
    fr = np.fft.rfftfreq(n, 1 / fs_g); df = fs_g / n
    on = np.zeros(Y.size, bool); pk = []
    for k in range(1, kmax + 1):
        b = int(round(k * F0 / df))
        if b + guard >= Y.size:
            break
        on[b - guard:b + guard + 1] = True
        pk.append(Y[b - guard:b + guard + 1].max())
    sel = (fr > 20) & (fr < kmax * F0 * 1.3)
    if not pk or not (sel & ~on).any():
        return None
    return float(10 * np.log10(np.median(pk) / np.median(Y[sel & ~on])))


def measure(arm, el, seed=20260814):
    E, prf = load(arm, el)
    if E is None:
        return None
    rng = np.random.default_rng(seed)
    c = comb_snr(E, prf, el)
    g, fsg = band_g(E, prf, el)
    m = mod_snr(g, fsg) if g is not None else None
    # 치환 널 — 시간축을 뒤섞어 주기성을 없앤다
    cn, mn = [], []
    for _ in range(N_NULL):
        p = rng.permutation(E.size)
        v = comb_snr(E[p], prf, el)
        if v is not None:
            cn.append(v)
        if g is not None:
            v2 = mod_snr(rng.permutation(g), fsg)
            if v2 is not None:
                mn.append(v2)
    out = dict(arm=arm, el_deg=float(el))
    if c is not None and cn:
        out.update(comb_snr_db=round(c, 2), comb_null_max=round(max(cn), 2),
                   comb_visible=bool(c > max(cn)))
    if m is not None and mn:
        out.update(mod_snr_db=round(m, 2), mod_null_max=round(max(mn), 2),
                   mod_visible=bool(m > max(mn)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", nargs="+", required=True)
    ap.add_argument("--els", default="0,-15,-30,-45,-60,-75")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    els = [float(x) for x in a.els.split(",") if x.strip()]
    rows = []
    for key, lab in (("comb", "① 느린시간 FFT — 날개 선이 서 있나"),
                     ("mod", "② 맵 변조 — 줄무늬가 시간축으로 뛰나")):
        print(f"\n=== {lab}  [dB, * = 치환 널 위] ===")
        print(f"{'팔':40s}" + "".join(f"{('0' if e == 0 else e):>9}" for e in els) + "   보임")
        print("─" * (40 + 9 * len(els) + 8))
        for arm in a.arms:
            cells, ok, tot = "", 0, 0
            for el in els:
                r = next((x for x in rows if x["arm"] == arm and x["el_deg"] == el), None)
                if r is None:
                    r = measure(arm, el)
                    if r: rows.append(r)
                if not r or f"{key}_snr_db" not in r:
                    cells += f"{'—':>9s}"; continue
                tot += 1
                vis = r[f"{key}_visible"]
                ok += int(vis)
                cells += f"{r[f'{key}_snr_db']:8.1f}" + ("*" if vis else " ")
            print(f"{arm:40s}{cells}   {ok}/{tot}")
    if a.out and rows:
        json.dump(rows, open(a.out, "w"), ensure_ascii=False, indent=1)
        print(f"\n  → {a.out}  ({len(rows)} 행)")


if __name__ == "__main__":
    main()
