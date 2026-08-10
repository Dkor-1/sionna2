# -*- coding: utf-8 -*-
"""
report15_blade_flash_ladder.py — «프롭 정반사 0 칸» 이 **물리인가 예산인가**를 가른다.

왜 이 파일이 생겼나
--------------------
`report15_probe_blade_flash.py` 는 광선 **2.56 억** 발, 앙각 **0~60°** 격자에서 돌았고
«프롭 그룹을 맞은 정반사 경로 0 칸» 을 냈다. 8 권 2 편은 그 «0» 을 «Sionna 가 왜 얼룩인가» 의
주된 설명으로 쓴다.

⚠ 그런데 2026-08-10, 우리는 바로 같은 주에 **똑같은 모양의 주장**을 반증당했다:
   «40 m 는 PathSolver 의 구조적 한계» → 광선을 32M→64M 로 올리니 빈 자세가 77.3 % → 0 % 였다.
   원인은 구조가 아니라 **예산**이었다. 그때 남긴 규칙이 이것이다:

       ⭐ **벽이라고 부르기 전에 예산 사다리를 태워라.**

   2.56 억은 이 프로젝트가 쓰는 사다리의 **맨 아랫칸**이다(윗칸 10.24 억 · 40.96 억).
   그러므로 지금의 «0» 은 아직 «이 예산에서는 0» 일 뿐이다. 이 파일이 그것을 가른다.

무엇을 바꾸나 — 축 두 개를 따로 연다
  ① **예산 축**  spp 2.56 억 → 10.24 억 → 40.96 억 (같은 격자)
       올려서 프롭 정반사가 **나오면** → 예산이었다. 8 권 2 편의 설명을 갈아야 한다.
       끝까지 **0 이면** → 예산이 아니다. 그제서야 «없다» 에 가까워진다.
  ② **앙각 축**  0~60° → 0~85° (같은 예산, 맨 아랫칸)
       프롭 원판의 법선은 **위**를 향한다. 60° 격자는 법선 근처를 아예 안 본다 —
       즉 기존 «0» 은 «정반사가 날 만한 자리를 안 봤다» 일 수도 있다.
       ⚠ 이 둘을 **한 번에 바꾸면 원인을 못 가른다.** 그래서 한 축씩 연다.

⛔ 이 스크립트는 `report15_probe.json` 을 **건드리지 않는다**. 원 인구조사는 그대로 두고
   자기 원장(`outputs/report15_blade_flash_ladder.json`)에만 쓴다. 그래야 «옛 값이 무엇이었나»
   가 남는다.

    SIONNA2_GPU=2 PYTHONPATH=src python benchmark/report15_blade_flash_ladder.py
    옵션: --spp-ladder 256000000,1024000000,4096000000   --drones matrice4e
          --el-max 85   --quick(격자를 줄여 배선만 확인)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (os.path.join(ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

OUT = f"{ROOT}/outputs/report15_blade_flash_ladder.json"

#: 기존 인구조사가 쓴 격자 — 예산 축은 이것을 **그대로** 두고 spp 만 올린다.
BASE_ELS = (0.0, 10.0, 20.0, 30.0, 45.0, 60.0)
#: 앙각 축 — 프롭 법선이 향하는 가파른 쪽을 연다.
DEEP_ELS = (0.0, 10.0, 20.0, 30.0, 45.0, 60.0, 70.0, 75.0, 80.0, 85.0)


def run_cell(scan, spec, spp, els, n_az, n_phase, label):
    t0 = time.time()
    print(f"\n── {label}  spp {spp/1e6:.0f}M · 앙각 {min(els):.0f}~{max(els):.0f}° "
          f"({len(els)}단) · 방위 {n_az} · 위상 {n_phase}", flush=True)
    s = scan(spec, spp=spp, n_az=n_az, els=els, n_phase=n_phase)
    s["seconds"] = round(time.time() - t0, 1)
    # rows 는 수만 줄이라 원장이 비대해진다 — 프롭 정반사가 잡힌 줄만 남긴다(그게 증거다).
    s["rows_with_prop_specular"] = [r for r in s.get("rows", []) if r.get("prop_specular")]
    s.pop("rows", None)
    print(f"   → 정반사 칸 {s['n_cells_with_specular']}/{s['n_cells']} · "
          f"⭐**프롭** 정반사 칸 {s['n_cells_with_prop_specular']} · {s['seconds']:.0f} s",
          flush=True)
    return s


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spp-ladder", default="256000000,1024000000,4096000000")
    ap.add_argument("--drones", default="matrice4e,mini2")
    ap.add_argument("--el-max", type=float, default=85.0)
    ap.add_argument("--n-az", type=int, default=12)
    ap.add_argument("--n-phase", type=int, default=8)
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()

    import report15_probe_blade_flash as BF                             # noqa: E402
    from drones import DRONES                                           # noqa: E402

    ladder = [int(x) for x in a.spp_ladder.split(",") if x.strip()]
    keys = [k.strip() for k in a.drones.split(",") if k.strip()]
    n_az, n_phase = (4, 2) if a.quick else (a.n_az, a.n_phase)
    if a.quick:
        ladder = ladder[:1]

    out = {"_meta": {
        "generator": "benchmark/report15_blade_flash_ladder.py",
        "question_ko": "«프롭 정반사 0 칸» 이 물리인가 예산인가 — 축 두 개를 따로 연다",
        "why_ko": "같은 주에 «40 m 는 구조적 한계» 가 예산 사다리로 반증됐다(77.3 %→0 %). "
                  "같은 모양의 주장이므로 같은 검사를 받아야 한다.",
        "baseline_ko": "원 인구조사 = spp 2.56 억 · 앙각 0~60° · 방위 12 · 위상 8 "
                       "(outputs/report15_probe.json 의 blade_flash)",
        "reads_nothing_ko": "report15_probe.json 을 덮어쓰지 않는다 — 자기 원장에만 쓴다",
        "spp_ladder": ladder, "drones": keys,
        "el_base": list(BASE_ELS), "el_deep": [e for e in DEEP_ELS if e <= a.el_max],
        "n_az": n_az, "n_phase": n_phase, "quick": bool(a.quick)},
        "budget_axis": {}, "elevation_axis": {}}

    deep = tuple(e for e in DEEP_ELS if e <= a.el_max)

    for key in keys:
        spec = DRONES[key]
        # ① 예산 축 — 격자 고정, spp 만 올린다
        out["budget_axis"][key] = {
            str(spp): run_cell(BF.scan, spec, spp, BASE_ELS, n_az, n_phase,
                               f"[{key}] 예산 축")
            for spp in ladder}
        # ② 앙각 축 — 맨 아랫칸 예산 그대로, 앙각만 연다
        out["elevation_axis"][key] = {
            "deep": run_cell(BF.scan, spec, ladder[0], deep, n_az, n_phase,
                             f"[{key}] 앙각 축")}
        json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1)

    # 판정 — 두 축 중 어디서 프롭 정반사가 처음 나오나
    v = {}
    for key in keys:
        b = out["budget_axis"][key]
        first = next((s for s in sorted(b, key=int)
                      if b[s]["n_cells_with_prop_specular"] > 0), None)
        e = out["elevation_axis"][key]["deep"]["n_cells_with_prop_specular"]
        v[key] = {
            "budget_first_spp_with_prop": int(first) if first else None,
            "budget_top_spp": max(int(s) for s in b),
            "budget_top_prop_cells": b[str(max(int(s) for s in b))]["n_cells_with_prop_specular"],
            "deep_elevation_prop_cells": e,
            "verdict_ko": (
                "⭐예산이었다 — 광선을 올리니 프롭 정반사가 나온다. 8 권 2 편의 «0» 설명을 갈아야 한다."
                if first else
                ("⭐앙각이었다 — 예산으로는 안 나오는데 가파른 앙각을 열면 나온다. "
                 "«0» 은 격자가 프롭 법선 근처를 안 본 결과다." if e > 0 else
                 "예산도 앙각도 아니다 — 사다리 꼭대기·앙각 85° 까지 프롭 정반사가 0 칸이다. "
                 "이제서야 «스톡 RT 가 프롭 정반사를 못 낸다» 에 가까워진다."))}
    out["verdict"] = v
    json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1)

    print("\n" + "=" * 78)
    for key, d in v.items():
        print(f"  {key}: {d['verdict_ko']}")
    print(f"✅ {OUT}")


if __name__ == "__main__":
    main()
