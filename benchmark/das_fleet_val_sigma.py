# -*- coding: utf-8 -*-
"""
das_fleet_val_sigma.py — ⭐ 28 쌍 대조를 완성하기 위한 **phantom3 바이스태틱** σ(f, θb)
==========================================================================================
왜 이 파일이 따로 있나
  outputs/das_fleet_ours.json 은 mini2·m350rtk·phantom2 세 기체만 바이스태틱을 냈다.
  phantom3 는 **모노스태틱만**(outputs/p3_ours.json) 있다 — 그래서 대조표가 3×7+1 = 22 셀이고
  Das Table III 가 주는 28 셀(4 기체 × 7 각도)을 못 채운다. 이 파일이 그 6 셀(θb=15..90)을
  채운다. θb=0 은 통제군 검산으로 같이 계산해 p3_ours 와 맞는지 본다.

⛔ 건드리지 않는 것
  · benchmark/das_fleet_sigma.py 를 **편집하지 않는다** — 지금 그 파일로 도는 워커가 있다.
    대신 import 해서 GRIDS/LADDER/PARTIAL 만 이 프로세스 안에서 확장한다.
  · outputs/p3_*.json · outputs/das_fleet_*.json 을 쓰지 않는다. 이 파일은
    outputs/partial/das_fleet_val_0803/ 아래에만 쓴다.

규약 (das_fleet_prereg.json :: execution_contract 그대로 — 함대와 같은 자)
  div=16 · jitter=2 · max_bounce=1 · penetrate=True · exit_vis=True · symmetrize=False · ptd=False
  기하: 입사 az=φ, 산란 az=φ+θb, el=0 (표적 좌표계). θb 는 TX–표적–RX 낀각.
  격자: 1.8–18.2 GHz 21 점(p3_ours el0 과 **같은 격자**) × 방위 360 점 전주기(p3_ours 와 같다).

실행:
    bash benchmark/das_fleet_val_driver.sh <워커수> <GPU목록>
"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (os.path.join(ROOT, "src"), os.path.join(ROOT, "benchmark")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np                                   # noqa: E402
import das_fleet_sigma as dfs                        # noqa: E402  (import 시 gpu.pick() 실행)

#  ⭐ 새 키로만 추가한다. 기존 GRIDS 세 항목은 손대지 않는다.
dfs.GRIDS["phantom3"] = dict(
    mesh_key="phantom3", band_ghz=(1.8, 18.2),
    f_ghz=np.linspace(1.8, 18.2, 21),
    az_n=360,
    az_note="0:1:360 (360 unique) — p3_ours.json el0 과 같은 격자. "
            "⚠ Das Table I 은 −90:2:90 (91 점 180° 호)이고 시작각이 미상이다.",
    f_note="p3_ours el0 과 같은 21 점 균등격자 — θb=0 열이 통제군 검산이 되도록 맞췄다.",
    proxy_mesh=False)
dfs.LADDER["phantom3"] = [0, 1, 2, 3]

#  ⭐ 부분저장 위치를 함대 라운드와 **분리**한다(그 디렉터리는 다른 워크플로가 쓴다).
dfs.PARTIAL = os.path.join(ROOT, "outputs", "partial", "das_fleet_val_0803")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", default="phantom3:0,phantom3:1,phantom3:2,phantom3:3")
    a = ap.parse_args()
    plan = [(s.split(":")[0], int(s.split(":")[1])) for s in a.plan.split(",") if s.strip()]
    dfs.run_plan(plan)


if __name__ == "__main__":
    main()
