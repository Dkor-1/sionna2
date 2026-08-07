# -*- coding: utf-8 -*-
"""
report15_attack_spp_ladder_mini2.py — ⭐ 적대검증 Q1 전용 실측
================================================================================
Q1 "잡음바닥이 정말 바닥인가 — 표본수가 충분한가, spp 의존을 봤나" 에 답할 자료를 만든다.

기존 산출물에 **없는 것**을 정확히 두 가지 잰다.
  A. spp 사다리 — 판정 (a) 가 쓰는 통계 `total_ac_over_noise_db` 를 광선예산 16× 폭에서
     직접 잰다. 기존 shape_invariance 는 **모양·레벨**만 쟀고 (a) 통계는 한 번도 예산을
     바꿔 재지 않았다. 신호도 잡음도 √spp 로 함께 자라면 비가 불변이어야 한다 — 확인.
  B. 시드 사다리 — S=5 로 추정한 잡음바닥이 S 에 안정한가. S=16 까지 늘려서
     (a) 통계가 S 와 함께 어디로 가는지 본다. 부분집합 재표본으로 S=2..16 곡선도 낸다.

⛔ 기존 산출물 덮어쓰기 금지 → 출력은 outputs/report15_attack_spp_ladder_mini2.json (신규).
⛔ src/drones.py · src/drone_cad.py 는 읽기만 한다(SW 가 import 만 한다).
⛔ 숫자 손입력 금지.
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (os.path.join(ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.environ.setdefault(
    "REPORT15_SCRATCH",
    "/tmp/claude-1015/-home-yunjung-workspace/"
    "a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad/r15attack_mini2")

import report15_sweep_matrice4e as SW                                  # noqa: E402
from drones import DRONES, rotor_layout                                # noqa: E402

#  ⭐ 기체 교체 — report15_verdict_grid_mini2.py 와 같은 방식(모듈 전역 갈아끼우기)
SW.KEY = "mini2"
SW._SPEC = DRONES["mini2"]
SW._DIRS = [r["dir"] for r in rotor_layout(SW._SPEC)]

OUT_JSON = os.path.join(ROOT, "outputs", "report15_attack_spp_ladder_mini2.json")
SW.OUT_JSON = OUT_JSON            # 중간저장이 원본을 못 건드리게

#  ⭐ 판정의 선험 도플러칸(1/hot)을 포함하도록 자세는 hot 하나, 거리는 세 개 전부.
ASPECTS = (("hot", 0.0, 0.0),)
RANGES = (1.0, 3.0, 10.0)
MODES = (("prod", True),)         # 확산 채널 — 헤드라인이 여기서 나온다
N_PHASE = 64
SPP_LADDER = (256_000_000, 4_096_000_000)   # 16× 폭 (양 끝만 — 기울기에 충분)
SPP_MAIN = 2_048_000_000          # 본 격자가 쓴 값
SEEDS_A = (1, 2, 3, 4, 5)         # A: 본 격자와 같은 시드 집합
SEEDS_B = ()      # B(시드 사다리)는 matrice4e 쪽에서 이미 잰다


def main():
    t0 = time.time()
    os.makedirs(SW.SCRATCH, exist_ok=True)
    J = dict(meta=dict(
        script="benchmark/report15_attack_spp_ladder_mini2.py",
        role=("적대검증 Q1 — ⭐ mini2 는 광선예산 사다리를 한 번도 받은 적이 없다. 그것을 메운다"),
        drone=SW.KEY, fc_hz=SW.FC, max_depth=1, baseline_m=SW.BASELINE_M,
        n_phase=N_PHASE, aspects=[dict(name=n, az_deg=a, el_deg=e) for n, a, e in ASPECTS],
        ranges_m=[float(r) for r in RANGES], modes=[m for m, _ in MODES],
        spp_ladder=[int(s) for s in SPP_LADDER], spp_main_grid=int(SPP_MAIN),
        seeds_A=[int(s) for s in SEEDS_A], seeds_B=[int(s) for s in SEEDS_B],
        gpu=os.environ.get("CUDA_VISIBLE_DEVICES", "?"),
        gpu_status_at_start=SW.gpu_status(),
        stamp=time.strftime("%Y-%m-%d %H:%M:%S")), runs={})

    def save():
        J["meta"]["seconds_so_far"] = float(time.time() - t0)
        with open(OUT_JSON, "w") as f:
            json.dump(J, f, ensure_ascii=False)

    save()

    #  ── A. spp 사다리 ────────────────────────────────────────────────────────
    for spp in SPP_LADDER:
        tag = f"A_spp{spp}"
        print(f"\n===== A · spp={spp:,}  시드 {len(SEEDS_A)}  "
              f"추적 {N_PHASE*len(RANGES)*len(ASPECTS)*len(SEEDS_A)}", flush=True)
        sink: dict = {}
        g = SW.sec2_grid(n_phase=N_PHASE, seeds=SEEDS_A, spp=spp, ranges=RANGES,
                         aspects=ASPECTS, modes=MODES, sink=sink, save=save)
        J["runs"][tag] = dict(kind="spp_ladder", spp=int(spp),
                              seeds=[int(s) for s in SEEDS_A], grid=g)
        save()

    #  ── B 는 이 스크립트에서 생략 ───────────────────────────────────────────
    if not SEEDS_B:
        J["meta"]["gpu_status_at_end"] = SW.gpu_status()
        J["meta"]["seconds_total"] = float(time.time() - t0)
        save(); SW.drop(SW.SCRATCH)
        print(f"\n✅ 저장 → {OUT_JSON}  ({J['meta']['seconds_total']:.0f}s)")
        return
    tag = "B_seeds16"
    print(f"\n===== B · spp={SPP_MAIN:,}  시드 {len(SEEDS_B)}  "
          f"추적 {N_PHASE*len(RANGES)*len(ASPECTS)*len(SEEDS_B)}", flush=True)
    sink = {}
    g = SW.sec2_grid(n_phase=N_PHASE, seeds=SEEDS_B, spp=SPP_MAIN, ranges=RANGES,
                     aspects=ASPECTS, modes=MODES, sink=sink, save=save)
    J["runs"][tag] = dict(kind="seed_ladder", spp=int(SPP_MAIN),
                          seeds=[int(s) for s in SEEDS_B], grid=g)
    J["meta"]["gpu_status_at_end"] = SW.gpu_status()
    J["meta"]["seconds_total"] = float(time.time() - t0)
    save()
    SW.drop(SW.SCRATCH)
    print(f"\n✅ 저장 → {OUT_JSON}  ({J['meta']['seconds_total']:.0f}s)")


if __name__ == "__main__":
    main()
