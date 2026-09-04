# -*- coding: utf-8 -*-
"""
true_repeat_0903.py — PathSolver 재현성을 **같은 설정의 진짜 재실행**으로 잰다.

왜 다시 재나
    docs/DEEP_DROP_0902.md 가 인용해 온 「회절 켬 8~26 자세」는 `depth_axis_verdict_0816.json`
    의 **E0↔E1 짝**에서 나온 값이다. 그 원장은 스스로 설계를 밝혀 뒀다 —
    「모서리 E 는 닫힌 메쉬에서 경로를 사실상 안 바꾸니 «같은 물리의 재실행» 으로 쓴다」.

    ⛔그 논리는 순환이다. E 가 정말 무동작이면 두 판이 비트 동일해야 하는데, 실제로는
      다르다. 그 «다름» 을 비결정성이라 부르려면 E 가 무동작임을 먼저 보여야 하고,
      E 의 무동작을 보이려면 재현성이 먼저 있어야 한다. 하나로 둘을 다 살 수 없다.
    ⚠게다가 7 쌍 중 4 쌍이 F0(확산 끔) 팔이다 — 이 판의 상시 규약(확산은 항상 켠다) 밖이라
      애초에 인용하면 안 되는 칸이다. 깊이도 1 과 3 이 섞여 있다.

    ⭐디스크에 **진짜 재실행**이 있다: `…rep…` 샤드 354 장. 정본 메쉬 · 15 m · 깊이 2 ·
      확산 켬 · 앙각 6 개. 설정이 완전히 같고 이름만 다른 판이다. 이것으로 잰다.
    ⚠⚠**판 수가 칸마다 다르다** — PathSolver 네 팔은 el 0·−30·−60 에서 **5 판**,
      el −15·−45·−75 에서 **3 판**이고, **우리 커널 팔은 여섯 앙각 전부 2 판**이다
      (`n_reps` 열이 칸마다 적는다). 판이 적을수록 «다른 자세» 가 덜 나오므로
      **비교가 우리 쪽에 유리하게 기운다.** 판 수가 다른 칸끼리 `n_poses_any` 와
      `bit_identical` 을 나란히 읽지 않는다.

무엇을 내나
    팔 × 앙각마다 **그 칸에 있는 판 전부**를 서로 견줘
      · n_poses_any      한 자세라도 값이 다른 자세 수
      · n_poses_material 상대차 1 % 를 넘는 자세 수
      · max_rel          자세 상대차의 최대
      · d_power_db       판 사이 이동 전력 차의 최대 [dB]
      · bit_identical    그 칸의 판이 **전부** 비트 동일한가 (판 수는 `n_reps` 열)

    ⛔판정은 하지 않는다. 「회절을 켜면 깨진다」 같은 문장은 이 스크립트가 아니라
      사람이 원장을 보고 쓴다(주장 게이트 ⓑ).

쓰는 법
    CUDA_VISIBLE_DEVICES="" PYTHONPATH=src \
        ~/.venvs/py312/bin/python benchmark/true_repeat_0903.py
"""
from __future__ import annotations

import collections
import glob
import json
import os
import re

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SHD = os.path.join(ROOT, "outputs", "elev_sweep_shards")
OUT = os.path.join(ROOT, "outputs", "true_repeat_0903.json")

#: 정본 판만 본다 — 15 m · 정본 메쉬 · 깊이 2. 다른 판을 섞으면 다시 사과 ↔ 배가 된다.
KEEP = "_r15_n8192_rep"
NAME = re.compile(r"^(?P<a>.+?)_rep(?P<rep>\d+)(?P<b>.*?)_el(?P<el>[+-][\d.]+)_(?P<sh>\d+)\.npz$")


def bits_of(arm: str) -> str:
    m = re.search(r"sw(R\dD\dE\dF\d)", arm)
    return m.group(1) if m else ("OURS" if arm.startswith("ours") else "?")


