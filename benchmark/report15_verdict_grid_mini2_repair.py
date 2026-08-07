# -*- coding: utf-8 -*-
"""
report15_verdict_grid_mini2_repair.py — 격자 JSON 의 **메타데이터만** 복구한다
================================================================================

무슨 일이 있었나
  report15_verdict_grid_mini2.py 의 save() 클로저가 J["grid"] 를 **무조건** 중간저장본(sink)
  으로 덮어썼다. sec2_grid 가 돌려준 완성 격자(phases_deg·aspects·seeds·geometry·complete)가
  마지막 save() 에서 다시 sink 로 되돌아갔고, 그래서 sec3_analyze 가 KeyError 로 죽었다.

⭐ 값비싼 것은 **하나도 안 잃었다** — 9600 추적의 결과(blocks: 64 위상 × 5 시드 × 30 블록)는
   sink 안에 그대로 있다. 잃은 것은 전부 **결정론적으로 재계산 가능한 메타데이터**다.
   그러므로 다시 추적하지 않고 복구한다(GPU 안 씀).

⛔ 복구는 **재계산**이지 손입력이 아니다. 위상축·자세·기하는 원 스크립트와 같은 식으로 다시 만든다.
⛔ 원본을 덮어쓰기 전에 .prerepair 사본을 남긴다.
"""
from __future__ import annotations

import json
import math
import os
import shutil
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (os.path.join(ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from drones import DRONES                                              # noqa: E402

C0 = 299792458.0
FC = 3.5e9
BASELINE_M = 0.20
KEY = "mini2"
RANGES = (1.0, 3.0, 10.0)
ASPECTS = (("nose", 0.0, 15.0), ("oblique", 45.0, 15.0), ("side", 90.0, 15.0),
           ("hot", 0.0, 0.0), ("disc", 0.0, 75.0))
N_PHASE = 64
SEEDS = (1, 2, 3, 4, 5)
MODES = ("spec", "prod")
PATH = os.path.join(ROOT, "outputs", "report15_verdict_grid_mini2.json")


def look_dir(az_deg, el_deg):
    a, e = math.radians(az_deg), math.radians(el_deg)
    return np.array([math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)])


def basis_perp(u):
    t = np.array([0.0, 0.0, 1.0]) if abs(u[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    e1 = np.cross(u, t); e1 /= np.linalg.norm(e1)
    return e1, np.cross(u, e1)


def place_facts(az, el, rng, baseline=BASELINE_M):
    """report15_sweep_matrice4e.place() 와 **같은 식**으로 기하 사실을 다시 만든다."""
    u = look_dir(az, el)
    e1, _ = basis_perp(u)
    tx = rng * u + 0.5 * baseline * e1
    rx = rng * u - 0.5 * baseline * e1
    R1 = float(np.linalg.norm(tx)); R2 = float(np.linalg.norm(rx))
    bi = float(np.degrees(np.arccos(np.clip(float((tx / R1) @ (rx / R2)), -1.0, 1.0))))
    return dict(az_deg=float(az), el_deg=float(el), range_m=float(rng),
                baseline_m=float(baseline), bistatic_deg=bi,
                tau_expect_ns=float((R1 + R2) / C0 * 1e9),
                tx=[float(v) for v in tx], rx=[float(v) for v in rx])


def main():
    with open(PATH) as f:
        J = json.load(f)
    G = J["grid"]
    if G.get("complete"):
        print("이미 온전하다 — 할 일 없음")
        return

    blocks = G["blocks"]
    spec = DRONES[KEY]
    period = 360.0 / int(spec.prop_blades)
    phis = np.arange(N_PHASE) * (period / N_PHASE)

    #  ── 무결성 검사 먼저: 값이 정말 다 있는가 (없으면 복구가 아니라 은폐가 된다) ──
    bad = []
    for k, B in blocks.items():
        for fld in ("n", "n_prop", "hr", "hi", "hpr", "hpi"):
            a = np.asarray(B[fld], float)
            if a.shape != (N_PHASE, len(SEEDS)):
                bad.append(f"{k}.{fld} shape={a.shape}")
    if bad:
        raise SystemExit("⛔ 블록이 온전하지 않다 — 복구 중단:\n  " + "\n  ".join(bad[:10]))
    n_traced = sum(np.asarray(B["n"], float).size for B in blocks.values())
    expect = len(blocks) * N_PHASE * len(SEEDS)
    print(f"무결성 OK — 블록 {len(blocks)}개, 칸 {n_traced} (기대 {expect}), "
          f"n_traces={G.get('n_traces')}")

    shutil.copy2(PATH, PATH + ".prerepair")

    geo = {f"{R:g}/{ak}": place_facts(az, el, R)
           for R in RANGES for ak, az, el in ASPECTS}
    G.update(phases_deg=[float(x) for x in phis], phase_span_deg=float(period),
             phase_step_deg=float(period / N_PHASE),
             steps_per_revolution=float(N_PHASE * 360.0 / period),
             seeds=[int(s) for s in SEEDS], spp=int(J["meta"]["spp"]),
             ranges=[float(r) for r in RANGES],
             aspects=[dict(name=n, az_deg=a, el_deg=e) for n, a, e in ASPECTS],
             modes=list(MODES), max_depth=1, baseline_m=BASELINE_M,
             geometry=geo, seconds=float(G.get("seconds_so_far") or 0.0),
             complete=True)
    J["meta"]["repair"] = dict(
        script="benchmark/report15_verdict_grid_mini2_repair.py",
        what_ko=("save() 클로저가 완성 격자를 중간저장본으로 덮어써서 phases_deg·aspects·"
                 "geometry·complete 가 사라졌다. 추적 결과(blocks)는 손실 없음."),
        recovered_keys=["phases_deg", "phase_span_deg", "phase_step_deg",
                        "steps_per_revolution", "seeds", "spp", "ranges", "aspects",
                        "modes", "max_depth", "baseline_m", "geometry", "complete"],
        method_ko="원 스크립트와 같은 식으로 **재계산**했다(손입력 아님). GPU 미사용.",
        backup=os.path.relpath(PATH + ".prerepair", ROOT),
        integrity_checked_cells=int(n_traced))
    with open(PATH, "w") as f:
        json.dump(J, f, ensure_ascii=False)
    print(f"✅ 복구 완료 → {PATH}")
    print(f"   위상 {len(phis)}개 {phis[0]:.4f}…{phis[-1]:.4f}° (주기 {period}°), "
          f"자세 {len(ASPECTS)}, 거리 {RANGES}, 기하 {len(geo)} 칸")


if __name__ == "__main__":
    main()
