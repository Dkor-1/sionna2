# -*- coding: utf-8 -*-
"""
lowfreq_grid.py — **저주파 격차의 원인을 가른다: 표본화(A)인가 PO 근본한계(B)인가**
=====================================================================================
관측(2026-08-03, outputs/p3_ours.json el0, div=16):
    전대역 1.8–18.2 GHz  a = +0.4198 dB/GHz  (Das 실측 0.21 의 2.00 배)
    부분대역 1.8–6.0     a = +1.563 (R²=0.96)
    부분대역 6.0–18.2    a = +0.199 (R²=0.33)   ← 실측과 사실상 일치
  → 격차가 **전부 저주파에** 있다.

가설
  A 표본화 — 광선격자 d 가 λ 에 비례(λ/12·λ/16)하므로 저주파에서 절대적으로 성기다.
            특징 치수는 주파수와 무관하게 고정이다 → 저주파에서 형상이 표본화되지 않는다.
            **설정으로 고칠 수 있다.**
  B PO 근본한계 — 1.8 GHz 에서 특징/λ ≈ 0.15 라 PO 의 국소평면 가정이 깨진다.
            크리핑파·표면파도 PO 엔 없다. **설정으로 못 고친다.**

결정 실험
  같은 주파수에서 d 를 **λ 상대가 아니라 절대값[mm]으로** 계단식으로 줄이며 μ(f) 를 본다.
    · μ 가 크게 움직여 λ/12·λ/16 값과 다른 값으로 수렴 → A
    · μ 가 λ/12·λ/16 값 근처에 머묾            → B
  ⚠ 곡면 수렴은 단조롭지 않다(실루엣 grazing 위상 에일리어싱). 한 점이 아니라 **사다리 전체 추세**로 본다.
  그 다음 수렴 격자로 **부분대역 기울기를 다시 적합**해 Das 0.21 과의 배수를 다시 잰다.

실행:  ~/.venvs/py312/bin/python benchmark/lowfreq_grid.py --stage run
       ~/.venvs/py312/bin/python benchmark/lowfreq_grid.py --stage analyze
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

import numpy as np

ROOT = "/workspace/sionna"
SCRATCH = "/tmp/claude-1015/-workspace/a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad/lfg"
OUT_JSON = os.path.join(ROOT, "outputs", "lowfreq_grid.json")
FIG_PATH = os.path.join(ROOT, "outputs", "figs", "lowfreq_grid_convergence.png")

C0 = 299792458.0
N_AZ = 360                                   # 생산 규약과 동일 (Δ=1°)

#  판정용 사다리 주파수 — 저주파 3 · 고주파 2 (지시된 최소집합)
LADDER_F = [1.8, 3.5, 6.0, 12.0, 18.2]
#  절대 격자 사다리 [mm]. λ/12·λ/16 은 주파수마다 따로 붙인다(λ 상대 기준선).
ABS_D_MM = [6.0, 3.0, 1.5, 0.75, 0.5]
#  저주파 2 점은 한 계단 더 — "0.5 mm 도 아직 안 수렴했나" 를 본다.
EXTRA_D_MM = {1.8: [0.375], 3.5: [0.375]}

#  부분대역 재적합용 주파수 = 생산 산출(p3_ours el0)과 **같은 21 점 격자**.
REFIT_F = [round(x, 4) for x in np.linspace(1.8, 18.2, 21)]
D_CONV_MM = 0.75                             # 재적합에 쓸 수렴 격자(사다리 결과로 사후검증)
D_BASE_DIV = 16                              # 재적합 기준선 = 생산 λ/16


def build_tasks():
    tasks = []
    seen = set()

    def add(f_ghz, d_mm, tag):
        key = (round(f_ghz, 4), round(d_mm, 5))
        if key in seen:
            return
        seen.add(key)
        tasks.append(dict(f_ghz=round(float(f_ghz), 4), d_mm=round(float(d_mm), 5),
                          n_az=N_AZ, tag=tag))

    for f in LADDER_F:
        lam_mm = C0 / (f * 1e9) * 1e3
        add(f, lam_mm / 12.0, "ladder_lam12")
        add(f, lam_mm / 16.0, "ladder_lam16")
        for d in ABS_D_MM + EXTRA_D_MM.get(f, []):
            add(f, d, "ladder_abs")
    for f in REFIT_F:
        lam_mm = C0 / (f * 1e9) * 1e3
        add(f, lam_mm / D_BASE_DIV, "refit_base_lam16")
        add(f, D_CONV_MM, "refit_conv")
    return tasks


def _cost(t, r_max=0.30789):
    """대략적 상대비용 ∝ n_az · (2·Rout/d)²  (LPT 분배용, 절대시간 아님)."""
    d = t["d_mm"] * 1e-3
    rout = r_max * 1.15 + 3 * d
    n = np.ceil(2 * rout / d)
    return t["n_az"] * n * n


def partition(tasks, n_workers):
    """LPT(긴 것부터) 그리디 — 워커별 총비용을 맞춘다."""
    order = sorted(tasks, key=_cost, reverse=True)
    bins = [[] for _ in range(n_workers)]
    load = np.zeros(n_workers)
    for t in order:
        i = int(np.argmin(load))
        bins[i].append(t)
        load[i] += _cost(t)
    return bins, load


def run(n_workers, gpus, mem_mb):
    os.makedirs(SCRATCH, exist_ok=True)
    tasks = build_tasks()
    bins, load = partition(tasks, n_workers)
    print(f"[driver] 태스크 {len(tasks)} 개 → 워커 {n_workers} 개, "
          f"상대부하 최소/최대 = {load.min():.3g}/{load.max():.3g}")

    procs = []
    for i, b in enumerate(bins):
        tf = os.path.join(SCRATCH, f"tasks_{i}.json")
        of = os.path.join(SCRATCH, f"part_{i}.json")
        json.dump(b, open(tf, "w"))
        if os.path.exists(of):
            os.remove(of)
        env = dict(os.environ)
        env["SIONNA2_GPU"] = str(gpus[i % len(gpus)])
        env["SIONNA2_GPU_MEM"] = str(mem_mb)
        env["PYTHONPATH"] = f"{ROOT}/src:{ROOT}/benchmark"
        log = open(os.path.join(SCRATCH, f"log_{i}.txt"), "w")
        p = subprocess.Popen([os.path.expanduser("~/.venvs/py312/bin/python"),
                              os.path.join(ROOT, "benchmark", "lowfreq_grid_worker.py"), tf, of],
                             cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        procs.append((p, of, log))
        print(f"[driver] worker{i} pid={p.pid} gpu={env['SIONNA2_GPU']} tasks={len(b)}")
    for p, _, _ in procs:
        p.wait()
    for _, _, log in procs:
        log.close()
    print("[driver] 워커 종료. 반환코드:", [p.returncode for p, _, _ in procs])


def collect():
    recs = []
    for fn in sorted(os.listdir(SCRATCH)):
        if fn.startswith("part_") and fn.endswith(".json"):
            recs += json.load(open(os.path.join(SCRATCH, fn)))
    return recs


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="run")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--gpus", default="3,2")
    ap.add_argument("--mem", type=int, default=4500)
    a = ap.parse_args()
    if a.stage == "run":
        t0 = time.time()
        run(a.workers, [int(x) for x in a.gpus.split(",")], a.mem)
        print(f"[driver] 총 벽시계 {time.time()-t0:.0f}s")
    elif a.stage == "tasks":
        ts = build_tasks()
        print(len(ts), "tasks; total rel-cost", sum(_cost(t) for t in ts))
        for t in sorted(ts, key=_cost, reverse=True)[:8]:
            print(t, f"{_cost(t):.3g}")
