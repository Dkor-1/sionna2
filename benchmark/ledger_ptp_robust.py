# -*- coding: utf-8 -*-
"""
ledger_ptp_robust.py — 변조 «깊이» 를 두 자로 재서 원장에 남긴다.

왜 이 파일이 생겼나
--------------------
리포트 8-2 가 «Sionna 의 p-p 가 거리마다 32.6 / 2.5 / 50.1 dB 로 요동친다» 고 적고 있었는데,
그 수치는 **어느 원장에도 없었다** — 본문에 손으로 적힌 값이었다. 원본 시계열
(`report07_three_engines.npz` · `report07_three_engine_ranges.npz`)이 남아 있으므로
지우는 대신 **다시 재서 원장에 넣는다.** 그러면 인용해도 되는 수가 된다.

무엇을 재나 — 같은 시계열을 두 자로 잰다
  p-p        max − min  [dB]   원래 정의(`report07_three_engine_maps.py:184`)와 동일.
                               ⚠ **한 자세**가 전폭을 혼자 정할 수 있다.
  p5~p95     95 백분위 − 5 백분위 [dB]   양 끝 5 %를 버린 강건한 폭.

⭐ 두 자의 **간격**이 이 원장의 요점이다. 간격이 좁으면 그 팔의 깊이는 분포 전체가 낸
   것이고, 넓으면 이상치 몇 개가 낸 것이다 — 즉 **간격 자체가 안정성의 척도**다.
   그래서 `ptp_over_p5p95` 를 함께 낸다.

⚠ 이 파일은 무엇도 다시 계산하지 않는다. 이미 저장된 시계열을 읽어 통계만 낸다 —
  그래서 GPU 도 Sionna 도 필요 없고, 값이 원 실행과 어긋날 수 없다.

읽는 것: outputs/report07_three_engines.{npz,json}
        outputs/report07_three_engine_ranges.{npz,json}
쓰는 것: outputs/report07_depth_robust.json
"""
from __future__ import annotations

import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = f"{ROOT}/outputs/report07_depth_robust.json"


def depth(E) -> dict:
    """한 시계열의 깊이를 두 자로."""
    a = 20 * np.log10(np.abs(np.asarray(E, complex)) + 1e-30)
    pp = float(a.max() - a.min())
    rb = float(np.percentile(a, 95) - np.percentile(a, 5))
    return {"n": int(a.size), "ptp_db": pp, "p5p95_db": rb,
            "ptp_over_p5p95": float(pp / rb) if rb > 1e-9 else None,
            "min_db": float(a.min()), "max_db": float(a.max()),
            # 최솟값이 혼자 전폭을 정하는지 — 최소 한 자세를 빼면 p-p 가 얼마나 줄나
            "ptp_db_drop1": float(a.max() - np.sort(a)[1])}


def main() -> None:
    out = {"_meta": {
        "generator": "benchmark/ledger_ptp_robust.py",
        "reads": ["outputs/report07_three_engines.npz",
                  "outputs/report07_three_engine_ranges.npz"],
        "what_ko": "변조 깊이를 p-p 와 p5~p95 두 자로 재서 원장화 — 본문에 손으로 적혀 "
                   "있던 수치를 대체한다",
        "definition_ko": {
            "ptp_db": "20log10|E| 의 max − min (원 정의와 동일)",
            "p5p95_db": "같은 양의 95 백분위 − 5 백분위 (양 끝 5 % 버림)",
            "ptp_over_p5p95": "두 자의 비 — 클수록 이상치 몇 개가 폭을 정한다",
            "ptp_db_drop1": "최솟값 한 자세만 빼고 다시 잰 p-p"},
        "caveat_ko": "이 값들은 **같은 실행의 같은 시계열**을 다시 잰 것이다. 실행을 다시 "
                     "하면(격자·난수) 달라질 수 있다 — 실행 간 재현성은 이 원장이 답하지 "
                     "않는다."}}

    Z = np.load(f"{ROOT}/outputs/report07_three_engines.npz")
    J = json.load(open(f"{ROOT}/outputs/report07_three_engines.json"))
    out["engines"] = {k: depth(Z[k]) for k in ("sionna", "sbr", "po")}
    out["engines_meta"] = {"range_m": J["_meta"]["range_m"],
                           "drone": J["_meta"]["drone"],
                           "n": J["_meta"]["n"], "prf_hz": J["_meta"]["prf_hz"]}

    p = f"{ROOT}/outputs/report07_three_engine_ranges.npz"
    if os.path.exists(p):
        ZR = np.load(p)
        JR = json.load(open(f"{ROOT}/outputs/report07_three_engine_ranges.json"))
        out["sionna_by_range"] = {}
        for k in ("R3", "R8", "R15"):
            if f"{k}/E" not in ZR.files:
                continue
            d = depth(ZR[f"{k}/E"])
            d["range_m"] = JR["ranges"][k]["range_m"]
            d["spp"] = JR["ranges"][k]["spp"]
            d["paths_median"] = JR["ranges"][k]["paths_median"]
            d["paths_zero_frac"] = JR["ranges"][k]["paths_zero_frac"]
            out["sionna_by_range"][k] = d

    json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1)

    print("✅ outputs/report07_depth_robust.json\n")
    print(f"  {'팔':<22}{'p-p':>9}{'p5~p95':>10}{'비':>7}{'최소한개뺀 p-p':>16}")
    for k, v in out["engines"].items():
        print(f"  {k:<22}{v['ptp_db']:>8.1f}dB{v['p5p95_db']:>9.1f}dB"
              f"{v['ptp_over_p5p95']:>7.1f}{v['ptp_db_drop1']:>15.1f}dB")
    for k, v in out.get("sionna_by_range", {}).items():
        print(f"  {'sionna @ '+str(int(v['range_m']))+' m':<22}{v['ptp_db']:>8.1f}dB"
              f"{v['p5p95_db']:>9.1f}dB{v['ptp_over_p5p95']:>7.1f}"
              f"{v['ptp_db_drop1']:>15.1f}dB")


if __name__ == "__main__":
    main()