def load_run(arm: str, rep: int, el: float):
    """한 판(팔·재실행 번호·앙각)의 자세별 복소 진폭을 자세 번호 순으로 잇는다."""
    idx, val = [], []
    for f in glob.glob(os.path.join(SHD, "*.npz")):
        m = NAME.match(os.path.basename(f))
        if not m or int(m.group("rep")) != rep or float(m.group("el")) != el:
            continue
        if (m.group("a") + m.group("b")).replace("__", "_") != arm:
            continue
        z = np.load(f)
        idx.append(z["idx"])
        val.append(z["E"])
    if not idx:
        return None
    i = np.concatenate(idx)
    v = np.concatenate(val)
    o = np.argsort(i)
    return i[o], v[o]


def main() -> None:
    runs = collections.defaultdict(lambda: collections.defaultdict(set))
    for f in glob.glob(os.path.join(SHD, "*_rep*.npz")):
        b = os.path.basename(f)
        if KEEP not in b:
            continue
        m = NAME.match(b)
        if not m:
            continue
        arm = (m.group("a") + m.group("b")).replace("__", "_")
        runs[arm][float(m.group("el"))].add(int(m.group("rep")))

    cells = []
    print("═══ 같은 설정 재실행 — 판 사이 차이 ═══\n")
    print(f"  {'조합':9s} {'앙각':>6s} {'판':>2s} {'비트동일':>7s} {'값다른자세':>9s} "
          f"{'1%넘는자세':>9s} {'최대상대차':>9s} {'전력차dB':>9s}")
    for arm in sorted(runs):
        for el in sorted(runs[arm], reverse=True):
            reps = sorted(runs[arm][el])
            got = [(r, load_run(arm, r, el)) for r in reps]
            got = [(r, g) for r, g in got if g is not None]
            if len(got) < 2:
                continue
            base_i = got[0][1][0]
            if any(not np.array_equal(g[0], base_i) for _, g in got):
                print(f"  ⚠{arm} el{el:+.0f} — 판마다 자세 집합이 다르다, 건너뛴다")
                continue
            mats = np.stack([g[1] for _, g in got])          # (판, 자세)
            amp = np.abs(mats)
            ref = amp[0]
            denom = np.where(ref > 0, ref, np.nan)
            rel = np.nanmax(np.abs(amp - ref) / denom, axis=0)
            any_diff = int(np.sum(np.any(mats != mats[0], axis=0)))
            material = int(np.nansum(rel > 0.01))
            mx = float(np.nanmax(rel)) if np.isfinite(rel).any() else 0.0
            pw = 10 * np.log10(np.mean(amp ** 2, axis=1) + 1e-300)
            dpw = float(pw.max() - pw.min())
            bit = any_diff == 0
            cells.append(dict(arm=arm, combo=bits_of(arm), el_deg=el, n_reps=len(got),
                              bit_identical=bit, n_poses=int(mats.shape[1]),
                              n_poses_any=any_diff, n_poses_material=material,
                              max_rel=mx, d_power_db=dpw))
            print(f"  {bits_of(arm):9s} {el:+6.0f} {len(got):2d} {'✅' if bit else '⛔':>6s} "
                  f"{any_diff:9d} {material:9d} {mx:9.4f} {dpw:9.5f}")

    doc = {"_meta": {
        "generator": "benchmark/true_repeat_0903.py",
        "what_ko": "같은 설정을 이름만 바꿔 여러 판 돌린 «진짜 재실행» 으로 잰 PathSolver 재현성. "
                   "정본 메쉬 · 15 m · 깊이 2 · 확산 켬 · 자세 8192.",
        "why_ko": "옛 값(depth_axis_verdict_0816 : pathsolver_repeatability.diffraction_on)은 "
                  "E0↔E1 짝이라 «모서리가 무동작이다» 를 가정해야 성립했고, 7 쌍 중 4 쌍이 "
                  "확산 끔(F0) 팔이었다. 이 원장은 그 가정을 안 쓴다.",
        "reads_ko": "판정은 여기 적지 않는다 — 셀을 보고 사람이 쓴다(주장 게이트 ⓑ).",
    }, "cells": cells}
    json.dump(doc, open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"\n  ✅ {os.path.relpath(OUT, ROOT)}  ({len(cells)} 칸)")


if __name__ == "__main__":
    main()
