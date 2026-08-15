# -*- coding: utf-8 -*-
"""
ptd_level_probe.py — ours+PTD 팔의 **레벨차**(−30° 에서 −2.8 dB)가 프린지 물리인지 해부.

배경(2026-08-15 사용자 지시)
---------------------------
ours 와 ours+PTD 는 무늬(리듬 몫·맵상관 ≥0.998)는 사실상 같은데 **레벨**만
0° +0.15 / −30° −2.77 / −60° +1.91 dB 로 갈렸다. 이 dB 가
  (a) 모서리 프린지가 PO 플래시와 간섭한 **정합적 물리**인지
  (b) 버그(원점 불일치·스케일 오류 등)의 냄새인지
를 커널 재실행 없이 원장 두 팔의 차 Δ = E_ptd − E_ours 로 판정한다.

판정 잣대 — 물리라면 이래야 한다
  ① Δ 자체가 날개 박자에 잠겨 있다(comb-locked). 프린지의 주역이 회전하는 프로펠러
     모서리라면 Δ 의 리듬 몫이 높아야 한다. 버그성 잡음이면 백색(≈13 %)이다.
  ② Δ 는 플래시 순간에 몰린다 — |Δ|² 와 |E_ours,AC|² 의 상관이 양수로 유의해야 한다
     (모서리 정반사 조건은 면 정반사 조건과 같은 자세 근방에서 성립한다).
  ③ 레벨차의 부호는 간섭 교차항이 정한다: P_ptd − P_ours = 2Re⟨E_ac Δ_ac*⟩ + ‖Δ_ac‖².
     −30° 의 −2.8 dB 는 교차항이 음(상쇄 간섭)이어야 하고, 그 상쇄가 몇 자세에
     몰린 이상치가 아니라 플래시들에 고르게 퍼져 있어야 한다.
  ④ 프린지 몫 ‖Δ‖²/‖E_ac‖² 이 각도에 따라 매끄럽게 변한다(한 각도만 폭주하면 냄새).

    PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/ptd_level_probe.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, HERE)
from comb_snr import band_g                                            # noqa: E402

J = json.load(open(f"{ROOT}/outputs/elevation_sweep_md.json"))
Z = np.load(f"{ROOT}/outputs/elevation_sweep_md.npz", allow_pickle=True)
M = J["_meta"]
PRF, FFL = float(M["prf_hz"]), float(M["f_flash_hz"])
ROW = {(r["engine"], r["el_deg"]): r for r in J["rows"]}

A_PO = "ours_r15_n8192"
A_PT = "ours_ptd_r15_n8192"
ELS = [0.0, -30.0, -60.0, -90.0]


def rhythm(E, ftip, hw=8.0):
    """상한 위 에너지 중 박자 정수배 몫 [%] — 격자·덱과 같은 레시피."""
    n = E.size
    P = np.abs(np.fft.fft((E - E.mean()) * np.hanning(n))) ** 2
    fr = np.fft.fftfreq(n, 1.0 / PRF)
    above = np.abs(fr) >= ftip
    k = np.round(np.abs(fr) / FFL)
    on = np.abs(np.abs(fr) - k * FFL) <= hw
    return float(100.0 * P[above & on].sum() / P[above].sum())


def db(x):
    return 10.0 * np.log10(x)


doc = {"_meta": {
    "generator": "benchmark/ptd_level_probe.py",
    "question_ko": "ours+PTD 레벨차(−30° −2.8 dB)가 프린지 물리인가 버그인가",
    "identity_ko": "P_ptd − P_ours = 2Re⟨E_ac Δ_ac*⟩ + ‖Δ_ac‖², Δ = E_ptd − E_ours",
    "arms": [A_PO, A_PT],
}, "cells": {}}

print(f"{'el':>5} {'레벨차dB':>8} {'교차항':>8} {'|Δ|²항':>8} {'프린지몫%':>9} "
      f"{'Δ리듬%':>7} {'플래시상관':>9} {'대역차dB':>8}")
for el in ELS:
    Eo = np.asarray(Z[f"{A_PO}/el{el:+.0f}"], complex)
    Ep = np.asarray(Z[f"{A_PT}/el{el:+.0f}"], complex)
    ft = float(ROW[(A_PO, el)]["f_tip_hz"])
    ao, ap = Eo - Eo.mean(), Ep - Ep.mean()
    d = ap - ao                                   # Δ 의 AC 성분
    Po, Pp, Pd = np.mean(np.abs(ao) ** 2), np.mean(np.abs(ap) ** 2), np.mean(np.abs(d) ** 2)
    cross = 2.0 * float(np.mean(ao * np.conj(d)).real)
    # 항등식 검사 — Pp − Po 가 cross + Pd 와 맞는가(수치 안전판)
    ident = abs((Pp - Po) - (cross + Pd)) / max(Po, 1e-300)
    # 플래시 집중 — |Δ|² 와 |E_ac|² 의 피어슨 상관
    x, y = np.abs(d) ** 2, np.abs(ao) ** 2
    fcorr = float(np.corrcoef(x, y)[0, 1])
    # 대역(블레이드 밴드) 레벨차 — −90° 는 대역이 정의되지 않아 건너뛴다
    bdb = None
    go, _ = band_g(Eo, PRF, el)
    gp, _ = band_g(Ep, PRF, el)
    if go is not None and gp is not None:
        bdb = float(db(gp.mean() / go.mean()))
    cell = dict(
        level_db=round(float(db(Pp / Po)), 2),
        cross_term_rel=round(cross / Po, 4),
        delta_term_rel=round(Pd / Po, 4),
        identity_residual=float(ident),
        fringe_share_pct=round(100.0 * Pd / Po, 2),
        delta_rhythm_pct=round(rhythm(d + 0j, ft), 1),
        flash_corr=round(fcorr, 3),
        band_level_db=None if bdb is None else round(bdb, 2),
        arm_rhythm_pct=[round(rhythm(Eo, ft), 1), round(rhythm(Ep, ft), 1)],
    )
    doc["cells"][f"el{el:+.0f}"] = cell
    print(f"{el:+5.0f} {cell['level_db']:8.2f} {cell['cross_term_rel']:8.3f} "
          f"{cell['delta_term_rel']:8.3f} {cell['fringe_share_pct']:9.1f} "
          f"{cell['delta_rhythm_pct']:7.1f} {cell['flash_corr']:9.3f} "
          f"{'—' if bdb is None else f'{bdb:8.2f}'}")
    assert ident < 1e-9, f"⛔ 항등식 붕괴 el{el}: {ident:.2e}"

p = f"{ROOT}/outputs/ptd_level_probe.json"
json.dump(doc, open(p, "w"), ensure_ascii=False, indent=1)
print(f"✅ {p}")
