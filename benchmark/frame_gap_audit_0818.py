# -*- coding: utf-8 -*-
"""
frame_gap_audit_0818.py — 표준 프레임에 **빈칸이 남았나**를 원장에서 직접 센다
================================================================================

왜 필요한가
-----------
`docs/RESUME.md` 는 «빈 칸이 채워지기 전에는 분류·완성표를 돌리지 않는다 — 표본이 각도마다
다르면 깨진다» 를 규칙으로 못 박았다. 그런데 «채워졌나» 를 판정하는 코드가 없어서 사람이
눈으로 세고 있었다. 이 파일이 그 판정을 **원장에서 기계로** 낸다.

무엇을 세나
-----------
표준 프레임 = 팔 3 × 기체 4 × 앙각 10 = **120 칸**.
  * 팔   : ours(우리 커널) · ps_off(물리 끔, `sionna…_d1`) · refr(굴절만, `sionna…_onlyrefr…`)
  * 기체 : matrice4e(접미사 없음) · mavic4pro · mini5pro · s1000plus
  * 앙각 : 0 · −15 · −30 · −45 · −52 · −60 · −68 · −75 · −82 · −90
조건은 **r15 · n8192 · 방위 0°** 로 고정한다(방위 축은 별도 팔이라 여기서 뺀다).

⛔GPU·솔버 없음. `outputs/elevation_sweep_md.json` 만 읽는다.
산출: `outputs/frame_gap_audit_0818.json` (+ 표준출력에 표)

실행:  PYTHONPATH=src:benchmark \
       /workspace/.venvs/py312/bin/python benchmark/frame_gap_audit_0818.py
"""
from __future__ import annotations

import collections
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LEDGER = os.path.join(ROOT, "outputs", "elevation_sweep_md.json")
OUT = os.path.join(ROOT, "outputs", "frame_gap_audit_0818.json")

TAG = "mfixbatteryi5_blperairframe"          # 정본 메쉬 스위치 꼬리표
ELS = [0, -15, -30, -45, -52, -60, -68, -75, -82, -90]
DRONES = ["matrice4e", "mavic4pro", "mini5pro", "s1000plus"]
ARMS = ["ours", "ps_off", "refr"]
ARM_KO = {"ours": "우리 커널", "ps_off": "물리 끔", "refr": "굴절만"}


def classify(engine: str):
    """원장의 engine 태그 → (팔, 기체). 방위 팔은 None (표준 프레임 밖)."""
    if "az" in engine:
        return None
    drone = next((d for d in DRONES if d in engine), "matrice4e")
    if engine.startswith("ours"):
        arm = "ours"
    elif "onlyrefr" in engine:
        arm = "refr"
    else:
        arm = "ps_off"
    return arm, drone


def main() -> None:
    t0 = time.time()
    rows = json.load(open(LEDGER, encoding="utf-8"))["rows"]

    have = collections.defaultdict(set)
    for r in rows:
        e = r["engine"]
        if TAG not in e:
            continue
        if r.get("range_m") != 15.0 or r.get("n_poses") != 8192:
            continue
        w = classify(e)
        if w:
            have[w].add(int(round(r["el_deg"])))

    cells, missing = [], []
    for arm in ARMS:
        for drone in DRONES:
            present = sorted(have[(arm, drone)], reverse=True)
            miss = [e for e in ELS if e not in have[(arm, drone)]]
            cells.append(dict(arm=arm, arm_ko=ARM_KO[arm], drone=drone,
                              n_present=len(present), n_missing=len(miss),
                              missing_el_deg=miss))
            missing += [dict(arm=arm, drone=drone, el_deg=e) for e in miss]

    n_total = len(ARMS) * len(DRONES) * len(ELS)
    n_miss = len(missing)
    complete = n_miss == 0

    print(f"표준 프레임 {n_total} 칸 — 있음 {n_total - n_miss} · 빠짐 {n_miss}")
    print(f"{'팔':10s} {'기체':11s} 있음  빠진 앙각")
    for c in cells:
        print(f"{c['arm_ko']:10s} {c['drone']:11s} {c['n_present']:2d}/10  "
              f"{c['missing_el_deg'] if c['missing_el_deg'] else '—'}")
    print("✅ 빈칸 0 — 판정을 돌려도 된다" if complete else
          "⛔ 빈칸이 남았다 — 분류·완성표를 돌리면 각도마다 표본이 달라진다")

    doc = {
        "_meta": {
            "generator": "benchmark/frame_gap_audit_0818.py",
            # ⭐컨테이너는 UTC 로 돈다 — 한국시간은 항상 UTC+9 로 명시 환산한다
            "generated_kst": time.strftime("%Y-%m-%d %H:%M:%S (UTC+9)",
                                           time.gmtime(time.time() + 9 * 3600)),
            "role_ko": "표준 프레임(팔 3 × 기체 4 × 앙각 10)에 빈칸이 남았는지 원장에서 직접 센다",
            "gpu_used": False,
            "inputs": ["outputs/elevation_sweep_md.json"],
            "conditions_ko": "r15 · n8192 · 방위 0° · 정본 메쉬 꼬리표 " + TAG,
            "elapsed_s": round(time.time() - t0, 2),
        },
        "n_cells_total": n_total,
        "n_present": n_total - n_miss,
        "n_missing": n_miss,
        "complete": complete,
        "gate_ko": ("빈칸 0 — 판정 재실행 가능" if complete else
                    "빈칸 남음 — docs/RESUME.md 규칙에 따라 분류·완성표를 돌리지 않는다"),
        "cells": cells,
        "missing": missing,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print("saved", OUT)
    sys.exit(0 if complete else 1)


if __name__ == "__main__":
    main()
