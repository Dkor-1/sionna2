# -*- coding: utf-8 -*-
"""
report15_verdict_grid_mini2.py — **mini2 를 matrice4e 와 똑같은 격자로 Sionna 추적**
================================================================================

왜 이 스크립트가 필요한가
  판정을 **기체별로 따로** 내라는 지시인데, 지금 자료가 비대칭이다:
    · matrice4e : 거리 3 × 자세 5 × 위상 64 × 시드 5 × 채널 2 격자가 있다
                  (outputs/report15_sionna_sweep_matrice4e.json)
    · mini2     : R=3 m 한 점, 자세 2개(ref·hot), 위상 32 뿐이다(탐침·널대조).
  기체가 갈리는지 보려면 **같은 격자**여야 한다. 다른 격자에서 나온 두 수를 나란히 놓고
  "기체가 갈린다" 고 말할 수 없다.

⭐ 그래서 계측 하네스를 새로 짜지 않고 **matrice4e 스크립트의 함수를 그대로 불러 쓴다**.
   KEY 만 mini2 로 갈아끼운다. 관측량 정의(h = Σ a·exp(−j2πf_c·τ))·씬 조립·경로 분류·
   광선예산이 한 글자도 갈라지지 않아야 두 기체를 같은 축 위에 놓을 수 있다.

⛔ src/drones.py · src/drone_cad.py 는 **읽기만** 한다.
⛔ 기존 산출물 덮어쓰기 금지 — 출력은 outputs/report15_verdict_grid_mini2.json 하나(신규).
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

#  ⚠ SW 를 import 하는 순간 gpu.pick() 이 돌고 mitsuba 가 올라간다. 그 전에 스크래치를 갈라둔다.
os.environ.setdefault(
    "REPORT15_SCRATCH",
    "/tmp/claude-1015/-workspace/"
    "a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad/r15verdict_mini2")

import report15_sweep_matrice4e as SW                                  # noqa: E402
from drones import DRONES, rotor_layout                                # noqa: E402

# --------------------------------------------------------------------------- #
#  ⭐ 기체 교체 — 모듈 전역을 갈아끼운다. _SPEC·_DIRS 는 import 시점에 굳으므로 같이 고친다.
# --------------------------------------------------------------------------- #
KEY = "mini2"
SW.KEY = KEY
SW._SPEC = DRONES[KEY]
SW._DIRS = [r["dir"] for r in rotor_layout(SW._SPEC)]

OUT_JSON = os.path.join(ROOT, "outputs", "report15_verdict_grid_mini2.json")
SW.OUT_JSON = OUT_JSON          # 중간저장이 matrice4e 파일을 건드리지 않도록

#  matrice4e 와 **완전히 동일한** 격자 — 이것이 이 스크립트의 존재 이유다
RANGES = SW.RANGES              # (1, 3, 10) m
ASPECTS = SW.ASPECTS            # nose·oblique·side·hot·disc
N_PHASE = SW.N_PHASE            # 64 (한 주기 180° 등분 = 회전당 128 스텝)
SEEDS = SW.SEEDS                # (1,2,3,4,5)
MODES = SW.MODES                # spec / prod
SPP = 2_048_000_000             # ⭐ matrice4e 본 격자와 같은 광선예산(그 JSON grid.spp 에서 읽어 검증)


def _matrice4e_spp() -> int | None:
    """matrice4e 격자가 실제로 쓴 spp 를 읽어 온다 — 손입력한 숫자가 맞는지 대조."""
    try:
        with open(os.path.join(ROOT, "outputs",
                               "report15_sionna_sweep_matrice4e.json")) as f:
            return int(json.load(f)["grid"]["spp"])
    except Exception:
        return None


def main():
    t0 = time.time()
    ref_spp = _matrice4e_spp()
    spp = int(ref_spp) if ref_spp else SPP
    print(f"⭐ mini2 격자 — matrice4e 와 동일 조건")
    print(f"   거리 {RANGES}  자세 {[a[0] for a in ASPECTS]}  위상 {N_PHASE}  "
          f"시드 {SEEDS}  채널 {[m[0] for m in MODES]}")
    print(f"   spp = {spp:,}  (matrice4e 격자 실측값 {ref_spp:,})" if ref_spp
          else f"   spp = {spp:,}")
    print(f"   총 추적 = {N_PHASE * len(RANGES) * len(ASPECTS) * len(MODES) * len(SEEDS):,}")

    os.makedirs(SW.SCRATCH, exist_ok=True)
    J: dict = {}
    sink: dict = {}
    #  ⚠ 버그를 낸 자리 — save() 가 J["grid"] 를 **무조건** sink 로 덮어써서, sec2_grid 가
    #    돌려준 완성 격자(phases_deg·aspects·complete 포함)를 중간저장본으로 되돌려 놓았다.
    #    완성본이 들어온 뒤에는 sink 를 쓰지 않는다.
    grid_final = {"done": False}

    def save():
        if not grid_final["done"]:
            J["grid"] = sink
        J["meta"]["seconds_so_far"] = float(time.time() - t0)
        with open(OUT_JSON, "w") as f:
            json.dump(J, f, ensure_ascii=False)

    J["meta"] = dict(
        script="benchmark/report15_verdict_grid_mini2.py",
        drone=KEY, name=SW._SPEC.name,
        role="matrice4e 격자와 **동일 조건**의 mini2 대조 — 기체별 판정을 위해",
        harness="benchmark/report15_sweep_matrice4e.py 의 함수를 그대로 호출(정의 갈라짐 0)",
        observable="h = Σ_p a_p·exp(−j2πf_c·τ_p)  (Paths.a 는 패스밴드라 위상이 없다)",
        fc_hz=SW.FC, lambda_m=SW.LAM, baseline_m=SW.BASELINE_M, max_depth=1,
        ranges_m=[float(r) for r in RANGES],
        aspects=[dict(name=n, az_deg=a, el_deg=e) for n, a, e in ASPECTS],
        n_phase_steps=int(N_PHASE), seeds=[int(s) for s in SEEDS], spp=int(spp),
        spp_source=("matrice4e grid.spp 에서 읽음" if ref_spp else "기본값"),
        gpu=os.environ.get("CUDA_VISIBLE_DEVICES", "?"),
        gpu_status_at_start=SW.gpu_status(),
        stamp=time.strftime("%Y-%m-%d %H:%M:%S"))

    print("\n§0  물리·재질 (전부 계산)")
    J["physics"] = SW.sec0_physics(N_PHASE)
    J["materials"] = SW.sec0_materials()
    J["prop_normals"] = SW.sec0_prop_normals()
    save()

    print("\n§1  180° 주기 확인 (메쉬 · RT)")
    J["period_check"] = SW.sec1_period()
    save()

    print("\n§2  본 격자")
    J["grid"] = SW.sec2_grid(n_phase=N_PHASE, seeds=SEEDS, spp=spp, ranges=RANGES,
                             aspects=ASPECTS, modes=MODES, sink=sink, save=save)
    grid_final["done"] = True
    save()

    print("\n§3  격자 분석 (경로수 거동 · 0-경로 비율 · 대칭 널 조화)")
    J["grid_analysis"] = SW.sec3_analyze(J["grid"])
    #  통계 블록은 matrice4e 와 **같은 함수**로 낸다 — 판정 기준이 갈라지면 안 된다.
    md = {}
    for k, B in J["grid"]["blocks"].items():
        for ch in ("all", "prop"):
            try:
                md[f"{k}/{ch}"] = SW._stat_block(B, N_PHASE, len(SEEDS), channel=ch)
            except Exception as e:                       # 경로 0 칸 등
                md[f"{k}/{ch}"] = dict(error=str(e))
    J["modulation_depth"] = dict(by_block=md, n_seeds=len(SEEDS))
    save()

    J["meta"]["gpu_status_at_end"] = SW.gpu_status()
    J["meta"]["seconds_total"] = float(time.time() - t0)
    save()
    SW.drop(SW.SCRATCH)
    print(f"\n✅ 저장 → {OUT_JSON}   ({J['meta']['seconds_total']:.0f}s)")


if __name__ == "__main__":
    main()
