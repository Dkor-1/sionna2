# -*- coding: utf-8 -*-
"""build_physics_vs_deck_fig.py — ⭐«물리를 켜면 STFT 가 어제 덱과 닮게 나오나»

■ 사용자 물음 (2026-08-11)
    *"굴절 투과 회절 다중반사 이런거까지 키고 돌리면 아주 느리니?
      어제 팀미팅때 했던 자료 STFT 그리면 유사하게 나오나? 그것은 확인해봐야할거같은데"*

■ 왜 이 비교가 성립하나 — 기하가 **정확히 같다**
    8/11 덱      : matrice4e · az 0° · **el −15°** · 3.5 GHz · PRF 19,700 · 4,096 자세
    앙각 스윕    : matrice4e · az 0° · **el −15°** · 3.5 GHz · PRF 19,700 · 4,096 자세
    ⚠다른 것은 **거리 하나뿐**이다 — 덱은 3/8/15/40 m, 스윕은 10 m(8 과 15 사이).
      그래서 «닮았나» 는 물어도 되지만 «같아야 한다» 고 하면 안 된다.

■ 무엇을 나란히 놓나 (전부 같은 STFT 규약 `md_mapstyle.flash_spec`)
    ① ours          우리 커널, 모서리 회절 OFF   (지금까지의 정본)
    ② ours_ptd      우리 커널 + **PTD 모서리 회절 ON**
    ③ sionna        PathSolver, 굴절·회절·다중반사 **OFF** (지금까지의 정본)
    ④ sionna_phys   PathSolver, 굴절·회절·모서리회절 **ON**, max_depth=3
    ⑤ deck 8 m / 15 m   어제 덱이 실제로 쓴 그림의 원본 시계열(있으면)

⛔**STFT 만 쓴다** — 재할당·WVD 금지(프로젝트 상설 규칙).
⛔패널마다 **자기 최대값으로 정규화**한다. 팔 사이 정규화가 달라(우리 −54 dB 대
   PathSolver −125 dB) 밝기를 나란히 비교하면 거짓이 된다.

■ 닮음을 눈으로만 보지 않는다 — 숫자로도 낸다
    · 빗살 간격(플래시 박자)과 그 오차
    · 대역 상단이 예측 f_tip 을 따르는가
    · 두 맵의 **상관** (같은 시간·주파수 격자에서 dB 맵끼리)
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, f"{ROOT}/src")
sys.path.insert(0, f"{ROOT}/benchmark")

import matplotlib                                                    # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                      # noqa: E402
from md_mapstyle import flash_spec, draw                             # noqa: E402

NPZ = f"{ROOT}/outputs/elevation_sweep_md.npz"
JSN = f"{ROOT}/outputs/elevation_sweep_md.json"
DECK = f"{ROOT}/outputs/deck_ours_by_range.npz"
OUTP = f"{ROOT}/outputs/figures/physics_vs_deck_el-15.png"
OUTJ = f"{ROOT}/outputs/physics_vs_deck.json"

EL = "-15"
FTIP = 1272.9 * np.cos(np.radians(-15.0))   # 덱과 같은 예측 상한선
# (npz 키, 화면 이름, 무슨 물리가 켜져 있나)
ARMS = [
    ("ours/el-15",        "Ours (SBR+PO)",        "transmission on, edge diffraction off"),
    ("ours_ptd/el-15",    "Ours + PTD",           "transmission on, edge diffraction ON"),
    ("sionna/el-15",      "PathSolver (as run)",  "refraction off, diffraction off, 1 bounce"),
    ("sionna_phys/el-15", "PathSolver + physics 11.1M",
     "refraction ON, diffraction ON, 3 bounces"),
    # ⭐공정 예산 — 물리를 켜면 경로가 굶으므로 같은 11.1M 비교는 성립하지 않는다
    ("sionna_p250000000_phys/el-15", "PathSolver + physics 250M",
     "physics ON at the budget that gives 127-352 paths"),
]
# ⚠덱 npz 에 실제로 있는 거리만 넣는다 — 없는 키를 적으면 조용히 빠진다
DECK_KEYS = [("R3/E", "Deck 3 m (ours)"), ("R15/E", "Deck 15 m (ours)"),
             ("R40/E", "Deck 40 m (ours)")]


def load() -> tuple[dict, float, float]:
    d = np.load(NPZ, allow_pickle=True)
    meta = json.load(open(JSN))["_meta"]
    prf, ffl = float(meta["prf_hz"]), float(meta["f_flash_hz"])
    series = {k: np.asarray(d[k]) for k in d.files if k in {a[0] for a in ARMS}}
    if os.path.exists(DECK):
        z = np.load(DECK, allow_pickle=True)
        for k, nm in DECK_KEYS:
            if k in z.files:
                series[f"deck:{k}"] = np.asarray(z[k])
    return series, prf, ffl


def metrics(E: np.ndarray, prf: float, ffl: float) -> dict:
    """맵을 안 보고도 «닮았나» 를 말할 수 있게 하는 스칼라들."""
    E = np.asarray(E, complex)
    n = E.size
    x = E - E.mean()                       # 0 Hz(정지 동체) 제거
    # ⭐마이크로도플러는 **양쪽 스펙트럼**이다(다가오는 날개 ⊕, 멀어지는 날개 ⊖).
    #   E 가 복소라 rfft 를 쓰면 안 된다 — 반쪽만 보게 되고 부호 정보를 버린다.
    S = np.abs(np.fft.fft(x * np.hanning(n))) ** 2
    fr = np.fft.fftfreq(n, 1 / prf)
    floor = float(np.median(S[np.abs(fr) > 2500]))
    lines = {}
    for m in range(1, 9):
        f0 = ffl * m
        w = (np.abs(np.abs(fr) - f0) <= 12)          # ±m·f_flash 양쪽을 함께 본다
        lines[f"{m}x"] = round(float(10 * np.log10(S[w].max() / floor)), 2) if w.any() else None
    # 빗살 간격 — ⊕쪽 1~8 차 첨두 위치의 차이 중앙값
    pk = []
    for m in range(1, 9):
        f0 = ffl * m
        w = np.where((fr >= f0 - 20) & (fr <= f0 + 20))[0]
        if w.size:
            pk.append(float(fr[w[np.argmax(S[w])]]))
    spacing = float(np.median(np.diff(pk))) if len(pk) > 2 else float("nan")
    return dict(comb_spacing_hz=round(spacing, 2),
                comb_spacing_err_hz=round(spacing - ffl, 2),
                line_snr_db=lines,
                ac_over_dc_db=round(float(10 * np.log10(
                    (np.abs(x) ** 2).mean() / max((np.abs(E.mean()) ** 2), 1e-300))), 2))


def main() -> None:
    series, prf, ffl = load()
    have = [(k, nm, phys) for k, nm, phys in ARMS if k in series]
    missing = [k for k, _, _ in ARMS if k not in series]
    deck = [(f"deck:{k}", nm) for k, nm in DECK_KEYS if f"deck:{k}" in series]
    panels = have + [(k, nm, "deck reference") for k, nm in deck]
    if not panels:
        raise SystemExit("⛔ 그릴 것이 없다 — 시계열이 아직 안 났다")

    os.makedirs(f"{ROOT}/outputs/figures", exist_ok=True)
    ncol = min(3, len(panels))
    nrow = int(np.ceil(len(panels) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(5.4 * ncol, 4.0 * nrow), squeeze=False)

    out = {"_meta": {
        "generator": "benchmark/build_physics_vs_deck_fig.py",
        "question_ko": "물리(굴절·회절·다중반사)를 켜면 STFT 가 8/11 덱과 닮게 나오나",
        "geometry_ko": ("덱과 앙각 스윕은 matrice4e·az 0°·el −15°·3.5 GHz·PRF 19,700·"
                        "4,096 자세로 **같다**. 다른 것은 거리뿐 — 덱 3/8/15/40 m, 스윕 10 m."),
        "prf_hz": prf, "f_flash_hz": ffl,
        "stft_ko": "md_mapstyle.flash_spec (STFT 만. ⛔재할당·WVD 안 씀)",
        "normalisation_ko": "패널마다 자기 최대값 — 팔 사이 정규화가 달라 밝기 비교는 거짓이 된다",
        "missing_arms": missing,
    }, "cells": {}}

    maps = {}
    for ax, (key, nm, phys) in zip(axes.ravel(), panels):
        E = series[key]
        f, t, S, _ = flash_spec(np.asarray(E, complex), prf, ffl)
        maps[key] = (f, t, S)
        draw(ax, t, f, S, FTIP)          # 덱 빌더와 같은 인자 순서
        ax.set_title(f"{nm}\n{phys}", fontsize=9)
        out["cells"][key] = metrics(E, prf, ffl)
    for ax in axes.ravel()[len(panels):]:
        ax.axis("off")

    # 맵끼리의 상관 — «닮았나» 를 눈이 아니라 수로
    ref = "ours/el-15"
    if ref in maps:
        fr, tr, Sr = maps[ref]
        for k, (f2, t2, S2) in maps.items():
            if k == ref or S2.shape != Sr.shape:
                continue
            a = 10 * np.log10(Sr / Sr.max() + 1e-12)
            b = 10 * np.log10(S2 / S2.max() + 1e-12)
            out["cells"].setdefault(k, {})["corr_with_ours_db_map"] = round(
                float(np.corrcoef(a.ravel(), b.ravel())[0, 1]), 4)

    fig.suptitle("Micro-Doppler at el -15 deg, 10 m — physics on vs off "
                 "(each panel normalised to its own maximum)", fontsize=11)
    fig.tight_layout()
    fig.savefig(OUTP, dpi=150)
    json.dump(out, open(OUTJ, "w"), ensure_ascii=False, indent=1)

    print(f"  패널 {len(panels)} 장" + (f"  ⚠아직 없는 팔: {missing}" if missing else ""))
    print(f"  {'팔':<22}{'빗살간격[Hz]':>13}{'오차':>8}{'1x':>7}{'2x':>7}{'AC/DC':>9}{'ours와 상관':>12}")
    for k, v in out["cells"].items():
        ls = v.get("line_snr_db", {})
        print(f"  {k:<22}{v.get('comb_spacing_hz', float('nan')):13.2f}"
              f"{v.get('comb_spacing_err_hz', float('nan')):+8.2f}"
              f"{(ls.get('1x') or float('nan')):7.1f}{(ls.get('2x') or float('nan')):7.1f}"
              f"{v.get('ac_over_dc_db', float('nan')):9.2f}"
              f"{v.get('corr_with_ours_db_map', float('nan')):12.4f}")
    print(f"\n  → {OUTP}\n  → {OUTJ}")


if __name__ == "__main__":
    main()
